#!/usr/bin/env python3
"""Where should the discontinuity threshold sit?

Left open at M5: 2.0 admits ~70 terrain flags per scan, 3.0 probably does not.
"Probably" is not a number, and a threshold chosen by eye is the first thing a
technical jury will pull on.

Gaps are computed once per frame with no threshold applied, then filtered at
each candidate value, so the whole curve costs one traverse rather than one per
threshold. Detection is scored on the planted ditches; false flags are scored
against the *same terrain with no ditches in it*, which is the only honest
control.

    python scripts/threshold_sweep.py --frames 40 --fraction 0.05
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
from raysense.types import CellState

THRESHOLDS = [1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 7.0]


def mark_span(emap, near, far, frame):
    """Flag the ground each gap skipped over."""
    if not len(near):
        return
    seg = far - near
    steps = max(2, int(np.ceil(np.linalg.norm(seg[:, :2], axis=1).max()
                               / emap.config.resolution)) + 1)
    for s in np.linspace(0.0, 1.0, steps):
        p = near + seg * s
        r, c, inside = emap.world_to_cell(p[:, 0], p[:, 1])
        emap.state[r[inside], c[inside]] |= int(CellState.CANDIDATE_NEGATIVE)


def run(scene, sensor, alloc_name, fraction, thresholds, strip_ditches: bool):
    """One traverse; every threshold scored from the same gaps."""
    terrain = scene.terrain
    if strip_ditches:
        # identical seed and relief, no planted ditches: the control
        terrain = make_terrain(size_m=240.0, resolution=0.3, roughness=3.0, seed=scene.seed)
        for f in scene.terrain.features:
            if f.kind == "positive":
                terrain.add_boulder(f.center, f.extent[0], f.depth)

    maps = {t: FixedGridMap(scene.map_config) for t in thresholds}
    alloc = BASELINES[alloc_name]()
    budget = int(round(fraction * sensor.n_rays))

    for frame, origin, full in drive(terrain, sensor, scene.path):
        backend = ReplayBackend(full)
        world = WorldState(sensor=sensor, frame=frame, origin=origin)
        scan = backend.acquire(alloc.allocate(world, budget))
        near, far, ratio = find_discontinuities(scan, sensor, threshold=0.0)
        for t in thresholds:
            keep = ratio > t
            mark_span(maps[t], near[keep], far[keep], frame)
    return maps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--allocator", default="uniform")
    ap.add_argument("--fraction", type=float, default=0.05)
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--csv", type=Path, default=Path("results/threshold_sweep.csv"))
    ap.add_argument("--out", type=Path, default=Path("results/threshold_sweep.png"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)

    print("traverse 1/2 — terrain with ditches")
    with_ditches = run(scene, sensor, args.allocator, args.fraction, THRESHOLDS, False)
    print("traverse 2/2 — identical terrain, ditches removed (the control)")
    control = run(scene, sensor, args.allocator, args.fraction, THRESHOLDS, True)

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

    rows = []
    for t in THRESHOLDS:
        cand = (with_ditches[t].state & int(CellState.CANDIDATE_NEGATIVE)) != 0
        ctrl = (control[t].state & int(CellState.CANDIDATE_NEGATIVE)) != 0
        rows.append({
            "threshold": t,
            "ditch_recall": float((cand & neg).sum()) / max(1, int(neg.sum())),
            "false_cells": int(ctrl.sum()),
            "flagged_cells": int(cand.sum()),
            "precision_proxy": float((cand & neg).sum()) / max(1, int(cand.sum())),
        })

    df = pd.DataFrame(rows)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.csv, index=False)
    print(f"\nwrote {args.csv}\n")
    print(f"{'thresh':>7}{'ditch recall':>14}{'false cells':>13}{'precision':>11}")
    print("-" * 45)
    for r in rows:
        print(f"{r['threshold']:>7.2f}{r['ditch_recall']:>13.1%}"
              f"{r['false_cells']:>13,}{r['precision_proxy']:>11.1%}")

    plot(df, args.out)
    print(f"\nwrote {args.out}")
    return 0


def plot(df, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    from raysense.viz.charts import _style
    from raysense.viz.palette import INK, PALETTE

    fig = Figure(figsize=(8.6, 5.2), dpi=130, facecolor=INK["surface"])
    ax = fig.subplots()
    _style(ax)
    ax.plot(df.threshold, df.ditch_recall * 100, lw=2.0, color=PALETTE.traversable,
            marker="o", ms=6, mec=INK["surface"], mew=1.2, zorder=3)
    ax.annotate("ditch recall", xy=(df.threshold.iloc[-1], df.ditch_recall.iloc[-1] * 100),
                xytext=(8, 0), textcoords="offset points", fontsize=8.5,
                color=PALETTE.traversable, weight="bold", va="center")

    top = max(1, df.false_cells.max())
    ax.plot(df.threshold, df.false_cells / top * 100, lw=2.0, color=PALETTE.negative,
            marker="s", ms=6, mec=INK["surface"], mew=1.2, ls="--", zorder=3)
    ax.annotate("false flags\n(share of worst case)",
                xy=(df.threshold.iloc[-1], df.false_cells.iloc[-1] / top * 100),
                xytext=(8, 0), textcoords="offset points", fontsize=8.5,
                color=PALETTE.negative, weight="bold", va="center")

    ax.set_xlabel("anomaly threshold — measured gap ÷ predicted gap")
    ax.set_ylabel("percent")
    ax.set_xlim(1.1, 9.4)
    ax.set_ylim(-3, 105)
    ax.set_title("Where to set the threshold", fontsize=10.5, weight="bold",
                 loc="left", color=INK["primary"])
    fig.tight_layout()
    fig.savefig(out, dpi=130, facecolor=fig.get_facecolor())


if __name__ == "__main__":
    raise SystemExit(main())
