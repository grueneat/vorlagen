# Codebase Research — Issue #14 (Constraint DSL: page-bounds, aligned_below, SpreadImage)

Issue worktree: `/root/workspace/.worktrees/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility/`
All paths below are relative to that worktree.

---

## 0. Executive findings (planner: read first)

1. **`inside_page` cannot live as a free-form `Constraint`** the way `inside`/`same_y` do — those resolve through `primitives_by_anname` and have no notion of "which page is this primitive on". `inside_page` MUST be evaluated against `(primitives, doc)` so it can iterate `doc.pages` and inspect `page.items`. The natural home is `tools/sla_lib/builder/brand_constraints.py` as a `BrandRule` subclass; the rule_id should be `brand:inside_page` so the existing `meta.yml::brand_overrides` regex `^brand:[A-Za-z_0-9.]+$` accepts it without schema changes.
   *Confidence: HIGH — verified by reading both `Constraint` and `BrandRule` signatures, plus the regex in `meta_schema.py`.*

2. **No `rotated_bbox` helper exists in the codebase today.** `rotation_deg` is read/written verbatim as a frame attribute in `primitives.py`, but no module computes the axis-aligned bbox of a rotated rectangle. The planner must add a helper (`_rotated_aabb_mm(x, y, w, h, angle_deg) -> (min_x, min_y, max_x, max_y)`), preferably in `brand_constraints.py` next to `_InsidePageRule`. Scribus rotation is around the frame's top-left corner (`XPOS/YPOS`), confirmed by the `LOCALROT="0"` defaults and the `ROT` attribute being emitted bare alongside `XPOS/YPOS` (no center-of-rotation attribute).
   *Confidence: HIGH for "no helper exists" (exhaustive grep). MEDIUM for "rotation around top-left" — this is the standard Scribus convention and matches how `_xy_pt(page)` returns the origin without rotation correction, but I have not run a Scribus round-trip to confirm.*

3. **`BrandRule.check(primitives, doc)` already gets `doc`.** That is sufficient context for `inside_page` to iterate `doc.pages` directly — the planner does NOT need to widen `iter_all_primitives()` or introduce a per-primitive `_owning_page` link. (Several brand rules already iterate `doc.pages` directly: `_LogoSize3MRule` reads `doc.pages[0]` for `kurze_kante`; `_Bleed3mmRule` iterates `doc.pages` for `bleed_mm`.)
   *Confidence: HIGH.*

4. **Master-page items must be exempt from `inside_page`.** `Page.items` is shared between doc pages and master pages (`doc.masters` are also `Page` instances per `document.py:106-122`). The Zeitung's master pages legitimately carry full-bleed background imagery placed at `(-bleed, -bleed)` to `(w+bleed, h+bleed)` — that is INSIDE bleed bounds, but the planner should still scope the rule explicitly to non-master pages so a future tighter tolerance does not silently break master-page authoring. Mirror the convention used by `_LogoSize3MRule` (only inspects `doc.pages[0]`, not masters).
   *Confidence: HIGH (read `Document.iter_all_primitives` at `document.py:413-425` and `Page` dataclass).*

5. **The two known overflowing frames in `templates/zeitung-a4-grun/build.py`:**
   - `page9.add(ImageFrame(... anname="P9 Spread"))` at **lines 1802-1811** — `x=209.99..., w=209.99..., h=126.14`. Right edge at `x+w ≈ 420 mm` on a 210 mm wide page. Massive overflow (≈ 207 mm past `w + bleed`).
   - `page11.add(ImageFrame(... [unnamed]))` at **lines 2061-2071** — `x=209.99..., y=-0.18, w=210.8, h=297.18`. Right edge at `x+w ≈ 420.8 mm` on a 210 mm wide page. Massive overflow.
   Both are attached to a left-facing page when they are intended as the right-page half of a spread. These are the two `inside_page` errors that #14 must accept via `meta.yml::brand_overrides` with reason "see issue #16".

6. **Tests are run via `unittest` from `tools/`.** No pytest dependency. Tests live in `tools/sla_lib/tests/test_*.py` and use `sys.path.insert(0, str(ROOT / "tools"))` at the top. `test_constraints.py` builds real `TextFrame` instances (not fakes) and calls `Constraint.check(primitives_by_anname={anname: frame})` directly. `test_brand_constraints.py` builds a real `Document`, calls `list(doc.iter_all_primitives())`, then `rule.check(prims, doc)`. The new tests should follow the brand-constraints pattern (real `Document` + real frames).

7. **No existing test pins a specific brand-violation count for `--all`.** `AllRealTemplatesIntegrationTests` (`test_structural_check.py:310-322`) only asserts `rep.fatal_error is None` — it does NOT pin which brand rules pass/fail. So adding `inside_page` as a brand rule does not break any pinned tests; the only CI surface that breaks if `inside_page` errors leak through is `pages.yml` which exits 1 on errors. The issue mandates: add `brand_overrides` for `brand:inside_page` in `templates/zeitung-a4-grun/meta.yml` to keep `pages.yml` green, with reason citing #16.

8. **`SpreadImage` belongs in `blocks.py` next to `WahlkreuzSymbol` / `FoldedPanel`.** Existing block convention: dataclass with `emit(self, page=None)` (or no-arg), yields primitives. Some blocks already accept page references (`FoldLine.emit(page)`, `DieCut.emit(page)`). The convention for naming spreads-of-two: `<base> · left` and `<base> · right` (anname suffixes joined with " · ").

9. **`aligned_below` factory is straightforward** — it is a per-template free-form constraint exactly like `distance_y` + `same_x` collapsed into one. It lives in `constraints.py`, takes two anname references, and emits a single Violation if either x-drift or (y - (text.y + text.h + gap)) > tol. Tests follow `test_constraints.py` pattern.

10. **Documentation-surface lines:** `templates/_specs/SCHEMA.md` §12 "Constraints" at **line 484** (the catalog-of-factories enumeration is at **lines 493-495**). Add `inside_page`, `aligned_below` to that enumeration. `shared/brand/SPEC-WRITING-GUIDE.md` §5 "Constraints (Prosa)" at **line 154** is the canonical place for example-prose. The issue text says "§4" but that section is "Optional-Sektionen"; the planner should use §5 (or extend §8 "Worked Example") — I'll flag this as a docs ambiguity.

---

## 1. Interfaces

### 1.1 `tools/sla_lib/builder/constraints.py`

<interfaces>
# From tools/sla_lib/builder/constraints.py

# === Result types ===
@dataclass(frozen=True)
class Violation:
    severity: str           # "error" | "warning" | "info"
    message: str
    rule_id: str = ""
    targets: tuple = ()     # tuple of anname strings

@dataclass(frozen=True)
class Constraint:
    """Base — subclasses provide ``check``."""
    id: str
    targets: tuple
    name: str = ""
    def check(self, primitives_by_anname: dict) -> list:  # returns list[Violation]
        raise NotImplementedError
    def referenced_annames(self) -> tuple:
        return self.targets

# === Concrete subclasses (each frozen=True dataclass) ===
@dataclass(frozen=True)
class _SameAxisConstraint(Constraint):
    axis: str = "y"               # "y" or "x"
    tolerance_mm: float = 0.5

@dataclass(frozen=True)
class _SameSizeConstraint(Constraint):
    axis: str = "both"            # "both" | "w" | "h"
    tolerance_mm: float = 0.5

@dataclass(frozen=True)
class _MirroredConstraint(Constraint):
    axis: str = "x"               # "x" = vertical mirror line; "y" = horizontal
    axis_mm: float = 0.0
    tolerance_mm: float = 0.5

@dataclass(frozen=True)
class _InsideConstraint(Constraint):
    tolerance_mm: float = 0.5
    # check expects targets=(child_anname, parent_anname); both must resolve
    # to primitives — does NOT take a page reference.

@dataclass(frozen=True)
class _EqualGapConstraint(Constraint):
    axis: str = "y"               # "y" or "x"
    gap_mm: float = 0.0
    tolerance_mm: float = 0.5

@dataclass(frozen=True)
class _HierarchyConstraint(Constraint):
    by: str = "fontsize"

@dataclass(frozen=True)
class _SameStyleConstraint(Constraint):
    pass                          # compares ``.style`` attribute

@dataclass(frozen=True)
class _DistanceConstraint(Constraint):
    axis: str = "y"               # "y" or "x"
    equals: float = 0.0
    tolerance_mm: float = 0.5

# === Public factories (these are what templates call) ===
def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5,
              name: str = "") -> Constraint    # axis ∈ {"both","w","h"}
def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5,
               name: str = "") -> Constraint
def mirrored_y(top, bottom, axis_mm: float, tolerance_mm: float = 0.5,
               name: str = "") -> Constraint
def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def equal_gap(*targets, axis: str = "y", gap_mm: float, tolerance_mm: float = 0.5,
              name: str = "") -> Constraint
def hierarchy(*targets, by: str = "fontsize", name: str = "") -> Constraint
def same_style(*targets, name: str = "") -> Constraint
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint

# === Helpers ===
def _to_anname(t) -> str:
    """Accept a string or any object with .anname (raises if anname missing)."""
def _norm(targets) -> tuple:
    """Apply _to_anname across a tuple."""
def _autoname(kind: str, targets: tuple, name: str) -> str:
    """Build the constraint id; templates rarely need this."""
def _resolve(targets: tuple, mapping: dict) -> tuple[list, list]:
    """Look up each target in mapping; returns (resolved_frames, missing_names)."""
def _missing_violation(rid: str, targets: tuple, missing: list) -> Violation:
    """Build the standard 'references missing anname(s)' warning."""
</interfaces>

**Returned list semantics:** `Constraint.check()` returns `list[Violation]`. Empty list ⇒ pass. A single Violation with `severity="warning"` is the standard for missing-anname references; everything else is `severity="error"`.

### 1.2 `tools/sla_lib/builder/brand_constraints.py`

<interfaces>
# From tools/sla_lib/builder/brand_constraints.py

@dataclass(frozen=True)
class BrandRule:
    """A brand-CI constraint over a built Document.
    ``check(primitives, doc)`` walks the primitive list and inspects the
    doc-level metadata as needed.
    """
    id: str
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc) -> list:  # returns list[Violation]
        raise NotImplementedError

# === Concrete rules (all @dataclass(frozen=True), all subclasses of BrandRule) ===
@dataclass(frozen=True)
class _ColorPaletteRule(BrandRule): ...        # checks fill/line_color/fcolor
@dataclass(frozen=True)
class _FontFamilyRule(BrandRule): ...          # TextFrame.font allowlist
@dataclass(frozen=True)
class _LineSpacingRule(BrandRule):
    factor: float = 0.9
    tolerance_pt: float = 0.5
@dataclass(frozen=True)
class _HlSlDistanceRule(BrandRule):
    baseline_mm: float = 5.4
    tolerance_mm: float = 1.0
@dataclass(frozen=True)
class _LogoSize3MRule(BrandRule):
    factor: float = 3.0
    tolerance_mm: float = 0.5
    # Reads doc.pages[0] for kurze_kante; uses PT_TO_MM from document.py
@dataclass(frozen=True)
class _TextOnGreenRule(BrandRule):
    green_colors: tuple = ("Dunkelgrün", "Hellgrün")
@dataclass(frozen=True)
class _Bleed3mmRule(BrandRule):
    expected_mm: float = 3.0
    tolerance_mm: float = 0.01
    # Iterates doc.pages, reads p.bleed_mm
@dataclass(frozen=True)
class _WahlkreuzColoredBgRule(BrandRule):
    allowed: tuple = ("Dunkelgrün", "Hellgrün", "Magenta")

# === Module-level registry (8 rules today) ===
BRAND_CONSTRAINTS: list[BrandRule] = [
    # All instantiated via _make_rule(cls, id="brand:...", name=..., description=...)
    _ColorPaletteRule(...),
    _FontFamilyRule(...),
    _LineSpacingRule(...),
    _HlSlDistanceRule(...),
    _LogoSize3MRule(...),
    _TextOnGreenRule(...),
    _Bleed3mmRule(...),
    _WahlkreuzColoredBgRule(...),
]

# === Helpers ===
def _allowed_colors(doc) -> set[str]
def _all_para_styles(doc) -> dict
def _make_rule(cls, **kwargs) -> BrandRule
</interfaces>

**Frozen-dataclass gotcha:** `BrandRule` is `@dataclass(frozen=True)`. Subclasses that add fields (e.g. `_LineSpacingRule.factor`) must use `field(default=...)`-friendly syntax inside `@dataclass(frozen=True)`. The `_make_rule(_LogoSize3MRule, id="brand:logo_size_3M", name=..., description=...)` pattern shows that the standard kwargs (`id`, `name`, `description`, `severity`) must all be passed to the constructor — frozen dataclasses do not allow `__post_init__` mutation. The new `_InsidePageRule` should follow the same constructor-injection pattern.

### 1.3 `tools/sla_lib/builder/structural_check.py`

<interfaces>
# From tools/sla_lib/builder/structural_check.py

@dataclass
class CheckIssue:
    severity: str        # "error" | "warning" | "info" | "pass" | "skip"
    rule_id: str
    message: str
    location: str = ""   # comma-joined targets

@dataclass
class TemplateReport:
    slug: str
    constraint_issues: list[CheckIssue] = field(default_factory=list)
    brand_issues: list[CheckIssue] = field(default_factory=list)
    skipped_brand_rules: list[tuple[str, str]] = field(default_factory=list)
    fatal_error: Optional[str] = None
    @property
    def has_errors(self) -> bool: ...
    def to_markdown(self) -> str: ...

def check_template(slug: str, root: Path = _REPO_ROOT) -> TemplateReport
def discover_template_slugs(root: Path = _REPO_ROOT) -> list[str]
def main(argv: Optional[list[str]] = None) -> int  # CLI entry; exit code 0/1

# Internal:
def _load_build_module(slug: str, root: Path = _REPO_ROOT)  # importlib spec_from_file_location
def _violation_to_issue(v, default_rule_id: str) -> CheckIssue
def _report_to_dict(rep: TemplateReport) -> dict           # for --json
_EXCLUDED_DIRS = {"_specs", "_smoke"}                     # discovery filter
</interfaces>

**Walk semantics (structural_check.py:152-223):**
1. Import template's `build.py`, call `mod.build_doc()` ⇒ `doc`
2. `primitives = list(doc.iter_all_primitives())` (flat list, masters first then doc pages)
3. `primitives_by_anname = {p.anname: p for p in primitives if p.anname}`
4. Evaluate template's `mod.CONSTRAINTS` list (free-form constraints) — each `c.check(primitives_by_anname)` produces `list[Violation]`
5. Load `meta.yml::brand_overrides` IDs via `load_brand_overrides(slug, root)`
6. For each rule in `BRAND_CONSTRAINTS`: skip if id in override-set, else `rule.check(primitives, doc)`

### 1.4 `tools/sla_lib/builder/meta_schema.py`

<interfaces>
# From tools/sla_lib/builder/meta_schema.py

# JSON-Schema for brand_overrides (lines 23-40)
_BRAND_OVERRIDE_SCHEMA: dict = {
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "reason"],
        "properties": {
            "id": {"type": "string", "pattern": r"^brand:[A-Za-z_0-9.]+$"},
            "reason": {"type": "string", "minLength": 1},
        },
    },
}

def load_brand_overrides(slug: str, root: Path | None = None) -> set[str]
    """Returns the SET of override IDs (just the strings).
    - Returns empty set if meta.yml is absent or has no brand_overrides field.
    - Raises ValueError on jsonschema validation failure.
    - Emits a warnings.warn (not error) for IDs not present in BRAND_CONSTRAINTS.
    """

def _meta_path(slug: str, root: Path | None = None) -> Path
def _validate_and_collect_ids(overrides: Any, path: Path) -> set[str]
</interfaces>

### 1.5 `tools/sla_lib/builder/primitives.py`

<interfaces>
# From tools/sla_lib/builder/primitives.py

@dataclass
class _Frame:
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 50
    h_mm: float = 30
    anchor: Optional[Anchor] = None        # if set, x_mm/y_mm ignored at emit time
    rotation_deg: float = 0                # frame rotation around top-left corner
    layer: int = 2                         # default Text layer
    anname: str = ""                       # SLA ANNAME — Constraint targets resolve to this
    custom_path: Optional[str] = None
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    # Verbatim pt overrides (round-trip-byte-stable hatch)
    xpos_pt: Optional[float] = None
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""               # ParaStyle.PARENT
    fcolor: str = ""              # frame-default fill color (read by brand rules)
    runs: Optional[list] = None   # list of Run, or legacy (text, dict, sep) tuples
    columns: int = 1
    col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None   # ALIGN
    text_align: Optional[int] = None            # deprecated alias
    default_linesp_mode: Optional[int] = None
    trail_style: Optional[str] = None
    trail_attrs: Optional[dict] = None
    fill: Optional[str] = None         # PCOLOR
    line_color: Optional[str] = None   # PCOLOR2
    line_width_pt: float = 0
    default_style_attrs: Optional[dict] = None
    next_item: Optional["TextFrame"] = field(default=None, repr=False, compare=False)
    _preallocated_id: Optional[int] = field(default=None, repr=False, compare=False)
    def link_to(self, other: "TextFrame") -> "TextFrame": ...

@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE
    image: str = ""           # alias for src
    layer: int = 1            # default Bilder layer
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)   # ← key field for SpreadImage
    local_rotation_deg: float = 0.0
    scale_type: int = 1       # SCALETYPE: 1 = fit-to-frame, 0 = free / aspect-locked
    ratio: int = 1
    pic_art: int = 1
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None  # "png" | "jpg"

@dataclass
class Polygon(_Frame):
    fill: str = "Black"               # PCOLOR
    line_color: Optional[str] = None  # PCOLOR2
    line_width_pt: float = 0
    layer: int = 0                    # default Hintergrund
    shape: str = "rectangle"          # 'rectangle' | 'ellipse'
    fill_shade: int = 100
    dash_pattern: Optional[tuple[float, ...]] = None
</interfaces>

**Critical for `inside_page`:**
- `_Frame.anchor` may override `x_mm/y_mm` at emit time — but for built-doc inspection, the constraint can read `frame.x_mm` and `frame.y_mm` (anchor resolution is a render-time concern, not a stored-coordinate concern; the corpus templates set `x_mm`/`y_mm` directly, the round-tripped `templates/zeitung-a4-grun/build.py` has zero anchor uses).
- `_Frame.xpos_pt`/`width_pt` overrides bypass mm — for round-tripped frames carrying these, the constraint should prefer `width_pt / MM_TO_PT` if `width_pt is not None`, else `w_mm`. Same for `height_pt`. This is needed for the Zeitung's `page12.add(ImageFrame(...))` Wahlkreuz at lines 2251-2267 which carries `xpos_pt=...`, `width_pt=...`, etc.
- `_Frame.rotation_deg` is in degrees, may be any float, rotation around top-left.

### 1.6 `tools/sla_lib/builder/document.py`

<interfaces>
# From tools/sla_lib/builder/document.py

# Constants
MM_TO_PT = 72.0 / 25.4              # ≈ 2.83464566929...
PT_TO_MM = 25.4 / 72.0              # ≈ 0.352777777777...

@dataclass
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float = 3.0
    margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10)  # L,R,T,B
    master_name: str = ""
    label: str = ""
    items: list = field(default_factory=list)
    own_page: int = 0
    page_xpos_pt: float = 0
    page_ypos_pt: float = 0
    is_left: bool = False           # facing-pages layout
    is_master: bool = False         # ← True for MasterPage, False for doc page
    master_id: str = ""
    def add(self, item) -> "Page":  # expands blocks via item.emit()

class Document:
    pages: list[Page]               # doc pages
    masters: list[Page]             # master pages
    facing_pages: bool
    # ... many other fields
    def add_master(self, name="Normal", size="A4", orientation="portrait",
                   bleed_mm=3.0, margins_mm=(10,10,10,10), facing="right",
                   page_xpos_pt=None, page_ypos_pt=None,
                   width_pt=None, height_pt=None) -> Page
    def add_page(self, size="A4", orientation="portrait", bleed_mm=3.0,
                 margins_mm=(10,10,10,10), master="Normal", label="",
                 page_xpos_pt=None, page_ypos_pt=None,
                 width_pt=None, height_pt=None) -> Page
    def iter_all_primitives(self) -> Iterable:
        """Yields primitives from masters then doc pages, in page.items order.
        Does NOT yield page references — primitives are bare."""
    def save(self, path) -> None
    # ...

def mm_to_pt(value_mm: float) -> float
def resolve_size(size: str | tuple[float, float], orientation: str) -> tuple[float, float]
def _fmt_num(value: float) -> str
ISO_SIZES_MM: dict[str, tuple[float, float]]    # A0..A7 portrait
</interfaces>

**Page width/height in mm.** `Page` only stores `width_pt`/`height_pt`. To get mm: `page.width_pt * PT_TO_MM`. Already used in `_LogoSize3MRule.check()` at `brand_constraints.py:240-242`.

---

## 2. The page-bounds problem in code (literal lines)

The two known overflowing frames in `templates/zeitung-a4-grun/build.py`:

### 2.1 "P9 Spread" — print page 10 (`page9` zero-indexed)

Lines **1802-1811**:

```python
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
```

- Page9 is added at `templates/zeitung-a4-grun/build.py:184-193` with size `(210, 297)` mm and `bleed_mm=3.0`.
- Right edge of frame: `x + w ≈ 419.9999... mm` ≫ `w + bleed = 213 mm`.
- Page9 carries `master='Neue Musterseite links'`, i.e. it is a LEFT-facing page in the spread for print pages 10/11. The image is intended as the spread image bridging pages 10 and 11 — it should be the LEFT half on page9 (right half on page10), but the original SLA placed the entire 420 mm image on the left page anchored at x=210 (which is the right edge of the left page). The intended fix in #16 is to use `SpreadImage` to emit two frames, one per page.

### 2.2 Unnamed full-A4 image — print page 12 (`page11` zero-indexed)

Lines **2061-2071**:

```python
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
```

- Page11 is added at `templates/zeitung-a4-grun/build.py:204-213`.
- Frame right edge: `x + w ≈ 420.8 mm` ≫ `w + bleed = 213 mm`.
- This frame is unnamed (`anname=""`) — the existing brand rules cannot reference it.
- `inside_page` violations should NOT skip unnamed frames; the rule must inspect every primitive on every doc page regardless of anname. The Violation message should fall back to a sensible identifier (frame index on page, or `f"<unnamed {type(frame).__name__} at ({x},{y})>"`).

### 2.3 Boundary cases that should be `warning`, not `error`

For reference — these are EXAMPLES from the same file that are *just* outside the trim but well inside `[-bleed, w+bleed]`:

- `templates/zeitung-a4-grun/build.py:1952-1961` — `page11` `ImageFrame(x=0, y=-0.18, w=210.8, h=213.9, fill='Dunkelgrün')`. Right edge `x+w ≈ 210.8` mm. With `bleed=3 mm`, `w + bleed = 213 mm` — INSIDE bounds. Top edge `y = -0.18 mm` ≥ `-bleed = -3 mm` ⇒ INSIDE. This frame is FINE under `inside_page` even though it bleeds past trim; it stays within `[-bleed, w+bleed]`. No violation.
- The 0.5 mm-tolerance "warning" bucket exists for sub-mm float drift (Scribus exports often round at the 5th-decimal); the planner should test the ≤ 0.5 mm bleed-edge nudge case explicitly so the warning/error split is unambiguous.

### 2.4 What "intended-correct" looks like (target for #16)

Page9 is a left page in the spread (print 10) and page10 is the corresponding right page (print 11). A correct `SpreadImage` would:
- Emit ImageFrame on page9 at `(0, 0, 210, 126.14)` with `local_offset_mm=(0, 0)` and `local_scale=(0.5, 1.0)` (or symmetric), showing the LEFT half of the source image.
- Emit ImageFrame on page10 at `(0, 0, 210, 126.14)` with `local_offset_mm=(-210, 0)` and `local_scale=(0.5, 1.0)`, showing the RIGHT half.

But: `SpreadImage` is constraint-DSL-only here (#14 is foundation; #16 actually applies it). The planner does NOT need to fix the Zeitung spread — only ship `SpreadImage` as a tested utility and ship a doc snippet showing the migration recipe.

---

## 3. How rotation interacts with bbox (current state)

### 3.1 No existing rotation-aware bbox math

Verified by:

```
grep -rn "rotated_bbox\|rotated bbox" tools/sla_lib/   # no hits
grep -rn "math.cos\|math.sin"        tools/sla_lib/builder/   # only blocks.py:713-714
                                                              # (DoorHangerCutout circle path)
grep -rn "ROT\|rotation_deg"          tools/sla_lib/reader.py tools/sla_lib/editor.py
                                                              # no hits
```

`rotation_deg` is currently used only as a frame *attribute* round-tripped verbatim from SLA — written to `ROT="..."` in the emitted PAGEOBJECT (`primitives.py:637`, `:819`, `:882`). The reader/editor do not touch it.

### 3.2 What the planner must add

A helper `_rotated_aabb_mm(x: float, y: float, w: float, h: float, angle_deg: float) -> tuple[float, float, float, float]` that returns `(min_x, min_y, max_x, max_y)`. Recommended:
- Place in `brand_constraints.py` as a private module-level helper next to `_InsidePageRule` (keeps the rotation math co-located with the only consumer).
- Rotation is around the frame's top-left corner (Scribus convention — `ROT` attribute on PAGEOBJECT, with no separate center-of-rotation attribute; `LOCALROT` is for the image *content* inside the frame, not the frame).
- For `angle_deg == 0` (the overwhelming default), return `(x, y, x+w, y+h)` directly to avoid float fuzz. Almost every frame in the corpus has `rotation_deg == 0`; only the Plakat A1 Impressum carries 270° (rotated vertical).

### 3.3 Two corpus references for rotation

- `tools/sla_lib/builder/blocks.py:208` — `Impressum.rotation_deg: float = 0` — the only block-level rotation parameter; the Plakat A1 Impressum sets it to 270.
- `tools/sla_lib/builder/blocks.py:813` — legacy `StoererBadge.rotation_deg: float = 8` — eight-degree slant on a circular badge.

These are evidence that rotation is real and the test must cover non-zero-rotation cases (the issue requires "rotation handling"). Suggested test cases: 0°, 90°, 180°, 270°, 45° (covering exact-angle vs. arbitrary).

---

## 4. How `meta.yml::brand_overrides` skipping works today

### 4.1 Flow

1. `templates/<slug>/meta.yml` carries top-level YAML key `brand_overrides:` — a list of `{id, reason}` objects.
2. `meta_schema.load_brand_overrides(slug, root)` (signature in §1.4 above):
   - Reads `templates/<slug>/meta.yml`.
   - Parses YAML; errors raise `ValueError`.
   - Validates against `_BRAND_OVERRIDE_SCHEMA` via `jsonschema.validate(...)`.
   - Cross-references each `id` against `BRAND_CONSTRAINTS` (warning, not error, on unknown id).
   - Returns `set[str]` of override IDs.
3. `structural_check.check_template(slug, root)` calls `load_brand_overrides`, then for each `rule in BRAND_CONSTRAINTS`:
   - If `rule.id in skip_ids`: append to `rep.skipped_brand_rules` with reason from a separate dict, continue.
   - Else: `violations = rule.check(primitives, doc)` and convert to `CheckIssue`.
4. The `skipped_brand_rules` list rendering happens in `TemplateReport.to_markdown()` and `_report_to_dict()`.

### 4.2 Reason-string lookup

The validated `set[str]` from `load_brand_overrides` only carries IDs. The orchestrator separately re-reads `meta.yml` to build `overrides_with_reason: dict[str, str]` (`structural_check.py:194-200`). This is a small DRY violation but does not affect the `inside_page` flow.

### 4.3 Where the new `brand:inside_page` reference goes

If the planner names the rule `brand:inside_page`:
- The regex `^brand:[A-Za-z_0-9.]+$` matches: `brand:inside_page` ⇒ `i`, `n`, `s`, `i`, `d`, `e`, `_`, `p`, `a`, `g`, `e` — all allowed by `[A-Za-z_0-9.]+`. **Confirmed valid.**
- No schema change needed.
- `templates/zeitung-a4-grun/meta.yml` adds an entry under the existing `brand_overrides:` list:
  ```yaml
  brand_overrides:
    - id: brand:inside_page
      reason: >-
        P9 Spread (print page 10) and the unnamed full-A4 frame on print
        page 12 overflow the page right edge by ~210 mm. These are intentional
        round-trip-faithful captures from the upstream Scribus original; fix
        is tracked in issue #16 (use SpreadImage block + reattach unnamed
        image to its correct page).
  ```

### 4.4 Per-frame opt-out NOT supported by the override mechanism

The `brand_overrides` mechanism is rule-level, not frame-level. If a template wants to skip `inside_page` only for a specific frame (e.g. a deliberate overflow), it must skip the entire rule. The planner should call this out in the docs — there is no per-frame allowlist.

Alternative if per-frame opt-out is desired: the rule can short-circuit on a magic anname prefix (e.g. `_overflow:`) — but that is out-of-scope for #14 unless the issue text reverses; it doesn't.

---

## 5. Where `SpreadImage` slots in (`blocks.py` convention)

### 5.1 Existing blocks (`tools/sla_lib/builder/blocks.py`)

| Block | LOC | Public surface | Convention |
|---|---|---|---|
| `PageNumber` | 68-131 | `@dataclass`; `emit() -> Iterable` (no page arg). Trivial kwarg passthrough for SLA round-trip fidelity. | Yields ONE `TextFrame`. |
| `Impressum` | 142-270 | `@dataclass`; `emit() -> Iterable`. Heavy multi-shape dispatch (1-Run / 2-Run / 3-Run / `runs=` override). | Yields ONE `TextFrame`. |
| `PageBackground` | 279-351 | `@dataclass`; `emit() -> Iterable`; **also** classmethod `for_page(page_w_mm, page_h_mm, ...)` which returns a sized `_SizedPageBackground`. | Yields ONE `Polygon` covering trim+bleed. |
| `_SizedPageBackground` | 354-378 | Internal sized variant. | Yields ONE `Polygon`. |
| `ContactBlock` | 386-436 | `@dataclass`; `emit() -> Iterable`. | Yields ONE `TextFrame` with multiple Runs. |
| `ColumnTextStory` | 444-480 | `@dataclass`; `emit() -> Iterable`. Linked-frame text-flow (calls `link_to` between frames). | Yields **N TextFrames** (the chain). |
| `WahlkreuzSymbol` | 487-551 | `@dataclass`; `emit(self, page=None) -> Iterable`. D12 enforcement via `ValueError`. | Yields ONE `Polygon` + ONE `ImageFrame`. |
| `FoldLine` | 558-597 | `@dataclass`; `emit(self, page=None) -> Iterable`. | Yields ONE `Polygon` (line via `custom_path`). |
| `DieCut` | 604-640 | `@dataclass`; `emit(self, page=None) -> Iterable`. | Yields ONE `Polygon`. |
| `FoldedPanel` | 646-677 | `@dataclass`; `emit(self, page=None) -> Iterable`. **Accepts `children: list`** which it re-emits. | Yields N children + 1 `FoldLine`. |
| `DoorHangerCutout` | 684-720 | `@dataclass`; `emit(self, page=None) -> Iterable`. | Yields 2 `DieCut`s. |
| `TableTentFold` | 727-746 | `@dataclass`; `emit(self, page=None) -> Iterable`. | Yields 1 `FoldLine`. |

### 5.2 What the convention tells us

- **`emit()` signature varies.** Older blocks use `emit(self) -> Iterable`. Newer blocks (`WahlkreuzSymbol`, `FoldLine`, `FoldedPanel`, etc.) use `emit(self, page=None) -> Iterable` so they can read page dimensions. **`SpreadImage` should use `emit(self, page=None)` for forward compatibility.**
- **Page references are handed in by the caller, not stored on the block.** No existing block carries a `Page` reference as a dataclass field. The convention is: caller does `left_page.add(SpreadImage(...))` once, then `right_page.add(...)` ... — but that is wrong here because a `SpreadImage` is intrinsically two-page. The cleanest model:
  - Make `SpreadImage` a *two-page emitter* invoked once by the caller, taking both pages as constructor args.
  - Provide a method `add_to_pages()` that calls `left_page.add(...)` and `right_page.add(...)` directly with the appropriate frame.
  - OR: emit one frame at a time via two distinct blocks (`SpreadImage(...).left()` returns a single-page block, `.right()` similarly).
- **`anname` strategy.** Single-frame blocks default `anname` to a fixed string (`PageNumber.anname = "Seitenzahl"`). Multi-frame blocks vary: `WahlkreuzSymbol` derives `f"{self.anname} (Hintergrund)"` for the polygon (`blocks.py:525`). The issue mandates the same suffix-derivation pattern: `f"{base} · left"` and `f"{base} · right"`.
- **Construct-then-add still applies.** Per `SPEC-WRITING-GUIDE.md` §6, frames should be built as named locals first, then added. For `SpreadImage`, the cleanest form is:
  ```python
  spread = SpreadImage(left_page=page9, right_page=page10,
                      src="...", w_mm=2*210, h_mm=126.14, anname="P9 Spread")
  spread.add_to_pages()   # or: page9.add(spread.left); page10.add(spread.right)
  ```

### 5.3 Splitting one image across two frames via `local_offset_mm` / `local_scale`

Both fields are on `ImageFrame` (`primitives.py:769-771`):
```python
local_scale: tuple[float, float] = (1.0, 1.0)
local_offset_mm: tuple[float, float] = (0.0, 0.0)
```

These map to Scribus's `LOCALSCX/LOCALSCY` and `LOCALX/LOCALY` (mm-converted to pt at `primitives.py:807`). For a 2-page spread:
- Source image is `2*page_w × page_h`. Both frames are sized to `page_w × page_h`.
- Left frame: `local_offset_mm = (0, 0)`. The image's top-left aligns with frame's top-left.
- Right frame: `local_offset_mm = (-page_w, 0)`. The image is shifted left by one page-width so its right half shows in the frame.
- Both frames use `scale_type=0` (free / aspect-locked, so `local_scale` is honored) or `scale_type=1` (fit-to-frame, in which case `local_scale` is overridden by Scribus). For a spread that needs explicit local-scale control, `scale_type=0` is the right choice.

**Caveat — the issue mentions `local_offset_mm` for the split.** Confirmed: `local_offset_mm=(-page_w, 0)` is the standard pattern. With `scale_type=0` and `local_scale=(1, 1)`, the image is shown 1:1 and shifted by the offset.

### 5.4 SpreadImage — recommended dataclass shape (for the planner)

```python
@dataclass
class SpreadImage:
    left_page: Page
    right_page: Page
    src: str = ""              # PFILE; or use inline_image_data + inline_image_ext
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None
    full_w_mm: float = 0.0     # full spread width (typically 2 * page_w)
    full_h_mm: float = 0.0     # full spread height (typically page_h)
    page_w_mm: float = 0.0     # single-page width (used for offset)
    page_h_mm: float = 0.0     # single-page height
    layer: int = 1
    anname: str = "Spread"     # base; left/right get " · left"/" · right" suffix
    gutter_offset_mm: float = 0.0  # optional; subtracted from both halves' offset
    scale_type: int = 0
    line_width_pt: float = 0
    fill: Optional[str] = None
    def emit_pair(self) -> tuple[ImageFrame, ImageFrame]:
        """Return (left_frame, right_frame)."""
    def add_to_pages(self) -> None:
        """Convenience: page.add() each half."""
```

This signature matches how the issue describes inputs ("left page, right page, image src, full-spread `w_mm × h_mm`, optional gutter offset"). The planner is free to refine names.

---

## 6. Test patterns

### 6.1 Where tests live and how they run

- `tools/sla_lib/tests/test_*.py` — all unit tests live here.
- Each test file starts with:
  ```python
  ROOT = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(ROOT / "tools"))
  ```
  so it can `from sla_lib.builder import ...` regardless of cwd.
- Discovery happens via `unittest`. Convention: `python3 -m unittest discover -s tools/sla_lib/tests` from repo root, OR `python3 -m unittest tools.sla_lib.tests.test_X` (with `tools` on PYTHONPATH).
- The `pages.yml` workflow runs `python3 -m sla_lib.builder.structural_check --all` with `PYTHONPATH=tools`.

### 6.2 Constraint test pattern (`test_constraints.py`)

```python
def _frame(name, x=0, y=0, w=10, h=10, style="", fontsize=None):
    f = TextFrame(x_mm=x, y_mm=y, w_mm=w, h_mm=h, anname=name, style=style)
    if fontsize is not None:
        f.fontsize = fontsize       # post-hoc attr injection (TextFrame has no fontsize field)
    return f

def _by_anname(*frames) -> dict:
    return {f.anname: f for f in frames}

class SameYTests(unittest.TestCase):
    def test_happy_path_passes(self):
        a = _frame("A", y=10); b = _frame("B", y=10)
        v = same_y(a, b).check(_by_anname(a, b))
        self.assertEqual(v, [])
    # ...
```

Real `TextFrame` instances, not fakes. Each constraint factory has tests for: happy / violation / tolerance-edge / missing-anname / mixed-form / string-form.

For `aligned_below`: the test should mirror `DistanceYTests` and `SameXTests` patterns but combined.

### 6.3 Brand-rule test pattern (`test_brand_constraints.py`)

```python
def _doc(size="A6", orientation="portrait", bleed=3.0):
    d = Document(title="t", template_id="t")
    d.add_page(size=size, orientation=orientation, bleed_mm=bleed)
    return d

def _find_rule(rid):
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")

class Bleed3mmRuleTests(unittest.TestCase):
    def test_3mm_passes(self):
        d = _doc(bleed=3.0)
        rule = _find_rule("brand:bleed_3mm")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])
```

Real `Document` + real `Page` + real frames. The new `test_constraints_inside_page.py` should follow this pattern (since `inside_page` is a brand rule needing a real `doc`).

### 6.4 Integration test for `--all`

`AllRealTemplatesIntegrationTests` (`test_structural_check.py:310-322`) auto-skips unless every real template's `build.py` exposes `build_doc()`. As of 2026-05-08 this is already true (issue #12 wired it up). The test checks `rep.fatal_error is None` only — it does NOT pin which brand rules pass/fail.

The new "snapshot of `--all` output showing exactly 2 `inside_page` errors" requested in the issue is best implemented as a NEW test (e.g. `test_inside_page_real_templates.py`) that:
1. Calls `structural_check.check_template("zeitung-a4-grun", ROOT)` directly (NOT through the full `--all` discovery).
2. Asserts that — BEFORE the brand_overrides entry is added — the rep contains exactly 2 `brand:inside_page` errors at `P9 Spread` and the unnamed full-A4 image.
3. Asserts that — WITH the brand_overrides entry — `brand:inside_page` is in `rep.skipped_brand_rules`.

The synthetic-template tests in `test_structural_check.py` already show how to write a tmp-dir-scoped template tree with `_write_template`.

---

## 7. Documentation surfaces

### 7.1 `templates/_specs/SCHEMA.md` §6 (Constraint catalogue)

The issue text says "§6 (Constraint catalogue)" but **§6 in the actual file is "Background-Color Contract für Wahlkreuz"**. The constraint factory enumeration lives in **§12 "Constraints (Issue #12 — Spec-System v2)" at line 484**, specifically the parenthetical at lines 493-495:

> `(siehe tools/sla_lib/builder/constraints.py für die Factories: same_y, same_x, same_size, mirrored_x, mirrored_y, inside, equal_gap, hierarchy, same_style, distance_x, distance_y).`

Add `inside_page` and `aligned_below` to this list. Ideally the planner also adds a short factory-by-factory table (one-line description each) below this paragraph and references the `BRAND_CONSTRAINTS` list separately for `brand:inside_page` (since it is global, not per-template).

The Brand-Constraints documentation at lines 509-512 lists the 8 rules:

> Brand-Constraints. Automatisch aktiv via `BRAND_CONSTRAINTS` (siehe `tools/sla_lib/builder/brand_constraints.py`); 8 Regeln zu Color-Palette, Font-Family, Line-Spacing, HL/SL-Distanz, Logo-Größe, Text-auf-Grün, Bleed, Wahlkreuz-Hintergrund. Diese Spec NICHT wiederholen.

The planner should bump `8 Regeln` to `9 Regeln` and add `Page-Bounds (inside_page)` to the enumeration.

### 7.2 `shared/brand/SPEC-WRITING-GUIDE.md` §4 (Constraint examples)

The issue text says "§4 (Constraint examples)" but **§4 in the actual file is "Optional-Sektionen"**. Constraint-prose examples are in:

- §2 "Pflicht-Sektionen → Constraints (Prosa)" at line 74
- §5 "Wie schreibt man jeden Abschnitt gut? → Constraints (Prosa)" at line 154
- §8 "Worked Example — themen-plakat-a3-quer" at line 268

The cleanest place to add the `aligned_below`/`SpreadImage` migration recipe is a NEW subsection under §8 or a new top-level section after §8. The planner should pick the placement; the issue text on this exact line number is loose.

### 7.3 SpreadImage migration recipe (issue requires)

> Document the `SpreadImage` migration recipe (one frame at `x=page_w` → `SpreadImage(left, right, src, w=2×page_w)`).

Place this either at SCHEMA.md §12 next to the constraint catalog, or in SPEC-WRITING-GUIDE.md as a new sub-section. Recommend SPEC-WRITING-GUIDE.md since it's the spec-author audience.

---

## 8. Gotchas the planner must avoid

### 8.1 `BrandRule.check(primitives, doc)` vs `Constraint.check(primitives_by_anname)`

These are TWO DIFFERENT signatures. `inside_page` MUST be a `BrandRule`-shaped class (so it gets `doc`). `aligned_below` MUST be a `Constraint`-shaped factory (so it composes with the existing per-template CONSTRAINTS list). Don't conflate them.

### 8.2 Frozen-dataclass + parameterised brand rule

`BrandRule` is `@dataclass(frozen=True)`. Subclasses adding fields must redeclare them at class scope. The `_make_rule(cls, id=..., name=..., description=...)` helper constructs them — see `brand_constraints.py:366-419`. Follow the existing pattern; do NOT use `__post_init__`.

### 8.3 `width_pt`/`height_pt`/`xpos_pt`/`ypos_pt` overrides bypass `*_mm`

Round-tripped frames in the Zeitung carry these (`templates/zeitung-a4-grun/build.py:2257-2260` shows `xpos_pt=976.38..., ypos_pt=5982.58..., width_pt=33.07..., height_pt=27.78...`). For these frames the `x_mm/y_mm/w_mm/h_mm` fields may be present but lower precision. The `inside_page` rule should prefer `width_pt * PT_TO_MM` over `w_mm` whenever `width_pt is not None`, mirroring the runtime-behavior of `_Frame._wh_pt()` at `primitives.py:483-487`.

However: `xpos_pt` is in scratch-canvas-absolute coordinates (`primitives.py:470-481` adds `page.page_xpos_pt`), not page-local. Translation: `local_x_pt = xpos_pt - page.page_xpos_pt`. Then `local_x_mm = local_x_pt * PT_TO_MM`. This is fiddly and easy to get wrong.

**Recommendation for the planner:** in the FIRST cut, just use `x_mm/y_mm/w_mm/h_mm` and document the verbatim-pt-override edge case as a known limitation. The two known overflowing frames (P9 Spread, unnamed A4) do NOT carry verbatim pt overrides — they use `x_mm/w_mm` directly. Float precision at the 13-digit level (e.g. `209.99999999993608` vs nominal 210) is well within the 0.5 mm tolerance.

### 8.4 Scratch-canvas vs page-local origin in stored frame coords

Built `Document` frames store `x_mm`/`y_mm` as **page-local mm**, not scratch-canvas. Verified by `templates/zeitung-a4-grun/build.py` — every frame's `x_mm`/`y_mm` is in 0..297 range (page-local), never near `100+595*N` (scratch-absolute). The constraint can read `x_mm/y_mm` as page-local without any transformation.

### 8.5 No `Page` reference on primitives

`Page.items.append(primitive)` does NOT set a back-pointer. The `_InsidePageRule` cannot ask a primitive "what page are you on" — it must enumerate `doc.pages`, then iterate `page.items`, and inspect each primitive in that scope. This is mandatory.

### 8.6 `iter_all_primitives()` includes master-page items

`Document.iter_all_primitives()` yields masters first, then doc pages (`document.py:413-425`). For `inside_page`, the rule should:
- Skip master pages (`page.is_master == True`), OR
- Inspect master items against the master's own bbox.

The Zeitung's masters declare full-page sizes (`templates/zeitung-a4-grun/build.py:73-92`); master items can be checked against the master's bbox safely. **Recommendation: do check master items against their master's bbox** so master-page authoring drift is caught too.

### 8.7 `bleed_mm` is per-page

`Page.bleed_mm` is per-page (`document.py:110`), not document-level. `_Bleed3mmRule` iterates pages individually. `_InsidePageRule` MUST do the same — read `page.bleed_mm` per-page. Do NOT cache `doc.pages[0].bleed_mm` and apply globally.

### 8.8 The issue's "page-12 unnamed" coordinate text vs actual code

The issue text says `Print page 12 has an unnamed ImageFrame at x=210, y=−0.18, w=210.8, h=297.2`. The actual code at `templates/zeitung-a4-grun/build.py:2061-2071` matches exactly: `x_mm=209.99..., y_mm=-0.18..., w_mm=210.8, h_mm=297.18`. Confirmed.

### 8.9 Tolerance defaults match across the codebase

The `0.5 mm` default tolerance is used everywhere: `_SameAxisConstraint`, `_InsideConstraint`, `_DistanceConstraint`, `_LineSpacingRule.tolerance_pt=0.5`, `_LogoSize3MRule.tolerance_mm=0.5`. The planner should keep `inside_page` and `aligned_below` at `0.5 mm` for consistency. The issue confirms this in its text.

### 8.10 No "third or extra" inside_page report (issue acceptance criterion)

> Running `--all` today reports **exactly two** `inside_page` errors. Any third or extra report is investigated and added to this issue's findings before merge.

This is the highest-risk acceptance criterion. The planner MUST run `python3 -m sla_lib.builder.structural_check --all --json` after wiring `inside_page` (and BEFORE adding the zeitung overrides) to enumerate every error. Any frame whose `x + w > page.width_mm + bleed_mm + 0.5` OR `y + h > page.height_mm + bleed_mm + 0.5` OR `x < -bleed_mm - 0.5` OR `y < -bleed_mm - 0.5` is a hit.

A grep for suspicious x_mm values in zeitung-a4-grun/build.py turned up only 2 hits past x=207:
```
$ grep -nE "x_mm=21[0-2]|x_mm=20[7-9]" templates/zeitung-a4-grun/build.py
1803:        x_mm=209.99999999993608,           # P9 Spread (left edge AT page-right; w extends to ~420)
2062:        x_mm=209.99999999999991,           # unnamed (left edge AT page-right; w extends to ~420)
```

These are the two known offenders. Other templates (`themen-plakat-a3-quer`, `postkarte-a6-kampagne`, `plakat-a1-hochformat`) have not been spot-checked for this issue's scope; the planner may want a quick pre-flight grep across all template `build.py` files for `x_mm=2..` or large `w_mm=2..` patterns.

### 8.11 The issue's hint about "rule_id name"

The issue text uses the bare name `inside_page` throughout. To use `meta.yml::brand_overrides` without a schema change, the actual rule ID inside `BRAND_CONSTRAINTS` must be `brand:inside_page` (regex compliance). The planner should use the prefixed id as the canonical id and refer to `inside_page` only as the factory/short-name in docs.

### 8.12 Public surface: `__init__.py` exports

Adding `inside_page`, `aligned_below`, `SpreadImage` requires updating `tools/sla_lib/builder/__init__.py` to import and re-export them (`__all__` lines 90-132). Templates and tests do `from sla_lib.builder import same_y, distance_y, ...` — keep that pattern consistent.

### 8.13 No `aligned_below` ⇄ `same_x` + `distance_y` overlap test currently

Templates today encode the "image hangs from text above on the same left axis" pattern as TWO constraints (`same_x("Hero","Body")` + `distance_y("Body","Hero", equals=...)`). After `aligned_below` ships, templates that opt into it should still pass the underlying constraints — the planner should test both forms in isolation but not require migration.

---

## 9. Key references (for the planner — file:line)

| Concern | File | Lines |
|---|---|---|
| Free-form constraint base + factories | `tools/sla_lib/builder/constraints.py` | full file (462 LOC) |
| `_InsideConstraint` (existing parent-bbox check) | `tools/sla_lib/builder/constraints.py` | 198-223 |
| Constraint factory naming convention (`_autoname`) | `tools/sla_lib/builder/constraints.py` | 351-354 |
| `BrandRule` base + 8 concrete subclasses | `tools/sla_lib/builder/brand_constraints.py` | full file (421 LOC) |
| `BRAND_CONSTRAINTS` registry | `tools/sla_lib/builder/brand_constraints.py` | 370-420 |
| `_LogoSize3MRule` (uses `doc.pages[0]` + `PT_TO_MM`) | `tools/sla_lib/builder/brand_constraints.py` | 229-263 |
| `_Bleed3mmRule` (iterates `doc.pages`) | `tools/sla_lib/builder/brand_constraints.py` | 306-324 |
| Structural-check orchestrator | `tools/sla_lib/builder/structural_check.py` | full file (316 LOC) |
| Override skip-list flow | `tools/sla_lib/builder/structural_check.py` | 186-223 |
| Override schema (regex `^brand:[A-Za-z_0-9.]+$`) | `tools/sla_lib/builder/meta_schema.py` | 23-40 |
| `load_brand_overrides` | `tools/sla_lib/builder/meta_schema.py` | 49-92 |
| `Document.iter_all_primitives` | `tools/sla_lib/builder/document.py` | 413-425 |
| `Page` dataclass (with `bleed_mm`, `is_master`) | `tools/sla_lib/builder/document.py` | 106-134 |
| `PT_TO_MM` / `MM_TO_PT` | `tools/sla_lib/builder/document.py` | 30-31 |
| `_Frame` base (fields: `x_mm/y_mm/w_mm/h_mm/rotation_deg/anname/...`) | `tools/sla_lib/builder/primitives.py` | 433-487 |
| `TextFrame` | `tools/sla_lib/builder/primitives.py` | 540-576 |
| `ImageFrame` (`local_offset_mm`, `local_scale`, `scale_type`) | `tools/sla_lib/builder/primitives.py` | 764-787 |
| `Polygon` | `tools/sla_lib/builder/primitives.py` | 847-911 |
| `blocks.py` block convention (PageNumber, etc.) | `tools/sla_lib/builder/blocks.py` | 1-746 (active blocks 1-746) |
| `WahlkreuzSymbol` (multi-frame block, anname-suffix pattern) | `tools/sla_lib/builder/blocks.py` | 487-551 |
| `FoldedPanel` (children-list block; emit(page)) | `tools/sla_lib/builder/blocks.py` | 646-677 |
| Zeitung "P9 Spread" frame | `templates/zeitung-a4-grun/build.py` | 1802-1811 |
| Zeitung unnamed full-A4 frame on page11 (print 12) | `templates/zeitung-a4-grun/build.py` | 2061-2071 |
| Zeitung page9 declaration (left-facing) | `templates/zeitung-a4-grun/build.py` | 184-193 |
| Zeitung page11 declaration (left-facing) | `templates/zeitung-a4-grun/build.py` | 204-213 |
| Zeitung `meta.yml` (existing brand_overrides) | `templates/zeitung-a4-grun/meta.yml` | 1-30 |
| Sample CONSTRAINTS list | `templates/themen-plakat-a3-quer/build.py` | 344-385 |
| Constraint test pattern | `tools/sla_lib/tests/test_constraints.py` | full file (326 LOC) |
| Brand-rule test pattern | `tools/sla_lib/tests/test_brand_constraints.py` | full file (311 LOC) |
| Structural-check test (synthetic templates) | `tools/sla_lib/tests/test_structural_check.py` | full file (327 LOC) |
| `iter_all_primitives` test | `tools/sla_lib/tests/test_document_iter_primitives.py` | full file (115 LOC) |
| SCHEMA.md constraint enum | `templates/_specs/SCHEMA.md` | 484-538 (§12); list at 493-495 |
| SCHEMA.md brand-overrides format | `templates/_specs/SCHEMA.md` | 542-583 (§13) |
| SPEC-WRITING-GUIDE.md constraint prose conventions | `shared/brand/SPEC-WRITING-GUIDE.md` | §2 (line 74), §5 (line 154), §8 (line 268) |
| pages.yml structural_check invocation | `.github/workflows/pages.yml` | 141-147 |
| `__init__.py` public surface | `tools/sla_lib/builder/__init__.py` | full file (133 LOC) |

---

## 10. Confidence summary

| Finding | Confidence |
|---|---|
| `inside_page` belongs in `brand_constraints.py` as a `BrandRule` | HIGH |
| Naming the rule `brand:inside_page` works with existing override regex | HIGH |
| No `rotated_bbox` helper exists today | HIGH |
| Scribus rotation is around the frame top-left corner | MEDIUM (convention-based; not verified by render) |
| `BrandRule.check(primitives, doc)` gets `doc` — no need to widen `iter_all_primitives` | HIGH |
| Master-page items shouldn't be skipped (catch master drift too) | MEDIUM (issue text doesn't say; my recommendation) |
| Two and only two overflowing frames in zeitung today | HIGH (verified by literal grep + line read) |
| The issue's coordinate snippet for the unnamed image matches the code | HIGH |
| Templates outside zeitung-a4-grun do not have `inside_page` violations | MEDIUM (not yet verified; planner should pre-flight grep) |
| `aligned_below` is a per-template `Constraint` factory living in `constraints.py` | HIGH |
| `SpreadImage` belongs in `blocks.py` next to `WahlkreuzSymbol` | HIGH |
| `local_offset_mm` is the right knob for image-content shifting | HIGH |
| Existing tests don't pin `--all` brand-rule output (won't break) | HIGH |
| Documentation surface lines (SCHEMA §12, SPEC-WRITING-GUIDE §5/§8) | HIGH (issue's "§6"/"§4" line refs are off but findable) |
| `width_pt`/`xpos_pt` overrides edge case is fiddly but safe to defer | MEDIUM (planner should explicitly call out the limitation) |

End of codebase.md
