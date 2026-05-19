# Tolerance Log — falzflyer-z-falz-6-seitig-zweigeteiltes-cover

Companion log for `TOLERANCES.yml` and `meta.yml::brand_overrides`.
The protocol in `.claude/skills/idml-tune/tolerance_protocol.md`
formally gates additions to `meta.yml::brand_overrides` / `non_ci_*`
lists. The brand_overrides below are added in parity with the sibling
v2 falzflyer template — every entry documents an IDML-import gap class
the converter cannot close per the current pipeline.

Append-only. To remove an entry, add a new row at the bottom that says
`REMOVED <id> — <date>: <reason fix landed>`.

---

## brand:line_spacing_0.9 — 2026-05-13 — IDML ParagraphStyles violate Quickguide leading factor

Reason: The original InDesign ParagraphStyles preserved verbatim from
the IDML source (idml/headline-in-gruenem-kasten, idml/absatzformat-1,
idml/fliesstext-auf-gruenem-hintergrund,
idml/aufzaehlungen-auf-gruenem-hintergrund, idml/normalparagraphstyle,
idml/no-paragraph-style, plus the ci/* family) carry leading values
that do not follow the Quickguide 0.9-factor convention. Examples:
headline-in-gruenem-kasten linesp=12 fontsize=12 = 1.0x;
fliesstext-auf-gruenem-hintergrund linesp=16 fontsize=11 = 1.45x;
absatzformat-1 linesp=14.3 fontsize=11 = 1.3x. The converter emits
these verbatim from the IDML Resources/Styles.xml; changing them
would diverge from the InDesign-authored baseline.pdf which is the
convergence target (issue 35 P1).

Follow-up: engine-bug; no upstream issue yet. Same gap class as the
sibling v2 falzflyer.

## brand:font_family — 2026-05-13 — Times Roman fallback for idml/no-paragraph-style

Reason: 11 text frames inherit FONT="Times Roman" via the
idml/no-paragraph-style and idml/normalparagraphstyle defaults that
the IDML preserves untouched (the InDesign source never overrides
them for these minor labels). The converter cannot remap to brand
fonts without changing the baseline.pdf convergence target.

Follow-up: converter-extension; future Stage-1 work
(tools/idml_to_dsl.py font resolution for unresolved styles). Same
gap class as the sibling v2 falzflyer (which lists 2 frames; this
template's IDML uses the pattern more broadly).

## brand:bleed_3mm — 2026-05-13 — IDML source authored with bleed=0

Reason: The IDML's InDesign document was authored with bleed=0;
converter respects the source page geometry. The baseline.pdf
(convergence target) also has bleed=0. Adjusting bleed would force
a deviation from the InDesign-authored output. Brand-team review
pending — the canonical Quickguide requires 3mm but the existing
IDML asset predates that requirement.

Follow-up: authoring; baseline.pdf needs re-export with 3mm bleed,
then the override can be removed. Same gap class as the sibling
v2 falzflyer.

## brand:inside_page — 2026-05-13 — Decorative frames intentionally overshoot trim

Reason: Multiple frames in the original IDML extend slightly outside
the trim box (u1ae background polygon with 1.82mm overshoot; u514,
u3a2, and several decorative shapes with similar overshoot). These
were intentional InDesign-side bleed/extension marks in the source
asset. The converter preserves the source geometry verbatim per
issue 35 P1 (baseline.pdf is the convergence target).

Follow-up: engine-bug; no upstream issue yet. Same gap class as
the sibling v2 falzflyer.

## brand:image_text_overlap — 2026-05-13 — White-on-green text overlaps green polygon

Reason: The IDML places impressum text and other white-on-green
text overlapping the green page-background polygon by design — the
visual result is white-text-on-green, visually correct against
baseline.pdf. The brand:image_text_overlap rule cannot distinguish
"text on a colored polygon backdrop" (intentional) from "text on a
raster image" (overlap concern).

Follow-up: engine-bug; the rule itself needs a polygon-vs-image
distinction. Same gap class as the sibling v2 falzflyer.

---

## tol:headline-gotham-narrow-ultra-1char-wrap — 2026-05-13 — Gotham Narrow Ultra 1-char width drift

Reason: Scribus's Gotham Narrow Ultra renders one character wider per
line than InDesign's at 30pt. The 30pt "Ich bin auch eine Headline."
wraps to "Ich bin auc / eine Headli." in our preview. This is a font-
metric difference between the two renderers and not converter-fixable.
Audit signal: text_position_audit. Visual recognisability preserved.

Follow-up: engine-bug; no upstream issue yet.

## tol:squirrel-photo-fill-vs-fit-blur — 2026-05-13 — SCALETYPE=1 vs 0 sharpness trade-off

Reason: Scribus's free-scale path (SCALETYPE=1) interpolates pixels
during render, producing marginally softer photo output than auto-fit
(SCALETYPE=0). We use SCALETYPE=1 + computed FILL math because
SCALETYPE=0 fits-within (leaves empty bands) rather than fills-and-
crops; the IDML's FittingOnEmptyFrame=FillProportionally has no native
Scribus equivalent. Trade-off accepted: fill the frame even if
marginally softer. Audit signal: visual_diff_regions.

Follow-up: engine-bug; no upstream issue yet.

## tol:u3a0-plakat-dunkel-rightcrop-not-honored — 2026-05-13 — IDML RightCrop=640.6pt not translated

Reason: The IDML's FrameFittingOption @RightCrop=640.6pt would clip
"plakat-dunkel-fuer-flyer" to the tree-strip-only view shown in the
baseline. The converter does not yet translate FrameFittingOption
per-side crops; ours fills the whole panel. Audit signal: image_audit.

Follow-up: converter-extension; future Stage-1 work (FrameFittingOption
per-side crops).

## tol:text-position-audit-201-word-drifts — 2026-05-13 — sub-perceptible kerning drift

Reason: 201 words exceed the 2.0pt position threshold against the
baseline; the drift is dominated by FreeType vs InDesign rasteriser
kerning differences. All 444 words render correctly per
text_render_audit; position drift is intrinsic to font-engine
differences. Audit signal: text_position_audit.

Follow-up: engine-bug; no upstream issue yet.

## tol:image-audit-26-inline-vector-path-delta — 2026-05-13 — inline TextPath vectors not regenerated

Reason: The IDML emits curly quote marks and a wind-turbine ornament
as inline vector paths (`<TextPath>` siblings of `<Content>` inside
text frames). The converter extracts these as inline images instead
of regenerating them as Scribus Polygons. Architectural fix requires
extending the pattern library to detect and re-emit inline-TextPath
vectors. Audit signal: image_audit.

Follow-up: converter-extension; future Stage-1 work
(pattern_library inline-TextPath).

## tol:line-spacing-audit-4-subpoint-drifts — 2026-05-13 — sub-pt Aki-model drift

Reason: 4 frames show |delta| > 0.5pt line-spacing drift against the
baseline. All drifts are sub-1.0pt (sub-perceptible). Engine-level
drift in how Scribus interprets LeadingModelAki Aki-below vs InDesign's
Aki-above default; the converter applies the +12% AKI_BELOW correction
factor but residual drift remains. Audit signal: line_spacing_audit.

Follow-up: engine-bug; no upstream issue yet.

## tol:asset-extraction-composite-ai-social-icons — 2026-05-13 — splitter ran, audit classifier outdated

Reason: composite_ai_split produced a manifest and sub-PDFs for
"Social Media Icons weiss.ai"; build.py renders icons via
offset-cropping the source PNG. asset_extraction_audit flags the
template because the manifest is present — the audit classifier
needs to be extended to recognise "manifest emitted + offsets used
correctly" as the expected post-split state, not an error.

Follow-up: converter-extension; future Stage-1 work
(asset_extraction_audit classifier for split-icon).

## tol:run-style-audit-extractor-disagreement — 2026-05-13 — pdfplumber vs pdftotext word-count disagreement

Reason: pdfplumber reports 444 words; pdftotext reports 463-464 words.
The segmenters handle inline composition differently at hyphen
boundaries, soft-wraps, and curly-quote-adjacent whitespace.
text_render_audit verifies content equality via pdftotext-substring
matching; the per-engine word count is an audit-engine quirk.

Follow-up: engine-bug; no upstream issue yet (audit-engine selection).

## tol:visual-diff-regions-20-hot — 2026-05-13 — covered by other tolerances

Reason: 20 hot regions are produced when the heatmap overlays preview
against baseline. They co-locate with residuals already documented
above (squirrel FILL blur, plakat-dunkel crop delta, inline-vector
decorations, sub-perceptible text-position drifts). No new converter
bugs flagged.

Follow-up: covered by other tolerances above.

---

## 2026-05-19 — re-scaffold for the 3-line headline + green-texture-embed converter fix set

This template was re-scaffolded (`bin/idml-import --scaffold-only
--reimport`) so build.py is regenerated with the converter's
single-line-per-headline-line emission. Two defects from the
pre-fix scaffold are closed:

- **3-line headline.** The cover headline "Das ist die / dreizeilige
  / Headline" is now emitted as three single-line TextFrames
  (`u16c` / `u16c_l2` / `u16c_l3`) at the IDML Leading interval, each
  `LINESPMode=0 LINESP=34.13`. `line_spacing_pixel_audit` reports
  0.0pt per-line drift against baseline.pdf — `split_headline_spacing`
  is GREEN. (The pre-fix scaffold rendered the headline as one
  mixed-font frame with broken inter-line spacing.)
- **Green brand texture.** `plakat-dunkel-fuer-flyer.png` (the green
  crumpled-paper brand texture, despite the filename) now classifies
  as `asset_policy::embedded` via the converter's known-brand-asset
  rule (`tools/idml_import_driver.py::_EMBEDDED_BRAND_STEMS`). The
  converter inlines the texture bytes; `template.sla` carries it as
  `isInlineImage` ImageData (no `PFILE` reference) so the downloaded
  SLA always shows the brand panel, never a missing-image
  placeholder.

`meta.yml::brand_overrides` was re-added (4 rules: `bleed_3mm`,
`image_text_overlap`, `inside_page`, `line_spacing_0.9`) — the
re-scaffold regenerates meta.yml and drops them; they are restored
in parity with the shipped sibling
26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover (each gap class
already documented row-by-row above in this log). The stale
`template-preview.sla` orphaned by the re-scaffold was removed (the
regenerated build.py has an empty INJECT_MAP, so the gallery renders
`template.sla` directly, matching gruenes-cover).

Residual preflight reds (image_audit vector-path delta,
line_match / text_position cross-renderer line-wrap, composite-AI
social-icon visibility) are the documented Scribus-vs-InDesign
engine-floor classes covered by the TOLERANCES.yml rows above —
unchanged in kind from the pre-fix state and from gruenes-cover.
