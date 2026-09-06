# Raysense — measured results

**SIH26053 · DRDO · Adaptive Variable Resolution 2.5D Lidar Mapping**

Every number here comes from a committed CSV in `results/`. None is typed by hand.
All are measured on the controlled testbed (`sim/scenes.py`, seed 7), where ground truth
is *known* rather than inferred — and **none has yet been corroborated on real sensor data.**

Supersedes the framing in `SIH_2026_RESEARCH.md`, `SIH26053_CRITIQUE.md` and
`RAYSENSE_BATTLE_PLAN.md`, which describe the original efficiency-through-allocation idea.

---

## The finding

A lidar on a ground vehicle sees **what sticks up** far better than **what you can fall
into**. From 40 full scans — every ray, forty times, no budget limit:

| | Detected |
|---|---:|
| Positive obstacles (boulders) | **92.9%** |
| Negative obstacles (trenches, craters) | **11.5%** |

Spending more rays cannot fix it: a full scan already spends everything. A narrow trench is
not entered by beams, it is **stepped over**.

Worse, the failure gets *more confident* with more data. The share of real hazards reported
as safe to drive over rises from 1.9% at a 2% budget to **6.4% at full scan** — the system
sees the trench rim, judges it flat, and calls it drivable while the interior is never
observed.

---

## Why: negative obstacles degrade quadratically

| | Smallest guaranteed detectable |
|---|---|
| A **bump** of height *h* at range *r* | `h ≥ r · Δθ` — linear |
| A **ditch** of width *w* at range *r* | `w ≥ r² · Δθ / h_sensor` — **quadratic** |

Measured against a level plane with real Ouster OS1-64 geometry (Δθ = 0.714°, 1.8 m mast):

| Range | Beam spacing on the ground (measured) | Smallest bump | Smallest ditch |
|---:|---:|---:|---:|
| 10 m | 0.72 m | 0.12 m | 0.69 m |
| 20 m | 3.51 m | 0.25 m | 2.77 m |
| 30 m | 9.17 m | 0.37 m | 6.23 m |
| 40 m | 16.51 m | 0.50 m | 11.08 m |

**At 30 m a stock OS1-64 can drive past a six-metre-wide ditch and register nothing.**
The closed form understates the real spacing by ~40% at 40 m, so quote the measured column.

### The speed limit that follows

A 1 m ditch is guaranteed straddled only out to **12 m**. With a 2 m/s² braking model that
caps safe speed at **6.4 m/s — about 23 km/h.**

> **A stock OS1-64 on a UGV that must never drive into a one-metre ditch cannot safely
> exceed 23 km/h, and the sensor gives no indication that this is so.**

---

## The detector

The same quadratic that causes the blindness, normalised, detects it. Two adjacent beams
that both return land a predictable distance apart on level ground; if the far one lands
much further out, the surface between them dropped away.

```
anomaly = measured gap ÷ predicted gap at that range
```

| Scene | Max ratio | Flags per scan |
|---|---:|---:|
| Flat ground | — | 0 |
| Rolling terrain | 2.48 | 70 |
| **Rolling + 2.4 m trench** | **7.28** | 299 |

### Threshold — chosen by sweep, not by eye

Scored against the *identical terrain with the ditches removed*, which is the only honest
control (`results/threshold_sweep.csv`):

| Threshold | Ditch recall | False cells | Precision |
|---:|---:|---:|---:|
| 2.0 | 94.0% | 3,883 | 45.6% |
| **3.0** | **88.0%** | **436** | **73.3%** |
| 4.0 | 82.6% | 249 | 82.7% |
| 7.0 | 59.6% | 0 | 92.2% |

**3.0 is the knee.** Against 2.0 it costs six points of recall and removes **89% of the
false flags**; going further costs another five points for far less. It is not clean — 73%
precision, not 100% — and that limitation is stated on the deck.

### What it buys

Negative obstacles detected, at threshold 3.0, with **plain uniform decimation** — no
allocator involved:

| Budget | Absence test (M4) | **Discontinuity test** |
|---:|---:|---:|
| 2% | 6.7% | **74.9%** |
| 5% | 9.7% | **91.4%** |
| 8.6% | 11.3% | **96.0%** |
| 100% | 15.2% | **99.8%** |

> **91% of negative obstacles at 5% of the point budget. A full scan with no absence
> reasoning finds 12%.** Twenty times fewer points, seven times better detection.

It costs **43 ms per frame**, against 500 ms for the absence test it replaces.

---

## The allocator: it wins on one metric and loses on the other

Both statements are true and they are not in tension.

**Whole-map recall** asks *did you eventually map every ditch, including one 60 m off your
route?* Coverage wins that, so plain decimation wins it:

| Budget | uniform | front_roi | raysense |
|---:|---:|---:|---:|
| 2% | **74.9%** | 64.5% | 57.6% |
| 5% | **91.4%** | 82.7% | 81.4% |

**Warning distance** asks *how far off was the ditch ahead when you noticed it?* That is
what a vehicle cares about, and concentration wins it:

| Budget | uniform | front_roi | **raysense** |
|---:|---:|---:|---:|
| 2% | 12.3 m | 19.1 m | **23.2 m** |
| 5% | 15.0 m | 21.5 m | **26.4 m** |
| 10% | 18.3 m | **30.2 m** | 28.3 m |
| 20% | 21.9 m | **30.2 m** | 28.3 m |

**At a 2% budget the allocator gives 1.88× the warning of uniform** — 5.8 seconds to react
instead of 3.1. It is also the only method that finds **all four** ditches at 2%.

Above about 10% the static front wedge overtakes it, and at 10% that wedge matches a full
scan's 30.2 m warning distance. **If the deck quotes an allocator number, quote the 2% one**
— and say the limitation before being asked.

Three allocator designs were built and measured; the first two lost outright:

1. **Ray-wise need-weighted top-k** left 3.5 beams per azimuth column where uniform left 16.
   The detector compares *adjacent beams within a column*, so thinning the column silences
   it. **An allocator that ignores its detector's structural requirement makes the system
   worse.**
2. **Column-wise** fixed that — 40× more gaps found at 2% — but covered too little of the
   scene to point at most ditches.
3. **Hybrid** — a guaranteed uniform sweep plus a steered surplus. This is the shipped one.

---

## The demo, frame by frame

Both systems at a **2% budget** — 1,280 rays against 1,256, so ours uses slightly *fewer*.
Left is what a conventional height-based system does; right is the need-weighted budget plus
the gap test. Approaching a 3 m wide, 2.2 m deep trench:

| Frame | Distance to ditch | Conventional | Raysense |
|---:|---:|---|---|
| 4 | 18.4 m | unknown ahead | **DITCH AHEAD** |
| 6 | 14.8 m | unknown ahead | **DITCH AHEAD** |
| **8** | **11.4 m** | **clear to drive** | **DITCH AHEAD** |
| 10 | 8.6 m | DITCH AHEAD | DITCH AHEAD |

**We warn at 18.4 m. The conventional system reports the ground as *clear to drive* at
11.4 m and only warns at 8.6 m** — 9.8 metres later, 2.5 seconds later at traverse speed,
and inside the braking distance it would need at any real speed.

It also does not hold: at frames 20 and 22 the conventional system reverts to *unknown
ahead*, because it is reasoning about heights it can see instead of gaps it cannot.

Reproduce: `python scripts/make_demo.py --fraction 0.02 --frames 40 --every 2`
Frame image: `results/demo_frames/frame_008.png`

---

## Honest limitations

1. **73% precision at threshold 3.0.** Crest occlusions produce genuine range gaps. Whether
   that is a false positive is arguable — the ground behind a crest *is* unobserved — but it
   is not zero.
2. **Smart allocation does not beat plain decimation on whole-map recall.** We say so.
3. **Nothing has touched real sensor data.** RELLIS-3D is the intended corroboration;
   `n_azimuth`, `.label` packing and the pose frame all remain unverified.
4. **The official problem-statement text has never been read.** Everything here is built
   from the title and the domain.

---

## Reproducing

**Verified.** `bash scripts/verify_reproducible.sh` builds a virtualenv from
`pyproject.toml` alone, rebuilds the ground truth and the sweep from nothing, and diffs the
result against the committed CSVs. Last run: **13 rows compared, largest difference in any
metric 0.00e+00 — bit-identical.**

```bash
python scripts/build_ground_truth.py --frames 40          # cached ground truth
python scripts/run_sweep.py --frames 40 \
    --allocators full uniform front_roi raysense           # the comparison
python scripts/threshold_sweep.py --frames 40              # the threshold curve
python scripts/make_demo.py --fraction 0.05 --frames 40    # the offline demo
pytest -q && ruff check src tests scripts                  # 103 tests
```

| Output | What |
|---|---|
| `results/final_sweep.csv` | every metric, every allocator, every budget |
| `results/final_sweep_detections.csv` | first-detection event per ditch per run |
| `results/threshold_sweep.csv` | the threshold curve with its control |
| `results/demo.html` | the offline demo player |
| `deck/Raysense_SIH26053_Idea.pdf` | six-slide idea submission |
