"""Budget allocation: the protocol, the baselines, and (from M5) our method."""

from raysense.allocate.base import Allocator, WorldState
from raysense.allocate.baselines import (
    FullScan,
    RandomSubsample,
    StaticFrontROI,
    UniformDecimation,
)

BASELINES = {
    "full": FullScan,
    "uniform": UniformDecimation,
    "random": RandomSubsample,
    "front_roi": StaticFrontROI,
}

__all__ = [
    "BASELINES", "Allocator", "FullScan", "RandomSubsample", "StaticFrontROI",
    "UniformDecimation", "WorldState",
]
