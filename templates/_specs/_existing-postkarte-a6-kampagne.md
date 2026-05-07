# Retro-Spec: Postkarte A6 Kampagne

> **Hinweis:** Dies ist eine *Retro-Spec* — sie dokumentiert ein **bereits gebautes**
> Template (`templates/postkarte-a6-kampagne/`) im Spec-Format aus
> `templates/_specs/SCHEMA.md`. Zweck: das Spec-Format gegen reale Komplexität stresstesten
> und eine Brand-Hierarchy-Baseline für Reviewer:innen liefern, die alle 8 Templates
> gegeneinander vergleichen.

```yaml
id: postkarte-a6-kampagne
title: Kampagnen-Postkarte A6
format: A6 hochformat 2-seitig
trim_mm: [105, 148]
bleed_mm: 3
pages: 2
fold_type: none
fold_positions_mm: []
cut_type: none
audience: [bezirksgruppe, landesgruppe, ortsgruppe]
```

## Audience und Layout-Philosophie

Zweiseitige A6-Kampagnen-Postkarte für Bezirks- und Ortsgruppen. **Vorderseite** trägt
die Hauptbotschaft (4-zeilige Headline mit alternierenden Brand-Farben) und einen
Stoerer-Badge (Magenta-Kreis). **Rückseite** trägt den Erklär-Text, Social-Handles,
QR-Code und Impressum. Die Postkarte ist als Skelett konzipiert — Endnutzer:innen
ersetzen Platzhalter in Scribus und drucken im Kleinauflagen-Digitaldruck.

## Layout — Vorderseite (Page 1)

```text
   <-------105mm------->
  +---------------------+   ↑
  |                     |   |
  |  +---------------+  |   |
  |  |               |  |   |
  |  |   (Hero IMG   |  |   |
  |  |    optional)  |  | 148
  |  |               |  | mm
  |  +---------------+  |   |
  |                     |   |
  |    H1  H1  H1  H1   |   |
  |   (4-zeilig wechsel-|   |
  |    farbig W/Y/W/Y)  |   |
  |       ◯ ST ◯        |   |
  |     CTA  L          |   |
  |                     |   ↓
  +---------------------+

Legende:
  H1  = Headline 4-zeilig (Brand-Wechselfarbe Weiss/Gelb)
  ST  = Störer-Text 3-zeilig (Magenta-Kreis, ~21 mm)
  CTA = Call-to-Action (1-zeilig, Weiss/Gelb)
  L   = Logo Grüne (weiss)
  IMG = Hero-Bild (optional, sonst Vollfarbe Dunkelgrün)
```

## Layout — Rückseite (Page 2)

```text
   <-------105mm------->
  +---------------------+   ↑
  |    H2 (Headline)    |   |
  |                     |   |
  |    B  B  B  B       |   |
  |    B  B  B  B       |   |
  |    B  B  B  B       |   |
  |    B  B  B  B       | 148
  |    (Erklärtext)     |  mm
  |                     |   |
  |   SH SH SH SH       |   |
  |   (Social Handles)  |   |
  |       URL           |   |
  |       QR            |   |
  |   ▭ ▭ ▭ ▭           |   |
  |     I (Impressum)   |   ↓
  +---------------------+

Legende:
  H2 = Headline Rückseite ("Was wir wollen")
  B  = Erklärtext (Fließtext, 4-Zeilen-Block)
  SH = Social Handles (4-zeilig)
  URL= Kampagnen-URL unter QR
  QR = QR-Code
  I  = Impressum (1-zeilig Bottom-Strip)
```

## Slot-Tabelle

| anname                              | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                                |
|-------------------------------------|-----------|------|------|------|------|-----------|---------------------------------|--------------------------------------------------------|
| Seitenhintergrund (P1)              | Polygon   |  -3  |  -3  | 111  | 154  | Dunkelgrün| —                               | (Vollbild-Hintergrund)                                 |
| Headline 4-zeilig (Brand-Wechselfarbe)| TextFrame|  14  |  47  |  93  |  47  | White/Gelb| Headline sehr wichtig           | Klima retten / Jetzt / Mit deiner / Stimme             |
| CTA                                 | TextFrame |  18  |  93  |  70  |   8  | White     | Default Paragraph Style (2)     | Wähle Grün am 23. Mai                                  |
| Störer-Text 3-zeilig                | TextFrame |  68  |  78  |  19  |  12  | White     | Schrift rosa Kreis              | NEU\nim Mai\n2026                                      |
| Stoerer-Kreis (Magenta-Polygon)     | Polygon   |  68  |  78  |  21  |  21  | Magenta   | —                               | (visueller Störer)                                     |
| Logo Grüne (weiss)                  | ImageFrame|  43  |  88  |  21  |  21  | —         | shared/logos/gruene-weiss.png   | (verwende shared/logos/gruene-weiss.png)               |
| Hero-Bild (optional)                | ImageFrame|  10  |  10  |  85  | 127  | —         | optional                        | (optional — sonst Vollfarbe Dunkelgrün)                |
| Seitenhintergrund (P2)              | Polygon   |  -3  |  -3  | 111  | 154  | Dunkelgrün| —                               | (Vollbild-Rückseite)                                   |
| Erklärtext Rückseite                | TextFrame |  14  |  18  |  71  | 114  | White     | Fließtext                       | (mehrzeiliger Fließtext)                               |
| Social Handles (4-zeilig)           | TextFrame |  14  |  85  |  39  |  16  | White     | Kontaktmöglichkeiten            | Facebook: gruene.noe\nInstagram: @gruene_noe\n…        |
| Kampagnen-URL                       | TextFrame |  60  | 105  |  42  |  11  | White     | Kontaktmöglichkeiten            | gruene.at/klima                                        |
| QR-Code (wird aus URL generiert)    | ImageFrame|  60  |  90  |  20  |  20  | —         | optional                        | (QR-Generator)                                         |
| Impressum (1-zeilig)                | TextFrame |   5  | 138  |  83  |   4  | White     | Impressum                       | Medieninhaber: Die Grünen NÖ, …                        |

```yaml
slots:
  - anname: "Seitenhintergrund"
    type: Polygon
    x_mm: -3
    y_mm: -3
    w_mm: 111
    h_mm: 154
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "Vollbild-Hintergrund"
  - anname: "Headline 4-zeilig (Brand-Wechselfarbe)"
    type: TextFrame
    x_mm: 14
    y_mm: 47
    w_mm: 93
    h_mm: 47
    fcolor: "White"
    style_ref: "Headline sehr wichtig"
    example: "Klima retten / Jetzt / Mit deiner / Stimme"
  - anname: "Störer-Text 3-zeilig"
    type: TextFrame
    x_mm: 68
    y_mm: 78
    w_mm: 19
    h_mm: 12
    fcolor: "White"
    style_ref: "Schrift rosa Kreis"
    example: "NEU\nim Mai\n2026"
  - anname: "Erklärtext Rückseite"
    type: TextFrame
    x_mm: 14
    y_mm: 18
    w_mm: 71
    h_mm: 114
    fcolor: "White"
    style_ref: "Fließtext"
    example: "Was wir wollen: …"
  - anname: "Social Handles (4-zeilig)"
    type: TextFrame
    x_mm: 14
    y_mm: 85
    w_mm: 39
    h_mm: 16
    fcolor: "White"
    style_ref: "Kontaktmöglichkeiten"
    example: "Facebook: gruene.noe\nInstagram: @gruene_noe\noffice@gruene-noe.at\n02742 / 90 230"
  - anname: "Impressum (1-zeilig)"
    type: TextFrame
    x_mm: 5
    y_mm: 138
    w_mm: 83
    h_mm: 4
    fcolor: "White"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten"
```

> Hinweis: nicht alle Frames im SLA tragen einen `ANNAME` (z.B. die Hero-Bild- und
> CTA-Frames der Postkarte sind unbenannt). Die Slot-Tabelle bezieht sich auf das
> Mensch-Verständnis, was diese Frames tun. Für `tools/spec_check.py`-Drift gilt nur die
> Untermenge mit explizitem `anname` in `meta.yml.slots.*`.

## Brand-Hierarchy Observations (Baseline)

Konkrete Beobachtungen aus dem heutigen Build, die als Vergleichsbasis für Gate 3 dienen:

1. **Headline-Größe:** 27 pt (Gotham Narrow Ultra) für 4-zeilige Headline — auf 105×148
   mm Postkarte ist das die maximale Größe ohne Überlauf.
2. **Color-Wechsel:** alternierend `White`/`Gelb` Run-für-Run innerhalb eines Frames
   (nicht zwei verschiedene Frames). Pattern: erste/dritte Zeile Weiß, zweite/vierte
   Gelb. Erzeugt visuellen Rhythmus auf Dunkelgrün-Hintergrund.
3. **Stoerer:** genau **ein** Magenta-Kreis (~21 mm Durchmesser), mit weißem 3-zeiligem
   Text in `Schrift rosa Kreis` (Gotham Narrow Ultra 10 pt, 11 pt linesp). Niemals
   mehrere Stoerer auf einem Layout.
4. **Logo-Größe:** 21 mm × 21 mm, Vorderseite zentriert unten, Rückseite oben links.
   Logo ist das **Brand-Anker**-Element — auf jeder Seite präsent.
5. **Body-Schriftgröße:** 12 pt (`Fließtext`, Gotham Narrow Book) — Mindestlesbarkeit
   bei A6-Distanz (Hand-Lesedistanz ~35–50 cm).
6. **Impressum:** 5 pt (`Impressum`, Gotham Narrow Book) — gerade noch lesbar bei
   Hand-Distanz, gesetzlich-pflichtig (Mediengesetz §24).
7. **Whitespace:** 14 mm Margin allseitig (außer der Hintergrund, der den Bleed mit-deckt).
8. **Color-Mix:** Dunkelgrün als Primary-Background, Weiß als Primary-Text, Gelb als
   Wechsel-Akzent in Headline, Magenta nur im Stoerer. Kein Schwarz, kein Hellgrün.

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: []
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Bilderdruck matt 250–300 g/m²"
  print_method: "Digital (≤ 250 Stück) oder Offset (> 250)"
  cmyk_only: true
```

## Mediengesetz §24

Impressum ist im Slot `impressum` enthalten. Default-Text aus
`tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`. Endnutzer:innen passen Druckerei
und Auflagen-Hinweis an.
