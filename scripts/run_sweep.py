#!/usr/bin/env python3
"""Run the budget sweep — the M2 exit criterion.

Raycasts each frame once, replays it through every allocator at every budget,
writes one long-format CSV, and draws the curve from that CSV.

    python scripts/run_sweep.py --frames 40
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from raysense.eval import build_runs, run_sweep, summarise
from raysense.mapping import FixedGridMap
from raysense.sensor import SensorModel
from raysense.sim import SCENES
from raysense.viz import budget_curve, convergence

DEFAULT_FRACTIONS = [0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--allocators", nargs="+", default=["full", "uniform", "random"])
    ap.add_argument("--fractions", nargs="+", type=float, default=DEFAULT_FRACTIONS)
    ap.add_argument("--gt", type=Path, default=Path("cache/gt_offroad_course.npz"))
    ap.add_argument("--csv", type=Path, default=Path("results/m2_sweep.csv"))
    ap.add_argument("--out", type=Path, default=Path("results/m2_budget_curve.png"))
    ap.add_argument("--no-ray-accounting", action="store_true",
                    help="skip the discontinuity test, to measure what it buys")
    ap.add_argument("--absence-test", action="store_true",
                    help="also run the M4 fired-no-answer test (slow, low yield)")
    args = ap.parse_args()

    if not args.gt.exists():
        raise SystemExit(
            f"no ground truth at {args.gt}\n"
            "build it first:  python scripts/build_ground_truth.py"
        )

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    gt = FixedGridMap.load(args.gt)
    runs = build_runs(args.allocators, args.fractions)

    print(f"scene:   {scene.name} seed {scene.seed}, {scene.n_frames} frames")
    print(f"sensor:  {sensor.name}, {sensor.n_rays:,} rays per full scan")
    print(f"truth:   {gt} ({gt.observed().sum():,} observed cells)")
    print(f"runs:    {len(runs)}  ({', '.join(args.allocators)})")
    print(f"absence reasoning: {'off' if args.no_ray_accounting else 'ON'}")

    rows = run_sweep(scene, sensor, gt, runs, seed=args.seed,
                     ray_accounting=not args.no_ray_accounting,
                     absence_test=args.absence_test)

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.csv, index=False)
    print(f"\nwrote {args.csv}  ({len(rows)} rows)\n")
    print(summarise(rows))

    fig = budget_curve(rows, title=f"Budget versus map quality — {scene.name}, "
                                   f"{scene.n_frames} frames")
    fig.savefig(args.out, dpi=130, facecolor=fig.get_facecolor())
    print(f"\nwrote {args.out}")

    conv = args.out.with_name(args.out.stem.replace("budget_curve", "convergence") + ".png")
    convergence(rows).savefig(conv, dpi=130, facecolor=INK_BG)
    print(f"wrote {conv}")
    return 0


INK_BG = "#FCFCFB"

if __name__ == "__main__":
    raise SystemExit(main())
