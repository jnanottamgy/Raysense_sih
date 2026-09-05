"""Sensor geometry.

A `SensorModel` describes the beam pattern a lidar can emit. It is the object
that answers the first question any DRDO evaluator will ask - "what sensor
does this run on?" - and it carries the geometry the safety floor is derived
from.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from raysense.types import RayGrid


@dataclass(frozen=True)
class SensorModel:
    """A scanning lidar's native ray pattern.

    Beams are laid out on a regular grid: `n_beams` elevation rows spanning
    [v_fov_min_deg, v_fov_max_deg], by `n_azimuth` columns spanning
    [az_min_deg, az_max_deg]. Ray index is row-major (beam-major), so
    index = beam * n_azimuth + column.
    """

    name: str
    n_beams: int
    v_fov_min_deg: float
    v_fov_max_deg: float
    n_azimuth: int
    az_min_deg: float
    az_max_deg: float
    max_range: float
    frame_rate_hz: float = 10.0
    mount_height: float = 1.8      # metres above the vehicle's ground contact
    steerable: bool = False        # can it be told where to look?

    # ---------------------------------------------------------------- loading

    @classmethod
    def from_yaml(cls, path: str | Path) -> SensorModel:
        with open(path) as fh:
            raw = yaml.safe_load(fh)
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})

    # ------------------------------------------------------------- properties

    @property
    def n_rays(self) -> int:
        """Size of the full native ray grid - the denominator of every budget."""
        return self.n_beams * self.n_azimuth

    @property
    def delta_theta_v(self) -> float:
        """Vertical angular spacing between adjacent beams, radians."""
        span = np.deg2rad(self.v_fov_max_deg - self.v_fov_min_deg)
        return span / (self.n_beams - 1) if self.n_beams > 1 else span

    @property
    def delta_theta_h(self) -> float:
        """Horizontal angular spacing between adjacent columns, radians."""
        span = np.deg2rad(self.az_max_deg - self.az_min_deg)
        return span / self.n_azimuth if self.n_azimuth else span

    # --------------------------------------------------------- safety geometry

    def min_detectable_height(self, r: float | np.ndarray, delta_theta: float | None = None):
        """Smallest obstacle height guaranteed to be struck by a beam at range r.

        An object of height h at range r subtends an angle of about h/r at the
        sensor. For a beam to be guaranteed to fall within that extent, the
        angular sample spacing must satisfy dtheta <= h / r, so the smallest
        guaranteed-detectable height is::

            h_min(r) = r * dtheta

        This is the whole safety floor, and it is geometry rather than a tuned
        heuristic - which is precisely why it is defensible in front of a jury.
        """
        dt = self.delta_theta_v if delta_theta is None else delta_theta
        return np.asarray(r) * dt

    def required_delta_theta(self, h_target: float, r: float) -> float:
        """Angular spacing needed to guarantee detecting height `h_target` at `r`."""
        if r <= 0:
            raise ValueError(f"range must be positive, got {r}")
        return h_target / r

    def max_safe_range(self, h_target: float, delta_theta: float | None = None) -> float:
        """Furthest range at which `h_target` is still guaranteed detectable.

        The inverse reading of the safety floor, and the more useful one: given
        a sensor and a budget, this is how far ahead the vehicle can actually
        be trusted to see.
        """
        dt = self.delta_theta_v if delta_theta is None else delta_theta
        return h_target / dt if dt > 0 else float("inf")

    # ------------------------------------------------------------- ray grids

    def full_ray_grid(self, origin: np.ndarray | None = None) -> RayGrid:
        """Every ray the sensor can emit, in native (beam-major) order."""
        elev = np.deg2rad(np.linspace(self.v_fov_min_deg, self.v_fov_max_deg, self.n_beams))
        az = np.deg2rad(
            np.linspace(self.az_min_deg, self.az_max_deg, self.n_azimuth, endpoint=False)
        )
        az_grid, el_grid = np.meshgrid(az, elev)   # (n_beams, n_azimuth)
        return RayGrid(
            azimuth=az_grid.ravel(),
            elevation=el_grid.ravel(),
            origin=np.zeros(3) if origin is None else np.asarray(origin, dtype=float),
            max_range=self.max_range,
            beam_index=np.arange(self.n_rays),
        )

    def beam_of(self, ray_index: np.ndarray) -> np.ndarray:
        """Which elevation row each native ray index belongs to."""
        return np.asarray(ray_index) // self.n_azimuth

    def column_of(self, ray_index: np.ndarray) -> np.ndarray:
        """Which azimuth column each native ray index belongs to."""
        return np.asarray(ray_index) % self.n_azimuth
