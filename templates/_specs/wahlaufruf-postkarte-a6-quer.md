# Spec: Wahlaufruf-Postkarte A6 quer (V1 "Symbol-Tight")

```yaml
id: wahlaufruf-postkarte-a6-quer
title: Wahlaufruf-Postkarte A6 quer
format: A6 quer 2-seitig
trim_mm: [148, 105]
bleed_mm: 3
pages: 2
fold_type: none
fold_positions_mm: []
cut_type: none
audience: [bezirksgruppe, ortsgruppe, kandidat]
```

## Audience und Layout-Philosophie

Wahlkampf-Postkarte für die Endphase einer Wahl: Bezirks- und Ortsgruppen verteilen sie
in Postwurf, am Infostand oder in der Tür-Kampagne. Lese-Distanz **Hand-Distanz** ~30–40 cm.

**Layout-Philosophie (V1 — "Symbol-Tight"):** Symbol-zentriert vorne mit Hellgrün-Halo,
zwei-spaltige Info-Komposition hinten.

- **Vorderseite:** Wahlkreuz-Hero (60×60 mm) auf Dunkelgrün-Vollbild, mit zentriertem
  Hellgrün-Halo (62×62 mm Ellipse) als atmender Schutzhülle. Darunter ein zweiteiliger
  Headline-Stack: Datum-Zeile (Vollkorn Black Italic 26 pt Gelb) + Call-to-Action
  (Gotham Narrow Bold 14 pt Weiß CAPS, letter-spacing ≈ 0.15 em).
- **Rückseite:** Split-Half — Dunkelgrün links (3 W-Fragen Was/Warum/Wann), weißes
  Impressum-Strip unten, weißer rechter Bereich für QR-Block (Label + Code 36×36 +
  URL) und das weiße Logo oben rechts.

V1 ist die "Symbol-Tight"-Variante aus `improvements/01-wahlaufruf-postkarte.md` §"Variante 1".
V2 (Datum-Banner) und V3 (Asymmetric Hero) sind Backlog (eigene Issues).

V1 etabliert das `*-on-green`-ParaStyle-Migrationsmuster (`wahlaufruf/cell-body-on-green`
parallel zur bestehenden `wahlaufruf/cell-body`), das #18-#21 wiederverwenden.

## Layout — Vorderseite (Page 1, Wahlkreuz-Hero + Headline-Stack)

```text
   <--------148mm-------->
  +----------------------+   ↑
  | L                    |   |  ← 6 mm top (Logo Grüne weiss, 18.9×5.7)
  |                      |   |
  |     ╱─────────────╲  |   |
  |    │ ┌──────────┐  │ |   |  Halo (Hellgrün-Ellipse 62×62)
  |    │ │   WK     │  │ |   |  WK = Wahlkreuz 60×60 (zentriert (74, 48))
  |    │ │  60×60   │  │ |   |
  |    │ └──────────┘  │ | 105
  |     ╲─────────────╱  | mm
  |                      |   |
  | DATUM (Gelb 26 pt)   |   |  headline_datum  (y=82)
  | CTA   (Weiß 14 pt)   |   |  headline_cta    (y=92, ≡ datum + 10mm)
  +----------------------+   ↓

Legende:
  L     = Logo Grüne (weiss), 18.9 × 5.7 mm Print-Soll 3×M
  Halo  = wahlkreuz_halo, Hellgrün-Polygon shape="ellipse", layer=0
  WK    = Wahlkreuz, 60 × 60 mm, layer=1, anname kept capitalized
          (brand:wahlkreuz_colored_bg ist case-sensitive)
  DATUM = headline_datum, Vollkorn Black Italic 26 pt Gelb (Demo: "SONNTAG, 26. JÄNNER 2026")
  CTA   = headline_cta,   Gotham Narrow Bold 14 pt Weiß, kern=2.1
          (Demo: "GIB DEINE STIMME DEN GRÜNEN")
```

## Layout — Rückseite (Page 2, Split-Half + 3 W-Fragen + QR)

```text
   <--------148mm-------->
  +----------------------+   ↑
  |::::::::::::::::|     |   |  Dunkelgrün-Polygon links (-3, -3, 93, 111)
  |:: WAS?      :::|  L  |   |  L     = logo_back (weiss, 18.9×5.7) bei (96, 8)
  |:: …body…   :::|     |   |  WAS?  = frage_was_headline (y=12, Gelb 18 pt)
  |::             |╲QR-L╱|   |  body  = frage_was_body    (y=21, Weiß  9 pt)
  |:: WARUM?    ::|│QR-C│|   |  QR-L  = qr_label  "WO INFORMIEREN"   (y=24)
  |:: …body…   :::|│ 36 │|   |  QR-C  = qr_code   36×36 mm           (y=31)
  |::             |╱QR-U╲|   |  QR-U  = qr_url    "gruene-noe.at"    (y=71)
  |:: WANN?     ::|     |   |  WARUM?= frage_warum_headline (y=40)
  |:: …body…   :::|     |   |  body  = frage_warum_body    (y=49)
  |::             |     | 105|  WANN? = frage_wann_headline (y=68)
  |____________________ |   |  body  = frage_wann_body     (y=77)
  | I (Impressum y=101) | mm |  Strip = impressum_strip_bg White (0,96,148,9)
  +----------------------+   ↓

Hierarchie der Hintergrund-Polygons (layer=0, emit-order zuerst):
  1. seitenhintergrund_back_left (Dunkelgrün, -3, -3, 93, 111)
  2. impressum_strip_bg          (White,         0, 96, 148, 9)
```

## Constraints — V1 strukturelle Invarianten (Prosa, SCHEMA.md §11-12)

Code lebt in `templates/wahlaufruf-postkarte-a6-quer/build.py::CONSTRAINTS`
(20 Einträge). Diese Spec beschreibt Intent — Code ist Vertrag.

### Vorderseite — Halo + Symbol + Headline-Stack

- **Halo und Symbol teilen sich beide Mittelachsen.** Halo `wahlkreuz_halo` (62×62,
  Ellipse) und Symbol `Wahlkreuz` (60×60) zentrieren beide auf `(74, 48)`.
  Code: `CONSTRAINTS["halo_x_centered"]` (`mirrored_x` mit `axis_mm=74.0`),
  `CONSTRAINTS["halo_y_centered"]` (`mirrored_y` mit `axis_mm=48.0`).
  **Wichtig:** `mirrored_x/y` (Mittelpunkts-Mittel) statt `same_x/y` (Eck-Vergleich) —
  die Eckpunkte unterscheiden sich um 1 mm > Toleranz und würden `same_*` rot machen.
- **Halo umschließt Symbol.** Code: `CONSTRAINTS["halo_contains_symbol"]` (`inside`).
- **Datum→CTA vertikaler Abstand 10 mm.** Code: `CONSTRAINTS["datum_to_cta"]`
  (`distance_y(equals=10.0)`).
- **Logo→Headline-Spalten-Offset 4 mm.** Logo sitzt am Trim-Margin (x=6); die
  Headline-Spalte hat 4 mm zusätzliche Padding (x=10). Code:
  `CONSTRAINTS["logo_to_headline_column_offset_datum"]` und
  `CONSTRAINTS["logo_to_headline_column_offset_cta"]` (`distance_x(equals=4.0)`).
  Formalisiert das absichtliche Offset gegen `brand:undeclared_alignment_drift`.

### Rückseite — 3 W-Fragen-Stack

- **Headlines und Bodies teilen sich die linke Achse x=6.** Code:
  `CONSTRAINTS["fragen_left_axis"]` und `CONSTRAINTS["bodies_left_axis"]`
  (`same_x` über die jeweiligen 3 Frames).
- **Pro W-Frage hängt der Body 1 mm unter der Headline.** Code:
  `CONSTRAINTS["was_stack"]`, `CONSTRAINTS["warum_stack"]`,
  `CONSTRAINTS["wann_stack"]` (`aligned_below(gap_mm=1.0)`).
- **Impressum hängt 4.5 mm unter dem letzten W-Frage-Body.**
  `frage_wann_body.bottom = 77+20 = 97` → `Impressum.y = 101.5` (auf
  `impressum_strip_bg`). Code: `CONSTRAINTS["impressum_below_wann"]`
  (`aligned_below(gap_mm=4.5)`).

### Rückseite — QR-Block (rechte Spalte)

- **Label, Code und URL teilen sich die rechte Achse x=96.** Code:
  `CONSTRAINTS["qr_axis"]` (`same_x`).
- **Code hängt 2 mm unter Label** (`qr_label.bottom=24+5=29` → `qr_code.y=31`).
  Code: `CONSTRAINTS["qr_label_anchors_code"]` (`aligned_below(gap_mm=2.0)`).
- **URL hängt 4 mm unter Code** (`qr_code.bottom=31+36=67` → `qr_url.y=71`).
  Code: `CONSTRAINTS["qr_url_below_code"]` (`aligned_below(gap_mm=4.0)`).
- **Label hängt 10.3 mm unter logo_back** (`logo_back.bottom=8+5.7=13.7` →
  `qr_label.y=24`). Code: `CONSTRAINTS["logo_back_anchors_qr"]`
  (`aligned_below(gap_mm=10.3)`).

> **Achtung — locked decision #2 / ship-blocker B2/B3:** Die ISSUE.md gibt
> y-Werte 24/30/68 vor. Diese verletzen `aligned_below` mit den deklarierten
> Gaps (2 mm und 4 mm). V1 verwendet die korrigierten Werte **24/31/71**.

### Rückseite — Cross-Column-Offsets

Diese Constraints formalisieren absichtliche, nicht-axiale Offsets, die der
Audit-Heuristik (`brand:undeclared_alignment_drift`, axis_tol_mm=5.0) sonst
als verdächtig flaggt. Geometrie unverändert; nur Intent dokumentiert.

- **Background-left-Polygon (x=-3) vs Impressum-Strip (x=0): 3 mm Offset.**
  Code: `CONSTRAINTS["back_bg_strip_x_offset"]` (`distance_x(equals=3.0)`).
- **logo_back (y=8) vs erster W-Frage-Headline (y=12): 4 mm.** Code:
  `CONSTRAINTS["logo_back_to_first_frage_y_offset"]` (`distance_y(equals=4.0)`).
- **frage_was_body (y=21) vs qr_label (y=24): 3 mm.** Code:
  `CONSTRAINTS["frage_was_body_to_qr_label_y_offset"]` (`distance_y(equals=3.0)`).
- **frage_wann_headline (y=68) vs qr_url (y=71): 3 mm.** Code:
  `CONSTRAINTS["frage_wann_headline_to_qr_url_y_offset"]`
  (`distance_y(equals=3.0)`).

### Brand-Constraints

Aktiv via `BRAND_CONSTRAINTS` aus `tools/sla_lib/builder/brand_constraints.py`:
Color-Palette, Font-Family, HL/SL-Distanz, Logo-Größe (jetzt nativ grün, weil
beide V1-Logos exakt 3×M = 18.9 mm sind), Text-auf-Grün, Bleed,
Wahlkreuz-Hintergrund (D12), `inside_page`, `spine_safety`,
`undeclared_alignment_drift` (jetzt nativ grün, weil V1 alle Adjacencies
deklariert).

**Override aktiv (siehe `meta.yml::brand_overrides`):**

- `brand:line_spacing_0.9` — V1's `wahlaufruf/cell-body-on-green` (9 pt body,
  11 pt linesp) driftet bewusst um 2.9 pt vom Quickguide-0.9-Faktor. Begründung:
  Lesbarkeit von 9 pt Weiß-auf-Dunkelgrün braucht eine luftigere Zeilenführung
  als der dichte 0.9-Default. Die Pre-V1-Styles (`wahlaufruf/headline`,
  `wahlaufruf/cell-headline`, `wahlaufruf/cell-body`) bleiben als Orphans im
  ParaStyle-Set für die `*-on-green`-Migration in #18-#21; sie driften ebenfalls
  vom 0.9-Faktor.

**Stale Overrides entfernt (V1):**

- `brand:logo_size_3M` — V1 setzt beide Logos auf exakt 3×M = 18.9 mm.
- `brand:undeclared_alignment_drift` — V1 deklariert alle Adjacencies via
  CONSTRAINTS (siehe oben).

## Slot-Tabelle — Vorderseite (Page 1)

| anname               | type             | x_mm | y_mm | w_mm | h_mm | fcolor      | style_ref                       | example                              |
|----------------------|------------------|------|------|------|------|-------------|---------------------------------|--------------------------------------|
| Seitenhintergrund (front) | Polygon     | -3   | -3   | 154  | 111  | Dunkelgrün  | —                               | Vollbild Vorderseite                 |
| Logo Grüne (weiss)   | ImageFrame       | 6    | 6    | 18.9 | 5.7  | —           | shared/logos/gruene-weiss.png   | Print-Soll 3×M, local_scale=0.130    |
| wahlkreuz_halo       | Polygon (ellipse)| 43   | 17   | 62   | 62   | Hellgrün    | —                               | Hellgrün-Schutzhülle, layer=0        |
| Wahlkreuz            | ImageFrame       | 44   | 18   | 60   | 60   | —           | shared/assets/wahlkreuz.png     | Symbol, layer=1, anname capitalized  |
| headline_datum       | TextFrame        | 10   | 82   | 128  | 10   | Gelb        | wahlaufruf/headline-emphasis    | "SONNTAG, 26. JÄNNER 2026"           |
| headline_cta         | TextFrame        | 10   | 92   | 128  | 10   | White       | wahlaufruf/headline-cta         | "GIB DEINE STIMME DEN GRÜNEN"        |

## Slot-Tabelle — Rückseite (Page 2)

| anname                       | type      | x_mm | y_mm  | w_mm | h_mm | fcolor      | style_ref                           | example                                  |
|------------------------------|-----------|------|-------|------|------|-------------|-------------------------------------|------------------------------------------|
| seitenhintergrund_back_left  | Polygon   | -3   | -3    | 93   | 111  | Dunkelgrün  | —                                   | Linke Hälfte (W-Fragen-Hintergrund)      |
| impressum_strip_bg           | Polygon   | 0    | 96    | 148  | 9    | White       | —                                   | Impressum-Strip-Hintergrund              |
| logo_back                    | ImageFrame| 96   | 8     | 18.9 | 5.7  | —           | shared/logos/gruene-weiss.png       | local_scale=(0.130, 0.130) explizit      |
| frage_was_headline           | TextFrame | 6    | 12    | 84   | 8    | Gelb        | wahlaufruf/cell-headline-yellow     | "WAS?"                                   |
| frage_was_body               | TextFrame | 6    | 21    | 84   | 20   | White       | wahlaufruf/cell-body-on-green       | Klimaschutz, leistbares Wohnen, Bildung… |
| frage_warum_headline         | TextFrame | 6    | 40    | 84   | 8    | Gelb        | wahlaufruf/cell-headline-yellow     | "WARUM?"                                 |
| frage_warum_body             | TextFrame | 6    | 49    | 84   | 20   | White       | wahlaufruf/cell-body-on-green       | Mut zur Veränderung. Faktenbasiert. …    |
| frage_wann_headline          | TextFrame | 6    | 68    | 84   | 8    | Gelb        | wahlaufruf/cell-headline-yellow     | "WANN?"                                  |
| frage_wann_body              | TextFrame | 6    | 77    | 84   | 20   | White       | wahlaufruf/cell-body-on-green       | Sonntag, 26. Jänner 2026, 7–17 Uhr.      |
| qr_label                     | TextFrame | 96   | 24    | 36   | 5    | Dunkelgrün  | wahlaufruf/qr-label                 | "WO INFORMIEREN"                         |
| qr_code                      | ImageFrame| 96   | 31    | 36   | 36   | —           | samples/qr-back.png (optional)      | Demo-QR; ersetzt durch Bezirks-URL       |
| qr_url                       | TextFrame | 96   | 71    | 36   | 5    | Dunkelgrün  | wahlaufruf/qr-url                   | "gruene-noe.at"                          |
| Impressum                    | TextFrame | 6    | 101.5 | 136  | 4    | Black       | wahlaufruf/impressum                | Medieninhaber: Die Grünen NÖ, …          |

```yaml
slots:
  - anname: "Seitenhintergrund (front)"
    type: Polygon
    x_mm: -3
    y_mm: -3
    w_mm: 154
    h_mm: 111
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "Vollbild Vorderseite"
  - anname: "Logo Grüne (weiss)"
    type: ImageFrame
    x_mm: 6
    y_mm: 6
    w_mm: 18.9
    h_mm: 5.7
    fcolor: ""
    style_ref: "shared/logos/gruene-weiss.png"
    example: "Print-Soll 3*M, local_scale=(0.130, 0.130)"
  - anname: "wahlkreuz_halo"
    type: Polygon
    x_mm: 43
    y_mm: 17
    w_mm: 62
    h_mm: 62
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Hellgrün-Ellipse, shape='ellipse', layer=0"
  - anname: "Wahlkreuz"
    type: ImageFrame
    x_mm: 44
    y_mm: 18
    w_mm: 60
    h_mm: 60
    fcolor: ""
    style_ref: "shared/assets/wahlkreuz.png"
    example: "Symbol, layer=1, ANNAME case-sensitive für brand:wahlkreuz_colored_bg"
  - anname: "headline_datum"
    type: TextFrame
    x_mm: 10
    y_mm: 82
    w_mm: 128
    h_mm: 10
    fcolor: "Gelb"
    style_ref: "wahlaufruf/headline-emphasis"
    example: "SONNTAG, 26. JÄNNER 2026"
  - anname: "headline_cta"
    type: TextFrame
    x_mm: 10
    y_mm: 92
    w_mm: 128
    h_mm: 10
    fcolor: "White"
    style_ref: "wahlaufruf/headline-cta"
    example: "GIB DEINE STIMME DEN GRÜNEN"
  - anname: "seitenhintergrund_back_left"
    type: Polygon
    x_mm: -3
    y_mm: -3
    w_mm: 93
    h_mm: 111
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "Linke Hälfte (W-Fragen-Hintergrund)"
  - anname: "impressum_strip_bg"
    type: Polygon
    x_mm: 0
    y_mm: 96
    w_mm: 148
    h_mm: 9
    fcolor: "White"
    style_ref: ""
    example: "Impressum-Strip-Hintergrund"
  - anname: "logo_back"
    type: ImageFrame
    x_mm: 96
    y_mm: 8
    w_mm: 18.9
    h_mm: 5.7
    fcolor: ""
    style_ref: "shared/logos/gruene-weiss.png"
    example: "local_scale=(0.130, 0.130) explizit; default 1.0 würde 5.5x clippen"
  - anname: "frage_was_headline"
    type: TextFrame
    x_mm: 6
    y_mm: 12
    w_mm: 84
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "wahlaufruf/cell-headline-yellow"
    example: "WAS?"
  - anname: "frage_was_body"
    type: TextFrame
    x_mm: 6
    y_mm: 21
    w_mm: 84
    h_mm: 20
    fcolor: "White"
    style_ref: "wahlaufruf/cell-body-on-green"
    example: "Klimaschutz, leistbares Wohnen, Bildung — konkret in deiner Gemeinde."
  - anname: "frage_warum_headline"
    type: TextFrame
    x_mm: 6
    y_mm: 40
    w_mm: 84
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "wahlaufruf/cell-headline-yellow"
    example: "WARUM?"
  - anname: "frage_warum_body"
    type: TextFrame
    x_mm: 6
    y_mm: 49
    w_mm: 84
    h_mm: 20
    fcolor: "White"
    style_ref: "wahlaufruf/cell-body-on-green"
    example: "Mut zur Veränderung. Faktenbasiert. Generationen-gerecht."
  - anname: "frage_wann_headline"
    type: TextFrame
    x_mm: 6
    y_mm: 68
    w_mm: 84
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "wahlaufruf/cell-headline-yellow"
    example: "WANN?"
  - anname: "frage_wann_body"
    type: TextFrame
    x_mm: 6
    y_mm: 77
    w_mm: 84
    h_mm: 20
    fcolor: "White"
    style_ref: "wahlaufruf/cell-body-on-green"
    example: "Sonntag, 26. Jänner 2026, 7-17 Uhr."
  - anname: "qr_label"
    type: TextFrame
    x_mm: 96
    y_mm: 24
    w_mm: 36
    h_mm: 5
    fcolor: "Dunkelgrün"
    style_ref: "wahlaufruf/qr-label"
    example: "WO INFORMIEREN"
  - anname: "qr_code"
    type: ImageFrame
    x_mm: 96
    y_mm: 31
    w_mm: 36
    h_mm: 36
    fcolor: ""
    style_ref: "samples/qr-back.png"
    example: "Demo-QR; ersetzt durch Bezirks-URL"
  - anname: "qr_url"
    type: TextFrame
    x_mm: 96
    y_mm: 71
    w_mm: 36
    h_mm: 5
    fcolor: "Dunkelgrün"
    style_ref: "wahlaufruf/qr-url"
    example: "gruene-noe.at"
  - anname: "Impressum"
    type: TextFrame
    x_mm: 6
    y_mm: 101.5
    w_mm: 136
    h_mm: 4
    fcolor: "Black"
    style_ref: "wahlaufruf/impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
```

## ParaStyle-Hygiene

Template-lokale ParaStyles (in `meta.yml::ci_overrides.non_ci_styles`):

**V1-spezifisch (NEU):**

- `wahlaufruf/headline-emphasis` — Vollkorn Black Italic 26 pt Gelb, linesp 23,
  align=center. Hero-Datum-Zeile vorne.
- `wahlaufruf/headline-cta` — Gotham Narrow Bold 14 pt White, linesp 13,
  align=center, **kern=2.1** (≈ 0.15 em letter-spacing — die DSL hat keine
  em-Einheit). Hero-CTA vorne.
- `wahlaufruf/cell-headline-yellow` — Vollkorn Black Italic 18 pt Gelb,
  linesp 16, align=left. W-Frage-Headlines.
- `wahlaufruf/cell-body-on-green` — Gotham Narrow Book 9 pt White, linesp 11,
  align=left. W-Frage-Bodies. **Bricht `brand:line_spacing_0.9`** (linesp 11
  vs. 9×0.9=8.1 → 2.9pt drift) — Lesbarkeit-Ausnahme, dokumentiert in
  `meta.yml::brand_overrides`.
- `wahlaufruf/qr-label` — Gotham Narrow Bold 12 pt Dunkelgrün, linesp 11,
  align=center. QR-Label oben.
- `wahlaufruf/qr-url` — Gotham Narrow Bold 11 pt Dunkelgrün, linesp 10,
  align=center. QR-URL unten.

**V1-modifiziert:**

- `wahlaufruf/impressum` — Gotham Narrow Book **5 pt** Black, linesp **4.5**,
  align=left. (War 6 pt / linesp 7 vor V1; defensive Anpassung — passt jetzt
  nativ in den 0.9-Faktor.)

**Legacy / Orphan (gelöschte Frames; bewusst beibehalten als Migrations-Anker):**

- `wahlaufruf/headline` — Gotham Narrow Bold 24 pt White. **Orphan in V1**;
  die V1-Headline-Hierarchie ersetzt diesen Style durch
  `headline-emphasis` + `headline-cta`.
- `wahlaufruf/cell-headline` — Gotham Narrow Bold 14 pt Dunkelgrün. **Orphan
  in V1**; `cell-headline-yellow` ist die V1-Variante (gelb auf Dunkelgrün).
- `wahlaufruf/cell-body` — Gotham Narrow Book 9 pt Black. **Orphan in V1**;
  parallel-style `cell-body-on-green` für Dunkelgrün-Hintergrund. Bewusst
  belassen, damit #18-#21 das `*-on-green`-Migrationsmuster ablesen können
  (existing+parallel statt mutate-in-place).

## EPS / Image-Embedding-Strategie

```yaml
eps_strategy:
  asset_path: "shared/assets/wahlkreuz.png"
  scale_type: 0           # free / aspect-locked
  background_color: "Dunkelgrün"   # D12-Pflicht
  background_padding_mm: 4.0
  encoding: "qcompress"
  helper: "pack_inline_image"
```

`shared/assets/wahlkreuz.png` ist ein RGBA-PNG (1200×1299, gelbes Kreuz im
weißen Kreis, Alpha-Channel außerhalb des Kreises). Für Scribus als
`inline_image_data` mit `qCompress`-Encoding eingebettet (Helper
`pack_inline_image` in `tools/sla_lib/builder/primitives.py`).

V1 ergänzt: `shared/logos/gruene-weiss.png` wird sowohl auf der Vorderseite
(weißes Wordmark auf Dunkelgrün) ALS AUCH auf der Rückseite (`logo_back` über
dem QR-Block) verwendet. Beide bei Print-Soll **3×M = 18.9 mm** mit explizitem
`local_scale=(0.130, 0.130)`. **Wichtig:** Default `local_scale=(1.0, 1.0)`
würde das Asset bei 5.5× rendern und clippen.

## Background-Color Contract für Wahlkreuz (D12)

> **Der Wahlkreuz MUSS auf farbigem Brand-Hintergrund stehen — `Dunkelgrün`,
> `Hellgrün`, oder `Magenta`. NIE auf Weiß. NIE auf Gelb.**
>
> Begründung: Das Asset ist ein gelbes Kreuz in einem weißen Kreis (PNG mit
> Alpha-Channel, RGBA 1200×1299). Der weiße Kreis ist die Schutzhülle, die den
> Symbolcharakter ausmacht ("geschützter Wahlakt im Kreis"). Auf weißem
> Hintergrund verschwindet der Kreis und nur das gelbe Kreuz bleibt — der
> Symbolcharakter geht verloren. Auf gelbem Hintergrund verschwindet das Kreuz.

**V1 wählt zwei Schichten Brand-Hintergrund:**

- `Seitenhintergrund (front)` — **Dunkelgrün** Vollbild (D12-Pflicht).
- `wahlkreuz_halo` — **Hellgrün** Ellipse 62×62 (atmende Schutzhülle).

Beide sind Brand-Farben aus dem D12-Set; beide kontrastieren mit dem gelben
Kreuz. Der Halo addiert eine sekundäre Hervorhebung ohne den primären
D12-Vertrag zu brechen.

## Falz / Stanze

Keine.

## Brand-Hierarchy Contract

| Schicht                  | Größe   | Font                 | Farbe                          |
|--------------------------|---------|----------------------|--------------------------------|
| Datum (front)            | 26 pt   | Vollkorn Black Italic| Gelb (auf Dunkelgrün)          |
| CTA (front)              | 14 pt   | Gotham Narrow Bold   | White (auf Dunkelgrün), kern=2.1 |
| W-Frage-Headline (back)  | 18 pt   | Vollkorn Black Italic| Gelb (auf Dunkelgrün)          |
| W-Frage-Body (back)      | 9 pt    | Gotham Narrow Book   | White (auf Dunkelgrün)         |
| QR-Label (back)          | 12 pt   | Gotham Narrow Bold   | Dunkelgrün (auf White)         |
| QR-URL (back)            | 11 pt   | Gotham Narrow Bold   | Dunkelgrün (auf White)         |
| Impressum (back)         | 5 pt    | Gotham Narrow Book   | Black (auf White)              |

**Begründung:**

- Datum 26 pt ist die größte Hero-Type des Templates — Datum vor CTA dominiert,
  weil es die dringende Information ist. Vollkorn Black Italic für emotionalen
  Akzent; Gotham Narrow Bold (CTA) für funktionalen Akzent.
- W-Frage-Headlines 18 pt / W-Frage-Body 9 pt — Verhältnis 2.0, klare Hierarchie.
- 3 W-Fragen (NICHT 4) wegen vertikaler Atemwegen auf 105 mm hoch — V1 trades
  Cell-4 ("Wo informieren") gegen den eigenständigen QR-Block rechts.

**Whitespace-Rhythmus:**

- Vorderseite: Wahlkreuz 18–78 mm, Headline-Stack 82–102 mm. 4 mm Atempause
  zwischen Symbol-Bottom und Datum-Top, lässt das Symbol "atmen". Datum→CTA
  Gap 10 mm (formalisiert via `distance_y`).
- Rückseite: 3 W-Frage-Stacks bei y=12 / y=40 / y=68 (Pitch 28 mm pro Stack).
  Body unter Headline mit 1 mm Gap (formalisiert via `aligned_below`). Letzter
  Body (y=77, h=20) endet bei y=97; Impressum ab y=101.5 (4.5 mm Gap auf der
  weißen Strip).

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: []
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Bilderdruck matt 300 g/m² (Postkarten-Standard)"
  print_method: "Offset (≥ 500) oder Digital (< 500)"
  cmyk_only: true
```

## Mediengesetz §24

Impressum-Slot vorhanden auf Rückseite, Default-Text aus
`tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`.

## Messaging-Legality (NRWO §53)

> NRWO §53 verbietet die direkte Wahlanleitung. Erlaubt: „Wähle Grün am
> [Datum]" / „Gib deine Stimme den Grünen". Verboten: „Mach dein Kreuz bei
> den Grünen", „Kreuze hier".

Die V1 Demo-Strings (`headline_cta`: "GIB DEINE STIMME DEN GRÜNEN") sind
formell Wahlempfehlung, kein Anweisungstext. Endnutzer:innen MÜSSEN diesen
Text beim Anpassen beibehalten oder durch eine andere wahlempfehlungs-konforme
Formulierung ersetzen.

## Codex-Demo-Image (D11)

Optional. V1 lässt das Layout reine Symbol+Headline+Info-Komposition (kein
Hero-Bild). Falls eine spätere Iteration ein Hero-Bild einsetzen will, kann
ein Codex-Demo-Bild über das Manifest unter
`templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml` erzeugt werden.
Im Default-Bauchschritt **kein** Demo-Bild — Layout funktioniert ohne.
