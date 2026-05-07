# Spec: Kandidat-Falzflyer DIN-lang

```yaml
id: kandidat-falzflyer-din-lang
title: Kandidat-Falzflyer DIN-lang
format: A4 quer (297x210) Zickzackfalz auf 3 Panele DIN-lang (99x210)
trim_mm: [297, 210]
bleed_mm: 3
pages: 2
fold_type: zickzackfalz
fold_positions_mm: [99, 198]
cut_type: none
audience: [kandidat, bezirksgruppe, ortsgruppe]
```

## Audience und Layout-Philosophie

**Kandidaten-Vorstellungs-Flyer** für Personalisierung im Kommunal-, Landtags- und
Nationalratswahlkampf. Bezirksgruppen drucken den Flyer pro Kandidat:in, verteilen am
Infostand und in der Tür-Kampagne. Lese-Distanz **Hand-Distanz** ~30–40 cm, aber durch
Falz-Mechanik mit **gestaffelter Aufmerksamkeit**: Cover hooks → Teaser teases → Themen
delivers → Closer (Wahlkreuz) acts.

**Layout-Philosophie:** Multi-Panel-Narrativ mit Falz-Logik. Der Flyer ist ein A4 quer
mit **Zickzackfalz** (Z-fold/accordion, 3 Panele à 99 mm) — geschlossen sieht man Panel 1
(Cover), beim ersten Aufklappen Panel 2 (Teaser), beim vollen Aufklappen Panel 3 (Closer)
+ alle Back-Panele (Themen). Der Wahlkreuz sitzt auf Panel 3 (Closer) — der letzte
Aufmerksamkeits-Anker bevor der Flyer wieder zugefaltet wird.

## Layout — Front (Page 1, flach 297×210 mm)

```text
   <-99mm->|<-99mm->|<-99mm->
  +-------+-------+-------+   ↑
  | L     | T-Hd  | WK    |   |
  | (Logo)|       | (auf  |   |
  | PORT  | T Body| Dunkel|   |
  | (Foto)|       |  grün)|   |
  | NAME  |       |       |   |
  | SLOG  | logo  | "Wäh- |   | 210mm
  |       | klein | le    |   |
  |       |       | Grün  |   |
  |       |       | am    |   |
  |       |       | 23.5."|   |
  |       |       |       |   |
  +-------+-------+-------+   ↓
   Panel 1  Panel 2  Panel 3
   (Cover) (Teaser) (Closer)
   = was beim Falten sichtbar ist (außen)

Falten:
  Panel 3 wird auf Panel 2 gefaltet (Falz bei x=198)
  Dann beide auf Panel 1 (Falz bei x=99)
  Geschlossen: nur Panel 1 sichtbar (= Cover)

Legende:
  L    = Logo Grüne (cmyk)
  PORT = Kandidat-Portrait (Codex demo image)
  NAME = Kandidat-Name (groß)
  SLOG = Slogan (1-2 Zeilen)
  T-Hd = Teaser-Headline
  T-Body = Teaser-Body
  WK   = Wahlkreuz auf Dunkelgrün (D12)
```

## Layout — Back (Page 2, flach 297×210 mm)

```text
   <-99mm->|<-99mm->|<-99mm->
  +-------+-------+-------+   ↑
  |T1 Hd  |T3 Hd  |Kontakt|   |
  |T1 Body|T3 Body| · · · |   |
  |       |       |       |   |
  |T2 Hd  |T4 Hd  | QR    |   |
  |T2 Body|T4 Body|       |   | 210mm
  |       |       | Imp.  |   |
  |       |       |       |   |
  |       |       |       |   |
  +-------+-------+-------+   ↓
   Panel 4  Panel 5  Panel 6
   (Themen (Themen  (Kontakt
    1+2)    3+4)     +Imp.)
   = beim vollen Aufklappen sichtbar (innen)

Legende:
  T1-T4 Hd/Body = vier Themen-Module mit Headline + Body
  Kontakt = Adresse, Tel, Email
  QR    = QR-Code zur Kandidaten-Webseite
  Imp.  = Impressum
```

## Reading-Order

```text
1. Geschlossen: nur Panel 1 sichtbar.
   "Wer ist die Kandidatin? Wie heißt sie?"
   Cover muss in 1 Sekunde Person + Botschaft transportieren.

2. Erstes Aufklappen: Panel 2 erscheint neben Panel 1.
   "Was vertritt sie?"
   Teaser-Headline + 3-4-Satz-Teaser. Ein Aufruf zur Vertiefung.

3. Volles Aufklappen: Panele 4-6 (innen) plus Panel 3 als Hängelasche sichtbar.
   "Themen" (Panele 4-5) + "Kontakt" (Panel 6) + "Wahlaufruf" (Panel 3 als Closer).

4. Zufalten: Wahlkreuz auf Panel 3 ist die letzte Botschaft.
   Symbolische Reinforcement: nicht nur Person, nicht nur Themen, sondern Aufruf zur Wahl.
```

## Constraints

- **Coordinate-Origin:** Trim-Top-Left (0, 0).
- **Trim:** 297 × 210 mm. **Bleed 3 mm.**
- **Falz-Linien:** vertikal bei **x = 99 mm** und **x = 198 mm** auf Falz-Layer.
- **Per-Panel Inhalts-Bereich:** 99 mm Panel − 6 mm Safety (3 mm pro Falz-/Trim-Kante)
  = **93 mm usable Width** pro Panel. Bei Panel 1 (linker Trim) und Panel 3 (rechter Trim)
  ist die Safety zur Trim-Außenkante 3 mm + zur Falz-Innenkante 3 mm.
- **Per-Panel-Headline ≥ 16 pt** (SCHEMA.md DIN-lang-Mindest).
- **Per-Panel-Body ≥ 9 pt**.
- **Wahlkreuz auf Panel 3:** 50 mm × 50 mm auf Dunkelgrün-Polygon (D12), padding 4 mm.
- **Logo auf Panel 1 + Panel 2 + Panel 6** (Brand-Anker auf jeder „Aufmerksamkeits-Phase").

## Slot-Tabelle — Front (Panele 1, 2, 3)

### Panel 1 — Cover (x=0–99 mm)

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                      |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|----------------------------------------------|
| P1 Logo Grüne (cmyk)         | ImageFrame       |   6  |  10  |  35  |  10  | —         | shared/logos/gruene-cmyk.png       | (verwende shared/logos/gruene-cmyk.png)      |
| P1 Kandidat-Portrait         | ImageFrame       |   6  |  28  |  87  | 105  | —         | optional / Codex demo (D11)        | (Codex DALL·E generiert)                     |
| P1 Kandidat-Name             | TextFrame        |   6  | 138  |  87  |  16  | Dunkelgrün| falzflyer/cand-name                | Maria Beispiel                               |
| P1 Slogan                    | TextFrame        |   6  | 156  |  87  |  40  | Black     | falzflyer/slogan                   | Mut zur Klima-Wende.\nFür Mödling.           |

### Panel 2 — Teaser (x=99–198 mm)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                              |
|------------------------------|-----------|------|------|------|------|-----------|---------------------------------|------------------------------------------------------|
| P2 Teaser-Headline           | TextFrame | 105  |  20  |  87  |  20  | Dunkelgrün| falzflyer/teaser-headline       | Was ich für Mödling will                             |
| P2 Teaser-Body               | TextFrame | 105  |  44  |  87  | 130  | Black     | falzflyer/teaser-body           | Mödling hat einen Klimaplan — er muss umgesetzt werden. Ich bringe Erfahrung aus 10 Jahren Energiewende-Beratung mit und will sie für unsere Gemeinde einsetzen. |
| P2 Logo (klein)              | ImageFrame| 105  | 188  |  25  |   8  | —         | shared/logos/gruene-cmyk.png    | (verwende shared/logos/gruene-cmyk.png)              |

### Panel 3 — Closer (x=198–297 mm)

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                      |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|----------------------------------------------|
| P3 Hintergrund               | Polygon          | 198  |   0  |  99  | 210  | Dunkelgrün| —                                  | (Vollbild Closer-Panel)                      |
| P3 Wahlkreuz                 | Block:WahlkreuzSymbol| 222| 30 |  50  |  50  | —         | —                                  | (Wahlkreuz auf Dunkelgrün-Polygon)           |
| P3 Closer-Headline           | TextFrame        | 204  |  90  |  87  |  30  | White     | falzflyer/closer-headline          | Wähle Grün am 23. Mai                        |
| P3 Datum-Akzent              | TextFrame        | 204  | 125  |  87  |  20  | Gelb      | falzflyer/closer-datum             | Sonntag, 23. Mai 2026                        |
| P3 URL                       | TextFrame        | 204  | 175  |  87  |  10  | White     | falzflyer/closer-url               | gruene-moedling.at                           |

### Falz-Linien (Front)

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                      |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|----------------------------------------------|
| Falz x=99 (Front)            | Block:FoldLine   |  99  |   0  |   0  | 210  | Falz      | —                                  | (FoldLine vertikal y=0..210, x=99)           |
| Falz x=198 (Front)           | Block:FoldLine   | 198  |   0  |   0  | 210  | Falz      | —                                  | (FoldLine vertikal y=0..210, x=198)          |

## Slot-Tabelle — Back (Panele 4, 5, 6)

### Panel 4 — Themen 1+2 (x=0–99 mm)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                              |
|------------------------------|-----------|------|------|------|------|-----------|---------------------------------|------------------------------------------------------|
| P4 Thema 1 — Headline        | TextFrame |   6  |  20  |  87  |  14  | Dunkelgrün| falzflyer/thema-headline        | Klimaplan umsetzen                                   |
| P4 Thema 1 — Body            | TextFrame |   6  |  35  |  87  |  60  | Black     | falzflyer/thema-body            | Solar auf jedes Gemeindedach. Heizungstausch fördern. Öffis verdoppeln. |
| P4 Thema 2 — Headline        | TextFrame |   6  | 105  |  87  |  14  | Dunkelgrün| falzflyer/thema-headline        | Leistbares Wohnen                                    |
| P4 Thema 2 — Body            | TextFrame |   6  | 120  |  87  |  60  | Black     | falzflyer/thema-body            | Gemeinde-Wohnbau ankurbeln. Mietpreis-Bremse für Neubauten. |

### Panel 5 — Themen 3+4 (x=99–198 mm)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                              |
|------------------------------|-----------|------|------|------|------|-----------|---------------------------------|------------------------------------------------------|
| P5 Thema 3 — Headline        | TextFrame | 105  |  20  |  87  |  14  | Dunkelgrün| falzflyer/thema-headline        | Bildung vor Ort                                      |
| P5 Thema 3 — Body            | TextFrame | 105  |  35  |  87  |  60  | Black     | falzflyer/thema-body            | Volksschulen ausbauen. Nachmittagsbetreuung gratis. Schulwege sicher. |
| P5 Thema 4 — Headline        | TextFrame | 105  | 105  |  87  |  14  | Dunkelgrün| falzflyer/thema-headline        | Lokale Wirtschaft                                    |
| P5 Thema 4 — Body            | TextFrame | 105  | 120  |  87  |  60  | Black     | falzflyer/thema-body            | Regionale Lieferketten. Handwerks-Förderung. Klein­betriebe statt Konzern-Filialen. |

### Panel 6 — Kontakt + Impressum (x=198–297 mm)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                       | example                                              |
|------------------------------|-----------|------|------|------|------|-----------|---------------------------------|------------------------------------------------------|
| P6 Kontakt-Headline          | TextFrame | 204  |  20  |  87  |  14  | Dunkelgrün| falzflyer/contact-headline      | Sprich mich an                                       |
| P6 Kontakt-Adresse           | TextFrame | 204  |  35  |  87  |  20  | Black     | falzflyer/contact-body          | Hauptstraße 12\n2340 Mödling                         |
| P6 Kontakt-Email-Tel         | TextFrame | 204  |  56  |  87  |  20  | Black     | falzflyer/contact-body          | maria.beispiel@gruene-moedling.at\n+43 660 1234567   |
| P6 QR-Code                   | ImageFrame| 232  |  85  |  35  |  35  | —         | optional / generated            | (QR zur Kandidaten-Webseite)                         |
| P6 Logo Grüne                | ImageFrame| 204  | 130  |  35  |  10  | —         | shared/logos/gruene-cmyk.png    | (verwende shared/logos/gruene-cmyk.png)              |
| P6 Impressum                 | TextFrame | 204  | 145  |  87  |  60  | Black     | Impressum                       | Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten. |

### Falz-Linien (Back)

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                      |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|----------------------------------------------|
| Falz x=99 (Back)             | Block:FoldLine   |  99  |   0  |   0  | 210  | Falz      | —                                  | (FoldLine vertikal y=0..210, x=99)           |
| Falz x=198 (Back)            | Block:FoldLine   | 198  |   0  |   0  | 210  | Falz      | —                                  | (FoldLine vertikal y=0..210, x=198)          |

```yaml
slots:
  # Front Panel 1 — Cover
  - anname: "P1 Logo Grüne"
    type: ImageFrame
    x_mm: 6
    y_mm: 10
    w_mm: 35
    h_mm: 10
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "P1 Kandidat-Portrait"
    type: ImageFrame
    x_mm: 6
    y_mm: 28
    w_mm: 87
    h_mm: 105
    fcolor: ""
    style_ref: "optional / Codex demo (D11)"
    example: ""
  - anname: "P1 Kandidat-Name"
    type: TextFrame
    x_mm: 6
    y_mm: 138
    w_mm: 87
    h_mm: 16
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/cand-name"
    example: "Maria Beispiel"
  - anname: "P1 Slogan"
    type: TextFrame
    x_mm: 6
    y_mm: 156
    w_mm: 87
    h_mm: 40
    fcolor: "Black"
    style_ref: "falzflyer/slogan"
    example: "Mut zur Klima-Wende.\nFür Mödling."
  # Front Panel 2 — Teaser
  - anname: "P2 Teaser-Headline"
    type: TextFrame
    x_mm: 105
    y_mm: 20
    w_mm: 87
    h_mm: 20
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/teaser-headline"
    example: "Was ich für Mödling will"
  - anname: "P2 Teaser-Body"
    type: TextFrame
    x_mm: 105
    y_mm: 44
    w_mm: 87
    h_mm: 130
    fcolor: "Black"
    style_ref: "falzflyer/teaser-body"
    example: "Mödling hat einen Klimaplan — er muss umgesetzt werden."
  - anname: "P2 Logo (klein)"
    type: ImageFrame
    x_mm: 105
    y_mm: 188
    w_mm: 25
    h_mm: 8
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  # Front Panel 3 — Closer
  - anname: "P3 Hintergrund"
    type: Polygon
    x_mm: 198
    y_mm: 0
    w_mm: 99
    h_mm: 210
    fcolor: "Dunkelgrün"
    style_ref: ""
    example: "Vollbild Closer-Panel"
  - anname: "P3 Wahlkreuz"
    type: "Block:WahlkreuzSymbol"
    x_mm: 222
    y_mm: 30
    w_mm: 50
    h_mm: 50
    fcolor: ""
    style_ref: ""
    example: "Wahlkreuz auf Dunkelgrün-Polygon"
  - anname: "P3 Closer-Headline"
    type: TextFrame
    x_mm: 204
    y_mm: 90
    w_mm: 87
    h_mm: 30
    fcolor: "White"
    style_ref: "falzflyer/closer-headline"
    example: "Wähle Grün am 23. Mai"
  - anname: "P3 Datum-Akzent"
    type: TextFrame
    x_mm: 204
    y_mm: 125
    w_mm: 87
    h_mm: 20
    fcolor: "Gelb"
    style_ref: "falzflyer/closer-datum"
    example: "Sonntag, 23. Mai 2026"
  - anname: "P3 URL"
    type: TextFrame
    x_mm: 204
    y_mm: 175
    w_mm: 87
    h_mm: 10
    fcolor: "White"
    style_ref: "falzflyer/closer-url"
    example: "gruene-moedling.at"
  - anname: "Falz x=99 (Front)"
    type: "Block:FoldLine"
    x_mm: 99
    y_mm: 0
    w_mm: 0
    h_mm: 210
    fcolor: "Falz"
    style_ref: ""
    example: "FoldLine vertikal y=0..210, x=99"
  - anname: "Falz x=198 (Front)"
    type: "Block:FoldLine"
    x_mm: 198
    y_mm: 0
    w_mm: 0
    h_mm: 210
    fcolor: "Falz"
    style_ref: ""
    example: "FoldLine vertikal y=0..210, x=198"
  # Back Panel 4 — Themen 1+2
  - anname: "P4 Thema 1 — Headline"
    type: TextFrame
    x_mm: 6
    y_mm: 20
    w_mm: 87
    h_mm: 14
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/thema-headline"
    example: "Klimaplan umsetzen"
  - anname: "P4 Thema 1 — Body"
    type: TextFrame
    x_mm: 6
    y_mm: 35
    w_mm: 87
    h_mm: 60
    fcolor: "Black"
    style_ref: "falzflyer/thema-body"
    example: "Solar auf jedes Gemeindedach. Heizungstausch fördern. Öffis verdoppeln."
  - anname: "P4 Thema 2 — Headline"
    type: TextFrame
    x_mm: 6
    y_mm: 105
    w_mm: 87
    h_mm: 14
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/thema-headline"
    example: "Leistbares Wohnen"
  - anname: "P4 Thema 2 — Body"
    type: TextFrame
    x_mm: 6
    y_mm: 120
    w_mm: 87
    h_mm: 60
    fcolor: "Black"
    style_ref: "falzflyer/thema-body"
    example: "Gemeinde-Wohnbau ankurbeln. Mietpreis-Bremse für Neubauten."
  # Back Panel 5 — Themen 3+4
  - anname: "P5 Thema 3 — Headline"
    type: TextFrame
    x_mm: 105
    y_mm: 20
    w_mm: 87
    h_mm: 14
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/thema-headline"
    example: "Bildung vor Ort"
  - anname: "P5 Thema 3 — Body"
    type: TextFrame
    x_mm: 105
    y_mm: 35
    w_mm: 87
    h_mm: 60
    fcolor: "Black"
    style_ref: "falzflyer/thema-body"
    example: "Volksschulen ausbauen. Nachmittagsbetreuung gratis."
  - anname: "P5 Thema 4 — Headline"
    type: TextFrame
    x_mm: 105
    y_mm: 105
    w_mm: 87
    h_mm: 14
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/thema-headline"
    example: "Lokale Wirtschaft"
  - anname: "P5 Thema 4 — Body"
    type: TextFrame
    x_mm: 105
    y_mm: 120
    w_mm: 87
    h_mm: 60
    fcolor: "Black"
    style_ref: "falzflyer/thema-body"
    example: "Regionale Lieferketten. Handwerks-Förderung."
  # Back Panel 6 — Kontakt
  - anname: "P6 Kontakt-Headline"
    type: TextFrame
    x_mm: 204
    y_mm: 20
    w_mm: 87
    h_mm: 14
    fcolor: "Dunkelgrün"
    style_ref: "falzflyer/contact-headline"
    example: "Sprich mich an"
  - anname: "P6 Kontakt-Adresse"
    type: TextFrame
    x_mm: 204
    y_mm: 35
    w_mm: 87
    h_mm: 20
    fcolor: "Black"
    style_ref: "falzflyer/contact-body"
    example: "Hauptstraße 12\n2340 Mödling"
  - anname: "P6 Kontakt-Email-Tel"
    type: TextFrame
    x_mm: 204
    y_mm: 56
    w_mm: 87
    h_mm: 20
    fcolor: "Black"
    style_ref: "falzflyer/contact-body"
    example: "maria.beispiel@gruene-moedling.at\n+43 660 1234567"
  - anname: "P6 QR-Code"
    type: ImageFrame
    x_mm: 232
    y_mm: 85
    w_mm: 35
    h_mm: 35
    fcolor: ""
    style_ref: "optional / generated"
    example: "QR zur Kandidaten-Webseite"
  - anname: "P6 Logo Grüne"
    type: ImageFrame
    x_mm: 204
    y_mm: 130
    w_mm: 35
    h_mm: 10
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "P6 Impressum"
    type: TextFrame
    x_mm: 204
    y_mm: 145
    w_mm: 87
    h_mm: 60
    fcolor: "Black"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
  - anname: "Falz x=99 (Back)"
    type: "Block:FoldLine"
    x_mm: 99
    y_mm: 0
    w_mm: 0
    h_mm: 210
    fcolor: "Falz"
    style_ref: ""
    example: "FoldLine vertikal y=0..210, x=99"
  - anname: "Falz x=198 (Back)"
    type: "Block:FoldLine"
    x_mm: 198
    y_mm: 0
    w_mm: 0
    h_mm: 210
    fcolor: "Falz"
    style_ref: ""
    example: "FoldLine vertikal y=0..210, x=198"
```

## EPS / Image-Embedding-Strategie

```yaml
eps_strategy:
  asset_path: "shared/assets/wahlkreuz.png"
  scale_type: 0
  background_color: "Dunkelgrün"   # D12: Closer-Panel hat Dunkelgrün-Vollbild
  background_padding_mm: 4.0
  encoding: "qcompress"
  helper: "pack_inline_image"
```

## Background-Color Contract für Wahlkreuz (D12)

> **Der Wahlkreuz MUSS auf farbigem Brand-Hintergrund stehen — `Dunkelgrün`, `Hellgrün`,
> oder `Magenta`. NIE auf Weiß. NIE auf Gelb.**

**Diese Spec wählt `Dunkelgrün`** als Background. Begründung: das gesamte Panel 3 ist
Dunkelgrün-Vollbild — der Wahlkreuz integriert sich visuell in das Closer-Panel statt
es zu fragmentieren. Der weiße Kreis hebt sich klar vom Dunkelgrün ab.

## Falz / Stanze

**Falz:** Zickzackfalz an x=99 mm und x=198 mm. **Stanze:** keine.

### Falz-Layer + Spot-Color

```yaml
layer_falz:
  name: "Falz"
  printable: false
  flow: false
  exportable: true

color_falz:
  name: "Falz"
  cmyk: [100, 0, 0, 0]
  spot: true
  document_local: true
```

### Falz-Mechanik

**Zickzackfalz** (Z-fold/accordion): die drei Panele falten sich akkordeonartig. Panel 1
liegt unten, Panel 2 oben darauf, Panel 3 wieder unten. Geschlossen sieht man nur Panel 1
(Cover). Beim ersten Aufklappen erscheinen Panel 2 und Panel 1 nebeneinander; beim vollen
Aufklappen alle 3 Panele (= Front aufgeklappt) und auf der Rückseite Panele 4–6.

**Druckerei-Anweisung:** Z-fold, Falz-Linien gestrichelt im PDF-Preview erkennbar (auf
Falz-Layer mit Spot-Color), Falzweite je 99 mm.

### Layer-Stack (bottom → top)

1. `Hintergrund` — Polygon-Fills (Panel 3 Dunkelgrün-Vollbild)
2. `Bilder` — Logos, Portrait, QR, Wahlkreuz-Image
3. `Text` — alle TextFrames
4. `Falz` — gestrichelte vertikale Linien

## Brand-Hierarchy Contract

| Schicht | Größe | Font | Farbe |
|---|---|---|---|
| Kandidat-Name (Cover) | **24 pt** | Vollkorn Black Italic | Dunkelgrün |
| Slogan (Cover) | 14 pt | Gotham Narrow Bold | Black |
| Teaser-Headline | 18 pt | Gotham Narrow Bold | Dunkelgrün |
| Teaser-Body | 11 pt | Gotham Narrow Book | Black |
| Closer-Headline | 22 pt | Gotham Narrow Bold | White |
| Closer-Datum-Akzent | 14 pt | Vollkorn Black Italic | Gelb |
| Closer-URL | 11 pt | Gotham Narrow Bold | White |
| Thema-Headline | 16 pt | Gotham Narrow Bold | Dunkelgrün |
| Thema-Body | 9 pt | Gotham Narrow Book | Black |
| Kontakt-Headline | 16 pt | Gotham Narrow Bold | Dunkelgrün |
| Kontakt-Body | 10 pt | Gotham Narrow Book | Black |
| Impressum | 6 pt | Gotham Narrow Book | Black |

**Begründung:**

- Kandidat-Name 24 pt ist 8 pt über dem DIN-lang-Mindest (16 pt) — auf 87 mm Cover-Width
  ist ein 12–14-Zeichen-Name in 24 pt Voll-Italic der visuelle Anker.
- Closer-Headline 22 pt auf Dunkelgrün ist 6 pt über dem Mindest. Closer ist die
  letzte Botschaft → groß genug für 1-Sekunden-Lesbarkeit.
- Datum-Akzent 14 pt in Vollkorn-Italic-Gelb auf Dunkelgrün ist die zweite Anker-Hierarchie
  unter dem Closer.
- Thema-Body 9 pt × 87 mm Zeilenbreite → ~70 Zeichen/Zeile. Hart am Lesbarkeits-Limit, aber
  bei Hand-Distanz machbar.

**Whitespace-Rhythmus:**

- Pro Panel 6 mm linke + 6 mm rechte Margin = 87 mm Inhaltsbreite (3 mm Trim-Safety + 3 mm
  Falz-Safety beidseitig).
- Auf Themen-Panele 4–5: 25 mm Spacing zwischen Thema 1 (Body endet ~95 mm) und Thema 2
  (Headline beginnt 105 mm) — visuelle Trennung der Module.

## Print-Hints

```yaml
print_hints:
  bleed_mm: 3
  fold_mm: [99, 198]
  cut_layer: ""
  min_dpi: 300
  paper_recommendation: "Bilderdruck matt 130–170 g/m² (gut für Z-fold)"
  print_method: "Offset (≥ 500) oder Digital (< 500). Maschinelle Falzung empfohlen."
  cmyk_only: true
  fold_type: "Zickzackfalz (Z-fold/accordion)"
  alternative_fold: "Wickelfalz möglich, Spec-Variante (D3)"
```

**Druckerei-Hinweis:** Zickzackfalz ist österreichischer Druckerei-Standard für DIN-lang.
Wickelfalz (= das innere Panel ist ~1 mm schmaler, damit es beim Wickeln passt) ist
alternativ — die Spec liefert Z-fold als Default; eine Wickelfalz-Variante wäre eine
spätere Spec-Erweiterung (D3).

## Mediengesetz §24

Impressum-Slot vorhanden auf Panel 6 (Kontakt-Panel). Default-Text aus
`tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`.

## Messaging-Legality (NRWO §53)

> Closer auf Panel 3 verwendet **„Wähle Grün am 23. Mai"** — Wahlempfehlung, kein
> Anweisungstext. ✅
> Endnutzer:innen MÜSSEN die Formulierung beibehalten oder durch eine andere
> wahlempfehlungs-konforme Formulierung ersetzen.

## Style-Hygiene

`style_ref` referenziert Template-lokale Styles in `meta.yml.ci_overrides.non_ci_styles`:

- `falzflyer/cand-name` (Vollkorn Black Italic 24 pt Dunkelgrün)
- `falzflyer/slogan` (Gotham Narrow Bold 14 pt Black)
- `falzflyer/teaser-headline` (Gotham Narrow Bold 18 pt Dunkelgrün)
- `falzflyer/teaser-body` (Gotham Narrow Book 11 pt linesp 14 Black)
- `falzflyer/closer-headline` (Gotham Narrow Bold 22 pt White)
- `falzflyer/closer-datum` (Vollkorn Black Italic 14 pt Gelb)
- `falzflyer/closer-url` (Gotham Narrow Bold 11 pt White)
- `falzflyer/thema-headline` (Gotham Narrow Bold 16 pt Dunkelgrün)
- `falzflyer/thema-body` (Gotham Narrow Book 9 pt linesp 11 Black)
- `falzflyer/contact-headline` (Gotham Narrow Bold 16 pt Dunkelgrün)
- `falzflyer/contact-body` (Gotham Narrow Book 10 pt linesp 12 Black)

`Impressum` ist bestehender Style.

## Codex-Demo-Image (D11)

Cover (Panel 1) trägt einen Kandidat-Portrait-Slot. Demo-Bild via Codex DALL·E:

```yaml
# templates/kandidat-falzflyer-din-lang/samples/manifest.yml
images:
  - id: kandidat-portrait
    prompt: "Documentary-style portrait photo of a 40s Austrian woman with short brown hair, wearing a green blazer, friendly direct gaze, soft natural light, neutral light-grey backdrop. Vertical 3-quarter portrait, head and shoulders. Natural skin tones. No text overlays. No watermarks."
    output: kandidat-portrait.jpg
    size: 768x1024
```

Wird einmal generiert via `tools/codex_image_gen.py`, JPG committed unter `samples/`,
in der Gallery-Preview-SLA injiziert. Endnutzer:innen ersetzen das Bild mit dem
echten Kandidaten-Portrait beim Anpassen.
