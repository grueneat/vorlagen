# Codebase Research — Issue 38

## Project context

- **No `CLAUDE.md`** anywhere in the repo. Repo-wide constraints come from `MEMORY.md`:
  - `feedback_fix_generator_not_artifact.md` — fix `tools/idml_to_dsl.py`, not `build.py`.
  - `feedback_font_fidelity_check.md` — pdffonts before engine-floor claims.
  - `feedback_verify_reference_before_trusting.md` — measure references against ground truth first.
  - `feedback_idml_leading_vs_rendered.md` — IDML CSR `<Leading>` unreliable.
  - `feedback_preserve_issue_artifacts.md` — archive, don't delete.
  - `feedback_no_claude_attribution.md` — no "claude" in commits/files.

- `.issues/config.yaml`: opus research/plan, sonnet execute, branch `issue/{slug}`, GitHub mirror `GrueneAT/vorlagen`.
- **One existing skill**: `.claude/skills/experiments/SKILL.md` (300 lines) — the model.

## Build matrix (what's shipped vs needed)

| Phase | What exists | Path | Status |
|---|---|---|---|
| A — `bin/idml-import` | Shim pattern in `bin/render-gallery` (15 lines) | new shim + `tools/idml_import.py` | NEW |
| A — converter | `tools/idml_to_dsl.py` (3360 LOC, all Backports 9/10/11/PolyLine shipped) | existing | reuse |
| A — asset export | `tools/links_export.py` (481 LOC, dispatch table for `.ai/.psd/.jpg/.png`) | existing | reuse + extend |
| A — render+audit | `bin/render-gallery --audit-strict` → 11 sub-audits → `preflight.yml` | existing | reuse |
| B — convergence-review | DOES NOT EXIST | new `bin/convergence-review` + `tools/convergence_review.py` | NEW |
| C — skill | Model: `.claude/skills/experiments/SKILL.md` | new `.claude/skills/idml-import/SKILL.md` | NEW |
| D — pattern library | Registry model: `tools/sla_lib/builder/brand_constraints.py::BRAND_CONSTRAINTS` (line 1525) | new `tools/idml_to_dsl_patterns/` | NEW |
| E — asset audit | `links_export.py` has dispatch table but NO composite-AI detection | extend `links_export.py` + new `tools/composite_ai_split.py` | extend + NEW |
| F — inject.yml | Precedent: `meta.yml::brand_overrides` schema-validated via `meta_schema.py` | new `templates/<slug>/inject.yml` + `tools/reconcile_build_py.py` | NEW |

## Interfaces (existing tools the executor must touch)

```
<interfaces>

# tools/links_export.py (481 LOC) — asset extractor
@dataclass(frozen=True)
class AssetEntry:
    original_basename: str  # NFC-normalised
    output_rel: str
    kind: str               # vector_ai|raster_psd|raster_jpg|raster_png
    recipe: str

@dataclass(frozen=True)
class ExportResult:
    out_dir: Path
    manifest_path: Path
    entries: list[AssetEntry]
    skipped: list[tuple[str, str]]

def slugify_stem(name: str) -> str
def export(links_dir, out_dir, *, quiet=False) -> ExportResult
def main(argv: Optional[list[str]] = None) -> int  # CLI

# Dispatch table (lines 154-180):
# .ai  → pdftocairo -png -transp -r 600 -singlefile
# .psd → Pillow ImageCms ICC-aware (docstring lies, says convert -flatten)
# .jpg/.jpeg → passthrough (.jpeg→.jpg rename)
# .png → passthrough
# else → skipped[] (no raise)

# tools/idml_to_dsl.py (3360 LOC) — converter
def convert(source, output, template_id, assets_dir, logo_map_path=None,
            asset_map_path=None, allow_dropped_pageitems=False) -> None
def main(argv) -> int

# Shipped backports (locked on main):
JUSTIFICATION_MAP = {"LeftAlign":0,"CenterAlign":1,"RightAlign":2,
                     "FullyJustified":3,"LeftJustified":3,
                     "RightJustified":3,"CenterJustified":3}  # line 992
# scale_type=1 emitted only when local_scale/local_offset_pt deviate (lines 2040-2061)
# default_style ALIGN + per-paragraph paragraph_attrs={'ALIGN':N} (lines 2305-2390)
# PolyLine PLINEEND/PLINEJOIN from IDML EndCap/EndJoin (lines 1858-1879)

# CLI flags:
#   --template-id SLUG (REQUIRED)
#   --asset-map PATH (PREFERRED — Phase 2 manifest)
#   --assets-dir PATH (legacy; hardcoded default is wrong for non-v2-falzflyer!)
#   --logo-map PATH (legacy)
#   --allow-dropped-pageitems (debug bypass)
# Auto-invokes tools/links_export.py if neither asset-map nor logo-map given.

# tools/render_pipeline.py (1444 LOC) — orchestrator
def _run_audit(tdir, meta, args) -> tuple[int, str]  # line 662
def _build_preflight(tdir, meta, audit_results) -> dict  # line 1097
def _verify_brand_fonts() -> None  # line 262 — HARD-FAILS if fc-list has <30 gruene fonts
def main(argv) -> int

# Audit chain order in _run_audit:
# A1 inventory → A2 baseline_text → A3 baseline_image → D6 font →
# D7 text_render → D8 text_position → F run_style → E2 line_spacing →
# E per_element_drift (diagnostic only) → G region_color (diagnostic only) →
# H visual_diff_regions

# tools/sla_lib/builder/brand_constraints.py (registry pattern, line 1525)
class BrandRule(Protocol):
    id: str
    name: str
    def check(self, doc) -> list[Violation]: ...

BRAND_CONSTRAINTS: list[BrandRule] = [_make_rule(...), ...]  # 16 rules

# tools/sla_lib/builder/meta_schema.py
def load_brand_overrides(slug, root) -> set[str]  # JSON-Schema validated
def load_ci_overrides(slug, root) -> dict          # non_ci_styles/colors/layers

# tools/idml_meta_stub.py (92 LOC) — slot block emitter
def main(argv) -> int  # outputs slots: YAML for paste into meta.yml

</interfaces>
```

## Audit YAML schemas (post-#37, on main)

```
<interfaces>

# build/validation/<slug>/preflight.yml
{template, ok: bool,
 audits: {<name>: {ok: bool, issues: int, detail: str}, ...},
 hot_issues: [{audit, issues, message}]}

# inventory.yml
{template, spreads: [{spread_id, page, elements_total, elements_emitted,
                      elements_dropped: [{self, type, bbox_pt?, hint}]}],
 elements_extra_global: [{anname, type_in_build_py, hint}]}

# text_audit.yml
{template, pages: [{page, lines_unmatched: [...]}]}

# image_audit.yml
{template, pages: [{vector_paths: {emitted, baseline, delta}, raster_counts}],
 composite_strips: [...]}

# font_audit.yml
{template, baseline_fonts, preview_fonts,
 missing_in_preview: [str], extra_in_preview: [str], ok}

# text_render_audit.yml
{template, baseline_word_count, preview_word_count,
 missing_in_preview: {word: count}, extra_in_preview: {word: count}, ok}

# text_position_audit.yml
{template, threshold_pt, common_word_threshold,
 large_deltas_count, suppressed_common_word_deltas_count,
 suppressed_unmatched_word_count,
 large_deltas: [{text, page, baseline_xy_pt, preview_xy_pt, dx_pt, dy_pt, severity}],
 ok}

# run_style_audit.yml
{template, baseline_word_count, preview_word_count, threshold_size_pt,
 common_word_threshold, style_drift_count,
 suppressed_common_word_drifts_count,
 style_drifts: [{text, page, baseline:{fontname,size,color},
                 preview:{...}, drift:{fontname,size_pt,color}, severity}],
 ok, extraction_engine_disagreement?: {...}}

# per_element_drift.yml (DIAGNOSTIC ONLY in preflight)
{template, pages: [{page, total_mismatch_pct, total_mismatch_px,
                    bbox_count, normalisation_factor,
                    top_contributors: [{slot, mismatch_px_summed,
                                        pct_of_page_mismatch,
                                        pct_of_page_total_drift,
                                        bbox_count}]}]}

# region_color_audit.yml (DIAGNOSTIC ONLY in preflight)
{template, by_severity: {ok, icc_likely, fill_likely},
 pattern: "predominantly_icc_drift"|"concentrated_fill_bugs"|"mixed",
 frames: [{anname, page, type, bbox_mm, baseline_rgb, preview_rgb,
           mean_delta, rms_delta, severity}]}

# line_spacing_audit.yml
{template, threshold_pt,
 line_spacing_drift_count,
 line_spacing_drift: [{anname, page, para_style,
                       baseline_linesp_pt, preview_linesp_pt,
                       delta_pt, recommendation}],
 ok}

# visual_diff_regions.yml
{pages: [{page, grid: {cols, rows},
          regions: [{col, row, mismatch_pct, pass}],
          hot_regions: [...]}], ok}

# diff_bboxes.json (POST-#37: drift_type field added)
{dpi, template_slug,
 pages: [{page, delta_png,
          bboxes: [{bbox_px, bbox_mm, area_px, mismatch_pct_in_bbox,
                    attributed_slot, attribution_overlap_pct,
                    attribution_candidates,
                    drift_type: "missing"|"extra"|"position"|"text"|"unknown"}]}]}

# visual_diff.json
{template, pass, pages: [{page, mismatch_pct, mismatch_pixels, delta_png}]}

</interfaces>
```

## Templates state

- 9 templates total. 4 have baseline.pdf + diff.yml (audit-eligible): v2-falzflyer (IDML-sourced), plakat-a1-hochformat, postkarte-a6-kampagne, zeitung-a4-grun.
- v2-falzflyer `build.py` has **14 `# P5/inject` comments** (the seed data for Phase F migration).
- v2-falzflyer `meta.yml` has **5 brand_overrides** silently masking known drift classes (line_spacing_0.9, font_family, bleed_3mm, inside_page, image_text_overlap).
- `previews_for_sla:` is a SHA256 pin auto-updated by `bin/render-gallery`; `bin/check-stale-previews` enforces it.

## Critical caveats

1. **`tools/idml_to_dsl.py:--assets-dir` default is hardcoded to a v2-falzflyer-specific path.** Any new template MUST use `--asset-map`.
2. **`build.py` emits absolute worktree paths** (`/workspace/.worktrees/35-…/shared/assets/…`). Re-emission from a different worktree breaks. Must be fixed during Phase D refactor.
3. **`region_color_audit` and `per_element_drift` are diagnostic-only in preflight** (forced `ok=True` at `render_pipeline.py:1206-1217`). Issue 38 P8 may need to change this for `fill_likely` count.
4. **`tools/links_export.py` docstring lies about `.psd`** — actual impl uses Pillow ImageCms.
5. **No `tools/sla_lib/tests/idml_fixtures/`** — IDML fixtures are in-memory `BytesIO` zipfiles (see `tests/unit/test_idml_inventory.py` pattern).
6. **`_verify_brand_fonts()` hard-fails if <30 gruene fonts available.** `bin/idml-import` must call it before converter to avoid opaque render failure.
7. **`drift_type` enum currently emits only 5 values** (`missing`/`extra`/`position`/`text`/`unknown`); reserved values `scale`/`rotation`/`color` exist in the schema but aren't yet emitted.
8. **#35's "engine floor" was wrong twice in the same session** (Backports 9 + 10). The audit gates that would have caught both didn't exist. #38 P2 must prevent recurrence via machine-checked classification.

## Convergence-loop discipline gaps from #35

Five `brand_overrides` were silently added in #35 to make CI pass — each one hid a real converter or audit gap:

| Disabled rule | Reason given | Drift it hid |
|---|---|---|
| `brand:line_spacing_0.9` | "IDML emits these verbatim" | Backport 9 / E2 (whole session) |
| `brand:font_family` | "2 frames fall back to Times Roman" | Converter font-resolution gap (still open) |
| `brand:bleed_3mm` | "IDML authored with bleed=0" | Authoring issue, no detection |
| `brand:inside_page` | "Decorative shapes outside trim" | Possibly authoring, never measured |
| `brand:image_text_overlap` | "Impressum overlaps polygon by design" | Possibly legit, no test gate |

Plus `ci_overrides.non_ci_styles` grew to 6 entries — every `idml/<style>` emitted by the converter.

**#38 P4 mechanism**: a CI gate `tools/check_overrides_growth.py` that diffs `meta.yml::brand_overrides|ci_overrides` between branches and requires a corresponding `inject.yml::reason` entry or per-template `TOLERANCE_LOG.md` row.

## Test infrastructure

- `pytest` (not unittest); `tests/unit/test_*.py` + `tests/integration/test_*.py`; `tools/sla_lib/tests/test_*.py` for sla_lib internals.
- Synthetic IDML fixtures: in-memory `io.BytesIO` + `zipfile.ZipFile` (canonical example: `tests/unit/test_idml_inventory.py`). No on-disk fixture directory.
- `Dockerfile.claude` pins `SimpleIDML==1.3.1`. Don't upgrade.
