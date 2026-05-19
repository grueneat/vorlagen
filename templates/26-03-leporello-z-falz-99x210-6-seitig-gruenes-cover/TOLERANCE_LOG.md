# Tolerance Log — 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover

Documents every entry in meta.yml::brand_overrides, non_ci_styles,
non_ci_colors, non_ci_layers and every TOLERANCES.yml row, with the
rationale for why the converter cannot fix the underlying drift.

Append-only. Remove entries via a new row at the bottom that says
"REMOVED <rule_id> — <date>: <reason fix landed>".

No `meta.yml::brand_overrides` / `non_ci_*` entries were added for this
template. All tolerances below live in `TOLERANCES.yml` as accepted
visual residuals; all Stage-2 edits were build.py changes (image
reference swap, noinject comments, a y_mm pin) and did not grow any
tolerance list.

## tol:cross-renderer-line-wrap-structural — 2026-05-18 — Scribus vs InDesign line wrap

Reason: Scribus 1.6.x wraps paragraph text at different points than
InDesign because Gotham Narrow / Vollkorn render a fraction wider per
line in Scribus. Frames re-flow by a line and every subsequent word
shifts, producing `text_position_audit_structural` deltas > 5pt. The
systematic text audit confirms "line count differs" for the affected
frames (u16c baseline=5/preview=4, u3a2 baseline=3/preview=4, uf7
baseline=20/preview=19, etc.). The y_mm_shift and line_spacing
playbooks cannot close a wrap re-flow — a leading override does not
move the wrap point. Measured residual: 60 large structural drifts
(scaffold start 90; the y_mm_shift playbook brought uniform-offset
frames in, leaving the wrap-driven remainder). Conservative: this is
the documented known-issue class for this batch — the Flyer templates
settled at ~254-279; this 6-panel Leporello settles at 60.
Classification: scribus-engine-bug.
Follow-up: engine-bug; no upstream issue yet.

## tol:cross-renderer-line-wrap-jitter — 2026-05-18 — sub-perceptible word drift

Reason: Same Scribus vs InDesign font-metric difference, below the
5pt visible-shift threshold. Measured residual: 22 sub-perceptible
jitter drifts (scaffold start 112; y_mm_shift closed the uniform-
offset majority). Conservative: sub-perceptible by definition.
Classification: scribus-engine-bug.
Follow-up: engine-bug; no upstream issue yet.

## tol:systematic-text-actionable-wrap — 2026-05-18 — sim-actionable wrap residual

Reason: 10 frames carry sim-actionable drift (scaffold start 21). The
systematic audit attributes the majority to "line count differs —
text wrapped differently" (u155, u16c, u2d5, u3a2, u3ba, uf7) which
line_spacing_sim cannot resolve. u1b0/u1e6 are SPLIT offsets (per-
paragraph anchor, signs differ across lines); u1c7 is a uniform
+1.92pt offset already inside the y_mm_shift convergence band.
Measured residual: 10 actionable, 13 sub-threshold, 0 tolerated→clean.
Conservative: each frame's cause is either wrap (un-fixable) or
already at the playbook floor. Classification: scribus-engine-bug.
Follow-up: engine-bug; no upstream issue yet.

## tol:u2cd-pine-cmyk-jpeg-blank — 2026-05-18 — CMYK JPEG renders blank

Reason: u2cd references `green-pine-trees-covered-with-fog.jpg`.
`identify -verbose` confirms `Colorspace: CMYK`, `Type:
ColorSeparation`. Scribus 1.6.x renders CMYK JPEGs blank;
`links_export.py` passes the JPEG through unchanged (`recipe:
passthrough`) with no ICC conversion. This is a known shared batch
issue. The asset file IS present on disk — this is NOT a missing-link
blocker. Measured residual: `image_content_audit` baseline_variance
93.69 vs preview_variance 2.63 (variance_ratio 0.028); preview mean
RGB ~253 (white/blank). The fix is an authoring-side sRGB re-export
(the sibling gruenes-cover-2 ships `green-pine-trees-covered-with-fog-
srgb.png` for exactly this reason). Conservative: no converter fix
exists; documented and accepted per the batch known-issues policy.
Classification: authoring-bug.
Follow-up: authoring; baseline asset needs sRGB re-export.

## tol:social-icons-composite-ai-invisible — 2026-05-18 — composite-AI crop frames invisible

Reason: u3e7/u3f0/u3f5 (left-column social-media icons) render
invisible. They reference the composite `Social Media Icons
weiss.ai` (aspect 3.46, content analysis shows 4 icons in one file).
The scaffold ran `--allow-composite-ai`, keeping the composite whole
and cropping it per-frame via `local_offset_mm` + `SCALETYPE=1`.
Scribus 1.6.x does not render that small-frame (3.3mm) composite-crop
RGBA path; the frames are blank. Measured residual:
`image_frame_visibility_audit` baseline ink density ~0.20-0.62 vs
preview 0.0 on each. The proper fix is the composite-AI split
(`tools/composite_ai_split.py`), a Stage-1 / converter-stage concern
requiring re-scaffold — it cannot be a Stage-2 build.py edit because
the individual icon files do not exist on disk and the per-frame icon
mapping is not derivable from the offsets without rendering. The
right-column icons u477/u4a2/u4da carry individual split blobs and
render fine. Conservative: leaving the frames invisible-but-documented
is safer than guessing the wrong icon (visually wrong > invisible).
Classification: authoring-bug (composite-AI is per-template, L-002).
Follow-up: authoring; re-scaffold with composite_ai_split for the
left-column icons.

## tol:composite-ai-social-media-icons-weiss — 2026-05-18 — composite-AI flag

Reason: `asset_extraction` reports `ok: false` solely because `Social
Media Icons weiss.ai` is flagged composite-AI (3 distinct frame
offsets reference one .ai). All 7 links resolve on disk
(`links_missing: []`). Imported via `--allow-composite-ai`.
Conservative: composite-AI detection is informational; the visibility
consequence is logged separately above. Classification: authoring-bug.
Follow-up: authoring; composite-AI is per-template, accepted.

## tol:run-style-headline-cross-extraction-match — 2026-05-18 — cross-frame word collision

Reason: One large `run_style_audit` drift on the word "Headline":
baseline GothamNarrow-Bold 12pt vs preview GothamNarrow-Ultra 38pt.
"Headline" appears in two frames (the small page-1 subheadline and
the large headline); the audit cross-matched them across frames.
Colour drift is `delta_format` only (`#ffffff` vs `cmyk:0,0,0,0` —
the same white in two encodings). Conservative: not a real style
regression; surfaced for human review. Classification: human-review.
Follow-up: human-review; cross-frame word collision in run_style_audit.

## tol:image-audit-vector-path-and-icc-delta — 2026-05-18 — vector-path + ICC delta

Reason: 26 `image_audit` issues: 26 vector-path deltas plus region
colour drift classified predominantly `icc_likely`. Vector-path
deltas are the Scribus vs pdftocairo path-flattening difference on
the imported .ai-derived PDFs; `icc_likely` colour drift is the ICC-
profile rendering difference upstream in Scribus. Conservative:
neither is converter-fixable. Classification: scribus-engine-bug.
Follow-up: engine-bug; no upstream issue yet.

## tol:visual-diff-regions-residual — 2026-05-18 — page-level aggregate

Reason: 20 hot regions, driven by the cross-renderer line-wrap (text
re-flow shifts pixels across wide regions) and the invisible image
frames (u2cd, u3e7/u3f0/u3f5). Each underlying cause is documented in
its own row above; `visual_diff_regions` is the page-level aggregate.
Conservative: no independent cause. Classification: scribus-engine-bug.
Follow-up: engine-bug; aggregate of the rows above.

## tol:cross-renderer-line-wrap-jitter — 2026-05-19 — cap raised 30 → 34

Reason: On the converter-fix-set re-import the u1c7 body frame received
a y_mm_shift (uniform median drift -5.04pt × cached sign -1 → +1.778mm).
That shift moved the whole text block onto the correct baseline and cut
`text_position_audit_structural` from 128 to 48 (well under cap 70) and
`line_match_audit` from 32 to 14. The trade-off is that several words
which were previously >5pt structural drifts now land in the 2-5pt
jitter band, so the jitter count moved from 30 to 34. These 4 extra
items are sub-perceptible cross-renderer font-metric noise — the pixel
audit confirms 0 frames carry any remaining uniform vertical offset, so
the jitter is irreducible at the build.py level. Smallest covering cap
is 34. Conservative: net visual fidelity improved (structural −80,
line_match −18); the jitter cap rise is the accounting consequence of
words crossing the 5pt boundary, not new drift. Classification:
scribus-engine-bug. Follow-up: engine-bug; no upstream issue yet.

## REMOVED tol:u2cd-pine-cmyk-jpeg-blank — 2026-05-19: fix landed

The converter fix set now routes the CMYK pine JPEG through a
CMYK→sRGB + aspect-fill crop (`crops/green-pine-trees-covered-with-fog-
u2cd.png`). u2cd renders correctly: `image_frame_visibility_audit`
asset_render_ratio 0.994, `image_content_audit` 0 broken. The blank-
render residual no longer exists; the tolerance row is retired.

## REMOVED tol:social-icons-composite-ai-invisible — 2026-05-19: fix landed

The three left-column social icons (u3e7 Facebook, u3f0 Instagram,
u3f5 TikTok) referenced the composite `Social Media Icons weiss.ai`
4-icon strip and rendered invisible as a small-frame composite-crop
RGBA path. Stage-2 fix: the composite PNG was sliced into three
individual square icon crops (`crops/social/social-{facebook,
instagram,tiktok}-weiss.png`), and the three frames switched from
`inline_image_data` to `image=` ref + `scale_type=0` per the idml-tune
SKILL worked example. The frame→icon mapping was derived from the IDML
FrameFittingOption LeftCrop/RightCrop values and verified against the
baseline PDF. `image_frame_visibility_audit` now reports all three OK
(asset_render_ratio ~0.85-0.99); only the u4a2 white-on-dark L-014
false positive remains. The tolerance row is retired.
