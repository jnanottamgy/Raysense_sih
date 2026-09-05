"""Allocators and the replay backend.

The backend test is the load-bearing one: replaying a budget must preserve the
three-way distinction the project rests on, rather than quietly collapsing
fired-and-empty into never-sampled.
"""

import numpy as np
import pytest

from raysense.allocate import FullScan, RandomSubsample, UniformDecimation, WorldState
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import make_terrain

SENSOR = SensorModel.from_yaml("configs/sensor/ouster_os1_64.yaml")


@pytest.fixture(scope="module")
def full_scan():
    t = make_terrain(size_m=120, resolution=0.5, roughness=1.5, seed=11)
    t.add_trench((15.0, 0.0), length=12.0, width=3.0, depth=2.0, angle_deg=90.0)
    return t.raycast(SENSOR.full_ray_grid(np.array([0.0, 0.0, 1.8])))


def world():
    return WorldState(sensor=SENSOR, frame=0, origin=np.zeros(3))


@pytest.mark.parametrize("alloc", [FullScan(), UniformDecimation(), RandomSubsample(0)])
@pytest.mark.parametrize("frac", [0.02, 0.1, 0.5, 1.0])
def test_allocators_never_overspend(alloc, frac):
    w = world()
    b = alloc.allocate(w, int(frac * SENSOR.n_rays))
    assert b.n_rays <= SENSOR.n_rays
    assert np.unique(b.ray_indices).size == b.n_rays
    assert b.ray_indices.min() >= 0 and b.ray_indices.max() < SENSOR.n_rays
    if alloc.name != "full":
        assert b.n_rays <= int(frac * SENSOR.n_rays) + 1


def test_full_scan_spends_everything():
    b = FullScan().allocate(world(), 1)
    assert b.n_rays == SENSOR.n_rays
    assert b.fraction == 1.0


def test_uniform_thins_both_axes():
    """A comb down one axis would be a different, worse baseline."""
    b = UniformDecimation().allocate(world(), SENSOR.n_rays // 16)
    beams = np.unique(SENSOR.beam_of(b.ray_indices))
    cols = np.unique(SENSOR.column_of(b.ray_indices))
    assert len(beams) < SENSOR.n_beams
    assert len(cols) < SENSOR.n_azimuth


def test_random_is_reproducible_from_its_seed():
    a = RandomSubsample(42).allocate(world(), 1000)
    b = RandomSubsample(42).allocate(world(), 1000)
    assert np.array_equal(a.ray_indices, b.ray_indices)


def test_replay_at_full_budget_reproduces_the_recording(full_scan):
    out = ReplayBackend(full_scan).acquire(FullScan().allocate(world(), 0))
    assert out.n_fired == full_scan.n_fired
    assert out.n_returns == full_scan.n_returns


def test_replay_preserves_fired_but_empty_rays(full_scan):
    """The distinction the whole project rests on must survive subsampling."""
    budget = UniformDecimation().allocate(world(), SENSOR.n_rays // 4)
    out = ReplayBackend(full_scan).acquire(budget)

    assert out.n_fired == budget.n_rays
    assert out.n_returns < out.n_fired          # some budgeted rays came back empty
    assert out.empty_rays().n_rays > 0
    assert out.n_returns + out.empty_rays().n_rays == out.n_fired
    # and the rays outside the budget are a third thing entirely
    assert SENSOR.n_rays - out.n_fired > 0


def test_replay_never_invents_returns(full_scan):
    """A replayed return must be one the recording actually contained."""
    budget = RandomSubsample(3).allocate(world(), SENSOR.n_rays // 8)
    out = ReplayBackend(full_scan).acquire(budget)
    assert out.n_returns <= full_scan.n_returns

    recorded = {tuple(np.round(p, 6)) for p in full_scan.points}
    for p in out.points[:200]:
        assert tuple(np.round(p, 6)) in recorded


def test_smaller_budgets_never_yield_more_returns(full_scan):
    backend = ReplayBackend(full_scan)
    counts = [
        backend.acquire(UniformDecimation().allocate(world(), int(f * SENSOR.n_rays))).n_returns
        for f in (0.02, 0.1, 0.3, 1.0)
    ]
    assert counts == sorted(counts)
