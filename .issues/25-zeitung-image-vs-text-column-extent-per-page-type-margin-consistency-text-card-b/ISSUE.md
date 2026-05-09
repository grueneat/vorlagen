---
id: '25'
title: Zeitung image-vs-text-column extent + per-page-type margin consistency + text-card
  border variation
status: open
priority: high
labels:
- bug
- templates
- dsl
source: github
source_id: 50
source_url: https://github.com/GrueneAT/vorlagen/issues/50
---

# Zeitung image-vs-text-column extent + facing-page margin consistency + text-card border variation

## Why

After #24 fixed INJECT_MAP drift (images now fill their frames), user verification on the post-#24 main surfaces a **different bug class**: the FRAMES THEMSELVES are dimensioned wrong. Hero/background images extend to page bleed when they should match the underlying text column block.

User-cited issues per page (post-#24 state):

- **Page 2**: P1 Hero is `x=-3, w=210` (full bleed). Should be **text-column-block width** (~170mm = x=20 to x=190, matching the 3-column body grid below). Currently extends 20mm past the body text on each side.
- **Page 4**: Image on right-top extends beyond the right-column text both horizontally AND vertically. Should fit inside the right-column text-extent (x=135.3, w=54.67) AND not extend below the column.
- **Page 5**: Bottom picture extends beyond text width. Should be ≤170mm. Plus L/R margins not equal.
- **Page 8**: User confirmed flush after re-look ("aligns perfectly").
- **Page 10**: Hero image on top extends beyond text. Should be text-column-block width. Plus bottom bleed.
- **Page 11**: Hero image bleeds INTO the next page (still — #16 was supposed to fix this, but a different frame is now bleeding). Portrait picture extends beyond column width AND height. Too much space between text-end and portrait. Portrait should sit INSIDE the right-text-column, not extend past it.
- **Page 12**: Confirmed clean. Image left side has a small white border which is the inset, fits fine.
- **Pages 12, 13, 14**: Green borders around some text frames have **inconsistent widths** across pages. Should be uniform.

**General observation (user)**: Facing-page L/R margins differ between inner/outer pages. The print convention is inner-margin-smaller-than-outer (gutter inset), but it should be DELIBERATE and CONSISTENT. Currently appears accidental.

This is distinct from #24 (which was about images not filling their frames). This issue is about **frames being the wrong dimensions** — they extend past the underlying text block when they should match it.

## Scope

### Phase 1 — Codex visual audit (refined prompt for THIS bug class)

NEW Codex prompt `prompts/zeitung-image-vs-text-extent.md` that asks Codex to identify per page:

1. Image frames whose horizontal extent is **wider than the underlying text-column block** (typically 170mm wide for 3-column layout, 54.67mm wide for single-column).
2. Image frames whose vertical extent **extends past the text frames they're paired with**.
3. Polygon-as-text-container (e.g. green Dunkelgrün cards on pages 12-14) where the **border widths differ** across pages or vs. the contained text.
4. **L/R margin asymmetry** within a single spread (LEFT page vs RIGHT page of the spread should have mirrored inner/outer margins).

Save output to `reviews/codex-zeitung-image-vs-text-iter1.md`. Cross-check against new audit-tool findings.

### Phase 2 — New rules

**`brand:image_within_text_block`** (severity ERROR):
- For each non-master page, identify the "text-column block" by clustering text frames by left-edge x position. Determine the block's outer extent `[x_block_left, x_block_right]`.
- For each ImageFrame on the same page that is "adjacent to text" (within 30mm vertically of any text frame in the block):
  - Assert `image.x >= x_block_left - 0.5` AND `image.x + image.w <= x_block_right + 0.5`.
  - Skip if image is exempt via `meta.yml::brand_overrides[brand:image_within_text_block]` OR has anname tagged `(full-bleed)` (intentional cover-photo design).
- Severity ERROR for body-page images; WARNING for cover-page images.

**`brand:document_margins_consistent`** (severity WARNING) — per user's "margins should be clearly defined per page type, but consistent across all pages of that type":
- Identify body-text block on each non-master page by clustering text frames.
- Define **per-page-type margin specs** in `meta.yml::body_block_margins` (new field):
  ```yaml
  body_block_margins:
    cover:    {left_mm: 20, right_mm: 20, top_mm: 20, bottom_mm: 20}
    left:     {outer_mm: 20, inner_mm: 12, top_mm: 20, bottom_mm: 20}  # outer=left, inner=right (spine)
    right:    {outer_mm: 20, inner_mm: 12, top_mm: 20, bottom_mm: 20}  # outer=right, inner=left (spine; mirrored)
  ```
  Cover, LEFT, and RIGHT pages can have DIFFERENT specs (typical: cover symmetric, body pages have inner < outer for spine). But every page of the same type MUST match its spec within 0.5mm.
- Page-type detection: cover = `own_page == 0`; LEFT = `master_name` matches `\blinks\b`; RIGHT = `\brechts\b`.
- Assert every page's body block matches its type's spec.
- Drift on ANY page = warning. Catches per-page accidental drift.
- Per-template skip via `brand_overrides`. Single-page templates only need the cover spec.

**`brand:text_card_size_consistent`** (severity WARNING):
- For colored polygons that contain text (already known to the `image_text_overlap` rule via the "text fully contained in shape" allow-case), assert: polygons of similar shape across pages with similar text content have similar `(w, h)` (within 1mm tolerance).
- Implementation: hash polygons by `(fill, anname-pattern, contained-text-style)`, group, then assert size within group.
- Catches pages 12/13/14 green-border variation.

### Phase 3 — Fix Zeitung frames

Per Codex's findings + new rules, fix per-page:

- **P1 Hero (page 2)**: `(x=-3, w=210)` → `(x=20, w=170)` (matches body block).
- **P3 Hero (page 4)**: shrink to fit single-column right (x=135.3, w=54.67) AND below the column's text-bottom y.
- **P4 Foto-Spread (page 5)**: extend to text-block width OR shrink to single-column.
- **P9 Spread halves (pages 10/11)**: width matches text-block 170mm (currently 213mm).
- **Page 11 P10 Portrait**: shrink to right-column text extent (x=135.3, w=54.67); ensure y stack with text above.
- **Pages 12/13/14 green polygons**: standardize border widths.

Each fix is a one-line change in `build.py` (frame `x_mm` and `w_mm`).

### Phase 4 — Geometric invariant tests

Extend `tools/sla_lib/tests/test_zeitung_geometry.py`:
- Per page: `image.outer_x_extent == text_block.outer_x_extent` for non-bleed-tagged images.
- Per spread: `LEFT.outer_margin == RIGHT.outer_margin` AND `LEFT.inner_margin == RIGHT.inner_margin`.
- Per polygon group: `polygon.size == group.median_size ± 1mm`.

### Phase 5 — Re-run Codex post-fix

Re-run with same prompt; verdict = pass with zero remaining findings. If any class remains, defer to #26.

### Phase 6 — Apply across other templates

Pre-apply `brand_overrides[brand:image_within_text_block]` and `[brand:facing_page_margins_consistent]` and `[brand:text_card_size_consistent]` to non-Zeitung templates with reason "scheduled for follow-up audit per #25".

### Phase 7 — Regen + SHA bump

`bin/render-gallery zeitung-a4-grun --skip-visual-diff` + meta.yml SHA bump.

## Acceptance Criteria

- [ ] Codex visual audit completed for all 14 Zeitung pages with the NEW prompt focused on image-vs-text-extent + margin consistency + text-card border width.
- [ ] 3 new BrandRules added: `brand:image_within_text_block`, `brand:facing_page_margins_consistent`, `brand:text_card_size_consistent`. Registry 15 → 18.
- [ ] All Zeitung frames identified as wrong-dimensioned are fixed in `build.py` (geometry change, not encoded).
- [ ] `python3 -m sla_lib.builder.structural_check --all` exit 0.
- [ ] `bin/audit-alignment zeitung-a4-grun --strict` exit 0.
- [ ] `python3 -m unittest discover tools/sla_lib/tests` exit 0.
- [ ] Re-run Codex post-fix: zero remaining alignment issues from new rule perspectives.
- [ ] Geometric invariant tests pin image-vs-text-block and margin relationships.

## Out of scope

- Re-authoring Zeitung's design.
- V1 templates (#19, #20, #21) — they get the new rules globally; per-template encoding stays in their own issues.

## Dependencies

Depends on: #14, #22, #23, #24.

## Labels

bug, templates, dsl, zeitung
