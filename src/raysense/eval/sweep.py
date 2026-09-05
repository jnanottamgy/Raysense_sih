"""The sweep runner — the most important script in the repository.

It raycasts each frame **once** and replays that single full scan through every
allocator and every budget. So the cost is one raycast per frame regardless of
how many strategies are being compared, and — more importantly — every strategy
sees numerically identical ground truth. Any difference in the results is the
allocation, and nothing else.

Output is one long-format table. Every chart and every figure downstream is a
groupby on it; nothing is ever typed in by hand.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from raysense.allocate import BASELINES, WorldState
from raysense.eval.metrics import (
    corridor_recall,
    distance_to_path,
    elevation_metrics,
    feature_recall,
    traversability_metrics,
)
from raysense.mapping import FixedGridMap
from raysense.perceive import classify, feature_masks, true_traversability
from raysense.raycast import integrate_rays, mark_discontinuities
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import drive
from raysense.types import CellState


@dataclass(frozen=True)
class Run:
    """One cell of the sweep: a strategy at a budget."""

    allocator: str
    fraction: float

    @property
    def label(self) -> str:
        return f"{self.allocator}@{self.fraction:.3f}"


def build_runs(allocators: list[str], fractions: list[float]) -> list[Run]:
    """Cross allocators with budgets, dropping the combinations that make no sense."""
    runs: list[Run] = []
    for name in allocators:
        if name == "full":
            runs.append(Run("full", 1.0))       # the ceiling has exactly one budget
            continue
        for f in fractions:
            runs.append(Run(name, float(f)))
    return runs


def run_sweep(
    scene,
    sensor: SensorModel,
    gt: FixedGridMap,
    runs: list[Run],
    record_every: int = 5,
    seed: int = 0,
    ray_accounting: bool = True,
    absence_test: bool = False,
    verbose: bool = True,
) -> list[dict]:
    """Drive the scene once, replay it through every run, return metric rows."""
    n_native = sensor.n_rays

    # Truth comes from the terrain itself, not from what any scan managed to
    # see — otherwise every strategy scores perfectly on the ditches nobody
    # ever observed. Computed once; it does not change.
    probe = FixedGridMap(scene.map_config)
    truth_trav = true_traversability(probe, scene)
    masks = feature_masks(probe, scene)
    path_dist = distance_to_path(probe, scene.path)

    # Per-feature masks, for measuring *when* each hazard is first flagged.
    # How far away a ditch is when you first notice it is the operational
    # question; whole-run recall cannot answer it.
    X, Y = probe.cell_centres()
    hazards = []
    for f in scene.terrain.features:
        if f.kind != "negative":
            continue
        if f.label == "crater":
            fm = np.hypot(X - f.center[0], Y - f.center[1]) <= f.extent[0]
        else:
            fm = ((np.abs(X - f.center[0]) <= f.extent[1] / 2)
                  & (np.abs(Y - f.center[1]) <= f.extent[0] / 2))
        hazards.append((f.label, np.asarray(f.center), fm))

    maps = {r: FixedGridMap(scene.map_config) for r in runs}
    allocs = {
        r: (BASELINES[r.allocator](seed=seed)
            if r.allocator == "random" else BASELINES[r.allocator]())
        for r in runs
    }
    stats = {r: {"rays": 0, "returns": 0, "seconds": 0.0, "candidates": 0} for r in runs}

    rows: list[dict] = []
    detections: list[dict] = []
    first_seen = {(r, h[0], i): None for r in runs for i, h in enumerate(hazards)}
    t_start = time.perf_counter()

    for frame, origin, full_scan in drive(scene.terrain, sensor, scene.path):
        backend = ReplayBackend(full_scan)

        for r in runs:
            world = WorldState(sensor=sensor, frame=frame, origin=origin,
                               emap=maps[r], speed=getattr(scene, "speed", 4.0))
            t0 = time.perf_counter()
            budget = allocs[r].allocate(world, int(round(r.fraction * n_native)))
            scan = backend.acquire(budget)
            maps[r].integrate(scan.points, frame=frame)
            if ray_accounting:
                # Signature B: gaps in the ground returns that geometry cannot
                # explain. This is the one that finds stepped-over ditches.
                stats[r]["candidates"] += mark_discontinuities(
                    maps[r], scan, sensor, frame=frame
                )
            if absence_test:
                # Signature A: fired, no answer. Cheap to keep, but M4 showed
                # it fires on almost none of the ditches that matter.
                integrate_rays(maps[r], scan, frame=frame)
            stats[r]["seconds"] += time.perf_counter() - t0
            stats[r]["rays"] += scan.n_fired
            stats[r]["returns"] += scan.n_returns

        # when was each hazard first flagged, and how far off was it then?
        for r in runs:
            state = maps[r].state
            for i, (label, centre, fm) in enumerate(hazards):
                key = (r, label, i)
                if first_seen[key] is not None:
                    continue
                if ((state[fm] & int(CellState.CANDIDATE_NEGATIVE)) != 0).any():
                    dist = float(np.hypot(*(centre - origin[:2])))
                    first_seen[key] = frame
                    detections.append({
                        "allocator": r.allocator, "fraction": r.fraction,
                        "hazard": label, "hazard_index": i,
                        "frame": frame, "detection_range_m": dist,
                        "lead_time_s": dist / max(0.1, getattr(scene, "speed", 4.0)),
                    })

        last = frame == scene.n_frames - 1
        if frame % record_every == 0 or last:
            for r in runs:
                s = stats[r]
                est_trav = classify(maps[r])
                rows.append({
                    "scene": scene.name,
                    "seed": scene.seed,
                    "allocator": r.allocator,
                    "fraction": r.fraction,
                    "frame": frame,
                    "final": last,
                    "rays_fired": s["rays"],
                    "returns": s["returns"],
                    "rays_per_frame": s["rays"] / (frame + 1),
                    "ray_accounting": ray_accounting,
                    "candidates_flagged": s["candidates"],
                    # what it actually spent. Integer strides mean uniform
                    # decimation cannot hit an arbitrary budget, so the
                    # requested fraction is not always the delivered one.
                    "achieved_fraction": s["rays"] / ((frame + 1) * n_native),
                    "ms_per_frame": 1e3 * s["seconds"] / (frame + 1),
                    **elevation_metrics(maps[r], gt),
                    **traversability_metrics(est_trav, truth_trav),
                    **feature_recall(est_trav, masks),
                    **corridor_recall(est_trav, masks, path_dist, half_width=12.0),
                })
        if verbose and (frame % 10 == 0 or last):
            print(f"  frame {frame:3d}/{scene.n_frames}  "
                  f"({time.perf_counter() - t_start:5.1f}s)")

    if verbose:
        print(f"  sweep done in {time.perf_counter() - t_start:.1f}s "
              f"({len(runs)} runs x {scene.n_frames} frames)")
    for r in runs:
        for i, (label, _c, _m) in enumerate(hazards):
            if first_seen[(r, label, i)] is None:
                detections.append({
                    "allocator": r.allocator, "fraction": r.fraction,
                    "hazard": label, "hazard_index": i,
                    "frame": -1, "detection_range_m": float("nan"),
                    "lead_time_s": float("nan"),
                })
    return rows, detections


def final_table(rows: list[dict]) -> list[dict]:
    """Just the last frame of each run — the headline numbers."""
    return [r for r in rows if r["final"]]


def summarise(rows: list[dict]) -> str:
    """A compact text report, for the terminal and for commit messages."""
    finals = sorted(final_table(rows), key=lambda r: (r["allocator"], r["fraction"]))
    out = [
        f"{'allocator':<10}{'spent':>7}{'cover':>7}{'neg.det':>9}{'pos.det':>9}"
        f"{'CORRIDOR neg':>14}{'corr.unsafe':>13}{'ms/fr':>7}",
        "-" * 76,
    ]
    for r in finals:
        out.append(
            f"{r['allocator']:<10}{r['achieved_fraction']:>6.1%}"
            f"{r['coverage_recall']:>7.0%}{r['negative_detected']:>9.1%}"
            f"{r['positive_detected']:>9.1%}"
            f"{r['corridor_negative_detected']:>14.1%}"
            f"{r['corridor_negative_missed_unsafe']:>13.2%}{r['ms_per_frame']:>7.1f}"
        )
    return "\n".join(out)
