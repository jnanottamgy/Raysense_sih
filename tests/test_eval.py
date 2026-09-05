"""Metrics, and the reason coverage must always be read next to error."""

import numpy as np
import pytest

from raysense.eval import elevation_metrics
from raysense.mapping import FixedGridMap, MapConfig

CFG = MapConfig(resolution=0.5, size_m=20.0, origin=(-10.0, -10.0))


def filled(points):
    m = FixedGridMap(CFG)
    m.integrate(np.asarray(points, dtype=float))
    return m


def test_a_map_scored_against_itself_is_perfect():
    rng = np.random.default_rng(0)
    pts = np.column_stack([rng.uniform(-9, 9, 500), rng.uniform(-9, 9, 500),
                           rng.normal(size=500)])
    m = filled(pts)
    r = elevation_metrics(m, m)
    assert r["elev_rmse"] == pytest.approx(0.0)
    assert r["coverage_recall"] == pytest.approx(1.0)
    assert r["n_extra"] == 0


def test_a_subset_map_scores_low_coverage_but_low_error():
    """The degeneracy this project has to keep in view.

    A budget that observes very little, very well, posts an excellent error
    while knowing almost nothing. Error is only meaningful beside coverage.
    """
    rng = np.random.default_rng(1)
    x = rng.uniform(-9, 9, 2000)
    y = rng.uniform(-9, 9, 2000)
    # a smooth surface, so the error being measured is sampling, not noise
    pts = np.column_stack([x, y, 0.10 * x + 0.05 * y])
    gt = filled(pts)
    part = filled(pts[:150])

    r = elevation_metrics(part, gt)
    assert r["coverage_recall"] < 0.25          # it saw very little
    assert r["elev_rmse"] < 0.05                # yet scores well on what it saw


def test_error_is_measured_where_both_maps_saw_something():
    gt = filled([[0.0, 0.0, 1.0], [3.0, 3.0, 5.0]])
    est = filled([[0.0, 0.0, 2.0]])
    r = elevation_metrics(est, gt)
    assert r["n_compared"] == 1
    assert r["elev_mae"] == pytest.approx(1.0)
    assert r["coverage_recall"] == pytest.approx(0.5)


def test_mismatched_grids_are_rejected():
    other = FixedGridMap(MapConfig(resolution=1.0, size_m=20.0, origin=(-10.0, -10.0)))
    with pytest.raises(ValueError, match="must share a grid"):
        elevation_metrics(filled([[0.0, 0.0, 1.0]]), other)
