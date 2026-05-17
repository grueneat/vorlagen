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
