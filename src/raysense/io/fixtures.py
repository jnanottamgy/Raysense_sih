"""Write RELLIS-3D-format files from synthetic data.

The real dataset cannot be downloaded in every environment, and waiting on it
would leave the reader untested. These helpers serialise arbitrary points into
exactly the on-disk layout `raysense.io.rellis` expects, so the parsing path -
dtype, packing, shape agreement, pose format - is covered by real round-trip
tests today, and only the assumptions about the *real* dataset's conventions
remain open.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from raysense.io.rellis import LABELS_DIR, POINTS_DIR, POSES_FILE


def write_bin(path: str | Path, points: np.ndarray, intensity: np.ndarray | None = None) -> None:
    """Serialise (N,3) points as a KITTI-style float32 x/y/z/intensity .bin."""
    points = np.asarray(points, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points must be (N, 3), got {points.shape}")
    inten = (
        np.zeros(points.shape[0], dtype=np.float32)
        if intensity is None
        else np.asarray(intensity, dtype=np.float32)
    )
    np.column_stack([points, inten]).astype(np.float32).tofile(str(path))


def write_label(path: str | Path, semantic: np.ndarray, instance: np.ndarray | None = None) -> None:
    """Serialise labels in SemanticKITTI packing: instance << 16 | semantic."""
    sem = np.asarray(semantic, dtype=np.uint32) & 0xFFFF
    inst = (
        np.zeros_like(sem)
        if instance is None
        else (np.asarray(instance, dtype=np.uint32) & 0xFFFF)
    )
    ((inst << 16) | sem).astype(np.uint32).tofile(str(path))


def write_poses(path: str | Path, poses: np.ndarray) -> None:
    """Serialise (F,4,4) transforms as 12 row-major values per line."""
    poses = np.asarray(poses, dtype=np.float64)
    if poses.ndim != 3 or poses.shape[1:] != (4, 4):
        raise ValueError(f"poses must be (F, 4, 4), got {poses.shape}")
    np.savetxt(str(path), poses[:, :3, :4].reshape(len(poses), 12), fmt="%.9f")


def write_sequence(
    root: str | Path,
    frames: list[np.ndarray],
    labels: list[np.ndarray] | None = None,
    poses: np.ndarray | None = None,
) -> Path:
    """Write a complete RELLIS-3D-shaped sequence directory and return its path."""
    root = Path(root)
    (root / POINTS_DIR).mkdir(parents=True, exist_ok=True)
    if labels is not None:
        (root / LABELS_DIR).mkdir(parents=True, exist_ok=True)

    for i, pts in enumerate(frames):
        write_bin(root / POINTS_DIR / f"{i:06d}.bin", pts)
        if labels is not None:
            write_label(root / LABELS_DIR / f"{i:06d}.label", labels[i])

    if poses is not None:
        write_poses(root / POSES_FILE, poses)
    return root
