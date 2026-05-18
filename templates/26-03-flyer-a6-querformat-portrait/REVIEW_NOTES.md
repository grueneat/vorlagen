# REVIEW NOTES — 26-03-flyer-a6-querformat-portrait

Prose summary for the human reviewer. Read alongside `TOLERANCE_LOG.md`
(per-tolerance detail) and `TOLERANCES.yml` (machine-readable).

## What the template is

A6 landscape ("Querformat") candidate flyer for Die Grünen NÖ, source
`26-03-Flyer A6 Querformat Portrait.idml`. It is a **folded flyer**: the
IDML has 4 spreads totalling 6 pages — spread 1 = page 1 (single,
A6 419x297pt), spread 2 = pages 2+3 (facing pair), spread 3 = pages 4+5
(facing pair), spread 4 = page 6 (single). InDesign exports this layout
**spread-based**, so `baseline.pdf` has 4 pages: 419 / 839 / 839 / 419 pt
wide (the two facing spreads are double-width single pages).

Content: page 1 cover (three-line headline, Störer circle, Leonore
portrait, subheadline); pages 2-3 and 4-5 are inner panels with lorem-
ipsum body text, bullet lists, a windmill line-art icon, and a quote
panel; page 6 is a full-bleed green "Plakat" background with a centred
white quote and yellow attribution.

## Scaffold outcome — GREEN (structural)

The scaffold required two converter changes in `tools/idml_to_dsl.py`
(Stage 1 permits converter edits):

1. **Spread-merged page model.** The converter previously emitted one
   SLA page per IDML *page* (6 pages). InDesign exports spread-based, so
   the rendered preview never aligned with `baseline.pdf` and the
   `visual_diff` audit crashed on a 6-vs-4 size mismatch. The converter
   now emits one SLA page per IDML *spread*: a facing-pages spread merges
   into one double-width page with all items placed relative to the
   leftmost page's origin. New helper `_collect_spread_pages`;
   `_emit_pages` / `_emit_build_template` / `_emit_page_stubs` rewired.
   Result: preview.pdf is 4 pages at 419/839/839/420pt — matches
   baseline page-for-page.

2. **Rotated-frame geometry fix.** `_compute_page_local_bbox_pt` used to
   return the rotated *axis-aligned bbox* as the frame width/height for
   rotated frames. Scribus rotates a frame around its XPOS/YPOS top-left,
   so this swept the -90deg full-bleed "Plakat" background (u978) off the
   top of the sheet — page 6 rendered blank. The converter now returns
   the un-rotated WIDTH/HEIGHT plus the rotation pivot. Page 6 now
   renders the green background correctly.

Also fixed a latent crash in `tools/systematic_text_audit.py`
(`max_drift_pt=None` TypeError on the MD report) and a stale-PNG bug in
`tools/visual_diff.py::rasterise` (it globbed `prefix-*.png` and picked
up leftover higher-numbered PNGs when the page count decreased 6->4).
The `test_rotated_90deg_textframe` unit test was updated to encode the
corrected rotated-frame contract; the full 597-test unit suite passes.

Every IDML element is emitted or explicitly skipped (completeness
assertion passes); all 4 `<Link>` assets resolve on disk; build.py runs
and renders. `SCAFFOLD_INVENTORY.yml` captured 46 elements, 40 emitted,
6 deliberately skipped off-page artifacts.

## 2026-05-18 re-import + re-tune — outcome

The template was re-imported (`bin/idml-import --reimport`) and
re-tuned against the full converter + audit-chain fix set. Net result:
preflight RED with **5** documented structural residuals (was 6); the
CMYK-image audits and one text audit improved out of the red set.

### What the fix set closed

- **CMYK images — both now correct.** The CMYK->sRGB + aspect-fill
  fix set fixed `image_content_audit` (2 broken -> 0) and
  `image_frame_visibility_audit` (1 invisible + 1 faint -> 0). The
  Leonore portrait (u9cc, CMYK PSD) renders with correct colour and
  the pine-tree photo (u906, CMYK JPEG) is no longer blank. All four
  image frames render with `asset_render_ratio` 0.94-1.00 — the
  DIE GRÜNEN logo u46c at 0.94, well above the 0.35 floor. The two
  former CMYK tolerances were removed from `TOLERANCES.yml`.
- **Squiggle alignment — clean.** `squiggle_alignment_audit` is GREEN.
  The body-leading change shifted text and one squiggle (u96c) drifted
  off its word mid-tune; the `squiggle_realign` playbook re-anchored it
  (`squiggle_anchors.yml`). All squiggles are yellow and on their word.
- **attribute_coverage — clean.** `idml_attribute_coverage` GREEN; no
  new significant unconsumed attribute.

### Per-frame tune fixes applied (build.py `# P5/tune`)

- Body ParaStyle leading 16.0 -> 15.0pt on all three body styles. The
  InDesign baseline renders body text on a 15.00pt baseline grid; the
  converter emitted 16.0, giving +1pt/line drift and 11-line overflow.
  This closed the pre-tune `frame_vertical_position` / `baseline_y`
  findings on u94a and cut `text_position_audit_structural` 279 -> 206
  and `systematic_text_audit` 12 -> 6.
- `SpaceAfter` dropped from `fliesstext-auf-weissem-hintergrund`. The
  IDML declares `SpaceAfter=5.6693` but the baseline snaps body text to
  a 5.30mm grid that absorbs the sub-pitch SpaceAfter (baseline u92e/
  u94a show uniform 5.30mm gaps, no inter-paragraph jump). Scribus has
  no grid model, so emitting it added a real gap and structural drift.
- The `line_spacing` tune-fix playbook also converted several headline
  frames from `LINESPMode=1` (auto) to explicit `LINESPMode=0` +
  empirical LINESP.

### 5 audits remain RED — all cross-renderer line-wrap

`systematic_text_audit` (6), `text_position_audit_structural` (206),
`text_render_audit` (5 words), `visual_diff_regions` (38),
`line_match_audit` (27). One root cause: Gotham Narrow Book renders
~0.75% wider in Scribus than in InDesign, so each justified body line
holds one word fewer (measured: baseline col-1 line-1 = 4 words across
56mm, preview = 3 words across the same 56mm). Fitting the lost word
would need ~16% horizontal compression — far beyond a non-distorting
glyph shrink (`min_glyph_shrink` is already 0.98). Unclosable without a
Scribus justification/hyphenation alignment. All five are documented in
`TOLERANCES.yml` with `severity: structural` (documentation-only —
preflight stays red, not fudged green). A red preflight with fully
documented, classified residuals is the accepted terminal state for
this batch — the sibling flyer/leporello templates committed the same way.

`text_position_audit_jitter` (37 sub-perceptible <=5pt drifts) is
tolerated: cap raised 36 -> 38 (TOLERANCE_LOG row 4) because the
body-leading correction moved a few words across the 5pt jitter
boundary.

## Residual drift numbers (2026-05-18)

| Audit | Count | vs prior | Class |
|---|---|---|---|
| text_position_audit_structural | 206 large (>5pt) word drifts | 279 | scribus-engine (red, documented) |
| text_position_audit_jitter | 37 sub-perceptible (<=5pt) | 32 | scribus-engine (tolerated) |
| line_match_audit | 27 mismatched lines | n/a | scribus-engine (red, documented) |
| visual_diff_regions | 38 hot grid regions | 38 | scribus-engine (red, documented) |
| systematic_text_audit | 6 sim-actionable frames | 12 | scribus-engine (red, documented) |
| text_render_audit | 5 unique boundary words | 10 | scribus-engine (red, documented) |
| image_audit | 24 vector/image deltas | 24 | scribus-engine (tolerated) |
| inventory | 6 off-page artifacts | 6 | human-review (tolerated) |
| image_content_audit | 0 broken | 2 | FIXED |
| image_frame_visibility_audit | 0 invisible/faint | 1+1 | FIXED |

## human-review items

- The 6 `inventory` dropped elements are off-page registration furniture
  (17.9x17.9pt Rectangles at x=476..794pt or x=-504pt). The converter
  correctly skips them and InDesign omits them too — no action needed,
  the audit is just conservative.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page geometry** — confirm preview is 4 pages at 419/839/839/420pt
   matching baseline (the whole point of the spread-merge converter fix).
2. **Page 4 (last spread)** — confirm the green full-bleed Plakat
   background renders (this is the rotated-frame fix; it was blank
   before).
3. **Page 3 top-right strip** — u906 pine-tree photo now renders
   green-toned foliage matching the baseline (was blank before the
   2026-05-18 CMYK->sRGB fix).
4. **Body-text wrap on pages 2-3** — Scribus wraps the justified
   lorem-ipsum body paragraphs to ~2 more lines than InDesign because
   Gotham Narrow Book renders ~0.75% wider. The text all fits inside
   the (widened) frames — verified by pdfplumber line-top scans, no
   clipping — but the differing wrap shifts every downstream word.
   This is the cross-renderer wrap residual, not lost content in the
   data model.
5. **Page 1 cover** — should match closely (headline, Störer, portrait,
   subheadline all present and positioned correctly).
