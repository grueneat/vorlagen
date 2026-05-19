# Retro-Spec: Grüne Zeitung A4

> **Hinweis:** Retro-Spec für `templates/zeitung-a4/` — eine 14-seitige
> Master-Page-Komposition, das komplexeste der drei bestehenden Templates. Stresstet das
> Spec-Format gegen Multi-Page + Multi-Master + linked-frame text-flow.

```yaml
id: zeitung-a4
title: Grüne Zeitung A4
format: A4 hochformat 14-seitig
trim_mm: [210, 297]
bleed_mm: 3
pages: 14
fold_type: none
fold_positions_mm: []
cut_type: none
audience: [bezirksgruppe, landesgruppe]
```

## Audience und Layout-Philosophie

Mehrseitige A4-Zeitungs-Vorlage für regelmäßige Bezirks-/Landes-Gruppen-Publikationen
(monatlich/quartalsweise). Eine Datei mit allen typischen Zeitungs-Layouts —
Bezirks-/Landesgruppen duplizieren die gewünschten Beispielseiten, passen Inhalte an,
löschen ungenutzte. **Master-Pages-Architektur** macht das Layout konsistent über alle
14 Seiten: 6 Master (Normal, rechts-3col, links-3col, titelseite, foto-spread,
impressum-master). 84 linked-text-frame-chains für mehrspaltigen Artikel-Fluss.

## Master-Page-Inventar

| Master | Verwendung | Layout-Element |
|---|---|---|
| `Normal` | Default-Hülle | Header-Streifen, Seitenzahl-Position |
| `titelseite` | Cover (Page 1) | Hero-Bereich + Header + Inhaltsverzeichnis |
| `rechts-3col` | rechte Innenseiten | 3-Spalten-Grid + Footer-Akzent (rechte Bindung) |
| `links-3col` | linke Innenseiten | 3-Spalten-Grid + Footer-Akzent (linke Bindung) |
| `foto-spread` | Vollbild-Fotoseite | Bleed-Bild + Bildunterschrift |
| `impressum-master` | Rückseite (Page 14) | Impressum-Block + Vertriebs-Info |

## Layout — Titelseite (Page 1)

```text
   <-----210mm----->
  +-----------------+   ↑
  |H L              |   |  Header-Bereich:
  |  (Monat/Ausgabe)|   |  H = Header-Streifen
  +=================+   |  L = Logo
  |                 |   |
  |     HERO        |   |
  |    (Vollbild    |   |
  |     mit Inhalt) |   |
  |                 |   |
  | ┌─────────────┐ |   |
  | │ Inhalts-    │ |  297
  | │ headline    │ |  mm
  | │ (Cover-     │ |   |
  | │  Aufmacher) │ |   |
  | └─────────────┘ |   |
  |                 |   |
  | ┌──Inhaltsver-┐ |   |
  | │  zeichnis   │ |   |
  | │ (3-spaltig) │ |   |
  | └─────────────┘ |   |
  |             #1  |   |
  +-----------------+   ↓

Legende:
  H  = Header-Streifen (titelseite header style)
  L  = Logo Grüne (oben links)
  HERO = Hero-Bild oder Vollfarbe Dunkelgrün
  #1 = Seitenzahl
```

## Layout — Innenseite 3-spaltig (Page 2 als Beispiel)

```text
   <-----210mm----->
  +-----------------+   ↑
  | H Header        |   |
  +-+-----+-+-----+-+   |
  | |     | |     | |   |
  | | C1  | | C2  | |   |  3 Spalten = 3 linked
  | |     | |     | |   |  TextFrames
  | | C1  | | C2  | |  297
  | |     | |     | |  mm
  | | C1  | | C2  | |   |
  | |     | |     | |   |
  | +-----+ +-----+ |   |
  | C3              |   |
  | +-----+         |   |
  | | C3  |  IMG    |   |
  | |     |         |   |
  | +-----+         |   |
  | F   F   F   #2  |   |
  +-----------------+   ↓

Legende:
  C1, C2, C3 = drei verlinkte TextFrames (ColumnTextStory-Block)
  IMG = Artikel-Bild
  F   = Footer-Akzent (Brand-Farbband)
  #2  = Seitenzahl
```

## Slot-Tabelle (representativ; Detail-Slots in `meta.yml`)

Die Zeitung hat 14 Seiten und ~400 PAGEOBJECTs. `meta.yml.slots` enthält keine pixelgenauen
Slot-Positionen; diese Retro-Spec listet die **Slot-Klassen** (wiederholt sich pro Seite/
Master).

| anname-Klasse              | type      | Vorkommen | fcolor    | style_ref                    | example                                           |
|----------------------------|-----------|-----------|-----------|------------------------------|---------------------------------------------------|
| Seitenzahl                 | TextFrame | 12× (Pages 1, 3-14)| Dunkelgrün/White | Seitenzahl       | `<var name="pgno"/>` (auto-resolved)              |
| Titelseite Header          | TextFrame |  1× (P1)  | White     | Titelseite Header            | „Grüne Zeitung Niederösterreich · Ausgabe 5/2026" |
| Monat/Ausgabe              | TextFrame |  1× (P1)  | White     | Monat/Ausgabe                | „Mai 2026 · Ausgabe 5"                            |
| Inhaltsheadline Titelseite | TextFrame |  1× (P1)  | Gelb      | Inhaltsheadline Titelseite   | „Energiewende: Konkrete Schritte"                 |
| Überschrift Dunkelgrün     | TextFrame | ~12×      | Dunkelgrün| Überschrift Dunkelgrün       | „Klimaschutz auf der Gemeindeebene"               |
| Überschrift weiß           | TextFrame | ~6×       | White     | Überschrift weiß             | (auf Dunkelgrün-Background)                       |
| Fließtext                  | TextFrame | ~84-Chain | Black     | Fließtext                    | (Artikel-Body, mehrspaltig)                       |
| Fließtext weiß             | TextFrame | ~12×      | White     | Fließtext weiß               | (auf Dunkelgrün-Background)                       |
| Zwischenüberschrift        | TextFrame | ~16×      | Black     | Zwischenüberschrift          | (Inline-Sub im Artikel)                           |
| Bildunterschrift weiß      | TextFrame | ~8×       | White     | Bildunterschrift weiß        | „Foto: Kreisversammlung Mödling, April 2026"      |
| Zitat weißer Text          | TextFrame | ~4×       | White     | Zitat weißer Text            | (Pull-Quote auf grünem Kasten)                    |
| Schrift Störer             | TextFrame |  1-2×     | White     | Schrift Störer               | (Magenta-Stoerer wo es passt)                     |
| Impressum                  | TextFrame |  1× (P14) | Black     | Impressum                    | (Mediengesetz-§24-Block)                          |

```yaml
slots:
  - anname: "Seitenzahl"
    type: TextFrame
    x_mm: 8
    y_mm: 280
    w_mm: 12
    h_mm: 9
    fcolor: "White"
    style_ref: "Seitenzahl"
    example: "1"
  - anname: "Titelseite Header"
    type: TextFrame
    x_mm: 14
    y_mm: 8
    w_mm: 180
    h_mm: 10
    fcolor: "White"
    style_ref: "Titelseite Header"
    example: "Grüne Zeitung Niederösterreich · Ausgabe 5/2026"
  - anname: "Inhaltsheadline Titelseite"
    type: TextFrame
    x_mm: 14
    y_mm: 100
    w_mm: 180
    h_mm: 60
    fcolor: "Gelb"
    style_ref: "Inhaltsheadline Titelseite"
    example: "Energiewende: Konkrete Schritte für unsere Gemeinde"
  - anname: "Überschrift Dunkelgrün"
    type: TextFrame
    x_mm: 14
    y_mm: 30
    w_mm: 180
    h_mm: 20
    fcolor: "Dunkelgrün"
    style_ref: "Überschrift Dunkelgrün"
    example: "Klimaschutz auf der Gemeindeebene"
  - anname: "Fließtext"
    type: TextFrame
    x_mm: 14
    y_mm: 60
    w_mm: 60
    h_mm: 200
    fcolor: "Black"
    style_ref: "Fließtext"
    example: "(Artikel-Body, in 3 Spalten mit ColumnTextStory-Block verlinkt)"
  - anname: "Impressum"
    type: TextFrame
    x_mm: 14
    y_mm: 250
    w_mm: 180
    h_mm: 30
    fcolor: "Black"
    style_ref: "Impressum"
    example: "Medieninhaber und Herausgeber: Die Grünen Niederösterreich, Daniel-Gran-Straße 48, 3100 St. Pölten"
```

> `meta.yml` für Zeitung enthält im aktuellen Stand **keine** `slots:`-Sektion mit pro-Slot
> Detail; statt dessen nutzt es `masters:` und `example_pages:`. Dies ist ein
> bewusster Verzicht: bei 14 Seiten × 30 Slots wäre eine flache Slot-Tabelle nicht
> nützlich. Die Retro-Spec listet **Slot-Klassen** statt -Instanzen. Daher ist
> `tools/spec_check.py` für zeitung-a4 **Drift-Check by Klasse** (Style-Existenz),
> nicht pro-Frame Pixel-Match.

## Brand-Hierarchy Observations (Baseline)

1. **Hauptheadline:** 27 pt (`Inhaltsheadline Titelseite`, Vollkorn Black Italic, Gelb).
   Cover-Aufmacher — analog zum Plakat-Headline-Anker.
2. **Innen-Überschriften:** ~20 pt (`Überschrift Dunkelgrün` oder `Überschrift weiß`).
   Eindeutige Hierarchie unter der Hauptheadline.
3. **Body:** 11 pt (`Fließtext`, Gotham Narrow Book). Lese-Distanz ~30–50 cm — klassische
   Zeitungs-Lesbarkeit.
4. **Zwischenüberschrift:** ~13 pt — visueller Gliederungs-Anker im Fließtext.
5. **Impressum:** 5 pt — gleich wie Postkarte, gesetzlich-pflichtig.
6. **Bildunterschrift:** ~8 pt, auf weißem oder dunkelgrünem Hintergrund.
7. **3-Spalten-Grid:** Spaltenbreite ~60 mm, Gutter 11 pt (~3.9 mm); klassisch-deutsche
   Zeitungs-Konvention.
8. **Color-Anker:** Dunkelgrün als Brand-Primary in Header und Footer-Bändern; Weiß als
   Body-Hintergrund (Lesbarkeit); Gelb als Akzent in Cover-Headline; Magenta nur als
   Stoerer auf 1–2 Seiten.
9. **Logo:** weiß auf Dunkelgrün-Header der Titelseite, schwarz auf weißem Hintergrund
   einzelner Innenseiten — Color-mode passt zum Untergrund.
10. **Whitespace-Rhythmus:** 14 mm Margin allseitig + 11 pt Spalten-Gutter. Die Zeitung ist
    bewusst dichter als Plakat/Postkarte — Lese-Material braucht Body-Dichte.
11. **Footer-Akzent:** dünnes Brand-Farbband am unteren Seitenrand (variiert pro Master)
    erzeugt Wiederholungs-Rhythmus über alle Innenseiten.

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: []
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Zeitungsdruckpapier 70–80 g/m² (Massenauflage) oder Bilderdruck matt 90 g/m² (Hochwertige Ausgabe)"
  print_method: "Rollenoffset (≥ 5000) oder Bogenoffset (< 5000)"
  cmyk_only: true
```

## Master-Page-Drift-Hinweis

Die 6 Master-Pages sind im SLA als separate `<MASTERPAGE>`-Elemente vorhanden. Slots auf
einer Master-Page propagieren auf alle Doc-Pages, die `masterPageName` matcht. Drift-Check
sollte eines Tages Master-Slots gesondert behandeln — heute prüft `tools/spec_check.py`
nur Doc-Page-Slots.

## Schema-Stress-Findings

Diese Retro-Spec hat folgende Punkte als Schema-Lücken aufgedeckt:

1. **Multi-Master-Templates** brauchen ein `masters:`-Feld in der Spec-YAML (heute nur in
   `meta.yml`). Spec-Schema erweitern, wenn ein neues Template Multi-Master verwendet.
   Bisher ist nur die Zeitung Multi-Master, daher keine Schema-Änderung jetzt.
2. **Multi-Page-Templates mit identischen Layouts** (z.B. 5× linked-articles) brauchen
   keine 5 ASCII-Skizzen — eine repräsentative + Hinweis. Ist im SCHEMA bereits implizit
   (eine Skizze pro „sichtbarer Seite" — Doppelseiten-Wiederholung deklariert).
3. **Linked-text-frame-Stories** (84 Chains in zeitung-a4) sind im DSL ein
   Block-Pattern (`ColumnTextStory`), nicht ein einzelner Slot. Sollten in der Slot-Tabelle
   als `Block:ColumnTextStory` markiert werden — heute ist das nur sporadisch dokumentiert.
   Future Schema-Refinement.

Keine dieser Findings blockiert die fünf neuen Specs.
