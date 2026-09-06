"""Signature B — a ditch that was stepped over rather than fallen into.

M4 established that the obvious absence test (a ray fired at the ground that
comes back with nothing) fires on almost none of the ditches that matter. A
narrow trench is not entered by beams; it is **stepped over**. Every ray returns
normally, before it and beyond it, and nothing looks wrong ray by ray.

What is wrong is the *spacing*. Two adjacent beams that both return will land a
predictable distance apart on flat ground. If the far one lands much further out
than that, the surface between them dropped away.

The prediction has to be local and geometric, not a global threshold, because
ground spacing grows quadratically with range — the M0 result. So for adjacent
rays `i` and `i+1`, we take the ground height established by return `i`, ask
where ray `i+1` would strike a level plane at that height, and compare:

    x_pred  = x_i + (z_sensor - z_i) * (1/tan(-el_{i+1}) - 1/tan(-el_i))
    anomaly = (x_meas - x_i) / (x_pred - x_i)

Flat and rolling terrain both sit near 1.0. A trench sends it to 6-9x. Being
local, it needs no assumption about the world beyond the two beams involved —
and it costs one sort and one diff per azimuth column, rather than a ray march.
"""

from __future__ import annotations

import numpy as np

from raysense.mapping import FixedGridMap
from raysense.sensor import SensorModel
from raysense.types import CellState, ScanResult

# Chosen by sweep, not by eye — see scripts/threshold_sweep.py and
# results/threshold_sweep.csv. Scored against the identical terrain with the
# ditches removed, which is the only honest control:
#
#   2.0  ->  94.0% ditch recall,  3,883 false cells,  45.6% precision
#   3.0  ->  88.0% ditch recall,    436 false cells,  73.3% precision   <- knee
#   4.0  ->  82.6% ditch recall,    249 false cells,  82.7% precision
#
# Moving 2.0 -> 3.0 costs six points of recall and removes 89% of the false
# flags. Going further costs another five points for far less, so 3.0 is where
# the curve turns.
DEFAULT_THRESHOLD = 3.0
MIN_GAP = 0.5      # m — ignore gaps too small to hide anything a vehicle cares about


def find_discontinuities(
    scan: ScanResult,
    sensor: SensorModel,
    threshold: float = DEFAULT_THRESHOLD,
    min_gap: float = MIN_GAP,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Locate range gaps that geometry cannot explain.

    Returns `(near, far, ratio)` — the two return points bracketing each
    suspicious gap, and how many times larger it is than predicted.
    """
    if scan.n_returns < 2:
        empty = np.zeros((0, 3))
        return empty, empty, np.zeros(0)

    o = np.asarray(scan.fired.origin, dtype=float)
    native = scan.fired.beam_index
    if native is None:
        raise ValueError("discontinuity search needs `fired.beam_index`")

    ret_native = native[scan.ray_index]
    col = sensor.column_of(ret_native)
    el = scan.fired.elevation[scan.ray_index]
    pts = scan.points

    # only downward beams describe ground
    down = el < -1e-3
    if down.sum() < 2:
        empty = np.zeros((0, 3))
        return empty, empty, np.zeros(0)
    col, el, pts = col[down], el[down], pts[down]

    horiz = np.hypot(pts[:, 0] - o[0], pts[:, 1] - o[1])

    # sort by column, then outward along the ground
    order = np.lexsort((horiz, col))
    col, el, pts, horiz = col[order], el[order], pts[order], horiz[order]

    same = col[1:] == col[:-1]
    if not same.any():
        empty = np.zeros((0, 3))
        return empty, empty, np.zeros(0)

    i = np.flatnonzero(same)          # near return
    j = i + 1                         # far return

    # where would the far beam land on a level plane through the near return?
    drop = o[2] - pts[i, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        cot_near = 1.0 / np.tan(-el[i])
        cot_far = 1.0 / np.tan(-el[j])
        predicted = drop * (cot_far - cot_near)

    measured = horiz[j] - horiz[i]
    ok = np.isfinite(predicted) & (predicted > 1e-3) & (measured > min_gap)
    ratio = np.full(i.shape, 1.0)
    ratio[ok] = measured[ok] / predicted[ok]

    flagged = ok & (ratio > threshold)
    return pts[i[flagged]], pts[j[flagged]], ratio[flagged]


def mark_discontinuities(
    emap: FixedGridMap,
    scan: ScanResult,
    sensor: SensorModel,
    frame: int = 0,
    threshold: float = DEFAULT_THRESHOLD,
    min_gap: float = MIN_GAP,
) -> int:
    """Flag the ground between each unexplained gap as a possible ditch.

    The suspicion attaches to the span the beams skipped over, not to the
    returns themselves — that span is precisely the part of the world no
    measurement covered.
    """
    near, far, _ = find_discontinuities(scan, sensor, threshold, min_gap)
    if not len(near):
        return 0

    res = emap.config.resolution
    seg = far - near
    length = np.linalg.norm(seg[:, :2], axis=1)
    n_steps = int(np.ceil(max(1.0, length.max() / res))) + 1

    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    for s in np.linspace(0.0, 1.0, n_steps):
        p = near + seg * s
        r, c, inside = emap.world_to_cell(p[:, 0], p[:, 1])
        rows.append(r[inside])
        cols.append(c[inside])

    r = np.concatenate(rows)
    c = np.concatenate(cols)
    emap.state[r, c] |= int(CellState.CANDIDATE_NEGATIVE)
    emap.state[r, c] &= ~int(CellState.FREE)
    emap.last_seen[r, c] = frame
    return int(np.unique(np.stack([r, c]), axis=1).shape[1])
