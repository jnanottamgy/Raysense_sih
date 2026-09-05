# Raysense — Build Plan

**SIH26053 · DRDO · Adaptive Variable Resolution 2.5D Lidar Mapping**
Engineering plan. No code yet — this is the contract we build against.

---

## 0. Two decisions that govern everything

### 0.1 Non-returns are first-class data

Every point-cloud library in existence throws away rays that came back empty. **We cannot.**
Our entire contribution is the difference between *"a ray went there and nothing came back"*
and *"no ray ever went there."* If that distinction is not carried in the core data type, it
will be lost somewhere in the pipeline and the project dies quietly.

So `ScanResult` carries the fired rays, not just the returns. The type system enforces the
insight.

### 0.2 The demo is a map view, not a point cloud

**You cannot show an absence in a point-cloud viewer.** A missing point is invisible — that
is literally the problem we are solving. A 3D point cloud of our output and a 3D point cloud
of the naive baseline look identical to a jury.

The demo is therefore a **top-down 2.5D map render**: elevation as colour, obstacles marked,
and `UNKNOWN` in its own distinct colour. Absence becomes *visible*. This is also what the
problem statement actually asks us to output, it reads clearly on a projector at three
metres, and it is far cheaper to build than a 3D viewer.

Consequence: **Open3D is a development inspection tool, not the demo.** Do not build the
demo on it.

---

## 1. Principles

1. **The curve exists by day 5, even ugly.** Two allocators, one metric, three budget levels
   is a valid day-5 result. Everything after that is replacing components behind stable
   interfaces.
2. **One protocol, five allocators.** Baselines and our method are interchangeable objects.
   If a baseline needs special-casing anywhere in the pipeline, the abstraction is wrong.
3. **Precompute the demo.** Frames are rendered offline and played back. Live computation on
   stage is how teams lose rounds to laptops.
4. **Every number in the deck comes from a committed CSV.** No hand-typed results, ever.
5. **Deterministic.** Seeded RNG, pinned versions, cached ground truth. A result we cannot
   reproduce on demand is a result we cannot defend under questioning.

---

## 2. Repository layout

```
raysense/
├── pyproject.toml
├── configs/
│   ├── sensor/       ouster_os1_64.yaml · mems_steerable.yaml
│   ├── vehicle/      warthog.yaml            # geometry, speed, braking model
│   ├── allocator/    raysense.yaml · uniform.yaml · random.yaml · front_roi.yaml
│   └── experiment/   budget_sweep.yaml · failure_hunt.yaml
├── src/raysense/
│   ├── types.py      # ScanResult, RayGrid, RayBudget, CellState  ← the contract
│   ├── io/           # RELLIS-3D loader, pose loader, caching
│   ├── sensor/       # SensorModel + three backends
│   ├── mapping/      # ElevationMap interface + implementations
│   ├── raycast/      # ray accounting — the core kernel
│   ├── perceive/     # positive + negative obstacle extraction, traversability
│   ├── allocate/     # need map, safety floor, allocators
│   ├── track/        # dynamic object tracks            (M5+)
│   ├── sim/          # synthetic terrain + analytic raycaster
│   ├── eval/         # metrics, sweep runner, aggregation
│   ├── viz/          # map renderer, side-by-side composer, charts
│   └── pipeline.py   # the frame loop
├── scripts/          # download_rellis.sh, run_sweep.py, make_demo.py
├── tests/
└── results/          # CSVs + figures, committed
```

---

## 3. Core data model

Defined once in `types.py`, changed almost never. Everything else depends on these.

```
RayGrid          fired ray directions (az, el) + origin pose + max_range
                 — the set of rays the sensor ACTUALLY emitted this frame

ScanResult       points        (N,3)  returns in sensor frame
                 ray_index     (N,)   which fired ray produced each point
                 fired         RayGrid
                 → rays in `fired` with no point  = FIRED, NO RETURN
                 → directions absent from `fired` = NEVER LOOKED
                 These two must never merge.

RayBudget        per-angular-bin sample counts, or a boolean mask over the
                 sensor's native beam grid. Output of an Allocator.

CellState        bitfield: SURFACE | OBSTACLE | FREE | SHADOW
                           | UNKNOWN | CANDIDATE_NEGATIVE | CONFIRMED_NEGATIVE

WorldState       map + tracks + ego pose + frame index.
                 The only thing an Allocator is allowed to see.
```

---

## 4. Modules

### 4.1 `io/` — data access

RELLIS-3D loader: point clouds, per-point semantic labels, GPS/IMU poses, calibration.
Sequence-level iteration with a frame index.

**Ego-motion is consumed, never estimated.** We read poses from the dataset. This is the
scope boundary from the plan, enforced in code.

Cache aggressively — decoded scans and computed ground-truth maps go to disk keyed by
sequence + config hash. Recomputing ground truth on every sweep run will eat the schedule.

### 4.2 `sensor/` — the "which lidar?" answer

`SensorModel` holds the beam geometry: vertical/horizontal FOV, beam counts, angular
resolution Δθ, max range. Loaded from YAML. `ouster_os1_64.yaml` matches RELLIS-3D exactly.

Three backends behind one `acquire(budget) -> ScanResult`:

| Backend | Behaviour |
|---|---|
| `ReplayBackend` | Selects a subset of a recorded full scan. **Primary — the evaluation harness.** Full scan is retained separately as ground truth. |
| `MaskBackend` | Models a fixed-pattern spinning sensor: all rays physically fire, we choose which to *process*. Saves bandwidth/compute, not laser energy — and the accounting reflects that honestly. |
| `SteerableBackend` | Models a MEMS/OPA sensor: only budgeted rays are emitted. Saves laser energy too. Used in sim. |

The three backends are what we point at when a DRDO engineer asks what hardware this assumes.

### 4.3 `mapping/` — the 2.5D map

`ElevationMap` interface: `update(scan, pose)`, `query(cell)`, `cells_in_fov(pose)`,
`render_state()`.

Two implementations behind it:

- **`FixedGridMap`** — flat 2D array, per-cell `{height_mean, height_var, n_obs, last_seen,
  state}` as parallel NumPy arrays. Built first. Fast, simple, sufficient for all the science.
- **`QuadtreeMap`** — subdivides where elevation variance or gradient is high. Built second.
  This is the *variable resolution* the PS title names, so it must exist — but it must not
  block the first curve.

Building `FixedGridMap` first is deliberate risk management: it de-risks the pipeline before
we take on the harder data structure.

Height fusion is a running mean + variance per cell (Welford), not a naive overwrite.

### 4.4 `raycast/` — the core kernel

This is the module the whole contribution lives in. Numba-JIT'd, because it runs per-ray
per-frame and the real-time claim depends on it.

For each **fired** ray:

- **Return within range** → mark hit cell `SURFACE` or `OBSTACLE`; mark every cell traversed
  before the hit as `FREE`.
- **No return** → cast against the predicted ground plane. If the ray *should* have struck
  ground at `r_expected` and did not, the surface is lower than predicted → mark
  `CANDIDATE_NEGATIVE`.
- **Behind a hit** → `SHADOW`, which is explicitly *not* `UNKNOWN` and explicitly not `FREE`.

Cells no fired ray ever crossed remain `UNKNOWN`. That is the default, and it is never
silently upgraded.

**Invariant, asserted in tests:** a cell only leaves `UNKNOWN` when a ray demonstrably
traversed it.

### 4.5 `perceive/` — obstacles and traversability

- **Positive obstacles** — height step above threshold relative to local ground estimate.
- **Negative obstacles** — `CANDIDATE_NEGATIVE` regions promoted to `CONFIRMED_NEGATIVE` on
  the rear-wall signature from the literature: returns just beyond the gap, at longer range
  and lower elevation. Accumulated across frames with a Bayesian update rather than decided
  on one frame.
- **Traversability** — from slope, roughness and step height. **Three-valued:**
  `traversable / blocked / unknown`. There is no code path that maps `unknown → traversable`.

### 4.6 `allocate/` — the allocator

One protocol:

```
Allocator.allocate(world: WorldState, budget: int) -> RayBudget
```

Five implementations. Baselines are not scripts, they are objects that satisfy the same
protocol, selected by config:

| Allocator | Behaviour |
|---|---|
| `FullScan` | Everything. The quality ceiling. |
| `UniformDecimation` | Every *k*-th beam. The honest naive baseline. |
| `RandomSubsample` | Seeded random subset. |
| `StaticFrontROI` | Fixed dense wedge ahead. **The one a judge will propose — we must beat it.** |
| `RaysenseAllocator` | Ours. |

`RaysenseAllocator` runs in two stages:

**Stage 1 — safety floor (hard, allocated first, never traded).**
From the vehicle config: braking distance `d_brake` from current speed, reaction time and
deceleration. From `Δθ ≤ h_target / r`, derive the minimum angular density required inside
the corridor. Reserve that budget before anything adaptive happens.

If the remaining budget cannot satisfy the floor, the allocator **reports the maximum safe
speed** instead of silently degrading. That inversion is a feature, and it is the thing that
will land with a defence audience.

**Stage 2 — need-weighted water-fill.**
Score every angular bin by projecting map cells into sensor angles and summing weighted
terms: edge/gradient, staleness, predicted track footprints, frontier, corridor proximity,
and `CANDIDATE_NEGATIVE` (the novel term). Distribute the remaining budget in proportion to
need, with a per-bin cap so it cannot collapse onto one region.

Weights live in YAML. They are a config artefact, not magic numbers in source — because a
juror *will* ask how they were chosen, and "here is the sweep" is the only good answer.

### 4.7 `sim/` — synthetic testbed

**We build a lightweight analytic raycaster, not CARLA/Gazebo/Isaac.**

Rationale, and this is the defensible version to say out loud: real datasets contain almost
no labelled negative obstacles, so we need a controlled environment where ditch geometry and
position are exactly known. A heightmap world with analytically cast rays gives exact ground
truth, arbitrary obstacle placement, closed-loop ego-motion, and installs in seconds. A full
game-engine simulator costs a week of setup and buys us nothing we need.

Contents: procedural terrain (noise + slopes), planted negative obstacles (trenches, craters,
washouts) with known extents, planted positive obstacles, a scripted or closed-loop vehicle
path.

### 4.8 `eval/` — the harness

The sweep runner is the most important script in the repo:

```
for sequence × allocator × budget_fraction:
    run pipeline → per-frame metrics → tidy rows
```

Emits one long-format CSV. Everything downstream — every chart, every number in the deck —
is a groupby on that file.

Metrics: elevation MAE/RMSE (range-binned) · traversability precision/recall/F1 · positive
obstacle recall · **negative obstacle recall** · time-to-detect (frames) · per-frame latency
(ms) · points processed · minimum detectable obstacle size in corridor.

Ground truth is the full-scan map plus RELLIS-3D semantic labels in real data, and exact
planted geometry in sim.

### 4.9 `viz/` — demo and charts

- `render_map(state) -> RGB` — the top-down 2.5D view. Elevation ramp for known surface,
  distinct hue for `UNKNOWN`, marked positive and negative obstacles, corridor overlay.
- `compose_side_by_side(a, b, counters)` — two renders plus a live counter strip: points
  used, ms/frame, obstacles detected, **obstacles missed**.
- Frames render to PNG, then to MP4. **The stage demo plays back precomputed frames.**
- `charts.py` — reads the sweep CSV, emits the budget-vs-metric curve and the failure-case
  figure. Charts are generated, never hand-drawn.

---

## 5. The frame loop

`pipeline.py`, one function, deliberately readable — a juror may be shown this file.

```
for frame in sequence:
    pose      = io.pose(frame)
    world     = world.predict(pose)          # warp map, propagate tracks, age cells
    budget    = allocator.allocate(world, B) # safety floor, then need-weighted fill
    scan      = backend.acquire(budget)      # returns AND fired-but-empty rays
    world.map = raycast.integrate(world.map, scan, pose)
    world     = perceive.update(world)       # obstacles, negative candidates, traversability
    metrics.record(frame, world, scan, timings)
```

Single pass. No sparse-then-rescan round trip: the current frame's budget is decided from the
*previous* frame's state plus ego-motion.

---

## 6. Configuration

YAML throughout, composed at run time, and **the resolved config is hashed into every result
row.** This is not bureaucracy — when a result looks wrong at 2am in December, the hash is
what tells us which knob moved.

---

## 7. Testing

| Level | What |
|---|---|
| **Unit** | Welford fusion · angular projection · `Δθ ≤ h/r` against closed-form `h_min = r·Δθ` |
| **Golden** | A hand-computed toy scene: one ditch, one rock, six rays. Exact expected cell states. |
| **Property** | Budget never exceeded · safety floor always satisfied · **`UNKNOWN` never becomes `traversable`** |
| **Regression** | Sweep on one short sequence, metrics within tolerance of committed baseline |

The property tests are worth building carefully. "Here is the test that proves unknown is
never reported as safe" is a strong thing to be able to say to a defence jury.

---

## 8. Build order

Ordered by risk, not by architecture. Each milestone has an exit criterion — if it is not
met, we stop and fix rather than proceeding.

| # | Days | Milestone | Exit criterion |
|---|---|---|---|
| **M0** | 1–2 | Skeleton · RELLIS-3D loader · render one scan | A real scan renders. Data access proven. |
| **M1** | 2–4 | `FixedGridMap` · full-scan map · map renderer | Ground-truth map for a full sequence, cached. |
| **M2** | 3–5 | `Allocator` protocol · `FullScan` + `UniformDecimation` · `ReplayBackend` · elevation RMSE · sweep runner | **First curve exists.** Ugly is fine. This is the spine. |
| **M3** | 5–7 | Traversability + obstacle recall metrics · `RandomSubsample` · `StaticFrontROI` | Four baselines on one chart. |
| **M4** | 6–9 | `raycast/` ray accounting · `UNKNOWN` vs `FREE` · `CANDIDATE_NEGATIVE` | Property test passes: unknown never traversable. |
| **M5** | 8–11 | `RaysenseAllocator` — safety floor + need map · predictive single-pass loop | Ours beats uniform and random on the curve. |
| **M6** | 9–12 | `sim/` raycaster · planted ditches · negative obstacle recall metric | Negative-obstacle recall measurable on known ground truth. |
| **M7** | 11–13 | **Failure hunt** — sweep for a frame where uniform@30% misses a ditch and ours catches it | The frame is found, captured, reproducible from a seed. |
| **M8** | 12–14 | Side-by-side demo video · final charts · 6-slide PDF | Demo runs with the network cable unplugged. |
| **M9** | 14–15 | Freeze · rehearse | No new code. |

**Deferred to Oct–Nov, only if nominated:** `QuadtreeMap` · `track/` dynamic tracking ·
Jetson-class latency benchmark · SemanticKITTI generalisation · learned need map ·
closed-loop sim.

### The decision point

**M5's exit criterion is the whole project.** If our allocator does not beat `StaticFrontROI`,
we do not paper over it. We analyse why, report it honestly, and pivot the claim toward
whatever *is* true — most likely the negative-obstacle safety result, which stands on its own
even if the efficiency margin is thin. An honest negative result presented well beats a tuned
lie, and a technical jury can tell the difference.

---

## 9. Environment

Deliberately small. Anything that takes more than two minutes to install is a liability.

```
numpy · numba · scipy · pyyaml · pandas · matplotlib · imageio-ffmpeg
dev: pytest · ruff
inspection only: open3d          # NOT a demo dependency
```

No PyTorch in core. No ROS. No game engine. Python 3.11, versions pinned.

---

## 10. Division of labour

Given that the build capacity is realistically the two of us:

**Needs your machine or a large VM:** RELLIS-3D download and decode (large, slow, on the
critical path — start day 0), any Jetson benchmark, recording the final demo.

**I can write end to end:** every module above, the sweep harness, the tests, the charts, the
renderer, the deck.

**Needs you specifically:** the official PS text mapped clause by clause, the SPOC and
deadline facts, the six-person team registration, and every decision where the honest answer
is a judgement call about what to cut.

---

## 11. First three actions

1. Confirm the deadline (20 vs 30 September) and the internal hackathon date.
2. Start the RELLIS-3D download — nothing in M1 onward can begin without it.
3. Get me the official PS text so the module list can be checked against every clause before
   a line of code is written.
