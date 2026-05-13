# Tolerance Log — kandidat-falzflyer-din-lang-gruenes-cover-v2

Documents every entry in `meta.yml::brand_overrides` with the rationale
for why the converter cannot fix the underlying drift. Migrated from
issue #35 PR descriptions into this on-disk record per issue #38 Task 17
+ Task 3 (`tools/check_overrides_growth.py` gate).

Append-only. Remove entries via a new row at the bottom that says
"REMOVED `<rule_id>` — `<date>`: <reason fix landed>".

## brand:line_spacing_0.9 — 2026-05-13 — migrated from issue #35

Reason: IDML-imported template. The original InDesign ParagraphStyles
(Headline in grünem Kasten, Absatzformat 1, Fließtext auf grünem
Hintergrund, Aufzählungen auf grünem Hintergrund) carry leading values
that do NOT follow the Quickguide 0.9-factor convention (e.g.
headline-in-gruenem-kasten linesp=12 fontsize=12 = 1.0×,
fliesstext-auf-gruenem-hintergrund linesp=16 fontsize=11 = 1.45×,
absatzformat-1 linesp=14.3 fontsize=11 = 1.3×). The converter emits
these verbatim from Resources/Styles.xml; changing them would diverge
from the InDesign-authored baseline.pdf which is the convergence target.

Follow-up: issue #37 Phase E2 line_spacing_audit + the
line_spacing_audit pattern would let the converter detect & flag these
authoring choices rather than silently passing them through, but
overriding the brand-rule lint for THIS template remains the right
call.

## brand:font_family — 2026-05-13 — migrated from issue #35

Reason: IDML-imported template. The IDML contains 2 text frames (u347,
u3ba) that the converter cannot resolve to a brand font and falls back
to Times Roman. Both are minor labels (impressum / credit).

Follow-up: extend `tools/idml_to_dsl.py` to resolve font names from
the IDML's `<Fonts>` section so brand-font detection covers PostScript
names + style suffixes. Track as a follow-up converter-extension
issue.

## brand:bleed_3mm — 2026-05-13 — migrated from issue #35

Reason: IDML-imported template. The IDML's InDesign document was
authored without the brand-standard 3mm bleed; baseline.pdf was
exported with bleed=0 to match. Adding bleed in the SLA would diverge
from the baseline.

Follow-up: future templates authored in InDesign should include the
standard 3mm bleed. This is an authoring-process correction, not a
converter fix.

## brand:inside_page — 2026-05-13 — migrated from issue #35

Reason: IDML-imported template. Multiple frames in the original IDML
violate the brand inside-page conventions (e.g. text crossing fold
lines, frames extending beyond the standard text safe area). These
are intentional design choices in the Z-Falz layout where the inner
panels intentionally bleed across the fold.

Follow-up: brand-rule lint should grow an exemption hint for Z-Falz
folded layouts. Not a converter concern.

## brand:image_text_overlap — 2026-05-13 — migrated from issue #35

Reason: IDML-imported template. The IDML places the impressum text
over the cover photo with intentional overlap (designer choice). The
brand-rule lint flags this as a layout regression but the baseline.pdf
shows the same overlap.

Follow-up: brand-rule lint should grow a per-template exemption
mechanism for intentional overlay text. Not a converter concern.

## sla-size-bloat — 2026-05-13 — issue #39 brand-embed first PR

Reason: Issue #39 inlines every brand asset into `template.sla` via
`ImageFrame(inline_image_data=…, inline_image_ext=…)` to make the
downloaded SLA self-contained (no broken external file references).
For v2-falzflyer this inlines 9 PFILE-referenced PNG/JPG assets
(brand logos, social-media icons, photo crop, and the plakat poster).

Pre-emission size:  58_037 bytes (text-only SLA, 9 absolute PFILEs).
Post-emission size: 17_951_630 bytes (~18 MB, 9 inline images).
Delta:              +17_893_593 bytes (~309× bloat).

This size is accepted per `.issues/39-…/CONTEXT.md` — the brand-team
decision on Phase D (zip pipeline) / Phase E (gallery flip) / Phase G
(AI watermark) is pending. Until that decision, the bare SLA is the
download artifact; inlining is the only way to keep the file
self-contained.

Follow-up: when Phase D lands, content assets (the photo + plakat)
can move to `shipped:` and out of the SLA, shrinking it back to a few
hundred KB.
