# Spec: Kandidat-Falzflyer DIN-lang (V1 "Falz-Rhythm")

```yaml
id: kandidat-falzflyer-din-lang
title: Kandidat-Falzflyer DIN-lang
format: A4 quer (297×210 mm), 3-fach Zickzackfalz
trim_mm: [297, 210]
bleed_mm: 3
pages: 2
fold_type: zickzack
fold_positions_mm: [99, 198]   # vertikal, beide Seiten
panels: 6                       # 3 vorne (P1/P2/P3), 3 hinten (P4/P5/P6)
panel_w_mm: 99                  # 297 / 3
panel_h_mm: 210                 # full trim height
audience: [kandidat, bezirksgruppe, ortsgruppe]
```

## Audience und Layout-Philosophie

**Kandidaten-Visitenkarte für Bezirks- und Ortsgruppen-Wahlkampf.** 6 Panele auf
DIN-A4-quer mit Zickzackfalz (Z-Falz, alternierende Faltrichtung an x=99 und x=198):
P1/P2/P3 vorne, P4/P5/P6 hinten. Lese-Distanz im Stand bzw. von Hand zu Hand
~30–60 cm; Inhalte müssen sich panelweise unabhängig lesen lassen, ohne dass die
Falz-Sequenz ihre Reihenfolge fixiert.

**Layout-Philosophie (V1 — "Falz-Rhythm"):** Universal-Top-Band über alle 6 Panele
plus markenfarbige "grüne Klammer" P1↔P6 für die äußeren Hüllen. Inneres
Themen-Raster auf P4/P5 mit halbierender Trenner-Polygone und Photo-zentrischer
Erzählung.

- **Front (P1 Cover · P2 Mein Plan · P3 Wahltag):** Cover trägt Top-Band +
  Logo + Portrait + voll-bleed Name-Card mit Slogan; P2 trägt Top-Band +
  Top-Title "Mein Plan" + Headline + Hellgrün-Body-Backing-Card; P3 ist
  vollflächig Dunkelgrün mit Wahlkreuz-Hero und Top-Title "Wahltag" (Gelb).
- **Back (P4 Themen 1·2 · P5 Themen 3·4 · P6 Kontakt):** P4/P5 spiegeln sich
  intra-panel: Eyebrow (Caps) → Headline → Photo (87×44 native 1.5:1) →
  Trenner (3 mm Hellgrün) → zweites Thema desselben Musters; P6 ist
  vollflächig Dunkelgrün mit Top-Title "Kontakt", 2-Spalten-Kontakt-Layout
  symmetrisch um AXIS_P6_CENTER_X=247.5, zwei QR-Codes mit Caps-Captions
  und Footer-Logo (38×34 white wordmark).

V1 schließt die V1-Rollout-Sequenz aus #15: implementiert das volle
ParaStyle-Migrationsmuster (`*-on-green` Variants), die Universal-Top-Band-
Konvention aus #20, das INJECT_MAP-Idiom (post-#24) und die 22-CONSTRAINT-
Liste (parallel zu #20). Schließt den **M-Basis-Konflikt**: die `brand:logo_size_3M`-
Regel war bereits Trim-konsistent (`M = 0.06 * min(trim_w, trim_h)`); auf
DIN-lang heißt das `min(297, 210) = 210 → 3M = 37.8 mm`. Die V0-Logos (20mm /
16mm / 17mm) waren systematisch zu klein; V1 setzt P1+P6 auf 38mm Print-Soll
und löscht das überflüssige P2-Klein-Logo, da das Top-Band das visuelle
Branding übernimmt.

## Brand Compliance — M-Basis Resolution (Issue #21)

**Konflikt (vor #21):** Build-Code-Comment in `templates/kandidat-falzflyer-
din-lang/build.py:195-199` referenzierte "kurze Kante=105 → 18.9 mm Logo-Soll"
(panel-basiert), während die Quickguide-Konvention "Trim-kurze-Kante=210 →
37.8 mm Soll" verlangt (trim-basiert). Die Brand-Regel
`brand:logo_size_3M` (`tools/sla_lib/builder/brand_constraints.py:262`) war
**bereits** trim-konsistent — der Konflikt lag nur im Build-Code-Kommentar +
3 untermaßigen Logos.

**Resolution (#21):**
1. Build-Code-Header-Kommentar berichtigt (T01) — verweist jetzt auf
   `M = 0.06 * min(trim_w, trim_h)` mit konkretem Beispiel
   `min(297, 210)=210 → M=12.6 → 3M=37.8mm` und Cross-Reference zur
   `brand_constraints.py` + `shared/brand/DESIGN-SYSTEM-BRIEF.md`.
2. 3 Logo-Frames auf Soll resized (T02): P1 Logo 20×18 → 38×22, P6 Logo
   17×15 → 38×34, P2 Logo (klein) gelöscht (Top-Band übernimmt).
3. `meta.yml.brand_overrides`-Eintrag `brand:logo_size_3M` entfernt
   (T01) — die Regel blockiert jetzt korrekt zu kleine Logos.
4. Geometry-Test `test_m_basis_rule_all_v1_templates` validiert
   parametrisch alle 5 V1-Templates gegen die Regel.

**Keine Änderung an `tools/check_ci.py` oder `tools/sla_lib/builder/
brand_constraints.py`** — die Regel war bereits korrekt. Issue-Beschreibung
erwähnte fälschlich `check_ci.py`; RESEARCH locked decision #1 korrigiert
dies (`check_ci.py` enthält keine Logo-/Alignment-Logik).

## ParaStyle-Tabelle (V1 — 16 Styles)

| Name | Font | Size | Linesp | Align | fcolor | Usage |
|---|---|---|---|---|---|---|
| `falzflyer/cand-name` | Vollkorn Black Italic | 24 | 27 | 1 | White | P1 Kandidat-Name auf Name-Card |
| `falzflyer/slogan` | Gotham Narrow Bold | 14 | 17 | 1 | Black | (Reserved; align flipped) |
| `falzflyer/slogan-on-green` *NEW* | Gotham Narrow Bold | 14 | 17 | 1 | Gelb | P1 Slogan auf Name-Card (Dunkelgrün) |
| `falzflyer/teaser-headline` | Gotham Narrow Bold | 18 | 22 | 0 | Dunkelgrün | P2 Teaser-Headline (UNCHANGED) |
| `falzflyer/teaser-body` | Gotham Narrow Book | 11 | 14 | 0 | White | P2 Teaser-Body auf Hellgrün-Backing |
| `falzflyer/thema-headline` | Gotham Narrow Bold | 16 | 20 | 0 | Dunkelgrün | P4/P5 Thema-Headlines (UNCHANGED) |
| `falzflyer/thema-body` | Gotham Narrow Book | 10 | 13 | 1 | Black | P4/P5 Thema-Bodies (V1: 9→10pt, 11→13 linesp) |
| `falzflyer/themen-eyebrow` *NEW* | Gotham Narrow Bold | 9 | 12 | 0 | Dunkelgrün | "THEMA 0X" Caps + P6 QR-Captions (fcolor=White override) |
| `falzflyer/top-title` *NEW* | Gotham Narrow Bold | 11 | 14 | 0 | White | P2/P4/P5/P6 Top-Title (P3 trägt fcolor=Gelb override) |
| `falzflyer/quote-on-green` *NEW* | Vollkorn Black Italic | 18 | 20 | 1 | White | Pull-Quote (registriert; kein Frame in V1, deferred) |
| `falzflyer/closer-headline` | Gotham Narrow Bold | 22 | 26 | 1 | White | P3 Closer-Headline auf Dunkelgrün |
| `falzflyer/closer-datum` | Vollkorn Black Italic | 14 | 18 | 1 | Gelb | P3 Datum-Akzent |
| `falzflyer/closer-url` | Gotham Narrow Bold | 11 | 14 | 1 | White | P3 URL |
| `falzflyer/contact-headline` | Gotham Narrow Bold | 16 | 20 | 1 | White | P6 Kontakt-Headline auf Dunkelgrün |
| `falzflyer/contact-body` | Gotham Narrow Book | 10 | 12 | 1 | White | P6 4 Kontakt-Cells (2-Spalten) |
| `falzflyer/impressum` | Gotham Narrow Book | 6 | 8 | 1 | White | P6 Impressum auf Dunkelgrün |

**V1 Migration summary:** 10 in-place mutations (9 align flips + 1 fcolor-only
auf teaser-body), 4 NEW parallel styles (slogan-on-green, quote-on-green,
top-title, themen-eyebrow), 2 KEPT unchanged (teaser-headline, thema-headline —
beide bleiben align=0 für redaktionellen Charakter).

## V1 Frame-Inventar (TARGET state)

### Page 0 (Front) — P1 / P2 / P3

| Anname | Type | x | y | w | h | Layer | Notes |
|---|---|---|---|---|---|---|---|
| `P1 Top-Band` | Polygon | -3 | -3 | 105 | 31 | 0 | Dunkelgrün, +3mm bleed left + +3mm overshoot right (outer) |
| `P1 Logo Grüne (weiss)` | Image | 6 | 4 | 38 | 22 | 1 | gruene-weiss.png — 3M Trim-konform |
| `P1 Kandidat-Portrait` | Image | 6 | 34 | 87 | 100 | 1 | INJECT_MAP → portrait_maria |
| `P1 Name-Card` | Polygon | -3 | 134 | 105 | 79 | 0 | Dunkelgrün vollbleed bottom (134+79=213=210+3) |
| `P1 Kandidat-Name` | Text | 6 | 142 | 87 | 18 | 2 | falzflyer/cand-name |
| `P1 Slogan` | Text | 6 | 164 | 87 | 20 | 2 | falzflyer/slogan-on-green (Gelb on Dunkelgrün) |
| `P3 Hintergrund` | Polygon | 198 | -3 | 102 | 216 | 0 | Dunkelgrün vollflächig (gruene-Klammer pair) |
| `P2 Top-Band` | Polygon | 99 | -3 | 99 | 31 | 0 | Inner panel flush both folds |
| `P2 Top-Title` | Text | 105 | 8 | 87 | 14 | 2 | "Mein Plan" — top-title style |
| `P2 Teaser-Headline` | Text | 105 | 38 | 87 | 22 | 2 | falzflyer/teaser-headline (UNCHANGED) |
| `P2 Body-Backing` | Polygon | 99 | 66 | 99 | 144 | 0 | Hellgrün card backing |
| `P2 Teaser-Body` | Text | 113 | 72 | 73 | 130 | 2 | inset +8mm; teaser-body fcolor=White |
| `P3 Top-Title` | Text | 204 | 8 | 87 | 14 | 2 | "Wahltag" + frame fcolor='Gelb' override |
| `P3 Wahlkreuz` | Image | 222 | 44 | 50 | 50 | 1 | shared/assets/wahlkreuz.png |
| `P3 Closer-Headline` | Text | 204 | 100 | 87 | 32 | 2 | falzflyer/closer-headline |
| `P3 Datum-Akzent` | Text | 204 | 145 | 87 | 22 | 2 | falzflyer/closer-datum |
| `P3 URL` | Text | 204 | 185 | 87 | 12 | 2 | falzflyer/closer-url |
| `Falz x=99 (Front)` | FoldLine | 99 | 0..210 | — | — | 3 | Z-Falz vorne |
| `Falz x=198 (Front)` | FoldLine | 198 | 0..210 | — | — | 3 | Z-Falz vorne |

### Page 1 (Back) — P4 / P5 / P6

| Anname | Type | x | y | w | h | Layer | Notes |
|---|---|---|---|---|---|---|---|
| `P4 Top-Band` | Polygon | -3 | -3 | 105 | 31 | 0 | Dunkelgrün outer |
| `P4 Top-Title` | Text | 6 | 8 | 87 | 14 | 2 | "Themen 1·2" (middle-dot literal) |
| `P4 Thema 1 — Eyebrow` | Text | 6 | 38 | 87 | 6 | 2 | "THEMA 01" themen-eyebrow |
| `P4 Thema 1 — Headline` | Text | 6 | 46 | 87 | 14 | 2 | thema-headline (UNCHANGED) |
| `P4 Thema 1 — Photo` | Image | 6 | 62 | 87 | 44 | 1 | INJECT_MAP → themen_klimaschutz_solar |
| `P4 Thema 1·2 Trenner` | Polygon | -3 | 108 | 105 | 3 | 0 | Hellgrün strip (V1) |
| `P4 Thema 1 — Body` | Text | 6 | 114 | 87 | 26 | 2 | thema-body (V1: align=1, 10pt) |
| `P4 Thema 2 — Eyebrow` | Text | 6 | 144 | 87 | 6 | 2 | "THEMA 02" |
| `P4 Thema 2 — Headline` | Text | 6 | 152 | 87 | 14 | 2 | thema-headline |
| `P4 Thema 2 — Photo` | Image | 6 | 168 | 87 | 44 | 1 | INJECT_MAP → themen_soziales_kaffeehaus |
| `P5 Top-Band` | Polygon | 99 | -3 | 99 | 31 | 0 | Dunkelgrün inner |
| `P5 Top-Title` | Text | 105 | 8 | 87 | 14 | 2 | "Themen 3·4" |
| `P5 Thema 3 — Eyebrow` | Text | 105 | 38 | 87 | 6 | 2 | "THEMA 03" |
| `P5 Thema 3 — Headline` | Text | 105 | 46 | 87 | 14 | 2 | thema-headline |
| `P5 Thema 3 — Photo` | Image | 105 | 62 | 87 | 44 | 1 | INJECT_MAP → themen_bildung_volksschule |
| `P5 Thema 3·4 Trenner` | Polygon | 99 | 108 | 99 | 3 | 0 | Hellgrün strip |
| `P5 Thema 3 — Body` | Text | 105 | 114 | 87 | 26 | 2 | thema-body |
| `P5 Thema 4 — Eyebrow` | Text | 105 | 144 | 87 | 6 | 2 | "THEMA 04" |
| `P5 Thema 4 — Headline` | Text | 105 | 152 | 87 | 14 | 2 | thema-headline |
| `P5 Thema 4 — Photo` | Image | 105 | 168 | 87 | 44 | 1 | NEW V1 — INJECT_MAP → themen_wirtschaft_handwerk |
| `P6 Hintergrund` | Polygon | 198 | -3 | 102 | 216 | 0 | Dunkelgrün vollflächig (grüne-Klammer pair) |
| `P6 Top-Title` | Text | 204 | 8 | 87 | 14 | 2 | "Kontakt" top-title |
| `P6 Kontakt-Headline` | Text | 204 | 38 | 87 | 14 | 2 | contact-headline |
| `P6 Adresse` | Text | 204 | 62 | 41 | 20 | 2 | 2-col cell row 1 left |
| `P6 Telefon` | Text | 250 | 62 | 41 | 20 | 2 | 2-col cell row 1 right |
| `P6 Email` | Text | 204 | 90 | 41 | 20 | 2 | 2-col cell row 2 left |
| `P6 Sprechtag` | Text | 250 | 90 | 41 | 20 | 2 | 2-col cell row 2 right |
| `P6 QR-Code (mitmachen)` | Image | 218 | 128 | 24 | 24 | 1 | mirror around 247.5 |
| `P6 QR-Caption (mitmachen)` | Text | 218 | 154 | 24 | 6 | 2 | "MITMACHEN" themen-eyebrow + fcolor=White override |
| `P6 QR-Code (termine)` | Image | 254 | 128 | 24 | 24 | 1 | mirror partner |
| `P6 QR-Caption (termine)` | Text | 254 | 154 | 24 | 6 | 2 | "TERMINE" |
| `P6 Logo Grüne (weiss)` | Image | 228 | 168 | 38 | 34 | 1 | 3M Trim-konform |
| `P6 Impressum` | Text | 204 | 200 | 87 | 8 | 2 | impressum (V1: h 60→8, fcolor=White) |
| `Falz x=99 (Back)` | FoldLine | 99 | 0..210 | — | — | 3 | Z-Falz hinten |
| `Falz x=198 (Back)` | FoldLine | 198 | 0..210 | — | — | 3 | Z-Falz hinten |

## CONSTRAINTS (22 entries)

Read by `structural_check`. All anname strings use REAL names (em-dash U+2014
literal, case-sensitive). `AXIS_P6_CENTER_X = 247.5 mm`.

- **Top-Band uniformity (3):** `top_bands_uniform_h` (4 polygons same h),
  `p3_top_title_anchored` (inside P3 Hintergrund), `p6_top_title_anchored`.
- **P3↔P6 grüne-Klammer (1):** `gruene_klammer_p3_p6` (same_size).
- **P4 themen mirror (5):** `p4_eyebrow_x`, `p4_headline_x`, `p4_photo_x`,
  `p4_photos_size`, `p4_t1_photo_anchored` (aligned_below gap=2.0).
- **P5 themen mirror (5):** `p5_eyebrow_x`, `p5_headline_x`, `p5_photo_x`,
  `p5_photos_size`, `p5_t3_photo_anchored`.
- **Cross-panel (1):** `cross_panel_themen_photos_size`.
- **P6 Kontakt 2-Spalten (4):** `p6_col_mirror_row1`, `p6_col_mirror_row2`,
  `p6_qr_mirror`, `p6_qrs_size`.
- **Logo Print-Soll (1):** `logos_print_soll_w_uniform`.
- **Style consistency (2):** `thema_headline_style_consistent`,
  `thema_body_style_consistent`.

Total = 22. P6 baseline same_y + cells_uniform deferred to geometry test
(`tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py`) to maintain
the 22-count constraint.

## INJECT_MAP (5 photo bindings)

```python
INJECT_MAP: dict[str, str] = {
    "P1 Kandidat-Portrait":  "portrait_maria",
    "P4 Thema 1 — Photo":    "themen_klimaschutz_solar",
    "P4 Thema 2 — Photo":    "themen_soziales_kaffeehaus",
    "P5 Thema 3 — Photo":    "themen_bildung_volksschule",
    "P5 Thema 4 — Photo":    "themen_wirtschaft_handwerk",
}
```

`build_template()` setzt die Frames ohne inline-image-data; `build_preview()`
liest die LIVE-Frame-Dimensionen (post-#24 idiom) und ruft
`library.inject_into_frame(frame, img, target_w_mm=frame.w_mm,
target_h_mm=frame.h_mm)` für jeden Match. `build_doc = build_template`
Alias dient `structural_check` / `spec_check` / Smoke-Test.

## Print Production

- **Trim:** 297×210 mm A4-quer
- **Bleed:** 3 mm umlaufend → SLA-Fläche 303×216
- **Falz:** Zickzackfalz (Z-Falz), 2 vertikale Falten an x=99 und x=198 mm,
  alternierende Faltrichtung. Falz-Layer "Falz" (`printable=False`)
  trägt nur die 4 Hilfslinien.
- **Safe-Area pro Panel:** x=6 .. 93 (innen 87 mm), y=6 .. 204 (innen 198 mm).
  Top-Band-Texte y=8..28 sind im inneren der 31-mm-Top-Band-Polygons.
- **Color profiles:** CMYK (cmyk_only=true). Spot-Color "Falz" nur auf
  Falz-Layer (visible=true, printable=false) für Pre-Press.
- **Min image DPI:** 300.

## Verification

```bash
# Build clean SLA
python3 templates/kandidat-falzflyer-din-lang/build.py

# Structural check (CONSTRAINTS + brand rules)
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang

# Smoke test (15 V1 assertions)
PYTHONPATH=tools python3 -m unittest templates._smoke.test_kandidat_falzflyer_din_lang

# Geometry invariants (21 V1 invariants)
PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_kandidat_falzflyer_geometry

# Re-render preview artifacts
bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff

# Verify SHA freshness
bin/check-stale-previews
```

All exits 0 in V1 final state.
