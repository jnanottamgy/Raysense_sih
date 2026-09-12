#!/usr/bin/env python3
"""Per-frame cost of the perception pipeline, measured rather than estimated.

Run it anywhere — a laptop, a workstation, a Jetson — with the same command:

    python scripts/benchmark.py --label "Jetson Orin Nano 8GB"

WHAT IS TIMED, AND WHAT IS NOT
------------------------------
Timed: the four stages a vehicle would actually run per frame —

    allocate   decide which rays to spend this frame
    acquire    take those rays from the sensor
    integrate  fold the returns into the 2.5D map
    detect     the range-normalised gap test  (the contribution)

NOT timed: generating the scan. In this harness a simulated raycast stands in
for the sensor, and on a real vehicle the sensor produces that for free. Timing
it would measure our simulator, not our system. `eval/sweep.py` draws the same
line, so the numbers here and there are comparable.

The absence test (`integrate_rays`, the M4 ray march) is measured separately
under --absence, because it is the method our detector replaces and the
comparison is the point.

Nothing here is extrapolated. If you want a number for a device, run it on the
device; that is the whole reason this script takes a --label.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from raysense.allocate import BASELINES, WorldState
from raysense.mapping import FixedGridMap
from raysense.raycast import integrate_rays, mark_discontinuities
from raysense.sensor import SensorModel
from raysense.sensor.backends import ReplayBackend
from raysense.sim import SCENES
from raysense.sim.terrain import drive

STAGES = ("allocate", "acquire", "integrate", "detect")


def host_info() -> dict:
    """Whatever identifies the machine a number came from."""
    cpu = platform.processor() or platform.machine()
    try:                                    # Linux gives a real model name
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith(("model name", "Model")):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    try:
        cores = len(os.sched_getaffinity(0))
    except AttributeError:
        cores = os.cpu_count()
    return {
        "cpu": cpu,
        "cores_available": cores,
        "machine": platform.machine(),
        "system": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "numpy": np.__version__,
    }


def time_frames(scans, sensor, scene, fraction: int | float, allocator: str,
                absence: bool) -> dict[str, list[float]]:
    """One pass over every frame. Returns per-stage millisecond lists."""
    emap = FixedGridMap(scene.map_config)
    alloc = BASELINES[allocator]()
    n_native = sensor.n_rays
    n_rays = int(round(fraction * n_native))
    per: dict[str, list[float]] = {s: [] for s in STAGES}
    if absence:
        per["absence"] = []

    for frame, origin, full_scan in scans:
        backend = ReplayBackend(full_scan)
        world = WorldState(sensor=sensor, frame=frame, origin=origin,
                           emap=emap, speed=4.0)

        t = time.perf_counter()
        budget = alloc.allocate(world, n_rays)
        per["allocate"].append((time.perf_counter() - t) * 1e3)

        t = time.perf_counter()
        scan = backend.acquire(budget)
        per["acquire"].append((time.perf_counter() - t) * 1e3)

        t = time.perf_counter()
        emap.integrate(scan.points, frame=frame)
        per["integrate"].append((time.perf_counter() - t) * 1e3)

        t = time.perf_counter()
        mark_discontinuities(emap, scan, sensor, frame=frame)
        per["detect"].append((time.perf_counter() - t) * 1e3)

        if absence:
            t = time.perf_counter()
            integrate_rays(emap, scan, frame=frame)
            per["absence"].append((time.perf_counter() - t) * 1e3)

    return per


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", default=None,
                    help='name this machine, e.g. "Jetson Orin Nano 8GB"')
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=5,
                    help="passes over every frame; the median is reported")
    ap.add_argument("--fractions", nargs="+", type=float,
                    default=[0.02, 0.05, 0.10, 0.50, 1.00])
    ap.add_argument("--allocator", default="uniform", choices=sorted(BASELINES))
    ap.add_argument("--absence", action="store_true",
                    help="also time the M4 absence test, the method we replace")
    ap.add_argument("--csv", type=Path, default=Path("results/benchmark.csv"))
    args = ap.parse_args()

    host = host_info()
    label = args.label or host["cpu"]

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=7, n_frames=args.frames)

    print(f"device      {label}")
    print(f"cpu         {host['cpu']}  ({host['cores_available']} cores visible)")
    print(f"platform    {host['system']} · {host['machine']} · "
          f"python {host['python']} · numpy {host['numpy']}")
    print(f"sensor      {sensor.name}  {sensor.n_beams}x{sensor.n_azimuth} "
          f"= {sensor.n_rays:,} rays/scan")
    print(f"workload    {args.frames} frames x {args.repeats} repeats, "
          f"allocator={args.allocator}\n")

    # Generating the scans is the simulator standing in for the sensor. It is
    # deliberately outside every timer, so it runs once, here.
    print("building scans (not timed — this is the sensor's job on a vehicle) ...",
          end=" ", flush=True)
    t0 = time.perf_counter()
    scans = list(drive(scene.terrain, sensor, scene.path))
    print(f"{time.perf_counter() - t0:.1f}s, {len(scans)} frames\n")

    head = f"{'budget':>7} {'rays':>8} │ " + " ".join(f"{s:>10}" for s in STAGES)
    if args.absence:
        head += f" {'absence':>10}"
    head += f" │ {'TOTAL':>9} {'p95':>8}"
    print(head)
    print("─" * len(head))

    rows = []
    for frac in args.fractions:
        acc: dict[str, list[float]] = {}
        totals: list[float] = []
        for _ in range(args.repeats):
            per = time_frames(scans, sensor, scene, frac, args.allocator, args.absence)
            for k, v in per.items():
                acc.setdefault(k, []).extend(v)
            # per-frame total of the stages a vehicle must run
            totals.extend(np.sum([per[s] for s in STAGES], axis=0).tolist())

        med = {k: statistics.median(v) for k, v in acc.items()}
        total_med = statistics.median(totals)
        p95 = float(np.percentile(totals, 95))
        n_rays = int(round(frac * sensor.n_rays))

        line = f"{frac:>6.0%} {n_rays:>8,} │ " + " ".join(
            f"{med[s]:>9.2f}m" for s in STAGES)
        if args.absence:
            line += f" {med['absence']:>9.2f}m"
        line += f" │ {total_med:>8.2f}m {p95:>7.2f}m"
        print(line)

        row = {"device": label, "budget": frac, "rays": n_rays,
               "total_ms_median": round(total_med, 3), "total_ms_p95": round(p95, 3),
               **{f"{s}_ms_median": round(med[s], 3) for s in STAGES}}
        if args.absence:
            row["absence_ms_median"] = round(med["absence"], 3)
        row.update({"frames": args.frames, "repeats": args.repeats,
                    "allocator": args.allocator, "sensor": sensor.name,
                    "n_rays_native": sensor.n_rays, **host})
        rows.append(row)

    # How the cost scales with rays — the only principled basis for saying
    # anything about a machine you have not run on.
    x = np.array([r["rays"] for r in rows], dtype=float)
    y = np.array([r["total_ms_median"] for r in rows], dtype=float)
    var = float(((y - y.mean()) ** 2).sum())
    if len(rows) >= 3 and var > 0:
        slope, intercept = np.polyfit(x, y, 1)
        resid = y - (slope * x + intercept)
        r2 = 1.0 - float(resid @ resid) / var
        print(f"\nscaling     {slope * 1e3:.4f} µs per ray + {intercept:.2f} ms fixed "
              f"(linear fit, R² = {r2:.4f})")
    else:
        print("\nscaling     needs >= 3 budgets to fit; pass more --fractions")

    hz = sensor.frame_rate_hz
    budget_ms = 1000.0 / hz
    at5 = next((r for r in rows if abs(r["budget"] - 0.05) < 1e-9), rows[0])
    print(f"headroom    {at5['total_ms_median']:.1f} ms at a 5% budget against a "
          f"{budget_ms:.0f} ms frame at {hz:.0f} Hz "
          f"— {budget_ms / at5['total_ms_median']:.0f}x")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote       {args.csv}")
    print(f"host        {json.dumps(host)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
