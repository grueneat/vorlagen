# Codebase Research — Issue #18 (V1 "Composed Hero" for `wahltag-tueranhaenger`)

**Researched:** 2026-05-09
**Worktree:** `/root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero`
**Confidence (overall):** HIGH (every finding cites file:line; geometry math verified by hand against rule semantics)

---

## 0. Executive notes for the planner

Five things worth surfacing immediately because they change the plan shape:

1. **The task description's claim that #23 added `brand:portrait_column_alignment` and `brand:image_in_container_flush` is WRONG.** Registry has 14 rules, not 16. Both proposed rules were folded into `brand:visual_adjacency_drift`'s 4-axis logic per the archived #23 PLAN.md (line 189). The wahltag template will NOT trigger those two rules — they don't exist. Only the *real* new #23 rules apply: `brand:bleed_coverage`, `brand:image_text_overlap`, `brand:cover_extent_match`, `brand:visual_adjacency_drift`. See §4 below.

2. **ISSUE.md's CONSTRAINTS list is largely a mismatch for V1's actual back layout.** It references `stat_card_1/2/3` and uses snake-case stub annames (`brand_bar_top`, `logo_weiss_front`, `kandidat_name`). V1's back is **Portrait + Visitenkarten-Footer** (NOT 3 stat cards), and existing/V1 annames are German+parenthesized (`Brand-Bar (Vorderseite)`, `Logo Grüne (weiss, top)`, `Kandidat-Name`). The CONSTRAINTS list in ISSUE.md was copy-pasted from the design doc's §"Alignment-Beziehungen" stat-card sketch; it must be rewritten against V1's real frames. See §5 below.

3. **Rule-id error in ISSUE.md.** Acceptance criterion #6 says log under `brand:hl_sub_gap_2x`. The registered id is `brand:hl_sl_distance_x2` (`tools/sla_lib/builder/brand_constraints.py:1074`). The current `meta.yml::brand_overrides` already correctly uses `brand:hl_sl_distance_x2` (`templates/wahltag-tueranhaenger/meta.yml:30`). Plan should keep `brand:hl_sl_distance_x2`; the ISSUE.md text is wrong but the meta.yml entry is right.

4. **The `brand:image_text_overlap` brand_override in meta.yml (lines 67-71) MUST be REMOVED by V1.** Predictive geometry (§6) shows V1 has zero partial overlaps — every text frame is either disjoint from or fully contained inside its background polygon/image.

5. **The V1 plan must cover BOTH ParaStyle FONTSIZE bumps (Kandidat-Name 14→18) AND new `*-on-green` parallel styles** (white text on green/yellow on green) — not just frame coords. ParaStyle changes in the spec text are sometimes invisible in coord-tables.

---

## 1. Frame inventory (current baseline) vs ISSUE.md V1 deltas

### Page 1 (Front) — 9 frames + 2 cutout polygons

| # | line | type | anname | (x, y, w, h) mm | fill / style | V1 delta | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 157-165 | `Polygon` | `Brand-Bar (Vorderseite)` | (-2, -2, 109, 22) | fill=Dunkelgrün, layer=0 | **h: 22→16** (overall y range -2..14) | ISSUE.md says "h 22→16" — emit as `h_mm=14 + BLEED_MM` to mirror current pattern |
| 2 | 171-178 | `ImageFrame` | `Logo Grüne (weiss, top)` | (10, 8, 35, 10) | local_scale=(0.240, 0.240), layer=1 | **w 35→18.9, h 10→5.7, local_scale 0.240→0.130, x stays 10 ⇒ may need x recompute** | Per ISSUE.md y stays 8 (not changed); rule `brand:logo_size_3M` will pass once 18.9mm. `kurze_kante=105mm`, M=6.3, 3M=18.9 ✓ |
| 3 | 190-198 | `Polygon` | `Hellgrün-Band (Wahlkreuz)` | (-2, 65, 109, 60) | fill=Hellgrün, layer=0 | **y 65→63, h 60→64** ⇒ (-2, 63, 109, 64), bottom 127 | Spec adds 4mm vertical breathing for Wahlkreuz |
| 4 | 200-208 | `ImageFrame` | `Wahlkreuz (Hero)` | (27.5, 70, 50, 50) | layer=1 | **x 27.5→25, y 70→70, w 50→55, h 50→55** | Centered: 25..80 horizontal, 70..125 vertical — fits inside band 63..127 |
| 5 | 212-223 | `TextFrame` | `Headline-Wahltag` | (10, 128, 85, 28) | style=tueranhaenger/headline | **y 128→138, h 28→32; linesp 30→25.2** (ParaStyle change) | linesp 25.2 = 28 × 0.9 (Quickguide-konform) |
| 6 | 226-233 | `TextFrame` | `Sub-Headline` | (10, 160, 85, 12) | style=tueranhaenger/sub | **y 160→176** | HL bottom y=170 (138+32), Sub top y=176 → gap 6mm (50% of 19.8 formula) |
| 7 | 236-247 | `TextFrame` | `Bullet-Liste` | (10, 175, 85, 60) | style=tueranhaenger/body | **y 175→200, h 60→40, fcolor Black→White** | Sits on new Hellgrün Bullets-Card |
| — | (NEW) | `Polygon` | `Hellgrün-Akzent` (proposed name) | (-2, 14, 109, 4) | fill=Hellgrün, layer=0 | **NEW** | 4mm strip directly under Brand-Bar (touches at y=14) |
| — | (NEW) | `Polygon` | `Bullets-Card` (proposed name) | (-2, 192, 109, 58) | fill=Hellgrün, layer=0 | **NEW** | Sits below Sub-Headline (y=176, h=12 → bottom y=188; 4mm gap to card top y=192) |
| 8 | 250-260 | `TextFrame` | `Impressum` | (10, 240, 85, 6) | style=tueranhaenger/impressum | **fcolor Black→White** (sitting on Bullets-Card Hellgrün) | Card y=192..250, Impressum y=240..246 fully inside |
| 9 | 263-268 | `DoorHangerCutout` | `Stanzkontur Außen` + `Stanzkontur Loch` | n/a | layer=3 | unchanged | Hole center (52.5, 42.5), radius 17.5 — sits in y=25..60 |

### Page 2 (Back) — 10 frames + 2 cutout polygons

| # | line | type | anname | (x, y, w, h) mm | fill / style | V1 delta | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 272-280 | `Polygon` | `Brand-Bar (Rückseite)` | (-2, -2, 109, 22) | fill=Dunkelgrün, layer=0 | **h 22→16** ⇒ (-2, -2, 109, 18) | mirrors front |
| 2 | 285-292 | `ImageFrame` | `Logo Grüne (weiss, back-band)` | (10, 8, 35, 10) | local_scale=(0.240, 0.240), layer=1 | **w 35→18.9, h 10→5.7, local_scale 0.240→0.130** | mirrors front |
| 3 | 303-309 | `ImageFrame` | `Logo Grüne (Bund-Dunkel, back)` | (68, 24, 18, 16) | layer=1 | **DELETE** (double-logo elimination) | Asset still used by 4 other templates (§7) — only the FRAME goes |
| — | (NEW) | `Polygon` | `Portrait-Card` (proposed name) | (15, 70, 75, 100) | fill=Hellgrün, layer=0 | **NEW** | Hellgrün backing for Portrait |
| 4 | 323-330 | `ImageFrame` | `Kandidat-Portrait` | (20, 75, 65, 85) | layer=1 | **h 85→90** (geometry stays x=20, y=75, w=65) | Inside Portrait-Card (5mm uniform inset on left/top, 5mm/5mm right/bottom) |
| 5 | 334-341 | `TextFrame` | `Kandidat-Name` | (10, 168, 85, 10) | style=tueranhaenger/cand-name (fontsize=14) | **y 168→184, fontsize 14→18, fcolor Dunkelgrün→White** | Needs ParaStyle bump or new on-green variant |
| 6 | 344-351 | `TextFrame` | `Kandidat-Position` | (10, 178, 85, 8) | style=tueranhaenger/cand-pos (fontsize=10) | **y 178→196, fcolor Black→White, opacity 100%→85%** | Opacity is non-trivial — see §10 |
| — | (NEW) | `Polygon` | `Visitenkarten-Footer` (proposed name) | (-2, 178, 109, 72) | fill=Dunkelgrün, layer=0 | **NEW** | Bottom-footer for Visitenkarten effect |
| 7 | 354-361 | `TextFrame` | `Kontakt-URL` | (10, 200, 50, 8) | style=tueranhaenger/url | **y 200→210, w 50→55, fcolor Dunkelgrün→Gelb**, NEW style `tueranhaenger/url-on-green` | |
| 8 | 364-372 | `TextFrame` | `Kontakt-Info` | (10, 210, 50, 20) | style=tueranhaenger/body | **y 210→218, w 50→55, fcolor Black→White** | use `tueranhaenger/body-on-green` |
| 9 | 382-389 | `ImageFrame` | `QR-Code (back)` | (65, 200, 30, 30) | layer=1 | **x 65→70, y 200→210, w 30→26, h 30→26** | |
| — | (NEW) | `Polygon` | `QR-Backing` (proposed name) | (68, 208, 30, 30) | fill=White, layer=0 | **NEW** white backing for QR contrast on Dunkelgrün footer | Note fill=White is NOT in `FILLED_POLYGON_FILLS` — see §6 |
| 10 | 392-402 | `TextFrame` | `Impressum (back)` | (10, 240, 85, 6) | style=tueranhaenger/impressum | **y 240→242, fcolor Black→White** | sitting on Visitenkarten-Footer Dunkelgrün |
| 11 | 406-411 | `DoorHangerCutout` | `Stanzkontur Außen` + `Stanzkontur Loch` | n/a | layer=3 | unchanged | |

**No anname mismatches.** The audit report (§11) and structural_check both find every frame by exactly the annames the build.py emits.

---

## 2. ParaStyle inventory + recommended changes

### Current ParaStyles (all template-local, all in `tueranhaenger/` namespace)

`templates/wahltag-tueranhaenger/build.py:72-141`

| name | font | fontsize | linesp | linesp_mode | align | fcolor | Used by (V1 future) |
|---|---|---|---|---|---|---|---|
| `tueranhaenger/headline` | Vollkorn Black Italic | 28 | **30** | 0 | 0 | Dunkelgrün | Headline-Wahltag (front, Hellgrün-Band background) |
| `tueranhaenger/sub` | Gotham Narrow Bold | 18 | 22 | 0 | 0 | Dunkelgrün | Sub-Headline (front, Hellgrün-Band background) |
| `tueranhaenger/body` | Gotham Narrow Book | 11 | 14 | 0 | 0 | Black | Bullet-Liste (V1: White on Hellgrün), Kontakt-Info (V1: White on Dunkelgrün) |
| `tueranhaenger/cand-name` | Gotham Narrow Bold | **14** | 16 | 0 | 0 | Dunkelgrün | Kandidat-Name (V1: 18pt White on Dunkelgrün) |
| `tueranhaenger/cand-pos` | Gotham Narrow Book Italic | 10 | 12 | 0 | 0 | Black | Kandidat-Position (V1: White 85% on Dunkelgrün) |
| `tueranhaenger/url` | Gotham Narrow Bold | 11 | 14 | 0 | 0 | Dunkelgrün | Kontakt-URL (V1: Gelb on Dunkelgrün, NEW style `url-on-green`) |
| `tueranhaenger/impressum` | Gotham Narrow Book | 6 | 7 | 0 | 0 | Black | Impressum + Impressum (back) (V1: both White) |

### Cross-template usage check

`grep -rn 'tueranhaenger/'` across templates: ZERO references from any other template. All 7 styles are template-private. **Safe to mutate** without cross-impact.

### V1 ParaStyle action list (recommended, parallels #17 `*-on-green` pattern)

ISSUE.md prescribes only TWO new styles:
- `tueranhaenger/body-on-green` (variant of body, fcolor=White)
- `tueranhaenger/url-on-green` (Vollkorn Black Italic Gelb 11pt)

But V1 actually changes fcolor on FOUR more text frames (Kandidat-Name → White, Kandidat-Position → White 85%, Impressum + Impressum (back) → White). **Three options for the planner:**

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| (A) Add `*-on-green` parallel style for every reused style | Mirrors #17 pattern; survives `same_style` constraint cleanly; styles describe semantic intent | 5+ new ParaStyle entries; verbose | **Recommended** — matches feedback in `feedback_simple_stack_for_tests.md`-adjacent feel of "explicit > clever" |
| (B) Use Run-level `fcolor` overrides | Minimal new styles; less verbose | Run.fcolor overrides are silently broken if the ParaStyle parent is re-applied; harder to grep | Acceptable fallback |
| (C) Mutate existing ParaStyle fcolor in-place | Fewest lines | Loses backward semantic (e.g. `cand-name` no longer "Dunkelgrün") and locked decision #5 from #17 explicitly forbids in-place mutation | **NO** — violates #17 pattern |

**Headline ParaStyle:** ISSUE.md V1 explicitly says `linesp 30→25.2` for Headline-Wahltag — that's a `tueranhaenger/headline` ParaStyle change (linesp 30→25.2), AND removes one violation of `brand:line_spacing_0.9`. The other 6 styles still violate (sub: 22 vs 16.2, body: 14 vs 9.9, cand-name: 16 vs 12.6, cand-pos: 12 vs 9.0, url: 14 vs 9.9, impressum: 7 vs 5.4). The brand_override for `brand:line_spacing_0.9` (meta.yml:24-29) should REMAIN with reason updated to mention the headline now passes but column-narrow constraints keep others looser. Or be more ambitious: bring ALL 7 to 0.9× and remove the override entirely (V2 ambition; not required by ISSUE.md acceptance).

**Kandidat-Name fontsize:** V1 says 14→18. Either:
- bump `tueranhaenger/cand-name.fontsize=14→18, linesp=16→16.2`, fcolor stays Dunkelgrün, AND add `tueranhaenger/cand-name-on-green` (fcolor=White, fontsize=18, linesp=16.2); OR
- one new style only `tueranhaenger/cand-name-on-green` (fontsize=18, linesp=16.2, fcolor=White) and apply it directly to the Kandidat-Name frame.

The second is cleaner (no in-place mutation). Same applies to `cand-pos-on-green`.

---

## 3. CONSTRAINTS list — current state

`templates/wahltag-tueranhaenger/build.py:431-454` — 4 constraints exist:

```python
CONSTRAINTS = [
    same_x("Headline-Wahltag", "Sub-Headline", "Bullet-Liste", "Impressum",
           name="front_panel_left_edge"),
    distance_y("Headline-Wahltag", "Sub-Headline", equals=32.0,
               name="front_hl_to_sl_distance"),
    same_style("Impressum", "Impressum (back)",
               name="impressum_style_consistent"),
    same_x("Kandidat-Name", "Kandidat-Position",
           name="back_kandidat_caption_left_edge"),
]
```

### Conflicts with V1 deltas

- `front_hl_to_sl_distance: equals=32.0` — V1 changes Headline y=128→138, Sub y=160→176 ⇒ new distance = 38mm. **Update to `equals=38.0`** OR rephrase as `aligned_below(Sub-Headline, Headline-Wahltag, gap_mm=6.0)` (HL bottom y=170 with new h=32; Sub top y=176; gap=6mm).
- `front_panel_left_edge: same_x(...)` — All frames remain at x=10 ⇒ **survives unchanged**.
- `impressum_style_consistent: same_style(Impressum, Impressum (back))` — If both Impressum frames stay on `tueranhaenger/impressum` (Run-level fcolor override route) the constraint passes. If they switch to `tueranhaenger/impressum-on-green`, both must switch together — constraint still passes. **Keep as-is, but make sure both frames stay aligned on style.**
- `back_kandidat_caption_left_edge: same_x(Kandidat-Name, Kandidat-Position)` — V1 keeps both at x=10 ⇒ **survives unchanged**.

### ISSUE.md proposed CONSTRAINTS list — anname mismatch

ISSUE.md lines 56-74 propose this CONSTRAINTS list:

```python
CONSTRAINTS = [
    same_size("brand_bar_top", "brand_bar_back", axis="h", name="brand_bar_h_pair"),
    same_x("logo_weiss_front", "logo_weiss_back", name="logo_x_mirror"),
    same_x("stat_card_1", "stat_card_2", "stat_card_3", name="stat_cards_axis"),
    same_x("stat_card_1_eyebrow", "stat_card_1_hero", "stat_card_1_body", ...),
    same_x("stat_card_2_eyebrow", "stat_card_2_hero", "stat_card_2_body", ...),
    same_x("stat_card_3_eyebrow", "stat_card_3_hero", "stat_card_3_body", ...),
    aligned_below("kandidat_name", "kandidat_position", gap_mm=12.0, ...),
    aligned_below("kontakt_info", "kontakt_url", gap_mm=8.0, ...),
]
```

**Six problems with this list:**

1. **Annames don't match V1 frames.** `brand_bar_top` should be `Brand-Bar (Vorderseite)`; `logo_weiss_front` should be `Logo Grüne (weiss, top)`; `kandidat_name` should be `Kandidat-Name`, etc.
2. **`stat_card_1/2/3` and their `_eyebrow/_hero/_body` children DO NOT EXIST in V1.** V1's back is Portrait + Visitenkarten-Footer (single Portrait + 4 text frames + QR), NOT three stat-cards. The stat-card design is from §"Alignment-Beziehungen (V1 — Anker-Verträge)" in the design doc — that section was an *aspirational* alignment sketch for a hypothetical V1 with a 3-stat back; the *actual* V1 §"Variante 1" build.py table (lines 49-76 of design doc) describes the Portrait-Footer layout. The two halves of the design doc disagree.
3. **`aligned_below("kandidat_name", "kandidat_position", gap_mm=12.0)`** has the wrong direction AND wrong gap. `aligned_below(below, above, ...)` per `tools/sla_lib/builder/constraints.py:507` — so the call should be `aligned_below("Kandidat-Position", "Kandidat-Name", gap_mm=...)`. V1 actuals: Name y=184 h=11 → bottom 195; Position y=196 → gap 1mm. So `aligned_below("Kandidat-Position", "Kandidat-Name", gap_mm=1.0)`.
4. **`aligned_below("kontakt_info", "kontakt_url", gap_mm=8.0)`** — V1 actuals: URL y=210 h=8 → bottom 218; Info y=218 → gap 0mm. So `aligned_below("Kontakt-Info", "Kontakt-URL", gap_mm=0.0)`.
5. The brand-bar mirror IS valid: `same_size("Brand-Bar (Vorderseite)", "Brand-Bar (Rückseite)", axis="h")` AND `same_x("Logo Grüne (weiss, top)", "Logo Grüne (weiss, back-band)")` — but the front Brand-Bar y=-2 h=18 vs back Brand-Bar y=-2 h=18 → both 18 ⇒ same_size axis="h" passes.
6. Kandidat-Name fontsize 14→18 means `same_style(Impressum, Impressum (back))` constraint covers a different concern from any constraint touching cand-name. ISSUE.md doesn't propose that constraint — current build.py has it. **Keep it.**

### Recommended V1 CONSTRAINTS list (for the planner to refine)

```python
CONSTRAINTS = [
    # Symmetry pairs (front-back mirror)
    same_size(
        "Brand-Bar (Vorderseite)", "Brand-Bar (Rückseite)",
        axis="h", name="brand_bar_h_pair",
    ),
    same_x(
        "Logo Grüne (weiss, top)", "Logo Grüne (weiss, back-band)",
        name="logo_weiss_x_mirror",
    ),
    # Front-panel left-edge alignment (was current)
    same_x(
        "Headline-Wahltag", "Sub-Headline", "Bullet-Liste", "Impressum",
        name="front_panel_left_edge",
    ),
    # Front HL→Sub gap (V1: 6mm = 0.5×Quickguide formula; declared so the
    # adjacency-drift rule sees a tight tolerance, NOT to override
    # brand:hl_sl_distance_x2)
    aligned_below(
        "Sub-Headline", "Headline-Wahltag", gap_mm=6.0,
        name="front_hl_to_sub",
    ),
    # Front Bullets-Card encloses Bullets and Impressum (front)
    inside("Bullet-Liste", "Bullets-Card", name="bullets_inside_card"),
    inside("Impressum", "Bullets-Card", name="impressum_front_inside_card"),
    # Wahlkreuz centered on Hellgrün-Band horizontally
    # (Wahlkreuz x=25, w=55 → center 52.5; band x=-2, w=109 → center 52.5)
    # Use mirrored_x against page center 52.5 (doc-level constant) — but
    # mirrored_x compares TWO frames. Use same_x on the band & wahlkreuz
    # plus equality-of-center via distance_x against 0 — or skip; the audit
    # surfaces the relationship via center-x.
    # Back-panel left-edge alignment for caption block (was current)
    same_x(
        "Kandidat-Name", "Kandidat-Position",
        name="back_kandidat_caption_left_edge",
    ),
    # Back: Visitenkarten-Footer encloses URL/Info/Impressum (back)
    inside("Kontakt-URL", "Visitenkarten-Footer", name="kontakt_url_in_footer"),
    inside("Kontakt-Info", "Visitenkarten-Footer", name="kontakt_info_in_footer"),
    inside("Impressum (back)", "Visitenkarten-Footer", name="impressum_back_in_footer"),
    # Back: Portrait inside Portrait-Card
    inside("Kandidat-Portrait", "Portrait-Card", name="portrait_in_card"),
    # Back: Name and Position adjacency
    aligned_below(
        "Kandidat-Position", "Kandidat-Name", gap_mm=1.0,
        name="back_name_to_position",
    ),
    # Back: URL and Info adjacency (zero-gap ⇒ touching)
    aligned_below(
        "Kontakt-Info", "Kontakt-URL", gap_mm=0.0,
        name="back_url_to_info",
    ),
    # Back: Impressum style consistency (was current)
    same_style(
        "Impressum", "Impressum (back)",
        name="impressum_style_consistent",
    ),
]
```

**Tolerance pin:** All factories default to `tolerance_mm=0.5`. V1 deltas should hit declared values within ±0.5mm; declarations that drift further will trigger `brand:visual_adjacency_drift` "declaration disagrees with actual geometry" (see `tools/sla_lib/builder/brand_constraints.py:976-989`).

---

## 4. Post-#23 rule applicability for V1 — predictive check

### Registered rules (14 total) — `tools/sla_lib/builder/brand_constraints.py:1052-1171`

```
1.  brand:color_palette
2.  brand:font_family
3.  brand:line_spacing_0.9
4.  brand:hl_sl_distance_x2          ← ISSUE.md mis-spells as brand:hl_sub_gap_2x
5.  brand:logo_size_3M
6.  brand:text_on_green
7.  brand:bleed_3mm
8.  brand:wahlkreuz_colored_bg
9.  brand:inside_page                 ← Issue #14
10. brand:spine_safety                ← Issue #22
11. brand:bleed_coverage              ← Issue #23 (NEW)
12. brand:image_text_overlap          ← Issue #23 (NEW)
13. brand:cover_extent_match          ← Issue #23 (NEW)
14. brand:visual_adjacency_drift      ← Issue #23 (replaces undeclared_alignment_drift)
```

**The task description listed `brand:portrait_column_alignment` and `brand:image_in_container_flush` as new. They do NOT exist in the registry.** Per `.issues/archive/23-…/PLAN.md:189`, both were folded into `brand:visual_adjacency_drift`'s 4-axis dx_left/dx_right/dy_top/dy_bottom logic. Confidence: HIGH (verified by `grep` of source).

### Per-rule prediction for V1

#### `brand:bleed_coverage` — **NO-OP**
Early returns when `facing_pages == False` (`brand_constraints.py:633-634`). build.py sets `facing_pages=False` (`templates/wahltag-tueranhaenger/build.py:59`). **Will never fire.** Confidence: HIGH.

#### `brand:image_text_overlap` — **PASS (after V1)**
Predictive geometry check, full mathematical walk:

V1 shapes in scope (ImageFrames + filled-polygons with `fill ∈ {Dunkelgrün, Hellgrün, Magenta, Gelb}`):

| Page | Shape | Bbox (x0, y0, x1, y1) mm |
|---|---|---|
| 1 | `Brand-Bar (Vorderseite)` Dunkelgrün | (-2, -2, 107, 14) |
| 1 | `Logo Grüne (weiss, top)` ImageFrame | (10, 8, 28.9, 13.7) |
| 1 | `Hellgrün-Akzent` Hellgrün | (-2, 14, 107, 18) |
| 1 | `Hellgrün-Band (Wahlkreuz)` Hellgrün | (-2, 63, 107, 127) |
| 1 | `Wahlkreuz (Hero)` ImageFrame | (25, 70, 80, 125) |
| 1 | `Bullets-Card` Hellgrün | (-2, 192, 107, 250) |
| 2 | `Brand-Bar (Rückseite)` Dunkelgrün | (-2, -2, 107, 14) |
| 2 | `Logo Grüne (weiss, back-band)` ImageFrame | (10, 8, 28.9, 13.7) |
| 2 | `Portrait-Card` Hellgrün | (15, 70, 90, 170) |
| 2 | `Kandidat-Portrait` ImageFrame | (20, 75, 85, 165) |
| 2 | `Visitenkarten-Footer` Dunkelgrün | (-2, 178, 107, 250) |
| 2 | `QR-Code (back)` ImageFrame | (70, 210, 96, 236) |
| — | `QR-Backing` (V1 white, fill=White) — **out of scope** (White not in `FILLED_POLYGON_FILLS`) | (68, 208, 98, 238) |

V1 text frames:

| Page | TextFrame | Bbox (x0, y0, x1, y1) mm |
|---|---|---|
| 1 | `Headline-Wahltag` | (10, 138, 95, 170) |
| 1 | `Sub-Headline` | (10, 176, 95, 188) |
| 1 | `Bullet-Liste` | (10, 200, 95, 240) |
| 1 | `Impressum` | (10, 240, 95, 246) |
| 2 | `Kandidat-Name` | (10, 184, 95, 195) |
| 2 | `Kandidat-Position` | (10, 196, 95, 204) |
| 2 | `Kontakt-URL` | (10, 210, 65, 218) |
| 2 | `Kontakt-Info` | (10, 218, 65, 238) |
| 2 | `Impressum (back)` | (10, 242, 95, 248) |

Walk: for each (shape, text) pair, bbox-overlap → check `txt_inside ∨ shape_inside ∨ disjoint`.

**Page 1 violations check:**

- `Brand-Bar (Vorderseite)` (-2..107, -2..14) vs all text — no text in y<14 region. Disjoint ✓.
- `Hellgrün-Akzent` (-2..107, 14..18) vs all text — no text in y<63. Disjoint ✓.
- `Hellgrün-Band (Wahlkreuz)` (-2..107, 63..127) vs all text — Headline y=138..170 > 127. Disjoint ✓.
- `Bullets-Card` (-2..107, 192..250) vs:
  - `Bullet-Liste` (10..95, 200..240): `txt_inside`? sx0=-2≤10, tx1=95≤107, sy0=192≤200, ty1=240≤250 ⇒ **fully inside ✓**.
  - `Impressum` (10..95, 240..246): same check ⇒ **fully inside ✓**.
  - Headline (10..95, 138..170), Sub (10..95, 176..188): both y_max < 192 ⇒ **disjoint ✓**.
- `Wahlkreuz (Hero)` (25..80, 70..125) vs all text — Headline y=138 > 125. Disjoint ✓.
- `Logo Grüne (weiss, top)` (10..28.9, 8..13.7) vs all text — disjoint ✓.

**Page 2 violations check:**

- `Brand-Bar (Rückseite)` (-2..107, -2..14) vs all text — disjoint ✓.
- `Portrait-Card` (15..90, 70..170) vs:
  - `Kandidat-Portrait` (20..85, 75..165): inside (this is image-vs-polygon, image is "shape" — pair is shape-vs-shape, not in scope; rule only checks shape×text).
  - All text frames y_min ≥ 184 > 170 ⇒ disjoint with all texts ✓.
- `Kandidat-Portrait` (20..85, 75..165) vs all text — disjoint (texts y ≥ 184) ✓.
- `Visitenkarten-Footer` (-2..107, 178..250) vs:
  - `Kandidat-Name` (10..95, 184..195): `txt_inside`? sx0=-2≤10, tx1=95≤107, sy0=178≤184, ty1=195≤250 ⇒ **fully inside ✓**.
  - `Kandidat-Position` (10..95, 196..204): inside ✓.
  - `Kontakt-URL` (10..65, 210..218): inside ✓.
  - `Kontakt-Info` (10..65, 218..238): inside ✓.
  - `Impressum (back)` (10..95, 242..248): inside ✓.
- `QR-Code (back)` (70..96, 210..236) vs:
  - `Kontakt-URL` (10..65, 210..218): `tx1=65 < sx0=70` ⇒ disjoint ✓.
  - `Kontakt-Info` (10..65, 218..238): same disjoint ✓.
  - All other texts: y disjoint or x disjoint ✓.

**Conclusion: V1 will PASS `brand:image_text_overlap` cleanly.** The pre-applied override at `meta.yml:67-71` MUST BE REMOVED in the V1 commit. Confidence: HIGH (geometry is deterministic; rule semantics in `brand_constraints.py:744-805` confirmed).

#### `brand:cover_extent_match` — **PASS (after V1)**
Rule fires only on **vertically-touching** full-width frames (`w >= 0.95 * page_w`, touch tolerance 0.5mm). page_w=105mm → 0.95×105 = 99.75mm. Full-width frames in V1: Brand-Bar (109mm), Hellgrün-Akzent (109mm), Hellgrün-Band Wahlkreuz (109mm), Bullets-Card (109mm), Visitenkarten-Footer (109mm). All extend x=-2..107.

**Vertical-touch pairs to check (touch_tolerance_mm=0.5):**

Page 1:
- `Brand-Bar (Vorderseite)` (y0=-2, y1=14) ↔ `Hellgrün-Akzent` (y0=14, y1=18): touch at y=14 ✓. Both x=-2..107 ⇒ extents match ✓ PASSES.
- `Hellgrün-Akzent` (y1=18) ↔ `Hellgrün-Band (Wahlkreuz)` (y0=63): no touch (45mm gap).
- `Hellgrün-Band (Wahlkreuz)` (y1=127) ↔ `Bullets-Card` (y0=192): no touch (65mm gap).
- All other pairs: no touch.

Page 2:
- `Brand-Bar (Rückseite)` (y0=-2, y1=14) ↔ `Visitenkarten-Footer` (y0=178): no touch.
- `Visitenkarten-Footer` is the only full-width on page 2 below brand bar.

**Conclusion: PASS.** Confidence: HIGH.

#### `brand:visual_adjacency_drift` — **WARNINGS expected unless CONSTRAINTS list captures every adjacency**

The current `meta.yml::brand_overrides[brand:visual_adjacency_drift]` (lines 61-66) silences this rule until V1 lands. **V1 must remove this override AND populate CONSTRAINTS.** The audit (§11) lists ~59 candidate adjacencies on the current geometry. After V1's geometry shifts, the audit will list a different (probably similarly-sized) set. Strategy:

- Use the recommended CONSTRAINTS list in §3 — covers ~12 declared pairs.
- Run `bin/audit-alignment wahltag-tueranhaenger` after V1 to capture remaining undeclared pairs.
- For each remaining pair: either add a constraint (if intentional) or fix geometry (if accidental).
- The `--all` baseline currently has 122 warnings (almost all Zeitung); adding a few wahltag warnings is acceptable per the locked decision #5 in #22, but acceptance #4 ("`structural_check --all` stays green") technically allows warnings (only errors break "green"). Confirm with planner.

**Tolerance trap:** the new `brand:visual_adjacency_drift` rule re-runs each declaration against actual geometry (`brand_constraints.py:964-991`). If the CONSTRAINTS list says `aligned_below(Sub-Headline, Headline-Wahltag, gap_mm=6.0)` but the actual gap is 5.7mm, the rule emits "declaration disagrees with actual geometry" — encode-and-silence no longer works. **Pin every gap to within ±0.5mm of the actual.**

#### `brand:hl_sl_distance_x2` — **STILL OVERRIDE NEEDED**
V1 HL bottom y=170, Sub top y=176 → gap 6mm; rule expects baseline_X×2 = 5.4×2 = 10.8mm ±1.0mm. 6 vs 10.8 ⇒ violates. **Override MUST stay** (currently `meta.yml:30-37`). ISSUE.md acceptance #6 confirms this with the rule-id correction (`brand:hl_sl_distance_x2`, NOT `brand:hl_sub_gap_2x`).

#### `brand:line_spacing_0.9` — **STILL OVERRIDE NEEDED** (unless all 7 styles fixed)
V1 fixes only `tueranhaenger/headline` (linesp 30→25.2); the other 6 styles still violate. Override stays unless planner chooses to fix all of them.

#### `brand:logo_size_3M` — **OVERRIDE CAN BE REMOVED**
V1 brings both white logos to 18.9mm = 3×M. Bund-Dunkel back logo is DELETED in V1. After V1: only the two white logos remain, both at 18.9mm. **Remove the override** (currently `meta.yml:37-42`).

#### `brand:bleed_3mm` — **OVERRIDE STAYS**
Template uses 2mm bleed for die-cut. Permanent override.

#### `brand:wahlkreuz_colored_bg` — **OVERRIDE STAYS** (or can be removed if Hellgrün-Band still overlaps Wahlkreuz)
V1: Wahlkreuz (25..80, 70..125) overlaps Hellgrün-Band (-2..107, 63..127). The rule (`brand_constraints.py:342-374`) checks for overlapping non-self polygon with fill in (Dunkelgrün, Hellgrün, Magenta). The Hellgrün-Band Polygon's anname is `Hellgrün-Band (Wahlkreuz)` ≠ Wahlkreuz frame's anname `Wahlkreuz (Hero)` ⇒ they're distinct primitives ⇒ rule should now PASS (the band IS an overlapping Hellgrün polygon). **The override may finally be removable.** Pre-merge, run structural_check with the override removed to confirm.

#### `brand:font_family` — **OVERRIDE STAYS**
`tueranhaenger/cand-pos` uses Gotham Narrow Book Italic, not in `shared/ci.yml::fonts`. Override (`meta.yml:55-60`) stays.

#### `brand:text_on_green` — **PASSES**
Rule looks for white-fcolor TextFrames whose paragraph_style starts with `^ci/(h|headline)` (`brand_constraints.py:287-291`). V1 uses `tueranhaenger/*` styles — none start with `ci/h*`. Rule no-op for this template.

#### `brand:inside_page` — **PASS**
All V1 frame bboxes computed: max overshoot is ≤2mm (the 109mm-wide bleed-extending polygons go to x=-2 and x=107; bleed=2mm; so x0=-bleed=-2 ✓, x1=page_w+bleed=107 ✓; y similarly ✓). Confidence: HIGH.

#### `brand:spine_safety` — **NO-OP** (single-page doc, facing_pages=False).
#### `brand:color_palette` — **PASSES** (all colors in palette).

---

## 5. Rule-id correctness check

ISSUE.md acceptance #6 says "log HL/Sub-Gap deviation as `meta.yml::brand_overrides` entry referencing rule `brand:hl_sub_gap_2x`".

Actual registered id: `brand:hl_sl_distance_x2` (`tools/sla_lib/builder/brand_constraints.py:1074`).

Current `meta.yml` already correctly uses `brand:hl_sl_distance_x2` (`meta.yml:30`). **The plan should keep `brand:hl_sl_distance_x2`. ISSUE.md acceptance text is wrong — note the correction in the plan and execution log.**

---

## 6. Post-#23 rule applicability for V1 — see §4

(Section §4 covers all 14 rules with verdicts. No further action needed here.)

---

## 7. INJECT_MAP — current state, V1 needs

This template uses NO inject system (no `INJECT_MAP` in build.py). Text content is hard-coded in build.py (e.g. `"Heute ist"`, `"Wahltag."`, `"Wähle Grün."`, `"Stefan Beispiel"`, `"Bürgermeisterkandidat Mödling"`, `"gruene-moedling.at"`, etc.). V1 changes coords + ParaStyles + Polygons but **does not require any text content edits** — same hard-coded strings.

Portrait is loaded via `library.load("portrait_stefan", optional=True)` (`build.py:317`). V1 keeps this exact pattern.

---

## 8. Asset availability

| Asset | Path | Size | V1 Status |
|---|---|---|---|
| `gruene-weiss.png` | `shared/logos/gruene-weiss.png` | 7411 bytes | Available ✓; V1 uses on both pages at w=18.9 h=5.7 |
| `wahlkreuz.png` | `shared/assets/wahlkreuz.png` | 81019 bytes | Available ✓; V1 uses at 55×55 |
| `gruene-logo-bund-dunkel.png` | `shared/logos/gruene-logo-bund-dunkel.png` | (present) | V1 deletes the FRAME, not the asset; asset remains used by 4 other templates (`grep -rln gruene-logo-bund-dunkel templates/`) — themen-plakat, wahlaufruf-postkarte, infostand-tent-card, kandidat-falzflyer |
| `portrait_stefan` library | `tools/sla_lib/builder/library/...` | — | Available ✓ (verified `library.load('portrait_stefan', optional=True)` returns non-None) |
| `qr-back.png` | `templates/wahltag-tueranhaenger/samples/qr-back.png` | (present) | V1 keeps; resized to 26×26 frame (was 30×30); white backing polygon under it |

All assets present. No new assets introduced by V1.

---

## 9. Reference-SLA status (`previews_for_sla` SHA)

`templates/wahltag-tueranhaenger/meta.yml:20`:

```yaml
previews_for_sla: 6a744dff92c206606b33d35f96f1892d71266350d804ac6aea719a0c5248d8be
```

`original_sla` is **not present** in meta.yml ⇒ this template is DSL-only (no upstream original). Per `tools/check_stale_previews.py:74-88`, the stale-check compares the SHA256 of the current `template.sla` against `previews_for_sla`. V1 changes geometry → SHA changes → `bin/check-stale-previews` fails CI until re-run.

**Mandatory post-V1 step:** `bin/render-gallery wahltag-tueranhaenger --skip-visual-diff` — this regenerates the previews and updates `previews_for_sla` SHA in meta.yml (per `tools/render_pipeline.py:291-323`). The plan must include this as a build step.

`site/src/content/templates/wahltag-tueranhaenger.md` ALSO has `previews_for_sla: 5fcc602e...` (a different SHA). The site catalog regenerates from meta.yml — confirm by reading the catalog generator (suggest the planner trace `tools/_authoring/` or `bin/render-gallery` to confirm side-effects).

---

## 10. Spec file (`templates/_specs/wahltag-tueranhaenger.md`)

420-line spec, organized as: header YAML → audience → ASCII layout → Constraints → Stanzkontur → Slot tables (front + back) → EPS strategy → Background-color contract → Falz/Stanze → Brand-Hierarchy contract → Print-Hints → Mediengesetz/NRWO/Style hygiene → Codex demo manifest.

V1 will invalidate **most** of this spec:

| Section | Status after V1 |
|---|---|
| ASCII layout (lines 30-104) | Stale — V1 changes Brand-Bar height, adds Hellgrün-Akzent, Bullets-Card, Portrait-Card, Visitenkarten-Footer |
| Constraints (lines 107-122) | Stale: Brand-Bar y=5..20 → V1 y=-2..14; Hellgrün-Band y=65..125 → V1 y=63..127; Bullets-Card zone is new |
| Slot tables (lines 145-318) | Stale — every coordinate has changed; new polygon slots needed |
| Brand-Hierarchy (lines 348-358) | Stale — Kandidat-Name fontsize 14→18; fcolor changes for several |
| EPS strategy (lines 319-329) | Unchanged — Wahlkreuz still at Hellgrün |
| Codex demo manifest (lines 405-419) | Unchanged |
| Mediengesetz/NRWO sections | Unchanged |

**Recommendation:** Spec rewrite is required (per #17 pattern, where `templates/_specs/wahlaufruf-postkarte-a6-quer.md` was rewritten for the V1 layout). Acceptance criteria don't explicitly mandate it but the spec serves as designer documentation; leaving it stale will degrade the codebase.

---

## 11. Smoke test impact (`templates/_smoke/test_wahltag_tueranhaenger.py`)

Test classes/assertions and V1 impact:

| Test | Asserts | V1 impact |
|---|---|---|
| `test_page_count` | 2 PAGEs | unchanged ✓ |
| `test_trim_dimensions` | 105×250mm | unchanged ✓ |
| `test_bleed_2mm` | 2mm bleed | unchanged ✓ |
| `test_stanzkontur_layer_present_not_printable` | Stanzkontur layer DRUCKEN=0 | unchanged ✓ |
| `test_stanzkontur_layer_top_of_stack` | Stanzkontur is highest LEVEL | unchanged ✓ |
| `test_stanzkontur_color_document_local` | Stanzkontur color isSpot=1 | unchanged ✓ |
| `test_stanzkontur_polygons_present_on_layer` | ≥4 Stanz polys (2 per page) | unchanged ✓ |
| `test_stanzkontur_hole_circle_has_many_segments` | Stanzkontur Loch path ≥36 L cmds | unchanged ✓ |
| `test_wahlkreuz_on_hellgruen_band` | ≥1 Hellgrün polygon on front | passes still — V1 has Hellgrün-Akzent + Hellgrün-Band + Bullets-Card on front ✓ |
| `test_wahlkreuz_inline_image` | `Wahlkreuz (Hero)` is inline image | passes still (frame anname unchanged) ✓ |
| `test_existing_postkarte_round_trip_no_critical` | Postkarte sla_diff critical=0 | unrelated ✓ |

**No smoke test breakage expected.** No new assertions strictly required (acceptance #5 doesn't ask), but planner could add a smoke test for the Visitenkarten-Footer Dunkelgrün polygon and the QR-Backing white polygon for V1-specific structure.

**Adopt the zeitung-geometry-test pattern** (`tools/sla_lib/tests/test_zeitung_geometry.py`) for any new V1 invariant tests — pin RELATIONSHIPS not absolute coords:
- `Brand-Bar (Vorderseite).h_mm == Brand-Bar (Rückseite).h_mm` within 0.5mm
- `Logo Grüne (weiss, top).x_mm == Logo Grüne (weiss, back-band).x_mm`
- `Bullet-Liste` bbox fully inside `Bullets-Card` bbox
- `Kandidat-Portrait` bbox fully inside `Portrait-Card` bbox
- Visitenkarten-Footer fills the bottom 72mm + bleed
- Hellgrün-Akzent touches Brand-Bar bottom (y_min == brand_bar.y_max)

---

## 12. `bin/audit-alignment wahltag-tueranhaenger` live output (current geometry)

Captured 2026-05-09 (current build, pre-V1).

**Page 1 stats:**
- primitives: 10
- declared pairs: 6
- suspicious-undeclared adjacencies: **25**

**Page 2 stats:**
- primitives: 12
- declared pairs: 1
- suspicious-undeclared adjacencies: **34**

Most adjacencies are obvious x=10 left-margin alignments (5 frames at x=10 → 10 pairs) plus Stanzkontur-relative axis matches (most frames vs Stanzkontur Außen at x=0 → 10mm drift).

**Useful output for the planner:** the audit output for V1's *new* geometry (run after V1 lands) will produce ~10-15 truly-meaningful undeclared pairs. Use those to populate the CONSTRAINTS list. The current-geometry audit is mostly noise — it doesn't reflect V1.

Full output: 201 lines, captured by `bin/audit-alignment wahltag-tueranhaenger 2>&1` from worktree root.

---

## 13. Open questions from ISSUE.md — empirical answers

### Q1: Doppel-Logo back-band — was `Logo Grüne (Bund-Dunkel, back)` a deliberate Bund-migration display or transitional artifact?

**Empirical evidence (HIGH confidence):**
- The frame was added in iter-3 (`build.py:294-309` comment explicitly says "iter-3: Brand-Bund logo on the white area below the Brand-Bar. Reinforces brand recognition on the contact side of the door-hanger.").
- It's at 18×16mm — 95% of `brand:logo_size_3M` (18.9mm). The 0.9mm undersize was logged in `meta.yml::brand_overrides[brand:logo_size_3M]` with "kept for back-content compactness".
- It overlaps the loch-zone (y=24..40 → frame top y=24 vs hole y_top=25..60). Currently the cutout is on a higher LEVEL so the loch covers the logo at print time — but during proofing the logo appears INSIDE the loch zone, which is iconic of "transitional artifact" not "deliberate".
- The audit warns axis-y drift 1.00mm vs `Stanzkontur Loch` (back-band logo at y=24..40 vs hole top y=25..60).

**Recommendation: DELETION IS SAFE and aesthetically correct.** Audit + iter-3 rationale + 95% scale-violation strongly suggest this was a "stuff more brand on it" iter-3 addition that V1 cleans up. Default assumption stands; no brand-stewardship rollback expected.

### Q2: HL/Sub-Gap formula 50% under (Sub at y=176 vs y=190 strict)

**Recommendation: log as `meta.yml::brand_overrides[brand:hl_sl_distance_x2]` with reason "format-pragmatic 250mm vertical — V1 layout intentionally compresses HL→Sub gap to 6mm (50% of 19.8mm formula) to fit two-zone composition (Hero + Bullets-Card) within the column. See issue #18."** The override is already present (meta.yml:30-37); just refresh the reason text to mention #18. **CRITICAL: use the registered id `brand:hl_sl_distance_x2`, NOT the ISSUE.md typo `brand:hl_sub_gap_2x`.**

### Q3: Bullets-Card Hellgrün height (58mm) — Druck-Kosten-Sensibilität

V1 spec: Polygon x=-2 y=192 w=109 h=58. Hellgrün is a CMYK color with 100% Yellow + 69% Cyan = high ink. Coverage area: 109×58 = 6322 mm² = ~12.5% of page area. 

**Recommendation:** Defer to user/planner. If "yes" → reduce to 38mm (y=192 h=38, ends y=230 — still encloses Bullets y=200..240 partially BUT cuts Bullets bottom edge below the card; not a drop-in change). For the 58mm-cap strategy, keep V1 coords. The planner may want to ask the user explicitly. CONTEXT.md (if it exists) likely has the answer.

---

## 14. Stanzkontur layer integrity

V1 adds 5 new Polygons. **None should write to `LAYER_STANZKONTUR` (layer index 3).** All V1 polygons are background polygons (Hellgrün-Akzent, Bullets-Card, Portrait-Card, Visitenkarten-Footer, QR-Backing) belonging on `LAYER_HINTERGRUND` (layer index 0). The existing `DoorHangerCutout` blocks on layer 3 are UNCHANGED.

Layer constants from build.py:46-49:
```
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_STANZKONTUR = 3
```

V1 emit pattern (recommended):
```python
page0.add(Polygon(
    x_mm=-BLEED_MM, y_mm=14, w_mm=TRIM_W_MM + 2*BLEED_MM, h_mm=4,
    fill="Hellgrün", layer=LAYER_HINTERGRUND, anname="Hellgrün-Akzent",
))
```

Verify: every `Polygon(...)` call in V1 uses `layer=LAYER_HINTERGRUND` (or `LAYER_BILDER` if QR-Backing is treated as image-layer; spec is ambiguous — recommend `LAYER_HINTERGRUND` since it's a background fill polygon, NOT an image).

---

## 15. Hole-zone check — V1 polygons vs hole

35-mm hole at center (52.5, 42.5), radius 17.5 → bbox (35, 25, 70, 60).

V1 polygon overlaps:
- Brand-Bar V1 (y=-2..14) — above hole top (y=25) ✓
- Hellgrün-Akzent V1 (y=14..18) — above hole top ✓
- Hellgrün-Band V1 (y=63..127) — below hole bottom (y=60) ✓ (3mm gap)
- Bullets-Card V1 (y=192..250) — far below ✓
- Visitenkarten-Footer V1 (y=178..250) — far below ✓
- Portrait-Card V1 (y=70..170) — below hole bottom ✓
- QR-Backing V1 (y=208..238) — far below ✓

**No V1 polygon overlaps the loch.** ✓ Confidence: HIGH (math checked).

The Hellgrün-Akzent at y=14..18 directly under the Brand-Bar (which itself ends at y=14) means Brand-Bar.y_max == Hellgrün-Akzent.y_min — they touch perfectly (no gap). Both are full-width and same x-extent ⇒ `brand:cover_extent_match` PASSES.

The Hellgrün-Band y_min=63 vs hole y_max=60 → 3mm gap ✓ within typical safety margin.

---

## 16. `brand_overrides` cleanup checklist for V1

Current `meta.yml::brand_overrides` (lines 22-71): 8 overrides.

| Rule | Currently overridden? | Should V1 keep? | Reason |
|---|---|---|---|
| `brand:line_spacing_0.9` | ✓ | ✓ KEEP | 6 of 7 styles still violate after V1 (only headline fixed to 25.2) |
| `brand:hl_sl_distance_x2` | ✓ | ✓ KEEP | V1 explicitly chose 50%-formula gap; reason text should reference #18 |
| `brand:logo_size_3M` | ✓ | ✗ REMOVE | V1 brings both logos to 18.9mm; Bund-Dunkel back logo deleted |
| `brand:bleed_3mm` | ✓ | ✓ KEEP | Permanent format constraint (die-cut) |
| `brand:wahlkreuz_colored_bg` | ✓ | ⚠ TEST + REMOVE if passes | V1 keeps Hellgrün-Band overlapping Wahlkreuz; rule should now find the overlap (band ≠ wahlkreuz frame). Run structural_check with override removed to confirm. |
| `brand:font_family` | ✓ | ✓ KEEP | Kandidat-Position keeps Italic font (V1 doesn't change font, just fcolor) |
| `brand:visual_adjacency_drift` | ✓ | ✗ REMOVE | V1 introduces a CONSTRAINTS list capturing declared adjacencies — that's the locked-decision-#9 contract from #22 |
| `brand:image_text_overlap` | ✓ | ✗ REMOVE | V1 has zero partial overlaps (verified §4) |

**Net post-V1: 5 overrides retained, 3 removed.** `brand:wahlkreuz_colored_bg` is the conditional-removal.

---

## 17. Constraint factory interfaces (for the planner)

`tools/sla_lib/builder/constraints.py` exports these factories (all importable from `sla_lib.builder`):

<interfaces>
# From tools/sla_lib/builder/constraints.py

# Result type
@dataclass(frozen=True)
class Violation:
    severity: str             # "error" | "warning" | "info"
    message: str
    rule_id: str = ""
    targets: tuple = ()

# Factory signatures (default tolerance_mm=0.5 unless noted)
def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5,
              name: str = "") -> Constraint  # axis ∈ {"both", "w", "h"}
def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5,
               name: str = "") -> Constraint  # axis_mm = mirror line x_mm
def mirrored_y(top, bottom, axis_mm: float, tolerance_mm: float = 0.5,
               name: str = "") -> Constraint
def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def equal_gap(*targets, axis: str = "y", gap_mm: float, tolerance_mm: float = 0.5,
              name: str = "") -> Constraint
def hierarchy(*targets, by: str = "fontsize", name: str = "") -> Constraint
def same_style(*targets, name: str = "") -> Constraint
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5,
                  name: str = "") -> Constraint
# ↑ ARG ORDER: below first (the frame hanging beneath), above second (the anchor)
# Each factory accepts targets either as primitive instances (with .anname set)
# or as anname strings.
# Issue #14, see constraints.py:507-519.

# From tools/sla_lib/builder/__init__.py — exported names
__all__ contains: same_x, same_y, same_size, mirrored_x, mirrored_y, inside,
                  equal_gap, hierarchy, same_style, distance_x, distance_y,
                  aligned_below, BRAND_CONSTRAINTS, BrandRule, ...
</interfaces>

<interfaces>
# From tools/sla_lib/builder/blocks.py

# DoorHangerCutout (currently in use by wahltag-tueranhaenger)
@dataclass
class DoorHangerCutout:
    page_size_mm: tuple[float, float] = (105, 250)
    hole_diameter_mm: float = 35
    hole_top_offset_mm: float = 25
    layer_idx: int = 3
    def emit(self, page=None) -> Iterable: ...   # yields 2 DieCut polys

# WahlkreuzSymbol — NOT used by tueranhaenger (uses raw ImageFrame +
# Hellgrün-Band Polygon). V1 does not need to migrate.
@dataclass
class WahlkreuzSymbol:
    pos: Anchor
    size: tuple[float, float] = (55, 55)
    background_color: str = "Dunkelgrün"   # D12: never White, never Gelb
    background_padding_mm: float = 4.0
    anname: str = "Wahlkreuz"
</interfaces>

<interfaces>
# From tools/sla_lib/builder/primitives.py

# TextFrame — relevant kwargs for V1
@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""              # ParaStyle name
    fcolor: str = ""             # OVERRIDE color (e.g. White)
    runs: Optional[list] = None  # list of Run dataclass instances
    columns: int = 1
    col_gap_mm: float = 4
    fill: Optional[str] = None        # PCOLOR (frame background)
    line_color: Optional[str] = None  # PCOLOR2 (border)
    line_width_pt: float = 0
    layer: int = 0
    anname: str = ""
    rotation_deg: float = 0
    # ... + many xml-emit knobs

# Run — fcolor override at run level (used in V1 for per-frame fcolor changes
# without making new ParaStyles; option B in §2)
@dataclass
class Run:
    text: str = ""
    fcolor: Optional[str] = None    # overrides paragraph_style.fcolor
    paragraph_style: Optional[str] = None
    separator: Optional[str] = None  # "para" | None
    font: Optional[str] = None
    fshade: Optional[int] = None
    features: Optional[str] = None
    var: Optional[str] = None        # e.g. "pgno" for page-number variable
    var_attrs: Optional[Mapping[str, str]] = None
    has_itext: bool = True

# ImageFrame — V1 uses for Logo + Wahlkreuz + Portrait + QR
@dataclass
class ImageFrame(_Frame):
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None
    image: str = ""        # alternative: external src path
    scale_type: int = 0    # 0=free/aspect-locked, 1=auto-fit
    ratio: int = 1
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    layer: int = 0
    anname: str = ""

# Polygon — V1 uses for new background cards
@dataclass
class Polygon(_Frame):
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    custom_path: Optional[str] = None
    shape: str = "rect"          # "rect" | "ellipse" (used by WahlkreuzSymbol)
    dash_pattern: Optional[tuple[float, float]] = None
    layer: int = 0
    anname: str = ""
</interfaces>

<interfaces>
# From tools/sla_lib/builder/styles.py — ParaStyle for new on-green styles
@dataclass
class ParaStyle:
    name: str
    font: Optional[str] = None
    fontsize: Optional[float] = None
    linesp: Optional[float] = None       # leading in pt
    linesp_mode: int = 0                 # 0 = fixed leading
    align: Optional[int] = None          # 0=left, 1=center, 2=right, 3=block
    fcolor: Optional[str] = None
    language: str = "de"
    # ... plus other inheritance/parent kwargs

# Pattern (from #17 wahlaufruf-postkarte build.py:140-148):
ParaStyle(
    name="wahlaufruf/cell-body-on-green",
    font="Gotham Narrow Book",
    fontsize=9,
    linesp=11,
    linesp_mode=0,
    align=0,
    fcolor="White",
    language="de",
)
</interfaces>

<interfaces>
# From tools/sla_lib/builder/brand_constraints.py
# All 14 registered rule IDs (post-#23):
BRAND_CONSTRAINTS = [
    "brand:color_palette",
    "brand:font_family",
    "brand:line_spacing_0.9",
    "brand:hl_sl_distance_x2",          # NOT brand:hl_sub_gap_2x (ISSUE.md typo)
    "brand:logo_size_3M",
    "brand:text_on_green",
    "brand:bleed_3mm",
    "brand:wahlkreuz_colored_bg",
    "brand:inside_page",                 # Issue #14
    "brand:spine_safety",                # Issue #22 (no-op for facing_pages=False)
    "brand:bleed_coverage",              # Issue #23 (no-op for facing_pages=False)
    "brand:image_text_overlap",          # Issue #23
    "brand:cover_extent_match",          # Issue #23
    "brand:visual_adjacency_drift",      # Issue #23 (replaces #22's brand:undeclared_alignment_drift)
]

# brand:image_text_overlap — IN-SCOPE filled-polygon fills
FILLED_POLYGON_FILLS = ("Dunkelgrün", "Hellgrün", "Magenta", "Gelb")
# White polygons (e.g. V1's QR-Backing) are NOT in scope.

# brand:visual_adjacency_drift defaults
axis_drift_min_mm   = 0.5
axis_drift_max_mm   = 25.0
adjacency_gap_min_mm = 0.5
adjacency_gap_max_mm = 30.0
</interfaces>

---

## 18. Summary of "things the planner must NOT miss"

1. **Reject ISSUE.md's CONSTRAINTS list verbatim.** It references nonexistent stat-card frames AND uses snake-case stub annames. Use §3 recommended list as starting point; refine after running `bin/audit-alignment` post-V1.

2. **Use `brand:hl_sl_distance_x2` (NOT `brand:hl_sub_gap_2x`)** in the brand_overrides entry per ISSUE.md acceptance #6.

3. **Remove three brand_overrides** post-V1: `brand:image_text_overlap`, `brand:visual_adjacency_drift`, `brand:logo_size_3M`. **Test removal of `brand:wahlkreuz_colored_bg`** — likely removable too.

4. **The brand:image_in_container_flush and brand:portrait_column_alignment rules from the task description DON'T EXIST.** No need to plan around them.

5. **Add new ParaStyles `*-on-green` for every text frame whose fcolor changes** (parallels #17 pattern; see §2 option A). At minimum: `tueranhaenger/body-on-green` and `tueranhaenger/url-on-green`. Recommended additionally: `tueranhaenger/cand-name-on-green` (also bumps fontsize 14→18), `tueranhaenger/cand-pos-on-green`, `tueranhaenger/impressum-on-green`.

6. **Update the Headline ParaStyle in-place** (linesp 30→25.2) — this is what ISSUE.md prescribes. The other 6 styles' linesp violations remain; keep the `brand:line_spacing_0.9` override.

7. **Spec rewrite is recommended (per #17)** — the existing spec is fully stale post-V1.

8. **Mandatory post-V1 build steps:**
   - `python3 templates/wahltag-tueranhaenger/build.py` (regen `template.sla`)
   - `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger` (verify zero errors)
   - `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all` (verify --all stays green)
   - `tools/check_ci.py templates/wahltag-tueranhaenger/template.sla` (verify CI drift OK)
   - `bin/render-gallery wahltag-tueranhaenger --skip-visual-diff` (regen previews + bump SHA)
   - `tools/check_ci.py` aggregate (per acceptance #5)
   - Update `improvements/02-wahltag-tueranhaenger.md` Session-History `Resulting issue`
   - Update `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 Session-History row

9. **Layer discipline:** All new V1 polygons go on `LAYER_HINTERGRUND` (index 0), not Stanzkontur (index 3). Verified safe (§14).

10. **Keep the `same_style(Impressum, Impressum (back))` constraint** — both must point to the same style after V1 (e.g. both `tueranhaenger/impressum-on-green`).

---

## 19. Confidence assessment

| Section | Confidence | Reason |
|---|---|---|
| Frame inventory | HIGH | line-by-line read of build.py |
| ParaStyle inventory | HIGH | line-by-line read; cross-template grep confirms isolation |
| CONSTRAINTS state | HIGH | direct read of build.py:431-454 |
| Rule-id correctness | HIGH | grep of registry confirms `brand:hl_sl_distance_x2` |
| Post-#23 rule applicability | HIGH | read all 14 rule classes; manual geometric verification |
| INJECT_MAP | HIGH | template uses no inject system |
| Asset availability | HIGH | `ls -l` + `library.load(...)` smoke test |
| Reference SLA / SHA flow | HIGH | read `tools/check_stale_previews.py`, `tools/render_pipeline.py` |
| Spec staleness | HIGH | direct read of all 420 lines |
| Smoke test impact | HIGH | walked every assertion |
| Audit output | HIGH | live capture |
| Open-question Q1 (Doppel-Logo) | MEDIUM | iter-3 comment + audit confirms artifact-likely; final call belongs to brand stewardship |
| Open-question Q3 (Bullets-Card 58mm) | LOW | Druck-Kosten is a business decision, not technical |
| Stanzkontur layer integrity | HIGH | layer constants + planned polygon emit pattern |
| Hole-zone overlap | HIGH | math verified |
| brand_overrides cleanup | HIGH | per-rule walk |
| Constraint factory interfaces | HIGH | direct read of constraints.py |

**Overall confidence: HIGH** for technical correctness; MEDIUM-LOW only on the design-judgment open questions (Q1 deletion approval, Q3 ink-cost cap), which are user/brand decisions not codebase facts.
