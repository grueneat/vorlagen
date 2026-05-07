# Retro-Spec: Plakat A1 Hochformat

> **Hinweis:** Retro-Spec für `templates/plakat-a1-hochformat/`, im Spec-Format aus
> `templates/_specs/SCHEMA.md`. Stresst das Spec-Format gegen ein Großformat-Template.

```yaml
id: plakat-a1-hochformat
title: Event-Plakat A1
format: A1 hochformat 1-seitig
trim_mm: [594, 841]
bleed_mm: 3
pages: 1
fold_type: none
fold_positions_mm: []
cut_type: none
audience: [bezirksgruppe, landesgruppe, ortsgruppe]
```

## Audience und Layout-Philosophie

Veranstaltungs-Plakat A1 für Events, Mahnwachen, Stammtische, Kundgebungen. Nutzungsfall:
Schaufenster, Plakatwand, Kundgebungs-Backdrop. Lese-Distanz **2–6 m**. Layout teilt
sich vertikal in zwei Hälften: **oben weiß** mit dem Logo (rechts oben) und Veranstaltungs-
Daten (Datum, Ort, URL); **unten Dunkelgrün-Vollbild** mit der 4-zeiligen Headline in
alternierenden Brand-Farben (Weiß/Gelb). Impressum vertikal am rechten Rand (gedreht 270°).
Die Headline trägt die Hauptbotschaft, die Veranstaltungs-Daten oben sind sekundär.

## Layout — Vorderseite (Page 1, einzige Seite)

```text
   <-----594mm----->
  +-----------------+   ↑
  |          L      |   |  Obere Hälfte:
  |                 |   |  Weißer Hintergrund
  |   DATUM         |   |  L  = Logo Grüne (rechts oben)
  |   ORT           |   |  Veranstaltungs-Daten links
  |   URL           |   |
  |                 |   |
  +=================+   |  ← Trennlinie ~y=414 mm
  |  H1             |   |
  |   H1 H1         |   |  Untere Hälfte:
  |    H1 H1 H1     | 841  Dunkelgrün-Vollbild
  |     H1 H1       |  mm  Headline 4-zeilig
  |      H1 H1 H1   |   |  Wechselfarbe (W/Y/W/Y)
  |       H1        |   |
  |                 |   |
  |                I|   |
  +-----------------+   ↓
                     ↑
                     Impressum (vertikal, rotiert 270°)

Legende:
  H1 = Headline 4-zeilig (Wechselfarbe Weiss/Gelb auf Dunkelgrün)
  L  = Logo Grüne (weiss-cmyk, rechts oben auf Weiß)
  DATUM = Veranstaltung — Datum/Zeit
  ORT   = Veranstaltung — Ort/Adresse
  URL   = Anmelde-URL
  I     = Impressum vertikal am rechten Rand
```

## Slot-Tabelle (Auszug aus build.py + meta.yml)

| anname                                | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref           | example                                            |
|---------------------------------------|-----------|------|------|------|------|-----------|---------------------|----------------------------------------------------|
| Hintergrund-Streifen unten            | Polygon   |   0  | 414  | 594  | 427  | Dunkelgrün| —                   | (Dunkelgrün-Vollbild-Streifen untere Hälfte)       |
| Headline 4-zeilig (Brand-Wechselfarbe)| TextFrame |  33  | 443  | 491  | 244  | White     | Headlineweiß        | Hier steht / eine große / vierzeilige / Überschrift|
| Logo (top-right, cmyk)                | ImageFrame| 374  |  20  | 200  |  60  | —         | shared/logos/gruene-cmyk.png| shared/logos/gruene-cmyk.png (rechtsbündig: 594 − 20 − 200 = 374) |
| Veranstaltung — Datum/Zeit            | TextFrame | 100  | 700  | 200  |  40  | White     | Fließtext           | Samstag, 15. Mai · 14:00                           |
| Veranstaltung — Ort/Adresse           | TextFrame | 100  | 745  | 200  |  40  | White     | Fließtext           | Hauptplatz Baden                                   |
| Anmelde-URL                           | TextFrame | 100  | 790  | 200  |  20  | White     | Fließtext           | gruene.at/anmelde                                  |
| Impressum (vertikal)                  | TextFrame | 564  | 833  | 377  |  21  | White     | Impressum (270°)    | Medieninhaber: Die Grünen NÖ, …                    |

> Hinweis: Die exakten Slot-Positionen weichen leicht ab (sub-mm), weil das Original-SLA
> aus PT-Werten konvertiert wurde. Die Slot-Tabelle rundet auf ganze mm. `meta.yml.slots`
> enthält keine x/y-Felder (nur anname + description), daher prüft `tools/spec_check.py`
> nur Anname-Existenz, nicht Pixel-Genauigkeit für dieses Retro.

```yaml
slots:
  - anname: "Headline 4-zeilig (Brand-Wechselfarbe)"
    type: TextFrame
    x_mm: 33
    y_mm: 443
    w_mm: 491
    h_mm: 244
    fcolor: "White"
    style_ref: "Headlineweiß"
    example: "Hier steht / eine große / vierzeilige / Überschrift"
  - anname: "Veranstaltung — Datum/Zeit"
    type: TextFrame
    x_mm: 100
    y_mm: 700
    w_mm: 200
    h_mm: 40
    fcolor: "White"
    style_ref: "Fließtext"
    example: "Samstag, 15. Mai · 14:00"
  - anname: "Veranstaltung — Ort/Adresse"
    type: TextFrame
    x_mm: 100
    y_mm: 745
    w_mm: 200
    h_mm: 40
    fcolor: "White"
    style_ref: "Fließtext"
    example: "Hauptplatz Baden"
  - anname: "Anmelde-URL"
    type: TextFrame
    x_mm: 100
    y_mm: 790
    w_mm: 200
    h_mm: 20
    fcolor: "White"
    style_ref: "Fließtext"
    example: "gruene.at/anmelde"
  - anname: "Logo (top-right, cmyk)"
    type: ImageFrame
    x_mm: 374
    y_mm: 20
    w_mm: 200
    h_mm: 60
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "Impressum (vertikal)"
    type: TextFrame
    x_mm: 564
    y_mm: 833
    w_mm: 377
    h_mm: 21
    fcolor: "White"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ"
```

## Brand-Hierarchy Observations (Baseline)

1. **Headline-Größe:** ~150 pt (extrapoliert aus 491 mm × 244 mm Frame mit 4 Zeilen
   Gotham Narrow Ultra) — bei A1-Distanz (2–6 m) der visuelle Hauptanker. **Distanz-Lesbarkeit
   ist hart am Maximum**, jede kleinere Headline scheitert.
2. **Color-Wechsel:** identisches Pattern wie Postkarte (Run-Wechsel `Headlineweiß`/
   `Überschrift gelb` para-für-para). Konsistenz mit Postkarte ist Brand-Signal.
3. **Layout-Halbierung:** **obere ~50% weißer Hintergrund** mit Veranstaltungs-Daten +
   Logo rechts oben. **Untere ~50% Dunkelgrün-Vollbild** mit Headline 4-zeilig
   (Wechselfarbe Weiß/Gelb). Klarer Gestalt-Bruch in der Mitte (Trennlinie ~y=414 mm).
   Der Dunkelgrün-Streifen unten ist visuell schwerer als die helle Daten-Zone oben —
   bewusste „Headline-Anker"-Wahl auf der unteren Hälfte (Augen-Lese-Höhe).
4. **Body-Schriftgröße:** 50 pt für Datum/Ort/URL (`Fließtext` Gotham Narrow Book) — bei
   A1-Distanz die Mindest-Lesbarkeit für Sekundär-Inhalt.
5. **Impressum:** 20 pt (groß für A1-Distanz, aber **vertikal um 270° gedreht**) am
   rechten Rand. Mediengesetz-Pflicht ohne den Hauptlayout-Fluss zu stören.
6. **Logo:** rechts oben, 200 mm × 60 mm — bewusst groß als Brand-Erkennung aus Distanz.
7. **Whitespace:** 14 mm Margin reduziert auf ~6 mm bei Logo (Brand-Element darf
   randständig sein); Headline hat 33 mm linke Margin, 70 mm Top-Margin.
8. **Color-Mix:** Dunkelgrün-Streifen + Weißer Hintergrund + Gelb-Akzent in Headline.
   Kein Magenta (Plakate haben keinen Stoerer — der Stoerer ist eher ein Postkarte/Flyer-
   Element). Konsistente Brand-Logik.

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: []
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Plakatpapier blueback 135 g/m² (Außen) oder Bilderdruck matt 170 g/m² (Schaufenster)"
  print_method: "Offset oder Großformat-Digital"
  cmyk_only: true
```
