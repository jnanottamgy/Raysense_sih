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
