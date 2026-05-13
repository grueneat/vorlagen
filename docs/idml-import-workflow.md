# IDML Import Workflow

The one-command pipeline at `bin/idml-import` turns an Adobe InDesign `.idml`
file into a fully validated `templates/<slug>/` directory ready for the
gallery, audit chain, and CI gates. Issue #38 ships this driver to replace
the ad-hoc multi-tool sequence that produced unmanaged tolerance growth in
earlier IDML imports.

## 1. Overview

`bin/idml-import` runs eleven phases for every `.idml` input:

1. Verify required CLI tools are on `PATH`.
2. Derive `<slug>` from the IDML filename via NFC + slugify.
3. Refuse to overwrite an existing template without `--reimport`.
4. Gate on brand fonts (bypassable with `--no-brand-fonts`).
5. Resolve `baseline.pdf` (sibling of the IDML or `--keep-baseline-from-pdf`).
6. Extract `Links/` through `tools/links_export.py`.
7. Run `asset_extraction_audit` — fails fast on missing links or composite-AI.
8. Scaffold `templates/<slug>/{meta.yml, diff.yml, baseline.pdf}`.
9. Run `tools/idml_to_dsl.py` to emit `build.py`.
10. Convergence loop: `bin/render-gallery --audit-strict` →
    `bin/convergence-review --format json` → append `iteration.jsonl` → regression
    guard → terminate or iterate.
11. Emit `build/<slug>/import_report.md` and exit with the appropriate code.

## 2. Prerequisites

System tools (verified at startup):

- [Scribus 1.6.x](https://scribus.net/) for the SLA renderer.
- [poppler-utils](https://poppler.freedesktop.org/) for `pdftocairo`, `pdffonts`.
- [ImageMagick](https://imagemagick.org/) for `convert`.

Python packages (pinned in the repo):

- `Pillow == 12.2.0`
- `SimpleIDML == 1.3.1`
- `pdfplumber`, `lxml`, `PyYAML`, `jsonschema`

Brand fonts: the gruene font family must be installed for full audit fidelity.
In CI environments without the fonts, pass `--no-brand-fonts` to bypass the
verification gate. Font-fidelity audits downstream will be degraded.

## 3. Quick start

```bash
# Single IDML next to its baseline PDF and Links/ folder.
bin/idml-import path/to/template.idml

# Batch — every *.idml under the directory.
bin/idml-import path/to/incoming/

# Re-import an existing template (overwrites templates/<slug>/).
bin/idml-import path/to/template.idml --reimport
```

After the command completes, inspect `build/<slug>/import_report.md` for the
verdict (`PASS`, `NEEDS_REVIEW`, `BLOCKED`) and the list of open issues.

## 4. CLI reference

```
bin/idml-import <path>... [options]
```

| Flag | Default | Effect |
|------|---------|--------|
| `path` | — | One or more `.idml` files or directories containing them. |
| `--accept-residual ID` | `[]` | Accept the named issue id (`human-review` / `authoring-bug`). Repeat or pass `*` for "all". |
| `--dry-run` | off | Run through scaffold + convert only; skip the convergence loop. |
| `--max-iterations N` | 10 | Maximum convergence iterations before exit 3. |
| `--keep-baseline-from-pdf PATH` | sibling `<stem>.pdf` | Override the auto-derived baseline PDF. |
| `--scaffold-only` | off | Halt after scaffold + first audit cycle. |
| `--reimport` | off | Allow overwriting `templates/<slug>/`. |
| `--no-brand-fonts` | off | Skip the brand-fonts pre-flight (degraded fidelity). |
| `--allow-composite-ai` | off | Downgrade composite-AI findings to warnings. |
| `--non-interactive` | off | Never prompt; exit 2 on unaccepted residual. |

## 5. The convergence loop

After scaffold + convert, the driver enters the convergence loop:

1. `bin/render-gallery <slug> --audit-strict` rasterises and runs the 11 audits:
   - asset_extraction (Issue #38 Phase E)
   - inventory (A1)
   - baseline_text (A2), baseline_image (A3)
   - font (D6), text_render (D7), text_position (D8)
   - run_style (F), per_element_drift, region_color, line_spacing (E2)
   - visual_diff_regions (Phase H)
2. `bin/convergence-review <slug> --format json` reads every audit yml/json
   and produces a classified issue list:
   - **converter-bug** — the converter emitted wrong output; fix `tools/idml_to_dsl.py`.
   - **scribus-engine-bug** — Scribus renders correctly-emitted SLA wrong.
   - **authoring-bug** — the source IDML or `baseline.pdf` is inconsistent.
   - **human-review** — ambiguous; needs triage.
   - **minor** — below `--min-drift-pp` (default 0.5); filtered out of hot list.
3. The driver appends one row to `build/<slug>/iteration.jsonl` with the
   schema documented in section 6.
4. `regression_guard` halts the loop with exit 3 if BOTH `drift_p1` and
   `drift_p1_max_region` regress AND no new audit was added this iteration.
5. If `preflight_ok` is true, or if all remaining open issues are covered by
   `--accept-residual`, the driver exits 0.
6. Otherwise the actionable issue list is surfaced and the driver exits 2.
   The user fixes the converter (extending `tools/idml_to_dsl_patterns/` or
   the inline converter logic) and re-runs `bin/idml-import --reimport`.

The driver never auto-fixes converter bugs. Issue #38 P2 ships the pattern
library that makes adding the next converter fix mechanical, not freeform.

## 6. Output layout

```
templates/<slug>/
├── build.py                  # converter-emitted; reconciled with inject.yml later
├── build.py.generated        # verbatim converter output (Phase F artifact)
├── meta.yml                  # metadata + tolerance lists
├── diff.yml                  # visual_diff tolerances
├── baseline.pdf              # copied from <stem>.pdf
├── inject.yml                # hand_patches (declarative; Phase F)
├── TOLERANCE_LOG.md          # justification for each brand_overrides row
├── template.sla              # built by render-gallery
├── preview.pdf               # rendered by Scribus
├── page-NN.png               # per-page rasters
├── page-NN-hires.png         # per-page hi-res rasters
└── README.md                 # gallery-card copy

build/<slug>/
├── import_report.md          # PASS / NEEDS_REVIEW / BLOCKED verdict
└── iteration.jsonl           # one JSON row per convergence iteration

build/validation/<slug>/
├── preflight.yml             # aggregated audit status
├── asset_audit.yml           # Phase E audit
├── inventory.yml             # A1
├── text_audit.yml            # A2
├── image_audit.yml           # A3
├── font_audit.yml            # D6
├── text_render_audit.yml     # D7
├── text_position_audit.yml   # D8
├── run_style_audit.yml       # F
├── per_element_drift.yml     # diagnostic
├── region_color_audit.yml    # diagnostic
├── line_spacing_audit.yml    # E2
├── visual_diff_regions.yml   # Phase H
├── diff_bboxes.json          # bbox extraction
└── visual_diff.json          # page-wide mismatch
```

### `iteration.jsonl` schema

Each row is a single-line JSON object with these fields (sorted alphabetically
for byte-stability):

| Field | Type | Meaning |
|-------|------|---------|
| `_schema_version` | int | Always 1 for the current format. |
| `audits_run` | list[str] | Audit ids that produced output this iteration. |
| `changes` | list[str] | Free-form labels describing what changed since the previous iteration. |
| `drift_p1`, `drift_p2` | float \| null | Page-wide mismatch (%) for pages 1 and 2. |
| `drift_p1_max_region`, `drift_p2_max_region` | float \| null | Hottest per-region mismatch on each page. |
| `issues_open` | int | Count of issues NOT classified `minor`. |
| `iteration` | int | 1-indexed iteration number. |
| `preflight_ok` | bool | `preflight.yml::ok`. |
| `rules_seen` | int | Counter; tracks SOP-injection-budget per RESEARCH.md 1.2. |
| `timestamp` | str | ISO-8601 UTC. |

## 7. Exit codes

| Code | Meaning |
|------|---------|
| 0 | `preflight.ok=true` OR every remaining open issue is in `--accept-residual`. |
| 1 | Tool missing, IDML missing, scaffold blocked, converter crashed. |
| 2 | NEEDS_REVIEW: actionable converter/engine bug surfaced; user must act. |
| 3 | Drift regression detected OR `--max-iterations` exhausted. |

## 8. Re-importing an existing template

`--reimport` overwrites `templates/<slug>/` after the asset audit succeeds.
`inject.yml` is preserved across re-imports: the converter emits
`build.py.generated`, the reconcile step folds in the `hand_patches` from
`inject.yml`, and the result lands in `build.py`. Use this when:

- The IDML changed (new authoring round).
- The converter changed (new pattern landed).
- The asset extraction recipe changed (e.g. AI emits both PDF and PNG now).

## 9. Composite-AI handling

A single `.ai` file containing multiple icons side-by-side (a "strip") is
common in InDesign templates. Out of the box, the asset audit detects them
by three signals:

- `page_count > 1` in the AI's PDF view, OR
- `aspect_ratio > 3.0`, OR
- `>= 2` distinct ImageFrame offsets referencing the same `.ai`.

If detected, the audit fails by default. Two paths forward:

- **Recommended (Issue #38 Task 14):** run `tools/composite_ai_split.py
  <ai_path> <idml> <out_dir>` to emit one PDF per icon, then re-import. The
  pattern `image_frame_pdf_source_for_vectors` in
  `tools/idml_to_dsl_patterns/` consumes the resulting per-icon PDFs.
- **Bypass:** pass `--allow-composite-ai` to downgrade to a warning. Vector
  quality degrades to whatever raster fallback `pdftocairo -png -r 600`
  produces. Acceptable for previews; not acceptable for print.

## 10. Troubleshooting

### Brand fonts not found

`bin/idml-import` calls `render_pipeline._verify_brand_fonts()`, which
runs `fc-list` and counts variants. If you see "brand fonts not available",
either install the gruene font family or pass `--no-brand-fonts` (acceptable
for converter-development iteration; not for production renders).

### Baseline PDF in a different folder

The default auto-resolution looks for `<idml-stem>.pdf` next to the IDML.
Override with `--keep-baseline-from-pdf <path>`.

### Slugified-name collisions

`tools/links_export.py` normalises filenames via NFC + ASCII transliteration.
If two source IDMLs slugify to the same name, the second overwrites the
first under `shared/assets/<slug>/`. Rename one of the source files.

### "templates/&lt;slug&gt;/ exists; use --reimport"

The driver refuses to overwrite by default. Pass `--reimport` or move the
existing directory out of the way first.

## 11. See also

- `.claude/skills/idml-import/SKILL.md` — skill workflow for Claude Code sessions.
- `tools/sop_lint.py` — bans the rendering-floor family of phrases.
- `tools/check_overrides_growth.py` — gates `brand_overrides` growth on a
  matching `TOLERANCE_LOG.md` row or `inject.yml` entry.
- `tools/idml_to_dsl_patterns/INDEX.md` — pattern catalogue for the
  converter.
- `tools/reconcile_build_py.py` — applies `inject.yml` over the
  converter-emitted `build.py.generated`.
