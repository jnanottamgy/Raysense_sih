"""Baseline allocators.

These are not straw men. `UniformDecimation` is what a competent engineer does
first, and it is the honest comparison: same sensor, same budget, no state, no
cleverness. If our allocator cannot beat it, that is a result to report rather
than to hide.
"""

from __future__ import annotations

import numpy as np

from raysense.allocate.base import WorldState
from raysense.types import RayBudget


class FullScan:
    """Every ray. The quality ceiling and the source of ground truth."""

    name = "full"

    def allocate(self, world: WorldState, budget: int) -> RayBudget:
        n = world.sensor.n_rays
        return RayBudget(np.arange(n), n_native=n)


class UniformDecimation:
    """Every k-th beam by every j-th column.

    Strides are split between the two axes rather than loaded onto one, so the
    angular pattern is thinned evenly and the baseline keeps a sensible sensor
    geometry instead of degenerating into a comb.
    """

    name = "uniform"

    def allocate(self, world: WorldState, budget: int) -> RayBudget:
        s = world.sensor
        n = s.n_rays
        if budget >= n:
            return RayBudget(np.arange(n), n_native=n)
        budget = max(1, budget)

        total_stride = n / budget
        kb = max(1, int(round(np.sqrt(total_stride))))
        kb = min(kb, s.n_beams)
        kc = max(1, int(np.ceil(total_stride / kb)))

        beams = np.arange(0, s.n_beams, kb)
        cols = np.arange(0, s.n_azimuth, kc)
        idx = (beams[:, None] * s.n_azimuth + cols[None, :]).ravel()
        return RayBudget(np.sort(idx), n_native=n)


class RandomSubsample:
    """A seeded random subset — the null hypothesis for "where to look".

    Scheduled for M3, pulled forward because it costs nothing and turns the
    first curve from a single line into an actual comparison.
    """

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def allocate(self, world: WorldState, budget: int) -> RayBudget:
        n = world.sensor.n_rays
        k = int(np.clip(budget, 1, n))
        return RayBudget(np.sort(self._rng.choice(n, size=k, replace=False)), n_native=n)


class StaticFrontROI:
    """A fixed dense wedge ahead, the remainder spread thinly elsewhere.

    This is the baseline that matters. It is what a competent engineer proposes
    in the first five minutes — "just look where you're going" — it is free, it
    has no state, and a judge *will* raise it. Beating uniform decimation proves
    very little; beating this is the result.
    """

    name = "front_roi"

    def __init__(self, half_angle_deg: float = 30.0, front_share: float = 0.8) -> None:
        self.half_angle_deg = half_angle_deg
        self.front_share = front_share

    def allocate(self, world: WorldState, budget: int) -> RayBudget:
        s = world.sensor
        n = s.n_rays
        if budget >= n:
            return RayBudget(np.arange(n), n_native=n)
        budget = max(1, budget)

        col = np.arange(s.n_azimuth)
        az = np.rad2deg(
            np.linspace(np.deg2rad(s.az_min_deg), np.deg2rad(s.az_max_deg),
                        s.n_azimuth, endpoint=False)
        )
        # forward is azimuth 0, wrapped onto (-180, 180]
        ahead = np.abs((az + 180.0) % 360.0 - 180.0) <= self.half_angle_deg
        front_cols, rest_cols = col[ahead], col[~ahead]

        n_front = int(round(budget * self.front_share))
        n_rest = budget - n_front

        def spread(cols: np.ndarray, want: int) -> np.ndarray:
            """Take `want` rays from these columns, thinning both axes evenly."""
            if want <= 0 or cols.size == 0:
                return np.empty(0, dtype=np.int64)
            avail = cols.size * s.n_beams
            stride = max(1.0, avail / want)
            kb = max(1, min(s.n_beams, int(round(np.sqrt(stride)))))
            kc = max(1, int(np.ceil(stride / kb)))
            beams = np.arange(0, s.n_beams, kb)
            take = cols[::kc]
            return (beams[:, None] * s.n_azimuth + take[None, :]).ravel()

        idx = np.concatenate([spread(front_cols, n_front), spread(rest_cols, n_rest)])
        return RayBudget(np.unique(idx), n_native=n)
