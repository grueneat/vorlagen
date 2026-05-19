# Review notes — flyer-a6-querformat-zweigeteilt

## What this template is

A6 landscape (Querformat) campaign flyer, "zweigeteilt" (two-part)
layout — a 6-page InDesign document exported page-based. Front uses a
full-bleed photo (`ziesel.jpg`, a squirrel), a dark-green panel with a
three-line headline and bullet-list body copy; the back carries the DIE
GRUENEN logo, a candidate strip ("Leonore Gewessler"), social-media
icons, an Impressum line, and a dark poster image (`plakat-dunkel-fuer-
flyer.png`). It is the landscape sibling of `26-03-flyer-a6-hochformat-
zweigeteilt` and shares an issue profile with `26-03-flyer-a6-
querformat-portrait`.

## Re-import outcome — GREEN (structural)

`bin/idml-import --scaffold-only --reimport` ran clean with the current
converter (the batch's full fix set — CMYK->sRGB + aspect-fill crop,
squiggle re-anchoring, the consumed attributes, SpaceAfter/FLOP/
min_glyph_shrink, the layout fixes, the mixed-font headline split — was
already in the worktree; no new converter changes were needed).

- `asset_audit.yml::ok == true` — all 4 `<Link>` files resolved and
  converted. No missing assets — the HARD EXCEPTION does not apply.
- `every_idml_run_present_in_build_py: true`; every applied
  ParagraphStyle emitted; every frame `Self` has an `anname`.
- The converter deliberately skipped 4 off-page Rectangles (u6f0,
  u6f2, u77f, u964 — registration furniture on the pasteboard).
- Inventory compare: exit 3 (drift only, additions — the split-headline
  frames uaf8_l2/uaf8_l3/u6aa_l2; no `missing`, no regression). The
  fresh inventory was promoted to `SCAFFOLD_INVENTORY.yml`.

## What the new fix set resolved this pass

- **CMYK images now render.** The previous pass tolerated `ziesel.jpg`
  and `green-pine-trees-covered-with-fog.jpg` (both CMYK JPEGs)
  rendering blank. The converter's CMYK->sRGB + aspect-fill crop fix
  fully resolves this: `image_content_audit` 4 ok / 0 broken;
  `image_frame_visibility_audit` 4 ok / 0 invisible. asset_render_ratio
  — uace (ziesel) 0.998, u906 (green-pine) 0.996, uad7 (DIE GRUENEN
  logo) 0.928 — all well above the 0.35 floor. ub34 (plakat) renders
  all-black in baseline and preview (intentional dark poster artwork).
  Two tolerance entries were removed as obsolete.
- **`text_render_audit` is GREEN** (was 12 words clipped) — no baseline
  body text is missing from the render.
- **`split_headline_spacing` GREEN** — the mixed-font headline split
  (uaf8 + uaf8_l2 + uaf8_l3) renders evenly spaced; pixel audit
  max_drift 0.0pt on uaf8, 0.48pt on u6aa (both under the 2.0pt gate).
- **`squiggle_alignment_audit` GREEN** — both squiggles (u678, u679)
  sit on their word, yellow, 0 issues.
- **`idml_attribute_coverage` GREEN** — no new unconsumed attribute.

## Per-frame tune fixes applied (build.py — no tolerance)

1. **u9df bullet list — LINESP 8.0 -> 15.999999999999998.** The
   re-imported build.py carried `LINESP: '8.0'` on every body paragraph
   of the u9df bullet frame. The converter propagated a stray
   `<Leading>8</Leading>` from a CharacterStyleRange whose content is
   only `'.\t'` (a period + tab, not body text). At 8pt leading all 5
   bullets collapsed into column 1 so Scribus never flowed the 2nd
   column — u9df rendered single-column where the baseline (and the
   sibling 2-column frame u67c, which carries NO LINESP override)
   render 2-column. Setting LINESP to the bullet ParaStyle's ~16pt
   restored the 2-column flow. line_match 47 -> 40.
2. **u9df — y_mm 45.55 -> 46.566 (+2.88pt).** After the LINESP fix the
   pixel audit measured u9df's line-1 ink-top 2.88pt above the baseline
   and line_match raised a `frame_vertical_position` finding. The
   +2.88pt y_mm correction anchored the block onto the baseline first
   line — `frame_vertical_position` cleared, line_match 40 -> 34.

The `bin/tune-render` -> `bin/tune-fix` loop ran to the point where no
playbook can advance (`line_spacing` sim returned no measurable drift
for every frame; `y_mm_shift` found no uniform-offset frames). The
final render that produced the committed artifacts ran
`bin/tune-render --no-transactional` so the documented-red render is
promoted into `templates/`.

## Tune outcome — RESIDUAL (red preflight, fully documented)

Three tolerances flip their audit green (`severity: cosmetic`):
inventory (4 off-page registration marks), image_audit (43 raster/ICC
deltas), text_position_audit_jitter (67 sub-perceptible FreeType
kerning drifts).

Four audits stay RED — documented, classified, NOT flipped green:

| Audit | Issues | vs prev pass | Classification |
|---|---|---|---|
| line_match_audit | 34 (38/72 match) | 47 -> 34 | scribus-engine-bug |
| systematic_text_audit | 6 | 11 -> 6 | scribus-engine-bug |
| text_position_audit_structural | 205 | 269 -> 205 | scribus-engine-bug |
| visual_diff_regions | 52 | (was phase error) | human-review |

All four are the same root cause: **cross-renderer line-wrap
divergence**. Scribus and InDesign break the justified body / bullet
paragraphs — most of them inside the 2-column frames u67c / u92e /
u9df / u6d8 — at slightly different words because their font-metric
and hyphenation models differ. The `line_spacing` simulator returned
NO measurable drift for any (LINESPMode, LINESP) candidate on any
frame: no leading value reconciles a wrap-count change. Every
remaining line_match finding is `wrap` / `unmatched` / `first_word_x`
on a frame whose baseline and preview line counts differ (u6d8 10 vs
11, u67c 7 vs 9, u92e 10 vs 9, u9df 8 vs 7, ub3b 4 vs 3). u693 / u85a
`first_word_x` are -90deg rotated Impressum frames — pdfplumber's
x-measurement on rotated text is unreliable.

This is a known-acceptable residual (the overnight-batch known-issues
policy lists cross-renderer body-text line-wrap drift). A red preflight
with fully documented, classified residuals is the accepted terminal
state for this template, matching the sibling flyer/leporello
templates committed earlier in this batch.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 1 (front, ziesel/squirrel photo)** — the squirrel photo
   `uace` now renders correctly (CMYK->sRGB fix). Was blank last pass.
2. **Page 5 (back)** — the green-pine photo strip `u906` now renders a
   dark forest band. Was blank last pass.
3. **DIE GRUENEN logo (uad7)** — renders correctly (white logo).
4. **Page 4 bullet list (u9df)** — now renders as 2 columns matching
   the baseline (was collapsed to a single column last pass).
5. **Body / bullet text on the green panels** — lines wrap at slightly
   different words than the baseline. Cross-renderer line-wrap;
   cosmetically visible but not a template-level defect.
6. **plakat-dunkel back cover (ub34)** — renders as a dark/black panel
   in both baseline and preview (poster artwork is intentionally very
   dark); no issue.
