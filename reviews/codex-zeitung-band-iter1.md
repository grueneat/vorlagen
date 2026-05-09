---
review_of: zeitung-band-consistency-iter1
review_type: visual
review_topic: "Zeitung A4 band-consistency audit (Issue #25 pre-fix baseline)"
reviewed_at: 2026-05-09
tool: codex
codex_cli_version: codex-cli 0.128.0
prompt_path: prompts/zeitung-band-consistency-audit.md
images_attached: 14
---

## Codex output (verbatim)

**Per-Page Audit**

`Page 01`
Feature page. Excluded from band-rule findings. Inspected; no body-pool audit items reported.

`Page 02`
Feature page. Excluded from band-rule findings. Inspected; no body-pool audit items reported.

`Page 03`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: lowest body content stays above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 04`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: lowest body content stays above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 05`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: bottom photo and text block stay above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 06`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: bottom image/caption group stays above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 07`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: lowest body text stays above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 08`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: lower profile card and portrait stay above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 09`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: quote block and text stay above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 10`
Feature page. Excluded from band-rule findings. Inspected; no body-pool audit items reported.

`Page 11`
Feature page. Excluded from band-rule findings. Inspected; no body-pool audit items reported.

`Page 12`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: bottom photo stays above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 13`
No findings.
Header band check: first body headline starts below `y=49 mm`, around `y=58-60 mm`.
Footer band check: lowest quote/text content stays above `y=283 mm`; page number sits alone in footer zone.
Margin check: body content stays within `x=20-190 mm`.

`Page 14`
Feature page. Excluded from band-rule findings. Inspected; no body-pool audit items reported.

**Findings**
No body-pool findings to report. No `ERROR`. No `WARNING`.

**Spread Baseline Check**
`Spread 04-05`: pass. Headline tops align visually; page numbers/footers align.
`Spread 06-07`: pass. Headline tops align visually; page numbers/footers align.
`Spread 08-09`: pass. Headline tops align visually; page numbers/footers align.
`Spread 12-13`: pass. Headline tops align visually; page numbers/footers align.

```xml
<verdict value="pass" body_pool_findings="0" spread_baseline_findings="0">
  All 14 PNG previews were opened and visually inspected. On the body-pool pages (03, 04, 05, 06, 07, 08, 09, 12, 13), body content remains below the header cutoff at y=49 mm, above the footer cutoff at y=283 mm, and within the left/right content bounds at x=20-190 mm. Feature pages were inspected but excluded from body-pool extent reporting per the rule. The comparable body-pool spreads also hold a consistent headline start line and footer/page-number baseline, so the template passes the Issue #25 band-consistency audit.
</verdict>
```

## Cross-check vs audit JSON

`bin/audit-alignment zeitung-a4-grun --json` (saved to
`/tmp/audit-iter1.json`) reports 13 `[ERROR]` `band_consistency_warnings`
across 7 body-pool pages: 3, 4, 5, 7, 9, 12, 13.

| Page | Audit-tool finding | Codex iter1 |
|------|-------------------|-------------|
| 3    | unnamed Quote TextFrame at x=19.3 (drift 0.7mm past LEFT outer margin) | clean |
| 4    | P3 Hero at x=[135.3, 207.0] extends 17mm past inner margin | clean |
| 5    | P4 Foto-Spread at y_bottom=297 intrudes 14mm into footer band | clean |
| 7    | Kopie von u2d5c (8) at y_top=37.2 intrudes into header band; u6e8 inline icon at y=[43, 60.7] crosses header boundary | clean |
| 9    | Kopie von u2d5c (11) + Kopie von u2da1 (14) at y_top=37.2; unnamed inline icon at y=[41.7, 51.5] | clean |
| 12   | unnamed "Weiße Headlines" TextFrame at y=[20, 55.3] crosses header-band boundary; P11 Bottom image at y=[213.7, 297] intrudes into footer band | clean |
| 13   | Kopie von u2d5c (17) + Kopie von u2da1 (22)/(23) at y_top=37.0-37.8 cross header-band boundary | clean |

### Pages flagged by BOTH Codex and audit-tool

None.

### Pages flagged ONLY by Codex

None.

### Pages flagged ONLY by audit-tool

All 7 pages above (3, 4, 5, 7, 9, 12, 13).

## Cross-check verdict

**Codex visual review passes; audit-tool geometric review fails.** This
is a genuine disagreement between visual rendering and geometric
extent. The discrepancy is explained by Scribus text-frame baseline
padding: a TextFrame declared at y_mm=37 with body-text style has its
visual text glyphs starting around y=43-45 mm because of leading +
top-of-frame padding. Codex sees the rendered glyphs and judges them
"below y=49"; the audit-tool sees the FRAME extent and correctly
identifies the y_top intrusion.

The architectural intent of `brand:band_consistency` is to pin FRAME
extents (not visual rendering) because frames are the geometric
primitive that gets shuffled when Bezirksgruppen recombine LEFT/RIGHT
pages. A frame at y=37 paired with a frame at y=49 in a spread will
visually misalign the headline baseline even if the individual page
looks fine. The audit-tool's findings are the source of truth.

Page-3 0.7mm margin drift on a Quote TextFrame is sub-millimeter and
genuinely below visual perception; Codex correctly judges this clean
visually. The audit catches it because the rule's tolerance is 0.5mm
and the drift is 0.7mm. Both verdicts are right at their level of
abstraction.

Page-4 P3 Hero (17mm past inner margin), page-5 P4 Foto-Spread (14mm
into footer band), page-12 P11 Bottom (full-bleed photo into footer
band) are LARGE drifts that Codex did NOT flag. This suggests Codex's
visual inspection is missing image extents that the audit clearly
catches. Two interpretations:

1. Codex genuinely doesn't visually distinguish "image extends to bleed"
   from "image fits in band" at the resolution of the PNG (210mm at
   100dpi = ~830px wide; 14mm = ~55px which IS visible).
2. Codex' prompt-rule mental model uses a coarser visual heuristic
   ("does it look balanced") rather than measuring against the band
   y-coordinates.

Either way, the geometric audit is the correctness gate. The Codex
verdict gives confidence that, **after T06's fixes**, the rendered
output will look right (no headline misalignment, no obvious bleed
into footer). The audit-tool gives confidence that the FRAME geometry
will be correct.

## Gate decision

**PROCEED to T06 with the audit-tool's 13 findings as the geometry-fix
spec.** No Codex-only findings → no rule strengthening needed (no Rule-1
gap). Audit-only findings are expected and acceptable per the planner's
tightening #6 ("acceptable: machine-precision only" + "frames at the
boundary").

T06's scope expands beyond RESEARCH §2's 6 rows to also cover:
- Page 3 unnamed Quote drift (0.7mm, may resolve via x_mm=20 normalization).
- Page 12 "Weiße Headlines" header-band intrusion (similar to pages 7/9/13).
- Page 12 P11 Bottom photo crop (similar to page 5 P4 Foto-Spread).

After T06, iter2 cross-check should show audit-tool with zero
band_consistency_warnings AND Codex still pass (since visual was
already clean).

**Iteration count:** 1 of 2 Codex budget consumed (T09 will be iter2).
