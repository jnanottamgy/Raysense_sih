#!/usr/bin/env python3
"""Render one scan — the M0 exit criterion.

Runs against either data source, so neither blocks the other:

    # synthetic world, works anywhere, no download needed
    python scripts/render_scan.py --out results/m0_synthetic.png

    # real RELLIS-3D sequence, once the dataset is on disk
    python scripts/render_scan.py --rellis data/rellis/00000 --frame 0 \
        --out results/m0_rellis.png
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from raysense.sensor import SensorModel  # noqa: E402
from raysense.sim import make_terrain  # noqa: E402
from raysense.types import RayGrid, ScanResult  # noqa: E402
from raysense.viz import render_scan  # noqa: E402


def build_synthetic(sensor: SensorModel, seed: int):
    """A rolling off-road surface with three planted, ground-truthed features."""
    terrain = make_terrain(size_m=140.0, resolution=0.25, roughness=2.6, seed=seed)
    # A trench narrower than the beam spacing at its range: the case this whole
    # project exists for. See docs/M0_FINDINGS.md.
    terrain.add_trench(center=(18.0, 0.0), length=14.0, width=2.2, depth=1.6, angle_deg=90.0)
    terrain.add_boulder(center=(-12.0, 8.0), radius=1.4, height=1.1)
    terrain.add_crater(center=(30.0, -14.0), radius=4.0, depth=1.2)

    ground = float(terrain.sample(np.array(0.0), np.array(0.0)))
    origin = np.array([0.0, 0.0, ground + sensor.mount_height])
    rays = sensor.full_ray_grid(origin)

    t0 = time.perf_counter()
    scan = terrain.raycast(rays)
    print(f"  raycast {scan.n_fired:,} rays in {time.perf_counter() - t0:.2f}s")
    return scan, terrain


def load_rellis(path: Path, frame: int, sensor: SensorModel):
    """Load a real frame and reconstruct which native rays it corresponds to.

    A recorded scan arrives as returns only, so the fired grid is reconstructed
    by binning each point back onto the sensor's native beam grid. Points that
    fall in the same bin keep the nearer return.
    """
    from raysense.io import RellisSequence

    seq = RellisSequence(path)
    print(f"  {seq}")
    f = seq[frame]
    pts = f.points
    print(f"  frame {frame}: {f.n_points:,} points")

    az = np.arctan2(pts[:, 1], pts[:, 0]) % (2 * np.pi)
    rng = np.linalg.norm(pts, axis=1)
    el = np.arcsin(np.clip(pts[:, 2] / np.maximum(rng, 1e-9), -1, 1))

    col = np.clip(
        (az / (2 * np.pi) * sensor.n_azimuth).astype(int), 0, sensor.n_azimuth - 1
    )
    el_lo, el_hi = np.deg2rad(sensor.v_fov_min_deg), np.deg2rad(sensor.v_fov_max_deg)
    beam = np.clip(
        np.rint((el - el_lo) / (el_hi - el_lo) * (sensor.n_beams - 1)).astype(int),
        0, sensor.n_beams - 1,
    )
    native = beam * sensor.n_azimuth + col

    # keep the nearest return per native ray
    order = np.argsort(rng)
    native_sorted, pts_sorted = native[order], pts[order]
    uniq, first = np.unique(native_sorted, return_index=True)
    kept = pts_sorted[first]
    dropped = len(pts) - len(uniq)
    if dropped:
        print(f"  {dropped:,} points shared a beam cell; kept the nearer return")

    full = sensor.full_ray_grid(np.zeros(3))
    fired = RayGrid(
        azimuth=full.azimuth[uniq], elevation=full.elevation[uniq],
        origin=np.zeros(3), max_range=sensor.max_range, beam_index=uniq,
    )
    return ScanResult(points=kept, ray_index=np.arange(len(uniq)), fired=fired), None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--rellis", type=Path, help="path to a RELLIS-3D sequence directory")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=Path("results/m0_scan.png"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    print(f"sensor: {sensor.name}  {sensor.n_beams}x{sensor.n_azimuth} = {sensor.n_rays:,} rays")
    print(f"        vertical spacing {np.rad2deg(sensor.delta_theta_v):.3f} deg")

    if args.rellis:
        print(f"source: RELLIS-3D {args.rellis}")
        scan, terrain = load_rellis(args.rellis, args.frame, sensor)
        title = f"RELLIS-3D {args.rellis.name} frame {args.frame}"
    else:
        print(f"source: synthetic terrain (seed {args.seed})")
        scan, terrain = build_synthetic(sensor, args.seed)
        title = f"Synthetic off-road terrain (seed {args.seed})"

    print(f"        {scan.n_returns:,} returns, {scan.empty_rays().n_rays:,} fired with no return")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig = render_scan(scan, sensor, terrain=terrain, title=title)
    fig.savefig(args.out, dpi=130, facecolor=fig.get_facecolor())
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
