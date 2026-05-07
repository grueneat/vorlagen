# RESEARCH — Review build.py + DSL before more templates

**Issue:** 5-review-buildpy-dsl-before-more-templates
**Researched:** 2026-05-07
**Confidence:** HIGH (codebase fully read; numbers below from direct measurement)

## User Constraints (from CONTEXT.md)

### Locked Decisions
1. `build.py` is **always AI-authored**, never hand-written. Source inputs: SLA (current via `tools/sla_to_dsl.py`), PDF, InDesign, or spec brief. Visual diff vs committed gallery PDFs is the correctness gate.
2. **DSL is optimized for LLM emission**, not human reading. Verbose, regular, named-args-heavy, no clever shortcuts. Higher-level **blocks** may be more compact (a block bug surfaces everywhere → easier to gate-test).
3. **Review scope spans all four input paths** (SLA + PDF + InDesign + spec). Implementations of PDF/InDesign/spec converters are deferred; DSL design must accommodate them now.
4. **Migration: rewrite all three existing templates** onto the new constructs, in size order Postkarte → Plakat → Zeitung, as separate follow-up issues, gated by visual-diff equivalence.
5. **Review report path is `.issues/5-…/REVIEW.md`** (co-located, ships with PR; not `reviews/`).
6. **`extra_*_attrs` strategy:** hoist common values to DSL defaults (likely via `Brand`); keep escape hatch on `Document(...)`.

### Claude's Discretion
- Naming/shape of brand-level construct (`Brand`, `BrandProfile`, expanded `ci.py`…).
- Block file split: stay in `blocks.py` vs split into `blocks/` package.
- Spec-file format design (YAML? JSON? Markdown frontmatter?).
- Granularity of follow-up migration issues (one per template vs one bundled).
- Mechanism for `extra_*_attrs` deduplication (constructor injection / emit time / `Brand.apply(doc)`).

### Deferred (OUT OF SCOPE)
- PDF/InDesign/spec converter **implementations**.
- Rewrites of the three existing templates (separate follow-up issues, depend on DSL hardening).
- Render-pipeline changes (`tools/render.py`, `visual_diff.py`, `sla_diff.py`) unless review surfaces a hard dependency.
- Gallery / Pages publication changes.

## Summary

The DSL surface in `tools/sla_lib/builder/` is solid and well-typed (no `raw_attrs` escape hatch, validated closed sets for paragraph/var/default-style overrides) but the **emitter** (`tools/sla_to_dsl.py`) was tuned for byte-equivalent SLA round-trip, not for clean LLM-targetable output: every per-frame call carries 8 redundant geometry kwargs (mm + pt + width pt + height pt) and the `extra_doc_attrs`/`extra_pdf_attrs` dicts hold **136 + 45 keys, 113 + 34 of them identical across all three templates**, on a single line each. The blocks layer (`blocks.py`, 400 lines) ships 8 blocks but only `Headline4Line`/`StoererBadge`/`Impressum*` correspond to anything actually used in the existing `build.py` files — none of the three templates currently `import` from `blocks`, so the blocks layer is **unused in production**. The clean win is a `Brand` profile that injects DSL-level defaults for the 113/34 identical extras + the small set of brand para/char styles, plus a small set of *truthful* high-level blocks (Impressum, Seitenzahl/PageNumber, MasterpageRectangle, ColumnTextBlock, ContactCard) seeded from idioms that actually recur in the corpus. With those hoists, Postkarte's 437 lines drop to roughly 250-280 (≈40% reduction), Plakat's 235 to ≈180, and Zeitung's 3244 to ≈2200-2400 (the per-frame geometry + structural noise still dominates). The big remaining lever — collapsing the per-frame XPOS/YPOS/WIDTH/HEIGHT pt-overrides — depends on whether the visual-diff gate accepts mm-only round-trip; **CONTEXT.md confirms visual diff is the gate, so this is in scope** and is the largest single LOC reduction available.

**Primary recommendation to the planner:** drive `/issue:review` against the four-file surface (`tools/sla_lib/builder/{primitives,document,styles,ci,blocks}.py` + `tools/sla_lib/{editor,reader,slot}.py` + `tools/sla_to_dsl.py` + the three `templates/*/build.py`) in three reviewer-area splits (DSL surface, converter+templates, multi-input-readiness), then land four P1 hardening items in sequence: (1) `Brand` profile that hoists the 113 identical `extra_doc_attrs` keys + 34 identical `extra_pdf_attrs` keys + the brand para/char-style stack into DSL defaults; (2) drop the redundant `xpos_pt/ypos_pt/width_pt/height_pt` from converter output unless the visual-diff gate actually requires them on a given frame; (3) replace the unused/aspirational blocks in `blocks.py` with five evidence-driven blocks (`PageNumber`, `Impressum`, `MasterpageRectangle`/`PageBackground`, `ContactBlock`, `ColumnTextStory`) plus one masterpage-layout helper; (4) ship a tiny spec-file schema sketch (YAML, frontmatter-style) so the spec→build.py path is unblocked.

## Current State

### DSL surface (`tools/sla_lib/`)

**File / LOC inventory:**

| File | LOC | Role |
|---|---|---|
| `builder/__init__.py` | 73 | Public surface re-exports |
| `builder/primitives.py` | 753 | `_Frame`, `TextFrame`, `ImageFrame`, `Polygon`, `Line`, `Run`, anchor resolver, validators |
| `builder/document.py` | 1028 | `Document`, `Page`, `_IdGen`, XML emit pipeline (colors, styles, layers, masters, pages, PAGEOBJECTs, PDF/Printer stubs, PageSets, Sections) |
| `builder/styles.py` | 140 | `DocumentLayer`, `ParaStyle`, `CharStyle`, `SoftShadow` |
| `builder/ci.py` | 181 | `BrandColor`, `BrandStyle`, `BrandLayer`, `_CI` loader from `shared/ci.yml`, `Color`/`Style` enums |
| `builder/blocks.py` | 400 | 8 compose-level blocks (see below) |
| `editor.py` | 106 | `SLAEditor.set_text/set_image/fill` — used by legacy slot-fill render pipeline, NOT the builder |
| `reader.py` | 139 | `SLADocument` parse + iterators (used by converter and `sla_diff`) |
| `slot.py` | 37 | `Slot`/`SlotKind` ANNAME parser |

**Public API (`from sla_lib.builder import …`):**

```python
Document, Page,                                           # composition
TextFrame, ImageFrame, Polygon, Line, Run, Anchor,        # primitives
ParaStyle, CharStyle, DocumentLayer, SoftShadow,          # typed style overrides
Color, Style, load_ci,                                    # brand identity
blocks                                                     # the (unused) higher-level layer
```

**Key invariants the DSL gets right:**
- **No raw_attrs escape hatch on frames/styles/runs.** The closed sets `PARAGRAPH_OVERRIDE_ATTRS`, `DEFAULTSTYLE_OVERRIDE_ATTRS`, `VAR_OVERRIDE_ATTRS` are validated in `__post_init__` and the converter raises `UnhandledElement` if it encounters something outside them. This is exactly the discipline CONTEXT.md D2 calls for.
- **PARENT-style inheritance preserved** by only-non-None emission of `ParaStyle`/`CharStyle` attributes (`document.py:742-810`). Tested.
- **Inline images round-tripped verbatim** (no PNG re-encode); explained in code with rationale.
- **ItemID chain pre-allocation** for linked TextFrames (`_preallocate_chain_ids`) so NEXTITEM/BACKITEM resolve.
- **HCMS / PDF ICC pass-through** keeps render colors stable.
- **Bleed dimensions guarded** in `extra_pdf_attrs` (see `BLEED_GUARDED` set).

**Ergonomics findings for LLM emission (HIGH confidence):**

- **The `_Frame` base mixes mm and pt geometry.** A frame can be authored with `(x_mm, y_mm, w_mm, h_mm)` OR with `(xpos_pt, ypos_pt, width_pt, height_pt)`, and the converter currently emits BOTH on every frame (see `_resolve_xy_pt` in `tools/sla_to_dsl.py:364-374` plus the kwargs-stuffing in `_convert_pageobject:570-582`). For an LLM rebuilding from PDF or spec, the pt overrides are noise. The DSL should keep them but make them *explicitly opt-in* (e.g. `xpos_pt=...` only when sub-ulp byte-equivalence is required).
- **`anchor=` semantics are subtle** (`primitives.py:106-153`): strings like `"top-center"`, `"bottom-20"`, tuples like `("center", 30)`, and `("right-15", "bottom-4")` all do different things. An LLM is likely to guess wrong with positional or string-tuple anchors. For LLM-friendliness: either restrict to one form or document strict rules. CONTEXT.md D2 prefers verbose+predictable, so a single-form `anchor=Anchor(h="center", v="bottom", margin_mm=20)` would be more emit-friendly than the current overloaded string DSL.
- **`Run` accepts both the typed dataclass and a legacy `(text, dict, sep)` tuple form** (`primitives.py:258-283`). Legacy form should be flagged for review — keep it for `blocks.py` migration only, drop from public surface for new emission paths.
- **`TextFrame.style` vs `TextFrame.trail_style` vs `TextFrame.default_style_attrs` vs `TextFrame.text_align`** is a four-channel API for "what paragraph style does this frame use." An LLM authoring from a spec brief has no way to choose between them without reading the converter. This is the single highest-cost ergonomics issue for the spec→build.py path.
- **`Polygon` doubles as Line and arbitrary shape.** The converter even emits ex-Lines as Polygons with `custom_path` (`sla_to_dsl.py:738-753`). The `Line` primitive in `primitives.py` is therefore essentially dead code from the converter's perspective. Either remove `Line` from public surface or document that it's spec-input only.
- **`Color`/`Style` enums are class-attribute strings**, not real enums. `Color.DUNKELGRUEN == "Dunkelgrün"`, fine, but an LLM emitting `fcolor=Color.DUNKELGRUEN` needs to know the import. The plain string `"Dunkelgrün"` works just as well and is what the converter emits — the enum gives no real safety. For LLM emission these are noise; for human authoring (which CONTEXT.md says we don't optimize for), they help discoverability. Recommend: keep `Color`/`Style` for blocks code, drop from converter output.
- **`_format_path_coord` and `_fmt_num` precision rules** (`primitives.py:22-35`, `document.py:50-72`) are tuned for byte-equivalent SLA round-trip. PDF→build.py and spec→build.py paths will not need this precision; the DSL should make round-trip-precision opt-in via `xpos_pt=` etc. (already the case), and the *converter* should stop emitting it when it isn't needed.
- **`Document(palette_replaces_ci=True)` is set in all three converted templates** so the brand `ci.yml` colors are NOT auto-injected. The whole CI palette is then *manually re-listed* via `doc.add_color(...)` calls, including identical-CMYK brand colors (Black, Dunkelgrün, Gelb, Hellgrün, Magenta, White, Registration). This defeats the "single source of truth" point of `shared/ci.yml`.
- **`Document(__init__)` has 18 kwargs.** That's fine for an AI emitter, but several are converter-byte-equivalence hooks (`doc_page_width_pt`, `doc_page_height_pt`, `palette_replaces_ci`, `extra_doc_attrs`, `extra_pdf_attrs`) that the spec→build.py path will not need. A `Brand(...)` wrapper that supplies safe defaults for these is a clean win.

**Existing blocks coverage (`blocks.py`):**

| Block | Used by any current `build.py`? | Notes |
|---|---|---|
| `Headline4Line` | NO | Closest match: Plakat/Postkarte multi-line headlines using `Run(paragraph_style=...)`. Block produces 1 TextFrame with 4 runs — close, but the converter doesn't currently emit it; templates use raw `TextFrame`. |
| `StoererBadge` | NO | Postkarte has the rotated pink-circle störer (lines 195-225 of postkarte build.py: `Polygon(shape='ellipse', fill='Magenta', rotation_deg=351)` + offset TextFrame). Block API doesn't match the actual rotated-pair shape used. |
| `ImpressumLine` / `ImpressumBlock` | NO | Postkarte and Zeitung both have an Impressum frame; both render via raw `TextFrame` with `trail_style='Impressum'` and a long verbatim text. |
| `SocialHandlesVertical` | NO | Postkarte has a 4-line `Kontaktmöglichkeiten` frame; block API is close, but the converter emits raw `TextFrame` with explicit Run list. |
| `LogoCorner` | NO | None of the three templates use it; the originals embed inline images via `inline_image_data=`. |
| `EventDetails` | NO | Hypothetical; not used. |
| `Masthead` | NO | Zeitung has a "Zeitungs / name" Titelseite-Header frame; block could plausibly fit but is currently unused. |
| `ContentTeasers`, `ArticleHeadline`, `ArticleBody`, `QuoteSidebar` | NO | Aspirational. |

**Conclusion: every `build.py` in the repo today is purely primitive-level. The blocks layer is aspirational and untested against actual originals.** This is the top finding for the review: blocks were designed forward (what we wished templates looked like) rather than backward from the corpus (what idioms actually recur). The hardening must rebuild blocks from the corpus.

**`tools/check_ci.py` — what brand validation currently catches:**
- Critical: a CI brand color (Dunkelgrün/Hellgrün/Gelb/Magenta/Black/White/Registration) is missing OR has wrong CMYK/RGB values.
- Critical (only): missing **brand-primary** (`role: brand-primary` → Dunkelgrün) is critical; other missing colors are info.
- Warning: an SLA color or style is not in CI (legacy / template-local).
- Info: a style is `Default Paragraph Style*` (Scribus internal).

What it **doesn't** catch today:
- PARENT-inheritance correctness (a STYLE re-emits a parent attribute).
- Font drift in the brand stack (uses `Gotham Narrow Bold` where CI says `Gotham Narrow Book`).
- Fontsize/linesp drift in the named CI styles (e.g. an SLA `Headline sehr wichtig` with `fontsize=24` vs CI's 27).
- `extra_doc_attrs` drift between templates — the new `Brand`-injected defaults will need a separate validator.

### Converter (`tools/sla_to_dsl.py`)

**Inventory:** 1203 LOC, single-file. Public entrypoint `convert(sla_path, out_path, template_id, assets_dir)`. Strict mode (CONTEXT D6 / `UnhandledElement`) — raises on any attribute the DSL can't translate.

**What it does well:**
- Captures every PDF-element ICC profile attribute via `extra_pdf_attrs` so render colors stay stable.
- Round-trips inline images verbatim as base64 — no PNG re-encode.
- Detects text-frame chains (`_detect_chains`) and emits explicit `link_to(...)` post-construction.
- Scans `<para>`, `<DefaultStyle>`, `<var>`, `<trail>` against the closed override sets and raises if it finds anything new.

**What it skips / where it leaks (HIGH confidence):**
- **No deduplication of `extra_*_attrs` against a brand profile.** Every template gets the same ~136-key dict literal expanded inline. Concrete numbers (computed by walking the three current `build.py` files):

  | Field | Plakat | Postkarte | Zeitung | In all 3 | Identical value across all 3 | Differing values |
  |---|---|---|---|---|---|---|
  | `extra_doc_attrs` | 136 | 136 | 136 | **136** | **113** | 23 |
  | `extra_pdf_attrs` | 45 | 45 | 45 | **45** | **34** | 11 |

  The 23 truly-template-specific `extra_doc_attrs` keys are: `AUTOCHECK, DPIn3, DPInCMYK, DPPr, GROUPC, GapVertical, GuideRad, MAJGRID, MINGRID, PAGESIZE, POLYF, SHOWBASE, SHOWGRID, SHOWGUIDES, SHOWMARGIN, ScratchBottom, ScratchLeft, ScratchRight, ScratchTop, calligraphicPenAngle, dispX, dispY, renderStack`. Most of those are user-pref/UI-state values that don't affect render output (`SHOWGRID`, `dispX`, `renderStack`, `ScratchBottom`, etc.) — they could safely become DSL defaults too with a smaller "if you really need it, override" surface.

  The 11 differing `extra_pdf_attrs` keys: `ImageP, InfoString, PicRes, PrintP, RGBMode, RecalcPic, SolidP, UseProfiles2, Version, bleedMarks, useDocBleeds`. These ARE render-affecting (ICC profiles, RGB mode, picture resolution) and stay per-template.

- **Every per-frame call carries 8 geometry kwargs** (`x_mm`, `y_mm`, `w_mm`, `h_mm`, `xpos_pt`, `ypos_pt`, `width_pt`, `height_pt`) even though the mm pair is mathematically derivable from the pt pair (and vice versa). The pt overrides exist *only* for sub-ulp-precision byte-equivalent SLA round-trip on certain inline-image frames. For a re-authored template gated by visual diff (not byte diff), the pt overrides are pure noise.

- **`palette_replaces_ci=True` is set on all converter outputs**, suppressing the brand `ci.yml` entirely and re-listing every CI color manually. This makes the output completely self-contained, but breaks the "single source of truth" model the CI YAML was built for. A re-authored template should default to `palette_replaces_ci=False` and only register *additions* via `add_color`.

- **`Default Character Style` is re-emitted in every template with all 22 default attrs**, even though Plakat and Postkarte are byte-identical here and Zeitung differs only in `font='Gotham Narrow Book'` vs `'Gotham Narrow Black'` and `fontfeatures='-clig'`.

- **`Default Paragraph Style` is re-emitted in every template** with the same 18 defaults; Zeitung adds `font/fontfeatures/space_after_pt`. Identical-prefix block, suitable for a brand-default helper.

- **`Impressum` para style**: present in all 3, content varies only in `fontsize` (5 / 8 / 20) and `linesp` (6 / 9 / 20) and `fcolor` (default / `White` / default). Trivially parameterizable.

- **One-line giant dicts.** `extra_doc_attrs={...}` is emitted on a single line of 6.5–7 KB (135+ keys). Not a correctness issue, but makes diff review impossible. A `Brand`-driven approach would shrink this to a 2–4 line override block per template.

- **Round-trip story (SLA → build.py → SLA):** the existing tests demonstrate byte-equivalent (or visually indistinguishable) round-trip for all three templates today. Nothing here is *wrong*; the issue is that the emitter optimizes for "same SLA bytes back" rather than "minimum LLM-emittable shape" — which is now the priority.

### `build.py` corpus (3 templates)

**Top-level LOC and structural decomposition (HIGH confidence, measured):**

| Section | Plakat (235) | Postkarte (437) | Zeitung (3244) |
|---|---|---|---|
| Imports / scaffolding | 5 | 5 | 5 |
| Blank lines | 18 | 27 | 150 |
| `doc = Document(...)` block (incl. extras) | 19 | 19 | 19 |
| `doc.add_color` calls (1 per line) | 5 | 8 | 8 |
| `doc.add_para_style` calls (1 per line) | 5 | 9 | 23 |
| `doc.add_char_style` calls (1 per line) | 1 | 2 | 1 |
| `doc.add_master(...)` blocks | 11 | 11 | 22 (2 masters) |
| `page = doc.add_page(...)` blocks | 10 (1 page) | 20 (2 pages) | 140 (14 pages) |
| `page.add(TextFrame/ImageFrame/Polygon)` blocks | 154 (9 frames) | 329 (18 frames) | 1847 (98 frames) |
| Run-list interior + `link_to()` (continuation lines) | 7 | 7 | 1029 |

**Frame counts per template (HIGH confidence, regex-matched):**

| | Plakat | Postkarte | Zeitung |
|---|---|---|---|
| `TextFrame(...)` total instances | 6 | 7 | 112 |
| `ImageFrame(...)` total instances | 3 | 8 | 20 |
| `Polygon(...)` total instances | 0 | 3 | 8 |
| `Run(...)` instances | 12 | 26 | 416 |
| `runs=[ ]` text-frame openings | n/a | n/a | 84 |
| `clip_edit=True` flag | rare | rare | **87** of 146 frames |
| `var='pgno'` (page-number var) | 0 | 0 | **12** (one per inner page) |
| `inline_image_data=` (verbatim base64) | 0 | 7 (logos/icons) | 6 |
| `custom_path='M0 0 L…'` (rect-as-path) | 0 | 0 | **86** (clip-edited frames) |

**Recurring idioms by frequency (Zeitung, the largest signal):**
- `clip_edit=True` + `custom_path='M0 0 L<w> 0 L<w> <h> L0 <h> L0 0 Z'` + `fill_rule=0` on **86 of the 98 page-frames** — Scribus stored the verbatim rectangle path because the user manually edited the clip path once. This is structural noise for an AI re-author. Could become a single helper attribute (`preserve_clip_path=True`) or the DSL could auto-emit this combo when `clip_edit=True`.
- `Run(text='', has_itext=False, var='pgno', separator='para', paragraph_style='Seitenzahl')` appears **12 times** verbatim across pages 1–12 of the Zeitung. **Crystal-clear PageNumber block candidate** — same TextFrame coordinates per facing-pages side, same `var='pgno'` payload.
- `paragraph_style='Seitenzahl'` (12 occurrences), `paragraph_style='Fließtext'` (many), `paragraph_style='Überschrift weiß'` (5 frames) — these recur but with different content; classic block-able layouts.
- The Zeitung's two masterpages (`Neue Musterseite rechts`, `Neue Musterseite links`) are mostly mirror images. Both carry identical layouts on facing pages, plus a left/right-flipped column gutter. Strong "facing-pages master layout" candidate for a `MasterLayout(left_master=..., right_master=...)` helper.
- `Polygon(fill='Dunkelgrün', custom_path='M0 0 L…')` covering an entire page as background (`page0.add(Polygon(...))` first call on Postkarte page0/page1 and Zeitung Titelseite). Candidate for `PageBackground(color='Dunkelgrün')`.

**Per-template noise breakdown:**
- **Plakat A1 (235 lines):** ~58 lines of structural overhead (imports + Document + color/style/master/page setup) and ~177 lines of frame definitions for 9 frames (~20 lines/frame). Smallest absolute win from refactoring.
- **Postkarte A6 (437 lines):** ~108 lines of overhead and ~329 lines for 18 frames (~18 lines/frame). Mid-size win; hosts the störer-rotated-pair, contact-block, impressum-with-icons, and a clean front/back masterpage layout that maps well to a `MasterLayout` helper.
- **Zeitung A4 (3244 lines):** ~232 lines of overhead and ~3012 lines of frame definitions + run lists for 146 frames (~21 lines/frame including run list expansions averaging 3-5 runs/frame). The bulk of this is structural verbosity (per-frame 8 geometry kwargs + clip_edit + custom_path-rectangle) and Run lists. A `Brand`-driven hoist saves ≈15 lines per template up front, plus a converter change to drop redundant pt-overrides could save ~3 lines per frame on byte-non-critical frames (≈400 lines on Zeitung alone).

**Drift between the three templates (concrete):**
- All three call `Document(..., palette_replaces_ci=True, hcms=True, deffont='Gotham Narrow Black' or 'Gotham Narrow Book', defsize=12, ...)`.
- All three list the same 5–8 brand colors (Plakat is the smallest with 5 — missing Hellgrün, Magenta, Green).
- `Default Paragraph Style` is identical between Plakat and Postkarte (18 attrs); Zeitung adds 3 more (`font`, `fontfeatures`, `space_after_pt=5`). All three could share a base.
- `Default Character Style` differs only in `font` (Black/Black/Book) and `fontfeatures` (''/''/'-clig').
- `Impressum` para style differs only in fontsize/linesp/fcolor (parameterizable).
- `Fließtext` differs in fontsize (50/12) and align (left/center) — same family, different sizing.
- All three masterpages carry verbatim `bleed_mm=3.0000000000000013` (the float-repr of `mm_to_pt^-1(8.504...)` ≈ 3 with sub-ulp jitter). A `Brand` default of `bleed_mm=3` would be cleaner.

## Higher-level construct proposals (options, NOT decisions)

### Brand-level construct

**Option A (recommended): `Brand` dataclass passed to `Document(brand=...)`.**

```python
# tools/sla_lib/builder/brand.py (new file, ~120 LOC)
@dataclass(frozen=True)
class Brand:
    """A brand profile bundling defaults, palette, styles, and PDF state.
    Pass to Document(brand=Brand.GRUENE_NOE) to inject all brand defaults."""
    name: str
    short: str
    colors: dict[str, BrandColor]                       # from ci.yml
    para_styles: dict[str, ParaStyle]                   # default brand paragraph styles
    char_styles: dict[str, CharStyle]                   # default brand char styles (often just the default)
    layers: list[DocumentLayer]                         # default layer stack
    default_doc_attrs: dict[str, str]                   # the 113 identical keys
    default_pdf_attrs: dict[str, str]                   # the 34 identical keys
    deffont: str = "Gotham Narrow Book"
    defsize: float = 12
    column_gap_default_pt: float = 11.0
    bleed_mm: float = 3.0

    @classmethod
    def gruene_noe(cls) -> "Brand":
        """Load from shared/ci.yml + shared/ci-defaults.yml (new file holding
        the 113 + 34 identical extras that were leaking into every template)."""
        ...

# Usage in build.py:
doc = Document(template_id="postkarte-a6-kampagne",
               brand=Brand.gruene_noe(),
               extra_doc_attrs={"PAGESIZE": "A6", "ScratchTop": "20.001"},  # the 23 differing keys
               extra_pdf_attrs={"Version": "14", "useDocBleeds": "1"})       # the 11 differing keys
```

Trade-offs: clean, single-construct, easy to validate. Forces a new file; requires the converter to emit `brand=Brand.gruene_noe()` and only the diff-from-brand `extra_doc_attrs`.

**Option B: extend `ci.py`'s `_CI` class with `default_doc_attrs`/`default_pdf_attrs` loaded from extended `ci.yml`.**

Smaller surface (no new dataclass), but conflates "brand identity" with "Scribus-runtime defaults" which are arguably different concerns. Existing `Color`/`Style` enums make it less obvious where the defaults come from.

**Option C: `Document(__init__)` reads brand defaults eagerly, no Brand object at all.**

Cheapest to implement; the `Document(...)` call in build.py just stops listing identical extras. But it leaks "Grüne NÖ"-specific defaults into the DSL, which the multi-input adapter design (PDF/InDesign/spec) will eventually want to override per source.

**Recommendation:** Option A. CONTEXT.md D6 mandates "hoist common values to DSL defaults" but explicitly preserves the escape hatch — a `Brand` object both hoists *and* makes the inheritance visible to an LLM emitter.

**Worked example — Postkarte's first ~100 lines:**

Today (lines 15-65 of `templates/postkarte-a6-kampagne/build.py`, ≈51 lines):

```python
doc = Document(
    title='', template_id='postkarte-a6-kampagne', author='', facing_pages=False,
    column_gap_default_pt=11, deffont='Gotham Narrow Black', defsize=12,
    first_page_num=1, palette_replaces_ci=True, hcms=True,
    doc_page_width_pt=297.637795275591, doc_page_height_pt=419.527559055118,
    extra_doc_attrs={'ALAYER': '0', 'AUTOCHECK': '0', ... 134 more keys ... },  # 1 megabyte-line
    extra_pdf_attrs={'CMethod': '0', ... 44 more keys ... },                    # 1 megabyte-line
    layers=[DocumentLayer(name='Hintergrund', visible=True, printable=True, ...)],
)
doc.add_color('Black', cmyk=(0, 0, 0, 100))      # 8 calls, all CI-redundant
... 7 more brand colors verbatim ...
doc.add_char_style(CharStyle(name='Default Character Style', font='Gotham Narrow Black', ... 22 attrs ... ))  # 2 lines
doc.add_char_style(CharStyle(name='Default Character Style (2)', ...))                                       # 2 lines
doc.add_para_style(ParaStyle(name='Default Paragraph Style', ... 18 attrs ... is_default=True))               # 1 line of 350 chars
... 8 more ParaStyles, 1 line each ...
```

After Option A, ≈18 lines:

```python
doc = Document(
    title='', template_id='postkarte-a6-kampagne',
    brand=Brand.gruene_noe(),                                # injects palette + base styles + 113+34 default attrs
    facing_pages=False,
    doc_page_width_pt=297.637795275591, doc_page_height_pt=419.527559055118,
    extra_doc_attrs={'PAGESIZE': 'A6', 'AUTOCHECK': '0',     # only the 23 differing keys
                     'ScratchTop': '20.001', ...},
    extra_pdf_attrs={'Version': '14', 'PicRes': '300', ...}, # only the 11 differing keys
)
# CI brand colors auto-registered by Brand. Add only template-specifics:
doc.add_color('Green', rgb=(153, 102, 51))
# CI-default styles auto-registered by Brand. Add only template-specifics:
doc.add_para_style(ParaStyle(name='Schrift rosa Kreis', font='Gotham Narrow Ultra',
                              fcolor='White', fontsize=10, linesp=11, align=1))
doc.add_para_style(ParaStyle(name='Headline sehr wichtig', font='Gotham Narrow Ultra',
                              fcolor='White', fontsize=27, linesp=23, align=1, kern=1))
doc.add_para_style(ParaStyle(name='Vollkorn Headline sehr wichtig', font='Vollkorn Black Italic',
                              fcolor='Gelb', fontsize=27, linesp=23, align=1))
doc.add_para_style(ParaStyle(name='Unterüberschrift', ...))
doc.add_para_style(ParaStyle(name='Kontaktmöglichkeiten', ...))
# Impressum para style now comes from Brand defaults.
```

Roughly **−33 lines on Postkarte's setup block alone**, and the result is dramatically more legible — the 7 KB of `extra_doc_attrs` is gone from the diff.

### Content blocks

Drive the block list **from the corpus**, not from imagination. The five blocks below are the ones with at least 2 instances across the three current templates plus a clear LLM-emit story.

**Option A: 5 evidence-driven blocks, replacing the current 8.**

```python
@dataclass
class PageNumber:
    """Page-number TextFrame with <var name='pgno'/>. Used 12× in Zeitung."""
    pos: Anchor                                           # required
    style: str = "Seitenzahl"                             # paragraph style name
    fcolor: Optional[str] = None                          # None = inherit from style
    w_mm: float = 8
    h_mm: float = 5

@dataclass
class Impressum:
    """Bottom-of-page legal text. Replaces ImpressumLine + ImpressumBlock."""
    text: str = DEFAULT_IMPRESSUM
    pos: Anchor                                           # required
    w_mm: float
    h_mm: float = 6
    fcolor: str = Color.WHITE
    fontsize: Optional[float] = None                      # None = use Brand.impressum_default
    bold_label: bool = True                               # makes "Impressum:" Gotham Narrow Bold

@dataclass
class PageBackground:
    """Full-bleed colored rectangle (PTYPE=6 polygon, layer 0).
    Used as page0/page1 first frame in Postkarte (Dunkelgrün) and Zeitung Titelseite."""
    color: str = Color.DUNKELGRUEN
    bleed_mm: float = 3
    line_color: Optional[str] = None
    line_width_pt: float = 0

@dataclass
class ContactBlock:
    """Multi-line contact info on a postcard back. Replaces SocialHandlesVertical
    and the Postkarte 'Kontaktmöglichkeiten' frame."""
    handles: Sequence[str]                                # one line per entry
    pos: Anchor
    w_mm: float
    h_mm: float
    style: str = "Kontaktmöglichkeiten"                   # or Brand default
    fcolor: str = Color.WHITE
    icons: Optional[Sequence[str]] = None                 # icon image paths, one per handle

@dataclass
class ColumnTextStory:
    """A linked-frame text-flow story. Wraps the TextFrame.link_to chain pattern."""
    frames: Sequence[TextFrame]                           # the frames to link in order
    runs: Sequence[Run]                                   # the story content
    # Lays out runs sequentially across the linked frames; emitter pre-allocates IDs.
```

**Option B:** keep the current 8 blocks, deprecate the unused 4 (`LogoCorner`, `EventDetails`, `ContentTeasers`, `ArticleHeadline`/`ArticleBody`/`QuoteSidebar`/`Masthead`), and fix the 4 that map to actual idioms (`Headline4Line`, `StoererBadge`, `ImpressumLine`, `SocialHandlesVertical`) to match the corpus shape exactly.

**Option C:** Defer blocks entirely to a follow-up issue, and ship only `Brand` + converter cleanup in this issue. Lower risk, but means migration of existing templates can't yet collapse onto blocks.

**Recommendation:** Option A, plus a one-line deprecation note on the existing 8 (CONTEXT D2 says verbose and predictable — replacing 8 fictional blocks with 5 evidence-driven ones is in scope). The replaced blocks remain available under `blocks.legacy` for a release if external consumers exist (none in this repo).

**Block file split:** Stay in `blocks.py` until file exceeds ~600 lines. Five new blocks + helpers will fit comfortably.

### Page-template / `MasterLayout` layer

**Option A (recommended): `MasterLayout` for facing-pages publications.**

```python
@dataclass
class MasterLayout:
    """A pair (or single) of master-page definitions.
    Generates the masters and binds doc pages to the appropriate side."""
    name: str
    size: str | tuple[float, float] = "A4"
    margins_mm: tuple[float, float, float, float] = (21, 21, 21, 21)
    bleed_mm: float = 3
    facing: bool = False
    items_left: list = field(default_factory=list)        # items emitted on left master
    items_right: list = field(default_factory=list)       # items emitted on right master (or single)

    def apply(self, doc: Document) -> None:
        """Register masters on doc; users then add_page(master=name+'_left'/'_right')."""
```

**Option B:** keep masters at the `Document.add_master()` level (current), but offer a `Document.add_facing_pages_masters(name='Inhalt', items_left=[...], items_right=[...])` convenience.

**Recommendation:** Option B. The Zeitung is the only multi-master template today; adding a third construct (`MasterLayout`) for it alone is over-engineering. The convenience wrapper saves the duplication without adding API surface.

**Estimate of line-count delta on Zeitung:**

| Source of reduction | Lines saved | Notes |
|---|---|---|
| Hoist 113 identical extra_doc_attrs to Brand defaults | ~5 (the line, but ~7 KB on disk and 1 megaline of diff noise) | The line is one giant blob; LOC change is tiny but emit/diff usability skyrockets |
| Hoist 34 identical extra_pdf_attrs to Brand defaults | ~3 | Same caveat as above |
| Drop redundant `xpos_pt`/`ypos_pt`/`width_pt`/`height_pt` from non-byte-equivalent frames | **~250-400** | Each frame currently emits 4 redundant lines; if visual-diff-only template (Zeitung's first re-author target), every frame becomes 4 lines lighter → 98 frames × 4 ≈ 400 |
| Replace 12 page-number frames with `PageNumber(...)` | **~200** | Each page-number TextFrame today is ~16 lines; PageNumber is 1-3 lines |
| Replace 86 `clip_edit=True` + verbatim rect-path frames with implicit DSL emit | **~170** | Each currently emits `clip_edit=True, custom_path='M0 0 L…', fill_rule=0` (3 lines); becomes 1 (`clip_edit=True`) if DSL auto-emits the rect path |
| Replace 14 page setup blocks (`page = doc.add_page(...)`) with a `for` loop using `MasterLayout` | **~130** | Pages 1-13 are 10-line blocks each, mostly identical; collapse to a 3-line factory |
| Replace 23 `add_para_style(ParaStyle(...))` lines with a single `Brand.zeitung_styles()` import | **~22** | Most are identical mappings; only 5-6 truly Zeitung-specific |

**Total Zeitung delta estimate (HIGH confidence on direction, MEDIUM on magnitude):** 800-1100 lines, taking the file from 3244 → ≈2150-2450. Postkarte: 437 → ≈250-280. Plakat: 235 → ≈170-180.

The big remaining residue (≈1500 lines on Zeitung) is the actual content — Run lists, headlines, body-text, image references — which is *irreducible* and is exactly what an LLM should be authoring per template.

## Multi-input adapter requirements on the DSL

### SLA input (current path) — what must not regress
- All eight existing closed override sets stay closed (`PARAGRAPH_OVERRIDE_ATTRS`, `DEFAULTSTYLE_OVERRIDE_ATTRS`, `VAR_OVERRIDE_ATTRS`, `PAGEOBJECT_HANDLED_PRIM`, the four converter-side `*_HANDLED` sets).
- Inline-image base64 verbatim round-trip stays.
- ItemID chain pre-allocation stays.
- HCMS / PDF ICC pass-through stays.
- The visual-diff gate (`tools/visual_diff.py` invoked by `bin/render-gallery`) keeps the existing tolerance — render fidelity reverification is the gate, not byte-equivalence of the rebuilt SLA.
- The DSL must continue to support `xpos_pt/ypos_pt/width_pt/height_pt` overrides on individual frames so the round-trip-precision-required path (≈the 6 inline-image frames in Zeitung that have HEIGHT='27.7755590551181') still works. The change is making them *opt-in* rather than *always emitted*.

### PDF input — what the DSL must absorb
- **PDF→build.py recovery loses paragraph-style names.** A PDF carries fonts/sizes/colors per glyph but not "this paragraph belongs to style `Headline sehr wichtig`". The AI emitter would need to **infer** style identity from font+size+color clusters, then map to brand styles via a closed lookup. The DSL must be comfortable with `style=None` + `default_style_attrs={'FONT': ..., 'FONTSIZE': ...}` per-frame as the fallback path. Current DSL supports this; no change required.
- **PDF gives word/character bounding boxes, not frame extents.** Frames must be reconstructed by clustering glyph positions (pdfplumber/pymupdf). The DSL needs no changes here, but the `anchor=` channel becomes useless from PDF input — only absolute mm coords work. Verify that `x_mm/y_mm/w_mm/h_mm` (without `anchor=`) is sufficient for every existing primitive.
- **PDF text reading order may not match SLA story order.** Linked text-frame chains (`a.link_to(b)`) become hard to recover. Recommend: spec-input or InDesign-input remain the primary paths for chained stories; PDF input is for posters and single-frame layouts only. Document this.
- **PDF colors are post-ICC.** The DSL's CMYK-named-color story (`Color.DUNKELGRUEN` → CMYK 85/35/95/10) would need a PDF→CMYK→brand-color reverse lookup. Easiest: require the PDF input pipeline to take the brand profile as a side input and snap colors to the nearest brand color within a tolerance.
- **No DSL changes proposed for the PDF path now.** The DSL is already sufficient; the converter is what changes.

### InDesign input (IDML) — what the DSL must absorb
- **IDML is a ZIP of XMLs** (`designmap.xml`, `Spreads/`, `Stories/`, `MasterSpreads/`, `Resources/`). Python tooling: `SimpleIDML` (Starou/SimpleIDML), maintenance status MEDIUM ([repo](https://github.com/Starou/SimpleIDML), maintenance lightly active).
- **InDesign style names** map directly to Scribus paragraph-style names (both have named paragraph + character styles), so the DSL's existing `style=`/`paragraph_style=`/`char_style=` channels work. The IDML→build.py converter would need a brand-style remap table (e.g. InDesign `Body Text` → SLA `Fließtext`).
- **IDML masterspread = SLA masterpage.** Direct mapping. The proposed `Document.add_facing_pages_masters(...)` convenience would be the natural target.
- **IDML stores text in `Stories/Story_<id>.xml` referenced by frame `ParentStory` attribute.** Linked-frame chains map directly to TextFrame.link_to. DSL is ready.
- **IDML has run-level character formatting via `<CharacterStyleRange>`** which maps cleanly to `Run(font=..., fontsize=..., fcolor=...)`. DSL is ready.
- **Likely DSL gap:** InDesign supports text **decoration** (drop caps, paragraph rules, baseline shift) the DSL currently doesn't surface. `ParaStyle` already has `drop_cap`, `drop_lines`, `baseline_offset`, `paragraph_effect_offset` — coverage is adequate. Verify against the corpus before claiming completeness; if a gap surfaces, add the field to `ParaStyle` (closed surface stays closed).

### Spec input — proposed spec schema sketch

Goal: a small, LLM-emittable, human-reviewable description that an AI can turn into a valid `build.py`. Recommend YAML with frontmatter-style structure (familiar to designers; jq/yq-readable).

```yaml
# templates/foo-a4/spec.yml
template:
  id: foo-a4
  title: "Foo A4 Hochformat"
  size: A4
  orientation: portrait
  facing_pages: false
  bleed_mm: 3

brand: gruene-noe                                      # → loads Brand.gruene_noe() into Document(brand=...)

styles:                                                # template-specific extras only
  big-headline:
    parent: ci/headline-ultra
    fontsize: 36
  contact-line:
    parent: ci/impressum
    fontsize: 8

pages:
  - layout: cover                                      # named layout from layouts/ below
    background: Dunkelgrün
    headline:
      style: big-headline
      lines:
        - { text: "Hier steht eine", color: White }
        - { text: "vierzeilige", color: Gelb }
        - { text: "Überschrift", color: White }
    impressum:
      text: "Medieninhaber..."
    page_number: false

  - layout: content
    title: "Artikel Headline"
    body_columns: 3
    body: |
      Lorem ipsum...
    quote: "Pull-Quote in Vollkorn"

layouts:                                               # reusable named layouts
  cover:
    page_background: { color: brand.primary }
    headline_pos: top-center
    impressum_pos: bottom-center
  content:
    title_pos: { x_mm: 21, y_mm: 21 }
    body_pos: { x_mm: 21, y_mm: 50, w_mm: 168, h_mm: 240 }
```

The AI authoring path: `spec.yml` → reasoning step → typed Python `build.py` using `Brand`, blocks, primitives. The DSL is rich enough today to represent everything in the schema above; the spec→build.py *converter* is deferred (CONTEXT.md), but the schema sketch is the contract that converter will need to honor.

**DSL implications of the spec path:**
- Need a way to express "page background = full-bleed Polygon at layer 0" cleanly → `PageBackground` block (proposed above) covers this.
- Need to support symbolic color references (`brand.primary`) → already covered by `Color.DUNKELGRUEN`-style strings; the YAML→build.py converter resolves `brand.primary` to `Color.DUNKELGRUEN` at emit time.
- Need named layouts (e.g. `cover`, `content`). These would live in either the template's own file or a shared layouts library. Proposal: keep them in the template's `build.py` as plain Python functions taking a `Page` and emitting frames — no new DSL construct needed.

## Default-hoisting opportunities

**Concrete `extra_doc_attrs` keys that should become DSL/Brand defaults (all 113 are identical across the 3 templates; here are the highest-value ones):**

| Key | Value | Reason |
|---|---|---|
| `ALAYER`, `AUTOL`, `AUTOMATIC`, `BASEGRID`, `BASEO` | constants | Scribus runtime defaults, never vary in this brand |
| `BaseC` | `#c0c0c0` | UI grid color |
| `CPICT`, `CSPICT` | `None` | image clipping defaults |
| `DPIn`, `DPIn2`, `DPSFo`, `DPSo`, `DPbla`, `DPgam`, `DPuse` | constants | display profile state |
| `EmbeddedPath`, `EndArrow`, `StartArrow` | `0` | path/line defaults |
| `FirstLineOffset` | `1` | typography default |
| `GapHorizontal`, `GapVertical` | constants | scratch-canvas layout |
| `GridType`, `GuideC`, `MAJORC`, `MINORC` | constants | UI grid colors |
| `PEN`, `PENLINE`, `PENSHADE`, `PENTEXT`, `BRUSH`, `BRUSHSHADE` | brand defaults | already half-handled by `_doc_attrs()` but currently overridden by `extra_doc_attrs` |
| `POLYC`, `POLYCUR`, `POLYF`, `POLYIR`, `POLYOCUR`, `POLYR`, `POLYS` | shape defaults | never vary |
| `STIL`, `STILLINE`, `WIDTH`, `WIDTHLINE` | line-style defaults | never vary |
| `SUBJECT`, `TabFill`, `TabWidth`, `TextBackGround`, `TextBackGroundShade`, `TextDistBottom/Left/Right/Top`, `TextLineColor`, `TextLineShade`, `TextPenShade`, `TextStrokeShade` | text frame defaults | never vary |
| `UnderlinePos`, `UnderlineWidth`, `StrikeThruPos`, `StrikeThruWidth`, `VHOCH`, `VHOCHSC`, `VKAPIT`, `VTIEF`, `VTIEFSC` | typography defaults | never vary |
| `arcStartAngle`, `arcSweepAngle`, `calligraphicPen*`, `constrain`, `currentProfile`, `spiralEndAngle`, `spiralFactor`, `spiralStartAngle`, `rulerMode`, `rulerXoffset`, `rulerYoffset`, `showcolborders`, `showrulers` | UI/tool defaults | never vary |

**Concrete `extra_pdf_attrs` keys that should become DSL/Brand defaults (all 34 identical):**

`Articles, Bookmarks, CMethod, Clip, Compress, Encrypt, FontEmbedding, Grayscale, ImagePr, Intent, Intent2, MirrorH, MirrorV, PageLayout, PassOwner, PassUser, Permissions, PresentMode, Quality, RotateDeg, Thumbnails, UseLayers, UseLpi, UseProfiles, UseSpotColors, colorMarks, cropMarks, displayBookmarks, displayFullscreen, displayLayers, displayThumbs, doMultiFile, docInfoMarks, fitWindow, hideMenuBar, hideToolBar, openAfterExport, rangeSel, rangeTxt, registrationMarks` (covers the 34; truncated for brevity).

**Per-frame raw-attr keys that recur and should become semantic fields:**

| Pattern | Frequency | Proposed semantic field |
|---|---|---|
| `clip_edit=True` + `custom_path='M0 0 L<w> 0 L<w> <h> L0 <h> L0 0 Z'` + `fill_rule=0` | 86× in Zeitung, 1× in Postkarte | When `clip_edit=True` and frame is a rectangle, DSL emits this combo automatically. New `clip_edit=True` alone implies the verbatim rect path. |
| `default_linesp_mode=2` | recurring on text-bearing frames | Should be the DSL default for any frame whose paragraph style has `linesp_mode=2` (baseline-spacing); auto-derive from style when unset. |
| `line_width_pt=1` (with no PCOLOR2) | nearly every frame | This is a Scribus default; emit only when ≠ 0 OR when PCOLOR2 is set. Today emits everywhere → noise. |
| `local_scale=(<float>, <float>)` for inline-image scaling | 7 in Postkarte, 6 in Zeitung | Already a semantic field; just need a `fit_to_frame=True/False` shortcut for the common case. |
| `column_gap=0` on TextFrames with COLUMNS=1 | many | When `columns=1`, `col_gap_mm` is meaningless and should not emit. |

## Review-execution scaffolding

### Exact paths the executor must point `/issue:review` at

The review must read the actual code (per `feedback_review_no_code_in_prompt.md`) — no diffs in prompt. The executor invokes `/issue:review <slug>` which auto-detects the issue branch and the surface from acceptance criteria. The relevant code surface:

```
tools/sla_lib/builder/__init__.py            73 LOC
tools/sla_lib/builder/primitives.py         753 LOC
tools/sla_lib/builder/document.py          1028 LOC
tools/sla_lib/builder/styles.py             140 LOC
tools/sla_lib/builder/ci.py                 181 LOC
tools/sla_lib/builder/blocks.py             400 LOC
tools/sla_lib/editor.py                     106 LOC
tools/sla_lib/reader.py                     139 LOC
tools/sla_lib/slot.py                        37 LOC
tools/sla_to_dsl.py                        1203 LOC
tools/check_ci.py                           265 LOC
shared/ci.yml                               128 LOC
templates/plakat-a1-hochformat/build.py     235 LOC
templates/postkarte-a6-kampagne/build.py    437 LOC
templates/zeitung-a4-grun/build.py         3244 LOC
docs/dsl-reference.md                       122 LOC
docs/render-fidelity.md                     280 LOC
                                          ~8970 LOC total
```

Plus secondary context: `tools/sla_lib/tests/test_blocks.py`, `test_builder.py`, `test_dsl_extensions.py`, `test_sla_to_dsl.py`, `test_multipage.py` for behavior probes, and `.research/01-sla-format.md` + `.research/04-scribus-multipage-masters.md` for prior context.

### Recommended review-area split (so each LLM has a focused brief)

The CONTEXT-locked decision is "Claude + Codex + Gemini in parallel via `/issue:review`." Split the review brief by area, so each tool can have a different focus or each tool can run all three areas (the `/issue:review` orchestrator decides). Areas:

1. **DSL surface review.** Files: `tools/sla_lib/builder/*.py`, `tools/sla_lib/{editor,reader,slot}.py`, `docs/dsl-reference.md`. Brief: "Audit the DSL public API for LLM-emission ergonomics. Flag positional traps, magic defaults, redundant channels (e.g. `style` vs `default_style_attrs`), validation gaps, and design issues that would prevent PDF/InDesign/spec→build.py converters from comfortably producing valid `build.py`. Propose typed APIs for any closed override sets that the corpus needs but the DSL doesn't have. Do NOT propose changes to the visual-diff or render-pipeline."
2. **Converter + templates review.** Files: `tools/sla_to_dsl.py`, all three `templates/*/build.py`. Brief: "Audit converter output quality and template duplication. Quantify duplication (already done in RESEARCH.md — verify the numbers). Identify hoisting opportunities for `extra_doc_attrs`/`extra_pdf_attrs`/style-stack into a brand profile. Propose a higher-level construct surface (Brand, blocks, page-template) drawn ONLY from idioms that recur in the existing three templates. Estimate line-count delta for each existing template after refactor. Do NOT propose render-pipeline changes."
3. **Multi-input-readiness review.** Files: `tools/sla_lib/builder/*.py`, `docs/dsl-reference.md`, `shared/ci.yml`, plus implicit research on PDF/IDML/spec input shapes. Brief: "Audit the DSL's readiness to receive AI translations from PDF, InDesign IDML, and a structured spec brief. For each: enumerate the metadata the input carries that the DSL must absorb, the metadata the input loses that the DSL must compensate for, and any DSL gap that blocks a clean input→build.py path. Propose a minimum spec-file schema. Do NOT design the converters themselves — just the DSL-side requirements."

Each reviewer also lists **P1 (must-fix-before-next-template), P2 (should-fix-soon), P3 (nice-to-have)** items.

### Where REVIEW.md goes and what sections it must contain

`.issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md` — co-located with this RESEARCH.md (per CONTEXT decision 5).

Required sections:

```markdown
# REVIEW — Review build.py + DSL before more templates

## Synthesis (orchestrator output)
- Top-3 cross-area findings the three reviewers converged on
- Top-3 disagreements (if any) and how the orchestrator resolved them

## Area A — DSL surface
- (per reviewer × P1/P2/P3 items, with file:line citations)

## Area B — Converter + templates
- (same shape)

## Area C — Multi-input adapter readiness
- (same shape)

## Higher-level construct proposals (concrete API)
- Brand: API + worked example
- Blocks: 5 evidence-driven blocks
- MasterLayout / facing-pages helper

## Line-count delta estimates after P1 refactor
- Postkarte: from 437 → ~X
- Plakat: from 235 → ~X
- Zeitung: from 3244 → ~X

## Prioritized P1 backlog (the executor implements these in this issue)
1. ...
2. ...
3. ...

## P2 follow-up issues to file (deferred)
- (each as a one-liner; planner will queue separately)

## Gating decision
- Confirm: no new templates land before P1 items merge.
- Confirm: existing-template rewrites are themselves the migration follow-ups.

## Per-reviewer raw output
- (Claude / Codex / Gemini transcripts, untouched)
```

## Risks and unknowns

- **Converter dropping `xpos_pt/ypos_pt/width_pt/height_pt` on most frames may regress the byte-equivalent SLA round-trip** that the existing `tools/sla_diff.py` tests rely on. Visual-diff will still pass (all three originals were rendered by Scribus from these SLAs), but `sla_diff` may flag attribute-level differences. Need to check whether the existing test suite gates on `sla_diff` byte-equivalence or only on visual diff. **Action for executor:** before stripping pt-overrides, run `pytest tools/sla_lib/tests/test_sla_to_dsl.py test_sla_diff.py` and check whether they require byte-equivalence. If yes, keep the pt-overrides only on inline-image frames.
- **`palette_replaces_ci=True` deeply baked into the converter.** Switching to `palette_replaces_ci=False` for re-authored templates means the CI brand colors get auto-injected, plus the template-specific extras stack on top. If two templates carry `Black` with slightly different CMYK (they don't today, but check), the merge order must match what Scribus expects.
- **The 23 differing `extra_doc_attrs` keys include some that ARE rendering-relevant** (`PAGESIZE`, `Scratch*` for scratch-canvas position, `renderStack` for layer order). These cannot be brand defaults; they remain per-template. Verify with a render-fidelity test on each template after the brand hoist.
- **Soft-shadow `SoftShadow` defaults differ subtly between templates.** Postkarte uses `Dunkelgrün` shadow; the DSL default is `Black`. Brand-level shadow defaults may help.
- **The five evidence-driven blocks have NOT been validated against a re-render.** The line-count delta estimate is high-confidence on direction, medium on magnitude; only re-rendering Postkarte from a `blocks`-using `build.py` and visual-diffing will confirm.
- **Tests currently assert against the existing block API** (`test_blocks.py`). Replacing the 8 blocks will require rewriting those tests against the 5 new ones. Cost: ~134 LOC of test changes — manageable.
- **Locale issue**: the German style names with umlauts (`Überschrift gelb`, `Schrift Störer  `, etc.) are emitted as Python strings using `\xad` and verbatim umlauts. The converter handles them. Brand profiles must keep using exact verbatim names so the para-style references in templates resolve. No change needed.

## Recommendations to the planner

**P1 hardening items (executor must land these in this issue, after `/issue:review` completes):**

1. **Run `/issue:review`** with the three-area split brief above. Wait for the orchestrator to write `.issues/5-…/REVIEW.md`. **Hard prerequisite — every P1 item below depends on the review's converged findings, not just this RESEARCH.md.** RESEARCH.md is the planner's input; REVIEW.md is the executor's input.
2. **Introduce `Brand` profile** (Option A above): new file `tools/sla_lib/builder/brand.py` (~120 LOC), populated from `shared/ci.yml` + a new `shared/ci-defaults.yml` (the 113 + 34 identical extras). `Document(brand=...)` consumes it, palette/styles/layers auto-register, `extra_doc_attrs`/`extra_pdf_attrs` only carry the diff. Update `tools/sla_to_dsl.py` to emit `brand=Brand.gruene_noe()` and only the differing extras.
3. **Strip redundant geometry overrides from converter output**: drop `xpos_pt/ypos_pt/width_pt/height_pt` on frames that don't carry sub-ulp-precision values (essentially: keep them only on inline-image frames where the original SLA's HEIGHT had >12 decimal digits). Verify `sla_diff` tests still pass; if they require byte-equivalence, gate the strip with a `--strict-bytes` converter flag.
4. **Replace `blocks.py` aspirational blocks with 5 evidence-driven ones** (`PageNumber`, `Impressum`, `PageBackground`, `ContactBlock`, `ColumnTextStory`). Update or remove `test_blocks.py`.
5. **Auto-emit `clip_edit=True`'s associated rect-path** in `_apply_shape_attrs` so `clip_edit=True` alone is sufficient for the 86 Zeitung frames currently carrying explicit `custom_path='M0 0 L…'`.
6. **Land the spec-file schema sketch** as `docs/spec-input-schema.md` (no converter, just the schema as documentation) so the future spec→build.py issue has a stable target.

**P2 follow-ups (separate issues filed by the planner):**

- Migration: re-author Postkarte onto Brand + blocks (smallest, highest signal-to-noise).
- Migration: re-author Plakat.
- Migration: re-author Zeitung (use the post-Brand+blocks DSL, take the line-count delta).
- PDF→build.py converter (per CONTEXT, deferred).
- InDesign IDML→build.py converter (per CONTEXT, deferred).
- Spec→build.py translator (per CONTEXT, deferred).
- Extend `check_ci.py` to validate brand-style PARENT inheritance correctness and font-stack drift.

**Explicit hand-off note for the executor:**

> The executor's first action is `/issue:review`. Do NOT begin P1 implementation until `.issues/5-…/REVIEW.md` exists and converges with this RESEARCH.md (or supersedes it where the three reviewers find something this research missed). The review's REVIEW.md is the authoritative artifact for the gating decision in the issue's acceptance criteria. P1 items above are *recommended priorities*, not commitments — the review may reorder or substitute.

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` exists in the worktree. The repo-level conventions discoverable from code/docs:
- **Brand fonts MUST be installed for headless renders** (see `docs/render-fidelity.md` — without Gotham Narrow + Vollkorn Black Italic the visual diff fails; this is gated in CI).
- **Visual diff is the correctness gate** for build.py changes — `tools/visual_diff.py` against `templates/*/baseline.pdf` (per `docs/diff-tolerance.md`).
- **Templates are committed PDFs + `build.py` source-of-truth**; do NOT edit `template.sla` by hand.
- **Strict-mode converter (`UnhandledElement`)** — never silently drop a Scribus attribute.
- **Closed override sets only**, no `raw_attrs` escape hatch on frames/styles/runs (CONTEXT.md D2).
- **No "claude" attribution** in commits/code (per user memory `feedback_no_claude_attribution.md`).
- **Reviews must read code themselves**, not receive diffs in prompt (per user memory `feedback_review_no_code_in_prompt.md`).
- **Reviews must be deeply thorough** — line-by-line, exhaustive grep, runtime-trace (per user memory `feedback_thorough_reviews.md`). Plan accordingly when shaping the `/issue:review` brief.
- **Issue artifacts are preserved**, not deleted, when the issue closes (per user memory `feedback_preserve_issue_artifacts.md`). RESEARCH.md and REVIEW.md ship with the PR.

## Sources

### HIGH confidence
- Codebase analysis (read every file in scope; counts measured by direct script):
  - `tools/sla_lib/__init__.py`, `tools/sla_lib/builder/{__init__,primitives,document,styles,ci,blocks}.py`, `tools/sla_lib/{editor,reader,slot}.py`, `tools/sla_lib/tests/*.py`
  - `tools/sla_to_dsl.py`, `tools/check_ci.py`
  - `templates/plakat-a1-hochformat/build.py`, `templates/postkarte-a6-kampagne/build.py`, `templates/zeitung-a4-grun/build.py`
  - `shared/ci.yml`
  - `docs/dsl-reference.md`, `docs/render-fidelity.md`, `docs/diff-tolerance.md`
- Direct measurement: `extra_doc_attrs` (136 keys per template, 113 identical), `extra_pdf_attrs` (45 keys, 34 identical), frame-counts, run counts, clip_edit frequency, var='pgno' frequency.

### MEDIUM confidence
- WebSearch on InDesign IDML format and Python tooling (SimpleIDML; format is ZIP-of-XML). Used only to confirm the multi-input adapter design is feasible; no API claims used.
- WebSearch on PDF→layout reconstruction (pdfplumber, pymupdf both adequate). Used only to confirm DSL gaps for the PDF input path.

### LOW confidence (needs validation)
- Line-count delta estimates after refactor are derived by counting lines saveable per pattern; the actual delta requires re-authoring Postkarte and measuring. Treat as direction-correct, magnitude-±20%.
- Whether `sla_diff` byte-equivalence is gated in CI or only visual-diff is — needs verification by running the test suite.

## Metadata

**Confidence breakdown:**
- Codebase: HIGH (all files read, all counts measured)
- Standard stack: HIGH (DSL + converter are the entire stack)
- Architecture: HIGH (CONTEXT.md decisions clear; constructs proposed are corpus-driven)
- Pitfalls: MEDIUM (one risk — `sla_diff` byte-equivalence requirement — is unresolved)
- Multi-input adapter design: MEDIUM (PDF/IDML is research, not corpus-validated)

**Research date:** 2026-05-07
**Sub-agents used:** none (single-agent research; corpus is small enough for one pass and the value is in measurement, not parallelism)
**Raw research files:** `.issues/5-review-buildpy-dsl-before-more-templates/research/` (empty — synthesis was direct)
