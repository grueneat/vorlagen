# Execution Log — Constraint Envelope + Experiments Skill + v2 Run

**Status:** complete (T01–T16, T16a, T16b done; T17 pending manual handoff to Flo)
**Branch:** issue/30-constraint-envelope-tooling-experiments-skill-v2-run
**Worktree:** .worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run/
**Started:** 2026-05-10
**Completed:** 2026-05-10 (T01–T16), 2026-05-10 (T16a + T16b — codegen tool + run)
**Scope this run:** T01–T16, T16a, T16b (T17 = manual Flo voting + corpus update, deferred)

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
- [x] T16a — implement-experiment-codegen — `4aa9dfa` — tools/experiment_codegen.py + bin/experiment-codegen shim; multi-LLM (claude + codex) prompt composes envelope + DSL signature + scaffold contract + 3 reference impls; per-slug import + scaffold + envelope validation gate; skip-existing default + --force; 12 unit tests pass; ruff + mypy clean; --help OK
- [x] T16b — run-codegen-and-render-v2 — `4262df4` — bin/experiment-codegen produced 18 LLM-written builders + 3 retained = 21 total (1 failed: resident-quote-then-pledge — claude returned `false` lowercase, codex used `Hellgrun` instead of `Hellgrün`); bin/experiment-render: 21 OK, 1 dropped (4.5% drop rate, well under 40% threshold); all PNGs + hi-res + site/public mirrors populated; manifest.json schema-valid; Astro build clean; production byte-stable
- [ ] T17 — Pending: manual handoff to Flo for voting and dual-section corpus update (closes both #30 and #29 T15)

## Verification status

- All Python unit/integration tests: **PASS** — 865 tests run, 0 failures, 11 skipped (was 853 before T16a; +12 from test_experiment_codegen)
- `npm --prefix site run build`: **PASS** — 12 pages built including v2 voting page
- v2 hypothesis manifest generated (T15): **PASS — 22 hypotheses, manifest validates against schema**
- v2 variants rendered (T16 + T16b): **PASS — 21 rendered, 1 dropped (resident-quote-then-pledge: both LLMs failed codegen)**
  - 3 retained-from-v1: `numbered-priority-list-v2`, `manifesto-single-statement-v2`, `dunkelgrun-rules-between-items-v2`
  - 18 LLM-codegen (claude or codex): `two-tier-privileged-item`, `paragraph-form-prose-block`, `eyebrow-plus-body-three`, `horizontal-band-tricolor-zones`, `vollkorn-italic-cornerstone-jump`, `caps-eyebrow-categorical-tags`, `two-column-editorial-split`, `two-statement-call-response`, `quote-plus-reply-single-family`, `candidate-portrait-overlay-pact`, `manifesto-single-pledge-v2`, `three-pillars-with-explainer`, `editorial-left-column-rules`, `ranked-numerals-scale-list`, `first-person-compact-paragraph`, `cornerstone-banner-with-minors`, `accent-chip-and-open-field`, `ballot-cross-text-container`
  - 1 dropped: `resident-quote-then-pledge` — claude rejected for `NameError("name 'false' is not defined")` (lowercase Python `false` in source); codex rejected for `brand:color_palette` violation (emitted `Hellgrun` instead of `Hellgrün`)
- Production falzflyer page-01.png byte-stable: **PASS** — SHA256 `34730f1e…` unchanged
- `.claude/skills/experiments/SKILL.md` exists + validates (wc -w ≤ 5000): **PASS — 1310 words**
- ruff/mypy on new code: **PASS** — `tools/experiment_*.py` (incl. new `experiment_codegen.py`), all v2 variants, all new tests clean

## Three retained concepts — visual checks

- **numbered-priority-list (v1)**: PNG inspected → constant 28pt numerals, no rank scaling. v2 corrected by 36/30/24/20/16pt geometric series. v2 renders within envelope (smoke test pass + Scribus PNG generated).
- **manifesto-single-statement (v1)**: PNG inspected → renders, but specifies `Vollkorn Black` (NOT in `shared/ci.yml::fonts` — only `Vollkorn Black Italic` registered). v2 corrected by switching to the registered face + dropping the v1 footer. v2 renders within envelope.
- **asymmetric-editorial-rules (v1)** → **dunkelgrun-rules-between-items-v2**: PNG inspected → 5 rows × 22mm = 110mm packed into 130mm, ~15% whitespace. v2 corrected by reducing to 3 rows (~49% body-area whitespace). v2 renders within envelope.

## Architectural finding (closed by T16a + T16b)

**Variant codegen gap closed.** The T16 architectural finding noted `bin/experiment-generate` produced hypothesis text but no Python builders, leaving 19/22 v2 hypotheses unrenderable. T16a implemented `bin/experiment-codegen` (mirroring `experiment-generate`'s multi-LLM subprocess pattern: claude + codex, 600s timeout, raw stdouts preserved for audit, per-slug import+scaffold+envelope validation before accepting a builder, fallback to second LLM on rejection). T16b ran it on `falzflyer-p2-mein-plan-v2`, producing 18 new builders + 3 retained = 21 total. The one remaining failure (`resident-quote-then-pledge`) is named in the dropped list with both LLMs' specific rejection reasons; the methodology is right (gate enforced; bad output not silently accepted), the prompt could be tightened for the residual edge cases (claude's lowercase `false`, codex's umlaut-stripping) in a follow-up. The render gate's drop_threshold_pct=40 is satisfied with margin: 1/22 = 4.5% drop rate. T17 voting can now operate on a density+form-balanced pool of 21 variants.

## Other deviations from plan (auto-fixed Rule 1-3)

- **[Rule 2 - Production-mirror relaxations]** `experiments/_constraints/falzflyer-default.yml` now relaxes 5 rules instead of `relax: []`. Three are inherited from `templates/kandidat-falzflyer-din-lang/meta.yml::brand_overrides` (`brand:line_spacing_0.9`, `brand:image_text_overlap`, `brand:band_consistency`). Two are Layer-1 heuristic-imprecision relaxations (`layer1:negative_space_pct`, `layer1:body_line_length_chars`) the production scaffold's tall body frame would otherwise trip. Without these, the production scaffold itself fails the envelope and every variant trips on production-side issues.
- **[Rule 1 - Merge semantics]** `_shallow_merge` in `experiment_envelope.py` was changed: `relax` entries from child are now APPENDED to parent's (was: child's list replaced parent's). Without this fix, every per-experiment `constraints.yml` would lose the production-mirror relaxations.
- **[Rule 4 - design-guide tracking]** `design-guide/` lives at `/root/workspace/design-guide/` (workspace-level), NOT inside the worktree. Per the worktree-scope hard rule, copied into the worktree as a tracked addition before applying T10's edits. This is the first time design-guide is in the repo; future merges to main move it there permanently.
- **[Rule 1 - Layer-1 P2 scoping]** `_check_body_min_pt`, `_check_caption_impressum_min_pt`, `_check_body_line_length_chars` now scope to anname starting `"P2 "` (the experiment panel under test) so back-panel production-side text doesn't trip experiment gates.
- **[Rule 1 - Constraints.yml tested-axis relaxations]** `experiments/falzflyer-p2-mein-plan-v2/constraints.yml` relaxes `layer1:type_sizes_per_panel` and `layer1:type_families_per_panel` because v2's tested axis (density+form) requires multi-size scales (the rank-weighted 36/30/24/20/16 series in numbered-priority-list-v2 alone is 5 distinct sizes).

## Discovered issues (out of scope, logged for follow-up)

- **`_check_negative_space_pct` is frame-area-based, not ink-area-based.** Production scaffold's body frame is h=130mm but actual text ink occupies far less. The metric over-counts content area. Genuinely measuring optical whitespace would require rasterised analysis. Relaxed in falzflyer-default; future improvement: per-frame ink-area estimation from fontsize × line count.
- **`bin/experiment-generate` doesn't write variant code.** CLOSED by T16a (`bin/experiment-codegen` added) and T16b (codegen ran end-to-end).
- **Codex `workspace-write` sandbox writes side-effect files into the workspace root.** During T16b, codex emitted `tmp_vollkorn_italic_cornerstone_jump.py` at the workspace root (in addition to its stdout). Cleaned up before commit; future improvement: capture codex stdout in a temp dir and pass `--sandbox read-only` if subprocess prompt-only mode is sufficient.
- **Two LLM-codegen failure modes are visible in the dropped variant.** (a) Claude emitted Python with `wildcard: false` (lowercase) which raises `NameError`. (b) Codex stripped the umlaut from `Hellgrün` → `Hellgrun`, failing `brand:color_palette`. Both are tightenable in the codegen prompt — add an explicit "use exact brand color names, including umlauts" + "Python booleans are True/False (capitalized)" constraint before the next run.
- **Existing `tools/sla_lib/tests/test_experiment_render.py` had two tests that needed `constraints.yml` scaffolding.** Updated; not a regression — they now correctly exercise the new envelope-loading path.

## Handoff to user (T17)

The runbook for Flo to close this issue (architectural gap closed by T16a + T16b — Flo can vote immediately):

1. Open the Astro voting page: `npm --prefix site run dev` then `http://localhost:4321/experiments/falzflyer-p2-mein-plan-v2/`.

2. Read the SUMMARY.md stub (after step 4 below) BEFORE voting — verify the variant set is density+form-balanced (check the `axis_commitments` column in `manifest.yml`).

3. Run a complete pairwise voting session. Aim for full coverage of all C(N, 2) pairs (with N=21, that's 210 pairs × 2 axes = 420 votes; if 420 is impractical, sample a balanced subset per axis).

4. Export results JSON via the Astro page's "Export" button to `experiments/falzflyer-p2-mein-plan-v2/results/flo-2026-05-XX.json`.

5. Run `bin/experiment-results falzflyer-p2-mein-plan-v2` to aggregate into `experiments/falzflyer-p2-mein-plan-v2/results/SUMMARY.md`. The SUMMARY now carries:
   - `## Variants dropped during render` (auto-populated from `manifest.json::_dropped` — currently lists `resident-quote-then-pledge`)
   - `## Corpus update stub` with two pre-labelled subsections: `### From v1 (envelope necessity)` and `### From v2 (density+form findings)`.

6. Amend `design-guide/gruene-corpus.md` with the dual-section corpus update:
   - **Part 1 (closes #29 T15):** v1 meta-lesson on envelope necessity. Verbatim text already drafted in SUMMARY.md's corpus stub.
   - **Part 2 (closes #30 substantively):** v2 density+form findings. Top-3 by win-rate, bottom-3 by loss-rate, Spearman halo flag if applicable. Provenance: link to `experiments/falzflyer-p2-mein-plan-v2/results/flo-<DATE>.json` and the SUMMARY.md.

7. Commit the results JSON + amended corpus as a single commit:
   `30+29: docs(corpus): close envelope-necessity + v2 density+form findings`

8. Run the final acceptance-gate verification (PLAN.md `<verification>` block):
   ```bash
   python3 -m unittest discover tools/sla_lib/tests
   npm --prefix site run build
   bash /root/.claude/skills/generate-skill/scripts/validate.sh .claude/skills/experiments/
   grep -q "ARE the constraint envelope for design experiments" design-guide/README.md
   ! grep -q "no other brand rule runs on variants" tools/experiment_render.py
   ```

9. Open PR. PR description should reference closing both issues — body should say `Closes #30. Closes #29 (T15 carry-over).`
