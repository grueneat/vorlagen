# Tolerance Log — 26-03-flyer-a6-hochformat-portrait

Every tolerance, override, frame-geometry clamp, and accepted residual for
this template, with measured drift and classification. Newest first.

| # | What | Values (before → after) | Drift it resolves | Why conservative | Classification |
|---|------|--------------------------|-------------------|------------------|----------------|
| 1 | Frame `u1175` height clamp (build.py) | `h_mm` 81.8444 → 52.0 | Cover headline frame overflowed page 1 by 68pt; Scribus rendered the spill onto PDF page 3 (page-3 text-position drift dropped from dx≈-180pt cascade to ≤6pt). | 52.0mm still fits all 3 visible headline lines (38pt text, ~34.13pt leading → 3×34.13=102pt=36mm, 52mm leaves generous margin) and keeps the frame inside page 1 (y_mm 90.12 + 52 = 142.1 < 148 page height). The IDML's own frame is 34.79mm; the converter's Pattern-9 auto-adjust over-inflated to 232pt by miscounting empty `para`-separator Runs as text lines. | converter-bug (Pattern-9 line-count overshoot) — fixed per-template in build.py; the converter heuristic should be corrected upstream as a follow-up |
| 2 | `# noinject:` on 4 ImageFrames `u115d`, `u1164`, `u1260`, `ubc2` (build.py) | external_asset_substitution_audit: 4 missing → 0 | Cleared `external_asset_substitution_audit` (4 frames flagged "missing INJECT_MAP/noinject"). | These are the genuine IDML-placed content images (Gewessler portrait, radial-gradient overlay, pine-forest photo, dark-plakat background) — present on disk, embedded in the SLA, and the real template content. They are NOT demo placeholders, so library substitution is wrong; `# noinject:` with a content reason is the correct disposition per the audit's own fix hint. | not-a-tolerance (correct disposition); logged for transparency |

## Accepted residuals (preflight not green)

The Stage-2 `bin/tune-render` → `bin/tune-fix` loop could not drive preflight
green; the residual below is accepted per the overnight gate policy
(human-review / scribus-engine classes, never converter-bug-left-unfixed).

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `text_position_audit_structural` | 255 large drifts (>5pt) | scribus-engine | Dominated by cross-renderer line-wrap differences: Scribus and InDesign break the justified bullet-list paragraphs at slightly different words (font-metric / hyphenation differences). One wrap-point difference cascades into dozens of "drifted" words downstream. Page content and frame geometry verified correct (PDF page-by-page word check). Not a converter or routing bug. |
| `text_position_audit_jitter` | 35 sub-perceptible drifts (≤5pt) | scribus-engine | Sub-perceptible (≤5pt) cross-renderer position jitter; below the visible threshold. A residual uniform ~2-6pt offset on several body frames; the `y_mm_shift` playbook entered a 2-cycle limit cycle on these frames (shift +X, next render drift flips sign, shift -X) and could not converge — needs a playbook oscillation guard (follow-up). |
| `systematic_text_audit` | 11 frames sim-actionable | scribus-engine | Same frames as the jitter bucket; the `line_spacing` playbook's simulator returned no rows for these frames so no deterministic leading override could be applied. |
| `image_content_audit` / `image_frame_visibility_audit` | 3 frames broken/invisible: `u1164`, `u1260`, `ubc2` (+`u116b`) | scribus-engine | Known Scribus 1.6.x image-rendering limitation (SCALETYPE handling for scaled PSD/JPG content). The `frame_visibility` playbook ESCALATED ("not inline_image_data form"). Assets are on disk and embedded; the SLA references them correctly. |
| `image_audit` | 40 vector-path delta | scribus-engine | Derivative of the above image-rendering differences plus brand-colour ICC shifts. |
| `inventory` | 1 dropped element (`u1152`) | authoring | `u1152` is a 6.3mm magenta registration/colour-control mark the IDML places ~28mm off the left page edge. The converter correctly skips it as an off-page design artifact (recorded via `# idml-skip:` in build.py); InDesign does not export it to the trimmed PDF either. The inventory audit counts it as "dropped" — it is a deliberate, documented non-emit. |

## Notes
- No `meta.yml::brand_overrides`, `non_ci_*`, or `TOLERANCES.yml` numeric
  growth was required — the residual is cross-renderer fidelity, not a brand
  or CI-rule violation (`region_color_audit` and `run_style_audit` are green).
- No `TOLERANCES.yml` per-element entries were needed; `TOLERANCES.yml` is
  present only as a placeholder documenting that no numeric tolerance was grown.
