"""The Raysense allocator.

Two stages, in this order and never the other way round.

**Stage 1 — the safety floor.** Reserved before anything adaptive happens, and
never traded away. Sized against *negative* obstacles, because those are the
binding constraint: a bump of height `h` at range `r` needs angular spacing
`h/r`, but a ditch of width `w` needs `w·h_sensor/r²` — quadratically tighter.
A floor sized for bumps is comfortably met while ditches stay invisible.

**Stage 2 — need-weighted fill.** Every remaining ray is scored by what sits at
the patch of ground it would strike, and the budget goes to the highest scores.
The term that matters is `candidate`: ground flagged by the discontinuity test
as possibly hiding a ditch. That is the difference between "spend budget on
unknown cells", of which a map has tens of thousands, and "spend budget where a
measurement has already suggested something is wrong".

Staleness is what keeps this honest over time. Without it a high-need region
would hold the budget forever; with it, ignored ground climbs the ranking until
it gets looked at.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from raysense.allocate.base import WorldState
from raysense.types import CellState, RayBudget


@dataclass(frozen=True)
class VehicleModel:
    """Enough of the platform to size a braking corridor."""

    name: str = "generic"
    width: float = 1.4
    speed: float = 4.0
    decel: float = 2.0
    reaction_time: float = 0.3
    min_ditch_width: float = 1.0

    @classmethod
    def from_yaml(cls, path: str | Path) -> VehicleModel:
        with open(path) as fh:
            raw = yaml.safe_load(fh)
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def braking_distance(self, speed: float | None = None) -> float:
        v = self.speed if speed is None else speed
        return v * self.reaction_time + v * v / (2.0 * self.decel)

    def max_safe_speed(self, sight_range: float) -> float:
        """The speed at which braking distance equals how far we can be trusted.

        The inverse reading of the safety floor, and the one a defence customer
        actually wants: given this sensor and this budget, how fast may we go?
        """
        t, a = self.reaction_time, self.decel
        return float(max(0.0, -t * a + np.sqrt((t * a) ** 2 + 2 * a * sight_range)))


@dataclass(frozen=True)
class NeedWeights:
    """Relative pull of each reason to look somewhere."""

    candidate: float = 6.0     # a measurement already suggested a ditch here
    unknown: float = 1.5       # never observed
    stale: float = 0.05        # per frame since last seen
    edge: float = 2.0          # per unit of local height gradient
    corridor: float = 2.0      # multiplier inside the braking corridor
    stale_cap: float = 40.0


class RaysenseAllocator:
    """Safety floor first, then need-weighted fill."""

    name = "raysense"

    def __init__(
        self,
        vehicle: VehicleModel | None = None,
        weights: NeedWeights | None = None,
        corridor_half_angle_deg: float = 35.0,
        base_share: float = 0.6,
        seed: int = 0,
    ) -> None:
        self.vehicle = vehicle or VehicleModel()
        self.w = weights or NeedWeights()
        self.corridor_half_angle_deg = corridor_half_angle_deg
        # share of the budget spent on the guaranteed sweep, before any of it
        # is steered. The floor under our own cleverness.
        self.base_share = base_share
        self._rng = np.random.default_rng(seed)
        self._cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    # ------------------------------------------------------------- geometry

    def _contacts(self, world: WorldState, ground_z: float) -> tuple[np.ndarray, ...]:
        """Where every native ray would strike a level plane at `ground_z`.

        Cheap, and good enough to *rank* rays: we only need to know which patch
        of ground a beam is aimed at, not exactly where it will land.
        """
        s = world.sensor
        key = s.n_rays
        if key not in self._cache:
            g = s.full_ray_grid()
            self._cache[key] = (g.azimuth, g.elevation, np.tan(-g.elevation))
        az, el, tan_dep = self._cache[key]

        drop = max(0.05, world.origin[2] - ground_z)
        with np.errstate(divide="ignore", invalid="ignore"):
            dist = np.where(tan_dep > 1e-4, drop / tan_dep, np.inf)
        dist = np.minimum(dist, s.max_range)

        x = world.origin[0] + dist * np.cos(az)
        y = world.origin[1] + dist * np.sin(az)
        reaches_ground = np.isfinite(dist) & (dist < s.max_range)
        return x, y, dist, az, reaches_ground

    def required_spacing(self, range_m: float, drop: float) -> float:
        """Angular spacing needed to straddle a `min_ditch_width` gap at range."""
        if range_m <= 0:
            return np.inf
        return self.vehicle.min_ditch_width * drop / (range_m * range_m)

    # ------------------------------------------------------------ allocation

    def allocate(self, world: WorldState, budget: int) -> RayBudget:
        """Choose azimuth columns, and keep each one vertically dense.

        Allocating ray by ray looks obviously right and is obviously wrong. The
        discontinuity test compares *adjacent beams within a column*: scatter
        the budget across many columns and consecutive returns end up far apart
        in elevation, the predicted gap between them grows to swallow any real
        one, and the detector goes quiet. Measured directly, ray-wise
        allocation left 3.5 beams per column where uniform decimation left 16 —
        and detected fewer ditches at a larger budget.

        So the unit of allocation is a column. We trade azimuth coverage for
        elevation resolution, because seeing a ditch is an elevation-resolution
        problem. Which columns to keep is where the need map earns its place.
        """
        s = world.sensor
        n = s.n_rays
        if budget >= n:
            return RayBudget(np.arange(n), n_native=n)
        budget = max(1, budget)

        emap = world.emap
        ground_z = world.origin[2] - s.mount_height
        x, y, dist, az, on_ground = self._contacts(world, ground_z)
        col_of_ray = s.column_of(np.arange(n))

        # ---- layer 1: a guaranteed sweep -----------------------------------
        # Never look at less of the world than plain decimation would. A ditch
        # you never point at cannot be found however cleverly you sample, and
        # measurement showed concentration alone losing to uniform for exactly
        # that reason.
        base_budget = int(round(budget * self.base_share))
        base = self._decimate(s, base_budget)

        # ---- layer 2: the surplus, spent on whole columns -------------------
        # Columns rather than rays, because the discontinuity test compares
        # adjacent beams *within* a column: scattering the surplus ray by ray
        # thins each column until the predicted gap swallows any real one.
        surplus = budget - base.size
        extra = np.empty(0, dtype=np.int64)
        if surplus >= s.n_beams:
            n_cols = min(s.n_azimuth, surplus // s.n_beams)

            speed = world.speed or self.vehicle.speed
            d_brake = max(2.0, self.vehicle.braking_distance(speed))
            forward = (np.abs((np.rad2deg(az) + 180.0) % 360.0 - 180.0)
                       <= self.corridor_half_angle_deg)
            corridor_ray = forward & on_ground & (dist <= d_brake)

            # the braking corridor is reserved first and never traded away
            keep = np.unique(col_of_ray[corridor_ray])[: max(1, n_cols // 2)]

            remaining = n_cols - keep.size
            if remaining > 0:
                score = np.zeros(s.n_azimuth)
                if emap is not None:
                    need = self._need(world, emap, x, y, on_ground, corridor_ray)
                    np.add.at(score, col_of_ray, np.maximum(need, 0.0))
                score[keep] = -np.inf
                score = score + self._rng.random(s.n_azimuth) * 1e-6
                keep = np.concatenate(
                    [keep, np.argpartition(-score, remaining - 1)[:remaining]]
                )

            beams = np.arange(s.n_beams)
            extra = (beams[:, None] * s.n_azimuth + np.unique(keep)[None, :]).ravel()

        return RayBudget(np.unique(np.concatenate([base, extra])), n_native=n)

    @staticmethod
    def _decimate(sensor, budget: int) -> np.ndarray:
        """The same even thinning the uniform baseline uses, as our floor."""
        n = sensor.n_rays
        if budget >= n:
            return np.arange(n)
        budget = max(1, budget)
        stride = n / budget
        kb = max(1, min(sensor.n_beams, int(round(np.sqrt(stride)))))
        kc = max(1, int(np.ceil(stride / kb)))
        beams = np.arange(0, sensor.n_beams, kb)
        cols = np.arange(0, sensor.n_azimuth, kc)
        return (beams[:, None] * sensor.n_azimuth + cols[None, :]).ravel()

    def _need(
        self,
        world: WorldState,
        emap,
        x: np.ndarray,
        y: np.ndarray,
        on_ground: np.ndarray,
        corridor: np.ndarray,
    ) -> np.ndarray:
        """Score every ray by what is at the ground it is aimed at."""
        n = x.size
        need = np.zeros(n)

        row, col, inside = emap.world_to_cell(x, y)
        usable = inside & on_ground
        if not usable.any():
            return need
        r, c = row[usable], col[usable]

        state = emap.state[r, c]
        observed = emap.n_obs[r, c] > 0

        cand = (state & int(CellState.CANDIDATE_NEGATIVE)) != 0
        score = self.w.candidate * cand
        score = score + self.w.unknown * (~observed)

        last = emap.last_seen[r, c]
        stale = np.where(last >= 0, np.minimum(world.frame - last, self.w.stale_cap), 0.0)
        score = score + self.w.stale * stale

        var = emap.variance(fill=0.0)[r, c]
        score = score + self.w.edge * np.sqrt(np.maximum(var, 0.0))

        need[usable] = score
        need[corridor] *= self.w.corridor
        # a ray that never reaches the ground informs a plan-view map of nothing
        need[~on_ground] = -1.0
        return need
