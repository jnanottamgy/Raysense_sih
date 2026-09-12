# Raysense — Judge Q&A

**SIH26053 · DRDO · Adaptive Variable Resolution 2.5D Lidar Mapping**
8 minutes to present · **2 minutes of questions — that is about 4 questions, so ~25 seconds each.**

Every number below is traceable to a committed CSV in `results/`. If you cannot trace it,
do not say it.

---

## 0 · How to answer (read this part twice)

### The three-move answer

| Move | Length | Example |
|---|---|---|
| **1. The claim** | one sentence | *"Ninety-one percent, at five percent of the points."* |
| **2. The evidence** | one sentence | *"Forty frames, ground truth known, committed CSV."* |
| **3. The bound** | one sentence | *"On our testbed — we have not run real sensor data yet."* |

Move 3 is not weakness. **Move 3 is why they believe moves 1 and 2.** A team that volunteers
its own limit has told the judge it knows where the limit is; a team that doesn't has told
the judge it hasn't looked.

### When you do not know

Say exactly this, then stop:

> **"We haven't measured that. What we did measure is ⟨nearest thing⟩. To answer your
> question properly we'd need to ⟨the specific experiment⟩."**

Never invent a number. Never say "roughly" or "around" about something you did not compute.
A judge who catches one fabricated figure discounts every other figure you gave.

### Never say these

- ❌ "It should work on real data" → ✅ "We have not run real data. Zero frames."
- ❌ "Basically" / "kind of" / "sort of" → cut them, they read as hedging under pressure
- ❌ "Our AI…" — **there is no learning in this system**, it is geometry. Say *geometry*.
- ❌ Any number you cannot name the source of
- ❌ Talking over a judge. If they interrupt, **stop mid-word and listen.**
- ❌ "Good question!" — it wastes 1.5 of your 25 seconds

### Who takes what

| Topic | Answers | Backup |
|---|---|---|
| Why this PS · prior art · references · framing | **Pranavi** | Jeevika |
| What it does · why it's new · the demo | **Jeevika** | Nikita |
| Physics · the detector · feasibility · performance | **Nikita** | Jeevika |
| Impact · deployment · who benefits | **Anuj** | Pranavi |

**Rule: one person answers. Nobody adds.** Two voices on one question looks like the first
answer was wrong. If you genuinely must add, wait for a full stop and say *"one number to add —"*.

If a question lands outside everyone's lane, **Nikita takes anything technical, Pranavi
takes anything else.** Decide this now, not at the podium.

---

## 1 · The six numbers everyone must know cold

Any of you can be asked any of these. Drill until they come out without thinking.

| # | Fact | Say it as |
|---|---|---|
| 1 | Full scan detects **92.9%** of positive obstacles, **11.5%** of negative ones | *"Ninety-three percent of what sticks up. Eleven percent of what you fall into."* |
| 2 | Ditch detectability is **quadratic** in range, bump is **linear** | *"A bump scales with r. A ditch scales with r-squared."* |
| 3 | At 30 m an OS1-64 can miss a **6.2 m** wide ditch | *"Six metres wide. Invisible at thirty."* |
| 4 | Our detector: **91.4%** at a **5%** budget (vs **9.7%** for the prior method) | *"Ninety-one percent at a twentieth of the points."* |
| 5 | Precision at threshold 3.0 is **79.4%**, not 100% — and only **5** cells now flag on clean terrain, down from 436 | *"Seventy-nine percent — and five false cells, not four hundred."* |
| 6 | **Zero** frames of real sensor data run so far | *"Zero. It's the next thing we do."* |

---

## A · Premise and "so what"

**Q. What problem are you actually solving?**
> A lidar on a ground vehicle sees what sticks up far better than what you can fall into.
> On our testbed, a full scan — every ray, no budget limit — finds 92.9% of boulders and
> 11.5% of trenches. Our contribution is a geometric test that takes that 11.5% to 91%
> while using a twentieth of the points.

**Q. Isn't this a solved problem? Lidar obstacle detection is everywhere.**
> Positive-obstacle detection is solved. Negative-obstacle detection is not, and the reason
> is geometry, not algorithms. A boulder blocks beams. A ditch is *stepped over* — the beams
> that should have entered it land beyond it. You cannot fix that by spending more rays,
> because a full scan already spends everything. That's the 11.5% number.

**Q. Why does it matter? It's just a ditch.**
> For a UGV a ditch is not damage, it's mission loss — the vehicle is immobilised in the
> field, often under observation. And the failure is worse than blindness: the system is
> *confidently wrong*. It sees the trench rim, judges it flat, and reports drivable. On our
> data that confident-wrong rate rises with more data — 1.9% at a 2% budget up to 6.4% at
> full scan.

**Q. Why this problem statement?**
> Because the blindness is structural, so no amount of engineering effort on the existing
> approach removes it — which means there is something real to contribute. And because it's
> DRDO: off-road, unmapped ground, where negative obstacles are common and a stuck vehicle
> is a casualty risk, not an inconvenience.

---

## B · The physics (Nikita)

**Q. Derive the quadratic for me.**
> Sensor at height h, beam pitch Δθ. Two adjacent beams hit level ground at ranges r and
> r + Δr. From similar triangles the ground spacing grows as r²·Δθ/h. A ditch narrower than
> that spacing has no beam land inside it — both beams straddle it. So the smallest
> guaranteed-detectable ditch width is **w ≥ r²·Δθ / h_sensor**. A bump is different: a bump
> of height h intercepts a beam when h ≥ r·Δθ. Linear, not quadratic.

**Q. What sensor are those numbers for?**
> Ouster OS1-64. Δθ = 0.714°, mounted on a 1.8 m mast. Real published geometry, not invented.

**Q. Give me the table.**

| Range | Ground spacing (measured) | Smallest bump | Smallest ditch |
|---:|---:|---:|---:|
| 10 m | 0.72 m | 0.12 m | 0.69 m |
| 20 m | 3.51 m | 0.25 m | 2.77 m |
| 30 m | 9.17 m | 0.37 m | 6.23 m |
| 40 m | 16.51 m | 0.50 m | 11.08 m |

> Note: quote the **measured** spacing column. The closed form understates it by about 40%
> at 40 m, because the ground isn't a perfect plane. We use the measured one.

**Q. Where does 23 km/h come from?**
> A 1 m ditch is guaranteed straddled — invisible — beyond 12 m. Braking model: 0.3 s
> reaction, 2.0 m/s² deceleration. Solving for the speed whose stopping distance equals 12 m
> gives 6.35 m/s, which is 22.9 km/h. So a stock OS1-64 on a UGV that must never enter a
> one-metre ditch cannot safely exceed about 23 km/h — **and the sensor gives no indication
> that this is so.** That number is a deliverable in itself.

**Q. Your braking model is optimistic/pessimistic.**
> Possibly — 2 m/s² on loose off-road surface is a defensible mid-estimate, and the reaction
> time is a placeholder for a real autonomy stack. The model is one dataclass with four
> fields; give us your platform's numbers and the speed ceiling recomputes in one line.
> The *method* is what we're claiming, not the 23.

**Q. Just raise the sensor.**
> It helps linearly and it's the right first move — w scales as 1/h. But on a 1.4 m wide
> UGV you cannot mount a 4 m mast, and doubling mast height only halves the minimum ditch
> width while range squares against you. It buys you a constant, not a different curve.

**Q. Just tilt the sensor down.**
> Then you trade far-field range for near-field density and lose the ability to see what's
> coming. It's the same total angular budget; tilting moves the blindness, it doesn't remove
> it. Our approach doesn't change the scan pattern at all — it reasons about the gaps.

---

## C · The detector (Nikita / Jeevika)

**Q. How does the detector work — in one sentence?**
> Two adjacent beams that both return should land a predictable distance apart on level
> ground. If the far one lands much further out than predicted, the surface between them
> dropped away. **anomaly = measured gap ÷ predicted gap at that range.**

**Q. Why is it range-normalised?**
> Because the predicted gap already grows as r². Dividing by it makes the test
> range-independent — one threshold works at 10 m and at 40 m. An un-normalised gap test
> would fire constantly at long range and never at short range.

**Q. Where does threshold 3.0 come from? Did you tune it to look good?**
> We swept it and scored against the **identical terrain with the ditches removed** — that's
> the only honest control, because it isolates what the test does to terrain that has no
> ditch in it.

| Threshold | Ditch recall | False cells | Precision |
|---:|---:|---:|---:|
| 2.0 | 94.0% | 3,883 | 45.6% |
| **3.0** | **88.0%** | **436 → 5** | **73.3% → 79.4%** |
| 4.0 | 82.6% | 249 | 82.7% |
| 7.0 | 59.6% | 0 | 92.2% |

> 3.0 is the knee. Against 2.0 it costs six points of recall and removes 89% of the false
> flags. Going to 4.0 costs another five points for far less gain. `results/threshold_sweep.csv`.

**Q. Show me the whole budget curve, not just the 5% number.**

| Point budget | Prior method (absence test) | **Our discontinuity test** |
|---:|---:|---:|
| 2% | 6.7% | **74.9%** |
| 5% | 9.7% | **91.4%** |
| 8.6% | 11.3% | **96.0%** |
| 100% | 15.2% | **99.8%** |

> Two things to read off it. The prior method never gets above 15% *even at a full scan* —
> that's the structural blindness. And our curve is already at 91% by 5%, so the last 95% of
> the points buys eight more points of recall. That flatness is the whole argument for a
> budget.

**Q. 79% precision means one alarm in five is false. An operator will start ignoring it.**
> It used to be one in four. We found out what those false alarms actually were and removed
> most of them. **A crest occlusion makes the same signature as a ditch** — the ground rises,
> the far beam clears the rise, and the shadow behind it is an unexplained gap.
>
> There is one physical asymmetry: **a crest is reached uphill, a ditch is not.** We measured
> the approach slope of every flagged gap. Real-ditch gaps top out at **0.039**; crest gaps on
> the ditch-free control start at **0.069**. The populations do not overlap. Rejecting gaps
> approached on a grade steeper than 0.10 takes false cells from **436 to 5 — a 98.9%
> reduction — with ditch recall unchanged at 88.0%** and the headline 91.4% untouched.
>
> What's left is mostly the flagged span overrunning the true ditch rectangle. That is
> localisation slop, not a phantom hazard. And a candidate is "slow down and look", not "stop".

**Q. What does the crest guard cost you?**
> A ditch approached on a steep uphill. We measured the boundary rather than guessing it: up
> to a **10% grade** the trench is still found; at **12%** the detector can see it but the
> guard suppresses it; from about **15%** the trench is invisible either way, because the near
> rim occludes it. So the harm window is roughly **11–14% of uphill grade**. It is pinned by a
> test so it cannot regress silently, and `crest_rise=0` turns the guard off for any platform
> that would rather take the false alarms.

**Q. What's your false positive rate on flat ground?**
> Zero flags on flat ground. On rolling terrain the max ratio is 2.48 and it produces 70
> flags per scan. Put a 2.4 m trench in that same rolling terrain and the max ratio goes to
> 7.28 with 299 flags. The signal separates from the terrain; the threshold at 3.0 sits in
> that gap.

**Q. Why not use deep learning?**
> Three reasons. **Data** — labelled negative obstacles barely exist; RELLIS-3D, the standard
> off-road set, has almost none, so we'd be training on the sensor's own blind spot.
> **Verifiability** — DRDO has to certify this. A closed-form geometric bound can be argued
> in a safety case; a network's failure modes cannot. **It isn't needed** — the physics gave
> us 91% at 5% budget with 1.5 ms of NumPy. A network would be a heavier answer to a solved
> question. Where learning *would* help is classifying what kind of negative obstacle it is,
> once you know one is there. That's downstream of us.

**Q. What's the three-state map and why does it matter?**
> Conventional maps are two-state: free or occupied. That silently merges "I looked and it
> was clear" with "I never looked" — and a ditch returns nothing, exactly like an unscanned
> patch. We carry OBSERVED, UNKNOWN and CANDIDATE_NEGATIVE, and **UNKNOWN is the zero value**,
> so a fresh map starts honest rather than starting optimistic. Nothing in the system
> upgrades "I did not look there" into "safe to drive", and there is a test that proves that
> across randomised maps.

**Q. How do you tell a ditch from a puddle / from absorbing material / from a sensor dropout?**
> We can't, and we don't claim to. We report a *geometric* anomaly: the surface between two
> beams is not where the ground plane says it should be. Classifying it is downstream work
> and would need reflectivity or a second modality. What we've done is turn an invisible
> hazard into a flagged region — that's the step that was missing.

---

## D · The allocator — the honest loss (know this cold)

> **This is the question most likely to hurt you, because the PS title says "adaptive
> variable resolution" and our measurement says the adaptive part is not where the win is.
> Do not dodge it. Own it, and it becomes your strongest moment.**

**Q. Your problem statement is about adaptive allocation. Does yours beat uniform sampling?**
> On whole-map recall, no — and we say so on the slide. Plain uniform decimation gets 91.4%
> at a 5% budget; ours gets 79.3%. Coverage wins a question about *the whole map*.
> On **warning distance** — how far away was the ditch when you first saw it, which is what a
> vehicle actually cares about — ours wins: **24.5 m against 12.3 m at a 2% budget, 1.99×.**
> That's 6.1 seconds to react instead of 3.1. It's also the only method that finds all four
> ditches at 2%.

**Q. So which is it? Are you claiming the allocator works or not?**
> Both statements are true and they're not in tension. They answer different questions.
> Whole-map recall asks "did you eventually map every ditch, including one 60 m off your
> route?" — spreading your rays wins that. Warning distance asks "how early did you see the
> one in front of you?" — concentrating them wins that. We report both because reporting
> only the favourable one would be dishonest.

**Q. Then what is your actual contribution?**
> **The detector, not the allocator.** We started out believing the win was smart allocation.
> We measured it, and it wasn't. The win is a geometric test that recovers 91% of negative
> obstacles from 5% of the points — and that works with plain uniform decimation, no
> allocator involved. We changed our claim to match the measurement. The allocator earns its
> place at very low budgets, around 2%, and we quote it only there.

**Q. Where does the allocator stop helping?**
> Above about 10% budget a static forward wedge overtakes it, and at 10% that wedge already
> matches a full scan's 28.2 m warning distance. So the allocator's window is roughly 2–8%.
> We say that before being asked.

**Q. Did you try other allocator designs?**
> Three, and the first two lost outright. Ray-wise need-weighted top-k left 3.5 beams per
> azimuth column where uniform left 16 — and our detector compares *adjacent beams within a
> column*, so thinning the column silenced the detector. That's the lesson: an allocator that
> ignores its detector's structural requirement makes the whole system worse. Column-wise
> fixed that — 40× more gaps found at 2% — but covered too little scene. The shipped design
> is a hybrid: a guaranteed uniform sweep first, then a steered surplus.

---

## E · Validation — the hardest area

**Q. Have you tested on real sensor data?**
> **No. Zero frames.** Everything we've shown is a controlled testbed where ground truth is
> known rather than inferred. RELLIS-3D is the intended corroboration and it's the next
> thing we do — the reader is written, but `n_azimuth`, the `.label` packing and the pose
> frame are all unverified, so we will not claim it works until it has run.

**Q. Then why should I believe any of it?**
> Because the testbed was chosen to make the result *harder* to fake, not easier. Public
> off-road datasets contain almost no labelled ditches — so scoring against them means
> scoring against the sensor's own blind spot, and you would measure your own blindness as
> success. We built a scene where we know exactly where every ditch is. And the whole thing
> rebuilds from an empty virtualenv and reproduces bit-identically: 13 rows compared,
> largest difference in any metric 0.00e+00.

**Q. Simulation always works. Real lidar is noisy.**
> Agreed, and that's the honest risk. Two things in our favour. The effect we exploit is
> *geometric*, not photometric — it depends on where beams land, which range noise of a few
> centimetres doesn't change at a ratio threshold of 3.0. And our simulator uses the real
> OS1-64 angular geometry, so the beam spacing that produces the blindness is not invented.
> But we won't pretend: until RELLIS-3D runs, it is a simulation result.

**Q. How many tests? What's your coverage?**
> 103 tests, ruff clean. They pin the things the project rests on — that a fired-but-empty
> ray survives the pipeline, that a cell inside a trench is never marked observed, that a
> deep trench destroys all returns. When one of those tests asserted the wrong physics we
> rewrote the test, not the code.

**Q. What would falsify your claim?**
> A RELLIS-3D sequence with a labelled ditch where our anomaly ratio never exceeds 3.0 at a
> range where the geometry says it should. That's a clean falsification and we'd report it.

---

## F · Hardware and deployment (Nikita / Anuj)

**Q. What hardware do you need?**
> None that isn't already on the vehicle. This is software on data a deployed UGV already
> produces, running on the lidar that platform already carries. That's deliberate — it makes
> it retrofittable to fielded vehicles rather than a next-generation-platform proposal.

**Q. Will it run on embedded hardware — Jetson, a rugged box?**
> **We have not run it on a Jetson, so we quote no Jetson number.** What we *have* measured,
> on an Intel Xeon at 2.10 GHz: **1.5 ms per frame at the 5% budget that produces the 91%
> result**, p95 2.2 ms — **67× inside a 100 ms frame at 10 Hz**. Cost is linear in rays at
> **0.44 µs per ray, R² = 0.9998**. `results/benchmark.csv`.
>
> Because it is linear with a measured constant, the bound is easy arithmetic: a device
> **20× slower per core still lands at 30 ms** — inside the frame. That is arithmetic on a
> measured fit, not a measurement. The benchmark takes a `--label`, so one command on a
> Jetson produces a comparable row and we would publish whatever it says.

**Q. What does it cost per frame?**

| Budget | allocate | acquire | integrate | detect | **TOTAL** | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 2% | 0.22 | 0.10 | 0.16 | 0.18 | **0.71 ms** | 1.22 ms |
| **5%** | 0.56 | 0.19 | 0.32 | 0.34 | **1.48 ms** | **2.20 ms** |
| 100% | 11.10 | 1.32 | 4.05 | 12.42 | **28.77 ms** | 35.78 ms |

> Timed: allocate, acquire, integrate, detect. **Not timed: generating the scan** — on a
> vehicle the sensor does that, so timing it would measure our simulator. 20 frames × 5
> repeats. Milliseconds.

**Q. Is that real-time?**
> At 10 Hz the frame budget is 100 ms and we use **1.5**. Sixty-seven times over.
> The method we replace — the absence test — costs **252 ms at the same budget**, so it
> cannot run in real time at all. That is the practical argument for the gap test, separate
> from the 9.7% → 91.4% detection difference.


**Q. Does it need a steerable lidar?**
> The detector does not — it works with plain uniform decimation of a normal spinning lidar,
> which is the 91%-at-5% result. The allocator benefits from steerability. Today one
> `acquire()` seam exists with a replay backend behind it; steerable and fixed-pattern slot
> in behind the same signature. **Only the replay backend is built.**

**Q. What's the difference between saving rays and saving compute?**
> Important and we're careful about it. On a steerable sensor a saved ray is a laser pulse
> never fired — real power and eye-safety budget. On a normal spinning lidar every ray fires
> regardless, so the budget saves *bandwidth, memory and compute*, not laser energy. We do
> not claim SWaP savings on a spinning sensor.

**Q. Is this indigenous? Any foreign dependency?**
> Pure Python 3.11 and NumPy — no proprietary libraries, no cloud service, no foreign
> runtime. It runs air-gapped. The sensor model is parameterised, so it retargets to an
> Indian lidar by editing four numbers.

**Q. What about GPS-denied or jamming environments?**
> The detector needs no GPS at all — it's a within-scan test on adjacent beams. The
> allocator's predict step uses ego-motion, which can come from wheel odometry or IMU;
> degraded odometry degrades the steering, not the detection.

---

## G · Novelty and prior art (Pranavi)

**Q. What's actually new here? Adaptive lidar already exists.**
> It does and we cite it — AEye's iDAR patents, NEC Labs' MEMS foveating lidar, the 2025
> temporal-cues work. Negative-obstacle detection also exists — DTIC, IEEE ROBIO, RELLIS-3D.
> **The two literatures never met.** Every adaptive-lidar paper we found is urban driving,
> where ditches barely occur. Every negative-obstacle paper assumes dense uniform scanning.
> Our contribution is at the intersection: the corrected quadratic detectability floor, a
> three-state map where unknown is a real value, and a range-normalised gap test that works
> *at a fraction of a scan*.

**Q. Isn't the gap test just standard discontinuity detection?**
> Discontinuity detection is standard. Two things aren't. First, **range normalisation** —
> dividing by the predicted gap so a single threshold works across the full range, which
> matters precisely because the gap grows quadratically. Second, we run it on a *decimated*
> scan and show it still works — 91% at 5%. Standard methods are applied to full clouds.

**Q. Name your references.**
> RELLIS-3D (ICRA 2021, off-road, Ouster OS1-64). NEC Labs MEMS foveating lidar,
> Pittaluga et al. Adaptive LiDAR Scanning with temporal cues, 2025. AEye iDAR / 4Sight —
> US 11675053, 11782136, 11860313. Larson & Trivedi, DTIC ADA561293, negative obstacles.
> IEEE ROBIO 2024 on sparse 3D lidar and off-road ditches.

**Q. Have you read the official problem statement text?**
> Not the full official text — we worked from the title and the domain. That's a gap we'd
> close first, and if the official text asks for something we haven't covered we'd rather
> find that out now than after nomination.
> *(If you have obtained it by presentation day, delete this answer and say so.)*

---

## H · Feasibility, scope, timeline

**Q. What exists today versus what's a plan?**
> Built and measured: the sensor model, the simulated off-road testbed with known ground
> truth, the three-state fixed-grid 2.5D map, ray accounting, the discontinuity detector,
> three allocators, the evaluation harness, 103 tests, and an offline demo. Designed but not
> built: the quadtree map, the live steerable and fixed-pattern backends, dynamic object
> tracking. We keep that line visible in the repo so nobody is misled about which side of it
> something is on.

**Q. What's the biggest risk to delivery?**
> RELLIS-3D corroboration. If the anomaly ratio doesn't separate on real data the way it does
> on ours, the headline number changes. That's why it's the next task and not the last one.

**Q. How long to a field-ready version?**
> We won't give you a date we can't defend. The ordered path is: RELLIS-3D corroboration,
> then an embedded benchmark, then a live-sensor backend, then integration against a real
> autonomy stack. The first two are weeks of work; the last two depend on platform access,
> which isn't ours to schedule.

**Q. Who built what?**
> *(Answer honestly and specifically — judges ask this to find passengers. Each of you name
> your own contribution in one sentence. Do not let one person narrate the whole team.)*

---

## I · Impact and benefits (Anuj)

**Q. Who benefits and how?**
> Three groups. **Defence UGV operators** — unmapped ground becomes navigable, because the
> vehicle now knows what it hasn't seen. **Field crews** — a ditch doesn't damage a vehicle,
> it ends the mission, often somewhere you can't recover it from. **Platform designers** —
> they get a quantified speed ceiling per sensor, which today nobody publishes.

**Q. Quantify the impact.**
> Detection of negative obstacles goes from 11.5% to 91.4% while using 5% of the points —
> twenty times fewer points, and nearly eight times the detection. Warning distance at a 2%
> budget goes from 12.3 m to 24.5 m, which is 6.1 seconds to react instead of 3.1. And the
> speed ceiling — 23 km/h for a 1 m ditch on a stock OS1-64 — is a number a programme manager
> can act on immediately, before any of our software ships.

**Q. Civilian applications?**
> Agricultural autonomy (irrigation channels and furrows are negative obstacles), mining haul
> roads, disaster response over rubble and washouts, and construction sites. All share the
> property that the ground is unmapped and the hazards are things you fall into.

**Q. What does this cost to deploy?**
> Software on existing hardware, so the marginal cost is integration effort, not capital. No
> new sensor, no new mount, no new compute specified — though we haven't benchmarked embedded
> compute, so we won't claim it fits an existing box until we've measured it.

---

## J · Hostile and trap questions

**Q. This is just a simulation. You haven't built anything.**
> It's a measurement harness with known ground truth, 103 tests, and bit-identical
> reproducibility from an empty environment — and yes, the sensor data is synthetic. That's
> the stated limitation, it's on the slide, and RELLIS-3D is next. What we have built is the
> part that was missing: a test that finds ditches a full scan misses.

**Q. Your own slide says your allocator loses. Why are you here?**
> Because the allocator was never the contribution — we found that out by measuring, and we
> changed the claim instead of the number. The contribution is the detector: 11.5% to 91%.
> A team that only reports its wins hasn't finished testing.

**Q. You've got 79% precision and no real data. That's not a product.**
> Correct. It's not a product, it's a result — and the result is that the blindness is
> structural and measurable, and one geometric test removes most of it. The speed-ceiling
> number is deployable today with no software at all.

**Q. Isn't 5% of the points just throwing away data?**
> Yes, deliberately — and the interesting part is that it costs almost nothing. 91.4% at 5%
> against 99.8% at 100%. Eight points of recall for twenty times less data. That's the trade
> a bandwidth- or compute-limited platform wants to know about.

**Q. What if I told you a stereo camera solves this for a tenth of the cost?**
> Stereo has the same geometry problem plus a texture problem — it also cannot see into a
> gap it doesn't sample, and off-road terrain is often texture-poor. Where stereo genuinely
> helps is as a second modality for classification once we've flagged a candidate. We'd take
> that as complementary, not competing.

**Q. *(Silence / a judge just stares)*.**
> Stop talking. The answer is finished. Silence is a test of whether you'll pad. Wait.

**Q. *(A judge asserts something factually wrong about your work)*.**
> Correct it once, politely, with the number: *"I think there may be a mix-up — the 91% is at
> a 5% budget, not a full scan. Full scan is 99.8%."* Then stop. Do not argue twice.

---

## K · Team and process

**Q. How did you validate your own assumptions?**
> Wherever we could, against a control. The threshold was swept against the identical terrain
> with the ditches removed. The allocator was measured against uniform decimation and a static
> forward wedge, and lost on one metric. When a test asserted the wrong physics we rewrote the
> test. We also withdrew a claim mid-project — we had said "zero false positives on rolling
> terrain", found we'd measured it on a single azimuth column, and corrected it to 70 flags.

**Q. What would you do differently?**
> Read the official problem statement text first, and get real data in earlier. We spent
> effort building three allocators before measuring whether allocation was where the win was.

---

## L · Questions you want them to ask (plant these)

If the floor goes quiet, one of you offers *one* of these — it converts dead air into your
strongest material. **Offer one, not three.**

> *"May I show you the one frame where the conventional system says clear to drive?"*
> → Frame 8. 11.4 m from a 3 m wide, 2.2 m deep trench. Both systems at a 2% budget —
> 1,280 rays for the conventional one, 1,256 for ours, so we use slightly **fewer**. It says
> clear to drive. We said DITCH AHEAD at 18.4 m. It only warns at 8.6 m — 9.8 metres and
> 2.5 seconds later, inside the braking distance it needs at any real speed. And it doesn't
> hold — later in the run, at frames 20 and 22, it reverts to *unknown ahead*, because it is
> reasoning about heights it can see instead of gaps it cannot.

> *"Would you like the number a programme manager can use tomorrow?"*
> → 23 km/h. The speed ceiling for a 1 m ditch on a stock OS1-64. Nobody publishes it.

---

## M · The last thing they hear

If you get a closing sentence, make it this one:

> **"Your sensor sees ninety-three percent of what sticks up, and eleven percent of what you
> can fall into. One geometric test takes that to ninety-one — at a twentieth of the points.
> And the same geometry tells you how fast you may drive."**

Then stop. Thank them. Do not add.
