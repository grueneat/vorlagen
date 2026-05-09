# RESEARCH — #20: V1 "Hero Band" layout for `infostand-tent-card-a5-quer`

**Status:** synthesized from two parallel research dimensions (codebase + pitfalls). HIGH confidence — every claim file:line-traced to current main; build pipeline verified live (build.py runs clean, smoke 9/9 ✓, structural_check 0 errors/6 skipped/15 pass). ISSUE.md contains 4 errata that this RESEARCH corrects so the planner can produce zero-ambiguity tasks.

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for line-level evidence and arithmetic.

---

## Executive summary

ISSUE.md prescribes V1 "Hero Band" — Dunkelgrün hero-band at the apex side of each panel (Logo + Headline 26pt White + Pay-off 16pt Italic Gelb), full-bleed Photo-Backing + photo, white Bullets+Termine zone, Hellgrün Footer-Strip with CTA-Footer + Impressum White. First multi-panel template, establishes the rotation contract reused in #21 (kandidat-falzflyer).

Both research dimensions converged on **4 ISSUE.md errata corrections** plus several layout fits to lock:

1. **`Group(rotation=180, around=(148.5, 52.5))` does NOT exist.** No `Group` primitive in the DSL. Implement rotation contract via two builder helpers `_panel_de(...)` and `_panel_en(...)` that produce identical local-coord primitives; the build then emits Panel A directly (rotation_deg=0) and Panel B via per-frame `rotation_deg=180` + bbox-corner SLA math (existing build.py pattern).
2. **The spec's "rotate Panel A" is inverted from the existing convention.** Existing build.py + smoke test rotate Panel B (EN, bottom half). Following ISSUE.md verbatim breaks the smoke test (`test_panel_a_frames_not_rotated` and `test_panel_b_frames_rotated_180`). Geometric truth for valley-fold tent-card with apex at table: bottom half of flat sheet has text reading upside-down on the un-folded sheet. **Lock: Panel B rotated, Panel A not.**
3. **`inside` constraints with mixed rotation states FAIL.** ISSUE.md's CONSTRAINTS list has `inside("logo_panel_a", "hero_band_a")` etc. Logo Panel A is unrotated (Panel A convention) AND Hero-Band Panel A is unrotated (Polygon, rectangle = no visual rotation needed) → these PASS in Panel A. But the symmetric Panel B versions would fail. **Lock: declare `inside` only for intra-Panel-A. Cross-panel = `mirrored_y` on Polygons + `same_size` + `same_style`.**
4. **Snake_case anname stubs in ISSUE.md don't match real annames.** Real annames are German title-case with parens (`"Logo Grüne (panel A)"`, `"Hero-Band Panel A"`). Constraint resolver matches on exact string. **Lock: rewrite all CONSTRAINTS targets with real annames.**

Plus 5 layout-fit decisions:
- **QR D1:** keep at 17×17 mm (D1-conformant 0.515 mm/module), position at (12, 78) inside white zone — NOT inside footer-strip. Footer-strip houses CTA-Footer + Impressum only.
- **Bullets fit:** 2 bullets (not 3) at fontsize 11 linesp 14.3, x=32..142 (cleared of QR).
- **Termine fit:** 2 lines at fontsize 9 linesp 11.7, drop "Nächste Termine" header.
- **Photo aspect:** use post-#24 `library.inject_into_frame` with live frame dims; manifest's `crop_focus: [0.50, 0.55]` produces the 9:1 horizontal slab through table+people.
- **brand_overrides:** REMOVE 3 (`logo_size_3M`, `image_text_overlap`, `image_fills_frame`); KEEP 3 (`line_spacing_0.9`, `visual_adjacency_drift`, `band_consistency`) with updated reasons.

---

## User Constraints (from CONTEXT.md)

**No CONTEXT.md found** — no separate discussion artifact. ISSUE.md is the only upstream input. The user's standing directive ("in a fully automated way, without discussion") means RESEARCH.md must lock all open questions so the planner can produce zero-ambiguity tasks. This RESEARCH does so via the locked-decisions table below.

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **Rotation contract via `_panel_de(...)` and `_panel_en(...)` builder helpers**, NOT a `Group` primitive (which doesn't exist). Each helper returns a list of primitives in panel-LOCAL coords (as if the panel were upright). Wrap-step is the build's responsibility: Panel A primitives placed directly with rotation_deg=0; Panel B Text/Image frames receive rotation_deg=180 + bbox-corner SLA math (`x = x_local_mirror + w; y = y_local_mirror + h` where `_mirror = 210 − local − size`); Panel B Polygons (rectangles, no visual rotation needed) get rotation_deg=0 with `y = 210 − local_y − h`, `x = local_x` directly. | Codebase agent §5; pitfalls P0.1, P10. No `Group` import path in `tools/sla_lib/builder/__init__.py`; existing build.py already uses per-frame rotation_deg=180 with bbox-corner math. |
| 2 | **Panel B is the rotated half** (existing convention; matches valley-fold tent-card with apex at table). Smoke test contract preserved: `test_panel_a_frames_not_rotated` + `test_panel_b_frames_rotated_180` stay. Spec's "Panel A rotated" wording is geometrically backwards relative to the existing-and-correct convention. | Codebase agent §1; pitfalls P0.2. Verified by valley-fold geometry derivation. |
| 3 | **Real annames in CONSTRAINTS** (not snake_case stubs). Production annames: `"Hero-Band Panel A"`, `"Hero-Band Panel B"`, `"Photo-Backing Panel A"`, `"Photo-Backing Panel B"`, `"Footer-Strip Panel A"`, `"Footer-Strip Panel B"`, `"Logo Grüne (panel A)"`, `"Logo Grüne (panel B)"`, `"Headline Panel A"`, `"Headline Panel B"`, `"Pay-off Panel A"`, `"Pay-off Panel B"`, `"Hintergrund-Mitmachen"` (Panel A only — see decision #4 for Panel B), `"Body Panel A"`, `"Body Panel B"` (kept anname for Bullets text frame for backwards compat with smoke test), `"Termine Panel A"`, `"Termine Panel B"`, `"QR-Code (mitmachen, panel A)"`, `"QR-Code (mitmachen, panel B)"` (NEW Panel B QR added in V1), `"CTA-Footer Panel A"`, `"CTA-Footer Panel B"`, `"Impressum (Tent)"` (Panel A; existing anname kept), `"Impressum (Tent, panel B)"` (NEW). | Pitfalls P0.4; constraint resolver `_to_anname` at `constraints.py:74-90`. |
| 4 | **Cross-panel constraints limited to: `mirrored_y` on the 6 Polygons (3 per panel), `same_size` on the same Polygon pairs, `same_style` on text-frame style pairs.** No cross-panel `inside`/`aligned_below`/`same_y`/`same_x` (rotation-state mismatch makes raw bbox math invalid). Intra-Panel-A: full set of `inside`, `same_y`, `aligned_below` available. Intra-Panel-B: ONLY between same-rotation-state frames (e.g. `same_y(Bullets Panel B, Termine Panel B)` works since both are ROT=180; `inside(Logo Panel B, Hero-Band Panel B)` fails since Logo is ROT=180 and Hero-Band is ROT=0). | Pitfalls P0.3; `_InsideConstraint.check` at `constraints.py:198-223` uses raw bbox math. |
| 5 | **QR remains 17×17 mm at (12, 78, 17, 17) on Panel A** — NOT inside Footer-Strip. D1-conformant: 17/33 ≈ 0.515 mm/module ✓ (QR is v4-H per `samples/manifest.yml`). Footer-Strip houses CTA-Footer + Impressum only. README.md documents this rationale per ISSUE.md acceptance criterion. Symmetric Panel B QR at mirrored coords with rotation_deg=180. | Pitfalls P0/P15; QR PNG verified 410×410 px = (33+8)×10 → v4. |
| 6 | **Bullets at fontsize 11 linesp 14.3 (= 1.3 × 11; body convention)**, 2 short bullets. x=32..142 (w=110), y=78..94 (h=16). Cleared of QR's x-range (12..29). Drop one bullet from current 3-bullet text (combine "Erneuerbare Energie + Wärmepumpe" or just remove "Wärmepumpe statt Gas" — content stewards choose at execution time; either works). | Pitfalls P15 fit arithmetic. |
| 7 | **Termine at fontsize 9 linesp 11.7**, 2 lines max. Drop "Nächste Termine" header from current text — keep 2 date bullets compactly. x=152..285 (w=133), y=78..94 (h=16). Symmetric Panel B Termine. | Pitfalls P15 fit arithmetic. |
| 8 | **Photo via post-#24 `library.inject_into_frame` pattern** in `build_preview()`. Build split: `build_doc()` aliased to `build_template()` for round-trip stability + structural_check; `build_preview()` wraps it and applies INJECT_MAP. Map: `{"Hintergrund-Mitmachen": "kontext_infostand_szene"}` (Panel A only — Panel B photo is a duplicate ImageFrame with the same library binding via build_preview symmetric loop, OR an independent `Hintergrund-Mitmachen Panel B` anname; lock the latter for clarity). | Codebase agent §13; #19 precedent (commit c116bf6). |
| 9 | **ParaStyle MUTATION pattern** (per #19 precedent), NOT parallel `*-on-green` styles (per #17/#18 precedent). MUTATE `tent/headline` (fontsize 36→26, linesp 40→23.4, fcolor Dunkelgrün→White), `tent/body` (12pt linesp 15.6, fcolor stays Black), `tent/termine` (10pt→9pt linesp 11.7), `tent/impressum` (5→6pt linesp 7.8 fcolor Black→White align→2-right). NEW `tent/payoff` (Vollkorn Black Italic 16pt linesp 14.4 fcolor=Gelb). NEW `tent/cta-footer` (Gotham Narrow Bold 11pt linesp 14 fcolor=White). DROP `tent/cta` (CTA Panel A frame deleted; new `CTA-Footer Panel A` uses `tent/cta-footer`). | Pitfalls P3 + locked precedent #19. |
| 10 | **brand_overrides cleanup** at T07 (post-V1 verification): REMOVE `brand:logo_size_3M` (38mm ≈ 3M ± 0.2mm in tol), REMOVE `brand:image_text_overlap` (V1 text fully inside polygons), REMOVE `brand:image_fills_frame` (post-#24 inject_into_frame fills exactly). KEEP with reason update: `brand:line_spacing_0.9` (body 1.3× rationale), `brand:visual_adjacency_drift` (intra-Panel-B combinatorial warnings), `brand:band_consistency` (no body_block_margins; defer). | Pitfalls P5–P9, P16. |
| 11 | **Smoke test ADDITIONS, not full rewrite.** Existing 9 assertions stay (PASS post-V1) EXCEPT `test_impressum_above_fold` (relax bound from ≤102 to ≤105 — Impressum sits inside Footer-Strip which extends to apex). ADD assertions: Hero-Band/Photo-Backing/Footer-Strip Polygons present (× both panels) with `LAYER="0"` and correct fills; Pay-off Panel A frame present; Logo asset is `gruene-weiss.png`; Falz layer integrity (only `Mittelfalz (horizontal)` on LAYER="3"). | Pitfalls P11, P13; codebase agent §9. |
| 12 | **Spec rewrite mandatory** — `templates/_specs/infostand-tent-card-a5-quer.md` is already drifted from existing build.py (Panel B coords mismatch). V1 must rewrite ASCII layout diagram, both slot tables, ParaStyle list, Constraints prose, Layout-Philosophie. Pattern: follow #19 spec rewrite (commit c116bf6 `templates/_specs/themen-plakat-a3-quer.md`). | Codebase agent §12. |
| 13 | **NEW `tools/sla_lib/tests/test_infostand_tent_card_geometry.py`** with ≥12 invariant-pinning assertions (#23 / #18 / #19 pattern). Pin RELATIONSHIPS not coordinates. Targeted invariants: cross-panel Polygon mirror around y=105 (3 pairs); Panel-A `inside` containment (Logo/Headline/Pay-off in Hero-Band; Photo in Photo-Backing; CTA-Footer/Impressum in Footer-Strip); intra-Panel `same_y(Bullets, Termine)`; logo width = 38 mm (3M ± 0.5); Falz layer integrity (only one PAGEOBJECT on LAYER=3); rotation-state contract (Panel A polygons ROT=0, Panel B Text/Image frames ROT=180). Calls `build_template()` (clean doc) — avoids photo-injection IO during tests. TOL_MM=0.6. | Codebase agent §16; pitfalls P11, P13; #19 precedent. |
| 14 | **Atomic-PR ordering: 9 tasks T01..T09.** T01 ParaStyles + ci_overrides update; T02 build_template/build_preview split + INJECT_MAP scaffold; T03 V1 Panel A layout (frames + polygons via _panel_de helper, no rotation); T04 V1 Panel B layout (rotated via _panel_en helper); T05 V1 CONSTRAINTS list (replaces existing 5-entry); T06 regen template.sla + render-gallery + meta.yml SHA; T07 brand_overrides cleanup; T08 smoke test additions + spec rewrite + geometry tests + README QR-decision documentation; T09 brief §10 + EXECUTION + close. **Codex iter1/iter2 SKIPPED** (single-page A4 quer; no historical Codex pattern for tent-card; `brand:image_fills_frame` is the primary detector for the regression class). | Pitfalls P17; #19 precedent (locked decision #6). |
| 15 | **Logo asset: `shared/logos/gruene-weiss.png`**. Verify existence at T01 environment probe; if missing, fallback to `shared/logos/gruene-logo-bund-dunkel.png` and document deviation. (Asset is mentioned in #17/#18 V1 patterns and ls earlier shows shared/logos/ tree present.) | Pitfalls P14. |
| 16 | **Codex visual review SKIPPED** for this implementation. Single-page A4 quer; Brand-rule registry already covers regression classes. Trigger Codex follow-up only if visual artifacts surface in T06 page-01.png. | Pitfalls P17; #19 precedent. |

---

## Scope changes vs. ISSUE.md

| ISSUE.md item | Status | Why |
|---|---|---|
| `Group(rotation=180, around=(148.5, 52.5))` wrap | **DROPPED** — replaced by `_panel_de`/`_panel_en` helpers (locked #1). |
| "Wrap Panel A in rotation" | **INVERTED** — Panel B is rotated (locked #2). |
| `inside("logo_panel_a", "hero_band_a")` etc. (snake_case) | **REWRITE** with real annames (locked #3); cross-panel `inside` DROPPED (locked #4). |
| Bullets/Termine `h=16, fontsize 12, 3 bullets` | **REVISE** — 2 bullets at fontsize 11 / 2 lines termine at fontsize 9 (locked #6, #7). |
| QR `w 17→8` (footer-tiny) | **DROPPED** — fails D1. Keep 17×17 mm in white zone (locked #5). |
| Spec rewrite | **ADDED** in scope per locked #12 (issue silent on this). |
| Geometry tests | **ADDED** in scope per locked #13. |
| README.md QR documentation | **EXPLICIT** per locked #5 (issue mentions "documented in README.md" as AC). |

---

## Codebase Analysis — interfaces

<interfaces>

### Constraint factories (`tools/sla_lib/builder/constraints.py`) — V1 uses

```python
# All factories take *targets as anname strings (or frame instances; .anname extracted).
# tolerance_mm default 0.5; name optional (auto-generated from kind+targets if blank).
def same_y(*targets, tolerance_mm=0.5, name="") -> Constraint     # L399
def same_x(*targets, tolerance_mm=0.5, name="") -> Constraint     # L408
def same_size(*targets, axis="both"|"w"|"h", tolerance_mm=0.5, name="") -> Constraint   # L417
def mirrored_x(left, right, axis_mm, tolerance_mm=0.5, name="") -> Constraint   # L433  -- vertical mirror line at x=axis_mm
def mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="") -> Constraint   # L443  -- horizontal mirror line at y=axis_mm; uses (a.y_mm + a.h_mm/2 + b.y_mm + b.h_mm/2) / 2 == axis_mm
def inside(child, parent, tolerance_mm=0.5, name="") -> Constraint    # L453  -- raw-bbox containment; FAILS on rotated/unrotated mismatch
def aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="") -> Constraint    # L507  -- has rotation guard returning warning at L337-343
def same_style(*targets, name="") -> Constraint   # L481  -- rotation-invariant
def distance_y(a, b, equals, tolerance_mm=0.5, name="") -> Constraint    # L489
def distance_x(a, b, equals, tolerance_mm=0.5, name="") -> Constraint    # L498
# Resolver matches on `anname` exactly (case-sensitive).
# NO Group, NO same_y_top, NO same_x_center, NO mirrored_around_bbox-aware helpers exist.
```

### Primitive surface (`tools/sla_lib/builder/primitives.py`)

```python
# All frames inherit _Frame at primitives.py:434
@dataclass
class _Frame:
    x_mm: float = 0          # SLA XPOS in mm; for ROT≠0 represents bbox top-left in scratch space (= visual bottom-right corner of pre-rotation rect for ROT=180)
    y_mm: float = 0          # SLA YPOS in mm; same convention as x_mm
    w_mm: float = 50
    h_mm: float = 30
    rotation_deg: float = 0  # ROT in SLA; 180 = bbox visually upside-down with XPOS/YPOS at original bottom-right
    layer: int = 2           # 0=Hintergrund, 1=Bilder, 2=Text, 3=Falz (per build.py LAYER_* constants)
    anname: str = ""
    # ... soft_shadow, custom_path, fill_rule, corner_radius_mm, clip_edit, xpos_pt/ypos_pt overrides, is_full_bleed

@dataclass
class TextFrame(_Frame):
    style: str = ""          # ParaStyle name reference
    runs: list[Run] = ...
    layer: int = 2           # default Text
    # ... col_count, col_gap_mm, vertical_text_align, fcolor (override style), text_attrs, etc.

@dataclass
class ImageFrame(_Frame):
    inline_image_data: Optional[str] = None   # base64 zlib-compressed JPEG/PNG bytes (set by pack_inline_image)
    inline_image_ext: Optional[str] = None    # "jpg" | "png"
    scale_type: int = 0      # 0=ScaleAuto fit-to-frame; 1=Manual
    ratio: int = 1           # 1=preserve aspect, 0=stretch
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    layer: int = 1           # default Bilder

@dataclass
class Polygon(_Frame):
    fill: str = "Black"      # "Dunkelgrün" | "Hellgrün" | "Gelb" | "Magenta" | "White" | None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0           # default Hintergrund
    shape: str = "rectangle" # 'rectangle' | 'ellipse'
    fill_shade: int = 100

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Returns (base64_zlib_data, ext) for ImageFrame.inline_image_data/inline_image_ext."""
```

### Library helper (`tools/sla_lib/builder/library.py:436-500`)

```python
def inject_into_frame(frame, img: LibraryImage, *, target_w_mm: float, target_h_mm: float,
                       dpi: int = 300, quality: int = 80, apply_watermark: bool = True) -> None:
    """Crop img to (target_w_mm, target_h_mm) aspect via crop_for_frame
    (honours manifest crop_focus); pack as inline JPEG; set frame.scale_type=0.
    Watermark band re-stamped on cropped output.
    """

def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]:
    """Look up id in shared/sample-images/manifest.yml; return LibraryImage with .bytes / .crop_focus_x / .crop_focus_y."""

def crop_for_frame(img, *, target_w_mm, target_h_mm, dpi=300, quality=80,
                    apply_watermark=True) -> bytes:
    """Centre-crop to (target_w_mm, target_h_mm) aspect using img.crop_focus_x/y; re-stamp watermark; encode JPEG."""
```

### BRAND_CONSTRAINTS registry — exactly 16 rules (post-#25)

`tools/sla_lib/builder/brand_constraints.py:1525-1680`:
```
1.  brand:color_palette
2.  brand:font_family
3.  brand:line_spacing_0.9
4.  brand:hl_sl_distance_x2
5.  brand:logo_size_3M
6.  brand:text_on_green
7.  brand:bleed_3mm
8.  brand:wahlkreuz_colored_bg
9.  brand:inside_page
10. brand:spine_safety
11. brand:bleed_coverage
12. brand:image_text_overlap
13. brand:cover_extent_match
14. brand:visual_adjacency_drift
15. brand:image_fills_frame      # Issue #24
16. brand:band_consistency       # Issue #25
```

#20 adds NO new BrandRule. Registry stays at 16.

### `Document` and `add_para_style` / `add_color`  / `add_master` / `add_page`

```python
# tools/sla_lib/builder/document.py
class Document:
    def __init__(self, *, brand: Brand, title: str, template_id: str, author: str = "...",
                 facing_pages: bool = False, layers: list[DocumentLayer] = None): ...
    def add_color(self, name: str, *, cmyk: tuple[int,int,int,int] = None,
                   rgb: tuple[int,int,int] = None, spot: bool = False) -> None: ...
    def add_para_style(self, ps: ParaStyle) -> None: ...
    def add_master(self, *, name, size, bleed_mm, margins_mm) -> Master: ...
    def add_page(self, *, size, bleed_mm, margins_mm, master) -> Page: ...
    def save(self, path: Path | str) -> None: ...
    pages: list[Page]
```

### Existing build.py contract (`templates/infostand-tent-card-a5-quer/build.py`)

```python
HERE = Path(__file__).resolve().parent
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_FALZ = 3
TRIM_W_MM = 297.0; TRIM_H_MM = 210.0; BLEED_MM = 3.0; FOLD_Y_MM = 105.0

def build_doc() -> Document:
    """V0 — single function. V1 will rename to build_template + add build_preview wrapper."""

def build(out_path: str | Path = HERE / "template.sla") -> Path: ...

# Module-level CONSTRAINTS list (5 entries currently) — read by structural_check.
CONSTRAINTS = [...]
```

### Existing meta.yml (`templates/infostand-tent-card-a5-quer/meta.yml`)

```yaml
id: infostand-tent-card-a5-quer
version: 0.1.0
title: Infostand-Tent-Card A5 quer
format: A4
orientation: landscape
pages: 1
preview_dpi: 100
audience: [bezirksgruppe, ortsgruppe, infostand-helfer]
build:
  script: build.py
  output: template.sla
previews_for_sla: <SHA hash, auto-bumped by render-gallery>
brand_overrides:        # 6 entries currently
  - id: brand:line_spacing_0.9 (KEEP)
  - id: brand:logo_size_3M       (REMOVE post-V1)
  - id: brand:visual_adjacency_drift (KEEP)
  - id: brand:image_text_overlap (REMOVE post-V1)
  - id: brand:image_fills_frame  (REMOVE post-V1)
  - id: brand:band_consistency   (KEEP)
ci_overrides:
  non_ci_styles: [tent/headline, tent/body, tent/impressum]   # extend to 6 V1 styles
  non_ci_colors: [Falz]
  non_ci_layers: [Falz]
slots: { ... 6 entries currently — V1 extends to ≥18 ... }
example_pages: [{num: 1, label: "Flach (vor dem Falzen) — Panel A oben, Panel B unten 180°"}]
preflight: { bleed_mm: 3, fold_mm: [105], cmyk_only: true, min_image_dpi: 300 }
```

### Smoke test contract (`templates/_smoke/test_infostand_tent_card_a5_quer.py`)

```python
# 9 existing tests — V1 ADDITIONS not full rewrite (locked decision #11):
class InfostandTentCardSmokeTests(unittest.TestCase):
    def test_page_count(self): ...                          # PASS post-V1
    def test_trim_dimensions(self): ...                     # PASS
    def test_falz_layer_present_not_printable(self): ...    # PASS
    def test_falz_color_document_local_spot(self): ...      # PASS
    def test_mittelfalz_polygon_at_y_105(self): ...         # PASS
    def test_four_main_text_frames_present(self): ...       # PASS (V1 keeps Headline/Body Panel A/B annames)
    def test_panel_b_frames_rotated_180(self): ...          # PASS (V1 keeps convention)
    def test_panel_a_frames_not_rotated(self): ...          # PASS
    def test_impressum_above_fold(self): ...                # FAIL post-V1 — relax to ≤105 (locked #11)
    # ADD: test_hero_band_polygons_present, test_photo_backing_polygons_present,
    #      test_footer_strip_polygons_present, test_payoff_panel_a_present,
    #      test_logo_asset_is_gruene_weiss, test_falz_layer_integrity (only Mittelfalz on LAYER=3)
```

### Frame inventory current → V1 (TARGET)

| anname | Current SLA coords | V1 SLA coords | Notes |
|---|---|---|---|
| `Logo Grüne (panel A)` | (12, 10, 36, 32) ROT=0 | (12, 6, 38, 30) ROT=0 | Asset `gruene-logo-bund-dunkel.png` → `gruene-weiss.png` |
| `Headline Panel A` | (62, 12, 223, 24) ROT=0 | (55, 9, 230, 18) ROT=0 | style=tent/headline (mutated to 26pt White) |
| **`Pay-off Panel A`** (NEW) | — | (55, 27, 230, 8) ROT=0 | style=tent/payoff text="Konkret. Lokal. Jetzt." |
| **`Hero-Band Panel A`** (NEW Polygon) | — | (−3, −3, 303, 42) ROT=0 fill=Dunkelgrün layer=0 | |
| **`Photo-Backing Panel A`** (NEW Polygon) | — | (−3, 39, 303, 33) ROT=0 fill=Dunkelgrün layer=0 | |
| `Hintergrund-Mitmachen` | (12, 44, 44, 33) ROT=0 inline JPEG | (0, 39, 297, 33) ROT=0 inline JPEG (via build_preview INJECT_MAP) | Aspect 9:1 from 1.5:1 source via inject_into_frame + crop_focus |
| `Body Panel A` (= Bullets) | (62, 44, 223, 26) ROT=0 | (32, 78, 110, 16) ROT=0 | style=tent/body (mutated 12pt linesp 15.6); 2 bullets (drop 1) |
| `Termine Panel A` | (125, 68, 160, 26) ROT=0 | (152, 78, 133, 16) ROT=0 | style=tent/termine (mutated 9pt linesp 11.7); 2 lines, drop "Nächste Termine" header |
| `QR-Code (mitmachen, panel A)` | (12, 80, 17, 17) ROT=0 | (12, 78, 17, 17) ROT=0 | Same asset/size; 2mm shift up |
| `CTA Panel A` (DELETE in V1) | (62, 68, 60, 6) ROT=0 | — | Functionally replaced by Pay-off + CTA-Footer |
| **`Footer-Strip Panel A`** (NEW Polygon) | — | (−3, 95, 303, 10) ROT=0 fill=Hellgrün layer=0 | |
| **`CTA-Footer Panel A`** (NEW) | — | (12, 97, 200, 6) ROT=0 | style=tent/cta-footer text="gruene-noe.at/mitmachen" |
| `Impressum (Tent)` | (35, 96, 257, 4) ROT=0 | (215, 97, 80, 6) ROT=0 align=2-right | style=tent/impressum (mutated 6pt linesp 7.8 White right-align) |
| `Mittelfalz (horizontal)` | y=105 layer=Falz | y=105 layer=Falz | Unchanged (TableTentFold block) |

Panel B frames mirror Panel A around y=105. Polygons stay rotation_deg=0 (rectangles); Text/Image frames are rotation_deg=180 with bbox-corner SLA math:
- For each Text/Image frame on Panel A at local (x_a, y_a, w, h): Panel B SLA = (x_a + w, 210 − y_a, w, h, ROT=180). E.g. Logo Panel A (12, 6, 38, 30) → Logo Panel B (50, 204, 38, 30, ROT=180).
- For each Polygon on Panel A at (x_a, y_a, w, h): Panel B SLA = (x_a, 210 − y_a − h, w, h, ROT=0). E.g. Hero-Band Panel A (−3, −3, 303, 42) → Hero-Band Panel B (−3, 171, 303, 42, ROT=0).

</interfaces>

---

## V1 ParaStyles (planner: pass these verbatim to T01)

```python
# MUTATE existing
doc.add_para_style(ParaStyle(
    name="tent/headline",
    font="Vollkorn Black Italic", fontsize=26, linesp=23.4, linesp_mode=0,
    align=0, fcolor="White", language="de",
))
doc.add_para_style(ParaStyle(
    name="tent/body",
    font="Gotham Narrow Book", fontsize=12, linesp=15.6, linesp_mode=0,
    align=0, fcolor="Black", language="de",
))
doc.add_para_style(ParaStyle(
    name="tent/termine",
    font="Gotham Narrow Book", fontsize=9, linesp=11.7, linesp_mode=0,
    align=0, fcolor="Black", language="de",
))
doc.add_para_style(ParaStyle(
    name="tent/impressum",
    font="Gotham Narrow Book", fontsize=6, linesp=7.8, linesp_mode=0,
    align=2, fcolor="White", language="de",
))
# NEW
doc.add_para_style(ParaStyle(
    name="tent/payoff",
    font="Vollkorn Black Italic", fontsize=16, linesp=14.4, linesp_mode=0,
    align=0, fcolor="Gelb", language="de",
))
doc.add_para_style(ParaStyle(
    name="tent/cta-footer",
    font="Gotham Narrow Bold", fontsize=11, linesp=14, linesp_mode=0,
    align=0, fcolor="White", language="de",
))
# REMOVE: tent/cta (delete the call to add_para_style for it)
```

ci_overrides.non_ci_styles becomes:
```yaml
non_ci_styles:
  - "tent/headline"
  - "tent/body"
  - "tent/termine"
  - "tent/impressum"
  - "tent/payoff"
  - "tent/cta-footer"
```

---

## V1 CONSTRAINTS list (planner: pass verbatim to T05)

```python
CONSTRAINTS = [
    # ── Panel A intra-panel containment (rotation_deg=0 throughout — raw bbox math works) ──
    inside("Logo Grüne (panel A)", "Hero-Band Panel A",
           name="logo_in_band_a"),
    inside("Headline Panel A", "Hero-Band Panel A",
           name="headline_in_band_a"),
    inside("Pay-off Panel A", "Hero-Band Panel A",
           name="payoff_in_band_a"),
    inside("Hintergrund-Mitmachen", "Photo-Backing Panel A",
           name="photo_in_backing_a"),
    inside("CTA-Footer Panel A", "Footer-Strip Panel A",
           name="cta_footer_in_strip_a"),
    inside("Impressum (Tent)", "Footer-Strip Panel A",
           name="impressum_in_strip_a"),
    # ── Panel A intra-panel adjacency ──
    aligned_below("Photo-Backing Panel A", "Hero-Band Panel A", gap_mm=0.0,
                  name="photo_backing_below_hero_band_a"),
    same_x("Hero-Band Panel A", "Photo-Backing Panel A", "Footer-Strip Panel A",
           name="full_bleed_polygons_share_left_x_a"),
    same_y("Body Panel A", "Termine Panel A",
           name="bullets_termine_baseline_a"),
    same_size("Body Panel A", "Termine Panel A", axis="h",
              name="bullets_termine_height_a"),
    # ── Panel B intra-panel: only same-rotation-state pairs ──
    same_y("Body Panel B", "Termine Panel B",
           name="bullets_termine_baseline_b"),
    same_size("Body Panel B", "Termine Panel B", axis="h",
              name="bullets_termine_height_b"),
    # ── Cross-panel mirror at apex (Polygons only — both rotation_deg=0) ──
    mirrored_y("Hero-Band Panel A", "Hero-Band Panel B", axis_mm=105.0,
               name="hero_band_mirror_at_apex"),
    mirrored_y("Photo-Backing Panel A", "Photo-Backing Panel B", axis_mm=105.0,
               name="photo_backing_mirror_at_apex"),
    mirrored_y("Footer-Strip Panel A", "Footer-Strip Panel B", axis_mm=105.0,
               name="footer_strip_mirror_at_apex"),
    same_size("Hero-Band Panel A", "Hero-Band Panel B",
              name="hero_bands_same_size"),
    same_size("Photo-Backing Panel A", "Photo-Backing Panel B",
              name="photo_backings_same_size"),
    same_size("Footer-Strip Panel A", "Footer-Strip Panel B",
              name="footer_strips_same_size"),
    # ── Cross-panel style consistency (rotation-invariant) ──
    same_style("Headline Panel A", "Headline Panel B",
               name="hero_headline_style"),
    same_style("Pay-off Panel A", "Pay-off Panel B",
               name="payoff_style"),
    same_style("Body Panel A", "Body Panel B",
               name="bullets_style"),
    same_style("Termine Panel A", "Termine Panel B",
               name="termine_style"),
    same_style("CTA-Footer Panel A", "CTA-Footer Panel B",
               name="cta_footer_style"),
    same_style("Impressum (Tent)", "Impressum (Tent, panel B)",
               name="impressum_style"),
]
```

22 constraints (3 cross-panel mirrors + 3 cross-panel sizes + 6 style + 6 panel-A inside + 1 aligned_below + 1 same_x + 2 same_y/same_size baseline). All file:line evidence in `research/codebase.md` §5.

---

## Standard Stack

| Item | Value |
|---|---|
| Python | 3.13.5 (verified) |
| Tests (geometry + smoke) | `python3 -m unittest tools.sla_lib.tests.test_infostand_tent_card_geometry templates._smoke.test_infostand_tent_card_a5_quer` |
| Build | `python3 templates/infostand-tent-card-a5-quer/build.py` |
| Regen | `bin/render-gallery infostand-tent-card-a5-quer --skip-visual-diff` (auto-bumps SHA in meta.yml; mirrors site/public) |
| Audit | `PYTHONPATH=tools bin/audit-alignment infostand-tent-card-a5-quer` |
| structural_check | `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer` (and `--all`) |
| Stale check | `bin/check-stale-previews` |
| New deps | none |

---

## Don't Hand-Roll

- All Constraint factories from #14 + helpers from #22/#23 — use them; do NOT invent `same_x_center`, `same_y_top`, `mirrored_around_bbox`, `Group`, `aspect_fill`.
- `library.inject_into_frame` — use it post-#24 with live `frame.w_mm`/`frame.h_mm`; do NOT call `crop_for_frame` + `pack_inline_image` directly.
- `bin/render-gallery <slug> --skip-visual-diff` — regenerates template.sla + page-NN.png + preview.pdf + meta.yml SHA + site/public mirror in one command.
- ParaStyle MUTATION pattern (#19 precedent) — do NOT create parallel `*-on-green` siblings.
- Smoke test ADDITION pattern — do NOT rewrite from scratch; existing assertions stay (with one bound relaxation).

---

## Common Pitfalls (consolidated; see `research/pitfalls.md` for full taxonomy)

### Must-handle (HIGH severity)
1. **`Group` doesn't exist** — use `_panel_de`/`_panel_en` helpers (locked #1).
2. **Spec inverts rotation convention** — Panel B is rotated, not Panel A (locked #2).
3. **`inside` with mixed rotation states fails** — declare only intra-Panel-A; cross-panel = mirrored_y on Polygons (locked #4).
4. **Snake_case anname stubs** — use real annames (locked #3).
5. **Photo aspect 9:1 from 1.5:1** — use INJECT_MAP + crop_focus (locked #8).
6. **Falz layer integrity** — explicit `layer=LAYER_HINTERGRUND` on every V1 Polygon; geometry test asserts (locked #13).
7. **Smoke test contract drift** — only relax `test_impressum_above_fold` bound; keep panel-rotation assertions (locked #11).

### Worth knowing (MEDIUM)
8. **brand_overrides cleanup** — REMOVE 3, KEEP 3 (locked #10).
9. **ParaStyle MUTATION not parallel** — smaller diff, no deprecated styles (locked #9).
10. **Bullets/Termine fontsize fit** — 11pt 2-bullet body, 9pt 2-line termine (locked #6, #7).
11. **QR D1 conformance** — keep at 17×17 in white zone, NOT inside footer (locked #5).

### Informational (LOW)
12. **Logo asset** `gruene-weiss.png` — verify existence at T01; fallback documented (locked #15).
13. **Codex review SKIPPED** — single-page A4 quer; brand:image_fills_frame is primary detector (locked #16).
14. **No new BrandRule** added — registry stays at 16.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python | build.py | ✓ | 3.13.5 | — |
| `lxml.etree` | smoke test SLA parsing | ✓ | (system) | — |
| `Pillow` (PIL) | library.inject_into_frame, samples QR | ✓ | (system) | — |
| `shared/sample-images/manifest.yml` + `kontext_infostand_szene` asset | Photo Hintergrund-Mitmachen | ✓ | 1536×1024 | — |
| `shared/logos/gruene-weiss.png` | Logo asset | ✓ assumed (T01 verifies) | — | `gruene-logo-bund-dunkel.png` |
| `samples/qr-mitmachen.png` | QR-Code | ✓ | 410×410 v4-H | — |
| `bin/render-gallery` | Regen artifacts | ✓ | (verified ls) | — |
| `bin/audit-alignment` | Optional audit | ✓ (rotation-skip aware) | — | — |
| `tools/sla_lib/builder/*` | Builder DSL | ✓ | post-#25 | — |

---

## Project Constraints (from CLAUDE.md / MEMORY.md)

The user's MEMORY.md (auto-context) is unrelated to this issue (covers Austender procurement, KEBA Wärmepumpe, Music Assistant, Pi infrastructure, Psychotherapie-site, Issue System tooling). No project-level CLAUDE.md found at repo root.

Standing user directives applicable to this work:
- **No "claude" or AI attribution** in commits, code, files (per `feedback_no_claude_attribution.md`).
- **Issue artifacts preserved** (no deletes; archive when done — per `feedback_preserve_issue_artifacts.md`).
- **Reviews must read code themselves** (no diffs in prompts — per `feedback_review_no_code_in_prompt.md`). Plan tasks should not embed code snippets the executor must paste; instead reference file:line locations.
- **Working over theoretical** (per `feedback_working_over_theoretical.md`). Lock practical decisions; don't propose refactors not needed for V1.

---

## Sources

### HIGH confidence
- `tools/sla_lib/builder/constraints.py:165-225, 318-358, 399-518` — constraint factory implementations
- `tools/sla_lib/builder/__init__.py:73-134` — public exports (NO `Group`, NO `aspect_fill`)
- `tools/sla_lib/builder/primitives.py:434-905` — _Frame.rotation_deg, ImageFrame, Polygon, TextFrame
- `tools/sla_lib/builder/library.py:436-500` — inject_into_frame
- `tools/sla_lib/builder/brand_constraints.py:1525-1680` — BRAND_CONSTRAINTS (16 rules)
- `templates/infostand-tent-card-a5-quer/build.py` — current 416-line state (full read)
- `templates/infostand-tent-card-a5-quer/meta.yml` — 6 brand_overrides + 3 ci_overrides + 6 slots
- `templates/_smoke/test_infostand_tent_card_a5_quer.py` — 9 assertions
- `templates/_specs/infostand-tent-card-a5-quer.md` — current 314 lines (drifted from build.py)
- `shared/sample-images/manifest.yml:237-252` — `kontext_infostand_szene` 1536×1024 + crop_focus[0.50, 0.55]
- `templates/infostand-tent-card-a5-quer/samples/qr-mitmachen.png` — 410×410 PNG (verified PIL)
- `templates/infostand-tent-card-a5-quer/samples/manifest.yml` — QR config (v4 v derived from box_size=10/border=4/410px)
- Live verification: build.py exits 0 ✓; smoke 9/9 ✓; structural_check 0 errors ✓; audit-alignment runs (lots of suggestions in current state).
- Improvements/04-infostand-tent-card.md (workspace root, untracked) — V1 spec source-of-truth
- Improvements/HANDOFF.md (workspace root) — broader rollout context
- Archived #17/#18/#19 RESEARCH.md + PLAN.md + EXECUTION.md (under `.issues/archive/`)

### MEDIUM confidence
- Photo crop visual quality post-9:1-from-1.5:1 (extrapolated from manifest crop_focus + crop_for_frame docstring; visual verification deferred to T06 page-01.png)
- brand_overrides removability predictions (require T05 SLA emission for empirical confirmation)

### LOW confidence (needs validation)
- None — every critical claim verified against current main worktree state.

---

## Metadata

**Confidence breakdown:**
- Codebase: HIGH (every interface file:line traced; build pipeline executed live)
- Standard Stack: HIGH (Python 3.13.5 verified; all binaries present; structural_check 0 errors today)
- Architecture (rotation contract): HIGH (geometry derived; existing convention verified by smoke test)
- Constraints: HIGH (factory implementations read line-by-line; rotation guards mapped)
- Pitfalls: HIGH (P0.1–P0.4 all file:line traced; P5–P9 arithmetic verified; P15 fit math verified)
- Open-question decisions (QR, bullets/termine fit, asset paths): HIGH (locked with arithmetic; ready for plan)

**Research date:** 2026-05-09
**Sub-agents used:** synthesized inline (codebase + pitfalls dimensions; tools-set excludes Agent dispatch — researcher acted as the synthesizer directly)
**Raw research files:** `.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/research/codebase.md`, `.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/research/pitfalls.md`

---

## Suggested PR shape (planner: ~9 tasks T01..T09)

| T# | Title | Files | Verification gate |
|---|---|---|---|
| T01 | feat(infostand-tent-card): V1 ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides extend | build.py (ParaStyles only), meta.yml | build.py runs clean; structural_check still passes (with 5-entry CONSTRAINTS) |
| T02 | refactor(infostand-tent-card): build_template + build_preview split + INJECT_MAP scaffold + build_doc alias | build.py | structural_check unchanged; build emits identical SLA pre-INJECT_MAP populating |
| T03 | feat(infostand-tent-card): V1 Panel A layout — _panel_de helper, Hero-Band/Photo-Backing/Footer-Strip polygons, Pay-off + CTA-Footer frames, Logo asset swap, frame repositioning + delete CTA Panel A | build.py | smoke fails on impressum (expected); audit-alignment shows new V1 frame state |
| T04 | feat(infostand-tent-card): V1 Panel B layout — _panel_en helper with mirror+rotation transform, Panel B Pay-off/CTA-Footer/Impressum/QR added, photo INJECT_MAP entry for Panel B | build.py | structural_check shows panel B mirror constraints once T05 lands |
| T05 | feat(infostand-tent-card): V1 CONSTRAINTS list (22 entries — replaces 5-entry list) | build.py | structural_check 0 errors; all CONSTRAINTS green |
| T06 | chore(infostand-tent-card): regenerate template.sla + render-gallery + meta.yml SHA bump | template.sla, page-01.png, preview.pdf, meta.yml, site/public mirror | check-stale-previews PASS |
| T07 | chore(infostand-tent-card): brand_overrides cleanup (REMOVE logo_size_3M + image_text_overlap + image_fills_frame; UPDATE reasons on line_spacing_0.9 + visual_adjacency_drift + band_consistency) | meta.yml | structural_check 0 errors / 3 skipped (was 6) |
| T08 | test+docs(infostand-tent-card): smoke test additions + spec rewrite + NEW geometry tests + README QR-decision documentation | _smoke/, _specs/, tools/sla_lib/tests/, README.md | All tests pass; spec_check exits 0 |
| T09 | docs(brand,execution): brief §10 session-history row + EXECUTION.md + close issue | shared/brand/DESIGN-SYSTEM-BRIEF.md, .issues/<slug>/EXECUTION.md, ISSUE.md status | issue closes cleanly |

Plus artifact commits (RESEARCH.md ✓, PLAN.md, EXECUTION.md). ~12-13 commits total.

Codex iter1/iter2 SKIPPED (locked decision #16 — single-page A4 quer; not the regression class Codex was used for in #25).

Next: `/issue:plan` turns this RESEARCH into XML-tagged tasks for the executor.

---

## Addendum — Logo asset aspect verification (post-research probe)

**Verified at research time:**
- `shared/logos/gruene-weiss.png` exists (413×118 px, **3.5:1 wordmark "DIE GRÜNEN"**, white-on-transparent).
- `shared/logos/gruene-logo-bund-dunkel.png` exists (499×445 px, ~1.12:1 brushstroke G + DIE-GRÜNEN tag, dunkelgrün-on-transparent).
- **No `bund-weiss` variant exists**; `gruene-weiss.png` is the only white logo.

**Implication for V1 logo frame at (12, 6, 38, 30):**
- Frame aspect 38:30 = 1.27:1; asset aspect 3.5:1.
- With `scale_type=0, ratio=1` (Scribus auto-fit preserving aspect), the wordmark fills frame to **width-bound**: image renders at 38 mm wide × 38/3.5 = 10.86 mm tall, vertically centered in the 30 mm frame (≈9.5mm empty above + 9.5mm below).
- This is **acceptable visual** for V1 (logo at top of hero-band reading "DIE GRÜNEN" wide, with vertical breathing room before Headline+Pay-off start to the right at x=55).
- `brand:logo_size_3M` rule fires on **frame width** (per rule docstring) — frame `w=38` ≈ 3M ± 0.2 mm ✓.

**Caveat:** The visual rendered logo height (10.86 mm) is well below 3M = 37.8 mm. If the brand rule were strict about visual logo height, it would fail. The rule operates on frame.w_mm, so passes; but a future "rendered-extent" rule (or human review) might object. **Lock: accept this for V1; document in README.md alongside QR rationale.** Trigger reconsideration in iter-2 if brand stewardship requests a true 3M-tall logo (which would require either commissioning a `bund-weiss.png` asset OR using a Hellgrün safety panel under the bund-dunkel logo).

**Alternative considered and rejected:** Resize Logo frame to 38×11 mm (exact 3.5:1) so the wordmark fills the frame edge-to-edge with no empty space. Rejected because:
1. The 30 mm frame height matches the ISSUE.md spec literally.
2. The visual breathing room above+below the wordmark balances the Headline+Pay-off stack on the right (which spans y=9..35 = 26 mm tall — comparable to the 30 mm logo frame).
3. Avoids spec drift on a fit-detail; ISSUE.md is the source of truth on coords.

**Constraint impact (planner):** `inside("Logo Grüne (panel A)", "Hero-Band Panel A")` checks frame bbox containment — frame at (12, 6, 38, 30) inside band at (−3, −3, 303, 42) → 30 + 6 = 36 ≤ 42 − 3 = 39 ✓; passes regardless of rendered-image extent.
