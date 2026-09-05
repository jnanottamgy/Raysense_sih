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
