---
id: '38'
title: IDML import skill — end-to-end converter-driven convergence (no engine floor)
status: open
priority: high
labels:
- dsl
- templates
- tooling
- skills
- workflow
- visual-qa
source: github
source_id: '78'
source_url: 'https://github.com/GrueneAT/vorlagen/issues/78'
---

## Context

Issues #35 (PR #76) and #37 (PR #77) shipped the converter and the audit
infrastructure. Today, importing a new IDML template still requires a human
to drive the loop manually:

1. Run `tools/idml_to_dsl.py` with the right flags.
2. Author `templates/<slug>/meta.yml` (preflight, ci_overrides, slots).
3. Author `templates/<slug>/diff.yml` (visual-diff tolerance).
4. Run `bin/render-gallery <slug> --audit` and read 11+ separate YAML files.
5. Decide for each surfaced drift whether to:
   - hand-patch `build.py` (P5/inject),
   - extend the converter,
   - add a `brand_overrides` entry,
   - declare "engine floor".

The v2 falzflyer convergence session (issue #35) showed two failure modes:

- **The "engine floor" trap.** Two Sonnet executor agents (~5 hr / ~1500 tool
  calls) declared an engine floor at page1=7.31% / page2=6.31% while large
  structural issues remained (invisible icons, left-aligned headlines, missing
  attribution caption, broken icon strip). A 6-image visual review by a
  third reviewer surfaced 7 concrete converter bugs the executors had missed.
  **The user's directive:** never assume a floor. Every drift is a converter
  bug until proven otherwise. Always extend the converter when a new pattern
  surfaces.
- **The "silent skip" trap.** `brand_overrides` and `non_ci_styles` in
  `meta.yml` let an executor silently exclude failing checks. Once excluded,
  the issue disappears from the audit oracle and never gets fixed.

This issue lands the end-to-end **import-and-converge** machinery so that:

1. A human drops one or more `.idml` files into a known directory.
2. A single skill invocation extracts assets, scaffolds the template, runs
   the converter, runs all audits, classifies every surfaced drift, and
   either fixes it in the converter or escalates to the human with a
   concrete remediation plan.
3. The loop iterates until all audits pass, OR a residual class of issues
   requires explicit human review (with full context: which slot, what
   audit, suggested fix path).
4. The converter is extended on every novel IDML pattern. No silent
   tolerance growth.

This is the "Phase C" workflow scaffold that was scoped out of #37
(plus Phase B2 / Phase D5 from the same scope-out), wrapped in a strict
SOP that enforces converter-first remediation.

## Principles

These rules govern the IDML import workflow and must be encoded verbatim
in the `/idml-import` skill so they cannot be bypassed mid-run.

### P1 — `baseline.pdf` is THE convergence target. Only success criterion.

(Inherited from #37.) `templates/<slug>/baseline.pdf` is the InDesign-exported
PDF supplied by the source asset. The job is to reproduce it. If
`preview.pdf` differs from `baseline.pdf`, the question is never "is the
difference acceptable" — it is **always** "what is the converter, the SLA,
or the IDML doing differently from InDesign, and how do we close the gap."

### P2 — No engine floor. Every drift is a converter bug until proven otherwise.

The convergence loop never terminates with "this is the engine floor."
When per-page `mismatch_pct` plateaus, the SOP requires:

1. Run all audits (preflight.yml must reflect current state).
2. For each non-zero issue, classify (see P5).
3. If classification yields `converter-fix`, extend the converter, re-emit.
4. If classification yields `human-review`, present concrete context to the
   user (which slot, which audit, which IDML element, what InDesign did
   that Scribus cannot).
5. Only `human-review` and `authoring-bug` (baseline.pdf has a typo / bad
   alignment that the converter would faithfully reproduce) can result in
   not closing the drift. NOT "engine floor."

The phrase "engine floor" is banned in EXECUTION.md / NEXT_STEPS.md. The
SOP linter rejects PRs that introduce it.

### P3 — Converter-first remediation. Hand-patching `build.py` is a last resort.

When a drift is identified:

1. **Default action:** extend `tools/idml_to_dsl.py` (or a new pattern in
   `tools/idml_to_dsl_patterns/`) so the regenerated `build.py` already
   handles the case. Add a regression test BEFORE the fix.
2. **Only when the converter cannot detect the pattern** (e.g. composite-AI
   strip where the IDML LocalOffset is wrong), hand-patch `build.py` with a
   `# P5/inject: ...` comment AND open a follow-up issue documenting the
   converter gap.
3. Hand-patches in `build.py` are tracked in `inject.yml` (Phase D5) so a
   future converter-extension PR can remove them.

Memory note `feedback_fix_generator_not_artifact.md` is the canonical
restatement of this rule.

### P4 — No silent tolerance growth.

`brand_overrides`, `non_ci_styles`, `non_ci_colors`, `non_ci_layers`,
`per_page` tolerance overrides, and `fuzz_pct` per-region tweaks all
require:

1. Explicit user confirmation in the skill flow (the skill MUST ask before
   adding any tolerance entry).
2. A `reason` field that names the source-asset intent OR the engine bug
   (not just "noisy").
3. An entry in `templates/<slug>/TOLERANCE_LOG.md` with date + user +
   reason.

The skill refuses to auto-add tolerances. If the user declines, the issue
stays open and becomes an open question on the import.

### P5 — Every drift gets classified before any action.

The four classifications:

- **`converter-bug`** — the converter emitted SLA differently from what the
  IDML actually says. Fix the converter, re-emit, re-test. Examples:
  Backports 9/10/11 from #37.
- **`scribus-engine-bug`** — the converter emitted SLA correctly per IDML
  spec, but Scribus 1.6.x renders it wrong. Document with minimal SLA
  reproducer, hand-patch `build.py`, open upstream Scribus issue link.
  Example: SCALETYPE=1 invisible icons (issue 37 Backport 10 root cause).
- **`authoring-bug`** — `baseline.pdf` itself has the bug. InDesign authored
  the source with a misalignment, missing glyph, bad spacing, etc. The
  converter faithfully reproduces the bug. Flag for human review with the
  exact baseline.pdf coordinates + IDML XPath; do NOT fix on the
  converter side.
- **`human-review`** — drift cannot be auto-classified. Present full context
  to the user; user picks the path forward.

The skill emits a classification for every issue in
`build/<slug>/iteration_<N>.classification.yml`.

### P6 — One-command end-to-end import.

The user-facing contract is:

```
$ # Drop /workspace/incoming/<name>.idml into the workspace
$ bin/idml-import /workspace/incoming/<name>.idml
# OR
$ bin/idml-import /workspace/incoming/                # whole directory
```

The command:

1. Slugifies the IDML filename → `<slug>`.
2. Validates IDML structure (Spreads + Stories + Styles + Resources present;
   `Links/` directory present sibling; brand fonts available in `shared/fonts/`).
3. Runs `tools/links_export.py` → `shared/assets/<slug>/<asset>.png` +
   `links_export.yml`.
4. Runs `tools/idml_to_dsl.py` → `templates/<slug>/build.py`.
5. Scaffolds `templates/<slug>/meta.yml` and `templates/<slug>/diff.yml` from
   templates (no `brand_overrides` unless user confirms).
6. Copies the InDesign-exported reference PDF to `templates/<slug>/baseline.pdf`
   (the user supplies this alongside the IDML).
7. Runs `bin/render-gallery <slug> --audit` (audit-strict by default).
8. Runs `bin/convergence-review <slug>` → structured issue list.
9. Iterates: classify → fix converter → re-emit → re-render → re-audit.
   The loop terminates when `preflight.ok == true` OR all remaining
   issues are classified as `human-review` / `authoring-bug` with user
   confirmation.

Multiple IDMLs in one batch: process each independently, then report a
combined summary.

### P7 — Asset extraction completeness is a hard precondition.

Before any conversion attempt:

1. The IDML's `Links/` directory must exist and be sibling to the `.idml`.
2. Every `<Link>` element in any Story / Spread must resolve to a file in
   `Links/`.
3. Every asset must convert successfully via `tools/links_export.py`:
   - `.ai` → PDF (vector, not PNG) if the asset will be referenced as
     an ImageFrame source; AND a PNG fallback at 600 DPI.
   - `.psd` → PNG via Pillow ImageCms (already shipped).
   - `.jpg`, `.png` → passthrough.
4. **NEW:** composite-AI files (multiple icons in one `.ai`) must be split
   per-icon by reading the AI's page-region geometry, not via hand-cropped
   PNGs. The converter's emission references the per-icon AI page, never
   a hand-cropped PNG.

If asset extraction fails or is incomplete, the skill aborts BEFORE
running the converter and emits a concrete error: "Asset `X` missing in
Links/" or "Composite AI `social-media-icons-weiss.ai` requires per-page
extraction; converter cannot handle this until issue #N lands."

### P8 — `preflight.yml::ok` is the only gate. No bypass.

`bin/render-gallery --audit` hard-fails on `preflight.ok=false` (already
shipped in #37). This issue tightens:

- `--audit-strict` becomes the default for `bin/idml-import` (cannot be
  disabled by argument).
- The skill refuses to declare convergence done while
  `preflight.ok=false` unless the user explicitly approves the remaining
  issues with `--accept-residual <issue-id>...` flags AND each accepted
  issue is classified `human-review` or `authoring-bug` (NOT
  `converter-bug` or `scribus-engine-bug` — those must be fixed).

### P9 — Pattern library, not ad-hoc converter edits.

When a converter extension is required, it lands as a **pattern** in
`tools/idml_to_dsl_patterns/<pattern_name>.py`:

```python
# Example: tools/idml_to_dsl_patterns/round_line_caps.py
"""Map IDML EndCap=RoundEndCap / EndJoin=RoundEndJoin to Scribus
PLINEEND=32 / PLINEJOIN=128."""

def matches(idml_element) -> bool:
    return (idml_element.get("EndCap") in CAP_MAP
            or idml_element.get("EndJoin") in JOIN_MAP)

def apply(kwargs: dict, idml_element) -> None:
    # mutate kwargs in place
    ...

# tests/unit/test_pattern_round_line_caps.py
def test_pattern_round_caps_emits_pline_attrs():
    ...
```

Each pattern has:
- A `matches(idml_element) -> bool` predicate.
- An `apply(kwargs: dict, idml_element) -> None` mutator.
- A unit test with a synthetic IDML fixture.
- A row in `tools/idml_to_dsl_patterns/INDEX.md` (purpose, source IDML
  attribute, target SLA attribute, regression-test path).

Patterns are loaded in `tools/idml_to_dsl.py` via a registry. New patterns
land via PR with regression tests. Removing a pattern requires the same
PR-review discipline (no silent removal).

### P10 — Iteration log is the audit trail.

Every render cycle writes a row to `build/<slug>/iteration.jsonl`:

```jsonl
{"iteration": 1, "timestamp": "2026-05-13T10:00:00Z", "preflight_ok": false, "issues_open": 12, "drift_p1": 7.31, "drift_p2": 6.31, "changes": ["initial_emission"]}
{"iteration": 2, "timestamp": "2026-05-13T10:05:00Z", "preflight_ok": false, "issues_open": 8, "drift_p1": 3.21, "drift_p2": 2.42, "changes": ["pattern:round_line_caps applied"]}
{"iteration": 3, "timestamp": "2026-05-13T10:08:00Z", "preflight_ok": true, "issues_open": 0, "drift_p1": 0.8, "drift_p2": 0.5, "changes": ["pattern:align_inheritance applied"]}
```

The skill rejects iterations that increase drift on any page (regression
guard). Acceptance criterion: every render cycle is logged; regressions
are surfaced as such.

## Scope

Six deliverables, organised by user-visible value.

### Phase A — `bin/idml-import` end-to-end driver

**Tool:** `bin/idml-import` + `tools/idml_import_driver.py`

CLI:

```
bin/idml-import <path>... [--accept-residual ISSUE_ID...] [--dry-run]
                          [--max-iterations N] [--keep-baseline-from-pdf]
                          [--scaffold-only]

Arguments:
  <path>      One or more .idml file paths, OR a directory containing .idml files.

Flags:
  --accept-residual ISSUE_ID...   Explicit list of human-review / authoring-bug
                                  issues the user has accepted. Required to
                                  exit success with preflight.ok=false.
  --max-iterations N              Cap the convergence loop at N iterations
                                  (default 10). Useful for CI.
  --dry-run                       Run conversion + audit, do not commit
                                  anything.
  --keep-baseline-from-pdf <P>    Use PDF at <P> as baseline.pdf (otherwise
                                  reads sibling `<name>.pdf` of the IDML).
  --scaffold-only                 Stop after step 6 (scaffold + first audit).
                                  Useful for inspecting the initial state.
```

Output:

- `templates/<slug>/` populated with `build.py`, `meta.yml`, `diff.yml`,
  `template.sla`, `preview.pdf`, `baseline.pdf`, `page-*.png`.
- `build/<slug>/iteration.jsonl` log of every cycle.
- `build/<slug>/import_report.md` final summary (PASS / NEEDS_REVIEW /
  BLOCKED with issue list).

### Phase B — `bin/convergence-review` issue classifier

**Tool:** `bin/convergence-review` + `tools/convergence_review.py`

CLI:

```
bin/convergence-review <slug> [--format md|json] [--out PATH]
```

Reads:
- `build/validation/<slug>/preflight.yml`
- All 10 sub-audit YAMLs
- `build/validation/<slug>/diff_bboxes.json`
- `build/validation/<slug>/visual_diff.json`
- `build/validation/<slug>/visual_diff_regions.yml`

Emits a sorted issue list:

```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
verdict: NEEDS_WORK         # PASS / NEEDS_WORK / BLOCKED_BY_AUTHORING
issues_open: 4
issues:
  - id: 1
    slot: u376
    audit: text_position_audit
    severity: large
    classification: converter-bug
    converter_path: tools/idml_to_dsl.py:1782-1798 (DefaultStyle ALIGN)
    suggested_action: |
      The DefaultStyle inheritance for mixed-Justification frames is
      incomplete (Backport 11 edge case). Extend the converter to emit
      per-paragraph ALIGN regardless of effective alignment, not only
      when non-zero.
    regression_test_path: tests/unit/test_idml_to_dsl_align_mixed.py (NEW)
  - id: 2
    slot: u1ae
    audit: region_color_audit
    severity: icc_likely
    classification: scribus-engine-bug
    suggested_action: |
      ICC RGB→CMYK conversion drift on the Dunkelgrün background polygon.
      Hand-patch templates/<slug>/build.py with `# P5/inject: ICC engine
      drift, tracked in inject.yml`. Open issue X for upstream tracking.
  - id: 3
    slot: u2cd
    audit: per_element_drift
    severity: 2.01pp
    classification: human-review
    suggested_action: |
      Pine-forest crop offset. The IDML's <Image> ItemTransform encodes
      a crop that the converter applies, but Scribus's PDF export shifts
      the crop by ~0.5mm in Y. Could be (a) converter mis-reads the
      transform, (b) Scribus rendering bug, (c) baseline.pdf
      InDesign-specific anti-aliasing. Human inspection of all three
      PDFs side-by-side at 600 DPI is required.
hot_issues_by_leverage:
  - {id: 1, est_drift_drop: 1.5pp}
  - {id: 2, est_drift_drop: 1.7pp}
```

### Phase C — `/idml-import` skill (SOP enforcement)

**Skill:** `.claude/skills/idml-import/SKILL.md` + helpers.

Skill workflow:

1. **Pre-flight checks** — IDML structure, Links present, fonts available,
   baseline.pdf present.
2. **Extraction** — invoke `tools/links_export.py`, assert all `<Link>` URIs
   resolve. If composite AI detected, refuse and emit error per P7.
3. **Scaffold** — `templates/<slug>/{meta.yml, diff.yml}` from minimal
   templates; ask user before adding any `brand_overrides`.
4. **Conversion** — invoke `tools/idml_to_dsl.py`.
5. **First-render audit** — `bin/render-gallery <slug> --audit-strict`.
6. **Review** — `bin/convergence-review <slug>` emits the classified issue
   list.
7. **Convergence loop**:
   - For each `converter-bug`: locate converter code, write regression
     test, extend converter (or add pattern in
     `tools/idml_to_dsl_patterns/`), re-emit, re-render, re-audit.
   - For each `scribus-engine-bug`: hand-patch build.py with explicit
     `# P5/inject` comment, register in `inject.yml`.
   - For each `authoring-bug`: present to user with baseline.pdf
     coordinates + IDML XPath; user decides whether to leave as-is or
     fix in IDML.
   - For each `human-review`: STOP loop iteration, present full context,
     wait for user direction.
8. **Termination** — `preflight.ok=true` OR remaining issues all
   `human-review` / `authoring-bug` with `--accept-residual` flags.

The skill REFUSES to:
- Add `brand_overrides` entries without user confirmation.
- Declare "engine floor."
- Skip audit failures via meta.yml overrides without rationale.
- Cap the converter at "good enough" — extends until preflight is clean
  or the user explicitly accepts a residual.

### Phase D — `tools/idml_to_dsl_patterns/` pattern library

**Initial patterns to extract from current converter:**

1. `justification_to_align.py` — Backport 9 (IDML `Justification` →
   Scribus `ALIGN` int). Extracted from `tools/idml_to_dsl.py:JUSTIFICATION_MAP`.
2. `scale_type_for_cropped_images.py` — Backport 10 edge case (SCALETYPE=1
   when local_offset_mm != (0,0) OR local_scale != (1,1)).
3. `default_style_align_inheritance.py` — Backport 11 (DefaultStyle ALIGN
   propagation). Extracted from `tools/idml_to_dsl.py:1775-1787`.
4. `polyline_round_caps_joins.py` — `EndCap` / `EndJoin` → `PLINEEND` /
   `PLINEJOIN`. Extracted from issue #76's PolyLine emission.
5. `text_frame_height_widening.py` — current Pattern 9 (Scribus clips,
   IDML overflows silently). Already in converter; refactor as pattern.
6. `image_frame_pdf_source_for_vectors.py` — NEW. When the IDML references
   an `.ai` file, emit ImageFrame with `image=<path>.pdf` (not the PNG
   raster). Preserves vector quality.

**Registry:** `tools/idml_to_dsl_patterns/__init__.py` exposes a
`PATTERNS` list; `tools/idml_to_dsl.py` iterates patterns at the
appropriate emission points.

### Phase E — Asset extraction completeness

**Tool:** `tools/asset_extraction_audit.py`

Checks:

1. Walk IDML for every `<Link LinkResourceURI=...>`.
2. Verify the file exists in `<idml>/../Links/`.
3. Verify `links_export.yml` has an entry for it.
4. Verify the converted asset exists in `shared/assets/<slug>/`.
5. **NEW:** Detect composite-AI files (multiple icons in one `.ai`) and
   refuse to proceed until per-icon page extraction lands. Detection:
   AI has > 1 page OR the IDML references the AI from > 1 ImageFrame
   with different `LocalOffset` values that don't match the AI's
   single-page extent.
6. Emit `build/validation/<slug>/asset_audit.yml`:

   ```yaml
   template: <slug>
   links_total: 7
   links_resolved: 7
   links_converted: 7
   composite_ai_detected: []
   ok: true
   ```

Wired into `_run_audit` BEFORE A1 inventory (so the inventory audit
doesn't trip on missing assets).

### Phase F — `inject.yml` overlay + `tools/reconcile_build_py.py`

**Files:**

- `templates/<slug>/inject.yml` — declarative hand-patches.
- `tools/reconcile_build_py.py` — applies `inject.yml` on top of the
  converter's emitted `build.py` to produce the final `build.py`.

Schema:

```yaml
# templates/<slug>/inject.yml
hand_patches:
  - target: ImageFrame[anname=u4a2]
    field: scale_type
    set: 0
    reason: |
      Backport 10 edge case — Scribus 1.6.x renders SCALETYPE=1 with high
      downscale ratio invisible (white-on-transparent RGBA PNG). See
      issue #37 Backport 10. Tracking upstream: scribus-bug-XXXX.
    classification: scribus-engine-bug
    follow_up_issue: null     # or e.g. "39"
  - target: TextFrame[anname=u376]
    field: default_style_attrs
    set: {ALIGN: '1'}
    reason: |
      Authoring-side: IDML has Justification=CenterAlign on the ParaStyle
      but the StoryText doesn't propagate. Converter could do this
      automatically — open issue #N to extend the converter, then remove
      this inject entry.
    classification: converter-bug
    follow_up_issue: '39'
```

Workflow:

1. Converter emits `build.py.generated` (verbatim from IDML).
2. `reconcile_build_py.py` reads `inject.yml`, applies hand-patches,
   writes final `build.py` with `# P5/inject (from inject.yml line N): <reason>`
   inline comments.
3. CI lints `build.py` to ensure every `# P5/inject` comment has a
   matching `inject.yml` entry (no hidden hand-patches).
4. When a converter-fix lands that obsoletes an inject entry, the
   reconcile run detects the redundancy and warns: "inject entry X is
   redundant; remove it after re-emission verified."

## Acceptance Criteria

### Phase A — `bin/idml-import` end-to-end

- [ ] `bin/idml-import /tmp/foo.idml` processes a single file end-to-end.
- [ ] `bin/idml-import /tmp/incoming/` processes every `.idml` in directory.
- [ ] Exits 0 only when `preflight.ok=true` OR `--accept-residual` covers
      all remaining issues.
- [ ] Writes `build/<slug>/iteration.jsonl` for every render cycle.
- [ ] Writes `build/<slug>/import_report.md` final summary.
- [ ] `--scaffold-only` mode stops cleanly after first audit.
- [ ] `--max-iterations N` halts the loop and reports unresolved issues.

### Phase B — `bin/convergence-review`

- [ ] Reads all 11 audit outputs from `build/validation/<slug>/`.
- [ ] Emits per-issue classification (4 categories per P5).
- [ ] Sorts issues by estimated drift-drop leverage.
- [ ] Each issue has a `suggested_action` field with concrete next step.
- [ ] Each `converter-bug` issue has a `converter_path` with file:line.
- [ ] Each `converter-bug` issue has a `regression_test_path` for a
      new or extended test.
- [ ] `--format json` emits machine-readable output for the skill.

### Phase C — `/idml-import` skill

- [ ] Skill file at `.claude/skills/idml-import/SKILL.md`.
- [ ] Workflow enforces 8 steps per scope.
- [ ] Skill refuses to add `brand_overrides` without user confirmation.
- [ ] Skill refuses to use the phrase "engine floor" in any artifact.
- [ ] Skill enforces "regression test before converter fix" rule.
- [ ] Skill works for multi-IDML batches (process N templates,
      combined report at end).

### Phase D — Pattern library

- [ ] At least 6 patterns extracted from current converter into
      `tools/idml_to_dsl_patterns/`.
- [ ] Pattern registry in `__init__.py`.
- [ ] Every pattern has a unit test with synthetic IDML fixture.
- [ ] `tools/idml_to_dsl_patterns/INDEX.md` documents each pattern.
- [ ] `tools/idml_to_dsl.py` iterates patterns at the right emission
      points; behavior identical to current converter on v2 falzflyer
      template (regression test).
- [ ] New pattern (e.g. `image_frame_pdf_source_for_vectors`) demonstrates
      the extensibility: matches AI-source images, emits PDF as
      ImageFrame source, regression test on v2 falzflyer's social-media
      icons.

### Phase E — Asset extraction completeness

- [ ] `tools/asset_extraction_audit.py` exists, wired into `_run_audit`
      BEFORE A1.
- [ ] Detects missing `Links/` files.
- [ ] Detects composite-AI files; refuses to proceed without per-icon
      extraction.
- [ ] Emits `asset_audit.yml` with structured shape.
- [ ] Regression test: synthetic IDML with missing link → audit ok=false.

### Phase F — `inject.yml` + reconcile

- [ ] `tools/reconcile_build_py.py` exists.
- [ ] `templates/<slug>/inject.yml` schema validated via `jsonschema`.
- [ ] Reconcile applies entries in deterministic order; output is byte-
      stable across runs.
- [ ] CI lint enforces 1:1 mapping between `# P5/inject` comments in
      `build.py` and `inject.yml` entries.
- [ ] Redundancy detection warns when an inject entry is no longer
      necessary (converter now emits the same value).
- [ ] v2 falzflyer template migrated: all current `# P5/inject` patches
      moved into `inject.yml`.

### Cross-cutting

- [ ] All audits remain green on the existing 9 templates after this
      issue lands. No regressions.
- [ ] `preflight.yml::ok=true` for v2 falzflyer template after applying
      this issue's converter extensions (patterns).
- [ ] The phrase "engine floor" appears nowhere in the codebase
      (grep -i "engine[_ ]floor" returns 0 hits across `templates/`,
      `tools/`, `bin/`, `.claude/skills/`).
- [ ] `bin/idml-import` is the documented entry point in `README.md`.

## Out of scope

- New audit tools (E2 / Backport 12 already shipped; this issue uses
  them, doesn't extend them).
- Multi-IDML coalescing into a single template (each IDML stays one
  template).
- Real-time GUI for the import flow (CLI + skill only).
- Automated upstream Scribus bug reporting.
- IDML mutation (the converter never modifies the source IDML).

## References

- Issue #35 (PR #76) — strict IDML→DSL converter bootstrap.
- Issue #37 (PR #77) — audit infrastructure, Backports 9/10/11/12.
- Memory: `feedback_fix_generator_not_artifact.md` — P3 motivation.
- Memory: `feedback_idml_leading_vs_rendered.md` — P5 classification
  example (CSR `<Leading>` vs rendered).
- Memory: `feedback_verify_reference_before_trusting.md` — P1
  motivation (baseline.pdf is the only ground truth).

## Estimated effort

3 sub-phases that can ship independently:

- **Sub-phase 1** (1-2 days): Phases A + B + E. The end-to-end driver,
  the classifier, the asset audit. Enables one-command import for any
  IDML the existing converter already handles.
- **Sub-phase 2** (2-3 days): Phase D pattern library. Refactors the
  current converter into a pattern registry, lands the 6 initial
  patterns, sets up the pattern-extension SOP.
- **Sub-phase 3** (1-2 days): Phases C + F. The skill SOP, `inject.yml`
  overlay, reconcile tool, v2 falzflyer migration.

Sub-phase 1 unlocks the user-visible "drop IDML, get template" workflow.
Sub-phase 2 makes converter extensions safe and tested. Sub-phase 3
enforces the discipline via skill + inject overlay.
