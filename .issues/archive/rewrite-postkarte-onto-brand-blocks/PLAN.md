# Plan: Rewrite Postkarte A6 onto Brand + blocks

<objective>
What this plan accomplishes: Migrate `templates/postkarte-a6-kampagne/build.py` (437 LOC) onto `Brand.gruene_noe()` plus the 5 evidence-driven blocks landed in merged issue #5, judged by visual-diff fidelity vs `templates/postkarte-a6-kampagne/baseline.pdf` and Brand uptake (not by an LOC target).

Why it matters: First template migration in the size-order sequence (Postkarte to Plakat to Zeitung). Postkarte is the smallest non-trivial template, so it has the highest signal-to-noise ratio for proving the Brand+blocks pattern works on a real corpus template. It also forces us to close a known acceptance gap surfaced in #5: `bin/validate --ci` runs `sla_diff --strict` which fails on Brand-injected `extra-layer`/`extra-style` warnings — `tools/sla_diff.py` lacks the allowlist surface that `tools/sla_lib/tests/test_sla_to_dsl.py` already implements at the code level.

Scope IN:
- `tools/sla_diff.py`: add `--allow-brand-extras` flag (filters `extra-layer` / `extra-style` warnings).
- `bin/validate`: pass the new flag when invoking `sla_diff` so `--ci` mode tolerates Brand-injected additions across all three templates.
- `tools/sla_lib/builder/blocks.py`: forward `line_color` and `line_width_pt` kwargs through `PageBackground.for_page()` (the only block-API gap small enough to fix here per ISSUE.md "smallest local fixes" carve-out).
- `shared/ci-defaults.yml`: add the 1 missing PDF-attr key so Postkarte's `extra_pdf_attrs` count drops from 12 to <= 11.
- Regenerate `templates/postkarte-a6-kampagne/build.py` from the existing `template.sla` via the converter; hand-edit the 2 PageBackground polygons into block calls (the only viable block substitutions per RESEARCH.md).
- Rebuild `template.sla` from the new `build.py`, regenerate gallery previews, and prove `bin/validate --ci` is green for ALL three templates.
- Write EXECUTION.md with task-by-task status, achieved LOC (informational), `extra_doc_attrs` and `extra_pdf_attrs` counts, and any P2 follow-ups.

Scope OUT (per ISSUE.md non-goals + RESEARCH.md gap analysis):
- No widening of `Impressum`, `ContactBlock`, `PageNumber`, or `ColumnTextStory` block APIs (P2 follow-ups; file as future issues in EXECUTION.md, do not implement).
- No hand-edits to `templates/postkarte-a6-kampagne/template.sla` — `build.py` is source of truth, `template.sla` regenerates from it.
- No further DSL changes beyond the three small edits listed above.
- No migration of Plakat (issue #7) or Zeitung (issue #8).
- No visual changes to the rendered output (any pixel change beyond `docs/diff-tolerance.md` thresholds means revert).
- No PR open or push — `/issue:ship` runs separately.

No CONTEXT.md — discuss step skipped per user direction. Decisions below derive directly from RESEARCH.md plus user prompt constraints.
</objective>

<context>
Issue: @.issues/rewrite-postkarte-onto-brand-blocks/ISSUE.md
Research: @.issues/rewrite-postkarte-onto-brand-blocks/RESEARCH.md

Key files (executor will read these as needed; do not pre-explore beyond the interfaces below):
@templates/postkarte-a6-kampagne/build.py — current 437-LOC build, source of truth for the regen
@templates/postkarte-a6-kampagne/template.sla — current SLA, input to converter
@templates/postkarte-a6-kampagne/baseline.pdf — pixel oracle for visual_diff
@templates/postkarte-a6-kampagne/diff.yml — visual_diff thresholds (1% mismatch, 5% fuzz)
@templates/postkarte-a6-kampagne/meta.yml — `previews_for_sla` SHA gate
@templates/postkarte-a6-kampagne/assets/ — inline-image asset directory
@tools/sla_to_dsl.py — converter; emits `brand=Brand.gruene_noe()`
@tools/sla_diff.py — structural differ; CLI at lines 1175 to 1209; needs `--allow-brand-extras` flag
@tools/sla_lib/builder/blocks.py — PageBackground at 134 to 202; `for_page()` factory at 187 to 201 needs `line_color`/`line_width_pt` passthrough
@tools/sla_lib/builder/brand.py — `Brand.gruene_noe()` source of injected layer/style names
@tools/sla_lib/tests/test_sla_to_dsl.py — lines 99 to 106 contain the existing code-level allowlist used as the model for the CLI flag
@bin/validate — pipeline that calls `sla_diff --strict`; line 60 to 69
@shared/ci-defaults.yml — `default_pdf_attrs` at line 135 onwards; missing key needs to be added
@docs/diff-tolerance.md — visual-diff tolerance schema and rebaseline workflow

<interfaces>
<!-- Executor: use these contracts directly. Do not re-explore the codebase for them. -->

From tools/sla_diff.py (current CLI; lines 1175 to 1209):
  ap.add_argument("--left", type=Path, required=True)
  ap.add_argument("--right", type=Path, required=True)
  ap.add_argument("--json", nargs="?", const="-", default=None)
  ap.add_argument("--markdown", nargs="?", const="-", default=None)
  ap.add_argument("--strict", action="store_true",
                  help="Exit 1 also when warnings are present (default: exit 1 on critical only).")
  # report.has_critical -> exit 1
  # args.strict and report.has_warning -> exit 1

  # Issue model (from earlier in the same file, used by the allowlist):
  # Each `report.issues[i]` has at minimum: .severity (str), .code (str), .left, .right
  # Codes that need filtering when --allow-brand-extras: "extra-style", "extra-layer"

From tools/sla_lib/tests/test_sla_to_dsl.py:99 to 106 (existing code-level allowlist — model for the flag):
  non_brand_warnings = [
      i for i in report.issues
      if i.severity == sla_diff.SEVERITY_WARNING
      and not (i.code in ("extra-style", "extra-layer"))
  ]

From tools/sla_lib/builder/blocks.py:134 to 202 (current PageBackground surface):
  @dataclass
  class PageBackground:
      color: str = Color.DUNKELGRUEN
      bleed_mm: float = 3.0
      line_color: Optional[str] = None
      line_width_pt: float = 0
      layer: int = 0
      anname: str = "Seitenhintergrund"
      def emit(self) -> Iterable: ...
      @classmethod
      def for_page(cls, page_w_mm: float, page_h_mm: float,
                   color: str = Color.DUNKELGRUEN,
                   bleed_mm: float = 3.0,
                   layer: int = 0) -> "PageBackground":
          return _SizedPageBackground(
              page_w_mm=page_w_mm, page_h_mm=page_h_mm,
              color=color, bleed_mm=bleed_mm, layer=layer,
          )
  # GAP: for_page() does NOT forward line_color or line_width_pt — Task 2 fixes this.

  @dataclass
  class _SizedPageBackground:
      page_w_mm: float
      page_h_mm: float
      color: str = Color.DUNKELGRUEN
      bleed_mm: float = 3.0
      line_color: Optional[str] = None
      line_width_pt: float = 0
      layer: int = 0
      anname: str = "Seitenhintergrund"
      def emit(self) -> Iterable: ...
  # _SizedPageBackground already accepts line_color/line_width_pt — only the factory needs widening.

From bin/validate (lines 60 to 69 — the call site that must pass the new flag):
  if ! python3 tools/sla_diff.py \
      --left "$original" \
      --right "${tdir}template.sla" \
      --json "$OUT_BASE/${tid}-sla_diff.json" \
      --strict > /dev/null; then
      echo "  sla_diff: FAIL"
      EXIT=1
  else
      echo "  sla_diff: PASS"
  fi
  # Add --allow-brand-extras to this invocation (and only this one — sla_diff is also used
  # without --strict elsewhere; do not regress those callers).

From shared/ci-defaults.yml (header comment, lines 14 to 18):
  # Differing pdf-attrs (NOT in defaults): ImageP, InfoString, PicRes, PrintP, RGBMode,
  # RecalcPic, SolidP, UseProfiles2, Version, bleedMarks, useDocBleeds.
  # The 12-key Postkarte residual is one of these; the 11 truly differing keys go in the
  # per-template extra_pdf_attrs override, but one of the 12 is actually constant across
  # all three templates and belongs in default_pdf_attrs. Identify and hoist it (Task 3).

From templates/postkarte-a6-kampagne/build.py:30 to 32 (current explicit layer; needed in regen too):
  layers=[DocumentLayer(name='Hintergrund', visible=True, printable=True, editable=True,
                        flow=True, transparent=1, blend=0, outline=False,
                        layer_color='#000000')]

Page dimensions for Postkarte: 105 mm x 148 mm (A6). Bleed: 3 mm. PageBackground polygon
should match the current build.py:89 to 103 / 216 to 230 polygons exactly: x=-3, y=-3,
w=111, h=154, fill='Dunkelgrün', line_color='Black', line_width_pt=1, layer=0.
</interfaces>
</context>

<commit_format>
Format: conventional with numeric issue prefix
Pattern: `6: {type}({scope}): {description}`
Example: `6: feat(sla_diff): add --allow-brand-extras flag`
Types used in this plan: feat, fix, chore, test, refactor, docs.
</commit_format>

<critical_path>
Task 1 MUST complete before Tasks 4, 5, or 6 can validate green. Without `--allow-brand-extras` wired into `bin/validate`, the rebuilt Postkarte SLA will fail `sla_diff --strict` on 11 brand-injected `extra-layer` / `extra-style` warnings.

Task 2 (PageBackground.for_page widening) is required before Task 5 (the substitution) — Task 5's call shape passes `line_color` / `line_width_pt` through the factory.

Task 3 (ci-defaults hoist) MUST complete before Task 4 (regenerate build.py) — otherwise the regenerated `extra_pdf_attrs` will still have 12 keys and miss the AC.

Tasks 1, 2, 3 are independent of each other and can be implemented in any order, but ALL THREE must land before Task 4. Tasks 4 -> 5 -> 6 -> 7 are strictly sequential.
</critical_path>

<tasks>

<task type="auto">
  <name>Task 1: Add --allow-brand-extras flag to sla_diff and wire it through bin/validate</name>
  <files>tools/sla_diff.py, tools/sla_lib/tests/test_sla_diff.py, bin/validate</files>
  <action>
  GOAL: Make `bin/validate --ci` tolerate Brand-injected `extra-layer` / `extra-style` warnings, mirroring the existing code-level allowlist at `tools/sla_lib/tests/test_sla_to_dsl.py:99 to 106`. This is the hard prerequisite for every later task — without it, the regenerated Postkarte will fail acceptance even when the rendering is byte-clean.

  STEP 1A — `tools/sla_diff.py` CLI surface:
  - In `main()` (the function that defines `argparse` at lines 1175 to 1183), add a new flag:
        ap.add_argument("--allow-brand-extras", action="store_true",
                        help="Filter out 'extra-style' and 'extra-layer' warnings injected by "
                             "Brand profiles (e.g. Brand.gruene_noe()'s ci/* paragraph styles "
                             "and Bilder/Text/Hilfslinien layers). Critical issues are unaffected.")
  - When the flag is set, filter `report.issues` IN-PLACE (or rebuild a filtered list) before the strict-mode check at line 1207, so `report.has_warning` reflects only non-allowlisted warnings. Use the EXACT predicate from `test_sla_to_dsl.py:99 to 106`:
        if args.allow_brand_extras:
            report.issues = [
                i for i in report.issues
                if not (i.severity == SEVERITY_WARNING and i.code in ("extra-style", "extra-layer"))
            ]
            # Recompute has_warning / summary fields if they are cached on the report.
  - Inspect the `Report` dataclass / class definition near the top of `sla_diff.py` to determine whether `has_warning` is a property (recomputes on each access) or a cached attribute. If cached, recompute the relevant counts after filtering. The Markdown/JSON reporters MUST also reflect the filtered list (so `bin/validate`'s JSON dump doesn't show suppressed warnings as failures upstream).
  - Behavior of existing callers: `--allow-brand-extras` defaults to False, so any caller invoking `sla_diff --strict` without the new flag sees IDENTICAL behavior to today.

  STEP 1B — Unit test in `tools/sla_lib/tests/test_sla_diff.py`:
  - Add a new test class or test method that exercises the flag end-to-end via the public `main()` entry point (use `subprocess.run([...])` if the file follows that pattern, or call `sla_diff.main(argv=[...])` directly — match the file's existing style).
  - Test cases (write all three):
    1. `test_allow_brand_extras_filters_extra_style_warning`: build a tiny pair of SLA fixtures (or reuse existing test fixtures) where the right-hand side has a paragraph style not present on the left. Run `main(["--left", LEFT, "--right", RIGHT, "--strict"])` -> expect exit 1. Run with `["--strict", "--allow-brand-extras"]` -> expect exit 0.
    2. `test_allow_brand_extras_filters_extra_layer_warning`: same shape, but for an extra layer.
    3. `test_allow_brand_extras_does_not_suppress_critical`: ensure that critical issues still fail the run even with the flag set.
  - If the test file does not yet have suitable fixtures, generate them inline by calling the existing `Document(...)` builder or by constructing minimal SLA strings — keep the test self-contained.

  STEP 1C — `bin/validate` invocation:
  - Modify the `sla_diff` call at lines 60 to 69 of `bin/validate` to add `--allow-brand-extras` on a new line in the python3 invocation:
        if ! python3 tools/sla_diff.py \
            --left "$original" \
            --right "${tdir}template.sla" \
            --json "$OUT_BASE/${tid}-sla_diff.json" \
            --strict \
            --allow-brand-extras > /dev/null; then
  - Confirm there is no other `sla_diff --strict` invocation in `bin/` that would need the same change (search `bin/` for `sla_diff` — leave non-strict callers alone).

  STEP 1D — VERIFY (do this BEFORE Tasks 4 to 6 touch the SLA): the worktree's main is currently green; after this task `bin/validate --ci` MUST still pass on all three existing templates AS-IS, proving the flag is additive and non-disruptive.

  CONSTRAINT: Do NOT change the default behavior of `sla_diff` — `--strict` without `--allow-brand-extras` MUST exit 1 on the same warnings it does today.
  CONSTRAINT: Do NOT remove the `--strict` flag from `bin/validate`; we still want strict mode for non-Brand warnings.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x -v && bin/validate --ci</automated>
  </verify>
  <done>
  - `tools/sla_diff.py` accepts `--allow-brand-extras`; help text documents the filter.
  - When the flag is set, `extra-style` and `extra-layer` warnings are excluded from `--strict` failure logic AND from the JSON/Markdown report.
  - When the flag is NOT set, behavior is byte-identical to current main.
  - 3 new tests in `test_sla_diff.py` pass: filters extra-style, filters extra-layer, does not suppress critical.
  - `bin/validate --ci` is still green on current main (run before Tasks 4 to 6).
  </done>
  <commit_message>6: feat(sla_diff): add --allow-brand-extras for brand-injected warnings</commit_message>
</task>

<task type="auto">
  <name>Task 2: Forward line_color and line_width_pt through PageBackground.for_page()</name>
  <files>tools/sla_lib/builder/blocks.py, tools/sla_lib/tests/test_blocks.py</files>
  <action>
  GOAL: Close the only block-API gap small enough to ship inside this issue (per ISSUE.md "smallest local fixes" carve-out): `PageBackground.for_page()` does NOT forward `line_color` or `line_width_pt` to the internal `_SizedPageBackground`, even though the dataclass already accepts them. Two-line edit.

  STEP 2A — Edit `tools/sla_lib/builder/blocks.py` lines 187 to 201 (the `for_page` classmethod):
  - Add two kwargs to the signature with the same defaults as the dataclass (`line_color: Optional[str] = None`, `line_width_pt: float = 0`).
  - Forward both kwargs to the `_SizedPageBackground(...)` constructor call.

  After edit, the method should look approximately like:
      @classmethod
      def for_page(cls, page_w_mm: float, page_h_mm: float,
                   color: str = Color.DUNKELGRUEN,
                   bleed_mm: float = 3.0,
                   line_color: Optional[str] = None,
                   line_width_pt: float = 0,
                   layer: int = 0) -> "PageBackground":
          """..."""
          return _SizedPageBackground(
              page_w_mm=page_w_mm, page_h_mm=page_h_mm,
              color=color, bleed_mm=bleed_mm,
              line_color=line_color, line_width_pt=line_width_pt,
              layer=layer,
          )

  STEP 2B — Add unit test in `tools/sla_lib/tests/test_blocks.py`:
  - `test_page_background_for_page_forwards_line_args`: construct `PageBackground.for_page(105, 148, color='Dunkelgrün', line_color='Black', line_width_pt=1)`, then call its `emit()` and inspect the yielded `Polygon`. Assert `polygon.line_color == 'Black'` and `polygon.line_width_pt == 1`.
  - If `test_blocks.py` does not exist, create it. If it exists, add the new test alongside existing PageBackground tests (search for `PageBackground` in the file first).

  CONSTRAINT: Do NOT widen `Impressum`, `ContactBlock`, `PageNumber`, or `ColumnTextStory` block APIs in this task. Those are P2 follow-ups (record them in EXECUTION.md in Task 7).
  CONSTRAINT: Do NOT change `_SizedPageBackground` — it already accepts these kwargs.
  CONSTRAINT: Do NOT change the existing positional/keyword call sites of `PageBackground.for_page()` — the new kwargs are optional with defaults.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_blocks.py -x -v && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `PageBackground.for_page()` accepts and forwards `line_color` and `line_width_pt`.
  - New unit test in `test_blocks.py` passes and asserts both fields propagate to the emitted Polygon.
  - All existing tests under `tools/sla_lib/tests/` still pass.
  </done>
  <commit_message>6: feat(blocks): forward line_color and line_width_pt through PageBackground.for_page</commit_message>
</task>

<task type="auto">
  <name>Task 3: Hoist the missing PDF attribute key into shared/ci-defaults.yml</name>
  <files>shared/ci-defaults.yml</files>
  <action>
  GOAL: Drop Postkarte's `extra_pdf_attrs` count from 12 to <= 11 (criterion in ISSUE.md). RESEARCH.md (paragraph "Residual converter quirks", risk R3) identifies the surplus as one of the 11 keys currently listed as "differing" in the comment block at `shared/ci-defaults.yml:14 to 18`: `ImageP, InfoString, PicRes, PrintP, RGBMode, RecalcPic, SolidP, UseProfiles2, Version, bleedMarks, useDocBleeds`. One of those 11 is actually constant across all three templates and belongs in `default_pdf_attrs`.

  STEP 3A — Identify the surplus key empirically:
  - Run a scratch comparison: regenerate the Postkarte build.py to a tmp path (do NOT overwrite the committed one yet — that's Task 4):
        python3 tools/sla_to_dsl.py templates/postkarte-a6-kampagne/template.sla /tmp/postkarte-task3.py --template-id postkarte-a6-kampagne --assets-dir /tmp/postkarte-task3-assets/
  - Open `/tmp/postkarte-task3.py` and locate the `extra_pdf_attrs={...}` literal in the `Document(...)` call. List the keys.
  - Cross-check by inspecting all three current committed `build.py` files (`templates/{plakat-a1-hochformat,postkarte-a6-kampagne,zeitung-a4-grun}/build.py`) and their `extra_pdf_attrs` literals. The surplus key is the one present in Postkarte's regen-residual whose VALUE matches the corresponding entry in Plakat's and Zeitung's `extra_pdf_attrs` literals (i.e. it is constant across the corpus and was missed by the original ci-defaults audit). RESEARCH.md flags `useDocBleeds` and `bleedMarks` as the most-likely candidates — VERIFY against the literals; do NOT guess.
  - Reference: the file's own header comment at `shared/ci-defaults.yml:14 to 18` lists the 11 names that were declared "differing"; the one that is actually constant goes in defaults.

  STEP 3B — Edit `shared/ci-defaults.yml`:
  - Add the identified key under `default_pdf_attrs:` (around line 135) with the verbatim value from the templates (string, single-quoted to match yaml style — e.g. `'0'` or `'1'`).
  - Update the comment block at lines 14 to 18 to remove the key from the "Differing pdf-attrs" list (since it's no longer differing).

  STEP 3C — Verify by regen:
  - Re-run the converter to a tmp path again and confirm `extra_pdf_attrs` now has 11 or fewer keys.

  CONSTRAINT: Do NOT add a key whose value is NOT identical across all three templates — that would inject incorrect defaults into Plakat or Zeitung. The whole point of `default_*_attrs` is "constant across the corpus".
  CONSTRAINT: Do NOT touch `default_doc_attrs` — `extra_doc_attrs` is already at exactly 23 keys per RESEARCH.md, the criterion is met.
  CONSTRAINT: Do NOT modify any committed `templates/*/build.py` in this task — the regen-and-edit is Task 4.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && python3 tools/sla_to_dsl.py templates/postkarte-a6-kampagne/template.sla /tmp/postkarte-task3.py --template-id postkarte-a6-kampagne --assets-dir /tmp/postkarte-task3-assets/ && python3 -c "import re, ast; src = open('/tmp/postkarte-task3.py').read(); m = re.search(r'extra_pdf_attrs\s*=\s*(\{[^}]*\})', src, re.S); assert m, 'extra_pdf_attrs not found'; d = ast.literal_eval(m.group(1)); print('extra_pdf_attrs has', len(d), 'keys:', sorted(d.keys())); assert len(d) <= 11, 'still ' + str(len(d)) + ' keys, must be <=11'; print('OK')" && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `shared/ci-defaults.yml::default_pdf_attrs` gains 1 key (the identified surplus).
  - Header comment at lines 14 to 18 updated to remove the hoisted key from the "Differing" list.
  - Re-regenerated Postkarte build.py shows `extra_pdf_attrs` with <= 11 keys.
  - All `tools/sla_lib/tests` still pass.
  </done>
  <commit_message>6: chore(ci-defaults): hoist constant pdf attr to drop residual under 12</commit_message>
</task>

<task type="auto">
  <name>Task 4: Regenerate templates/postkarte-a6-kampagne/build.py via converter</name>
  <files>templates/postkarte-a6-kampagne/build.py</files>
  <action>
  GOAL: Replace the 437-LOC committed `templates/postkarte-a6-kampagne/build.py` with a converter-emitted version that uses `brand=Brand.gruene_noe()`, drops 113 to 23 doc-attrs and 34 to 11 pdf-attrs, drops `palette_replaces_ci=True`, and emits `clip_edit=True` rect-collapses.

  STEP 4A — Inspect converter CLI: run `python3 tools/sla_to_dsl.py --help` first if the call signature looks different from RESEARCH.md's documented form. Then run:
        python3 tools/sla_to_dsl.py \
            templates/postkarte-a6-kampagne/template.sla \
            templates/postkarte-a6-kampagne/build.py \
            --template-id postkarte-a6-kampagne \
            --assets-dir templates/postkarte-a6-kampagne/assets/

  Note: This DIRECTLY OVERWRITES the committed build.py. Confirm git status is clean before running so a `git diff` will surface the conversion delta. If the converter complains about an existing assets dir, check `--help` for the right flag — RESEARCH.md confirmed this exact form works against this template.

  STEP 4B — Sanity check the regenerated file:
  - It should parse as Python: `python3 -c "import ast; ast.parse(open('templates/postkarte-a6-kampagne/build.py').read())"` exits 0.
  - It should be ~383 LOC (per RESEARCH.md measurement). LOC is informational only — do not gate on a target.
  - It should contain `brand=Brand.gruene_noe()` in the `Document(...)` call.
  - It should NOT contain `palette_replaces_ci=True`.
  - It should contain `extra_doc_attrs=` with <= 23 keys and `extra_pdf_attrs=` with <= 11 keys (Task 3 already hoisted the surplus pdf key).
  - It should contain at least 2 `Polygon(...)` calls with `clip_edit=True` corresponding to the page0 + page1 Dunkelgrün backgrounds (these are the candidates Task 5 will substitute with `PageBackground`).

  STEP 4C — Add explicit `layers=[DocumentLayer('Hintergrund', ...)]` to the `Document(...)` constructor:
  - The current committed build.py carries this on lines 30 to 32. The converter may or may not emit it (RESEARCH.md notes `DocumentLayer` lines = 0 in regen because Brand auto-injects 4 layers). Even with `--allow-brand-extras` in Task 1, we want the explicit `Hintergrund` layer to remain so the rebuilt SLA still has the named layer the polygons reference.
  - If the regenerated `Document(...)` does NOT already include `layers=[DocumentLayer('Hintergrund', ...)]`, hand-add it using the EXACT kwargs from the current committed line 30 to 32:
        layers=[DocumentLayer(name='Hintergrund', visible=True, printable=True, editable=True,
                              flow=True, transparent=1, blend=0, outline=False,
                              layer_color='#000000')],
  - If `DocumentLayer` is not already imported at the top of the regenerated file, add the import alongside the existing `Document, Page, ...` line.

  STEP 4D — Smoke test the regen builds:
        cd templates/postkarte-a6-kampagne && python3 build.py && cd ../..
  - This regenerates `template.sla` from the new build.py. The SLA should be valid XML.

  CONSTRAINT: Do NOT hand-edit any frame DSL in this task beyond the `layers=` kwarg. Block substitutions are Task 5.
  CONSTRAINT: Do NOT touch `templates/postkarte-a6-kampagne/template.sla` directly. The build.py regenerates it.
  CONSTRAINT: If the regen output mismatches RESEARCH.md's measurements substantially (e.g. emits `palette_replaces_ci=True`, or is over 450 LOC, or has > 23 doc-attrs / > 11 pdf-attrs), STOP and inspect — Task 1 / Task 3 may not have landed correctly.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && python3 -c "import ast; ast.parse(open('templates/postkarte-a6-kampagne/build.py').read())" && grep -q "brand=Brand.gruene_noe()" templates/postkarte-a6-kampagne/build.py && ! grep -q "palette_replaces_ci=True" templates/postkarte-a6-kampagne/build.py && grep -q "DocumentLayer(name='Hintergrund'" templates/postkarte-a6-kampagne/build.py && cd templates/postkarte-a6-kampagne && python3 build.py && cd ../.. && python3 -c "import re, ast; src = open('templates/postkarte-a6-kampagne/build.py').read(); 
[setattr(__import__('builtins'), '_count_'+l, len(ast.literal_eval(re.search(l + r'\s*=\s*(\{[^}]*\})', src, re.S).group(1)))) for l in ('extra_doc_attrs','extra_pdf_attrs')];
print('extra_doc_attrs:', _count_extra_doc_attrs); assert _count_extra_doc_attrs <= 23;
print('extra_pdf_attrs:', _count_extra_pdf_attrs); assert _count_extra_pdf_attrs <= 11;
print('LOC:', len(src.splitlines()))"</automated>
  </verify>
  <done>
  - `templates/postkarte-a6-kampagne/build.py` is the converter-regenerated version.
  - `Document(...)` uses `brand=Brand.gruene_noe()` and an explicit `layers=[DocumentLayer('Hintergrund', ...)]`.
  - No `palette_replaces_ci=True` anywhere in the file.
  - `extra_doc_attrs` <= 23 keys; `extra_pdf_attrs` <= 11 keys.
  - `python3 build.py` succeeds and regenerates a valid `template.sla`.
  </done>
  <commit_message>6: refactor(postkarte): regenerate build.py via converter onto Brand</commit_message>
</task>

<task type="auto">
  <name>Task 5: Substitute the 2 PageBackground polygons with block calls</name>
  <files>templates/postkarte-a6-kampagne/build.py</files>
  <action>
  GOAL: Replace the 2 full-bleed Dunkelgrün `Polygon(...)` calls in the regenerated build.py with `PageBackground.for_page(...)` block calls — the only viable block substitutions for Postkarte per RESEARCH.md (Impressum, ContactBlock, PageNumber, ColumnTextStory all have idiom gaps not in scope here).

  STEP 5A — Locate the two polygons:
  - In the regenerated `build.py`, search for `Polygon(` calls with `fill='Dunkelgrün'` (or `fill=Color.DUNKELGRUEN`) and `clip_edit=True`. There should be exactly 2 — one each on page0 and page1.
  - Each will resemble (line numbers approximate per RESEARCH.md regen at 79 to 89 for page0 and 182 to 192 for page1):
        page0.add(Polygon(
            x_mm=-2.9999999999999942,
            y_mm=-2.9999999999999942,
            w_mm=111.00000000000014,
            h_mm=153.99999999999994,
            layer=0,
            clip_edit=True,
            fill='Dunkelgrün',
            line_color='Black',
            line_width_pt=1,
        ))

  STEP 5B — Replace each with a one-line block call:
        page0.add(PageBackground.for_page(105, 148, color='Dunkelgrün',
                                           line_color='Black', line_width_pt=1))
  And similarly for `page1`. Page dimensions are 105x148 mm (A6); bleed defaults to 3 mm in `PageBackground` so the resulting polygon math will produce x=-3, y=-3, w=111, h=154 — identical to the polygon being replaced (modulo floating-point tail digits, which the SLA writer normalizes). Task 2 widened `for_page()` to forward `line_color` and `line_width_pt` so this call shape works.

  STEP 5C — Add `PageBackground` to the imports near the top of the file:
  - Find the `from sla_lib.builder import ...` block (or equivalent — confirm by reading the import section). Add `PageBackground` to the imported names. If the file imports `from sla_lib.builder import blocks` then use `blocks.PageBackground` instead — match the existing style.
  - Verify the file still parses with `python3 -c "import ast; ast.parse(open(...).read())"`.

  STEP 5D — Rebuild and visual-diff:
        cd templates/postkarte-a6-kampagne && python3 build.py && cd ../..
        python3 tools/visual_diff.py \
            templates/postkarte-a6-kampagne/template.sla \
            --baseline templates/postkarte-a6-kampagne/baseline.pdf \
            --tolerance templates/postkarte-a6-kampagne/diff.yml \
            --dpi 96 \
            --out build/validation/postkarte-a6-kampagne/
  - Should exit 0. RESEARCH.md measured per-page mismatch ~0.0001%, well under the 1% threshold. If mismatch jumps after this task, the polygon-coords math in `PageBackground` regressed — REVERT this task and file a P2 follow-up. **Visual-diff fidelity is the correctness gate; any pixel change beyond `docs/diff-tolerance.md` thresholds means revert.**

  CONSTRAINT: Do NOT touch frames OTHER than the 2 Dunkelgrün full-bleed polygons. RESEARCH.md is explicit: of 17 frames, only 2 are block-substitutable; everything else stays primitive.
  CONSTRAINT: Do NOT widen `Impressum`, `ContactBlock`, `PageNumber`, or `ColumnTextStory` blocks to "make them fit" — those are P2 follow-ups (recorded in EXECUTION.md in Task 7).
  CONSTRAINT: Do NOT hand-edit `template.sla` — it regenerates from build.py.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && python3 -c "import ast; ast.parse(open('templates/postkarte-a6-kampagne/build.py').read())" && grep -q "PageBackground" templates/postkarte-a6-kampagne/build.py && cd templates/postkarte-a6-kampagne && python3 build.py && cd ../.. && python3 tools/visual_diff.py templates/postkarte-a6-kampagne/template.sla --baseline templates/postkarte-a6-kampagne/baseline.pdf --tolerance templates/postkarte-a6-kampagne/diff.yml --dpi 96 --out build/validation/postkarte-a6-kampagne/</automated>
  </verify>
  <done>
  - `templates/postkarte-a6-kampagne/build.py` imports and uses `PageBackground.for_page(...)` for both page0 and page1 backgrounds.
  - The 2 raw `Polygon(...)` calls with `fill='Dunkelgrün'` and `clip_edit=True` are removed.
  - `python3 build.py` rebuilds `template.sla` cleanly.
  - `tools/visual_diff.py` exits 0 against the committed `baseline.pdf` with `diff.yml` tolerance.
  </done>
  <commit_message>6: refactor(postkarte): substitute PageBackground block for full-bleed polygons</commit_message>
</task>

<task type="auto">
  <name>Task 6: Rebuild gallery, run full validation, regenerate previews_for_sla SHA</name>
  <files>templates/postkarte-a6-kampagne/template.sla, templates/postkarte-a6-kampagne/page-01.png, templates/postkarte-a6-kampagne/page-02.png, templates/postkarte-a6-kampagne/preview.pdf, templates/postkarte-a6-kampagne/meta.yml</files>
  <action>
  GOAL: Run the full validation pipeline and regenerate the gallery artifacts so the stale-preview gate (`tools/check_stale_previews.py:106 to 118`) doesn't block the ship. After this task, ALL THREE templates must be `bin/validate --ci` green.

  STEP 6A — Regenerate gallery previews:
        bin/render-gallery
  This regenerates `page-01.png`, `page-02.png`, `preview.pdf`, and updates `meta.yml::previews_for_sla` to the new SHA256 of `template.sla`. If `bin/render-gallery` does not exist or has a different name, search `bin/` for the gallery-render entrypoint (the project carries `bin/render-gallery`, `bin/render`, or similar — RESEARCH.md uses `bin/render-gallery`).

  STEP 6B — Run the structural diff explicitly to confirm allowlist behavior:
        python3 tools/sla_diff.py \
            --left templates/postkarte-a6-kampagne/original-sla-path \
            --right templates/postkarte-a6-kampagne/template.sla \
            --strict \
            --allow-brand-extras
  - Replace `original-sla-path` with the `original_sla` path from `templates/postkarte-a6-kampagne/meta.yml`. This must exit 0.
  - For comparison, run WITHOUT `--allow-brand-extras` and WITH `--strict` — exit code SHOULD be 1 (because the brand extras are still present, just allowlisted). This proves the allowlist is doing real work.

  STEP 6C — Full validation pipeline:
        bin/validate --ci
  All three templates (plakat, postkarte, zeitung) must report `sla_diff: PASS` and `visual_diff: PASS`. Exit code must be 0.

  STEP 6D — CI compliance check:
        python3 tools/check_ci.py templates/postkarte-a6-kampagne/template.sla
  Exit 0.

  STEP 6E — Stale-preview gate:
        python3 tools/check_stale_previews.py
  (or the equivalent invocation if it takes a template path argument). Exit 0.

  STEP 6F — Test suite:
        python3 -m pytest tools/sla_lib/tests -x

  CONSTRAINT: Do NOT skip `bin/render-gallery` — without it, `meta.yml::previews_for_sla` will not match the rebuilt SLA's SHA and the stale-preview gate will fail.
  CONSTRAINT: Do NOT hand-edit `meta.yml::previews_for_sla` — `bin/render-gallery` updates it as a side-effect.
  CONSTRAINT: If any of the three templates (Plakat, Postkarte, Zeitung) reports `visual_diff: FAIL` or `sla_diff: FAIL` after Task 1 to 5 changes, STOP and diagnose — the brand-extras allowlist must NOT mask non-brand warnings.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && bin/render-gallery && bin/validate --ci && python3 tools/check_ci.py templates/postkarte-a6-kampagne/template.sla && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `bin/render-gallery` regenerates page PNGs, preview.pdf, and updates `meta.yml::previews_for_sla` SHA.
  - `bin/validate --ci` exits 0 with `sla_diff: PASS` and `visual_diff: PASS` for plakat, postkarte, AND zeitung.
  - `tools/check_ci.py templates/postkarte-a6-kampagne/template.sla` exits 0.
  - `pytest tools/sla_lib/tests -x` exits 0.
  - Stale-preview gate is clean (`previews_for_sla` SHA matches rebuilt `template.sla`).
  </done>
  <commit_message>6: chore(postkarte): rebuild gallery and validate pipeline green</commit_message>
</task>

<task type="auto">
  <name>Task 7: Acceptance check + write EXECUTION.md</name>
  <files>.issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md</files>
  <action>
  GOAL: Verify all 6 ISSUE.md acceptance criteria against produced artifacts, write EXECUTION.md, and file the P2 follow-ups discovered during the migration.

  STEP 7A — Acceptance walk-through. For each AC in `ISSUE.md::Acceptance criteria`, record PASS/FAIL with concrete evidence (command run + exit code + relevant output excerpt). The 6 ACs are:
  1. `tools/visual_diff.py` clean against `templates/postkarte-a6-kampagne/baseline.pdf` (within `docs/diff-tolerance.md`). Evidence: rerun the visual_diff command from Task 5 step 5D.
  2. `pytest tools/sla_lib/tests -x` green. Evidence: the Task 6 verify run.
  3. `bin/validate --ci` green for ALL three templates. Evidence: the Task 6 verify run.
  4. `tools/check_ci.py templates/postkarte-a6-kampagne` clean. Evidence: the Task 6 verify run.
  5. `extra_doc_attrs` <= 23 keys. Evidence: count from Task 4 verify.
  6. `extra_pdf_attrs` <= 11 keys. Evidence: count from Task 4 verify.

  STEP 7B — Measure achieved LOC for the new `templates/postkarte-a6-kampagne/build.py` (informational only):
        wc -l templates/postkarte-a6-kampagne/build.py
  RESEARCH.md projects ~363 to 366 LOC after block substitution + explicit Hintergrund layer. Record the actual number; do not gate on it.

  STEP 7C — Write `.issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md` with this structure:

      # Execution — Rewrite Postkarte A6 onto Brand + blocks

      **Issue:** rewrite-postkarte-onto-brand-blocks (id 6)
      **Status:** complete | partial | blocked
      **Executed:** YYYY-MM-DD

      ## Tasks

      - [x] Task 1: Add --allow-brand-extras flag to sla_diff and wire through bin/validate
      - [x] Task 2: Forward line_color / line_width_pt through PageBackground.for_page()
      - [x] Task 3: Hoist missing PDF attribute key into shared/ci-defaults.yml
        - Hoisted key: `<KEY_NAME> = '<VALUE>'`
      - [x] Task 4: Regenerate templates/postkarte-a6-kampagne/build.py via converter
      - [x] Task 5: Substitute the 2 PageBackground polygons with block calls
      - [x] Task 6: Rebuild gallery, run full validation, regenerate previews_for_sla SHA
      - [x] Task 7: Acceptance check + write EXECUTION.md

      ## Acceptance criteria

      | # | Criterion | Status | Evidence |
      |---|---|---|---|
      | 1 | visual_diff clean | PASS | `tools/visual_diff.py ... -> exit 0; max mismatch <X>%` |
      | 2 | pytest tools/sla_lib/tests -x | PASS | `<count> tests passing` |
      | 3 | bin/validate --ci | PASS | plakat/postkarte/zeitung all PASS |
      | 4 | check_ci.py | PASS | exit 0 |
      | 5 | extra_doc_attrs <= 23 | PASS | <count> keys |
      | 6 | extra_pdf_attrs <= 11 | PASS | <count> keys |

      ## Metrics

      - LOC: <before> -> <after> (informational; not an AC)
      - extra_doc_attrs: <before-count> -> <after-count>
      - extra_pdf_attrs: <before-count> -> <after-count>
      - Block substitutions: 2 (PageBackground page0 + page1)
      - Brand uptake: brand=Brand.gruene_noe(), palette_replaces_ci removed

      ## P2 follow-ups (file as future issues, do NOT implement here)

      1. **Widen `Impressum` block to support prefix-bold-Run idiom.** Current API emits a single Run; all three production templates (Plakat, Postkarte, Zeitung) carry an "Impressum:" Bold prefix Run that the block can't represent. Proposal: add `prefix_text=`, `prefix_font=` kwargs OR a `runs=` override.
      2. **Widen `ContactBlock` block to support `separator='breakline'`, `default_style_attrs=`, `vertical_text_align=`, and per-Run `fshade=`.** Postkarte's contact frame uses all four; the current block fits the defaulted shape only.
      3. **Audit `extra_pdf_attrs` for further hoist candidates** once Plakat and Zeitung migrate (issue #7, #8). The 11-key residual may shrink further once we see what's actually constant across all three regenerations.
      4. **Optional: widen `_SizedPageBackground` to accept `anname=` override.** Current default 'Seitenhintergrund' — fine for Postkarte but might collide with multi-frame layered backgrounds in Zeitung. Defer until issue #8 surfaces it.

      ## Notes

      - `--allow-brand-extras` is now the canonical mechanism for tolerating Brand-injected `extra-style` / `extra-layer` warnings in `bin/validate`. Future template migrations (Plakat #7, Zeitung #8) will rely on this flag.
      - The Postkarte rewrite is mostly mechanical: 95% of the work is the converter-regen; hand edits are surgical (2 block substitutions + 1 layer kwarg).

  Replace `<KEY_NAME>`, `<VALUE>`, `<count>`, `<before>`, `<after>` placeholders with actual values from Tasks 1 to 6.

  STEP 7D — Final commit. Stage EXECUTION.md plus any artifacts modified by `bin/render-gallery` (page-01.png, page-02.png, preview.pdf, meta.yml) and commit with the message below. The orchestrator will commit; this task just stages and writes EXECUTION.md.

  CONSTRAINT: Do NOT push or open a PR. The user runs `/issue:ship` separately.
  CONSTRAINT: If any AC in Step 7A is FAIL, mark Status as `blocked`, leave the failed checkbox unchecked, and surface the failure in the EXECUTION.md notes — do NOT pretend the issue is complete.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks && test -f .issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md && grep -q "Acceptance criteria" .issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md && grep -q "P2 follow-ups" .issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md && bin/validate --ci && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `.issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md` exists.
  - All 6 ACs are recorded with PASS/FAIL status and evidence.
  - LOC, doc-attrs count, pdf-attrs count are recorded as numbers (not estimates).
  - At least 3 P2 follow-ups are filed (Impressum widening, ContactBlock widening, post-#7/#8 ci-defaults audit).
  - `bin/validate --ci` and `pytest tools/sla_lib/tests -x` are green.
  </done>
  <commit_message>6: docs(postkarte): record execution and acceptance evidence</commit_message>
</task>

</tasks>

<verification>
After all tasks complete, run the final battery (this is also the body of the Task 6 + Task 7 verifies, repeated here as a single-shot reproducer for the reviewer):

```
cd /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks
python3 -m pytest tools/sla_lib/tests -x
python3 tools/check_ci.py templates/postkarte-a6-kampagne/template.sla
python3 tools/visual_diff.py \
    templates/postkarte-a6-kampagne/template.sla \
    --baseline templates/postkarte-a6-kampagne/baseline.pdf \
    --tolerance templates/postkarte-a6-kampagne/diff.yml \
    --dpi 96 \
    --out build/validation/postkarte-a6-kampagne/
bin/validate --ci
```

All five must exit 0. The visual_diff per-page mismatch must be under the 1% threshold defined in `templates/postkarte-a6-kampagne/diff.yml`.
</verification>

<success_criteria>
Maps 1:1 to the 6 acceptance criteria in ISSUE.md:

1. `tools/visual_diff.py` clean against `templates/postkarte-a6-kampagne/baseline.pdf` within `docs/diff-tolerance.md` thresholds.
2. `pytest tools/sla_lib/tests -x` green.
3. `bin/validate --ci` green for ALL three templates (plakat, postkarte, zeitung) — enabled by Task 1's `--allow-brand-extras` flag.
4. `tools/check_ci.py templates/postkarte-a6-kampagne` clean.
5. New `extra_doc_attrs` in `templates/postkarte-a6-kampagne/build.py` contains <= 23 keys.
6. New `extra_pdf_attrs` in `templates/postkarte-a6-kampagne/build.py` contains <= 11 keys (enabled by Task 3's ci-defaults hoist).

Plus: `templates/postkarte-a6-kampagne/build.py` uses `brand=Brand.gruene_noe()` and at least 2 `PageBackground.for_page(...)` block calls; EXECUTION.md records achieved LOC, all 6 AC outcomes, and the P2 follow-ups.
</success_criteria>
