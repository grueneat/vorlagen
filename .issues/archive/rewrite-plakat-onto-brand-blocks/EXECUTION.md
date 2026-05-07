# Execution — Rewrite Plakat A1 onto Brand + blocks

**Issue:** rewrite-plakat-onto-brand-blocks (id 7)
**Status:** complete
**Executed:** 2026-05-07

## Tasks

- [x] Task 1: Extend --allow-brand-extras to filter extra-color warnings for brand colors — commit e92213c
- [x] Task 2: Regenerate templates/plakat-a1-hochformat/build.py via converter (zero hand edits) — commit 8aaaa66
- [x] Task 3: Update PlakatRoundTrip test allowlist to filter brand-additive warnings — commit 048261e
- [x] Task 4: Rebuild gallery, run full validation pipeline, regenerate previews_for_sla SHA — commit 7387ffe
- [x] Task 5: Acceptance check + write EXECUTION.md

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | visual_diff clean vs baseline.pdf | PASS | `python3 tools/visual_diff.py ... --dpi 96` → exit 0; max pixel mismatch ~0% (byte-clean against committed baseline) |
| 2 | pytest tools/sla_lib/tests -x | PASS | 251 passed, 0 failed, 3 deprecation warnings (pre-existing) |
| 3 | bin/validate --ci | PASS | plakat sla_diff: PASS, visual_diff: PASS; postkarte sla_diff: PASS, visual_diff: PASS; zeitung sla_diff: PASS, visual_diff: PASS |
| 4 | check_ci.py plakat template | PASS | exit 0; 4 local-style warnings (template-local German names, expected and non-blocking) |
| 5 | extra_doc_attrs <= 23 keys | PASS | exactly 23 keys (target met exactly) |
| 6 | extra_pdf_attrs <= 11 keys | PASS | exactly 11 keys (target met exactly) |

Informational (LOC target dropped per user direction):
- LOC: 235 → 198 (target was ≤ 180; achieved 198; informational only per user direction)

## Metrics

- LOC: 235 → 198 (-37; informational, not an AC)
- extra_doc_attrs: 113 → 23 (-90 keys)
- extra_pdf_attrs: 44 → 11 (-33 keys)
- Block substitutions: 0 (Plakat has 0 Polygons / 0 chains / 0 pgno / 0 contact frames; 1 Impressum frame stays primitive due to two API gaps — rotation_deg + Bold-prefix Run)
- Brand uptake: brand=Brand.gruene_noe() emitted, palette_replaces_ci removed, layers default to Brand stack (no explicit DocumentLayer)
- sla_diff allowlist: --allow-brand-extras now additionally filters brand extra-color warnings (new in this issue; needed because Plakat original carried only 5/7 brand colors)
- previews_for_sla SHA: cff461714e044eb343b7593bf7b0de2d40a5bb38a458d62db80359748902a3b4 → 5c9a04ed876a8bdfad9ed7bb1851fbe4e39fd6119db1469f18b06f1c07bad48c

## P2 follow-ups (file as future issues, do NOT implement here)

1. **Widen `Impressum` block to support `rotation_deg=` kwarg.** Plakat carries a vertical (rotation_deg=270) Impressum at the right margin. The modern block at `tools/sla_lib/builder/blocks.py:89-124` has no rotation_deg surface. Combined with gap #2 below, this blocks Impressum block substitution for Plakat.

2. **Widen `Impressum` block to support Bold-prefix Run idiom (`prefix_text=`, `prefix_font=`).** Plakat (and Postkarte) carry a Bold "Impressum:" prefix Run before the Book body. The modern block emits a single Run from `text=`. This is the same gap Postkarte EXECUTION.md filed as P2 follow-up #1; reaffirmed here for the second time. Combined widening: add `prefix_text=`, `prefix_font=`, AND `rotation_deg=` kwargs to `Impressum`.

3. **(Optional, P3 hygiene) Add `PlakatConverterFreshRun` test class** to mirror `PostkarteConverterFreshRun` at `tools/sla_lib/tests/test_sla_to_dsl.py:81`. Plakat is currently covered only by the round-trip test, not by the from-scratch convert-and-check guard. Low priority.

4. **(Optional, P3) Audit `extra_pdf_attrs` and `extra_doc_attrs` for further hoist candidates** once Zeitung migrates (issue #8). Plakat's 23/11 residual is at exact AC parity; Zeitung may surface more constants.

## Notes

- Plakat is the smallest of the three migrations: zero block substitutions, zero hand edits to the regenerated build.py, zero ci-defaults hoists. The whole issue value is (a) closing the `extra-color` allowlist gap that Plakat alone surfaces and (b) demonstrating the regen-and-ship pattern works on a template the blocks don't fit.
- The `--allow-brand-extras` flag is now the canonical mechanism for tolerating Brand-injected `extra-style` / `extra-layer` / brand `extra-color` warnings in `bin/validate`. Zeitung migration (#8) inherits this directly; RESEARCH.md notes Zeitung carries all 7 brand colors so it likely won't re-trigger the extra-color path.
- Structural diff WITHOUT `--allow-brand-extras` and WITH `--strict` exits 1 with 13 brand-additive warnings (8 extra-style ci/* + 3 extra-layer Bilder/Text/Hilfslinien + 2 extra-color Hellgrün/Magenta), proving the allowlist is necessary and doing real work for Plakat.
- Visual_diff fidelity against `baseline.pdf` is the correctness gate. Verified clean at every step (exit 0, ~0% pixel mismatch).
