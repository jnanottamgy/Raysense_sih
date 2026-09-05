# SIH26053 — Adaptive Variable Resolution 2.5D Lidar Mapping (DRDO)

**Team Raysense — brutal review of the proposed approach.**
Compiled 5 September 2026.

| Field | Value |
|---|---|
| PS ID | **SIH26053** |
| Organisation | **DRDO** |
| Title | Adaptive Variable Resolution 2.5D Lidar Mapping for Dynamic Environment Perception |
| Category | Software |
| Theme | Smart Automation *(one tracker lists Transportation & Logistics — verify on portal)* |
| Prize | ₹1,00,000 |
| Listed deadline | **20 September 2026** *(other sources say 30 Sept — verify on portal, this is a 10-day swing)* |

---

## Verdict

**The problem statement choice: excellent.**
**The plan as written: not yet a winner.** It has five holes a DRDO jury finds inside ten
minutes. All five are fixable in the time available. None require abandoning the idea.

---

## What is genuinely right (do not change these)

1. **PS selection is smart.** A narrow, technical, unglamorous sampling-theory problem.
   Most teams pile into generic "AI platform" statements; few will pick this, and most who
   do will do it badly. Low competition per statement is a real, undervalued edge.
2. **Metric-first framing is exactly what wins.** "Prove it with real numbers, live
   side-by-side" is the shape of every SIH winner: Solar Masters won on a measured 20%
   efficiency gain, Team NYX on train section throughput, NALCO on demonstrated accuracy
   and scalability. The instinct here is correct.
3. **Scope discipline is correct and rare.** Explicitly refusing SLAM, sensor fusion and
   fleet dashboards directly counters the #3 documented cause of loss (feature bloat).
   Keep this. Defend it out loud to the jury as a deliberate engineering decision.

Three hardest strategic calls, all made correctly. The problems are all in the technical
framing, not the strategy.

---

## Hole 1 — The hardware question. This is the one that kills you.

"Scan sparsely, then re-scan densely" **assumes a steerable sensor**. Most lidar cannot
do this:

| Sensor class | Can it foveate? |
|---|---|
| Spinning mechanical (Velodyne, **Ouster OS1**) | **No.** Scan pattern is mechanically fixed. You cannot tell it to densify a region. |
| Livox (Risley prism) | **No.** Non-repetitive pattern, but not steerable to a chosen ROI. |
| MEMS mirror (AEye 4Sight), OPA, galvo | **Yes.** This is the hardware class your idea requires. |

Foveated scanning is a commercial product with a patent family — AEye's "LiDAR systems
and methods for focusing on ranges of interest" (US 11675053, 11782136, 11860313).

**The first question from a DRDO electro-optics engineer (IRDE Dehradun does exactly this
work) will be: "What sensor does this run on?"** If the answer is a shrug, you are
simulating a sensor they may not own, and the power round is over.

**Fix — support both paths and say so explicitly:**
- **Steerable path:** name the hardware class (MEMS-mirror), cite AEye and the NEC Labs
  MEMS adaptive lidar work. Here you save laser energy *and* compute.
- **Fixed-pattern path:** on a spinning sensor you don't steer the beam, you allocate
  *processing and storage*. You save compute, bandwidth and memory — **not** laser power.
- **Best answer:** frame your contribution as a **sensor-agnostic point-budget allocator**
  that maps to beam steering when hardware allows and to decimation when it doesn't.
  That is a stronger, more defensible, more procurement-friendly claim than either alone.

---

## Hole 2 — The novelty claim. This ground is well trodden.

The idea as described is not new, and DRDO jurors on a lidar PS will know it:

- **"Towards a MEMS-based Adaptive LIDAR"** — Pittaluga et al., NEC Labs (arXiv 2003.09545).
  Foveated MEMS lidar. Directly this.
- **"Adaptive LiDAR Scanning: Harnessing Temporal Cues for Efficient 3D Object Detection
  via Multi-Modal Fusion"** (arXiv 2508.01562, 2025). Uses past frames to predict ROIs,
  scans ROIs densely and elsewhere sparsely. **This is very nearly your exact pipeline,
  published a year ago.**
- **AEye iDAR / 4Sight** — shipping commercial foveated lidar.
- "Fast Adaptive Scene Sampling for Single-Photon 3D Lidar Images"; "Fast Task-Based
  Adaptive Sampling for 3D Single-Photon Multispectral Lidar"; "Integrated adaptive
  coherent LiDAR for 4D bionic vision"; "3D Environment Mapping with a Variable
  Resolution NDT Method".

Novelty is **10 marks at idea stage** and one of the **five finale axes**. Claiming
invention and being caught costs you credibility on every other axis too.

**Fix — do not abandon, reposition.** DRDO wrote this PS *knowing* the technique exists;
they want it built and characterised for **their** operating conditions. Say so. Open with
the literature, then state precisely what is unsolved for a defence UGV. That single move
converts your weakest axis into your strongest: it is the "read the sponsor's own domain"
differentiator that almost no SIH team does.

### Where to actually put your novelty (pick one or two — not all four)

1. **Off-road / unstructured terrain, not urban.** Almost all adaptive-lidar work targets
   autonomous driving — roads, lanes, cars, pedestrians, KITTI/nuScenes. DRDO needs rugged
   terrain with no lane structure, vegetation-vs-solid-obstacle discrimination, and
   **negative obstacles** (ditches, holes, craters). Negative-obstacle detection under a
   reduced point budget is genuinely hard and genuinely military. **Strongest angle.**
2. **A provable safety floor.** Not "we match detection on average" but "we *never* drop
   below X angular density inside the braking corridor." A safety-constrained allocator.
   DRDO buys risk reduction, not average-case efficiency.
3. **Sensor-agnostic allocation** that degrades gracefully from steerable to fixed-pattern.
4. **Real SWaP characterisation** — a measured energy and compute model on Jetson-class
   edge hardware, not a hand-wave.

---

## Hole 3 — "We'll simulate it" is the weakest possible evidence

Documented SIH failure mode: judges prefer a rough working thing over a polished
theoretical thing. Simulation-only on a DRDO PS invites the obvious kill shot: *"it works
in the simulator where you also wrote the ground truth."*

**The single highest-value change you can make:**

> Run the adaptive sampler as a **subsampler over real recorded lidar data.**

Take **RELLIS-3D** — an Ouster OS1 on a Warthog all-terrain UGV in rugged off-road
terrain, 13,556 point-wise annotated LiDAR scans, 20 semantic classes. This is the closest
public dataset to a DRDO ground-vehicle scenario that exists. Optionally add SemanticKITTI
for a structured-environment contrast.

The mechanism: the **full recorded scan is ground truth**. Your algorithm decides which
points it *would have acquired*. Then measure task performance against point budget.

This converts "we simulated it" into **"we validated on real sensor data from a real
off-road UGV"** — at zero hardware cost, inside the time available. Keep the simulator as
well, for the closed-loop moving-platform story, but the dataset result is the evidence
that survives cross-examination.

---

## Hole 4 — The two-pass latency problem

"Sparse scan → detect → dense re-scan" is a **two-pass loop**. On a platform moving at
5 m/s with a 10 Hz frame, you travel ~0.5 m between passes — the dense re-scan targets
stale coordinates. Worse, the perception you are trying to speed up now costs a round trip.

Expect: *"What is your latency budget, and is the loop stable?"*

**Fix:** go single-pass and predictive. Use the **previous** frame (plus ego-motion and
object tracks) to allocate the budget for the **current** frame. That is what the
temporal-cues literature does, it removes the round trip, and it makes your
moving-object-tracking component load-bearing instead of decorative.

---

## Hole 5 — The battery claim is probably wrong as stated

"Wastes compute, processing time, and battery" — on a spinning lidar the motor and laser
draw are essentially constant. **Ignoring returns saves no sensor power.** Real savings:

- **Laser pulse energy** — only on steerable/addressable systems
- **Data bandwidth and memory**
- **Downstream compute** (and therefore SoC power)

Say which, with a number. Use **SWaP (Size, Weight and Power)** — that is DRDO's own
vocabulary and signals you have read their material.

---

## Hole 6 — "2.5D resolution map" is ambiguous

The PS says *2.5D Lidar Mapping* — that means an **elevation / height map**: a 2D grid
with height per cell, the standard representation for ground-vehicle traversability. Your
phrase "output a 2.5D resolution map" reads as though it might mean a map *of resolutions*.

Nail the definition, and note that a **variable-resolution 2.5D map needs a real data
structure** — a quadtree or multi-resolution grid. That is legitimate engineering worth
marks, and it positions cleanly against the "Variable Resolution NDT" prior art.

---

## The demo that wins the power round

Side-by-side on **real RELLIS-3D off-road data**:

- **Left:** fixed uniform scanning, full budget
- **Right:** your adaptive allocator at ~30% of the budget
- **Live counters:** points used · ms/frame · obstacle detection recall · **missed obstacles**
- **One honest failure case you found and fixed** — e.g. a shallow negative obstacle that
  naive adaptive sampling misses, caught by your safety floor.

Showing a failure you discovered and handled is worth more than a clean result. It is the
clearest possible proof you did the work rather than tuned a demo.

**Target headline number:** something of the shape *"matched obstacle-detection recall at
3× fewer points and 2.4× lower per-frame latency on Jetson Orin Nano."* A ratio, a task
metric, and a named platform. Not "significantly fewer."

---

## Immediate actions

1. **Verify the deadline** — the PS listing says 20 September, other sources say 30. Also
   get your college's internal hackathon date from the SPOC. This sets everything.
2. **Pull the full official PS text** from sih.gov.in and map **every clause** to a
   deliverable. Misreading the statement is the #2 documented cause of loss; every clause
   is a scored requirement.
3. **Read the three key papers** (NEC Labs MEMS adaptive lidar; Adaptive LiDAR Scanning
   with temporal cues; RELLIS-3D) so you are never blindsided on prior art.
4. **Decide the hardware story** — steerable, fixed-pattern, or sensor-agnostic.
5. **Get RELLIS-3D downloading.** It is large; start now.

---

## Sources

- [SIH 2026 problem statement browser](https://sih2026.vuce.in/) · [official portal](https://www.sih.gov.in/)
- [Towards a MEMS-based Adaptive LIDAR — Pittaluga et al., NEC Labs](https://arxiv.org/pdf/2003.09545)
- [Adaptive LiDAR Scanning: Harnessing Temporal Cues for Efficient 3D Object Detection via Multi-Modal Fusion](https://arxiv.org/html/2508.01562v2)
- [Fast Adaptive Scene Sampling for Single-Photon 3D Lidar Images](https://www.researchgate.net/publication/339756153_Fast_Adaptive_Scene_Sampling_for_Single-Photon_3D_Lidar_Images)
- [Fast Task-Based Adaptive Sampling for 3D Single-Photon Multispectral Lidar Data](https://arxiv.org/pdf/2109.01743)
- [Integrated adaptive coherent LiDAR for 4D bionic vision](https://arxiv.org/html/2410.08554v1)
- [AEye — LiDAR systems and methods for focusing on ranges of interest (US 11675053)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11675053)
- [AEye 4Sight long-range lidar — Design News](https://www.designnews.com/automotive-engineering/aeye-4sight-long-range-lidar-gives-continental-more-complete-vision)
- [MEMS Mirrors for LiDAR: A Review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7281653/)
- [Livox scanning pattern documentation](https://github.com/Livox-SDK/livox_wiki_en/blob/master/source/introduction/livox_scanning_pattern.rst)
- [RELLIS-3D Dataset: Data, Benchmarks and Analysis (ICRA 2021)](https://dl.acm.org/doi/10.1109/ICRA48506.2021.9561251) · [overview](https://www.emergentmind.com/papers/2011.12954)
- [3D Environment Mapping with a Variable Resolution NDT Method](https://www.researchgate.net/publication/366198780_3D_Environment_Mapping_with_a_Variable_Resolution_NDT_Method)
- [Graph SLAM-Based 2.5D LIDAR Mapping Module for Autonomous Vehicles](https://www.mdpi.com/2072-4292/13/24/5066)
- [DRDO — Technologies for Autonomous Unmanned Ground Vehicle](https://drdo.gov.in/drdo/technologies-autonomous-unmanned-ground-vehicle-and-testing-automotive-platform)
