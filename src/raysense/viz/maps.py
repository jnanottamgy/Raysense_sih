"""Render the 2.5D map — the view the demo is built on.

A point cloud cannot show an absence: a cell nothing was measured in looks
exactly like empty space. The map view can, and does, because unobserved cells
are drawn with hatching rather than left blank. That is the whole reason this
project renders map state instead of points.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches  # noqa: E402

matplotlib.rcParams["hatch.linewidth"] = 0.6
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from raysense.mapping import FixedGridMap  # noqa: E402
from raysense.viz.palette import ELEVATION_CMAP, FEATURE_COLOR, INK, STATUS  # noqa: E402


def _style(ax) -> None:
    ax.set_facecolor(INK["surface"])
    ax.tick_params(colors=INK["muted"], labelsize=8, length=3)
    for sp in ax.spines.values():
        sp.set_color(INK["grid"])
    ax.xaxis.label.set_color(INK["secondary"])
    ax.yaxis.label.set_color(INK["secondary"])


def draw_map(
    ax,
    emap: FixedGridMap,
    terrain=None,
    vlim: tuple[float, float] | None = None,
    title: str = "",
    path: np.ndarray | None = None,
    show_unknown: bool = True,
) -> tuple:
    """Draw one elevation map onto `ax`. Returns the image handle and limits."""
    _style(ax)
    h = emap.height()
    seen = emap.observed()

    if vlim is None:
        vals = h[seen]
        vlim = tuple(np.percentile(vals, [2, 98])) if vals.size else (0.0, 1.0)

    if show_unknown:
        # Unknown is hatching, not a colour: it survives colour-blindness,
        # greyscale printing and a bad projector.
        ax.add_patch(
            mpatches.Rectangle(
                (emap.extent[0], emap.extent[2]),
                emap.extent[1] - emap.extent[0],
                emap.extent[3] - emap.extent[2],
                facecolor="#F5F6F3", hatch="///",
                edgecolor=STATUS["never_fired"], lw=0, zorder=0,
            )
        )

    im = ax.imshow(
        np.ma.masked_where(~seen, h), origin="lower", extent=emap.extent,
        cmap=ELEVATION_CMAP, vmin=vlim[0], vmax=vlim[1], interpolation="nearest", zorder=1,
    )

    if terrain is not None:
        for f in terrain.features:
            colour = FEATURE_COLOR[f.kind]
            if f.label in ("crater", "boulder"):
                patch = mpatches.Circle(f.center, f.extent[0], fill=False,
                                        ec=colour, lw=1.5, ls="--", zorder=4)
            else:
                patch = mpatches.Rectangle(
                    (f.center[0] - f.extent[1] / 2, f.center[1] - f.extent[0] / 2),
                    f.extent[1], f.extent[0], fill=False, ec=colour, lw=1.5, ls="--", zorder=4)
            ax.add_patch(patch)

    if path is not None and len(path):
        ax.plot(path[:, 0], path[:, 1], color=INK["primary"], lw=1.2, ls=":", zorder=5)
        ax.plot(path[-1, 0], path[-1, 1], marker="^", ms=8,
                color=INK["primary"], zorder=6)

    ax.set_xlim(emap.extent[0], emap.extent[1])
    ax.set_ylim(emap.extent[2], emap.extent[3])
    ax.set_aspect("equal")
    ax.set_xlabel("x  (m)")
    ax.set_ylabel("y  (m)")
    if title:
        ax.set_title(title, fontsize=10, weight="bold", loc="left", color=INK["primary"])
    return im, vlim


def render_map(
    emap: FixedGridMap,
    terrain=None,
    path: np.ndarray | None = None,
    title: str = "Ground-truth 2.5D map",
) -> Figure:
    """Two panels: the elevation map, and how densely each cell was sampled."""
    fig = Figure(figsize=(12.6, 5.6), dpi=130, facecolor=INK["surface"])
    ax_h, ax_n = fig.subplots(1, 2)

    im, _ = draw_map(ax_h, emap, terrain=terrain, path=path,
                     title="Elevation — hatched where never observed")
    cb = fig.colorbar(im, ax=ax_h, pad=0.015, fraction=0.045)
    cb.set_label("elevation (m)", color=INK["secondary"], fontsize=8)
    cb.ax.tick_params(colors=INK["muted"], labelsize=7)
    cb.outline.set_edgecolor(INK["grid"])
    ax_h.legend(
        handles=[mpatches.Patch(facecolor="#F5F6F3", hatch="///",
                                edgecolor=STATUS["never_fired"], label="Never observed")],
        loc="upper right", fontsize=7.5, framealpha=0.95, edgecolor=INK["grid"])

    _style(ax_n)
    counts = np.ma.masked_where(~emap.observed(), emap.n_obs)
    im2 = ax_n.imshow(counts, origin="lower", extent=emap.extent, cmap="magma",
                      norm=matplotlib.colors.LogNorm(vmin=1, vmax=max(2, emap.n_obs.max())),
                      interpolation="nearest")
    cb2 = fig.colorbar(im2, ax=ax_n, pad=0.015, fraction=0.045)
    cb2.set_label("returns per cell", color=INK["secondary"], fontsize=8)
    cb2.ax.tick_params(colors=INK["muted"], labelsize=7)
    cb2.outline.set_edgecolor(INK["grid"])
    if path is not None and len(path):
        ax_n.plot(path[:, 0], path[:, 1], color="white", lw=1.2, ls=":", zorder=5)
    ax_n.set_xlim(emap.extent[0], emap.extent[1])
    ax_n.set_ylim(emap.extent[2], emap.extent[3])
    ax_n.set_aspect("equal")
    ax_n.set_xlabel("x  (m)")
    ax_n.set_ylabel("y  (m)")
    ax_n.set_title("Sampling density — where the budget went", fontsize=10,
                   weight="bold", loc="left", color=INK["primary"])

    fig.suptitle(f"{title}     coverage {emap.coverage:.1%}",
                 fontsize=11, weight="bold", color=INK["primary"], x=0.007, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig
