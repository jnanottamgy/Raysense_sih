#!/usr/bin/env bash
# Fetch RELLIS-3D — the primary evidence base for this project.
#
# The dataset is hosted by the Texas A&M Unmanned Systems Lab. Links, licence
# and the full file listing are at:
#
#     https://github.com/unmannedlab/RELLIS-3D
#
# It is distributed via Google Drive rather than direct HTTP, so this script
# does not fetch it for you — it lays out the expected directory structure and
# checks what is present. Download the two Ouster archives per sequence:
#
#     os1_cloud_node_kitti_bin          point clouds
#     os1_cloud_node_semantickitti_label_id
#                                       per-point semantic labels
#     poses.txt / calib.txt             pose and calibration
#
# Start with sequence 00000 — one sequence is enough through milestone M4.
set -euo pipefail

ROOT="${1:-data/rellis}"
mkdir -p "$ROOT"
echo "RELLIS-3D root: $ROOT"
echo
echo "Expected layout:"
echo "  $ROOT/00000/os1_cloud_node_kitti_bin/*.bin"
echo "  $ROOT/00000/os1_cloud_node_semantickitti_label_id/*.label"
echo "  $ROOT/00000/poses.txt"
echo
found=0
for seq in "$ROOT"/*/; do
  [ -d "$seq" ] || continue
  n=$(find "$seq/os1_cloud_node_kitti_bin" -name '*.bin' 2>/dev/null | wc -l)
  l=$(find "$seq/os1_cloud_node_semantickitti_label_id" -name '*.label' 2>/dev/null | wc -l)
  p=$([ -f "$seq/poses.txt" ] && echo yes || echo NO)
  echo "  $(basename "$seq"): $n scans, $l labels, poses: $p"
  found=$((found + 1))
done
[ "$found" -eq 0 ] && echo "  (nothing downloaded yet)"
echo
echo "Then verify the reader against real bytes:"
echo "  python scripts/render_scan.py --rellis $ROOT/00000 --frame 0 --out results/m0_rellis.png"
