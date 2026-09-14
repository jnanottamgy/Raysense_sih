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

# A crest occlusion produces the same range gap as a ditch: the ground rises,
# the far beam clears the rise, and the shadow behind it reads as an
# unexplained gap. The asymmetry is the approach — a crest is reached *uphill*,
# a ditch is not. `scripts/crest_study.py` measured both populations at a 5%
# budget over 40 frames: the approach slope of a real-ditch gap tops out at
# 0.039, while crest gaps on the ditch-free control start at 0.069. Nothing
# overlaps. The cut sits above the ditch population, not between the two, so
# the bias is toward keeping a ditch rather than dropping one — a missed hole
# is worse than a false alarm.
CREST_RISE = 0.10  # reject a gap approached on a grade steeper than this


def find_discontinuities(
    scan: ScanResult,
    sensor: SensorModel,
    threshold: float = DEFAULT_THRESHOLD,
    min_gap: float = MIN_GAP,
    crest_rise: float = CREST_RISE,
    details: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | tuple[
        np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Locate range gaps that geometry cannot explain.

    Returns `(near, far, ratio)` — the two return points bracketing each
    suspicious gap, and how many times larger it is than predicted.

    With `details=True` a fourth element carries the per-gap geometry the
    crest guard is built on, so the guard and the study that justified it read
    the same numbers from the same code path.
    """
    def _empty(d: bool):
        e = np.zeros((0, 3))
        if not d:
            return e, e, np.zeros(0)
        keys = ("measured", "predicted", "dz", "rise_before", "horiz_near", "have_prev")
        return e, e, np.zeros(0), {k: np.zeros(0) for k in keys}

    if scan.n_returns < 2:
        return _empty(details)

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
        return _empty(details)
    col, el, pts = col[down], el[down], pts[down]

    horiz = np.hypot(pts[:, 0] - o[0], pts[:, 1] - o[1])

    # sort by column, then outward along the ground
    order = np.lexsort((horiz, col))
    col, el, pts, horiz = col[order], el[order], pts[order], horiz[order]

    same = col[1:] == col[:-1]
    if not same.any():
        return _empty(details)

    i = np.flatnonzero(same)          # near return
    j = i + 1                         # far return

    # Ground slope on the approach to the near return, taken from the previous
    # return in the same column. Where there is no previous return we have no
    # evidence, so the crest guard must not fire.
    prev_ok = i > 0
    k = np.where(prev_ok, i - 1, 0)
    run = horiz[i] - horiz[k]
    have_prev = prev_ok & (col[k] == col[i]) & (run > 1e-6)
    rise = np.zeros(i.shape, dtype=float)
    rise[have_prev] = ((pts[i[have_prev], 2] - pts[k[have_prev], 2])
                       / run[have_prev])

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
    if crest_rise > 0:
        flagged &= ~(have_prev & (rise > crest_rise))
    if not details:
        return pts[i[flagged]], pts[j[flagged]], ratio[flagged]

    d = {
        "measured": measured[flagged],
        "predicted": predicted[flagged],
        "dz": (pts[j, 2] - pts[i, 2])[flagged],
        "rise_before": rise[flagged],
        "horiz_near": horiz[i][flagged],
        "have_prev": have_prev[flagged].astype(float),
    }
    return pts[i[flagged]], pts[j[flagged]], ratio[flagged], d


def mark_discontinuities(
    emap: FixedGridMap,
    scan: ScanResult,
    sensor: SensorModel,
    frame: int = 0,
    threshold: float = DEFAULT_THRESHOLD,
    min_gap: float = MIN_GAP,
    crest_rise: float = CREST_RISE,
    trim: float = 0.0,
) -> int:
    """Flag the ground between each unexplained gap as a possible ditch.

    The suspicion attaches to the span the beams skipped over, not to the
    returns themselves — that span is precisely the part of the world no
    measurement covered.
    """
    near, far, _ = find_discontinuities(scan, sensor, threshold, min_gap, crest_rise)
    if not len(near):
        return 0

    res = emap.config.resolution
    seg = far - near
    length = np.linalg.norm(seg[:, :2], axis=1)

    # `trim` metres are left unpainted at each end. Both endpoints are returns,
    # so we *measured* ground there — painting them is guaranteed imprecision.
    # It is off by default: see docs/RESULTS.md, trimming buys precision and
    # costs a little of the zero-missed-unsafe margin.
    # Step count comes from the longest gap *before* any trim filter, so the
    # sampling density does not depend on which gaps survive trimming — one
    # walk is then comparable with another.
    n_steps = int(np.ceil(max(1.0, length.max() / res))) + 1

    if trim > 0.0:
        usable = length > 2.0 * trim + 1e-6
        if not usable.any():
            return 0
        near, seg, length = near[usable], seg[usable], length[usable]
        lo = trim / length
        hi = 1.0 - lo
    else:
        lo = np.zeros(length.shape)
        hi = np.ones(length.shape)

    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    for u in np.linspace(0.0, 1.0, n_steps):
        p = near + seg * (lo + u * (hi - lo))[:, None]
        r, c, inside = emap.world_to_cell(p[:, 0], p[:, 1])
        rows.append(r[inside])
        cols.append(c[inside])

    r = np.concatenate(rows)
    c = np.concatenate(cols)
    emap.state[r, c] |= int(CellState.CANDIDATE_NEGATIVE)
    emap.state[r, c] &= ~int(CellState.FREE)
    emap.last_seen[r, c] = frame
    return int(np.unique(np.stack([r, c]), axis=1).shape[1])


def prune_candidates(emap: FixedGridMap, rim: int = 2) -> int:
    """Drop CANDIDATE_NEGATIVE from cells we have a return from.

    A cell with a return is measured ground, so it cannot be a hole — except
    at the lip of one, where the return sits on the rim of a gap whose interior
    was never seen. `rim` is how many cells of that lip to keep, so the
    suspicion survives exactly where it is doing safety work.

    **Off by default in the shipped pipeline.** It raises candidate precision
    from 79.4% to 84.6% at rim=2, and further with `mark_discontinuities(trim=)`,
    but it moves `negative_missed_unsafe` off zero — the cells it costs are on
    the floor of a broad, shallow crater, which reads as locally flat once
    observed and is held non-drivable only by this flag. Enable it where a
    platform would rather take the misses than the false alarms, and say which
    you chose. Measured curve: `results/localise_study.csv`.

    Returns how many cells were cleared.
    """
    cand = (emap.state & int(CellState.CANDIDATE_NEGATIVE)) != 0
    if not cand.any():
        return 0
    seen = emap.observed()
    core = cand & ~seen                       # the part nobody ever looked at
    lip = core.copy()
    for _ in range(max(0, rim)):
        grown = lip.copy()
        for ax in (0, 1):
            grown |= np.roll(lip, 1, axis=ax) | np.roll(lip, -1, axis=ax)
        lip = grown
    keep = core | (cand & lip & seen)
    drop = cand & ~keep
    emap.state[drop] &= ~int(CellState.CANDIDATE_NEGATIVE)
    return int(drop.sum())
