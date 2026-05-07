# Plan: Rewrite Zeitung A4 onto Brand + blocks

<objective>
What this plan accomplishes: Migrate `templates/zeitung-a4-grun/build.py` (3244 LOC) onto `Brand.gruene_noe()` plus the 5 evidence-driven blocks landed in merged issue #5, judged by visual-diff fidelity vs `templates/zeitung-a4-grun/baseline.pdf` and Brand uptake. RESEARCH.md projects the post-migration LOC at ~2300 (informational only per user direction; visual-diff is the gate).

Why it matters: Third and final template migration in the size-order sequence (Postkarte #6 -> Plakat #7 -> Zeitung #8). Zeitung is the largest of the three (3244 LOC, 14 pages, 140 page items, 14 linked-story chains, 12 page-number frames) and the largest payoff: -944 LOC vs Postkarte's -68 and Plakat's -37, AND the only one with significant block-substitution leverage (26 substitutions = 12 PageNumber + 14 ColumnTextStory). Two narrowly-scoped DSL changes outside `templates/zeitung-a4-grun/build.py` are required:

1. **Hard blocker:** `tools/sla_diff.py --allow-brand-extras` filters `extra-style` / `extra-layer` / `extra-color` warnings (extended in #6 and #7) but does NOT cover the new `missing-layer` warning Zeitung surfaces. Zeitung's original SLA carries a single legacy layer named `Ebene 1` that the brand stack (`Hintergrund` / `Bilder` / `Text` / `Hilfslinien`) does not include. The rebuilt SLA produces `missing-layer LAYERS .NAME: left='Ebene 1' right='(absent)'` which fails strict mode. RESEARCH.md confirmed live: `sla_diff --strict --allow-brand-extras` exits 1 on the rebuilt Zeitung today. This MUST be fixed before any other validation runs.

2. **Trivial kwarg passthrough:** `PageNumber` block must accept and forward `clip_edit`, `line_width_pt`, `col_gap_mm`, and `var_attrs` to its inner `TextFrame` / inner `Run`. Without these passthroughs, the 12 PageNumber substitutions in Task 4 either leak `attr-differs CLIPEDIT` / `col_gap_mm` warnings (defeats the substitution) or stay primitive (negates the ~144 LOC savings). ISSUE.md's "trivial kwarg passthrough" carve-out covers this — these are 4 fields piped into the existing inner-frame emit.

Scope IN:
- `tools/sla_diff.py`: extend `--allow-brand-extras` to also filter `missing-layer` warnings whose `left` value is in a new `_LEGACY_LAYER_NAMES = ("Ebene 1",)` constant. Add 2 unit tests (positive + negative).
- `tools/sla_lib/builder/blocks.py`: widen the `PageNumber` dataclass with `clip_edit: bool = False`, `line_width_pt: Optional[float] = None`, `col_gap_mm: Optional[float] = None`, `var_attrs: Optional[Mapping[str, str]] = None`; forward to the emitted `TextFrame` / inner `Run`. Add unit tests proving each kwarg round-trips.
- `tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip`: extend `test_diff_against_original_clean` allowlist to filter brand-additive `extra-style` / `extra-layer` / `extra-color` AND brand-replacement `missing-layer Ebene 1` warnings (mirror PlakatRoundTrip's pattern at lines 136-148, plus the new legacy-layer clause).
- Regenerate `templates/zeitung-a4-grun/build.py` from the existing `template.sla` via the converter (zero hand edits at the regen step; the converter alone takes the file from 3244 to ~2526 LOC and meets the doc-attrs/pdf-attrs/Brand uptake criteria).
- Hand-edit the regenerated `build.py` to substitute the 12 `PageNumber` frames (one per page that carries a page number).
- Hand-edit the regenerated `build.py` to substitute the 14 `ColumnTextStory` chains (each chain collapses 3 frame definitions + 3 page.adds + 2 link_to wirings into one block call) and delete the trailing block of 28 `link_to()` calls (the block emits link_to internally).
- Rebuild `template.sla` from the new `build.py`, regenerate gallery previews, and prove `bin/validate --ci` is green for ALL three templates.
- Write EXECUTION.md with task-by-task `[x]` status, achieved LOC (informational, expected ~2300), `extra_doc_attrs` count (expected exactly 23), `extra_pdf_attrs` count (expected exactly 11), and P2 follow-ups discovered.

Scope OUT (per ISSUE.md non-goals + RESEARCH.md gap analysis + user prompt constraints):
- **No widening of the `Impressum` block API.** Zeitung surfaces a third `Impressum` gap (3-run heading + spacer + body schema) on top of Postkarte's bold-prefix gap (P2 from #6) and Plakat's rotation_deg gap (P2 from #7). All three Impressum gaps are P2 follow-ups for a separate combined widening issue. Zeitung's Impressum stays as a primitive `TextFrame`.
- **No widening of `ContactBlock`, `PageBackground`, or `ColumnTextStory` block APIs.** Zeitung has zero `ContactBlock` candidates, zero `PageBackground` candidates (RESEARCH.md verified all 8 polygons are decorative inline shapes — none full-bleed; the Titelseite "full-bleed" assumption from issue scoping is wrong), and the `ColumnTextStory` block already accepts the chain frames verbatim (no kwarg gap).
- **No `PageBackground` substitutions.** Zeitung has 0 viable sites. The 8 Polygons in regen are all decorative inline shapes (90°-rotated decorative boxes, ellipse Störer); none match the full-bleed PageBackground geometry pattern.
- **No converter regressions to fix.** RESEARCH.md verified live that the regen handles Zeitung's complexity correctly: 14 chains × 3 frames + 28 link_to round-trips byte-clean, 87 `clip_edit=True` rect-frames auto-emit with 0 `custom_path=`, 6 inline images preserve `xpos_pt` / `ypos_pt` / `width_pt` / `height_pt`, master pages emit empty (Codex master-chain bug from #5 doesn't apply because Zeitung's masters carry no items), Brand emission and attr hoisting clean.
- **No hand-edits to the converter (`tools/sla_to_dsl.py`).** No converter logic changes are needed.
- **No hand-edits to `templates/zeitung-a4-grun/template.sla`** outside the rebuild. `build.py` is the source of truth; `template.sla` regenerates from it on every Task 3-6 verify.
- **No further DSL changes** beyond the small `--allow-brand-extras` extension and the `PageNumber` kwarg passthroughs.
- **No migration of Postkarte (#6) or Plakat (#7).** Postkarte is merged to main; Plakat is in PR #15. This branch is stacked on Plakat and rebases onto main once #15 merges.
- **No visual changes** to the rendered output. Visual-diff fidelity vs `templates/zeitung-a4-grun/baseline.pdf` is the correctness gate. Any pixel drift beyond `templates/zeitung-a4-grun/diff.yml` thresholds (1% mismatch, 5% fuzz) means revert.
- **No PR open or push.** The orchestrator runs `/issue:ship` separately.
- **LOC target:** ISSUE.md states `<= 2400` is **informational only** per user direction. Achieved is expected ~2300 with the recommended block substitutions; do not gate on the literal number.

No CONTEXT.md — discuss step skipped per user direction. Decisions below derive directly from RESEARCH.md plus user prompt constraints.
</objective>

<context>
Issue: @.issues/rewrite-zeitung-onto-brand-blocks/ISSUE.md
Research: @.issues/rewrite-zeitung-onto-brand-blocks/RESEARCH.md

Pattern reference (the two prior migrations in this sequence):
@/root/workspace/.issues/archive/rewrite-postkarte-onto-brand-blocks/PLAN.md
@/root/workspace/.issues/archive/rewrite-postkarte-onto-brand-blocks/EXECUTION.md
@/root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks/.issues/rewrite-plakat-onto-brand-blocks/PLAN.md
@/root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks/.issues/rewrite-plakat-onto-brand-blocks/EXECUTION.md

Stacking note: This branch (`issue/rewrite-zeitung-onto-brand-blocks`) is stacked on `issue/rewrite-plakat-onto-brand-blocks` (PR #15). All toolchain from #6 (PR #14, merged) AND #7 (in PR #15) is ALREADY present on this branch as base:
- `--allow-brand-extras` filtering `extra-style`, `extra-layer`, `extra-color` (the last from #7).
- `Brand.gruene_noe()`, all 5 evidence-driven blocks, `PageBackground.for_page()` widened with `line_color` / `line_width_pt`, ergonomics fixes.
- Synthetic legacy module fix; deploy workflow gated to push-to-main.
- `_BRAND_COLOR_NAMES = ("Black", "White", "Registration", "Dunkelgrün", "Hellgrün", "Gelb", "Magenta")` already defined in `tools/sla_diff.py:49`.
- `AllowBrandExtrasTests` class in `tools/sla_lib/tests/test_sla_diff.py:730` with 5 existing tests (extra-style, extra-layer, extra-color brand, extra-color non-brand, does-not-suppress-critical).

This plan extends that work; do not reintroduce it.

Key files (executor will read these as needed; do not pre-explore beyond the interfaces below):
@templates/zeitung-a4-grun/build.py — current 3244-LOC build, source of truth for the regen
@templates/zeitung-a4-grun/template.sla — current SLA, input to converter
@templates/zeitung-a4-grun/baseline.pdf — pixel oracle for visual_diff (1.35 MB, 14 pages; research-confirmed clean against raw regen at 96 dpi)
@templates/zeitung-a4-grun/diff.yml — visual_diff thresholds (1% mismatch, 5% fuzz; no per-page overrides)
@templates/zeitung-a4-grun/meta.yml — `previews_for_sla` SHA gate
@templates/zeitung-a4-grun/assets/ — inline-image asset directory (6 inline images preserved verbatim base64)
@gruene-zeitung-vorlage-original.sla — pristine source SLA at the worktree root (used by `ZeitungRoundTrip._diff_clean`)
@tools/sla_to_dsl.py — converter; emits `brand=Brand.gruene_noe()`, `extra_doc_attrs=23`, `extra_pdf_attrs=11`
@tools/sla_diff.py — structural differ; CLI at lines 1181-1224; `--allow-brand-extras` filter at 1202-1211 needs `missing-layer Ebene 1` extension; `_BRAND_COLOR_NAMES` constant at line 49
@tools/sla_lib/builder/blocks.py — `PageNumber` dataclass at lines 45-81 needs 4 kwarg passthroughs; `ColumnTextStory` block at lines 298-334 (no widening — accepts frames verbatim)
@tools/sla_lib/tests/test_sla_diff.py — `AllowBrandExtrasTests` class at line 730 (existing; mirror its `_write_sla_with_extra_layer` helper for the new missing-layer test fixtures)
@tools/sla_lib/tests/test_sla_to_dsl.py — `ZeitungRoundTrip` class at lines 163-184 (allowlist needs extending; PlakatRoundTrip's already-merged allowlist at lines 119-150 is the reference pattern)
@tools/sla_lib/tests/test_blocks.py — `PageNumber` widening tests go alongside existing PageBackground / Impressum block tests
@bin/validate — already passes `--allow-brand-extras` to sla_diff (from #6); no edit needed
@bin/render-gallery — regenerates page-01.png … page-14.png + preview.pdf and updates `meta.yml::previews_for_sla` SHA
@shared/ci.yml — brand color names at lines 19-45 (the canonical 7-tuple already wired into `_BRAND_COLOR_NAMES`)

<interfaces>
<!-- Executor: use these contracts directly. Do not re-explore the codebase for them. -->

From tools/sla_diff.py CLI (lines 1199-1211 — the filter that needs extending):

  args = ap.parse_args(argv)
  report = diff(args.left, args.right)

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

Task 1 extends this predicate to ALSO drop `missing-layer` warnings whose `i.left` is in a new `_LEGACY_LAYER_NAMES = ("Ebene 1",)` tuple. The semantics: when the rebuilt right SLA is built with a Brand profile, the brand layer stack REPLACES the original SLA's single legacy layer; the differ surfaces this as `missing-layer LAYERS .NAME: left='Ebene 1' right='(absent)'`. This is brand-replacement (not brand-additive — the `extra-layer` cases handle the brand-additive direction Bilder/Text/Hilfslinien).

From tools/sla_diff.py near the top (line 49 — the constant to mirror for the new tuple):

  _BRAND_COLOR_NAMES = (
      "Black", "White", "Registration",
      "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
  )

Task 1 adds, immediately adjacent (same module-private style):

  _LEGACY_LAYER_NAMES = (
      "Ebene 1",  # Scribus's German default name; replaced by Brand.gruene_noe()'s 4-layer stack.
  )

From tools/sla_diff.py palette/layers comparison (lines 1048-1050 reported by RESEARCH.md):
- `missing-layer` is SEVERITY_WARNING.
- Each Issue's `left` field carries the LAYERS .NAME (e.g. 'Ebene 1') and `right` is '(absent)' (or the reverse for `extra-layer`).
- Use `i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES` as the additional filter clause.

From tools/sla_lib/tests/test_sla_diff.py existing AllowBrandExtrasTests (line 730 — pattern to mirror):

  class AllowBrandExtrasTests(unittest.TestCase):
      def setUp(self):
          self.tmp = Path(tempfile.mkdtemp())

      def _write_sla_with_extra_style(self, name, extra_style_name): ...
      def _write_sla_with_extra_layer(self, name, extra_layer_name): ...
      def _write_sla_with_extra_color(self, name, extra_color_name): ...

      def test_allow_brand_extras_filters_extra_style_warning(self): ...
      def test_allow_brand_extras_filters_extra_layer_warning(self): ...
      def test_allow_brand_extras_filters_extra_color_warning_for_brand_color(self): ...
      def test_allow_brand_extras_does_not_filter_non_brand_color(self): ...
      def test_allow_brand_extras_does_not_suppress_critical(self): ...

Task 1 adds a `_write_sla_with_missing_layer(name, present_layer_name)` helper that creates an SLA carrying ONLY the named layer (so when paired against a left SLA carrying `Ebene 1`, the differ reports `missing-layer left='Ebene 1' right='(absent)'`). Then adds 2 new test methods:

  test_allow_brand_extras_filters_missing_layer_for_legacy_name -> positive (Ebene 1 -> filtered)
  test_allow_brand_extras_does_not_filter_missing_layer_for_arbitrary_name -> negative (some other layer name -> still fails)

The helper shape mirrors `_write_sla_with_extra_layer` exactly — same lxml.etree imports, same root attributes, same page/masterpage attributes; the difference is which layer NAME the SLA carries.

From tools/sla_lib/builder/blocks.py PageNumber (lines 45-81 — the block that needs widening):

  @dataclass
  class PageNumber:
      """Page-number TextFrame using <var name='pgno'/>."""
      x_mm: float = 10
      y_mm: float = 280
      w_mm: float = 10
      h_mm: float = 6
      style: str = "Seitenzahl"
      layer: int = 2
      anname: str = "Seitenzahl"

      def emit(self) -> Iterable:
          yield TextFrame(
              x_mm=self.x_mm,
              y_mm=self.y_mm,
              w_mm=self.w_mm,
              h_mm=self.h_mm,
              runs=[Run(
                  text="",
                  has_itext=False,
                  var="pgno",
                  separator="para",
                  paragraph_style=self.style,
              )],
              layer=self.layer,
              anname=self.anname,
          )

Task 2 widens this with 4 NEW dataclass fields and forwards them in `emit()`:

  @dataclass
  class PageNumber:
      x_mm: float = 10
      y_mm: float = 280
      w_mm: float = 10
      h_mm: float = 6
      style: str = "Seitenzahl"
      layer: int = 2
      anname: str = "Seitenzahl"
      # NEW kwarg passthroughs (trivial; carved out by ISSUE.md):
      clip_edit: bool = False
      line_width_pt: Optional[float] = None
      col_gap_mm: Optional[float] = None
      var_attrs: Optional[Mapping[str, str]] = None  # forwarded to the inner Run

      def emit(self) -> Iterable:
          yield TextFrame(
              x_mm=self.x_mm, y_mm=self.y_mm, w_mm=self.w_mm, h_mm=self.h_mm,
              runs=[Run(
                  text="", has_itext=False, var="pgno",
                  separator="para", paragraph_style=self.style,
                  var_attrs=self.var_attrs,           # NEW (passthrough)
              )],
              layer=self.layer,
              anname=self.anname,
              clip_edit=self.clip_edit,                # NEW
              line_width_pt=self.line_width_pt,        # NEW
              col_gap_mm=self.col_gap_mm,              # NEW
          )

The forwarding only emits each NEW field when non-None / non-default to avoid widening the inner `TextFrame`/`Run` shape on existing call sites that don't pass these. If `Run` does not currently accept `var_attrs=` as a kwarg, inspect `tools/sla_lib/builder/document.py` (or wherever Run is defined) and EITHER (a) confirm it does and pass through, OR (b) widen Run with `var_attrs: Optional[Mapping[str, str]] = None` (also a trivial passthrough — Zeitung's regen already uses `var_attrs=` on Run literals, so the field MUST already exist; this is anchor verification, not block widening).

From tools/sla_lib/tests/test_sla_to_dsl.py PlakatRoundTrip (lines 119-150 — pattern to mirror for ZeitungRoundTrip):

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
  self.assertEqual(non_brand_warnings, [], msg=...)

From tools/sla_lib/tests/test_sla_to_dsl.py ZeitungRoundTrip (lines 163-184 — what needs editing in Task 6):

  class ZeitungRoundTrip(unittest.TestCase):
      TEMPLATE_DIR = ROOT / "templates" / "zeitung-a4-grun"
      ORIGINAL = ROOT / "gruene-zeitung-vorlage-original.sla"

      def test_diff_against_original_clean(self):
          sla = _run_build(self.TEMPLATE_DIR / "build.py")
          report = _diff_clean(self.ORIGINAL, sla)
          self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0, msg=...)
          self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0, msg=...)   # this fails after Task 3

      def test_chain_topology_intact(self):                                          # DO NOT touch (independent)
          ...

Task 6 step 6A replaces the unconditional `summary[WARNING] == 0` with the PlakatRoundTrip-style allowlist plus the new `missing-layer Ebene 1` clause. ZeitungRoundTrip-specific facts (RESEARCH.md confirmed): rebuilt Zeitung carries 8 extra-style (ci/*) + 4 extra-layer (Bilder/Text/Hilfslinien — Hintergrund overlaps) + 1 missing-layer (Ebene 1) = 13 unfiltered warnings before allowlist; 0 after.

Zeitung-specific facts (from RESEARCH.md, do not re-derive):

- 14 pages: page 0 (Titelseite, no master attribute), pages 1-13 alternate left/right master via `facing_pages=True`.
- 140 page items total: 78 inline TextFrames + 34 chain TextFrames = 112 TextFrames (RESEARCH inventory tally), 20 ImageFrames (6 inline, 14 file-asset), 8 Polygons (all decorative inline; 0 full-bleed).
- 12 `var='pgno'` PageNumber idioms on pages 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13 (no pgno on Titelseite/page 0 or page 10).
  - Approximate line ranges in regen: 446-459, 599-612, 691-704, 862-875, 964-977, 1236-1249, 1379-1392, 1513-1526, 1680-1693, 1970-1983, 2157-2170, 2302-2315 (RESEARCH-measured; may shift slightly on the executor's regen — find them by `var='pgno'` substring).
  - All 12 use `paragraph_style='Seitenzahl'` (PageNumber default — no style kwarg needed).
  - All 12 carry `clip_edit=True`, `line_width_pt=1`, `col_gap_mm=3.207461712525627` (or similar; preserve verbatim).
  - 1 of the 12 (page 12, near regen line 2157) carries `var_attrs={'FCOLOR': 'White', 'FSHADE': '100'}` (white pgno on dark background); the other 11 have no `var_attrs`.
  - All 12 use `layer=0` (Zeitung's brand-replaced base layer); pass explicit `layer=0` (PageNumber's default is layer=2).
  - `anname` varies per frame (e.g. `'Kopie von u2d45'`, `'Seitenzahl'`); pass each explicitly.

- 14 `_chain<N>_<idx>` chains on pages 1, 2 (×2: chain0 + chain2), 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 (×2: chain12 + chain13). Each chain has 3 frames (42 total chain TextFrames).
  - First frame (`_chainN_0`) carries the story `runs=[...]` list (typically 8-12 Runs); frames 1 and 2 have empty runs.
  - First frame may carry `trail_style='Fließtext '` (note trailing space — preserve verbatim) and a unique `line_width_pt` (e.g. `1.011...`).
  - All chain frames carry `clip_edit=True` and `col_gap_mm` (verbatim float; preserve).
  - 28 trailing `link_to()` calls (= 14 × 2 wirings per chain length 3) clustered at lines ~3214-3241 of the regen — Task 5 deletes this entire block since `ColumnTextStory.emit()` calls `link_to()` internally.

- 8 Polygons stay primitive (none full-bleed; 0 PageBackground substitutions).
- 1 Impressum frame on page 13 stays primitive (3-run heading + spacer + body; modern Impressum block is single-Run only).
- 0 ContactBlock candidates.

Converter CLI (research-verified working invocation; will OVERWRITE the committed build.py in Task 3):

  python3 tools/sla_to_dsl.py \
      templates/zeitung-a4-grun/template.sla \
      templates/zeitung-a4-grun/build.py \
      --template-id zeitung-a4-grun \
      --assets-dir templates/zeitung-a4-grun/assets/

Expected post-regen measurements (RESEARCH-verified live):
- LOC ~2526 (informational; ±5 acceptable)
- `extra_doc_attrs` exactly 23 keys
- `extra_pdf_attrs` exactly 11 keys
- Contains `brand=Brand.gruene_noe()`
- Does NOT contain `palette_replaces_ci=True`
- Does NOT contain `layers=[DocumentLayer(` (Brand provides the stack — Task 1's filter handles the resulting `missing-layer Ebene 1` warning)
- 12 `var='pgno'` Run instances
- 42 `_chainN_<idx> = TextFrame(` assignments (14 chains × 3 frames)
- 28 `.link_to(` calls
- 0 `custom_path=` (test_5c_zeitung_clip_rect_frames_omit_custom_path invariant)
- 6 inline images preserve `xpos_pt=...` (test_5b_zeitung_inline_images_keep_xpos_pt invariant)
</interfaces>
</context>

<commit_format>
Format: conventional with numeric issue prefix (per `.issues/config.yaml::commits.prefix=true` + `commits.format=conventional`)
Pattern: `8: {type}({scope}): {description}`
Example: `8: feat(sla_diff): extend --allow-brand-extras to missing-layer warnings`
Types used in this plan: feat, refactor, test, chore, docs.
</commit_format>

<critical_path>
Strict ordering: Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6. DO NOT reorder.

Task 1 (sla_diff `missing-layer Ebene 1` filter) MUST complete before Task 3 (regenerate build.py). Without this, Task 3's `bin/validate --ci` step fails on Zeitung at the `sla_diff --strict --allow-brand-extras` gate (RESEARCH.md proved this live: exit=1 with `missing-layer LAYERS .NAME: left='Ebene 1' right='(absent)'`).

Task 2 (PageNumber kwarg passthrough widening) MUST complete before Task 3 (regenerate build.py) and ESPECIALLY before Task 4 (PageNumber substitutions). The regen itself does NOT depend on PageNumber-block widening (the converter emits primitive `TextFrame(... var='pgno' ...)`, not the block). However, since `bin/validate --ci` is a verify step in Task 3 and the same is run after Task 4's substitutions, having the kwarg passthroughs already in place when block calls land prevents `attr-differs CLIPEDIT / col_gap_mm / line_width_pt` warnings from polluting the diff. Putting Task 2 before Task 3 is the safer ordering: it lets Task 4 substitute with full attr fidelity.

Task 4 (PageNumber substitutions) and Task 5 (ColumnTextStory substitutions) MUST each be verified independently — substituting 26 blocks is enough hand-editing that an intermediate `bin/validate --ci` + `visual_diff` after Task 4 catches PageNumber-substitution regressions before Task 5 piles on more changes. DO NOT collapse Tasks 4 and 5.

Task 6 (ZeitungRoundTrip allowlist update + render-gallery + final pipeline + EXECUTION.md) cannot run before Task 5 because the gallery render gates on the rebuilt `template.sla` SHA, which only stabilizes after both substitution waves land.

The `gruene-zeitung-vorlage-original.sla` at the worktree root is the canonical "left" SLA for `sla_diff` and `ZeitungRoundTrip._diff_clean`. Do not edit it; do not move it.
</critical_path>

<tasks>

<task type="auto">
  <name>Task 1: Extend --allow-brand-extras to filter missing-layer warnings for legacy layer names</name>
  <files>tools/sla_diff.py, tools/sla_lib/tests/test_sla_diff.py</files>
  <action>
  GOAL: Make `--allow-brand-extras` ALSO drop `missing-layer` warnings whose left value is one of a hardcoded set of legacy original-SLA layer names — currently just `('Ebene 1',)`. Hard prerequisite for every later task; without it Zeitung's rebuilt SLA fails `bin/validate --ci` even when the rendering is byte-clean. RESEARCH.md verified live that current main produces 1 unfiltered warning (`missing-layer LAYERS .NAME: left='Ebene 1' right='(absent)'`) when running sla_diff against the rebuilt Zeitung SLA under `--strict --allow-brand-extras`.

  Why `missing-layer` is the right code (and not `extra-layer` flipped):
  - `extra-layer` (already filtered) fires when the right SLA has a layer the left lacks (the brand-additive direction: Bilder/Text/Hilfslinien on the right when the left only has Hintergrund or Ebene 1).
  - `missing-layer` (NEW filter target) fires when the LEFT SLA has a layer the right lacks (the brand-replacement direction: original 'Ebene 1' on the left when the right has the brand 4-layer stack but no 'Ebene 1').
  - Postkarte and Plakat originals carry `Hintergrund` (which IS in the brand stack) so they emit no `missing-layer` warning. Zeitung's original carries `Ebene 1` (NOT in the brand stack) so it does.

  STEP 1A — Edit `tools/sla_diff.py`:

  Add a module-level constant immediately after `_BRAND_COLOR_NAMES` (currently at line 49). Mirror the same comment style:

      _LEGACY_LAYER_NAMES = (
          "Ebene 1",  # Scribus German default; replaced by Brand.gruene_noe()'s 4-layer stack.
      )
      # Source: original SLA layer names that the brand stack replaces. Hardcoded
      # here (rather than YAML-loaded) to keep tools/sla_diff.py free of yaml imports.
      # Add new legacy names if future templates surface them; out-of-sync risk is low.

  Then edit the `--allow-brand-extras` filter at lines 1202-1211. The current shape:

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

  Becomes (NEW clause added as third `or` arm):

      if args.allow_brand_extras:
          report.issues = [
              i for i in report.issues
              if not (
                  i.severity == SEVERITY_WARNING and (
                      i.code in ("extra-style", "extra-layer")
                      or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
                      or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)
                  )
              )
          ]

  Update the help text on the `--allow-brand-extras` argparse line (1191-1198) to document the missing-layer extension. Append (do not remove existing text):

      ap.add_argument("--allow-brand-extras", action="store_true",
                      help="Filter out 'extra-style', 'extra-layer', brand-color "
                           "'extra-color', and legacy-layer 'missing-layer' warnings "
                           "injected by Brand profiles (e.g. Brand.gruene_noe()'s "
                           "ci/* paragraph styles, Bilder/Text/Hilfslinien layers, "
                           "full 7-color palette, and replacement of legacy 'Ebene 1' "
                           "layer). Only missing-layer warnings whose left layer NAME "
                           "matches a known legacy name are filtered; non-legacy "
                           "missing layers still fail. Critical issues are unaffected.")

  CONSTRAINT: Do NOT change the default behavior of `sla_diff` — `--strict` without `--allow-brand-extras` MUST exit 1 on the same warnings it does today. The new filter only RUNS when `args.allow_brand_extras` is True.
  CONSTRAINT: Do NOT change the existing `extra-style` / `extra-layer` / `extra-color` filter clauses. The new clause is additive (a third `or` arm), not a replacement.
  CONSTRAINT: Do NOT load `shared/ci.yml` or any YAML file from `sla_diff.py`. Hardcode `_LEGACY_LAYER_NAMES` as a tuple, mirroring `_BRAND_COLOR_NAMES`. PR #14's review chose surface-area minimization; preserve that.
  CONSTRAINT: Do NOT add `_LEGACY_LAYER_NAMES` to a new module — keep it as a single private constant adjacent to the filter logic for diff readability.

  STEP 1B — Add unit tests in `tools/sla_lib/tests/test_sla_diff.py`:

  Locate the existing `AllowBrandExtrasTests` class at line 730. Read the existing helpers `_write_sla_with_extra_style(...)`, `_write_sla_with_extra_layer(...)`, `_write_sla_with_extra_color(...)` to understand the fixture style. Then:

  STEP 1B-i — Add a helper method `_write_sla_with_layer(name, layer_name)` (singular `layer`, distinct from the existing `_write_sla_with_extra_layer`) that writes a SCRIBUSUTF8NEW SLA carrying EXACTLY ONE LAYERS element with the given NAME — and nothing else. The body mirrors `_write_sla_with_extra_layer` exactly except the LAYERS NAME is the only differentiator. This helper is what generates the asymmetric "left has Ebene 1, right has Hintergrund" pair to provoke a `missing-layer` warning.

  Pseudocode (match the file's existing fixture style):

      def _write_sla_with_layer(self, name, layer_name):
          """Write a minimal SLA at self.tmp/name with a single LAYERS NAME=layer_name."""
          # Build SCRIBUSUTF8NEW root; under it, DOCUMENT with one MASTERPAGE,
          # one PAGE, and one LAYERS sub-element with NAME=layer_name.
          # Mirror the existing _write_sla_with_extra_layer body verbatim except
          # the LAYERS NAME assignment — that helper adds an EXTRA layer beyond
          # a baseline; this helper sets the SOLE layer.

  STEP 1B-ii — Add TWO new test methods to the `AllowBrandExtrasTests` class:

  1. `test_allow_brand_extras_filters_missing_layer_for_legacy_name` — positive case:
     - Build LEFT SLA with `_write_sla_with_layer('left.sla', 'Ebene 1')`.
     - Build RIGHT SLA with `_write_sla_with_layer('right.sla', 'Hintergrund')`.
     - Run `sd.main(["--left", left, "--right", right, "--strict"])` -> assert exit 1 (the unfiltered warning fires).
     - Run `sd.main(["--left", left, "--right", right, "--strict", "--allow-brand-extras"])` -> assert exit 0 (filtered because `'Ebene 1'` is in `_LEGACY_LAYER_NAMES`).

  2. `test_allow_brand_extras_does_not_filter_missing_layer_for_arbitrary_name` — negative case:
     - Build LEFT SLA with `_write_sla_with_layer('left.sla', 'SomeRandomLegacyX')` (a name explicitly NOT in `_LEGACY_LAYER_NAMES`).
     - Build RIGHT SLA with `_write_sla_with_layer('right.sla', 'Hintergrund')`.
     - Run `sd.main([..., "--strict"])` -> assert exit 1.
     - Run `sd.main([..., "--strict", "--allow-brand-extras"])` -> assert exit 1 (NOT filtered because `'SomeRandomLegacyX'` is not a legacy name).
     - This is the critical guard: it proves the legacy-name predicate actually narrows the filter, not just rubber-stamps every missing-layer warning.

  Match the assertion message style of the existing `test_allow_brand_extras_filters_extra_layer_warning` and `test_allow_brand_extras_does_not_filter_non_brand_color` tests (e.g. `"Expected exit 1 from --strict with missing-layer warning"`).

  STEP 1B-iii — IF `_compare_layers` (or whatever produces `missing-layer` issues) requires both SLAs to share other DOCUMENT/MASTERPAGE infrastructure to even emit the LAYERS comparison, ensure the helper writes the same DOCUMENT/MASTERPAGE shell as the existing helpers do. The other helpers were verified to produce their respective `extra-layer` warnings; matching their shell (root attrs, DOCUMENT attrs, single MASTERPAGE, single PAGE) keeps `missing-layer` symmetric. If the test fails because the two SLAs are TOO different (e.g. different page counts cause earlier issues to dominate), keep all non-LAYERS attributes identical between left and right.

  STEP 1C — Run the targeted test suite to confirm both old and new tests pass:

      python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x -v -k AllowBrandExtras

  Then run the full sla_diff test suite to confirm nothing else regressed:

      python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x

  STEP 1D — Smoke test that the existing two templates still pass `bin/validate --ci`. Postkarte and Plakat both carry `Hintergrund` as their original layer (which IS in the brand stack) so they have NO `missing-layer` warning to filter; the new filter clause is a no-op for them. `bin/validate --ci` MUST still report `sla_diff: PASS` for postkarte and plakat at this stage. Note about Zeitung at this stage: Zeitung will still fail `bin/validate --ci` after Task 1 alone because the COMMITTED Zeitung build.py is still on the pre-Brand path (no `missing-layer` warning yet); the filter will activate only after Task 3 regenerates Zeitung onto Brand. This is expected — Task 1 is necessary infrastructure, Task 3 is what triggers it.

  CONSTRAINT: Do NOT regenerate any template's build.py in this task. Task 3 is the regen task.
  CONSTRAINT: Do NOT touch `bin/validate` — `--allow-brand-extras` is already wired through it (from PR #14).
  CONSTRAINT: Do NOT extend `_LEGACY_LAYER_NAMES` with anything other than `'Ebene 1'`. Only Zeitung surfaces this gap; future templates that surface other legacy names get appended in their own issues.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x -v -k AllowBrandExtras && python3 -m pytest tools/sla_lib/tests/test_sla_diff.py -x && bin/validate --ci</automated>
  </verify>
  <done>
  - `tools/sla_diff.py` defines `_LEGACY_LAYER_NAMES = ("Ebene 1",)` adjacent to `_BRAND_COLOR_NAMES`.
  - The `--allow-brand-extras` filter additionally drops `missing-layer` warnings whose `i.left` is in `_LEGACY_LAYER_NAMES`.
  - Help text for `--allow-brand-extras` documents the missing-layer extension.
  - 2 new tests added to `AllowBrandExtrasTests`: filters legacy `missing-layer`, does NOT filter arbitrary `missing-layer`. Total `AllowBrandExtras*` tests now 7 (5 existing + 2 new).
  - `pytest tools/sla_lib/tests/test_sla_diff.py -x` is green.
  - `bin/validate --ci` still PASS for postkarte and plakat (Zeitung regen is Task 3; it may still fail at this stage on the pre-Brand committed build.py).
  - When `--allow-brand-extras` is NOT set, behavior is byte-identical to current main.
  </done>
  <commit_message>8: feat(sla_diff): extend --allow-brand-extras to legacy missing-layer warnings</commit_message>
</task>

<task type="auto">
  <name>Task 2: Widen PageNumber block with clip_edit / line_width_pt / col_gap_mm / var_attrs kwarg passthroughs</name>
  <files>tools/sla_lib/builder/blocks.py, tools/sla_lib/tests/test_blocks.py</files>
  <action>
  GOAL: Add 4 trivial kwarg passthroughs to the `PageNumber` block so the 12 substitutions in Task 4 can preserve attr fidelity (`CLIPEDIT`, `LINEWIDTH`, `COLGAP`, and the 1 white-on-dark `var_attrs` case on page 12). Without this widening, PageNumber substitutions either leak `attr-differs CLIPEDIT / col_gap_mm / line_width_pt` warnings (defeats the substitution) or stay primitive (negates the ~144 LOC savings). ISSUE.md's "trivial kwarg passthrough" carve-out covers this.

  STEP 2A — Read `tools/sla_lib/builder/blocks.py` lines 40-82 to confirm the current `PageNumber` shape matches the `<interfaces>` block in this PLAN. If the dataclass already exposes any of the 4 fields, do NOT re-add them — only widen the missing ones.

  STEP 2B — Read the inner `Run` class definition to confirm it already accepts a `var_attrs` kwarg. The Zeitung regen (RESEARCH.md) emits `Run(text='', has_itext=False, var='pgno', separator='para', paragraph_style='Seitenzahl', var_attrs={'FCOLOR': 'White', 'FSHADE': '100'})` for the page-12 white-on-dark pgno, which proves Run already accepts `var_attrs`. Locate Run's definition (search for `class Run` in `tools/sla_lib/builder/`); if `var_attrs` is NOT a field there, do NOT widen Run — instead, in this task's STEP 2C, do the in-place TextFrame / Run construction inside `PageNumber.emit()` directly via the same kwarg path the converter uses. IF Run already has `var_attrs` (likely), the rest is a straight passthrough.

  STEP 2C — Edit `tools/sla_lib/builder/blocks.py`. Add the 4 NEW dataclass fields to `PageNumber` (with sensible defaults that emit nothing different when unset). Then forward each in `emit()`. Final shape:

      from typing import Mapping, Optional   # confirm these imports exist; add if missing.

      @dataclass
      class PageNumber:
          """Page-number TextFrame using <var name='pgno'/>.

          Corpus: templates/zeitung-a4-grun/build.py:547 (and 11 more occurrences).
          Each occurrence is a TextFrame with one Run(var='pgno', separator='para',
          paragraph_style='Seitenzahl').

          Usage::

              page.add(PageNumber(x_mm=10, y_mm=280))
              page.add(PageNumber(x_mm=8.51, y_mm=283.7, w_mm=12.78, h_mm=9.48,
                                  layer=0, anname='Kopie von u2d45',
                                  clip_edit=True, line_width_pt=1, col_gap_mm=3.207,
                                  var_attrs={'FCOLOR': 'White', 'FSHADE': '100'}))
          """

          x_mm: float = 10
          y_mm: float = 280
          w_mm: float = 10
          h_mm: float = 6
          style: str = "Seitenzahl"
          layer: int = 2
          anname: str = "Seitenzahl"
          # Trivial kwarg passthroughs (in scope per ISSUE.md "trivial kwarg passthrough"
          # carve-out; needed for Zeitung's 12 PageNumber substitutions to preserve
          # CLIPEDIT, COLGAP, LINEWIDTH attr fidelity and the 1 white-pgno var_attrs case).
          clip_edit: bool = False
          line_width_pt: Optional[float] = None
          col_gap_mm: Optional[float] = None
          var_attrs: Optional[Mapping[str, str]] = None

          def emit(self) -> Iterable:
              # Build the inner Run; only set var_attrs if non-None to avoid changing
              # the Run literal shape on existing call sites.
              run_kwargs = dict(
                  text="",
                  has_itext=False,
                  var="pgno",
                  separator="para",
                  paragraph_style=self.style,
              )
              if self.var_attrs is not None:
                  run_kwargs["var_attrs"] = dict(self.var_attrs)

              # Build the outer TextFrame; only forward kwargs whose value differs from
              # default to avoid widening TextFrame's emitted SLA shape on existing
              # callers.
              tf_kwargs = dict(
                  x_mm=self.x_mm,
                  y_mm=self.y_mm,
                  w_mm=self.w_mm,
                  h_mm=self.h_mm,
                  runs=[Run(**run_kwargs)],
                  layer=self.layer,
                  anname=self.anname,
              )
              if self.clip_edit:
                  tf_kwargs["clip_edit"] = True
              if self.line_width_pt is not None:
                  tf_kwargs["line_width_pt"] = self.line_width_pt
              if self.col_gap_mm is not None:
                  tf_kwargs["col_gap_mm"] = self.col_gap_mm

              yield TextFrame(**tf_kwargs)

  Rationale for the conditional kwarg style: keeps existing `PageNumber()` callers' emitted SLA byte-identical (no clip_edit / col_gap / line_width attrs added when defaults are used), preserves Postkarte's PageNumber-free build, and only opts in for Zeitung's substitutions that pass the kwargs explicitly.

  STEP 2D — Add unit tests in `tools/sla_lib/tests/test_blocks.py`. Locate existing PageNumber tests (search for `PageNumber` in the file). Add 4 new test methods alongside them:

  1. `test_page_number_default_emits_minimal_text_frame`:
     - Construct `PageNumber(x_mm=10, y_mm=280)` (no extra kwargs).
     - Call `list(pn.emit())`; assert one TextFrame yielded.
     - Assert the yielded frame has NO `clip_edit=True`, NO `line_width_pt`, NO `col_gap_mm` (or whatever the dataclass default reports).
     - Assert the inner Run has NO `var_attrs` (or `var_attrs is None`).
     - Guards backward compatibility — Postkarte/Plakat callers do not regress.

  2. `test_page_number_forwards_clip_edit_and_geometry_kwargs`:
     - Construct `PageNumber(x_mm=8.51, y_mm=283.7, w_mm=12.78, h_mm=9.48, layer=0, anname='Kopie von u2d45', clip_edit=True, line_width_pt=1, col_gap_mm=3.207461712525627)`.
     - Call `emit()`; assert the yielded TextFrame's `clip_edit == True`, `line_width_pt == 1`, `col_gap_mm == pytest.approx(3.207461712525627)`, `layer == 0`, `anname == 'Kopie von u2d45'`.

  3. `test_page_number_forwards_var_attrs_to_inner_run`:
     - Construct `PageNumber(x_mm=10, y_mm=280, var_attrs={'FCOLOR': 'White', 'FSHADE': '100'})`.
     - Call `emit()`; assert the yielded TextFrame's `runs[0].var_attrs == {'FCOLOR': 'White', 'FSHADE': '100'}` (or however Run exposes the field — match its accessor).

  4. `test_page_number_round_trips_through_document`:
     - Optional but high-value: construct a minimal Document with one Page that adds a `PageNumber(... full Zeitung kwargs ...)`. Call `doc.save(tmp_path)` and read the resulting SLA; assert `CLIPEDIT="1"`, `COLGAP="3.207..."`, `LINEWIDTH="1"` are present on the PAGEOBJECT, AND the var element's FCOLOR/FSHADE attributes are present (when var_attrs is set).
     - If the test infrastructure for "build doc, save, reparse SLA" already exists in `test_blocks.py` for PageBackground (PR #14 added a similar check), mirror its pattern; otherwise skip this test (the 3 above are sufficient).

  Match the assertion message style and import patterns of the existing PageBackground tests in the same file.

  CONSTRAINT: Do NOT widen the inner `Run` or `TextFrame` dataclasses in this task. They already accept these kwargs (verified by the converter's regen literal output).
  CONSTRAINT: Do NOT widen `Impressum`, `ContactBlock`, `PageBackground`, or `ColumnTextStory` blocks. Out of scope.
  CONSTRAINT: Do NOT change the existing `PageNumber()` zero-kwarg call shape. The 4 new fields all default such that `PageNumber()` emits an identical TextFrame to the current main.
  CONSTRAINT: If `Mapping` / `Optional` are not imported at the top of `blocks.py`, add the import (`from typing import Mapping, Optional`). Do not add unused imports.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_blocks.py -x -v -k PageNumber && python3 -m pytest tools/sla_lib/tests -x</automated>
  </verify>
  <done>
  - `PageNumber` dataclass in `tools/sla_lib/builder/blocks.py` carries 4 NEW fields: `clip_edit: bool = False`, `line_width_pt: Optional[float] = None`, `col_gap_mm: Optional[float] = None`, `var_attrs: Optional[Mapping[str, str]] = None`.
  - `PageNumber.emit()` forwards each NEW field to the inner TextFrame / Run only when set (zero-kwarg `PageNumber()` still emits a byte-identical SLA to current main).
  - At least 3 new unit tests in `test_blocks.py` cover: default zero-kwarg path, all-4-kwargs forwarding, var_attrs forwarding to inner Run.
  - `pytest tools/sla_lib/tests -x` is green (251+ tests).
  - Existing PageNumber callers (none in committed Postkarte / Plakat builds; this is forward-looking for Zeitung) compile cleanly.
  </done>
  <commit_message>8: feat(blocks): widen PageNumber with clip_edit/line_width_pt/col_gap_mm/var_attrs passthroughs</commit_message>
</task>

<task type="auto">
  <name>Task 3: Regenerate templates/zeitung-a4-grun/build.py via converter (zero hand edits)</name>
  <files>templates/zeitung-a4-grun/build.py, templates/zeitung-a4-grun/template.sla</files>
  <action>
  GOAL: Replace the 3244-LOC committed `templates/zeitung-a4-grun/build.py` with a converter-emitted version that uses `brand=Brand.gruene_noe()`, drops doc-attrs from 113 to 23 keys, drops pdf-attrs from 44 to 11 keys, drops `palette_replaces_ci=True`, drops the explicit `layers=[DocumentLayer('Ebene 1', ...)]` (Brand provides the layer stack; Task 1 filters the resulting `missing-layer Ebene 1` warning), and emits `clip_edit=True` rect-collapses for 87 frames with 0 `custom_path=`. RESEARCH.md verified live that the raw converter output meets all 3 of 4 numeric ACs (`extra_doc_attrs=23`, `extra_pdf_attrs=11`, Brand emitted) immediately, with LOC at 2526 (block substitutions in Tasks 4-5 take that to ~2300).

  STEP 3A — Confirm git status is clean before running the converter, so a `git diff` will surface the conversion delta exactly:

      git -C /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks status --short

  Only modifications expected at this point are from Tasks 1-2 (`tools/sla_diff.py`, `tools/sla_lib/builder/blocks.py`, the two test files). If `templates/zeitung-a4-grun/` shows modifications, STOP and report — Tasks 1 or 2 inadvertently touched a template.

  STEP 3B — Run the converter (research-verified working invocation; will OVERWRITE the committed build.py):

      python3 tools/sla_to_dsl.py \
          templates/zeitung-a4-grun/template.sla \
          templates/zeitung-a4-grun/build.py \
          --template-id zeitung-a4-grun \
          --assets-dir templates/zeitung-a4-grun/assets/

  STEP 3C — Sanity check the regenerated file. Run the following inline check (adapt the script if the file's quoting style needs adjustment):

      python3 -c "
      import re, ast
      src = open('templates/zeitung-a4-grun/build.py').read()
      print('LOC:', len(src.splitlines()))
      for k in ('extra_doc_attrs','extra_pdf_attrs'):
          m = re.search(k+r'\s*=\s*(\{[^}]*\})', src, re.S)
          d = ast.literal_eval(m.group(1)); print(k, len(d), 'keys')
      print('Brand:', 'Brand.gruene_noe()' in src)
      print('palette_replaces_ci=True:', 'palette_replaces_ci=True' in src)
      print('explicit layers=:', 'layers=[DocumentLayer(' in src)
      print('var pgno count:', src.count(\"var='pgno'\"))
      print('chain frame count:', len(re.findall(r'_chain\d+_\d+\s*=\s*TextFrame\(', src)))
      print('link_to count:', src.count('.link_to('))
      print('custom_path count:', src.count('custom_path='))
      print('clip_edit count:', src.count('clip_edit=True'))
      "

  Expected (RESEARCH-projected; ±5 acceptable on LOC, ±0 acceptable on the structural counts):
  - LOC: ~2526
  - extra_doc_attrs: 23 keys
  - extra_pdf_attrs: 11 keys
  - Brand: True
  - palette_replaces_ci=True: False
  - explicit layers=: False
  - var pgno count: 12
  - chain frame count: 42
  - link_to count: 28
  - custom_path count: 0
  - clip_edit count: 87 (or 86 — RESEARCH-noted ±1 ambiguity is acceptable)

  If any of `Brand: True`, `palette_replaces_ci=True: False`, `extra_doc_attrs <= 23`, `extra_pdf_attrs <= 11`, `var pgno count == 12`, `chain frame count == 42`, `link_to count == 28`, `custom_path count == 0` fails — STOP and inspect. The converter behavior changed since RESEARCH.md was written.

  STEP 3D — Smoke test the regen builds:

      cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks/templates/zeitung-a4-grun && python3 build.py && cd ../..

  This regenerates `template.sla` from the new build.py. The SLA should be valid XML and around 530-550 KB in size (RESEARCH measured 538740 bytes on a similar run). DO NOT hand-edit `template.sla` after rebuild — it is purely a build artifact.

  STEP 3E — Confirm the structural diff with allowlist is clean (this is the gate Task 1 unblocked):

      python3 tools/sla_diff.py \
          --left gruene-zeitung-vorlage-original.sla \
          --right templates/zeitung-a4-grun/template.sla \
          --strict --allow-brand-extras > /dev/null

  Must exit 0. If it exits 1, inspect with:

      python3 tools/sla_diff.py \
          --left gruene-zeitung-vorlage-original.sla \
          --right templates/zeitung-a4-grun/template.sla \
          --strict --allow-brand-extras --json - | head -200

  There should be ZERO unfiltered warnings. If `missing-layer Ebene 1` still appears, Task 1 didn't land correctly. If a different non-brand warning appears (e.g. an unexpected `extra-color` whose name is not in `_BRAND_COLOR_NAMES`, or an `attr-differs` from a converter regression), the converter behavior changed since RESEARCH.md was written; STOP and surface to user.

  STEP 3F — Confirm visual_diff is byte-clean (this is the rendering acceptance gate; budget ~30-60 seconds for the 14-page render at 96 dpi):

      python3 tools/visual_diff.py \
          templates/zeitung-a4-grun/template.sla \
          --baseline templates/zeitung-a4-grun/baseline.pdf \
          --tolerance templates/zeitung-a4-grun/diff.yml \
          --dpi 96 \
          --out build/validation/zeitung-a4-grun/

  Must exit 0. RESEARCH.md verified live that per-page mismatch is essentially 0% on the regenerated SLA before any block substitutions. If mismatch jumps above the 1% threshold defined in `diff.yml`, the converter regressed since research; STOP and surface to user.

  CONSTRAINT: Do NOT hand-edit any frame DSL in this task. RESEARCH.md is explicit that the raw regen meets 3 of 4 numeric ACs immediately. Block substitutions are Tasks 4-5.
  CONSTRAINT: Do NOT hand-add `layers=[DocumentLayer('Ebene 1', ...)]` to recover the legacy layer. Task 1's filter handles the `missing-layer Ebene 1` warning; the brand stack is the canonical layer set going forward.
  CONSTRAINT: Do NOT widen `Impressum`, `ContactBlock`, `PageNumber` (already done in Task 2), `PageBackground`, or `ColumnTextStory` block APIs in this task.
  CONSTRAINT: Do NOT touch `templates/zeitung-a4-grun/template.sla` outside the rebuild. The build.py regenerates it.
  CONSTRAINT: If the regen output mismatches RESEARCH.md's measurements substantially (e.g. emits `palette_replaces_ci=True`, has > 23 doc-attrs, has > 11 pdf-attrs, emits an explicit `layers=[DocumentLayer(`, or has `custom_path=` count > 0), STOP and inspect — Tasks 1-2 may have introduced unintended side effects, OR the converter changed since research.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks && python3 -c "import ast; ast.parse(open('templates/zeitung-a4-grun/build.py').read())" && grep -q "brand=Brand.gruene_noe()" templates/zeitung-a4-grun/build.py && ! grep -q "palette_replaces_ci=True" templates/zeitung-a4-grun/build.py && ! grep -q "DocumentLayer(name='Ebene 1'" templates/zeitung-a4-grun/build.py && cd templates/zeitung-a4-grun && python3 build.py && cd ../.. && python3 -c "
import re, ast
src = open('templates/zeitung-a4-grun/build.py').read()
for k in ('extra_doc_attrs','extra_pdf_attrs'):
    m = re.search(k+r'\s*=\s*(\{[^}]*\})', src, re.S)
    d = ast.literal_eval(m.group(1)); print(k, len(d))
    assert len(d) <= (23 if 'doc' in k else 11), k+' over budget'
print('LOC:', len(src.splitlines()))
print('var pgno:', src.count(\"var='pgno'\")); assert src.count(\"var='pgno'\") == 12
print('chain frames:', len(re.findall(r'_chain\d+_\d+\s*=\s*TextFrame\(', src))); assert len(re.findall(r'_chain\d+_\d+\s*=\s*TextFrame\(', src)) == 42
print('link_to:', src.count('.link_to(')); assert src.count('.link_to(') == 28
print('custom_path:', src.count('custom_path=')); assert src.count('custom_path=') == 0
print('OK')
" && python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict --allow-brand-extras > /dev/null && python3 tools/visual_diff.py templates/zeitung-a4-grun/template.sla --baseline templates/zeitung-a4-grun/baseline.pdf --tolerance templates/zeitung-a4-grun/diff.yml --dpi 96 --out build/validation/zeitung-a4-grun/</automated>
  </verify>
  <done>
  - `templates/zeitung-a4-grun/build.py` is the converter-regenerated version (~2526 LOC).
  - `Document(...)` uses `brand=Brand.gruene_noe()`.
  - No `palette_replaces_ci=True` anywhere in the file.
  - No explicit `layers=[DocumentLayer(` in the file.
  - `extra_doc_attrs` exactly 23 keys; `extra_pdf_attrs` exactly 11 keys.
  - 12 `var='pgno'` Run instances; 42 chain TextFrame assignments; 28 `link_to()` calls; 0 `custom_path=`.
  - `python3 build.py` succeeds and regenerates a valid `template.sla` (~530-550 KB).
  - `tools/sla_diff.py --strict --allow-brand-extras` exits 0 against `gruene-zeitung-vorlage-original.sla`.
  - `tools/visual_diff.py` exits 0 against the committed `baseline.pdf` with `diff.yml` tolerance (per-page mismatch under 1%).
  </done>
  <commit_message>8: refactor(zeitung): regenerate build.py via converter onto Brand</commit_message>
</task>

<task type="auto">
  <name>Task 4: Substitute the 12 PageNumber frames with PageNumber(...) block calls</name>
  <files>templates/zeitung-a4-grun/build.py, templates/zeitung-a4-grun/template.sla</files>
  <action>
  GOAL: Replace each of the 12 `pageX.add(TextFrame(... var='pgno' ...))` blocks in the regenerated build.py with `pageX.add(PageNumber(...))` block calls, using the kwarg passthroughs added in Task 2 to preserve attr fidelity (CLIPEDIT, COLGAP, LINEWIDTH, and the 1 white-on-dark var_attrs case on page 12). Expected LOC delta: ~144 (12 frames × ~12 LOC each).

  STEP 4A — Find all 12 PageNumber TextFrame blocks. Use grep to locate the line numbers:

      grep -n "var='pgno'" templates/zeitung-a4-grun/build.py

  Should return exactly 12 hits. For each hit, the surrounding `TextFrame(...)` extends roughly 13-14 lines from a `pageX.add(TextFrame(` opener to a `))` closer.

  Approximate regen line ranges (RESEARCH-measured; use grep result as the authoritative source):
  - 446-459, 599-612, 691-704, 862-875, 964-977, 1236-1249, 1379-1392, 1513-1526, 1680-1693, 1970-1983, 2157-2170, 2302-2315.

  Pages with pgno (per RESEARCH inventory): 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13. (No pgno on Titelseite/page 0 or page 10.)

  STEP 4B — Add `PageNumber` to the imports near the top of the file. Find the `from sla_lib.builder import ...` block (or `from sla_lib.builder.blocks import ...` — match the existing style of the regen). Add `PageNumber` to the imported names. If the regen does not import any block (because the converter doesn't emit block calls), add a new import line:

      from sla_lib.builder.blocks import PageNumber

  Match whichever exact import path the existing imports use (e.g. `from sla_lib.builder import Document, Page, TextFrame` would imply adding `, PageNumber` to that line, but inspect the file's actual import surface first — Plakat's regen uses `from sla_lib.builder import ...`; Zeitung's may differ).

  STEP 4C — For each of the 12 pgno blocks, replace it with a `PageNumber(...)` call. Each replacement preserves the ORIGINAL frame's `x_mm`, `y_mm`, `w_mm`, `h_mm`, `layer` (always 0 for Zeitung pgnos), `anname`, `clip_edit` (always True), `line_width_pt` (always 1), `col_gap_mm` (verbatim float — copy exactly, do NOT round), and `var_attrs` (None for 11 of 12; `{'FCOLOR': 'White', 'FSHADE': '100'}` for the page 12 frame).

  Example BEFORE (around regen line 446):

      page1.add(TextFrame(
          x_mm=8.51073047881968,
          y_mm=283.69722222116576,
          w_mm=12.775464220466706,
          h_mm=9.480247708017236,
          layer=0,
          anname='Kopie von u2d45',
          clip_edit=True,
          line_width_pt=1,
          col_gap_mm=3.207461712525627,
          runs=[
              Run(text='', has_itext=False, var='pgno', separator='para', paragraph_style='Seitenzahl'),
          ],
      ))

  Example AFTER:

      page1.add(PageNumber(
          x_mm=8.51073047881968,
          y_mm=283.69722222116576,
          w_mm=12.775464220466706,
          h_mm=9.480247708017236,
          layer=0,
          anname='Kopie von u2d45',
          clip_edit=True,
          line_width_pt=1,
          col_gap_mm=3.207461712525627,
      ))

  For the page-12 white-on-dark pgno frame (around regen line 2157), include the `var_attrs` kwarg:

      page12.add(PageNumber(
          x_mm=...,
          y_mm=...,
          w_mm=...,
          h_mm=...,
          layer=0,
          anname='...',
          clip_edit=True,
          line_width_pt=1,
          col_gap_mm=...,
          var_attrs={'FCOLOR': 'White', 'FSHADE': '100'},
      ))

  CRITICAL: Preserve `paragraph_style='Seitenzahl'` semantics. Since `Seitenzahl` is the PageNumber default for `style=`, do NOT pass `style=` (the kwarg-name on PageNumber is `style`, not `paragraph_style`). If any of the 12 frames carries a `paragraph_style` OTHER than `'Seitenzahl'`, pass that explicitly as `style='<that name>'` — but RESEARCH.md verified all 12 use `'Seitenzahl'` so the default applies.

  STEP 4D — Verify the substituted file parses and builds:

      python3 -c "import ast; ast.parse(open('templates/zeitung-a4-grun/build.py').read())"
      cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks/templates/zeitung-a4-grun && python3 build.py && cd ../..

  STEP 4E — Confirm the structural diff is still clean:

      python3 tools/sla_diff.py \
          --left gruene-zeitung-vorlage-original.sla \
          --right templates/zeitung-a4-grun/template.sla \
          --strict --allow-brand-extras > /dev/null

  Must exit 0. If `attr-differs` warnings on `CLIPEDIT`, `COLGAP`, or `LINEWIDTH` for the 12 pgno PAGEOBJECTs appear, Task 2's PageNumber widening did NOT correctly forward those kwargs — STOP and fix Task 2 before proceeding.

  STEP 4F — Confirm visual_diff is still byte-clean (this MUST stay green; PageNumber substitution is a structural refactor not a visual change):

      python3 tools/visual_diff.py \
          templates/zeitung-a4-grun/template.sla \
          --baseline templates/zeitung-a4-grun/baseline.pdf \
          --tolerance templates/zeitung-a4-grun/diff.yml \
          --dpi 96 \
          --out build/validation/zeitung-a4-grun/

  Must exit 0. Per-page mismatch must remain under 1%. **Visual-diff fidelity is the correctness gate; any pixel drift beyond `diff.yml` thresholds means revert this task.**

  STEP 4G — Verify count: `grep -c "PageNumber(" templates/zeitung-a4-grun/build.py` should return 12 (exactly one per substituted frame). `grep -c "var='pgno'" templates/zeitung-a4-grun/build.py` should return 0 (the block emits Run(var='pgno') internally; no literal var='pgno' should remain in the build).

  CONSTRAINT: Substitute EXACTLY the 12 pgno frames. Do NOT touch any other TextFrame (including chain frames — those are Task 5).
  CONSTRAINT: Do NOT widen `PageNumber` further in this task. If a frame needs an attr the block doesn't accept, STOP and surface — but RESEARCH.md verified the 4 fields added in Task 2 cover all 12 cases.
  CONSTRAINT: Do NOT round any numeric kwargs. Copy `col_gap_mm`, `line_width_pt`, `x_mm`, `y_mm`, `w_mm`, `h_mm` verbatim including all trailing decimal digits — even tiny rounding changes the SLA's `XPOS=...` / `WIDTH=...` strings and may pollute the structural diff with float-precision attr-differs.
  CONSTRAINT: Do NOT delete the trailing `link_to()` block at lines ~3214-3241. That is Task 5.
  CONSTRAINT: Do NOT touch `templates/zeitung-a4-grun/template.sla` outside the rebuild.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks && python3 -c "import ast; ast.parse(open('templates/zeitung-a4-grun/build.py').read())" && test "$(grep -c 'PageNumber(' templates/zeitung-a4-grun/build.py)" -eq 12 && test "$(grep -c "var='pgno'" templates/zeitung-a4-grun/build.py)" -eq 0 && cd templates/zeitung-a4-grun && python3 build.py && cd ../.. && python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict --allow-brand-extras > /dev/null && python3 tools/visual_diff.py templates/zeitung-a4-grun/template.sla --baseline templates/zeitung-a4-grun/baseline.pdf --tolerance templates/zeitung-a4-grun/diff.yml --dpi 96 --out build/validation/zeitung-a4-grun/</automated>
  </verify>
  <done>
  - 12 `PageNumber(...)` block calls in `templates/zeitung-a4-grun/build.py` (one per substituted frame).
  - 0 literal `var='pgno'` Runs remain in the file (the block emits the Run internally).
  - Page 12's white-on-dark PageNumber call carries `var_attrs={'FCOLOR': 'White', 'FSHADE': '100'}`.
  - All 12 calls preserve `clip_edit=True`, `line_width_pt=1`, `col_gap_mm=<verbatim float>`, `layer=0`, and `anname` from the original frames.
  - `PageNumber` is imported from the appropriate sla_lib module.
  - `python3 build.py` succeeds; rebuilt SLA is valid XML.
  - `tools/sla_diff.py --strict --allow-brand-extras` exits 0 (no new attr-differs from PageNumber substitutions).
  - `tools/visual_diff.py` exits 0 (per-page mismatch under 1%).
  - LOC has dropped by ~144 from the 2526-LOC regen baseline (now ~2380; informational only).
  </done>
  <commit_message>8: refactor(zeitung): substitute PageNumber block for 12 var pgno frames</commit_message>
</task>

<task type="auto">
  <name>Task 5: Substitute the 14 ColumnTextStory chains and delete trailing link_to() block</name>
  <files>templates/zeitung-a4-grun/build.py, templates/zeitung-a4-grun/template.sla</files>
  <action>
  GOAL: Replace each of the 14 `_chain<N>_<idx>` chains in the regenerated build.py with one `pageX.add(ColumnTextStory(frames=[...], runs=[...]))` block call, and delete the trailing block of 28 `link_to()` calls (the block emits link_to internally). Expected LOC delta: ~84 (14 chains × ~6 LOC saved each, plus ~28 LOC saved by deleting the trailing link_to block, partially offset by the block-call wrapping overhead).

  STEP 5A — Add `ColumnTextStory` to the imports near the top of the file. Match Task 4's import style:

      from sla_lib.builder.blocks import ColumnTextStory, PageNumber

  (or `from sla_lib.builder import ..., ColumnTextStory` if that's how Task 4 imported PageNumber — match exactly).

  STEP 5B — Locate the 14 chains. Use grep:

      grep -n "_chain[0-9]*_0 = TextFrame(" templates/zeitung-a4-grun/build.py

  Should return exactly 14 hits (one per chain's first frame). The chains are numbered 0 through 13 in the regen (NOT necessarily 1-14; chain numbering follows the converter's internal allocation order, not the page order).

  Chain ownership (from RESEARCH.md inventory):
  - chain1 on page1
  - chain0 + chain2 on page2 (TWO chains on one page)
  - chain3 on page3
  - chain4 on page4
  - chain5 on page5
  - chain6 on page6
  - chain7 on page7
  - chain8 on page8
  - chain9 on page9
  - chain10 on page10
  - chain11 on page11
  - chain12 + chain13 on page12 (TWO chains on one page)
  - (No chains on Titelseite/page 0 or back-page/page 13; the back-page Impressum is independent.)

  STEP 5C — For each chain, identify and collapse this 6-LOC-skeleton pattern (regen typically emits this contiguously per chain; ~60 LOC per chain including frame definitions and runs):

  BEFORE (chain1 on page1, schematic):

      _chain1_0 = TextFrame(
          x_mm=20.00, y_mm=130.75, w_mm=54.67, h_mm=146.25,
          layer=0, anname='Kopie von u2f23',
          clip_edit=True, col_gap_mm=4.23,
          runs=[
              Run(text='Perem la posseditatur ...', fontsize=12, separator='para', paragraph_style='Einleitungstext'),
              Run(text='...', ...),
              # ... 8-12 story runs total
          ],
      )
      page1.add(_chain1_0)

      _chain1_1 = TextFrame(
          x_mm=77.67, y_mm=130.75, w_mm=54.67, h_mm=146.25,
          layer=0, anname='Kopie von u2f23 (2)',
          clip_edit=True, col_gap_mm=4.23,
          # NO runs — empty TextFrame, story flows in via link_to from _chain1_0
      )
      page1.add(_chain1_1)

      _chain1_2 = TextFrame(
          x_mm=135.34, y_mm=130.75, w_mm=54.67, h_mm=146.25,
          layer=0, anname='Kopie von u2f23 (3)',
          clip_edit=True, col_gap_mm=4.23,
      )
      page1.add(_chain1_2)

  AFTER (chain1 collapsed into a single block call):

      page1.add(ColumnTextStory(
          frames=[
              TextFrame(
                  x_mm=20.00, y_mm=130.75, w_mm=54.67, h_mm=146.25,
                  layer=0, anname='Kopie von u2f23',
                  clip_edit=True, col_gap_mm=4.23,
              ),
              TextFrame(
                  x_mm=77.67, y_mm=130.75, w_mm=54.67, h_mm=146.25,
                  layer=0, anname='Kopie von u2f23 (2)',
                  clip_edit=True, col_gap_mm=4.23,
              ),
              TextFrame(
                  x_mm=135.34, y_mm=130.75, w_mm=54.67, h_mm=146.25,
                  layer=0, anname='Kopie von u2f23 (3)',
                  clip_edit=True, col_gap_mm=4.23,
              ),
          ],
          runs=[
              Run(text='Perem la posseditatur ...', fontsize=12, separator='para', paragraph_style='Einleitungstext'),
              Run(text='...', ...),
              # ... all 8-12 story runs from the original first frame, copied verbatim
          ],
      ))

  KEY POINTS for each substitution:
  - The first frame (`_chainN_0`) carries the story `runs=[...]`. Hoist these into the outer `ColumnTextStory(runs=[...])` argument; remove from the first frame's TextFrame literal.
  - Frames 1 and 2 (`_chainN_1`, `_chainN_2`) had no `runs=`; their TextFrame literals stay shape-identical inside the `frames=[...]` list.
  - The first frame may carry `trail_style='Fließtext '` (note trailing space — preserve VERBATIM) and a unique `line_width_pt`. Pass these on the FIRST TextFrame in the `frames=[...]` list, not on the outer block.
  - All 3 frames carry `clip_edit=True` and `col_gap_mm` — preserve verbatim on each frame.
  - DROP the 3 `pageX.add(_chainN_<idx>)` lines per chain (replaced by the single `pageX.add(ColumnTextStory(...))`).
  - DROP the 3 `_chainN_<idx> = ...` variable bindings (no longer needed since each TextFrame is now an inline literal inside the `frames=[...]` list).

  STEP 5D — Delete the trailing `link_to()` block. The regen emits 28 link_to calls clustered at the END of the file, just before `doc.save(...)`. Approximate location: lines ~3214-3241 in the regen (post-Task 4 line numbers will be ~144 lower; use grep to find the cluster).

      grep -n "_chain[0-9]*_[0-9]*\.link_to(" templates/zeitung-a4-grun/build.py

  Should return 28 hits clustered together. Delete every line in this cluster (also delete any blank lines / comment lines that exclusively bracket the cluster). After deletion, NO `_chainN_<idx>.link_to(` calls should remain in the file. The block emits link_to internally inside `ColumnTextStory.emit()` via `frames[i].link_to(frames[i+1])`.

  STEP 5E — Verify count and structure:

      python3 -c "import ast; ast.parse(open('templates/zeitung-a4-grun/build.py').read())"
      grep -c "ColumnTextStory(" templates/zeitung-a4-grun/build.py   # should be 14
      grep -c "_chain" templates/zeitung-a4-grun/build.py             # should be 0 (no leftover named-var refs)
      grep -c "\.link_to(" templates/zeitung-a4-grun/build.py         # should be 0

  STEP 5F — Build and validate:

      cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks/templates/zeitung-a4-grun && python3 build.py && cd ../..

      python3 tools/sla_diff.py \
          --left gruene-zeitung-vorlage-original.sla \
          --right templates/zeitung-a4-grun/template.sla \
          --strict --allow-brand-extras > /dev/null

      python3 tools/visual_diff.py \
          templates/zeitung-a4-grun/template.sla \
          --baseline templates/zeitung-a4-grun/baseline.pdf \
          --tolerance templates/zeitung-a4-grun/diff.yml \
          --dpi 96 \
          --out build/validation/zeitung-a4-grun/

  Both must exit 0. If `chain-*` warnings appear in `sla_diff` output (e.g. `chain-length-mismatch`, `chain-order`, `chain-runs-mismatch`), the substitution dropped a frame/run/order — STOP and inspect the chain structure. The block calls `frames[i].link_to(frames[i+1])` internally so chain length is preserved as long as `frames=[...]` has 3 elements per chain.

  CONSTRAINT: Substitute EXACTLY the 14 chains. Do NOT touch any other TextFrame (including PageNumber frames already substituted in Task 4 and inline TextFrames / ImageFrames / Polygons that stay primitive).
  CONSTRAINT: Do NOT widen `ColumnTextStory`. The block already accepts `frames=[...]` and `runs=[...]` verbatim; the chain frames' kwargs (clip_edit, col_gap_mm, trail_style, anname, line_width_pt) flow through unchanged because they're attached to the inner TextFrame literals.
  CONSTRAINT: Do NOT round any numeric kwargs. Same float-precision discipline as Task 4.
  CONSTRAINT: Do NOT preserve the `_chainN_<idx>` variable bindings. They were a converter artifact for the named-variable chain pattern; the block call obviates them.
  CONSTRAINT: Do NOT preserve the trailing `link_to()` block. ColumnTextStory.emit() generates link_to internally.
  CONSTRAINT: Verify the order of `frames=[...]` matches the original chain order (frame 0 first, frame 2 last). The block does `link_to(frames[i+1])` in list order, so reversed order would reverse the story flow.
  CONSTRAINT: The first frame's `runs=` MUST move to the outer `ColumnTextStory.runs=` argument; do NOT leave the first-frame `runs=` AND a duplicate outer `runs=`. The block attaches outer `runs` to `frames[0]` automatically (`first.runs = list(self.runs)`).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks && python3 -c "import ast; ast.parse(open('templates/zeitung-a4-grun/build.py').read())" && test "$(grep -c 'ColumnTextStory(' templates/zeitung-a4-grun/build.py)" -eq 14 && test "$(grep -c '_chain' templates/zeitung-a4-grun/build.py)" -eq 0 && test "$(grep -c '\.link_to(' templates/zeitung-a4-grun/build.py)" -eq 0 && cd templates/zeitung-a4-grun && python3 build.py && cd ../.. && python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict --allow-brand-extras > /dev/null && python3 tools/visual_diff.py templates/zeitung-a4-grun/template.sla --baseline templates/zeitung-a4-grun/baseline.pdf --tolerance templates/zeitung-a4-grun/diff.yml --dpi 96 --out build/validation/zeitung-a4-grun/</automated>
  </verify>
  <done>
  - 14 `ColumnTextStory(...)` block calls in `templates/zeitung-a4-grun/build.py` (one per substituted chain).
  - 0 `_chain` references and 0 `.link_to(` calls remain (the block emits link_to internally).
  - Each ColumnTextStory call carries `frames=[TextFrame(...), TextFrame(...), TextFrame(...)]` (3 frames per chain) and `runs=[...]` (the story runs hoisted from the original first frame).
  - Frame ordering matches the original chain order; first-frame kwargs (trail_style, line_width_pt, anname) are preserved as inner TextFrame kwargs.
  - `python3 build.py` succeeds; rebuilt SLA is valid XML.
  - `tools/sla_diff.py --strict --allow-brand-extras` exits 0 (no `chain-*` warnings; no new attr-differs).
  - `tools/visual_diff.py` exits 0 (per-page mismatch under 1%).
  - LOC has dropped by ~84 from the post-Task-4 baseline (now ~2300; informational only).
  </done>
  <commit_message>8: refactor(zeitung): substitute ColumnTextStory block for 14 linked chains</commit_message>
</task>

<task type="auto">
  <name>Task 6: Update ZeitungRoundTrip allowlist, rebuild gallery, run full validation, write EXECUTION.md</name>
  <files>tools/sla_lib/tests/test_sla_to_dsl.py, templates/zeitung-a4-grun/template.sla, templates/zeitung-a4-grun/page-01.png, templates/zeitung-a4-grun/page-02.png, templates/zeitung-a4-grun/page-03.png, templates/zeitung-a4-grun/page-04.png, templates/zeitung-a4-grun/page-05.png, templates/zeitung-a4-grun/page-06.png, templates/zeitung-a4-grun/page-07.png, templates/zeitung-a4-grun/page-08.png, templates/zeitung-a4-grun/page-09.png, templates/zeitung-a4-grun/page-10.png, templates/zeitung-a4-grun/page-11.png, templates/zeitung-a4-grun/page-12.png, templates/zeitung-a4-grun/page-13.png, templates/zeitung-a4-grun/page-14.png, templates/zeitung-a4-grun/preview.pdf, templates/zeitung-a4-grun/meta.yml, .issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md</files>
  <action>
  GOAL: Update `ZeitungRoundTrip.test_diff_against_original_clean` to filter the 13 brand-additive + brand-replacement warnings, run the full validation pipeline, regenerate the gallery, and write EXECUTION.md.

  STEP 6A — Edit `tools/sla_lib/tests/test_sla_to_dsl.py` lines 170-176 (the `test_diff_against_original_clean` method on `ZeitungRoundTrip`). Mirror PlakatRoundTrip's pattern at lines 119-150 PLUS add the new `missing-layer Ebene 1` clause.

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
          # styles, the 4-layer brand stack (Hintergrund/Bilder/Text/Hilfslinien),
          # and the full 7-color palette. Zeitung's original SLA carries a single
          # legacy layer named 'Ebene 1' that the brand stack replaces, so rebuilding
          # adds a 'missing-layer Ebene 1' warning. All four categories of warnings
          # are additive-only or replacement-only (do not change rendering) and are
          # tolerated the same way as PostkarteRoundTrip and PlakatRoundTrip.
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

  STEP 6B — Do NOT touch `test_chain_topology_intact` (lines 178-184). It is independent of the warning allowlist and continues to pass after the chain substitutions in Task 5 (the block emits the same `link_to()` topology).

  STEP 6C — Run the test to confirm it passes against the rewritten Zeitung build.py:

      python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip -x -v

  Both `test_diff_against_original_clean` and `test_chain_topology_intact` must pass.

  STEP 6D — Run the full test suite to confirm no regressions in adjacent test classes:

      python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py -x
      python3 -m pytest tools/sla_lib/tests -x

  Both must exit 0. The 251+ tests pre-this-issue should all still pass, plus the 2 new `AllowBrandExtras*` tests from Task 1 and the 3+ new PageNumber widening tests from Task 2.

  STEP 6E — Regenerate gallery previews (budget ~1-2 minutes for the 14-page render):

      bin/render-gallery

  This regenerates `page-01.png` through `page-14.png`, `preview.pdf`, and updates `meta.yml::previews_for_sla` to the new SHA256 of `template.sla`. Zeitung is 14 pages so there are 14 page PNGs (NOT 1 like Plakat, NOT 2 like Postkarte).

  STEP 6F — Run the structural diff explicitly to confirm allowlist behavior on the rewritten Zeitung:

      python3 tools/sla_diff.py \
          --left gruene-zeitung-vorlage-original.sla \
          --right templates/zeitung-a4-grun/template.sla \
          --strict \
          --allow-brand-extras

  Must exit 0. For comparison, run WITHOUT `--allow-brand-extras` and WITH `--strict` — exit code SHOULD be 1 (because the brand extras + missing-layer Ebene 1 are still present, just allowlisted). Capture the WITHOUT exit code and the WITH exit code; both go in EXECUTION.md as proof the allowlist is doing real work for Zeitung.

  STEP 6G — Full validation pipeline:

      bin/validate --ci

  All three templates (postkarte, plakat, zeitung) must report `sla_diff: PASS` and `visual_diff: PASS`. Exit code must be 0.

  STEP 6H — CI compliance check:

      python3 tools/check_ci.py templates/zeitung-a4-grun/template.sla

  Must exit 0.

  STEP 6I — Measure final metrics for EXECUTION.md:

      wc -l templates/zeitung-a4-grun/build.py
      python3 -c "
      import re, ast
      src = open('templates/zeitung-a4-grun/build.py').read()
      for k in ('extra_doc_attrs','extra_pdf_attrs'):
          m = re.search(k+r'\s*=\s*(\{[^}]*\})', src, re.S)
          d = ast.literal_eval(m.group(1)); print(k, len(d))
      print('PageNumber count:', src.count('PageNumber('))
      print('ColumnTextStory count:', src.count('ColumnTextStory('))
      print('Polygon count:', src.count('Polygon('))
      "

  Record actual numbers (not estimates).

  STEP 6J — Write `.issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md` with this structure:

      # Execution — Rewrite Zeitung A4 onto Brand + blocks

      **Issue:** rewrite-zeitung-onto-brand-blocks (id 8)
      **Status:** complete | partial | blocked
      **Executed:** 2026-MM-DD

      ## Tasks

      - [x] Task 1: Extend --allow-brand-extras to filter missing-layer warnings for legacy layer names
      - [x] Task 2: Widen PageNumber block with clip_edit / line_width_pt / col_gap_mm / var_attrs kwarg passthroughs
      - [x] Task 3: Regenerate templates/zeitung-a4-grun/build.py via converter (zero hand edits)
      - [x] Task 4: Substitute the 12 PageNumber frames with PageNumber(...) block calls
      - [x] Task 5: Substitute the 14 ColumnTextStory chains and delete trailing link_to() block
      - [x] Task 6: Update ZeitungRoundTrip allowlist, rebuild gallery, run full validation, write EXECUTION.md

      ## Acceptance criteria

      | # | Criterion | Status | Evidence |
      |---|---|---|---|
      | 1 | visual_diff clean | PASS | `tools/visual_diff.py ... -> exit 0; max mismatch <X>%` |
      | 2 | pytest tools/sla_lib/tests -x | PASS | `<count> tests passing` |
      | 3 | bin/validate --ci | PASS | postkarte/plakat/zeitung all PASS |
      | 4 | check_ci.py | PASS | exit 0 |
      | 5 | extra_doc_attrs <= 23 | PASS | <count> keys |
      | 6 | extra_pdf_attrs <= 11 | PASS | <count> keys |

      Informational (LOC target dropped per user direction):
      - LOC: 3244 -> <after> (target was <= 2400; achieved <after>; informational only — visual_diff is the gate)

      ## Metrics

      - LOC: 3244 -> <after> (-<delta>; informational, not an AC)
      - extra_doc_attrs: 113 -> <after-count> (criterion <=23)
      - extra_pdf_attrs: 44 -> <after-count> (criterion <=11)
      - Block substitutions: 26 = 12× PageNumber + 14× ColumnTextStory
        - PageBackground × 0 (Zeitung has 0 full-bleed Polygons; the Titelseite "full-bleed" assumption from issue scoping was wrong — all 8 polygons are decorative inline shapes)
        - Impressum × 0 (3-run heading + spacer + body schema; modern block is single-Run only — third Impressum gap surfaced in this migration sequence)
        - ContactBlock × 0 (no candidates)
      - Brand uptake: brand=Brand.gruene_noe(), palette_replaces_ci removed, layers default to Brand stack (no explicit DocumentLayer; legacy 'Ebene 1' filtered by Task 1's allowlist extension)
      - sla_diff allowlist: --allow-brand-extras now also filters legacy `missing-layer Ebene 1` (new in this issue)
      - PageNumber block: widened with clip_edit / line_width_pt / col_gap_mm / var_attrs kwarg passthroughs (new in this issue)
      - Allowlist proof: `sla_diff --strict` (no allowlist) exits <code>; `sla_diff --strict --allow-brand-extras` exits 0 (proves the allowlist does real work for Zeitung)

      ## P2 follow-ups (file as future issues, do NOT implement here)

      1. **Combined `Impressum` block widening: prefix-bold-Run idiom + rotation_deg + 3-run heading+spacer+body schema.** This is the THIRD Impressum gap surfaced across the migration sequence:
         - Postkarte (#6 P2 #1): Bold "Impressum:" prefix Run before Book body — single-Run block can't model.
         - Plakat (#7 P2 #1, #2): rotation_deg=270 + Bold-prefix Run.
         - Zeitung (#8, this issue): 3-run schema (heading "Impressum" in `Inhaltsheadline Titelseite` style + empty para spacer + body run with default trail_style) — block emits a single Run from `text=`, can't carry the heading+spacer+body shape.
         Combined widening proposal: add `runs=Sequence[Run]` override (bypasses the default-text emit), `prefix_text=`/`prefix_font=` (handles bold prefix), and `rotation_deg=` (handles vertical layout). All three templates' Impressum frames could then substitute to the block, saving ~36 LOC across the corpus.

      2. **(Optional, P3 hygiene) Add `ZeitungConverterFreshRun` test class** to mirror `PostkarteConverterFreshRun` at `tools/sla_lib/tests/test_sla_to_dsl.py:81`. Plakat (#7) deferred this same hygiene check; Zeitung is currently covered only by `ZeitungRoundTrip` + the `test_5*_zeitung_*` invariant tests, not by a from-scratch convert-and-check guard. Low priority.

      3. **(Optional, P3) Audit `extra_pdf_attrs` and `extra_doc_attrs` for further hoist candidates** now that all three templates have migrated. The exact 23/11 residual on each suggests there may be more constants across the corpus that could move into `shared/ci-defaults.yml`. Low priority — the AC bar is met.

      4. **(Optional, P3) Audit whether `_LEGACY_LAYER_NAMES` should be expanded.** Currently just `('Ebene 1',)`. If a future template surfaces a different legacy layer name (e.g. 'Layer 1' English default, 'Couche 1' French), append. Low priority — only Zeitung surfaces this gap in the current corpus.

      ## Notes

      - Zeitung is the LARGEST payoff of the three migrations: -944 LOC vs Postkarte's -68 and Plakat's -37. It's also the only migration where block substitutions provide significant value (26 subs vs Postkarte's 2 vs Plakat's 0).
      - The `--allow-brand-extras` flag has now been extended once per migration: `extra-style`/`extra-layer` (#6), `extra-color` (#7), `missing-layer` (#8 / this issue). Each extension is independent and trivially testable.
      - Three Impressum gaps are now filed across the migration sequence (Postkarte's bold-prefix, Plakat's rotation_deg, Zeitung's 3-run schema). A combined `Impressum`-widening issue is well-justified as a follow-up.
      - Visual-diff fidelity against `templates/zeitung-a4-grun/baseline.pdf` is the correctness gate. Verified clean at every step (after Task 3 regen, after Task 4 PageNumber subs, after Task 5 ColumnTextStory subs).
      - The Codex master-page text-chain bug from #5 does NOT apply to Zeitung because Zeitung's masters carry no items. No converter regressions surfaced; no converter fixes were needed in scope.

  Replace `<after>`, `<after-count>`, `<count>`, `<X>`, `<delta>`, `<code>` placeholders with actual values from Tasks 1-5 verifies and Step 6I measurements. Use `wc -l` output for LOC verbatim — do not round, estimate, or smooth.

  STEP 6K — Stage EXECUTION.md plus the artifacts modified by `bin/render-gallery` (page-01.png … page-14.png, preview.pdf, meta.yml, template.sla). The orchestrator will commit; this task just stages and writes EXECUTION.md.

  CONSTRAINT: Do NOT push or open a PR. The user runs `/issue:ship` separately.
  CONSTRAINT: Do NOT define `_LEGACY_LAYER_NAMES` as a module-level constant in `test_sla_to_dsl.py`. Keep it inline within the test method (mirrors the inline `_BRAND_COLOR_NAMES` pattern PlakatRoundTrip uses). Do NOT depend on a private `_LEGACY_LAYER_NAMES` from `sla_diff` (it's a private module attribute; duplication is intentional for test independence).
  CONSTRAINT: Do NOT add a `ZeitungConverterFreshRun` test class. RESEARCH.md (R11) flagged this as P3 hygiene; out of scope for this issue.
  CONSTRAINT: Do NOT skip `bin/render-gallery` — without it, `meta.yml::previews_for_sla` will not match the rebuilt SLA's SHA and the stale-preview gate will fail.
  CONSTRAINT: Do NOT hand-edit `meta.yml::previews_for_sla` — `bin/render-gallery` updates it as a side-effect.
  CONSTRAINT: If any AC in Step 6J's table is FAIL, mark Status as `blocked`, leave the failed checkbox unchecked, and surface the failure in EXECUTION.md notes — do NOT pretend the issue is complete.
  CONSTRAINT: If any of the three templates (Postkarte, Plakat, Zeitung) reports `visual_diff: FAIL` or `sla_diff: FAIL` after the full pipeline, STOP and diagnose — the brand-extras allowlist must NOT mask non-brand warnings. The Task 1 negative test (`test_allow_brand_extras_does_not_filter_missing_layer_for_arbitrary_name`) is the regression guard for this.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks && python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip -x -v && python3 -m pytest tools/sla_lib/tests -x && bin/render-gallery && bin/validate --ci && python3 tools/check_ci.py templates/zeitung-a4-grun/template.sla && test -f .issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md && grep -q "Acceptance criteria" .issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md && grep -q "P2 follow-ups" .issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md && grep -q "Impressum" .issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md</automated>
  </verify>
  <done>
  - `ZeitungRoundTrip.test_diff_against_original_clean` filters brand-additive `extra-style`, `extra-layer`, brand-color `extra-color`, AND legacy-layer `missing-layer Ebene 1` warnings before asserting zero non-brand warnings.
  - `ZeitungRoundTrip.test_chain_topology_intact` is unchanged and still passes (chain link_to topology preserved by `ColumnTextStory.emit()`).
  - `pytest tools/sla_lib/tests -x` is green (PostkarteRoundTrip, PostkarteConverterFreshRun, PlakatRoundTrip, ZeitungRoundTrip, AllowBrandExtrasTests with new missing-layer cases, PageNumber widening tests, all 5 `test_5*_zeitung_*` invariants).
  - `_LEGACY_LAYER_NAMES = ("Ebene 1",)` is inline in the test method (not imported from sla_diff).
  - `bin/render-gallery` regenerates `page-01.png` through `page-14.png`, `preview.pdf`, and updates `meta.yml::previews_for_sla` to the new SHA.
  - `bin/validate --ci` exits 0 with `sla_diff: PASS` and `visual_diff: PASS` for postkarte, plakat, AND zeitung.
  - `tools/check_ci.py templates/zeitung-a4-grun/template.sla` exits 0.
  - Zeitung's structural diff WITHOUT `--allow-brand-extras` still exits 1 (proves the allowlist is necessary, not redundant); WITH the flag exits 0.
  - `.issues/rewrite-zeitung-onto-brand-blocks/EXECUTION.md` exists with all 6 ACs recorded as PASS, achieved LOC (informational), `extra_doc_attrs` and `extra_pdf_attrs` counts, and at least 4 P2 follow-ups (combined Impressum widening, ZeitungConverterFreshRun hygiene, ci-defaults audit, _LEGACY_LAYER_NAMES audit).
  - Stale-preview gate is clean (`previews_for_sla` SHA matches rebuilt `template.sla`).
  </done>
  <commit_message>8: chore(zeitung): rebuild gallery, validate full pipeline, record execution</commit_message>
</task>

</tasks>

<verification>
After all tasks complete, run the final battery (this is also the body of the Task 6 verify, repeated here as a single-shot reproducer for the reviewer):

```
cd /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks
python3 -m pytest tools/sla_lib/tests -x
python3 tools/check_ci.py templates/zeitung-a4-grun/template.sla
python3 tools/visual_diff.py \
    templates/zeitung-a4-grun/template.sla \
    --baseline templates/zeitung-a4-grun/baseline.pdf \
    --tolerance templates/zeitung-a4-grun/diff.yml \
    --dpi 96 \
    --out build/validation/zeitung-a4-grun/
python3 tools/sla_diff.py \
    --left gruene-zeitung-vorlage-original.sla \
    --right templates/zeitung-a4-grun/template.sla \
    --strict --allow-brand-extras
bin/validate --ci
```

All five must exit 0. The visual_diff per-page mismatch must be under the 1% threshold defined in `templates/zeitung-a4-grun/diff.yml`. Budget: ~30-60s for visual_diff (14 A4 pages at 96 dpi); ~2-3 min for `bin/validate --ci` end-to-end. CI tolerates this.
</verification>

<success_criteria>
Maps 1:1 to the 6 acceptance criteria in ISSUE.md (LOC criterion is informational only per user direction):

1. `tools/visual_diff.py` clean against `templates/zeitung-a4-grun/baseline.pdf` within `templates/zeitung-a4-grun/diff.yml` thresholds (1% mismatch, 5% fuzz; per-page).
2. `pytest tools/sla_lib/tests -x` green (including ZeitungRoundTrip with new allowlist + new AllowBrandExtrasTests for missing-layer + new PageNumber widening tests).
3. `bin/validate --ci` green for ALL three templates (postkarte, plakat, zeitung) — enabled by Task 1's `--allow-brand-extras` extension and Task 2's PageNumber widening.
4. `tools/check_ci.py templates/zeitung-a4-grun` clean.
5. New `extra_doc_attrs` in `templates/zeitung-a4-grun/build.py` contains <= 23 keys (expected exactly 23).
6. New `extra_pdf_attrs` in `templates/zeitung-a4-grun/build.py` contains <= 11 keys (expected exactly 11).

Plus: `templates/zeitung-a4-grun/build.py` uses `brand=Brand.gruene_noe()`; carries 12 `PageNumber(...)` block calls and 14 `ColumnTextStory(...)` block calls; carries 0 `_chain` references and 0 `.link_to(` calls. `tools/sla_diff.py` documents and implements the legacy-layer extension to `--allow-brand-extras`. `tools/sla_lib/builder/blocks.py::PageNumber` accepts `clip_edit`, `line_width_pt`, `col_gap_mm`, `var_attrs` kwargs. EXECUTION.md records achieved LOC (informational, expected ~2300), all 6 AC outcomes, and the P2 follow-ups (combined Impressum widening, ZeitungConverterFreshRun hygiene, ci-defaults audit, _LEGACY_LAYER_NAMES audit).

LOC criterion (ISSUE.md line 58: `<= 2400`) is **informational only** per user direction. Achieved is expected ~2300. Record verbatim, do not gate.
</success_criteria>
