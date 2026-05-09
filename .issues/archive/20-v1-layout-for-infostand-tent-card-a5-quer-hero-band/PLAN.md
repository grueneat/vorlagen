# Plan: V1 "Hero Band" layout for `infostand-tent-card-a5-quer`

<objective>
What this plan accomplishes: implement the V1 "Hero Band" layout for the `infostand-tent-card-a5-quer` template per the 16 locked decisions in RESEARCH.md. Both panels (DE = Panel A upright, EN = Panel B rotated 180°) emitted from a single source via two builder helpers `_panel_de()` / `_panel_en()`. New polygons (Hero-Band Dunkelgrün, Photo-Backing Dunkelgrün, Footer-Strip Hellgrün) per panel; mutated ParaStyles for white-on-green typography; QR D1-conformant 17×17 mm in white zone (NOT inside footer); ParaStyle MUTATION pattern (no parallel `*-on-green` siblings); post-#24 INJECT_MAP idiom for full-width photo crop.

Why it matters: fourth of five V1 implementations; first multi-panel template; establishes the rotation contract reused in #21 (kandidat-falzflyer).

Scope IN: V1 deltas across build.py / meta.yml / template.sla / page-01.png / preview.pdf / README.md / smoke test / spec / NEW geometry tests / Brief §10 row.

Scope OUT: V2 "Side-By-Side Pillar"; V3 "Pure Type"; new asset cropping for `hintergrund-mitmachen.jpg` (#13); shortening QR URL (out-of-scope brand stewardship).

No CONTEXT.md — decisions based on the 16 locked decisions in RESEARCH.md (which corrects 4 ISSUE.md errata).
</objective>

<context>
Issue: @.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/ISSUE.md
Research: @.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/RESEARCH.md
Codebase trace: @.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/research/codebase.md
Pitfalls: @.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/research/pitfalls.md

ISSUE.md errata (already corrected in RESEARCH.md — DO NOT re-apply):
1. `Group(rotation=180, around=(148.5, 52.5))` does NOT exist as a primitive — use `_panel_de`/`_panel_en` builder helpers.
2. ISSUE.md says "wrap Panel A in rotation"; correct is "Panel B is the rotated half" (matches existing valley-fold convention; smoke test enforces). Locked: Panel A NOT rotated, Panel B rotated 180°.
3. CONSTRAINTS in ISSUE.md use snake_case stubs (`logo_panel_a`, `hero_band_a`); resolver matches on EXACT anname strings. Locked: use real annames `"Hero-Band Panel A"`, `"Logo Grüne (panel A)"`, etc.
4. `inside()` between rotated and unrotated frames FAILS (raw bbox math). Locked: declare `inside()` ONLY for intra-Panel-A pairs; cross-panel = `mirrored_y` on Polygons + `same_size` + `same_style` only.
5. QR `w 17→8` fails D1 (0.242 mm/module). Locked: keep QR at 17×17 mm in white zone (0.515 mm/module ✓ for v4-H).
6. Bullets/Termine fontsize must shrink (h=16 cannot fit 14pt 3-bullet body). Locked: 2 bullets fontsize 11 linesp 14.3 (Bullets); 2 lines fontsize 9 linesp 11.7 (Termine).

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase. -->

From tools/sla_lib/builder/__init__.py (public exports — NO `Group`, NO `aspect_fill`):
constraint factories: same_y, same_x, same_size(axis="both"|"w"|"h"), mirrored_x, mirrored_y, inside, equal_gap, hierarchy, same_style, distance_y, distance_x, aligned_below
primitives: TextFrame, ImageFrame, Polygon, ParaStyle, Run, Document, Brand, DocumentLayer, Master, Page

From tools/sla_lib/builder/primitives.py:434 (_Frame, all primitives inherit):
@dataclass class _Frame:
    x_mm: float = 0           # SLA XPOS in mm
    y_mm: float = 0           # SLA YPOS in mm; for ROT=180 this is the post-rotation bbox top-left = pre-rotation visual bottom-right
    w_mm: float = 50
    h_mm: float = 30
    rotation_deg: float = 0
    layer: int = 2            # 0=Hintergrund, 1=Bilder, 2=Text, 3=Falz
    anname: str = ""
@dataclass class TextFrame(_Frame):
    style: str = ""
    runs: list[Run] = ...
    layer: int = 2 (default Text)
@dataclass class ImageFrame(_Frame):
    inline_image_data: Optional[str] = None  # set by pack_inline_image / library.inject_into_frame
    inline_image_ext: Optional[str] = None
    scale_type: int = 0       # 0=ScaleAuto fit-to-frame; 1=Manual
    ratio: int = 1            # 1=preserve aspect, 0=stretch
    layer: int = 1 (default Bilder)
@dataclass class Polygon(_Frame):
    fill: str = "Black"       # "Dunkelgrün" | "Hellgrün" | "Gelb" | "Magenta" | "White" | None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0 (default Hintergrund)
    shape: str = "rectangle"

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    # Returns (base64_zlib_data, ext) for ImageFrame.inline_image_data/inline_image_ext.

From tools/sla_lib/builder/library.py:436-500:
def inject_into_frame(frame, img: LibraryImage, *, target_w_mm: float, target_h_mm: float,
                       dpi: int = 300, quality: int = 80, apply_watermark: bool = True) -> None:
    # Crop img to (target_w_mm, target_h_mm) aspect via crop_for_frame (honours manifest crop_focus);
    # pack as inline JPEG; set frame.scale_type=0. Watermark band re-stamped.
def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]

From tools/sla_lib/builder/constraints.py:
def same_y(*targets, tolerance_mm=0.5, name="") -> Constraint                        # L399
def same_x(*targets, tolerance_mm=0.5, name="") -> Constraint                        # L408
def same_size(*targets, axis="both"|"w"|"h", tolerance_mm=0.5, name="") -> Constraint # L417
def mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="") -> Constraint         # L443
def inside(child, parent, tolerance_mm=0.5, name="") -> Constraint                    # L453 — raw bbox; FAILS on rotation mismatch
def aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="") -> Constraint      # L507 — has rotation guard
def same_style(*targets, name="") -> Constraint                                       # L481 — rotation-invariant

Existing build.py (`templates/infostand-tent-card-a5-quer/build.py`) constants:
HERE = Path(__file__).resolve().parent
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_FALZ = 3
TRIM_W_MM = 297.0; TRIM_H_MM = 210.0; BLEED_MM = 3.0; FOLD_Y_MM = 105.0
def build_doc() -> Document          # current V0 single fn — V1 splits into build_template + build_preview, with build_doc = build_template alias for round-trip stability
def build(out_path=HERE/"template.sla") -> Path
CONSTRAINTS = [...]                  # current 5 entries; V1 replaces with 22

BRAND_CONSTRAINTS registry (16 rules post-#25; V1 adds NONE):
brand:color_palette, brand:font_family, brand:line_spacing_0.9, brand:hl_sl_distance_x2,
brand:logo_size_3M, brand:text_on_green, brand:bleed_3mm, brand:wahlkreuz_colored_bg,
brand:inside_page, brand:spine_safety, brand:bleed_coverage, brand:image_text_overlap,
brand:cover_extent_match, brand:visual_adjacency_drift, brand:image_fills_frame, brand:band_consistency

Frame inventory V1 TARGET (all SLA coords):
| anname                              | SLA coords                          | rotation_deg | layer        | style/asset                   |
|-------------------------------------|-------------------------------------|--------------|--------------|-------------------------------|
| Hero-Band Panel A         (Polygon) | (-3, -3, 303, 42)                   | 0            | Hintergrund  | fill=Dunkelgrün               |
| Logo Grüne (panel A)      (Image)   | (12, 6, 38, 30)                     | 0            | Bilder       | shared/logos/gruene-weiss.png |
| Headline Panel A          (Text)    | (55, 9, 230, 18)                    | 0            | Text         | tent/headline                 |
| Pay-off Panel A           (Text)    | (55, 27, 230, 8)                    | 0            | Text         | tent/payoff                   |
| Photo-Backing Panel A     (Polygon) | (-3, 39, 303, 33)                   | 0            | Hintergrund  | fill=Dunkelgrün               |
| Hintergrund-Mitmachen     (Image)   | (0, 39, 297, 33)                    | 0            | Bilder       | INJECT_MAP kontext_infostand_szene |
| QR-Code (mitmachen, panel A) (Image)| (12, 78, 17, 17)                    | 0            | Bilder       | samples/qr-mitmachen.png      |
| Body Panel A              (Text)    | (32, 78, 110, 16)                   | 0            | Text         | tent/body  (Bullets, 2 short) |
| Termine Panel A           (Text)    | (152, 78, 133, 16)                  | 0            | Text         | tent/termine                  |
| Footer-Strip Panel A      (Polygon) | (-3, 95, 303, 10)                   | 0            | Hintergrund  | fill=Hellgrün                 |
| CTA-Footer Panel A        (Text)    | (12, 97, 200, 6)                    | 0            | Text         | tent/cta-footer               |
| Impressum (Tent)          (Text)    | (215, 97, 80, 6)                    | 0            | Text         | tent/impressum (right-align)  |
| Mittelfalz (horizontal)             | y=105 w=297                         | 0            | Falz (=3)    | (TableTentFold block — UNCHANGED) |
| Hero-Band Panel B         (Polygon) | (-3, 171, 303, 42)                  | 0            | Hintergrund  | fill=Dunkelgrün               |
| Logo Grüne (panel B)      (Image)   | (50, 204, 38, 30)                   | 180          | Bilder       | shared/logos/gruene-weiss.png |
| Headline Panel B          (Text)    | (285, 201, 230, 18)                 | 180          | Text         | tent/headline                 |
| Pay-off Panel B           (Text)    | (285, 183, 230, 8)                  | 180          | Text         | tent/payoff                   |
| Photo-Backing Panel B     (Polygon) | (-3, 138, 303, 33)                  | 0            | Hintergrund  | fill=Dunkelgrün               |
| Hintergrund-Mitmachen Panel B (Image)| (297, 171, 297, 33)                | 180          | Bilder       | INJECT_MAP kontext_infostand_szene |
| QR-Code (mitmachen, panel B) (Image)| (29, 132, 17, 17)                   | 180          | Bilder       | samples/qr-mitmachen.png      |
| Body Panel B              (Text)    | (142, 132, 110, 16)                 | 180          | Text         | tent/body                     |
| Termine Panel B           (Text)    | (285, 132, 133, 16)                 | 180          | Text         | tent/termine                  |
| Footer-Strip Panel B      (Polygon) | (-3, 105, 303, 10)                  | 0            | Hintergrund  | fill=Hellgrün                 |
| CTA-Footer Panel B        (Text)    | (212, 113, 200, 6)                  | 180          | Text         | tent/cta-footer               |
| Impressum (Tent, panel B) (Text)    | (295, 113, 80, 6)                   | 180          | Text         | tent/impressum (right-align)  |

Panel B SLA math (use this rule, do NOT re-derive per frame):
- Text/Image frame on Panel A at LOCAL (x_a, y_a, w, h) → Panel B SLA = (x_a + w, 210 − y_a, w, h, ROT=180)
- Polygon on Panel A at LOCAL (x_a, y_a, w, h)         → Panel B SLA = (x_a, 210 − y_a − h, w, h, ROT=0)

V1 ParaStyles (verbatim — pass to T01):
# MUTATE existing
ParaStyle(name="tent/headline",   font="Vollkorn Black Italic", fontsize=26, linesp=23.4, linesp_mode=0, align=0, fcolor="White", language="de")
ParaStyle(name="tent/body",       font="Gotham Narrow Book",    fontsize=12, linesp=15.6, linesp_mode=0, align=0, fcolor="Black", language="de")
ParaStyle(name="tent/termine",    font="Gotham Narrow Book",    fontsize=9,  linesp=11.7, linesp_mode=0, align=0, fcolor="Black", language="de")
ParaStyle(name="tent/impressum",  font="Gotham Narrow Book",    fontsize=6,  linesp=7.8,  linesp_mode=0, align=2, fcolor="White", language="de")
# NEW
ParaStyle(name="tent/payoff",     font="Vollkorn Black Italic", fontsize=16, linesp=14.4, linesp_mode=0, align=0, fcolor="Gelb",  language="de")
ParaStyle(name="tent/cta-footer", font="Gotham Narrow Bold",    fontsize=11, linesp=14,   linesp_mode=0, align=0, fcolor="White", language="de")
# DROP existing tent/cta (no V1 frame uses it)

V1 CONSTRAINTS list (verbatim — 22 entries — pass to T05):
CONSTRAINTS = [
    # ── Panel A intra-panel containment (rotation_deg=0 throughout) ──
    inside("Logo Grüne (panel A)",     "Hero-Band Panel A",      name="logo_in_band_a"),
    inside("Headline Panel A",          "Hero-Band Panel A",      name="headline_in_band_a"),
    inside("Pay-off Panel A",           "Hero-Band Panel A",      name="payoff_in_band_a"),
    inside("Hintergrund-Mitmachen",     "Photo-Backing Panel A",  name="photo_in_backing_a"),
    inside("CTA-Footer Panel A",        "Footer-Strip Panel A",   name="cta_footer_in_strip_a"),
    inside("Impressum (Tent)",          "Footer-Strip Panel A",   name="impressum_in_strip_a"),
    # ── Panel A intra-panel adjacency ──
    aligned_below("Photo-Backing Panel A", "Hero-Band Panel A", gap_mm=0.0, name="photo_backing_below_hero_band_a"),
    same_x("Hero-Band Panel A", "Photo-Backing Panel A", "Footer-Strip Panel A", name="full_bleed_polygons_share_left_x_a"),
    same_y("Body Panel A", "Termine Panel A", name="bullets_termine_baseline_a"),
    same_size("Body Panel A", "Termine Panel A", axis="h", name="bullets_termine_height_a"),
    # ── Panel B intra-panel: only same-rotation-state pairs ──
    same_y("Body Panel B", "Termine Panel B", name="bullets_termine_baseline_b"),
    same_size("Body Panel B", "Termine Panel B", axis="h", name="bullets_termine_height_b"),
    # ── Cross-panel mirror at apex (Polygons only — both rotation_deg=0) ──
    mirrored_y("Hero-Band Panel A",      "Hero-Band Panel B",      axis_mm=105.0, name="hero_band_mirror_at_apex"),
    mirrored_y("Photo-Backing Panel A",  "Photo-Backing Panel B",  axis_mm=105.0, name="photo_backing_mirror_at_apex"),
    mirrored_y("Footer-Strip Panel A",   "Footer-Strip Panel B",   axis_mm=105.0, name="footer_strip_mirror_at_apex"),
    same_size("Hero-Band Panel A",       "Hero-Band Panel B",      name="hero_bands_same_size"),
    same_size("Photo-Backing Panel A",   "Photo-Backing Panel B",  name="photo_backings_same_size"),
    same_size("Footer-Strip Panel A",    "Footer-Strip Panel B",   name="footer_strips_same_size"),
    # ── Cross-panel style consistency (rotation-invariant) ──
    same_style("Headline Panel A",   "Headline Panel B",   name="hero_headline_style"),
    same_style("Pay-off Panel A",    "Pay-off Panel B",    name="payoff_style"),
    same_style("Body Panel A",       "Body Panel B",       name="bullets_style"),
    same_style("Termine Panel A",    "Termine Panel B",    name="termine_style"),
    same_style("CTA-Footer Panel A", "CTA-Footer Panel B", name="cta_footer_style"),
    same_style("Impressum (Tent)",   "Impressum (Tent, panel B)", name="impressum_style"),
]
</interfaces>

Key files:
@templates/infostand-tent-card-a5-quer/build.py — main rewrite (ParaStyles + helpers + frames + Polygons + INJECT_MAP + CONSTRAINTS)
@templates/infostand-tent-card-a5-quer/meta.yml — brand_overrides cleanup, ci_overrides extension, slots rewrite, SHA bump
@templates/infostand-tent-card-a5-quer/template.sla — regen via render-gallery
@templates/infostand-tent-card-a5-quer/page-01.png — regen via render-gallery
@templates/infostand-tent-card-a5-quer/preview.pdf — regen via render-gallery
@templates/infostand-tent-card-a5-quer/README.md — append V1 deltas + QR D1 + logo aspect rationale
@templates/_smoke/test_infostand_tent_card_a5_quer.py — extend assertions (locked decision #11)
@templates/_specs/infostand-tent-card-a5-quer.md — full V1 rewrite (locked decision #12)
@tools/sla_lib/tests/test_infostand_tent_card_geometry.py — NEW invariant-pinning test file (locked decision #13)
@shared/brand/DESIGN-SYSTEM-BRIEF.md — append §10 row dated 2026-05-09
</context>

<commit_format>
Format: conventional with issue prefix (per `.issues/config.yaml`)
Pattern: `20: <type>(<scope>): <subject>`
Examples:
  20: feat(infostand-tent-card): V1 ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides
  20: feat(infostand-tent-card): build_template/build_preview split + INJECT_MAP scaffold
  20: chore(infostand-tent-card): regen template.sla + page-01.png + preview.pdf
  20: test(infostand-tent-card): smoke test additions + NEW geometry tests
  20: docs(brand): brief §10 session-history row
NO "claude" / AI attribution anywhere — commits, code, comments, files (per user standing directive).
</commit_format>

<tasks>

<task type="auto">
  <name>Task 1 (T01): V1 ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides extension</name>
  <files>templates/infostand-tent-card-a5-quer/build.py, templates/infostand-tent-card-a5-quer/meta.yml</files>
  <action>
  Step 1 — Environment probe BEFORE editing build.py: verify `shared/logos/gruene-weiss.png` exists (read returns non-empty file). If MISSING (extremely unlikely per RESEARCH addendum which verified 413×118 px), STOP and document in EXECUTION.md "fallback to gruene-logo-bund-dunkel.png" — and use that asset name in T03 instead. If present, proceed.

  Step 2 — Edit `templates/infostand-tent-card-a5-quer/build.py` ParaStyle section ONLY (currently lines 79-129; do NOT touch frames in this task). MUTATE 4 existing styles, ADD 2 new, DROP 1:
  - MUTATE `tent/headline`: change fontsize=36→26, linesp=40→23.4, fcolor="Dunkelgrün"→"White". Keep font="Vollkorn Black Italic", linesp_mode=0, align=0, language="de".
  - MUTATE `tent/body`: change fontsize=14→12, linesp=18→15.6. Keep font="Gotham Narrow Book", fcolor="Black", linesp_mode=0, align=0, language="de".
  - MUTATE `tent/termine`: change fontsize=10→9, linesp=13→11.7. Keep font="Gotham Narrow Book", fcolor="Black", linesp_mode=0, align=0, language="de".
  - MUTATE `tent/impressum`: change fontsize=5→6, linesp=6→7.8, fcolor="Black"→"White", align=0→2 (right-align). Keep font="Gotham Narrow Book", linesp_mode=0, language="de".
  - ADD `tent/payoff`: font="Vollkorn Black Italic", fontsize=16, linesp=14.4, linesp_mode=0, align=0, fcolor="Gelb", language="de".
  - ADD `tent/cta-footer`: font="Gotham Narrow Bold", fontsize=11, linesp=14, linesp_mode=0, align=0, fcolor="White", language="de".
  - DROP `tent/cta`: delete the `doc.add_para_style(ParaStyle(name="tent/cta", ...))` block (currently lines 110-119). The `CTA Panel A` text frame that uses it will be deleted in T03.

  Use the MUTATION pattern (per #19 precedent), NOT parallel `*-on-green` siblings (per locked decision #9 / pitfall P3).

  Step 3 — Edit `templates/infostand-tent-card-a5-quer/meta.yml` ONLY ci_overrides.non_ci_styles (do NOT touch brand_overrides or slots in this task — those land in T06 and T03):
  - Replace the existing `non_ci_styles` list with:
    ```yaml
    non_ci_styles:
      - "tent/headline"
      - "tent/body"
      - "tent/termine"
      - "tent/impressum"
      - "tent/payoff"
      - "tent/cta-footer"
    ```
  - DO NOT add new colors/layers — palette stays standard CI (Dunkelgrün, Hellgrün, Gelb, White, Black already in the document via Brand defaults; only `Falz` stays in non_ci_colors).

  Step 4 — Verify `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0 (the build still works pre-T03 because frames using deprecated styles still reference valid style names IF you don't yet remove the CTA Panel A frame — leave the frame for now even though the style is gone, since this is a syntax-only ParaStyle pass and the existing frame's style reference is just a string. Build.py will still emit; the WIP frame will fail style-resolution at structural_check but we will not run structural_check yet). Equivalent acceptance: build.py runs without ImportError or AttributeError.

  AVOID: do NOT yet remove the CTA Panel A frame in this task (defer to T03). Do NOT touch brand_overrides in meta.yml (defer to T06).

  COMMIT: `20: feat(infostand-tent-card): V1 ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && python3 templates/infostand-tent-card-a5-quer/build.py</automated>
  </verify>
  <done>
  - 4 ParaStyles mutated (`tent/headline`, `tent/body`, `tent/termine`, `tent/impressum`) with exact values per the table above.
  - 2 ParaStyles added (`tent/payoff`, `tent/cta-footer`) with exact values per the table above.
  - 1 ParaStyle removed (`tent/cta` add_para_style call deleted).
  - meta.yml `ci_overrides.non_ci_styles` lists exactly the 6 V1 styles.
  - `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0.
  - Commit message exactly: `20: feat(infostand-tent-card): V1 ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides`.
  - No "claude" / AI attribution anywhere.
  </done>
</task>

<task type="auto">
  <name>Task 2 (T02): build_template + build_preview split + INJECT_MAP scaffold + build_doc alias</name>
  <files>templates/infostand-tent-card-a5-quer/build.py</files>
  <action>
  Refactor `build.py` to introduce the post-#24 INJECT_MAP idiom. This is a NO-OP refactor for SLA output (round-trip stable) — it only restructures the `build_doc()` function into two functions for round-trip stability + structural_check + photo-injection separation.

  Step 1 — Rename existing `build_doc()` to `build_template()`. The function body stays IDENTICAL — keep all current frame creation, polygon emission, page setup. Do NOT yet add the new V1 frames in this task (defer to T03/T04). The single-line semantic: `build_template()` returns a clean Document with the EXISTING V0 layout but with photo's `inline_image_data=None` (clean for round-trip).

  Step 2 — In current `build_doc()` (now `build_template()`), find the `Hintergrund-Mitmachen` ImageFrame block (currently lines 222-234, uses `library.crop_for_frame` + `pack_inline_image`). REMOVE the inline image attachment. Change to: an ImageFrame with no `inline_image_data` set (or explicit `inline_image_data=None`, `inline_image_ext=None`). The frame still has `anname="Hintergrund-Mitmachen"`, current coords (12, 44, 44, 33) for now — defer V1 reposition to T03.

  Step 3 — Add module-level constant `INJECT_MAP` after the LAYER_* constants:
    ```python
    INJECT_MAP = {
        # Anname → library image id (resolved by library.load() in build_preview)
        "Hintergrund-Mitmachen":         "kontext_infostand_szene",
        "Hintergrund-Mitmachen Panel B": "kontext_infostand_szene",
    }
    ```
  (The Panel B entry is dormant until T04 adds the `Hintergrund-Mitmachen Panel B` frame; leaving it pre-declared here is fine — `build_preview` will skip annames it doesn't find in the document.)

  Step 4 — Add new `build_preview() -> Document` function above `build()`:
    ```python
    def build_preview() -> Document:
        """Build the doc and inject library images into INJECT_MAP frames.

        Round-trip stability: build_template() produces the SLA without inline images
        (clean for structural_check + spec_check). build_preview() wraps it for actual
        rendering (page-01.png + preview.pdf).
        """
        doc = build_template()
        from sla_lib.builder import library  # local import to avoid module-load cost on test paths
        for page in doc.pages:
            for item in page.items:
                if not isinstance(item, ImageFrame):
                    continue
                lib_id = INJECT_MAP.get(item.anname)
                if not lib_id:
                    continue
                img = library.load(lib_id, optional=True)
                if img is None:
                    continue
                library.inject_into_frame(
                    item, img,
                    target_w_mm=item.w_mm,   # use LIVE frame dims (post-#24 lesson)
                    target_h_mm=item.h_mm,
                )
        return doc
    ```
  CRITICAL: target_w_mm / target_h_mm MUST come from `item.w_mm` / `item.h_mm` (live frame attrs), NEVER hard-coded literals (per pitfall P7 — that lesson cost #24 a follow-up).

  Step 5 — Add module-level alias `build_doc = build_template` (one line, immediately after `build_template()` definition). This preserves any external caller (structural_check, spec_check, render-gallery) that imports `build_doc`.

  Step 6 — Update existing `build(out_path=...)` to call `build_preview()` (so the emitted SLA carries the injected JPEG): change the line that previously called `build_doc()` to call `build_preview()`.

  Step 7 — Verify build still produces an SLA with substantively-identical content for non-photo frames. Quick smoke: run `python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer` — all 9 existing assertions should still PASS (since we have NOT yet changed any V1 frame coords). The photo's inline data may differ (re-injected by build_preview) but smoke does not assert photo content.

  AVOID: do NOT yet add V1 frames or polygons (T03/T04). Do NOT yet touch CONSTRAINTS (T05). Do NOT call `library.crop_for_frame` directly (use `library.inject_into_frame`, post-#24 idiom). Do NOT use literal target_w_mm/target_h_mm.

  COMMIT: `20: refactor(infostand-tent-card): build_template/build_preview split + INJECT_MAP`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && python3 templates/infostand-tent-card-a5-quer/build.py && python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer 2>&1 | tail -3</automated>
  </verify>
  <done>
  - `build_template()` exists; produces Document without inline image data on `Hintergrund-Mitmachen` frame.
  - `build_preview()` exists; loops INJECT_MAP and calls `library.inject_into_frame(item, img, target_w_mm=item.w_mm, target_h_mm=item.h_mm)`.
  - `build_doc = build_template` alias declared.
  - `build()` calls `build_preview()`.
  - INJECT_MAP includes both Panel A and (dormant) Panel B entries.
  - 9/9 existing smoke tests still pass.
  - Commit message exactly: `20: refactor(infostand-tent-card): build_template/build_preview split + INJECT_MAP`.
  </done>
</task>

<task type="auto">
  <name>Task 3 (T03): V1 Panel A layout via _panel_de helper — frames, polygons, logo asset swap, photo reposition, CTA frame deletion</name>
  <files>templates/infostand-tent-card-a5-quer/build.py</files>
  <action>
  Implement the full V1 Panel A layout. This is the largest single task — touches every Panel A frame plus 3 new Polygons.

  Step 1 — Add helper function `_panel_de() -> list` ABOVE `build_template()`. Returns a list of primitives in panel-LOCAL coords (i.e. as-if Panel A were the whole page; coords are absolute on the flat sheet for Panel A since Panel A is NOT rotated). The helper returns the V1 Panel A primitive set listed below (12 items). Each Polygon MUST specify `layer=LAYER_HINTERGRUND` explicitly (per pitfall P2/P13 — Falz layer integrity).

  Panel A primitives produced by `_panel_de()` (return as a Python list in this order, all rotation_deg=0):
  1. Polygon(anname="Hero-Band Panel A",     x_mm=-3, y_mm=-3,  w_mm=303, h_mm=42, fill="Dunkelgrün", layer=LAYER_HINTERGRUND, rotation_deg=0)
  2. ImageFrame(anname="Logo Grüne (panel A)", x_mm=12, y_mm=6, w_mm=38, h_mm=30, layer=LAYER_BILDER, rotation_deg=0, scale_type=0, ratio=1, inline_image_data + ext from `pack_inline_image(open("shared/logos/gruene-weiss.png","rb").read(), "png")` — read the asset relative to the workspace root (use absolute path from HERE.parent.parent / "shared/logos/gruene-weiss.png" or equivalent — check existing build.py L152-161 for the existing asset-loading pattern and reuse it, just swap filename and coords))
  3. TextFrame(anname="Headline Panel A",    x_mm=55, y_mm=9,  w_mm=230, h_mm=18, layer=LAYER_TEXT, rotation_deg=0, style="tent/headline", runs=[Run(text="Klimaschutz konkret.")])
  4. TextFrame(anname="Pay-off Panel A",     x_mm=55, y_mm=27, w_mm=230, h_mm=8,  layer=LAYER_TEXT, rotation_deg=0, style="tent/payoff",   runs=[Run(text="Konkret. Lokal. Jetzt.")])
  5. Polygon(anname="Photo-Backing Panel A", x_mm=-3, y_mm=39, w_mm=303, h_mm=33, fill="Dunkelgrün", layer=LAYER_HINTERGRUND, rotation_deg=0)
  6. ImageFrame(anname="Hintergrund-Mitmachen", x_mm=0, y_mm=39, w_mm=297, h_mm=33, layer=LAYER_BILDER, rotation_deg=0, scale_type=0, ratio=1, inline_image_data=None, inline_image_ext=None)  # populated by build_preview INJECT_MAP
  7. ImageFrame(anname="QR-Code (mitmachen, panel A)", x_mm=12, y_mm=78, w_mm=17, h_mm=17, layer=LAYER_BILDER, rotation_deg=0, scale_type=0, ratio=1, inline_image_data + ext from existing `samples/qr-mitmachen.png` (reuse existing pattern at current build.py L245-252; just shift y from 80→78))
  8. TextFrame(anname="Body Panel A",        x_mm=32, y_mm=78, w_mm=110, h_mm=16, layer=LAYER_TEXT, rotation_deg=0, style="tent/body",     runs=[Run(text="• Erneuerbare Energie für alle\n• Leistbares Wohnen schützen")])  # 2 short bullets, drop the third per locked decision #6
  9. TextFrame(anname="Termine Panel A",     x_mm=152, y_mm=78, w_mm=133, h_mm=16, layer=LAYER_TEXT, rotation_deg=0, style="tent/termine",  runs=[Run(text="• 12. Juni — Klimastammtisch\n• 26. Juni — Bezirkstreffen")])  # 2 lines, drop "Nächste Termine" header per locked decision #7
  10. Polygon(anname="Footer-Strip Panel A", x_mm=-3, y_mm=95, w_mm=303, h_mm=10, fill="Hellgrün", layer=LAYER_HINTERGRUND, rotation_deg=0)
  11. TextFrame(anname="CTA-Footer Panel A", x_mm=12, y_mm=97, w_mm=200, h_mm=6, layer=LAYER_TEXT, rotation_deg=0, style="tent/cta-footer", runs=[Run(text="gruene-noe.at/mitmachen")])
  12. TextFrame(anname="Impressum (Tent)",   x_mm=215, y_mm=97, w_mm=80, h_mm=6, layer=LAYER_TEXT, rotation_deg=0, style="tent/impressum",  runs=[Run(text="Medieninhaber: Die Grünen NÖ — gruene-noe.at")])  # right-aligned via tent/impressum align=2

  Step 2 — In `build_template()` body, REMOVE the existing V0 Panel A frames (Logo Grüne (panel A), Headline Panel A, Body Panel A, CTA Panel A, Termine Panel A, Hintergrund-Mitmachen, QR-Code (mitmachen, panel A), Impressum (Tent)) — do NOT remove the `Mittelfalz (horizontal)` block (LAYER=Falz, untouched). Then call `for prim in _panel_de(): page.add(prim)` (adapt to whatever the actual Page-add API is in current build.py — read existing pattern; same pattern as V0 used `page.add(...)` for each frame).

  Step 3 — DELETE the `CTA Panel A` text frame entirely (was at current build.py L192-199; functionally replaced by `Pay-off Panel A` + `CTA-Footer Panel A`).

  Step 4 — Polygon LAYER assertion: every NEW Polygon (`Hero-Band Panel A`, `Photo-Backing Panel A`, `Footer-Strip Panel A`) MUST have explicit `layer=LAYER_HINTERGRUND` (=0). NEVER `LAYER_FALZ` (=3). Per pitfall P2/P13 — Falz layer integrity is asserted by T08's geometry test.

  Step 5 — Ensure the `Mittelfalz (horizontal)` Falz block is left UNTOUCHED (still on layer=LAYER_FALZ). This stays the ONLY object on LAYER 3.

  Step 6 — Ensure NO V1 task in this file writes to LAYER 1 (Falz). Per pitfall P13 — only the Falz block on LAYER=3.

  Step 7 — Verify build runs clean: `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0.

  EXPECTED smoke test status post-T03 (do NOT fix yet):
  - `test_panel_a_frames_not_rotated`: PASS (all Panel A frames ROT=0).
  - `test_panel_b_frames_rotated_180`: PASS (Panel B frames untouched in T03 — V0 Panel B still present).
  - `test_impressum_above_fold` (asserts Impressum bottom ≤ 102): FAIL (V1 Impressum at y=97, h=6 → bottom y=103). EXPECTED — relaxed in T08.
  - `test_four_main_text_frames_present`: PASS (Headline/Body Panel A annames preserved).
  Other 5 tests: PASS.

  AVOID: do NOT yet add Panel B V1 frames (T04). Do NOT use snake_case annames (use real annames per pitfall P0.4). Do NOT use a `Group` primitive (does not exist — pitfall P0.1). Do NOT yet add CONSTRAINTS list (T05).

  COMMIT: `20: feat(infostand-tent-card): V1 Panel A layout via _panel_de helper`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && python3 templates/infostand-tent-card-a5-quer/build.py && python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer 2>&1 | tail -8</automated>
  </verify>
  <done>
  - `_panel_de()` helper exists, returns 12-element list with EXACT coords per the table above.
  - All NEW Polygons have `layer=LAYER_HINTERGRUND` explicit.
  - `CTA Panel A` text frame deleted from build.
  - `Logo Grüne (panel A)` asset is `shared/logos/gruene-weiss.png`.
  - `Hintergrund-Mitmachen` ImageFrame at (0, 39, 297, 33) with no inline image data (build_preview INJECT_MAP populates it).
  - `Mittelfalz (horizontal)` Falz block UNTOUCHED on LAYER_FALZ.
  - `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0.
  - Smoke test fails ONLY on `test_impressum_above_fold` (expected — relaxed in T08); 8/9 other tests pass.
  - Commit message exactly: `20: feat(infostand-tent-card): V1 Panel A layout via _panel_de helper`.
  </done>
</task>

<task type="auto">
  <name>Task 4 (T04): V1 Panel B layout via _panel_en helper — mirror+rotation transform, full V1 Panel B</name>
  <files>templates/infostand-tent-card-a5-quer/build.py</files>
  <action>
  Implement Panel B by transforming Panel A primitives via the locked rotation+mirror math. Panel B frames are the EN/Panel-B counterparts of Panel A; they appear in the SLA at coords computed by the rule:
  - Text/Image frame on Panel A LOCAL (x, y, w, h) → Panel B SLA (x + w, 210 − y, w, h, ROT=180)
  - Polygon on Panel A LOCAL (x, y, w, h)         → Panel B SLA (x, 210 − y − h, w, h, ROT=0)

  Step 1 — Add helper function `_panel_en() -> list` ABOVE `build_template()` (after `_panel_de()`). Implementation: build a fresh list of Panel B primitives by calling `_panel_de()` then transforming each primitive per the rule above. Use a different anname for each (Panel B suffix). The text content is ENGLISH equivalents.

  Pseudocode for `_panel_en()` (executor: implement as a list of explicit constructor calls — do NOT mutate Panel A primitives in place since they are already in the page; build new ones):

  Panel B primitives produced by `_panel_en()` (12 items, in order):
  1.  Polygon(anname="Hero-Band Panel B",     x_mm=-3, y_mm=171, w_mm=303, h_mm=42, fill="Dunkelgrün", layer=LAYER_HINTERGRUND, rotation_deg=0)
  2.  ImageFrame(anname="Logo Grüne (panel B)", x_mm=50, y_mm=204, w_mm=38, h_mm=30, layer=LAYER_BILDER, rotation_deg=180, scale_type=0, ratio=1, inline_image_data+ext = same gruene-weiss.png pattern as Panel A)
  3.  TextFrame(anname="Headline Panel B",    x_mm=285, y_mm=201, w_mm=230, h_mm=18, layer=LAYER_TEXT, rotation_deg=180, style="tent/headline", runs=[Run(text="Climate. Concrete.")])
  4.  TextFrame(anname="Pay-off Panel B",     x_mm=285, y_mm=183, w_mm=230, h_mm=8,  layer=LAYER_TEXT, rotation_deg=180, style="tent/payoff",   runs=[Run(text="Concrete. Local. Now.")])
  5.  Polygon(anname="Photo-Backing Panel B", x_mm=-3, y_mm=138, w_mm=303, h_mm=33, fill="Dunkelgrün", layer=LAYER_HINTERGRUND, rotation_deg=0)
  6.  ImageFrame(anname="Hintergrund-Mitmachen Panel B", x_mm=297, y_mm=171, w_mm=297, h_mm=33, layer=LAYER_BILDER, rotation_deg=180, scale_type=0, ratio=1, inline_image_data=None, inline_image_ext=None)  # populated by build_preview INJECT_MAP entry already declared in T02
  7.  ImageFrame(anname="QR-Code (mitmachen, panel B)", x_mm=29, y_mm=132, w_mm=17, h_mm=17, layer=LAYER_BILDER, rotation_deg=180, scale_type=0, ratio=1, inline_image_data+ext = same qr-mitmachen.png pattern as Panel A)
  8.  TextFrame(anname="Body Panel B",        x_mm=142, y_mm=132, w_mm=110, h_mm=16, layer=LAYER_TEXT, rotation_deg=180, style="tent/body",     runs=[Run(text="• Renewable energy for all\n• Affordable housing")])
  9.  TextFrame(anname="Termine Panel B",     x_mm=285, y_mm=132, w_mm=133, h_mm=16, layer=LAYER_TEXT, rotation_deg=180, style="tent/termine",  runs=[Run(text="• Jun 12 — Climate Stammtisch\n• Jun 26 — District meeting")])
  10. Polygon(anname="Footer-Strip Panel B",  x_mm=-3, y_mm=105, w_mm=303, h_mm=10, fill="Hellgrün", layer=LAYER_HINTERGRUND, rotation_deg=0)
  11. TextFrame(anname="CTA-Footer Panel B", x_mm=212, y_mm=113, w_mm=200, h_mm=6, layer=LAYER_TEXT, rotation_deg=180, style="tent/cta-footer", runs=[Run(text="noe.gruene.at/joinus")])
  12. TextFrame(anname="Impressum (Tent, panel B)", x_mm=295, y_mm=113, w_mm=80, h_mm=6, layer=LAYER_TEXT, rotation_deg=180, style="tent/impressum", runs=[Run(text="Medieninhaber: Die Grünen NÖ — gruene-noe.at")])

  Sanity-check the math (executor: spot-check 3 of these by hand):
  - Logo Panel A (12, 6, 38, 30) → Panel B Text/Image SLA (12+38, 210−6, 38, 30, ROT=180) = (50, 204, 38, 30, ROT=180) ✓
  - Hero-Band Panel A (−3, −3, 303, 42) Polygon → Panel B SLA (−3, 210−(−3)−42, 303, 42, ROT=0) = (−3, 171, 303, 42, ROT=0) ✓
  - Footer-Strip Panel A (−3, 95, 303, 10) Polygon → Panel B SLA (−3, 210−95−10, 303, 10, ROT=0) = (−3, 105, 303, 10, ROT=0) ✓ (this is the deliberate 20mm Hellgrün band straddling the apex per RESEARCH §3 — Panel A footer 95-105 + Panel B footer 105-115 abut the fold).

  Step 2 — In `build_template()` body, REMOVE the existing V0 Panel B frames (Headline Panel B, Body Panel B, CTA Panel B, Termine Panel B, Logo Grüne (panel B)). Call `for prim in _panel_en(): page.add(prim)` after the `_panel_de()` loop.

  Step 3 — Verify INJECT_MAP entry `"Hintergrund-Mitmachen Panel B": "kontext_infostand_szene"` is present (declared in T02). build_preview will now find this anname in the document and inject the cropped image.

  Step 4 — Verify all NEW Polygons have `layer=LAYER_HINTERGRUND` explicit (per pitfall P2/P13 — applies to Panel B polygons too).

  Step 5 — Verify build runs clean: `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0.

  EXPECTED smoke test status post-T04:
  - `test_panel_a_frames_not_rotated`: PASS.
  - `test_panel_b_frames_rotated_180`: PASS (Panel B Headline/Body now ROT=180 per V1 spec).
  - `test_impressum_above_fold`: still FAIL — relaxed in T08.
  Other tests: PASS.

  AVOID: do NOT use a `Group` primitive (P0.1). Do NOT use snake_case annames (P0.4). Do NOT mutate `_panel_de()`'s primitive list — build a fresh list. Do NOT use `MirroredPair` (per pitfall P10 — does not rotate).

  COMMIT: `20: feat(infostand-tent-card): V1 Panel B layout via _panel_en helper`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && python3 templates/infostand-tent-card-a5-quer/build.py && python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer 2>&1 | tail -8</automated>
  </verify>
  <done>
  - `_panel_en()` helper exists, returns 12-element list with EXACT coords per the table above.
  - All Panel B Text/Image frames have `rotation_deg=180`.
  - All Panel B Polygons have `rotation_deg=0` and `layer=LAYER_HINTERGRUND`.
  - `Hintergrund-Mitmachen Panel B` declared as new anname (separate from Panel A's `Hintergrund-Mitmachen`).
  - `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0.
  - Smoke 8/9 PASS (only `test_impressum_above_fold` fails — relaxed in T08).
  - Commit message exactly: `20: feat(infostand-tent-card): V1 Panel B layout via _panel_en helper`.
  </done>
</task>

<task type="auto">
  <name>Task 5 (T05): V1 CONSTRAINTS list (22 entries, replaces 5)</name>
  <files>templates/infostand-tent-card-a5-quer/build.py</files>
  <action>
  Replace the existing 5-entry `CONSTRAINTS` list (currently lines 386-410) with the V1 22-entry list. Use the EXACT contents from the `<interfaces>` block (V1 CONSTRAINTS list). Use real annames (not snake_case stubs — pitfall P0.4). Restrict `inside()` to intra-Panel-A (per locked decision #4 / pitfall P0.3 — `inside` fails on rotated/unrotated mismatch).

  Step 1 — Locate `CONSTRAINTS = [` block in build.py (currently 5 entries: panel_headline_style_consistent, panel_body_style_consistent, panel_cta_style_consistent, panel_termine_style_consistent, panel_headline_size_match). Replace ENTIRELY with the 22-entry V1 list verbatim from the `<interfaces>` block. Keep the import statements for the constraint factories (`from sla_lib.builder import same_y, same_x, same_size, mirrored_y, inside, aligned_below, same_style, ...` — adapt to existing build.py imports).

  Step 2 — Verify factor names: `inside`, `same_y`, `same_x`, `same_size`, `aligned_below`, `mirrored_y`, `same_style` — all exist in `tools/sla_lib/builder/__init__.py` exports. NO `Group`, NO `same_y_top`, NO custom helpers (per RESEARCH §"Don't Hand-Roll").

  Step 3 — Run structural_check:
  ```
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
  ```
  Expected: 0 errors. Should report 22 constraints, all passing. If any constraint fires:
  - `child '<X>' bbox not inside parent '<Y>'`: re-verify that target frame coords match the table above. Fix the frame coords (in T03/T04 helpers), not the constraint.
  - `_missing_violation` for an anname: real anname mismatch — fix the constraint target string OR fix the frame anname.
  - `mirrored_y` failure on Polygons: re-verify Panel B polygon SLA coords. Hero-Band: A(−3, −3, 303, 42) vs B(−3, 171, 303, 42) → centers (−3+303/2, −3+42/2) = (148.5, 18) vs (148.5, 192) → midpoint y = (18+192)/2 = 105 ✓.
  - `aligned_below` warning on rotated frame: should not fire here since we declare it only for Panel A polygons (both rotation_deg=0).

  Step 4 — Run `--all` to ensure no regression on other templates:
  ```
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
  ```
  Expected: 0 errors across all templates.

  AVOID: do NOT add cross-panel `inside` (pitfall P0.3). Do NOT add `aligned_below` between rotated and unrotated frames. Do NOT use snake_case annames. Do NOT add NEW BrandRule (registry stays at 16 — RESEARCH §6).

  COMMIT: `20: feat(infostand-tent-card): V1 CONSTRAINTS (22 entries)`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5</automated>
  </verify>
  <done>
  - `CONSTRAINTS` list contains exactly 22 entries with the names from the `<interfaces>` block.
  - All 22 constraints PASS structural_check.
  - `structural_check infostand-tent-card-a5-quer` exits 0.
  - `structural_check --all` exits 0.
  - Brand override count UNCHANGED (still 6); brand_overrides cleanup deferred to T06.
  - Commit message exactly: `20: feat(infostand-tent-card): V1 CONSTRAINTS (22 entries)`.
  </done>
</task>

<task type="auto">
  <name>Task 6 (T06): Regen template.sla + page-01.png + preview.pdf + meta.yml SHA + brand_overrides cleanup + slots rewrite</name>
  <files>templates/infostand-tent-card-a5-quer/template.sla, templates/infostand-tent-card-a5-quer/page-01.png, templates/infostand-tent-card-a5-quer/preview.pdf, templates/infostand-tent-card-a5-quer/meta.yml, site/public/templates/infostand-tent-card-a5-quer/page-01.png, site/public/templates/infostand-tent-card-a5-quer/preview.pdf</files>
  <action>
  Regenerate the rendering artifacts and finalize meta.yml. This is two combined concerns (regen + meta.yml cleanup) since render-gallery rewrites the SHA in meta.yml — combining minimizes commit churn.

  Step 1 — Run gallery regen:
  ```
  cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band
  bin/render-gallery infostand-tent-card-a5-quer --skip-visual-diff
  ```
  This rebuilds template.sla, page-01.png, preview.pdf, mirrors site/public, AND auto-bumps `previews_for_sla` SHA in meta.yml.

  Step 2 — Verify check-stale-previews passes:
  ```
  bin/check-stale-previews
  ```
  Exit 0 expected.

  Step 3 — Verify structural_check still passes:
  ```
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
  ```
  Both exit 0 expected.

  Step 4 — `meta.yml` brand_overrides cleanup. Open `templates/infostand-tent-card-a5-quer/meta.yml`. The current brand_overrides has 6 entries (line_spacing_0.9, logo_size_3M, visual_adjacency_drift, image_text_overlap, image_fills_frame, band_consistency).

  EMPIRICAL VERIFICATION FIRST (per planner's tightening — promotes RESEARCH MED-confidence prediction to a verification step):

  Run structural_check after each removal to confirm. Method:
  - REMOVE `brand:logo_size_3M` first → run structural_check → if 0 errors, commit removal; if it fires, RESTORE with reason "V1 logo width 38mm computes 38/12.6=3.02M; rule's tolerance is stricter than expected — keep override (reviewed 2026-05-09)" — do NOT punt.
  - REMOVE `brand:image_text_overlap` → run structural_check → same protocol; if it fires (likely on Panel B due to rotation bbox math per pitfall P6 caveat), RESTORE with reason "Panel B rotation_deg=180 makes raw bbox math non-intuitive; rule false-positives on rotated text/polygon containment — KEEP override".
  - REMOVE `brand:image_fills_frame` → run structural_check → expected PASS since INJECT_MAP fills frame exactly via inject_into_frame. If it fires, RESTORE with reason — but verify inject_into_frame is using LIVE frame dims (per T02 step 4); if literal hardcoded dims slipped in, fix the bug rather than restoring the override.

  KEEP these 3 with reason updates (verbatim text):
  - `brand:line_spacing_0.9` reason: "Body 1.3× and Termine 1.3× and CTA-Footer 1.27× linesp ratios are intentional Quickguide-body convention; tent/headline at 26/23.4=0.9 IS conformant (verified 2026-05-09)."
  - `brand:visual_adjacency_drift` reason: "V1 CONSTRAINTS captures Panel-A and cross-panel adjacencies. Combinatorial intra-Panel-B warnings on rotated text/polygon pairs cannot be silenced without 20+ pairwise declarations; deferred to constraint-engine rotation-awareness work (verified 2026-05-09)."
  - `brand:band_consistency` reason: "Tent-card has no body-pool model; rule no-ops by design (verified 2026-05-09)."

  Step 5 — `meta.yml` slots rewrite. Replace the existing 6-entry slots block with a V1 slot enumeration covering ALL Panel-A + Panel-B annames. Slot list (executor: pattern after existing slot entries — each slot needs `id`, `anname`, `description`, `fontsize`, `style` etc. as the schema requires; read existing slots block for the exact field set):

  Slots to enumerate (24 slots):
  - hero_band_a (Hero-Band Panel A polygon) / hero_band_b (Hero-Band Panel B polygon)
  - logo_panel_a (Logo Grüne (panel A)) / logo_panel_b (Logo Grüne (panel B))
  - headline_a (Headline Panel A) / headline_b (Headline Panel B)
  - payoff_a (Pay-off Panel A) / payoff_b (Pay-off Panel B)
  - photo_backing_a (Photo-Backing Panel A polygon) / photo_backing_b (Photo-Backing Panel B polygon)
  - photo_a (Hintergrund-Mitmachen) / photo_b (Hintergrund-Mitmachen Panel B)
  - qr_a (QR-Code (mitmachen, panel A)) / qr_b (QR-Code (mitmachen, panel B))
  - bullets_a (Body Panel A) / bullets_b (Body Panel B)
  - termine_a (Termine Panel A) / termine_b (Termine Panel B)
  - footer_strip_a / footer_strip_b
  - cta_footer_a (CTA-Footer Panel A) / cta_footer_b (CTA-Footer Panel B)
  - impressum_a (Impressum (Tent)) / impressum_b (Impressum (Tent, panel B))

  If the slots schema requires fewer fields per slot (read existing block to match the schema exactly), use the minimum schema. Match field shape to current entries.

  Step 6 — Update `example_pages` if needed (currently `[{num: 1, label: "Flach (vor dem Falzen) — Panel A oben, Panel B unten 180°"}]`). This stays correct for V1; no change.

  Step 7 — Final verification gate for T06:
  ```
  bin/render-gallery infostand-tent-card-a5-quer --skip-visual-diff   # if SHA needs rebump after meta.yml edit
  bin/check-stale-previews                                              # exit 0
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer  # exit 0
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all                          # exit 0
  ```

  AVOID: do NOT run a Codex visual review (per locked decision #16 — SKIPPED). Do NOT manually edit page-01.png / preview.pdf — only render-gallery emits these. Do NOT introduce a new BrandRule.

  COMMIT (single commit covering regen + brand_overrides + slots): `20: chore(infostand-tent-card): regen artifacts + brand_overrides cleanup + slots rewrite`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && bin/check-stale-previews && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5</automated>
  </verify>
  <done>
  - `template.sla`, `page-01.png`, `preview.pdf` regenerated by render-gallery.
  - `site/public/templates/infostand-tent-card-a5-quer/` mirror updated.
  - `meta.yml` `previews_for_sla` SHA bumped (auto by render-gallery).
  - `meta.yml` `brand_overrides` count = 3 (kept) UNLESS empirical verification restored 1+ removed override (in which case document the deviation in EXECUTION.md). Each kept override has updated 2026-05-09 reason text.
  - `meta.yml` `slots` enumerates the V1 anname set (24 slots).
  - `bin/check-stale-previews` exits 0.
  - `structural_check infostand-tent-card-a5-quer` exits 0.
  - `structural_check --all` exits 0.
  - Commit message exactly: `20: chore(infostand-tent-card): regen artifacts + brand_overrides cleanup + slots rewrite`.
  </done>
</task>

<task type="auto">
  <name>Task 7 (T07): README.md V1 deltas + QR D1 rationale + logo aspect note</name>
  <files>templates/infostand-tent-card-a5-quer/README.md</files>
  <action>
  Append a V1 section to the template's README.md documenting the V1 layout decisions per ISSUE.md acceptance criterion ("QR module-size decision documented in README.md").

  Read existing README.md first to preserve its structure / style (likely brief — 20-50 lines per template convention).

  Append section "## V1 Layout: Hero Band (2026-05-09)" with these subsections:

  1. "### Layout zones": brief enumeration (Hero-Band Dunkelgrün top + apex; Photo-Band full-width 297×33; Bullets+Termine white zone with QR; Footer-Strip Hellgrün at apex with CTA URL + Impressum). Cite the rotation contract: Panel A upright DE; Panel B 180° EN; mirror axis y=105.

  2. "### QR module-size decision": Document the locked decision #5 in plain prose:
     "QR-Code remains at 17×17 mm in the white zone (Panel coords (12, 78, 17, 17); symmetrically (29, 132, 17, 17) ROT=180 on Panel B). Encoded URL `https://noe.gruene.at/mitmachen/` (32 chars, error-correction H) compiles to QR-v4 (33 modules). At 17 mm frame, 17/33 ≈ 0.515 mm/module — D1-conformant (≥0.5 mm). Reducing to 14 mm would drop to 0.424 mm/module (fails D1); reducing to v3 would require URL shortening (out of scope, brand stewardship coordination tracked elsewhere). Footer-Strip houses CTA-Footer + Impressum only — QR does NOT live inside the footer."

  3. "### Logo aspect note": Document the locked decision per RESEARCH addendum:
     "Logo asset `shared/logos/gruene-weiss.png` (413×118 px, 3.5:1 wordmark 'DIE GRÜNEN', white-on-transparent). Frame is 38×30 mm (1.27:1). Scribus auto-fit (scale_type=0, ratio=1) preserves aspect → wordmark renders at 38×10.86 mm centered in the 30 mm frame, with ≈9.5 mm vertical breathing room above and below. The brand:logo_size_3M rule operates on frame.w_mm (38 mm ≈ 3M ± 0.2 mm ✓). The 30 mm frame height balances the Headline+Pay-off stack on the right (y=9..35 = 26 mm tall). Future iter could commission a `bund-weiss.png` true-3M-tall asset; current V1 accepts the 10.86 mm rendered height."

  4. "### Photo crop note": Brief — source `kontext_infostand_szene` (1536×1024, 1.5:1) is cropped to 9:1 in build_preview via library.inject_into_frame using the manifest's crop_focus [0.50, 0.55] (table+people area). Acceptable for demo; production aspect optimization tracked in #13.

  Keep the section concise (60-80 lines added). Use existing README's heading style if any.

  AVOID: do NOT include Codex review notes. Do NOT include "claude" / AI attribution. Do NOT cite RESEARCH.md / PLAN.md by path (those are issue artifacts).

  COMMIT: `20: docs(infostand-tent-card): V1 README — QR D1 rationale + logo aspect note`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && grep -E "QR|D1|logo|3.5:1|0.515" templates/infostand-tent-card-a5-quer/README.md | head -5</automated>
  </verify>
  <done>
  - README.md contains a "V1 Layout: Hero Band (2026-05-09)" section.
  - README.md contains explicit QR D1 rationale (cites 17/33 ≈ 0.515 mm/module).
  - README.md contains logo aspect note (cites 3.5:1 wordmark + 38×10.86 mm rendered).
  - README.md contains photo crop note (cites crop_focus + #13).
  - No "claude" / AI attribution.
  - Commit message exactly: `20: docs(infostand-tent-card): V1 README — QR D1 rationale + logo aspect note`.
  </done>
</task>

<task type="auto">
  <name>Task 8 (T08): Smoke test additions + spec rewrite + NEW geometry tests</name>
  <files>templates/_smoke/test_infostand_tent_card_a5_quer.py, templates/_specs/infostand-tent-card-a5-quer.md, tools/sla_lib/tests/test_infostand_tent_card_geometry.py</files>
  <action>
  Three sub-files in one task (combined per RESEARCH §"Suggested PR shape" T08 — they are all "verify+document" concerns).

  ── Sub-task 8a: Extend smoke test ──
  Edit `templates/_smoke/test_infostand_tent_card_a5_quer.py`. Existing 9 assertions stay (per locked decision #11 — additions, not full rewrite). One bound relaxation + 6 new assertions:

  RELAX: `test_impressum_above_fold` — change the bound from `≤ 102` to `≤ 105`. Update docstring/comment to: "Impressum sits inside Footer-Strip Panel A which extends to apex y=105; bound relaxed in V1."

  ADD assertions (6 new test methods):
  - `test_hero_band_polygons_present`: parses SLA via lxml, finds PAGEOBJECT with ANNAME="Hero-Band Panel A" and "Hero-Band Panel B"; asserts each has FCOLOR="Dunkelgrün" (or document's color reference equivalent — match existing color-resolution pattern in current smoke tests) and LAYER="0".
  - `test_photo_backing_polygons_present`: same pattern; ANNAMEs "Photo-Backing Panel A" and "Photo-Backing Panel B"; FCOLOR="Dunkelgrün"; LAYER="0".
  - `test_footer_strip_polygons_present`: same; ANNAMEs "Footer-Strip Panel A" and "Footer-Strip Panel B"; FCOLOR="Hellgrün"; LAYER="0".
  - `test_payoff_panel_a_present`: ANNAME="Pay-off Panel A"; PSTYLE-style attribute = "tent/payoff" (or whatever style attribute the SLA uses — match existing smoke pattern).
  - `test_logo_asset_is_gruene_weiss`: parses Logo Grüne (panel A) PAGEOBJECT; checks the embedded inline image data correlates to gruene-weiss.png. Quickest: assert `<PFILE>` or asset reference contains "gruene-weiss" OR the inline_image_data length is in the expected range for the 413×118 PNG. Use whichever is most stable based on existing smoke pattern.
  - `test_falz_layer_integrity`: enumerates ALL PAGEOBJECT elements; collects those with LAYER="3"; asserts the COUNT == 1 AND that singleton's ANNAME == "Mittelfalz (horizontal)". This is the Falz-layer-integrity test (per pitfall P13 / locked decision #11).

  Use lxml.etree like the existing smoke tests (verified available per RESEARCH §"Environment Availability"). Match existing helper functions / fixtures from current `test_infostand_tent_card_a5_quer.py`.

  Run smoke: `python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer` — all 9+6=15 tests should PASS.

  ── Sub-task 8b: Spec rewrite ──
  REWRITE `templates/_specs/infostand-tent-card-a5-quer.md` for V1. The existing spec is drifted (Panel B coords mismatch — RESEARCH §12). Pattern after the post-#19 `templates/_specs/themen-plakat-a3-quer.md` structure (commit c116bf6).

  Sections to include:
  1. Header (title, format A4 quer, pages 1, audience).
  2. Layout-Philosophie: V1 "Hero Band" — establishes the rotation contract for multi-panel templates; valley-fold tent-card with apex-at-table.
  3. ASCII layout diagram for V1 zones (Hero-Band 0..42 / Photo-Band 39..72 / Bullets+Termine zone 78..94 / Footer-Strip 95..105 / Falz @ 105 / mirror Panel B 105..210).
  4. Slot tables for both panels with V1 SLA coords (Panel A direct; Panel B post-rotation per the SLA math rule). Include all 24 V1 annames + Falz line.
  5. ParaStyle list (6 styles) with font + size + linesp + color + align.
  6. Constraints prose section: list all 22 constraints grouped by category (intra-Panel-A inside, intra-Panel-A adjacency, intra-Panel-B same-rotation, cross-panel mirror, cross-panel style).
  7. Brand overrides: list the 3 KEPT (line_spacing_0.9, visual_adjacency_drift, band_consistency) with reasons.

  Run spec_check (if it exists): `PYTHONPATH=tools python3 -m sla_lib.builder.spec_check infostand-tent-card-a5-quer` (exit 0 expected). If spec_check is not a separate command, structural_check covers spec coherence.

  ── Sub-task 8c: NEW geometry tests ──
  CREATE `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` (≥12 invariant-pinning assertions per locked decision #13). Pattern after `tools/sla_lib/tests/test_tueranhaenger_geometry.py` from #18 (167 lines, 12 invariants) AND `tools/sla_lib/tests/test_themen_plakat_geometry.py` from #19. Pin RELATIONSHIPS, not coordinates.

  Test setup: import `build_template` (clean doc, no inline image IO during tests):
  ```python
  from templates.infostand_tent_card_a5_quer.build import build_template
  doc = build_template()
  ```
  (Adapt the import path to the actual project layout — check existing tueranhaenger/themen_plakat geometry tests for the `sys.path` setup; reuse identical pattern.)

  TOL_MM = 0.6 (per RESEARCH §"Decision 13").

  ≥12 assertions (executor: implement at least these; add more if natural):

  1. `test_hero_bands_mirror_around_apex`: assert `(panel_a_band.y_mm + panel_a_band.h_mm/2 + panel_b_band.y_mm + panel_b_band.h_mm/2) / 2` is within TOL_MM of 105.0 for the Hero-Band pair.
  2. `test_photo_backings_mirror_around_apex`: same for Photo-Backing pair.
  3. `test_footer_strips_mirror_around_apex`: same for Footer-Strip pair.
  4. `test_hero_bands_same_size`: w_mm and h_mm match within TOL_MM.
  5. `test_photo_backings_same_size`: same.
  6. `test_footer_strips_same_size`: same.
  7. `test_logo_panel_a_inside_hero_band_a`: bbox-containment check.
  8. `test_headline_panel_a_inside_hero_band_a`: bbox-containment.
  9. `test_payoff_panel_a_inside_hero_band_a`: bbox-containment.
  10. `test_photo_inside_photo_backing_a`: Hintergrund-Mitmachen frame inside Photo-Backing Panel A.
  11. `test_cta_footer_a_inside_footer_strip_a`: bbox-containment.
  12. `test_impressum_a_inside_footer_strip_a`: bbox-containment.
  13. `test_bullets_termine_baseline_a`: y_mm equal within TOL_MM.
  14. `test_bullets_termine_height_a`: h_mm equal within TOL_MM.
  15. `test_logo_width_3M`: assert `abs(logo.w_mm - 37.8) <= 0.5` (3M ± 0.5 tol).
  16. `test_para_style_existence`: parse the saved SLA via lxml; assert presence of <STYLE> elements named "tent/headline", "tent/body", "tent/termine", "tent/impressum", "tent/payoff", "tent/cta-footer". Assert ABSENCE of "tent/cta".
  17. `test_logo_asset_is_gruene_weiss`: probe the Logo Panel A frame's inline_image_data — verify the asset is the gruene-weiss PNG (e.g. via expected size of base64 payload, OR by saving the doc and grep-ing the SLA for "gruene-weiss" or PNG header signature).
  18. `test_falz_layer_integrity`: build doc + save to a tmp SLA via `doc.save(tmp_path)`, then parse SLA via lxml; assert ONLY ONE PAGEOBJECT has LAYER="3" AND its ANNAME == "Mittelfalz (horizontal)". Assert all V1 Polygons (Hero-Band/Photo-Backing/Footer-Strip × A+B) have LAYER="0".
  19. `test_panel_a_polygons_rotation_zero`: all 3 Panel A Polygons have rotation_deg == 0.
  20. `test_panel_b_polygons_rotation_zero`: all 3 Panel B Polygons have rotation_deg == 0 (rectangles need no visual rotation).
  21. `test_panel_b_text_image_rotation_180`: Panel B Logo, Headline, Pay-off, Body, Termine, CTA-Footer, Impressum, QR all have rotation_deg == 180. Hintergrund-Mitmachen Panel B has rotation_deg == 180.

  Aim for 18-21 tests; minimum 12 per locked decision #13.

  Run tests: `python3 -m unittest tools.sla_lib.tests.test_infostand_tent_card_geometry` — all PASS expected.

  Final verification gate for T08:
  ```
  python3 -m unittest discover tools/sla_lib/tests
  python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
  bin/check-stale-previews
  ```
  All exit 0.

  AVOID: do NOT pin exact coordinates (pin relationships per #19 precedent). Do NOT call build_preview() in tests (use build_template() to skip photo IO). Do NOT add a Codex review hook. Do NOT introduce a new BrandRule.

  COMMIT: `20: test+docs(infostand-tent-card): smoke additions + spec rewrite + geometry tests`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -3 && python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer 2>&1 | tail -3 && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -3 && bin/check-stale-previews</automated>
  </verify>
  <done>
  - `templates/_smoke/test_infostand_tent_card_a5_quer.py` has 15+ assertions; `test_impressum_above_fold` bound relaxed to ≤105; 6 new V1-structure assertions added.
  - `templates/_specs/infostand-tent-card-a5-quer.md` rewritten for V1: Layout-Philosophie + ASCII zones + slot tables (24 slots) + ParaStyle list (6 styles) + 22-constraint prose + 3-brand-override prose.
  - `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` exists with ≥12 invariant-pinning tests (preferably 18-21); all PASS.
  - `python3 -m unittest discover tools/sla_lib/tests` exits 0.
  - `python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer` exits 0.
  - `structural_check --all` exits 0.
  - `bin/check-stale-previews` exits 0.
  - Commit message exactly: `20: test+docs(infostand-tent-card): smoke additions + spec rewrite + geometry tests`.
  </done>
</task>

<task type="auto">
  <name>Task 9 (T09): Brief §10 session-history row + EXECUTION.md final commit + ISSUE.md status flip</name>
  <files>shared/brand/DESIGN-SYSTEM-BRIEF.md, .issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/EXECUTION.md, .issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/ISSUE.md</files>
  <action>
  Final close-out task — three sub-files in one commit per locked decision #14.

  ── Sub-task 9a: Brief §10 session-history row ──
  Read the existing `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 section to find the table format. Append ONE row dated 2026-05-09:

  Pattern (match existing rows' columns — likely date + issue + summary + status):
  | 2026-05-09 | #20 | V1 layout for infostand-tent-card-a5-quer (Hero Band) | done |

  If §10 has more columns (e.g. "files touched", "constraints added"), match the schema. Read 5+ existing rows to infer column order.

  ── Sub-task 9b: EXECUTION.md final commit ──
  EXECUTION.md should already exist in `.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/` from the issue:execute orchestration; it is appended to throughout T01..T08 (one row per task). Append the final closing row for T09 (this task) noting:
  - Tasks completed: T01..T09
  - Files touched count (≈ 13 — list the actual count after this commit)
  - Tightenings applied beyond RESEARCH (e.g. the empirical brand_overrides verification step in T06; any restored override; logo asset fallback if used; etc.)
  - Final verification gate result: all green.

  If EXECUTION.md does NOT yet exist, CREATE it with a single-task summary row covering all of T01..T09 (the executor's standard EXECUTION.md schema — match the format used in archived issues like `.issues/archive/19-*/EXECUTION.md`).

  ── Sub-task 9c: ISSUE.md status flip ──
  Edit `.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/ISSUE.md`. In the YAML frontmatter, change:
  ```yaml
  status: open
  ```
  to:
  ```yaml
  status: done
  ```
  Leave all other frontmatter fields and the body unchanged.

  ── Final verification gate (cumulative for the whole plan) ──
  Run all of:
  ```
  cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band
  python3 -m unittest discover tools/sla_lib/tests
  python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
  bin/check-stale-previews
  ```
  All exit 0.

  AVOID: do NOT include "claude" / AI attribution in EXECUTION.md or commits. Do NOT delete any issue artifact (per `feedback_preserve_issue_artifacts.md` — archive only via separate workflow). Do NOT modify `improvements/04-infostand-tent-card.md` line 282 here — that file is workspace root, untracked, not in worktree git index (same as #17 noted in RESEARCH §16); leave for a separate manual update.

  COMMIT: `20: docs(brand,execution): brief §10 row + EXECUTION close + ISSUE status=done`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band && python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -3 && python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer 2>&1 | tail -3 && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -3 && bin/check-stale-previews && grep -E "^status:" .issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/ISSUE.md</automated>
  </verify>
  <done>
  - `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 has new row dated 2026-05-09 for issue #20.
  - `.issues/<slug>/EXECUTION.md` exists with final close-out summary.
  - `.issues/<slug>/ISSUE.md` frontmatter `status: done`.
  - Final verification gate: all 5 commands exit 0 (geometry tests + smoke + structural --all + stale-previews + grep confirms status=done).
  - Commit message exactly: `20: docs(brand,execution): brief §10 row + EXECUTION close + ISSUE status=done`.
  - No "claude" / AI attribution.
  </done>
</task>

</tasks>

<verification>
After all 9 tasks complete, run the cumulative verification gate from the worktree root:

```bash
cd /root/workspace/.worktrees/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band

# 1. NEW geometry tests (≥12 invariants per locked decision #13)
python3 -m unittest discover tools/sla_lib/tests
# expect: OK; 0 failures across all geometry test files

# 2. Smoke test for this template (15+ assertions post-T08)
python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer
# expect: OK; 15+ tests pass

# 3. structural_check for this template (22 CONSTRAINTS green)
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
# expect: 0 errors

# 4. structural_check --all (no regression on other templates)
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
# expect: 0 errors across all templates

# 5. Stale-preview detection (template.sla SHA must match preview artifacts)
bin/check-stale-previews
# expect: exit 0
```

ALL 5 commands MUST exit 0 before declaring the issue done.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria (corrected per RESEARCH.md errata):

- [x] V1 deltas applied; Panel A + Panel B implemented via the rotation-contract pattern (single source `_panel_de` for upright, `_panel_en` for rotated 180°). [T01-T04]
- [x] `template.sla` regenerates cleanly via `bin/render-gallery infostand-tent-card-a5-quer --skip-visual-diff`. [T06]
- [x] `structural_check infostand-tent-card-a5-quer` zero errors; all 22 CONSTRAINTS green; `mirrored_y(Hero-Band Panel A, Hero-Band Panel B, axis_mm=105.0)` PASSES. [T05, T06, T08 verification gate]
- [x] `structural_check --all` zero errors. [T05, T06, T08 verification gate]
- [x] `check_ci.py` passes (or its post-#25 equivalent — covered by structural_check brand-rules invocation; ci_overrides updated in T01). [T01]
- [x] `Falz` layer untouched — verified by SLA `LAYER` attribute scan in NEW geometry test `test_falz_layer_integrity` (exactly 1 PAGEOBJECT on LAYER=3, anname=`Mittelfalz (horizontal)`). [T08]
- [x] QR module-size decision documented in `templates/infostand-tent-card-a5-quer/README.md` (17/33 ≈ 0.515 mm/module v4-H D1-conformant rationale). [T07]
- [x] Brief §10 Session-History row added dated 2026-05-09. [T09]
- [x] ISSUE.md status flipped to `done`. [T09]

NOT addressed in this plan (out of scope per RESEARCH.md):
- `improvements/04-infostand-tent-card.md` line 282 cell update (workspace root file, untracked, not in worktree git index — same exclusion as #17).
- V2 / V3 layouts.
- Asset cropping for `hintergrund-mitmachen.jpg` (#13).
- URL shortening for QR (would require brand stewardship coordination).
- Codex visual review (SKIPPED per locked decision #16).
</success_criteria>
