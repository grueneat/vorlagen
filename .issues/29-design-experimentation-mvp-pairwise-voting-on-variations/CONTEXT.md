# CONTEXT — Design Decisions

Captured before research/planning. Research and planner MUST follow the locked decisions; the discretion section is open for the planner to refine; deferred items are explicitly out of scope for this issue.

## Decisions (locked — research/planner must follow)

### Architecture

1. **Per-variant Python file.** Each variation lives at `experiments/<exp-id>/variants/<hypothesis-slug>.py`. Self-contained build script that imports shared falzflyer scaffolding (`templates/kandidat-falzflyer-din-lang/build.py` factored as needed) so only P2 differs across variants. Chosen explicitly because the user requires *structurally-different* variations, and parametric/YAML approaches encourage parameter-tweak variations.

2. **Voting UI in existing Astro site.** New route(s) at `site/src/pages/experiments/index.astro` (list of experiments) and `site/src/pages/experiments/[id].astro` (single experiment with all variations + voting modes). Inherits layout/styles from the existing gallery, deploys via the same `astro build` pipeline.

3. **All-pairs randomized-order versus mode.** For N variations, present all N(N-1)/2 pairs in randomized order. Rater can stop anytime; wins-ratio over completed pairs is the ranking. Direct-pick mode is in addition, not instead.

4. **Two-axis voting per pair.** Each pair shown once with two questions answered simultaneously: "which appeals more?" (axis A) and "which transports the information better?" (axis T). Two clicks per pair. Left/right randomized per pair to neutralize position bias.

5. **Variations rendered in situ.** Each variation is a full-page render (the entire DIN-lang front side, P1+P2+P3 with P2 varying), never the panel floating on white. Context changes the verdict.

### Hypothesis generation (most consequential decision)

6. **Pure multi-LLM hypothesis generation, no Flo review at generation stage.** The user explicitly rejected a Flo-review gate at hypothesis time (too much friction per experiment). Instead:

   - **Multiple LLMs generate hypothesis sets independently** for each experiment subject (Opus + at least one other model — Codex/GPT, Gemini, or an external review LLM via the issue:review pipeline). Independent generation diversifies the hypothesis pool and avoids any single model's blind spots.
   - **Prompt design must enforce structural distinctness.** The prompt explicitly forbids parameter-tweak variations and demands hypotheses that differ in commitment, anatomy, typography strategy, or design philosophy — not numeric values. The prompt must include positive and negative examples ("good: cut-to-three-with-body-text; bad: change spacing from 8mm to 12mm").
   - **Hypothesis sets are merged/deduped automatically** — overlapping hypotheses across LLMs collapse to one entry (with attribution to multiple sources, which is a confidence signal).
   - **Flo's first interaction is voting**, not hypothesis selection.
   - **Post-experiment hypothesis review.** After running an experiment, look back at which hypotheses won/lost and feed insights into the hypothesis prompt for future experiments. This is the LLM-prompt evolution loop. Not part of MVP execution but designed in.

7. **MVP experiment subject: falzflyer P2 "Mein Plan" panel.** Already diagnosed in `design-guide/gruene-corpus.md` §6 with named failure mode in §2.1 / §8 ("even-spaced peer list"). Builder code at `templates/kandidat-falzflyer-din-lang/build.py:432–505`.

8. **≥10 variations for MVP** (within the 8–12 range — aim higher to give multi-LLM generation room to surface structurally-distinct ideas).

### Persistence & output

9. **Vote persistence: localStorage during session + explicit JSON export.** Rater can refresh / revisit without losing votes. Export button writes a JSON file; results are downloaded, not server-stored.

10. **Results JSON format includes provenance.** Per result file: rater identity (free text, can be anonymous), session start/end timestamps, per-pair entries (variant-A id, variant-B id, axis voted, winner, position-on-screen, vote timestamp), computed wins-ratio per variant per axis, computed ranking per axis, and a "disagreement index" surfacing pairs where appeal and transport disagreed.

11. **Captured corpus updates from running this MVP experiment is a mandatory deliverable.** The issue ships only when an actual run has fed at least the top-3 winning hypotheses + bottom-3 losing hypotheses back into `design-guide/gruene-corpus.md` with provenance tags. Proves the feedback loop, not just builds the tooling.

## Claude's Discretion (research/planner explores)

- **Ranking algorithm:** simple wins-ratio per axis is the MVP default. Bradley-Terry / Elo deferred to phase-2 unless research surfaces a strong reason to do it sooner.
- **Exact LLM mix for hypothesis generation:** pick from what's available — Opus + (Codex via OpenAI / Gemini / `issue:review` external-LLM tools). Aim for ≥2 independent generators. Document the choice in the manifest.
- **Manifest format:** suggest YAML at `experiments/<exp-id>/manifest.yml` listing experiment metadata (subject, target weak-area, contributing LLMs) + the hypothesis list with attribution. YAML matches existing `meta.yml` and `template-spec.schema.yaml` conventions in the repo.
- **Tooling layout:** likely new `tools/experiment_*.py` (one or more modules: hypothesis generation, variant rendering, results aggregation) and `bin/experiment-*` shell wrappers mirroring existing `bin/render-gallery` patterns.
- **Voting page implementation:** vanilla JS + Astro client island is sufficient — no Svelte/React needed for MVP. Localised CSS via Astro scoped styles.
- **Variant image dimensions:** match the existing gallery preview sizes (page-01.png + page-01-hires.png) used in the falzflyer template — keeps consistency with the rest of the gallery.
- **Optional Flo override:** offer (but do not require) a Flo-can-prune-hypotheses-before-render flow, gated by a CLI flag. Keeps the door open without being the default.

## Deferred (out of scope for this issue — phase 2 / separate issue)

- Multi-rater real-time merging (MVP: each rater exports their own JSON; merging is manual).
- Auto-corpus-update from results (MVP: manual update with rater oversight).
- Generalised generator/manifest for arbitrary regions across templates (MVP hardcoded to falzflyer P2).
- Hosted/shared deployment beyond local Astro dev/build.
- Adaptive pair sampling (Glicko/Elo).
- Hypothesis prompt-evolution automation (the loop is designed in, but iteration happens after MVP runs).
- Bradley-Terry / Elo ranking (deferred unless research finds a reason to bring it forward).
- Image generation via codex/external image models for portrait variations — separate problem; this experiment focuses on layout/typography hypotheses, not portrait swaps.
