"""Bend metrics from the Combine RUN_THE_HOOP_DRILL (DL/EDGE).

Drill layout (verified on 2023-25 tracking, reports/figures/hoop_paths_sample.png):
approach -> figure-eight around two hoops (loop radius ~1-1.3 yd, opposite turn
directions) -> ~6 yd sprint out. 1 attempt per player (119 attempts / 109 players).

Path = arc A around hoop 1 (~-100 deg) -> full loop B around hoop 2 (~+250 deg)
-> arc C back around hoop 1 (~-120 deg) -> sprint out. Per attempt, per segment
(arcA, loopB, arcC, hoop1 = A+C, all = A+B+C):
  *_s_mean / *_s_min        speed carried through the arc (yd/s)
  *_ac_med / *_ac_mean      centripetal accel s*omega = s^2/r (yd/s^2) -- "bend load"
  *_r_fit                   least-squares circle radius of the arc path (yd)
  *_dur, *_turn_deg         time and heading change in the arc
plus:
  bend_index                median centripetal accel over all turning frames (primary)
  bend_s_mean, bend_dur     speed and time while turning
  asym_s                    (hoop1 speed - hoop2 speed) / mean  (direction asymmetry)
  exit_s_peak, exit_accel   sprint-out burst after the last arc
  move_time                 seconds from first movement (s>1) to last frame

    python -m bdb27.bend   # -> data/derived/bend_attempts.csv, bend_players.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl

from . import kinematics as K
from .paths import DERIVED, PQ

OMEGA_MIN = 0.6      # rad/s: in a hoop arc the yaw rate is ~1.5-3 rad/s
S_MIN = 1.5          # yd/s: ignore heading noise while nearly stationary
MIN_RUN_FRAMES = 5
MIN_RUN_TURN = 45.0  # deg; hoop-1 arcs are ~70-120 deg, hoop-2 loop ~220-260 deg


def _turn_runs(omega: np.ndarray, s: np.ndarray, t: np.ndarray) -> list[tuple[int, int, float]]:
    """Sign-consistent runs with |omega| >= OMEGA_MIN and s >= S_MIN -> [(i0, i1, turn_deg)]."""
    sign = np.sign(omega) * ((np.abs(omega) >= OMEGA_MIN) & (s >= S_MIN))
    runs, i, n = [], 0, len(omega)
    while i < n:
        if sign[i] == 0:
            i += 1
            continue
        j = i
        while j < n and sign[j] == sign[i]:
            j += 1
        if j - i >= MIN_RUN_FRAMES:
            turn = abs(np.rad2deg(np.trapezoid(omega[i:j], t[i:j])))
            if turn >= MIN_RUN_TURN:
                runs.append((i, j, float(turn)))
        i = j
    return runs


def _arc_stats(idx: np.ndarray, t, x, y, s, omega) -> dict:
    ac = np.abs(K.centripetal(omega[idx], s[idx]))
    _, _, r = K.fit_circle(x[idx], y[idx])
    return {
        "s_mean": float(s[idx].mean()),
        "s_min": float(s[idx].min()),
        "ac_mean": float(ac.mean()),
        "ac_med": float(np.median(ac)),
        "ac_p90": float(np.percentile(ac, 90)),
        "r_fit": r,
        "dur": float(len(idx) * 0.1),
        "turn_deg": float(abs(np.rad2deg(np.trapezoid(omega[idx], t[idx])))),
    }


def attempt_metrics(df: pl.DataFrame) -> dict | None:
    """df: one attempt's PLAYER frames sorted by time.

    Segmentation: the three largest alternating-sign turning runs, in time order,
    are arc A (hoop 1, in), loop B (hoop 2, full), arc C (hoop 1, out).
    """
    if df.height < 30:
        return None
    t = df["time"].dt.epoch("us").to_numpy() / 1e6
    t = t - t[0]
    x, y = df["x"].to_numpy().astype(float), df["y"].to_numpy().astype(float)
    s, a = df["s"].to_numpy().astype(float), df["a"].to_numpy().astype(float)
    omega = K.turn_rate(df["dir"].to_numpy().astype(float), t)

    runs = _turn_runs(omega, s, t)
    if len(runs) < 3:
        return None
    runs = sorted(sorted(runs, key=lambda r: -r[2])[:3])
    (a0, a1, _), (b0, b1, _), (c0, c1, _) = runs
    sA, sB, sC = (np.sign(omega[i:j].mean()) for i, j in ((a0, a1), (b0, b1), (c0, c1)))
    if not (sA == sC and sA != sB):
        return None

    A = _arc_stats(np.arange(a0, a1), t, x, y, s, omega)
    B = _arc_stats(np.arange(b0, b1), t, x, y, s, omega)
    C = _arc_stats(np.arange(c0, c1), t, x, y, s, omega)
    H1 = _arc_stats(np.r_[a0:a1, c0:c1], t, x, y, s, omega)  # hoop 1 = A + C
    ALL = _arc_stats(np.r_[a0:a1, b0:b1, c0:c1], t, x, y, s, omega)

    moving = np.where(s > 1.0)[0]
    t_start = t[moving[0]] if len(moving) else t[0]
    exit_sl = slice(c1, len(t))
    out = {
        "n_frames": int(df.height),
        "move_time": float(t[-1] - t_start),
        "t_to_first_arc": float(t[a0] - t_start),
        "approach_s_peak": float(s[:a0].max()) if a0 > 0 else np.nan,
        "exit_s_peak": float(s[exit_sl].max()) if c1 < len(t) else np.nan,
        "exit_accel": float(a[exit_sl].mean()) if c1 < len(t) else np.nan,
        "exit_dur": float(t[-1] - t[c1 - 1]),
        "turn_sign_first": float(sA),
    }
    for k, D in (("arcA", A), ("loopB", B), ("arcC", C), ("hoop1", H1), ("all", ALL)):
        out.update({f"{k}_{m}": v for m, v in D.items()})
    out["bend_index"] = ALL["ac_med"]
    out["bend_s_mean"] = ALL["s_mean"]
    out["bend_dur"] = ALL["dur"]
    out["asym_s"] = (H1["s_mean"] - B["s_mean"]) / ALL["s_mean"]  # + = faster around hoop 1
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
    cols = ["move_time", "bend_index", "bend_s_mean", "bend_dur", "asym_s", "exit_s_peak", "arcA_turn_deg", "loopB_turn_deg", "arcC_turn_deg", "loopB_r_fit"]
    with pl.Config(tbl_cols=12, float_precision=2):
        print(att.select(cols).describe())


if __name__ == "__main__":
    main()
