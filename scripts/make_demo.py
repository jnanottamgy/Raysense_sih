#!/usr/bin/env python3
"""Build the demo — the M8 deliverable.

Two systems driven over the identical scene, in lockstep, at the identical
budget. The only difference is whether the discontinuity test is running.

Frames are rendered offline and played back from a single self-contained HTML
file with the images embedded. Nothing is computed live and nothing is fetched
over a network, because a demo that needs either is a demo that fails in the
room.

    python scripts/make_demo.py --fraction 0.05 --frames 40
"""

from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
from matplotlib.figure import Figure

from raysense.allocate import BASELINES, WorldState
from raysense.mapping import FixedGridMap
from raysense.perceive import Traversability, classify
from raysense.raycast import mark_discontinuities
from raysense.sensor import ReplayBackend, SensorModel
from raysense.sim import SCENES, drive
from raysense.viz.palette import INK, PALETTE
from raysense.viz.states import draw_traversability


def counters_panel(ax, label, stats, highlight: bool) -> None:
    ax.axis("off")
    ax.set_facecolor(INK["surface"])
    colour = PALETTE.negative if highlight else INK["muted"]
    ax.text(0, 0.92, label, fontsize=12, weight="bold", color=INK["primary"],
            transform=ax.transAxes)
    rows = [
        ("rays this frame", f"{stats['rays']:,}"),
        ("ditch cells flagged", f"{stats['flagged']:,}"),
        ("ditches found", f"{stats['found']} / {stats['total']}"),
        ("nearest ditch", stats["nearest"]),
        ("first warned at", stats["warned_at"]),
        ("VERDICT", stats["verdict"]),
    ]
    for i, (k, v) in enumerate(rows):
        y = 0.76 - i * 0.145
        ax.text(0, y, k, fontsize=9, color=INK["muted"], transform=ax.transAxes)
        ax.text(1.0, y, v, fontsize=11, weight="bold", ha="right",
                color=colour if k == "VERDICT" else INK["primary"],
                transform=ax.transAxes)


def stats_for(trav, rays, flagged, feat_masks, nearest_idx, near_label, flagged_at) -> dict:
    """What each system currently believes, for the counter strip."""
    found = sum(int((trav[m] == int(Traversability.BLOCKED)).any()) for m in feat_masks)
    near = feat_masks[nearest_idx]
    blocked = (trav[near] == int(Traversability.BLOCKED)).any()
    drivable = (trav[near] == int(Traversability.TRAVERSABLE)).any()
    verdict = ("DITCH AHEAD" if blocked
               else "clear to drive" if drivable else "unknown ahead")
    return {"rays": rays, "flagged": flagged, "found": found,
            "total": len(feat_masks), "nearest": near_label, "verdict": verdict,
            "warned_at": "—" if flagged_at is None else f"{flagged_at:.0f} m out"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="offroad_course", choices=sorted(SCENES))
    ap.add_argument("--sensor", default="configs/sensor/ouster_os1_64.yaml")
    ap.add_argument("--baseline", default="uniform", choices=sorted(BASELINES),
                    help="what a conventional system does: heights only")
    ap.add_argument("--ours", default="raysense", choices=sorted(BASELINES),
                    help="the full system: need-weighted budget plus the gap test")
    ap.add_argument("--fraction", type=float, default=0.05)
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--every", type=int, default=2, help="render every Nth frame")
    ap.add_argument("--out", type=Path, default=Path("results/demo.html"))
    ap.add_argument("--frame-dir", type=Path, default=Path("results/demo_frames"))
    args = ap.parse_args()

    sensor = SensorModel.from_yaml(args.sensor)
    scene = SCENES[args.scene](seed=args.seed, n_frames=args.frames)
    budget = int(round(args.fraction * sensor.n_rays))

    off = FixedGridMap(scene.map_config)
    on = FixedGridMap(scene.map_config)
    alloc_off = BASELINES[args.baseline]()
    alloc_on = BASELINES[args.ours]()
    # when each system first flags the ditch it is approaching — the metric the
    # allocator actually wins on, and the one a driver would feel
    first_flag = {"off": None, "on": None}

    neg_features = [f for f in scene.terrain.features if f.kind == "negative"]
    X, Y = off.cell_centres()
    feat_masks = []
    for f in neg_features:
        if f.label == "crater":
            feat_masks.append(np.hypot(X - f.center[0], Y - f.center[1]) <= f.extent[0])
        else:
            feat_masks.append((np.abs(X - f.center[0]) <= f.extent[1] / 2)
                              & (np.abs(Y - f.center[1]) <= f.extent[0] / 2))

    args.frame_dir.mkdir(parents=True, exist_ok=True)
    encoded: list[str] = []
    captions: list[str] = []
    flagged_on = 0

    for frame, origin, full in drive(scene.terrain, sensor, scene.path):
        backend = ReplayBackend(full)
        rays_used = {}
        for emap, alloc, detect in ((off, alloc_off, False), (on, alloc_on, True)):
            world = WorldState(sensor=sensor, frame=frame, origin=origin, emap=emap)
            scan = backend.acquire(alloc.allocate(world, budget))
            emap.integrate(scan.points, frame=frame)
            rays_used["on" if detect else "off"] = scan.n_fired
            if detect:
                flagged_on += mark_discontinuities(emap, scan, sensor, frame=frame)

        if frame % args.every and frame != scene.n_frames - 1:
            continue

        trav_off, trav_on = classify(off), classify(on)
        d_all = [np.hypot(*(np.asarray(f.center) - origin[:2])) for f in neg_features]
        kk = int(np.argmin(d_all))
        for tag, trav in (("off", trav_off), ("on", trav_on)):
            if first_flag[tag] is None and (
                trav[feat_masks[kk]] == int(Traversability.BLOCKED)
            ).any():
                first_flag[tag] = d_all[kk]
        # the ditch the vehicle is closest to, and what each system says about it
        d = [np.hypot(*(np.asarray(f.center) - origin[:2])) for f in neg_features]
        k = int(np.argmin(d))
        near_label = f"{neg_features[k].label} @ {d[k]:.0f} m"

        s_off = stats_for(trav_off, rays_used["off"], 0, feat_masks, k, near_label,
                          first_flag["off"])
        s_on = stats_for(trav_on, rays_used["on"], flagged_on, feat_masks, k, near_label,
                         first_flag["on"])

        fig = Figure(figsize=(15.0, 6.4), dpi=110, facecolor=INK["surface"])
        gs = fig.add_gridspec(2, 2, height_ratios=[4.2, 1.0], hspace=0.05, wspace=0.12)
        a1, a2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
        c1, c2 = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

        draw_traversability(a1, off, terrain=scene.terrain,
                            title=f"Conventional — {args.baseline}, heights only")
        draw_traversability(a2, on, terrain=scene.terrain,
                            title="Raysense — need-weighted budget + gap test")
        for ax in (a1, a2):
            ax.plot(origin[0], origin[1], marker="^", ms=11, color=INK["primary"],
                    mec="white", mew=1.2, zorder=9)
            ax.set_xlim(-60, 80)
            ax.set_ylim(-40, 40)

        counters_panel(c1, "Conventional", s_off, s_off["verdict"] == "DITCH AHEAD")
        counters_panel(c2, "Raysense", s_on, s_on["verdict"] == "DITCH AHEAD")

        fig.suptitle(
            f"Frame {frame:02d} / {scene.n_frames}     "
            f"both at {args.fraction:.0%} of a full scan     "
            f"same sensor, same scene, same budget",
            fontsize=12, weight="bold", color=INK["primary"], x=0.007, ha="left")

        png = args.frame_dir / f"frame_{frame:03d}.png"
        fig.savefig(png, dpi=110, facecolor=fig.get_facecolor())
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=90, facecolor=fig.get_facecolor())
        encoded.append(base64.b64encode(buf.getvalue()).decode())
        captions.append(f"frame {frame} · {d_all[kk]:.0f} m to the nearest ditch — "
                        f"conventional: {s_off['verdict']} · raysense: {s_on['verdict']}")
        print(f"  frame {frame:3d}  {d_all[kk]:5.1f} m to ditch   "
              f"conventional: {s_off['verdict']:<15} raysense: {s_on['verdict']}")

    write_player(args.out, encoded, captions, scene, args)
    print(f"\nwrote {args.out}  ({len(encoded)} frames embedded, fully offline)")
    print(f"wrote {args.frame_dir}/  (individual PNGs)")
    return 0


def write_player(out: Path, frames: list[str], captions: list[str], scene, args) -> None:
    """A single self-contained HTML file. No network, no codec, no dependencies."""
    imgs = ",".join(f'"data:image/png;base64,{f}"' for f in frames)
    caps = ",".join(f'"{c}"' for c in captions)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""<!doctype html><meta charset=utf-8>
<title>Raysense demo</title>
<style>
 body{{margin:0;background:#14181A;color:#E8EDEB;
      font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;text-align:center}}
 h1{{font-size:16px;letter-spacing:.12em;text-transform:uppercase;
     padding:14px;margin:0;color:#9FB0AD;font-weight:600}}
 img{{max-width:100%;height:auto;display:block;margin:0 auto}}
 #cap{{padding:10px;color:#9FB0AD;font-family:"IBM Plex Mono",monospace;font-size:13px}}
 .bar{{display:flex;gap:10px;align-items:center;justify-content:center;padding:12px}}
 button{{background:#1F2729;color:#E8EDEB;border:1px solid #3A4547;border-radius:3px;
        padding:7px 16px;font-size:13px;cursor:pointer}}
 button:hover{{background:#2A3335}} input{{width:min(560px,70vw)}}
</style>
<h1>Raysense &middot; both systems at {args.fraction:.0%} of a full scan</h1>
<img id=f><div id=cap></div>
<div class=bar>
 <button onclick=step(-1)>&#9664; prev</button>
 <button id=pp onclick=toggle()>&#9654; play</button>
 <button onclick=step(1)>next &#9654;</button>
 <input id=s type=range min=0 max="{len(frames) - 1}" value=0 oninput=go(+this.value)>
</div>
<script>
const F=[{imgs}],C=[{caps}];let i=0,t=null;
function go(n){{i=(n+F.length)%F.length;document.getElementById('f').src=F[i];
 document.getElementById('cap').textContent=C[i];document.getElementById('s').value=i;}}
function step(d){{pause();go(i+d);}}
function pause(){{if(!t)return;clearInterval(t);t=null;
 document.getElementById('pp').innerHTML='&#9654; play';}}
function toggle(){{if(t)return pause();
 t=setInterval(()=>go(i+1),450);document.getElementById('pp').innerHTML='&#10074;&#10074; pause';}}
document.onkeydown=e=>{{if(e.key==='ArrowRight')step(1);if(e.key==='ArrowLeft')step(-1);
 if(e.key===' '){{e.preventDefault();toggle();}}}};
go(0);
</script>
""")


if __name__ == "__main__":
    raise SystemExit(main())
