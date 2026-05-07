# Spec: Themen-Plakat A3 quer

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
Veranstaltung einladen oder zum Wahltag aufrufen). Das Plakat hängt im
Gemeindeamts-Aushang, in Lokalen und auf Infotafeln. Lese-Distanz **50 cm – 1.5 m**
(klassisches A3-Plakat-Aushang-Distanz).

Die **Layout-Philosophie** ist `These → Belege → Quelle`: Eine
Hauptthese spannt oben über die volle Breite; darunter argumentieren drei Belege in
einer 3-Spalten-Grid; eine Quelle unten zitiert die Faktenbasis. Whitespace-betont, klar
strukturiert, **Argumentation vor Aufruf**. Nicht Wahlkampf-spezifisch — dauerhaft
einsetzbar zwischen Wahlen.

## Layout — Vorderseite (Page 1, einzige Seite)

```text
   <----------------------420mm---------------------->
  +---------------------------------------------------+   ↑
  | L                                                 |   |  ← 12 mm top
  |                                                   |   |
  | H1 — Klimaschutz ist Wirtschaftspolitik.          |   |
  |   (Hauptthese, span volle Breite)                 |   |
  |                                                   |   |
  | (Sub-Headline, optional)                          |   |
  |                                                   |   |
  | +-----------+   +-----------+   +-----------+     |   |
  | |E1 Hd      |   |E2 Hd      |   |E3 Hd      |     | 297
  | |           |   |           |   |           |     | mm
  | |E1 Body    |   |E2 Body    |   |E3 Body    |     |   |
  | | (4-5 Z)   |   | (4-5 Z)   |   | (4-5 Z)   |     |   |
  | |           |   |           |   |           |     |   |
  | +-----------+   +-----------+   +-----------+     |   |
  |                                                   |   |
  |                                                   |   |
  |  Q (Quelle: Statistik Austria, …)             I   |   |
  +---------------------------------------------------+   ↓

Legende:
  L  = Logo Grüne (oben links)
  H1 = Headline-These (Vollkorn Black Italic, dunkelgrün)
  E1/E2/E3 = drei Belege (3-Spalten-Grid)
  Q  = Quelle/Source (kleinere Schrift, links unten)
  I  = Impressum (klein, rechts unten)
```

## Constraints

- **Coordinate-Origin:** Trim-Top-Left (0, 0). Trim 420 × 297 mm. Bleed 3 mm allseitig.
- **Margin:** 15 mm seitlich, 12 mm oben/unten. Inhalts-Bereich: 390 × 273 mm.
- **3-Column-Grid:** Gutter **8 mm** (P-A3-1: nicht Scribus-Default 11 pt — explizit setzen).
  Spaltenbreite = (420 − 30 − 16) / 3 = **124.67 mm** pro Spalte.
- **Headline ≥ 36 pt** (A3-Distanz-Mindest aus SCHEMA.md §8); empfohlen 60 pt.
- **Body ≥ 11 pt** (A3-Distanz-Body); empfohlen 13 pt.
- **Min-DPI 300** für eingebettete Bilder.
- **Hintergrund:** Weiß. Akzente: Dunkelgrün (Headline + Hairlines), Magenta (sparsam,
  als Highlight in Quelle-Kasten oder Stoerer falls verwendet). **Kein Vollbild-Hintergrund**
  — Whitespace ist die Argument-Trägerin.

## Slot-Tabelle

| anname                        | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                                 |
|-------------------------------|-----------|------|------|------|------|-----------|------------------------------------|---------------------------------------------------------|
| Logo Grüne (top-left)         | ImageFrame|  15  |  10  |  60  |  18  | —         | shared/logos/gruene-cmyk.png       | (verwende shared/logos/gruene-cmyk.png)                 |
| Headline These                | TextFrame |  15  |  40  | 390  |  50  | Dunkelgrün| themen-plakat/headline             | Klimaschutz ist Wirtschaftspolitik.                     |
| Sub-Headline (optional)       | TextFrame |  15  |  92  | 390  |  16  | Dunkelgrün| themen-plakat/sub                  | Drei Belege aus Niederösterreich, Mai 2026.             |
| Beleg 1 — Headline            | TextFrame |  15  | 130  | 124  |  20  | Dunkelgrün| themen-plakat/beleg-headline       | 12 700 grüne Jobs                                       |
| Beleg 1 — Body                | TextFrame |  15  | 152  | 124  |  90  | Black     | themen-plakat/beleg-body           | In Niederösterreich arbeiten 12 700 Menschen direkt in der Erneuerbaren-Energie-Branche — mehr als in der konventionellen Energiewirtschaft. |
| Beleg 2 — Headline            | TextFrame | 147  | 130  | 124  |  20  | Dunkelgrün| themen-plakat/beleg-headline       | 1.2 Mrd. € Umsatz                                       |
| Beleg 2 — Body                | TextFrame | 147  | 152  | 124  |  90  | Black     | themen-plakat/beleg-body           | Die Solar- und Wind-Branche macht in NÖ 1.2 Mrd. € Jahresumsatz aus — Tendenz steigend. Jeder Euro fließt in die regionale Wertschöpfung zurück. |
| Beleg 3 — Headline            | TextFrame | 281  | 130  | 124  |  20  | Dunkelgrün| themen-plakat/beleg-headline       | 36 % weniger CO₂                                        |
| Beleg 3 — Body                | TextFrame | 281  | 152  | 124  |  90  | Black     | themen-plakat/beleg-body           | Seit 2010 hat NÖ den industriellen CO₂-Ausstoß um 36 % reduziert — bei gleichzeitig wachsender Industrie-Produktion. |
| Quelle/Source                 | TextFrame |  15  | 270  | 280  |  10  | Dunkelgrün| themen-plakat/source               | Quelle: Statistik Austria, AEA-Energiebilanz NÖ 2024.   |
| Impressum                     | TextFrame | 305  | 270  | 100  |  10  | Black     | Impressum                          | Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten. |

```yaml
slots:
  - anname: "Logo Grüne (top-left)"
    type: ImageFrame
    x_mm: 15
    y_mm: 10
    w_mm: 60
    h_mm: 18
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "Headline These"
    type: TextFrame
    x_mm: 15
    y_mm: 40
    w_mm: 390
    h_mm: 50
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/headline"
    example: "Klimaschutz ist Wirtschaftspolitik."
  - anname: "Sub-Headline"
    type: TextFrame
    x_mm: 15
    y_mm: 92
    w_mm: 390
    h_mm: 16
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/sub"
    example: "Drei Belege aus Niederösterreich, Mai 2026."
  - anname: "Beleg 1 — Headline"
    type: TextFrame
    x_mm: 15
    y_mm: 130
    w_mm: 124
    h_mm: 20
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/beleg-headline"
    example: "12 700 grüne Jobs"
  - anname: "Beleg 1 — Body"
    type: TextFrame
    x_mm: 15
    y_mm: 152
    w_mm: 124
    h_mm: 90
    fcolor: "Black"
    style_ref: "themen-plakat/beleg-body"
    example: "In Niederösterreich arbeiten 12 700 Menschen direkt in der Erneuerbaren-Energie-Branche — mehr als in der konventionellen Energiewirtschaft."
  - anname: "Beleg 2 — Headline"
    type: TextFrame
    x_mm: 147
    y_mm: 130
    w_mm: 124
    h_mm: 20
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/beleg-headline"
    example: "1.2 Mrd. € Umsatz"
  - anname: "Beleg 2 — Body"
    type: TextFrame
    x_mm: 147
    y_mm: 152
    w_mm: 124
    h_mm: 90
    fcolor: "Black"
    style_ref: "themen-plakat/beleg-body"
    example: "Die Solar- und Wind-Branche macht in NÖ 1.2 Mrd. € Jahresumsatz aus — Tendenz steigend. Jeder Euro fließt in die regionale Wertschöpfung zurück."
  - anname: "Beleg 3 — Headline"
    type: TextFrame
    x_mm: 281
    y_mm: 130
    w_mm: 124
    h_mm: 20
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/beleg-headline"
    example: "36 % weniger CO₂"
  - anname: "Beleg 3 — Body"
    type: TextFrame
    x_mm: 281
    y_mm: 152
    w_mm: 124
    h_mm: 90
    fcolor: "Black"
    style_ref: "themen-plakat/beleg-body"
    example: "Seit 2010 hat NÖ den industriellen CO₂-Ausstoß um 36 % reduziert — bei gleichzeitig wachsender Industrie-Produktion."
  - anname: "Quelle"
    type: TextFrame
    x_mm: 15
    y_mm: 270
    w_mm: 280
    h_mm: 10
    fcolor: "Dunkelgrün"
    style_ref: "themen-plakat/source"
    example: "Quelle: Statistik Austria, AEA-Energiebilanz NÖ 2024."
  - anname: "Impressum"
    type: TextFrame
    x_mm: 305
    y_mm: 270
    w_mm: 100
    h_mm: 10
    fcolor: "Black"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
```

## EPS / Image-Embedding-Strategie

Keine. Kein Wahlkreuz. Themen-Plakat ist Argument, nicht Wahlaufruf.

## Background-Color Contract für Wahlkreuz

Nicht zutreffend (kein Wahlkreuz).

## Falz / Stanze

Keine.

## Brand-Hierarchy Contract

| Schicht | Größe | Font | Farbe |
|---|---|---|---|
| Headline (These) | **60 pt** | Vollkorn Black Italic | Dunkelgrün |
| Sub-Headline | 18 pt | Gotham Narrow Book | Dunkelgrün |
| Beleg-Headline | **24 pt** | Gotham Narrow Bold | Dunkelgrün |
| Beleg-Body | 13 pt | Gotham Narrow Book | Black |
| Quelle | 10 pt | Gotham Narrow Book Italic | Dunkelgrün |
| Impressum | 7 pt | Gotham Narrow Book | Black |

**Begründung der Schriftgröße-Wahl:**

- 60 pt These ist 24 pt über dem A3-Mindest (36 pt). Bewusst groß als visueller Anker.
  Vergleich: Postkarte-Headline ist 27 pt auf 105 mm Breite (Verhältnis ~0.26 pt/mm),
  A3-These ist 60 pt auf 390 mm (~0.15 pt/mm); A3 ist relativ zur Fläche **kleiner** —
  Whitespace trägt die Botschaft, Headline ist konzentriert.
- 24 pt Beleg-Headline ist 11 pt unter These — eindeutige Hierarchie.
- 13 pt Body ist 2 pt über dem Mindest (11 pt). Lese-Distanz 50 cm rechtfertigt etwas
  größeren Body als bei Zeitung (11 pt).
- Body-Spaltenbreite 124 mm × 13 pt entspricht ~60 Zeichen/Zeile — Soll-Bereich für
  Lesbarkeit (45–75 Zeichen).

**Whitespace-Rhythmus:**

- 12 mm Top-Margin → 40 mm Headline-Top-Y (28 mm Logo+Spacing).
- Headline-Block 50 mm hoch, 8 mm Spacing → Sub bei 92 mm.
- Sub-Block 16 mm + 22 mm Spacing → Beleg-Headlines bei 130 mm.
- Beleg-Headlines 20 mm + 2 mm Spacing → Beleg-Body bei 152 mm.
- Beleg-Body 90 mm hoch → Ende 242 mm; 28 mm Whitespace nach unten → Quelle/Impressum bei 270 mm.
- 28 mm Whitespace zwischen Beleg-Body und Quelle ist die "Atempause" der Argumentation
  — visuell entscheidend für die Kontemplation der Belege.

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: []
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Bilderdruck matt 170 g/m² oder Plakatpapier blueback 135 g/m²"
  print_method: "Offset (≥ 100 Stück) oder Großformat-Digital (< 100)"
  cmyk_only: true
```

## Mediengesetz §24

Impressum-Slot vorhanden, Default-Text aus
`tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`. Endnutzer:innen passen Druckerei
und Auflage an.

## Style-Hygiene

`style_ref` referenziert Template-lokale Styles (Prefix `themen-plakat/`), die in
`build.py` als `ParaStyle` deklariert und in `meta.yml.ci_overrides.non_ci_styles`
dokumentiert werden:

- `themen-plakat/headline` (Vollkorn Black Italic 60 pt)
- `themen-plakat/sub` (Gotham Narrow Book 18 pt)
- `themen-plakat/beleg-headline` (Gotham Narrow Bold 24 pt)
- `themen-plakat/beleg-body` (Gotham Narrow Book 13 pt linesp 16)
- `themen-plakat/source` (Gotham Narrow Book Italic 10 pt)

`Impressum` ist ein bestehender Style aus den Postkarte/Plakat-Konventionen — wieder­
verwenden statt neu deklarieren.
