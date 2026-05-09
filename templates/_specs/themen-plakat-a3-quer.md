# Spec: Themen-Plakat A3 quer (V1 "Evidence Cards")

```yaml
id: themen-plakat-a3-quer
title: Themen-Plakat A3 quer
format: A3 quer 1-seitig
trim_mm: [420, 297]
bleed_mm: 3
pages: 1
fold_type: none
fold_positions_mm: []
cut_type: none
audience: [bezirksgruppe, landesgruppe, ortsgruppe]
```

## Audience und Layout-Philosophie

Bezirks- und Landesgruppen, die zu einem Sachthema **argumentieren** (statt einer
Veranstaltung einladen oder zum Wahltag aufrufen). Das Plakat hängt im Gemeindeamts-
Aushang, in Lokalen und auf Infotafeln. Lese-Distanz **50 cm – 1.5 m**.

**Layout-Philosophie (V1 — "Evidence Cards"):** 60/40-Split aus links-bleibender
Hero-Foto-Karte + rechts-bleibendem Headline-Stack, darunter drei Hellgrün-Cards
mit Stat-Hero-Zahlen + caps-Labels + weißem Body-Text auf Grün — die Belege bekommen
visuelle Eigenständigkeit, der Body löst sich vom Weißraum.

V1 ist die "Evidence Cards"-Variante aus `improvements/03-themen-plakat.md` §"Variante 1".
V2 ("Hero Photo Plakat", Vollbild-Foto-Hälfte) und V3 ("Argument Stack", foto-loses
Backup) sind Backlog (eigene Issues).

V1 nutzt das post-#24 INJECT_MAP-Idiom für `Themen-Hero` (`build_template` + `build_preview`-
Split, `library.inject_into_frame(target_w_mm=item.w_mm, target_h_mm=item.h_mm)` mit
LIVE Frame-Dimensionen) und korrigiert damit die "halb-leerer Frame"-Regression
aus iter-3 (`crop_for_frame(target_w_mm=180, target_h_mm=60)` vs Frame 194×114).

## Layout — Vorderseite (Page 1, einzige Seite)

```text
   <----------------------420mm---------------------->
  +---------------------------------------------------+   ↑
  | L                                  Q              |   |  L=Logo (15,10,53.46×48), Q=QR (370,8,35×35)
  |                                                   |   |
  | +-----------------------+   ╭─────────────────╮   |   |  Hero-Foto-Card (Hellgrün 15,70,200×120)
  | |                       |   │  Klimaschutz    │   |   |  Headline These (235,70,170×100)
  | |    Themen-Hero        |   │  ist Wirt-      │   |   |
  | |    18,73,194×114      |   │  schafts-       │   |   |
  | |    1.7:1 windrad      |   │  politik.       │   |   |
  | |    (INJECT_MAP)       |   ╰─────────────────╯   |   |
  | |                       |   Sub (235,172,170×14)  | 297
  | +-----------------------+                         | mm
  |                                                   |   |
  | +-----------+   +-----------+   +-----------+     |   |  3 Beleg-Cards (Hellgrün, layer=1)
  | | 12 700    |   | 1.2 Mrd.€ |   | 36 %      |     |   |  Stat (col_x+5, 215, 114×24, Gelb 56pt)
  | |           |   |           |   |           |     |   |
  | | GRÜNE…    |   | UMSATZ…   |   | WENIGER…  |     |   |  Label CAPS (col_x+5, 242, 114×8, Gelb 18pt)
  | |           |   |           |   |           |     |   |
  | | In NÖ…    |   | Die Solar |   | Seit 2010 |     |   |  Body (col_x+5, 252, 114×26, White 13pt)
  | +-----------+   +-----------+   +-----------+     |   |
  |                                                   |   |
  |  Quelle (15, 287, 200×8)              Impressum   |   |
  +---------------------------------------------------+   ↓

Legende:
  L  = Logo Grüne (top-left), 53.46×48 mm Print-Soll 3×M
  Q  = QR-Code (quelle), 35×35 mm
  Themen-Hero = ImageFrame, INJECT_MAP value "themen_klimaschutz_windrad"
  3 Cards = Polygon Hellgrün layer=1 (Beleg N — Card)
  Stat / Label / Body = TextFrames inset 5mm im Card

Hierarchie der Hintergrund-Polygons (layer=0/1):
  1. Seitenhintergrund   (White,    -3, -3, 426, 303)  layer=0
  2. Hero-Foto-Card      (Hellgrün, 15, 70, 200, 120)  layer=1
  3. Beleg N — Card      (Hellgrün, col_x, 210, 124.67, 72)  layer=1 (für N=1,2,3)
```

## Constraints — V1 strukturelle Invarianten (Prosa, SCHEMA.md §11-12)

Code lebt in `templates/themen-plakat-a3-quer/build.py::CONSTRAINTS` (19 Einträge).
Diese Spec beschreibt Intent — Code ist Vertrag.

### Headline-Stack (right-half column)

- **Headline These → Sub-Headline vertikaler Abstand 102 mm** (top-to-top distance
  per `distance_y` Semantik). Code: `CONSTRAINTS["hl_to_sub"]`
  (`distance_y(equals=102.0)`).

### Drei Evidence-Cards (lower band)

- **Cards teilen sich obere y-Kante** (alle bei y=210). Code:
  `CONSTRAINTS["cards_top_aligned"]` (`same_y` über die 3 Cards).
- **Cards teilen sich Größe** (alle 124.67 × 72 mm). Code:
  `CONSTRAINTS["cards_same_size"]` (`same_size`).
- **Cards 1 + 3 spiegeln sich um die horizontale Seitenmitte** (axis_mm=210).
  Code: `CONSTRAINTS["cards_mirror_around_page_center"]` (`mirrored_x`).
  Card 1 left=15 ↔ Card 3 right=405.67 → Achse 210.335 mm; Drift 0.335 mm < 0.5 mm
  Toleranz ✓.

### Per-Card innere Achse + Containment

- **Pro Card teilen sich Stat / Label / Body die innere x-Achse** (col_x + 5).
  Code: `CONSTRAINTS["card1_v_axis"]`, `card2_v_axis`, `card3_v_axis`
  (`same_x` mit jeweils Stat / Label / Body — **NICHT** mit Card; Card.x=col_x
  während Stat/Label/Body.x=col_x+5; 5 mm Drift > 0.5 mm Tol würde `same_x`
  rot machen.)
- **Pro Card sitzt jeder Inhalt INSIDE der Card-Polygon-Hülle.** Code:
  9 `CONSTRAINTS["bN_{stat,label,body}_in_card"]` (`inside`-Containment).
  Deklarativer Witness für "weißer Text auf grünem Polygon".

### Hero-Containment

- **Themen-Hero sitzt INSIDE Hero-Foto-Card** (3 mm Padding allseitig: Hero
  18,73,194×114; Card 15,70,200×120). Code: `CONSTRAINTS["hero_in_card"]`
  (`inside`).
  **Wichtig (locked decision #2 / pitfalls §4):** ISSUE.md schlägt
  `aligned_below(Themen-Hero, Sub-Headline, gap_mm=8.0)` vor — geometrisch
  ungültig, da Hero (x=18) und Sub (x=235) in unterschiedlichen Spalten sitzen
  und Hero (y=73) ABOVE Sub (y=172) ist. Der `inside`-Witness ersetzt diesen
  Versuch.

### Style-Konsistenz

- **Stat-Style ist konsistent** über die 3 Cards. Code:
  `CONSTRAINTS["stat_style_consistent"]` (`same_style`).
- **Body-Style ist konsistent** über die 3 Cards. Code:
  `CONSTRAINTS["body_style_consistent"]` (`same_style`).

### Brand-Constraints

Aktiv via `BRAND_CONSTRAINTS` aus `tools/sla_lib/builder/brand_constraints.py`:
Color-Palette, Font-Family, Logo-Größe (jetzt nativ grün, weil V1 `w=53.46` =
exakt 3×M), Text-auf-Grün, Bleed, `inside_page`, `spine_safety`,
`visual_adjacency_drift` (jetzt nativ — V1 deklariert die zentralen Adjacencies).

**Override aktiv (siehe `meta.yml::brand_overrides` — final 2 Einträge):**

- `brand:line_spacing_0.9` — V1's `themen-plakat/beleg-body-on-green` (13 pt body,
  16.9 pt linesp = 1.3) und 5 weitere Pre-V1-Styles driften vom 0.9-Faktor.
  Begründung: Lesbarkeit von 13 pt Weiß-auf-Hellgrün braucht eine luftigere
  Zeilenführung als der 0.9-Default. Template-weite Drift, separates Brand-
  Team-Review (out-of-scope #19).
- `brand:hl_sl_distance_x2` — V1 60/40-Split platziert Sub-Headline 2 mm unter der
  100 mm hohen Headline These in der gleichen rechten Spalte. Vertikaler Abstand
  ist absichtlich tight, weil der visuelle Rhythmus aus dem Spalten-Split kommt
  (links Hero+Hellgrün-Backing, rechts Headline-Stack), nicht aus der HL/SL-
  Distanz-Formel.

**Stale Overrides entfernt (V1):**

- `brand:visual_adjacency_drift` — V1 deklariert die zentralen Adjacencies via
  CONSTRAINTS-Liste (Cards-Row, mirror, per-card axis + containment).
- `brand:image_text_overlap` — V1-Text liegt vollständig INSIDE der Hellgrün-Cards
  (rule docstring carve: "text fully inside shape = allowed").
- `brand:image_fills_frame` — V1 INJECT_MAP-Pre-Crop füllt Hero-Frame exakt.
- `brand:logo_size_3M` — V1 setzt Logo auf exakt 3×M = 53.46 mm.

## Slot-Tabelle — Vorderseite (Page 1)

| anname                  | type      | x_mm | y_mm | w_mm   | h_mm | fcolor      | style_ref                              | example                                          |
|-------------------------|-----------|------|------|--------|------|-------------|----------------------------------------|--------------------------------------------------|
| Seitenhintergrund       | Polygon   | -3   | -3   | 426    | 303  | White       | —                                      | Vollbild-Hintergrund, layer=0                    |
| Logo Grüne (top-left)   | ImageFrame| 15   | 10   | 53.46  | 48   | —           | shared/logos/gruene-logo-bund-dunkel.png| Print-Soll 3×M (M=0.06×297=17.82, 3M=53.46)      |
| Headline These          | TextFrame | 235  | 70   | 170    | 100  | Dunkelgrün  | themen-plakat/headline                 | Klimaschutz ist Wirtschaftspolitik.              |
| Sub-Headline            | TextFrame | 235  | 172  | 170    | 14   | Dunkelgrün  | themen-plakat/sub                      | Drei Belege aus Niederösterreich, Mai 2026.      |
| Hero-Foto-Card          | Polygon   | 15   | 70   | 200    | 120  | Hellgrün    | —                                      | Hellgrün-Backing für Themen-Hero, layer=1        |
| Themen-Hero             | ImageFrame| 18   | 73   | 194    | 114  | —           | INJECT_MAP themen_klimaschutz_windrad  | 1.7:1 Hero, post-#24 inject_into_frame          |
| Beleg 1 — Card          | Polygon   | 15   | 210  | 124.67 | 72   | Hellgrün    | —                                      | Backing-Card, layer=1                            |
| Beleg 1 — Stat          | TextFrame | 20   | 215  | 114    | 24   | Gelb        | themen-plakat/stat-hero                | "12 700"                                         |
| Beleg 1 — Label         | TextFrame | 20   | 242  | 114    | 8    | Gelb        | themen-plakat/beleg-headline-yellow    | "GRÜNE JOBS IN NÖ" (CAPS via .upper())           |
| Beleg 1 — Body          | TextFrame | 20   | 252  | 114    | 26   | White       | themen-plakat/beleg-body-on-green      | In NÖ arbeiten 12 700 Menschen…                  |
| Beleg 2 — Card          | Polygon   | 147.67 | 210 | 124.67 | 72   | Hellgrün    | —                                      | Backing-Card, layer=1                            |
| Beleg 2 — Stat          | TextFrame | 152.67 | 215 | 114    | 24   | Gelb        | themen-plakat/stat-hero                | "1.2 Mrd. €"                                     |
| Beleg 2 — Label         | TextFrame | 152.67 | 242 | 114    | 8    | Gelb        | themen-plakat/beleg-headline-yellow    | "UMSATZ SOLAR + WIND"                            |
| Beleg 2 — Body          | TextFrame | 152.67 | 252 | 114    | 26   | White       | themen-plakat/beleg-body-on-green      | Die Solar- und Wind-Branche…                     |
| Beleg 3 — Card          | Polygon   | 280.33 | 210 | 124.67 | 72   | Hellgrün    | —                                      | Backing-Card, layer=1                            |
| Beleg 3 — Stat          | TextFrame | 285.33 | 215 | 114    | 24   | Gelb        | themen-plakat/stat-hero                | "36 %"                                           |
| Beleg 3 — Label         | TextFrame | 285.33 | 242 | 114    | 8    | Gelb        | themen-plakat/beleg-headline-yellow    | "WENIGER CO₂ SEIT 2010"                          |
| Beleg 3 — Body          | TextFrame | 285.33 | 252 | 114    | 26   | White       | themen-plakat/beleg-body-on-green      | Seit 2010 hat NÖ den industriellen CO₂…          |
| QR-Code (quelle)        | ImageFrame| 370  | 8    | 35     | 35   | —           | samples/qr-quelle.png                  | Top-right balance to larger Logo                 |
| Quelle                  | TextFrame | 15   | 287  | 200    | 8    | Dunkelgrün  | themen-plakat/source                   | Quelle: Statistik Austria, AEA-Energiebilanz NÖ. |
| Impressum               | TextFrame | 305  | 287  | 100    | 8    | Black       | themen-plakat/impressum                | Medieninhaber: Die Grünen NÖ, …                  |

```yaml
slots:
  - anname: "Seitenhintergrund"
    type: Polygon
    x_mm: -3
    y_mm: -3
    w_mm: 426
    h_mm: 303
    fcolor: "White"
    style_ref: ""
    example: "Vollbild-Hintergrund, layer=0"
  - anname: "Logo Grüne (top-left)"
    type: ImageFrame
    x_mm: 15
    y_mm: 10
    w_mm: 53.46
    h_mm: 48
    fcolor: ""
    style_ref: "shared/logos/gruene-logo-bund-dunkel.png"
    example: "Print-Soll 3*M (M=0.06*297=17.82, 3M=53.46)"
  - anname: "Headline These"
    type: TextFrame
    x_mm: 235
    y_mm: 70
    w_mm: 170
    h_mm: 100
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/headline"
    example: "Klimaschutz ist Wirtschaftspolitik."
  - anname: "Sub-Headline"
    type: TextFrame
    x_mm: 235
    y_mm: 172
    w_mm: 170
    h_mm: 14
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/sub"
    example: "Drei Belege aus Niederösterreich, Mai 2026."
  - anname: "Hero-Foto-Card"
    type: Polygon
    x_mm: 15
    y_mm: 70
    w_mm: 200
    h_mm: 120
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Hellgrün-Backing für Themen-Hero, layer=1"
  - anname: "Themen-Hero"
    type: ImageFrame
    x_mm: 18
    y_mm: 73
    w_mm: 194
    h_mm: 114
    fcolor: ""
    style_ref: "INJECT_MAP:themen_klimaschutz_windrad"
    example: "1.7:1 Hero, post-#24 inject_into_frame fills exactly"
  - anname: "Beleg 1 — Card"
    type: Polygon
    x_mm: 15
    y_mm: 210
    w_mm: 124.67
    h_mm: 72
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Backing-Card, layer=1"
  - anname: "Beleg 1 — Stat"
    type: TextFrame
    x_mm: 20
    y_mm: 215
    w_mm: 114
    h_mm: 24
    fcolor: "Gelb"
    style_ref: "themen-plakat/stat-hero"
    example: "12 700"
  - anname: "Beleg 1 — Label"
    type: TextFrame
    x_mm: 20
    y_mm: 242
    w_mm: 114
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "themen-plakat/beleg-headline-yellow"
    example: "GRÜNE JOBS IN NÖ"
  - anname: "Beleg 1 — Body"
    type: TextFrame
    x_mm: 20
    y_mm: 252
    w_mm: 114
    h_mm: 26
    fcolor: "White"
    style_ref: "themen-plakat/beleg-body-on-green"
    example: "In Niederösterreich arbeiten 12 700 Menschen direkt in der Erneuerbaren-Energie-Branche."
  - anname: "Beleg 2 — Card"
    type: Polygon
    x_mm: 147.67
    y_mm: 210
    w_mm: 124.67
    h_mm: 72
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Backing-Card, layer=1"
  - anname: "Beleg 2 — Stat"
    type: TextFrame
    x_mm: 152.67
    y_mm: 215
    w_mm: 114
    h_mm: 24
    fcolor: "Gelb"
    style_ref: "themen-plakat/stat-hero"
    example: "1.2 Mrd. €"
  - anname: "Beleg 2 — Label"
    type: TextFrame
    x_mm: 152.67
    y_mm: 242
    w_mm: 114
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "themen-plakat/beleg-headline-yellow"
    example: "UMSATZ SOLAR + WIND"
  - anname: "Beleg 2 — Body"
    type: TextFrame
    x_mm: 152.67
    y_mm: 252
    w_mm: 114
    h_mm: 26
    fcolor: "White"
    style_ref: "themen-plakat/beleg-body-on-green"
    example: "Die Solar- und Wind-Branche macht in NÖ 1.2 Mrd. € Jahresumsatz aus."
  - anname: "Beleg 3 — Card"
    type: Polygon
    x_mm: 280.33
    y_mm: 210
    w_mm: 124.67
    h_mm: 72
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Backing-Card, layer=1"
  - anname: "Beleg 3 — Stat"
    type: TextFrame
    x_mm: 285.33
    y_mm: 215
    w_mm: 114
    h_mm: 24
    fcolor: "Gelb"
    style_ref: "themen-plakat/stat-hero"
    example: "36 %"
  - anname: "Beleg 3 — Label"
    type: TextFrame
    x_mm: 285.33
    y_mm: 242
    w_mm: 114
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "themen-plakat/beleg-headline-yellow"
    example: "WENIGER CO₂ SEIT 2010"
  - anname: "Beleg 3 — Body"
    type: TextFrame
    x_mm: 285.33
    y_mm: 252
    w_mm: 114
    h_mm: 26
    fcolor: "White"
    style_ref: "themen-plakat/beleg-body-on-green"
    example: "Seit 2010 hat NÖ den industriellen CO₂-Ausstoß um 36 % reduziert."
  - anname: "QR-Code (quelle)"
    type: ImageFrame
    x_mm: 370
    y_mm: 8
    w_mm: 35
    h_mm: 35
    fcolor: ""
    style_ref: "samples/qr-quelle.png"
    example: "Top-right balance to larger Logo"
  - anname: "Quelle"
    type: TextFrame
    x_mm: 15
    y_mm: 287
    w_mm: 200
    h_mm: 8
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/source"
    example: "Quelle: Statistik Austria, AEA-Energiebilanz NÖ 2024."
  - anname: "Impressum"
    type: TextFrame
    x_mm: 305
    y_mm: 287
    w_mm: 100
    h_mm: 8
    fcolor: "Black"
    style_ref: "themen-plakat/impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
```

## ParaStyle-Hygiene

Template-lokale ParaStyles (in `meta.yml::ci_overrides.non_ci_styles` — 9 Einträge):

**V1-spezifisch (NEU — #19):**

- `themen-plakat/stat-hero` — Vollkorn Black Italic 56 pt Gelb, linesp 50.4
  (= 56 × 0.9 — line_spacing_0.9 conformant), align=left. Hero-Stat-Zahl pro Card.
- `themen-plakat/beleg-body-on-green` — Gotham Narrow Book 13 pt White, linesp 16.9,
  align=center. Body-Text auf Hellgrün-Card. **Bricht `brand:line_spacing_0.9`**
  (16.9 vs 13×0.9=11.7 → 5.2 pt Drift) — Lesbarkeit-Ausnahme, dokumentiert in
  `meta.yml::brand_overrides`.
- `themen-plakat/beleg-headline-yellow` — Gotham Narrow Bold 18 pt Gelb, linesp 16.2
  (= 18 × 0.9), align=center, **kern=0.72** (≈ 0.04 em letter-spacing — die DSL hat
  keine em-Einheit). CAPS via `Run.text.upper()` zum Emit-Zeitpunkt (ParaStyle hat
  kein `caps`-Feld).

**V1-modifiziert:**

- `themen-plakat/headline` — Vollkorn Black Italic 60 pt Dunkelgrün, **linesp 54**
  (war 64 vor V1 — auf 0.9-Faktor angepasst). align=left.

**Pre-V1, weiter aktiv (legacy / orphan):**

- `themen-plakat/sub` — Gotham Narrow Book 18 pt Dunkelgrün, linesp 22, align=left.
  Sub-Headline.
- `themen-plakat/beleg-headline` — Gotham Narrow Bold 24 pt Dunkelgrün, linesp 27,
  align=left. **Orphan in V1** — die V1-Beleg-Hierarchie ersetzt diesen Style durch
  `stat-hero` + `beleg-headline-yellow`. Belassen für Backward-Compat / spätere
  V2/V3-Layout-Optionen.
- `themen-plakat/beleg-body` — Gotham Narrow Book 13 pt Black, linesp 16, align=left.
  **Orphan in V1** — `beleg-body-on-green` ersetzt für Hellgrün-Hintergrund. Belassen
  für Backward-Compat.
- `themen-plakat/source` — Gotham Narrow Book 10 pt Dunkelgrün, linesp 12, align=left.
  Quelle bottom-left.
- `themen-plakat/impressum` — Gotham Narrow Book 7 pt Black, linesp 8, align=right.
  Impressum bottom-right.

## EPS / Image-Embedding-Strategie

```yaml
inject_strategy:
  hero_asset: "shared/sample-images/themen/klimaschutz-windrad.jpg"
  hero_anname: "Themen-Hero"
  inject_idiom: "library.inject_into_frame(target_w_mm=item.w_mm, target_h_mm=item.h_mm)"
  scale_type: 0
  watermark: true
  source_aspect: 1.5
  frame_aspect: 1.7
  crop_focus: [0.65, 0.50]
```

Themen-Hero wird via `INJECT_MAP` post-#24 Idiom (in `build.py::build_preview()`)
mit dem Library-Asset `themen_klimaschutz_windrad` gefüllt:

- `library.load("themen_klimaschutz_windrad", optional=True)` → PIL.Image (1536×1024).
- `library.inject_into_frame(item, img, target_w_mm=item.w_mm, target_h_mm=item.h_mm)` —
  pre-cropped die Quelle auf Frame-Aspect (194×114 = 1.7018) per
  `crop_focus=[0.65, 0.50]` (Turbine rechts der Mitte), embedded als inline JPEG
  bei 300 dpi, setzt `frame.scale_type=0`.
- Resultat: Hero füllt den 194×114 mm Frame exakt (kein Letterbox).

`build_template()` lässt den Frame ohne `inline_image_data` — round-trip-stabil für
`structural_check` / `spec_check` / Smoke. Nur `build_preview()` (genutzt von `build()`
für Gallery-Render) injiziert die Photo-Bytes in `template.sla`.

QR und Logo werden direkt als `inline_image_data` im `build_template()` eingebettet
(nicht via INJECT_MAP, da nicht library-managed).

## Background-Color Contract

Themen-Plakat hat kein Wahlkreuz — D12 ist nicht zutreffend.

Die V1-Hellgrün-Polygons (`Hero-Foto-Card`, `Beleg N — Card`) sind Brand-Hintergründe
für lesbare Text- und Foto-Überlagerung. Beleg-Body-Text in Weiß auf Hellgrün
(`brand:text_on_green`-Regel scope-skipped, da V1-Styles `themen-plakat/*`-Prefix
verwenden — Regel feuert nur für `^ci/(h|headline)`).

## Falz / Stanze

Keine.

## Brand-Hierarchy Contract

| Schicht                  | Größe   | Font                  | Farbe                           |
|--------------------------|---------|-----------------------|---------------------------------|
| Headline (These)         | **60 pt** | Vollkorn Black Italic | Dunkelgrün (auf White)        |
| Sub-Headline             | 18 pt   | Gotham Narrow Book    | Dunkelgrün (auf White)          |
| Beleg-Stat-Hero          | **56 pt** | Vollkorn Black Italic | Gelb (auf Hellgrün)           |
| Beleg-Label (CAPS)       | 18 pt   | Gotham Narrow Bold    | Gelb (auf Hellgrün), kern=0.72  |
| Beleg-Body               | 13 pt   | Gotham Narrow Book    | White (auf Hellgrün)            |
| Quelle                   | 10 pt   | Gotham Narrow Book    | Dunkelgrün (auf White)          |
| Impressum                | 7 pt    | Gotham Narrow Book    | Black (auf White)               |

**Begründung der V1-Schriftgröße-Wahl:**

- **60 pt These** in 170 mm Spalte: ~50 Zeichen Headline-Maxlänge, klare Lesbarkeit
  bei 50 cm Distanz. Vollkorn Black Italic für emotionalen Anker.
- **56 pt Stat-Hero** als Eyecatch pro Card: Verhältnis ~0.93 zur Headline (≈ gleichwertig
  als visueller Hierarchie-Peer, nicht subordinated).
- **18 pt Label CAPS** Yellow + 0.72 pt kern: caption-style Verbindung zwischen
  Stat und Body, formaler "Tag" pro Card.
- **13 pt Body** Weiß auf Hellgrün: 2 pt über A3-Mindest, Lese-Distanz 50 cm.
  16.9 pt linesp gibt visuelle Atempause auf grünem Hintergrund (1.3-Faktor statt
  Quickguide-0.9 — bewusst, dokumentiert).

**Whitespace-Rhythmus (V1 60/40-Split):**

- 12 mm Top-Margin → Logo (15, 10, 53.46×48); Logo bottom = 58.
- Hero-Foto-Card (15, 70, 200×120) und Headline These (235, 70, 170×100) starten beide
  bei y=70 — visuelle Top-Linie der "Hero-Region".
- Sub-Headline (235, 172, 170×14) sitzt 2 mm unter Headline These bottom.
- Hero-Foto-Card bottom = 190; 20 mm Whitespace bis zur Beleg-Card-Reihe (y=210).
- Beleg-Card (210, 124.67, 72) — Stat (215, 114, 24) — Label (242, 8) — Body (252, 26).
  Card bottom = 282; Body bottom = 278 (4 mm innerer Padding).
- 5 mm Whitespace nach Card bottom → Quelle/Impressum (y=287).

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: []
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Bilderdruck matt 170 g/m² oder Plakatpapier blueback 135 g/m²"
  print_method: "Offset (>= 100 Stück) oder Großformat-Digital (< 100)"
  cmyk_only: true
```

## Mediengesetz §24

Impressum-Slot vorhanden (anname `Impressum`), Default-Text aus
`tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`. Endnutzer:innen passen
Druckerei und Auflage an.

## Brand-Accent — Hellgrün als Layout-Träger

V1 antwortet auf den iter-3-Befund "Body löst sich nicht vom Weißraum" mit drei
Hellgrün-Cards. Magenta-Stoerer wird bewusst nicht eingesetzt — V1 nutzt
Brand-Hellgrün als sekundäre Trägerfarbe (parallel zu Headline-Dunkelgrün), damit
die Argumentation strukturierte visuelle Wegweiser bekommt ohne den ruhigen
Argumentations-Modus zu zerschneiden.

## Codex-Demo-Image (D11)

V1 nutzt das library-managed Hero-Asset `themen_klimaschutz_windrad` (Windrad-
Foto, 1536×1024, native 1.5:1). Asset liegt unter
`shared/sample-images/themen/klimaschutz-windrad.jpg`. Manifest-Eintrag in
`tools/sla_lib/library/manifest.yml`.

Codex-visual-Review für #19: SKIP (locked decision #6 — single-page A3 quer,
`brand:image_fills_frame` ist Primär-Detector für die Regression-Klasse).

## Content-Discipline (Stat-Hero-Format)

V1 ersetzt den iter-3 "12 700 grüne Jobs"-Headline durch ein big-number + caps
Label-Pair pro Card. Bezirksgruppen müssen den Stat-Wert auf eine prägnante,
lesbare Zahl reduzieren ("12 700", "1.2 Mrd. €", "36 %") — der erläuternde Kontext
liegt im Body-Text, nicht im Stat. Open Question 2 in ISSUE.md: README-Note für
`templates/themen-plakat-a3-quer/README.md` als Follow-up.
