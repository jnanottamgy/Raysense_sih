# Raysense — Adaptive Variable Resolution 2.5D Lidar Mapping

**Smart India Hackathon 2026 · Problem Statement `SIH26053` · DRDO · Software**
*Adaptive Variable Resolution 2.5D Lidar Mapping for Dynamic Environment Perception*

---

## The finding

A lidar on a ground vehicle sees **what sticks up** far better than **what you can fall
into.** Measured over 40 full scans — every ray, no budget limit:

| | Detected |
|---|---:|
| Positive obstacles (boulders) | **92.9 %** |
| Negative obstacles (trenches, craters) | **11.5 %** |

Spending more rays cannot fix it, because a full scan already spends everything. A narrow
trench is not *entered* by beams — it is **stepped over.**

The reason is geometric. A bump of height *h* is detectable when `h ≥ r·Δθ` — **linear** in
range. A ditch of width *w* needs `w ≥ r²·Δθ / h_sensor` — **quadratic.** On a stock Ouster
OS1-64 (Δθ = 0.714°, 1.8 m mast) that means **a 6.2 m wide ditch is invisible at 30 m**, and
a vehicle that must never enter a 1 m ditch **cannot safely exceed ≈ 23 km/h** — a limit the
sensor gives no indication of.

## What we contribute

The same quadratic, normalised, becomes the detector:

```
anomaly = measured gap ÷ predicted gap at that range
```

Negative obstacles found, at threshold 3.0, using **plain uniform decimation** — no
allocator involved:

| Point budget | Prior method | **Discontinuity test** |
|---:|---:|---:|
| 2 % | 6.7 % | **74.9 %** |
| 5 % | 9.7 % | **91.4 %** |
| 8.6 % | 11.3 % | **96.0 %** |
| 100 % | 15.2 % | **99.8 %** |

> **91 % of negative obstacles at 5 % of the point budget.** A full scan with no absence
> reasoning finds 12 %. Twenty times fewer points, nearly eight times the detection.
> It costs **1.5 ms per frame** at that 5 % budget — 67× inside a 100 ms frame at 10 Hz
> — against **252 ms** for the method it replaces, which cannot run in real time at all.
> Measured on an Intel Xeon @ 2.10 GHz; see [`results/benchmark.csv`](results/benchmark.csv).

The map carries **three** states — `OBSERVED`, `UNKNOWN`, `CANDIDATE_NEGATIVE` — and
`UNKNOWN` is the zero value, so a fresh map starts out admitting it knows nothing. Nothing
in the system upgrades *"I did not look there"* into *"safe to drive"*, and a test pins that
across randomised maps.

## What does *not* work, stated up front

1. **Precision is 73.3 %, not 100 %.** Crest occlusions produce genuine range gaps.
2. **Smart allocation does not beat plain decimation on whole-map recall** — 81.4 % against
   91.4 % at a 5 % budget. It wins only on *warning distance*, and only below ~8 %: at a 2 %
   budget it gives **23.2 m of warning against 12.3 m**, 1.88×. We quote it only there.
3. **Nothing has touched real sensor data.** Zero frames. RELLIS-3D corroboration is the
   next task; `n_azimuth`, the `.label` packing and the pose frame are all unverified.
4. **No embedded benchmark.** 1.5 ms is an x86 figure. Cost is linear in rays
   (0.44 µs/ray, R² = 0.9998), so the arithmetic bounds well — but we have not run a
   Jetson and quote no Jetson number. `scripts/benchmark.py --label "..."` produces a
   comparable row on any device.

Every number above comes from a committed CSV in [`results/`](results/). None is typed by
hand. See **[`docs/RESULTS.md`](docs/RESULTS.md)** for the full record.

## Run it

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                                          # 103 tests
python scripts/render_scan.py                      # one scan, three panels
python scripts/make_demo.py --fraction 0.02 --frames 40 --every 2
```

Then open [`results/demo.html`](results/demo.html) — conventional vs. Raysense, side by
side, both at a 2 % budget.

**Reproducibility.** `bash scripts/verify_reproducible.sh` builds a clean virtualenv from
`pyproject.toml` alone, rebuilds the ground truth and the sweep from nothing, and diffs
against the committed CSVs. Last run: *13 rows compared, largest difference in any metric
`0.00e+00` — bit-identical.*

## Layout

| Path | What |
|---|---|
| [`src/raysense/`](src/raysense/) | The system — sensor model, terrain sim, 2.5D map, ray accounting, detector, allocators, evaluation |
| [`tests/`](tests/) | 103 tests. They pin the physics, not just the plumbing |
| [`scripts/`](scripts/) | Ground truth, sweeps, threshold sweep, demo, reproducibility check |
| [`results/`](results/) | Every committed CSV and figure — the evidence base |
| [`docs/RESULTS.md`](docs/RESULTS.md) | **Measured results. Start here.** |
| [`docs/`](docs/) | Build plan, per-milestone findings, testing guide, runbook |
| [`presentation/`](presentation/) | Deck, speaker scripts, judge Q&A, runnable prototype ZIP |

Planning documents in `docs/` that predate the measurements are marked **SUPERSEDED** —
the original efficiency-through-allocation claim did not survive testing, and we changed
the claim rather than the number.

## Team

**Team Raysense** — Pranavi · Jeevika · Nikita · Anuj
<!-- add remaining members and the portal Team ID before submitting -->

## Acknowledgements

Built with [Claude Code](https://claude.ai/code). Prior art we build on is cited in full on
the deck and in [`docs/SIH26053_CRITIQUE.md`](docs/SIH26053_CRITIQUE.md) — RELLIS-3D
(ICRA 2021), NEC Labs MEMS foveating lidar, Adaptive LiDAR Scanning with temporal cues
(2025), AEye iDAR (US 11675053 / 11782136 / 11860313), Larson & Trivedi (DTIC ADA561293),
IEEE ROBIO 2024.
