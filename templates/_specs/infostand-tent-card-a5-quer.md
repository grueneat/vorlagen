# Spec: Infostand-Tent-Card A5 quer

```yaml
id: infostand-tent-card-a5-quer
title: Infostand-Tent-Card A5 quer
format: A4 quer (297x210) gefalzt zu A5-Tent
trim_mm: [297, 210]
bleed_mm: 3
pages: 1
fold_type: tent
fold_positions_mm: [105]   # horizontal fold at y=105 mm (mittig)
cut_type: none
audience: [bezirksgruppe, ortsgruppe, infostand-helfer]
```

## Audience und Layout-Philosophie

**Infostand-Tisch-Aufsteller** (Tent-Card / Table-Tent): Bezirks-/Ortsgruppen stellen die
Karte am Infostand, am Pfarrkaffee-Tisch oder bei Veranstaltungen auf. Selbsttragend
durch eine horizontale Falzung in der Mitte: das A4-quer-Blatt wird zu einem A5-quer-Tent
gefalzt, das aus beiden Richtungen sichtbar ist.

Lese-Distanz **Tisch-Augen-Distanz** ~50–80 cm.

**Layout-Philosophie:** 3D-doppelseitig sichtbar. Beide Panele (Panel A oben, Panel B unten
des flach liegenden A4) müssen so layoutet sein, dass nach dem Falzen **jede Seite
unabhängig richtig liest** — Headline oben, Body darunter. Beim Falzen wird Panel B
gespiegelt nach unten — bedeutet, der Inhalt von Panel B muss **kopfüber** layoutet sein,
damit er nach dem Falzen richtig steht. Das Build-Skript handhabt diese Rotation
automatisch via `TableTentFold`-Block.

## Layout — Flach (Page 1, vor dem Falzen)

```text
   <----------------297mm--------------->
  +---------------------------------------+   ↑
  |                                       |   |
  |    L              H1 — Klimaschutz    |   |  Panel A
  |                   (Vollkorn 36 pt)    |   |  (105 mm hoch)
  |                                       |   |
  |    Body (28 pt Tisch-Distanz)         |   |
  |    • Punkt 1                          |   |
  |    • Punkt 2                          |   |
  |    • Punkt 3                          |   |
  +- - - - - - - - - - - - - - - - - - - -+   |
  |          ← FOLD-LINE y=105 mm →       |   ↓ 210mm
  +- - - - - - - - - - - - - - - - - - - -+   ↑
  |    (wird beim Falzen gespiegelt)      |   |
  |                                       |   |
  |    Body (28 pt) — ENGLISCH/SECOND     |   |
  |                                       |   |  Panel B
  |    H1 — Climate is Economy            |   |  (105 mm hoch,
  |    (Vollkorn 36 pt)                   |   |   wird kopfüber
  |                                       |   |   gerendert!)
  |    L  QR                              |   |
  |                                       |   ↓
  +---------------------------------------+

Legende:
  H1 = Headline (Vollkorn Black Italic 36 pt)
  Body = Bullet-Liste (Gotham Narrow Book 14 pt)
  L  = Logo Grüne (CMYK)
  QR = QR-Code (Event-Anmeldung optional)
  FOLD-LINE = horizontaler Falz auf Falz-Layer mit Spot-Color
```

## Layout — 3D-Aufsteller-Schema (nach dem Falzen)

```text
       Vorderansicht           Seitenansicht
          (Panel A)
       +-----------+           +-----+
       |           |           | A   |
       |  H1       |           | |   |  Tisch-
       |  Body     |           | | B |  Kontaktzone
       |           |           | |   |  (3 mm jeder Seite)
       +-----------+           +=====+
                                ↓ Tisch
       Rückansicht
          (Panel B,
           gerade gestellt)
       +-----------+
       |           |
       |  H1       |
       |  Body     |
       |           |
       +-----------+
```

Beide Panele lesen unabhängig. Panel A trifft Personen, die von einer Tischseite
kommen; Panel B die andere. Inhalts-Strategie: dieselbe Botschaft in zwei Sprachen
(DE/EN), oder zwei unterschiedliche Themen — Spec-Default ist „selbe Botschaft DE/EN"
für maximalen Reach.

## Constraints

- **Coordinate-Origin:** Trim-Top-Left (0, 0). Trim 297 × 210 mm. **Bleed 3 mm.**
- **Falz:** horizontal bei **y = 105 mm** (mittig, halbiert die 210 mm Höhe).
- **Bottom-3-mm-Tisch-Kontaktzone** (P-PRINT-4): die unterste 3 mm jedes Panels
  (y=102–105 mm in Panel A; y=207–210 mm in Panel B) MUSS frei von Text und kritischen
  Bild-Elementen sein. Diese Zone berührt den Tisch und sammelt Schmutz/Wasser.
- **Headline ≥ 28 pt** (SCHEMA.md A5-Tent-Mindest für Tisch-Distanz). Empfohlen 36 pt.
- **Body ≥ 14 pt** (Tisch-Distanz). Empfohlen 14 pt.
- **Margin:** 12 mm allseitig + 3 mm Tisch-Kontaktzone unten.
- **Panel-Inhalts-Bereich:** 297−24 = 273 mm × (105−12−3) = 90 mm pro Panel.
- **Background:** weiß für Lesbarkeit; Akzente in Dunkelgrün (Headline + Bullet-Punkte).

## Slot-Tabelle — Panel A (y=0–105 mm)

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                              |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|------------------------------------------------------|
| Logo Grüne (cmyk, panel A)   | ImageFrame       |  12  |  10  |  45  |  14  | —         | shared/logos/gruene-cmyk.png       | (verwende shared/logos/gruene-cmyk.png)              |
| Headline Panel A             | TextFrame        |  62  |  10  | 223  |  30  | Dunkelgrün| tent/headline                      | Klimaschutz konkret.                                 |
| Body Panel A                 | TextFrame        |  62  |  44  | 223  |  56  | Black     | tent/body                          | • Erneuerbare Energie ausbauen\n• Öffis verdoppeln\n• Wärmepumpe statt Gas |
| Hintergrund-Mitmachen        | ImageFrame       |  12  |  44  |  44  |  33  | —         | samples/hintergrund-mitmachen.jpg  | Demo Hintergrund (synthetic, watermarked) — optional |
| QR-Code (mitmachen, panel A) | ImageFrame       |  12  |  80  |  17  |  17  | —         | samples/qr-mitmachen.png           | Demo: https://noe.gruene.at/mitmachen/ — endusers replace |
| Impressum (Tent)             | TextFrame        |  35  |  96  | 257  |   4  | Black     | Impressum                          | Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten. |
| Falzlinie (horizontal)       | Block:TableTentFold|   0|  105| 297  |   0  | Falz      | —                                  | (FoldLine auf Falz-Layer y=105)                      |

## Slot-Tabelle — Panel B (y=105–210 mm; **kopfüber gerendert**)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                           |
|------------------------------|-----------|------|------|------|------|-----------|---------------------------------|---------------------------------------------------|
| Logo Grüne (cmyk, panel B)   | ImageFrame|  240 | 196  |  45  |  14  | —         | shared/logos/gruene-cmyk.png    | (verwende shared/logos/gruene-cmyk.png)           |
| Headline Panel B             | TextFrame |  12  | 170  | 223  |  30  | Dunkelgrün| tent/headline                   | Climate. Concrete.                                |
| Body Panel B                 | TextFrame |  12  | 113  | 223  |  56  | Black     | tent/body                       | • Renewables: scale up\n• Public transport: double\n• Heat pump, not gas |

> **Note (Issue #11, 2026-05-08):** The previous Panel-B `QR-Code (optional)` slot was 14×14 mm, which violates D1's 0.5 mm/module minimum (33-module QR encoding `noe.gruene.at/mitmachen/` would yield 0.42 mm/module). The QR slot has been **enlarged to 17×17 mm** and **moved to Panel A** (Mitmachen-Seite) — yielding 17/33 ≈ 0.515 mm/module, just above the threshold.

> **Hinweis zur Panel-B-Rotation:** Sowohl die Markdown-Tabelle als auch der eingebettete
> YAML-Block enthalten die **finalen Frame-Koordinaten** wie sie im SLA stehen werden —
> nach Anwendung der 180°-Rotation, die `TableTentFold`/`build.py` für Panel B emittiert.
> Pivot der Rotation ist die Mitte von Panel B = (148.5, 157.5) mm im flachen A4-quer-Layout.
> Bei einer Person, die das gefalzte Tent von der Rückseite betrachtet, lesen die Frames
> dann korrekt aufrecht. Tabelle + YAML entsprechen 1:1 dem, was `tools/spec_check.py`
> im SLA als Frame-Position findet.

```yaml
slots:
  - anname: "Logo Grüne (cmyk, panel A)"
    type: ImageFrame
    x_mm: 12
    y_mm: 10
    w_mm: 45
    h_mm: 14
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "Headline Panel A"
    type: TextFrame
    x_mm: 62
    y_mm: 10
    w_mm: 223
    h_mm: 30
    fcolor: "Dunkelgrün"
    style_ref: "tent/headline"
    example: "Klimaschutz konkret."
  - anname: "Body Panel A"
    type: TextFrame
    x_mm: 62
    y_mm: 44
    w_mm: 223
    h_mm: 56
    fcolor: "Black"
    style_ref: "tent/body"
    example: "• Erneuerbare Energie ausbauen\n• Öffis verdoppeln\n• Wärmepumpe statt Gas"
  - anname: "Hintergrund-Mitmachen"
    type: ImageFrame
    x_mm: 12
    y_mm: 44
    w_mm: 44
    h_mm: 33
    fcolor: ""
    style_ref: "samples/hintergrund-mitmachen.jpg"
    example: "Demo Hintergrund (synthetic, watermarked) — optional"
  - anname: "QR-Code (mitmachen, panel A)"
    type: ImageFrame
    x_mm: 12
    y_mm: 80
    w_mm: 17
    h_mm: 17
    fcolor: ""
    style_ref: "samples/qr-mitmachen.png"
    example: "Demo: https://noe.gruene.at/mitmachen/ — endusers replace. Enlarged 2026-05-08 per Issue #11 (D1 module-size: 17/33 ≈ 0.515 mm/module)."
  - anname: "Falzlinie"
    type: "Block:TableTentFold"
    x_mm: 0
    y_mm: 105
    w_mm: 297
    h_mm: 0
    fcolor: "Falz"
    style_ref: ""
    example: "FoldLine auf Falz-Layer y=105"
  - anname: "Logo Grüne (cmyk, panel B)"
    type: ImageFrame
    x_mm: 240
    y_mm: 196
    w_mm: 45
    h_mm: 14
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "Headline Panel B"
    type: TextFrame
    x_mm: 12
    y_mm: 170
    w_mm: 223
    h_mm: 30
    fcolor: "Dunkelgrün"
    style_ref: "tent/headline"
    example: "Climate. Concrete."
  - anname: "Body Panel B"
    type: TextFrame
    x_mm: 12
    y_mm: 113
    w_mm: 223
    h_mm: 56
    fcolor: "Black"
    style_ref: "tent/body"
    example: "• Renewables: scale up\n• Public transport: double\n• Heat pump, not gas"
  - anname: "Impressum (Tent)"
    type: TextFrame
    x_mm: 35
    y_mm: 96
    w_mm: 257
    h_mm: 4
    fcolor: "Black"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
```

## EPS / Image-Embedding-Strategie

Kein Wahlkreuz im Default-Layout. Optional kann eine Bezirksgruppe die Tent-Card für
Wahlkampf-Phasen mit Wahlkreuz erweitern; das wäre eine Spec-Variante (D3:
Spec-Update + Re-Review erforderlich).

## Background-Color Contract für Wahlkreuz

Nicht zutreffend (Default-Layout ohne Wahlkreuz). Falls eine Variante mit Wahlkreuz
gebaut wird, gilt SCHEMA.md §6 (D12-Pflicht).

## Falz / Stanze

**Falz:** ja, horizontal bei y=105 mm. **Stanze:** keine.

### Falz-Layer + Spot-Color

```yaml
layer_falz:
  name: "Falz"
  printable: false       # nicht im Druck
  flow: false
  exportable: true       # Druckerei sieht den Pfad

color_falz:
  name: "Falz"
  cmyk: [100, 0, 0, 0]
  spot: true
  document_local: true   # NICHT in shared/ci.yml
```

### Layer-Stack (bottom → top)

1. `Hintergrund` (kein Vollbild-Background nötig — weißer Default-Hintergrund)
2. `Bilder` (Logos, optional QR)
3. `Text` (Headlines + Body)
4. `Falz` (gestrichelte horizontale Linie y=105)

## Brand-Hierarchy Contract

| Schicht | Größe | Font | Farbe |
|---|---|---|---|
| Headline (Panel A & B) | **36 pt** | Vollkorn Black Italic | Dunkelgrün |
| Body (Bullet-Liste) | 14 pt | Gotham Narrow Book | Black |
| Impressum | 5 pt | Gotham Narrow Book | Black |

**Begründung:**

- 36 pt Headline ist 8 pt über dem Tent-Mindest (28 pt). Bei 80 cm Tisch-Distanz und
  20-Grad-Sehwinkel braucht der Anker visuelle Wucht — 36 pt liefert sie ohne den
  schmalen 90 mm Höhen-Bereich pro Panel zu sprengen.
- 14 pt Body × 223 mm Zeilenbreite → ~110 Zeichen/Zeile, hart am Lesbarkeits-Limit.
  Bullets statt Fließtext halten die Zeilen kurz.
- Impressum 5 pt knapp über der Falz-Linie auf Panel A (klein, aber pflichtig).

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: [105]
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Karton 250–300 g/m² (Steifigkeit für Frei-Stand)"
  print_method: "Digital oder Offset (≥ 100); Falz-Linie maschinell perforiert ODER
                 manuelle Falz mit Falzbein"
  cmyk_only: true
```

**Druckerei-Hinweis:** bei 250–300 g/m² ist eine maschinelle Perforation entlang der
Falz-Linie nicht zwingend; Endnutzer:innen können die Karte mit einem Falzbein
manuell falten. Bei 350+ g/m² Karton ist Perforation empfohlen.

## Mediengesetz §24

Impressum-Slot vorhanden auf Panel A (knapp vor der Falz-Linie). Default-Text aus
`tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`.

## Style-Hygiene

`style_ref` referenziert Template-lokale Styles in `meta.yml.ci_overrides.non_ci_styles`:

- `tent/headline` (Vollkorn Black Italic 36 pt Dunkelgrün)
- `tent/body` (Gotham Narrow Book 14 pt linesp 18 Black)

`Impressum` ist bestehender Style (Postkarte-Konvention).

## Codex-Demo-Image (D11)

Optional — die Default-Variante ist Text+Bullet-only. Eine Variante mit Hero-Bild
(z.B. „Solar-Anlage am Gemeindeamt") könnte ein Demo-Bild via Codex bekommen, aber das
ist Spec-Erweiterung (D3).
