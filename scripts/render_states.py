#!/usr/bin/env python3
"""Render the ray-accounting state map — the M4 exit visual.

    python scripts/render_states.py --frames 40 --fraction 0.2
"""

from __future__ import annotations

import argparse
from pathlib import Path

from raysense.allocate import BASELINES, WorldState
from raysense.mapping import FixedGridMap
from raysense.perceive import Traversability, classify, feature_masks, true_traversability
from raysense.raycast import integrate_rays
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import SCENES, drive
from raysense.viz import render_states


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--allocator", default="uniform", choices=sorted(BASELINES))
    ap.add_argument("--fraction", type=float, default=1.0)
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-ray-accounting", action="store_true")
    ap.add_argument("--out", type=Path, default=Path("results/m4_states.png"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    alloc = BASELINES[args.allocator]()
    emap = FixedGridMap(scene.map_config)
    budget_rays = int(round(args.fraction * sensor.n_rays))

    for frame, origin, full in drive(scene.terrain, sensor, scene.path):
        backend = ReplayBackend(full)
        world = WorldState(sensor=sensor, frame=frame, origin=origin, emap=emap)
        scan = backend.acquire(alloc.allocate(world, budget_rays))
        emap.integrate(scan.points, frame=frame)
        if not args.no_ray_accounting:
            integrate_rays(emap, scan, frame=frame)
        if frame % 10 == 0:
            print(f"  frame {frame:3d}/{scene.n_frames}")

    trav = classify(emap)
    truth = true_traversability(emap, scene)
    neg = feature_masks(emap, scene)["negative"]
    det = (trav[neg] == int(Traversability.BLOCKED)).mean()
    unk = (trav[neg] == int(Traversability.UNKNOWN)).mean()
    unsafe = (trav[neg] == int(Traversability.TRAVERSABLE)).mean()
    hazard = truth == int(Traversability.BLOCKED)
    print(f"\nnegative obstacles: {det:.1%} flagged blocked, "
          f"{unk:.1%} admitted unknown, {unsafe:.2%} waved through")
    unsafe_all = (trav[hazard] == int(Traversability.TRAVERSABLE)).mean()
    print(f"all hazards:        {unsafe_all:.2%} waved through")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mode = "off" if args.no_ray_accounting else "on"
    fig = render_states(
        emap, terrain=scene.terrain,
        title=f"Ray accounting {mode} — {args.allocator} at {args.fraction:.0%} budget",
    )
    fig.savefig(args.out, dpi=130, facecolor=fig.get_facecolor())
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
