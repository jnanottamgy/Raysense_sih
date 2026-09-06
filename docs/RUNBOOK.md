# Runbook — the room

For the internal hackathon, the nomination pitch and the grand finale. Everything in the
repository is evidence; this is how it gets used in front of people.

**Every number here appears in [`RESULTS.md`](RESULTS.md), which is generated from committed
CSVs. If a number is not in that file, do not say it.**

---

## The first ninety seconds

Rehearse this until it is not read. It follows two rules that matter more than anything else
you could add: open in their language, and lead with the failure rather than the fix.

> "A UGV operating in unstructured terrain carries a hard SWaP budget on its perception
> stack. We looked at what that budget actually buys.
>
> *[slide 2]*
>
> We took a stock Ouster OS1-64 — the sensor on the RELLIS off-road platform — and drove it
> past six obstacles, forty times, at full resolution. Every ray. No budget limit at all.
>
> It found **93 percent** of the obstacles that stick up.
>
> And **11 percent** of the ones you fall into.
>
> *[pause]*
>
> That is not a budget problem. At full scan you are already spending everything. So we went
> and found out why."

Do not say the team name, the college, or the words "we are excited to present". The jury has
your slide. Start with their problem.

### Then, in order

| Beat | Slide | The line that carries it |
|---|---|---|
| **Why** | 3 | "A bump degrades linearly with range. A ditch degrades **quadratically**. At 30 metres this sensor can drive past a six-metre ditch and register nothing." |
| **The consequence** | 4 | "Same geometry, run backwards: this sensor caps you at **23 km/h** if you must never enter a one-metre ditch. Nobody publishes that number." |
| **The fix** | 3 | "The quadratic that causes the blindness, normalised, is the detector. **91 percent, at a twentieth of the points.**" |
| **The proof** | 5 | *run the demo — see below* |
| **What we got wrong** | 6 | "Three things we believed and then disproved by building them." |

---

## The demo — exact sequence

`results/demo.html`. Open it **before** you walk in. Do not open it in front of them.

1. **Set up the frame.** *"Both systems, same sensor, same scene, 2 percent budget. Ours
   actually uses slightly fewer rays — 1,256 against 1,280. Left is a conventional
   height-based system. Right is ours."*
2. **Scrub to frame 4.** *"Eighteen metres out. We say ditch ahead. It says it does not know."*
3. **Scrub to frame 8.** Stop. Let it sit. *"Eleven metres. It now says **clear to drive**."*
   — this is the moment; do not talk over it.
4. **Frame 10.** *"Eight point six metres. It finally warns — nine point eight metres later
   than us, and inside the braking distance it would need at any real speed."*
5. **Frames 20 and 22.** *"And it does not hold. It goes back to 'unknown'. It is reasoning
   about heights it can see instead of gaps it cannot."*

Then stop talking. Do not narrate the rest.

### Before the room

- [ ] `demo.html` already open in a browser tab, at frame 0
- [ ] Laptop in **flight mode** — prove it, it costs nothing and it lands
- [ ] Screen brightness up; the hatching is the point and it dies on a dim projector
- [ ] Second laptop with the same tab open
- [ ] The PDF deck on a USB stick, and on both laptops
- [ ] `results/demo_frames/frame_008.png` open as a still, in case the player fails

Nothing is computed live. There is nothing to go wrong except the machine, and the still
image covers that.

---

## The hard questions

Short answer first, number second, offer of detail third. Never bluff a number.

| They ask | Say |
|---|---|
| **Which sensor does this run on?** | "Three backends. Steerable if you have it, return-masking on a spinning sensor if you do not, replay for evaluation. On a spinning sensor we save bandwidth, memory and compute — not laser power, and we do not claim otherwise." |
| **How is this different from AEye, or the 2025 adaptive-scanning paper?** | "Those are urban and unconstrained. Adaptive lidar sampling is established — we cite it on slide 6. What does not exist is anyone reconciling it with negative obstacles, because all of that work is on roads where ditches barely occur." |
| **Isn't this just simulation?** | "Yes, and that is a real limitation. We use a controlled testbed because ground truth is *known* rather than inferred — public off-road datasets contain almost no labelled ditches. RELLIS-3D corroboration is the next step and it has not been done." |
| **What is your false-positive rate?** | "73 percent precision at our threshold. Not clean. Crest occlusions produce genuine range gaps — arguably not false positives, since the ground behind a crest really is unobserved, but we count them against ourselves." |
| **How did you choose that threshold?** | "By sweep, against the identical terrain with the ditches removed. 2.0 gives 94 percent recall at 46 percent precision; 3.0 gives 88 at 73. Six points of recall bought an 89 percent reduction in false flags. The curve is in the repository." |
| **Does the smart allocation actually help?** | *Answer this one honestly and fast — it is the trap.* "On whole-map recall, no — plain decimation beats it. On warning distance at a 2 percent budget, yes: 1.88 times, 23 metres against 12. Above about 10 percent budget a static forward wedge beats us. We built three allocator designs and the first two lost outright." |
| **Is it real-time?** | "43 milliseconds a frame for the detector, on a laptop CPU, in Python. It replaced an approach that cost 500. We have not benchmarked on Jetson-class hardware and will not claim a number we have not measured." |
| **Why not just scan the front densely?** | "That is one of our baselines and it is a good one — above 10 percent budget it beats us on warning distance. Below that it does not, because threats are not only ahead and staleness matters." |
| **What happens if it misses one?** | "Then it reports *unknown*, not *drivable*. There is no code path that turns an unobserved cell into a traversable one, and there is a property test asserting it across randomised maps." |

### If you do not know

*"I do not have that measured. I can tell you what we did measure, which is X."* Then move.
A jury forgives a gap. It does not forgive an invented number, and on a DRDO problem
statement they will know.

---

## Rounds 1 to 3 are free consulting

The finale has four stages. The first three are mentoring; the fourth is the power round.
Most teams spend the first three defending their design. Do not.

At the end of each early round, ask every juror the same question, out loud, with a notebook
open where they can see it:

> **"What would you need to see to trust this in the field?"**

Write it down. Then build it. Open the next round with **"you asked for X — here it is."**
That single behaviour is worth more than any feature you could add in the same hours.

---

## Never say

- **"We invented this."** Say *characterised*, *quantified*, *constrained*, *made
  deployable*. Adaptive lidar sampling is a published field with shipping products, and
  slide 6 says so before anyone asks.
- **"Our allocator beats the baselines."** It does not, on whole-map recall. Say the metric
  it wins on and the budget where it stops winning.
- **"No false positives."** 73 percent precision. An earlier version of this project claimed
  zero, measured on a single azimuth column, and it was wrong.
- **Any number not in `RESULTS.md`.**

---

## Who does what in the room

| Role | Owns |
|---|---|
| **Lead** | The ninety seconds, the demo narration, jury interaction, the notebook |
| **Mapping** | The 2.5D grid, three-valued traversability, the "what if it misses one" answer |
| **Allocator** | The safety floor, the 23 km/h derivation, the honest allocator answer |
| **Evaluation** | Every number, the threshold sweep, "how did you choose that" |
| **Simulation** | Why a controlled testbed, what ground truth means, the RELLIS gap |
| **Demo** | The laptops, the fallbacks, the still image, the USB stick |

**Everyone must answer for their own module unprompted.** Juries probe by asking the quiet
member a question. If four people look at the lead when asked something, the team reads as
one person and five passengers.

---

## Before submission

- [ ] Confirm the deadline on sih.gov.in — the listing showed **20 September**, other sources
      said the 30th
- [ ] Confirm the internal hackathon date with the SPOC — it is earlier and it is the one that
      binds
- [ ] Six members, same college, **at least one female member** — eligibility gate
- [ ] **Get the official problem-statement text and map every clause to a deliverable.**
      Nothing in this repository has been checked against it, and every clause is a scored
      requirement
- [ ] Rebuild the deck in the official template if one is published — a non-conforming deck
      can be rejected on format alone
- [ ] `bash scripts/verify_reproducible.sh` passes
