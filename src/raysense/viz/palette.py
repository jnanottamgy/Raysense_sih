"""The project's visual system - one source of truth for every figure.

Colour is assigned by the job it does, never by taste:

* **Sequential** (elevation, range) - one hue, light to dark, deliberately
  desaturated so it reads as context rather than competing with the states
  drawn on top of it. Never a rainbow.
* **Categorical** (terrain states, planted feature kinds) - a fixed order of
  four hues, validated for colour-vision deficiency separation, lightness
  band, chroma floor and contrast against both light and dark surfaces. The
  same four steps clear every check on both surfaces, so figures do not need a
  separate dark palette.
* **Status** - non-returns are a *state*, not a magnitude, so they get a
  reserved colour and are never drawn from the categorical order.

UNKNOWN is drawn as hatching rather than a hue. That keeps the most important
state in the project out of the colour-separation problem entirely, and it
matches the cartographic convention for "no survey data here", which is
exactly what it means.
"""

from __future__ import annotations

from dataclasses import dataclass

from matplotlib.colors import LinearSegmentedColormap

from raysense.types import CellState


@dataclass(frozen=True)
class Palette:
    """Validated categorical steps, in fixed assignment order.

    Verified with the six-check validator on both the light (#fcfcfb) and dark
    (#1a1a19) chart surfaces: lightness band, chroma floor, CVD separation,
    normal-vision floor and contrast all pass. Do not re-step these casually -
    re-run the validator if you do.
    """

    negative: str = "#D2622A"    # ditches, craters - the danger state
    obstacle: str = "#7A55B5"    # positive obstacles - blocked
    traversable: str = "#2E9E68"  # confirmed drivable
    sensor: str = "#2C8FBF"      # rays, beams, the sensor itself

    @property
    def order(self) -> tuple[str, ...]:
        """Fixed assignment order. Never cycled; a fifth category folds in."""
        return (self.negative, self.obstacle, self.traversable, self.sensor)


PALETTE = Palette()

# Reserved status colours - never reused as a categorical slot.
STATUS = {
    "no_return": "#D2622A",   # fired, nothing came back — the evidence state
    "never_fired": "#B9BDB4",  # not sampled — absence of evidence, not evidence
}

# Text and chrome. Marks carry identity; text stays in ink.
INK = {
    "primary": "#14181A",
    "secondary": "#43504F",
    "muted": "#6E7B79",
    "grid": "#DFE3DC",
    "surface": "#FCFCFB",
}

# Sequential ramps: single hue, monotonic light -> dark, low chroma.
ELEVATION_CMAP = LinearSegmentedColormap.from_list(
    "raysense_elevation", ["#EFF1EC", "#A8B3A6", "#5F6E5F", "#2F3A30"]
)
RANGE_CMAP = LinearSegmentedColormap.from_list(
    "raysense_range", ["#E7EDF1", "#9FB6C4", "#5A7C90", "#27404E"]
)

# How each map state is drawn. `hatch` supplies secondary encoding where the
# state must survive colour-blindness, greyscale printing and a projector.
STATE_STYLE: dict[CellState, dict[str, str | None]] = {
    CellState.UNKNOWN: {"color": "#F0F1EE", "hatch": "///", "label": "Unknown"},
    CellState.FREE: {"color": "#E4E8E1", "hatch": None, "label": "Free"},
    CellState.SURFACE: {"color": "#A8B3A6", "hatch": None, "label": "Surface"},
    CellState.OBSTACLE: {"color": PALETTE.obstacle, "hatch": None, "label": "Obstacle"},
    CellState.SHADOW: {"color": "#C9CEC6", "hatch": "\\\\\\", "label": "Shadow"},
    CellState.CANDIDATE_NEGATIVE: {
        "color": PALETTE.negative,
        "hatch": "xxx",
        "label": "Candidate negative",
    },
    CellState.CONFIRMED_NEGATIVE: {
        "color": PALETTE.negative,
        "hatch": None,
        "label": "Confirmed negative",
    },
}

# Ground-truth feature kinds in the synthetic world.
FEATURE_COLOR = {"negative": PALETTE.negative, "positive": PALETTE.obstacle}

# Series identity on charts, keyed by allocator name. Colour follows the
# entity, never its rank — dropping a series from a plot must not repaint the
# survivors. `full` is a reference ceiling rather than a series, so it is drawn
# as a dashed rule in ink and holds no hue.
SERIES_COLOR = {
    "uniform": PALETTE.sensor,        # the honest naive baseline
    "random": PALETTE.obstacle,       # the null hypothesis
    "front_roi": PALETTE.traversable,  # M3 — the baseline a judge will propose
    "raysense": PALETTE.negative,     # M5 — ours
}
SERIES_LABEL = {
    "uniform": "Uniform decimation",
    "random": "Random subsample",
    "front_roi": "Static front ROI",
    "raysense": "Raysense",
    "full": "Full scan",
}
