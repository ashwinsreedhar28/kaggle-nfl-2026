"""Synthetic figure-eight: approach, loop CCW r=1.2 at 4 yd/s, loop CW r=1.2 at 4 yd/s, sprint out.
Expected: loop_r_fit ~ 1.2, bend_index ~ s^2/r = 13.3 yd/s^2, opposite loop signs.
Run: PYTHONPATH=src python -m pytest -q tests/
"""
from datetime import datetime, timedelta

import numpy as np
import polars as pl

from bdb27.bend import attempt_metrics

DT = 0.1


def _frames(x, y, s, dirs):
    n = len(x)
    t0 = datetime(2025, 3, 2, 18, 0, 0)
    return pl.DataFrame({
        "time": [t0 + timedelta(seconds=DT * i) for i in range(n)],
        "x": x, "y": y, "s": s, "a": np.gradient(np.array(s), DT), "dir": dirs,
    }).with_columns(pl.col("time").cast(pl.Datetime("ms")))


def synthetic_eight(r=1.2, v_loop=4.0):
    pos = np.array([0.0, 0.0]); heading = 0.0  # radians, 0 = +y (NGS convention), clockwise positive
    X, Y, S, D = [], [], [], []

    def step(v, dheading):
        nonlocal pos, heading
        heading += dheading
        pos = pos + v * DT * np.array([np.sin(heading), np.cos(heading)])
        X.append(pos[0]); Y.append(pos[1]); S.append(v); D.append(np.rad2deg(heading) % 360)

    for i in range(12):                      # approach, accelerating
        step(1.0 + 0.3 * i, 0.0)
    w = v_loop / r
    for _ in range(int(1.6 * np.pi / w / DT)):  # loop 1 (CCW: negative yaw)
        step(v_loop, -w * DT)
    for _ in range(4):
        step(v_loop, 0.0)
    for _ in range(int(1.6 * np.pi / w / DT)):  # loop 2 (CW)
        step(v_loop, w * DT)
    for i in range(15):                      # sprint out
        step(min(v_loop + 0.3 * i, 7.5), 0.0)
    return _frames(X, Y, S, D)


def test_figure_eight():
    m = attempt_metrics(synthetic_eight())
    assert m is not None
    assert abs(m["loop_r_fit"] - 1.2) < 0.2, m["loop_r_fit"]
    assert abs(m["bend_index"] - 4.0**2 / 1.2) < 2.0, m["bend_index"]
    assert m["l1_sign"] != m["l2_sign"]
    assert 7.0 < m["exit_s_peak"] <= 7.5
    assert m["asym_s"] < 0.05


def test_rejects_short():
    assert attempt_metrics(synthetic_eight().head(20)) is None
