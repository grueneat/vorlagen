# Tolerance Log — 26-03-flyer-a6-hochformat-gruenes-cover

Companion log for `TOLERANCES.yml`. Append-only. Every row records a
tolerance/override granted during the Stage-2 tune, the measured drift
it resolves, the specific values, why it is the smallest conservative
choice, and its classification label. To remove an entry, append a new
row at the bottom: `REMOVED <id> — <date>: <reason fix landed>`.

This template is the A6-Hochformat flyer sibling of
`26-03-flyer-a6-hochformat-portrait` and
`26-03-flyer-a6-hochformat-quadrat-in-bild`; the tolerance classes
below mirror those templates' established, user-reviewed handling of
the same IDML-import gap classes.

---

## tol:inventory-offpage-registration-marks — 2026-05-17 — 2 off-page artifact rectangles

What: `inventory` audit tolerance, `severity: cosmetic`, `max_issues: 2`.
Values: cap 2; current issue count 2.
Measured drift it resolves: the converter deliberately skips two
`Rectangle` elements — `u141f` (x=-25.8mm) and `u1424` (x=-25.8mm),
both 5.2×5.1mm — that the IDML places ~26mm off the left page edge.
They are inline vector paths with no `<Image>`/`<PDF>` child (registration
/ colour-control furniture). The converter logs each as
`[skip] Rectangle Self='u141X': entirely outside page bounds … InDesign
design artifact, not emitted`. InDesign also omits them from the
trimmed PDF export. The inventory audit counts them as "dropped
elements" — they are a deliberate, documented non-emit, not a silent
drop.
Why conservative: cap is exactly 2 (the precise count of the two known
off-page marks); any genuine extra dropped element pushes the count to
3 and re-fails the audit.
Classification: human-review (correct converter behaviour; audit is
conservative).

## tol:image-audit-vector-path-delta — 2026-05-17 — 41 vector-path deltas

What: `image_audit` tolerance, `severity: cosmetic`, `max_issues: 45`.
Values: cap 45; current issue count 41.
Measured drift it resolves: 41 vector-path deltas. Derivative of the
Scribus raster/ICC rendering differences on full-bleed Dunkelgrün
page backgrounds and photo content, plus the IDML's inline decorative
vector paths (curly quotes, Wahlkreis ellipse / underline ornaments)
that the converter extracts as inline images rather than re-emitting
as Scribus Polygon items. Same gap class as the sibling flyer
templates' `tol:image-audit-vector-path-delta` (40 deltas, cap 45).
Why conservative: cap 45 = 41 current + a 4-unit buffer, matching the
sibling templates' cap; a real raster regression beyond the buffer
re-fails.
Classification: scribus-engine-bug (intrinsic raster + ICC differences).

## tol:text-position-jitter-freetype-kerning — 2026-05-17 — 31 sub-perceptible drifts

What: `text_position_audit_jitter` tolerance, `severity: cosmetic`,
`max_issues: 40`.
Values: cap 40; current issue count 31.
Measured drift it resolves: 31 sub-perceptible (≤5pt) per-word
position drifts — FreeType-vs-InDesign per-character kerning jitter
intrinsic to the two rasterisers. The structural bucket
(`text_position_audit_structural`) separately catches the larger
(>5pt) shifts. The `y_mm_shift` playbook found no reliable
calibration frame and emitted only tentative recommendations; the
`line_spacing` sim returned no rows for any frame.
Why conservative: cap 40 = 31 current + buffer, matching the sibling
flyer templates' cap; a real layout regression surfaces in the
structural bucket, not here.
Classification: scribus-engine-bug (intrinsic to FreeType
rasterisation).

## tol:text-position-structural-cross-renderer-wrap — 2026-05-17 — 254 large drifts (DOCUMENTED, preflight stays red)

What: `text_position_audit_structural` tolerance, `severity: structural`,
`max_issues: 260`.
Values: cap 260; current issue count 254. `severity: structural` →
documented only, does NOT flip preflight green.
Measured drift it resolves: 254 large (>5pt) word-position drifts,
concentrated on pages 2–4. Verified page-by-page (rendered pages 3 and
4 at 150dpi and compared to baseline): the rendered content and frame
geometry are correct. The drift is dominated by cross-renderer
line-wrap differences — Scribus and InDesign break the justified
body / bullet-list paragraphs at slightly different words because
their font-metric and hyphenation models differ (e.g. page-3 bullet
"Scim rem utas si vellaccum eatus nullquae cum et arum vendellab
iditatequi" fits 2 lines in the InDesign baseline but wraps to 3 lines
in Scribus). One wrap-point difference cascades into dozens of
downstream words counted as "drifted". Not a converter bug and not a
routing bug — the facing-pages multi-page routing was verified correct
(PDF page 3 shows "Ich bin auch eine Headline", matching the baseline).
Why conservative: `severity: structural` keeps preflight RED — this is
documented, NOT tolerated-as-passing. Cap 260 = 254 + small buffer
matching the sibling.
Classification: scribus-engine-bug (cross-renderer paragraph line-wrap
divergence). Same class as the sibling flyer templates'
`tol:text-position-structural-cross-renderer-wrap` (255 drifts).

## tol:systematic-text-line-count-divergence — 2026-05-17 — 12 frames (DOCUMENTED, preflight stays red)

What: `systematic_text_audit` tolerance, `severity: structural`,
`max_issues: 12`.
Values: cap 12; current issue count 12. `severity: structural` →
documented only.
Measured drift it resolves: 12 frames flagged with "line count differs"
(e.g. u13cd baseline=5 vs preview=4, u13eb baseline=3 vs preview=2).
This is the same cross-renderer wrap divergence as
`text_position_audit_structural` measured per-frame: when a paragraph
wraps to a different number of lines, the systematic audit reports it
as un-addressed sim-actionable drift. The `line_spacing` playbook ran
`line_spacing_sim` on all 12 frames and returned no rows for any of
them, so no (LINESPMode, LINESP) override is derivable.
Why conservative: `severity: structural` keeps preflight RED; cap 12
is the exact current count, so any new frame re-fails.
Classification: scribus-engine-bug (cross-renderer line-wrap; same
root cause as the structural text-position drift).

## tol:image-content-leonore-cmyk-psd-conversion — 2026-05-17 — u145b portrait color distortion (DOCUMENTED, preflight stays red)

What: `image_content_audit` tolerance, `severity: structural`,
`max_issues: 1`.
Values: cap 1; current issue count 1 (frame `u145b`). `severity:
structural` → documented only.
Measured drift it resolves: the page-6 portrait `u145b` renders with
heavily distorted colours (posterized blue/magenta/yellow instead of a
natural portrait). `image_content_audit` flags `mean_color_shift`
(mean_delta_rgb 78.0) and `hist_divergence` (0.28). Root cause: the
source link `2026-03-Leonore für Flyer.psd` is a **CMYK-mode**
Photoshop document, and the Stage-1 asset pipeline
(`links_export.yml` recipe `convert -flatten`) flattened it to RGB
PNG WITHOUT an ICC-aware CMYK→RGB conversion, producing the colour
distortion. The frame itself renders and is positioned correctly
(`image_frame_visibility_audit` reports it `ok`, visibility_ratio
2.09) — only the pixel colours are wrong. This is the documented
shared PSD→PNG CMYK→RGB conversion bug class confirmed on batch
templates 1–2.
Why conservative: `severity: structural` keeps preflight RED — this is
documented, NOT tolerated-as-passing. Cap 1 = the single affected
frame. The fix is upstream in the Stage-1 asset pipeline
(`tools/links_export.py` recipe needs an ICC CMYK→RGB step), NOT a
converter or build.py edit — per the overnight brief, do not attempt
a converter fix.
Classification: authoring-bug (Stage-1 asset-pipeline CMYK→RGB
conversion).

## tol:visual-diff-image-size-mismatch — 2026-05-17 — pdftocairo 1px rasterisation rounding (DOCUMENTED, preflight stays red)

What: `visual_diff_regions` phase-error, documented as
`severity: cosmetic`, `max_issues: 0`.
Values: no audit issue count — this surfaces as a phase ERROR, not an
audit issue. Preflight treats any entry in the `errors` dict as a hard
red regardless of tolerances, so this entry is documentation only.
Measured drift it resolves: `visual_diff_regions` errors with
`image size mismatch: baseline=(620, 874), preview=(621, 875)` — a
1-pixel difference in each dimension. Scribus's pdftocairo
rasterisation rounds the trim-box page size to a slightly different
pixel count than the InDesign baseline export at the same DPI. The
functional diff signal is covered by `visual_diff` and the per-region
audits; the phase surfaces the rounding honestly rather than coercing
dimensions.
Why conservative: documentation only — this cannot be made green by a
tolerance (phase errors are a hard red). Same artefact appears on the
sibling falz/flyer templates.
Classification: scribus-engine-bug (pdftocairo vs InDesign
rasterisation DPI rounding).

---

## Build.py changes (no numeric tolerance growth)

- **u13e4 (DIE GRÜNEN logo)** — switched from `inline_image_data` PNG +
  `scale_type=1` + `local_scale`/`local_offset_mm` to a direct
  `image=` reference (`gruene-logo-bund-weiss-cmyk.png`) +
  `scale_type=0`. The inline PNG rendered fully transparent under the
  Scribus 1.6.x SCALETYPE=1 bug (preview ink density 0.0); the
  `frame_visibility` playbook's documented fix. Logo now renders.
- **u1260 (pine-forest photo)** — switched from `scale_type=1` +
  `local_scale`/`local_offset_mm` to `scale_type=0`. The photo
  rendered invisible (preview ink density 0.0) under the same SCALETYPE
  bug; now renders correctly.
- **u145b (Leonore portrait)** — switched from `scale_type=1` +
  `local_scale`/`local_offset_mm` to `scale_type=0` for a
  fit-to-frame crop consistent with the baseline placement. Frame now
  renders (colour distortion is the separate CMYK-PSD authoring-bug
  above).
- **2× `# noinject:` markers** — added above the `u1260` and `u145b`
  ImageFrame `add()` calls; both are real IDML-placed content photos,
  not demo placeholders. Clears `external_asset_substitution_audit`.

None of these grows a numeric tolerance; all are playbook-class
structural image-frame fixes.

---

## Re-render pass — 2026-05-18 (template 3 of 8, combined-fidelity)

Re-imported `--reimport` to pick up the HEAD `7144731` converter/audit
fix set. Inventory gate exit 0 (perfect match against the committed
`SCAFFOLD_INVENTORY.yml`). The build.py edits below were re-applied on
top of the fresh converter output; none grows a numeric tolerance.

- **Green-body `SpaceAfter`** — the bare re-import dropped `SpaceAfter`
  on the green body paragraph style `idml/fliesstext-auf-gruenem-
  hintergrund` (the IDML's green `Fließtext` variant carries no
  `SpaceAfter`, while the white sibling `Fließtext auf weißem` carries
  `5.669…` explicitly; verified in `Resources/Styles.xml`). The
  `baseline.pdf` shows ~5.67pt inter-paragraph spacing on the green
  body, so `space_after_pt=5.6693` was added to the green style (the
  bullet style `aufzaehlungen-auf-gruenem-hintergrund` inherits it).
  This collapsed `text_position_audit_structural` 155 → 46 and
  `systematic_text_audit` 10 → 8. Same fix as siblings 1 and 2.
- **u13cd / u13cd_l2 split-headline ALIGN** — the converter splits the
  mixed-font headline "Ich bin eine" (Gotham Ultra) / "Headline."
  (Vollkorn Black Italic) into two single-line frames but loses the
  IDML `CenterAlign` justification on the `<trail>` paragraph of each.
  A single-Run frame's only line is closed by `<trail>`, so the ALIGN
  must live there. `ALIGN: '1'` added to `trail_attrs` of both frames
  and to the `paragraph_attrs` of u13cd_l2's Run. Also corrected the
  frame width 102mm → 90mm (the IDML `TextColumnFixedWidth`
  255.118pt); the converter had over-widened it, shifting the centred
  text right. Together these closed the two worst `line_match`
  findings (u13cd Δ-24.18pt, u13cd_l2 Δ-33.08pt → matched); line_match
  17 → 15.
- **u13ca squiggle geometry** — the re-import converter mis-emits this
  yellow encircling-ellipse Polygon on the IDML `[0 -1 -1 0]`
  ItemTransform: it swaps w/h, anchors on the wrong corner, and adds a
  redundant `rotation_deg=-90` that the HEAD PolyLine builder now
  applies, turning the wide ellipse vertical and dropping it off to
  the right of the headline. Restored to an un-rotated wide ellipse
  at the IDML-transform-verified page-local bbox (x 60.097mm,
  y 43.2715mm, w 35.0628mm × h 12.4143mm — w/h from the path's own
  bbox 99.4×35.2pt), keeping `fill='Gelb'`. The squiggle now encircles
  "eine", matching the baseline (verified visually). This is a build.py
  edit, not a converter change; the converter regression in rotated-
  PolyLine geometry should be addressed in Stage 1 (escalation noted in
  REVIEW_NOTES.md).

No numeric tolerance changed: `text_position_audit_structural` 46 ≤ cap
260, `systematic_text_audit` 8 ≤ cap 12, `text_position_audit_jitter`
36 ≤ cap 40, `image_audit` 41 ≤ cap 45 — all within the prior caps.

### line_match_audit residual — 15 of 71 lines (DOCUMENTED honest residual)

`line_match_audit` is not tolerance-able per the gate policy. After the
ALIGN fix closed the 2 closeable findings (17 → 15), the remaining 15
are all genuinely-unclosable cross-renderer residual — no per-frame fix
closes them:

- **2× rotated Impressum frames** (`u11fd`, `u126f`, `first_word_x`
  Δ28.34pt). 28.34pt = the 10mm frame width — Scribus measures `-90°`
  rotated text from the opposite cross-axis edge. Documented rotated-
  frame engine limit; text content matches (`:musserpmI xxxxxx` both
  renders). Verified visually (page 2 impressum strip).
- **1× rotated Störer frame** (`u1403`, `baseline_y` Δ-1.48pt). Same
  rotated-frame engine limit, sub-2pt.
- **7× body line-wrap** (`u1242` ×1, `u129e` ×6 cascade). Scribus and
  InDesign break the justified body paragraphs at different words; one
  wrap-point difference cascades. Same root cause as
  `text_position_audit_structural`. Frame widths verified correct
  (IDML `TextColumnFixedWidth` 212.6pt = 75mm).
- **5× sub-2pt centred-line residual** (`u12fb` Δ-1.92pt, `u13eb` ×2
  Δ~1.4pt, `u14b1` ×2 Δ~1.8pt). The ~0.75% Vollkorn/Gotham glyph-width
  difference shifts a centred line's start by ~half the width delta.
  Below the visible threshold; FreeType-vs-InDesign kerning.

Classification: scribus-engine-bug. Documented per the gate policy;
preflight stays honestly RED on `line_match_audit`.

### REMOVED tol:image-content-leonore-cmyk-psd-conversion — 2026-05-18

The 2026-05-18 re-import picked up the ICC-aware CMYK→sRGB asset recipe
(`links_export.yml` recipe is now `convert -profile sRGB -strip
(ICC-aware)`). The page-6 portrait `u145b` no longer renders distorted:
`image_content_audit` reports `0 broken, 3 ok`, `u145b` `classification:
ok`, `mean_delta_rgb` 9.1 (was 78.0), no flags. The tolerance is
obsolete — the audit passes outright — and has been removed from
`TOLERANCES.yml`.

---

## Re-render pass — 2026-05-19 (template 3 of 8, FINAL re-import)

Re-imported `--reimport --scaffold-only` on the HEAD `5e2cbbf` converter
/ audit fix set. Inventory gate exit 0 (perfect match against the
committed `SCAFFOLD_INVENTORY.yml`; no anname lost, no count decreased,
no word dropped). The bare re-import re-emitted build.py from the
converter and dropped the three prior per-frame fixes (the converter
does not consume `SpaceAfter`, the split-headline ALIGN, or the
normalised squiggle path); all three were re-applied on top of the
fresh converter output. No numeric tolerance grew — the two
`severity:structural` caps (260, 12) are unchanged; their `reason`
text was refreshed to the current counts.

- **Green-body `SpaceAfter`** — re-applied `space_after_pt=5.6693` on
  `idml/fliesstext-auf-gruenem-hintergrund`. The `baseline.pdf` page-1
  green body measures a 20.0pt paragraph gap vs a 14.3pt line gap =
  +5.7pt inter-paragraph spacing; the converter does not consume it
  (IDML green `Fließtext` carries it as line-break-separated runs the
  converter splits into paragraphs without spacing). This collapsed
  `text_position_audit_structural` 152 → 47 and `systematic_text_audit`
  6 → 4 and `text_position_audit` word drift 183 → 82.
- **u13cd / u13cd_l2 split-headline ALIGN + width** — re-applied
  `ALIGN: '1'` to the `trail_attrs` of both single-run frames and to
  the `paragraph_attrs` of u13cd_l2's Run (IDML `Story_u13d0` is
  `Justification=CenterAlign`; the split-headline emitter drops ALIGN
  from the trail paragraph). Re-applied frame width 102mm → 90mm
  (IDML `TextColumnFixedWidth=255.118pt`). Closed the two worst
  `line_match` findings: u13cd Δ24pt and u13cd_l2 Δ33pt → matched;
  `line_match_audit` 17 → 15.
- **u13ca squiggle geometry + path** — re-applied the un-rotated wide
  ellipse at the IDML-transform-verified page-local bbox (x 60.097mm,
  y 43.2715mm, w 35.0628 × h 12.4143mm) with the path normalised to
  positive coordinates. The converter's bare re-emit keeps the raw
  IDML-local negative-coordinate path plus a `rotation_deg=-90`; with
  the rotation removed but the raw path kept, the ellipse renders
  above the headline. The normalised path restores it onto the word
  "eine" — `squiggle_alignment_audit` OK, verified visually (page 1).

`split_headline_spacing` GREEN, `image_frame_visibility_audit` GREEN
(logo u141f / icons all render), `squiggle_alignment_audit` GREEN,
`attribute_coverage_audit` GREEN (no new unconsumed attribute). The
4 residual-RED audits (`line_match_audit` 15, `systematic_text_audit`
4, `text_position_audit_structural` 47, `visual_diff_regions` 55) are
the documented cross-renderer line-wrap / rasterisation residual —
all within their existing caps, classification `scribus-engine-bug`,
no playbook can advance them (`line_spacing_sim` returns no rows for
any flagged frame — the divergence is wrap-point, not leading).

---

## brand_overrides — 2026-05-19 — IDML-import structural-check exceptions

`meta.yml::brand_overrides` entries granted for this scaffold-imported
26-03 template. Each silences one `structural_check` brand rule whose
violation traces to the IDML import, not to a build.py defect. Identical
gap class to the sibling 26-03 leporello templates (gruenes-cover-2,
portrait, zweigeteiltes-cover) that already carry the same block.

- **`brand:bleed_3mm`** — The IDML document was authored with bleed=0 and build.py deliberately emits bleed_mm=0 so the rendered PDF compares directly against the trim-only InDesign baseline.pdf. The Quickguide's 3mm print bleed postdates this asset. Resolution path: inject the brand 3mm bleed in tools/idml_to_dsl.py at scaffold time — deferred.
- **`brand:image_text_overlap`** — The original InDesign layout deliberately overlays headline / Zitat text on full-bleed photo backdrops and on the magenta Stoerer decoration. The brand rule cannot distinguish intentional design overlay from accidental clipping. Resolution path: per-frame intent annotation in the rule — deferred.
- **`brand:inside_page`** — The IDML spread coordinate system places multi-panel content on a single oversized canvas; frames belonging to later panels register outside the converter's declared trim-sized page. The converter preserves source geometry verbatim per issue #35 P1. Resolution path: emit a true multi-panel spread layout — deferred.
- **`brand:line_spacing_0.9`** — The IDML-imported InDesign ParagraphStyles (idml/* and ci/* families) carry leading values that do not follow the Quickguide 0.9-factor convention. tools/idml_to_dsl.py emits the source leading verbatim; the InDesign-authored baseline.pdf is the convergence target (issue #35 P1). Identical handling to the sibling 26-03 leporello templates that already carry this override. Resolution path: a per-template tune pass — deferred.
