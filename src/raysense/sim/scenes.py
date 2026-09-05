"""The standard evaluation scenes.

Every milestone measures the same world, so numbers stay comparable across the
project. A scene fixes the terrain, the planted ground truth and the vehicle
path together, and is fully determined by its seed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from raysense.mapping import MapConfig
from raysense.sim.terrain import Terrain, make_terrain, straight_path


@dataclass(frozen=True)
class Scene:
    name: str
    terrain: Terrain
    path: np.ndarray
    map_config: MapConfig
    seed: int

    @property
    def n_frames(self) -> int:
        return len(self.path)


def offroad_course(seed: int = 7, n_frames: int = 40, speed: float = 4.0) -> Scene:
    """A traverse across rolling terrain past six planted features.

    Features sit at a spread of ranges and offsets from the path so the budget
    sweep has targets both in the braking corridor and out at the edge of
    usefulness, which is where the quadratic falloff in negative-obstacle
    detectability bites.
    """
    terrain = make_terrain(size_m=240.0, resolution=0.3, roughness=3.0, seed=seed)

    # Negative obstacles — the ones this project exists for.
    terrain.add_trench((10.0, 0.0), length=16.0, width=2.4, depth=1.8, angle_deg=90.0)
    terrain.add_trench((-15.0, 7.0), length=12.0, width=3.0, depth=2.2, angle_deg=90.0)
    terrain.add_crater((25.0, -9.0), radius=4.5, depth=1.6)
    # Floor out of reach at shallow incidence: the "no return at all" case.
    terrain.add_trench((52.0, 0.0), length=40.0, width=16.0, depth=6.0, angle_deg=90.0)

    # Positive obstacles, for contrast and for positive-recall scoring.
    terrain.add_boulder((0.0, 11.0), radius=1.5, height=1.2)
    terrain.add_boulder((31.0, 4.0), radius=1.1, height=0.9)

    # 2 m of travel per frame: a real traverse without an absurd frame count.
    path = straight_path((-40.0, 0.0), heading_deg=0.0, speed=speed,
                         n_frames=n_frames, rate_hz=speed / 2.0)

    return Scene(
        name="offroad_course",
        terrain=terrain,
        path=path,
        map_config=MapConfig(resolution=0.4, size_m=200.0, origin=(-100.0, -100.0)),
        seed=seed,
    )


SCENES = {"offroad_course": offroad_course}
