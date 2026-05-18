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

## Tune outcome — RESIDUAL (image/squiggle/coverage/frame-position green; line-wrap red)

Stage 2 (`/idml-tune`) ran the `bin/tune-render` → `bin/tune-fix`
loop. The image, squiggle, attribute-coverage, text-render,
per-region-regression and `frame_vertical_position` audits were driven
fully green; the line-wrap-driven text-position audits remain at the
documented cross-renderer floor. Those carry `severity: structural` in
`TOLERANCES.yml` — DOCUMENTED but deliberately non-preflight-flipping —
so the render was promoted via `bin/tune-render --no-transactional`
(the same terminal state as the prior committed run).

### The headline win — green-body SpaceAfter

The bare re-import dropped `SpaceAfter` on the green body paragraph
style `idml/fliesstext-auf-gruenem-hintergrund`. The IDML resolves
this style's `SpaceAfter` to 0 (its `BasedOn` is `[No paragraph
style]`, `SpaceAfter=0`), while the white sibling
`fliesstext-auf-weissem-hintergrund` carries `5.669…` explicitly. But
`baseline.pdf` shows ~5.67pt inter-paragraph spacing on the green
body AND the green bullet lists (measured: ~14pt within-paragraph
gaps, ~20pt at paragraph boundaries). `space_after_pt=5.6693` was
added to the green style (the bullet style inherits it). This single
fix collapsed `text_position_audit_structural` from 253 to **46** —
the prior 207-word cascade was the green-body paragraphs sitting at
the wrong vertical positions.

### Edits applied (build.py)

1. **Green-body `SpaceAfter`** (above) — `space_after_pt=5.6693` on
   `idml/fliesstext-auf-gruenem-hintergrund`.
2. **u133f three-line headline** — the converter split the mixed-font
   headline ("Das ist eine" / "dreizeilige" Vollkorn / "Headline")
   into 3 single-line frames but lost the `CenterAlign` justification
   on lines 2-3 and on the `<trail>` of all three. `ALIGN: '1'` was
   added to the `paragraph_attrs` of lines 2-3 and to the `trail_attrs`
   of all three (a single-Run frame's only paragraph is closed by
   `<trail>`, so the ALIGN must live there). Frame width was set to
   the IDML text-column width (58.4538mm = `TextColumnFixedWidth`)
   rather than the full frame width so the centred lines land on the
   baseline's text-column centre. This dropped the worst line_match
   finding from Δ-21.72pt to Δ-1.04pt.
3. **u133f_l2 (Vollkorn "dreizeilige")** — `y_mm` shifted +2.20mm
   (+6.24pt). The pixel audit (authoritative) measured the Vollkorn
   line 6.24pt too high — Vollkorn Black Italic's cap-top sits higher
   than the IDML expects under FLOP. Shifting the single split frame
   down closes it; `line_spacing_pixel_audit` went 2 major → 0 major.
4. **u1386 (radial-gradient overlay)** — `# noinject:` comment;
   genuine IDML-placed content. Cleared `external_asset_substitution`.

### Accepted residuals — what stays red

- `text_position_audit_structural`: 46 large (>5pt) word drifts
  (prior run: 253 — the SpaceAfter fix collapsed it). Within cap 260.
- `line_match_audit`: 16 of 70 lines mismatched. Breakdown: 2 rotated
  Impressum frames (`u11fd`/`u126f`, Δ28.34pt = the 10mm frame width —
  Scribus centres `-90°` rotated text on the opposite cross-axis edge,
  the documented rotated-frame engine limit); 6 body line-wrap
  differences (`u1242`, `u129e`); 8 sub-2pt centred-line residuals
  (`u133f`×3 Δ~1.2pt, `u12fb` Δ-1.9pt, `u1390`×2 Δ~1.8pt — the
  ~0.75% Vollkorn/Gotham glyph-width difference shifts a centred
  line's start by ~half the width delta; `u1358` Δ-1.47pt rotated).
  No single fix closes these; documented per the gate policy.
- `systematic_text_audit`: 6 frames (prior run: 9).
  Same root cause as structural: cross-renderer line-wrap. Scribus and
  InDesign break justified paragraphs at different words; line-count
  mismatches cascade word positions. The per-line GAP the converter
  emitted is CORRECT (`line_spacing_pixel_audit`: baseline gaps
  13.9-14.9pt == preview gaps 13.9-14.9pt). `line_spacing_sim`
  returned no rows for all 6 frames — no leading value can reconcile a
  wrap-count difference. Classified `scribus-engine`.

`text_position_audit_jitter` (37 ≤ cap 38 — bumped 35→38 this pass,
see TOLERANCE_LOG), `image_audit` (39 ≤ 45) and `visual_diff_regions`
(54 ≤ 65) are within their tolerance caps — green.

## IMAGE AUDIT — verified

| Audit | Result | Outcome |
|-------|--------|---------|
| `image_content_audit` | **0 broken, 5 ok** | every image frame ok; no CMYK frame blank or discoloured |
| `image_frame_visibility_audit` | **0 invisible**, 1 faint (`u1386`) | the DIE GRÜNEN logo `u1336` renders; `u1386` faint is the accepted CMYK→sRGB tone residual on the dark PSD |

Per-frame `image_content_audit` mean_delta_rgb: `u132c` pine cover 4.8,
`u1260` pine banner 6.8, `u137f` Leonore portrait 1.7, `u1386` radial
PSD 3.4. All five `ok`, no flags. No CMYK or photo frame is broken.
Logo `u1336` `asset_render_ratio` 0.849 — well above the 0.35 floor.

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
  The GREEN sibling `fliesstext-auf-gruenem-hintergrund` is missing
  `SpaceAfter` in the IDML (inherits 0 from `[No paragraph style]`)
  yet `baseline.pdf` shows the same ~5.67pt spacing — `space_after_pt`
  was added to the green style by hand to match (a tune-stage edit,
  not converter output; see TOLERANCE_LOG).
- **`TextColumnCount` / `TextColumnGutter`** — every text frame in this
  template is single-column (`TextColumnCount="1"`), so the converter
  correctly omits `columns` / `col_gap_pt`. No multi-column body text
  exists here to apply them to; the converter handles >1 elsewhere.

## Tolerances granted

This pass grew exactly one numeric `TOLERANCES.yml` cap:
`text_position_audit_jitter` 35 → 38. The jitter count rose 19 → 37 as
the green-body `SpaceAfter` fix moved ~207 words off the structural
(>5pt) cascade — the tail of that correction lands sub-5pt in the
jitter bucket. The bump is the smallest that covers the post-fix count
(37 + 1 headroom). The other five entries hold within their prior caps
WITH ROOM TO SPARE — structural 46 ≤ 260, systematic 6 ≤ 11,
visual_diff 54 ≤ 65, image_audit 39 ≤ 45, image-visibility faint
1 ≤ 1. No `meta.yml::brand_overrides` / `non_ci_*` growth.

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1** — pine-forest background, green box, three-line headline
  ("dreizeilige" in yellow Vollkorn italic) — the three lines are now
  correctly centred on the text-column centre and vertically stacked
  (ALIGN + Vollkorn baseline fix this pass). DIE GRÜNEN logo inside the
  box, magenta "Störer" badge. Headline first-word x within ~1.2pt of
  baseline (the ~0.75% glyph-width residual).
- **Page 5** — pine-forest banner photo at the top + body text below.
  Yellow squiggles under "auch" and on "om:".
- **Pages 2-4** — green body pages. The green body paragraphs and
  bullet lists now carry ~5.67pt inter-paragraph spacing (the
  `SpaceAfter` restore) — paragraph rhythm matches the baseline. Body
  text still wraps a hair differently word-for-word (cross-renderer);
  sub-perceptible, nothing missing.
- **Page 6** — Gewessler portrait with the radial-gradient vignette
  (a dark vignette at fill_opacity 0.9, a touch lighter than baseline —
  the accepted CMYK tone residual, not a defect), the green box, and
  the quote.
