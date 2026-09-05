# M3 + M4 — findings

**M3** (traversability, hazard metrics, `StaticFrontROI`) is complete.
**M4** is complete as specified — the property test passes — **but the mechanism the
build plan specified turns out to be the wrong one for this problem.** That is the
substance of this document, along with the verified replacement.

84 tests pass, lint clean.

---

## 1. The headline number, now measured properly

From 40 frames, with truth taken from the terrain rather than from what any scan saw:

| Budget spent | Positive obstacles detected | **Negative obstacles detected** |
|---:|---:|---:|
| 2% | 64.3% | 6.7% |
| 8.6% | 85.7% | 11.3% |
| 25% | 88.6% | 13.0% |
| 50% | 92.9% | 13.2% |
| **100%** | **92.9%** | **15.2%** |

**At full budget — every ray, forty frames — uniform scanning detects 93% of the things
sticking up and 15% of the things you can fall into.**

`StaticFrontROI` at 24% spend reaches 14.4% on negatives, *marginally better* than uniform
at 25% (13.0%) but nowhere near closing the gap. **Aiming does not fix this.** Ditches are
missed for geometric reasons, not for want of pointing the sensor in the right direction.
That is worth saying out loud to the judge who proposes the front-ROI baseline.

### The failure gets *worse* with more data

| Budget spent | Hazards admitted unknown | **Hazards waved through as drivable** |
|---:|---:|---:|
| 2% | 82.6% | **2.18%** |
| 25% | 68.7% | **5.35%** |
| 100% | 62.7% | **6.38%** |

More rays make the system more **confidently wrong**. It observes the rim of a trench,
finds it locally flat, and declares it drivable — while the interior is never observed at
any budget. A sparse budget leaves the same cells honestly `UNKNOWN`, which is the safe
behaviour.

This is why the metric is split three ways — detected / admitted unknown / waved through.
Collapsing the last two into "not detected" would hide the only distinction that matters
to a vehicle.

---

## 2. The M4 mechanism does not work. Here is the evidence.

The build plan specified: a ray fired into ground that comes back with nothing implies the
surface is lower than expected → `CANDIDATE_NEGATIVE`. That is signature **A** from the M0
findings. It is implemented, tested, and it fires — on the wrong cells.

Share of each planted ditch actually flagged, at full budget:

| Ditch | Width | Depth | Cells | **Flagged** |
|---|---:|---:|---:|---:|
| Trench | 2.4 m | 1.8 m | 240 | **0.0%** |
| Trench | 3.0 m | 2.2 m | 217 | **0.0%** |
| Crater | 9.0 m | 1.6 m | 401 | **0.0%** |
| Trench | 16.0 m | 6.0 m | 4,000 | **4.5%** |

3,593 cells were flagged in total, and almost none of them are inside a real ditch.
`results/m4_states_full.png` shows it plainly: the flags cluster at the **periphery of the
map**, where the flat-plane fallback for unmapped ground is simply wrong over rolling
terrain. The three narrow trenches remain white holes inside their ground-truth boxes.

**Why it fails.** A narrow trench is not *entered* by rays — it is **stepped over**. Beams
land before it and beyond it, each returning normally at its expected range. No ray comes
back empty, so no anomaly is raised. Signature A only fires when a ditch is wide and deep
enough to swallow rays outright, which is why only the 16 m × 6 m trench registered at all.

The apparent improvement in the sweep (11.5% → 15.2% on negatives) is therefore **not a
real win** — it is largely spurious flags that happen to land on hazard cells, plus the
`CANDIDATE_NEGATIVE → BLOCKED` rule catching rough terrain. It should not be quoted.

### It is also far too slow

Ray accounting pushed the loop from **93 ms to 989 ms per frame** at full budget. Ten times
over the real-time budget, for a mechanism that does not work.

---

## 3. The mechanism that *does* work — verified

Signature **B** from the M0 findings: a ditch that is stepped over leaves a **gap in the
ground returns larger than geometry allows**.

The test cannot use a fixed threshold, because ground sampling gaps grow quadratically with
range — that is the M0 result. Against a flat plane, a "2.2× the median gap" rule flags
seven false anomalies. The gap must be judged against what geometry **predicts at that
range**:

```
predicted_gap(r) = r² · Δθ / h            ← the M0 formula, used as a detector
anomaly          = measured_gap / predicted_gap(r)
```

Measured on forward-looking beams:

| Scene | max gap / predicted | Flagged at > 2× |
|---|---:|---:|
| Flat, no trench | 1.21 | **0** |
| Rolling terrain, no trench | 1.28 | **0** |
| 2.4 m × 1.8 m trench | **5.98** | 1, at x = 8.4 m |
| 3.0 m × 2.2 m trench | **8.56** | 1, at x = 7.9 m |

**Clean separation, zero false positives on both flat and rolling terrain**, on exactly the
trenches signature A scored 0.0% on.

Three things make this the right answer:

1. **It works** where the implemented mechanism does not.
2. **It is roughly a hundred times cheaper** — a sort and a diff per azimuth column,
   `O(rays)`, against the ray march's `O(rays × steps)`. It fixes the timing blowout as a
   side effect.
3. **It closes the argument.** The quadratic falloff discovered at M0 was the project's
   central *limitation*. Used this way it becomes the *detector*. The same formula states
   the danger and finds it.

This is also what the negative-obstacle literature actually uses — "spacing jump between
points" — which was in the M0 research and which I built the wrong half of.

---

## 4. What changes

**Into M5, ahead of the allocator:**

1. **Implement signature B** as the primary negative-obstacle detector, range-normalised
   as above. Keep signature A for ray-swallowing ditches; it is cheap and it catches the
   16 m case.
2. **Fix the false-positive source** — the flat-plane fallback for unmapped ground. Fit a
   local plane from nearby observations instead of assuming the sensor's own ground height
   out to 100 m.
3. **Re-time the loop.** The cheap detector should bring per-frame cost back under budget
   without needing Numba yet.

**For the allocator itself,** this sharpens the design considerably. "Spend budget on
unknown cells" is vague and the map has tens of thousands of them. "Spend budget resolving
range discontinuities that exceed geometric prediction" is specific, cheap to evaluate, and
points at exactly the cells where a ditch might be hiding.

**For the deck:** do not quote 15.2%, and do not present M4 as working. The honest and
stronger line is that the naive absence test fails on the ditches that matter, we can show
why, and the fix falls out of the same geometry that created the problem.

---

## What was built

| Module | State |
|---|---|
| `perceive/traversability.py` | Three-valued classification from step height, slope and roughness. No code path maps an unobserved cell to drivable. |
| `perceive/truth.py` | Ground truth rasterised from the terrain, so ditches no scan ever saw are still `BLOCKED` in truth. |
| `eval/metrics.py` | Traversability P/R/F1, the three-way hazard split, per-feature recall. |
| `allocate/baselines.py` | `StaticFrontROI` — dense forward wedge, remainder spread thin. |
| `raycast/accounting.py` | Signature-A absence reasoning. Correct as specified; see §2. |
| `viz/states.py` | The state map — unknown as hatching, suspected ditches in the reserved status colour. |

```bash
python scripts/run_sweep.py --frames 40 --allocators full uniform front_roi
python scripts/render_states.py --frames 40 --fraction 1.0
pytest -q && ruff check src tests scripts
```

## Still unverified

Unchanged: **`n_azimuth` for RELLIS-3D**, `.label` packing, the pose frame, and the
**official problem-statement text**. Everything here is measured on the synthetic course.

## Next — M5

Signature B, the false-positive fix, then the safety floor and the need-weighted allocator.
M5's exit criterion stands: **ours must beat `StaticFrontROI`.** On the evidence here the
margin will come from negative-obstacle recall, not from map error.
