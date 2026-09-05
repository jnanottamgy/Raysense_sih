"""Render one scan - the M0 exit criterion, and a permanent sanity check.

Three panels, chosen so that what matters is visible rather than merely
present:

1. **Plan view** - where the returns landed, coloured by elevation, with the
   planted ground-truth features outlined.
2. **Sensor view** - the native beam grid, coloured by range. This is the panel
   that carries the project's thesis, because rays that were fired and came
   back with nothing are drawn in a reserved status colour rather than left
   blank. Absence becomes visible.
3. **Forward profile** - a slice along the direction of travel, where a ditch
   shows up as a gap in the ground line.

Panel 2 is the reason this project renders map state and not point clouds: in
a plain point cloud a missing return is simply nothing at all.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from raysense.sensor import SensorModel  # noqa: E402
from raysense.types import ScanResult  # noqa: E402
from raysense.viz.palette import (  # noqa: E402
    ELEVATION_CMAP,
    FEATURE_COLOR,
    INK,
    RANGE_CMAP,
    STATUS,
)


def _style_axes(ax) -> None:
    """Recessive chrome: the data should be the loudest thing on the panel."""
    ax.set_facecolor(INK["surface"])
    ax.tick_params(colors=INK["muted"], labelsize=8, length=3)
    for spine in ax.spines.values():
        spine.set_color(INK["grid"])
    ax.xaxis.label.set_color(INK["secondary"])
    ax.yaxis.label.set_color(INK["secondary"])
    ax.title.set_color(INK["primary"])


def render_scan(
    scan: ScanResult,
    sensor: SensorModel,
    terrain=None,
    title: str = "",
    plan_extent: float = 45.0,
    profile_halfwidth: float = 1.5,
) -> Figure:
    """Build the three-panel diagnostic figure for a single scan."""
    fig = Figure(figsize=(15.5, 5.2), dpi=130, facecolor=INK["surface"])
    ax_plan, ax_sensor, ax_prof = fig.subplots(1, 3)

    pts = scan.points
    origin = np.asarray(scan.fired.origin, dtype=float)

    # ---------------------------------------------------------- 1. plan view
    _style_axes(ax_plan)
    near = np.abs(pts[:, 0]) < plan_extent
    near &= np.abs(pts[:, 1]) < plan_extent
    # Clip the ramp to the terrain's actual spread. Without this the relief is
    # swamped by a handful of outliers and the panel reads as one flat colour.
    z = pts[near, 2]
    zlo, zhi = (np.percentile(z, [2, 98]) if z.size else (0.0, 1.0))
    sc = ax_plan.scatter(
        pts[near, 0], pts[near, 1], c=z, vmin=zlo, vmax=zhi,
        cmap=ELEVATION_CMAP, s=1.1, linewidths=0, rasterized=True,
    )
    cb_plan = fig.colorbar(sc, ax=ax_plan, pad=0.015, fraction=0.045)
    cb_plan.set_label("elevation (m)", color=INK["secondary"], fontsize=8)
    cb_plan.ax.tick_params(colors=INK["muted"], labelsize=7)
    cb_plan.outline.set_edgecolor(INK["grid"])
    ax_plan.plot(origin[0], origin[1], marker="^", ms=9,
                 color=INK["primary"], zorder=5, label="Sensor")

    if terrain is not None and terrain.features:
        for feat in terrain.features:
            colour = FEATURE_COLOR[feat.kind]
            if feat.label in ("crater", "boulder"):
                patch = mpatches.Circle(
                    feat.center, feat.extent[0], fill=False,
                    ec=colour, lw=1.6, ls="--", zorder=4,
                )
            else:
                patch = mpatches.Rectangle(
                    (feat.center[0] - feat.extent[1] / 2, feat.center[1] - feat.extent[0] / 2),
                    feat.extent[1], feat.extent[0], fill=False,
                    ec=colour, lw=1.6, ls="--", zorder=4,
                )
            ax_plan.add_patch(patch)
            ax_plan.annotate(
                feat.label, feat.center, textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=7.5, color=colour, weight="bold",
            )

    ax_plan.set_xlim(-plan_extent, plan_extent)
    ax_plan.set_ylim(-plan_extent, plan_extent)
    ax_plan.set_aspect("equal")
    ax_plan.set_xlabel("x  (m, forward)")
    ax_plan.set_ylabel("y  (m, left)")
    ax_plan.set_title("Plan view — returns by elevation", fontsize=10, weight="bold", loc="left")
    ax_plan.grid(True, color=INK["grid"], lw=0.5, alpha=0.7)
    ax_plan.set_axisbelow(True)
    ax_plan.legend(
        handles=[
            mpatches.Patch(
                ec=FEATURE_COLOR["negative"], fc="none", ls="--", label="Negative (truth)"
            ),
            mpatches.Patch(
                ec=FEATURE_COLOR["positive"], fc="none", ls="--", label="Positive (truth)"
            ),
        ],
        loc="upper right", fontsize=7.5, framealpha=0.95, edgecolor=INK["grid"],
    )

    # -------------------------------------------------------- 2. sensor view
    _style_axes(ax_sensor)
    beams, cols = sensor.n_beams, sensor.n_azimuth
    native = scan.fired.beam_index
    if native is None:
        raise ValueError("sensor view needs `fired.beam_index` to place rays on the beam grid")

    # Start every cell as "not sampled", then fill in what was fired.
    img = np.full((beams, cols), np.nan)
    fired_flag = np.zeros((beams, cols), dtype=bool)
    fb, fc = sensor.beam_of(native), sensor.column_of(native)
    fired_flag[fb, fc] = True

    ret = scan.returned_mask()
    rb, rc = fb[ret], fc[ret]
    img[rb, rc] = np.linalg.norm(scan.points - origin, axis=1)

    # Draw order matters: never-fired ground, then fired-but-empty on top of it,
    # then the ranges. Each layer is a different kind of knowledge.
    ax_sensor.imshow(
        np.ones((beams, cols)), cmap=matplotlib.colors.ListedColormap([STATUS["never_fired"]]),
        aspect="auto", origin="lower", interpolation="nearest",
    )
    empty_layer = np.where(fired_flag & np.isnan(img), 1.0, np.nan)
    ax_sensor.imshow(
        empty_layer, cmap=matplotlib.colors.ListedColormap([STATUS["no_return"]]),
        aspect="auto", origin="lower", interpolation="nearest",
    )
    finite = img[np.isfinite(img)]
    rlo, rhi = (np.percentile(finite, [1, 97]) if finite.size else (0.0, 1.0))
    im = ax_sensor.imshow(
        img, cmap=RANGE_CMAP, vmin=rlo, vmax=rhi,
        aspect="auto", origin="lower", interpolation="nearest",
    )
    cb = fig.colorbar(im, ax=ax_sensor, pad=0.015, fraction=0.045)
    cb.set_label("range (m)", color=INK["secondary"], fontsize=8)
    cb.ax.tick_params(colors=INK["muted"], labelsize=7)
    cb.outline.set_edgecolor(INK["grid"])

    ax_sensor.set_xlabel("azimuth column")
    ax_sensor.set_ylabel("beam (elevation row)")
    ax_sensor.set_title("Sensor view — where absence lives", fontsize=10, weight="bold", loc="left")
    ax_sensor.legend(
        handles=[
            mpatches.Patch(fc=STATUS["no_return"], ec="none", label="Fired, no return"),
            mpatches.Patch(fc=STATUS["never_fired"], ec="none", label="Never fired"),
        ],
        loc="upper right", fontsize=7.5, framealpha=0.95, edgecolor=INK["grid"],
    )

    # ----------------------------------------------------- 3. forward profile
    _style_axes(ax_prof)
    corridor = np.abs(pts[:, 1] - origin[1]) < profile_halfwidth
    corridor &= pts[:, 0] > origin[0]
    fx = pts[corridor, 0]
    fz = pts[corridor, 2]
    order = np.argsort(fx)
    ax_prof.plot(
        fx[order], fz[order], marker="o", ms=2.6, lw=0.8,
        color=INK["secondary"], mfc=INK["secondary"], mec="none", label="Ground returns",
    )
    ax_prof.axhline(origin[2], color=INK["grid"], lw=1, ls=":")
    ax_prof.annotate(
        "sensor height", (plan_extent * 0.62, origin[2]), textcoords="offset points",
        xytext=(0, 4), fontsize=7, color=INK["muted"],
    )

    if terrain is not None:
        for feat in terrain.features:
            if abs(feat.center[1]) > profile_halfwidth + max(feat.extent):
                continue
            half = feat.extent[1] / 2 if feat.label == "trench" else feat.extent[0]
            ax_prof.axvspan(
                feat.center[0] - half, feat.center[0] + half,
                color=FEATURE_COLOR[feat.kind], alpha=0.16, lw=0,
            )
            ax_prof.annotate(
                feat.label, (feat.center[0], ax_prof.get_ylim()[1]),
                textcoords="offset points", xytext=(0, -11), ha="center",
                fontsize=7.5, color=FEATURE_COLOR[feat.kind], weight="bold",
            )

    ax_prof.set_xlim(0, plan_extent)
    ax_prof.set_xlabel("x  (m, forward)")
    ax_prof.set_ylabel("z  (m)")
    ax_prof.set_title(
        f"Forward profile — ±{profile_halfwidth:g} m corridor", fontsize=10,
        weight="bold", loc="left",
    )
    ax_prof.grid(True, color=INK["grid"], lw=0.5, alpha=0.7)
    ax_prof.set_axisbelow(True)
    ax_prof.legend(loc="lower right", fontsize=7.5, framealpha=0.95, edgecolor=INK["grid"])

    header = title or "Raysense — single scan"
    fig.suptitle(
        f"{header}     "
        f"{scan.n_returns:,} returns / {scan.n_fired:,} fired  ({scan.return_ratio:.1%})",
        fontsize=11, weight="bold", color=INK["primary"], x=0.007, ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    return fig
