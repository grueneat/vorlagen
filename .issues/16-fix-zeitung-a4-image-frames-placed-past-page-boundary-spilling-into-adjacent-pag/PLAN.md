# Plan: Fix Zeitung A4 — image frames placed past page boundary

<objective>
What this plan accomplishes:
Fix the two right-edge image frames in `templates/zeitung-a4-grun/build.py` that
overflow the page bounds by ~207 mm (Frame A "P9 Spread" on print page 10;
Frame B unnamed dark-green polygon misattributed to print page 12 instead of
print page 13). The mechanical fix is two single-coordinate edits in build.py
plus one page-attribution change. To land it without breaking the existing
round-trip CI gate (`tools/sla_diff.py --strict`), we add a per-template opt-out
flag `meta.yml::sla_diff_strict: false` and gate `_run_sla_diff_strict` on it.

Why it matters:
After #14 added the `brand:inside_page` rule, zeitung silences it via a rule-level
override. This plan makes the underlying frames clean (so the override no longer
hides the two named bugs) while preserving silencing for the residual `u2950`
cover-polygon overflow which is tracked separately as GH #39.

Scope:
IN — Frames A and B (per Locked decisions #1, #2 in RESEARCH.md). New per-template
flag `sla_diff_strict`. Override rewording. Test count update. Regen
`template.sla` + previews + page PNGs. README divergence note. Final
`structural_check --all` + `unittest discover` green.

OUT — Frames C and D (within bleed envelope, not flagged — Locked decision #3).
u2950 cover-polygon (GH #39 follow-up — Locked decision #4). Per-frame allowlist
in `tools/sla_diff.py` (Locked decision #5). Visual baseline regen
(`baseline.pdf` stays untouched; PR reviewer rebases). `SpreadImage` migration
(PDF evidence shows empty placeholder — Locked decision #1).

No CONTEXT.md exists for this issue. Decisions come from RESEARCH.md's "Locked
decisions" table; those are binding.
</objective>

<context>
Issue: @.issues/16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag/ISSUE.md
Research: @.issues/16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag/RESEARCH.md
Codebase evidence: @.issues/16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag/research/codebase.md
Pitfalls: @.issues/16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag/research/pitfalls.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

# Frame A — TRUE error — templates/zeitung-a4-grun/build.py:1802-1811
page9.add(ImageFrame(
    x_mm=209.99999999993608,    # MUST become 0.0. Keep w_mm/h_mm/anname intact.
    y_mm=0,
    w_mm=209.9999999999361,
    h_mm=126.13945871829057,
    layer=0,
    image='',
    line_width_pt=1,
    anname="P9 Spread",          # PRESERVE — INJECT_MAP + CONSTRAINTS depend on it.
))

# Frame B — TRUE error — templates/zeitung-a4-grun/build.py:2061-2071
page11.add(ImageFrame(           # MUST become page12.add(...)
    x_mm=209.99999999999991,    # MUST become 0.0
    y_mm=-0.1807155930984082,    # KEEP (research labels this "y=-0.18")
    w_mm=210.7990642201835,      # KEEP (within bleed envelope on the destination page)
    h_mm=297.1807155930968,
    layer=0,
    image='',
    fill='Dunkelgrün',
    line_width_pt=1,
    local_offset_mm=(0.3303109072374783, -0.3257155930969475),
))

# INJECT_MAP consumer of "P9 Spread" — build.py:2504 — DO NOT TOUCH
# (anname stays "P9 Spread"; the move preserves it)
"P9 Spread": ("themen_klimaschutz_solar", 210, 126.1),

# CONSTRAINTS consumer — build.py:2555 — DO NOT TOUCH
same_size("P9 Spread", name="p9_spread_anchor"),

# meta.yml jsonschema validator — tools/sla_lib/builder/meta_schema.py
# Currently validates ONLY brand_overrides. The module exposes:
#   load_brand_overrides(slug, root=None) -> set[str]
# `meta` elsewhere is consumed as a raw dict (yaml.safe_load) — see render_pipeline.py.
# NEW helper to add (T01):
#   load_sla_diff_strict(slug, root=None) -> bool   (defaults True; reads top-level key)

# render_pipeline gate — tools/render_pipeline.py:384-408
def _run_sla_diff_strict(tid, tdir, meta):
    original_rel = meta.get("original_sla", "")
    if not original_rel:
        print(f"[{tid}] skipping sla_diff — no original_sla in meta.yml", file=sys.stderr)
        return 0
    # NEW (T02): if not meta.get("sla_diff_strict", True): return 0
    original_abs = (tdir / original_rel).resolve()
    template_sla = tdir / "template.sla"
    r = subprocess.run(["python3", str(ROOT / "tools" / "sla_diff.py"),
        "--left", str(original_abs), "--right", str(template_sla),
        "--strict", "--allow-brand-extras"], capture_output=True, text=True)
    ...

# inside_page baseline (verified by harness in research/codebase.md §3):
#   today (override removed)              -> 3 errors: P9 Spread, <unnamed ImageFrame>, u2950
#   after T04+T05 (override removed)      -> 1 error : u2950 only
#   after T04+T05 (override active per T03) -> 0 errors

# _load_zeitung_doc() helper exists in test_zeitung_overflow.py:41-48
# (importlib.util-based loader; reuse verbatim in T07).
</interfaces>

Key files:
@templates/zeitung-a4-grun/build.py — frame moves at lines 1802 and 2061
@templates/zeitung-a4-grun/meta.yml — flag + override rewording
@tools/sla_lib/builder/meta_schema.py — schema extension + new loader
@tools/render_pipeline.py — _run_sla_diff_strict gate
@tools/sla_lib/tests/test_zeitung_overflow.py — count update from 3 to 1
@templates/zeitung-a4-grun/README.md — divergence note
@bin/render-gallery — wrapper for tools/render_pipeline.py:main (regen step)
</context>

<commit_format>
Format: conventional with numeric issue prefix (per `.issues/config.yaml`).
Pattern: `16: <type>(<scope>): <subject>`
Examples:
  16: feat(meta_schema): add sla_diff_strict opt-out flag
  16: fix(zeitung): move P9 Spread frame to page-local origin
  16: chore(zeitung): regenerate template.sla and gallery previews
One commit per task (8 commits total). Atomic PR — see "Risks and verification".
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="true">
  <name>Task 1: Add `sla_diff_strict` field to meta.yml schema</name>
  <files>tools/sla_lib/builder/meta_schema.py, tools/sla_lib/tests/test_meta_schema.py</files>
  <depends-on>none</depends-on>
  <behavior>
  - `load_sla_diff_strict("zeitung-a4-grun")` returns `False` when meta.yml has
    `sla_diff_strict: false` (will be False after T03; today defaults to True,
    so the False-path test uses a tempdir fixture).
  - `load_sla_diff_strict(<other-template>)` returns `True` when key is absent
    (e.g. `postkarte-a6-quer`).
  - `load_sla_diff_strict("nonexistent-slug")` returns `True` (no meta.yml).
  - Schema-violating values (`sla_diff_strict: "no"`, `sla_diff_strict: 1`)
    raise `ValueError`, consistent with the existing brand_overrides validator
    pattern at meta_schema.py:71-78.
  - Existing `load_brand_overrides` behaviour unchanged for all templates.
  </behavior>
  <action>
  RED: Create `tools/sla_lib/tests/test_meta_schema.py` (new file). Use stdlib
  `unittest`; mirror the import + ROOT-walk pattern from
  `tools/sla_lib/tests/test_zeitung_overflow.py:28-36`. Five tests:

  ```python
  import tempfile, unittest
  from pathlib import Path
  import sys
  ROOT = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(ROOT / "tools"))
  from sla_lib.builder.meta_schema import load_sla_diff_strict, load_brand_overrides

  class SlaDiffStrictTests(unittest.TestCase):
      def test_default_true_for_template_without_flag(self):
          self.assertTrue(load_sla_diff_strict("postkarte-a6-quer"))

      def test_default_true_for_unknown_slug(self):
          self.assertTrue(load_sla_diff_strict("does-not-exist"))

      def test_false_when_meta_opts_out(self):
          with tempfile.TemporaryDirectory() as td:
              tdir = Path(td) / "templates" / "fake-tpl"
              tdir.mkdir(parents=True)
              (tdir / "meta.yml").write_text("id: fake-tpl\nsla_diff_strict: false\n")
              self.assertFalse(load_sla_diff_strict("fake-tpl", root=Path(td)))

      def test_invalid_type_raises(self):
          with tempfile.TemporaryDirectory() as td:
              tdir = Path(td) / "templates" / "fake-tpl"
              tdir.mkdir(parents=True)
              (tdir / "meta.yml").write_text('id: fake-tpl\nsla_diff_strict: "no"\n')
              with self.assertRaises(ValueError):
                  load_sla_diff_strict("fake-tpl", root=Path(td))

      def test_brand_overrides_loader_unchanged(self):
          ids = load_brand_overrides("zeitung-a4-grun")
          self.assertIn("brand:line_spacing_0.9", ids)
          self.assertIn("brand:inside_page", ids)
  ```

  GREEN: In `tools/sla_lib/builder/meta_schema.py`, add (alongside
  `_BRAND_OVERRIDE_SCHEMA` and `load_brand_overrides`):

  ```python
  _SLA_DIFF_STRICT_SCHEMA: dict = {"type": "boolean"}


  def load_sla_diff_strict(slug: str, root: Path | None = None) -> bool:
      """Return per-template `sla_diff_strict` flag (default True).

      Templates that intentionally diverge from their upstream SLA opt out
      by setting `sla_diff_strict: false` at the top level of meta.yml.
      Used by tools/render_pipeline.py::_run_sla_diff_strict to skip the
      strict round-trip diff for opted-out templates (issue #16).
      """
      p = _meta_path(slug, root)
      if not p.exists():
          return True
      try:
          data = yaml.safe_load(p.read_text(encoding="utf-8"))
      except yaml.YAMLError as e:
          raise ValueError(f"meta.yml at {p} is not valid YAML: {e}") from e
      if not isinstance(data, dict) or "sla_diff_strict" not in data:
          return True
      value = data["sla_diff_strict"]
      try:
          jsonschema.validate(instance=value, schema=_SLA_DIFF_STRICT_SCHEMA)
      except jsonschema.ValidationError as e:
          raise ValueError(
              f"meta.yml sla_diff_strict at {p} must be a boolean: {e.message}"
          ) from e
      return bool(value)
  ```

  REFACTOR: keep `load_sla_diff_strict` symmetric with `load_brand_overrides`
  (same `_meta_path` helper, same YAML parse error handling). Additive change
  only — do not modify the existing function or schema constant.
  </action>
  <verify>
    <automated>python3 -m unittest discover tools/sla_lib/tests -p "test_meta_schema.py" -v</automated>
  </verify>
  <done>
  - New test module `tools/sla_lib/tests/test_meta_schema.py` with 5 tests, all pass.
  - `load_sla_diff_strict` exported from `meta_schema.py`.
  - Full suite `python3 -m unittest discover tools/sla_lib/tests` still passes
    (no regression on `test_zeitung_overflow.py`; its update lands in T07).
  </done>
  <dont>
  - Don't introduce a `TemplateMeta` dataclass — `meta` is a raw dict everywhere
    (`render_pipeline.py:_orchestrate_single` reads `meta.get(...)`). RESEARCH.md
    used `@dataclass TemplateMeta` notation conceptually; the real code is
    dict-based. Stay dict-based.
  - Don't move `_BRAND_OVERRIDE_SCHEMA` or refactor the existing function.
  - Don't add `sla_diff_strict: false` to zeitung's meta.yml here — that is T03.
  - Don't try to add per-frame ignores to `tools/sla_diff.py` — out of scope;
    the per-template flag is the chosen mechanism (Locked decision #5).
  </dont>
</task>

<task id="T02" type="auto" tdd="true">
  <name>Task 2: Gate `_run_sla_diff_strict` on `sla_diff_strict` flag</name>
  <files>tools/render_pipeline.py, tools/sla_lib/tests/test_render_pipeline.py</files>
  <depends-on>T01</depends-on>
  <behavior>
  - When `meta.get("sla_diff_strict", True)` is `False`, `_run_sla_diff_strict`
    returns `0` immediately, prints a one-line skip message, and does NOT
    invoke `subprocess.run`.
  - When the flag is `True` (or absent), behaviour is unchanged
    (calls `tools/sla_diff.py --strict --allow-brand-extras` via subprocess).
  - When `original_sla` is missing, the existing skip path still wins (it is
    checked first — order matters for log clarity).
  </behavior>
  <action>
  RED: In `tools/sla_lib/tests/test_render_pipeline.py`, add a new TestCase
  class `SlaDiffStrictGateTests`. Two tests; mirror the existing import idiom
  (check the file head for how `render_pipeline` is imported — likely
  `from render_pipeline import ...` after sys.path insert):

  ```python
  from unittest.mock import patch
  import subprocess

  class SlaDiffStrictGateTests(unittest.TestCase):
      def test_skips_when_meta_opts_out(self):
          from render_pipeline import _run_sla_diff_strict
          meta = {"id": "fake", "original_sla": "../../fake.sla", "sla_diff_strict": False}
          with patch("subprocess.run") as mock_run:
              rc = _run_sla_diff_strict("fake", Path("/tmp/fake-tdir"), meta)
          self.assertEqual(rc, 0)
          mock_run.assert_not_called()

      def test_runs_when_flag_absent(self):
          from render_pipeline import _run_sla_diff_strict
          meta = {"id": "fake", "original_sla": "../../fake.sla"}
          fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
          with patch("subprocess.run", return_value=fake_result) as mock_run:
              rc = _run_sla_diff_strict("fake", Path("/tmp/fake-tdir"), meta)
          self.assertEqual(rc, 0)
          self.assertEqual(mock_run.call_count, 1)
          self.assertIn("--strict", mock_run.call_args.args[0])
  ```

  GREEN: Edit `tools/render_pipeline.py:_run_sla_diff_strict` (lines 384-408).
  Insert the gate AFTER the `original_sla` skip and BEFORE building
  `original_abs`:

  ```python
  def _run_sla_diff_strict(tid: str, tdir: Path, meta: dict) -> int:
      """Run tools/sla_diff.py --strict against original_sla. Returns exit code."""
      original_rel = meta.get("original_sla", "")
      if not original_rel:
          print(f"[{tid}] skipping sla_diff — no original_sla in meta.yml", file=sys.stderr)
          return 0
      if not meta.get("sla_diff_strict", True):
          print(
              f"[{tid}] skipping strict sla_diff — meta.yml::sla_diff_strict=false "
              f"(template intentionally diverges from upstream; see issue #16)",
              file=sys.stderr,
          )
          return 0
      original_abs = (tdir / original_rel).resolve()
      # ... rest unchanged
  ```

  Reading `sla_diff_strict` directly off `meta` (rather than calling
  `load_sla_diff_strict`) is correct here because `_orchestrate_single` already
  has `meta` as a parsed dict. T01's helper exists for callers without the
  dict in hand.

  REFACTOR: none. Single-block insertion.
  </action>
  <verify>
    <automated>python3 -m unittest discover tools/sla_lib/tests -p "test_render_pipeline.py" -v</automated>
  </verify>
  <done>
  - The gate fires on `sla_diff_strict: False`; no subprocess invocation.
  - The gate is bypassed when the key is absent (default-True semantics).
  - Both new tests pass.
  - All existing `test_render_pipeline.py` tests still pass.
  </done>
  <dont>
  - Don't add `--ignore-pageobject-by-anname` to `tools/sla_diff.py` — out of
    scope (Locked decision #5; pitfalls P-1 Option 2 was REJECTED).
  - Don't gate based on `load_sla_diff_strict()` here — `meta` is already a dict.
  - Don't reorder the existing `original_sla`-missing skip; it stays first so
    `[tid] skipping sla_diff — no original_sla` remains the canonical message.
  - Don't drop `--strict` globally — that weakens validation for the other 8
    round-trip templates (pitfalls P-1 Option 1 was REJECTED).
  </dont>
</task>

<task id="T03" type="auto" tdd="false">
  <name>Task 3: Set `sla_diff_strict: false` on zeitung + reword inside_page override</name>
  <files>templates/zeitung-a4-grun/meta.yml</files>
  <depends-on>T01, T02</depends-on>
  <behavior>
  - `meta.yml` carries a top-level `sla_diff_strict: false` (with comment).
  - The `brand_overrides[].id == "brand:inside_page"` entry's `reason` field
    is rewritten to point at GH #39 (the u2950 cover-polygon follow-up),
    explicitly stating the override silences ONLY the residual u2950 case
    after #16's frame-moves land.
  - The `brand:line_spacing_0.9` override is untouched.
  - All other meta.yml keys (id, version, title, masters, etc.) untouched.
  </behavior>
  <action>
  Edit `templates/zeitung-a4-grun/meta.yml`. Two surgical changes:

  1. Replace the existing inside_page override block (current lines 31-36) with:

  ```yaml
    - id: brand:inside_page
      reason: >-
        Residual after issue #16: the rotated cover-page polygon `u2950`
        (build.py:246-256, 148.6×220.5 mm at (216.41, 155.57), rotation 90°,
        fill Dunkelgrün) overflows the page bottom by ~4.17 mm — its
        rotation-aware bbox extends below y=300. Tracked separately in
        GH #39. Removing this override requires resolving #39 first
        (do not delete pre-emptively — `structural_check --all` will go
        red).
  ```

  2. Insert (top-level; recommended placement: directly below the
  `previews_for_sla:` line):

  ```yaml
  # Issue #16 — this template intentionally diverges from gruene-zeitung-
  # vorlage-original.sla at two frames (build.py:1802 P9 Spread, build.py:2061
  # unnamed page-12 polygon — both authoring drift in the upstream Scribus
  # original). Strict round-trip diff is opted out here; the divergence is
  # documented in this template's README.md and gated by render_pipeline.py
  # honouring this flag.
  sla_diff_strict: false
  ```

  No other meta.yml keys touched. Verification: see the `<verify>` block.
  </action>
  <verify>
    <automated>PYTHONPATH=tools python3 -c "from sla_lib.builder.meta_schema import load_sla_diff_strict, load_brand_overrides; assert load_sla_diff_strict('zeitung-a4-grun') is False, 'flag did not load'; assert 'brand:inside_page' in load_brand_overrides('zeitung-a4-grun'), 'override gone'; print('OK')" &amp;&amp; PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun</automated>
  </verify>
  <done>
  - `load_sla_diff_strict('zeitung-a4-grun') is False`.
  - `load_brand_overrides('zeitung-a4-grun')` still contains `'brand:inside_page'`.
  - `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` exits 0.
  - The reworded override reason explicitly references GH #39.
  </done>
  <dont>
  - Don't delete the `brand:inside_page` override — `u2950` is still a real
    overflow tracked by GH #39 (Locked decision #4).
  - Don't touch `brand:line_spacing_0.9`.
  - Don't change `previews_for_sla` SHA here — that is T06.
  - Don't fix u2950 inline (GH #39's responsibility).
  </dont>
</task>

<task id="T04" type="auto" tdd="false">
  <name>Task 4: Move Frame A "P9 Spread" to page-local origin (x=0)</name>
  <files>templates/zeitung-a4-grun/build.py</files>
  <depends-on>T03</depends-on>
  <behavior>
  - The `P9 Spread` ImageFrame on `page9` (build.py:1802-1811) sits at
    `x_mm=0.0, y_mm=0` (was `x_mm≈210, y_mm=0`).
  - `w_mm`, `h_mm`, `layer`, `image`, `line_width_pt`, `anname` UNCHANGED.
  - `INJECT_MAP["P9 Spread"]` (build.py:2504) and
    `same_size("P9 Spread", name="p9_spread_anchor")` (build.py:2555)
    untouched and still resolve.
  - `inside_page` rule (override bypassed) reports 2 errors instead of 3
    (P9 Spread no longer flagged; <unnamed ImageFrame> + u2950 remain).
  </behavior>
  <action>
  Single edit in `templates/zeitung-a4-grun/build.py:1802-1811`. Change ONE field:

  ```python
  # OLD (lines 1802-1811):
      page9.add(ImageFrame(
          x_mm=209.99999999993608,
          y_mm=0,
          w_mm=209.9999999999361,
          h_mm=126.13945871829057,
          layer=0,
          image='',
          line_width_pt=1,
          anname="P9 Spread",  # issue #13
      ))

  # NEW:
      page9.add(ImageFrame(
          x_mm=0.0,
          y_mm=0,
          w_mm=209.9999999999361,
          h_mm=126.13945871829057,
          layer=0,
          image='',
          line_width_pt=1,
          anname="P9 Spread",  # issue #13; moved to page-local origin in #16
      ))
  ```

  No edits to INJECT_MAP, CONSTRAINTS, or anything else. The whole change is
  one number: `209.99999999993608` -> `0.0` (and a one-line comment update).
  </action>
  <verify>
    <automated>PYTHONPATH=tools python3 -c "import importlib.util, sys; sys.path.insert(0, 'tools'); from sla_lib.builder.brand_constraints import _InsidePageRule; spec=importlib.util.spec_from_file_location('z','templates/zeitung-a4-grun/build.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); doc=mod.build_doc(); rule=_InsidePageRule(id='brand:inside_page', name='x', description='x'); errs=[v for v in rule.check(list(doc.iter_all_primitives()), doc) if v.severity=='error']; assert len(errs)==2, f'expected 2 errors after T04, got {len(errs)}: {[v.message for v in errs]}'; assert not any('P9 Spread' in t for v in errs for t in v.targets), 'P9 Spread still flagged'; print('OK')"</automated>
  </verify>
  <done>
  - build.py:1802 `x_mm` is `0.0`.
  - `anname="P9 Spread"` preserved; INJECT_MAP and CONSTRAINTS still resolve.
  - Inside-page rule reports 2 errors (down from 3); none target `"P9 Spread"`.
  </done>
  <dont>
  - Don't replace the frame with `SpreadImage(...).place(page9, page10)` —
    PDF evidence (research/codebase.md §5) confirms there is no rendered image;
    the frame is an empty placeholder. SpreadImage would emit annames
    `"P9 Spread · left/right"` which break INJECT_MAP and CONSTRAINTS
    (Locked decision #1; pitfalls P-5, P-9).
  - Don't rename `anname="P9 Spread"`.
  - Don't touch `w_mm`, `h_mm`, `y_mm`, `layer`, `image`, `line_width_pt`.
  - Don't regenerate `template.sla` here — that is T06.
  </dont>
</task>

<task id="T05" type="auto" tdd="false">
  <name>Task 5: Move Frame B (unnamed Dunkelgrün polygon) from page11 to page12</name>
  <files>templates/zeitung-a4-grun/build.py</files>
  <depends-on>T04</depends-on>
  <behavior>
  - The unnamed Dunkelgrün ImageFrame currently in `page11.add(...)`
    (build.py:2061-2071) lives in `page12.add(...)` instead, with `x_mm=0.0`.
  - `y_mm`, `w_mm`, `h_mm`, `layer`, `image`, `fill`, `line_width_pt`,
    `local_offset_mm` UNCHANGED.
  - `inside_page` rule (override bypassed) now reports 1 error (only u2950).
  - The frame ends up on `page12` (0-indexed = print page 13) — the
    decorative dark-green tile's intended page per Locked decision #2.
    On the destination page, `(x=0, y=-0.18, w=210.799, h=297.18)` is inside
    the bleed envelope `[-3, 213] × [-3, 300]` (verified in pitfalls.md §P-8).
  </behavior>
  <action>
  Single edit in `templates/zeitung-a4-grun/build.py:2061-2071`. Change two
  things: page binding (`page11` -> `page12`) and `x_mm` (~210 -> `0.0`).
  EVERY OTHER FIELD verbatim, INCLUDING `local_offset_mm`.

  ```python
  # OLD (lines 2061-2071):
      page11.add(ImageFrame(
          x_mm=209.99999999999991,
          y_mm=-0.1807155930984082,
          w_mm=210.7990642201835,
          h_mm=297.1807155930968,
          layer=0,
          image='',
          fill='Dunkelgrün',
          line_width_pt=1,
          local_offset_mm=(0.3303109072374783, -0.3257155930969475),
      ))

  # NEW:
      page12.add(ImageFrame(
          x_mm=0.0,
          y_mm=-0.1807155930984082,
          w_mm=210.7990642201835,
          h_mm=297.1807155930968,
          layer=0,
          image='',
          fill='Dunkelgrün',
          line_width_pt=1,
          local_offset_mm=(0.3303109072374783, -0.3257155930969475),
      ))
  ```

  Keep field order verbatim with the original (minimum-diff). After the edit,
  the harness from T04 (now expecting 1 residual error) is the verification.
  </action>
  <verify>
    <automated>PYTHONPATH=tools python3 -c "import importlib.util, sys; sys.path.insert(0, 'tools'); from sla_lib.builder.brand_constraints import _InsidePageRule; spec=importlib.util.spec_from_file_location('z','templates/zeitung-a4-grun/build.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); doc=mod.build_doc(); rule=_InsidePageRule(id='brand:inside_page', name='x', description='x'); errs=[v for v in rule.check(list(doc.iter_all_primitives()), doc) if v.severity=='error']; assert len(errs)==1, f'expected 1 error after T04+T05, got {len(errs)}: {[v.message for v in errs]}'; assert errs[0].targets==('u2950',), f'expected only u2950, got {errs[0].targets}'; print('OK')"</automated>
  </verify>
  <done>
  - build.py:2061 reads `page12.add(ImageFrame(x_mm=0.0, ...))` (was `page11`).
  - `inside_page` rule reports exactly 1 error: `u2950`.
  - All other field values unchanged.
  </done>
  <dont>
  - Don't trim `w_mm` from `210.7990642201835` to `210.0` — pitfalls P-8 + P-11
    explicitly note this trim adds an `sla_diff` warning for zero correctness
    benefit (frame is inside bleed envelope on the destination page).
  - Don't drop `local_offset_mm` (Locked decision #2 says "preserve").
  - Don't add an `anname=` (the original frame is intentionally unnamed).
  - Don't move the frame to `page12` AND keep `x_mm=210` — that recreates the
    bug on the next page.
  </dont>
</task>

<task id="T06" type="auto" tdd="false">
  <name>Task 6: Regenerate template.sla, page PNGs, and previews_for_sla SHA</name>
  <files>templates/zeitung-a4-grun/template.sla, templates/zeitung-a4-grun/template-preview.sla, templates/zeitung-a4-grun/preview.pdf, templates/zeitung-a4-grun/page-*.png, templates/zeitung-a4-grun/meta.yml, site/public/templates/zeitung-a4-grun/*</files>
  <depends-on>T04, T05</depends-on>
  <behavior>
  - `template.sla` and `template-preview.sla` are regenerated from the edited
    build.py (the two moved frames are reflected in the SLA bytes).
  - `meta.yml::previews_for_sla` SHA is updated to `sha256(template.sla)` of
    the new SLA bytes (`tools/render_pipeline.py:_update_meta_hash`).
  - `page-*.png` and `preview.pdf` are regenerated from a fresh Scribus export.
  - `site/public/templates/zeitung-a4-grun/*` mirror is updated
    (`_mirror_to_site_public` in render_pipeline.py).
  - `bin/check-stale-previews zeitung-a4-grun` exits 0 (SHA matches).
  - `baseline.pdf` is NOT modified (do NOT regenerate; PR reviewer rebases —
    Locked decision #7; pitfalls P-15).
  </behavior>
  <action>
  Run the regen pipeline with visual diff disabled:

  ```bash
  bin/render-gallery --skip-visual-diff zeitung-a4-grun
  ```

  This wraps `tools/render_pipeline.py:main` (single-template invocation). It
  performs: build.py -> template.sla; render to preview.pdf via Scribus;
  rasterise to page-NN.png; **skip** sla_diff (gated by T03's
  `sla_diff_strict: false`); skip visual_diff (CLI flag); update SHA; mirror
  to site/public.

  If `bin/render-gallery zeitung-a4-grun` fails because Scribus is not
  reachable in the executor's environment (no /usr/bin/scribus, no xvfb), use
  the manual-regen fallback. Verify Scribus availability first:
  `which scribus && which xvfb-run`. If both are present, the wrapper works.
  If either is missing, the executor must STOP and surface the env gap to the
  user — the SHA bump and PNG regen require a real Scribus run; a dry-run is
  not acceptable.

  Manual fallback (only if `bin/render-gallery` is structurally broken — it
  should NOT be; it has been the canonical regen entry since #4):
  1. `python3 templates/zeitung-a4-grun/build.py` -> writes `template.sla`.
  2. `xvfb-run -a scribus -g -ns -py tools/render_to_pdf.py -- templates/zeitung-a4-grun/template.sla templates/zeitung-a4-grun/preview.pdf`
     (script name to be confirmed; `bin/render-gallery` is the abstraction
     precisely so this step is not hand-rolled).
  3. `pdftoppm -r 150 -png templates/zeitung-a4-grun/preview.pdf templates/zeitung-a4-grun/page` then zero-pad.
  4. `python3 -c "import hashlib, pathlib; p=pathlib.Path('templates/zeitung-a4-grun/template.sla'); print(hashlib.sha256(p.read_bytes()).hexdigest())"` -> paste into meta.yml `previews_for_sla:`.

  Strongly prefer `bin/render-gallery --skip-visual-diff` — the manual path is
  brittle.

  After regen, commit ALL of:
  - `templates/zeitung-a4-grun/template.sla`
  - `templates/zeitung-a4-grun/template-preview.sla` (if regenerated)
  - `templates/zeitung-a4-grun/preview.pdf`
  - `templates/zeitung-a4-grun/page-*.png` (delta only — use `git status` to enumerate)
  - `templates/zeitung-a4-grun/meta.yml` (the SHA line bump only)
  - `site/public/templates/zeitung-a4-grun/*` (mirror)

  DO NOT commit `templates/zeitung-a4-grun/baseline.pdf` even if it changes
  size; if `git status` shows it modified, `git checkout templates/zeitung-a4-grun/baseline.pdf`
  to revert. The visual baseline is the human reviewer's job.
  </action>
  <verify>
    <automated>bin/check-stale-previews zeitung-a4-grun &amp;&amp; PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun</automated>
  </verify>
  <done>
  - `bin/check-stale-previews zeitung-a4-grun` exits 0 (template.sla SHA matches
    meta.yml::previews_for_sla).
  - `templates/zeitung-a4-grun/template.sla` mtime is fresh.
  - `templates/zeitung-a4-grun/page-01.png` ... `page-09.png` (or however many
    pages the build emits) regenerated; no stray legacy single-digit `page-1.png`.
  - `git status` shows `baseline.pdf` UNMODIFIED.
  - `structural_check zeitung-a4-grun` exits 0 (override silences inside_page;
    other rules pass).
  </done>
  <dont>
  - Don't run `bin/render-gallery` WITHOUT `--skip-visual-diff` — the visual
    diff against `baseline.pdf` will fail because the two moved frames change
    the rendered pixels (pitfalls P-15).
  - Don't regenerate or commit `baseline.pdf`.
  - Don't manually edit the SHA in meta.yml — let `_update_meta_hash` write it.
  - Don't skip the `site/public/templates/zeitung-a4-grun/*` mirror update —
    the wrapper handles it; just commit the resulting changes.
  - Don't run sla_diff manually here — T02's gate now skips it for zeitung;
    that's the intended state.
  </dont>
</task>

<task id="T07" type="auto" tdd="false">
  <name>Task 7: Update test_zeitung_overflow.py — count 3 -> 1, rename, refresh docstring</name>
  <files>tools/sla_lib/tests/test_zeitung_overflow.py</files>
  <depends-on>T03, T04, T05, T06</depends-on>
  <behavior>
  - The first test `test_inside_page_finds_the_known_overflows_without_override`
    is renamed to `test_inside_page_finds_only_u2950_without_override` and
    asserts exactly 1 error whose `targets == ("u2950",)`.
  - The second test `test_inside_page_passes_with_override` is unchanged in
    intent (override is still in place; rule still skipped); only its docstring
    references are refreshed if it mentions the old "two named frames" framing.
  - Module docstring (lines 1-27) is rewritten to reflect post-#16 state: the
    two named frames are fixed; only u2950 remains, tracked in GH #39.
  - Test runtime stays under 2 s (`build_doc()` is the bottleneck; unchanged).
  </behavior>
  <action>
  Edit `tools/sla_lib/tests/test_zeitung_overflow.py`. Three changes:

  1. Replace the module docstring (lines 1-27) with:

  ```python
  """Regression tests for the residual zeitung inside_page overflow.

  Issue #16 fixed the two right-edge spread frames in build.py:
    - `P9 Spread` (build.py:1802) — moved from x=210 to x=0 on its own page;
      `anname` preserved so INJECT_MAP and CONSTRAINTS keep resolving.
    - Unnamed full-A4 Dunkelgrün polygon (build.py:2061) — moved from
      page11 (print 12) to page12 (print 13) at x=0.

  One residual overflow remains, tracked in GH #39:
    - Rotated cover-page polygon `u2950` (build.py:246-256) — Polygon at
      (216.41, 155.57, 148.60, 220.49, rotation 90°, fill Dunkelgrün).
      Rotation-aware bbox spans (-4.08, 155.57)→(216.41, 304.17), overshooting
      the page bottom by 4.17 mm. Silenced today by the rule-level
      `brand:inside_page` override (which now points at GH #39).
  """
  ```

  2. Replace `test_inside_page_finds_the_known_overflows_without_override`
  (lines 52-94) with:

  ```python
      def test_inside_page_finds_only_u2950_without_override(self):
          """After #16: only the cover-polygon u2950 (~4.17 mm) remains.

          Tracked in GH #39. If this count grows, a real new overflow has been
          introduced — investigate before bumping the assertion.
          """
          doc = _load_zeitung_doc()
          rule = _InsidePageRule(
              id="brand:inside_page",
              name="Frames inside page bounds",
              description="(test instance — bypasses brand_overrides)",
          )
          violations = rule.check(list(doc.iter_all_primitives()), doc)
          errors = [v for v in violations if v.severity == "error"]
          self.assertEqual(
              len(errors), 1,
              msg=(
                  f"expected exactly 1 inside_page error after #16 "
                  f"(rotated u2950 cover polygon), got {len(errors)}: "
                  f"{[v.message for v in errors]}"
              ),
          )
          self.assertEqual(errors[0].targets, ("u2950",))
  ```

  3. Leave `test_inside_page_passes_with_override` (lines 96-109) intact —
  the override is still in place (T03 reworded it, did not delete). If its
  inline comment mentions "two named frames" or "spread frames", refresh to
  "u2950 cover polygon (GH #39)". Do not change its assertions.
  </action>
  <verify>
    <automated>python3 -m unittest tools.sla_lib.tests.test_zeitung_overflow -v</automated>
  </verify>
  <done>
  - `test_inside_page_finds_only_u2950_without_override` passes; asserts
    exactly 1 error with target `u2950`.
  - `test_inside_page_passes_with_override` still passes (override active).
  - Module docstring reflects post-#16 state, references GH #39 for u2950.
  - Full suite `python3 -m unittest discover tools/sla_lib/tests` passes.
  </done>
  <dont>
  - Don't delete `test_inside_page_passes_with_override` — the override is
    still in place (T03 reworded; did not remove). The test still pins the
    "rule is in `skipped_brand_rules`" contract.
  - Don't add a new test pinning `P9 Spread`'s coordinate — the build.py edit
    is already enforced by the `inside_page`-clean assertion above (any
    re-regression to x=210 surfaces as a 2nd error).
  - Don't change the assertion to `len(errors) == 0` (would require fixing
    u2950 inline; out of scope).
  </dont>
</task>

<task id="T08" type="auto" tdd="false">
  <name>Task 8: README divergence note + final --all verification</name>
  <files>templates/zeitung-a4-grun/README.md</files>
  <depends-on>T01, T02, T03, T04, T05, T06, T07</depends-on>
  <behavior>
  - `templates/zeitung-a4-grun/README.md` carries a German section
    "Bekannte Abweichungen vom Original-SLA" explaining the two intentional
    frame moves and the `sla_diff_strict: false` flag, with references to
    issues #16 and #39.
  - `python3 -m sla_lib.builder.structural_check --all` exits 0.
  - `python3 -m unittest discover tools/sla_lib/tests` exits 0.
  - `bin/check-stale-previews` (no slug) exits 0 across all templates.
  </behavior>
  <action>
  Append to `templates/zeitung-a4-grun/README.md` (insert after the
  "Vorlagen-Generierung" section, around line 51):

  ```markdown
  ## Bekannte Abweichungen vom Original-SLA

  `gruene-zeitung-vorlage-original.sla` enthält zwei Bildrahmen, die der
  Scribus-Autor versehentlich um 210 mm nach rechts (auf den Off-Page-
  Scratch-Canvas) plaziert hat — sie rendern im Original-PDF nichts
  Sichtbares (verifiziert via `pdfimages -list`):

  - `P9 Spread` (build.py:1802, war `x_mm=210` auf `page9`) → korrigiert
    auf `x_mm=0` auf derselben Seite. `anname` bleibt erhalten, damit
    `INJECT_MAP` und `CONSTRAINTS` weiter aufgelöst werden. Issue #16.
  - Unbenannter Vollseiten-Dunkelgrün-Rahmen (build.py:2061, war
    `page11.add(...)` mit `x_mm=210`) → verschoben zu `page12.add(...)`
    mit `x_mm=0` (gedruckte Seite 13, dem ursprünglich gemeinten Ziel).
    Issue #16.

  Daher weicht `template.sla` an diesen zwei Stellen bewusst vom
  Original-SLA ab. Der Round-Trip-Check `tools/sla_diff.py --strict`
  ist für diese Vorlage entsprechend deaktiviert
  (`meta.yml::sla_diff_strict: false`); `tools/render_pipeline.py`
  überspringt den Strict-Diff für Templates mit diesem Flag.

  Eine dritte, davon unabhängige Überfüllung — der gedrehte
  Cover-Polygon `u2950` (build.py:246-256, ~4.17 mm Bottom-Overshoot) —
  bleibt vorerst durch den `brand_overrides[brand:inside_page]`-Eintrag
  abgedeckt und wird in GH #39 separat behoben.
  ```

  After the edit, run the final-verification block (the `<verify>` block
  below covers it). All three commands must exit 0; capture their output
  for `EXECUTION.md`.
  </action>
  <verify>
    <automated>PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all &amp;&amp; python3 -m unittest discover tools/sla_lib/tests &amp;&amp; bin/check-stale-previews</automated>
  </verify>
  <done>
  - README carries the German "Bekannte Abweichungen" section with refs to
    issues #16 and #39.
  - `structural_check --all` exits 0 (zeitung override active; other 8
    templates unchanged).
  - `unittest discover tools/sla_lib/tests` exits 0 (T01, T02, T07 tests
    green; no regression elsewhere).
  - `bin/check-stale-previews` exits 0 (all templates, including zeitung
    after T06's SHA bump).
  </done>
  <dont>
  - Don't reword existing README sections — additive change only.
  - Don't add the divergence note in English; the existing README is in
    German.
  - Don't reference internal RESEARCH.md or PLAN.md from README — those are
    workflow artefacts, not user docs.
  </dont>
</task>

</tasks>

<verification>
After all 8 tasks land, run the final checks (CI parity):

```bash
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
python3 -m unittest discover tools/sla_lib/tests
bin/check-stale-previews
```

All three commands MUST exit 0. If any returns non-zero, do NOT mark the issue
done — capture the failure in EXECUTION.md and triage. The most likely
failure modes are:

- `structural_check --all` non-zero -> check whether the `brand:inside_page`
  override is still in meta.yml after T03's rewording (a YAML indentation
  mistake can drop the entire block silently).
- `unittest discover` non-zero on `test_zeitung_overflow.py` -> T07's count
  update did not land OR T04/T05 frame moves did not land.
- `check-stale-previews` non-zero -> T06's `bin/render-gallery
  --skip-visual-diff` did not write `meta.yml::previews_for_sla`. Re-run T06.

Optional manual sanity (NOT a Claude action — for the human PR reviewer):

```bash
bin/render-gallery zeitung-a4-grun  # without --skip-visual-diff
```

If pages 10 / 13 in `templates/zeitung-a4-grun/page-NN.png` look wrong, the
reviewer rebases `baseline.pdf` per `docs/render-fidelity.md`.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance (rewritten per RESEARCH.md scope changes):

- `python3 -m sla_lib.builder.structural_check --all` reports zero
  `inside_page` errors on `zeitung-a4-grun` (override silences u2950;
  Frames A and B no longer overflow).
- The `meta.yml::brand_overrides[brand:inside_page]` entry on `zeitung-a4-grun`
  is REWORDED (not removed) and references GH #39 explicitly.
- `tools/sla_diff.py --strict` is OPT-OUT for `zeitung-a4-grun` via
  `meta.yml::sla_diff_strict: false`; `tools/render_pipeline.py:_run_sla_diff_strict`
  honours the flag and skips the call. The other 8 round-trip templates are
  unaffected (default `True`).
- `bin/render-gallery --skip-visual-diff zeitung-a4-grun` regenerated
  `template.sla`, `template-preview.sla`, `preview.pdf`, `page-NN.png`,
  `meta.yml::previews_for_sla` SHA, and the `site/public/...` mirror.
  `baseline.pdf` is UNMODIFIED.
- `tools/sla_lib/tests/test_zeitung_overflow.py` runs in <2 s and asserts
  exactly 1 `inside_page` error (`u2950`) without override; 0 with override.
- `tools/sla_lib/tests/test_meta_schema.py` exists with 5 tests covering
  `load_sla_diff_strict`'s default-True / explicit-false / invalid-type /
  missing-meta paths and a `load_brand_overrides` smoke regression.
- `tools/sla_lib/tests/test_render_pipeline.py` carries the
  `SlaDiffStrictGateTests` class with 2 tests proving the gate skips on
  opt-out and runs otherwise.
- `templates/zeitung-a4-grun/README.md` carries the "Bekannte Abweichungen"
  section in German referencing both #16 and #39.
- `python3 -m unittest discover tools/sla_lib/tests` exits 0.
</success_criteria>

<risks_and_verification>

## Atomic-PR reminder

All 8 commits land in ONE PR. Do not push intermediate commits to `main`. The
intermediate states between T03 (override rewording) and T05 (frame moves
complete) are still CI-green because the override silences `inside_page`
template-wide; but T06's `previews_for_sla` SHA depends on T04 and T05 having
landed. Recommended branch-local verification before opening the PR:

```bash
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
python3 -m unittest discover tools/sla_lib/tests
bin/check-stale-previews
```

All three exit 0 -> safe to open PR.

## Visual baseline rebase is the human reviewer's job

The PR will not include a regenerated `baseline.pdf`. The reviewer runs
`bin/render-gallery zeitung-a4-grun` (without `--skip-visual-diff`) locally,
compares the new `page-10.png` and `page-13.png` to the old `baseline.pdf`,
and either accepts the visual delta and rebases `baseline.pdf`, or kicks the
PR back. Per Locked decision #7 + pitfalls P-15, Claude does NOT inspect
PNGs.

## u2950 follow-up tracking — GH #39

The reworded override comment in T03 references #39 explicitly. If GH #39
does not exist when this issue is being executed, STOP at T03 and surface
the missing-issue gap before continuing — the override comment must point at
a real tracker or the rewording is misleading. The user's prior planning
session filed #39; verify with `gh issue view 39 -R GrueneAT/vorlagen` (or
a similar gh CLI invocation against the configured repo).

## `bin/render-gallery` decision tree (T06)

`bin/render-gallery` is a 14-line wrapper around `tools/render_pipeline.py:main`
(see `bin/render-gallery` shim verified during planning). It accepts CLI
flags including `--skip-visual-diff`. Test before relying on it:

```bash
bin/render-gallery --help   # confirm the wrapper resolves and prints render_pipeline help
which scribus xvfb-run     # confirm Scribus + xvfb available
```

If `bin/render-gallery --help` works AND Scribus + xvfb are present:
proceed with `bin/render-gallery --skip-visual-diff zeitung-a4-grun`.

If `bin/render-gallery` is broken or Scribus is missing: STOP and surface
the env gap to the user. Do NOT attempt the manual fallback unless
explicitly instructed — the manual path described in T06's `<action>` is a
last resort and risks producing inconsistent SHA / PNG / mirror state.
The Dockerfile at `Dockerfile.claude` already pins Scribus 1.6.5; if the
executor is in that container, both `scribus` and `xvfb-run` should be on PATH.

## Risk: T01's `load_sla_diff_strict` interaction with existing meta.yml validators

The new helper does NOT alter the existing `_BRAND_OVERRIDE_SCHEMA` flow. The
`test_brand_overrides_loader_unchanged` test in T01 is the regression
guard. If it ever fails, the executor has accidentally refactored
`load_brand_overrides` — revert and try again with a strictly additive change.

## Risk: T07 import order vs. T04/T05 frame moves

`test_zeitung_overflow.py` uses `importlib.util.spec_from_file_location` to
load `build.py` fresh on each invocation (no `sys.modules` caching issue —
verified in pitfalls.md §P-19). T07 can be authored at any time; its
assertions only pass after T03 (override rewording), T04 (Frame A),
T05 (Frame B), and T06 (regen) have landed. Order strictly: T01 -> T02 -> T03 ->
T04 -> T05 -> T06 -> T07 -> T08.

</risks_and_verification>
