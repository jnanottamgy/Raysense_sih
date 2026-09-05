# M7 + M8 — findings

**M7's exit criterion is met**: the failure case exists, is captured, and reproduces from a
seed. **M8's is met**: the demo runs with the network cable unplugged.

And the open question left at M5 is answered — **the allocator does earn its place**, but
only on the metric that measures what a vehicle actually needs.

103 tests pass, lint clean.

---

## 1. The allocator wins on warning distance

M5 measured whole-map recall and the allocator lost to plain decimation. The question left
open was whether it wins on **time-to-detect** — how far away a ditch is when it is first
flagged. That question was posed *before* this run, which is why the answer counts.

Mean distance from the vehicle to each ditch at the moment it is first flagged, over a
40-frame traverse past four planted ditches:

| Budget spent | uniform | front_roi | **raysense** |
|---:|---:|---:|---:|
| 2% | 17.2 m | 25.3 m | **37.6 m** |
| 5% | 34.4 m | 36.1 m | **37.6 m** |
| 10% | 25.3 m | **54.4 m** | 42.2 m |
| 20% | 36.6 m | **54.4 m** | 53.9 m |

**At a 2% budget the allocator gives 2.19× the warning distance of uniform decimation** —
37.6 m against 17.2 m. At the traverse speed of 4 m/s that is **9.4 seconds to react
instead of 4.3.** More than double.

Note what else this table says: **uniform decimation is the worst method at every budget**
on warning distance, despite being the best on whole-map recall. Both facts are true, and
they are not in tension:

* **Whole-map recall** asks *did you eventually map every ditch, including the one 60 m off
  your route?* Coverage wins that, so uniform wins.
* **Warning distance** asks *how far off was the ditch in front of you when you noticed it?*
  Concentration wins that.

A vehicle only cares about the second. The first is a mapping metric wearing a safety
metric's clothes.

**Where the allocator stops paying:** above about 10% budget `StaticFrontROI` overtakes it.
Concentrating forward is simply a good idea once you can afford it, and our need map adds
nothing beyond that. If the deck quotes an allocator number, quote the 2% one.

---

## 2. The failure case — seed 7, frame 6

`results/demo_frames/frame_006.png`. Two systems, the **same 3,277 rays**, the same scene,
the same frame. The only difference is whether the discontinuity test is running.

| | Baseline | Raysense |
|---|---|---|
| Rays this frame | 3,277 | 3,277 |
| Ditch cells flagged | 0 | 134 |
| Ditches found | 0 / 4 | 1 / 4 |
| Nearest ditch | trench @ 15 m | trench @ 15 m |
| **Verdict** | **clear to drive** | **DITCH AHEAD** |

A 3 m wide, 2.2 m deep trench sits 15 metres ahead. One system reports the ground as
drivable. The other reports a ditch. Identical input.

That is the ten seconds of the power round, and it reproduces exactly from
`--seed 7 --frames 40 --fraction 0.05`.

The full sequence is worth showing rather than just the frame: the baseline says *clear to
drive* at frame 4, and again reverts to *unknown ahead* at frame 20 — it never settles,
because it is reasoning about heights it can see instead of gaps it cannot.

---

## 3. The demo

`results/demo.html` — a single self-contained file. Twenty-one frames embedded as base64,
a play/pause/scrub control, arrow-key and spacebar navigation. **No network, no codec, no
dependencies, no live computation.** Open it from a USB stick on a machine in flight mode
and it works.

That is deliberate. Everything is rendered offline and played back, because a demo that
computes live is a demo that fails in the room, and "teams lose rounds to laptops, not to
logic" is the most repeated failure in the SIH write-ups.

`results/demo_frames/` holds the individual PNGs, so any single frame can be dropped
straight into a slide.

---

## 4. The deck

`deck/Raysense_SIH26053_Idea.pdf` — six slides, built from `deck/slides.html`, every figure
generated from a committed CSV.

1. **Title** — the one-line claim
2. **Problem** — 92.9% / 15.2% / 6.4%, measured
3. **Solution** — the anomaly ratio, the detector table, 20× fewer points
4. **Technical approach** — the safety floor, 23 km/h, three sensor backends, explicit scope
5. **Results** — frame 6, and three numbers
6. **Prior art and what is ours** — the literature cited up front, limitations volunteered

Slide 6 does the work that most teams skip: it names the prior art prominently, states three
honest limitations including *"smart allocation does not beat plain decimation on whole-map
recall"*, and only then says what is ours.

> **This must be rebuilt in the official SIH template if one is published.** A
> non-conforming deck can be rejected on format alone. Treat this as the content, not the
> artefact.

---

## 5. What the pitch is now

The claim has moved twice during the build, both times toward something stronger and better
supported. As it stands:

1. **Your sensor sees 93% of what sticks up and 15% of what you can fall into.** Measured,
   at full budget, on hardware DRDO already fields.
2. **One geometric test takes that to 96% — at a twentieth of the points.** The same
   quadratic that causes the blindness, normalised, is the detector.
3. **The same geometry caps safe speed at 23 km/h**, and the sensor gives no indication of it.
4. **Allocating that budget by need buys 2.19× the warning distance** at tight budgets — and
   nothing above 10%, which we say ourselves.

Earlier documents in `docs/` still describe the original framing — efficiency through smart
allocation. That framing is superseded. **`docs/RAYSENSE_BATTLE_PLAN.md` and the published
battle-plan page are out of date on the central claim** and should be revised before either
is shown to anyone.

---

## Still open

1. **Threshold sweep** for the discontinuity test — 2.0 admits 70 terrain flags per scan,
   3.0 probably does not. Measure it.
2. **RELLIS-3D.** Everything here is the controlled testbed. Nothing has touched real sensor
   data, and `n_azimuth`, `.label` packing and the pose frame remain unverified.
3. **The official problem-statement text**, which none of this has been checked against —
   still the highest-value thing anyone can hand this project.
