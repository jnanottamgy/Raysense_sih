#!/usr/bin/env python3
"""What does candidate precision actually cost?

With the crest guard on, only 5 cells flag on ditch-free terrain — so the
remaining imprecision is not phantom hazards. It is the flagged span
overrunning the true ditch. Both ends of a span are *returns*, so painting them
is guaranteed imprecision, and the margin around a ditch is solid ground we can
see.

Two levers, both shipped but off by default:

  trim    metres left unpainted at each end of a span
          (`mark_discontinuities(trim=...)`)
  rim     keep the flag only on unobserved cells plus this many cells of the
          lip around them (`prune_candidates(rim=...)`)

The table below is the reason they are off. Precision rises, but
`negative_missed_unsafe` — the share of real ditch cells the system calls
drivable — moves off zero. That number is the one this project exists to keep
at zero, so the trade is a platform decision, not a default.

Scored the way the sweep scores it: `classify()` output against the planted
obstacles, so the columns mean the same thing here as in `final_sweep.csv`.

    python scripts/localise_study.py --frames 40 --fraction 0.05
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from raysense.allocate import BASELINES, WorldState
from raysense.mapping import FixedGridMap
from raysense.perceive import Traversability, classify, feature_masks
from raysense.raycast import mark_discontinuities, prune_candidates
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import SCENES, drive
from raysense.types import CellState

MAP_ARRAYS = ("n_obs", "h_sum", "h_sumsq", "last_seen", "state")


def traverse(scene, sensor, alloc_name, fraction, trim) -> FixedGridMap:
    """One drive, marking spans under a given trim policy."""
    emap = FixedGridMap(scene.map_config)
    alloc = BASELINES[alloc_name]()
    budget = int(round(fraction * sensor.n_rays))
    for frame, origin, full in drive(scene.terrain, sensor, scene.path):
        backend = ReplayBackend(full)
        world = WorldState(sensor=sensor, frame=frame, origin=origin)
        scan = backend.acquire(alloc.allocate(world, budget))
        emap.integrate(scan.points, frame=frame)
        mark_discontinuities(emap, scan, sensor, frame=frame, trim=trim)
    return emap


def score(emap, neg, n_true) -> dict:
    est = classify(emap)
    cand = (emap.state & int(CellState.CANDIDATE_NEGATIVE)) != 0
    return {
        "negative_detected":
            float((est[neg] == int(Traversability.BLOCKED)).sum()) / n_true,
        "negative_unknown":
            float((est[neg] == int(Traversability.UNKNOWN)).sum()) / n_true,
        "negative_missed_unsafe":
            float((est[neg] == int(Traversability.TRAVERSABLE)).sum()) / n_true,
        "candidate_precision": float((cand & neg).sum()) / max(1, int(cand.sum())),
        "candidate_cells": int(cand.sum()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--allocator", default="uniform")
    ap.add_argument("--fraction", type=float, default=0.05)
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--trims", nargs="+", type=float, default=[0.0, 0.3, 0.6])
    ap.add_argument("--rims", nargs="+", type=int, default=[-1, 1, 2, 3])
    ap.add_argument("--csv", type=Path, default=Path("results/localise_study.csv"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    neg = feature_masks(FixedGridMap(scene.map_config), scene)["negative"]
    n_true = int(neg.sum())
    print(f"{n_true:,} true negative-obstacle cells · {args.allocator} at "
          f"{args.fraction:.0%} over {args.frames} frames\n")

    hdr = (f"{'trim':>6}{'rim':>6}{'detected':>11}{'missed-unsafe':>16}"
           f"{'precision':>12}{'cells':>9}")
    print(hdr)
    print("─" * (len(hdr) + 14))
    rows = []
    for trim in args.trims:
        base = traverse(scene, sensor, args.allocator, args.fraction, trim)
        for rim in args.rims:
            emap = FixedGridMap(scene.map_config)
            for a in MAP_ARRAYS:
                setattr(emap, a, getattr(base, a).copy())
            if rim >= 0:
                prune_candidates(emap, rim=rim)
            r = score(emap, neg, n_true)
            rows.append({"trim_m": trim, "rim_cells": rim, **r})
            note = "  zero unsafe" if r["negative_missed_unsafe"] == 0.0 else ""
            print(f"{trim:>6.1f}{'off' if rim < 0 else rim:>6}"
                  f"{r['negative_detected']:>10.1%}"
                  f"{r['negative_missed_unsafe']:>15.2%}"
                  f"{r['candidate_precision']:>12.1%}"
                  f"{r['candidate_cells']:>9,}{note}")

    df = pd.DataFrame(rows)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.csv, index=False)
    print(f"\nwrote {args.csv}")
    print("Shipped default is trim 0.0 / rim off — the only setting that holds "
          "negative_missed_unsafe at zero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
