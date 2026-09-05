"""The 2.5D map: accumulation, readout, and the honesty of the default state."""

import numpy as np
import pytest

from raysense.mapping import FixedGridMap, MapConfig
from raysense.types import CellState

CFG = MapConfig(resolution=0.5, size_m=20.0, origin=(-10.0, -10.0))


def test_fresh_map_knows_nothing():
    m = FixedGridMap(CFG)
    assert m.coverage == 0.0
    assert not m.observed().any()
    assert (m.state == int(CellState.UNKNOWN)).all()
    assert np.isnan(m.height()).all()


def test_height_is_the_mean_of_what_landed_in_the_cell():
    m = FixedGridMap(CFG)
    m.integrate(np.array([[0.1, 0.1, 1.0], [0.2, 0.2, 3.0]]))
    r, c, _ = m.world_to_cell(np.array(0.1), np.array(0.1))
    assert m.height()[r, c] == pytest.approx(2.0)
    assert m.variance()[r, c] == pytest.approx(1.0)
    assert m.n_obs[r, c] == 2


def test_points_outside_the_grid_are_dropped_not_clamped():
    m = FixedGridMap(CFG)
    n = m.integrate(np.array([[0.0, 0.0, 1.0], [500.0, 0.0, 1.0], [0.0, -500.0, 1.0]]))
    assert n == 1
    assert m.observed().sum() == 1


def test_observation_marks_the_cell_as_surface():
    m = FixedGridMap(CFG)
    m.integrate(np.array([[0.0, 0.0, 1.0]]))
    r, c, _ = m.world_to_cell(np.array(0.0), np.array(0.0))
    assert m.state[r, c] & int(CellState.SURFACE)


def test_staleness_counts_frames_since_last_seen():
    m = FixedGridMap(CFG)
    m.integrate(np.array([[0.0, 0.0, 1.0]]), frame=4)
    r, c, _ = m.world_to_cell(np.array(0.0), np.array(0.0))
    assert m.staleness(frame=9)[r, c] == 5
    assert m.staleness(frame=9)[0, 0] == -1        # never seen


def test_round_trips_through_disk(tmp_path):
    m = FixedGridMap(CFG)
    rng = np.random.default_rng(0)
    m.integrate(np.column_stack([rng.uniform(-9, 9, 400), rng.uniform(-9, 9, 400),
                                 rng.normal(size=400)]), frame=2)
    m.save(tmp_path / "m.npz")
    back = FixedGridMap.load(tmp_path / "m.npz")

    assert back.config.shape == m.config.shape
    assert np.array_equal(back.n_obs, m.n_obs)
    assert np.allclose(np.nan_to_num(back.height()), np.nan_to_num(m.height()))
    assert back.coverage == m.coverage


def test_rejects_wrong_shaped_points():
    with pytest.raises(ValueError, match=r"\(N, 3\)"):
        FixedGridMap(CFG).integrate(np.zeros((4, 2)))
