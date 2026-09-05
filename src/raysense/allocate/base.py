"""The allocator contract.

One protocol, and every strategy in the project satisfies it — the baselines
and our own method alike. That is deliberate: if a baseline ever needs
special-casing inside the pipeline, the abstraction is wrong and the
comparison is no longer honest.

An allocator sees only `WorldState`. It cannot peek at the full scan it is
about to sample, because a real sensor cannot either.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from raysense.mapping import FixedGridMap
from raysense.sensor import SensorModel
from raysense.types import RayBudget


@dataclass(frozen=True)
class WorldState:
    """Everything an allocator is allowed to know before it decides.

    Note what is absent: the scan for this frame. Allocation happens *before*
    acquisition, from the previous frame's map plus ego-motion — a single pass,
    with no sparse-then-rescan round trip.
    """

    sensor: SensorModel
    frame: int
    origin: np.ndarray                  # sensor world position
    emap: FixedGridMap | None = None    # the map as of the previous frame
    speed: float = 0.0                  # m/s, for the braking corridor at M5


@runtime_checkable
class Allocator(Protocol):
    name: str

    def allocate(self, world: WorldState, budget: int) -> RayBudget: ...
