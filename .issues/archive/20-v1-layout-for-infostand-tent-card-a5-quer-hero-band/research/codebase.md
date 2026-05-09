# Codebase research — #20 V1 layout for `infostand-tent-card-a5-quer`

Status: HIGH confidence. Every claim file:line-traced to current main; build pipeline verified live (`python3 templates/infostand-tent-card-a5-quer/build.py` + smoke 9/9 passing + structural_check 0/0/6-skipped/15-pass).

---

## 1. Current build.py inventory (line numbers from current `templates/infostand-tent-card-a5-quer/build.py`)

| Line | What | x_mm | y_mm | w_mm | h_mm | layer | rotation | anname |
|---|---|---|---|---|---|---|---|---|
| 79–88 | ParaStyle `tent/headline` | Vollkorn Black Italic 36pt linesp 40 fcolor=Dunkelgrün align=0 | | | | | | |
| 89–98 | ParaStyle `tent/body` | Gotham Narrow Book 14pt linesp 18 fcolor=Black align=0 | | | | | | |
| 99–108 | ParaStyle `tent/impressum` | Gotham Narrow Book 5pt linesp 6 fcolor=Black align=0 | | | | | | |
| 110–119 | ParaStyle `tent/cta` | Gotham Narrow Bold 11pt linesp 14 fcolor=Dunkelgrün align=0 | | | | | | |
| 120–129 | ParaStyle `tent/termine` | Gotham Narrow Book 10pt linesp 13 fcolor=Black align=0 | | | | | | |
| 152–161 | ImageFrame `Logo Grüne (panel A)` | 12 | 10 | 36 | 32 | BILDER | 0 | gruene-logo-bund-dunkel.png inline |
| 164–171 | TextFrame `Headline Panel A` | 62 | 12 | 223 | 24 | TEXT | 0 | "Klimaschutz konkret." style=tent/headline |
| 175–186 | TextFrame `Body Panel A` | 62 | 44 | 223 | 26 | TEXT | 0 | 3-bullet German body, style=tent/body |
| 192–199 | TextFrame `CTA Panel A` | 62 | 68 | 60 | 6 | TEXT | 0 | "Mitmachen — Komm zu uns!" style=tent/cta |
| 205–216 | TextFrame `Termine Panel A` | 125 | 68 | 160 | 26 | TEXT | 0 | 3-line Termine list, style=tent/termine |
| 222–234 | ImageFrame `Hintergrund-Mitmachen` | 12 | 44 | 44 | 33 | BILDER | 0 | library `kontext_infostand_szene` via `library.crop_for_frame(target_w_mm=44, target_h_mm=33)` + `pack_inline_image` (OLD pattern, NOT post-#24) |
| 245–252 | ImageFrame `QR-Code (mitmachen, panel A)` | 12 | 80 | 17 | 17 | BILDER | 0 | `samples/qr-mitmachen.png` inline |
| 256–266 | TextFrame `Impressum (Tent)` | 35 | 96 | 257 | 4 | TEXT | 0 | DE Mediengesetz §24 line, style=tent/impressum |
| 269–270 | Block `TableTentFold` | 0 | 105 | 297 | 0 | FALZ (=3) | 0 | "Mittelfalz (horizontal)" Falz spotcolor line |
| 294–302 | TextFrame `Headline Panel B` | 235 | 198 | 223 | 24 | TEXT | **180** | "Climate. Concrete." style=tent/headline. SLA bbox-corner math: pre_x=12+223, pre_y=174+24 |
| 307–319 | TextFrame `Body Panel B` | 235 | 166 | 223 | 26 | TEXT | **180** | EN body, style=tent/body. pre_x=12+223, pre_y=140+26 |
| 324–332 | TextFrame `CTA Panel B` | 122 | 142 | 60 | 6 | TEXT | **180** | "Get involved — Talk to us!" style=tent/cta. pre_y=210−68−6=136, then 136+6=142; pre_x=62+60=122 |
| 337–349 | TextFrame `Termine Panel B` | 285 | 142 | 160 | 26 | TEXT | **180** | EN Termine. pre_y=210−68−26=116, then 116+26=142; pre_x=125+160=285 |
| 354–363 | ImageFrame `Logo Grüne (panel B)` | 48 | 210 | 36 | 32 | BILDER | **180** | gruene-logo-bund-dunkel.png. pre_x=12+36=48, pre_y=178+32=210 |

Total non-Falz frames: 11 (5 Panel A + 5 Panel B + 1 Falz). 11 anname slots.

**Note on rotation convention** (build.py:272-286 docstring): "Panel B (unten, y=105..210) wird beim Falzen umgedreht — daher rotiert build.py die Panel-B-TextFrames effektiv um 180°". So Panel B is the rotated half, Panel A is the un-rotated half. The smoke test enshrines this:
- `test_panel_a_frames_not_rotated` (line 95–101): Headline/Body Panel A must have ROT=0.
- `test_panel_b_frames_rotated_180` (line 87–93): Headline/Body Panel B must have ROT=180.

**ISSUE.md §"Rotation contract" contradicts existing convention** — it says "wrap Panel A in `Group(rotation=180, around=(148.5, 52.5))`". This is a mis-specification. The geometrically correct convention for valley-fold tent-card (apex at table) is to rotate the bottom half on the flat sheet — i.e. Panel B. Rotating Panel A would force a smoke-test rewrite for backwards-incompatible reasons. **Locked decision (in RESEARCH.md): keep existing convention — Panel B is rotated, Panel A is not.** Spec terminology is preserved (`_panel_de()` / `_panel_en()` builder functions output identical local-coords primitives), but the application to the SLA inverts: `_panel_en()` (Panel B) outputs receive rotation_deg=180 + bbox-corner SLA math; `_panel_de()` (Panel A) outputs are placed directly with rotation_deg=0.

## 2. ParaStyle inventory and V1 deltas

Current ParaStyles (5):
- `tent/headline`: Vollkorn Black Italic 36 / 40 / Dunkelgrün
- `tent/body`: Gotham Narrow Book 14 / 18 / Black
- `tent/impressum`: Gotham Narrow Book 5 / 6 / Black
- `tent/cta`: Gotham Narrow Bold 11 / 14 / Dunkelgrün
- `tent/termine`: Gotham Narrow Book 10 / 13 / Black

V1 needs (per ISSUE.md §Scope + improvements/04-infostand-tent-card.md §"Variante 1"):
- **MUTATE `tent/headline`**: fontsize 36→26, linesp 40→23.4 (= 0.9 × 26), fcolor Dunkelgrün→**White** (Headline now sits on Dunkelgrün hero-band).
- **NEW `tent/payoff`**: Vollkorn Black Italic 16 / 14.4 (= 0.9 × 16) / **Gelb** / align=0. (Per spec; ISSUE.md says Italic — use existing "Vollkorn Black Italic" font name from CI.)
- **MUTATE `tent/body`**: fontsize 14→12, linesp 18→15.6, fcolor stays Black (sits on white background between hero-band and footer-strip). The bullet-list per-paragraph leading "•  " stays in run text. The new style name is conceptually `tent/bullet` but we MUTATE existing `tent/body` instead of forking — fewer ParaStyles, simpler diff. (Decision: mutate, per #19 precedent of mutating `themen-plakat/headline` linesp.)
- **NEW `tent/cta-footer`**: Gotham Narrow Bold 11 / 14 / **White** / align=0. (Sits on Hellgrün footer-strip — needs white text.)
- **MUTATE `tent/impressum`**: fontsize 5→6, linesp 6→7.8 (= 1.3 × 6), fcolor Black→**White**, align=0→2 (right-aligned). (Sits on Hellgrün footer-strip.)
- **MUTATE `tent/termine`**: fontsize 10→9, linesp 13→11.7 (= 1.3 × 9). Stays Black (white area below photo). (Optional — could keep at 10/13 if vertical fit is OK; spec implies smaller for the 16mm bullet zone.)
- **DROP `tent/cta`**: V1 deletes the `CTA Panel A` text frame (Pay-off replaces it functionally). Remove the ParaStyle, OR keep it deprecated and remove in iter-5. Recommendation: **REMOVE** (no V1 frame uses it). Update ci_overrides.non_ci_styles accordingly.

**Final ParaStyle list after V1 (6 styles):** `tent/headline` (mutated), `tent/payoff` (NEW), `tent/body` (mutated, doubles as bullet style), `tent/termine` (mutated), `tent/cta-footer` (NEW), `tent/impressum` (mutated to white right-aligned).

## 3. Polygon inventory deltas

Currently NO polygons in tent-card except the Falz `Mittelfalz (horizontal)` line. V1 adds 6 polygons (3 per panel × 2 panels):

Panel A:
- `Hero-Band Panel A`: x=−3, y=−3, w=303, h=42, fill=Dunkelgrün, layer=Hintergrund (=0), rotation=0
- `Photo-Backing Panel A`: x=−3, y=39, w=303, h=33, fill=Dunkelgrün, layer=Hintergrund, rotation=0
- `Footer-Strip Panel A`: x=−3, y=95, w=303, h=10, fill=Hellgrün, layer=Hintergrund, rotation=0

Panel B (mirror around y=105; Polygons need NO rotation since rectangles):
- `Hero-Band Panel B`: visual top y = 2×105 − (−3+42) = 171; visual bottom y = 2×105 − (−3) = 213. So x=−3, y=171, w=303, h=42, fill=Dunkelgrün, layer=Hintergrund, rotation=0
- `Photo-Backing Panel B`: visual top y = 2×105 − (39+33) = 138; bottom = 2×105 − 39 = 171. x=−3, y=138, w=303, h=33, fill=Dunkelgrün, layer=Hintergrund, rotation=0
- `Footer-Strip Panel B`: visual top y = 2×105 − (95+10) = 105; bottom = 2×105 − 95 = 115. x=−3, y=105, w=303, h=10, fill=Hellgrün, layer=Hintergrund, rotation=0

NOTE: `Footer-Strip Panel B` at y=105..115 means it ABUTS the Falz line at y=105 from below. `Footer-Strip Panel A` at y=95..105 abuts from above. Together they create a visual "double Hellgrün band" at the apex region. Visually this matches the spec's "footer at outer edge of each panel" interpretation, since each panel's outer edge is its OWN-side outermost. Wait — re-check: footer-strip should be at OUTER edge of each panel (away from apex), i.e. far from y=105. Panel A footer at y=95..105 places it AT the apex (3mm from apex). That's ADJACENT to the apex/fold. Per ISSUE.md spec: "Polygon Footer-Strip x=-3 y=95 w=303 h=10". That confirms y=95..105 — i.e. the footer ABUTS the apex from Panel A's side. After folding, this footer is at the BOTTOM of the 3D card (table side). ✓ Correct for valley-fold.

Mirroring Panel A footer (y=95..105) around y=105 → Panel B footer y=105..115. Also abuts the apex from Panel B's side. ✓

**Caveat**: Both footer-strips together form a 20mm Hellgrün band straddling the fold. This is intentional per the spec — "footer at apex side of each panel". Test expectation: visual continuity of the Hellgrün band across the Falz line.

## 4. Photo & Logo deltas

- **Photo `Hintergrund-Mitmachen`**:
  - Current: x=12, y=44, w=44, h=33 (small "stamp" beside bullets)
  - V1: x=0, y=39, w=297, h=33 (nearly-full-width band; 3mm bleed left and 3mm bleed right via `−3..300` would be fuller, but ISSUE.md spec says x=0, w=297 — leaving frame-edge at x=0 and x+w=297 inside the trim).
  - **Asset aspect mismatch**: source 1536×1024 (1.5:1); target 297×33 (9:1). The crop ratio is severe. Use post-#24 INJECT_MAP pattern (`library.inject_into_frame(item, img, target_w_mm=item.w_mm, target_h_mm=item.h_mm)`) to crop in build_preview, NOT build_template, for round-trip stability. Manifest's `crop_focus: [0.50, 0.55]` keeps the table+people in the 9:1 horizontal slab.
  - Photo-Backing Polygon (Dunkelgrün) fully covers the frame → if photo is partially missing or watermarked-only, the band still renders dark green (§7 Body-on-Green compliance maintained even sans-photo).

- **Logo `Logo Grüne (panel A)`**:
  - Current: x=12, y=10, w=36, h=32, asset=`gruene-logo-bund-dunkel.png` (G+DIE-GRÜNEN dunkelgrün on transparent)
  - V1: x=12, y=6, w=38, h=30, asset=`shared/logos/gruene-weiss.png` (white variant for Dunkelgrün hero-band).
  - V1 logo width: 38mm = 0.06 × 210 × 3 = 37.8mm + 0.2mm. Within 0.5mm tolerance of `brand:logo_size_3M`. Override REMOVABLE post-V1.
  - Asset existence: `shared/logos/gruene-weiss.png` — verified in ls earlier; present.

## 5. Constraint factory inventory (`tools/sla_lib/builder/constraints.py` + `composites.py`)

Public exports (from `tools/sla_lib/builder/__init__.py:73-89`):
- `same_y(*targets, ...)` L399
- `same_x(*targets, ...)` L408
- `same_size(*targets, axis="both"|"w"|"h", ...)` L417
- `mirrored_x(left, right, axis_mm, ...)` L433
- `mirrored_y(top, bottom, axis_mm, ...)` L443
- `inside(child, parent, ...)` L453
- `equal_gap(*targets, axis="x"|"y", gap_mm, ...)` L462
- `hierarchy(*targets, by="fontsize", ...)` L472
- `same_style(*targets, ...)` L481
- `distance_y(a, b, equals, ...)` L489
- `distance_x(a, b, equals, ...)` L498
- `aligned_below(below, above, gap_mm, ...)` L507  — **HAS rotation guard** (lines 337–343): if either target has `rotation_deg != 0`, returns `severity="warning"` with message `"rotated frame — aligned_below skipped"` (NOT an error, but documents the limitation).

**NO `Group` primitive exists.** ISSUE.md's "wrap Panel A in `Group(rotation=180, around=(148.5, 52.5))`" is a phantom abstraction. Nearest in-codebase match: `MirroredPair` composite (`composites.py:84-128`) which only repositions, doesn't rotate. Build.py emits per-frame `rotation_deg=N` directly (Polygon, ImageFrame, TextFrame all support it via `_Frame.rotation_deg` at `primitives.py:440`).

**Other constraint factories' rotation handling:**
- `same_y`, `same_x`, `same_size`: use raw `x_mm`/`y_mm`/`w_mm`/`h_mm` — work for two rotated-identically frames (both have same SLA y_mm), fail for rotated-vs-unrotated pairs.
- `inside(child, parent)`: raw bbox math (lines 198–223). FAILS when child is rotated and parent is not (or vice versa) because Scribus stores rotated-frame XPOS/YPOS at the rotated bbox top-left (≈ pre-rotation bottom-right for ROT=180), while unrotated frames store at visual top-left.
- `mirrored_x`, `mirrored_y`: raw center math. Works iff both frames have matching rotation states (both 0 or both 180).
- `same_style`: rotation-invariant ✓.

**Implication for V1 CONSTRAINTS (locked in RESEARCH.md):**
- **Inter-Panel constraints** (Panel A ↔ Panel B): only safe between Polygons (which have rotation_deg=0 in both panels — rectangles need no visual rotation). So `mirrored_y(Hero-Band Panel A, Hero-Band Panel B, axis_mm=105.0)` and `same_size(...)` work. `same_style` works for any pair.
- **Intra-Panel-A constraints** (Logo, Headline, Pay-off, Photo, Bullets, Termine, QR, CTA-Footer, Impressum, Photo-Backing, Hero-Band, Footer-Strip): all have rotation_deg=0 in Panel A. `inside`, `same_y`, `aligned_below` all work directly.
- **Intra-Panel-B constraints**: Logo/Headline/Pay-off/Photo/Bullets/Termine/QR/CTA-Footer/Impressum are rotated 180°; Polygons (Hero-Band, Photo-Backing, Footer-Strip) are not. So `inside(Logo Panel B, Hero-Band Panel B)` would fail (rotated vs unrotated mismatch). **Workaround: declare intra-Panel-B constraints only between same-rotation-state frames.** Skip `inside` Panel-B-Image-or-Text inside Panel-B-Polygon. The rule `brand:visual_adjacency_drift` will still surface adjacency warnings (KEPT as override, same as #18).

## 6. BRAND_CONSTRAINTS registry — exactly 16 rules (post-#25)

`tools/sla_lib/builder/brand_constraints.py:1525-1680`:
1. `brand:color_palette`
2. `brand:font_family`
3. `brand:line_spacing_0.9`
4. `brand:hl_sl_distance_x2`
5. `brand:logo_size_3M`
6. `brand:text_on_green`
7. `brand:bleed_3mm`
8. `brand:wahlkreuz_colored_bg`
9. `brand:inside_page`
10. `brand:spine_safety`
11. `brand:bleed_coverage`
12. `brand:image_text_overlap`
13. `brand:cover_extent_match`
14. `brand:visual_adjacency_drift`
15. `brand:image_fills_frame`   (NEW from #24)
16. `brand:band_consistency`    (NEW from #25)

#20 adds **NO new brand rules**. Registry stays at 16.

## 7. Library asset path and crop_focus

`shared/sample-images/manifest.yml` line 237-252:
- ID: `kontext_infostand_szene`
- Path: `kontext/infostand-szene.jpg`
- Native size: `1536×1024` (1.5:1 aspect)
- crop_focus: `[0.50, 0.55]` (lower-half, table+people area)
- Watermark: "Symbolfoto — KI-generiert" (auto re-stamped post-crop by `library.crop_for_frame`)

For V1 297×33 (9:1) target: `library.inject_into_frame(frame, img, target_w_mm=297, target_h_mm=33)` calls `crop_for_frame` which:
- Computes crop window of aspect 9:1 inside source 1.5:1
- Source 1536×1024; for 9:1 aspect with width=1536, height = 1536/9 ≈ 171 px. Crop window centered around `(0.50, 0.55)` of source → vertical center at y_px = 0.55 × 1024 = 563.2. Crop window: y_px in [563−85, 563+85] = [478, 648]. Final cropped JPEG: 1536×171 px (≈ 9.0:1).
- At 300dpi, 1536px/300 = 5.12 inch = 130mm wide. For frame 297mm at 300dpi, 297×300/25.4 = 3508 px wide. So source upscales 2.28× (interpolation). Acceptable for demo; print-quality marginal but `kontext_infostand_szene` is `synthetic: true` so not production-bound.
- `inject_into_frame` sets `scale_type=0` (ScaleAuto, fit-to-frame) on the ImageFrame. Cropped image aspect matches frame aspect → fills exactly, no letterbox.

**This satisfies `brand:image_fills_frame` post-#24 rule** → override REMOVABLE.

## 8. QR-Code D1 conformance arithmetic

QR PNG dimensions: 410×410 px (verified via Python PIL).
Encoding: `https://noe.gruene.at/mitmachen/` (32 chars), error correction H, box_size=10, border=4 (per `samples/manifest.yml`).
Module count: (410 / box_size_px) − 2×border_modules. With box_size=10 and border=4 modules each side: 410/10 = 41 = N_modules + 2×border = 33 + 8. So **QR is v4 (33 modules)**.

D1 minimum: 0.5 mm/module.
- 8 mm frame: 8/33 ≈ 0.242 mm/module — **fails D1.**
- 14 mm frame: 14/33 ≈ 0.424 mm/module — **fails D1.**
- 17 mm frame (current): 17/33 ≈ 0.515 mm/module ✓ (locked in #11).
- 18 mm frame: 18/33 ≈ 0.545 mm/module ✓.

V3 (29 modules) requires either fewer characters or lower error correction. URL is 32 chars, exceeds v3-H byte capacity (17 chars). Would require URL shortening — out of scope for #20 (brand stewardship coordination).

**Locked decision (in RESEARCH.md): keep QR at 17×17 mm; reposition to (12, 78, 17, 17) inside bullets/termine zone (left column). Footer-strip housing CTA-Footer + Impressum only.** Document in template README.

## 9. Smoke test contract (`templates/_smoke/test_infostand_tent_card_a5_quer.py`)

9 assertions:
1. `test_page_count` — 1 page
2. `test_trim_dimensions` — 297×210 mm
3. `test_falz_layer_present_not_printable` — `LAYERS[NAME=Falz][DRUCKEN=0]`
4. `test_falz_color_document_local_spot` — `COLOR[NAME=Falz][Spot=1]`
5. `test_mittelfalz_polygon_at_y_105` — Falz polygon at y=105 mm, w=297 mm (full width)
6. `test_four_main_text_frames_present` — annames `Headline Panel A`, `Body Panel A`, `Headline Panel B`, `Body Panel B`
7. `test_panel_b_frames_rotated_180` — Headline+Body Panel B have ROT=180
8. `test_panel_a_frames_not_rotated` — Headline+Body Panel A have ROT=0
9. `test_impressum_above_fold` — `Impressum (Tent)` bottom ≤ y=102 mm (3mm clear of fold y=105)

V1 changes affecting smoke:
- Headline/Body Panel A/B annames stay → assertions 6, 7, 8 still pass.
- Impressum bottom: V1 places Impressum at y=97, h=6 → bottom y=103. **VIOLATES assertion 9 (≤102).** Either:
  - (a) Lower Impressum to y=96, h=6 → bottom=102 ✓ (within 1mm of spec).
  - (b) Update assertion to ≤105 (since Footer-Strip extends to y=105 with no separation from fold and the spec deliberately places Impressum within Footer-Strip). Recommendation: (b) — update assertion since the spec INTENDS Impressum to live inside the apex-side Footer-Strip.

**Locked decision (RESEARCH.md): UPDATE smoke test** — relax `test_impressum_above_fold` to assert bottom ≤ y=105 (Impressum can sit inside Footer-Strip which extends to apex y=105). Also widen scope to ALL Panel-A and Panel-B frames not crossing fold (Panel A frames bottom ≤ 105; Panel B frames top ≥ 105). Plus ADD assertions for V1-specific structures: Hero-Band Panel A polygon at y=−3..39, Photo-Backing Panel A at y=39..72, Pay-off Panel A frame present, Footer-Strip both panels present, Logo asset is `gruene-weiss.png`.

## 10. Existing CONSTRAINTS (5 entries, line 386-410)

```python
CONSTRAINTS = [
    same_style("Headline Panel A", "Headline Panel B", name="panel_headline_style_consistent"),
    same_style("Body Panel A", "Body Panel B", name="panel_body_style_consistent"),
    same_style("CTA Panel A", "CTA Panel B", name="panel_cta_style_consistent"),
    same_style("Termine Panel A", "Termine Panel B", name="panel_termine_style_consistent"),
    same_size("Headline Panel A", "Headline Panel B", axis="both", name="panel_headline_size_match"),
]
```

V1 will replace this list (CTA Panel A is DELETED in V1 — `CTA-Footer Panel A/B` replaces it).

## 11. meta.yml schema (`templates/infostand-tent-card-a5-quer/meta.yml`)

Current keys: id, version, title, format, orientation, pages, preview_dpi, audience, description, build, previews_for_sla, brand_overrides (6), ci_overrides (non_ci_styles=3 + non_ci_colors=1 + non_ci_layers=1), slots (6), example_pages, preflight.

V1 changes:
- `previews_for_sla` SHA: bump after gallery regen (auto by `bin/render-gallery`).
- `brand_overrides`: REMOVE 3 (`logo_size_3M`, `image_text_overlap`, `image_fills_frame`); KEEP 3 with updated reason text (`line_spacing_0.9`, `visual_adjacency_drift`, `band_consistency`).
- `ci_overrides.non_ci_styles`: drop `tent/cta` (deleted), add `tent/payoff` and `tent/cta-footer`. New list: `[tent/headline, tent/body, tent/termine, tent/payoff, tent/cta-footer, tent/impressum]` — 6 styles.
- `slots`: rewrite to enumerate the V1 anname set. Add `hero_band_a/b`, `photo_backing_a/b`, `footer_strip_a/b`, `logo_panel_a/b` (already there, retitled white-logo), `payoff_a/b`, `cta_footer_a/b`. Update existing entries with V1 dimensions/styles.

## 12. Spec file `templates/_specs/infostand-tent-card-a5-quer.md`

Currently 314 lines. ASCII layout diagram at lines 33–65, Slot tables at 108–127. Already drifted (Panel B coords in spec don't match build.py — see RESEARCH.md note). V1 must rewrite:
- ASCII diagram for V1 zones (Hero-Band / Photo-Band / Bullets+Termine / Footer-Strip)
- Slot tables for both panels with V1 coords (post-rotation for Panel B per spec convention)
- ParaStyle list (6 styles)
- Constraints prose section (mirror Panel A↔B, inside Hero-Band, etc.)
- Layout-Philosophie updated to V1 "Hero Band"

Rewrite pattern: follow `templates/_specs/themen-plakat-a3-quer.md` post-#19 structure (commit c116bf6).

## 13. EPS / library / image embedding

V1 photo uses post-#24 INJECT_MAP idiom:
- `build_template()` returns clean Document with photo `inline_image_data=None`.
- `INJECT_MAP = {"Hintergrund-Mitmachen": "kontext_infostand_szene"}`.
- `build_preview()` calls `build_template()` then loops INJECT_MAP, resolves library ID, calls `library.inject_into_frame(frame, img, target_w_mm=frame.w_mm, target_h_mm=frame.h_mm)`. **NEVER use literal `target_w_mm=297, target_h_mm=33`** — always use live frame dims (post-#24 lesson).
- `build_doc = build_template` alias for structural_check / spec_check.
- `build()` calls `build_preview()` so emitted SLA carries injected JPEG.

## 14. Files-touched inventory (estimate)

| File | Action | Estimated LOC delta |
|---|---|---|
| `templates/infostand-tent-card-a5-quer/build.py` | major rewrite (+ build_template/build_preview split, _panel_de/_panel_en helpers, V1 layout, INJECT_MAP, CONSTRAINTS rewrite) | +220 / −150 |
| `templates/infostand-tent-card-a5-quer/meta.yml` | brand_overrides cleanup, ci_overrides update, slots rewrite, SHA bump | +20 / −15 |
| `templates/infostand-tent-card-a5-quer/template.sla` | regen by build.py | full rewrite |
| `templates/infostand-tent-card-a5-quer/preview.pdf` | regen by render-gallery | binary |
| `templates/infostand-tent-card-a5-quer/page-01.png` | regen by render-gallery | binary |
| `templates/infostand-tent-card-a5-quer/README.md` | append V1 deltas + QR D1 decision | +40 lines |
| `site/public/templates/infostand-tent-card-a5-quer/...` | mirrored copy via render-gallery | (auto) |
| `templates/_smoke/test_infostand_tent_card_a5_quer.py` | extend assertions, relax impressum y-bound, add hero-band/photo-backing/footer-strip/payoff/logo-asset checks | +60 lines |
| `templates/_specs/infostand-tent-card-a5-quer.md` | full rewrite for V1 anname set + layout zones | +50 / −80 |
| `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` | NEW invariant-pinning test file | +180 lines |
| `shared/brand/DESIGN-SYSTEM-BRIEF.md` | append §10 session-history row | +1 line |
| `.issues/<slug>/RESEARCH.md` | this file | new |
| `.issues/<slug>/PLAN.md` | next phase | new |
| `.issues/<slug>/EXECUTION.md` | execution phase | new |

## 15. Reusable patterns from #17 / #18 / #19 commits

- **#17 wahlaufruf-postkarte (commit 3d1ae11)**: ParaStyle `*-on-green` parallel pattern (NOT used here — we MUTATE existing styles instead, simpler diff). MirroredPair use for halo+wahlkreuz. `mirrored_y` constraint pioneer use.
- **#18 wahltag-tueranhaenger (commit c70cc28)**: 5 *-on-green styles, multi-page layout, NEW invariant-pinning test file `test_tueranhaenger_geometry.py` (167 lines, 12 invariants).
- **#19 themen-plakat (commit c116bf6)**: post-#24 INJECT_MAP idiom (`build_template + build_preview` split), `build_doc = build_template` alias for round-trip stability, brand_overrides cleanup (REMOVE 3 + KEEP 1 with updated reason), full spec rewrite, smoke test rewrite, NEW geometry tests. **#19 is the closest precedent for #20.**

Use #19's PLAN.md as the structural template for #20's PLAN.md.

## 16. Acceptance criteria mapping

| ISSUE.md AC | How verified |
|---|---|
| V1 deltas applied; Panel A + B implemented via rotation-contract pattern | build.py inspection + smoke test (panel-A-not-rotated, panel-B-rotated-180); `_panel_de()` and `_panel_en()` helper functions emit identical local primitives |
| `template.sla` regenerates cleanly | `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0 |
| `structural_check` zero errors; all CONSTRAINTS green; mirror_y constraint specifically validates Panel A/B at apex | `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer` returns 0 errors; constraint `hero_band_mirror_at_apex` PASS |
| `--all` stays green | `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all` 0 errors across all templates |
| `check_ci.py` passes | (verify path; legacy CI rule; if absent, equivalent is structural_check brand rules) |
| `Falz` layer untouched (verified by SLA `LAYER` attribute scan in test) | NEW geometry test: enumerate all V1 polygons, assert `LAYER` attribute = `0` (Hintergrund), never `3` (Falz) |
| QR module-size decision documented in README.md | T0X commits README.md addendum: "QR remains 17×17 mm at panel y=78 (D1 conformant 0.515 mm/module v4-H). Footer-Strip houses CTA-Footer + Impressum only." |
| Brief §10 Session-History row added | `shared/brand/DESIGN-SYSTEM-BRIEF.md` appends row dated 2026-05-09 |
| .md Session-History `Resulting issue` updated | `improvements/04-infostand-tent-card.md` line 282 cell — change `_(seed for /issue:new)_` → GitHub issue/PR URL (workspace root, untracked, not in worktree git index — same as #17 noted) |
