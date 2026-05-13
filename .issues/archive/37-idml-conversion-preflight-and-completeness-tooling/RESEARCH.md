# Research — Issue #37: IDML→DSL pre-flight tooling + post-conversion completeness checks

**Date:** 2026-05-12
**Confidence:** HIGH on codebase state and library choices; MEDIUM on per-region grid ergonomics (no industry precedent to anchor); LOW on environment determinism risks (need probe during execute).

## Summary

Issue #37 lands the tooling so future IDML imports converge in **one session at <1 hr**, not 5 hr across multiple sessions, with **structural completeness proven before any drift work begins**. The previous convergence session (issue 35) hit specific bugs that motivated 12 backport candidates.

**Most of Phase A through G is already shipped** in the issue-35 worktree (PR #76): A1/A2/A3 inventory tools, D6/D7/D8 text/font audits, E per-element drift, F run-style audit, G region-color audit — 8 of 9 audit tools built and wired into `bin/render-gallery --audit`. Three of the four backports (9 Justification mapping, 10 SCALETYPE=0 default, 11 DefaultStyle ALIGN) are also shipped.

**The remaining scope of #37** breaks into:

1. **Backport 12 — per-region visual_diff** (largest deliverable; ~6×4 grid; PIL + ImageMagick hybrid; new `visual_diff_regions.yml` + heatmap PNG)
2. **Phase E2 — line_spacing_audit** (already spec'd in ISSUE.md; pdfplumber-based; catches LeadingModel mismatches)
3. **B1 / B2 / B3** — converter completeness assertion, slot baseline snapshots, drift_type classification on bbox extractor
4. **C1 / C2 / C3 / C4** — workflow scaffolding (`bin/idml-import`, `iteration.jsonl`, `bin/convergence-review`, pattern lib)
5. **D5** — `tools/reconcile_build_py.py` + inject.yml overlay
6. **Critical missing gate**: `bin/render-gallery --audit` is NON-BLOCKING by default; need `preflight.yml::ok: bool` single-line oracle and hard-fail on `false`
7. **Bugfixes from pitfalls research** (P0): per-element drift math broken on real data (139% over-attribution); text_position_audit produces garbage when pdfplumber word order ≠ glyph order; run_style_audit silently disagrees with text_render_audit; Backport 10 + 11 have edge cases (mixed Justification frames, image cropping with SCALETYPE=0)

## Recommendation (primary)

**Execute in three independent sub-phases:**

1. **P1 — Critical bugfixes + hard-fail gate** (1-2 days). Fix per_element_drift double-counting, text_position_audit word-order garbage, run_style_audit / text_render_audit disagreement. Add `preflight.yml` with aggregated `ok: bool` + hard-fail `--audit` on `false`.
2. **P2 — Backport 12 (per-region visual_diff)** (2-3 days). Extend `tools/visual_diff.py` with grid mode + per-cell tolerances + heatmap PNG. New `visual_diff_regions.yml`. Wire as Phase H in `_run_audit`.
3. **P3 — Phase E2 (line_spacing_audit) + remaining structural tools** (3-4 days). E2 alone is the highest-leverage remaining item (catches LeadingModel issues). B1/B2/B3/C1-C4/D5 follow.

The tradeoff: P1 must ship first (otherwise P2/P3 audit tools build on broken foundations). P2 is independent of P3 and can run in parallel.

## User Constraints (from prior conversation)

- No `CONTEXT.md` file exists for this issue. The user instructed direct entry into research/plan/execute without discuss phase.
- `commit_artifacts: true` in `.issues/config.yaml` → RESEARCH.md / PLAN.md / EXECUTION.md ship with PR.
- Branch: `issue/37-idml-conversion-preflight-and-completeness-tooling`.
- Issue-35 PR #76 is currently open; #37 work depends on its merge (B12 extends `visual_diff.py` which is on that branch).
- **Memory note** `feedback_fix_generator_not_artifact.md`: when audit surfaces dropped elements, fix the converter, not build.py.

## Codebase Analysis

See [research/codebase.md](research/codebase.md) for full interfaces.

### Build matrix (8 of 9 audit tools shipped)

```
<interfaces>

# All tools live in /workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/tools/
# All wired into render_pipeline.py:_run_audit (line 662-943)
# All outputs land in build/validation/<slug>/

# SHIPPED (re-use, don't rewrite):
tools/idml_inventory.py          → inventory.yml         # A1: IDML PageItem vs build.py anname
tools/baseline_text_audit.py     → text_audit.yml        # A2: pdftotext line presence
tools/baseline_image_audit.py    → image_audit.yml       # A3: pdfimages + vector path count
tools/font_audit.py              → font_audit.yml        # D6: pdffonts comparison
tools/text_render_audit.py       → text_render_audit.yml # D7: word presence
tools/text_position_audit.py     → text_position_audit.yml # D8: word position drift (BUG: glyph-order)
tools/per_element_drift.py       → per_element_drift.yml # E:  per-anname drift attribution (BUG: 139% over-counts)
tools/run_style_audit.py         → run_style_audit.yml   # F:  font/size/color per run (BUG: disagrees with D7)
tools/region_color_audit.py      → region_color_audit.yml # G: ICC vs fill-bug classification
tools/visual_diff.py             → visual_diff.json      # page-wide diff (Backport 12 EXTENSION TARGET)
tools/diff_bbox_extract.py       → diff_bboxes.json      # bbox extraction (B3 EXTENSION TARGET)

# Converter (Backports 9/10/11 SHIPPED):
tools/idml_to_dsl.py:978         JUSTIFICATION_MAP       # Backport 9
tools/sla_lib/builder/primitives.py:789  scale_type=0    # Backport 10 (default flipped)
tools/idml_to_dsl.py:1775-1787   default_style_attrs ALIGN # Backport 11

# NOT BUILT (this issue's scope):
tools/visual_diff_regions.py     → visual_diff_regions.yml + heatmap PNG  # Backport 12
tools/line_spacing_audit.py      → line_spacing_audit.yml                  # Phase E2
tools/snapshot_slot_baselines.py                                            # Phase B2
tools/reconcile_build_py.py + inject.yml                                    # Phase D5
bin/idml-import (single entry)                                              # Phase C1
bin/convergence-review                                                      # Phase C3
build/<slug>/iteration.jsonl (per-iteration log)                            # Phase C2
tools/idml_to_dsl_patterns/                                                 # Phase C4

# Hard-fail gate (CRITICAL missing piece):
preflight.yml with single `ok: bool` aggregating all 9 audit oks            # P1 deliverable

</interfaces>
```

### File paths the executor needs

- `tools/visual_diff.py` — extend with grid mode for Backport 12
- `tools/diff_bbox_extract.py` — extend with `drift_type` field for Phase B3
- `tools/idml_to_dsl.py` — assertion at end of conversion (Phase B1) + Backport 10/11 edge-case fixes
- `tools/render_pipeline.py:_run_audit` — wire Phase H (regions) + E2 + preflight.yml + hard-fail
- `tools/sla_lib/builder/template_loader.py` — reuse `load_build_module`
- `tools/sla_lib/builder/bbox.py` — reuse `frame_bbox_mm` for cell↔slot intersection
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml` — schema extension for grid + per_cell
- `docs/diff-tolerance.md` — update schema docs

## Standard Stack (verified versions)

| Component | Version | Status |
|---|---|---|
| Pillow (PIL) | 12.2.0 | Pinned in Dockerfile; do NOT upgrade |
| lxml | 5.4.0 | apt-installed |
| PyYAML | 6.0.3 | apt-installed |
| pdfplumber | 0.11.9 | Installed but NOT declared in Dockerfile (declare when E2 + region tools land) |
| pdftoppm, pdftocairo, pdfimages, pdftotext, pdffonts | poppler-utils apt | Installed |
| ImageMagick compare/convert/montage | apt | Installed |
| odiff | v3.x | Installed but unused (rejected — perceptual semantics ≠ fuzz_pct) |
| Scribus 1.6.x | apt | Headless render via xvfb |

**Not installed** (do not introduce): numpy, scikit-image, opencv-python, matplotlib, pixelmatch.

## Don't Hand-Roll

- **pdftotext / pdfplumber word extraction** — use existing helpers in `tools/baseline_text_audit.py` (line-mode) and `tools/text_position_audit.py` (word-mode with positions).
- **YAML dump idiom** — `yaml.dump(payload, sort_keys=True, allow_unicode=True, default_flow_style=False)` — used in 7+ existing audit tools.
- **Template build.py loader** — `tools/sla_lib/builder/template_loader.py:load_build_module` (importlib with sys.modules.pop() cache prevention).
- **bbox arithmetic** — `tools/sla_lib/builder/bbox.py:frame_bbox_mm` and `rotated_bbox`.
- **Image diff primitive** — `PIL.ImageChops.difference() + ImageChops.lighter() + Image.histogram()` matches ImageMagick `compare -metric AE -fuzz` semantics.

## Architecture Patterns

### Per-region visual_diff (Backport 12)

```python
# Slot 1 — extend tools/visual_diff.py TemplateTolerance with grid block:
class TemplateTolerance:
    grid: dict = {}                # {cols: 6, rows: 4}
    per_cell: list = []            # [{col, row, max_pixel_mismatch_pct, fuzz_pct}]
    # existing: max_pixel_mismatch_pct, fuzz_pct, per_page, per_region

# Slot 2 — new function in visual_diff.py:
def compare_grid(baseline_png, preview_png, grid_cols, grid_rows,
                 fuzz_pct) -> list[dict]:
    # PIL crop per cell + ImageChops.difference + histogram
    # Return per-cell mismatch_pct + bbox_px

# Slot 3 — wire into _run_audit as Phase H after visual_diff:
# Generate visual_diff_regions.yml and visual_diff_heatmap-page-NN.png
```

### Hard-fail preflight gate (P1)

```yaml
# build/validation/<slug>/preflight.yml
ok: false
generated: 2026-05-12T19:38:00Z
audits:
  inventory:           {ok: true,  issues: 0}
  text_audit:          {ok: false, issues: 3}
  image_audit:         {ok: true,  issues: 0}
  font_audit:          {ok: true,  issues: 0}
  text_render_audit:   {ok: false, issues: 12}
  text_position_audit: {ok: true,  issues: 0}
  run_style_audit:     {ok: true,  issues: 0}
  per_element_drift:   {ok: true,  issues: 0}
  region_color_audit:  {ok: true,  issues: 0}
  line_spacing_audit:  {ok: false, issues: 2}  # Phase E2
  visual_diff_regions: {ok: false, issues: 7}  # Backport 12
hot_issues:           # top 5 most actionable
  - audit: text_render_audit
    message: "12 baseline words missing in preview (e.g. 'diegruenen' x2)"
  - audit: line_spacing_audit
    message: "u376 LINESP 14.3pt declared vs 16.0pt rendered"
```

### Phase E2 line_spacing_audit

```python
# tools/line_spacing_audit.py
def run_line_spacing_audit(preview_pdf, baseline_pdf, template="",
                            threshold_pt=0.5) -> dict:
    # For each TextFrame: extract 3 consecutive lines via pdfplumber
    # Compute median baseline-to-baseline pt gap
    # Compare preview vs baseline; flag if delta > threshold_pt
    # Cross-reference flagged frame's anname → ParaStyle slug
    # Output: {flagged_frames: [{anname, baseline_pt, preview_pt, delta_pt, hint}]}
```

## Common Pitfalls (from research/pitfalls.md)

See [research/pitfalls.md](research/pitfalls.md) for full details.

### P0 — Critical bugs in already-shipped tools

1. **per_element_drift math is broken on real data.** `tools/visual_diff.py` uses `compare -metric AE -fuzz 25%` (pixel mismatch); `tools/diff_bbox_extract.py` uses HSL-saturation > 30% on dilated diff PNG (perceptual). The denominator math in `per_element_drift.py:55` doesn't compensate. **Top-3 slots' `pct_of_page_mismatch` sums to 139% on v2 falzflyer page 0.** Executor agents read "u1ae=53% of page mismatch" and chase the wrong slot.
2. **text_position_audit produces systematic garbage.** Today's v2 yml literally contains `text: :musserpmI` (Impressum reversed), `text: ssi`, `text: pem` — pdfplumber's `extract_words` walks glyphs in PDF content-stream order, not visual order. The "100+ large drifts" are mostly false positives.
3. **run_style_audit disagrees with text_render_audit.** pdftotext: 444 words; pdfplumber: 464 baseline / 458 preview. 6 words missing per pdfplumber but `text_render_audit.ok: true`. Nothing surfaces this.

### P1 — Backport 10/11 edge cases

4. **Backport 10 leaves a hole.** SCALETYPE=0 (ScaleAuto) ignores LOCALX/LOCALY/LOCALSCX/LOCALSCY. When the converter emits non-trivial `local_offset_mm` or `local_scale` from per-Image crop transforms, Scribus renders fit-to-frame anyway. Fix: emit `scale_type=1` when local_offset OR local_scale deviates from defaults.
5. **Backport 11 breaks mixed-Justification frames.** DefaultStyle ALIGN propagates only the FIRST PSR's Justification. Inner PSRs with `align_int=0` don't emit override and silently inherit DefaultStyle. Fix: ALWAYS emit per-paragraph ALIGN explicitly, not just when non-zero.

### P2 — Per-region diff edge cases

6. **Cell-border bleeding** — a misaligned headline at the cell boundary appears as two moderate cells instead of one critical cell. Mitigation: overlap regions slightly (10% padding) or report "hottest connected cell cluster" not just per-cell.
7. **Empty-baseline regions** — cells with all-white baseline pixels (margins) produce artificially clean diffs even when preview has content (overflow text). Mitigation: per-cell threshold should respect ink density.
8. **Default fuzz_pct=25 is too lenient for small text regions** (where every glyph subpixel matters) and too strict for halftone gradients. Mitigation: per-cell fuzz override in `diff.yml`.

### P3 — Convergence-loop discipline

9. **`--audit` is non-blocking by default.** P4 "structural completeness is a hard precondition" is asserted in prose but not enforced in code. Need `preflight.yml::ok: bool` single-line oracle + hard-fail.
10. **Token budget**: agents currently read 9 separate YAMLs. preflight.yml reduces this to ONE file with aggregated verdict.

## Environment Availability

- **CI runs without Gotham Narrow / Vollkorn** (proprietary fonts gitignored). `render-gallery` is dev-container only; CI relies on committed previews + `bin/check-stale-previews`. **Cannot run visual_diff in CI** — only structural checks + sla_lib unit tests run there.
- **Headless Scribus** via `xvfb-run` is established (used by current `tools/visual_diff.py`).
- **pdfplumber not yet declared** in `Dockerfile.claude` despite being installed. Declare it before new tools land that depend on it.
- **Pillow 12 deprecation**: `Image.getdata()` removal scheduled for Pillow 14 (2027-10-15). Use `Image.histogram()` / `Image.tobytes()` instead.

## Project Constraints

- **No `CLAUDE.md`** at repo root.
- **`.issues/config.yaml`**: opus for research/plan, sonnet for execute.
- **Commit message convention**: `<id>: <type>(<scope>): <subject>` — e.g. `37: feat(tools): line_spacing_audit`.
- **No emoji in commits/code/files** (project convention).

## Sources

| Source | Confidence | Notes |
|---|---|---|
| `tools/visual_diff.py:46-87` | HIGH | TemplateTolerance schema for Backport 12 extension |
| `tools/render_pipeline.py:_run_audit:662-943` | HIGH | Audit wire-up pattern |
| `tools/per_element_drift.py:55` | HIGH | Confirmed 139% over-attribution math bug |
| `tools/text_position_audit.py` + live v2 yml | HIGH | "musserpmI" garbage observed |
| `Pillow ImageChops docs` | HIGH | Per-region diff primitive |
| `lxml.de performance benchmarks` | HIGH | lxml stays for IDML parsing |
| `pdfplumber 0.11.9` repo + REPL probe | HIGH | E2 line-spacing measurement |
| `tools/sla_lib/builder/primitives.py:789` | HIGH | Backport 10 shipped state |
| `tools/idml_to_dsl.py:1775-1787` | HIGH | Backport 11 shipped state |
| `BackstopJS / Percy / Chromatic docs` | MEDIUM | No industry precedent for fixed grid sizing |
| `papersizes.org A-paper dimensions` | HIGH | Cell-size sanity (35×74mm for 6×4 A4) |
| `ISSUE.md` Phase E2/Backport 10/11/12 specs | HIGH | Authoritative requirements |
| `feedback_idml_leading_vs_rendered.md` (memory) | HIGH | E2 motivation (LeadingModel mismatch) |
| `feedback_font_fidelity_check.md` (memory) | HIGH | D6 motivation |

## Open Questions for Planner

1. **Hard-fail policy**: should `--audit` (without `--strict`) hard-fail when `preflight.yml::ok=false`? Recommendation: yes — making `--audit-strict` the default and `--audit-soft` the opt-in. Alternative: keep `--audit-strict` separate; require executor agents to ALWAYS pass it.
2. **Backport 12 grid sizing**: 6×4 fixed (24 regions) is a reasonable default for A4. Should poster formats (A1, A3) use larger grids? Recommendation: configurable via `diff.yml::grid: {cols, rows}` per template; default 6×4.
3. **Per-cell heatmap PNG location**: `build/validation/<slug>/visual_diff_heatmap-page-NN.png` or `templates/<slug>/visual_diff_heatmap-page-NN.png`? Recommendation: build/ (auto-generated, gitignored).
4. **Phase B1 assertion fail-mode**: hard-error or just warn-and-emit? Recommendation: hard-error on missing IDML elements (the whole motivation is "no silent drop"), warn on extra-in-build.py.

## Cross-references

- Issue 35 PR #76 (in-flight): https://github.com/GrueneAT/vorlagen/pull/76 — must merge before #37 work starts
- Issue 36 PR #75 (merged): bbox extractor — sibling to Backport 12
- Memory: `project_workspace_layout.md`, `feedback_idml_leading_vs_rendered.md`, `feedback_font_fidelity_check.md`, `feedback_fix_generator_not_artifact.md`
