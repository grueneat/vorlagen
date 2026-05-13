# Research — Issue #38: IDML import skill — end-to-end converter-driven convergence

**Date:** 2026-05-13
**Confidence:** HIGH on codebase state + library choices + skill patterns; MEDIUM on classifier heuristics + grid sizing; LOW on composite-AI splitting correctness (no prior art).

## Summary

The user's directive: drop one or many `.idml` files into the workspace, run one command, get fully imported templates that converge against `baseline.pdf` without falling into the "engine floor" trap. The converter must be extended on every novel pattern; no silent tolerance growth.

Most of the underlying machinery already exists on main (post #76, #77): the converter (`tools/idml_to_dsl.py` with Backports 9/10/11), the asset extractor (`tools/links_export.py`), 11 audits feeding `preflight.yml`, the bbox extractor with `drift_type` classification. Issue 38 wraps these into a **single one-command driver** with a **SOP-enforcing skill** and **mechanically-enforceable rules** that prevent the failure modes #35 hit.

Three sub-phases for execute:

1. **P1 — Driver + classifier + asset audit + machine enforcement** (Phases A + B + E + the machine-checked SOP hooks). User-visible: `bin/idml-import <path>` works end-to-end on simple IDMLs. The asset audit detects composite-AI files and refuses to proceed silently. A pre-commit / CI hook bans "engine floor" and gates `brand_overrides` additions.
2. **P2 — Pattern library refactor** (Phase D). Extract 6+ inline backports from `tools/idml_to_dsl.py` into `tools/idml_to_dsl_patterns/<name>.py` with regression tests. Adds the `image_frame_pdf_source_for_vectors` pattern (vector AI as ImageFrame source, not raster PNG) which fixes the composite-AI case via per-page PDF references rather than hand-cropped rasters.
3. **P3 — Skill + inject.yml + reconcile** (Phases C + F). Ships `.claude/skills/idml-import/SKILL.md` with progressive disclosure, the `inject.yml` overlay schema + `tools/reconcile_build_py.py`, and migrates v2-falzflyer's 14 `# P5/inject` comments into `inject.yml`.

## Recommendation (primary)

**Sub-phase 1 ships first** because everything else depends on it: the driver orchestrates, the classifier produces the data, and the machine enforcement (Hook 1) makes the SOP unbypassable. Within P1, the asset audit must come FIRST in `_run_audit` (before A1 inventory) so composite-AI files fail-fast.

**Composite-AI handling** (P7 in ISSUE.md): the user's directive is "always extend the converter when something new shows up." The composite-AI splitting MUST be part of this issue, not deferred. The path: detect composite (Phase E audit), split via `pdftocairo -pdf -f N -l N` to per-page single-page PDFs, emit ImageFrame references with `image=<page>.pdf` (vector). Test case: v2-falzflyer's `social-media-icons-weiss.ai` (1-page wide strip; detected by aspect-ratio + multi-ImageFrame-LocalOffset).

**SOP enforcement** (P2, P4): prose-only rules failed in #35 (two Sonnet executors declared engine floor anyway). Replace prose with machine checks:
- `tools/sop_lint.py` (new): grep-bans "engine floor" / "engine_floor" / synonyms ("engine ceiling", "rendering floor"); fails CI.
- `tools/check_overrides_growth.py` (new): diffs `meta.yml::brand_overrides|ci_overrides` between branches; requires matching `inject.yml::reason` or `TOLERANCE_LOG.md` row.
- Pre-commit hook calls both.

**Critical bug to fix BEFORE adding the grep-CI check**: `tools/region_color_audit.py:6` and `:245` already contain "engine floor". Rename to `icc_drift_uniform_small`.

## User Constraints (from prior conversation + ISSUE.md)

- **P1 — `baseline.pdf` is the only success criterion.** Never accept drift as inherent.
- **P2 — No engine floor.** Banned phrase, mechanically enforced.
- **P3 — Converter-first remediation.** Hand-patches are last resort, tracked in `inject.yml`.
- **P4 — No silent tolerance growth.** Skill refuses to add `brand_overrides` without user confirmation + `reason` + `TOLERANCE_LOG.md` row.
- **P5 — Every drift classified before action.** Categories: `converter-bug` / `scribus-engine-bug` / `authoring-bug` / `human-review`.
- **P6 — One-command end-to-end.** `bin/idml-import <path>` drives the loop.
- **P7 — Asset extraction completeness is a hard precondition.** Composite-AI splitting is IN scope.
- **P8 — `preflight.yml::ok` is the only gate.** No bypass except `--accept-residual` for human-review/authoring-bug.
- **P9 — Pattern library, not ad-hoc converter edits.**
- **P10 — Iteration log is the audit trail.**

`feedback_no_claude_attribution.md`: no "claude" in commits/code/files.

## Codebase Analysis

See [research/codebase.md](research/codebase.md) for full interfaces.

### Build matrix

```
<interfaces>

# EXISTING (reuse, don't rewrite):
tools/idml_to_dsl.py             # 3360 LOC; Backports 9/10/11/PolyLine shipped
tools/links_export.py            # 481 LOC; dispatch for .ai/.psd/.jpg/.png
tools/render_pipeline.py         # 1444 LOC; _run_audit + _build_preflight
tools/idml_meta_stub.py          # 92 LOC; slot block emitter (paste-into-meta.yml)
tools/sla_lib/builder/brand_constraints.py    # BRAND_CONSTRAINTS registry pattern (line 1525)
tools/sla_lib/builder/meta_schema.py          # load_brand_overrides loader pattern
tools/sla_lib/builder/library.py              # inject_into_frame (existing overlay primitive)
.claude/skills/experiments/SKILL.md           # 300 LOC; canonical skill model

# Audit outputs in build/validation/<slug>/ (all 11 wired into _run_audit):
preflight.yml, inventory.yml, text_audit.yml, image_audit.yml,
font_audit.yml, text_render_audit.yml, text_position_audit.yml,
run_style_audit.yml, per_element_drift.yml, region_color_audit.yml,
line_spacing_audit.yml, visual_diff_regions.yml, diff_bboxes.json,
visual_diff.json

# NEW (this issue):
bin/idml-import                              # 15-line shim → tools/idml_import_driver.py
tools/idml_import_driver.py                  # Phase A — orchestrator + convergence loop
bin/convergence-review                       # 15-line shim → tools/convergence_review.py
tools/convergence_review.py                  # Phase B — classifier + leverage scorer
.claude/skills/idml-import/SKILL.md          # Phase C — SOP body (≤500 LOC)
.claude/skills/idml-import/classification.md # Phase C — P5 detail
.claude/skills/idml-import/pattern_library.md # Phase C — how to add a pattern
.claude/skills/idml-import/tolerance_protocol.md  # Phase C — P4 confirmation gate
.claude/skills/idml-import/inject_protocol.md    # Phase C — P5/inject reconcile
tools/idml_to_dsl_patterns/__init__.py       # Phase D — ordered PATTERNS list
tools/idml_to_dsl_patterns/{6+ patterns}.py  # Phase D — extracted Backports + new
tools/idml_to_dsl_patterns/INDEX.md          # Phase D — pattern catalogue
tools/idml_to_dsl_patterns/image_frame_pdf_source_for_vectors.py  # NEW pattern
tools/composite_ai_split.py                  # Phase E — per-page AI extraction
tools/asset_extraction_audit.py              # Phase E — completeness gate
tools/sop_lint.py                            # Hooks — bans "engine floor"
tools/check_overrides_growth.py              # Hooks — gates brand_overrides
tools/reconcile_build_py.py                  # Phase F — applies inject.yml
shared/inject.schema.yaml                    # Phase F — jsonschema (Draft 2020-12)
templates/<slug>/inject.yml                  # Phase F — per-template overlay
templates/<slug>/TOLERANCE_LOG.md            # P4 audit trail

</interfaces>
```

## Standard Stack (verified installed)

| Library | Version | Use case |
|---|---|---|
| simple_idml | 1.3.1 | IDML XPath via `get_spread_object_by_xpath/by_name` |
| lxml | 5.4.0 | IDML XML; `xpath()` with `[@attr='val']` predicates |
| jsonschema | 4.26.0 | Draft 2020-12, idiom from `tools/experiment_envelope.py:170` |
| pdfplumber | 0.11.9 | composite-AI page enumeration via `len(pdf.pages)`, `page.bbox` |
| PyYAML | 6.0.3 | `yaml.safe_dump(sort_keys=True)` idiom |
| Pillow | 12.2.0 | pinned; heatmap, region crop |
| poppler 25.03 | pdfinfo, pdftocairo, pdfimages, pdftotext, pdffonts | |
| ImageMagick | compare/convert/montage | page-wide diff (visual_diff.py) |
| argparse | stdlib | CLI consistency with rest of repo |

**Don't introduce**: click, typer, pikepdf, pypdf, numpy, matplotlib, opencv. Stdlib + lxml + simple_idml + pdfplumber + Pillow covers every concrete need.

## Don't Hand-Roll

- **CLI parsing**: argparse, mirror `bin/render-gallery` shim pattern.
- **Skill body**: copy `.claude/skills/experiments/SKILL.md` structure verbatim — frontmatter, `## When invoked as /<verb>` dispatch table, `## Pre-flight checks per verb`, per-verb numbered steps with bash invocations.
- **Pattern registry**: hand-rolled ordered list at `tools/idml_to_dsl_patterns/__init__.py::PATTERNS` (model after `BRAND_CONSTRAINTS` at line 1525). NO entry_points / pkgutil auto-discovery (loses ordering).
- **YAML validation**: copy `tools/experiment_envelope.py:170-185` idiom with `Draft202012Validator`. Schema lives at `shared/inject.schema.yaml`, NOT inline.
- **JSONL iteration log**: `json.dumps(row, separators=(",",":")) + "\n"` appended to file. No structured-logging library.
- **Composite-AI page count**: `pdfplumber.open(ai_path); len(pdf.pages)`. AI files are PDF-compatible.
- **Asset audit** integration: existing `tools/links_export.py::ExportResult` + new `tools/asset_extraction_audit.py` that consumes `links_export.yml` + IDML refs.

## Architecture Patterns

### `inject.yml` selector — structured dict, NOT CSS

ISSUE.md proposed `target: ImageFrame[anname=u4a2]` CSS-selector syntax. lxml doesn't natively support CSS in `.xpath()`. Use a structured dict instead — easier to validate, smaller surface area:

```yaml
hand_patches:
  - target: {element: ImageFrame, anname: u4a2}
    field: scale_type
    set: 0
    reason: "Backport 10 edge case — Scribus 1.6.x SCALETYPE=1 with high downscale ratio. See scribus-bug-XXXX."
    classification: scribus-engine-bug
    follow_up_issue: null
```

Reconcile resolves via `idml.get_spread_object_by_name(anname)` (SimpleIDML).

### Pattern registry shape (Phase D)

```python
# tools/idml_to_dsl_patterns/__init__.py
PATTERNS: list[type] = [
    JustificationToAlign,          # Backport 9
    DefaultStyleAlign,             # Backport 11 (depends on JustificationToAlign)
    ScaleTypeCropped,              # Backport 10
    PolylineRoundCaps,
    TextFrameHeightWidening,
    ImageFramePdfSourceForVectors, # NEW — fixes composite-AI via per-page PDF refs
]

# Each pattern:
class Pattern:
    id: str
    def matches(self, idml_element) -> bool: ...
    def apply(self, kwargs: dict, idml_element) -> None: ...
```

Order matters: later patterns can override earlier kwargs (last-writer-wins on key). Documented + tested via `tests/unit/test_patterns_ordering.py`.

### Convergence loop (Phase A)

```python
def converge(slug, max_iter=10, accept_residual=[]):
    prev_drift = None
    for i in range(1, max_iter+1):
        render_and_audit(slug)               # writes preflight.yml
        review = run_convergence_review(slug)  # classifies + scores leverage
        log_iteration(slug, i, review)       # appends iteration.jsonl

        if review.preflight_ok:
            return 0

        # P10 regression guard (page-wide primary; per-region secondary)
        if prev_drift and review.drift_p1 > prev_drift.p1 + 0.05:
            return 3

        prev_drift = review.drift

        actionable = [i for i in review.issues
                      if i.classification in ("converter-bug","scribus-engine-bug")
                      and i.id not in accept_residual]
        if not actionable:
            if all(i.id in accept_residual for i in review.issues):
                return 0
            return 2  # NEEDS_REVIEW

        apply_fix(actionable[0])  # may extend converter and re-emit
    return 1  # max iterations exceeded
```

### Classification rules (P5)

Heuristics map audit signals to one of 4 categories. **Bias to `human-review` on uncertainty** — F1 expectations for narrow rule-based classifiers are 0.7 (per flaky-test prior art).

| Signal | Classification | Confidence |
|---|---|---|
| `region_color_audit::icc_likely` + brand-color region | scribus-engine-bug | HIGH |
| `text_position_audit::drift_mm > 0.5` + IDML XPath shows mixed-Justification | converter-bug | MEDIUM |
| `per_element_drift::region` matches Backport-10-class IDML attrs | scribus-engine-bug | HIGH |
| `drift_type == missing` and bbox covers IDML element NOT in build.py annames | converter-bug | HIGH |
| Drift exists only in baseline.pdf (preview matches reference) | authoring-bug | HIGH |
| Otherwise | human-review | SAFE FALLBACK |

### Leverage scoring (`est_drift_drop`)

Linear, pessimistic, sum-of-attributed-contributions per slot. Cap at page total.

```python
def est_drift_drop(issue, per_element_drift):
    slot, page = issue.slot, issue.page
    contributions = [r.mismatch_pct for r in per_element_drift[page].regions
                     if r.slot == slot]
    return min(sum(contributions), per_element_drift[page].total_mismatch_pct)
```

Sort key: `(-est_drift_drop, severity_rank, slot)` for byte-stable output.

### Hook chain (machine enforcement)

```
git commit / CI
  ↓
pre-commit:
  → tools/sop_lint.py        — grep -i "engine[_ ]floor" in tracked files
  → tools/check_overrides_growth.py — diff meta.yml::brand_overrides, require inject.yml/TOLERANCE_LOG.md entry
  → existing CI gates (sla_diff, structural_check, pytest, etc.)
```

Skill SOP prose is layer 1 (reduces violation rate); hooks are layer 2 (the actual guarantee).

## Common Pitfalls

See [research/pitfalls.md](research/pitfalls.md) for full catalogue.

### P0 — Blockers for acceptance criteria as written

1. **"engine floor" string already exists in main** (`tools/region_color_audit.py:6, :245`). Acceptance criterion "grep returns 0 hits" fails until renamed. Concrete fix: rename to `icc_drift_uniform_small`.
2. **Composite-AI detection rule "AI has > 1 page" misses v2-falzflyer**. The Social Media Icons AI is **1 page, 526×152pt** (wide strip with 4 icons side-by-side). Detection MUST fall back to: aspect ratio > 3:1 OR multiple ImageFrame references to the AI with different LocalOffsets.
3. **Composite-AI splitting must be IN scope** (not deferred per ISSUE.md). Otherwise v2-falzflyer cannot be re-imported end-to-end — the literal test case for the new tooling.

### P1 — `build.py` portability

4. **Current `build.py` embeds absolute worktree paths.** Phase D refactor must emit repo-relative paths.

### P2 — Per-region regression-guard noise

5. **Per-region regression detection is noisy.** Structural fixes routinely improve page-wide drift while worsening anti-aliasing in individual cells. Use page-wide as primary halt signal (P10 regression guard); per-region only triggers if BOTH regress.

### P3 — Brand-fonts CI gap

6. **`_verify_brand_fonts()` hard-fails if <30 gruene fonts available.** Add `--no-brand-fonts` flag with loud warning (never silent skip).

### P4 — Pattern library refactor regression risk

7. **Refactoring 6 inline backports out of `tools/idml_to_dsl.py` without changing byte-output on existing templates is risky.** Strategy: regenerate `build.py` for all 4 audit-eligible templates before+after refactor, diff at byte level, fail on any change. Allow per-pattern enable flag during incremental migration.

### P5 — Inject.yml migration risk for v2-falzflyer

8. **v2 has 14 P5/inject comments today**, including 4 y-coord bumps (FirstBaselineOffset compensation) that don't fit naturally into the `set:` schema. Add a `delta:` field for additive overrides alongside `set:` for absolute overrides.

### P6 — Convergence-review classifier risk

9. **`converter-bug` vs `scribus-engine-bug` ambiguity.** Example: Kasten not centered — could be either (was actually engine). The classifier must inspect IDML attributes AND post-conversion build.py emission AND compare to baseline.pdf coords. Bias toward `human-review` when signals disagree.

### P7 — Already-imported re-import semantics

10. **`bin/idml-import` on existing template**: detect existing `templates/<slug>/`, switch to "re-audit" mode unless `--reimport` flag given. Don't silently overwrite hand-patched build.py.

### P8 — Multi-IDML batch failures

11. **One IDML fails mid-batch.** Continue processing remaining, report at end, exit code reflects "any failure". Per-template `import_report.md` independent of batch.

### P9 — Pattern ordering bugs

12. **Late pattern reads stale state set by earlier pattern.** Document the contract: patterns SHOULD only set keys they own; if they read other keys, declare dependency in docstring; assertion tests cover known interactions.

## Environment Availability

- **CI**: brand fonts NOT installed (proprietary, gitignored). `bin/render-gallery --audit` fails on font_audit step. `bin/idml-import` must detect this and either skip render-dependent audits with explicit `--no-brand-fonts` warning OR run structural audits only.
- **Dev container**: brand fonts installed via Dockerfile.claude. Full pipeline works.
- **`pdfplumber 0.11.9`** is installed but NOT declared in `Dockerfile.claude` (per #37 ecosystem research — flag for explicit declaration when new tools land that depend on it).
- **Pillow 12** deprecation: `Image.getdata()` removal Pillow 14 (2027). Use `Image.histogram()` / `Image.tobytes()`.

## Project Constraints

- No `CLAUDE.md` repo-wide.
- `.issues/config.yaml`: opus research/plan, sonnet execute; branch `issue/{slug}`; GitHub mirror.
- Commit format: `<id>: <type>(<scope>): <subject>`.
- No "claude" in commits/code/files.
- No emoji unless asked.
- Pillow pinned 12.2.0; no upgrade.
- SimpleIDML pinned 1.3.1; no upgrade.

## Sources

| Source | Confidence | Notes |
|---|---|---|
| `tools/idml_to_dsl.py:992,2040-2061,2305-2390,1858-1879` | HIGH | Backports 9/10/11/PolyLine line ranges |
| `tools/render_pipeline.py:662,1097,262,1206-1217` | HIGH | _run_audit, _build_preflight, fonts gate, diagnostic-only audits |
| `tools/sla_lib/builder/brand_constraints.py:1525` | HIGH | Registry pattern to mirror for Phase D |
| `tools/sla_lib/builder/meta_schema.py::load_brand_overrides` | HIGH | Overlay-loader pattern |
| `tools/links_export.py:154-180,223-283` | HIGH | Dispatch table; docstring lies about .psd |
| `tools/region_color_audit.py:6,245` | HIGH | "engine floor" string in main (must rename) |
| `.claude/skills/experiments/SKILL.md` | HIGH | Skill model |
| `tools/experiment_envelope.py:170-185` | HIGH | jsonschema validation idiom |
| `Anthropic Skill authoring best practices` | HIGH | Frontmatter, 500-line body, MUST-language |
| `pdfplumber 0.11.9` REPL probe | HIGH | `len(pages)`, `page.bbox` on .ai files |
| `Dockerfile.claude:66-74` | HIGH | Pinned deps; no upgrade |
| v2 falzflyer `build.py` P5/inject grep | HIGH | 14 inject comments (seed data for Phase F) |
| v2 falzflyer `meta.yml` brand_overrides | HIGH | 5 silently-added entries from #35 (P4 motivation) |
| `/workspace/originals/.../Social Media Icons weiss.ai` `pdfinfo` | HIGH | 1-page 526×152pt strip (composite detection edge case) |
| flaky-test classifier prior art | LOW | F1 expectations ~0.35-0.67 for narrow rule-based classifiers |
| BackstopJS / Percy / Chromatic | MEDIUM | No industry precedent for fixed-grid sizing (per #37 research) |

## Open Questions for Planner

1. **Composite-AI splitting depth**: detect-only (Phase E) vs full per-page extraction + ImageFrame PDF reference (Phase D pattern). Recommendation: BOTH — Phase E audit detects + scaffolds, Phase D pattern handles the emission. v2-falzflyer is the regression test for both.
2. **Pattern refactor incrementality**: refactor all 6 backports in one PR vs one-pattern-per-PR. Recommendation: one PR, one pattern at a time, byte-diff regression test after each. Easier to bisect if something breaks.
3. **`bin/idml-import` re-import semantics**: refuse vs --reimport flag vs auto-merge with inject.yml preserved. Recommendation: refuse by default; `--reimport` overwrites build.py but preserves inject.yml.
4. **`drift_type` schema extension**: currently emits 5 values, schema reserves 7. Recommendation: extend the bbox extractor to emit `scale` and `color` based on existing region_color_audit signals. Not strictly required for #38 but improves classifier signal.
5. **Iteration cap**: `--max-iterations` default. Recommendation: 10. CI runs may set to 3.
6. **Skill body length budget**: 500 lines fits SOP body, but classification.md + pattern_library.md + tolerance_protocol.md + inject_protocol.md add 4 more files. Recommendation: keep them — Anthropic best-practices explicitly mention progressive disclosure with one-level-deep linked files.

## Cross-references

- Issue #35 (PR #76) — converter bootstrap + v2 convergence; lessons informing P2/P4 mechanism.
- Issue #37 (PR #77) — audit infrastructure + Backports 9/10/11/12; this issue builds on it.
- Issue #36 (PR #75) — diff_bbox_extract (drift_type field added in #37).
- Memory: `feedback_fix_generator_not_artifact.md` (P3), `feedback_idml_leading_vs_rendered.md` (P5 example), `feedback_verify_reference_before_trusting.md` (P1), `feedback_no_claude_attribution.md` (commit hygiene).
