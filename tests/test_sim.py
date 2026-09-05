"""Terrain sampling and the raycaster, checked against closed-form geometry."""

import numpy as np

from raysense.sim import Terrain, make_terrain
from raysense.types import RayGrid


def flat_terrain(size=200, res=0.5):
    n = int(size / res)
    return Terrain(height=np.zeros((n, n)), resolution=res, origin=(-size / 2, -size / 2))


def down_rays(origin, elevations_deg, max_range=150.0):
    el = np.deg2rad(np.asarray(elevations_deg, dtype=float))
    return RayGrid(
        azimuth=np.zeros_like(el), elevation=el,
        origin=np.asarray(origin, dtype=float), max_range=max_range,
        beam_index=np.arange(el.size),
    )


def test_sample_returns_nan_outside_the_world():
    """A ray leaving the map must return nothing, never a clamped edge hit."""
    t = flat_terrain()
    assert np.isnan(t.sample(np.array(1e6), np.array(0.0)))
    assert np.isfinite(t.sample(np.array(0.0), np.array(0.0)))


def test_flat_ground_range_matches_h_over_sin_theta():
    """On a flat plane a beam at depression theta returns at h / sin(theta)."""
    h = 2.0
    t = flat_terrain()
    angles = np.array([-30.0, -20.0, -10.0, -5.0])
    scan = t.raycast(down_rays([0, 0, h], angles), step=0.2, refine=16)

    assert scan.n_returns == len(angles)
    got = np.linalg.norm(scan.points - scan.fired.origin, axis=1)
    want = h / np.sin(np.deg2rad(-angles))
    assert np.allclose(got, want, rtol=2e-3)


def test_upward_rays_return_nothing():
    t = flat_terrain()
    scan = t.raycast(down_rays([0, 0, 2.0], [5.0, 15.0, 30.0]))
    assert scan.n_returns == 0
    assert scan.empty_rays().n_rays == 3


def test_trench_interior_is_never_observed():
    """The premise of the project, as an executable check.

    Identical rays over identical terrain, with and without a trench carved in.
    The rays that would have sampled that patch of ground now sail over it and
    land beyond, so the trench interior receives no returns at all. The ditch
    is not seen dimly — it is not seen.
    """
    rays = down_rays([0, 0, 1.8], np.linspace(-14, -4, 200))
    x0, x1 = 16.8, 19.2      # the trench footprint in x

    def inside(scan):
        p = scan.points
        return int(((p[:, 0] > x0) & (p[:, 0] < x1)).sum())

    flat = flat_terrain()
    dug = flat_terrain()
    dug.add_trench(center=(18.0, 0.0), length=20.0, width=2.4, depth=2.0, angle_deg=90.0)

    before = inside(flat.raycast(rays, step=0.2, refine=12))
    after = inside(dug.raycast(rays, step=0.2, refine=12))

    assert before > 0, "flat ground should be sampled there — otherwise this proves nothing"
    assert after == 0, "the trench interior must receive no returns"


def test_deep_trench_can_destroy_returns_entirely():
    """A negative obstacle does not always announce itself with a long return.

    When the floor lies beyond the sensor's reach, the rays simply never come
    back. The scan then holds no point at all where the ground used to be —
    which is indistinguishable, from the returns alone, from never having
    looked. Hence the ray-level accounting at M4.
    """
    rays = down_rays([0, 0, 1.8], np.linspace(-6.0, -4.5, 60), max_range=40.0)

    flat = flat_terrain(size=400)
    deep = flat_terrain(size=400)
    deep.add_trench(center=(60.0, 0.0), length=80.0, width=90.0, depth=6.0, angle_deg=90.0)

    on_flat = flat.raycast(rays, step=0.2, refine=12)
    in_ditch = deep.raycast(rays, step=0.2, refine=12)

    assert on_flat.n_returns == 60
    assert in_ditch.n_returns == 0
    # and every one of those rays is still on record as having been fired
    assert in_ditch.empty_rays().n_rays == 60


def test_planted_features_carry_exact_ground_truth():
    t = make_terrain(size_m=60, resolution=0.5, seed=1)
    tr = t.add_trench((10, 0), length=8, width=2, depth=1.5)
    bo = t.add_boulder((-8, 4), radius=1.5, height=1.0)

    assert tr.kind == "negative" and bo.kind == "positive"
    assert t.feature_at(np.array(10.0), np.array(0.0)) == tr.id
    assert t.feature_at(np.array(-8.0), np.array(4.0)) == bo.id
    assert t.feature_at(np.array(25.0), np.array(25.0)) == 0


def test_returns_never_exceed_max_range():
    t = make_terrain(size_m=200, resolution=0.5, roughness=1.0, seed=3)
    rays = down_rays([0, 0, 1.8], np.linspace(-25, -0.5, 300), max_range=40.0)
    scan = t.raycast(rays)
    r = np.linalg.norm(scan.points - scan.fired.origin, axis=1)
    assert r.size and r.max() <= 40.0 + 1e-6


def test_raycast_preserves_every_fired_ray():
    t = make_terrain(size_m=80, resolution=0.5, seed=2)
    rays = down_rays([0, 0, 1.8], np.linspace(-30, 10, 120))
    scan = t.raycast(rays)
    assert scan.n_fired == 120
    assert scan.n_returns + scan.empty_rays().n_rays == 120
