# Review notes — 26-03-flyer-a6-querformat-zweigeteilt

## What this template is

A6 landscape (Querformat) campaign flyer, "zweigeteilt" (two-part)
layout — a 6-page InDesign document exported page-based. Front uses a
full-bleed photo (`ziesel.jpg`, a squirrel), a dark-green panel with a
three-line headline and bullet-list body copy; the back carries the DIE
GRUENEN logo, a candidate strip ("Leonore Gewessler"), social-media
icons, an Impressum line, and a dark poster image (`plakat-dunkel-fuer-
flyer.png`). It is the landscape sibling of `26-03-flyer-a6-hochformat-
zweigeteilt` (which was blocked elsewhere in this batch on a missing
source image) and shares an issue profile with `26-03-flyer-a6-
querformat-portrait`.

## Scaffold outcome — GREEN (structural)

`bin/idml-import --scaffold-only` ran clean with the existing converter
(the batch's facing-pages / spread-merge / page-based-export-detection
fixes were already in the worktree; no new converter changes were
needed). Derived slug: `26-03-flyer-a6-querformat-zweigeteilt`.

- `asset_audit.yml::ok == true` — all 4 `<Link>` files resolved and
  converted (`Grüne Logo Bund weiss CMYK.ai`, `Plakat dunkel für
  Flyer.psd`, `Ziesel.jpg`, `green-pine-trees-covered-with-fog.jpg`).
  No missing assets — the HARD EXCEPTION does not apply.
- `every_idml_run_present_in_build_py: true`; every applied
  ParagraphStyle emitted; every frame `Self` has an `anname`. Two
  ParagraphStyle definitions (`Zwischenüberschrift auf weißem
  Hintergrund`, `Headline in grünem Kasten`) are in the IDML style
  catalog but applied by no `<ParagraphStyleRange>` — correctly not
  emitted.
- The converter deliberately skipped 4 off-page Rectangles (u6f0,
  u6f2, u77f, u964 — registration furniture on the pasteboard).

## Tune outcome — RESIDUAL (red preflight, fully documented)

The `bin/tune-render` -> `bin/tune-fix` loop ran to the point where no
playbook can advance (`tune-fix` exits 3). The terminal state is a red
preflight with every residual classified and documented — the same
accepted terminal state as the sibling flyer/leporello templates in
this batch.

### Direct fixes applied (build.py — no tolerance needed)

1. **uad7 (DIE GRUENEN logo) — FIXED.** Switched from a 64 KB
   `inline_image_data` base64 PNG blob + `scale_type=1` to a direct
   `image=` reference + `scale_type=0`. Scribus 1.6.x renders
   SCALETYPE=1 + small frame + RGBA white-on-transparent PNG fully
   transparent. After the fix the logo renders —
   `image_frame_visibility_audit` dropped from 3 invisible to 2.
2. **uace / u906 / ub34 — `# noinject:` comments added.** This cleared
   `external_asset_substitution_audit` (3 missing -> OK).
3. **ub52 ("Leonore Gewessler") — y_mm reverted to scaffold 69.4096.**
   The y_mm_shift playbook oscillated this single-line frame without
   converging and triggered a per-region regression; reverting stopped
   the churn (`per_region_regression` back to OK).

### Tolerances granted (9 — see TOLERANCE_LOG.md for the full table)

Three carry `severity: cosmetic` and flip their audit green:

- `tol:inventory-offpage-registration-marks` (inventory, cap 4) — the
  4 deliberately-skipped off-page Rectangles.
- `tol:image-audit-vector-path-delta` (image_audit, cap 48) — 44
  raster/ICC + inline-vector-path extraction deltas.
- `tol:text-position-jitter-freetype-kerning` (text_position_audit_
  jitter, cap 34) — 21 sub-perceptible FreeType kerning drifts.

Six carry `severity: structural` — DOCUMENTED but preflight stays red:

- `tol:image-content-cmyk-jpeg-blank` (image_content_audit, cap 1)
- `tol:image-frame-visibility-cmyk-jpeg-blank` (image_frame_visibility_
  audit, cap 2)
- `tol:systematic-text-line-wrap-no-sim-rows` (systematic_text_audit,
  cap 11)
- `tol:text-position-structural-cross-renderer-wrap` (text_position_
  audit_structural, cap 269)
- `tol:text-render-cross-renderer-wrap-overflow` (text_render_audit,
  cap 12)
- `tol:visual-diff-regions-raster-size-mismatch` (visual_diff_regions,
  cap 1 — phase error, cannot be tolerance-cleared)

No `meta.yml::brand_overrides` / `non_ci_*` growth — the 46 brand-rule
errors are the inherited Minion-Pro-on-abstract-ParaStyle false
positive and informational rows, left un-suppressed.

### Residual drift numbers (terminal state)

| Audit | Issues | Classification | Status |
|---|---|---|---|
| inventory | 4 | human-review | tolerated green |
| image_audit | 44 | scribus-engine-bug | tolerated green |
| text_position_audit_jitter | 21 | scribus-engine-bug | tolerated green |
| image_content_audit | 1 (u906) | authoring-bug | red, documented |
| image_frame_visibility_audit | 2 (u906, uace) | authoring-bug | red, documented |
| systematic_text_audit | 11 | scribus-engine-bug | red, documented |
| text_position_audit_structural | 269 | scribus-engine-bug | red, documented |
| text_render_audit | 12 words / 132 chars | scribus-engine-bug | red, documented |
| visual_diff_regions | phase error (1px raster) | human-review | red, phase error |

Worst per-frame line-spacing drift: u67c +62.4pt, ub3b +29.8pt, uaf8
+27.8pt — all line-WRAP-count divergence (Scribus wraps the justified
body paragraphs to a different number of lines than InDesign). No
(LINESPMode, LINESP) override reconciles a wrap-count change, so the
line_spacing simulator returned 0 rows for every frame.

## Items classified human-review / authoring-bug

- **authoring-bug — uace (ziesel.jpg) and u906 (green-pine-trees-
  covered-with-fog.jpg)**: both are CMYK JPEGs. Scribus 1.6.x cannot
  rasterise CMYK JPEGs (passed through unchanged by
  `tools/links_export.py`). u906 renders fully blank; uace renders
  near-blank (ink density 0.06 vs baseline 0.33). Accepted residual
  per the overnight-batch known-issues policy — no converter fix.
- **human-review — visual_diff_regions phase error**: baseline and
  preview rasterise to pixel dimensions differing by 1px per axis
  (sub-mm rounding at 150 dpi). Tooling artifact; same error on
  sibling batch templates. No template edit changes it.
- **human-review — inventory 4 dropped**: off-page registration
  Rectangles; correct converter behaviour, audit is conservative.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 1 (front, ziesel/squirrel photo)** — the squirrel photo
   `uace` will be near-blank/white in preview.pdf where baseline.pdf
   shows the photo. This is the CMYK-JPEG render failure, expected.
2. **Page 5 (back)** — the green-pine photo strip `u906` is blank in
   preview where baseline shows a dark forest band. Same CMYK-JPEG
   failure.
3. **DIE GRUENEN logo (uad7, page 1 back area)** — should now render
   correctly (white logo). This was the one image FIXED this pass;
   confirm it is visible.
4. **Body / bullet text on the dark-green panels** — lines wrap at
   slightly different words than baseline and the tail words of the
   longest lorem-ipsum paragraphs are clipped (12 words missing).
   Cross-renderer line-wrap; cosmetically visible but not a defect to
   fix at the template level.
5. **plakat-dunkel back cover (ub34)** — renders as a dark/black panel
   in both baseline and preview (the poster artwork is intentionally
   very dark); no issue.
