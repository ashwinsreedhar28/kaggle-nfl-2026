"""Combine Sensor Report Card — the usable artifact.

One row per (drill, sensor feature) with:
  icc            single-rep test-retest reliability (from features.py)
  reps_for_0.8   reps needed to reach ICC 0.8 (Spearman-Brown: k = 0.8(1-r) / (r(1-0.8)))
  redundancy     |r| with the best stopwatch number for that drill (forty / ten / three_cone / shuttle)
  transfer_move  partial Spearman with in-game top speed within the drill's position group,
                 after weight + draft slot + stopwatch (incremental over what scouts already have)
  transfer_prod  best |partial rho| with a production outcome for that group (from screen.csv), with q
  verdict        USE / USE WITH 2+ REPS / REDUNDANT / DON'T USE
Also writes a per-player prospect card table using only USE-tier features (within-position percentiles)
and the game-speed index (in-game top speed minus Combine top speed, position-adjusted).

    python -m bdb27.reportcard  # -> data/derived/report_card.csv, prospect_cards.csv, game_speed_index.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm
from scipy.stats import spearmanr

from .paths import DERIVED, PQ
from .screen import GROUPS

DRILL_GROUP = {  # which position group runs the drill (for transfer tests); 40 -> all
    "BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION": "DB", "BACK_PEDAL_AND_90_DEGREE_BREAK": "DB", "W_DRILL": "DB", "LINE_DRILL": "DB",
    "GAUNTLET_DRILL": "WR", "PASS_RUSH_DRILL": "EDGE", "RUN_THE_HOOP_DRILL": "EDGE", "PASS_RUSH_DROP": "OL",
    "FIVE_YARD_WAVE_DRILL_SLIDE_AND_SHUFFLE": "OL", "THREE_CONE_DRILL": "ALL", "SHORT_SHUTTLE": "ALL", "FORTY_YARD_DASH": "ALL",
    "CORNER_ROUTE": "TE", "SHORT_ZONE_BREAKS": "EDGE",
}
STOPWATCH_FOR = {"FORTY_YARD_DASH": ["forty", "ten_yd_split"], "THREE_CONE_DRILL": ["three_cone"], "SHORT_SHUTTLE": ["short_shuttle"]}
FEATS = ["duration", "s_peak", "t_10yd", "t_20yd", "a_max", "a_mean_1s", "s_min_after_peak", "lat_ac_p90"]
NICE = {"duration": "drill time", "s_peak": "top speed", "t_10yd": "time to 10 yd", "t_20yd": "time to 20 yd", "a_max": "max accel",
        "a_mean_1s": "accel, first 1 s", "s_min_after_peak": "speed trough", "lat_ac_p90": "lateral accel (p90)"}


def reps_needed(icc: float, target: float = 0.8) -> float:
    if icc <= 0:
        return np.inf
    return target * (1 - icc) / (icc * (1 - target))


def group_expr() -> pl.Expr:
    e = pl.lit("OTHER")
    for g, poss in GROUPS.items():
        e = pl.when(pl.col("nfl_position").is_in(poss)).then(pl.lit(g)).otherwise(e)
    return e.alias("group")


def partial_rho(df: pl.DataFrame, f: str, oc: str, ctrl: list[str]):
    s = df.select(f, oc, *ctrl).drop_nulls()
    if s.height < 15:
        return np.nan, np.nan, s.height
    X = sm.add_constant(s.select(*ctrl).to_numpy().astype(float))
    rx = sm.OLS(s[f].to_numpy().astype(float), X).fit().resid
    ry = sm.OLS(s[oc].to_numpy().astype(float), X).fit().resid
    r, p = spearmanr(rx, ry)
    return r, p, s.height


def main() -> None:
    rel = pl.read_csv(DERIVED / "drill_reliability.csv").filter(pl.col("icc").is_not_nan() & (pl.col("players") >= 20))
    dp = pl.read_parquet(DERIVED / "drill_players.parquet")
    out = pl.read_csv(DERIVED / "outcomes_all.csv").with_columns(pl.col(pl.Float64).fill_nan(None)).with_columns(group_expr())
    scr = pl.read_csv(DERIVED / "screen.csv")
    base_ctrl = ["combine_weight", "draft_overall_pick", "forty"]
    rows = []
    for (dn,), sub in rel.group_by(["drill_name"]):
        grp = DRILL_GROUP.get(dn)
        if grp is None:
            continue
        d = out.join(dp.filter(pl.col("drill_name") == dn), on="nfl_id")
        if grp != "ALL":
            d = d.filter(pl.col("group") == grp)
        d = d.filter(pl.col("ig_plays") >= 40)
        for f in FEATS:
            r = sub.filter(pl.col("feature") == f)
            if not r.height:
                continue
            icc = float(r["icc"][0]); nplayers = int(r["players"][0])
            # redundancy with stopwatch
            red = 0.0
            for sw in STOPWATCH_FOR.get(dn, ["forty"]):
                z = d.select(f, sw).drop_nulls()
                if z.height >= 15:
                    red = max(red, abs(spearmanr(z[f], z[sw])[0]))
            # incremental transfer to in-game top speed, over weight+draft+forty
            rho_m, p_m, n_m = partial_rho(d, f, "ig_s_p95", base_ctrl)
            # best production transfer from the screen (already adjusted for weight+draft)
            sc = scr.filter((pl.col("drill") == dn) & (pl.col("feature") == f) & ~pl.col("outcome").str.starts_with("ig_") & ~pl.col("outcome").str.starts_with("career"))
            if grp != "ALL":
                sc = sc.filter(pl.col("group") == grp)
            if sc.height:
                best = sc.sort(pl.col("rho").abs(), descending=True).row(0, named=True)
                prod = f"{best['outcome']} ({best['group']}): ρ={best['rho']:+.2f}, q={best['q']:.2f}"; prod_rho, prod_q = best["rho"], best["q"]
            else:
                prod, prod_rho, prod_q = "—", np.nan, np.nan
            k = reps_needed(icc)
            if icc >= 0.8:
                verdict = "REDUNDANT with stopwatch" if red >= 0.9 else "USE"
            elif icc >= 0.5:
                verdict = f"USE WITH {int(np.ceil(k))}+ REPS"
            else:
                verdict = "DON'T USE" if k > 6 or not np.isfinite(k) else f"NEEDS {int(np.ceil(k))} REPS"
            rows.append({"drill": dn, "feature": NICE[f], "group": grp, "players_2reps": nplayers, "icc": round(icc, 2),
                         "reps_for_0.8": round(k, 1) if np.isfinite(k) else None, "redundancy_stopwatch": round(red, 2),
                         "transfer_move_rho": round(rho_m, 2) if not np.isnan(rho_m) else None, "transfer_move_p": round(p_m, 3) if not np.isnan(p_m) else None,
                         "n_move": n_m, "transfer_prod_best": prod, "verdict": verdict})
    rc = pl.DataFrame(rows).sort("icc", descending=True)
    rc.write_csv(DERIVED / "report_card.csv")
    with pl.Config(tbl_rows=120, tbl_width_chars=220, fmt_str_lengths=60):
        print(rc.select("drill", "feature", "group", "icc", "reps_for_0.8", "redundancy_stopwatch", "transfer_move_rho", "transfer_move_p", "verdict"))

    # ---- prospect cards: USE-tier features as within-position percentiles ----
    use_feats = [(r["drill"], r["feature"]) for r in rc.filter(pl.col("verdict") == "USE").to_dicts()]
    inv = {v: k for k, v in NICE.items()}
    cards = out.select("nfl_id", "display_name", "nfl_position", "group", "draft_year", "draft_overall_pick", "forty", "combine_weight")
    for dn, nice in use_feats:
        f = inv[nice]
        feat = dp.filter(pl.col("drill_name") == dn).select("nfl_id", pl.col(f).alias(f"{dn}:{nice}"))
        cards = cards.join(feat, on="nfl_id", how="left")
    val_cols = [c for c in cards.columns if ":" in c]
    cards = cards.with_columns([((pl.col(c).rank("average") - 1) / (pl.col(c).count() - 1) * 100).over("group").round(0).alias(c + " [pctl in group]") for c in val_cols])
    cards.write_csv(DERIVED / "prospect_cards.csv")
    print(f"prospect cards: {cards.height} players, {len(val_cols)} trusted sensor features: {val_cols}")

    # ---- game-speed index ----
    fp = pl.read_csv(DERIVED / "forty_players.csv").select("nfl_id", "vmax")
    g = out.join(fp, on="nfl_id").filter(pl.col("ig_plays") >= 40).select("nfl_id", "display_name", "nfl_position", "group", "vmax", "ig_s_p95", "ig_plays")
    # residual of in-game top speed on Combine top speed, within group
    parts = []
    for (grp,), s in g.group_by(["group"]):
        if s.height < 15:
            continue
        b = np.polyfit(s["vmax"].to_numpy(), s["ig_s_p95"].to_numpy(), 1)
        parts.append(s.with_columns((pl.col("ig_s_p95") - (b[0] * pl.col("vmax") + b[1])).round(2).alias("game_speed_index"),
                                     pl.lit(round(float(np.corrcoef(s["vmax"], s["ig_s_p95"])[0, 1]), 2)).alias("r_group")))
    gsi = pl.concat(parts).sort("game_speed_index", descending=True)
    gsi.write_csv(DERIVED / "game_speed_index.csv")
    print(gsi.group_by("group").agg(pl.len(), pl.col("r_group").first(), pl.col("game_speed_index").std().round(2)).sort("group"))
    print(gsi.head(8)); print(gsi.tail(5))


if __name__ == "__main__":
    main()
