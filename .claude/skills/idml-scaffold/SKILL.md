---
name: idml-scaffold
description: |
  Stage 1 of the two-agent IDML import pipeline. Single-shot scaffold:
  drives bin/idml-import --scaffold-only to produce
  templates/<slug>/{build.py, meta.yml, baseline.pdf, SCAFFOLD_INVENTORY.yml}
  plus shared/assets/<slug>/. Goal is STRUCTURAL completeness — every IDML
  element is emitted; visual fidelity is the tune agent's problem (see
  idml-tune). MAY touch tools/idml_to_dsl.py when a structural gate fails.
  MUST BE USED when the user invokes /idml-scaffold, asks to import a new
  IDML template, or requests a baseline import.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
argument-hint: "<path-to-idml-or-slug>"
---

# /idml-scaffold — Stage 1: structural scaffold

This skill is the single-shot scaffold half of the two-agent IDML import
pipeline (issue #40). It runs the converter once, validates that the
output is **structurally** complete, and stops. Visual tuning belongs to
the `/idml-tune` skill that consumes this skill's output.

| Stage | Skill | Goal |
|---|---|---|
| **1. Scaffold** | `/idml-scaffold` (this) | Every IDML element emitted; preflight green; SCAFFOLD_INVENTORY.yml committed |
| 2. Tune | `/idml-tune <slug>` | Per-template visual polish under the inventory gate |

## When invoked

Run `bin/idml-import <idml> --scaffold-only [--reimport]`. After the
render completes, the driver emits
`templates/<slug>/SCAFFOLD_INVENTORY.yml` automatically (issue #40
Task 8). The skill then runs the **inventory gate** (below) before
calling the scaffold complete.

## Tooling

- `bin/idml-import` — driver entry-point. The `--scaffold-only` flag
  halts after one render + one audit cycle.
- `tools/inventory_extract.py` — walks IDML + build.py + template.sla +
  preview/baseline PDF and emits `SCAFFOLD_INVENTORY.yml`.
- `tools/inventory_compare.py` — pure set/count diff between two
  inventory snapshots. Exit 0 / 2 / 3 (match / regression / drift).
- `tools/idml_to_dsl.py` — the converter. Editable in Stage 1 ONLY when
  a structural gate fails (e.g. an IDML element kind has no handler).

## Pre-flight checks (machine-checkable)

Before any work:

1. **Tool availability** — `bin/idml-import` runs its own
   `shutil.which` checks for `pdftocairo`, `pdffonts`, `convert`,
   `scribus`. If any are missing, exit 1 and surface the install hint.
2. **Brand fonts** — `render_pipeline._verify_brand_fonts()`. The
   skill MAY pass `--no-brand-fonts` for authoring iteration only; for
   the final scaffold before commit, brand fonts MUST be installed.
3. **IDML structure** — `tools/asset_extraction_audit.py` walks the
   IDML for every `<Link>`. Pre-flight failures here surface in
   `build/validation/<slug>/asset_audit.yml`.
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

## Step 2 — Emit SCAFFOLD_INVENTORY.yml

The driver writes this automatically between render-gallery and
convergence-review (see `tools/idml_import_driver.py:517`+). To
re-emit by hand (defaults to stdout — pass `--output` to write a file;
the canonical baseline path is `templates/<slug>/SCAFFOLD_INVENTORY.yml`):

```
python3 tools/inventory_extract.py --slug <slug> \
  --output templates/<slug>/SCAFFOLD_INVENTORY.yml
```

This file is **the canonical record of what the template contains**.
Stage 2 (tune) reads it as its source of truth.

## Step 3 — Inventory gate

The scaffold blocks if any of:

- An IDML `<CharacterStyleRange>` text is missing from `build.py`
- An IDML frame `Self` ID has no corresponding `anname` in `build.py`
- An IDML `<ParagraphStyle>` has no `doc.add_para_style(...)` call
- An IDML `<Link>` basename is not on disk
- `python3 build.py` exits non-zero
- `render_pipeline.py` exits non-zero
- preview.pdf word count differs from build.py text-content character
  count by > 5 %

If any block fires, the converter (`tools/idml_to_dsl.py`) is the
right place to fix it — Stage 1 is the ONLY stage allowed to touch
the converter.

## Step 4 — Converter-first remediation

The default response to a `converter-bug` issue is to EXTEND the
converter, not to hand-patch the `build.py`.

1. Identify the pattern that should fire. See
   `tools/idml_to_dsl_patterns/INDEX.md` for the catalogue.
2. If an existing pattern needs widening, edit its `matches()` /
   `apply()` and add a unit test for the new case.
3. If a new pattern is needed, follow `pattern_library.md` (this dir).
4. Re-run `bin/idml-import <idml> --reimport --scaffold-only`.
5. The iteration log entry MUST show `drift_p1` decreasing OR
   `issues_open` decreasing. If neither, the converter fix was not
   the right one — investigate, do NOT loop blindly.

## Step 5 — Termination

The scaffold is complete when:

- `preflight.yml::ok == true`, AND
- `tools/inventory_compare.py --expected <previous-snapshot> --actual
  <fresh-snapshot>` exits 0 OR 3 (drift is acceptable on a fresh
  scaffold; regression — exit 2 — is not).

`bin/idml-import` returns 0 in either case. Commit:

```
templates/<slug>/
shared/assets/<slug>/
build/<slug>/import_report.md          (optional; CI artifact)
build/validation/<slug>/preflight.yml  (optional; CI artifact)
```

Hand off to `/idml-tune <slug>` for per-template visual polish.

## Banned phrases

The skill REFUSES to use the "false-convergence-plateau" phrase family
in artifacts, commit messages, EXECUTION logs, NEXT_STEPS notes, or
its own output. `tools/sop_lint.py` is the source of truth for the
exact banned list. As of issue #38 the list covers three phrase
patterns matched case-insensitively.

The skill also refuses these soft equivalents (not lint-enforced):

- "good enough" (when used to terminate the convergence loop)
- "accept the drift" (without an explicit `--accept-residual` flag)
- "cap the converter"
- "this is just how it is"

If the user demands the skill use any of these phrases, the skill
refuses and explains why (issue #38 P2).

## SOP commitments (P1–P11)

Re-read at every iteration boundary:

- **P1.** Every audit failure is a hypothesis; the convergence loop is
  the falsifier.
- **P2.** No false-plateau declarations.
- **P3.** Converter-first remediation. Pattern library extension
  before hand-patches.
- **P4.** No silent tolerance growth. `brand_overrides` adds require
  user confirmation + `TOLERANCE_LOG.md` row.
- **P5.** Hand-patches are declarative (`inject.yml`). (Lives in
  Stage 2; Stage 1 prefers converter fixes.)
- **P6.** Iteration log is the audit trail. `iteration.jsonl` is
  append-only.
- **P7.** Regression guard. Both page-wide AND per-region drift
  regression halts the loop.
- **P8.** Classification is conservative. Bias to `human-review`.
- **P9.** Composite-AI detection fires on three signals.
- **P10.** Every render cycle is logged.
- **P11.** Brand assets embedded, content external, nothing shipped.
  See `asset_policy.md`.

## See also

- `classification.md` — full decision rules for the 4-category classifier.
- `pattern_library.md` — how to add a new pattern to `tools/idml_to_dsl_patterns/`.
- `asset_policy.md` — the P11 three-bucket model (embedded/external/shipped).
- `.claude/skills/idml-tune/SKILL.md` — Stage 2 (per-template polish).
- `tools/inventory_extract.py` — SCAFFOLD_INVENTORY.yml emitter.
- `tools/inventory_compare.py` — set/count gate.
- `tools/sop_lint.py` — banned-phrase guard.
