# Codebase Research — Issue #10 (5 neue Vorlagen + Spec + Visual-QA)

**Researched:** 2026-05-07
**Scope:** All files under `tools/sla_lib/builder/`, `tools/`, `templates/`, `shared/`, `bin/`, `.github/workflows/` plus the three original SLAs at workspace root.

---

## 0. TL;DR for the planner

- **DSL is mature.** `Document`, `add_master`, `add_page` exist. `DocumentLayer` + `Document(layers=[...])` already supports per-document layer stacks (D4 needs **zero new mechanism**, just usage). `ImageFrame.inline_image_data` / `inline_image_ext` is a verbatim pass-through to SLA — D1 only needs an encoder helper.
- **Inline image data is non-trivial:** the value is base64( 4-byte BE length prefix + zlib(image_bytes) ). This is documented in `tools/sla_to_dsl.py` and exercised in `tools/sla_lib/tests/test_sla_diff.py:340-349`; **no helper currently exists in the builder package** to construct fresh inline images. Templates today only pass through bytes captured from the original SLAs by the converter.
- **Block library is small (5 evidence-driven blocks + 11 deprecated).** `WahlkreuzSymbol`, `FoldedPanel`, `DoorHangerCutout`, `TableTentFold`, `FoldLine`, `DieCut` are entirely new. None of the existing 5 blocks is generic enough to extend; `PageBackground.for_page` is the closest pattern to mimic (factory for page-aware blocks).
- **Spec format prior art exists** at `shared/template-spec.schema.yaml` + `docs/spec-input-schema.md`. **NOT a starting point** for the issue's Markdown-first spec format — the existing schema is YAML-only, no ASCII layout, doesn't cover Falz/Stanz/EPS-embedding. Decision D2 (Markdown + embedded YAML) supersedes it but should reference the YAML keys for consistency with `meta.yml`.
- **No Makefile.** `bin/render-gallery`, `bin/validate`, `bin/check-fontsizes`, `bin/check-stale-previews` are the canonical entry points. CI uses inline shell in `.github/workflows/pages.yml` rather than a make target.
- **No PIL/Pillow installed.** D7 composite grid should use ImageMagick `montage` (already used in `tools/visual_diff.py:188`).
- **No jsonschema installed.** Strict spec validation in CI requires `pip3 install jsonschema` (low cost).
- **Original SLAs have a single layer** (`Hintergrund` for postkarte/plakat, `Ebene 1` for zeitung). Templates currently emit one layer too via `Document(layers=[DocumentLayer(name='Hintergrund', ...)])`. Multi-layer (Falz/Stanz) is greenfield in this codebase.
- **EPS at workspace root**: `Wahl Kreuz im Kreis.eps` is 270 KB Adobe Illustrator, BoundingBox 0 0 84 91 (unit pt). Has a binary EPSF preview header before `%!PS-Adobe-3.1`.
- **Round-trip fidelity is sacred.** The bulk of `tools/sla_diff.py`, `_export_pdf.py`, the `_fmt_num` precision logic, the verbatim-pt-overrides on frames, and the entire xmp/PDF scrub pipeline exist solely to keep the three originals byte-equivalent. New templates must not destabilise this.

---

## 1. DSL Surface Summary

| Symbol | Source | Public via | Purpose |
|---|---|---|---|
| `Document` | `tools/sla_lib/builder/document.py:140` | `__init__.py:58` | Top-level SLA emitter |
| `Page` | `document.py:106` | `__init__.py:58` | Page object (mm coords, items list) |
| `Document.add_master` | `document.py:281` | method | Define MASTERPAGE |
| `Document.add_page` | `document.py:332` | method | Add doc PAGE |
| `Document.add_color` | `document.py:247` | method | Per-doc CMYK or RGB color, supports `spot=`, `register=` |
| `Document.add_para_style` | `document.py:265` | method | Register `ParaStyle` (per-doc) |
| `Document.add_char_style` | `document.py:269` | method | Register `CharStyle` (per-doc) |
| `Document(layers=[…])` | `document.py:148` | ctor kwarg | **Replaces** the brand layer stack with caller's `DocumentLayer` list (`document.py:881-896` emits them) |
| `Document(brand=…)` | `document.py:147,215` | ctor kwarg | Brand profile injection (auto-registers brand colors/styles/layers/defaults) |
| `Document(facing_pages=…)` | `document.py:149` | ctor kwarg | Spread layout (zeitung) |
| `Color` enum | `tools/sla_lib/builder/ci.py:140` | `__init__.py:57` | `BLACK`, `WHITE`, `REGISTRATION`, `DUNKELGRUEN`, `HELLGRUEN`, `GELB`, `MAGENTA` |
| `Style` enum | `ci.py:160` | `__init__.py:57` | `HEADLINE_ULTRA`, `HEADLINE_VOLLKORN`, `BODY_12`, `BODY_11`, `IMPRESSUM`, `STOERER`, `CTA` |
| `BrandColor` | `ci.py:30` | indirect | Dataclass: `name, cmyk, spot, register, role, rgb_native` |
| `BrandStyle` | `ci.py:58` | indirect | Dataclass mapping ci.yml `styles:` block |
| `BrandLayer` | `ci.py:71` | indirect | Default-stack layer (level/visible/printable/editable) |
| `Brand` | `tools/sla_lib/builder/brand.py:42` | `__init__.py:61` | Bundle of CI + 113 default doc-attrs + 34 default pdf-attrs |
| `Brand.gruene_noe()` | `brand.py:79` | classmethod | Loads `shared/ci.yml` + `shared/ci-defaults.yml` |
| `TextFrame` | `tools/sla_lib/builder/primitives.py:531` | `__init__.py:59` | PTYPE=4, columns, runs, default_style_attrs, link_to chain |
| `ImageFrame` | `primitives.py:741` | `__init__.py:59` | PTYPE=2, `src`/`image`, `inline_image_data`, `inline_image_ext`, `local_scale`, `local_offset_mm`, `scale_type`, `ratio` |
| `Polygon` | `primitives.py:824` | `__init__.py:59` | PTYPE=6, `shape='rectangle'\|'ellipse'`, `fill`, `line_color`, `custom_path`, `fill_shade`, `corner_radius_mm` |
| `Line` | `primitives.py:889` | `__init__.py:59` | **DEPRECATED** — emits `DeprecationWarning` on `to_pageobject()`. Use `Polygon(custom_path=..., line_color=..., fill='None')` instead |
| `Anchor` | `primitives.py:110` | `__init__.py:59` | `Anchor(h=..., v=..., margin_mm=...)`; legacy str/tuple via `Anchor.from_legacy()` (deprecated) |
| `Run` | `primitives.py:284` | `__init__.py:59` | Per-segment text formatting + separator + var |
| `ParaStyle` | `tools/sla_lib/builder/styles.py:32` | `__init__.py:60` | Full `<STYLE>` attribute surface (40+ optional fields) |
| `CharStyle` | `styles.py:95` | `__init__.py:60` | Full `<CHARSTYLE>` surface |
| `DocumentLayer` | `styles.py:17` | `__init__.py:60` | `name, visible, printable, editable, flow, transparent, blend, outline, layer_color` |
| `SoftShadow` | `styles.py:130` | `__init__.py:60` | Frame-level effect |
| `_Frame` (base) | `primitives.py:425` | indirect | Common attrs: `x_mm, y_mm, w_mm, h_mm, anchor, rotation_deg, layer, anname, custom_path, fill_rule, corner_radius_mm, soft_shadow, clip_edit, xpos_pt, ypos_pt, width_pt, height_pt` |
| `_Frame.layer` | `primitives.py:432` | int field | Default layer index — TextFrame=2, ImageFrame=1, Polygon=0 |
| `mm_to_pt` | `document.py:46` | indirect import | 1 mm × 72/25.4 |
| `MM_TO_PT` constant | `document.py:30` | indirect | 2.83464566929... |
| `ISO_SIZES_MM` | `document.py:34` | indirect | A0..A7 in portrait mm |

### Frame layer semantics
- `_Frame.layer` is the **integer index** (`LAYER` attr), 0-based, into the `LAYERS` list.
- The CI default stack is 4 layers: `Hintergrund (0)`, `Bilder (1)`, `Text (2)`, `Hilfslinien (3)` (`shared/ci.yml:124-128`).
- Templates currently emit a **single layer** (Hintergrund) and put everything on `layer=0` — this is by round-trip choice (originals each have one layer). New templates can declare more.
- For D4 (Falz/Stanz on dedicated layers), the planner adds two new layers via `Document(layers=[…])` and references them by integer index on each `Polygon`/`FoldLine`/`DieCut` block.

---

## 2. Block Library Inventory (`tools/sla_lib/builder/blocks.py`)

| Class | LoC | Category | Description | Reuse value |
|---|---|---|---|---|
| `PageNumber` | `blocks.py:46-108` | composition | TextFrame with `<var name='pgno'/>` Run; trivial passthroughs for clip_edit, line_width_pt, col_gap_mm, var_attrs | LOW for new templates (zeitung-specific) |
| `Impressum` | `blocks.py:117-151` | composition | TextFrame with `trail_style='Impressum'` | HIGH — every new template likely needs it |
| `PageBackground` | `blocks.py:161-232` | composition | Full-bleed Polygon at layer 0 fill=Dunkelgrün | HIGH — wahlaufruf, plakat-style backgrounds |
| `PageBackground.for_page(w_mm, h_mm)` | `blocks.py:215-232` | factory | Returns `_SizedPageBackground` with exact page dimensions | **Pattern to copy** for any block that needs page-aware sizing |
| `_SizedPageBackground` | `blocks.py:236-259` | internal | Concrete sized Polygon emitter | — |
| `ContactBlock` | `blocks.py:268-317` | composition | TextFrame with `trail_style='Kontaktmöglichkeiten'`, multi-Run | MEDIUM — wahlaufruf-postkarte uses social handles |
| `ColumnTextStory` | `blocks.py:326-361` | composition | Linked TextFrame chain with `link_to()` | MEDIUM — falzflyer, plakat A3 long body |
| `legacy.Headline4Line` | `blocks.py:401-418` | deprecated | 4-zeilige Headline mit Wechselfarbe | Pattern to **port** for new templates (issue #10 should write own variant) |
| `legacy.StoererBadge` | `blocks.py:420-435` | deprecated | Magenta-Kreis + 3-Run-Text rotated | Pattern reference |
| `legacy.ImpressumLine`, `legacy.ImpressumBlock` | `blocks.py:437-463` | deprecated | Inline 1-zeilig / Block-Variante des Impressums | superseded by `Impressum` |
| `legacy.SocialHandlesVertical` | `blocks.py:465-478` | deprecated | superseded by `ContactBlock` |
| `legacy.LogoCorner` | `blocks.py:480-494` | deprecated | **NOT a real image-embed wrapper** — references `shared/logos/gruene-weiss.png` via `src=` (PFILE, not inline). No callers wire to actual files; no real templates use it. |
| `legacy.EventDetails` | `blocks.py:496-517` | deprecated | 2- or 1-Spalten Datum/Zeit/Ort | Pattern for plakat A3 event |
| `legacy.Masthead` | `blocks.py:519-532` | deprecated | Zeitungsname + Ausgabe |
| `legacy.ContentTeasers` | `blocks.py:534-552` | deprecated | 3 Spalten Headline+Body |
| `legacy.ArticleHeadline`, `legacy.ArticleBody`, `legacy.QuoteSidebar` | `blocks.py:554-596` | deprecated | Zeitung-Artikel-Bausteine |

**All legacy blocks emit `DeprecationWarning`** on `emit()`. Only `_smoke/` templates use them; production builds (postkarte/plakat/zeitung) reference them zero times. Deprecation cycle ends in next major DSL revision (issue #9).

**Pattern for new blocks:**
```python
@dataclass
class WahlkreuzSymbol:
    """One-liner."""
    # Public fields with defaults
    x_mm: float = 0
    y_mm: float = 0
    diameter_mm: float = 30
    # ... block-specific fields
    layer: int = 1
    anname: str = "Wahlkreuz"

    def emit(self) -> Iterable:
        # yield one or more primitive instances
        yield ImageFrame(x_mm=..., y_mm=..., ...)
```

`Page.add(item)` (`document.py:124-134`) calls `item.emit()` if present and unrolls primitives into `page.items`. Blocks therefore compose freely.

---

## 3. Existing Image-Embed Mechanics

### 3.1. Inline image storage: qCompress wrapper

The `ImageData` attribute on a `<PAGEOBJECT PTYPE="2" isInlineImage="1" …>` is documented at `tools/sla_to_dsl.py:202-216`:

> base64-encoded **qCompress payload**: 4-byte big-endian uncompressed-length prefix + `zlib`-compressed stream around the original PNG/JPEG bytes.

**The DSL stores this verbatim and never decodes/re-encodes** (`primitives.py:756-764`):

```python
inline_image_data: Optional[str] = None
inline_image_ext: Optional[str] = None  # e.g. "png", "jpg"
```

Emission (`primitives.py:798-808`):
```python
if is_inline:
    attrs["Pagenumber"] = "0"
    attrs["isInlineImage"] = "1"
    attrs["inlineImageExt"] = self.inline_image_ext or "png"
    attrs["ImageData"] = self.inline_image_data
    attrs["EMBEDDED"] = "0"
```

### 3.2. Real example from `templates/postkarte-a6-kampagne/build.py:96-118`

```python
page0.add(ImageFrame(
    x_mm=42.18263536891868,
    y_mm=89.39182357288504,
    w_mm=20.545843114650424,
    h_mm=20.90539536915682,
    layer=0,
    xpos_pt=219.573824667801,        # verbatim pt override (round-trip)
    ypos_pt=273.395145560934,
    width_pt=58.2401852068831,
    height_pt=59.2593884480036,
    inline_image_ext='png',
    image='',                         # PFILE empty for inline
    scale_type=0,
    line_width_pt=1,
    local_scale=(0.0485334876724026, 0.0485334876724026),
    inline_image_data='AAEI4HicVLsJOJTtGzd8z9jXkiyVJQpl7B4lu4pKoTDGNkwJZR3Z9yFLpeiphshWQg…',  # truncated
))
```

### 3.3. Production usage stats

| Template | inline ImageFrames | inline_image_ext values |
|---|---|---|
| postkarte-a6-kampagne | 7 | `png` only |
| plakat-a1-hochformat | 2 | `png` only |
| zeitung-a4-grun | 6 | `png` only |
| **All production** | **15** | **`png` only** |
| **All originals** | **15** | **`png` only** |

**No template currently uses `inline_image_ext='pdf'` or `'eps'`.** This is a green-field path for D1.

### 3.4. Constructing a fresh inline image (for D1 EPS→PDF embedding)

Since the builder ships **no helper to encode raw bytes into the qCompress base64 form**, the issue must add one. The reference encoder lives in the test suite (`tools/sla_lib/tests/test_sla_diff.py:340-349`):

```python
import zlib
from base64 import b64encode

def encode_inline_image(image_bytes: bytes) -> str:
    """Wrap raw bytes in qCompress format and base64-encode for SLA emission."""
    compressed = zlib.compress(image_bytes, 9)
    qcompressed = len(image_bytes).to_bytes(4, "big") + compressed
    return b64encode(qcompressed).decode("ascii")
```

Recommended placement: **add to `tools/sla_lib/builder/primitives.py`** as a module-level helper next to `ImageFrame`, OR a new utility module `tools/sla_lib/builder/inline_image.py` if generalising. Plan should pick one; my recommendation is **`primitives.py` module-level function `pack_inline_image(data: bytes, ext: str) -> tuple[str, str]`** returning `(base64_qcompressed, ext)` for symmetric use.

### 3.5. Whether Scribus accepts `inlineImageExt="pdf"`

**External evidence confirms YES.** Scribus 1.6 imports PDF files as image-frame content natively (`Content > Get Image` accepts `.pdf` and `.eps`). The blog post jfml-blog/2024-01-03 explicitly documents this — vector content stays vector through PDF export when "Embed PDF & EPS files" is enabled.

**MEDIUM-confidence caveat** (no in-codebase test exercises this): the qCompress wrapper around `pdf` bytes is the same envelope, and `inlineImageExt="pdf"` is the documented canonical extension for PDF inline images in Scribus. The image-embedder GitHub project (`Afueth/scribus-image-embedder`) confirms the wrapping is identical for any binary content; Scribus sniffs the extension to dispatch the renderer (libpoppler for PDF). The risk is **render quality** (Ghostscript-rendered PDF inside Scribus may rasterise at preview resolution), not embedding mechanics.

**Fallback path if `inlineImageExt='pdf'` proves unreliable:** convert PDF to high-res PNG (`pdftoppm -r 600 -png -singlefile`) and embed PNG. This loses vector fidelity but matches the proven path.

---

## 4. Layer Support Status — D4 readiness

### 4.1. DSL has full layer support

`DocumentLayer` (`styles.py:17-29`) maps every `<LAYERS>` attribute the SLA schema accepts:

```python
@dataclass(frozen=True)
class DocumentLayer:
    name: str
    visible: bool = True
    printable: bool = True
    editable: bool = True
    flow: bool = True              # FLOW (text wraps around items on this layer)
    transparent: float = 1.0       # TRANS (opacity 0..1)
    blend: int = 0                 # BLEND (mode index)
    outline: bool = False          # OUTL (outline-only render in editor)
    layer_color: str = "#000000"   # LAYERC (editor highlight color)
```

`Document(layers=[…])` (`document.py:148, 201`) overrides the CI default stack, and `_emit_layers` (`document.py:878-910`) writes each `DocumentLayer` into `<LAYERS NUMMER=… LEVEL=… NAME=… SICHTBAR=… DRUCKEN=… EDIT=… SELECT=1 FLOW=… TRANS=… BLEND=… OUTL=… LAYERC=…/>` with bottom-up index ordering.

### 4.2. What D4 needs

**Only usage, no DSL extension.** A template's build.py for the Türanhänger would write:

```python
doc = Document(
    brand=Brand.gruene_noe(),
    layers=[
        DocumentLayer(name="Hintergrund", printable=True),  # 0
        DocumentLayer(name="Inhalt",      printable=True),  # 1
        DocumentLayer(name="Stanzkontur", printable=False), # 2  — D4
        DocumentLayer(name="Falz",        printable=False), # 3  — D4
    ],
    template_id="wahltag-tueranhaenger",
    # …
)
```

Then any frame on the stanze layer:
```python
page0.add(Polygon(
    x_mm=…, y_mm=…, w_mm=…, h_mm=…,
    custom_path="M…",        # die-cut shape
    fill="None",
    line_color="Stanzkontur",
    line_width_pt=0.5,
    layer=2,                   # int index into the layers= list above
    anname="Stanzkontur Außenkontur",
))
```

The plan-time work for `FoldLine` and `DieCut` is a thin wrapper that defaults `fill='None'`, picks the right layer index, and offers ergonomic mm-coords for the path.

### 4.3. Spot-color drift via `check_ci.py`

`tools/check_ci.py:117-145` flags any color in the SLA not in `shared/ci.yml`. Adding `Falz` and `Stanzkontur` as `spot: true` colors in `shared/ci.yml` → both validator and brand layer pick them up automatically. **No `ci_overrides` shenanigans needed** if they're in `ci.yml`.

`Brand.gruene_noe()` reads `ci.yml` (`brand.py:96`) and auto-registers them when `Document(brand=…)` is called.

---

## 5. Scribus SLA Layer Schema (verified from originals)

All three originals use a single layer:

```xml
<LAYERS NUMMER="0" LEVEL="0" NAME="Hintergrund"
        SICHTBAR="1" DRUCKEN="1" EDIT="1" SELECT="0"
        FLOW="1" TRANS="1" BLEND="0" OUTL="0" LAYERC="#000000"/>
```

(Postkarte and Plakat use `NAME="Hintergrund"`; Zeitung uses `NAME="Ebene 1"`.)

| Attr | DSL field | Type | Meaning |
|---|---|---|---|
| `NUMMER` | (auto from list index) | int | Layer number (Scribus uses both NUMMER and LEVEL identically; index in layer list) |
| `LEVEL` | (auto from list index) | int | Render order (low → bottom) |
| `NAME` | `DocumentLayer.name` | str | Display name |
| `SICHTBAR` | `DocumentLayer.visible` | 0/1 | Visible in editor |
| `DRUCKEN` | `DocumentLayer.printable` | 0/1 | **Included in PDF/print export** ← key for D4: Falz/Stanz layers set to `0` |
| `EDIT` | `DocumentLayer.editable` | 0/1 | Editor allows changes |
| `SELECT` | (DSL hardcodes `1`) | 0/1 | Selectable in editor |
| `FLOW` | `DocumentLayer.flow` | 0/1 | Text frames on lower layers wrap around items on this layer |
| `TRANS` | `DocumentLayer.transparent` | float | Layer opacity (0..1) |
| `BLEND` | `DocumentLayer.blend` | int | Blend mode index (0=Normal) |
| `OUTL` | `DocumentLayer.outline` | 0/1 | Outline-only in editor |
| `LAYERC` | `DocumentLayer.layer_color` | `#rrggbb` | Editor highlight color (the colored bar in the Layers panel) |

Per-frame layer reference is `LAYER="<int>"` on `<PAGEOBJECT>` — frames bind to layer **by index**, not name. The DSL emits this from `_Frame.layer`. Once layers are ordered as a list (via `Document(layers=[…])`), the index is stable.

### Spot-color binding

`<COLOR NAME="Stanzkontur" SPACE="CMYK" C="0" M="100" Y="0" K="0" Spot="1"/>` is the canonical emission (`document.py:684-703`). The DSL already supports `spot=true` (`ci.py:36`) and the `_emit_colors` method honours it (`document.py:701`).

When a frame has `line_color="Stanzkontur"` (or `fill="Stanzkontur"`), Scribus binds the spot channel correctly even on a non-printable layer; the printer's PDF/X-4 export pulls the spot pathway out separately.

---

## 6. Render / Validation Pipeline (flow)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. AUTHORING                                                            │
│    templates/<id>/build.py  ──► python3 build.py ──► template.sla       │
│         (uses sla_lib.builder DSL)                                      │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. STRUCTURAL VALIDATION                                                │
│    tools/check_ci.py template.sla                                       │
│         scans <COLOR>, <STYLE>; warns on extras, criticals on missing   │
│         brand-primary or wrong CMYK values                              │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. ROUND-TRIP DIFF (only for templates with original_sla in meta.yml)   │
│    tools/sla_diff.py  --left <original>  --right template.sla  --strict │
│         10-step normalisation: volatile attrs, ItemID renumber, page-   │
│         local coords, float rounding, attribute sort. Three severity    │
│         levels (critical/warning/info). 1249 LOC.                       │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. PDF RENDER                                                           │
│    xvfb-run scribus -g -ns -py tools/_export_pdf.py template.sla …pdf   │
│         _export_pdf.py is 7 lines: openDoc + PDFfile + save             │
│    + tools/render_pipeline.py:_scrub_pdf_metadata to make it byte-      │
│      idempotent (epoch dates, fixed UUIDs, canonical XMP order)         │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. PNG RASTERISE                                                        │
│    pdftoppm -r <dpi> -png preview.pdf  page                             │
│         tools/render_pipeline.py:_zero_pad_pngs renames page-N → 0N     │
│         Default DPI from meta.yml::preview_dpi (postkarte=100, others   │
│         use 50 default)                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. VISUAL DIFF (vs baseline.pdf)                                        │
│    tools/visual_diff.py --tolerance diff.yml --dpi 96 --out build/<id>/ │
│         per-page ImageMagick `compare -metric AE -fuzz 25%` + montage   │
│         composite (baseline | dsl | delta), HTML report, JSON summary   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. GALLERY PUBLISH                                                      │
│    tools/gallery_build.py  copies template.sla, preview.pdf, page-*.png │
│         to site/public/templates/<id>/ and writes site/src/content/     │
│         templates/<id>.md with frontmatter from meta.yml +              │
│         _downloads/_previews keys + embedded README.md                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 8. CI (GitHub Actions, .github/workflows/pages.yml)                     │
│    Install Scribus 1.6.5 AppImage → run all build.py → gallery_build →  │
│    Astro build → unittest discover → sla_diff --strict for the three    │
│    templates → check_ci.py per SLA → upload-pages-artifact → deploy     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key entry points
- `bin/render-gallery` (Python shim → `tools/render_pipeline.py:main`) — local rebuild + validation; writes to `site/public/`
- `bin/validate` (bash) — sla_diff + visual_diff for every template with `original_sla:` (but not new templates without one)
- CI (`.github/workflows/pages.yml`) — runs templates' build.py individually, no `bin/render-gallery` invocation; instead inline `python3 tools/sla_diff.py … --strict --allow-brand-extras` for the three round-trip templates. This loop **does not include new templates** unless they have `original_sla:` set.

### DPI handling
- `tools/render.py:48-67` (lower-level) and `tools/visual_diff.py:112-143` (pipeline) both invoke `xvfb-run -a --server-args="-screen 0 1024x768x24" scribus -g -ns -py tools/_export_pdf.py`.
- Scribus's PDF export DPI is set inside `_export_pdf.py` (currently uses default — Scribus's default is 300 dpi for raster; vector stays vector regardless).
- Rasterisation DPI is set on the **pdftoppm** call in `tools/render_pipeline.py:DEFAULT_DPI=50` and per-template via `meta.yml::preview_dpi` (`render_pipeline.py:439`).
- D7 200 DPI: bump `meta.yml::preview_dpi: 200` for new templates and add a CLI flag in the new `tools/visual_review.py` to pass through.

---

## 7. Existing Smoke Test Pattern

Located under `templates/_smoke/<id>/{build.py, template.sla}`. Two examples:

### `templates/_smoke/postcard-a6/build.py` (39 LoC)
Self-contained: imports `Document, Color, Polygon, blocks` from `sla_lib.builder`, calls `Document.add_page(size="A6", …)`, uses `blocks.legacy.Headline4Line`, `blocks.legacy.StoererBadge`, `blocks.legacy.ImpressumLine`. Saves to `template.sla` next to itself.

Entry-point pattern:
```python
def build(out_path: Path) -> None:
    doc = Document(title="Postkarte A6 (smoke)", template_id="smoke-postcard-a6")
    page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3, margins_mm=(8,8,8,8))
    page.add(Polygon(...))
    page.add(blocks.legacy.Headline4Line(...))
    doc.save(out_path)

if __name__ == "__main__":
    build(Path(__file__).parent / "template.sla")
```

### `templates/_smoke/zeitung-mini/build.py` (60 LoC)
Multi-page + multi-master demonstration. Uses 4 pages, 2 masters, mixes `blocks.legacy.Masthead`, `Headline4Line`, `ContentTeasers`, `ArticleHeadline`, `ArticleBody`, `ImpressumBlock`. Sets `label="Beispiel: …"` on each page so the `Hilfslinien` layer guide shows the variant name.

### How smoke tests are run
- CI: `for build in templates/_smoke/*/build.py templates/*/build.py; do python3 "$build"; done` (`.github/workflows/pages.yml:69-71`)
- That's it — there's **no per-page assertion logic** in the smoke tests. They serve as compile-tests (does the DSL emit valid XML?) and as exemplars.
- `tools/sla_lib/tests/test_blocks.py` and `tools/sla_lib/tests/test_multipage.py` cover behavioural assertions.

### What "Smoke" means in this codebase
- **Build-success only** — does `python3 build.py` complete without raising and write a parseable SLA?
- The CI job catches schema-level breakage (XML well-formedness, type signatures).
- C1 in the issue ("Layout-Brüche werden erkannt: überlappende Frames, leerer Slot, Text außerhalb Trim") **goes beyond** today's smoke test concept — it's a new layer of structural-checking that needs a new tool. Plan must build it; can live as `tests/visual/` or as a checking module under `tools/`.

### What a C1 smoke test would assert (suggested layer)
1. Frames don't overlap on the same layer (parse `<PAGEOBJECT>` rectangles, intersection > 0 % is a flag).
2. No frame extends beyond `(trim_w + bleed, trim_h + bleed)`.
3. Every slot named in `meta.yml::slots` is present as a frame with matching `ANNAME`.
4. Text frames have non-empty `runs` or `text` (no orphan empty TextFrames).

This is **not present in the codebase today.** The plan needs a new tool, e.g. `tools/check_layout.py`.

---

## 8. Multi-Model Tooling Survey

### 8.1. Existing review scripts
**None** in the workspace. `tools/visual_diff.py` is pixel-comparison only (no LLM). No `tools/visual_review.py`, no `review_*.py`, no `gallery_compare.py`.

### 8.2. Codex CLI (verified by `codex --help`, `codex exec --help`)

Binary: `/root/.npm-global/bin/codex` (verified present).

**Image attachment is a first-class flag:**
```
codex exec [OPTIONS] [PROMPT]
  -i, --image <FILE>...
          Optional image(s) to attach to the initial prompt
  -m, --model <MODEL>
          Model the agent should use
  -o, --output-last-message <FILE>
          Specifies file where the last message from the agent should be written
  --output-schema <FILE>
          Path to a JSON Schema file describing the model's final response shape
```

**Recommended invocation form for visual review:**
```bash
codex exec \
  --image preview.png \
  --image side-by-side-grid.png \
  --output-last-message reviews/visual-qa-<slug>-codex.md \
  --output-schema tools/visual_review/response.schema.json \
  -m gpt-5.4 \
  "$(cat tools/visual_review/prompt_template.md)"
```

The prompt comes via the trailing positional or stdin (`codex exec` reads stdin if `-` is used).

### 8.3. Gemini CLI (verified by `gemini --help`)

Binary: `/root/.npm-global/bin/gemini` (verified present).

**No `--image` flag.** Gemini CLI takes a prompt via `-p/--prompt` and additional context via `--include-directories`. To pass image input non-interactively, the path is to **place the image in a directory and reference it from the prompt** — Gemini will read it via filesystem tools, OR the prompt is structured as multimodal via the SDK rather than CLI.

**Verified flags relevant for review use:**
```
-p, --prompt                  Run in non-interactive mode with the given prompt
-m, --model                   Model
-o, --output-format           text|json|stream-json
--include-directories         Additional directories to include in the workspace
--allowed-tools               Tools that are allowed to run without confirmation (deprecated)
--yolo                        Auto-approve all actions
--approval-mode               default|auto_edit|yolo|plan
```

**Recommended invocation form:**
```bash
gemini \
  --include-directories reviews/visual-qa-input/<slug>/ \
  --output-format json \
  --yolo \
  --prompt "$(cat tools/visual_review/prompt_template.md)" \
  > reviews/visual-qa-<slug>-gemini.json
```

The prompt template must explicitly reference the image filenames in the included directory (Gemini will read them as files via its built-in tools).

**LOW-confidence**: alternative — invoke Gemini via the `google-generativeai` Python SDK directly with multimodal content blocks. Cost: extra dep but cleaner image handling. **Recommendation: start with CLI form for parity with codex, fall back to SDK if image grounding is unreliable.**

### 8.4. Claude Vision

Two routes:
- **In-session (the same Claude executing the review pipeline)** uses its native `Read` tool to view PNG files and reason on them. Simplest path; no extra plumbing.
- **Anthropic API** via Python SDK if a parallel/independent Claude is desired: `anthropic-sdk-python`, multimodal content with `image/png` source type. Requires `ANTHROPIC_API_KEY` env var.

### 8.5. Recommended `tools/visual_review.py` shape

```python
# tools/visual_review.py — orchestrator (issue C2)
def run_review(template_slug: str, png_paths: list[Path], grid_png: Path,
               iter_id: int) -> dict:
    """Run all three models, collect structured findings, write report."""
    prompt = (HERE / "visual_review" / "prompt_template.md").read_text()
    schema = HERE / "visual_review" / "response.schema.json"
    out = REVIEWS / f"visual-qa-{template_slug}.md"

    findings = {}
    findings["claude"] = _claude_review(png_paths, grid_png, prompt)         # native Read or SDK
    findings["codex"] = _codex_review(png_paths, grid_png, prompt, schema)   # subprocess
    findings["gemini"] = _gemini_review(png_paths, grid_png, prompt)         # subprocess

    consensus = _build_consensus(findings)  # 3/3 yes per D6
    _write_report(out, template_slug, iter_id, findings, consensus)
    return consensus
```

The existing reference for orchestrator-style multi-model is `/issue:review` skill (mentioned in MEMORY.md but the skill source is **not in this workspace** — exists in Claude Code's plugin system, not loadable from the repo). Plan should treat the visual_review as **independent script**, not a skill extension.

---

## 9. Reusability Opportunities

### 9.1. Reuse without modification
- `Document(brand=Brand.gruene_noe())` → all 5 new templates plug in identically; no new ci.yml entries except the two spot colors (`Falz`, `Stanzkontur`).
- `Impressum` block (`blocks.py:117`) → all 5 new templates (legal requirement; postkarte/zeitung pattern fits).
- `PageBackground.for_page(w, h, color=…)` → wahlaufruf-postkarte, falzflyer panels, türanhänger.
- `ContactBlock` (`blocks.py:268`) → wahlaufruf-postkarte (back side) and possibly tent-card.
- `ColumnTextStory` (`blocks.py:326`) → falzflyer narrative panel chains; themen-plakat A3 long body.
- `Document.add_color(name, cmyk=…, spot=True, register=False)` (`document.py:247`) → already supports `spot=True`; D4's Falz/Stanzkontur land here if not added to ci.yml. **Recommendation: put them in ci.yml**, not as per-template doc-local colors, so check_ci.py validates them and other templates can adopt.
- `DocumentLayer(name=…, printable=False)` → D4 Falz/Stanz layers (no new code needed).
- `Polygon(custom_path="M…", line_color="Stanzkontur", fill="None")` → `DieCut` block built directly on existing `Polygon`. The path string is the only new logic.

### 9.2. Reuse with extension
- `legacy.Headline4Line` (deprecated) → port the alternating-color-runs pattern into a non-deprecated `HeadlineMultiline` block when needed by wahlaufruf/themen-plakat. The legacy version uses `(text, dict, sep)` tuple Run form that emits `DeprecationWarning`; a fresh implementation should use `Run(text=…, fcolor=…, separator=…, paragraph_style=…)` which **suppresses the warning**.
- `legacy.EventDetails` → wahlaufruf-postkarte election details; same comment about Run modernisation.
- Existing `_export_pdf.py` (7 LoC) → reuse as-is; new `tools/visual_review.py` invokes it the same way.

### 9.3. Build-from-scratch (no precedent in codebase)
- **EPS→PDF conversion script** (D1, D10): no helper exists. Add `tools/eps_to_pdf.py` (or build-time hook in template build.py) using `gs -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite`. Output to `shared/assets/derived/wahlkreuz-kreis.pdf`, committed for determinism (D10).
- **Inline-image qCompress encoder helper** (`pack_inline_image(bytes, ext)`): not in builder; exists only in test fixtures. Add to `tools/sla_lib/builder/primitives.py` or new module.
- **Spec-Markdown parser** (`tools/spec_parse.py`): extract YAML fenced block from Markdown for D2's spec format. ~30 LoC.
- **Spec drift checker** (`tools/spec_check.py`, D3): compare spec slots ↔ `meta.yml` slots ↔ frame anames in SLA. ~80 LoC.
- **Layout smoke checker** (`tools/check_layout.py`, C1): overlap, out-of-bounds, missing-slot detection. ~150 LoC.
- **Visual review orchestrator** (`tools/visual_review.py`, C2): three-model fan-out, consensus, report. ~250 LoC.
- **Composite grid generator** (D7): use ImageMagick `montage … -tile 4x2 -geometry +8+8 -label '%t' …` (already used in visual_diff.py:191). ~50 LoC including labels.

### 9.4. Block API conventions to follow

From `tools/sla_lib/builder/blocks.py`:
1. `@dataclass` with public fields + sensible defaults.
2. Public fields named in mm/pt the way the SLA stores them (`x_mm`, `w_mm`, `line_width_pt`).
3. `layer: int = N` defaulting to the layer typical for the block class (Polygon=0, Image=1, Text=2).
4. `anname: str = "..."` — every block sets a default `ANNAME` so the frame is identifiable in Scribus's Object Properties panel.
5. `def emit(self) -> Iterable:` yields one or more primitive instances.
6. **No DocumentLayer or Document mutation in `emit()`.** Blocks emit primitives only; the page accumulates them.
7. Header docstring **must** include corpus citation (`# Corpus: templates/<id>/build.py:<line> …`) — this convention came from issue #5 and is enforced by review.

---

## 10. Gotchas Already Visible in Code

### 10.1. `Line` is deprecated
`primitives.py:889-951` — `Line.to_pageobject()` raises `DeprecationWarning`. SLA round-trip emits `Polygon(custom_path=..., line_color=..., fill='None')` instead because Scribus stores PTYPE=5 as a polygon-with-tiny-path frame. **`FoldLine` should NOT subclass or use `Line`**; it must use `Polygon` with a 2-point custom path.

### 10.2. `inline_image_data` is verbatim, not raw
See §3.4 above. Templates can't pass raw PNG bytes — they need the qCompress wrapper.

### 10.3. `text_align` is deprecated alias for `vertical_text_align`
`primitives.py:543, 574` — `TextFrame(text_align=…)` emits `DeprecationWarning`. Use `vertical_text_align=` (0=top, 1=center, 2=bottom). Existing zeitung build.py uses both; new templates must use `vertical_text_align`.

### 10.4. `Run` tuple form `(text, dict, sep)` is deprecated
`primitives.py:391-415` — emits `DeprecationWarning` outside `_internal=True`. New templates must use `Run(text=…, fcolor=…, separator=…)`.

### 10.5. `Anchor` legacy string form is deprecated
`primitives.py:140-156` — `Anchor.from_legacy("bottom-20")` emits warning. Use `Anchor(v="bottom", margin_mm=20)`.

### 10.6. `palette_replaces_ci=True` gate on per-doc styles
`document.py:732-755` — when `Brand` is supplied, `palette_replaces_ci` is forced True. CI styles flow through brand auto-registration; **per-doc `add_para_style` is additive on top**. Per-doc names matching CI names override (last-write-wins per `dict.update`).

### 10.7. `default_style_attrs` vs `style` ambiguity warning
`primitives.py:587-596` — setting both `style="ci/headline-ultra"` and `default_style_attrs={"FONT": ...}` on a TextFrame emits `UserWarning`. New templates should pick one.

### 10.8. ScratchTop/ScratchLeft/page_xpos_pt round-trip subtleties
`document.py:277-279, 332-404` — auto-computed scratch offsets nearly always need to be **manually overridden** via `page_xpos_pt=` / `page_ypos_pt=` for round-trip stability. New templates that don't round-trip can rely on the auto path (offset = SCRATCH_LEFT + page index × (h + GAP_VERTICAL)). All five new templates **should not need pixel-precise overrides** since they have no original to diff against.

### 10.9. `clip_edit=True` auto-generates a rect path
`primitives.py:637-642` — TextFrames with `clip_edit=True` and no `custom_path` automatically get FRTYPE=3 with the canonical rectangle clip path. This is round-trip-only behaviour; new templates can leave `clip_edit=False`.

### 10.10. `bleed_mm` precision drift on round-trip
Originals carry `bleed_mm=3.0000000000000013` due to float rounding when Scribus persists. New templates should use plain `bleed_mm=3.0` (or `=3`); only round-trip targets need the multi-digit form.

### 10.11. `add_master(name="Normal")` is auto-injected
`document.py:476-487` — if no master is declared, a `"Normal"` master is auto-created. Templates that declare any master skip this. Wahlaufruf-Postkarte (2 pages, no master needed) can let auto-injection handle it.

### 10.12. Postkarte-style 2-page: pages share master
`templates/postkarte-a6-kampagne/build.py:62-82` — both pages reference the same auto-injected master. Wahlaufruf-Postkarte should mirror this.

### 10.13. Zeitung's "facing pages" mechanism
`document.py:366-391` — `facing_pages=True` triggers PageSets="Facing Pages", per-page side determined by index parity (page 0 right, odd → left, even>0 → right). For falzflyer (3-fold), this is **not the right mechanism**: it's a single landscape page (297×210mm A4 quer), with 3 panels visually delimited by Falz lines. The Falz lines are vector paths on a `Falz` layer (D4); panels are not separate "pages" in the SLA sense.

### 10.14. ImageData encoding is platform-dependent on read-back
`tools/sla_to_dsl.py:9-19` (the verbatim-rather-than-decode-reencode rationale): qCompress wraps zlib, and zlib parameters on encode-then-decode-then-re-encode are not byte-stable across machines. The DSL's verbatim policy works here because the bytes never leave round-trip path. **For D1's freshly-encoded Wahlkreuz PDF, the encoder will write platform-specific bytes** — but that's fine because all five new templates encode the same input deterministically on the same Ghostscript+Python version, and the result is committed to git per D10.

### 10.15. Smoke templates use `blocks.legacy.*`
`templates/_smoke/postcard-a6/build.py:21-31` — these still use deprecated blocks. Don't import patterns from there for new production templates.

### 10.16. `meta.yml::ci_overrides::non_ci_styles` is a manual-list
`tools/check_ci.py` doesn't read `ci_overrides`. Plain extra styles pass as `warning` severity (not `critical`) — `check_ci.py:181-191`. The `ci_overrides` block in meta.yml is **documentation only**; it's enumerated by humans for context, not validated by tooling. New templates that introduce template-local styles should still list them there for reviewers.

### 10.17. `gallery_build.py` fails if PNGs are missing
`tools/gallery_build.py:36-45` — exits with FATAL if `template.sla`, `preview.pdf`, or `page-*.png` aren't present. The CI workflow runs `tools/gallery_build.py` after running each `build.py`, but **does NOT render PDFs/PNGs in CI** — instead it relies on locally-rendered artifacts being committed (per `docs/render-fidelity.md` "Local-only rendering"). New templates **must commit `template.sla`, `preview.pdf`, `page-*.png`** to make `gallery_build` happy. This is a real workflow constraint: new template PRs won't pass CI without locally rendering and committing artifacts.

### 10.18. `bin/check-stale-previews` enforces hash freshness
`tools/check_stale_previews.py` (151 LOC) computes SHA256 of `template.sla` and compares against `meta.yml::previews_for_sla`. If they diverge, CI fails with "previews are stale". Workflow: after editing build.py, run `bin/render-gallery <id>` locally — it updates the hash and re-renders PNGs in one shot.

### 10.19. New templates with no `original_sla` skip round-trip diff
The five new templates have no original to round-trip against. `bin/validate` (`bin/validate:42-46`) skips templates without `original_sla:` in meta.yml. The CI workflow's sla_diff loop (`pages.yml:100-119`) **enumerates the three known templates explicitly** — so it's not "skip if missing", it's "diff only the three named". New templates fall outside this loop entirely. **No regression risk** to round-trip.

### 10.20. CMYK→RGB heuristic in CI is naive
`ci.py:19-26` (`_cmyk_to_rgb`) is a stub for non-color-managed display only; real PDF export goes through Scribus's ICC pipeline (`hcms=True` in templates). Spot-color rendering (Falz/Stanzkontur) bypasses CMYK conversion entirely — Scribus emits the spot pathway directly to the printer's plate. `check_ci.py` only validates CMYK% values match ci.yml; it doesn't render-check.

---

## 11. `<interfaces>` blocks for the 6 new blocks

These are **proposed** signatures matching the convention in §9.4. Plan should refine.

```python
# From tools/sla_lib/builder/blocks.py — proposed additions for issue #10

# ---------------------------------------------------------------------------
# Block: WahlkreuzSymbol
# Used by: wahlaufruf-postkarte-a6-quer (hero), kandidat-falzflyer-din-lang
#          (closer panel), wahltag-tueranhaenger (hero)
# Embeds: shared/assets/derived/wahlkreuz-kreis.pdf via inline_image_data
# ---------------------------------------------------------------------------
@dataclass
class WahlkreuzSymbol:
    """Adobe-Illustrator Wahlkreuz im Kreis embedded as inline PDF.

    Loads shared/assets/derived/wahlkreuz-kreis.pdf at construction time,
    base64-qCompress-wraps it, and emits an ImageFrame with vector content
    preserved through Scribus PDF export (per Decision D1).

    Aspect ratio of the EPS: 84:91 (BoundingBox 0 0 84 91). Width is the
    primary control; height is computed from aspect-ratio lock unless
    explicitly overridden.
    """
    x_mm: float = 0
    y_mm: float = 0
    width_mm: float = 30                 # diameter-equivalent (long edge)
    aspect_ratio: float = 84/91          # default from EPS BoundingBox
    height_mm: Optional[float] = None    # if None, computed from width/aspect
    rotation_deg: float = 0
    layer: int = 1                       # default Bilder layer
    anname: str = "Wahlkreuz im Kreis"
    pdf_path: Optional[Path] = None      # default: shared/assets/derived/wahlkreuz-kreis.pdf

    def emit(self) -> Iterable: ...      # yields ImageFrame with packed inline data


# ---------------------------------------------------------------------------
# Block: FoldLine
# Used by: kandidat-falzflyer-din-lang (2 vertical fold lines),
#          infostand-tent-card-a5-quer (1 horizontal fold line)
# Renders as: Polygon with custom_path 2-point line, line_color="Falz",
#             fill="None", on layer "Falz" (printable=False)
# ---------------------------------------------------------------------------
@dataclass
class FoldLine:
    """Strichlierte Falz-Linie als Polygon mit Spot-Color-Stroke.

    Emits a 2-point Polygon with custom_path on the configured Falz layer
    (per Decision D4). The 'Falz' spot color must be registered (either in
    shared/ci.yml or via doc.add_color) before the template is built.
    """
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float
    layer: int                            # caller passes integer index
    color: str = "Falz"                   # spot color name
    line_width_pt: float = 0.5
    dash_pattern: str = "dashed"          # "dashed" | "dotted" | "solid"
    anname: str = "Falzlinie"

    def emit(self) -> Iterable: ...       # yields Polygon


# ---------------------------------------------------------------------------
# Block: DieCut
# Used by: wahltag-tueranhaenger (Außenkontur + Türklinken-Loch)
# Renders as: Polygon with closed custom_path, line_color="Stanzkontur",
#             fill="None", on layer "Stanzkontur" (printable=False)
# ---------------------------------------------------------------------------
@dataclass
class DieCut:
    """Geschlossener Pfad für Stanzform — Druckereistandard via Spot-Color.

    Caller provides the path data in mm coordinates relative to page origin;
    the block converts to pt and emits as Polygon with custom_path on the
    configured Stanzkontur layer (per Decision D4).
    """
    path_mm: str                          # SVG-style path data, mm coords
    layer: int                            # caller passes integer index
    color: str = "Stanzkontur"
    line_width_pt: float = 0.5
    anname: str = "Stanzkontur"
    fill: str = "None"

    def emit(self) -> Iterable: ...       # yields Polygon


# ---------------------------------------------------------------------------
# Block: FoldedPanel
# Used by: kandidat-falzflyer-din-lang (3 panels per side), infostand-tent-card
# Renders as: A logical panel slot — emits a non-printing guide frame on the
#             Hilfslinien layer (label) and is a no-op on the printable surface.
#             Templates draw INTO panels by composing other blocks at panel-
#             relative coordinates (the FoldedPanel itself just identifies the
#             zone for layout reasoning).
# Alternative: this block could also auto-emit a FoldLine on its trailing edge
# ---------------------------------------------------------------------------
@dataclass
class FoldedPanel:
    """Logischer Panel-Slot in einem gefalzten Layout.

    Provides:
    - A non-printing guide TextFrame on the Hilfslinien layer with the panel
      label (e.g. "Panel 1: Vorderseite", "Panel 2: Aufmacher") for editor
      visibility.
    - Optional: emits the trailing FoldLine automatically when emit_fold_line=True.

    Coordinates are page-relative; the panel is a logical zone and does NOT
    clip child content (Scribus has no panel concept; frames are placed at
    absolute coords).
    """
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float
    label: str                            # e.g. "Panel 1: Closer"
    fold_line_at: Optional[str] = None    # "right" | "bottom" | None
    fold_line_layer: Optional[int] = None
    hilfslinien_layer: int = 3            # default index for the Hilfslinien layer
    anname_prefix: str = "Panel"

    def emit(self) -> Iterable: ...       # yields TextFrame label + optional FoldLine


# ---------------------------------------------------------------------------
# Block: DoorHangerCutout
# Used by: wahltag-tueranhaenger
# Composes: An outer DieCut for the door-hanger silhouette (rounded rectangle
#           with the hanging hole at the top) + an inner DieCut for the
#           Türklinken-Loch (the keyhole-shaped slot users hang it on).
# ---------------------------------------------------------------------------
@dataclass
class DoorHangerCutout:
    """Stanzform für Türanhänger: Außenkontur + Türklinken-Loch.

    Standard-Türanhänger-Geometrie nach DIN-Druckereistandard: vertikales
    Rechteck mit oben rundem Hänger-Loch (typischerweise 30 mm Durchmesser)
    plus oben mittig die schlüsselloch-förmige Aussparung für die Türklinke.

    Per Decision D4: emittiert auf der Stanzkontur-Layer als Polygon mit
    geschlossenem Path; Druckerei sieht die Stanzform separat im PDF/X-4.
    """
    outer_w_mm: float = 105
    outer_h_mm: float = 250
    corner_radius_mm: float = 5
    hanger_hole_diameter_mm: float = 30
    hanger_hole_center_y_mm: float = 15   # from top edge
    keyhole_slot_w_mm: float = 25         # bigger circle of the keyhole
    keyhole_slot_h_mm: float = 50         # total length including the slot
    layer: int                            # caller passes integer index
    anname: str = "Türanhänger Stanzform"

    def emit(self) -> Iterable: ...       # yields one or two DieCut instances


# ---------------------------------------------------------------------------
# Block: TableTentFold
# Used by: infostand-tent-card-a5-quer
# Composes: A FoldLine across the horizontal centre of an A4 landscape page
#           (which folds into A5 quer tent), plus optional Hilfslinien-Layer
#           panel labels for "Vorderseite (sichtbar)" and "Rückseite (sichtbar)".
# ---------------------------------------------------------------------------
@dataclass
class TableTentFold:
    """Falz-Geometrie für A5-Tent-Card aus A4 quer (gefalzt mittig horizontal).

    Emittiert die zentrale Falzlinie + zwei Hilfslinien-Labels für die beiden
    sichtbaren Seiten der aufgestellten Tent-Card.
    """
    page_w_mm: float                       # caller passes page width (typically 297)
    page_h_mm: float                       # caller passes page height (typically 210)
    fold_line_layer: int                   # caller passes Falz layer index
    hilfslinien_layer: int = 3
    line_width_pt: float = 0.5

    def emit(self) -> Iterable: ...        # yields FoldLine + 2 panel labels
```

### Reference: existing primitive interfaces these blocks compose

```python
# From tools/sla_lib/builder/primitives.py — VERBATIM signatures already in use

@dataclass
class _Frame:
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 50
    h_mm: float = 30
    anchor: Optional[Anchor] = None
    rotation_deg: float = 0
    layer: int = 2
    anname: str = ""
    custom_path: Optional[str] = None
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    xpos_pt: Optional[float] = None         # round-trip override
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
    text_align: Optional[int] = None         # DEPRECATED alias
    default_linesp_mode: Optional[int] = None
    trail_style: Optional[str] = None
    trail_attrs: Optional[dict] = None
    fill: Optional[str] = None               # PCOLOR
    line_color: Optional[str] = None         # PCOLOR2
    line_width_pt: float = 0
    default_style_attrs: Optional[dict] = None
    next_item: Optional["TextFrame"] = None
    def link_to(self, other: "TextFrame") -> "TextFrame": ...

@dataclass
class ImageFrame(_Frame):
    src: str = ""
    image: str = ""                          # alias for src
    layer: int = 1
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1
    ratio: int = 1
    pic_art: int = 1
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    inline_image_data: Optional[str] = None  # base64( BE-len + zlib( raw_bytes ) )
    inline_image_ext: Optional[str] = None   # "png" | "jpg" | "pdf" | …

@dataclass
class Polygon(_Frame):
    fill: str = "Black"
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0
    shape: str = "rectangle"                 # "rectangle" | "ellipse"
    fill_shade: int = 100

# From tools/sla_lib/builder/document.py
class Document:
    def __init__(self, *, brand=None, layers: Optional[list[DocumentLayer]] = None,
                 facing_pages=False, ...): ...
    def add_master(self, name="Normal", size="A4", orientation="portrait",
                   bleed_mm=3.0, margins_mm=(10,10,10,10), facing="right",
                   page_xpos_pt=None, page_ypos_pt=None,
                   width_pt=None, height_pt=None) -> Page: ...
    def add_page(self, size="A4", orientation="portrait", bleed_mm=3.0,
                 margins_mm=(10,10,10,10), master="Normal", label="",
                 page_xpos_pt=None, page_ypos_pt=None,
                 width_pt=None, height_pt=None) -> Page: ...
    def add_color(self, name, *, rgb=None, cmyk=None, spot=False, register=False) -> None: ...
    def add_para_style(self, style: ParaStyle) -> None: ...
    def add_char_style(self, style: CharStyle) -> None: ...
    def save(self, path) -> None: ...

# From tools/sla_lib/builder/styles.py
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

# Helper proposed for issue #10 (does NOT exist today; plan must add it)
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Wrap raw bytes into Scribus's qCompress base64 envelope.

    Returns (base64_data, ext) tuple suitable for ImageFrame(
        inline_image_data=…, inline_image_ext=…).
    """
    import zlib
    from base64 import b64encode
    compressed = zlib.compress(image_bytes, 9)
    qcompressed = len(image_bytes).to_bytes(4, "big") + compressed
    return b64encode(qcompressed).decode("ascii"), ext
```

---

## 12. Sources

| Confidence | Source | Citation |
|---|---|---|
| HIGH | DSL public API | `tools/sla_lib/builder/__init__.py:1-82` |
| HIGH | Frame primitives surface | `tools/sla_lib/builder/primitives.py:1-951` |
| HIGH | Document/Page surface | `tools/sla_lib/builder/document.py:1-1088` |
| HIGH | DocumentLayer dataclass | `tools/sla_lib/builder/styles.py:17-29` |
| HIGH | Layer emission | `tools/sla_lib/builder/document.py:878-910` |
| HIGH | inline image attribute emission | `tools/sla_lib/builder/primitives.py:798-808` |
| HIGH | qCompress encoding format | `tools/sla_to_dsl.py:202-216`, `tools/sla_lib/tests/test_sla_diff.py:340-349` |
| HIGH | Brand profile | `tools/sla_lib/builder/brand.py:1-149` |
| HIGH | CI loader | `tools/sla_lib/builder/ci.py:1-181` |
| HIGH | Block library | `tools/sla_lib/builder/blocks.py:1-621` |
| HIGH | Existing template builds | `templates/postkarte-a6-kampagne/build.py:1-369`, `templates/plakat-a1-hochformat/build.py:1-198`, `templates/zeitung-a4-grun/build.py:1-2463` |
| HIGH | Smoke pattern | `templates/_smoke/postcard-a6/build.py`, `templates/_smoke/zeitung-mini/build.py` |
| HIGH | meta.yml fields | `templates/postkarte-a6-kampagne/meta.yml:1-99`, `templates/plakat-a1-hochformat/meta.yml`, `templates/zeitung-a4-grun/meta.yml` |
| HIGH | shared/ci.yml structure | `shared/ci.yml:1-129` |
| HIGH | shared/ci-defaults.yml | `shared/ci-defaults.yml:1-174` |
| HIGH | Existing spec schema | `shared/template-spec.schema.yaml:1-313`, `docs/spec-input-schema.md` |
| HIGH | check_ci validator | `tools/check_ci.py:1-265` |
| HIGH | sla_diff overview | `tools/sla_diff.py:1-100` (+ test fixtures) |
| HIGH | render pipeline | `tools/render.py:1-117`, `tools/render_pipeline.py:1-684`, `tools/_export_pdf.py:1-7` |
| HIGH | visual_diff | `tools/visual_diff.py:1-360` |
| HIGH | gallery_build | `tools/gallery_build.py:1-135` |
| HIGH | Original SLA layer schemas | `postkarte-vorlage-original.sla` LAYERS line, `plakat-a1-hochformat-original.sla`, `gruene-zeitung-vorlage-original.sla` |
| HIGH | inlineImageExt usage in originals | `grep "inlineImageExt"` of three originals — all `"png"` |
| HIGH | Codex CLI flags | `codex exec --help` (verified at `/root/.npm-global/bin/codex`) |
| HIGH | Gemini CLI flags | `gemini --help` (verified at `/root/.npm-global/bin/gemini`) |
| HIGH | CI workflow | `.github/workflows/pages.yml:1-141` |
| HIGH | bin/render-gallery, bin/validate | `bin/render-gallery`, `bin/validate` |
| HIGH | Environment availability | `command -v` for gs (10.05.1), pdftoppm (25.03.0), convert (ImageMagick 7.1.1-43), scribus (1.6.3 in container, 1.6.5 in CI), python3, node, xvfb-run; `pdftocairo`/`pdftoppm` available; `inkscape`/`rsvg-convert` not present |
| HIGH | EPS file structure | head of `/root/workspace/Wahl Kreuz im Kreis.eps`: Adobe Illustrator 30.2, BoundingBox 0 0 84 91, 270 KB |
| HIGH | No PIL, no jsonschema | `python3 -c "import PIL"` fails, `import jsonschema` fails |
| MEDIUM | Scribus PDF inline support | `https://blog.jfml.eu/2024/01/03/how-to-import-pdfs-as-images-in-scribus/` (vector preserved through "Embed PDF & EPS files" PDF export option). External, single-source. |
| MEDIUM | Scribus 1.6 forum threads on PDF/EPS embedding | `https://forums.scribus.net/index.php?topic=1024.0`, `https://forums.scribus.net/index.php?topic=4384.0` — confirms PDF/EPS embed pathway |
| MEDIUM | scribus-image-embedder reference | `https://github.com/Afueth/scribus-image-embedder` — confirms qCompress wrapping convention is identical for any binary content |
| LOW | Whether `inlineImageExt='pdf'` Scribus 1.6.5 round-trips byte-stably | not exercised in this codebase; should be verified empirically in Phase 2 prototype |
| LOW | Optimal Ghostscript flags for deterministic EPS→PDF | D10 picks `-dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite`; cross-check needed against per-machine output drift |
