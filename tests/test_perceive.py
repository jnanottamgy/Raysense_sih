"""Traversability — and the invariant the whole project's safety case rests on."""

import numpy as np
import pytest

from raysense.mapping import FixedGridMap, MapConfig
from raysense.perceive import (
    Traversability,
    TraversabilityConfig,
    classify,
    feature_masks,
    true_traversability,
)
from raysense.sim import offroad_course
from raysense.types import CellState

CFG = MapConfig(resolution=0.4, size_m=24.0, origin=(-12.0, -12.0))


def flat_map(z=0.0, n_per_cell=3):
    """A map fully observed with a level surface."""
    m = FixedGridMap(CFG)
    X, Y = m.cell_centres()
    pts = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, z)])
    for _ in range(n_per_cell):
        m.integrate(pts)
    return m


# --------------------------------------------------------------- the invariant


def test_unknown_never_becomes_traversable():
    """The property test named in the build plan as M4's exit criterion.

    Across empty maps, partial maps and fully observed ones, a cell that was
    never observed must never come back as drivable. There is no threshold, no
    smoothing and no interpolation that is allowed to fill that in.
    """
    rng = np.random.default_rng(0)
    for trial in range(25):
        m = FixedGridMap(CFG)
        k = int(rng.integers(0, 400))
        if k:
            m.integrate(np.column_stack([
                rng.uniform(-11, 11, k), rng.uniform(-11, 11, k), rng.normal(0, 0.4, k),
            ]))
        out = classify(m)
        unseen = ~m.observed()
        assert not (out[unseen] == int(Traversability.TRAVERSABLE)).any(), (
            f"trial {trial}: an unobserved cell was reported as drivable"
        )
        assert (out[unseen] == int(Traversability.UNKNOWN)).all()


def test_candidate_negative_is_never_traversable():
    """A suspected ditch outranks a comfortable-looking surface."""
    m = flat_map()
    m.state[10:14, 10:14] |= int(CellState.CANDIDATE_NEGATIVE)
    out = classify(m)
    assert (out[10:14, 10:14] == int(Traversability.BLOCKED)).all()
    # ... and the identical geometry elsewhere is still fine
    assert out[30, 30] == int(Traversability.TRAVERSABLE)


# ------------------------------------------------------------------- geometry


def test_fresh_map_is_entirely_unknown():
    assert (classify(FixedGridMap(CFG)) == int(Traversability.UNKNOWN)).all()


def test_level_ground_is_traversable():
    out = classify(flat_map())
    assert (out == int(Traversability.TRAVERSABLE)).mean() > 0.9


def test_a_step_blocks():
    m = flat_map()
    X, Y = m.cell_centres()
    tall = (np.abs(X) < 1.0) & (np.abs(Y) < 1.0)
    m.integrate(np.column_stack([X[tall], Y[tall], np.full(tall.sum(), 1.5)]))
    out = classify(m)
    assert (out[tall] == int(Traversability.BLOCKED)).any()


def test_within_cell_spread_reads_as_roughness():
    m = FixedGridMap(CFG)
    X, Y = m.cell_centres()
    base = np.column_stack([X.ravel(), Y.ravel(), np.zeros(X.size)])
    m.integrate(base)
    rough = base.copy()
    rough[:, 2] = 1.0
    m.integrate(rough)
    cfg = TraversabilityConfig(max_step=99, max_slope=99, max_roughness=0.05)
    assert (classify(m, cfg) == int(Traversability.BLOCKED)).mean() > 0.9


# ---------------------------------------------------------------------- truth


def test_planted_ditches_are_blocked_in_the_truth_map():
    """Truth comes from the terrain, so it knows about ditches no scan saw."""
    scene = offroad_course(seed=7, n_frames=4)
    m = FixedGridMap(scene.map_config)
    truth = true_traversability(m, scene)
    neg = feature_masks(m, scene)["negative"]
    assert neg.any()
    assert (truth[neg] == int(Traversability.BLOCKED)).all()


def test_truth_map_admits_no_unknowns_inside_the_world():
    scene = offroad_course(seed=7, n_frames=4)
    m = FixedGridMap(scene.map_config)
    truth = true_traversability(m, scene)
    assert (truth != int(Traversability.UNKNOWN)).mean() > 0.99


def test_feature_masks_separate_the_two_kinds():
    scene = offroad_course(seed=7, n_frames=4)
    masks = feature_masks(FixedGridMap(scene.map_config), scene)
    assert masks["negative"].sum() > 0
    assert masks["positive"].sum() > 0
    assert not (masks["negative"] & masks["positive"]).any()


def test_rejects_nothing_silently_on_an_all_nan_map():
    m = FixedGridMap(CFG)
    out = classify(m)
    assert out.shape == CFG.shape
    assert out.dtype == np.int8


@pytest.mark.parametrize("value", list(Traversability))
def test_traversability_values_are_distinct(value):
    assert list(Traversability).count(value) == 1
