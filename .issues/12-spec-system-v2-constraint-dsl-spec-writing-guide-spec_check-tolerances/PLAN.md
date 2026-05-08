# Plan: Spec-System v2 — Constraint-DSL + Spec-Writing-Guide + spec_check tolerances

<objective>
What this plan accomplishes: deliver "Spec-System v2" — a code-first Constraint-DSL
(composite blocks + free-form predicates + brand-rule auto-application) with a
`structural_check` orchestrator, refactor all 8 templates onto a uniform
`build_doc()` import contract, calibrate the API on `themen-plakat-a3-quer` as the
Phase 3 vorzeige, fan out to the remaining 7 templates while keeping SLA bytes
byte-stable, tune `tools/spec_check.py` to a 0.5mm tolerance with severity buckets,
and author the long-form `shared/brand/SPEC-WRITING-GUIDE.md` plus a SCHEMA.md update.

Why it matters: today, structural template constraints (alignment, symmetry,
hierarchy, brand-CI rules) live as prose only — drift goes undetected until visual
review. This plan makes structural correctness deterministic in CI, captures the
hard-won spec-authoring knowledge from issues #10/#11/#13 in a guide, and removes
the 0.1mm spec_check noise from build-loop refinements.

Scope (in): DSL modules (composites, constraints, brand_constraints, structural_check,
`Document.iter_all_primitives()`); `build_doc()` contract on all 8 templates;
vorzeige refactor of themen-plakat; brand-drift discovery + meta.yml overrides;
SHA-stable refactor of remaining 7 templates; spec_check tolerance change; SCHEMA.md
update; SPEC-WRITING-GUIDE.md (~2500 German words); CI wiring.

Scope (out): constraint solver (kiwisolver/z3 — predicates suffice); auto-fix mode;
constraint inheritance; visual linting over rendered PNGs; per-template tolerance
overrides; brand-rule plugin/decorator registry; performance optimization beyond
the <30s CI total budget.
</objective>

<context>
Issue: @.issues/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/ISSUE.md
Decisions: @.issues/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/CONTEXT.md
Research: @.issues/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/RESEARCH.md
Codebase research: @.issues/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/research/codebase.md
Ecosystem research: @.issues/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/research/ecosystem.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

# tools/sla_lib/builder/__init__.py — current re-exports (additive only)
from .document import Document, Page
from .ci import Color, Style, load_ci
from .primitives import (
    TextFrame, ImageFrame, Polygon, Line, Anchor, Run, pack_inline_image,
)
from .styles import DocumentLayer, ParaStyle, CharStyle, SoftShadow
from .brand import Brand
from . import blocks
# NEW exports added by this plan:
#   composites.py:  AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
#                   GridSpec, GridCell, HierarchyBlock
#   constraints.py: same_y, same_x, same_size, mirrored_x, mirrored_y, inside,
#                   equal_gap, hierarchy, same_style, distance_y, distance_x,
#                   Constraint, Violation
#   brand_constraints.py: BRAND_CONSTRAINTS (list), BrandRule


# tools/sla_lib/builder/primitives.py (existing, unchanged)
@dataclass
class _Frame:
    x_mm: float; y_mm: float; w_mm: float; h_mm: float
    anname: str = ""
    # ... + Anchor, rotation_deg, layer, etc; see primitives.py:433-487

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""
    fcolor: str = ""
    # ... see primitives.py:540-744
    def link_to(self, other) -> None: ...

@dataclass
class ImageFrame(_Frame):
    src: str | None = None
    # ... see primitives.py:764-841

@dataclass
class Polygon(_Frame):
    fill: str = ""
    line_color: str = ""
    shape: str = "rectangle"


# tools/sla_lib/builder/document.py — Page.add() unwraps emit() immediately
class Page:
    items: list  # flat list of post-emit primitives
    def add(self, item) -> "Page":
        if hasattr(item, "emit"):
            for p in item.emit():
                self.items.append(p)
        else:
            self.items.append(item)
        return self

class Document:
    masters: list[Page]
    pages: list[Page]
    _extra_colors: dict
    def add_page(self, ...) -> Page: ...
    def add_master(self, ...) -> Page: ...
    def save(self, path) -> None: ...
    # NEW additive (Task 1):
    def iter_all_primitives(self) -> Iterable: ...


# tools/sla_lib/builder/blocks.py — existing pattern (do not modify)
@dataclass
class PageBackground:
    def emit(self) -> Iterable: ...

@dataclass
class WahlkreuzSymbol:
    background_color: str   # raises if in {"White","Gelb"} (D12)
    def emit(self, page=None) -> Iterable: ...


# tools/sla_lib/builder/ci.py — allow-lists for brand_constraints
class Color:
    @classmethod
    def all(cls) -> list[str]: ...   # BLACK,WHITE,REGISTRATION,DUNKELGRUEN,HELLGRUEN,GELB,MAGENTA

class Style:
    @classmethod
    def all(cls) -> list[str]: ...

def load_ci(path=None):
    """Returns _CI with .colors, .fonts (list[str]), .styles, .layers."""


# === NEW INTERFACES (this plan creates them) ===

# tools/sla_lib/builder/composites.py — D1, D2/D5-corrected (anname; replace, not mutate)
@dataclass
class AlignedRow:
    y_mm: float; children: list; name: str = ""
    def emit(self, page=None) -> Iterable:
        import dataclasses
        for child in self.children:
            yield dataclasses.replace(child, y_mm=self.y_mm)

@dataclass
class AlignedColumn:
    x_mm: float; children: list; name: str = ""
    def emit(self, page=None) -> Iterable: ...

@dataclass
class MirroredPair:
    left: object; right: object; axis_mm: float
    axis: str = "x"   # "x" = vertical mirror line; "y" = horizontal
    name: str = ""
    def emit(self, page=None) -> Iterable: ...

@dataclass
class EqualGapStack:
    gap_mm: float; children: list
    axis: str = "y"; start_mm: float = 0.0; name: str = ""
    def emit(self, page=None) -> Iterable: ...

@dataclass
class GridSpec:
    cols: int; rows: int
    gutter_mm: float = 10.0; margin_mm: float = 12.0
    page_w_mm: float = 0.0; page_h_mm: float = 0.0
    def cell_xy(self, row, col, span_cols=1, span_rows=1) -> tuple: ...

@dataclass
class GridCell:
    grid: GridSpec; row: int; col: int; child: object
    span_cols: int = 1; span_rows: int = 1; name: str = ""
    def emit(self, page=None) -> Iterable: ...

@dataclass
class HierarchyBlock:
    """Headline > Subline > Body with descending fontsize. Raises ValueError on bad order."""
    headline: object; subline: object | None = None; body: object | None = None
    name: str = ""
    def emit(self, page=None) -> Iterable: ...


# tools/sla_lib/builder/constraints.py — D2/D5-corrected (anname; both forms)
@dataclass(frozen=True)
class Violation:
    severity: str   # "error" | "warning" | "info"
    message: str
    rule_id: str = ""
    targets: tuple = ()

@dataclass(frozen=True)
class Constraint:
    id: str; targets: tuple; name: str = ""
    def check(self, primitives_by_anname: dict) -> list: ...
    def referenced_annames(self) -> tuple: ...

# Factories accept Frame objects (records .anname) OR strings
def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def mirrored_y(top, bottom, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def equal_gap(*targets, axis: str = "y", gap_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def hierarchy(*targets, by: str = "fontsize", name: str = "") -> Constraint: ...
def same_style(*targets, name: str = "") -> Constraint: ...
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...


# tools/sla_lib/builder/brand_constraints.py — D3 (auto-applied; meta.yml override)
@dataclass(frozen=True)
class BrandRule:
    id: str          # e.g. "brand:logo_size_3M" — exact strings used in meta.yml
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc) -> list: ...

BRAND_CONSTRAINTS: list = [
    rule_color_palette_only(),    # brand:color_palette
    rule_font_family_only(),      # brand:font_family
    rule_line_spacing_factor_0_9(),  # brand:line_spacing_0.9
    rule_hl_sl_distance_x2(),     # brand:hl_sl_distance_x2
    rule_logo_size_3M(),          # brand:logo_size_3M
    rule_text_on_green(),         # brand:text_on_green
    rule_bleed_3mm(),             # brand:bleed_3mm
    rule_wahlkreuz_colored_bg(),  # brand:wahlkreuz_colored_bg
]


# tools/sla_lib/builder/structural_check.py — orchestrator + CLI
@dataclass
class CheckIssue:
    severity: str; rule_id: str; message: str; location: str

@dataclass
class TemplateReport:
    slug: str
    constraint_issues: list
    brand_issues: list
    skipped_brand_rules: list
    @property
    def has_errors(self) -> bool: ...
    def to_markdown(self) -> str: ...

def check_template(slug: str) -> TemplateReport: ...
def main(argv=None) -> int: ...


# build_doc() contract — D13 — uniform import target on all 8 templates
# 5 NEW templates (themen-plakat, wahlaufruf-postkarte, wahltag-tueranhaenger,
#                  infostand-tent-card, kandidat-falzflyer):
def build_doc() -> Document:
    """Return constructed Document, no save."""

def build(out_path=HERE / "template.sla") -> Path:
    doc = build_doc()
    doc.save(out_path)
    return Path(out_path)

# 3 PRODUCTION templates (postkarte-a6-kampagne, plakat-a1-hochformat, zeitung-a4-grun)
# already have build_template() / build_preview() (post-#13). Add module-level alias:
build_doc = build_template


# meta.yml — new optional field validated by jsonschema
# brand_overrides:
#   - id: brand:logo_size_3M
#     reason: "monochrome poster — 2.5xM variant, intentional design"
</interfaces>

Key files to read for context (executor):
@tools/sla_lib/builder/__init__.py — public API surface
@tools/sla_lib/builder/primitives.py — frame dataclasses
@tools/sla_lib/builder/document.py — Page.add() emit-flatten; iter_all_primitives() addition site
@tools/sla_lib/builder/blocks.py — emit() signature pattern
@tools/sla_lib/builder/ci.py — Color.all() / Style.all() / load_ci().fonts allow-lists
@tools/spec_check.py — tolerance default at line ~178 (currently 0.1mm)
@templates/themen-plakat-a3-quer/build.py — Phase 3 vorzeige refactor target
@shared/brand/QUICKGUIDE-NOTES.md — brand-rule formula source-of-truth
@bin/validate, @bin/check-stale-previews, @bin/render-gallery — verification harness
</context>

<commit_format>
Format: conventional with numeric issue prefix
Pattern: 12: type(scope): subject
Example: 12: feat(dsl): add Document.iter_all_primitives() for constraint walking
Types in use: feat, fix, test, refactor, docs, chore
NO "claude" attribution in commit body, code comments, file content, or PR.
</commit_format>

<tasks>

<!-- ============================================================== -->
<!-- PHASE 1 — DSL FOUNDATION (5 tasks)                               -->
<!-- ============================================================== -->

<task type="auto">
  <id>p1-iter-primitives</id>
  <name>Task 1: Add Document.iter_all_primitives() + tests</name>
  <files>tools/sla_lib/builder/document.py, tools/sla_lib/tests/test_document_iter_primitives.py</files>
  <action>
  Add a small additive method on `Document`:

  ```python
  def iter_all_primitives(self):
      """Yield primitives across master pages and pages, in stable order
      (masters first, then pages; per page: order matches `page.items`)."""
      for page in (*self.masters, *self.pages):
          yield from page.items
  ```

  No caching. KISS — see RESEARCH "Don't Hand-Roll" §3.

  Tests in new `tools/sla_lib/tests/test_document_iter_primitives.py`:
  1. empty doc yields nothing
  2. doc with one page + 3 frames yields 3 frames in `page.items` order
  3. doc with master page + 2 pages yields master items first
  4. frames preserve their `anname` through iteration
  5. items added via a tiny stub composite (object with `emit(self)`) appear post-emit (already flattened by `Page.add`)

  Per RESEARCH "Architecture Patterns" #4: this is THE orchestration anchor. Do not add iter helpers elsewhere.
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/test_document_iter_primitives.py -v</automated>
  </verify>
  <done>
  - `Document.iter_all_primitives()` exists, iterates masters then pages
  - Test file added with ≥5 tests, all green
  - Existing `tools/sla_lib/tests/` continues to pass
  </done>
  <commit>12: feat(dsl): add Document.iter_all_primitives() for constraint walking</commit>
</task>

<task type="auto" tdd="true">
  <id>p1-composites</id>
  <name>Task 2: Composite blocks module (composites.py) + tests</name>
  <files>tools/sla_lib/builder/composites.py, tools/sla_lib/tests/test_composites.py, tools/sla_lib/builder/__init__.py</files>
  <behavior>
  - `AlignedRow(y_mm=N, children=[f1,f2,f3]).emit()` yields 3 frames each with y_mm=N; originals unchanged
  - `AlignedColumn(x_mm=N, children=[...])` yields children with x_mm forced
  - `MirroredPair(left, right, axis_mm=A, axis="x")` reflects right's center-x so `(left_center_x + right_center_x)/2 == A`
  - `EqualGapStack(gap_mm=G, children=[...], axis="y", start_mm=S)` yields children at y = S, S+h0+G, S+h0+G+h1+G, ...
  - `GridSpec.cell_xy(row, col)` returns correct (x,y,w,h)
  - `GridCell(grid, row, col, child, span_cols, span_rows)` yields child with x/y/w/h forced from grid
  - `HierarchyBlock(headline, subline, body)` yields all set frames; raises ValueError if fontsize order is wrong (when both fontsize values resolvable; partial subline=None ok)
  - All composites: original child objects MUST NOT be mutated. Use `dataclasses.replace(child, ...)` per RESEARCH P-COMPOSITE-MUTATION.
  </behavior>
  <action>
  RED: Write `tools/sla_lib/tests/test_composites.py` with ≥6 tests per composite (≥36 total). Cover:
  - happy path (constraint applied)
  - children-not-mutated (assert original frame's y_mm/x_mm unchanged)
  - empty children for variable-arity composites
  - single child
  - mixed frame types (TextFrame + ImageFrame)
  - axis variants (`MirroredPair(axis="y")`, `EqualGapStack(axis="x")`)
  - For `HierarchyBlock`: valid order passes, invalid order raises ValueError, partial (subline=None) ok
  - For `GridCell`: span_cols=2 wider; span_rows=2 taller

  GREEN: Implement `tools/sla_lib/builder/composites.py` per `<interfaces>`. Each composite is a `@dataclass`. Signature `emit(self, page=None)` matches existing block pattern at blocks.py:391.

  Use `dataclasses.replace(child, y_mm=...)` not in-place mutation. Verify dataclasses.replace works on TextFrame/ImageFrame/Polygon (all inherit from `_Frame` which is a dataclass).

  REFACTOR: file ≤300 LoC; docstrings cite CONTEXT D1.

  Update `tools/sla_lib/builder/__init__.py`:
  ```python
  from .composites import (
      AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
      GridSpec, GridCell, HierarchyBlock,
  )
  ```
  Add to `__all__`.

  Do NOT modify `blocks.py` — composites is its own home (RESEARCH P-COMPOSITE-NAMING).
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/test_composites.py -v && python3 -c "from sla_lib.builder import AlignedRow, AlignedColumn, MirroredPair, EqualGapStack, GridSpec, GridCell, HierarchyBlock"</automated>
  </verify>
  <done>
  - `composites.py` with 6 composites + GridSpec helper
  - ≥36 tests (≥6/composite) all green
  - `from sla_lib.builder import AlignedRow, ...` succeeds
  - Original child frames unmutated after emit (test-verified)
  - All existing tests green
  </done>
  <commit>12: feat(dsl): add composite blocks (AlignedRow, MirroredPair, EqualGapStack, etc.) for constraint-by-construction</commit>
</task>

<task type="auto" tdd="true">
  <id>p1-constraints</id>
  <name>Task 3: Free-form constraints module (constraints.py) + tests</name>
  <files>tools/sla_lib/builder/constraints.py, tools/sla_lib/tests/test_constraints.py, tools/sla_lib/builder/__init__.py</files>
  <behavior>
  Per RESEARCH "Correction to D5": resolution by **anname**, not Python id().
  Each factory accepts Frame objects (records `.anname`) or strings.

  Per-factory:
  - `same_y(*targets, tolerance_mm=0.5)`: y_mm agree within tolerance
  - `same_x(*targets, tolerance_mm=0.5)`: x_mm agree
  - `same_size(*targets, axis="both"|"w"|"h", tolerance_mm=0.5)`: dims agree
  - `mirrored_x(left, right, axis_mm, tolerance_mm=0.5)`: `(left_center_x + right_center_x)/2 ≈ axis_mm`
  - `mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5)`: same on Y
  - `inside(child, parent, tolerance_mm=0.5)`: child bbox ⊂ parent bbox
  - `equal_gap(*targets, axis, gap_mm, tolerance_mm=0.5)`: consecutive gaps ≈ gap_mm
  - `hierarchy(*targets, by="fontsize")`: descending order by attribute
  - `same_style(*targets)`: all targets have identical `.style`
  - `distance_y(a, b, equals, tolerance_mm=0.5)`: `|a.y_mm - b.y_mm| ≈ equals`
  - `distance_x(a, b, equals, tolerance_mm=0.5)`: `|a.x_mm - b.x_mm| ≈ equals`

  Each Constraint exposes `referenced_annames() -> tuple` for orphan-check (RESEARCH §10).

  Auto-id: if `name=""`, generate from class name + targets.
  </behavior>
  <action>
  RED: Write `tools/sla_lib/tests/test_constraints.py` with ≥4 tests per factory (≥44 total). Cover:
  - happy path (passes, returns empty list)
  - violation (returns Violation with severity="error", correct rule_id, targets)
  - tolerance edge (drift = tolerance passes; drift > tolerance fails)
  - mixed input forms (Frame + string accepted in same call)
  - missing anname → Violation severity="warning" naming the missing target
  - For `inside`: fully-inside passes; outside fails; partial-overlap fails
  - For `mirrored_x`: passes regardless of arg order
  - For `hierarchy`: ascending fails, descending passes
  - For `equal_gap`: uniform gap passes; uneven fails

  GREEN: Implement `tools/sla_lib/builder/constraints.py` per `<interfaces>`.
  Resolution helper:
  ```python
  def _to_anname(t) -> str:
      return t if isinstance(t, str) else t.anname
  ```

  Update `__init__.py`:
  ```python
  from .constraints import (
      same_y, same_x, same_size, mirrored_x, mirrored_y, inside,
      equal_gap, hierarchy, same_style, distance_y, distance_x,
      Constraint, Violation,
  )
  ```
  Add all to `__all__`.

  Per RESEARCH "Don't Hand-Roll": no solver. Plain predicates only.
  Per RESEARCH P-INLINE-FRAME: orphan anname returns warning Violation, not silent skip.
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/test_constraints.py -v && python3 -c "from sla_lib.builder import same_y, same_x, mirrored_x, inside, equal_gap, hierarchy, same_style, distance_y, distance_x, Constraint, Violation"</automated>
  </verify>
  <done>
  - `constraints.py` with 11 factory functions + Constraint/Violation
  - ≥44 tests (≥4/factory) all green
  - All factories accept both Frame and string forms
  - Orphan-anname returns warning Violation
  - All existing tests green
  </done>
  <commit>12: feat(dsl): add free-form constraint factories (same_y, mirrored_x, inside, ...)</commit>
</task>

<task type="auto" tdd="true">
  <id>p1-brand-constraints</id>
  <name>Task 4: Brand-constraints module (brand_constraints.py) + tests</name>
  <files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/tests/test_brand_constraints.py, tools/sla_lib/builder/__init__.py</files>
  <behavior>
  Per CONTEXT D3 + RESEARCH §"Brand-rule sketches": 8 BrandRule predicates auto-applied via structural_check, with override mechanism in meta.yml.

  Rules — IDs are EXACT (used in meta.yml.brand_overrides):
  1. `brand:color_palette` — every primitive's fill / line_color / fcolor ∈ `Color.all() ∪ doc._extra_colors.keys() ∪ {"None", ""}`
  2. `brand:font_family` — every TextFrame uses font from `load_ci().fonts`
  3. `brand:line_spacing_0.9` — every paragraph style: `linesp ≈ fontsize × 0.9` (tolerance 0.5pt)
  4. `brand:hl_sl_distance_x2` — for each (Headline, Sub-Headline/Subline) pair on a page (anname substring match), distance_y ≈ baseline_x × 2; baseline_x ≈ body-12 fontsize × 0.9 / 2 ≈ 5.4mm; allow ±1mm
  5. `brand:logo_size_3M` — for ImageFrame whose anname matches `\bLogo\b` (case-insensitive), `width ≈ 3 × M` where `M = 0.06 × min(page_w_mm, page_h_mm)`, tolerance 0.5mm
  6. `brand:text_on_green` — TextFrame with brand-typography style (style starts with `ci/h*` or `ci/headline*`) AND `fcolor=White` must overlap a Polygon with fill ∈ {Dunkelgrün, Hellgrün}
  7. `brand:bleed_3mm` — doc bleed = 3mm on all sides
  8. `brand:wahlkreuz_colored_bg` — for any block emitted by WahlkreuzSymbol (anname containing "Wahlkreuz"), background_color ∈ {Dunkelgrün, Hellgrün, Magenta}

  Each rule returns `list[Violation]` with severity="error", rule_id = the brand id, and a clear message naming the offending frame's anname.

  Module exposes `BRAND_CONSTRAINTS: list[BrandRule]` — flat list, no decorator-registry (RESEARCH §8 Pattern A).
  </behavior>
  <action>
  RED: Write `tools/sla_lib/tests/test_brand_constraints.py` with ≥3 tests per rule (≥24 total). Synthetic minimal Documents — do NOT depend on real templates here.

  Examples:
  - `logo_size_3M`: A3-quer (kurze_kante=297mm), M=17.82mm, logo at 3M=53.46mm passes; 60mm fails
  - `font_family`: Gotham passes, Arial fails
  - `text_on_green`: white text on green polygon passes; white text on white bg fails; non-white text exempt
  - `bleed_3mm`: 3mm passes, 0mm fails
  - `color_palette`: Black/White passes; off-palette fcolor fails

  GREEN: Implement `tools/sla_lib/builder/brand_constraints.py`. Each rule is a BrandRule instance via `_make_rule_*()` helper or a thin subclass. Module-level `BRAND_CONSTRAINTS = [...]` lists 8 instances.

  Use `Color.all()` and `load_ci().fonts` as allow-lists. Do NOT hardcode.

  Module header docstring cites RESEARCH §1 + ecosystem §1: "Predicate-style validation, NOT a constraint solver. Do not reach for kiwisolver or z3."

  Update `__init__.py`:
  ```python
  from .brand_constraints import BRAND_CONSTRAINTS, BrandRule
  ```

  Drift on real templates is EXPECTED in Phase 4; do NOT make rules pass on real templates here.
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/test_brand_constraints.py -v && python3 -c "from sla_lib.builder.brand_constraints import BRAND_CONSTRAINTS; ids=[r.id for r in BRAND_CONSTRAINTS]; assert len(BRAND_CONSTRAINTS)==8 and 'brand:logo_size_3M' in ids; print(ids)"</automated>
  </verify>
  <done>
  - `brand_constraints.py` with 8 rules, IDs match CONTEXT D5 exactly
  - ≥24 tests (≥3/rule) all green
  - `BRAND_CONSTRAINTS` list of length 8 importable
  - All existing tests green
  </done>
  <commit>12: feat(dsl): add 8 brand-CI constraint predicates auto-applied across templates</commit>
</task>

<task type="auto">
  <id>p1-structural-check</id>
  <name>Task 5: structural_check.py orchestrator + meta.yml override schema + tests</name>
  <files>tools/sla_lib/builder/structural_check.py, tools/sla_lib/builder/meta_schema.py, tools/sla_lib/tests/test_structural_check.py</files>
  <action>
  Per CONTEXT D3, D7, D11 + RESEARCH §10 (orphan warning) + §3 (jsonschema).

  Implement `tools/sla_lib/builder/structural_check.py`:

  1. `check_template(slug: str) -> TemplateReport`:
     - `mod = importlib.import_module(f"templates.{slug}.build")` — adjust sys.path; templates/<slug>/build.py is the file
     - if not `hasattr(mod, "build_doc")`: return TemplateReport with error CheckIssue
     - `doc = mod.build_doc()`
     - `primitives = list(doc.iter_all_primitives())`
     - `primitives_by_anname = {p.anname: p for p in primitives if getattr(p,'anname','')}`
     - load `templates/<slug>/meta.yml`, extract `brand_overrides` via meta_schema
     - For each `BrandRule` in BRAND_CONSTRAINTS NOT in overrides:
         - `for v in rule.check(primitives, doc): brand_issues.append(CheckIssue(...))`
     - For each Constraint in `getattr(mod, "CONSTRAINTS", [])`:
         - `missing = set(c.referenced_annames()) - set(primitives_by_anname)`
         - If missing: append CheckIssue(severity="warning", rule_id=c.id, message=f"references missing anname(s): {sorted(missing)}"), skip evaluating
         - Else: `for v in c.check(primitives_by_anname): constraint_issues.append(CheckIssue(...))`
     - Return TemplateReport(slug, constraint_issues, brand_issues, skipped_brand_rules=overrides)

  2. `def main(argv=None) -> int` CLI:
     - `python3 -m sla_lib.builder.structural_check <slug>`
     - `python3 -m sla_lib.builder.structural_check --all`
     - `python3 -m sla_lib.builder.structural_check --json`
     - `--all` walks `templates/*/` excluding `_specs/` and `_smoke/`
     - Default output: markdown to stdout
     - Exit 1 if any TemplateReport has any error-severity issue; warnings do NOT fail CI (RESEARCH §10)

  3. Markdown output (CONTEXT D7) — plain ASCII markers (no emojis):
     ```
     # structural_check report

     ## templates/<slug>
     ### CONSTRAINTS
     - PASS themen_row_alignment (same_y on 3 frames)
     - FAIL inside(qr_code, panel_closer): qr at (245,195) outside panel (210-300, 200-280)
     ### BRAND_CONSTRAINTS
     - PASS brand:color_palette
     - SKIP brand:logo_size_3M (overridden in meta.yml)
     - FAIL brand:hl_sl_distance_x2: distance 18.5mm, expected 10.8±1mm

     Result: 2 errors, 0 warnings, 1 skipped, 6 passes
     ```

  Implement `tools/sla_lib/builder/meta_schema.py` (~50 LoC):
  - Validates `brand_overrides:` field of meta.yml using `jsonschema` (already installed)
  - Schema requires each entry to have `id` (matching `^brand:[a-z_0-9]+$`) and `reason` (non-empty string)
  - On schema fail: raise with clear pointer
  - On unknown rule-id: warn (do not fail)
  - Public function: `load_brand_overrides(slug: str) -> set[str]` returns IDs to skip; empty set if no overrides

  Tests `tools/sla_lib/tests/test_structural_check.py`:
  - synthetic build module: write fake build.py to tmp_path / sys.path-insert / importlib; build_doc returns Document with 3 frames; CONSTRAINTS contains passing same_y + failing inside; assert 1 constraint error, 1 pass
  - synthetic with orphan reference: `CONSTRAINTS = [same_y("Foo", "Bar")]` → 1 warning, 0 errors, exit 0
  - meta.yml override: `brand_overrides: [{id: brand:logo_size_3M, reason: "test"}]` → that rule SKIP
  - missing build_doc(): TemplateReport with one error CheckIssue
  - CLI exit code: 0 green, 1 error, 0 warnings-only
  - Markdown output renders all four sections
  - meta_schema rejects malformed entry (id missing) with clear message
  - meta_schema warns (not raises) on unknown rule-id

  Mark a `--all` real-templates integration test as `pytest.mark.skip` until Task 6 — flip on then.

  No `__init__.py` change (orchestrator is module, not library export).
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/test_structural_check.py -v && python3 -m sla_lib.builder.structural_check --help</automated>
  </verify>
  <done>
  - `structural_check.py` + `meta_schema.py` exist
  - CLI `--help` works
  - ≥8 tests in test_structural_check.py, all green (real-template `--all` skipped until Task 6)
  - Synthetic-build via importlib + sys.path proven
  - Orphan-anname returns warning
  - Meta.yml override skips rules; jsonschema validates entries
  </done>
  <commit>12: feat(dsl): add structural_check orchestrator + meta.yml brand-overrides schema</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 2 — build_doc() CONTRACT ON ALL 8 TEMPLATES (1 task)       -->
<!-- ============================================================== -->

<task type="auto">
  <id>p2-build-doc-contract</id>
  <name>Task 6: Add build_doc() to all 8 templates (additive only, SHA-stable)</name>
  <files>templates/themen-plakat-a3-quer/build.py, templates/wahlaufruf-postkarte-a6-quer/build.py, templates/wahltag-tueranhaenger/build.py, templates/infostand-tent-card-a5-quer/build.py, templates/kandidat-falzflyer-din-lang/build.py, templates/postkarte-a6-kampagne/build.py, templates/plakat-a1-hochformat/build.py, templates/zeitung-a4-grun/build.py</files>
  <action>
  Per CONTEXT D13: unify import contract for structural_check.

  **5 NEW templates** (themen-plakat-a3-quer, wahlaufruf-postkarte-a6-quer, wahltag-tueranhaenger, infostand-tent-card-a5-quer, kandidat-falzflyer-din-lang):

  Refactor existing `def build(out_path) -> Path` into a `build_doc() -> Document` helper plus a thin `build()`:
  ```python
  def build_doc() -> Document:
      doc = Document(...)
      # ALL existing construction logic, verbatim, indented one level
      return doc

  def build(out_path: Path | str = HERE / "template.sla") -> Path:
      doc = build_doc()
      doc.save(out_path)
      return Path(out_path)
  ```
  Existing CLI `if __name__ == "__main__": build()` stays unchanged.

  **3 PRODUCTION templates** (postkarte-a6-kampagne, plakat-a1-hochformat, zeitung-a4-grun) — already have `build_template()` + `build_preview()` from #13:

  Append after `build_template` definition:
  ```python
  # Public alias for structural_check (Issue #12, D13)
  build_doc = build_template
  ```
  DO NOT touch `build_template()` or `build_preview()` bodies. DO NOT alias to `build_preview` — `build_doc` reflects the clean end-user template (RESEARCH "Correction D13").

  **CRITICAL — SHA stability gate (CONTEXT D10)**: This task is purely additive. No existing logic moves, no order changes, no construction code is rewritten. Verify byte-stability by capturing pre-task `sha256sum templates/*/template.sla`, completing edits, rebuilding, comparing. Diff MUST be empty.

  Flip the structural_check `--all` integration test (skipped in Task 5) to enabled. Each template should be importable via `mod.build_doc()` returning a Document; structural_check should run without ImportError. Constraint and brand-rule failures are EXPECTED (Phase 4 handles); only assert that `mod.build_doc()` succeeds and orchestrator completes.
  </action>
  <verify>
    <automated>for d in themen-plakat-a3-quer wahlaufruf-postkarte-a6-quer wahltag-tueranhaenger infostand-tent-card-a5-quer kandidat-falzflyer-din-lang postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do python3 -c "import importlib.util; spec=importlib.util.spec_from_file_location('m','templates/'+'$d'+'/build.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); assert hasattr(m,'build_doc'), '$d missing build_doc'; doc=m.build_doc(); assert doc is not None"; done && bin/check-stale-previews</automated>
  </verify>
  <done>
  - All 8 templates expose `build_doc() -> Document`
  - 5 new templates: build() refactored to call build_doc().save(); construction logic verbatim
  - 3 production templates: `build_doc = build_template` alias added; bodies untouched
  - SHA-stability verified: pre-task SHAs == post-task SHAs for all 8 SLAs
  - `bin/check-stale-previews` green
  - structural_check `--all` integration test enabled and runs without ImportError
  - All existing tests green
  </done>
  <commit>12: refactor(templates): unify build_doc() import contract across all 8 templates</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 3 — VORZEIGE-REFACTOR (themen-plakat-a3-quer) (1 task)     -->
<!-- ============================================================== -->

<task type="auto">
  <id>p3-themen-plakat-vorzeige</id>
  <name>Task 7: Refactor themen-plakat-a3-quer with composites + CONSTRAINTS list (vorzeige, SHA-stable)</name>
  <files>templates/themen-plakat-a3-quer/build.py</files>
  <action>
  Per CONTEXT D9 + RESEARCH "Correction to D9": calibrate the API on the simplest template (~13 emitted primitives). API-survives-first-contact gate.

  Refactor strategy (codebase research §2 ASCII sketch):

  1. Construct frames as named locals BEFORE adding to page (RESEARCH P-INLINE-FRAME — construct-then-add convention):
     ```python
     logo = ImageFrame(x_mm=15, y_mm=10, w_mm=32, h_mm=28, anname="Logo Grüne (top-left)", ...)
     qr   = ImageFrame(x_mm=380, y_mm=8, w_mm=25, h_mm=25, anname="QR-Code (quelle)", ...)
     headline = TextFrame(x_mm=15, y_mm=40, w_mm=390, h_mm=50, anname="Headline These", ...)
     sub      = TextFrame(x_mm=15, y_mm=92, w_mm=390, h_mm=16, anname="Sub-Headline", ...)
     beleg_hds = [TextFrame(x_mm=col_x_for(i), y_mm=130, w_mm=COL_W_MM, h_mm=20,
                            anname=f"Beleg {i+1} — Headline", style="...") for i in range(3)]
     beleg_bds = [TextFrame(x_mm=col_x_for(i), y_mm=152, w_mm=COL_W_MM, h_mm=70,
                            anname=f"Beleg {i+1} — Body", style="...") for i in range(3)]
     hero = ImageFrame(...)
     quelle = TextFrame(...)
     impressum = TextFrame(...)
     ```

  2. Compose with composites where natural:
     ```python
     page.add(Polygon(..., anname="Seitenhintergrund", fill="White"))
     page.add(logo); page.add(qr)
     page.add(headline); page.add(sub)
     page.add(AlignedRow(y_mm=130, children=beleg_hds, name="beleg_headlines_row"))
     page.add(AlignedRow(y_mm=152, children=beleg_bds, name="beleg_bodies_row"))
     page.add(hero); page.add(quelle); page.add(impressum)
     ```

  3. Module-level CONSTRAINTS list:
     ```python
     CONSTRAINTS = [
         same_y(*beleg_hds, name="beleg_headlines_row"),
         same_y(*beleg_bds, name="beleg_bodies_row"),
         distance_y(headline, sub, equals=52.0, name="hl_to_sub"),
         distance_y(beleg_hds[0], beleg_bds[0], equals=22.0, name="beleg_hd_to_body"),
         same_style(*beleg_hds, name="beleg_hd_style_consistent"),
         same_style(*beleg_bds, name="beleg_body_style_consistent"),
     ]
     ```

  **CRITICAL — order preservation** (RESEARCH P-SHA-DRIFT): the page.add() sequence must produce the SAME page.items list as the pre-refactor build. AlignedRow.emit() yields children in list order. Check the original loop order in build.py:130-292; if the original interleaved beleg_hds[i] and beleg_bds[i] per iteration, the refactor MUST preserve that interleave (use one composite per iteration OR fall back to per-frame add for the loop section).

  Verify SHA stability: pre-vs-post `templates/themen-plakat-a3-quer/template.sla` SHA must be IDENTICAL. If different: STOP, investigate composite emit() ordering, dataclasses.replace() field handling. Do NOT update `previews_for_sla` blindly.

  Run `python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer` — CONSTRAINTS list reports PASS on all 6. Brand-constraints may FAIL — Phase 4 handles.

  **Phase-2 EXIT criterion** (RESEARCH §"Phase-2 acceptance gate"): if Composite-API requires hacks (monkey-patching, global state, inspect-magic), or `dataclasses.replace` fails on a frame type, or SLA bytes drift unfixably — STOP and re-design Phase 1 modules. Do NOT proceed to Phase 5 fan-out until vorzeige is byte-clean.
  </action>
  <verify>
    <automated>(cd templates/themen-plakat-a3-quer && python3 build.py) && bin/check-stale-previews && python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - themen-plakat build.py uses ≥1 AlignedRow composite for the belege grid
  - CONSTRAINTS list with ≥4 entries
  - Pre-vs-post SHA on templates/themen-plakat-a3-quer/template.sla IDENTICAL
  - `bin/check-stale-previews` green (previews_for_sla SHA unchanged)
  - structural_check exits 0 on CONSTRAINTS (brand may FAIL — handled Phase 4)
  - Author has confirmed composite-API ergonomics good for fan-out OR documented adjustments needed in build.py comments
  - All existing tests green
  </done>
  <commit>12: refactor(themen-plakat): use AlignedRow composites + CONSTRAINTS list (vorzeige)</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 4 — BRAND-CONSTRAINT DISCOVERY + OVERRIDES (1 task)        -->
<!-- ============================================================== -->

<task type="auto">
  <id>p4-brand-discovery</id>
  <name>Task 8: Run structural_check on all 8, capture brand drift, add meta.yml overrides</name>
  <files>templates/themen-plakat-a3-quer/meta.yml, templates/wahlaufruf-postkarte-a6-quer/meta.yml, templates/wahltag-tueranhaenger/meta.yml, templates/infostand-tent-card-a5-quer/meta.yml, templates/kandidat-falzflyer-din-lang/meta.yml, templates/postkarte-a6-kampagne/meta.yml, templates/plakat-a1-hochformat/meta.yml, templates/zeitung-a4-grun/meta.yml</files>
  <action>
  Per RESEARCH §"Brand-rule sketches" + P-BRAND-DRIFT-DISCOVERY: 4-5 templates expected to surface KNOWN drift (line_spacing, hl_sl_distance, logo_size, text_on_green). Address via `brand_overrides` with explanation, NOT by hiding via implementation hacks (issue prompt "Don't" rule).

  Process:

  1. Run `python3 -m sla_lib.builder.structural_check --all > /tmp/brand-drift-report.md`

  2. For each FAIL entry, classify:
     - **Genuine drift** (template bug): rare; if found, document and defer to a follow-up issue (do NOT fix template construction in this issue — out of scope)
     - **Intentional design deviation** (override needed): add to that template's meta.yml.brand_overrides with a clear `reason`

  3. Edit each affected template's meta.yml:
     ```yaml
     brand_overrides:
       # See shared/brand/SPEC-WRITING-GUIDE.md "Brand-Override-Konvention"
       - id: brand:hl_sl_distance_x2
         reason: "Türanhänger uses tighter HL/SL spacing (12pt vs. 18pt baseline) to fit the door-hanger format; design choice approved by brand team."
       - id: brand:logo_size_3M
         reason: "Plakat A1 logo at 2.5xM (digital-tier ratio) for visual balance with headline block; intentional."
     ```

  4. Re-run `structural_check --all` until exit 0.

  5. **SHA-stability check**: meta.yml edits must NOT change SLA bytes. After edits, rebuild all 8 and compare SHAs to Task 6 post-state — must be IDENTICAL.

  6. **Round-trip diff** (3 production templates): `python3 tools/sla_diff.py --strict --allow-brand-extras` must remain green (critical=0).

  Estimate: 4-5 of 8 templates need overrides; 1-3 entries each.

  IMPORTANT — do NOT fix brand-rule code to make rules pass on templates with intentional deviations. The override mechanism IS the right tool. RESEARCH P-BRAND-DRIFT-DISCOVERY: "address via overrides with explanation, not hide via implementation hacks."
  </action>
  <verify>
    <automated>python3 -m sla_lib.builder.structural_check --all && bin/check-stale-previews && python3 tools/sla_diff.py --strict --allow-brand-extras</automated>
  </verify>
  <done>
  - `structural_check --all` exits 0 (all error-severity resolved via overrides)
  - 4-5 affected templates have `brand_overrides:` entries with `id` + `reason`
  - SLA SHAs unchanged from Task 6 post-state
  - `bin/check-stale-previews` green
  - `tools/sla_diff.py --strict` green on 3 production templates
  - /tmp/brand-drift-report.md captures discovery (referenced in Phase 6 SPEC-WRITING-GUIDE worked example)
  </done>
  <commit>12: chore(templates): add brand_overrides to meta.yml for known-deviation templates</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 5 — FAN-OUT REFACTOR OF 7 REMAINING TEMPLATES (7 tasks)   -->
<!-- ============================================================== -->

<task type="auto">
  <id>p5-wahlaufruf-postkarte</id>
  <name>Task 9: Refactor wahlaufruf-postkarte-a6-quer with composites + CONSTRAINTS (SHA-stable)</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/build.py</files>
  <action>
  Per RESEARCH codebase §2 (refactor naturalness HIGH — symmetric 2x2 cell grid).

  Patterns:
  - Front headline: single TextFrame, no composite
  - Back: 2x2 grid. Use `AlignedRow(y=22, children=[c1_hd, c2_hd])` and `AlignedRow(y=62, children=[c3_hd, c4_hd])` for the two header rows. Optionally `AlignedColumn(x=6, children=[c1_hd, c3_hd])` etc.
  - Construct-then-add convention: all frames as named locals before page.add()

  CONSTRAINTS list (~4-6 entries): same_y for header rows; same_x for columns; mirrored_x if symmetric design; same_style for cells of the same kind.

  SHA-stability gate: pre-vs-post SHA on templates/wahlaufruf-postkarte-a6-quer/template.sla IDENTICAL. If different: investigate emit-order; fall back to per-frame add + CONSTRAINTS-only (pure metadata) if needed.

  Run `python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer` — exit 0 on CONSTRAINTS (brand-overrides from Task 8 cover known drift).
  </action>
  <verify>
    <automated>(cd templates/wahlaufruf-postkarte-a6-quer && python3 build.py) && bin/check-stale-previews && python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py uses ≥1 composite (AlignedRow / AlignedColumn / MirroredPair)
  - CONSTRAINTS list with ≥4 entries
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` green
  - structural_check exits 0
  - All existing tests green
  </done>
  <commit>12: refactor(wahlaufruf-postkarte): use composites + CONSTRAINTS list</commit>
</task>

<task type="auto">
  <id>p5-wahltag-tueranhaenger</id>
  <name>Task 10: Refactor wahltag-tueranhaenger with composites + CONSTRAINTS (SHA-stable)</name>
  <files>templates/wahltag-tueranhaenger/build.py</files>
  <action>
  Per RESEARCH codebase §2 (refactor naturalness MEDIUM — strict vertical, single column).

  Patterns:
  - Use `HierarchyBlock(headline, sub, body)` for the front-panel HL → SL → body
  - Conditional inclusion (e.g. portrait_path.exists() at build.py:309-322): construct optional frame outside block, conditionally assign to None or instance, pass to composite/CONSTRAINTS only when non-None. Document convention in a comment.
  - Mostly free-form constraints (less alignment composites apply)

  CONSTRAINTS list (~3-5 entries):
  - `hierarchy(headline, sub, body, by="fontsize")` — explicit fontsize ordering
  - `same_x` for stacked elements
  - `distance_y(...)` for spacing
  - `same_style` for repeating elements

  Note: Türanhänger has known brand drift (line_spacing, hl_sl_distance — overridden in Task 8). structural_check exits 0 on CONSTRAINTS.

  SHA-stability gate: pre-vs-post SHA IDENTICAL. Conditional construction must preserve emit order.
  </action>
  <verify>
    <automated>(cd templates/wahltag-tueranhaenger && python3 build.py) && bin/check-stale-previews && python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py uses ≥1 HierarchyBlock composite
  - CONSTRAINTS list with ≥3 entries
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` green
  - structural_check exits 0
  - Conditional-frame convention documented in build.py comment
  - All existing tests green
  </done>
  <commit>12: refactor(wahltag-tueranhaenger): add HierarchyBlock + CONSTRAINTS list</commit>
</task>

<task type="auto">
  <id>p5-infostand-tent-card</id>
  <name>Task 11: Refactor infostand-tent-card-a5-quer with composites + CONSTRAINTS (SHA-stable)</name>
  <files>templates/infostand-tent-card-a5-quer/build.py</files>
  <action>
  Per RESEARCH codebase §2 (refactor naturalness MEDIUM — 2-panel symmetry around fold y=105).

  Patterns:
  - `MirroredPair(left=panel_A_hd, right=panel_B_hd, axis_mm=105.0, axis="y")` for panel-headlines mirror around fold. Panel B is rotated 180° in source — mirror is more semantic than geometric. If MirroredPair geometry doesn't fit, use individual frames + CONSTRAINTS-list mirrored_y as assertion-only.
  - Construct frames as named locals; mirror via composite OR CONSTRAINTS depending on what keeps SHA stable.

  CONSTRAINTS list (~3-5 entries): same_x for stacked panel-headers; mirrored_y(panel_A_hd, panel_B_hd, axis_mm=105.0); same_size; same_style.

  SHA-stability gate: pre-vs-post SHA IDENTICAL.

  If MirroredPair causes SHA drift due to coordinate rounding: drop the composite, use only CONSTRAINTS-list assertion (free-form mirrored_y). Both produce identical bytes (no emit-time mutation), assertion still catches drift. Document in build.py comment.
  </action>
  <verify>
    <automated>(cd templates/infostand-tent-card-a5-quer && python3 build.py) && bin/check-stale-previews && python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py uses MirroredPair OR free-form mirrored_y + same_size in CONSTRAINTS
  - CONSTRAINTS list with ≥3 entries
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` green
  - structural_check exits 0
  - All existing tests green
  </done>
  <commit>12: refactor(infostand-tent-card): use MirroredPair + CONSTRAINTS list</commit>
</task>

<task type="auto">
  <id>p5-kandidat-falzflyer</id>
  <name>Task 12: Refactor kandidat-falzflyer-din-lang with composites + CONSTRAINTS (SHA-stable)</name>
  <files>templates/kandidat-falzflyer-din-lang/build.py</files>
  <action>
  Per RESEARCH codebase §2 (refactor naturalness HIGH — 6-panel grid; densest template).

  Patterns:
  - `AlignedRow(y_mm=20, children=[p4_t1_hd, p5_t3_hd, p6_kontakt_hd])` for "all panel-top headlines share y=20"
  - `AlignedColumn(x_mm=6, children=[...])` for left-aligned slots in panels P1/P4
  - `EqualGapStack(axis="y", gap_mm=85, children=[klimaschutz_photo, soziales_photo])` for the 2 themen-photos in P4
  - Loop-constructed frames (`for sname, photo, body, name_idx in (...)`) stay as loops; resulting frames CAN feed an AlignedRow after construction

  CONSTRAINTS list (~6-10 entries — densest template):
  - `same_y` for panel-top headlines across panels
  - `same_x` for left columns
  - `equal_gap` for stacked themen-photos
  - `mirrored_x(p4_back, p6_back, axis_mm=148.5)` (RESEARCH "Phase Order")
  - `same_style` for repeated themen elements
  - `hierarchy` for HL → SL → body within each panel
  - `inside(qr_code, panel_closer)` if applicable

  SHA-stability gate: most complex template; spend extra care on emit-order. The original loop may interleave ImageFrame + TextFrame per iteration — refactor MUST preserve that. If composite use forces reorder: use CONSTRAINTS-only for the loop section.

  Pre-vs-post SHA IDENTICAL.
  </action>
  <verify>
    <automated>(cd templates/kandidat-falzflyer-din-lang && python3 build.py) && bin/check-stale-previews && python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py uses ≥2 composites (AlignedRow + EqualGapStack natural fit)
  - CONSTRAINTS list with ≥6 entries
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` green
  - structural_check exits 0
  - All existing tests green
  </done>
  <commit>12: refactor(kandidat-falzflyer): use AlignedRow + EqualGapStack composites + CONSTRAINTS list</commit>
</task>

<task type="auto">
  <id>p5-postkarte-a6-kampagne</id>
  <name>Task 13: Add CONSTRAINTS list to postkarte-a6-kampagne (production, no composite, SHA-stable)</name>
  <files>templates/postkarte-a6-kampagne/build.py</files>
  <action>
  Per RESEARCH codebase §2 (refactor naturalness LOW — production round-trip; no composite use).

  CONSTRAINTS-list-only refactor. Production templates are auto-generated from real SLAs; reorganizing page.add() sequences would break byte-stability. CONSTRAINTS list is pure metadata — no SLA bytes change.

  At the bottom of build_template() OR at module level, add:
  ```python
  # Pure metadata: not consumed by build_template().
  # Read by tools/sla_lib/builder/structural_check.py.
  CONSTRAINTS = [
      same_y("Headline-Front", "Sub-Front", ...),  # use anname strings since frames not exposed as locals
      inside("QR-Code", "Panel-Vorderseite"),
      same_style("Body-Front-1", "Body-Front-2"),
      ...
  ]
  ```

  Use string-anname references (not Frame objects) — production templates don't expose locals. The factory accepts both forms.

  Round-trip diff must remain green: `python3 tools/sla_diff.py --strict --allow-brand-extras`.

  Pre-vs-post SHA IDENTICAL (CONSTRAINTS list is at module level after build_doc; doesn't affect doc construction).

  Inspect actual annames in the existing template SLA via `grep '"anname"' templates/postkarte-a6-kampagne/*.sla` (or look at the dsl-generated build.py output). 3-5 CONSTRAINTS entries enough for production-template assertion coverage.
  </action>
  <verify>
    <automated>(cd templates/postkarte-a6-kampagne && python3 build.py) && bin/check-stale-previews && python3 tools/sla_diff.py --strict --allow-brand-extras && python3 -m sla_lib.builder.structural_check postkarte-a6-kampagne && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py has module-level CONSTRAINTS list (≥3 entries, string-anname form)
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` green
  - `tools/sla_diff.py --strict` green
  - structural_check exits 0
  - All existing tests green
  </done>
  <commit>12: refactor(postkarte-a6-kampagne): add CONSTRAINTS list (anname-form, production)</commit>
</task>

<task type="auto">
  <id>p5-plakat-a1</id>
  <name>Task 14: Add CONSTRAINTS list to plakat-a1-hochformat (production, SHA-stable)</name>
  <files>templates/plakat-a1-hochformat/build.py</files>
  <action>
  Same pattern as Task 13 (CONSTRAINTS-list-only, production).

  Plakat A1 is the simplest of 3 production templates (~198 LoC). Add module-level CONSTRAINTS with 3-5 entries using string-anname references:
  ```python
  CONSTRAINTS = [
      same_y("Headline", "Sub-Headline"),       # if same row
      same_x("Logo", "Plakat-Footer"),          # left-aligned
      inside("QR-Code", "Stoerer-Box"),
      same_style("Body-Top", "Body-Bottom"),
  ]
  ```

  Round-trip diff: `python3 tools/sla_diff.py --strict --allow-brand-extras` must stay green.

  Pre-vs-post SHA IDENTICAL.
  </action>
  <verify>
    <automated>(cd templates/plakat-a1-hochformat && python3 build.py) && bin/check-stale-previews && python3 tools/sla_diff.py --strict --allow-brand-extras && python3 -m sla_lib.builder.structural_check plakat-a1-hochformat && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py has module-level CONSTRAINTS list (≥3 entries)
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` + `sla_diff --strict` green
  - structural_check exits 0
  - All existing tests green
  </done>
  <commit>12: refactor(plakat-a1-hochformat): add CONSTRAINTS list (anname-form, production)</commit>
</task>

<task type="auto">
  <id>p5-zeitung</id>
  <name>Task 15: Add CONSTRAINTS list to zeitung-a4-grun (production, large, SHA-stable)</name>
  <files>templates/zeitung-a4-grun/build.py</files>
  <action>
  Same pattern as Task 13 (CONSTRAINTS-list-only, production). Zeitung is the largest auto-generated template (~2463 LoC, ~870 primitives).

  Performance budget (CONTEXT D11, RESEARCH "CI Integration"): structural_check on Zeitung must stay <5s. Don't add hundreds of CONSTRAINTS — focus on cross-page invariants:
  ```python
  CONSTRAINTS = [
      same_style("Body-Page-1-Col-1", "Body-Page-2-Col-1"),     # body-style consistency across pages
      hierarchy("Headline-Page-1", "Sub-Headline-Page-1", "Body-Page-1-Col-1"),
      inside("QR-Code-Impressum", "Impressum-Box"),
      same_x("PageNumber-Page-1", "PageNumber-Page-3"),         # page-number alignment across pages
      ... 5-8 entries total, focused on cross-page invariants
  ]
  ```

  Round-trip diff: `python3 tools/sla_diff.py --strict --allow-brand-extras` must stay green.

  Pre-vs-post SHA IDENTICAL.

  Time `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` — should complete in <5s (including build_doc()).
  </action>
  <verify>
    <automated>(cd templates/zeitung-a4-grun && python3 build.py) && bin/check-stale-previews && python3 tools/sla_diff.py --strict --allow-brand-extras && time python3 -m sla_lib.builder.structural_check zeitung-a4-grun && python3 -m pytest tools/sla_lib/tests/ -v</automated>
  </verify>
  <done>
  - build.py has module-level CONSTRAINTS list (≥5 entries focused on cross-page invariants)
  - Pre-vs-post SHA IDENTICAL
  - `bin/check-stale-previews` + `sla_diff --strict` green
  - structural_check zeitung-a4-grun exits 0 in <5s (timed)
  - All existing tests green
  </done>
  <commit>12: refactor(zeitung-a4-grun): add CONSTRAINTS list (anname-form, production)</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 6 — POLISH (3 tasks)                                       -->
<!-- ============================================================== -->

<task type="auto" tdd="true">
  <id>p6-spec-check-tolerance</id>
  <name>Task 16: spec_check.py tolerance 0.1 → 0.5mm + info/error severity + float-aware YAML</name>
  <files>tools/spec_check.py, tools/sla_lib/tests/test_spec_check_tolerance.py</files>
  <behavior>
  Per CONTEXT D8 + RESEARCH "Correction to D8":
  - Default `--tolerance-mm` 0.1 → 0.5
  - Severity buckets: <0.05mm silent; 0.05-0.5mm info (logged, non-blocking); >0.5mm error (exit 1, blocking)
  - YAML slot-positions accept floats with 1 decimal place (e.g. `x_mm: 12.5`); existing parser does `float(...)` already — verify no schema-side rejects
  - SCHEMA.md update is Task 17 (decoupled)
  </behavior>
  <action>
  RED: Add `tools/sla_lib/tests/test_spec_check_tolerance.py`:
  - drift = 0.0mm: silent (no output mentioning the slot)
  - drift = 0.03mm (< 0.05): silent
  - drift = 0.2mm (info range): emits "info:" prefix, exit 0
  - drift = 0.45mm (info range, near boundary): emits info, exit 0
  - drift = 0.6mm: emits "error:" prefix, exit 1
  - drift = 1.0mm: error, exit 1
  - YAML slot with `x_mm: 12.5` (float, 1 decimal) parses correctly
  - YAML slot with `x_mm: 12` (int, legacy) still parses correctly
  - --tolerance-mm 0.1 (legacy override) restores old behavior

  GREEN: Edit `tools/spec_check.py`:
  - Change default `--tolerance-mm` from 0.1 to 0.5 (current line ~178)
  - Refactor drift-classification into severity buckets:
     ```python
     def _classify(drift_mm: float, tolerance_mm: float) -> str:
         if drift_mm < 0.05: return "silent"
         if drift_mm <= tolerance_mm: return "info"
         return "error"
     ```
  - Output format: prefix lines with `info:` or `error:` accordingly; silent rows omitted entirely
  - Exit-code logic: 1 only if any "error" found; "info" alone → exit 0
  - Verify YAML parsing accepts floats (existing code already coerces; test inline)

  Update CLI help text to describe severity buckets.
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/test_spec_check_tolerance.py -v && python3 tools/spec_check.py --all 2>&1 | head -20</automated>
  </verify>
  <done>
  - Default tolerance is 0.5mm
  - 3 severity buckets implemented (silent/info/error)
  - ≥9 tests in test_spec_check_tolerance.py, all green
  - YAML float-coordinate parsing verified by test
  - All existing tests green
  </done>
  <commit>12: feat(spec_check): tolerance 0.5mm with info/error severity buckets</commit>
</task>

<task type="auto">
  <id>p6-schema-update</id>
  <name>Task 17: Update templates/_specs/SCHEMA.md with constraint-prose convention + float slot table</name>
  <files>templates/_specs/SCHEMA.md</files>
  <action>
  Per ISSUE.md §C + CONTEXT D6 + RESEARCH §"spec_check tolerance update": document the new conventions in SCHEMA.md.

  Edits:

  1. **Constraints section convention** (§C in ISSUE.md):
     - Specs describe constraints in PROSE only (no parallel YAML)
     - Reference Code-CONSTRAINTS by name, e.g. "see CONSTRAINTS['themen_row_alignment'] in build.py"
     - Brand-Constraints automatically active; do NOT repeat in spec
     - If a template waives a brand rule, the spec mentions it AND meta.yml has `brand_overrides`

  2. **Slot table convention** (D8):
     - Slot positions accept floats with 1 decimal place: `x_mm: 12.5`
     - Drift severity: <0.05mm silent, 0.05-0.5mm info, >0.5mm error
     - Default tolerance is 0.5mm; legacy 0.1mm available via `--tolerance-mm 0.1`

  3. **`brand_overrides` in meta.yml** (D5):
     - List of `{id, reason}` pairs
     - id matches `^brand:[a-z_0-9]+$`
     - reason required (non-empty); explanation visible in CI report
     - Schema-validated via `tools/sla_lib/builder/meta_schema.py`

  4. **Worked example** referencing the existing themen-plakat spec — show how a constraint reads in prose with a code-name reference.

  Length: ~150-300 lines added/modified. Existing SCHEMA.md content stays intact unless contradicted.

  Self-consistency: SCHEMA.md ITSELF is a spec-style doc. The Constraints section convention applies to SCHEMA.md too (it should describe its own constraints in prose, not parallel YAML).

  No code changes; this is pure docs.
  </action>
  <verify>
    <automated>test -f templates/_specs/SCHEMA.md && grep -q "brand_overrides" templates/_specs/SCHEMA.md && grep -q "0.5mm" templates/_specs/SCHEMA.md && grep -q "CONSTRAINTS" templates/_specs/SCHEMA.md && python3 tools/spec_check.py --all 2>&1 | tail -5</automated>
  </verify>
  <done>
  - SCHEMA.md mentions Constraints-prose convention with worked example
  - SCHEMA.md describes float-aware slot tables, severity buckets, default 0.5mm
  - SCHEMA.md describes meta.yml brand_overrides format
  - No SLA byte changes (docs-only); spec_check still green on all 8 specs
  </done>
  <commit>12: docs(schema): document Constraint-prose convention + 0.5mm tolerance + brand_overrides</commit>
</task>

<task type="auto">
  <id>p6-spec-writing-guide</id>
  <name>Task 18: Author shared/brand/SPEC-WRITING-GUIDE.md (~2500 German words)</name>
  <files>shared/brand/SPEC-WRITING-GUIDE.md</files>
  <action>
  Per ISSUE §B + CONTEXT D6 + RESEARCH §"Spec-Writing-Guide content (D6)" + ecosystem §5: author the long-form authoring guide.

  Target: `shared/brand/SPEC-WRITING-GUIDE.md`, ~2500 German words. Sections:

  1. **Einleitung** — wer schreibt Specs, wie werden sie gelesen (~150 Wörter)
  2. **Pflicht-Sektionen** (~600 Wörter)
     - Funktional: Audience, Use-Case, CTA, Druck-Output
     - Visuell: Layout-Philosophie, Hierarchie-Order, Brand-Akzente, Hero-Color
     - Strukturell: Trim/Bleed/Falz mm, Slot-Tabelle, Lese-Reihenfolge
     - Constraints (Prosa): Verweis auf CONSTRAINTS list im build.py
  3. **Empfohlen-Sektionen** (~250 Wörter)
     - Druckpraxis (Spot-Colors, Min-DPI, Druckerei-Anforderungen)
     - Endnutzer:innen-Workflow (welche Slots häufig ersetzt, welche nie)
  4. **Optional-Sektionen** (~150 Wörter)
     - Robustheit (Übertext-Verhalten, häufige Fehler)
     - Provenance (owner, version)
  5. **Wie schreibt man jeden Abschnitt gut?** — Mini-Anleitung + Beispiel + Anti-Pattern (~500 Wörter)
  6. **Construct-then-add Konvention** — wichtig für CONSTRAINTS list, mit Beispiel (~150 Wörter)
     - Cite RESEARCH P-INLINE-FRAME: warum `page.add(TextFrame(...))` inline NICHT funktioniert
     - Beispiel: korrekt `frame = TextFrame(...); page.add(frame); CONSTRAINTS = [same_y(frame, ...)]`
  7. **Brand-Override-Konvention** — wann brand_overrides in meta.yml gerechtfertigt ist (~150 Wörter)
     - Format mit `{id, reason}`; reason muss erklärend sein, nicht "siehe Spec"
     - Worked example aus Phase 4 (Türanhänger HL/SL spacing override)
  8. **Worked Example** — themen-plakat: eine Slot-Beschreibung in der Spec → Code-Constraint mit benanntem Identifier → Spec-Prosa die per Name referenziert (~250 Wörter)
  9. **Review-Checklist** — 10-15 Ja/Nein-Fragen vor Implementation-Freigabe (~150 Wörter)
  10. **Common Pitfalls** — aus #10/#11/#13 retro (RESEARCH "Common Pitfalls" Top-10) (~250 Wörter)

  Total: ~2500 words. Calibration source: ecosystem §5 (Carbon-style 200-400 words/section).

  Sprache: Deutsch. Imperativer Ton wo passend ("Beschreibe...", "Verwende keine..."). Anti-Pattern-Boxen.

  Do NOT teach the constraint-DSL syntax (that lives in module docstrings + SCHEMA.md). Teach how to TALK about constraints in spec prose and reference them by name.

  Meta-Konsistenz: das Dokument folgt selbst dem eigenen Schema (Pflicht/Empfohlen/Optional Sektionen mit Worked Examples).

  No "claude" attribution. No emojis.
  </action>
  <verify>
    <automated>test -f shared/brand/SPEC-WRITING-GUIDE.md && wc -w shared/brand/SPEC-WRITING-GUIDE.md && grep -c "##" shared/brand/SPEC-WRITING-GUIDE.md && grep -q "construct-then-add\|construct-then-add Konvention" shared/brand/SPEC-WRITING-GUIDE.md && grep -q "brand_overrides" shared/brand/SPEC-WRITING-GUIDE.md && grep -q "CONSTRAINTS" shared/brand/SPEC-WRITING-GUIDE.md && ! grep -qi claude shared/brand/SPEC-WRITING-GUIDE.md</automated>
  </verify>
  <done>
  - shared/brand/SPEC-WRITING-GUIDE.md exists, ~2500 German words (range 2200-3000 ok)
  - All 10 sections present
  - Construct-then-add convention documented with example
  - Brand-Override-Konvention documented with example from Phase 4
  - Worked example from themen-plakat present
  - Review checklist with 10-15 questions
  - Common Pitfalls top-10 from RESEARCH
  - No "claude" attribution, no emojis
  - Self-consistent with own schema
  </done>
  <commit>12: docs(brand): add SPEC-WRITING-GUIDE for template authoring</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 7 — CI INTEGRATION + FINAL VERIFY (1 task)                 -->
<!-- ============================================================== -->

<task type="auto">
  <id>p7-ci-final-verify</id>
  <name>Task 19: CI workflow step + full verification suite</name>
  <files>.github/workflows/pages.yml</files>
  <action>
  Per CONTEXT D11 + RESEARCH "CI Integration": wire structural_check into CI.

  1. Edit `.github/workflows/pages.yml` — add a step AFTER existing `tools/check_ci.py` and BEFORE the gallery build:
     ```yaml
     - name: Run structural check
       run: |
         set -euo pipefail
         python3 -m sla_lib.builder.structural_check --all
     ```
     Performance budget: <30s for all 8 templates (CONTEXT D11; ecosystem §10 estimates ~8s).

  2. Run the full verification suite locally to confirm green state:
     - `python3 -m pytest tools/sla_lib/tests/` — all green
     - `python3 -m sla_lib.builder.structural_check --all` — exit 0
     - `python3 tools/spec_check.py --all` — exit 0 (no errors; info-level drift OK)
     - `python3 tools/sla_diff.py --strict --allow-brand-extras` — exit 0 on 3 production
     - `bin/check-stale-previews` — green
     - `bin/validate` — green (full orchestrator)
     - SHA stability: rebuild all 8, compare SHAs to Task 6 post-state — IDENTICAL

  3. Spot-check render gallery on 1-2 templates for visual sanity (no regressions):
     - `bin/render-gallery themen-plakat-a3-quer`
     - `bin/render-gallery wahlaufruf-postkarte-a6-quer`
     - Visual diff vs main: no perceptual changes expected (SHA-stable refactors).

  No new dependencies. No new tools. No CI minutes added beyond ~10s.
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/ && python3 -m sla_lib.builder.structural_check --all && python3 tools/spec_check.py --all && python3 tools/sla_diff.py --strict --allow-brand-extras && bin/check-stale-previews && bin/validate && grep -q "structural_check" .github/workflows/pages.yml</automated>
  </verify>
  <done>
  - `.github/workflows/pages.yml` has `structural_check --all` step before gallery build
  - All 6 verification commands above exit 0 locally
  - SLA SHAs unchanged from Task 6 post-state on all 8 templates
  - Visual spot-check of 1-2 templates: no regressions vs main
  - Total local verification time <2min (CI total <30s structural_check budget; full suite <5min)
  </done>
  <commit>12: ci(structural): wire structural_check --all into pages.yml workflow</commit>
</task>

<!-- ============================================================== -->
<!-- PHASE 8 — SHIP (1 task)                                          -->
<!-- ============================================================== -->

<task type="auto">
  <id>p8-ship-pr</id>
  <name>Task 20: Open PR with full description; do NOT merge</name>
  <files></files>
  <action>
  Per "Don't merge yourself — open PR only" (issue prompt hard rule).

  1. Final verification one more time (paranoia gate):
     - `python3 -m pytest tools/sla_lib/tests/`
     - `python3 -m sla_lib.builder.structural_check --all`
     - `python3 tools/spec_check.py --all`
     - `python3 tools/sla_diff.py --strict --allow-brand-extras`
     - `bin/check-stale-previews`
     - `bin/validate`
     - SHA stability re-confirmed for all 8 templates

  2. Commit any final adjustments with `12: chore: ...` if needed (minor cleanup; do NOT amend prior commits).

  3. Push branch: `git push -u origin issue/12-spec-system-v2-...`

  4. Open PR with `gh pr create`:
     - Title: `12: Spec-System v2 — Constraint-DSL + Spec-Writing-Guide + spec_check tolerances`
     - Body: structured description with Summary, Phases-Recap, Verification, Out-of-Scope, Notes
     - Use HEREDOC for body to preserve formatting
     - Reference `Closes #23` (issue's source github URL is https://github.com/GrueneAT/vorlagen/issues/23)

  PR body sections:
  - **Summary** — 3-5 bullets
  - **Phases delivered** — Phase 1 DSL Foundation; Phase 2 build_doc() contract; Phase 3 vorzeige; Phase 4 brand-discovery + overrides; Phase 5 fan-out; Phase 6 polish; Phase 7 CI
  - **Verification** — checklist of green commands
  - **Backwards-compat** — SLA bytes byte-stable across all 8; round-trip diff green on production
  - **Out of scope** — solver, auto-fix, plugin registry (deferred items from CONTEXT)
  - **Notes** — any rough-edges-noted, follow-up issues to file

  Do NOT auto-merge. Do NOT request review explicitly. Wait for human review.

  Per memory rule: NO "claude" attribution anywhere in the PR.
  </action>
  <verify>
    <automated>python3 -m pytest tools/sla_lib/tests/ && python3 -m sla_lib.builder.structural_check --all && python3 tools/spec_check.py --all && python3 tools/sla_diff.py --strict --allow-brand-extras && bin/check-stale-previews && bin/validate && git log --oneline -20 | head && gh pr view 2>&1 | head -30</automated>
  </verify>
  <done>
  - All verification commands green
  - Branch pushed to origin
  - PR open against main with structured body
  - PR title format `12: Spec-System v2 — ...`
  - PR body references "Closes #23"
  - PR NOT auto-merged
  - No "claude" attribution anywhere in PR or commits
  </done>
  <commit>12: chore: open PR for spec-system-v2 review</commit>
</task>

</tasks>

<verification>
After all tasks, run final checks (also embedded in Task 19 + Task 20):
- `python3 -m pytest tools/sla_lib/tests/` — all unit tests green (≥100 new tests added)
- `python3 -m sla_lib.builder.structural_check --all` — exit 0; <30s wall time
- `python3 tools/spec_check.py --all` — exit 0; info-level drift OK
- `python3 tools/sla_diff.py --strict --allow-brand-extras` — exit 0 on 3 production templates
- `bin/check-stale-previews` — exit 0 (previews_for_sla SHA stable)
- `bin/validate` — exit 0 (full orchestrator)
- SHA stability: each of the 8 `templates/<slug>/template.sla` SHAs at Phase 7 == SHAs at Phase 2 (Task 6 baseline)
- Spot-check `bin/render-gallery` on themen-plakat + wahlaufruf-postkarte — no visual regressions vs main
- No "claude" attribution in code, commits, or PR body (memory rule)
</verification>

<success_criteria>
Maps 1:1 to acceptance criteria from ISSUE.md:

- [x] **Constraint-DSL Composite-Blöcke** (Task 2): AlignedRow, AlignedColumn, MirroredPair, EqualGapStack, GridCell, HierarchyBlock as @dataclass with emit() — ≥6 tests/Composite ✓
- [x] **Free-form Constraints** (Task 3): same_y/same_x/same_size, mirrored_x/y, inside, same_style, distance_x/y, equal_gap, hierarchy as factories returning Constraint — ≥4 tests/Constraint ✓
- [x] **Brand-Constraints** (Task 4): 8 rules from QUICKGUIDE-NOTES.md auto-applied via BRAND_CONSTRAINTS list ✓
- [x] **`tools/structural_check.py`** (Task 5): imports build_doc(), walks primitives, evaluates CONSTRAINTS + BRAND_CONSTRAINTS, markdown report, exit 0/1 ✓ (lives at `tools/sla_lib/builder/structural_check.py`, callable as `python3 -m sla_lib.builder.structural_check`)
- [x] **Wired into `bin/validate`** (Task 19): CI step in pages.yml; bin/validate continues to call sub-tools ✓
- [x] **Refactor of 8 existing Templates** (Tasks 7, 9-15): Composite + CONSTRAINTS lists; SLA bytes byte-stable verified per-template ✓
- [x] **Spec-Writing-Guide** (Task 18): shared/brand/SPEC-WRITING-GUIDE.md with all sections from §B; ~2500 German words; meta-consistent ✓
- [x] **SCHEMA.md updated** (Task 17): constraint-prose convention + float slot table + brand_overrides format ✓
- [x] **`tools/spec_check.py` Tolerance-Tuning** (Task 16): 0.5mm tolerance, info/error severity, float slot positions, with tests ✓
- [x] **Visual review** (Task 19): SHA stability across 8 templates implies no visual regressions; spot-check render-gallery confirms ✓
- [x] **CI green** (Task 19/20): all tests passing, structural_check green, spec_check green, check-stale-previews green ✓

Plus hard rules from issue prompt:
- [x] No "claude" attribution (verified in Task 18 + Task 20)
- [x] Conventional commits `12: type(scope): subject` (every task's `<commit>`)
- [x] SLA bytes byte-stable across all 8 (Tasks 6, 7, 9-15 each verify SHA pre/post)
- [x] Round-trip diff green on 3 production templates (Tasks 13, 14, 15 verify)
- [x] No new runtime deps (jsonschema/Pillow/qrcode/pyzbar already installed; hypothesis test-only and skipped if missing)
- [x] PR opened, NOT merged (Task 20)
</success_criteria>
