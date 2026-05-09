---
id: '22'
title: 'Alignment system v2: spine-safety + undeclared-drift detection + audit tooling
  + apply to stable templates'
status: open
priority: high
labels:
- bug
- templates
- dsl
source: github
source_id: 41
source_url: https://github.com/GrueneAT/vorlagen/issues/41
---

# Alignment system v2: spine-safety + undeclared-drift detection + automated audit tooling + apply to stable templates

## Why

#16 (PR #40) addressed bbox-overflow (`brand:inside_page` errors) but missed two larger bug classes the user identified post-merge:

1. **Spine-bleed.** On a facing-page spread, a frame at `x=0, w=210` (LEFT page) or `x=0` (RIGHT page) sits flush against the spine. Scribus extends the 3 mm bleed across the spine into the facing page. `inside_page` doesn't catch it (the bbox ends exactly at the page boundary). Verified via `pdfimages -list`: image obj 42 is on both pages 2 + 3, obj 84 on pages 10 + 11, obj 97 on pages 12 + 13 — each is a single image leaking across the spread.

2. **Systemic template-level alignment failures.** The Zeitung template was authored in Scribus by hand, then round-tripped into our build.py. Many frames were placed by eyeball; alignments between images, text columns, and Dunkelgrün/Hellgrün backgrounds drift across pages. User-confirmed instances:
   - **Page 1 (cover)**: `Cover Hero` (x=0, y=0, w=210, h=155.57) ends at y=155.57. The Dunkelgrün polygon `u2950` (rotated 90°) bbox is x=-4.1..216.4, y=155.6..304.2 — it extends 4 mm past the left bleed AND 6.4 mm past the right bleed, AND past the page bottom. They don't share width or vertical extent.
   - **Page 8**: `P7 Portrait` (x=134.7–186.0) sits inside Dunkelgrün polygon `u918` (x=20–190) but isn't flush — 4 mm gap right, 5.6 mm gap top — and its left edge doesn't align to the right-column text axis above (x=135.3).
   - **Page 10**: `P9 Spread` ends at y=126.1; text columns "Kopie von u2d5c (13)" and "u2da1 (16)" start at y=49.5 — text overlaps image.
   - **Page 11**: `P10 Portrait` left edge (x=143.4) is 8.1 mm off the right-column text axis above (x=135.3).
   - **Page 12**: unnamed Dunkelgrün polygon (#16's fix moved x=210→0 but kept it on idx 11) — same spine-bleed pattern AND likely a misattribution.

3. **My #16 P9 Spread fix was wrong.** `P9 Spread` is a true intended SPREAD image (the name says so). The `pdfimages -list` evidence in #16's research ("pages 10/12 render zero image content") was misread — those pages DO render content, shared with the adjacent page via the spine-bleed mechanism. `P9 Spread` should use the `SpreadImage` block from #14, not be flattened to a single page.

The **user's framing** (which this issue adopts): the question isn't "fix these specific frames." It's: **encode the intended alignment relationships of every Zeitung element as constraints**, then mechanically catch any drift. The same approach catches the user-named bugs above AND any future drift, in code, without visual review.

## Scope

This is a **template-wide alignment audit + encode + fix + new spine-safety rule**, in one PR. Larger than a per-frame patch, but principled and testable.

### Phase 1 — Audit (executor inventories what's on each page; planner shapes the constraint catalogue)

For each of the 14 print pages, enumerate every primitive (ImageFrame, Polygon, TextFrame) with `(x, y, w, h, anname, fill, scale_type)`. Group into:
- **Page-bounds** (what the printable content area + bleed are).
- **Background polygons** (Dunkelgrün/Hellgrün/Gelb fills — the "container" elements).
- **Hero images / portraits / photos**.
- **Text columns** (3-column body grid; common columns: x=20, 77.7, 135.3, w=54.67).
- **Header/footer** (page number, breadcrumb).

For each page, write the **intended** alignment relationships. Examples per the user's complaints:
- Page 1: `Cover Hero.bottom == u2950.top` AND `Cover Hero.width == u2950.bbox_width` AND `u2950.bbox_left == -bleed` AND `u2950.bbox_right == page_w + bleed` (full-bleed bottom band).
- Page 8: `P7 Portrait.left == column_3.left` AND `P7 Portrait.right == u918.right - inset` AND `P7 Portrait.top == u918.top + inset`.
- Page 10: `aligned_below(text_column_n_top, P9_Spread.bottom, gap_mm=4)`.
- Page 11: `aligned_below(P10 Portrait, column_3, gap_mm=...)` AND `same_x(P10 Portrait, column_3)`.

The intended relationships become the per-template `CONSTRAINTS = [...]` list. They start RED (current build.py violates them); the executor then edits build.py to make them GREEN.

### Phase 2 — Encode (per-template CONSTRAINTS list extension)

Add to `templates/zeitung-a4-grun/build.py`:

```python
CONSTRAINTS = [
    # Page 1 cover
    distance_y("Cover Hero", "u2950", equals=0.0, tolerance_mm=0.5,
               name="cover_top_to_green_bottom_flush"),
    same_size("Cover Hero", "u2950", axis="w", tolerance_mm=0.5,
              name="cover_top_bottom_share_width"),  # would need u2950 trimmed
    # ... etc, one entry per audited relationship
    # Page 8
    same_x("P7 Portrait", "<column-3 text frame above>", name="p8_portrait_col3_axis"),
    # Page 10 (after P9 Spread converted to SpreadImage)
    aligned_below("Kopie von u2d5c (13)", "P9 Spread · left", gap_mm=4.0,
                  name="p10_text_below_spread"),
    # Page 11
    same_x("P10 Portrait", "<column-3 text frame on p11>", name="p11_portrait_col3_axis"),
    aligned_below("P10 Portrait", "Kopie von u2da1 (19)", gap_mm=11.6,
                  name="p11_portrait_below_text"),
    # ... etc
]
```

### Phase 3 — Fix build.py to satisfy constraints

For each red constraint, edit the offending frame's `(x, y, w, h)` until green. Common fixes:
- Trim u2950 polygon to fit page bounds (may need to coordinate with #39).
- Convert `P4 Foto-Spread` (intended spread) to `SpreadImage(left=page3, right=page4, image=..., page_w_mm=210, h_mm=108.1)` with `local_offset_mm=(-210, 0)` on right half.
- Convert `P9 Spread` to `SpreadImage` (revert my #16 misfix).
- Inset spine-touching single-page frames (`P1 Hero`, `P3 Hero`, `P10 Portrait`, `P11 Bottom`, `P13 Hero`): `w=210→207` (preserves left axis, leaves 3 mm spine safety).
- Re-position page-8 portrait to align with column-3 axis and polygon edges.
- Re-position page-10 text columns to start below the (newly-Spread) image.
- Re-position page-11 portrait to align with text column above.

### Phase 4 — Add `brand:spine_safety` rule (global)

New BrandRule (rule #10) in `tools/sla_lib/builder/brand_constraints.py`:

For any non-`SpreadImage` ImageFrame on a facing-page LEFT/RIGHT page where the frame's spine-side edge is within 3 mm of the spine (right edge for LEFT pages = `x+w >= page_w - tol`; left edge for RIGHT pages = `x <= tol`), emit a `warning`. Use `Document.facing_pages` AND `master_name` containing "links"/"rechts" to determine side.

Then verify ALL templates' previews under `--all` after the rule is enabled. Other templates likely don't have facing pages — quick win, no cascade.

### Phase 4b — Heuristic "undeclared-alignment-drift" rule (general detection)

The user's request: **"detect this kind of spill or misalignment of elements automatically; even if it's not defined in the spec, either report warnings or errors in case those alignment configurations aren't defined in the spec and mentioned as conditions."**

Add a new BrandRule (rule #11): **`brand:undeclared_alignment_drift`**.

Algorithm:
1. Build the set of declared-relationship pairs from the template's `CONSTRAINTS = [...]` list. For every constraint that references multiple annames (`same_x`, `same_y`, `mirrored_x/y`, `inside`, `aligned_below`, `distance_x/y`, `equal_gap`, `same_size`, `same_style`), add each pairwise combination to the set.
2. For each page, iterate every pair of primitives `(P, Q)`:
   - **Suspicious-axis test**: if `|P.x - Q.x|` is between 0.5 mm and `axis_threshold_mm` (default 5 mm), they're "almost aligned on x" — flag if pair is not in the declared set.
   - **Suspicious-axis test (y)**: same for y.
   - **Suspicious-adjacency test**: if `P` is above `Q` (`P.bottom < Q.top`) and the gap `Q.top - P.bottom` is between 0.5 mm and `adjacency_threshold_mm` (default 12 mm), and `|P.x - Q.x| < axis_threshold_mm`, they're "almost stacked" — flag if pair not in declared set.
   - **Containment-near test**: if `P` is mostly inside `Q` (≥ 80% bbox overlap area) but not fully inside, flag if pair not in declared set.
3. Emit one warning per suspicious pair: `"Frames {A!r} and {B!r} on page {N} appear visually adjacent (axis-x drift {δ}mm). Either declare the relationship via aligned_below/same_x/inside in CONSTRAINTS, or fix the geometry."`
4. Severity = warning by default (heuristic rules can false-positive). Per-template opt-out via `meta.yml::brand_overrides[brand:undeclared_alignment_drift]` for templates that aren't ready to be audited.

This rule is the heart of the user's request: **the template either declares its alignment intent, or the rule complains.** It catches the page-8/10/11 cases above without the planner needing to enumerate them by hand. Once the template is audited (Phase 1-3), the rule is silent — alignments are all declared, geometry matches.

Implementation footprint: ~80 lines of pair-iteration + tests. No new dependencies. `Constraint.referenced_annames()` already exists; the rule unions across all entries to build the declared-pair set. For BrandRule constraints (which don't have `referenced_annames`), we union the targets too if they expose them.

Test cases for `test_brand_undeclared_alignment_drift.py`:
- Two frames with near-shared x-axis (1 mm drift) and no constraint → warning.
- Same two frames + an explicit `same_x(A, B)` declared → no warning.
- Two frames far apart in both x and y → no warning (not adjacent).
- Two frames stacked with `aligned_below` declared → no warning.
- Two frames stacked with no constraint, gap < adjacency_threshold → warning.

### Phase 5 — Tests + regen

- New file `tools/sla_lib/tests/test_brand_spine_safety.py` — 6 cases (LEFT/RIGHT × within-tol/outside-tol × non-facing no-op). Atomic.
- Update `tools/sla_lib/tests/test_zeitung_overflow.py` — assert zero `inside_page` errors AND zero `brand:spine_safety` warnings AND all per-template CONSTRAINTS green.
- Update `tools/sla_lib/tests/test_brand_constraints.py` — bump count from 9 to 10.
- Update `tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip` allow-list — broader divergence than #16 introduced.
- `bin/render-gallery --skip-visual-diff` to regen `template.sla`, `template-preview.sla`, `previews_for_sla` SHA, `page-*.png`.
- Update `templates/_specs/SCHEMA.md` §12 + `shared/brand/SPEC-WRITING-GUIDE.md` catalogue with `brand:spine_safety`.

### Phase 6 — Doc + verification

- `templates/zeitung-a4-grun/README.md` German note explaining the alignment-encoded model and the difference from upstream.
- Final verification: `pdfimages -list templates/zeitung-a4-grun/preview.pdf` shows each image object on **only one page** (no cross-spread leakage). Capture verbatim in EXECUTION.md.

## Acceptance Criteria

- [ ] All per-template `CONSTRAINTS = [...]` entries are GREEN (zero violations on `python3 -m sla_lib.builder.structural_check zeitung-a4-grun`).
- [ ] `brand:spine_safety` rule reports zero warnings on Zeitung after the fix.
- [ ] `python3 -m sla_lib.builder.structural_check --all` exits 0.
- [ ] `pdfimages -list templates/zeitung-a4-grun/preview.pdf` shows each image on exactly ONE page (zero cross-spread sharing).
- [ ] `python3 -m unittest discover tools/sla_lib/tests` exits 0.
- [ ] `bin/check-stale-previews` exits 0.
- [ ] CI green (`.github/workflows/pages.yml::Validate reproductions` keeps the `sla_diff_strict: false` from #16 — Zeitung's intentional divergence from upstream is accepted).
- [ ] User-reported pages 1, 8, 10, 11, 12 visually inspected by a human reviewer in the PR (Claude doesn't view images per token-budget constraint).
- [ ] Brief §10 Session-History row added.

### Phase 7 — Apply to other stable templates

The new infrastructure (spine-safety + undeclared-drift + audit tool) lands once globally. Applying it to per-template alignment audit is then mechanical:

- **`templates/postkarte-a6-kampagne/`** — apply audit, encode CONSTRAINTS for declared adjacencies, fix any geometry drift, re-render.
- **`templates/plakat-a1-hochformat/`** — same.
- **`templates/zeitung-a4-grun/`** — full Phase 1-6 above.

Templates `wahlaufruf-postkarte-a6-quer`, `wahltag-tueranhaenger`, `themen-plakat-a3-quer`, `infostand-tent-card-a5-quer`, `kandidat-falzflyer-din-lang` are bound to V1 layouts in #17–#21. Their alignment encoding lives **inside those issues** (which already prescribe `CONSTRAINTS = [...]` lists). The new BrandRules from this issue will catch any V1 drift automatically once the V1 layouts land. **Do not pre-encode their CONSTRAINTS in this issue** — duplicate work and would conflict with #17–#21.

### Phase 8 — Automated audit tooling

To keep token usage low and make this auditable in the future:

- `tools/audit_alignment.py` — CLI that scans one or all templates and emits a per-template Markdown report of:
  - Page-by-page primitive inventory.
  - Heuristic suspicious-pair list (per `brand:undeclared_alignment_drift` algorithm above).
  - Spine-bleed flag list (per `brand:spine_safety` algorithm above).
  - Suggested CONSTRAINTS entries (skeletons the executor / human can paste into the template's build.py).
- Wired into `bin/audit-alignment` for ergonomics.
- Wired into `.github/workflows/pages.yml` as a non-fatal step (informational only initially; promotion to fatal once all production templates are clean).
- Unit tests for the audit tool: synthetic doc with known suspicious pair → tool flags it; synthetic doc with declared CONSTRAINTS → tool stays quiet.

The audit tool's Markdown output becomes the input for future per-template `CONSTRAINTS` encoding work — humans (or LLMs in tight token budgets) can read the per-template report and paste the suggested constraint skeletons into build.py without re-deriving them.

## Acceptance Criteria (final)

- [ ] `brand:spine_safety` and `brand:undeclared_alignment_drift` exist as new BrandRules with full test coverage.
- [ ] `tools/audit_alignment.py` exists, has CLI + library API, has tests.
- [ ] `--all` reports zero errors and zero warnings on `templates/zeitung-a4-grun`, `templates/postkarte-a6-kampagne`, `templates/plakat-a1-hochformat`.
- [ ] `pdfimages -list templates/zeitung-a4-grun/preview.pdf` shows each image on exactly ONE page (no cross-spread sharing).
- [ ] Per-template `CONSTRAINTS = [...]` lists are present for the three stable templates, capturing all detected adjacencies.
- [ ] `bin/audit-alignment --all` produces clean report for the three stable templates (no undeclared adjacencies remaining).
- [ ] All tests pass: `python3 -m unittest discover tools/sla_lib/tests`.
- [ ] CI green; gallery regenerated; `previews_for_sla` SHAs bumped.
- [ ] User-reported pages 1, 8, 10, 11, 12 of Zeitung visually inspected by a human reviewer in the PR.
- [ ] SCHEMA.md §12 + SPEC-WRITING-GUIDE.md updated with the two new rules + audit-tool reference + worked migration recipe.
- [ ] Brief §10 Session-History row added.

## Out of scope

- V1 templates' alignment encoding (#17–#21 own that, the new BrandRules will catch drift automatically once V1 lands).
- Re-authoring the Zeitung's overall design — only encoded alignment + targeted frame fixes; no layout redesign.
- Visual-pixel comparison by Claude (token budget).
- Promoting `bin/audit-alignment` from informational to CI-fatal — defer to a follow-up after enough templates are clean.

### Superseded follow-ups

- **#39 (u2950 cover polygon)** — supersedes by Phase 3 of this issue (Page-1 alignment audit will trim u2950 as part of the cover-image-to-bottom-band relationship). Close #39 as duplicate when this lands.

## Dependencies

Depends on: #14 (`SpreadImage`, `aligned_below`). Blocks: nothing immediately. Supersedes: #39 (cover polygon).

## Labels

bug, templates, zeitung, dsl
