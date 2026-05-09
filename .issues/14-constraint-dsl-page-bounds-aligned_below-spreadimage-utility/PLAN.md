# Plan: Constraint DSL — page-bounds, aligned_below, SpreadImage utility (#14)

<objective>
Goal: extend the constraint DSL so the most damaging class of layout bug we have —
**a frame whose bbox crosses a page boundary** — is caught mechanically by
`structural_check`, not by visual review.

Three deliverables, atomic in one PR:

1. `brand:inside_page` — global brand-rule that checks every non-master frame's
   rotation- and anchor-aware bbox is inside `[-bleed, page_w + bleed] × [-bleed,
   page_h + bleed]` of its OWNING page.
2. `aligned_below` — per-template free-form constraint factory locking the
   "image hangs from the text above on the same left axis" pattern.
3. `SpreadImage` — block utility emitting two `inside_page`-clean `ImageFrame`s
   that together render one continuous picture across two pages, replacing the
   today-broken `(x=page_w, w=page_w)` pattern.

Why it matters: today `structural_check --all` reports zero failures even though
`templates/zeitung-a4-grun/build.py` has TWO frames whose bbox overflows the
right edge of their page by >200 mm (`P9 Spread` at line 1802-1811 and an
unnamed full-A4 at 2061-2071). Future templates will recreate the same bug
silently unless we encode the constraint in code. This issue is the foundation
for #16 (zeitung fix), #17–#21 (V1 layouts).

Scope (in):
- `_InsidePageRule` BrandRule + rotation-aware bbox helpers in
  `brand_constraints.py`.
- `_AlignedBelowConstraint` + `aligned_below()` factory in `constraints.py`.
- `SpreadImage` dataclass in `blocks.py`.
- `templates/zeitung-a4-grun/meta.yml` `brand_overrides` skip with
  `reason: "see issue #16"`.
- Doc updates: `templates/_specs/SCHEMA.md` §12 and `shared/brand/SPEC-WRITING-GUIDE.md`
  §5 + §8.
- Test additions covering the three new pieces, registry tests updated to 9 rules.

Scope (out):
- Actually fixing the Zeitung spread (that's #16 — leaves the two frames in
  build.py untouched, accepts them via `brand_overrides`).
- V1 layouts for #17–#21.
- No SLA regen, no PNG diffing, no rendering inside the test loop.
- No retrofitting `inside`'s rotation handling (scope creep).
- No new dependencies.

Locked architectural decisions (do NOT re-litigate):
- `inside_page` lives in `brand_constraints.py` as a `BrandRule` (id
  `brand:inside_page`) — needs `(primitives, doc)` for page geometry and
  benefits from the existing `meta.yml::brand_overrides` skip mechanism.
- `aligned_below` lives in `constraints.py` as a per-template `Constraint`
  factory + `_AlignedBelowConstraint` dataclass — only needs anname-keyed
  primitives.
- `SpreadImage` lives in `blocks.py` as a new dataclass with `emit()` and
  `place(page_left, page_right)` methods, mirroring the `WahlkreuzSymbol` /
  `FoldedPanel` two-page-emit precedent. Anname suffixes `· left` / `· right`.
- Rotation pivot: top-left corner of the un-rotated frame, ROT is CCW positive
  (deduced from `templates/plakat-a1-hochformat/build.py:102-116` ROT=270 case
  fitting the page only under CCW). One render-verify before merge.
- Severity split for `inside_page`: warning ≤ 1.0 mm overshoot; error > 1.0 mm.
  ISSUE.md text says cutoff is 0.5 mm; T02 includes a decision point to confirm
  with the user OR document the 1.0 mm tolerance + reason in code (the two
  existing zeitung 0.8 mm bleed-edge nudges from float-imprecise SLA emit
  shouldn't break CI but should still surface as warnings).
- Atomic PR — `pages.yml:147` runs `structural_check --all` with `set -euo
  pipefail`; partial PRs break CI.

No CONTEXT.md was authored — decisions above are based on the research
synthesis at `.issues/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/RESEARCH.md`
and confirmed against the codebase.
</objective>

<context>
Issue: @.issues/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/ISSUE.md
Research synthesis: @.issues/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/RESEARCH.md
Per-dimension reports:
- @.issues/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/research/codebase.md
- @.issues/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/research/pitfalls.md
- @.issues/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/research/ecosystem.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

# === From tools/sla_lib/builder/constraints.py ===

@dataclass(frozen=True)
class Violation:
    severity: str             # "error" | "warning" | "info"
    message: str
    rule_id: str = ""
    targets: tuple = ()       # tuple of anname strings

@dataclass(frozen=True)
class Constraint:
    id: str
    targets: tuple
    name: str = ""
    def check(self, primitives_by_anname: dict) -> list[Violation]: ...
    def referenced_annames(self) -> tuple: return self.targets

# Helpers — use as-is, do NOT redefine:
def _to_anname(t) -> str: ...                        # accept Frame.anname or str
def _norm(targets) -> tuple: ...                     # tuple of annames
def _autoname(kind: str, targets: tuple, name: str) -> str: ...
def _resolve(targets: tuple, mapping: dict) -> tuple[list, list]:
    """Returns (resolved_frames, missing_names)."""
def _missing_violation(rid: str, targets: tuple, missing: list) -> Violation: ...

# Existing factories the executor will sit alongside:
def same_y(...) -> Constraint
def same_x(...) -> Constraint
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, ...) -> Constraint
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, ...) -> Constraint
def inside(child, parent, tolerance_mm: float = 0.5, ...) -> Constraint
# ... (same_size, mirrored_x, mirrored_y, equal_gap, hierarchy, same_style)

# === From tools/sla_lib/builder/brand_constraints.py ===

@dataclass(frozen=True)
class BrandRule:
    id: str                   # MUST match ^brand:[A-Za-z_0-9.]+$
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc) -> list[Violation]: ...

# Module-level registry — the executor MUST extend this list (currently 8 entries):
BRAND_CONSTRAINTS: list[BrandRule] = [...]   # at brand_constraints.py:370

def _make_rule(cls, **kwargs) -> BrandRule: ...   # used to instantiate frozen subclasses

# === From tools/sla_lib/builder/document.py ===

MM_TO_PT = 72.0 / 25.4                # ≈ 2.83464566929
PT_TO_MM = 25.4 / 72.0                # ≈ 0.352777777777

@dataclass
class Page:
    width_pt: float                   # source-of-truth at emit time (NOT size kwarg)
    height_pt: float
    bleed_mm: float = 3.0
    margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10)
    master_name: str = ""
    label: str = ""
    items: list = field(default_factory=list)
    own_page: int = 0
    page_xpos_pt: float = 0           # scratch-canvas offset
    page_ypos_pt: float = 0
    is_left: bool = False
    is_master: bool = False
    master_id: str = ""
    def add(self, item) -> "Page": ...    # if hasattr(item, "emit") flattens

class Document:
    pages: list[Page]
    masters: list[Page]
    facing_pages: bool
    def iter_all_primitives(self) -> Iterable: ...   # masters first, then doc pages

def mm_to_pt(value_mm: float) -> float: ...

# === From tools/sla_lib/builder/primitives.py ===

@dataclass
class _Frame:
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 50
    h_mm: float = 30
    anchor: Optional[Anchor] = None       # if set, x_mm/y_mm are IGNORED at emit
    rotation_deg: float = 0               # CCW positive, pivot = top-left of un-rotated frame
    layer: int = 2
    anname: str = ""
    custom_path: Optional[str] = None
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    # Verbatim pt overrides (round-trip byte-stable):
    xpos_pt: Optional[float] = None       # scratch-canvas absolute pt; subtract page.page_xpos_pt for page-local
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""
    fcolor: str = ""
    runs: Optional[list] = None
    columns: int = 1
    col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    # ... see primitives.py for full set

@dataclass
class ImageFrame(_Frame):
    src: str = ""                         # PFILE
    image: str = ""                       # alias for src
    layer: int = 1                        # default Bilder layer
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)   # NEGATIVE x for SpreadImage right half
    local_rotation_deg: float = 0.0
    scale_type: int = 1                   # 1 = fit-to-frame, 0 = free / aspect-locked
    ratio: int = 1
    pic_art: int = 1
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0

@dataclass
class Polygon(_Frame):
    fill: str = "Black"
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0
    shape: str = "rectangle"
    fill_shade: int = 100
    dash_pattern: Optional[tuple[float, ...]] = None

# Anchor handling — mirror this when computing bbox:
def resolve_anchor(anchor: Anchor, page_w_pt: float, page_h_pt: float,
                   frame_w_pt: float, frame_h_pt: float) -> tuple[float, float]:
    """Returns (local_x_pt, local_y_pt) — relative to page top-left."""

# === From tools/sla_lib/builder/structural_check.py ===

# Orchestrator flow — already wired, the executor does NOT modify it:
# 1. mod = _load_build_module(slug); doc = mod.build_doc()
# 2. primitives = list(doc.iter_all_primitives())
# 3. primitives_by_anname = {p.anname: p for p in primitives if p.anname}
# 4. for c in mod.CONSTRAINTS: c.check(primitives_by_anname)
# 5. skip_ids = load_brand_overrides(slug, root)
# 6. for rule in BRAND_CONSTRAINTS:
#       if rule.id in skip_ids: rep.skipped_brand_rules.append(...)
#       else: rule.check(primitives, doc)

# === From tools/sla_lib/builder/__init__.py (public surface) ===
# Currently exports: same_y, same_x, same_size, mirrored_x, mirrored_y, inside,
#   equal_gap, hierarchy, same_style, distance_x, distance_y, Constraint,
#   Violation, BRAND_CONSTRAINTS, BrandRule, ... (and everything from blocks/composites)
# Executor MUST add: aligned_below to the constraints import + __all__.
# `SpreadImage` is accessed via `blocks.SpreadImage` (blocks is already exported).

</interfaces>

Key files for the executor (read each before touching):
- @tools/sla_lib/builder/brand_constraints.py — 420 LOC, registry at line 370, module docstring "The eight rules" at line 17-37.
- @tools/sla_lib/builder/constraints.py — 462 LOC, factories at end of file, helpers `_to_anname`/`_norm`/`_autoname`/`_resolve`/`_missing_violation`.
- @tools/sla_lib/builder/blocks.py — 1005 LOC, `WahlkreuzSymbol` two-emit precedent at line 487-551.
- @tools/sla_lib/builder/primitives.py — `_Frame` base, `_xy_pt` anchor logic (line 470-481), `ImageFrame` with `local_offset_mm` field.
- @tools/sla_lib/builder/document.py — `Page` dataclass, `iter_all_primitives` (line 413-425), `MM_TO_PT`/`PT_TO_MM` constants.
- @tools/sla_lib/builder/__init__.py — public surface (132 LOC).
- @tools/sla_lib/builder/meta_schema.py — `load_brand_overrides`, `^brand:[A-Za-z_0-9.]+$` regex.
- @tools/sla_lib/tests/test_constraints.py — factory test pattern.
- @tools/sla_lib/tests/test_brand_constraints.py — registry test (currently `test_eight_rules_exact`, MUST become 9).
- @tools/sla_lib/tests/test_blocks.py — block emit test pattern.
- @templates/zeitung-a4-grun/build.py — lines 1802-1811 and 2061-2071 are the two known offenders; lines 184-213 are the page9/page11 declarations.
- @templates/zeitung-a4-grun/meta.yml — existing `brand_overrides` at lines 21-30; the new entry appends here.
- @templates/_specs/SCHEMA.md — §12 at line 484, factory list at lines 493-495, brand-rule count "8 Regeln" at line 510.
- @shared/brand/SPEC-WRITING-GUIDE.md — §5 at line 154, §8 at line 268.
- @.github/workflows/pages.yml — line 147 runs `structural_check --all`.
</context>

<commit_format>
Format: conventional with numeric issue prefix (per `.issues/config.yaml::commits.prefix=true`).
Pattern: `{issue-id}: {type}({scope}): {description}`
Examples (one per task):
- `14: feat(constraints): add rotation-aware bbox helpers`
- `14: feat(brand): add brand:inside_page rule`
- `14: test(brand): update registry tests for 9-rule count`
- `14: feat(constraints): add aligned_below factory`
- `14: feat(blocks): add SpreadImage builder block`
- `14: chore(zeitung): brand_overrides skip for inside_page (see #16)`
- `14: ci(structural): verify --all green with new rule`
- `14: docs(schema): add inside_page, aligned_below, SpreadImage to SCHEMA §12`
- `14: docs(brand): add SpreadImage migration recipe to SPEC-WRITING-GUIDE`
- `14: test(zeitung): regression for the two known overflow frames`
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="true">
  <name>T01: Rotation-aware bbox helpers</name>
  <files>
    tools/sla_lib/builder/brand_constraints.py (add ~40 LOC near top of file, after imports at line 38-46),
    tools/sla_lib/tests/test_constraints_inside_page.py (new file, ~120 LOC)
  </name>
  <files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/tests/test_constraints_inside_page.py</files>

  <behavior>
  Pure-function helpers; tests written FIRST (RED), then implementation (GREEN).

  `_rotated_bbox(x, y, w, h, deg) -> (min_x, min_y, max_x, max_y)`
    - deg == 0 → fast path returns `(x, y, x+w, y+h)` exactly (no float fuzz).
    - deg ∈ {90, 180, 270} → axis-aligned closed-form (use multiples to avoid sin/cos noise; OK to use the general formula and accept ~1e-15 noise — 0.5 mm tolerance trivially absorbs it).
    - Arbitrary deg (e.g. 45, 8, 351, 355) → rotate the four corners (0,0),(w,0),(w,h),(0,h) CCW around (0,0) and translate by (x, y); take min/max of resulting xs and ys.
    - Pivot is the un-rotated frame's top-left corner. Rotation sense is CCW positive (per Scribus ROT convention; see Risks section for verification).

  `_frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]`
    - Returns `(min_x, min_y, max_x, max_y)` in PAGE-LOCAL mm.
    - Returns None if `item` lacks any of `x_mm`, `y_mm`, `w_mm`, `h_mm` (e.g. Run, ParaStyle, layer placeholder — those slip into `iter_all_primitives()` results in some templates).
    - Anchor handling: if `item.anchor is not None`, compute the page-local pt position via `resolve_anchor(item.anchor, page.width_pt, page.height_pt, mm_to_pt(item.w_mm), mm_to_pt(item.h_mm))` and convert to mm via `PT_TO_MM`. Mirrors `_Frame._xy_pt` at primitives.py:470-481. Otherwise read `item.x_mm` / `item.y_mm` directly.
    - Verbatim-pt-override handling (xpos_pt / ypos_pt / width_pt / height_pt): for FIRST CUT, fall back to `x_mm/y_mm/w_mm/h_mm` and add a docstring note "Verbatim-pt overrides are not yet honored; the two known offenders use *_mm directly so this is safe today." Document as a known limitation. (Pitfall P-2 / P-15.)
    - Rotation handling: read `item.rotation_deg` (default 0); pass through `_rotated_bbox`.
  </behavior>

  <action>
  RED — write tests first in `tools/sla_lib/tests/test_constraints_inside_page.py`.

  Test file preamble (mandatory; matches existing pattern):

  ```python
  """Tests for rotation-aware bbox helpers and brand:inside_page rule (Issue #14)."""
  from __future__ import annotations
  import sys
  import unittest
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(ROOT / "tools"))

  from sla_lib.builder import Document  # noqa: E402
  from sla_lib.builder.primitives import (  # noqa: E402
      TextFrame, ImageFrame, Polygon, Anchor,
  )
  from sla_lib.builder.brand_constraints import (  # noqa: E402
      _rotated_bbox, _frame_bbox_mm,
  )
  ```

  Test cases for `_rotated_bbox` (class `RotatedBboxTests`):
  - `test_no_rotation_returns_corners`: `_rotated_bbox(10, 20, 50, 30, 0)` → `(10, 20, 60, 50)` exactly.
  - `test_rotation_90_ccw`: `_rotated_bbox(0, 0, 50, 30, 90)` → bbox spans `[-30, 0] × [0, 50]` (within 1e-9). With CCW: corner (w, 0) maps to (0, w); corner (w, h) maps to (-h, w); corner (0, h) maps to (-h, 0). So min_x=-h=-30, max_x=0, min_y=0, max_y=w=50.
  - `test_rotation_180`: `_rotated_bbox(0, 0, 50, 30, 180)` → bbox spans `[-50, 0] × [-30, 0]`.
  - `test_rotation_270_ccw`: `_rotated_bbox(0, 0, 50, 30, 270)` → bbox spans `[0, 30] × [-50, 0]`. (corner (w, 0) → (0, -w); corner (w, h) → (h, -w); corner (0, h) → (h, 0).)
  - `test_rotation_45_arbitrary`: `_rotated_bbox(0, 0, 10, 10, 45)` → check `max_x ≈ 10*cos(45°) = 7.071...`, `min_y ≈ -10*sin(45°)`, etc., with `assertAlmostEqual` and places=6.
  - `test_rotation_355_small_ccw`: `_rotated_bbox(0, 0, 25, 25, 355)` (the zeitung Störer pattern) — assert resulting bbox is < 0.5 mm wider/taller than 25×25 (the postkarte/zeitung small-rotation cases all stay within ~0.4 mm overshoot per pitfall P-1).
  - `test_translation_offset`: `_rotated_bbox(100, 200, 10, 10, 0)` → `(100, 200, 110, 210)` exactly.

  Test cases for `_frame_bbox_mm` (class `FrameBboxMmTests`):
  - `test_unrotated_textframe`: build `TextFrame(x_mm=10, y_mm=20, w_mm=50, h_mm=30, anname="x")` on a fresh A6 page; assert `_frame_bbox_mm(f, page) == (10, 20, 60, 50)` exactly.
  - `test_anchored_frame_uses_resolve_anchor`: build `Polygon(anchor=Anchor(h="left", v="top", margin_mm=5), w_mm=10, h_mm=10, x_mm=-999, y_mm=-999)` on an A4 page; assert bbox is `(5, 5, 15, 15)` (anchor obliterates `x_mm/y_mm`). Use `Anchor(h=, v=, margin_mm=)` form — NOT legacy tuple/string.
  - `test_rotated_frame`: build `TextFrame(x_mm=100, y_mm=100, w_mm=50, h_mm=20, rotation_deg=90, anname="r")`; assert bbox at top-left pivot — corners after CCW90 around (100,100): (100,100), (100,150), (80,150), (80,100). So bbox `(80, 100, 100, 150)`.
  - `test_non_frame_returns_none`: pass a `Run(text="x")` (no x_mm) — assert `_frame_bbox_mm(run, page) is None`.

  GREEN — implement helpers in `brand_constraints.py`. Add NEW imports near
  the existing import block (line 38-46 currently has `re`, `dataclass`,
  `Iterable`, `Optional`, `.ci`, `.constraints`, `.primitives`):

  ```python
  import math
  from .document import PT_TO_MM, mm_to_pt
  from .primitives import resolve_anchor
  ```

  Then add the helpers as private module-level functions, immediately
  after the `_allowed_colors`/`_all_para_styles`/`_make_rule` helpers
  (or in a new "# --- Bbox helpers (Issue #14) ---" section near the top
  of the rules list, after the BrandRule dataclass). Recommended location:
  right before the `BRAND_CONSTRAINTS` registry, so `_InsidePageRule`
  (added in T02) can reference them in the same logical block.

  ```python
  # ---------------------------------------------------------------------------
  # Bbox helpers (Issue #14) — used by _InsidePageRule
  # ---------------------------------------------------------------------------
  def _rotated_bbox(
      x: float, y: float, w: float, h: float, deg: float,
  ) -> tuple[float, float, float, float]:
      """Axis-aligned bbox of a w×h rectangle rotated CCW by ``deg`` around
      its top-left corner ``(x, y)``.

      Returns ``(min_x, min_y, max_x, max_y)`` in the same units as inputs.
      For ``deg == 0`` returns the un-rotated corners exactly (no float fuzz).
      Pivot convention matches Scribus ROT (CCW positive, top-left anchor;
      verified against the plakat Impressum ROT=270 page-fit).
      """
      if deg == 0:
          return x, y, x + w, y + h
      rad = math.radians(deg)
      cos_a, sin_a = math.cos(rad), math.sin(rad)
      pts = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
      rx = [px * cos_a - py * sin_a for px, py in pts]
      ry = [px * sin_a + py * cos_a for px, py in pts]
      return x + min(rx), y + min(ry), x + max(rx), y + max(ry)


  def _frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
      """Page-local mm bbox of ``item`` on ``page``, or ``None`` if the item
      has no spatial extent (e.g. ``Run``, ``ParaStyle``).

      Mirrors ``_Frame._xy_pt`` for anchor-positioned frames so the bbox
      reflects the SLA-emit-time position, not the dead ``x_mm/y_mm``.

      Limitation: verbatim-pt overrides (``xpos_pt`` / ``width_pt`` etc.)
      are NOT honored in this first cut — the rule falls back to ``*_mm``.
      The two known offenders (zeitung P9 Spread, unnamed page-12 image)
      use ``x_mm``/``w_mm`` directly so this is safe today; widen if a
      future template exercises the override path.
      """
      if not all(hasattr(item, a) for a in ("x_mm", "y_mm", "w_mm", "h_mm")):
          return None
      if getattr(item, "anchor", None) is not None:
          x_pt, y_pt = resolve_anchor(
              item.anchor, page.width_pt, page.height_pt,
              mm_to_pt(item.w_mm), mm_to_pt(item.h_mm),
          )
          x_mm, y_mm = x_pt * PT_TO_MM, y_pt * PT_TO_MM
      else:
          x_mm, y_mm = float(item.x_mm), float(item.y_mm)
      w_mm, h_mm = float(item.w_mm), float(item.h_mm)
      rot = float(getattr(item, "rotation_deg", 0) or 0)
      return _rotated_bbox(x_mm, y_mm, w_mm, h_mm, rot)
  ```

  REFACTOR — re-read the helpers, ensure types are concrete (no `Any`),
  ensure docstrings name the rotation sign convention explicitly.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m unittest discover -s tools/sla_lib/tests -p "test_constraints_inside_page.py" -v</automated>
  </verify>

  <done>
  - `_rotated_bbox` and `_frame_bbox_mm` exist in `brand_constraints.py`, public-by-name within the module.
  - All 11 test cases pass (7 for `_rotated_bbox`, 4 for `_frame_bbox_mm`).
  - No existing test broken: `python3 -m unittest discover tools/sla_lib/tests` exits 0.
  - Commit: `14: feat(constraints): add rotation-aware bbox helpers (Issue #14)`.
  </done>

  <dont>
  - Don't compute `resolve_anchor` with mm units — `resolve_anchor` takes pt and returns pt; convert via `mm_to_pt` then `PT_TO_MM`.
  - Don't add a "skip rotation if angle < 5°" shortcut. The general formula is < 1µs per call; the postkarte ROT=351 case has ~0.4 mm bbox growth that the shortcut would mis-bucket (pitfall P-1).
  - Don't honor `xpos_pt`/`width_pt` overrides yet — defer with a docstring note. The two known offenders don't use them (verified in research).
  - Don't pass legacy Anchor forms in tests — use `Anchor(h="left", v="top", margin_mm=...)` to avoid `DeprecationWarning` (pitfall P-14).
  </dont>
</task>

<task id="T02" type="auto" tdd="true">
  <name>T02: brand:inside_page rule + threshold confirmation</name>
  <files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/tests/test_constraints_inside_page.py</files>

  <depends-on>T01</depends-on>

  <behavior>
  Add `_InsidePageRule` dataclass + register `brand:inside_page` in `BRAND_CONSTRAINTS`.

  Rule semantics:
  - For each `page` in `doc.pages` (NOT masters — masters are abstract layout grids; see decision note below):
    - Compute `pw_mm = page.width_pt * PT_TO_MM`, `ph_mm = page.height_pt * PT_TO_MM`, `bleed = float(page.bleed_mm or 0)`.
    - For each `item` in `page.items`: bbox = `_frame_bbox_mm(item, page)`; skip if None.
    - Compute four side-overshoots: `over_l = -bleed - x0` (positive if x0 < -bleed), `over_r = x1 - (pw_mm + bleed)`, `over_t = -bleed - y0`, `over_b = y1 - (ph_mm + bleed)`. Worst overshoot = `max(over_l, over_r, over_t, over_b, 0.0)`.
    - If `worst <= 0.5`: pass (no Violation).
    - If `0.5 < worst <= 1.0`: emit Violation with `severity="warning"`. (Bleed-edge nudge bucket.)
    - If `worst > 1.0`: emit Violation with `severity="error"`. (Real overflow.)
  - Master pages are SKIPPED in this first cut. Rationale: zeitung's master pages legitimately carry full-bleed background polygons placed at `(-bleed, -bleed)` to `(w+bleed, h+bleed)` — that IS inside bleed bounds, but the conservative move is to scope to non-masters so this rule never surfaces master-page noise. Document with a comment "Master-page items skipped — they're abstract layout grids; tighten in a future issue if needed."
  - Violation message template: `f"frame {item.anname!r} bbox ({x0:.2f}, {y0:.2f})-({x1:.2f}, {y1:.2f}) exceeds page {page.label or page.master_name!r} (trim {pw_mm:.1f}×{ph_mm:.1f}, bleed {bleed:.1f}); worst overshoot {worst:.2f}mm"`.
  - Targets tuple: `(item.anname or f"<unnamed {type(item).__name__}>",)`.

  Threshold decision point (visible in code as a docstring + a constant):
  ISSUE.md acceptance text says cutoff is 0.5 mm (warning ≤ 0.5, error > 0.5).
  Research found two zeitung frames with ~0.8 mm bleed-edge nudges from float-imprecise SLA emit (`x=210.799...` on a 210 mm page with 3 mm bleed) — at 0.5 mm cutoff these would be ERRORS and break CI. Two options:
    Option A — keep 0.5 mm cutoff (matches ISSUE text strictly): then T06 brand_overrides MUST skip the entire rule for zeitung (rule-level skip — no per-frame opt-out exists; pitfall P-8). The two real overflows (>200 mm) also get silenced, which is what we want.
    Option B — split into 0.5 mm warning / 1.0 mm error: bleed-edge nudges surface as warnings (don't break CI), real overflows still surface as errors. Matches the architectural-decisions table in the prompt.
  RECOMMENDATION: implement Option B (1.0 mm error cutoff) and document the choice in code with a comment citing the ISSUE.md text and the float-precision rationale. The per-violation severity emit pattern is novel but supported (pitfall P-11 — `BrandRule.severity` field default is `"error"` but per-Violation severity wins). The acceptance criterion "exactly two `inside_page` errors" is preserved (the 0.8 mm nudges are warnings, not errors).
  EXECUTOR ACTION: implement Option B and ALSO in this task's commit message note "Implements 1.0 mm error / 0.5 mm warning split per RESEARCH §`severity split`. ISSUE acceptance text says 0.5 mm — confirmed 1.0 mm is the pragmatic choice given two ~0.8 mm float-imprecise bleed-edge nudges in existing zeitung frames; revert to 0.5 mm in a follow-up if user disagrees." (This is the explicit confirmation the user asked for. Do not add a config flag — the spec is global.)
  </behavior>

  <action>
  Tests first (RED) — append new test classes to `test_constraints_inside_page.py`:

  ```python
  from sla_lib.builder.brand_constraints import (  # noqa: E402
      BRAND_CONSTRAINTS, _InsidePageRule,
  )

  def _find_rule(rid: str):
      for r in BRAND_CONSTRAINTS:
          if r.id == rid:
              return r
      raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")
  ```

  Test classes:

  - `class InsidePageRulePassTests(unittest.TestCase)`:
    - `test_inbounds_frame_passes`: A4 doc, single frame at `(10, 10, 100, 100)` → `[]`.
    - `test_at_bleed_edge_passes`: A4 doc, polygon at `(-3, -3, 216, 303)` (exactly the bleed rectangle, bleed=3) → `[]` (worst overshoot 0).
    - `test_anchored_frame_passes`: A4 page, `Polygon(anchor=Anchor(h="right", v="top", margin_mm=10), w_mm=20, h_mm=20)` — passes because anchor places it at `(180, 10)` to `(200, 30)` on a 210-wide page.

  - `class InsidePageRuleErrorTests(unittest.TestCase)`:
    - `test_overflow_right_more_than_1mm_is_error`: A4 doc, frame at `(210, 0, 210, 100)` (the P9 Spread shape) → exactly one Violation, `severity="error"`, `rule_id="brand:inside_page"`, target tuple non-empty, message contains `"exceeds page"` AND `"P9 Spread"` (use `anname="P9 Spread"`).
    - `test_overflow_left`: A4 frame at `(-10, 0, 50, 50)` (extends to x=-10, bleed=3, overshoot 7 mm) → severity="error".
    - `test_overflow_top`: A4 frame at `(0, -10, 50, 50)` → severity="error".
    - `test_overflow_bottom`: A4 (297 tall) frame at `(0, 250, 50, 80)` (y=330) → severity="error".

  - `class InsidePageRuleWarningTests(unittest.TestCase)`:
    - `test_bleed_nudge_within_1mm_is_warning`: frame at `(0, 0, 210.8, 100)` on A4 (bleed=3, w+bleed=213). Worst overshoot ~0.8 mm. → exactly one Violation, `severity="warning"`.
    - `test_within_tolerance_passes`: frame at `(0, 0, 213.4, 100)` on A4 (overshoot ~0.4 mm ≤ 0.5 tolerance) → `[]`.

  - `class InsidePageRuleMasterSkipTests(unittest.TestCase)`:
    - `test_master_page_items_skipped`: build a doc with a master via `doc.add_master(...)`; add an overflowing frame to the master; assert rule emits nothing for the master frame.

  - `class InsidePageRuleRotationTests(unittest.TestCase)`:
    - `test_rotation_270_fits_when_unrotated_origin_outside`: replicate the plakat Impressum case — A1 page (594×841), frame `(563.69, 832.69, 377.38, 21.02, rotation_deg=270)`. Un-rotated bbox would extend to x=941 (overshoot 350 mm); rotated bbox via CCW270 spans `[563.69-21.02, 563.69] × [832.69-377.38+? ...]` — re-derive with `_rotated_bbox` directly in the test and assert NO error (rule passes).
    - `test_rotated_bbox_overshoot_is_error`: frame `(200, 0, 100, 50, rotation_deg=45)` on A4 — rotated bbox extends to x=200+100*cos45+50*sin45 ≈ 306, overshoot ≈ 93 mm → severity="error".

  - `class InsidePageRuleRegistryTests(unittest.TestCase)`:
    - `test_rule_in_registry`: assert `_find_rule("brand:inside_page")` is a `_InsidePageRule` instance.

  GREEN — implement `_InsidePageRule` in `brand_constraints.py` after the helpers from T01, BEFORE the `BRAND_CONSTRAINTS` registry:

  ```python
  # ---------------------------------------------------------------------------
  # brand:inside_page (Issue #14)
  # ---------------------------------------------------------------------------
  @dataclass(frozen=True)
  class _InsidePageRule(BrandRule):
      """Each non-master frame's rotation- and anchor-aware bbox must fit
      inside its OWNING page's ``[-bleed, w+bleed] × [-bleed, h+bleed]``.

      Severity split:
        - worst overshoot ≤ 0.5 mm → pass (within constraint-default tolerance).
        - 0.5 < worst ≤ 1.0 mm    → warning (bleed-edge nudge from float-
          imprecise Scribus SLA emit; does NOT break CI).
        - worst > 1.0 mm           → error (real overflow; CI fails unless
          template lists ``brand:inside_page`` in ``meta.yml::brand_overrides``).

      The 1.0 mm error cutoff is pragmatic: two existing zeitung frames have
      ~0.8 mm right-edge nudges from float-imprecise bleed math during SLA
      round-trip emit (e.g. ``w_mm=210.799...`` on a 210 mm page with 3 mm
      bleed); a strict 0.5 mm cutoff would surface these as errors and
      require a separate brand_overrides escape. ISSUE.md acceptance text
      reads 0.5 mm as the warning/error boundary; the 1.0 mm value is the
      planner's confirmation choice — revert if the user disagrees.

      Master-page items are skipped — masters are abstract layout grids and
      legitimately carry full-bleed background polygons. Tighten in a
      follow-up issue if master-page drift becomes a concern.
      """

      tolerance_mm: float = 0.5
      error_cutoff_mm: float = 1.0

      def check(self, primitives: list, doc) -> list:
          # We IGNORE the flat ``primitives`` arg — only doc-level iteration
          # carries ``(page, item)`` pairs. Pattern matches _Bleed3mmRule.
          violations: list = []
          for page in doc.pages:
              if page.is_master:
                  continue
              pw_mm = page.width_pt * PT_TO_MM
              ph_mm = page.height_pt * PT_TO_MM
              bleed = float(page.bleed_mm or 0)
              for item in page.items:
                  bbox = _frame_bbox_mm(item, page)
                  if bbox is None:
                      continue
                  x0, y0, x1, y1 = bbox
                  over_l = (-bleed) - x0
                  over_r = x1 - (pw_mm + bleed)
                  over_t = (-bleed) - y0
                  over_b = y1 - (ph_mm + bleed)
                  worst = max(over_l, over_r, over_t, over_b, 0.0)
                  if worst <= self.tolerance_mm:
                      continue
                  sev = "warning" if worst <= self.error_cutoff_mm else "error"
                  ident = item.anname or f"<unnamed {type(item).__name__}>"
                  loc = page.label or page.master_name or f"page#{page.own_page}"
                  violations.append(Violation(
                      severity=sev,
                      rule_id=self.id,
                      message=(
                          f"frame {ident!r} bbox "
                          f"({x0:.2f}, {y0:.2f})-({x1:.2f}, {y1:.2f}) "
                          f"exceeds page {loc!r} "
                          f"(trim {pw_mm:.1f}x{ph_mm:.1f}, bleed {bleed:.1f}); "
                          f"worst overshoot {worst:.2f}mm"
                      ),
                      targets=(ident,),
                  ))
          return violations
  ```

  Add to `BRAND_CONSTRAINTS` registry (line 370 → 419 currently). Append AFTER `_WahlkreuzColoredBgRule` entry (line 414-419), so the registry list ends with 9 entries:

  ```python
      _make_rule(
          _InsidePageRule,
          id="brand:inside_page",
          name="Frames inside page bounds",
          description="Every non-master frame's rotation-aware bbox sits "
                      "inside its own page's [-bleed, w+bleed] x [-bleed, h+bleed].",
      ),
  ```

  Update the module docstring (currently `brand_constraints.py:1-37`, "The eight rules:"):
  - Change line 3: `Eight rules` → `Nine rules`.
  - Change line 17 heading: `The eight rules:` → `The nine rules:`.
  - Append entry 9:
    ```
      9. ``brand:inside_page`` — every non-master frame's rotation- and
         anchor-aware bbox sits inside its own page's
         ``[-bleed, w+bleed] x [-bleed, h+bleed]`` (Issue #14).
    ```

  REFACTOR — confirm the rule iterates `doc.pages` (not `iter_all_primitives`),
  Master-skip is in place, severity emit is per-Violation, registration `id`
  matches the regex `^brand:[A-Za-z_0-9.]+$`.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m unittest discover -s tools/sla_lib/tests -p "test_constraints_inside_page.py" -v</automated>
  </verify>

  <done>
  - `_InsidePageRule` exists, registered in `BRAND_CONSTRAINTS` with id `brand:inside_page` (registry length now 9).
  - Module docstring header updated 8→9 and entry 9 added.
  - All test classes pass: `InsidePageRulePassTests`, `InsidePageRuleErrorTests`, `InsidePageRuleWarningTests`, `InsidePageRuleMasterSkipTests`, `InsidePageRuleRotationTests`, `InsidePageRuleRegistryTests`.
  - The full test suite still passes: `python3 -m unittest discover tools/sla_lib/tests` exits 0 EXCEPT for the two registry tests in `test_brand_constraints.py` that hardcode `len == 8` and the 8-id set — those are fixed in T03.
  - Commit: `14: feat(brand): add brand:inside_page rule with rotation-aware bbox`. Body of commit message MUST include the threshold confirmation note from the docstring (1.0 mm error cutoff; revert if user disagrees).
  </done>

  <dont>
  - Don't iterate `iter_all_primitives()` inside the rule — it doesn't carry page binding (pitfall P-12, P-22). Walk `doc.pages` directly.
  - Don't include masters yet (`if page.is_master: continue`).
  - Don't hard-code `bleed_mm = 3.0` — read `page.bleed_mm` per-page (pitfall P-4; the wahltag template uses 2 mm).
  - Don't use `page.size` or a stored `page_w_mm` — neither exists; derive from `page.width_pt * PT_TO_MM` (pitfall P-15).
  - Don't add per-frame allowlists or magic anname prefixes — `meta.yml::brand_overrides` is rule-level (pitfall P-8). Add this constraint to the rule's docstring as a caveat.
  - Don't try to mutate `self.severity` inside `check()` — `BrandRule` is `frozen=True`; emit per-Violation severity instead (pitfall P-11).
  - Don't fix the registry tests in this task — that's T03's atomic concern (so the commits stay clean).
  </dont>
</task>

<task id="T03" type="auto">
  <name>T03: 9-rule registry test update</name>
  <files>tools/sla_lib/tests/test_brand_constraints.py</files>

  <depends-on>T02</depends-on>

  <behavior>
  Update the existing `RegistryTests` class to expect 9 rules including `brand:inside_page`. Verify all existing brand-rule tests still pass (the new rule is purely additive and doesn't touch existing rule semantics).
  </behavior>

  <action>
  Edit `tools/sla_lib/tests/test_brand_constraints.py:47-63` (the `RegistryTests` class):

  ```python
  class RegistryTests(unittest.TestCase):
      def test_nine_rules_exact(self):
          self.assertEqual(len(BRAND_CONSTRAINTS), 9)

      def test_ids_are_canonical(self):
          ids = [r.id for r in BRAND_CONSTRAINTS]
          expected = {
              "brand:color_palette",
              "brand:font_family",
              "brand:line_spacing_0.9",
              "brand:hl_sl_distance_x2",
              "brand:logo_size_3M",
              "brand:text_on_green",
              "brand:bleed_3mm",
              "brand:wahlkreuz_colored_bg",
              "brand:inside_page",
          }
          self.assertEqual(set(ids), expected)
  ```

  Rename the test method `test_eight_rules_exact` → `test_nine_rules_exact` (a method-rename, not a count-bump-in-place — the rename is a discoverable signal that the count changed).

  Also update the import at lines 16-27 to add `_InsidePageRule` so future per-rule tests in this file (if any are added) can import it cleanly:

  ```python
  from sla_lib.builder.brand_constraints import (  # noqa: E402
      BRAND_CONSTRAINTS,
      BrandRule,
      _ColorPaletteRule,
      _FontFamilyRule,
      _LineSpacingRule,
      _HlSlDistanceRule,
      _LogoSize3MRule,
      _TextOnGreenRule,
      _Bleed3mmRule,
      _WahlkreuzColoredBgRule,
      _InsidePageRule,  # Issue #14
  )
  ```
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m unittest discover -s tools/sla_lib/tests -v 2>&amp;1 | tail -50</automated>
  </verify>

  <done>
  - `RegistryTests::test_nine_rules_exact` passes (registry length 9).
  - `RegistryTests::test_ids_are_canonical` passes with `brand:inside_page` in the expected set.
  - Full test suite passes: `python3 -m unittest discover tools/sla_lib/tests` exits 0.
  - Commit: `14: test(brand): update registry tests for 9-rule count`.
  </done>

  <dont>
  - Don't add new rule-specific tests for `_InsidePageRule` in this file — those live in `test_constraints_inside_page.py` (T01/T02). Keep registry-level concerns here.
  - Don't drop the rename — `test_eight_rules_exact` is misleading once the count is 9. The git history preserves the rename.
  </dont>
</task>

<task id="T04" type="auto" tdd="true">
  <name>T04: aligned_below constraint factory</name>
  <files>tools/sla_lib/builder/constraints.py, tools/sla_lib/builder/__init__.py, tools/sla_lib/tests/test_constraints.py</files>

  <depends-on>T03</depends-on>

  <behavior>
  Add `_AlignedBelowConstraint` dataclass + `aligned_below()` factory in
  `constraints.py`, re-export from package `__init__.py`. Per-template
  opt-in constraint: locks the "below frame hangs from above frame on the
  same left edge with a fixed gap" pattern.

  Argument order — IMPORTANT: `aligned_below(below, above, gap_mm,
  tolerance_mm=0.5, name="")`. First positional argument is the frame
  hanging beneath, second is the anchor above. Targets tuple stored as
  `(below_anname, above_anname)`; `_AlignedBelowConstraint.check()`
  unpacks in the same order.

  Asserts (within `tolerance_mm`, default 0.5 mm):
    - `below.y_mm == above.y_mm + above.h_mm + gap_mm`
    - `below.x_mm == above.x_mm`

  Edge cases:
    - Missing anname (either target unresolved) → single Violation via
      `_missing_violation(self.id, self.targets, missing)` with the
      framework's standard severity (`warning`).
    - Either frame rotated (`rotation_deg != 0`) → return one
      `severity="warning"` Violation with message
      `"rotated frame — aligned_below skipped"`, then early-return. Raw
      bbox math doesn't apply to rotated frames.
    - Both checks fail → ONE error Violation listing both drift entries
      in the message (matches RESEARCH skeleton's `bad` list pattern).

  Public surface: `aligned_below` joins the existing factory imports in
  `tools/sla_lib/builder/__init__.py` (currently exports `same_y`,
  `same_x`, `inside`, `distance_x`, `distance_y`, etc.).
  </behavior>

  <action>
  RED — append a new test class to `tools/sla_lib/tests/test_constraints.py`
  (the file has the existing factory-test pattern; mirror it):

  ```python
  from sla_lib.builder.constraints import (  # noqa: E402
      aligned_below, _AlignedBelowConstraint,
  )
  from sla_lib.builder.primitives import TextFrame, ImageFrame  # noqa: E402


  class AlignedBelowTests(unittest.TestCase):
      def _pair(self, below_kwargs=None, above_kwargs=None):
          above = TextFrame(x_mm=20, y_mm=10, w_mm=80, h_mm=30,
                            anname="above", **(above_kwargs or {}))
          below = ImageFrame(x_mm=20, y_mm=45, w_mm=80, h_mm=60,
                             anname="below", **(below_kwargs or {}))
          return below, above, {"above": above, "below": below}

      def test_pass_when_aligned(self):
          below, above, by = self._pair()
          # gap = 5 mm: above.y(10) + above.h(30) + 5 = 45 = below.y
          c = aligned_below(below, above, gap_mm=5)
          self.assertEqual(c.check(by), [])

      def test_x_drift_errors(self):
          below, above, by = self._pair(below_kwargs={"x_mm": 22})  # 2 mm drift
          c = aligned_below(below, above, gap_mm=5)
          vs = c.check(by)
          self.assertEqual(len(vs), 1)
          self.assertEqual(vs[0].severity, "error")
          self.assertIn("x", vs[0].message)

      def test_y_drift_errors(self):
          below, above, by = self._pair(below_kwargs={"y_mm": 50})  # gap=10, expected 5
          c = aligned_below(below, above, gap_mm=5)
          vs = c.check(by)
          self.assertEqual(len(vs), 1)
          self.assertEqual(vs[0].severity, "error")
          self.assertIn("y", vs[0].message)

      def test_within_tolerance_passes(self):
          below, above, by = self._pair(below_kwargs={"x_mm": 20.4, "y_mm": 45.4})
          c = aligned_below(below, above, gap_mm=5, tolerance_mm=0.5)
          self.assertEqual(c.check(by), [])

      def test_missing_anname_warns(self):
          _, above, by = self._pair()
          by_only_above = {"above": above}  # 'below' missing
          c = aligned_below("below", "above", gap_mm=5)
          vs = c.check(by_only_above)
          self.assertEqual(len(vs), 1)
          self.assertEqual(vs[0].severity, "warning")

      def test_rotated_frame_warn_skip(self):
          below, above, by = self._pair(above_kwargs={"rotation_deg": 90})
          c = aligned_below(below, above, gap_mm=5)
          vs = c.check(by)
          self.assertEqual(len(vs), 1)
          self.assertEqual(vs[0].severity, "warning")
          self.assertIn("rotated", vs[0].message)

      def test_string_form_accepts_annames(self):
          below, above, by = self._pair()
          c = aligned_below("below", "above", gap_mm=5)
          self.assertEqual(c.check(by), [])

      def test_factory_id_uses_autoname(self):
          below, above, _ = self._pair()
          c = aligned_below(below, above, gap_mm=5)
          self.assertTrue(c.id.startswith("aligned_below"))
          self.assertEqual(c.targets, ("below", "above"))
  ```

  GREEN — append to `tools/sla_lib/builder/constraints.py` (after
  `distance_x`, mirroring the RESEARCH skeleton verbatim):

  ```python
  @dataclass(frozen=True)
  class _AlignedBelowConstraint(Constraint):
      gap_mm: float = 0.0
      tolerance_mm: float = 0.5

      def check(self, primitives_by_anname: dict) -> list[Violation]:
          resolved, missing = _resolve(self.targets, primitives_by_anname)
          if missing:
              return [_missing_violation(self.id, self.targets, missing)]
          below, above = resolved
          if any(float(getattr(f, "rotation_deg", 0) or 0) != 0 for f in resolved):
              return [Violation(
                  severity="warning",
                  rule_id=self.id,
                  message="rotated frame — aligned_below skipped",
                  targets=self.targets,
              )]
          expected_y = above.y_mm + above.h_mm + self.gap_mm
          bad = []
          if abs(below.y_mm - expected_y) > self.tolerance_mm:
              bad.append(("y", below.y_mm, expected_y))
          if abs(below.x_mm - above.x_mm) > self.tolerance_mm:
              bad.append(("x", below.x_mm, above.x_mm))
          if not bad:
              return []
          return [Violation(
              severity="error",
              rule_id=self.id,
              message=f"aligned_below drift > {self.tolerance_mm}mm: {bad}",
              targets=self.targets,
          )]


  def aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5,
                    name: str = "") -> Constraint:
      """`below` hangs from `above`: same x, below.y == above.y + above.h + gap.

      Argument order: ``below`` first (the frame hanging beneath), then
      ``above`` (the anchor). Mirrors how an editor reads the layout
      ("the image hangs below the headline").
      """
      t = _norm((below, above))
      return _AlignedBelowConstraint(
          id=_autoname("aligned_below", t, name), targets=t, name=name,
          gap_mm=gap_mm, tolerance_mm=tolerance_mm,
      )
  ```

  Re-export — edit `tools/sla_lib/builder/__init__.py`: add
  `aligned_below` to the existing `from .constraints import (...)` block
  AND to the `__all__` tuple if one exists. Match neighbouring factory
  imports' ordering (alphabetical within the group, or grouped by
  semantic family — follow the file's existing pattern).

  REFACTOR — confirm: targets tuple order is `(below, above)` everywhere;
  string and Frame forms both work via `_norm`/`_to_anname`; rotated-frame
  early-return runs BEFORE the geometric check.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m unittest discover -s tools/sla_lib/tests -v 2>&amp;1 | tail -40</automated>
  <manual>Verify `from sla_lib.builder import aligned_below` resolves: `cd tools && python3 -c "from sla_lib.builder import aligned_below; print(aligned_below)"`.</manual>
  </verify>

  <done>
  - `_AlignedBelowConstraint` and `aligned_below()` exist in `constraints.py`.
  - `aligned_below` re-exported from `tools/sla_lib/builder/__init__.py`.
  - All 8 `AlignedBelowTests` cases pass.
  - Full suite still green.
  - Commit: `14: feat(constraints): add aligned_below factory`.
  </done>

  <dont>
  - Don't swap argument order — `(below, above)` is load-bearing for the editor's mental model. Inverting it makes the call site read backwards.
  - Don't fall back to a generic `inside`-style check for rotated frames — early-return with the warning so callers know the constraint was skipped.
  - Don't try to compute drift in pt — use `*_mm` directly; `_resolve` returns the live primitives.
  - Don't import `_AlignedBelowConstraint` into `__init__.py` — only the factory is public surface (matches `same_y`/`distance_x` pattern where the dataclass stays private).
  </dont>
</task>

<task id="T05" type="auto" tdd="true">
  <name>T05: SpreadImage block</name>
  <files>tools/sla_lib/builder/blocks.py, tools/sla_lib/builder/__init__.py, tools/sla_lib/tests/test_spread_image.py</files>

  <depends-on>T01, T02</depends-on>

  <behavior>
  New dataclass `SpreadImage` in `blocks.py` mirroring the
  `WahlkreuzSymbol` two-emit precedent (blocks.py:487-551). Emits two
  `ImageFrame`s — one per facing page — that together render one
  continuous picture across two pages, replacing the today-broken
  `(x=page_w, w=page_w)` overflow pattern.

  Methods:
    - `emit() -> tuple[ImageFrame, ImageFrame]` — build the two frames.
    - `place(page_left, page_right) -> tuple[ImageFrame, ImageFrame]` —
      `emit()` + `page_left.add(left)` + `page_right.add(right)`, return
      both for further use.

  Anname pattern: if `base_anname` is set, frames are named
  `f"{base} · left"` and `f"{base} · right"` (middle-dot ' · '). If
  `base_anname` is empty, both anname fields stay empty.

  Critical fields:
    - Right half MUST use `local_offset_mm=(-page_w_mm, 0)` — NEGATIVE x
      (pitfall P-30 / P-3): scrolls the source image left so the right
      half of the picture shows in the right page's frame. Sign-flipping
      is the highest-risk bug.
    - Both halves MUST hard-pin `scale_type=0` (free / aspect-locked).
      Default `scale_type=1` is auto-fit, which fits each half
      independently and visually breaks the spread (pitfall P-30).
    - Both halves sit at `x_mm=0` on their respective pages — by
      construction `inside_page`-clean.

  Re-export: `SpreadImage` is accessed via `blocks.SpreadImage`; add to
  `__init__.py` if blocks classes are individually re-exported (check the
  existing pattern — `WahlkreuzSymbol`/`FoldedPanel` placement is the
  reference).
  </behavior>

  <action>
  RED — write tests first in NEW file
  `tools/sla_lib/tests/test_spread_image.py`:

  ```python
  """Tests for SpreadImage block (Issue #14)."""
  from __future__ import annotations
  import sys
  import unittest
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(ROOT / "tools"))

  from sla_lib.builder import Document  # noqa: E402
  from sla_lib.builder.blocks import SpreadImage  # noqa: E402
  from sla_lib.builder.primitives import ImageFrame  # noqa: E402
  from sla_lib.builder.brand_constraints import _frame_bbox_mm  # noqa: E402


  class SpreadImageEmitTests(unittest.TestCase):
      def test_emit_returns_two_image_frames(self):
          si = SpreadImage(image="img/cover.jpg",
                           page_w_mm=210, page_h_mm=297, h_mm=297,
                           base_anname="P9 Spread")
          left, right = si.emit()
          self.assertIsInstance(left, ImageFrame)
          self.assertIsInstance(right, ImageFrame)

      def test_anname_pattern(self):
          si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297,
                           h_mm=297, base_anname="Cover")
          left, right = si.emit()
          self.assertEqual(left.anname, "Cover · left")
          self.assertEqual(right.anname, "Cover · right")

      def test_anname_empty_when_no_base(self):
          si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297)
          left, right = si.emit()
          self.assertEqual(left.anname, "")
          self.assertEqual(right.anname, "")

      def test_right_half_local_offset_is_negative_x(self):
          si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297)
          left, right = si.emit()
          self.assertEqual(left.local_offset_mm, (0.0, 0.0))
          self.assertEqual(right.local_offset_mm, (-210.0, 0.0))

      def test_scale_type_pinned_to_zero(self):
          si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297)
          left, right = si.emit()
          self.assertEqual(left.scale_type, 0)
          self.assertEqual(right.scale_type, 0)

      def test_both_halves_inside_page_clean(self):
          # Build a tiny doc with two A4 pages, place the spread, run the
          # bbox helper to confirm both frames sit inside [-bleed, w+bleed].
          doc = Document(facing_pages=True)
          pl = doc.add_page(width_mm=210, height_mm=297, bleed_mm=3, label="L")
          pr = doc.add_page(width_mm=210, height_mm=297, bleed_mm=3, label="R")
          si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297,
                           h_mm=297, base_anname="P9 Spread")
          l, r = si.place(pl, pr)
          for frame, page in ((l, pl), (r, pr)):
              x0, y0, x1, y1 = _frame_bbox_mm(frame, page)
              self.assertGreaterEqual(x0, -3.0)
              self.assertLessEqual(x1, 213.0)
              self.assertGreaterEqual(y0, -3.0)
              self.assertLessEqual(y1, 300.0)

      def test_place_appends_to_pages(self):
          doc = Document(facing_pages=True)
          pl = doc.add_page(width_mm=210, height_mm=297, bleed_mm=3)
          pr = doc.add_page(width_mm=210, height_mm=297, bleed_mm=3)
          before_l, before_r = len(pl.items), len(pr.items)
          SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297).place(pl, pr)
          self.assertEqual(len(pl.items), before_l + 1)
          self.assertEqual(len(pr.items), before_r + 1)
  ```

  Note: `Document.add_page` signature — verify by reading
  `tools/sla_lib/builder/document.py` if the kwargs above don't match.
  Adjust the test's page-construction calls to whatever the real API is
  (the existing `test_blocks.py` will show the canonical pattern).

  GREEN — append `SpreadImage` to `tools/sla_lib/builder/blocks.py`
  near the other two-page-emit blocks (after `WahlkreuzSymbol` /
  `FoldedPanel`). Use the RESEARCH skeleton verbatim:

  ```python
  @dataclass
  class SpreadImage:
      """Two ImageFrames, one per facing page, sharing one source image.

      Right half uses ``local_offset_mm=(-page_w_mm, 0)`` so the source
      image "scrolls" left and the right half shows the right half of the
      picture. Both frames are ``inside_page``-clean by construction
      (each sits at ``x=0`` on its own page).

      ``scale_type`` is hard-pinned to 0 (free / aspect-locked); the
      default 1 (auto-fit) breaks the spread because each half auto-fits
      independently.
      """
      image: str
      page_w_mm: float
      page_h_mm: float
      h_mm: float
      y_mm: float = 0.0
      base_anname: str = ""
      scale_type: int = 0
      local_scale: tuple[float, float] = (1.0, 1.0)

      def emit(self) -> tuple[ImageFrame, ImageFrame]:
          left = ImageFrame(
              x_mm=0.0, y_mm=self.y_mm,
              w_mm=self.page_w_mm, h_mm=self.h_mm,
              image=self.image,
              local_scale=self.local_scale,
              local_offset_mm=(0.0, 0.0),
              scale_type=self.scale_type,
              anname=f"{self.base_anname} · left" if self.base_anname else "",
          )
          right = ImageFrame(
              x_mm=0.0, y_mm=self.y_mm,
              w_mm=self.page_w_mm, h_mm=self.h_mm,
              image=self.image,
              local_scale=self.local_scale,
              local_offset_mm=(-self.page_w_mm, 0.0),
              scale_type=self.scale_type,
              anname=f"{self.base_anname} · right" if self.base_anname else "",
          )
          return left, right

      def place(self, page_left, page_right) -> tuple[ImageFrame, ImageFrame]:
          """Convenience: emit + add to two pages, return the frames."""
          l, r = self.emit()
          page_left.add(l)
          page_right.add(r)
          return l, r
  ```

  Re-export from `tools/sla_lib/builder/__init__.py` next to the other
  block re-exports (`WahlkreuzSymbol`, `FoldedPanel`, etc.).

  REFACTOR — visually scan `local_offset_mm=(-self.page_w_mm, 0.0)` to
  confirm the negative sign is present; confirm `scale_type=self.scale_type`
  with class default `0`.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m unittest discover -s tools/sla_lib/tests -p "test_spread_image.py" -v</automated>
  </verify>

  <done>
  - `SpreadImage` class exists in `blocks.py` with `emit()` and `place()`.
  - Re-exported from `__init__.py`.
  - All 7 `SpreadImageEmitTests` cases pass.
  - Full suite still green.
  - Commit: `14: feat(blocks): add SpreadImage builder block`.
  </done>

  <dont>
  - Don't drop the negative sign on `local_offset_mm=(-self.page_w_mm, 0.0)` (pitfall P-3).
  - Don't let `scale_type` default to 1 — hard-pin 0 (pitfall P-30).
  - Don't add a "single-page" emit variant — the `WahlkreuzSymbol` precedent always emits two frames; consumers add to whichever pages they need.
  - Don't change the anname separator from ` · ` (middle-dot, U+00B7, with surrounding spaces) — `WahlkreuzSymbol` uses the same convention; downstream tools may filter on it.
  </dont>
</task>

<task id="T06" type="auto">
  <name>T06: zeitung brand_override skip for inside_page</name>
  <files>templates/zeitung-a4-grun/meta.yml</files>

  <depends-on>T02</depends-on>

  <behavior>
  Append a single entry to the EXISTING `brand_overrides` list in
  `templates/zeitung-a4-grun/meta.yml`:

  ```yaml
    - id: brand:inside_page
      reason: >-
        Two frames (P9 Spread at build.py:1802-1811, unnamed page-12
        image at 2061-2071) overflow the right page edge by >200 mm —
        tracked in issue #16. This override silences the rule globally
        for zeitung until #16 lands the SpreadImage migration.
  ```

  Find the right list element under `brand_overrides:` (currently
  contains only `brand:line_spacing_0.9` at lines 22-30). Do NOT
  re-author the rest of the file. Use Edit, not Write.

  After the edit, the rule is enabled at structural-check time AND
  silenced for zeitung — so `python3 -m sla_lib.builder.structural_check
  zeitung-a4-grun` MUST exit 0. The `skipped_brand_rules` list will
  contain `brand:inside_page` (visible in the report output).
  </behavior>

  <action>
  Use Edit on `templates/zeitung-a4-grun/meta.yml`. Locate the existing
  `brand_overrides:` block (line ~21-30 — `id: brand:line_spacing_0.9`
  with its `reason:`) and append the new entry as a sibling list item.
  Maintain YAML indentation (2-space). Use `>-` block scalar to match
  the existing reason's style.

  Verify by running `structural_check zeitung-a4-grun` and confirming
  exit 0 with `brand:inside_page` listed under skipped rules. The
  command's output already prints skipped rules (per
  `structural_check.py` orchestrator flow at the `skip_ids` step in the
  interfaces block).
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m sla_lib.builder.structural_check zeitung-a4-grun; echo "exit=$?"</automated>
  <manual>Confirm the report output mentions `brand:inside_page` under skipped rules.</manual>
  </verify>

  <done>
  - `meta.yml` has TWO `brand_overrides` entries: existing `brand:line_spacing_0.9`, new `brand:inside_page`.
  - `structural_check zeitung-a4-grun` exits 0.
  - Existing `brand:line_spacing_0.9` entry is byte-identical (no incidental reformatting).
  - Commit: `14: chore(zeitung): brand_overrides skip for inside_page (see #16)`.
  </done>

  <dont>
  - Don't rewrite the file — use Edit to append the single new list item only. The `original_sla` / `previews_for_sla` / `ci_overrides` blocks must stay byte-identical.
  - Don't add a per-frame allowlist — the override mechanism is rule-level only (pitfall P-8).
  - Don't try to "fix" the two known overflows — that's #16's scope. This issue silences them via override.
  - Don't drop the `reason:` field — `meta_schema.py` may validate that brand_overrides entries carry a reason; the existing entry sets that precedent.
  </dont>
</task>

<task id="T07" type="auto">
  <name>T07: --all green-bar verification + tolerance investigation gate</name>
  <files>(verification gate; no code changes by default)</files>

  <depends-on>T01, T02, T03, T04, T05, T06</depends-on>

  <behavior>
  Run `python3 -m sla_lib.builder.structural_check --all` against every
  template in `templates/`. Confirm exit 0. Report the summary line:
  "T07: 0 errors, N warnings, M skipped rules".

  Decision tree if a template OTHER than zeitung surfaces an
  `inside_page` error or a >0.5 mm warning:

  1. **Real bug** — frame genuinely overflows the page (e.g. another
     spread image at `(x=page_w, w=page_w)`). Action: file a follow-up
     issue, add a `brand_overrides` entry to that template's `meta.yml`
     referencing the new issue id (mirror T06's pattern). Do NOT fix the
     bug in this issue's PR.

  2. **Expected 0.8 mm bleed-edge nudge** (already covered by zeitung's
     two known cases — `x=210.799...` on a 210 mm A4 page with 3 mm
     bleed). Action: none — these surface as warnings (not errors) and
     the override + 1.0 mm cutoff handle them.

  3. **Tolerance miscalibration** — false positive at e.g. 0.51 mm
     overshoot from float-imprecise math that should pass cleanly.
     Action: bump the warning threshold from 0.5 mm to a documented
     value (e.g. 0.6 mm), keep the 1.0 mm error cutoff, and add a
     paragraph to `_InsidePageRule`'s docstring citing the specific
     template + frame that motivated the bump.

  This task is a verification gate, not a code task. The executor MUST
  report which branch of the decision tree applied. If branch (1)
  triggers, the executor adds the override AND notes the new follow-up
  issue id in this task's commit message.
  </behavior>

  <action>
  Step 1 — run the full sweep:

  ```bash
  cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility
  python3 -m sla_lib.builder.structural_check --all
  echo "exit=$?"
  ```

  Step 2 — also run the GitHub Actions equivalent locally to surface
  any pages.yml-specific failure mode (per pages.yml:141-147 with
  `set -euo pipefail`):

  ```bash
  cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility
  set -euo pipefail
  python3 -m sla_lib.builder.structural_check --all
  ```

  Step 3 — categorise EACH inside_page warning/error per the decision
  tree above. Most likely path: 0 errors, 2 warnings (zeitung's two
  bleed-edge nudges show as warnings on pages 12+14, NOT silenced
  because the override is rule-level — but warnings don't fail CI).

  Step 4 — Wait. Re-read step 3: the override silences the WHOLE rule
  for zeitung, so the two nudges + the two real overflows ALL get
  reported as `skipped_brand_rules`, not as warnings. Expected output:
  "0 errors, 0 inside_page warnings (zeitung skipped via override),
  K other warnings (pre-existing)". Confirm this matches reality.

  Step 5 — if any non-zeitung template surfaces an inside_page error,
  run the decision tree above and act on the matching branch BEFORE
  declaring T07 done.

  No code changes in the default path (all branches except 1+3 are
  no-ops). If branch 1 fires: edit the affected template's `meta.yml`
  (mirror T06). If branch 3 fires: edit `_InsidePageRule`'s docstring
  + the `tolerance_mm` default in `brand_constraints.py`.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; set -euo pipefail; python3 -m sla_lib.builder.structural_check --all</automated>
  <manual>Report: "T07: structural_check --all exit 0; inside_page errors=0; inside_page warnings=N; skipped_brand_rules contains brand:inside_page for zeitung-a4-grun; decision-tree branch X applied."</manual>
  </verify>

  <done>
  - `structural_check --all` exits 0 under `set -euo pipefail`.
  - Zero `inside_page` errors across all templates.
  - Decision-tree branch outcome reported in the executor's status message.
  - If a follow-up override or tolerance bump was applied, that change is committed under `14: ci(structural): handle inside_page surface across all templates` (or absorbed into T06's commit if the override is for zeitung; otherwise its own commit).
  - If no code changed, no commit needed for T07 — the gate is a verification-only step. Note in the executor report: "T07: verification-only, no commit".
  </done>

  <dont>
  - Don't force-pass by adding overrides to every template — only add an override if the decision tree's branch (1) explicitly applies. Wide overrides defeat the rule's purpose.
  - Don't fix unrelated CI failures discovered along the way — note them as follow-up issues. T07 is scoped to inside_page surface.
  - Don't fix the two zeitung overflows themselves — issue #16's scope.
  </dont>
</task>

<task id="T08" type="auto">
  <name>T08: SCHEMA.md catalogue entries for the three new pieces</name>
  <files>templates/_specs/SCHEMA.md</files>

  <depends-on>T02, T04, T05</depends-on>

  <behavior>
  Add catalogue entries to `templates/_specs/SCHEMA.md` §12 (the
  factory-list section). Three new rows:

    - `brand:inside_page` — global brand rule; brand-overrides skippable.
    - `aligned_below(below, above, gap_mm, tolerance_mm=0.5)` — per-template
      free-form constraint factory.
    - `SpreadImage(image, page_w_mm, page_h_mm, h_mm, ...)` — block
      utility emitting two `ImageFrame`s for a continuous-across-two-pages
      picture.

  Also bump every "8 Regeln" / "eight rules" / "acht Regeln" reference
  in the same file from 8 to 9. ISSUE.md says §6, but the actual
  factory list is §12 (per RESEARCH pitfall #6); do NOT chase the wrong
  section number.
  </behavior>

  <action>
  Step 1 — read the file's current state to find the EXACT line numbers
  for §12 and the brand-rule count line:

  ```bash
  grep -n "^## " templates/_specs/SCHEMA.md            # section headers
  grep -n "8 Regeln\|eight rules\|acht Regeln\|brand:" templates/_specs/SCHEMA.md
  ```

  Per RESEARCH: §12 is at ~line 484, factory list at ~lines 493-495,
  "8 Regeln" at ~line 510. Verify these by Reading the file before
  editing.

  Step 2 — Edit §12 to append three rows. Match the existing factory
  list's row format (likely a Markdown table or bulleted list — read
  before composing). For the bulleted-list variant:

  ```
  - `aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="")` —
    `below` hangs from `above` on the same x axis with the given gap.
    Per-template free-form constraint (Issue #14).
  - `SpreadImage(image, page_w_mm, page_h_mm, h_mm, y_mm=0,
    base_anname="", scale_type=0, local_scale=(1,1))` — emits two
    `ImageFrame`s for a continuous-across-two-pages picture; right half
    uses `local_offset_mm=(-page_w_mm, 0)`. Block utility (Issue #14).
  ```

  Step 3 — under the brand-rule list (or the rule-count line), add:

  ```
  - `brand:inside_page` — every non-master frame's rotation- and
    anchor-aware bbox sits inside its own page's
    `[-bleed, w+bleed] × [-bleed, h+bleed]`. Skippable via
    `meta.yml::brand_overrides` (Issue #14).
  ```

  Step 4 — bump every "8 Regeln" / "eight rules" mention to "9 Regeln" /
  "nine rules". Use grep before AND after to confirm zero residual
  references to "8" or "eight" in the brand-rule context.

  ```bash
  grep -n "Regeln\|rules" templates/_specs/SCHEMA.md   # confirm 9, not 8
  ```
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; grep -nE "brand:inside_page|aligned_below|SpreadImage|9 Regeln|nine rules" templates/_specs/SCHEMA.md</automated>
  <manual>Re-Read §12 to confirm rows render correctly, no broken Markdown tables.</manual>
  </verify>

  <done>
  - SCHEMA.md §12 contains rows for `brand:inside_page`, `aligned_below`, `SpreadImage`.
  - Every "8 Regeln" / "eight rules" reference bumped to 9.
  - Commit: `14: docs(schema): add inside_page, aligned_below, SpreadImage to SCHEMA §12`.
  </done>

  <dont>
  - Don't trust ISSUE.md's "§6" reference — pitfall P-6 says the actual section is §12.
  - Don't add code examples beyond the function signature — SCHEMA.md is a catalogue, not a tutorial. The worked example for SpreadImage lives in SPEC-WRITING-GUIDE.md (T09).
  - Don't reflow neighbouring rows — append-only.
  </dont>
</task>

<task id="T09" type="auto">
  <name>T09: SPEC-WRITING-GUIDE.md catalogue + SpreadImage migration recipe</name>
  <files>shared/brand/SPEC-WRITING-GUIDE.md</files>

  <depends-on>T08</depends-on>

  <behavior>
  Add catalogue rows to `shared/brand/SPEC-WRITING-GUIDE.md` §5 (the
  constraint-factory catalogue) and §8 (the brand-rule catalogue), AND a
  short worked example showing the migration from
  `ImageFrame(x=page_w, w=page_w)` (broken) to `SpreadImage(...)`
  (correct). Per RESEARCH pitfall P-6: actual sections are §5 and §8,
  NOT the §4 reference in ISSUE.md.
  </behavior>

  <action>
  Step 1 — verify exact section locations:

  ```bash
  grep -n "^## " shared/brand/SPEC-WRITING-GUIDE.md
  grep -n "aligned_below\|SpreadImage\|inside_page\|brand:" shared/brand/SPEC-WRITING-GUIDE.md
  ```

  Per RESEARCH: §5 at ~line 154, §8 at ~line 268. Read the file to
  confirm the row format used in each section (table vs. bulleted list).

  Step 2 — append to §5 (constraint-factory catalogue):

  ```
  - `aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="")` —
    locks the "image hangs below the headline on the same left edge"
    pattern. Per-template free-form constraint. Targets order:
    `(below, above)` — first arg is the frame hanging beneath. Issue #14.
  ```

  Step 3 — append to §8 (brand-rule catalogue):

  ```
  - `brand:inside_page` — every non-master frame's rotation- and
    anchor-aware bbox sits inside its own page's
    `[-bleed, w+bleed] × [-bleed, h+bleed]`. Severity: warning at
    >0.5 mm overshoot, error at >1.0 mm. Skippable via
    `meta.yml::brand_overrides` (rule-level). Issue #14.
  ```

  Step 4 — add a new subsection (or extend an existing "blocks /
  composites" section) with the SpreadImage migration recipe:

  ```
  ### Spreading an image across two facing pages

  ❌ Broken — overflows the right edge of the left page by one full
  page width:

      ImageFrame(x_mm=0, y_mm=0, w_mm=2*page_w, h_mm=page_h,
                 image="cover.jpg", anname="P9 Spread")

  ✅ Correct — emits two `inside_page`-clean frames, right half scrolls
  the source image left:

      from sla_lib.builder.blocks import SpreadImage

      spread = SpreadImage(image="cover.jpg",
                           page_w_mm=210, page_h_mm=297, h_mm=297,
                           base_anname="P9 Spread")
      spread.place(page_left, page_right)
      # → frames named "P9 Spread · left" and "P9 Spread · right"
      # → right half uses local_offset_mm=(-210, 0); scale_type=0 pinned

  See `tools/sla_lib/builder/blocks.py::SpreadImage` for the full
  signature. Issue #14 / #16 (zeitung migration).
  ```

  Step 5 — confirm no other "8 / eight" rule-count references in this
  guide. If present, bump to 9.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; grep -nE "aligned_below|SpreadImage|brand:inside_page" shared/brand/SPEC-WRITING-GUIDE.md</automated>
  <manual>Re-Read §5 and §8 plus the new migration recipe; confirm Markdown renders.</manual>
  </verify>

  <done>
  - SPEC-WRITING-GUIDE.md §5 has the `aligned_below` row.
  - SPEC-WRITING-GUIDE.md §8 has the `brand:inside_page` row.
  - A worked-example subsection demonstrates the
    `ImageFrame(x=page_w, w=page_w)` → `SpreadImage(...)` migration.
  - Any rule-count references bumped 8→9.
  - Commit: `14: docs(brand): add SpreadImage migration recipe to SPEC-WRITING-GUIDE`.
  </done>

  <dont>
  - Don't trust ISSUE.md's "§4" — RESEARCH P-6 says §5 and §8 are the right sections.
  - Don't elide the negative-x note in the recipe — it's the highest-risk pitfall (P-3 / P-30).
  - Don't add the recipe inside §5/§8 themselves — they're catalogues; the recipe is its own subsection.
  </dont>
</task>

<task id="T10" type="auto" tdd="true">
  <name>T10: regression test for the two zeitung overflows</name>
  <files>tools/sla_lib/tests/test_zeitung_overflow.py</files>

  <depends-on>T02, T06</depends-on>

  <behavior>
  NEW test file mechanically anchoring the issue's "exactly two
  inside_page errors today" acceptance criterion. Two tests:

  1. `test_inside_page_finds_the_two_overflows_without_override` —
     temporarily strip the `brand:inside_page` entry from zeitung's
     `meta.yml` overrides (in-memory; do NOT mutate the file on disk),
     run `_InsidePageRule.check()` on the loaded zeitung doc, assert
     EXACTLY 2 errors with `rule_id == "brand:inside_page"`. The two
     known offenders' annames are `"P9 Spread"` (line 1802-1811) and
     `""` (the unnamed full-A4 image at line 2061-2071) — assert the
     error message for the unnamed one contains `"<unnamed ImageFrame>"`
     (the rule's fallback ident from T02).

  2. `test_inside_page_passes_with_override` — with zeitung's
     `meta.yml` in production state (i.e. `brand:inside_page` IS in
     the override list, per T06), run the full
     `structural_check zeitung-a4-grun` and assert 0 errors and the
     report's `skipped_brand_rules` contains `brand:inside_page`.

  Both tests pin the acceptance criterion mechanically — if a future
  refactor re-introduces a third overflow OR fixes the two known ones
  silently, the regression test breaks.
  </behavior>

  <action>
  RED — write tests first in NEW file
  `tools/sla_lib/tests/test_zeitung_overflow.py`:

  ```python
  """Regression tests for the two known zeitung inside_page overflows.

  Anchors the Issue #14 acceptance criterion: today there are EXACTLY
  two frames in templates/zeitung-a4-grun/build.py whose bbox overflows
  the right page edge by >200 mm — `P9 Spread` (build.py:1802-1811) and
  an unnamed full-A4 image (build.py:2061-2071). #16 will fix both via
  SpreadImage migration; until then they are silenced via
  meta.yml::brand_overrides.
  """
  from __future__ import annotations
  import importlib.util
  import sys
  import unittest
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(ROOT / "tools"))

  from sla_lib.builder.brand_constraints import _InsidePageRule  # noqa: E402


  def _load_zeitung_doc():
      """Load templates/zeitung-a4-grun/build.py and return its built doc."""
      build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
      spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      return mod.build_doc()


  class ZeitungInsidePageRegressionTests(unittest.TestCase):
      def test_inside_page_finds_the_two_overflows_without_override(self):
          doc = _load_zeitung_doc()
          # Construct the rule directly — bypasses meta.yml override entirely.
          rule = _InsidePageRule(
              id="brand:inside_page",
              name="Frames inside page bounds",
              description="(test instance — bypasses brand_overrides)",
          )
          violations = rule.check(list(doc.iter_all_primitives()), doc)
          errors = [v for v in violations if v.severity == "error"]
          self.assertEqual(
              len(errors), 2,
              msg=f"expected exactly 2 inside_page errors, got {len(errors)}: "
                  f"{[v.message for v in errors]}",
          )
          targets = sorted(t for v in errors for t in v.targets)
          self.assertIn("P9 Spread", targets)
          # The unnamed page-12 image surfaces as the fallback ident:
          self.assertTrue(
              any("<unnamed ImageFrame>" in v.message for v in errors),
              msg=f"expected unnamed-ImageFrame error in {[v.message for v in errors]}",
          )

      def test_inside_page_passes_with_override(self):
          # Use the production structural_check pipeline (override IS active).
          from sla_lib.builder import structural_check as sc
          # Whatever the orchestrator's public API is — likely a function
          # returning a Report with .errors and .skipped_brand_rules.
          # If the API is process-only (no in-Python entry point), shell
          # out to `python -m sla_lib.builder.structural_check zeitung-a4-grun`
          # via subprocess and assert exit 0 + parse the report.
          report = sc.run_template("zeitung-a4-grun", root=ROOT)
          self.assertEqual(
              [e for e in report.violations if e.severity == "error"
               and e.rule_id == "brand:inside_page"],
              [],
          )
          self.assertIn(
              "brand:inside_page",
              {s.id for s in report.skipped_brand_rules},
          )
  ```

  Note on `structural_check.run_template`: verify the actual entry-point
  name by reading `tools/sla_lib/builder/structural_check.py`. If no
  in-Python entry exists, switch the second test to a `subprocess.run`
  variant that asserts `returncode == 0` and greps stdout for
  `brand:inside_page` under a "skipped" header.

  GREEN — these are integration tests; once T01-T06 are merged, both
  should pass without further code. If the first test reports a third
  error, T07's decision tree applies (most likely: a real bug — file a
  follow-up issue and override per branch 1). If the second test fails,
  T06 is incomplete.

  REFACTOR — confirm the test file is self-contained (no fixtures
  leaking into other test files), docstring is accurate, both anname
  references match build.py source-of-truth.
  </action>

  <verify>
  <automated>cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility &amp;&amp; python3 -m unittest discover -s tools/sla_lib/tests -p "test_zeitung_overflow.py" -v</automated>
  </verify>

  <done>
  - Both `ZeitungInsidePageRegressionTests` cases pass.
  - Full suite still green: `python3 -m unittest discover tools/sla_lib/tests` exits 0.
  - Commit: `14: test(zeitung): regression for the two known overflow frames`.
  </done>

  <dont>
  - Don't mutate `meta.yml` on disk in the first test — load it as data and strip the entry in memory, OR construct the `_InsidePageRule` directly (recommended; the latter completely bypasses meta.yml and tests rule semantics in isolation).
  - Don't hard-code line numbers in assertions — assert by anname (or `<unnamed ImageFrame>` message fragment), not by source line. The line numbers will drift.
  - Don't assert the EXACT message string — assert message fragments (e.g. `"P9 Spread"`, `"exceeds page"`, `"<unnamed ImageFrame>"`). Full-string matches are fragile.
  - Don't add a third "fix the bug" test — that's #16's regression to write, not this issue's.
  </dont>
</task>

</tasks>

<verification>
After all tasks, run final checks:
- `python3 -m unittest discover tools/sla_lib/tests -v` — full unittest suite, exit 0.
- `cd /root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility && set -euo pipefail; python3 -m sla_lib.builder.structural_check --all` — every template still passes structural check, exit 0.
- `grep -rn "PageBackground(" templates/` — sanity check pitfall P-20 (no template uses the no-arg form that would default to 220×310 mm and overflow A6). Expected: every match uses `.for_page(...)`.
- `grep -nE "8 Regeln|eight rules|acht Regeln" templates/_specs/SCHEMA.md shared/brand/SPEC-WRITING-GUIDE.md` — should be empty after T08+T09.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:

- ✅ `brand:inside_page` exists as a `BrandRule` with rotation- and anchor-aware bbox math (T01+T02).
- ✅ Severity split: warning at 0.5–1.0 mm overshoot, error at >1.0 mm (T02; documented confirmation of 1.0 mm vs. ISSUE's 0.5 mm in commit message).
- ✅ `aligned_below(below, above, gap_mm, ...)` factory exists in `constraints.py`, re-exported from `__init__.py` (T04).
- ✅ `SpreadImage` block exists in `blocks.py` with `emit()` + `place()`, right half uses `local_offset_mm=(-page_w_mm, 0)`, `scale_type=0` pinned (T05).
- ✅ `BRAND_CONSTRAINTS` registry has 9 entries; tests updated (T02 + T03).
- ✅ Zeitung's `meta.yml` skips `brand:inside_page` with a `reason:` referencing #16 (T06).
- ✅ `structural_check --all` exits 0 across every template under `set -euo pipefail` (T07).
- ✅ The TWO known zeitung overflows are mechanically detected by the rule when the override is bypassed; mechanically silenced when the override is active (T10).
- ✅ SCHEMA.md §12 + SPEC-WRITING-GUIDE.md §5/§8 catalogue the three new pieces; SPEC-WRITING-GUIDE.md has the `ImageFrame` → `SpreadImage` migration recipe (T08 + T09).
- ✅ All 10 commits on a single feature branch, single PR (per locked atomic-PR decision).
</success_criteria>

## Risks and verification

- **Render-verify (rotation pivot, CCW-positive math).** The rotation-pivot convention (top-left corner of un-rotated frame, CCW positive) is *deduced* from the plakat-a1-hochformat ROT=270 case fitting the page only under that convention. Before merging the PR, open the emitted `templates/plakat-a1-hochformat` SLA in Scribus once and visually confirm the rotated Impressum frame lands where `_rotated_bbox` predicts. If the convention is actually CW-positive (or center-pivot), `_InsidePageRule` will silently mis-report rotated-frame bboxes. The executor does NOT need to run Scribus — this is a human verification gate before merge. Severity: medium (rare but high-impact regression class).
- **`grep -rn "PageBackground(" templates/` (pitfall P-20).** `PageBackground()` with no args defaults to a 220×310 mm polygon — would overflow A6 by ~118 mm and fire the new rule. Production templates all use `.for_page(w, h)` so today nothing breaks; the grep is a 10-second sanity check before merge. Add to the post-T07 verification block.
- **Exact-2-errors snapshot expectation.** The acceptance criterion "exactly two `brand:inside_page` errors today" is anchored mechanically by T10's first test case (overflow detection with override bypassed) AND verified at T07 (override active, 0 errors). Both must hold for the PR to ship. If T10 reports >2 errors, branch 1 of T07's decision tree applies — file a follow-up, add an override, do NOT touch the third frame in this PR.
- **Decision tree for T07.** Already enumerated in T07's `<behavior>`/`<action>`. Branch 1 = real bug → follow-up issue + override. Branch 2 = expected nudge → no action. Branch 3 = tolerance miscalibration → docstring-justified bump of the warning threshold.
- **Atomic-PR reminder.** T01-T10 ship together as ~10 commits on a single feature branch, single PR. `pages.yml:141-147` runs `set -euo pipefail` around `structural_check --all`; partial PRs (e.g. T02 without T06) break CI on push because the rule fires errors that no override yet silences. Do NOT push intermediate commits to a tracking branch that triggers CI before T06.
