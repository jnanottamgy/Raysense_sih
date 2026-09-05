#!/usr/bin/env python3
"""Build and cache the full-scan ground-truth map — the M1 exit criterion.

Every later comparison is scored against this map, so it is computed once from
complete scans and cached. Rebuilding it on every sweep would dominate the
run time and, worse, invite it to drift.

    python scripts/build_ground_truth.py --frames 40
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from raysense.mapping import FixedGridMap
from raysense.sensor import SensorModel
from raysense.sim import SCENES, drive
from raysense.viz import render_map


def build(scene, sensor: SensorModel, cache: Path, force: bool = False):
    """Accumulate every return from every full scan into one world-frame map."""
    if cache.exists() and not force:
        print(f"cache hit: {cache}")
        return FixedGridMap.load(cache), None

    emap = FixedGridMap(scene.map_config)
    scans = []
    t0 = time.perf_counter()
    for frame, _origin, scan in drive(scene.terrain, sensor, scene.path):
        emap.integrate(scan.points, frame=frame)
        scans.append(scan)
        if frame % 10 == 0 or frame == scene.n_frames - 1:
            print(f"  frame {frame:3d}/{scene.n_frames}  "
                  f"{scan.n_returns:6,} returns  coverage {emap.coverage:.1%}")
    print(f"  built in {time.perf_counter() - t0:.1f}s")
    emap.save(cache)
    print(f"  cached -> {cache}")
    return emap, scans


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cache", type=Path, default=Path("cache/gt_offroad_course.npz"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", type=Path, default=Path("results/m1_ground_truth.png"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    print(f"scene: {scene.name} seed {scene.seed}, {scene.n_frames} frames, "
          f"{len(scene.terrain.features)} planted features")
    print(f"map:   {scene.map_config.shape} @ {scene.map_config.resolution} m")

    emap, _ = build(scene, sensor, args.cache, force=args.force)
    print(f"\n{emap}")
    obs = emap.observed()
    print(f"observed cells: {obs.sum():,} / {obs.size:,}")
    print(f"returns per observed cell: median {np.median(emap.n_obs[obs]):.0f}, "
          f"max {emap.n_obs.max():,}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig = render_map(emap, terrain=scene.terrain, path=scene.path,
                     title=f"Ground truth — {scene.name} ({scene.n_frames} full scans)")
    fig.savefig(args.out, dpi=130, facecolor=fig.get_facecolor())
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
