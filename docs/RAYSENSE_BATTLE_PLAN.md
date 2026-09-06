# Team Raysense — SIH26053 Battle Plan

> ## ⚠ SUPERSEDED — do not present from this document
>
> This was the plan written before anything was built. Building it changed the central
> claim twice, both times toward something better supported. **The measured results are in
> [`RESULTS.md`](RESULTS.md); present from there.**
>
> What changed:
>
> | This document says | What was actually measured |
> |---|---|
> | The contribution is **adaptive allocation** — same safety at a third of the points | The contribution is a **detector**. Allocation loses to plain decimation on whole-map recall, and wins only on warning distance at tight budgets. |
> | The safety floor is `Δθ ≤ h/r` (positive obstacles) | Ditches bind **quadratically**: `Δθ ≤ w·h/r²`. A floor sized for bumps is met while ditches stay invisible. |
> | A ditch shows the literature's rear-wall signature | A ditch is usually **stepped over**, not fallen into. The absence test finds almost none of them; the gap test finds 91%. |
>
> The strategy, presentation rules, schedule, roles and risk register below all still hold.
> Only the technical claim is out of date.


**PS:** SIH26053 · **DRDO** · Software · Smart Automation ·  ₹1,00,000
**Title:** Adaptive Variable Resolution 2.5D Lidar Mapping for Dynamic Environment Perception

> **Deadline warning:** the PS listing shows **20 September 2026**; other sources say 30
> September. Your college's internal hackathon date is earlier still. **Verify both before
> reading any further** — everything in this plan is scheduled against the 20th.

---

## 1. The one-line pitch

> A lidar perception system that decides **where to spend its measurements**, so a
> defence UGV gets the same obstacle safety from roughly a third of the points — and,
> uniquely, it knows the difference between *"there's nothing there"* and *"I didn't look
> there."*

---

## 2. The insight the whole project rests on

This is what makes us different from every other team and every existing paper. Everything
else is execution.

**Negative obstacles — ditches, craters, washouts, shell holes — are detected by the
*absence* of laser returns.** You see a hole because the ground stopped returning where
the ground plane says it should.

**Adaptive sampling deliberately creates absences.** You skip regions on purpose.

So the moment you combine them, a fatal ambiguity appears:

| Observation | Explanation A | Explanation B | Explanation C |
|---|---|---|---|
| No return from this patch of ground | **A ditch** | Occlusion shadow behind an obstacle | **We never sampled it** |

Naive adaptive sampling collapses A and C into one bucket. On a road that is a nuisance.
On a UGV crossing broken terrain at speed, it is how you lose the vehicle.

**Nobody has addressed this**, because all published adaptive-lidar work targets urban
autonomous driving — KITTI, nuScenes, lanes, cars, pedestrians — where negative obstacles
are essentially absent. Meanwhile the negative-obstacle literature all assumes dense
uniform scanning. The two fields have never been put in the same room.

**Raysense puts them in the same room.** Our allocator carries an explicit three-valued
state — `OBSERVED` / `UNKNOWN` / `CANDIDATE_NEGATIVE` — never conflates unknown with
empty, and **actively spends measurement budget to resolve dangerous ambiguity.**

That is a defensible research contribution, a safety argument a defence audience
immediately understands, and — critically — it gives us the single most persuasive demo
available: *watch the naive method drive into a ditch, then watch ours refuse to.*

---

## 3. What we are building — precise architecture

We build a **point-budget allocator**. Given a budget of B measurements per frame
(B ≪ full scan N), decide how to distribute them across the sensor's field of view to
maximise terrain-map quality and obstacle safety.

### State carried between frames

- **`M`** — multi-resolution 2.5D elevation map (quadtree). Per cell:
  `{height μ, variance σ², confidence, last_observed_t, state}`
  where `state ∈ {SURFACE, OBSTACLE, SHADOW, UNKNOWN, CANDIDATE_NEGATIVE}`
- **`T`** — dynamic object tracks (position, velocity, covariance)
- **`x`** — ego pose from odometry/IMU (**consumed, not estimated** — see §6)

### Per-frame loop (single pass — no re-scan round trip)

**1. Predict.** Warp `M` from frame *t−1* into frame *t* using ego-motion. Propagate
tracks forward. Increment staleness on every cell.

**2. Build the need map `I(θ, φ)`** over angular bins. Weighted sum of:

| Term | Meaning |
|---|---|
| `w_edge` | local elevation gradient / roughness — discontinuities carry the information |
| `w_stale` | time since the cell was last observed |
| `w_track` | predicted footprint of moving objects, dilated by track uncertainty |
| `w_frontier` | never-observed cells entering the field of view |
| **`w_negative`** | **`CANDIDATE_NEGATIVE` cells awaiting disambiguation — the novel term** |
| `w_path` | proximity to planned path / braking corridor |

**3. Apply the safety floor — a hard constraint, allocated *before* anything else.**

This is provable geometry, not a heuristic. To guarantee a beam strikes an obstacle of
height *h* at range *r*, the angular sample spacing Δθ must satisfy:

```
Δθ  ≤  h / r          →        h_min(r) = r · Δθ
```

So inside the braking corridor (range `d_brake`, set by current speed), we enforce
`Δθ ≤ h_target / d_brake` and allocate that budget first. **It is never traded away.**

Worked example — 20 cm obstacle:

| Speed | Braking distance | Required Δθ | Feasible on a 64-beam sensor? |
|---|---|---|---|
| 5 m/s | ~8 m | 1.43° | Comfortably |
| 10 m/s | ~28 m | 0.41° | Tight |
| 15 m/s | ~60 m | 0.19° | **No** |

This falls straight out of honest geometry, and it hands us a feature no other team will
have: **the allocator can state the maximum safe speed for a given point budget and
sensor.** For a defence customer that is not a nice-to-have, that is the whole argument.

**4. Allocate the remaining budget** across angular bins in proportion to normalised need,
with a per-bin cap so it can't collapse onto one region.

**5. Acquire — three interchangeable backends** (this is our answer to "which sensor?"):

| Backend | What it does | What it saves |
|---|---|---|
| **Steerable** (MEMS/OPA) | emits an actual scan command | laser energy + bandwidth + compute |
| **Fixed-pattern** (spinning: Velodyne, Ouster) | masks which returns get processed | bandwidth + memory + compute (**not** laser power) |
| **Replay** (dataset) | selects a subset of a recorded full scan | — this is our evaluation harness |

**6. Update the map.** Fuse selected points into the quadtree, subdividing where variance
or gradient is high. Per-cell Bayesian height update.

**7. Negative-obstacle disambiguation — the core contribution.**
Track rays, not just points. A cell becomes `EMPTY` **only if a ray actually traversed it
and returned from beyond**. Everything else is `UNKNOWN`. Cells showing the geometric
signature of a negative obstacle — missing ground returns where the ground plane predicts
them, plus the characteristic range jump at the far edge (the "rear wall" signature from
the literature) — are flagged `CANDIDATE_NEGATIVE` and receive **priority budget next
frame** to confirm or clear.

**8. Output.** Per-cell slope, roughness and step height → **three-valued** traversability:
`traversable` / `blocked` / `unknown`. **Unknown is never treated as safe.**

### Stack

Python + NumPy/Numba for the allocator · Open3D for point-cloud work · a quadtree/grid in
NumPy or C++ via pybind11 if latency demands · PyTorch only if we add a learned need-map
(**stretch goal, not core**) · matplotlib/plotly for charts · a web or Open3D
side-by-side viewer for the demo.

**Keep it boring.** Judges score the result, not the framework.

---

## 4. How we prove it — the experiment

The experiment *is* the project. Design it first, build backwards from it.

### Data — two legs, deliberately

1. **RELLIS-3D** *(primary, credibility)* — a real all-terrain UGV in rugged off-road
   terrain, Ouster OS1, 13,556 point-wise annotated scans, 20 semantic classes. The
   closest public dataset to a DRDO ground-vehicle scenario that exists.
   **The full recorded scan is our ground truth**; our algorithm chooses which points it
   *would have acquired*. This is how we escape "you simulated it *and* wrote the answers."
2. **Simulation** *(secondary, control)* — for closed-loop moving-platform behaviour and,
   crucially, for **deliberately placed negative obstacles with exact ground truth**, which
   real datasets barely contain.
3. **SemanticKITTI** *(optional)* — structured/urban contrast, shows generalisation.

Say this two-leg rationale out loud. It converts "why simulation?" from an attack into
evidence that we thought about experimental design.

### Baselines — all at identical point budget

1. **Full scan (100%)** — the quality ceiling
2. **Uniform decimation** — every *k*-th beam. The honest naive baseline.
3. **Random subsampling**
4. **Static front-focused ROI** — the "reasonable engineer" baseline, and the one we must
   beat convincingly, because a judge will propose it
5. **Ours**

### Metrics

| Metric | Why |
|---|---|
| Elevation MAE / RMSE vs full-scan map (range-binned) | map fidelity |
| Traversability precision / recall / F1 | standard in the field |
| **Positive obstacle detection recall** | core safety |
| **Negative obstacle detection recall** | **our headline** |
| Time-to-detect (frames until a new obstacle is flagged) | latency that matters |
| Per-frame latency (ms) on named hardware | SWaP |
| Points processed per frame | the budget axis |
| **Minimum detectable obstacle size in braking corridor** | the provable safety number |

### The two charts that win

1. **Task metric vs point budget** — ours dominating all baselines, converging on
   full-scan performance somewhere around 25–35% of the points.
2. **The failure case.** Uniform decimation at 30% budget misses a ditch. Ours catches it.
   Same frame, same budget, side by side.

**Target headline:** *"Matched obstacle-detection recall at 3× fewer points and 2.4× lower
per-frame latency."* A ratio, a task metric, a named platform. Never "significantly fewer."

---

## 5. Verified against what actually wins SIH

| What winners did | Our version |
|---|---|
| Solar Masters — measured **20% efficiency gain** vs fixed panels | our budget-vs-recall curve with a hard ratio |
| Team NYX (2025 champion) — **section throughput** for Railways | points-per-frame and max safe speed |
| NALCO / Team Mad Astra — **accuracy + scalability on the sponsor's real process** | real off-road UGV data, not a toy |
| Every winner — **live working demo over slideware** | side-by-side replay demo, offline-capable |
| Winners — **read the sponsor's own domain** | negative obstacles, braking corridors, SWaP |
| Winners — **narrow scope, executed deeply** | one algorithm, characterised properly |

We match all six. That is not a coincidence — the plan was built against them.

---

## 6. What we explicitly do NOT build

State this on a slide. Volunteering your scope boundaries reads as confidence and
preempts the gotcha.

- **SLAM / localisation.** We *consume* ego-motion (RELLIS-3D ships GPS/IMU; sim gives it
  free). Estimating it is a solved, separate problem and out of scope.
- **Sensor fusion.** Lidar only. Adding cameras would confound the measurement we are making.
- **Path planning.** We define the braking corridor, we do not plan routes.
- **Fleet dashboards, cloud, user accounts.** Nobody asked.
- **Hardware.** This is a software PS.

Each of these is a deliberate decision with a reason. Say the reason.

---

## 7. The 6-slide idea submission

Max 6 slides, PDF, **use the official portal template if one is published.**

**1 — Title.** Team Raysense · PS **SIH26053** · full PS title · DRDO · Smart Automation ·
Software. Nothing else.

**2 — Problem.** Open in DRDO's language: SWaP-constrained perception on UGVs in
unstructured terrain. Then the gap in one sentence and one diagram: *adaptive sampling
creates absences; negative obstacles are detected by absences; nobody has reconciled that.*

**3 — Solution.** The single-pass predictive loop, as one clean diagram. Need map → safety
floor → allocation → acquisition → map update → disambiguation.

**4 — Technical approach.** Three sensor backends. The `Δθ ≤ h/r` safety-floor geometry
with the speed table. Stack. Datasets.

**5 — Feasibility & impact.** The budget-vs-recall curve. The headline ratio. The max-safe-
speed output. Deployment path onto DRDO's existing AUGV programme.

**6 — References & team.** Cite the prior art **properly and prominently** — NEC Labs MEMS
adaptive lidar, Adaptive LiDAR Scanning (2025), AEye's patents, RELLIS-3D, the
negative-obstacle literature. Then one line: what is ours.

Slide 6 is not a formality. It is where we win the novelty axis, by proving we read the
field instead of pretending it doesn't exist.

---

## 8. Winner mentality — how we present

Nine rules. These are worth more than any feature we could add.

**1. Open in their language, not ours.** The first thirty seconds should sound like a
capability briefing, not a college project. *"UGVs in unstructured terrain operate under a
hard SWaP budget…"* — never *"Hi, we're Raysense and we made a cool lidar thing."*

**2. Preempt the novelty question yourself.** Do not wait to be caught. *"Adaptive lidar
sampling is established — AEye ships it, NEC published it in 2020, there's a 2025 paper on
temporal cues. What does not exist is…"* This flips our single biggest risk into a
credibility asset. Judges relax visibly when a team demonstrably knows its own field.

**3. Lead with the failure, not the success.** Show naive adaptive sampling missing the
ditch **first**. Let them feel it. *Then* show ours. Almost no team structures a pitch this
way and it is the most persuasive order available.

**4. One number, repeated three times.** Slide 1, the demo, the closing line. Judges see
twenty teams; they will retain exactly one number per team. Choose it deliberately.

**5. Treat rounds 1–3 as free consulting — because they are.** The finale has four stages;
the first three are mentoring and critique, the fourth is the power round. Ask each juror
directly: *"What would you need to see to trust this in the field?"* Write it down where
they can see you writing it. Then **ship it and open the next round with "you asked for X —
here it is."** This is the highest-leverage behaviour available at the finale, and most
teams waste those rounds defending their original design instead.

**6. Never say "we invented."** Say *characterised*, *constrained*, *made deployable*,
*quantified*. Overclaiming is the fastest way to lose a technical jury.

**7. Bring offline fallbacks.** Recorded demo video, seeded local data, zero network
dependency, spare laptop, spare cable. "Teams lose rounds to laptops, not to logic."

**8. One presenter, but everyone answers for their own component.** Juries probe by asking
the quiet member a question. Every person must be able to defend their module unprompted.

**9. Volunteer your limitations before you're asked.** *"Here's what we don't handle, and
here's why that's the right scope."* Confidence, not weakness — and it kills the gotcha.

### The hard questions, and our answers

| Question | Answer |
|---|---|
| *Which sensor does this run on?* | Three backends. Steerable if you have it, masking if you don't, replay for evaluation. Sensor-agnostic by design. |
| *How is this different from AEye / the 2025 paper?* | Those are urban and unconstrained. Ours is off-road, negative-obstacle-aware, and carries a provable safety floor. |
| *Isn't this just simulation?* | No — primary results are on RELLIS-3D, real lidar from a real off-road UGV. Sim is only for controlled negative-obstacle ground truth. |
| *Does it save battery?* | On a spinning sensor, no laser energy — bandwidth, memory and compute. On a steerable sensor, laser energy too. Here is the measured number. |
| *What if it misses something?* | It can't, below the floor: `Δθ ≤ h/r` inside the braking corridor is enforced before any adaptive allocation. Here's the minimum detectable size. |
| *Real-time?* | X ms/frame on [named platform]. Here's the profile. |
| *Why not just scan the front densely?* | That's baseline 4. Here's the chart where we beat it — because threats aren't only in front, and staleness matters. |

---

## 9. The plan

### Phase 0 — Days 0–1 (5–6 Sept) · UNBLOCK
- [ ] **Confirm the real deadline** (20 vs 30 Sept) on sih.gov.in
- [ ] **Get the internal hackathon date from the SPOC** — this is the true deadline
- [ ] **Pull the full official PS text** and map **every clause** to a deliverable
- [ ] Confirm team of 6, same college, **at least one female member** — eligibility gate
- [ ] Start the RELLIS-3D download (it is large)
- [ ] Assign roles (§10)

### Phase 1 — Days 1–5 · FOUNDATION
- [ ] RELLIS-3D loader; render one scan
- [ ] Full-scan 2.5D elevation map + viewer — this is ground truth for everything
- [ ] Read the three papers (NEC MEMS adaptive lidar · Adaptive LiDAR Scanning 2025 · RELLIS-3D)
- [ ] Budget harness: subsample a recorded scan to B points, rebuild the map, score it

### Phase 2 — Days 4–9 · BASELINES AND FIRST CURVE
- [ ] Baselines 1–4 implemented
- [ ] Metrics: elevation RMSE, traversability P/R/F1, obstacle recall
- [ ] **First budget-vs-quality curve.** Even ugly, this is the project's spine.

### Phase 3 — Days 7–12 · THE ALLOCATOR
- [ ] Need map (all six terms)
- [ ] Safety floor with the `Δθ ≤ h/r` geometry + max-safe-speed output
- [ ] Single-pass predictive loop with ego-motion warping
- [ ] Ours on the curve, beating the baselines

### Phase 4 — Days 10–14 · THE CONTRIBUTION
- [ ] Ray-level `UNKNOWN` vs `EMPTY` accounting
- [ ] Negative-obstacle signature detection
- [ ] `CANDIDATE_NEGATIVE` priority budgeting
- [ ] **Find and capture the failure case** — naive misses a ditch, ours catches it
- [ ] Sim scene with planted negative obstacles and exact ground truth

### Phase 5 — Days 12–15 · SUBMIT
- [ ] Side-by-side demo, offline-capable
- [ ] Two headline charts finalised
- [ ] 6-slide PDF (§7)
- [ ] Internal hackathon presentation + **rehearse the nine rules**

### Phase 6 — Oct–Nov (if nominated) · HARDEN
Jetson-class benchmark for real SWaP numbers · closed-loop sim · SemanticKITTI
generalisation · learned need map (stretch) · demo polish · rehearse the power round as a
separate deliverable from the code.

### Phase 7 — December · FINALE
36 hours. Integrate nothing new. Ship the jury's feedback between rounds.

---

## 10. Roles

Six members, non-overlapping ownership. Everyone defends their own module to the jury.

| # | Role | Owns |
|---|---|---|
| 1 | **Lead / presenter** | narrative, PS clause mapping, jury interaction, the nine rules |
| 2 | **Mapping** | 2.5D quadtree, fusion, traversability output |
| 3 | **Allocator** | need map, budget optimisation, safety floor |
| 4 | **Evaluation** | RELLIS-3D pipeline, baselines, metrics, the two charts |
| 5 | **Simulation** | closed-loop, planted negative obstacles, ground truth |
| 6 | **Demo** | the side-by-side viewer — the thing judges actually look at |

The demo role is not junior work. It is the highest-visibility component in the room.

---

## 11. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Deadline is the 20th, not the 30th | **Critical** | Verify day 0. Plan assumes the 20th. |
| No registered SPOC at our college | **Critical** | Verify day 0. Nothing else matters if this fails. |
| RELLIS-3D too large / slow to process | High | Start day 0. Work on one sequence first. |
| Negative obstacles rare in real data | High | That is exactly why we plant them in sim. Two-leg design. |
| Allocator doesn't beat the front-focused baseline | High | If so, **report it honestly** and analyse why. An honest negative result beats a tuned lie, and juries can smell the difference. |
| Scope creep | Medium | §6 is a contract. Re-read it weekly. |
| Demo fails live | Medium | Offline data, recorded video, spare laptop. |
| Judged as "not novel" | Medium | Rule 2. Preempt it in our own opening. |

---

## 12. The three things that matter most

1. **Verify the deadline and the SPOC today.** Over 80% of SIH teams are eliminated on
   administration before anyone writes code. Do not be one of them.
2. **Get the budget-vs-recall curve working early, even ugly.** It is the spine of the
   entire project. Everything else is decoration hung on it.
3. **Find the failure case and show it first.** Naive adaptive sampling driving into a
   ditch is the most persuasive ten seconds we will ever have in front of a jury.

---

## Sources

- [SIH 2026 problem statements](https://sih2026.vuce.in/) · [official portal](https://www.sih.gov.in/)
- [Towards a MEMS-based Adaptive LIDAR — NEC Labs](https://arxiv.org/pdf/2003.09545)
- [Adaptive LiDAR Scanning: Harnessing Temporal Cues (2025)](https://arxiv.org/html/2508.01562v2)
- [AEye — LiDAR systems and methods for focusing on ranges of interest (US 11675053)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11675053)
- [RELLIS-3D Dataset (ICRA 2021)](https://dl.acm.org/doi/10.1109/ICRA48506.2021.9561251) · [overview](https://www.emergentmind.com/papers/2011.12954)
- [Negative Obstacle Detection in Off-Road Environments Using Sparse 3D LiDAR Point Cloud (IEEE)](https://ieeexplore.ieee.org/document/10907401/)
- [Lidar Based Off-road Negative Obstacle Detection and Analysis — DTIC](https://apps.dtic.mil/sti/tr/pdf/ADA561293.pdf)
- [LiDAR-Based Negative Obstacle Detection for UGVs in Orchards](https://pmc.ncbi.nlm.nih.gov/articles/PMC11679008/)
- [An Analytic Model for Negative Obstacle Detection with Lidar](https://pmc.ncbi.nlm.nih.gov/articles/PMC8125519/)
- [Traversability Analysis for Autonomous Driving: A LiDAR-based Terrain Modeling Approach](https://arxiv.org/pdf/2307.02060)
- [MEM: Multi-Modal Elevation Mapping for Robotics and Learning](https://arxiv.org/html/2309.16818)
- [DRDO — Technologies for Autonomous Unmanned Ground Vehicle](https://drdo.gov.in/drdo/technologies-autonomous-unmanned-ground-vehicle-and-testing-automotive-platform)
- [MEMS Mirrors for LiDAR: A Review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7281653/)
