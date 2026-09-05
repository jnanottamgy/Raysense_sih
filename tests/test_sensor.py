"""Sensor geometry, including the safety floor the whole method rests on."""

import numpy as np
import pytest

from raysense.sensor import SensorModel

SENSOR = "configs/sensor/ouster_os1_64.yaml"


def test_loads_from_yaml():
    s = SensorModel.from_yaml(SENSOR)
    assert s.name == "ouster_os1_64"
    assert s.n_rays == s.n_beams * s.n_azimuth


def test_min_detectable_height_matches_closed_form():
    """h_min(r) = r * dtheta — geometry, not a tuned constant."""
    s = SensorModel.from_yaml(SENSOR)
    for r in (5.0, 20.0, 80.0):
        assert s.min_detectable_height(r) == pytest.approx(r * s.delta_theta_v)


def test_required_delta_theta_inverts_min_detectable_height():
    s = SensorModel.from_yaml(SENSOR)
    r, h = 40.0, 0.35
    dt = s.required_delta_theta(h, r)
    assert s.min_detectable_height(r, delta_theta=dt) == pytest.approx(h)


def test_max_safe_range_inverts_too():
    s = SensorModel.from_yaml(SENSOR)
    h = 0.2
    r = s.max_safe_range(h)
    assert s.min_detectable_height(r) == pytest.approx(h)


def test_required_delta_theta_rejects_nonpositive_range():
    with pytest.raises(ValueError, match="must be positive"):
        SensorModel.from_yaml(SENSOR).required_delta_theta(0.2, 0.0)


def test_ray_grid_indexing_round_trips():
    s = SensorModel.from_yaml(SENSOR)
    g = s.full_ray_grid()
    assert g.n_rays == s.n_rays
    idx = np.array([0, 1, s.n_azimuth, s.n_rays - 1])
    assert np.array_equal(
        s.beam_of(idx) * s.n_azimuth + s.column_of(idx), idx
    )


def test_full_grid_spans_the_stated_field_of_view():
    s = SensorModel.from_yaml(SENSOR)
    g = s.full_ray_grid()
    assert np.rad2deg(g.elevation.min()) == pytest.approx(s.v_fov_min_deg)
    assert np.rad2deg(g.elevation.max()) == pytest.approx(s.v_fov_max_deg)
