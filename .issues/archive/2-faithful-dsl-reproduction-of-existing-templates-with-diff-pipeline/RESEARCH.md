# RESEARCH — Faithful DSL reproduction of existing templates with diff pipeline

**Researched:** 2026-05-05
**Issue:** 2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline
**Confidence:** HIGH (inventory and gap analysis are direct measurements of the three originals; pipeline tooling and CI plans are MEDIUM, depending on exact tolerance numbers and rebaselining workflow that the planner will lock in)

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D1 — Equivalence target: semantic, not byte-level.** Diff target is "the rebuilt SLA renders to the same layout/content as the original" up to documented tolerances. ItemID renumbered sequentially on both sides; XML attribute order sorted; floats rounded to 6 decimals; PAGEOBJECT order sorted by `(OwnPage, YPOS, XPOS)`.
- **D2 — Converter emits typed DSL, not `raw_attrs` escape hatch.** `tools/sla_to_dsl.py` must produce `build.py` files that use typed DSL primitives only. Every Scribus attribute the converter encounters in the three originals must have a typed counterpart in the DSL. `raw_attrs` is **not** part of the public DSL surface.
- **D3 — Visual baseline is committed PDFs, frozen now.** For each original SLA we render its PDF once locally with the current Scribus 1.6.5 toolchain and commit it at `templates/<id>/baseline.pdf`. `visual_diff` always compares the DSL build against the committed `baseline.pdf` (not against a re-render of the original). Rebaselining is an explicit human action.
- **D4 — CI runtime budget.** Local: 150 dpi rasters, full coverage. CI: 96 dpi rasters, runs on every push to main and PRs touching `tools/`, `templates/`, `shared/`. Acceptable runtime ~5 min.
- **D5 — Gallery output: only DSL-built reproductions.** `templates/<id>/template.sla` (DSL-built) is what the gallery offers. Originals stay in repo as diff baseline only.
- **D6 — Strict converter.** Raises a typed exception on any unhandled element/attribute in the originals. Better to fail loudly than emit a `build.py` that renders something subtly different.

### Claude's Discretion
None separately listed; CONTEXT.md is fully prescriptive.

### Deferred Ideas (OUT OF SCOPE)
- Bundled fonts and ICC profiles
- LLM authoring tooling
- Block-extraction tools
- Visual-regression baseline-blessing UI

## Summary

The three originals are simpler than initial fears: only one used layer (`Hintergrund`/`Ebene 1`, LAYER=0 on every PAGEOBJECT), no MASTEROBJECTs anywhere (masters are empty templates used purely as left/right discriminators in the Zeitung), no gradients, no patterns, no transparency, no PDF annotations, no nested groups, no text-flow obstacles. The DSL is much closer to "byte-equivalent" than the issue title implies.

The **real gaps** are concentrated in three areas: (1) per-document **paragraph and character styles** — every original defines its own (e.g. `Headline sehr wichtig`, `Fließtext`, `Zwischenüberschrift`) which do not match the `ci/...` names in `shared/ci.yml`; (2) **per-run text formatting** (FCOLOR/FONTSIZE/FSHADE/FONT/FEATURES/KERN overrides on individual `<ITEXT>` runs) — the Zeitung has 183 ITEXTs with FONTSIZE override and 11 with FONT override; (3) **NEXTITEM/BACKITEM linked-frame chains** — 14 chains in the Zeitung for multi-column article flow. Plus a long tail: rounded-corner rectangles (FRTYPE=2, `RADRECT`), inline embedded images (`isInlineImage="1"` + `ImageData=...`), soft-hyphens (Plakat has 7), `<var name="pgno"/>` page-number placeholders (Zeitung), one soft-shadow frame (Postkarte), one non-CI `Green` color (different RGB in Postkarte vs Zeitung — both must be reproduced verbatim), `fillRule` on 86 polygons in the Zeitung, and FRTYPE=3 paths that are themselves trivial rectangles but with reverse vertex ordering.

**Primary recommendation:** Build the converter incrementally, Postkarte first, with strict-mode raising on every unhandled element. Each `raise UnhandledElement` triggers a typed DSL extension. Because no new third-party libraries are required (we already own lxml, the reader, the builder), the work is well-bounded; the main risk is style scope (the Zeitung has 23 paragraph styles with 23 distinct attribute combinations including drop caps, paragraph spacing, language/hyphenation, font features). A `DocumentStyle` typed builder that mirrors `BrandStyle` plus the long-tail attributes is the load-bearing addition.

For the diff pipeline: `sla_diff` should land **first** (before the converter) so the converter has a clean go/no-go test loop. `visual_diff` can land last; ImageMagick `compare`+`montage` with `pdftoppm` rasterisation is sufficient at the 1% tolerance the issue prescribes. `odiff` is not installed and would require new dependency negotiation.

## Codebase Analysis

### Relevant code (existing, to extend)

| File | Purpose | LOC | Relevance |
|---|---|---|---|
| `tools/sla_lib/builder/__init__.py` | DSL public surface (`Document`, `Page`, `TextFrame`, `ImageFrame`, `Polygon`, `Line`, `Color`, `Style`) | 45 | Re-exports; will add `CharStyle`, `ParaStyle`, `RoundedRectFrame`/path support, linked-frame helpers |
| `tools/sla_lib/builder/document.py` | `Document` (top-level), `Page`, `_IdGen`, ISO size table, XML emission order | 545 | Add: per-document custom palette registration, per-document style definitions, sections override, optional 2nd master, AUTOTEXT toggle |
| `tools/sla_lib/builder/primitives.py` | `_Frame`, `TextFrame`, `ImageFrame`, `Polygon`, `Line`, anchor resolution | 319 | Add: per-run FCOLOR/FONTSIZE/FONT/FSHADE/FEATURES/KERN; `RADRECT` (rounded corner); `path=` custom; `<var name="pgno"/>` insertion; soft-hyphen passthrough; linked chain via NEXTITEM/BACKITEM; soft-shadow attrs; `fillRule` |
| `tools/sla_lib/builder/blocks.py` | Composite blocks (`Headline4Line`, `StoererBadge`, `Masthead`, `EventDetails`, `ImpressumLine`, ...) | 401 | Will be largely **replaced** for the three reproductions — D5 says gallery serves DSL output, so block-call sites (in templates/`*/build.py`) become emitter-generated raw-primitive calls. The block library stays for greenfield future templates. |
| `tools/sla_lib/builder/ci.py` | Loads `shared/ci.yml` as `BrandColor`/`BrandStyle`/`BrandLayer`; exposes `Color`/`Style` enums | 175 | No change required; `BrandStyle`/`BrandColor` are sufficient as the reused dataclass shape for new typed `ParaStyle`/`Color(custom=...)`. |
| `tools/sla_lib/reader.py` | Parsing primitive: `SLADocument`, `iter_itext`, `frame_text`, `find_by_anname`, `slots()` | 108 | The converter consumes this. Will need extensions: `iter_pages()`, `iter_masters()`, `iter_layers()`, `iter_styles()`, `iter_charstyles()`, `iter_colors()`. |
| `tools/sla_lib/editor.py` | Slot-based fill (text/image substitution) | (top of file inspected) | Out of scope for this issue. |
| `tools/sla_lib/slot.py` | `Slot`, `SlotKind` for ANNAME parsing | (small) | Possibly reused by sla_diff for "this is a known slot, ignore semantic difference" rules. Probably no change needed. |
| `tools/check_ci.py` | Brand-drift validator (color/style mismatch) | 266 | Emits `extra-style`/`extra-color` warnings — the reproductions will trip these unless we relax to "warning OK if defined per-document". The reproductions WILL ship with non-CI styles by design (the originals defined them). Decision needed: extend `check_ci.py` to accept per-template style allowlist OR teach it that document-local styles are not "drift". Recommended: per-template `meta.yml` declares allowed extra-styles. |
| `tools/render.py`, `tools/_export_pdf.py` | Headless render; `xvfb-run -a scribus -g -ns -py _export_pdf.py <sla> <pdf>` | 117/7 | Reused unchanged for baseline render and visual_diff render. |
| `tools/gallery_build.py` | Generates per-template gallery content (PDFs, PNG previews, frontmatter) | (inspected top) | Reused unchanged; runs after `templates/*/build.py` produces `template.sla`. |
| `templates/postkarte-a6-kampagne/build.py` | Current placeholder DSL build (will be replaced by converter output) | 145 | Replace. |
| `templates/zeitung-a4-grun/build.py` | Current placeholder | (assumed similar) | Replace. |
| `templates/plakat-event/build.py` | Current placeholder | (assumed similar) | Replace. |
| `shared/ci.yml` | Canonical brand identity (colors/fonts/styles/layers) | 129 | **No change** — D2 says the converter must reproduce per-document styles via typed DSL, not by mutating shared ci.yml. Per-document styles live in the `build.py`. |
| `.research/01-sla-format.md` | Canonical SLA format reference | 290 | Authoritative; no new format research needed for this issue. |
| `.research/04-scribus-multipage-masters.md` | Master pages, OwnPage stability, page sets | 100+ | Authoritative for the Zeitung's facing-pages + 2-master setup. |
| `.github/workflows/pages.yml` | Build & deploy gallery; runs `tools/check_ci.py`, builds Astro site, deploys to Pages | 90 | Add: `validate-reproductions` step before `deploy` job runs. |
| `tools/sla_lib/tests/` | Existing unittest suite (`test_builder.py`, `test_blocks.py`, `test_check_ci.py`, `test_multipage.py`, `test_reader.py`) | (5 files) | Extend with `test_sla_to_dsl.py` (round-trip per template), `test_sla_diff.py` (synthetic-diff cases), `test_dsl_extensions.py` (new typed APIs). |

### Interfaces

<interfaces>
// From tools/sla_lib/builder/document.py — current public surface
class Document:
    def __init__(self, title: str = "", template_id: str = "",
                 author: str = "Die Grünen Niederösterreich",
                 ci_path: Optional[Path | str] = None) -> None: ...
    def add_master(self, name: str = "Normal",
                   size: str | tuple[float, float] = "A4",
                   orientation: str = "portrait",
                   bleed_mm: float = 3.0,
                   margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10),
                   facing: str = "right") -> Page: ...
    def add_page(self, size: str | tuple[float, float] = "A4",
                 orientation: str = "portrait",
                 bleed_mm: float = 3.0,
                 margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10),
                 master: str = "Normal",
                 label: str = "") -> Page: ...
    def save(self, path: Path | str) -> None: ...
    pages: list[Page]
    masters: list[Page]
    facing_pages: bool
    title: str
    template_id: str
    author: str
    ci: _CI

@dataclass
class Page:
    width_pt: float; height_pt: float; bleed_mm: float; margins_mm: tuple
    master_name: str; label: str; items: list
    own_page: int; page_xpos_pt: float; page_ypos_pt: float
    is_left: bool; is_master: bool; master_id: str
    def add(self, item) -> "Page": ...

// From tools/sla_lib/builder/primitives.py
@dataclass
class _Frame:
    x_mm: float; y_mm: float; w_mm: float; h_mm: float
    anchor: Optional[Anchor]; rotation_deg: float; layer: int; anname: str

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""
    fcolor: str = ""
    runs: Optional[list] = None     # list of (text, style_override_dict, separator)
                                    # separator in {"para", None (default = breakline)}
                                    # style_override currently supports ONLY "fcolor" and "fontsize"
    columns: int = 1
    col_gap_mm: float = 4
    def to_pageobject(self, idgen, page) -> etree._Element: ...

@dataclass
class ImageFrame(_Frame):
    src: str = ""           # → PFILE
    layer: int = 1
    def to_pageobject(self, idgen, page) -> etree._Element: ...

@dataclass
class Polygon(_Frame):
    fill: str = "Black"           # → PCOLOR
    line_color: str = "None"      # → PCOLOR2
    line_width_pt: float = 0      # → PWIDTH
    layer: int = 0
    shape: str = "rectangle"      # 'rectangle' (FRTYPE=0) | 'ellipse' (FRTYPE=1)
    def to_pageobject(self, idgen, page) -> etree._Element: ...

@dataclass
class Line:
    x1_mm: float; y1_mm: float; x2_mm: float; y2_mm: float
    color: str = "Black"; width_pt: float = 1.0; layer: int = 2; anname: str = ""
    def to_pageobject(self, idgen, page) -> etree._Element: ...

// From tools/sla_lib/builder/ci.py
@dataclass(frozen=True)
class BrandColor:
    name: str
    cmyk: tuple[int, int, int, int]
    spot: bool = False; register: bool = False
    role: Optional[str] = None
    @property
    def rgb(self) -> tuple[int,int,int]: ...
    @property
    def cmyk_hex8(self) -> str: ...

@dataclass(frozen=True)
class BrandStyle:
    name: str; font: str; fontsize: float
    align: int = 0
    parent: Optional[str] = None
    linesp: float = 13.0
    fcolor: str = "Black"
    language: str = "de"

@dataclass(frozen=True)
class BrandLayer:
    name: str; level: int
    visible: bool = True; printable: bool = True; editable: bool = True

class _CI:
    brand_name: str; brand_short: str
    colors: dict[str, BrandColor]
    fonts: list[str]
    styles: dict[str, BrandStyle]
    layers: list[BrandLayer]

def load_ci(path: Path | str = CI_YAML_DEFAULT) -> _CI: ...   # cached singleton

// From tools/sla_lib/reader.py
class SLADocument:
    def __init__(self, path: str | Path): ...
    @property
    def version(self) -> str: ...
    @property
    def page_count(self) -> int: ...
    @property
    def page_size_pt(self) -> tuple[float, float]: ...
    @property
    def bleed_pt(self) -> dict[str, float]: ...
    def page_objects(self) -> list[etree._Element]: ...
    def pages(self) -> list[etree._Element]: ...
    def find_by_anname(self, anname: str) -> etree._Element | None: ...
    def slots(self) -> list[Slot]: ...
    def iter_itext(self, frame: etree._Element) -> Iterator[etree._Element]: ...
    def frame_text(self, frame: etree._Element) -> str: ...
    def write(self, path: str | Path) -> None: ...

// From tools/check_ci.py — reused signatures
@dataclass
class Issue:
    severity: str   # 'critical' | 'warning' | 'info'
    code: str; message: str; detail: dict

@dataclass
class CIDriftReport:
    target: str; issues: list[Issue]
    @property
    def has_critical(self) -> bool: ...
    @property
    def has_any(self) -> bool: ...
def check_sla(sla_path: Path, ci: dict) -> CIDriftReport: ...
</interfaces>

### Reusable Components
- **`SLADocument`** (`tools/sla_lib/reader.py`) is the parse front-end for the converter and for `sla_diff`. Extend it with `iter_pages()`, `iter_masters()`, `iter_layers()`, `iter_colors()`, `iter_styles()`, `iter_charstyles()` rather than re-parsing from scratch.
- **`Issue`/`CIDriftReport` pattern** in `tools/check_ci.py` is exactly the schema shape `sla_diff` should use (severity + code + message + detail). Reuse this dataclass shape.
- **Render pipeline** `tools/render.py` and `tools/_export_pdf.py` are the only sanctioned PDF emission path (CONTEXT.md constraint). `visual_diff` calls into `render_sla(sla_path, pdf_path)` and `pdftoppm` to convert both PDFs to PNGs.
- **`expand_blocks(items)`** generator in `blocks.py` already handles primitive flattening; converter-emitted code calls primitive constructors directly so blocks aren't in the path.
- **`tools/sla_lib/tests/`** unittest harness; `test_multipage.py` already proves multi-page+master setup works, so the new tests can lean on the same fixture pattern.
- **lxml's attribute-preserving parse** (`SLADocument` already uses `XMLParser(remove_blank_text=False, strip_cdata=False)`) — no need to re-research XML handling.

### Potential Conflicts
- **`tools/check_ci.py` will flag the reproductions as drifty** because every original defines its own `Fließtext`/`Headline sehr wichtig`/etc. styles, none of which match `ci/headline-ultra` etc. Two paths: (1) accept warnings but not critical (current code already returns 0 if no critical, with `--strict` opt-in), or (2) extend `check_sla` to accept a per-template allow-list (preferred — gives cleaner CI output).
- **Per-document custom colors**: Postkarte has `Green` (RGB 153,102,51) and Zeitung has `Green` (RGB 0,255,0) — same name, different values. The converter must emit them as document-local colors without registering them in `shared/ci.yml`. The DSL needs `Document.register_color(name, rgb=..., cmyk=...)`. The `check_ci.py` `extra-color` warning is fine; we'll accept it for the reproductions.
- **Multi-master collision**: `Document.add_master(name)` raises if a master named `name` already exists. The Zeitung has two masters (`"Neue Musterseite rechts"`, `"Neue Musterseite links"`); the existing logic supports adding multiple masters, so no conflict. But the implicit "Normal" auto-insertion in `Document._build_xml()` (line 206) will inject an unwanted third master if the Zeitung's masters don't include one named `"Normal"`. That auto-insertion needs to be conditional on _any_ master existing, not specifically `"Normal"`.
- **The current DSL emits a label TextFrame for each named page** ("BEISPIELSEITE — Vorderseite", line 254-264 in `document.py`). The converter must not emit this — the originals don't have it. Either suppress via `label=""` or add `Page(suppress_label=True)`.
- **DSL emits `LANGUAGE="de"` in every STYLE** (`document.py:_emit_styles`). The Zeitung's styles set LANGUAGE on only 13 of 23. The diff normaliser must treat LANGUAGE-default differences as info-level, not warning.
- **DSL emits a fixed scratch-canvas position** (`SCRATCH_LEFT=100`, `SCRATCH_TOP=20`, `GAP_VERTICAL=40`). The Zeitung uses different scratch positions for facing pages (`PAGEXPOS=695.276` for right-column pages). The Document.add_page logic in line 178-183 already supports facing-pages X/Y stacking, but the constants don't match — Scribus normalises on next save anyway, so the diff normaliser must ignore PAGEXPOS/PAGEYPOS as long as the relative ordering is consistent.

### Code Patterns in Use
- **Dataclasses + `to_pageobject(idgen, page) -> etree._Element`** for every primitive. Converter emits primitive constructor calls; primitives are responsible for their own XML. Stay with this pattern.
- **`_IdGen` monotonic IDs**, never qHash. Keep.
- **Anchor resolution** via `resolve_anchor` accepts string anchors ("center", "top-left", "bottom-20"). Converter emits `x_mm`/`y_mm` directly (it has computed page-local coords from XPOS - PAGEXPOS), not anchors.
- **Layer index, not name**: primitives carry `layer: int` (LAYER attribute is integer). The originals all use `LAYER=0`; the converter emits `layer=0` everywhere. The DSL's default `layer=2` for TextFrame and `layer=1` for ImageFrame is wrong for these reproductions — converter must override.
- **`anname=""` on `_Frame`** sets `ANNAME` attribute. The originals have ANNAME on 0 to 85 of N items per file (most ANNAMEs are auto-generated like "u2950"); converter preserves ANNAME verbatim where present. sla_diff treats ANNAME as info-level (not part of layout).

## Per-original inventory

This section is the authoritative gap list — everything the converter must handle and everything the DSL must express. Counts are direct measurements via lxml on the originals at workspace root.

### Postkarte — `postkarte-vorlage-original.sla`

| Property | Value | Confidence |
|---|---|---|
| File size | 200 048 bytes | HIGH |
| Scribus version (root @Version) | `1.6.5` | HIGH |
| ANZPAGES | 2 | HIGH |
| Page size | 297.638 × 419.528 pt = **105 × 148 mm (A6 portrait)** | HIGH |
| ORIENTATION | 0 (portrait) | HIGH |
| PAGESIZE | `A6` | HIGH |
| UNITS | 1 (mm) | HIGH |
| BOOK | 0 (single page) | HIGH |
| Bleed (T/B/L/R) | 8.504 pt = **3 mm** all sides | HIGH |
| Margins (BORDER L/R/T/B) | 40 pt all sides ≈ 14.11 mm | HIGH |
| AUTOSPALTEN | 1, ABSTSPALTEN 11 (default column hint) | HIGH |
| AUTOTEXT | (absent) — no automatic text-frame chains | HIGH |

**Master pages (1):** Single master `NAM="Normal"`, `LEFT=0`, full-page geometry — **empty**, contains no MASTEROBJECTs. Used only as default for both doc pages.

**Pages (2):**
| NUM | MNAM | LEFT | XPOS | YPOS |
|---|---|---|---|---|
| 0 | `Normal` | 0 | 100.001 | 20.001 |
| 1 | `Normal` | 0 | 100.001 | 479.529 |

**Layers (1):**
| NUMMER | LEVEL | NAME | SICHTBAR | DRUCKEN | EDIT | LAYERC |
|---|---|---|---|---|---|---|
| 0 | 0 | `Hintergrund` | 1 | 1 | 1 | `#000000` |

The DSL's default 4-layer stack (`Hintergrund` / `Bilder` / `Text` / `Hilfslinien`) is wrong for this template. Converter must emit a **document-local layer override** so only `Hintergrund` is present.

**COLOR palette (8):**
| NAME | SPACE | Values | In CI? |
|---|---|---|---|
| `Black` | CMYK | 0/0/0/100 | yes |
| `White` | CMYK | 0/0/0/0 | yes |
| `Registration` | CMYK | 100/100/100/100 | yes |
| `Dunkelgrün` | CMYK | 85/35/95/10 | yes |
| `Hellgrün` | CMYK | 69/0/100/0 | yes |
| `Gelb` | CMYK | 0/0/100/0 | yes |
| `Magenta` | CMYK | 0/100/0/0 | yes |
| `Green` | RGB | 153/102/51 | **NO — not in shared/ci.yml** |

**Paragraph styles (9, NONE matching `ci/...`):**
| NAME | font | size | fcolor | align | linesp | parent | extras |
|---|---|---|---|---|---|---|---|
| `Default Paragraph Style` | (empty) | (default) | (default) | 0 | 15 | — | DefaultStyle="1" |
| `Fließtext` | Gotham Narrow Book | 12 | White | 1 | 13 | — | LANGUAGE=de |
| `Impressum` | Gotham Narrow Book | 5 | (inherit) | (inherit) | 6 | — | |
| `Default Paragraph Style (2)` | Gotham Narrow Book | (inherit) | (inherit) | 0 | 15 | — | duplicate of default |
| `Schrift rosa Kreis` | Gotham Narrow Ultra | 10 | White | 1 | 11 | — | |
| `Headline sehr wichtig` | Gotham Narrow Ultra | 27 | White | 1 | 23 | — | |
| `Kontaktmöglichkeiten` | Gotham Narrow Book | 8 | (inherit) | (inherit) | 10 | — | |
| `Vollkorn Headline sehr wichtig` | Vollkorn Black Italic | 27 | Gelb | 1 | 23 | — | |
| `Unterüberschrift` | Gotham Narrow Book | 13 | White | 1 | 16 | — | |

**Charstyles (2, neither in CI):**
| CNAME | font | size | fcolor |
|---|---|---|---|
| `Default Character Style` | Gotham Narrow Black | 12 | Black |
| `Default Character Style (2)` | Gotham Narrow Book | 12 | Black |

**PAGEOBJECTs (18) — PTYPE × FRTYPE distribution:**
| PTYPE | FRTYPE | Count | What |
|---|---|---|---|
| 4 (Text) | 0 (rect) | 7 | Headlines, body, impressum, störer text |
| 2 (Image) | 0 (rect) | 4 | One large image frame + 3 small inline-image frames (logo, QR-like) |
| 2 (Image) | 2 (round-rect, **RADRECT=2.835pt = 1mm corner**) | 4 | Inline-embedded PNG buttons (4 sub-page-1 graphics) |
| 6 (Polygon) | 0 (rect) | 2 | Two big background rectangles (Dunkelgrün full-page bleed) |
| 6 (Polygon) | 1 (ellipse) | 1 | Magenta störer circle |

PAGEOBJECTs per page: page 0 → 7 items; page 1 → 11 items.

**FRAMEOBJECTs (3, all clipboard/scratch — NOT visible in document):** `XPOS=0 YPOS=0 OwnPage=-1`. PTYPE=4 FRTYPE=3 (custom path) and PTYPE=4 FRTYPE=0. Contents include text snippets `'UNTERÜBERSCHRIFT'`, `'ÜBERSCHRIFT SEHR WICHTIG'`. **Recommendation:** converter drops these silently (Scribus serializes orphan inline frames; they don't render). sla_diff ignores FRAMEOBJECT count.

**Linked text-frame chains:** **None** (no NEXTITEM/BACKITEM != -1).

**Soft-hyphens (`\xad`):** **0** occurrences.

**HYPHEN/EXCEPTION block:** absent.

**ITEXT runs (27):** 8 with `FCOLOR` override, 7 with `FSHADE`, 2 with `FONTSIZE` override, 2 with `FONT` override, 2 with `FEATURES`, 1 with `KERN`. Per-run formatting is REAL HERE.

**StoryText element types:** `DefaultStyle`(10), `ITEXT`(27), `para`(13), `breakline`(5), `trail`(10).

**Sections (1):** `Number=0 Name="Abschnitt 1" From=0 To=1 Type=Type_1_2_3 Start=1`. Compatible with DSL's auto-section emission.

**PageSets (4 standard sets):** Identical to DSL emit. No change.

**Exotic attrs:**
- `RADRECT="2.83464566929134"` (1 mm rounded corners) on 4 PTYPE=2 frames → **DSL gap** (FRTYPE=2 not supported)
- `HASSOFTSHADOW="1"` + 9 `SOFTSHADOW*` attributes on **1 text frame** → **DSL gap** (no soft-shadow support)
- `ROT="351"` (negative rotation 9°) on 2 frames → already supported via `rotation_deg`
- `isInlineImage="1"` + `ImageData="<base64-qcompress>"` + `inlineImageExt="png"` on 7 frames → **DSL gap** (cannot emit embedded images)
- 2 PTYPE=2 frames with `LOCALSCX/LOCALSCY` of 0.099 (placeholder image, non-1.0 scale) — already supported via raw frame emission, but would require typed kwargs to round-trip cleanly

### Plakat A1 — `plakat-a1-hochformat-original.sla`

| Property | Value | Confidence |
|---|---|---|
| File size | 235 841 bytes | HIGH |
| Scribus version | `1.6.5` | HIGH |
| ANZPAGES | 1 | HIGH |
| Page size | 1683.78 × 2383.94 pt = **594 × 841 mm (A1 portrait)** | HIGH |
| ORIENTATION | 0 (portrait) | HIGH |
| PAGESIZE | `Custom` (A1 isn't a Scribus preset) | HIGH |
| UNITS | 1 (mm) | HIGH |
| BOOK | 0 | HIGH |
| Bleed | 3 mm all sides | HIGH |
| Margins | 40 pt = 14.11 mm all sides | HIGH |

**Master pages (1):** `NAM="Normal"`, empty (no MASTEROBJECTs).

**Pages (1):** NUM=0, MNAM=`Normal`, LEFT=0, XPOS=100.001, YPOS=20.001.

**Layers (1):** Same as Postkarte — single `Hintergrund`, `LAYER=0` on every PAGEOBJECT.

**COLOR palette (5):** `Black`, `White`, `Registration`, `Dunkelgrün`, `Gelb`. **All in CI.** No custom colors. (Note: `Hellgrün` and `Magenta` are absent — `check_ci.py` would flag as `info missing-color`.)

**Paragraph styles (5, NONE matching `ci/...`):**
| NAME | font | size | fcolor | align | linesp |
|---|---|---|---|---|---|
| `Default Paragraph Style` | (empty) | (default) | (default) | 0 | 15 |
| `Headlineweiß` | Gotham Narrow Ultra | 160 | White | 0 | 150 |
| `Überschrift gelb` | Vollkorn Black Italic | 160 | Gelb | 0 | 150 |
| `Fließtext` | Gotham Narrow Book | 50 | White | (inherit) | (inherit) |
| `Impressum` | Gotham Narrow Book | 20 | (inherit) | (inherit) | 20 |

**Charstyles (1):** `Default Character Style`, Gotham Narrow Black, size 12, Black.

**PAGEOBJECTs (9) — PTYPE × FRTYPE distribution:**
| PTYPE | FRTYPE | Count | What |
|---|---|---|---|
| 4 (Text) | 0 (rect) | 6 | Headline (multi-run), body, event details, impressum |
| 2 (Image) | 0 (rect) | 3 | Background image, logo, QR/event image |

**FRAMEOBJECTs (3, all scratch):** Same pattern as Postkarte; orphans, not visible. Drop.

**Linked text-frame chains:** **None.**

**Soft-hyphens (`\xad`):** **7 occurrences** in real words: `'ei\xadne gro\xadße '`, `'vier\xadzei\xadli\xadge '`, `'Ü\xadber\xadschrift '`. **CRITICAL**: must round-trip verbatim; DSL must not strip them.

**HYPHEN/EXCEPTION:** absent.

**ITEXT runs (18):** 2 with `FCOLOR`, 2 with `FSHADE`, 1 with `FONT`. Lighter per-run formatting than the Postkarte.

**StoryText element types:** `DefaultStyle`(9), `ITEXT`(18), `para`(9), `trail`(9). No `breakline`.

**Sections (1):** `Number=0 From=0 To=0 Type=Type_1_2_3 Start=1`.

**Exotic attrs:**
- `ROT="270"` (90° CCW) on 1 frame → already supported via `rotation_deg`
- `isInlineImage="1"` on 2 frames → DSL gap (same as Postkarte)
- No `RADRECT`, no `HASSOFTSHADOW`, no `fillRule`

### Grüne Zeitung — `gruene-zeitung-vorlage-original.sla` (the hard one)

| Property | Value | Confidence |
|---|---|---|
| File size | 569 864 bytes | HIGH |
| Scribus version | `1.6.5` | HIGH |
| ANZPAGES | **14** | HIGH |
| Page size | 595.276 × 841.890 pt = **210 × 297 mm (A4 portrait)** | HIGH |
| ORIENTATION | 0 (portrait) | HIGH |
| PAGESIZE | `Custom` (overridden — it's A4 dimensionally) | HIGH |
| UNITS | 1 (mm) | HIGH |
| BOOK | 1 (**facing pages**) | HIGH |
| Bleed | 3 mm all sides | HIGH |
| Margins | 59.528 pt = 21 mm all sides | HIGH |
| AUTOSPALTEN | 1, ABSTSPALTEN 12 | HIGH |

**Master pages (2):**
| NAM | LEFT | NUM | Size |
|---|---|---|---|
| `Neue Musterseite rechts` | 0 (right) | 0 | 595.276 × 841.890 |
| `Neue Musterseite links` | 1 (left) | 1 | 595.276 × 841.890 |

Both empty — **no MASTEROBJECTs anywhere** in the document. The masters serve only as left/right discriminators carrying the same blank geometry.

**Pages (14):** Master assignments are inconsistent with page position (per `.research/04` — `LEFT` on PAGE is recomputed by Scribus from page-set columns, not from MNAM). Distribution: 5 pages with MNAM=`Neue Musterseite rechts`, 9 pages with MNAM=`Neue Musterseite links`. The master-name choice is not load-bearing for layout (since both masters are empty), so the converter must reproduce MNAM **verbatim** but the visual diff won't depend on it.

**Layers (1):** `NUMMER=0 LEVEL=0 NAME='Ebene 1' SICHTBAR=1 DRUCKEN=1 EDIT=1` — note **NAME differs from Postkarte/Plakat** (`Ebene 1` vs `Hintergrund`). Converter emits document-local layer named `Ebene 1`.

**COLOR palette (8):**
| NAME | SPACE | Values | In CI? |
|---|---|---|---|
| `Black` `White` `Registration` `Dunkelgrün` `Hellgrün` `Gelb` `Magenta` | CMYK | (CI values) | yes |
| `Green` | RGB | **0/255/0** (different from Postkarte's 153/102/51!) | **NO — and same name, different value than Postkarte** |

The converter MUST emit `Green` as a per-document RGB color with the file-specific value. Since `Green` exists in two reproductions with different RGB triples, treating it as a shared-CI color would be wrong. → DSL needs `Document.add_color(name, rgb=(R,G,B))` and `Document.add_color(name, cmyk=(C,M,Y,K))`.

**Paragraph styles (23, NONE matching `ci/...`).** Full list:

| NAME | font | size | fcolor | align | linesp | parent | extras |
|---|---|---|---|---|---|---|---|
| `Default Paragraph Style` | Gotham Narrow Book | (default) | (default) | 0 | 15 | — | DefaultStyle=1 |
| `[No paragraph style]` | Gotham Narrow Book | 12 | Black | 0 | (inherit) | `Default Paragraph Style` | |
| `Titelseite Header` | Gotham Narrow Ultra | 55 | Gelb | 1 | 46 | — | |
| `Monat/Ausgabe` | Gotham Narrow Black | 13 | White | (inherit) | (inherit) | — | |
| `Zustellerhinweis (Post)` | Gotham Narrow Book | 6 | Black | 0 | (inherit) | — | |
| `Impressum` | Gotham Narrow Book | 8 | White | (inherit) | 9 | — | |
| `Copyright` | Gotham Narrow Book | 5.5 | (inherit) | (inherit) | (inherit) | — | |
| `Seitenzahl` | Gotham Narrow Black | (inherit) | Dunkelgrün | (inherit) | (inherit) | — | |
| `Fließtext` | (empty) | (inherit) | (inherit) | 3 (justify) | (inherit) | — | |
| `Schrift Störer` | Gotham Narrow Ultra | 19 | White | 1 | 13 | — | |
| `Inhaltsheadline Titelseite` | Gotham Narrow Ultra | (inherit) | White | (inherit) | 11 | — | |
| `Überschrift weiß` | Gotham Narrow Ultra | 40 | White | (inherit) | (inherit) | — | |
| `Überschrift Dunkelgrün` | Gotham Narrow Ultra | 40 | Dunkelgrün | (inherit) | 35 | — | |
| `Bildunterschrift weiß` | Gotham Narrow Book | 10 | White | (inherit) | 12 | — | |
| `Fließtext weiß` | Gotham Narrow Book | (inherit) | White | 3 (justify) | (inherit) | — | |
| `Fließtext in grünem Kasten` | (empty) | 11 | White | 3 (justify) | (inherit) | — | |
| `Headline in grünem Kasten` | Gotham Narrow Bold | (inherit) | White | 1 | (inherit) | — | |
| `Zwischenüberschrift` | Gotham Narrow Bold | (inherit) | Dunkelgrün | (inherit) | (inherit) | — | |
| `Einleitungstext` | Gotham Narrow Black | (inherit) | (inherit) | (inherit) | (inherit) | `Zwischenüberschrift` | |
| `Zwischenüberschrift weiß` | Gotham Narrow Black | (inherit) | White | (inherit) | (inherit) | `Zwischenüberschrift` | |
| `Zitat weißer Text` | Vollkorn Black Italic | 14 | White | 1 | (inherit) | — | |
| `Zitat grüner Text` | (empty) | (inherit) | Dunkelgrün | (inherit) | (inherit) | `Zitat weißer Text` | |
| `NormalParagraphStyle` | Gotham Narrow Black | (inherit) | (inherit) | (inherit) | (inherit) | — | |

**Plus** the following STYLE attributes are used (across the 23 styles):

| Attribute | # styles using it | Meaning |
|---|---|---|
| `FONTFEATURES` | 18 | OpenType feature flags |
| `LINESPMode` | 14 | Line-spacing mode (0=auto, 1=fixed, 2=relative) |
| `LANGUAGE` | 13 | Language for hyphenation |
| `NACH` | 10 | Paragraph spacing after (pt) |
| `VOR` | 6 | Paragraph spacing before (pt) |
| `MinWordTrack` | 4 | Min word-spacing tracking |
| `FEATURES` | 3 | (CharStyle features attached to paragraph default char style) |
| `MinGlyphShrink` | 3 | Min glyph shrink for justification |
| `DIRECTION` | 2 | LTR/RTL |
| `INDENT` | 2 | First-line indent |
| `RMARGIN` | 2 | Right margin |
| `FIRST` | 2 | First-line indent (alt) |
| `DROP` | 2 | Drop cap enabled |
| `DROPLIN` | 2 | Drop cap line count |
| `HyphenConsecutiveLines` | 2 | Max consecutive hyphens |
| `TXTULP` | 2 | Underline position |
| `TXTSTP` | 2 | Strikethrough position |
| `KeepTogether` | 2 | Paragraph keep-together |
| `KERN` | 2 | Kerning |
| `BCOLOR`/`BSHADE` | 1 | Paragraph background color |
| `TXTSHX/Y/OUT/ULW/STW` | 1 ea | Text shadow / outline / underline width / strikethrough width |
| `SCALEV` | 1 | Vertical scale |
| `FSHADE` | 1 | Fill shade |
| `MaxGlyphExtend` | 1 | Max glyph extend |
| `KeepLinesStart` | 1 | Keep N start lines |
| `HyphenWordMin` | 1 | Min word length for hyphenation |
| `ParagraphEffectOffset` | 1 | Effect offset |
| `Bullet` | 1 | Bullet char |
| `Numeration` | 1 | Numbered list |
| `BASEO` | 1 | Baseline offset |
| `DefaultStyle` | 1 | Marks the default-paragraph style |

The current DSL `BrandStyle` only carries `name, font, fontsize, align, parent, linesp, fcolor, language`. It must grow to support all 31 attribute names above (or accept arbitrary extra attrs in a typed `extra: dict[str, str]` field) for the Zeitung to round-trip.

**Charstyles (1):** `Default Character Style`, Gotham Narrow Book, size 12, Black.

**PAGEOBJECTs (140) — PTYPE × FRTYPE distribution:**
| PTYPE | FRTYPE | Count |
|---|---|---|
| 4 (Text) | 3 (custom path, all rectangles) | **79** |
| 4 (Text) | 0 (rect) | 33 |
| 2 (Image) | 0 (rect) | 19 |
| 2 (Image) | 3 (custom path) | 1 |
| 6 (Polygon) | 3 (custom path, all rectangles) | 6 |
| 6 (Polygon) | 1 (ellipse) | 2 |

The 79+1+6 = **86 frames with FRTYPE=3** are dominantly trivial rectangles in the path (e.g. `M0 0 L0 H L W H L W 0 L0 0 Z`) — but with **vertex order reversed** (counterclockwise) compared to the DSL's emitted clockwise rectangle. This is significant for `sla_diff`: the DSL emits FRTYPE=0 with a clockwise path, while the originals emit FRTYPE=3 with an explicit (CCW) path. The diff normaliser must (a) treat any FRTYPE in {0, 3} with a 5-vertex closed-rectangle path as equivalent to FRTYPE=0, OR (b) the converter must emit FRTYPE=3 with the matching path — recommended (b) since CONTEXT.md D2 says we round-trip the format faithfully.

Items per page distribution:
```
page 0: 14 items   page 7:  9 items
page 1:  6 items   page 8: 16 items
page 2: 10 items   page 9:  9 items
page 3: 11 items   page 10: 8 items
page 4:  6 items   page 11: 8 items
page 5:  7 items   page 12: 12 items
page 6: 10 items   page 13: 14 items
```

**FRAMEOBJECTs (5, all scratch — NOT visible):** Includes a `PTYPE=12` (Group) and several PTYPE=4 with FRTYPE=3, all `OwnPage=-1`, contain Lorem-ipsum / event-text / german-text snippets. Drop.

**Linked text-frame chains (14 chains, total 42 frames):** All chains are **3 frames per chain on a single page** (multi-column article flow within one page). Sample:

```
chain 1 (page 1):  114975536 → 119019072 → 118939664      (ANNAMEs: 'Kopie von u2f23', '... (2)', '... (3)')
chain 2 (page 2):  114499680 → 110819792 → 110822608      (ANNAMEs: 'u2d5c', 'u2da1', 'Kopie von u2da1')
chain 3 (page 2):  117930928 → 117933760 → 117928096
chain 4 (page 3):  117945088 → 117936592 → 117942256
chain 5 (page 4):  117962080 → 117976240 → 117964912
chain 6 (page 5):  117967744 → 117981904 → 117970576
chain 7 (page 6):  235082448 → 235076784 → 235079616
chain 8 (page 7):  235096608 → 235099440 → 235088112
chain 9 (page 8):  235119264 → 235122096 → 239971488
chain 10 (page 9): 239982816 → 239988480 → 239985648
chain 11 (page 10):240008304 → 239996976 → 240002640
chain 12 (page 11):240022464 → 240016800 → 240019632
chain 13 (page 12):250028736 → 250017408 → 250023072
chain 14 (page 12):250040064 → 250037232 → 250034400
```

The converter must (a) detect each chain by walking BACKITEM=-1 → NEXTITEM, (b) emit them as a typed DSL chain — see Gap §2.5 below — (c) the DSL emitter must allocate ItemIDs in chain order so the NEXTITEM/BACKITEM links resolve.

**Soft-hyphens (`\xad`):** **0 occurrences.** (The Zeitung uses Scribus's hyphenation engine, not pre-baked soft-hyphens.)

**HYPHEN/EXCEPTION:** absent.

**ITEXT runs (453):**
- **183 with `FONTSIZE` override** (heaviest in the doc — body text with mid-paragraph size shifts)
- **20 with `FCOLOR` override**
- **11 with `FSHADE` override**
- **11 with `FONT` override**
- **10 with `FEATURES`**

**StoryText element types:** `DefaultStyle`(90), `ITEXT`(453), `para`(421), `breakline`(6), `trail`(40), **`var`(12)** — page-number placeholders `<var name="pgno"/>`.

**Sections (1):** `Number=0 From=0 To=13 Type=Type_1_2_3 Start=1`.

**PAGEOBJECT exotic attrs:**
- `fillRule` (path winding rule, evenodd vs nonzero) on **86 frames** — every FRTYPE=3 polygon. Always `fillRule="0"` (nonzero). DSL gap, but trivially fixed: emit `fillRule="0"` for all FRTYPE=3.
- `ANNAME` populated on 85 of 140 frames (auto-IDs like `u2950`, `u29b9`, etc., plus copies `'Kopie von ...'`).
- `ALIGN` (vertical text alignment) on 4 PTYPE=4 frames (values 1, 3, 3, 3) — DSL gap; primitives emit `VAlign="0"` always but never `ALIGN` on PAGEOBJECT.
- `ROT` non-zero on 4 frames: 90°, 270°, 355°, 355°. Already supported via `rotation_deg`.
- `SHADE` on 1 frame (Polygon).
- `<var name="pgno"/>` (page-number variable) — DSL has zero support for variables.
- No `HASSOFTSHADOW`, no `RADRECT`, no `isInlineImage` is wrong — actually 6 inline images. Recheck: `isInlineImage="1"` count = 6 (small bullets / glyphs).

**Per-page para-style references (DefaultStyle inside PAGEOBJECT/StoryText):** 90 occurrences across 112 PTYPE=4 frames. The bulk reference `Fließtext`, `[No paragraph style]`, `Bildunterschrift weiß`, `Überschrift weiß`, etc. — the document-local style names, never `ci/...`.

## DSL gap analysis

Each gap below proposes the smallest typed addition that closes it. All proposals stay inside CONTEXT.md D2 (typed primitives only, no `raw_attrs`). Where an attribute is rare (e.g. soft-shadow = 1 occurrence, RADRECT = 4 occurrences), the proposal is still typed — D6 strict mode means the converter must raise on any unhandled element, so we cannot ignore the rare attributes.

### 1. Document-level

#### 1.1 Per-document layer override
**Gap:** DSL hard-codes the 4-layer stack (`Hintergrund`/`Bilder`/`Text`/`Hilfslinien`) loaded from `shared/ci.yml`. The originals have a single `Hintergrund` (Postkarte/Plakat) or `Ebene 1` (Zeitung) layer.
**Proposal:** Add `Document(layers=...)` that, when set, overrides the CI-loaded layer stack. Type:
```python
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

class Document:
    def __init__(self, ..., layers: list[DocumentLayer] | None = None): ...
```
Where to wire: `_emit_layers()` in `document.py:402` reads `self.ci.layers`; add a `self._layers_override` and emit those instead when set. The default 4-layer stack stays for greenfield templates.

#### 1.2 Per-document custom colors
**Gap:** No way to register a one-off color (e.g. `Green`) without polluting `shared/ci.yml`. The originals all carry a `Green` color with file-specific RGB.
**Proposal:**
```python
class Document:
    def add_color(self, name: str, *, rgb: tuple[int,int,int] | None = None,
                  cmyk: tuple[int,int,int,int] | None = None,
                  spot: bool = False, register: bool = False) -> None: ...
```
Stored on `self._extra_colors: dict[str, BrandColor]`; emitted in `_emit_colors()` after the CI-loaded colors. `BrandColor` already supports both CMYK and (via the property) RGB; we'd add an RGB-native variant by adding `rgb: tuple|None = None` and emitting `SPACE="RGB"` when set.

#### 1.3 Per-document paragraph & character styles
**Gap:** DSL only emits the 8 CI styles (`ci/default`, `ci/headline-ultra`, ...). Each original defines its own (Postkarte: 9, Plakat: 5, Zeitung: 23). The Zeitung uses 31 distinct STYLE attribute names (FONTFEATURES, NACH, VOR, DROP, etc.).
**Proposal:**
```python
@dataclass(frozen=True)
class ParaStyle:
    name: str
    font: str | None = None
    fontsize: float | None = None
    fcolor: str | None = None
    align: int | None = None
    parent: str | None = None
    linesp: float | None = None
    linesp_mode: int | None = None        # LINESPMode 0/1/2
    language: str | None = None
    # Paragraph spacing
    space_before_pt: float | None = None  # VOR
    space_after_pt: float | None = None   # NACH
    # Indent
    first_indent_pt: float | None = None  # FIRST
    left_indent_pt: float | None = None   # INDENT
    right_indent_pt: float | None = None  # RMARGIN
    # Hyphenation
    hyph_consecutive_lines: int | None = None
    hyph_word_min: int | None = None
    # Drop cap
    drop_cap: bool | None = None          # DROP
    drop_lines: int | None = None         # DROPLIN
    # Tracking
    min_word_track: float | None = None
    min_glyph_shrink: float | None = None
    max_glyph_extend: float | None = None
    # Keep
    keep_together: bool | None = None
    keep_lines_start: int | None = None
    # Direction (RTL support)
    direction: int | None = None
    # Background
    bcolor: str | None = None             # BCOLOR
    bshade: int | None = None             # BSHADE
    # Char-style passthrough on the para's default char style
    fontfeatures: str | None = None
    features: str | None = None           # space-joined char features
    kern: float | None = None
    scalev: float | None = None           # SCALEV
    fshade: int | None = None
    # Marks the paragraph as "this is the document's default style"
    is_default: bool = False

@dataclass(frozen=True)
class CharStyle:
    name: str               # CNAME
    font: str | None = None
    fontsize: float | None = None
    fcolor: str | None = None
    is_default: bool = False

class Document:
    def add_para_style(self, style: ParaStyle) -> None: ...
    def add_char_style(self, style: CharStyle) -> None: ...
```
**Inheritance discipline:** `_emit_styles()` only emits attributes that are **not None** (per `.research/01-sla-format.md` §4: implicit-by-absence). The current `_emit_styles()` re-emits every default; that's already wrong for inheritance and must be fixed regardless.

#### 1.4 Document attributes: facing pages, custom margins, alternative defaults
**Gap:** `Document` doesn't expose `facing=True` directly; `facing_pages` is a public attribute set after construction. Bleed-on-document is hard-coded to use the first page's bleed value. ABSTSPALTEN is hard-coded to "11"; the Zeitung has "12".
**Proposal:**
```python
class Document:
    def __init__(self, ..., facing_pages: bool = False,
                 column_gap_default_pt: float = 11.0,
                 unit: str = "mm",                # 1 = mm; could be "pt" for 0
                 deffont: str = "Gotham Narrow Book",
                 defsize: float = 12,
                 first_page_num: int = 1) -> None: ...
```

#### 1.5 Page label suppression
**Gap:** DSL emits a magenta `BEISPIELSEITE — <label>` text frame on the Hilfslinien layer when `label` is set (`document.py:254-264`). The originals have no such frame.
**Proposal:** Treat `label=""` as suppression (already the case if not set); converter never sets `label`. No DSL change required, just discipline.

### 2. Frame-level

#### 2.1 Per-run text formatting (CharStyle inline overrides)
**Gap:** Current `TextFrame.runs` accepts a tuple `(text, override_dict, separator)` but only `fcolor` and `fontsize` are wired (`primitives.py:152-158`). The Zeitung needs `font`, `fshade`, `features`, `kern`, `fontfeatures` per-run.
**Proposal:** Replace the loose tuple with a typed `Run`:
```python
@dataclass(frozen=True)
class Run:
    text: str
    font: str | None = None
    fontsize: float | None = None
    fcolor: str | None = None
    fshade: int | None = None
    fontfeatures: str | None = None
    features: str | None = None       # space-joined: "inherit smallcaps superscript"
    kern: float | None = None
    underline_position: int | None = None  # TXTULP
    strike_position: int | None = None     # TXTSTP
    char_style: str | None = None     # CPARENT
    # Separator placed AFTER this run (before the next):
    separator: str | None = None      # None, "para", "breakline", "tab", "breakcol", "breakframe"
    # Non-text inserts after the separator; e.g. var:
    var: str | None = None            # "pgno" → emits <var name="pgno"/>
```
Then `TextFrame.runs: list[Run]`.

The current `(text, dict, separator)` tuple shape is preserved by accepting either form for migration; converter only emits `Run(...)`.

#### 2.2 Soft-hyphen passthrough
**Gap:** `TextFrame.text` and `Run.text` currently accept any string; the question is whether intermediate processing strips `\xad`. Looking at `primitives.py:165` (`it.set("CH", self.text)`), the answer is no — lxml passes the string through. **No code change needed**, but a regression test must lock in: round-trip a string with embedded `\xad` and assert the emitted SLA still contains it.

#### 2.3 `<var name="pgno"/>` page-number variable
**Gap:** The Zeitung has 12 `<var name="pgno"/>` elements inside StoryText. DSL emits no `<var>`.
**Proposal:** `Run(var="pgno")` (above) emits `<var name="pgno"/>` after the text run; alternatively a top-level helper:
```python
@dataclass(frozen=True)
class PageNumberVar:
    """Inserts <var name='pgno'/> at this position in a TextFrame's run list."""
```
Recommend the `Run.var` approach — keeps the run list flat.

#### 2.4 Custom path / FRTYPE=3 support
**Gap:** All Polygon and most Zeitung text frames use `FRTYPE=3` with explicit `path=` data. DSL emits `FRTYPE=0` (rect) or `FRTYPE=1` (ellipse) with computed paths only.
**Proposal:** Add `path` parameter to TextFrame/ImageFrame/Polygon (single Frame mixin):
```python
@dataclass
class _Frame:
    ...
    custom_path: str | None = None   # SVG-ish path string. When set, FRTYPE=3 and
                                     # `path`/`copath` attrs are this verbatim,
                                     # WIDTH/HEIGHT still serialise the bbox.
    fill_rule: int | None = None     # fillRule attribute (0 = nonzero, 1 = evenodd)
```
For the 86 trivial-rectangle FRTYPE=3 cases in the Zeitung, the converter emits `custom_path="M0 0 L0 H L W H L W 0 L0 0 Z"` (the verbatim path from the original) so sla_diff sees byte-equal `path` strings.

#### 2.5 Linked text-frame chains (NEXTITEM/BACKITEM)
**Gap:** Completely missing today. Every TextFrame emits `NEXTITEM=-1 BACKITEM=-1`. Zeitung has 14 chains.
**Proposal:** Two coupling mechanisms:

```python
class TextFrame(_Frame):
    next_item: TextFrame | None = None  # set after construction
    # BACKITEM is computed from the inverse mapping at emit time

# Sugar:
class TextFrame:
    def link_to(self, other: "TextFrame") -> "TextFrame":
        """Chain self → other. Returns other for fluent chaining."""
        self.next_item = other
        return other
```

ItemID assignment becomes order-dependent: pre-walk all frames, build the chain graph, allocate IDs depth-first per chain so NEXTITEM points at an already-allocated ID. Emit BACKITEM = previous chain member's ID.

Wire into `Document._build_xml()`:
```python
# Pre-pass: assign ItemIDs in chain order
for page in self.pages:
    for item in page.items:
        if isinstance(item, TextFrame):
            if item.next_item is not None:
                # Walk chain to head, then allocate IDs in order
                ...
```

`tools/sla_lib/builder/document.py:_emit_page_item` currently calls `item.to_pageobject(self._idgen, page)` — that's where ItemID is allocated. Need to pre-allocate so the to_pageobject calls receive the assigned ID (e.g. via `idgen.peek_for(item)` or by pre-storing on the item).

#### 2.6 Rounded-rectangle frames (FRTYPE=2 / RADRECT)
**Gap:** 4 PTYPE=2 frames in the Postkarte have `RADRECT="2.83464566929134"` (1mm corner radius) and `FRTYPE=2`, with a bezier path describing the rounded rectangle.
**Proposal:** Add `corner_radius_mm: float = 0` to `_Frame` (or just to ImageFrame and Polygon). When > 0:
- Emit `FRTYPE=2`
- Emit `RADRECT="{corner_radius_pt:.6f}"`
- Emit a generated bezier-rounded-rect path (Scribus regenerates it on next save anyway, so an approximate path is fine — but for sla_diff, the converter must emit the exact path string the original carries, so the converter passes the original `path=` through verbatim using `custom_path=`).

#### 2.7 Soft-shadow on text frame
**Gap:** 1 frame in Postkarte has `HASSOFTSHADOW="1"` plus 9 `SOFTSHADOW*` attrs. Strict mode means we can't ignore it.
**Proposal:** Add an optional dataclass attribute group to `_Frame`:
```python
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

@dataclass
class _Frame:
    ...
    soft_shadow: SoftShadow | None = None
```
Emit all `SOFTSHADOW*` attrs only when `soft_shadow is not None`; HASSOFTSHADOW="1".

#### 2.8 Inline embedded images (`isInlineImage=1`, `ImageData=<base64>`)
**Gap:** 7 frames in Postkarte, 2 in Plakat, 6 in Zeitung have inline-embedded PNG data (base64-of-qCompress, NOT raw deflate — Qt prepends a 4-byte big-endian length, per `.research/01-sla-format.md` §5).
**Proposal — option A (preferred):** the converter extracts the embedded bytes, qDecompresses (length prefix + zlib decompress), writes a sidecar PNG file under `templates/<id>/assets/inline-N.png`, and emits `ImageFrame(src="assets/inline-N.png", ...)`. This is **lossless** (the same PNG bytes round-trip via PFILE) and aligns with CONTEXT.md's spirit of "no embedded blobs in DSL".
**Proposal — option B (fallback):** add `ImageFrame(inline_data: bytes | None = None, inline_ext: str = "png")`. The DSL re-encodes via qCompress + base64 at emit time. Requires implementing Qt's qCompress (4-byte big-endian length prefix + zlib deflate level 9). Doable in ~10 LOC, but option A is simpler.

**Recommend option A.** sla_diff has to be lenient about ImageData (since round-tripping bytes is fragile across zlib levels) — compare semantic equivalence: same decoded PNG bytes (or same SHA256 of decompressed content), not byte-equal compressed strings.

#### 2.9 ALIGN attribute on PAGEOBJECT (vertical text alignment)
**Gap:** 4 PTYPE=4 frames in the Zeitung carry `ALIGN="1"` or `ALIGN="3"`. DSL emits `VAlign="0"` always, never `ALIGN`.

Actually `ALIGN` on a PAGEOBJECT is the **horizontal text alignment** override (VAlign is vertical). Need to confirm via Scribus source. Per `.research/01-sla-format.md` §2 "PAGEOBJECT attribute coverage" doesn't enumerate ALIGN explicitly; the Zeitung's only 4 occurrences are on linked-chain text frames. Since strict mode forbids ignoring it: **add `text_align: int | None = None` to TextFrame**, emit as ALIGN attribute when set.

#### 2.10 SHADE on Polygon
**Gap:** 1 polygon in the Zeitung has `SHADE` (color shade percentage 0-100).
**Proposal:** Add `fill_shade: int = 100` to Polygon; emit `SHADE` only when != 100.

#### 2.11 LANGUAGE on STYLE only sometimes
**Gap:** Current `_emit_styles()` always emits `LANGUAGE=de`. The Zeitung's `Default Paragraph Style` does NOT have LANGUAGE; only 13 of 23 styles do.
**Proposal:** Honor `ParaStyle.language is None` → don't emit. Already implied by §1.3 above.

### 3. PageSets / Sections
**No gap** — DSL emits exactly the 4 standard sets and 1 default section, identical to all originals. Only verify that `Section.From`/`Section.To` honour the actual page count (current code does: `_emit_sections` uses `len(self.pages) - 1`).

### 4. AUTOSPALTEN / ABSTSPALTEN
**Minor gap:** DSL hard-codes ABSTSPALTEN=11. Zeitung uses 12. Trivial fix via `Document(column_gap_default_pt=12)`.

### 5. ScratchTop/ScratchLeft normalisation
**Not a gap** — Scribus normalises these on next save. sla_diff must ignore them (they're scratch-canvas position and cannot be made stable). Document this in sla_diff's normalisation rules.

## sla_diff strategy

### Normalisation pipeline (run on BOTH sides before comparison)

1. **Parse with lxml** preserving attribute order and text (`XMLParser(remove_blank_text=False, strip_cdata=False)`).
2. **Strip volatile attributes** at the document level: `DOCSAVED`, `DOCDATE`, autosave timestamps if any, `currentProfile`.
3. **Renumber ItemIDs sequentially**:
   - Walk all PAGEOBJECTs, MASTEROBJECTs, FRAMEOBJECTs in document order
   - Assign IDs starting at 100_000_000 (matches DSL convention)
   - Update every NEXTITEM/BACKITEM/WeldSource/WeldID reference in lockstep using the old→new mapping
4. **Sort PAGEOBJECTs** by `(int(OwnPage), float(YPOS), float(XPOS))`. MASTEROBJECTs sort by `(OnMasterPage, YPOS, XPOS)`. FRAMEOBJECTs are dropped before comparison (orphaned scratch items, see Postkarte/Plakat/Zeitung inventory).
5. **Round all floating-point numeric attributes to 6 decimals**: walk every `<*>` node, every `attrib[k]`; if `re.match(r'^-?\d+\.\d+$', v)`, replace with `f"{float(v):.6f}"`. Path data (`path=`/`copath=` strings) parsed and per-coordinate rounded.
6. **Sort attributes alphabetically** within every element. (lxml preserves insertion order; sort by serialising via `sorted(elem.attrib.items())` in the diff comparator.)
7. **Drop attributes with default values** that the DSL might or might not emit:
   - `LOCALSCX/LOCALSCY=1`, `LOCALX/LOCALY=0`, `LOCALROT=0`
   - `SCALETYPE=1`, `RATIO=1`, `PICART=1`
   - `ROT=0`
   - `NEXTITEM=-1`, `BACKITEM=-1`
   - `LINESPMode=2` (default), `LINESP=15` (default)
   - `gXpos/gYpos = XPOS/YPOS`, `gWidth=0`, `gHeight=0` (when not in a group)
8. **Strip purely-volatile fields:** `PAGEXPOS/PAGEYPOS` (scratch-canvas position, normalised by Scribus on save).
9. **Coordinate normalisation for items:** convert XPOS/YPOS from scratch-space to **page-local** by subtracting the owning page's PAGEXPOS/PAGEYPOS — this neutralises any scratch-canvas drift.
10. **Sort COLOR/STYLE/CHARSTYLE/LAYERS** lists by NAME.

### Severity rules

| Severity | Rule |
|---|---|
| **critical** | ANZPAGES differs; PAGEWIDTH/PAGEHEIGHT differ by > 0.01 pt; bleed differs; missing PAGE element; missing MASTERPAGE referenced from a PAGE's MNAM; PAGEOBJECT count per OwnPage differs; PTYPE differs for matched item; FRTYPE differs (after rectangle-equivalence rule, see below); chain topology differs (different head→tail by structural hash) |
| **warning** | XPOS/YPOS drift > 0.5 pt after page-local normalisation; WIDTH/HEIGHT drift > 0.5 pt; FONTSIZE drift > 0.5 pt on STYLE or ITEXT; FCOLOR mismatch; PCOLOR mismatch on Polygon; ROT differs by > 0.5°; missing/extra COLOR; missing/extra STYLE; LAYER ID differs |
| **info** | ItemID literal value differs (after renumbering, this should be silent — info if it surfaces); ANNAME differs; gXpos/gYpos differ but XPOS/YPOS match; auto-attributes (CLIPEDIT, PLINEART, PWIDTH=0, etc.) differ in default-equivalent ways; FRAMEOBJECT counts differ (orphan-scratch, ignored); PageSets differ in default contents |

### Rectangle-equivalence rule
A frame is "rectangular" if its `path=` matches one of:
- `M0 0 L<W> 0 L<W> <H> L0 <H> L0 0 Z` (CW-from-origin)
- `M0 0 L0 <H> L<W> <H> L<W> 0 L0 0 Z` (CCW-from-origin)

If both sides are rectangular AND `(WIDTH, HEIGHT)` match within 6-decimal tolerance, treat FRTYPE differences (0 vs 3) as **info**, not warning. This handles the Zeitung's FRTYPE=3 trivial rectangles vs DSL's FRTYPE=0 rectangles. (Even better: the converter emits FRTYPE=3 with the verbatim path, which sidesteps this rule entirely. The rule is a safety net.)

### Linked-chain comparison
For each chain (sequence of PAGEOBJECTs linked by NEXTITEM/BACKITEM):
1. Compute "chain hash" = SHA256 of the concatenation of `(OwnPage, normalised XPOS, normalised YPOS, WIDTH, HEIGHT)` for each member, in order from BACKITEM=-1 head to NEXTITEM=-1 tail.
2. Match chains across sides by (a) head OwnPage, (b) chain length, (c) chain hash.
3. Mismatched chains → critical.

### Output formats
- **JSON** (machine-readable, for CI consumption):
```json
{
  "left": "postkarte-vorlage-original.sla",
  "right": "templates/postkarte-a6-kampagne/template.sla",
  "summary": {"critical": 0, "warning": 2, "info": 5},
  "issues": [
    {"severity":"warning","code":"position-drift",
     "path":"DOCUMENT/PAGEOBJECT[0]","attr":"YPOS",
     "left":"58.27","right":"58.84","detail":"|delta| = 0.57pt > 0.5pt"},
    ...
  ]
}
```
- **Markdown** (human-readable, for git review). Use the same shape as `tools/check_ci.py:format_report_text`. Group by severity.
- **Exit code:** 0 iff no critical AND no warning. (`--strict` flag = exit 1 on warning.)

### Dependencies
- Existing `tools/sla_lib/reader.py` (parse), `lxml` (already a dep).
- Mirror `Issue`/`CIDriftReport` dataclass shape from `tools/check_ci.py` for consistency.

## visual_diff strategy

### Tool selection (verified locally)
| Tool | Available locally | Purpose | Recommendation |
|---|---|---|---|
| ImageMagick `compare` | yes (6.9.11-60) | Per-pixel diff metric | **Use** |
| ImageMagick `montage` | yes | Side-by-side composite | **Use** |
| `odiff` | **NOT installed** | Faster alternative pixel-diff | Skip — adding a new dep is out of CONTEXT.md scope; ImageMagick is sufficient at our 1% tolerance |
| `pdftoppm` (Poppler) | yes (22.12.0) | PDF → PNG rasterisation | **Use** (preferred — Poppler renders cleanly with crisp font hinting) |
| Ghostscript `gs` | yes (10.05.1) | Alternative PDF → PNG | Fallback only |
| Scribus 1.6.5 + Xvfb | yes (system path) | SLA → PDF | Already wired in `tools/render.py` |

Recommend **pdftoppm over Ghostscript** because: (a) Poppler's antialiasing matches Scribus's expectations more cleanly, (b) it's already used in `tools/gallery_build.py` for thumbnails (consistency), (c) `gs` font rendering can drift between releases.

### Pipeline
```
1. Render DSL build:    xvfb-run -a scribus -g -ns -py tools/_export_pdf.py \
                          templates/<id>/template.sla \
                          build/<id>/dsl.pdf

2. Reference PDF:        templates/<id>/baseline.pdf  (committed, frozen — D3)

3. Rasterise both:       pdftoppm -r {DPI} -png templates/<id>/baseline.pdf  build/<id>/baseline-page
                          pdftoppm -r {DPI} -png build/<id>/dsl.pdf            build/<id>/dsl-page

4. Per-page compare:     for each page N:
                            compare -metric AE -fuzz 2% \
                              build/<id>/baseline-page-{N}.png \
                              build/<id>/dsl-page-{N}.png \
                              build/<id>/diff-page-{N}.png 2> mismatch.txt
                          # AE = absolute error pixel count; fuzz = per-pixel
                          # tolerance for color noise (sub-pixel jitter)
                          mismatch_pct = mismatch_pixels / total_pixels

5. Side-by-side report:  montage \
                              build/<id>/baseline-page-{N}.png \
                              build/<id>/dsl-page-{N}.png \
                              build/<id>/diff-page-{N}.png \
                              -tile 3x1 -geometry +4+4 \
                              build/<id>/composite-page-{N}.png

6. Threshold:            fail if any page's mismatch_pct > tolerance (default 1%)
```

DPI per CONTEXT.md D4: `--dpi 96` in CI, `--dpi 150` locally. CLI flag location: `tools/visual_diff.py --dpi {N}` with a `--ci` shortcut → 96.

### Per-template tolerance config (`templates/<id>/diff.yml`)
```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0       # global default
  fuzz_pct: 2                       # ImageMagick -fuzz (color tolerance)
  per_page:
    - page: 0
      max_pixel_mismatch_pct: 0.5   # tighter for cover page
  per_region:                       # optional rectangular regions in mm
    - page: 1
      bbox_mm: { x: 10, y: 100, w: 50, h: 60 }
      max_pixel_mismatch_pct: 5.0   # body-text region — laxer
```
Schema parsed by `visual_diff.py`; if file missing, defaults apply.

### Rebaselining workflow (README excerpt)
```
When the original SLA, Scribus version, or fonts change intentionally:

  1. rm templates/<id>/baseline.pdf
  2. xvfb-run -a scribus -g -ns -py tools/_export_pdf.py \
        <original-or-current>.sla templates/<id>/baseline.pdf
  3. Visually verify the regenerated baseline.pdf is what you expect
     (open it in a PDF viewer and confirm).
  4. git add templates/<id>/baseline.pdf
  5. git commit -m "rebaseline <id>: <reason>"
```
Mark the baseline file as binary in `.gitattributes` (`*.pdf binary`) to keep diff noise down.

### Output
- Per-template JSON report at `build/<id>/visual_diff.json`
- Per-template HTML index at `build/<id>/visual_diff.html` linking the composite PNGs (helpful when reviewing PRs locally)
- CI prints summary + uploads `composite-page-*.png` as artifacts on failure (so reviewers can see the delta in the failed CI job's artifacts tab)

## CI integration

### New workflow step in `.github/workflows/pages.yml`

Insert between the "Run unit tests" step and the "Run brand validator" step (or replace the brand validator step entirely with a stronger one):

```yaml
- name: Validate reproductions (sla_diff + visual_diff)
  run: |
    set -e
    for tdir in templates/postkarte-a6-kampagne templates/plakat-event templates/zeitung-a4-grun; do
      tid=$(basename "$tdir")
      original=$(ls "$(dirname "$tdir")"/../*"-original.sla" \
                 | grep -E "(postkarte|plakat-a1|zeitung)" | head -1)
      # Or, more robustly, embed the mapping in templates/<id>/meta.yml
      # via a `original_sla:` key.
      python3 tools/sla_diff.py \
        --left "$original" --right "$tdir/template.sla" \
        --json --out build/$tid/sla_diff.json
      python3 tools/visual_diff.py \
        "$tdir/template.sla" \
        --baseline "$tdir/baseline.pdf" \
        --dpi 96 \
        --tolerance "$tdir/diff.yml" \
        --out build/$tid/
    done
```

Mapping `templates/<id>` → original SLA file: store the mapping in each `templates/<id>/meta.yml` as a new `original_sla:` key (e.g. `original_sla: ../../postkarte-vorlage-original.sla`). The converter and validator both consume this.

### Job dependencies
- `build` job: keeps current sequence; appends `Validate reproductions` AFTER `Run unit tests` and BEFORE `actions/upload-pages-artifact`.
- `deploy` job already declares `needs: build`, so a failed validation step fails the entire build job and short-circuits deploy. ✓

### Caching
- **Scribus AppImage**: `actions/cache` keyed by `SCRIBUS_VERSION`, restore path `/opt/squashfs-root`. Saves ~30s install on every run.
- **Fonts**: not currently bundled (CONTEXT.md says "no font/ICC changes"). System fonts only. Cache the apt downloads (`apt-cache` action) if needed.
- **Baseline PDFs**: committed in repo (D3), no caching needed.
- **Per-page rasters**: not cached — quick to regenerate from frozen PDFs.

### Triggers
Per CONTEXT.md D4: every push to main, every PR touching `tools/`, `templates/`, `shared/`. Add path filters:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    paths:
      - 'tools/**'
      - 'templates/**'
      - 'shared/**'
      - '.github/workflows/pages.yml'
  workflow_dispatch:
```

(Currently only `push: main` and `workflow_dispatch` are wired — PRs go ungated.)

### Runtime budget
- Scribus AppImage install (cached): ~5s
- DSL build all 3 templates: ~3s
- Render 3 SLAs to PDF: ~30s (Scribus is slow; Zeitung's 14 pages dominates)
- pdftoppm at 96 dpi: ~5s for 17 pages total (2+1+14)
- ImageMagick compare: ~2s × 17 = ~30s
- sla_diff: ~2s × 3 = ~6s

Total: ~80s. Well under the 5-minute D4 budget.

## Sequencing and risk-ordered approach

Recommended ordering reframes the issue's "do reproductions and validate" into "build validators first, use them as the test loop while iterating on converter+DSL":

### Phase 0 — Foundation: sla_diff (target: 1 day)
**Why first:** Without sla_diff, the converter has no go/no-go signal. Building it first means every converter iteration produces a measurable score. It's also the lowest-risk component (pure XML normalisation, no Scribus invocation).
1. Implement `tools/sla_diff.py` with the normalisation pipeline above.
2. Unit-test on synthetic SLAs (one per severity rule).
3. Lock in the rectangle-equivalence rule and chain-hash comparison.
4. Sanity check: run sla_diff on each original against itself (must be clean).
5. **Output:** working `sla_diff.py` + tests.

### Phase 1 — DSL extensions (target: 2 days)
**Why before converter:** The converter needs typed APIs to call. Build the DSL extensions in dependency order: per-document styles (1.3) and colors (1.2) first (the converter's first action is emitting `Document.add_color`/`add_para_style` for everything in the original), then per-run formatting (2.1) and var (2.3), then linked chains (2.5), then the long tail (custom path 2.4, RADRECT 2.6, soft-shadow 2.7, ALIGN 2.9, SHADE 2.10).
1. Add `ParaStyle`, `CharStyle`, `Document.add_para_style/add_char_style/add_color/layers=` (gaps 1.1-1.3).
2. Add `Run` typed dataclass; rewire `TextFrame.runs` (gap 2.1).
3. Add `custom_path` and `fill_rule` on `_Frame` (gap 2.4).
4. Add `link_to()` on `TextFrame` + ID pre-allocation (gap 2.5).
5. Add `corner_radius_mm`, `soft_shadow`, `text_align`, `fill_shade` (gaps 2.6-2.10).
6. Soft-hyphen pass-through regression test (gap 2.2).
7. Page-number var (gap 2.3).
8. **Output:** extended DSL + unit tests covering each new typed API.

### Phase 2 — Converter for Postkarte (target: 1 day)
**Why Postkarte first:** Smallest (18 frames, 2 pages, no chains, no var, no facing). Surfaces gaps in DSL via D6 strict mode.
1. Implement `tools/sla_to_dsl.py` skeleton: parses SLA via `SLADocument`, emits a `build.py` script.
2. Iteratively run on Postkarte; each `UnhandledElement` raise drives a DSL extension OR converter dispatch fix.
3. Run `sla_diff` on output until clean.
4. Render → commit `templates/postkarte-a6-kampagne/baseline.pdf`. Replace placeholder `build.py`.
5. **Output:** Postkarte reproduction with clean sla_diff, baseline.pdf locked in.

### Phase 3 — Converter extensions for Plakat A1 (target: 0.5 day)
1. Run converter on Plakat. Likely surfaces: soft-hyphen handling needs verification (7 occurrences), 90° rotation (already supported), no new structural elements.
2. Clean sla_diff.
3. Commit `templates/plakat-event/baseline.pdf`.
4. **Output:** Plakat reproduction.

### Phase 4 — Converter extensions for Zeitung (target: 2-3 days, the long tail)
1. Run converter on Zeitung. Surfaces: 23 paragraph styles with 31 distinct attributes, 14 linked chains, 12 page-number vars, 86 FRTYPE=3 paths, fillRule, ALIGN-on-PAGEOBJECT, multi-master setup, facing-pages.
2. Each new gap → DSL extension (most are covered by Phase 1 if it was thorough) → re-run.
3. Clean sla_diff.
4. Commit `templates/zeitung-a4-grun/baseline.pdf`.
5. **Output:** Zeitung reproduction.

### Phase 5 — visual_diff (target: 1 day)
**Why last:** The expensive validator. By Phase 5, all three templates have clean sla_diffs and committed baseline PDFs; visual_diff's only job is to detect rendering drift in CI. Building it earlier wouldn't have given useful signal because the converter wasn't producing renderable SLAs yet.
1. Implement `tools/visual_diff.py` with the pdftoppm + compare + montage pipeline.
2. Per-template `diff.yml` tolerance config.
3. Run on all three templates, tune tolerances.
4. **Output:** working `visual_diff.py` + tolerances locked in.

### Phase 6 — CI integration (target: 0.5 day)
1. Add `validate-reproductions` step to `.github/workflows/pages.yml`.
2. Cache Scribus AppImage.
3. Add path-filtered PR triggers.
4. Verify under 5-minute budget.
5. README: round-trip validation section + rebaselining workflow.
6. **Output:** green CI on main with the new gate.

### Why NOT visual_diff first
Considered. Counter-argument: visual_diff alone gives a single number (mismatch %); without sla_diff, debugging "why does the rendered PDF look slightly different" reduces to staring at PNG deltas. sla_diff gives structural reasons ("WIDTH differs by 0.7pt on PAGEOBJECT[3]") that map directly to converter or DSL bugs. So sla_diff first is correct.

### Alternative ordering (if Phase 1 explodes)
If extending the DSL turns out to be a multi-week effort (e.g. linked chains require restructuring `_IdGen` or the emission order), an interim mode worth considering:
- **Interim mode** (NOT in current scope): converter accepts an internal `raw_attrs` dict for unhandled attrs, emits via a private `RawFrame` class. This violates D2's letter but lets us keep moving while DSL extensions land. The reproductions would temporarily ship with `raw_attrs=...` calls in `build.py`, scrubbed once the typed APIs catch up. **This is explicitly out of scope per D2** — flagging only as a fallback if Phase 1 estimates are wildly off.

## Common Pitfalls

### Pitfall: Soft-hyphen stripping in intermediate processing
**What goes wrong:** A `\xad` in source text gets removed by string normalisation (e.g. unicodedata.normalize, str.strip, regex `\W` removal).
**Why it happens:** Python str methods don't touch `\xad` by default, but lxml's CDATA handling, file-encoding round-trips, or downstream LLM/template renderers can strip them.
**How to avoid:** End-to-end regression test: read Plakat's "ei\xadne" snippet, round-trip through reader→builder→file, assert the emitted SLA bytes still contain `'ei\xadne'`. In sla_diff, treat soft-hyphen presence as critical — they materially affect line breaks.
**Warning signs:** Plakat's hyphenation looks visibly different in the rendered PDF (long words now break in different places).

### Pitfall: ItemID renumbering breaks linked chains
**What goes wrong:** The converter renumbers ItemIDs in document order, but a NEXTITEM points at the OLD ID of the next chain member, which has now been renumbered.
**Why it happens:** The Zeitung's 14 chains have NEXTITEM pointing at IDs the converter is rewriting. Without lockstep updates, the chain breaks.
**How to avoid:** Build a `old_id → new_id` map during the renumber pass. THEN walk all NEXTITEM/BACKITEM/WeldSource/WeldID values and remap. Test: run converter on Zeitung, assert all 14 chains are intact (each chain head's NEXTITEM points at a frame whose BACKITEM points back, and so on).
**Warning signs:** Visual diff on the Zeitung shows article text spilling off page boundaries or duplicating.

### Pitfall: STYLE inheritance silently broken
**What goes wrong:** DSL re-emits every attribute on every STYLE, overriding parent inheritance. The originals only emit attributes that differ from parent.
**Why it happens:** `_emit_styles()` in `document.py:375-394` reads from `BrandStyle` (which has all required fields) and emits unconditionally. The new `ParaStyle` dataclass has `Optional` fields, but the emitter must respect None-vs-default.
**How to avoid:** When emitting a `ParaStyle`, only set the attribute if the value is non-None. For `parent` chains, never emit a value equal to the parent's value (per `.research/01-sla-format.md` §4 inheritance rules). Test: define a `ParaStyle(name="child", parent="parent_name", fontsize=None)` and a `ParaStyle(name="parent_name", fontsize=12)`. Emit. Assert the child STYLE has NO `FONTSIZE` attribute (inheritance applies).
**Warning signs:** sla_diff reports STYLE attributes appearing in the DSL output that aren't in the original.

### Pitfall: lxml attribute order non-determinism on emit
**What goes wrong:** `etree.tostring(... pretty_print=True)` re-serialises attributes in insertion order. If the DSL emits attrs in a different order than the original, byte-equality fails (which is fine — D1 says we don't compare bytes), but it makes manual review of git diffs noisy.
**How to avoid:** Document the chosen order. Optionally post-process the emitted SLA to alphabetise attribute order on every element (then the same diff-friendly ordering is used for both the original and the DSL output). Match Scribus's writer order: it follows `scribus150format_save.cpp::SetItemProps` which has its own deterministic order. For our purposes, alphabetical is simpler and "diffable enough".
**Warning signs:** `git diff templates/<id>/template.sla` after running the build shows attribute reordering noise.

### Pitfall: Embedded PNG round-trip drift
**What goes wrong:** Converter extracts inline image to PNG file; DSL re-encodes via PFILE; sla_diff sees PFILE differs (plus ImageData absent on DSL side) and flags critical.
**How to avoid:** sla_diff treats `isInlineImage="1"` + ImageData on one side and `PFILE` referencing same-bytes PNG on the other side as equivalent (compare decoded image SHA256). OR simpler: drop ImageData/isInlineImage entirely from comparison (info only); compare PFILE filenames as strings.
**Warning signs:** `visual_diff` is clean but `sla_diff` reports critical "extra ImageData attribute".

### Pitfall: Scratch-canvas position drift
**What goes wrong:** Scribus normalises PAGEXPOS/PAGEYPOS on every save based on its current page-set rules. Two equivalent SLAs can have different PAGEXPOS/YPOS after a round-trip.
**How to avoid:** sla_diff strips PAGEXPOS/PAGEYPOS from PAGE/MASTERPAGE. Item XPOS/YPOS are normalised to page-local before comparison.
**Warning signs:** Every page reports PAGEXPOS/YPOS warnings, masking real drift.

### Pitfall: D6 strict converter blocks itself on a frame the DSL will never need
**What goes wrong:** Strict mode raises on, say, the 1 soft-shadow in Postkarte. We add the typed `SoftShadow` dataclass (gap 2.7), but it'll never be used by greenfield templates — it's a one-off the strict mode forced us to support.
**How to avoid:** Accept the cost — D6 chose this tradeoff. The DSL grows in proportion to what the originals need, no more. Document the long-tail attributes as "supports for round-trip; not part of the recommended authoring API".
**Warning signs:** DSL surface bloats with attributes used in 1-2 places only. (Already accepted in CONTEXT.md.)

### Pitfall: Visual diff false positives from sub-pixel font hinting
**What goes wrong:** At 96 dpi, font glyph edges have sub-pixel jitter that varies between Scribus runs (especially with `xvfb-run` randomising the X server seed). Pixel-accurate compare reports 0.5%-2% mismatch on body-text-heavy pages even when the layout is identical.
**How to avoid:** ImageMagick `-fuzz 2%` already absorbs most of this. Per-region tolerance config (in `diff.yml`) lets body-text regions be laxer than headline regions. CI runs at 96 dpi (D4) precisely because higher dpi = more font-edge jitter.
**Warning signs:** Visual diff fails on "noisy" pages but the composite PNG looks visually identical to a human. Increase tolerance for those regions.

## Environment Availability

| Dependency | Required by | Available locally | Version | Available in CI? | Fallback |
|---|---|---|---|---|---|
| Python 3 | DSL, converter, diff tools | yes | (assumed 3.11+) | yes (Ubuntu runner) | — |
| `lxml` | reader, builder, diff | yes | 5.4.0 | yes (`python3-lxml`) | — |
| PyYAML | ci.yml load, diff.yml load | yes | 6.0.2 | yes (`python3-yaml`) | — |
| Scribus 1.6.5 | render | yes (`/usr/bin/scribus`) | 1.6.5 | yes (AppImage in workflow) | — |
| Xvfb (`xvfb-run`) | headless render | yes | (default) | yes (`xvfb` apt) | — |
| ImageMagick `compare` | visual_diff metric | yes | 6.9.11-60 | needs apt install (`imagemagick`) — currently NOT in workflow | document new dep |
| ImageMagick `montage` | composite output | yes | (same) | same | — |
| `pdftoppm` (Poppler) | rasterise | yes | 22.12.0 | yes (`poppler-utils`) | — |
| Ghostscript `gs` | rasterise (alt) | yes | 10.05.1 | yes (`ghostscript`) | use as fallback |
| `odiff` | faster pixel diff (optional) | **NO** | — | not currently | skip per CONTEXT.md scope |

**CI workflow change required:** add `imagemagick` to the `apt-get install` line in `.github/workflows/pages.yml` (current line 32 installs `xvfb poppler-utils ghostscript python3-lxml python3-yaml`).

## Project Constraints (from CLAUDE.md)

No workspace `./CLAUDE.md` found.

User memory contains relevant directives:
- **No "claude" attribution** in commits/code/files (`feedback_no_claude_attribution.md`).
- **Issue artifacts are preserved**, never deleted (`feedback_preserve_issue_artifacts.md`).
- **Working over theoretically better** for tool swaps (`feedback_working_over_theoretical.md`) — supports the "stick with ImageMagick, skip odiff" choice in §visual_diff.

## Sources

### HIGH confidence (codebase analysis + Context7-equivalent direct measurement)
- Direct lxml probe of `postkarte-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `gruene-zeitung-vorlage-original.sla` at workspace root (this session, 2026-05-05).
- `tools/sla_lib/builder/{__init__.py,document.py,primitives.py,blocks.py,ci.py}` (read in full this session).
- `tools/sla_lib/reader.py`, `tools/check_ci.py`, `tools/render.py`, `tools/_export_pdf.py` (read in full this session).
- `shared/ci.yml` (read in full this session).
- `templates/postkarte-a6-kampagne/build.py` (read in full this session).
- `.research/01-sla-format.md` (290 lines, authoritative format reference).
- `.research/04-scribus-multipage-masters.md` (multi-page + master pages structural rules).
- `.github/workflows/pages.yml` (read in full this session).
- Local tool availability probed via `command -v` and `--version` flags.

### MEDIUM confidence (verified secondary sources)
- ImageMagick `compare -metric AE -fuzz 2%` semantics: standard behaviour, documented in `compare(1)`. Verified locally.
- `pdftoppm -r {dpi} -png` semantics: standard. Verified locally.
- ItemID `qHash(item) & 0x7FFFFFFF` and inheritance rules: from `.research/01-sla-format.md` §1 + §4, sourced from Scribus source.
- The 4 PageSets being mandatory: from `.research/04` §3.

### LOW confidence (needs validation during implementation)
- Whether ALIGN on PAGEOBJECT is horizontal text alignment (ALIGN) vs vertical (VAlign) — needs Scribus source check.
- Whether `qCompress` is exactly `4-byte big-endian length + zlib deflate` for round-tripping inline images — `.research/01-sla-format.md` says yes; not directly verified by decoding one of the originals' ImageData in this research pass.
- Exact ImageMagick `-fuzz 2%` value vs. real font-jitter: 2% is a starting guess; tune from Phase 5 measurements.
- Optimal tolerance per template — `1%` is the issue's target; per-page or per-region overrides may be needed for the Zeitung.

## Open Questions for the Planner

1. **Mapping `templates/<id>/` to original SLA filename.** Three originals at workspace root, three template directories with names that don't match (e.g. `templates/plakat-event/` ↔ `plakat-a1-hochformat-original.sla`). Recommend adding `original_sla:` key to each `templates/<id>/meta.yml`. Planner: confirm meta.yml is the right home, or propose alternative.
2. **`templates/plakat-event/` directory rename?** Current name suggests an event poster (the original IS an event poster), but the issue says "Plakat A1 Hochformat" — does the directory get renamed (e.g. `templates/plakat-a1-hochformat/`) or stay? If renamed, gallery URL/Astro frontmatter needs updating in the same PR.
3. **`check_ci.py` warnings on the reproductions.** The reproductions ship with non-CI styles (`Fließtext`, `Headline sehr wichtig`, etc.) by design. Should `check_ci.py` be extended to accept a per-template allowlist (cleanest), or should we accept that `check_ci.py` produces warnings on the reproductions but `--strict` is never used in CI for these templates? Recommend the allowlist approach but flag the LOC cost.
4. **Embedded inline images: Option A (extract to sidecar PNG) vs Option B (round-trip qCompress).** Option A is simpler and lossless. Option B keeps the SLA self-contained. Recommend A; planner: confirm.
5. **Inline FRAMEOBJECT (orphan-scratch frames) handling.** Postkarte/Plakat/Zeitung all have 3-5 of these (`OwnPage=-1`). Recommend the converter drops them silently and `sla_diff` ignores FRAMEOBJECT count. Planner: confirm this is acceptable (they don't render, so visual_diff won't catch the absence; sla_diff treating their presence as info is harmless).
6. **Scribus 1.6.5 LANGUAGE handling on STYLE.** The Zeitung's 23 paragraph styles only set LANGUAGE on 13 of them. Does omitting LANGUAGE inherit from the document's default (de) or fall back to system locale? If the latter, omitting LANGUAGE might cause hyphenation drift. Verify by rendering the Zeitung in `xvfb-run scribus` and inspecting paragraph hyphenation against the original's PDF.
7. **Soft-hyphen test corpus.** Plakat has 7 occurrences but the Zeitung has 0 — Scribus's hyphen engine handles the Zeitung autonomously. Should the DSL document this as "soft-hyphens are escape-hatches for words Scribus's German hyph dict gets wrong" rather than "use them everywhere"? (Documentation question for the planner.)
8. **Diff exit codes.** Recommend `sla_diff` exit 1 on `critical`, exit 0 otherwise (with `--strict` exit 1 also on warning). `visual_diff` exit 1 on any per-page/region threshold breach. CI relies on exit codes — confirm the planner's preferred convention.
9. **Schema for `templates/<id>/diff.yml`.** Proposed in §visual_diff. Planner: bless or revise the YAML key names before any per-template configs are committed (cheap to change now, expensive after 3 templates ship configs).
10. **Where does the converter live in the test loop?** Two options: (a) `tools/sla_to_dsl.py` is a one-shot generator — run it manually, commit the resulting `templates/<id>/build.py`, then `build.py` is the source of truth (the converter never runs in CI). (b) The converter runs in CI on every push, regenerating `build.py` and asserting it's unchanged. Recommend (a) — D2's "typed DSL" implies hand-readable build.py files that humans extend; a CI-regenerated file would be confusing. Planner: confirm.

## Metadata

**Confidence breakdown:**
- Codebase: HIGH (every relevant file was read end-to-end this session).
- Per-original inventory (§1): HIGH (all numbers are direct lxml measurements).
- DSL gap analysis (§2): HIGH (every gap maps to a measured original-side count).
- sla_diff strategy (§3): MEDIUM-HIGH (normalisation rules are derived from research; severity thresholds are starting guesses subject to tuning).
- visual_diff strategy (§4): MEDIUM (tools verified locally; tolerance numbers need empirical tuning in Phase 5).
- CI integration (§5): MEDIUM (workflow shape is clear; runtime budget is a model, not measured).
- Sequencing (§6): MEDIUM (order is informed but the per-phase day estimates are ranges, not commitments).

**Research date:** 2026-05-05.

**Sub-agents used:** None — this researcher worked single-threaded because the issue is bounded to a known codebase + 3 measurable artifacts, and the prompt's 7 sections were self-organising. Spawning specialist sub-agents would have re-investigated the same files. The codebase / ecosystem / pitfalls split was instead handled inline: codebase by direct file reading, ecosystem by `command -v` probes and the existing `.research/01` `.research/04`, pitfalls by cross-referencing `.research/01` §8 against measured anomalies in the originals.

**Raw research files:** None — synthesis was inline. If the planner wants raw inventory dumps (e.g. exhaustive STYLE attribute listing per template), they can be regenerated by re-running the lxml probes documented in this researcher's bash transcripts.

**Files this RESEARCH.md cites or relies upon (paths absolute to repo root):**
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/postkarte-vorlage-original.sla`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/plakat-a1-hochformat-original.sla`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/gruene-zeitung-vorlage-original.sla`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/tools/sla_lib/builder/{__init__,document,primitives,blocks,ci}.py`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/tools/sla_lib/{reader,editor,slot}.py`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/tools/{check_ci,render,_export_pdf,gallery_build}.py`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/shared/ci.yml`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/templates/postkarte-a6-kampagne/build.py`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/.research/01-sla-format.md`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/.research/04-scribus-multipage-masters.md`
- `/root/workspace/.worktrees/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/.github/workflows/pages.yml`
