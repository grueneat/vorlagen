# Review Notes — 26-03-flyer-a6-hochformat-gruenes-cover

## What this template is

A **6-page A6-Hochformat flyer** for Die Grünen, "grünes Cover" variant.
Source: `26-03-Flyer A6 Hochformat gruenes Cover.idml` — a 4-spread
InDesign document (spreads 1 and 4 single-page, spreads 2 and 3
facing-pages with 2 pages each = 6 pages).

Content: page 1 cover (two-line headline "Ich bin eine / Headline." +
Störer badge + Wahlkreis-ellipse ornament + DIE GRÜNEN logo), pages 2-5
inner content (headlines, body paragraphs, bullet lists, Impressum),
page 6 a quote page with the Leonore Gewessler portrait.

It is the A6-Hochformat sibling of `26-03-flyer-a6-hochformat-portrait`
and `26-03-flyer-a6-hochformat-quadrat-in-bild`; the tolerance handling
below mirrors those templates' established, user-reviewed outcome for
the same IDML-import gap classes.

## Scaffold outcome — GREEN

`bin/idml-import --scaffold-only` completed (exit 0). The Stage-1
inventory gate passed: every IDML `<CharacterStyleRange>` run is present
in build.py (`every_idml_run_present_in_build_py: true`), all 3
`<Link>` assets resolve and are on disk (`asset_audit.yml::ok: true`),
build.py runs clean, render produced all 6 pages, and the preview word
count equals the baseline word count (342 == 342, 0 % delta).

**No converter changes were needed** — the facing-pages support,
assets-dir resolution, `# idml-skip:` annotation handling, and
worktree-path fixes landed by batch templates 1-2 already cover this
template. The two `inventory` "dropped elements" (`u141f`, `u1424`) are
off-page registration-mark rectangles the converter deliberately skips
(see tolerance below) — not a structural gap.

`SCAFFOLD_INVENTORY.yml` was committed as the Stage-2 source of truth.

## Tune outcome — RESIDUAL (preflight not green)

`bin/tune-render` → `bin/tune-fix` ran. The playbook loop could not
drive preflight green: `line_spacing_sim` returned no rows for any of
the 12 systematic-audit frames, and `y_mm_shift` found no reliable
calibration frame. The residual is accepted per the overnight gate
policy and the established sibling-template precedent.

Three high-leverage image-frame fixes were made during tuning (all
playbook-class, `frame_visibility`):

- **u13e4 (DIE GRÜNEN logo, page 1)** — was `inline_image_data` PNG +
  `scale_type=1` + `local_scale`/`local_offset_mm`; rendered fully
  transparent under the Scribus 1.6.x SCALETYPE=1 bug (preview ink
  density 0.0). Switched to a direct `image=` reference
  (`gruene-logo-bund-weiss-cmyk.png`) + `scale_type=0`. Logo now
  renders correctly.
- **u1260 (pine-forest photo, page 5)** — was `scale_type=1` +
  `local_scale`/`local_offset_mm`; rendered invisible (ink density
  0.0) under the same bug. Switched to `scale_type=0`. Photo now
  renders correctly.
- **u145b (Leonore portrait, page 6)** — switched `scale_type=1` +
  `local_*` to `scale_type=0`; frame now renders (positioned and
  cropped correctly). The colour distortion that remains is the
  separate CMYK-PSD authoring-bug below.
- **2× `# noinject:` markers** added above the `u1260` and `u145b`
  ImageFrame `add()` calls — both are real IDML-placed content photos,
  not demo placeholders. Cleared `external_asset_substitution_audit`.

## Tolerances granted (7 entries — see TOLERANCE_LOG.md / TOLERANCES.yml)

No `brand_overrides`, `non_ci_*`, or `meta.yml` numeric growth was
required (parity with the flyer siblings — `check_ci` is `ok: true`
warnings-only, `region_color_audit` and `run_style_audit` are green).
All 7 tolerances live in `TOLERANCES.yml`:

| id | audit | severity | cap | classification |
|----|-------|----------|-----|----------------|
| `tol:inventory-offpage-registration-marks` | inventory | cosmetic | 2 | human-review |
| `tol:image-audit-vector-path-delta` | image_audit | cosmetic | 45 | scribus-engine-bug |
| `tol:text-position-jitter-freetype-kerning` | text_position_audit_jitter | cosmetic | 40 | scribus-engine-bug |
| `tol:text-position-structural-cross-renderer-wrap` | text_position_audit_structural | structural | 260 | scribus-engine-bug |
| `tol:systematic-text-line-count-divergence` | systematic_text_audit | structural | 12 | scribus-engine-bug |
| `tol:image-content-leonore-cmyk-psd-conversion` | image_content_audit | structural | 1 | authoring-bug |
| `tol:visual-diff-image-size-mismatch` | visual_diff_regions | cosmetic | 0 | scribus-engine-bug |

The 3 `cosmetic` entries (inventory, image_audit, jitter) flip their
audits green. The 3 `structural` entries (structural text drift,
systematic text, image_content) are **documented only** — they keep
preflight RED on purpose. The `visual_diff_regions` entry documents a
phase error that is a hard red regardless of tolerances.

## Residual drift numbers (final preflight)

| Audit | Issues | Status |
|-------|--------|--------|
| `text_position_audit_structural` | 254 large drifts (>5pt) | accepted — cross-renderer line-wrap divergence |
| `systematic_text_audit` | 12 frames (line-count differs) | accepted — same wrap divergence, per-frame |
| `image_content_audit` | 1 broken (u145b) | accepted — CMYK-PSD authoring-bug |
| `visual_diff_regions` | phase error (1px size mismatch) | accepted — pdftocairo DPI rounding |
| `image_audit` | 41 vector-path delta | green via tolerance (cap 45) |
| `text_position_audit_jitter` | 31 sub-perceptible (≤5pt) | green via tolerance (cap 40) |
| `inventory` | 2 dropped (u141f, u1424) | green via tolerance (cap 2) |
| green outright | asset_extraction, external_asset_substitution, font_audit, run_style, text_audit, text_render, region_color, image_frame_visibility, line_spacing | — |

The Stage-2 inventory gate (`inventory_compare`) exits 0 (match) — no
structural regression: every run, frame anname, colour and word is
preserved from the scaffold snapshot.

## human-review / authoring-bug items

- **u145b — CMYK-PSD colour distortion (authoring-bug).** The page-6
  portrait `2026-03-Leonore für Flyer.psd` is a **CMYK-mode** Photoshop
  document. The Stage-1 asset pipeline (`shared/assets/<slug>/
  links_export.yml` recipe `convert -flatten`) flattened it to RGB PNG
  WITHOUT an ICC-aware CMYK→RGB conversion, producing a posterized
  rainbow distortion. This is the documented shared PSD→PNG CMYK→RGB
  conversion bug confirmed on batch templates 1-2. Per the overnight
  brief this is NOT a converter fix — the frame renders and is
  positioned correctly; only the pixels are wrong. The fix belongs
  upstream in `tools/links_export.py` (the `raster_psd` recipe needs an
  ICC CMYK→RGB step).
- **u141f / u1424 — off-page registration marks (human-review).** Two
  5.2×5.1mm Rectangle elements the IDML places ~26mm off the left page
  edge. The converter correctly skips them; InDesign also omits them
  from the trimmed PDF. The inventory audit counts them as "dropped"
  — correct, conservative behaviour, no action needed.
- **Cross-renderer line-wrap divergence (engine-bug, follow-up).**
  Scribus and InDesign break justified body/bullet paragraphs at
  slightly different words; one wrap point cascades into 254 reported
  word drifts. Not converter-fixable; needs Scribus
  justification/hyphenation alignment or a baseline re-flow.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 1 (cover)** — confirm the **DIE GRÜNEN logo** renders (white
   "G" + "DIE GRÜNEN" wordmark, centred below the subheadline). This
   was invisible before the u13e4 fix. Also confirm the Störer badge
   and the headline are present. The Wahlkreis-ellipse ornament around
   "eine" renders **black/outline** in preview vs **yellow** in the
   baseline — a vector-path/colour rendering difference (covered by
   `tol:image-audit-vector-path-delta`).
2. **Page 5** — confirm the **pine-forest photo** fills the top band
   (was invisible before the u1260 fix).
3. **Page 6** — the **Leonore portrait** renders but with **wrong,
   posterized rainbow colours**. This is the known CMYK-PSD
   authoring-bug — eyeball that the framing/crop is correct; the colour
   is expected to be wrong until the asset pipeline is fixed upstream.
4. **Body / bullet-list paragraphs (pages 2-4)** — expect line breaks
   to fall at slightly different words than the baseline (e.g. page-3
   bullet 1 wraps to 3 lines in preview vs 2 in the baseline). This is
   the accepted cross-renderer wrap divergence — check the *text* is
   complete and correct, not the exact wrap column.
5. **Facing-pages routing** — pages 3 and 5 are the right-hand pages of
   the two facing-pages spreads. Confirm each shows its own content (a
   wrong-page content leak would show here first).
