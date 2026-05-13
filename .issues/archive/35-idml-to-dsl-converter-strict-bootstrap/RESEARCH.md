# RESEARCH — Issue 35: IDML → DSL converter

**Confidence: HIGH.** Three parallel agents (codebase, ecosystem, pitfalls)
converged on the same architecture; coordinate math, library versions, and
DSL primitive surface are all empirically verified. Six concrete open
questions remain for the planner to resolve.

Sub-reports: [research/codebase.md](research/codebase.md) ·
[research/ecosystem.md](research/ecosystem.md) ·
[research/pitfalls.md](research/pitfalls.md)

---

## User Constraints

None in CONTEXT.md (not authored for this issue). Repo-wide constraints
from `CLAUDE.md` and prior-art issue #2 carry over:

- **Typed DSL only** (issue #2 D2). Emitter must call typed primitives —
  no `raw_attrs` bags, no string-template SLA fragments.
- **Strict mode** (issue #2 D6). Unknown elements raise `UnhandledElement`
  with a hint pointing at the converter function to extend. Better to fail
  loud than emit a silently-wrong `build.py`.
- **One-shot bootstrap.** Not a CI tool. Run once per IDML, hand-edit the
  emitted `build.py` from there. Mirrors `tools/sla_to_dsl.py`.

---

## Summary

We are building `tools/idml_to_dsl.py`, a strict-mode one-shot converter
that reads an Adobe IDML and emits a DSL `build.py` against the existing
`sla_lib.builder` primitives. The first target is the Grüne design
team's `26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml`,
which is the same physical format as `templates/kandidat-falzflyer-din-lang`
(297×210 A4-quer, 3-fold Zickzack, 6 panels à 99×210).

**Three primary architectural decisions** the planner must lock in:

1. **Reuse, don't extend, the DSL.** The current `sla_lib.builder` surface
   covers every primitive the target IDML needs — `TextFrame`,
   `ImageFrame`, `Polygon`, `Run`, `ParaStyle`, `CharStyle`, `SoftShadow`,
   `Anchor`, `Brand`, `DocumentLayer`. The IDML corpus introduces *no new
   primitive types*. Mapping gaps are about *coverage* (handling `Oval`,
   `Group`, nested `PDF` blocks, `Br/`), not new types.

2. **Mirror `sla_to_dsl.py`'s 7-phase structure.** Doc meta → imports →
   `Document(...)` → colors → styles → layers/masters/pages → page
   objects. Same `UnhandledElement` shape (one typed exception, closed
   allow-list per attribute). Same emitted-file shape (`build_template`/
   `build_preview`/`build` trio, `INJECT_MAP` idiom for asset injection).

3. **Geometry is the only genuinely new logic.** SLA stores frame
   geometry as `XPOS`/`YPOS`/`WIDTH`/`HEIGHT` directly; IDML stores it as
   `ItemTransform` affine matrix × `PathPointArray` anchors, with a
   *three-stacked* coordinate cascade (spread origin at centre +
   `Spread/ItemTransform` page translation + page `ItemTransform`),
   potentially plus nested `Group` matrices. The math is settled; the
   *implementation* needs care.

**Out of scope** (explicit non-goals, confirmed across all three forks):
DSL→IDML round-trip, `.indd` binary parsing, multi-IDML batch, threaded
TextFrames (zero in corpus — raise loudly if encountered), master-spread
items (master is empty in target), anchored objects, tables, footnotes,
RTL text, baseline.pdf for visual_diff (sibling falzflyer doesn't have
one either), fuzzy-snap CMYK→Brand colour matching.

**Recommended ordering:** ship the converter against this one IDML, treat
every unhandled element as a deliberate `UnhandledElement` raise (not a
no-op), and let the next IDML import drive corpus extension. Don't
pre-build for IDML features we haven't seen.

---

## Codebase Analysis

### Existing converter to mirror — `tools/sla_to_dsl.py`

- 1288 LOC, 4-arg CLI: `<source.sla> <output build.py> --template-id <id> --assets-dir <dir>`
  (`--assets-dir` is currently a no-op — codebase.md§"CLI" line refs)
- 7-phase `convert()`: doc meta → imports → `Document(...)` →
  colors → char/para styles → masters + pages → page objects (chains
  last)
- Strict mode: single typed `UnhandledElement(Exception)` raised everywhere
  (sla_to_dsl.py:59, 1281-1283). Message format: `"<element-kind> '<self-id>' attribute '<attr>' value <value> (extend tools/sla_to_dsl.py:_function_name)"`. Mirror this pattern verbatim.
- Emits: `from sla_lib.builder import (Brand, Document, TextFrame, ImageFrame, Polygon, Run, ParaStyle, CharStyle, SoftShadow,)` + `Brand.gruene_noe()` Document scaffold + `INJECT_MAP` placeholder + `build_template`/`build_preview`/`build` trio.

### DSL primitive surface (the emit phase calls these — all already exist)

<interfaces>
# tools/sla_lib/builder/__init__.py — public surface
from .document import Document, Page
from .primitives import TextFrame, ImageFrame, Polygon, Anchor, Run, pack_inline_image
from .styles import DocumentLayer, ParaStyle, CharStyle, SoftShadow
from .brand import Brand
from .composites import AlignedRow, AlignedColumn, MirroredPair, EqualGapStack, GridSpec, GridCell, HierarchyBlock
from .constraints import (same_y, same_x, same_size, mirrored_x, mirrored_y, inside,
                          equal_gap, hierarchy, same_style, distance_y, distance_x, aligned_below)

class Document:
    def __init__(self, title="", template_id="",
                 author="Die Grünen Niederösterreich",
                 ci_path=None, *, brand=None,
                 layers=None, facing_pages=False,
                 column_gap_default_pt=11.0, unit="mm",
                 deffont="Gotham Narrow Book", defsize=12,
                 first_page_num=1, palette_replaces_ci=False, ...): ...
    def add_color(self, name, *, cmyk=None, rgb=None, spot=False, register=False): ...
    def add_para_style(self, ps: ParaStyle): ...
    def add_char_style(self, cs: CharStyle): ...
    def add_master(self, *, name="Normal", size="A4", orientation="portrait",
                   bleed_mm=3.0, margins_mm=(10,10,10,10), facing="right",
                   page_xpos_pt=None, page_ypos_pt=None,
                   width_pt=None, height_pt=None) -> Page: ...
    def add_page(self, *, size=..., orientation="portrait",
                 bleed_mm=3.0, margins_mm=(10,10,10,10),
                 master="Normal", label="",
                 page_xpos_pt=None, page_ypos_pt=None) -> Page: ...
    def save(self, path): ...

@dataclass
class _Frame:
    x_mm=0; y_mm=0; w_mm=50; h_mm=30
    anchor: Optional[Anchor] = None
    rotation_deg: float = 0          # ← rotated TextFrames flow into this
    layer: int = 2                   # default Text
    anname: str = ""
    custom_path: Optional[str] = None  # FRTYPE=3 verbatim path
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    xpos_pt: Optional[float] = None    # pt overrides; ignored by frame_bbox_mm
    is_full_bleed: bool = False

@dataclass
class TextFrame(_Frame):
    text: str = ""; style: str = ""; fcolor: str = ""
    runs: Optional[list[Run]] = None
    columns: int = 1; col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None
    default_linesp_mode: Optional[int] = None
    fill: Optional[str] = None       # PCOLOR
    next_item: Optional["TextFrame"] = None
    def link_to(self, other) -> "TextFrame": ...  # threaded text (n/a for target IDML)

@dataclass
class ImageFrame(_Frame):
    src: str = ""; image: str = ""    # converter emits image=
    layer: int = 1                     # default Bilder
    local_scale: tuple[float,float] = (1.0, 1.0)
    local_offset_mm: tuple[float,float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1; ratio: int = 1; pic_art: int = 1
    inline_image_data: Optional[str] = None  # qCompress base64 (n/a for IDML)
    inline_image_ext: Optional[str] = None

@dataclass
class Polygon(_Frame):
    fill: str = "Black"; line_color: Optional[str] = None; line_width_pt: float = 0
    layer: int = 0
    shape: str = "rectangle"          # 'rectangle' | 'ellipse'  ← Oval → shape="ellipse"
    fill_shade: int = 100
    dash_pattern: Optional[tuple] = None

@dataclass(frozen=True)
class Run:
    text=""; has_itext=True
    font=None; fontsize=None; fcolor=None; fshade=None
    fontfeatures=None; kern=None
    char_style=None; paragraph_style=None
    paragraph_attrs=None
    separator=None     # "para" | "breakline" | "tab" | "breakcol" | "breakframe"
                       # ← <Br/> → Run(separator="breakline")

@dataclass(frozen=True)
class ParaStyle:
    name: str; parent: Optional[str] = None
    font=None; fontsize=None; fcolor=None
    align=None; linesp=None; linesp_mode=None
    space_before_pt=None; space_after_pt=None
    first_indent_pt=None; left_indent_pt=None; right_indent_pt=None
    # + bullet/numeration/drop_cap/underline/strike/shadow fields
    is_default: bool = False

@dataclass(frozen=True)
class DocumentLayer:
    name: str; visible: bool = True; printable: bool = True
    editable: bool = True; flow: bool = True
    transparent: float = 1.0; blend: int = 0
    outline: bool = False; layer_color: str = "#000000"

# Coordinate helpers (sla_lib/builder/document.py)
MM_TO_PT = 72.0 / 25.4
PT_TO_MM = 25.4 / 72.0
def mm_to_pt(value_mm): ...
</interfaces>

### Sibling template — `templates/kandidat-falzflyer-din-lang/`

Same physical format (A4 quer, 3-fold, 6 panels à 99×210). `meta.yml`
slot schema and layer naming (`Hintergrund`/`Bilder`/`Text`/`Falz`) are
clone-adjustable. Existing `build.py` is 1029 LOC, hand-organised as
constants → helpers → `build_preview`. The IDML emitter does NOT need
to reproduce this hand-organisation — emit flat per-page assemblies,
the human refactors after.

### CI surface — what the emitted template must satisfy

- `bin/render-gallery`: invokes `build.py` → `template.sla` + `preview.pdf`
- `tools/spec_check.py`: needs `templates/_specs/<slug>.md` with slots YAML; OPTIONAL — no-op if missing
- `tools/audit_alignment.py`: requires `build.py` to be import-clean, defines `build_doc`/`build_template`
- `tools/visual_diff.py`: opt-in per template via `meta.yml: original_sla:` + `baseline.pdf`. The new IDML target has **no SLA original** — `bin/validate` skips it. visual_diff against the bundled InDesign-rendered PDF is a follow-up (issue #36 / GH #73 territory).
- `bin/check-fontsizes`: rejects fractional FONTSIZE values — IDML PointSize can be fractional; rounder or warn
- `bin/check-stale-previews`: SHA-match against `meta.yml: previews_for_sla:`

---

## Standard Stack

| Library | Version | License | Role | Confidence |
|---|---|---|---|---|
| **SimpleIDML** | **1.3.1** (released 2025-08-15) | BSD-3 | IDML zip + XML access (designmap, spreads, stories) | HIGH — installed in container, verified imports |
| lxml | ≥5.0 (currently 5.4.0) | BSD-3 | Frame geometry parsing where SimpleIDML doesn't reach | HIGH — already in repo |
| PyYAML | (existing) | MIT | meta.yml emission | HIGH |

**Critical correction to ISSUE.md:** the SimpleIDML API has `pkg.style_groups`
(returns `RootCharacterStyleGroup`/`RootParagraphStyleGroup`), NOT
`pkg.character_styles` / `pkg.paragraph_styles`. The issue body listed
attributes that don't exist on `IDMLPackage`.

**License caveat:** SimpleIDML transitively pulls `suds-py3` (LGPL), used
only by `simple_idml.indesign` for InDesign-Server SOAP. We will **never
import `simple_idml.indesign`** — document this in a top-of-module
comment in `idml_to_dsl.py`.

**Install:** add `'SimpleIDML==1.3.1'` to the existing
`pip3 install --break-system-packages` block in `Dockerfile.claude`
(~lines 73-79) and add `simple_idml.idml` to the sanity-probe import
line. No new system packages needed.

---

## Don't-Hand-Roll List

- ❌ ZIP traversal, XML parsing of `designmap.xml` — `SimpleIDML.IDMLPackage` already does this
- ❌ Iterating spreads/stories/font_families/style_groups — already on `IDMLPackage`
- ❌ Affine matrix math for 2×3 transforms — write a tiny 8-line helper, don't pull `numpy`
- ❌ Color-space conversion — IDML CMYK strings map 1:1 to repo brand palette (verified)
- ❌ DSL primitives — every needed primitive exists in `sla_lib.builder`
- ❌ SLA emission — `Document.save()` does it; the emitter only writes the *Python source* that calls `save()`
- ❌ A new test harness — wire the emitted template into existing `bin/validate`

---

## Architecture Patterns

### Coordinate math (verified across all three forks)

The IDML→mm conversion is a **three-cascade**:

```
# Per PageItem (TextFrame / Rectangle / Polygon / Oval / Group):
# 1. PathPointArray anchors are in inner space (frame-centre for TextFrame,
#    spread-origin under identity for Rectangle/Polygon)
# 2. Apply matrix:   x' = a·x + c·y + tx,  y' = b·x + d·y + ty
# 3. Cascade up nested Groups:  M_effective = M_self · M_parent · M_grandparent · ...
#    (Indiscripts Chasles convention — right-multiply on each level)
# 4. Subtract Spread/ItemTransform translation (spread-centre → spread-stack-origin)
# 5. Subtract Page/ItemTransform translation (spread-stack-origin → page-top-left)
# 6. Convert pt → mm:  mm = pt * 25.4 / 72

# Confirmed empirically: PageWidth 841.8897… pt × 25.4/72 = 297.00 mm exactly.
```

For **rotated TextFrames** (`b≠0` or `c≠0`):
- IDML rotates around inner frame-centre
- Scribus `ROT` rotates CCW around top-left
- Pivot translation required: emit `rotation_deg = -atan2(b, a)` and
  pre-translate (x, y) by the post-rotation offset of the (0, 0) anchor
  back to the rotated bbox's top-left

For **axis-aligned frames** (the common case), `w = max_x - min_x` of
raw anchors, `h = max_y - min_y`, `(x_page, y_page)` derives from
`(tx, ty)` plus the inner-min-anchor offset.

### Emit-phase output shape (mirror sla_to_dsl.py)

```python
# Emitted build.py — flat per-page, hand-editable afterwards
from sla_lib.builder import (
    Brand, Document, DocumentLayer,
    TextFrame, ImageFrame, Polygon,
    Run, ParaStyle, Anchor,
)

INJECT_MAP: dict[str, str] = {}   # populated by human after emit

def build_template(out_path):
    brand = Brand.gruene_noe()
    doc = Document(
        title="...", template_id="...",
        brand=brand,
        layers=[
            DocumentLayer(name="Gestaltung", printable=True),
            DocumentLayer(name="Info", printable=False),  # IDML's non-printable Info layer
        ],
    )
    doc.add_master(...)
    page = doc.add_page(...)
    page.add(Polygon(x_mm=..., y_mm=..., w_mm=..., h_mm=..., fill="Dunkelgrün", anname="..."))
    page.add(TextFrame(x_mm=..., y_mm=..., w_mm=..., h_mm=..., runs=[Run(text="...", font="Gotham Narrow Bold", fontsize=14, fcolor="White")], style="Headline in grünem Kasten", anname="..."))
    page.add(ImageFrame(x_mm=..., y_mm=..., image="originals/.../Links/portrait.jpg", anname="..."))
    # ... per page
    doc.save(out_path)

def build_preview(out_path):
    # template + INJECT_MAP-driven asset wiring
    ...

def build(out_path):
    build_template(out_path)
```

### Resource resolution

IDML stores asset references as `file:` URIs pointing at the designer's
local path (e.g. `file:/Users/vonhollenstein/Library/Mobile Documents/.../portrait.jpg`).
The actual files are bundled alongside the IDML in `originals/.../Links/`.

Strategy: `--assets-dir originals/26-03-.../Links/` (default), resolve
each `file:` URI's basename against that dir, raise `UnhandledElement`
if missing.

---

## Common Pitfalls

### CRITICAL — must be handled in v1

| Pitfall | What goes wrong | Mitigation |
|---|---|---|
| **3-stacked coord cascade** | Frames land at wrong page coordinates if any of the 3 translations is skipped | Implement `_compute_page_local_bbox(item, ancestors, spread, page)` that applies all three explicitly + cascade Group ItemTransforms |
| **Rotated TextFrame pivot** | u347 (90°) on back, u186 (9°) on cover — IDML pivot ≠ Scribus pivot | Pivot-translate before emit; emit `rotation_deg` AND adjust `(x_mm, y_mm)` to the post-rotation top-left |
| **AI files appear as `<PDF>` not `<Image>`** | 5 of 7 contact icons (BlueSky/Mail/Website/Social-Media/Bund-Logo) are AI → skipped if we only filter `<Image>` | Detect nested `<PDF>` inside `<Rectangle>`; emit `ImageFrame` pointing at pre-rasterised PNG; require `--logo-map` YAML mapping AI/PDF Self-IDs → asset paths, or raise loudly if unmapped |
| **Info layer print marks** | 12 fold/safety guides on `Info` layer use non-brand swatches (`Color/Druckformat`, `Color/Faltung`, …) — would pollute brand palette if added | Map `Info` to `DocumentLayer(printable=False)`; either skip its items entirely or emit them with `layer=<info-idx>` and preserve raw swatch names |
| **Font cascade via ParaStyle chain** | `CharacterStyleRange` may set only `FontStyle="Black"` with no `AppliedFont` — family inherits from the applied paragraph style chain | Resolve `AppliedFont` by walking `<BasedOn>` chain up to NormalParagraphStyle; never assume inline font on the range |
| **Multiple ParagraphStyleRanges per frame** | One TextFrame can hold multiple paragraph styles | Emit one `Run` per range with `separator="para"` between, plus per-Run `paragraph_style=` |
| **`<Br/>` inside `<Content>`** | Hard line break inside a paragraph | Emit as `Run(separator="breakline")` between text runs |
| **Bleed = 2 mm, not 3 mm** | Target IDML uses 2 mm bleed; sibling falzflyer template hard-codes 3 mm | Pass `bleed_mm=2.0` to `add_master`/`add_page`. Raise `UnhandledElement` if `DocumentPreference DocumentBleed*Offset` is unexpected |
| **CMYK→Brand exact-match** | All 5 used brand colours map cleanly (Dunkelgrün, Gelb, Magenta, Black, White; CMYK values match `shared/ci.yml`) | Implement exact-CMYK match only. Raise on non-brand printable swatches. Skip Paper/Registration. Snap-to-brand fuzzy matching is OUT OF SCOPE for v1 |

### LIKELY — raise loudly, extend per-corpus

- Threaded TextFrames (`NextTextFrame` ≠ "n") — zero in corpus; raise
- Anchored objects — zero in corpus; raise
- Master-spread items beyond master-page bounding box — empty in corpus; raise on any
- `<Oval>` — present (1 instance, page 1); emit as `Polygon(shape="ellipse")`
- Nested `<Group>` with own `ItemTransform` — 5 groups page 1, 10 page 2; cascade required
- Multiple-paragraph `<ParagraphStyleRange>` with `<BasedOn>` inheritance — present; emit `ParaStyle(parent=...)`
- Non-zero `<ParagraphStyleRange>`-level overrides on `PointSize` / `FillColor` — fold into the trailing `Run` rather than redefining the ParaStyle

### Strict-mode UX

Every `raise UnhandledElement(...)` includes element kind + Self ID +
offending attribute + `(extend tools/idml_to_dsl.py:_function_name)`
hint. Mirror `sla_to_dsl.py:59` and `:1281-1283` verbatim.

### Security

- IDML is a ZIP — SimpleIDML uses stdlib `zipfile.ZipFile`, no zip-slip path traversal (CWE-22 mitigated upstream)
- XML parsing — lxml 5.4 is XXE-safe by default on `etree.fromstring` (CVE-2026-41066 affects only `iterparse` / `ETCompatXMLParser`, which we don't use)

---

## Environment Availability

| Component | Status | Notes |
|---|---|---|
| Python 3.13.5 | ✅ in container | Compatible with SimpleIDML 1.3.1 (≥3.9) |
| SimpleIDML 1.3.1 | ✅ pre-installed | Pin in `Dockerfile.claude` lines 73-79; add `simple_idml.idml` to sanity-probe |
| lxml 5.4.0 | ✅ in container | XXE-safe by default |
| Scribus 1.6.5 (xvfb-run) | ✅ via `tools/_export_pdf.py` | Renders emitted `template.sla` → `preview.pdf` |
| Brand fonts (Gotham Narrow Book/Bold/Black/Ultra, Vollkorn Black Italic) | ✅ in `fonts/` | Names match IDML font references |
| Image assets | ✅ in `originals/26-03-.../Links/` | 7 raster + AI assets present |
| Target IDML | ✅ verified openable | 2 spreads, 23 stories, 6 font families, 5 style groups, 15 colours |

---

## Project Constraints

- **Issue file at:** `.worktrees/35-idml-to-dsl-converter-strict-bootstrap/.issues/35-idml-to-dsl-converter-strict-bootstrap/ISSUE.md` (worktree; `commit_artifacts: true`)
- **Branch:** `issue/35-idml-to-dsl-converter-strict-bootstrap` from `origin/main`
- **GitHub mirror:** https://github.com/GrueneAT/vorlagen/issues/72
- **No baseline.pdf for visual_diff v1.** Sibling falzflyer doesn't have one; this template won't either. Visual review goes through `bin/render-gallery` + manual inspection until issue #36 (bbox extractor) lands.
- **Worktree caveat:** during issue creation, the `.git/worktrees/35-…` ref was accidentally pruned and re-added; branch tip is intact at commit `4a294ad` (which contains ISSUE.md with `## Acceptance Criteria` capitalised; AC heading was amended in-place). No further fragility expected.

---

## Open Questions for Plan Stage

These six questions surfaced across all three forks. The planner should
either pick a default explicitly or punt to the executor with a clear
strict-mode raise:

1. **Color mapping policy** — verbatim CMYK names (`Color/C=85 M=35 Y=95 K=10`) or auto-rename to brand names (`Dunkelgrün`) on exact CMYK match? Codebase fork: prefer auto-rename for the 5 brand colours; raise on others. Ecosystem fork: confirms exact match is safe. **Recommended default: auto-rename on exact CMYK match against `shared/ci.yml` palette; raise on non-brand printable swatches.**
2. **Vector-logo assets** — AI/PDF logos need pre-rasterised PNG counterparts. Approach: `--logo-map FILE.yml` mapping Self-ID → asset path? Or hard-raise and let the human extend the converter per logo? **Recommended default: hard-raise with a list of unmapped logos in the message; let the human stage assets and re-run.**
3. **Raster source bytes** — IDML uses external `Links/` references, not embedded streams. Use `--assets-dir originals/<bundle>/Links/` (default), resolve `file:` URI basename against it. **Recommended default: yes, with that flag.**
4. **Bleed value** — keep IDML's 2 mm or coerce to brand-standard 3 mm? **Recommended default: keep IDML value (2 mm). Document mismatch in emitted build.py comment.**
5. **Falz lines** — derive from IDML guides on the `Info` layer or add manually post-bootstrap (matching sibling template's `FoldLine` block)? **Recommended default: skip in converter; add manually post-emit (sibling pattern).**
6. **SimpleIDML dependency** — runtime requirement or only-when-converter-runs? Converter is one-shot, not CI. **Recommended default: development-only dependency. Pin in `Dockerfile.claude` because the dev image is the same as the CI image.**

---

## Sources

| Source | Confidence |
|---|---|
| `tools/sla_to_dsl.py` (1288 LOC, read in full) | HIGH |
| `tools/sla_lib/builder/{__init__,document,primitives,styles,brand,bbox,blocks}.py` | HIGH |
| `templates/kandidat-falzflyer-din-lang/{meta.yml,build.py}` | HIGH |
| `originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/...idml` (extracted, walked) | HIGH |
| `.issues/archive/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/` (prior art) | HIGH |
| [Adobe IDML File Format Specification PDF (IDMLlib mirror)](https://raw.githubusercontent.com/jorisros/IDMLlib/master/docs/idml-specification.pdf) | HIGH |
| [Indiscripts: Coordinate Spaces & Transformations vol. 5 PDF](https://indiscripts.com/blog/public/data/coordinate-spaces-and-transformations-5/CoordinateSpacesTransfos01-05.pdf) | HIGH |
| [SimpleIDML PyPI](https://pypi.org/pypi/SimpleIDML/json) | HIGH |
| [Starou/SimpleIDML GitHub source](https://github.com/Starou/SimpleIDML) | HIGH |
| [Adobe community: IDML Rotation Matrix concern](https://community.adobe.com/t5/indesign-discussions/idml-rotation-matrix-concern/m-p/9680181) | MEDIUM |
| [Adobe community: TextFrame Position in IDML with Python](https://community.adobe.com/t5/indesign-discussions/how-to-determining-textframe-position-in-idml-using-xml-and-python-handling-negative-values/m-p/14836594) | MEDIUM |
| [Customer's Canvas: Importing AI graphics to IDML](https://customerscanvas.com/help/designers-manual/adobe/indesign/importing-ai-graphics.html) | MEDIUM |
| [lxml FAQ](https://lxml.de/FAQ.html) (XXE defaults) | HIGH |
| [GitLab advisory CVE-2026-41066](https://advisories.gitlab.com/pypi/lxml/CVE-2026-41066/) | HIGH |
| guardian/pyidml (archived; confirmed dead) | HIGH |

---

**Next:** `/issue:plan 35-idml-to-dsl-converter-strict-bootstrap`
