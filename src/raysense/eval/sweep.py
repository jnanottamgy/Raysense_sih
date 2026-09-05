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
from raysense.eval.metrics import elevation_metrics
from raysense.mapping import FixedGridMap
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
    verbose: bool = True,
) -> list[dict]:
    """Drive the scene once, replay it through every run, return metric rows."""
    n_native = sensor.n_rays

    maps = {r: FixedGridMap(scene.map_config) for r in runs}
    allocs = {
        r: (BASELINES[r.allocator](seed=seed)
            if r.allocator == "random" else BASELINES[r.allocator]())
        for r in runs
    }
    stats = {r: {"rays": 0, "returns": 0, "seconds": 0.0} for r in runs}

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
            stats[r]["seconds"] += time.perf_counter() - t0
            stats[r]["rays"] += scan.n_fired
            stats[r]["returns"] += scan.n_returns

        last = frame == scene.n_frames - 1
        if frame % record_every == 0 or last:
            for r in runs:
                s = stats[r]
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
                    # what it actually spent. Integer strides mean uniform
                    # decimation cannot hit an arbitrary budget, so the
                    # requested fraction is not always the delivered one.
                    "achieved_fraction": s["rays"] / ((frame + 1) * n_native),
                    "ms_per_frame": 1e3 * s["seconds"] / (frame + 1),
                    **elevation_metrics(maps[r], gt),
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
        f"{'allocator':<10}{'asked':>7}{'spent':>8}{'rays/frame':>12}"
        f"{'RMSE m':>9}{'coverage':>10}{'ms/frame':>10}",
        "-" * 66,
    ]
    for r in finals:
        out.append(
            f"{r['allocator']:<10}{r['fraction']:>6.1%}{r['achieved_fraction']:>8.1%}"
            f"{r['rays_per_frame']:>12,.0f}{r['elev_rmse']:>9.3f}"
            f"{r['coverage_recall']:>9.1%}{r['ms_per_frame']:>10.1f}"
        )
    return "\n".join(out)
