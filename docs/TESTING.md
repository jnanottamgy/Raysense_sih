# How to test this

Nothing here needs a GPU, a dataset download, or a network connection. Python 3.11+ and
about ten minutes.

---

## Setup — 1 minute

```bash
git clone https://github.com/jnanottamgy/Raysense_sih
cd Raysense_sih
git checkout claude/sih-2026-hackathon-research-7r18pt

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

If `pip install -e .` fails, that is itself a finding — the dependency list is meant to be
complete. Report the error rather than installing something extra by hand.

---

## The 20-second smoke test

```bash
pytest -q
```

**Expect:** `103 passed`, about 17 seconds.

Two of those tests are worth reading rather than just running, because they are the project's
safety argument in executable form:

- `tests/test_perceive.py::test_unknown_never_becomes_traversable` — across 25 randomised
  maps, a cell nobody observed is never reported as drivable.
- `tests/test_sim.py::test_deep_trench_can_destroy_returns_entirely` — a ditch whose floor is
  out of sensor range returns *nothing*, and all 60 rays are still on record as fired.

---

## The one command that checks everything

```bash
bash scripts/verify_reproducible.sh
```

**Expect,** after roughly 8 minutes:

```
rows compared: 13
largest difference in any metric: 0.00e+00
identical to the committed results
=== FROZEN: reproduces from a clean environment ===
```

It builds a *separate* virtualenv from `pyproject.toml` alone, reruns the ground truth and
the full sweep from nothing, and diffs against the committed CSVs. If any number moved, it
exits non-zero and prints which metric.

---

## Seeing it work, piece by piece

Every script takes `--help`.

| Command | Time | What you get |
|---|---|---|
| `python scripts/render_scan.py --out out.png` | 3 s | One lidar scan, three panels. **Middle panel is the thesis:** orange is "fired, nothing came back". |
| `python scripts/build_ground_truth.py --frames 40` | 40 s | The 2.5D map from 40 *full* scans. **The trenches render as white holes** — unobserved at full budget. |
| `python scripts/run_sweep.py --frames 40 --allocators full uniform front_roi raysense` | 90 s | The comparison table and budget curve. |
| `python scripts/threshold_sweep.py --frames 40` | 3 min | The threshold curve, scored against terrain with the ditches removed. |
| `python scripts/make_demo.py --fraction 0.02 --frames 40` | 3 min | `results/demo.html` — open it with the network off. |

---

## How to try to break it

This is the part that matters. Everything above only shows the claims reproduce; these check
they are not baked in. **If any of these does not behave as described, the result is wrong
and we need to know.**

### 1. Change the world

```bash
python scripts/build_ground_truth.py --seed 42 --frames 40 --force \
    --cache cache/gt42.npz --out results/gt42.png
python scripts/run_sweep.py --seed 42 --frames 40 --gt cache/gt42.npz \
    --allocators full uniform --csv /tmp/s42.csv --out /tmp/c42.png
```

Different terrain, different ditch placements. **The detection numbers should stay in the
same region.** If they collapse, the result was tuned to one map.

### 2. Turn the detector off

```bash
python scripts/run_sweep.py --frames 40 --allocators full uniform \
    --no-ray-accounting --csv /tmp/off.csv --out /tmp/off.png
```

**`neg.det` should fall to roughly 10–15%** at every budget, including full scan. That
collapse *is* the contribution — if the numbers barely move, the detector is not doing the
work we say it is.

### 3. Move the threshold

Edit `DEFAULT_THRESHOLD` in `src/raysense/raycast/discontinuity.py`.

- **Set it to 1.5** → recall rises toward 98%, false flags rise about ninefold.
- **Set it to 7.0** → false flags reach zero, recall falls to about 60%.

If recall and precision do *not* trade against each other, the detector is keying on
something other than the geometry we claim.

### 4. Check the safety floor is geometry, not a fitted constant

```bash
python -c "
from raysense.sensor import SensorModel
import numpy as np
s = SensorModel.from_yaml('configs/sensor/ouster_os1_64.yaml')
for r in (10, 20, 40):
    print(f'{r:3d} m: bump {s.min_detectable_height(r):.2f} m, '
          f'ditch {r*r*s.delta_theta_v/1.8:.2f} m')
"
```

**Expect** the bump column to double as range doubles, and the ditch column to **quadruple**.
That ratio is the whole argument. It is arithmetic, so it cannot be tuned.

### 5. Read the frame the demo is built on

`results/demo_frames/frame_008.png`. Both systems, 2% budget, a trench 11.4 m ahead.
Left says **clear to drive**; right says **DITCH AHEAD**. Check the ray counts in the
counter strip — ours uses **1,256** against the baseline's **1,280**. If ours were spending
more, the comparison would be worthless.

---

## What a failure looks like

| Symptom | What it means |
|---|---|
| `pip install -e .` fails | The dependency list is incomplete. A real bug — tell us. |
| Tests pass, `verify_reproducible.sh` reports a non-zero difference | Something is non-deterministic. The numbers cannot be quoted until it is found. |
| `neg.det` stays high with `--no-ray-accounting` | The measurement is not isolating the detector. The headline claim would be wrong. |
| The trenches are *not* white holes in the ground-truth map | The scene is not being built as described. |

---

## What this does not test

**Real sensor data.** Every number is from the synthetic testbed, where ground truth is
*known* rather than inferred. That is a deliberate choice — public off-road datasets contain
almost no labelled ditches — but it means none of this has met a real lidar. RELLIS-3D
corroboration is the outstanding work, and `scripts/download_rellis.sh` lays out the
directory structure it expects.
