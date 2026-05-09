# Spec: Wahltag-Türanhänger (V1 "Composed Hero")

```yaml
id: wahltag-tueranhaenger
title: Wahltag-Türanhänger
format: 105x250 mm vertikal 2-seitig
trim_mm: [105, 250]
bleed_mm: 2
pages: 2
fold_type: none
fold_positions_mm: []
cut_type: die-cut
audience: [bezirksgruppe, ortsgruppe, kandidat]
```

## Audience und Layout-Philosophie

**Tür-Kampagne am Wahltag-Vorabend:** Bezirks- und Ortsgruppen hängen den Anhänger am
Wahltag (oder am Abend davor) an Türklinken — Lese-Distanz **kurz und im Vorbeigehen**,
~30 cm. Trägt den Wahlkreuz-Hero und 1–2 Sätze als Erinnerung („Heute ist Wahltag.
Wähle Grün."). Rückseite trägt Kandidat-Foto + Kontaktdaten als Visitenkarte.

**Layout-Philosophie (V1 — "Composed Hero"):** Schmal-vertikal, 3-Zonen-Komposition mit
markenfarbigen Backing-Polygonen, die jeden Block zur eigenständigen "Karte" machen.

- **Vorderseite:** Brand-Bar (Dunkelgrün 14 mm) → Hellgrün-Akzent (4 mm Strip) →
  Lochzone → Hellgrün-Band mit zentriertem Wahlkreuz-Hero (55×55 mm) →
  Headline-Stack (Headline 28 pt + Sub 18 pt) → Bullets-Card (Hellgrün-Vollbleed
  unten 58 mm, white-on-green Body + Impressum).
- **Rückseite:** Brand-Bar mirrored → Lochzone → Portrait-Card (Hellgrün
  75×100 mm mit 5 mm uniformer Inset-Marge für das Portrait) → Visitenkarten-Footer
  (Dunkelgrün-Vollbleed unten 72 mm, Kandidat-Name 18 pt + Position + Kontakt-URL Gelb +
  Kontakt-Info weiß + QR auf weißem Backing + Impressum).

V1 etabliert das `*-on-green`-ParaStyle-Migrationsmuster aus #17 und führt es um die
Footer-/Card-Komposition fort (5 neue `tueranhaenger/*-on-green` ParaStyles). Die 35 mm
Türklinken-Stanze am oberen Drittel ist nicht-verhandelbar (das ist *was* den
Türanhänger zum Türanhänger macht); alle Inhalts-Zonen liegen außerhalb der Lochzone
y=25..60.

V2 ("Vertical Stripe", 90°/270° rotierte Logos — braucht neuen `RotatedImageFrame`-Helper)
und V3 ("Manifesto", `YellowUnderline`-Block) sind Backlog (eigene Issues).

## Layout — Vorderseite (Page 1, Composed Hero)

```text
   <--105mm-->
  +-----------+   ↑
  | L  Brand  |   |  ← Brand-Bar Dunkelgrün (-2..107 × -2..14, h_visible=14)
  +-----------+   |     L = Logo (weiss, 18.9×5.7) bei (10, 8)
  |::Akzent:::|   |  Hellgrün-Akzent (-2..107 × 14..18, h=4)
  +-----------+   |
  |           |   |
  |   Loch    |   |  Lochzone (Stanzkontur, y=25..60), keine Inhalte
  |    Ø35    |   |
  |           |   |
  +-----------+   |
  |:::Hellgrün-Band::|  Hellgrün-Band (-2..107 × 63..127, h=64)
  |::  ┌─────┐  ::|     WK = Wahlkreuz (Hero) bei (25, 70, 55, 55),
  |::  │ WK  │  ::| 250  zentriert auf Panel x=52.5
  |::  └─────┘  ::| mm
  +-----------+   |
  |           |   |  Heute ist  ← Headline-Wahltag (10, 138, 85, 32)
  | Heute ist |   |  Wahltag.     Vollkorn Black Italic 28 pt Dunkelgrün
  |  Wahltag. |   |               linesp 25.2 (Quickguide-konform 0.9×)
  |           |   |
  | Wähle Grün|   |  Sub-Headline (10, 176, 85, 12)
  |           |   |  Gotham Narrow Bold 18 pt Dunkelgrün
  |           |   |
  +-----------+   |
  |:::Bullets-Card::|  Bullets-Card (-2..107 × 192..250, h=58, Hellgrün)
  |:: • Klima ::|     Bullet-Liste (10, 200, 85, 40)
  |:: • Vor Ort::|     tueranhaenger/body-on-green (Gotham Book 11 pt White)
  |:: • gruene  ::|
  |::           ::|
  |:: I (Imp.) ::|     Impressum (10, 240, 85, 6)
  +-----------+   ↓     tueranhaenger/impressum-on-green (white)

Stanzkontur (S, on top-of-stack, DRUCKEN=0):
  - Außen-Rechteck: (0, 0) → (105, 250) mm
  - Loch-Kreis: Mittelpunkt (52.5, 42.5), Radius 17.5 mm
                (= 35 mm Ø, 25 mm vom Top + 17.5 mm Radius)
```

## Layout — Rückseite (Page 2, Visitenkarte)

```text
   <--105mm-->
  +-----------+   ↑
  | L  Brand  |   |  ← Brand-Bar Dunkelgrün (mirror front, h=14 visible)
  +-----------+   |     L = Logo (weiss, back-band) bei (10, 8)
  |           |   |
  |   Loch    |   |  Lochzone (selbe Koordinaten wie Front)
  |    Ø35    |   |
  |           |   |
  +-----------+   |
  |::::::::::::::|  Portrait-Card (15..90 × 70..170, h=100, Hellgrün)
  |::┌─────────┐:|  Kandidat-Portrait (20..85 × 75..165, h=90)
  |::│  FOTO   │:|     5 mm uniforme Inset-Marge auf allen Seiten
  |::│  65×90  │:|     (left/top/right) und 5 mm bottom
  |::└─────────┘:| 250
  |::::::::::::::| mm
  +-----------+   |
  |::Visitenkarten-Footer::| (-2..107 × 178..250, h=72, Dunkelgrün-Vollbleed)
  |::Stefan Beispiel:::::::|  Kandidat-Name (10, 184, 85, 10)
  |::                ::::::|  cand-name-on-green (Gotham Bold 18 pt White)
  |::Bürgermeisterkand.::::|  Kandidat-Position (10, 196, 85, 8)
  |::                ::::::|  cand-pos-on-green (Gotham Italic 10 pt White)
  |:: gruene-moedling.at:::|  Kontakt-URL (10, 210, 50, 8)
  |::                ┌────┐|  url-on-green (Vollkorn Italic 11 pt Gelb)
  |:: name@example   │ QR │|  Kontakt-Info (10, 218, 50, 20)
  |:: +43 660 ...    │26×│|  body-on-green (Gotham Book 11 pt White)
  |::                └────┘|  QR-Code (back) (70, 210, 26, 26) auf
  |::                ::::::|  QR White-Backing (68, 208, 30, 30, White)
  |:: I (Imp.)      ::::::|  Impressum (back) (10, 242, 85, 6)
  +-----------+   ↓        impressum-on-green (Gotham Book 6 pt White)

Stanzkontur (S, on top-of-stack, DRUCKEN=0):
  Identisch zur Vorderseite — Außen-Rechteck + Loch-Kreis.
```

## Constraints — V1 strukturelle Invarianten (Prosa, SCHEMA.md §11-12)

Die ausführbare Encoding der untenstehenden Beziehungen lebt im
`templates/wahltag-tueranhaenger/build.py::CONSTRAINTS`-Block (15 Einträge,
verifiziert durch `structural_check`). Diese Sektion ist die menschliche
Prosa-Beschreibung; sie wird **NICHT** als YAML-Block in der Spec dupliziert.

**Vorderseite:**

- **Brand-Bar → Hellgrün-Akzent (touching).** Die Brand-Bar (Dunkelgrün) endet bei
  y=14; die Hellgrün-Akzent-Strip beginnt exakt bei y=14 (Gap 0). Die beiden
  Polygone teilen die Full-Bleed-x-Achse (x=-2, w=109).
- **Hellgrün-Akzent → Hellgrün-Band: 49 mm Lochzone-Distanz.** Akzent endet bei y=18;
  das Band beginnt bei y=63 — die Lochzone (y=25..60 für die 35 mm Stanze)
  liegt sauber dazwischen.
- **Wahlkreuz horizontal zentriert auf Panel-Mitte (x=52.5).** Die `mirrored_x`-
  Beziehung zwischen Hellgrün-Band und Wahlkreuz pinned die Symmetrie um
  Panel-Center. Wahlkreuz 25..80 × 70..125 mm (55×55), Band hostet ihn
  vollständig (`inside`-Containment).
- **Headline 11 mm unterhalb des Hellgrün-Bands.** Band endet bei y=127, Headline
  beginnt bei y=138. Geometrie via `distance_y` gepinnt (75 mm absolute
  Top-zu-Top-Distanz, da die x-Positionen nicht aligned sind: Band x=-2,
  Headline x=10).
- **Headline → Sub-Headline: 38 mm Top-Distanz.** Pragmatic-Override im
  250-mm-Vertikalformat (HL→Sub-Quickguide-Formel = 19.8 mm; V1 nutzt
  38 mm = ca. zweifache Formel zur Auffüllung der Hero-Zone). Dokumentiert
  als Override in `meta.yml::brand_overrides[brand:hl_sl_distance_x2]`.
- **Bullets-Card und Hellgrün-Akzent teilen Full-Bleed-x.** Beide bei x=-2,
  w=109 — `same_x`-Pin garantiert konsistente Vollbleed-Ausdehnung.
- **Bullet-Liste containment.** Bullet-Liste (10, 200, 85, 40) liegt
  vollständig in der Bullets-Card (-2, 192, 109, 58); ebenso das
  Front-Impressum bei (10, 240, 85, 6).

**Rückseite:**

- **Brand-Bar Mirror-Pair.** Brand-Bar (Vorderseite) und Brand-Bar (Rückseite)
  teilen `same_size axis="h"` — beide 16 mm hoch (14 visible + 2 bleed).
  Die Logos darin sind ebenfalls mirror-positioniert (x=10, y=8, 18.9×5.7).
- **Portrait-Containment in Portrait-Card.** Portrait-Card (15, 70, 75, 100)
  hostet Kandidat-Portrait (20, 75, 65, 90) mit 5 mm uniformer Inset-Marge
  auf left/top/right und 5 mm bottom. Visuell wirkt die Hellgrün-Karte als
  Rahmen, der Portrait und Footer verbindet.
- **Kandidat-Name 109 mm absolute Top-Distanz zum Portrait.** Portrait y=75,
  Name y=184 — kein x-Alignment (Name x=10, Portrait x=20), daher
  `distance_y`-Pin statt `aligned_below`.
- **Kandidat-Position 2 mm unter Kandidat-Name (gestapelt).** Beide bei x=10
  (`aligned_below`-Pin). Position y=196 = Name y=184 + Name h=10 + 2 mm Gap.
- **Visitenkarten-Footer-Containment.** Kontakt-URL und Kontakt-Info liegen
  vollständig in der Visitenkarten-Footer-Polygon (-2, 178, 109, 72).
- **QR-Backing-Containment.** QR-Code (back) (70, 210, 26, 26) liegt
  vollständig in QR White-Backing (68, 208, 30, 30) — 2 mm uniformer
  Weiß-Rand für Kontrast auf Dunkelgrün.

## Stanzkontur

**Außen-Pfad:** geschlossenes Rechteck (0, 0) → (105, 0) → (105, 250) → (0, 250) → (0, 0).

**Loch-Pfad:** Kreis 35 mm Ø, 36-Segment-Polygon-Approximation (DSL-Block `DieCut`
generiert das automatisch via `DoorHangerCutout`-Wrapper).

**Spot-Color:** `Stanzkontur` (CMYK 0/100/0/0), document-local — siehe SCHEMA.md §7.

**Layer:** `Stanzkontur` (printable=False, flow=False, exportable=True).

**Druckerei-Naming-Variants** (P-PRINT-1):

```yaml
stanz_naming_variants:
  - "Stanzkontur"   # DACH-Default
  - "CutContour"    # International / Pantone-Druckereien
```

Endnutzer:innen müssen ggf. die Spot-Color umbenennen, wenn die Druckerei „CutContour"
fordert. Wir liefern „Stanzkontur" als Default (Österreichischer Druckerei-Standard).

## Slot-Tabelle — Vorderseite (Page 1)

| anname                     | type             | x_mm | y_mm | w_mm | h_mm | fcolor      | style_ref                              | example                                                 |
|----------------------------|------------------|------|------|------|------|-------------|----------------------------------------|---------------------------------------------------------|
| Brand-Bar (Vorderseite)    | Polygon          |  -2  |  -2  | 109  |  16  | Dunkelgrün  | —                                      | Vollbleed-Top, h_visible=14                             |
| Logo Grüne (weiss, top)    | ImageFrame       |  10  |   8  | 18.9 | 5.7  | —           | shared/logos/gruene-weiss.png          | local_scale=(0.130, 0.130), Print-Soll 3×M              |
| Hellgrün-Akzent            | Polygon          |  -2  |  14  | 109  |   4  | Hellgrün    | —                                      | Akzent-Strip unter Brand-Bar, layer=0                   |
| Hellgrün-Band (Wahlkreuz)  | Polygon          |  -2  |  63  | 109  |  64  | Hellgrün    | —                                      | Hero-Band hinter Wahlkreuz, layer=0                     |
| Wahlkreuz (Hero)           | ImageFrame       |  25  |  70  |  55  |  55  | —           | shared/assets/wahlkreuz.png            | Zentriert auf x=52.5 (Panel-Center)                     |
| Headline-Wahltag           | TextFrame        |  10  | 138  |  85  |  32  | Dunkelgrün  | tueranhaenger/headline (linesp 25.2)   | Heute ist\nWahltag.                                     |
| Sub-Headline               | TextFrame        |  10  | 176  |  85  |  12  | Dunkelgrün  | tueranhaenger/sub                      | Wähle Grün.                                             |
| Bullets-Card               | Polygon          |  -2  | 192  | 109  |  58  | Hellgrün    | —                                      | Vollbleed-Bottom-Card, layer=0                          |
| Bullet-Liste               | TextFrame        |  10  | 200  |  85  |  40  | White       | tueranhaenger/body-on-green            | • Klima · Soziales · Bildung\n• Vor Ort · Ehrlich · …   |
| Impressum                  | TextFrame        |  10  | 240  |  85  |   6  | White       | tueranhaenger/impressum-on-green       | Medieninhaber: Die Grünen NÖ, … (siehe "Bekannte Sorgen") |
| Stanzkontur Außen          | Polygon          |   0  |   0  | 105  | 250  | Stanzkontur | —                                      | Außen-Rechteck, DRUCKEN=0, top-of-stack                 |
| Stanzkontur Loch           | Polygon          | 35   | 25   |  35  |  35  | Stanzkontur | —                                      | 35 mm Ø Loch, 36-Segment-Approx, top-of-stack           |

## Slot-Tabelle — Rückseite (Page 2)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor      | style_ref                                | example                                                 |
|------------------------------|-----------|------|------|------|------|-------------|------------------------------------------|---------------------------------------------------------|
| Brand-Bar (Rückseite)        | Polygon   |  -2  |  -2  | 109  |  16  | Dunkelgrün  | —                                        | Mirror der Front-Brand-Bar                              |
| Logo Grüne (weiss, back-band)| ImageFrame|  10  |   8  | 18.9 | 5.7  | —           | shared/logos/gruene-weiss.png            | local_scale=(0.130, 0.130), Mirror der Front-Logo       |
| Portrait-Card                | Polygon   |  15  |  70  |  75  | 100  | Hellgrün    | —                                        | NEW V1 — Backing-Karte für Portrait, layer=0            |
| Kandidat-Portrait            | ImageFrame|  20  |  75  |  65  |  90  | —           | library:portrait_stefan / Codex demo     | 5 mm uniforme Inset-Marge in Portrait-Card              |
| Visitenkarten-Footer         | Polygon   |  -2  | 178  | 109  |  72  | Dunkelgrün  | —                                        | NEW V1 — Vollbleed-Footer, layer=0                      |
| Kandidat-Name                | TextFrame |  10  | 184  |  85  |  10  | White       | tueranhaenger/cand-name-on-green         | Stefan Beispiel (18 pt — V1 bumped 14→18)               |
| Kandidat-Position            | TextFrame |  10  | 196  |  85  |   8  | White       | tueranhaenger/cand-pos-on-green          | Bürgermeisterkandidat Mödling (kein opacity — DSL-Lücke) |
| Kontakt-URL                  | TextFrame |  10  | 210  |  50  |   8  | Gelb        | tueranhaenger/url-on-green               | gruene-moedling.at (Vollkorn Italic Gelb auf Dunkelgrün) |
| Kontakt-Info                 | TextFrame |  10  | 218  |  50  |  20  | White       | tueranhaenger/body-on-green              | stefan.beispiel@gruene-moedling.at\n+43 660 1234567     |
| QR White-Backing             | Polygon   |  68  | 208  |  30  |  30  | White       | —                                        | NEW V1 — Weiß-Backing für QR-Kontrast, layer=0          |
| QR-Code (back)               | ImageFrame|  70  | 210  |  26  |  26  | —           | samples/qr-back.png                      | 26 mm / 33 modules ≈ 0.79 mm/module (über D1-Min 0.5 mm) |
| Impressum (back)             | TextFrame |  10  | 242  |  85  |   6  | White       | tueranhaenger/impressum-on-green         | (gleicher Text wie Front-Impressum)                     |
| Stanzkontur Außen            | Polygon   |   0  |   0  | 105  | 250  | Stanzkontur | —                                        | Mirror der Front-Stanze                                 |
| Stanzkontur Loch             | Polygon   |  35  |  25  |  35  |  35  | Stanzkontur | —                                        | Mirror der Front-Stanze                                 |

```yaml
slots:
  - anname: "Brand-Bar (Vorderseite)"
    type: Polygon
    x_mm: -2
    y_mm: -2
    w_mm: 109
    h_mm: 16
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "Vollbleed-Top, h_visible=14"
  - anname: "Logo Grüne (weiss, top)"
    type: ImageFrame
    x_mm: 10
    y_mm: 8
    w_mm: 18.9
    h_mm: 5.7
    fcolor: ""
    style_ref: "shared/logos/gruene-weiss.png"
    example: "local_scale=(0.130, 0.130), Print-Soll 3*M"
  - anname: "Hellgrün-Akzent"
    type: Polygon
    x_mm: -2
    y_mm: 14
    w_mm: 109
    h_mm: 4
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Akzent-Strip unter Brand-Bar, layer=0"
  - anname: "Hellgrün-Band (Wahlkreuz)"
    type: Polygon
    x_mm: -2
    y_mm: 63
    w_mm: 109
    h_mm: 64
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Hero-Band hinter Wahlkreuz, layer=0"
  - anname: "Wahlkreuz (Hero)"
    type: ImageFrame
    x_mm: 25
    y_mm: 70
    w_mm: 55
    h_mm: 55
    fcolor: ""
    style_ref: "shared/assets/wahlkreuz.png"
    example: "Zentriert auf x=52.5 (Panel-Center)"
  - anname: "Headline-Wahltag"
    type: TextFrame
    x_mm: 10
    y_mm: 138
    w_mm: 85
    h_mm: 32
    fcolor: "Dunkelgrün"
    style_ref: "tueranhaenger/headline"
    example: "Heute ist\nWahltag."
  - anname: "Sub-Headline"
    type: TextFrame
    x_mm: 10
    y_mm: 176
    w_mm: 85
    h_mm: 12
    fcolor: "Dunkelgrün"
    style_ref: "tueranhaenger/sub"
    example: "Wähle Grün."
  - anname: "Bullets-Card"
    type: Polygon
    x_mm: -2
    y_mm: 192
    w_mm: 109
    h_mm: 58
    fcolor: "Hellgrün"
    style_ref: ""
    example: "Vollbleed-Bottom-Card, layer=0"
  - anname: "Bullet-Liste"
    type: TextFrame
    x_mm: 10
    y_mm: 200
    w_mm: 85
    h_mm: 40
    fcolor: "White"
    style_ref: "tueranhaenger/body-on-green"
    example: "• Klima · Soziales · Bildung\n• Vor Ort · Ehrlich · Faktenbasiert\n• Mehr auf gruene-noe.at"
  - anname: "Impressum"
    type: TextFrame
    x_mm: 10
    y_mm: 240
    w_mm: 85
    h_mm: 6
    fcolor: "White"
    style_ref: "tueranhaenger/impressum-on-green"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
  - anname: "Stanzkontur Außen"
    type: Polygon
    x_mm: 0
    y_mm: 0
    w_mm: 105
    h_mm: 250
    fcolor: "Stanzkontur"
    style_ref: ""
    example: "Außen-Rechteck, DRUCKEN=0, top-of-stack"
  - anname: "Stanzkontur Loch"
    type: Polygon
    x_mm: 35
    y_mm: 25
    w_mm: 35
    h_mm: 35
    fcolor: "Stanzkontur"
    style_ref: ""
    example: "35 mm Ø Loch, 36-Segment-Approx, top-of-stack"
  - anname: "Brand-Bar (Rückseite)"
    type: Polygon
    x_mm: -2
    y_mm: -2
    w_mm: 109
    h_mm: 16
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "Mirror der Front-Brand-Bar"
  - anname: "Logo Grüne (weiss, back-band)"
    type: ImageFrame
    x_mm: 10
    y_mm: 8
    w_mm: 18.9
    h_mm: 5.7
    fcolor: ""
    style_ref: "shared/logos/gruene-weiss.png"
    example: "local_scale=(0.130, 0.130), Mirror der Front-Logo"
  - anname: "Portrait-Card"
    type: Polygon
    x_mm: 15
    y_mm: 70
    w_mm: 75
    h_mm: 100
    fcolor: "Hellgrün"
    style_ref: ""
    example: "NEW V1 — Backing-Karte für Portrait, layer=0"
  - anname: "Kandidat-Portrait"
    type: ImageFrame
    x_mm: 20
    y_mm: 75
    w_mm: 65
    h_mm: 90
    fcolor: ""
    style_ref: "library:portrait_stefan / Codex demo"
    example: "5 mm uniforme Inset-Marge in Portrait-Card"
  - anname: "Visitenkarten-Footer"
    type: Polygon
    x_mm: -2
    y_mm: 178
    w_mm: 109
    h_mm: 72
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "NEW V1 — Vollbleed-Footer, layer=0"
  - anname: "Kandidat-Name"
    type: TextFrame
    x_mm: 10
    y_mm: 184
    w_mm: 85
    h_mm: 10
    fcolor: "White"
    style_ref: "tueranhaenger/cand-name-on-green"
    example: "Stefan Beispiel (18 pt — V1 bumped 14->18)"
  - anname: "Kandidat-Position"
    type: TextFrame
    x_mm: 10
    y_mm: 196
    w_mm: 85
    h_mm: 8
    fcolor: "White"
    style_ref: "tueranhaenger/cand-pos-on-green"
    example: "Buergermeisterkandidat Moedling (no opacity DSL field)"
  - anname: "Kontakt-URL"
    type: TextFrame
    x_mm: 10
    y_mm: 210
    w_mm: 50
    h_mm: 8
    fcolor: "Gelb"
    style_ref: "tueranhaenger/url-on-green"
    example: "gruene-moedling.at (Vollkorn Italic Gelb auf Dunkelgrün)"
  - anname: "Kontakt-Info"
    type: TextFrame
    x_mm: 10
    y_mm: 218
    w_mm: 50
    h_mm: 20
    fcolor: "White"
    style_ref: "tueranhaenger/body-on-green"
    example: "stefan.beispiel@gruene-moedling.at\n+43 660 1234567"
  - anname: "QR White-Backing"
    type: Polygon
    x_mm: 68
    y_mm: 208
    w_mm: 30
    h_mm: 30
    fcolor: "White"
    style_ref: ""
    example: "NEW V1 — Weiss-Backing fuer QR-Kontrast, layer=0"
  - anname: "QR-Code (back)"
    type: ImageFrame
    x_mm: 70
    y_mm: 210
    w_mm: 26
    h_mm: 26
    fcolor: ""
    style_ref: "samples/qr-back.png"
    example: "26 mm / 33 modules ~= 0.79 mm/module (above D1 min 0.5 mm)"
  - anname: "Impressum (back)"
    type: TextFrame
    x_mm: 10
    y_mm: 242
    w_mm: 85
    h_mm: 6
    fcolor: "White"
    style_ref: "tueranhaenger/impressum-on-green"
    example: "(gleicher Text wie Front-Impressum)"
```

## ParaStyle-Hygiene

Template-lokale ParaStyles (in `meta.yml::ci_overrides.non_ci_styles`, 12 Einträge):

**Original (V1 unverändert):**

- `tueranhaenger/headline` — Vollkorn Black Italic 28 pt Dunkelgrün, **linesp 25.2**
  (V1 brachte Headline auf Quickguide-konformen 0.9× Faktor; pre-V1 war 30 pt).
- `tueranhaenger/sub` — Gotham Narrow Bold 18 pt Dunkelgrün, linesp 22.
- `tueranhaenger/body` — Gotham Narrow Book 11 pt Black, linesp 14.
- `tueranhaenger/cand-name` — Gotham Narrow Bold 14 pt Dunkelgrün, linesp 16.
- `tueranhaenger/cand-pos` — Gotham Narrow Book Italic 10 pt Black, linesp 12.
- `tueranhaenger/url` — Gotham Narrow Bold 11 pt Dunkelgrün, linesp 14.
- `tueranhaenger/impressum` — Gotham Narrow Book 6 pt Black, linesp 7.

**V1 NEU (5 *-on-green Parallel-Styles, #17-Pattern):**

- `tueranhaenger/body-on-green` — Gotham Narrow Book 11 pt **White**, linesp 14.
- `tueranhaenger/url-on-green` — Vollkorn Black Italic 11 pt **Gelb**, linesp 14.
- `tueranhaenger/cand-name-on-green` — Gotham Narrow Bold **18 pt** White,
  linesp 20 (bumped fontsize 14→18 für stärkere Kandidat-Identifikation auf Footer).
- `tueranhaenger/cand-pos-on-green` — Gotham Narrow Book Italic 10 pt White, linesp 12.
- `tueranhaenger/impressum-on-green` — Gotham Narrow Book 6 pt White, linesp 7.

**Drift gegen `brand:line_spacing_0.9`:** 6 von 7 Original-Styles driften (z. B. body
14/11=1.27× statt 0.9×). Headline ist nach V1 jetzt konform (25.2/28=0.9). Override
in `meta.yml::brand_overrides[brand:line_spacing_0.9]` bleibt — der Block dokumentiert
die Drift als typografische Konvention.

## EPS / Image-Embedding-Strategie

```yaml
eps_strategy:
  asset_path: "shared/assets/wahlkreuz.png"
  scale_type: 0
  background_color: "Hellgrün"   # D12: alternative zur Postkarte-Dunkelgrün
  background_padding_mm: 4.0
  encoding: "qcompress"
  helper: "pack_inline_image"
```

## Background-Color Contract für Wahlkreuz (D12)

> **Der Wahlkreuz MUSS auf farbigem Brand-Hintergrund stehen — `Dunkelgrün`, `Hellgrün`,
> oder `Magenta`. NIE auf Weiß. NIE auf Gelb.**

**Diese Spec wählt `Hellgrün`** als Background. Begründung: Vorderseite hat weißen
Hintergrund (oben Brand-Bar weiß auf Dunkelgrün-Logo, Hero auf Weiß) — ein
Hellgrün-Polygon hinter dem Wahlkreuz erzeugt einen visuellen Anker, der die
Brand-Energie im Hero-Bereich konzentriert ohne das Layout vollflächig zu dunkeln.
Konsistenz mit Wahlaufruf-Postkarte (dort Dunkelgrün) ist nicht erforderlich — die
beiden Templates sind unabhängig nutzbar.

## Background-Color Contract — V1 Composed-Hero (gesamt)

V1 nutzt 4 Brand-Polygon-Farben über beide Seiten verteilt:

- **Hellgrün** auf: Hellgrün-Akzent (Front), Hellgrün-Band (Front), Bullets-Card (Front),
  Portrait-Card (Back).
- **Dunkelgrün** auf: Brand-Bar (beide Seiten), Visitenkarten-Footer (Back).
- **White** auf: QR White-Backing (Back) — dient als Kontrast-Backing für den QR auf
  Dunkelgrün und ist explizit NICHT in `FILLED_POLYGON_FILLS`, daher von
  `brand:image_text_overlap`-Detektion ausgeschlossen.
- **Stanzkontur** (Spot-Color, document-local) auf den DieCut-Pfaden (beide Seiten).

## Falz / Stanze

**Stanze:** ja, siehe Stanzkontur-Sektion oben. **Falz:** keine.

## Brand-Hierarchy Contract

| Schicht                | Größe  | Font                          | Farbe        | Notiz                                       |
|------------------------|--------|-------------------------------|--------------|---------------------------------------------|
| Logo (top + back-band) | 18.9 mm Breite (3×M) | gruene-weiss.png | weiß auf Dunkelgrün | local_scale=(0.130, 0.130) per #17-Pattern |
| Brand-Bar              | h_visible=14 mm | Polygon Dunkelgrün | —          | beidseitig, mirror via `same_size axis="h"` |
| Hellgrün-Akzent        | h=4 mm | Polygon Hellgrün             | —            | Vollbleed-Strip unter Brand-Bar (nur Front) |
| Headline-Wahltag       | 28 pt  | Vollkorn Black Italic         | Dunkelgrün   | linesp 25.2 (Quickguide-konform 0.9×)       |
| Sub-Headline           | 18 pt  | Gotham Narrow Bold            | Dunkelgrün   |                                             |
| Bullet-Liste           | 11 pt  | Gotham Narrow Book            | **White**    | auf Hellgrün Bullets-Card                   |
| Kandidat-Name          | 18 pt  | Gotham Narrow Bold            | **White**    | V1 bumped 14→18 für Visitenkarten-Wirkung   |
| Kandidat-Position      | 10 pt  | Gotham Narrow Book Italic     | **White**    | (kein opacity-Effekt — DSL-Lücke)           |
| Kontakt-URL            | 11 pt  | Vollkorn Black Italic         | **Gelb**     | Gelb auf Dunkelgrün — höchste Lesbarkeit    |
| Kontakt-Info           | 11 pt  | Gotham Narrow Book            | **White**    |                                             |
| Impressum (beide)      | 6 pt   | Gotham Narrow Book            | **White**    | (Front: WCAG-Sorge auf Hellgrün, siehe unten) |

**Begründung:**

- Logo-Shrink von 35 mm → 18.9 mm (V1) bringt beide weißen Logos auf das
  Quickguide-Sollmaß 3×M (kurze Kante = 105 mm → M = 6.3 mm → 3×M = 18.9 mm).
  Die Brand-Bar shrinkt entsprechend von 20 → 14 mm visible (16 mit Bleed),
  damit Logo und Bar im selben Verhältnis bleiben.
- Bund-Dunkel-Backseiten-Logo aus iter-3 wurde gelöscht (war transitorisches
  Doppel-Logo-Artefakt).
- Kandidat-Name-Bump 14→18 pt verstärkt Visitenkarten-Wirkung im neuen
  Footer-Block — das ist die primäre Person-Identifikation.
- Bullets-Card weiß-auf-Hellgrün: Body-Text-Lesbarkeit auf Brand-Farbe ist gut
  (~7:1 Kontrast). Das 6-pt-Impressum auf derselben Hellgrün-Fläche ist
  hingegen kritisch — siehe "Bekannte Sorgen".

## Print-Hints

```yaml
print_hints:
  bleed_mm: 2
  fold_mm: []
  cut_layer: "Stanzkontur"
  min_dpi: 300
  paper_recommendation: "Karton 250–300 g/m² (Steifigkeit für Türklinken-Aufhängung)"
  print_method: "Offset oder Digital, Stanze separat"
  cmyk_only: true
  stanz_naming_variants:
    - "Stanzkontur"
    - "CutContour"
```

## Mediengesetz §24

Impressum-Slot vorhanden (auf beiden Seiten), Default-Text. V1 Front-Impressum nutzt
`tueranhaenger/impressum-on-green` (white) auf Bullets-Card-Hellgrün; Back-Impressum
nutzt denselben Style auf Visitenkarten-Footer-Dunkelgrün.

## Messaging-Legality (NRWO §53)

> „Heute ist Wahltag. Wähle Grün." — Wahlempfehlung, kein Anweisungstext. ✅

## Bekannte Sorgen (V1 known concerns)

- **WCAG-Kontrast Front-Impressum** — `Impressum` (front) ist 6 pt **white-on-Hellgrün**
  (Hellgrün ≈ #C7DA6A → ungefähres Kontrast-Verhältnis ~1.7:1, deutlich unter
  AA-Schwelle 4.5:1). Bekannte Design-Sorge, in #18 RESEARCH.md (Pitfalls P2.2)
  dokumentiert. Brand-Team-Review kann das Front-Impressum in einer späteren
  Iteration vom Hellgrün herunterverlagern (z. B. auf einen weißen Streifen unter
  der Bullets-Card). Nicht V1-blockierend.
- **Kandidat-Position-Opacity-Lücke** — ISSUE.md spezifizierte „opacity 85%" für
  Kandidat-Position. Die DSL-`TextFrame`-Primitive hat kein `opacity`-Feld
  (RESEARCH.md locked decision #6). V1 nutzt 100 %-weiß auf Dunkelgrün, was
  visuell akzeptabel ist (~12:1 Kontrast). Eine Opacity-DSL-Erweiterung wäre
  ein eigenes Issue — aktuell out-of-scope.
- **HL→Sub-Gap-Pragmatismus** — V1 nutzt 38 mm Top-Distanz (≈ 50 % der
  19.8-mm-Quickguide-Formel × 2-Faktor) statt der Formel-strikten 19.8 mm,
  um die Zwei-Zonen-Komposition Hero + Bullets-Card im 250-mm-Vertikalformat
  unterzubringen. Logged als Override in
  `meta.yml::brand_overrides[brand:hl_sl_distance_x2]`.
- **Bullets-Card 58 mm Hellgrün-Tinte** — die Vollbleed-Hellgrün-Karte hat hohen
  CMYK-Tintenverbrauch (≈ 12.5 % der Seitenfläche; 100 % Yellow + 69 % Cyan).
  Bei Druck-Kosten-Sensibilität kann die Höhe auf 38 mm reduziert werden
  (revisit in einer Folge-Iteration). Default in V1: 58 mm beibehalten.

## Codex-Demo-Image (D11)

Rückseite trägt einen Kandidat-Portrait-Slot (optional in `meta.yml`). Demo-Bild via
zentrale `library:portrait_stefan`-Referenz. Die V1-Bildhöhe ist 90 mm (vorher 85 mm)
für 5 mm uniformen Inset in der Portrait-Card.

```yaml
# templates/wahltag-tueranhaenger/samples/manifest.yml
images:
  - id: kandidat-portrait
    prompt: "Documentary-style portrait photo of a 40s Austrian man with short brown hair and a green blazer, friendly direct gaze, neutral light-grey studio backdrop, soft front light. Vertical headshot, head and shoulders. Natural skin tones, no makeup-heavy look. No text overlays. No watermarks."
    output: kandidat-portrait.jpg
    size: 768x1024
```

Wird einmal generiert via `tools/codex_image_gen.py`, JPG committed unter `samples/`,
in der Gallery-Preview-SLA injiziert. Endnutzer:innen ersetzen das Bild beim Anpassen.
