# RESEARCH — Scribus Template Authoring Pipeline

This document synthesises the existing research in `.research/` plus DSL-specific design patterns. Everything cited here is confirmed before issuing into PLAN.md.

## Summary

The authoring kernel is buildable today with the materials at hand. The hard parts (SLA XML emission, multi-page documents with master pages, brand consistency, headless render verification) all have known solutions. The remaining unknowns are tactical: exact DSL surface, block extraction methodology, gallery layout details. This research closes them.

## Foundational findings (carried over from existing research)

### From `.research/01-sla-format.md`

| Topic | Finding | Implication for DSL |
|---|---|---|
| Schema availability | No published XSD/RNG. `scribus150format_save.cpp` (~3000 LOC) is the canonical writer reference. 1.5.x and 1.6.x share this loader. | DSL must be defensive — round-trip every emit through Scribus to verify validity. Add unit test suite that opens DSL output through headless Scribus before any commit lands. |
| PAGEOBJECT structure | Sibling of `<PAGE>`, not child. Linked via `OwnPage` (numeric, page index) or `OnMasterPage` (string, master page name). | DSL emits PAGEOBJECTs in the right XML position (after PAGE) and with correct linkage attributes. |
| Coordinates | Always points (1pt = 1/72in) regardless of `UNITS` attribute. `XPOS`/`YPOS` are scratch-space (multi-page coordinate plane) — page-relative coords need `+ PAGEXPOS`/`+ PAGEYPOS` of the owning page. | DSL accepts user-friendly mm and converts internally. Emits scratch-space XPOS = page_xpos + local_x_pt. |
| ItemID | `qHash(item) & 0x7FFFFFFF` — unstable across reloads. Used by NEXTITEM/BACKITEM/welds. | DSL generates monotonic IDs at emission time. NEXTITEM/BACKITEM only used inside a single emission (e.g. linked text frames). |
| Style PARENT inheritance | Implicit-by-absence. Re-emitting an attribute equal to parent's silently overrides inheritance. | DSL stores style definitions as deltas relative to parent. Style serializer never emits an attribute that equals the parent's value. |
| Inline images | base64 of qCompress (Qt zlib wrapper, not raw deflate). | We never inline images in the DSL output — all images are external (PFILE) for editability. |
| Text runs (ITEXT) | Flat sequence inside StoryText: DefaultStyle, ITEXT runs, para separators (carrying paragraph style attrs), breakline, tab, var, MARK, trail. | DSL `Text(...)` accepts plain string OR list of `Run(text, style_override)`; emits ITEXT runs separated by para or breakline. Soft-hyphen handling via explicit Run flag. |
| Bleed | Lives on DOCUMENT (`BleedTop`, `BleedBottom`, `BleedLeft`, `BleedRight`). | DSL `Document(bleed_mm=3)` writes those four attributes. Bleed cannot vary per page. |

### From `.research/02-tooling-ecosystem.md`

- **Scribus 1.6.x in Docker (Xvfb-headless) is the only fully open-source, press-grade option** for our format mix. Confirmed via PoC: arm64 Debian trixie (1.6.3) renders all three existing templates correctly under `xvfb-run`.
- **PyScribus is dormant** (last release Aug 2023) — we do not depend on it. Our `tools/sla_lib/` uses lxml directly.
- **ScribusGenerator's multi-page mode is "works but error-prone"** by its own README — we deliberately avoid that approach. Our DSL emits multi-page natively.
- **LLM authoring of raw SLA fails reliably**; LLMs filling slots in human-built templates works; the strongest pattern is **structured-spec emission into a deterministic builder** (which is exactly our DSL+LLM approach).
- **Vision-LLM-as-judge** works in pairwise mode against a reference render; absolute scoring is unreliable.

### From `.research/03-validation-distribution.md`

- **Astro on GitHub Pages** is the strongest 2026 default for the gallery. Pagefind for search. Per-template detail page with PDF embed (`pdfjs-viewer-element`) and PNG carousel.
- **Cloudflare Pages + Cloudflare Access** is the auth path if internal-only is later required.
- **Visual regression / preflight is follow-up work** — not in this issue's scope. The Dockerfile has the optional `INSTALL_PREFLIGHT=1` build arg ready when needed.

## DSL design patterns (new for this issue)

### Lessons from comparable projects

- **reportlab** (PDF builder): nested-element model with explicit canvas + flowables. Good model for *positioning* but forces too much absolute-coord thinking. We want named anchors (top-left, center, bottom-X-mm).
- **simpleidml** (InDesign IDML manipulation): deeply object-tree-based, mirrors the underlying XML 1:1. Too thin an abstraction — exposes IDML's quirks. Lesson: hide the format quirks behind ergonomic block primitives.
- **WeasyPrint** (HTML/CSS → PDF): users write HTML+CSS, library does layout. Wrong direction for us — we want users to write *less*, not more.
- **Streamlit / FastAPI (typed Python APIs)**: declarative composition with sane defaults. Right model — `page.add(Headline4Line(...))` reads naturally and is LLM-friendly.

### DSL surface decisions

- **Two layers**:
  - *Low-level primitives*: `TextFrame(x, y, w, h, story=..., style=...)`, `ImageFrame(x, y, w, h, src=...)`, `LineShape(...)`, `PolygonShape(...)`. These are 1:1 with PAGEOBJECT PTYPEs. Used internally by blocks; exposed for advanced users.
  - *Block primitives*: `Headline4Line(...)`, `StoererBadge(...)`, `Masthead(...)`, `EventDetails(...)`, etc. Compose primitives + apply CI styles + position via named anchors. Used by 80% of authoring.
- **Anchors instead of raw coordinates**: `pos="top-center"`, `pos=("center", 30)` (x = center, y = 30mm), `pos=(40, "bottom-20")` (x = 40mm, y = 20mm above bottom). DSL resolves anchors against page geometry + bleed.
- **Units**: mm everywhere in the public surface. DSL converts to pt internally (1pt = 1/72in, 1mm ≈ 2.83465pt).
- **Brand integration**: `Color.DUNKELGRUN`, `Color.GELB`, etc. — enums populated from `shared/ci.yml` at DSL load time. Same for `Style.HEADLINE`, `Style.BODY_12`. Hardcoded enums + runtime-validated against ci.yml = both IDE autocomplete and brand consistency.
- **Page sizes**: ISO presets (`"A0".."A6"`) plus `("custom", w_mm, h_mm)`. Roll-up known sizes (85x200cm) added as named presets.
- **Multi-page**: `Document.add_master(name, ...)` and `Document.add_page(master=..., label=..., content=[...])`. Master-page support is critical for the Zeitung use case (deep-dive launched as agent).
- **Example content visible**: every block has sensible defaults rendered as visible Scribus text — `Headline4Line()` with no args produces "[Zeile 1]\n[Zeile 2]\n[Zeile 3]\n[Zeile 4]" so the template ships with placeholder text users see and replace.
- **Layer organization**: every Document gets default layers `Hintergrund`, `Bilder`, `Text`, `Hilfslinien` (last hidden by default). Blocks declare which layer their elements land on.

### What the DSL does NOT need (explicitly)

- Generic "any-shape" support — we have ImageFrame, TextFrame, Polygon, Line, that's enough for our blocks. Custom Bezier paths are out of v0.
- Arbitrary style mutation — styles are defined once in `shared/ci.yml`, DSL references them, never inline-overrides. Per-frame style tweaks happen in Scribus GUI.
- Tables — none of the existing templates use tables; defer until a real use case appears.
- Scribus tables of contents, indexes, footnotes, marks — not in our authoring use cases.

## Block extraction methodology

Goal: take an existing SLA (Postkarte, Plakat, Zeitung), select a region or set of frames, save as a self-contained block fragment that the DSL can re-instantiate.

### Approach

1. **Manual selection by ANNAME or ItemID**: `extract_block --source X.sla --frames "text:headline,text:cta,polygon:#7" --out shared/blocks/content/headline-with-cta.sla`. Frame list is the human-curated selection.
2. **Style hoisting**: a block fragment must include the paragraph styles, character styles, and colors it references — otherwise re-instantiation produces orphan refs. Tool walks each selected frame, collects all referenced STYLE/CHARSTYLE/COLOR names, copies their definitions into the fragment.
3. **Coordinate normalization**: block fragments are saved with **block-local coordinates** (top-left of the block bounding box at 0,0). DSL re-instantiates by adding the block's target page position to the local coords.
4. **Style-name remap**: the DSL holds the canonical brand stylenames. Block fragments use those canonical names. Old names like "Vollkorn Headline sehr wichtig" get renamed to `ci/headline-vollkorn` during extraction. The renamer has a hand-curated mapping table.
5. **Catalog metadata**: each block has a `<id>.meta.yml` describing slots, recommended page sizes, suggested anchor positions, example content semantics.

### Catalog structure

```yaml
# shared/blocks/catalog.yml
blocks:
  content/headline-4line-alt:
    title: Brand-Headline 4-zeilig (Wechselfarbe)
    description: Hauptüberschrift, 4 Zeilen, Weiß/Gelb-Wechsel, Vollkorn-Italic
    fragment: shared/blocks/content/headline-4line-alt.sla
    bbox_mm: { w: 90, h: 50 }
    slots:
      - { kind: text, name: line1, lines: 1 }
      - { kind: text, name: line2, lines: 1 }
      - { kind: text, name: line3, lines: 1 }
      - { kind: text, name: line4, lines: 1 }
    suitable_for: [postkarte, plakat, zeitung-titelseite]
  footer/impressum-line:
    ...
```

LLM uses `catalog.yml` as a menu when proposing layouts.

## Gallery patterns (reuse from .research/03)

Reaffirmed: Astro Content Collections, sidecar `meta.yml` per template, Pagefind search, `pdfjs-viewer-element` embed, page-by-page PNG carousel for multi-page templates, family card with size selector, GitHub Action workflow renders previews and deploys.

Additions surfaced this issue:
- "How to use" section per template (open in Scribus, duplicate example pages, edit content, replace placeholder images)
- "What is each example page?" mini-legend for multi-page templates (page 3 = "Doppelseite Hauptartikel rechts")
- Brand quickstart link on every page (colors, fonts, logo download)

## Open / pending

- **Scribus master-pages mechanics deep-dive** — agent dispatched. Findings will be appended to `.research/04-scribus-multipage-masters.md` and inform the multi-page DSL section of PLAN.md. Current PLAN can proceed independently for Phase 1-3 (CI, blocks, single-page DSL); Phase 5 (newspaper) waits on this report or starts after it lands.

## Out of scope (deferred — recap)

Online configurator, AI image generation, vision-LLM judge with iterative loop, PDF/X-4 conformance, visual regression testing.
