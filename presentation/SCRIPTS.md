# Raysense — Internal SIH presentation

**8 minutes speaking · 2 minutes Q&A · 4 speakers**
Pranavi (1, 7) · Jeevika (2, 6) · Nikita (3, 4) · Anuj (5)

---

# ⚠ PART 0 — FIX THESE FOUR THINGS FIRST

I compared the deck against what we actually measured. **Four claims do not match, and two
of them will end the presentation if a judge pushes.** Fix the slides if you still can; if
you cannot, the scripts below are written to be true anyway — say what is written, not what
is printed.

### 1. CRITICAL — the deck says RELLIS-3D validated us. It did not.

- **Slide 4:** *"validated on real off-road lidar (RELLIS-3D), not simulation alone"*
- **Slide 6:** *"Validation on real off-road lidar (RELLIS-3D), not urban driving datasets"*

**We have never run a single frame of RELLIS-3D.** Every number is from our own controlled
testbed. If a judge says *"show me the RELLIS results"* — and on a DRDO statement one might —
you have nothing, and the rest of your credibility goes with it.

> **Change slide 4 to:** "Validated on a controlled off-road testbed with exact ground truth.
> RELLIS-3D corroboration is the next step."
> **Change slide 6 to:** "Ground truth is known rather than inferred — public off-road
> datasets contain almost no labelled ditches."

Said that way it becomes a **strength**: it shows you chose your evaluation deliberately.

### 2. The safety-floor formula on the slides is the wrong one

Slides 2, 3 and 6 all say **Δθ ≤ h/r**. That is the formula for a **bump**. Our actual
finding — the interesting one — is that a **ditch** binds *quadratically*:

> **Δθ ≤ w · h_sensor / r²**

A floor sized with `h/r` is comfortably satisfied **while ditches stay invisible.** That is
literally our discovery, and the slide states the thing we disproved.

> **Change to:** "Δθ ≤ w·h/r² — ditches bind quadratically, bumps linearly."

### 3. "Obstacle-Detection Safety: EQUAL TO FULL SCAN" — overstated

Measured: **91.4% at a 5% budget** against **99.8% at full scan.** Close. Not equal.
> **Change to:** "Within a few points of full-scan detection, at a twentieth of the budget."

### 4. "~3x REDUCTION" — understated, and not one of our numbers

We measured **20×** (5% budget). Do not say 3×; we cannot source it.
> **Change to:** "20× fewer points."

**Rule for all four speakers: if a number is not in this document, do not say it.**

---

# PART 1 — HOW YOU ARE BEING SCORED

Judges at the internal round are **alumni and industry professionals, technically strong,
and independent of your college coordinators.** They score against a standard rubric and
write remarks. Every team gets its marking sheet back.

| Criterion | ~Marks | Who earns it |
|---|---|---|
| **Novelty of the idea** | 10 | Jeevika (§2) |
| **Feasibility & practicability** | 10 | Nikita (§4) |
| **Technical approach / architecture** | 10 | Nikita (§3) |
| **Impact & scale** | 10 | Anuj (§5) |
| **Clarity & completeness** | 10 | Pranavi (§1, §7) — and all of you |

**The three questions judges ask most often.** Have the answer ready before it is asked:

1. **"Who actually has this problem today?"** — Name DRDO and the vehicle class. Never read
   the problem statement back at them.
2. **"What have you built so far?"** — This is where you win. **You have a running system.**
   Most teams at an internal round have slides.
3. **"Why this team?"** — Each of you must name a *different* role. Not "we all code."

---

# PART 2 — THE SCRIPTS

**Timed at 140 words per minute, pauses counted, handoffs included. Total: 8 minutes 1 second.**

| # | Section | Speaker | Slide | Time |
|---|---|---|---|---:|
| 1 | Introduction | **Pranavi** | 1 | 55 s |
| 2 | Solution + innovativeness | **Jeevika** | 2 | 96 s |
| 3 | Technical approach | **Nikita** | 3 | 84 s |
| 4 | Feasibility & viability | **Nikita** | 4 | 48 s |
| 5 | Impact & benefits | **Anuj** | 5 | 66 s |
| 6 | Prototype | **Jeevika** | demo | 73 s |
| 7 | Research + conclusion | **Pranavi** | 6 | 41 s |
| | *handoffs, 6 × 3 s* | | | *18 s* |
| | **TOTAL** | | | **481 s** |

If your stopwatch says more than 8:15 on a dry run, you are speaking too fast **and** cutting
pauses — which sounds worse, not better. Slow down and keep the silences.

**Notation**
`[PAUSE 2]` — stop, silently count two · `→ CLICK` — advance slide
*(italics)* — tone and body · **↓** slow down · **↑** lift energy

**Pace: roughly 140 words a minute.** That is slower than feels natural. Everyone rushes
under lights. If you finish early that is fine — finishing late is not.

---

## 1 · INTRODUCTION — PRANAVI — 55 s → SLIDE 1

*(Walk to centre. Do not begin until you have made eye contact with two judges. Hands still.)*

> "Good morning. Problem statement S-I-H two-six-zero-five-three, from DRDO."

**[PAUSE 2]** *(let them find the slide)*

> "A defence ground vehicle drives through terrain nobody has mapped. One lidar. A hard power
> budget."
>
> "So we asked what that lidar actually sees. We took the sensor that class of vehicle
> carries — an Ouster OS1 sixty-four — and drove it past six obstacles, forty times over.
> Full resolution. Every ray. **No budget limit at all.**"

**[PAUSE 2]** *(↓ slow right down — the next two lines are the whole presentation)*

> "It found **ninety-three percent** of the obstacles that stick up."

**[PAUSE 2]**

> "And **eleven percent** of the ones you fall into."

**[PAUSE 3]** ← *(Do not fill this. Let them do the arithmetic. This silence is the single
most valuable three seconds you have.)*

> "That is not a budget problem — at full scan you are already spending everything. So we
> went and found out why. Jeevika."

*(Step back. Do not keep talking.)*

---

## 2 · PROPOSED SOLUTION + INNOVATIVENESS — JEEVIKA — 96 s → SLIDE 2

*(Confident, brisk. You are explaining a mechanism, not selling.)*

> "The reason is geometry. A ditch is not detected by what comes back — it is detected by
> what **doesn't**. And a narrow trench is never entered by the beams at all. It is
> **stepped over**."

**[PAUSE 1]**

*(Point at the three-panel figure, right side of the slide.)*

> "Three cases. A — beam fired, hits ground, you get a return. B — beam fired into a ditch,
> **nothing comes back.** C — no beam ever fired there, nothing comes back."

**[PAUSE 2]** *(↓)*

> "To the sensor, **B and C are identical.** A ditch and a patch you never looked at produce
> exactly the same signal. Every existing system treats both as empty space."

**[PAUSE 2]**

> "So our map carries **three** states, not two — observed, unknown, candidate-negative.
> Unknown is a real answer. **Nothing in our system turns 'I did not look there' into 'safe to
> drive'** — and a test in our code proves it."

**[PAUSE 1]** *(↑ lift — this is the novelty claim, the 10 marks)*

> "And here is what is genuinely ours. Adaptive lidar sampling exists — AEye ships it, NEC
> published it. Negative-obstacle detection exists too. But **all** the adaptive work is
> urban driving, where ditches barely occur, and **all** the ditch work assumes dense
> scanning."

**[PAUSE 1]**

> "Nobody has put those two fields in the same room. We did — and found that adaptive
> sampling creates exactly the absences that hide a ditch. Nikita."

---

## 3 · TECHNICAL APPROACH — NIKITA — 84 s → SLIDE 3

*(Precise, unhurried. This is the architecture mark. Sound like an engineer.)*

> "The fix comes from the same geometry that causes the problem."

**[PAUSE 1]**

> "Two adjacent beams that both return land a **predictable** distance apart on level ground.
> If the far one lands much further out than it should — the surface between them dropped
> away."

**[PAUSE 2]**

> "The catch is that the prediction has to be local, because ground spacing grows
> **quadratically** with range. At ten metres, adjacent beams land seventy centimetres apart.
> At thirty metres, **nine metres apart.**"

**[PAUSE 2]** *(↓ — this is the number that makes technical judges sit up)*

> "That is why a stock OS1 can drive past a **six-metre-wide ditch at thirty metres** and
> register nothing."

**[PAUSE 1]**

*(Point at the pipeline, right of slide.)*

> "So the pipeline runs single-pass, per frame. We predict the map forward using ego-motion.
> We apply a hard safety floor **before** anything adaptive — that budget is never traded
> away. We score every angular bin by need. We acquire through one of three sensor backends —
> steerable, fixed-pattern, or replay. Then we disambiguate: we track **rays**, not just
> points, so a cell is only empty if a ray actually went there and came back from beyond."

**[PAUSE 1]**

> "Python, NumPy and Numba. The detector costs **forty-three milliseconds a frame.**"

---

## 4 · FEASIBILITY AND VIABILITY — NIKITA — 48 s → SLIDE 4

*(Steady. Do not get defensive. Owning risk reads as senior.)*

> "This needs no new hardware. It is software on data a deployed vehicle already produces,
> running on the lidar that platform already carries."

**[PAUSE 1]**

> "Our evidence is a controlled testbed where ground truth is **known** rather than inferred.
> That was deliberate — public off-road datasets contain almost no labelled ditches, so
> scoring against them means scoring against the sensor's own blind spots."

**[PAUSE 2]**

> "Three honest risks. Our precision is **seventy-three percent**, not a hundred — crest
> occlusions produce real range gaps. **RELLIS-3D corroboration is outstanding**, and it is
> next. And we have not benchmarked on embedded hardware, so we do not quote that number."

**[PAUSE 1]**

> "Anuj."

---

## 5 · IMPACT AND BENEFITS — ANUJ — 66 s → SLIDE 5

*(Warmest delivery of the four. You are the one who makes it matter.)*

> "Three groups feel this."

**[PAUSE 1]**

> "The vehicle — unmapped ground becomes something it can navigate, without waiting for a
> human to survey it first."
>
> "The field operator — fewer platforms stranded or destroyed by a ditch nobody saw. A
> negative obstacle does not damage a vehicle. It **ends** it."

**[PAUSE 2]** *(↓ — this is the line they remember)*

> "And the platform designer gets something that does not exist today. Run our geometry
> backwards and it tells you **how fast you are allowed to drive.**"

**[PAUSE 2]**

> "For a stock OS1 sixty-four, on a vehicle that must never enter a one-metre ditch, that
> answer is **twenty-three kilometres an hour.**"

**[PAUSE 2]**

> "Nobody publishes that number. The sensor gives no indication of it. It is a property of
> hardware already in the field — and it is true whether or not anything we built works."

**[PAUSE 1]**

> "Jeevika will show you it running."

---

## 6 · PROTOTYPE — JEEVIKA — 73 s → **THE DEMO**

*(Have `demo.html` **already open**, at frame 0, before you walk in. Laptop in flight mode.)*

> "This is running code, not a mockup. Both systems, same sensor, same scene, **two percent**
> of a full scan. Ours actually uses slightly fewer rays — one thousand two five six against
> one thousand two eighty."

**[PAUSE 1]**

> "Left is a conventional height-based system. Right is ours. We are driving at a trench three
> metres wide and two metres deep."

*(→ scrub to frame 4)*

> "Eighteen metres out. We say ditch ahead. It says it does not know."

*(→ scrub to frame 8. **STOP. Take your hand off the trackpad.**)*

**[PAUSE 3]** ← *(This is your money shot. Say nothing. Let them read the screen.)*

> "Eleven metres. It now says **clear to drive.**"

**[PAUSE 2]**

*(→ frame 10)*

> "Eight point six metres. It finally warns — nine point eight metres later than us, and
> **inside the braking distance it would need at any real speed.**"

**[PAUSE 1]**

*(→ frames 20, 22)*

> "And it does not hold. It reverts to 'unknown'. It is reasoning about heights it can see,
> instead of gaps it cannot."

**[PAUSE 1]**

> "Across the run: **ninety-one percent** of ditches found at five percent of the points.
> A full scan, with no absence reasoning, finds twelve. Pranavi."

*(Stop talking. Do not narrate the remaining frames.)*

---

## 7 · RESEARCH, REFERENCES AND CONCLUSION — PRANAVI — 41 s → SLIDE 6

*(Calm, unhurried. Land it — do not trail off.)*

> "Our references are on the slide. We cite them **because** the field exists — we did not
> invent adaptive lidar."

**[PAUSE 1]**

> "We found the one place those two literatures never met, and measured it."

**[PAUSE 2]** *(↓ — final three lines, slow and even)*

> "Your sensor sees ninety-three percent of what sticks up, and eleven percent of what you can
> fall into. One geometric test takes that to ninety-one — at a twentieth of the points. And
> the same geometry tells you how fast you may drive."

**[PAUSE 2]**

> "Thank you. We are happy to take questions."

*(All four step forward slightly. Nobody looks at the floor.)*

---

# PART 3 — THE 2 MINUTES OF QUESTIONS

**Answer format: short answer → the number → offer detail.** Roughly 20 seconds each; you
will get four to six questions. **The person who owns the section answers.** If you do not
know, say so and hand back a number you do know. A judge forgives a gap. A judge does not
forgive an invented number — and on a DRDO statement, they will know.

| Question | Who | Answer |
|---|---|---|
| **Have you tested on real data?** | Nikita | "Not yet, and that is our main gap. Our testbed gives exact ground truth, which public off-road datasets cannot — they contain almost no labelled ditches. RELLIS-3D is the next step and the loader is already written." |
| **Which lidar does this need?** | Nikita | "Any of three. Steerable if you have it, return-masking on a spinning sensor if you do not. On a spinning sensor we save bandwidth, memory and compute — not laser power, and we do not claim otherwise." |
| **How is this different from AEye / existing work?** | Jeevika | "Those are urban and unconstrained — we cite them on slide six. What does not exist is anyone reconciling adaptive sampling with negative obstacles, because that work is all on roads where ditches barely occur." |
| **What is your false-positive rate?** | Nikita | "Seventy-three percent precision. Not clean. Crest occlusions produce real range gaps — arguably not false positives, since the ground behind a crest genuinely is unobserved, but we count them against ourselves." |
| **How did you pick that threshold?** | Nikita | "By sweep, against the identical terrain with the ditches removed. Two-point-zero gives 94% recall at 46% precision. Three-point-zero gives 88 at 73. Six points of recall bought an 89% reduction in false flags." |
| **Does the smart allocation actually help?** | Jeevika | *(The trap. Answer fast and honestly.)* "On whole-map recall, no — plain decimation beats it. On **warning distance** at a two percent budget, yes: one-point-eight-eight times, twenty-three metres against twelve. Above ten percent budget a static forward wedge beats us. We built three allocator designs and the first two lost." |
| **Is it real-time?** | Nikita | "Forty-three milliseconds a frame on a laptop CPU, in Python. It replaced an approach costing five hundred. We have not benchmarked on Jetson and will not quote a number we have not measured." |
| **What if it misses one?** | Jeevika | "Then it reports **unknown**, not drivable. There is no code path that turns an unobserved cell into a traversable one, and a property test asserts it across randomised maps." |
| **Why this team? / who did what?** | Each, one line | Pranavi — problem framing and evaluation design. Jeevika — the three-state map and detector. Nikita — allocator, safety-floor geometry, pipeline. Anuj — impact modelling and the vehicle braking model. **Four different roles. Never "we all coded."** |

---

# PART 4 — DELIVERY RULES

1. **Nobody reads the slide aloud.** The judges can read. Your voice adds what the slide
   cannot.
2. **Rehearse with a stopwatch, three times.** First run will be 10–11 minutes. That is
   normal. The pauses are what get cut under pressure — protect them.
3. **Never say "we invented."** Say *characterised*, *measured*, *quantified*. The field
   exists and slide 6 says so before anyone asks.
4. **Volunteer the limitations before you are asked.** Nikita's §4 does this deliberately. It
   is the most credible thing a student team can do in front of industry judges.
5. **Handoffs are one word: the next person's name.** No "over to you now for the next
   section which is about…" — it wastes eight seconds, six times.
6. **All four stand for the whole presentation.** Nobody sits down. Nobody looks at a phone.
7. **The person not speaking looks at the person speaking**, not at the audience and not at
   the screen. It pulls the judges' eyes where you want them.

## Equipment — checked the night before

- [ ] `demo.html` open at frame 0, **before** entering the room
- [ ] Laptop in **flight mode** — say so out loud, it costs nothing and it lands
- [ ] Brightness at maximum (the hatched "unknown" regions die on a dim projector)
- [ ] `frame_008.png` open in a second tab as a still fallback
- [ ] Second laptop, same two tabs, same state
- [ ] Deck on a USB stick **and** emailed to all four of you
- [ ] HDMI adapter. Test it in the actual room if you can get in.
