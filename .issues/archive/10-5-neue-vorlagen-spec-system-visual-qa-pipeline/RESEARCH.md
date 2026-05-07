# Research Synthesis — 10-5-neue-vorlagen-spec-system-visual-qa-pipeline

Synthesized 2026-05-07 from three parallel research streams:
- `research/codebase.md` (DSL surface, blocks, image embedding, existing patterns)
- `research/ecosystem.md` (Scribus 1.6, Ghostscript, Pillow, vision APIs, print standards)
- `research/pitfalls.md` (risks, edge cases, environment audit)

**Confidence: HIGH** for foundational findings. **MEDIUM** for some D1/D4 reversals where final empirical confirmation will land in Phase 2 spike.

---

## User Constraints (verbatim from CONTEXT.md, with revisions surfaced)

CONTEXT.md captured 10 locked decisions (D1–D10). Research surfaces **four corrections**, **one new decision (D11)**, and **one new constraint (D12)**. Plan must follow the corrected versions; legacy CONTEXT.md text is overridden by this section.

### Corrections to CONTEXT.md (locked decisions revised by evidence)

#### Revision to D1 — Use Existing PNG (no Ghostscript step)

**Original D1:** EPS → PDF → inline `ImageFrame` (base64).

**Revised D1:** **Use the existing `Wahlkreuz.png`** at workspace root (1200×1299, RGBA with alpha channel, 81 KB). Copy to `shared/assets/wahlkreuz.png` and embed via `ImageFrame` with `inline_image_ext='png'`, `scale_type=0`. Encoding via qCompress wrapper (see new helper below).

**Evidence:**
- User identified `Wahlkreuz.png` already exists at `/root/workspace/Wahlkreuz.png` — 1200×1299, color_type=6 (RGBA), 8-bit depth. Verified by direct PNG header inspection.
- The alpha channel preserves the white circle as visible against any colored background, with full transparency outside the circle's circumference.
- The earlier ecosystem/pitfalls agents had not seen this asset — they planned around the EPS file alone. With the PNG in hand, no Ghostscript conversion is needed at all, eliminating the entire deterministic-PDF concern (P-EPS-3) and the runtime `gs` dependency.
- All three production templates use `inline_image_ext='png'` exclusively with `scale_type=0`.

**Implementation impact:**
- Copy `Wahlkreuz.png` → `shared/assets/wahlkreuz.png` (commit the bytes to repo).
- `WahlkreuzSymbol` block reads these bytes, applies `pack_inline_image()`, embeds via `ImageFrame`.
- Keep the EPS at `shared/assets/wahlkreuz-kreis.eps` as the source-of-truth original for archival/regeneration purposes.
- No `tools/eps_to_pdf.py`, no Ghostscript at build time, no derived/ directory, no `.gitignore` bookkeeping.
- Determinism: PNG bytes pinned in repo; SLAs build byte-stable across machines.

#### Revision to D1.helper — qCompress Encoding (CRITICAL)

**Original D1 (implicit):** `inline_image_data = base64.b64encode(image_bytes)`.

**Revised:** Scribus's inline `ImageData` requires **qCompress format** — `base64( 4-byte big-endian length prefix + zlib_compress(image_bytes) )`. Naive base64 of raw bytes makes Scribus abort with `qUncompress: Z_DATA_ERROR` and the SLA fails to open.

**Evidence:**
- Documented in `tools/sla_to_dsl.py:202-216` (decoder reference).
- Exercised in `tools/sla_lib/tests/test_sla_diff.py:340-349` (encoder fixture).
- Confirmed by pitfalls agent's empirical write-and-open test.
- All 15 inline images in production templates use this format.

**Implementation impact:** Plan adds `pack_inline_image(bytes: bytes, ext: str) -> tuple[str, str]` helper (returns `(qcompressed_b64, ext)`) to `tools/sla_lib/builder/primitives.py` near `ImageFrame`. Every new image-embedding code path uses this helper. ~10 LoC including docstring.

#### Revision to D4 — Layer + Spot-Color Surface

**Original D4:** "DSL hat heute kein explizites Layer-Konzept" → propose `Document.add_layer(...)` API.

**Revised D4:** Layer support already exists. **No new layer API needed.** Spot color support also exists. **No new spot-color API needed.** Caveat: spot colors must be **document-local** (`doc.add_color('Falz', spot=True, ...)`), NOT added to `shared/ci.yml`, to avoid round-trip-diff regression on the three existing templates (which don't have these colors).

**Evidence:**
- `DocumentLayer` dataclass exists at `tools/sla_lib/builder/styles.py:17-29` with `name`, `printable`, `flow`, `transparency`, `blendmode`, `outline` attributes.
- `Document.__init__` accepts `layers=[...]` parameter (`tools/sla_lib/builder/document.py:148`).
- `Document._emit_layers()` implementation at `document.py:881-910` correctly emits all `<LAYERS>` attributes Scribus expects.
- `Document.add_color(name, ..., spot=True)` already supports spot at `document.py:247-263`.
- Existing brand color `Registration` uses `register=True` — same family pattern.
- Pitfalls agent confirmed: adding `Falz`/`Stanzkontur` to `shared/ci.yml` would make `tools/check_ci.py` flag the existing three templates as having undefined-in-SLA colors → red CI on un-related templates.

**Implementation impact:** New blocks (`FoldLine`, `DieCut`) take a `layer_name` argument and rely on the template's `build.py` to: (1) `doc.add_color('Falz', spot=True, cmyk=(...))`, (2) `doc.add_layer(name='Falz', printable=False, ...)`. This is per-template, surgical, and zero-risk to the round-trip of the three existing templates.

#### Revision to D7 — Side-by-Side Compositing Tool

**Original D7:** Pillow (`PIL`) for grid composite.

**Revised D7:** ImageMagick `montage` (already used in `tools/visual_diff.py:188-195`). No new dependency, deterministic, supports labels and proportional scaling out of the box.

**Evidence:**
- Pillow not installed in the container or in `Dockerfile.claude`. Adding it is a real dependency change.
- ImageMagick is already installed and used. `montage -tile 4x2 -geometry 1024x1024+10+10 -label "%t" *.png grid.png` produces the desired layout.
- Pitfalls agent's empirical run confirmed determinism of `montage` output across two runs.

**Implementation impact:** `tools/visual_review.py` invokes `montage` via `subprocess.run`. No `PIL` import needed.

### New Decisions Surfaced by Research

#### D11 — Codex DALL·E Demo-Image Generation (one-shot, per-template)

**Source:** User directive during research phase. Confirmed via [openai/codex#8758](https://github.com/openai/codex/issues/8758).

**Decision:**
- For each new template with image slots, generate **per-template demo images** by invoking `codex` with a detailed image-generation prompt and an output path. Generated images are committed to `templates/<slug>/samples/<image>.jpg`.
- Generation is **one-shot, not at build time.** Demo images are committed bytes; CI never re-renders them.
- A `templates/<slug>/samples/manifest.yml` documents the prompts used, so future regenerations are reproducible.
- A helper `tools/codex_image_gen.py` orchestrates: read manifest → call codex → write image.
- **Templates do NOT hard-reference these images** as required slot fills. Image slots remain `optional` in `meta.yml`. Demo images are used by the **gallery preview** render only — a separate "preview" SLA (e.g. `template-preview.sla`) is generated alongside `template.sla` with the demo images injected, used solely for the PNG preview the gallery displays.
- This avoids the "missing-file when end user opens template.sla" footgun.

**Implementation impact:**
- Add `tools/codex_image_gen.py` (~80 LoC) — invokes `codex exec -i ... --output <path>` per the Codex CLI image-generation form, reads manifest, writes image.
- Each new template that needs demo images: add `samples/manifest.yml` listing prompts + output filenames.
- Gallery build pipeline: when rendering the preview, prefer `<slug>-preview.sla` if present, else `template.sla`.
- Generation happens once per new template, in this issue's execute phase. After commit, no further codex calls are made by build/CI.

#### D12 — Wahlkreuz EPS Renders With White Circle (background constraint)

**Source:** User clarification during research phase, confirmed by EPS inspection.

**Finding:** The EPS file `Wahl Kreuz im Kreis.eps` contains a **yellow cross with a white circle around it**. When rendered on a white background, the circle disappears — only the cross is visible. The file is designed to be placed on a colored background.

**Decision:**
- Every template using the Wahlkreuz **must** render it on a colored background — `Dunkelgrün`, `Hellgrün`, or `Magenta`. Never plain white. Never plain `Gelb` (yellow on yellow disappears).
- The Spec for Wahlkreuz-using templates explicitly documents this constraint in the spec body.
- Visual QA Gate 3: a Wahlkreuz visible on a white-or-yellow background is a **blocking finding**. The vision-review prompt explicitly checks "Is the Wahlkreuz placed on a colored background that makes the white outer ring visible?".
- The PNG generated from the EPS preserves the white ring (alpha channel disabled, white pixels remain white). The composite block (`WahlkreuzSymbol`) takes a `background_color` argument that fills the area behind the image with a brand color before placing the EPS.

**Implementation impact:**
- `WahlkreuzSymbol` block draws a `Polygon` background fill (default `Dunkelgrün`) at the same Z-position before the `ImageFrame`.
- Spec template includes a "Background-color contract" section for Wahlkreuz-using templates.
- Visual-review prompt template references this constraint by name.

---

## Summary

This is a 5-template, 10-spec, multi-block, multi-tool, multi-gate effort with three review checkpoints. Foundational research reduces three planned new APIs to zero (layers, spot colors), pivots the EPS path from PDF-inline to PNG-inline (matches existing pattern, deterministic), and surfaces a 6-line `pack_inline_image()` helper as the single critical addition to `primitives.py`. Demo-image generation via Codex DALL·E is added as a one-shot tool to give the new templates believable preview imagery without bloating the build pipeline.

The execute phase will be heavy on careful per-template authoring and gate iteration, light on infrastructure invention. The biggest design risk is **content** rather than tooling: the Wahlkreuz EPS only works on colored backgrounds, and visual-quality is the hard ship criterion. Both have explicit gate checks.

Primary recommendation: implement strictly in the order Phase 1 (specs + Gate 1) → Phase 2 (small DSL extensions: `pack_inline_image`, blocks) → Phase 3 (5 templates, one-by-one with smoke-test) → Phase 4 (visual-QA tooling) → Phase 5 (Gate 3 iteration loop). Codex demo-image generation slots into Phase 3 per template.

---

## Codebase Analysis

### DSL Surface Map (lines verified)

```
tools/sla_lib/builder/
├── __init__.py             — public re-exports: Document, Page, ImageFrame, TextFrame,
│                             Polygon, Run, Anchor, Brand, Color, Style, blocks
├── primitives.py:111       — Anchor (positioning system)
│                :285       — Run (text-run with style attrs)
│                :425       — _Frame (base for TextFrame, ImageFrame, Polygon)
│                :532       — TextFrame
│                :742       — ImageFrame (incl. inline_image_data path)
│                :825       — Polygon (use this; Line at :890 is deprecated)
├── document.py:140         — Document.__init__ (accepts layers=[...])
│              :148         — `layers` parameter
│              :247         — Document.add_color(name, ..., spot=True, register=False)
│              :281         — Document.add_master(name, size)
│              :332         — Document.add_page(...)
│              :881         — Document._emit_layers() — emits <LAYERS> with all attributes
├── styles.py:17            — DocumentLayer dataclass (name, printable, flow,
│                             transparency, blendmode, outline)
├── brand.py                — Brand wrapper around shared/ci.yml
├── ci.py                   — ci.yml loader and validator
└── blocks.py               — composition blocks (see below)
```

### Block Library Inventory

Live blocks (evidence-driven, used in production templates):
- `PageNumber` — page-number text frame on master pages
- `Impressum` — Impressum text block (legally required)
- `PageBackground` (incl. `_SizedPageBackground` and `for_page()` factory) — full-page color fill
- `ContactBlock` — contact info layout
- `ColumnTextStory` — multi-column flowing text

Legacy/deprecated blocks (`blocks.legacy.*`) — used by smoke templates only, **do not copy patterns from these**:
- `Headline4Line`, `StoererBadge`, `ImpressumLine`, `ImpressumBlock`, `SocialHandlesVertical`, `LogoCorner`, `EventDetails`, `Masthead`, `ContentTeasers`, `ArticleHeadline`, `ArticleBody`, `QuoteSidebar`

Helper convention (live blocks):
- `@dataclass`-decorated classes with sensible defaults
- `emit(self, page) -> Iterable[primitive]` returning ImageFrame/TextFrame/Polygon/...
- Docstring documents source SLA(s) and sample anchors
- `anname` defaulted in dataclass
- `for_page()` classmethod factory pattern (see `PageBackground.for_page()`)

### Existing Image Embed Mechanics

```python
# templates/postkarte-a6-kampagne/build.py:96-118 — verified pattern
page0.add(ImageFrame(
    pos=Anchor.from_page("topright", x_offset_mm=-12, y_offset_mm=8),
    size=(40, 12),
    inline_image_data="<qcompress-base64-blob>",   # ← qCompress format
    inline_image_ext="png",                          # ← raster only
    scale_type=0,                                    # ← critical default
    anname="Logo Grüne (weiss)",
))
```

The `inline_image_data` is what the SLA emitter writes verbatim to `<PAGEOBJECT ImageData="...">`. It MUST be qCompress-encoded; Scribus aborts on raw base64. Helper `pack_inline_image(bytes, ext)` will wrap this. Reference encoder lives in `tools/sla_lib/tests/test_sla_diff.py:340-349`.

### Layer + Spot Color Path (already supported)

```python
# In a template's build.py, this is now the supported pattern:
doc = Document(
    title="...",
    template_id="...",
    layers=[
        DocumentLayer(name="Background", printable=True, flow=True),
        DocumentLayer(name="Falz",       printable=False, flow=False, exportable=True),
        DocumentLayer(name="Stanzkontur",printable=False, flow=False, exportable=True),
    ],
)
doc.add_color("Falz", cmyk=(100, 0, 0, 0), spot=True)
doc.add_color("Stanzkontur", cmyk=(0, 100, 0, 0), spot=True)
```

### `<interfaces>` for Six New Blocks

```python
<interfaces>
@dataclass
class WahlkreuzSymbol:
    """Wahlkreuz im Kreis (yellow cross + white circle).
    
    The EPS image has a white outer circle that will disappear on white
    backgrounds. This block draws a colored background fill behind the
    image to keep the circle visible. Default background: Dunkelgrün.
    
    Source asset: shared/assets/derived/wahlkreuz-kreis.png (600 DPI from
    Wahl Kreuz im Kreis.eps via Ghostscript).
    """
    pos: Anchor
    size: tuple[float, float]                # (w_mm, h_mm); the symbol auto-fits inside
    background_color: str = "Dunkelgrün"     # MUST be a colored brand color, not White
    background_padding_mm: float = 4.0
    anname: str = "Wahlkreuz"
    def emit(self, page) -> Iterable: ...

@dataclass
class FoldLine:
    """Strichlierte Falz-Linie auf 'Falz'-Layer mit Spot-Color-Stroke.
    
    Used by FoldedFlyer and TableTent templates.
    """
    start_mm: tuple[float, float]
    end_mm: tuple[float, float]
    layer_name: str = "Falz"
    spot_color: str = "Falz"
    line_width_pt: float = 0.5
    dash_pattern: tuple[float, float] = (3.0, 1.5)
    anname: str = "Falzlinie"
    def emit(self, page) -> Iterable: ...

@dataclass
class DieCut:
    """Geschlossener Stanzpfad auf 'Stanzkontur'-Layer.
    
    For door hangers: outer trim path + door-handle hole.
    Pass list of (x, y) mm pairs forming a closed polygon.
    """
    path_mm: list[tuple[float, float]]
    layer_name: str = "Stanzkontur"
    spot_color: str = "Stanzkontur"
    line_width_pt: float = 0.25
    anname: str = "Stanzkontur"
    def emit(self, page) -> Iterable: ...

@dataclass
class FoldedPanel:
    """Wrapper that lays out a single panel of a folded flyer.
    
    Provides margin handling and auto-positions Falz-line on the right edge
    if not the last panel. Caller adds children to the panel; FoldedPanel
    handles fold-aware geometry.
    """
    panel_index: int                         # 0-based
    panel_count: int                         # 3 for DIN-lang
    panel_size_mm: tuple[float, float]       # (99, 210) for DIN-lang vertical
    has_fold_right: bool = True              # auto-False on last panel
    children: list = field(default_factory=list)
    def emit(self, page) -> Iterable: ...

@dataclass
class DoorHangerCutout:
    """Standard door-hanger outer + handle-hole stanzpfad.
    
    105×250 mm with circular hole at top (35 mm diameter, 25 mm from top edge).
    Auto-emits a DieCut on Stanzkontur layer.
    """
    page_size_mm: tuple[float, float] = (105, 250)
    hole_diameter_mm: float = 35
    hole_top_offset_mm: float = 25
    def emit(self, page) -> Iterable: ...

@dataclass
class TableTentFold:
    """A4 quer folded into A5-tent: emits horizontal Falz-line at center.
    
    Used by Infostand-Tent-Card.
    """
    page_size_mm: tuple[float, float] = (297, 210)
    def emit(self, page) -> Iterable: ...
</interfaces>
```

### Render / Validation Pipeline (no Makefile; entry points in `bin/`)

```
build.py  →  template.sla       (DSL emits SLA; idempotent)
   ↓
check_ci.py  →  pass/fail        (drift detection vs shared/ci.yml)
   ↓
sla_diff.py  →  diff report      (round-trip vs original SLA, when applicable)
   ↓
bin/render-gallery <id>          (Scribus headless via Xvfb → PDF + PNGs at 100 DPI)
   ↓
gallery_build.py                 (Astro content + montage composite previews)
   ↓
.github/workflows/pages.yml      (deploy to GitHub Pages)
```

CI never re-renders. Local-built artifacts (`preview.pdf`, `page-*.png`) are committed; `bin/check-stale-previews` enforces SHA256 of `template.sla` matches `meta.yml::previews_for_sla`. Same scheme applies to the five new templates.

### Existing Smoke Test Pattern (`templates/_smoke/`)

Per-template `test_*.py` using `unittest`. Patterns:
- Import the build module
- Call build, write to temp file
- Re-parse via `sla_lib`
- Assert structural invariants (page counts, frame counts, slot annames present, no overlap, etc.)

Smoke templates use `blocks.legacy.*` — these are *not* the new convention. New templates use live blocks only.

### Multi-Model Tooling Survey

| Tool | Image input | Auth state | Notes |
|---|---|---|---|
| `claude-code` (Vision via SDK) | ✓ via Anthropic SDK | env API key | Used direct from `tools/visual_review.py` |
| `codex exec` | `-i FILE [--image FILE]…` | OAuth cached at `/root/.codex/auth.json` | Verified `--help`. Supports `--output-schema` for JSON. Image-generation via DALL·E confirmed by user. |
| `gemini` | NO `--image` flag | OAuth in `~/.gemini/oauth_creds.json` (token currently expired but auto-refreshes) | Use `--include-directories` workaround OR switch to `google-generativeai` Python SDK for clean multimodal. |
| `montage` (ImageMagick) | n/a (not vision) | n/a | Used for grid composite |
| `gs` (Ghostscript) | n/a | n/a | EPS → PNG conversion |
| `pdftoppm` | n/a | n/a | Available; not used on EPS path |

CI runners have NEITHER Codex nor Gemini auth → **Gate 3 vision review is local-only**, never on CI. CI runs structural and visual-smoke only.

### Reusability Opportunities

1. **Round-trip diff scaffolding** — existing `tools/sla_diff.py` invariant on the three production templates must remain green. New templates have NO original SLA → they only need `check_ci.py` validation, not `sla_diff.py`.
2. **`PageBackground.for_page()` factory** — exact pattern to copy for new blocks that need page-size-aware defaults.
3. **`tools/visual_diff.py:188-195`** — existing `montage` invocation — copy directly into `tools/visual_review.py`.
4. **`tools/check_ci.py` `non_ci_styles` / `non_ci_colors` overrides** — already supports per-template document-local exceptions; new templates use this for `Falz`/`Stanzkontur`.
5. **Galerie PNG pipeline** — `tools/gallery_build.py` already converts SLA→PDF→PNG; just runs over five additional template directories.

### Spec Schema Prior Art

`shared/template-spec.schema.yaml` (313 LoC, JSON Schema) plus `docs/spec-input-schema.md` predate this issue. They define a YAML-only spec format **without** ASCII layouts, EPS-strategy section, or Falz/Stanz handling. **Don't extend this schema** for the new spec; instead, the new Markdown+YAML spec format references it where slot conventions overlap (so `meta.yml` keys still match), but is its own document under `templates/_specs/`.

### Documented DSL Gotchas (from codebase agent)

20 documented gotchas. The five most relevant for the new templates:
- `Line` is deprecated; use `Polygon` with two points.
- `Run` tuple form is deprecated; use the `Run` dataclass with named args.
- `text_align` is deprecated; use `vertical_text_align`.
- `Anchor` legacy strings are deprecated; use `Anchor.from_page("topleft", ...)` factory.
- `default_style_attrs` + `style` together emits a warning — pick one.

---

## Standard Stack (verified versions)

| Tool | Version | Path | Status |
|---|---|---|---|
| Python | 3.13 | `/usr/bin/python3` | ✓ |
| Scribus | 1.6.3 (local), 1.6.5 (CI) | `/usr/bin/scribus` | ✓ — CI/local skew handled by `check_stale_previews` |
| Ghostscript | 10.x | `/usr/bin/gs` | ✓ |
| ImageMagick (`montage`, `convert`) | 7.x | `/usr/bin/montage` | ✓ |
| `pdftoppm` | 24.x | `/usr/bin/pdftoppm` | ✓ |
| `xvfb-run` | 1.21+ | `/usr/bin/xvfb-run` | ✓ |
| `codex` | latest | `/root/.npm-global/bin/codex` | ✓ — OAuth via ChatGPT |
| `gemini` | latest | `/root/.npm-global/bin/gemini` | ✓ — OAuth (token may need refresh) |
| `gh` | 2.x | `/usr/bin/gh` | ✓ |
| Pillow | not installed | n/a | ✗ — use `montage` instead per D7 revision |
| `jsonschema` Python | not installed | n/a | ✗ — needed only if we strict-validate specs in CI; Phase 4 decides |

## Don't Hand-Roll

- **Don't write a custom EPS parser.** Use Ghostscript `gs -dEPSCrop -sDEVICE=png16m -r600`.
- **Don't write a custom PNG writer.** Ghostscript writes PNG; just consume it.
- **Don't write a custom inline-image encoder.** Wrap qCompress in a 6-line helper; use Python `zlib.compress` + `struct.pack(">I", len)` + `base64.b64encode`. Reference encoder already in test fixtures.
- **Don't write a custom grid compositor.** Use `montage`.
- **Don't add a layer API.** It's already there.
- **Don't add a spot-color API.** It's already there.
- **Don't extend `shared/template-spec.schema.yaml`.** The new Markdown+YAML format is a separate document genre.
- **Don't write a Falz-detection regex.** The convention from print shops is `Falz` and `Stanzkontur` — fixed names; pin them.
- **Don't write your own multi-model orchestrator from scratch.** Pattern after `/issue:review` skill (which is in the user's available skills) — orchestrate Claude (direct API), Codex (`codex exec -i`), Gemini (CLI or Python SDK).

---

## Architecture Patterns (from research)

1. **One template = one directory under `templates/<slug>/`** with `build.py`, `meta.yml`, `README.md`, plus build artifacts (`template.sla`, `preview.pdf`, `page-*.png`). New directories follow this structure plus `samples/` for D11 demo images and `template-preview.sla` for the gallery preview render.

2. **DSL as source of truth** — `template.sla` is regeneratable; never hand-edit. `meta.yml` and the spec are authored.

3. **Per-template document-local extensions** — spot colors, custom styles, custom layers all declared inside `build.py`; never bleed into `shared/ci.yml` unless used by ≥3 templates.

4. **Brand gate via `check_ci.py`** with `meta.yml.ci_overrides` listing locally allowed exceptions (per-template).

5. **Round-trip diff** only applies to templates with an original SLA at workspace root. New templates skip it; they're DSL-original.

6. **PNG previews committed locally** with SHA256-pin guard (`bin/check-stale-previews`).

7. **Composition over inheritance** in blocks — every block emits primitives; no block inherits from `_Frame`.

---

## Common Pitfalls (top 12, ranked by likelihood × impact)

| # | ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| 1 | P-EPS-2 | qCompress format required for inline images | CERTAIN | CRITICAL | Add `pack_inline_image()` helper in Phase 2 |
| 2 | P-CONTENT-1 | Wahlkreuz EPS has white circle — invisible on white bg | CERTAIN (now known) | HIGH | D12 constraint; `WahlkreuzSymbol` background fill default Dunkelgrün; visual-QA explicit check |
| 3 | P-EPS-1 | PDF-in-ImageFrame quality + determinism poor | CONFIRMED | HIGH | D1 revision: PNG path |
| 4 | P-CI-4 | Spot colors in `shared/ci.yml` regress existing templates | HIGH | HIGH | D4 revision: document-local |
| 5 | P-DSL-2 | Merge conflicts with parallel issue #9 | MEDIUM | MEDIUM | Sync at PR time; both branches touch `blocks.py` |
| 6 | P-VISION-2 | Vision API auth absent on CI | CERTAIN | MEDIUM | Gate 3 is local-only by design |
| 7 | P-SPEC-1 | Spec ↔ build drift | MEDIUM | HIGH | `tools/spec_check.py` in Phase 4 |
| 8 | P-EPS-3 | Ghostscript PDF non-determinism | CONFIRMED | HIGH | PNG path avoids; PNG byte-stable |
| 9 | P-VISION-4 | Hallucinated/disagreement-spiral findings | MEDIUM | MEDIUM | 3-iteration cap (D6); structured prompt with named criteria; human override |
| 10 | P-PRINT-2 | Falz coordinate confusion (trim vs bleed origin) | MEDIUM | HIGH | Spec template explicitly states origin convention; `FoldLine` block enforces |
| 11 | P-VISION-5 | Multi-model cost runaway | LOW (calc'd <$1 total) | LOW | Bound by 3-iteration cap |
| 12 | P-WAHL-LIABILITY | Wahlkreuz copy implies "vote ONLY Grüne" | LOW | HIGH | Spec template review checklist: copy says "wählen" not "die einzige Wahl"; legal liability boundary respected |

---

## Environment Availability (audit results)

All checked in current shell on 2026-05-07:

| Binary | Required for | Status | Notes |
|---|---|---|---|
| `python3` | DSL build | ✓ 3.13 | |
| `scribus` | Render | ✓ 1.6.3 (local) | CI uses 1.6.5 — both fine |
| `gs` | EPS→PNG | ✓ 10.x | Use `-dEPSCrop -sDEVICE=png16m -r600` |
| `montage` | Grid composite | ✓ | Already used in `tools/visual_diff.py` |
| `pdftoppm` | PDF→PNG | ✓ | Backup path |
| `xvfb-run` | Headless Scribus | ✓ | Existing pipeline |
| `gh` | PR/issue | ✓ | Already used |
| `codex` | Vision review | ✓ | OAuth cached |
| `gemini` | Vision review | ✓ | OAuth (refresh on use) |
| Pillow | NOT NEEDED | n/a | `montage` replaces it |
| `jsonschema` (py) | Phase 4 spec validator | ✗ | Install only if Phase 4 needs strict validation |
| `veraPDF`, `pdfcpu` | (referenced in Dockerfile.claude) | ✗ on PATH | Different image variant; not blocking |
| Wahlkreuz EPS | source asset | ✓ | At workspace root; will be copied to `shared/assets/wahlkreuz-kreis.eps` |

---

## Project Constraints (from memory + repo conventions)

- **No "claude" attribution** in commits, code, files, reports — user doesn't expose tools to clients.
- **Issue artifacts persist after merge** — archive, never delete.
- **Reviews must be deeply thorough** (line-by-line, exhaustive grep, trace runtime paths) — the 3 review gates inherit this.
- **Use issue-cli WorktreeManager** (not raw git) for worktree ops in any tooling we add.
- **`/issue:review` runs during execute, not pre-research** — Gates 1, 2, 3 fit this convention (they all run inside the execute phase of this issue).

---

## Sources (with confidence levels)

### HIGH confidence
- **Codebase agent** — `research/codebase.md` — line-numbered citations against repo
- **Pitfalls agent** empirical tests — wrote-and-opened SLAs, rendered EPS at multiple GS settings, ran `gs` repeatedly to verify non-determinism
- **Existing template SLAs** — `*-original.sla` at workspace root, all confirmed to use `inline_image_ext='png'` and qCompress encoding
- **Anthropic Claude Vision docs** — primary docs on 1024 px sweet-spot
- **Codex CLI `--help`** — verified `-i, --image FILE...` flag

### MEDIUM confidence
- **Scribus PDF-as-image rendering** — community consensus from Scribus forums; renders but inferior to PNG path
- **Gemini CLI image input** — community workaround via `--include-directories`; switching to Python SDK is cleaner; needs Phase 4 spike
- **Codex DALL·E image generation** — referenced in [openai/codex#8758](https://github.com/openai/codex/issues/8758); user confirmed working in their session; Phase 3 spike per template

### LOW confidence (needs Phase 2 spike)
- **PDF-in-ImageFrame inline support** — claim on Scribus blog; pitfalls agent wrote-and-opened, but quality was visibly worse. PNG path bypasses the question entirely; we don't depend on this.
- **GS PNG byte-determinism** — likely deterministic but not exhaustively verified across distros. Mitigation: commit the PNG bytes to repo, build never re-runs `gs`.

---

## Plan Inputs (what PLAN.md needs to absorb)

1. **Six new blocks** with API signatures from `<interfaces>` block above.
2. **One new helper** (`pack_inline_image`) in `primitives.py`.
3. **Five new spec documents** + **one schema** + **three retro-specs**.
4. **One new tool**: `tools/visual_review.py` (multi-model image review).
5. **One new tool**: `tools/codex_image_gen.py` (one-shot demo image generation).
6. **One new tool**: `tools/spec_check.py` (spec ↔ build drift detector).
7. **Five new template directories** under `templates/<slug>/`.
8. **Asset paths**: `shared/assets/wahlkreuz-kreis.eps` (archival original) and `shared/assets/wahlkreuz.png` (bytes from `/root/workspace/Wahlkreuz.png`, RGBA, 1200×1299, used by `WahlkreuzSymbol`). No build-time conversion.
9. **Three review gates** orchestrated as separate execute phases.
10. **No CI workflow changes** required — local render + commit pipeline is unchanged. Only new repo paths to glob over.

Phase ordering exactly per the issue's revised phase plan (8 steps).
