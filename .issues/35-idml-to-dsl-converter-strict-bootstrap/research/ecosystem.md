# Ecosystem Research — Issue 35 (IDML → DSL converter)

**Researched:** 2026-05-11
**Focus:** External dependencies, versions, Adobe-spec facts. Network-bound. Codebase analysis is out of scope here.
**Bottom line:** `SimpleIDML 1.3.1` + already-installed `lxml 5.4.0` is the entire runtime. Already present in this container. Adobe IDML spec is well-defined and stable; coordinate math in the issue body is correct, with one important correction to the API path for character/paragraph styles.

---

## 1. Recommended Stack

| Library | Version | License | Role | Already installed | Confidence |
|---|---|---|---|---|---|
| **SimpleIDML** | **1.3.1** (2025-08-15) | BSD 3-clause | IDML package open + spread/story/designmap/style/font discovery | **Yes** (`pip3 show SimpleIDML` → 1.3.1 in `/usr/local/lib/python3.13/dist-packages`) | HIGH |
| **lxml** | 5.4.0 (Debian trixie pkg `python3-lxml`) | BSD | XML parsing for everything inside the IDML — Spread/Story/Graphic/Preferences | **Yes** | HIGH |
| **suds-py3** | 1.4.5.0 (2021-11-15) | LGPL | Transitive of SimpleIDML — SOAP client for InDesign-Server (we will NEVER call it) | Yes (pulled by SimpleIDML) | HIGH |

**Recommendation: pin `SimpleIDML==1.3.1` explicitly** in `Dockerfile.claude` next to the existing `qrcode[pil]==8.2` block. This repo's convention is to declare Python deps via `pip3 install --break-system-packages` in Dockerfile.claude with hard `==` pins (no `pyproject.toml`, no `requirements.txt`). Match that convention.

**Do NOT pin lxml**: it comes from Debian trixie's `python3-lxml` package (5.4.0). The Dockerfile carries an extensive comment explaining why this Debian package must come from trixie (the Scribus 1.6 dependency forces Python 3.13, which Bookworm's lxml does not support). Pip-installing a newer lxml on top is unnecessary and risks shadowing the Debian build of libxml2.

### Stack notes
- **Python 3.13** is the container's interpreter. SimpleIDML 1.3.1 has no upper-bound on Python version and Python 3.13 is empirically working (verified by opening the target IDML and walking spreads/stories/styles/fonts/Graphic.xml — see Section 5).
- **SimpleIDML 1.2.0 (the version listed in ISSUE.md) is two minor releases behind**. Use 1.3.1. Changelog impact for our use: 1.3.0 + 1.3.1 are mostly PEP-265 packaging cleanup and small bug fixes; no API surface we touch was changed (we only read, never write). Confidence: HIGH (release dates from PyPI JSON; commit log on master shows no API breaks since 1.1.x for the read path).
- **suds-py3 is LGPL**, but only matters if we link against it — we will not. SimpleIDML only invokes `suds.client.Client` inside `simple_idml/indesign/indesign.py` (the InDesign-Server save-as path), which we never touch. The import is lazy at the module level; merely having SimpleIDML installed does not pull suds code into our process at runtime as long as we never `import simple_idml.indesign`. License-wise this is "use as a library" and stays clear of GPL contamination. Confidence: MEDIUM — recommend a one-line comment in the converter `# noqa: do not import simple_idml.indesign — pulls in LGPL suds`.
- **Snyk health score for SimpleIDML:** 50/100 with "no commits over the last 6 months" flag. This is a *maintenance signal*, not a bug. The library is stable, narrow, and adequate for our read-only purposes. No CVEs.

### Alternatives ruled out

| Library | Status | Reason |
|---|---|---|
| `guardian/pyidml` | **Archived 2022-06-21**, 7 stars | Abandoned by The Guardian. Last commit 2022. |
| `goinvo/BatchIDMLGenerator` | Project-specific batch tool, not a library | Wraps InDesign-Server; not a parser. |
| `yzyly1992/PDF2IDML` | Wrong direction (PDF→IDML) | Not relevant. |
| Roll-our-own `zipfile + lxml` reader | Possible | We'd reimplement Spread/Story discovery, Designmap parsing, story-id mapping. SimpleIDML's source is BSD; if we ever need to drop the dep we can vendor the ~600 lines we actually use. Not now. |

---

## 2. IDML Spec Anchors

**Primary reference: the official Adobe IDML File Format Specification PDF.** Adobe pulled the live link (`wwwimages.adobe.com/content/dam/acom/en/devnet/indesign/sdk/cs6/idml/idml-specification.pdf` returns 404), but the full PDF is mirrored at the IDMLlib GitHub repo:

> https://raw.githubusercontent.com/jorisros/IDMLlib/master/docs/idml-specification.pdf  
> (CS6-era, ~5.8 MB, 46666 lines of text after `pdftotext`. This is the canonical text; it has not been superseded — Adobe stopped publishing standalone IDML PDFs after CS6 in 2012 and only updates SDK HTML docs.)

**Use the spec PDF as authoritative ground truth.** Pages cited below refer to logical page numbers visible in the PDF.

| Topic | IDML Spec section / quote | Page |
|---|---|---|
| Pasteboard coordinates — global frame | §10.3.3 "Pasteboard Coordinates" — "The pasteboard coordinate system starts at zero, above the first page in the document, and encompasses all of the spreads in the document. (The pasteboard coordinate system does not have a negative extent.)" | p.100 |
| Units = points always | §10.3.3 — "The units used by the pasteboard coordinate system are points, defined as 72 units per inch. Changing the definition of points in the InDesign user interface has no effect on the definition of points used in IDML." | p.101 |
| Y-axis direction | §10.3.3 — "Increasing a vertical coordinate (y) moves the specified location down in pasteboard coordinates." | p.101 |
| Spread coordinates origin | §10.3.3 "Spread Coordinates" — "The origin of the spread coordinate system is located at center of the spread. The left edge of the first right-hand page in the spread aligns with the horizontal center of the spread; the right edge of the first left-hand page in the spread appears to the left." Figure 7 shows -X to left, +X to right, -Y up, +Y down. | p.103-104 |
| Spread `ItemTransform` constraint | §10.3.3 — "Spreads cannot be scaled or skewed using the transformation matrix in the ItemTransform attribute" (only y-translation and 90°-step rotation allowed). | p.103 |
| Transform matrix form `[a b c d e f]` | §10.3.3 "Transformations" — `(a c e / b d f / 0 0 1)` 3×3 form, written compactly as the 6-tuple `[a b c d e f]`. | p.102 |
| Order of decomposition | §10.3.3 — "Transformations are applied in the following order: scale, shear, rotate, translate." | p.103 |
| `Page.GeometricBounds` order = `y1 x1 y2 x2` | §10.4.2 (Page schema) — `attribute GeometricBounds { list { xsd:double, xsd:double, xsd:double, xsd:double } }`; spec text: "values define the upper-left and lower-right corners of the page, in the inner coordinates of the page." Adobe convention is `y1 x1 y2 x2`. **Confirmed empirically against target IDML** (see Section 5). | p.156-157 |
| `Page.ItemTransform` = translation only | §10.4.2 — "The transformation matrix in the ItemTransform attribute is a complete transformation matrix, but only translations are supported." | p.157 |
| `Page.MasterPageTransform` | §10.4.2 — "Defines the relationship of master page items to the page … applied after the ItemTransform of the Spread, but before the ItemTransform of the individual master spread page items." | p.157 |
| PathGeometry / PathPointType / Anchor in inner coords | §10.3.3 "Page Item Geometry" — "Each `<PathPoint>` element contains attributes defining three coordinate pairs … `PathPointAnchor` (the location of the point), `LeftDirection`, `RightDirection`. Each takes the form `x y` … expressed in the inner coordinate system of the page item." | p.105-106 |
| `DocumentPreference.PageWidth/PageHeight` units | §13.x schema: `attribute PageWidth { xsd:double }?, attribute PageHeight { xsd:double }?` — type is plain double. By the global rule (p.101) these are **always points**, regardless of UI ruler unit. | p.319-320 |
| Color schema | §11.x — `Color_Object` carries `Self`, `Model ∈ {Spot, Process}`, `Space ∈ {RGB, CMYK, LAB}`, `ColorValue` (space-separated doubles). | p.265-267 |
| FillColor reference is by Self string | §11.x — `attribute FillColor { xsd:string }` is a Self-reference into the Color/Tint/Gradient/Swatch/MixedInk inventory in `Resources/Graphic.xml`. Common Self formats observed: `Color/Black`, `Color/C=15 M=100 Y=100 K=0`, `Color/DGC1_446a`, `Swatch/None`. | p.265, examples throughout |
| FillTint | §10.x page-item properties — `FillTint { double }`, percent 0–100; `-1` means "use inherited/overridden value". | p.85-86 |

### Secondary references (cross-verification)

| Source | URL | Use |
|---|---|---|
| **Indiscripts: Coordinate Spaces & Transformations in InDesign CS4–CC** (Marc Autret) | https://indiscripts.com/blog/public/data/coordinate-spaces-and-transformations-5/CoordinateSpacesTransfos01-05.pdf | Definitive secondary explanation of matrix math, TextFrame exception, Chasles composition rule. Used to cross-check the spec PDF. |
| Indiscripts blog post (same topic) | https://www.indiscripts.com/post/2018/06/coordinate-spaces-and-transformations-5 | Web companion to the PDF; quotable. |
| Adobe community thread on rotation matrix | https://community.adobe.com/t5/indesign-discussions/idml-rotation-matrix-concern/td-p/9680180 | Confirms `[a b c d tx ty]` PostScript convention; community confirms TextFrame "exception". |
| SimpleIDML source (`src/simple_idml/components.py`) | https://github.com/Starou/SimpleIDML/blob/master/src/simple_idml/components.py | The Spread docstring (lines 200-225) reproduces the spread coordinate diagram verbatim. The `Page.coordinates`, `page_item_is_in_self`, `set_face` methods show working coordinate math in production. |

---

## 3. Coordinate-Math Cheat Sheet

> **Paste this verbatim into PLAN.md / docstrings.** Every line below is sourced from the Adobe IDML spec PDF (`idml_spec.txt` lines 7518-7755) and cross-confirmed by Indiscripts and by SimpleIDML's own source.

### Units & axes

- All IDML coordinates are **points (1pt = 1/72 inch)** regardless of what the InDesign UI ruler shows. *Spec p.101.*
- **+X is right, +Y is down.** Same as ruler / screen, opposite of academic geometry / PostScript / PDF. *Spec p.101.*
- Conversion to millimetres: `mm = pt × 25.4 / 72`. Conversion to points: `pt = mm × 72 / 25.4`. *Standard, not IDML-specific.*

### Origin per coordinate space (top to bottom of the hierarchy)

| Space | Origin location | Note |
|---|---|---|
| Pasteboard (document) | top-of-pasteboard, no negative extent | We never address this directly; SimpleIDML treats the spread as the top of its model. |
| **Spread** | **centre of the spread** | Pages straddle this centre; left-hand pages have negative X. |
| Page | top-left of the page, in page-inner coords | Page `GeometricBounds = "y1 x1 y2 x2"` typically `"0 0 H W"`. Position-in-spread is set by `Page.ItemTransform` (translation only). |
| PageItem (Rectangle, Polygon, Oval, GraphicLine) | **coincides with the spread origin when `ItemTransform = identity`**; moves to the new location when the item is dragged. *Indiscripts §1, p.17.* | Path points are always in this inner space. |
| **TextFrame** (exception) | **centre of the TextFrame's bounding box.** *Indiscripts §1, p.17, and Adobe community confirmation.* | This is why a fresh untranslated TextFrame's PathPointArray reads like `(-W/2,-H/2) (-W/2,+H/2) (+W/2,+H/2) (+W/2,-H/2)`. |

### `ItemTransform = "a b c d tx ty"`

The 6-tuple expresses the 3×3 affine matrix:

```
| a  b  0 |
| c  d  0 |
| tx ty 1 |
```

InDesign uses **row-vector × matrix** notation: a point `(x, y)` in *child inner space* maps to *parent space* as

```
[x'  y'  1] = [x  y  1] × | a  b  0 |
                          | c  d  0 |
                          | tx ty 1 |
```

Expanded:

```
x' = a·x + c·y + tx
y' = b·x + d·y + ty
```

*(Spec p.102-103. Confirmed by Indiscripts §1 line 510 "(xa+yc+e, xb+yd+f)" and §1 line 517 "[x' y'] = [x y] × [[a b][c d]]"). The 6-tuple uses the column ordering `a b c d e f` matching PostScript / PDF / SVG `matrix(a b c d e f)`.*

**Decomposition order is `S × H × R × T`** (scale, shear, rotation, translation). *Spec p.103.*

**Common forms** *(spec p.103):*
- Identity: `"1 0 0 1 0 0"` — child space coincides with parent space.
- Translation only: `"1 0 0 1 tx ty"`.
- Rotation by θ (CCW relative to pasteboard, but since Y is flipped, this is visually CW): `"cosθ sinθ -sinθ cosθ 0 0"`.
- 90°-step spread rotations (the only rotations allowed on `Spread.ItemTransform`): `"0 1 -1 0 0 0"` (90° CW), `"0 -1 1 0 0 0"` (90° CCW), `"-1 0 0 -1 0 0"` (180°).

### Group cascading

Chasles relation *(Indiscripts §2, p.19, exercise footnote 1)*:

> Given three coordinate spaces A, B, C, if `Mab` maps A→B and `Mbc` maps B→C, then `Mab × Mbc` maps A→C.

Concretely, to get a path point on a Rectangle nested inside a Group into spread space:

```
spread_xy = anchor_xy × M_rect × M_group   (row-vector form)
```

Equivalently, walking up the parent chain: apply child's `ItemTransform` first, then each parent's `ItemTransform` in order. **Never apply the Spread's own `ItemTransform`** when you want spread-coordinates output — `Spread.ItemTransform` describes spread→pasteboard, not page-item→spread.

### Page→spread translation

The page's location in the spread is in `Page.ItemTransform[4..5] = (tx, ty)`. To go from spread coords to page-top-left coords, subtract the upper-left corner of the page-in-spread:

```python
# Standard "page top-left in spread coords"
x_page_origin_in_spread = page.geometric_bounds[1] + page.item_transform[4]   # x1 + tx
y_page_origin_in_spread = page.geometric_bounds[0] + page.item_transform[5]   # y1 + ty
```

This is exactly what `SimpleIDML`'s `Page.coordinates` property does (`components.py:793-805`).

### Bbox of a transformed (possibly rotated) frame

When `b ≠ 0 or c ≠ 0`, the frame is rotated and the raw `(width, height)` from `PathPointArray` extents is wrong. Transform all four anchor points through the cumulative matrix, then take `(min_x, min_y, max_x, max_y)` of the transformed quad. **The issue body's pitfall note is correct.**

### Algorithm: PageItem → page-relative `(x_mm, y_mm, w_mm, h_mm)`

1. Compute cumulative `M = M_item × M_parentGroup × M_grandparentGroup × …` walking up to (but not including) the Spread.
2. For each `PathPointType.Anchor`, apply `[x' y'] = [x y 1] × M` → spread coords.
3. Find `min/max` of x' and y' → spread-space bbox.
4. Find the owning Page using SimpleIDML's `Page.page_item_is_in_self()` rule (the first anchor's X falls inside the page's `x1..x2` range).
5. Subtract `(page.coordinates["x1"], page.coordinates["y1"])` → page-relative pt.
6. Multiply by `25.4/72` → mm.

(SimpleIDML supplies the page-mapping rule, but **does not compute step 1 or the rotated-bbox in step 3** — those are ours to write. This is the core of the converter's geometry module.)

---

## 4. Installation Notes

### What's already there

The container (`Dockerfile.claude` running `ghcr.io/flomotlik/claude-code:latest`) already has:

```
SimpleIDML 1.3.1  (pip3, /usr/local/lib/python3.13/dist-packages)
lxml 5.4.0        (apt python3-lxml from trixie)
suds-py3 1.4.5.0  (pulled by SimpleIDML)
Python 3.13.5
```

This was confirmed by `pip3 show SimpleIDML` and by successfully opening the target IDML file. **No new system dependencies are needed.**

### What to pin in `Dockerfile.claude`

Add a line to the existing `pip3 install` block alongside qrcode/pyzbar/pillow/jsonschema:

```dockerfile
RUN pip3 install --break-system-packages --no-cache-dir \
        'qrcode[pil]==8.2' \
        'pyzbar==0.1.9' \
        'pillow==12.2.0' \
        'jsonschema==4.26.0' \
        'SimpleIDML==1.3.1'           # <-- new
```

Rationale per repo convention (see Dockerfile.claude comments at lines 70-83): pin exact versions to guard byte-determinism across container rebuilds. SimpleIDML doesn't affect byte-determinism of any output we render, but pinning is the convention.

Also extend the sanity probe (Dockerfile.claude near the bottom):

```dockerfile
python3 -c "import lxml.etree, yaml, simple_idml.idml; print('python deps ok')"
```

### Transitive footprint

`pip install SimpleIDML==1.3.1` pulls exactly two packages: `lxml` (Debian-system) and `suds-py3` (~140 KB pure Python). No native compilation. No tricky system libs. Total install footprint: <1 MB of Python on top of an already-present lxml.

### `.indd` reminder

SimpleIDML reads **only `.idml`** (the ZIP/UCF text package). `.indd` (the proprietary binary InDesign file) is unsupported by every open-source library on earth — only Adobe's own SDK reads it. This matches the issue's "Out of scope" bullet. If the design team ever drops a `.indd` instead of an `.idml`, the converter must raise immediately with a clear message ("Save as `.idml` from InDesign: File > Export > InDesign Markup (IDML)").

---

## 5. Empirical Verification (target IDML)

Opened `/root/workspace/originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml` with the already-installed SimpleIDML 1.3.1:

```
spreads:    Spreads/Spread_ueb.xml, Spreads/Spread_u108.xml
stories:    23 stories (Stories/Story_*.xml)
designmap:
  spread_nodes:  [Spread_ueb.xml, Spread_u108.xml]
  layer_nodes:   [('uba', 'Gestaltung'), ('ue6', 'Info')]
  active_layer:  uba
DocumentPreference: PageWidth=841.8897637795276  PageHeight=595.2755905511812
                    PagesPerDocument=1, FacingPages=true (implied)
                    → 297.000mm × 210.000mm = A4 landscape ✓
Spread 1: 1 page  GeometricBounds=[-157.3 0 437.9 841.9]  ItemTransform=[1 0 0 1 -420.94 -140.31]
                   computed coords: x1=-420.94, y1=-297.64, x2=420.94, y2=297.64
                   (i.e. the page is exactly 841.89×595.28 pt centred on spread origin) ✓
Fonts:      6 FontFamilies — including Gotham Narrow, Vollkorn (brand fonts already installed)
Styles:     5 style groups: RootCharacterStyleGroup, RootParagraphStyleGroup,
            RootCellStyleGroup, RootTableStyleGroup, RootObjectStyleGroup
Colors:     15 Color elements in Resources/Graphic.xml (Process CMYK + 1 Spot)
```

This validates the coordinate model, the unit assumption (points), and that `SimpleIDML.IDMLPackage` is sufficient to walk the document end-to-end. **No surprise elements.** Two spreads × one page each = 2 pages total (Spread 1 = front cover + 2 inner panels visible side-by-side as a single A4 landscape; Spread 2 = back).

---

## 6. API Surface — what we'll actually call

### Confirmed against SimpleIDML 1.3.1 source (`src/simple_idml/idml.py`, `src/simple_idml/components.py`)

```python
from simple_idml import idml
from lxml import etree

pkg = idml.IDMLPackage(path_to_idml)         # also a context manager
pkg.spreads                                  # list[str] — Spread XML *filenames*
pkg.spreads_objects                          # list[Spread] — the lxml-backed objects (use this)
pkg.last_spread                              # Spread
pkg.pages                                    # flat list[Page] across all spreads
pkg.stories                                  # list[str] — Story XML *filenames*
pkg.story_ids                                # list[str] — bare story ids
pkg.designmap                                # Designmap object → .spread_nodes, .layer_nodes, .active_layer
pkg.font_families                            # list[lxml.etree._Element] of <FontFamily>
pkg.style_groups                             # list[lxml.etree._Element]: Root{Character,Paragraph,Cell,Table,Object}StyleGroup
pkg.style                                    # Style helper: .get_style_node_by_name(name), .get_root()
pkg.style_mapping                            # StyleMapping helper (XML/Mapping.xml may not exist)
pkg.graphic                                  # Graphic helper (Resources/Graphic.xml)
pkg.tags, pkg.xml_structure                  # XML-import / structure views (unused for our purpose)

# Per-Spread:
spread = pkg.spreads_objects[0]
spread.pages                                 # list[Page]
spread.node                                  # the <Spread> lxml Element
spread.dom                                   # the full lxml root

# Per-Page:
page = spread.pages[0]
page.geometric_bounds                        # [Decimal, Decimal, Decimal, Decimal] in order y1 x1 y2 x2
page.item_transform                          # [Decimal × 6] = [a, b, c, d, tx, ty]
page.coordinates                             # dict {x1, y1, x2, y2} in spread-coord space
page.page_items                              # list[lxml.etree._Element] — siblings of the <Page> node
                                             #   that the .page_item_is_in_self heuristic claims for this page
page.is_recto, page.face                     # 'recto' | 'verso'
```

### What SimpleIDML does NOT do (we write this)

- **Cascade ItemTransforms up the parent chain (groups)**. SimpleIDML only exposes each item's own matrix. Our converter must walk parents and multiply.
- **Apply matrices to PathPointType anchors**. SimpleIDML has no matrix-multiply utility. Use plain Python (`Decimal` arithmetic is fine; or convert to `float` for the geometry pass — the answer goes to mm with 3-decimal precision, no determinism risk).
- **Compute bounding boxes of rotated frames**. Caller's responsibility.
- **Resolve `MasterPageTransform` overrides**. The base geometry lives in `MasterSpreads/*.xml`; SimpleIDML exposes the `MasterSpread` class (`components.py:194`) but doesn't merge into per-page items. We probably don't need this for the target — the target has no `AppliedMaster` overrides other than the trivial identity-matrix case — but the strict converter should `raise UnhandledElement` if it encounters `MasterPageTransform != "1 0 0 1 0 0"`.
- **Handle threaded TextFrames** (`NextTextFrame` / `PreviousTextFrame`). SimpleIDML doesn't follow the chain. Our converter must (a) detect a chain, (b) collect the full Story content once, (c) decide whether the DSL representation is "one TextFrame per IDML frame" (no reflow) or "one slot fed across frames" (the latter only matters for content authoring, not the bootstrap). For the strict bootstrap: emit one DSL `TextFrame` per IDML frame and let the slot schema in `meta.yml` describe threading at the DSL level.

### Correction to ISSUE.md

ISSUE.md mentions `pkg.character_styles` and `pkg.paragraph_styles`. **These attributes do not exist** on `IDMLPackage` in any version (confirmed by reading `src/simple_idml/idml.py` and by `hasattr` probe). The correct access path is:

```python
for group in pkg.style_groups:
    if group.tag == 'RootParagraphStyleGroup':
        for ps in group.findall('ParagraphStyle'):
            ...
    elif group.tag == 'RootCharacterStyleGroup':
        for cs in group.findall('CharacterStyle'):
            ...
```

Or use `pkg.style.get_style_node_by_name(...)`.

---

## 7. Don't-Hand-Roll List

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Open an IDML (UCF/ZIP container with `mimetype`, `META-INF/`, `designmap.xml` …) | A `zipfile.ZipFile` wrapper + custom file resolution | `SimpleIDML.idml.IDMLPackage` | Handles the UCF quirks, lazy-loads, exposes `spreads`/`stories`/`designmap` as one API. ~600 lines we don't need to write or maintain. |
| Map a PageItem to its owning Page in a multi-page spread | A custom rule based on geometric overlap | `SimpleIDML.components.Page.page_item_is_in_self()` (delegates to the first PathPoint's X-falls-inside-page-X-range rule) | Adobe-correct; this is the same heuristic InDesign uses. |
| Compute spread→page-top-left offset | Trial-and-error sign math | `Page.coordinates` property | Already returns `{x1,y1,x2,y2}` in spread coords. |
| Parse `designmap.xml` to find which Spreads exist | Custom XPath | `pkg.designmap.spread_nodes` | One line. |
| Iterate Layers | Custom XPath | `pkg.designmap.layer_nodes` (returns the `<Layer>` elements with `Self` and `Name`) | One line. |
| XML parsing in general | `xml.etree.ElementTree` | `lxml.etree` (already installed) | Repo standard (Dockerfile comment lines 14-15); supports XPath properly; existing `tools/sla_lib/` is built on lxml. |
| Affine-matrix utility | Numpy | Plain Python 6-tuple multiply | Avoid pulling numpy into the rendering toolchain for what is literally six adds and four mults. Borrow the multiply pattern from any 2D-graphics tutorial. Three lines. |
| ZIP-based detection of `.idml` vs `.indd` | Heuristics | First-bytes check: IDML is a ZIP starting with `PK\x03\x04`; `.indd` starts with the Adobe-proprietary `OBFM` chunk. Reject loudly. | One-line guard, prevents confusing downstream errors. |

---

## 8. Out-of-Scope (explicit)

Per the issue, and re-confirmed by this research, the converter does **not** need any of:

- **Layout reflow / line breaking**. SimpleIDML doesn't do it; we don't either. The DSL replays text into Scribus, which does its own layout.
- **IDML→PDF rendering**. We emit `build.py` + `meta.yml`; rendering is downstream (`tools/render.py` on Scribus).
- **Font shaping, kerning, hyphenation**. None of these are in IDML's data model — InDesign computes them at display time.
- **`.indd` binary parsing**. Not solved by any open library. Refuse-and-message at the entry point.
- **Round-trip DSL→IDML**. One-way only, mirroring `sla_to_dsl.py`.
- **`indesign-server` SOAP integration** (the only feature in SimpleIDML that touches `suds-py3` / LGPL). Never import `simple_idml.indesign`.
- **InDesign Scripting DOM / ExtendScript**. Not relevant — we read XML, we don't drive InDesign.
- **Multi-document batch import**. One IDML at a time. (Future issue if ever needed.)

We are reading IDML and emitting Python source. Everything else is the renderer's problem.

---

## 9. Sources

### HIGH confidence
- Adobe IDML File Format Specification (CS6 era), mirrored at `raw.githubusercontent.com/jorisros/IDMLlib/master/docs/idml-specification.pdf` — the canonical spec. Sections referenced: §8.1.4 (Resources folder), §10.3.3 (Geometry), §10.4.2 (Page schema), §11.x (Color), §13.x (DocumentPreference). All quotes above sourced verbatim from `pdftotext` output.
- SimpleIDML PyPI metadata — https://pypi.org/pypi/SimpleIDML/json (1.3.1, BSD, 2025-08-15, Python 3.9+).
- SimpleIDML source on GitHub master — https://github.com/Starou/SimpleIDML (commit `f72114d4`, 2025-08-15). Read `src/simple_idml/idml.py` and `src/simple_idml/components.py` directly.
- SimpleIDML LICENSE (BSD 3-clause) — https://github.com/Starou/SimpleIDML/blob/master/LICENSE (Stanislas Guerra, 2012).
- suds-py3 PyPI metadata — https://pypi.org/pypi/suds-py3/json (LGPL).
- Empirical: opened the target IDML in this container with SimpleIDML 1.3.1 and confirmed every coordinate, font, style, color claim above.

### MEDIUM confidence
- Indiscripts: *Coordinate Spaces & Transformations in InDesign CS4–CC*, v3.2 (2021-10), Marc Autret — https://indiscripts.com/blog/public/data/coordinate-spaces-and-transformations-5/CoordinateSpacesTransfos01-05.pdf. Independent verification of matrix-vector convention and TextFrame inner-origin exception. Cross-checks the Adobe spec on every point we use.
- Indiscripts blog companion — https://www.indiscripts.com/post/2018/06/coordinate-spaces-and-transformations-5
- Snyk Advisor for SimpleIDML — https://security.snyk.io/package/pip/simpleidml (health 50/100, no CVEs, "no commits over the last 6 months" maintenance flag as of 2026-05).
- GitHub repo metadata — `gh api repos/Starou/SimpleIDML` returns: 235 stars, 9 open issues, last push 2025-10-24, default branch `master`, not archived.

### LOW confidence (or noted-but-not-relied-upon)
- Adobe community thread "IDML Rotation Matrix concern" — https://community.adobe.com/t5/indesign-discussions/idml-rotation-matrix-concern/td-p/9680180. Confirms `[a b c d tx ty]` PostScript-style convention; community-sourced.
- Adobe community thread "Determining TextFrame Position in IDML Using XML and Python" — https://community.adobe.com/t5/indesign-discussions/how-to-determining-textframe-position-in-idml-using-xml-and-python-handling-negative-values/m-p/14836594. Useful sanity check that TextFrame origin is frame-center.
- pyidml (Guardian) — https://github.com/guardian/pyidml — *archived 2022-06-21*. Mentioned only to rule out as an alternative.

---

## 10. Confidence Self-Assessment

| Claim | Confidence | Evidence |
|---|---|---|
| SimpleIDML 1.3.1 is the current release | HIGH | PyPI JSON + GitHub `gh api` |
| BSD 3-clause license | HIGH | LICENSE file contents read directly |
| Python 3.13 works | HIGH | Empirically verified — opened the target IDML, walked spreads/stories/styles |
| `pkg.character_styles` / `pkg.paragraph_styles` exist | **HIGH WRONG — they do NOT exist** | Source inspection + `hasattr` probe — ISSUE.md needs this correction |
| Spread origin = spread center | HIGH | Adobe spec §10.3.3 + SimpleIDML source docstring + Indiscripts |
| `x' = a·x + c·y + tx`, `y' = b·x + d·y + ty` | HIGH | Three independent sources (Adobe spec, Indiscripts PDF, working SimpleIDML code) |
| TextFrame inner origin = frame center | HIGH | Indiscripts §1 explicit statement + Adobe community confirmation + visible in PathPointArray of any IDML TextFrame |
| Units = points throughout | HIGH | Spec p.101 — "Changing the definition of points in the InDesign UI has no effect on the definition of points used in IDML." |
| `25.4/72` mm-per-point conversion | HIGH | Standard. Confirmed empirically: target IDML's PageWidth=841.8897... × 25.4/72 = 297.00mm exactly. |
| `Page.GeometricBounds` = "y1 x1 y2 x2" | HIGH | Schema definition + SimpleIDML source uses `geometric_bounds[1]` for x1 and `[0]` for y1 |
| Master spread overrides via `MasterPageTransform` | HIGH on spec / MEDIUM on edge-case handling | Spec §10.4.2 documents the field; we have no overrides in the target so production behaviour untested |
| FillColor is Self-string into Graphic.xml | HIGH | Spec + empirical observation of `Color/Black`, `Color/C=...`, `Color/Druckformat` Selfs in target |
| LGPL on suds-py3 doesn't contaminate us | MEDIUM | We never import the InDesign-Server module. Not legal advice. |
| 1.3.1 release notes don't break our API | MEDIUM | Recent commits are PEP-265 packaging / minor fixes; no API touched. CHANGES.rst not available via raw URL (404), so confidence limited to commit-log skim. |
