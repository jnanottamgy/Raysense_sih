"""Ray accounting: FREE vs SHADOW vs UNKNOWN vs CANDIDATE_NEGATIVE."""

from raysense.raycast.accounting import integrate_rays
from raysense.raycast.discontinuity import (
    find_discontinuities,
    mark_discontinuities,
    prune_candidates,
)

__all__ = [
    "find_discontinuities",
    "integrate_rays",
    "mark_discontinuities",
    "prune_candidates",
]
