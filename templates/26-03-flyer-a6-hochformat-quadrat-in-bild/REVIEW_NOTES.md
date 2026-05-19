# Review Notes — 26-03-flyer-a6-hochformat-quadrat-in-bild

Prose summary for a human reviewer. Read alongside `TOLERANCE_LOG.md`
(every edit + accepted residual, newest first) and `TOLERANCES.yml`
(structured).

This is the **FINAL verification re-render** (template 2 of 8). The
template was re-imported against the current committed converter/audit
fix set (HEAD `870a9a3`): CMYK→sRGB conversion, deterministic
aspect-fill crop, squiggle colour + re-anchoring, the five Tier-A
attributes, the recalibrated mixed-font headline splitter, the
colour-managed comparison, and the full audit chain including the
`split_headline_spacing` hard gate.

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
current converter, overwriting the prior pass's `build.py` as intended.

- Asset audit `ok: true` — all `<Link>` files resolved and converted
  (pine-forest JPG, Gewessler JPG, radial-gradient PSD, DIE GRÜNEN AI
  logo). No missing assets — no BLOCKED condition.
- Inventory gate: `inventory_compare` exits 0 — a clean match against
  the committed `SCAFFOLD_INVENTORY.yml`, no structural regression.

## Tune outcome — RESIDUAL (image/squiggle/coverage/headline green; line-wrap red)

Stage 2 (`/idml-tune`) ran the `bin/tune-render` → `bin/tune-fix`
loop. The image, squiggle, attribute-coverage, headline-spacing,
text-render, per-region-regression and inventory audits are all green;
the line-wrap-driven text-position audits remain at the documented
cross-renderer floor (`severity: structural`, deliberately
non-preflight-flipping). The render was promoted via
`bin/tune-render --no-transactional` — the same terminal state as the
prior committed run.

### The headline — converter-emitted geometry + audit-tool bugfix

The current converter's mixed-font headline splitter emits the three
`u133f` lines ("Das ist eine" / "dreizeilige" Vollkorn italic /
"Headline") as single-line frames, each widened by a `+12mm`
clip-safety margin (`w_mm=70.4538`), with the per-line FLOP baseline
correction applied in-converter. A direct pixel scan restricted to the
green box confirmed all three lines render at **0.0pt drift** at the
converter-emitted `y_mm` — the headline geometry is correct as emitted.

Two things still needed Stage-2 attention:

1. **Centring.** The converter emits the widened frames left-aligned;
   the IDML story is `Justification="CenterAlign"`. `ALIGN: '1'` was
   added to lines 2-3 `paragraph_attrs` and to all three `trail_attrs`
   (a single-Run frame's only paragraph is closed by `<trail>`), and
   each frame's `x_mm` was shifted `-6.0mm` (half the `+12` widening)
   so the widened frame's centre stays exactly on the IDML text
   frame's centre (52.50mm). The headline now centres in the green box.

2. **`split_headline_spacing` false positive — fixed in the audit
   tool.** The audit reported `u133f` "worst 2.88pt" and the number
   did not respond to any frame move. Root cause: the `+12mm`-widened
   frames' union bbox (x 17.27→87.73mm) overhangs the green box
   (x 21→84mm) onto the foggy pine-forest photo, and the audit's
   white-colour ink scan latched onto the diffuse atmospheric fog
   instead of the headline glyphs. A density-aware scanner
   (`_scan_color_headline_top` in `tools/line_spacing_pixel_audit.py`)
   now selects the densest matched band (the real glyphs; diffuse
   contamination forms low-peak bands) and returns its glyph cap-top.
   `split_headline_spacing` went RED → GREEN; the 10 pixel-audit unit
   tests still pass. See TOLERANCE_LOG for the full root-cause writeup.

### The body win — green-body SpaceAfter

The re-import dropped inter-paragraph spacing on the green body
paragraph style `idml/fliesstext-auf-gruenem-hintergrund`. The IDML
carries it as `<SameParaStyleSpacing>` (the style's `BasedOn` is
`[No paragraph style]`, `SpaceAfter=0`), which the converter does not
consume; the white sibling `fliesstext-auf-weissem-hintergrund`
carries `5.669…` explicitly via `SpaceAfter`. `baseline.pdf` shows the
same ~5.67pt inter-paragraph spacing on the green body + bullet lists.
`space_after_pt=5.6693` was re-applied to the green style (the bullet
style inherits it). This collapsed `text_position_audit_structural`
152 → **46** and `systematic_text_audit` 6 → **4**. Templates 1-3 all
needed this re-applied on re-import.

### Edits applied (build.py)

1. **Green-body `SpaceAfter`** — `space_after_pt=5.6693` on
   `idml/fliesstext-auf-gruenem-hintergrund`.
2. **u133f three-line headline** — `ALIGN: '1'` on lines 2-3
   `paragraph_attrs` + all three `trail_attrs`; each frame `x_mm`
   shifted 23.2731 → 17.2731 (centre kept on the IDML centre). The
   converter-emitted `y_mm` / `w_mm` were left untouched.
3. **u1386 (radial-gradient overlay)** — `# noinject:` comment;
   genuine IDML-placed content. Cleared `external_asset_substitution`.

Plus one shared audit-tool bugfix in `tools/line_spacing_pixel_audit.py`
(see above).

### Accepted residuals — what stays red

- `text_position_audit_structural`: 46 large (>5pt) word drifts
  (down from 152 — the `SpaceAfter` fix). The 46 are the 2 wrap events
  (`u1242`, `u129e`) cascading downstream words. Within cap 260.
- `line_match_audit`: 16 of 70 lines mismatched. Breakdown: 6 body
  line-wrap + 1 unmatched (`u1242`, `u129e` — Scribus breaks justified
  paragraphs at different words); 3 rotated-frame (`u11fd`/`u126f`
  Δ28.34pt rotated `-90°` Impressum sidebar, `u1358` Δ-1.47pt rotated
  `-9°` Störer); 6 sub-2pt centred/justified `first_word_x` (`u133f`×3
  Δ~1.2pt, `u12fb` Δ-1.92pt, `u1390`×2 Δ~1.8pt — the ~0.75%
  Vollkorn/Gotham glyph-width difference). All 16 are in the brief's
  known-acceptable residual classes. `line_match_audit` is not
  tolerance-able — preflight stays red; no fix is durable.
- `systematic_text_audit`: 4 frames (`u1287`, `u129e`, `u12b5`,
  `u13a7`). Cross-renderer line-wrap; `line_spacing_sim` returned no
  rows for all four — no leading value reconciles a wrap-count
  difference. The per-line GAP the converter emitted is CORRECT.
  Within cap 11.

`text_position_audit_jitter` (37 ≤ cap 38), `image_audit` (39 ≤ 45)
and `visual_diff_regions` (54 ≤ 65) are within their tolerance caps —
green. No tolerance cap grew this pass.

## IMAGE AUDIT — verified

| Audit | Result | Outcome |
|-------|--------|---------|
| `image_content_audit` | **0 broken, 5 ok** | every image frame ok; no CMYK frame blank or discoloured |
| `image_frame_visibility_audit` | **0 invisible**, 1 faint (`u1386`) | the DIE GRÜNEN logo `u1336` renders; `u1386` faint is the accepted CMYK→sRGB tone residual on the dark PSD |

Logo `u1336` `asset_render_ratio` 0.849 — well above the 0.35 floor.
`u1386` (radial vignette) visibility_ratio 0.686, `asset_render_ratio`
0.987 — renders, a touch lighter than baseline (small CMYK→sRGB tone
shift on the dark PSD; accepted). No CMYK or photo frame is broken.

## SQUIGGLE AUDIT (ground-truth) — verified

`squiggle_alignment_audit`: `ok: true`, 0 issues. All 8 squiggle
PolyLines carry `fill='Gelb'` (yellow). The audit reports every
squiggle `status: ok` with `vgap_mm` ≈ 0 — the squiggles render yellow
and sit on their words.

## COVERAGE GATE (Phase E5f) — verified

`idml_attribute_coverage`: `ok: true`, 0 issues — "all significant
unconsumed attributes accounted for (920-entry baseline)". No new
significant unconsumed attribute.

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1** — pine-forest background, green box, three-line headline
  ("dreizeilige" in yellow Vollkorn italic) — the three lines are
  centred in the green box and vertically stacked. DIE GRÜNEN logo
  inside the box, magenta "Störer" badge. Headline first-word x within
  ~1.2pt of baseline (the ~0.75% glyph-width residual).
- **Pages 2-4** — green body pages. The green body paragraphs and
  bullet lists carry ~5.67pt inter-paragraph spacing (the `SpaceAfter`
  restore) — paragraph rhythm matches the baseline. Body text still
  wraps a hair differently word-for-word (cross-renderer);
  sub-perceptible, nothing missing.
- **Page 5** — pine-forest banner photo at the top + body text below.
  Yellow squiggles under "auch" and on "om:".
- **Page 6** — Gewessler portrait with the radial-gradient vignette
  (a dark vignette at fill_opacity 0.9, a touch lighter than baseline —
  the accepted CMYK tone residual, not a defect), the green box, and
  the quote.
