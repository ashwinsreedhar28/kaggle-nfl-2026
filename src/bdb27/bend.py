"""Bend metrics from the Combine RUN_THE_HOOP drill.

Per attempt we isolate the arc (sustained turning at speed) and measure:
  s_entry          speed entering the arc (yd/s)
  s_min_arc        speed trough inside the arc
  speed_retention  s_min_arc / s_entry  (1.0 = no slowdown through the bend)
  ac_p90, ac_max   centripetal acceleration sustained (yd/s^2) -- "bend load"
  r_fit            least-squares circle radius of the arc path (yd)
  r_eff            1 / mean curvature (yd)
  total_turn_deg   heading change across the arc
  arc_dur          seconds in the arc
  exit_accel       mean `a` over 0.5 s after arc exit (re-acceleration)
  s_peak           peak speed in the attempt

    python -m bdb27.bend            # writes data/derived/bend_attempts.csv, bend_players.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl

from . import kinematics as K
from .paths import DERIVED, PQ

OMEGA_MIN = 1.0   # rad/s (~57 deg/s) -> "turning"
S_MIN = 3.0       # yd/s -> "at speed"
MIN_ARC_FRAMES = 5


def attempt_metrics(df: pl.DataFrame) -> dict | None:
    """df: one attempt's PLAYER frames sorted by time."""
    if df.height < 15:
        return None
    t = df["time"].dt.epoch("us").to_numpy() / 1e6  # unit-safe -> seconds
    t = t - t[0]
    x, y = df["x"].to_numpy(), df["y"].to_numpy()
    s, a = df["s"].to_numpy().astype(float), df["a"].to_numpy().astype(float)
    d = df["dir"].to_numpy().astype(float)

    omega = K.turn_rate(d, t)
    ac = K.centripetal(omega, s)
    kappa = K.curvature(omega, s)

    turning = (np.abs(omega) >= OMEGA_MIN) & (s >= S_MIN)
    i0, i1 = K.longest_run(turning)
    if i1 - i0 < MIN_ARC_FRAMES:
        return None

    cx, cy, r_fit = K.fit_circle(x[i0:i1], y[i0:i1])
    k_mean = np.nanmean(np.abs(kappa[i0:i1]))
    exit_mask = (t > t[i1 - 1]) & (t <= t[i1 - 1] + 0.5)

    return {
        "n_frames": int(df.height),
        "duration": float(t[-1]),
        "s_peak": float(s.max()),
        "arc_start_t": float(t[i0]),
        "arc_dur": float(t[i1 - 1] - t[i0]),
        "arc_frames": int(i1 - i0),
        "s_entry": float(s[i0]),
        "s_min_arc": float(s[i0:i1].min()),
        "s_mean_arc": float(s[i0:i1].mean()),
        "speed_retention": float(s[i0:i1].min() / max(s[i0], 1e-6)),
        "ac_p90": float(np.nanpercentile(np.abs(ac[i0:i1]), 90)),
        "ac_max": float(np.nanmax(np.abs(ac[i0:i1]))),
        "r_fit": r_fit,
        "r_eff": float(1.0 / k_mean) if k_mean > 0 else np.nan,
        "total_turn_deg": float(abs(np.rad2deg(np.trapezoid(omega[i0:i1], t[i0:i1])))),
        "exit_accel": float(a[exit_mask].mean()) if exit_mask.any() else np.nan,
    }


def hoop_attempts() -> pl.DataFrame:
    ct = (
        pl.scan_parquet(PQ / "combine_tracking.parquet")
        .filter((pl.col("entity_type") == "PLAYER") & pl.col("drill_name").str.contains("HOOP"))
        .sort("event_id", "time")
        .collect()
    )
    rows = []
    for (event_id, nfl_id, year, attempt, drill), g in ct.group_by(
        ["event_id", "nfl_id", "draft_year", "attempt", "drill_name"], maintain_order=True
    ):
        m = attempt_metrics(g)
        if m:
            rows.append({"event_id": event_id, "nfl_id": nfl_id, "draft_year": year,
                         "attempt": attempt, "drill_name": drill, **m})
    return pl.DataFrame(rows)


def aggregate_players(att: pl.DataFrame) -> pl.DataFrame:
    metrics = ["s_peak", "s_entry", "s_min_arc", "speed_retention", "ac_p90", "ac_max",
               "r_fit", "r_eff", "total_turn_deg", "exit_accel", "arc_dur"]
    return (
        att.group_by("nfl_id", "draft_year")
        .agg(
            pl.len().alias("n_attempts"),
            *[pl.col(m).mean().alias(f"{m}_mean") for m in metrics],
            *[pl.col(m).std().alias(f"{m}_sd") for m in ("speed_retention", "ac_p90", "r_fit")],
        )
    )


def main() -> None:
    att = hoop_attempts()
    att.write_csv(DERIVED / "bend_attempts.csv")
    players = aggregate_players(att)
    players.write_csv(DERIVED / "bend_players.csv")
    print(f"attempts: {att.height}, players: {players.height}")
    print(att.select("s_entry", "s_min_arc", "speed_retention", "ac_p90", "r_fit", "total_turn_deg").describe())


if __name__ == "__main__":
    main()
