"""Ray accounting — turning absences into evidence.

These tests pin the distinction the project rests on: a ray that was fired and
came back with nothing must leave a different mark on the map from a direction
that was never sampled at all.
"""

import numpy as np
import pytest

from raysense.mapping import FixedGridMap, MapConfig
from raysense.raycast import integrate_rays
from raysense.sim import Terrain
from raysense.types import CellState, RayGrid, ScanResult

CFG = MapConfig(resolution=0.5, size_m=120.0, origin=(-60.0, -60.0))


def flat_terrain(size=200, res=0.5):
    n = int(size / res)
    return Terrain(height=np.zeros((n, n)), resolution=res, origin=(-size / 2, -size / 2))


def down_rays(origin, elevations_deg, max_range=80.0):
    el = np.deg2rad(np.asarray(elevations_deg, dtype=float))
    return RayGrid(np.zeros_like(el), el, np.asarray(origin, float), max_range,
                   np.arange(el.size))


def has(state, flag):
    return (state & int(flag)) != 0


def test_a_returning_ray_leaves_free_space_behind_it():
    t = flat_terrain()
    rays = down_rays([0, 0, 1.8], np.linspace(-20, -6, 40))
    scan = t.raycast(rays, step=0.2, refine=12)

    m = FixedGridMap(CFG)
    m.integrate(scan.points)
    integrate_rays(m, scan)

    assert has(m.state, CellState.SURFACE).any()
    assert has(m.state, CellState.FREE).any()
    assert not has(m.state, CellState.CANDIDATE_NEGATIVE).any()


def test_a_ditch_that_swallows_rays_is_flagged_as_a_candidate():
    """The core mechanism: fired, no return, where ground was expected."""
    dug = flat_terrain(size=400)
    dug.add_trench(center=(30.0, 0.0), length=80.0, width=60.0, depth=8.0, angle_deg=90.0)
    rays = down_rays([0, 0, 1.8], np.linspace(-5.0, -3.0, 60), max_range=40.0)
    scan = dug.raycast(rays, step=0.2, refine=12)

    assert scan.n_returns == 0, "this geometry is meant to destroy every return"

    m = FixedGridMap(CFG)
    tally = integrate_rays(m, scan)
    assert tally["candidate_negative"] > 0
    assert has(m.state, CellState.CANDIDATE_NEGATIVE).any()


def test_unsampled_directions_stay_unknown():
    """A ray never fired must leave no mark at all — the third state."""
    t = flat_terrain()
    rays = down_rays([0, 0, 1.8], np.linspace(-20, -10, 20))   # forward only
    scan = t.raycast(rays, step=0.2, refine=12)

    m = FixedGridMap(CFG)
    m.integrate(scan.points)
    integrate_rays(m, scan)

    X, Y = m.cell_centres()
    behind = X < -20.0                       # nothing was ever fired that way
    assert (m.state[behind] == int(CellState.UNKNOWN)).all()


def test_upward_rays_teach_a_plan_view_map_nothing():
    t = flat_terrain()
    rays = down_rays([0, 0, 1.8], [5.0, 15.0, 30.0])
    scan = t.raycast(rays)
    assert scan.n_returns == 0

    m = FixedGridMap(CFG)
    tally = integrate_rays(m, scan)
    assert tally["to_sky"] == 3
    assert tally["candidate_negative"] == 0
    assert (m.state == int(CellState.UNKNOWN)).all()


def test_a_candidate_cell_is_not_also_marked_free():
    """Two rays can disagree; the suspicion must win."""
    dug = flat_terrain(size=400)
    dug.add_trench(center=(25.0, 0.0), length=80.0, width=50.0, depth=8.0, angle_deg=90.0)
    rays = down_rays([0, 0, 1.8], np.linspace(-6.0, -3.0, 80), max_range=40.0)
    scan = dug.raycast(rays, step=0.2, refine=12)

    m = FixedGridMap(CFG)
    integrate_rays(m, scan)
    cand = has(m.state, CellState.CANDIDATE_NEGATIVE)
    assert cand.any()
    assert not has(m.state[cand], CellState.FREE).any()


def test_an_empty_scan_is_handled_without_complaint():
    m = FixedGridMap(CFG)
    empty = ScanResult(
        points=np.zeros((0, 3)), ray_index=np.zeros(0, dtype=int),
        fired=RayGrid(np.zeros(0), np.zeros(0), np.zeros(3), 80.0, np.zeros(0, dtype=int)),
    )
    assert integrate_rays(m, empty) == {"returned": 0, "candidate_negative": 0, "to_sky": 0}


def test_accounting_never_un_observes_a_surface():
    t = flat_terrain()
    rays = down_rays([0, 0, 1.8], np.linspace(-25, -5, 60))
    scan = t.raycast(rays, step=0.2, refine=12)

    m = FixedGridMap(CFG)
    m.integrate(scan.points)
    before = m.observed().sum()
    integrate_rays(m, scan)
    assert m.observed().sum() == before


@pytest.mark.parametrize("depth", [3.0, 6.0, 10.0])
def test_deeper_ditches_are_at_least_as_detectable(depth):
    dug = flat_terrain(size=400)
    dug.add_trench((30.0, 0.0), length=80.0, width=60.0, depth=depth, angle_deg=90.0)
    rays = down_rays([0, 0, 1.8], np.linspace(-5.0, -3.0, 60), max_range=40.0)
    m = FixedGridMap(CFG)
    tally = integrate_rays(m, dug.raycast(rays, step=0.2, refine=12))
    assert tally["candidate_negative"] > 0
