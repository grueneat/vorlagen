# Plan — 40-idml-import-two-agent-pipeline-with-script-based-inventory-gate

<objective>
Land the full two-agent IDML→Scribus import pipeline in one PR: a deterministic
inventory extractor/comparator pair, driver wiring, calibration against the
26-03 leporello anchor, mutation tests, and the `idml-scaffold` / `idml-tune`
skill split + semantics catalog. No LLM in the comparison loop; gate is pure
set/count diff with exit codes 0 / 2 / 3.
Scope: ships per CONTEXT.md "Decisions locked in". Out of scope: replacing
drift_p1, rewriting `idml_to_dsl.py`, CI/Slack integration, composite-AI
splitter overhaul, migrating other tuned templates.
</objective>

## Acceptance criteria

- `python3 tools/inventory_extract.py --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover` emits a valid YAML matching the `SCAFFOLD_INVENTORY.yml` schema (Issue.md §Inventory schema), populating every documented field.
- `python3 tools/inventory_compare.py --expected <leporello>.yml --actual <leporello>.yml` exits 0 on identical inputs.
- Mutation: drop a `Run(text=...)` word from leporello build.py → `inventory_compare.py` exits 2 with the missing word reported in `inventory_diff.yml`.
- Mutation: rename one `anname='u514'` → `anname='u514X'` in build.py → exit 2 with the anname reported as missing from build.py.
- Mutation: swap a `<Color>` CMYK in IDML side OR drop an `add_color` call → exit 2 with the color diff reported.
- `.claude/skills/idml-scaffold/SKILL.md` and `.claude/skills/idml-tune/SKILL.md` exist, each references `tools/inventory_extract.py` and `tools/inventory_compare.py`, and `idml-tune` lists forbidden paths (`tools/idml_to_dsl.py`, `tools/sla_lib/**`, shared converter code).
- `docs/scribus-sla-attribute-semantics.md` exists with sections: SCALETYPE, FLOP, LINESPMode, HCMS, PRFILE, LOCALSCX, EMBEDDED, frame rotation (w/h swap).
- `.claude/skills/idml-import/SKILL.md` becomes a redirect stub pointing at the two new skills (back-compat preserved).
- `templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml` committed as the calibrated baseline.
- `python3 tools/idml_import_driver.py --help` still works; all existing tests still pass.

## Decisions (open questions resolved)

| Open question | Decision | Why |
|---|---|---|
| AST walker fallback when a kwarg is not a literal | Skip the kwarg, record an entry in `parse_warnings: []` at the top of the extracted snapshot; do NOT fall back to importlib in v1. | RESEARCH.md §build.py walker: anchor leporello is 100% literal-kwarg; importlib executes side effects (reads `shared/assets/<slug>/`). Side-effect-free + explicit warnings beats accuracy we don't yet need. |
| Anchor template materialization | `inventory_extract.py` takes `--templates-dir` and `--originals-dir` flags; defaults are `../../templates` and `../../originals` relative to repo root (i.e. resolve to `/workspace/templates`, `/workspace/originals`). Worktree does NOT copy the 26-03 anchor in. | RESEARCH.md: anchor only exists at `/workspace/templates/`; worktree templates dir is sparse. Flag-driven path resolution avoids 200 MB worktree duplication and matches future CI invocation. |
| Inventory baseline vs runtime snapshot format | SAME schema, both produced by `inventory_extract.py`. `inventory_compare.py` reads two snapshots; the "baseline" is just the one stored in `templates/<slug>/SCAFFOLD_INVENTORY.yml`. | Simplest possible contract; matches CONTEXT.md "expected ↔ actual" diff model. |
| Composite-AI assets — one row or N | ONE row in `assets[]` per physical file, with `referenced_from_frames: [u514, u156, ...]` listing every anname that consumes it. Composite splits get one row each with a `parent_composite: <basename>` field. | CONTEXT.md / ISSUE.md schema sample shows one row; RESEARCH.md pitfall #5 confirms `composite_ai_split.yml` already records the parent linkage. |
| inject.yml ownership in the walker | MERGE into the build.py walker. After `tools/reconcile_build_py.py <slug>` materializes inject.yml into build.py, the walker parses the reconciled file. Each emitted `text_run` carries `text_source: build_py \| inject_yml` based on whether the text appears in inject.yml. | RESEARCH.md §Risks #2 recommendation; matches Stage 2 "edits build.py OR inject.yml" model with single canonical reconciled source. |
| `frames.polygon_frames[]` for falz/PolyLine | Mark with `source: manual` field; the gate ignores rows with `source: manual` on the IDML-missing side (they have no IDML counterpart). | RESEARCH.md pitfall #3: anchor has 34 manual PolyLine fold-lines. Without this flag the gate emits 34 false-positive "extras". |
| Old `idml-import/` sub-docs | Redistribute: `asset_policy.md`, `classification.md`, `pattern_library.md` → copied into `idml-scaffold/`; `inject_protocol.md`, `tolerance_protocol.md` → copied into `idml-tune/`. Original files stay in place under `idml-import/` (read-only stubs may link out). Hard-delete deferred. | RESEARCH.md §Risks #5: back-compat for tools or external docs that still link the old paths. |

<context>
Issue: @.issues/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate/ISSUE.md
Context: @.issues/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate/CONTEXT.md
Research: @.issues/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate/RESEARCH.md

Key reuse points (line numbers from RESEARCH.md):
- @tools/idml_inventory.py — 439 lines; walks spreads, `_bbox_from_element` (line 143), `_extract_annames_from_build_py` (line 282). RENAME + EXTEND.
- @tools/idml_to_dsl.py — `_walk_csr` (line 2566) emits (text, font, fontsize, fcolor) tuples; `_walk_story` (line 2347); `_walk_idml_pageitem_self_ids` (line 2873); `_PAGE_ITEM_LEAF_TAGS` (line 2867); `_assert_conversion_completeness` (line 2896); `_emit_colors_from_xml` (line 881); `_read_paragraph_styles_from_xml` (line 1076); `_pt_to_mm` (line 381).
- @tools/sla_lib/reader.py — `SLADocument` (139 lines), `page_objects()` (line 56), `find_by_anname` (line 62), `iter_colors` (line 108), `iter_styles` (line 113), `iter_itext` (line 125), `frame_text` (line 128).
- @tools/baseline_image_audit.py — `_parse_pdfimages_list` (line 44), `_extract_imageframes_from_build_py` (line 149) — AST-based ImageFrame pattern to copy.
- @tools/text_render_audit.py — `extract_pdf_words` (line 77) returns Counter of normalized words.
- @tools/idml_import_driver.py — `_scaffold_template_dir` (line 187); `--scaffold-only` branch (lines 517–528, plug between 519 and 520).
- @tools/links_export.py — emits `shared/assets/<slug>/links_export.yml` manifest.
- @.claude/skills/idml-import/SKILL.md — 229 lines; banned-phrase block (lines 165–183); SOP P1–P10 (lines 185–217). Source for skill split.

Anchor counts (RESEARCH.md §Calibration baseline) — for sanity-checking, NOT hard-coded:
- IDML: TextFrame=23, Rectangle=25, Polygon=34, Oval=1, GraphicLine=4, Group=14, Image=3, PDF=7, EPS=0; CSR non-empty=36; ParagraphStyle=6; Color=15; Link=10.
- build.py (1135 lines): TextFrame=23, ImageFrame=10, Polygon=16, PolyLine=34, add_para_style=6, add_color=3, Run=104, anname=83.
- template.sla: PAGEOBJECT=83, STYLE=14, COLOR=10, ITEXT=69, PFILE-bearing PAGEOBJECTs=3.
- baseline.pdf words=450; preview.pdf words=450; pdfimages rows=13 across 2 pages.

ISSUE.md sample value `text_runs.total_idml: 437` is illustrative from a different template and MUST NOT be hard-coded.
</context>

<call_sites>
Surfaces grepped: `.github/workflows/`, `Makefile`, `bin/`, `tools/`, `README*`, `docs/`, `.claude/skills/`, `tests/`.

Found:
- `bin/idml-import` (13 lines) — `sys.exit(main(sys.argv[1:]))` of `tools/idml_import_driver.py::main`. NO change needed: `--scaffold-only` flag already exists in the driver argparse. IN SCOPE only as a smoke verification (`bin/idml-import --help` must still parse).
- `tools/idml_import_driver.py:517–528` — `--scaffold-only` branch. IN SCOPE (Task 8: emit inventory between render-gallery and convergence-review).
- `.claude/skills/idml-import/SKILL.md` lines 165–217 — banned phrases + SOP P1–P10. IN SCOPE (Task 11–12: split into scaffold + tune).
- `.claude/skills/idml-import/{asset_policy,classification,inject_protocol,pattern_library,tolerance_protocol}.md` — IN SCOPE (Task 11: copy redistribution).
- `tools/sop_lint.py` — runs on skill output. OUT OF SCOPE: skill SKILL.md prose changes only, no banned-phrase change; verify it still runs by `python3 tools/sop_lint.py --help` smoke.
- `tools/reconcile_build_py.py` — referenced from build.py walker. OUT OF SCOPE for code change; walker calls it as-is.
- No `Makefile`, `.github/workflows/*.yml`, or README references invoke `idml_inventory.py` or the new `inventory_*.py` scripts. No additional invocation sites to update.
</call_sites>

<skills>
Read and follow during execution:
- @.claude/skills/idml-import/SKILL.md — context only (about to be split; do not edit until Task 11).
- @.claude/skills/idml-import/asset_policy.md — P11 embedded/external classification rules drive `assets[].classified`.
</skills>

<commit_format>
Format: conventional with numeric issue prefix.
Pattern: `{id}: {type}({scope}): {description}`
Example: `40: feat(inventory): add deterministic inventory comparator with set/count diff`
Types in use here: feat, refactor, test, docs, chore.
</commit_format>

<tasks>

<task type="auto">
  <name>Task 1: Inventory schema sketch (dataclasses, no extractor logic)</name>
  <files>tools/walkers/__init__.py, tools/walkers/schema.py</files>
  <action>
  Create the `tools/walkers/` package. In `schema.py` define dataclasses (or TypedDicts; pick dataclasses for `asdict()` ergonomics) mirroring exactly the YAML keys in ISSUE.md §Inventory schema: `Inventory`, `TextRunBucket`, `TextFrame`, `ImageFrame`, `PolygonFrame`, `GroupFrame`, `ParagraphStyleEntry`, `ColorEntry`, `AssetEntry`, `WordsBlock`. Add `parse_warnings: list[str] = field(default_factory=list)` at the top-level `Inventory`. Add `source: Literal["idml","manual","inject_yml","build_py"] | None = None` on every frame entry. Add `text_source: Literal["build_py","inject_yml"]` on text-run sub-records. Implement a `to_yaml(inv: Inventory) -> str` helper (use `yaml.safe_dump`, sort_keys=False) and a `from_yaml(text: str) -> Inventory` round-tripper. No I/O, no walking.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 -c "from tools.walkers.schema import Inventory, to_yaml, from_yaml; inv = Inventory(schema_version=1, template='x'); assert from_yaml(to_yaml(inv)).template == 'x'"</automated>
  </verify>
  <done>
  - `tools/walkers/schema.py` defines every key listed in ISSUE.md §Inventory schema
  - Round-trip YAML test passes
  - No imports beyond stdlib + `yaml`
  </done>
</task>

<task type="auto">
  <name>Task 2: IDML walker — rename idml_inventory.py and extend</name>
  <files>tools/walkers/walk_idml_inventory.py, tools/idml_inventory.py</files>
  <action>
  Move `tools/idml_inventory.py` to `tools/walkers/walk_idml_inventory.py` (use `git mv`). Keep `tools/idml_inventory.py` as a 3-line shim: `from tools.walkers.walk_idml_inventory import *  # noqa` for back-compat with any caller. In the moved file, extend the existing `_collect_spread_items`-style traversal to also emit: (a) `text_runs` — call into `tools.idml_to_dsl._walk_csr` (line 2566) per story to harvest `(text, font, fontsize, fcolor, paragraph_style)` tuples; (b) `paragraph_styles` — call `tools.idml_to_dsl._read_paragraph_styles_from_xml` (line 1076); (c) `colors` — call `tools.idml_to_dsl._emit_colors_from_xml` (line 881) in extract-only mode (don't emit, just collect `(name, cmyk)` pairs); (d) `assets` — read `shared/assets/<slug>/links_export.yml` produced by `tools/links_export.py` and copy basenames. Convert bboxes to mm via `tools.idml_to_dsl._pt_to_mm` (line 381). The walker's entry point is `walk_idml(idml_path: Path, slug: str) -> Inventory` (partial — only IDML-side fields populated).
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 -c "
from pathlib import Path
from tools.walkers.walk_idml_inventory import walk_idml
inv = walk_idml(Path('/workspace/originals/26-03-Leporello z-Falz 99x210 6-seitig zweigeteiltes Cover Ordner').glob('*.idml').__next__(), '26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover')
assert sum(b.idml_count for b in inv.text_runs.by_paragraph_style) >= 20, f'expected >=20 idml text-runs, got {sum(b.idml_count for b in inv.text_runs.by_paragraph_style)}'
assert len(inv.paragraph_styles) == 6, f'expected 6 paragraph styles, got {len(inv.paragraph_styles)}'
assert len(inv.colors) == 15, f'expected 15 colors, got {len(inv.colors)}'
print('OK', sum(b.idml_count for b in inv.text_runs.by_paragraph_style), len(inv.paragraph_styles), len(inv.colors))
"</automated>
  </verify>
  <done>
  - `tools/walkers/walk_idml_inventory.py` exists; `tools/idml_inventory.py` reduced to shim
  - Anchor leporello extraction yields 6 paragraph styles, 15 colors, ≥20 text-runs
  - Frame entries carry both mm position and IDML `Self` ID
  </done>
</task>

<task type="auto">
  <name>Task 3: SLA walker — thin wrapper over SLADocument</name>
  <files>tools/walkers/walk_sla.py</files>
  <action>
  Implement `walk_sla(sla_path: Path) -> dict` that returns SLA-side fields keyed for merging into an `Inventory`. Use only `tools.sla_lib.reader.SLADocument`: `page_objects()` for the universe of PAGEOBJECTs, `find_by_anname(anname)` for each frame the IDML side identified, `iter_itext(frame)` count → `sla_storytext_runs`, `frame.get("PFILE")` truthiness → `sla_pfile_present`, `iter_styles()` → `paragraph_styles[].sla_pstyle_present` set, `iter_colors()` → `colors[].sla_color_present` set. No new `lxml` parsing. Return a dict whose keys mirror `Inventory` fields so the orchestrator can merge.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 -c "
from pathlib import Path
from tools.walkers.walk_sla import walk_sla
out = walk_sla(Path('/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/template.sla'))
assert out['pageobject_count'] == 83, out['pageobject_count']
assert out['itext_total'] == 69, out['itext_total']
assert out['pfile_count'] == 3, out['pfile_count']
assert len(out['sla_styles']) == 14, len(out['sla_styles'])
assert len(out['sla_colors']) == 10, len(out['sla_colors'])
print('OK')
"</automated>
  </verify>
  <done>
  - Anchor SLA yields PAGEOBJECT=83, ITEXT total=69, PFILE-bearing=3, STYLE=14, COLOR=10
  - No direct `lxml.etree.parse` calls — only via `SLADocument`
  </done>
</task>

<task type="auto">
  <name>Task 4: PDF walker — reuse existing audit helpers</name>
  <files>tools/walkers/walk_pdf.py</files>
  <action>
  Implement `walk_pdf(preview_pdf: Path, baseline_pdf: Path | None) -> WordsBlock` plus `walk_pdf_images(preview_pdf: Path) -> list[dict]`. For words, call `tools.text_render_audit.extract_pdf_words` (line 77) on both PDFs, materialize `baseline_pdf_count`, `preview_pdf_count`, `missing_from_preview` (baseline_set - preview_set), `extra_in_preview` (preview_set - baseline_set). For images, call `tools.baseline_image_audit._parse_pdfimages_list` (line 44) and group rows by `(page, round(w_in*xppi), round(h_in*yppi))` to collapse jpeg+smask pairs per RESEARCH.md pitfall #4. Each grouped image gets a dict with page, pixel dims, count_of_rows (so the smask pair is one logical image but auditable). Return both objects ready for the orchestrator to drop into `Inventory.words` and `Inventory.frames.image_frames[].pdf_image_present`.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 -c "
from pathlib import Path
from tools.walkers.walk_pdf import walk_pdf, walk_pdf_images
T = Path('/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover')
wb = walk_pdf(T/'preview.pdf', T/'baseline.pdf')
assert wb.preview_pdf_count == 450, wb.preview_pdf_count
assert wb.baseline_pdf_count == 450, wb.baseline_pdf_count
imgs = walk_pdf_images(T/'preview.pdf')
assert len(imgs) >= 5 and len(imgs) <= 13, len(imgs)
print('OK', wb.preview_pdf_count, len(imgs))
"</automated>
  </verify>
  <done>
  - Anchor preview/baseline yield 450 words each
  - Grouped image count collapses smask pairs (≤13 raw rows → ≥5 logical images)
  - No new pdftotext/pdfimages subprocess wrappers — all via existing audit helpers
  </done>
</task>

<task type="auto">
  <name>Task 5: build.py walker — AST-based, mirror baseline_image_audit pattern</name>
  <files>tools/walkers/walk_build_py.py</files>
  <action>
  Implement `walk_build_py(build_py: Path, inject_yml: Path | None) -> dict`. First, if inject.yml exists, call `tools/reconcile_build_py.py <slug>` programmatically (or document the dependency and require it run before extraction — pick programmatic to avoid drift). Parse the reconciled build.py with `ast.parse`. Use the pattern in `tools/baseline_image_audit.py::_extract_imageframes_from_build_py` (line 149) as the template. Walk `ast.Call` nodes for: `add_para_style(...)`, `add_color(...)`, `page.add(TextFrame|ImageFrame|Polygon|Oval|GraphicLine|PolyLine(...))`. For each frame call, harvest kwargs via `ast.literal_eval` of each `keyword.value`; for nested `runs=[Run(...), ...]` walk the inner Call nodes manually (`literal_eval` does NOT handle Call). Per Run, capture `(text, font, fontsize, fcolor, paragraph_style)`. Tag each Run with `text_source='inject_yml'` if its text string also appears in inject.yml's text overrides; else `text_source='build_py'`. Mark every `PolyLine` row with `source='manual'` (no anname). For any kwarg whose `ast.literal_eval` raises, append `f"{file}:{node.lineno}: non-literal kwarg {kw.arg}"` to a `parse_warnings: list[str]` and skip the kwarg. For inline_image_data, store `sha256(payload)` + byte-length only — never the base64 (pitfall #7). Return dict with: `text_runs` (list), `frames` (by kind), `add_para_style_names`, `add_color_names`, `parse_warnings`.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 -c "
from pathlib import Path
from tools.walkers.walk_build_py import walk_build_py
T = Path('/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover')
out = walk_build_py(T/'build.py', None)
assert len(out['frames']['text_frames']) == 23, len(out['frames']['text_frames'])
assert len(out['frames']['image_frames']) == 10, len(out['frames']['image_frames'])
assert sum(1 for f in out['frames'].get('polyline_frames', []) if f.get('source')=='manual') == 34, 'expected 34 manual polylines'
assert len(out['add_para_style_names']) == 6, len(out['add_para_style_names'])
assert len(out['add_color_names']) == 3, len(out['add_color_names'])
assert len(out['text_runs']) >= 90, len(out['text_runs'])  # 104 Run() calls; some may be empty
assert out.get('parse_warnings', []) == [] or all('non-literal' in w for w in out['parse_warnings'])
print('OK', len(out['text_runs']), len(out['frames']['text_frames']))
"</automated>
  </verify>
  <done>
  - Anchor walk emits 23 text frames, 10 image frames, 34 manual PolyLines, 6 para styles, 3 colors, ≥90 text-runs
  - `parse_warnings` either empty or contains only `non-literal kwarg` entries
  - sha256 hash + bytelen present for any inline_image_data; no base64 payload in output
  </done>
</task>

<task type="auto">
  <name>Task 6: Orchestrator — inventory_extract.py</name>
  <files>tools/inventory_extract.py</files>
  <action>
  Implement CLI: `python3 tools/inventory_extract.py --slug <slug> [--templates-dir DIR] [--originals-dir DIR] [--output FILE]`. Defaults: `--templates-dir` resolves to `<repo-root>/../../templates` (i.e. `/workspace/templates` from worktree), `--originals-dir` likewise to `/workspace/originals`. Resolve `<slug>` to `<templates_dir>/<slug>/{build.py,inject.yml,template.sla,preview.pdf,baseline.pdf}` and the IDML under `<originals_dir>/<idml-bundle>/*.idml` (use `meta.yml::source_idml` if present, else first `.idml` matching slug prefix). Call walkers 2–5 in order, merge results into a single `Inventory` dataclass, then join: per `text_runs.by_paragraph_style[]` populate `(idml_count, build_py_count, sla_itext_count, pdf_word_count)` from the respective walkers; per `frames.text_frames[]` join by `anname` (primary) and `(kind, round(mm_pos,1))` (secondary key per RESEARCH.md pitfall #1); per `colors[]` join by name; per `assets[]` collapse composite-AI parents to one row with `referenced_from_frames` aggregated. Emit YAML via `schema.to_yaml` to stdout if `--output -` or default `<templates_dir>/<slug>/SCAFFOLD_INVENTORY.yml`. Exit 0 on success; non-zero on missing files.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 tools/inventory_extract.py --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover --output /tmp/inv-leporello.yml && python3 -c "
import yaml
inv = yaml.safe_load(open('/tmp/inv-leporello.yml'))
assert inv['schema_version'] == 1
assert inv['template'] == '26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover'
assert inv['words']['preview_pdf_count'] == 450
assert inv['words']['baseline_pdf_count'] == 450
assert len([f for f in inv['frames']['text_frames']]) == 23
assert len([f for f in inv['frames']['image_frames']]) == 10
assert len(inv['paragraph_styles']) == 6
assert len(inv['colors']) >= 3
print('OK')
"</automated>
  </verify>
  <done>
  - CLI runs end-to-end on anchor; emits a YAML conforming to schema
  - 23 text_frames, 10 image_frames, 6 paragraph_styles, words=450
  - Composite-AI parents appear once with `referenced_from_frames` ≥1
  </done>
</task>

<task type="auto">
  <name>Task 7: Comparator — inventory_compare.py with exit codes 0/2/3</name>
  <files>tools/inventory_compare.py</files>
  <action>
  Implement CLI: `python3 tools/inventory_compare.py --expected <FILE> --actual <FILE> [--out <FILE>]`. Pure set/count diff. Compute, per top-level section, the set of names/annames present in each side; report `missing` (in expected, not in actual) and `extra` (in actual, not in expected). For numeric `count` fields (`text_runs.by_paragraph_style[].*_count`, `words.preview_pdf_count`, etc.) report deltas. Exit code: `0` if no diffs; `2` if any `missing` (regression — element lost); `3` if all diffs are `extra` only (new content drifted in, no regression). Rows tagged `source: manual` on the actual side with no expected counterpart do NOT trigger exit 3 (RESEARCH.md pitfall #3). Words: report `missing_from_preview` / `extra_in_preview` from the actual side's `words` block. Write `inventory_diff.yml` to `--out` (default: stdout) with sections `missing`, `extra`, `count_deltas`, `summary: {exit_code, ...}`.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 tools/inventory_compare.py --expected /tmp/inv-leporello.yml --actual /tmp/inv-leporello.yml --out /tmp/diff.yml; rc=$?; [ $rc -eq 0 ] || { echo "expected 0 got $rc"; exit 1; }; echo "self-compare OK rc=$rc"</automated>
  </verify>
  <done>
  - Self-comparison of `/tmp/inv-leporello.yml` exits 0 with empty `missing` and `extra`
  - `inventory_diff.yml` contains `summary.exit_code: 0`
  - Tool documented to exit 2 on missing, 3 on extra-only
  </done>
</task>

<task type="auto">
  <name>Task 8: Driver integration — emit inventory in --scaffold-only path</name>
  <files>tools/idml_import_driver.py</files>
  <action>
  In `tools/idml_import_driver.py`'s `--scaffold-only` branch (between line 519 `_run_render_gallery(...)` and line 520 `review = _run_convergence_review(slug)`), insert a call that invokes `tools.inventory_extract` programmatically (import its `main()` or refactor a `build_inventory(slug, ...)` function out of Task 6's CLI). Write output to `templates/<slug>/SCAFFOLD_INVENTORY.yml`. If extraction raises, log a warning but DO NOT fail the scaffold (this is informational in v1; gate enforcement is Stage 2's job). Add `--no-inventory` flag to allow skipping. Keep default behavior change minimal so `bin/idml-import --help` and the non-`--scaffold-only` loop are unaffected.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && python3 tools/idml_import_driver.py --help | grep -q -- '--scaffold-only' && python3 tools/idml_import_driver.py --help | grep -q -- '--no-inventory' && python3 -c "import ast; tree = ast.parse(open('tools/idml_import_driver.py').read()); assert any('inventory_extract' in (ast.dump(n)) for n in ast.walk(tree)), 'inventory_extract not referenced'" && echo "OK"</automated>
  </verify>
  <done>
  - `--help` shows both `--scaffold-only` and the new `--no-inventory`
  - `inventory_extract` is referenced inside the scaffold-only branch
  - Non-scaffold loop path unchanged
  </done>
</task>

<task type="auto">
  <name>Task 9: Calibration — generate and commit SCAFFOLD_INVENTORY.yml for the anchor</name>
  <files>/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml (note: lives in main workspace, not worktree)</files>
  <action>
  Run `python3 tools/inventory_extract.py --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover` to materialize the baseline. Hand-verify by spot-checking: total text_frames=23, image_frames=10, paragraph_styles=6, colors at least covers `Dunkelgrün`, `White`, and the IDML 15-color set, words=450, every image_frame.anname matches one in `links_export.yml`. If any field is empty/None where it should not be, fix the relevant walker before committing. The file is committed at the anchor's path on disk; if the worktree is sparse and does not include the anchor, also commit a symbolic copy at `<worktree>/templates/26-03-leporello-.../SCAFFOLD_INVENTORY.yml` so the repo state shows the file. Verify with `inventory_compare.py --expected <committed> --actual <(extract)` → exit 0.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && BASELINE="/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml" && test -f "$BASELINE" && python3 tools/inventory_extract.py --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover --output /tmp/inv-actual.yml && python3 tools/inventory_compare.py --expected "$BASELINE" --actual /tmp/inv-actual.yml; rc=$?; [ $rc -eq 0 ] || { echo "expected 0 got $rc"; exit 1; }; echo "calibration OK"</automated>
  </verify>
  <done>
  - `SCAFFOLD_INVENTORY.yml` committed at the anchor path
  - Self-compare of freshly-extracted vs committed exits 0
  - Field hand-verification log appended to the file as a leading comment block
  </done>
</task>

<task type="auto">
  <name>Task 10: Mutation tests — confirm gate catches regressions</name>
  <files>tests/test_inventory_gate_mutations.py</files>
  <action>
  Write a pytest-compatible unittest module exercising three mutations on a copy of the anchor build.py in a tmp dir: (M1) delete a `Run(text='...')` entry and re-run inventory_extract+compare → assert exit code 2 and the deleted word appears in `inventory_diff.yml` under `text_runs.missing`. (M2) rename `anname='u514'` → `anname='u514X'` in build.py → assert exit 2 and `u514` reported missing from `frames.image_frames`. (M3) Drop one `add_color('Dunkelgrün', ...)` call → assert exit 2 and `Dunkelgrün` reported missing in `colors`. Use `tmp_path` fixture for pytest and `setUp/tearDown` with `tempfile.TemporaryDirectory` for unittest so BOTH runners pass. The test must not require Scribus rendering — it works directly off the existing baseline preview.pdf/template.sla in the anchor (mutation is build.py only; PDF/SLA stay unchanged, so the gate catches the build.py↔IDML divergence). Tests reference paths via env var `LEPORELLO_DIR` defaulting to `/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover`.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && pytest tests/test_inventory_gate_mutations.py -q && python3 -m unittest discover tests -p 'test_inventory_gate_mutations.py' -v</automated>
  </verify>
  <done>
  - All three mutation scenarios pass under both pytest and unittest discover
  - Each test asserts `exit_code == 2` and the mutated element appears under the correct `missing` section of `inventory_diff.yml`
  </done>
</task>

<task type="auto">
  <name>Task 11: Skill split — duplicate idml-import into idml-scaffold + idml-tune</name>
  <files>.claude/skills/idml-scaffold/SKILL.md, .claude/skills/idml-scaffold/{asset_policy,classification,pattern_library}.md, .claude/skills/idml-tune/SKILL.md, .claude/skills/idml-tune/{inject_protocol,tolerance_protocol,forbidden_paths}.md</files>
  <action>
  Create `.claude/skills/idml-scaffold/` and `.claude/skills/idml-tune/`. Copy sub-docs per the Decisions table: `asset_policy.md`, `classification.md`, `pattern_library.md` into `idml-scaffold/`; `inject_protocol.md`, `tolerance_protocol.md` into `idml-tune/`. Write a new `idml-scaffold/SKILL.md`: scope = "single-shot scaffold producing `templates/<slug>/{build.py, meta.yml, baseline.pdf, SCAFFOLD_INVENTORY.yml}`; may touch `tools/idml_to_dsl.py` only when a structural gate fails". Reference `tools/inventory_extract.py` and `tools/inventory_compare.py` in a Tooling section. Copy banned-phrase block (lines 165–183 of source SKILL.md) and SOP P1–P11. Write a new `idml-tune/SKILL.md`: scope = "per-template iterative tuning of one template's directory; bound to `templates/<slug>/`". Same Tooling section. Add a `## Forbidden paths` section that lists `tools/idml_to_dsl.py`, `tools/sla_lib/**`, and pointers to the converter; also reference `.claude/skills/idml-tune/forbidden_paths.md`. Create `forbidden_paths.md` with the explicit path list and a one-liner suggestion: "`tools/check_stage2_forbidden_paths.py <changed-files>` to enforce" (script itself is OUT OF SCOPE for this PR — RESEARCH.md flagged it as nice-to-have only).
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && test -f .claude/skills/idml-scaffold/SKILL.md && test -f .claude/skills/idml-tune/SKILL.md && grep -q 'inventory_extract.py' .claude/skills/idml-scaffold/SKILL.md && grep -q 'inventory_compare.py' .claude/skills/idml-scaffold/SKILL.md && grep -q 'inventory_compare.py' .claude/skills/idml-tune/SKILL.md && grep -q 'tools/idml_to_dsl.py' .claude/skills/idml-tune/SKILL.md && grep -q 'Forbidden' .claude/skills/idml-tune/SKILL.md && echo OK</automated>
  </verify>
  <done>
  - Both new SKILL.md files exist, reference both inventory CLIs
  - `idml-tune/SKILL.md` lists forbidden paths including the converter and `sla_lib`
  - Sub-docs redistributed per Decisions table
  </done>
</task>

<task type="auto">
  <name>Task 12: SOP rewrite in idml-tune — replace banned-phrase-only iteration discipline with inventory gate</name>
  <files>.claude/skills/idml-tune/SKILL.md</files>
  <action>
  In `idml-tune/SKILL.md`, locate the section corresponding to the source SKILL.md's banned-phrase + P1–P11 block (lines 165–217). Add a NEW preceding step titled `## Per-iteration inventory gate (HARD precondition)` that mandates: every iteration begins by running `python3 tools/inventory_extract.py --slug <slug> --output /tmp/inv-current.yml` and `python3 tools/inventory_compare.py --expected templates/<slug>/SCAFFOLD_INVENTORY.yml --actual /tmp/inv-current.yml --out build/validation/<slug>/inventory_diff.yml`. If exit code != 0, the loop is BLOCKED — the tune agent must revert its last edit and try again. Keep banned phrases (they catch symptoms the inventory diff does not, e.g. cosmetic over-claims), but make them advisory; the inventory gate is the hard signal. Add the explicit Stage 2 blocking rules from CONTEXT.md §Gate behavior verbatim.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && grep -q 'Per-iteration inventory gate' .claude/skills/idml-tune/SKILL.md && grep -q 'exit code != 0' .claude/skills/idml-tune/SKILL.md && grep -q 'inventory_compare.py' .claude/skills/idml-tune/SKILL.md && grep -q 'HARD precondition' .claude/skills/idml-tune/SKILL.md && echo OK</automated>
  </verify>
  <done>
  - `idml-tune/SKILL.md` has a HARD-precondition inventory-gate section preceding the iteration loop
  - Banned phrases retained but marked advisory; inventory diff is the blocking signal
  - CONTEXT.md §Gate behavior Stage 2 rules quoted verbatim
  </done>
</task>

<task type="auto">
  <name>Task 13: Semantics catalog — docs/scribus-sla-attribute-semantics.md</name>
  <files>docs/scribus-sla-attribute-semantics.md</files>
  <action>
  Author a new markdown doc with H2 sections in this order: `## SCALETYPE`, `## FLOP`, `## LINESPMode`, `## HCMS`, `## PRFILE`, `## LOCALSCX`, `## EMBEDDED`, `## Frame rotation (w/h swap)`. Each section captures the empirically tested behavior from the session that motivated this issue. For each: (1) Scribus attribute name + where it appears in SLA (`PAGEOBJECT` attr vs child element vs `STYLE`); (2) the values we have empirically observed and what they mean; (3) the converter file/line where we emit it (`tools/idml_to_dsl.py` or `tools/sla_lib/builder/primitives.py`); (4) at least one "wrong-behavior" anti-example from the past sessions and the resolution. Pull lore from `tools/sla_lib/builder/primitives.py` (line 829 is the PFILE emit) and `tools/idml_to_dsl.py` (LOCALSCX scale base, frame rotation w/h swap). Length target: 250–400 lines. End with a `## How to extend this catalog` block.
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && test -f docs/scribus-sla-attribute-semantics.md && for s in SCALETYPE FLOP LINESPMode HCMS PRFILE LOCALSCX EMBEDDED 'Frame rotation'; do grep -q "## $s" docs/scribus-sla-attribute-semantics.md || { echo "MISSING: $s"; exit 1; }; done && echo OK</automated>
  </verify>
  <done>
  - File exists with all 8 required H2 sections
  - Each section names the SLA attribute and references the converter emit site
  </done>
</task>

<task type="auto">
  <name>Task 14: Deprecate old idml-import skill — redirect stub</name>
  <files>.claude/skills/idml-import/SKILL.md</files>
  <action>
  Replace the contents of `.claude/skills/idml-import/SKILL.md` with a ~30-line redirect stub: explain that the skill has been split, point readers at `.claude/skills/idml-scaffold/SKILL.md` (Stage 1) and `.claude/skills/idml-tune/SKILL.md` (Stage 2). List which sub-docs moved where (per the Decisions table). Note that the sub-docs in `.claude/skills/idml-import/` remain on disk for back-compat reference, but new work should consume them from the new skills. Do NOT delete the sub-docs in this PR. Verify `tools/sop_lint.py --help` still parses (the lint enforcer must not break — it likely globs all skills).
  </action>
  <verify>
    <automated>cd /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate && test -f .claude/skills/idml-import/SKILL.md && grep -q 'idml-scaffold' .claude/skills/idml-import/SKILL.md && grep -q 'idml-tune' .claude/skills/idml-import/SKILL.md && [ $(wc -l < .claude/skills/idml-import/SKILL.md) -lt 60 ] && python3 tools/sop_lint.py --help >/dev/null && echo OK</automated>
  </verify>
  <done>
  - `idml-import/SKILL.md` is a <60-line stub pointing at the two new skills
  - `tools/sop_lint.py --help` still works
  - Original sub-docs left in place for back-compat
  </done>
</task>

</tasks>

<verification>
After all 14 tasks, run final checks:
- `python3 tools/inventory_extract.py --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover --output /tmp/inv.yml` → exit 0
- `python3 tools/inventory_compare.py --expected /workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml --actual /tmp/inv.yml` → exit 0
- `pytest tests/test_inventory_gate_mutations.py -q && python3 -m unittest discover tests -p 'test_inventory_gate_mutations.py' -v` → both green
- `python3 tools/idml_import_driver.py --help` → exits 0 and shows `--scaffold-only` and `--no-inventory`
- `bin/idml-import --help` → exits 0 (smoke; no behavior change)
- `python3 tools/sop_lint.py --help` → exits 0 (skill split didn't break the linter)
- Any pre-existing test suite the repo runs: `pytest tests/ -q` (smoke; tolerate prior-known failures, just no NEW failures introduced)
</verification>

<success_criteria>
Mapped 1:1 to the Acceptance criteria block at top:
- All `SCAFFOLD_INVENTORY.yml` schema fields populate for 26-03 leporello (Tasks 2–6, 9).
- `inventory_compare.py` exits 0 on identical inputs (Task 7, 9).
- Mutation: drop a word → exit 2, word reported (Task 10 M1).
- Mutation: rename an anname → exit 2, anname reported (Task 10 M2).
- Mutation: drop a color → exit 2, color reported (Task 10 M3).
- `.claude/skills/idml-scaffold/SKILL.md` and `.claude/skills/idml-tune/SKILL.md` exist and reference the inventory CLIs (Tasks 11–12).
- `docs/scribus-sla-attribute-semantics.md` exists with all 8 required sections (Task 13).
- `python3 tools/inventory_extract.py --slug ...` runs and emits valid YAML (Task 6).
- `python3 tools/idml_import_driver.py --help` works; existing tests still pass (Task 8, verification block).
- `idml-import/SKILL.md` is a redirect stub (Task 14).
</success_criteria>
