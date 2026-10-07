"""Frame-level kinematics shared by Combine and in-game tracking.

Conventions (NGS): x along field length (yd), y across (yd), s yd/s, a yd/s^2,
dir = direction of motion in degrees, 0 = +y, clockwise (NGS convention).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter


def unwrap_deg(deg: np.ndarray) -> np.ndarray:
    return np.rad2deg(np.unwrap(np.deg2rad(deg)))


def smooth(x: np.ndarray, window: int = 7, poly: int = 2) -> np.ndarray:
    n = len(x)
    if n < 5:
        return x
    w = min(window, n if n % 2 == 1 else n - 1)
    if w <= poly:
        return x
    return savgol_filter(x, w, poly)


def heading_from_xy(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Fallback heading (deg, unwrapped) from displacement when `dir` is noisy."""
    dx, dy = np.gradient(x), np.gradient(y)
    return unwrap_deg(np.rad2deg(np.arctan2(dx, dy)) % 360.0)


def turn_rate(dir_deg: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Signed yaw rate omega in rad/s from the NGS `dir` column."""
    h = np.deg2rad(unwrap_deg(dir_deg))
    h = smooth(h)
    return np.gradient(h, t)


def curvature(omega: np.ndarray, s: np.ndarray, s_floor: float = 1.0) -> np.ndarray:
    """kappa = omega / s  (1/yd). Undefined when nearly stationary."""
    s_safe = np.where(s < s_floor, np.nan, s)
    return omega / s_safe


def centripetal(omega: np.ndarray, s: np.ndarray) -> np.ndarray:
    """a_c = s * omega  (yd/s^2). This is the 'bend load' a player sustains."""
    return s * omega


def fit_circle(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Algebraic (Kasa) least-squares circle fit. Returns (cx, cy, r)."""
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x**2 + y**2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(max(sol[2] + cx**2 + cy**2, 0.0))
    return float(cx), float(cy), float(r)


def longest_run(mask: np.ndarray) -> tuple[int, int]:
    """Start (inclusive) and end (exclusive) of the longest True run. (0,0) if none."""
    best = (0, 0)
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        else:
            i += 1
    return best
