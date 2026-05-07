# Plan: 5 neue Vorlagen + Spec-System + Visual-QA-Pipeline

<objective>
What this plan accomplishes:
- Establish a Markdown+YAML spec format under `templates/_specs/` and write 9 spec docs (1 schema + 5 new + 3 retro).
- Add **one** DSL helper (`pack_inline_image`) and **six** new live blocks (`WahlkreuzSymbol`, `FoldLine`, `DieCut`, `FoldedPanel`, `DoorHangerCutout`, `TableTentFold`) consistent with the existing live-block pattern.
- Ship five new production templates (Themen-Plakat A3, Wahlaufruf-Postkarte A6 quer, Wahltag-Türanhänger, Infostand-Tent-Card, Kandidat-Falzflyer DIN-lang) — each with `build.py`, `meta.yml`, `README.md`, smoke test, committed `template.sla`+`preview.pdf`+`page-*.png`, and (where applicable) Codex-generated demo images.
- Build local-only Visual-QA tooling: `tools/visual_review.py` (3-model orchestrator), `tools/spec_check.py` (drift detector), `tools/codex_image_gen.py` (one-shot demo image generator).
- Run three review gates with documented artifacts: Gate 1 (specs), Gate 2 (DSL+templates), Gate 3 (rendered visual QA with iteration loop).

Why it matters:
- Today the gallery has 3 templates; this delivers 5 more covering layout classes the brand currently lacks (folded multi-panel, querformat, die-cut, 3D-tent, wahlkampf-symbol).
- **Visual quality is the hard ship criterion.** Other Landesgruppen will look at this work; the new templates must look at least as good as the existing three, ideally better.
- The spec system + drift detector + visual-QA pipeline turn template authoring from ad-hoc into a repeatable process that survives iteration N to N+1.

Scope:
- IN: 9 specs, 6 new blocks + 1 helper, 5 new templates, 3 new tools, 3 review gates with documented iteration.
- OUT: Pillow dependency, Ghostscript at build time, layer/spot-color API additions (already exist), CI workflow changes, EPS to PDF conversion, Visual review on CI, items in CONTEXT.md "Deferred" section.

CONTEXT.md fidelity:
- D1 honored as **revised in RESEARCH.md** — uses existing /root/workspace/Wahlkreuz.png, no Ghostscript, archival EPS at shared/assets/wahlkreuz-kreis.eps.
- D4 honored as **revised in RESEARCH.md** — layer + spot-color APIs already exist; new colors stay document-local.
- D7 honored as **revised in RESEARCH.md** — ImageMagick montage not Pillow.
- D11 (Codex demo-image generation) and D12 (Wahlkreuz background-color rule) implemented as locked.
- D2, D3, D5, D6, D8, D9, D10 (deterministic asset commit), D11, D12 implemented as locked.
</objective>

<skills>
Read and follow these skills during execution:
- python — Python tools and DSL changes touch tools/sla_lib/builder/*.py and tools/*.py. Follow project conventions (snake_case, dataclasses, type hints), use existing patterns from blocks.py / primitives.py.
- git-committer — Atomic commits per task with the repo's "<id>: type(scope): subject" convention.
- issue:review — Multi-model orchestration (Claude + Codex + Gemini) for Gates 1, 2, 3.
</skills>

<context>
Issue: @.issues/10-5-neue-vorlagen-spec-system-visual-qa-pipeline/ISSUE.md
Decisions: @.issues/10-5-neue-vorlagen-spec-system-visual-qa-pipeline/CONTEXT.md
Research: @.issues/10-5-neue-vorlagen-spec-system-visual-qa-pipeline/RESEARCH.md
Codebase research: @.issues/10-5-neue-vorlagen-spec-system-visual-qa-pipeline/research/codebase.md
Ecosystem research: @.issues/10-5-neue-vorlagen-spec-system-visual-qa-pipeline/research/ecosystem.md
Pitfalls research: @.issues/10-5-neue-vorlagen-spec-system-visual-qa-pipeline/research/pitfalls.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

==== NEW HELPER: tools/sla_lib/builder/primitives.py ====

# Add near the existing ImageFrame (~line 742). ~10 LoC.
# Reference encoder pattern lives in tools/sla_lib/tests/test_sla_diff.py:340-349
# Reference decoder lives in tools/sla_to_dsl.py:202-216

import base64, struct, zlib

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).

    Scribus's inline ImageData attribute is qCompress-encoded:
    base64( 4-byte big-endian uncompressed-length prefix + zlib_compress(image_bytes) ).
    Naive base64 of raw bytes makes Scribus abort with qUncompress: Z_DATA_ERROR.

    Returns (qcompressed_b64, ext) — pass to ImageFrame as
    inline_image_data=..., inline_image_ext=ext.
    """
    blob = struct.pack(">I", len(image_bytes)) + zlib.compress(image_bytes, 6)
    return base64.b64encode(blob).decode("ascii"), ext


==== EXISTING (already in codebase, do NOT re-create) ====

# tools/sla_lib/builder/styles.py:17-29 — DocumentLayer dataclass
@dataclass
class DocumentLayer:
    name: str
    printable: bool = True       # SLA DRUCKEN
    flow: bool = True            # SLA FLOW (text flow around)
    transparency: float = 1.0    # SLA TRANS
    blendmode: int = 0           # SLA BLEND
    outline: bool = False        # SLA OUTL

# tools/sla_lib/builder/document.py
class Document:
    def __init__(self, ..., layers: list[DocumentLayer] | None = None, ...): ...      # :140-160
    def add_color(self, name: str, ..., spot: bool = False, register: bool = False) -> None: ...  # :247-263
    def add_master(self, name, size): ...
    def add_page(self, ...): ...

# tools/sla_lib/builder/primitives.py
class Anchor:                          # :111
    @classmethod
    def from_page(cls, where: str, x_offset_mm: float = 0, y_offset_mm: float = 0): ...

@dataclass
class ImageFrame(_Frame):              # :742
    pos: Anchor
    size: tuple[float, float]
    inline_image_data: str | None = None
    inline_image_ext: str | None = None
    scale_type: int = 1                # 0 = free, 1 = fit-to-frame
    ratio: int = 1                     # 1 = preserve aspect
    anname: str = ""
    local_scale: tuple[float, float] = (1.0, 1.0)

@dataclass
class TextFrame(_Frame): ...           # :532
@dataclass
class Polygon(_Frame): ...             # :825
                                       # supports custom_path (list of (x,y) mm), shape='ellipse',
                                       # fill, line_color, line_width, dash_pattern,
                                       # layer (layer_name string)


==== SIX NEW BLOCKS (add to tools/sla_lib/builder/blocks.py) ====

# Match existing live-block pattern: @dataclass + emit(self, page) -> Iterable.
# Append at the bottom of blocks.py (avoid merge conflict with issue #9).
# Each block carries a docstring citing source assets / spec / patterns.

@dataclass
class WahlkreuzSymbol:
    """Wahlkreuz im Kreis (yellow cross + white circle).

    The PNG asset has a white outer circle. On a white background the circle
    disappears — only the yellow cross stays visible. Per D12, this block draws
    a colored background polygon BEFORE placing the ImageFrame, so the white
    ring stays visible. Default background: Dunkelgruen.

    Source asset: shared/assets/wahlkreuz.png (RGBA 1200x1299, copied from
    /root/workspace/Wahlkreuz.png — no Ghostscript step).
    """
    pos: Anchor
    size: tuple[float, float]                # (w_mm, h_mm)
    background_color: str = "Dunkelgruen"    # D12: never White, never Gelb
    background_padding_mm: float = 4.0
    anname: str = "Wahlkreuz"
    def emit(self, page) -> Iterable: ...

@dataclass
class FoldLine:
    """Strichlierte Falz-Linie auf 'Falz'-Layer mit Spot-Color-Stroke."""
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
    """Wrapper for a single panel of a folded flyer.

    Provides margin handling and auto-positions a FoldLine on the right edge
    if not the last panel. Caller adds children to the panel.
    """
    panel_index: int                            # 0-based
    panel_count: int                            # 3 for DIN-lang
    panel_size_mm: tuple[float, float]          # (99, 210) for DIN-lang vertical
    has_fold_right: bool = True
    children: list = field(default_factory=list)
    def emit(self, page) -> Iterable: ...

@dataclass
class DoorHangerCutout:
    """Standard door-hanger outer + handle-hole stanzpfad.

    105x250 mm with circular hole at top (35 mm diameter, 25 mm from top edge).
    Auto-emits a DieCut on Stanzkontur layer.
    """
    page_size_mm: tuple[float, float] = (105, 250)
    hole_diameter_mm: float = 35
    hole_top_offset_mm: float = 25
    def emit(self, page) -> Iterable: ...

@dataclass
class TableTentFold:
    """A4 quer folded into A5 tent: emits horizontal Falz-line at center."""
    page_size_mm: tuple[float, float] = (297, 210)
    def emit(self, page) -> Iterable: ...
</interfaces>

Key files:
@tools/sla_lib/builder/primitives.py — add `pack_inline_image()` near ImageFrame
@tools/sla_lib/builder/blocks.py — append 6 new blocks at bottom (avoid #9 conflicts)
@tools/sla_lib/builder/styles.py — DocumentLayer (use as-is, do not modify)
@tools/sla_lib/builder/document.py — add_color(spot=True), layers=[…] (use as-is)
@tools/sla_lib/tests/test_blocks.py — append unit tests for 6 new blocks
@tools/sla_lib/tests/test_sla_diff.py:340-349 — qCompress encoder reference for the helper
@tools/visual_diff.py:188-195 — montage invocation pattern to copy into visual_review.py
@templates/postkarte-a6-kampagne/build.py — reference live-template build pattern
@templates/postkarte-a6-kampagne/meta.yml — reference meta.yml schema
@shared/ci.yml — brand colors and styles (DO NOT add Falz/Stanzkontur here per D4 revised)
@shared/assets/wahlkreuz.png — copy from /root/workspace/Wahlkreuz.png in Task 9 (created during execute)
@shared/assets/wahlkreuz-kreis.eps — archival original (created during execute)
@bin/render-gallery — local-only render entry point (Scribus + pdftoppm)
@bin/check-stale-previews — SHA pin enforcement (must stay green)
@bin/validate — global validator
@.github/workflows/pages.yml — DO NOT modify; CI runs build/check/gallery_build only

Cross-issue:
- Issue #9 (post-migration-dsl-hygiene) is in flight on a parallel branch and also touches
  tools/sla_lib/builder/blocks.py and test_blocks.py. Append all new code at the bottom
  of files (no insertion in the middle) to keep the rebase trivial.
</context>

<commit_format>
Format: conventional with issue prefix
Pattern: `10: TYPE(SCOPE): description`
Examples:
- `10: feat(specs): add SCHEMA.md for template specs`
- `10: feat(blocks): add WahlkreuzSymbol with colored background fill`
- `10: feat(template): wahlaufruf-postkarte-a6-quer build + smoke + previews`
- `10: chore(review): record gate-1 spec-review report`
- `10: fix(template): tighten headline hierarchy on themen-plakat per visual review`

No "claude" attribution anywhere (commits, code, file names, generated content) per memory rule.
</commit_format>

<tasks>

<!-- ============================================================ -->
<!-- PHASE 1 — SPEC FOUNDATION (A1, A2, A3)                       -->
<!-- ============================================================ -->

<task type="auto">
  <name>Task 1: Spec schema doc (templates/_specs/SCHEMA.md)</name>
  <files>templates/_specs/SCHEMA.md</files>
  <action>
  Create templates/_specs/SCHEMA.md defining the Markdown+YAML spec format per CONTEXT.md D2.
  This is the single source of truth for how every spec under templates/_specs/SLUG.md is
  structured.

  Required sections:
  1. Frontmatter / mandatory fields — title, audience, format (e.g. "A6 quer 2-seitig"),
     trim_mm (w x h), bleed_mm, fold_type (none|wickelfalz|zickzack|altar|tent), pages.
  2. Audience and Layout-Philosophie — German prose, free-form, 2-4 sentences.
  3. ASCII layout convention — fenced code blocks. Box-drawing chars for frame outlines,
     dimension callouts as "<-210mm->", slot markers like H1, B, I with a legend. One ASCII
     skizze per visible side. Origin = top-left of trim corner (NOT bleed corner) — this
     is the canonical convention to prevent P-PRINT-2.
  4. Slot table — Markdown table with columns: anname, type (TextFrame/ImageFrame/Polygon/
     Block), x_mm, y_mm, w_mm, h_mm, fcolor (or ref: link to a Block), style_ref (refs
     shared/ci.yml styles), example (realistic text/content). Coordinates are mm from
     trim top-left.
  5. EPS / image embedding strategy — for templates using the Wahlkreuz, document: asset
     path, scale_type (0 free / 1 fit), background_color (D12 contract), and that
     pack_inline_image() is required. State explicitly: white circle invisible on white;
     never place on plain Weiss or plain Gelb.
  6. Background-color contract for Wahlkreuz — verbatim text reproducing D12: must be
     Dunkelgruen, Hellgruen, or Magenta; never Weiss or Gelb. Mark as a hard rule.
  7. Falz / Stanze conventions — coordinate origin = trim top-left (NOT bleed). Falz
     positions in absolute mm from origin. Spot colors are document-local (build.py adds
     them via doc.add_color(name, spot=True, ...) — NOT in shared/ci.yml). Layers stack
     bottom to top: Hintergrund, Bilder, Text, Falz, Stanzkontur.
  8. Brand-hierarchy contract — typography/whitespace/color rules the spec must satisfy:
     H1 >= 22pt for A6-quer; >= 36pt for A1; >= 16pt for DIN-lang panels; min body 9pt.
     shared/ci.yml-only colors/styles by default; non-CI requires meta.yml.ci_overrides
     justification.
  9. Print hints — bleed_mm, fold_mm, cut_layer name, min_dpi, paper recommendation,
     stanzkontur naming variants (Stanzkontur is default DACH; CutContour for international
     printers). Impressum requirement (Mediengesetz §24).
  10. Messaging legality (Wahlaufruf templates) — placeholder text must be encouraging,
      not directive. AVOID: "Mach dein Kreuz bei den Gruenen". USE: "Waehle Gruen am
      [Datum]". Reference NRWO §53 (Wahlanleitung-Verbot).
  11. Drift policy (D3) — spec is contract; deviations require spec-update + Reviewer
      sign-off. tools/spec_check.py mechanically diffs spec slots vs build output.

  Tone: precise, German prose for descriptions, English snake_case for keys, mm everywhere.
  Length: ~250-400 lines.
  Reference shared/template-spec.schema.yaml for prior-art slot field naming — match the keys
  but DO NOT extend that schema (it's a different document genre).
  </action>
  <verify>
  <automated>test -f templates/_specs/SCHEMA.md && python3 -c "import sys; t=open('templates/_specs/SCHEMA.md').read().lower(); req=['ascii','slot','bleed','fold','wahlkreuz','falz','stanzkontur','impressum','origin','trim']; missing=[w for w in req if w not in t]; sys.exit(f'missing sections: {missing}' if missing else 0)"</automated>
  </verify>
  <done>
  - templates/_specs/SCHEMA.md exists with all 11 sections.
  - ASCII convention worked example included (showing one slot in a sample frame).
  - D12 Wahlkreuz background-color rule reproduced verbatim.
  - Coordinate-origin convention stated as "trim top-left, NOT bleed corner".
  - Layer stack order documented.
  - Commit: 10: feat(specs): add SCHEMA.md for template specs
  </done>
</task>

<task type="auto">
  <name>Task 2: Three retro-specs for existing templates</name>
  <files>templates/_specs/_existing-postkarte-a6-kampagne.md, templates/_specs/_existing-plakat-a1-hochformat.md, templates/_specs/_existing-zeitung-a4-grun.md</files>
  <action>
  Reverse-engineer one retro-spec per existing template under templates/_specs/_existing-SLUG.md
  per CONTEXT.md D9. Read the template's meta.yml + build.py + actual template.sla (use
  `xmllint --xpath '//PAGEOBJECT/@ANNAME' template.sla 2>/dev/null` for slot inventory) and
  produce a spec exactly conforming to SCHEMA.md (Task 1).

  Retro-specs validate the schema — if a real template can't be expressed, SCHEMA.md is
  not good enough and Task 1 must be revised.

  For each:
  - Audience + Layout-Philosophie (2-3 sentences inferred from README + meta.yml).
  - Trim/Bleed mm exactly per build.py.
  - ASCII-Skizze of every page from actual frame coordinates (rounded to whole mm).
  - Slot table with anname, type, x/y/w/h_mm matching the SLA exactly, fcolor matching CI,
    style_ref matching shared/ci.yml, example matching meta.yml.slots.id.example.
  - No EPS embedding strategy (none of the existing 3 templates use Wahlkreuz).
  - No Falz/Stanze (none of the existing 3 templates use these).
  - Print hints from meta.yml.
  - Brand hierarchy notes for cross-comparison: list every font size used, color palette,
    whitespace rhythm — these become the calibration baseline that the 5 new specs and
    Gate 3 reviews compare against.

  Length per file: ~150-300 lines. Order of writing: Postkarte first (smallest), then Plakat,
  then Zeitung (most complex). This order is intentional — start small, work up.

  As you write, if SCHEMA.md cannot express something the existing template does, STOP and
  revise SCHEMA.md before continuing. Document any such revisions in the relevant retro-spec
  body for traceability.
  </action>
  <verify>
  <automated>for f in templates/_specs/_existing-postkarte-a6-kampagne.md templates/_specs/_existing-plakat-a1-hochformat.md templates/_specs/_existing-zeitung-a4-grun.md; do test -f "$f" || { echo "missing $f"; exit 1; }; grep -qi audience "$f" || { echo "$f missing audience"; exit 1; }; grep -qi slot "$f" || { echo "$f missing slot table"; exit 1; }; done</automated>
  </verify>
  <done>
  - Three retro-spec files exist conforming to SCHEMA.md.
  - Slot annames in each retro-spec match the actual SLA frame annames (verifiable via xmllint).
  - At least 5 specific brand-hierarchy observations per spec (font sizes, color use, etc.)
    that future specs and Gate 3 reviews can cite as the baseline.
  - Commit: 10: feat(specs): retro-specs for postkarte/plakat/zeitung as schema validation
  </done>
</task>

<task type="auto">
  <name>Task 3: Spec — themen-plakat-a3-quer (simplest, no EPS, no fold)</name>
  <files>templates/_specs/themen-plakat-a3-quer.md</files>
  <action>
  Write the spec for the A3 quer Themen-Plakat. This template is deliberately first of the
  new specs because it has no EPS embedding, no folding, no die-cutting — it's the cleanest
  exercise of the schema for a brand-typical layout.

  Format: A3 quer = 420 x 297 mm, 1-seitig, 3 mm bleed all around.
  Layout-Philosophie: Argumentation: These -> Belege -> Quelle. Three-column grid with thesis
  spanning the top, three-column evidence grid below, source citation at bottom.

  Constraints:
  - Coordinate origin = trim top-left.
  - Margins 15 mm side, 12 mm top/bottom (matches Plakat A1 conventions scaled).
  - 3-column grid: gutter 8 mm explicit (not Scribus default 11pt — see P-A3-1).
    Column width = (420 - 30 - 16) / 3 ~= 124.7 mm.
  - Headline >= 36 pt (A3 distance ~50-100cm); body >= 11 pt; min DPI 300 for any image.
  - Background: brand color from shared/ci.yml (recommend a Hellgruen or Weiss + Magenta accent —
    pick one and document why).

  Slot inventory (target ~10 slots):
  - headline_thesis — large, top, 1-2 lines, span full content width.
  - subheadline — optional supporting line under thesis.
  - evidence_1_headline, evidence_1_body — column 1.
  - evidence_2_headline, evidence_2_body — column 2.
  - evidence_3_headline, evidence_3_body — column 3.
  - source_citation — small text, bottom, full width.
  - impressum — small text, bottom corner (Mediengesetz §24).
  - logo_grueneAT — top corner or bottom corner.

  Realistic example content: thesis like "Klimaschutz ist Wirtschaftspolitik", three evidence
  beats with source-cited statistics. NOT placeholder lorem ipsum — real-feeling NOe campaign
  copy. Source citation contains a concrete reference.

  ASCII-Skizze of the single page showing all slots with coordinates.
  Print hints: 3 mm bleed, no fold, 300 DPI min for any image, recommend offset print for >=A3.
  Brand-hierarchy contract block listing every font size + color used.

  Length: 200-350 lines. This is the calibration spec — get it tight; subsequent specs will
  reference its hierarchy patterns.
  </action>
  <verify>
  <automated>test -f templates/_specs/themen-plakat-a3-quer.md && grep -qE "420.*297|297.*420" templates/_specs/themen-plakat-a3-quer.md && grep -qi impressum templates/_specs/themen-plakat-a3-quer.md && grep -qi gutter templates/_specs/themen-plakat-a3-quer.md</automated>
  </verify>
  <done>
  - Spec file exists, conforms to SCHEMA.md.
  - All 10 slots present with mm coordinates.
  - Headline >= 36 pt, body >= 11 pt, gutter explicit in mm.
  - Realistic example content (no lorem).
  - Brand hierarchy block enumerated.
  - Commit: 10: feat(specs): themen-plakat-a3-quer spec
  </done>
</task>

<task type="auto">
  <name>Task 4: Spec — wahlaufruf-postkarte-a6-quer (Wahlkreuz + 2-sided)</name>
  <files>templates/_specs/wahlaufruf-postkarte-a6-quer.md</files>
  <action>
  Spec for A6 quer Wahlaufruf-Postkarte: 148 x 105 mm, 2-seitig, Wahlkreuz hero front + info
  grid back.

  Front:
  - Wahlkreuz hero, centered, 60-70 mm diameter.
  - Headline below it: "Waehle Gruen am [Datum]" — 22pt min (P-PRINT-5), Gotham Narrow Bold.
  - Background: Dunkelgruen (D12 contract). Wahlkreuz must sit on Dunkelgruen for white ring
    to remain visible.
  - WahlkreuzSymbol block, default background_color="Dunkelgruen", padding 4 mm.

  Back (info-grid):
  - 2x2 grid (NOT 3x2 — see P-A6QUER-1) of cells. Each cell: small headline + 1-2 line body.
  - Cell content examples: "Was wir tun", "Warum Gruen", "Wann gewaehlt wird", "Wo informieren".
  - Body 9 pt min, cell-headline 14 pt min.
  - Impressum bottom strip, full width, 6 pt.
  - Logo top-left corner.

  Wahlkreuz section (per SCHEMA.md): asset = shared/assets/wahlkreuz.png, scale_type=0,
  background_color="Dunkelgruen", background_padding_mm=4.0. Quote D12 verbatim. Reference
  D11 — gallery preview will show with one Codex demo image (back side) but slot stays
  optional in meta.yml.

  Messaging legality: example placeholders use "Waehle Gruen", never "Kreuze hier".
  Reference NRWO §53.

  Bleed 3 mm, trim 148 x 105 mm. ASCII-Skizze for both sides.
  Length: 250-350 lines. This spec is the first Wahlkreuz spec — get the WahlkreuzSymbol
  contract tight; templates 4 and 5 will reference it.
  </action>
  <verify>
  <automated>test -f templates/_specs/wahlaufruf-postkarte-a6-quer.md && grep -qi wahlkreuz templates/_specs/wahlaufruf-postkarte-a6-quer.md && grep -qiE "dunkelgruen|dunkelgrün" templates/_specs/wahlaufruf-postkarte-a6-quer.md && grep -qE "148.*105|105.*148" templates/_specs/wahlaufruf-postkarte-a6-quer.md && grep -qi D12 templates/_specs/wahlaufruf-postkarte-a6-quer.md</automated>
  </verify>
  <done>
  - Spec exists, both sides ASCII-skizzed, ~12 slots total.
  - Wahlkreuz section explicitly references D12 background-color contract.
  - Headline >= 22 pt, body >= 9 pt; 2x2 grid not 3x2.
  - Messaging-legality note present (NRWO §53 ref).
  - Commit: 10: feat(specs): wahlaufruf-postkarte-a6-quer spec with Wahlkreuz contract
  </done>
</task>

<task type="auto">
  <name>Task 5: Spec — wahltag-tueranhaenger (Stanzkontur + Wahlkreuz)</name>
  <files>templates/_specs/wahltag-tueranhaenger.md</files>
  <action>
  Spec for 105 x 250 mm Tueranhaenger with door-handle hole + Wahlkreuz.

  Format: 105 x 250 mm, vertical, 1-seitig (or 2-seitig — pick 2-seitig for richer messaging),
  bleed 2 mm (die-cut tighter than 3 mm).
  Stanzkontur: outer rectangle path + 35 mm circular hole, 25 mm from top edge, centered.
  Bleed safety: 2 mm clear from any die-cut edge to first content.

  Layout (front):
  - Top zone above the hole (~20 mm): brand bar with logo.
  - Hole zone (35 mm): kept clear of all content.
  - Mid-upper (after hole, ~35-105 mm from top): Wahlkreuz hero (40-50 mm) on Dunkelgruen
    or Hellgruen band, with Headline "Waehle Gruen" right below.
  - Lower (~110-230 mm): 2-3 short bullets / dates, contact info.
  - Bottom strip: Impressum, <= 8 mm.

  Back (optional second page):
  - Larger photo slot (Codex demo image; optional in meta.yml per D11).
  - Short call-to-action.
  - Repeat Impressum.

  Stanzkontur details:
  - Spot color Stanzkontur (CMYK 0/100/0/0, document-local — D4 revised, NOT in ci.yml).
  - Layer Stanzkontur (printable=False, flow=False, exportable=True).
  - Layer stack bottom to top: Hintergrund, Bilder, Text, Falz (none here), Stanzkontur on top.
  - Hole shape: round, 35 mm diameter. Note alternative variant keyhole (40 x 20 mm) per
    P-PRINT-3 — but pick round as default.

  Wahlkreuz section: as Task 4, reference D12, default Dunkelgruen or Hellgruen band.
  Print-shop variant note: Stanzkontur (DACH default), CutContour (international) —
  document both per P-PRINT-1.

  ASCII-Skizze showing trim outline + hole position + content zones + Stanzkontur layer.
  Length: 250-400 lines.
  </action>
  <verify>
  <automated>test -f templates/_specs/wahltag-tueranhaenger.md && grep -qi stanzkontur templates/_specs/wahltag-tueranhaenger.md && grep -qE "105.*250|250.*105" templates/_specs/wahltag-tueranhaenger.md && grep -qE "35.*mm|35mm" templates/_specs/wahltag-tueranhaenger.md && grep -qi wahlkreuz templates/_specs/wahltag-tueranhaenger.md</automated>
  </verify>
  <done>
  - Spec exists with both sides ASCII-skizzed.
  - Stanzkontur path described (outer + hole, 35 mm round).
  - Layer stack order documented.
  - Wahlkreuz background-color contract referenced.
  - Print-shop spot-color naming variants documented.
  - Commit: 10: feat(specs): wahltag-tueranhaenger spec with Stanzkontur + Wahlkreuz
  </done>
</task>

<task type="auto">
  <name>Task 6: Spec — infostand-tent-card-a5-quer (Falz + 3D)</name>
  <files>templates/_specs/infostand-tent-card-a5-quer.md</files>
  <action>
  Spec for Infostand-Tent-Card: A4 quer (297 x 210 mm) gefalzt -> A5-Tent.
  Single fold horizontal at 105 mm (halving the 210 mm dimension), giving two 297 x 105 mm
  panels each visible doppelseitig.

  Layout-Philosophie: 3D doppelseitig sichtbar. Two A5-quer panels read top-down when standing;
  text on each panel must be readable at table-eye distance (~50-80 cm).

  Constraints:
  - Trim 297 x 210 mm, bleed 3 mm (folded, not die-cut, so 3 mm safe).
  - Fold line horizontal at y=105 mm (centered on long axis).
  - Bottom 3 mm of each panel = table-contact zone — leave clear of text (P-PRINT-4).
  - Body >= 14 pt (read at distance), headline >= 28 pt.
  - Each panel reads independently (assembled tent shows panel A facing one direction,
    panel B the opposite).

  Slot inventory:
  - panel_a_headline (Side A, 297 x 105 mm minus margins).
  - panel_a_body (2-3 lines).
  - panel_a_image (optional, Codex demo image per D11).
  - panel_a_logo.
  - panel_b_headline (Side B, mirrored layout).
  - panel_b_body.
  - panel_b_qr_code (optional, for event registration).
  - impressum (must appear at least once, on the side that always faces forward).

  Falz section: TableTentFold block emits a horizontal FoldLine at y=105 mm on the Falz layer.
  Spot color Falz (CMYK 100/0/0/0), document-local. Layer Falz (printable=False).

  Wahlkreuz: optional. If used, place on a colored band (D12 contract). NOT a default.

  Print hints: 3 mm bleed all around, fold at 105 mm horizontal, 250-300 g/m^2 paper for
  free-standing rigidity, dry-trim acceptable for fold (no perforation needed at this paper
  weight).

  ASCII-Skizze: flat layout (297 x 210 mm) with fold line + panel labels A and B; plus a
  3D side-view skizze showing the assembled tent with table contact zone.
  Length: 200-300 lines.
  </action>
  <verify>
  <automated>test -f templates/_specs/infostand-tent-card-a5-quer.md && grep -qi falz templates/_specs/infostand-tent-card-a5-quer.md && grep -qE "297.*210|210.*297" templates/_specs/infostand-tent-card-a5-quer.md && grep -qE "105.*mm|105mm" templates/_specs/infostand-tent-card-a5-quer.md && grep -qi tent templates/_specs/infostand-tent-card-a5-quer.md</automated>
  </verify>
  <done>
  - Spec exists with flat + 3D ASCII skizzes.
  - Fold line position 105 mm horizontal documented.
  - Two panels each have a slot inventory.
  - Bottom 3 mm contact zone documented.
  - Headlines >= 28 pt, body >= 14 pt for table-distance readability.
  - Commit: 10: feat(specs): infostand-tent-card-a5-quer spec with TableTentFold
  </done>
</task>

<task type="auto">
  <name>Task 7: Spec — kandidat-falzflyer-din-lang (3-fach Falz + Wahlkreuz closer)</name>
  <files>templates/_specs/kandidat-falzflyer-din-lang.md</files>
  <action>
  Spec for Kandidat-Falzflyer DIN-lang: A4 quer (297 x 210 mm) 3-fach gefalzt -> 6 panele
  (3 front + 3 back), each 99 x 210 mm.

  Falz type: zickzackfalz (Z-fold/accordion) — uniform 99 mm panels, simpler design and
  print, accepted by Austrian/German printers (per ecosystem research §6.3). Wickelfalz
  noted as alternative in print hints.

  Panel order on flat sheet (front side, reading L to R):
  - Panel 1 (cover): Kandidat portrait + Name + Slogan (this is what users see closed).
  - Panel 2 (inside-fold-back): not visible until partly opened — short teaser.
  - Panel 3 (closer-back): closer panel — Wahlkreuz hero + "Waehle Gruen am [Datum]".
    Per D12, on Dunkelgruen or Hellgruen band.

  Back side (open, reading L to R):
  - Panel 4 (open-left): Themen 1+2 short.
  - Panel 5 (open-mid): Themen 3+4 short.
  - Panel 6 (open-right): contact info + Impressum.

  Layout-Philosophie: Multi-panel narrative. Cover hooks; first opening reveals teaser;
  full opening shows themes; closing panel drives action via Wahlkreuz.

  Constraints:
  - Trim 297 x 210 mm. Bleed 3 mm.
  - Fold lines at x=99 mm and x=198 mm.
  - Coordinate origin = trim top-left.
  - Per-panel content area: 99 mm minus 6 mm safety (3 mm each side from fold/trim) =
    93 mm usable width.
  - Headline per-panel >= 16 pt; body >= 9 pt.

  Slot inventory (~18 slots, 3 per panel x 6 panels):
  - p1_portrait, p1_name, p1_slogan.
  - p2_teaser_headline, p2_teaser_body, p2_logo.
  - p3_wahlkreuz, p3_headline, p3_date.
  - p4_thema1_headline, p4_thema1_body, p4_thema2_headline, p4_thema2_body.
  - p5_thema3_headline, p5_thema3_body, p5_thema4_headline, p5_thema4_body.
  - p6_contact, p6_qr, p6_impressum.

  Wahlkreuz section: panel 3, on Dunkelgruen background (D12). Realistic placeholder text
  matching messaging legality (P-PRINT-7).

  Falz block: FoldedPanel(panel_index=0..5, panel_count=3, panel_size_mm=(99, 210),
  has_fold_right=...). Panels 1,2 have has_fold_right=True; panel 3 has has_fold_right=False.
  Same on back side. FoldLine at x=99 and x=198 on Falz layer.

  ASCII-Skizze: flat front + flat back + folded-state schematic showing reading order.
  Print hints: 3 mm bleed, zickzackfalz, 130-170 g/m^2 paper, 300 DPI portrait min,
  recommend Bilderdruck matt finish.
  Length: 350-500 lines (most complex of the 5).
  </action>
  <verify>
  <automated>test -f templates/_specs/kandidat-falzflyer-din-lang.md && grep -qi zickzack templates/_specs/kandidat-falzflyer-din-lang.md && grep -qE "99.*210|210.*99" templates/_specs/kandidat-falzflyer-din-lang.md && grep -qi wahlkreuz templates/_specs/kandidat-falzflyer-din-lang.md && grep -qi panel templates/_specs/kandidat-falzflyer-din-lang.md</automated>
  </verify>
  <done>
  - Spec exists with flat-front + flat-back + folded-state ASCII skizzes.
  - 6 panels documented with reading order.
  - Wahlkreuz on closer panel with D12 contract.
  - Falz lines at x=99 and x=198 documented.
  - ~18 slots present.
  - Commit: 10: feat(specs): kandidat-falzflyer-din-lang spec with 3-fach Zickzackfalz
  </done>
</task>

<!-- ============================================================ -->
<!-- GATE 1 — SPEC-REVIEW                                         -->
<!-- ============================================================ -->

<task type="auto" review="gate-1">
  <name>Task 8: Gate 1 — Spec-Review (Multi-Model)</name>
  <files>reviews/spec-review-1.md, reviews/spec-review-2.md (if iteration needed), templates/_specs/*.md (potential fixes)</files>
  <action>
  Run /issue:review skill orchestration over the 9 spec docs from Tasks 1-7
  (1 SCHEMA + 3 retro + 5 new). This is a NON-CODE review: pure spec reading by
  Claude + Codex + Gemini.

  Reviewer prompt MUST stress (verbatim, in this order):
  1. **VISUAL QUALITY IS THE PRIMARY CRITERION.** Are the specs precise enough that
     two implementers would produce templates of equal visual quality?
  2. Do the new specs propose layouts AT LEAST AS GOOD as the three retro-specs
     (postkarte / plakat / zeitung)? Where do they look better? Where weaker?
  3. Hierarchy: Headline > Sub > Body > Akzent > Impressum on brand-niveau in every spec?
  4. Typography mixing, whitespace, color use specified to brand level?
  5. Risks: slots zu eng, text-laengen unrealistic, EPS scale undefined, fold/cut
     dimensions inconsistent?
  6. Does each Wahlkreuz spec correctly cite D12 background-color contract?
  7. Coordinate origin = trim top-left in every spec? Falz/Stanze positions consistent?
  8. Messaging legality (NRWO §53, Mediengesetz §24) addressed?

  Reviewer output: structured Markdown with sections per spec; merge_ready: yes/no;
  blocking_findings (must address); nice_to_have (advisory).

  Process:
  - Run /issue:review (or equivalent multi-model orchestration) with the spec files
    as input.
  - Save raw outputs into reviews/spec-review-1.md (one file with sections per
    reviewer).
  - For every blocking_finding: either fix the spec (commit "10: fix(specs): address
    gate-1 finding X") or document a justified rejection in reviews/spec-review-1.md.
  - If after Round 1 any reviewer still says merge_ready=no, run a second round
    (reviews/spec-review-2.md). Cap at 3 rounds (D6 cap applies to the spec gate too).

  Quality emphasis: The user said "iterate often, review often." Plan for at least
  one iteration on the spec set — first-pass merge-ready is unlikely with 9 docs.

  Do NOT begin Phase 2 (DSL changes) until Gate 1 reaches consensus or human-override.
  </action>
  <verify>
  <automated>test -f reviews/spec-review-1.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/spec-review-1.md && grep -qE "claude|codex|gemini" reviews/spec-review-1.md</automated>
  </verify>
  <done>
  - reviews/spec-review-1.md exists with all three reviewer sections (Claude, Codex, Gemini).
  - All blocking findings either addressed (commit) or rejected with justification in the report.
  - Final consensus state recorded: 3/3 merge_ready=yes OR human-override documented.
  - At least 1 iteration attempted; if Round 1 was unanimous, document why.
  - Commit: 10: chore(review): record gate-1 spec-review consensus
  </done>
</task>

<!-- ============================================================ -->
<!-- PHASE 2 — DSL EXTENSIONS (B2, B3)                            -->
<!-- ============================================================ -->

<task type="auto" tdd="true">
  <name>Task 9: Wahlkreuz assets + pack_inline_image helper</name>
  <files>shared/assets/wahlkreuz.png, shared/assets/wahlkreuz-kreis.eps, tools/sla_lib/builder/primitives.py, tools/sla_lib/tests/test_primitives.py</files>
  <action>
  Two atomic changes; commit separately for clean history.

  Step 9a — Asset placement:
  - Copy /root/workspace/Wahlkreuz.png to shared/assets/wahlkreuz.png (binary copy).
  - Copy "/root/workspace/Wahl Kreuz im Kreis.eps" to shared/assets/wahlkreuz-kreis.eps
    (archival original; build does not consume the EPS — see RESEARCH.md D1 revised).
  - Verify: SHA256 of /root/workspace/Wahlkreuz.png matches shared/assets/wahlkreuz.png.
  - Verify PNG is RGBA 1200x1299 via `python3 -c "import struct; d=open('shared/assets/wahlkreuz.png','rb').read(); print(struct.unpack('>II', d[16:24]))"`
    -> expect (1200, 1299).
  - Commit: 10: feat(assets): add wahlkreuz.png and archival EPS

  Step 9b — pack_inline_image helper (TDD):
  - RED: write tests in tools/sla_lib/tests/test_primitives.py for pack_inline_image:
    * Returns tuple (str, str) where first is base64-encoded.
    * The base64-decoded payload starts with 4-byte big-endian length prefix that equals
      len(input_bytes).
    * After zlib.decompress on the payload-after-prefix, you get back the original bytes
      identically.
    * Empty bytes produce a valid encoding (4 zero bytes prefix + zlib-empty).
    * ext is passed through unchanged.
    * Round-trip: decode the result and confirm it matches reference encoder in
      tools/sla_lib/tests/test_sla_diff.py:340-349.
  - GREEN: add pack_inline_image to tools/sla_lib/builder/primitives.py near ImageFrame
    (~line 742-820 region). ~10 LoC implementation per the <interfaces> contract above.
    Place it as a module-level function (not a class method).
    Add to tools/sla_lib/builder/__init__.py public exports.
  - REFACTOR: ensure docstring quotes "qCompress" explicitly and references the failure
    mode if used wrong.

  Verify final: `python3 -m pytest tools/sla_lib/tests/test_primitives.py -k pack_inline -v`
  </action>
  <verify>
  <automated>python3 -c "import hashlib; a=open('/root/workspace/Wahlkreuz.png','rb').read(); b=open('shared/assets/wahlkreuz.png','rb').read(); assert hashlib.sha256(a).hexdigest()==hashlib.sha256(b).hexdigest(), 'PNG mismatch'; print('PNG OK')" && test -f shared/assets/wahlkreuz-kreis.eps && python3 -m pytest tools/sla_lib/tests/test_primitives.py -k pack_inline -v</automated>
  </verify>
  <done>
  - shared/assets/wahlkreuz.png exists, byte-identical to source.
  - shared/assets/wahlkreuz-kreis.eps exists (archival).
  - pack_inline_image tests pass (5+ assertions covering qCompress format, round-trip, empty input).
  - pack_inline_image exported from tools/sla_lib/builder package.
  - Commits: "10: feat(assets): add wahlkreuz.png and archival EPS" and "10: feat(primitives): add pack_inline_image helper for inline ImageData"
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 10: Six new blocks in tools/sla_lib/builder/blocks.py</name>
  <files>tools/sla_lib/builder/blocks.py, tools/sla_lib/tests/test_blocks.py</files>
  <action>
  Add 6 new live blocks to the BOTTOM of tools/sla_lib/builder/blocks.py (no insertions
  in the middle — minimizes #9 conflict per P-DSL-2). Match the existing live-block
  pattern exactly: @dataclass, emit(self, page) -> Iterable, sensible anname defaults,
  docstring citing source/spec.

  Use the API signatures verbatim from <interfaces> above. Implement TDD-style:

  Behaviors per block (RED tests):

  WahlkreuzSymbol:
  - emit() yields a Polygon (background fill at background_color, padded
    background_padding_mm beyond size box) followed by an ImageFrame (loads
    shared/assets/wahlkreuz.png, calls pack_inline_image, scale_type=0,
    inline_image_ext='png').
  - With background_color="Weiss" or "Gelb", emit() raises ValueError citing D12.
  - The Polygon and ImageFrame share the same anchor logic; the polygon is layered below.
  - Default anname "Wahlkreuz".
  - Test: build a 1-page SLA via Document with this block; assert the SLA has a Polygon
    fill before the ImageFrame in element order.

  FoldLine:
  - emit() yields a Polygon with custom_path=[start_mm, end_mm], layer set to
    layer_name, line_color=spot_color, line_width matching line_width_pt, dash_pattern
    matching the dataclass default.
  - line_width_pt converts to whatever the Polygon line-width unit is (mm? pt?
    inspect Polygon's line_width docstring to confirm).
  - Default anname "Falzlinie".
  - Test: emit on a layer named "Falz"; assert the SLA Polygon has LAYER attribute
    pointing at "Falz" and stroke=Falz spot color.

  DieCut:
  - emit() yields a Polygon with custom_path=path_mm (closed polygon — first point
    appended at end if not already closed), layer=layer_name, line_color=spot_color,
    line_width_pt=0.25 default, no fill (transparent).
  - Default anname "Stanzkontur".
  - Test: build a 4-point rectangle path; assert SLA has a closed Polygon on Stanzkontur
    layer.

  FoldedPanel:
  - emit() yields whatever children include in their emits, positioned within the
    panel's bbox; AND a FoldLine on the right edge if has_fold_right=True.
  - Pure layout wrapper; does no rendering itself other than potentially the right-edge
    FoldLine.
  - Test: panel_index=0, panel_count=3, panel_size_mm=(99,210), no children;
    assert one FoldLine emitted at x=99 mm (right edge of panel 0).

  DoorHangerCutout:
  - emit() yields a DieCut with the outer rectangle (4 corners with bleed inset 0)
    AND a circular hole approximated as a 36-segment polygon at top-center
    (x=page_w/2, y=hole_top_offset_mm + hole_diameter_mm/2).
  - Test: page_size_mm=(105,250); assert the emitted DieCut path has >=40 points
    (4 corners + 36+ circle segments).

  TableTentFold:
  - emit() yields a single horizontal FoldLine at y = page_h/2 spanning the full
    page width.
  - Test: page_size_mm=(297,210); assert FoldLine.start_mm=(0,105), end_mm=(297,105).

  Common test scaffolding for tools/sla_lib/tests/test_blocks.py:
  - Use unittest.TestCase. One TestCase class per block.
  - Use existing helpers from test_blocks.py for SLA building / parsing where they
    exist; otherwise inline-build a minimal Document.
  - Save SLAs to a tempfile, parse with sla_lib reader, assert structural invariants.
  - Each block class needs >=3 tests (basic emit, edge cases, integration with
    Document). 18+ new tests total.

  Round-trip safety:
  - After adding the new blocks, run python3 tools/sla_diff.py for each existing
    template (postkarte, plakat, zeitung). All three must remain green (P-DETERMINISM-1).
    If any fails, the new blocks have leaked into the shared emission paths — fix before
    moving on.

  Commit pattern: one commit per block (six commits total). Each commit messages:
  10: feat(blocks): add WahlkreuzSymbol with colored background fill
  10: feat(blocks): add FoldLine on spot-color layer
  ... etc.
  </action>
  <verify>
  <automated>python3 -m pytest tools/sla_lib/tests/test_blocks.py -v 2>&1 | tail -30 && for t in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do python3 tools/sla_diff.py originals/$t-original.sla templates/$t/template.sla 2>&1 | tail -3 || true; done</automated>
  </verify>
  <done>
  - 6 blocks added at bottom of blocks.py with the locked signatures.
  - 18+ tests added in test_blocks.py, all passing.
  - WahlkreuzSymbol raises ValueError on background_color="Weiss" or "Gelb" (D12 enforcement).
  - Existing templates' tools/sla_diff.py round-trip remains green.
  - Six commits, one per block.
  </done>
</task>

<!-- ============================================================ -->
<!-- PHASE 3 — TEMPLATE IMPLEMENTATION (B1, B4, B5)               -->
<!-- ============================================================ -->
<!-- "Build template #1 fully (build -> smoke -> render -> codex images -> -->
<!--  Gate-3-self-review-pass) BEFORE starting #2." Iteration loop closed once  -->
<!--  on Themen-Plakat A3 (simplest, no EPS, no fold) — then templates #2-#5    -->
<!--  build on the lessons.                                                     -->

<task type="auto">
  <name>Task 11: Codex demo-image generator (tools/codex_image_gen.py)</name>
  <files>tools/codex_image_gen.py</files>
  <action>
  Build the helper that Phase 3 templates use to author per-template demo images per D11.
  This is a pure CLI wrapper around codex's image-generation CLI form. ~80 LoC.

  Inputs:
  - Path to a template's samples/manifest.yml. The manifest is YAML with structure:
    images:
      - id: kandidat-portrait
        prompt: "Photorealistic portrait of a 40s woman with short brown hair and a green blazer, friendly expression, neutral grey studio backdrop, soft front light. Headshot crop. No text overlays."
        output: kandidat-portrait.jpg
        size: 1024x1024     # optional, defaults vary by codex
      - id: gemeindestrasse
        prompt: "..."
        output: gemeindestrasse.jpg
  - --dry-run flag: prints what it would do, does not call codex.

  Behavior:
  - Parse manifest.yml.
  - For each image entry:
    * Skip if templates/SLUG/samples/ID.jpg already exists AND mtime newer than manifest.
      (idempotency — don't regenerate on every run.)
    * Otherwise, invoke codex image-generation CLI form. Use the form documented in
      ecosystem research §4.2: codex exec with image-generation prompt, output written
      via --output-last-message or by codex writing the JPG to stdout/path.
      The exact codex CLI subcommand for image generation: per Codex CLI vision capabilities
      (March-April 2026, gpt-image-2 default), the form is similar to:
        codex exec --skip-git-repo-check --json --output-image OUTPATH "PROMPT"
      Verify the exact flag name from `codex exec --help` at runtime; if the documented
      flag has changed, report the actual flag in the error message.
    * Write the JPG to the resolved output path.
    * Log: "wrote SLUG/samples/ID.jpg (NN KB)".
  - On any codex error, print the codex stderr verbatim and exit 1.
  - Auth: relies on existing codex OAuth (no env var). If codex login status is not
    "Logged in", print clear error referencing /root/.codex/auth.json.

  Brand-quality prompt guidance documented in module docstring:
  - "Photorealistic" or "documentary photo" preferred over generic terms.
  - Soft natural light or neutral studio light — never harsh shadows.
  - Greens-friendly subject types: candidates (40s+ Austrians, professional but
    approachable), event photos (community gatherings, infostand, street scenes),
    nature/sustainability (urban gardens, public transport, renewable energy
    infrastructure).
  - Always end the prompt with "No text overlays. No watermarks." to avoid model
    hallucinated logos.

  This tool is **authoring-only**. CI never runs it. Build never runs it.
  Each template's manifest+image-bytes are committed.
  </action>
  <verify>
  <automated>python3 tools/codex_image_gen.py --help && python3 tools/codex_image_gen.py --dry-run /dev/null 2>&1 | grep -qiE "manifest|input|file"</automated>
  </verify>
  <done>
  - tools/codex_image_gen.py exists.
  - --help and --dry-run paths work without invoking codex.
  - Idempotent: skips existing+newer images.
  - Module docstring documents prompt-quality conventions.
  - Commit: 10: feat(tools): add codex_image_gen for per-template demo images
  </done>
</task>

<task type="auto">
  <name>Task 12: Template — themen-plakat-a3-quer (build #1 — full lap)</name>
  <files>templates/themen-plakat-a3-quer/build.py, templates/themen-plakat-a3-quer/meta.yml, templates/themen-plakat-a3-quer/README.md, templates/_smoke/test_themen_plakat_a3_quer.py, templates/themen-plakat-a3-quer/template.sla, templates/themen-plakat-a3-quer/preview.pdf, templates/themen-plakat-a3-quer/page-01.png</files>
  <action>
  Build template #1 fully. Per the user's emphasis on "iterate often, review often",
  this template runs through build -> smoke -> render -> self-review BEFORE templates
  2-5 begin. Lessons learned here (e.g. typography rules that work at A3 scale, brand
  hierarchy patterns) propagate to subsequent templates.

  Step 12a — Author build.py:
  - Read templates/_specs/themen-plakat-a3-quer.md (Task 3) and implement EXACTLY.
  - Use Document with title, template_id, no extra layers, no spot colors (this template
    has none).
  - Use ColumnTextStory or hand-built TextFrames for the 3-column evidence grid.
  - PageBackground.for_page() factory if a colored bg is used per spec.
  - Frame annames must match spec slot annames exactly (spec_check.py will diff later).
  - Use only shared/ci.yml colors and styles. If a non-CI style is needed, add to
    meta.yml.ci_overrides.non_ci_styles with a one-line justification.
  - No EPS handling, no Wahlkreuz, no Falz, no Stanze.

  Step 12b — Author meta.yml:
  - Match templates/postkarte-a6-kampagne/meta.yml structure.
  - id: themen-plakat-a3-quer, version: 0.1.0, type: single (NOT family).
  - format: A3 quer; trim, bleed, audience per spec.
  - slots: list of every slot from the spec with type, fcolor, example.
  - example_pages: at least one entry referencing page-01.png.
  - previews_for_sla: SHA256 of template.sla (filled after build).
  - build: { entry: "build.py", produces: ["template.sla"] }.
  - No samples/ entry needed — A3 plakat has no Codex demo image.

  Step 12c — Author README.md:
  - One-page README with: title, format, when to use, what's customizable, example
    rendered preview reference (page-01.png), how to build (`python3 build.py`), printer
    recommendations, license note.

  Step 12d — Smoke test (templates/_smoke/test_themen_plakat_a3_quer.py):
  - unittest.TestCase pattern matching existing _smoke tests.
  - Imports build module, runs build to a temp file, re-parses via sla_lib.
  - Assertions:
    * Page count == 1.
    * Trim dimensions == 420 x 297 mm.
    * Bleed == 3 mm.
    * Every slot anname from meta.yml is present in the SLA.
    * No frame extends beyond trim+bleed.
    * No two frames overlap pathologically (small acceptable overlaps OK; >75%
      area overlap on different annames = fail).
    * Headline frame's apparent font size >= 36 pt.

  Step 12e — Local render:
  - Run python3 templates/themen-plakat-a3-quer/build.py to produce template.sla.
  - Run bin/render-gallery themen-plakat-a3-quer (or equivalent xvfb-run scribus +
    pdftoppm pipeline) to produce preview.pdf and page-01.png at 150 DPI committed
    artifact (existing convention in the other templates).
  - Compute SHA256(template.sla) and write into meta.yml.previews_for_sla.

  Step 12f — Self-review pass (CRITICAL — mini-Gate-3 for the calibration template):
  - Render page-01.png; place it side-by-side with the existing postkarte/plakat/zeitung
    page-01 PNGs.
  - Use tools/visual_review.py if Phase 4 has shipped it; otherwise eyeball-pass with
    explicit critique notes saved to reviews/visual-qa-themen-plakat-a3-quer-self.md.
    Critique criteria, in priority order:
    1. AT LEAST AS GOOD as plakat-a1-hochformat? Where better, where weaker?
    2. Hierarchy on first glance: 1-second-test passes?
    3. Brand-CI consistency vs the existing 3 templates?
    4. Whitespace rhythm OK at A3 distance?
  - If self-review identifies a fix, do the fix and re-render. Document before/after
    in reviews/visual-qa-themen-plakat-a3-quer-self.md.
  - This step is what makes #12 the "calibration template". The lessons end up in commit
    messages and inform Tasks 13-16.

  Commit pattern: 4-5 commits across this task (build+meta+readme; smoke test; render
  artifacts; self-review fix if applicable).
  </action>
  <verify>
  <automated>python3 templates/themen-plakat-a3-quer/build.py && python3 -m pytest templates/_smoke/test_themen_plakat_a3_quer.py -v && python3 tools/check_ci.py themen-plakat-a3-quer && bin/check-stale-previews</automated>
  </verify>
  <done>
  - All 7 file outputs exist with correct content.
  - build.py runs cleanly producing template.sla.
  - Smoke test passes.
  - check_ci.py green.
  - check-stale-previews green (SHA pin matches).
  - reviews/visual-qa-themen-plakat-a3-quer-self.md exists with at least one cycle of
    self-critique + fix.
  - Commits: feat(template): themen-plakat-a3-quer build/meta/readme; test(smoke):
    themen-plakat-a3-quer smoke test; chore(template): themen-plakat-a3-quer rendered
    artifacts; (optional) fix(template): themen-plakat-a3-quer per self-review.
  </done>
</task>

<task type="auto">
  <name>Task 13: Template — wahlaufruf-postkarte-a6-quer (build #2 — first Wahlkreuz)</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/build.py, templates/wahlaufruf-postkarte-a6-quer/meta.yml, templates/wahlaufruf-postkarte-a6-quer/README.md, templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml, templates/wahlaufruf-postkarte-a6-quer/samples/*.jpg, templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py, templates/wahlaufruf-postkarte-a6-quer/template.sla, templates/wahlaufruf-postkarte-a6-quer/preview.pdf, templates/wahlaufruf-postkarte-a6-quer/page-*.png</files>
  <action>
  First template using WahlkreuzSymbol + pack_inline_image. Implement strictly per
  templates/_specs/wahlaufruf-postkarte-a6-quer.md.

  Step 13a — build.py:
  - Document with title, template_id, 2 pages (front + back).
  - Front page:
    * PageBackground (Dunkelgruen).
    * WahlkreuzSymbol(pos=center, size=(65,65), background_color="Dunkelgruen",
      background_padding_mm=4.0). Loads shared/assets/wahlkreuz.png automatically via
      the block.
    * Headline TextFrame "Waehle Gruen am [Datum]" with Gotham Narrow Bold 24pt.
    * Logo top-left.
  - Back page:
    * White-with-Hellgruen-accent background.
    * 2x2 cell grid (4 cells), each with cell_headline + cell_body TextFrame.
    * Impressum bottom strip.
    * Logo top-left.
  - Use Anchor.from_page() factory for positioning.
  - frame annames match spec exactly (drift-checked later).

  Step 13b — meta.yml: as Task 12, plus:
  - 2 example_pages entries.
  - samples block referencing optional Codex demo image (back-side decorative photo if used).
    Slot "back_decorative_image" stays optional — template.sla works without it.

  Step 13c — README.md.

  Step 13d — Smoke test:
  - Same pattern as Task 12.
  - Specific assertions:
    * Page count == 2.
    * Front page has a Polygon fill before the Wahlkreuz ImageFrame (D12 enforcement).
    * The Polygon's fill color is "Dunkelgruen" (D12).
    * The Wahlkreuz ImageFrame's inline_image_data is non-empty and decodes to the
      shared/assets/wahlkreuz.png bytes (qCompress-decode round-trip).
    * Back page has 4 cell-headline frames and 4 cell-body frames (2x2 grid).
    * Impressum frame present.
    * No text frame extends beyond trim+bleed.

  Step 13e — Codex demo image (D11):
  - templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml lists 1 demo image
    (e.g. back-side decorative element). Prompt example: a documentary photo of a
    community gathering / infostand, not text.
  - Run tools/codex_image_gen.py against the manifest.
  - Resulting JPG committed under samples/.
  - The "preview SLA" used for gallery_build.py rendering injects the demo image into
    the optional slot — use a separate template-preview.sla generated alongside if
    needed (per D11). For this template the back side has no required image slot, so
    the demo image is purely decorative; you may either inject into a preview SLA or
    skip if the back side already looks polished without it. Document the decision.

  Step 13f — Local render + commit artifacts.
  Step 13g — Self-review (mini-Gate-3 again, but lighter than #12):
  - Render side-by-side with postkarte-a6-kampagne (existing) and themen-plakat-a3-quer
    (Task 12).
  - Specifically check D12 compliance: is the Wahlkreuz visibly on a colored band,
    not on white?
  - reviews/visual-qa-wahlaufruf-postkarte-a6-quer-self.md.
  - Iterate once if needed.

  Crucial: this is the first template that exercises pack_inline_image + WahlkreuzSymbol
  + D12. If anything fails to open in Scribus headless (qUncompress error), the helper
  is wrong — fix Task 9 before continuing.
  </action>
  <verify>
  <automated>python3 templates/wahlaufruf-postkarte-a6-quer/build.py && xvfb-run -a scribus -g -ns -py /dev/null templates/wahlaufruf-postkarte-a6-quer/template.sla 2>&1 | grep -qiE "qUncompress|Z_DATA_ERROR|PoDoFo error" && echo "FAIL: SLA has decode error" && exit 1 || true; python3 -m pytest templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py -v && python3 tools/check_ci.py wahlaufruf-postkarte-a6-quer && bin/check-stale-previews</automated>
  </verify>
  <done>
  - All file outputs exist.
  - SLA opens cleanly in headless Scribus (no qUncompress error).
  - WahlkreuzSymbol Polygon fill present and on Dunkelgruen.
  - Smoke test asserts D12 compliance.
  - Codex demo image generated (or decision documented to skip).
  - Self-review markdown exists.
  - 4-5 commits per the same pattern as Task 12.
  </done>
</task>

<task type="auto">
  <name>Task 14: Template — wahltag-tueranhaenger (build #3 — Stanzkontur + Wahlkreuz)</name>
  <files>templates/wahltag-tueranhaenger/build.py, templates/wahltag-tueranhaenger/meta.yml, templates/wahltag-tueranhaenger/README.md, templates/wahltag-tueranhaenger/samples/manifest.yml, templates/wahltag-tueranhaenger/samples/*.jpg, templates/_smoke/test_wahltag_tueranhaenger.py, templates/wahltag-tueranhaenger/template.sla, templates/wahltag-tueranhaenger/preview.pdf, templates/wahltag-tueranhaenger/page-*.png</files>
  <action>
  First template using DieCut + DoorHangerCutout. Implement strictly per
  templates/_specs/wahltag-tueranhaenger.md.

  Step 14a — build.py:
  - Document with explicit layers list:
    layers=[
      DocumentLayer(name="Hintergrund", printable=True, flow=True),
      DocumentLayer(name="Bilder", printable=True, flow=True),
      DocumentLayer(name="Text", printable=True, flow=True),
      DocumentLayer(name="Stanzkontur", printable=False, flow=False),
    ]
  - doc.add_color("Stanzkontur", cmyk=(0,100,0,0), spot=True) — DOCUMENT-LOCAL per D4 revised.
  - Two pages (front + optional back), 105 x 250 mm trim, 2 mm bleed.
  - DoorHangerCutout(page_size_mm=(105,250), hole_diameter_mm=35, hole_top_offset_mm=25)
    — emits the DieCut on Stanzkontur layer.
  - Front: brand bar with logo (top), Wahlkreuz hero (mid-upper) on Hellgruen band,
    headline "Waehle Gruen", bullets, Impressum.
  - Back: optional photo slot (Codex demo), CTA, Impressum.
  - Frame annames match spec.

  Step 14b — meta.yml:
  - ci_overrides:
      non_ci_colors: ["Stanzkontur"]   # justified: print-required spot color, document-local
      non_ci_layers: ["Stanzkontur"]
  - samples block referencing 1 Codex demo image (back-side photo).

  Step 14c — README.md mentioning print-shop spot-color naming alternatives
  (Stanzkontur vs CutContour) per spec.

  Step 14d — Smoke test:
  - Page count 2.
  - Trim 105 x 250.
  - Stanzkontur color present in SLA (xmllint check).
  - Stanzkontur layer present with DRUCKEN=0.
  - DieCut Polygon present on Stanzkontur layer with >=40 path points (rectangle + 36-segment circle).
  - WahlkreuzSymbol Polygon fill on a colored brand color (D12).
  - Layer stack order: Stanzkontur is the topmost layer (highest LEVEL).
  - Round-trip safety: existing 3 templates still pass tools/sla_diff.py.

  Step 14e — Codex demo image generation per D11.
  Step 14f — Local render + commit artifacts.
  Step 14g — Self-review with side-by-side (3 existing + 2 new now in scope: postkarte
  a6-kampagne, themen-plakat, wahlaufruf-postkarte-a6-quer + wahltag-tueranhaenger).
  Iterate once if needed.

  Crucial: this is the first template with a non-default layer stack and document-local
  spot color. The round-trip safety check is non-negotiable (P-CI-4).
  </action>
  <verify>
  <automated>python3 templates/wahltag-tueranhaenger/build.py && python3 -m pytest templates/_smoke/test_wahltag_tueranhaenger.py -v && python3 tools/check_ci.py wahltag-tueranhaenger && for t in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do python3 tools/sla_diff.py originals/$t-original.sla templates/$t/template.sla 2>&1 | tail -2; done && bin/check-stale-previews</automated>
  </verify>
  <done>
  - All outputs exist.
  - Stanzkontur layer + spot color document-local (NOT in shared/ci.yml).
  - DieCut path includes outer rectangle + circular hole.
  - Wahlkreuz on colored band (D12).
  - Existing templates' round-trip diff still green.
  - Self-review markdown exists.
  - 4-5 commits.
  </done>
</task>

<task type="auto">
  <name>Task 15: Template — infostand-tent-card-a5-quer (build #4 — TableTentFold)</name>
  <files>templates/infostand-tent-card-a5-quer/build.py, templates/infostand-tent-card-a5-quer/meta.yml, templates/infostand-tent-card-a5-quer/README.md, templates/infostand-tent-card-a5-quer/samples/manifest.yml, templates/infostand-tent-card-a5-quer/samples/*.jpg, templates/_smoke/test_infostand_tent_card_a5_quer.py, templates/infostand-tent-card-a5-quer/template.sla, templates/infostand-tent-card-a5-quer/preview.pdf, templates/infostand-tent-card-a5-quer/page-01.png</files>
  <action>
  First template using TableTentFold. Implement strictly per
  templates/_specs/infostand-tent-card-a5-quer.md.

  Step 15a — build.py:
  - Document with layers including Falz:
    layers=[
      DocumentLayer(name="Hintergrund", printable=True, flow=True),
      DocumentLayer(name="Bilder", printable=True, flow=True),
      DocumentLayer(name="Text", printable=True, flow=True),
      DocumentLayer(name="Falz", printable=False, flow=False),
    ]
  - doc.add_color("Falz", cmyk=(100,0,0,0), spot=True) document-local.
  - One page, 297 x 210 mm trim, 3 mm bleed.
  - TableTentFold(page_size_mm=(297,210)) — emits horizontal FoldLine at y=105.
  - Two visual zones (panel A above fold, panel B below fold): each with headline, body,
    optional image, logo. Mirror the layout so when folded, both sides face up
    correctly.
  - Bottom 3 mm of each panel is empty (table-contact zone — P-PRINT-4).
  - frame annames match spec.

  Step 15b — meta.yml: ci_overrides: non_ci_colors:["Falz"], non_ci_layers:["Falz"].
  Step 15c — README.md noting paper weight recommendation 250-300 g/m^2 for rigidity.
  Step 15d — Smoke test:
  - Trim 297 x 210, page count 1, FoldLine Polygon present at y=105 spanning full width.
  - Falz layer with DRUCKEN=0.
  - Falz spot color document-local present.
  - Bottom 3 mm of each panel has no text frames overlapping.
  - Headline >= 28 pt, body >= 14 pt.

  Step 15e — Codex demo image (1 image per panel, optional) per D11.
  Step 15f — Local render + commit artifacts.
  Step 15g — Self-review side-by-side with all prior templates.
  </action>
  <verify>
  <automated>python3 templates/infostand-tent-card-a5-quer/build.py && python3 -m pytest templates/_smoke/test_infostand_tent_card_a5_quer.py -v && python3 tools/check_ci.py infostand-tent-card-a5-quer && bin/check-stale-previews</automated>
  </verify>
  <done>
  - All outputs exist.
  - Falz layer + spot color document-local.
  - FoldLine at y=105 mm horizontal.
  - Bottom 3 mm contact zones clear.
  - Self-review markdown exists.
  - 4-5 commits.
  </done>
</task>

<task type="auto">
  <name>Task 16: Template — kandidat-falzflyer-din-lang (build #5 — most complex)</name>
  <files>templates/kandidat-falzflyer-din-lang/build.py, templates/kandidat-falzflyer-din-lang/meta.yml, templates/kandidat-falzflyer-din-lang/README.md, templates/kandidat-falzflyer-din-lang/samples/manifest.yml, templates/kandidat-falzflyer-din-lang/samples/*.jpg, templates/_smoke/test_kandidat_falzflyer_din_lang.py, templates/kandidat-falzflyer-din-lang/template.sla, templates/kandidat-falzflyer-din-lang/preview.pdf, templates/kandidat-falzflyer-din-lang/page-*.png</files>
  <action>
  Most complex template: 6 panels, FoldedPanel + FoldLine + WahlkreuzSymbol on closer panel.
  Implement strictly per templates/_specs/kandidat-falzflyer-din-lang.md.

  Step 16a — build.py:
  - Document with layers including Falz (as Task 15).
  - 2 pages (front + back), each 297 x 210 mm. Bleed 3 mm.
  - For each side: 3 FoldedPanel instances (panel_index 0/1/2, panel_count=3,
    panel_size_mm=(99,210)). FoldedPanel emits FoldLines automatically on the right
    edge of panels 0 and 1 (panel 2 has has_fold_right=False).
  - Front panel 1 (cover): kandidat portrait + name + slogan.
  - Front panel 2: teaser headline + body + small logo.
  - Front panel 3 (closer): WahlkreuzSymbol on Dunkelgruen band, headline "Waehle Gruen",
    date.
  - Back panels 4, 5, 6: 4 themen, contact, qr, impressum (per spec).
  - Frame annames match spec exactly.

  Step 16b — meta.yml: ci_overrides for Falz.
  Step 16c — README.md noting Zickzackfalz, paper recommendation.
  Step 16d — Smoke test:
  - 2 pages, each 297 x 210.
  - 4 FoldLines total (2 per side at x=99 and x=198).
  - Wahlkreuz on closer panel with Dunkelgruen background polygon (D12).
  - 18+ slot annames present matching spec.
  - Per-panel content stays inside 99 mm minus 3 mm safety = 93 mm width.
  - Round-trip safety: existing 3 templates still green.

  Step 16e — Codex demo images: 2-3 (kandidat portrait, optional thema-photo per panel)
  per D11.
  Step 16f — Local render + commit artifacts (page-01.png front, page-02.png back).
  Step 16g — Self-review side-by-side with all prior templates.

  This is the last new template. After this, all 8 templates exist (3 existing + 5 new)
  ready for Gate 2.
  </action>
  <verify>
  <automated>python3 templates/kandidat-falzflyer-din-lang/build.py && python3 -m pytest templates/_smoke/test_kandidat_falzflyer_din_lang.py -v && python3 tools/check_ci.py kandidat-falzflyer-din-lang && for t in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do python3 tools/sla_diff.py originals/$t-original.sla templates/$t/template.sla 2>&1 | tail -2; done && bin/check-stale-previews</automated>
  </verify>
  <done>
  - All outputs exist.
  - 4 fold lines (2 per side).
  - Wahlkreuz on Dunkelgruen on closer panel.
  - 18+ slot annames present.
  - Round-trip safety green.
  - Self-review markdown exists.
  - 4-5 commits.
  </done>
</task>

<task type="auto">
  <name>Task 17: Gallery build pre-flight (all 8 templates)</name>
  <files>(no new files; verifies tools/gallery_build.py emits 8 templates)</files>
  <action>
  Run tools/gallery_build.py and confirm it picks up all 5 new templates (matching the
  3 existing) without code changes — the existing pipeline already globs templates/SLUG/
  for meta.yml + previews. New templates inherit for free.

  Steps:
  - Run python3 tools/gallery_build.py (it reads templates/, copies artifacts to
    site/public/templates/SLUG/, writes site/src/content/templates/SLUG.md).
  - Verify site/public/templates/ has 8 directories (3 existing + 5 new).
  - Verify each new template has a frontmatter file in site/src/content/templates/.
  - If any template fails (e.g. permission collision, schema mismatch in
    site/src/content.config.ts due to a missing key), debug:
    * If schema is too strict (e.g. requires a key not in new meta.yml), the right
      fix is to extend meta.yml with the missing key, not to relax the schema.
    * If a glob pattern misses the new template, that's a bug in gallery_build.py —
      fix and document.
  - Smoke-build the Astro site locally (cd site && npm run build) to confirm no
    schema errors.

  No commits expected unless a fix is needed.
  </action>
  <verify>
  <automated>python3 tools/gallery_build.py && ls site/public/templates/ | sort | wc -l | grep -qE "^8$" && ls site/src/content/templates/ | wc -l</automated>
  </verify>
  <done>
  - gallery_build.py emits 8 templates without modification.
  - Astro build succeeds locally.
  - If a fix was needed, single-line commit "10: fix(gallery): explain the fix"
  </done>
</task>

<!-- ============================================================ -->
<!-- GATE 2 — CODE / BUILD REVIEW                                 -->
<!-- ============================================================ -->

<task type="auto" review="gate-2">
  <name>Task 18: Gate 2 — Code/Build Review (Multi-Model)</name>
  <files>reviews/code-review-1.md, (potentially) reviews/code-review-2.md, fixes across DSL + templates</files>
  <action>
  Run /issue:review skill orchestration over the DSL changes (Tasks 9-10) + the 5 template
  builds (Tasks 12-16) + smoke tests. Reviewers (Claude + Codex + Gemini) read the code
  themselves — do NOT include diffs in the prompt (per memory rule
  feedback_review_no_code_in_prompt).

  Reviewer prompt MUST stress (verbatim, in this order):
  1. **VISUAL QUALITY OVER CODE-ELEGANCE.** Does the rendered output of each new template
     achieve at-least-as-good-as the existing 3? Reviewers must read build.py AND read
     the rendered preview-PDF/PNG.
  2. DSL patterns consistent with the 3 existing templates' build.py?
  3. New blocks (WahlkreuzSymbol, FoldLine, DieCut, FoldedPanel, DoorHangerCutout,
     TableTentFold) reusable, with sensible API boundaries?
  4. Each template's implementation matches its spec (Tasks 3-7) slot-for-slot?
  5. Is anything missing that undermines visual quality (e.g. bleed, default spacing,
     alignment bugs, frame collisions, tight whitespace, font hierarchy off)?
  6. Wahlkreuz templates: D12 background-color contract enforced (no Wahlkreuz on
     Weiss or Gelb)?
  7. Round-trip diff of existing 3 templates still green?
  8. pack_inline_image: correct qCompress format, used everywhere needed?
  9. Smoke tests substantive enough to catch regressions, not just smoke?

  Reviewer output: structured Markdown per template + per-DSL-change. Output to
  reviews/code-review-1.md.

  Process:
  - Run /issue:review with the relevant file paths.
  - Save outputs.
  - Address every blocking finding via fix commits (10: fix(scope): explain).
  - Run a second round if any reviewer says merge_ready=no after Round 1
    (reviews/code-review-2.md). Cap at 3 rounds.

  Quality emphasis: The user wants iteration. Plan for at least one round of fixes
  here — first-pass merge-ready is unlikely with 5 new templates.

  Do NOT begin Phase 4 (visual-QA tooling) until Gate 2 reaches consensus.

  NOTE: Phase 4's visual_review.py and spec_check.py are USED in Gate 3 but not yet
  built. Gate 2 is purely about code + spec-conformance, not rendered visuals
  (those are Gate 3's job). However Gate 2 reviewers should ALSO open the
  preview PNGs to do an early-pass visual sanity check; full visual rigour is Gate 3.
  </action>
  <verify>
  <automated>test -f reviews/code-review-1.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/code-review-1.md && grep -qE "claude|codex|gemini" reviews/code-review-1.md</automated>
  </verify>
  <done>
  - reviews/code-review-1.md exists with all three reviewer sections.
  - Blocking findings addressed (commits) or rejected with justification.
  - Final consensus state recorded.
  - At least 1 iteration attempted.
  - Commit: 10: chore(review): record gate-2 code-review consensus
  </done>
</task>

<!-- ============================================================ -->
<!-- PHASE 4 — VISUAL-QA PIPELINE TOOLING (C1, C2)                -->
<!-- ============================================================ -->

<task type="auto" tdd="true">
  <name>Task 19: tools/spec_check.py (drift detector)</name>
  <files>tools/spec_check.py, tools/sla_lib/tests/test_spec_check.py</files>
  <action>
  Mechanical drift detector per CONTEXT.md D3 + P-SPEC-1. Reads a spec file
  (templates/_specs/SLUG.md), parses the embedded YAML slot table, opens
  templates/SLUG/template.sla, reads PAGEOBJECT entries, diffs each slot's coordinates
  against the spec.

  CLI: tools/spec_check.py SLUG  (default exits 0 on match, 1 on drift)
       tools/spec_check.py --all (checks every spec under templates/_specs/, summary)
       tools/spec_check.py --tolerance-mm 0.1 (default 0.1, configurable)

  Behavior:
  - For each slot in spec: find PAGEOBJECT with matching ANNAME in the SLA.
  - Compare x_mm, y_mm, w_mm, h_mm with tolerance (default 0.1 mm).
  - Compare fcolor (PAGEOBJECT FCOLOR attribute) with spec.
  - If a slot is in spec but missing in SLA: drift (anname_missing).
  - If a slot is in SLA (with non-internal anname) but not in spec: drift (anname_extra).
  - SLA frames whose anname starts with "internal:" or "_" are skipped (escape hatch
    for DSL-internal frames the spec intentionally omits — per P-SPEC-3).
  - Output:
    * On match: "OK: SLUG (N slots, all match within Xmm)"
    * On drift: structured Markdown report listing each drift with line numbers from
      both sources. Exit 1.
  - --report PATH writes the report to a file (used by Gate 3 review aggregation).

  Skip retro-spec files (those starting with `_existing-`) — those validate the schema,
  not the build.

  TDD:
  - RED tests:
    * Spec slot matches SLA exactly: returns OK.
    * Spec slot x_mm differs by 0.05 mm: returns OK (within tolerance).
    * Spec slot x_mm differs by 0.5 mm: returns drift.
    * Slot in spec missing in SLA: drift (anname_missing).
    * Slot in SLA missing in spec: drift (anname_extra).
    * Anname starting with "internal:" in SLA: ignored.
    * --all summarizes across all 5 new templates.
  - GREEN: implement.
  - Use lxml.etree (already in deps) to parse SLA, PyYAML to parse the YAML block from
    the spec markdown.

  This tool is RUN in Gate 3 and (optionally) wired into bin/validate. Don't add to
  CI workflow yet — Phase 5 ship task decides.
  </action>
  <verify>
  <automated>python3 -m pytest tools/sla_lib/tests/test_spec_check.py -v && python3 tools/spec_check.py --all 2>&1 | tail -10</automated>
  </verify>
  <done>
  - tools/spec_check.py exists, --help works, --all works.
  - 7+ tests pass.
  - Running --all on the 5 new templates passes (specs and templates already aligned by Gate 2).
  - Internal-prefix anname escape hatch documented in module docstring.
  - Commit: 10: feat(tools): add spec_check for spec-vs-build drift detection
  </done>
</task>

<task type="auto">
  <name>Task 20: tools/visual_review.py (multi-model orchestrator)</name>
  <files>tools/visual_review.py, tools/visual_review/prompt_template.md</files>
  <action>
  Multi-model vision review orchestrator per CONTEXT.md D5 + D6 + D7. Local-only by
  design (P-VISION-2 — no CI auth).

  CLI:
    tools/visual_review.py SLUG [--iter N] [--out reviews/]
    tools/visual_review.py --all [--out reviews/]

  Behavior:
  1. Resolve target template's preview PNG (templates/SLUG/page-01.png). For multi-page
     templates use page-01 as the hero; optionally include all pages.
  2. Build a side-by-side composite of all 8 templates (3 existing + 5 new) labeled,
     using ImageMagick `montage` (NOT Pillow) per D7 revised. Pattern verbatim from
     tools/visual_diff.py:188-195. Output: reviews/all-templates-grid.png.
  3. Downscale the SLUG's hero PNG to 1024 px long edge (also via ImageMagick `convert`
     -resize 1024x1024 -strip), output reviews/visual-qa-SLUG-detail.png.
  4. Read tools/visual_review/prompt_template.md (see content below).
  5. Send {detail_image, grid_image, prompt} to all three models in parallel:
     - Claude Vision: anthropic Python SDK if available; else `claude` CLI; else mark
       unavailable.
     - Codex: `codex exec --image DETAIL --image GRID --json --skip-git-repo-check
       --output-last-message OUTFILE` (per RESEARCH ecosystem §4.2). Pass the prompt
       via stdin or argv.
     - Gemini: `gemini -p "PROMPT @DETAIL @GRID" -o json --yolo` (per ecosystem §4.3).
  6. Parse each model's structured output (JSON if available, else markdown).
  7. Write reviews/visual-qa-SLUG-iter-N.md aggregating all three model outputs with
     sections per model + a consensus summary section. Track:
     - merge_ready per model (yes/no/unclear).
     - blocking_findings (deduped, with source-model attribution).
     - nice_to_have (deduped).
     - One-sentence overall verdict.
  8. If --iter > 1, the file is suffixed -iter-2, -iter-3, etc.

  Prompt template (tools/visual_review/prompt_template.md, ~80 lines):
  - First sentence: "VISUAL QUALITY IS THE PRIMARY CRITERION."
  - Question 1, in priority order:
    "Compared to the 3 existing templates (Postkarte, Plakat, Zeitung) shown in the grid,
     is this NEW template AT LEAST AS GOOD visually? Where is it better, where weaker?"
  - Question 2: 1-second-test — what is the main message at first glance?
  - Question 3: brand consistency (Greens-CI, not generic).
  - Question 4: print risks (text near trim, missing bleed, contrast, frame collisions,
    whitespace rhythm).
  - Question 5: Wahlkreuz background-color (D12) — must be on a colored band, never
    on white or yellow. If white-or-yellow background visible, it's BLOCKING.
  - Question 6: 3 concrete improvements with rationale.
  - Output: strict JSON, schema:
    {
      "merge_ready": "yes|no|unclear",
      "comparison_to_existing": "<paragraph>",
      "hierarchy_readability": "<paragraph>",
      "brand_consistency": "<paragraph>",
      "print_risks": ["..."],
      "blocking_findings": ["..."],
      "nice_to_have": ["..."],
      "wahlkreuz_background_color_check": "pass|fail|n/a"
    }
  - Reviewer must cite SPECIFIC COORDINATES or REGIONS for findings, not vague terms
    (per P-VISION-4 — coordinate-cited findings reduce hallucination).

  Auth:
  - Claude: ANTHROPIC_API_KEY env var OR live agent context.
  - Codex: codex login OAuth (cached at /root/.codex/auth.json — verified by RESEARCH).
  - Gemini: gemini OAuth at /root/.gemini/oauth_creds.json — auto-refresh on first call.
  - If any model is unavailable, run with the available subset and note in the report:
    "MODEL_X unavailable (auth/CLI), proceeding with N/3 reviewers".

  Implementation: ~250-350 LoC. Uses subprocess for codex/gemini, anthropic SDK or
  claude CLI for Claude. No Pillow.

  Tests:
  - Mock subprocess calls; assert correct CLI invocation per model.
  - Assert composite generation invokes montage with correct flags.
  - Assert detail-image downscale correct.
  - Assert report file structure matches expected schema.
  </action>
  <verify>
  <automated>test -f tools/visual_review/prompt_template.md && python3 tools/visual_review.py --help && python3 -m pytest tools/sla_lib/tests/test_visual_review.py -v 2>&1 | tail -10</automated>
  </verify>
  <done>
  - tools/visual_review.py + tools/visual_review/prompt_template.md exist.
  - --help works.
  - Mock-based tests pass.
  - Prompt template stresses visual quality FIRST, lists D12 check, requires
    coordinate-cited findings.
  - Tool gracefully handles missing model auth.
  - Commit: 10: feat(tools): add visual_review.py multi-model orchestrator
  </done>
</task>

<!-- ============================================================ -->
<!-- GATE 3 — VISUAL RENDER REVIEW (THE BIG ONE)                  -->
<!-- ============================================================ -->
<!-- "Iteration is EXPECTED. Plan for at least 2 iterations per template by default." -->
<!-- Each template gets up to 3 iterations: review -> fix -> re-review.               -->

<task type="auto" review="gate-3-template-1">
  <name>Task 21: Gate 3 — themen-plakat-a3-quer iteration loop</name>
  <files>reviews/visual-qa-themen-plakat-a3-quer.md, reviews/visual-qa-themen-plakat-a3-quer-iter-1.md, reviews/visual-qa-themen-plakat-a3-quer-iter-2.md, reviews/visual-qa-themen-plakat-a3-quer-iter-3.md (as needed), templates/themen-plakat-a3-quer/build.py + page-*.png (fixes)</files>
  <action>
  Per-template iteration block. Cap at 3 iterations. Stop early on unanimous merge_ready.

  Iteration 1 (review-only):
  - Run python3 tools/visual_review.py themen-plakat-a3-quer.
  - Output: reviews/visual-qa-themen-plakat-a3-quer-iter-1.md.
  - Read all three model verdicts.
  - If 3/3 merge_ready=yes, document, copy to reviews/visual-qa-themen-plakat-a3-quer.md
    (canonical), and SKIP iterations 2-3.

  Iteration 2 (fix + re-review):
  - For every blocking_finding from iteration 1: fix in build.py.
  - Re-render template.sla, preview.pdf, page-*.png.
  - Re-run check_ci, smoke test, check-stale-previews.
  - Run python3 tools/visual_review.py themen-plakat-a3-quer.
  - Output: reviews/visual-qa-themen-plakat-a3-quer-iter-2.md, with explicit
    "vorher/nachher" section comparing iter-1 to iter-2 page-01.png.
  - If 3/3 merge_ready=yes, copy to canonical reviews/visual-qa-themen-plakat-a3-quer.md
    and STOP.

  Iteration 3 (final fix + re-review):
  - As iteration 2.
  - If still not 3/3 merge_ready=yes after iter-3, escalate to human-override per D6.
    Document the escalation reason in the report.

  Critically — visual quality emphasis:
  - "first-pass merge-ready is unlikely; plan for at least 2 iterations per template"
    per the user's quality emphasis.
  - "Polish loop carved out separately from build loop" — Tasks 12-16 closed the build
    loop; Tasks 21-25 close the polish loop.
  - "Should look at least as good as previous templates, or even better, to impress
    other teams" — the canonical visual-qa-SLUG.md MUST contain a paragraph explicitly
    answering "Where is this NEW template better than the existing 3?" with specific
    references to the rendered preview.

  Anti-spiral hygiene per P-VISION-4:
  - Track findings per iteration; if iteration N introduces a new "blocking_finding"
    that contradicts iteration N-1's fix, document the contradiction. Don't blindly
    bounce back-and-forth.
  - If only 1/3 model says blocking, treat as advisory not blocking (per P-VISION-4).
  - Brand-relative interpretation per P-VISION-5: "this looks generic" is not
    actionable; "this lacks the magenta/dunkelgruen contrast that the existing Plakat
    has at top-corner" is actionable.

  Output: reviews/visual-qa-themen-plakat-a3-quer.md is the canonical merge-gate
  artifact per template.
  </action>
  <verify>
  <automated>test -f reviews/visual-qa-themen-plakat-a3-quer.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/visual-qa-themen-plakat-a3-quer.md && grep -qiE "where.*better|better.*than" reviews/visual-qa-themen-plakat-a3-quer.md && python3 templates/themen-plakat-a3-quer/build.py && python3 -m pytest templates/_smoke/test_themen_plakat_a3_quer.py -v && bin/check-stale-previews</automated>
  </verify>
  <done>
  - At least one iteration ran (iter-1.md exists).
  - If multiple iterations: vorher/nachher section in each iter-N.md.
  - Canonical reviews/visual-qa-themen-plakat-a3-quer.md exists.
  - Final state: 3/3 merge_ready=yes OR documented human-override.
  - "Where it's better" paragraph present.
  - Build still green after fixes; smoke test passes; check-stale-previews passes.
  - Commits: per fix commit + final "10: chore(review): record gate-3
    themen-plakat-a3-quer consensus"
  </done>
</task>

<task type="auto" review="gate-3-template-2">
  <name>Task 22: Gate 3 — wahlaufruf-postkarte-a6-quer iteration loop</name>
  <files>reviews/visual-qa-wahlaufruf-postkarte-a6-quer.md, reviews/visual-qa-wahlaufruf-postkarte-a6-quer-iter-*.md, templates/wahlaufruf-postkarte-a6-quer/build.py + page-*.png (fixes)</files>
  <action>
  Same iteration structure as Task 21 (iter-1 review, iter-2 fix+review, iter-3
  fix+review, cap at 3, stop on unanimous).

  Template-specific Gate-3 emphasis:
  - D12 enforcement: visual-review prompt explicitly checks "Is the Wahlkreuz on a
    colored band (Dunkelgruen / Hellgruen / Magenta), NOT on Weiss or Gelb?". A "fail"
    on this check is BLOCKING regardless of other consensus.
  - Front-vs-back hierarchy: front is symbol-zentriert; back is info-grid. Both must
    pass independent 1-second-tests.
  - 2x2 grid spacing on back: cells must not feel cramped (P-A6QUER-1).
  - Headline >= 22 pt enforcement (P-PRINT-5).
  </action>
  <verify>
  <automated>test -f reviews/visual-qa-wahlaufruf-postkarte-a6-quer.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/visual-qa-wahlaufruf-postkarte-a6-quer.md && grep -qiE "wahlkreuz|background" reviews/visual-qa-wahlaufruf-postkarte-a6-quer.md && python3 templates/wahlaufruf-postkarte-a6-quer/build.py && python3 -m pytest templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py -v && bin/check-stale-previews</automated>
  </verify>
  <done>
  - Same as Task 21 plus D12 background-color check explicit pass.
  - Front and back both pass 1-second-test verdict in the canonical report.
  </done>
</task>

<task type="auto" review="gate-3-template-3">
  <name>Task 23: Gate 3 — wahltag-tueranhaenger iteration loop</name>
  <files>reviews/visual-qa-wahltag-tueranhaenger.md, reviews/visual-qa-wahltag-tueranhaenger-iter-*.md, templates/wahltag-tueranhaenger/build.py + page-*.png (fixes)</files>
  <action>
  Same iteration structure as Task 21.

  Template-specific Gate-3 emphasis:
  - D12 Wahlkreuz background-color check.
  - Stanzkontur visibility in preview PNG: the Stanzkontur layer is NOT printable but
    IS exportable, so it appears in the rendered preview as a thin spot-color line —
    confirm it's visible, on top, and traces the expected outline + 35 mm hole.
  - Hole position: 25 mm from top, centered horizontally — visible in rendered PNG.
  - 2 mm bleed safety: no text within 2 mm of any Stanzkontur edge.
  - Layer stack visual order: Stanzkontur on top, brand colors below.
  </action>
  <verify>
  <automated>test -f reviews/visual-qa-wahltag-tueranhaenger.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/visual-qa-wahltag-tueranhaenger.md && grep -qiE "stanzkontur|hole" reviews/visual-qa-wahltag-tueranhaenger.md && python3 templates/wahltag-tueranhaenger/build.py && python3 -m pytest templates/_smoke/test_wahltag_tueranhaenger.py -v && bin/check-stale-previews</automated>
  </verify>
  <done>
  - Same as Task 21 plus Stanzkontur visibility + hole position pass.
  </done>
</task>

<task type="auto" review="gate-3-template-4">
  <name>Task 24: Gate 3 — infostand-tent-card-a5-quer iteration loop</name>
  <files>reviews/visual-qa-infostand-tent-card-a5-quer.md, reviews/visual-qa-infostand-tent-card-a5-quer-iter-*.md, templates/infostand-tent-card-a5-quer/build.py + page-*.png (fixes)</files>
  <action>
  Same iteration structure as Task 21.

  Template-specific Gate-3 emphasis:
  - Fold line visible at y=105 mm in preview PNG.
  - Both panels read independently — flip the rendered PNG vertically (mental model)
    and check that text on each side is readable.
  - Bottom 3 mm of each panel is empty (no text near table-contact zone).
  - Headline >= 28 pt readable at table-eye distance.
  </action>
  <verify>
  <automated>test -f reviews/visual-qa-infostand-tent-card-a5-quer.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/visual-qa-infostand-tent-card-a5-quer.md && python3 templates/infostand-tent-card-a5-quer/build.py && python3 -m pytest templates/_smoke/test_infostand_tent_card_a5_quer.py -v && bin/check-stale-previews</automated>
  </verify>
  <done>
  - Same as Task 21 plus fold-line visibility + bottom-zone clearance pass.
  </done>
</task>

<task type="auto" review="gate-3-template-5">
  <name>Task 25: Gate 3 — kandidat-falzflyer-din-lang iteration loop</name>
  <files>reviews/visual-qa-kandidat-falzflyer-din-lang.md, reviews/visual-qa-kandidat-falzflyer-din-lang-iter-*.md, templates/kandidat-falzflyer-din-lang/build.py + page-*.png (fixes)</files>
  <action>
  Same iteration structure as Task 21.

  Template-specific Gate-3 emphasis (most-complex template, most prone to issues):
  - All 4 fold lines visible (2 per side at x=99 and x=198).
  - Each panel content stays within 93 mm safe width.
  - D12: Wahlkreuz on Dunkelgruen on closer panel.
  - Reading order: cover (panel 1) hooks, partial-open (panel 2) teases, full-open
    (panels 4-6) delivers, closing (panel 3) acts.
  - 18+ slot annames present and matching spec.
  - Per-panel hierarchy >= 16 pt headline, 9 pt body.
  </action>
  <verify>
  <automated>test -f reviews/visual-qa-kandidat-falzflyer-din-lang.md && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/visual-qa-kandidat-falzflyer-din-lang.md && python3 templates/kandidat-falzflyer-din-lang/build.py && python3 -m pytest templates/_smoke/test_kandidat_falzflyer_din_lang.py -v && bin/check-stale-previews</automated>
  </verify>
  <done>
  - Same as Task 21 plus 4 fold lines visible + reading-order verdict pass.
  </done>
</task>

<task type="auto" review="gate-3-summary">
  <name>Task 26: Gate 3 — Aggregate summary report (all 8 templates)</name>
  <files>reviews/visual-qa-summary.md, reviews/all-templates-grid.png</files>
  <action>
  Produce the gesamt-report aggregating Gate 3 outcomes per template.

  Content of reviews/visual-qa-summary.md:
  - Generated date.
  - Overview: 8 templates (3 existing + 5 new) ship-readiness verdict.
  - For each new template: link to canonical reviews/visual-qa-SLUG.md, final
    merge_ready state (3/3 yes / human-override / pending), iterations consumed
    (1 / 2 / 3), key visual improvement vs the existing 3 (one sentence).
  - Embed reviews/all-templates-grid.png (already produced by visual_review.py during
    Tasks 21-25; re-run montage on the latest 8 page-01.png files if older versions
    are stale).
  - Side-by-side table:
    | Template | Format | Iterations | Merge-Ready | Better-Than note |
    |----------|--------|------------|-------------|------------------|
    | postkarte-a6-kampagne | A6 hoch | (existing baseline) | n/a | reference |
    | plakat-a1-hochformat | A1 hoch | (existing baseline) | n/a | reference |
    | zeitung-a4-grun | A4 newspaper | (existing baseline) | n/a | reference |
    | themen-plakat-a3-quer | A3 quer | N | yes/override | "..." |
    | wahlaufruf-postkarte-a6-quer | A6 quer | N | yes/override | "..." |
    | wahltag-tueranhaenger | 105x250 | N | yes/override | "..." |
    | infostand-tent-card-a5-quer | A4 quer tent | N | yes/override | "..." |
    | kandidat-falzflyer-din-lang | A4 quer 3-fold | N | yes/override | "..." |
  - Explicit recommendation paragraph: "merge-ready" for the entire batch, OR list of
    blockers if any template still pending.

  This is the artifact the PR description embeds in Phase 5.
  </action>
  <verify>
  <automated>test -f reviews/visual-qa-summary.md && test -f reviews/all-templates-grid.png && grep -qiE "merge.ready|merge-ready|merge_ready" reviews/visual-qa-summary.md && python3 -c "lines=open('reviews/visual-qa-summary.md').read().splitlines(); count=sum(1 for l in lines if 'themen-plakat-a3-quer' in l or 'wahlaufruf-postkarte-a6-quer' in l or 'wahltag-tueranhaenger' in l or 'infostand-tent-card-a5-quer' in l or 'kandidat-falzflyer-din-lang' in l); assert count >= 5, f'expected 5+ template refs, found {count}'"</automated>
  </verify>
  <done>
  - reviews/visual-qa-summary.md exists with side-by-side table for all 8.
  - reviews/all-templates-grid.png exists (current versions of all 8 page-01s).
  - "merge-ready" explicit recommendation present.
  - Each new template's "better than the existing 3" sentence present.
  - Commit: 10: chore(review): record gate-3 visual-qa summary across 8 templates
  </done>
</task>

<!-- ============================================================ -->
<!-- PHASE 5 — SHIP (PR + MERGE)                                  -->
<!-- ============================================================ -->

<task type="auto">
  <name>Task 27: Pre-merge sweep (validation + linter + drift)</name>
  <files>(no new files; runs all checks)</files>
  <action>
  Final pre-merge sweep before opening PR.

  Required checks, all must pass:
  1. python3 tools/check_ci.py — all 8 templates green.
  2. python3 tools/sla_diff.py against the 3 originals — round-trip green for the existing 3.
  3. python3 -m pytest tools/sla_lib/tests/ -v — all DSL tests pass.
  4. python3 -m pytest templates/_smoke/ -v — all smoke tests pass.
  5. python3 tools/spec_check.py --all — no drift between specs and builds.
  6. bin/check-stale-previews — all 8 templates' SHA pins match.
  7. bin/validate — global validator green.
  8. python3 tools/gallery_build.py — emits 8 templates.
  9. cd site && npm run build — Astro build succeeds (if site builds locally).

  If any check fails, fix and re-run. If a fix changes a template's SLA, re-run
  Gate 3 for that template (small iteration, can be a single iter-N pass).

  Final commit before PR: 10: chore(release): pre-merge sweep green for 8 templates.
  </action>
  <verify>
  <automated>python3 tools/check_ci.py 2>&1 | tail -5 && python3 -m pytest tools/sla_lib/tests/ templates/_smoke/ -v 2>&1 | tail -10 && python3 tools/spec_check.py --all 2>&1 | tail -5 && bin/check-stale-previews 2>&1 | tail -5 && bin/validate 2>&1 | tail -5 && python3 tools/gallery_build.py 2>&1 | tail -5</automated>
  </verify>
  <done>
  - All 9 checks listed above pass.
  - Commit: 10: chore(release): pre-merge sweep green
  </done>
</task>

<task type="auto">
  <name>Task 28: Open PR + populate description with side-by-side gallery</name>
  <files>(no new files; uses gh CLI)</files>
  <action>
  Open the PR via gh CLI per project convention.

  PR title: "10: 5 neue Vorlagen + Spec-System + Visual-QA-Pipeline"

  PR description (use HEREDOC; long-form):
  - Summary: 1-2 sentences on what landed (5 new templates, spec system, visual-QA
    pipeline, 3 review gates).
  - Files-changed overview: brief.
  - Acceptance criteria checklist from ISSUE.md, each ticked with link to evidence
    (commit, file, or report).
  - Side-by-side gallery: embed reviews/all-templates-grid.png AS AN INLINE IMAGE
    in the PR description (gh markdown supports image references). Use the relative
    path or upload via the gh API if needed.
  - Per-template summary: 5 sections each with a thumbnail + 1-line "better than
    existing-3 because…" + link to canonical reviews/visual-qa-SLUG.md.
  - Notes:
    * Vision review is local-only (Gate 3 ran locally; CI does build/check/gallery only).
    * Round-trip diff of the existing 3 templates remained green throughout.
    * No CI workflow changes.
    * No "claude" attribution anywhere.
    * Coordinate with #9 (post-migration-dsl-hygiene) — this branch appended to
      blocks.py at the bottom; rebase should be trivial. If #9 lands first, rebase #10.
  - Mensch-Review Bitte: ask for at least 2 confirmations "sieht mindestens so gut aus
    wie die bestehenden drei" per acceptance criterion.

  Steps:
  - git status / git diff base summary.
  - Confirm branch tracks remote; if not, push -u origin <branch>.
  - gh pr create with the description.
  - Print the PR URL.

  Do NOT merge. Wait for human confirmation.
  </action>
  <verify>
  <automated>gh pr view --json number,title,body,url 2>&1 | head -20</automated>
  </verify>
  <done>
  - PR open and visible via gh pr view.
  - Description embeds reviews/all-templates-grid.png.
  - All acceptance criteria checked off with links.
  - Mensch-Review request explicitly in description.
  - PR URL reported.
  </done>
</task>

</tasks>

<verification>
Final pre-merge checks (all must pass; this is duplicated in Task 27 but listed here as
the canonical end-of-plan validation):

- `python3 tools/check_ci.py` — 8 templates green
- `python3 tools/sla_diff.py` against 3 originals — no regression on existing templates
- `python3 -m pytest tools/sla_lib/tests/ templates/_smoke/ -v` — all tests pass
- `python3 tools/spec_check.py --all` — no spec/build drift
- `bin/check-stale-previews` — SHA pins match
- `bin/validate` — global validator green
- `python3 tools/gallery_build.py` — 8 templates emitted
- `cd site && npm run build` — Astro build succeeds locally
- `gh pr view` — PR open with side-by-side gallery in description
- All 16 acceptance criteria from ISSUE.md ticked with evidence links
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md "Acceptance Criteria":

- templates/_specs/SCHEMA.md exists with Pflichtfelder, ASCII-Konvention, Slot-Tabellen-Format. (Task 1)
- 5 neue Spec-Dokumente complete with all required sections. (Tasks 3-7)
- 3 Retro-Specs match heutigen Build (slot list deckt sich mit meta.yml). (Task 2)
- 5 neue Templates bauen sauber via python3 build.py, valides Scribus-1.6-SLA, ohne Warnung. (Tasks 12-16)
- Wahlkreuz-PNG in shared/assets/ + EPS archival; eingebettet in Wahlaufruf-Postkarte, Falzflyer, Türanhänger. (Tasks 9, 13, 14, 16)
- tools/check_ci.py green für alle 5 neuen Templates. (Task 27)
- tools/sla_diff.py round-trip green auf 3 bestehenden Templates. (Task 10 + Task 27)
- Visual-Smoke-Tests in templates/_smoke/ erkennen Layout-Brüche. (Tasks 12-16)
- tools/visual_review.py ausführbar, sendet PNGs an >=2 externe Modelle, schreibt Markdown-Report. (Task 20)
- Gate 1 — Spec-Review report unter reviews/spec-review-*.md, Findings adressiert. (Task 8)
- Gate 2 — Code-Review report unter reviews/code-review-*.md, Findings adressiert. (Task 18)
- Gate 3 — Visual Render-Review pro Template unter reviews/visual-qa-SLUG.md (Multi-Model). (Tasks 21-25)
- Gate 3 — Side-by-Side-Konsens: 3 Vision-Modelle bestätigen "mindestens so gut wie bestehend" pro Template. (Tasks 21-25 final state)
- Mindestens eine Review->Fix->Re-Review-Schleife pro Template; Vorher/Nachher dokumentiert. (Tasks 21-25 explicit iter-2/iter-3 documents)
- Gesamt-Report reviews/visual-qa-summary.md mit Side-by-Side aller 8 + merge-ready pro Template. (Task 26)
- Mensch-Review: 2 Bestätigungen "sieht mindestens so gut aus wie die bestehenden drei" in PR-Kommentaren. (Task 28 PR description requests this; user/team confirms after open.)
- gallery_build.py emittiert die 5 neuen Templates inkl. PNG-Previews. (Task 17)
- CI-Workflow .github/workflows/pages.yml baut, validiert, deployed alle 8 Templates ohne manuellen Eingriff. (Task 27 — no CI YAML change required; existing workflow globs templates/.)
- PR-Beschreibung enthält Vorher/Nachher-Galerie-Screenshots aller 8 Templates nebeneinander. (Task 28)
</success_criteria>
