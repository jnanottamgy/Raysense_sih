"""Budget allocation: the protocol, the baselines, and our method."""

from raysense.allocate.base import Allocator, WorldState
from raysense.allocate.baselines import (
    FullScan,
    RandomSubsample,
    StaticFrontROI,
    UniformDecimation,
)
from raysense.allocate.raysense import NeedWeights, RaysenseAllocator, VehicleModel

BASELINES = {
    "full": FullScan,
    "uniform": UniformDecimation,
    "random": RandomSubsample,
    "front_roi": StaticFrontROI,
    "raysense": RaysenseAllocator,
}

__all__ = [
    "BASELINES", "Allocator", "FullScan", "NeedWeights", "RandomSubsample",
    "RaysenseAllocator", "StaticFrontROI", "UniformDecimation", "VehicleModel",
    "WorldState",
]
