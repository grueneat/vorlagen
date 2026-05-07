# Spec: Wahltag-Türanhänger

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
Wähle Grün."). Rückseite kann Kandidaten-Foto + Kontaktdaten tragen.

**Layout-Philosophie:** Schmal-vertikal mit Stanzform-Constraint. Die Türklinken-Stanze
am oberen Drittel ist nicht-verhandelbar (das ist *was* den Türanhänger zum Türanhänger
macht). Inhalts-Zonen sind: Brand-Bar oben (über dem Loch), Hero-Zone (Wahlkreuz +
Headline) Mitte, CTA-Zone unten.

## Layout — Vorderseite (Page 1)

```text
   <--105mm-->
  +-----------+   ↑
  | L         |   |  ← 5 mm top
  |           |   |
  |   ┌-----┐ |   |  Brand-Bar:
  |   |     | |   |  L = Logo Grüne (weiss)
  |   |  Ø  | |   |
  |   |     | | 25mm Lochrand
  |   └-----┘ |   |
  +-----------+   |
  |           |   |  Hole-Zone (35 mm Ø rund)
  |           |   |  ← Stanzkontur
  +-----------+   |
  |           |   |
  |  ┌─────┐  |   |
  |  │ WK  │  |   |
  |  │  on │  |   |  Hero-Zone:
  |  │ Hell│  | 250  WK = Wahlkreuz auf
  |  │ grün│  | mm    Hellgrün-Polygon (D12)
  |  └─────┘  |   |
  |           |   |
  | H1: Heute |   |
  |   ist     |   |
  |  Wahltag. |   |
  |           |   |
  | • Punkt 1 |   |
  | • Punkt 2 |   |  CTA-Zone:
  | • Punkt 3 |   |
  |           |   |
  | url        |   |
  |           |   |
  | I (Imp.)  |   |
  +-----------+   ↓

Stanzkontur (S):
  - Außen-Rechteck: (0,0)→(105,250) mm
  - Loch-Kreis: Mittelpunkt (52.5, 42.5), Radius 17.5 mm
                (= 35 mm Ø, 25 mm vom Top + 17.5 mm Radius)
```

## Layout — Rückseite (Page 2)

```text
   <--105mm-->
  +-----------+   ↑
  | L         |   |
  |           |   |
  |  Lochzone |   |  Loch dieselben
  |    (frei) |   |  Koordinaten
  +-----------+   |
  |           |   |
  | ┌───────┐ |   |  Optional:
  | │       │ |   |  Kandidaten-
  | │ FOTO  │ | 250  Portrait
  | │       │ | mm   (Codex demo
  | │       │ |   |   image)
  | └───────┘ |   |
  |           |   |
  | NAME      |   |
  | Position  |   |
  |           |   |
  | URL/QR    |   |
  | Kontakt   |   |
  |           |   |
  | I         |   |
  +-----------+   ↓

Legende:
  L  = Logo (auch hier, über dem Loch)
  FOTO = Kandidaten-Portrait (optional, D11 demo)
  NAME = Kandidaten-Name + Funktion
  URL/QR = Anmelde-/Info-Link
  I    = Impressum
```

## Constraints

- **Coordinate-Origin:** Trim-Top-Left (0, 0).
- **Trim:** 105 × 250 mm. **Bleed 2 mm** allseitig (Stanzungen brauchen knapperen Bleed
  als 3 mm Standard — siehe SCHEMA.md §9).
- **Loch:** rund, **Ø 35 mm**, Mittelpunkt **25 mm vom Top + 17.5 mm Radius = 42.5 mm**
  vertikal, horizontal zentriert (52.5 mm).
- **Safety-Zone:** 2 mm Mindestabstand zwischen Stanzkontur (Loch + Trim-Außenkante) und
  erstem Inhalts-Pixel.
- **Brand-Bar oben:** y=5 mm bis y=20 mm (15 mm hoch, über dem Loch).
- **Hole-Zone:** y=20 mm bis y=65 mm. **Keine Inhalte** in dieser Zone.
- **Hero-Zone:** y=65 mm bis y=180 mm (115 mm hoch). Wahlkreuz + Headline.
- **CTA-Zone:** y=180 mm bis y=240 mm (60 mm hoch). Bullets + URL.
- **Impressum-Strip:** y=240 mm bis y=248 mm (8 mm hoch).
- **Headline ≥ 22 pt** (SCHEMA.md A6-Mindest). Empfohlen 28 pt.
- **Body ≥ 9 pt**. Empfohlen 11 pt.

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

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                   |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|-------------------------------------------|
| Logo Grüne (weiss, top)      | ImageFrame       |  10  |   8  |  35  |  10  | —         | shared/logos/gruene-weiss.png      | (verwende shared/logos/gruene-weiss.png)  |
| Wahlkreuz (Hero)             | Block:WahlkreuzSymbol| 27.5| 70 |  50  |  50  | —         | —                                  | (Wahlkreuz auf Hellgrün-Polygon)          |
| Headline-Wahltag             | TextFrame        |  10  | 130  |  85  |  20  | Dunkelgrün| tueranhaenger/headline             | Heute ist Wahltag.                        |
| Sub-Headline                 | TextFrame        |  10  | 152  |  85  |  10  | Dunkelgrün| tueranhaenger/sub                  | Wähle Grün.                               |
| Bullet-Liste                 | TextFrame        |  10  | 175  |  85  |  60  | Black     | tueranhaenger/body                 | • Klima · Soziales · Bildung\n• Vor Ort · Ehrlich · Faktenbasiert\n• Mehr auf gruene-noe.at |
| Impressum                    | TextFrame        |  10  | 240  |  85  |   6  | Black     | Impressum                          | Medieninhaber: Die Grünen NÖ, …           |
| Stanzkontur (Außen + Loch)   | Block:DoorHangerCutout|  0|   0 | 105  | 250  | Stanzkontur|—                                  | (Außen-Rechteck + 35 mm Loch)             |

## Slot-Tabelle — Rückseite (Page 2)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                              |
|------------------------------|-----------|------|------|------|------|-----------|---------------------------------|------------------------------------------------------|
| Logo Grüne (cmyk, back)      | ImageFrame|  10  |   8  |  35  |  10  | —         | shared/logos/gruene-cmyk.png    | (verwende shared/logos/gruene-cmyk.png)              |
| Kandidat-Portrait (optional) | ImageFrame|  20  |  75  |  65  |  85  | —         | optional / Codex demo (D11)     | (Codex DALL·E generiert; siehe samples/manifest.yml) |
| Kandidat-Name                | TextFrame |  10  | 168  |  85  |  10  | Dunkelgrün| tueranhaenger/cand-name         | Maria Beispiel                                       |
| Kandidat-Position            | TextFrame |  10  | 178  |  85  |   8  | Black     | tueranhaenger/cand-pos          | Bürgermeisterkandidatin Mödling                      |
| Kontakt-URL                  | TextFrame |  10  | 200  |  85  |   8  | Dunkelgrün| tueranhaenger/url               | gruene-moedling.at                                   |
| Kontakt-Info                 | TextFrame |  10  | 210  |  85  |  20  | Black     | tueranhaenger/body              | maria.beispiel@gruene-moedling.at\n+43 660 1234567   |
| Impressum (back)             | TextFrame |  10  | 240  |  85  |   6  | Black     | Impressum                       | (gleicher Text wie Page 1)                           |

```yaml
slots:
  - anname: "Logo Grüne (weiss, top)"
    type: ImageFrame
    x_mm: 10
    y_mm: 8
    w_mm: 35
    h_mm: 10
    fcolor: ""
    style_ref: "shared/logos/gruene-weiss.png"
    example: ""
  - anname: "Wahlkreuz"
    type: "Block:WahlkreuzSymbol"
    x_mm: 27.5
    y_mm: 70
    w_mm: 50
    h_mm: 50
    fcolor: ""
    style_ref: ""
    example: "Wahlkreuz auf Hellgrün-Polygon, padding 4mm"
  - anname: "Headline-Wahltag"
    type: TextFrame
    x_mm: 10
    y_mm: 130
    w_mm: 85
    h_mm: 20
    fcolor: "Dunkelgrün"
    style_ref: "tueranhaenger/headline"
    example: "Heute ist Wahltag."
  - anname: "Sub-Headline"
    type: TextFrame
    x_mm: 10
    y_mm: 152
    w_mm: 85
    h_mm: 10
    fcolor: "Dunkelgrün"
    style_ref: "tueranhaenger/sub"
    example: "Wähle Grün."
  - anname: "Bullet-Liste"
    type: TextFrame
    x_mm: 10
    y_mm: 175
    w_mm: 85
    h_mm: 60
    fcolor: "Black"
    style_ref: "tueranhaenger/body"
    example: "• Klima · Soziales · Bildung\n• Vor Ort · Ehrlich · Faktenbasiert\n• Mehr auf gruene-noe.at"
  - anname: "Impressum"
    type: TextFrame
    x_mm: 10
    y_mm: 240
    w_mm: 85
    h_mm: 6
    fcolor: "Black"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
  - anname: "Stanzkontur"
    type: "Block:DoorHangerCutout"
    x_mm: 0
    y_mm: 0
    w_mm: 105
    h_mm: 250
    fcolor: "Stanzkontur"
    style_ref: ""
    example: "Außen-Rechteck + 35 mm Loch zentriert horizontal, 25 mm vom Top"
  - anname: "Kandidat-Portrait"
    type: ImageFrame
    x_mm: 20
    y_mm: 75
    w_mm: 65
    h_mm: 85
    fcolor: ""
    style_ref: "optional / Codex demo (D11)"
    example: ""
  - anname: "Kandidat-Name"
    type: TextFrame
    x_mm: 10
    y_mm: 168
    w_mm: 85
    h_mm: 10
    fcolor: "Dunkelgrün"
    style_ref: "tueranhaenger/cand-name"
    example: "Maria Beispiel"
  - anname: "Kontakt-Info"
    type: TextFrame
    x_mm: 10
    y_mm: 210
    w_mm: 85
    h_mm: 20
    fcolor: "Black"
    style_ref: "tueranhaenger/body"
    example: "maria.beispiel@gruene-moedling.at\n+43 660 1234567"
```

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

## Falz / Stanze

**Stanze:** ja, siehe Stanzkontur-Sektion oben. **Falz:** keine.

## Brand-Hierarchy Contract

| Schicht | Größe | Font | Farbe |
|---|---|---|---|
| Headline-Wahltag | **28 pt** | Vollkorn Black Italic | Dunkelgrün |
| Sub-Headline | 18 pt | Gotham Narrow Bold | Dunkelgrün |
| Body (Bullet) | 11 pt | Gotham Narrow Book | Black |
| Kandidat-Name | 14 pt | Gotham Narrow Bold | Dunkelgrün |
| Kandidat-Position | 10 pt | Gotham Narrow Book Italic | Black |
| Kontakt-Info | 9 pt | Gotham Narrow Book | Black |
| Impressum | 6 pt | Gotham Narrow Book | Black |

**Begründung:**

- 28 pt Headline ist 6 pt über dem A6-Mindest. „Heute ist Wahltag." ist der visuelle
  Anker — kurz und groß.
- Bullet-Body 11 pt × 85 mm Zeilenbreite → ~70 Zeichen/Zeile, gut lesbar.
- Kandidaten-Name 14 pt ist hierarchisch zwischen Sub-Headline (18 pt) und Body (11 pt) —
  klare Person-Identifikation.

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

Impressum-Slot vorhanden (auf beiden Seiten), Default-Text.

## Messaging-Legality (NRWO §53)

> „Heute ist Wahltag. Wähle Grün." — Wahlempfehlung, kein Anweisungstext. ✅

## Style-Hygiene

`style_ref` referenziert Template-lokale Styles in `meta.yml.ci_overrides.non_ci_styles`:

- `tueranhaenger/headline` (Vollkorn Black Italic 28 pt Dunkelgrün)
- `tueranhaenger/sub` (Gotham Narrow Bold 18 pt Dunkelgrün)
- `tueranhaenger/body` (Gotham Narrow Book 11 pt Black)
- `tueranhaenger/cand-name` (Gotham Narrow Bold 14 pt Dunkelgrün)
- `tueranhaenger/cand-pos` (Gotham Narrow Book Italic 10 pt Black)
- `tueranhaenger/url` (Gotham Narrow Bold 11 pt Dunkelgrün)

`Impressum` ist bestehender Style.

## Codex-Demo-Image (D11)

Rückseite trägt einen Kandidat-Portrait-Slot (optional in `meta.yml`). Demo-Bild via
Codex DALL·E:

```yaml
# templates/wahltag-tueranhaenger/samples/manifest.yml
images:
  - id: kandidat-portrait
    prompt: "Documentary-style portrait photo of a 40s Austrian woman with short brown hair and a green blazer, friendly direct gaze, neutral light-grey studio backdrop, soft front light. Vertical headshot, head and shoulders. Natural skin tones, no makeup-heavy look. No text overlays. No watermarks."
    output: kandidat-portrait.jpg
    size: 768x1024
```

Wird einmal generiert via `tools/codex_image_gen.py`, JPG committed unter `samples/`,
in der Gallery-Preview-SLA injiziert. Endnutzer:innen ersetzen das Bild beim Anpassen.
