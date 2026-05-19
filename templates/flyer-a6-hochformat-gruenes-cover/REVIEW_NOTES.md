# Review Notes — flyer-a6-hochformat-gruenes-cover

Prose summary for a human reviewer. Read alongside `TOLERANCE_LOG.md`
(every edit + accepted residual) and `TOLERANCES.yml` (structured).

This is the **FINAL re-render pass** (template 3 of 8). The template
was re-imported (`/idml-scaffold --reimport`) to pick up the full
converter/audit fix set at HEAD `5e2cbbf`: CMYK→sRGB + aspect-fill
crop, squiggle colour + re-anchoring, the five consumed Tier-A
attributes, `SpaceAfter`/`FLOP=1`/`min_glyph_shrink`, the four layout
fixes, the mixed-font headline split with corrected Vollkorn
calibration, colour-managed comparison, and the full audit chain incl.
the `split_headline_spacing` hard gate.

It is the A6-Hochformat sibling of `26-03-flyer-a6-hochformat-portrait`
and `26-03-flyer-a6-hochformat-quadrat-in-bild`; the residual handling
below mirrors those templates' established, user-reviewed outcome for
the same IDML-import gap classes.

## What this template is

A **6-page A6-Hochformat flyer** for Die Grünen, "grünes Cover" variant.
Source: `26-03-Flyer A6 Hochformat gruenes Cover.idml` — a 4-spread
InDesign document (spreads 1 and 4 single-page, spreads 2 and 3
facing-pages = 6 pages). Trim ~105 × 148 mm per page.

Content: page 1 cover (two-line mixed-font headline "Ich bin eine /
Headline." + yellow encircling-ellipse squiggle around "eine" + magenta
Störer badge + DIE GRÜNEN logo), pages 2-5 inner content (headlines,
justified body paragraphs, bullet lists, rotated Impressum), page 6 a
quote page with the Leonore Gewessler portrait. All body copy is
lorem-ipsum placeholder (the IDML ships it that way).

## Re-import outcome — GREEN

Stage 1 (`/idml-scaffold --reimport`) regenerated `build.py` from the
fully-fixed converter. `bin/idml-import --scaffold-only` completed
(exit 0).

- Asset audit `ok: true` — all 3 `<Link>` files resolved and converted
  (pine-forest JPG, Leonore PSD, DIE GRÜNEN AI logo). No missing
  assets — no BLOCKED condition.
- Inventory gate: `inventory_compare` exits 0 — a perfect match against
  the committed `SCAFFOLD_INVENTORY.yml` after the build.py re-applied
  edits below. No frame anname, run, colour or style regressed.

## Tune outcome — RESIDUAL (image/squiggle/coverage/image-content green; line-wrap red)

Stage 2 (`/idml-tune`) ran the `bin/tune-render` → `bin/tune-fix` loop.
The image-visibility, squiggle, attribute-coverage, image-content,
text-render and per-region-regression audits were driven fully green;
the line-wrap-driven text-position audits remain at the documented
cross-renderer floor. Those carry `severity: structural` in
`TOLERANCES.yml` — DOCUMENTED but deliberately non-preflight-flipping —
so the render was promoted via `bin/tune-render --no-transactional`
(the same terminal state as the sibling templates and the prior run).

### The headline win — green-body SpaceAfter

The bare re-import dropped `SpaceAfter` on the green body paragraph
style `idml/fliesstext-auf-gruenem-hintergrund`. The IDML's green
`Fließtext` variant carries no `SpaceAfter` (verified in
`Resources/Styles.xml`), while the white sibling `Fließtext auf weißem`
carries `5.669…` explicitly. But `baseline.pdf` shows the same ~5.67pt
inter-paragraph spacing on the green body — measured on page 1 as a
20.0pt paragraph gap vs a 14.3pt line gap = +5.7pt. `space_after_pt=
5.6693` was added to the green style (the bullet style inherits it).
This single fix collapsed `text_position_audit_structural` 152 → **47**
and `systematic_text_audit` 6 → 4. Same fix as siblings 1 and 2.

### Edits applied (build.py)

1. **Green-body `SpaceAfter`** (above) — `space_after_pt=5.6693` on
   `idml/fliesstext-auf-gruenem-hintergrund`.
2. **u13cd / u13cd_l2 split-headline ALIGN + width** — the converter
   splits the mixed-font headline "Ich bin eine" (Gotham Ultra) /
   "Headline." (Vollkorn Black Italic) into two single-line frames but
   loses the IDML `CenterAlign` justification on the `<trail>`
   paragraph (a single-Run frame's only line is closed by `<trail>`,
   so the ALIGN must live there). `ALIGN: '1'` added to `trail_attrs`
   of both frames and to u13cd_l2's Run `paragraph_attrs`. Frame width
   corrected 102mm → 90mm (the IDML `TextColumnFixedWidth` 255.118pt);
   the converter over-widened it, shifting the centred text right.
   Together these closed the two worst `line_match` findings
   (u13cd Δ-24.18pt, u13cd_l2 Δ-33.08pt → matched); line_match 17 → 15.
3. **u13ca squiggle geometry + path** — the re-import converter
   mis-emits this yellow encircling-ellipse Polygon on the IDML
   `[0 -1 -1 0]` ItemTransform: swapped w/h, anchored on the wrong
   corner, kept the raw IDML-local negative-coordinate path, and added
   a redundant `rotation_deg=-90` that the HEAD PolyLine builder
   applies, turning the wide ellipse vertical and dropping it above
   the headline. Restored to an un-rotated wide ellipse at the
   IDML-transform-verified page-local bbox (x 60.097mm, y 43.2715mm,
   w 35.0628 × h 12.4143mm, w/h from the path's own bbox) with the
   path normalised to positive coordinates, `fill='Gelb'`. (Removing
   only the rotation while keeping the raw negative-coord path renders
   the ellipse above the word — both the geometry and the normalised
   path are needed.) The squiggle now encircles "eine", matching the
   baseline (verified visually, `squiggle_alignment_audit` OK).
   **Escalation note:** the rotated-Polygon geometry + raw-path
   mis-emit is a converter regression — Stage 1 should fix
   `tools/idml_to_dsl.py`'s `[0 -1 -1 0]` ItemTransform handling for
   Polygon paths so the re-import emits u13ca correctly without a
   build.py hand-fix.

### Accepted residuals — what stays red

- `text_position_audit_structural`: 47 large (>5pt) word drifts
  (re-import run: 152 — the SpaceAfter fix collapsed it). Within cap
  260. Cross-renderer line-wrap divergence — Scribus and InDesign break
  the justified body/bullet paragraphs at different words; one wrap
  point cascades into dozens of word drifts. `severity: structural`.
- `line_match_audit`: 15 of 71 lines mismatched (was 17 — the
  split-headline ALIGN fix closed the 2 closeable findings). NOT
  tolerance-able per the gate policy; documented as honest residual.
  Breakdown: 2 rotated Impressum frames (`u11fd`/`u126f`, Δ28.34pt =
  the 10mm frame width — Scribus measures `-90°` rotated text from the
  opposite cross-axis edge, the documented rotated-frame engine
  limit); 1 rotated Störer frame (`u1403` Δ-1.48pt); 7 body line-wrap
  differences (`u1242` ×1, `u129e` ×6 cascade); 5 sub-2pt centred-line
  residuals (`u12fb` Δ-1.9pt, `u13eb` ×2 Δ~1.4pt, `u14b1` ×2 Δ~1.8pt —
  the ~0.75% Vollkorn/Gotham glyph-width difference shifts a centred
  line's start by ~half the width delta). No single per-frame fix
  closes any of these — all genuinely-unclosable cross-renderer
  residual. See TOLERANCE_LOG.md for the full per-finding breakdown.
- `systematic_text_audit`: 4 frames (re-import run: 6). `u1287` is a
  single-line mixed-font headline-split frame whose split bbox the
  audit cannot match against the multi-line baseline region (measured
  0pt drift — a matching artifact); `u13eb` (+0.96pt), `u129e`
  (+3.36pt) and `u12b5` (+1.92pt) are body-text wrap. Same root cause
  as the structural bucket. `line_spacing_sim` returned no rows for
  any frame — no leading value reconciles a wrap-count difference.
  `severity: structural`.
- `visual_diff_regions`: phase error — `image size mismatch
  baseline=(620,874) preview=(621,875)`, a 1-pixel pdftocairo
  rasterisation rounding. A phase error is a hard red regardless of
  tolerances; documentation only.

`text_position_audit_jitter` (35 ≤ cap 40), `image_audit` (41 ≤ 45)
and `inventory` (2 ≤ 2) are within their tolerance caps — green.

## IMAGE AUDIT — verified

| Audit | Result | Outcome |
|-------|--------|---------|
| `image_content_audit` | **0 broken, 3 ok** | every image frame ok; the u145b Leonore portrait is **no longer distorted** — the ICC-aware CMYK→sRGB asset recipe fixed it this re-import (mean_delta_rgb low). The prior pass's `tol:image-content-leonore-cmyk-psd-conversion` tolerance is now obsolete (audit passes). |
| `image_frame_visibility_audit` | **0 invisible**, 3 ok | the DIE GRÜNEN logo `u13e4` renders (`asset_render_ratio` 0.798 — well above the 0.35 floor); pine photo `u1260` 0.994; Leonore portrait `u145b` 0.998 |

No CMYK or photo frame is broken; the logo renders correctly (verified
visually on page 1).

## SQUIGGLE AUDIT (ground-truth) — verified

`squiggle_alignment_audit`: `ok: true`, 0 issues. All 7 thin-underline
squiggle PolyLines (`u11e3`/`u11e4`/`u11e2`/`u11e5`/`u126c`/`u126e`/
`u1269`) carry `fill='Gelb'` and the audit reports each `status: ok`
with `vgap_mm` ≈ 0 and healthy `hoverlap_mm`. The page-1 encircling-
ellipse squiggle `u13ca` (not tracked by the audit — a different motif
kind) was geometry-fixed by hand and verified visually to encircle
"eine" in yellow, matching the baseline.

## COVERAGE GATE — verified

`idml_attribute_coverage`: `ok: true`, 0 issues — "all significant
unconsumed attributes accounted for (920-entry baseline)". No new
significant unconsumed attribute.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 1 (cover)** — the **DIE GRÜNEN logo** renders (white "G" +
   "DIE GRÜNEN" wordmark). The two-line headline "Ich bin eine /
   Headline." is centred. The **yellow squiggle encircles "eine"** (the
   converter mis-emitted it; restored by hand). Störer badge present.
2. **Page 6** — the **Leonore portrait** renders with **natural
   colours** (the prior pass's CMYK posterization is fixed by the
   ICC-aware asset recipe).
3. **Body / bullet-list paragraphs (pages 2-4)** — expect line breaks
   to fall at slightly different words than the baseline. Accepted
   cross-renderer wrap divergence — check the *text* is complete, not
   the exact wrap column.
4. **Rotated Impressum (pages 2/3)** — the `-90°` "Impressum: xxxxxx"
   text renders; its measured 28.34pt drift is the documented rotated-
   frame engine limit (Scribus cross-axis origin), not a misplacement.
5. **Facing-pages routing** — pages 3 and 5 are the right-hand pages of
   the two facing-pages spreads. Confirm each shows its own content.
