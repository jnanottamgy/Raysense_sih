"""The Raysense allocator: budget discipline, safety floor, sampling structure."""

import numpy as np
import pytest

from raysense.allocate import RaysenseAllocator, UniformDecimation, VehicleModel, WorldState
from raysense.mapping import FixedGridMap
from raysense.sensor import SensorModel
from raysense.sim import offroad_course

SENSOR = SensorModel.from_yaml("configs/sensor/ouster_os1_64.yaml")
VEHICLE = VehicleModel.from_yaml("configs/vehicle/warthog.yaml")


def world(emap=None, frame=0):
    return WorldState(sensor=SENSOR, frame=frame,
                      origin=np.array([0.0, 0.0, 1.8]), emap=emap)


@pytest.mark.parametrize("frac", [0.02, 0.05, 0.2, 0.5])
def test_never_overspends_and_never_under_spends_badly(frac):
    """Under-spending would flatter us in every comparison."""
    b = RaysenseAllocator(vehicle=VEHICLE).allocate(world(), int(frac * SENSOR.n_rays))
    assert b.n_rays <= int(frac * SENSOR.n_rays) + SENSOR.n_beams
    assert b.fraction > frac * 0.75


def test_produces_a_valid_budget():
    b = RaysenseAllocator(vehicle=VEHICLE).allocate(world(), 5000)
    assert np.unique(b.ray_indices).size == b.n_rays
    assert b.ray_indices.min() >= 0 and b.ray_indices.max() < SENSOR.n_rays


def test_keeps_columns_vertically_dense():
    """The discontinuity test compares adjacent beams inside a column.

    Ray-wise allocation thinned columns to 3.5 beams and the detector went
    quiet; this is the regression test for that.
    """
    scene = offroad_course(seed=7, n_frames=4)
    emap = FixedGridMap(scene.map_config)
    a = RaysenseAllocator(vehicle=VEHICLE)
    b = a.allocate(world(emap, frame=3), int(0.05 * SENSOR.n_rays))

    cols = SENSOR.column_of(b.ray_indices)
    _, counts = np.unique(cols, return_counts=True)

    u = UniformDecimation().allocate(world(), int(0.05 * SENSOR.n_rays))
    _, ucounts = np.unique(SENSOR.column_of(u.ray_indices), return_counts=True)

    assert counts.max() >= ucounts.max()


def test_safety_floor_geometry_is_the_negative_obstacle_one():
    """Ditches bind quadratically, bumps linearly. The floor uses the ditch."""
    a = RaysenseAllocator(vehicle=VEHICLE)
    near, far = a.required_spacing(10.0, 1.8), a.required_spacing(20.0, 1.8)
    assert near / far == pytest.approx(4.0, rel=1e-6)   # quadratic, not linear


def test_braking_distance_and_safe_speed_invert_each_other():
    v = VEHICLE
    d = v.braking_distance(5.0)
    assert v.max_safe_speed(d) == pytest.approx(5.0, rel=1e-6)


def test_slower_vehicles_are_allowed_shorter_sight():
    v = VEHICLE
    assert v.braking_distance(2.0) < v.braking_distance(8.0)
    assert v.max_safe_speed(5.0) < v.max_safe_speed(40.0)


def test_never_worse_covered_than_plain_decimation_by_construction():
    """The guaranteed sweep is a floor under our own cleverness."""
    a = RaysenseAllocator(vehicle=VEHICLE, base_share=0.6)
    b = a.allocate(world(), int(0.1 * SENSOR.n_rays))
    cols = np.unique(SENSOR.column_of(b.ray_indices))
    u = UniformDecimation().allocate(world(), int(0.06 * SENSOR.n_rays))
    ucols = np.unique(SENSOR.column_of(u.ray_indices))
    assert len(cols) >= len(ucols) * 0.9
