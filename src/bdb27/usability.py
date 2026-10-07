"""Scout-facing layer on top of the Report Card.

1. Measurement error per feature: SEM = SD_between * sqrt(1 - ICC); 90% band on a single-rep value;
   minimum detectable difference between two prospects MDD = 1.96 * sqrt(2) * SEM; and the same in
   within-position percentile points (so a scout reads "72nd pct ± 15").
2. Prospect cards with bands: for every player and every trusted-or-usable feature, the value, the
   within-position percentile, and the percentile band implied by the feature's reliability.
3. Hidden-talent test: does a trusted sensor feature identify players who out-play their draft slot?
   residual(career snaps | draft pick, group) ~ residual(feature | draft pick, group).

    python -m bdb27.usability  # -> data/derived/measurement_error.csv, prospect_cards_bands.csv, hidden_talent.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm
from scipy.stats import spearmanr, norm

from .paths import DERIVED, PQ
from .reportcard import NICE, DRILL_GROUP, group_expr

Z90 = norm.ppf(0.95)


def measurement_error() -> pl.DataFrame:
    rc = pl.read_csv(DERIVED / "report_card.csv")
    dp = pl.read_parquet(DERIVED / "drill_players.parquet")
    att = pl.read_parquet(DERIVED / "drill_attempts.parquet")
    out = pl.read_csv(DERIVED / "outcomes_all.csv").select("nfl_id", "nfl_position").with_columns(group_expr())
    inv = {v: k for k, v in NICE.items()}
    rows = []
    for r in rc.filter(pl.col("icc") > 0).to_dicts():
        dn, f, icc = r["drill"], inv[r["feature"]], r["icc"]
        # single-attempt SD within the drill's position group (use first attempt per player to avoid averaging)
        first = att.filter(pl.col("drill_name") == dn).sort("attempt").unique(subset=["nfl_id"], keep="first").join(out, on="nfl_id")
        grp = DRILL_GROUP.get(dn, "ALL")
        if grp != "ALL":
            first = first.filter(pl.col("group") == grp)
        x = first[f].drop_nulls().to_numpy()
        if len(x) < 20:
            continue
        sd = float(np.std(x, ddof=1)); sem = sd * np.sqrt(1 - icc); mdd = 1.96 * np.sqrt(2) * sem
        # percentile-point equivalents at the median: shift by +/- z*SEM and read percentile change
        med = float(np.median(x))
        pct = lambda v: float((x < v).mean() * 100)
        band_pct = (pct(med + Z90 * sem) - pct(med - Z90 * sem)) / 2
        mdd_pct = pct(med + mdd) - pct(med)
        rows.append({"drill": dn, "feature": r["feature"], "group": grp, "n": len(x), "icc": icc, "sd_between": round(sd, 3),
                     "sem": round(sem, 3), "band90": round(Z90 * sem, 3), "mdd": round(mdd, 3),
                     "band90_pctile_pts": round(band_pct, 0), "mdd_pctile_pts": round(mdd_pct, 0), "verdict": r["verdict"]})
    me = pl.DataFrame(rows).sort("icc", descending=True)
    me.write_csv(DERIVED / "measurement_error.csv")
    return me


def prospect_cards_with_bands(me: pl.DataFrame) -> pl.DataFrame:
    dp = pl.read_parquet(DERIVED / "drill_players.parquet")
    out = pl.read_csv(DERIVED / "outcomes_all.csv").select("nfl_id", "display_name", "nfl_position", "draft_year", "draft_overall_pick", "forty", "combine_weight").with_columns(group_expr())
    inv = {v: k for k, v in NICE.items()}
    keep = me.filter(~pl.col("verdict").str.starts_with("DON'T") & ~pl.col("verdict").str.starts_with("NEEDS"))
    rows = []
    for r in keep.to_dicts():
        dn, f = r["drill"], inv[r["feature"]]
        d = dp.filter(pl.col("drill_name") == dn).select("nfl_id", pl.col(f).alias("value"), "n_att").join(out, on="nfl_id")
        if r["group"] != "ALL":
            d = d.filter(pl.col("group") == r["group"])
        d = d.drop_nulls("value")
        # percentile within group; band shrinks with reps: SEM_k = SEM / sqrt(k)
        d = d.with_columns(((pl.col("value").rank("average") - 1) / (pl.len() - 1) * 100).over("group").round(0).alias("pctile"))
        sem_k = r["sem"] / np.sqrt(d["n_att"].to_numpy())
        vals = d["value"].to_numpy()
        lo = np.array([float((vals < v - Z90 * s).mean() * 100) for v, s in zip(vals, sem_k)])
        hi = np.array([float((vals < v + Z90 * s).mean() * 100) for v, s in zip(vals, sem_k)])
        d = d.with_columns(pl.Series("pctile_lo", lo.round(0)), pl.Series("pctile_hi", hi.round(0)),
                           pl.lit(dn).alias("drill"), pl.lit(r["feature"]).alias("feature"), pl.lit(r["verdict"]).alias("verdict"))
        rows.append(d.select("nfl_id", "display_name", "nfl_position", "group", "draft_year", "draft_overall_pick", "drill", "feature",
                             "value", "n_att", "pctile", "pctile_lo", "pctile_hi", "verdict"))
    cards = pl.concat(rows).sort("nfl_id", "drill", "feature")
    cards.write_csv(DERIVED / "prospect_cards_bands.csv")
    return cards


def hidden_talent(cards: pl.DataFrame) -> pl.DataFrame:
    """Within group: does feature residual (| draft pick) predict career snaps/starts residual (| draft pick)?"""
    out = pl.read_csv(DERIVED / "outcomes_all.csv").select("nfl_id", "career_offensive_snaps", "career_defensive_snaps", "career_games_started", "draft_year").with_columns(
        (pl.col("career_offensive_snaps") + pl.col("career_defensive_snaps")).alias("career_snaps"))
    rows = []
    for (dn, f, g), d in cards.group_by(["drill", "feature", "group"]):
        d = d.join(out.drop("draft_year"), on="nfl_id").drop_nulls(["value", "career_snaps"])
        if d.height < 25:
            continue
        # control for draft pick and draft year (exposure)
        X = sm.add_constant(np.column_stack([d["draft_overall_pick"].to_numpy(), np.log1p(d["draft_overall_pick"].to_numpy()),
                                             (d["draft_year"].to_numpy() == 2024).astype(float), (d["draft_year"].to_numpy() == 2025).astype(float)]))
        rx = sm.OLS(d["value"].to_numpy().astype(float), X).fit().resid
        res = {"drill": dn, "feature": f, "group": g, "n": d.height}
        for oc in ["career_snaps", "career_games_started"]:
            ry = sm.OLS(np.log1p(d[oc].to_numpy().astype(float)), X).fit().resid
            rho, p = spearmanr(rx, ry)
            res[f"rho_{oc}"] = round(rho, 3); res[f"p_{oc}"] = round(p, 3)
        rows.append(res)
    ht = pl.DataFrame(rows).sort("p_career_snaps")
    ht.write_csv(DERIVED / "hidden_talent.csv")
    return ht


def main() -> None:
    me = measurement_error()
    with pl.Config(tbl_rows=40, tbl_width_chars=200):
        print(me.filter(~pl.col("verdict").str.starts_with("DON'T")).select("drill", "feature", "group", "icc", "sd_between", "sem", "mdd", "band90_pctile_pts", "mdd_pctile_pts", "verdict"))
    cards = prospect_cards_with_bands(me)
    print(f"prospect card rows: {cards.height}; players: {cards['nfl_id'].n_unique()}; features: {cards.select('drill','feature').unique().height}")
    ht = hidden_talent(cards)
    with pl.Config(tbl_rows=40, tbl_width_chars=200):
        print(ht)


if __name__ == "__main__":
    main()
