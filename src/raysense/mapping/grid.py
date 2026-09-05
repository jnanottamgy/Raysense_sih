"""The 2.5D elevation map.

A 2.5D map is a plan-view grid carrying one height per cell — the standard
representation for deciding what a ground vehicle can drive over, and what the
problem statement asks us to produce.

`FixedGridMap` is deliberately the simple implementation: a flat array, no
subdivision. Every experiment in this project works on it unchanged, so it
de-risks the pipeline before the multi-resolution structure named in the
problem statement title arrives behind the same interface.

Cells accumulate `n`, `sum` and `sum of squares` rather than a running
Welford update, because those three are *mergeable*: points scatter into cells
in arbitrary order, across arbitrary frames, and can be combined with a plain
scatter-add. Heights are metres in a range of a few tens, so the loss of
precision against Welford is irrelevant here.

Unobserved cells stay `CellState.UNKNOWN`, which is the zero value. A freshly
allocated map therefore starts out admitting it knows nothing, and only a
measurement moves it off that.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from raysense.types import CellState


@dataclass(frozen=True)
class MapConfig:
    """Extent and cell size of the plan-view grid."""

    resolution: float = 0.4              # metres per cell
    size_m: float = 120.0                # square extent
    origin: tuple[float, float] = (-60.0, -60.0)   # world (x, y) of cell [0, 0]

    @property
    def n_cells(self) -> int:
        n = int(round(self.size_m / self.resolution))
        return n * n

    @property
    def shape(self) -> tuple[int, int]:
        n = int(round(self.size_m / self.resolution))
        return (n, n)


@runtime_checkable
class ElevationMap(Protocol):
    """What every map implementation must offer.

    `QuadtreeMap` will satisfy this too, so the pipeline never learns which
    one it is holding.
    """

    config: MapConfig

    def integrate(self, points_world: np.ndarray, frame: int) -> None: ...
    def height(self) -> np.ndarray: ...
    def observed(self) -> np.ndarray: ...


class FixedGridMap:
    """A flat-array 2.5D elevation map in the world frame."""

    def __init__(self, config: MapConfig | None = None) -> None:
        self.config = config or MapConfig()
        shape = self.config.shape
        self.n_obs = np.zeros(shape, dtype=np.int32)
        self.h_sum = np.zeros(shape, dtype=np.float64)
        self.h_sumsq = np.zeros(shape, dtype=np.float64)
        self.last_seen = np.full(shape, -1, dtype=np.int32)
        self.state = np.zeros(shape, dtype=np.int32)   # CellState.UNKNOWN

    # ----------------------------------------------------------- coordinates

    def world_to_cell(
        self, x: np.ndarray, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """World metres -> (row, col, inside). Cells outside the grid are flagged."""
        c = self.config
        ny, nx = c.shape
        col = np.floor((np.asarray(x) - c.origin[0]) / c.resolution).astype(np.int64)
        row = np.floor((np.asarray(y) - c.origin[1]) / c.resolution).astype(np.int64)
        inside = (col >= 0) & (col < nx) & (row >= 0) & (row < ny)
        return row, col, inside

    def cell_centres(self) -> tuple[np.ndarray, np.ndarray]:
        """(X, Y) world coordinates of every cell centre."""
        c = self.config
        ny, nx = c.shape
        xs = c.origin[0] + (np.arange(nx) + 0.5) * c.resolution
        ys = c.origin[1] + (np.arange(ny) + 0.5) * c.resolution
        return np.meshgrid(xs, ys)

    @property
    def extent(self) -> tuple[float, float, float, float]:
        """(left, right, bottom, top) for imshow."""
        c = self.config
        ny, nx = c.shape
        return (
            c.origin[0], c.origin[0] + nx * c.resolution,
            c.origin[1], c.origin[1] + ny * c.resolution,
        )

    # ------------------------------------------------------------ integration

    def integrate(self, points_world: np.ndarray, frame: int = 0) -> int:
        """Fold return points into the grid. Returns how many landed inside."""
        pts = np.asarray(points_world, dtype=np.float64)
        if pts.size == 0:
            return 0
        if pts.ndim != 2 or pts.shape[1] != 3:
            raise ValueError(f"points_world must be (N, 3), got {pts.shape}")

        row, col, inside = self.world_to_cell(pts[:, 0], pts[:, 1])
        r, c_, z = row[inside], col[inside], pts[inside, 2]
        if r.size == 0:
            return 0

        np.add.at(self.n_obs, (r, c_), 1)
        np.add.at(self.h_sum, (r, c_), z)
        np.add.at(self.h_sumsq, (r, c_), z * z)
        self.last_seen[r, c_] = frame
        self.state[r, c_] |= int(CellState.SURFACE)
        return int(r.size)

    # --------------------------------------------------------------- readout

    def observed(self) -> np.ndarray:
        """Cells that have at least one return."""
        return self.n_obs > 0

    def height(self, fill: float = np.nan) -> np.ndarray:
        """Mean height per cell; `fill` where nothing has been observed."""
        out = np.full(self.config.shape, fill, dtype=np.float64)
        seen = self.observed()
        out[seen] = self.h_sum[seen] / self.n_obs[seen]
        return out

    def variance(self, fill: float = np.nan) -> np.ndarray:
        """Population variance of the heights in each cell.

        A roughness proxy, and one of the terms the M5 need map is built from:
        cells whose height disagrees with itself are where the information is.
        """
        out = np.full(self.config.shape, fill, dtype=np.float64)
        seen = self.observed()
        n = self.n_obs[seen]
        mean = self.h_sum[seen] / n
        out[seen] = np.maximum(self.h_sumsq[seen] / n - mean * mean, 0.0)
        return out

    @property
    def coverage(self) -> float:
        """Share of the grid that has been observed at all."""
        return float(self.observed().mean())

    def staleness(self, frame: int, fill: int = -1) -> np.ndarray:
        """Frames since each cell was last updated; `fill` where never seen."""
        out = np.full(self.config.shape, fill, dtype=np.int32)
        seen = self.last_seen >= 0
        out[seen] = frame - self.last_seen[seen]
        return out

    # ------------------------------------------------------------ persistence

    def save(self, path: str | Path) -> None:
        """Cache to .npz. Ground-truth maps are expensive; build them once."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(path),
            n_obs=self.n_obs, h_sum=self.h_sum, h_sumsq=self.h_sumsq,
            last_seen=self.last_seen, state=self.state,
            resolution=self.config.resolution, size_m=self.config.size_m,
            origin=np.asarray(self.config.origin),
        )

    @classmethod
    def load(cls, path: str | Path) -> FixedGridMap:
        d = np.load(str(path))
        m = cls(MapConfig(
            resolution=float(d["resolution"]),
            size_m=float(d["size_m"]),
            origin=tuple(d["origin"].tolist()),
        ))
        m.n_obs, m.h_sum, m.h_sumsq = d["n_obs"], d["h_sum"], d["h_sumsq"]
        m.last_seen, m.state = d["last_seen"], d["state"]
        return m

    def __repr__(self) -> str:
        ny, nx = self.config.shape
        return (
            f"FixedGridMap({ny}x{nx} @ {self.config.resolution} m, "
            f"coverage {self.coverage:.1%})"
        )
