# Review Notes — 26-03-flyer-a6-hochformat-portrait

## What this template is

A **6-page A6 portrait flyer** (105 × 148 mm trim) for Die Grünen. Source:
`26-03-Flyer A6 Hochformat Portrait.idml`. The IDML is a 4-spread document:
spread 1 and spread 4 are single-page (cover, back), spreads 2 and 3 are
**facing-pages spreads** with 2 pages each — 6 pages total.

Content: page 1 cover (three-line headline + Störer badge + Gewessler portrait
photo), pages 2–5 inner content (headlines, bullet lists, Impressum), page 6 a
quote page.

## Scaffold outcome — GREEN

`bin/idml-import --scaffold-only` completed (exit 0), Stage-1 inventory gate
passed, `SCAFFOLD_INVENTORY.yml` written, `build.py` runs clean and renders all
6 pages. Reaching GREEN required four converter / driver fixes (all in Stage 1,
where converter edits are permitted):

1. **`--assets-dir` default was a stale hardcoded path** from a previous
   template's import. Changed to `None`, resolved post-parse to the IDML's
   own sibling `Links/` directory so multi-template runs are independent.
2. **`_emit_pages` only handled one-page-per-spread documents** — it raised
   `UnhandledElement` on this 6-page / 4-spread layout. Added facing-pages
   support: iterate every `<Page>` in each spread, route each top-level
   PageItem to the page whose page-local bbox centre contains it
   (`_route_item_to_page`), emit one `_add_page_<i>` per page with the global
   index matching `pkg.pages` document order.
3. **Driver path bugs in a git worktree** — `from tools import …` failed
   (repo root not on `sys.path`); `render_pipeline.py` had 5 hardcoded
   `/workspace/templates` literals; `inventory_extract` defaulted to
   `/workspace/templates`. Fixed to resolve against the running checkout's
   `ROOT`.
4. **Stage-1 gate did not understand deliberate converter skips.** The
   converter now writes `# idml-skip: <self_id> — <reason>` lines into
   build.py; the gate reads them so an off-page registration mark and an
   unused IDML paragraph style no longer trip the gate as "missing".

## Tune outcome — RESIDUAL (preflight not green)

`bin/tune-render` → `bin/tune-fix` ran. The playbook loop could not drive
preflight green; the `y_mm_shift` playbook oscillated (a 2-cycle limit cycle)
on several body frames. The residual is accepted per the overnight gate policy.

Two high-leverage fixes were made during tuning before accepting the residual:

- **Baseline trim-normalization (driver, Stage 1).** The IDML's sibling
  `baseline.pdf` was exported by InDesign **with printer's marks + 3 mm
  bleed** baked into a 356.65 × 496.53 pt MediaBox, while the converter
  (correctly, per corpus convention) emits a trim-only 297.64 × 419.53 pt
  preview. Comparing the two made *every* word read as drifted (328 drifts)
  and the marks-area furniture text read as 15 "missing words" with a phantom
  `Helvetica` font failure. Added `_detect_trim_box` + `_normalize_baseline_to_trim`
  to the scaffold driver: it finds the trim box from the crop marks and crops
  the baseline to trim-only with Ghostscript so it page-matches the preview.
  Effect: word drift 328 → ~290, vector delta 558 → 40, missing-words 15 → 0,
  `font_audit` now green.
- **Frame `u1175` height clamp (build.py, Stage 2).** The cover's three-line
  headline frame was over-inflated by the converter's Pattern-9 auto-adjust
  (it counted empty `para`-separator Runs as text lines → 232 pt instead of
  ~99 pt). At y_mm 90.12 a 232 pt frame overflowed page 1 and Scribus rendered
  the spill onto **PDF page 3**. Clamped `h_mm` to 52 mm — fits all 3 headline
  lines, keeps the frame inside page 1. Page 3 now shows the correct content.
- **`# noinject:` on 4 ImageFrames** — the real IDML-placed content photos;
  cleared `external_asset_substitution_audit`.

## Tolerances granted

See `TOLERANCE_LOG.md` and `TOLERANCES.yml` for the full table. Summary:

- **2 per-template build.py changes**: u1175 height clamp; 4× `# noinject:`.
  Neither grows a numeric tolerance.
- **5 accepted residuals** in `TOLERANCES.yml`: structural text-position
  drift (255), jitter (35), image-content (3 frames), image-audit (40 vector
  delta), inventory (1 off-page mark). All classified `scribus-engine-bug` or
  `human-review` — none is an unfixed converter bug.
- **No `brand_overrides`, `non_ci_*`, or numeric tolerance growth** was
  required. `region_color_audit` and `run_style_audit` are green.

## Residual drift numbers (final preflight)

| Audit | Issues | Status |
|-------|--------|--------|
| `text_position_audit_structural` | 255 large drifts (>5pt) | accepted — cross-renderer line-wrap divergence |
| `text_position_audit_jitter` | 35 sub-perceptible (≤5pt) | accepted — sub-visible jitter |
| `systematic_text_audit` | 11 frames | accepted — same frames as jitter |
| `image_content_audit` | 3 broken (u1164, u1260, ubc2) | accepted — Scribus SCALETYPE |
| `image_frame_visibility_audit` | 2 invisible (u116b, u1260) | accepted — Scribus SCALETYPE |
| `image_audit` | 40 vector-path delta | accepted — raster + ICC |
| `inventory` | 1 dropped (u1152) | accepted — off-page registration mark |
| green | asset_extraction, external_asset_substitution, font_audit, run_style, text_audit, text_render, region_color, line_spacing | — |

## human-review / authoring-bug items

- **`u1152` (authoring / human-review)** — an off-page magenta registration
  mark in the IDML. Correctly skipped by the converter; counts as a "dropped
  element" in the inventory audit. No action needed — it is printer furniture.
- **Converter Pattern-9 over-inflation (follow-up)** — the auto-height
  heuristic counts empty `para`-separator Runs as text lines. Worked around
  per-template here (u1175); the converter heuristic should be corrected
  upstream so future imports don't need the manual clamp.
- **`y_mm_shift` playbook oscillation (follow-up)** — the playbook ping-pongs
  on frames whose drift sign flips each render. It needs an oscillation guard.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 1 (cover)** — confirm the three-line headline "Das ist die /
   dreizeilige / Headline" sits fully inside the page and does **not** spill
   below the page edge. This was the frame-overflow bug; verify the clamp held.
2. **Page 3 and page 5** — these are the right-hand pages of the two
   facing-pages spreads. Confirm each shows its **own** content (page 3 =
   "Ich bin auch eine Headline" + bullet list; page 5 = the other inner
   spread). The facing-pages routing is new code — a wrong-page leak would
   show here first.
3. **Bullet-list paragraphs (pages 3, 5)** — expect the line breaks to fall
   at slightly different words than the baseline; this is the accepted
   cross-renderer wrap divergence, not a content error. Check the *text* is
   complete and correct, not the exact wrap column.
4. **Images** — `u1164` (radial gradient overlay, page 1), `u1260` (pine
   forest, page 5), `ubc2` (dark plakat background, page 6): these may render
   faint / wrong in Scribus. Confirm against baseline whether the design
   intent survives; this is the Scribus SCALETYPE limitation.
5. **Page geometry** — both PDFs should now be 297.6 × 419.5 pt (A6 trim).
   The baseline was cropped from a marks-on 356.6 × 496.5 pt export.
