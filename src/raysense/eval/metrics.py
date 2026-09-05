"""Metrics. Every number in the deck comes from here, via a committed CSV.

At M2 the questions are the two simplest honest ones:

* **How wrong is the map** where the budget did observe something?
* **How much of the world did it fail to observe at all?**

The second matters more than it looks. A tiny budget can post an excellent
elevation error simply by observing very little, very close in — so error must
always be read next to coverage, never alone.
"""

from __future__ import annotations

import numpy as np

from raysense.mapping import FixedGridMap


def elevation_metrics(est: FixedGridMap, gt: FixedGridMap) -> dict[str, float]:
    """Compare an estimated map against the full-scan ground truth."""
    if est.config.shape != gt.config.shape:
        raise ValueError(
            f"map shapes differ: {est.config.shape} vs {gt.config.shape}; "
            "estimate and ground truth must share a grid"
        )

    est_seen, gt_seen = est.observed(), gt.observed()
    both = est_seen & gt_seen

    n_gt = int(gt_seen.sum())
    n_both = int(both.sum())

    if n_both:
        err = est.height()[both] - gt.height()[both]
        mae = float(np.abs(err).mean())
        rmse = float(np.sqrt((err * err).mean()))
        p95 = float(np.percentile(np.abs(err), 95))
    else:
        mae = rmse = p95 = float("nan")

    return {
        "elev_mae": mae,
        "elev_rmse": rmse,
        "elev_p95": p95,
        "n_compared": n_both,
        "n_gt_cells": n_gt,
        # share of the ground truth this budget managed to observe at all
        "coverage_recall": n_both / n_gt if n_gt else float("nan"),
        "coverage": float(est_seen.mean()),
        # cells claimed that ground truth never saw — should be ~0 by construction
        "n_extra": int((est_seen & ~gt_seen).sum()),
    }


def traversability_metrics(est: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    """Score a three-valued decision against a two-valued truth.

    The split that matters is three-way, not two. Calling a ditch `UNKNOWN` is
    a failure to detect, but it is an *honest* one — the vehicle slows or stops.
    Calling it `TRAVERSABLE` is the failure that destroys the vehicle. Lumping
    them together as "not detected" hides the only distinction a defence
    customer cares about.
    """
    from raysense.perceive import Traversability as T

    blocked_truth = truth == int(T.BLOCKED)
    free_truth = truth == int(T.TRAVERSABLE)

    said_blocked = est == int(T.BLOCKED)
    said_free = est == int(T.TRAVERSABLE)
    said_unknown = est == int(T.UNKNOWN)

    n_blocked = int(blocked_truth.sum())
    n_free = int(free_truth.sum())

    tp = int((said_blocked & blocked_truth).sum())
    fp = int((said_blocked & free_truth).sum())
    unsafe = int((said_free & blocked_truth).sum())     # the one that kills
    unknown_on_hazard = int((said_unknown & blocked_truth).sum())

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / n_blocked if n_blocked else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (tp + fp) and n_blocked and (precision + recall) > 0 else float("nan"))

    return {
        "trav_precision": precision,
        "trav_recall": recall,
        "trav_f1": f1,
        # share of real hazards reported as safe to drive over
        "unsafe_rate": unsafe / n_blocked if n_blocked else float("nan"),
        # share of real hazards the system admits it cannot judge
        "unknown_on_hazard": unknown_on_hazard / n_blocked if n_blocked else float("nan"),
        "n_hazard_cells": n_blocked,
        "n_free_cells": n_free,
        "free_coverage": float(said_free.sum() + said_blocked.sum()) / est.size,
    }


def feature_recall(est: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, float]:
    """Per-kind outcome on the planted obstacles.

    Reported as the same three-way split: detected, admitted unknown, or
    silently waved through. The last column is the headline of this project.
    """
    from raysense.perceive import Traversability as T

    out: dict[str, float] = {}
    for kind, m in masks.items():
        n = int(m.sum())
        if not n:
            out[f"{kind}_detected"] = float("nan")
            out[f"{kind}_unknown"] = float("nan")
            out[f"{kind}_missed_unsafe"] = float("nan")
            continue
        out[f"{kind}_detected"] = float((est[m] == int(T.BLOCKED)).sum()) / n
        out[f"{kind}_unknown"] = float((est[m] == int(T.UNKNOWN)).sum()) / n
        out[f"{kind}_missed_unsafe"] = float((est[m] == int(T.TRAVERSABLE)).sum()) / n
        out[f"n_{kind}_cells"] = n
    return out


def corridor_recall(
    est: np.ndarray,
    masks: dict[str, np.ndarray],
    path_distance: np.ndarray,
    half_width: float,
) -> dict[str, float]:
    """Recall restricted to hazards the vehicle could actually drive into.

    Whole-map recall weights a ditch sixty metres off the route exactly as
    heavily as one directly ahead, which is not what a vehicle cares about and
    not what the allocator is trying to optimise. This scores only the hazards
    inside the driven corridor.
    """
    from raysense.perceive import Traversability as T

    near = path_distance <= half_width
    out: dict[str, float] = {}
    for kind, m in masks.items():
        sel = m & near
        n = int(sel.sum())
        if not n:
            out[f"corridor_{kind}_detected"] = float("nan")
            out[f"corridor_{kind}_missed_unsafe"] = float("nan")
            out[f"n_corridor_{kind}"] = 0
            continue
        out[f"corridor_{kind}_detected"] = float((est[sel] == int(T.BLOCKED)).sum()) / n
        out[f"corridor_{kind}_missed_unsafe"] = (
            float((est[sel] == int(T.TRAVERSABLE)).sum()) / n
        )
        out[f"n_corridor_{kind}"] = n
    return out


def distance_to_path(emap, path: np.ndarray) -> np.ndarray:
    """Shortest distance from every map cell to the driven route."""
    X, Y = emap.cell_centres()
    best = np.full(X.shape, np.inf)
    for px, py in path:
        np.minimum(best, np.hypot(X - px, Y - py), out=best)
    return best
