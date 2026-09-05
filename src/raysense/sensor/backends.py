"""Sensor backends — the three answers to "which lidar does this run on?".

Only `ReplayBackend` exists at M2, because it is the one the evaluation harness
needs. The other two are stated in the build plan and slot in behind the same
`acquire` signature:

* **steerable** (MEMS/OPA) — emits only the budgeted rays; a saved ray is a
  laser pulse not fired.
* **fixed-pattern** (spinning) — every ray fires regardless; the budget selects
  what is *processed*, saving bandwidth, memory and compute but not laser
  energy. Being honest about that distinction is what keeps the SWaP claim
  defensible.
"""

from __future__ import annotations

import numpy as np

from raysense.types import RayBudget, ScanResult


class ReplayBackend:
    """Sample a recorded full scan down to a budget.

    The full scan is ground truth; the budget decides which of its rays the
    system would have acquired. Crucially, budgeted rays that returned nothing
    are carried through as fired-and-empty rather than dropped — otherwise the
    replay would destroy exactly the evidence the project is about.
    """

    name = "replay"

    def __init__(self, full: ScanResult) -> None:
        self.full = full
        native = full.fired.beam_index
        if native is None:
            raise ValueError("replay needs `fired.beam_index` to address rays by native index")

        n_native = int(native.max()) + 1
        # native ray id -> its position in `full.fired`
        self._pos_of_native = np.full(n_native, -1, dtype=np.int64)
        self._pos_of_native[native] = np.arange(native.size)
        # position in `full.fired` -> its point in `full.points`
        self._point_of_pos = np.full(native.size, -1, dtype=np.int64)
        self._point_of_pos[full.ray_index] = np.arange(full.n_returns)

    def acquire(self, budget: RayBudget) -> ScanResult:
        pos = self._pos_of_native[budget.ray_indices]
        pos = pos[pos >= 0]                       # rays the recording never fired

        fired = self.full.fired.select(pos)
        pt = self._point_of_pos[pos]
        got = pt >= 0
        return ScanResult(
            points=self.full.points[pt[got]],
            ray_index=np.flatnonzero(got),
            fired=fired,
        )
