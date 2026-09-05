# M1 + M2 — findings

**M1** (2.5D map, ground truth, map renderer) and **M2** (allocator protocol, replay
backend, metrics, sweep runner) are complete. **The first curve exists.** 61 tests
pass, lint clean.

Three results, one of which changes what we are claiming.

---

## 1. Uniform scanning does not have a *budget* problem with ditches. It has a *blindness* problem.

Coverage inside each planted feature, measured from **40 full scans** — every ray, forty
times, no budget limit at all:

| Feature | Kind | Cells | Observed |
|---|---|---:|---:|
| Trench, x = 10 m | negative | 240 | **59.6%** |
| Trench, x = −15 m | negative | 217 | **40.6%** |
| Crater, x = 25 m | negative | 401 | 89.8% |
| Wide deep trench, x = 52 m | negative | 4,000 | **1.5%** |
| Boulder, x = 0 m | positive | 44 | 90.9% |
| Boulder, x = 31 m | positive | 26 | 96.2% |
| *Driven area, for reference* | — | 45,000 | *83.6%* |

**Positive obstacles: 91–96% observed. Negative obstacles: 1.5–60%.** Same scans, same
rays, same forty frames.

Spending *more* rays uniformly cannot fix this, because the full scan already spends
everything. The geometry simply never illuminates the inside of a ditch.

### What this changes about the claim

The pitch so far has been *"same detection at a third of the points."* For **positive**
obstacles that is the right frame. For **negative** obstacles it is the wrong one
entirely — there is no budget at which uniform scanning sees them.

The honest and much stronger claim is:

> Uniform scanning cannot see negative obstacles at any budget. The contribution is not
> spending fewer rays — it is **noticing that something has not been seen, and spending
> budget to go and look.**

That is precisely the `CANDIDATE_NEGATIVE` priority-budgeting mechanism scheduled for
M4–M5. It was reasoned from first principles in the build plan; it is now measured.

It also sets up the demo cleanly: the full-scan ground-truth map already renders the
trenches as white holes. **The baseline's failure is visible before we show our fix.**

---

## 2. Uniform decimation cannot spend an arbitrary budget — and plotting the requested one is wrong

Decimation strides are integers, so the achievable budgets are `1/(k_beam · k_col)`.
Everything in between is unreachable:

| Asked for | Actually spent |
|---:|---:|
| 10% | 8.6% |
| 20% | 16.7% |
| 35% | **25.0%** |
| 50% | 50.0% |
| 75% | **50.0%** |

Asked for 75%, it delivered 50% — and posted the *identical* result to the 50% run,
because it was the same run.

**Any chart plotting quality against the requested budget is wrong.** Ours plots against
rays actually spent, and the sweep records both. This is worth saying out loud at the
finale: it is the kind of detail that separates a measured result from a plausible one,
and a judge who has run this experiment themselves will look for it.

It is also a small point in our favour — a need-weighted allocator spends exactly the
budget it is given.

---

## 3. Elevation error is nearly degenerate as a metric. Coverage is what carries information.

| Spent | Uniform RMSE | Coverage |
|---:|---:|---:|
| 2% | 0.065 m | 15.0% |
| 10% | 0.023 m | 33.2% |
| 50% | 0.004 m | 78.4% |
| 100% | 0.000 m | 100% |

A 2% budget posts a 6.5 cm elevation error, which sounds excellent — but only because
the metric averages over the cells the budget *did* observe, which are the near ones,
densely sampled and easy. It knows almost nothing and scores well for it.

This is exactly the pathology `eval/metrics.py` was written to warn about, now confirmed
on real numbers. There is a regression test for it (`test_a_subset_map_scores_low_coverage_but_low_error`).

**Consequence:** never show the error panel without the coverage panel beside it. And the
metric that will actually decide this project is neither of them — it is
**negative-obstacle recall**, which arrives at M4–M6.

### The expected null result

Uniform and random are statistically indistinguishable on coverage (15.0% vs 15.2% at 2%;
the lines cross repeatedly). That is correct and it is the setup for everything that
follows: **if where you look does not matter when you are not thinking, then all of the
value is in the thinking.**

---

## What was built

| Module | State |
|---|---|
| `mapping/` | `FixedGridMap` — mergeable per-cell `n`/`sum`/`sumsq`, so points scatter in any order across any frame. Height, variance, staleness, coverage, `.npz` caching. `ElevationMap` protocol so `QuadtreeMap` slots in later. |
| `sim/scenes.py` | `offroad_course` — one seeded world shared by every milestone, so numbers stay comparable. Six planted features spanning the ranges where the quadratic falloff bites. |
| `sim.drive` | Sensor carried along a path; one raycast per frame. |
| `allocate/` | `Allocator` protocol + `WorldState`; `FullScan`, `UniformDecimation`, `RandomSubsample`. Baselines are objects satisfying the same protocol, never special cases. |
| `sensor/backends.py` | `ReplayBackend` — subsamples a recorded scan while preserving fired-but-empty rays. |
| `eval/` | Elevation MAE/RMSE/p95, coverage recall; the sweep runner. |
| `viz/` | Map renderer (unknown drawn as hatching, not a hue) and the budget curve. |

**The sweep raycasts each frame once** and replays that single scan through every
allocator at every budget. Cost is independent of how many strategies are compared, and
every strategy sees numerically identical ground truth — so any difference in the results
is the allocation and nothing else.

```bash
python scripts/build_ground_truth.py --frames 40      # M1, ~37 s, cached
python scripts/run_sweep.py --frames 40               # M2, ~40 s, 15 runs
pytest -q && ruff check src tests scripts
```

Outputs: `results/m1_ground_truth.png`, `results/m2_budget_curve.png`,
`results/m2_convergence.png`, `results/m2_sweep.csv`.

---

## Still unverified

Unchanged from M0, and still gating anything quotable: **`n_azimuth` for RELLIS-3D** (it
is the denominator of every budget fraction on this page), `.label` packing, the pose
frame, and **the official problem-statement text**.

Everything above is measured on the synthetic course. It is exact where a real dataset is
approximate — the ground truth is known rather than inferred — but it is not yet
corroborated on real sensor data.

## Next — M3

Traversability and obstacle-recall metrics, plus `StaticFrontROI`: the baseline a judge
will propose, and the one we actually have to beat.
