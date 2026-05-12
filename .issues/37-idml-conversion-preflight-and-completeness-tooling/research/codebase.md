# Codebase Research — Issue #37

**Branch investigated**: `issue/35-idml-to-dsl-converter-strict-bootstrap` at `/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/` (PR #76).
**On `main`**: only `.issues/37-…/ISSUE.md` exists; no code.

## TL;DR build matrix

| Phase / Backport | Status | Path (worktree-relative) | Wired into `--audit`? |
|---|---|---|---|
| **A1** idml_inventory | **BUILT** | `tools/idml_inventory.py` (439 LOC) | YES |
| **A2** baseline_text_audit | **BUILT** | `tools/baseline_text_audit.py` (348 LOC) | YES |
| **A3** baseline_image_audit | **BUILT** | `tools/baseline_image_audit.py` (453 LOC) | YES |
| **A4** `bin/render-gallery --audit` flag | **BUILT** | `tools/render_pipeline.py:_run_audit` (282 LOC inside) | n/a (it IS the wiring) |
| **B1** end-of-conversion frame-count assertion | **NOT BUILT** | (would extend `tools/idml_to_dsl.py`) | n/a |
| **B2** snapshot_slot_baselines.py | **NOT BUILT** | — | NO |
| **B3** `drift_type` classification on `diff_bbox_extract` | **NOT BUILT** | (would extend `tools/diff_bbox_extract.py`) | n/a |
| **C1** `bin/idml-import` single entry | **NOT BUILT** | — | n/a |
| **C2** per-iteration `iteration.jsonl` | **NOT BUILT** | — | n/a |
| **C3** `bin/convergence-review` | **NOT BUILT** | — | n/a |
| **C4** `tools/idml_to_dsl_patterns/` pattern lib | **NOT BUILT** | — | n/a |
| **D5** `tools/reconcile_build_py.py` + inject.yml | **NOT BUILT** | — | n/a |
| **D6** font_audit | **BUILT** | `tools/font_audit.py` (183 LOC) | YES |
| **D7** text_render_audit | **BUILT** | `tools/text_render_audit.py` (213 LOC) | YES |
| **D8** text_position_audit | **BUILT** | `tools/text_position_audit.py` (257 LOC) | YES |
| **E** per_element_drift | **BUILT** | `tools/per_element_drift.py` (133 LOC) | YES |
| **F** run_style_audit | **BUILT** | `tools/run_style_audit.py` (384 LOC) | YES |
| **G** region_color_audit | **BUILT** | `tools/region_color_audit.py` (444 LOC) | YES |
| **E2** line_spacing_audit | **NOT BUILT** | — | n/a |
| **Backport 9** Justification→align mapping | **BUILT (SHIPPED)** | `tools/idml_to_dsl.py:978` `JUSTIFICATION_MAP`; used at L1268, L2272, L2397 | n/a |
| **Backport 10** SCALETYPE=0 default | **BUILT (SHIPPED)** | `tools/sla_lib/builder/primitives.py:789` `scale_type: int = 0` | n/a |
| **Backport 11** DefaultStyle ALIGN | **BUILT (SHIPPED)** | `tools/idml_to_dsl.py:1775-1787` | n/a |
| **Backport 12** per-region visual_diff (grid) | **NOT BUILT** — biggest deliverable | `tools/visual_diff.py` extension target | n/a |

8 of 9 audit tools + 3 converter backports (9/10/11) already shipped. **Remaining scope**: B1, B2, B3, C1-C4, D5, E2, Backport 12, acceptance cross-cutting checks.

## Repo layout

- `/workspace` (main): only issue docs at `.issues/37-…/`.
- `/workspace/.worktrees/35-…/`: in-flight implementation (PR #76).
- No `CLAUDE.md` at repo root.
- `.issues/config.yaml`: opus for research/plan, sonnet for execute, `commit_artifacts: true`.

## Templates inventory

- 9 templates total. **4 have baseline.pdf + diff.yml** (audit-eligible):
  - `kandidat-falzflyer-din-lang-gruenes-cover-v2` (IDML-sourced, canonical regression target)
  - `plakat-a1-hochformat`, `postkarte-a6-kampagne`, `zeitung-a4-grun`

## Detailed interfaces

```
<interfaces>

# ===========================================================================
# Phase A1 — tools/idml_inventory.py
# Wired: render_pipeline.py:694-712
# Output: build/validation/<slug>/inventory.yml
# Tests: tests/unit/test_idml_inventory.py (311 LOC)
# ===========================================================================
PAGE_ITEM_TAGS = frozenset({"Rectangle", "Polygon", "Oval", "TextFrame",
                            "Image", "PDF", "Group", "GraphicLine"})
def run_inventory(idml_path, build_py_path, template=None) -> dict
# CLI: python3 tools/idml_inventory.py --idml PATH --build-py PATH --out PATH [--template SLUG]
# YAML: template, idml_path, build_py_path, spreads[*: spread_id, page,
#       elements_total, elements_emitted, elements_dropped[*]], elements_extra_global[*]

# ===========================================================================
# Phase A2 — tools/baseline_text_audit.py
# Wired: render_pipeline.py:715-735
# Output: build/validation/<slug>/text_audit.yml
# ===========================================================================
def run_text_audit(baseline_pdf, build_py_path, template=None) -> dict
# CLI: python3 tools/baseline_text_audit.py --baseline PATH --build-py PATH --out PATH
# YAML: pages[*: page, lines_total, lines_matched, lines_unmatched[*]]

# ===========================================================================
# Phase A3 — tools/baseline_image_audit.py
# Wired: render_pipeline.py:738-760
# ===========================================================================
def run_image_audit(baseline_pdf, build_py_path, template=None) -> dict
# YAML: pages[*: raster, vector_paths], composite_strips[*]

# ===========================================================================
# Phase D6 — tools/font_audit.py
# Wired: render_pipeline.py:762-787
# ===========================================================================
def run_font_audit(preview_pdf, baseline_pdf, template="") -> dict
# CLI exit 1 if missing variants
# YAML: baseline_fonts, preview_fonts, missing_in_preview, extra_in_preview, ok

# ===========================================================================
# Phase D7 — tools/text_render_audit.py
# Wired: render_pipeline.py:789-815
# ===========================================================================
_LIGATURE_FOLD = {"ﬀ":"ff", "ﬁ":"fi", ...}
def run_text_render_audit(preview_pdf, baseline_pdf, template="") -> dict
# YAML: baseline_word_count, preview_word_count, missing_in_preview, extra_in_preview, ok

# ===========================================================================
# Phase D8 — tools/text_position_audit.py
# Wired: render_pipeline.py:817-844
# ===========================================================================
def run_text_position_audit(preview_pdf, baseline_pdf, template="",
                            large_delta_threshold_pt=2.0,
                            common_word_threshold=5) -> dict
# YAML: large_deltas_count, suppressed_common_word_deltas_count, large_deltas[*], ok

# ===========================================================================
# Phase F — tools/run_style_audit.py
# Wired: render_pipeline.py:846-879
# ===========================================================================
def run_style_audit(preview_pdf, baseline_pdf, template="",
                    threshold_size_pt=0.5, common_word_threshold=5) -> dict
# YAML: style_drift_count, suppressed_common_word_drifts_count, style_drifts[*], ok

# ===========================================================================
# Phase E — tools/per_element_drift.py
# Wired: render_pipeline.py:881-908
# ===========================================================================
UNATTRIBUTED_KEY = "__unattributed__"
def aggregate_per_element(diff_bboxes: dict, visual_diff: dict) -> dict
# YAML: pages[*: total_mismatch_pct, total_mismatch_px, bbox_count,
#                top_contributors[*: slot, mismatch_px_summed,
#                                   pct_of_page_mismatch, pct_of_page_total_drift,
#                                   bbox_count]]

# ===========================================================================
# Phase G — tools/region_color_audit.py
# Wired: render_pipeline.py:910-936
# ===========================================================================
def run_region_color_audit(build_py, baseline_pdf, preview_pdf, template,
                           dpi=150) -> dict
# Severity: ok (<3), icc_likely (<15), fill_likely (>=15)
# YAML: by_severity, pattern, frames[*]

# ===========================================================================
# tools/visual_diff.py — Backport 12 extension target
# ===========================================================================
@dataclass
class TemplateTolerance:
    max_pixel_mismatch_pct: float = 1.0
    fuzz_pct: float = 25.0
    per_page: dict = field(default_factory=dict)
    per_region: list = field(default_factory=list)

def compare_pages(baseline, dsl, diff_path, fuzz_pct) -> tuple[int, int]
def crop_for_region(image, dpi, page_w_pt, page_h_pt, bbox_mm) -> Path
def visual_diff(template_sla, baseline_pdf, tolerance, dpi, out_dir
               ) -> tuple[bool, list[PageResult]]

# ===========================================================================
# tools/diff_bbox_extract.py — Phase B3 extension target
# ===========================================================================
def extract_all(out_dir, template_slug=None, threshold=200, min_area_px=100,
                coverage_threshold=0.5, overlay_out=False) -> dict
# Each bbox: bbox_px, bbox_mm, area_px, mismatch_pct_in_bbox,
#            attributed_slot, attribution_overlap_pct, attribution_candidates
# Phase B3 adds: drift_type field

# ===========================================================================
# tools/render_pipeline.py — _run_audit is the wiring hub
# ===========================================================================
def _run_audit(tdir, meta, args) -> tuple[int, str]
# bin/render-gallery [TEMPLATE_ID] [--audit] [--audit-strict] ...

</interfaces>
```

## Where Backport 12 (per-region visual_diff) slots in

**Recommended**: extend `tools/visual_diff.py` directly + add Phase H to `_run_audit`. Pattern:

1. New `grid: {cols: 6, rows: 4}` block in `TemplateTolerance.load()`.
2. New `per_cell: [{col, row, max_pixel_mismatch_pct, fuzz_pct}]` for cell-specific overrides.
3. Reuse `compare_pages()` for per-cell comparison via `convert -crop`.
4. Emit `visual_diff_regions.yml` + heatmap PNG.

## Where Phase E2 (line_spacing_audit) slots in

Sibling to D7/D8/F. Uses `pdfplumber.extract_words()`. Threshold: 0.5pt drift.

## Reusable helpers from sla_lib

- `tools/sla_lib/builder/bbox.py:frame_bbox_mm` — canonical slot bbox computer
- `tools/sla_lib/builder/template_loader.py:load_build_module` — importlib with cache prevention
- `tools/sla_lib/builder/primitives.py:773-845` — `ImageFrame` dataclass

## Critical existing output (reference shape)

`build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/`:
- `inventory.yml`, `text_audit.yml`, `image_audit.yml`, `font_audit.yml`,
  `text_render_audit.yml`, `text_position_audit.yml`, `run_style_audit.yml`,
  `per_element_drift.yml`, `region_color_audit.yml`, `diff_bboxes.json`,
  `visual_diff.json`

All produced today (verified existence in worktree).
