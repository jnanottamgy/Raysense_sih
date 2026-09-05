"""RELLIS-3D reader.

RELLIS-3D is a real off-road UGV dataset - an Ouster OS1-64 on an all-terrain
platform in rugged terrain - and it is the primary evidence base for this
project. It follows SemanticKITTI file conventions::

    <sequence>/
      os1_cloud_node_kitti_bin/000000.bin        float32 (N, 4) x y z intensity
      os1_cloud_node_semantickitti_label_id/
                               000000.label      uint32  (N,) semantic + instance
      poses.txt                                  12 floats per line, 3x4 row-major
      calib.txt

NOT YET VERIFIED against the real dataset - it has not been downloadable in
this environment. The layout above is from the published RELLIS-3D
documentation and the loader validates aggressively rather than guessing, so a
mismatch fails loudly with a useful message instead of producing quiet
nonsense. Two things to confirm on first contact with real data:

  * whether `.label` packs instance id in the high 16 bits, as SemanticKITTI
    does - `semantic_label` assumes it does and masks them off
  * whether poses are sensor-frame or camera-frame, and the calib transform
    needed to reconcile them

`tests/test_rellis_io.py` exercises this against fixtures written in the same
format by `raysense.io.fixtures`, so the parsing logic is covered even while
the real bytes are out of reach.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

POINTS_DIR = "os1_cloud_node_kitti_bin"
LABELS_DIR = "os1_cloud_node_semantickitti_label_id"
POSES_FILE = "poses.txt"


@dataclass(frozen=True)
class RellisFrame:
    """One scan: points, optional per-point labels, and the sensor pose."""

    index: int
    points: np.ndarray                 # (N, 3) metres, sensor frame
    intensity: np.ndarray              # (N,)
    label: np.ndarray | None           # (N,) uint32 raw label word
    pose: np.ndarray | None            # (4, 4) sensor-to-world

    @property
    def n_points(self) -> int:
        return int(self.points.shape[0])

    @property
    def semantic_label(self) -> np.ndarray | None:
        """Class id with any instance id masked off (SemanticKITTI convention)."""
        return None if self.label is None else (self.label & 0xFFFF).astype(np.uint16)

    @property
    def ranges(self) -> np.ndarray:
        return np.linalg.norm(self.points, axis=1)

    def to_world(self) -> np.ndarray:
        """Points transformed into the world frame; requires a pose."""
        if self.pose is None:
            raise ValueError(f"frame {self.index} has no pose; cannot transform to world")
        return self.points @ self.pose[:3, :3].T + self.pose[:3, 3]


def read_bin(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a KITTI-style .bin point cloud -> (points (N,3), intensity (N,))."""
    raw = np.fromfile(str(path), dtype=np.float32)
    if raw.size % 4:
        raise ValueError(
            f"{path}: {raw.size} float32 values is not a multiple of 4 "
            "(expected x, y, z, intensity per point)"
        )
    pts = raw.reshape(-1, 4)
    return pts[:, :3].astype(np.float64), pts[:, 3].copy()


def read_label(path: str | Path, n_points: int | None = None) -> np.ndarray:
    """Read a SemanticKITTI-style .label file -> (N,) uint32."""
    lab = np.fromfile(str(path), dtype=np.uint32)
    if n_points is not None and lab.size != n_points:
        raise ValueError(
            f"{path}: {lab.size} labels for {n_points} points - "
            "label and point files are out of step"
        )
    return lab


def read_poses(path: str | Path) -> np.ndarray:
    """Read KITTI-odometry poses.txt -> (F, 4, 4) homogeneous transforms."""
    flat = np.loadtxt(str(path), dtype=np.float64)
    flat = np.atleast_2d(flat)
    if flat.shape[1] != 12:
        raise ValueError(
            f"{path}: expected 12 values per line (3x4 row-major), got {flat.shape[1]}"
        )
    poses = np.tile(np.eye(4), (flat.shape[0], 1, 1))
    poses[:, :3, :4] = flat.reshape(-1, 3, 4)
    return poses


class RellisSequence:
    """Frame-indexed access to one RELLIS-3D sequence directory."""

    def __init__(
        self,
        root: str | Path,
        points_dir: str = POINTS_DIR,
        labels_dir: str = LABELS_DIR,
    ) -> None:
        self.root = Path(root)
        if not self.root.is_dir():
            raise FileNotFoundError(f"sequence directory not found: {self.root}")

        self.points_dir = self.root / points_dir
        if not self.points_dir.is_dir():
            raise FileNotFoundError(
                f"no point-cloud directory at {self.points_dir}. "
                f"Expected a RELLIS-3D sequence containing '{points_dir}/'."
            )

        self.labels_dir = self.root / labels_dir
        self._bins = sorted(self.points_dir.glob("*.bin"))
        if not self._bins:
            raise FileNotFoundError(f"no .bin scans found in {self.points_dir}")

        poses_path = self.root / POSES_FILE
        self.poses = read_poses(poses_path) if poses_path.exists() else None

    def __len__(self) -> int:
        return len(self._bins)

    def __getitem__(self, i: int) -> RellisFrame:
        bin_path = self._bins[i]
        points, intensity = read_bin(bin_path)

        label = None
        label_path = self.labels_dir / f"{bin_path.stem}.label"
        if label_path.exists():
            label = read_label(label_path, n_points=points.shape[0])

        pose = None
        if self.poses is not None:
            if i >= len(self.poses):
                raise IndexError(
                    f"frame {i} has no pose: poses.txt holds {len(self.poses)} entries "
                    f"for {len(self)} scans"
                )
            pose = self.poses[i]

        return RellisFrame(
            index=i, points=points, intensity=intensity, label=label, pose=pose
        )

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    @property
    def has_labels(self) -> bool:
        return self.labels_dir.is_dir()

    def __repr__(self) -> str:
        return (
            f"RellisSequence({self.root.name}: {len(self)} frames, "
            f"labels={self.has_labels}, poses={self.poses is not None})"
        )
