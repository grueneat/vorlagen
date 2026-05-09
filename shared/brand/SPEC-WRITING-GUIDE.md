# Spec-Writing-Guide

**Status:** Living document. Aktualisiert, wenn ein neues Template oder eine
Retrospektive eine Konvention hervorbringt.
**Audience:** Spec-Autor:innen (Mensch oder LLM), die für ein neues Druck-Template
eine Spec schreiben — oder eine bestehende Spec überarbeiten.
**Verwandte Dokumente:** [`templates/_specs/SCHEMA.md`](../../templates/_specs/SCHEMA.md)
(Pflichtfelder + Konventionen), [`shared/brand/DESIGN-SYSTEM-BRIEF.md`](DESIGN-SYSTEM-BRIEF.md)
(Brand-Werte + Designprinzipien), [`shared/brand/QUICKGUIDE-NOTES.md`](QUICKGUIDE-NOTES.md)
(Quickguide-Formeln als Brand-CI-Vertrag), [`.github/workflows/pages.yml`](../../.github/workflows/pages.yml)
(CI-Verkettung — `tools/spec_check.py`, `tools/check_ci.py`,
`python3 -m sla_lib.builder.structural_check --all`).

## 1. Einleitung

Eine Spec ist der Vertrag zwischen Brand/Design und Build. Sie beschreibt **visuelle
Komposition** so präzise, dass zwei verschiedene Implementer:innen — Mensch oder LLM —
das gleiche Template bauen würden. Sie ist **kein Bedienungshandbuch** für End­nutzer:innen
und keine Marketingbroschüre für die Designentscheidungen; sie ist die Quelle der
Wahrheit für ALLE strukturellen Entscheidungen, die in `templates/<slug>/build.py`
ausgespielt werden.

Wer schreibt eine Spec? In der Regel die Person, die das Template vorschlägt —
oft als Auftakt zu einem Issue im Format „Wir brauchen ein <Format>-<Anlass> für die
<Zielgruppe>". Wer liest sie? Implementer:innen (auch zukünftige), Reviewer:innen,
und mechanische Werkzeuge (`tools/spec_check.py`).

Eine gute Spec überlebt drei Iterationen ohne strukturelle Drift, drei Reviewer ohne
Klärungsfragen, und einen Wechsel des Implementers ohne Verlust an Designintent.

## 2. Pflicht-Sektionen

Jede Spec MUSS folgende vier Sektionen enthalten — als Markdown-Headings oder
Schlüssel im eingebetteten YAML-Block. Reihenfolge frei, aber alle Felder vorhanden.

### Funktional

- Zielgruppe (`audience`): Wer soll das fertige Druckwerk bekommen?
  Bezirksgruppe? Wahlhelfer:innen am Infostand? Kandidat:innen für
  Tür-Aktionen? Das beeinflusst Sprache, Format und Robustheit.
- Use-Case: In welchem Setting wird das Template eingesetzt? (Wahlkampf-Endspurt,
  Stammtisch-Plakat, Tür-zu-Tür-Aktion, etc.)
- Call-to-Action: Was soll die lesende Person tun? (informieren, weitergeben,
  am Wahltag wählen, Kontakt aufnehmen?)
- Druck-Output: Format + Auflage-Vorgabe (A6 Postkarte, A3 Plakat, A1 Plakat,
  Falzflyer DIN-lang, Türanhänger 105×250); Druckereianforderungen falls
  nicht-Standard (Stanzkontur, Spot-Color, Sonderfalz).

### Visuell

- Layout-Philosophie (2–4 Sätze freie Prosa): „Was vermittelt das Template?"
  Beispiel: „Argumentationsplakat — eine starke These oben in voller Breite, drei
  Belege darunter in 3 Spalten, Quellenangabe + Impressum unten."
- Hierarchie-Order: Welche Reihenfolge führt das Auge? (Headline → Sub-Headline →
  Body? Foto → Caption → Body?) Diese Reihenfolge entscheidet über Schriftgrößen,
  Whitespace und Layer-Stack.
- Brand-Akzente: Welche Brand-Farbe spielt welche Rolle? (Dunkelgrün als
  Hintergrund-Hero, Magenta als ein Stoerer, Gelb als Highlight-Akzent.)
- Hero-Element: Welches Bild oder Symbol trägt die meiste visuelle Last? (Das
  Wahlkreuz im Kreis, ein Kandidat:innen-Portrait, eine Themen-Photographie.)

### Strukturell

- Trim/Bleed/Falz: Maße in mm. Trim ist die finale Schnittkante; Bleed (typisch
  3 mm; bei Stanzformen 2 mm) ist die Sicherheitsfläche darum; Falz-Positionen
  sind absolute mm vom Trim-Top-Left.
- Slot-Tabelle: Pro Frame eine Zeile mit `anname`, `type`, `x_mm`, `y_mm`,
  `w_mm`, `h_mm`, optional `fcolor`, `style_ref`, `example`. Die Spalten sind in
  [`templates/_specs/SCHEMA.md` §4](../../templates/_specs/SCHEMA.md) detailliert.
- Lese-Reihenfolge: In welcher Reihenfolge nimmt das Auge die Slots wahr? Diese
  Information geht NICHT in die Slot-Tabelle (mechanisch parsbar) ein, sondern in
  die Layout-Philosophie als Prosa.

### Constraints (Prosa)

- Strukturelle Constraints (Ausrichtungen, Symmetrien, Hierarchien, Distanzen)
  werden **nur in Prosa** beschrieben, mit Verweis auf den Code-Identifier in
  `templates/<slug>/build.py::CONSTRAINTS`.
- Brand-Constraints werden NICHT wiederholt — sie sind durch
  [`tools/sla_lib/builder/brand_constraints.py`](../../tools/sla_lib/builder/brand_constraints.py)
  automatisch aktiv. In der Spec NUR erwähnen, wenn ein Brand-Override gerechtfertigt
  und in `meta.yml::brand_overrides` dokumentiert ist (siehe Sektion 7 unten).

## 3. Empfohlen-Sektionen

Diese Sektionen verbessern die Spec deutlich, sind aber nicht für jedes Template
zwingend. Wenn vorhanden, in dieser Form:

### Druckpraxis

- Spot-Colors: Falz und Stanzkontur als document-local Spot-Colors, nicht in
  `shared/ci.yml` (siehe SCHEMA §7).
- Min-DPI: Für Bilder typisch 300 dpi; bei großformatigen Plakaten (A1) reichen
  150 dpi für Distanz-Betrachtung.
- Druckerei-Anforderungen: Sonderwünsche (Hefftung, Falzart, Spezialpapier,
  Veredelung) gehören hierher.

### Endnutzer:innen-Workflow

- Welche Slots werden häufig ersetzt? (Headline, Foto, Datum, URL, Kandidat-Name)
- Welche Slots werden NIE ersetzt? (Logo, Impressum, Stanzkontur, Falz)
- Welche Slots brauchen besondere Vorsicht? (Headline mit Längenrestriktion,
  Foto mit Mindest-DPI, Wahlkreuz mit D12-Kontrakt)

## 4. Optional-Sektionen

Diese Sektionen sind „nice to have" — wenn ein Template-Aspekt sie nahelegt,
gehören sie hinein.

### Robustheit

- Übertext-Verhalten: Was passiert, wenn ein Text-Slot überläuft? (Frame
  expandiert? Text wird abgeschnitten? Body wird verkleinert?)
- Häufige Fehler: Welche Implementer-Fallen sind aus früheren Issues bekannt?
  (Wahlkreuz auf weißem Hintergrund — D12-Kontraktverletzung;
  Falz-Spot-Color in `shared/ci.yml` — `check_ci` rot.)

### Provenance

- Owner: Wer pflegt diese Spec? (Brand-Team, Bezirksgruppe X, Issue #N)
- Version: SemVer der Spec (Major-Bump bei strukturellen Änderungen).

## 5. Wie schreibt man jeden Abschnitt gut?

### Funktional

- **Gut:** „Türanhänger für Wahltag — 105×250 mm Vertikal-Format mit 35 mm-
  Loch-Stanzform für Türklinken-Aufhängung. Audience: Bezirksgruppen verteilen am
  Wahltag-Morgen. Botschaft: ‚Heute ist Wahltag — Wähle Grün'. Front: Wahlkreuz-
  Hero auf Hellgrün-Band. Back: Kandidat:innen-Portrait + Kontakt."
- **Anti-Pattern:** „Türanhänger für Wahlen. Schön gestaltet. A6-Format." (Zu vage:
  welche Wahlen? Welcher Schwerpunkt? Welche Audience?)

### Visuell

- **Gut:** „Headline (60 pt Vollkorn Black Italic in Dunkelgrün) trägt die These.
  Sub-Headline (18 pt Gotham Book in Dunkelgrün) gibt den Quellen-Kontext. Drei
  Beleg-Spalten (24 pt Headline + 13 pt Body in 3 Spalten zu je ca. 125 mm) liefern
  die Daten. Themen-Hero-Photo (180×60 mm, zentriert) als visueller Anker. Quelle
  + Impressum unten in zwei kleinen Spalten."
- **Anti-Pattern:** „Schöne Typografie. Headline groß, Body klein. Bunt und
  ansprechend." (Keine konkreten Größen, keine konkreten Farben, keine
  Hierarchie-Ordnung.)

### Strukturell

- **Gut:** Slot-Tabelle mit allen Pflichtspalten + YAML-Block für `spec_check.py`.
  Jede Zeile hat eindeutiges `anname` (UTF-8 OK, deutsche Umlaute willkommen),
  Float-Werte für `x_mm/y_mm/w_mm/h_mm` (1 Nachkommastelle ist häufig genug;
  ganzzahlige Werte erlaubt für glatte Trim-Werte).
- **Anti-Pattern:** „Headline ist oben. Body ist unten. Logo links." (Keine
  Maße, kein `anname`, kein YAML-Block — `spec_check.py` kann nicht prüfen.)

### Constraints (Prosa)

- **Gut:** „Die drei Beleg-Headlines (`Beleg 1 — Headline`, `Beleg 2 — Headline`,
  `Beleg 3 — Headline`) müssen auf gleicher y-Achse liegen. Code-Verweis:
  `CONSTRAINTS['beleg_headlines_row']` in `build.py`. Prüft `same_y` mit Toleranz
  0.5 mm."
- **Anti-Pattern:** „Die Belege sind aligned." (Welche? Auf welcher Achse? Mit
  welcher Toleranz? Wo ist der Code-Verweis?)

#### Issue #14 — neue Constraint-Factory `aligned_below`

- `aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="")` — sperrt das
  „Bild hängt unter der Headline auf derselben linken Achse"-Muster ein.
  Per-Template free-form Constraint. Argumentreihenfolge: `(below, above)` —
  erstes Argument ist der Frame, der unten hängt; zweites der Anker oben.
  Issue #14.

## 6. Construct-then-add Konvention

Constraint-Listen brauchen `anname`-Strings, um Frames zu referenzieren. Damit dieses
Cross-Referencing funktioniert, MÜSSEN Frames erst als benannte lokale Variablen
konstruiert und DANN zum Page hinzugefügt werden — nicht inline.

### Korrekt

```python
def build_doc():
    doc = Document(...)
    page = doc.add_page(...)

    # Frames als benannte Locals KONSTRUIEREN
    headline = TextFrame(
        x_mm=15, y_mm=40, w_mm=390, h_mm=50,
        anname="Headline These",
        ...
    )
    sub = TextFrame(
        x_mm=15, y_mm=92, w_mm=390, h_mm=16,
        anname="Sub-Headline",
        ...
    )

    # Erst DANN zum Page HINZUFÜGEN
    page.add(headline)
    page.add(sub)
    return doc

# Constraint-Liste auf Modul-Ebene — anname-Strings statt Frame-Referenzen,
# weil die Frame-Locals außerhalb von build_doc() out of scope sind.
CONSTRAINTS = [
    distance_y("Headline These", "Sub-Headline", equals=52.0,
               name="hl_to_sub"),
]
```

### Anti-Pattern

```python
def build_doc():
    doc = Document(...)
    page = doc.add_page(...)
    page.add(TextFrame(x_mm=15, y_mm=40, ..., anname="Headline These"))  # inline
    page.add(TextFrame(x_mm=15, y_mm=92, ..., anname="Sub-Headline"))   # inline
    return doc

# Wo soll man jetzt die Constraint-Liste platzieren? Inline-Frames lassen sich
# nicht referenzieren; man müsste sie nachträglich aus iter_all_primitives()
# zurückholen — das verzweigt den Code unnötig.
```

Per `RESEARCH.md` „P-INLINE-FRAME": orphan anname (Constraint referenziert einen
Namen, der im Doc nicht existiert) erzeugt eine Warning, kein silent skip — damit
ein Renaming-Drift bemerkt wird.

## 7. Brand-Override-Konvention

Wenn ein Template intentional eine Brand-Regel verletzt (Logo bewusst kleiner,
Bleed bewusst 2 mm, Line-Spacing-Faktor weicht ab), MUSS:

1. Die Spec-Prosa die Verletzung erwähnen UND begründen.
2. `templates/<slug>/meta.yml::brand_overrides` einen passenden Eintrag tragen mit
   den zwei Pflichtfeldern `id` (matched `^brand:[A-Za-z_0-9.]+$`) und `reason`
   (nicht-leerer String).

Das Format wird durch [`tools/sla_lib/builder/meta_schema.py`](../../tools/sla_lib/builder/meta_schema.py)
JSON-Schema-validiert. Bei Schema-Verletzung (fehlende `id`, fehlende `reason`,
ungültiges Pattern): `ValueError`-Raise mit klarem Pointer auf die Stelle.

### Issue #14 — neue Brand-Regel `brand:inside_page`

- `brand:inside_page` — jeder Non-Master-Frame liegt mit rotation- und
  anchor-bewusster Bbox innerhalb von `[-bleed, w+bleed] × [-bleed, h+bleed]`
  seiner Seite. Severity: **Warning** bei >0.5 mm Übersicht, **Error** bei
  >1.0 mm. Skipping über `meta.yml::brand_overrides` (Rule-Level — keine
  Per-Frame-Allowlist). Issue #14.

### Issue #22 — neue Brand-Regeln `brand:spine_safety` + `brand:undeclared_alignment_drift`

- **`brand:spine_safety`** (warning) — Auf `facing_pages=True`-Dokumenten
  warnt die Regel, wenn die Rücken-Seite eines Non-SpreadImage-Frames
  innerhalb von 3 mm vom Buchrücken sitzt: Scribus erweitert den Bleed
  über den Rücken hinweg in die gegenüberliegende Seite. SpreadImage-
  Hälften (Anname-Pattern ` · (left|right)$`) sind exempt — sie berühren
  den Rücken intentional. Cover-Seite (`own_page == 0`) wird übersprungen
  (in Facing-Pages-Mode steht sie alleine). Side-Detection via
  `master_name`-Regex `\b(links|rechts)\b` (case-insensitive). Issue #22.

- **`brand:undeclared_alignment_drift`** (warning) — Heuristischer
  Detektor für Paare visueller Frames die fast aligniert/anliegend
  erscheinen, aber NICHT in der Per-Template-`CONSTRAINTS = […]`-Liste
  deklariert sind. Drei Tests pro Pair: Achsen-Ausrichtung x/y (Drift
  zwischen 0.5 mm und 5 mm), Vertikal-Adjacency (A oberhalb B mit Gap
  zwischen 0.5 mm und 12 mm bei <5 mm x-Drift). Skipped: Master-Pages,
  anonyme Frames, rotierte Frames. Per-Template opt-out via
  `meta.yml::brand_overrides[brand:undeclared_alignment_drift]` — gilt
  als Übergangsmaßnahme, bis das Template eine vollständige
  CONSTRAINTS-Liste mit allen deklarierten Adjacencies trägt. Issue #22.

## Auditing alignment

`tools/audit_alignment.py` (CLI-Shim `bin/audit-alignment <slug>`)
emittiert einen Per-Template-Markdown-/JSON-Report mit:

- Page-by-Page-Primitive-Inventory (Anzahl + Side-Detection links/rechts).
- Verdächtige undeklarierte Adjacencies (selbe Heuristik wie
  `brand:undeclared_alignment_drift`) mit ready-to-paste Constraint-
  Skeletons (`same_x("A", "B", name="p1_x_1")`,
  `same_y(...)`, `aligned_below(...)`).
- Spine-Safety-Kandidaten (Frames innerhalb 3 mm vom Rücken auf
  Facing-Pages-Dokumenten).

Workflow für das Encoding der CONSTRAINTS eines Templates:

1. `bin/audit-alignment <slug> --md report.md` ausführen.
2. Für jedes verdächtige Pair entscheiden: deklarieren (das vorgeschlagene
   Skeleton in `CONSTRAINTS = [...]` einfügen) oder Geometrie korrigieren
   (die Ausrichtung ist nicht intendiert — Frame so verschieben dass
   der Drift > 5 mm wird).
3. Re-run; iterieren bis Report sauber ist.

`bin/audit-alignment --all` läuft über alle Templates. CI führt den Audit
informational aus (Artifact `audit-alignment-report` immer hochgeladen,
fail nie); Promotion auf fatal ist deferred bis genug Production-Templates
encoded sind (locked decision #10 aus Issue #22).

CLI-Optionen:
- `--axis-tol-mm <float>` (default 5.0) — narrow für strengere
  Achsen-Detektion.
- `--adjacency-tol-mm <float>` (default 12.0) — narrow für strengere
  Adjacency-Detektion.
- `--json` / `--md FILE.md` — Ausgabe-Format.
- `--all --output-dir DIR` — pro-Template `<slug>.md` in DIR.

### Worked Example aus Phase-4-Entdeckung (Türanhänger)

Während Phase 4 von Issue #12 wurde entdeckt, dass der Türanhänger den HL/SL-
Abstand-Quickguide-Vertrag absichtlich verletzt — die schmale 105 mm-Spalte
würde mit 2× Baseline (10.8 mm) Abstand zu viel Whitespace verlieren. Dokumentiert
in `meta.yml`:

```yaml
brand_overrides:
  - id: brand:hl_sl_distance_x2
    reason: >-
      Türanhänger uses tighter HL/SL spacing to fit the door-hanger format
      (105x250mm narrow vertical column) — design choice approved by brand
      team and documented in QUICKGUIDE-NOTES.md "Worked example: HL → SL
      gap drift flag — sub is much closer than Quickguide suggests. May be
      intentional for the narrow Türanhänger column."
```

Die `reason` MUSS eine Brand-Reviewer:in nachvollziehen können, ohne den Code
zu öffnen. „intentional", „siehe Spec" oder „brand-team approved" ohne
Erklärung sind unzureichend.

### Wann ist ein Override gerechtfertigt?

- **Ja** — Logo bewusst kleiner für Layout-Komposition (Türanhänger 35 mm front
  vs. 18.9 mm Quickguide-Target).
- **Ja** — HL/SL-Abstand bewusst tighter wegen Format-Beschränkung (schmale
  105 mm-Spalte).
- **Ja** — Bleed bewusst 2 mm wegen Stanzkontur-Toleranz der Druckerei.
- **Ja** — Line-Spacing-Faktor 0.9 weicht ab, weil CI-Palette pre-existing drift hat
  (Brand-Team-Review pending).
- **Nein** — Override als Workaround für einen Implementierungs-Bug. Den Bug fixen.
- **Nein** — Override ohne klare Begründung. Das ist nur stille Akzeptanz von Drift.

### SpreadImage-Migration — ein Bild über zwei Doppelseiten

Wenn ein Bild als kontinuierliches Bild über zwei Doppelseiten gerendert
werden soll (z.B. ein Foto-Spread auf den Innenseiten einer Zeitung), ist
das heute übliche Muster — ein einzelner `ImageFrame` mit `x_mm=0` und
`w_mm=2*page_w_mm` auf der linken Seite — fundamental kaputt: der Frame
überschreitet den rechten Rand der linken Seite um eine volle Seitenbreite
und wird von `brand:inside_page` als Error geflagged.

#### ❌ Falsch — überschreitet den rechten Rand der linken Seite um eine volle Seitenbreite

```python
ImageFrame(x_mm=0, y_mm=0, w_mm=2*page_w, h_mm=page_h,
           image="cover.jpg", anname="P9 Spread")
```

#### ✅ Richtig — zwei `inside_page`-saubere Frames, rechte Hälfte scrollt das Quellbild nach links

```python
from sla_lib.builder.blocks import SpreadImage

spread = SpreadImage(image="cover.jpg",
                     page_w_mm=210, page_h_mm=297, h_mm=297,
                     base_anname="P9 Spread")
spread.place(page_left, page_right)
# → Frames mit anname "P9 Spread · left" und "P9 Spread · right"
# → rechte Hälfte verwendet local_offset_mm=(-210, 0)  [NEGATIV-x!]
# → scale_type=0 hard-pinned (sonst würde Scribus jede Hälfte einzeln
#   auto-fitten und der Spread visuell zerbrechen)
```

Vollständige Signatur in `tools/sla_lib/builder/blocks.py::SpreadImage`.
Issue #14 / #16 (zeitung-Migration).

## 8. Worked Example — themen-plakat-a3-quer

Eine Spec-Slot-Beschreibung mit Code-Constraint-Verweis sieht in der Praxis so aus:

### In der Spec (Markdown-Prosa-Sektion)

> **Beleg-Reihen-Ausrichtung.** Die drei Beleg-Headlines auf dem Plakat
> (Slots `Beleg 1 — Headline`, `Beleg 2 — Headline`, `Beleg 3 — Headline`)
> liegen auf der gleichen y-Achse (y=130 mm). Die zugehörigen Beleg-Bodies
> (`Beleg 1 — Body` … `Beleg 3 — Body`) liegen auf y=152 mm. Diese
> Reihen-Ausrichtung wird durch Code-Constraints `same_y` validiert; siehe
> `CONSTRAINTS['beleg_headlines_row']` und `CONSTRAINTS['beleg_bodies_row']`
> in `templates/themen-plakat-a3-quer/build.py`.

### Im Code (`build.py` Modul-Ebene)

```python
CONSTRAINTS = [
    same_y(
        "Beleg 1 — Headline", "Beleg 2 — Headline", "Beleg 3 — Headline",
        name="beleg_headlines_row",
    ),
    same_y(
        "Beleg 1 — Body", "Beleg 2 — Body", "Beleg 3 — Body",
        name="beleg_bodies_row",
    ),
    distance_y(
        "Headline These", "Sub-Headline", equals=52.0,
        name="hl_to_sub",
    ),
    same_style(
        "Beleg 1 — Headline", "Beleg 2 — Headline", "Beleg 3 — Headline",
        name="beleg_hd_style_consistent",
    ),
]
```

Der `name`-Parameter ist der Cross-Lookup-Identifier, den die Spec-Prosa
referenziert. Der Constraint-Code ist Source-of-Truth — die Spec-Prosa
ist die menschliche Erläuterung.

## 9. Review-Checklist

Vor dem Implementation-Freigabe-Konsens (Gate 1) — die Spec-Autor:in beantwortet
diese Fragen mit Ja:

1. Hat die Spec alle vier Pflicht-Sektionen (Funktional / Visuell / Strukturell /
   Constraints in Prosa)?
2. Ist die Slot-Tabelle vollständig — jede Zeile mit `anname`, `type` und allen
   vier Maßen `x_mm/y_mm/w_mm/h_mm`?
3. Ist der eingebettete YAML-Block (`spec_check`-Quelle) Spalten-identisch zur
   Markdown-Tabelle?
4. Hat jeder Slot ein eindeutiges `anname` — keine Doppelungen?
5. Sind Float-Werte mit 1 Nachkommastelle (oder Integer für ganzzahlige Trim-
   Werte) gewählt — keine 6-Stellen-Floats wie 12.345678?
6. Sind alle Brand-Akzente in der Color-Palette (`Dunkelgrün`, `Hellgrün`, `Gelb`,
   `Magenta`, `White`, `Black`, `Registration`) — keine Custom-Farben ohne
   `meta.yml::ci_overrides::non_ci_colors`?
7. Halten die Mindest-Schriftgrößen aus SCHEMA.md §8 (z.B. A6: H1 ≥ 22 pt;
   A1: H1 ≥ 80 pt)?
8. Wenn Wahlkreuz-Symbol verwendet: ist der `background_color`-Vertrag (D12,
   nicht weiß und nicht gelb) erfüllt? In der Spec begründet?
9. Wenn Falz/Stanzkontur: sind sie als document-local Spot-Colors deklariert,
   nicht in `shared/ci.yml`?
10. Sind Constraints in Prosa beschrieben (mit Code-`name`-Verweis), NICHT als
    parallele YAML-Liste neben der Slot-Tabelle?
11. Wenn ein Brand-Override gerechtfertigt: hat `meta.yml::brand_overrides`
    einen Eintrag mit `id` und vollständiger `reason`?
12. Wurde die Layout-Philosophie in 2–4 Sätzen freier Prosa formuliert — keine
    Bullet-Punkte aus Marketing-Vokabular?
13. Verwendet die Spec konsistent Deutsch? (Ausnahme: technische Strings wie
    `anname` und `style_ref` nutzen den im Code verwendeten Wortlaut.)

Wenn auch nur eine Frage „Nein" ist: zurück zum Schreibtisch, NICHT zur
Implementation-Freigabe.

## 10. Common Pitfalls aus Issue #10/#11/#13

Aus Retrospektiven der ersten drei Spec-System-Issues, die hier dokumentiert sind,
damit zukünftige Spec-Autor:innen sie nicht wiederholen.

### P-1 — Inline-Frame ohne Local

`page.add(TextFrame(...))` inline ist bequem, lässt sich aber nicht in einer
Constraint-Liste referenzieren (Frame-Local wird nie an einen Variablennamen
gebunden). Resultat: Constraint-Liste muss anname-Strings nutzen, was OK ist —
aber der Spec-Author muss die anname-Strings erst aus dem Build-Code rückübersetzen.
Construct-then-add ist die saubere Konvention.

### P-2 — Brand-Constraint-Drift ohne Override

Wenn `structural_check` rot wird auf einem Brand-Constraint, gibt es zwei richtige
Reaktionen: (a) Template fixen, oder (b) `brand_overrides` mit `reason` ergänzen.
Falsch: Brand-Constraint-Code ändern, damit der Test passt. Die Brand-Regel ist
ein Vertrag — Verletzungen werden dokumentiert, nicht versteckt.

### P-3 — Wahlkreuz auf weißem Hintergrund (D12)

Der Wahlkreuz-Asset (gelbes Kreuz im weißen Kreis) verschwindet auf weißem
Hintergrund — der weiße Schutzkreis fließt mit dem Hintergrund zusammen, und
es bleibt nur ein gelbes Kreuz. Spec MUSS `background_color` für den
WahlkreuzSymbol-Block dokumentieren — Standard ist `Dunkelgrün`. Andere Farben
brauchen Spec-Begründung.

### P-4 — Falz-Spot-Color in `shared/ci.yml`

Falz und Stanzkontur sind `template-lokale` Spot-Colors. Sie in `shared/ci.yml`
zu legen würde `tools/check_ci.py` für die drei Templates ohne diese Farben rot
färben. Korrekt: pro Template `Document.add_color("Falz", cmyk=..., spot=True)`
und `meta.yml::ci_overrides::non_ci_colors`-Eintrag.

### P-5 — Slot-Tabelle und YAML-Block divergieren

Die Markdown-Slot-Tabelle ist Mensch-lesbar; der YAML-Block ist die
maschinen-parsbare Wahrheit für `spec_check.py`. Wenn beide auseinanderlaufen
(„Tabelle hat Logo bei x=5, YAML hat Logo bei x=8"): YAML gewinnt; Tabelle muss
nachgezogen werden. Spec-Reviewer:innen sollten beide vergleichen.

### P-6 — Übertext-Verhalten nicht spezifiziert

Headline-Slots überlaufen unweigerlich, wenn die End­nutzer:in eine längere
Botschaft verwendet. Spec MUSS in der Robustheit-Sektion dokumentieren: Frame
expandiert? Text wird abgeschnitten? Schriftgröße wird auto-skaliert? Andernfalls
hat das Build-Team keinen Vertrag und entscheidet ad-hoc.

### P-7 — Mediengesetz §24 vergessen

Wahlaufruf-Templates müssen einen Impressum-Block tragen, der die formellen
Anforderungen aus §24 Mediengesetz erfüllt (Medieninhaber, Anschrift, Hersteller-
Information bei Druckerzeugnissen). Spec MUSS die genaue Impressum-Pflicht
dokumentieren, nicht nur „Impressum unten klein".

### P-8 — Audience zu vage

„Für alle" ist keine `audience`. Die `audience` einer Spec entscheidet über
Sprache (Du oder Sie?), Schwere des Inhalts (Wahlpolitik vs. Themenplakat),
Format (A6 für Tür-zu-Tür vs. A3 für öffentlichen Aushang) und Robustheit
(unerfahrene Bezirksgruppe vs. erfahrene Landesgruppe). Spec, die `audience`
auslässt, ist Implementation-blockierend.

### P-9 — `anname` auf Englisch

Wenn die Spec deutschsprachig ist, sind auch die `anname`-Strings deutsch:
„Logo Grüne (weiss)", nicht „Logo green (white)". Konsistenz mit der bestehenden
Postkarte-Vorlage und mit den Begriffen, die End­nutzer:innen in Scribus
sehen werden.

### P-10 — Mehrere Stoerer in einem Layout

Magenta soll Aufmerksamkeit ziehen, nicht teilen. Mehr als ein Stoerer pro
Layout entwertet den Akzent — Spec sollte, wenn ein Stoerer geplant ist, das
auch im Singular formulieren („der Stoerer", nicht „die Stoerer").

---

## Anhang — Cross-Links

- [SCHEMA.md](../../templates/_specs/SCHEMA.md) — Pflichtfelder, Slot-Tabelle,
  Severity-Buckets, Brand-Overrides-Format
- [DESIGN-SYSTEM-BRIEF.md](DESIGN-SYSTEM-BRIEF.md) — Brand-Werte, Designprinzipien,
  Tonality
- [QUICKGUIDE-NOTES.md](QUICKGUIDE-NOTES.md) — Brand-CI-Formeln (Quickguide-
  Notes als Vertragsquelle)
- [.github/workflows/pages.yml](../../.github/workflows/pages.yml) — CI-Verkettung:
  `tools/spec_check.py`, `tools/check_ci.py`, `python3 -m sla_lib.builder.structural_check --all`

---

**Versionierung.** Diese Datei: SPEC-WRITING-GUIDE v1 (2026-05-08; Issue #12).
Änderungen werden mit Issue-Referenz im Commit-Body dokumentiert und im
SCHEMA.md-Versionseintrag mit-bewegt.
