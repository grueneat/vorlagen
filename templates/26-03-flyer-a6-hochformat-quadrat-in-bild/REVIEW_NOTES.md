# Review Notes — 26-03-flyer-a6-hochformat-quadrat-in-bild

Prose summary for a human reviewer. Read alongside `TOLERANCE_LOG.md`
(every edit + accepted residual) and `TOLERANCES.yml` (structured).

This is the **combined-fidelity re-render pass** (template 2 of 8). The
template was re-imported to pick up the full converter/tooling fix set:
CMYK→sRGB conversion, deterministic aspect-fill crop, squiggle colour +
re-anchoring, the five newly-consumed Tier-A attributes (`SpaceAfter`,
`BlendingSetting/Opacity`, `VerticalJustification`, `TextColumnCount`,
`TextColumnGutter`), the ground-truth squiggle alignment audit, the
attribute-coverage gate (Phase E5f), and the R5 converter fix from
template 1's re-render (trailing-`<Br/>` no longer doubles the
paragraph break).

## What this template is

A 6-page A6 portrait flyer ("Flyer A6 Hochformat — Quadrat in Bild"),
imported from `26-03-Flyer A6 Hochformat Quadrat in Bild.idml`. Trim
~99 × 140 mm per page.

Layout: page 1 cover (pine-forest photo full-bleed, green box with a
three-line headline + DIE GRÜNEN logo, magenta "Störer" badge); pages
2-4 green-background body pages with headlines, justified body text and
bullet lists; page 5 a pine-forest banner photo + body text; page 6 a
Gewessler portrait photo with a quote, a green "Headline in einem
grünen Kasten" box, and a radial-gradient vignette overlay. All body
copy is lorem-ipsum placeholder text (the IDML ships it that way).

## Re-import outcome — GREEN

Stage 1 (`/idml-scaffold --reimport`) regenerated `build.py` from the
fully-fixed converter, overwriting the prior pass's `build.py` as
intended.

- Asset audit `ok: true` — all 4 `<Link>` files resolved and converted
  (pine-forest JPG, Gewessler JPG, radial-gradient PSD, DIE GRÜNEN AI
  logo). No missing assets — no BLOCKED condition.
- The rotated-TextFrame converter fix from the prior pass is carried by
  the committed converter; the Impressum frames (`u11fd`, `u126f`) did
  not re-clip this pass.
- Inventory gate: after the three build.py re-applied edits (below),
  `inventory_compare` exits 0 — a perfect match against the committed
  `SCAFFOLD_INVENTORY.yml`. The bare re-import (pre-edits) had a 2-word
  regression (`maioriat` clipped); the `u12b5` widening restored parity.

## Tune outcome — RESIDUAL (image/squiggle/coverage green; text-position red)

Stage 2 (`/idml-tune`) ran the `bin/tune-render` → `bin/tune-fix`
loop. The image, squiggle, attribute-coverage and text-render audits
were driven fully green; the two text-position audits remain at the
documented cross-renderer line-wrap floor. Those two carry
`severity: structural` in `TOLERANCES.yml` — DOCUMENTED but
deliberately non-preflight-flipping — so the render was promoted via
`bin/tune-render --no-transactional` (the same terminal state as the
prior committed run, which also shipped with a red preflight).

### Edits applied (build.py — see TOLERANCE_LOG rows 2-4)

The combined-fidelity re-import regenerated `build.py` from the
converter and dropped the prior tune's three hand-edits; they were
re-applied:

1. **u1336 (DIE GRÜNEN logo)** — swapped `inline_image_data` +
   `scale_type=1` → `image=` ref + `scale_type=0`. The white-on-
   transparent RGBA logo was fully invisible under the inline path
   (known Scribus 1.6.x bug); it now renders inside the green box on
   page 1. The `bin/tune-fix` `frame_visibility` playbook escalated
   (could not auto-resolve the asset basename), so the documented swap
   was applied by hand.
2. **u1386 (radial-gradient overlay)** — added a `# noinject:`
   comment. It is genuine IDML-placed content, not a demo placeholder.
   Cleared `external_asset_substitution_audit`.
3. **u12b5 (page 4 body text)** — `h_mm` widened 63.5mm → 71.0mm.
   At the IDML `h_mm` Scribus wraps the justified body to 12 lines vs
   InDesign's 11; the last line ("…sed maioriat fuga.") fell below the
   frame and clipped, dropping 2 words. The widening clears the
   overflow. The prior pass widened to 74.79mm — this pass needs less
   (+7.5mm vs +11.3mm) because the R5 trailing-`<Br/>` converter fix
   removed the doubled empty paragraphs that previously inflated the
   line count.

### Accepted residuals — what stays red

- `text_position_audit_structural`: 253 large (>5pt) word drifts
  (prior run: 254).
- `systematic_text_audit`: 9 frames (prior run: 10).
  Both are the SAME root cause: cross-renderer line-wrap. Scribus and
  InDesign break justified paragraphs at different words; line-count
  mismatches (u1242 16→17, u129e 10→9, u12b5 11→12) cascade word
  positions. The per-line GAP the converter emitted is CORRECT
  (`line_spacing_pixel_audit`: baseline gaps 13.9-14.9pt == preview
  gaps 13.9-14.9pt). `line_spacing_sim` returned no rows for all 9
  frames — no leading value can reconcile a wrap-count difference.
  Classified `scribus-engine`.

`text_position_audit_jitter` (19), `image_audit` (39) and
`visual_diff_regions` (59) are within their tolerance caps — green.

## IMAGE AUDIT — verified

| Audit | Result | Outcome |
|-------|--------|---------|
| `image_content_audit` | **0 broken, 5 ok** | every image frame ok; no CMYK frame blank or discoloured |
| `image_frame_visibility_audit` | **0 invisible**, 1 faint (`u1386`) | the DIE GRÜNEN logo `u1336` renders; `u1386` faint is the accepted CMYK→sRGB tone residual on the dark PSD |

Per-frame `image_content_audit` mean_delta_rgb: `u132c` pine cover 4.8,
`u1260` pine banner 7.1, `u137f` Leonore portrait 1.7, `u1386` radial
PSD 3.5. All five `ok`, no flags. No CMYK or photo frame is broken.

## SQUIGGLE AUDIT (ground-truth) — verified

`squiggle_alignment_audit`: `ok: true`, 0 issues. All 8 squiggle
PolyLines carry `fill='Gelb'` (yellow). The audit reports every
squiggle `status: ok` with `vgap_mm` ≈ 0 and healthy `hoverlap_mm` —
the squiggles render yellow and sit on their words (verified visually
on pages 5/6: yellow underline under "auch" / on "om:").

## COVERAGE GATE (Phase E5f) — verified

`idml_attribute_coverage`: `ok: true`, 0 issues — "all significant
unconsumed attributes accounted for (920-entry baseline)". No new
significant unconsumed attribute.

## The five new attributes in this template

- **`BlendingSetting/Opacity`** → `fill_opacity` 0.7 / 0.7 / 0.9 on 3
  frames. `u1386` (the radial vignette behind the page-6 quote) at 0.9
  — the vignette renders translucent, matching the IDML `Opacity="90"`.
- **`VerticalJustification`** ("CenterAlign") → `vertical_text_align=1`
  → SLA PAGEOBJECT `ALIGN="1"` on the two rotated Impressum frames
  `u11fd` / `u126f` — their text is vertically centred in the frame.
- **`SpaceAfter`** → `space_after_pt=5.6693` on the
  `fliesstext-auf-weissem-hintergrund` body paragraph style → SLA
  STYLE `NACH="5.6693"`: paragraph spacing below the white-background
  body paragraphs (matches the IDML style's `SpaceAfter="5.669…"`).
- **`TextColumnCount` / `TextColumnGutter`** — every text frame in this
  template is single-column (`TextColumnCount="1"`), so the converter
  correctly omits `columns` / `col_gap_pt`. No multi-column body text
  exists here to apply them to; the converter handles >1 elsewhere.

## Tolerances granted

This pass: one new build.py edit row (TOLERANCE_LOG row 4 — the `u12b5`
`h_mm` widening, classified scribus-engine, resolves the text loss; it
is an edit, not an audit-cap residual). No new `TOLERANCES.yml`
audit-cap entries, no numeric growth — the six existing entries
(structural 253 ≤ 260, jitter 19 ≤ 35, systematic 9 ≤ 11,
visual_diff 59 ≤ 65, image_audit 39 ≤ 45, image-visibility faint 1 ≤ 1)
all hold within their prior caps. No `meta.yml::brand_overrides` /
`non_ci_*` growth.

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1** — pine-forest background, green box, three-line headline
  ("dreizeilige" in yellow Vollkorn italic), DIE GRÜNEN logo inside the
  box (renders — was invisible under the inline path), magenta "Störer"
  badge. Headline wraps a hair differently (cross-renderer).
- **Page 5** — pine-forest banner photo at the top + body text below;
  the body ends with "…sed maioriat fuga." fully visible (the `u12b5`
  widening). Yellow squiggles under "auch" and on "om:".
- **Pages 2-4** — green body pages. Content and layout match; body
  text wraps a hair differently and sits slightly higher (Scribus vs
  InDesign metrics). Sub-perceptible; nothing missing.
- **Page 6** — Gewessler portrait with the radial-gradient vignette
  (a dark vignette at fill_opacity 0.9, a touch lighter than baseline —
  the accepted CMYK tone residual, not a defect), the green box, and
  the quote.
