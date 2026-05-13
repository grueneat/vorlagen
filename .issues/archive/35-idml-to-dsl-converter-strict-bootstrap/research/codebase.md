# Codebase research — Issue 35 (IDML → DSL converter)

**Researched:** 2026-05-11
**Scope:** Map every existing piece that `tools/idml_to_dsl.py` will lean on or extend, so the planner has zero hidden surprises.
**Confidence:** HIGH (every fact below is grounded in file:line citations).

---

## Summary

The new converter is structurally a sibling of `tools/sla_to_dsl.py` — same one-shot bootstrap shape (CLI → walk → emit `build.py` → strict `UnhandledElement`), but **reading IDML** instead of SLA. The output build.py uses the *identical* DSL surface (`sla_lib.builder.{Document, DocumentLayer, TextFrame, ImageFrame, Polygon, Run, ParaStyle, Brand, pack_inline_image}`) — there is no need to extend any primitive's signature for first-cut. Coordinate semantics differ (IDML uses **spread-centered affine + nested-group transforms**, SLA uses **scratch-canvas page origin**), so the geometry routine is the single load-bearing new piece.

The source IDML is small (`~41k lines of XML, 2 spreads, 24 stories`), **no threaded TextFrames** (every `Next/PreviousTextFrame="n"`), **no Tables**, **no EPS**, **no Anchored Objects**, **23 paragraph styles defined / 5 actually used in stories**. Two complications that ARE present and NOT yet in the issue's mapping table: **(a) nested vector PDF/AI imports** (logos imported as `<PDF>` children of `<Rectangle>`, not as raster `<Image>`) and **(b) 15 `<Group>` elements with their own `ItemTransform`** that need cascade-multiplication.

`SimpleIDML==1.2.0` installs cleanly via `pip install SimpleIDML` (verified — package name is `SimpleIDML` capital-cased, module `simple_idml`). For the bootstrap, using `lxml` directly on the unzipped XML is probably faster than learning SimpleIDML's `Spread`/`Page`/`Story` wrappers; the issue's "SimpleIDML + lxml" wording lets us pick either.

**The sibling template's `meta.yml` (`templates/kandidat-falzflyer-din-lang/meta.yml`) cannot be re-used unchanged** — it encodes a *V1 "Falz-Rhythm" 6-panel kandidaten flyer*; the new IDML is a *zickzack-Falz **Themen**-flyer* with completely different slot content (1 cover + 5 themen panels, no kandidat-portrait, no per-panel top-band). The new meta.yml needs from-scratch slot authoring, not clone-edit.

---

## Existing Converter Architecture — `tools/sla_to_dsl.py` (1288 lines)

### Entry point & CLI
- `main(argv)` (sla_to_dsl.py:1271–1285): argparse with **4 args**:
  - positional `source` (Path) → input .sla
  - positional `output` (Path) → output build.py path
  - `--template-id` (required) → string baked into the emitted `Document(template_id=…)`
  - `--assets-dir` (required, Path) → **retained for API compatibility but no longer used** (sla_to_dsl.py:933–936); the converter round-trips inline images verbatim instead of dumping sidecar PNGs.
- On `UnhandledElement` (sla_to_dsl.py:1281–1283) the binary prints `f"UnhandledElement: {e}"` to stderr and exits 2.

### `UnhandledElement` exception
- Defined sla_to_dsl.py:59–62 — single-class typed exception. Every walker raises it with a message that points to *where in the converter to extend* (e.g. sla_to_dsl.py:317 `STYLE {name} carries unhandled attribute {k}`, sla_to_dsl.py:551 `ITEXT carries unhandled attribute {k}`, sla_to_dsl.py:601 `StoryText element {tag}`).

### Code emitter
- `class PythonRepr` (sla_to_dsl.py:140–162) — line buffer + indent tracker.
- `_py_value(v)` (sla_to_dsl.py:165–195) — Black-style literal formatter; **uses `repr()` for floats** (sla_to_dsl.py:181) so 17-digit round-trip precision survives.
- `_kwarg(name, value)` (sla_to_dsl.py:198–199).
- `_emit_call(cls, kwargs)` (sla_to_dsl.py:872–889) — emits multi-line constructor calls; pops `runs=` and `soft_shadow=` and emits them as nested `Run(...)`/`SoftShadow(...)` literals.

### Walk phases (single-pass)
The `convert()` function (sla_to_dsl.py:926–1268) executes 7 phases in order:
1. **Document metadata** sla_to_dsl.py:937–963: parse `<DOCUMENT>` attributes, derive page-w/h, bleed, margins, facing, fonts, HCMS, etc. Filter doc-level attrs into `differing_doc_extras` against `Brand.gruene_noe().default_doc_attrs` (sla_to_dsl.py:1036) so only template-specific extras are emitted.
2. **Imports block** sla_to_dsl.py:1044–1057: emits `from sla_lib.builder import (Brand, Document, TextFrame, ImageFrame, Polygon, Run, ParaStyle, CharStyle, SoftShadow,)`.
3. **`Document(...)` constructor** sla_to_dsl.py:1066–1094: `brand=Brand.gruene_noe(),` + per-template kwargs (title, template_id, facing_pages, page dims in pt, hcms, extras).
4. **Document-local colors** sla_to_dsl.py:1097–1115: emit `doc.add_color(name, cmyk=…, spot=…, register=…)` for every COLOR not already in `brand.colors`.
5. **CharStyle / ParaStyle** sla_to_dsl.py:1118–1133: emit `doc.add_char_style(CharStyle(...))` / `doc.add_para_style(ParaStyle(...))`.
6. **Masters** sla_to_dsl.py:1136–1174 and **Pages** sla_to_dsl.py:1177–1210: emit `doc.add_master(...)` / `var = doc.add_page(...)`, passing through `page_xpos_pt` / `page_ypos_pt` / `width_pt` / `height_pt` verbatim so scratch-canvas offsets round-trip byte-stable.
7. **PageObjects** sla_to_dsl.py:1212–1260: group by `OwnPage`, detect chains (sla_to_dsl.py:893–922), for each PAGEOBJECT call `_convert_pageobject()` (sla_to_dsl.py:614–857). Chains are emitted as `_chainN_M = TextFrame(...); pageX.add(_chainN_M)` then `_chain0_0.link_to(_chain0_1)` lines (sla_to_dsl.py:1254–1258).
- Final two lines: `doc.save(HERE / "template.sla")` + `print(f"OK: ...")` (sla_to_dsl.py:1262–1263).

### Strict-mode attribute taxonomy
The converter has **closed allow-lists** for every attribute it touches; anything outside raises `UnhandledElement`:
- `PARA_ATTR_MAP_STR/FLOAT/INT/BOOL + PARA_ATTR_HANDLED` (sla_to_dsl.py:244–296) — STYLE element attrs.
- `CHAR_ATTR_MAP_*` (sla_to_dsl.py:321–338) — CHARSTYLE element attrs.
- `PAGEOBJECT_HANDLED_PRIM` (sla_to_dsl.py:362–411) — ~70 PAGEOBJECT attribute names accepted.
- `ITEXT_ATTR_HANDLED` (sla_to_dsl.py:465–474), `PARAGRAPH_OVERRIDE_ATTRS` / `DEFAULTSTYLE_OVERRIDE_ATTRS` / `VAR_OVERRIDE_ATTRS` (re-exported from `sla_lib/builder/primitives.py:53–86`).

### Output build.py shape (representative)
```python
# Auto-generated from <source.sla> by tools/sla_to_dsl.py.
# Hand-edit thereafter; this file is the source of truth.

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))

from sla_lib.builder import (  # noqa: E402
    Brand, Document, TextFrame, ImageFrame, Polygon, Run,
    ParaStyle, CharStyle, SoftShadow,
)

doc = Document(
    brand=Brand.gruene_noe(),
    title="...", template_id="...", author="...",
    facing_pages=False, ...
    extra_doc_attrs={...},
    extra_pdf_attrs={...},
)

# Colors, char/para styles, masters, pages, page objects ...

doc.save(HERE / "template.sla")
print(f"OK: {HERE / 'template.sla'}")
```
Emitted by `sla_to_dsl.py:1043–1264`. The IDML converter should emit **byte-identical scaffolding** so existing tooling (`bin/render-gallery`, `bin/validate`, `tools/spec_check.py`) just works.

### What the IDML emit phase will NOT need (vs SLA converter)
- Inline image qCompress base64 round-trip (sla_to_dsl.py:203–216, primitives.py:758–769) — IDML has no inline-image-as-base64 concept; raster images are external Links. We will need to import the actual JPEG/PSD bytes and call `pack_inline_image(image_bytes, "jpg")` instead (verbatim qCompress passthrough is SLA-specific).
- Path-rect detection (sla_to_dsl.py:66–117 `_is_rect_path`) — IDML PathPointArray normalises differently; the IDML walker derives bbox-from-anchor-points directly.
- Chain detection (sla_to_dsl.py:893–922) — no threaded TextFrames in this IDML (see Corpus Inventory below); leave as YAGNI / raise on `Next/PreviousTextFrame != "n"`.

---

## DSL Primitives Reference

**All public exports** live behind `from sla_lib.builder import …` (`tools/sla_lib/builder/__init__.py:57–89`). The emitted build.py uses *only* these names.

<interfaces>
// ==========================================================================
// From tools/sla_lib/builder/__init__.py (public surface, lines 57–134)
// ==========================================================================
from .ci import Color, Style, load_ci
from .document import Document, Page
from .primitives import TextFrame, ImageFrame, Polygon, Line, Anchor, Run, pack_inline_image
from .styles import DocumentLayer, ParaStyle, CharStyle, SoftShadow
from .brand import Brand
from . import blocks
from . import library
from .composites import AlignedRow, AlignedColumn, MirroredPair, EqualGapStack, GridSpec, GridCell, HierarchyBlock
from .constraints import (same_y, same_x, same_size, mirrored_x, mirrored_y, inside,
                          equal_gap, hierarchy, same_style, distance_y, distance_x,
                          aligned_below, Constraint, Violation)
from .brand_constraints import BRAND_CONSTRAINTS, BrandRule

// ==========================================================================
// From tools/sla_lib/builder/document.py
// ==========================================================================
class Document:
    def __init__(self, title: str = "", template_id: str = "",
                 author: str = "Die Grünen Niederösterreich",
                 ci_path: Optional[Path | str] = None, *,
                 brand: Optional[Brand] = None,
                 layers: Optional[list[DocumentLayer]] = None,
                 facing_pages: bool = False,
                 column_gap_default_pt: float = 11.0,
                 unit: str = "mm",
                 deffont: str = "Gotham Narrow Book",
                 defsize: float = 12,
                 first_page_num: int = 1,
                 palette_replaces_ci: bool = False,
                 hcms: bool = False,
                 doc_page_width_pt: Optional[float] = None,
                 doc_page_height_pt: Optional[float] = None,
                 extra_doc_attrs: Optional[dict[str, str]] = None,
                 extra_pdf_attrs: Optional[dict[str, str]] = None) -> None: ...
    def add_color(self, name: str, *, cmyk=None, rgb=None,
                  spot: bool = False, register: bool = False) -> None: ...
    def add_para_style(self, ps: ParaStyle) -> None: ...
    def add_char_style(self, cs: CharStyle) -> None: ...
    def add_master(self, *, name: str = "Normal",
                   size: str | tuple[float, float] = "A4",
                   orientation: str = "portrait",
                   bleed_mm: float = 3.0,
                   margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10),
                   facing: str = "right",
                   page_xpos_pt: Optional[float] = None,
                   page_ypos_pt: Optional[float] = None,
                   width_pt: Optional[float] = None,
                   height_pt: Optional[float] = None) -> Page: ...
    def add_page(self, *, size=..., orientation: str = "portrait",
                 bleed_mm: float = 3.0, margins_mm=(10,10,10,10),
                 master: str = "Normal", label: str = "",
                 page_xpos_pt: Optional[float] = None,
                 page_ypos_pt: Optional[float] = None,
                 width_pt: Optional[float] = None,
                 height_pt: Optional[float] = None) -> Page: ...
    def save(self, path: Path | str) -> None: ...

@dataclass
class Page:
    width_pt: float; height_pt: float; bleed_mm: float = 3.0
    margins_mm: tuple[float, float, float, float] = (10,10,10,10)
    master_name: str = ""; label: str = ""
    items: list = []
    own_page: int = 0
    page_xpos_pt: float = 0; page_ypos_pt: float = 0
    is_left: bool = False; is_master: bool = False
    master_id: str = ""
    def add(self, item) -> "Page": ...  # expands .emit() iterables

MM_TO_PT = 72.0 / 25.4   # document.py:30
PT_TO_MM = 25.4 / 72.0   # document.py:31
def mm_to_pt(value_mm: float) -> float: ...   # document.py:46

// ==========================================================================
// From tools/sla_lib/builder/primitives.py
// ==========================================================================
@dataclass(frozen=True)
class Anchor:
    h: str = "left"   # "left" | "center" | "right"
    v: str = "top"    # "top"  | "center" | "bottom"
    margin_mm: float = 0.0

@dataclass(frozen=True)
class Run:
    text: str = ""
    has_itext: bool = True
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    fshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    features: Optional[str] = None
    kern: Optional[float] = None
    underline_position: Optional[int] = None    # TXTULP
    strike_position: Optional[int] = None       # TXTSTP
    char_style: Optional[str] = None            # CPARENT
    paragraph_style: Optional[str] = None       # PARENT on trailing <para/>
    paragraph_attrs: Optional[dict] = None      # keys in PARAGRAPH_OVERRIDE_ATTRS
    separator: Optional[str] = None             # "para" | "breakline" | "tab" | "breakcol" | "breakframe"
    var: Optional[str] = None                   # "pgno"
    var_attrs: Optional[dict] = None            # keys in VAR_OVERRIDE_ATTRS

@dataclass
class _Frame:
    x_mm: float = 0; y_mm: float = 0; w_mm: float = 50; h_mm: float = 30
    anchor: Optional[Anchor] = None
    rotation_deg: float = 0
    layer: int = 2  # default Text layer
    anname: str = ""
    custom_path: Optional[str] = None    # FRTYPE=3 verbatim path data
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0           # FRTYPE=2 / RADRECT
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    xpos_pt: Optional[float] = None       # verbatim pt overrides
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None
    is_full_bleed: bool = False

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""                # DefaultStyle PARENT (paragraph style name)
    fcolor: str = ""               # legacy override
    runs: Optional[list[Run]] = None
    columns: int = 1
    col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None   # 0=top, 1=center, 2=bottom
    text_align: Optional[int] = None             # deprecated alias
    default_linesp_mode: Optional[int] = None
    trail_style: Optional[str] = None
    trail_attrs: Optional[dict] = None
    fill: Optional[str] = None       # PCOLOR
    line_color: Optional[str] = None # PCOLOR2
    line_width_pt: float = 0         # PWIDTH
    default_style_attrs: Optional[dict] = None  # keys in DEFAULTSTYLE_OVERRIDE_ATTRS
    next_item: Optional["TextFrame"] = None
    def link_to(self, other: "TextFrame") -> "TextFrame": ...

@dataclass
class ImageFrame(_Frame):
    src: str = ""                   # PFILE path
    image: str = ""                 # alias (converter emits image=)
    layer: int = 1                  # default Bilder
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1             # SCALETYPE
    ratio: int = 1                  # RATIO
    pic_art: int = 1                # PICART
    fill: Optional[str] = None      # PCOLOR
    line_color: Optional[str] = None # PCOLOR2
    line_width_pt: float = 0
    inline_image_data: Optional[str] = None   # qCompress base64
    inline_image_ext: Optional[str] = None    # "png" | "jpg"

@dataclass
class Polygon(_Frame):
    fill: str = "Black"                  # PCOLOR
    line_color: Optional[str] = None     # PCOLOR2
    line_width_pt: float = 0
    layer: int = 0                       # default Hintergrund
    shape: str = "rectangle"             # 'rectangle' | 'ellipse'
    fill_shade: int = 100                # SHADE — emitted when != 100
    dash_pattern: Optional[tuple[float, ...]] = None

# Line is deprecated — converter emits Polygon(custom_path=..., fill='None'). primitives.py:925–987

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """qCompress wrap + base64; pass to ImageFrame(inline_image_data=..., inline_image_ext=...)."""
    # primitives.py:758–769

// ==========================================================================
// From tools/sla_lib/builder/styles.py
// ==========================================================================
@dataclass(frozen=True)
class DocumentLayer:
    name: str
    visible: bool = True
    printable: bool = True
    editable: bool = True
    flow: bool = True
    transparent: float = 1.0
    blend: int = 0
    outline: bool = False
    layer_color: str = "#000000"

@dataclass(frozen=True)
class ParaStyle:
    name: str
    parent: Optional[str] = None
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    align: Optional[int] = None         # 0=left,1=center,2=right,3=block
    linesp: Optional[float] = None
    linesp_mode: Optional[int] = None
    language: Optional[str] = None
    space_before_pt: Optional[float] = None  # VOR
    space_after_pt: Optional[float] = None   # NACH
    first_indent_pt: Optional[float] = None  # FIRST
    left_indent_pt: Optional[float] = None   # INDENT
    right_indent_pt: Optional[float] = None  # RMARGIN
    hyph_consecutive_lines: Optional[int] = None
    hyph_word_min: Optional[int] = None
    drop_cap: Optional[bool] = None
    drop_lines: Optional[int] = None
    min_word_track: Optional[float] = None
    min_glyph_shrink: Optional[float] = None
    max_glyph_extend: Optional[float] = None
    keep_together: Optional[bool] = None
    keep_lines_start: Optional[int] = None
    direction: Optional[int] = None
    bcolor: Optional[str] = None
    bshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    features: Optional[str] = None
    kern: Optional[float] = None
    scalev: Optional[int] = None
    fshade: Optional[int] = None
    # ... txt_underline_* / txt_strike_* / txt_shadow_* / txt_outline / baseline_offset
    # ... paragraph_effect_offset / bullet / numeration
    is_default: bool = False

@dataclass(frozen=True)
class CharStyle:
    name: str
    font: Optional[str] = None; fontsize: Optional[float] = None
    fcolor: Optional[str] = None; fshade: Optional[int] = None
    fontfeatures: Optional[str] = None; features: Optional[str] = None
    kern: Optional[float] = None; language: Optional[str] = None
    # ... scolor / sshade / bgcolor / bgshade / txt_*
    is_default: bool = False

@dataclass(frozen=True)
class SoftShadow:
    color: str = "Black"
    blur_radius_pt: float = 8.504
    x_offset_pt: float = 1.984
    y_offset_pt: float = 1.984
    blend_mode: int = 1
    opacity: float = 0.0
    shade: int = 100
    erase: bool = False
    object_trans: bool = False

// ==========================================================================
// From tools/sla_lib/builder/brand.py
// ==========================================================================
@dataclass(frozen=True)
class Brand:
    name: str; short: str
    colors: dict[str, BrandColor]
    para_styles: dict[str, ParaStyle]
    char_styles: dict[str, CharStyle]
    layers: list[DocumentLayer]
    default_doc_attrs: dict[str, str]    # 113 entries; brand defaults for Scribus
    default_pdf_attrs: dict[str, str]    # 34 entries
    deffont: str = "Gotham Narrow Book"
    defsize: float = 12.0
    column_gap_default_pt: float = 11.0
    bleed_mm: float = 3.0
    @classmethod
    def gruene_noe(cls, ci_path=None, defaults_path=None) -> "Brand": ...

// ==========================================================================
// From tools/sla_lib/builder/bbox.py — used by audit_alignment / brand rules
// ==========================================================================
def rotated_bbox(x, y, w, h, deg) -> tuple[float, float, float, float]: ...
def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """Page-local mm bbox honouring anchor + rotation. Returns None for
    primitives without spatial extent. NOTE: ignores xpos_pt/width_pt
    overrides — falls back to *_mm."""

// ==========================================================================
// From tools/sla_lib/builder/blocks.py — composed blocks
// ==========================================================================
# 13 active blocks + 11 legacy (under blocks.legacy). The converter does NOT
# emit blocks — it emits raw primitives. But the build.py the human edits
# afterwards may import them; emitted import line is safe to omit.
@dataclass
class FoldLine:
    start_mm: tuple[float, float]; end_mm: tuple[float, float]
    layer_idx: int = 3              # Falz layer
    layer_name: str = "Falz"        # documentation hint
    spot_color: str = "Falz"
    line_width_pt: float = 0.5
    dash_pattern: tuple[float, float] = (3.0, 1.5)
    anname: str = "Falzlinie"
    def emit(self, page=None) -> Iterable: ...   # yields Polygon
# Other relevant blocks: PageNumber, Impressum, PageBackground, ContactBlock,
# ColumnTextStory, WahlkreuzSymbol, DieCut, FoldedPanel, SpreadImage,
# DoorHangerCutout, TableTentFold (blocks.py:68–851).

// ==========================================================================
// From tools/sla_lib/reader.py (existing SLA reader — not used by IDML conv,
//   but the planner should know what reader-shaped API already exists)
// ==========================================================================
class SLADocument:
    def __init__(self, path: str | Path): ...
    @property version() -> str
    @property page_count() -> int
    @property page_size_pt() -> tuple[float, float]
    @property bleed_pt() -> dict[str, float]
    def page_objects() -> list[etree._Element]
    def pages() -> list[etree._Element]
    def find_by_anname(self, anname: str) -> etree._Element | None
    def slots() -> list[Slot]
    def iter_pages() / iter_masters() / iter_layers()
    def iter_colors() / iter_styles() / iter_charstyles()
    def iter_itext(frame) -> Iterator[etree._Element]
    def frame_text(frame) -> str
    def write(path) -> None
</interfaces>

---

## Sibling Template Anatomy — `templates/kandidat-falzflyer-din-lang/`

Structure to mirror (build.py:1029 lines, meta.yml:294 lines):

| File | Purpose | Notes |
|---|---|---|
| `meta.yml` | Slot schema + brand_overrides + samples + preflight | **NOT clone-edit-friendly** — encodes 6-panel kandidat-flyer slots that don't match the new themen-flyer IDML. New meta.yml must be authored from scratch. |
| `build.py` | DSL-built Document; `build_template()` + `build_preview()` + `build()` | Mirror the **scaffold** (imports, HERE, constants, `build_template`, alias `build_doc = build_template`, `build_preview` with INJECT_MAP), but the per-frame body is generated by the IDML converter. |
| `template.sla` | Output of `build_preview()` | Generated; not hand-edited. |
| `preview.pdf` | Rendered via `bin/render-gallery` | Generated. |
| `samples/` | Sample renders for gallery | Generated. |
| `README.md` | Optional human notes | Optional. |

### Scaffold structure to mirror (build.py:1–67, 872–946)
```python
"""<title> — DSL build entry point.

Spec: templates/_specs/<slug>.md.
Format: ...
"""
from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))

from sla_lib.builder import (  # noqa: E402
    Brand, Document, DocumentLayer,
    TextFrame, ImageFrame, Polygon, Run, ParaStyle, pack_inline_image,
    library,
    # constraints (only if the spec carries CONSTRAINTS list)
)
from sla_lib.builder.blocks import FoldLine  # noqa: E402

# Constants ---------------------------------------------------------------
TRIM_W_MM = 297.0; TRIM_H_MM = 210.0; BLEED_MM = 3.0   # ← BUT IDML uses 2.0!
PANEL_W_MM = 99.0
FOLD_X1_MM = 99.0; FOLD_X2_MM = 198.0
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_FALZ = 3

INJECT_MAP: dict[str, str] = { ... }   # anname -> library lib_id

def _add_styles(doc): ...           # registers all per-template ParaStyles
def _add_front(doc, page0): ...     # all P1/P2/P3 frames
def _add_back(doc, page1): ...      # all P4/P5/P6 frames

def build_template() -> Document:
    doc = Document(brand=Brand.gruene_noe(), title="...", template_id="...",
                   author="Die Grünen Niederösterreich", facing_pages=False,
                   layers=[DocumentLayer(...), ...])
    doc.add_color("Falz", cmyk=(100, 0, 0, 0), spot=True)
    _add_styles(doc)
    doc.add_master(name="Normal", size=(TRIM_W_MM, TRIM_H_MM),
                   bleed_mm=BLEED_MM, margins_mm=(0.0, 0.0, 0.0, 0.0))
    page0 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                        margins_mm=(0.0, 0.0, 0.0, 0.0), master="Normal")
    page1 = doc.add_page(...)
    _add_front(doc, page0)
    _add_back(doc, page1)
    return doc

def build_preview() -> Document:
    doc = build_template()
    if not INJECT_MAP: return doc
    for page in doc.pages:
        for item in page.items:
            if not isinstance(item, ImageFrame): continue
            lib_id = INJECT_MAP.get(item.anname)
            if not lib_id: continue
            img = library.load(lib_id, optional=True)
            if img is None: continue
            library.inject_into_frame(item, img,
                target_w_mm=item.w_mm, target_h_mm=item.h_mm)
    return doc

build_doc = build_template   # alias for structural_check / spec_check / smoke

def build(out_path: str | Path = HERE / "template.sla") -> Path:
    doc = build_preview(); doc.save(Path(out_path)); return Path(out_path)

CONSTRAINTS = [...]   # OPTIONAL — only if the new template warrants intra-panel rules
```

### `meta.yml` shape (sibling falzflyer:1–58)
```yaml
id: <slug>
version: 0.1.0
title: <human title>
format: A4
orientation: landscape
pages: 2
preview_dpi: 100
audience: [...]
description: >
  <free-text>
build:
  script: build.py
  output: template.sla

previews_for_sla: <sha256>          # auto-managed by check_stale_previews
brand_overrides: []                 # optional; each {id, reason}
ci_overrides:
  non_ci_styles: [...]              # ParaStyles defined per-template
  non_ci_colors: [...]
  non_ci_layers: [...]

slots: { slot_id: {type, description?, anname, optional?, source?}, ... }
example_pages: [{ num, label }, ...]
samples: []                          # gallery samples
preflight:
  bleed_mm: <int>
  fold_mm: [99, 198]
  cmyk_only: true
  min_image_dpi: 300
```

The new target dir is `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` (per ISSUE.md scope).

---

## CI Surface

### `shared/ci.yml` (128 lines)
Brand identity — single source of truth (`shared/ci.yml:1–129`):
- Colors: `Black, White, Registration, Dunkelgrün, Hellgrün, Gelb, Magenta` (7 CI colors)
- Fonts: `Gotham Narrow Book/Bold/Black/Ultra, Vollkorn Black Italic` (5)
- Styles: `ci/default, ci/headline-ultra, ci/headline-vollkorn-italic, ci/body-12, ci/body-11, ci/impressum, ci/stoerer, ci/cta` (8)
- Layers: `Hintergrund (0), Bilder (1), Text (2), Hilfslinien (3)`

### `tools/spec_check.py` (60+ lines inspected; spec_check.py:1–30)
Reads `templates/_specs/<slug>.md`, parses embedded `slots:` YAML, opens `templates/<slug>/template.sla`, diffs each slot's coords against PAGEOBJECT entries.
- CLI: `spec_check.py SLUG` or `--all` or `--tolerance-mm 0.1`.
- Default tolerance: 0.5 mm. Severity: drift < 0.05 mm silent; 0.05 ≤ d ≤ tol info; d > tol error → exit 1.
- Skips slots whose anname starts with `internal:` or `_`.
- Skips retro-specs (`_existing-*.md`).
- **Implication for issue 35:** the new template needs `templates/_specs/kandidat-falzflyer-din-lang-gruenes-cover-v2.md` (with embedded `slots:` block) to be testable by `spec_check`. OR ship without a spec file and accept that `spec_check` simply has nothing to validate.

### `tools/audit_alignment.py` (audit_alignment.py:1–58)
Reads `templates/<slug>/build.py` via `template_loader.load_build_module()`, computes per-template alignment audit (suspicious adjacencies, spine-safety, tolerance suspicion). Loads each frame's `frame_bbox_mm()` (bbox.py:49–74).
- CLI: `audit_alignment.py <slug> [--json|--md FILE.md]`; `--strict` exits 1 on any finding.
- Defaults: `axis_tol_mm=25.0, adjacency_tol_mm=30.0, min_drift_mm=0.5`.
- Threshold for "encode-and-silence" tolerance: `>1.0 mm tol` or `>30.0 mm gap` is flagged.
- **Implication:** the new build.py must `load_build_module`-cleanly (i.e. importable, defines `build_doc` or `build_template`).

### `tools/visual_diff.py` (visual_diff.py:1–80)
Renders DSL `template.sla` → PDF via `tools/_export_pdf.py` under `xvfb-run -a scribus` (visual_diff.py docstring), rasterises baseline.pdf + DSL PDF via `pdftoppm` at requested DPI, ImageMagick `compare -metric AE -fuzz` per page. Per-page/per-region tolerance via `templates/<slug>/diff.yml`. Default `max_pixel_mismatch_pct=1.0, fuzz_pct=25.0` (visual_diff.py:53–54).
- CI flag `--ci` ⇒ 96 dpi. Default local 150 dpi (per bin/validate).
- **Implication:** issue 35 does NOT need a baseline.pdf for first cut (visual_diff is opt-in per-template via `meta.yml:original_sla:` and `baseline.pdf` presence — bin/validate:`grep -q ^original_sla:`).

### `tools/_export_pdf.py` (7 lines)
Minimal: `scribus.openDoc(infile); pdf = scribus.PDFfile(); pdf.file = outfile; pdf.save()`. Called inside `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>`.

### `bin/` scripts
- `bin/validate` (validate:1–80) — local round-trip. Runs `bin/check-fontsizes` + `bin/check-stale-previews` then sla_diff+visual_diff for every template with `original_sla:` in meta. **The IDML target template doesn't have an `original_sla:` SLA file, so validate will skip it** (good — no SLA baseline to diff against).
- `bin/check-fontsizes` — pre-flight: rejects fractional FONTSIZEs in any template.sla.
- `bin/check-stale-previews` — pre-flight: rejects gallery previews whose `previews_for_sla` sha doesn't match the current SLA.
- `bin/audit-alignment` — wrapper around `tools/audit_alignment.py`.
- `bin/render-gallery` — runs each template's build.py to produce template.sla + preview.pdf.

### `shared/ci.yml` + `shared/ci-defaults.yml`
- `shared/ci.yml` (128 lines) — brand identity (palette, styles, fonts, layers).
- `shared/ci-defaults.yml` (173 lines) — 113 `default_doc_attrs` + 34 `default_pdf_attrs` Scribus defaults bundled by `Brand.gruene_noe()`.

---

## IDML Corpus Inventory — `/tmp/idml-research/`

Re-extract: `unzip -o "<idml>" -d /tmp/idml-research/`.
Source IDML carries InDesign DOM v21.2 (`designmap.xml:1–3`).

### Top-level files & shape
```
META-INF/{container.xml, metadata.xml}
mimetype
designmap.xml                                    # document root + spread/story refs
MasterSpreads/MasterSpread_ubb.xml               # 1 master, EMPTY (no items)
Spreads/{Spread_ueb.xml, Spread_u108.xml}        # 2 spreads, 1 page each
Stories/{Story_u189.xml … Story_u530.xml}        # 24 stories
Resources/{Fonts.xml, Graphic.xml, Styles.xml, Preferences.xml}
XML/{BackingStory.xml, Tags.xml}
```

### Document geometry (`Resources/Preferences.xml` + designmap.xml)
- `DocumentPreference`: `PageWidth="841.89 pt"`, `PageHeight="595.28 pt"` → **297 × 210 mm = A4 quer** ✓ matches sibling falzflyer trim.
- **`DocumentBleed*Offset = 5.669292 pt` ≈ 2 mm** ⚠ **DIFFERS from sibling falzflyer's 3 mm** — issue 35 build.py must use `BLEED_MM = 2.0` (or whatever the IDML carries), not the sibling's 3.0.
- `FacingPages="false"`, `PageBinding="LeftToRight"`.
- `ZeroPoint="0 0"` (designmap.xml:3).
- Default language: `de_DE_2006` (designmap.xml:10).

### Layers (designmap.xml:73–82)
2 layers:
| Self | Name | Locked | Printable | Visible | Items |
|------|------|--------|-----------|---------|-------|
| `uba` | `Gestaltung` | false | **true** | true | most |
| `ue6` | `Info` | true | **false** | true | druck.at marks (32 frames using Druckformat/Endformat/Sicherheit/Faltung spot colors) |

**Converter MUST skip Layer `ue6` (non-printable)** — it carries InDesign-internal printer-mark frames that are not part of the deliverable.

### Spread / Page transforms
| Spread | Page | Spread.ItemTransform | Page.ItemTransform |
|---|---|---|---|
| `ueb` | `uf2` (Name="1") | `1 0 0 1 0 0` | `1 0 0 1 -420.94 -140.31` |
| `u108` | `u10f` (Name="2") | `1 0 0 1 ~0 786.61` | `1 0 0 1 -420.94 -140.31` |

So the **page-relative→spread-relative** transform is `(−420.94, −140.31)` for both pages (= `(−297mm − bleed_2mm, half(spread_extent))` — InDesign centers the page in the spread).

`Page.GeometricBounds = "-157.32 -4e-14 437.95 841.89"` — yMin/xMin/yMax/xMax in **page-local space** (i.e. ZeroPoint of the page sits at origin; page bounds are *not* `(0,0)→(W,H)` — they extend symmetrically around the binding axis). For converter purposes, the page-relative item coordinates are computed by:
```python
# Frame anchor i in spread-coords:  pt_spread = transform_cascade @ frame_anchors_i
# Frame anchor i in page-coords:    pt_page   = pt_spread − page_origin_in_spread
# where page_origin_in_spread = page.ItemTransform translation (tx, ty)
# Then convert pt → mm via PT_TO_MM.
```

### Element counts per spread

| Page | Toplevel items (printable layer `uba`) | Notes |
|------|---|---|
| 1 (Spread_ueb) | 8 TextFrames, 8 Rectangles, 17 Polygons, 0 Images, 1 Oval, 5 Groups (printable) + 6 items on `Info` layer | u347 = **1 rotated TextFrame** (90° CCW); 2 Rectangles contain nested `<PDF>` (vector logo imports) |
| 2 (Spread_u108) | 15 TextFrames, 16 Rectangles, 17 Polygons, **2 Images**, 0 Oval, 10 Groups (printable) + 6 items on `Info` layer | 2 raster images (1 JPEG `green-pine-trees`, 1 PSD `Plakat dunkel`); 7 social-media-icon Rectangles each contain nested `<PDF>` (.ai vector imports) |

15 `<Group>` elements total — Groups carry their own `ItemTransform`; converter must cascade.

### Threaded frames: **NONE**
Every `<TextFrame>` carries `PreviousTextFrame="n" NextTextFrame="n"` (verified `grep -c` returns 8+15=23 ALL having both attrs = "n"). The single Story spans a single Frame; no NEXTITEM chain wiring required for first cut. **Action:** raise `UnhandledElement` if a future IDML has threaded frames, to force a follow-up.

### Rotated frames: **1**
TextFrame `u347` on Spread_ueb has `ItemTransform="-2.83e-16 -0.9999 0.9999 -2.83e-16 124.68 180.78"` — that's a 90° CCW rotation around frame center. The converter must derive `rotation_deg = atan2(b, a) * 180/π` from `(a, b, c, d, tx, ty)` and pass to `TextFrame(rotation_deg=…)`.

### MasterSpread: empty
`MasterSpread_ubb.xml` (19 lines) — `<MasterSpread Self="ubb" Name="A-Mustervorlage">` contains exactly one `<Page>` and zero page-items. The converter can emit `doc.add_master(name="Normal", size=(297,210), bleed_mm=2.0, margins_mm=(0,0,0,0))` with no MASTEROBJECTs (parallel to the sibling falzflyer).

### Stories
24 stories, 14 of them ≤ 22 lines (single-line headlines or short slogans). Largest stories: Story_u200 (64 lines), Story_u1b3 / Story_u1e9 (58 lines each), Story_u251 (52 lines), Story_u2d9 (52 lines) — these are the long body-copy panels. Every Story uses `<ParagraphStyleRange>` + `<CharacterStyleRange>` + `<Content>` (+ `<Br/>` for soft line breaks).

### Colors (`Resources/Graphic.xml`)
| Self | Name | Space | Value | Brand mapping |
|---|---|---|---|---|
| `Color/Black` | Black | CMYK | 0,0,0,100 | → Brand `Black` ✓ |
| `Color/C=0 M=100 Y=0 K=0` | C=0 M=100 Y=0 K=0 | CMYK | 0,100,0,0 | = Magenta, but Brand calls it `Magenta` ⚠ naming mismatch |
| `Color/C=85 M=35 Y=95 K=10` | C=85 M=35 Y=95 K=10 | CMYK | 85,35,95,10 | = `Dunkelgrün` ⚠ naming mismatch |
| `Color/C=0 M=0 Y=100 K=0` | C=0 M=0 Y=100 K=0 | CMYK | 0,0,100,0 | = `Gelb` ⚠ naming mismatch |
| `Color/Paper` | Paper | CMYK | 0,0,0,0 | = `White` ⚠ Scribus has no Paper |
| `Color/Registration` | Registration | Reg | 100,100,100,100 | → Brand `Registration` ✓ |
| `Color/Druckformat` | Druckformat | **Spot** | 0,0,0,100 | druck.at print-mark; Info-layer only |
| `Color/Endformat` | Endformat | CMYK | 0,100,100,0 | druck.at print-mark; Info-layer only |
| `Color/Sicherheit` | Sicherheit | **Spot** | 100,0,0,0 | druck.at print-mark; Info-layer only |
| `Color/Faltung` | Faltung | CMYK | 50,0,100,0 | druck.at fold-mark (could be re-purposed as the `Falz` spot if Info layer were printable — but it's NOT; Falz lines on the printable layer would need a separate `Falz` spot color emitted via `doc.add_color`) |
| `Color/Cyan`, `Color/Magenta`, `Color/Yellow` | (process inks, hidden) | | | converter skip |
| `Color/u85`, `Color/u87` | (auto-generated, hidden) | | | converter skip |

**Critical decision the planner must make:** how to map IDML-named colors to Brand-named colors. Three options:
1. **Rename in converter**: `Color/C=85 M=35 Y=95 K=10` → `Dunkelgrün` (etc.) by CMYK lookup. → Cleanest emitted build.py; works because Brand colors are CMYK-stable.
2. **Emit verbatim**: register each as a per-document color with the IDML name. → build.py has `doc.add_color("C=85 M=35 Y=95 K=10", cmyk=(85,35,95,10))` and TextFrames reference that name. Brand drift warnings.
3. **Hybrid**: rename if CMYK matches a Brand color, else verbatim.

Recommendation (echoed in Mapping Gap Analysis below): **option 3**. The 4 matches are unambiguous; the spot colors stay verbatim (and the Info-layer frames are dropped entirely).

### Fonts (`Resources/Fonts.xml`)
8 declared FontFamilies. The ones actually used in stories (via `AppliedFont`) are only:
- `Gotham Narrow` (with `FontStyle="Book"`, `Bold`, `Ultra`) — matches Brand fonts ✓
- `Vollkorn` (with `FontStyle="Black Italic"`) — = `Vollkorn Black Italic` ✓
- `Minion Pro` — only as bullets fallback (designmap.xml:208–212); not used in any rendered run
- `Myriad Pro`, `Kozuka Mincho Pro`, `Times` — Adobe defaults, irrelevant
The converter joins `AppliedFont + " " + FontStyle` to get Scribus's `FONT` string. **Format:** `"Gotham Narrow" + " " + "Book" → "Gotham Narrow Book"` ✓ matches what Scribus / Brand expects.

### Paragraph styles (`Resources/Styles.xml`)
6 `<ParagraphStyle>` defined; 5 actually applied in stories (with usage counts via grep on `AppliedParagraphStyle`):

| ParagraphStyle name | Usage count | Maps to Brand? |
|---|---|---|
| `[No paragraph style]` | (system) | n/a |
| `NormalParagraphStyle` | 11 | ⚠ generic; converter must register as `idml/NormalParagraphStyle` ParaStyle |
| `Absatzformat 1` | 7 | Custom — register as `idml/Absatzformat-1` |
| `Aufzählungen auf grünem Hintergrund` | 1 | Custom — register as `idml/aufzaehlungen-gruen` |
| `Fließtext auf grünem Hintergrund` | 4 | Custom — register as `idml/fliesstext-gruen` |
| `Headline in grünem Kasten` | 1 | Custom — register as `idml/headline-gruen` |

All five custom styles BasedOn `NormalParagraphStyle` or `Fließtext auf grünem Hintergrund` (per Styles.xml `<BasedOn>` properties). Converter must emit ParaStyle with `parent=` set to map this inheritance.

Story-level `<CharacterStyleRange>` ALSO carry per-run formatting (PointSize, FillColor, Leading, AppliedFont, FontStyle) which OVERRIDE the paragraph style. These map cleanly to `Run(fontsize, fcolor, font, ...)`.

### Character styles (`Resources/Styles.xml`)
Only `CharacterStyle/$ID/[No character style]` exists. **No custom char styles** to emit. ✓

---

## Mapping Gap Analysis — what's in this IDML that ISN'T yet in the ISSUE.md table

The ISSUE.md mapping table covers DocumentPreference, Layer, Spread/Page, Rectangle/Polygon, TextFrame+ParentStory, TextFrame containing Image, ParagraphStyleRange/CharacterStyleRange, Resources/Graphic.xml Color. Below is the **additional** corpus elements found in the source IDML that the converter must handle (or explicitly reject):

| IDML element | What it is in this IDML | DSL handling proposal | Status in mapping table |
|---|---|---|---|
| `<Oval>` | u185 on page 1: yellow circle (probably a sticker / pictogram) | → `Polygon(shape="ellipse", fill=..., layer=...)` (FRTYPE=1) | **MISSING from table** |
| `<Group>` (15 occurrences) | Logical grouping with own `ItemTransform`; children inherit cascade | Recurse into children; cascade `transform_cascade = parent @ group.ItemTransform`; group itself emits nothing | **MISSING from table** |
| Nested `<PDF>` inside `<Rectangle>` (≥8 occurrences) | Vector AI/PDF logo import (Grüne wordmark, Social-Media icons, Mail, Website) | → `ImageFrame(image="<repo-relative-path>", ...)` to pre-rasterized PNG in `shared/logos/` or `shared/assets/`. Strict mode raises `UnhandledElement(LinkResourceURI=…)` so the human decides per-icon what to point to | **MISSING from table** |
| `<Image>` (2 occurrences) | Raster JPEG / PSD import via `<Link LinkResourceURI=...>` | → `ImageFrame(image=…)` *or* — if asset available — `pack_inline_image(open(asset).read(), "jpg")` + `ImageFrame(inline_image_data=…)`. **Strict mode raises** if the source file isn't found in the IDML "Links/" sibling dir AND no asset mapping is supplied | partially covered: ISSUE.md mentions "TextFrame containing Image"; raster Image as direct page item is more common |
| `<Image>` PSD | u39b on page 2 — Photoshop file, EffectivePpi 314, scale 0.9547 | Same as above; Pillow can read PSD but only flat (no layers). Pre-convert PSD→PNG offline; reference as `image=` | **MISSING from table** |
| druck.at print-mark frames (Layer `ue6`) | 32 items on the Info layer using `Druckformat/Endformat/Sicherheit/Faltung` spot colors | **Skip entirely** — layer is non-printable in InDesign (`Printable="false"`) | **MISSING from table** |
| Rotated TextFrame (u347 on page 1) | 90° CCW rotation; `b,c ≠ 0` in ItemTransform | → `TextFrame(rotation_deg=90, ...)` + bbox-of-anchor-points geometry | partially covered: ISSUE.md mentions "Rotated frames"; but the *one* rotated frame in this corpus is the only test case |
| `<Br/>` inside `<CharacterStyleRange><Content>` | Soft line break inside a story | → `Run(text="...", separator="breakline"), Run(text="...", ...)` | partially covered: ISSUE.md mentions `ParagraphStyleRange/CharacterStyleRange`; `<Br/>` is the concrete separator |
| `<ParagraphStyleRange>` with `<Properties><BasedOn>` | Style inheritance chain | → `ParaStyle(parent=...)` | covered (issue says `ParaStyle`); needs explicit BasedOn handling |
| `<DocumentBleed*Offset = 5.669 pt` (≈2 mm) | Bleed | → `Document(...)` + `Page(bleed_mm=2.0)` — **NOT 3.0 like the sibling template** | covered conceptually; the *value* differs |
| Paper / Registration / Cyan / Magenta / Yellow colors | InDesign internal colors | Paper → `White`; Reg → `Registration`; CMY → skip (hidden, ColorOverride="Hiddenreserved") | partially covered |
| Spot color `Faltung` | `Color/Faltung` is a process CMYK (50,0,100,0), not declared spot. Sibling template's `Falz` IS spot. | Don't import as `Falz`; emit a separate `doc.add_color("Falz", cmyk=(100,0,0,0), spot=True)` to match the sibling-template convention | **MISSING from table** |
| Tables, Anchored Objects, Endnotes, Footnotes | Declared in designmap.xml but UNUSED in stories | Raise `UnhandledElement` if encountered (defensive); none in this corpus | n/a |
| EPS imports | NONE in this corpus | Raise `UnhandledElement` if encountered (defensive) | n/a |

### Critical conversion-flow recommendation
The walker should:
1. **Parse designmap.xml** → list layers; build `layer_id_to_name` map; **mark non-printable layers as "skip"**.
2. **Walk every spread**: for each top-level page-item:
   - If `ItemLayer` is in the skip set → drop.
   - If `<Group>` → recurse into children with `transform_cascade = parent_cascade @ ItemTransform`.
   - Otherwise dispatch on tag: `Rectangle | Polygon | Oval | TextFrame | Image`.
3. **Geometry helper** `frame_bbox_pt(transform_cascade, item_transform, path_points) → (x_pt, y_pt, w_pt, h_pt, rotation_deg)` is the load-bearing piece; this needs ~30 lines of code and unit tests. (Issue's "## Geometry" section spells out the algorithm.)
4. **Strict mode**: every unknown tag, unknown attribute, unknown nested element, unknown FillColor name → `raise UnhandledElement(f"... — extend tools/idml_to_dsl.py at <pointer>")`.

---

## Prior Art — Issue 2 RESEARCH

`.issues/archive/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/RESEARCH.md` is the most-similar prior issue (the original SLA→DSL converter). Two distillations relevant to issue 35:

1. **Locked decision D2 (sla_to_dsl, retained for idml_to_dsl):** "Converter emits typed DSL, not `raw_attrs` escape hatch." (RESEARCH.md:12). Every IDML attribute the converter touches needs a typed counterpart in the DSL. The DSL is rich enough today (ParaStyle has 30+ Optional fields, TextFrame has trail_attrs/default_style_attrs typed-channels). No new primitive type is required for the first cut.
2. **Locked decision D6 (strict mode):** "Raises a typed exception on any unhandled element/attribute. Better to fail loudly than emit a build.py that renders something subtly different." (RESEARCH.md:16). Mirror verbatim into `tools/idml_to_dsl.py`.

What does NOT carry over: D1 ("byte-equivalence target via sla_diff"), D3 ("baseline.pdf frozen for visual_diff"). The IDML target template has NO SLA original to diff against — `bin/validate` will skip it (validate:`grep -q ^original_sla:`). Visual fidelity is anchored against the IDML's own PDF export (`originals/<dir>/<name>.pdf`) **only if** the team wants a baseline; ISSUE.md says "visual_diff with sensible per-region tolerances if needed" so leave baseline.pdf out-of-scope unless the planner wires it in explicitly.

The DSL extension scope from issue 2 (CharStyle, ParaStyle, DocumentLayer, SoftShadow, NEXTITEM/BACKITEM, RADRECT, custom path, soft-hyphen, `<var name="pgno"/>`, fillRule, FRTYPE=2/3, inline_image_data) is **all already in the DSL** as of 2026-05-11; issue 35 does not need to extend the DSL primitives at all — only the converter walker.

---

## File/Line Citations Index

| Reference | File path | Lines |
|---|---|---|
| `sla_to_dsl.py` docstring + CLI examples | `tools/sla_to_dsl.py` | 1–28 |
| `UnhandledElement` exception | `tools/sla_to_dsl.py` | 59–62 |
| `_py_value` float-repr behaviour | `tools/sla_to_dsl.py` | 165–195 |
| `PAGEOBJECT_HANDLED_PRIM` allowlist | `tools/sla_to_dsl.py` | 362–411 |
| `_convert_pageobject` dispatch | `tools/sla_to_dsl.py` | 614–857 |
| Inline image capture (qCompress base64) | `tools/sla_to_dsl.py` | 203–216 |
| Output build.py scaffold emission | `tools/sla_to_dsl.py` | 1043–1093 |
| Master/Page emission with `page_xpos_pt` override | `tools/sla_to_dsl.py` | 1136–1209 |
| Chain detection | `tools/sla_to_dsl.py` | 893–922 |
| CLI / `main` | `tools/sla_to_dsl.py` | 1271–1285 |
| DSL public surface re-exports | `tools/sla_lib/builder/__init__.py` | 57–134 |
| `Document.__init__` signature | `tools/sla_lib/builder/document.py` | 140–200 |
| `Page` dataclass | `tools/sla_lib/builder/document.py` | 106–134 |
| `MM_TO_PT` / `PT_TO_MM` | `tools/sla_lib/builder/document.py` | 30–31 |
| `mm_to_pt()` helper | `tools/sla_lib/builder/document.py` | 46 |
| `Anchor` typed dataclass | `tools/sla_lib/builder/primitives.py` | 113–164 |
| `Run` typed dataclass | `tools/sla_lib/builder/primitives.py` | 293–353 |
| `PARAGRAPH_OVERRIDE_ATTRS` etc. allowlists | `tools/sla_lib/builder/primitives.py` | 53–86 |
| `_Frame` base dataclass | `tools/sla_lib/builder/primitives.py` | 433–495 |
| `TextFrame` dataclass | `tools/sla_lib/builder/primitives.py` | 548–614 |
| `ImageFrame` dataclass | `tools/sla_lib/builder/primitives.py` | 772–795 |
| `Polygon` dataclass | `tools/sla_lib/builder/primitives.py` | 855–920 |
| `pack_inline_image()` | `tools/sla_lib/builder/primitives.py` | 758–769 |
| `ParaStyle` dataclass | `tools/sla_lib/builder/styles.py` | 31–92 |
| `CharStyle` dataclass | `tools/sla_lib/builder/styles.py` | 94–126 |
| `DocumentLayer` dataclass | `tools/sla_lib/builder/styles.py` | 16–28 |
| `SoftShadow` dataclass | `tools/sla_lib/builder/styles.py` | 129–140 |
| `Brand.gruene_noe()` | `tools/sla_lib/builder/brand.py` | 79–149 |
| `frame_bbox_mm` (used by audit) | `tools/sla_lib/builder/bbox.py` | 49–74 |
| `FoldLine` block | `tools/sla_lib/builder/blocks.py` | 558–597 |
| `library.load` / `library.inject_into_frame` docs | `tools/sla_lib/builder/library.py` | 1–80 |
| Falzflyer build.py scaffold | `templates/kandidat-falzflyer-din-lang/build.py` | 1–67, 872–946 |
| Falzflyer `_add_styles` example | `templates/kandidat-falzflyer-din-lang/build.py` | 122–290 |
| Falzflyer meta.yml | `templates/kandidat-falzflyer-din-lang/meta.yml` | 1–294 |
| Falzflyer spec | `templates/_specs/kandidat-falzflyer-din-lang.md` | 1–100 |
| `tools/spec_check.py` docstring + CLI | `tools/spec_check.py` | 1–30 |
| `tools/audit_alignment.py` docstring + CLI | `tools/audit_alignment.py` | 1–57 |
| `tools/visual_diff.py` docstring + tolerance dataclass | `tools/visual_diff.py` | 1–80 |
| `tools/_export_pdf.py` (full file) | `tools/_export_pdf.py` | 1–7 |
| `bin/validate` template loop | `bin/validate` | 1–80 |
| `shared/ci.yml` brand + palette + styles + layers | `shared/ci.yml` | 1–128 |
| IDML root + spread refs | `/tmp/idml-research/designmap.xml` | 1, 83–164 |
| IDML layers | `/tmp/idml-research/designmap.xml` | 73–82 |
| IDML `DocumentPreference` page geometry | `/tmp/idml-research/Resources/Preferences.xml` | line containing `DocumentPreference` (~bottom) |
| IDML colors palette | `/tmp/idml-research/Resources/Graphic.xml` | 3–17 |
| IDML fonts (used subset) | `/tmp/idml-research/Resources/Fonts.xml` | 66–82 |
| IDML paragraph styles | `/tmp/idml-research/Resources/Styles.xml` | 52–100 |
| IDML master spread (empty) | `/tmp/idml-research/MasterSpreads/MasterSpread_ubb.xml` | 1–19 |
| IDML page 1 Rectangle example (vector PDF logo) | `/tmp/idml-research/Spreads/Spread_ueb.xml` | 56–98 |
| IDML rotated TextFrame (u347) | `/tmp/idml-research/Spreads/Spread_ueb.xml` | search `ItemTransform="-2.8327` |
| IDML raster Image (JPEG, page 2) | `/tmp/idml-research/Spreads/Spread_u108.xml` | search `Image Self="u2ce"` |
| IDML Story (single-paragraph w/ Br) | `/tmp/idml-research/Stories/Story_u519.xml` | 1–21 |
| Issue 2 RESEARCH locked decisions | `.issues/archive/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/RESEARCH.md` | 9–22 |

---

## Open questions for the planner

1. **Color mapping policy.** Auto-rename CMYK-matching IDML colors to Brand names (Dunkelgrün/Hellgrün/Gelb/Magenta), or emit verbatim by IDML name? **Recommendation:** auto-rename on exact CMYK match (Brand colors are the canonical, ci.yml-validated names); document the mapping table in the converter.
2. **Vector logo imports.** The IDML embeds `.ai` / `.pdf` vector logos as nested `<PDF>` inside Rectangles. Scribus/SLA has no native vector-import primitive; we must point ImageFrame at a *pre-rasterised PNG* (e.g. `shared/logos/gruene-weiss.png` which already exists in the repo). **Recommendation:** the converter detects "Rectangle with nested `<PDF>` Link" and emits `ImageFrame(image="<TODO: shared/logos/...>"; layer=LAYER_BILDER, anname="<TODO>")` and raises a soft warning ("vector logo at <bbox> — manually map after first emit"), or accepts a `--logo-map FILE.yml` CLI mapping {LinkResourceURI-basename → repo asset path}.
3. **Raster image bytes.** PSD (`Plakat dunkel für Flyer.psd`) is referenced but not bundled in the IDML — the IDML is a "links-not-embedded" package. We must pre-convert PSD→PNG offline OR fail the converter unless `--assets-dir` points at a directory containing the missing rasters. **Recommendation:** introduce `--assets-dir` resolving against `originals/<dir>/Links/` if the IDML's sibling `Links/` directory exists, otherwise require explicit path.
4. **Bleed = 2 mm (not 3).** Confirm the new template should keep IDML's 2 mm bleed (faithful to InDesign source), or coerce to the sibling falzflyer's 3 mm (Grüne-Quickguide standard). The two diverge — sibling falzflyer's `meta.yml.preflight.bleed_mm: 3` would not apply. **Recommendation:** follow IDML verbatim (2 mm); brand can decide later.
5. **Falz lines.** The IDML carries `Color/Faltung` (process 50,0,100,0) and has fold-mark visuals on the Info layer. The sibling template emits `Falz` spot color + `FoldLine` blocks on a printable `Falz` layer (so prepress can output a separate dieline). The IDML's Faltung is NOT a spot color and is on a non-printable layer. **Recommendation:** the emitted build.py adds Falz lines manually post-bootstrap (matching sibling convention); converter need not derive them from the IDML.
6. **Whether to use SimpleIDML or raw lxml.** Verified `pip install SimpleIDML` works (PyPI package `SimpleIDML`, module `simple_idml`, components `IDMLPackage`, `Spread`, `Page`, `Story`). SimpleIDML's helpers are useful for `style_groups` / `font_families` / `pages` traversal but its abstraction over spread items is thin (calls return lxml elements anyway). **Recommendation:** add `SimpleIDML` as a runtime dep (one-line `pip install` in the dev image), but only use it for the `IDMLPackage` extraction + `designmap` parse; walk spread XMLs directly with lxml for full attribute access (matches `sla_to_dsl.py`'s style).
