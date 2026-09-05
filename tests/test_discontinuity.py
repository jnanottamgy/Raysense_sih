"""Signature B — the gap in the ground that geometry cannot explain."""

import numpy as np
import pytest

from raysense.mapping import FixedGridMap, MapConfig
from raysense.raycast import find_discontinuities, mark_discontinuities
from raysense.sensor import SensorModel
from raysense.sim import Terrain, make_terrain
from raysense.types import CellState

SENSOR = SensorModel.from_yaml("configs/sensor/ouster_os1_64.yaml")
CFG = MapConfig(resolution=0.4, size_m=200.0, origin=(-100.0, -100.0))


def scan_over(terrain, origin=(0.0, 0.0)):
    g = float(terrain.sample(np.array(origin[0]), np.array(origin[1])))
    o = np.array([origin[0], origin[1], g + SENSOR.mount_height])
    return terrain.raycast(SENSOR.full_ray_grid(o))


def test_flat_ground_raises_nothing():
    n = 800
    flat = Terrain(np.zeros((n, n)), 0.3, (-120.0, -120.0))
    near, _, _ = find_discontinuities(scan_over(flat), SENSOR)
    assert len(near) == 0


def test_rolling_ground_raises_far_fewer_flags_than_a_trench():
    """Uneven ground is not free of flags, and pretending otherwise is a trap.

    Crests occlude the ground behind them, which produces a genuine range gap.
    Whether that counts as a false positive is arguable — the ground behind a
    crest really is unobserved — but it is certainly not zero, and any claim
    that the detector is clean on rolling terrain is wrong. What is true is
    that a trench raises many times more flags, at much higher ratios.
    """
    t = make_terrain(size_m=240, resolution=0.3, roughness=3.0, seed=7)
    bare, _, bare_ratio = find_discontinuities(scan_over(t), SENSOR)

    dug = make_terrain(size_m=240, resolution=0.3, roughness=3.0, seed=7)
    dug.add_trench((10.0, 0.0), length=16.0, width=2.4, depth=1.8, angle_deg=90.0)
    with_trench, _, trench_ratio = find_discontinuities(scan_over(dug), SENSOR)

    assert len(with_trench) > len(bare)
    assert trench_ratio.max() > bare_ratio.max()
    # and flags stay a small share of the returns either way
    assert len(bare) / scan_over(t).n_returns < 0.01


def test_a_stepped_over_trench_is_found():
    """The exact case the M4 absence test scored 0.0% on."""
    t = make_terrain(size_m=240, resolution=0.3, roughness=3.0, seed=7)
    t.add_trench((10.0, 0.0), length=16.0, width=2.4, depth=1.8, angle_deg=90.0)
    near, far, ratio = find_discontinuities(scan_over(t), SENSOR)
    assert len(near) > 0
    assert ratio.max() > 3.0


@pytest.mark.parametrize("width,depth", [(2.4, 1.8), (3.0, 2.2), (5.0, 2.0)])
def test_trenches_of_several_sizes_are_found(width, depth):
    t = make_terrain(size_m=240, resolution=0.3, roughness=3.0, seed=7)
    t.add_trench((12.0, 0.0), length=16.0, width=width, depth=depth, angle_deg=90.0)
    near, _, _ = find_discontinuities(scan_over(t), SENSOR)
    assert len(near) > 0


def test_the_flagged_span_lands_on_the_trench():
    t = make_terrain(size_m=240, resolution=0.3, roughness=3.0, seed=7)
    t.add_trench((10.0, 0.0), length=16.0, width=2.4, depth=1.8, angle_deg=90.0)
    m = FixedGridMap(CFG)
    n = mark_discontinuities(m, scan_over(t), SENSOR)
    assert n > 0

    X, Y = m.cell_centres()
    inside = (np.abs(X - 10.0) <= 1.2) & (np.abs(Y) <= 8.0)
    cand = (m.state & int(CellState.CANDIDATE_NEGATIVE)) != 0
    assert (cand & inside).sum() / inside.sum() > 0.5


def test_a_flagged_cell_is_not_also_free():
    t = make_terrain(size_m=240, resolution=0.3, roughness=3.0, seed=7)
    t.add_trench((10.0, 0.0), length=16.0, width=2.4, depth=1.8, angle_deg=90.0)
    m = FixedGridMap(CFG)
    mark_discontinuities(m, scan_over(t), SENSOR)
    cand = (m.state & int(CellState.CANDIDATE_NEGATIVE)) != 0
    assert not ((m.state[cand] & int(CellState.FREE)) != 0).any()


def test_too_few_returns_is_not_an_error():
    from raysense.types import RayGrid, ScanResult
    g = RayGrid(np.zeros(1), np.array([-0.2]), np.zeros(3), 50.0, np.zeros(1, dtype=int))
    near, _, _ = find_discontinuities(ScanResult(np.zeros((1, 3)), np.array([0]), g), SENSOR)
    assert len(near) == 0
