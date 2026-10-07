"""40-yd dash speed-curve decomposition from Combine tracking.

Per attempt we fit the classic mono-exponential sprint model
    v(t) = vmax * (1 - exp(-(t - t0) / tau)),  t >= t0
giving vmax (top speed, yd/s), tau (acceleration time constant, s: small = reaches
top speed quickly) and t0 (movement onset). From the fit and the raw track:
  vmax, tau, t0, fit_rmse
  v10, v20, v40       speed when 10/20/40 yd of path have been covered
  t10, t20, t40       model-implied split times from onset
  d95                 distance (yd) needed to reach 95% of vmax
  a0                  initial acceleration = vmax / tau (yd/s^2)
  v_end_drop          vmax - speed at 40 yd (fade)
Player level: mean over attempts (and best vmax), plus test-retest ICC.

    python -m bdb27.forty   # -> data/derived/forty_attempts.csv, forty_players.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
from scipy.optimize import curve_fit

from .paths import DERIVED, PQ

ONSET_S = 1.0  # yd/s; speed threshold for movement onset (tracking starts before the clock)


def _model(t, vmax, tau, t0):
    return vmax * (1.0 - np.exp(-np.clip(t - t0, 0, None) / tau))


def fit_attempt(g: pl.DataFrame) -> dict | None:
    if g.height < 25:
        return None
    t = g["time"].dt.epoch("us").to_numpy() / 1e6
    t = t - t[0]
    s = g["s"].to_numpy().astype(float)
    x, y = g["x"].to_numpy().astype(float), g["y"].to_numpy().astype(float)
    onset = int(np.argmax(s >= ONSET_S))
    if s[onset] < ONSET_S:
        return None
    # distance along the track from the onset position
    d = np.hypot(x - x[onset], y - y[onset])
    d[:onset] = 0.0
    # fit only the forward run: from onset to the first frame past 40 yd (or end)
    end = int(np.argmax(d >= 40.0)) if (d >= 40.0).any() else len(d)
    end = max(end + 1, onset + 15)
    tt, ss = t[onset:end], s[onset:end]
    try:
        p, _ = curve_fit(_model, tt, ss, p0=[max(ss.max(), 5.0), 1.2, tt[0] - 0.1],
                         bounds=([5.0, 0.3, tt[0] - 1.0], [13.0, 4.0, tt[0] + 0.6]), maxfev=4000)
    except Exception:
        return None
    vmax, tau, t0 = p
    rmse = float(np.sqrt(np.mean((_model(tt, *p) - ss) ** 2)))

    def v_at(dist):
        idx = np.where(d >= dist)[0]
        return float(s[idx[0]]) if idx.size else np.nan

    def t_model(dist):  # invert distance of the model numerically
        tg = np.arange(0, 8, 0.001)
        dist_m = np.cumsum(_model(tg + t0, vmax, tau, t0)) * 0.001
        idx = np.where(dist_m >= dist)[0]
        return float(tg[idx[0]]) if idx.size else np.nan

    return {
        "vmax": float(vmax), "tau": float(tau), "t0": float(t0 - t[onset]), "fit_rmse": rmse,
        "a0": float(vmax / tau),
        "v10": v_at(10), "v20": v_at(20), "v40": v_at(40),
        "t10": t_model(10), "t20": t_model(20), "t40": t_model(40),
        "s_peak_raw": float(s.max()), "v_end_drop": float(s.max() - v_at(40)) if not np.isnan(v_at(40)) else np.nan,
        "track_yds": float(d.max()), "n_frames": int(g.height),
    }


def main() -> None:
    ct = (
        pl.scan_parquet(PQ / "combine_tracking.parquet")
        .filter((pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "FORTY_YARD_DASH"))
        .sort("event_id", "time").collect()
    )
    rows = []
    for (ev, nid, yr, att), g in ct.group_by(["event_id", "nfl_id", "draft_year", "attempt"], maintain_order=True):
        f = fit_attempt(g)
        if f:
            rows.append({"event_id": ev, "nfl_id": nid, "draft_year": yr, "attempt": att, **f})
    a = pl.DataFrame(rows)
    # d95 = distance covered while reaching 95% of vmax (t = 3*tau): vmax*(3tau - tau(1-e^-3))
    a = a.with_columns((pl.col("vmax") * (3 * pl.col("tau") - pl.col("tau") * (1 - np.exp(-3.0)))).alias("d95"))
    a.write_csv(DERIVED / "forty_attempts.csv")
    feats = ["vmax", "tau", "a0", "v10", "v20", "v40", "t10", "t20", "t40", "d95", "v_end_drop", "fit_rmse"]
    p = a.group_by("nfl_id").agg(pl.len().alias("n_att"), *[pl.col(f).mean() for f in feats], pl.col("vmax").max().alias("vmax_best"))
    c = pl.read_parquet(PQ / "combine_results.parquet").select("nfl_id", "forty", "ten_yd_split", "combine_position")
    p = p.join(c, on="nfl_id", how="left")
    p.write_csv(DERIVED / "forty_players.csv")
    print(f"attempts fit: {a.height} / players: {p.height}; median rmse {a['fit_rmse'].median():.3f} yd/s")
    print(a.select("vmax", "tau", "a0", "t10", "t20", "t40", "d95", "v_end_drop").describe())
    from scipy.stats import pearsonr
    for f, o in (("t40", "forty"), ("t10", "ten_yd_split"), ("vmax", "forty"), ("tau", "ten_yd_split")):
        z = p.select(f, o).drop_nulls()
        print(f"{f} vs official {o}: r={pearsonr(z[f], z[o])[0]:+.3f}  mean diff={float((z[f]-z[o]).mean()):+.3f}  n={z.height}")
    # ICC for players with 2 attempts
    m = a.filter(pl.len().over("nfl_id") >= 2)
    for f in feats:
        grp = m.group_by("nfl_id").agg(pl.col(f).mean().alias("m"), pl.col(f).var().alias("v"))
        w, b = float(grp["v"].mean()), float(grp["m"].var())
        print(f"ICC {f}: {(b - w/2)/(b + w/2):.3f}")


if __name__ == "__main__":
    main()
