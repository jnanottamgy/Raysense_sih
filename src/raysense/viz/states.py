"""Render what the map *knows*, not just how high it is.

This is the panel the demo is built around. Three categories carry the whole
argument and they are drawn so that each survives colour-blindness, greyscale
printing and a bad projector:

* **drivable** — a hue
* **blocked** — a hue
* **unknown** — hatching, no hue at all, because it is the absence of a value
  rather than one more value
* **suspected ditch** — the reserved status colour, cross-hatched

A viewer should be able to point at the screen and say "you don't know what is
there" without being told which colour means what.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["hatch.linewidth"] = 0.6

import matplotlib.patches as mpatches  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from raysense.mapping import FixedGridMap  # noqa: E402
from raysense.perceive import Traversability, classify  # noqa: E402
from raysense.types import CellState  # noqa: E402
from raysense.viz.palette import INK, PALETTE, STATUS  # noqa: E402

_UNKNOWN_FILL = "#F5F6F3"


def _style(ax) -> None:
    ax.set_facecolor(INK["surface"])
    ax.tick_params(colors=INK["muted"], labelsize=8, length=3)
    for sp in ax.spines.values():
        sp.set_color(INK["grid"])
    ax.xaxis.label.set_color(INK["secondary"])
    ax.yaxis.label.set_color(INK["secondary"])


def _hatch_ground(ax, emap: FixedGridMap) -> None:
    """Everything starts unknown; observations are painted over it."""
    ax.add_patch(mpatches.Rectangle(
        (emap.extent[0], emap.extent[2]),
        emap.extent[1] - emap.extent[0], emap.extent[3] - emap.extent[2],
        facecolor=_UNKNOWN_FILL, hatch="///",
        edgecolor=STATUS["never_fired"], lw=0, zorder=0,
    ))


def draw_traversability(ax, emap: FixedGridMap, terrain=None, title: str = "") -> None:
    _style(ax)
    _hatch_ground(ax, emap)

    trav = classify(emap)
    known = trav != int(Traversability.UNKNOWN)
    img = np.ma.masked_where(~known, trav)
    ax.imshow(
        img, origin="lower", extent=emap.extent, zorder=1, interpolation="nearest",
        cmap=ListedColormap([_UNKNOWN_FILL, PALETTE.traversable, PALETTE.obstacle]),
        vmin=0, vmax=2,
    )

    if terrain is not None:
        for f in terrain.features:
            if f.kind != "negative":
                continue
            if f.label == "crater":
                p = mpatches.Circle(f.center, f.extent[0], fill=False,
                                    ec=INK["primary"], lw=1.4, ls="--", zorder=5)
            else:
                p = mpatches.Rectangle(
                    (f.center[0] - f.extent[1] / 2, f.center[1] - f.extent[0] / 2),
                    f.extent[1], f.extent[0], fill=False,
                    ec=INK["primary"], lw=1.4, ls="--", zorder=5)
            ax.add_patch(p)

    ax.set_xlim(emap.extent[0], emap.extent[1])
    ax.set_ylim(emap.extent[2], emap.extent[3])
    ax.set_aspect("equal")
    ax.set_xlabel("x  (m)")
    ax.set_ylabel("y  (m)")
    ax.set_title(title or "Can we drive here?", fontsize=10, weight="bold",
                 loc="left", color=INK["primary"])
    ax.legend(
        handles=[
            mpatches.Patch(fc=PALETTE.traversable, ec="none", label="Drivable"),
            mpatches.Patch(fc=PALETTE.obstacle, ec="none", label="Blocked"),
            mpatches.Patch(fc=_UNKNOWN_FILL, hatch="///",
                           ec=STATUS["never_fired"], label="Unknown"),
            mpatches.Patch(fc="none", ec=INK["primary"], ls="--", label="Real ditch"),
        ],
        loc="upper right", fontsize=7.5, framealpha=0.96, edgecolor=INK["grid"])


def draw_candidates(ax, emap: FixedGridMap, terrain=None, title: str = "") -> None:
    """Where the map has fired rays into ground that failed to answer."""
    _style(ax)
    _hatch_ground(ax, emap)

    surface = (emap.state & int(CellState.SURFACE)) != 0
    free = ((emap.state & int(CellState.FREE)) != 0) & ~surface
    cand = (emap.state & int(CellState.CANDIDATE_NEGATIVE)) != 0

    layer = np.zeros(emap.config.shape, dtype=float)
    layer[free] = 1
    layer[surface] = 2
    layer[cand] = 3
    ax.imshow(
        np.ma.masked_where(layer == 0, layer), origin="lower", extent=emap.extent,
        cmap=ListedColormap(["#E6EAE4", "#A8B3A6", PALETTE.negative]),
        vmin=1, vmax=3, zorder=1, interpolation="nearest",
    )

    if terrain is not None:
        for f in terrain.features:
            if f.kind != "negative":
                continue
            if f.label == "crater":
                p = mpatches.Circle(f.center, f.extent[0], fill=False,
                                    ec=INK["primary"], lw=1.4, ls="--", zorder=5)
            else:
                p = mpatches.Rectangle(
                    (f.center[0] - f.extent[1] / 2, f.center[1] - f.extent[0] / 2),
                    f.extent[1], f.extent[0], fill=False,
                    ec=INK["primary"], lw=1.4, ls="--", zorder=5)
            ax.add_patch(p)

    ax.set_xlim(emap.extent[0], emap.extent[1])
    ax.set_ylim(emap.extent[2], emap.extent[3])
    ax.set_aspect("equal")
    ax.set_xlabel("x  (m)")
    ax.set_ylabel("y  (m)")
    ax.set_title(title or "What the rays established", fontsize=10, weight="bold",
                 loc="left", color=INK["primary"])
    ax.legend(
        handles=[
            mpatches.Patch(fc="#A8B3A6", ec="none", label="Surface — a ray returned"),
            mpatches.Patch(fc="#E6EAE4", ec="none", label="Free — rays passed over"),
            mpatches.Patch(fc=PALETTE.negative, ec="none",
                           label="Suspected ditch — fired, no answer"),
            mpatches.Patch(fc=_UNKNOWN_FILL, hatch="///",
                           ec=STATUS["never_fired"], label="Unknown — never sampled"),
        ],
        loc="upper right", fontsize=7.5, framealpha=0.96, edgecolor=INK["grid"])


def render_states(emap: FixedGridMap, terrain=None, title: str = "") -> Figure:
    """Side by side: what the rays established, and what it means for driving."""
    fig = Figure(figsize=(13.2, 6.0), dpi=130, facecolor=INK["surface"])
    ax1, ax2 = fig.subplots(1, 2)
    draw_candidates(ax1, emap, terrain=terrain)
    draw_traversability(ax2, emap, terrain=terrain)
    fig.suptitle(title or "Ray accounting — absence as evidence",
                 fontsize=11.5, weight="bold", color=INK["primary"], x=0.007, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig
