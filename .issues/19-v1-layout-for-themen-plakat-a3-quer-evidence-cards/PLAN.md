# Plan: V1 layout for `themen-plakat-a3-quer` — "Evidence Cards"

<objective>
What this plan accomplishes: Implement V1 "Evidence Cards" for `templates/themen-plakat-a3-quer/` — 60/40 hero-photo + headline-stack split, three Hellgrün backing cards each carrying stat-hero number + Gelb caps label + white body text — with 3 NEW ParaStyles + 1 ParaStyle linesp mutation, the post-#24 `build_template + build_preview` split using INJECT_MAP for `Themen-Hero`, a 17-entry CONSTRAINTS rewrite that drops Card from inner-axis `same_x` and uses `inside(Hero, Hero-Foto-Card)` instead of the geometrically-invalid `aligned_below(Hero, Sub-Headline)`, regenerated artifacts via `bin/render-gallery` + meta.yml SHA bump, brand_overrides cleanup (REMOVE 3 + UPDATE 1 reason + decide on `logo_size_3M` per locked logo `w=53.46`), full smoke-test rewrite for the V1 anname set, full spec rewrite, NEW invariant-pinning geometry tests in `tools/sla_lib/tests/test_themen_plakat_geometry.py`, and a Brief §10 session-history row + EXECUTION.md.

Why it matters: Third of five V1 implementations in the iter-4 sequence. Fixes the "halb-leerer Frame" hero photo (today's `crop_for_frame(target_w_mm=180, target_h_mm=60)` literal-targets-vs-frame-dims drift), lifts the body off white onto Hellgrün cards, and gives the three Belege real visual weight. Validates that the post-#24 INJECT_MAP idiom + the post-#23 `brand:visual_adjacency_drift` rule handle a single-page A3-quer composition cleanly without override carry-over.

Scope:
- IN: `templates/themen-plakat-a3-quer/build.py` (ParaStyles + layout deltas + build split + INJECT_MAP + CONSTRAINTS rewrite); `templates/themen-plakat-a3-quer/meta.yml` (ci_overrides extend, brand_overrides cleanup, previews_for_sla SHA bump); `templates/themen-plakat-a3-quer/template.sla` + `preview.pdf` + `page-01.png` (regen); `templates/_smoke/test_themen_plakat_a3_quer.py` (rewrite); `templates/_specs/themen-plakat-a3-quer.md` (full rewrite); NEW `tools/sla_lib/tests/test_themen_plakat_geometry.py`; `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 row; `.issues/<slug>/EXECUTION.md`.
- OUT: V2 "Hero Photo Plakat", V3 "Argument Stack" (both backlog per ISSUE.md "Out of scope"); Codex visual review (locked decision #6 — SKIP for single-page A3); new BrandRule additions (locked #13 — registry stays at 15); DSL extensions (`scale_type=aspect_fill` enum, `same_x_center` helper — both locked-OUT per RESEARCH.md scope changes); refactor of pre-existing non-conformant ParaStyles (`themen-plakat/sub`/`beleg-headline`/`beleg-body`/`source`/`impressum` linesp — out of scope per locked #7, KEEP `brand:line_spacing_0.9` override).

No CONTEXT.md exists for this issue — decisions follow RESEARCH.md's 13 locked decisions (lines 25-39), which override ISSUE.md where they conflict. ISSUE.md has 3 documented errors that this plan corrects in the executor's output without re-litigating: (1) `scale_type=aspect_fill` doesn't exist → use INJECT_MAP; (2) `same_x` quad with Card+contents will fail → drop Card, rely on `inside()`; (3) `aligned_below(Hero, Sub-Headline)` is geometrically invalid (different x columns + different y stacking) → replace with `inside(Hero, Hero-Foto-Card)`.
</objective>

<skills>
No workspace skills directory present (`.claude/skills/` not found in worktree). Executor follows the inline `Don't:` blocks per task and the standard repo conventions documented in `shared/brand/SPEC-WRITING-GUIDE.md` (referenced by current `build.py` line 1-8 docstring) and `shared/brand/DESIGN-SYSTEM-BRIEF.md`.
</skills>

<context>
Issue: @.issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/ISSUE.md
Research (synthesized, locked decisions): @.issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/RESEARCH.md
Pitfalls (predictive verification, brand-rule arithmetic): @.issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/research/pitfalls.md
Design package (V1 source-of-truth, brainstorm with internal contradictions — see RESEARCH.md §14): @improvements/03-themen-plakat.md (workspace root, NOT committed; reference only)
Reference plan (V1 pattern precedent, INJECT_MAP discussion): @.issues/archive/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/PLAN.md
Reference plan (V1 pattern precedent, ParaStyle parallel pattern): @.issues/archive/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/PLAN.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

### BRAND_CONSTRAINTS registry — exactly 15 rules (post-#24; #19 doesn't add)
From `tools/sla_lib/builder/brand_constraints.py:1302-1443`:
```
1.  brand:color_palette
2.  brand:font_family
3.  brand:line_spacing_0.9
4.  brand:hl_sl_distance_x2
5.  brand:logo_size_3M
6.  brand:text_on_green               # only fires for ^ci/(h|headline) — V1 styles use themen-plakat/* prefix → scope-skips
7.  brand:bleed_3mm
8.  brand:wahlkreuz_colored_bg
9.  brand:inside_page
10. brand:spine_safety
11. brand:visual_adjacency_drift      # 4-axis check + declaration-disagreement (re-enabled in T07)
12. brand:bleed_coverage              # facing_pages early-return → no-op here
13. brand:image_text_overlap          # text fully inside shape = allowed (rule docstring at brand_constraints.py:725-727)
14. brand:cover_extent_match
15. brand:image_fills_frame           # NEW from #24 — JPEG aspect must match frame; INJECT_MAP pre-crop satisfies by-construction
```

### Constraint factories (`tools/sla_lib/builder/constraints.py`) — V1 uses
```python
def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint    # L408
def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint    # L399
def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint   # L453
def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint   # L433
def aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint   # L507  -- NOT USED in V1 CONSTRAINTS list
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint   # L498
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint   # L489
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5, name: str = "") -> Constraint   # L417
def same_style(*targets, name: str = "") -> Constraint
# Resolver matches on `anname` exactly (case-sensitive).
# NO same_x_right / same_y_bottom / same_x_center helpers exist — do not invent.
```

### Primitives (`tools/sla_lib/builder/primitives.py`)
```python
@dataclass
class Polygon(_Frame):
    fill: Optional[str] = None      # "Dunkelgrün" | "Hellgrün" | "Gelb" | "White" | ...
    layer: int = 0                  # V1 backing polygons (Hero-Foto-Card + 3 Beleg cards) use layer=1
    anname: str = ""
    shape: str = "rect"

@dataclass
class ImageFrame(_Frame):
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None
    scale_type: int = 0             # 0=ScaleAuto fit-to-frame, 1=Manual. NO `aspect_fill` enum.
    ratio: int = 1                  # 1=preserve aspect, 0=stretch
    local_scale: tuple[float, float] = (1.0, 1.0)
    layer: int = 0
    anname: str = ""

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""
    fcolor: str = ""
    runs: Optional[list] = None
    layer: int = 0
    anname: str = ""

@dataclass
class Run:
    text: str = ""
    fcolor: Optional[str] = None
    paragraph_style: Optional[str] = None
    separator: Optional[str] = None
```

### ParaStyle (`tools/sla_lib/builder/styles.py:31-91`)
```python
@dataclass
class ParaStyle:
    name: str
    font: str                # exact face e.g. "Vollkorn Black Italic", "Gotham Narrow Bold"
    fontsize: float
    linesp: float
    linesp_mode: int = 0     # 0 = fixed
    align: int = 0           # 0=left, 1=center, 2=right
    fcolor: str = "Black"    # color-palette name e.g. "Gelb", "White", "Dunkelgrün"
    kern: Optional[float] = None         # KERN attribute, units = points
    fontfeatures: Optional[str] = None   # OpenType feature string
    language: Optional[str] = "de"
# NO `caps`/`uppercase`/`smcp` field. CAPS = uppercase the run text literally.
# Letter-spacing 0.04em on 18pt font → kern = 0.04 * 18 = 0.72 (points).
```

### `library` API (`tools/sla_lib/builder/library.py`)
```python
def load(lib_id: str, *, optional: bool = False) -> Optional[PIL.Image]:    # L300-ish
    """Load a library image by `lib_id` (manifest key). Returns None if missing & optional."""

def inject_into_frame(frame: ImageFrame, img: PIL.Image, *,
                      target_w_mm: float, target_h_mm: float,
                      dpi: int = 300, quality: int = 80,
                      apply_watermark: bool = True) -> None:   # L436-500
    """Pre-crop img to frame aspect via crop_for_frame, embed as inline JPEG,
    set frame.scale_type=0. Result: frame fills exactly with no letterbox.

    POST-#24 IDIOM: pass `target_w_mm=frame.w_mm, target_h_mm=frame.h_mm` (LIVE,
    not literal) so any geometry change in build_template propagates without
    drift-target updates."""
```

### Post-#24 INJECT_MAP reference patterns
Single-page (preferred for #19):
- `templates/postkarte-a6-kampagne/build.py:391-405`

Multi-page Zeitung (verbose reference):
- `templates/zeitung-a4-grun/build.py:2570-2625`

### Current `themen-plakat-a3-quer/build.py` state (`templates/themen-plakat-a3-quer/build.py` — 389 lines)
- L50-334: single `build_doc()` (no split today)
- L66-124: 6 ParaStyles (`themen-plakat/headline`, `/sub`, `/beleg-headline`, `/beleg-body`, `/source`, `/impressum`)
- L160-176: Logo block (w=32, h=28)
- L186-209: Headline These (x=15, y=40, w=390, h=50, fontsize 60) + Sub-Headline (x=15, y=92, w=390, h=16)
- L220-256: 3 Beleg loop (Headline + Body) using `AlignedRow` wrappers
- L272-286: Themen-Hero with INLINE `library.crop_for_frame(target_w_mm=180, target_h_mm=60)` — V1 must remove this inlining
- L295-302: QR (x=380, y=8, w=25, h=25)
- L308-317: Quelle (x=15, y=287, w=80, h=8)
- L320-332: Impressum (x=305, y=287, w=100, h=8)
- L353-384: 6-entry CONSTRAINTS list (will be fully replaced — 17 entries)

### Current `meta.yml` state (`templates/themen-plakat-a3-quer/meta.yml` — 118 lines)
- L18: `previews_for_sla: b89e207447b5d61bfe8295a2bd0c36a05af70245071f690bb9efebb789c5f9c7` (must bump in T06)
- L19-57: 6 brand_overrides (cleanup in T07)
- L58-66: ci_overrides.non_ci_styles (6 entries; extend in T01 with 3 NEW styles)
- L68-110: slots dict (will be revised in T09 spec rewrite — slots stay anname-keyed)

### Current smoke test state (`templates/_smoke/test_themen_plakat_a3_quer.py` — 153 lines, 8/8 pass on baseline)
- L70-80: `test_required_annames_present` asserts `Beleg N — Headline` annames that V1 deletes — REWRITE in T08
- L142-148: `test_styles_include_themen_plakat_locals` asserts existing 5 styles — extend optionally in T08

### Current spec state (`templates/_specs/themen-plakat-a3-quer.md` — 301 lines)
- 24 errors + 1 warning vs current SLA (per pitfalls §5 P5) — fully drifted; full rewrite in T09

### Frame geometry sanity (computed from ISSUE.md numbers — pitfalls §8)
```
Page A3 quer: 420×297 mm, bleed 3mm, MARGIN_X=15mm, GUTTER=8mm, COL_W=124.67mm
Card 1: x=15,  y=210, w=124.67, h=72 → right=139.67, bottom=282
Card 2: x=148, y=210, w=124.67, h=72 → right=272.67, bottom=282
Card 3: x=281, y=210, w=124.67, h=72 → right=405.67, bottom=282
  Right margin: 420-405.67 = 14.33mm (≈ MARGIN_X)
  Inter-card gap: 8.33mm ≈ GUTTER
  Mirror axis: (15+405.67)/2 = 210.335 → drift 0.335mm < 0.5mm tol ✓
Card N inner stack (col_x=Card N x):
  Stat:  x=col_x+5, y=215, w=114, h=24
  Label: x=col_x+5, y=242, w=114, h=8
  Body:  x=col_x+5, y=252, w=114, h=26
Themen-Hero:    x=18,  y=73,  w=194, h=114 → bottom=187
Hero-Foto-Card: x=15,  y=70,  w=200, h=120 → contains Hero with 2-3mm gap ✓
Headline These: x=235, y=70,  w=170, h=100 → right=405 (≤ 420-15=405 ✓)
Sub-Headline:   x=235, y=172, w=170, h=14
Logo:           x=15,  y=10,  w=53.46, h=48 → 3M-conformant
QR:             x=370, y=8,   w=35, h=35
```

### `themen_klimaschutz_windrad` asset
- `shared/sample-images/themen/klimaschutz-windrad.jpg` (1536×1024, native aspect 1.50)
- `crop_focus=[0.65, 0.50]` (turbine right of center)
- For Hero frame 194×114 (aspect 1.7018): centre-crop trims height; 1536×902 px keep → resize 2291×1346 px @ 300 dpi
- `inject_into_frame` re-applies Symbolfoto watermark by default
</interfaces>

Key files (executor reference):
@templates/themen-plakat-a3-quer/build.py — primary edit target (T01-T05)
@templates/themen-plakat-a3-quer/meta.yml — ci_overrides + brand_overrides + SHA (T01, T06, T07)
@templates/themen-plakat-a3-quer/template.sla — regenerated (T06)
@templates/themen-plakat-a3-quer/preview.pdf — regenerated (T06)
@templates/themen-plakat-a3-quer/page-01.png — regenerated (T06)
@templates/_smoke/test_themen_plakat_a3_quer.py — rewritten (T08)
@templates/_specs/themen-plakat-a3-quer.md — rewritten (T09)
@tools/sla_lib/tests/test_themen_plakat_geometry.py — NEW (T10)
@shared/brand/DESIGN-SYSTEM-BRIEF.md — §10 row appended (T11)
@.issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/EXECUTION.md — appended (T11)
</context>

<commit_format>
Format: conventional with numeric-id prefix (per `.issues/config.yaml::commits.format=conventional, prefix=true`)
Example: `19: feat(themen-plakat): add stat-hero, beleg-body-on-green, beleg-headline-yellow ParaStyles`
Pattern: `19: <type>(<scope>): <subject>` where type ∈ {feat, fix, chore, refactor, docs, test} and scope identifies the touched subsystem (`themen-plakat`, `meta`, `smoke`, `spec`, `tests`, `brief`, `execution`).
</commit_format>

<tasks>

<task type="auto">
  <name>Task 1: feat(themen-plakat): add 3 V1 ParaStyles + headline linesp mutation + meta.yml ci_overrides extension</name>
  <files>templates/themen-plakat-a3-quer/build.py, templates/themen-plakat-a3-quer/meta.yml</files>
  <action>
Add 3 NEW ParaStyles into `build.py::build_doc()` (which T02 will rename to `build_template()`) right after the existing 6 ParaStyles block (current line 124, after the `themen-plakat/impressum` add). Mutate the existing `themen-plakat/headline` linesp 64→54 in place (single in-template consumer; not a parallel-pattern candidate per pitfalls §P14).

Why this order first: T03 frames reference these style names. Adding them first prevents Scribus default-style fallback from masking constraint misfires in later tasks.

`build.py` additions (insert after current line 124):
```python
# V1 (#19) Evidence Cards — 3 NEW ParaStyles + headline linesp mutation.
# stat-hero: large yellow Vollkorn Black Italic for the per-card statistic.
doc.add_para_style(ParaStyle(
    name="themen-plakat/stat-hero",
    font="Vollkorn Black Italic",
    fontsize=56,
    linesp=50.4,        # 0.9 × 56 = 50.4 — line_spacing_0.9 conformant
    linesp_mode=0,
    align=0,            # left flush — caps Label sits centred below; stat reads as anchor
    fcolor="Gelb",
    language="de",
))
# beleg-body-on-green: white body text laid on Hellgrün card.
# Per pitfalls §P15 we do NOT mutate the existing themen-plakat/beleg-body align
# (no consumer post-V1; mutation contradicts ISSUE.md own ParaStyles list).
doc.add_para_style(ParaStyle(
    name="themen-plakat/beleg-body-on-green",
    font="Gotham Narrow Book",
    fontsize=13,
    linesp=16.9,        # NOT 0.9-conformant (drift 5.2pt) — brand:line_spacing_0.9 override stays per locked #7
    linesp_mode=0,
    align=1,            # centre per improvements.md §"Alignment-Spezifikation" + RESEARCH.md §18 Q2 recommendation
    fcolor="White",
    language="de",
))
# beleg-headline-yellow: small caps Gelb label below stat-hero.
# CAPS achieved by uppercasing the run text in T03 (no smcp ParaStyle field).
# letter-spacing 0.04em @ 18pt → kern = 0.04 × 18 = 0.72 pt.
doc.add_para_style(ParaStyle(
    name="themen-plakat/beleg-headline-yellow",
    font="Gotham Narrow Bold",
    fontsize=18,
    linesp=16.2,        # 0.9 × 18 = 16.2 — line_spacing_0.9 conformant
    linesp_mode=0,
    align=1,            # centre — caption-style under stat-hero
    fcolor="Gelb",
    kern=0.72,
    language="de",
))
```

Mutate the existing `themen-plakat/headline` ParaStyle (current build.py L66-74): change `linesp=64` to `linesp=54`. Reason: Headline These fontsize will drop 60→52 in T03; 0.9 × 60 = 54 keeps it 0.9-conformant for both fontsize 60 (current run-text) and the 52pt T03 layout, with leading enough room for fontsize 60 fallback rendering. Per pitfalls §P14: in-place mutation is acceptable here (single in-template consumer; not analogous to the parallel `*-on-green` pattern from #17/#18).

`meta.yml::ci_overrides.non_ci_styles` (current L58-66): EXTEND the list by appending the 3 NEW style names. Final list contains 9 entries:
```yaml
ci_overrides:
  non_ci_styles:
    - "themen-plakat/headline"
    - "themen-plakat/sub"
    - "themen-plakat/beleg-headline"
    - "themen-plakat/beleg-body"
    - "themen-plakat/source"
    - "themen-plakat/impressum"
    - "themen-plakat/stat-hero"
    - "themen-plakat/beleg-body-on-green"
    - "themen-plakat/beleg-headline-yellow"
```

**Don't:**
- Don't add `themen-plakat/beleg-body align=0→1` mutation (ISSUE.md ParaStyles bullet 5 contradicts itself per pitfalls §P15 — `beleg-body` has no consumer post-V1).
- Don't try to set `caps=True` or `uppercase=True` on the ParaStyle — these fields don't exist on `ParaStyle` (verified `tools/sla_lib/builder/styles.py:31-91`). CAPS in T03 is implemented by literal uppercasing the run text.
- Don't try OpenType `fontfeatures='c2sc'` for CAPS — `c2sc` produces small-caps from caps, NOT all-caps from lowercase.
- Don't lower `themen-plakat/beleg-body-on-green linesp` to 11.7 to satisfy `brand:line_spacing_0.9` per-style — the override stays template-wide (5 existing styles violate it; locked #7); 11.7pt on 13pt body is visually too tight (RESEARCH.md §18 Q3).
- Don't add a parallel `themen-plakat/headline-tight` instead of mutating in place (RESEARCH.md §18 Q5 — mutate is recommended for single-consumer style).
- Don't reorder the existing 6 ParaStyles — additive only.

Run order check: T01 commits ParaStyles + meta.yml ci_overrides ATOMICALLY. The `headline.linesp 64→54` mutation breaks `bin/check-stale-previews` (template.sla now drifts from cached SHA) — this is expected and resolved in T06 regen. Smoke test `test_styles_include_themen_plakat_locals` still passes (current asserts cover the existing 5; new ones are additions).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -c "import importlib.util, pathlib; p = pathlib.Path('templates/themen-plakat-a3-quer/build.py'); s = importlib.util.spec_from_file_location('m', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); doc = m.build_doc(); names = {ps.name for ps in doc.para_styles}; expected = {'themen-plakat/headline','themen-plakat/sub','themen-plakat/beleg-headline','themen-plakat/beleg-body','themen-plakat/source','themen-plakat/impressum','themen-plakat/stat-hero','themen-plakat/beleg-body-on-green','themen-plakat/beleg-headline-yellow'}; missing = expected - names; assert not missing, f'missing styles: {missing}'; hl = next(ps for ps in doc.para_styles if ps.name=='themen-plakat/headline'); assert hl.linesp == 54, f'headline linesp {hl.linesp} != 54'; sh = next(ps for ps in doc.para_styles if ps.name=='themen-plakat/stat-hero'); assert sh.fcolor == 'Gelb' and sh.fontsize == 56, sh; print('T01 ParaStyles OK')"</automated>
  </verify>
  <done>
  - 3 NEW ParaStyles present in `doc.para_styles` with correct font/fontsize/linesp/fcolor/kern/align values
  - `themen-plakat/headline.linesp` == 54 (mutated from 64)
  - `meta.yml::ci_overrides.non_ci_styles` lists all 9 styles (6 existing + 3 NEW)
  - `build.py` still imports clean; no NameError
  - Existing smoke `test_styles_include_themen_plakat_locals` continues to pass (additions don't break existing assertions)
  </done>
</task>

<task type="auto">
  <name>Task 2: refactor(themen-plakat): split build_doc into build_template + build_preview with build_doc alias</name>
  <files>templates/themen-plakat-a3-quer/build.py</files>
  <action>
Refactor `build.py` to introduce the post-#24 `build_template + build_preview` split per RESEARCH.md "V1 build_template + build_preview split" pattern (lines 144-176) + locked decision #1.

Why now (BEFORE T03 layout edits): T03 will REMOVE the inline `library.load("themen_klimaschutz_windrad", optional=True) + library.crop_for_frame(target_w_mm=180, target_h_mm=60) + pack_inline_image(...)` block at current build.py L272-286. T04 will ADD the INJECT_MAP loop into `build_preview()`. Splitting first means T03/T04 land on a clean shape.

Concrete changes to `build.py`:

1. RENAME the current `build_doc()` (L50-334) to `build_template()`. The function signature stays `def build_template() -> Document:`. The docstring becomes:
```python
def build_template() -> Document:
    """Construct the Themen-Plakat A3 quer Document — DSL-only, no photo bytes.

    Round-trip stable: T03 removes inline image data so this function is
    safe to feed into structural_check / spec_check / smoke without
    triggering image-fills-frame / preview-SHA drift.

    For preview rendering (PDF + PNG gallery) callers go through
    build_preview() which wraps build_template() and injects library
    images per INJECT_MAP using the post-#24 idiom (#19 RESEARCH §1).

    Returns the Document without saving — callers (CLI / structural_check)
    decide where (or whether) to persist.
    """
```

2. ADD `build_preview()` function placed AFTER `build_template()` and BEFORE `build()`. T04 will fill in the loop body — for now T02 gives it a no-op skeleton that just calls `build_template()`:
```python
INJECT_MAP: dict[str, str] = {}   # T04 fills with {"Themen-Hero": "themen_klimaschutz_windrad"}


def build_preview() -> Document:
    """Inject demo library images for gallery PNG render (#24 idiom).

    Pattern: pre-crops the source image to the frame's LIVE dimensions
    via library.inject_into_frame, eliminating the literal-target drift
    that produced the half-empty hero frame in iter-3.
    """
    doc = build_template()
    if not INJECT_MAP:
        return doc
    for page in doc.pages:
        for item in page.items:
            if isinstance(item, ImageFrame) and item.anname in INJECT_MAP:
                lib_id = INJECT_MAP[item.anname]
                img = library.load(lib_id, optional=True)
                if img is None:
                    continue
                library.inject_into_frame(
                    item, img,
                    target_w_mm=item.w_mm,
                    target_h_mm=item.h_mm,
                )
    return doc
```

3. ADD the `build_doc` alias AT MODULE LEVEL (after `build_preview` and before `build`):
```python
# Alias for structural_check / spec_check / smoke — they expect build_doc.
# Keep this alias indefinitely; it points at the clean template (no photos).
build_doc = build_template
```

4. UPDATE `build()` (currently L337-341) to use `build_preview()` so the saved `template.sla` (consumed by `bin/render-gallery`) carries the injected hero image for preview rendering:
```python
def build(out_path: str | Path = HERE / "template.sla") -> Path:
    doc = build_preview()
    out_path = Path(out_path)
    doc.save(out_path)
    return out_path
```

Note on the duality of `template.sla`: `bin/render-gallery` (T06) regenerates `template.sla` via `build()` → `build_preview()` so the saved file carries the injected hero. `structural_check` and `spec_check` import the module and call `build_doc` (= `build_template`) directly so they see the CLEAN doc with no photo bytes — exactly the post-#24 contract for `brand:image_fills_frame` and round-trip-stable validation. This duality matches the Postkarte-A6-Kampagne pattern (`templates/postkarte-a6-kampagne/build.py:391-405`).

**Don't:**
- Don't move the existing inline image block (current L272-286 hero or L160-176 logo or L291-302 QR) yet — T02 only does the structural split. T03/T04 own the hero refactor; logo + QR stay inline (they are NOT library-managed).
- Don't make `build_doc` a wrapper function — it MUST be an alias `build_doc = build_template` (some downstream tools reference `build_doc` by attribute identity).
- Don't put the INJECT_MAP loop body in `build_template()` — it MUST live in `build_preview()` only, otherwise photo bytes leak into the clean doc and `brand:image_fills_frame` would fail on the structurally-checked clean doc.
- Don't hard-fail when `library.load` returns None — the `if img is None: continue` early-skip is mandatory (template must build offline / when shared/sample-images is missing).
- Don't change the `build()` signature or `out_path` default — downstream callers depend on `templates/themen-plakat-a3-quer/template.sla` as the canonical artifact.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -c "import importlib.util, pathlib; p = pathlib.Path('templates/themen-plakat-a3-quer/build.py'); s = importlib.util.spec_from_file_location('m', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); assert callable(m.build_template), 'build_template missing'; assert callable(m.build_preview), 'build_preview missing'; assert m.build_doc is m.build_template, 'build_doc must be alias of build_template'; assert isinstance(m.INJECT_MAP, dict), 'INJECT_MAP missing'; doc1 = m.build_template(); doc2 = m.build_preview(); assert doc1 is not doc2, 'build_template and build_preview must return distinct Document instances'; print('T02 split OK')"</automated>
  </verify>
  <done>
  - `build.py` exposes `build_template()`, `build_preview()`, `build_doc` (alias), `build()`, `INJECT_MAP` (dict, may be empty after T02 — T04 populates)
  - `build_doc is build_template` evaluates True
  - `build()` calls `build_preview()` (verified by `template.sla` regen at T06 picking up T04's INJECT_MAP)
  - Existing smoke test still passes (no anname / style changes yet)
  - `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer` still runs (structural state unchanged)
  </done>
</task>

<task type="auto">
  <name>Task 3: feat(themen-plakat): V1 layout deltas — frames added, deleted, repositioned</name>
  <files>templates/themen-plakat-a3-quer/build.py</files>
  <action>
Apply ALL V1 frame edits inside `build_template()` per ISSUE.md geometry + RESEARCH.md interfaces "Frame geometry sanity check". This is the largest single edit; commit it atomically so smoke (T08) and CONSTRAINTS (T05) reference a single coherent state.

Edits (use ISSUE.md geometry table — RESEARCH.md §14 confirmed canonical):

### 3.1 Logo (current L168-176)
Change `w_mm=32, h_mm=28` → `w_mm=53.46, h_mm=48`. Per locked decision #5: w=53.46 (not 54) for `brand:logo_size_3M` exact-3M conformance (M=0.06×297=17.82, 3M=53.46). Updates the inline comment block (L151-159) to reflect 3M-on-A3-quer placement and remove the "60% of target" justification.

```python
page.add(ImageFrame(
    x_mm=15, y_mm=10, w_mm=53.46, h_mm=48,
    inline_image_data=data,
    inline_image_ext=ext,
    scale_type=0,
    ratio=1,
    layer=1,
    anname="Logo Grüne (top-left)",
))
```

### 3.2 Headline These (current L186-196)
Change `x_mm=15, y_mm=40, w_mm=390, h_mm=50` → `x_mm=235, y_mm=70, w_mm=170, h_mm=100`. Right-half 60/40 column. The `themen-plakat/headline` ParaStyle was mutated to fontsize 60 (still) → linesp 54 (T01). For V1 ISSUE.md prescribes fontsize 52 — emit run text identical, but the layout-fontsize coupling is implicit (Vollkorn Black Italic 52pt @ linesp 54 = 1.038× ratio, slightly looser than 0.9 — acceptable; if executor wants strict 0.9 conformance, set fontsize 60 in style + emit 60pt visually OR adjust linesp to 46.8 — the T01 mutation chose 54 which works for both 60 and 52 fontsize). KEEP fontsize 60 in ParaStyle (T01 only changed linesp); the visual fontsize-52 from improvements.md is a future polish not required for this PR. Run text: `"Klimaschutz ist Wirtschaftspolitik."` (same as current).

### 3.3 Sub-Headline (current L199-209)
Change `x_mm=15, y_mm=92, w_mm=390, h_mm=16` → `x_mm=235, y_mm=172, w_mm=170, h_mm=14`. Same right-half column. Run text: `"Drei Belege aus Niederösterreich, Mai 2026."` (same as current).

### 3.4 NEW Hero-Foto-Card backing polygon (insert BEFORE the Themen-Hero ImageFrame so layer ordering renders backing behind photo)
```python
# V1 (#19) Evidence Cards — Hellgrün backing for the hero photo. layer=1
# (above background layer=0, below text layer=2). Provides visual weight
# behind the 60/40-split photo + frames `Themen-Hero` for the
# inside(Hero, Hero-Foto-Card) constraint witness.
page.add(Polygon(
    x_mm=15, y_mm=70, w_mm=200, h_mm=120,
    fill="Hellgrün",
    layer=1,
    anname="Hero-Foto-Card",
))
```

### 3.5 Themen-Hero ImageFrame (current L272-286)
DELETE the inline `library.load + crop_for_frame + pack_inline_image` block (L272-278). REPLACE the ImageFrame with a clean DSL frame (NO inline image data — INJECT_MAP fills in T04). Geometry: `x_mm=18, y_mm=73, w_mm=194, h_mm=114`. Sits inside Hero-Foto-Card with 3mm gap top/left, 3mm bottom (15+200=215, 18+194=212 → 3mm right; 70+120=190, 73+114=187 → 3mm bottom).

```python
# Themen-Hero — central library reference (#13). 194×114mm landscape frame
# (~1.7:1). Source 1536×1024 (~1.5:1) → centre-crop trims height per
# crop_focus=[0.65, 0.50] manifest entry. Image bytes injected by
# build_preview()::INJECT_MAP loop using the post-#24 idiom that reads
# frame.w_mm / frame.h_mm LIVE — no literal target drift.
page.add(ImageFrame(
    x_mm=18, y_mm=73, w_mm=194, h_mm=114,
    scale_type=0, ratio=1,
    layer=1,
    anname="Themen-Hero",
))
```

### 3.6 DELETE old Beleg loop (current L220-256: 3× headline + body via AlignedRow)
Remove the entire `belege = [...]` list and the `for i, (hd, body, label) in enumerate(belege):` block including the two AlignedRow page.add calls. The AlignedRow imports (`AlignedRow` from `sla_lib.builder` at current L29) become unused — remove from the import block (current L18-32) to keep `from __future__ import annotations` lint-clean.

### 3.7 ADD V1 Beleg blocks (insert in the position the deleted loop occupied)
For each `i in (0, 1, 2)`, emit (in this exact order so layer/Z-index renders Card behind Stat/Label/Body):
1. Card backing polygon (`Beleg N — Card`, layer=1, fill=Hellgrün)
2. Stat-Hero text (`Beleg N — Stat`, layer=2, style=themen-plakat/stat-hero)
3. Label text (`Beleg N — Label`, layer=2, style=themen-plakat/beleg-headline-yellow, run text UPPERCASED)
4. Body text (`Beleg N — Body`, layer=2, style=themen-plakat/beleg-body-on-green)

```python
# V1 (#19) Evidence Cards — three Hellgrün backing cards each carrying
# stat-hero number + caps Gelb label + white body text on green. Card
# x = MARGIN_X + i × (COL_W + GUTTER); inner Stat/Label/Body inset by 5mm.
v1_belege = [
    ("12 700",    "Grüne Jobs in NÖ",
     "In Niederösterreich arbeiten 12 700 Menschen direkt in der "
     "Erneuerbaren-Energie-Branche — mehr als in der konventionellen "
     "Energiewirtschaft.",
     "Beleg 1"),
    ("1.2 Mrd. €", "Umsatz Solar + Wind",
     "Die Solar- und Wind-Branche macht in NÖ 1.2 Mrd. € Jahresumsatz "
     "aus — Tendenz steigend. Jeder Euro fließt in die regionale "
     "Wertschöpfung zurück.",
     "Beleg 2"),
    ("36 %",       "weniger CO₂ seit 2010",
     "Seit 2010 hat NÖ den industriellen CO₂-Ausstoß um 36 % reduziert — "
     "bei gleichzeitig wachsender Industrie-Produktion.",
     "Beleg 3"),
]
for i, (stat, label, body, anname_prefix) in enumerate(v1_belege):
    col_x = MARGIN_X_MM + i * (COL_W_MM + GUTTER_MM)
    inner_x = col_x + 5.0
    inner_w = COL_W_MM - 10.0   # 124.67 - 10 = 114.67 ≈ ISSUE.md w=114 (drift 0.67mm < 0.5? NO — 0.67mm. Use 114.0 explicit per ISSUE.md.)

    # Card backing (Hellgrün polygon, layer=1)
    page.add(Polygon(
        x_mm=col_x, y_mm=210, w_mm=COL_W_MM, h_mm=72,
        fill="Hellgrün",
        layer=1,
        anname=f"{anname_prefix} — Card",
    ))
    # Stat-hero (Vollkorn Black Italic 56pt Gelb, left-flush at inner_x)
    page.add(TextFrame(
        x_mm=inner_x, y_mm=215, w_mm=114.0, h_mm=24,
        layer=2,
        style="themen-plakat/stat-hero",
        runs=[Run(text=stat, paragraph_style="themen-plakat/stat-hero")],
        anname=f"{anname_prefix} — Stat",
    ))
    # Label (CAPS Gotham Narrow Bold 18pt Gelb, centred, kern=0.72)
    # CAPS via literal upper(); ParaStyle has no caps field.
    page.add(TextFrame(
        x_mm=inner_x, y_mm=242, w_mm=114.0, h_mm=8,
        layer=2,
        style="themen-plakat/beleg-headline-yellow",
        runs=[Run(text=label.upper(),
                  paragraph_style="themen-plakat/beleg-headline-yellow")],
        anname=f"{anname_prefix} — Label",
    ))
    # Body (Gotham Narrow Book 13pt White centred on green)
    page.add(TextFrame(
        x_mm=inner_x, y_mm=252, w_mm=114.0, h_mm=26,
        layer=2,
        style="themen-plakat/beleg-body-on-green",
        runs=[Run(text=body,
                  paragraph_style="themen-plakat/beleg-body-on-green")],
        anname=f"{anname_prefix} — Body",
    ))
```

### 3.8 QR (current L295-302)
Change `x_mm=380, y_mm=8, w_mm=25, h_mm=25` → `x_mm=370, y_mm=8, w_mm=35, h_mm=35`. Top-right balance to the larger logo.

### 3.9 Quelle (current L308-317)
Change `w_mm=80` → `w_mm=200`. The wider Quelle accommodates fuller source citation now that the hero photo no longer dominates the bottom band.

### 3.10 Impressum (current L320-332)
No coordinate change required by ISSUE.md (already at x=305, y=287, w=100, h=8 — left-edge already past Quelle's new w=200 endpoint at x=15+200=215; 305-215=90mm gap is fine). KEEP as-is.

**Don't:**
- Don't keep the `Beleg N — Headline` annames anywhere — V1 deletes them. T08 smoke rewrite asserts they are absent.
- Don't use the `AlignedRow` composite for V1 cards — T05 CONSTRAINTS uses `same_y` + `mirrored_x` declaratively. AlignedRow was a #12 carryover for the OLD per-row emit-order discipline.
- Don't try `scale_type=aspect_fill` or any string value for `scale_type` — it's an int (0 or 1), and there is NO "fill" enum (locked #1 + pitfalls §1).
- Don't put inline image data on Themen-Hero in `build_template()` — T04 owns the photo bytes via `build_preview()::INJECT_MAP`. Photo bytes in the clean template would (a) bloat round-trip diffs, (b) break the post-#24 `brand:image_fills_frame` clean-doc contract.
- Don't pre-crop or upper() the run texts inside `build_preview()` — T03 owns the literal run-text uppercasing for Label (the executor types `"Grüne Jobs in NÖ".upper()` once at module load).
- Don't widen Card to 130mm or shorten to h=130 (improvements.md YAML mock contradiction noted in pitfalls §16). Use ISSUE.md numbers (Card h=72).
- Don't set Stat fontsize to 22pt (improvements.md table contradiction). Use ParaStyle 56pt (T01).
- Don't add `local_scale` overrides on the Hero/Logo/QR ImageFrames — defaults `(1.0, 1.0)` are correct.
- Don't preserve the inline `crop_for_frame` block (current L272-278) — T03 deletes it as part of the Hero refactor; T04 doesn't re-add it (uses `library.inject_into_frame` instead).
- Don't change Headline run text — keep `"Klimaschutz ist Wirtschaftspolitik."`. ISSUE.md "Open Question 2" (stat-hero content discipline) is flagged for the README, not implemented as a run-text change.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -c "import importlib.util, pathlib; p = pathlib.Path('templates/themen-plakat-a3-quer/build.py'); s = importlib.util.spec_from_file_location('m', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); doc = m.build_template(); items = [it for page in doc.pages for it in page.items]; annames = {getattr(it,'anname','') for it in items}; v1_required = {'Logo Grüne (top-left)','Headline These','Sub-Headline','Hero-Foto-Card','Themen-Hero','Beleg 1 — Card','Beleg 1 — Stat','Beleg 1 — Label','Beleg 1 — Body','Beleg 2 — Card','Beleg 2 — Stat','Beleg 2 — Label','Beleg 2 — Body','Beleg 3 — Card','Beleg 3 — Stat','Beleg 3 — Label','Beleg 3 — Body','QR-Code (quelle)','Quelle','Impressum'}; missing = v1_required - annames; assert not missing, f'V1 annames missing: {missing}'; deleted = {'Beleg 1 — Headline','Beleg 2 — Headline','Beleg 3 — Headline'}; still_present = deleted & annames; assert not still_present, f'old annames still present: {still_present}'; logo = next(it for it in items if getattr(it,'anname','') == 'Logo Grüne (top-left)'); assert abs(logo.w_mm - 53.46) < 0.01, f'logo w {logo.w_mm} != 53.46'; hero = next(it for it in items if getattr(it,'anname','') == 'Themen-Hero'); assert hero.w_mm == 194 and hero.h_mm == 114, hero; assert hero.inline_image_data is None, 'Hero must have no inline image data in build_template'; print('T03 layout OK')"</automated>
  </verify>
  <done>
  - All V1 annames present in `build_template()` output (19 frames listed above)
  - Old `Beleg N — Headline` annames absent
  - Logo `w_mm == 53.46` (locked #5)
  - Themen-Hero `inline_image_data is None` in `build_template()` (T04 will inject in `build_preview()`)
  - Themen-Hero geometry x=18, y=73, w=194, h=114
  - Hero-Foto-Card Polygon geometry x=15, y=70, w=200, h=120, fill="Hellgrün", layer=1
  - 3 Beleg cards each at correct (col_x, 210, 124.67, 72)
  - 3 Beleg stat/label/body at (col_x+5, 215/242/252, 114, 24/8/26)
  - All 3 Label run texts are UPPERCASED literally
  - `AlignedRow` import removed from build.py imports
  - `build.py` imports clean (no NameError, no unused imports)
  </done>
</task>

<task type="auto">
  <name>Task 4: feat(themen-plakat): INJECT_MAP for Themen-Hero (post-#24 pattern, live frame dims)</name>
  <files>templates/themen-plakat-a3-quer/build.py</files>
  <action>
Populate the `INJECT_MAP` constant added in T02 with the single Themen-Hero entry. T02 placed the empty dict and the loop body. T04 only changes the dict literal:

Find the `INJECT_MAP: dict[str, str] = {}` line added in T02 and replace with:
```python
# Post-#24 INJECT_MAP idiom (#19 RESEARCH §1, locked decision #1):
# value = bare lib_id (manifest key). Loop reads target_w_mm / target_h_mm
# LIVE from each frame, eliminating the literal-target drift that produced
# the half-empty hero in iter-3 (`crop_for_frame(target_w_mm=180, h=60)`
# vs frame at w=194, h=114 → photo rendered at 90×60 inside 194×114 frame).
INJECT_MAP: dict[str, str] = {
    "Themen-Hero": "themen_klimaschutz_windrad",
}
```

After this change, calling `build()` will:
1. Run `build_preview()` → calls `build_template()` (clean doc, no photo bytes)
2. Iterate pages → finds `Themen-Hero` ImageFrame with `anname` matching INJECT_MAP key
3. Calls `library.load("themen_klimaschutz_windrad", optional=True)` → returns PIL.Image (1536×1024)
4. Calls `library.inject_into_frame(item, img, target_w_mm=item.w_mm=194, target_h_mm=item.h_mm=114)` → centre-crops img to 194×114 aspect (1.7018) per crop_focus=[0.65, 0.50] manifest, embeds as inline JPEG at 300dpi, sets `item.scale_type=0`
5. Result: Themen-Hero frame fills exactly with watermarked windrad photo (no letterbox)
6. `doc.save("template.sla")` writes the SLA with the injected JPEG inline

For `structural_check` / `spec_check` / smoke (which call `build_doc` = `build_template` directly): photo bytes are NEVER injected in the clean doc → `brand:image_fills_frame` rule sees a frame with no inline image data and scope-skips per its docstring.

**Don't:**
- Don't pass literal `target_w_mm=194, target_h_mm=114` to `inject_into_frame` — must read from `item.w_mm` / `item.h_mm` LIVE so any future geometry change in T03 propagates without code edits to T04 (this is the post-#24 lesson).
- Don't add Logo or QR to INJECT_MAP — those are NOT library-managed (Logo loads from `shared/logos/gruene-logo-bund-dunkel.png` directly via `pack_inline_image`; QR loads from `templates/themen-plakat-a3-quer/samples/qr-quelle.png` directly).
- Don't add a wrapping function or class — `INJECT_MAP` MUST be a module-level `dict[str, str]` so callers can introspect it.
- Don't use `library.compute_aspect_fill` instead — it has a known DSL unit bug at `LOCALSCX != 1` (pitfalls §1, library.py:521); the post-#24 standard is `inject_into_frame` with pre-crop (locked #1).
- Don't fail-hard if `library.load` returns None — the `if img is None: continue` guard in T02 stays. The template MUST build offline (CI without `shared/sample-images/`).
- Don't drop the `library` import at the top of `build.py` — it stays for `library.load` + `library.inject_into_frame` usage in `build_preview()`.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -c "import importlib.util, pathlib; p = pathlib.Path('templates/themen-plakat-a3-quer/build.py'); s = importlib.util.spec_from_file_location('m', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); assert m.INJECT_MAP == {'Themen-Hero': 'themen_klimaschutz_windrad'}, m.INJECT_MAP; doc_clean = m.build_template(); doc_preview = m.build_preview(); hero_clean = next(it for page in doc_clean.pages for it in page.items if getattr(it,'anname','') == 'Themen-Hero'); hero_preview = next(it for page in doc_preview.pages for it in page.items if getattr(it,'anname','') == 'Themen-Hero'); assert hero_clean.inline_image_data is None, 'clean doc must have no photo bytes'; assert hero_preview.inline_image_data is not None, f'preview doc must have injected photo bytes (got {hero_preview.inline_image_data})'; assert hero_preview.scale_type == 0, f'inject_into_frame must set scale_type=0, got {hero_preview.scale_type}'; print('T04 INJECT_MAP OK')" && cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer 2>&1 | tail -20</automated>
  </verify>
  <done>
  - `INJECT_MAP == {"Themen-Hero": "themen_klimaschutz_windrad"}`
  - `build_template().pages` Hero has `inline_image_data is None`
  - `build_preview().pages` Hero has `inline_image_data is not None` (assuming `shared/sample-images/themen/klimaschutz-windrad.jpg` is present in worktree)
  - `inject_into_frame` set `hero.scale_type = 0`
  - `bin/audit-alignment themen-plakat-a3-quer` shows zero `image_fills_frame` errors after this task (verifiable via `--all` summary)
  </done>
</task>

<task type="auto">
  <name>Task 5: feat(themen-plakat): replace CONSTRAINTS list with V1 17-entry corrected list</name>
  <files>templates/themen-plakat-a3-quer/build.py</files>
  <action>
Replace the entire module-level `CONSTRAINTS = [...]` list (current L353-384, 6 entries) with the V1 17-entry list per RESEARCH.md "V1 CONSTRAINTS list (corrected)" (lines 178-218). This list is the centerpiece correction of ISSUE.md errors 2 + 3.

Update the import line (current L18-32 import block) to reflect what V1 needs:
```python
from sla_lib.builder import (  # noqa: E402
    Brand,
    Document,
    TextFrame,
    ImageFrame,
    Polygon,
    Run,
    ParaStyle,
    pack_inline_image,
    same_x,
    same_y,
    same_size,
    inside,
    mirrored_x,
    distance_y,
    same_style,
)
```

Note: drop `AlignedRow` (T03 removed its usage), drop `distance_y` if unused (V1 uses it; KEEP). Add `same_x`, `same_size`, `inside`, `mirrored_x` (NEW V1 imports). Verify these names are exported by `tools/sla_lib/builder/__init__.py` — they ARE (per RESEARCH.md interfaces line 76-86).

Replace the CONSTRAINTS list literal:
```python
CONSTRAINTS = [
    # Headline-stack vertical hierarchy: Sub sits below Headline These in same
    # right-half column. Distance 102mm (Headline y=70 + h=100 = 170 → Sub y=172,
    # gap 2mm). Use distance_y for explicit numeric assertion.
    distance_y("Headline These", "Sub-Headline", equals=102.0,
               name="hl_to_sub"),

    # Three Evidence cards share top y=210 and same width=124.67 (row alignment +
    # uniform card sizing). same_y + same_size cover the cards_top_aligned and
    # cards_same_size invariants the layout depends on.
    same_y("Beleg 1 — Card", "Beleg 2 — Card", "Beleg 3 — Card",
           name="cards_top_aligned"),
    same_size("Beleg 1 — Card", "Beleg 2 — Card", "Beleg 3 — Card",
              name="cards_same_size"),

    # Cards mirror around page horizontal centre (axis 210mm = page_w/2).
    # Card 1 left=15 ↔ Card 3 right=405.67 → axis (15+405.67)/2 = 210.335 → drift
    # 0.335mm < 0.5mm tolerance ✓.
    mirrored_x("Beleg 1 — Card", "Beleg 3 — Card", axis_mm=210.0,
               name="cards_mirror_around_page_center"),

    # Per-card inner-axis sharing: 3 stat-heros / labels / bodies share x = col_x+5.
    # NOTE: Card itself NOT in this same_x — Card.x = col_x, contents.x = col_x+5;
    # 5mm drift > 0.5mm tol would FAIL. Containment encoded by inside() below.
    # (Pitfalls §3 P3 — ISSUE.md errata.)
    same_x("Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body",
           name="card1_v_axis"),
    same_x("Beleg 2 — Stat", "Beleg 2 — Label", "Beleg 2 — Body",
           name="card2_v_axis"),
    same_x("Beleg 3 — Stat", "Beleg 3 — Label", "Beleg 3 — Body",
           name="card3_v_axis"),

    # Per-card containment: each Stat/Label/Body sits inside its Card backing.
    # 9 inside() constraints — declarative witness for "white text on green polygon".
    inside("Beleg 1 — Stat",  "Beleg 1 — Card", name="b1_stat_in_card"),
    inside("Beleg 1 — Label", "Beleg 1 — Card", name="b1_label_in_card"),
    inside("Beleg 1 — Body",  "Beleg 1 — Card", name="b1_body_in_card"),
    inside("Beleg 2 — Stat",  "Beleg 2 — Card", name="b2_stat_in_card"),
    inside("Beleg 2 — Label", "Beleg 2 — Card", name="b2_label_in_card"),
    inside("Beleg 2 — Body",  "Beleg 2 — Card", name="b2_body_in_card"),
    inside("Beleg 3 — Stat",  "Beleg 3 — Card", name="b3_stat_in_card"),
    inside("Beleg 3 — Label", "Beleg 3 — Card", name="b3_label_in_card"),
    inside("Beleg 3 — Body",  "Beleg 3 — Card", name="b3_body_in_card"),

    # Themen-Hero containment in Hero-Foto-Card (NOT aligned_below to Sub-Headline
    # — pitfalls §4 P4: Hero (x=18) and Sub-Headline (x=235) are side-by-side in
    # the 60/40 split, NOT vertically stacked. aligned_below would be geometrically
    # invalid in either argument order.).
    inside("Themen-Hero", "Hero-Foto-Card", name="hero_in_card"),

    # Style consistency across the 3 Stat / Body frames (Label uniformity is
    # implicit via inner-axis same_x; explicit same_style covers the parallel
    # ParaStyle dependency.)
    same_style("Beleg 1 — Stat", "Beleg 2 — Stat", "Beleg 3 — Stat",
               name="stat_style_consistent"),
    same_style("Beleg 1 — Body", "Beleg 2 — Body", "Beleg 3 — Body",
               name="body_style_consistent"),
]
```

Total entries: 1 distance_y + 1 same_y + 1 same_size + 1 mirrored_x + 3 same_x + 9 inside + 1 inside (hero) + 2 same_style = **19 constraints**. (RESEARCH.md said 17; the additional 2 same_style names emerge from the parallel pattern. Acceptable — every constraint is geometrically valid by construction per RESEARCH.md "Frame geometry sanity check" + pitfalls §8.)

Sanity check the `distance_y("Headline These", "Sub-Headline", equals=102.0)` value:
- Headline These y=70, h=100 → bottom=170
- Sub-Headline y=172
- Gap = 172 - 170 = 2mm. `distance_y` semantics per `tools/sla_lib/builder/constraints.py:489` measure top-to-top NOT gap-between-frames.
- Top-to-top distance = 172 - 70 = 102. **Use equals=102.0.**
- (Cross-check with constraint factory docstring if needed — but RESEARCH.md's example uses equals=84.0 referring to a "60pt × 2 × 0.353 ≈ 42mm gap" convention; the executor should use top-to-top=102.0 to match the V1 layout literally. If `distance_y` actually measures gap-between-bottoms-and-tops, set `equals=2.0`. The executor MUST verify by reading `tools/sla_lib/builder/constraints.py:489` semantics and pick the value that satisfies the constraint at structural_check time.)

After T05, run `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer` — expected: 0 errors, all CONSTRAINTS green or 1 SKIP entry (`brand:hl_sl_distance_x2` overridden in meta.yml — kept per locked #7), 1 SKIP (`brand:line_spacing_0.9` overridden — kept). All other rules either PASS or no-op. Special attention to `brand:visual_adjacency_drift` — currently overridden; T07 will remove the override and expect this rule to PASS once the V1 CONSTRAINTS list captures the declared adjacencies (per `meta.yml` reason text at L40-45).

**Don't:**
- Don't include `Beleg N — Card` in the per-card `same_x("Beleg N — Stat", ..., "Beleg N — Body")` factories — Card.x=col_x but Stat/Label/Body.x=col_x+5; 5mm drift > 0.5mm tolerance → FAIL. Containment is captured by `inside()` (pitfalls §3 P3).
- Don't add `aligned_below("Themen-Hero", "Sub-Headline", gap_mm=8.0)` — geometrically invalid: different x columns (Hero x=18, Sub x=235), different y stacking (Hero y=73 ABOVE Sub y=172). Use `inside("Themen-Hero", "Hero-Foto-Card")` instead (pitfalls §4 P4).
- Don't increase tolerances above the 0.5mm default to "make a constraint pass" — that defeats the purpose. If a constraint fails at default tol, the geometry is wrong (or the constraint is wrong) — fix the geometry / constraint, not the tolerance.
- Don't reuse the `beleg_headlines_row` / `beleg_bodies_row` constraint names from the old list — the old `same_y` for `Beleg N — Headline` annames must NOT be referenced (those frames don't exist post-T03). New names per the list above.
- Don't drop the existing `same_style` for body — V1 keeps it; the new list's `same_style("Beleg 1 — Body", ...)` covers the 3 V1 bodies.
- Don't add a `same_y` for Stat/Label/Body across cards — implicit via `same_y` on Cards + per-card `inside`. Adding cross-card same_y for inner stack is redundant noise.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -c "import importlib.util, pathlib; p = pathlib.Path('templates/themen-plakat-a3-quer/build.py'); s = importlib.util.spec_from_file_location('m', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); names = [c.name for c in m.CONSTRAINTS]; expected_names = {'hl_to_sub','cards_top_aligned','cards_same_size','cards_mirror_around_page_center','card1_v_axis','card2_v_axis','card3_v_axis','b1_stat_in_card','b1_label_in_card','b1_body_in_card','b2_stat_in_card','b2_label_in_card','b2_body_in_card','b3_stat_in_card','b3_label_in_card','b3_body_in_card','hero_in_card','stat_style_consistent','body_style_consistent'}; missing = expected_names - set(names); assert not missing, f'missing constraints: {missing}'; assert len(m.CONSTRAINTS) >= 17, f'expected >= 17 constraints, got {len(m.CONSTRAINTS)}'; print(f'T05 CONSTRAINTS OK: {len(m.CONSTRAINTS)} entries')" && cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer 2>&1 | tail -30</automated>
  </verify>
  <done>
  - CONSTRAINTS list contains exactly the 19 expected names (verifiable via Python introspection)
  - No CONSTRAINTS entry references `Beleg N — Headline` (old annames)
  - No `aligned_below(Themen-Hero, Sub-Headline)` entry
  - `structural_check themen-plakat-a3-quer` reports 0 errors
  - All declared CONSTRAINTS report PASS (or expected SKIP for overridden brand rules)
  - `brand:visual_adjacency_drift` no longer warns (CONSTRAINTS list captures the adjacencies; T07 will then remove the override safely)
  </done>
</task>

<task type="auto">
  <name>Task 6: chore(themen-plakat): regenerate template.sla + preview.pdf + page-01.png + meta.yml SHA bump</name>
  <files>templates/themen-plakat-a3-quer/template.sla, templates/themen-plakat-a3-quer/preview.pdf, templates/themen-plakat-a3-quer/page-01.png, templates/themen-plakat-a3-quer/meta.yml</files>
  <action>
Run `bin/render-gallery themen-plakat-a3-quer --skip-visual-diff` from the repo root. This pipeline (`tools/render_pipeline.py`):
1. Calls `build()` → which now calls `build_preview()` → which injects the windrad photo via INJECT_MAP
2. Saves `templates/themen-plakat-a3-quer/template.sla`
3. Renders `template.sla` → `preview.pdf` via Scribus 1.6.5 (`xvfb-run scribus -g …`)
4. Rasters `preview.pdf` → `page-01.png` via `pdftoppm` at 100 dpi (per `meta.yml::preview_dpi=100`)
5. Computes SHA-256 of the freshly-saved `template.sla` and writes it to `meta.yml::previews_for_sla` automatically (`tools/render_pipeline.py` step 7)

Expected runtime: ~7 seconds (pitfalls §13 verified baseline).

Expected outputs:
- `template.sla` updated (now contains Hellgrün polygons + 4 V1 frames per Beleg + injected JPEG inline for Hero + new Logo/QR/Quelle dimensions + 3 NEW ParaStyle definitions)
- `preview.pdf` re-rendered (1 page, 420×297mm, 3mm bleed)
- `page-01.png` re-rastered (~4960×3508 px @ 300 dpi or whatever `preview_dpi` resolves to)
- `meta.yml::previews_for_sla` SHA bumped from current `b89e207447b5d61bfe8295a2bd0c36a05af70245071f690bb9efebb789c5f9c7` to a NEW SHA-256 (executor MUST commit this auto-bumped value)

Post-regen verification:
- Run `PYTHONPATH=tools python3 tools/check_stale_previews.py themen-plakat-a3-quer` (or `bin/check-stale-previews`) — expected: GREEN (SHA matches).
- Visually inspect `page-01.png` — Hero photo should fill the 194×114mm frame with no letterbox (post-#24 INJECT_MAP contract); Hellgrün backing visible behind hero; 3 Hellgrün cards visible in lower band each with large Gelb stat number, Gelb caps label, white body.

If `bin/render-gallery` fails (Scribus crash, font missing, asset missing), the executor STOPS and reports the failure — DO NOT commit partial regen. Re-running the same command after a transient failure is safe (idempotent on the build side).

**Don't:**
- Don't manually edit `meta.yml::previews_for_sla` — let the pipeline write the SHA. Manually-typed SHAs drift silently.
- Don't run without `--skip-visual-diff` — visual-diff requires a baseline-PNG which doesn't exist for V1 yet (the V1 layout is the new baseline). The `--skip-visual-diff` flag is mandatory for V1 first-render.
- Don't commit `template.sla` without also committing `preview.pdf` + `page-01.png` + the bumped `meta.yml` SHA — the four files form an atomic state per `bin/check-stale-previews` contract (`tools/check_stale_previews.py:46-49` SHA contract).
- Don't run `bin/render-gallery --all` — too slow; we only changed one template.
- Don't bypass `xvfb-run` — Scribus headless requires a display; the pipeline handles this internally.
- Don't try to render via direct `scribus -python` — use the wrapper `bin/render-gallery` so `meta.yml` SHA bump happens.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && bin/render-gallery themen-plakat-a3-quer --skip-visual-diff 2>&1 | tail -20 && PYTHONPATH=tools python3 tools/check_stale_previews.py themen-plakat-a3-quer && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer 2>&1 | tail -10 && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5</automated>
  </verify>
  <done>
  - `bin/render-gallery themen-plakat-a3-quer --skip-visual-diff` exits 0
  - `template.sla` newer mtime than build.py
  - `meta.yml::previews_for_sla` SHA differs from `b89e207447b5d61bfe8295a2bd0c36a05af70245071f690bb9efebb789c5f9c7`
  - `bin/check-stale-previews` (or `tools/check_stale_previews.py themen-plakat-a3-quer`) GREEN
  - `structural_check themen-plakat-a3-quer` reports 0 errors
  - `structural_check --all` reports 0 errors maintained (no other templates touched)
  - `page-01.png` regenerated (file mtime newer than build.py edit timestamp)
  </done>
</task>

<task type="auto">
  <name>Task 7: chore(themen-plakat): brand_overrides cleanup in meta.yml</name>
  <files>templates/themen-plakat-a3-quer/meta.yml</files>
  <action>
Edit `templates/themen-plakat-a3-quer/meta.yml::brand_overrides` (current L19-57, 6 entries) per RESEARCH.md locked decision #7 + pitfalls §6 "Brand-Override Removability Predictions" table.

Final state: 3 entries (REMOVE 3, UPDATE 1 reason, KEEP 2 — depends on logo decision).

### REMOVE these 3 entries entirely

1. `brand:visual_adjacency_drift` (current L40-45) — REASON for removal: V1 lands a 19-entry CONSTRAINTS list (T05) that captures the declared adjacencies. Per `meta.yml` reason text itself ("Re-enable once V1 lands and a CONSTRAINTS list captures the declared adjacencies (Issue #22 locked decision #9)") + #22 locked decision #9. After T05/T06 the rule should pass. If it warns/fails after removal, T05 missed an adjacency — return to T05.
2. `brand:image_text_overlap` (current L46-50) — REASON for removal: V1 has no partial text-shape overlaps. All Beleg text frames sit fully INSIDE Hellgrün card polygons (verified by `inside()` constraints in T05). The `_ImageTextOverlapRule` (`tools/sla_lib/builder/brand_constraints.py:715-805`) explicitly carves "text fully inside shape = allowed" (rule docstring at L725-727). Pitfalls §10 confirmed.
3. `brand:image_fills_frame` (current L51-57) — REASON for removal: V1 uses post-#24 `inject_into_frame(target_w_mm=item.w_mm, target_h_mm=item.h_mm)` (T04). The pre-crop guarantees Hero JPEG aspect matches frame aspect → no letterbox → `_ImageFillsFrameRule` passes by-construction. Logo + QR are not subject to this rule (they are PNG-with-aspect=ratio).

### UPDATE reason on this 1 entry (KEEP entry)

4. `brand:hl_sl_distance_x2` (current L27-33) — KEEP entry, REPLACE reason text with V1 60/40-split rationale per pitfalls §6:
```yaml
  - id: brand:hl_sl_distance_x2
    reason: >-
      V1 (#19) Evidence-Cards 60/40 columnar split places Sub-Headline at
      y=172, 2mm below the 100mm-tall Headline These at y=70 — same right-half
      column x=235. Vertical gap is intentionally tight in this layout because
      the visual rhythm is set by the column-split (left-half hero + Hellgrün
      backing carries the layout weight), not the HL/SL distance formula.
      Per improvements/03-themen-plakat.md "Brand-Rule-Konformität" §4 △.
```

### KEEP these 2 entries unchanged

5. `brand:line_spacing_0.9` (current L20-26) — KEEP. 5 existing styles (`themen-plakat/sub`, `/beleg-headline`, `/beleg-body`, `/source`, `/impressum`) violate the 0.9 ratio (drift table in pitfalls §7). NEW `themen-plakat/beleg-body-on-green` 13/16.9 also violates (T01 chose 16.9 for visual breathing per RESEARCH.md §18 Q3). Override scope is template-wide; fixing one style does not lift it. Reason text stays as-is.

### DECIDE on `brand:logo_size_3M` (current L34-39) — depends on T03 logo width

Per locked decision #5: T03 set logo `w_mm=53.46` (exact 3M = 0.06 × 297 = 17.82, 3M = 53.46). At w=53.46 with 0.5mm tolerance, `_LogoSize3MRule` (`brand_constraints.py:243-277`) PASSES → REMOVE this override entry.

Cross-check: run `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer` after the override removal. If `brand:logo_size_3M` PASSES, the removal is correct. If it fails, the executor must decide: revert to keeping the override (less clean) OR adjust logo h to a 3M-on-A3-quer conformant value.

After cleanup, expected `meta.yml::brand_overrides` final state (2-3 entries):
```yaml
brand_overrides:
  - id: brand:line_spacing_0.9
    reason: >-
      The CI palette in shared/ci.yml carries linesp/fontsize ratios that drift
      from the Quickguide 0.9 factor (e.g. ci/body-12 has 13/12 = 1.083). This
      is real palette-versus-rule drift across all templates and warrants a
      separate brand-team review (out of scope for #12). Per-template overrides
      apply uniformly. V1 (#19) themen-plakat/beleg-body-on-green at 13/16.9
      preserves the existing drift class — visual breathing chosen over
      0.9-conformance per RESEARCH.md §18 Q3.
  - id: brand:hl_sl_distance_x2
    reason: >-
      [V1 60/40 rationale — see above]
  # brand:logo_size_3M REMOVED — V1 logo w=53.46 = exact 3M conformant.
  # brand:visual_adjacency_drift REMOVED — V1 CONSTRAINTS captures adjacencies (#22 locked #9).
  # brand:image_text_overlap REMOVED — V1 text fully inside Hellgrün cards (rule carve).
  # brand:image_fills_frame REMOVED — V1 INJECT_MAP pre-crop fills exactly (#24).
```

**Don 't:**
- Don 't remove `brand:line_spacing_0.9` — multiple existing styles still violate it (pitfalls §7).
- Don 't remove `brand:hl_sl_distance_x2` — V1 60/40 split intentionally violates the gap formula (Open Question 3 from ISSUE.md).
- Don 't keep `brand:image_fills_frame` "just in case" — the post-#24 INJECT_MAP idiom is the canonical fix; carrying the override is dead weight that masks future drift.
- Don 't carry `brand:visual_adjacency_drift` — its `meta.yml` reason text itself promises removal once #19 lands.
- Don 't reorder the existing entries — append-then-delete pattern keeps git diff readable.
- Don 't bump `meta.yml::version` (0.1.0 → 0.2.0) — version bumps are not in #19 scope.
  </action>
  <verify>
  <automated>python3 -c "import yaml; d = yaml.safe_load(open('templates/themen-plakat-a3-quer/meta.yml')); ids = {o['id'] for o in d.get('brand_overrides', [])}; removed = {'brand:visual_adjacency_drift', 'brand:image_text_overlap', 'brand:image_fills_frame'}; still_present = removed & ids; assert not still_present, f'overrides should be removed: {still_present}'; assert 'brand:line_spacing_0.9' in ids, 'line_spacing_0.9 must stay'; assert 'brand:hl_sl_distance_x2' in ids, 'hl_sl_distance_x2 must stay'; print(f'T07 brand_overrides cleanup OK: final ids={sorted(ids)}')" && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer 2>&1 | tail -15 && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5</automated>
  </verify>
  <done>
  - `meta.yml::brand_overrides` final list contains 2 or 3 entries (logo_size_3M may be removed)
  - `brand:visual_adjacency_drift`, `brand:image_text_overlap`, `brand:image_fills_frame` REMOVED
  - `brand:hl_sl_distance_x2` reason text references V1 60/40 split
  - `brand:line_spacing_0.9` UNCHANGED
  - `structural_check themen-plakat-a3-quer` 0 errors after override removal
  - `structural_check --all` 0 errors maintained
  </done>
</task>

<task type="auto">
  <name>Task 8: test(smoke): rewrite test_themen_plakat_a3_quer.py for V1 anname set</name>
  <files>templates/_smoke/test_themen_plakat_a3_quer.py</files>
  <action>
Rewrite `templates/_smoke/test_themen_plakat_a3_quer.py::test_required_annames_present` (current L65-83) to assert the V1 anname set per pitfalls §2 P2. Optionally extend `test_styles_include_themen_plakat_locals` (current L137-149) to cover the 3 NEW V1 styles.

The 6 other tests (`test_page_count`, `test_trim_dimensions`, `test_bleed`, `test_no_frame_outside_trim_plus_bleed`, `test_headline_frame_height_supports_36pt`, `test_color_palette_contains_dunkelgruen`) PASS unchanged — pitfalls §2 verified via baseline run + V1 frame geometry computed (Card 3 right=405.67 < 423; Body bottom=278 < 300).

### 8.1 Replace `test_required_annames_present` body

```python
def test_required_annames_present(self):
    annames = {
        po.attrib.get("ANNAME", "")
        for po in self.doc.findall("PAGEOBJECT")
    }
    required = {
        # Header / hero region
        "Headline These",
        "Sub-Headline",
        "Themen-Hero",                # NEW load-bearing hero (V1)
        "Hero-Foto-Card",             # NEW Hellgrün backing (V1)
        # Three Beleg cards (V1 Evidence Cards layout)
        "Beleg 1 — Card",
        "Beleg 1 — Stat",
        "Beleg 1 — Label",
        "Beleg 1 — Body",
        "Beleg 2 — Card",
        "Beleg 2 — Stat",
        "Beleg 2 — Label",
        "Beleg 2 — Body",
        "Beleg 3 — Card",
        "Beleg 3 — Stat",
        "Beleg 3 — Label",
        "Beleg 3 — Body",
        # Bottom band
        "Quelle",
        "Impressum",
    }
    missing = required - annames
    self.assertFalse(missing, f"missing annames: {missing}")
    # V1 deletes the old Beleg N — Headline annames; assert their absence
    # to catch accidental legacy carry-over in build.py.
    forbidden = {"Beleg 1 — Headline", "Beleg 2 — Headline", "Beleg 3 — Headline"}
    leaked = forbidden & annames
    self.assertFalse(leaked, f"V1 should have removed these annames: {leaked}")
```

### 8.2 Extend `test_styles_include_themen_plakat_locals`

```python
def test_styles_include_themen_plakat_locals(self):
    styles = {
        s.attrib.get("NAME", "")
        for s in self.doc.findall("STYLE")
    }
    for needed in (
        # Existing baseline styles
        "themen-plakat/headline",
        "themen-plakat/beleg-headline",
        "themen-plakat/beleg-body",
        "themen-plakat/source",
        "themen-plakat/impressum",
        # V1 NEW styles (#19)
        "themen-plakat/stat-hero",
        "themen-plakat/beleg-body-on-green",
        "themen-plakat/beleg-headline-yellow",
    ):
        self.assertIn(needed, styles)
```

Run the smoke test after T08 + after T06 regen to confirm 8/8 pass on V1 SLA:
```
PYTHONPATH=tools python3 -m unittest templates._smoke.test_themen_plakat_a3_quer -v
```

**Don't:**
- Don't keep `Beleg N — Headline` in the required set — those frames don't exist post-V1 (T03 deleted them).
- Don't delete the `forbidden` assertion — it catches future regressions where someone re-adds the old Headline frames by mistake.
- Don't add brittle assertions on exact frame coordinates inside the smoke test — those belong in T10's geometry test (per #23 pattern, pin RELATIONSHIPS not COORDINATES).
- Don't change `test_no_frame_outside_trim_plus_bleed` — V1 frames all fit; modifying it weakens the bleed-sanity check.
- Don't add a test for `Themen-Hero.scale_type == 0` here — that's an integration concern handled by `brand:image_fills_frame` rule (T07 removed the override; rule now passes by-construction).
- Don't run the smoke test BEFORE T03 lands — the rewritten anname set will fail because `Hero-Foto-Card` etc. don't exist yet on the in-progress branch. Order: T03 → T05 → T06 regen → T08 smoke rewrite → smoke test passes.
  </action>
  <verify>
  <automated>PYTHONPATH=tools python3 -m unittest templates._smoke.test_themen_plakat_a3_quer -v 2>&1 | tail -20</automated>
  </verify>
  <done>
  - All 8 smoke tests pass (`Ran 8 tests in <2s OK`)
  - `test_required_annames_present` asserts the 18 V1 annames (16 listed + Quelle + Impressum)
  - `test_required_annames_present` ALSO asserts the 3 old `Beleg N — Headline` annames are ABSENT
  - `test_styles_include_themen_plakat_locals` asserts the 3 NEW V1 styles + 5 baseline styles
  </done>
</task>

<task type="auto">
  <name>Task 9: docs(spec): rewrite _specs/themen-plakat-a3-quer.md for V1 layout</name>
  <files>templates/_specs/themen-plakat-a3-quer.md</files>
  <action>
Full rewrite of `templates/_specs/themen-plakat-a3-quer.md` (currently 301 lines, 24 errors + 1 warning vs current SLA per pitfalls §5). Use #17 + #18 V1-spec rewrite patterns as templates (they are accessible at `.issues/archive/17-.../` and `.issues/archive/18-.../`).

The spec is the contract `tools/spec_check.py` validates against. After T09, `PYTHONPATH=tools python3 tools/spec_check.py themen-plakat-a3-quer` MUST report 0 errors.

### Spec sections to (re)write

1. **Frontmatter / preamble** — keep `id`, `version`, `title`, `format`, `orientation`, `pages`, `audience`, `description`. Update description to reference V1 Evidence Cards layout.

2. **Page geometry** — A3 quer 420×297mm, bleed 3mm, MARGIN_X=15mm, MARGIN_Y=12mm, GUTTER=8mm. Same as build.py constants.

3. **Slot table** — full V1 slot inventory with exact x/y/w/h matching what T03 emits and what T06 saved into `template.sla`. Use the `<interfaces>` "Frame geometry sanity check" block from this PLAN as the canonical numbers. One row per anname:

| Anname | Type | x | y | w | h | Style/Fill | Notes |
|---|---|---|---|---|---|---|---|
| Seitenhintergrund | Polygon | -3 | -3 | 426 | 303 | White | full-bleed background, layer=0 |
| Logo Grüne (top-left) | ImageFrame | 15 | 10 | 53.46 | 48 | (PNG inline) | 3M-conformant on A3 quer |
| Headline These | TextFrame | 235 | 70 | 170 | 100 | themen-plakat/headline | right-half 60/40 column |
| Sub-Headline | TextFrame | 235 | 172 | 170 | 14 | themen-plakat/sub | same column as Headline These |
| Hero-Foto-Card | Polygon | 15 | 70 | 200 | 120 | Hellgrün | layer=1, backing for Themen-Hero |
| Themen-Hero | ImageFrame | 18 | 73 | 194 | 114 | (JPEG via INJECT_MAP) | left-half 60/40 column |
| Beleg 1 — Card | Polygon | 15 | 210 | 124.67 | 72 | Hellgrün | layer=1 |
| Beleg 1 — Stat | TextFrame | 20 | 215 | 114 | 24 | themen-plakat/stat-hero | Vollkorn Black Italic 56pt Gelb |
| Beleg 1 — Label | TextFrame | 20 | 242 | 114 | 8 | themen-plakat/beleg-headline-yellow | CAPS Gotham Bold 18pt Gelb |
| Beleg 1 — Body | TextFrame | 20 | 252 | 114 | 26 | themen-plakat/beleg-body-on-green | Gotham Book 13pt White centred |
| Beleg 2 — Card | Polygon | 148 | 210 | 124.67 | 72 | Hellgrün | … |
| Beleg 2 — Stat | TextFrame | 153 | 215 | 114 | 24 | … | … |
| Beleg 2 — Label | TextFrame | 153 | 242 | 114 | 8 | … | … |
| Beleg 2 — Body | TextFrame | 153 | 252 | 114 | 26 | … | … |
| Beleg 3 — Card | Polygon | 281 | 210 | 124.67 | 72 | Hellgrün | … |
| Beleg 3 — Stat | TextFrame | 286 | 215 | 114 | 24 | … | … |
| Beleg 3 — Label | TextFrame | 286 | 242 | 114 | 8 | … | … |
| Beleg 3 — Body | TextFrame | 286 | 252 | 114 | 26 | … | … |
| QR-Code (quelle) | ImageFrame | 370 | 8 | 35 | 35 | (PNG inline) | top-right balance to Logo |
| Quelle | TextFrame | 15 | 287 | 200 | 8 | themen-plakat/source | bottom-left |
| Impressum | TextFrame | 305 | 287 | 100 | 8 | themen-plakat/impressum | bottom-right |

4. **ParaStyle hygiene list** — name, font, fontsize, linesp, linesp_mode, align, fcolor, kern (where set):

```
themen-plakat/headline           Vollkorn Black Italic   60   54    fixed   left    Dunkelgrün
themen-plakat/sub                Gotham Narrow Book      18   22    fixed   left    Dunkelgrün
themen-plakat/beleg-headline     Gotham Narrow Bold      24   27    fixed   left    Dunkelgrün       (LEGACY — no V1 consumer; kept for backward compat)
themen-plakat/beleg-body         Gotham Narrow Book      13   16    fixed   left    Black            (LEGACY — no V1 consumer)
themen-plakat/source             Gotham Narrow Book      10   12    fixed   left    Dunkelgrün
themen-plakat/impressum          Gotham Narrow Book       7    8    fixed   right   Black
themen-plakat/stat-hero          Vollkorn Black Italic   56   50.4  fixed   left    Gelb             (V1 — #19)
themen-plakat/beleg-body-on-green Gotham Narrow Book     13   16.9  fixed   centre  White            (V1 — #19)
themen-plakat/beleg-headline-yellow Gotham Narrow Bold   18   16.2  fixed   centre  Gelb     kern=0.72  (V1 — #19, CAPS via run-text)
```

5. **CONSTRAINTS section** — prose summary of the 19 declared CONSTRAINTS (T05): "Three Beleg-Cards share top y and uniform size; cards 1 + 3 mirror around page horizontal centre; per-card inner Stat/Label/Body share a left axis (col_x+5) and each sits inside its Card; Themen-Hero sits inside Hero-Foto-Card backing; Stat and Body styles are consistent across the three cards." Reference T05 for the full list.

6. **Brand-rule status** — list the 2-3 active brand_overrides (T07 final state) with reasons. Note that `visual_adjacency_drift`, `image_text_overlap`, `image_fills_frame` are NO LONGER overridden (V1 #19 lifted them).

7. **Layout philosophy** — V1 60/40 split (left hero + Hellgrün backing | right headline-stack); 3 Hellgrün Evidence Cards in the lower band carrying Stat-Hero numbers + Gelb caps labels + white body text on green; bottom-band Quelle / Impressum / QR.

8. **Removed sections** — drop any spec content referencing the old `Beleg N — Headline` frames, the old hero geometry (x=120, y=225, w=180, h=60), or pre-V1 logo dims (32×28). 

After T09, run:
```
PYTHONPATH=tools python3 tools/spec_check.py themen-plakat-a3-quer
```
Expected: 0 errors. (Warnings about `Seitenhintergrund` extra-in-SLA may still appear if the spec doesn't declare it; declare it explicitly in the slot table to suppress.)

**Don't:**
- Don't reuse the existing 301-line spec body verbatim — it has 24 drift errors. Full rewrite is mandatory (pitfalls §5 P5).
- Don't omit `Hero-Foto-Card` from the slot table — it MUST be declared so `spec_check` doesn't flag it as "extra in SLA".
- Don't omit `Seitenhintergrund` — declare it in the slot table to suppress the baseline warning.
- Don't put `Beleg N — Headline` slot rows back — they don't exist in V1 SLA; spec_check would flag them as "extra in spec, missing in SLA" errors.
- Don't reference V2 or V3 layouts (out of scope).
- Don't include `template.sla` SHA in the spec — the SHA lives in `meta.yml::previews_for_sla` only.
- Don't change the spec frontmatter `version` — version bumps are out of #19 scope.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 tools/spec_check.py themen-plakat-a3-quer 2>&1 | tail -20</automated>
  </verify>
  <done>
  - `spec_check.py themen-plakat-a3-quer` reports 0 errors
  - Spec slot table covers all 21 V1 annames (Seitenhintergrund + Logo + Headline These + Sub + Hero-Foto-Card + Hero + 12 Beleg + QR + Quelle + Impressum)
  - Spec ParaStyle table lists all 9 styles (6 baseline + 3 V1 NEW)
  - Spec references T05 CONSTRAINTS in prose
  - No references to deleted `Beleg N — Headline` frames
  </done>
</task>

<task type="auto">
  <name>Task 10: test(geometry): NEW invariant-pinning tests in tools/sla_lib/tests/test_themen_plakat_geometry.py</name>
  <files>tools/sla_lib/tests/test_themen_plakat_geometry.py</files>
  <action>
Create NEW test file `tools/sla_lib/tests/test_themen_plakat_geometry.py`. Follow the #23 pattern: pin RELATIONSHIPS, NOT absolute coordinates. RESEARCH.md locked decision #12 + codebase agent §9 prescribe ≥10 invariants. Reference: `.issues/archive/23-stricter-alignment-validation.../` for the exact pattern style if executor needs more.

```python
"""Geometry invariant tests for themen-plakat-a3-quer V1 (#19 Evidence Cards).

Per #23 pattern: pin RELATIONSHIPS not absolute COORDINATES. If V2 / V3
layouts move frames, these tests should still pass as long as the
relational invariants of the V1 design intent are preserved.

Invariants tested (≥10):
  1. Three Beleg cards share top y (row alignment)
  2. Three Beleg cards share width (uniform sizing)
  3. Three Beleg cards share height (uniform sizing)
  4. Card 1 left edge sits at MARGIN_X
  5. Card 3 right edge sits at page_w - MARGIN_X (within tolerance)
  6. Card 1 + Card 3 mirror around page horizontal centre (axis = page_w/2)
  7. Per-card Stat / Label / Body share inner-left x = card.x + 5mm
  8. Per-card Stat / Label / Body sit fully inside Card (containment)
  9. Themen-Hero sits inside Hero-Foto-Card (containment)
 10. Hero left edge sits at MARGIN_X (Hero-Foto-Card backing left edge = MARGIN_X)
 11. Headline These + Sub-Headline share left x (right-half column AXIS_HEADLINE_LEFT)
 12. Logo width is 3M = 0.06 * 297 = 53.46 mm (within tolerance)
"""
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

TEMPLATE_DIR = ROOT / "templates" / "themen-plakat-a3-quer"

# Page constants (must match build.py)
PAGE_W_MM = 420.0
PAGE_H_MM = 297.0
MARGIN_X_MM = 15.0
TOL_MM = 0.6   # slightly looser than 0.5 to absorb COL_W rounding (124.67)


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "themen_plakat_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ThemenPlakatGeometryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        mod = _load_build_module()
        # Use clean template (no photo bytes) for geometry assertions
        doc = mod.build_template()
        cls.items_by_anname = {
            getattr(it, "anname", ""): it
            for page in doc.pages
            for it in page.items
            if getattr(it, "anname", "")
        }

    def _f(self, anname):
        item = self.items_by_anname.get(anname)
        self.assertIsNotNone(item, f"frame missing: {anname}")
        return item

    def _right(self, item):
        return item.x_mm + item.w_mm

    def _bottom(self, item):
        return item.y_mm + item.h_mm

    # -------- Card row + size invariants --------

    def test_cards_share_top_y(self):
        c1, c2, c3 = (self._f(f"Beleg {i} — Card") for i in (1, 2, 3))
        self.assertAlmostEqual(c1.y_mm, c2.y_mm, delta=TOL_MM)
        self.assertAlmostEqual(c2.y_mm, c3.y_mm, delta=TOL_MM)

    def test_cards_share_width(self):
        c1, c2, c3 = (self._f(f"Beleg {i} — Card") for i in (1, 2, 3))
        self.assertAlmostEqual(c1.w_mm, c2.w_mm, delta=TOL_MM)
        self.assertAlmostEqual(c2.w_mm, c3.w_mm, delta=TOL_MM)

    def test_cards_share_height(self):
        c1, c2, c3 = (self._f(f"Beleg {i} — Card") for i in (1, 2, 3))
        self.assertAlmostEqual(c1.h_mm, c2.h_mm, delta=TOL_MM)
        self.assertAlmostEqual(c2.h_mm, c3.h_mm, delta=TOL_MM)

    # -------- Card edge anchoring --------

    def test_card_1_left_at_margin(self):
        c1 = self._f("Beleg 1 — Card")
        self.assertAlmostEqual(c1.x_mm, MARGIN_X_MM, delta=TOL_MM)

    def test_card_3_right_at_page_minus_margin(self):
        c3 = self._f("Beleg 3 — Card")
        self.assertAlmostEqual(self._right(c3), PAGE_W_MM - MARGIN_X_MM,
                               delta=TOL_MM)

    def test_cards_mirror_around_page_center(self):
        c1 = self._f("Beleg 1 — Card")
        c3 = self._f("Beleg 3 — Card")
        axis = (c1.x_mm + self._right(c3)) / 2.0
        self.assertAlmostEqual(axis, PAGE_W_MM / 2.0, delta=TOL_MM)

    # -------- Per-card inner-axis sharing --------

    def test_per_card_inner_left_axis(self):
        for i in (1, 2, 3):
            card = self._f(f"Beleg {i} — Card")
            inner_x = card.x_mm + 5.0
            for inner in ("Stat", "Label", "Body"):
                f = self._f(f"Beleg {i} — {inner}")
                self.assertAlmostEqual(
                    f.x_mm, inner_x, delta=TOL_MM,
                    msg=f"Beleg {i} — {inner} x={f.x_mm} != card+5={inner_x}",
                )

    def test_per_card_containment(self):
        for i in (1, 2, 3):
            card = self._f(f"Beleg {i} — Card")
            for inner in ("Stat", "Label", "Body"):
                f = self._f(f"Beleg {i} — {inner}")
                self.assertGreaterEqual(f.x_mm, card.x_mm - TOL_MM)
                self.assertGreaterEqual(f.y_mm, card.y_mm - TOL_MM)
                self.assertLessEqual(self._right(f), self._right(card) + TOL_MM)
                self.assertLessEqual(self._bottom(f), self._bottom(card) + TOL_MM)

    # -------- Hero containment --------

    def test_hero_inside_hero_foto_card(self):
        hero = self._f("Themen-Hero")
        card = self._f("Hero-Foto-Card")
        self.assertGreaterEqual(hero.x_mm, card.x_mm - TOL_MM)
        self.assertGreaterEqual(hero.y_mm, card.y_mm - TOL_MM)
        self.assertLessEqual(self._right(hero), self._right(card) + TOL_MM)
        self.assertLessEqual(self._bottom(hero), self._bottom(card) + TOL_MM)

    def test_hero_foto_card_left_at_margin(self):
        card = self._f("Hero-Foto-Card")
        self.assertAlmostEqual(card.x_mm, MARGIN_X_MM, delta=TOL_MM)

    # -------- Headline-stack column --------

    def test_headline_and_sub_share_left_x(self):
        hl = self._f("Headline These")
        sub = self._f("Sub-Headline")
        self.assertAlmostEqual(hl.x_mm, sub.x_mm, delta=TOL_MM)

    def test_headline_stack_in_right_half(self):
        # Per V1 60/40 split, headline-stack left edge sits past page_w/2.
        hl = self._f("Headline These")
        self.assertGreater(hl.x_mm, PAGE_W_MM / 2.0)

    # -------- Logo brand-rule conformance --------

    def test_logo_width_is_3M(self):
        # 3M = 0.06 * min(420, 297) = 0.06 * 297 = 17.82; 3M = 53.46
        logo = self._f("Logo Grüne (top-left)")
        self.assertAlmostEqual(logo.w_mm, 53.46, delta=0.5)


if __name__ == "__main__":
    unittest.main()
```

Run after T03 (since the test calls `build_template()` which depends on T02 split + T03 layout):
```
PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_themen_plakat_geometry -v
```

**Don't:**
- Don't pin absolute coordinates like `self.assertEqual(c1.x_mm, 15)` — pin RELATIONSHIPS (e.g. `c1.x_mm == MARGIN_X_MM`) so V2/V3 refactors don't break the tests just because someone moved a card by 1mm.
- Don't read `template.sla` XML in this test — call `build_template()` directly. The smoke test in T08 reads SLA; the geometry test reads the in-memory Document. This separation is per the #23 pattern (smoke = SLA-level invariants; geometry = build-level invariants).
- Don't add tests that duplicate CONSTRAINTS (T05) — CONSTRAINTS run inside `structural_check`; the geometry test is the pre-`structural_check` safety net for build-time regressions.
- Don't use `assertEqual` for floats — always `assertAlmostEqual(..., delta=TOL_MM)`. Floats accumulate.
- Don't import from `templates.themen_plakat_a3_quer.build` (not a Python package) — use `importlib.util.spec_from_file_location` per the smoke-test pattern.
- Don't tighten `TOL_MM` below 0.5mm — `COL_W = (420 - 30 - 16) / 3 = 124.6666…mm` rounds to 124.67mm in code; the 0.0033mm rounding noise compounds across 3-card spans and a strict 0.5 tolerance flakes intermittently.
- Don't add tests for ParaStyle properties (font, fontsize, fcolor) — those belong in T08 smoke or in a future style-test file. Geometry test is geometry only.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_themen_plakat_geometry -v 2>&1 | tail -25</automated>
  </verify>
  <done>
  - NEW file `tools/sla_lib/tests/test_themen_plakat_geometry.py` exists
  - All 12 invariant tests pass (`Ran 12 tests in <1s OK`)
  - File pins RELATIONSHIPS not COORDINATES (no literal `assertEqual(x_mm, 15)` patterns)
  - Test calls `build_template()` (clean doc) not `build_preview()` (avoids photo-injection IO during test runs)
  </done>
</task>

<task type="auto">
  <name>Task 11: docs(brief): append session-history row + complete EXECUTION.md</name>
  <files>shared/brand/DESIGN-SYSTEM-BRIEF.md, .issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/EXECUTION.md</files>
  <action>
Two parallel doc edits. Both are append-only — neither risks breaking existing artifacts.

### 11.1 Append session-history row to `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10

The current §10 table (`shared/brand/DESIGN-SYSTEM-BRIEF.md:151-154`) carries 2 rows for #17 + #18. Append a third row for #19 immediately after the #18 row (line 154):

```markdown
| 2026-05-09 | Pattern B · `themen-plakat-a3-quer` (Source: `improvements/03-themen-plakat.md`) | 3 Layout-Varianten (Evidence Cards / Hero Photo / Argument Stack) mit build.py-line-targeted Slot-Änderungen + SVG-Companion-Mocks unter `improvements/03-themen-plakat.html` | https://github.com/GrueneAT/vorlagen/issues/35 (V1 only; V2/V3 backlog) |
```

KEEP the trailing prose ("When you (Claude Design) finish a session, append a row here…") at line 156.

### 11.2 Write `EXECUTION.md` for issue #19

Create `.issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/EXECUTION.md`. Follow the EXECUTION.md pattern from `.issues/archive/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/EXECUTION.md` and `.issues/archive/12-spec-system-v2.../EXECUTION.md` (most recent reference).

Required sections (per project convention):

```markdown
# Execution: V1 layout for `themen-plakat-a3-quer` — Evidence Cards (#19)

## Summary
[1-2 paragraphs: what landed, links to PR # if known, end state of all validation gates]

## Tasks completed
[Task-by-task: T01 through T11 with one-line summary + commit SHA per task. Use `git log --oneline -- templates/themen-plakat-a3-quer/` to recover SHAs.]

## ISSUE.md errata corrected during planning
- `scale_type=aspect_fill` (Open Question 1) → replaced with post-#24 INJECT_MAP idiom (locked decision #1)
- `same_x("Beleg N — Card", "Stat", "Label", "Body")` → dropped Card from quad (would fail by 5mm); 3 per-row same_x + 9 inside() instead (locked decision #2)
- `aligned_below("Themen-Hero", "Sub-Headline")` → geometrically invalid (different x cols); replaced with inside(Hero, Hero-Foto-Card) (locked decision #2)
- `Logo w=54` → corrected to w=53.46 for exact 3M conformance (locked decision #5)

## Brand-overrides cleanup
[Before / after table: 6 entries before T07 → 2-3 entries after. List each entry's status: REMOVED / KEEP / UPDATE-REASON.]

## Verification gates (final state)
- `structural_check themen-plakat-a3-quer`: 0 errors
- `structural_check --all`: 0 errors maintained
- `spec_check themen-plakat-a3-quer`: 0 errors
- `unittest templates._smoke.test_themen_plakat_a3_quer`: 8/8 pass
- `unittest tools.sla_lib.tests.test_themen_plakat_geometry`: 12/12 pass
- `bin/check-stale-previews`: GREEN
- `check_ci.py`: 6 extra-style warnings (unchanged baseline behaviour — non-blocking)

## Acceptance criteria mapping
[1-line per ISSUE.md AC bullet, mapped to the task that satisfied it.]

## Out of scope (deferred)
- V2 "Hero Photo Plakat" (full-bleed photo half) — backlog
- V3 "Argument Stack" (foto-loses Backup) — backlog
- Codex visual review (locked #6 — SKIP for single-page A3)
- New BrandRule additions (locked #13 — registry stays at 15)

## Open follow-ups
- README.md content discipline note (Open Question 2 from ISSUE.md): add a note to `templates/themen-plakat-a3-quer/README.md` about the new Stat-Hero requiring Bezirksgruppen content discipline (big number + caps label format). Tracked as a future polish; not a #19 blocker.
```

**Don't:**
- Don't backdate the §10 row (use today's date — 2026-05-09 per the issue's `RESEARCH.md` and `pitfalls.md` headers).
- Don't reference an `improvements/03-themen-plakat.html` file unless it exists (current `improvements/` directory contains `03-themen-plakat.md` only — verify before linking; if HTML is missing, drop the HTML reference from the row).
- Don't insert the row in the middle of the table — append at the end (after the #18 row at line 154).
- Don't replace the trailing prose at line 156.
- Don't write EXECUTION.md before all prior tasks are committed — its commit-SHA section depends on T01-T10 git history. Run T11 LAST.
- Don't attempt an `archive` move for the issue artifacts — that's a separate `issue:close` step run by the operator after PR merge, not part of the in-PR EXECUTION write.
- Don't include `claude` references or attribution anywhere in EXECUTION.md (project memory rule).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards && grep -q "themen-plakat-a3-quer" shared/brand/DESIGN-SYSTEM-BRIEF.md && grep -q "https://github.com/GrueneAT/vorlagen/issues/35" shared/brand/DESIGN-SYSTEM-BRIEF.md && test -f .issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/EXECUTION.md && grep -q "structural_check" .issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/EXECUTION.md && grep -q "ISSUE.md errata" .issues/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/EXECUTION.md && echo "T11 OK"</automated>
  </verify>
  <done>
  - `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 table has 3 rows (was 2)
  - New row references `themen-plakat-a3-quer`, GitHub issue #35, dated 2026-05-09
  - `.issues/19-.../EXECUTION.md` exists with all required sections
  - EXECUTION.md documents the 4 ISSUE.md errata corrections + brand_overrides before/after
  - EXECUTION.md verification gates section reports actual final-state numbers (not placeholders)
  - No `claude` references in EXECUTION.md
  </done>
</task>

</tasks>

<verification>
After all 11 tasks land, run the full validation pipeline from the worktree root. Expected: GREEN across the board.

```bash
cd /root/workspace/.worktrees/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer       # 0 errors
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all                       # 0 errors maintained
PYTHONPATH=tools python3 tools/spec_check.py themen-plakat-a3-quer                       # 0 errors
PYTHONPATH=tools python3 tools/check_ci.py templates/themen-plakat-a3-quer/template.sla  # baseline warnings only (6 extra-style — non-blocking)
PYTHONPATH=tools python3 -m unittest templates._smoke.test_themen_plakat_a3_quer -v      # 8/8 pass
PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_themen_plakat_geometry -v  # 12/12 pass
PYTHONPATH=tools python3 tools/check_stale_previews.py themen-plakat-a3-quer             # GREEN
bin/audit-alignment themen-plakat-a3-quer                                                # zero `image_fills_frame` errors
```

If any gate fails, the executor STOPS and reports which task introduced the regression. Tasks land in numeric order with one commit per task; rollback is `git revert <task-commit-sha>`.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md "Acceptance Criteria" (lines 73-80):

- [ ] V1 deltas applied in `templates/themen-plakat-a3-quer/build.py` in one commit per atomic task → satisfied by T01 + T02 + T03 + T04 + T05 (build.py touched only in these 5 tasks; each is a single coherent commit).
- [ ] `build.py` regenerates `template.sla` cleanly → satisfied by T06 (`bin/render-gallery` exits 0).
- [ ] `structural_check` zero errors, all CONSTRAINTS green → satisfied by T05 + T06 (post-T05 + T06 regen, structural_check reports 0 errors with all 19 CONSTRAINTS green).
- [ ] `--all` stays green → verified at T05, T06, T07.
- [ ] `check_ci.py` passes → baseline 6 extra-style warnings on `themen-plakat/*` are non-blocking; no NEW errors expected (verify at T06 + final).
- [ ] Hero photo fills the frame (no half-empty rendering) — verified by reading the emitted `template.sla` and confirming the right Scribus `SCALETYPE`/`SCALE` attributes (no PNG inspection) → satisfied by T04 (INJECT_MAP idiom sets `scale_type=0` + pre-crops to frame aspect → `_ImageFillsFrameRule` passes by-construction).
- [ ] HL/Sub-Gap exception documented → satisfied by T07 (`brand:hl_sl_distance_x2` reason updated to V1 60/40 split rationale; entry KEPT in `meta.yml::brand_overrides`).
- [ ] Brief §10 gets the Session-History row → satisfied by T11.

Additional success criteria (not in ISSUE.md but added by RESEARCH.md):
- [ ] Smoke test reflects V1 anname set → T08.
- [ ] Spec rewritten + zero `spec_check` errors → T09.
- [ ] Invariant-pinning geometry tests added → T10.
- [ ] EXECUTION.md complete and committed → T11.
- [ ] BRAND_CONSTRAINTS registry stays at 15 (no new BrandRule added) → satisfied by NOT touching `tools/sla_lib/builder/brand_constraints.py` (locked #13).
</success_criteria>

<risks>

## Risks and verification

### High-confidence risks (already mitigated by RESEARCH.md errata correction in this plan)

1. **`scale_type=aspect_fill` does not exist in the DSL** (ISSUE.md Open Question 1).
   - **Mitigation:** T04 uses post-#24 INJECT_MAP idiom (`library.inject_into_frame(target_w_mm=item.w_mm, target_h_mm=item.h_mm)`). No DSL extension.
   - **Verification:** T04 verify command asserts `INJECT_MAP == {"Themen-Hero": "themen_klimaschutz_windrad"}` and `hero_preview.scale_type == 0`. T06 verify runs `bin/audit-alignment` which surfaces zero `image_fills_frame` errors. T07 removes the `brand:image_fills_frame` override; rule must pass by-construction.

2. **`same_x("Card", "Stat", "Label", "Body")` would FAIL** (ISSUE.md CONSTRAINTS extension).
   - **Mitigation:** T05 drops Card from per-card same_x; uses 3 per-row `same_x` (Stat/Label/Body) + 9 `inside()` for containment.
   - **Verification:** T05 verify enumerates the 19 expected constraint names; missing-set check rejects any reversion. `structural_check` post-T05 reports 0 errors.

3. **`aligned_below("Themen-Hero", "Sub-Headline")` is geometrically invalid** (ISSUE.md CONSTRAINTS extension).
   - **Mitigation:** T05 replaces with `inside("Themen-Hero", "Hero-Foto-Card")` (containment witness, geometrically valid by T03 geometry).
   - **Verification:** T05 verify confirms `hero_in_card` constraint exists; no `aligned_below` reference for Hero+Sub.

### Medium-confidence risks (require executor attention at task time)

4. **`distance_y` semantics** (T05, sanity-check note).
   - **Risk:** RESEARCH.md and pitfalls disagree on whether `distance_y` measures top-to-top (102mm in V1) or gap-between-bottom-and-top (2mm). The constraint factory at `tools/sla_lib/builder/constraints.py:489` is the canonical source.
   - **Mitigation:** T05 action explicitly tells the executor to verify by reading L489 and pick the value that satisfies at structural_check time. Both options are documented.
   - **Verification:** T05 verify runs `structural_check`; if `hl_to_sub` constraint fails, the executor knows to flip the value.

5. **`brand:logo_size_3M` removability decision** (T07).
   - **Risk:** If T03 logo `w=53.46` rendering accumulates floating-point drift in template.sla (e.g. saved as 53.4599999), `_LogoSize3MRule` (tolerance 0.5mm) might still pass — but it might fail under stricter PrintEngine sanity checks downstream.
   - **Mitigation:** T07 verify runs `structural_check` after override removal. If `brand:logo_size_3M` fails, executor reverts the removal (keeps the override) and notes in EXECUTION.md.
   - **Verification:** T07 verify command tail-checks `structural_check` output for any new error.

6. **`themen_klimaschutz_windrad` asset availability in CI** (T04, T06).
   - **Risk:** If the CI runner doesn't have `shared/sample-images/themen/klimaschutz-windrad.jpg` (e.g. asset stripped from container), `library.load(..., optional=True)` returns None and `build_preview()` skips injection → `template.sla` saved without hero photo → `bin/check-stale-previews` may flake if SHA bump expects photo bytes.
   - **Mitigation:** Asset is verified present in worktree (pitfalls §13). T04's `if img is None: continue` guard prevents a hard fail. T06 regen produces a deterministic SHA only if asset is present.
   - **Verification:** Executor confirms asset existence with `test -f shared/sample-images/themen/klimaschutz-windrad.jpg` before T06 regen.

### Low-confidence risks (informational)

7. **`improvements/03-themen-plakat.md` lives at workspace root, NOT committed** (referenced by §10 row in T11).
   - **Mitigation:** T11 row text says `improvements/03-themen-plakat.md` (matching the #17/#18 row pattern); the file's commit status doesn't affect the row. `improvements/03-themen-plakat.html` does NOT exist (only `.md`); T11 action explicitly instructs the executor to drop the HTML reference if missing.
   - **Verification:** T11 verify greps for issue #35 URL in BRIEF — passes regardless of whether HTML exists.

8. **Smoke-test ordering** (T08 vs T03).
   - **Risk:** Running T08 BEFORE T03 lands would assert `Hero-Foto-Card` etc. that don't yet exist → false-fail during in-progress dev.
   - **Mitigation:** Plan ordering is T03 → T05 → T06 regen → T08. T08 action explicitly notes "Don't run the smoke test BEFORE T03 lands."

### Out-of-scope risks (acknowledged, not addressed by #19)

- V2 / V3 layouts are backlog; no design work in this PR.
- Refactoring 5 existing non-conformant ParaStyles to satisfy `brand:line_spacing_0.9` is template-wide drift outside #19 scope (locked #7 KEEPS the override).
- Codex visual review skipped (locked #6); if Bezirksgruppen feedback surfaces visual concerns at print scale, follow-up issue.

### Final verification gate

After all 11 tasks land, the `<verification>` block above MUST pass cleanly. If any single command fails, the executor STOPS and either rolls back to the last green state OR diagnoses the failing task per its `<done>` checklist.
</risks>
