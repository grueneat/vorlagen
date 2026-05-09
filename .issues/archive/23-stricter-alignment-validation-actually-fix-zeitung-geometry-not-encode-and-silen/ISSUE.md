---
id: '23'
title: Stricter alignment validation + actually fix Zeitung geometry (not encode-and-silence)
status: done
priority: high
labels:
- bug
- templates
- dsl
source: github
source_id: 44
source_url: https://github.com/GrueneAT/vorlagen/issues/44
---

# Stricter alignment validation + actually fix Zeitung geometry (not encode-and-silence)

## Why

#22 (PR #42) added 2 alignment rules + an audit tool, and the executor reported "0 suspicious adjacencies" + "structural_check --all green". User verification: **the Zeitung still has the same alignment failures** the original audit motivated:

- **Page 1 cover**: `Cover Hero` (image, x=0, w=210, no bleed) does NOT share outer-bbox extent with the trimmed `u2950` polygon (x=-3 to x=213, full bleed). The image leaves a 3 mm white margin on each side after print cut. The mismatch was correctly identified in #22's RESEARCH.md and explicitly ignored by the executor.
- **Page 8**: `P7 Portrait` (x=135.3-186.6, y=200.6-277) does NOT align with `u918` Dunkelgrün polygon (x=20-190, y=195-277): 5.6 mm top gap, 3.4 mm right gap. The audit flagged this; the executor declared it "intentional" via CONSTRAINTS to silence the warning instead of fixing the geometry.
- **Page 10**: Text columns start at y=130.1 (just below the spread image at y=126.1, 4 mm gap — OK). But Polygon `Kopie von u1529` (Dunkelgrün card, y=175-277) overlaps text columns extending to y=252.4. Image-text partial overlap is a legitimate bug class with no rule today.
- **11 frames have outer-edge bleed gaps**: `Cover Hero`, `P1 Hero`, `P4 Foto-Spread`, `P9 Spread halves`, `P11 Bottom`, `P13 Hero`, plus 3 unnamed full-width Dunkelgrün polygons. All inset 3 mm from the spine in #22 (correct — prevents spine-bleed-into-facing-page) but NOT extended to ±bleed on the outer edge (incorrect — leaves white margin after print cut).

Root cause: #22's rules + audit have *too-loose thresholds* and *too-narrow scope*, AND the encode-via-CONSTRAINTS escape hatch lets the executor silence warnings without fixing geometry.

This issue makes validation **stricter by default** AND **actually fixes** the Zeitung geometry. Tests pin geometric outcomes, not rule counts.

## Scope

**Strict ordering (per user direction "build the validation script first until it finds all of those issues by itself" + "review visually if necessary but make sure the script finds these issues in a generic way"):**

1. Build Phases 1+2+3 (rules + audit tool + CI script) FIRST.
2. Run `bin/audit-alignment zeitung-a4-grun --strict` and verify all 6 known issues from Phase 3b are detected.
3. **If issues are missed:** strengthen the rules. **The rules must be generic** — they MUST work on any template, not be hardcoded with Zeitung-specific anname matches or coordinate constants. Tune by adjusting thresholds + detection logic, not by special-casing.
4. **Visual review is permitted** for this specific verification step: comparing the audit's output against `templates/zeitung-a4-grun/page-*.png` to confirm the script catches what a human would catch. Two routes available:
   - **Codex CLI** (preferred for token-budget reasons): `codex exec` with a prompt that asks Codex to identify alignment issues in `templates/zeitung-a4-grun/page-*.png` and produce a structured list (page, type, what's wrong). Compare against `bin/audit-alignment` JSON output. Run via `issue-cli review-exec --tool codex --prompt <path> --name zeitung-alignment-audit --review-type topic --review-mode topic --output-dir reviews/`. Save Codex's report alongside the audit's report in the issue directory.
   - **Direct Claude image read**: only as fallback if Codex disagrees with audit and a tiebreaker is needed. Limit to user-reported pages (1, 8, 10, 11, 12).
   
   The two outputs become the test suite for the rules — every visual issue on either list MUST be in the audit's output. If the audit misses one, strengthen the rules.
5. **Iterate** Phase 1 + Phase 3b until the audit catches every visible alignment issue without false-positive explosion.
6. Only then proceed to Phase 4 (fix Zeitung based on audit's findings, not pre-listed coordinates).
7. Re-run audit after fix → must report zero error-severity violations on Zeitung.

This is TDD-for-rules: known violations are the test cases the rules must catch generically.

### Phase 1 — Stricter rules (`tools/sla_lib/builder/brand_constraints.py`)

**New rule `brand:bleed_coverage`** (severity=ERROR):
- For each non-master page in a facing-pages document, identify full-width frames (`w > 0.7 × page_w`) that are not anchor-positioned and not rotated.
- For LEFT pages: outer edge = left. Required: `x ≤ -bleed + tol`.
- For RIGHT pages: outer edge = right. Required: `x + w ≥ page_w + bleed - tol`.
- Severity = ERROR (not warning) — this is a print-cut hazard.
- Skip via per-frame anname tag `(no-bleed)` in the frame's anname OR per-template `meta.yml::bleed_coverage_exempt_annames: [...]` list.

**Replace `brand:undeclared_alignment_drift` with `brand:visual_adjacency_drift`** (broader thresholds):
- `axis_drift_min_mm: 0.5`, `axis_drift_max_mm: 25.0` (was 5.0)
- `adjacency_gap_min_mm: 0.5`, `adjacency_gap_max_mm: 30.0` (was 12.0)
- Severity stays warning; per-template skip via `brand_overrides`.
- Catches the 5.6 mm page-8 case the prior thresholds missed.
- **CONSTRAINTS declaration no longer fully silences the warning** — if the declaration is `aligned_below(A, B, gap=10)` but actual gap is 15 mm (declaration disagrees with geometry), STILL emit warning "constraint declaration disagrees with actual geometry by 5 mm". This breaks the encode-and-silence escape.

**New rule `brand:image_text_overlap`** (severity=ERROR):
- For each non-master page, iterate every (ImageFrame, TextFrame) pair. Compute axis-aligned bbox overlap area.
- Allowed: zero overlap OR text fully contained in image (caption-on-photo) OR image fully contained in text (drop-cap; rare).
- Forbidden: partial overlap (text crossing image boundary).
- Skip via `brand_overrides[brand:image_text_overlap]`.

**New rule `brand:cover_extent_match`** (severity=WARNING initially, ERROR after audit):
- For pairs of full-width-ish frames on the same page that touch each other vertically (one's bottom == other's top within 0.5 mm), assert their outer bboxes match (`x ≈ x'` and `x+w ≈ x'+w'` within 0.5 mm).
- Catches page-1 `Cover Hero` vs `u2950` mismatch.

**New rule `brand:image_in_container_flush`** (severity=ERROR):
- For each ImageFrame whose bbox is contained inside a colored Polygon (fill in `{Dunkelgrün, Hellgrün, Magenta, Gelb}`), assert at least **2 of the 4 edges are flush** (within 0.5 mm) with the container's edges. A portrait sitting inside a green card with arbitrary inset on all four sides (page-8 `P7 Portrait` vs `u918`: 3.4 mm right gap + 5.6 mm top gap + asymmetric left/bottom) is forbidden — the design intent is either flush-anchor (TL/TR/BL/BR corner anchored) or a uniform inset (all-four-sides equal). Asymmetric insets indicate accidental drift.
- Skip via `brand_overrides[brand:image_in_container_flush]` per template if the design is genuinely asymmetric.

**New rule `brand:portrait_column_alignment`** (severity=ERROR):
- For each ImageFrame on a page that is "portrait-shaped" (`h > w` AND `h > 60` mm AND `w > 30` mm) AND is adjacent to a text column above it (text frame whose bbox bottom is within 30 mm of image top AND whose `x` matches `image.x` within 25 mm), assert:
  - `image.x ≈ text_column.x` (within 0.5 mm) — share left axis with column.
  - **AND** `image.x + image.w ≈ text_column.x + text_column.w` (within 0.5 mm) OR `image.x + image.w ≈ page_w + bleed` (right edge in bleed). Width-match-or-bleed: portrait must either be column-width OR extend to outer bleed.
- Catches page-11 `P10 Portrait` (left axis matches column ✓ but right edge is 8.1 mm short of bleed AND not column-width). Catches page-8 `P7 Portrait` (left edge doesn't match column above, right edge doesn't match polygon edge).
- Skip per-template via `brand_overrides`.

### Phase 2 — Audit tool tightening (`tools/audit_alignment.py`)

- New default thresholds matching the new rule (`--axis-tol 25.0 --adjacency-tol 30.0`); CLI flags still override.
- New `--strict` mode: emit ERRORs (not warnings) for everything. Used in CI per-template after the template is "audited clean".
- Output adds geometric-outcome suggestions: not just "declare with `same_x(A, B)`" but also "OR fix geometry: A.x=N, B.x=N".

### Phase 3 — Generalized CI script (NOT template-specific tests)

**Per user direction:** validation must be **generalized across all templates**, not pinned to Zeitung coordinates. Mechanism = the new BrandRules running globally + a CI script that hard-fails on any error-severity violation across any template.

- **No `test_zeitung_geometry.py`.** Pinning specific frame coordinates would be brittle (any future legitimate Zeitung edit breaks the test) AND template-specific (other templates need the same protection but wouldn't get it).
- Instead: **`bin/audit-alignment --all --strict`** wired into `.github/workflows/pages.yml` exits non-zero on ANY error-severity violation across ANY template. Promoted from #22's informational `|| true` to fatal in this issue.
- Rule-level unit tests stay generic: each new rule has its own `test_brand_<rule>.py` using synthetic mini-docs to verify the rule semantics. NO real-template coordinates pinned.
- Per-template `meta.yml::brand_overrides` lets templates skip a rule with documented reason. After Phase 4 the Zeitung geometry passes all rules naturally — Zeitung does NOT skip them. Other templates (postkarte, plakat, V1-bound) get pre-applied skips with reason "scheduled for follow-up audit" so the global gate doesn't block them mid-rollout.
- `bin/audit-alignment --strict` exit-codes: `0` clean across all templates, `1` any error-severity violation. Output stays Markdown for human reading; `--json` for machine-readable.

### Phase 3b — Build-detector verification gate (BEFORE Phase 4)

After Phases 1+2+3 land:
1. Run `bin/audit-alignment zeitung-a4-grun --strict --json > reviews/audit-zeitung.json`.
2. Run Codex visual review via `issue-cli review-exec --tool codex --prompt prompts/zeitung-visual-audit.md --name zeitung-visual --review-type topic --review-mode topic --output-dir reviews/` with a prompt that asks Codex to enumerate alignment issues per page in `templates/zeitung-a4-grun/page-*.png` (output: structured Markdown list).
3. Cross-check: every visual issue Codex reports MUST appear in the audit JSON. If the audit misses any, strengthen the rule (Phase 1) and re-run. **Generic rules only — no Zeitung-specific anname matches or coordinate constants in the rule code.**
4. Confirm at minimum the following known issues are detected.

Required detections (from this issue's "Why" section, verified against current main):

| # | Page | Issue | Rule that should catch it |
|---|---|---|---|
| 1 | 1 | `Cover Hero` (x=0, w=210) ≠ `u2950` outer-bbox extent (x=-3 to x=213) | `brand:cover_extent_match` OR `brand:bleed_coverage` |
| 2 | 2,5,10,11,12,13,14 (×11 frames) | full-width frames inset from outer edge (no outer bleed) | `brand:bleed_coverage` |
| 3 | 8 | `P7 Portrait` not flush with `u918` polygon (3.4 mm right + 5.6 mm top) | `brand:image_in_container_flush` |
| 4 | 8 | `P7 Portrait` left edge doesn't match column-3 text axis above | `brand:portrait_column_alignment` |
| 5 | 10 | text columns `Kopie von u2d5c (13)` etc. partially overlap green polygon `Kopie von u1529` | `brand:image_text_overlap` |
| 6 | 11 | `P10 Portrait` right edge 8.1 mm short of bleed | `brand:portrait_column_alignment` |

If `bin/audit-alignment zeitung-a4-grun --strict` reports all 6 (no missing detections), proceed to Phase 4. Else: strengthen rules and re-run.

### Phase 4 — Actually fix Zeitung geometry (`templates/zeitung-a4-grun/build.py`)

- **Page 1 Cover Hero**: `(x=0, w=210)` → `(x=-3, w=216)` (full-bleed match with u2950).
- **Page 2 P1 Hero**: `(x=0, w=207)` → `(x=-3, w=210)` (extends to LEFT bleed; spine inset preserved).
- **Page 5 P4 Foto-Spread**: `(x=3, w=207)` → `(x=0, w=213)` (extends to RIGHT bleed; spine inset preserved).
- **Pages 10/11 P9 Spread halves**: each `(x=0, w=210)` — extend outer edges. LEFT half: `(x=-3, w=213)`; RIGHT half: `(x=0, w=213)` with the right edge in bleed.
- **Page 12 unnamed Dunkelgrün + P11 Bottom**: each `(x=0, w=207)` → `(x=-3, w=210)` (LEFT page outer = bleed-extended).
- **Page 13 unnamed**: similar inversion for RIGHT page.
- **Page 14 P13 Hero + unnamed**: `(x=0, w=207)` → `(x=-3, w=210)`.
- **Page 8 P7 Portrait + u918**: portrait must satisfy `brand:image_in_container_flush` AND `brand:portrait_column_alignment`. Recommended: `P7 Portrait (x=135.3, y=195, w=54.7, h=82)` — flush with u918 top (y=195) AND right (x=190 → x+w=190 → w=54.7). Aligns with column-3 above (x=135.3, w=54.7). Or alternative: shrink u918 to fit portrait. Planner decides per design intent.
- **Page 10 text columns + Polygon `Kopie von u1529`**: image-text overlap. Recommended: text columns end at y=175 (matching green-card top, no overlap). Verifies `brand:image_text_overlap` clean.
- **Page 11 P10 Portrait**: `(x=135.3, y=202.6, w=66.6, h=94.4)` → `(x=135.3, y=202.6, w=77.7, h=94.4)` — column-x preserved AND right edge extends to outer bleed (x+w = 213). Verifies `brand:portrait_column_alignment` clean (right edge in bleed).

### Phase 5 — Drop encode-and-silence CONSTRAINTS entries

For each declaration in `templates/zeitung-a4-grun/CONSTRAINTS = [...]` that was added in #22 to silence a warning on misaligned geometry: REMOVE the declaration. Re-run the audit (now with stricter thresholds): warnings should appear. Fix the geometry per Phase 4 until warnings clear naturally (no encode-and-silence).

### Phase 6 — Apply across other facing-pages templates

`brand:bleed_coverage` runs globally. Verify on other templates:
- `postkarte-a6-kampagne`, `plakat-a1-hochformat`, all V1-bound templates — pre-applied `brand_overrides[brand:bleed_coverage]` skip with reason "single-page, no facing-page bleed concerns" if facing_pages=False.
- `wahlaufruf-postkarte-a6-quer` (just merged in #17): single-page, no bleed-coverage applicable, but **`brand:image_text_overlap` MAY surface real issues** — re-run audit and document.

### Phase 7 — Promote `bin/audit-alignment` to fatal CI step

`.github/workflows/pages.yml`: `bin/audit-alignment --all --strict` becomes a fatal step (no `|| true`). Drops in this PR — Zeitung is clean by Phase 4; other templates have skip overrides applied in Phase 6.

Subsequent template work (e.g. #18-#21) MUST keep this CI step green: either by passing the rules naturally OR by adding a documented `brand_overrides` skip per template.

## Acceptance Criteria

- [ ] `brand:bleed_coverage` exists with full test coverage; severity=ERROR; per-template skip mechanism documented.
- [ ] `brand:visual_adjacency_drift` replaces `brand:undeclared_alignment_drift` (broader thresholds, declaration-disagreement detection).
- [ ] `brand:image_text_overlap` exists with full test coverage.
- [ ] `brand:cover_extent_match` exists with full test coverage.
- [ ] `tools/audit_alignment.py` default thresholds tightened; `--strict` flag added.
- [ ] `tools/sla_lib/tests/test_zeitung_geometry.py` exists, pins ≥15 frame coordinates, all pass after Phase 4 lands.
- [ ] Zeitung's 11 outer-bleed-gap frames are fixed (geometry, not encoded). Verified by: `bin/audit-alignment zeitung-a4-grun` reports zero `brand:bleed_coverage` ERRORs.
- [ ] Page-1 Cover Hero shares outer-bbox extent with u2950 (verified by `brand:cover_extent_match`).
- [ ] Page-8 P7 Portrait flush with u918 (verified by geometric-outcome test).
- [ ] Page-10 text/card overlap resolved (verified by `brand:image_text_overlap` zero violations).
- [ ] Page-11 P10 Portrait outer edge at bleed.
- [ ] All Zeitung CONSTRAINTS that previously silenced misalignments are REMOVED. Re-encoded only for genuinely-intentional adjacencies.
- [ ] `python3 -m sla_lib.builder.structural_check --all` exits 0.
- [ ] `python3 -m unittest discover tools/sla_lib/tests` exits 0.
- [ ] `bin/check-stale-previews` exits 0 (template.sla regenerated, SHA bumped).
- [ ] CI green.
- [ ] User-confirmed pages 1, 8, 10, 11, 12 of Zeitung visually re-checked by human reviewer in PR.

## Out of scope

- V1 templates' alignment encoding (#18-#21) — they get the new rules globally; their per-template encoding remains in their issues. After #23 lands, #17 (postkarte V1, already merged) needs re-audit with the stricter rules and possible fixup PR.
- Re-authoring Zeitung's design — only geometric drift fixes, not layout redesign.
- Visual-pixel comparison by Claude.

## Dependencies

Depends on: #14, #22 (constraint DSL + alignment rules + audit tool). Closes: nothing additional.

## Labels

bug, templates, dsl, zeitung
