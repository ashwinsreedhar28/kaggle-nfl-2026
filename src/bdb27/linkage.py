"""Linkage v0: does hoop-drill bend add to stopwatch/size controls in predicting
NFL pass-rush production, within position group?

Model: binomial GLM  pressures ~ controls (+ bend feature), weights = rush snaps.
Reported per feature:
  rho_partial   Spearman of feature vs outcome after residualizing both on controls
  beta_sd       GLM log-odds coefficient per 1 SD of the feature (bootstrap 95% CI)
  d_loo_dev     LOO-CV binomial deviance (controls+feature) minus (controls only); negative = helps

    python -m bdb27.linkage            # -> data/derived/linkage_v0.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm
from scipy.stats import spearmanr

from .paths import DERIVED, PQ

MIN_SNAPS = 100
EDGE = {"DE", "OLB"}
INTERIOR = {"DT", "NT"}
CONTROLS = ["ten_yd_split", "combine_weight", "arm_length"]
FEATURES = ["move_time", "bend_dur", "bend_s_mean", "bend_index", "loopB_s_mean", "hoop1_s_mean",
            "exit_s_peak", "asym_s", "three_cone", "short_shuttle", "ngs_athleticism_score"]
OUTCOMES = {"pressure": "pressure_rate", "quick_pressure": "quick_pressure_rate", "sack": "sack_rate"}


def analysis_table() -> pl.DataFrame:
    b = pl.read_csv(DERIVED / "bend_players.csv")
    o = pl.read_csv(DERIVED / "rush_outcomes_career.csv")
    c = pl.read_parquet(PQ / "combine_results.parquet")
    p = pl.read_parquet(PQ / "players.parquet").select("nfl_id", "nfl_position", "draft_overall_pick", "display_name")
    d = b.join(o, on="nfl_id").join(c, on="nfl_id").join(p, on="nfl_id").filter(pl.col("rush_snaps") >= MIN_SNAPS)
    d = d.with_columns(
        pl.when(pl.col("nfl_position").is_in(EDGE)).then(pl.lit("EDGE"))
        .when(pl.col("nfl_position").is_in(INTERIOR)).then(pl.lit("IDL")).otherwise(pl.lit("OTHER")).alias("group"),
        pl.col("draft_overall_pick").fill_null(260),
    )
    d.write_csv(DERIVED / "analysis_table.csv")
    return d


def _design(df: pl.DataFrame, cols: list[str]) -> np.ndarray:
    X = df.select(cols).to_numpy().astype(float)
    X = (X - X.mean(0)) / X.std(0, ddof=1)
    return sm.add_constant(X)


def _fit(X, k, n):
    return sm.GLM(np.column_stack([k, n - k]), X, family=sm.families.Binomial()).fit()


def _loo_deviance(X, k, n) -> float:
    dev = 0.0
    for i in range(len(k)):
        m = np.ones(len(k), bool); m[i] = False
        r = _fit(X[m], k[m], n[m])
        p = float(np.clip(r.predict(X[i:i + 1])[0], 1e-6, 1 - 1e-6))
        ki, ni = k[i], n[i]
        dev += -2 * (ki * np.log(p) + (ni - ki) * np.log(1 - p))
    return dev


def evaluate(d: pl.DataFrame, outcome: str, n_boot: int = 500, seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    n = d["rush_snaps"].to_numpy().astype(float)
    k = np.round(d[OUTCOMES[outcome]].to_numpy() * n)
    X0 = _design(d, CONTROLS)
    base_dev = _loo_deviance(X0, k, n)
    base = _fit(X0, k, n)
    resid_y = base.resid_response  # outcome residual after controls
    rows = []
    for f in FEATURES:
        sub = d.filter(pl.col(f).is_not_null())
        if sub.height < d.height:  # refit controls on the subset with this feature
            n_s = sub["rush_snaps"].to_numpy().astype(float); k_s = np.round(sub[OUTCOMES[outcome]].to_numpy() * n_s)
            X0s = _design(sub, CONTROLS); bdev = _loo_deviance(X0s, k_s, n_s); ry = _fit(X0s, k_s, n_s).resid_response
        else:
            n_s, k_s, X0s, bdev, ry = n, k, X0, base_dev, resid_y
        X1 = _design(sub, CONTROLS + [f])
        fit = _fit(X1, k_s, n_s)
        # feature residualized on controls
        fx = sm.OLS(X1[:, -1], X0s).fit().resid
        rho, pv = spearmanr(fx, ry)
        betas = []
        for _ in range(n_boot):
            idx = rng.integers(0, sub.height, sub.height)
            try:
                betas.append(_fit(X1[idx], k_s[idx], n_s[idx]).params[-1])
            except Exception:
                pass
        lo, hi = np.percentile(betas, [2.5, 97.5])
        rows.append({
            "outcome": outcome, "feature": f, "n": sub.height,
            "rho_partial": round(rho, 3), "p_partial": round(pv, 3),
            "beta_sd": round(fit.params[-1], 3), "ci_lo": round(lo, 3), "ci_hi": round(hi, 3),
            "d_loo_dev": round(_loo_deviance(X1, k_s, n_s) - bdev, 1),
        })
    return pl.DataFrame(rows)


def main() -> None:
    d = analysis_table()
    print(d.group_by("group").agg(pl.len(), pl.col("rush_snaps").median()).sort("group"))
    out = []
    for grp in ("EDGE", "IDL", "ALL"):
        sub = d if grp == "ALL" else d.filter(pl.col("group") == grp)
        for oc in OUTCOMES:
            r = evaluate(sub, oc).with_columns(pl.lit(grp).alias("group"))
            out.append(r)
    res = pl.concat(out).select("group", "outcome", "feature", "n", "rho_partial", "p_partial", "beta_sd", "ci_lo", "ci_hi", "d_loo_dev")
    res.write_csv(DERIVED / "linkage_v0.csv")
    with pl.Config(tbl_rows=200, tbl_cols=12, tbl_width_chars=160):
        print(res.filter(pl.col("outcome") == "pressure").sort("group", "d_loo_dev"))


if __name__ == "__main__":
    main()
