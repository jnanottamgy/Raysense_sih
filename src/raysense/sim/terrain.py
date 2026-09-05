"""Synthetic off-road terrain and an analytic heightfield raycaster.

Why this exists rather than a game-engine simulator: the experiments this
project stands on need negative obstacles - ditches, craters, washouts - whose
geometry and extent are known exactly. Public off-road datasets contain very
few labelled ones. A heightfield world with rays cast analytically gives exact
ground truth, arbitrary obstacle placement and closed-loop motion, in a few
hundred lines and with no dependencies beyond NumPy.

The raycaster returns a `ScanResult`, so rays that were fired and came back
with nothing are preserved rather than dropped. That is the entire point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from raysense.types import RayGrid, ScanResult

FeatureKind = Literal["negative", "positive"]


@dataclass(frozen=True)
class Feature:
    """A deliberately planted terrain feature, with known ground truth."""

    id: int
    kind: FeatureKind
    label: str
    center: tuple[float, float]
    depth: float            # metres; positive number, meaning depends on `kind`
    extent: tuple[float, float]   # (along, across) or (radius, radius)


# --------------------------------------------------------------------- noise


def _bilinear_resize(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Bilinear upsample of a 2-D array to `shape`, NumPy only."""
    ny, nx = shape
    y = np.linspace(0.0, a.shape[0] - 1, ny)
    x = np.linspace(0.0, a.shape[1] - 1, nx)
    y0 = np.floor(y).astype(int)
    x0 = np.floor(x).astype(int)
    y1 = np.minimum(y0 + 1, a.shape[0] - 1)
    x1 = np.minimum(x0 + 1, a.shape[1] - 1)
    wy = (y - y0)[:, None]
    wx = (x - x0)[None, :]
    return (
        a[np.ix_(y0, x0)] * (1 - wy) * (1 - wx)
        + a[np.ix_(y1, x0)] * wy * (1 - wx)
        + a[np.ix_(y0, x1)] * (1 - wy) * wx
        + a[np.ix_(y1, x1)] * wy * wx
    )


def _fractal_noise(shape: tuple[int, int], octaves: int, seed: int) -> np.ndarray:
    """Value noise in [0, 1], summed over octaves of halving amplitude."""
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, dtype=float)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = 2 ** (o + 2)
        out += amp * _bilinear_resize(rng.random((n, n)), shape)
        total += amp
        amp *= 0.5
    return out / total


# ------------------------------------------------------------------- terrain


@dataclass
class Terrain:
    """A 2.5D heightfield world with labelled planted features.

    `feature_id` carries the exact ground truth used to score negative-obstacle
    detection: 0 means undisturbed terrain, any other value indexes `features`.
    """

    height: np.ndarray                    # (ny, nx) metres
    resolution: float                     # metres per cell
    origin: tuple[float, float] = (0.0, 0.0)   # world (x, y) of cell [0, 0]
    feature_id: np.ndarray | None = None  # (ny, nx) int
    features: list[Feature] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.feature_id is None:
            self.feature_id = np.zeros(self.height.shape, dtype=np.int32)

    # --------------------------------------------------------------- geometry

    @property
    def shape(self) -> tuple[int, int]:
        return self.height.shape

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(x_min, x_max, y_min, y_max) in world metres."""
        ny, nx = self.height.shape
        return (
            self.origin[0],
            self.origin[0] + nx * self.resolution,
            self.origin[1],
            self.origin[1] + ny * self.resolution,
        )

    def sample(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Bilinear terrain height at world (x, y). NaN outside the map.

        NaN rather than an edge clamp is deliberate: a ray that leaves the
        world must not register a spurious hit, it must return nothing.
        """
        gx = (np.asarray(x, dtype=float) - self.origin[0]) / self.resolution
        gy = (np.asarray(y, dtype=float) - self.origin[1]) / self.resolution
        ny, nx = self.height.shape

        inside = (gx >= 0) & (gx <= nx - 1) & (gy >= 0) & (gy <= ny - 1)
        gxc = np.clip(gx, 0, nx - 1)
        gyc = np.clip(gy, 0, ny - 1)

        x0 = np.floor(gxc).astype(int)
        y0 = np.floor(gyc).astype(int)
        x1 = np.minimum(x0 + 1, nx - 1)
        y1 = np.minimum(y0 + 1, ny - 1)
        wx = gxc - x0
        wy = gyc - y0

        h = (
            self.height[y0, x0] * (1 - wx) * (1 - wy)
            + self.height[y0, x1] * wx * (1 - wy)
            + self.height[y1, x0] * (1 - wx) * wy
            + self.height[y1, x1] * wx * wy
        )
        return np.where(inside, h, np.nan)

    def feature_at(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Nearest-cell feature id at world (x, y); 0 outside the map."""
        gx = np.rint((np.asarray(x) - self.origin[0]) / self.resolution).astype(int)
        gy = np.rint((np.asarray(y) - self.origin[1]) / self.resolution).astype(int)
        ny, nx = self.height.shape
        ok = (gx >= 0) & (gx < nx) & (gy >= 0) & (gy < ny)
        out = np.zeros(gx.shape, dtype=np.int32)
        out[ok] = self.feature_id[gy[ok], gx[ok]]
        return out

    # --------------------------------------------------------------- features

    def _grid_xy(self) -> tuple[np.ndarray, np.ndarray]:
        ny, nx = self.height.shape
        xs = self.origin[0] + np.arange(nx) * self.resolution
        ys = self.origin[1] + np.arange(ny) * self.resolution
        return np.meshgrid(xs, ys)

    def add_trench(
        self,
        center: tuple[float, float],
        length: float,
        width: float,
        depth: float,
        angle_deg: float = 0.0,
        label: str = "trench",
    ) -> Feature:
        """Carve a rectangular depression - the canonical negative obstacle."""
        gx, gy = self._grid_xy()
        a = np.deg2rad(angle_deg)
        dx, dy = gx - center[0], gy - center[1]
        along = dx * np.cos(a) + dy * np.sin(a)
        across = -dx * np.sin(a) + dy * np.cos(a)
        mask = (np.abs(along) <= length / 2) & (np.abs(across) <= width / 2)

        fid = len(self.features) + 1
        self.height[mask] -= depth
        self.feature_id[mask] = fid
        feat = Feature(fid, "negative", label, center, depth, (length, width))
        self.features.append(feat)
        return feat

    def add_crater(
        self,
        center: tuple[float, float],
        radius: float,
        depth: float,
        label: str = "crater",
    ) -> Feature:
        """A smooth bowl - a softer negative obstacle than a trench."""
        gx, gy = self._grid_xy()
        r = np.hypot(gx - center[0], gy - center[1])
        mask = r <= radius
        fid = len(self.features) + 1
        # cosine profile so the rim is continuous with the surrounding terrain
        self.height[mask] -= depth * 0.5 * (1 + np.cos(np.pi * r[mask] / radius))
        self.feature_id[mask] = fid
        feat = Feature(fid, "negative", label, center, depth, (radius, radius))
        self.features.append(feat)
        return feat

    def add_boulder(
        self,
        center: tuple[float, float],
        radius: float,
        height: float,
        label: str = "boulder",
    ) -> Feature:
        """A positive obstacle, for contrast and for positive-recall scoring."""
        gx, gy = self._grid_xy()
        r = np.hypot(gx - center[0], gy - center[1])
        mask = r <= radius
        fid = len(self.features) + 1
        self.height[mask] += height * np.sqrt(np.clip(1 - (r[mask] / radius) ** 2, 0, 1))
        self.feature_id[mask] = fid
        feat = Feature(fid, "positive", label, center, height, (radius, radius))
        self.features.append(feat)
        return feat

    # -------------------------------------------------------------- raycasting

    def raycast(
        self,
        rays: RayGrid,
        step: float = 0.35,
        refine: int = 10,
    ) -> ScanResult:
        """March `rays` against the heightfield and return what came back.

        Rays are advanced together in fixed steps until they pass below the
        surface, then the crossing is bracketed and bisected. Rays that never
        cross - because they point at the sky, leave the world, or reach max
        range over a depression - simply produce no return, and are preserved
        in `ScanResult.fired` as evidence.
        """
        d = rays.directions()
        o = np.asarray(rays.origin, dtype=float)
        m = len(rays)

        hit_t = np.full(m, np.inf)
        alive = np.arange(m)          # indices of rays still marching
        t_prev = np.zeros(m)

        n_steps = int(np.ceil(rays.max_range / step))
        for i in range(1, n_steps + 1):
            if alive.size == 0:
                break
            t = i * step
            p = o + d[alive] * t
            h = self.sample(p[:, 0], p[:, 1])
            crossed = np.isfinite(h) & (p[:, 2] <= h)
            if crossed.any():
                idx = alive[crossed]
                hit_t[idx] = t
                t_prev[idx] = t - step
            alive = alive[~crossed]

        hit = np.isfinite(hit_t)
        hi = np.flatnonzero(hit)
        if hi.size:
            lo_t = t_prev[hi].copy()
            hi_t = hit_t[hi].copy()
            dh = d[hi]
            for _ in range(refine):
                mid = 0.5 * (lo_t + hi_t)
                p = o + dh * mid[:, None]
                h = self.sample(p[:, 0], p[:, 1])
                below = np.isfinite(h) & (p[:, 2] <= h)
                hi_t = np.where(below, mid, hi_t)
                lo_t = np.where(below, lo_t, mid)
            hit_t[hi] = hi_t

        # a crossing beyond max range is not a return
        valid = np.flatnonzero(np.isfinite(hit_t) & (hit_t <= rays.max_range))
        points = o + d[valid] * hit_t[valid][:, None]
        return ScanResult(points=points, ray_index=valid, fired=rays)


def make_terrain(
    size_m: float = 120.0,
    resolution: float = 0.25,
    roughness: float = 0.6,
    octaves: int = 5,
    seed: int = 0,
    centered: bool = True,
) -> Terrain:
    """A rolling off-road surface with no planted features yet.

    `roughness` is the peak-to-peak height variation in metres.
    """
    n = int(round(size_m / resolution))
    h = _fractal_noise((n, n), octaves=octaves, seed=seed)
    h = (h - h.mean()) * roughness
    origin = (-size_m / 2, -size_m / 2) if centered else (0.0, 0.0)
    return Terrain(height=h, resolution=resolution, origin=origin)
