# M5 + M6 — findings

**The detector is the contribution. The allocator is not.**

M5's exit criterion — *ours must beat `StaticFrontROI`* — is **not met**. The Raysense
allocator loses to plain uniform decimation at every budget, on every metric, including
one written specifically to favour it. That is reported here rather than tuned away,
and the reason it loses turns out to be the most useful thing this milestone produced.

103 tests pass, lint clean.

---

## 1. Signature B works, and it is the whole result

Replacing the M4 absence test with the range-normalised discontinuity test:

| Budget spent | Negative obstacles detected — **M4 absence test** | **M5 discontinuity test** |
|---:|---:|---:|
| 2% | 6.7% | **82.5%** |
| 5% | 9.7% | **96.0%** |
| 8.6% | 11.3% | **98.1%** |
| 100% | 15.2% | **100.0%** |

Both columns are plain uniform decimation. The allocator is not involved.

**The headline that survives everything below:**

> Uniform sampling at **5% of the point budget, with the detector**, finds **96%** of
> negative obstacles. A **full scan without it** finds **15%**.
> Twenty times fewer points, six times better detection.

The mechanism costs 43 ms per frame against the absence test's 500 ms, so it is also
twelve times cheaper than the thing it replaces.

---

## 2. Correction: the detector is not clean on rolling terrain

An earlier claim in this project — "zero false positives on flat and rolling terrain" —
was measured on a **single forward azimuth column**. Across a whole scan it is wrong:

| Scene | Returns | Flags raised | Rate | Max ratio |
|---|---:|---:|---:|---:|
| Flat | 31,744 | **0** | 0.00% | — |
| Rolling, no trench | 31,733 | **70** | 0.22% | 2.48 |
| Rolling + 2.4 m trench | 31,733 | 299 | 0.94% | **7.28** |

Flat ground really is clean. Rolling ground is not: crests occlude the ground behind
them, which produces a genuine range gap. Whether that is a false positive is arguable —
the ground behind a crest *is* unobserved — but it is certainly not zero, and the earlier
claim should not be repeated.

The separation is still strong: **2.48 against 7.28**. Raising the threshold from 2.0 to
about 3.0 would clear most terrain flags while keeping every trench. That is a tuning
question with a real answer, and it belongs in a sweep rather than in a guess.

---

## 3. The allocator loses. Three designs, none of them better than decimation.

Negative-obstacle detection at matched spend, 40 frames:

| Spent | uniform | front_roi | **raysense** |
|---:|---:|---:|---:|
| ~2% | **82.5%** | 84.3% | 64.4% |
| ~5% | **96.0%** | 90.8% | 91.8% |
| ~10% | **98.1%** | 97.7% | 96.5% |
| ~20% | **99.3%** | 98.7% | 98.8% |

Under the corridor-restricted metric — hazards within 12 m of the driven route, written
because whole-map recall weights a ditch 60 m off the path as heavily as one directly
ahead — the picture does not change. Uniform reaches **96.1% at 2% budget**; everything
saturates at 100% by 10%. The metric designed to favour concentration made the task
easier for every method equally.

### Three attempts, and what each one taught

**Ray-wise, need-weighted top-k.** Lost badly. Diagnosis, measured directly: it left
**3.5 beams per azimuth column** where uniform left 16. The discontinuity test compares
*adjacent beams within a column*; thin the column and consecutive returns land far apart
in elevation, the predicted gap grows to swallow any real one, and the detector goes
quiet. **An allocator that ignores its detector's structural requirement makes the system
worse, not better.**

**Column-wise.** Fixed that — 40× more discontinuities found at 2% budget. Still lost, now
on **coverage**: concentrating on 40 columns of 1024 means never pointing at most of the
ditches. You cannot detect what you never aim at.

**Hybrid — a guaranteed uniform sweep plus a steered surplus.** Closed most of the gap and
still did not cross it. The surplus buys extra beams in azimuths the base layer already
covers: more rays, no new ground.

### Why it cannot win here

Once the detector is this good, **the only thing that matters is pointing at more
ditches**, and that means maximum coverage. Concentration has nothing left to buy. Smart
allocation is the answer to *"I cannot afford to look everywhere well"*; signature B
removed the premise by making a cheap look good enough.

This is a real finding, not a failed experiment. It says something true about the problem:
**negative-obstacle detection is a detector problem, not an allocation problem.**

---

## 4. What survives, and it is strong

**The detector.** 15% → 96% at a twentieth of the budget, from one geometric test.

**The safety floor**, which stands on its own and needs no allocator:

```
ditch of width w at range r needs   Δθ ≤ w · h_sensor / r²
```

For a stock Ouster OS1-64 (Δθ = 0.714°, mounted at 1.8 m) and a 1 m ditch:

| Range | Spacing required | Sensor has | Met? |
|---:|---:|---:|:--|
| 8 m | 1.611° | 0.714° | yes |
| 12 m | 0.714° | 0.714° | **the limit** |
| 20 m | 0.258° | 0.714° | no |
| 40 m | 0.064° | 0.714° | no |

A 1 m ditch is guaranteed straddled only out to **12 m**. With this vehicle's braking
model that caps safe speed at **6.4 m/s — about 23 km/h.**

> **A stock OS1-64 on a UGV that must never drive into a one-metre ditch cannot safely
> exceed 23 km/h — and the sensor gives no indication that this is so.**

That is a capability statement about hardware DRDO already fields, derived from geometry,
and it does not depend on anything we built winning a comparison.

---

## 5. What this changes for the pitch

**Do not claim smart allocation.** It does not beat decimation on this problem and a jury
that asks for the baseline comparison will find out.

**Claim the detector and the floor.** Both are stronger, simpler and more defensible:

1. Your sensor sees 93% of what sticks up and 15% of what you can fall into.
2. One geometric test takes the second number to 96% — at a twentieth of the points.
3. The same geometry says how fast you may safely drive, and the answer is 23 km/h.

Leading with a negative result on our own idea is also the most credible thing we can do
in front of a technical jury: it demonstrates we ran the comparison honestly, which is
precisely what most teams cannot show.

---

## 6. What was built

| Module | State |
|---|---|
| `raycast/discontinuity.py` | Signature B. Local, geometric, `O(returns)`. |
| `allocate/raysense.py` | Safety floor sized on negative obstacles; `VehicleModel` with braking and max-safe-speed. Hybrid allocator — **does not beat the baselines.** |
| `eval/metrics.py` | Corridor-restricted recall and distance-to-path. |
| `configs/vehicle/warthog.yaml` | Braking model and minimum ditch width. |

```bash
python scripts/run_sweep.py --frames 40 --allocators full uniform front_roi raysense
pytest -q && ruff check src tests scripts
```

## Open

1. **Threshold sweep** for the discontinuity test — 2.0 keeps terrain flags, 3.0 probably
   does not. Measure it; do not guess.
2. **Does the allocator win under a time-to-detect metric?** Detecting a ditch four frames
   earlier matters operationally and no metric here captures it. If it does not win there
   either, drop the allocator from the deck entirely.
3. Unchanged and still gating anything quotable: **`n_azimuth` for RELLIS-3D**, `.label`
   packing, the pose frame, and the **official problem-statement text**.
