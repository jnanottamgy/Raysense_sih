"""Obstacle extraction and three-valued traversability."""

from raysense.perceive.traversability import (
    Traversability,
    TraversabilityConfig,
    classify,
)
from raysense.perceive.truth import feature_masks, true_heights, true_traversability

__all__ = [
    "Traversability", "TraversabilityConfig", "classify",
    "feature_masks", "true_heights", "true_traversability",
]
