"""Raysense — adaptive variable-resolution 2.5D lidar mapping.

SIH26053 (DRDO). The organising idea is that a lidar scan is a set of rays
that were *fired*, not merely a bag of points that came back: distinguishing
"nothing is there" from "nothing was sampled there" is what makes adaptive
sampling safe over terrain that contains ditches.
"""

__version__ = "0.1.0"
