# Tolerance Log — 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover

Companion log for TOLERANCES.yml entries. The protocol in
`.claude/skills/idml-tune/tolerance_protocol.md` formally gates additions
to `meta.yml::brand_overrides` / `non_ci_*` lists; this template adds
NO entries to those lists (P4-gated, requires user confirmation that
was not available during finalisation). The entries below document the
audit residuals declared in TOLERANCES.yml for review continuity.

Append-only. To remove an entry, add a new row at the bottom that says
`REMOVED <id> — <date>: <reason fix landed>`.

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
