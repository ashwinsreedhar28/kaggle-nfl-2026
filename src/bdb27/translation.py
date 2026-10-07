"""Stage 1 — does Combine tracking predict in-game movement better than the stopwatch?

For each position group and in-game outcome (top speed p95, median max accel per
play, p90 lateral accel), compare nested OLS models by leave-one-out R^2:
  M0  controls:  weight + draft pick
  M1  M0 + stopwatch (forty, ten_yd_split)
  M2  M0 + sensor   (vmax, v10, accel_resid = v10 | vmax)
  M3  M0 + stopwatch + sensor
and report standardized coefficients from M3.

Stage 2 — production, where the data supports it:
  IDL/EDGE pressure_rate ~ controls + sensor (binomial, snaps-weighted)
  WR yac_oe / sep_oe / epa_per_target ~ controls + sensor

    python -m bdb27.translation   # -> data/derived/translation_stage1.csv, translation_stage2.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm

from .paths import DERIVED
from .screen import GROUPS

CONTROLS = ["combine_weight", "draft_overall_pick"]
STOPWATCH = ["forty", "ten_yd_split"]
SENSOR = ["vmax", "accel_resid"]  # v10 = f(vmax) + accel_resid, so v10 itself would be collinear
IG_OUTCOMES = ["ig_s_p95", "ig_amax_med", "ig_lat_ac_p90"]
MIN_IG_PLAYS = 40


def table() -> pl.DataFrame:
    out = pl.read_csv(DERIVED / "outcomes_all.csv").with_columns(pl.col(pl.Float64).fill_nan(None))
    f = pl.read_csv(DERIVED / "forty_players.csv").select("nfl_id", "vmax", "v10", "v20", "t10", "t40", "n_att")
    d = out.join(f, on="nfl_id", how="inner")
    # acceleration independent of top speed: residual of v10 on vmax (pooled)
    z = d.select("v10", "vmax").drop_nulls()
    b = np.polyfit(z["vmax"].to_numpy(), z["v10"].to_numpy(), 1)
    d = d.with_columns((pl.col("v10") - (b[0] * pl.col("vmax") + b[1])).alias("accel_resid"))
    grp = pl.when(pl.lit(False)).then(pl.lit("")).otherwise(pl.lit("OTHER"))
    for g, poss in GROUPS.items():
        grp = pl.when(pl.col("nfl_position").is_in(poss)).then(pl.lit(g)).otherwise(grp)
    d = d.with_columns(grp.alias("group"))
    d.write_csv(DERIVED / "translation_table.csv")
    return d


def _z(X: np.ndarray) -> np.ndarray:
    return (X - X.mean(0)) / X.std(0, ddof=1)


def loo_r2(X: np.ndarray, y: np.ndarray) -> float:
    n = len(y); pred = np.empty(n)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        beta, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        pred[i] = X[i] @ beta
    return 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)


def stage1(d: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for g in ["WR", "TE", "OL", "EDGE", "IDL", "DB", "LB", "ALL"]:
        sub = d if g == "ALL" else d.filter(pl.col("group") == g)
        sub = sub.filter(pl.col("ig_plays") >= MIN_IG_PLAYS)
        for oc in IG_OUTCOMES:
            s = sub.select(oc, *CONTROLS, *STOPWATCH, *SENSOR).drop_nulls()
            if s.height < 20:
                continue
            y = s[oc].to_numpy().astype(float)
            def X(cols): return np.column_stack([np.ones(s.height), _z(s.select(cols).to_numpy().astype(float))])
            r = {"group": g, "outcome": oc, "n": s.height,
                 "r2_controls": loo_r2(X(CONTROLS), y), "r2_stopwatch": loo_r2(X(CONTROLS + STOPWATCH), y),
                 "r2_sensor": loo_r2(X(CONTROLS + SENSOR), y), "r2_both": loo_r2(X(CONTROLS + STOPWATCH + SENSOR), y)}
            fit = sm.OLS(y, X(CONTROLS + STOPWATCH + SENSOR)).fit()
            for name, b, p in zip(CONTROLS + STOPWATCH + SENSOR, fit.params[1:], fit.pvalues[1:]):
                r[f"b_{name}"] = round(b, 3); r[f"p_{name}"] = round(p, 3)
            rows.append(r)
    res = pl.DataFrame(rows).with_columns(pl.col("^r2_.*$").round(3))
    res = res.with_columns((pl.col("r2_sensor") - pl.col("r2_stopwatch")).round(3).alias("sensor_minus_stopwatch"))
    return res


def stage2(d: pl.DataFrame) -> pl.DataFrame:
    rows = []
    specs = [("IDL", "pressure_rate", "rush_snaps", 100, True), ("EDGE", "pressure_rate", "rush_snaps", 100, True),
             ("IDL", "quick_pressure_rate", "rush_snaps", 100, True), ("EDGE", "quick_pressure_rate", "rush_snaps", 100, True),
             ("WR", "yac_oe", "targets", 30, False), ("WR", "sep_oe", "targets", 30, False), ("WR", "epa_per_target", "targets", 30, False),
             ("TE", "yac_oe", "targets", 30, False), ("OL", "pressure_allowed_rate", "pp_snaps", 100, True)]
    for g, oc, vol, mn, binom in specs:
        s = d.filter((pl.col("group") == g) & (pl.col(vol) >= mn)).select(oc, vol, *CONTROLS, *SENSOR, "forty").drop_nulls()
        if s.height < 15:
            continue
        Xc = np.column_stack([np.ones(s.height), _z(s.select(CONTROLS).to_numpy().astype(float))])
        Xs = np.column_stack([Xc, _z(s.select(SENSOR).to_numpy().astype(float))])
        Xf = np.column_stack([Xc, _z(s.select(["forty"]).to_numpy().astype(float))])
        if binom:
            n = s[vol].to_numpy().astype(float); k = np.round(s[oc].to_numpy() * n)
            def fit(X): return sm.GLM(np.column_stack([k, n - k]), X, family=sm.families.Binomial()).fit()
            f0, f1, ff = fit(Xc), fit(Xs), fit(Xf)
            r = {"group": g, "outcome": oc, "n": s.height, "model": "binomial",
                 "dev_controls": round(f0.deviance, 1), "dev_sensor": round(f1.deviance, 1), "dev_stopwatch": round(ff.deviance, 1)}
        else:
            y = s[oc].to_numpy().astype(float)
            f1 = sm.OLS(y, Xs).fit()
            r = {"group": g, "outcome": oc, "n": s.height, "model": "ols",
                 "r2_loo_controls": round(loo_r2(Xc, y), 3), "r2_loo_sensor": round(loo_r2(Xs, y), 3), "r2_loo_stopwatch": round(loo_r2(Xf, y), 3)}
        for name, b, p in zip(SENSOR, f1.params[-len(SENSOR):], f1.pvalues[-len(SENSOR):]):
            r[f"b_{name}"] = round(b, 3); r[f"p_{name}"] = round(p, 3)
        rows.append(r)
    return pl.DataFrame(rows)


def main() -> None:
    d = table()
    print(d.group_by("group").len().sort("group"))
    s1 = stage1(d); s1.write_csv(DERIVED / "translation_stage1.csv")
    with pl.Config(tbl_rows=40, tbl_width_chars=200, tbl_cols=20):
        print(s1.select("group", "outcome", "n", "r2_controls", "r2_stopwatch", "r2_sensor", "r2_both", "sensor_minus_stopwatch",
                        "b_forty", "p_forty", "b_ten_yd_split", "p_ten_yd_split", "b_vmax", "p_vmax", "b_accel_resid", "p_accel_resid"))
        s2 = stage2(d); s2.write_csv(DERIVED / "translation_stage2.csv"); print(s2)


if __name__ == "__main__":
    main()
