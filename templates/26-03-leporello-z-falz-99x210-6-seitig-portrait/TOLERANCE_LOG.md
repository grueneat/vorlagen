# Tolerance Log — 26-03-leporello-z-falz-99x210-6-seitig-portrait

Companion log for `TOLERANCES.yml` and `meta.yml::brand_overrides`.
The protocol in `.claude/skills/idml-tune/tolerance_protocol.md`
formally gates additions to `meta.yml::brand_overrides` / `non_ci_*`
lists. The brand_overrides below are added in parity with the sibling
falz templates (zweigeteiltes-cover, kandidat-falzflyer-din-lang-
gruenes-cover-v2) — every entry documents an IDML-import gap class
the converter cannot close per the current pipeline.

Append-only. To remove an entry, add a new row at the bottom that says
`REMOVED <id> — <date>: <reason fix landed>`.

---

## brand:line_spacing_0.9 — 2026-05-14 — IDML ParagraphStyles violate Quickguide leading factor

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
sibling falz templates.

## brand:font_family — 2026-05-14 — Times Roman fallback for idml/no-paragraph-style

Reason: 11 text frames inherit FONT="Times Roman" via the
idml/no-paragraph-style and idml/normalparagraphstyle defaults that
the IDML preserves untouched (the InDesign source never overrides
them for these minor labels). All actual Run() calls inside the
flagged frames carry brand fonts explicitly (Gotham Narrow Book,
Gotham Narrow Bold, Gotham Narrow Ultra, Vollkorn Black Italic);
only the abstract paragraph-style fallback retains Times Roman. The
converter cannot remap to brand fonts without changing the
baseline.pdf convergence target.

Follow-up: converter-extension; future Stage-1 work
(tools/idml_to_dsl.py font resolution for unresolved styles). Same
gap class as the sibling falz templates.

## brand:bleed_3mm — 2026-05-14 — IDML source authored with bleed=0

Reason: The IDML's InDesign document was authored with bleed=0;
converter respects the source page geometry. The baseline.pdf
(convergence target) also has bleed=0. Adjusting bleed would force
a deviation from the InDesign-authored output. Brand-team review
pending — the canonical Quickguide requires 3mm but the existing
IDML asset predates that requirement.

Follow-up: authoring; baseline.pdf needs re-export with 3mm bleed,
then the override can be removed. Same gap class as the sibling
falz templates.

## brand:inside_page — 2026-05-14 — Decorative frames intentionally overshoot trim

Reason: Multiple frames in the original IDML extend slightly outside
the trim box (u1ae background polygon with 1.82mm overshoot; u3a2
and several decorative shapes with similar overshoot). These were
intentional InDesign-side bleed/extension marks in the source asset.
The converter preserves the source geometry verbatim per issue 35 P1
(baseline.pdf is the convergence target).

Follow-up: engine-bug; no upstream issue yet. Same gap class as
the sibling falz templates.

## brand:image_text_overlap — 2026-05-14 — White-on-green text overlaps green polygon

Reason: The IDML places impressum text and other white-on-green
text overlapping the green page-background polygon by design — the
visual result is white-text-on-green, visually correct against
baseline.pdf. The brand:image_text_overlap rule cannot distinguish
"text on a colored polygon backdrop" (intentional) from "text on a
raster image" (overlap concern).

Follow-up: engine-bug; the rule itself needs a polygon-vs-image
distinction. Same gap class as the sibling falz templates.
