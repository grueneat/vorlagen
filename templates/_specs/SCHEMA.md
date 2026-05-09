# Template-Spec-Schema

**Status:** Living document. Updated when a real template forces a revision.
**Audience:** Implementer:innen (Mensch oder LLM), die ein neues Template aus einer Spec
bauen, ohne Rückfragen stellen zu müssen.

Eine *Spec* (in `templates/_specs/<slug>.md`) beschreibt **visuelle Komposition** so präzise,
dass zwei verschiedene Implementer:innen das gleiche Template bauen würden. Sie ist
Vertrag zwischen Brand/Design und Build (D3): nach Gate-1-Konsens dürfen Abweichungen nur
mit Spec-Update + Reviewer-Sign-off passieren. Drift wird mechanisch durch
`tools/spec_check.py` erkannt.

Format: **Markdown mit eingebettetem YAML**. Maschinen-parsbar (YAML in fenced
` ```yaml `-Block) plus Mensch-lesbarer Prosa-Sektionen.

---

## 1. Pflichtfelder

Jede Spec MUSS folgende Felder enthalten — entweder als Markdown-Headings oder als
Schlüssel im eingebetteten YAML-Block. Reihenfolge frei, aber alle Felder vorhanden.

| Schlüssel | Typ | Beschreibung |
|---|---|---|
| `id` | string | Slug, identisch zu Verzeichnisname (`themen-plakat-a3-quer`) |
| `title` | string | Mensch-lesbarer Titel (`Themen-Plakat A3 quer`) |
| `format` | string | Format-Kürzel + Orientierung (`A3 quer 1-seitig`) |
| `trim_mm` | `[w, h]` | Trim-Maße in mm |
| `bleed_mm` | int | Bleed (Anschnitt) auf jeder Seite in mm (typisch 3, Stanzen 2) |
| `pages` | int | Anzahl logischer Seiten (Vorder/Rückseite = 2) |
| `fold_type` | enum | `none` \| `wickelfalz` \| `zickzackfalz` \| `altarfalz` \| `tent` |
| `fold_positions_mm` | list | Fold-Linien in mm vom Trim-Origin (leer wenn `fold_type=none`) |
| `cut_type` | enum | `none` \| `die-cut` (Stanzkontur erforderlich) |
| `audience` | list | Zielgruppen (`bezirksgruppe`, `landesgruppe`, `kandidat`, …) |
| `layout_philosophy` | text | 2–4 Sätze, freie Prosa, **was** das Template vermittelt |
| `slots` | list | Strukturierte Slot-Tabelle (siehe §4) |
| `eps_strategy` | object | Wahlkreuz-Embedding-Details (leer wenn nicht verwendet) |
| `print_hints` | object | Bleed, Falz, Min-DPI, Papier, Stanzkontur-Naming-Variants |

---

## 2. Audience und Layout-Philosophie

Freie deutsche Prosa, 2–4 Sätze. Beantwortet:

- **Wer** nutzt das Template (Bezirksgruppe, Kandidat:in, Infostand-Helfer:in, …)?
- **Wann** und **wo** kommt es zum Einsatz (Wahlkampf-Endspurt, Türkampagne, Einkaufszone, …)?
- **Welche** Botschaft trägt es (eine konkrete Hauptbotschaft + 2–3 unterstützende)?
- **Warum** genau diese Layout-Klasse (z.B. „Wahltag-Türanhänger braucht Stanzkontur weil
  Türklinke + sehr schmaler Aufmerksamkeits-Korridor")?

Kein Marketing-Sprech. Konkret bleiben.

---

## 3. ASCII-Layout-Konvention

**Eine ASCII-Skizze pro sichtbarer Seite** (Vorder+Rückseite, oder bei Falzflyer alle
Panele beider Seiten + Falz-Schema). Zweck: Reviewer:innen erkennen Layout-Hierarchie und
Komposition auf einen Blick — auch ohne Renderer.

### Konventionen

- **Box-Drawing-Zeichen** für Frame-Outlines: `+`, `-`, `|` reichen aus (kein Unicode-Box-Drawing
  zwingend, aber erlaubt: `┌`, `─`, `│`, `└`, `┐`, `┘`).
- **Maße** als Beschriftung außen am Layout: `<-148mm->` für Breite, `↕105mm` für Höhe.
- **Slot-Marker** im Layout: 1–3-Buchstaben-Codes mit Legende darunter.
  - `H1` = Hauptheadline, `H2` = Sub-Headline, `B` = Body, `I` = Impressum, `L` = Logo,
    `WK` = Wahlkreuz, `Q` = QR-Code, `F` = Falzlinie (gestrichelt darstellen mit `- - -`),
    `S` = Stanzkontur (mit `+- - +` umrahmen).
- **Coordinate-Origin = Trim-Top-Left** (NICHT Bleed-Corner). Diese Konvention ist
  verbindlich, um P-PRINT-2 (Falz-Origin-Verwirrung) zu vermeiden. Alle Slot-Koordinaten in
  der Slot-Tabelle und alle Falz/Stanz-Positionen sind absolute mm vom Trim-Top-Left.

### Worked Example

Postkarte A6 hochformat, Rückseite (so sieht eine Skizze aus):

```text
   <-------------105mm------------->
  +---------------------------------+   ↑
  | L                       |   I   |   |
  |   +-------------------+ |       |   |
  |   |       H1          | |       |   |
  |   |   (4-zeilig)      | |       |   |
  |   +-------------------+ |       | 148
  |   +-------------------+ |  ST   |  mm
  |   |        B          | |       |   |
  |   |   (Erklärtext)    | |       |   |
  |   +-------------------+ |       |   |
  | I (Impressum-Strip)              |   ↓
  +---------------------------------+

Legende:
  H1 = Headline 4-zeilig (Brand-Wechselfarbe)
  B  = Erklärtext Rückseite
  L  = Logo Grüne (weiss, oben links)
  ST = Störer-Text 3-zeilig (Magenta-Kreis)
  I  = Impressum
```

Die Skizze ist **schematisch**, kein pixelgenauer Mock. Verhältnisse sollen stimmen,
exakte Maße kommen aus der Slot-Tabelle.

---

## 4. Slot-Tabelle

**Markdown-Tabelle** mit den folgenden Spalten in dieser Reihenfolge. Eine Zeile pro Slot.

| Spalte | Pflicht | Beschreibung |
|---|---|---|
| `anname` | ja | Frame-`ANNAME` im SLA, identisch zu `meta.yml.slots.<key>.anname`. UTF-8 OK. |
| `type` | ja | `TextFrame` \| `ImageFrame` \| `Polygon` \| `Block:<Name>` |
| `x_mm` | ja | X in mm vom Trim-Top-Left |
| `y_mm` | ja | Y in mm vom Trim-Top-Left (positiv = nach unten) |
| `w_mm` | ja | Breite in mm |
| `h_mm` | ja | Höhe in mm |
| `fcolor` | nein | Vorder/Füll-Farbe; verweist auf `shared/ci.yml`-Color (`Dunkelgrün`, `Hellgrün`, `Magenta`, `Gelb`, `White`, `Black`) |
| `style_ref` | nein | Para-/Char-Style-Name (`Headline sehr wichtig`, `Fließtext`, `Impressum`, …) — referenziert `shared/ci.yml.styles` oder dokumentiert lokal |
| `example` | ja | Realistischer Inhalt (kein Lorem) — wird so in `meta.yml.slots.<key>.example` übernommen |

### Empfohlenes Pattern

Slot-Tabelle einmal pro Seite (bei mehrseitigen Templates). Entscheidend ist die
**Eins-zu-Eins-Verbindung** zur `meta.yml`: jede Slot-Zeile hat ein Pendant in
`meta.yml.slots.<key>` (gleicher `anname`). `tools/spec_check.py` validiert mechanisch.

### Eingebetteter YAML-Block

Zusätzlich zur Markdown-Tabelle ein YAML-Block mit identischen Daten — maschinen-parsbar
durch `tools/spec_check.py`:

```yaml
slots:
  - anname: "Headline 4-zeilig"
    type: TextFrame
    x_mm: 14
    y_mm: 30
    w_mm: 77
    h_mm: 70
    fcolor: White
    style_ref: "Headline sehr wichtig"
    example: "Klimaschutz ist Wirtschaftspolitik"
  - anname: "Logo Grüne (weiss)"
    type: ImageFrame
    x_mm: 5
    y_mm: 5
    w_mm: 25
    h_mm: 8
    style_ref: "shared/logos/gruene-weiss.png"
    example: ""
```

Wenn die Tabelle und der YAML-Block divergieren: YAML ist die maschinen-parsbare Wahrheit.
Tabelle ist Mensch-lesbarer Spiegel — beide sollten übereinstimmen, das Spec-Format
toleriert minimale Whitespace-Diffs.

---

## 5. EPS / Image-Embedding-Strategie

**Nur erforderlich** für Templates mit Wahlkreuz oder anderen eingebetteten Pixel-Assets.

### YAML-Schlüssel

```yaml
eps_strategy:
  asset_path: "shared/assets/wahlkreuz.png"
  scale_type: 0          # 0 = free / aspect-locked, 1 = fit-to-frame
  background_color: "Dunkelgrün"   # MUST be a colored brand color (D12)
  background_padding_mm: 4.0
  encoding: "qcompress"  # Scribus inline ImageData format
  helper: "pack_inline_image"
```

### Hard rule (D12 — Wahlkreuz-Background-Color)

> Der Wahlkreuz-Asset zeigt ein **gelbes Kreuz in einem weißen Kreis**. Der weiße Kreis
> verschwindet auf weißem Hintergrund, das gelbe Kreuz verschwindet auf gelbem
> Hintergrund. Daher MUSS der Wahlkreuz auf farbigem Brand-Hintergrund platziert werden:
> **`Dunkelgrün`, `Hellgrün`, oder `Magenta`**. **Nie auf Weiß. Nie auf Gelb.**
>
> Das `WahlkreuzSymbol`-DSL-Block enforced diese Regel: bei `background_color="White"`
> oder `background_color="Gelb"` wirft `WahlkreuzSymbol.emit()` ein `ValueError`.
> `tools/visual_review.py` Gate-3-Prompt prüft diese Regel als Blocking-Finding.

### Helper-Pattern

Inline-PNG-Bytes für Scribus müssen als `qCompress` encodiert sein:
`base64( 4-byte big-endian length prefix + zlib_compress(image_bytes) )`. Naive Base64
führt zu `qUncompress: Z_DATA_ERROR` und macht das SLA un-öffenbar.

Verwendung:

```python
from sla_lib.builder.primitives import pack_inline_image, ImageFrame

bytes_ = open("shared/assets/wahlkreuz.png", "rb").read()
data, ext = pack_inline_image(bytes_, "png")
page.add(ImageFrame(
    x_mm=..., y_mm=..., w_mm=..., h_mm=...,
    inline_image_data=data,
    inline_image_ext=ext,
    scale_type=0,
))
```

`WahlkreuzSymbol`-Block kapselt das alles inkl. Background-Polygon-Fill.

---

## 6. Background-Color Contract für Wahlkreuz

**Verbindliche Regel (D12), in jeder Wahlkreuz-Spec wörtlich zu reproduzieren:**

> **Der Wahlkreuz MUSS auf farbigem Brand-Hintergrund stehen — `Dunkelgrün`, `Hellgrün`,
> oder `Magenta`. NIE auf Weiß. NIE auf Gelb.**
>
> Begründung: Das Asset ist ein gelbes Kreuz in einem weißen Kreis (PNG mit Alpha-Channel,
> RGBA 1200×1299). Der weiße Kreis ist die Schutzhülle, die den Symbolcharakter ausmacht
> ("geschützter Wahlakt im Kreis"). Auf weißem Hintergrund verschwindet der Kreis und nur
> das gelbe Kreuz bleibt — der Symbolcharakter geht verloren. Auf gelbem Hintergrund
> verschwindet das Kreuz.
>
> Default des `WahlkreuzSymbol`-DSL-Blocks: `background_color="Dunkelgrün"`,
> `background_padding_mm=4.0`. Andere Farben sind erlaubt, aber müssen in der Spec
> begründet sein (z.B. „Falzflyer-Closer-Panel auf Hellgrün passt zum Cover-Magenta").

---

## 7. Falz / Stanze — Konventionen

### Coordinate-Origin

**Trim-Top-Left**, NICHT Bleed-Corner. Falz- und Stanz-Positionen sind absolute mm vom
Trim-Top-Left. Auf einer 297×210 mm A4-quer-Seite mit 3 mm Bleed beginnt das Trim bei
(0,0); der Bleed reicht von (-3,-3) bis (300,213). Eine horizontale Falzlinie auf
y=105 mm liegt im Trim-Bereich, NICHT auf Bleed-Mitte.

### Spot-Colors — Document-Local (D4 revised)

Falz und Stanzkontur sind **per-Template**, NICHT in `shared/ci.yml`. Begründung: das
Hinzufügen von `Falz`/`Stanzkontur` zu `shared/ci.yml` würde `tools/check_ci.py` für die
drei bestehenden Templates auf rot setzen (sie haben diese Farben nicht im SLA → CI-Drift).

Pattern in `build.py`:

```python
doc = Document(
    title="...",
    template_id="...",
    layers=[
        DocumentLayer(name="Hintergrund", printable=True, flow=True),
        DocumentLayer(name="Bilder",      printable=True, flow=True),
        DocumentLayer(name="Text",        printable=True, flow=True),
        DocumentLayer(name="Falz",        printable=False, flow=False),    # nicht im Druck
        DocumentLayer(name="Stanzkontur", printable=False, flow=False),
    ],
)
doc.add_color("Falz",        cmyk=(100, 0, 0, 0), spot=True)   # document-local
doc.add_color("Stanzkontur", cmyk=(0, 100, 0, 0), spot=True)
```

In `meta.yml.ci_overrides`:

```yaml
ci_overrides:
  non_ci_colors:
    - "Falz"
    - "Stanzkontur"
```

### Layer-Stack (bottom → top)

Die Render-Reihenfolge ist **bottom-to-top**:

1. `Hintergrund` — Polygon-Fills, Vollbild-Farbflächen
2. `Bilder` — alle ImageFrames (inkl. Wahlkreuz)
3. `Text` — alle TextFrames
4. `Falz` — gestrichelte Falzlinien (nicht-druckbar, exportierbar)
5. `Stanzkontur` — geschlossene Stanz-Pfade (nicht-druckbar, exportierbar)

Falz und Stanzkontur werden auf der Druckerei-PDF als Spot-Color-Pfade sichtbar; in der
finalen Druckung erscheinen sie nicht (PRINTABLE=0), aber die Druckerei sieht sie zur
Schneid-/Falz-Anweisung.

---

## 8. Brand-Hierarchy Contract

Typografie-/Whitespace-/Color-Regeln, die jede Spec einhalten muss. Ziel: **mindestens
auf Augenhöhe** mit den drei bestehenden Templates (Postkarte A6, Plakat A1, Zeitung A4).

### Mindest-Schriftgrößen

| Format | H1 (Headline) | H2 (Sub) | Body | Impressum |
|---|---|---|---|---|
| A6 (alle Orientierungen) | ≥ 22 pt | ≥ 14 pt | ≥ 9 pt | ≥ 5 pt |
| DIN-lang Falzflyer (99 mm Panel) | ≥ 16 pt | ≥ 12 pt | ≥ 9 pt | ≥ 5 pt |
| A5 Tent-Card (297 mm × 105 mm Panel) | ≥ 28 pt (Tisch-Distanz!) | ≥ 16 pt | ≥ 14 pt | ≥ 5 pt |
| A4 Zeitung | ≥ 20 pt | ≥ 14 pt | ≥ 11 pt | ≥ 5 pt |
| A3 Plakat | ≥ 36 pt | ≥ 18 pt | ≥ 11 pt | ≥ 5 pt |
| A1 Plakat | ≥ 80 pt (Distanz!) | ≥ 40 pt | ≥ 16 pt | ≥ 5 pt |
| Türanhänger 105×250 | ≥ 22 pt | ≥ 14 pt | ≥ 9 pt | ≥ 5 pt |

### Color-Palette

Nur `shared/ci.yml`-Farben:
- `Dunkelgrün` (Brand-Primary)
- `Hellgrün` (Brand-Secondary)
- `Gelb` (Brand-Accent — als Highlight, nie als großflächiger Hintergrund mit Gelb-Text)
- `Magenta` (Brand-Stoerer — sparsam, max. 1 Stoerer pro Layout)
- `White` (Text auf Dunkelgrün, oder Hintergrund-Insel)
- `Black` (selten — für Body auf hellem Untergrund)

Non-CI-Farben (z.B. `Falz`, `Stanzkontur`) MÜSSEN über `meta.yml.ci_overrides.non_ci_colors`
mit kurzer Begründung dokumentiert sein.

### Whitespace-Rhythmus

- Mindestens **5 mm** zwischen Headline und Body.
- Mindestens **3 mm** Margin zur Trim-Kante (besser 14 mm außer am sehr knappen Türanhänger).
- Mindestens **2 mm** Abstand zwischen jedem nicht-Stoerer-Frame.
- Bei Stanzungen: **2 mm Safety-Zone** zwischen Stanzkontur und erstem Inhalts-Pixel.

### Style-Hygiene

`shared/ci.yml`-Styles standardmäßig nutzen. Lokale Styles (z.B. `Headline sehr wichtig`,
das aus dem Original-Postkarten-SLA stammt) gelten als legitim wenn in
`meta.yml.ci_overrides.non_ci_styles` mit Begründung dokumentiert.

---

## 9. Print-Hints

```yaml
print_hints:
  bleed_mm: 3                     # Stanzungen: 2 mm tighter
  fold_mm: [99, 198]              # leer wenn fold_type=none
  cut_layer: "Stanzkontur"        # leer wenn cut_type=none; Druckerei-Variante: CutContour
  min_dpi: 300                    # für eingebettete Pixel-Bilder
  paper_recommendation: "Bilderdruck matt 170 g/m²"
  print_method: "Offset (≥ 250 Stück) oder Digital (< 250)"
  stanz_naming_variants:          # Alternativ-Names der Druckerei-Spot-Color
    - "Stanzkontur"               # DACH default
    - "CutContour"                # International / Pantone-shop
```

### Mediengesetz §24

Jedes Druck-Erzeugnis (außer rein interne Dokumente) braucht einen **Impressum-Block**:
Medieninhaber + Herausgeber + Druckerei. Die Spec muss einen Impressum-Slot haben.

Default-Text steht in `tools/sla_lib/builder/blocks.py::DEFAULT_IMPRESSUM`. Templates können
eigenen Text liefern; für die Spec-Beispiele bitte den Default + Hinweis auf
„von Endnutzer:in zu ergänzen / anzupassen" verwenden.

---

## 10. Messaging-Legality (Wahlaufruf-Templates)

**NRWO §53** verbietet die direkte „Wahlanleitung" („Mach dein Kreuz bei den Grünen") als
direktiven Aufruf. Erlaubt: Kandidaten-Information, Themen-Plakate, persönliche
Wahlempfehlungen mit „Ich/Wir wählen Grün". Verboten: parteilicher Aufruf, der eine
Wahlanleitung suggeriert.

Daher:

- **VERMEIDE** in Beispieltexten: „Mach dein Kreuz bei den Grünen", „Kreuze hier",
  „Stimm für ...".
- **VERWENDE**: „Wähle Grün am [Datum]", „Am [Datum] zur Wahl", „Themen die zählen".
- Spec muss diesen Hinweis im Wahlkreuz-Slot-Beispiel referenzieren.

---

## 11. Drift-Policy (D3)

Die Spec ist **Vertrag**. Nach Gate-1-Konsens dürfen Implementierung und Spec nur durch
Spec-Update + Reviewer-Sign-off auseinanderlaufen.

`tools/spec_check.py SLUG` vergleicht mechanisch:

- Slot-`anname` aus YAML ↔ `meta.yml.slots.<key>.anname` ↔ SLA `PAGEOBJECT/@ANNAME`.
- Slot-`x_mm/y_mm/w_mm/h_mm` aus YAML ↔ SLA-Frame-Position.
- Slot-`fcolor` aus YAML ↔ SLA `PCOLOR`/`PCOLOR2`.

### Toleranz und Severity-Buckets (Issue #12 D8)

Default-Toleranz: **0.5 mm** (vorher 0.1 mm). Drift wird in drei Buckets klassifiziert:

| Drift-Magnitude | Severity | Verhalten |
|---|---|---|
| `< 0.05 mm` | silent | Nicht gemeldet (Sub-Pixel-Float-Rauschen) |
| `0.05 mm <= d <= tolerance` | info | Geloggt mit `info:`-Präfix, exit 0 |
| `d > tolerance` | error | Geloggt mit `error:`-Präfix, exit 1 |

Hintergrund: Bei Build-Loop-Refinements (Heuristik-Tuning, Style-Adjustments) entstehen
oft 0.1–0.4 mm-Drifts ohne visuellen Effekt — die alte 0.1 mm-Schwelle erzeugte
CI-Noise. Die 0.5 mm-Schwelle entspricht dem typografischen Auflösungsvermögen bei
A4-Druck und tolerierter Position-Genauigkeit der meisten Druckereien.

Legacy-Verhalten: `python3 tools/spec_check.py --tolerance-mm 0.1` reaktiviert die alte
0.1 mm-Schwelle für Build-Loop-Refinement-Phasen.

### Float-Slot-Positions

Spec-`slots.<i>.x_mm/y_mm/w_mm/h_mm` akzeptieren **Floats mit 1 Nachkommastelle**, z.B.
`x_mm: 12.5`. Legacy-`int`-Werte (z.B. `x_mm: 12`) bleiben gültig — der YAML-Parser
coerce'd in beide Richtungen.

Wenn Spec und SLA divergieren: `spec_check.py` exit 1 nur bei error-Bucket-Drifts;
info-Bucket-Drifts sind im CI-Run "PASS mit info:". Bei legitimem
Implementierungs-Finding („Slot zu eng für realistischen Text") wird die Spec
aktualisiert und der Spec-Check re-validiert.

### Escape-Hatch

SLA-Frames mit `anname` beginnend mit `internal:` oder `_` werden von `spec_check.py`
ignoriert. Das ist die Konvention für DSL-interne Helper-Frames (z.B. ein zusätzliches
`internal:bg-fill` das `WahlkreuzSymbol` als Hintergrund-Polygon emittiert), die in der
Spec nicht als reguläre Slots aufgeführt werden müssen.

---

## Worked Example — Slot-Tabelle einer minimalen Spec

```text
| anname             | type      | x_mm | y_mm | w_mm | h_mm | fcolor    | style_ref            | example                                      |
|--------------------|-----------|------|------|------|------|-----------|----------------------|----------------------------------------------|
| Headline-4-zeilig  | TextFrame |  14  |  30  |  77  |  70  | White     | Headline sehr wichtig| Klimaschutz ist Wirtschaftspolitik           |
| Logo Grüne (weiss) | ImageFrame|   5  |   5  |  25  |   8  | —         | shared/logos/...     | (verwende shared/logos/gruene-weiss.png)     |
| Impressum          | TextFrame |  14  | 130  |  77  |  10  | White     | Impressum            | Medieninhaber: Die Grünen NÖ, Daniel-Gran-Str|
```

Mit eingebettetem YAML:

```yaml
slots:
  - anname: "Headline-4-zeilig"
    type: TextFrame
    x_mm: 14
    y_mm: 30
    w_mm: 77
    h_mm: 70
    fcolor: White
    style_ref: "Headline sehr wichtig"
    example: "Klimaschutz ist Wirtschaftspolitik"
  - anname: "Logo Grüne (weiss)"
    type: ImageFrame
    x_mm: 5
    y_mm: 5
    w_mm: 25
    h_mm: 8
    style_ref: "shared/logos/gruene-weiss.png"
    example: ""
  - anname: "Impressum"
    type: TextFrame
    x_mm: 14
    y_mm: 130
    w_mm: 77
    h_mm: 10
    fcolor: White
    style_ref: "Impressum"
    example: "Medieninhaber: Die Grünen NÖ, Daniel-Gran-Straße 48, 3100 St. Pölten"
```

---

## Anti-Patterns (woran man eine schlechte Spec erkennt)

- **Lorem ipsum als Beispiel** — keine realistische Textlänge → Slots zu eng/groß im Build.
- **Keine ASCII-Skizze** — Reviewer:innen müssen die Spec im Kopf rendern.
- **„Centered" ohne mm-Koordinaten** — was heißt zentriert auf 105 mm × 250 mm Türanhänger
  mit Loch?
- **Wahlkreuz-Spec ohne D12-Referenz** — ein wahrscheinlicher Build-Fehler.
- **Falz/Stanze ohne Layer-Stack-Order** — Druckerei kann Stanzkontur nicht trennen.
- **Mehrere Stoerer in einem Layout** — Magenta soll Aufmerksamkeit ziehen, nicht teilen.
- **Body-Text < 9 pt** — auch Distanz-erwachsene Leser:innen scheitern.
- **Anname auf Englisch wenn der Slot deutschsprachig ist** — Inkonsistenz mit Postkarte.

---

## 12. Constraints (Issue #12 — Spec-System v2)

### Constraints in Prosa beschreiben, nicht parallel YAML

Strukturelle Constraints (Ausrichtungs-, Symmetrie-, Hierarchie- und Distanz-Invarianten)
werden in der Spec **als deutsche Prosa** beschrieben — NICHT als zweite YAML-Liste
neben der Slot-Tabelle (CONTEXT D6).

Begründung: Constraints leben als Code in `templates/<slug>/build.py::CONSTRAINTS`
(siehe `tools/sla_lib/builder/constraints.py` für die Factories: `same_y`, `same_x`,
`same_size`, `mirrored_x`, `mirrored_y`, `inside`, `equal_gap`, `hierarchy`,
`same_style`, `distance_x`, `distance_y`, `aligned_below`). Doppelte Source-of-Truth
(YAML in Spec + Python in build.py) würde zwangsläufig auseinanderlaufen. Code ist
Vertrag; Spec-Prosa ist menschliche Erläuterung des Vertrags.

### Neue Factories (Issue #14)

- `aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="")` — `below`
  hängt unter `above` auf derselben x-Achse mit dem definierten Abstand
  (`below.y_mm == above.y_mm + above.h_mm + gap_mm`). Per-Template
  free-form Constraint. Argumentreihenfolge `(below, above)` ist
  load-bearing — erstes Argument ist der hängende Frame.
- `SpreadImage(image, page_w_mm, page_h_mm, h_mm, y_mm=0, base_anname="",
  scale_type=0, local_scale=(1,1))` — Block-Utility in
  `tools/sla_lib/builder/blocks.py`; gibt zwei `ImageFrame`s aus, eine
  pro Seite einer Doppelseite, sodass das Quellbild als kontinuierliches
  Bild über zwei Seiten hinweg gerendert wird. Rechte Hälfte verwendet
  `local_offset_mm=(-page_w_mm, 0)` (negativ!). Ersetzt das heute defekte
  Muster `ImageFrame(x=page_w, w=page_w)`. Anname-Suffix
  ` · (left|right)` ist load-bearing — `brand:spine_safety` (Issue #22)
  exempted SpreadImage-Hälften via diesem Pattern.

### Neue Brand-Regeln (Issue #22)

- **`brand:spine_safety`** (warning) — On `facing_pages=True` Dokumenten
  warnt die Regel, wenn ein Non-SpreadImage-Frame mit seiner Rücken-Seite
  innerhalb von 3mm vom Buchrücken sitzt. Scribus erweitert den 3mm-Bleed
  über den Rücken hinweg in die gegenüberliegende Seite. Cover-Seite
  (own_page=0) wird übersprungen — bei Facing-Pages-Dokumenten steht sie
  alleine. SpreadImage-Hälften sind via Anname-Pattern
  ` · (left|right)$` exempt.
- **`brand:undeclared_alignment_drift`** (warning) — Heuristischer
  Detektor für Paare visueller Frames die fast aligniert/anliegend
  erscheinen, aber NICHT in der Per-Template-`CONSTRAINTS = […]`-Liste
  deklariert sind. Drei Tests: Achsen-Ausrichtung x/y (`min_drift_mm
  < |a.x0 - b.x0| < axis_tolerance_mm`), und Vertikal-Adjacency (A
  über B mit Gap im `(min_drift_mm, adjacency_gap_mm)`-Bereich).
  Defaults: `axis_tolerance_mm=5.0`, `adjacency_gap_mm=12.0`,
  `min_drift_mm=0.5`. Skipped: Master-Pages, anonyme Frames,
  rotierte Frames. Per-Template opt-out via
  `meta.yml::brand_overrides[brand:undeclared_alignment_drift]`.

### Audit-Tool (Issue #22)

`tools/audit_alignment.py` (CLI-Shim `bin/audit-alignment`) emittiert
einen Per-Template-Markdown-/JSON-Report:
- Page-by-Page-Primitive-Inventory (Anzahl + Side-Detection).
- Verdächtige undeklarierte Adjacencies (selbe Heuristik wie
  `brand:undeclared_alignment_drift`) mit ready-to-paste-Skeletons
  (`same_x("A", "B", name="p1_x")`, `aligned_below(...)`).
- Spine-Safety-Kandidaten (Frames innerhalb 3mm vom Rücken).

CI integriert über `.github/workflows/pages.yml::Run alignment audit`
als informational step (`|| true`); Promotion auf fatal nach
genügend encoded Templates (locked decision #10).

Konvention pro Constraint in der Spec:

```markdown
### Strukturelle Constraints

- **Beleg-Headlines (3 Spalten) horizontal ausgerichtet.** Code-Verweis:
  `CONSTRAINTS["beleg_headlines_row"]` in `build.py`. Prüft `same_y` mit
  Toleranz 0.5 mm.
- **Headline → Sub-Headline-Distanz 52 mm.** Code-Verweis:
  `CONSTRAINTS["hl_to_sub"]`. Prüft `distance_y(equals=52.0)`.
- **Brand-Constraints.** Automatisch aktiv via `BRAND_CONSTRAINTS` (siehe
  `tools/sla_lib/builder/brand_constraints.py`); 11 Regeln zu Color-Palette,
  Font-Family, Line-Spacing, HL/SL-Distanz, Logo-Größe, Text-auf-Grün, Bleed,
  Wahlkreuz-Hintergrund, **`brand:inside_page`** (Issue #14: jeder Non-Master-
  Frame liegt mit rotation- und anchor-bewusster Bbox innerhalb von
  `[-bleed, w+bleed] × [-bleed, h+bleed]` seiner Seite),
  **`brand:spine_safety`** (Issue #22: Non-SpreadImage-Frames auf
  Facing-Pages-Dokumenten müssen mind. 3mm vom Rücken eingerückt sein;
  warning-only), **`brand:undeclared_alignment_drift`** (Issue #22:
  Heuristik — Paare nahezu visuell ausgerichteter/anliegender Frames
  ohne explizite Constraint-Deklaration; warning-only, per-template
  opt-out via `meta.yml::brand_overrides`). Skipping über
  `meta.yml::brand_overrides`. Diese Spec NICHT wiederholen.
```

Wenn ein Template eine Brand-Regel intentional verletzt (z.B. Logo bewusst kleiner als
3×M wegen Layout-Beschränkung), MUSS:

1. Die Spec-Prosa die Verletzung erwähnen UND begründen.
2. `meta.yml.brand_overrides` einen passenden Eintrag tragen (siehe §13).

### Worked Example (themen-plakat-a3-quer)

Die `templates/themen-plakat-a3-quer/build.py` hat:

```python
CONSTRAINTS = [
    same_y("Beleg 1 — Headline", "Beleg 2 — Headline", "Beleg 3 — Headline",
           name="beleg_headlines_row"),
    distance_y("Headline These", "Sub-Headline", equals=52.0,
               name="hl_to_sub"),
    same_style("Beleg 1 — Headline", "Beleg 2 — Headline", "Beleg 3 — Headline",
               name="beleg_hd_style_consistent"),
    # ... weitere
]
```

Die Spec referenziert diese **nur in Prosa**, mit `name`-Identifier zum Cross-Lookup —
keine zweite YAML-Liste mit Constraint-Daten.

---

## 13. Brand-Overrides in meta.yml (Issue #12)

Wenn ein Template eine `BRAND_CONSTRAINTS`-Regel intentional verletzt, listet
`templates/<slug>/meta.yml` die Override-IDs unter `brand_overrides`:

```yaml
brand_overrides:
  - id: brand:logo_size_3M
    reason: "Logo bei 32mm sitzt bei ~60% des Quickguide 3*M = 53.46mm Targets
              auf A3 quer (kurze_kante=297mm). Eckpositionierung vermeidet
              Konkurrenz mit der breiten Headline; Verdoppeln würde das Logo
              ins typografische Feld der Headline drängen."
  - id: brand:hl_sl_distance_x2
    reason: "Sub-Headline bei y=92 sitzt ~2mm unter dem 50mm-Headline-Frame; das
              Quickguide-Target 2×Baseline (10.8mm) ist für Body-Größen gedacht,
              nicht für 60pt-Headlines auf einem Plakat. Knapper HL/SL-Abstand ist
              die intentionale Plakat-Hierarchie."
```

### Schema-Validierung

Format: Liste von `{id, reason}`-Objekten:

- `id`: matched `^brand:[A-Za-z_0-9.]+$`. Muss eine bekannte Regel-ID aus
  `BRAND_CONSTRAINTS` sein (typo-Detection: warning, nicht error).
- `reason`: Non-empty string. Erklärung MUSS verständlich für Brand-Reviewer:innen
  sein — kein „siehe Spec", keine Abkürzung wie „intentional".

Validiert durch `tools/sla_lib/builder/meta_schema.py::load_brand_overrides`. Bei
Schema-Verletzung (fehlende `id`, fehlende `reason`, ungültiges Pattern):
`ValueError`-Raise mit klarem Pointer auf die Stelle. `structural_check` markiert
übersprungene Regeln im Markdown-Report als `SKIP <id> (overridden in meta.yml: <reason>)`.

### Wann ist ein Override gerechtfertigt?

- **Ja** — Logo bewusst kleiner für Layout-Komposition (Türanhänger, Falzflyer).
- **Ja** — HL/SL-Abstand bewusst tighter wegen Format-Beschränkung (schmale Spalte).
- **Ja** — Bleed bewusst 2mm wegen Stanzkontur-Toleranz der Druckerei.
- **Ja** — Line-Spacing-Faktor 0.9 weicht ab, weil CI-Palette pre-existing drift hat
  (CI-Brand-Team-Review pending).
- **Nein** — Override als Workaround für einen Implementierungs-Bug. Den Bug fixen.
- **Nein** — Override ohne klare Begründung. Das ist nur stille Akzeptanz von Drift.

---

## Versionierung

Diese Datei: SCHEMA v2 (2026-05-08; Issue #12). Änderungen an Pflichtfeldern oder
Konventionen erfordern PR + Review. Specs, die einer früheren Version folgen, müssen vor
Gate 3 nachgezogen werden.

Issue #12 erweitert um: §11 Severity-Buckets + Float-Slots, §12 Constraint-Prosa-
Konvention, §13 Brand-Overrides-Format.
