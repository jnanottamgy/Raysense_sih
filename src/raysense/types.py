"""Core data contract for Raysense.

The single most important idea in this project lives in `ScanResult`: a lidar
scan is not just a bag of returned points. It is a set of rays that were
*fired*, some of which came back and some of which did not.

Three situations must stay distinguishable, forever:

  1. a ray was fired and returned          -> we know what is there
  2. a ray was fired and returned nothing  -> something is different from
                                              expectation (possibly a ditch)
  3. no ray was ever fired in that
     direction                             -> we know nothing at all

Ordinary point-cloud code collapses (2) and (3) by discarding non-returns.
For adaptive sampling over off-road terrain that collapse is exactly the
failure mode we exist to prevent, so the distinction is encoded here in the
type rather than left to convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag

import numpy as np


class CellState(IntFlag):
    """Per-cell knowledge state of the 2.5D map.

    UNKNOWN is deliberately zero so a freshly allocated array starts out
    honest: nothing is known until a ray demonstrably says otherwise.
    """

    UNKNOWN = 0
    FREE = 1 << 0               # a ray passed through and returned from beyond
    SURFACE = 1 << 1            # a return landed here, consistent with ground
    OBSTACLE = 1 << 2           # a return landed here, above the local ground
    SHADOW = 1 << 3             # occluded behind a return; not free, not unknown
    CANDIDATE_NEGATIVE = 1 << 4  # fired, no return, where ground was expected
    CONFIRMED_NEGATIVE = 1 << 5  # candidate corroborated (e.g. far-wall signature)

    @staticmethod
    def is_observed(state: np.ndarray) -> np.ndarray:
        """True where anything at all has been established about the cell."""
        return state != CellState.UNKNOWN


@dataclass(frozen=True)
class RayGrid:
    """The rays a sensor actually emitted for one frame.

    Directions are in the sensor frame: azimuth measured counter-clockwise
    about +Z from the +X axis, elevation positive upward from the XY plane.

    `beam_index` records which row of the sensor's native beam grid each ray
    came from, so a subset can always be related back to the full pattern.
    """

    azimuth: np.ndarray       # (M,) radians
    elevation: np.ndarray     # (M,) radians
    origin: np.ndarray        # (3,) sensor origin, sensor frame
    max_range: float
    beam_index: np.ndarray | None = None   # (M,) int, index into the native grid

    def __post_init__(self) -> None:
        if self.azimuth.shape != self.elevation.shape:
            raise ValueError(
                f"azimuth {self.azimuth.shape} and elevation "
                f"{self.elevation.shape} must have the same shape"
            )
        if self.azimuth.ndim != 1:
            raise ValueError(f"ray arrays must be 1-D, got {self.azimuth.ndim}-D")
        if self.origin.shape != (3,):
            raise ValueError(f"origin must be shape (3,), got {self.origin.shape}")
        if self.beam_index is not None and self.beam_index.shape != self.azimuth.shape:
            raise ValueError("beam_index must match the ray arrays in shape")

    def __len__(self) -> int:
        return int(self.azimuth.shape[0])

    @property
    def n_rays(self) -> int:
        return len(self)

    def directions(self) -> np.ndarray:
        """(M, 3) unit direction vectors in the sensor frame."""
        ce = np.cos(self.elevation)
        return np.stack(
            [ce * np.cos(self.azimuth), ce * np.sin(self.azimuth), np.sin(self.elevation)],
            axis=-1,
        )

    def select(self, idx: np.ndarray) -> RayGrid:
        """A sub-grid containing only the rays at `idx`."""
        return RayGrid(
            azimuth=self.azimuth[idx],
            elevation=self.elevation[idx],
            origin=self.origin,
            max_range=self.max_range,
            beam_index=None if self.beam_index is None else self.beam_index[idx],
        )


@dataclass(frozen=True)
class ScanResult:
    """One frame of sensing: what was fired, and what came back.

    `points` holds only the returns. `fired` holds every ray emitted, whether
    it returned or not. `ray_index[i]` is the index into `fired` that produced
    `points[i]`, which is what makes non-returns recoverable rather than
    merely absent.

    Frame convention: `points` and `fired.origin` are always in the *same*
    coordinate system, and the map consumes them as world coordinates. The
    simulator produces these directly; a recorded dataset is transformed by its
    pose on load. Subtracting `fired.origin` therefore always gives the
    sensor-relative vector, whatever the source.
    """

    points: np.ndarray        # (N, 3) return positions, sensor frame
    ray_index: np.ndarray     # (N,) index into `fired`
    fired: RayGrid
    intensity: np.ndarray | None = None   # (N,) optional return strength

    def __post_init__(self) -> None:
        n = self.points.shape[0]
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"points must be (N, 3), got {self.points.shape}")
        if self.ray_index.shape != (n,):
            raise ValueError(f"ray_index must be ({n},), got {self.ray_index.shape}")
        if n > self.fired.n_rays:
            raise ValueError(
                f"{n} returns from only {self.fired.n_rays} fired rays: "
                "a ray cannot return more than once"
            )
        if n and (self.ray_index.min() < 0 or self.ray_index.max() >= self.fired.n_rays):
            raise ValueError("ray_index contains indices outside `fired`")
        if self.intensity is not None and self.intensity.shape != (n,):
            raise ValueError(f"intensity must be ({n},), got {self.intensity.shape}")

    @property
    def n_returns(self) -> int:
        return int(self.points.shape[0])

    @property
    def n_fired(self) -> int:
        return self.fired.n_rays

    def returned_mask(self) -> np.ndarray:
        """(M,) bool over `fired`: did this ray produce a return?"""
        mask = np.zeros(self.fired.n_rays, dtype=bool)
        mask[self.ray_index] = True
        return mask

    def empty_rays(self) -> RayGrid:
        """The rays that were fired and came back with nothing.

        These are the rays that carry negative-obstacle evidence. They are
        *not* the same as directions that were never sampled, which do not
        appear in `fired` at all.
        """
        return self.fired.select(np.flatnonzero(~self.returned_mask()))

    @property
    def return_ratio(self) -> float:
        return self.n_returns / self.n_fired if self.n_fired else 0.0


@dataclass(frozen=True)
class RayBudget:
    """An allocator's decision: which of the sensor's rays to spend this frame.

    Expressed as indices into the sensor's native full ray grid, so every
    allocator - ours and each baseline - speaks the same language and any of
    them can drive any sensor backend.
    """

    ray_indices: np.ndarray   # (K,) int indices into the native grid
    n_native: int             # size of that native grid, for accounting

    def __post_init__(self) -> None:
        if self.ray_indices.ndim != 1:
            raise ValueError("ray_indices must be 1-D")
        if self.ray_indices.size:
            if self.ray_indices.min() < 0 or self.ray_indices.max() >= self.n_native:
                raise ValueError("ray_indices outside the native grid")
            if np.unique(self.ray_indices).size != self.ray_indices.size:
                raise ValueError("ray_indices contains duplicates")

    def __len__(self) -> int:
        return int(self.ray_indices.shape[0])

    @property
    def n_rays(self) -> int:
        return len(self)

    @property
    def fraction(self) -> float:
        """Share of the full scan this budget spends."""
        return self.n_rays / self.n_native if self.n_native else 0.0
