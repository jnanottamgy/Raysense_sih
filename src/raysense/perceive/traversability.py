"""Turn a 2.5D map into a decision: can the vehicle drive here?

The output is **three-valued**, and that is the point. `UNKNOWN` is a first-class
answer, not a gap to be filled in with optimism. There is no code path anywhere
in this module that maps an unobserved cell to `TRAVERSABLE`, and there is a
property test that says so.

Three geometric tests decide the rest, all standard for ground-vehicle
traversability:

* **step height** — how far the cell stands above the local ground
* **slope** — the local height gradient
* **roughness** — the spread of returns that landed in the cell

A cell fails if any one of them fails.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from raysense.mapping import FixedGridMap
from raysense.types import CellState


class Traversability(IntEnum):
    """UNKNOWN is zero, so an unfilled result is never accidentally optimistic."""

    UNKNOWN = 0
    TRAVERSABLE = 1
    BLOCKED = 2


@dataclass(frozen=True)
class TraversabilityConfig:
    """Thresholds, in the units a vehicle engineer would state them in."""

    max_step: float = 0.25        # m — a step taller than this stops the vehicle
    max_slope: float = 0.45       # rise/run, about 24 degrees
    max_roughness: float = 0.09   # m^2 — within-cell height variance
    ground_window: int = 7        # cells — neighbourhood for the local ground estimate


def _window_min(a: np.ndarray, k: int) -> np.ndarray:
    """Minimum over a (2k+1)^2 neighbourhood, ignoring NaN. NumPy only."""
    r = k // 2
    pad = np.pad(a, r, mode="edge")
    out = np.full(a.shape, np.inf)
    ny, nx = a.shape
    for dy in range(k):
        for dx in range(k):
            out = np.fmin(out, pad[dy:dy + ny, dx:dx + nx])
    return out


def _nan_gradient(h: np.ndarray, res: float) -> np.ndarray:
    """Gradient magnitude, using whichever neighbours exist.

    A one-sided difference where the other neighbour is missing, and NaN only
    where neither side is available — so the frontier degrades to "unknown"
    rather than to a fabricated slope.
    """
    def axis_grad(arr, axis):
        fwd = np.full_like(arr, np.nan)
        bwd = np.full_like(arr, np.nan)
        sl_a = [slice(None)] * 2
        sl_b = [slice(None)] * 2
        sl_a[axis] = slice(0, -1)
        sl_b[axis] = slice(1, None)
        diff = (arr[tuple(sl_b)] - arr[tuple(sl_a)]) / res
        fwd[tuple(sl_a)] = diff
        bwd[tuple(sl_b)] = diff
        with warnings.catch_warnings():
            # a cell with neither neighbour observed yields NaN by design
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(np.stack([fwd, bwd]), axis=0)

    with np.errstate(invalid="ignore"):
        gy = axis_grad(h, 0)
        gx = axis_grad(h, 1)
        return np.hypot(np.nan_to_num(gy, nan=0.0), np.nan_to_num(gx, nan=0.0))


def classify(
    emap: FixedGridMap,
    cfg: TraversabilityConfig | None = None,
) -> np.ndarray:
    """Three-valued traversability over the map grid."""
    cfg = cfg or TraversabilityConfig()
    out = np.full(emap.config.shape, int(Traversability.UNKNOWN), dtype=np.int8)

    seen = emap.observed()
    if not seen.any():
        return out

    h = emap.height()
    ground = _window_min(np.where(seen, h, np.nan), cfg.ground_window)
    step = np.where(seen, h - ground, np.nan)
    slope = _nan_gradient(np.where(seen, h, np.nan), emap.config.resolution)
    rough = emap.variance(fill=0.0)

    with np.errstate(invalid="ignore"):
        blocked = (
            (np.nan_to_num(step, nan=0.0) > cfg.max_step)
            | (slope > cfg.max_slope)
            | (rough > cfg.max_roughness)
        )

    out[seen & ~blocked] = int(Traversability.TRAVERSABLE)
    out[seen & blocked] = int(Traversability.BLOCKED)

    # Anything the ray accounting flagged as a possible ditch is not drivable,
    # whatever the heights say — a suspected negative obstacle outranks a
    # comfortable-looking surface. (Set from M4 onward.)
    suspect = (emap.state & int(CellState.CANDIDATE_NEGATIVE)) != 0
    suspect |= (emap.state & int(CellState.CONFIRMED_NEGATIVE)) != 0
    out[suspect] = int(Traversability.BLOCKED)

    return out
