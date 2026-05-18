# Tolerance Log — 26-03-flyer-a6-gruenes-cover

Companion log for `TOLERANCES.yml`. Append-only. Every row records a
tolerance/override granted during the Stage-2 tune, the measured drift
it resolves, the specific values, why it is the smallest conservative
choice, and its classification label. To remove an entry, append a new
row at the bottom: `REMOVED <id> — <date>: <reason fix landed>`.

This template is the A6-Querformat flyer (gruenes Cover variant) — the
Querformat sibling of `26-03-flyer-a6-hochformat-gruenes-cover`. The
tolerance classes below mirror that template's established,
user-reviewed handling of the same IDML-import gap classes.

---

## tol:inventory-offpage-registration-marks — 2026-05-18 — 4 off-page artifact rectangles

What: `inventory` audit tolerance, `severity: cosmetic`, `max_issues: 4`.
Values: cap 4; current issue count 4.
Measured drift it resolves: the converter deliberately skips four
`Rectangle` elements — `u6f0`, `u6f2`, `u77f`, `u964`, each 6.3×6.3mm —
that the IDML places far outside the page (x=-29.8mm or x≈180mm, well
beyond the page edges). They are inline vector paths with no
`<Image>`/`<PDF>` child (registration / colour-control furniture on
the pasteboard). The converter logs each as `[skip] Rectangle
Self='uXXX': entirely outside page bounds … InDesign design artifact,
not emitted`. InDesign also omits them from the trimmed PDF export.
The inventory audit counts them as "dropped elements" — they are a
deliberate, documented non-emit, not a silent drop (the scaffold
completeness assertion still passes: `every_idml_run_present_in_build_py:
true`).
Why conservative: cap is exactly 4 (the precise count of the four
known off-page marks); any genuine extra dropped element pushes the
count to 5 and re-fails the audit.
Classification: human-review (correct converter behaviour; audit is
conservative).

## tol:image-audit-vector-path-delta — 2026-05-18 — 41 vector-path deltas

What: `image_audit` tolerance, `severity: cosmetic`, `max_issues: 45`.
Values: cap 45; current issue count 41.
Measured drift it resolves: 41 vector-path deltas. Derivative of the
Scribus raster/ICC rendering differences on full-bleed Dunkelgrün page
backgrounds and photo content, plus the IDML's inline decorative
vector paths the converter extracts as inline images rather than
re-emitting as Scribus Polygon items. Same gap class as the sibling
flyer templates' `tol:image-audit-vector-path-delta`.
Why conservative: cap 45 = 41 current + a 4-unit buffer, matching the
sibling `26-03-flyer-a6-hochformat-gruenes-cover` (41 deltas, cap 45);
a real raster regression beyond the buffer re-fails.
Classification: scribus-engine-bug (intrinsic raster + ICC differences).

## tol:text-position-jitter-freetype-kerning — 2026-05-18 — 22 sub-perceptible drifts

What: `text_position_audit_jitter` tolerance, `severity: cosmetic`,
`max_issues: 26`.
Values: cap 26; current issue count 22.
Measured drift it resolves: 22 sub-perceptible (≤5pt) per-word
position drifts — FreeType-vs-InDesign per-character kerning jitter
intrinsic to the two rasterisers. The structural bucket
(`text_position_audit_structural`) separately catches the larger
(>5pt) shifts. The `y_mm_shift` playbook found no reliable calibration
frame and the `line_spacing` sim returned no rows for any frame.
Why conservative: cap 26 = 22 current + a 4-unit buffer; a real layout
regression surfaces in the structural bucket, not here.
Classification: scribus-engine-bug (intrinsic to FreeType
rasterisation).

## tol:text-position-structural-cross-renderer-wrap — 2026-05-18 — 257 large drifts (DOCUMENTED, preflight stays red)

What: `text_position_audit_structural` tolerance, `severity: structural`,
`max_issues: 265`.
Values: cap 265; current issue count 257. `severity: structural` →
documented only, does NOT flip preflight green.
Measured drift it resolves: 257 large (>5pt) word-position drifts. The
drift is dominated by cross-renderer line-wrap differences — Scribus
and InDesign break the justified body / bullet-list paragraphs at
slightly different words because their font-metric and hyphenation
models differ. One wrap-point difference cascades into dozens of
downstream words counted as "drifted". The `line_spacing_pixel_audit`
probe of the worst frame (`u67c`) shows 7 lines in BOTH baseline and
preview but with the preview text starting ~62pt lower and the lines
compressed to catch up — the signature of a reflow cascade, not a
per-line leading error (`line_spacing_full_audit` classifies every
paragraph `drift_minor`, ≈1pt). Not a converter bug. This is the
documented cross-renderer line-wrap gap for Querformat flyers (the
overnight brief flags Querformat flyers settling at ~279 structural
drifts).
Why conservative: `severity: structural` keeps preflight RED — this is
documented, NOT tolerated-as-passing. Cap 265 = 257 + small buffer.
Classification: scribus-engine-bug (cross-renderer paragraph line-wrap
divergence).

## tol:systematic-text-line-count-divergence — 2026-05-18 — 10 frames (DOCUMENTED, preflight stays red)

What: `systematic_text_audit` tolerance, `severity: structural`,
`max_issues: 11`.
Values: cap 11; current issue count 10. `severity: structural` →
documented only.
Measured drift it resolves: 10 frames flagged "line count differs" /
"SPLIT offset" / "text wrapped differently" — the same cross-renderer
wrap divergence as `text_position_audit_structural` measured per
frame. The `line_spacing` playbook ran `line_spacing_sim` on all
flagged frames and returned no rows for any of them, so no
(LINESPMode, LINESP) override is derivable.
Why conservative: `severity: structural` keeps preflight RED; cap 11 =
10 current + 1-unit buffer.
Classification: scribus-engine-bug (cross-renderer line-wrap; same
root cause as the structural text-position drift).

## tol:text-render-cross-renderer-wrap-wordsplit — 2026-05-18 — 12 word-split FPs (DOCUMENTED, preflight stays red)

What: `text_render_audit` tolerance, `severity: structural`,
`max_issues: 12`.
Values: cap 12; current issue count 12. `severity: structural` →
documented only.
Measured drift it resolves: `text_render_audit` reports 12 unique
"missing" words (`impressum`, `consent.`, `eaque`, `eosenihicto`,
`quaturem`, `volor`, `xxxxxx`, `et`, `ipis`, `nam`, `quatur.`, `quis`).
All 12 were verified present in `build.py` (2-3 occurrences each). The
audit also reports `extra_in_preview: impressu` — confirming the words
are not lost but SPLIT at a different line-wrap point (`impressum` →
`impressu` + `m`) so the per-word string comparison no longer matches.
This is the same cross-renderer line-wrap divergence surfacing in the
text-extraction word comparison; no text is actually suppressed.
Why conservative: `severity: structural` keeps preflight RED; cap 12 =
exact current count.
Classification: scribus-engine-bug (cross-renderer line-wrap word-split
in text extraction; not real text loss).

## tol:image-content-cmyk-render — 2026-05-18 — u906 + ube9 colour/blank (DOCUMENTED, preflight stays red)

What: `image_content_audit` tolerance, `severity: structural`,
`max_issues: 2`.
Values: cap 2; current issue count 2 (frames `u906`, `ube9`).
`severity: structural` → documented only.
Measured drift it resolves: 2 image frames classified broken.
`ube9` (`2026-03-leonore-fuer-flyer.png`, converted from a CMYK PSD)
renders with a mean-RGB shift (`mean_delta_rgb 75.5`, `hist_divergence
0.19`) — the known broken CMYK-PSD conversion: `tools/links_export.py`'s
`convert -flatten` recipe produces non-ICC CMYK→RGB output that
posterizes/discolours the portrait. `u906`
(`green-pine-trees-covered-with-fog.jpg`) is a CMYK JPEG
(`links_export.py` recipe `passthrough`) and renders fully blank —
Scribus 1.6.x cannot rasterise CMYK JPEGs. Both are Stage-1
asset-pipeline limitations called out in the overnight brief's
"known shared issues — do not re-litigate" list; neither is a
converter or build.py bug.
Why conservative: `severity: structural` keeps preflight RED — this is
documented, NOT tolerated-as-passing. Cap 2 = the two affected frames.
Classification: authoring-bug (Stage-1 asset-pipeline CMYK handling).

## tol:image-frame-visibility-cmyk-jpeg-blank — 2026-05-18 — u906 invisible (DOCUMENTED, preflight stays red)

What: `image_frame_visibility_audit` tolerance, `severity: structural`,
`max_issues: 1`.
Values: cap 1; current issue count 1 (frame `u906`). `severity:
structural` → documented only.
Measured drift it resolves: `u906`
(`green-pine-trees-covered-with-fog.jpg`) is invisible in the preview
(`preview_ink_density 0.0`, `visibility_ratio 0.0`). The frame was
already switched to `scale_type=0` (the documented `frame_visibility`
playbook fix); it remained invisible because the source is a CMYK
JPEG which Scribus 1.6.x cannot decode at all — the same CMYK-JPEG
blank-render shared issue as `image_content_audit` above.
Why conservative: `severity: structural` keeps preflight RED; cap 1 =
the single affected frame.
Classification: authoring-bug (Scribus CMYK-JPEG decode failure;
Stage-1 asset pipeline).

## tol:visual-diff-image-size-mismatch — 2026-05-18 — pdftocairo 1px rasterisation rounding (DOCUMENTED, preflight stays red)

What: `visual_diff_regions` phase-error, documented as
`severity: cosmetic`, `max_issues: 0`.
Values: no audit issue count — this surfaces as a phase ERROR, not an
audit issue. Preflight treats any entry in the `errors` dict as a hard
red regardless of tolerances, so this entry is documentation only.
Measured drift it resolves: `visual_diff_regions` errors with
`image size mismatch: baseline=(874, 620), preview=(875, 621)` — a
1-pixel difference in each dimension. The scaffold cropped the
baseline.pdf to remove printer's marks (`cropped to trim box
419.5x297.6pt`); the auto-crop box does not land on an exact pixel
boundary at 150dpi, so the cropped baseline rasterises to 874×620
while the trim-only SLA preview rasterises to 875×621. The sibling
querformat-portrait template — whose baseline had no printer's marks —
does NOT hit this error. The functional diff signal is covered by
`visual_diff` and the per-region audits.
Why conservative: documentation only — this cannot be made green by a
tolerance (phase errors are a hard red). Same artefact appears on the
sibling `26-03-flyer-a6-hochformat-gruenes-cover`.
Classification: authoring-bug (baseline.pdf printer's-marks crop
rounding) / scribus-engine adjacent (pdftocairo DPI rounding).

---

## Build.py changes (no numeric tolerance growth)

- **uad7 (DIE GRÜNEN logo, page 1 cover)** — switched from
  `inline_image_data` PNG + `scale_type=1` + `local_scale` to a direct
  `image=` reference (`gruene-logo-bund-weiss-cmyk.png`) +
  `scale_type=0`. The inline PNG rendered fully transparent under the
  Scribus 1.6.x SCALETYPE=1 white-on-transparent-PNG bug (preview ink
  density 0.0); the `frame_visibility` playbook's documented fix. Logo
  now renders (image_frame_visibility_audit dropped 2 invisible → 1).
- **u906 (pine-forest photo, page 5)** — switched from `scale_type=1`
  + `local_scale`/`local_offset_mm` to `scale_type=0` (fit-to-frame),
  the documented playbook form. The photo remains invisible because
  the source is a CMYK JPEG Scribus 1.6.x cannot decode — that residual
  is the authoring-bug documented above, not a frame-fitting error.
- **2× `# noinject:` markers** — added above the `u906` and `ube9`
  ImageFrame `add()` calls; both are real IDML-placed content images,
  not demo placeholders. Clears `external_asset_substitution_audit`.

None of these grows a numeric tolerance; all are playbook-class
structural image-frame fixes.
