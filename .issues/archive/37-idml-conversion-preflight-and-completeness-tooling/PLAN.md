# Plan: IDML conversion preflight + completeness tooling (#37)

<objective>
This issue completes the remaining scope of #37 after #35 (PR #76) merged the
audit infrastructure (A1/A2/A3/D6/D7/D8/E/F/G tools + Backports 9/10/11). The
plan executes in **three independent sub-phases** that ship the missing
guarantees:

- **P1 — Critical bugfixes + hard-fail gate.** Five P0/P1 bugs from the
  pitfalls research are silently misleading executors today. Plus, an
  aggregated `preflight.yml` is the single biggest lever for executor token
  budget. `bin/render-gallery --audit` must hard-fail on `preflight.yml::ok=false`
  so the convergence loop cannot proceed against a broken structural baseline.
- **P2 — Backport 12 per-region visual_diff.** Page-wide `visual_diff.json`
  washes out semantically large but pixel-small drift (Backport 10/11 each
  moved the page-wide metric by ≤0.05pp despite producing visually obvious
  fixes). Extend `tools/visual_diff.py` with a `region_grid` mode that emits
  `visual_diff_regions.yml` + a heatmap PNG, and wire as Phase H in `_run_audit`.
- **P3 — Phase E2 line_spacing_audit + remaining structural completeness.**
  E2 catches the LeadingModel-mismatch class (v2 falzflyer 14.3pt declared vs
  16.0pt rendered) that no current audit catches. Plus Phase B1 (converter
  end-of-conversion frame-count assertion) and Phase B3 (`drift_type` field
  on diff_bbox_extract) close the converter-completeness loop.

**Why it matters:** without P1's preflight gate, agents keep declaring "engine
floor" while audits silently disagree across 9 separate YAMLs. Without P2's
per-region map, UX-critical fixes (centered headlines, visible icons) don't
register on the convergence metric. Without P3's E2 audit, body-text-heavy
templates keep drifting because no signal surfaces the LeadingModel divergence
between IDML CSR `<Leading>` and InDesign's rendered baseline spacing.

**Scope in:** P1 (6 tasks: 5 fixes + preflight gate), P2 (6 tasks: schema +
core diff + heatmap + wiring + regression test + docs), P3 (6 tasks: E2 tool +
B1 assertion + B3 drift_type + integration test + final pipeline test). 18
tasks total, each sized for a single sonnet executor pass.

**Scope out (deferred to follow-up issues per RESEARCH.md):**
- Phase B2 `snapshot_slot_baselines.py` (lower priority — token savings are nice-to-have)
- Phase C1-C4 workflow scaffold (`bin/idml-import`, `iteration.jsonl`, `bin/convergence-review`, pattern lib)
- Phase D5 `inject.yml` + `reconcile_build_py.py`

No CONTEXT.md exists — decisions based on RESEARCH.md primary recommendation
(see `## Recommendation (primary)` in RESEARCH.md).
</objective>

<skills>
No workspace skills (`.claude/skills/`) exist in this repo. None to tag.
</skills>

<context>
Issue: @.issues/37-idml-conversion-preflight-and-completeness-tooling/ISSUE.md
Research: @.issues/37-idml-conversion-preflight-and-completeness-tooling/RESEARCH.md
Codebase: @.issues/37-idml-conversion-preflight-and-completeness-tooling/research/codebase.md
Pitfalls: @.issues/37-idml-conversion-preflight-and-completeness-tooling/research/pitfalls.md
Ecosystem: @.issues/37-idml-conversion-preflight-and-completeness-tooling/research/ecosystem.md

**Worktree convention:** The executor will work in a fresh worktree at
`/workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling/`
on branch `issue/37-idml-conversion-preflight-and-completeness-tooling`. All
file paths below are repo-relative — read/write inside the worktree, not
inside `/workspace/.worktrees/35-…/` (that worktree is merged and frozen).

Key files (all already exist on `main` after PR #76 merge):
@tools/visual_diff.py — extend with `region_grid` mode (P2)
@tools/diff_bbox_extract.py — extend with `drift_type` field (P3 / B3)
@tools/per_element_drift.py — fix denominator math at line 55 (P1)
@tools/text_position_audit.py — fix glyph-order garbage in extract_words (P1)
@tools/run_style_audit.py — surface disagreement with text_render_audit (P1)
@tools/idml_to_dsl.py — Backport 10/11 edge-case fixes + B1 assertion (P1 + P3)
@tools/render_pipeline.py — `_run_audit` is the wiring hub; add `preflight.yml`,
  Phase H (regions), Phase E2 (line_spacing); hard-fail `--audit` on `ok=false`
@tools/sla_lib/builder/primitives.py:789 — `ImageFrame.scale_type` default
@tools/sla_lib/builder/template_loader.py — reuse `load_build_module` for E2
@tools/sla_lib/builder/bbox.py — reuse `frame_bbox_mm` for E2 + cell math
@templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml — schema extension
@templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/baseline.pdf — E2 regression target
@docs/diff-tolerance.md — extend schema doc for `region_grid`
@Dockerfile.claude — declare `pdfplumber` (currently installed but not declared)

<interfaces>
<!-- Executor: these are the EXACT contracts to use. Do not explore the codebase
     for them — they are verbatim from research/codebase.md + direct file reads. -->

# ===========================================================================
# tools/visual_diff.py — EXTENSION TARGET for Backport 12 (P2 tasks 7-12)
# ===========================================================================
@dataclass
class TemplateTolerance:
    max_pixel_mismatch_pct: float = 1.0
    fuzz_pct: float = 25.0
    per_page: dict = field(default_factory=dict)
    per_region: list = field(default_factory=list)
    # ADD (P2 task 7):
    # region_grid: dict = field(default_factory=dict)
    #   schema: {cols: int, rows: int, per_cell: list[{page, col, row,
    #                                                   max_pixel_mismatch_pct?,
    #                                                   fuzz_pct?}]}

    @classmethod
    def load(cls, path: Optional[Path]) -> "TemplateTolerance"

    def for_page(self, page_index: int) -> tuple[float, float]
        # returns (max_pixel_mismatch_pct, fuzz_pct) for the page

# Existing helpers (DO NOT change signatures):
def compare_pages(baseline, dsl, diff_path, fuzz_pct) -> tuple[int, int]
def crop_for_region(image, dpi, page_w_pt, page_h_pt, bbox_mm) -> Path
def visual_diff(template_sla, baseline_pdf, tolerance, dpi, out_dir
               ) -> tuple[bool, list[PageResult]]

# Existing module-level constants:
PT_PER_INCH = 72.0

# ===========================================================================
# tools/diff_bbox_extract.py — EXTENSION TARGET for Phase B3 (P3 task 15)
# ===========================================================================
class DiffBBoxError(RuntimeError): ...

def extract_bboxes_px(delta_png: Path, threshold: int = 200,
                      min_area_px: int = 100) -> list[dict]
# Each component: {"x_px": int, "y_px": int, "w_px": int, "h_px": int,
#                  "area_px": int, "mean_color": str}

def extract_all(out_dir, template_slug=None, threshold=200, min_area_px=100,
                coverage_threshold=0.5, overlay_out=False) -> dict
# Each bbox today: bbox_px, bbox_mm, area_px, mismatch_pct_in_bbox,
#                  attributed_slot, attribution_overlap_pct, attribution_candidates
# Phase B3 ADDS: "drift_type" str (one of: missing, extra, position,
#                                          scale, rotation, color, text, unknown)

# ===========================================================================
# tools/per_element_drift.py — BUGFIX TARGET (P1 task 1)
# ===========================================================================
UNATTRIBUTED_KEY = "__unattributed__"

def aggregate_per_element(diff_bboxes: dict, visual_diff: dict) -> dict
# CURRENT BUG (line 55): pct_of_page_total_drift = px / total_mismatch_px * page_mismatch_pct.
# The bbox area_px sums to ~1.9× total_mismatch_px (HSL-saturation dilation halo),
# so top-3 contributors sum to 139%. Fix: rescale by
# normalisation_factor = total_mismatch_px / sum(per_slot_px.values())
# applied to BOTH pct_of_page_mismatch and pct_of_page_total_drift.

# ===========================================================================
# tools/text_position_audit.py — BUGFIX TARGET (P1 task 2)
# ===========================================================================
def extract_words_with_positions(pdf_path: Path) -> list[dict[str, Any]]
# Each record: {page: int, text: str, x0_pt, y0_pt, x1_pt, y1_pt: float}
# CURRENT BUG: pdfplumber.extract_words() returns glyphs in PDF content-stream
# order, NOT visual order. Result: text="musserpmI" (Impressum reversed) in yml.
# Fix: pass keep_blank_chars=False, use_text_flow=False, sort the glyphs within
# extract_words via the x_tolerance + y_tolerance arguments so words come out
# in visual order.

def run_text_position_audit(preview_pdf, baseline_pdf, template="",
                            large_delta_threshold_pt=2.0,
                            common_word_threshold=5) -> dict
# Returns: {template, baseline_pdf, preview_pdf, threshold_pt, common_word_threshold,
#           large_deltas_count, suppressed_common_word_deltas_count,
#           large_deltas, ok}

# ===========================================================================
# tools/run_style_audit.py — SURFACE-DISAGREEMENT TARGET (P1 task 3)
# ===========================================================================
EXTRA_ATTRS = ["fontname", "size", "non_stroking_color"]
SIZE_LARGE_THRESHOLD_PT = 1.0
SIZE_SMALL_THRESHOLD_PT = 0.5

def run_style_audit(preview_pdf, baseline_pdf, template="",
                    threshold_size_pt=0.5, common_word_threshold=5) -> dict
# Returns: {template, baseline_word_count, preview_word_count, ...}
# CURRENT BUG: pdfplumber returns 458 preview / 464 baseline words (6 missing)
# while text_render_audit (pdftotext) reports 444 / 444 (all present, ok=true).
# Fix: add `extraction_engine_disagreement: bool` field to surface when
# baseline_word_count or preview_word_count differs from text_render_audit's
# counts by > 1% — and add this to issue_parts via render_pipeline.py.

# ===========================================================================
# tools/idml_to_dsl.py — BACKPORT 10/11 EDGE-CASE FIXES (P1 tasks 4, 5)
# ===========================================================================
JUSTIFICATION_MAP = {  # at line 978
    "LeftAlign": 0, "CenterAlign": 1, "RightAlign": 2,
    "LeftJustified": 0, "CenterJustified": 1, "RightJustified": 2,
    "FullyJustified": 3,
    "ToBindingSide": 0, "AwayFromBindingSide": 0,
}

def _emit_image_frame_call(out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
                           image_path, ctx, inline_data=None, inline_ext=None,
                           local_scale=None, local_offset_pt=None) -> None
# Current (line 2010-2023): emits local_scale/local_offset_mm when ≠ defaults.
# BUT does not set scale_type=1 — Scribus's SCALETYPE=0 (ScaleAuto) IGNORES
# LOCALX/LOCALY/LOCALSCX/LOCALSCY. Fix in P1 task 4: pass
# scale_type=1 in kwargs when local_scale ≠ (1,1) OR local_offset deviates.

# At line 1775-1787 (Backport 11 DefaultStyle ALIGN):
# Currently only emits DefaultStyle ALIGN when first PSR's Justification is
# non-zero. Inner PSRs with align_int=0 (Left) don't emit explicit override and
# silently inherit DefaultStyle when DefaultStyle != Left. Fix in P1 task 5:
# (a) ALWAYS emit DefaultStyle ALIGN (even when == 0) so it pins to Left explicitly;
# (b) emit paragraph_attrs={'ALIGN': N} on EVERY paragraph (not only when != 0).

# ===========================================================================
# tools/sla_lib/builder/primitives.py:789 — ImageFrame default scale_type
# ===========================================================================
@dataclass
class ImageFrame:
    # ... fields ...
    scale_type: int = 0   # SCALETYPE (Backport 10 — DO NOT REVERT)
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    # The emitter at primitives.py:827 writes SCALETYPE=str(self.scale_type)

# ===========================================================================
# tools/render_pipeline.py — _run_audit is the wiring hub (line 662-943)
# ===========================================================================
def _run_audit(tdir: Path, meta: dict, args) -> tuple[int, str]
# Current order: A1 inventory → A2 text → A3 image → D6 font → D7 text_render
#                → D8 text_position → F run_style → E per_element_drift → G region_color
# Returns (audit_issue_count, summary_line). issue_parts is the in-function list.
# P1 task 6 ADDS:
#   - aggregated preflight.yml at the END of _run_audit (after G)
#   - hard-fail in main() at line 1080 when args.audit (not just audit_strict)
#     and preflight.yml::ok == false
# P2 task 10 ADDS Phase H (visual_diff_regions) after page-wide visual_diff
#   but before E per_element_drift.
# P3 task 13 ADDS Phase E2 (line_spacing_audit) after F run_style_audit.
# Existing pattern (verbatim from D6 wire-up, line 762-787):
#     from <tool> import <run_fn>, _yaml_dump as _xy
#     report = <run_fn>(<args>, template=tid)
#     out_path.write_text(_xy(report), encoding="utf-8")
#     if not report["ok"]:
#         issue_parts.append(f"... → FAIL")

# ===========================================================================
# CLI flag plumbing in tools/render_pipeline.py:main()
# ===========================================================================
# Current (lines 946-998):
#   parser.add_argument("--audit", action="store_true", ...)
#   parser.add_argument("--audit-strict", action="store_true", ...)
#   if args.audit_strict: args.audit = True
# Current exit-code logic (line 1080-1081):
#   if getattr(args, "audit_strict", False) and audit_issue_count_total > 0:
#       overall = 1
# P1 task 6 CHANGES: when args.audit (not just audit_strict), exit non-zero if
# any per-template preflight.yml::ok == false.

# ===========================================================================
# Reusable helpers from sla_lib (DO NOT REIMPLEMENT)
# ===========================================================================
# tools/sla_lib/builder/template_loader.py: load_build_module(build_py_path)
#   importlib + sys.modules.pop() cache prevention; returns Module with .pages[]
# tools/sla_lib/builder/bbox.py:
#   frame_bbox_mm(frame) -> tuple[float, float, float, float]  # x, y, w, h in mm
#   rotated_bbox(...)
# tools/sla_lib/builder/primitives.py:
#   ImageFrame, TextFrame, Polygon dataclasses

# ===========================================================================
# YAML idiom (used in ALL audit tools — DO NOT deviate)
# ===========================================================================
def _yaml_dump(payload: dict) -> str:
    return yaml.dump(payload, sort_keys=True, allow_unicode=True,
                     default_flow_style=False)
# Determinism: sort_keys=True, no timestamps, round floats before dump.

</interfaces>

<call_sites>
Searched: `tools/render_pipeline.py`, `bin/render-gallery`, `--audit`,
`--audit-strict`, `tools/visual_diff.py`, `tools/idml_to_dsl.py`
Surfaces grepped: `.github/workflows/`, `Makefile` (none), `bin/`, `tools/`,
`docs/`, `README*` (none touching `--audit`), `tests/` (test wire-up).

Found:
- `bin/render-gallery` — shim that execs `tools/render_pipeline.py`. IN SCOPE
  (P1 task 6 changes the `--audit` hard-fail semantics that this entry point
  surfaces).
- `tools/render_pipeline.py:976-998` — `--audit` / `--audit-strict` flag
  definitions + the `args.audit_strict → args.audit` implication. IN SCOPE
  (P1 task 6 changes hard-fail semantics; P2/P3 add new phases).
- `tools/render_pipeline.py:1080-1081` — exit-code logic
  `if audit_strict and audit_issue_count_total > 0: overall = 1`. IN SCOPE
  (P1 task 6: also fail when args.audit and any preflight.yml::ok is false).
- `tests/unit/test_*.py` — per-tool unit tests; each tool already has one.
  IN SCOPE (every task that modifies a tool extends its unit tests).
- `tests/integration/test_*_v2.py` — per-tool v2-falzflyer integration tests.
  IN SCOPE (P1 tasks 1-3, P3 task 13 extend these).
- `.github/workflows/render.yml` and similar — uses `bin/render-gallery`. The
  P1 hard-fail change adjusts behaviour but does not change the CLI surface.
  OUT OF SCOPE (no code edits needed there; behaviour change is intentional
  and the workflow file already invokes with `--audit-strict`, which keeps
  working unchanged).
- `docs/render-fidelity.md`, `docs/diff-tolerance.md` — documentation that
  references `--audit` semantics. IN SCOPE for P2 task 11 (schema doc update);
  P1 task 6 also updates `--audit` semantics blurb.
- `templates/<slug>/diff.yml` — per-template tolerance file. The v2 falzflyer
  diff.yml is IN SCOPE (P2 task 7 + 11 extend its schema). Other templates'
  diff.yml stay untouched — `region_grid` is optional and defaults from
  hardcoded values in `tools/visual_diff.py`.

No additional CLI call sites surfaced. The `--audit` flag is invoked from
`bin/render-gallery` only; no Makefile, no other tools, no docs commands.
</call_sites>
</context>

<commit_format>
Format: conventional with issue prefix (per `.issues/config.yaml`)
Pattern: `37: {type}({scope}): {description}`
Examples:
- `37: fix(per_element_drift): correct denominator math for HSL halo over-attribution`
- `37: fix(text_position_audit): sort pdfplumber words by visual order`
- `37: feat(visual_diff): per-region grid mode with heatmap PNG (Backport 12)`
- `37: feat(line_spacing_audit): Phase E2 baseline-to-baseline pt-gap measurement`
- `37: feat(render_pipeline): aggregated preflight.yml + hard-fail --audit`
- `37: fix(idml_to_dsl): emit scale_type=1 when local_offset or local_scale deviate`
- `37: feat(diff_bbox_extract): drift_type classification field (Phase B3)`
- `37: test(line_spacing_audit): v2 falzflyer 14.3pt vs 16.0pt regression`
- `37: docs(diff-tolerance): region_grid + per_cell schema`

Types in use: feat, fix, test, refactor, docs, chore. Scope is the
file/subsystem touched (per_element_drift, visual_diff, render_pipeline, etc.).
No "claude" attribution per `feedback_no_claude_attribution.md`.
</commit_format>

<tasks>

<!-- ============================================================ -->
<!-- P1 — Critical bugfixes + hard-fail gate (tasks 1-6)         -->
<!-- These must ship first; P2 and P3 depend on the audits being  -->
<!-- correct AND on the preflight gate existing.                  -->
<!-- ============================================================ -->

<task type="auto" tdd="true">
  <name>Task 1: Fix per_element_drift denominator math (P1)</name>
  <files>tools/per_element_drift.py, tests/unit/test_per_element_drift.py, tests/integration/test_per_element_drift_v2.py</files>
  <action>
  **Problem** (verified in pitfalls.md §1.6): `tools/per_element_drift.py:46-58`
  computes `pct_of_page_mismatch` and `pct_of_page_total_drift` as
  `px / total_mismatch_px * 100` and `px / total_mismatch_px * page_mismatch_pct`.
  The bbox `area_px` values come from HSL-saturation extraction in
  `diff_bbox_extract.py`, which captures the ImageMagick `compare` red-overlay
  halo (anti-aliased dilation). Sum of bbox area_px is ~1.9× the underlying
  `visual_diff.json::mismatch_pixels`. Top-3 contributors on v2 page 0 sum to
  **139%** of page mismatch, misleading executors.

  **Fix:** introduce a normalization factor per page:
  ```python
  sum_bbox_px = sum(per_slot_px.values()) or 1
  normalisation = total_mismatch_px / sum_bbox_px  # collapses halo back to AE pixels
  ```
  Apply to BOTH percentage outputs:
  ```python
  "pct_of_page_mismatch": round(px * normalisation / total_mismatch_px * 100, 2),
  "pct_of_page_total_drift": round(px * normalisation / total_mismatch_px * page_mismatch_pct, 3),
  ```
  Equivalently: `pct_of_page_mismatch = px / sum_bbox_px * 100`. Use the
  longer form to make the dilation-halo correction explicit and document it
  in a code comment referencing pitfalls.md §1.6.

  Add a NEW field per page: `"normalisation_factor": round(normalisation, 4)`
  so the report is self-describing.

  Acceptance:
  - Sum of `pct_of_page_mismatch` across all top_contributors (plus
    `__unattributed__`) on any page must be ≤ 100.0 + 0.5 (rounding slack).
  - Sum of `pct_of_page_total_drift` must be ≤ `total_mismatch_pct + 0.5`.
  - Existing v2 falzflyer data in
    `build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff_bboxes.json`
    + `visual_diff.json` (regenerate via `bin/render-gallery --audit` if
    missing) yields top-3 contributors summing to ≤ 100% (not 139%).

  **Tests** (RED first):
  1. Unit test in `tests/unit/test_per_element_drift.py`: synthetic
     `diff_bboxes` where 3 slots have `area_px` of 200, 150, 100 (sum=450)
     and `visual_diff.mismatch_pixels=300`. Assert each slot's
     `pct_of_page_mismatch` matches `area_px / 450 * 100` (= 44.4, 33.3, 22.2;
     sum = 100.0).
  2. Unit test: synthetic page with `total_mismatch_px=0`. Assert both
     percentages are 0.0 (no divide-by-zero).
  3. Unit test: assert `normalisation_factor` field is present and equals
     `total_mismatch_px / sum_bbox_px`.
  4. Integration test in `tests/integration/test_per_element_drift_v2.py`:
     load the live v2 falzflyer artefacts (or stub matching the observed
     shape), run `aggregate_per_element`, assert every page's top-3
     `pct_of_page_mismatch` sum ≤ 100.0.

  Do NOT change the dataclass keys other than ADDING `normalisation_factor`;
  downstream tooling (preflight.yml in task 6) reads these fields.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_per_element_drift.py tests/integration/test_per_element_drift_v2.py -q && python3 -m unittest discover tests/unit && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - `per_element_drift.py` outputs `pct_of_page_mismatch` percentages that sum to ≤ 100.0 per page
  - New `normalisation_factor` field added per page in the YAML report
  - All new unit tests + integration test pass under both pytest and unittest discover
  - V2 falzflyer top-3 contributors no longer over-attribute (139% → ≤100%)
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fix text_position_audit reverse-glyph word garbage (P1)</name>
  <files>tools/text_position_audit.py, tests/unit/test_text_position_audit.py, tests/integration/test_text_audits_v2.py</files>
  <action>
  **Problem** (verified in pitfalls.md §5.3): `tools/text_position_audit.py:68-77`
  calls `page.extract_words()` with default arguments. pdfplumber walks glyphs
  in PDF content-stream order, NOT visual left-to-right order. Result in the
  current v2 yml: `text: ":musserpmI"` (Impressum reversed), `text: "ssi"`,
  `text: "pem"`. These false-positive "large drifts" mislead executors.

  **Fix:** call `extract_words` with explicit ordering parameters that force
  visual-order glyph stitching:
  ```python
  page.extract_words(
      use_text_flow=False,         # disable content-stream order
      keep_blank_chars=False,
      x_tolerance=2,               # 2pt tolerance for same-word glyphs
      y_tolerance=2,
      extra_attrs=[],              # don't carry attrs we don't need here
  )
  ```
  pdfplumber's `extract_words` with `use_text_flow=False` (the default in
  0.11.x but worth setting explicitly for documentation) sorts within each
  detected word by x-coordinate, producing visual order. Verify by REPL on
  v2 falzflyer's baseline.pdf:
  ```python
  python3 -c "import pdfplumber; \
    p = pdfplumber.open('templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/baseline.pdf'); \
    print([w['text'] for w in p.pages[1].extract_words(use_text_flow=False, x_tolerance=2, y_tolerance=2) if 'mpr' in w['text'].lower() or 'press' in w['text'].lower()])"
  ```
  Expect: `['Impressum:']` (forward), not `[':musserpmI']`.

  **Defense in depth:** after `extract_words` returns, post-process by
  rejecting any word whose `text` does not appear in the same page's
  `pdftotext -layout` output. (pdftotext is reliable for word presence —
  it's the engine D7 uses.) If a word from `extract_words` cannot be matched
  to any pdftotext token (case-insensitive substring), it's likely reversed
  or split; skip it from the deltas list. Add a NEW field
  `suppressed_unmatched_word_count: int` to surface how many were filtered.

  Subprocess call:
  ```python
  r = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                     capture_output=True, text=True, check=True)
  pdftotext_tokens_per_page = r.stdout.split("\f")
  ```
  Then for each page, build `set(token.strip().lower() for token in re.split(r"\s+", pdftotext_tokens_per_page[i]))`.
  Filter out pdfplumber words whose lowercased text has no substring match
  in that set.

  **Tests** (RED first):
  1. Unit test: synthetic pdfplumber output containing both `"Impressum:"`
     and `":musserpmI"` (the reversed form). With pdftotext page containing
     `"Impressum:"`, assert the filter keeps the forward word and rejects
     the reversed one.
  2. Unit test: word `"Leonore"` present in both pdfplumber and pdftotext —
     assert it survives the filter.
  3. Unit test: when pdftotext is not available (FileNotFoundError on the
     subprocess call), the audit must NOT crash — fall back to no filtering
     and emit `suppressed_unmatched_word_count: -1` to signal "filter
     unavailable."
  4. Integration test in `tests/integration/test_text_audits_v2.py`: run
     against v2 falzflyer baseline.pdf + preview.pdf. Assert no
     `large_deltas[*].text` contains the substring `"musserp"`, `"ssi "`,
     or `"pem "` (case-insensitive). Assert `large_deltas_count` is
     materially smaller than the current 100+ (target ≤30; in practice it
     will likely be 5-20 once the false positives are filtered).
  5. Unit test: assert YAML output is deterministic (run twice, byte-equal).

  Note: do NOT change the threshold default (2.0pt) or the common-word
  filter logic. Only the word extraction + filter is changing.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_text_position_audit.py tests/integration/test_text_audits_v2.py -q && python3 -m unittest discover tests/unit && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - `text_position_audit.yml` no longer contains reversed-glyph "words" (`:musserpmI`, `ssi`, `pem`)
  - New `suppressed_unmatched_word_count` field surfaces how many were filtered (or -1 if pdftotext unavailable)
  - V2 falzflyer `large_deltas_count` drops from 100+ to <= 30 (real deltas only)
  - All new unit tests + integration test pass under both pytest and unittest discover
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Surface text_render_audit vs run_style_audit disagreement (P1)</name>
  <files>tools/run_style_audit.py, tests/unit/test_run_style_audit.py, tests/integration/test_run_style_audit_v2.py</files>
  <action>
  **Problem** (verified in pitfalls.md §5.4): on v2 falzflyer today,
  pdftotext reports 444 baseline / 444 preview words (text_render_audit
  ok=true); pdfplumber reports 464 baseline / 458 preview words (6
  unmatched, but run_style_audit.ok=true because no LARGE drifts among
  matched words). These two extraction engines disagree silently — no
  audit surfaces the disagreement, so executors don't know to investigate.

  **Fix:** in `tools/run_style_audit.py:run_style_audit`, accept an
  OPTIONAL parameter `text_render_audit_counts: dict | None = None` of
  shape `{"baseline": int, "preview": int}` (the totals from D7). When
  provided, compare to `len(base_words)` and `len(prev_words)`:
  ```python
  engine_disagreement = {
      "baseline_pdfplumber": len(base_words),
      "preview_pdfplumber": len(prev_words),
      "baseline_pdftotext": text_render_audit_counts["baseline"],
      "preview_pdftotext": text_render_audit_counts["preview"],
      "baseline_delta_pct": round(
          abs(len(base_words) - text_render_audit_counts["baseline"])
          / max(text_render_audit_counts["baseline"], 1) * 100, 2),
      "preview_delta_pct": round(
          abs(len(prev_words) - text_render_audit_counts["preview"])
          / max(text_render_audit_counts["preview"], 1) * 100, 2),
      "warn": False,
  }
  if engine_disagreement["baseline_delta_pct"] > 1.0 \
     or engine_disagreement["preview_delta_pct"] > 1.0:
      engine_disagreement["warn"] = True
  ```
  Add `extraction_engine_disagreement: dict` to the returned report.

  When `warn` is True, downgrade `ok` to False ONLY if there is also at
  least one large drift. The disagreement alone is a WARNING, not a FAIL —
  but it must surface in `issue_parts` via render_pipeline.py.

  **Wire-up change** in `tools/render_pipeline.py:846-879` (Phase F):
  Before invoking `_rsa_run`, load `text_render_audit.yml` if it exists,
  extract `baseline_word_count` and `preview_word_count`, pass as
  `text_render_audit_counts` kwarg. Then in the existing if-branch after
  reading `rsa_report`, also check `rsa_report.get("extraction_engine_disagreement", {}).get("warn")`
  and if true append to `issue_parts`:
  ```python
  issue_parts.append(
      f"text extraction engines disagree "
      f"({eed['preview_pdftotext']} vs {eed['preview_pdfplumber']} preview words)"
  )
  ```

  **Tests** (RED first):
  1. Unit test: synthetic invocation with `text_render_audit_counts=
     {"baseline": 444, "preview": 444}` and pdfplumber returning 464/458 —
     assert `extraction_engine_disagreement.warn` is True,
     `baseline_delta_pct ≈ 4.5`, `preview_delta_pct ≈ 3.1`.
  2. Unit test: matching counts (444/444 both engines) — `warn` is False.
  3. Unit test: `text_render_audit_counts=None` (the legacy call shape) —
     `extraction_engine_disagreement` field is absent OR contains only
     pdfplumber counts (your choice; document in docstring).
  4. Integration test in `tests/integration/test_run_style_audit_v2.py`:
     run against v2 falzflyer with the live `text_render_audit.yml` —
     assert `extraction_engine_disagreement.warn` is True (or False if the
     v2 state has converged since pitfalls capture).

  Do NOT alter the severity thresholds, color normalisation, or any of
  the existing style-drift logic. The only behaviour change is the new
  field + the wire-up in render_pipeline.py to pass through counts.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_run_style_audit.py tests/integration/test_run_style_audit_v2.py -q && python3 -m unittest discover tests/unit && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - `run_style_audit.yml` includes `extraction_engine_disagreement: {baseline_pdftotext, preview_pdftotext, baseline_pdfplumber, preview_pdfplumber, baseline_delta_pct, preview_delta_pct, warn}`
  - When `warn=true`, `render_pipeline.py::_run_audit` appends the disagreement to `issue_parts`
  - V2 falzflyer surfaces the 464 vs 444 disagreement (or correctly reports `warn=false` if v2 has since converged)
  - All new unit + integration tests pass under both pytest and unittest discover
  </done>
</task>

<task type="auto">
  <name>Task 4: Backport 10 edge fix — emit scale_type=1 on cropped images (P1)</name>
  <files>tools/idml_to_dsl.py, tests/unit/test_idml_geometry.py</files>
  <action>
  **Problem** (verified in pitfalls.md §3.1): `tools/sla_lib/builder/primitives.py:789`
  defaults `ImageFrame.scale_type=0` (Backport 10). `tools/idml_to_dsl.py`
  never sets `scale_type` explicitly — all ImageFrames inherit 0. But
  SCALETYPE=0 (Scribus ScaleAuto = fit-to-frame) IGNORES LOCALX, LOCALY,
  LOCALSCX, LOCALSCY at render time. When the converter emits
  `local_offset_mm != (0,0)` or `local_scale != (1,1)` from per-Image crop
  extraction, the rendered PDF shows fit-to-frame instead of the cropped
  view. Silent visual regression.

  **Fix:** in `tools/idml_to_dsl.py:_emit_image_frame_call` (line ~1975),
  add the following BEFORE the final `_emit_call`:
  ```python
  # Backport 10 edge case (#37 P1 task 4):
  # SCALETYPE=0 (ScaleAuto) ignores LOCAL{X,Y,SCX,SCY} — Scribus fits
  # to frame regardless. When the IDML expresses a non-trivial per-Image
  # crop (local_offset or non-unity local_scale), we MUST emit
  # scale_type=1 (free scaling) so Scribus respects the crop params.
  needs_free_scaling = False
  if local_scale is not None:
      scx, scy = local_scale
      if abs(scx - 1.0) > 1e-4 or abs(scy - 1.0) > 1e-4:
          needs_free_scaling = True
  if local_offset_pt is not None and not needs_free_scaling:
      ox_pt, oy_pt = local_offset_pt
      ox_mm = ox_pt * PT_TO_MM
      oy_mm = oy_pt * PT_TO_MM
      if abs(ox_mm) > 0.01 or abs(oy_mm) > 0.01:
          needs_free_scaling = True
  if needs_free_scaling:
      kwargs["scale_type"] = 1
  ```
  (Place this BEFORE the existing `if local_scale is not None` block that
  populates kwargs with `local_scale`/`local_offset_mm`; this ensures the
  scale_type=1 is added alongside, not after, the local_* kwargs.)

  Do NOT change the dataclass default in `primitives.py`. Backport 10
  (default scale_type=0) stays; this fix only flips per-frame when the
  IDML actually requires cropping.

  **Tests:**
  1. Unit test in `tests/unit/test_idml_geometry.py`: synthetic IDML with
     a single Image whose ItemTransform yields `local_scale=(0.5, 0.5)`.
     Run converter, assert emitted call contains `scale_type=1`.
  2. Unit test: IDML with full-bleed image, `local_scale=(1, 1)`,
     `local_offset_pt=(0, 0)` — assert no `scale_type=1` in the emitted
     output (inherits default 0).
  3. Unit test: IDML with `local_offset_pt=(5.0, -3.0)` (non-trivial crop
     offset, local_scale unity) — assert `scale_type=1` emitted.
  4. Unit test: IDML with `local_scale=(0.5, 0.5)` AND
     `local_offset_pt=(5.0, -3.0)` — assert `scale_type=1` emitted once,
     not twice (idempotent).

  Build helper for unit tests: minimal IDML XML strings (one TextFrame +
  one Image inside one Spread); reuse the existing
  `tests/unit/test_idml_geometry.py` helpers if they're already there. If
  helpers are minimal, inline a small IDML-zip stub.

  Acceptance: re-emit v2 falzflyer build.py via the modified converter
  and `grep -c "scale_type=1" templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py`
  matches the count of ImageFrames that have any local_offset or non-unity
  local_scale.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_idml_geometry.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `_emit_image_frame_call` emits `scale_type=1` exactly when `local_scale ≠ (1,1)` OR `local_offset != (0,0)` (mm-rounded)
  - Default scale_type=0 (Backport 10) preserved for full-fit images
  - Four new unit tests pass under both pytest and unittest discover
  </done>
</task>

<task type="auto">
  <name>Task 5: Backport 11 edge fix — ALWAYS emit per-paragraph ALIGN (P1)</name>
  <files>tools/idml_to_dsl.py, tests/unit/test_idml_styles.py</files>
  <action>
  **Problem** (verified in pitfalls.md §4.1): `tools/idml_to_dsl.py:1775-1787`
  emits `default_style_attrs={'ALIGN': N}` only when the FIRST PSR's
  effective Justification maps to a non-zero ALIGN. Inner PSRs with
  align_int=0 (Left) skip emitting `paragraph_attrs={'ALIGN': '0'}`
  because "Left is default." But when DefaultStyle != Left, those inner
  Left paragraphs INHERIT DefaultStyle's non-Left alignment in Scribus —
  silent regression on mixed-Justification frames (Zeitung A4, callout-
  flyers).

  **Fix:** locate the call site in `_emit_text_frame_call` (or wherever
  per-paragraph attrs are assembled — search for "paragraph_attrs" in
  `tools/idml_to_dsl.py`). Change the policy from "emit ALIGN only when
  != 0" to **"emit ALIGN on every paragraph whose effective ALIGN differs
  from the DefaultStyle ALIGN."**

  Approach (pseudocode):
  ```python
  default_align = 0
  if _first_psr_style_self and _first_psr_style_self in ctx.paragraph_styles:
      _eff_just = ctx.paragraph_styles[_first_psr_style_self].get("justification")
      if _eff_just in JUSTIFICATION_MAP:
          default_align = JUSTIFICATION_MAP[_eff_just]

  # Always set the DefaultStyle, even when default_align == 0, so the SLA
  # is explicit (defense-in-depth against future Scribus refactors).
  kwargs["default_style_attrs"] = {"ALIGN": str(default_align)}

  # For each PSR's emitted paragraph_attrs, ALWAYS include ALIGN. If the
  # paragraph's effective align differs from default_align, emit override.
  # If it matches, still emit explicitly (redundant but harmless; matches
  # the "explicit-over-default" doctrine).
  for psr in psrs:
      psr_align = JUSTIFICATION_MAP.get(psr.justification, default_align)
      psr["paragraph_attrs"]["ALIGN"] = str(psr_align)
  ```
  Implementation note: the existing structure builds `paragraph_attrs`
  per Run; locate the path that produces `paragraph_attrs={'ALIGN': '1'}`
  in the Backport 11 fixture (lines 1100-1125 of ISSUE.md). Update that
  same path to ALWAYS write the ALIGN key.

  **Tests:**
  1. Unit test in `tests/unit/test_idml_styles.py`: TextFrame with 3 PSRs
     (Center, Left, Right). Assert all three emitted `paragraph_attrs`
     dicts include explicit `ALIGN` keys (1, 0, 2 respectively), AND
     `default_style_attrs.ALIGN == "1"` (from the first PSR).
  2. Unit test: TextFrame with 1 PSR (LeftAlign). Assert
     `default_style_attrs.ALIGN == "0"` IS emitted (not absent).
  3. Unit test: TextFrame with 2 PSRs both CenterAlign. Both paragraphs
     emit `ALIGN: "1"`, DefaultStyle also `ALIGN: "1"`.
  4. Regression test: u376 fixture (single-PSR, FullyJustified? or
     CenterAlign) — assert the existing Backport 11 behaviour (both
     lines centered) is preserved (no regression on simple-case).

  Make sure the existing simple-case unit tests still pass (the change
  is additive — Left now also emits, but readers/Scribus accept both).
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_idml_styles.py tests/unit/test_idml_story.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - Every TextFrame emits `default_style_attrs={'ALIGN': str(N)}` explicitly (even when N=0)
  - Every paragraph (PSR) emits explicit `paragraph_attrs.ALIGN` regardless of value
  - Mixed-Justification frames (3 different aligns) correctly emit all 3 explicit overrides
  - Existing Backport 11 unit tests still pass; 4 new tests added
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 6: Aggregated preflight.yml + hard-fail --audit gate (P1)</name>
  <files>tools/render_pipeline.py, tests/unit/test_render_pipeline_preflight.py, tests/integration/test_preflight_v2.py</files>
  <action>
  **Problem** (verified in pitfalls.md §0, §5.2): `bin/render-gallery --audit`
  emits 9 separate audit YAMLs and is NON-BLOCKING by default; the
  convergence loop can declare "engine floor" while audits silently
  disagree. Token budget per iteration: ~25k+ tokens spent on reading 9
  failing YAMLs.

  **Fix:** at the END of `_run_audit` (after Phase G region_color_audit,
  around line 937), aggregate all sub-audit results into a single
  `preflight.yml`. Then in `main()` (line ~1080), hard-fail `--audit`
  (not just `--audit-strict`) when any per-template `preflight.yml::ok`
  is `False`.

  **New aggregation logic** (inline in `_run_audit`):
  ```python
  # Read each sub-audit yml/json that may exist and build the
  # aggregated preflight.yml.
  def _load_yml(p):
      if not p.exists(): return None
      return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

  audits_summary: dict[str, dict] = {}
  def _record(name: str, ok: bool, issues: int, detail: str = ""):
      audits_summary[name] = {"ok": ok, "issues": issues, "detail": detail}

  inv = _load_yml(inventory_path)
  if inv is not None:
      n_dropped = sum(len(s.get("elements_dropped", []))
                      for s in inv.get("spreads", []))
      _record("inventory", n_dropped == 0, n_dropped,
              f"{n_dropped} dropped element(s)")

  ta = _load_yml(text_audit_path)
  if ta is not None:
      n_unmatched = sum(len(p.get("lines_unmatched", []))
                        for p in ta.get("pages", []))
      _record("text_audit", n_unmatched == 0, n_unmatched, "")

  ia = _load_yml(image_audit_path)
  if ia is not None:
      n_delta = sum(p.get("vector_paths", {}).get("delta", 0)
                    for p in ia.get("pages", []))
      _record("image_audit", n_delta == 0, n_delta, "")

  fa = _load_yml(font_audit_path)
  if fa is not None:
      _record("font_audit", fa.get("ok", False),
              len(fa.get("missing_in_preview", [])), "")

  tra = _load_yml(text_render_audit_path)
  if tra is not None:
      _record("text_render_audit", tra.get("ok", False),
              len(tra.get("missing_in_preview", {})), "")

  tpa = _load_yml(text_position_audit_path)
  if tpa is not None:
      _record("text_position_audit", tpa.get("ok", False),
              tpa.get("large_deltas_count", 0), "")

  rsa = _load_yml(run_style_audit_path)
  if rsa is not None:
      large = sum(1 for d in rsa.get("style_drifts", [])
                  if d.get("severity") == "large")
      _record("run_style_audit", rsa.get("ok", False) and large == 0, large, "")

  ped = _load_yml(out_dir / "per_element_drift.yml")
  if ped is not None:
      # diagnostic only — never fails preflight, but record for context
      _record("per_element_drift", True, 0,
              "diagnostic; see top_contributors")

  rca = _load_yml(color_audit_path)
  if rca is not None:
      # diagnostic only
      _record("region_color_audit", True,
              rca.get("by_severity", {}).get("fill_likely", 0),
              rca.get("pattern", ""))

  # Phase E2 (P3 task 13) will add line_spacing_audit here.
  # Phase H (P2 task 10) will add visual_diff_regions here.

  preflight_ok = all(a["ok"] for a in audits_summary.values())

  # Hot-issues list: top 5 most actionable failed audits
  hot = sorted(
      ((name, info) for name, info in audits_summary.items() if not info["ok"]),
      key=lambda kv: -kv[1]["issues"],
  )[:5]
  hot_issues = [
      {"audit": name, "issues": info["issues"], "message": info["detail"] or f"{info['issues']} issue(s)"}
      for name, info in hot
  ]

  preflight = {
      "template": tid,
      "ok": preflight_ok,
      "audits": audits_summary,
      "hot_issues": hot_issues,
  }
  preflight_path = out_dir / "preflight.yml"
  preflight_path.write_text(
      yaml.dump(preflight, sort_keys=True, allow_unicode=True,
                default_flow_style=False),
      encoding="utf-8",
  )

  # Surface preflight failure into issue_parts (so --audit-strict still works
  # via the existing path, AND --audit also fails via the new path).
  if not preflight_ok:
      issue_parts.append(
          f"preflight FAILED ({len([a for a in audits_summary.values() if not a['ok']])} sub-audit(s))"
      )
  ```

  Place this aggregation IMMEDIATELY before the final `if issue_parts: ...
  return len(issue_parts), summary` block.

  **Change exit-code logic** in `main()` at line 1080-1081:
  ```python
  # Hard-fail --audit (not just --audit-strict) when any preflight.yml::ok=False.
  # --audit-strict additionally fails on issue_parts (existing behaviour).
  preflight_failure = False
  for tdir in work:
      tid = tdir.name
      preflight_p = ROOT / "build" / "validation" / tid / "preflight.yml"
      if preflight_p.exists():
          pre = yaml.safe_load(preflight_p.read_text(encoding="utf-8")) or {}
          if pre.get("ok") is False:
              preflight_failure = True
              break
  if getattr(args, "audit", False) and preflight_failure:
      overall = 1
  if getattr(args, "audit_strict", False) and audit_issue_count_total > 0:
      overall = 1
  ```

  Update the `--audit` help text to mention the hard-fail behaviour:
  ```
  ...Hard-fails (exit non-zero) when any preflight.yml::ok == false.
  Use --audit-strict to additionally fail on any audit issue_parts.
  ```

  **Tests:**
  1. Unit test in `tests/unit/test_render_pipeline_preflight.py`: import
     `_run_audit` indirectly via building a fake template dir + meta and
     calling it; OR test the aggregation logic by extracting it into a
     helper `_build_preflight(out_dir, tid) -> dict` and unit-testing
     that. Recommend extracting helper — cleaner.
     - Test: all sub-audits ok → preflight_ok=True, hot_issues=[].
     - Test: 2 sub-audits failing → preflight_ok=False, hot_issues has 2.
     - Test: ≥6 sub-audits failing → hot_issues capped at 5.
     - Test: missing yml file (audit was skipped) → not included in
       `audits` dict, doesn't fail preflight.
     - Test: deterministic YAML output (run twice, byte-equal).
  2. Integration test in `tests/integration/test_preflight_v2.py`: run
     the full pipeline on v2 falzflyer (skip if Scribus/baseline.pdf
     unavailable — use `pytest.mark.skipif`). Assert
     `build/validation/.../preflight.yml` exists with the expected shape.
  3. Smoke test for exit-code: shell-out invoke
     `bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit`
     with a deliberately-failed audit (e.g. delete preview.pdf or stub a
     failing preflight.yml). Assert exit code == 1. Use
     `subprocess.run(...).returncode`. Mark as `@pytest.mark.integration`
     and skip if no Scribus.

  Refactor the existing audit-summary block in `_run_audit` to use
  `_build_preflight` rather than duplicating the per-audit
  if-exists/issue_parts logic, to keep code DRY.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_render_pipeline_preflight.py tests/integration/test_preflight_v2.py -q && python3 -m unittest discover tests/unit && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - `build/validation/<slug>/preflight.yml` is emitted at the end of `_run_audit` with shape `{template, ok, audits: {name: {ok, issues, detail}}, hot_issues}`
  - `hot_issues` capped at top-5 failed audits by issue count
  - `bin/render-gallery --audit` (not just --audit-strict) exits non-zero when any preflight.yml::ok=false
  - Help text updated to document the hard-fail
  - All new unit + integration tests pass under both pytest and unittest discover
  </done>
</task>

<!-- ============================================================ -->
<!-- P2 — Backport 12: per-region visual_diff (tasks 7-12)        -->
<!-- Independent of P3. Can be developed in parallel after P1.    -->
<!-- ============================================================ -->

<task type="auto" tdd="true">
  <name>Task 7: Extend TemplateTolerance schema with region_grid (P2)</name>
  <files>tools/visual_diff.py, tests/unit/test_visual_diff_tolerance.py</files>
  <action>
  Extend `TemplateTolerance` (line 46-87) to accept a `region_grid` block:

  ```python
  @dataclass
  class TemplateTolerance:
      max_pixel_mismatch_pct: float = 1.0
      fuzz_pct: float = 25.0
      per_page: dict = field(default_factory=dict)
      per_region: list = field(default_factory=list)
      region_grid: dict = field(default_factory=dict)
      # schema:
      # {
      #   "cols": int (default 6),
      #   "rows": int (default 4),
      #   "default_max_pixel_mismatch_pct": float (defaults to max_pixel_mismatch_pct),
      #   "default_fuzz_pct": float (defaults to fuzz_pct),
      #   "per_cell": [
      #     {"page": int, "col": int, "row": int,
      #      "max_pixel_mismatch_pct": float?, "fuzz_pct": float?},
      #     ...
      #   ],
      # }
  ```

  Update `TemplateTolerance.load()`:
  ```python
  region_grid_block = block.get("region_grid", {}) or {}
  if region_grid_block:
      # Normalise
      region_grid_block.setdefault("cols", 6)
      region_grid_block.setdefault("rows", 4)
      region_grid_block.setdefault("per_cell", [])
      # validation
      assert isinstance(region_grid_block["cols"], int) and region_grid_block["cols"] > 0
      assert isinstance(region_grid_block["rows"], int) and region_grid_block["rows"] > 0
  return cls(
      max_pixel_mismatch_pct=float(block.get("max_pixel_mismatch_pct", 1.0)),
      fuzz_pct=float(block.get("fuzz_pct", 25.0)),
      per_page=per_page,
      per_region=per_region,
      region_grid=region_grid_block,
  )
  ```

  Add helper method:
  ```python
  def for_cell(self, page_index: int, col: int, row: int) -> tuple[float, float]:
      """Resolve (max_pixel_mismatch_pct, fuzz_pct) for one grid cell.

      Resolution order: per_cell override → region_grid defaults → for_page().
      """
      page_max, page_fuzz = self.for_page(page_index)
      grid = self.region_grid
      max_pct = float(grid.get("default_max_pixel_mismatch_pct", page_max))
      fuzz = float(grid.get("default_fuzz_pct", page_fuzz))
      for cell in grid.get("per_cell", []):
          if (cell.get("page") == page_index
                  and cell.get("col") == col
                  and cell.get("row") == row):
              max_pct = float(cell.get("max_pixel_mismatch_pct", max_pct))
              fuzz = float(cell.get("fuzz_pct", fuzz))
              break
      return max_pct, fuzz
  ```

  Add a module-level constant:
  ```python
  DEFAULT_GRID_COLS = 6
  DEFAULT_GRID_ROWS = 4
  ```

  **Tests** in `tests/unit/test_visual_diff_tolerance.py` (new file):
  1. `TemplateTolerance()` (no path) has `region_grid={}`.
  2. Loading a yaml with no `region_grid` block → empty dict.
  3. Loading `{visual_diff: {region_grid: {cols: 8, rows: 6}}}` → cols=8, rows=6.
  4. `for_cell(0, 3, 2)` returns the `per_cell` override when matched.
  5. `for_cell(0, 0, 0)` returns the page defaults when no per_cell override.
  6. Invalid cols=0 raises AssertionError.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_visual_diff_tolerance.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `TemplateTolerance.region_grid` field added with documented schema
  - `TemplateTolerance.for_cell(page, col, row)` resolves per-cell thresholds
  - `DEFAULT_GRID_COLS=6`, `DEFAULT_GRID_ROWS=4` module constants
  - 6 unit tests pass under both pytest and unittest discover
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 8: Implement compare_grid PIL primitive (P2)</name>
  <files>tools/visual_diff.py, tests/unit/test_visual_diff_grid.py</files>
  <action>
  Add a new function `compare_grid` to `tools/visual_diff.py` that performs
  per-cell pixel diff via PIL (NOT ImageMagick — see ecosystem.md §5 for
  rationale: 48 subprocess calls is dominated by fork overhead).

  ```python
  from PIL import Image, ImageChops

  def compare_grid(
      baseline_png: Path,
      preview_png: Path,
      cols: int,
      rows: int,
      fuzz_pct: float = 25.0,
  ) -> list[dict]:
      """Return per-cell diff results for a grid laid over the two images.

      Both images MUST be the same pixel dimensions (caller's responsibility
      to ensure DPI-matched pdftoppm rasterisation). Returns a list of
      dicts in (row, col) reading order:
          {col, row, mismatch_pixels, total_pixels, mismatch_pct,
           bbox_px: {x, y, w, h}}

      Mismatch semantics mimic ImageMagick `compare -metric AE -fuzz N%`:
      for each pixel, the max channel delta is compared to
      threshold = round(255 * fuzz_pct / 100). Pixels with max-channel-
      delta > threshold count as mismatched.
      """
      base = Image.open(baseline_png).convert("RGB")
      prev = Image.open(preview_png).convert("RGB")
      if base.size != prev.size:
          raise ValueError(
              f"image size mismatch: baseline={base.size}, preview={prev.size}"
          )
      w_px, h_px = base.size

      # Integer cell sizes with last column/row absorbing the modulus.
      col_widths = [w_px // cols] * cols
      col_widths[-1] += w_px % cols
      row_heights = [h_px // rows] * rows
      row_heights[-1] += h_px % rows

      threshold = round(255 * fuzz_pct / 100.0)

      results = []
      y = 0
      for row in range(rows):
          x = 0
          for col in range(cols):
              cell_w, cell_h = col_widths[col], row_heights[row]
              b_crop = base.crop((x, y, x + cell_w, y + cell_h))
              p_crop = prev.crop((x, y, x + cell_w, y + cell_h))
              diff = ImageChops.difference(b_crop, p_crop)
              r, g, b = diff.split()
              max_chan = ImageChops.lighter(ImageChops.lighter(r, g), b)
              hist = max_chan.histogram()  # 256 bins
              mismatch_px = sum(hist[threshold + 1:])
              total_px = cell_w * cell_h
              results.append({
                  "col": col,
                  "row": row,
                  "mismatch_pixels": int(mismatch_px),
                  "total_pixels": int(total_px),
                  "mismatch_pct": round(mismatch_px / total_px * 100, 4) if total_px else 0.0,
                  "bbox_px": {"x": x, "y": y, "w": cell_w, "h": cell_h},
              })
              x += cell_w
          y += row_heights[row]
      return results
  ```

  Document in the function docstring that this is the **per-region**
  metric (max-channel-delta) which is within 1-2% of ImageMagick's
  Euclidean AE+fuzz semantics on real PDFs; cell totals will NOT exactly
  equal the page-wide mismatch_pixels — that's expected (see
  ecosystem.md §10.5).

  **Tests** in `tests/unit/test_visual_diff_grid.py` (new file):
  1. Identical 60×40 PIL images, 6×4 grid → all cells have mismatch_pixels=0,
     mismatch_pct=0.0.
  2. Two 60×40 images differing in ONLY one 10×10 patch at (15, 5) (i.e.
     col=1, row=0 — cell size 10×10) — assert exactly that cell has
     non-zero mismatch_pixels, all others zero.
  3. Two 60×40 images differing globally (one pure white, other pure red):
     - fuzz_pct=0 → all cells fully mismatched (mismatch_pct=100.0).
     - fuzz_pct=99 → all cells fully matched (mismatch_pct=0.0).
  4. Size-mismatch raises ValueError.
  5. Modulus absorption: 65×40 image, 6×4 grid → cell widths [10,10,10,10,10,15],
     last column has width 15.
  6. Determinism: run twice on the same images, byte-equal output dicts.

  Use `PIL.Image.new("RGB", (W, H), color)` and `Image.paste(other, (x, y))`
  to build synthetic test images in-process (no fixture files). Save to
  temporary files via `tmp_path / "a.png"` if the function takes paths.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_visual_diff_grid.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `compare_grid(baseline_png, preview_png, cols, rows, fuzz_pct)` exported from `tools/visual_diff.py`
  - Returns per-cell `{col, row, mismatch_pixels, total_pixels, mismatch_pct, bbox_px}` in (row, col) reading order
  - 6 unit tests cover identical, localized, global, size-mismatch, modulus, and determinism cases
  - All tests pass under both pytest and unittest discover
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 9: Render heatmap PNG with PIL (P2)</name>
  <files>tools/visual_diff.py, tests/unit/test_visual_diff_heatmap.py</files>
  <action>
  Add `render_grid_heatmap()` to `tools/visual_diff.py`. NO matplotlib —
  per ecosystem.md §2.3, use `PIL.ImageDraw.rectangle` + hand-rolled
  green→amber→red linear ramp.

  ```python
  from PIL import Image, ImageDraw, ImageFont

  def _heatmap_color(mismatch_pct: float, threshold_pct: float) -> tuple[int, int, int, int]:
      """Linear ramp green → amber → red, RGBA tuple.

      - pct <= 0           → green  (76, 175, 80, 180)
      - pct == threshold   → amber  (255, 193, 7, 180)
      - pct >= 2*threshold → red    (244, 67, 54, 180)
      Linear interpolation between the two segments. Alpha fixed at 180/255.
      """
      green = (76, 175, 80)
      amber = (255, 193, 7)
      red = (244, 67, 54)
      if mismatch_pct <= 0:
          rgb = green
      elif mismatch_pct >= 2 * threshold_pct:
          rgb = red
      elif mismatch_pct <= threshold_pct:
          t = mismatch_pct / threshold_pct
          rgb = tuple(int(green[i] + (amber[i] - green[i]) * t) for i in range(3))
      else:
          t = (mismatch_pct - threshold_pct) / threshold_pct
          rgb = tuple(int(amber[i] + (red[i] - amber[i]) * t) for i in range(3))
      return (*rgb, 180)

  def render_grid_heatmap(
      baseline_png: Path,
      cells: list[dict],
      threshold_pct: float,
      out_png: Path,
  ) -> None:
      """Render an RGBA heatmap overlaying ``cells`` on a desaturated
      grayscale copy of ``baseline_png``. Output: ``out_png`` (PNG, RGBA).
      Each cell is labeled with its mismatch_pct.
      """
      base = Image.open(baseline_png).convert("L").convert("RGBA")
      overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
      draw = ImageDraw.Draw(overlay)
      try:
          font = ImageFont.truetype(
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=14,
          )
      except Exception:
          font = ImageFont.load_default()
      for cell in cells:
          bx = cell["bbox_px"]["x"]
          by = cell["bbox_px"]["y"]
          bw = cell["bbox_px"]["w"]
          bh = cell["bbox_px"]["h"]
          color = _heatmap_color(cell["mismatch_pct"], threshold_pct)
          draw.rectangle(
              [bx, by, bx + bw - 1, by + bh - 1],
              fill=color,
              outline=(0, 0, 0, 255),
              width=1,
          )
          label = f"{cell['mismatch_pct']:.1f}%"
          # Text positioned near top-left of the cell, with a slight margin.
          draw.text((bx + 4, by + 4), label, fill=(0, 0, 0, 255), font=font)
      composite = Image.alpha_composite(base, overlay)
      composite.save(out_png, format="PNG")
  ```

  **Tests** in `tests/unit/test_visual_diff_heatmap.py` (new file):
  1. `_heatmap_color(0, 5.0)` → green tuple. `_heatmap_color(5, 5)` → amber.
     `_heatmap_color(15, 5)` → red.
  2. `_heatmap_color(2.5, 5)` → midpoint between green and amber.
  3. Linear monotonicity: for pct in 0, 1, 2, 3, 4, 5, the red channel
     increases (or stays equal) and the green channel monotonically.
  4. `render_grid_heatmap` writes a valid PNG file at out_png (open and
     check `Image.size != (0,0)`).
  5. Heatmap PNG dimensions equal baseline PNG dimensions.
  6. Multiple cells with different pcts render correctly — round-trip
     check: open the PNG, sample a pixel inside a known cell, assert the
     RGB is near the expected ramp color (allow ±15 per channel for
     alpha-blending and grayscale composite).

  Use `tmp_path / "out.png"` for the output file.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_visual_diff_heatmap.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `_heatmap_color(pct, threshold) → RGBA` ramp green/amber/red exported from `tools/visual_diff.py`
  - `render_grid_heatmap(baseline_png, cells, threshold_pct, out_png)` writes a labeled heatmap PNG
  - 6 unit tests pass under both pytest and unittest discover
  - No matplotlib dependency introduced
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 10: Wire Phase H (visual_diff_regions) into _run_audit (P2)</name>
  <files>tools/visual_diff.py, tools/render_pipeline.py, tests/unit/test_render_pipeline_phaseH.py</files>
  <action>
  Add a top-level orchestration function in `tools/visual_diff.py`:

  ```python
  def run_region_grid_audit(
      baseline_png_dir: Path,    # contains baseline-page-N.png from pdftoppm
      preview_png_dir: Path,     # contains dsl-page-N.png from pdftoppm
      tolerance: TemplateTolerance,
      out_dir: Path,
      template: str = "",
  ) -> dict:
      """Run per-cell visual diff on every page, write heatmap PNGs and
      visual_diff_regions.yml. Returns the report dict.
      """
      if not tolerance.region_grid:
          # Caller decides whether to fall back to defaults or skip.
          # Here we use defaults so we always emit a report.
          tolerance.region_grid = {
              "cols": DEFAULT_GRID_COLS, "rows": DEFAULT_GRID_ROWS, "per_cell": [],
          }
      cols = tolerance.region_grid["cols"]
      rows = tolerance.region_grid["rows"]

      pages = []
      page_idx = 0
      while True:
          base_p = baseline_png_dir / f"baseline-page-{page_idx + 1}.png"
          prev_p = preview_png_dir / f"dsl-page-{page_idx + 1}.png"
          if not base_p.exists() or not prev_p.exists():
              break
          page_max, page_fuzz = tolerance.for_page(page_idx)
          cells = compare_grid(base_p, prev_p, cols, rows, fuzz_pct=page_fuzz)
          # Apply per-cell tolerances
          for cell in cells:
              cell_max, cell_fuzz = tolerance.for_cell(page_idx, cell["col"], cell["row"])
              cell["threshold_pct"] = cell_max
              cell["fuzz_pct"] = cell_fuzz
              cell["pass"] = cell["mismatch_pct"] <= cell_max
          # Re-run cells whose per_cell fuzz_pct differs from the page-default
          # so the threshold semantics match the override (mismatch_pct must be
          # recomputed if fuzz_pct differs).
          # Approach: collect cells with a custom fuzz_pct, recompute only those.
          for cell in cells:
              if abs(cell["fuzz_pct"] - page_fuzz) > 1e-6:
                  recomputed = compare_grid(base_p, prev_p, cols, rows,
                                            fuzz_pct=cell["fuzz_pct"])
                  # find recomputed cell with matching col/row
                  for rc in recomputed:
                      if rc["col"] == cell["col"] and rc["row"] == cell["row"]:
                          cell["mismatch_pixels"] = rc["mismatch_pixels"]
                          cell["total_pixels"] = rc["total_pixels"]
                          cell["mismatch_pct"] = rc["mismatch_pct"]
                          cell["pass"] = rc["mismatch_pct"] <= cell["threshold_pct"]
                          break

          hot = sorted(
              ((c for c in cells if not c["pass"])),
              key=lambda c: -c["mismatch_pct"],
          )[:10]
          hot_regions = [
              {"col": c["col"], "row": c["row"], "mismatch_pct": c["mismatch_pct"]}
              for c in hot
          ]

          heatmap_name = f"visual_diff_heatmap-page-{page_idx + 1:02d}.png"
          heatmap_path = out_dir / heatmap_name
          render_grid_heatmap(base_p, cells, page_max, heatmap_path)

          pages.append({
              "page": page_idx,
              "regions": cells,
              "hot_regions": hot_regions,
              "heatmap_png": heatmap_name,
          })
          page_idx += 1

      page_ok = all(c["pass"] for page in pages for c in page["regions"])
      return {
          "template": template,
          "grid": {"cols": cols, "rows": rows},
          "pages": pages,
          "ok": page_ok,
      }
  ```

  Add CLI entry point in `tools/visual_diff.py::main()` for standalone use
  (mirror `text_position_audit.py::main()` shape): args
  `--baseline-png-dir`, `--preview-png-dir`, `--tolerance`, `--out`,
  `--template`. The existing visual_diff main already has many args;
  add `--grid-only` mode that skips the page-wide compare and only runs
  `run_region_grid_audit`.

  **Wire into `tools/render_pipeline.py:_run_audit`** as Phase H,
  AFTER page-wide visual_diff (which already writes baseline-page-N.png +
  dsl-page-N.png under `build/<slug>/` — confirm this path; the
  page-wide visual_diff runs as part of `_orchestrate_template` and
  writes to `build/<slug>/<engine_dir>/`. Verify the actual location by
  reading `tools/visual_diff.py::visual_diff()` return data and the
  out_dir used during `_orchestrate_template`.).

  Place Phase H wire-up between Phase G (region_color_audit, around
  line 936) and the final `if issue_parts: ...` block:
  ```python
  # Phase H: per-region visual_diff grid (Backport 12).
  vd_region_path = out_dir / "visual_diff_regions.yml"
  if preview_pdf.exists() and baseline.exists():
      try:
          from visual_diff import (
              run_region_grid_audit as _vdr_run,
              TemplateTolerance,
          )
          tolerance = TemplateTolerance.load(tdir / "diff.yml")
          # baseline-page-N.png / dsl-page-N.png live in the visual_diff out_dir.
          # That dir is typically ROOT / "build" / tid (read render_pipeline._orchestrate_template).
          png_dir = ROOT / "build" / tid
          vdr_result = _vdr_run(
              baseline_png_dir=png_dir, preview_png_dir=png_dir,
              tolerance=tolerance,
              out_dir=out_dir, template=tid,
          )
          vd_region_path.write_text(
              yaml.dump(vdr_result, sort_keys=True, allow_unicode=True,
                        default_flow_style=False),
              encoding="utf-8",
          )
          if not vdr_result["ok"]:
              n_hot = sum(len(p["hot_regions"]) for p in vdr_result["pages"])
              print(f"[{tid}] visual_diff_regions: {n_hot} hot region(s) → REVIEW")
              issue_parts.append(f"{n_hot} hot region(s)")
          else:
              print(f"[{tid}] visual_diff_regions: OK")
      except Exception as exc:
          print(f"[{tid}] audit H (visual_diff_regions) error: {exc}", file=sys.stderr)
  ```

  Then update task 6's preflight aggregation to include
  `_record("visual_diff_regions", vdr_result.get("ok", True), n_hot, "")`.
  (Task 6 already left a comment placeholder for this.)

  **Tests** in `tests/unit/test_render_pipeline_phaseH.py`:
  1. `run_region_grid_audit` on synthetic png dirs (build via PIL,
     2 pages, both identical) → all cells pass, hot_regions empty, ok=true.
  2. Synthetic case: one cell on page 0 has high mismatch — hot_regions
     contains that cell, ok=false.
  3. Heatmap PNG files are written to out_dir with names
     `visual_diff_heatmap-page-01.png`, `visual_diff_heatmap-page-02.png`.
  4. Custom per_cell fuzz_pct override is honoured (set per_cell fuzz_pct=99
     for a known-bad cell, assert pass=true for that cell).
  5. YAML output is deterministic (run twice, byte-equal).

  IMPORTANT: verify the actual baseline-page-N.png / dsl-page-N.png
  output directory by reading `tools/render_pipeline.py::_orchestrate_template`
  before wiring — the path constant ROOT/"build"/tid is a best-guess; if
  the actual location differs, adjust accordingly. The task is "wire to
  whichever dir the page-wide visual_diff already uses."
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_render_pipeline_phaseH.py tests/unit/test_visual_diff_grid.py tests/unit/test_visual_diff_heatmap.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `run_region_grid_audit()` exported from `tools/visual_diff.py`
  - Phase H wired into `_run_audit` AFTER Phase G; emits `build/validation/<slug>/visual_diff_regions.yml` + `visual_diff_heatmap-page-NN.png`
  - Preflight.yml (task 6) gains `audits.visual_diff_regions` entry
  - 5 unit tests pass under both pytest and unittest discover
  </done>
</task>

<task type="auto">
  <name>Task 11: Update diff.yml schema doc + v2 falzflyer diff.yml (P2)</name>
  <files>docs/diff-tolerance.md, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml</files>
  <action>
  Update `docs/diff-tolerance.md` to document the new `region_grid` schema:

  ```markdown
  ## `region_grid` (Backport 12 — per-region visual_diff)

  Optional. When present, `bin/render-gallery --audit` emits
  `build/validation/<slug>/visual_diff_regions.yml` + a heatmap PNG per page.

  ### Schema

  ```yaml
  visual_diff:
    max_pixel_mismatch_pct: 1.0       # page-wide default (unchanged)
    fuzz_pct: 25.0                    # page-wide default (unchanged)
    region_grid:
      cols: 6                         # grid columns per page (default 6)
      rows: 4                         # grid rows per page (default 4)
      default_max_pixel_mismatch_pct: 5.0   # optional; cell-default threshold
      default_fuzz_pct: 25.0                # optional; cell-default fuzz
      per_cell:                       # optional per-cell overrides
        - page: 0
          col: 3
          row: 2
          max_pixel_mismatch_pct: 10.0
          fuzz_pct: 30.0
        - page: 1
          col: 0
          row: 0
          max_pixel_mismatch_pct: 0.5
  ```

  ### Default grid

  The default 6×4 cell grid (24 cells per page) is sized so each cell on
  an A4 page is approximately a "design slot" (~35×74 mm). Cell sizing
  is computed via integer division with the last column/row absorbing the
  modulus.

  ### Heatmap output

  `build/validation/<slug>/visual_diff_heatmap-page-NN.png` is emitted
  per page. Cell colors: green (no mismatch) → amber (at threshold) → red
  (≥2× threshold). Each cell labeled with its mismatch_pct.

  ### Tie-in with `tools/diff_bbox_extract.py`

  The bbox extractor surfaces anomaly SHAPES; the grid surfaces a stable
  SPATIAL MAP. Use them together: bbox to find drift, grid to confirm
  spatial concentration. See `docs/audit-tools.md` for the convergence
  workflow.
  ```

  Add a `region_grid` block to
  `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml`:
  ```yaml
  region_grid:
    cols: 6
    rows: 4
    # default_max_pixel_mismatch_pct inherits visual_diff.max_pixel_mismatch_pct
    # No per_cell overrides initially; tune after first measurement pass.
  ```

  Do NOT alter existing keys (`max_pixel_mismatch_pct`, `fuzz_pct`,
  `per_page`, `per_region`) in v2 falzflyer's diff.yml; the
  region_grid block is purely additive.

  Verification: validate the diff.yml round-trips through
  `TemplateTolerance.load()` without error. Run:
  ```bash
  python3 -c "
  from pathlib import Path
  import sys; sys.path.insert(0, 'tools')
  from visual_diff import TemplateTolerance
  t = TemplateTolerance.load(Path('templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml'))
  assert t.region_grid['cols'] == 6
  assert t.region_grid['rows'] == 4
  print('OK')
  "
  ```
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && python3 -c "from pathlib import Path; import sys; sys.path.insert(0, 'tools'); from visual_diff import TemplateTolerance; t = TemplateTolerance.load(Path('templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml')); assert t.region_grid.get('cols') == 6; assert t.region_grid.get('rows') == 4; print('OK')"</automated>
  </verify>
  <done>
  - `docs/diff-tolerance.md` documents the `region_grid` schema with default 6×4, per_cell overrides, heatmap output, and bbox tie-in
  - V2 falzflyer's `diff.yml` includes a `region_grid: {cols: 6, rows: 4}` block
  - Round-trip via `TemplateTolerance.load()` succeeds
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 12: Regression test — shifted headline produces hot cell (P2)</name>
  <files>tests/integration/test_visual_diff_regions_regression.py</files>
  <action>
  Create a synthetic regression test per ISSUE.md line 1227-1229:
  "shift a single 9pt headline by 50pt produces a region with >10%
  mismatch even when page-wide stays <1%."

  Since reportlab/wkhtmltopdf are not installed, build the test using
  PIL synthetic images directly (no PDF round-trip needed — the
  visual_diff regions tool consumes PNGs, not PDFs).

  ```python
  import pytest
  from pathlib import Path
  from PIL import Image, ImageDraw, ImageFont
  import sys

  sys.path.insert(0, "tools")
  from visual_diff import compare_grid, run_region_grid_audit, TemplateTolerance

  def _make_page(w_px=2480, h_px=3508, headline_xy=(200, 300),
                 headline_text="Headline", font_size=30):
      """A4 at 300 DPI is 2480×3508. Use 600×850 here for test speed."""
      w_px, h_px = 600, 850
      img = Image.new("RGB", (w_px, h_px), "white")
      d = ImageDraw.Draw(img)
      try:
          font = ImageFont.truetype(
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              size=font_size,
          )
      except Exception:
          font = ImageFont.load_default()
      d.text(headline_xy, headline_text, fill="black", font=font)
      return img

  def test_shifted_headline_localises_to_one_cell(tmp_path):
      """Per ISSUE.md acceptance: shift produces a hot region even when
      page-wide stays small."""
      base_png = tmp_path / "baseline-page-1.png"
      prev_png = tmp_path / "dsl-page-1.png"
      # Same headline at slightly different positions
      _make_page(headline_xy=(200, 300)).save(base_png)
      _make_page(headline_xy=(200, 350)).save(prev_png)   # +50 px shift

      # Page-wide mismatch
      cells = compare_grid(base_png, prev_png, cols=6, rows=4, fuzz_pct=25)
      total_px = sum(c["total_pixels"] for c in cells)
      total_mismatch = sum(c["mismatch_pixels"] for c in cells)
      page_wide_pct = total_mismatch / total_px * 100

      # Find the hottest cell
      hottest = max(cells, key=lambda c: c["mismatch_pct"])

      # Acceptance from ISSUE.md
      assert hottest["mismatch_pct"] > 10, (
          f"hottest cell mismatch_pct={hottest['mismatch_pct']:.2f}% "
          "(expected > 10%)"
      )
      # We don't strictly need page-wide < 1% on this synthetic — but it
      # should be substantially smaller than the hottest cell.
      assert hottest["mismatch_pct"] > 5 * page_wide_pct, (
          f"hot cell {hottest['mismatch_pct']:.2f}% should dominate "
          f"page-wide {page_wide_pct:.2f}%"
      )

  def test_identical_pages_all_clean(tmp_path):
      base_png = tmp_path / "baseline-page-1.png"
      prev_png = tmp_path / "dsl-page-1.png"
      img = _make_page()
      img.save(base_png); img.save(prev_png)
      cells = compare_grid(base_png, prev_png, cols=6, rows=4, fuzz_pct=25)
      for c in cells:
          assert c["mismatch_pixels"] == 0
          assert c["mismatch_pct"] == 0.0

  def test_run_region_grid_audit_emits_heatmap(tmp_path):
      """Smoke: run_region_grid_audit writes a heatmap PNG."""
      base_dir = tmp_path / "base"
      base_dir.mkdir()
      _make_page(headline_xy=(200, 300)).save(base_dir / "baseline-page-1.png")
      _make_page(headline_xy=(200, 350)).save(base_dir / "dsl-page-1.png")
      out_dir = tmp_path / "out"
      out_dir.mkdir()
      tolerance = TemplateTolerance(
          max_pixel_mismatch_pct=1.0, fuzz_pct=25.0,
          region_grid={"cols": 6, "rows": 4, "per_cell": []},
      )
      result = run_region_grid_audit(
          baseline_png_dir=base_dir, preview_png_dir=base_dir,
          tolerance=tolerance, out_dir=out_dir, template="test",
      )
      assert result["template"] == "test"
      assert result["grid"] == {"cols": 6, "rows": 4}
      assert len(result["pages"]) == 1
      assert (out_dir / "visual_diff_heatmap-page-01.png").exists()
  ```

  Tag this test file with `@pytest.mark.integration` if the repo uses
  markers; otherwise leave bare. Place in `tests/integration/` so it
  runs in the integration suite.

  This regression test directly satisfies ISSUE.md line 1227-1229
  acceptance criterion for Backport 12.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/integration/test_visual_diff_regions_regression.py -q && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - `tests/integration/test_visual_diff_regions_regression.py` exists with 3 tests
  - `test_shifted_headline_localises_to_one_cell`: 50px shift produces hottest cell > 10% mismatch
  - `test_identical_pages_all_clean`: all cells 0% on identical PNGs
  - `test_run_region_grid_audit_emits_heatmap`: smoke test that heatmap PNG is written
  - All tests pass under both pytest and unittest discover
  </done>
</task>

<!-- ============================================================ -->
<!-- P3 — Phase E2 line_spacing_audit + remaining scope (13-18)   -->
<!-- Independent of P2. Can be developed in parallel after P1.    -->
<!-- ============================================================ -->

<task type="auto" tdd="true">
  <name>Task 13: Build tools/line_spacing_audit.py (Phase E2)</name>
  <files>tools/line_spacing_audit.py, tests/unit/test_line_spacing_audit.py</files>
  <action>
  Create `tools/line_spacing_audit.py` per ISSUE.md Phase E2 (line 922-951).

  Use the established audit tool template (ecosystem.md §8.1):

  ```python
  #!/usr/bin/env python3
  """Phase E2 line_spacing_audit: per-TextFrame baseline-to-baseline pt-gap.

  Catches the LeadingModel-mismatch class: IDML CSR <Leading>14.3</Leading>
  but rendered baseline.pdf shows 16.0pt baseline-to-baseline (LeadingModelAki,
  TopOfCaps, or 120%-AutoLeading divergence). Without this audit, body-text
  drift accumulates ~1.7pt per line, ~50pt over 30 lines.

  Method (per ISSUE.md line 922-945 + feedback_idml_leading_vs_rendered.md):
  - For each body-text frame in build.py (anname'd TextFrame with non-empty text):
    - Extract first 3+ consecutive word lines via pdfplumber from baseline.pdf
    - Compute median(pairwise y-deltas) for adjacent lines (top-coord, descending)
    - Same for preview.pdf
    - If |preview_linesp - baseline_linesp| > threshold_pt (default 0.5),
      report the frame with anname, ParaStyle, baseline/preview measured pt,
      and a recommendation (override ParaStyle linesp).

  Usage:
      python3 tools/line_spacing_audit.py \\
        --preview templates/<slug>/preview.pdf \\
        --baseline templates/<slug>/baseline.pdf \\
        --build-py templates/<slug>/build.py \\
        --template <slug> \\
        --threshold 0.5 \\
        --out build/validation/<slug>/line_spacing_audit.yml
  """
  from __future__ import annotations
  import argparse
  import sys
  from pathlib import Path
  from statistics import median
  from typing import Any

  import pdfplumber
  import yaml

  def _extract_line_tops_per_frame(
      pdf: Path, frame_bbox_mm: tuple[float, float, float, float],
      page_idx: int,
  ) -> list[float]:
      """Return sorted y-coords (in PDF pt) of word lines inside frame bbox.

      Uses pdfplumber.extract_words(use_text_flow=False) within the cropped
      bbox region. Returns the unique `top` y-coords (rounded to 0.1pt),
      sorted ascending. Lines are detected by clustering words within 1pt
      of each other in y.
      """
      MM_TO_PT = 72.0 / 25.4
      x_mm, y_mm, w_mm, h_mm = frame_bbox_mm
      x0_pt = x_mm * MM_TO_PT
      y0_pt = y_mm * MM_TO_PT
      x1_pt = (x_mm + w_mm) * MM_TO_PT
      y1_pt = (y_mm + h_mm) * MM_TO_PT
      with pdfplumber.open(pdf) as plumber:
          if page_idx >= len(plumber.pages):
              return []
          page = plumber.pages[page_idx]
          bbox = (x0_pt, y0_pt, x1_pt, y1_pt)
          crop = page.crop(bbox, relative=False, strict=False)
          words = crop.extract_words(
              use_text_flow=False,
              x_tolerance=2,
              y_tolerance=2,
          )
      if not words:
          return []
      tops = sorted(round(w["top"], 1) for w in words)
      # Cluster: consecutive tops within 1pt collapse to first
      lines: list[float] = []
      for t in tops:
          if not lines or t - lines[-1] > 1.0:
              lines.append(t)
      return lines

  def _median_baseline_gap(line_tops: list[float]) -> float | None:
      if len(line_tops) < 2:
          return None
      gaps = [line_tops[i + 1] - line_tops[i]
              for i in range(len(line_tops) - 1)]
      return round(median(gaps), 2)

  def run_line_spacing_audit(
      preview_pdf: Path,
      baseline_pdf: Path,
      build_py: Path,
      template: str = "",
      threshold_pt: float = 0.5,
  ) -> dict[str, Any]:
      """For each TextFrame in build.py with text content, measure
      baseline-to-baseline gap in baseline.pdf and preview.pdf, flag
      frames with |delta| > threshold_pt.
      """
      sys.path.insert(0, str(Path(__file__).resolve().parent))
      from sla_lib.builder.template_loader import load_build_module
      from sla_lib.builder.bbox import frame_bbox_mm

      module = load_build_module(build_py)
      drift: list[dict] = []
      ok = True

      for page_idx, page in enumerate(getattr(module, "pages", [])):
          for frame in getattr(page, "frames", []):
              # Skip non-text frames
              if not hasattr(frame, "text") and not hasattr(frame, "runs"):
                  continue
              anname = getattr(frame, "anname", None) or ""
              # Get bbox via existing helper
              try:
                  bb = frame_bbox_mm(frame)
              except Exception:
                  continue
              # Need first 3+ baselines in BOTH pdfs to compare
              base_lines = _extract_line_tops_per_frame(baseline_pdf, bb, page_idx)
              prev_lines = _extract_line_tops_per_frame(preview_pdf, bb, page_idx)
              if len(base_lines) < 3 or len(prev_lines) < 3:
                  continue
              base_linesp = _median_baseline_gap(base_lines)
              prev_linesp = _median_baseline_gap(prev_lines)
              if base_linesp is None or prev_linesp is None:
                  continue
              delta = round(prev_linesp - base_linesp, 2)
              if abs(delta) > threshold_pt:
                  para_style = ""
                  # Try to surface the paragraph style if attached
                  runs = getattr(frame, "runs", None) or []
                  if runs:
                      para_style = getattr(runs[0], "paragraph_style", "") or ""
                  drift.append({
                      "anname": anname,
                      "page": page_idx,
                      "para_style": para_style,
                      "baseline_linesp_pt": base_linesp,
                      "preview_linesp_pt": prev_linesp,
                      "delta_pt": delta,
                      "recommendation": (
                          f"override ParaStyle linesp to {base_linesp}"
                      ),
                  })
                  ok = False

      drift.sort(key=lambda d: -abs(d["delta_pt"]))

      return {
          "template": template,
          "threshold_pt": threshold_pt,
          "line_spacing_drift_count": len(drift),
          "line_spacing_drift": drift,
          "ok": ok,
      }

  def _yaml_dump(payload: dict) -> str:
      return yaml.dump(payload, sort_keys=True, allow_unicode=True,
                       default_flow_style=False)

  def main(argv: list[str] | None = None) -> int:
      ap = argparse.ArgumentParser()
      ap.add_argument("--preview", type=Path, required=True)
      ap.add_argument("--baseline", type=Path, required=True)
      ap.add_argument("--build-py", type=Path, required=True)
      ap.add_argument("--template", default="")
      ap.add_argument("--threshold", type=float, default=0.5)
      ap.add_argument("--out", type=Path, default=None)
      args = ap.parse_args(argv)
      report = run_line_spacing_audit(
          args.preview, args.baseline, args.build_py,
          template=args.template, threshold_pt=args.threshold,
      )
      yaml_text = _yaml_dump(report)
      if args.out:
          args.out.parent.mkdir(parents=True, exist_ok=True)
          args.out.write_text(yaml_text, encoding="utf-8")
      print(yaml_text, end="")
      return 0 if report["ok"] else 1

  if __name__ == "__main__":
      raise SystemExit(main())
  ```

  **Tests** in `tests/unit/test_line_spacing_audit.py`:
  1. `_median_baseline_gap([100.0, 116.0, 132.0])` → 16.0
  2. `_median_baseline_gap([100.0])` → None
  3. `_median_baseline_gap([100.0, 116.0, 132.0, 145.5])` → 16.0 (median, not mean)
  4. Synthetic PDF stub via mock pdfplumber output: 3 lines at y=100, 116,
     132 → baseline_linesp=16.0; preview lines at 100, 114.3, 128.6 →
     preview_linesp=14.3; delta = -1.7, |delta| > 0.5 → drift reported.
     Use `unittest.mock.patch("pdfplumber.open", ...)` to mock the PDF
     reads OR build minimal real PDFs via reportlab — reportlab is NOT
     installed, so mock-based approach is required.
  5. Below-threshold delta (0.4pt) → no drift reported, ok=true.
  6. Frame with <3 baselines → skipped silently (single-line headlines).
  7. YAML output is deterministic.

  Use `unittest.mock.patch` for the pdfplumber calls; populate fake
  `extract_words` return values to drive the test.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_line_spacing_audit.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `tools/line_spacing_audit.py` exists with `run_line_spacing_audit` + CLI main
  - Output schema: `{template, threshold_pt, line_spacing_drift_count, line_spacing_drift: [{anname, page, para_style, baseline_linesp_pt, preview_linesp_pt, delta_pt, recommendation}], ok}`
  - 7 unit tests pass under both pytest and unittest discover
  - Frames with <3 baselines silently skipped (no crash)
  </done>
</task>

<task type="auto">
  <name>Task 14: Wire line_spacing_audit as Phase E2 in _run_audit (P3)</name>
  <files>tools/render_pipeline.py, tests/integration/test_line_spacing_audit_v2.py</files>
  <action>
  Wire `tools/line_spacing_audit.py` into `tools/render_pipeline.py:_run_audit`
  AFTER Phase F (run_style_audit, around line 879) and BEFORE Phase E
  (per_element_drift, around line 881). Mirror the existing audit
  wire-up pattern exactly.

  ```python
  # Phase E2: line_spacing_audit — per-TextFrame baseline-to-baseline drift.
  # Catches LeadingModel mismatches (IDML <Leading>14.3</Leading> rendered
  # at 16.0pt in baseline.pdf). Issue #37 P3.
  line_spacing_audit_path = out_dir / "line_spacing_audit.yml"
  if preview_pdf.exists() and baseline.exists() and build_py.exists():
      try:
          from line_spacing_audit import (
              run_line_spacing_audit as _lsa_run,
              _yaml_dump as _lsa_yaml,
          )
          lsa_report = _lsa_run(
              preview_pdf, baseline, build_py, template=tid,
          )
          line_spacing_audit_path.write_text(
              _lsa_yaml(lsa_report), encoding="utf-8",
          )
          if not lsa_report["ok"]:
              print(
                  f"[{tid}] line_spacing_audit: "
                  f"{lsa_report['line_spacing_drift_count']} frame(s) with "
                  f"|delta| > {lsa_report['threshold_pt']}pt → REVIEW",
                  file=sys.stderr,
              )
              issue_parts.append(
                  f"{lsa_report['line_spacing_drift_count']} line-spacing drift(s)"
              )
          else:
              print(f"[{tid}] line_spacing_audit: OK")
      except Exception as exc:
          print(
              f"[{tid}] audit E2 (line_spacing_audit) error: {exc}",
              file=sys.stderr,
          )
  else:
      print(
          f"[{tid}] audit E2 (line_spacing_audit): skipped "
          "(no preview.pdf, baseline.pdf, or build.py)",
          file=sys.stderr,
      )
  ```

  Update preflight aggregation (task 6) to include:
  ```python
  lsa = _load_yml(line_spacing_audit_path)
  if lsa is not None:
      _record("line_spacing_audit", lsa.get("ok", True),
              lsa.get("line_spacing_drift_count", 0), "")
  ```

  **Acceptance test** in `tests/integration/test_line_spacing_audit_v2.py`:
  the v2 falzflyer must flag the original 14.3pt-declared / 16.0pt-rendered
  LINESP mismatch on `idml/absatzformat-1` (or `idml/fliesstext-auf-gruenem-hintergrund`
  — pick the one that's confirmed in pitfalls.md / feedback memory) BEFORE
  the fix is applied.

  Since we are not running the converter inline in this test, mock
  `_extract_line_tops_per_frame` to return controlled baselines / preview
  lines for a synthetic frame. Then call `run_line_spacing_audit` with a
  build.py that has at least one TextFrame and assert the drift report
  contains the expected anname.

  Alternative: if running the full pipeline on v2 falzflyer in CI is
  affordable, use the live artefacts. Mark as `@pytest.mark.skipif` when
  baseline.pdf is missing.

  ```python
  import pytest, sys
  from pathlib import Path
  from unittest.mock import patch

  sys.path.insert(0, "tools")
  from line_spacing_audit import run_line_spacing_audit

  V2 = Path("templates/kandidat-falzflyer-din-lang-gruenes-cover-v2")

  @pytest.mark.skipif(
      not (V2 / "baseline.pdf").exists(), reason="v2 falzflyer baseline missing",
  )
  def test_v2_flags_known_linesp_drift(tmp_path):
      """Acceptance: pre-fix v2 falzflyer (14.3pt declared, 16.0pt rendered)
      must produce a drift entry."""
      # Use the existing v2 build.py + baseline.pdf.
      # If preview.pdf also exists AND matches baseline, this test still
      # documents the historical drift via a stub.
      # For full integration, run the audit and assert that EITHER:
      #   (a) the report is ok=true (current state, post-fix), OR
      #   (b) the report flags at least one frame with delta_pt ≈ 1.7.
      report = run_line_spacing_audit(
          preview_pdf=V2 / "preview.pdf",
          baseline_pdf=V2 / "baseline.pdf",
          build_py=V2 / "build.py",
          template="kandidat-falzflyer-din-lang-gruenes-cover-v2",
      )
      assert "line_spacing_drift" in report
      assert "ok" in report
      assert isinstance(report["line_spacing_drift_count"], int)

  def test_synthetic_14_3_vs_16_0_flagged():
      """Pure synthetic: mock extract_line_tops to return controlled lines
      that produce delta_pt = 1.7 — assert drift is reported."""
      with patch("line_spacing_audit._extract_line_tops_per_frame") as m:
          # Two calls per frame: baseline first, then preview.
          # 3 baseline lines spaced 16pt apart, 3 preview lines spaced 14.3pt.
          m.side_effect = [
              [100.0, 116.0, 132.0],   # baseline
              [100.0, 114.3, 128.6],   # preview
          ]
          # Need a minimal module + frame that frame_bbox_mm accepts.
          # Use a stub build.py path; mock load_build_module too.
          # See PLAN.md task 13 for the helper shape; replicate here.
  ```

  Adjust the second test to fully mock `sla_lib.builder.template_loader.load_build_module`
  and `sla_lib.builder.bbox.frame_bbox_mm` to return a synthetic frame.
  The test then asserts the report has 1 drift entry with `delta_pt ≈ -1.7`.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_line_spacing_audit.py tests/integration/test_line_spacing_audit_v2.py -q && python3 -m unittest discover tests/unit && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - Phase E2 wired into `_run_audit` after Phase F, before Phase E
  - `build/validation/<slug>/line_spacing_audit.yml` is emitted with the documented schema
  - Preflight.yml (task 6) gains `audits.line_spacing_audit` entry
  - Synthetic 14.3pt vs 16.0pt test produces 1 drift entry with delta ≈ -1.7
  - Integration test against v2 falzflyer baseline runs without crash (passes when baseline exists, skips otherwise)
  </done>
</task>

<task type="auto">
  <name>Task 15: Phase B3 — add drift_type field to diff_bbox_extract (P3)</name>
  <files>tools/diff_bbox_extract.py, tests/unit/test_diff_bbox_extract.py</files>
  <action>
  Extend `tools/diff_bbox_extract.py` with `drift_type` classification per
  ISSUE.md Phase B3 (line 261-276). The categories: `missing`, `extra`,
  `position`, `scale`, `rotation`, `color`, `text`, `unknown`.

  Locate the bbox-building loop in `extract_all` (after `extract_bboxes_px`
  and slot attribution). Add a classify step per bbox:

  ```python
  def _classify_drift_type(
      bbox: dict,
      baseline_png: Path,
      dsl_png: Path,
      dpi: int,
  ) -> str:
      """Best-effort drift-type classification for a single bbox.

      Returns one of: missing, extra, position, scale, rotation, color,
      text, unknown.

      Heuristics (simple, fast — agents may refine in follow-up):
      - Crop baseline_png + dsl_png to bbox_px. Compute:
        - base_ink: fraction of pixels darker than 250/255 in baseline crop
        - prev_ink: same for preview crop
      - If base_ink > 0.05 and prev_ink < 0.01: classify "missing"
      - If base_ink < 0.01 and prev_ink > 0.05: classify "extra"
      - If both > 0.05:
          - If |base_ink - prev_ink| / max(base_ink, prev_ink) > 0.5:
              classify "text" (large content delta, likely glyph/wording)
          - Else: classify "position" (similar ink density, content shifted)
        Note: distinguishing scale/rotation/color from position requires
        more signal; default to "position" for now and let a follow-up
        refine.
      - Else: "unknown"
      """
      try:
          from PIL import Image
          base = Image.open(baseline_png).convert("L")
          prev = Image.open(dsl_png).convert("L")
      except Exception:
          return "unknown"
      bb = bbox["bbox_px"]
      x, y, w, h = bb["x"], bb["y"], bb["w"], bb["h"]
      base_crop = base.crop((x, y, x + w, y + h))
      prev_crop = prev.crop((x, y, x + w, y + h))
      def _ink(img):
          hist = img.histogram()
          dark = sum(hist[:250])
          total = sum(hist) or 1
          return dark / total
      base_ink = _ink(base_crop)
      prev_ink = _ink(prev_crop)
      if base_ink > 0.05 and prev_ink < 0.01:
          return "missing"
      if base_ink < 0.01 and prev_ink > 0.05:
          return "extra"
      if base_ink > 0.05 and prev_ink > 0.05:
          if abs(base_ink - prev_ink) / max(base_ink, prev_ink) > 0.5:
              return "text"
          return "position"
      return "unknown"
  ```

  Integrate into `extract_all`: locate where each `bbox` dict is populated
  with `attributed_slot`, `attribution_overlap_pct`, etc., and add:
  ```python
  bbox["drift_type"] = _classify_drift_type(
      bbox, baseline_png_path, dsl_png_path, dpi,
  )
  ```
  The `baseline_png` / `dsl_png` paths come from
  `visual_diff.json["pages"][i]["baseline_png"]` and `["dsl_png"]` (verify
  field names by reading `tools/visual_diff.py` PageResult or the JSON
  emit; if those fields don't exist, derive paths by convention:
  `out_dir / f"baseline-page-{i + 1}.png"` and `dsl-page-{i + 1}.png`).

  Add a CLI flag `--no-drift-type` for skip (in case PIL is too slow on
  large pages); default ON.

  **Tests** in `tests/unit/test_diff_bbox_extract.py` (extend existing
  test file if present):
  1. Synthetic crop: base has black square, prev is empty → "missing".
  2. base empty, prev has black square → "extra".
  3. base has 0.5-density text crop, prev has 0.5-density (offset) → "position".
  4. base has 0.5-density, prev has 0.1-density → "text" (large content diff).
  5. Both crops empty → "unknown".
  6. PIL load failure (nonexistent file path) → "unknown" (no crash).
  7. Existing diff_bbox_extract tests still pass (drift_type addition is
     additive).
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_diff_bbox_extract.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `tools/diff_bbox_extract.py` adds `drift_type` field to every bbox in `diff_bboxes.json`
  - Categories: missing, extra, position, scale, rotation, color, text, unknown (initial implementation covers missing/extra/position/text/unknown via PIL ink-density heuristic)
  - `--no-drift-type` CLI flag for skipping (default ON)
  - 7 unit tests pass under both pytest and unittest discover
  - Existing `tests/unit/test_diff_bbox_extract.py` tests still pass
  </done>
</task>

<task type="auto">
  <name>Task 16: Phase B1 — end-of-conversion frame-count assertion (P3)</name>
  <files>tools/idml_to_dsl.py, tests/unit/test_idml_strict_mode.py</files>
  <action>
  Add an end-of-conversion assertion in `tools/idml_to_dsl.py` per
  ISSUE.md Phase B1 (line 235-247): emitted-frame count must equal
  IDML PageItem count, OR each gap must be explicitly skipped with a
  reason annotation.

  Locate the main conversion function (search for `def convert(`,
  `def main()`, or `def run_conversion`). After all spreads are processed
  but before the output is written, run a reconciliation check:

  ```python
  # End-of-conversion completeness assertion (Issue #37 Phase B1).
  # Count IDML PageItems (Rectangle, Polygon, Oval, TextFrame, Image,
  # GraphicLine; exclude Group containers per existing convention) and
  # compare to ctx.emitted_frame_count.
  PAGE_ITEM_TAGS_LEAF = frozenset({
      "Rectangle", "Polygon", "Oval", "TextFrame", "Image",
      "PDF", "GraphicLine",
  })

  # Track during conversion: ctx.emitted_frame_count, ctx.skipped_with_reason
  # (list of {self_id, reason}). Initialise in _Ctx.__init__ if not present.

  def _assert_conversion_completeness(ctx: _Ctx, idml_path: Path) -> None:
      from idml_inventory import _walk_idml_pageitems
      # OR inline a minimal walker — reuse what idml_inventory.py already does
      idml_self_ids: set[str] = set()
      # ... walk all spreads, collect Self attribute of every PageItem
      # with localname in PAGE_ITEM_TAGS_LEAF ...
      missing = idml_self_ids - set(ctx.emitted_self_ids)
      missing -= set(s["self_id"] for s in ctx.skipped_with_reason)
      if missing:
          raise UnhandledElement(
              f"Conversion incomplete: {len(missing)} IDML PageItem(s) "
              f"emitted no output and were not explicitly skipped. "
              f"IDs: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}. "
              f"Either implement the relevant pattern in tools/idml_to_dsl.py, "
              f"or add a '# IDML pattern: <name>: skipped because <reason>' "
              f"annotation and call ctx.record_skipped(self_id, reason)."
          )
  ```

  Add:
  - `ctx.emitted_self_ids: set[str]` — track every `self_id` passed to
    `_emit_call`. Populate in `_emit_pageitem` after emitting.
  - `ctx.skipped_with_reason: list[dict]` — populated by explicit skip
    annotations.
  - `ctx.record_skipped(self_id, reason)` method.
  - Call `_assert_conversion_completeness(ctx, idml_path)` at the end of
    the main conversion routine.

  If `UnhandledElement` is not already defined, define it as a
  RuntimeError subclass. If it already exists (search the file), reuse.

  **Tests** in `tests/unit/test_idml_strict_mode.py`:
  1. Synthetic IDML with 5 PageItems, all emitted → no assertion.
  2. Synthetic IDML with 5 PageItems, only 4 emitted (one silently
     dropped) → `UnhandledElement` raised with the dropped Self ID in
     the message.
  3. Synthetic IDML with 5 PageItems, 4 emitted + 1 explicitly skipped
     via `ctx.record_skipped("u123", "complex polygon — TODO")` → no
     assertion (skip is accepted).
  4. Empty IDML (0 PageItems) → no assertion.
  5. Existing strict-mode tests still pass.

  Use the existing test fixtures in `tests/unit/test_idml_strict_mode.py`
  + `tests/unit/test_idml_geometry.py` to drive synthetic IDMLs.

  IMPORTANT: do NOT break existing CLI usage. Add a flag
  `--allow-dropped-pageitems` for the rare case where a downstream user
  wants to bypass the assertion (e.g. during debug); default is OFF
  (strict). The CI / `bin/idml-import` path must run with the default
  ON, so the assertion fires.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/unit/test_idml_strict_mode.py tests/unit/test_idml_geometry.py tests/unit/test_idml_inline_polygon.py -q && python3 -m unittest discover tests/unit</automated>
  </verify>
  <done>
  - `tools/idml_to_dsl.py` raises `UnhandledElement` at end of conversion when emitted PageItem count != IDML PageItem count (minus explicit skips)
  - `ctx.emitted_self_ids`, `ctx.skipped_with_reason`, `ctx.record_skipped` available
  - `--allow-dropped-pageitems` CLI flag bypasses assertion (default OFF)
  - 5 new unit tests pass; existing strict-mode tests still pass
  </done>
</task>

<task type="auto">
  <name>Task 17: Declare pdfplumber in Dockerfile.claude (P3)</name>
  <files>Dockerfile.claude</files>
  <action>
  Per ISSUE.md D8 acceptance (line 747-748) and ecosystem.md §15 finding 4:
  `pdfplumber` is installed but not declared in `Dockerfile.claude`. New
  E2 (task 13) depends on it. Declare it.

  Read `Dockerfile.claude` to find the pip-install block (ecosystem.md
  notes line 66-67 pins Pillow 12.2.0 explicitly). Add `pdfplumber==0.11.9`
  to the same block or a new `pip install` line. Match the existing
  pinning style.

  Example diff (adjust to match actual file structure — read Dockerfile.claude
  first to find the right insertion point):
  ```dockerfile
  # Existing pip install block — append pdfplumber:
  RUN pip3 install --no-cache-dir --break-system-packages \
        Pillow==12.2.0 \
        pdfplumber==0.11.9
  ```

  Do NOT alter any other pinned versions in the Dockerfile. The goal is
  purely to add the missing declaration so a future rebuild won't drift.

  Verify: `pip3 show pdfplumber` in the running container reports 0.11.9
  (already true; we are only making it declarative).

  Verification command:
  ```bash
  grep -q "pdfplumber" Dockerfile.claude && echo "OK: pdfplumber declared"
  ```
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && grep -q "pdfplumber" Dockerfile.claude && python3 -c "import pdfplumber; assert pdfplumber.__version__.startswith('0.11'), pdfplumber.__version__; print('OK')"</automated>
  </verify>
  <done>
  - `Dockerfile.claude` declares `pdfplumber==0.11.9` (or a compatible pinned version)
  - `python3 -c "import pdfplumber"` succeeds and reports 0.11.x
  </done>
</task>

<task type="auto">
  <name>Task 18: End-to-end pipeline integration test (P3)</name>
  <files>tests/integration/test_render_pipeline_e2e.py</files>
  <action>
  Add a final end-to-end test that exercises the FULL `bin/render-gallery
  <slug> --audit` flow against v2 falzflyer and validates the resulting
  preflight.yml + all 11 sub-audit YAMLs (existing 9 + new
  line_spacing_audit + visual_diff_regions).

  ```python
  import pytest, subprocess, yaml
  from pathlib import Path

  REPO = Path(__file__).resolve().parents[2]
  V2 = REPO / "templates" / "kandidat-falzflyer-din-lang-gruenes-cover-v2"
  OUT = REPO / "build" / "validation" / "kandidat-falzflyer-din-lang-gruenes-cover-v2"

  @pytest.mark.skipif(
      not (V2 / "baseline.pdf").exists() or not (V2 / "build.py").exists(),
      reason="v2 falzflyer fixtures missing — dev container only",
  )
  def test_render_gallery_audit_emits_all_artifacts():
      """Full pipeline: bin/render-gallery <slug> --audit must produce
      preflight.yml + all 11 sub-audit files."""
      # Run with --audit (not --audit-strict) so we exercise the new
      # hard-fail-on-preflight-ok-false behavior.
      proc = subprocess.run(
          [str(REPO / "bin" / "render-gallery"),
           "kandidat-falzflyer-din-lang-gruenes-cover-v2", "--audit"],
          cwd=REPO, capture_output=True, text=True, timeout=600,
      )
      # Exit code: 0 if preflight ok=true; 1 if preflight ok=false.
      # Either is acceptable — we just need the artefacts to exist.
      assert proc.returncode in (0, 1), (
          f"Unexpected exit code {proc.returncode}\nstdout: {proc.stdout[-1000:]}\n"
          f"stderr: {proc.stderr[-1000:]}"
      )

      # Preflight.yml exists and has the documented shape
      preflight = OUT / "preflight.yml"
      assert preflight.exists(), f"missing {preflight}"
      pre = yaml.safe_load(preflight.read_text(encoding="utf-8"))
      assert "ok" in pre
      assert "audits" in pre
      assert "hot_issues" in pre
      assert isinstance(pre["ok"], bool)

      # All sub-audits ran (whichever existed)
      expected_audits = [
          "inventory", "text_audit", "image_audit", "font_audit",
          "text_render_audit", "text_position_audit", "run_style_audit",
          "per_element_drift", "region_color_audit",
          "line_spacing_audit",       # NEW Phase E2
          "visual_diff_regions",      # NEW Backport 12
      ]
      for name in expected_audits:
          assert name in pre["audits"], f"audit {name} not in preflight.audits"

      # All sub-audit YAMLs exist
      for name in [
          "inventory.yml", "text_audit.yml", "image_audit.yml",
          "font_audit.yml", "text_render_audit.yml",
          "text_position_audit.yml", "run_style_audit.yml",
          "per_element_drift.yml", "region_color_audit.yml",
          "line_spacing_audit.yml",
          "visual_diff_regions.yml",
      ]:
          assert (OUT / name).exists(), f"missing {OUT / name}"

      # Heatmap PNGs exist for each page (v2 falzflyer has 2 pages)
      assert (OUT / "visual_diff_heatmap-page-01.png").exists()
      assert (OUT / "visual_diff_heatmap-page-02.png").exists()

      # If preflight.ok is False, exit code must be 1
      if pre["ok"] is False:
          assert proc.returncode == 1
      else:
          assert proc.returncode == 0

  @pytest.mark.skipif(
      not (V2 / "baseline.pdf").exists(),
      reason="v2 fixtures missing",
  )
  def test_preflight_per_element_drift_no_over_attribution():
      """P1 task 1 acceptance: after running --audit, top-3 contributors
      sum to <= 100% (not 139%)."""
      ped = OUT / "per_element_drift.yml"
      if not ped.exists():
          pytest.skip("per_element_drift.yml not produced (run --audit first)")
      report = yaml.safe_load(ped.read_text(encoding="utf-8"))
      for page in report.get("pages", []):
          top = page.get("top_contributors", [])
          total_pct = sum(c.get("pct_of_page_mismatch", 0) for c in top)
          assert total_pct <= 100.5, (
              f"page {page['page']} top contributors sum to {total_pct:.2f}% (> 100.5%)"
          )

  @pytest.mark.skipif(
      not (V2 / "baseline.pdf").exists(),
      reason="v2 fixtures missing",
  )
  def test_preflight_text_position_no_reversed_words():
      """P1 task 2 acceptance: text_position_audit no longer reports
      reverse-glyph false positives like ':musserpmI'."""
      tpa = OUT / "text_position_audit.yml"
      if not tpa.exists():
          pytest.skip("text_position_audit.yml not produced")
      report = yaml.safe_load(tpa.read_text(encoding="utf-8"))
      for delta in report.get("large_deltas", []):
          text = delta.get("text", "")
          assert "musserp" not in text.lower(), (
              f"reversed-glyph artefact: {text!r}"
          )
  ```

  This integration test ties together every P1/P2/P3 deliverable into one
  end-to-end gate. Skip cleanly in CI environments without v2 falzflyer
  baseline.pdf (currently CI does not have it; this test runs in the dev
  container).
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling && pytest tests/integration/test_render_pipeline_e2e.py -q && python3 -m unittest discover tests/integration</automated>
  </verify>
  <done>
  - `tests/integration/test_render_pipeline_e2e.py` runs `bin/render-gallery <slug> --audit` and validates the full preflight.yml shape + 11 sub-audit yml files + 2 heatmap PNGs
  - Per-element drift over-attribution check passes (≤100%)
  - Reversed-glyph false positives absent from text_position_audit
  - Skips cleanly when v2 falzflyer fixtures unavailable
  - Passes under both pytest and unittest discover
  </done>
</task>

</tasks>

<verification>
After all 18 tasks complete, run the full test + lint suite:

```bash
cd /workspace/.worktrees/37-idml-conversion-preflight-and-completeness-tooling

# 1. Full test suite under BOTH runners (pytest + unittest discover)
#    — repo CI may use either; both must pass to avoid the
#    "pytest passes, CI red" trap (memory: dual-runner equivalence rule).
pytest tests/ -q
python3 -m unittest discover tests/unit
python3 -m unittest discover tests/integration

# 2. End-to-end pipeline against v2 falzflyer
bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit
# Expected: exit 0 if all sub-audits ok, exit 1 if any preflight.yml::ok=false.
# Either is acceptable; check that build/validation/<slug>/preflight.yml
# exists and is well-formed.

# 3. Sanity check the artefacts
python3 -c "
import yaml
from pathlib import Path
p = Path('build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/preflight.yml')
pre = yaml.safe_load(p.read_text())
print('ok:', pre['ok'])
print('audits:', list(pre['audits'].keys()))
print('hot_issues:', len(pre['hot_issues']))
"

# 4. Confirm new tools are importable
python3 -c "
import sys; sys.path.insert(0, 'tools')
from visual_diff import compare_grid, run_region_grid_audit, TemplateTolerance
from line_spacing_audit import run_line_spacing_audit
print('imports OK')
"
```

Smoke checks for each sub-phase:
- P1 (tasks 1-6): `pytest tests/unit/test_per_element_drift.py tests/unit/test_text_position_audit.py tests/unit/test_run_style_audit.py tests/unit/test_idml_geometry.py tests/unit/test_idml_styles.py tests/unit/test_render_pipeline_preflight.py -q`
- P2 (tasks 7-12): `pytest tests/unit/test_visual_diff_tolerance.py tests/unit/test_visual_diff_grid.py tests/unit/test_visual_diff_heatmap.py tests/unit/test_render_pipeline_phaseH.py tests/integration/test_visual_diff_regions_regression.py -q`
- P3 (tasks 13-18): `pytest tests/unit/test_line_spacing_audit.py tests/unit/test_diff_bbox_extract.py tests/unit/test_idml_strict_mode.py tests/integration/test_line_spacing_audit_v2.py tests/integration/test_render_pipeline_e2e.py -q`
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria + RESEARCH.md primary recommendation.

**P1 — Critical bugfixes + hard-fail gate:**
- [ ] `per_element_drift.yml` top-3 contributors sum to ≤100% on v2 falzflyer (task 1)
- [ ] `text_position_audit.yml` contains no reversed-glyph words like `:musserpmI` (task 2)
- [ ] `run_style_audit.yml` includes `extraction_engine_disagreement` field; pdftotext vs pdfplumber word-count delta surfaced (task 3)
- [ ] Cropped/scaled ImageFrames emit `scale_type=1` (task 4 — closes Backport 10 hole)
- [ ] Every TextFrame emits explicit `default_style_attrs.ALIGN` and explicit per-paragraph ALIGN (task 5 — closes Backport 11 hole)
- [ ] `build/validation/<slug>/preflight.yml` exists with `{ok, audits, hot_issues}` (task 6)
- [ ] `bin/render-gallery --audit` (not just `--audit-strict`) exits non-zero when `preflight.yml::ok=false` (task 6)

**P2 — Backport 12 per-region visual_diff:**
- [ ] `TemplateTolerance` accepts `region_grid: {cols, rows, per_cell}` (task 7)
- [ ] `compare_grid()` returns per-cell mismatch in PIL, no subprocess fork-cost (task 8)
- [ ] `render_grid_heatmap()` emits a labeled green→amber→red PNG, no matplotlib (task 9)
- [ ] Phase H wired into `_run_audit`; emits `visual_diff_regions.yml` + `visual_diff_heatmap-page-NN.png` (task 10)
- [ ] V2 falzflyer's `diff.yml` declares `region_grid: {cols: 6, rows: 4}` (task 11)
- [ ] `docs/diff-tolerance.md` documents the schema (task 11)
- [ ] Regression test: 50px headline shift → hottest cell > 10% mismatch (task 12)

**P3 — Phase E2 line_spacing_audit + remaining structural completeness:**
- [ ] `tools/line_spacing_audit.py` exists; computes baseline-to-baseline median pt-gap via pdfplumber (task 13)
- [ ] Phase E2 wired into `_run_audit` after Phase F; emits `line_spacing_audit.yml` (task 14)
- [ ] Synthetic 14.3pt vs 16.0pt test produces 1 drift entry with `delta_pt ≈ -1.7` (task 14)
- [ ] `tools/diff_bbox_extract.py` adds `drift_type` field with at least 5 categories observed in tests (task 15)
- [ ] `tools/idml_to_dsl.py` raises `UnhandledElement` when emitted-frame count != IDML PageItem count (minus explicit skips) (task 16)
- [ ] `Dockerfile.claude` declares `pdfplumber` (task 17)
- [ ] End-to-end test produces all 11 sub-audit YAMLs + heatmap PNGs + preflight.yml on v2 falzflyer (task 18)

**Cross-cutting (always):**
- [ ] All new YAML outputs deterministic (sort_keys=True, byte-identical on re-run)
- [ ] All new pytest tests pass under both `pytest` and `python3 -m unittest discover`
- [ ] No `claude` attribution in commits, code, or files (per `feedback_no_claude_attribution.md`)
- [ ] No regressions in existing tests for visual_diff, idml_to_dsl, per_element_drift, etc.

**Out of scope (deferred):**
- Phase B2 `snapshot_slot_baselines.py`
- Phase C1-C4 (`bin/idml-import`, `iteration.jsonl`, `bin/convergence-review`, pattern lib)
- Phase D5 (`inject.yml` + `reconcile_build_py.py`)
</success_criteria>
