---
name: idml-import
description: |
  Drives bin/idml-import end-to-end. Extracts assets, scaffolds the
  template, converts IDML to build.py, runs the audit convergence loop,
  classifies drift, and surfaces converter-first remediation. Enforces
  the P1-P10 SOP from issue #38 (no false-plateau declarations,
  converter-first remediation, no silent tolerance growth).
  MUST BE USED when the user invokes /idml-import or mentions importing
  an InDesign IDML, converting an IDML template, or running the
  convergence loop on a template slug.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
argument-hint: "[main|review_only|classify_only] <path-to-idml-or-slug>"
---

# /idml-import — IDML import skill

This skill drives the `bin/idml-import` pipeline that converts an
Adobe InDesign `.idml` file into a fully validated
`templates/<slug>/` directory ready for the gallery + audit chain.

Issue #38 ships the machinery; this skill enforces the operating
procedure that governs how it is used. Quality-bar rules below are
non-negotiable: the skill refuses to bypass them.

## When invoked

| Verb | Effect |
|------|--------|
| `/idml-import` (no verb, default `main`) | Run the full pipeline on the supplied IDML or directory. |
| `/idml-import-review` | Read the latest `build/<slug>/import_report.md` + `build/validation/<slug>/preflight.yml` and explain the verdict. |
| `/idml-import-classify` | Run `bin/convergence-review <slug> --format md` and surface the hot issue list. |

For every verb, the skill follows the numbered steps below in order.

## Pre-flight checks (machine-checkable)

Before any work, verify:

1. **Tool availability** — `bin/idml-import` runs its own
   `shutil.which` checks for `pdftocairo`, `pdffonts`, `convert`,
   `scribus`. If any are missing, exit 1 and surface the install hint.
2. **Brand fonts** — `render_pipeline._verify_brand_fonts()`. The
   skill MAY pass `--no-brand-fonts` when authoring iteration only;
   for the final convergence run before commit, brand fonts MUST be
   installed.
3. **IDML structure** — `tools/asset_extraction_audit.py` walks the
   IDML for every `<Link>`. Pre-flight failures here surface in
   `build/validation/<slug>/asset_audit.yml` with a `composite_ai_detected`
   list when applicable.
4. **Baseline.pdf** — the sibling `<stem>.pdf` next to the IDML, or
   `--keep-baseline-from-pdf <path>` override. Missing baseline => exit 1.

## Step 1 — Asset extraction

Always run `bin/idml-import <idml> --scaffold-only --reimport` (or
without `--reimport` for a fresh slug) FIRST. This produces:

- `shared/assets/<slug>/links_export.yml` — the manifest.
- `build/validation/<slug>/asset_audit.yml` — the audit verdict.
- `templates/<slug>/{build.py, meta.yml, diff.yml, baseline.pdf}`.

If `asset_audit.yml::ok == false`, STOP. Composite-AI handling lives
in `tools/composite_ai_split.py`. Missing links require re-exporting
the IDML from InDesign (authoring concern, not converter).

## Step 2 — First-render audit

Read `build/<slug>/import_report.md`. If the verdict is `PASS`, the
import is complete — commit and ship.

If the verdict is `NEEDS_REVIEW` or `BLOCKED_BY_AUTHORING`, proceed to
Step 3.

## Step 3 — Classification

Read the issue list in `build/<slug>/iteration.jsonl` (latest row's
`issues_open` count) and the rich detail in
`build/validation/<slug>/preflight.yml`. Or invoke
`bin/convergence-review <slug> --format md` for the human-readable
summary.

For each open issue, the classifier produces one of four labels:

| Label | Means | Skill response |
|-------|-------|----------------|
| `converter-bug` | The converter emitted wrong SLA | Step 4. |
| `scribus-engine-bug` | Scribus renders correct SLA incorrectly | Document in `inject.yml`; accept residual. |
| `authoring-bug` | The IDML or baseline.pdf is inconsistent | Surface to the user; pause. |
| `human-review` | Ambiguous; needs triage | Surface to the user; pause. |

See `classification.md` (this directory) for the full decision rules.

## Step 4 — Converter-first remediation

The default response to a `converter-bug` issue is to EXTEND the
converter, not to hand-patch the build.py.

1. Identify the pattern that should fire. See
   `tools/idml_to_dsl_patterns/INDEX.md` for the catalogue.
2. If an existing pattern needs widening, edit its `matches()` /
   `apply()` and add a unit test for the new case.
3. If a new pattern is needed, follow `pattern_library.md` (this
   directory).
4. Re-run `bin/idml-import <idml> --reimport`.
5. The iteration log entry MUST show `drift_p1` decreasing OR
   `issues_open` decreasing. If neither, the converter fix was not
   the right one — investigate, do NOT loop blindly.

## Step 5 — Hand-patch as last resort

ONLY when the converter-first path is closed (the rule cannot be
expressed as a pattern, OR the engine bug is upstream Scribus, OR
the IDML itself encodes the irregularity):

1. Author an `inject.yml` entry per `inject_protocol.md` (this
   directory). Required: `target`, `field`, `set:` or `delta:`,
   `classification`, `reason >= 10 chars`.
2. Run `tools/reconcile_build_py.py <slug>` to produce the patched
   `build.py`.
3. Re-render + verify `tools/lint_inject_consistency.py` passes.

Every `inject.yml` entry is a future converter fix waiting to be
written. The skill REQUIRES a `follow_up_issue` field (or `null`
with a justification in `reason`) so the debt is tracked.

## Step 6 — Tolerance growth requires user confirmation

P4: `meta.yml::brand_overrides` (and `non_ci_styles`, `non_ci_colors`,
`non_ci_layers`) growth is GATED.

The skill REFUSES to add a tolerance entry without user confirmation.
The flow:

1. The skill surfaces the tolerance rule it wants to add and the
   reason.
2. The user replies "yes, add brand:X with reason Y".
3. The skill writes the TOLERANCE_LOG.md row FIRST, then mutates
   `meta.yml`.
4. `tools/check_overrides_growth.py` runs on commit and verifies the
   pair.

See `tolerance_protocol.md` for the exact wording the skill uses for
the confirmation prompt.

## Step 7 — Termination

The import is complete when:

- `preflight.yml::ok == true`, OR
- `--accept-residual` covers every remaining issue AND every accepted
  issue is classified `human-review` or `authoring-bug` (NEVER
  `converter-bug` — those go through Step 4).

`bin/idml-import` returns 0 in either case. Commit:

```
templates/<slug>/
shared/assets/<slug>/
build/<slug>/import_report.md          (optional; CI artifact)
build/validation/<slug>/preflight.yml  (optional; CI artifact)
```

## Banned phrases

The skill REFUSES to use the "false-convergence-plateau" phrase family
in artifacts, commit messages, EXECUTION logs, NEXT_STEPS notes, or
its own output. `tools/sop_lint.py` is the source of truth for the
exact banned list; the skill defers to it mechanically. As of issue
#38 the list covers three phrase patterns matched case-insensitively:
the historical "floor" framing and two equivalents.

The skill also refuses these soft equivalents (not lint-enforced, but
SOP-banned):

- "good enough" (when used to terminate the convergence loop)
- "accept the drift" (without an explicit `--accept-residual` flag)
- "cap the converter"
- "this is just how it is"

If the user demands the skill use any of these phrases, the skill
refuses and explains why (issue #38 P2).

## SOP commitments (P1-P10)

Re-read at every iteration boundary per RESEARCH.md 1.2:

- **P1.** Every audit failure is a hypothesis; the convergence loop is
  the falsifier.
- **P2.** No false-plateau declarations. Every drift is a converter
  bug until proven otherwise (scribus-engine-bug, authoring-bug, or
  human-review classification).
- **P3.** Converter-first remediation. Pattern library extension
  before hand-patches.
- **P4.** No silent tolerance growth. `brand_overrides` adds require
  user confirmation + TOLERANCE_LOG.md row.
- **P5.** Hand-patches are declarative (`inject.yml`), not inline.
  Every patch has a `reason` and a follow-up issue link.
- **P6.** Iteration log is the audit trail. `iteration.jsonl` is
  append-only.
- **P7.** Regression guard. Both page-wide AND per-region drift
  regression halts the loop.
- **P8.** Classification is conservative. Bias to `human-review`
  rather than guessing.
- **P9.** Composite-AI detection fires on three signals; the splitter
  produces per-icon PDFs; the pattern emits PDF-source ImageFrames.
- **P10.** Every render cycle is logged. The user can replay the loop
  from `iteration.jsonl` without re-running the renders.

## See also

- `classification.md` — full decision rules for the 4-category classifier.
- `pattern_library.md` — how to add a new pattern to `tools/idml_to_dsl_patterns/`.
- `tolerance_protocol.md` — the P4 confirmation flow.
- `inject_protocol.md` — the P5 hand-patch workflow.
- `docs/idml-import-workflow.md` — user-facing CLI walkthrough.
- `tools/sop_lint.py` — banned-phrase guard.
- `tools/check_overrides_growth.py` — tolerance-growth gate.
- `tools/lint_inject_consistency.py` — inject.yml ↔ build.py 1:1 lint.
