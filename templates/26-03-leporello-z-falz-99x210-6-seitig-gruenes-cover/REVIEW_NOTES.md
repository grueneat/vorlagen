# Review Notes — 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover

## What this template is

The v1 "gruenes Cover" Leporello z-Falz — a 6-panel z-fold brochure,
99x210mm panels, imported from
`26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover.idml`. It is the
9th and final template of the overnight IDML-import batch. Three other
Leporello variants already exist (portrait, gruenes-cover-2,
zweigeteiltes-cover), so the converter already had Leporello
experience — this import required NO converter changes.

The IDML has 2 spreads, 23 stories, 5 paragraph styles. The layout is
text-heavy: green-background body copy and bullet lists, headline
boxes, a contact block with social-media icons, plus two photo banners.

## Scaffold outcome — GREEN

`bin/idml-import --scaffold-only --allow-composite-ai` produced a
structurally complete scaffold:

- 7 `<Link>` assets, all resolved on disk (`links_missing: []`).
- `Social Media Icons weiss.ai` flagged composite-AI (3 distinct
  frame offsets reference one .ai). Imported whole via
  `--allow-composite-ai` — the documented composite-AI path, not a
  missing asset.
- Inventory gate structurally clean: `every_idml_run_present_in_
  build_py: true`, `count_deltas: []` (no frame / style / colour /
  asset count regressions). build.py runs, render runs, preview word
  count 445 vs baseline 444.
- The only inventory_compare exit-2 signal is a non-deterministic
  PDF word-tokenisation jitter ("impressum" vs "impressu"+"m" — the
  same rendered glyphs, clustered differently). No content lost.

The converter was NOT modified at any point.

## Tune outcome — RESIDUAL (preflight not green; accepted)

The `bin/tune-render` -> `bin/tune-fix` loop ran two full passes. The
`y_mm_shift` playbook applied 17 frame y-coordinate corrections and
brought the text-position audits down substantially:

| Audit | Scaffold | After tune |
|---|---|---|
| text_position_audit_jitter | 112 | 22 |
| text_position_audit_structural | 90 | 60 |
| systematic_text_audit | 21 | 10 |
| line_spacing pixel major (>3pt) | 8 | 2 |
| image_frame_visibility invisible | 5 | 4 |

Three manual Stage-2 build.py edits were made (all permitted edits;
no converter touch, no tolerance-list growth):

1. **u141 (DIE GRÜNEN logo)** — switched from `inline_image_data` +
   `SCALETYPE=1` to a direct `image=` reference + `scale_type=0`. The
   `frame_visibility` playbook diagnosed the frame but could not
   auto-apply the swap (the build.py uses raw base64 blobs, not the
   `_inline_brand_icon("file")` helper its regex expects). This is the
   idml-tune SKILL's literal worked example. The logo now renders
   (invisible frames 5 -> 4).
2. **u2cd / u3a0 noinject comments** — added `# noinject:` comments so
   `external_asset_substitution_audit` passes (both are real brand
   assets, not demo photos — must not be AI-substituted).
3. **u3ba y_mm pin** — the y_mm_shift playbook oscillated this small
   frame (+/-2.54mm, never converged) because its drift is a cross-
   renderer line-wrap, not a uniform anchor offset. Pinned back to the
   scaffold original 123.1736 to remove the oscillation noise.

Preflight is NOT green. Remaining failing sub-audits are all the
documented known-issue classes — see TOLERANCES.yml / TOLERANCE_LOG.md
for the 9 rows. Reaching green would require a Stage-1 re-scaffold
(composite-AI split) which is out of this run's scope and time budget.

## Residual drift numbers (final render)

- text_position_audit_structural: 60 large drifts (>5pt)
- text_position_audit_jitter: 22 sub-perceptible drifts (<=5pt)
- systematic_text_audit: 10 sim-actionable frames
- image_frame_visibility_audit: 4 invisible (u2cd, u3e7, u3f0, u3f5)
  + 1 faint false positive (u4a2, white-on-dark, audit gap L-014)
- image_content_audit: 1 broken (u2cd)
- asset_extraction: 1 composite-AI flag
- image_audit: 26 (vector-path + ICC delta)
- visual_diff_regions: 20 hot regions
- run_style_audit: 1 (cross-frame word collision)
- line_spacing pixel: 2 major (>3pt), part of the wrap class

## Tolerances granted (9 rows in TOLERANCES.yml)

No `meta.yml::brand_overrides` or `non_ci_*` entries were added. All
9 tolerances are TOLERANCES.yml accepted-residual rows:

1. `tol:cross-renderer-line-wrap-structural` (scribus-engine) — 60
   structural word-drifts from Scribus wrapping wider than InDesign.
2. `tol:cross-renderer-line-wrap-jitter` (scribus-engine) — 22 sub-
   perceptible drifts, same cause.
3. `tol:systematic-text-actionable-wrap` (scribus-engine) — 10
   sim-actionable frames, mostly "line count differs" wrap.
4. `tol:u2cd-pine-cmyk-jpeg-blank` (authoring-bug) — CMYK JPEG
   renders blank in Scribus 1.6.x; needs sRGB re-export.
5. `tol:social-icons-composite-ai-invisible` (authoring-bug) — left-
   column icons reference an un-split composite; invisible.
6. `tol:composite-ai-social-media-icons-weiss` (authoring-bug) —
   composite-AI flag on the .ai asset.
7. `tol:run-style-headline-cross-extraction-match` (human-review) —
   the audit cross-matched the word "Headline" across two frames.
8. `tol:image-audit-vector-path-and-icc-delta` (scribus-engine) — 26
   vector-path + ICC colour deltas.
9. `tol:visual-diff-regions-residual` (scribus-engine) — page-level
   aggregate of the rows above.

## Items classified human-review / authoring-bug

- **human-review:** `run_style_audit` "Headline" drift (row 7) — a
  cross-frame word collision in the audit, not a real style bug.
  Also u1b0/u1c7/u1e6 line-spacing pixel drift (2.4-2.9pt) classified
  human-review by convergence-review — sub-3pt, within the wrap class.
- **authoring-bug:** u2cd CMYK JPEG (row 4) and the composite-AI
  social icons (rows 5, 6). Both need authoring-side asset work:
  u2cd a sRGB re-export, the social icons a composite split.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 2, left contact column** — the three social-media icons
   (u3e7/u3f0/u3f5) are MISSING in preview (blank where baseline
   shows white icons). The right-column icons (u477/u4a2/u4da) ARE
   present. This is the composite-AI split gap.
2. **Page 2, top-left pine banner (u2cd)** — BLANK in preview where
   baseline shows the pine-trees photo. CMYK JPEG / Scribus limitation.
3. **Page 1, DIE GRÜNEN logo (top-right, u141)** — should now render
   correctly (white logo on dark green); this was fixed this run.
   Confirm it sits in its frame without clipping.
4. **Body-copy paragraphs** — expect line-wrap differences vs the
   baseline (a word or two shifts per line, occasional extra/missing
   line). This is the accepted cross-renderer wrap; not a regression.
5. The `plakat-dunkel-fuer-flyer` photo (u3a0) renders fine (sRGB PNG).
