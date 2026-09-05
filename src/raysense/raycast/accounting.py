"""Ray accounting — where a scan's *absences* become evidence.

Integrating returns tells the map where surfaces are. This module tells it
about everywhere else, by following each fired ray and recording what its
outcome implies:

* **returned at range t** — `FREE` along the way, `SURFACE` at `t`.
* **no return, but it should have struck the predicted ground** — `FREE` up to
  that point, then `CANDIDATE_NEGATIVE`: the ground is lower than it ought to be.
* **no return, and it never would have struck ground** — it flew off into the
  sky and establishes nothing about the surface below.

Everything no ray ever crossed stays `UNKNOWN`, which is the zero state.

The middle row is the whole project. A ray that was fired into a patch of
ground and came back with nothing is not an absence of information — it is
information, and it says the surface is not where the map thinks it is. Without
this pass, a ditch and an unsampled direction are the same thing.
"""

from __future__ import annotations

import numpy as np

from raysense.mapping import FixedGridMap
from raysense.types import CellState, ScanResult


def _ground_at(emap: FixedGridMap, x: np.ndarray, y: np.ndarray, fallback: float) -> np.ndarray:
    """Predicted surface height, from the map where known, else a flat plane.

    The fallback matters on the frontier, where nothing has been observed yet:
    without it, a ray heading into unmapped ground could never be judged
    anomalous and every new ditch would be invisible on first sight.
    """
    row, col, inside = emap.world_to_cell(x, y)
    out = np.full(x.shape, fallback, dtype=float)
    if not inside.any():
        return out
    r, c = row[inside], col[inside]
    seen = emap.observed()[r, c]
    idx = np.flatnonzero(inside)[seen]
    out[idx] = emap.height()[r[seen], c[seen]]
    return out


def integrate_rays(
    emap: FixedGridMap,
    scan: ScanResult,
    frame: int = 0,
    step: float = 0.35,
    band: float = 2.0,
    ground_fallback: float | None = None,
) -> dict[str, int]:
    """Fold a scan's ray outcomes into the map's state grid.

    Only rays that can carry ground information are marched. In a 2.5D map a
    beam passing twenty metres overhead establishes nothing about the cell
    beneath it, so upward rays are dropped outright and the rest contribute
    only while they are within `band` metres of the predicted surface — the
    altitude range where "it flew over here without returning" is an actual
    upper bound on the ground height rather than a vacuous one.

    Returns a tally the sweep records: rays that returned, rays that implied a
    possible ditch, and rays that simply left.
    """
    fired = scan.fired
    o = np.asarray(fired.origin, dtype=float)
    d = fired.directions()
    m = fired.n_rays
    if m == 0:
        return {"returned": 0, "candidate_negative": 0, "to_sky": 0}

    returned = scan.returned_mask()
    t_end = np.full(m, fired.max_range)
    t_end[scan.ray_index] = np.linalg.norm(scan.points - o, axis=1)

    if ground_fallback is None:
        ground_fallback = float(_ground_at(emap, o[:1], o[1:2], o[2] - 1.8)[0])

    # Upward rays cannot inform a plan-view map; drop them before marching.
    informative = fired.elevation <= np.deg2rad(1.0)
    alive = np.flatnonzero(informative)
    n_sky = int((~informative).sum())

    free_row: list[np.ndarray] = []
    free_col: list[np.ndarray] = []
    cand_row: list[np.ndarray] = []
    cand_col: list[np.ndarray] = []

    n_steps = int(np.ceil(fired.max_range / step))
    for i in range(1, n_steps + 1):
        if alive.size == 0:
            break
        t = i * step
        alive = alive[t < t_end[alive]]          # returned rays stop at their hit
        if alive.size == 0:
            break

        p = o + d[alive] * t
        g = _ground_at(emap, p[:, 0], p[:, 1], ground_fallback)
        row, col, inside = emap.world_to_cell(p[:, 0], p[:, 1])

        # crossed below the predicted surface without returning: the ground is
        # not where the map thinks it is
        under = (p[:, 2] <= g) & ~returned[alive]
        if under.any():
            ok = under & inside
            cand_row.append(row[ok])
            cand_col.append(col[ok])

        # within the informative band, and still above the surface
        useful = inside & ~under & (p[:, 2] - g < band)
        if useful.any():
            free_row.append(row[useful])
            free_col.append(col[useful])

        alive = alive[~(under | (p[:, 2] <= g))]

    if free_row:
        fr, fc = np.concatenate(free_row), np.concatenate(free_col)
        emap.state[fr, fc] |= int(CellState.FREE)

    n_cand = 0
    if cand_row:
        cr, cc = np.concatenate(cand_row), np.concatenate(cand_col)
        emap.state[cr, cc] |= int(CellState.CANDIDATE_NEGATIVE)
        # a suspected ditch is not free space, whatever a passing ray implied
        emap.state[cr, cc] &= ~int(CellState.FREE)
        emap.last_seen[cr, cc] = frame
        n_cand = int(np.unique(np.stack([cr, cc]), axis=1).shape[1])

    return {
        "returned": int(returned.sum()),
        "candidate_negative": n_cand,
        "to_sky": n_sky,
    }
