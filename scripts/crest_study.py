#!/usr/bin/env python3
"""Can a crest occlusion be told apart from a ditch, using only the two returns?

Threshold 3.0 leaves 436 false cells on ditch-free terrain. The suspicion is
that most of them are *crest occlusions*: the ground rises, the far beam clears
the rise and lands well beyond it, and the shadow behind the crest reads as an
unexplained gap. Geometrically that is the same signature as a hole.

The physical asymmetry, if there is one: **a crest occlusion arrives at its near
return uphill.** A ditch on level ground does not. So `rise_before` — the ground
slope from the previous return in the same column to the near return — should
separate the two populations.

This script measures whether it does, rather than assuming it. Positives are
gaps whose span overlaps a planted ditch; negatives are every gap found on the
identical terrain with the ditches removed, which is the control the threshold
sweep already uses.

    python scripts/crest_study.py --frames 40 --fraction 0.05
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from raysense.allocate import BASELINES, WorldState
from raysense.mapping import FixedGridMap
from raysense.raycast import find_discontinuities
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import SCENES, drive, make_terrain

FEATURES = ("ratio", "measured", "predicted", "dz", "rise_before", "horiz_near")


def ditch_mask(scene) -> tuple[np.ndarray, FixedGridMap]:
    """Cells that really are inside a planted negative obstacle."""
    probe = FixedGridMap(scene.map_config)
    X, Y = probe.cell_centres()
    neg = np.zeros(probe.config.shape, dtype=bool)
    for f in scene.terrain.features:
        if f.kind != "negative":
            continue
        if f.label == "crater":
            neg |= np.hypot(X - f.center[0], Y - f.center[1]) <= f.extent[0]
        else:
            neg |= ((np.abs(X - f.center[0]) <= f.extent[1] / 2)
                    & (np.abs(Y - f.center[1]) <= f.extent[0] / 2))
    return neg, probe


def span_hits_ditch(emap, near, far, neg) -> np.ndarray:
    """For each gap, does the ground it skipped over contain a real ditch?"""
    if not len(near):
        return np.zeros(0, dtype=bool)
    seg = far - near
    steps = max(2, int(np.ceil(np.linalg.norm(seg[:, :2], axis=1).max()
                               / emap.config.resolution)) + 1)
    hit = np.zeros(len(near), dtype=bool)
    for s in np.linspace(0.0, 1.0, steps):
        p = near + seg * s
        r, c, inside = emap.world_to_cell(p[:, 0], p[:, 1])
        idx = np.flatnonzero(inside)
        if idx.size:
            hit[idx] |= neg[r[idx], c[idx]]
    return hit


def collect(scene, sensor, alloc_name, fraction, threshold, strip_ditches, neg, probe):
    """Every flagged gap from one traverse, with its geometry and its label."""
    terrain = scene.terrain
    if strip_ditches:
        terrain = make_terrain(size_m=240.0, resolution=0.3, roughness=3.0,
                               seed=scene.seed)
        for f in scene.terrain.features:
            if f.kind == "positive":
                terrain.add_boulder(f.center, f.extent[0], f.depth)

    alloc = BASELINES[alloc_name]()
    budget = int(round(fraction * sensor.n_rays))
    rows = []

    for frame, origin, full in drive(terrain, sensor, scene.path):
        backend = ReplayBackend(full)
        world = WorldState(sensor=sensor, frame=frame, origin=origin)
        scan = backend.acquire(alloc.allocate(world, budget))
        near, far, ratio, d = find_discontinuities(
            scan, sensor, threshold=threshold, details=True)
        if not len(near):
            continue
        label = (np.zeros(len(near), dtype=bool) if strip_ditches
                 else span_hits_ditch(probe, near, far, neg))
        for n in range(len(near)):
            rows.append({
                "control": int(strip_ditches),
                "is_ditch": int(label[n]),
                "ratio": float(ratio[n]),
                "measured": float(d["measured"][n]),
                "predicted": float(d["predicted"][n]),
                "dz": float(d["dz"][n]),
                "rise_before": float(d["rise_before"][n]),
                "horiz_near": float(d["horiz_near"][n]),
                "have_prev": float(d["have_prev"][n]),
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--allocator", default="uniform")
    ap.add_argument("--fraction", type=float, default=0.05)
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--threshold", type=float, default=3.0)
    ap.add_argument("--csv", type=Path, default=Path("results/crest_study.csv"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    neg, probe = ditch_mask(scene)

    print("traverse 1/2 — terrain with ditches")
    rows = collect(scene, sensor, args.allocator, args.fraction, args.threshold,
                   False, neg, probe)
    print("traverse 2/2 — identical terrain, ditches removed (the control)")
    rows += collect(scene, sensor, args.allocator, args.fraction, args.threshold,
                    True, neg, probe)

    df = pd.DataFrame(rows)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.csv, index=False)

    pos = df[(df.control == 0) & (df.is_ditch == 1)]
    ctl = df[df.control == 1]
    print(f"\n{len(pos):,} gaps over a real ditch · {len(ctl):,} gaps on ditch-free "
          f"terrain (the control)\n")

    hdr = f"{'feature':>12} │ {'ditch p10':>10}{'p50':>9}{'p90':>9} │ " \
          f"{'control p10':>12}{'p50':>9}{'p90':>9}"
    print(hdr)
    print("─" * len(hdr))
    for f in FEATURES:
        a, b = pos[f].to_numpy(), ctl[f].to_numpy()
        if not len(a) or not len(b):
            continue
        qa, qb = np.percentile(a, [10, 50, 90]), np.percentile(b, [10, 50, 90])
        print(f"{f:>12} │ {qa[0]:>10.2f}{qa[1]:>9.2f}{qa[2]:>9.2f} │ "
              f"{qb[0]:>12.2f}{qb[1]:>9.2f}{qb[2]:>9.2f}")

    # How much of each population a single cut on rise_before would remove.
    print(f"\n{'reject if rise_before >':>26}{'ditches lost':>15}{'control removed':>18}")
    print("─" * 59)
    for cut in (0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50):
        lost = float((pos.rise_before > cut).mean())
        gone = float((ctl.rise_before > cut).mean())
        print(f"{cut:>26.2f}{lost:>14.1%}{gone:>18.1%}")

    print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
