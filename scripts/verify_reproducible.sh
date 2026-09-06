#!/usr/bin/env bash
# The freeze check: does this repository reproduce its own published numbers
# from a clean environment?
#
# Builds a fresh virtualenv from pyproject.toml alone — so a dependency that
# only works because it happens to be installed here will fail — reruns the
# pipeline, and diffs the result against the committed CSVs.
#
#     bash scripts/verify_reproducible.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${1:-/tmp/raysense-verify}"
cd "$ROOT"

echo "=== 1. fresh environment from pyproject.toml only ==="
rm -rf "$WORK"
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q --upgrade pip
"$WORK/venv/bin/pip" install -q -e ".[dev]"
PY="$WORK/venv/bin/python"
$PY -c "import raysense, numpy, matplotlib, yaml, pandas; print('  imports ok, raysense', raysense.__version__)"

echo
echo "=== 2. tests and lint ==="
$PY -m pytest tests -q
"$WORK/venv/bin/ruff" check src tests scripts

echo
echo "=== 3. rebuild ground truth and the sweep from scratch ==="
rm -rf "$WORK/cache" "$WORK/out"
mkdir -p "$WORK/out"
$PY scripts/build_ground_truth.py --frames 40 \
    --cache "$WORK/cache/gt.npz" --out "$WORK/out/gt.png" > "$WORK/gt.log"
tail -2 "$WORK/gt.log"
$PY scripts/run_sweep.py --frames 40 \
    --allocators full uniform front_roi raysense --fractions 0.02 0.05 0.10 0.20 \
    --gt "$WORK/cache/gt.npz" --csv "$WORK/out/sweep.csv" \
    --out "$WORK/out/curve.png" > "$WORK/sweep.log"

echo
echo "=== 4. compare against the committed numbers ==="
$PY - "$WORK/out/sweep.csv" <<'PYEOF'
import sys
import pandas as pd

cols = ["allocator", "fraction", "achieved_fraction", "coverage_recall",
        "negative_detected", "positive_detected", "corridor_negative_detected"]
fresh = pd.read_csv(sys.argv[1])
fresh = fresh[fresh["final"]][cols].sort_values(["allocator", "fraction"]).reset_index(drop=True)
old = pd.read_csv("results/final_sweep.csv")
old = old[old["final"]][cols].sort_values(["allocator", "fraction"]).reset_index(drop=True)

if fresh.shape != old.shape:
    print(f"  SHAPE MISMATCH: fresh {fresh.shape} vs committed {old.shape}")
    sys.exit(1)

num = fresh.select_dtypes("number")
delta = (num - old.select_dtypes("number")).abs().max().max()
print(f"  rows compared: {len(fresh)}")
print(f"  largest difference in any metric: {delta:.2e}")
if delta > 1e-9:
    print("  NOT BIT-IDENTICAL — investigate before freezing")
    print((num - old.select_dtypes("number")).abs().max().to_string())
    sys.exit(1)
print("  identical to the committed results")
PYEOF

echo
echo "=== FROZEN: reproduces from a clean environment ==="
