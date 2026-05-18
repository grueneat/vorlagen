# Review Notes — 26-03-flyer-a6-hochformat-quadrat-in-bild

Prose summary for a human reviewer. Read alongside `TOLERANCE_LOG.md`
(every edit + accepted residual) and `TOLERANCES.yml` (structured).

This is the **image-fidelity re-render pass** (template 2 of 8). The
template was re-imported to pick up the shared CMYK→sRGB conversion
and geometry-derived aspect-fill crop fixes (commit `de96b7c`) plus
the four converter/tooling follow-ups from template 1's re-render
(commit `dcc52c7`). The goal of this pass is to verify the image
fixes landed.

## What this template is

A 6-page A6 portrait flyer ("Flyer A6 Hochformat — Quadrat in Bild"),
imported from `26-03-Flyer A6 Hochformat Quadrat in Bild.idml`. Trim
~99 × 140 mm per page (rendered 297.6 × 419.5 pt after the driver
cropped the printer's-marks baseline to trim box).

Layout: page 1 cover (pine-forest photo full-bleed, green box with a
three-line headline + DIE GRÜNEN logo, magenta "Störer" badge); pages
2-4 green-background body pages with headlines, justified body text and
bullet lists; page 5 a pine-forest banner photo + body text; page 6 a
Gewessler portrait photo with a quote, a green "Headline in einem
grünen Kasten" box, and a radial-gradient vignette overlay. All body
copy is lorem-ipsum placeholder text (the IDML ships it that way).

## Re-import outcome — GREEN

Stage 1 (`/idml-scaffold --reimport`) regenerated `build.py` from the
fixed converter, overwriting the earlier scaffold's `build.py` as
intended.

- Asset audit `ok: true` — all 4 `<Link>` files resolved and converted
  (pine-forest JPG, Gewessler JPG, radial-gradient PSD, DIE GRÜNEN AI
  logo). No missing assets.
- `text_render_audit: OK` — baseline/preview word counts match
  (337 == 337).
- `per_region_regression: OK`.
- Inventory gate: exit 0 after the converter fix (was exit 2 on the
  first re-import attempt — see below).

### Converter fix made in Stage 1

The first re-import attempt FAILED the structural gate: the two
rotated Impressum text frames (`u11fd`, `u126f`, both -90°) clipped
their text — "Impressum: xxxxxx" rendered as "impressu", dropping 2
words (337→335) and tripping `text_render_audit` + a
`per_region_regression`.

Root cause: the `de96b7c`/`5e48f81` rotated-frame branch in the
converter's `_compute_page_local_bbox_pt` emits the *un-rotated* frame
extent + rotation pivot. That model is correct for ImageFrames and for
empty (background-fill) frames — both placed verbatim by the SLA
builder. But the `TextFrame` primitive applies a text-flow W/H swap to
any ±90° frame carrying text (so Scribus computes wrap width from the
visible long edge). Feeding it the un-rotated model AND letting it
swap is a double-correction: the Impressum frame collapsed from a
53.4mm-wide text strip to a 10mm-wide one and clipped.

Fix (`tools/idml_to_dsl.py`, TextFrame emission): for ±90° **non-empty**
TextFrames, convert the un-rotated model to the axis-aligned-bbox-of-
rotated-rect form the primitive's text-swap expects. Closed-form
geometry, scoped to text frames only — ImageFrames and empty frames
keep the un-rotated model. Verified the fix reproduces the pre-
`dcc52c7` working `u11fd` geometry exactly. After the fix the
re-import is structurally green.

## Tune outcome — RESIDUAL (image audits green; text-position red)

Stage 2 (`/idml-tune`) ran the `bin/tune-render` → `bin/tune-fix`
loop. The image audits were driven fully green; the text-position
audits remain at the documented cross-renderer line-wrap floor.

### Edits applied (build.py — see TOLERANCE_LOG rows 2-3)

The re-import dropped the earlier tune's hand-edits; they were
re-applied:

1. **u1336 (DIE GRÜNEN logo)** — swapped `inline_image_data` +
   `scale_type=1` → `image=` ref + `scale_type=0`. The white-on-
   transparent RGBA logo was fully invisible under the inline path
   (known Scribus 1.6.x bug); it now renders inside the green box on
   page 1. The `bin/tune-fix` `frame_visibility` playbook escalated
   (could not auto-resolve the asset basename), so the documented swap
   was applied by hand.
2. **u1386 (radial-gradient overlay)** — added a `# noinject:`
   comment. It is genuine IDML-placed content, not a demo placeholder,
   so the audit's `# noinject:` disposition is correct. Cleared
   `external_asset_substitution_audit`.

Note: the three photo frames (`u132c`, `u1260`, `u137f`) did NOT need
the `# noinject:` / `scale_type=0` edits the prior run applied — the
`de96b7c` crop fix routes them through geometry-derived `crops/*.png`
images that the audits already accept.

### Accepted residuals — what stays red

- `text_position_audit_structural`: 253 large (>5pt) word drifts
  (prior run: 254).
- `systematic_text_audit`: 10 frames.
- `visual_diff_regions`: 59 hot regions.
  All three are the SAME root cause: cross-renderer line-wrap. Scribus
  and InDesign break justified paragraphs at different words; line-
  count mismatches (u1242 16→17, u129e 10→9, u12b5 11→12) cascade word
  positions. The per-line GAP the converter emitted is CORRECT
  (`line_spacing_pixel_audit`: baseline gaps 13.9-14.9pt == preview
  gaps 13.9-14.9pt). `line_spacing_sim` returned no rows for all 10
  frames — no leading value can reconcile a wrap-count difference.
  Classified `scribus-engine`.

`text_position_audit_jitter` (30) and `image_audit` (39) are within
their tolerance caps — green.

## IMAGE AUDIT — before vs after (the goal of this pass)

| Audit | Prior overnight run | This re-render |
|-------|--------------------|----------------|
| `image_content_audit` | 1 broken (`u1386` radial PSD — cyan blob, mean_delta_rgb 102.8) | **0 broken, 5 ok** (`u1386` mean_delta_rgb 4.2) |
| `image_frame_visibility_audit` | 1 invisible (`u1336` logo) | **0 invisible**, 1 faint (`u1386`) |
| `external_asset_substitution_audit` | 4 missing | **0 missing** |
| `visual_diff_regions` | phase-error (ValueError, 1px size mismatch) | runs clean, 59 hot regions — all text-driven |

The image fixes landed:

- **The radial-gradient PSD (`u1386`) is fixed.** The prior run shipped
  it as a pale-blue/cyan blob — the broken CMYK→RGB step turned the
  PSD's near-black corner into cyan. The `de96b7c` ICC-aware CMYK
  conversion brought it to mean_delta_rgb 4.2 (was 102.8). Page 6 now
  shows a dark vignette over the Gewessler portrait, matching the
  baseline. A faint tone residual remains (visibility_ratio 0.681) —
  the small CMYK→sRGB shift the brief classifies as acceptable.
- **The pine-forest photos are fixed.** `u132c` (page 1 cover,
  mean_delta_rgb 5.2) and `u1260` (page 5 banner, 7.1) were washed-out
  / invisible before; the geometry-derived crop now renders them
  correctly.
- **The Gewessler portrait (`u137f`) is fixed** — mean_delta_rgb 2.1,
  excellent.
- **The DIE GRÜNEN logo (`u1336`) renders** — the white-on-transparent
  SCALETYPE invisibility was resolved by the `image=` ref swap.

No CMYK or photo frame is still broken. The worst `visual_diff_regions`
on every page is now a body-TEXT band, not a photo band — confirming
the image frames no longer dominate the visual delta.

## Tolerances granted

Six `TOLERANCES.yml` accepted-residual entries (five `scribus-engine-
bug`, one `human-review` for the `u1386` faint CMYK tone). No
`meta.yml::brand_overrides`, `non_ci_*`, or numeric brand/CI tolerance
growth — `region_color_audit` and `run_style_audit` are green;
`image_audit` (39) is within its existing cap (45).

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1** — pine-forest background (FIXED, was washed-out), green
  box, three-line headline, DIE GRÜNEN logo inside the box (FIXED, was
  invisible), magenta "Störer" badge. Headline wraps a hair
  differently (cross-renderer).
- **Page 5** — pine-forest banner photo at the top (FIXED, was
  invisible) + body text below.
- **Pages 2-4** — green body pages. Content and layout match; body
  text wraps a hair differently and sits slightly higher (Scribus vs
  InDesign metrics). Sub-perceptible; nothing missing. Pages 2-3
  render byte-identical to the prior committed state.
- **Page 6** — Gewessler portrait (FIXED — was discoloured) with the
  radial-gradient vignette (FIXED — was a cyan blob, now a dark
  vignette), the green "Headline in einem grünen Kasten" box, and the
  quote. The vignette is a touch lighter than baseline (the accepted
  CMYK tone residual) but is clearly a dark vignette, not a defect.
