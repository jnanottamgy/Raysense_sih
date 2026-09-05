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

from raysense.allocate import BASELINES, WorldState
from raysense.eval.metrics import elevation_metrics, feature_recall, traversability_metrics
from raysense.mapping import FixedGridMap
from raysense.perceive import classify, feature_masks, true_traversability
from raysense.raycast import integrate_rays
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import drive


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

    maps = {r: FixedGridMap(scene.map_config) for r in runs}
    allocs = {
        r: (BASELINES[r.allocator](seed=seed)
            if r.allocator == "random" else BASELINES[r.allocator]())
        for r in runs
    }
    stats = {r: {"rays": 0, "returns": 0, "seconds": 0.0, "candidates": 0} for r in runs}

    rows: list[dict] = []
    t_start = time.perf_counter()

    for frame, origin, full_scan in drive(scene.terrain, sensor, scene.path):
        backend = ReplayBackend(full_scan)

        for r in runs:
            world = WorldState(sensor=sensor, frame=frame, origin=origin, emap=maps[r])
            t0 = time.perf_counter()
            budget = allocs[r].allocate(world, int(round(r.fraction * n_native)))
            scan = backend.acquire(budget)
            maps[r].integrate(scan.points, frame=frame)
            if ray_accounting:
                tally = integrate_rays(maps[r], scan, frame=frame)
                stats[r]["candidates"] += tally["candidate_negative"]
            stats[r]["seconds"] += time.perf_counter() - t0
            stats[r]["rays"] += scan.n_fired
            stats[r]["returns"] += scan.n_returns

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
                })
        if verbose and (frame % 10 == 0 or last):
            print(f"  frame {frame:3d}/{scene.n_frames}  "
                  f"({time.perf_counter() - t_start:5.1f}s)")

    if verbose:
        print(f"  sweep done in {time.perf_counter() - t_start:.1f}s "
              f"({len(runs)} runs x {scene.n_frames} frames)")
    return rows


def final_table(rows: list[dict]) -> list[dict]:
    """Just the last frame of each run — the headline numbers."""
    return [r for r in rows if r["final"]]


def summarise(rows: list[dict]) -> str:
    """A compact text report, for the terminal and for commit messages."""
    finals = sorted(final_table(rows), key=lambda r: (r["allocator"], r["fraction"]))
    out = [
        f"{'allocator':<10}{'spent':>7}{'cover':>7}{'haz.det':>9}{'haz.unk':>9}"
        f"{'UNSAFE':>8}{'neg.det':>9}{'pos.det':>9}{'ms/fr':>7}",
        "-" * 75,
    ]
    for r in finals:
        out.append(
            f"{r['allocator']:<10}{r['achieved_fraction']:>6.1%}"
            f"{r['coverage_recall']:>7.0%}{r['trav_recall']:>9.1%}"
            f"{r['unknown_on_hazard']:>9.1%}{r['unsafe_rate']:>8.2%}"
            f"{r['negative_detected']:>9.1%}{r['positive_detected']:>9.1%}"
            f"{r['ms_per_frame']:>7.1f}"
        )
    return "\n".join(out)
