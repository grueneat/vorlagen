# Plan: Rewrite Plakat A1 onto Brand + blocks

<objective>
What this plan accomplishes: Migrate `templates/plakat-a1-hochformat/build.py` (235 LOC) onto `Brand.gruene_noe()` plus the 5 evidence-driven blocks landed in merged issue #5, judged by visual-diff fidelity vs `templates/plakat-a1-hochformat/baseline.pdf` and Brand uptake (not by an LOC target).

Why it matters: Second template migration in the size-order sequence (Postkarte #6 -> Plakat #7 -> Zeitung #8). Plakat is the smallest payoff of the three migrations because it has 0 Polygons, 0 chains, 0 page-number frames, and 1 Impressum frame whose two API gaps (rotation_deg + Bold-prefix Run) put block substitution out of scope here. Its value is two-fold: (a) prove the regen-and-ship pattern works on a template with zero block-substitution wins, and (b) close a hard `bin/validate --ci` gap surfaced by Plakat alone — `--allow-brand-extras` filters `extra-style` and `extra-layer` warnings (added in #6) but NOT `extra-color`. Plakat's original SLA carries only 5 of 7 brand colors (no Hellgrün, no Magenta), so the rebuilt SLA produces 2 unfiltered `extra-color` warnings that fail strict mode. This blocker MUST be fixed in this issue.

Scope IN:
- `tools/sla_diff.py`: extend `--allow-brand-extras` to also filter `extra-color` warnings whose color name is one of the 7 brand colors from `shared/ci.yml`.
- `tools/sla_lib/tests/test_sla_diff.py`: add unit tests for the new `extra-color` filter behavior (positive + negative cases).
- `tools/sla_lib/tests/test_sla_to_dsl.py::PlakatRoundTrip`: extend the round-trip test's allowlist to filter `extra-style` / `extra-layer` / `extra-color` warnings injected by Brand, mirroring the Postkarte pattern from #6 commit `1ebe8ef`.
- Regenerate `templates/plakat-a1-hochformat/build.py` from the existing `template.sla` via the converter; **zero hand edits** (RESEARCH.md confirms all 4 numeric ACs are met by raw converter output).
- Rebuild `template.sla` from the new `build.py`, regenerate gallery previews, and prove `bin/validate --ci` is green for ALL three templates.
- Write EXECUTION.md with task-by-task status, achieved LOC (informational, expected 198), `extra_doc_attrs` count (expected 23), `extra_pdf_attrs` count (expected 11), and P2 follow-ups discovered.

Scope OUT (per ISSUE.md non-goals + RESEARCH.md gap analysis + user prompt constraints):
- No widening of the `Impressum` block API. Both gaps surfaced by Plakat (`rotation_deg=` and `prefix_text=`/`prefix_font=`) are P2 follow-ups for a separate DSL widening issue. Plakat's Impressum stays as a primitive `TextFrame`.
- No widening of `ContactBlock`, `PageNumber`, or `ColumnTextStory` block APIs. Plakat has zero candidates for these blocks.
- No hand-edits to the regenerated `templates/plakat-a1-hochformat/build.py`. RESEARCH.md verified that the raw converter output meets all 4 numeric ACs (`extra_doc_attrs=23`, `extra_pdf_attrs=11`, `Brand.gruene_noe()` emitted, `palette_replaces_ci` removed) with zero hand edits.
- No hand-edit of an explicit `layers=[DocumentLayer('Hintergrund', ...)]` into the regen. The Postkarte rewrite added it as belt-and-suspenders, but `--allow-brand-extras` (extended in Task 1) handles the brand-injected extra-layer warnings; Plakat demonstrates the cleaner pattern.
- No hand-edits to `templates/plakat-a1-hochformat/template.sla` — `build.py` is source of truth, `template.sla` regenerates from it.
- No further DSL changes beyond the small `--allow-brand-extras` extension.
- No migration of Postkarte (#6) or Zeitung (#8). The Postkarte branch is currently in review (PR #14); Plakat is stacked on it and rebases onto main once #14 merges.
- No visual changes to the rendered output (any pixel change beyond `templates/plakat-a1-hochformat/diff.yml` thresholds means revert).
- No PR open or push. The orchestrator runs `/issue:ship` separately.
- LOC target: ISSUE.md states `<= 180` is **informational only** per user direction. Achieved is 198; do not gate on the 180 number. RESEARCH.md proves 198 is the realistic floor without widening blocks.

No CONTEXT.md — discuss step skipped per user direction. Decisions below derive directly from RESEARCH.md plus user prompt constraints.
</objective>

<context>
Issue: @.issues/rewrite-plakat-onto-brand-blocks/ISSUE.md
Research: @.issues/rewrite-plakat-onto-brand-blocks/RESEARCH.md

Pattern reference (just-shipped Postkarte rewrite, PR #14):
@/root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks/.issues/rewrite-postkarte-onto-brand-blocks/PLAN.md
@/root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks/.issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md

Stacking note: This branch (`issue/rewrite-plakat-onto-brand-blocks`) is stacked on `issue/rewrite-postkarte-onto-brand-blocks` (PR #14). The Postkarte changes (sla_diff `--allow-brand-extras` flag, `bin/validate` wiring, PageBackground.for_page widening, ci-defaults hoist) are ALREADY present on this branch as base. This plan extends that work, not reintroduces it.

Key files (executor will read these as needed; do not pre-explore beyond the interfaces below):
@templates/plakat-a1-hochformat/build.py — current 235-LOC build, source of truth for the regen
@templates/plakat-a1-hochformat/template.sla — current SLA, input to converter
@templates/plakat-a1-hochformat/baseline.pdf — pixel oracle for visual_diff (research-confirmed clean against regen)
@templates/plakat-a1-hochformat/diff.yml — visual_diff thresholds (1% mismatch, 5% fuzz)
@templates/plakat-a1-hochformat/meta.yml — `previews_for_sla` SHA gate
@templates/plakat-a1-hochformat/assets/ — inline-image asset directory
@plakat-a1-hochformat-original.sla — pristine source SLA (used by PlakatRoundTrip's `_diff_clean`)
@tools/sla_to_dsl.py — converter; emits `brand=Brand.gruene_noe()`
@tools/sla_diff.py — structural differ; CLI at lines 1175 to 1213; current `--allow-brand-extras` filter at 1190 to 1194 needs `extra-color` extension
@tools/sla_lib/tests/test_sla_diff.py — `AllowBrandExtrasTests` class at line 730 (existing tests for extra-style + extra-layer; mirror pattern for extra-color)
@tools/sla_lib/tests/test_sla_to_dsl.py — `PlakatRoundTrip` class at lines 119 to 141 (allowlist needs extending); Postkarte's already-merged allowlist at lines 62 to 78 is the reference pattern
@bin/validate — already passes `--allow-brand-extras` to sla_diff (from #6); no edit needed in this issue
@shared/ci.yml — brand color names at lines 19 to 45 (the 7-tuple Black, White, Registration, Dunkelgrün, Hellgrün, Gelb, Magenta)

<interfaces>
<!-- Executor: use these contracts directly. Do not re-explore the codebase for them. -->

From tools/sla_diff.py CLI (lines 1180 to 1194; the filter that needs extending):

  ap.add_argument("--strict", action="store_true",
                  help="Exit 1 also when warnings are present (default: exit 1 on critical only).")
  ap.add_argument("--allow-brand-extras", action="store_true",
                  help="Filter out 'extra-style' and 'extra-layer' warnings injected by "
                       "Brand profiles (e.g. Brand.gruene_noe()'s ci/* paragraph styles "
                       "and Bilder/Text/Hilfslinien layers). Critical issues are unaffected.")
  args = ap.parse_args(argv)
  report = diff(args.left, args.right)

  if args.allow_brand_extras:
      report.issues = [
          i for i in report.issues
          if not (i.severity == SEVERITY_WARNING and i.code in ("extra-style", "extra-layer"))
      ]

Task 1 extends this predicate to ALSO drop extra-color warnings whose i.right (color name) is in the brand 7-tuple.

From tools/sla_diff.py palette-comparison call sites (lines 1100 to 1102) and `_compare_palette` (lines 985 to 996):
- `_compare_palette(left_doc, right_doc, "COLOR", "NAME", report.issues, SEVERITY_WARNING)` emits `extra-color` Issues at WARNING severity.
- Each such Issue's `right` field carries the color NAME (e.g. 'Hellgrün' or 'Magenta'). Source: `Issue(severity, f"extra-{tag.lower()}", ..., right=name)`.

From tools/sla_lib/tests/test_sla_diff.py existing AllowBrandExtrasTests (line 730):

  class AllowBrandExtrasTests(unittest.TestCase):
      def setUp(self):
          self.tmp = Path(tempfile.mkdtemp())

      def _write_sla_with_extra_style(self, name, extra_style_name): ...
      def _write_sla_with_extra_layer(self, name, extra_layer_name): ...

      def test_allow_brand_extras_filters_extra_style_warning(self): ...
      def test_allow_brand_extras_filters_extra_layer_warning(self): ...
      def test_allow_brand_extras_does_not_suppress_critical(self): ...

Task 1 adds an analogous `_write_sla_with_extra_color(...)` helper and 2 tests: one positive (brand-color name -> filtered), one negative (non-brand color name -> still fails strict mode).

From tools/sla_lib/tests/test_sla_to_dsl.py PostkarteRoundTrip (lines 62 to 78 — pattern to mirror):

  def test_diff_against_original_clean(self):
      sla = _run_build(self.TEMPLATE_DIR / "build.py")
      report = _diff_clean(self.ORIGINAL, sla)
      self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                       msg=f"critical issues: ...")
      non_brand_warnings = [
          i for i in report.issues
          if i.severity == sla_diff.SEVERITY_WARNING
          and not (i.code in ("extra-style", "extra-layer"))
      ]
      self.assertEqual(non_brand_warnings, [], msg=f"unexpected warning issues: ...")

From tools/sla_lib/tests/test_sla_to_dsl.py PlakatRoundTrip (lines 119 to 141 — what needs editing):

  class PlakatRoundTrip(unittest.TestCase):
      TEMPLATE_DIR = ROOT / "templates" / "plakat-a1-hochformat"
      ORIGINAL = ROOT / "plakat-a1-hochformat-original.sla"

      def test_diff_against_original_clean(self):
          sla = _run_build(self.TEMPLATE_DIR / "build.py")
          report = _diff_clean(self.ORIGINAL, sla)
          self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0, ...)
          self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0, ...)   # this fails after Task 2

      def test_soft_hyphens_byte_preserved(self):                              # DO NOT touch (independent)
          ...

From shared/ci.yml (lines 19 to 45 — the canonical 7-color brand palette):

  colors:
    Black: ...
    White: ...
    Registration: ...
    Dunkelgrün: ...
    Hellgrün: ...
    Gelb: ...
    Magenta: ...

The 7-tuple of names: ("Black", "White", "Registration", "Dunkelgrün", "Hellgrün", "Gelb", "Magenta").

Plakat-specific facts (from RESEARCH.md, do not re-derive):
- Original SLA has 5 of 7 brand colors (Black, Dunkelgrün, Gelb, Registration, White).
- Brand.gruene_noe() injects all 7 -> rebuilt SLA produces 2 unfiltered extra-color warnings: 'Hellgrün' and 'Magenta'.
- PTYPE counts: 6 TextFrames, 3 ImageFrames, 0 Polygons. No PageBackground substitution candidate.
- 0 link_to chains, 0 var='pgno' frames, 0 contact frames.
- Single Impressum frame at right margin: rotation_deg=270 + Bold-prefix Run -> two API gaps -> stays primitive.
- Regenerated build.py (zero hand edits) measures: 198 LOC, extra_doc_attrs=23, extra_pdf_attrs=11, brand=Brand.gruene_noe() emitted, palette_replaces_ci=False, layers default to Brand-supplied stack (no explicit DocumentLayer).
- visual_diff against committed baseline.pdf: exit 0 (verified live in research).
- Page dimensions: 594 mm x 841 mm (A1 portrait). Bleed: 3 mm.

Converter CLI (research-verified working invocation):

  python3 tools/sla_to_dsl.py \
      templates/plakat-a1-hochformat/template.sla \
      templates/plakat-a1-hochformat/build.py \
      --template-id plakat-a1-hochformat \
      --assets-dir templates/plakat-a1-hochformat/assets/
</interfaces>
</context>

<commit_format>
Format: conventional with numeric issue prefix (per `.issues/config.yaml::commits.prefix=true` + `commits.format=conventional`)
Pattern: `7: {type}({scope}): {description}`
Example: `7: feat(sla_diff): extend --allow-brand-extras to extra-color warnings`
Types used in this plan: feat, refactor, test, chore, docs.
</commit_format>

<critical_path>
Strict ordering: Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5. DO NOT reorder.

Task 1 MUST complete before Task 2's regenerate-and-rebuild can validate green via `bin/validate --ci`. Without the `extra-color` filter extension, the rebuilt Plakat SLA will fail `sla_diff --strict --allow-brand-extras` on 2 unfiltered warnings (`extra-color: Hellgrün`, `extra-color: Magenta`) — RESEARCH.md proved this live.

Task 3 MUST complete before Task 4's `pytest tools/sla_lib/tests` step. Without the `PlakatRoundTrip.test_diff_against_original_clean` allowlist update, the round-trip test fails with up to 13 unfiltered brand-additive warnings (3 extra-layer + 8 extra-style + 2 extra-color).

Task 3 also requires Task 2's regenerated build.py to be on disk before its test command runs (the test runs the committed build.py, not a tmp path). The strict serial order above is the safest pipeline.
</critical_path>

<tasks>

<task type="auto">
  <name>Task 1: Extend --allow-brand-extras to filter extra-color warnings for brand colors</name>
  <files>tools/sla_diff.py, tools/sla_lib/tests/test_sla_diff.py</files>
  <action>
  GOAL: Make `--allow-brand-extras` ALSO drop `extra-color` warnings whose color name is one of the 7 brand colors. Hard prerequisite for every later task — without it, the regenerated Plakat will fail `bin/validate --ci` even when rendering is byte-clean. RESEARCH.md verified live that current main produces 2 unfiltered warnings (`extra-color: Hellgrün`, `extra-color: Magenta`) when running sla_diff against the rebuilt Plakat SLA.

  STEP 1A — Edit `tools/sla_diff.py`:

  Add a module-level constant near the top of the file (alongside other CLI-related constants — search for `SEVERITY_WARNING =` or `SEVERITY_CRITICAL =` and place this 7-tuple near them):

      _BRAND_COLOR_NAMES = (
          "Black", "White", "Registration",
          "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
      )
      # Source: shared/ci.yml::colors. Hardcoded here (rather than YAML-loaded) to keep
      # tools/sla_diff.py free of yaml imports. Out-of-sync risk is low — these 7 names
      # are the canonical brand palette.

  Then edit the `--allow-brand-extras` filter at lines 1190 to 1194 to include `extra-color` for brand color names. The filter becomes:

      if args.allow_brand_extras:
          report.issues = [
              i for i in report.issues
              if not (
                  i.severity == SEVERITY_WARNING and (
                      i.code in ("extra-style", "extra-layer")
                      or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
                  )
              )
          ]

  Update the help text on the `--allow-brand-extras` argparse line (1183 to 1186) to document the extra-color extension:

      ap.add_argument("--allow-brand-extras", action="store_true",
                      help="Filter out 'extra-style', 'extra-layer', and brand-color "
                           "'extra-color' warnings injected by Brand profiles (e.g. "
                           "Brand.gruene_noe()'s ci/* paragraph styles, Bilder/Text/"
                           "Hilfslinien layers, and full 7-color palette). Only "
                           "extra-color warnings whose color NAME matches the brand "
                           "palette are filtered; non-brand color extras still fail. "
                           "Critical issues are unaffected.")

  CONSTRAINT: Do NOT change the default behavior of `sla_diff` — `--strict` without `--allow-brand-extras` MUST exit 1 on the same warnings it does today. The new filter only RUNS when `args.allow_brand_extras` is True.
  CONSTRAINT: Do NOT change the existing `extra-style` / `extra-layer` filter behavior. The new clause is additive (an `or` arm), not a replacement.
  CONSTRAINT: Do NOT load `shared/ci.yml` from `sla_diff.py`. Hardcode the 7-tuple. PR #14's review chose surface-area minimization; preserve that.
  CONSTRAINT: Do NOT add the brand-color list to a new module — keep it as a single private constant adjacent to the filter logic for diff readability.

  STEP 1B — Add unit tests in `tools/sla_lib/tests/test_sla_diff.py`:

  Locate the existing `AllowBrandExtrasTests` class at line 730. Add a helper method `_write_sla_with_extra_color(...)` that mirrors the existing `_write_sla_with_extra_style(...)` and `_write_sla_with_extra_layer(...)` helpers in shape. The body builds a SCRIBUSUTF8NEW root with one DOCUMENT, one PAGE, one MASTERPAGE, and (when extra_color_name is non-empty) a single COLOR sub-element with NAME=extra_color_name and CMYK="#00000000". Mirror the existing helpers exactly — same imports (lxml.etree as _et), same root attributes, same page/masterpage attributes.

  Then add TWO new test methods to the same class (positive + negative cases):

  1. `test_allow_brand_extras_filters_extra_color_warning_for_brand_color` — positive case:
     - Build left SLA with no extra COLOR; build right SLA with `extra_color_name='Hellgrün'`.
     - `sd.main([..., "--strict"])` -> assert exit 1 (extra-color is a warning).
     - `sd.main([..., "--strict", "--allow-brand-extras"])` -> assert exit 0 (filtered because 'Hellgrün' is in `_BRAND_COLOR_NAMES`).

  2. `test_allow_brand_extras_does_not_filter_non_brand_color` — negative case:
     - Build left SLA with no extra COLOR; build right SLA with `extra_color_name='SomeRandomBrandX'` (a name explicitly NOT in the 7-tuple).
     - `sd.main([..., "--strict"])` -> assert exit 1.
     - `sd.main([..., "--strict", "--allow-brand-extras"])` -> assert exit 1 (NOT filtered because 'SomeRandomBrandX' is not a brand color).
     - This is the critical guard: it proves the brand-name predicate actually narrows the filter, not just rubber-stamps every extra-color warning.

  Match the assertion message style of the existing `test_allow_brand_extras_filters_extra_style_warning` and `test_allow_brand_extras_filters_extra_layer_warning` tests (e.g. `"Expected exit 1 from --strict with extra-color warning"`).

  STEP 1C — Run the test suite to confirm both old and new tests pass:

      python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x -v -k AllowBrandExtras

  Then run the full sla_diff test suite to confirm nothing else regressed:

      python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x

  STEP 1D — Smoke test that the existing two templates still pass `bin/validate --ci`. Postkarte and Zeitung both carry all 7 brand colors in their original SLAs (RESEARCH.md MEDIUM-confidence note), so they have NO `extra-color` warnings to filter; the new filter clause is a no-op for them. `bin/validate --ci` MUST still report `sla_diff: PASS` for postkarte and zeitung.

  Note about Plakat at this stage: Plakat will still fail `bin/validate --ci` after Task 1 alone, because the COMMITTED Plakat build.py is still on the pre-Brand path. After Task 2 regenerates Plakat to use Brand, the new filter clause activates for Plakat too. This is expected — Task 1 is necessary infrastructure, Task 2 is what triggers it.

  CONSTRAINT: Do NOT regenerate any template's build.py in this task. Task 2 is the regen task.
  CONSTRAINT: Do NOT touch `bin/validate` — `--allow-brand-extras` is already wired through it (from PR #14).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x -v -k AllowBrandExtras && python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x && bin/validate --ci</automated>
  </verify>
  <done>
  - `tools/sla_diff.py` defines `_BRAND_COLOR_NAMES` as the 7-tuple and the `--allow-brand-extras` filter additionally drops `extra-color` warnings whose `i.right` is in that tuple.
  - Help text for `--allow-brand-extras` documents the extra-color extension.
  - 2 new tests added to `AllowBrandExtrasTests`: filters brand `extra-color`, does NOT filter non-brand `extra-color`.
  - All 5 tests in `AllowBrandExtrasTests` pass (3 existing + 2 new).
  - `bin/validate --ci` still PASS for postkarte and zeitung (Plakat regen is Task 2; it may still fail at this stage).
  - When `--allow-brand-extras` is NOT set, behavior is byte-identical to current main.
  </done>
  <commit_message>7: feat(sla_diff): extend --allow-brand-extras to brand extra-color warnings</commit_message>
</task>

<task type="auto">
  <name>Task 2: Regenerate templates/plakat-a1-hochformat/build.py via converter (zero hand edits)</name>
  <files>templates/plakat-a1-hochformat/build.py, templates/plakat-a1-hochformat/template.sla</files>
  <action>
  GOAL: Replace the 235-LOC committed `templates/plakat-a1-hochformat/build.py` with a converter-emitted version that uses `brand=Brand.gruene_noe()`, drops doc-attrs from 113 to 23 keys, drops pdf-attrs from 44 to 11 keys, drops `palette_replaces_ci=True`, and drops the explicit `layers=[DocumentLayer('Hintergrund', ...)]` (Brand provides the layer stack; Task 1 filters the resulting extra-layer warnings).

  RESEARCH.md verified live that the raw converter output meets all 4 numeric ACs with **zero hand edits**. The Plakat regen is the simplest of the three migrations — there are NO viable block substitutions, NO explicit-layer hand-add, NO ci-defaults hoist, and NO frame-shape edits.

  STEP 2A — Confirm git status is clean before running the converter, so a `git diff` will surface the conversion delta:

      git -C /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks status --short

  Should show no modifications to `templates/plakat-a1-hochformat/`. If it does, STOP and report — Task 1 may have inadvertently touched the template.

  STEP 2B — Run the converter (research-verified working invocation, will OVERWRITE the committed build.py):

      python3 tools/sla_to_dsl.py \
          templates/plakat-a1-hochformat/template.sla \
          templates/plakat-a1-hochformat/build.py \
          --template-id plakat-a1-hochformat \
          --assets-dir templates/plakat-a1-hochformat/assets/

  STEP 2C — Sanity check the regenerated file. RESEARCH.md projects ALL of these will hold:
  - Parses as Python: `python3 -c "import ast; ast.parse(open('templates/plakat-a1-hochformat/build.py').read())"` exits 0.
  - LOC: ~198 (informational only — do not gate). Acceptable range: 195 to 205.
  - Contains `brand=Brand.gruene_noe()` in the `Document(...)` call.
  - Does NOT contain `palette_replaces_ci=True` anywhere.
  - Does NOT contain `layers=[DocumentLayer(` (Brand provides the stack).
  - `extra_doc_attrs` has at most 23 keys (criterion: <= 23, expected exactly 23).
  - `extra_pdf_attrs` has at most 11 keys (criterion: <= 11, expected exactly 11).
  - 0 `Polygon(` calls (Plakat has no polygons; the visual "Dunkelgrün block" is a TextFrame).
  - 0 `PageBackground(` calls (no Polygon candidates -> no substitution).

  STEP 2D — Smoke test the regen builds:

      cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks/templates/plakat-a1-hochformat && python3 build.py && cd ../..

  This regenerates `template.sla` from the new build.py. The SLA should be valid XML and ~228 KB in size (RESEARCH.md measured 228054 bytes). DO NOT hand-edit `template.sla` after rebuild — it is purely a build artifact at this point.

  STEP 2E — Confirm the structural diff with allowlist is clean:

      python3 tools/sla_diff.py \
          --left plakat-a1-hochformat-original.sla \
          --right templates/plakat-a1-hochformat/template.sla \
          --strict --allow-brand-extras > /dev/null

  Must exit 0. If it exits 1, inspect the JSON output (`--json -`) — there should be ZERO unfiltered warnings. If `extra-color: Hellgrün` or `extra-color: Magenta` still appears, Task 1 didn't land correctly. If a different non-brand warning appears, the converter behavior changed since RESEARCH.md was written; STOP and surface to user.

  STEP 2F — Confirm visual_diff is byte-clean (this is the rendering acceptance gate):

      python3 tools/visual_diff.py \
          templates/plakat-a1-hochformat/template.sla \
          --baseline templates/plakat-a1-hochformat/baseline.pdf \
          --tolerance templates/plakat-a1-hochformat/diff.yml \
          --dpi 96 \
          --out build/validation/plakat-a1-hochformat/

  Must exit 0. RESEARCH.md verified live that the per-page mismatch is essentially 0% on the regenerated SLA. If mismatch jumps above the 1% threshold defined in `diff.yml`, the converter regressed since research; STOP and surface to user.

  CONSTRAINT: Do NOT hand-edit any frame DSL. RESEARCH.md is explicit that the raw regen meets all numeric ACs. The "regen-and-ship" pattern is the entire point of this issue's small scope.
  CONSTRAINT: Do NOT hand-add `layers=[DocumentLayer('Hintergrund', ...)]`. The Postkarte rewrite did this as belt-and-suspenders; Plakat demonstrates the cleaner pattern that relies on `--allow-brand-extras` filtering.
  CONSTRAINT: Do NOT widen `Impressum`, `ContactBlock`, `PageNumber`, or `ColumnTextStory` blocks. Even though Plakat's Impressum frame technically maps to the block in spirit, two API gaps (rotation_deg + Bold-prefix Run) put substitution out of scope here. P2 follow-ups in Task 5.
  CONSTRAINT: Do NOT touch `templates/plakat-a1-hochformat/template.sla` outside the rebuild. The build.py regenerates it.
  CONSTRAINT: If the regen output mismatches RESEARCH.md's measurements substantially (e.g. emits `palette_replaces_ci=True`, has > 23 doc-attrs, has > 11 pdf-attrs, or has > 205 LOC), STOP and inspect — Task 1 may not have landed correctly OR the converter changed since research.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks && python3 -c "import ast; ast.parse(open('templates/plakat-a1-hochformat/build.py').read())" && grep -q "brand=Brand.gruene_noe()" templates/plakat-a1-hochformat/build.py && ! grep -q "palette_replaces_ci=True" templates/plakat-a1-hochformat/build.py && cd templates/plakat-a1-hochformat && python3 build.py && cd ../.. && python3 -c "import re, ast; src=open('templates/plakat-a1-hochformat/build.py').read(); [print(label+':', len(ast.literal_eval(re.search(label+r'\s*=\s*(\{[^}]*\})', src, re.S).group(1))), 'keys') for label in ('extra_doc_attrs','extra_pdf_attrs')]; print('LOC:', len(src.splitlines())); print('Polygon count:', src.count('Polygon('))" && python3 tools/sla_diff.py --left plakat-a1-hochformat-original.sla --right templates/plakat-a1-hochformat/template.sla --strict --allow-brand-extras > /dev/null && python3 tools/visual_diff.py templates/plakat-a1-hochformat/template.sla --baseline templates/plakat-a1-hochformat/baseline.pdf --tolerance templates/plakat-a1-hochformat/diff.yml --dpi 96 --out build/validation/plakat-a1-hochformat/</automated>
  </verify>
  <done>
  - `templates/plakat-a1-hochformat/build.py` is the converter-regenerated version (~198 LOC).
  - `Document(...)` uses `brand=Brand.gruene_noe()`.
  - No `palette_replaces_ci=True` anywhere in the file.
  - No explicit `layers=[DocumentLayer(` in the file.
  - `extra_doc_attrs` <= 23 keys; `extra_pdf_attrs` <= 11 keys.
  - 0 `Polygon(` calls and 0 `PageBackground(` calls.
  - `python3 build.py` succeeds and regenerates a valid `template.sla`.
  - `tools/sla_diff.py --strict --allow-brand-extras` exits 0 against `plakat-a1-hochformat-original.sla`.
  - `tools/visual_diff.py` exits 0 against the committed `baseline.pdf` with `diff.yml` tolerance.
  </done>
  <commit_message>7: refactor(plakat): regenerate build.py via converter onto Brand</commit_message>
</task>

<task type="auto">
  <name>Task 3: Update PlakatRoundTrip test allowlist to filter brand-additive warnings</name>
  <files>tools/sla_lib/tests/test_sla_to_dsl.py</files>
  <action>
  GOAL: Extend `PlakatRoundTrip.test_diff_against_original_clean` (lines 119 to 141 of `tools/sla_lib/tests/test_sla_to_dsl.py`) to filter `extra-style`, `extra-layer`, and `extra-color` warnings injected by Brand. Mirror the Postkarte fix pattern from issue #6 commit `1ebe8ef` at lines 62 to 78, plus add the `extra-color` extension.

  After Task 2's regen, running this test against the committed Plakat build.py produces up to 13 unfiltered brand-additive warnings: 3 extra-layer (Bilder, Text, Hilfslinien) + 8 extra-style (ci/*) + 2 extra-color (Hellgrün, Magenta). All 13 are additive-only (do not change rendering) and tolerated the same way Postkarte tolerates its 11.

  STEP 3A — Edit `test_diff_against_original_clean` at lines 125 to 131. Replace the unconditional `summary[SEVERITY_WARNING] == 0` assertion with the same filter pattern as PostkarteRoundTrip (lines 62 to 78), but extended to also drop brand-color extras.

  Before (current):

      def test_diff_against_original_clean(self):
          sla = _run_build(self.TEMPLATE_DIR / "build.py")
          report = _diff_clean(self.ORIGINAL, sla)
          self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                           msg=f"critical: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
          self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0,
                           msg=f"warning: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_WARNING]}")

  After (replacement; preserves the critical-zero assertion and adds the filtered-warning assertion):

      def test_diff_against_original_clean(self):
          sla = _run_build(self.TEMPLATE_DIR / "build.py")
          report = _diff_clean(self.ORIGINAL, sla)
          self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                           msg=f"critical: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
          # build.py now uses brand=Brand.gruene_noe() which injects ci/* paragraph
          # styles, brand layers (Bilder/Text/Hilfslinien), and the full 7-color
          # palette. The original Plakat SLA carries only 5 of 7 brand colors, so
          # rebuilding adds 2 extra-color warnings (Hellgrün, Magenta). All three
          # categories of warnings are additive-only (do not change rendering) and
          # are tolerated the same way as PostkarteRoundTrip.
          _BRAND_COLOR_NAMES = (
              "Black", "White", "Registration",
              "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
          )
          non_brand_warnings = [
              i for i in report.issues
              if i.severity == sla_diff.SEVERITY_WARNING
              and not (
                  i.code in ("extra-style", "extra-layer")
                  or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
              )
          ]
          self.assertEqual(non_brand_warnings, [],
                           msg=f"unexpected warning issues: "
                               f"{[i.short() for i in non_brand_warnings]}")

  STEP 3B — Do NOT touch `test_soft_hyphens_byte_preserved` (lines 133 to 141). It is independent of the warning allowlist and continues to pass.

  STEP 3C — Run the test to confirm it passes against the regenerated Plakat build.py from Task 2:

      python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py::PlakatRoundTrip -x -v

  Both `test_diff_against_original_clean` and `test_soft_hyphens_byte_preserved` must pass.

  STEP 3D — Run the full test suite to confirm no regressions in adjacent test classes:

      python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py -x

  CONSTRAINT: Do NOT also extend `PostkarteConverterFreshRun` (lines 81 to 116) — its allowlist is correct as-is for Postkarte. Postkarte's original SLA has all 7 brand colors so there are no `extra-color` warnings to filter. The corresponding hygiene check for Plakat (a `PlakatConverterFreshRun` analogue) is OUT OF SCOPE per RESEARCH.md (R9 LOW-confidence note, P3 hygiene only).
  CONSTRAINT: Do NOT define `_BRAND_COLOR_NAMES` as a module-level constant in this test file. Keep it inline within the test method to keep the change self-contained — the same constant lives in `tools/sla_diff.py` (Task 1) and the duplication is intentional (test independence).
  CONSTRAINT: Do NOT add an `import sla_diff` of the constant — the test file already imports `sla_diff` for `SEVERITY_WARNING` / `SEVERITY_CRITICAL`. Keep the inline tuple definition for clarity; do NOT depend on a private `_BRAND_COLOR_NAMES` from `sla_diff` (which is a private module attribute).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py::PlakatRoundTrip -x -v && python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py -x</automated>
  </verify>
  <done>
  - `PlakatRoundTrip.test_diff_against_original_clean` filters brand-additive `extra-style`, `extra-layer`, and brand-color `extra-color` warnings before asserting zero non-brand warnings.
  - `PlakatRoundTrip.test_soft_hyphens_byte_preserved` is unchanged and still passes.
  - `pytest tools/sla_lib/tests/test_sla_to_dsl.py -x` is green (PostkarteRoundTrip, PostkarteConverterFreshRun, PlakatRoundTrip, ZeitungRoundTrip all pass).
  - `_BRAND_COLOR_NAMES` is inline in the test method (not imported from sla_diff).
  </done>
  <commit_message>7: test(plakat): allow brand-additive warnings in PlakatRoundTrip allowlist</commit_message>
</task>

<task type="auto">
  <name>Task 4: Rebuild gallery, run full validation pipeline, regenerate previews_for_sla SHA</name>
  <files>templates/plakat-a1-hochformat/template.sla, templates/plakat-a1-hochformat/page-01.png, templates/plakat-a1-hochformat/preview.pdf, templates/plakat-a1-hochformat/meta.yml</files>
  <action>
  GOAL: Run the full validation pipeline and regenerate the gallery artifacts so the stale-preview gate (`tools/check_stale_previews.py`) doesn't block the ship. After this task, ALL THREE templates must be `bin/validate --ci` green.

  STEP 4A — Regenerate gallery previews:

      bin/render-gallery

  This regenerates `page-01.png`, `preview.pdf`, and updates `meta.yml::previews_for_sla` to the new SHA256 of `template.sla`. Plakat is single-page (A1 portrait poster) so there is only `page-01.png`, NOT `page-02.png`.

  STEP 4B — Run the structural diff explicitly to confirm allowlist behavior on the rebuilt Plakat:

      python3 tools/sla_diff.py \
          --left plakat-a1-hochformat-original.sla \
          --right templates/plakat-a1-hochformat/template.sla \
          --strict \
          --allow-brand-extras

  Must exit 0. For comparison, run WITHOUT `--allow-brand-extras` and WITH `--strict` — exit code SHOULD be 1 (because the brand extras are still present, just allowlisted). This proves the allowlist is doing real work for Plakat (not just mirroring the empty-warning state Postkarte happens to have).

  STEP 4C — Full validation pipeline:

      bin/validate --ci

  All three templates (plakat, postkarte, zeitung) must report `sla_diff: PASS` and `visual_diff: PASS`. Exit code must be 0.

  STEP 4D — CI compliance check:

      python3 tools/check_ci.py templates/plakat-a1-hochformat/template.sla

  Exit 0.

  STEP 4E — Stale-preview gate (if `tools/check_stale_previews.py` is invokable as a standalone, otherwise this is covered by `bin/validate --ci`'s preflight):

      python3 tools/check_stale_previews.py 2>/dev/null || true

  STEP 4F — Test suite:

      python3 -m pytest tools/sla_lib/tests -x

  All tests pass — including the Task 1 new tests, the Task 3 updated PlakatRoundTrip, and the existing PostkarteRoundTrip / ZeitungRoundTrip / PostkarteConverterFreshRun.

  CONSTRAINT: Do NOT skip `bin/render-gallery` — without it, `meta.yml::previews_for_sla` will not match the rebuilt SLA's SHA and the stale-preview gate will fail.
  CONSTRAINT: Do NOT hand-edit `meta.yml::previews_for_sla` — `bin/render-gallery` updates it as a side-effect.
  CONSTRAINT: If any of the three templates (Plakat, Postkarte, Zeitung) reports `visual_diff: FAIL` or `sla_diff: FAIL`, STOP and diagnose — the brand-extras allowlist must NOT mask non-brand warnings. The Task 1 negative test (`test_allow_brand_extras_does_not_filter_non_brand_color`) is the regression guard for this.
  CONSTRAINT: Do NOT add a `PlakatConverterFreshRun` test class. RESEARCH.md (R9) flagged this as P3 hygiene; out of scope for this issue.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks && bin/render-gallery && bin/validate --ci && python3 tools/check_ci.py templates/plakat-a1-hochformat/template.sla && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `bin/render-gallery` regenerates `page-01.png`, `preview.pdf`, and updates `meta.yml::previews_for_sla` SHA.
  - `bin/validate --ci` exits 0 with `sla_diff: PASS` and `visual_diff: PASS` for plakat, postkarte, AND zeitung.
  - `tools/check_ci.py templates/plakat-a1-hochformat/template.sla` exits 0.
  - `pytest tools/sla_lib/tests -x` exits 0.
  - Stale-preview gate is clean (`previews_for_sla` SHA matches rebuilt `template.sla`).
  - Plakat's structural diff WITHOUT `--allow-brand-extras` still exits 1 (proves the allowlist is necessary, not redundant).
  </done>
  <commit_message>7: chore(plakat): rebuild gallery and validate full pipeline green</commit_message>
</task>

<task type="auto">
  <name>Task 5: Acceptance check + write EXECUTION.md</name>
  <files>.issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md</files>
  <action>
  GOAL: Verify all 6 ISSUE.md acceptance criteria against produced artifacts, write EXECUTION.md, and file the P2 follow-ups discovered during the migration.

  STEP 5A — Acceptance walk-through. For each AC in `ISSUE.md::Acceptance criteria`, record PASS/FAIL with concrete evidence (command run + exit code + relevant output excerpt). The 6 ACs are:

  1. `tools/visual_diff.py` clean against `templates/plakat-a1-hochformat/baseline.pdf` (within `docs/diff-tolerance.md`). Evidence: rerun the visual_diff command from Task 2 step 2F.
  2. `pytest tools/sla_lib/tests -x` green. Evidence: the Task 4 verify run.
  3. `bin/validate --ci` green for ALL three templates. Evidence: the Task 4 verify run.
  4. `tools/check_ci.py templates/plakat-a1-hochformat` clean. Evidence: the Task 4 verify run.
  5. `extra_doc_attrs` <= 23 keys. Evidence: count from Task 2 verify (expected exact 23).
  6. `extra_pdf_attrs` <= 11 keys. Evidence: count from Task 2 verify (expected exact 11).

  Plus the LOC criterion (informational only per user direction): record the actual LOC of `templates/plakat-a1-hochformat/build.py` (expected ~198, target ISSUE.md says <= 180 but this is informational only — do NOT mark it FAIL).

  STEP 5B — Measure achieved LOC (informational only):

      wc -l templates/plakat-a1-hochformat/build.py

  Record actual number. RESEARCH.md projects 198. Document in EXECUTION.md as informational; do not gate.

  STEP 5C — Write `.issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md` with this structure (replace `<...>` placeholders with actual values from Tasks 1 to 4):

      # Execution — Rewrite Plakat A1 onto Brand + blocks

      **Issue:** rewrite-plakat-onto-brand-blocks (id 7)
      **Status:** complete | partial | blocked
      **Executed:** 2026-MM-DD

      ## Tasks

      - [x] Task 1: Extend --allow-brand-extras to filter extra-color warnings for brand colors
      - [x] Task 2: Regenerate templates/plakat-a1-hochformat/build.py via converter (zero hand edits)
      - [x] Task 3: Update PlakatRoundTrip test allowlist to filter brand-additive warnings
      - [x] Task 4: Rebuild gallery, run full validation pipeline, regenerate previews_for_sla SHA
      - [x] Task 5: Acceptance check + write EXECUTION.md

      ## Acceptance criteria

      | # | Criterion | Status | Evidence |
      |---|---|---|---|
      | 1 | visual_diff clean | PASS | `tools/visual_diff.py ... -> exit 0; max mismatch <X>%` |
      | 2 | pytest tools/sla_lib/tests -x | PASS | `<count> tests passing` |
      | 3 | bin/validate --ci | PASS | plakat/postkarte/zeitung all PASS |
      | 4 | check_ci.py | PASS | exit 0 |
      | 5 | extra_doc_attrs <= 23 | PASS | <count> keys |
      | 6 | extra_pdf_attrs <= 11 | PASS | <count> keys |

      Informational (LOC target dropped per user direction):
      - LOC: 235 -> <after> (target was <= 180; achieved <after>; informational only)

      ## Metrics

      - LOC: 235 -> <after> (-<delta>; informational, not an AC)
      - extra_doc_attrs: 113 -> <after-count>
      - extra_pdf_attrs: 44 -> <after-count>
      - Block substitutions: 0 (Plakat has 0 Polygons / 0 chains / 0 pgno / 0 contact frames; 1 Impressum frame stays primitive due to two API gaps)
      - Brand uptake: brand=Brand.gruene_noe(), palette_replaces_ci removed, layers default to Brand stack
      - sla_diff allowlist: --allow-brand-extras now also filters brand `extra-color` (new in this issue)

      ## P2 follow-ups (file as future issues, do NOT implement here)

      1. **Widen `Impressum` block to support `rotation_deg=` kwarg.** Plakat carries a vertical (rotation_deg=270) Impressum at the right margin. The modern block at `tools/sla_lib/builder/blocks.py:89-124` has no rotation_deg surface. Combined with the second gap below, this blocks Impressum block substitution for Plakat.

      2. **Widen `Impressum` block to support Bold-prefix Run idiom (`prefix_text=`, `prefix_font=`).** Plakat (and Postkarte) carry a Bold "Impressum:" prefix Run before the Book body. The modern block emits a single Run from `text=`. This is the same gap Postkarte EXECUTION.md filed as P2 follow-up #1; reaffirmed here. Combined widening for issues 1+2: add `prefix_text=`, `prefix_font=`, AND `rotation_deg=` kwargs to `Impressum`.

      3. **(Optional, P3 hygiene) Add `PlakatConverterFreshRun` test class** to mirror `PostkarteConverterFreshRun` at `tools/sla_lib/tests/test_sla_to_dsl.py:81`. Plakat is currently covered only by the round-trip test, not by the from-scratch convert-and-check guard. Low priority.

      4. **(Optional, P3) Audit `extra_pdf_attrs` and `extra_doc_attrs` for further hoist candidates** once Zeitung migrates (issue #8). Plakat's 23/11 residual is at exact AC parity; Zeitung may surface more constants.

      ## Notes

      - Plakat is the smallest of the three migrations: zero block substitutions, zero hand edits to the regenerated build.py, zero ci-defaults hoists. The whole issue value is (a) closing the `extra-color` allowlist gap that Plakat alone surfaces and (b) demonstrating the regen-and-ship pattern works on a template the blocks don't fit.
      - The `--allow-brand-extras` flag is now the canonical mechanism for tolerating Brand-injected `extra-style` / `extra-layer` / brand `extra-color` warnings in `bin/validate`. Zeitung migration (#8) inherits this directly; RESEARCH.md notes Zeitung carries all 7 brand colors so it likely won't re-trigger the extra-color path.
      - Visual_diff fidelity against `baseline.pdf` is the correctness gate. Verified clean at every step.

  STEP 5D — Final commit. Stage EXECUTION.md plus any artifacts modified by `bin/render-gallery` (page-01.png, preview.pdf, meta.yml) and commit with the message below. The orchestrator will commit; this task just stages and writes EXECUTION.md.

  CONSTRAINT: Do NOT push or open a PR. The user runs `/issue:ship` separately.
  CONSTRAINT: If any AC in Step 5A is FAIL, mark Status as `blocked`, leave the failed checkbox unchecked, and surface the failure in the EXECUTION.md notes — do NOT pretend the issue is complete.
  CONSTRAINT: Use the LOC number measured in Step 5B verbatim. Do not round, estimate, or smooth. RESEARCH.md projects 198 but the actual converter output may differ by 1 to 2 LOC depending on how the SLA was last touched.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks && test -f .issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md && grep -q "Acceptance criteria" .issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md && grep -q "P2 follow-ups" .issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md && grep -q "Impressum" .issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md && bin/validate --ci && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `.issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md` exists.
  - All 6 ACs are recorded with PASS/FAIL status and concrete evidence.
  - LOC, doc-attrs count, pdf-attrs count are recorded as numbers (not estimates).
  - At least 2 P2 follow-ups are filed (Impressum rotation_deg widening, Impressum prefix-Run widening).
  - `bin/validate --ci` and `pytest tools/sla_lib/tests -x` are green.
  </done>
  <commit_message>7: docs(plakat): record execution and acceptance evidence</commit_message>
</task>

</tasks>

<verification>
After all tasks complete, run the final battery (this is also the body of the Task 4 + Task 5 verifies, repeated here as a single-shot reproducer for the reviewer):

```
cd /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks
python3 -m pytest tools/sla_lib/tests -x
python3 tools/check_ci.py templates/plakat-a1-hochformat/template.sla
python3 tools/visual_diff.py \
    templates/plakat-a1-hochformat/template.sla \
    --baseline templates/plakat-a1-hochformat/baseline.pdf \
    --tolerance templates/plakat-a1-hochformat/diff.yml \
    --dpi 96 \
    --out build/validation/plakat-a1-hochformat/
python3 tools/sla_diff.py \
    --left plakat-a1-hochformat-original.sla \
    --right templates/plakat-a1-hochformat/template.sla \
    --strict --allow-brand-extras
bin/validate --ci
```

All five must exit 0. The visual_diff per-page mismatch must be under the 1% threshold defined in `templates/plakat-a1-hochformat/diff.yml`.
</verification>

<success_criteria>
Maps 1:1 to the 6 acceptance criteria in ISSUE.md (LOC criterion is informational only per user direction):

1. `tools/visual_diff.py` clean against `templates/plakat-a1-hochformat/baseline.pdf` within `docs/diff-tolerance.md` thresholds.
2. `pytest tools/sla_lib/tests -x` green (including PlakatRoundTrip with new allowlist + new AllowBrandExtrasTests for extra-color).
3. `bin/validate --ci` green for ALL three templates (plakat, postkarte, zeitung) — enabled by Task 1's `--allow-brand-extras` extension.
4. `tools/check_ci.py templates/plakat-a1-hochformat` clean.
5. New `extra_doc_attrs` in `templates/plakat-a1-hochformat/build.py` contains <= 23 keys (expected exactly 23).
6. New `extra_pdf_attrs` in `templates/plakat-a1-hochformat/build.py` contains <= 11 keys (expected exactly 11).

Plus: `templates/plakat-a1-hochformat/build.py` uses `brand=Brand.gruene_noe()`; `tools/sla_diff.py` documents and implements the brand-color extension to `--allow-brand-extras`; EXECUTION.md records achieved LOC (informational), all 6 AC outcomes, and the P2 follow-ups (Impressum rotation_deg + Impressum prefix-Run widening).

LOC criterion (ISSUE.md line 53: `<= 180`) is **informational only** per user direction. Achieved is expected ~198. Record verbatim, do not gate.
</success_criteria>
