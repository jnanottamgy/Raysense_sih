"""Ground truth from the world itself, not from what a sensor happened to see.

This is the reason the synthetic testbed earns its place. Scoring against a
map built from full scans would score us against the *sensor's* blind spots,
and every strategy would look perfect on the ditches nobody ever observed. The
simulator knows where the ditches actually are, so truth is rasterised from the
terrain directly.
"""

from __future__ import annotations

import numpy as np

from raysense.mapping import FixedGridMap
from raysense.perceive.traversability import Traversability, TraversabilityConfig
from raysense.sim import Scene


def true_heights(emap: FixedGridMap, scene: Scene) -> np.ndarray:
    """The real terrain height at every map cell."""
    X, Y = emap.cell_centres()
    return scene.terrain.sample(X, Y)


def feature_masks(emap: FixedGridMap, scene: Scene) -> dict[str, np.ndarray]:
    """Boolean masks for the planted negative and positive obstacles."""
    X, Y = emap.cell_centres()
    neg = np.zeros(emap.config.shape, dtype=bool)
    pos = np.zeros(emap.config.shape, dtype=bool)

    for f in scene.terrain.features:
        if f.label in ("crater", "boulder"):
            m = np.hypot(X - f.center[0], Y - f.center[1]) <= f.extent[0]
        else:
            m = ((np.abs(X - f.center[0]) <= f.extent[1] / 2)
                 & (np.abs(Y - f.center[1]) <= f.extent[0] / 2))
        if f.kind == "negative":
            neg |= m
        else:
            pos |= m
    return {"negative": neg, "positive": pos}


def true_traversability(
    emap: FixedGridMap,
    scene: Scene,
    cfg: TraversabilityConfig | None = None,
) -> np.ndarray:
    """What a perfect sensor would conclude — two-valued, never unknown.

    Computed from the terrain itself, so the trenches are `BLOCKED` here even
    though no scan in the project ever observed their interiors. That gap
    between truth and observation is exactly what we are trying to measure.
    """
    cfg = cfg or TraversabilityConfig()
    h = true_heights(emap, scene)
    res = emap.config.resolution
    r = cfg.ground_window // 2

    pad = np.pad(h, r, mode="edge")
    ny, nx = h.shape
    ground = np.full(h.shape, np.inf)
    for dy in range(cfg.ground_window):
        for dx in range(cfg.ground_window):
            ground = np.fmin(ground, pad[dy:dy + ny, dx:dx + nx])
    step = h - ground

    gy, gx = np.gradient(np.nan_to_num(h), res)
    slope = np.hypot(gy, gx)

    out = np.full(h.shape, int(Traversability.TRAVERSABLE), dtype=np.int8)
    with np.errstate(invalid="ignore"):
        out[(step > cfg.max_step) | (slope > cfg.max_slope)] = int(Traversability.BLOCKED)

    # A ditch reads as a depression rather than a step, so the geometric tests
    # above can miss its floor. The planted masks are the authority.
    out[feature_masks(emap, scene)["negative"]] = int(Traversability.BLOCKED)
    out[np.isnan(h)] = int(Traversability.UNKNOWN)
    return out
