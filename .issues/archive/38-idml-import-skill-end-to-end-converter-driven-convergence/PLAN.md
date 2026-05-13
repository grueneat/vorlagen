# Plan: IDML import skill — end-to-end converter-driven convergence

<objective>
What this plan accomplishes: Ship the one-command `bin/idml-import` driver + classifier + asset audit + pattern library + `/idml-import` skill + `inject.yml` reconcile so the user can drop one or more `.idml` files in a known directory, invoke a single skill, and get fully imported templates that converge against `baseline.pdf` without falling into the "engine floor" trap.

Why it matters: Issue #35 showed two Sonnet executors (~5 hr / ~1500 tool calls) declared a false "engine floor" while 7 concrete converter bugs went unfixed. Prose-only SOPs failed. This issue replaces prose with machine enforcement: the SOP becomes the tools, not the documentation.

Scope (per RESEARCH.md primary recommendation — three INDEPENDENT sub-phases):
- **P1 (tasks 1-8)** — driver + classifier + asset audit + machine enforcement (Phases A + B + E + hooks). User-visible: `bin/idml-import <path>` works end-to-end.
- **P2 (tasks 9-14)** — pattern library refactor (Phase D). Extract 6 inline backports from `tools/idml_to_dsl.py` into `tools/idml_to_dsl_patterns/<name>.py` with byte-identity regression; add the NEW `image_frame_pdf_source_for_vectors` pattern.
- **P3 (tasks 15-18)** — `/idml-import` skill (Phase C) + `inject.yml` overlay (Phase F) + v2 falzflyer migration + CI lint.

Out of scope (deferred to follow-up issues):
- `drift_type` schema extension (scale/color emission)
- Reportable-to-upstream Scribus bug-report templates
- Multi-IDML coalescing into a single template
- Retroactive `TOLERANCE_LOG.md` migration for the existing 9 templates

Source: CONTEXT.md does not exist for this issue; decisions are based on RESEARCH.md primary recommendation + ISSUE.md acceptance criteria + the user's structuring guidance in the planner prompt.
</objective>

<skills>
No workspace skills currently exist relevant to this work (the only existing skill `.claude/skills/experiments/SKILL.md` is a model to mirror, not a runtime dependency). Task 15 CREATES the `.claude/skills/idml-import/` skill.

The executor MUST follow these in-repo conventions (no skill file required; they are constant context):
- All commits prefixed `38: <type>(<scope>): <subject>` per `.issues/config.yaml::commits`.
- All file paths in code/output should be repo-relative (never `/workspace/.worktrees/...` literals).
- No "claude" attribution in commits/code/files (memory `feedback_no_claude_attribution.md`).
</skills>

<context>
Issue: @.issues/38-idml-import-skill-end-to-end-converter-driven-convergence/ISSUE.md
Research synthesis: @.issues/38-idml-import-skill-end-to-end-converter-driven-convergence/RESEARCH.md
Codebase research: @.issues/38-idml-import-skill-end-to-end-converter-driven-convergence/research/codebase.md
Pitfalls research: @.issues/38-idml-import-skill-end-to-end-converter-driven-convergence/research/pitfalls.md
Config: @.issues/config.yaml

**Worktree convention**: The executor creates a fresh worktree at
`/workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence/`
on branch `issue/38-idml-import-skill-end-to-end-converter-driven-convergence`,
branched from `origin/main` (which already has all #76 + #77 work shipped).

<interfaces>
<!-- Executor: use these contracts directly. DO NOT explore the codebase for them.
     Source: research/codebase.md, all line numbers from main. -->

# tools/links_export.py (481 LOC) — existing asset extractor (REUSE)
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

# Dispatch table at lines 154-180:
#   .ai  → pdftocairo -png -transp -r 600 -singlefile
#   .psd → Pillow ImageCms (ICC-aware; docstring lies — says convert -flatten)
#   .jpg → passthrough (.jpeg→.jpg rename)
#   .png → passthrough
#   else → skipped[]


# tools/idml_to_dsl.py (3360 LOC) — converter (REUSE; refactor in P2)
def convert(source, output, template_id, assets_dir,
            logo_map_path=None, asset_map_path=None,
            allow_dropped_pageitems=False) -> None
def main(argv) -> int

# Shipped patterns currently inline (P2 extracts these):
JUSTIFICATION_MAP = {"LeftAlign":0,"CenterAlign":1,"RightAlign":2,
                     "FullyJustified":3,"LeftJustified":3,
                     "RightJustified":3,"CenterJustified":3}  # line 992 — Backport 9
# scale_type=1 emission when local_scale/local_offset_pt deviate — lines 2040-2061 (Backport 10)
# default_style ALIGN + per-paragraph ALIGN propagation — lines 2305-2390 (Backport 11)
# PolyLine PLINEEND/PLINEJOIN from EndCap/EndJoin — lines 1858-1879

# CLI flags:
#   --template-id SLUG (REQUIRED)
#   --asset-map PATH (PREFERRED — Phase 2 manifest from links_export.py)
#   --assets-dir PATH (legacy; hardcoded default is v2-falzflyer-specific — DO NOT use)
#   --logo-map PATH (legacy)
#   --allow-dropped-pageitems (debug bypass)

# tools/render_pipeline.py (1444 LOC) — orchestrator (REUSE)
def _run_audit(tdir, meta, args) -> tuple[int, str]  # line 662
def _build_preflight(tdir, meta, audit_results) -> dict  # line 1097
def _verify_brand_fonts() -> None  # line 262 — HARD-FAILS if fc-list has <30 gruene fonts
def main(argv) -> int

# Existing audit chain order in _run_audit:
#   A1 inventory → A2 baseline_text → A3 baseline_image → D6 font →
#   D7 text_render → D8 text_position → F run_style → E2 line_spacing →
#   E per_element_drift (diagnostic only) →
#   G region_color (diagnostic only) → H visual_diff_regions
# Task 2 wires asset_extraction_audit BEFORE A1.

# tools/sla_lib/builder/brand_constraints.py — registry pattern model (line 1525)
class BrandRule(Protocol):
    id: str
    name: str
    def check(self, doc) -> list[Violation]: ...
BRAND_CONSTRAINTS: list[BrandRule] = [_make_rule(...), ...]  # 16 rules

# tools/sla_lib/builder/meta_schema.py
def load_brand_overrides(slug, root) -> set[str]  # JSON-Schema validated
def load_ci_overrides(slug, root) -> dict          # non_ci_styles/colors/layers

# tools/experiment_envelope.py:170-185 — jsonschema validation idiom (REUSE for inject.schema.yaml)
# Uses Draft202012Validator(schema).validate(data)

# bin/render-gallery shim model (15 lines; mirror this for bin/idml-import + bin/convergence-review)


# AUDIT YAML SCHEMAS (post-#37, on main) — consumed by convergence_review.py

# build/validation/<slug>/preflight.yml
{template, ok: bool,
 audits: {<name>: {ok: bool, issues: int, detail: str}, ...},
 hot_issues: [{audit, issues, message}]}

# build/validation/<slug>/per_element_drift.yml (DIAGNOSTIC ONLY in preflight)
{template, pages: [{page, total_mismatch_pct, total_mismatch_px,
                    bbox_count, normalisation_factor,
                    top_contributors: [{slot, mismatch_px_summed,
                                        pct_of_page_mismatch,
                                        pct_of_page_total_drift,
                                        bbox_count}]}]}

# build/validation/<slug>/region_color_audit.yml (DIAGNOSTIC ONLY in preflight)
{template, by_severity: {ok, icc_likely, fill_likely},
 pattern: "predominantly_icc_drift"|"concentrated_fill_bugs"|"mixed",
 frames: [{anname, page, type, bbox_mm, baseline_rgb, preview_rgb,
           mean_delta, rms_delta, severity}]}
# NOTE: tools/region_color_audit.py:6 and :245 currently contain the literal
# string "engine floor". Task 1 renames these to "icc_drift_uniform_small".

# build/validation/<slug>/text_position_audit.yml
{template, threshold_pt, common_word_threshold,
 large_deltas_count, suppressed_common_word_deltas_count,
 suppressed_unmatched_word_count,
 large_deltas: [{text, page, baseline_xy_pt, preview_xy_pt, dx_pt, dy_pt, severity}],
 ok}

# build/validation/<slug>/run_style_audit.yml
{template, baseline_word_count, preview_word_count, threshold_size_pt,
 common_word_threshold, style_drift_count,
 suppressed_common_word_drifts_count,
 style_drifts: [{text, page, baseline:{fontname,size,color},
                 preview:{...}, drift:{fontname,size_pt,color}, severity}],
 ok, extraction_engine_disagreement?: {...}}

# build/validation/<slug>/diff_bboxes.json (POST-#37: drift_type field added)
{dpi, template_slug,
 pages: [{page, delta_png,
          bboxes: [{bbox_px, bbox_mm, area_px, mismatch_pct_in_bbox,
                    attributed_slot, attribution_overlap_pct,
                    attribution_candidates,
                    drift_type: "missing"|"extra"|"position"|"text"|"unknown"}]}]}

# build/validation/<slug>/visual_diff.json
{template, pass, pages: [{page, mismatch_pct, mismatch_pixels, delta_png}]}

# All 11 audit YAMLs the convergence_review.py reads:
#   preflight.yml, inventory.yml, text_audit.yml, image_audit.yml,
#   font_audit.yml, text_render_audit.yml, text_position_audit.yml,
#   run_style_audit.yml, per_element_drift.yml, region_color_audit.yml,
#   line_spacing_audit.yml, visual_diff_regions.yml, diff_bboxes.json,
#   visual_diff.json
</interfaces>

**v2 falzflyer state (template under test for end-to-end + migration tasks)**:
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` currently contains
  **14 `# P5/inject` comments** (lines 70, 117, 124, 157, 170, 180, 376, 402, 493,
  504, 621, 752 + 2 more per RESEARCH.md count).
- meta.yml has 5 brand_overrides silently added in #35.
- Composite-AI: `Social Media Icons weiss.ai` is 1-page 526x152pt strip
  (aspect ratio 3.5:1, 4 icons side-by-side).
</context>

<call_sites>
Searched (CLI surfaces this plan touches): `bin/idml-import` (NEW),
`bin/convergence-review` (NEW), `--accept-residual`, `--max-iterations`,
`--scaffold-only`, `--reimport`, `--no-brand-fonts`, `--format md|json`,
`tools/idml_to_dsl.py`, `tools/links_export.py`, `tools/render_pipeline.py`,
`bin/render-gallery`.

Surfaces grepped: `.github/workflows/`, `Makefile`, `bin/`, `tools/`,
`README*`, `docs/`, `.pre-commit-config.yaml` (if present).

Found (in-scope for this plan):
- `bin/idml-import` (new shim) — created in Task 4. CALL SITES of this NEW
  binary that the plan establishes: README.md (Task 8), docs/idml-import-workflow.md
  (Task 8), `.claude/skills/idml-import/SKILL.md` (Task 15).
- `bin/convergence-review` (new shim) — created in Task 5. Called by
  `tools/idml_import_driver.py` (Task 4) and from the skill SOP (Task 15).
- `tools/region_color_audit.py:6, :245` — current "engine floor" strings;
  RENAMED in Task 1. Call sites: existing region_color_audit tests (updated
  in Task 1) + `tools/render_pipeline.py` consumes the audit's `pattern`
  enum (Task 1 verifies no other consumers grep for the string).
- `.github/workflows/` CI gates — Task 18 wires `tools/sop_lint.py`,
  `tools/check_overrides_growth.py`, `tools/lint_inject_consistency.py` into
  pre-commit + GitHub Actions. Task 1 wires `sop_lint.py` first; Tasks 3 + 18
  wire the others.
- `tools/idml_to_dsl.py` — refactored across Tasks 10-14 to consume the new
  pattern registry from `tools/idml_to_dsl_patterns/__init__.py`. Byte-identity
  preserved against v2 falzflyer build.py at each step.
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` — Task 17 migrates
  14 P5/inject comments to inject.yml; Task 17 confirms reconcile produces
  byte-identical build.py.

Out-of-scope call sites (explicit deferrals):
- Other templates' meta.yml `brand_overrides` retroactive TOLERANCE_LOG.md —
  one-time migration deferred to follow-up; Task 3's lint catches FUTURE adds only.
- `bin/render-gallery` invocations in CI: NOT modified by this plan (it
  already supports `--audit-strict`; Task 4 just calls it).
- Pre-existing `tools/idml_to_dsl.py` CLI flags: untouched by this plan.
</call_sites>

<commit_format>
Format: conventional with issue prefix (per `.issues/config.yaml::commits`).
Pattern: `38: <type>(<scope>): <subject>`

Examples per task:
- Task 1: `38: chore(region_color_audit): rename engine_floor to icc_drift_uniform_small`
- Task 1: `38: feat(sop_lint): ban engine floor phrase in tracked files`
- Task 2: `38: feat(asset_extraction_audit): composite-AI detection + Phase E wire-up`
- Task 3: `38: feat(check_overrides_growth): gate brand_overrides growth on TOLERANCE_LOG row`
- Task 4: `38: feat(idml-import): one-command end-to-end driver`
- Task 5: `38: feat(convergence-review): classify + leverage-sort audit issues`
- Task 6: `38: feat(idml-import): iteration.jsonl log + regression guard`
- Task 7: `38: test(integration): bin/idml-import end-to-end on v2 falzflyer`
- Task 8: `38: docs(idml-import): README + walkthrough`
- Task 9: `38: feat(idml_to_dsl_patterns): registry scaffold + INDEX.md`
- Task 10: `38: refactor(idml_to_dsl_patterns): extract justification_to_align (Backport 9)`
- Task 11: `38: refactor(idml_to_dsl_patterns): extract default_style_align_inheritance (Backport 11)`
- Task 12: `38: refactor(idml_to_dsl_patterns): extract scale_type_for_cropped_images (Backport 10)`
- Task 13: `38: refactor(idml_to_dsl_patterns): extract polyline + textframe + group patterns`
- Task 14: `38: feat(idml_to_dsl_patterns): image_frame_pdf_source_for_vectors + composite_ai_split`
- Task 15: `38: feat(skills): .claude/skills/idml-import SOP`
- Task 16: `38: feat(reconcile_build_py): inject.yml overlay + byte-stability`
- Task 17: `38: refactor(v2-falzflyer): migrate 14 P5/inject comments to inject.yml`
- Task 18: `38: feat(lint_inject_consistency): CI lint for build.py inject.yml mapping`
</commit_format>

<tasks>

<!-- ============================================================
     P1 — Driver + classifier + asset audit + machine enforcement
     Tasks 1-8
     ============================================================ -->

<task type="auto">
  <name>Task 1: Rename "engine floor" + ship sop_lint.py</name>
  <files>tools/region_color_audit.py, tools/sop_lint.py, tests/unit/test_region_color_audit.py, tests/unit/test_sop_lint.py</files>
  <action>
  STEP A — rename existing strings (acceptance criterion: grep -i "engine[_ ]floor" returns 0 hits across templates/, tools/, bin/, .claude/skills/, .issues/):

  1. In `tools/region_color_audit.py:6` change docstring `"icc_likely — engine floor"` to `"icc_likely — icc_drift_uniform_small (sub-percent uniform RGB delta from ICC profile rendering)"`.
  2. In `tools/region_color_audit.py:245` change comment `"CMYK to sRGB ICC profile rendering drift (engine floor)"` to `"CMYK to sRGB ICC profile rendering drift (icc_drift_uniform_small)"`.
  3. Grep the tree (`git grep -i "engine[_ ]floor"`) and verify ZERO hits across `templates/`, `tools/`, `bin/`, `.claude/`, `.issues/`. Fix any remaining references (most likely none, but check `docs/`, `*.md`, `CHANGELOG.md`).
  4. Update `tests/unit/test_region_color_audit.py` to assert the new string in the audit's reported `pattern` field if it appears in any assertion.

  STEP B — ship `tools/sop_lint.py` (new file):

  ```python
  #!/usr/bin/env python3
  """SOP lint — bans the phrase 'engine floor' (and synonyms) in tracked files.
  Run via pre-commit + CI. Exit 0 = clean, 1 = banned phrase found."""
  import re, subprocess, sys
  BANNED = [r"engine[_ ]floor", r"engine[_ ]ceiling", r"rendering[_ ]floor"]
  SCOPES = ["templates/", "tools/", "bin/", ".claude/", ".issues/", "docs/", "README", "CHANGELOG"]
  def main():
      pattern = "|".join(BANNED)
      tracked = subprocess.check_output(["git", "ls-files"]).decode().splitlines()
      offenders = []
      regex = re.compile(pattern, re.IGNORECASE)
      for path in tracked:
          if not any(path.startswith(s) or s in path for s in SCOPES):
              continue
          try:
              with open(path, "r", encoding="utf-8") as fh:
                  for lineno, line in enumerate(fh, 1):
                      if regex.search(line):
                          offenders.append((path, lineno, line.rstrip()))
          except (UnicodeDecodeError, IsADirectoryError):
              continue
      if offenders:
          print("SOP-LINT FAILED — banned phrase found:", file=sys.stderr)
          for p, ln, txt in offenders:
              print(f"  {p}:{ln}: {txt}", file=sys.stderr)
          return 1
      return 0
  if __name__ == "__main__":
      sys.exit(main())
  ```

  Make it executable (`chmod +x tools/sop_lint.py`).

  STEP C — write `tests/unit/test_sop_lint.py`:
  - Test 1 (positive): with a tracked fixture file containing "engine floor", main() returns 1.
  - Test 2 (negative): with the same fixture renamed to "icc_drift_uniform_small", main() returns 0.
  - Test 3 (scope): a "engine floor" in `node_modules/foo.js` (not tracked, not in SCOPES) is ignored.
  - Test 4 (synonyms): "engine ceiling" and "rendering floor" both trigger.
  Use `tmp_path` + `subprocess.run` to invoke from a fresh git repo OR monkeypatch `git ls-files` output. The latter is more reliable in CI.

  WHY: RESEARCH.md identifies this as a P0 blocker — the acceptance criterion "grep returns 0 hits" fails out-of-the-box until renamed. The sop_lint locks the rename in mechanically.

  Per user-locked decision: NO synonym for "engine floor" sneaks back in via paraphrase ("engine ceiling", "rendering floor"); the lint catches both.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_region_color_audit.py tests/unit/test_sop_lint.py -q && python3 -m unittest discover tests/unit -p "test_region_color_audit.py" && python3 -m unittest discover tests/unit -p "test_sop_lint.py" && python3 tools/sop_lint.py && ! git grep -iE "engine[_ ]floor|engine[_ ]ceiling|rendering[_ ]floor" -- 'tools/' 'templates/' 'bin/' '.claude/' 'docs/' 'README*'</automated>
  </verify>
  <done>
  - `tools/region_color_audit.py` no longer contains "engine floor" (or any banned synonym).
  - `tools/sop_lint.py` exists, executable, returns exit 0 on clean tree.
  - `tests/unit/test_sop_lint.py` covers 4 cases (positive, negative, scope, synonym).
  - `git grep -iE "engine[_ ]floor|engine[_ ]ceiling|rendering[_ ]floor"` returns 0 hits in `tools/ templates/ bin/ .claude/ docs/ README*`.
  </done>
</task>

<task type="auto">
  <name>Task 2: asset_extraction_audit.py + composite-AI detection + Phase E wire-up</name>
  <files>tools/asset_extraction_audit.py, tools/render_pipeline.py, tests/unit/test_asset_extraction_audit.py, tests/integration/test_asset_audit_wired_into_run_audit.py</files>
  <action>
  STEP A — ship `tools/asset_extraction_audit.py` (new file).

  Public signature:
  ```python
  def audit(slug: str, idml_path: Path, links_export_yml: Path, repo_root: Path) -> dict
  ```
  Behaviour:
  1. Parse the IDML with `simple_idml` to walk every `<Link LinkResourceURI=...>` element across all Stories + Spreads. Collect link target basenames.
  2. Assert sibling `Links/` directory exists. For each link basename: assert presence in `Links/`. Missing => record in `links_missing: list[str]`.
  3. Read `links_export_yml` (from a prior `tools/links_export.py` run). For each link basename: assert there's a manifest entry. Missing => `links_unconverted: list[str]`.
  4. **Composite-AI detection** (per RESEARCH.md P0 #2):
     - For each `.ai` asset, open with `pdfplumber.open(path)`; record `page_count` and per-page bbox.
     - For each ImageFrame in IDML pointing at the AI, parse its `<Properties><PathGeometry>` and `<Properties><LocalOffset>` (lxml xpath `.//ImageFrame[@*[contains(name(), "LinkResourceURI")]]`). Collect distinct `(offset_x, offset_y, scale_x, scale_y)` tuples per AI source.
     - Mark AI as composite if ANY of:
       (a) `page_count > 1`
       (b) `aspect_ratio = max(w,h)/min(w,h) > 3.0`
       (c) `len(distinct_imageframe_offsets) >= 2 and not all offsets equal (0,0)`
     - Record composite AIs in `composite_ai_detected: list[{path, page_count, aspect_ratio, distinct_offsets_count}]`.
  5. Emit `build/validation/<slug>/asset_audit.yml`:
     ```yaml
     template: <slug>
     ok: bool   # True only if links_missing=[] AND links_unconverted=[] AND composite_ai_detected=[]
     links_total: N
     links_resolved: N
     links_converted: N
     links_missing: []
     links_unconverted: []
     composite_ai_detected: []
     ```
  6. Return the dict + exit code semantics: 0 on `ok=True`, 1 on `ok=False`.

  Use `yaml.safe_dump(data, sort_keys=True)` for byte-stability.

  Detection rule policy (RESEARCH.md P0 #2): composite AI is NOT a hard refuse in Phase 1 — Task 14 introduces the splitter. For Phase 1 of P1, emit `composite_ai_detected` and let `ok=False` block convergence with a clear remediation: "composite AI detected; Task 14's `tools/composite_ai_split.py` handles this. Re-run `bin/idml-import --reimport` after Task 14 ships, OR pass `--allow-composite-ai` to bypass (degraded vector quality)."

  Add an `--allow-composite-ai` flag to the audit (default False) that downgrades the composite finding from `ok=False` to a warning in `asset_audit.yml::warnings: list[str]`.

  STEP B — wire into `tools/render_pipeline.py::_run_audit` (line 662):

  Insert `asset_extraction_audit` as the FIRST audit step (before A1 inventory) so missing assets fail-fast before inventory tries to read them. Pass `args.idml_path` + `args.allow_composite_ai` through. If `asset_audit.yml::ok == False`, set `audit_results["asset_extraction"] = {ok: False, ...}` and continue to record other audits (they may fail downstream, which is the desired signal).

  Update `_build_preflight` so it includes `asset_extraction` in the `audits:` dict.

  STEP C — tests:
  - `tests/unit/test_asset_extraction_audit.py`:
    - synthetic minimal IDML zip (in-memory BytesIO + zipfile per `tests/unit/test_idml_inventory.py` pattern) with one Link to 1 `.ai` sibling, `links_export.yml` lists it; assert ok=True.
    - same fixture with the `.ai` missing from `Links/`; assert ok=False, `links_missing` contains it.
    - same fixture with the `.ai` present but missing from `links_export.yml`; assert ok=False, `links_unconverted`.
    - synthetic IDML referencing a wide-strip "AI" (use a single-page 600x100 pt PDF with `.ai` extension as a fixture); assert composite detection by aspect ratio.
    - `--allow-composite-ai`: same fixture; assert ok=True with `warnings` populated.
  - `tests/integration/test_asset_audit_wired_into_run_audit.py`:
    - Mock or stub `_run_audit` with a fixture template directory + `meta.yml`; assert asset_extraction runs FIRST in the audit chain (verify ordering by attribute set on the results dict or by logging assertion).

  Use `pdfplumber` for page count, `simple_idml` for IDML walk, `lxml` for ImageFrame offset extraction.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_asset_extraction_audit.py tests/integration/test_asset_audit_wired_into_run_audit.py -q && python3 -m unittest discover tests/unit -p "test_asset_extraction_audit.py" && python3 -m unittest discover tests/integration -p "test_asset_audit_wired_into_run_audit.py"</automated>
  </verify>
  <done>
  - `tools/asset_extraction_audit.py` exists with `audit(slug, idml_path, links_export_yml, repo_root) -> dict`.
  - Composite-AI detection fires on (page_count > 1) OR (aspect_ratio > 3.0) OR (>=2 distinct ImageFrame offsets).
  - `build/validation/<slug>/asset_audit.yml` shape matches the spec in this task's action.
  - Audit wired into `_run_audit` BEFORE A1 inventory.
  - `--allow-composite-ai` flag downgrades composite finding to warning.
  - 5 unit tests + 1 integration test pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 3: check_overrides_growth.py — gate brand_overrides growth</name>
  <files>tools/check_overrides_growth.py, tests/unit/test_check_overrides_growth.py</files>
  <action>
  Ship `tools/check_overrides_growth.py` (new file).

  Behaviour: diff `templates/*/meta.yml::brand_overrides` (and `non_ci_styles`, `non_ci_colors`, `non_ci_layers`) between the git base ref (`origin/main`) and HEAD. For each ADDED entry, assert that one of:
  - The same commit adds a row in `templates/<slug>/TOLERANCE_LOG.md` matching the entry.
  - The same commit adds a corresponding entry in `templates/<slug>/inject.yml::hand_patches` with a non-empty `reason` field (cross-reference target by slug).
  If neither, exit 1 with a clear error: `"meta.yml::brand_overrides added '<rule>' in templates/<slug>/ without TOLERANCE_LOG.md row or inject.yml entry. Add one explaining the rationale."`

  CLI:
  ```
  python3 tools/check_overrides_growth.py [--base-ref origin/main]
  ```
  Default base ref is `origin/main`. Reads `git diff <base>...HEAD --unified=0 -- 'templates/*/meta.yml'`, parses both versions with `PyYAML`, computes the set delta on each tolerance list.

  Implementation notes:
  - Use `subprocess.check_output(["git", "show", f"{base}:templates/<slug>/meta.yml"])` to read the base version.
  - Use `yaml.safe_load`.
  - For TOLERANCE_LOG matching: any row containing the rule name verbatim counts (markdown table parsing is overkill — substring match on the rule id is sufficient).
  - For inject.yml matching: load the YAML and check `hand_patches[*].reason` is non-empty and references the rule id OR the field being overridden.

  Tests in `tests/unit/test_check_overrides_growth.py`:
  - Test 1: base meta.yml has `brand_overrides: ["X"]`, HEAD adds `["X", "Y"]`, no TOLERANCE_LOG row => exit 1.
  - Test 2: same diff, TOLERANCE_LOG.md adds a "## Y — added 2026-05-13 — reason: ..." row => exit 0.
  - Test 3: same diff, inject.yml adds `{target: ..., reason: "Y rationale"}` => exit 0.
  - Test 4: HEAD removes an entry => exit 0 (removal is always allowed).
  - Test 5: base ref doesn't have meta.yml (new template) => all entries are "added"; require TOLERANCE_LOG.md for each.

  Use `subprocess.run` with `capture_output=True` + a synthetic git repo per `tmp_path` for each test. OR monkeypatch a `_git_show` shim. The latter is faster — prefer it.

  WHY: RESEARCH.md identifies this as P1 mechanism for "no silent tolerance growth". Issue #35 added 5 brand_overrides silently masking real converter bugs; this prevents recurrence. Task 18 wires it into pre-commit + CI.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_check_overrides_growth.py -q && python3 -m unittest discover tests/unit -p "test_check_overrides_growth.py" && python3 tools/check_overrides_growth.py --base-ref HEAD</automated>
  </verify>
  <done>
  - `tools/check_overrides_growth.py` exists with `--base-ref` flag.
  - Detects added entries in `brand_overrides`, `non_ci_styles`, `non_ci_colors`, `non_ci_layers`.
  - Requires a matching TOLERANCE_LOG.md row OR inject.yml entry; otherwise exits 1.
  - 5 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 4: bin/idml-import driver + tools/idml_import_driver.py</name>
  <files>bin/idml-import, tools/idml_import_driver.py, tests/unit/test_idml_import_driver.py</files>
  <action>
  STEP A — ship `bin/idml-import` (15-line shim mirroring `bin/render-gallery`):
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  exec python3 "$HERE/tools/idml_import_driver.py" "$@"
  ```
  Make executable.

  STEP B — ship `tools/idml_import_driver.py` (~400-600 LOC).

  CLI per ISSUE.md Phase A schema (use argparse, mirror existing tools' style):
  ```
  bin/idml-import <path>... [--accept-residual ISSUE_ID...] [--dry-run]
                            [--max-iterations N] [--keep-baseline-from-pdf PATH]
                            [--scaffold-only] [--reimport] [--no-brand-fonts]
                            [--allow-composite-ai] [--non-interactive]
  ```

  Flow (one IDML at a time; if `<path>` is a directory, walk for `*.idml` and process each):

  1. **Pre-flight tool availability** — `pdftocairo`, `pdffonts`, `convert`, `scribus` via `shutil.which`. Missing => exit 1 with install hints.
  2. **Slugify** — `tools.links_export.slugify_stem(idml_filename)` => `<slug>`.
  3. **Existing-template detection** — if `templates/<slug>/` exists AND no `--reimport`: exit 1 with the message in research/pitfalls.md section 9.1 ("templates/<slug>/ exists; use --reimport, or rename, or remove first").
  4. **Brand-fonts gate** — call `render_pipeline._verify_brand_fonts()` unless `--no-brand-fonts` is passed. Loud WARNING on bypass.
  5. **baseline.pdf resolution** — read sibling `<stem>.pdf` of the IDML; override with `--keep-baseline-from-pdf`. Missing => exit 1 with the message in research/pitfalls.md section 12.1.
  6. **Asset extraction** — invoke `tools.links_export.export(links_dir=<idml-parent>/Links, out_dir=shared/assets/<slug>)`. Capture `manifest_path` (links_export.yml).
  7. **Asset-extraction audit** — invoke `tools.asset_extraction_audit.audit(slug, idml_path, links_export_yml, repo_root)`. If `ok=False` and not `--allow-composite-ai`, exit 1.
  8. **Scaffold** — write `templates/<slug>/meta.yml` (minimal: `template: <slug>`, no brand_overrides) + `templates/<slug>/diff.yml` (minimal: `dpi: 300`, `fuzz_pct: 2.0`). Copy baseline.pdf to `templates/<slug>/baseline.pdf`.
  9. **Convert** — invoke `tools/idml_to_dsl.py --template-id <slug> --asset-map <links_export.yml>` to `templates/<slug>/build.py`.
  10. **`--scaffold-only` exit point** — if set, exit 0 after first audit (step 11).
  11. **Convergence loop** (max `--max-iterations`, default 10):
      a. Run `bin/render-gallery <slug> --audit-strict`.
      b. Run `bin/convergence-review <slug> --format json` (Task 5).
      c. Append iteration row to `build/<slug>/iteration.jsonl` (Task 6).
      d. Regression guard (Task 6): if `drift_p1 > prev_drift.p1 + 0.05`, exit 3.
      e. If `preflight.ok == True`, exit 0.
      f. Compute actionable issues = converter-bug union scribus-engine-bug minus `--accept-residual`. If actionable=[] and all remaining issues are in `--accept-residual` AND classified as `human-review|authoring-bug`, exit 0. Else if actionable=[] but unaccepted residual remains and `--non-interactive`, exit 2. Else (TTY): pause with prompt to fix manually, then continue.
      g. The driver does NOT auto-fix converter-bugs in this issue — it surfaces them and exits 2 with the issue list. Auto-fix is a follow-up (the executor or human is expected to extend the converter, then re-run).
  12. **Emit `build/<slug>/import_report.md`** — final summary listing PASS / NEEDS_REVIEW / BLOCKED with the classified issue list from the last convergence-review.

  Exit code semantics (per RESEARCH.md):
  - 0 = preflight.ok=true OR all-residual-accepted.
  - 1 = converter/asset/unknown failure (run aborted).
  - 2 = needs human review (NEEDS_REVIEW with unaccepted residual).
  - 3 = drift regression detected / max-iterations exceeded.

  STEP C — unit tests in `tests/unit/test_idml_import_driver.py`:
  - Test 1: tool-availability check => mock `shutil.which` to return None for `scribus`; assert exit 1 with install hint.
  - Test 2: slugify + existing-template detection => fixture `templates/<slug>/` exists, no `--reimport`; assert exit 1.
  - Test 3: missing baseline.pdf => exit 1 with the specific message.
  - Test 4: `--scaffold-only` => asserts driver halts after step 10.
  - Test 5: convergence-loop terminates on preflight.ok=true => mock convergence_review to return ok; exit 0 + iteration.jsonl has 1 row.
  - Test 6: `--max-iterations 1` with unresolved issues => exit 3.
  - Test 7: `--accept-residual` covers a human-review issue => exit 0; iteration.jsonl logs it.
  - Test 8: `--non-interactive` with NEEDS_REVIEW + unaccepted => exit 2.

  Use `pytest` fixtures + monkeypatch for subprocess calls. Mock `tools.links_export.export`, `tools.asset_extraction_audit.audit`, `subprocess.run` for `bin/render-gallery` + `bin/convergence-review`.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_idml_import_driver.py -q && python3 -m unittest discover tests/unit -p "test_idml_import_driver.py" && test -x bin/idml-import && bin/idml-import --help</automated>
  </verify>
  <done>
  - `bin/idml-import` shim exists + executable.
  - `tools/idml_import_driver.py` exists with full CLI per ISSUE.md Phase A.
  - Pre-existing-template detection refuses without `--reimport`.
  - Asset audit failure aborts before scaffold.
  - `--scaffold-only` mode stops cleanly after first audit.
  - 8 unit tests pass under BOTH pytest and unittest discover.
  - Exit codes 0/1/2/3 per spec.
  </done>
</task>

<task type="auto">
  <name>Task 5: bin/convergence-review + tools/convergence_review.py</name>
  <files>bin/convergence-review, tools/convergence_review.py, tests/unit/test_convergence_review.py</files>
  <action>
  STEP A — ship `bin/convergence-review` shim (15 lines, mirrors `bin/idml-import` pattern).

  STEP B — ship `tools/convergence_review.py` (~300-500 LOC).

  CLI:
  ```
  bin/convergence-review <slug> [--format md|json] [--out PATH]
                                [--min-drift-pp 0.5] [--idml PATH]
  ```

  Reads from `build/validation/<slug>/`:
  - preflight.yml (mandatory)
  - inventory.yml, text_audit.yml, image_audit.yml, font_audit.yml,
    text_render_audit.yml, text_position_audit.yml, run_style_audit.yml,
    per_element_drift.yml, region_color_audit.yml, line_spacing_audit.yml,
    visual_diff_regions.yml
  - diff_bboxes.json, visual_diff.json

  Emits a sorted issue list per the ISSUE.md Phase B example. Fields per issue:
  - `id: int`
  - `slot: str` (anname)
  - `audit: str` (which audit reported it)
  - `severity: str` (audit-specific severity tag)
  - `classification: "converter-bug"|"scribus-engine-bug"|"authoring-bug"|"human-review"`
  - `converter_path: "tools/idml_to_dsl.py:1782-1798 (DefaultStyle ALIGN)"` (when known)
  - `suggested_action: str` (multi-line)
  - `regression_test_path: str` (proposed path)
  - `est_drift_drop: float` (estimated pp)

  Plus a top-level `hot_issues_by_leverage` list sorted by `-est_drift_drop`.

  **Classification heuristics (P5 from ISSUE.md, refined by RESEARCH.md "Classification rules"):**

  | Signal | Classification | Confidence |
  |---|---|---|
  | `region_color_audit::icc_likely` + brand-color region (RGB delta <= 2.0) | scribus-engine-bug | HIGH |
  | `region_color_audit::fill_likely` (RGB delta > 5.0) | converter-bug | HIGH |
  | `text_position_audit::large_deltas` with dx>0.5pt AND IDML XPath (if --idml given) shows mixed-Justification | converter-bug | MEDIUM |
  | `per_element_drift::top_contributors` slot matches Backport-10-class IDML attrs (image with local_offset != 0 + local_scale != 1) | scribus-engine-bug | HIGH |
  | `diff_bboxes::drift_type == "missing"` + bbox covers IDML element NOT in build.py annames | converter-bug | HIGH |
  | `font_audit::missing_in_preview` non-empty | converter-bug (missing font emission) | MEDIUM |
  | `run_style_audit::style_drifts` with font name mismatch + IDML has correct font | converter-bug | HIGH |
  | `line_spacing_audit::drift_pt > 0.5` | converter-bug (CSR Leading vs rendered) | MEDIUM |
  | Otherwise | human-review | SAFE FALLBACK |

  Bias to `human-review` on uncertainty.

  **Leverage scoring** (RESEARCH.md):
  ```python
  def est_drift_drop(issue, per_element_drift):
      slot, page = issue.slot, issue.page
      regions = per_element_drift.get(page, {}).get("top_contributors", [])
      contributions = [r["pct_of_page_mismatch"] for r in regions if r["slot"] == slot]
      page_total = per_element_drift.get(page, {}).get("total_mismatch_pct", 0)
      return min(sum(contributions), page_total)
  ```
  Sort key: `(-est_drift_drop, severity_rank, slot)` for byte-stable output.

  **Minor-issue filter** (RESEARCH.md 7.4): if `est_drift_drop < --min-drift-pp` (default 0.5), classification becomes a 5th category `minor` and the issue does NOT appear in `hot_issues_by_leverage`. It still appears in `issues:` for completeness.

  **Verdict**:
  - `PASS` — preflight.ok=true.
  - `NEEDS_WORK` — preflight.ok=false; at least 1 issue classified converter-bug or scribus-engine-bug.
  - `BLOCKED_BY_AUTHORING` — all open issues are authoring-bug.

  **--format md** emits a markdown report; **--format json** emits JSON for `bin/idml-import` consumption. Default md.

  STEP C — tests in `tests/unit/test_convergence_review.py`:
  - Fixture: synthetic `build/validation/<slug>/` directory with the 13 YAMLs/JSONs (use yaml.safe_dump + json.dumps to write fixtures).
  - Test 1: preflight.ok=true => verdict=PASS, issues=[].
  - Test 2: region_color_audit reports `icc_likely` for a brand-color frame => classification=scribus-engine-bug.
  - Test 3: text_position_audit large_delta + IDML mixed-Justification => classification=converter-bug + converter_path includes `tools/idml_to_dsl.py`.
  - Test 4: drift_bboxes drift_type=missing + bbox not in annames => classification=converter-bug.
  - Test 5: leverage sorting => issues sorted by -est_drift_drop.
  - Test 6: --min-drift-pp filter => 0.3pp issue classified as `minor`, not in hot_issues.
  - Test 7: --format json produces parseable JSON with all fields.
  - Test 8: ambiguous signals (e.g. text drift but no IDML info) => classification=human-review.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_convergence_review.py -q && python3 -m unittest discover tests/unit -p "test_convergence_review.py" && test -x bin/convergence-review && bin/convergence-review --help</automated>
  </verify>
  <done>
  - `bin/convergence-review` shim exists + executable.
  - `tools/convergence_review.py` reads all 11 audit outputs + diff_bboxes.json + visual_diff.json.
  - Per-issue classification covers 4 categories + `minor` filter category.
  - `est_drift_drop` leverage scoring per RESEARCH.md formula.
  - Sort by `(-est_drift_drop, severity_rank, slot)` for byte-stability.
  - `--format md|json` both work.
  - 8 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 6: iteration.jsonl schema + log writer + regression guard</name>
  <files>tools/idml_import_driver.py, tests/unit/test_iteration_log.py</files>
  <action>
  Extend `tools/idml_import_driver.py` (built in Task 4) with the iteration-log mechanism.

  Add `log_iteration(slug: str, iteration: int, review: dict, changes: list[str]) -> dict` which:
  1. Constructs row:
     ```python
     row = {
         "iteration": iteration,
         "timestamp": datetime.now(timezone.utc).isoformat(),
         "preflight_ok": review["preflight_ok"],
         "issues_open": len([i for i in review["issues"] if i["classification"] != "minor"]),
         "drift_p1": review.get("drift", {}).get("p1", None),
         "drift_p2": review.get("drift", {}).get("p2", None),
         "drift_p1_max_region": review.get("drift", {}).get("p1_max_region", None),
         "drift_p2_max_region": review.get("drift", {}).get("p2_max_region", None),
         "changes": changes,
         "audits_run": review.get("audits_run", []),
         "rules_seen": iteration,  # incremented each iteration; SOP-injection counter
         "_schema_version": 1,
     }
     ```
  2. Appends to `build/<slug>/iteration.jsonl` as `json.dumps(row, separators=(",",":")) + "\n"`.
  3. Returns the row.

  Add `regression_guard(slug: str, current_row: dict) -> Optional[str]` which:
  1. Reads the previous row from `iteration.jsonl` (penultimate line).
  2. If `current_row["drift_p1"] > prev["drift_p1"] + 0.05` AND `current_row["drift_p1_max_region"] > prev["drift_p1_max_region"]`, return error string `"drift regression: p1 went from {prev} to {curr}"`. Per RESEARCH.md 8.1: page-wide is the primary signal, per-region is secondary; halt only if BOTH regressed.
  3. Filter audits: only compare audits that appeared in BOTH iterations (`current_row["audits_run"] intersect prev["audits_run"]`). If a new audit appeared this iteration, treat the issue-count delta from that audit as `audit_added` event, not regression.
  4. Return None if no regression.

  Wire into the convergence loop (Task 4 step 11): after step 11c (`log_iteration`), call `regression_guard`; on non-None return, exit 3 with the error message.

  Tests in `tests/unit/test_iteration_log.py`:
  - Test 1: log_iteration writes a single line + correct shape (round-trip via json.loads).
  - Test 2: 3 iterations written, file has 3 lines.
  - Test 3: regression_guard returns None for monotonically decreasing drift.
  - Test 4: regression_guard returns error when p1 jumps up by 0.1 AND p1_max_region also up.
  - Test 5: regression_guard returns None when p1 jumps up but p1_max_region drops (structural fix masking per-region anti-aliasing).
  - Test 6: regression_guard ignores new audits — iteration N has 5 audits, iteration N-1 has 4; the diff in issues_open is attributed to the new audit, not regression.
  - Test 7: `_schema_version: 1` always present.
  - Test 8: rules_seen monotonically increases (counter for SOP-injection-bug detection per RESEARCH.md 1.2).

  WHY: Per ISSUE.md P10 acceptance ("every render cycle logged; regressions surfaced") and RESEARCH.md 8.1 mitigation.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_iteration_log.py -q && python3 -m unittest discover tests/unit -p "test_iteration_log.py"</automated>
  </verify>
  <done>
  - `log_iteration()` writes valid JSONL rows with the schema above.
  - `regression_guard()` halts only when both page-wide AND per-region max regressed.
  - `_schema_version: 1` present in every row.
  - 8 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 7: End-to-end integration test on v2 falzflyer</name>
  <files>tests/integration/test_idml_import_v2_falzflyer.py</files>
  <action>
  Ship `tests/integration/test_idml_import_v2_falzflyer.py`.

  Test 1: `test_bin_idml_import_v2_falzflyer_end_to_end()`:
  1. Locate the v2 falzflyer IDML: try `originals/.../26-03 Leporello Z-Falz 99x210, 6-seitig grünes Cover 2.idml`. Skip the test with `pytest.skip(...)` if not present (CI may not have the originals).
  2. Set up an isolated tmp template root (or use the existing `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` with `--reimport`).
  3. Invoke `subprocess.run(["bin/idml-import", str(idml_path), "--max-iterations", "3", "--non-interactive", "--allow-composite-ai", "--accept-residual", "*"])` — `--accept-residual *` here means "accept any residual" for the purposes of this smoke test (the executor implements `*` as wildcard in Task 4; or use the literal set of expected residuals).
  4. Assert one of:
     - Exit code 0 (full PASS — preflight.ok=true OR fully accepted), OR
     - Exit code 2 (NEEDS_REVIEW with explicit accept_residual covering remaining authoring-bug class) — acceptable for this test as long as the asserted invariants below hold.
  5. Assert `build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/preflight.yml` exists.
  6. Assert `build/kandidat-falzflyer-din-lang-gruenes-cover-v2/iteration.jsonl` exists and has >= 1 row.
  7. Assert `build/kandidat-falzflyer-din-lang-gruenes-cover-v2/import_report.md` exists and contains either "PASS" or "NEEDS_REVIEW".
  8. Assert `build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/asset_audit.yml` exists and has `ok: true` (composite-AI allowed via flag).

  Test 2: `test_bin_idml_import_missing_idml_fails_cleanly()`:
  1. Invoke `subprocess.run(["bin/idml-import", "/nonexistent/path.idml"])`.
  2. Assert exit code 1 with stderr containing "not found" or "missing".

  Test 3: `test_bin_idml_import_scaffold_only_no_convergence_loop()`:
  1. With the v2 falzflyer IDML (or a smaller fixture IDML if available), invoke with `--scaffold-only --reimport`.
  2. Assert exit code 0.
  3. Assert `templates/<slug>/{build.py,meta.yml,diff.yml,baseline.pdf}` exist after the run.
  4. Assert `build/<slug>/iteration.jsonl` has exactly 1 row (single first-audit cycle, no loop).

  Marker the entire module with `@pytest.mark.integration` (or add to `pytest.ini` `markers` if not present) so unit-test runs can skip it. Make it skippable if `bin/render-gallery` cannot find brand fonts (use `--no-brand-fonts` in that case as a fallback path).

  WHY: This is the acceptance test for the full P1 pipeline — RESEARCH.md highest-leverage mitigation 7.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/integration/test_idml_import_v2_falzflyer.py -q --tb=short && python3 -m unittest discover tests/integration -p "test_idml_import_v2_falzflyer.py"</automated>
  </verify>
  <done>
  - Test 1 passes (or skips gracefully when originals/ unavailable in CI).
  - Test 2 verifies clean failure on missing IDML.
  - Test 3 verifies `--scaffold-only` halts after first audit.
  - Tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 8: README + walkthrough docs</name>
  <files>README.md, docs/idml-import-workflow.md</files>
  <action>
  STEP A — update `README.md` (read it first to determine exact insertion point):
  - Add a section "IDML Import" near the top (after the project intro / installation).
  - Point to `bin/idml-import` as THE canonical entry point. Show the basic invocation:
    ```
    bin/idml-import path/to/template.idml
    bin/idml-import path/to/incoming/   # batch
    ```
  - Link to `docs/idml-import-workflow.md` for the full walkthrough.
  - Link to `.claude/skills/idml-import/SKILL.md` (will exist after Task 15) for skill-driven runs.

  STEP B — create `docs/idml-import-workflow.md` (~200-400 LOC):

  Sections:
  1. **Overview** — one-paragraph summary of what `bin/idml-import` does.
  2. **Prerequisites** — Scribus, poppler-utils, ImageMagick, Python deps (pdfplumber, simple_idml, lxml, jsonschema, PyYAML, Pillow). Brand fonts for full audit; `--no-brand-fonts` for CI.
  3. **Quick start** — drop an IDML, run the command, read the import_report.md.
  4. **CLI reference** — full flag list with examples.
  5. **The convergence loop** — explain the 11 audits, classification, `--accept-residual`, `--max-iterations`.
  6. **Output layout** — `templates/<slug>/{build.py,meta.yml,diff.yml,baseline.pdf,template.sla,preview.pdf,page-*.png,inject.yml}` + `build/<slug>/{iteration.jsonl,import_report.md}` + `build/validation/<slug>/*.yml`.
  7. **Exit codes** — 0/1/2/3 semantics per Task 4.
  8. **Re-importing an existing template** — `--reimport` workflow with inject.yml preservation.
  9. **Composite-AI handling** — per Task 14 + 2; mention that until Task 14 lands, `--allow-composite-ai` is the bypass.
  10. **Troubleshooting** — common failure modes (missing brand fonts, missing baseline.pdf, sluggified-name collisions per RESEARCH.md 9.2).
  11. **See also** — link to `.claude/skills/idml-import/SKILL.md`, `tools/sop_lint.py`, `tools/check_overrides_growth.py`.

  WHY: ISSUE.md cross-cutting acceptance criterion: "`bin/idml-import` is the documented entry point in `README.md`."
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && test -f docs/idml-import-workflow.md && test -f README.md && grep -q "bin/idml-import" README.md && grep -q "idml-import-workflow" README.md && grep -qi "exit codes" docs/idml-import-workflow.md && grep -qi "convergence loop" docs/idml-import-workflow.md && python3 tools/sop_lint.py</automated>
  </verify>
  <done>
  - `README.md` has an "IDML Import" section linking to bin/idml-import + docs/idml-import-workflow.md.
  - `docs/idml-import-workflow.md` exists with all 11 sections above.
  - `tools/sop_lint.py` passes (no "engine floor" introduced in new docs).
  </done>
</task>

<!-- ============================================================
     P2 — Pattern library refactor
     Tasks 9-14
     ============================================================ -->

<task type="auto">
  <name>Task 9: Pattern registry scaffold + Pattern base class + INDEX.md</name>
  <files>tools/idml_to_dsl_patterns/__init__.py, tools/idml_to_dsl_patterns/INDEX.md, tools/idml_to_dsl_patterns/base.py, tests/unit/test_pattern_registry.py</files>
  <action>
  STEP A — create the patterns package:

  1. `tools/idml_to_dsl_patterns/base.py`:
     ```python
     """Pattern base class for IDML to DSL converter extensions.

     Patterns mutate the kwargs dict that idml_to_dsl.py passes to its element
     emitters. Order matters; later patterns can override earlier kwargs."""
     from typing import Protocol

     class Pattern(Protocol):
         id: str            # unique identifier, e.g. "justification_to_align"
         description: str   # one-line human-readable description
         applies_to: str    # element type the pattern matches: "TextFrame"|"ImageFrame"|"PolyLine"|"ParaStyle"|"DefaultStyle"|"AllElements"
         def matches(self, idml_element) -> bool: ...
         def apply(self, kwargs: dict, idml_element, context: dict | None = None) -> None: ...
     ```

  2. `tools/idml_to_dsl_patterns/__init__.py`:
     ```python
     """Pattern registry. Order matters: later patterns can override earlier kwargs."""
     from .base import Pattern
     # Tasks 10-14 append imports here.
     PATTERNS: list[Pattern] = [
         # Placeholder; populated by Tasks 10-14.
     ]
     ```

  3. `tools/idml_to_dsl_patterns/INDEX.md`:
     Catalogue table with columns: `id | description | source IDML attribute | target SLA attribute | regression test path | last_fired_on_template`. Initial row template (filled in Tasks 10-14):
     ```
     | id | description | source | target | test | last_fired |
     |----|-------------|--------|--------|------|-----------|
     | (populated in Tasks 10-14) |
     ```

  STEP B — write `tests/unit/test_pattern_registry.py`:
  - Test 1: PATTERNS is a list (even if empty initially).
  - Test 2: every entry in PATTERNS implements the Pattern Protocol (has id, description, applies_to, matches(), apply()).
  - Test 3: every pattern id is unique across the registry.
  - Test 4: every pattern id is documented in INDEX.md (substring match).

  WHY: Per ISSUE.md Phase D acceptance "Pattern registry in `__init__.py`" and "INDEX.md documents each pattern". This task creates the scaffold; Tasks 10-14 fill it.

  Use `BRAND_CONSTRAINTS` (tools/sla_lib/builder/brand_constraints.py:1525) as the model: a hand-rolled ordered list, no entry_points / pkgutil auto-discovery.

  Future patterns (Tasks 10-14) MUST add their imports to `__init__.py` AND their row to INDEX.md.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_pattern_registry.py -q && python3 -m unittest discover tests/unit -p "test_pattern_registry.py" && python3 -c "from tools.idml_to_dsl_patterns import PATTERNS; assert isinstance(PATTERNS, list)"</automated>
  </verify>
  <done>
  - `tools/idml_to_dsl_patterns/__init__.py` exists with `PATTERNS: list[Pattern]`.
  - `tools/idml_to_dsl_patterns/base.py` defines the Pattern Protocol.
  - `tools/idml_to_dsl_patterns/INDEX.md` exists with the catalogue table scaffold.
  - 4 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 10: Extract Backport 9 (JUSTIFICATION_MAP) into justification_to_align pattern</name>
  <files>tools/idml_to_dsl_patterns/justification_to_align.py, tools/idml_to_dsl_patterns/__init__.py, tools/idml_to_dsl_patterns/INDEX.md, tools/idml_to_dsl.py, tests/unit/test_pattern_justification_to_align.py, tests/integration/test_v2_falzflyer_build_byte_identity.py</files>
  <action>
  STEP A — snapshot the current v2 falzflyer `build.py` BEFORE refactor:
  Copy `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` to a test fixture `tests/integration/fixtures/v2_falzflyer_build_py_pre_refactor.py.snapshot`. This is the byte-identity oracle for Tasks 10-13.

  STEP B — extract Backport 9 into a pattern:

  Create `tools/idml_to_dsl_patterns/justification_to_align.py`:
  ```python
  """Backport 9: IDML Justification attribute => Scribus ALIGN integer.

  Sources:
  - IDML: <ParagraphStyle Justification="LeftAlign|CenterAlign|RightAlign|FullyJustified|LeftJustified|RightJustified|CenterJustified">
  - Scribus SLA: ALIGN attribute on PARAGRAPHSTYLE / paragraph_attrs
  """
  from .base import Pattern

  JUSTIFICATION_MAP = {
      "LeftAlign":       0,
      "CenterAlign":     1,
      "RightAlign":      2,
      "FullyJustified":  3,
      "LeftJustified":   3,
      "RightJustified":  3,
      "CenterJustified": 3,
  }

  class JustificationToAlign:
      id = "justification_to_align"
      description = "Map IDML Justification to Scribus ALIGN integer (Backport 9)"
      applies_to = "ParaStyle"

      def matches(self, idml_element) -> bool:
          # The kwargs path: caller passes a ParaStyle XML element OR the dict
          # of attrs. We check both for compatibility.
          if hasattr(idml_element, "get"):
              return idml_element.get("Justification") in JUSTIFICATION_MAP
          return False

      def apply(self, kwargs: dict, idml_element, context=None) -> None:
          j = idml_element.get("Justification")
          if j in JUSTIFICATION_MAP:
              kwargs["ALIGN"] = JUSTIFICATION_MAP[j]
  ```

  STEP C — refactor `tools/idml_to_dsl.py`:
  - Remove the inline `JUSTIFICATION_MAP` dict at line 992.
  - At the emission point that currently consults the inline map, import and use `JustificationToAlign().apply(kwargs, paragraph_style_element)`.
  - Add `from tools.idml_to_dsl_patterns import PATTERNS` at the top.

  STEP D — register the pattern:
  - Add to `tools/idml_to_dsl_patterns/__init__.py::PATTERNS`:
    ```python
    from .justification_to_align import JustificationToAlign
    PATTERNS: list[Pattern] = [
        JustificationToAlign(),
    ]
    ```
  - Add row to `INDEX.md`:
    ```
    | justification_to_align | Map IDML Justification to ALIGN int | ParaStyle.Justification | PARAGRAPHSTYLE.ALIGN | tests/unit/test_pattern_justification_to_align.py | kandidat-falzflyer-din-lang-gruenes-cover-v2 |
    ```

  STEP E — tests:

  1. `tests/unit/test_pattern_justification_to_align.py`:
     - Synthetic IDML fixture (in-memory BytesIO + zipfile) with ParaStyle Justification="CenterAlign"; assert kwargs["ALIGN"] == 1 after apply().
     - Same with "RightJustified" => 3.
     - Same with no Justification attr => matches() returns False, apply() does not mutate kwargs.
     - Pattern.applies_to == "ParaStyle"; Pattern.id == "justification_to_align".

  2. `tests/integration/test_v2_falzflyer_build_byte_identity.py`:
     - Re-emit v2 falzflyer build.py via `tools/idml_to_dsl.py` against the existing v2 IDML in `originals/...` (skip test if originals unavailable).
     - Compare the re-emitted bytes against `tests/integration/fixtures/v2_falzflyer_build_py_pre_refactor.py.snapshot`.
     - Assert byte-identical OR raise with a unified diff for triage.

  WHY: Per ISSUE.md Phase D acceptance "tools/idml_to_dsl.py iterates patterns at the right emission points; behavior identical to current converter on v2 falzflyer template (regression test)".

  Per RESEARCH.md P4: "Regression test BEFORE refactor: snapshot the current emitted build.py for ALL 4 templates ... After refactor, re-emit and demand byte-identical output." The snapshot is the contract.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_pattern_justification_to_align.py tests/integration/test_v2_falzflyer_build_byte_identity.py -q && python3 -m unittest discover tests/unit -p "test_pattern_justification_to_align.py" && python3 -m unittest discover tests/integration -p "test_v2_falzflyer_build_byte_identity.py"</automated>
  </verify>
  <done>
  - `tools/idml_to_dsl_patterns/justification_to_align.py` exists with JustificationToAlign class.
  - Registered in PATTERNS + documented in INDEX.md.
  - `tools/idml_to_dsl.py` no longer has the inline JUSTIFICATION_MAP at line 992; uses the pattern.
  - v2 falzflyer build.py byte-identity test passes (re-emission matches pre-refactor snapshot).
  - 4 unit tests + 1 integration test pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 11: Extract Backport 11 (DefaultStyle ALIGN inheritance)</name>
  <files>tools/idml_to_dsl_patterns/default_style_align_inheritance.py, tools/idml_to_dsl_patterns/__init__.py, tools/idml_to_dsl_patterns/INDEX.md, tools/idml_to_dsl.py, tests/unit/test_pattern_default_style_align.py, tests/integration/test_v2_falzflyer_build_byte_identity.py</files>
  <action>
  Same refactor pattern as Task 10, for Backport 11 (DefaultStyle ALIGN propagation, currently at `tools/idml_to_dsl.py:2305-2390`).

  Create `tools/idml_to_dsl_patterns/default_style_align_inheritance.py`:
  ```python
  """Backport 11: Propagate ALIGN from DefaultStyle to per-paragraph paragraph_attrs.

  Scribus's ALIGN-on-trail does NOT propagate to the paragraph it terminates,
  only DefaultStyle ALIGN does. This pattern emits DefaultStyle ALIGN AND
  per-paragraph ALIGN regardless of effective alignment, not only when non-zero.
  """
  from .base import Pattern
  from .justification_to_align import JUSTIFICATION_MAP

  class DefaultStyleAlignInheritance:
      id = "default_style_align_inheritance"
      description = "Propagate DefaultStyle ALIGN to per-paragraph paragraph_attrs (Backport 11)"
      applies_to = "TextFrame"
      depends_on = ["justification_to_align"]   # JUSTIFICATION_MAP from there

      def matches(self, idml_element) -> bool:
          # Matches TextFrame elements with a default ParaStyle that has Justification.
          # ... full logic extracted from idml_to_dsl.py:2305-2390 ...
          return True   # simplified; real impl mirrors current behaviour

      def apply(self, kwargs: dict, idml_element, context=None) -> None:
          # Mirror exactly the current Backport 11 logic at lines 2305-2390:
          # - Read DefaultStyle ParaStyle.Justification
          # - Map via JUSTIFICATION_MAP
          # - Emit default_style_attrs["ALIGN"] = N
          # - For each paragraph in the frame, emit paragraph_attrs["ALIGN"] = N
          #   (even when N == 0; suppression was the original bug)
          ...
  ```

  Order matters: this pattern depends on `JustificationToAlign`. The Pattern Protocol's `depends_on: list[str]` is informational (Task 9 may add a topo-sort assertion; for now, rely on PATTERNS list order). Register AFTER JustificationToAlign in `__init__.py::PATTERNS`.

  Refactor `tools/idml_to_dsl.py:2305-2390` to invoke `DefaultStyleAlignInheritance().apply(kwargs, text_frame_element, context={...})` and remove the inline logic.

  Tests:
  - `tests/unit/test_pattern_default_style_align.py`:
    - Synthetic IDML fixture with TextFrame + DefaultStyle ParaStyle Justification="CenterAlign"; assert kwargs["default_style_attrs"]["ALIGN"] == 1.
    - Same with Justification="LeftAlign"; assert kwargs["default_style_attrs"]["ALIGN"] == 0 (the suppressed case — Backport 11's fix is emitting 0 explicitly).
    - Per-paragraph propagation: kwargs["paragraph_attrs"][0]["ALIGN"] == 1.
    - Depends-on contract: assert `depends_on == ["justification_to_align"]`.
  - Re-run `tests/integration/test_v2_falzflyer_build_byte_identity.py` (already exists from Task 10); byte-identity preserved.

  WHY: Per ISSUE.md Phase D acceptance. Per RESEARCH.md P4: byte-identity test after EACH pattern extraction, not just at the end.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_pattern_default_style_align.py tests/integration/test_v2_falzflyer_build_byte_identity.py -q && python3 -m unittest discover tests/unit -p "test_pattern_default_style_align.py" && python3 -m unittest discover tests/integration -p "test_v2_falzflyer_build_byte_identity.py"</automated>
  </verify>
  <done>
  - `tools/idml_to_dsl_patterns/default_style_align_inheritance.py` exists.
  - Registered AFTER justification_to_align in PATTERNS.
  - `tools/idml_to_dsl.py:2305-2390` inline logic removed; pattern invoked instead.
  - v2 falzflyer byte-identity test still passes.
  - 4 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 12: Extract Backport 10 (SCALETYPE for cropped images)</name>
  <files>tools/idml_to_dsl_patterns/scale_type_for_cropped_images.py, tools/idml_to_dsl_patterns/__init__.py, tools/idml_to_dsl_patterns/INDEX.md, tools/idml_to_dsl.py, tests/unit/test_pattern_scale_type_cropped.py, tests/integration/test_v2_falzflyer_build_byte_identity.py</files>
  <action>
  Same refactor pattern, for Backport 10 (`tools/idml_to_dsl.py:2040-2061`).

  Create `tools/idml_to_dsl_patterns/scale_type_for_cropped_images.py`:
  ```python
  """Backport 10: Emit SCALETYPE=1 (free scale) only when local_scale or local_offset_pt
  deviate from identity. Otherwise SCALETYPE=0 (fit-to-frame).

  Scribus 1.6.x renders SCALETYPE=1 with high downscale ratio invisible
  (white-on-transparent RGBA PNG). This pattern emits SCALETYPE=0 in those
  cases to work around the engine bug.
  """
  from .base import Pattern

  class ScaleTypeForCroppedImages:
      id = "scale_type_for_cropped_images"
      description = "Emit SCALETYPE=1 only for cropped images (Backport 10)"
      applies_to = "ImageFrame"

      def matches(self, idml_element) -> bool:
          # Match ImageFrame elements with LocalOffset or LocalScale set
          return True   # full logic mirrors current behaviour at idml_to_dsl.py:2040-2061

      def apply(self, kwargs: dict, idml_element, context=None) -> None:
          # Mirror exactly: if local_scale != (1.0, 1.0) OR local_offset_pt != (0.0, 0.0):
          #   kwargs["scale_type"] = 1
          # else:
          #   kwargs["scale_type"] = 0
          ...
  ```

  Register in PATTERNS (order: after DefaultStyleAlignInheritance is fine; this pattern is independent).

  Refactor `tools/idml_to_dsl.py:2040-2061` to call `ScaleTypeForCroppedImages().apply(...)`.

  Tests in `tests/unit/test_pattern_scale_type_cropped.py`:
  - Synthetic ImageFrame with LocalOffset=(0,0), LocalScale=(1,1) => scale_type=0.
  - Same with LocalOffset=(5,0) => scale_type=1.
  - Same with LocalScale=(2,1) => scale_type=1.
  - Pattern.applies_to == "ImageFrame".

  Re-run v2 falzflyer byte-identity test (already exists).
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_pattern_scale_type_cropped.py tests/integration/test_v2_falzflyer_build_byte_identity.py -q && python3 -m unittest discover tests/unit -p "test_pattern_scale_type_cropped.py" && python3 -m unittest discover tests/integration -p "test_v2_falzflyer_build_byte_identity.py"</automated>
  </verify>
  <done>
  - `tools/idml_to_dsl_patterns/scale_type_for_cropped_images.py` exists.
  - Registered in PATTERNS; documented in INDEX.md.
  - `tools/idml_to_dsl.py:2040-2061` inline logic removed; pattern invoked instead.
  - v2 falzflyer byte-identity test still passes.
  - 4 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 13: Extract PolyLine + TextFrame-height-widening + Group-transform-cascade patterns</name>
  <files>tools/idml_to_dsl_patterns/polyline_round_caps_joins.py, tools/idml_to_dsl_patterns/text_frame_height_widening.py, tools/idml_to_dsl_patterns/group_transform_cascade.py, tools/idml_to_dsl_patterns/__init__.py, tools/idml_to_dsl_patterns/INDEX.md, tools/idml_to_dsl.py, tests/unit/test_pattern_polyline_round_caps.py, tests/unit/test_pattern_text_frame_height_widening.py, tests/unit/test_pattern_group_transform_cascade.py, tests/integration/test_v2_falzflyer_build_byte_identity.py</files>
  <action>
  Three patterns extracted in one task (each is small, ~40-80 LOC of pattern code + tests).

  STEP A — `polyline_round_caps_joins.py` (from `tools/idml_to_dsl.py:1858-1879`):
  ```python
  """Map IDML EndCap=RoundEndCap / EndJoin=RoundEndJoin to Scribus
  PLINEEND=32 / PLINEJOIN=128."""
  from .base import Pattern

  CAP_MAP = {"RoundEndCap": 32, "ButtEndCap": 0, "ProjectingEndCap": 16}
  JOIN_MAP = {"RoundEndJoin": 128, "MiterEndJoin": 0, "BevelEndJoin": 64}

  class PolylineRoundCapsJoins:
      id = "polyline_round_caps_joins"
      description = "Map IDML EndCap/EndJoin to Scribus PLINEEND/PLINEJOIN"
      applies_to = "PolyLine"
      def matches(self, idml_element) -> bool: ...
      def apply(self, kwargs, idml_element, context=None) -> None: ...
  ```

  STEP B — `text_frame_height_widening.py` (extract the current TextFrame-height pattern that compensates for Scribus's silent text clip vs IDML's silent overflow; locate in current converter via grep for `widen` or similar markers — RESEARCH.md identifies this as "current Pattern 9").

  STEP C — `group_transform_cascade.py` (extract the Group ItemTransform cascade logic that applies parent transforms down to child PageItems; locate in current converter — typical IDML Group handling).

  STEP D — register all three in PATTERNS (order: independent of each other; place after ScaleTypeForCroppedImages).

  STEP E — refactor `tools/idml_to_dsl.py` to invoke each pattern at the corresponding emission point; remove inline logic.

  STEP F — tests (3 unit-test files, each with 3-5 tests + the v2 falzflyer byte-identity test).

  Each pattern unit test has at minimum:
  - Synthetic IDML fixture exercising the positive case (assert matches() True, apply() mutates kwargs).
  - Counter-example (assert matches() False, apply() noop).
  - Pattern metadata (id, description, applies_to).

  WHY: Per ISSUE.md Phase D acceptance "At least 6 patterns extracted from current converter". After Task 13: 5 patterns (J2A, DS-Align, ScaleType, PolyLine, TextFrame-widening, Group-cascade) = 6 patterns. Task 14 adds the 7th (ImageFramePdfSourceForVectors).
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_pattern_polyline_round_caps.py tests/unit/test_pattern_text_frame_height_widening.py tests/unit/test_pattern_group_transform_cascade.py tests/integration/test_v2_falzflyer_build_byte_identity.py -q && python3 -m unittest discover tests/unit -p "test_pattern_polyline_round_caps.py" && python3 -m unittest discover tests/unit -p "test_pattern_text_frame_height_widening.py" && python3 -m unittest discover tests/unit -p "test_pattern_group_transform_cascade.py" && python3 -m unittest discover tests/integration -p "test_v2_falzflyer_build_byte_identity.py"</automated>
  </verify>
  <done>
  - 3 new pattern files exist in `tools/idml_to_dsl_patterns/`.
  - All registered in PATTERNS, documented in INDEX.md.
  - `tools/idml_to_dsl.py` inline logic removed for each.
  - v2 falzflyer byte-identity test still passes.
  - 3 unit-test files + 1 integration test pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 14: NEW pattern image_frame_pdf_source_for_vectors + composite_ai_split</name>
  <files>tools/idml_to_dsl_patterns/image_frame_pdf_source_for_vectors.py, tools/composite_ai_split.py, tools/links_export.py, tools/idml_to_dsl_patterns/__init__.py, tools/idml_to_dsl_patterns/INDEX.md, tests/unit/test_pattern_image_frame_pdf_source.py, tests/unit/test_composite_ai_split.py, tests/integration/test_v2_falzflyer_social_media_icons.py</files>
  <action>
  This task adds the NEW pattern that fixes composite-AI rendering (the v2 falzflyer regression case).

  STEP A — extend `tools/links_export.py` to ALSO emit `.pdf` for `.ai` sources (RESEARCH.md 5.3):

  Update the dispatch entry for `.ai` so it produces BOTH:
  - `<stem>.png` (raster, 600 DPI, transparent) — existing behaviour via `pdftocairo -png`.
  - `<stem>.pdf` (vector passthrough, NEW) — AI files since CS2 ARE valid PDFs; just `shutil.copy(ai_path, target.with_suffix(".pdf"))` OR `pdftocairo -pdf -f 1 -l <last>` for explicit reflow.

  Update `links_export.yml` schema: each `entries[*]` gains a `vector_output: <stem>.pdf` field alongside `output: <stem>.png`.

  STEP B — ship `tools/composite_ai_split.py` (~150-250 LOC):

  CLI:
  ```
  python3 tools/composite_ai_split.py <ai_path> <idml_path> <out_dir> [--slug SLUG]
  ```

  Behaviour:
  1. Open `ai_path` with `pdfplumber`; get page count + bbox.
  2. Walk IDML for ImageFrames referencing this AI (via simple_idml).
  3. For each distinct LocalOffset/LocalScale combination found in the IDML, compute the sub-bbox of the AI that corresponds (the IDML's LocalOffset is in points relative to the AI's full bbox; LocalScale tells us how much of the AI to show).
  4. Emit one PDF per detected icon via `pdftocairo -pdf -x X -y Y -W W -H H -f 1 -l 1` (cropped to the sub-rectangle). Name them deterministically: `<slug>--ai-<basename>--<index>.pdf` (index by descending position so the order is stable).
  5. Emit a manifest `composite_ai_split.yml`:
     ```yaml
     source: <ai_path>
     pages_emitted:
       - {index: 0, out: <slug>--ai-<basename>--0.pdf, bbox_pt: [...], idml_anname: u123}
       - {index: 1, out: <slug>--ai-<basename>--1.pdf, bbox_pt: [...], idml_anname: u124}
     ```

  STEP C — ship `tools/idml_to_dsl_patterns/image_frame_pdf_source_for_vectors.py`:
  ```python
  """When the IDML references an .ai file, emit ImageFrame with image=<vector_output> (PDF)
  not the raster PNG. Preserves vector quality.

  Precondition: links_export.yml entry for the .ai source MUST have a vector_output field
  (introduced in Task 14 STEP A).
  """
  from .base import Pattern
  from pathlib import Path

  class ImageFramePdfSourceForVectors:
      id = "image_frame_pdf_source_for_vectors"
      description = "Emit ImageFrame with PDF source for AI assets (vector preservation)"
      applies_to = "ImageFrame"

      def matches(self, idml_element) -> bool:
          # The IDML element has a LinkResourceURI pointing at an .ai file
          uri = idml_element.get("LinkResourceURI", "")
          return uri.lower().endswith(".ai")

      def apply(self, kwargs: dict, idml_element, context=None) -> None:
          # Read context["links_manifest"] for the AI's vector_output path.
          if not context or "links_manifest" not in context:
              # Precondition not met — emit a TODO comment via kwargs["_todo"]
              kwargs["_todo"] = "image_frame_pdf_source_for_vectors: links_manifest missing"
              return
          ai_basename = Path(idml_element.get("LinkResourceURI")).name
          entry = next((e for e in context["links_manifest"]["entries"]
                        if e["original_basename"] == ai_basename), None)
          if entry and entry.get("vector_output"):
              kwargs["image"] = entry["vector_output"]
          # If no vector_output, leave kwargs["image"] as-is (Task 12's ScaleType pattern + raster path).
  ```

  Register in PATTERNS; document in INDEX.md.

  STEP D — tests:

  1. `tests/unit/test_pattern_image_frame_pdf_source.py`:
     - Synthetic ImageFrame referencing `foo.ai` + manifest with `vector_output: shared/assets/<slug>/foo.pdf`; assert kwargs["image"] == "shared/assets/<slug>/foo.pdf".
     - Same fixture but manifest has no vector_output; assert kwargs gets `_todo` marker, no `image` mutation.
     - ImageFrame referencing `foo.png`; matches() returns False (only `.ai` triggers).

  2. `tests/unit/test_composite_ai_split.py`:
     - Synthetic AI (single-page PDF with 4 colored rectangles at known positions); IDML with 4 ImageFrames at distinct LocalOffsets matching the rectangles; assert 4 PDF pages emitted.
     - Manifest emitted with 4 rows; bbox_pt fields correct.
     - Idempotency: re-run on same inputs produces byte-identical outputs.

  3. `tests/integration/test_v2_falzflyer_social_media_icons.py`:
     - Locate v2 falzflyer's `Social Media Icons weiss.ai` + IDML (skip if originals unavailable).
     - Run `tools/composite_ai_split.py <ai> <idml> <tmp_out_dir>`.
     - Assert 4 per-icon PDFs emitted (Facebook, Instagram, Twitter/X, third one — whatever the actual count is on the strip).
     - Assert manifest fields populated.
     - Run the converter end-to-end and assert build.py emits ImageFrame entries with PDF paths (not PNG) for the social-media icons.

  WHY: Per ISSUE.md Phase D acceptance "New pattern (e.g. image_frame_pdf_source_for_vectors) demonstrates the extensibility: matches AI-source images, emits PDF as ImageFrame source, regression test on v2 falzflyer's social-media icons" + RESEARCH.md highest-leverage mitigation 2 ("composite-AI splitting in Phase E, not deferred").
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_pattern_image_frame_pdf_source.py tests/unit/test_composite_ai_split.py tests/integration/test_v2_falzflyer_social_media_icons.py -q && python3 -m unittest discover tests/unit -p "test_pattern_image_frame_pdf_source.py" && python3 -m unittest discover tests/unit -p "test_composite_ai_split.py" && python3 -m unittest discover tests/integration -p "test_v2_falzflyer_social_media_icons.py"</automated>
  </verify>
  <done>
  - `tools/links_export.py` dispatch emits both `.png` + `.pdf` for `.ai` sources.
  - `tools/composite_ai_split.py` exists with CLI + manifest emission.
  - `tools/idml_to_dsl_patterns/image_frame_pdf_source_for_vectors.py` registered + documented.
  - v2 falzflyer's social-media-icons-weiss.ai produces 4 per-icon PDFs.
  - Converter emits ImageFrame entries with PDF paths for the social-media icons.
  - 3 unit tests + 2 integration tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<!-- ============================================================
     P3 — Skill + inject.yml + reconcile + v2 migration
     Tasks 15-18
     ============================================================ -->

<task type="auto">
  <name>Task 15: .claude/skills/idml-import SKILL.md + progressive-disclosure files</name>
  <files>.claude/skills/idml-import/SKILL.md, .claude/skills/idml-import/classification.md, .claude/skills/idml-import/pattern_library.md, .claude/skills/idml-import/tolerance_protocol.md, .claude/skills/idml-import/inject_protocol.md, tests/unit/test_skill_idml_import_structure.py</files>
  <action>
  Ship the `/idml-import` skill, modelled on `.claude/skills/experiments/SKILL.md` (300 LOC).

  STEP A — `.claude/skills/idml-import/SKILL.md` (≤500 LOC):

  Frontmatter (YAML, per Anthropic skill-authoring best practices):
  ```yaml
  ---
  name: idml-import
  description: |
    Drives `bin/idml-import` end-to-end: extract assets, scaffold, convert,
    audit, classify drift, fix converter, re-emit. Enforces P1-P10 SOP
    (no engine floor, converter-first remediation, no silent tolerance growth).
  verb_routes:
    /idml-import: main
    /idml-import-review: review_only
    /idml-import-classify: classify_only
  ---
  ```

  Body sections:
  1. **When invoked as /idml-import**: verb dispatch table + per-verb numbered steps.
  2. **Pre-flight checks** (machine-checkable, calling bin/idml-import's pre-flight): tool availability, IDML structure, baseline.pdf, brand fonts.
  3. **Step 1: Asset extraction** (`bin/idml-import --scaffold-only`).
  4. **Step 2: First-render audit** (read import_report.md).
  5. **Step 3: Classification** (read convergence-review output; see `classification.md`).
  6. **Step 4: Converter-first remediation loop** (extend pattern library; see `pattern_library.md`).
  7. **Step 5: Hand-patch only as last resort** (write inject.yml entry; see `inject_protocol.md`).
  8. **Step 6: Tolerance growth requires user confirmation** (see `tolerance_protocol.md`).
  9. **Step 7: Termination** (preflight.ok=true OR `--accept-residual` for human-review/authoring-bug).
  10. **Banned phrases**: "engine floor", "engine ceiling", "rendering floor", "good enough", "accept the drift", "cap the converter", "this is just how it is". Skill REFUSES to use these and refers to `tools/sop_lint.py` for the mechanical guarantee.
  11. **SOP commitments** (P1-P10 restated verbatim from ISSUE.md, as a banner the skill re-reads at every iteration boundary per RESEARCH.md 1.2).

  STEP B — `.claude/skills/idml-import/classification.md` (~150 LOC):
  - P5 detail: 4 categories + the `minor` filter.
  - Decision rules (the table from Task 5's classification heuristics).
  - When to bias toward `human-review`.
  - The `--idml` argument for IDML XPath introspection (needed for `authoring-bug` decisions).

  STEP C — `.claude/skills/idml-import/pattern_library.md` (~150 LOC):
  - How to add a new pattern: copy template, add `matches()` + `apply()`, register in `__init__.py::PATTERNS`, add row to INDEX.md, write unit test, byte-identity test.
  - Pattern ordering: order matters, document depends_on, run byte-identity after each addition.
  - Anti-pattern: "added a pattern that matches nothing" (RESEARCH.md 3.3): the test MUST assert positive case fires.

  STEP D — `.claude/skills/idml-import/tolerance_protocol.md` (~100 LOC):
  - P4 enforcement: skill REFUSES to add `brand_overrides` / `non_ci_styles` / etc. without explicit user confirmation + `reason` + TOLERANCE_LOG.md row.
  - The flow: user types "yes, add brand:X with reason Y", skill writes the TOLERANCE_LOG row first, then mutates meta.yml. `tools/check_overrides_growth.py` gates the commit.
  - User-facing wording for the confirmation prompt.

  STEP E — `.claude/skills/idml-import/inject_protocol.md` (~100 LOC):
  - P3 + P5 reconcile workflow: when a hand-patch is the only path, write the `inject.yml` entry, run `tools/reconcile_build_py.py`, verify byte-stability.
  - When to remove an inject entry: redundancy detection (`reconcile_build_py.py` warns when an inject's `set:` matches what the converter now emits).
  - Cross-reference: open a follow-up issue with the converter-extension TODO.

  STEP F — tests in `tests/unit/test_skill_idml_import_structure.py`:
  - SKILL.md exists with valid YAML frontmatter (parseable by PyYAML).
  - Frontmatter has `name`, `description`, `verb_routes`.
  - 4 progressive-disclosure files exist: classification.md, pattern_library.md, tolerance_protocol.md, inject_protocol.md.
  - SKILL.md contains the SOP commitments (P1-P10 references).
  - Banned-phrases section exists in SKILL.md.
  - SKILL.md body is ≤500 LOC.
  - SKILL.md does NOT contain any of the banned phrases (verify via `tools/sop_lint.py` passing on the new files).

  WHY: Per ISSUE.md Phase C acceptance. Per RESEARCH.md 1.1/1.2/6.2: the skill is the recipe; tools enforce correctness; progressive-disclosure files are per Anthropic best practices.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_skill_idml_import_structure.py -q && python3 -m unittest discover tests/unit -p "test_skill_idml_import_structure.py" && python3 tools/sop_lint.py && test -f .claude/skills/idml-import/SKILL.md && test -f .claude/skills/idml-import/classification.md && test -f .claude/skills/idml-import/pattern_library.md && test -f .claude/skills/idml-import/tolerance_protocol.md && test -f .claude/skills/idml-import/inject_protocol.md && [ $(wc -l < .claude/skills/idml-import/SKILL.md) -le 500 ]</automated>
  </verify>
  <done>
  - `.claude/skills/idml-import/SKILL.md` exists, ≤500 LOC, with valid YAML frontmatter + 11 body sections.
  - 4 progressive-disclosure files exist with the spec'd content.
  - Banned-phrases section restates SOP commitments.
  - `tools/sop_lint.py` passes on the new files.
  - 7 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 16: inject.schema.yaml + tools/reconcile_build_py.py</name>
  <files>shared/inject.schema.yaml, tools/reconcile_build_py.py, tests/unit/test_reconcile_build_py.py, tests/unit/test_inject_schema.py</files>
  <action>
  STEP A — ship `shared/inject.schema.yaml` (jsonschema Draft 2020-12, per RESEARCH.md):

  ```yaml
  $schema: "https://json-schema.org/draft/2020-12/schema"
  $id: "https://gruene.at/schemas/inject.yaml"
  title: "inject.yml — declarative hand-patches for converter-emitted build.py"
  type: object
  required: [hand_patches]
  properties:
    hand_patches:
      type: array
      items:
        type: object
        required: [target, classification, reason]
        properties:
          target:
            type: object
            description: "Structured selector — element type + anname (per RESEARCH.md, NOT CSS)."
            required: [element, anname]
            properties:
              element:
                type: string
                enum: [TextFrame, ImageFrame, PolyLine, Group, ParaStyle, DefaultStyle, SLA]
              anname:
                type: string
                pattern: "^[uU][0-9a-fA-F]+$|^[a-zA-Z_][a-zA-Z0-9_]*$"
          field:
            type: string
            description: "Attribute to mutate (e.g. scale_type, ALIGN, default_style_attrs.ALIGN, y_mm)."
          set:
            description: "Absolute value to set. Mutually exclusive with delta."
          delta:
            description: "Additive offset to apply (e.g. y_delta_pt: +5.34). Mutually exclusive with set."
          reason:
            type: string
            minLength: 10
            description: "Why this hand-patch is needed. Cites engine-bug ID or authoring choice."
          classification:
            type: string
            enum: [converter-bug, scribus-engine-bug, authoring-bug, human-review]
          follow_up_issue:
            type: [string, "null"]
            description: "Issue number tracking the converter-fix that would obsolete this entry."
        oneOf:
          - required: [set]
          - required: [delta]
  ```

  STEP B — ship `tools/reconcile_build_py.py` (~300-500 LOC):

  CLI:
  ```
  python3 tools/reconcile_build_py.py <slug> [--check] [--quiet]
  ```

  Behaviour:
  1. Validate `templates/<slug>/inject.yml` against `shared/inject.schema.yaml` using `jsonschema.Draft202012Validator` (idiom from `tools/experiment_envelope.py:170-185`).
  2. Read `templates/<slug>/build.py.generated` (the converter's verbatim emission).
  3. Apply each `hand_patches[*]` entry in LIST order (RESEARCH.md 4.3: order matters; last-wins on conflict):
     - Resolve `target.anname` via `simple_idml.get_spread_object_by_name()` OR via in-build.py grep (the build.py uses `anname=` kwarg in every emitter call; locate by literal substring).
     - If `set:` is provided, replace the field's value with the new value.
     - If `delta:` is provided, parse the current numeric value, add the delta, write back.
     - Insert an inline comment IMMEDIATELY before the mutated kwarg: `# P5/inject (from inject.yml line N): <reason>` where `N` is the line in `inject.yml` and `<reason>` is the truncated first line of `reason`.
  4. Write the result to `templates/<slug>/build.py`.
  5. Redundancy detection: for each `hand_patches[*].set:`, compare against the corresponding kwarg's value in `build.py.generated`. If equal, emit a warning to stderr: `"inject entry at line N is redundant; the converter now emits the same value. Consider removing it."`
  6. With `--check`: do NOT write; exit 0 if `build.py` matches the reconciled output (byte-equal), 1 otherwise. Used by CI.

  STEP C — tests:

  1. `tests/unit/test_inject_schema.py`:
     - Valid inject.yml passes validation.
     - Missing `target` => ValidationError.
     - Both `set:` and `delta:` together => oneOf violation.
     - `reason` < 10 chars => ValidationError.
     - Unknown `classification` enum => ValidationError.

  2. `tests/unit/test_reconcile_build_py.py`:
     - Fixture: a synthetic `build.py.generated` + `inject.yml` with 1 entry; assert reconciled build.py contains the inline comment + mutated kwarg.
     - Byte-stability: reconcile twice, diff outputs, assert no diff.
     - Redundancy: inject entry's `set:` matches build.py.generated's value; assert warning emitted.
     - `delta:` mode: numeric y_mm value + delta=+1.884; assert result is sum.
     - Order: 2 entries targeting same field; assert last-wins.
     - `--check` mode: when build.py matches reconciled output, exit 0; otherwise exit 1.

  WHY: Per ISSUE.md Phase F acceptance. Per RESEARCH.md 4.1/4.2/4.3 mitigations: byte-stability, delta support for y-coord bumps, deterministic ordering.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_inject_schema.py tests/unit/test_reconcile_build_py.py -q && python3 -m unittest discover tests/unit -p "test_inject_schema.py" && python3 -m unittest discover tests/unit -p "test_reconcile_build_py.py" && python3 -c "import yaml, jsonschema; s = yaml.safe_load(open('shared/inject.schema.yaml')); jsonschema.Draft202012Validator.check_schema(s)"</automated>
  </verify>
  <done>
  - `shared/inject.schema.yaml` is valid Draft 2020-12.
  - `tools/reconcile_build_py.py` applies hand_patches in deterministic order with `set:` + `delta:` support.
  - Inline `# P5/inject (from inject.yml line N): <reason>` comments emitted.
  - Byte-stability test passes (reconcile twice => identical output).
  - Redundancy warnings emitted when inject's set matches generated value.
  - `--check` mode supported for CI.
  - 11 unit tests pass under BOTH pytest and unittest discover.
  </done>
</task>

<task type="auto">
  <name>Task 17: Migrate v2 falzflyer's 14 P5/inject comments to inject.yml</name>
  <files>templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py.generated, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/TOLERANCE_LOG.md, tests/integration/test_v2_falzflyer_inject_migration.py</files>
  <action>
  STEP A — extract the 14 P5/inject comments from the current v2 falzflyer build.py:

  1. Read `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py`.
  2. Grep for `# P5/inject` (expect 14 hits per RESEARCH.md, near lines 70, 117, 124, 157, 170, 180, 376, 402, 493, 504, 621, 752 + 2 more).
  3. For each hit, determine:
     - target element type + anname (from the surrounding emitter call)
     - field being mutated (e.g. `ALIGN`, `LINESP`, `default_style_attrs.ALIGN`, `scale_type`, `y_mm`)
     - whether it's `set:` (absolute override) or `delta:` (y-coord bump per RESEARCH.md 4.2: 4 of 14 entries are FirstBaselineOffset compensation deltas)
     - reason text (mine from the existing comment; expand if cryptic)
     - classification per P5 (scribus-engine-bug / converter-bug / authoring-bug)

  STEP B — write `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml`:

  ```yaml
  # Hand-patches for kandidat-falzflyer-din-lang-gruenes-cover-v2.
  # Migrated from inline # P5/inject comments in build.py per issue #38.
  # Validated against shared/inject.schema.yaml.
  hand_patches:
    - target: {element: SLA, anname: document}
      field: bleeds
      set: 0
      reason: "Authoring choice: v2 baseline.pdf was exported with bleed=0; converter would faithfully reproduce, but template.sla needs explicit 0 to match."
      classification: authoring-bug
      follow_up_issue: null

    - target: {element: ParaStyle, anname: idml/<style>}
      field: ALIGN
      set: 0
      reason: "Backport 11 edge case (converter-bug): ParaStyle Justification not propagating; converter fix tracked in issue #N. Remove this entry after fix lands."
      classification: converter-bug
      follow_up_issue: null

    # ... 12 more entries, one per P5/inject comment ...

    - target: {element: TextFrame, anname: u376}
      field: y_mm
      delta: +1.884   # +5.34pt / 2.834645669
      reason: "Scribus FirstBaselineOffset rendering differs from InDesign; y-coord bumped to match baseline.pdf. Tracking upstream Scribus bug."
      classification: scribus-engine-bug
      follow_up_issue: null
    # ...
  ```

  STEP C — split current build.py into generated + reconciled:
  1. Snapshot the CURRENT build.py as `templates/<slug>/build.py.generated` (the converter's verbatim emission — verify by re-running `tools/idml_to_dsl.py` and asserting byte-identity to the snapshot WITH the inject comments stripped).
  2. Run `python3 tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2` to produce the new `build.py`.
  3. Diff the new build.py against the original; expected diff: identical functional content, only comment format differs (now says `# P5/inject (from inject.yml line N): <reason>` instead of free-form).

  STEP D — create `templates/<slug>/TOLERANCE_LOG.md`:
  Document the 5 existing brand_overrides in meta.yml (from RESEARCH.md):
  ```markdown
  # Tolerance Log — kandidat-falzflyer-din-lang-gruenes-cover-v2

  ## brand:line_spacing_0.9 — 2026-05-13 — migrated from issue #35
  Reason: line spacing override for non-CI ParaStyles emitted by IDML.
  Backport-9 + E2 audit may obsolete this.

  ## brand:font_family — 2026-05-13 — migrated from issue #35
  Reason: 2 frames fall back to Times Roman due to converter font-resolution gap.
  Follow-up: extend converter to resolve font names from IDML's <Fonts> section.

  ... (3 more) ...
  ```

  STEP E — integration test `tests/integration/test_v2_falzflyer_inject_migration.py`:

  1. Validate inject.yml against `shared/inject.schema.yaml`.
  2. Assert `len(hand_patches) == 14`.
  3. Run `tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2 --check`; assert exit 0 (build.py matches reconciled output).
  4. Run `bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit-strict` (skip if brand fonts unavailable in CI); assert the SLA hash in `meta.yml::previews_for_sla` is UNCHANGED — this is the canonical regression check per RESEARCH.md 4.1 ("acceptance test is 'render => SLA hash unchanged'").
  5. Run `tools/check_overrides_growth.py --base-ref origin/main`; assert exit 0 (TOLERANCE_LOG.md row matches each brand_override entry).

  WHY: Per ISSUE.md Phase F acceptance "v2 falzflyer template migrated: all current `# P5/inject` patches moved into `inject.yml`."
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/integration/test_v2_falzflyer_inject_migration.py -q && python3 -m unittest discover tests/integration -p "test_v2_falzflyer_inject_migration.py" && python3 tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2 --check && python3 tools/sop_lint.py</automated>
  </verify>
  <done>
  - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml` exists with 14 hand_patches entries.
  - `templates/<slug>/TOLERANCE_LOG.md` documents the 5 existing brand_overrides.
  - `tools/reconcile_build_py.py --check` passes (build.py matches reconciled output).
  - The 4 y-coord-bump entries use `delta:` field; the rest use `set:`.
  - Integration test passes under BOTH pytest and unittest discover.
  - SLA hash in `meta.yml::previews_for_sla` unchanged after migration.
  </done>
</task>

<task type="auto">
  <name>Task 18: CI lint_inject_consistency.py + pre-commit wiring + GitHub Actions</name>
  <files>tools/lint_inject_consistency.py, .pre-commit-config.yaml, .github/workflows/ci.yml, tests/unit/test_lint_inject_consistency.py</files>
  <action>
  STEP A — ship `tools/lint_inject_consistency.py`:

  Behaviour: For every template that has both `build.py` AND `inject.yml`:
  1. Parse `build.py` for all `# P5/inject (from inject.yml line N): <reason>` comments. Build a set of `(slug, inject_line_number)` tuples.
  2. Parse `inject.yml::hand_patches` and build a set of `(slug, line_number)` tuples for each entry.
  3. Assert 1:1 mapping:
     - Every `# P5/inject` comment in build.py has a matching inject.yml entry => exit 1 if missing.
     - Every inject.yml entry produced a matching build.py inline comment => exit 1 if missing.
  4. Exit 0 on clean match across all templates.

  CLI:
  ```
  python3 tools/lint_inject_consistency.py [--template SLUG]
  ```
  Default: walk every `templates/*/` directory with both files present.

  STEP B — wire into pre-commit + CI:

  1. `.pre-commit-config.yaml` — read existing config if present. Add hooks (or create the file if not present):
     ```yaml
     repos:
       - repo: local
         hooks:
           - id: sop-lint
             name: SOP Lint — ban engine-floor phrase
             entry: python3 tools/sop_lint.py
             language: system
             pass_filenames: false
           - id: check-overrides-growth
             name: Check overrides growth — require TOLERANCE_LOG row
             entry: python3 tools/check_overrides_growth.py --base-ref origin/main
             language: system
             pass_filenames: false
           - id: lint-inject-consistency
             name: Lint inject.yml ↔ build.py consistency
             entry: python3 tools/lint_inject_consistency.py
             language: system
             pass_filenames: false
           - id: reconcile-build-py-check
             name: Reconcile build.py — check mode (every template)
             entry: bash -c 'for d in templates/*/; do test -f "$d/inject.yml" && python3 tools/reconcile_build_py.py "$(basename $d)" --check || true; done; exit 0'
             language: system
             pass_filenames: false
     ```

  2. `.github/workflows/ci.yml` — read existing if present. Add a job step (after the existing pytest step):
     ```yaml
     - name: SOP enforcement
       run: |
         python3 tools/sop_lint.py
         python3 tools/check_overrides_growth.py --base-ref origin/main
         python3 tools/lint_inject_consistency.py
         for d in templates/*/; do
           [ -f "$d/inject.yml" ] && python3 tools/reconcile_build_py.py "$(basename "$d")" --check
         done
     ```

  STEP C — tests in `tests/unit/test_lint_inject_consistency.py`:
  - Test 1: synthetic build.py with 2 `# P5/inject` comments + inject.yml with 2 hand_patches; assert exit 0.
  - Test 2: build.py has 2 comments, inject.yml has 1 hand_patch; assert exit 1 with stderr identifying the missing inject entry.
  - Test 3: build.py has 1 comment, inject.yml has 2 hand_patches; assert exit 1 with stderr identifying the missing build.py comment.
  - Test 4: build.py has no comments, inject.yml does not exist; assert exit 0 (no inject => no consistency required).
  - Test 5: `--template <slug>` flag restricts the check to one template.

  WHY: Per ISSUE.md Phase F acceptance "CI lint enforces 1:1 mapping between `# P5/inject` comments in build.py and inject.yml entries" + RESEARCH.md 1.1 + 4.1 mitigations.
  </action>
  <verify>
  <automated>cd /workspace/.worktrees/38-idml-import-skill-end-to-end-converter-driven-convergence && pytest tests/unit/test_lint_inject_consistency.py -q && python3 -m unittest discover tests/unit -p "test_lint_inject_consistency.py" && python3 tools/lint_inject_consistency.py && test -f .pre-commit-config.yaml && grep -q "sop-lint" .pre-commit-config.yaml && grep -q "lint-inject-consistency" .pre-commit-config.yaml && test -f .github/workflows/ci.yml && grep -q "sop_lint.py" .github/workflows/ci.yml</automated>
  </verify>
  <done>
  - `tools/lint_inject_consistency.py` exists; enforces 1:1 mapping.
  - `.pre-commit-config.yaml` has hooks for sop-lint, check-overrides-growth, lint-inject-consistency, reconcile-build-py-check.
  - `.github/workflows/ci.yml` runs the same 4 checks as a CI step.
  - 5 unit tests pass under BOTH pytest and unittest discover.
  - All 4 SOP checks pass on the current tree (i.e. tasks 1, 3, 16, 17 produced a consistent state).
  </done>
</task>

</tasks>

<verification>
After all 18 tasks, run the following final checks (all must pass):

1. **All audits remain green on the existing 9 templates** (ISSUE.md cross-cutting acceptance):
   ```
   for slug in $(ls templates/); do
     [ -f "templates/$slug/baseline.pdf" ] && bin/render-gallery "$slug" --audit-strict || true
   done
   ```
   Skip in CI if brand fonts unavailable; verify on dev container.

2. **`preflight.yml::ok=true` for v2 falzflyer template** (ISSUE.md cross-cutting):
   ```
   bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit-strict
   yq -r '.ok' build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/preflight.yml
   # Must print: true
   ```
   (Requires Task 14's composite-AI pattern + Task 17's inject.yml migration both shipped.)

3. **The phrase "engine floor" appears nowhere in the codebase** (ISSUE.md cross-cutting):
   ```
   git grep -iE "engine[_ ]floor|engine[_ ]ceiling|rendering[_ ]floor" -- 'templates/' 'tools/' 'bin/' '.claude/skills/' 'docs/' 'README*' && exit 1 || exit 0
   ```

4. **`bin/idml-import` documented in README.md** (ISSUE.md cross-cutting):
   ```
   grep -q "bin/idml-import" README.md
   ```

5. **Full pytest suite passes** (both runners):
   ```
   pytest tests/ -q
   python3 -m unittest discover tests -p "test_*.py"
   ```

6. **All 4 SOP gates pass**:
   ```
   python3 tools/sop_lint.py
   python3 tools/check_overrides_growth.py --base-ref origin/main
   python3 tools/lint_inject_consistency.py
   for d in templates/*/; do
     [ -f "$d/inject.yml" ] && python3 tools/reconcile_build_py.py "$(basename "$d")" --check
   done
   ```

7. **Pattern library has at least 6 patterns + INDEX.md complete**:
   ```
   python3 -c "from tools.idml_to_dsl_patterns import PATTERNS; assert len(PATTERNS) >= 6"
   ```

8. **Skill file is ≤500 LOC, has frontmatter, has 4 progressive-disclosure files**:
   ```
   test -f .claude/skills/idml-import/SKILL.md
   [ $(wc -l < .claude/skills/idml-import/SKILL.md) -le 500 ]
   for f in classification.md pattern_library.md tolerance_protocol.md inject_protocol.md; do
     test -f ".claude/skills/idml-import/$f"
   done
   ```
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria.

**Phase A — `bin/idml-import` end-to-end** (Tasks 4 + 6 + 7):
- [ ] `bin/idml-import /tmp/foo.idml` processes a single file end-to-end (Task 4 + 7).
- [ ] `bin/idml-import /tmp/incoming/` processes every `.idml` in directory (Task 4).
- [ ] Exits 0 only when `preflight.ok=true` OR `--accept-residual` covers all remaining issues (Task 4 exit-code semantics).
- [ ] Writes `build/<slug>/iteration.jsonl` for every render cycle (Task 6).
- [ ] Writes `build/<slug>/import_report.md` final summary (Task 4 step 12).
- [ ] `--scaffold-only` mode stops cleanly after first audit (Task 4 step 10 + Task 7 test 3).
- [ ] `--max-iterations N` halts the loop and reports unresolved issues (Task 4 + Task 6 regression guard).

**Phase B — `bin/convergence-review`** (Task 5):
- [ ] Reads all 11 audit outputs from `build/validation/<slug>/`.
- [ ] Emits per-issue classification (4 categories per P5).
- [ ] Sorts issues by estimated drift-drop leverage.
- [ ] Each issue has a `suggested_action` field with concrete next step.
- [ ] Each `converter-bug` issue has a `converter_path` with file:line.
- [ ] Each `converter-bug` issue has a `regression_test_path` for a new or extended test.
- [ ] `--format json` emits machine-readable output for the skill.

**Phase C — `/idml-import` skill** (Task 15):
- [ ] Skill file at `.claude/skills/idml-import/SKILL.md` with valid frontmatter.
- [ ] Workflow enforces 8 steps per ISSUE.md scope.
- [ ] Skill refuses to add `brand_overrides` without user confirmation (`tolerance_protocol.md`).
- [ ] Skill refuses to use the phrase "engine floor" (banned-phrases section + `tools/sop_lint.py` mechanical gate from Task 1).
- [ ] Skill enforces "regression test before converter fix" rule (`pattern_library.md`).
- [ ] Skill works for multi-IDML batches (Task 4 driver supports this).

**Phase D — Pattern library** (Tasks 9-14):
- [ ] At least 6 patterns extracted from current converter into `tools/idml_to_dsl_patterns/` (Tasks 10-14 ship 6).
- [ ] Pattern registry in `__init__.py` (Task 9).
- [ ] Every pattern has a unit test with synthetic IDML fixture (Tasks 10-14).
- [ ] `tools/idml_to_dsl_patterns/INDEX.md` documents each pattern (Task 9 scaffold; populated in 10-14).
- [ ] `tools/idml_to_dsl.py` iterates patterns at the right emission points; behavior identical to current converter on v2 falzflyer template (Task 10's byte-identity test, re-run in 11-14).
- [ ] New pattern `image_frame_pdf_source_for_vectors` demonstrates extensibility (Task 14).

**Phase E — Asset extraction completeness** (Task 2):
- [ ] `tools/asset_extraction_audit.py` exists, wired into `_run_audit` BEFORE A1.
- [ ] Detects missing `Links/` files.
- [ ] Detects composite-AI files; refuses to proceed without per-icon extraction (Task 14's splitter is the resolution).
- [ ] Emits `asset_audit.yml` with structured shape.
- [ ] Regression test: synthetic IDML with missing link → audit ok=false.

**Phase F — `inject.yml` + reconcile** (Tasks 16-18):
- [ ] `tools/reconcile_build_py.py` exists (Task 16).
- [ ] `templates/<slug>/inject.yml` schema validated via `jsonschema` (Task 16 STEP A).
- [ ] Reconcile applies entries in deterministic order; output is byte-stable across runs (Task 16 STEP B step 3).
- [ ] CI lint enforces 1:1 mapping between `# P5/inject` comments in `build.py` and `inject.yml` entries (Task 18).
- [ ] Redundancy detection warns when an inject entry is no longer necessary (Task 16 STEP B step 5).
- [ ] v2 falzflyer template migrated (Task 17).

**Cross-cutting**:
- [ ] All audits remain green on the existing 9 templates after this issue lands (verification block 1).
- [ ] `preflight.yml::ok=true` for v2 falzflyer template (verification block 2; requires Tasks 14 + 17).
- [ ] The phrase "engine floor" appears nowhere in the codebase (Task 1 + verification block 3).
- [ ] `bin/idml-import` is the documented entry point in `README.md` (Task 8 + verification block 4).
</success_criteria>

<deliverables>
**P1 sub-phase (tasks 1-8)** — driver + classifier + asset audit + machine enforcement:
- `tools/region_color_audit.py` (rename), `tools/sop_lint.py`, `tools/check_overrides_growth.py`
- `tools/asset_extraction_audit.py` + `_run_audit` wiring
- `bin/idml-import`, `tools/idml_import_driver.py`
- `bin/convergence-review`, `tools/convergence_review.py`
- iteration.jsonl schema + log writer + regression guard
- End-to-end integration test on v2 falzflyer
- README.md + docs/idml-import-workflow.md

**P2 sub-phase (tasks 9-14)** — pattern library refactor:
- `tools/idml_to_dsl_patterns/` package: `__init__.py`, `base.py`, `INDEX.md`
- 5 extracted patterns: justification_to_align, default_style_align_inheritance, scale_type_for_cropped_images, polyline_round_caps_joins, text_frame_height_widening, group_transform_cascade
- 1 new pattern + supporting tool: image_frame_pdf_source_for_vectors + composite_ai_split
- v2 falzflyer build.py byte-identity test re-run after each extraction
- v2 falzflyer social-media-icons regression test

**P3 sub-phase (tasks 15-18)** — skill + inject.yml + reconcile + v2 migration:
- `.claude/skills/idml-import/SKILL.md` + 4 progressive-disclosure files
- `shared/inject.schema.yaml` + `tools/reconcile_build_py.py`
- v2 falzflyer migration: 14 P5/inject comments to inject.yml + TOLERANCE_LOG.md
- `tools/lint_inject_consistency.py` + `.pre-commit-config.yaml` + `.github/workflows/ci.yml`

**Test count**: ~50+ unit tests + ~6 integration tests across tasks. Every task verifies via pytest AND unittest discover (dual-runner gate per planner instructions).

**Commit count**: ~18-22 commits (one per task minimum; Task 1 may split into 2; Task 17 splits into 3-4 for per-inject migration per RESEARCH.md 4.1).
</deliverables>
