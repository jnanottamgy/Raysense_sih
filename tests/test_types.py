"""The data contract. If these break, the project's central idea has leaked away."""

import numpy as np
import pytest

from raysense.types import CellState, RayBudget, RayGrid, ScanResult


def make_grid(m=8):
    return RayGrid(
        azimuth=np.linspace(0, 1, m),
        elevation=np.zeros(m),
        origin=np.zeros(3),
        max_range=100.0,
        beam_index=np.arange(m),
    )


def test_unknown_is_the_zero_state():
    """A freshly allocated map must start out admitting it knows nothing."""
    assert int(CellState.UNKNOWN) == 0
    fresh = np.zeros((4, 4), dtype=np.int32)
    assert not CellState.is_observed(fresh).any()


def test_directions_are_unit_vectors():
    d = make_grid().directions()
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0)


def test_non_returns_survive_the_scan():
    """The whole project: a fired ray that came back empty is still evidence."""
    grid = make_grid(10)
    returned = np.array([0, 3, 7])
    scan = ScanResult(points=np.zeros((3, 3)), ray_index=returned, fired=grid)

    assert scan.n_fired == 10
    assert scan.n_returns == 3
    assert scan.empty_rays().n_rays == 7
    assert scan.returned_mask().sum() == 3
    # every fired ray is accounted for as exactly one of the two kinds
    assert scan.n_returns + scan.empty_rays().n_rays == scan.n_fired


def test_empty_rays_are_not_the_same_as_unsampled_directions():
    """A budget of 4 rays leaves 6 directions never looked at — a third state."""
    native = 10
    grid = make_grid(native).select(np.array([0, 1, 2, 3]))
    scan = ScanResult(points=np.zeros((1, 3)), ray_index=np.array([0]), fired=grid)
    assert scan.n_fired == 4
    assert scan.empty_rays().n_rays == 3          # fired, nothing back
    assert native - scan.n_fired == 6             # never fired at all


def test_scan_rejects_more_returns_than_rays():
    grid = make_grid(2)
    with pytest.raises(ValueError, match="cannot return more than once"):
        ScanResult(np.zeros((3, 3)), np.array([0, 1, 1]), grid)


def test_scan_rejects_out_of_range_ray_index():
    with pytest.raises(ValueError, match="outside"):
        ScanResult(np.zeros((1, 3)), np.array([99]), make_grid(4))


def test_budget_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicates"):
        RayBudget(np.array([1, 1, 2]), n_native=10)


def test_budget_fraction_is_the_spend():
    b = RayBudget(np.arange(25), n_native=100)
    assert b.n_rays == 25
    assert b.fraction == pytest.approx(0.25)
