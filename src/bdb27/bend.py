"""Bend metrics from the Combine RUN_THE_HOOP_DRILL (DL/EDGE).

Drill layout (verified on 2023-25 tracking, reports/figures/hoop_paths_sample.png):
approach -> figure-eight around two hoops (loop radius ~1-1.3 yd, opposite turn
directions) -> ~6 yd sprint out. 1 attempt per player (119 attempts / 109 players).

Per attempt we segment the two loops as the two largest sign-consistent turning
runs and measure, per loop and combined:
  loop_s_mean / loop_s_min   speed carried through the hoop (yd/s)
  loop ac_med / ac_mean      centripetal accel s*omega = s^2/r (yd/s^2) -- "bend load"
  loop_r_fit                 least-squares circle radius of the loop path (yd)
  loop_dur, loop_turn_deg    time and heading change in the loop
  asym_s                     |loop1_s_mean - loop2_s_mean| / mean  (one-directional benders)
  exit_s_peak, exit_accel    peak speed and mean accel in the sprint-out
  move_time                  seconds from first movement (s>1) to last frame
  bend_index                 median centripetal accel, averaged over both loops (primary metric)

    python -m bdb27.bend   # -> data/derived/bend_attempts.csv, bend_players.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl

from . import kinematics as K
from .paths import DERIVED, PQ

OMEGA_MIN = 0.6     # rad/s: in a loop the yaw rate is ~2-3 rad/s
MIN_LOOP_FRAMES = 6
MIN_LOOP_TURN = 120.0  # deg; a real hoop loop is ~250-330 deg


def _turn_runs(omega: np.ndarray, t: np.ndarray) -> list[tuple[int, int, float]]:
    """Sign-consistent runs with |omega| >= OMEGA_MIN -> [(i0, i1, turn_deg)]."""
    sign = np.sign(omega) * (np.abs(omega) >= OMEGA_MIN)
    runs, i, n = [], 0, len(omega)
    while i < n:
        if sign[i] == 0:
            i += 1
            continue
        j = i
        while j < n and sign[j] == sign[i]:
            j += 1
        if j - i >= MIN_LOOP_FRAMES:
            turn = abs(np.rad2deg(np.trapezoid(omega[i:j], t[i:j])))
            runs.append((i, j, float(turn)))
        i = j
    return runs


def _loop_stats(i0, i1, t, x, y, s, omega) -> dict:
    ac = np.abs(K.centripetal(omega[i0:i1], s[i0:i1]))
    _, _, r = K.fit_circle(x[i0:i1], y[i0:i1])
    return {
        "s_mean": float(s[i0:i1].mean()),
        "s_min": float(s[i0:i1].min()),
        "ac_mean": float(ac.mean()),
        "ac_med": float(np.median(ac)),
        "ac_p90": float(np.percentile(ac, 90)),
        "r_fit": r,
        "dur": float(t[i1 - 1] - t[i0]),
        "turn_deg": float(abs(np.rad2deg(np.trapezoid(omega[i0:i1], t[i0:i1])))),
        "sign": float(np.sign(omega[i0:i1].mean())),
    }


def attempt_metrics(df: pl.DataFrame) -> dict | None:
    """df: one attempt's PLAYER frames sorted by time."""
    if df.height < 30:
        return None
    t = df["time"].dt.epoch("us").to_numpy() / 1e6
    t = t - t[0]
    x, y = df["x"].to_numpy().astype(float), df["y"].to_numpy().astype(float)
    s, a = df["s"].to_numpy().astype(float), df["a"].to_numpy().astype(float)
    omega = K.turn_rate(df["dir"].to_numpy().astype(float), t)

    runs = [r for r in _turn_runs(omega, t) if r[2] >= MIN_LOOP_TURN]
    if len(runs) < 2:
        return None
    runs = sorted(sorted(runs, key=lambda r: -r[2])[:2])  # two biggest, in time order
    (a0, a1, _), (b0, b1, _) = runs
    L1, L2 = _loop_stats(a0, a1, t, x, y, s, omega), _loop_stats(b0, b1, t, x, y, s, omega)
    if L1["sign"] == L2["sign"]:
        return None  # not a figure-eight; flag by returning None

    moving = np.where(s > 1.0)[0]
    t_start = t[moving[0]] if len(moving) else t[0]
    exit_sl = slice(b1, len(t))
    exit_s = s[exit_sl]
    out = {
        "n_frames": int(df.height),
        "move_time": float(t[-1] - t_start),
        "approach_s_peak": float(s[:a0].max()) if a0 > 0 else np.nan,
        "loop_gap_s": float(s[a1:b0].mean()) if b0 > a1 else np.nan,
        "exit_s_peak": float(exit_s.max()) if exit_s.size else np.nan,
        "exit_accel": float(a[exit_sl].mean()) if exit_s.size else np.nan,
        "exit_dur": float(t[-1] - t[b1 - 1]),
    }
    for k, L in (("l1", L1), ("l2", L2)):
        out.update({f"{k}_{m}": v for m, v in L.items()})
    out["loop_s_mean"] = (L1["s_mean"] + L2["s_mean"]) / 2
    out["loop_s_min"] = min(L1["s_min"], L2["s_min"])
    out["loop_r_fit"] = (L1["r_fit"] + L2["r_fit"]) / 2
    out["loop_dur"] = L1["dur"] + L2["dur"]
    out["bend_index"] = (L1["ac_med"] + L2["ac_med"]) / 2
    out["asym_s"] = abs(L1["s_mean"] - L2["s_mean"]) / out["loop_s_mean"]
    return out


def hoop_attempts() -> tuple[pl.DataFrame, list]:
    ct = (
        pl.scan_parquet(PQ / "combine_tracking.parquet")
        .filter((pl.col("entity_type") == "PLAYER") & pl.col("drill_name").str.contains("HOOP"))
        .sort("event_id", "time")
        .collect()
    )
    rows, failed = [], []
    for (event_id, nfl_id, year, attempt), g in ct.group_by(
        ["event_id", "nfl_id", "draft_year", "attempt"], maintain_order=True
    ):
        m = attempt_metrics(g)
        if m:
            rows.append({"event_id": event_id, "nfl_id": nfl_id, "draft_year": year, "attempt": attempt, **m})
        else:
            failed.append((event_id, nfl_id, year, g.height))
    return pl.DataFrame(rows), failed


def aggregate_players(att: pl.DataFrame) -> pl.DataFrame:
    metrics = [c for c in att.columns if c not in ("event_id", "nfl_id", "draft_year", "attempt", "n_frames")]
    return (
        att.group_by("nfl_id", "draft_year")
        .agg(pl.len().alias("n_attempts"), *[pl.col(m).mean().alias(m) for m in metrics])
    )


def main() -> None:
    att, failed = hoop_attempts()
    att.write_csv(DERIVED / "bend_attempts.csv")
    players = aggregate_players(att)
    players.write_csv(DERIVED / "bend_players.csv")
    print(f"attempts parsed: {att.height}, failed: {len(failed)}, players: {players.height}")
    for f in failed:
        print("  failed:", f)
    cols = ["move_time", "loop_s_mean", "loop_s_min", "loop_r_fit", "bend_index", "asym_s", "exit_s_peak", "l1_turn_deg", "l2_turn_deg"]
    with pl.Config(tbl_cols=12, float_precision=2):
        print(att.select(cols).describe())


if __name__ == "__main__":
    main()
