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
false flags**; going further costs another five points for far less.

### The crest guard — what those 436 false cells actually were

A crest occlusion makes the same signature as a ditch: the ground rises, the far beam clears
the rise, and the shadow behind it is a range gap geometry cannot explain. There is one
physical asymmetry, and it turns out to be decisive — **a crest is reached uphill, a ditch
is not.**

`scripts/crest_study.py` measures the approach slope of every flagged gap, taken from the
previous return in the same azimuth column. Positives are gaps whose span overlaps a planted
ditch; negatives are every gap found on the identical ditch-free control
(`results/crest_study.csv`, 670 ditch gaps against 68 control gaps):

| approach slope | p10 | p50 | p90 | max / min |
|---|---:|---:|---:|---|
| gaps over a real ditch | −0.02 | **0.00** | 0.01 | max **0.039** |
| gaps on the ditch-free control | 0.22 | **0.46** | 0.71 | min (with evidence) **0.069** |

**The two populations do not overlap.** `CREST_RISE = 0.10` sits above the ditch population
rather than between the two, so the bias is toward keeping a ditch rather than dropping one.
Where there is no previous return in the column there is no evidence, and the guard does not
fire.

Re-running the identical sweep with the guard on (`results/threshold_sweep_crest.csv`):

| Threshold | Ditch recall | False cells | Precision |
|---:|---:|---:|---:|
| 2.0 | 94.0% | 3,883 → **132** | 45.6% → **70.9%** |
| 2.5 | 90.8% | 1,954 → **18** | 57.4% → **76.0%** |
| **3.0** | **88.0%** (unchanged) | 436 → **5** | 73.3% → **79.4%** |
| 4.0 | 82.6% | 249 → **0** | 82.7% → **87.3%** |

> **Recall is unchanged at every threshold. False cells on the control fall 436 → 5, a 98.9%
> reduction, and precision gains 6.1 points.** The headline detection numbers are untouched:
> 74.9 / 91.4 / 96.0 / 98.3% at 2 / 5 / 10 / 20% budget, identical before and after
> (`results/final_sweep_crest.csv`). Full scan moves 99.8% → 99.6%, and flagged area at full
> scan falls by a third — 103,443 cells to 67,952.

The remaining 79.4% is no longer dominated by false alarms: only **5 cells** flag on
ditch-free terrain. What the proxy counts as imprecision is now mostly the flagged span
overrunning the true ditch rectangle — localisation slop, not a phantom hazard.

### Why precision stops at 79% — and what buying more of it costs

Once the crest guard removes the phantom hazards, the remaining imprecision is
**localisation, not detection**. `mark_span` paints every cell between the near and far
return, and both of those are returns — measured ground. A span that brackets a 2.4 m
trench starting 2 m short of it necessarily paints metres of solid ground too. Of every
flagged cell: **79.2% sit inside a real ditch, 15.5% within 3 m of one, 3.3% further away.**

Two levers are shipped, both **off by default**, and `scripts/localise_study.py` measures
what each costs (`results/localise_study.csv`, uniform at 5% over 40 frames):

| trim | rim | detected | **missed-unsafe** | candidate precision |
|---:|---:|---:|---:|---:|
| **0.0** | **off** | **91.4%** | **0.00%** | **79.4%** |
| 0.0 | 2 | 91.3% | 0.04% | 84.6% |
| 0.3 | off | 91.6% | 0.02% | 82.5% |
| 0.3 | 2 | 91.6% | 0.04% | 86.7% |
| 0.3 | 1 | 91.5% | 0.14% | 90.3% |
| 0.6 | 2 | 90.9% | 0.04% | **87.5%** |
| 0.6 | 1 | 90.8% | 0.14% | **90.7%** |

`trim` leaves *n* metres unpainted at each end of a span. `rim` keeps the flag only on
cells nobody observed, plus that many cells of lip around them — a cell we got a return
from is measured ground and cannot be a hole, except at the edge of one.

**Precision above 87% is available, and it is not free.** Every row that reaches it moves
`negative_missed_unsafe` — the share of real ditch cells the system calls *drivable* — off
zero. The cells it costs are on the floor of the shallow 1.6 m crater: broad, observed,
and locally flat, so the height test alone calls them traversable and only the
candidate flag holds them back.

> **We ship the 79.4% row.** It is the only setting where nothing real is waved through,
> and on a system whose entire claim is that it never turns *"I did not look there"* into
> *"safe to drive"*, that column outranks the precision column. The levers exist, the
> curve is committed, and a platform that would rather take the misses than the false
> alarms can move along it in one argument.

**The guard also moves the knee.** With it on, threshold **2.5 beats the shipped unguarded
3.0 on every axis at once** — 90.8% recall against 88.0%, 18 false cells against 436, 76.0%
precision against 73.3%. We have not moved the shipped threshold, because every other number
in this document is measured at 3.0 and re-baselining them is a separate exercise. It is the
obvious next change.

**The limitation, measured rather than guessed** (`tests/test_discontinuity.py`). On a
uniform uphill approach the guard keeps the trench to a **10% grade**. At **12%** the
detector can still see it but the guard suppresses it. From about **15%** the trench is
invisible to the detector with or without the guard, because the near rim occludes it. So
the harm window is roughly **11–14% of uphill grade**, and outside it the guard costs
nothing.

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

### What it costs — measured, not estimated

`scripts/benchmark.py` times the four stages a vehicle actually runs per frame —
allocate, acquire, integrate, detect — over 20 frames x 5 repeats. Generating the scan is
excluded: on a vehicle the sensor does that. Machine: **Intel Xeon @ 2.10 GHz, 4 cores,
Python 3.11.15, NumPy 2.4.6** (`results/benchmark.csv`).

| Budget | allocate | acquire | integrate | **detect** | **TOTAL** | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 2% | 0.22 | 0.10 | 0.16 | **0.18** | **0.71 ms** | 1.22 ms |
| **5%** | 0.56 | 0.19 | 0.32 | **0.34** | **1.48 ms** | **2.20 ms** |
| 10% | 0.96 | 0.28 | 0.48 | **0.94** | **2.66 ms** | 8.76 ms |
| 100% | 11.10 | 1.32 | 4.05 | **12.42** | **28.77 ms** | 35.78 ms |

**1.5 ms at the 5% budget that produces the 91.4% result** — against a 100 ms frame at
10 Hz, that is **67x headroom**. Cost is linear in rays: **0.44 µs per ray, R² = 0.9998**.

The absence test this replaces costs **252 ms at the same 5% budget** and 793 ms at full
scan — it cannot run in real time at all, which is the practical argument for the gap test
beyond the 9.7% -> 91.4% detection difference.

With the steered `raysense` allocator instead of uniform decimation, the need-map scoring
adds a fixed ~5.5 ms: 7.5 ms at 5% (`results/benchmark_raysense.csv`). Still 13x inside
the frame.

> **Correction.** Earlier drafts of this document and the deck quoted *"43 ms per frame
> against 500 ms"*. That number was never written to a CSV and does not reproduce. It
> appears to have been the steered allocator at or near a **full** budget (arithmetic on
> the measured fit gives 45.5 ms at 100%), quoted next to a **5%** detection result. The
> table above supersedes it. The error understated the system.

**Not measured: any embedded or ARM device.** The benchmark takes `--label`, so a Jetson
run produces a comparable row with one command. Until someone runs it, we quote no Jetson
number.

---

## The allocator: it wins on one metric and loses on the other

Both statements are true and they are not in tension.

**Whole-map recall** asks *did you eventually map every ditch, including one 60 m off your
route?* Coverage wins that, so plain decimation wins it:

| Budget | uniform | front_roi | raysense |
|---:|---:|---:|---:|
| 2% | **74.9%** | 64.5% | 57.6% |
| 5% | **91.4%** | 82.5% | 79.3% |

**Warning distance** asks *how far off was the ditch ahead when you noticed it?* That is
what a vehicle cares about, and concentration wins it:

| Budget | uniform | front_roi | **raysense** |
|---:|---:|---:|---:|
| 2% | 12.3 m | 16.5 m | **24.5 m** |
| 5% | 15.0 m | 21.5 m | **25.9 m** |
| 10% | 16.3 m | **28.2 m** | 26.3 m |
| 20% | 22.0 m | **28.2 m** | 26.3 m |

**At a 2% budget the allocator gives 1.99× the warning of uniform** — 6.1 seconds to react
instead of 3.1. It is also the only method that finds **all four** ditches at 2%.

Above about 10% the static front wedge overtakes it, and at 10% that wedge matches a full
scan's 28.2 m warning distance. **If the deck quotes an allocator number, quote the 2% one**
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
| 3 | 20.2 m | unknown ahead | unknown ahead |
| 4 | 18.4 m | unknown ahead | **DITCH AHEAD** |
| 5 | 16.6 m | unknown ahead | **DITCH AHEAD** |
| 6 | 14.8 m | unknown ahead | **DITCH AHEAD** |
| 7 | 13.0 m | DITCH AHEAD | **DITCH AHEAD** |
| **8** | **11.4 m** | **clear to drive** | **DITCH AHEAD** |
| 9 | 9.9 m | DITCH AHEAD | **DITCH AHEAD** |
| 10 | 8.6 m | DITCH AHEAD | DITCH AHEAD |

**We warn at 18.4 m and never let go. The conventional system first flags the trench at
13.0 m, takes it back at 11.4 m — reporting the ground as *clear to drive* — and only
warns steadily from 9.9 m.** That is **8.5 m later**, 2.1 s at the 4 m/s this run drives,
and inside the braking distance it would need at any real speed.

The reversal is the part worth looking at, because the failure is not blindness. It is
*confidence*. The conventional map has returns off the trench rim, judges the rim flat,
and never observes the interior at all, so it has something to report and reports the
wrong thing. Absence of evidence is being read as evidence of flat ground.

It happens again at the next trench (16 m × 2.4 m, 1.8 m deep, at x = 10): the conventional
system says *unknown ahead* at 10.0 m and again at 6.0 m, and only warns at 2.0 m, while
ours has it flagged throughout.

> **Correction.** An earlier version of this section said the conventional system "only
> warns at 8.6 m — 9.8 metres later, 2.5 seconds later". That was read off the demo's
> rendered frames, which are every *second* frame, so frames 7 and 9 were never looked at
> and the flag at 13.0 m and the recovery at 9.9 m were both missed. Every frame of the
> approach is now in the table above. The honest gap to a steady warning is **8.5 m /
> 2.1 s, not 9.8 m / 2.5 s** — and the conventional system is *unstable*, not merely late,
> which is the more damning finding rather than a softer one. A second claim went with it:
> "at frames 20 and 22 it reverts to unknown ahead" was about the *next* trench, not this
> one, which holds DITCH AHEAD from frame 9 to the end of the run.

Reproduce: `python scripts/make_demo.py --fraction 0.02 --frames 40 --every 2`
Every-frame verdicts: `python scripts/demo_trace.py` → `results/demo_trace.csv`
Frame image: `results/demo_frames/frame_008.png`

---

## Honest limitations

1. **79% precision at threshold 3.0**, up from 73% since the crest guard. Only 5 cells now
   flag on ditch-free terrain, down from 436. What the proxy still counts as imprecision is
   mostly the flagged span overrunning the true ditch rectangle rather than a phantom hazard.
   The guard costs a ditch approached on an 11–14% uphill grade; above 15% the detector
   cannot see it either way.
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
python scripts/crest_study.py --frames 40                  # crest vs ditch separation
python scripts/benchmark.py --label "this machine"         # per-frame cost
python scripts/make_demo.py --fraction 0.05 --frames 40    # the offline demo
pytest -q && ruff check src tests scripts                  # 103 tests
```

| Output | What |
|---|---|
| `results/final_sweep.csv` | every metric, every allocator, every budget |
| `results/final_sweep_detections.csv` | first-detection event per ditch per run |
| `results/threshold_sweep.csv` | the threshold curve with its control |
| `results/crest_study.csv` | approach slope of every flagged gap, ditch vs control |
| `results/benchmark.csv` | per-frame cost by budget, with the host it was measured on |
| `*_noguard.csv` | the same runs with the crest guard disabled, for comparison |
| `results/demo.html` | the offline demo player |
| `deck/Raysense_SIH26053_Idea.pdf` | six-slide idea submission |
