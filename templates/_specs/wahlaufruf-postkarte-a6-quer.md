# Spec: Wahlaufruf-Postkarte A6 quer

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

**Layout-Philosophie:** Symbol-zentriert vorne, Info-Grid hinten.

- **Vorderseite:** Wahlkreuz-Hero auf farbigem Brand-Hintergrund (D12: Dunkelgrün),
  knappe Headline darunter (`Wähle Grün am [Datum]`) — visuell-emotionaler Anker.
- **Rückseite:** 2×2 Info-Grid (4 Kacheln) mit knappen Antworten auf die typischen Fragen
  (`Was wir tun`, `Warum Grün`, `Wann gewählt wird`, `Wo informieren`) plus Impressum.

Die Postkarte ist **nicht** auf eine spezifische Wahl-Kampagne festgelegt; Endnutzer:innen
ersetzen Datum und ggf. Kandidaten-Hinweise.

## Layout — Vorderseite (Page 1, Wahlkreuz-Hero)

```text
   <--------148mm-------->
  +----------------------+   ↑
  | L                    |   |  ← 6 mm top
  |                      |   |
  |   ┌────────────┐     |   |
  |   │            │     |   |
  |   │     WK     │     |   |
  |   │ (Wahlkreuz │     | 105
  |   │  ~55 mm Ø  │     |  mm
  |   │  auf       │     |   |
  |   │  Dunkel-   │     |   |
  |   │  grün-     │     |   |
  |   │  Polygon)  │     |   |
  |   └────────────┘     |   |
  |                      |   |
  | H1: Wähle Grün am    |   |
  |     23. Mai          |   |
  |                      |   ↓
  +----------------------+

Legende:
  L  = Logo Grüne (weiss, oben links)
  WK = Wahlkreuz auf Dunkelgrün-Polygon (D12)
  H1 = Headline "Wähle Grün am [Datum]"
```

## Layout — Rückseite (Page 2, 2×2 Info-Grid)

```text
   <--------148mm-------->
  +----------------------+   ↑
  | L                    |   |  ← 6 mm top
  | +-----------------+  |   |
  | |C1 Hd  | C2 Hd   |  |   |
  | |       |         |  |   |
  | |C1 Body| C2 Body |  |   |  2x2 Grid:
  | |       |         |  |   |  C1 = Was wir tun
  | +-----------------+  | 105|  C2 = Warum Grün
  | |C3 Hd  | C4 Hd   |  | mm |  C3 = Wann gewählt wird
  | |       |         |  |   |  C4 = Wo informieren
  | |C3 Body| C4 Body |  |   |
  | |       |         |  |   |
  | +-----------------+  |   |
  |                      |   |
  | I (Impressum)        |   |
  +----------------------+   ↓

Legende:
  L  = Logo Grüne (links oben, klein)
  C1-C4 = Cell mit Headline + Body
  I  = Impressum (full-width Strip, ≥6 pt)
```

## Constraints

- **Coordinate-Origin:** Trim-Top-Left.
- **Trim:** 148 × 105 mm. **Bleed 3 mm** allseitig.
- **Margin:** 6 mm allseitig (knapp wegen kleinem Format), 5 mm Seiten-Innen-Abstand bei 2×2-Grid.
- **Wahlkreuz-Größe:** 55 mm × 55 mm (D12: Dunkelgrün-Background, padding 4 mm).
- **Headline ≥ 22 pt** (P-PRINT-5 / SCHEMA.md A6-Mindest); empfohlen 24 pt.
- **Cell-Headline ≥ 14 pt**; empfohlen 14 pt.
- **Body ≥ 9 pt**; empfohlen 9 pt.
- **Impressum ≥ 5 pt**; empfohlen 6 pt.
- **Background Vorderseite:** Dunkelgrün (Vollbild). Rückseite: Weiß (Lesbarkeit für Body).

## Slot-Tabelle — Vorderseite (Page 1)

| anname                       | type             | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref                          | example                                    |
|------------------------------|------------------|------|------|------|------|-----------|------------------------------------|--------------------------------------------|
| Seitenhintergrund (front)    | Polygon          |  -3  |  -3  | 154  | 111  | Dunkelgrün| —                                  | Vollbild Vorderseite                       |
| Logo Grüne (weiss)           | ImageFrame       |   6  |   6  |  35  |  10  | —         | shared/logos/gruene-weiss.png      | (verwende shared/logos/gruene-weiss.png)   |
| Wahlkreuz                    | Block:WahlkreuzSymbol| 47 | 16  |  55  |  55  | —         | —                                  | (Wahlkreuz auf Dunkelgrün-Polygon)         |
| Headline-Wahlaufruf          | TextFrame        |  10  |  78  | 128  |  20  | White     | wahlaufruf/headline                | Wähle Grün am 23. Mai                      |

## Slot-Tabelle — Rückseite (Page 2)

| anname                       | type      | x_mm | y_mm | w_mm | h_mm | fcolor   | style_ref                       | example                                              |
|------------------------------|-----------|------|------|------|------|----------|---------------------------------|------------------------------------------------------|
| Logo Grüne (cmyk)            | ImageFrame|   6  |   6  |  30  |   9  | —        | shared/logos/gruene-cmyk.png    | (verwende shared/logos/gruene-cmyk.png)              |
| Cell 1 — Headline            | TextFrame |   6  |  22  |  68  |   8  | Dunkelgrün| wahlaufruf/cell-headline       | Was wir tun                                          |
| Cell 1 — Body                | TextFrame |   6  |  31  |  68  |  30  | Black    | wahlaufruf/cell-body            | Klimaschutz, leistbares Wohnen, Bildung — konkret in deiner Gemeinde. |
| Cell 2 — Headline            | TextFrame |  78  |  22  |  64  |   8  | Dunkelgrün| wahlaufruf/cell-headline       | Warum Grün                                           |
| Cell 2 — Body                | TextFrame |  78  |  31  |  64  |  30  | Black    | wahlaufruf/cell-body            | Mut zur Veränderung. Faktenbasiert. Generationen­gerecht. |
| Cell 3 — Headline            | TextFrame |   6  |  62  |  68  |   8  | Dunkelgrün| wahlaufruf/cell-headline       | Wann gewählt wird                                    |
| Cell 3 — Body                | TextFrame |   6  |  71  |  68  |  20  | Black    | wahlaufruf/cell-body            | Sonntag, 23. Mai 2026, 7–17 Uhr.                     |
| Cell 4 — Headline            | TextFrame |  78  |  62  |  64  |   8  | Dunkelgrün| wahlaufruf/cell-headline       | Wo informieren                                       |
| Cell 4 — Body                | TextFrame |  78  |  71  |  64  |  20  | Black    | wahlaufruf/cell-body            | gruene-noe.at · Tel. 02742 / 90 230                  |
| Impressum                    | TextFrame |   6  |  96  | 136  |   6  | Black    | Impressum                       | Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten. |

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
    w_mm: 35
    h_mm: 10
    fcolor: ""
    style_ref: "shared/logos/gruene-weiss.png"
    example: ""
  - anname: "Wahlkreuz"
    type: "Block:WahlkreuzSymbol"
    x_mm: 47
    y_mm: 16
    w_mm: 55
    h_mm: 55
    fcolor: ""
    style_ref: ""
    example: "Wahlkreuz auf Dunkelgrün-Polygon, padding 4mm"
  - anname: "Logo Grüne (cmyk)"
    type: ImageFrame
    x_mm: 6
    y_mm: 6
    w_mm: 30
    h_mm: 9
    fcolor: ""
    style_ref: "shared/logos/gruene-cmyk.png"
    example: ""
  - anname: "Headline-Wahlaufruf"
    type: TextFrame
    x_mm: 10
    y_mm: 78
    w_mm: 128
    h_mm: 20
    fcolor: "White"
    style_ref: "wahlaufruf/headline"
    example: "Wähle Grün am 23. Mai"
  - anname: "Cell 1 — Headline"
    type: TextFrame
    x_mm: 6
    y_mm: 22
    w_mm: 68
    h_mm: 8
    fcolor: "Dunkelgrün"
    style_ref: "wahlaufruf/cell-headline"
    example: "Was wir tun"
  - anname: "Cell 1 — Body"
    type: TextFrame
    x_mm: 6
    y_mm: 31
    w_mm: 68
    h_mm: 30
    fcolor: "Black"
    style_ref: "wahlaufruf/cell-body"
    example: "Klimaschutz, leistbares Wohnen, Bildung — konkret in deiner Gemeinde."
  - anname: "Cell 2 — Headline"
    type: TextFrame
    x_mm: 78
    y_mm: 22
    w_mm: 64
    h_mm: 8
    fcolor: "Dunkelgrün"
    style_ref: "wahlaufruf/cell-headline"
    example: "Warum Grün"
  - anname: "Cell 2 — Body"
    type: TextFrame
    x_mm: 78
    y_mm: 31
    w_mm: 64
    h_mm: 30
    fcolor: "Black"
    style_ref: "wahlaufruf/cell-body"
    example: "Mut zur Veränderung. Faktenbasiert. Generationen­gerecht."
  - anname: "Cell 3 — Headline"
    type: TextFrame
    x_mm: 6
    y_mm: 62
    w_mm: 68
    h_mm: 8
    fcolor: "Dunkelgrün"
    style_ref: "wahlaufruf/cell-headline"
    example: "Wann gewählt wird"
  - anname: "Cell 3 — Body"
    type: TextFrame
    x_mm: 6
    y_mm: 71
    w_mm: 68
    h_mm: 20
    fcolor: "Black"
    style_ref: "wahlaufruf/cell-body"
    example: "Sonntag, 23. Mai 2026, 7–17 Uhr."
  - anname: "Cell 4 — Headline"
    type: TextFrame
    x_mm: 78
    y_mm: 62
    w_mm: 64
    h_mm: 8
    fcolor: "Dunkelgrün"
    style_ref: "wahlaufruf/cell-headline"
    example: "Wo informieren"
  - anname: "Cell 4 — Body"
    type: TextFrame
    x_mm: 78
    y_mm: 71
    w_mm: 64
    h_mm: 20
    fcolor: "Black"
    style_ref: "wahlaufruf/cell-body"
    example: "gruene-noe.at · Tel. 02742 / 90 230"
  - anname: "Impressum"
    type: TextFrame
    x_mm: 6
    y_mm: 96
    w_mm: 136
    h_mm: 6
    fcolor: "Black"
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten."
```

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

`shared/assets/wahlkreuz.png` ist ein RGBA-PNG (1200×1299, gelbes Kreuz im weißen Kreis,
Alpha-Channel außerhalb des Kreises). Für Scribus als `inline_image_data` mit `qCompress`-
Encoding eingebettet (Helper `pack_inline_image` in
`tools/sla_lib/builder/primitives.py`). Der `WahlkreuzSymbol`-DSL-Block kapselt das alles
inkl. Background-Polygon-Fill (D12).

## Background-Color Contract für Wahlkreuz (D12)

> **Der Wahlkreuz MUSS auf farbigem Brand-Hintergrund stehen — `Dunkelgrün`, `Hellgrün`,
> oder `Magenta`. NIE auf Weiß. NIE auf Gelb.**
>
> Begründung: Das Asset ist ein gelbes Kreuz in einem weißen Kreis (PNG mit Alpha-Channel,
> RGBA 1200×1299). Der weiße Kreis ist die Schutzhülle, die den Symbolcharakter ausmacht
> ("geschützter Wahlakt im Kreis"). Auf weißem Hintergrund verschwindet der Kreis und nur
> das gelbe Kreuz bleibt — der Symbolcharakter geht verloren. Auf gelbem Hintergrund
> verschwindet das Kreuz.

**Diese Spec wählt `Dunkelgrün`** als Background. Begründung: Brand-Primary-Farbe,
maximaler Kontrast zum gelben Kreuz, Konsistenz mit Postkarte-Vorderseite (auch
Dunkelgrün-Vollbild).

`WahlkreuzSymbol`-Block enforced D12: bei `background_color="White"` oder `"Gelb"` wirft
`emit()` ein `ValueError`.

## Falz / Stanze

Keine.

## Brand-Hierarchy Contract

| Schicht | Größe | Font | Farbe |
|---|---|---|---|
| Headline-Wahlaufruf | **24 pt** | Gotham Narrow Bold | White (auf Dunkelgrün) |
| Cell-Headline | 14 pt | Gotham Narrow Bold | Dunkelgrün (auf Weiß) |
| Cell-Body | 9 pt | Gotham Narrow Book | Black |
| Impressum | 6 pt | Gotham Narrow Book | Black |

**Begründung:**

- 24 pt Headline ist 2 pt über dem A6-Mindest (22 pt). 128 mm Zeilenbreite × 24 pt → ~10–12
  Wörter pro Zeile, ideal für „Wähle Grün am [Datum]".
- 14 pt Cell-Headline / 9 pt Cell-Body — Verhältnis 1.55, klare Hierarchie.
- 2×2-Grid (NICHT 3×2 oder 2×3 wegen P-A6QUER-1: 3 Spalten auf 148 mm × 9 pt = ~14
  Zeichen/Zeile, zu eng für sinnvollen Body).

**Whitespace-Rhythmus:**

- Vorderseite: Wahlkreuz 16–71 mm, Headline 78 mm — 7 mm Atempause zwischen Symbol und
  Wort, lässt das Symbol „atmen".
- Rückseite: 4 Cells je 70 × 39 mm, 2 mm Gutter horizontal + 2 mm Gutter vertikal.
  Ausreichend für visuelle Trennung, ohne Layout zerfetzt wirken zu lassen.

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

> NRWO §53 verbietet die direkte Wahlanleitung. Erlaubt: „Wähle Grün am [Datum]".
> Verboten: „Mach dein Kreuz bei den Grünen", „Kreuze hier".

Diese Spec verwendet **„Wähle Grün am 23. Mai"** — formal eine Wahlempfehlung, kein
Anweisungstext. Endnutzer:innen MÜSSEN diesen Text beim Anpassen beibehalten oder
durch eine andere wahlempfehlungs-konforme Formulierung ersetzen.

## Style-Hygiene

`style_ref` referenziert Template-lokale Styles in `meta.yml.ci_overrides.non_ci_styles`:

- `wahlaufruf/headline` (Gotham Narrow Bold 24 pt White)
- `wahlaufruf/cell-headline` (Gotham Narrow Bold 14 pt Dunkelgrün)
- `wahlaufruf/cell-body` (Gotham Narrow Book 9 pt Black)

`Impressum` ist bestehender Style (Postkarte-Konvention).

## Codex-Demo-Image (D11)

Optional. Diese Spec lässt die Vorderseite reine Symbol+Headline-Komposition (kein
Hero-Bild). Falls eine spätere Iteration ein Hero-Bild auf der Rückseite einsetzen will
(z.B. ein Community-Foto neben dem 2×2-Grid), kann ein Codex-DALL·E-Demo-Bild über das
Manifest unter `templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml` erzeugt
werden. Im Default-Bauchschritt **kein** Demo-Bild — Layout funktioniert ohne.
