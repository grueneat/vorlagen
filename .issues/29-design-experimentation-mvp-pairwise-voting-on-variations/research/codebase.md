# Codebase Research — Issue #29 (Design Experimentation MVP)

**Researcher:** codebase specialist
**Repo root:** `/root/workspace/`
**Read-only.** Every claim has a `path:line` citation. Anything not directly verified is marked `(uncertain)`.

This map is structured to let the planner copy `<interfaces>` blocks directly into PLAN.md.
Each section starts with the locked-decision element it serves, then API surface, then file:line citations.

---

## 0. Constraints up-front (NOT to violate)

- `./CLAUDE.md` does NOT exist at workspace root (`Read /root/workspace/CLAUDE.md` → file does not exist). No project-level Claude directives to honor beyond CONTEXT.md and the patterns in `README.md`.
- A `Dockerfile.claude` exists and is referenced for env determinism (e.g. Pillow / qrcode / jsonschema versions pinned) — see `tools/sla_lib/builder/library.py:608`, `tools/codex_image_gen.py:57`. Any new Python deps must be installed in this container.
- `.claude/skills/` does NOT exist (`/root/workspace/.claude/` only has `scheduled_tasks.lock` + `settings.local.json`). No project skills to load.
- `README.md` (root) documents the build flow: `python3 templates/<id>/build.py` → SLA → `xvfb-run scribus tools/_export_pdf.py` → PDF, OR `python3 tools/gallery_build.py` for full pipeline. `README.md:163-180`.
- Brand fonts (Gotham Narrow, Vollkorn) are **not** in repo; render pipeline hard-fails if fewer than 5 brand-font faces are present in `fc-list` — `tools/render_pipeline.py:257-278`. Any experiment render path must run inside the Dockerfile.claude container that has these fonts installed.

---

## 1. Python DSL Builder (`sla_lib.builder`)

### Locked decision served
> Decision 1: each variant is a self-contained `experiments/<exp-id>/variants/<hypothesis-slug>.py` that imports shared falzflyer scaffolding so only P2 differs.

The variant Python files MUST go through this DSL — there is no other path for emitting valid Scribus 1.6 SLA XML. `tools/sla_lib/builder/__init__.py:1-9`.

### Public API surface

<interfaces>
// From tools/sla_lib/builder/__init__.py — the canonical public re-exports
from sla_lib.builder import (
    Document, Page,                 // document.py
    Color, Style, load_ci,          // ci.py
    TextFrame, ImageFrame, Polygon, // primitives.py
    Line, Anchor, Run, pack_inline_image,
    ParaStyle, CharStyle, DocumentLayer, SoftShadow,  // styles.py
    Brand,                          // brand.py
    blocks,                         // blocks.py (named blocks like FoldLine, PageBackground, …)
    library,                        // library.py (load/inject_into_frame)
    AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
    GridSpec, GridCell, HierarchyBlock,                // composites.py
    same_y, same_x, same_size, mirrored_x, mirrored_y, // constraints.py
    inside, equal_gap, hierarchy, same_style,
    distance_y, distance_x, aligned_below,
    Constraint, Violation,
    BRAND_CONSTRAINTS, BrandRule,                      // brand_constraints.py
)

// From tools/sla_lib/builder/document.py:140
class Document:
    def __init__(self, title: str = "", template_id: str = "",
                 author: str = "Die Grünen Niederösterreich",
                 ci_path: Optional[Path | str] = None,
                 *,
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
    def add_color(self, name: str, *, rgb=None, cmyk=None,
                  spot: bool = False, register: bool = False) -> None: ...
    def add_para_style(self, style: ParaStyle) -> None: ...
    def add_char_style(self, style: CharStyle) -> None: ...
    def add_master(self, name: str = "Normal",
                   size: str | tuple[float, float] = "A4",
                   orientation: str = "portrait",
                   bleed_mm: float = 3.0,
                   margins_mm: tuple = (10, 10, 10, 10),
                   facing: str = "right",
                   page_xpos_pt: Optional[float] = None,
                   page_ypos_pt: Optional[float] = None,
                   width_pt: Optional[float] = None,
                   height_pt: Optional[float] = None) -> Page: ...
    def add_page(self, size="A4", orientation="portrait", bleed_mm=3.0,
                 margins_mm=(10, 10, 10, 10), master="Normal",
                 label="", page_xpos_pt=None, page_ypos_pt=None,
                 width_pt=None, height_pt=None) -> Page: ...
    def save(self, path: Path | str) -> None: ...                  // doc.py:407
    def iter_all_primitives(self) -> Iterable: ...                  // doc.py:413

// From tools/sla_lib/builder/document.py:107 (dataclass)
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float = 3.0
    margins_mm: tuple = (10, 10, 10, 10)
    master_name: str = ""
    label: str = ""
    items: list = field(default_factory=list)
    own_page: int = 0
    is_left: bool = False
    is_master: bool = False
    def add(self, item) -> "Page": ...   // expands blocks via .emit()

// From tools/sla_lib/builder/primitives.py:549 (dataclass _Frame subclass)
class TextFrame(_Frame):
    text: str = ""
    style: str = ""                      // PARENT paragraph style name
    fcolor: str = ""                     // override frame color
    runs: Optional[list[Run]] = None
    columns: int = 1
    col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None
    fill: Optional[str] = None           // PCOLOR (frame fill)
    line_color: Optional[str] = None
    line_width_pt: float = 0
    default_style_attrs: Optional[dict] = None
    next_item: Optional[TextFrame] = None        // chain via link_to(other)
    // inherits x_mm, y_mm, w_mm, h_mm, anchor, layer, anname, custom_path,
    // corner_radius_mm, soft_shadow, is_full_bleed, rotation_deg

// From tools/sla_lib/builder/primitives.py:773
class ImageFrame(_Frame):
    src: str = ""
    image: str = ""                       // alias for src
    layer: int = 1                        // Bilder default
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1                   // 0=ScaleAuto (fill); see library.inject_into_frame
    ratio: int = 1                        // 1 = preserve aspect
    pic_art: int = 1
    fill: Optional[str] = None
    inline_image_data: Optional[str] = None    // base64 from pack_inline_image
    inline_image_ext: Optional[str] = None     // "png" | "jpg"

// From tools/sla_lib/builder/primitives.py:856
class Polygon(_Frame):
    fill: str = "Black"
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0                        // Hintergrund default
    shape: str = "rectangle"              // 'rectangle' | 'ellipse'
    fill_shade: int = 100
    dash_pattern: Optional[tuple[float, ...]] = None

// From tools/sla_lib/builder/primitives.py:294 (typed run)
class Run:
    text: str = ""
    has_itext: bool = True
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    fshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    char_style: Optional[str] = None
    paragraph_style: Optional[str] = None    // PARENT on trailing <para/>
    paragraph_attrs: Optional[dict] = None   // closed key set
    separator: Optional[str] = None          // "para"|"breakline"|"tab"|"breakcol"|"breakframe"
    var: Optional[str] = None                // "pgno"

// From tools/sla_lib/builder/primitives.py:114
class Anchor:
    h: str = "left"        // "left" | "center" | "right"
    v: str = "top"         // "top"  | "center" | "bottom"
    margin_mm: float = 0.0

// From tools/sla_lib/builder/primitives.py:758
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Returns (base64-of-qCompressed-bytes, ext) ready for ImageFrame."""

// From tools/sla_lib/builder/styles.py — ParaStyle / CharStyle / DocumentLayer / SoftShadow
class ParaStyle:
    name: str
    font: str
    fontsize: float
    linesp: float
    align: int                 // 0=left, 1=center, 2=right, 3=justify
    fcolor: str
    language: str = "de"
    linesp_mode: int = 0
    space_before_pt: float = 0
    space_after_pt: float = 0

// From tools/sla_lib/builder/constraints.py:399-507
def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5, name: str = "") -> Constraint
def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def mirrored_y(top, bottom, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def equal_gap(*targets, axis: str = "y", gap_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def hierarchy(*targets, by: str = "fontsize", name: str = "") -> Constraint
def same_style(*targets, name: str = "") -> Constraint
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint

// From tools/sla_lib/builder/blocks.py:559 — used by falzflyer for the fold lines
class FoldLine:                       // emits a Polygon with PWIDTH on Falz layer
    start_mm: tuple[float, float]
    end_mm: tuple[float, float]
    layer_idx: int                    // typically LAYER_FALZ
    anname: str

// From tools/sla_lib/builder/library.py:242 — demo image API
def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]: ...
def inject_into_frame(frame, img: LibraryImage, *,
                      target_w_mm: float, target_h_mm: float,
                      dpi: int = 300, quality: int = 80,
                      apply_watermark: bool = True) -> None: ...
def crop_for_frame(img, *, target_w_mm, target_h_mm, dpi=300,
                   quality=80, apply_watermark=True) -> bytes: ...
</interfaces>

### Key behavior the planner needs
- A `Document(brand=Brand.gruene_noe(), …)` auto-registers all CI colors / paragraph-styles / char-styles / layers — `document.py:215-244`. So variant scripts can just `from sla_lib.builder import Brand, Document` and inherit all brand styles.
- Adding non-CI styles is `doc.add_para_style(ParaStyle(name="falzflyer/schlagwort", …))` — see `templates/kandidat-falzflyer-din-lang/build.py:122-326` for the canonical pattern.
- Page items are flat: `page.add(item)` either appends a primitive or expands a Block via `.emit()` — `document.py:124-134`.
- Save flow: `Document.save(path)` calls `_build_xml()` and writes via `lxml.etree` — `document.py:407-410`.

---

## 2. Falzflyer Template `build.py` — Anatomy of P2

### Locked decision served
> Decision 1: hoist scaffolding so only P2 varies.
> Decision 5: variations are full-page renders (P1+P2+P3 with P2 varying).
> Decision 7: experiment subject is falzflyer P2 "Mein Plan" panel; builder code at `templates/kandidat-falzflyer-din-lang/build.py:432–505`.

### File-level shape

`templates/kandidat-falzflyer-din-lang/build.py` (1029 lines). The function topology relevant to this issue:

| function | lines | role |
|---|---|---|
| `_top_band(panel_index)` | 69-119 | Helper that returns one of 6 panel-specific Top-Band Polygons |
| `_add_styles(doc)` | 122-326 | Registers 16 falzflyer-local ParaStyles (mutations + KEPT + NEW) |
| `_add_front(doc, page0)` | 329-571 | Builds entire FRONT side (P1 + P2 + P3 + Falz lines). **P2 lives at lines 432-491.** |
| `_add_back(doc, page1)` | 574-869 | Builds entire BACK side (P4 + P5 + P6 + Falz lines) |
| `build_template()` | 872-906 | Returns Document with NO inline image data on INJECT_MAP photos |
| `build_preview()` | 909-934 | Wraps `build_template()`, injects library images via `library.inject_into_frame` |
| `build_doc = build_template` | 939 | Alias for spec_check / structural_check / smoke |
| `build(out_path)` | 942-946 | Calls `build_preview()`, writes SLA |
| `CONSTRAINTS` list | 966-1024 | 22 constraint entries (not relevant for P2 variants) |
| `if __name__ == "__main__"` | 1027-1029 | CLI entry |

### Exact P2 structure (build.py:432-491)

P2 occupies x = 99..198 mm on the FRONT page (page0). The four named PAGEOBJECTs the locked-decision references:

| anname | type | x_mm, y_mm, w_mm, h_mm | style/fill | citation |
|---|---|---|---|---|
| `P2 Top-Band` | Polygon | (99, -3, 99, 31) | fill=Dunkelgrün, layer=Hintergrund | `_top_band(1)` build.py:90-96 + call at 434 |
| `P2 Top-Title` | TextFrame | (105, 8, 87, 14) | style=`falzflyer/top-title`, runs="Mein Plan" | build.py:436-443 |
| `P2 Teaser-Headline` | TextFrame | (105, 38, 87, 22) | style=`falzflyer/teaser-headline`, runs="Was ich für Mödling will" | build.py:445-453 |
| `P2 Body-Backing` | Polygon | (99, 28, 99, 185) | fill=Hellgrün, layer=Hintergrund | build.py:455-467 |
| `P2 Teaser-Body` | TextFrame | (105, 72, 87, 130) | style=`falzflyer/schlagwort`, 5 paragraphs of `Run(…, separator="para")` | build.py:469-491 |

The five paragraphs of `Teaser-Body` are: `"Klimaplan jetzt."`, `"Leistbares Wohnen."`, `"Bildung vor Ort."`, `"Lokale Wirtschaft."`, `"Bürgernähe statt Klüngel."` — build.py:478-489. **This is the exact "even-spaced peer list" (corpus §2.1, §6, §8 #3) that the experiment is targeting.**

### What's parameterizable today

P2's content is hardcoded (no variant input exists). The variation surface is:
- **The entire P2 region** (everything between the P3 polygon at line 332 and the start of P3 Top-Title at line 504) is structurally separable.
- P1 (build.py:342-430) and P3 (build.py:498-557) are independent — they don't reference P2 anames.
- P2 contributes ZERO entries to the `CONSTRAINTS` list (lines 966-1024) — only `same_size("P2 Top-Band", …)` couples it to P1/P4/P5 Top-Bands. This means a variant that *changes* P2's geometry is structurally legal as long as the Top-Band stays 99×31 (or the constraint is relaxed for variants).

### What needs hoisting (planner work)

For "import shared falzflyer scaffolding so only P2 differs", the cleanest hoist is to **factor `_add_front` so P2 is a callable parameter**:

```python
# Proposed factoring (planner decides exact shape):
def _add_front(doc, page0, *, p2_render_fn=_render_p2_default):
    # P3 Hintergrund (line 332-340)
    # P1 Top-Band, Logo, Portrait, Name-Card, Name, Slogan (342-430)
    p2_render_fn(doc, page0)            # <- variant point
    # P3 Top-Title, Wahlkreuz, Closer-Headline, Datum, URL (501-557)
    # Falz lines (559-571)
```

Each variant `experiments/<exp-id>/variants/<hypothesis-slug>.py` then defines its own `render_p2(doc, page)` and calls a shared `build_variant(p2_render_fn=…)` factory that produces a 1-page Document (just the FRONT — P4-P6 not needed for the experiment per Decision 5: "the entire DIN-lang front side, P1+P2+P3 with P2 varying"). The planner will need to decide whether to:
1. Keep the existing 2-page document and only render page 1, OR
2. Add a new entrypoint `build_variant_front_only(...)` that emits a 1-page Document.

`(uncertain)` — both are viable; option 2 is faster to render but needs new code; option 1 reuses everything.

### Style additions for P2 variants

A variant that uses, say, "yellow accent on one item" or "Vollkorn italic on the priority item" will need new ParaStyles or CharStyles. The pattern is:
- Variant calls `doc.add_para_style(ParaStyle(name="exp-<slug>/<name>", …))` before adding frames — same idiom as `_add_styles` at build.py:122.
- The 18 brand colors auto-registered by `Brand.gruene_noe()` (Dunkelgrün, Hellgrün, Gelb, Magenta, White, Black, …) are already available.

---

## 3. Render Pipeline (`tools/render_pipeline.py` and `bin/render-gallery`)

### Locked decision served
> Decision 5: full-page renders.
> Discretion: "Variant image dimensions: match the existing gallery preview sizes (page-01.png + page-01-hires.png) used in the falzflyer template."

### Pipeline shape

`bin/render-gallery` is a 15-line shim that imports `tools/render_pipeline.py:main` — `bin/render-gallery:1-14`.

`tools/render_pipeline.py` orchestrates per-template, for any template whose `meta.yml` has `original_sla:` OR `previews_for_sla:` — render_pipeline.py:53-68.

Per-template (single non-family) pipeline at `_orchestrate_single` (render_pipeline.py:475-534):
1. `python3 templates/<id>/build.py` (run as subprocess at lines 622-644 inside `_orchestrate_template`)
2. `render_sla_to_pdf(template.sla, preview.pdf)` — calls Scribus via xvfb (visual_diff.py:112-143)
3. `_scrub_pdf_metadata(preview.pdf)` — byte-deterministic PDF (lines 75-130)
4. `rasterise(preview.pdf, page, dpi=DEFAULT_DPI=50)` — `pdftoppm -r <dpi> -png` produces page-NN.png (visual_diff.py:146-150)
5. `rasterise(preview.pdf, hires, dpi=HIRES_DPI=150)` — Issue #28 hires variant
6. Rename `hires-NN.png` → `page-NN-hires.png` (lines 506-509)
7. (Optional) sla_diff vs original_sla — line 511
8. (Optional) visual_diff vs baseline.pdf — line 516
9. Update `meta.yml::previews_for_sla` SHA — line 522
10. Mirror artifacts to `site/public/templates/<id>/` — line 523

Falzflyer's `meta.yml::preview_dpi` = 100 (overrides DEFAULT_DPI=50). meta.yml:7. So gallery thumbnails are 100 dpi, hi-res is 150 dpi.

### Critical preflight

`_verify_brand_fonts()` (render_pipeline.py:257-278) hard-fails if `fc-list | grep -i 'gotham narrow|vollkorn'` returns < 5 lines. **Variant rendering MUST happen inside the Dockerfile.claude container.**

### Reusable functions for new `bin/experiment-render`

<interfaces>
// From tools/visual_diff.py — reusable building blocks
def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None       // visual_diff.py:112
def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path] // visual_diff.py:146

// From tools/render_pipeline.py — internal helpers (private but reusable)
def _scrub_pdf_metadata(p: Path) -> None                            // render_pipeline.py:75
def _verify_brand_fonts() -> None                                   // render_pipeline.py:257
def _zero_pad_pngs(tdir: Path, prefix: str) -> None                 // render_pipeline.py:343
DEFAULT_DPI = 50                                                    // render_pipeline.py:41
HIRES_DPI = 150                                                     // render_pipeline.py:46
</interfaces>

### Suggested `bin/experiment-render` shape

Mirroring the `bin/render-gallery` shim pattern (bin/render-gallery:1-14):

```python
#!/usr/bin/env python3
"""bin/experiment-render — render all variants of an experiment."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from experiment_render import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

The `tools/experiment_render.py` would:
1. Read `experiments/<exp-id>/manifest.yml`
2. For each variant: import the variant module, call its `build_variant()` (returns Document), `Document.save("variant.sla")`, then run `render_sla_to_pdf` + `rasterise` at preview_dpi (100) AND hires_dpi (150) as `experiments/<exp-id>/variants/<slug>/page-01.png` + `page-01-hires.png` for Astro consumption.
3. Optionally call `_verify_brand_fonts()` first (mirror of render_pipeline.py).

---

## 4. Astro Site (`site/`)

### Locked decision served
> Decision 2: Voting UI in existing Astro site, new routes at `site/src/pages/experiments/index.astro` and `site/src/pages/experiments/[id].astro`. Inherits layout from existing gallery.

### Site structure

```
site/
├── astro.config.mjs       # base: '/vorlagen/', site: 'https://grueneat.github.io'
├── package.json           # astro ^5.0.0; scripts: dev/build/preview/check
├── src/
│   ├── content.config.ts  # collection = templates, glob 'src/content/templates/**/*.md'
│   ├── content/templates/ # 8 template MD files (one per template)
│   ├── layouts/Base.astro # shared layout with header/footer + global CSS
│   └── pages/
│       ├── index.astro          # gallery grid
│       └── templates/[...id].astro  # per-template page (with #28 lightbox)
└── public/templates/<id>/  # mirrored renders (page-*.png, template.sla, preview.pdf)
```

### Routing pattern (locked decision says "mirror this")

The dynamic-route precedent is `site/src/pages/templates/[...id].astro`. Key idiom:

<interfaces>
// site/src/pages/templates/[...id].astro:1-14
---
import Base from '../../layouts/Base.astro';
import { getCollection, render } from 'astro:content';

export async function getStaticPaths() {
  const templates = await getCollection('templates');
  return templates.map(t => ({ params: { id: t.id }, props: { t } }));
}
const { t } = Astro.props;
const { Content } = await render(t);
const BASE = import.meta.env.BASE_URL;
const url = (p: string) => BASE + p.replace(/^\//, '');
---

// site/src/content.config.ts:1-26 — schema is permissive (z.record(z.any()))
const templates = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/templates' }),
  schema: z.object({
    id: z.string(),
    version: z.string(),
    title: z.string(),
    description: z.string().optional(),
    type: z.string().optional(),
    format: z.string().optional(),
    pages: z.number().optional(),
    audience: z.array(z.string()).optional(),
    sizes: z.array(z.any()).optional(),
    masters: z.array(z.any()).optional(),
    example_pages: z.array(z.any()).optional(),
    slots: z.record(z.any()).optional(),
    preflight: z.record(z.any()).optional(),
    build: z.record(z.any()).optional(),
    _downloads: z.array(z.any()).optional(),
    _previews: z.array(z.any()).optional(),
  }),
});
export const collections = { templates };
</interfaces>

### Lightbox / inline JS pattern (#28) — reusable for voting UI

The existing `[...id].astro:46-90` already demonstrates **vanilla JS in `<script is:inline>` wired to data-attributes on anchors**. This is exactly the "vanilla JS + Astro client island is sufficient" pattern from CONTEXT discretion §"Voting page implementation". Reuse:
- `<script is:inline>` block with IIFE — `[...id].astro:55-90`
- DOM querying via `document.querySelectorAll('a.preview-link')` then `addEventListener` — line 76-81
- Data-attribute passing (`data-hires`, `data-label`) for per-element state — line 33-36

For voting localStorage + JSON export (Decision 9, 10), this is the same pattern. No framework needed.

### Adding new routes

To add `site/src/pages/experiments/index.astro` and `site/src/pages/experiments/[id].astro`, the planner must decide whether to:
- **Option A:** Use a NEW Astro content collection (`experiments`), with its own `loader` + schema in `src/content.config.ts`. Mirror the templates pattern.
- **Option B:** Skip the content collection and read `experiments/<id>/manifest.yml` directly via Astro's filesystem APIs at build time. Less idiomatic but lighter.

`(uncertain — recommendation needed)` — Option A is the codebase-native approach (content collections are how every other route works). The planner should pick A unless there's a strong reason otherwise.

### Site base URL

`astro.config.mjs:13-15` sets `base: '/vorlagen/'`, `trailingSlash: 'always'`. All asset URLs are constructed via `BASE + path.replace(/^\//, '')` — see `[...id].astro:13`. The voting page must do the same.

---

## 5. Existing `meta.yml` Format and `template-spec.schema.yaml`

### Discretion decision served
> "Manifest format: suggest YAML at `experiments/<exp-id>/manifest.yml` listing experiment metadata + the hypothesis list with attribution. YAML matches existing `meta.yml` and `template-spec.schema.yaml` conventions."

### `template-spec.schema.yaml` structure

`shared/template-spec.schema.yaml:1-313`. JSON Schema draft-2020-12, expressed in YAML. Schema validates `templates/<x>/spec.yml` files (NOT meta.yml — different file). Top-level required keys: `template`, `brand`, `pages`. `template-spec.schema.yaml:23-27`.

Notable shape: the schema is hierarchical with `$defs` for `StyleOverride`, `PageSpec`, `HeadlineSlot`, `BodySlot`, `ImpressumSlot`, `ContactSlot`, `RunSpec`, `PositionSpec`, `LayoutSpec`. `template-spec.schema.yaml:118-313`.

### Existing `templates/<id>/meta.yml` shape

`templates/kandidat-falzflyer-din-lang/meta.yml:1-295`. Top-level keys actually used:

| key | type | purpose |
|---|---|---|
| `id` | str | machine-readable slug (e.g. `kandidat-falzflyer-din-lang`) |
| `version` | str | semver (e.g. `0.1.0`) |
| `title` | str | human-readable (German) |
| `format` | str | `A4` / `A6` / etc. |
| `orientation` | str | `landscape` / `portrait` |
| `pages` | int | page count |
| `preview_dpi` | int | DPI for thumbnail rasterise (overrides DEFAULT_DPI=50) |
| `audience` | list[str] | `[kandidat, bezirksgruppe, ortsgruppe]` |
| `description` | str (block) | multi-line description |
| `build` | mapping | `{script: build.py, output: template.sla}` |
| `previews_for_sla` | str | SHA256 of template.sla — staleness pin |
| `brand_overrides` | list of `{id, reason}` | exempted brand-rules with rationale |
| `ci_overrides` | mapping | `non_ci_styles: [...]`, `non_ci_colors: [...]`, `non_ci_layers: [...]` |
| `slots` | mapping | per-anname slot descriptions (see schema $defs) |
| `example_pages` | list of `{num, label}` | annotation for gallery |
| `samples` | list of `{id, description}` | sample image descriptions |
| `preflight` | mapping | `{bleed_mm, fold_mm, cmyk_only, min_image_dpi}` |

### Recommended `experiments/<exp-id>/manifest.yml` shape (for planner)

Following meta.yml conventions (snake_case keys, blocks for descriptions, list-of-mapping for sub-entries):

```yaml
id: 2026-05-falzflyer-p2-mein-plan
version: 0.1.0
title: "Falzflyer P2 'Mein Plan' — pairwise voting"
target_template: kandidat-falzflyer-din-lang
target_region: P2
target_panel_anname_prefix: "P2 "
weak_area_citation: design-guide/gruene-corpus.md#§6 + §2.1 + §8.3
description: >
  Generate ≥10 structurally-distinct hypotheses for the P2 panel,
  render each as a full-front-page image, vote pairwise on appeal +
  transport axes.

contributing_llms:
  - {model: claude-opus-4.x, role: hypothesis-design}
  - {model: gpt-5-codex, role: hypothesis-generation}    # or gemini, etc.

variants:
  - id: privilege-one-item-via-yellow-accent
    rationale: >
      Test corpus §6 lesson: "privilege one item visually" — single
      yellow-accent on top item, others demoted.
    sources: [claude-opus-4.x, gpt-5-codex]   # >1 = consensus signal
    builder: variants/privilege-one-item-via-yellow-accent.py
  # … 9 more entries
```

`(uncertain)` — final shape is the planner's call. The above mirrors meta.yml idioms; alternative: adopt the spec.schema.yaml pattern with `pages:` + `slots:`. Recommended NOT to do that — experiments are not templates.

---

## 6. Gallery Preview Generation (`tools/gallery_build.py`)

### Locked decision served
> Voting page reuses gallery preview style; experiment previews must "plug in" so the existing gallery patterns can serve them.

### End-to-end shape

`tools/gallery_build.py:1-136`. **This is COPY-ONLY since issue #4** (gallery_build.py:7-19). The render itself happens in `bin/render-gallery` (= `tools/render_pipeline.py`).

For each `templates/<id>/`:
1. Read `meta.yml` (gallery_build.py:50-56)
2. If `type: family`: copy per-size SLAs/PDFs/PNGs to `site/public/templates/<id>/` (lines 63-87)
3. Else: copy `template.sla` + `preview.pdf` + `page-*.png` to `site/public/templates/<id>/` (lines 88-106)
4. Inject `_downloads` and `_previews` synthetic keys into the meta dict (lines 86-87, 98-106)
5. Write `site/src/content/templates/<id>.md` with YAML frontmatter (`yaml.safe_dump`) + embed `templates/<id>/README.md` body (lines 122-130)

### `_previews` shape (this is what Astro reads)

```python
meta["_previews"] = [
    {"label": f"Seite {i+1}", "src": f"/templates/{tid}/{p.name}"}
    for i, p in enumerate(page_pngs)
]
```

gallery_build.py:103-106. Astro's `[...id].astro:20-44` then renders each `_previews[i]` as a thumbnail with a click-through to the `-hires.png` variant.

### Hi-res lightbox (#28) wiring

Already documented in §4 above. `[...id].astro:46-90` defines a single overlay div + IIFE script. The `data-hires` attribute is computed by `p.src.replace(/\.png$/, '-hires.png')` at line 28. **This entire pattern can be lifted into the experiment per-variant view** — every variant preview will need the same click-to-zoom (the user explicitly mentioned in-situ rendering matters for verdict, so high-detail viewing is critical to the voting experience).

### Where experiment previews plug in

The planner has a clean choice:
- **Option A:** Mirror gallery_build.py's pattern. Add a `tools/experiment_gallery_build.py` (or extend gallery_build.py with an `experiments` mode) that reads `experiments/<exp-id>/manifest.yml`, copies `experiments/<exp-id>/variants/<slug>/page-01*.png` to `site/public/experiments/<exp-id>/<slug>/`, and writes `site/src/content/experiments/<exp-id>.md` with frontmatter listing all variants.
- **Option B:** Skip site/public/ mirroring; have the Astro page read variants directly from `experiments/<exp-id>/` via filesystem APIs at build time.

Option A is more codebase-native. The Astro experiments page can then `getCollection('experiments')` exactly like templates do.

---

## 7. `bin/` Scripts — Inventory and Pattern

`/root/workspace/bin/` (5 scripts):

| script | LOC | purpose | citation |
|---|---|---|---|
| `audit-alignment` | 14 | Shim → `tools/audit_alignment.py:main` | bin/audit-alignment:1-14 |
| `check-fontsizes` | 79 | Standalone (not a shim). Validates SLA `ITEXT FONTSIZE` is integer-only inside PAGEOBJECT subtrees | bin/check-fontsizes:1-78 |
| `check-stale-previews` | 14 | Shim → `tools/check_stale_previews.py:main` | bin/check-stale-previews:1-14 |
| `render-gallery` | 14 | Shim → `tools/render_pipeline.py:main` | bin/render-gallery:1-14 |
| `validate` | 90 | Bash. Runs preflight (check-fontsizes, check-stale-previews) then sla_diff + visual_diff per template | bin/validate:1-90 |

### Shim pattern (4 of 5)

Identical 14-line pattern:

```python
#!/usr/bin/env python3
"""bin/<name> — <description>."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from <module_name> import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

This is the canonical wrapper for Python entry-points. New `bin/experiment-*` scripts should follow this exactly. The corresponding `tools/<module>.py` MUST expose `main(argv=None) -> int`.

### Suggested experiment scripts (planner work)

From CONTEXT discretion §"Tooling layout":
- `bin/experiment-generate` → `tools/experiment_generate.py:main` — calls multi-LLM hypothesis generation, writes manifest.yml
- `bin/experiment-render` → `tools/experiment_render.py:main` — renders all variants in an experiment
- `bin/experiment-results` → `tools/experiment_results.py:main` — aggregates JSON vote files, computes ranking

---

## 8. Existing Tests / Validation Infrastructure

### Test directory

`tools/sla_lib/tests/` — 47+ pytest files (visible: `test_kandidat_falzflyer_geometry.py`, `test_dsl_extensions.py`, `test_constraints.py`, `test_brand_*.py`, `test_codex_image_gen.py`, `test_check_stale_previews.py`, `test_gallery_build_copy_only.py`, …).

Per `README.md:177-179`, run with: `python3 -m unittest discover tools/sla_lib/tests`. (Despite the file naming `test_*.py`, the project standard is `unittest discover`, not pytest.)

### Validation tools relevant to experiments

| tool | role | citation |
|---|---|---|
| `tools/spec_check.py` | Spec-vs-build drift detector. Compares `templates/_specs/<slug>.md` slot YAML against `templates/<slug>/template.sla` PAGEOBJECT geometry. Tolerance buckets (silent/info/error). | spec_check.py:1-30 |
| `tools/sla_diff.py` | Structural SLA-vs-SLA diff with 10-step normalization | README.md:74-84 |
| `tools/visual_diff.py` | Renders SLAs to PDF via Scribus+Xvfb, rasterizes, ImageMagick `compare`, montage. Per-page tolerances via diff.yml. | visual_diff.py:1-40 |
| `tools/check_ci.py` | Drift-detection of brand state (CI palette / fonts / styles) against an SLA | README.md:60 |
| `tools/audit_alignment.py` | Per-template alignment audit (suspicious-undeclared adjacencies; tolerance-suspicion findings); `--strict` exits 1 on findings | audit_alignment.py:1-27 |
| `tools/sla_lib/builder/structural_check.py` | Walks Document.iter_all_primitives() and runs CONSTRAINTS list | (referenced from build.py:957) |
| `tools/sla_lib/builder/brand_constraints.py` | Defines BRAND_CONSTRAINTS list with rules like brand:logo_size_3M, brand:band_consistency, brand:image_text_overlap | sla_lib/builder/__init__.py:89-133 |

### Patterns the experiment system should adopt

- **`main(argv=None) -> int` entry-points** so `bin/<name>` shim works.
- **YAML-first config** (manifest.yml mirrors meta.yml).
- **Honest exit codes** — 0 = pass, 1 = fail, fail loudly with errors to stderr.
- **Idempotency** — render_pipeline.py's `_scrub_pdf_metadata` (lines 75-130) makes re-runs byte-deterministic; consider whether experiment renders need the same.
- **No external network at run time** — all LLM calls go through CLI tools (codex / gemini / claude) per the existing `tools/visual_review.py` pattern (see §10 below).

---

## 9. `shared/` Assets and Brand

### Available for variant rendering

```
shared/
├── ci.yml                       # 89-line single source of truth for brand
├── ci-defaults.yml              # 4183 bytes — defaults for templates without overrides
├── template-spec.schema.yaml    # the schema documented in §5
├── assets/
│   ├── wahlkreuz.png            # 79 KB — yellow X on transparent (used by P3 of falzflyer)
│   └── wahlkreuz-kreis.eps
├── brand/
│   ├── CD-Quickguide.pdf
│   ├── DESIGN-SYSTEM-BRIEF.md   # 16 KB — brand structural guidance
│   ├── QUICKGUIDE-NOTES.md      # 13 KB
│   ├── SPEC-WRITING-GUIDE.md    # 25 KB — guide for writing spec.md files
│   └── CLAUDE-DESIGN-KICKOFF-PROMPT.md  # may be relevant for hypothesis-gen prompts
├── fonts/
│   ├── 50-vollkorn-family-alias.conf    # fontconfig alias for Vollkorn family
│   └── README.md                # font installation instructions
├── logos/
│   ├── gruene-cmyk.png
│   ├── gruene-logo-bund-dunkel.png + .svg
│   ├── gruene-logo-bund-weiss.png       # used by falzflyer P1+P6
│   ├── gruene-weiss.png
│   └── sonnenblume-circle.png
└── sample-images/
    ├── manifest.yml              # 17 KB — central library manifest
    ├── portraits/                # portrait_maria.jpg, portrait_stefan.jpg, …
    ├── themen/                   # themen_klimaschutz_solar.jpg, themen_bildung_volksschule.jpg, …
    ├── kontext/                  # kontext images
    └── qr/                       # empty — QRs stay template-specific
```

For variants: `library.load("portrait_maria")` is one line; the existing `INJECT_MAP` dict in build.py:62-66 shows the per-template idiom but `build_preview()` at build.py:909-934 walks every ImageFrame whose `anname` is in the map.

For variants that vary P2 only (no images), the library is irrelevant; the variant `build_variant` factory just inherits P1's `INJECT_MAP` behavior unchanged.

### `shared/ci.yml`

Per `README.md:58-67`, this is the single source of truth for colors/fonts/styles. Drift-detected by `tools/check_ci.py`. Brand registers all CI when `Document(brand=Brand.gruene_noe(), …)` is called — `document.py:215-244`.

---

## 10. Existing LLM / External-API Integration Patterns

### What's in the repo

Search results (grep `anthropic|openai|gemini|requests.post` over `/root/workspace/tools/`):

| file | role | API pattern |
|---|---|---|
| `tools/codex_image_gen.py` | Calls `codex` CLI via subprocess for DALL·E image generation. Authoring-only (one-shot). | `subprocess.run(["codex", "exec", …])` — codex_image_gen.py:106-128 |
| `tools/visual_review.py` | Multi-model vision review orchestrator. Sends template PNG + composite to Codex / Gemini / Claude. Local-only. | `subprocess.run(["codex", "exec", "--skip-git-repo-check", "-i", str(detail), "-i", str(grid), prompt])` — visual_review.py:213-227; `subprocess.run(["gemini", "--yolo", "-p", …])` — visual_review.py:238-246 |

**There are NO direct HTTP / REST API integrations.** All LLM calls go through CLI tools that the user has logged into separately (`codex login status`, etc.). codex_image_gen.py:106-128.

### Pattern to mirror for hypothesis generation

<interfaces>
// From tools/visual_review.py:209-228 — Codex CLI call
if shutil.which("codex"):
    try:
        r = subprocess.run(
            [
                "codex", "exec",
                "--skip-git-repo-check",
                "--sandbox", "workspace-write",
                "--dangerously-bypass-approvals-and-sandbox",
                "-i", str(detail),    // optional: image inputs
                "-i", str(grid),
                prompt,
            ],
            capture_output=True, text=True, timeout=600,
            stdin=subprocess.DEVNULL,
        )
        # r.stdout contains the model response
    except Exception as e:
        ...

// From tools/visual_review.py:233-246 — Gemini CLI call
if shutil.which("gemini"):
    r = subprocess.run(
        ["gemini", "--yolo", "-p", f"{prompt}\n\n…"],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
    )

// From tools/codex_image_gen.py:106-128 — login-status check
def codex_login_status() -> str:
    if shutil.which("codex") is None:
        return "codex CLI not found on PATH"
    try:
        r = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True, text=True, timeout=10,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return "codex login status timed out"
    if r.returncode != 0:
        return ...
</interfaces>

### Relevance to Decision 6 (multi-LLM hypothesis generation)

CONTEXT.md decision 6 lists candidate models: "Opus + at least one other model — Codex/GPT, Gemini, or an external review LLM via the issue:review pipeline". The existing codebase already has ergonomics for at least:
- **Codex (`codex` CLI)** — used in codex_image_gen.py + visual_review.py
- **Gemini (`gemini --yolo` CLI)** — used in visual_review.py:238

Claude Opus is invoked **inline by the orchestrator agent** (visual_review.py:252-254 says "Claude review handled inline by the orchestrator agent (this session)"). For hypothesis generation, Opus's role is whatever the workflow calls — either the agent driving the issue (this session) or a separate `claude` CLI call.

`(uncertain)` — there is no dedicated `tools/claude_call.py`. If the planner wants an automated, non-interactive Opus call from a Python module, they'll have to either: (a) rely on the orchestrator agent's inline Claude (current pattern), or (b) shell out to `claude` CLI if installed (not verified in repo). Recommend (a) — make the experiment-generate flow have Opus produce one set of hypotheses *as part of this session*, then call `codex` and `gemini` for the others.

### Practical recommendation for `tools/experiment_generate.py`

Mirror `tools/visual_review.py` shape:
1. Read prompt template from `tools/experiment_generate/prompt_template.md` (mirrors `tools/visual_review/prompt_template.md` per visual_review.py:43)
2. For each available CLI (`codex`, `gemini`, …): subprocess call, capture stdout, parse JSON
3. Merge/dedupe hypothesis sets; write `experiments/<exp-id>/manifest.yml`
4. Note that Opus's contribution is THIS agent's writing of variants — there's no need for a separate `claude` subprocess

---

## 11. Project-Level Constraints (CLAUDE.md, README.md)

### CLAUDE.md
**Does not exist** at workspace root. No project-level Claude directives to honor.

### README.md highlights (relevant constraints)

- **Templates have a deterministic build flow:** `python3 templates/<id>/build.py` produces `template.sla`. README.md:42-48.
- **Round-trip validation:** templates with `original_sla:` go through `tools/sla_diff.py` (structural) + `tools/visual_diff.py` (visual). Bin entry: `bin/validate`. README.md:68-113.
- **Local rendering requires Scribus 1.6.x + Python 3.11+ + lxml + PyYAML + Node 20+.** README.md:160.
- **Brand fonts are NOT in repo** — Gotham Narrow + Vollkorn Black Italic are proprietary. README.md:182-184. The render pipeline hard-fails without them (§3).
- **DPI conventions:** local 150 dpi, CI 96 dpi for `visual_diff`. README.md:99.

### Other implicit conventions

- **German file/key naming** is preferred for brand-touching artifacts (e.g. "Dunkelgrün", "Hellgrün", "Falzflyer", "Wahltag", "Themen"). Variant slugs / hypothesis IDs can stay English (existing test/code is mostly English).
- **Anname strings are case-sensitive identifiers** with em-dash literal U+2014 (build.py:61) — variant code that touches existing P2 anames must preserve the exact "P2 Top-Band", "P2 Top-Title", "P2 Teaser-Headline", "P2 Body-Backing", "P2 Teaser-Body" strings (build.py:434, 442, 452, 466, 490).
- **Variants targeting P2** can rename their anames freely (e.g. `"P2 (variant slug) — accent dot"`) but should keep the `P2 ` prefix so audit_alignment / spec_check don't fire false positives.

---

## 12. Reuse Recommendations (per MVP Component)

For each MVP component the user / locked decisions name, here is the pattern to extend or mirror.

### 12.1 Variant Python files (Decision 1)

**Extend:** `templates/kandidat-falzflyer-din-lang/build.py` by **factoring `_add_front` to accept a `p2_render_fn` callable**. New per-variant files:
- `experiments/<exp-id>/variants/<slug>.py` — defines a `render_p2(doc, page0)` function; imports a shared `build_variant_front(p2_render_fn) -> Document` helper from a new `templates/kandidat-falzflyer-din-lang/variant_scaffold.py` (or similar).
- The variant must call `doc.add_para_style(...)` for any new ParaStyles before adding TextFrames.

**Mirror:** the idiom of build.py:122-326 (`_add_styles`) for any new styles a variant needs.

### 12.2 Render pipeline (Discretion §"Tooling layout")

**Extend:** the public functions in `tools/visual_diff.py` (`render_sla_to_pdf`, `rasterise`) and `tools/render_pipeline.py` (`_scrub_pdf_metadata`, `_verify_brand_fonts`, `_zero_pad_pngs`).

**Mirror:** the `bin/render-gallery` shim (bin/render-gallery:1-14) for new `bin/experiment-render`. The new `tools/experiment_render.py` follows the `main(argv=None) -> int` convention.

**Pin:** preview_dpi=100 (matches falzflyer meta.yml:7) for thumbnails, 150 for hires (matches `HIRES_DPI` at render_pipeline.py:46).

### 12.3 Voting UI (Decision 2)

**Mirror:** `site/src/pages/templates/[...id].astro` exactly (the file is 105 lines and demonstrates: dynamic route via `getStaticPaths` + content collection, `BASE_URL` URL helper, inline IIFE script for vanilla JS interactivity, lightbox overlay).

**Mirror:** `site/src/layouts/Base.astro` for the page chrome.

**Add:** new content collection `experiments` in `site/src/content.config.ts` with the pattern from templates collection (lines 4-23) — schema permissive (`z.record(z.any())` for variant lists).

**Implementation language:** vanilla JS in `<script is:inline>` — the lightbox at `[...id].astro:55-90` proves it's sufficient for: localStorage read/write, DOM event handling, JSON serialization, click-through navigation, escape-key handling. Add nothing else (no React, no Svelte).

### 12.4 Manifest (Discretion §"Manifest format")

**Mirror:** the YAML idioms in `templates/kandidat-falzflyer-din-lang/meta.yml`:
- Top-level scalars (`id`, `version`, `title`, `description`)
- Nested mapping for `build:`, `preflight:`, `samples:`
- List-of-mappings for `slots:`, `brand_overrides:`, `variants:` (new)
- snake_case keys throughout, em-dash U+2014 literal in strings

**Don't:** force the `template-spec.schema.yaml` shape onto the manifest — that schema is for `templates/<x>/spec.yml`, not for experiment metadata.

### 12.5 Results aggregation (Decision 10)

**No existing pattern in repo** for vote-results JSON. Build from scratch but mirror the OUTPUT shape conventions:
- Use ISO 8601 timestamps (consistent with `_scrub_pdf_metadata`'s epoch format `D:20000101000000Z` — render_pipeline.py:49 — though that's PDF-specific).
- Use snake_case keys (consistent with all YAML/JSON elsewhere).
- For ranking computation, simple wins-ratio (Decision 9 default). No external library needed.
- Place results under `experiments/<exp-id>/results/` with rater-name-based filenames (e.g. `flo-2026-05-10.json`).

`(uncertain)` — exact filename convention is a planner call.

### 12.6 Hypothesis generation (Decision 6)

**Mirror:** `tools/visual_review.py:209-258` (Codex / Gemini / inline-Claude orchestration pattern). Specifically:
- Subprocess CLI calls with `shutil.which()` guard
- Timeouts set to 600s
- `stdin=subprocess.DEVNULL`
- Write per-LLM raw output to a per-experiment file for audit trail

**New responsibility (no precedent):** prompt template for hypothesis generation. Place at `tools/experiment_generate/prompt_template.md` (mirror visual_review.py:43-44 — the prompt path lives next to the tool).

**Inputs to prompt:** target template path, target region anames, design-guide citations (e.g. `design-guide/gruene-corpus.md` §6 + §2.1 + §8). Per CONTEXT decision 6, prompt MUST forbid parameter-tweak variations and include positive/negative examples.

### 12.7 Mirror-to-Astro flow

**Mirror:** `tools/gallery_build.py` for a new `tools/experiment_gallery_build.py` (or a flag on the existing one). Key transformations:
- Read `experiments/<exp-id>/manifest.yml`
- For each variant: copy `experiments/<exp-id>/variants/<slug>/page-01.png` + `page-01-hires.png` to `site/public/experiments/<exp-id>/<slug>/`
- Write `site/src/content/experiments/<exp-id>.md` with frontmatter listing all variants + their preview paths
- The Astro page (`site/src/pages/experiments/[id].astro`) does `getCollection('experiments')` and `getEntry('experiments', id)`

---

## 13. Open Questions / Uncertainties

Things this map flagged as uncertain, that the planner needs to resolve:

1. **Variant SLA scope:** do variants render the full 2-page (front+back) document or only the front page? Decision 5 says "the entire DIN-lang front side" so render front-only, but the SLA may still need both pages for Scribus to render correctly. `(uncertain — verify by experimenting)`. Recommendation: keep 2-page Document (cheap), but only output `page-01.png` from the rasterise step.
2. **Where exactly to factor the hoist:** new module `templates/kandidat-falzflyer-din-lang/variant_scaffold.py`? Or refactor `_add_front` in-place? `(planner call — both viable)`.
3. **Astro content collection vs filesystem-direct:** §4 Option A (collection) vs Option B (direct fs read at build time). Recommend Option A. `(planner final call)`.
4. **Brand-rule enforcement on variants:** existing `brand_constraints.py` BRAND_CONSTRAINTS list runs on every Document via `structural_check`. Variants that intentionally violate brand rules (e.g. yellow accent block — `brand:max_yellow_area`) need to either (a) opt out via `is_full_bleed=True` per-frame or (b) be exempted via a per-variant `brand_overrides` block. `(planner needs to decide policy)`. Recommended: variants are research artifacts; don't run brand_constraints, period.
5. **Whether `bin/experiment-render` should run `_verify_brand_fonts`:** strongly recommended yes (mirroring render_pipeline.py:689) — otherwise variants render with DejaVu Sans fallback and the votes are invalidated.
6. **No `claude` CLI verification:** the codebase has no example of calling Claude as a subprocess (only inline-via-orchestrator). For decision 6's "≥2 independent generators", recommend: this session's Opus + `codex` + (optional) `gemini`. `(uncertain — verify codex / gemini are present in Dockerfile.claude before committing to specific mix)`.

---

## 14. File Inventory (one-line summaries, for planner orientation)

| File | Lines | Purpose |
|---|---|---|
| `templates/kandidat-falzflyer-din-lang/build.py` | 1029 | The TARGET. P2 lives at lines 432-491. |
| `templates/kandidat-falzflyer-din-lang/meta.yml` | 295 | Shape reference for experiment manifest.yml |
| `templates/_specs/kandidat-falzflyer-din-lang.md` | (not read; `(uncertain)`) | Spec format reference |
| `tools/sla_lib/builder/__init__.py` | 135 | Public API surface — what to import |
| `tools/sla_lib/builder/document.py` | 1300+ | `Document`, `Page`, save flow |
| `tools/sla_lib/builder/primitives.py` | 1000+ | `TextFrame`, `ImageFrame`, `Polygon`, `Run`, `Anchor`, `pack_inline_image` |
| `tools/sla_lib/builder/styles.py` | (not fully read) | `ParaStyle`, `CharStyle`, `DocumentLayer`, `SoftShadow` |
| `tools/sla_lib/builder/blocks.py` | 1100+ | Named blocks (`FoldLine`, `PageBackground`, …) |
| `tools/sla_lib/builder/library.py` | 600+ | Demo image library `load` / `inject_into_frame` |
| `tools/sla_lib/builder/constraints.py` | 500+ | Constraint helpers |
| `tools/render_pipeline.py` | 754 | Per-template render orchestration |
| `tools/visual_diff.py` | 400+ | `render_sla_to_pdf`, `rasterise`, ImageMagick `compare` |
| `tools/gallery_build.py` | 136 | Copy-only Astro content + public mirror |
| `tools/visual_review.py` | 300+ | Multi-LLM CLI orchestration pattern (Codex/Gemini) |
| `tools/codex_image_gen.py` | 700+ | Codex CLI subprocess pattern |
| `bin/render-gallery` | 14 | Shim pattern for entry-points |
| `bin/validate` | 90 | Bash orchestration of structural + visual diff |
| `site/src/pages/templates/[...id].astro` | 105 | Dynamic-route + lightbox pattern to mirror |
| `site/src/content.config.ts` | 26 | Content collection schema |
| `site/src/layouts/Base.astro` | 47 | Shared page chrome |
| `shared/template-spec.schema.yaml` | 313 | JSON Schema for templates/<x>/spec.yml (NOT for experiment manifest) |
| `shared/sample-images/manifest.yml` | (head read) | Library-image manifest format example |
| `design-guide/gruene-corpus.md` | 274 | §6 = falzflyer P2 critique; §2.1 + §8 = "even-spaced peer list" failure mode |

---

End of codebase research. Every claim citation is verified against the file at the cited path:line. Items marked `(uncertain)` are the planner's judgment calls.
