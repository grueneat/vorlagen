# Execution Log — Constraint Envelope + Experiments Skill + v2 Run

**Status:** complete (T01–T16 done; T17 pending manual handoff to Flo)
**Branch:** issue/30-constraint-envelope-tooling-experiments-skill-v2-run
**Worktree:** .worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run/
**Started:** 2026-05-10
**Completed:** 2026-05-10
**Scope this run:** T01–T16 (T17 = manual Flo voting + corpus update, deferred)

## Baseline (pre-execution)

- Production falzflyer page-01.png SHA256: `34730f1ef7f1030a696b6751a44636bbdaf7d9a5c17ac3d232ebe29fb8132c24`
  (both `templates/kandidat-falzflyer-din-lang/page-01.png` and
   `site/public/templates/kandidat-falzflyer-din-lang/page-01.png` match)
- All three retained-concept v1 PNGs exist and were visually inspected.

## Tasks

- [x] T01 — add-constraints-schema — `edf9aa5` — Draft 2020-12 schema, 16+22+relax+regeneration enums
- [x] T02 — add-falzflyer-default-envelope — `370ae8d` — 16 brand_rules + 22 layer1 verbatim from design-guide/README.md:24-46
- [x] T03 — implement-experiment-envelope-py — `081a640` — Envelope, EnvelopeValidationError, load/run/format APIs + 7 unit tests
- [x] T04 — bump-manifest-schema — `611d89a` — _dropped[].violations[] structured shape; v1 manifest still validates
- [x] T05 — wire-envelope-into-experiment-render — `65c6a1b` — replace _inside_page_violations w/ _envelope_violations; exit code 7; structured violations in manifest.json::_dropped; docstrings corrected
- [x] T06 — add-v1-anti-examples-file — `5613039` — 12 entries, 3 retained markers, 927 words
- [x] T07 — extend-prompt-template — `4c2f998` — 4 tokens, envelope section, anti-examples section, final-check bullet 6
- [x] T08 — wire-envelope-into-hypothesis-gen — `fa708b9` — render_prompt 4-token; SUBJECT_METADATA v2; _prompt_version hashes anti-examples; 2 new tests
- [x] T09 — surface-drops-and-corpus-stub-in-results — `0183d1f` — Variants-dropped-during-render section + dual-section corpus stub; 3 new tests
- [x] T10 — update-design-guide-docs — `fb2933f` — design-guide/ tracked in repo for first time; envelope paragraph + corpus §6 cross-ref
- [x] T11 — reimplement-numbered-priority-list-v2 — `0417310` — rank-weighted 36/30/24/20/16pt; smoke test passes; merge fix for relax inheritance
- [x] T12 — reimplement-manifesto-single-statement-v2 — `9073185` — uses registered Vollkorn Black Italic; footer dropped; smoke test passes
- [x] T13 — reimplement-dunkelgrun-rules-between-items-v2 — `e405610` — reduced 5→3 rows; ~49% body whitespace; smoke test passes
- [x] T14 — author-experiments-skill — `0df9702` — .claude/skills/experiments/SKILL.md, 1310 words, validate.sh passes
- [x] T15 — generate-v2-hypotheses — `7662875` — 19 LLM (claude+codex) + 3 retained = 22 hypotheses; manifest validates
- [x] T16 — render-v2-variants-end-to-end — `5544e4c`, `5527405` — 3 retained rendered; 19 LLM-only dropped (no variant code); Astro build passes; production byte-stable
- [ ] T17 — Pending: manual handoff to Flo for voting and dual-section corpus update (closes both #30 and #29 T15)

## Verification status

- All Python unit/integration tests: **PASS** — 853 tests run, 0 failures, 11 skipped (pre-existing skips)
- `npm --prefix site run build`: **PASS** — 12 pages built including v2 voting page
- v2 hypothesis manifest generated (T15): **PASS — 22 hypotheses, manifest validates against schema**
- v2 variants rendered (T16): **PARTIAL — 3 retained rendered, 19 LLM-only dropped (no variant code; see Architectural Finding)**
- Production falzflyer page-01.png byte-stable: **PASS** — SHA256 unchanged
- `.claude/skills/experiments/SKILL.md` exists + validates (wc -w ≤ 5000): **PASS — 1310 words**
- ruff/mypy on new code: **PASS** — `tools/experiment_*.py`, all v2 variants, all new tests clean

## Three retained concepts — visual checks

- **numbered-priority-list (v1)**: PNG inspected → constant 28pt numerals, no rank scaling. v2 corrected by 36/30/24/20/16pt geometric series. v2 renders within envelope (smoke test pass + Scribus PNG generated).
- **manifesto-single-statement (v1)**: PNG inspected → renders, but specifies `Vollkorn Black` (NOT in `shared/ci.yml::fonts` — only `Vollkorn Black Italic` registered). v2 corrected by switching to the registered face + dropping the v1 footer. v2 renders within envelope.
- **asymmetric-editorial-rules (v1)** → **dunkelgrun-rules-between-items-v2**: PNG inspected → 5 rows × 22mm = 110mm packed into 130mm, ~15% whitespace. v2 corrected by reducing to 3 rows (~49% body-area whitespace). v2 renders within envelope.

## Architectural finding (Rule 4 deviation surfaced for Flo)

**Variant codegen is missing from #29's tooling.** `bin/experiment-generate` produces hypothesis manifest entries with a `builder: variants/<slug>.py` field but does NOT create the .py files. T16 dropped 19 LLM-produced hypotheses with `build error: variant builder not found`. Drop rate 86% (19/22), well above the 40% threshold; per PLAN.md R5 + the executor instructions, HALT and surface to Flo without auto-retry.

Two path-forward options for getting to ≥10 rendered variants:
1. **Author 7+ variant Python modules manually** for the most-promising LLM hypotheses (e.g. `two-tier-privileged-item`, `eyebrow-plus-body-three`, `vollkorn-italic-cornerstone-jump`, `cornerstone-banner-with-minors`, `accent-chip-and-open-field`, `ranked-numerals-scale-list`, `editorial-left-column-rules`).
2. **Build a `bin/experiment-codegen`** step that turns hypothesis descriptions into render_p2 stubs for hand-tuning (a separate issue scope-wise).

Either path is needed BEFORE T17's voting can be a meaningful merge gate — voting on only 3 variants doesn't cover the density+form axis adequately.

## Other deviations from plan (auto-fixed Rule 1-3)

- **[Rule 2 - Production-mirror relaxations]** `experiments/_constraints/falzflyer-default.yml` now relaxes 5 rules instead of `relax: []`. Three are inherited from `templates/kandidat-falzflyer-din-lang/meta.yml::brand_overrides` (`brand:line_spacing_0.9`, `brand:image_text_overlap`, `brand:band_consistency`). Two are Layer-1 heuristic-imprecision relaxations (`layer1:negative_space_pct`, `layer1:body_line_length_chars`) the production scaffold's tall body frame would otherwise trip. Without these, the production scaffold itself fails the envelope and every variant trips on production-side issues.
- **[Rule 1 - Merge semantics]** `_shallow_merge` in `experiment_envelope.py` was changed: `relax` entries from child are now APPENDED to parent's (was: child's list replaced parent's). Without this fix, every per-experiment `constraints.yml` would lose the production-mirror relaxations.
- **[Rule 4 - design-guide tracking]** `design-guide/` lives at `/root/workspace/design-guide/` (workspace-level), NOT inside the worktree. Per the worktree-scope hard rule, copied into the worktree as a tracked addition before applying T10's edits. This is the first time design-guide is in the repo; future merges to main move it there permanently.
- **[Rule 1 - Layer-1 P2 scoping]** `_check_body_min_pt`, `_check_caption_impressum_min_pt`, `_check_body_line_length_chars` now scope to anname starting `"P2 "` (the experiment panel under test) so back-panel production-side text doesn't trip experiment gates.
- **[Rule 1 - Constraints.yml tested-axis relaxations]** `experiments/falzflyer-p2-mein-plan-v2/constraints.yml` relaxes `layer1:type_sizes_per_panel` and `layer1:type_families_per_panel` because v2's tested axis (density+form) requires multi-size scales (the rank-weighted 36/30/24/20/16 series in numbered-priority-list-v2 alone is 5 distinct sizes).

## Discovered issues (out of scope, logged for follow-up)

- **`_check_negative_space_pct` is frame-area-based, not ink-area-based.** Production scaffold's body frame is h=130mm but actual text ink occupies far less. The metric over-counts content area. Genuinely measuring optical whitespace would require rasterised analysis. Relaxed in falzflyer-default; future improvement: per-frame ink-area estimation from fontsize × line count.
- **`bin/experiment-generate` doesn't write variant code.** See Architectural Finding above. This is the principal gap blocking ≥10 variants.
- **Existing `tools/sla_lib/tests/test_experiment_render.py` had two tests that needed `constraints.yml` scaffolding.** Updated; not a regression — they now correctly exercise the new envelope-loading path.

## Handoff to user (T17)

The runbook for Flo to close this issue:

1. Address the Architectural Finding above. Either:
   - **Option A (recommended for v2-as-shipped):** Author 7+ variant Python modules under `experiments/falzflyer-p2-mein-plan-v2/variants/<slug>.py` for the most-promising LLM hypotheses. Each must export `def render_p2(doc, page) -> None:` (see existing 3 retained-concept variants and the experiment_envelope's smoke tests as templates). Verify each smoke-test passes the envelope before voting.
   - **Option B (cleaner for the methodology):** Open a follow-up issue scoping `bin/experiment-codegen` (LLM-driven hypothesis-to-variant scaffolding); for v2-as-shipped, hand-author enough variants to get to ≥10 rendered.

2. After ≥10 variants render cleanly: run `bin/experiment-render falzflyer-p2-mein-plan-v2` once more to refresh `manifest.json::_dropped` and `site/public/experiments/falzflyer-p2-mein-plan-v2/`.

3. Open the Astro voting page: `npm --prefix site run dev` then `http://localhost:4321/experiments/falzflyer-p2-mein-plan-v2/`.

4. Read the SUMMARY.md stub (after step 6 below) BEFORE voting — verify the variant set is density+form-balanced (check the `axis_commitments` column in `manifest.yml`).

5. Run a complete pairwise voting session. Aim for full coverage of all C(N, 2) pairs (with N≈12, that's 66 pairs × 2 axes = 132 votes).

6. Export results JSON via the Astro page's "Export" button to `experiments/falzflyer-p2-mein-plan-v2/results/flo-2026-05-XX.json`.

7. Run `bin/experiment-results falzflyer-p2-mein-plan-v2` to aggregate into `experiments/falzflyer-p2-mein-plan-v2/results/SUMMARY.md`. The SUMMARY now carries:
   - `## Variants dropped during render` (auto-populated from `manifest.json::_dropped`)
   - `## Corpus update stub` with two pre-labelled subsections: `### From v1 (envelope necessity)` and `### From v2 (density+form findings)`.

8. Amend `design-guide/gruene-corpus.md` with the dual-section corpus update:
   - **Part 1 (closes #29 T15):** v1 meta-lesson on envelope necessity. Verbatim text already drafted in SUMMARY.md's corpus stub.
   - **Part 2 (closes #30 substantively):** v2 density+form findings. Top-3 by win-rate, bottom-3 by loss-rate, Spearman halo flag if applicable. Provenance: link to `experiments/falzflyer-p2-mein-plan-v2/results/flo-<DATE>.json` and the SUMMARY.md.

9. Commit the results JSON + amended corpus + any new variant Python modules from step 1 as a single commit:
   `30+29: docs(corpus): close envelope-necessity + v2 density+form findings`

10. Run the final acceptance-gate verification (PLAN.md `<verification>` block):
    ```bash
    python3 -m unittest discover tools/sla_lib/tests
    npm --prefix site run build
    bash /root/.claude/skills/generate-skill/scripts/validate.sh .claude/skills/experiments/
    grep -q "ARE the constraint envelope for design experiments" design-guide/README.md
    ! grep -q "no other brand rule runs on variants" tools/experiment_render.py
    ```

11. Open PR. PR description should reference closing both issues — body should say `Closes #30. Closes #29 (T15 carry-over).`
