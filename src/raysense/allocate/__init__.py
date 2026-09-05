"""Budget allocation: the protocol, the baselines, and (from M5) our method."""

from raysense.allocate.base import Allocator, WorldState
from raysense.allocate.baselines import FullScan, RandomSubsample, UniformDecimation

BASELINES = {
    "full": FullScan,
    "uniform": UniformDecimation,
    "random": RandomSubsample,
}

__all__ = [
    "BASELINES", "Allocator", "FullScan", "RandomSubsample",
    "UniformDecimation", "WorldState",
]
