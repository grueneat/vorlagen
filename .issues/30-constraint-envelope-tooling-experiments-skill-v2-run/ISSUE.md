---
id: '30'
title: Encode constraint envelope in experiment tooling + author experiments skill
  (v2 run)
status: in_progress
priority: high
labels:
- enhancement
- templates
- visual-qa
source: github
source_id: 60
source_url: https://github.com/GrueneAT/vorlagen/issues/60
---

## Context

Issue #29 shipped the design-experimentation MVP. The first run (`experiments/falzflyer-p2-mein-plan`, 12 variants) revealed a fundamental methodology gap: variants violated basic design rules — no margins to panel edges, improper spacing, broken hierarchy — because the system never enforced a constraint envelope.

Root cause: `CONTEXT.md` decision #4 said "don't run `BRAND_CONSTRAINTS` on variants — some hypotheses deliberately violate brand rules." That conflated "research artifact" with "free pass on the floor." The correct framing: a hypothesis testing one design axis must respect ALL OTHER design rules — variants vary only on the tested axis, everything else is constraint.

## The three-layer model (correct framework, to be encoded)

1. **Constraint envelope** — fixed floor every variant respects: panel margins, minimum spacing, body text ≥10pt, contrast ≥4.5:1, all Layer-1 deterministic rules from `design-guide/README.md` (21-row table) plus selected `BRAND_CONSTRAINTS`. Non-negotiable.
2. **Variation surface** — the specific design lever the experiment is testing (hierarchy strategy, item count, headline tone, accent strategy). The ONLY thing LLMs and variants vary.
3. **Implementation** — the variant Python builder, expressing the variation within the envelope.

**Rule: the tested axis is the only relaxation; everything else is enforced.**

## Solution scope

### A. New `experiments` skill

Author `.claude/skills/experiments/SKILL.md` using the existing `generate-skill` skill. The skill encodes the process for future experiments:
- `/experiments new <subject>` — scaffold a new experiment directory, generate constraints.yml from design-guide defaults, declare the variation axis being tested.
- `/experiments generate <id>` — run multi-LLM hypothesis generation with envelope threaded into prompt.
- `/experiments render <id>` — render all variants, drop those violating the envelope.
- `/experiments capture <id>` — aggregate results, write SUMMARY.md, prompt corpus update.

The skill captures the three-layer model, the corpus-update merge gate, and v1's lessons (mode collapse, halo effect, position bias, the `BRAND_CONSTRAINTS` framing fix) so future runs follow the corrected methodology by default rather than relying on me remembering it.

### B. Constraint envelope schema and defaults

- `experiments/_schema/constraints.schema.yaml` — JSON Schema Draft 2020-12, mirroring existing repo schema style.
- `experiments/_constraints/falzflyer-default.yml` — default envelope for falzflyer experiments, inheriting from `design-guide/README.md` Layer-1 deterministic rules + selected `BRAND_CONSTRAINTS` (specifically: `brand:logo_size_3M`, `brand:bleed_3mm`, `brand:inside_page`, `brand:text_on_green`, `brand:cover_extent_match`, `brand:band_consistency` — the ones that ARE floor, not the ones an experiment might legitimately test).
- Per-experiment `constraints.yml` can override or extend the default, declaring the one axis being relaxed.

### C. Tooling changes (enforcement in code)

- `tools/experiment_hypothesis_gen.py` loads the envelope, threads it into the multi-LLM prompt as a hard floor with positive AND negative examples ("MUST respect: ≥6mm panel margin, ≥30% negative space, body ≥10pt; MAY vary: hierarchy, density, item count, accent strategy").
- `tools/experiment_generate/prompt_template.md` updated to include envelope + the 12 v1 variants as named "do-not-repeat these specific failure modes" anti-examples (closes the prompt-evolution loop CONTEXT.md decision #6 originally specified).
- `tools/experiment_render.py` gates every variant on the envelope before adding it to the voting bag — variants that violate are dropped with clear log, same pattern as `inside_page` already does today; failed variants are NOT shown to voters.

### D. Documentation corrections

- Reverse the wrong CONTEXT.md decision #4 framing in `design-guide/README.md` so Layer-1 deterministic rules are explicitly named as the constraint envelope for experiments (not just an abstract checklist).
- Update `design-guide/gruene-corpus.md` §6 with the v1 lesson: "first experiment run produced variants violating basic spacing/margins because the constraint envelope wasn't enforced — see `.claude/skills/experiments` for the corrected process."

### E. v2 run (verification gate)

Mirror issue #29's T15 mandatory deliverable: run a v2 experiment (`experiments/falzflyer-p2-mein-plan-v2`) end-to-end. Different from v1: variants this time MUST respect the envelope. Flo votes on the v2 page, results captured into corpus. Without this run, the claim "we fixed it" is unverified. The corpus update IS the merge gate.

## Acceptance Criteria

- [ ] `.claude/skills/experiments/SKILL.md` exists, authored via `generate-skill`, with the three-layer model + commands + v1 lessons documented
- [ ] `experiments/_schema/constraints.schema.yaml` exists and validates with `jsonschema`
- [ ] `experiments/_constraints/falzflyer-default.yml` exists, inherits from `design-guide/README.md` Layer-1 + selected `BRAND_CONSTRAINTS`
- [ ] `tools/experiment_hypothesis_gen.py` consumes envelope and threads it into prompt
- [ ] `tools/experiment_generate/prompt_template.md` includes envelope + v1 anti-examples
- [ ] `tools/experiment_render.py` gates every variant on envelope; failed variants logged and dropped (mirror `inside_page` pattern)
- [ ] `design-guide/README.md` reversed framing committed (Layer-1 rules named as constraint envelope)
- [ ] `experiments/falzflyer-p2-mein-plan-v2/` v2 run rendered end-to-end with ≥10 variants, all respecting envelope, 0 dropped (or all drops logged with reasons)
- [ ] Flo votes a v2 session, results JSON committed
- [ ] `design-guide/gruene-corpus.md` amended with v2 top-3 + bottom-3 with provenance — this closes both issue #29's deferred T15 AND this issue's verification gate

## Out of scope (phase 2)

- Generalising envelope to non-falzflyer templates (one envelope at a time)
- Multi-rater merging
- Hypothesis-prompt evolution beyond using v1 as anti-examples (full prompt evolution is a separate issue)
- Adaptive pair sampling
- Bradley-Terry / Elo ranking

## Dependencies

Issue #29 (merged as PR #59) — provides the experiment system that this issue corrects + extends.

## Rationale (why this is high priority)

The v1 run is unusable as a corpus contribution without this fix — variants violated basic design rules and humans correctly reject them, but the system can't yet tell which design-rule violations are intentional (the tested axis) vs. accidental (lack of envelope). Every future experiment in this workspace depends on the corrected methodology. The skill is the durable carrier — without it, the lesson decays out of memory and the next person (including future-me) reinvents the same mistake.
