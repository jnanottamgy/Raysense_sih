# M0 — findings

Milestone M0 is complete: repository skeleton, core data contract, sensor model,
synthetic off-road world with an analytic raycaster, a RELLIS-3D reader, and a
three-panel scan renderer. 31 tests pass, lint is clean.

Building it turned up two results that change the plan. Both fall out of
geometry, and both make the case stronger.

---

## 1. Negative obstacles degrade **quadratically** with range. Positive ones degrade linearly.

The safety floor in the battle plan was derived from positive obstacles:

```
h_min(r) = r · Δθ            a bump of height h at range r
```

That is right, and it is not the binding constraint. A **ditch** is missed when
it fits *between* two beams' ground contacts, so what matters is the spacing of
those contacts on the ground. For a sensor at height `h` on flat ground:

```
w_min(r) ≈ r² · Δθ / h       a ditch of width w at range r
```

**Quadratic in range**, and inversely proportional to mount height. Measured on
the raycaster against a perfectly flat plane, using the real Ouster OS1-64
geometry (64 beams over 45°, Δθ = 0.714°, mounted at 1.8 m):

| Range | Measured beam spacing on the ground | Small-angle prediction |
|---:|---:|---:|
| 9.6 m | **0.72 m** | 0.64 m |
| 16.0 m | **2.03 m** | 1.78 m |
| 20.7 m | **3.51 m** | 2.96 m |
| 32.1 m | **9.17 m** | 7.12 m |
| 41.2 m | **16.51 m** | 11.77 m |

The closed form is a small-angle approximation and it **understates** the real
spacing — by roughly 40% at 40 m. Quote the measured column, not the formula.

Side by side, the two floors on the same sensor:

| Range | Smallest detectable **bump** | Smallest detectable **ditch** |
|---:|---:|---:|
| 10 m | 0.12 m | 0.69 m |
| 20 m | 0.25 m | 2.77 m |
| 30 m | 0.37 m | 6.23 m |
| 40 m | 0.50 m | 11.08 m |
| 60 m | 0.75 m | 24.93 m |

**At 30 m a stock OS1-64 can drive past a six-metre-wide ditch and register
nothing at all.** Not a degraded reading — nothing.

### What this changes

- **The safety floor must be derived from the negative-obstacle case.** A floor
  sized for bumps is comfortably satisfied while ditches are invisible. The M5
  allocator constraint becomes `w_min`, not `h_min`.
- **This is the argument for adaptive allocation**, stated in DRDO's own terms.
  Uniform scanning spends its budget where the ground is already
  over-sampled — the spacing is 0.7 m at 10 m and 16 m at 40 m — while the
  dangerous band is under-sampled. Concentrating rays is not an efficiency
  nicety; it is the only way to extend the range at which a ditch is visible.
- **It sharpens the deck.** "Same recall, fewer points" is a good claim.
  "Your current sensor cannot see a 6 m ditch at 30 m, and here is what to do
  about it" is a much better one.

---

## 2. A negative obstacle has **three** signatures, not one

The build plan assumed the literature's rear-wall signature. Testing against the
raycaster shows that is only one of three outcomes, and which one occurs depends
on geometry the vehicle does not control:

| # | What the sensor sees | When |
|---|---|---|
| **A** | **No return at all** | the floor lies beyond max range, or the ray leaves the world first |
| **B** | **An anomalously long-range return** | the ray reaches the floor or far wall — the rear-wall signature |
| **C** | **A gap in ground returns where the ground plane predicted them** | **always** |

Both A and B are reproduced in `tests/test_sim.py`. A narrow trench at 18 m
produced **zero** returns inside its footprint while flat ground produced 16
from the same rays; a deep wide trench with its floor out of reach destroyed all
60 returns outright.

### What this changes

Detection cannot rest on the rear-wall signature alone, because case A has no
return to reason about. **Case C is the only universal one**, and it is a
statement about rays, not points: *a ray went there and did not come back where
the ground plane said it should.*

That is exactly the accounting `raycast/` was scheduled to build at M4, and it
is now load-bearing rather than a refinement. Case B, when present, promotes a
candidate to confirmed.

---

## What was built

| Module | State |
|---|---|
| `types.py` | `RayGrid`, `ScanResult`, `RayBudget`, `CellState`. Fired rays are carried alongside returns, so a non-return stays distinguishable from an unsampled direction. |
| `sensor/` | `SensorModel` from YAML; OS1-64 and a steerable MEMS profile; the safety-floor geometry with its inverse. |
| `sim/` | Heightfield terrain, fractal relief, planted trenches / craters / boulders with exact ground truth, vectorised analytic raycaster. 65,536 rays in ~0.85 s. |
| `io/` | RELLIS-3D reader plus fixtures that write the same on-disk format, so parsing is tested without the dataset. |
| `viz/` | Validated palette (six checks pass on light *and* dark surfaces) and the three-panel scan renderer. |

Run it:

```bash
python scripts/render_scan.py --out results/m0_synthetic.png     # works anywhere
python scripts/render_scan.py --rellis data/rellis/00000         # once downloaded
pytest -q && ruff check src tests scripts
```

The `sim/` module was scheduled for M6. Building it at M0 to unblock the data
problem means the negative-obstacle experiments are de-risked five milestones
early — and it is what produced both findings above.

---

## Still unverified

These are assumptions, clearly marked in the code, that only real data can settle:

1. **`n_azimuth` for RELLIS-3D.** The OS1-64 runs at 512, 1024 or 2048 columns;
   the config assumes 1024. This is the denominator of every budget fraction, so
   **check it before quoting any sweep number.**
2. **`.label` packing.** The reader assumes SemanticKITTI's `instance << 16 |
   semantic`. Tested against fixtures; unconfirmed against the real files.
3. **Pose frame.** Whether `poses.txt` is sensor-frame or camera-frame, and what
   `calib.txt` transform reconciles them.
4. **The official problem-statement text**, which nothing here has been checked
   against.

## Next — M1

`FixedGridMap`, the full-scan 2.5D elevation map, and the map renderer, so there
is a ground truth for every later comparison to be scored against.
