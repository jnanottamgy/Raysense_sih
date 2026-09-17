#!/usr/bin/env python3
"""What each system says about one ditch, on *every* frame of the approach.

`make_demo.py` renders every second frame, which is fine for a video and wrong
for a claim: a verdict that flips on an odd frame is invisible in it. This
walks the same run and prints the verdict on each frame, so a statement like
"it only warns at N metres" can be checked rather than inferred from the
pictures.

The verdict is exactly the one the demo panel shows: DITCH AHEAD if any cell of
the tracked ditch is BLOCKED, else clear to drive if any is TRAVERSABLE, else
unknown ahead. By default it tracks the trench at (-15, 7) — the one the
vehicle meets first, and the one the demo frames are about.

    python scripts/demo_trace.py
    python scripts/demo_trace.py --track 10 0 --frames 40
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from raysense.allocate import BASELINES, WorldState  # noqa: E402
from raysense.mapping import FixedGridMap  # noqa: E402
from raysense.perceive import Traversability, classify  # noqa: E402
from raysense.raycast import mark_discontinuities  # noqa: E402
from raysense.sensor import ReplayBackend, SensorModel  # noqa: E402
from raysense.sim import SCENES, drive  # noqa: E402


def feature_mask(emap: FixedGridMap, f) -> np.ndarray:
    X, Y = emap.cell_centres()
    if f.label == "crater":
        return np.hypot(X - f.center[0], Y - f.center[1]) <= f.extent[0]
    return ((np.abs(X - f.center[0]) <= f.extent[1] / 2)
            & (np.abs(Y - f.center[1]) <= f.extent[0] / 2))


def verdict(trav: np.ndarray, mask: np.ndarray) -> str:
    cells = trav[mask]
    if (cells == int(Traversability.BLOCKED)).any():
        return "DITCH AHEAD"
    if (cells == int(Traversability.TRAVERSABLE)).any():
        return "clear to drive"
    return "unknown ahead"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--baseline", default="uniform", choices=sorted(BASELINES))
    ap.add_argument("--ours", default="raysense", choices=sorted(BASELINES))
    ap.add_argument("--fraction", type=float, default=0.02)
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--track", nargs=2, type=float, default=[-15.0, 7.0],
                    metavar=("X", "Y"), help="centre of the ditch to follow")
    ap.add_argument("--csv", type=Path, default=Path("results/demo_trace.csv"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    budget = int(round(args.fraction * sensor.n_rays))

    off, on = FixedGridMap(scene.map_config), FixedGridMap(scene.map_config)
    alloc_off, alloc_on = BASELINES[args.baseline](), BASELINES[args.ours]()

    want = tuple(args.track)
    tracked = next((f for f in scene.terrain.features
                    if f.kind == "negative" and tuple(f.center) == want), None)
    if tracked is None:
        centres = [tuple(f.center) for f in scene.terrain.features
                   if f.kind == "negative"]
        print(f"no negative feature at {want}. Planted: {centres}")
        return 2
    mask = feature_mask(off, tracked)

    print(f"tracking {tracked.label} at {want} — "
          f"{tracked.extent[1]:.1f} m wide, {tracked.depth:.1f} m deep · "
          f"both systems at {args.fraction:.0%} of a full scan\n")
    hdr = f"{'frame':>6}{'distance':>11}  {'conventional':<16}{'raysense':<16}"
    print(hdr)
    print("─" * len(hdr))

    rows, first = [], {"off": None, "on": None}
    for frame, origin, full in drive(scene.terrain, sensor, scene.path):
        backend = ReplayBackend(full)
        rays = {}
        for emap, alloc, detect in ((off, alloc_off, False), (on, alloc_on, True)):
            world = WorldState(sensor=sensor, frame=frame, origin=origin, emap=emap)
            scan = backend.acquire(alloc.allocate(world, budget))
            emap.integrate(scan.points, frame=frame)
            rays["on" if detect else "off"] = scan.n_fired
            if detect:
                mark_discontinuities(emap, scan, sensor, frame=frame)

        d = float(np.hypot(*(np.asarray(tracked.center) - origin[:2])))
        v = {"off": verdict(classify(off), mask), "on": verdict(classify(on), mask)}
        for tag in ("off", "on"):
            if first[tag] is None and v[tag] == "DITCH AHEAD":
                first[tag] = d
        rows.append({"frame": frame, "distance_m": round(d, 2),
                     "conventional": v["off"], "raysense": v["on"],
                     "rays_conventional": rays["off"], "rays_raysense": rays["on"]})
        print(f"{frame:>6}{d:>10.1f} m  {v['off']:<16}{v['on']:<16}")

    df = pd.DataFrame(rows)
    approach = df[df.distance_m.diff().fillna(-1) < 0]  # while it is closing

    def steady(col: str) -> float | None:
        """First distance from which the warning never lapses again."""
        seq = approach[col].tolist()
        dist = approach.distance_m.tolist()
        for i, val in enumerate(seq):
            if val == "DITCH AHEAD" and all(s == "DITCH AHEAD" for s in seq[i:]):
                return dist[i]
        return None

    print()
    for tag, col in (("conventional", "conventional"), ("raysense", "raysense")):
        f, s = first["off" if tag == "conventional" else "on"], steady(col)
        print(f"{tag:>14}   first flag {'—' if f is None else f'{f:.1f} m':>8}"
              f"   steady from {'—' if s is None else f'{s:.1f} m':>8}")
    a, b = steady("conventional"), steady("raysense")
    if a is not None and b is not None:
        gap = b - a
        print(f"\n{'':>14}   we warn {gap:.1f} m earlier — "
              f"{gap / 4.0:.1f} s at the 4 m/s this run drives")
    lapse = approach[(approach.conventional == "clear to drive")
                     & (approach.raysense == "DITCH AHEAD")]
    for _, r in lapse.iterrows():
        print(f"{'':>14}   frame {r.frame}: conventional says CLEAR TO DRIVE at "
              f"{r.distance_m:.1f} m")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.csv, index=False)
    print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
