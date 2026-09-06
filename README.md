# Raysense — SIH 2026

Working repo for Smart India Hackathon 2026.

- [`docs/SIH_2026_RESEARCH.md`](docs/SIH_2026_RESEARCH.md) — deadlines, rules, scoring
  rubric, problem-statement landscape, failure modes, and what winning entries look like.

**Hard deadline: idea submission on the SIH portal closes 30 September 2026.**
The college internal hackathon deadline is earlier and is set by your SPOC.

## Documents

| File | What it is |
|---|---|
| **[`docs/RESULTS.md`](docs/RESULTS.md)** | **Measured results — start here. Supersedes the planning documents on the technical claim.** |
| [`docs/SIH_2026_RESEARCH.md`](docs/SIH_2026_RESEARCH.md) | SIH 2026 deadlines, rules, scoring rubrics, problem-statement landscape, failure modes |
| [`docs/SIH26053_CRITIQUE.md`](docs/SIH26053_CRITIQUE.md) | Review of the original approach — prior art, the steerable-hardware assumption, six holes |
| [`docs/RAYSENSE_BATTLE_PLAN.md`](docs/RAYSENSE_BATTLE_PLAN.md) | The reworked plan: architecture, experiment design, deck outline, schedule, roles, risks |
| [`docs/M0_FINDINGS.md`](docs/M0_FINDINGS.md) · [`M1_M2`](docs/M1_M2_FINDINGS.md) · [`M5_M6`](docs/M5_M6_FINDINGS.md) · [`M7_M8`](docs/M7_M8_FINDINGS.md) | Per-milestone findings, in build order |
| [`deck/Raysense_SIH26053_Idea.pdf`](deck/Raysense_SIH26053_Idea.pdf) | Six-slide idea submission |
| [`results/demo.html`](results/demo.html) | Offline side-by-side demo player |
| [`docs/raysense-results.html`](docs/raysense-results.html) | Shareable web version of the results |

## Testing

See **[`docs/TESTING.md`](docs/TESTING.md)** — setup, a 20-second smoke test, and five ways
to try to break the claims.

## Reproducing

```bash
bash scripts/verify_reproducible.sh
```

Builds a clean virtualenv from `pyproject.toml`, reruns everything, and fails if any number
differs from the committed CSVs.

**Freeze point:** commit `fe046ad` — *"Record that the freeze reproduces bit-identically"*.
Verified from clean: 13 rows compared, largest difference in any metric `0.00e+00`.

The annotated tag `v1.0-frozen` exists locally but could not be pushed from the environment
this was built in — that environment accepts branch pushes but rejects tag refs. To restore
it from any clone:

```bash
git tag -a v1.0-frozen fe046ad -m "Raysense v1.0 — frozen for SIH26053 idea submission"
git push origin v1.0-frozen
```

**Problem statement:** SIH26053 · DRDO · Software · Smart Automation
