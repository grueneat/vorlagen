# Plan: Post-migration DSL hygiene — Impressum widening, Zeitung fresh-run, extras audit

<objective>
What this plan accomplishes:
- A) Widen the `Impressum` block (`tools/sla_lib/builder/blocks.py:116-151`) with
  the three accumulated post-migration kwargs (bold-prefix Run, rotation
  passthrough, heading + spacer + body 3-Run schema) plus a `runs=` escape
  hatch, in a fully backward-compatible way.
- B) Add `ZeitungConverterFreshRun` to `tools/sla_lib/tests/test_sla_to_dsl.py`,
  mirroring the existing `PostkarteConverterFreshRun` shape.
- C) Document the `extra_*_attrs` and `_LEGACY_LAYER_NAMES` audits as outcomes
  in EXECUTION.md (no code/YAML changes).

Why it matters:
- Three small DSL hygiene items deferred during issues #6 / #7 / #8. Folding
  them into a single hardening pass avoids three near-trivial PRs and prevents
  the DSL from carrying a backlog of post-migration paper cuts.

Scope:
- IN: `tools/sla_lib/builder/blocks.py` (Impressum dataclass + emit only),
  `tools/sla_lib/tests/test_blocks.py` (extend `ImpressumTests`),
  `tools/sla_lib/tests/test_sla_to_dsl.py` (append one class), EXECUTION.md.
- OUT: No converter changes (`tools/sla_to_dsl.py` untouched), no
  `shared/ci-defaults.yml` edits, no `templates/*/build.py` corpus
  substitutions, no `_LEGACY_LAYER_NAMES` additions, no PR / push.

No CONTEXT.md — autonomous run, decisions taken from RESEARCH.md per the
parent prompt's locked guidance (hybrid Impressum API; tests-only verification
for A; no corpus substitutions; no hoists).
</objective>

<skills>
No workspace `.claude/skills/` directory in this repo — none to inject.
</skills>

<context>
Issue: @.issues/post-migration-dsl-hygiene/ISSUE.md
Research: @.issues/post-migration-dsl-hygiene/RESEARCH.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

From `tools/sla_lib/builder/blocks.py` (current Impressum, lines 116-151) — the
1-Run baseline you are widening:

```python
@dataclass
class Impressum:
    text: str = DEFAULT_IMPRESSUM
    x_mm: float = 5
    y_mm: float = 142
    w_mm: float = 95
    h_mm: float = 6
    fcolor: Optional[str] = None
    layer: int = 2
    anname: str = "Impressum"

    def emit(self) -> Iterable:
        yield TextFrame(
            x_mm=self.x_mm, y_mm=self.y_mm, w_mm=self.w_mm, h_mm=self.h_mm,
            trail_style="Impressum",
            runs=[Run(text=self.text, paragraph_style=None)],
            fcolor=self.fcolor, layer=self.layer, anname=self.anname,
        )
```

From `tools/sla_lib/builder/primitives.py` — the kwargs accepted by `Run` and
`TextFrame` that the new Impressum branches use (verified by reading the
corpus sites in RESEARCH.md sections A1/A2/A3):

```python
# Run kwargs used:
Run(text: str, font: Optional[str] = None,
    fcolor: Optional[str] = None, fshade: Optional[int] = None,
    features: Optional[str] = None,
    paragraph_style: Optional[str] = None,
    separator: Optional[str] = None,         # 'para' for Zeitung heading + spacer
    has_itext: bool = True)                  # False for the empty spacer Run

# TextFrame kwargs used (existing — passthroughs from Impressum):
TextFrame(x_mm, y_mm, w_mm, h_mm,
          trail_style: str,
          runs: Sequence[Run],
          fcolor=None, layer=2, anname=...,
          rotation_deg: Optional[float] = None,    # Plakat passthrough
          line_width_pt: Optional[float] = None,   # all 3 corpus sites set this
          col_gap_mm: Optional[float] = None)      # all 3 corpus sites set this
```

From `tools/sla_lib/tests/test_blocks.py:140-184` — the existing
`ImpressumTests` class shape and helper:

```python
class ImpressumTests(unittest.TestCase):
    def _doc_with_block(self, **kwargs):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(Impressum(x_mm=5, y_mm=142, w_mm=95, **kwargs))
        return doc
    # 5 existing tests:
    #   test_impressum_emits_one_text_frame
    #   test_impressum_default_text
    #   test_impressum_trail_style_impressum
    #   test_impressum_custom_text
    #   test_impressum_round_trips_through_emit
```

Module-level helpers (already imported at top of file):
- `_save(doc) -> SLADocument` — writes a tempfile and returns a parsed wrapper
- `_save_to_str(doc) -> str` — returns the full SLA XML as text

Use only these existing helpers; do NOT add new helpers and do NOT
`import pytest`.

From `tools/sla_lib/tests/test_sla_to_dsl.py:81-116` — the
`PostkarteConverterFreshRun` shape that the new Zeitung class mirrors. Module-
level helpers `_diff_clean` and `_run_build` already exist (lines 30-48) and
must be reused. `sla_diff` is imported at module top.

Zeitung corpus details for the new fresh-run class (from RESEARCH.md §B):
- Original SLA: `gruene-zeitung-vorlage-original.sla` (workspace root; same
  ROOT-relative shape as Postkarte).
- Template id passed to `mod.convert(...)`: `"zeitung-a4-grun"`.
- Allowlist: `extra-style` + `extra-layer` codes are allowed unconditionally;
  `extra-color` allowed only when `i.right in _BRAND_COLOR_NAMES`;
  `missing-layer` allowed only when `i.left in _LEGACY_LAYER_NAMES = ("Ebene 1",)`.
  This matches `ZeitungRoundTrip` at lines 163-198 verbatim.
</interfaces>

Key files:
@tools/sla_lib/builder/blocks.py — Impressum block (lines 116-151) — Task 1 edits
@tools/sla_lib/tests/test_blocks.py — ImpressumTests (lines 140-184) — Task 2 extends
@tools/sla_lib/tests/test_sla_to_dsl.py — Task 3 appends a new class after line 206
@.issues/post-migration-dsl-hygiene/EXECUTION.md — Task 4 writes audit outcomes
@.github/workflows/pages.yml — line 91 invokes `python3 -m unittest discover tools/sla_lib/tests` (CI gate)
</context>

<commit_format>
Format: conventional with numeric-id prefix
Pattern: `9: <type>(<scope>): <description>`
Examples:
- `9: feat(blocks): widen Impressum with prefix/heading/rotation kwargs`
- `9: test(blocks): cover Impressum prefix, rotation, heading idioms`
- `9: test(converter): add ZeitungConverterFreshRun mirror`
- `9: docs(issues): record extras + legacy-layer audit outcomes`
- `9: chore(issue): mark post-migration-dsl-hygiene done`
Allowed types: feat, fix, test, refactor, docs, chore.
</commit_format>

<tasks>

<!-- Strictly serial: Task 1 -> 2 -> 3 -> 4 -> 5. Tasks 2 and 3 are technically
     independent (different files) but the executor MUST serialize for safety
     so a green Task 2 gate is a precondition for Task 3. -->

<task type="auto">
  <name>Task 1: Widen the Impressum dataclass and emit() — backward-compatible</name>
  <inputs>
    - tools/sla_lib/builder/blocks.py (current Impressum at lines 116-151)
    - RESEARCH.md §A.4 (the proposed dataclass body and emit() sketch — follow verbatim)
    - tools/sla_lib/builder/primitives.py (Run + TextFrame kwarg surfaces; do NOT modify)
  </inputs>
  <outputs>
    - tools/sla_lib/builder/blocks.py with Impressum widened
  </outputs>
  <files>tools/sla_lib/builder/blocks.py</files>
  <action>
  Replace the Impressum dataclass at `tools/sla_lib/builder/blocks.py:116-151`
  with the widened version from RESEARCH.md §A.4. Concretely:

  1. Keep the existing 8 fields (`text`, `x_mm`, `y_mm`, `w_mm`, `h_mm`,
     `fcolor`, `layer`, `anname`) with their current defaults.

  2. Add 11 NEW optional fields (all default to a value that triggers the
     existing 1-Run shape so old call sites stay byte-identical):

     - `prefix_text: Optional[str] = None`         # A1 (Postkarte/Plakat)
     - `prefix_font: str = "Gotham Narrow Bold"`
     - `prefix_features: Optional[str] = None`     # Postkarte sets 'inherit'; Plakat omits
     - `prefix_fshade: Optional[int] = 100`        # both corpus sites: 100
     - `rotation_deg: float = 0`                    # A2 (Plakat)
     - `heading_text: Optional[str] = None`        # A3 (Zeitung)
     - `heading_font: Optional[str] = None`
     - `heading_paragraph_style: Optional[str] = None`
     - `line_width_pt: Optional[float] = None`     # frame passthrough
     - `col_gap_mm: Optional[float] = None`        # frame passthrough
     - `body_fshade: Optional[int] = None`         # body Run passthrough
     - `runs: Optional[Sequence[Run]] = None`      # full-override escape hatch

     Type the `runs:` field as `Optional[Sequence[Run]]` and import `Sequence`
     from `typing` at the top of the file if not already present. Use
     `Optional` (already imported in this module).

  3. Update the docstring to describe the four substitutable shapes
     (1-Run default, 2-Run prefix, 3-Run heading+spacer+body, full
     `runs=` override) and cite the corpus sources from RESEARCH.md §A1-A3
     (Postkarte build.py:223-236, Plakat build.py:91-105, Zeitung build.py:2445-2459).

  4. Replace `emit()` with the 4-branch if/elif/elif/else body from
     RESEARCH.md §A.4. Required behaviour:

     ```python
     def emit(self) -> Iterable:
         if self.runs is not None:
             body_runs = list(self.runs)                  # 1) full override
         elif self.heading_text is not None:
             body_runs = [                                # 2) heading + spacer + body
                 Run(text=self.heading_text, separator='para',
                     paragraph_style=self.heading_paragraph_style,
                     font=self.heading_font),
                 Run(text='', has_itext=False, separator='para',
                     paragraph_style=self.heading_paragraph_style),
                 Run(text=self.text, fcolor=self.fcolor, fshade=self.body_fshade),
             ]
         elif self.prefix_text is not None:
             body_runs = [                                # 3) bold-prefix
                 Run(text=self.prefix_text, font=self.prefix_font,
                     fcolor=self.fcolor, features=self.prefix_features,
                     fshade=self.prefix_fshade),
                 Run(text=self.text, fcolor=self.fcolor, fshade=self.body_fshade),
             ]
         else:
             body_runs = [Run(text=self.text, paragraph_style=None)]  # 4) baseline
         tf_kwargs = dict(
             x_mm=self.x_mm, y_mm=self.y_mm, w_mm=self.w_mm, h_mm=self.h_mm,
             trail_style="Impressum",
             runs=body_runs,
             fcolor=self.fcolor, layer=self.layer, anname=self.anname,
         )
         if self.rotation_deg:
             tf_kwargs["rotation_deg"] = self.rotation_deg
         if self.line_width_pt is not None:
             tf_kwargs["line_width_pt"] = self.line_width_pt
         if self.col_gap_mm is not None:
             tf_kwargs["col_gap_mm"] = self.col_gap_mm
         yield TextFrame(**tf_kwargs)
     ```

  Backward-compatibility constraint (load-bearing): when no new kwargs are
  set, the final `else` branch produces `[Run(text=self.text, paragraph_style=None)]`
  AND the three `if self.<x>:` guards on `tf_kwargs` (rotation_deg,
  line_width_pt, col_gap_mm) all fall through, so the emitted TextFrame
  carries the EXACT same kwarg set as before. This is what makes the
  existing 5 `ImpressumTests` pass unchanged.

  Out of scope (DO NOT do):
  - Do not touch `templates/*/build.py` — no corpus substitutions in this
    issue (locked decision; see RESEARCH.md §E2).
  - Do not touch `tools/sla_to_dsl.py` — converter-side changes are an
    explicit Non-goal in ISSUE.md.
  - Do not modify any other block in `blocks.py`.
  - Do not modify `Run` or `TextFrame` in `primitives.py`. The `runs=`,
    `has_itext=`, `separator=`, `rotation_deg=` etc. parameters already
    exist on those classes (used today by `templates/*/build.py`). Do
    not add new parameters there.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/post-migration-dsl-hygiene && \
      python3 -m unittest tools.sla_lib.tests.test_blocks -v 2>&1 | tail -40 && \
      pytest tools/sla_lib/tests/test_blocks.py -q 2>&1 | tail -20
    </automated>
  </verify>
  <done>
    - Impressum dataclass has 11 new optional fields (defaults preserve old behaviour)
    - `emit()` has the 4-branch if/elif/elif/else structure (override → heading → prefix → baseline)
    - All 5 existing `ImpressumTests` pass unchanged under BOTH unittest and pytest
    - All 21 other block tests in `test_blocks.py` (PageNumberTests, PageBackgroundTests, ContactBlockTests, ColumnTextStoryTests) still pass
    - No other file modified
  </done>
  <commit_message>9: feat(blocks): widen Impressum with prefix/heading/rotation kwargs</commit_message>
</task>

<task type="auto">
  <name>Task 2: Add 4 unittest-style coverage tests for the widened Impressum</name>
  <inputs>
    - tools/sla_lib/tests/test_blocks.py (existing ImpressumTests at lines 140-184)
    - The widened Impressum dataclass from Task 1
    - RESEARCH.md §A1, §A2, §A3 (corpus shapes that the tests must validate)
  </inputs>
  <outputs>
    - tools/sla_lib/tests/test_blocks.py with 4 new methods inside ImpressumTests
  </outputs>
  <files>tools/sla_lib/tests/test_blocks.py</files>
  <action>
  Append four new test methods INSIDE the existing `ImpressumTests` class at
  `tools/sla_lib/tests/test_blocks.py:140-184`. Use the existing class
  (do NOT create a sibling class), the existing `_doc_with_block` helper, and
  the module-level `_save` / `_save_to_str` helpers. All four tests must be
  unittest-style (`unittest.TestCase` methods, `self.assertX(...)`,
  `self.subTest(...)` if needed). NO `import pytest`. NO pytest fixtures or
  parametrize decorators. The repo's CI runs `python3 -m unittest discover`,
  not pytest (verified at `.github/workflows/pages.yml:91`); a stray
  `import pytest` failed CI in issue #16 even though it passed locally.

  The four tests, each gated by ONE of the new code paths in `emit()`:

  1. `test_impressum_with_bold_prefix` — Postkarte's 2-Run idiom (RESEARCH.md §A1).
     Build: `self._doc_with_block(prefix_text='Impressum:', prefix_features='inherit')`.
     Save with `_save(...)`, find the single PTYPE=4 frame, walk its
     StoryText, and assert:
       - StoryText has exactly 2 ITEXT child elements (no <para/> separator
         between them — same paragraph, font switch mid-line).
       - First ITEXT carries `FONT='Gotham Narrow Bold'`. (Read from
         `itext0.attrib.get('FONT')`.)
       - First ITEXT `CH` attribute equals `'Impressum:'`.
       - Second ITEXT does NOT set `FONT='Gotham Narrow Bold'` (either no
         FONT attr or a different value — assert `attrib.get('FONT') !=
         'Gotham Narrow Bold'`).
       - Second ITEXT `CH` contains the default impressum body
         (`assertIn('Grünen Niederösterreich', ...)`).

  2. `test_impressum_rotated` — Plakat's `rotation_deg=270` passthrough (§A2).
     Build: `self._doc_with_block(rotation_deg=270)`. Save with `_save(...)`.
     Find the single PTYPE=4 frame and assert its PAGEOBJECT carries
     `ROT='270'` (i.e. `frame.attrib.get('ROT') == '270'`). Also assert
     the StoryText still has exactly ONE ITEXT (rotation alone does not
     change the Run shape — backward compat with the 1-Run baseline).

  3. `test_impressum_with_heading` — Zeitung's heading + spacer + body (§A3).
     Build: `self._doc_with_block(heading_text='Impressum',
     heading_paragraph_style='Inhaltsheadline Titelseite')`. Save with
     `_save(...)`, walk StoryText. Assert:
       - StoryText contains the literal substring
         `'Inhaltsheadline Titelseite'` (use `_save_to_str(...)` then
         `assertIn`) — this proves the heading paragraph style reached the
         emitted frame.
       - StoryText contains exactly 2 ITEXT children with non-empty `CH`
         (heading text + body text) and at least 2 `<para/>` elements
         (one terminating the heading, one terminating the empty spacer
         paragraph). Implementation hint: count
         `len(story.findall('ITEXT'))` and `len(story.findall('para'))`
         then assert via `self.assertEqual` / `self.assertGreaterEqual`.
       - First non-empty ITEXT `CH` equals `'Impressum'` (heading).
       - Last non-empty ITEXT `CH` contains the default body marker
         (`assertIn('Grünen Niederösterreich', ...)`).

  4. `test_impressum_baseline_unchanged` — explicit backward-compat assertion
     for the 1-Run default path. Build TWO docs: one with the
     baseline call shape `self._doc_with_block()` and one constructed by
     calling Impressum with NONE of the new kwargs explicitly set. Save
     each via `_save_to_str(...)`. Assert that:
       - both XML strings contain `<SCRIBUSUTF8NEW`
       - the StoryText of each parsed-back doc has exactly ONE ITEXT
       - the first ITEXT `CH` contains `'Grünen Niederösterreich'` in BOTH
         (i.e. default text reaches the frame whether or not the new
         kwargs are present)
       - neither docs' single PTYPE=4 frame carries `ROT` set to a
         non-zero value (assert `attrib.get('ROT')` is either absent or
         a string parseable to 0.0)

  Notes for the executor:
  - Use the existing `_save` helper (returns a parsed `SLADocument` with
    `.page_objects()`) — DO NOT roll a new XML parser.
  - The PageNumberTests block (lines 42-134 of the same file) shows the
    correct idiom for: filtering PTYPE=4 frames, walking StoryText,
    reading `attrib.get(...)` from ITEXT/var children. Mirror that style.
  - Keep each new test under ~20 lines including the docstring.
  - Do not touch any test outside `ImpressumTests`.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/post-migration-dsl-hygiene && \
      python3 -m unittest tools.sla_lib.tests.test_blocks.ImpressumTests -v 2>&1 | tail -40 && \
      python3 -m unittest tools.sla_lib.tests.test_blocks -v 2>&1 | tail -10 && \
      pytest tools/sla_lib/tests/test_blocks.py::ImpressumTests -q 2>&1 | tail -15
    </automated>
  </verify>
  <done>
    - 4 new methods inside `ImpressumTests`: `test_impressum_with_bold_prefix`, `test_impressum_rotated`, `test_impressum_with_heading`, `test_impressum_baseline_unchanged`
    - All 9 ImpressumTests methods (5 old + 4 new) pass under unittest AND pytest
    - No other test in test_blocks.py was modified
    - `import pytest` does NOT appear anywhere in test_blocks.py (`grep -n 'import pytest' tools/sla_lib/tests/test_blocks.py` returns nothing)
  </done>
  <commit_message>9: test(blocks): cover Impressum prefix, rotation, heading idioms</commit_message>
</task>

<task type="auto">
  <name>Task 3: Add ZeitungConverterFreshRun mirror class</name>
  <inputs>
    - tools/sla_lib/tests/test_sla_to_dsl.py (existing PostkarteConverterFreshRun at lines 81-116; ZeitungRoundTrip allowlist at lines 163-198)
    - gruene-zeitung-vorlage-original.sla (workspace-root SLA original)
    - RESEARCH.md §B (proposed class body)
  </inputs>
  <outputs>
    - tools/sla_lib/tests/test_sla_to_dsl.py with one new class appended
  </outputs>
  <files>tools/sla_lib/tests/test_sla_to_dsl.py</files>
  <action>
  Append a new class `ZeitungConverterFreshRun(unittest.TestCase)` to
  `tools/sla_lib/tests/test_sla_to_dsl.py`. Place it AFTER the existing
  `ZeitungRoundTrip` class (after line 206, before the
  `StoryTextRoundTripTests` class at line 209). Mirror the exact shape of
  `PostkarteConverterFreshRun` at lines 81-116, adapting only the values
  that differ for Zeitung.

  Required structure (from RESEARCH.md §B):

  ```python
  class ZeitungConverterFreshRun(unittest.TestCase):
      """Run the converter from scratch in a tempdir against the Zeitung
      original and verify the diff stays clean. Mirror of
      PostkarteConverterFreshRun adapted for Zeitung's 14-page facing-pages
      layout, linked-story chains, and 'Ebene 1' legacy layer."""

      ORIGINAL = ROOT / "gruene-zeitung-vorlage-original.sla"

      def test_fresh_convert_is_clean(self):
          tmp = Path(tempfile.mkdtemp())
          try:
              spec = importlib.util.spec_from_file_location(
                  "sla_to_dsl", str(ROOT / "tools" / "sla_to_dsl.py"))
              mod = importlib.util.module_from_spec(spec)
              spec.loader.exec_module(mod)
              mod.convert(self.ORIGINAL, tmp / "build.py",
                           "zeitung-a4-grun", tmp / "assets")
              sla = _run_build(tmp / "build.py")
              report = _diff_clean(self.ORIGINAL, sla)
              self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                               msg=f"critical issues: "
                                   f"{[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
              _BRAND_COLOR_NAMES = (
                  "Black", "White", "Registration",
                  "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
              )
              _LEGACY_LAYER_NAMES = ("Ebene 1",)
              non_brand_warnings = [
                  i for i in report.issues
                  if i.severity == sla_diff.SEVERITY_WARNING
                  and not (
                      i.code in ("extra-style", "extra-layer")
                      or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
                      or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)
                  )
              ]
              self.assertEqual(non_brand_warnings, [],
                               msg=f"unexpected warning issues: "
                                   f"{[i.short() for i in non_brand_warnings]}")
          finally:
              shutil.rmtree(tmp, ignore_errors=True)
  ```

  Constraints:
  - Reuse the module-level helpers `_diff_clean` (line 30) and `_run_build`
    (line 34). Do NOT redefine them.
  - Reuse the module-level imports (`importlib`, `importlib.util`,
    `shutil`, `tempfile`, `unittest`, `Path`, `sla_diff`). Do NOT add new
    imports.
  - Allowlist MUST equal `ZeitungRoundTrip`'s exactly (same 7 brand colors,
    same `("Ebene 1",)` legacy tuple, same predicate shape). If the test
    fails, the resolution is to fix the converter or roll back a hand-edit
    in the committed `templates/zeitung-a4-grun/build.py` — DO NOT widen
    the allowlist (RESEARCH.md §E4).
  - Expected runtime ~10-20s; do not add `@unittest.skip` or any timeout
    knob.

  Out of scope: do NOT modify `PostkarteConverterFreshRun`,
  `PostkarteRoundTrip`, `PlakatRoundTrip`, `ZeitungRoundTrip`, or
  `StoryTextRoundTripTests`. Do NOT add a `PlakatConverterFreshRun`
  (that's a separate future issue if desired).
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/post-migration-dsl-hygiene && \
      python3 -m unittest tools.sla_lib.tests.test_sla_to_dsl.ZeitungConverterFreshRun -v 2>&1 | tail -30 && \
      pytest tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungConverterFreshRun -q 2>&1 | tail -15
    </automated>
  </verify>
  <done>
    - `ZeitungConverterFreshRun` class exists in test_sla_to_dsl.py with one method `test_fresh_convert_is_clean`
    - Class body matches the structure of `PostkarteConverterFreshRun` 1-for-1, with template id `zeitung-a4-grun` and the Zeitung allowlist
    - `python3 -m unittest tools.sla_lib.tests.test_sla_to_dsl.ZeitungConverterFreshRun` exits 0
    - `pytest tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungConverterFreshRun` exits 0
    - All other classes in the file still pass under both runners
    - `import pytest` does NOT appear anywhere in test_sla_to_dsl.py
  </done>
  <commit_message>9: test(converter): add ZeitungConverterFreshRun mirror</commit_message>
</task>

<task type="auto">
  <name>Task 4: Document the C1 (extras) and C2 (legacy-layer) audit outcomes in EXECUTION.md</name>
  <inputs>
    - RESEARCH.md §C.1 (extras audit hard counts)
    - RESEARCH.md §C.2 (`_LEGACY_LAYER_NAMES` audit)
    - The parent prompt's "Critical context from research" items 2 and 3
  </inputs>
  <outputs>
    - .issues/post-migration-dsl-hygiene/EXECUTION.md (created if missing; appended otherwise)
  </outputs>
  <files>.issues/post-migration-dsl-hygiene/EXECUTION.md</files>
  <action>
  Create (or extend if it already exists) the EXECUTION.md inside the issue
  directory at
  `.issues/post-migration-dsl-hygiene/EXECUTION.md`. The file MUST include
  these two sections (in addition to whatever the executor's task tracking
  already produced):

  ## Audit C1: extra_doc_attrs / extra_pdf_attrs cross-template

  - Method: programmatically computed `set ∩ set ∩ set` over the three
    template `Document(...)` calls (Postkarte build.py:29-30,
    Plakat build.py:28-29, Zeitung build.py:29-30).
  - Hard counts:
    - `extra_doc_attrs`: 23 keys per template, 23 keys in the 3-way set
      intersection, **0 keys with identical VALUES across all three**
      templates.
    - `extra_pdf_attrs`: 11 keys per template, 11 keys in the 3-way set
      intersection, **0 keys with identical VALUES across all three**
      templates.
  - Outcome: **No hoist candidates remain.** `shared/ci-defaults.yml`
    already absorbs every truly-shared key during issues #6/#7/#8. The
    residual 23+11 keys diverge in value because they encode per-template
    state (color profile names, paper size, image DPI, Scribus
    user-preference state, or Zeitung's higher-precision float
    serialization).
  - Action taken: **none.** No edit to `shared/ci-defaults.yml`. No edit
    to any `templates/*/build.py`.

  ## Audit C2: _LEGACY_LAYER_NAMES (tools/sla_diff.py)

  - Method: grepped `<LAYERS NAME=...>` in the three workspace-root SLA
    originals.
  - Findings:
    - `postkarte-vorlage-original.sla`: only `Hintergrund` (already in
      `Brand.gruene_noe()` 4-layer stack — produces no warning).
    - `plakat-a1-hochformat-original.sla`: only `Hintergrund` (same as
      Postkarte).
    - `gruene-zeitung-vorlage-original.sla`: `Ebene 1` (already in
      `_LEGACY_LAYER_NAMES`).
  - Outcome: `_LEGACY_LAYER_NAMES = ("Ebene 1",)` is **complete-as-is**
    for the three current templates.
  - Action taken: **none.** No edit to `tools/sla_diff.py`.

  Use plain Markdown headers and bullet lists. Do not write a YAML
  frontmatter block (this isn't an ISSUE.md). Do not summarize tasks
  beyond the audit findings here — Task 5 will append the per-task `[x]`
  status block.

  Out of scope:
  - Do NOT edit `shared/ci-defaults.yml`.
  - Do NOT edit `tools/sla_diff.py`.
  - Do NOT edit `templates/*/build.py`.
  - Do NOT introduce a 2-way `gruene_noe_kleinformat` preset (RESEARCH.md
    §E6 — flagged as out of scope until a 4th small-format template lands).
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/post-migration-dsl-hygiene && \
      test -f .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      grep -q 'Audit C1' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      grep -q 'Audit C2' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      grep -q '_LEGACY_LAYER_NAMES' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      grep -q 'No hoist candidates remain' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      echo "EXECUTION.md audit sections present"
    </automated>
  </verify>
  <done>
    - `.issues/post-migration-dsl-hygiene/EXECUTION.md` exists
    - Contains a `## Audit C1` section with the 23/11 keys + 0/0 hoist-candidate counts
    - Contains a `## Audit C2` section concluding `_LEGACY_LAYER_NAMES` is complete-as-is
    - No edit was made to `shared/ci-defaults.yml`, `tools/sla_diff.py`, or any `templates/*/build.py`
  </done>
  <commit_message>9: docs(issues): record extras + legacy-layer audit outcomes</commit_message>
</task>

<task type="auto">
  <name>Task 5: Final gate — full test suites + bin/validate --ci + tools/check_ci.py + finalize EXECUTION.md</name>
  <inputs>
    - The work landed by Tasks 1-4
    - bin/validate (CI runner over all 3 templates: sla_diff --strict + visual_diff)
    - tools/check_ci.py (general CI lint helper)
    - .github/workflows/pages.yml (CI gate; line 91 runs `python3 -m unittest discover tools/sla_lib/tests`)
    - ISSUE.md (7 acceptance criteria — must each be checked off)
  </inputs>
  <outputs>
    - .issues/post-migration-dsl-hygiene/EXECUTION.md updated with task-by-task `[x]` status, gate transcripts (or summaries), and any P3 follow-ups noted
  </outputs>
  <files>.issues/post-migration-dsl-hygiene/EXECUTION.md</files>
  <action>
  Run the full final-gate suite from the worktree root and append the
  results to EXECUTION.md. ALL THREE gates must exit 0 before the executor
  hands off; if any gate fails, fix and re-run rather than proceeding.

  Gates to run (in this order):

  1. **Pytest discovery** — local development equivalence.
     `pytest tools/sla_lib/tests -q`
     Catches lint-class issues unittest tolerates.

  2. **Unittest discover** — CI equivalence (this is mandatory; #16's
     stray `import pytest` was caught only here).
     `python3 -m unittest discover tools/sla_lib/tests`

  3. **Visual diff CI gate** — confirms the Impressum API widening hasn't
     regressed any template's reproducibility against committed gallery
     PDFs.
     `bin/validate --ci`
     Even though no template `build.py` files were modified, this gate
     is the correctness guard: a regression here would mean Task 1's
     emit() refactor changed the byte output for the existing 1-Run
     default path — the test_blocks.py suite alone is necessary but not
     sufficient.

  4. **CI lint** — repo's general CI sanity helper.
     `tools/check_ci.py`

  Once all four exit 0, finalize EXECUTION.md:

  - Add a `## Tasks` section listing each plan task with `[x]` status:
    - [x] Task 1: Widen the Impressum dataclass and emit()
    - [x] Task 2: Add 4 unittest-style coverage tests
    - [x] Task 3: Add ZeitungConverterFreshRun mirror class
    - [x] Task 4: Document the C1 + C2 audit outcomes
    - [x] Task 5: Final gate

  - Add a `## Acceptance criteria` section mapping ISSUE.md's 7 boxes to
    plan tasks and ticking each:
    - [x] Impressum block accepts `prefix_text`/`prefix_font`,
      `rotation_deg`, heading/spacer/body schema; each gap has a unit
      test in test_blocks.py — Tasks 1 + 2.
    - [x] `ZeitungConverterFreshRun` exists in test_sla_to_dsl.py — Task 3.
    - [x] `extra_doc_attrs` / `extra_pdf_attrs` audit completed; 0 hoist
      candidates documented — Task 4.
    - [x] `_LEGACY_LAYER_NAMES` audit completed; complete-as-is documented — Task 4.
    - [x] `pytest tools/sla_lib/tests` green AND `python3 -m unittest discover tools/sla_lib/tests` green — Task 5.
    - [x] `bin/validate --ci` green for all three templates — Task 5.
    - [x] No visual_diff drift against committed gallery PDFs — Task 5.

  - Add a `## P3 follow-ups (out of scope here)` section noting:
    - Substituting the three primitive `TextFrame(trail_style='Impressum',...)`
      corpus sites in `templates/*/build.py` for `Impressum(...)` block calls
      (RESEARCH.md §E2). Saves ~36 LOC across the three templates but adds
      visual_diff churn risk; defer until next hygiene pass or until the
      user explicitly asks.
    - Optional `gruene_noe_kleinformat` 2-way preset for Postkarte+Plakat
      shared values (RESEARCH.md §E6). Re-evaluate when a 4th
      small-format template lands.
    - Optional `PlakatConverterFreshRun` for symmetry with Postkarte and
      Zeitung. Trivially mirror-able if the user wants full converter
      coverage.

  Do NOT push, do NOT open a PR. The orchestrator handles commit and PR.

  Constraint: each gate's transcript snippet (last ~10 lines) MUST be
  pasted under a fenced code block in EXECUTION.md so reviewers can see
  the green status without re-running locally.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/post-migration-dsl-hygiene && \
      pytest tools/sla_lib/tests -q && \
      python3 -m unittest discover tools/sla_lib/tests && \
      bin/validate --ci && \
      python3 tools/check_ci.py && \
      grep -q '## Tasks' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      grep -q '## Acceptance criteria' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      grep -q 'P3 follow-ups' .issues/post-migration-dsl-hygiene/EXECUTION.md && \
      ! grep -rn '^import pytest$\|^import pytest ' tools/sla_lib/tests/ && \
      echo "ALL FINAL GATES GREEN"
    </automated>
  </verify>
  <done>
    - `pytest tools/sla_lib/tests -q` exits 0
    - `python3 -m unittest discover tools/sla_lib/tests` exits 0 (CI equivalence)
    - `bin/validate --ci` exits 0 for all 3 templates (no visual_diff drift)
    - `tools/check_ci.py` exits 0
    - No `import pytest` in any file under `tools/sla_lib/tests/`
    - EXECUTION.md contains `## Tasks` (5×`[x]`), `## Acceptance criteria` (7×`[x]`), `## P3 follow-ups` sections
    - All 7 acceptance criteria from ISSUE.md mapped 1-to-1 to plan tasks and ticked
  </done>
  <commit_message>9: chore(issue): finalize post-migration-dsl-hygiene hand-off</commit_message>
</task>

</tasks>

<verification>
After all tasks, the orchestrator's commit pipeline will run. Before that,
the executor must confirm:

- `pytest tools/sla_lib/tests -q` exits 0 (local-dev parity)
- `python3 -m unittest discover tools/sla_lib/tests` exits 0 (CI parity)
- `bin/validate --ci` exits 0 (visual_diff over all 3 templates)
- `tools/check_ci.py` exits 0 (general CI lint)
- `grep -rn 'import pytest' tools/sla_lib/tests/` returns nothing
- EXECUTION.md contains all required sections

Do NOT push. Do NOT open a PR. Orchestrator handles git operations.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:

1. Impressum block accepts `prefix_text` / `prefix_font`, `rotation_deg`,
   and the heading/spacer/body schema; each gap has at least one unit
   test in `tools/sla_lib/tests/test_blocks.py`. — **Tasks 1 + 2.**
2. `ZeitungConverterFreshRun` class exists in `test_sla_to_dsl.py`
   mirroring `PostkarteConverterFreshRun` / `PlakatRoundTrip`. — **Task 3.**
3. `extra_doc_attrs` / `extra_pdf_attrs` audit completed; any
   cross-template-identical keys hoisted. (Outcome: 0 hoist candidates
   identified empirically — recorded in EXECUTION.md.) — **Task 4.**
4. `_LEGACY_LAYER_NAMES` audit completed; documented as complete-as-is
   (no additions needed for the three current templates). — **Task 4.**
5. `pytest tools/sla_lib/tests` green AND
   `python3 -m unittest discover tools/sla_lib/tests` green. — **Task 5.**
6. `bin/validate --ci` green for ALL three templates. — **Task 5.**
7. No visual_diff drift against committed gallery PDFs. — **Task 5
   (covered by `bin/validate --ci`).**

Non-goals (must NOT appear in any task output):
- New template migrations.
- DSL surface changes outside `Impressum`.
- Converter (`tools/sla_to_dsl.py`) behavioural changes.
- Block additions beyond extending `Impressum`.
- `templates/*/build.py` edits (no Impressum corpus substitutions in this issue).
- `shared/ci-defaults.yml` edits.
- `tools/sla_diff.py` edits (specifically: no `_LEGACY_LAYER_NAMES` widening).
- Pushing or opening a PR.
</success_criteria>
