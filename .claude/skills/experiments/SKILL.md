---
name: experiments
description: |
  Run constraint-envelope design experiments with rank-mode voting (click-to-rank).
  MUST BE USED when the user invokes `/experiments <verb>` where <verb> in
  {new, generate, render, capture}, or when the user mentions design experimentation,
  hypothesis voting, variant rendering, or amending the corpus with experiment findings.
  Encodes the three-layer model (envelope / variation surface / implementation), the
  four-subcommand dispatch, v1's failure-mode lessons, and the corpus-update merge gate.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
argument-hint: "[new|generate|render|capture] <experiment-id>"
---

# experiments — constraint-envelope design experimentation

This skill runs design experiments on Grüne NÖ print collateral. Each experiment varies
ONE design axis (density, hierarchy, typography, asymmetry, …) while every other rule
remains constraint. Variants violating the envelope are dropped, not voted on. Findings
amend `design-guide/gruene-corpus.md` with provenance.

## When invoked as `/experiments <verb>`

Branch on the first positional argument:

| `$1`       | Section to execute |
|------------|--------------------|
| `new`      | `## new` — scaffold a new experiment |
| `generate` | `## generate` — multi-LLM hypothesis generation |
| `render`   | `## render` — envelope-gated rendering |
| `capture`  | `## capture` — aggregate voting results + corpus stub |

If `$1` is missing or unrecognised, print the usage hint and exit. If `$2` (experiment-id)
is missing for `generate`/`render`/`capture`, ask the user once for the id and proceed.

## The three-layer model

Every experiment has three layers. To understand a hypothesis, identify each layer:

1. **Envelope** — the floor every variant respects. 16 BRAND_CONSTRAINTS + 22 Layer-1
   thresholds (margins, body sizes, contrast, type families, alignment systems, …).
   Declared in `experiments/<id>/constraints.yml`, inheriting
   `experiments/_constraints/falzflyer-default.yml`.
2. **Variation surface** — the single axis the experiment varies. Declared as
   `tested_axis:` in `constraints.yml` (e.g. `density+form`). Hypotheses commit to
   different positions on this axis.
3. **Implementation** — the per-variant Python module under
   `experiments/<id>/variants/<slug>.py` exposing `render_p2(doc, page) -> None`.

The envelope is enforced at render-time on the built Document, NOT trusted from the
variant module's self-report (see `tools/experiment_envelope.py::run_envelope`).

## Voting mode (primary)

The site exposes **rank** as the **primary** voting mode and **direct-pick** as a
secondary fallback. Click-to-rank is the design default — voters click a dedicated
checkmark control on each variant card to add it to an ordered list rendered below
the grid; the ranked list reorders via ▲/▼ arrow buttons (accessible primary path)
and SortableJS drag-drop (tactile secondary). Image-click opens the existing lightbox
and never collides with the checkmark (the checkmark is a sibling button to the `<img>`,
so click bubbling can't reach the lightbox listener).

Rank mode is the default when the manifest has ≥3 variants; direct-pick is the
fallback for <3 variants where ranking adds no signal. Mode is switchable per session
via the toolbar.

**Breaking schema change.** v1 result files are no longer processable. The schema
bump is intentional; no migration tool ships. The aggregator
(`tools/experiment_results.py`) rejects unknown modes at validate-time.

## new

To scaffold a new experiment, do:

1. Validate `$2` is kebab-case and not already a directory under `experiments/`.
2. Create `experiments/<id>/{variants/}`.
3. Write `experiments/<id>/constraints.yml`:
   ```yaml
   extends: ../_constraints/falzflyer-default.yml
   tested_axis: "<ASK USER: density / hierarchy / typography / asymmetry / …>"
   relax: []
   regeneration:
     auto_retry_max: 0
     drop_threshold_pct: 40
   ```
4. Ask the user for the `tested_axis` value and substitute it before writing.
5. Print the path to the new directory and the next command (`/experiments generate <id>`).

Pre-flight: verify `experiments/_constraints/falzflyer-default.yml` exists and
`tools/experiment_envelope.py` imports cleanly (`python3 -c "import experiment_envelope"`).
If either fails, halt and surface — do not attempt to repair from the skill.

## generate

To generate hypotheses, do:

1. Verify `experiments/<id>/constraints.yml` exists; if not, run `/experiments new` first
   (or instruct the user to).
2. Verify `tested_axis` is not the placeholder `"default"`.
3. Run `bin/experiment-generate <id>`. The generator threads the envelope and the v1
   anti-examples into the prompt automatically; you do not need to pass them.
4. After completion, read `experiments/<id>/manifest.yml`. Assert:
   - `hypotheses` length ≥ 10 (schema floor)
   - exactly one entry has `wildcard: true`
   - no two slugs share an `axis_commitments` Jaccard ≥ 0.6 (the generator warns; surface)
5. If a retained-concept set was specified (e.g. v2's three retained-from-v1), splice
   them into the manifest now with `source: "retained-from-v1"`. The LLMs will not
   re-emit them because the anti-examples warn against the broken implementations; the
   re-implemented variants exist as Python modules but need manifest entries.

## render

To render all variants, do:

1. Verify brand fonts present: `fc-list | grep -i gruene | wc -l` returns ≥ 30.
2. Run `bin/experiment-render <id>`. The render pipeline:
   - Loads the envelope once from `<id>/constraints.yml`.
   - For each variant: builds via `variant_scaffold.build_variant_front`, runs
     `run_envelope(doc, envelope)`, drops on any error-severity violation with structured
     `{rule_id, message, severity, targets}` entries in `manifest.json::_dropped`.
   - Variants that pass: SLA → PDF (Scribus + xvfb-run) → PNG @100dpi + @150dpi → mirror
     to `site/public/experiments/<id>/<slug>/`.
3. Read `manifest.json::_dropped`. If drop rate > `regeneration.drop_threshold_pct`
   (default 40), STOP and surface to the user. Do not auto-retry; v2 ships with
   `auto_retry_max: 0` per the merge-gate transparency requirement.
4. Run `npm --prefix site run build` to verify the Astro voting page integrates.
5. Print the voting URL (`http://localhost:4321/experiments/<id>/` once `npm run dev`
   is running).

Render-gate trust model: the gate validates the rendered Document, NOT the variant
module's self-report. A variant cannot disable a check by claiming compliance — only
the rendered artefact decides.

## capture

To aggregate a voting session, do:

1. Verify the user has voted: `experiments/<id>/results/*.json` exists. Each results
   file MUST validate against `experiments/_schema/results.schema.yaml` and carry one
   of the two modes:
   - **rank** — ordered slug list (`"mode": "rank"`, `"ranking": ["slug1", ...]`).
   - **direct-pick** — unordered selection set (`"mode": "direct-pick"`, `"selections": [...]`).
2. Run `bin/experiment-results <id>`. This writes
   `experiments/<id>/results/SUMMARY.md` with:
   - Top-3 / Bottom-3 by mean linear Borda position score across raters.
   - Per-slug score + rater count.
   - `## Variants dropped during render` block (rendered from `manifest.json::_dropped`).
   - `## Corpus update stub` with two pre-labelled subsections:
     `### From v1 (envelope necessity)` and `### From v2 (density+form findings)`.
3. Display the corpus stub to the user and prompt them to amend
   `design-guide/gruene-corpus.md` with both sections. The dual structure is the merge
   gate: every experiment closes BOTH a methodology lesson AND a substantive finding.
4. Once the user confirms the corpus is updated, prompt them to commit the results JSON
   + the amended corpus together: `<issue-id>: docs(corpus): close <experiment-name>`.

### Results JSON shape (rank, primary)

```json
{
  "experiment_id": "falzflyer-p2-mein-plan-v2",
  "rater": "flo",
  "started_at": "2026-05-11T12:00:00Z",
  "exported_at": "2026-05-11T12:18:00Z",
  "mode": "rank",
  "ranking": ["numbered-priority-list-v2", "manifesto-single-statement-v2", "..."]
}
```

Direct-pick uses `"mode": "direct-pick"` and `"selections": [...]` instead of `ranking`.
The schema rejects files carrying both fields and files with unknown mode values.

### Aggregation math

Linear Borda position score, normalised: for a ranking of length `N`, the slug at
0-based rank `i` gets `(N - 1 - i) / (N - 1)`. Top-ranked → 1.0, bottom → 0.0. Slugs
no rater placed remain `None` (excluded, not zero). Direct-pick fallback assigns 1.0
to each selected slug and `None` otherwise. Multi-rater aggregation takes the mean of
the non-None per-slug scores; the SUMMARY surfaces top-3 and bottom-3 by mean.

## v1 lessons (the durable carriers)

- **Envelope conflation.** v1 enforced only `brand:inside_page`, missed the other 15
  brand rules + 22 Layer-1 thresholds. Every v1 variant violated the envelope. Fixed:
  `tools/experiment_envelope.py::run_envelope` enforces all of them, gate-loaded once
  per render.
- **Mode collapse.** Multi-LLM dedup via Jaccard ≥ 0.6 on `axis_commitments`
  (`experiment_hypothesis_gen.py:50`). Mitigation: one mandatory wildcard hypothesis
  per generation.
- **Halo effect.** Voters tend to rank by overall polish, not the tested axis.
  Mitigation: every hypothesis declares `axis_commitments`; SUMMARY.md surfaces
  axis-balance before voting is considered actionable. The rank-mode UI shows axis
  commitments on each card so the rater can sanity-check what they're ranking on.
- **Position bias.** Voters favour the first-presented variant. Mitigation: rank-mode
  variant grid renders in manifest order; we accept this as a stable presentation
  (post-hoc analysis can look for first-position bias if needed).
- **Why all 16 BRAND_CONSTRAINTS are floor by default.** The variation surface tests
  ONE axis; everything else is constraint. Relaxations MUST be explicit in
  `constraints.yml::relax` with a one-line rationale. Implicit relaxations are
  forbidden — they are how v1 happened.
- **Anti-examples format.** v1 anti-examples are `slug + violation + rule-id` triples,
  not bare negations. NeQA research: negation-only prompts degrade at scale. See
  `tools/experiment_generate/v1_anti_examples.md`.

## Corpus-update merge gate

No experiment merges without:
1. A complete Flo voting session (`experiments/<id>/results/flo-<DATE>.json`) in rank
   mode (or direct-pick for <3-variant runs).
2. A dual-section corpus amendment in `design-guide/gruene-corpus.md`:
   - **Part 1** — methodology lesson (e.g. "envelope necessity", "rank-mode adoption
     and what it changed", "axis-commitment dedup").
   - **Part 2** — substantive findings on the tested axis (top-3 / bottom-3 with
     provenance: experiment id + results JSON path + SUMMARY.md path).

This pairing is the durable cross-experiment learning loop. A finding without a
methodology lesson is anecdotal; a methodology lesson without a finding is theory.

## Pre-flight checks per verb

| Verb       | Required preconditions |
|------------|------------------------|
| `new`      | `experiments/_constraints/falzflyer-default.yml` exists; `tools/experiment_envelope.py` importable; `<id>` not already used |
| `generate` | `experiments/<id>/constraints.yml` exists; `tested_axis` not the default placeholder; ≥ 2 LLMs on PATH (`claude`/`codex`/`gemini`) |
| `render`   | brand fonts on PATH (`fc-list | grep -i gruene` ≥ 30); `experiments/<id>/manifest.yml` exists and validates |
| `capture`  | `experiments/<id>/results/*.json` exists with at least one rater session; each file validates against `experiments/_schema/results.schema.yaml` |

Halt loudly on any precondition failure. Do NOT attempt to repair from the skill —
surface the missing piece to the user so the failure mode is visible.

## Out of scope

The following are explicit non-features:

- Generalising the envelope to non-falzflyer templates (zeitung, poster, postkarte) —
  follow-up issues, one per template.
- Multi-rater real-time merging — Flo is the single rater for v2.
- Auto-corpus-update from results — corpus amendment stays manual; the skill prompts
  the user with the stub but writes nothing without confirmation.
- Hypothesis-prompt evolution beyond v1 anti-examples — separate issue once ≥ 2
  experiments have run.
- Adaptive pair sampling, Bradley-Terry / Elo, or Glicko ranking — out of scope.
- Reviving v1's two-axis (appeal + transport) inside rank mode — out of scope.
- Migrating v1 result files to the rank schema — out of scope; no migration tool ships.
- Touching `bin/experiment-*` entry-point scripts — they already work; this skill
  dispatches to them.
