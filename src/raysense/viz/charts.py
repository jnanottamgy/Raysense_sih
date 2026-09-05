"""Charts, generated from the sweep table. Never hand-drawn, never hand-typed.

The budget curve is the spine of the whole project, so it is built to be read
rather than admired: one measure per axis, a log budget axis because budgets
span two orders of magnitude, the full-scan ceiling as a reference rule rather
than a competing series, and every line labelled at its end so identity never
rests on colour alone.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from raysense.viz.palette import INK, SERIES_COLOR, SERIES_LABEL  # noqa: E402


def _style(ax) -> None:
    ax.set_facecolor(INK["surface"])
    ax.grid(True, color=INK["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK["muted"], labelsize=8.5, length=3)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK["grid"])
    ax.xaxis.label.set_color(INK["secondary"])
    ax.yaxis.label.set_color(INK["secondary"])


def _panel(ax, df: pd.DataFrame, metric: str, ylabel: str, title: str,
           lower_is_better: bool, pct: bool = False) -> None:
    _style(ax)

    ceiling = df[df.allocator == "full"]
    if len(ceiling):
        y = ceiling[metric].iloc[0] * (100 if pct else 1)
        ax.axhline(y, color=INK["muted"], lw=1.2, ls="--", zorder=1)
        ax.annotate(
            f"full scan  {y:.3g}{'%' if pct else ''}",
            xy=(0.015, y), xycoords=("axes fraction", "data"),
            xytext=(0, 5), textcoords="offset points",
            ha="left", fontsize=7.5, color=INK["muted"],
        )

    others = sorted(df[df.allocator != "full"].groupby("allocator"),
                    key=lambda kv: -kv[1].sort_values("fraction")[metric].iloc[-1])
    for rank, (name, grp) in enumerate(others):
        grp = grp.sort_values("fraction")
        x = grp["achieved_fraction"] * 100
        y = grp[metric] * (100 if pct else 1)
        colour = SERIES_COLOR.get(name, INK["secondary"])
        ax.plot(x, y, lw=2.0, color=colour, marker="o", ms=6,
                mfc=colour, mec=INK["surface"], mew=1.2, zorder=3,
                label=SERIES_LABEL.get(name, name))
        # direct label at the line's end — identity never rests on colour alone
        ax.annotate(
            SERIES_LABEL.get(name, name),
            xy=(x.iloc[-1], y.iloc[-1]),
            xytext=(8, 7 if rank == 0 else -8), textcoords="offset points",
            fontsize=8, color=colour, weight="bold", va="center",
        )

    ax.set_xscale("log")
    ax.set_xticks([2, 5, 10, 20, 35, 50, 75, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlim(1.6, 165)
    ax.set_xlabel("rays actually spent — share of a full scan (%)")
    ax.set_ylabel(f"{ylabel}  ({'lower' if lower_is_better else 'higher'} is better)")
    ax.set_title(title, fontsize=10.5, weight="bold", loc="left", color=INK["primary"])


def budget_curve(rows, title: str = "") -> Figure:
    """The first curve: map error and coverage against point budget."""
    df = pd.DataFrame(rows)
    df = df[df["final"]] if "final" in df else df

    fig = Figure(figsize=(13.4, 5.3), dpi=130, facecolor=INK["surface"])
    ax1, ax2 = fig.subplots(1, 2)

    _panel(ax1, df, "elev_rmse", "elevation RMSE (m)",
           "Map error where observed", lower_is_better=True)
    _panel(ax2, df, "coverage_recall", "share of ground-truth cells seen (%)",
           "How much of the world was seen at all", lower_is_better=False, pct=True)

    fig.suptitle(title or "Budget versus map quality",
                 fontsize=11.5, weight="bold", color=INK["primary"], x=0.007, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig


def convergence(rows, metric: str = "coverage_recall", title: str = "") -> Figure:
    """How each strategy accumulates knowledge as the vehicle drives."""
    df = pd.DataFrame(rows)
    fig = Figure(figsize=(7.6, 5.0), dpi=130, facecolor=INK["surface"])
    ax = fig.subplots()
    _style(ax)

    for (name, frac), grp in df.groupby(["allocator", "fraction"]):
        if name == "full":
            ax.plot(grp["frame"], grp[metric] * 100, lw=1.6, ls="--",
                    color=INK["muted"], zorder=2, label="Full scan")
            continue
        grp = grp.sort_values("frame")
        colour = SERIES_COLOR.get(name, INK["secondary"])
        ax.plot(grp["frame"], grp[metric] * 100, lw=1.5, color=colour,
                alpha=float(np.clip(frac * 1.3, 0.3, 1.0)), zorder=3)

    ax.set_xlabel("frame")
    ax.set_ylabel("share of ground-truth cells seen (%)")
    ax.set_title(title or "Coverage as the vehicle drives  (opacity = budget)",
                 fontsize=10.5, weight="bold", loc="left", color=INK["primary"])
    fig.tight_layout()
    return fig
