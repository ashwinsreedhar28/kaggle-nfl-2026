"""Synthetic hoop run: straight 10 yd at 7 yd/s, semicircle r=3 yd at 6 yd/s, straight out.
Checks the arc detector and that r_fit ~ 3 and a_c ~ s^2/r = 12 yd/s^2.
Run: python -m pytest -q tests/
"""
import numpy as np
import polars as pl
from datetime import datetime, timedelta

from bdb27.bend import attempt_metrics


def synthetic_attempt(r=3.0, v_arc=6.0, v_straight=7.0, dt=0.1):
    xs, ys, ss, dirs = [], [], [], []
    # straight along +x
    for i in range(int(10 / (v_straight * dt))):
        xs.append(i * v_straight * dt); ys.append(0.0); ss.append(v_straight); dirs.append(90.0)
    x0 = xs[-1]
    omega = v_arc / r
    n_arc = int(np.pi / omega / dt)
    for i in range(1, n_arc + 1):
        th = omega * dt * i
        xs.append(x0 + r * np.sin(th)); ys.append(r - r * np.cos(th)); ss.append(v_arc)
        dirs.append((90.0 - np.rad2deg(th)) % 360)  # heading rotates from +x toward -x
    x1, y1 = xs[-1], ys[-1]
    for i in range(1, 15):
        xs.append(x1 - i * v_straight * dt); ys.append(y1); ss.append(v_straight); dirs.append(270.0)
    n = len(xs)
    t0 = datetime(2025, 3, 2, 18, 0, 0)
    return pl.DataFrame({
        "time": [t0 + timedelta(seconds=dt * i) for i in range(n)],
        "x": xs, "y": ys, "s": ss,
        "a": np.gradient(np.array(ss), dt),
        "dir": dirs,
    }).with_columns(pl.col("time").cast(pl.Datetime("us")))


def test_arc_geometry():
    m = attempt_metrics(synthetic_attempt())
    assert m is not None
    assert abs(m["r_fit"] - 3.0) < 0.3, m["r_fit"]
    assert abs(m["ac_p90"] - 12.0) < 2.0, m["ac_p90"]
    assert 150 < m["total_turn_deg"] < 200, m["total_turn_deg"]
    assert abs(m["s_min_arc"] - 6.0) < 0.3


def test_short_attempt_rejected():
    assert attempt_metrics(synthetic_attempt().head(10)) is None
