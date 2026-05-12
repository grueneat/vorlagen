# Plan: IDML → DSL converter — strict bootstrap (idml_to_dsl.py)

## Objective

Deliver `tools/idml_to_dsl.py`: a strict, one-shot converter that reads `originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml` and emits `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` against the existing `sla_lib.builder` primitives, mirroring the 7-phase shape of `tools/sla_to_dsl.py`. Done when:
1. `python3 tools/idml_to_dsl.py <idml> <out> --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2 --assets-dir originals/26-03-Leporello\ z-Falz\ 99x210\ 6-seitig\ gruenes\ Cover\ 2\ Ordner/Links/` runs clean (zero `UnhandledElement`).
2. The emitted `build.py` imports clean and `build(out)` produces a valid `template.sla` openable in Scribus.
3. `bin/render-gallery` produces a `preview.pdf` for the new template.
4. `tools/audit_alignment.py`, `bin/check-fontsizes`, `bin/check-stale-previews` all pass.
5. The ISSUE.md acceptance checklist is satisfied.

The converter is one-shot — re-running overwrites the emitted `build.py`. Same philosophy as `tools/sla_to_dsl.py`.

## Locked Decisions

Verbatim from the planner spec (do NOT re-debate during execution):

1. **Color policy** — auto-rename swatches to brand names on exact CMYK match against `shared/ci.yml` palette (`Dunkelgrün`, `Gelb`, `Magenta`, `Hellgrün`, `White` via `Color/Paper`, `Black`). Raise `UnhandledElement` on any other printable swatch. `Color/None`, `Color/Registration`, `Color/Cyan`/`Magenta`/`Yellow`/`Black` built-ins skipped silently.
2. **Vector-logo assets** — hard-raise. Collect every `<PDF>` child element's `Self` ID + LinkResourceURI basename across the document, then raise `UnhandledElement` ONCE at end-of-conversion with the full list. Human stages pre-rasterised PNG counterparts under `shared/logos/` (or new dir) and re-runs.
3. **Raster assets** — `--assets-dir` flag, default `originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links/`. Resolve `file:` URI basename against it. Raise `UnhandledElement` (with the missing-file list at end-of-conversion) if any referenced asset is absent.
4. **Bleed** — keep IDML's 2 mm verbatim. Emit a one-line comment in the generated `build.py` noting the deviation from brand-standard 3 mm.
5. **Falz lines** — converter does NOT emit `FoldLine`. Document in the emitted `build.py` header that the human must add them post-bootstrap, matching `templates/kandidat-falzflyer-din-lang/build.py` pattern (`from sla_lib.builder.blocks import FoldLine`).
6. **SimpleIDML dependency** — pin `'SimpleIDML==1.3.1'` in `Dockerfile.claude` pip block (~lines 73-79). Add `simple_idml.idml` to the sanity-probe import line. Dev-only dep — no `pyproject.toml` change because the repo has none; Dockerfile is the convention.

## Out of Scope

- Threaded TextFrames (`NextTextFrame != "n"`) — corpus has zero; raise `UnhandledElement`.
- Anchored objects (`<AnchoredObjectSetting>`) — corpus has zero; raise.
- Master-spread items (MasterSpread `ubb` is empty) — raise on any PageItem inside `MasterSpreads/`.
- Round-trip DSL→IDML.
- `.indd` binary format — refuse at entry point.
- `baseline.pdf` for `visual_diff` v1 (sibling falzflyer also has none).
- Fuzzy-snap CMYK→Brand matching — v1 is exact-match only.
- Tables, footnotes, endnotes, hyperlinks, RTL text — raise on encounter.
- Multi-IDML batch processing.
- Conditional text, XML-tagged structure roundtrip.

## Skills

<skills>
- @.claude/skills/python/SKILL.md (Python implementation patterns; .py files)
- @.claude/skills/git-committer/SKILL.md (conventional commit format with id prefix)
</skills>

If those skill files are missing/empty at execution time, proceed without them — the inline `<action>` blocks below are self-contained.

## Context

Issue: @.issues/35-idml-to-dsl-converter-strict-bootstrap/ISSUE.md
Research: @.issues/35-idml-to-dsl-converter-strict-bootstrap/RESEARCH.md
Codebase deep dive: @.issues/35-idml-to-dsl-converter-strict-bootstrap/research/codebase.md
Ecosystem (SimpleIDML/IDML spec): @.issues/35-idml-to-dsl-converter-strict-bootstrap/research/ecosystem.md
Pitfalls (coordinates/colors/fonts): @.issues/35-idml-to-dsl-converter-strict-bootstrap/research/pitfalls.md

Key files to read before coding:
- @tools/sla_to_dsl.py — the strict converter we mirror (philosophy, 7-phase shape, `UnhandledElement` style, `_py_value`/`PythonRepr` emitter, CLI shape at lines 1271-1285)
- @tools/sla_lib/builder/__init__.py — DSL public surface (re-exports at lines 57-89)
- @tools/sla_lib/builder/primitives.py — `Run`, `_Frame`, `TextFrame`, `ImageFrame`, `Polygon`, `pack_inline_image` (lines 113-920)
- @tools/sla_lib/builder/styles.py — `DocumentLayer`, `ParaStyle`, `CharStyle`, `SoftShadow` (lines 16-140)
- @tools/sla_lib/builder/document.py — `Document`, `Page`, `MM_TO_PT`, `PT_TO_MM`, `mm_to_pt` (lines 30-200)
- @tools/sla_lib/builder/brand.py — `Brand.gruene_noe()` (lines 79-149)
- @templates/kandidat-falzflyer-din-lang/build.py — sibling scaffold to mimic in emitted output (lines 1-67 for header/imports/constants; lines 872-946 for `build_template`/`build_preview`/`build` trio)
- @shared/ci.yml — brand palette (CMYK match table; lines 19-45)
- @Dockerfile.claude — pip block at lines 73-80; sanity probe near line 148

## Interfaces

The executor MUST use these contracts directly; do not explore the codebase for them.

<interfaces>
# ==========================================================================
# DSL primitives — all already exist; converter calls these, does not extend
# tools/sla_lib/builder/__init__.py public surface (lines 57-89)
# ==========================================================================
from sla_lib.builder import (
    Brand, Document, DocumentLayer,
    TextFrame, ImageFrame, Polygon, Run,
    ParaStyle, CharStyle, SoftShadow, Anchor,
    pack_inline_image,
)
from sla_lib.builder.blocks import FoldLine   # human adds post-bootstrap; NOT emitted by converter

# tools/sla_lib/builder/document.py
class Document:
    def __init__(self, title: str = "", template_id: str = "",
                 author: str = "Die Grünen Niederösterreich",
                 ci_path=None, *, brand: Optional[Brand] = None,
                 layers: Optional[list[DocumentLayer]] = None,
                 facing_pages: bool = False,
                 column_gap_default_pt: float = 11.0, unit: str = "mm",
                 deffont: str = "Gotham Narrow Book", defsize: float = 12,
                 first_page_num: int = 1, palette_replaces_ci: bool = False,
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
                 bleed_mm: float = 3.0, margins_mm=(10, 10, 10, 10),
                 master: str = "Normal", label: str = "",
                 page_xpos_pt: Optional[float] = None,
                 page_ypos_pt: Optional[float] = None) -> Page: ...
    def save(self, path: Path | str) -> None: ...

MM_TO_PT = 72.0 / 25.4   # document.py:30
PT_TO_MM = 25.4 / 72.0   # document.py:31
def mm_to_pt(value_mm: float) -> float: ...   # document.py:46

# tools/sla_lib/builder/primitives.py
@dataclass(frozen=True)
class Anchor:
    h: str = "left"; v: str = "top"; margin_mm: float = 0.0

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
    char_style: Optional[str] = None
    paragraph_style: Optional[str] = None    # PARENT on trailing <para/>
    paragraph_attrs: Optional[dict] = None
    separator: Optional[str] = None          # "para" | "breakline" | "tab" | "breakcol" | "breakframe"
    var: Optional[str] = None
    var_attrs: Optional[dict] = None

@dataclass
class _Frame:
    x_mm: float = 0; y_mm: float = 0; w_mm: float = 50; h_mm: float = 30
    anchor: Optional[Anchor] = None
    rotation_deg: float = 0                  # <-- IDML rotated frames flow here
    layer: int = 2                           # default Text layer index
    anname: str = ""
    custom_path: Optional[str] = None        # FRTYPE=3 verbatim path
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    xpos_pt: Optional[float] = None
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None
    is_full_bleed: bool = False

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""                          # DefaultStyle PARENT (ParaStyle name)
    fcolor: str = ""
    runs: Optional[list[Run]] = None
    columns: int = 1
    col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None
    default_linesp_mode: Optional[int] = None
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    next_item: Optional["TextFrame"] = None
    def link_to(self, other) -> "TextFrame": ...

@dataclass
class ImageFrame(_Frame):
    src: str = ""
    image: str = ""                          # converter emits image=
    layer: int = 1                           # default Bilder index
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1
    ratio: int = 1
    pic_art: int = 1
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None

@dataclass
class Polygon(_Frame):
    fill: str = "Black"
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0                           # default Hintergrund index
    shape: str = "rectangle"                 # 'rectangle' | 'ellipse'  ← Oval -> shape="ellipse"
    fill_shade: int = 100
    dash_pattern: Optional[tuple] = None

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """qCompress wrap + base64; pass to ImageFrame(inline_image_data=..., inline_image_ext=...)."""

# tools/sla_lib/builder/styles.py
@dataclass(frozen=True)
class DocumentLayer:
    name: str; visible: bool = True; printable: bool = True
    editable: bool = True; flow: bool = True
    transparent: float = 1.0; blend: int = 0
    outline: bool = False; layer_color: str = "#000000"

@dataclass(frozen=True)
class ParaStyle:
    name: str; parent: Optional[str] = None
    font: Optional[str] = None; fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    align: Optional[int] = None              # 0=left, 1=center, 2=right, 3=block
    linesp: Optional[float] = None; linesp_mode: Optional[int] = None
    language: Optional[str] = None
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    first_indent_pt: Optional[float] = None
    left_indent_pt: Optional[float] = None
    right_indent_pt: Optional[float] = None
    bcolor: Optional[str] = None; bshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    kern: Optional[float] = None
    is_default: bool = False
    # ... ~30 more Optional fields; see styles.py:31-92

@dataclass(frozen=True)
class CharStyle:
    name: str
    font: Optional[str] = None; fontsize: Optional[float] = None
    fcolor: Optional[str] = None; fshade: Optional[int] = None
    is_default: bool = False

# tools/sla_lib/builder/brand.py
@dataclass(frozen=True)
class Brand:
    name: str; short: str
    colors: dict[str, BrandColor]
    para_styles: dict[str, ParaStyle]
    char_styles: dict[str, CharStyle]
    layers: list[DocumentLayer]
    default_doc_attrs: dict[str, str]
    default_pdf_attrs: dict[str, str]
    deffont: str = "Gotham Narrow Book"
    defsize: float = 12.0
    column_gap_default_pt: float = 11.0
    bleed_mm: float = 3.0
    @classmethod
    def gruene_noe(cls, ci_path=None, defaults_path=None) -> "Brand": ...

# tools/sla_lib/builder/blocks.py — referenced ONLY by emitted build.py header
# comment; NOT instantiated by the converter.
@dataclass
class FoldLine:
    start_mm: tuple[float, float]; end_mm: tuple[float, float]
    layer_idx: int = 3; layer_name: str = "Falz"
    spot_color: str = "Falz"
    line_width_pt: float = 0.5
    dash_pattern: tuple[float, float] = (3.0, 1.5)
    anname: str = "Falzlinie"

# ==========================================================================
# SimpleIDML 1.3.1 — read-only API surface we will use
# ==========================================================================
from simple_idml.idml import IDMLPackage
# pkg = IDMLPackage(path_to_idml)               # context manager
# pkg.spreads_objects   -> list[Spread]         # use this, not pkg.spreads (filenames only)
# pkg.pages             -> list[Page]           # flat across all spreads
# pkg.stories           -> list[str]            # Story XML filenames
# pkg.story_ids         -> list[str]
# pkg.designmap         -> Designmap with .spread_nodes, .layer_nodes, .active_layer
# pkg.font_families     -> list[lxml.etree._Element]  # <FontFamily>
# pkg.style_groups      -> list[lxml.etree._Element]  # Root{Character,Paragraph,...}StyleGroup
#                                              # NOTE: ISSUE.md mentions
#                                              # pkg.character_styles / pkg.paragraph_styles
#                                              # — THOSE ATTRS DO NOT EXIST. Use style_groups.
# pkg.graphic           -> Graphic helper for Resources/Graphic.xml
# pkg.read(path) / pkg.open(path)              # raw XML bytes for any path inside the IDML

# Per Spread:
# spread.pages          -> list[Page]
# spread.node, spread.dom

# Per Page:
# page.geometric_bounds -> [Decimal, Decimal, Decimal, Decimal]  # y1 x1 y2 x2
# page.item_transform   -> [Decimal × 6]                          # a b c d tx ty
# page.coordinates      -> {"x1", "y1", "x2", "y2"} in spread-coord space
# page.page_items       -> list[lxml.etree._Element]  # toplevel siblings of <Page>
# page.is_recto, page.face

# ==========================================================================
# Strict-mode exception shape (mirror sla_to_dsl.py:59-62 verbatim)
# ==========================================================================
class UnhandledElement(Exception):
    """Raised by the strict-mode converter when an element/attribute has no
    typed DSL counterpart. The traceback identifies what to extend."""
# Message pattern: f"<element-kind> Self={self_id!r} in {spread_filename!r}: "
#                  f"<unhandled aspect> (extend tools/idml_to_dsl.py:_function_name)"

# ==========================================================================
# Color map (locked decision #1) — hard-coded at module top
# ==========================================================================
# Exact CMYK match to shared/ci.yml. Raise on any printable swatch NOT in this set.
# Source: shared/ci.yml:19-45 cross-referenced against IDML Resources/Graphic.xml.
COLOR_CMYK_TO_BRAND = {
    (0,   0,   0,   100): "Black",
    (0,   0,   0,   0):   "White",         # also IDML "Color/Paper"
    (85,  35,  95,  10):  "Dunkelgrün",
    (69,  0,   100, 0):   "Hellgrün",
    (0,   0,   100, 0):   "Gelb",
    (0,   100, 0,   0):   "Magenta",
}
# Silently skipped (NOT printable / IDML built-ins): Color/None, Color/Registration,
# Color/Cyan, Color/Magenta (process ink), Color/Yellow, Color/Black (process).
# These show up in Resources/Graphic.xml with ColorOverride containing "Hiddenreserved"
# or names exactly matching process inks; suppress without raising.
</interfaces>

## Commit Format

Format: conventional with issue-id prefix (per `.issues/config.yaml`).
Example: `35: feat(idml): add IDML→DSL converter skeleton with UnhandledElement`
Pattern: `35: {type}({scope}): {description}` where `type ∈ {feat, fix, test, refactor, docs, chore}` and `scope ∈ {idml, docker, tests, template, …}`.

## Tasks

<task id="1" title="Bootstrap converter skeleton + Dockerfile pin">
  <action>
  Create `tools/idml_to_dsl.py` with:

  1. Top-of-file module docstring mirroring `tools/sla_to_dsl.py:1-28`. Include:
     - "One-shot bootstrap; not run in CI."
     - "Re-running REPLACES the emitted build.py and discards manual edits."
     - License: BSD (matches repo convention).
     - "noqa: NEVER import `simple_idml.indesign` — pulls in LGPL `suds-py3`."
     - Usage example: `python3 tools/idml_to_dsl.py originals/.../foo.idml templates/<slug>/build.py --template-id <slug> --assets-dir originals/.../Links/`

  2. Imports: `argparse`, `re`, `sys`, `pathlib.Path`, `typing.Optional`, `urllib.parse.unquote`, `lxml.etree`. Then `from simple_idml.idml import IDMLPackage` wrapped in try/except ImportError that prints `"Install SimpleIDML: pip install SimpleIDML==1.3.1"` and `sys.exit(2)`.

  3. `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `from sla_lib.builder import (...)` for every primitive listed in `<interfaces>`.

  4. Module-level constants:
     - `ROOT = Path(__file__).resolve().parent.parent`
     - `CI_YAML = ROOT / "shared" / "ci.yml"`
     - `PT_TO_MM = 25.4 / 72.0`
     - `MM_TO_PT = 72.0 / 25.4`
     - `COLOR_CMYK_TO_BRAND` dict from `<interfaces>` block above
     - `IDML_BUILTIN_COLORS_SKIP = {"Color/None", "Color/Registration", "Color/Cyan", "Color/Magenta", "Color/Yellow", "Color/Black"}` — but NOTE: `Color/Black` CMYK matches our `Black` so prefer letting the CMYK matcher handle it; only skip if `ColorOverride` contains "Hiddenreserved" OR `Name` is in the process-ink list `{"Cyan","Magenta","Yellow"}`. Treat `Color/Registration` via the `Self` string match (it has Space=MixedInk style).

  5. `class UnhandledElement(Exception): ...` mirroring `sla_to_dsl.py:59-62`. Docstring identical in spirit.

  6. `_SECURE_XMLPARSER = etree.XMLParser(resolve_entities=False, no_network=True, dtd_validation=False, load_dtd=False)` — used for any direct `etree.parse`/`fromstring` (defence-in-depth, even though SimpleIDML's internals are already safe under lxml 5.4).

  7. `main(argv)` function (mirror `sla_to_dsl.py:1271-1285`):
     ```python
     def main(argv=None) -> int:
         ap = argparse.ArgumentParser(description="Strict IDML→DSL converter (one-shot bootstrap).")
         ap.add_argument("source", type=Path, help="Input .idml file")
         ap.add_argument("output", type=Path, help="Output build.py path")
         ap.add_argument("--template-id", required=True, help="Slug baked into Document(template_id=...)")
         ap.add_argument("--assets-dir", type=Path, required=False,
             default=Path("originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links"),
             help="Directory containing the IDML's linked raster assets (resolves file: URIs by basename).")
         args = ap.parse_args(argv)
         try:
             convert(args.source, args.output, args.template_id, args.assets_dir)
         except UnhandledElement as e:
             print(f"UnhandledElement: {e}", file=sys.stderr)
             return 2
         return 0

     if __name__ == "__main__":
         sys.exit(main())
     ```

  8. `def convert(source: Path, output: Path, template_id: str, assets_dir: Path) -> None:` — for THIS task, just open the IDML and print a one-line summary. Later tasks fill in the 7 phases.
     ```python
     def convert(source, output, template_id, assets_dir):
         if not source.exists():
             raise UnhandledElement(f"Source IDML not found: {source}")
         # Reject .indd: first 4 bytes of IDML must be PK\x03\x04 (ZIP magic).
         with source.open("rb") as f:
             head = f.read(4)
         if head != b"PK\x03\x04":
             raise UnhandledElement(
                 f"{source.name} is not a valid IDML (ZIP). "
                 f"If this is a .indd, re-export from InDesign: File > Export > InDesign Markup (IDML)."
             )
         with IDMLPackage(str(source)) as pkg:
             print(f"OK: opened {source.name} — {len(pkg.spreads_objects)} spreads, "
                   f"{len(pkg.stories)} stories")
     ```

  9. Also edit `Dockerfile.claude` (locked decision #6):
     - Append `'SimpleIDML==1.3.1'` (with trailing line continuation) to the existing `pip3 install --break-system-packages --no-cache-dir` block at lines 76-80. Match the existing 8-space indent and `\` continuation style.
     - Find the sanity-probe `python3 -c "import lxml.etree, yaml; ..."` line (search for `python deps ok` — currently near line 148 area, OR in another sanity block). Extend it to: `python3 -c "import lxml.etree, yaml, simple_idml.idml; print('python deps ok')"`. If no such line exists yet, ADD it just after the SimpleIDML pip install line.
  </action>
  <files>
  tools/idml_to_dsl.py (new)
  Dockerfile.claude (modify pip block + sanity probe)
  </files>
  <verify>
  <automated>
  # Skeleton imports clean
  python3 -c "import sys; sys.path.insert(0, 'tools'); from idml_to_dsl import UnhandledElement, COLOR_CMYK_TO_BRAND, convert, main; print('OK', len(COLOR_CMYK_TO_BRAND))"
  # SimpleIDML resolves
  python3 -c "from simple_idml.idml import IDMLPackage; print('simple_idml.idml OK')"
  # Smoke: opening the target IDML prints the OK banner
  python3 tools/idml_to_dsl.py "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" /tmp/dummy_out.py --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2 2>&1 | head -5
  # Dockerfile pip block has the pin
  grep -q "SimpleIDML==1.3.1" Dockerfile.claude
  # Sanity probe includes simple_idml.idml
  grep -q "simple_idml.idml" Dockerfile.claude
  </automated>
  </verify>
  <done>tools/idml_to_dsl.py exists with CLI + UnhandledElement + .indd-reject guard; opens the target IDML cleanly; Dockerfile.claude pins SimpleIDML==1.3.1 and probes simple_idml.idml.</done>
</task>

<task id="2" title="Coordinate math helpers + unit tests" tdd="true">
  <action>
  Add coordinate math to `tools/idml_to_dsl.py` as pure functions (no IDML I/O):

  1. `_parse_matrix(s: str) -> tuple[float,float,float,float,float,float]` — split `"a b c d tx ty"` into 6 floats. Reject (raise UnhandledElement) on != 6 tokens.

  2. `_matrix_compose(parent: tuple, child: tuple) -> tuple` — multiply two affine `(a,b,c,d,tx,ty)` 6-tuples per Adobe row-vector convention (child applies first, then parent). The 3×3 form:
     ```
     | a  b  0 |
     | c  d  0 |
     | tx ty 1 |
     ```
     A point `(x,y)` maps via `[x y 1] × M`. To compose "child then parent" so that `apply(parent, apply(child, p)) == apply(compose(parent,child), p)`, write:
     ```python
     def _matrix_compose(parent, child):
         a1,b1,c1,d1,tx1,ty1 = child
         a2,b2,c2,d2,tx2,ty2 = parent
         return (
             a1*a2 + b1*c2,
             a1*b2 + b1*d2,
             c1*a2 + d1*c2,
             c1*b2 + d1*d2,
             tx1*a2 + ty1*c2 + tx2,
             tx1*b2 + ty1*d2 + ty2,
         )
     ```
     (Verify with identity: `compose(I, M) == M`; `compose(M, I) == M`; translations add.)

  3. `_apply_matrix(M: tuple, x: float, y: float) -> tuple[float,float]`:
     ```python
     a,b,c,d,tx,ty = M
     return (a*x + c*y + tx, b*x + d*y + ty)
     ```

  4. `_inner_bbox_from_anchors(anchors: list[tuple[float,float]]) -> tuple[float,float,float,float]` — return `(min_x, min_y, max_x, max_y)` of the raw PathPointArray anchor coords. (For TextFrames the anchors are symmetric around (0,0) — that's the "frame-center inner origin" idiosyncrasy.)

  5. `_compute_page_local_bbox_pt(item_transform_str: str, anchors: list[tuple[float,float]], ancestor_transforms: list[str], spread_item_transform_str: str, page_item_transform_str: str) -> tuple[float,float,float,float,float]`:

     Returns `(x_pt, y_pt, w_pt, h_pt, rotation_deg)` in page-top-left coordinates.

     Algorithm (locked decision math, per RESEARCH.md "3-stacked cascade"):
     1. Parse each transform string via `_parse_matrix`.
     2. Compose ancestor groups outer→inner: `M_ancestors = identity; for parent_t in ancestor_transforms (outermost first): M_ancestors = _matrix_compose(parent_t, M_ancestors)`. (Order: outermost group on the LEFT of the chain so inner-space points pass through inner→outer.)
     3. Compose item: `M_item_to_spread = _matrix_compose(M_ancestors, item_transform)`. (Item is innermost; its transform is applied first when mapping inner→spread.)
     4. Apply to all anchors → spread-space points.
     5. Spread-stack origin: apply `spread_item_transform` to (0,0) — that's where the spread sits in pasteboard. Subtract from each transformed anchor (most spreads are identity, but Spread `u108` has y-offset 786.61 pt — see P-COORD-5).
     6. Page origin in spread: from `page_item_transform`, the translation `(tx, ty)` is the page-top-left in spread-stack coords. Subtract from each anchor.
     7. AABB: `min_x, min_y, max_x, max_y` of the per-page-space points.
     8. Rotation: `rotation_deg = math.degrees(math.atan2(M_item_to_spread.b, M_item_to_spread.a))`. Sign: IDML CCW positive. Scribus DSL `rotation_deg` also CCW (per `tools/sla_lib/builder/bbox.py:5-8`); if convention sign-flips during emit testing, document in code comment.
     9. Reject non-uniform scaling / shear in v1: if `abs(sqrt(a²+b²) - sqrt(c²+d²)) > 0.01` or `abs(a*c + b*d) > 0.01`, raise `UnhandledElement(f"Sheared/non-uniform-scaled item; only rotation+uniform-scale supported (extend tools/idml_to_dsl.py:_compute_page_local_bbox_pt)")`.

  6. `_pt_to_mm(value_pt: float) -> float: return value_pt * PT_TO_MM` — wrapper for clarity.

  7. Add `tests/unit/test_idml_geometry.py` with the following cases (use pytest; the repo has no pytest setup, but pytest is in the container — `pip3 show pytest` works):
     ```python
     import sys; from pathlib import Path
     sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
     from idml_to_dsl import (_parse_matrix, _matrix_compose, _apply_matrix,
         _inner_bbox_from_anchors, _compute_page_local_bbox_pt)
     import pytest, math

     IDENT = "1 0 0 1 0 0"

     def test_identity_compose():
         I = _parse_matrix(IDENT)
         M = _parse_matrix("0.5 0 0 0.5 10 20")
         assert _matrix_compose(I, M) == M
         assert _matrix_compose(M, I) == M

     def test_translation_only():
         M = _parse_matrix("1 0 0 1 100 200")
         assert _apply_matrix(M, 0, 0) == pytest.approx((100, 200))
         assert _apply_matrix(M, 5, 7) == pytest.approx((105, 207))

     def test_axis_aligned_rectangle():
         # Rectangle at spread (100,100), 50×30 pt, no rotation, no ancestors,
         # spread identity, page origin at (-420.94, -140.31) per target IDML.
         anchors = [(0,0),(50,0),(50,30),(0,30)]
         x,y,w,h,rot = _compute_page_local_bbox_pt(
             item_transform_str="1 0 0 1 100 100",
             anchors=anchors, ancestor_transforms=[],
             spread_item_transform_str=IDENT,
             page_item_transform_str="1 0 0 1 -420.94 -140.31",
         )
         assert (w, h) == pytest.approx((50, 30))
         assert rot == pytest.approx(0, abs=1e-6)
         # Item lives at page-local (100 - (-420.94), 100 - (-140.31)) = (520.94, 240.31)
         assert x == pytest.approx(520.94)
         assert y == pytest.approx(240.31)

     def test_rotated_90deg_textframe():
         # Mimics target IDML's u347: 90° CCW, TextFrame inner anchors symmetric around 0
         # ItemTransform="-2.83e-16 -0.9999 0.9999 -2.83e-16 124.68 180.78"
         anchors = [(-49.5,-148.82),(49.5,-148.82),(49.5,148.82),(-49.5,148.82)]
         x,y,w,h,rot = _compute_page_local_bbox_pt(
             item_transform_str="0 -1 1 0 124.68 180.78",
             anchors=anchors, ancestor_transforms=[],
             spread_item_transform_str="1 0 0 1 0 786.61",
             page_item_transform_str="1 0 0 1 -420.94 -140.31",
         )
         # After 90° CCW, the inner 99×297.64 rectangle becomes 297.64×99 AABB
         assert (w, h) == pytest.approx((297.64, 99), rel=1e-3)
         assert abs(rot - 90) < 1 or abs(rot + 90) < 1 or abs(abs(rot) - 90) < 1

     def test_rotated_9deg_frame():
         # u186 cover: "0.9877 -0.1564 0.1564 0.9877 11.54 233.10"
         anchors = [(0,0),(60,0),(60,40),(0,40)]
         _,_,w,h,rot = _compute_page_local_bbox_pt(
             item_transform_str="0.9877 -0.1564 0.1564 0.9877 11.54 233.10",
             anchors=anchors, ancestor_transforms=[],
             spread_item_transform_str=IDENT,
             page_item_transform_str="1 0 0 1 -420.94 -140.31",
         )
         # 9° rotation → AABB grows
         assert w > 60 and h > 40
         assert abs(rot - 9) < 0.5 or abs(rot + 9) < 0.5

     def test_nested_group():
         # Outer group translates (50,50); inner group rotates 90°; item at (10,0)..(20,10)
         anchors = [(0,0),(10,0),(10,10),(0,10)]
         x,y,w,h,rot = _compute_page_local_bbox_pt(
             item_transform_str="1 0 0 1 10 0",
             anchors=anchors,
             ancestor_transforms=["0 -1 1 0 0 0", "1 0 0 1 50 50"],  # inner→outer
             spread_item_transform_str=IDENT,
             page_item_transform_str=IDENT,
         )
         # Item passes through inner→outer correctly
         assert (w, h) == pytest.approx((10, 10), abs=0.01)
         assert abs(rot - 90) < 1 or abs(rot + 90) < 1

     def test_inner_bbox_from_anchors():
         assert _inner_bbox_from_anchors([(0,0),(50,30),(50,0),(0,30)]) == (0,0,50,30)
         assert _inner_bbox_from_anchors([(-5,-3),(5,-3),(5,3),(-5,3)]) == (-5,-3,5,3)

     def test_shear_rejected():
         with pytest.raises(Exception):
             _compute_page_local_bbox_pt(
                 item_transform_str="1 0.5 0 1 0 0",  # shear
                 anchors=[(0,0),(10,0),(10,10),(0,10)],
                 ancestor_transforms=[], spread_item_transform_str=IDENT,
                 page_item_transform_str=IDENT,
             )
     ```

  IMPORTANT: pick `ancestor_transforms` ordering carefully — adjust the order/iteration in `_compute_page_local_bbox_pt` so the tests pass. Document the chosen order in a docstring. Re-verify ordering by manually walking the 1-rotated-frame target IDML output before declaring this task done.
  </action>
  <files>
  tools/idml_to_dsl.py (extend with helpers)
  tests/unit/test_idml_geometry.py (new)
  </files>
  <verify>
  <automated>
  python3 -m pytest tests/unit/test_idml_geometry.py -x -v
  </automated>
  </verify>
  <done>All 7 unit tests pass; helpers exposed from tools/idml_to_dsl.py; non-uniform scale/shear raises UnhandledElement.</done>
</task>

<task id="3" title="Resource walker: doc meta + layers + masters + designmap parse">
  <action>
  Implement Phase 1-3 of the converter in `tools/idml_to_dsl.py` and a code-emitter shell. Build out the `convert()` function to produce a SKELETON `build.py` that already has correct Document(), DocumentLayers, masters, and the empty page scaffold — but no per-page items yet (those land in tasks 6-7).

  1. Add a `PythonRepr` class mirroring `sla_to_dsl.py:140-162` — minimal line buffer + indent tracker:
     ```python
     class PythonRepr:
         def __init__(self):
             self.lines: list[str] = []
             self.indent = 0
         def w(self, s: str = "") -> None: self.lines.append("    " * self.indent + s)
         def render(self) -> str: return "\n".join(self.lines) + "\n"
     ```

  2. Add `_py_value(v)` mirroring `sla_to_dsl.py:165-195`. Use `repr()` for floats (preserves 17-digit precision). Strings, ints, bools, None, lists, tuples, dicts recursively.

  3. Add `_emit_call(out: PythonRepr, cls_name: str, kwargs: dict, multiline: bool = True)` — emits constructor calls. For task 3 we only need the simple form (multiline kwargs, one per line).

  4. Implement Phase A — open the IDML and extract document-level meta:
     ```python
     def _read_doc_preferences(pkg: IDMLPackage) -> dict:
         # Returns {page_width_pt, page_height_pt, bleed_top_pt, bleed_bottom_pt,
         #         bleed_inside_pt, bleed_outside_pt, facing_pages}
         prefs_xml = pkg.read("Resources/Preferences.xml")
         root = etree.fromstring(prefs_xml, parser=_SECURE_XMLPARSER)
         dp = root.find(".//DocumentPreference")
         if dp is None:
             raise UnhandledElement("Resources/Preferences.xml has no DocumentPreference")
         d = {
             "page_width_pt":   float(dp.get("PageWidth", "0")),
             "page_height_pt":  float(dp.get("PageHeight", "0")),
             "bleed_top_pt":    float(dp.get("DocumentBleedTopOffset", "0")),
             "bleed_bottom_pt": float(dp.get("DocumentBleedBottomOffset", "0")),
             "bleed_inside_pt": float(dp.get("DocumentBleedInsideOrLeftOffset", "0")),
             "bleed_outside_pt":float(dp.get("DocumentBleedOutsideOrRightOffset", "0")),
             "facing_pages":    dp.get("FacingPages", "false").lower() == "true",
         }
         # Sanity: all four bleeds match (target IDML has 5.669292 pt uniformly = 2mm)
         bleeds = (d["bleed_top_pt"], d["bleed_bottom_pt"], d["bleed_inside_pt"], d["bleed_outside_pt"])
         if max(bleeds) - min(bleeds) > 0.1:
             raise UnhandledElement(
                 f"DocumentPreference has non-uniform bleeds {bleeds!r}; "
                 f"v1 only supports uniform bleed (extend tools/idml_to_dsl.py:_read_doc_preferences)"
             )
         return d
     ```

  5. Implement Phase B — layers from designmap.xml:
     ```python
     def _read_layers(pkg: IDMLPackage) -> list[dict]:
         # Returns ordered [{self_id, name, visible, printable, locked}, ...]
         designmap_xml = pkg.read("designmap.xml")
         root = etree.fromstring(designmap_xml, parser=_SECURE_XMLPARSER)
         layers = []
         for L in root.findall(".//Layer"):
             layers.append({
                 "self_id":   L.get("Self"),
                 "name":      L.get("Name", ""),
                 "visible":   L.get("Visible", "true").lower() == "true",
                 "printable": L.get("Printable", "true").lower() == "true",
                 "locked":    L.get("Locked", "false").lower() == "true",
             })
         if not layers:
             raise UnhandledElement("designmap.xml has no <Layer> elements")
         return layers
     ```
     Build a `layer_id_to_idx` map for use in tasks 6-7: layer 0 = first in document order (Gestaltung = uba = idx 0; Info = ue6 = idx 1). When emitting build.py, the layers list passed to `Document(layers=[...])` controls this ordering.

  6. Implement Phase C — master spread strictness (locked decision: empty masters only):
     ```python
     def _check_masters_empty(pkg: IDMLPackage) -> None:
         for ms in [s for s in pkg.spreads if "MasterSpread" in s or "Master" in s]:
             # Cheap detection — true master files live under MasterSpreads/
             pass
         # Walk MasterSpreads/ directly
         for member in pkg.namelist():
             if not member.startswith("MasterSpreads/"):
                 continue
             xml = pkg.read(member)
             root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
             for tag in ("Rectangle", "Polygon", "Oval", "TextFrame", "Image", "Group", "PDF", "EPS"):
                 found = root.findall(f".//{tag}")
                 if found:
                     raise UnhandledElement(
                         f"MasterSpread {member} contains <{tag}> page items "
                         f"(v1 only supports empty masters; extend tools/idml_to_dsl.py:_check_masters_empty)"
                     )
     ```

  7. Implement Phase D — emit the build.py header & Document scaffold:
     ```python
     def _emit_header(out: PythonRepr, template_id: str, idml_name: str) -> None:
         out.w(f'"""{template_id} — DSL build entry point.')
         out.w("")
         out.w(f"Auto-generated from {idml_name} by tools/idml_to_dsl.py.")
         out.w("Hand-edit thereafter; this file is the source of truth.")
         out.w("")
         out.w("NOTE: bleed_mm=2.0 below matches the IDML verbatim. Brand standard")
         out.w("is 3.0 mm; coerce only after team review.")
         out.w("")
         out.w("Falz lines are NOT emitted by the converter — add manually post-bootstrap")
         out.w("matching templates/kandidat-falzflyer-din-lang/build.py: import FoldLine")
         out.w("from sla_lib.builder.blocks and instantiate at panel boundaries x=99/198 mm.")
         out.w('"""')
         out.w("from __future__ import annotations")
         out.w("import sys")
         out.w("from pathlib import Path")
         out.w("")
         out.w("HERE = Path(__file__).resolve().parent")
         out.w('sys.path.insert(0, str(HERE.parents[1] / "tools"))')
         out.w("")
         out.w("from sla_lib.builder import (  # noqa: E402")
         out.w("    Brand, Document, DocumentLayer,")
         out.w("    TextFrame, ImageFrame, Polygon, Run, ParaStyle, Anchor,")
         out.w("    pack_inline_image,")
         out.w(")")
         out.w("")
         out.w("INJECT_MAP: dict[str, str] = {}")
         out.w("")
     ```

  8. Implement Phase E — emit `build_template`/`build_preview`/`build` skeleton with Document() + add_master + add_page calls. Sizes come from `_read_doc_preferences`. Bleed = `bleed_top_pt * PT_TO_MM` (the locked 2.0 mm). Layers from `_read_layers` mapped to `DocumentLayer(name=..., printable=..., visible=..., editable=not locked)`.

     Critical: the page count = number of spreads × pages-per-spread. Target IDML has 2 spreads × 1 page = 2 pages. For each `<Page>` in `pkg.pages`, emit `pageN = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=2.0, margins_mm=(0,0,0,0), master="Normal")`.

  9. Wire `convert()` to:
     1. Open IDML, validate `.indd`-reject.
     2. `_read_doc_preferences(pkg)`.
     3. `_read_layers(pkg)`.
     4. `_check_masters_empty(pkg)`.
     5. Emit header + Document() + add_master + add_page calls.
     6. Reserved hooks for colors (task 4), styles (task 5), page items (tasks 6-7).
     7. Emit footer: `doc.save(out_path); print(f"OK: {out_path}")`.
     8. Write the rendered Python source to `output`.

  10. Ensure the emitted `build.py`, even with no page items yet, runs cleanly (`python3 templates/<slug>/build.py` produces a `template.sla` that opens in Scribus headless).
  </action>
  <files>
  tools/idml_to_dsl.py (extend with phases A-E)
  </files>
  <verify>
  <automated>
  # Run converter end-to-end; expect zero UnhandledElement at this skeleton level
  python3 tools/idml_to_dsl.py "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" /tmp/test_build.py --template-id test
  # Emitted build.py imports cleanly
  python3 -c "import sys; sys.path.insert(0, 'tools'); import importlib.util; spec = importlib.util.spec_from_file_location('b', '/tmp/test_build.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('OK: build.py imports')"
  # Document has 2 pages, A4-quer, bleed_mm=2.0
  python3 -c "import sys; sys.path.insert(0, 'tools'); import importlib.util; spec = importlib.util.spec_from_file_location('b', '/tmp/test_build.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); from pathlib import Path; out = Path('/tmp/test.sla'); m.build(out); assert out.exists(); print('OK: template.sla saved')"
  </automated>
  </verify>
  <done>Converter produces a skeleton build.py with correct Document(title, template_id, brand, layers), 2 pages of 297×210 mm with bleed_mm=2.0, and the file runs to produce a Scribus-readable template.sla.</done>
</task>

<task id="4" title="Color phase: brand-rename on CMYK match, raise on non-brand printable">
  <action>
  Add Phase F (colors) to `tools/idml_to_dsl.py` between layers and styles in the convert() flow.

  1. `_parse_color_value(s: str) -> tuple[int,int,int,int]` — split `"85 35 95 10"` into 4 ints (CMYK %). For floats coming through, round to nearest int (target IDML uses integer percentages). Raise if not 4 tokens or any out of [0..100].

  2. `_read_colors(pkg: IDMLPackage) -> dict[str, dict]`:
     Walk `Resources/Graphic.xml`; for each `<Color>` element collect:
     ```python
     {
       self_id: "Color/C=85 M=35 Y=95 K=10",
       name:    "C=85 M=35 Y=95 K=10",
       space:   "CMYK" | "RGB" | "LAB" | "MixedInk",
       model:   "Process" | "Spot",
       cmyk:    (c, m, y, k) | None,
       hidden:  bool (ColorOverride contains "Hiddenreserved"),
       is_printable_used: filled-in later by scanning FillColor refs
     }
     ```
     Use `pkg.graphic` if convenient or `etree.fromstring(pkg.read("Resources/Graphic.xml"), parser=_SECURE_XMLPARSER)`.

  3. `_collect_used_fillcolors(pkg: IDMLPackage, printable_layer_ids: set[str]) -> set[str]`:
     Walk every spread XML; for each PageItem (Rectangle, Polygon, Oval, TextFrame, Group, Image), if its `ItemLayer` attribute is in `printable_layer_ids`, collect its `FillColor`, `StrokeColor`, and (for TextFrame children) every `<CharacterStyleRange>`'s `FillColor` / `StrokeColor`. Return the set of Self references used.
     Plus: walk every Story XML in `pkg.stories` and collect `FillColor`/`StrokeColor` from `<CharacterStyleRange>` and `<ParagraphStyleRange>` — they apply on text regardless of frame layer.

  4. Phase F logic:
     ```python
     def _emit_colors(out, pkg, printable_layer_ids) -> dict[str, str]:
         # Returns map: idml_color_self -> dsl_color_name (brand-renamed or local)
         colors = _read_colors(pkg)
         used = _collect_used_fillcolors(pkg, printable_layer_ids)

         resolved: dict[str, str] = {}

         # Special: Color/Paper → "White" (CMYK 0,0,0,0)
         # Special: Color/None / Swatch/None → None (frame.fill = None)
         # Built-in process inks and Registration: silently skipped
         IDML_BUILTIN_SKIP = {"Color/Cyan", "Color/Magenta", "Color/Yellow",
                              "Color/Registration", "Color/None", "Swatch/None"}

         for self_id, c in colors.items():
             if self_id in IDML_BUILTIN_SKIP:
                 continue
             if c["hidden"] and self_id not in used:
                 continue  # process inks declared but unused
             if self_id == "Color/Paper":
                 resolved[self_id] = "White"
                 continue
             if c["space"] != "CMYK" or c["cmyk"] is None:
                 if self_id in used:
                     raise UnhandledElement(
                         f"Color {self_id!r} has unsupported space={c['space']!r} "
                         f"(extend tools/idml_to_dsl.py:_emit_colors)"
                     )
                 continue
             cmyk = c["cmyk"]
             brand_name = COLOR_CMYK_TO_BRAND.get(cmyk)
             if brand_name is not None:
                 resolved[self_id] = brand_name  # auto-rename to brand (decision #1)
                 # No add_color emit — brand palette already has it
                 continue
             # Non-brand printable swatch: raise (decision #1)
             if self_id in used:
                 raise UnhandledElement(
                     f"Color {self_id!r} CMYK={cmyk} does not match shared/ci.yml brand "
                     f"palette and is used by a printable PageItem. "
                     f"(extend tools/idml_to_dsl.py:_emit_colors or add to COLOR_CMYK_TO_BRAND)"
                 )
             # Declared-but-unused non-brand: silently drop

         return resolved
     ```

  5. Store the returned `idml_self -> dsl_name` map on the converter context (e.g. as an attribute of a `_Ctx` dataclass passed through the convert() pipeline, or as a module-level dict captured during convert() — your call). Tasks 6-7 will use it to translate `FillColor="Color/..."` to a DSL fill string.

  6. Update `_check_masters_empty` and `_read_layers` to expose `printable_layer_ids` for color collection.

  7. Add an end-of-Phase-F sanity print: `# (debug) print(f"colors resolved: {len(resolved)} brand-mapped, ... unmapped used")` then remove before commit. Confirm against expected target-IDML mapping:
     - `Color/Black` → `"Black"`
     - `Color/Paper` → `"White"`
     - `Color/C=85 M=35 Y=95 K=10` → `"Dunkelgrün"`
     - `Color/C=0 M=0 Y=100 K=0` → `"Gelb"`
     - `Color/C=0 M=100 Y=0 K=0` → `"Magenta"`
     - Spots `Druckformat / Faltung / Sicherheit / Endformat` should be UNUSED in the printable layer (Info layer is non-printable) and therefore silently dropped.

  8. Unit test: `tests/unit/test_idml_colors.py` with cases for the mapping table behaviour (use synthetic XML strings; do not require the real IDML for these tests):
     ```python
     def test_brand_rename_dunkelgruen()
     def test_paper_to_white()
     def test_registration_skipped()
     def test_non_brand_printable_raises()
     def test_non_brand_unused_silently_dropped()
     ```
  </action>
  <files>
  tools/idml_to_dsl.py (add _read_colors, _collect_used_fillcolors, _emit_colors)
  tests/unit/test_idml_colors.py (new)
  </files>
  <verify>
  <automated>
  python3 -m pytest tests/unit/test_idml_colors.py -x -v
  # End-to-end against the real IDML — should succeed (all corpus colors map)
  python3 tools/idml_to_dsl.py "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" /tmp/test_build.py --template-id test 2>&1 | tee /tmp/conv.log
  # No UnhandledElement on real IDML at this phase
  ! grep -q "UnhandledElement" /tmp/conv.log
  </automated>
  </verify>
  <done>All target-IDML colors resolve to brand names (Black/White/Dunkelgrün/Gelb/Magenta) or are silently dropped (process inks, Registration, Info-layer spots); unit tests cover the 5 cases; non-brand printable swatches raise UnhandledElement.</done>
</task>

<task id="5" title="Style phase: ParagraphStyle resolution + BasedOn chain + font cascade">
  <action>
  Add Phase G (styles) to `tools/idml_to_dsl.py`. CharacterStyles in the target are trivial (only `[No character style]`), but ParagraphStyles need real BasedOn-chain resolution and AppliedFont cascade.

  1. `_read_paragraph_styles(pkg: IDMLPackage) -> dict[str, dict]`:
     Walk `Resources/Styles.xml`; iterate `pkg.style_groups`; find `RootParagraphStyleGroup`; for each `<ParagraphStyle>` collect:
     ```python
     {
       self_id:        "ParagraphStyle/NormalParagraphStyle",  # Self attr
       name:           "NormalParagraphStyle",                  # Name attr (last segment of Self)
       based_on_self:  "ParagraphStyle/$ID/[No paragraph style]" | None,
       point_size:     float | None,
       leading:        float | None,        # from <Properties><Leading>...</Leading>
       justification:  "LeftAlign"|"CenterAlign"|"RightAlign"|"FullyJustified" | None,
       applied_font:   "Gotham Narrow" | None,        # from <Properties><AppliedFont type="string">...</AppliedFont>
       font_style:     "Book" | "Bold" | "Black" | "Ultra" | None,   # FontStyle attr
       fill_color:     "Color/Paper" | "Color/..." | None,
     }
     ```
     IDML may have spaces or unusual chars in Name (e.g. `Aufzählungen auf grünem Hintergrund`); preserve verbatim via lxml's `.get("Name")`.

  2. `_resolve_paragraph_style(style: dict, all_styles: dict[str, dict]) -> dict`:
     Walk the BasedOn chain upward; for each unset attribute on `style`, inherit from its parent. Stop at the root (`based_on_self` resolves to `[No paragraph style]` which has its own InDesign defaults — for the converter, treat as "no further info" and don't synthesise defaults).

     IMPORTANT: AppliedFont cascade per P-STYLE-1 — `CharacterStyleRange` in stories may set only `FontStyle="Black"` with NO inline `<AppliedFont>`; resolution must come from the applied ParagraphStyle's cascaded font.

  3. Map IDML Justification → Scribus `align` int (per `ParaStyle.align` semantics: 0=left, 1=center, 2=right, 3=block):
     ```python
     JUSTIFICATION_MAP = {"LeftAlign": 0, "CenterAlign": 1, "RightAlign": 2,
                          "FullyJustified": 3, "LeftJustified": 3,
                          "RightJustified": 3, "CenterJustified": 3}
     ```
     Raise on any value not in this map.

  4. `_make_font_name(family: str | None, style: str | None, *, ctx_self_id: str) -> str | None`:
     If both family and style: return `f"{family} {style}"` (e.g. "Gotham Narrow Bold"). If only one: return it. If neither: return None (let Scribus inherit from doc default).
     Validate against brand fonts (informational warning only — Scribus's fontconfig will fall back if needed):
     ```python
     BRAND_FONTS = {"Gotham Narrow Book", "Gotham Narrow Bold",
                    "Gotham Narrow Black", "Gotham Narrow Ultra",
                    "Vollkorn Black Italic"}
     ```
     Don't raise — `[No paragraph style]` defaults to "Times" which we want to preserve as-is.

  5. Slug-style IDML names for DSL: keep them sanitisable but recognisable. Pattern from RESEARCH §"Paragraph styles":
     - `NormalParagraphStyle` → `idml/NormalParagraphStyle`
     - `Absatzformat 1` → `idml/absatzformat-1`
     - `Aufzählungen auf grünem Hintergrund` → `idml/aufzaehlungen-auf-gruenem-hintergrund`
     - `Fließtext auf grünem Hintergrund` → `idml/fliesstext-auf-gruenem-hintergrund`
     - `Headline in grünem Kasten` → `idml/headline-in-gruenem-kasten`

     Add `_idml_style_slug(name: str) -> str`: lowercase, ASCII-fold (`ü→ue`, `ß→ss`, `ä→ae`, `ö→oe`), replace spaces with `-`, strip non-alphanum-or-hyphen, prefix with `idml/`.

  6. `_emit_paragraph_styles(out: PythonRepr, pkg, color_map: dict[str, str]) -> dict[str, str]`:
     Returns `idml_name -> dsl_slug` map. For each `ParagraphStyle` USED in any story (skip orphans), emit `doc.add_para_style(ParaStyle(name="idml/...", parent="idml/...", font=..., fontsize=..., align=..., fcolor=...))`.

     `fcolor` translation: pass the IDML FillColor through `color_map` from task 4. If the style references a color not in `color_map` (e.g. `Color/Druckformat` on an Info-only style), drop the field — that style is not going to be referenced from a printable frame anyway.

  7. Skip CharacterStyle emission entirely if the only character style is `[No character style]` (the corpus case). If any other `<CharacterStyle>` element is found inside `RootCharacterStyleGroup`, raise `UnhandledElement` (defensive — target has none).

  8. Wire into `convert()` between Phase F (colors) and Phase H (pages/items).

  9. Unit tests in `tests/unit/test_idml_styles.py`:
     - `_idml_style_slug` produces expected slugs (test all 5 corpus styles).
     - Synthetic Styles.xml: BasedOn chain resolves AppliedFont and PointSize correctly.
     - Justification map covers all 4 values; unknown raises.
     - `_make_font_name("Gotham Narrow", "Bold") == "Gotham Narrow Bold"`.
  </action>
  <files>
  tools/idml_to_dsl.py (add Phase G)
  tests/unit/test_idml_styles.py (new)
  </files>
  <verify>
  <automated>
  python3 -m pytest tests/unit/test_idml_styles.py -x -v
  # End-to-end against the real IDML — should still succeed with styles emitted
  python3 tools/idml_to_dsl.py "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" /tmp/test_build.py --template-id test
  # Emitted build.py imports clean
  python3 -c "import sys; sys.path.insert(0, 'tools'); import importlib.util; spec = importlib.util.spec_from_file_location('b', '/tmp/test_build.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); doc = m.build_template(); print('paragraph styles:', len(doc._para_styles) if hasattr(doc, '_para_styles') else 'n/a')"
  # Generated build.py contains expected ParaStyle slugs
  grep -q "idml/normalparagraphstyle\|idml/NormalParagraphStyle\|idml/headline-in-gruenem-kasten\|idml/headline" /tmp/test_build.py
  </automated>
  </verify>
  <done>All 5 corpus paragraph styles emitted as ParaStyle(name="idml/...", parent="...", ...) with font/fontsize/align/fcolor resolved through the BasedOn chain; tests cover slug+cascade+font-name; emitted build.py still imports cleanly.</done>
</task>

<task id="6" title="Page-object phase: Rectangle / Polygon / Oval / Image / Group cascade (no text yet)">
  <action>
  Add Phase H1 (geometric page items, no text content) to `tools/idml_to_dsl.py`. Text frames are stubbed out as empty `TextFrame(...)` for now — task 7 wires in the Story runs.

  1. `_iter_page_items(page_node, pkg, spread_root) -> Iterator[tuple[lxml.etree._Element, list[str]]]`:
     Walk a `<Page>`'s sibling page-items in the spread XML (per RESEARCH "Spread/Page transforms"); for each top-level item:
     - If `<Group>`: recurse, prepending the Group's `ItemTransform` to the ancestor chain.
     - Otherwise: yield `(item_node, ancestor_transforms_list_outermost_first)`.

     Determine which page-items belong to which page using SimpleIDML's heuristic: `page.page_items` already does this (`page_item_is_in_self` — first PathPoint's X falls within the page's X range). Iterate `page.page_items` rather than children of `<Page>`.

  2. Layer filter: skip items whose `ItemLayer` is on a non-printable layer ID (decision: layer is mapped 1:1 to `DocumentLayer(printable=False)`, so the Info layer's items should be DROPPED entirely in v1. This matches sibling-template behaviour: the `Falz` layer is printable but Info is not. The locked decision skips Falz lines anyway).

     Implementation choice: drop them. Document in code comment: "Info-layer items skipped per locked decision #5 (Falz lines added manually post-bootstrap; non-printable-layer items are designer-only print marks not part of the deliverable)."

  3. Item-type dispatch:
     ```python
     def _emit_pageitem(out, item, ancestors, spread_root, page, ctx) -> None:
         tag = etree.QName(item).localname
         self_id = item.get("Self", "<unknown>")
         if tag == "Rectangle":
             _emit_rectangle(out, item, ancestors, spread_root, page, ctx)
         elif tag == "Polygon":
             _emit_polygon(out, item, ancestors, spread_root, page, ctx)
         elif tag == "Oval":
             _emit_oval(out, item, ancestors, spread_root, page, ctx)
         elif tag == "TextFrame":
             _emit_textframe(out, item, ancestors, spread_root, page, ctx)  # task 7 fills runs
         elif tag == "GraphicLine":
             raise UnhandledElement(f"GraphicLine Self={self_id!r}: not in v1 corpus (extend tools/idml_to_dsl.py:_emit_pageitem)")
         else:
             raise UnhandledElement(f"PageItem <{tag}> Self={self_id!r}: not handled (extend tools/idml_to_dsl.py:_emit_pageitem)")
     ```

  4. `_extract_anchors(item) -> list[tuple[float,float]]`:
     ```python
     def _extract_anchors(item):
         pts = []
         for pp in item.findall(".//PathPointType"):
             ax, ay = pp.get("Anchor").split()
             pts.append((float(ax), float(ay)))
         if not pts:
             raise UnhandledElement(f"<{etree.QName(item).localname} Self={item.get('Self')!r}>: no PathPointType anchors")
         return pts
     ```

  5. `_resolve_fill(item_or_csr, color_map) -> Optional[str]`:
     - Read `FillColor` attr. If absent: return None.
     - If "Color/None" or "Swatch/None": return None.
     - Look up `color_map[fill_color_self]` → DSL color name. If not present: raise `UnhandledElement` (only colors resolved in task 4 are valid).

  6. `_emit_rectangle / _emit_polygon / _emit_oval`:
     - Detect nested `<PDF>` child → defer collection (decision #2: collect Self+LinkResourceURI basename into `ctx.unmapped_logos`, do NOT emit ImageFrame, return early).
     - Detect nested `<Image>` child → emit as `ImageFrame` (handled separately in `_emit_image_content`).
     - Detect nested `<EPS>` child → raise `UnhandledElement` (none in corpus).
     - Otherwise: emit `Polygon(x_mm=..., y_mm=..., w_mm=..., h_mm=..., fill=..., layer=..., anname="<Self>")`. Use `shape="ellipse"` for `<Oval>`. Use `rotation_deg=` from geometry helper.
     - For `corner_radius_mm`: detect via the Rectangle's `<Properties><CornerRadius>` or the path-point's Left/RightDirection asymmetry. Skip for v1 (raise on detection of non-zero corner radius? — confirm none in corpus first; if present, raise).

  7. `_emit_image_content(out, item, image_node, ancestors, spread_root, page, ctx)`:
     - From `<Link LinkResourceURI="file:/...">` get the absolute URI; parse with `urllib.parse.urlparse + urllib.parse.unquote`; take basename.
     - Resolve against `ctx.assets_dir / basename`. If missing: append to `ctx.missing_assets` and return (raise at end-of-conversion per decision #3).
     - If raster (.jpg/.jpeg/.png/.psd): use `pack_inline_image` for jpg/png (small files); for .psd, point `ImageFrame(image="<repo-relative path>")` and let Scribus place it (Scribus 1.6 reads PSD via libpsd). Sibling templates use `pack_inline_image` for jpgs in their build.py. For target IDML's 2 raster assets (`green-pine-trees-covered-with-fog.jpg` and `Plakat dunkel für Flyer.psd`), use:
       - JPG → `pack_inline_image(open(asset).read(), "jpg")` + `ImageFrame(inline_image_data=..., inline_image_ext="jpg", ...)`.
       - PSD → `ImageFrame(image="originals/.../Links/Plakat dunkel für Flyer.psd", ...)` (Scribus places PSD natively; convert to PNG later if needed).
     - Local transform: `<Image>` carries its own `ItemTransform` for local scale/offset within the frame. For v1, derive `local_scale` from `(sqrt(a²+b²), sqrt(c²+d²))` and `local_offset_mm` from `(tx*PT_TO_MM, ty*PT_TO_MM)`. Set `local_rotation_deg = atan2(b,a) deg`.

  8. `_emit_textframe` (TASK 6 STUB): emit `TextFrame(x_mm=..., y_mm=..., w_mm=..., h_mm=..., text="", style="idml/...", anname="<Self>", layer=...)` with empty `text=""` (task 7 wires `runs=`).

  9. End-of-conversion gates (decisions #2 and #3):
     ```python
     def _final_strictness_gates(ctx) -> None:
         msgs = []
         if ctx.unmapped_logos:
             logo_list = "\n  ".join(f"- {sid}: {uri}" for sid, uri in ctx.unmapped_logos)
             msgs.append(f"Unmapped vector logos ({len(ctx.unmapped_logos)}):\n  {logo_list}\n"
                         f"Stage pre-rasterised PNGs under shared/logos/ (or similar) and "
                         f"extend tools/idml_to_dsl.py:_emit_rectangle to point at them.")
         if ctx.missing_assets:
             m_list = "\n  ".join(f"- {p}" for p in ctx.missing_assets)
             msgs.append(f"Missing raster assets ({len(ctx.missing_assets)}):\n  {m_list}\n"
                         f"Place files under --assets-dir or extend the resolver.")
         if msgs:
             raise UnhandledElement("\n\n".join(msgs))
     ```
     Call this AFTER all page items have been emitted but BEFORE writing the build.py to disk.

  10. Wire into `convert()` as Phase H. Iterate `pkg.pages` (which already maps page items to pages via SimpleIDML's heuristic). For each Page, emit `pageN.add(<primitive>)` lines.

  11. Strict on threaded frames and anchored objects (decisions #1 from out-of-scope):
      ```python
      next_tf = item.get("NextTextFrame", "n")
      prev_tf = item.get("PreviousTextFrame", "n")
      if next_tf != "n" or prev_tf != "n":
          raise UnhandledElement(
              f"TextFrame Self={self_id!r}: threaded (Next/Previous != 'n'); "
              f"not supported in v1 (extend tools/idml_to_dsl.py:_emit_textframe)"
          )
      ```
  </action>
  <files>
  tools/idml_to_dsl.py (add Phase H1)
  </files>
  <verify>
  <automated>
  # Run converter end-to-end — expect either clean success OR a deliberate UnhandledElement
  # listing the unmapped logos (decision #2). EITHER outcome is acceptable at this task —
  # the unmapped-logo raise IS the success signal for the executor: it means the converter
  # is now structurally complete and just needs human-staged logo PNGs.
  python3 tools/idml_to_dsl.py "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" /tmp/test_build.py --template-id test 2>&1 | tee /tmp/conv.log
  # Either clean exit OR an UnhandledElement that lists exactly the corpus's 5 .ai logos by basename
  grep -qE "(OK:|Unmapped vector logos|BlueSky|Grüne Logo Bund|Mail weiss|Social Media Icons|Website weiss)" /tmp/conv.log
  </automated>
  </verify>
  <done>Converter emits Polygon/ImageFrame primitives with correct (x_mm,y_mm,w_mm,h_mm,rotation_deg) for every printable Rectangle/Polygon/Oval/Image; nested Groups cascade; threaded TextFrames raise; unmapped .ai logos and missing raster assets surface in a single end-of-run UnhandledElement listing.</done>
</task>

<task id="7" title="TextFrame text phase: Story runs + ParagraphStyleRange + CharacterStyleRange + Br/">
  <action>
  Add Phase H2 (story text wiring) to `tools/idml_to_dsl.py`. Fill the empty `text=""` stubs from task 6 with `runs=[Run(...), ...]`.

  1. `_resolve_story_xml(pkg, parent_story_id: str) -> lxml.etree._Element`:
     ```python
     def _resolve_story_xml(pkg, parent_story_id):
         # parent_story_id is e.g. "u189"; the Story XML lives at Stories/Story_u189.xml
         path = f"Stories/Story_{parent_story_id}.xml"
         if path not in pkg.namelist():
             raise UnhandledElement(f"Story XML not found for ParentStory={parent_story_id!r}: {path}")
         return etree.fromstring(pkg.read(path), parser=_SECURE_XMLPARSER)
     ```

  2. `_walk_story(story_root, paragraph_style_map: dict[str,str], color_map: dict[str,str]) -> list[Run]`:
     Walk `<Story>/<ParagraphStyleRange>/<CharacterStyleRange>/<Content>` plus `<Br/>` between runs.

     For each `<ParagraphStyleRange>`:
       - Read `AppliedParagraphStyle="ParagraphStyle/<name>"`. Look up `paragraph_style_map[name]` → DSL slug (e.g. `idml/headline-in-gruenem-kasten`).
       - For each child `<CharacterStyleRange>`:
         - Read `<AppliedFont>` (child text content) and `FontStyle` (attr).
         - Read `PointSize`, `FillColor`, `Leading` attrs (optional).
         - Walk children IN ORDER:
           - `<Content>...text...</Content>` → emit a `Run(text=<text>, paragraph_style=<slug-on-first-of-paragraph-only-or-last>, font=..., fontsize=..., fcolor=..., separator=None)`.
           - `<Br/>` → emit `Run(text="", separator="breakline")`.
           - `<HyperlinkTextSource>` (if any) → raise `UnhandledElement` (none in corpus).
           - `<?ACE 7?>` processing instruction → emit literal `\t` in the next Content's text (the `<?ACE 7?>` indent-to-here marker). For v1, just preserve a Tab character. If any other `<?ACE N?>` is encountered with N != 7, raise.
       - At the END of a `ParagraphStyleRange` (after all CharacterStyleRange children processed), emit `Run(separator="para", paragraph_style=<slug>)` UNLESS it's the last paragraph in the story (the last paragraph in a Scribus TextFrame doesn't need a trailing `<para/>`).

     The `paragraph_style=` field on Run carries the trailing `<para>` PARENT in Scribus; sla_to_dsl emits this on the "para" separator Run (per `sla_to_dsl.py` `_build_runs` shape). Mirror that pattern.

  3. Font cascade per P-STYLE-1 (CharacterStyleRange may set FontStyle without AppliedFont):
     - If `<AppliedFont>` is present in the CharacterStyleRange: use it.
     - Else: look up the applied ParagraphStyle, walk its BasedOn chain (task 5's resolution table), pick the first non-None AppliedFont.
     - Combine with `FontStyle` (CharacterStyleRange's `FontStyle` overrides ParaStyle's `FontStyle` if both present).
     - Emit `font=f"{family} {style}"` as a fully-qualified Scribus font name.
     - If both family AND style resolve to the values declared in the ParaStyle itself, OMIT `font=` from the Run (the Run inherits via ParaStyle PARENT — leaner emit). Optional optimisation; OK to emit redundantly in v1.

  4. Color mapping: `fcolor` on Run translates the IDML CharacterStyleRange's `FillColor` through `color_map` from task 4. If `FillColor` is absent on the CSR, inherit from the ParaStyle (don't emit `fcolor=` on the Run — let Scribus inherit through PARENT).

  5. Wire `_walk_story` into `_emit_textframe` from task 6:
     ```python
     def _emit_textframe(out, item, ancestors, spread_root, page, ctx):
         self_id = item.get("Self")
         # ... geometry (from task 6 stub) ...
         next_tf = item.get("NextTextFrame", "n")
         prev_tf = item.get("PreviousTextFrame", "n")
         if next_tf != "n" or prev_tf != "n":
             raise UnhandledElement(f"TextFrame Self={self_id!r}: threaded; not in v1")
         parent_story = item.get("ParentStory")
         if not parent_story:
             # Empty TextFrame (rare); emit with text=""
             runs = None
         else:
             story_root = _resolve_story_xml(ctx.pkg, parent_story)
             runs = _walk_story(story_root, ctx.paragraph_style_map, ctx.color_map)
         # Determine the DefaultStyle for the frame (per-frame; usually the FIRST
         # ParagraphStyleRange's applied style — Scribus uses it for the trailing
         # paragraph's PARENT).
         style_slug = ...  # first PSR's applied style slug, or ""
         # Emit
         _emit_call(out, "TextFrame", {
             "x_mm": x_mm, "y_mm": y_mm, "w_mm": w_mm, "h_mm": h_mm,
             "rotation_deg": rot,  # only if non-zero
             "anname": self_id, "layer": layer_idx,
             "style": style_slug,
             "runs": runs,
         })
     ```

  6. Bullet glyph preservation (P-STORY-1): the corpus has `<Content>\t•\t<?ACE 7?></Content>` for bullet items. Preserve the literal `\t•\t` (TAB + bullet glyph + TAB) verbatim as a Run's text. The `<?ACE 7?>` indent marker becomes a Tab character. If this looks wrong in the rendered PDF, follow up; for v1 strict-mode preservation is the goal.

  7. Strict on unknown processing instructions / elements inside a Story:
     - Any `<?ACE N?>` where N != 7: raise.
     - Any element inside CharacterStyleRange that isn't `Content`, `Br`, or a `<?ACE 7?>` processing instruction: raise (`<Footnote>`, `<HyperlinkTextSource>`, `<Note>`, `<Table>`, etc.).
     - Any element inside `<Story>` that isn't `ParagraphStyleRange` or known structural metadata: raise.

  8. Unit test in `tests/unit/test_idml_story.py` against synthetic Story XML strings:
     - Single `<ParagraphStyleRange>` with one `<CharacterStyleRange>` and one `<Content>` → produces one `Run(text=...)`.
     - `<Br/>` between two `<Content>` → produces `[Run(text="A"), Run(separator="breakline"), Run(text="B")]`.
     - Multi-paragraph story → `[Run("para1"), Run(separator="para"), Run("para2")]`.
     - Font cascade: CSR with `FontStyle="Bold"` and no `<AppliedFont>` falls back to ParaStyle's family.
     - Unknown processing instruction raises.
  </action>
  <files>
  tools/idml_to_dsl.py (add Phase H2)
  tests/unit/test_idml_story.py (new)
  </files>
  <verify>
  <automated>
  python3 -m pytest tests/unit/test_idml_story.py -x -v
  # The converter now needs the user to either:
  # (a) stage the .ai logos as PNGs (decision #2), or
  # (b) get the deliberate UnhandledElement listing
  # For verification purposes, assert the run either succeeds OR raises the LOGO list
  # AND that the partial /tmp/test_build.py — if written — contains Run(...) constructs
  python3 tools/idml_to_dsl.py "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" /tmp/test_build.py --template-id test 2>&1 | tee /tmp/conv.log
  # Either OK or unmapped-logo raise (decision #2 expected behaviour at this point)
  grep -qE "(OK:|Unmapped vector logos)" /tmp/conv.log
  </automated>
  </verify>
  <done>Stories walk produces Run lists with correct separator="para"/"breakline" markers, font cascade resolves through BasedOn chain, &lt;Br/&gt; maps to breakline, bullet glyphs preserved verbatim, unknown story elements raise. Unit tests cover all cases.</done>
</task>

<task id="8" title="Emit phase: assemble final build.py + write meta.yml + stage logo PNGs">
  <action>
  Finish the emit pipeline and create the new template directory.

  1. Assemble the final emitted `build.py` per the sibling template's scaffold:
     ```python
     # Imports + HERE + sys.path
     # INJECT_MAP = {}
     # _add_styles(doc): every ParaStyle from task 5
     # _add_front(doc, page0): every printable primitive on page 1 (Spread_ueb)
     # _add_back(doc, page1):  every printable primitive on page 2 (Spread_u108)
     # build_template() -> Document: Brand.gruene_noe() + add_master + add_page + _add_styles + _add_front + _add_back
     # build_preview() -> Document: build_template() + INJECT_MAP-driven library.inject_into_frame
     # build_doc = build_template  (alias for audit_alignment.py)
     # build(out_path) -> Path: build_preview().save(out_path)
     # main: HERE / "template.sla"
     ```
     Mirror the structure of `templates/kandidat-falzflyer-din-lang/build.py:1-67, 872-946`. Do NOT try to organise into per-panel `_add_p1 / _add_p2` helpers — flat per-page emit is fine (the human re-organises after).

  2. Create the new template directory at `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/`:
     - `build.py` (emitted)
     - `meta.yml` (task 9 — for now create a STUB matching the YAML shape: id, version, title, format, pages, build, ci_overrides, slots — empty if unsure)
     - `assets/` directory (empty for now; PSD/JPG resolved from `--assets-dir` flag, not staged here in v1)
     - `samples/` (created by `bin/render-gallery`)

     CLI flag: `--output` is the path to the emitted `build.py` (mirrors sla_to_dsl.py). The converter creates the parent directory if missing.

  3. Logo staging (locked decision #2 is "hard-raise, human stages, re-runs"): the converter does NOT stage logos. But the executor must, between tasks 8 and 10, run the converter once to surface the missing-logo list, then manually:

     a. Identify the 5 .ai logos:
        - `BlueSky weiss.ai`
        - `Grüne Logo Bund weiss CMYK.ai`
        - `Mail weiss.ai`
        - `Social Media Icons weiss.ai`
        - `Website weiss.ai`

     b. For each, find an existing PNG counterpart in `shared/logos/` (if any) OR rasterise from the .ai using `pdftoppm -png -r 600 "originals/.../Links/BlueSky weiss.ai" /tmp/bluesky-weiss`. The .ai files are PDF-wrapped — `pdftoppm` works directly.

     c. Save final PNGs at `shared/logos/<sanitised-name>.png` (e.g. `bluesky-weiss.png`, `gruene-logo-bund-weiss-cmyk.png`, `mail-weiss.png`, `social-media-icons-weiss.png`, `website-weiss.png`).

     d. Add a `--logo-map` CLI flag (Path to a small YAML mapping `LinkResourceURI basename → shared/logos/foo.png`). Empty default. When supplied, the converter consults this map BEFORE raising the unmapped-logo list. Schema:
        ```yaml
        # path/to/logo_map.yml — used only at bootstrap
        "BlueSky weiss.ai":              shared/logos/bluesky-weiss.png
        "Grüne Logo Bund weiss CMYK.ai": shared/logos/gruene-logo-bund-weiss-cmyk.png
        "Mail weiss.ai":                 shared/logos/mail-weiss.png
        "Social Media Icons weiss.ai":   shared/logos/social-media-icons-weiss.png
        "Website weiss.ai":              shared/logos/website-weiss.png
        ```

     e. Update `_emit_rectangle` to consult `ctx.logo_map` for any nested `<PDF>`. If present: emit `ImageFrame(image=<png-path>, ...)`. Else: append to `ctx.unmapped_logos` (existing behaviour).

  4. Asset directory verification: at the start of conversion, log (to stderr) the resolved `--assets-dir` and verify it exists. If not, raise `UnhandledElement(f"--assets-dir {dir} does not exist")`.

  5. Re-run the converter end-to-end with the staged logos + assets:
     ```
     python3 tools/idml_to_dsl.py \
         "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" \
         templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py \
         --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2 \
         --assets-dir "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links" \
         --logo-map shared/logos/26-03-leporello-logo-map.yml
     ```
     Expected: zero `UnhandledElement`, emits `build.py`, prints `"OK: templates/.../build.py"`.

  6. Smoke: `python3 templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` produces `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla`.

  Note: this task assumes raster assets (1 JPG + 1 PSD) are already present in `--assets-dir`. They are — verified at `originals/.../Links/`.
  </action>
  <files>
  tools/idml_to_dsl.py (add --logo-map flag + final emit phase)
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py (NEW — generated)
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml (STUB — task 9 fills it)
  shared/logos/bluesky-weiss.png (new — rasterised from .ai)
  shared/logos/gruene-logo-bund-weiss-cmyk.png (new — rasterised)
  shared/logos/mail-weiss.png (new — rasterised)
  shared/logos/social-media-icons-weiss.png (new — rasterised)
  shared/logos/website-weiss.png (new — rasterised)
  shared/logos/26-03-leporello-logo-map.yml (new — YAML map for converter)
  </files>
  <verify>
  <automated>
  # Converter runs clean (zero UnhandledElement) with logos staged
  python3 tools/idml_to_dsl.py \
    "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" \
    templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py \
    --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2 \
    --assets-dir "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links" \
    --logo-map shared/logos/26-03-leporello-logo-map.yml
  # Emitted build.py imports cleanly
  python3 -c "import sys, importlib.util; sys.path.insert(0, 'tools'); spec = importlib.util.spec_from_file_location('b', 'templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); doc = m.build_template(); print('OK pages:', len(doc.pages))"
  # build() produces template.sla
  python3 templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py && test -f templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla
  # All 5 logo PNGs exist
  for f in bluesky-weiss gruene-logo-bund-weiss-cmyk mail-weiss social-media-icons-weiss website-weiss; do test -f "shared/logos/$f.png" || { echo "MISSING: $f.png"; exit 1; }; done
  </automated>
  </verify>
  <done>Converter runs end-to-end clean; templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py exists and produces a valid template.sla; 5 logo PNGs + logo_map.yml staged.</done>
</task>

<task id="9" title="meta.yml authoring (clone-adjusted from sibling falzflyer)">
  <action>
  Author `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml` matching the schema seen in `templates/kandidat-falzflyer-din-lang/meta.yml`.

  1. Clone the header from sibling falzflyer's meta.yml and adjust:
     ```yaml
     id: kandidat-falzflyer-din-lang-gruenes-cover-v2
     version: 0.1.0
     title: Kandidat-Falzflyer DIN-lang (Grünes Cover v2)
     format: A4
     orientation: landscape
     pages: 2
     preview_dpi: 100
     audience: [kandidat, bezirksgruppe, ortsgruppe]
     description: >
       3-fach Zickzackfalz A4-quer-Themenflyer mit grünem Cover. Imported from
       InDesign IDML via tools/idml_to_dsl.py — initial slot schema; refine
       after first gallery render.
     build:
       script: build.py
       output: template.sla
     previews_for_sla: ""   # filled by bin/check-stale-previews / render-gallery
     brand_overrides: []     # (start empty; add as issues surface during validate)
     ci_overrides:
       non_ci_styles: []     # filled below — every emitted ParaStyle slug
       non_ci_colors: []
       non_ci_layers:
         - "Info"             # IDML's non-printable layer
     ```

  2. Populate `ci_overrides.non_ci_styles` with every `idml/<slug>` ParaStyle name emitted by task 5:
     - `idml/normalparagraphstyle`
     - `idml/absatzformat-1`
     - `idml/aufzaehlungen-auf-gruenem-hintergrund`
     - `idml/fliesstext-auf-gruenem-hintergrund`
     - `idml/headline-in-gruenem-kasten`
     (Read the actual emitted names from the generated `build.py` rather than hardcoding — slugs depend on `_idml_style_slug`.)

  3. Populate `ci_overrides.non_ci_colors` with anything that's NOT in the Brand palette. With the locked decisions, this should be EMPTY (all printable colors are brand-mapped). Leave empty.

  4. Generate a STARTER `slots:` block by scanning the emitted `build.py` for every `anname=` value. For each, emit:
     ```yaml
     slots:
       <slug-from-anname>:
         type: shape | text | image    # infer: Polygon → shape, TextFrame → text, ImageFrame → image
         description: ""               # placeholder; human fills after gallery review
         anname: "<exact-anname-from-build.py>"
     ```
     The annames will be the IDML `Self` strings (e.g. `u347`, `u186`, etc.) since the converter uses them. Provide a small script (`tools/_idml_meta_slot_extractor.py` or just inline in this task) that:
     ```python
     # scans templates/<id>/build.py for `anname="<...>"` + the surrounding class name
     # emits slots: block to stdout for paste into meta.yml
     ```
     OR (preferred) extend `tools/idml_to_dsl.py` with a `--emit-meta-stub` flag that writes the `slots:` block alongside `build.py`. Simpler: write a one-shot helper `tools/idml_meta_stub.py` that takes the emitted `build.py` path and prints the slots block:
     ```python
     import importlib.util, sys, yaml
     from pathlib import Path
     sys.path.insert(0, "tools")
     bp = Path(sys.argv[1])
     spec = importlib.util.spec_from_file_location("b", bp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
     doc = m.build_template()
     slots = {}
     for page in doc.pages:
         for it in page.items:
             if not it.anname: continue
             cls = type(it).__name__
             t = {"TextFrame": "text", "ImageFrame": "image", "Polygon": "shape"}.get(cls, "shape")
             slots[it.anname] = {"type": t, "description": "", "anname": it.anname}
     print(yaml.safe_dump({"slots": slots}, allow_unicode=True, sort_keys=False))
     ```
     Run it once; paste the output into `meta.yml`.

  5. Populate `example_pages` and `preflight`:
     ```yaml
     example_pages:
       - { num: 1, label: "Cover" }
       - { num: 2, label: "Innenseite" }
     preflight:
       bleed_mm: 2          # <-- 2 mm per locked decision #4, NOT 3
       fold_mm: [99, 198]   # falz positions (same as sibling)
       cmyk_only: true
       min_image_dpi: 300
     ```

  6. DO NOT try to clone-edit sibling's slot semantics (P1 Top-Band, P1 Logo, etc.). The team's IDML is a different design (themen-flyer, not kandidat-flyer). Use the IDML's own `Self` IDs as anname; let a human refactor anname→semantic-slot-name post-bootstrap.

  7. Validate the new meta.yml parses without errors and matches the meta_schema (tools/sla_lib/builder/meta_schema.py).
  </action>
  <files>
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml (new)
  tools/idml_meta_stub.py (new — one-shot slot extractor)
  </files>
  <verify>
  <automated>
  # meta.yml parses as YAML and contains required keys
  python3 -c "import yaml; d = yaml.safe_load(open('templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml')); assert d['id'] == 'kandidat-falzflyer-din-lang-gruenes-cover-v2'; assert d['preflight']['bleed_mm'] == 2; assert d['pages'] == 2; assert 'slots' in d and len(d['slots']) > 0; print('OK slots:', len(d['slots']))"
  # Validate against meta_schema if available
  python3 -c "import sys; sys.path.insert(0, 'tools'); from sla_lib.builder.meta_schema import validate_meta; import yaml; validate_meta(yaml.safe_load(open('templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml'))); print('OK schema')" 2>&1 | head -5 || true
  # Stub extractor works
  python3 tools/idml_meta_stub.py templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py | head -10
  </automated>
  </verify>
  <done>meta.yml exists with id, format, pages=2, bleed_mm=2 (NOT 3), Info as non-CI layer, every emitted ParaStyle in non_ci_styles, slots block populated with one entry per emitted anname, preflight + example_pages set. idml_meta_stub.py helper exists for future re-runs.</done>
</task>

<task id="10" title="End-to-end: gallery render + audit + checks">
  <action>
  Run the full repo validation pipeline against the new template.

  1. Run `bin/render-gallery` for the new template:
     ```
     bin/render-gallery templates/kandidat-falzflyer-din-lang-gruenes-cover-v2
     ```
     This invokes the build.py → template.sla → preview.pdf chain via xvfb-run + Scribus. Expected outputs:
     - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla`
     - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf`
     - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-01.png` (rendered preview)
     - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-02.png`
     - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-01-hires.png`
     - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-02-hires.png`
     - `meta.yml.previews_for_sla` updated to the new SHA

     If `bin/render-gallery` blocks on missing meta-keys (e.g. `previews_for_sla`), populate them or skip-render the per-template subset via its `--only` flag.

  2. Run `tools/audit_alignment.py` against the new template:
     ```
     python3 tools/audit_alignment.py kandidat-falzflyer-din-lang-gruenes-cover-v2
     ```
     Expected: 0 findings or only `info`-level (drift < 1mm). If any `error`-level findings, document them in the template's README.md and add `brand_overrides:` entries with `reason:` field per sibling-template pattern.

  3. Run `bin/check-fontsizes`:
     ```
     bin/check-fontsizes
     ```
     Expected: zero fractional FONTSIZE values. If any frame has a fractional size, audit — IDML PointSize CAN be fractional. Round to integer in `_walk_story` if the difference is < 0.5; raise `UnhandledElement` if >= 0.5.

  4. Run `bin/check-stale-previews`:
     ```
     bin/check-stale-previews
     ```
     Expected: SHA of `templates/.../template.sla` matches `meta.yml.previews_for_sla`. If not, re-run `bin/render-gallery` to update.

  5. Iterate on any `UnhandledElement` that surfaces. Common ones to expect:
     - `Color/Faltung` printable on a Falz-line frame → if any leak to Gestaltung layer (none should per layer analysis), raise — but Info-layer items are dropped per task 6. Verify.
     - Fractional PointSize → round/raise per above.
     - Corner radius on Rectangle → corpus has none, but if present extend `_emit_rectangle`.

  6. Verify the AC checklist from ISSUE.md is satisfied:
     - [x] `tools/idml_to_dsl.py` exists; runs strict against the bundled IDML
     - [x] Emits a valid `build.py` for `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/`
     - [x] The emitted `build.py` runs and produces a `template.sla` that renders to a `preview.pdf`
     - [x] `meta.yml` is in place with slot schema
     - [x] CI passes (audit_alignment, check-fontsizes, check-stale-previews)
     - [x] Unknown IDML elements raise `UnhandledElement` with a clear hint
     - [x] README in `tools/idml_to_dsl.py` docstring documents one-shot usage
  </action>
  <files>
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla (generated)
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf (generated)
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-{01,02}{,-hires}.png (generated)
  templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml (updated previews_for_sla)
  </files>
  <verify>
  <automated>
  bin/render-gallery templates/kandidat-falzflyer-din-lang-gruenes-cover-v2 || bin/render-gallery
  test -f templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla
  test -f templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf
  python3 tools/audit_alignment.py kandidat-falzflyer-din-lang-gruenes-cover-v2
  bin/check-fontsizes
  bin/check-stale-previews
  </automated>
  </verify>
  <done>bin/render-gallery produces template.sla + preview.pdf + 4 PNG previews; audit_alignment passes with no error-level findings (or documented brand_overrides); check-fontsizes and check-stale-previews pass.</done>
</task>

<task id="11" title="Integration smoke test in tests/">
  <action>
  Add `tests/integration/test_idml_to_dsl_smoke.py` to lock in the converter's behaviour for CI.

  ```python
  """Integration smoke for the IDML→DSL converter (issue 35).

  Runs the converter against the bundled target IDML and verifies:
  - Zero UnhandledElement
  - Emitted build.py imports clean
  - Emitted build.py contains expected primitives (>= N TextFrames, etc.)
  - meta.yml parses + has bleed_mm=2 + 2 pages
  """
  from __future__ import annotations
  import importlib.util
  import subprocess
  import sys
  import tempfile
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[2]
  IDML = ROOT / "originals" / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner" / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml"
  ASSETS = ROOT / "originals" / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner" / "Links"
  LOGO_MAP = ROOT / "shared" / "logos" / "26-03-leporello-logo-map.yml"

  def test_converter_runs_clean(tmp_path):
      out = tmp_path / "build.py"
      r = subprocess.run([
          sys.executable, str(ROOT / "tools" / "idml_to_dsl.py"),
          str(IDML), str(out),
          "--template-id", "kandidat-falzflyer-din-lang-gruenes-cover-v2",
          "--assets-dir", str(ASSETS),
          "--logo-map", str(LOGO_MAP),
      ], capture_output=True, text=True)
      assert r.returncode == 0, f"stderr:\n{r.stderr}\nstdout:\n{r.stdout}"
      assert out.exists()
      assert "UnhandledElement" not in r.stderr

  def test_emitted_build_imports(tmp_path):
      out = tmp_path / "build.py"
      subprocess.check_call([
          sys.executable, str(ROOT / "tools" / "idml_to_dsl.py"),
          str(IDML), str(out),
          "--template-id", "kandidat-falzflyer-din-lang-gruenes-cover-v2",
          "--assets-dir", str(ASSETS), "--logo-map", str(LOGO_MAP),
      ])
      sys.path.insert(0, str(ROOT / "tools"))
      spec = importlib.util.spec_from_file_location("b", out)
      m = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(m)
      doc = m.build_template()
      assert len(doc.pages) == 2
      # Sanity counts (loose bounds; corpus has 8 TextFrames page1, 15 page2 etc.)
      total_items = sum(len(p.items) for p in doc.pages)
      assert total_items >= 30, f"expected >=30 emitted items, got {total_items}"

  def test_meta_yml_parses():
      import yaml
      meta_path = ROOT / "templates" / "kandidat-falzflyer-din-lang-gruenes-cover-v2" / "meta.yml"
      d = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
      assert d["id"] == "kandidat-falzflyer-din-lang-gruenes-cover-v2"
      assert d["pages"] == 2
      assert d["preflight"]["bleed_mm"] == 2     # locked decision #4
  ```

  Also add a unit-test for `.indd` rejection and missing-assets-dir:
  ```python
  # tests/unit/test_idml_strict_mode.py
  def test_indd_binary_rejected(tmp_path):
      bogus = tmp_path / "x.indd"
      bogus.write_bytes(b"\x00\x00\x00\x00 not a zip")
      r = subprocess.run([sys.executable, "tools/idml_to_dsl.py",
                          str(bogus), "/tmp/out.py", "--template-id", "x"],
                          capture_output=True, text=True)
      assert r.returncode == 2
      assert "not a valid IDML" in r.stderr or "ZIP" in r.stderr
  ```
  </action>
  <files>
  tests/integration/test_idml_to_dsl_smoke.py (new)
  tests/unit/test_idml_strict_mode.py (new)
  </files>
  <verify>
  <automated>
  python3 -m pytest tests/unit/test_idml_strict_mode.py tests/integration/test_idml_to_dsl_smoke.py -x -v
  </automated>
  </verify>
  <done>Integration tests pass: converter runs clean against the real IDML, emitted build.py imports + has >=30 items + 2 pages, meta.yml parses with bleed_mm=2. Strict-mode unit test rejects fake .indd.</done>
</task>

<task id="12" title="Documentation polish + commit">
  <action>
  Final cleanup.

  1. Ensure `tools/idml_to_dsl.py` module docstring (top of file) contains:
     - One-shot bootstrap warning
     - Usage example using a real path
     - All 6 locked decisions summarised in one line each
     - "Out of scope" list (threaded frames, anchored objects, etc.)
     - The "noqa: do not import simple_idml.indesign" LGPL note

  2. Ensure each phase function has a single-line docstring describing its role.

  3. Update `tools/sla_to_dsl.py` is UNCHANGED (sanity check — we did not touch it).

  4. Add a one-line entry to the repo's top-level README (if any) under "Tools" pointing at `tools/idml_to_dsl.py`. Skip if no README mentions tools by section.

  5. Run a final cross-check:
     ```
     python3 -m pytest tests/unit/test_idml_*.py tests/integration/test_idml_to_dsl_smoke.py -v
     bin/render-gallery
     python3 tools/audit_alignment.py kandidat-falzflyer-din-lang-gruenes-cover-v2
     bin/check-fontsizes
     bin/check-stale-previews
     ```
     All green.

  6. Commit, per `.issues/config.yaml` (conventional + id prefix):
     ```
     35: feat(idml): strict IDML→DSL converter bootstrap
     ```
     Body: bullet-list of what landed (tools/idml_to_dsl.py + tests + new template dir + Dockerfile pin). One commit covering all changes is fine (this is a single feature delivery).

     DO NOT commit until the user explicitly asks. (Per CLAUDE.md / agent rules: do not be proactive about commits.)
  </action>
  <files>
  tools/idml_to_dsl.py (docstring polish)
  (No new files)
  </files>
  <verify>
  <automated>
  # Final all-green sweep
  python3 -m pytest tests/unit/test_idml_geometry.py tests/unit/test_idml_colors.py tests/unit/test_idml_styles.py tests/unit/test_idml_story.py tests/unit/test_idml_strict_mode.py tests/integration/test_idml_to_dsl_smoke.py -v
  python3 tools/audit_alignment.py kandidat-falzflyer-din-lang-gruenes-cover-v2
  bin/check-fontsizes
  bin/check-stale-previews
  # Smoke: doc-string contains the 6 locked decisions and one-shot warning
  python3 -c "import sys; sys.path.insert(0, 'tools'); import idml_to_dsl; doc = idml_to_dsl.__doc__ or ''; assert 'one-shot' in doc.lower(), 'docstring must mention one-shot'; assert 'UnhandledElement' in doc, 'docstring must mention strict mode'; print('OK docstring')"
  </automated>
  </verify>
  <done>All tests pass; gallery+audit+font-size+stale-preview checks green; docstring complete with one-shot warning + locked decisions summary + LGPL note; no commit yet (user-gated).</done>
</task>

## Order

Tasks 1-12 execute strictly sequentially. Notes:

- **Task 1** must complete before any other task (`UnhandledElement`, `convert()` skeleton, CLI shape, Dockerfile pin).
- **Task 2** (geometry helpers) blocks tasks 6, 7 (they use `_compute_page_local_bbox_pt`).
- **Task 3** (resource walker, layers, Document scaffold) blocks tasks 4, 5, 6, 7 (they need `_Ctx`, `printable_layer_ids`, the emitted Document).
- **Task 4** (colors) blocks task 5 (styles reference colors) and tasks 6, 7 (fill colors).
- **Task 5** (styles) blocks task 7 (story walker references paragraph style slugs).
- **Task 6** (geometric page items + textframe stub + end-of-run gates) MUST complete before task 7 — task 7 fills the empty TextFrame stub with runs.
- **Task 7** (text runs) blocks task 8 (final emit assembles the full build.py).
- **Task 8** (final emit + logo staging) blocks tasks 9, 10 — meta.yml needs the emitted slots, gallery needs the template.sla.
- **Task 9** (meta.yml) is independent of task 10 but conventionally precedes it.
- **Task 10** (gallery + audit) blocks task 11 only in the sense that the integration test depends on a clean end-to-end run.
- **Task 11** (tests) is mostly independent of task 10 — it can run alongside if the executor is parallelising, but the smoke test depends on the converter being feature-complete (task 8 done).
- **Task 12** (docs + green sweep) is the final wrap.

**Parallelisable:** Tasks 4 and 5 are largely independent — colors and styles touch different IDML files (Graphic.xml vs Styles.xml) and different `_emit_*` functions. Tasks 6 and 7 share `_emit_textframe` so must be sequential. Tasks 11 and 10 can interleave if the executor splits attention.

## Verification (overall)

End-to-end smoke (all must pass):

```bash
# 1. Converter runs clean against the target IDML
python3 tools/idml_to_dsl.py \
    "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" \
    templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py \
    --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2 \
    --assets-dir "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links" \
    --logo-map shared/logos/26-03-leporello-logo-map.yml

# 2. Emitted build.py runs and produces a valid .sla
python3 templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py
test -f templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla

# 3. Gallery renders preview.pdf + PNGs
bin/render-gallery
test -f templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf

# 4. Repo-wide checks
python3 tools/audit_alignment.py kandidat-falzflyer-din-lang-gruenes-cover-v2
bin/check-fontsizes
bin/check-stale-previews

# 5. All converter unit + integration tests
python3 -m pytest tests/unit/test_idml_geometry.py \
                  tests/unit/test_idml_colors.py \
                  tests/unit/test_idml_styles.py \
                  tests/unit/test_idml_story.py \
                  tests/unit/test_idml_strict_mode.py \
                  tests/integration/test_idml_to_dsl_smoke.py -v

# 6. Dockerfile pin sanity
grep -q "SimpleIDML==1.3.1" Dockerfile.claude
grep -q "simple_idml.idml" Dockerfile.claude
```

ISSUE.md acceptance criteria coverage (1:1):
- [x] `tools/idml_to_dsl.py` exists; runs strict against the bundled IDML — task 1, 10
- [x] Emits a valid `build.py` for `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` — task 8
- [x] Emitted `build.py` runs and produces a `template.sla` that renders to `preview.pdf` — task 10
- [x] `meta.yml` is in place with slot schema — task 9
- [x] CI passes (audit_alignment, font-sizes, stale-previews) — task 10
- [x] Unknown IDML elements raise `UnhandledElement` with a clear hint — tasks 1, 2, 3, 4, 5, 6, 7 (every raise includes the `(extend tools/idml_to_dsl.py:_function_name)` pointer)
- [x] README in `tools/idml_to_dsl.py` docstring documents one-shot usage — tasks 1, 12
