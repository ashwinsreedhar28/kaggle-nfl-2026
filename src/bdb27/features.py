"""Generic per-attempt kinematic features for EVERY Combine drill, plus per-player
per-drill means and test-retest reliability where a drill has >=2 attempts.

Features (per attempt): duration (first movement -> end), peak speed, time to peak,
time to 90% of peak, max accel, max decel, path length, mean speed while moving,
max/p90 lateral accel (s*|omega|) at speed, number of direction reversals,
and (for straight drills) tracking-derived time to 10/20/40 yards of path.

    python -m bdb27.features   # -> data/derived/drill_attempts.parquet, drill_players.parquet, drill_reliability.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl

from . import kinematics as K
from .paths import DERIVED, PQ


def attempt_features(g: pl.DataFrame) -> dict | None:
    if g.height < 10:
        return None
    t = g["time"].dt.epoch("us").to_numpy() / 1e6
    t = t - t[0]
    s = g["s"].to_numpy().astype(float)
    a = g["a"].to_numpy().astype(float)
    dis = g["dis"].to_numpy().astype(float)
    d = g["dir"].to_numpy().astype(float)
    moving = np.where(s > 1.0)[0]
    if len(moving) < 5:
        return None
    i0 = moving[0]
    t0 = t[i0]
    omega = K.turn_rate(d, t)
    ac = np.abs(omega * s)
    fast = s > 3.0
    path = np.cumsum(dis) - np.cumsum(dis)[i0]
    ip = int(np.argmax(s))
    s_peak = s[ip]
    i90 = int(np.argmax(s >= 0.9 * s_peak))
    sign = np.sign(omega) * (np.abs(omega) > 1.0) * fast
    nz = sign[sign != 0]
    reversals = int(np.sum(nz[1:] != nz[:-1])) if nz.size > 1 else 0

    def t_to(dist):
        idx = np.where(path >= dist)[0]
        return float(t[idx[0]] - t0) if idx.size else np.nan

    return {
        "n_frames": int(g.height),
        "duration": float(t[-1] - t0),
        "s_peak": float(s_peak),
        "t_peak": float(t[ip] - t0),
        "t_90pct": float(t[i90] - t0),
        "a_max": float(a[i0:].max()),
        "a_min": float(a[i0:].min()),
        "a_mean_1s": float(a[i0:i0 + 10].mean()),
        "path_yds": float(path[-1]),
        "s_mean_moving": float(s[moving].mean()),
        "lat_ac_max": float(ac[fast].max()) if fast.any() else np.nan,
        "lat_ac_p90": float(np.percentile(ac[fast], 90)) if fast.any() else np.nan,
        "s_min_after_peak": float(s[ip:].min()),
        "reversals": reversals,
        "t_10yd": t_to(10), "t_20yd": t_to(20), "t_40yd": t_to(40),
    }


def main() -> None:
    ct = (
        pl.scan_parquet(PQ / "combine_tracking.parquet")
        .filter(pl.col("entity_type") == "PLAYER")
        .sort("event_id", "time")
        .collect()
    )
    rows = []
    for (ev, nid, yr, drill, name, att), g in ct.group_by(
        ["event_id", "nfl_id", "draft_year", "drill_type", "drill_name", "attempt"], maintain_order=True
    ):
        f = attempt_features(g)
        if f:
            rows.append({"event_id": ev, "nfl_id": nid, "draft_year": yr, "drill_type": drill, "drill_name": name, "attempt": att, **f})
    att = pl.DataFrame(rows)
    # normalise a few name variants
    att = att.with_columns(pl.col("drill_name").str.replace("PASS_PRO-MIRROR", "PASS_PRO_MIRROR").str.replace("OVER_THE_SHOULDER", "OVER_SHOULDER"))
    att.write_parquet(DERIVED / "drill_attempts.parquet")
    feats = [c for c in att.columns if c not in ("event_id", "nfl_id", "draft_year", "drill_type", "drill_name", "attempt", "n_frames")]
    players = att.group_by("nfl_id", "drill_name").agg(pl.len().alias("n_att"), *[pl.col(f).mean() for f in feats])
    players.write_parquet(DERIVED / "drill_players.parquet")

    # test-retest reliability: ICC(1) approx via between/within variance on players with >=2 attempts
    rel = []
    for (dn,), sub in att.group_by(["drill_name"]):
        multi = sub.filter(pl.len().over("nfl_id") >= 2)
        if multi["nfl_id"].n_unique() < 8:
            continue
        for f in feats:
            x = multi.select("nfl_id", f).drop_nulls()
            if x.height < 16:
                continue
            grp = x.group_by("nfl_id").agg(pl.col(f).mean().alias("m"), pl.col(f).var().alias("v"), pl.len().alias("k"))
            within = float(grp["v"].mean()); between = float(grp["m"].var()); kbar = float(grp["k"].mean())
            icc = (between - within / kbar) / (between + within * (1 - 1 / kbar)) if between + within > 0 else np.nan
            rel.append({"drill_name": dn, "feature": f, "players": grp.height, "icc": round(icc, 3)})
    rel = pl.DataFrame(rel).sort("drill_name", "icc", descending=[False, True])
    rel.write_csv(DERIVED / "drill_reliability.csv")
    print(f"attempts: {att.height}, player-drill rows: {players.height}")
    with pl.Config(tbl_rows=60):
        print(rel.filter(pl.col("icc") > 0.5).sort("icc", descending=True).head(60))


if __name__ == "__main__":
    main()
