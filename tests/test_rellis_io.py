"""RELLIS-3D reader, exercised against fixtures in the same on-disk format.

The real dataset is not downloadable in every environment, so the parsing path
is covered by round-tripping synthetic data through the exact byte layout the
reader expects. What remains unverified is only whether the real dataset uses
these conventions — which is called out in `raysense.io.rellis`.
"""

import numpy as np
import pytest

from raysense.io import RellisSequence
from raysense.io.fixtures import write_sequence
from raysense.io.rellis import POINTS_DIR, read_bin, read_label, read_poses


@pytest.fixture
def sequence(tmp_path):
    rng = np.random.default_rng(0)
    frames = [rng.normal(size=(50 + 10 * i, 3)) * 10 for i in range(3)]
    labels = [rng.integers(0, 20, size=len(f)).astype(np.uint32) for f in frames]
    poses = np.tile(np.eye(4), (3, 1, 1))
    poses[:, 0, 3] = [0.0, 1.0, 2.0]        # translate along x each frame
    write_sequence(tmp_path / "00000", frames, labels, poses)
    return tmp_path / "00000", frames, labels


def test_reads_frames_points_labels_and_poses(sequence):
    root, frames, labels = sequence
    seq = RellisSequence(root)
    assert len(seq) == 3

    f = seq[1]
    assert f.n_points == len(frames[1])
    assert np.allclose(f.points, frames[1], atol=1e-5)   # float32 on disk
    assert np.array_equal(f.semantic_label, labels[1].astype(np.uint16))
    assert f.pose[0, 3] == pytest.approx(1.0)


def test_semantic_label_masks_off_instance_bits(tmp_path):
    from raysense.io.fixtures import write_label

    sem = np.array([3, 17, 255], dtype=np.uint32)
    inst = np.array([1, 900, 4], dtype=np.uint32)
    write_label(tmp_path / "a.label", sem, inst)

    raw = read_label(tmp_path / "a.label")
    assert np.array_equal(raw & 0xFFFF, sem)
    assert np.array_equal(raw >> 16, inst)


def test_to_world_applies_the_pose(sequence):
    root, frames, _ = sequence
    f = RellisSequence(root)[2]
    assert np.allclose(f.to_world(), f.points + np.array([2.0, 0, 0]), atol=1e-5)


def test_missing_sequence_directory_says_so(tmp_path):
    with pytest.raises(FileNotFoundError, match="sequence directory not found"):
        RellisSequence(tmp_path / "nope")


def test_directory_without_scans_names_what_it_expected(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="os1_cloud_node_kitti_bin"):
        RellisSequence(tmp_path / "empty")


def test_truncated_bin_is_rejected(tmp_path):
    (tmp_path / "seq" / POINTS_DIR).mkdir(parents=True)
    bad = tmp_path / "seq" / POINTS_DIR / "000000.bin"
    np.arange(7, dtype=np.float32).tofile(bad)      # not a multiple of 4
    with pytest.raises(ValueError, match="not a multiple of 4"):
        read_bin(bad)


def test_label_count_mismatch_is_rejected(tmp_path):
    from raysense.io.fixtures import write_label

    write_label(tmp_path / "a.label", np.arange(5, dtype=np.uint32))
    with pytest.raises(ValueError, match="out of step"):
        read_label(tmp_path / "a.label", n_points=6)


def test_wrong_width_poses_file_is_rejected(tmp_path):
    p = tmp_path / "poses.txt"
    p.write_text("1 0 0 0 1 0\n")
    with pytest.raises(ValueError, match="12 values per line"):
        read_poses(p)
