"""Mass screen: every (position group, drill, tracking feature) vs every relevant
outcome, as partial Spearman after controlling weight + draft overall pick.
Stopwatch/jump numbers are screened too (drill = STOPWATCH) as the baseline to beat.
BH-FDR q-values within each group.

    python -m bdb27.screen   # -> data/derived/screen.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm
from scipy.stats import spearmanr

from .paths import DERIVED

GROUPS = {
    "WR": ["WR"], "TE": ["TE"], "OL": ["T", "G", "C"], "EDGE": ["DE", "OLB"], "IDL": ["DT", "NT"],
    "DB": ["CB", "FS", "SS", "DB"], "LB": ["ILB", "MLB"],
}
OUTCOMES = {
    "WR": ["sep_oe", "yac_oe", "epa_per_target", "catch_rate", "ig_s_p95", "ig_lat_ac_p90", "career_games_started"],
    "TE": ["sep_oe", "yac_oe", "epa_per_target", "pressure_allowed_rate", "ig_s_p95", "career_games_started"],
    "OL": ["pressure_allowed_rate", "peak_ppa_mean", "sack_allowed_rate", "ig_s_p95", "ig_amax_med", "career_games_started"],
    "EDGE": ["pressure_rate", "quick_pressure_rate", "sack_rate", "get_off_median", "ig_s_p95", "ig_lat_ac_p90", "career_games_started"],
    "IDL": ["pressure_rate", "quick_pressure_rate", "sack_rate", "get_off_median", "ig_s_p95", "career_games_started"],
    "DB": ["ig_s_p95", "ig_lat_ac_p90", "ig_amax_med", "career_defensive_snaps", "career_games_started"],
    "LB": ["ig_s_p95", "ig_lat_ac_p90", "career_games_started"],
}
MIN_N = {"sep_oe": 30, "yac_oe": 30, "epa_per_target": 30, "catch_rate": 30, "pressure_rate": 100, "quick_pressure_rate": 100,
         "sack_rate": 100, "get_off_median": 100, "pressure_allowed_rate": 100, "peak_ppa_mean": 100, "sack_allowed_rate": 100,
         "ig_s_p95": 40, "ig_lat_ac_p90": 40, "ig_amax_med": 40}
VOLUME = {"sep_oe": "targets", "yac_oe": "targets", "epa_per_target": "targets", "catch_rate": "targets",
          "pressure_rate": "rush_snaps", "quick_pressure_rate": "rush_snaps", "sack_rate": "rush_snaps", "get_off_median": "rush_snaps",
          "pressure_allowed_rate": "pp_snaps", "peak_ppa_mean": "pp_snaps", "sack_allowed_rate": "pp_snaps",
          "ig_s_p95": "ig_plays", "ig_lat_ac_p90": "ig_plays", "ig_amax_med": "ig_plays"}
FEATS = ["duration", "s_peak", "t_peak", "t_90pct", "a_max", "a_min", "a_mean_1s", "s_mean_moving", "lat_ac_max", "lat_ac_p90",
         "s_min_after_peak", "t_10yd", "t_20yd"]
STOPWATCH = ["forty", "ten_yd_split", "three_cone", "short_shuttle", "vertical", "broad_jump", "bench_reps", "ngs_athleticism_score"]
CONTROLS = ["combine_weight", "draft_overall_pick"]


def bh(p: np.ndarray) -> np.ndarray:
    n = len(p); order = np.argsort(p); ranked = np.empty(n)
    ranked[order] = p[order] * n / (np.arange(n) + 1)
    out = np.minimum.accumulate(ranked[order][::-1])[::-1]; q = np.empty(n); q[order] = out
    return np.clip(q, 0, 1)


def partial_rho(df: pl.DataFrame, f: str, oc: str):
    s = df.select(f, oc, *CONTROLS).drop_nulls().filter(pl.col(f).is_finite() & pl.col(oc).is_finite())
    if s.height < 12:
        return None
    X = sm.add_constant(s.select(*CONTROLS).to_numpy().astype(float))
    rx = sm.OLS(s[f].to_numpy().astype(float), X).fit().resid
    ry = sm.OLS(s[oc].to_numpy().astype(float), X).fit().resid
    rho, p = spearmanr(rx, ry)
    raw = spearmanr(s[f], s[oc])[0]
    return s.height, raw, rho, p


def main() -> None:
    out = pl.read_csv(DERIVED / "outcomes_all.csv").with_columns(pl.col(pl.Float64).fill_nan(None))
    dp = pl.read_parquet(DERIVED / "drill_players.parquet")
    rows = []
    for grp, poss in GROUPS.items():
        base = out.filter(pl.col("nfl_position").is_in(poss))
        for oc in OUTCOMES[grp]:
            sub = base
            if oc in VOLUME:
                sub = sub.filter(pl.col(VOLUME[oc]) >= MIN_N[oc])
            for sw in STOPWATCH:
                r = partial_rho(sub, sw, oc)
                if r:
                    rows.append({"group": grp, "outcome": oc, "drill": "STOPWATCH", "feature": sw, "n": r[0], "raw": r[1], "rho": r[2], "p": r[3]})
            for (dn,), d in dp.group_by(["drill_name"]):
                m = sub.join(d, on="nfl_id")
                if m.height < 20:
                    continue
                for f in FEATS:
                    r = partial_rho(m, f, oc)
                    if r and r[0] >= 20:
                        rows.append({"group": grp, "outcome": oc, "drill": dn, "feature": f, "n": r[0], "raw": r[1], "rho": r[2], "p": r[3]})
    res = pl.DataFrame(rows)
    parts = []
    for (g,), s in res.group_by(["group"]):
        parts.append(s.with_columns(pl.Series("q", bh(s["p"].to_numpy()))))
    res = pl.concat(parts).with_columns(pl.col("raw", "rho").round(3), pl.col("p", "q").round(4)).sort("group", "q")
    res.write_csv(DERIVED / "screen.csv")
    print(f"{res.height} tests")
    with pl.Config(tbl_rows=120, tbl_width_chars=170):
        print(res.filter((pl.col("q") < 0.10) & (pl.col("rho").abs() > 0.3)).sort("group", "outcome", "q"))


if __name__ == "__main__":
    main()
