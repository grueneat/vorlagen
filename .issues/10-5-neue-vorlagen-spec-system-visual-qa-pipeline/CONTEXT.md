# Design Decisions — 10-5-neue-vorlagen-spec-system-visual-qa-pipeline

Captured 2026-05-07. Locked decisions are binding for research, plan, and execute phases.
Discretion items can be explored by research; deferred items are out of scope.

## Decisions (locked — research/planner must follow)

### D1. EPS-Embedding-Strategie: EPS → PDF → inline `ImageFrame`

**Entscheidung:** Die `Wahl Kreuz im Kreis.eps` wird einmalig im Build-Schritt zu PDF
konvertiert (Ghostscript `gs`), und das Resultat per `ImageFrame.inline_image_data`
(base64) in jedes Template eingebettet, das den Wahlkreuz braucht.

**Begründung:**
- Bestehender DSL-Pattern für eingebettete Bilder ist `ImageFrame` mit
  `inline_image_data` (siehe `ImageFrame` in `tools/sla_lib/builder/primitives.py`,
  bereits eingesetzt in Postkarte/Plakat).
- Scribus 1.6 rendert eingebettete PDFs via Ghostscript und behält Vektor-
  Charakteristiken weitgehend (Skalierung verlustfrei für die hier relevanten
  Größen 30–250 mm).
- Kein neuer Block-Typ nötig; bestehende `ImageFrame`-API reicht.
- Konvertierungs-Tool (`gs`) ist auf dem Container vorhanden und Standard.
- Alternative SVG→Polygon wäre vektoriell perfekter, aber tooling-aufwendig
  (SVG-Parser, Path-Conversion) — nicht skalierbar für künftige EPS-Assets.
- Alternative externe-Datei-Referenz verletzt Issue-Constraint
  „direkt eingebettet".

**Implementierung:**
- `shared/assets/wahlkreuz-kreis.eps` — original
- `tools/eps_to_pdf.py` (oder Make-Target) — konvertiert nach
  `shared/assets/derived/wahlkreuz-kreis.pdf`, cached, idempotent
- `shared/assets/derived/` ist `.gitignore`-tracked (build artifact);
  alternativ ins Repo committen, wenn Determinismus-Bedenken bestehen
  (Reviewer entscheidet in Gate 1)
- Build-Skript jeder Template-`build.py` lädt PDF-Bytes, base64-encoded, in
  `ImageFrame(inline_image_data=..., inline_image_ext="pdf")`

**Helper-Block:** `WahlkreuzSymbol` als wrapper um `ImageFrame` mit
sinnvollen Defaults (Aspect-Ratio-Lock, sensible Size-Range). Bewahrt
Pflege-Konsistenz über die drei Templates, die ihn nutzen.

---

### D2. Spec-Format: Markdown mit eingebettetem YAML `slots:`-Block + ASCII-Layout

**Entscheidung:** Specs unter `templates/_specs/<slug>.md` als Markdown geschrieben,
mit:
- Prosa-Sektionen (Audience, Layout-Philosophie, Druckhinweise, Beispieltexte)
- ASCII-Layout-Skizze in fenced code blocks (Konvention in `SCHEMA.md`)
- Eingebetteter YAML-Block mit allen strukturierten Feldern (slots, dimensions,
  ci_overrides, eps_strategy) — parsbar durch Python `yaml.safe_load` aus dem
  Markdown extrahiert

**Begründung:**
- Lesbarkeit für Reviewer:innen (Mensch und LLM in Gate 1) ist primärziel
- Maschinen-Parsbarkeit für künftigen Linter/Drift-Check bleibt durch YAML-Block
  erhalten (`tools/spec_parse.py` extrahiert YAML aus fenced ` ```yaml `-Block)
- Konsistent mit bestehender `meta.yml` Konvention (slot-Felder strukturell
  identisch zu `meta.yml.slots`)
- ASCII-Skizzen sind LLM-freundlicher als externe SVG/Penpot-Files für Gate 1

**Spec-Schema unter `templates/_specs/SCHEMA.md`** definiert:
- Pflichtfelder (id, format, trim_mm, bleed_mm, audience, layout-philosophy, slots, …)
- ASCII-Konvention (Box-Drawing, Maße als `←210mm→`, Slot-Marker `[H]` mit Legende)
- Slot-Tabellen-Format (anname, type, x_mm, y_mm, w_mm, h_mm, fcolor, style_ref, example)
- Verlinkung auf `shared/ci.yml`-Farben/Styles (Drift-Check möglich)

---

### D3. Spec ist Vertrag — gelockt nach Gate 1

**Entscheidung:** Nach Gate-1-Konsens gelten Specs als Design-Contract. Implementierung
in Phase 3 muss Spec folgen; jede Abweichung erfordert ein **Spec-Update mit
Begründung** im selben PR.

**Begründung:**
- Gate-1-Investment ist nur sinnvoll, wenn Spec danach Verbindlichkeit hat
- Reviewer:innen in Gate 2 (Code-Review) und Gate 3 (Visual-Review) prüfen
  explizit Spec-Konformität — ohne Lock ist diese Prüfung sinnlos
- Macht „spec-driven" zur tragenden Säule, nicht zur Floskel
- Bei berechtigten Implementierungs-Findings (z.B. „Slot zu eng für realistischen
  Text") wird die Spec aktualisiert und der entsprechende Abschnitt re-reviewed —
  nicht ignoriert

**Drift-Detection:** `tools/spec_check.py` in CI:
- Vergleicht Spec-`slots:`-YAML mit `meta.yml.slots` und Build-Output (Frame-Maße im SLA)
- Fail-fast bei Abweichungen ohne dokumentierten Spec-Update-Eintrag

---

### D4. Falz/Stanz: Spot-Color-Layer + dedizierte DSL-Blöcke

**Entscheidung:** Falzlinien und Stanzkontur als **Spot-Colors auf eigenen Layern**
implementieren — Druckerei-Standard.

**Implementierung:**
- `shared/ci.yml`: zwei neue Spot-Colors mit `spot: true`:
  - `Falz` — visueller CMYK-Wert (z.B. 100/0/0/0, ist Druck-irrelevant da Spot-Channel)
  - `Stanzkontur` — visueller CMYK-Wert (z.B. 0/100/0/0)
- DSL-Document erhält Layer-Konzept (falls noch nicht vorhanden): `add_layer(name, printable, exportable, flow_text_around)`
- Layer-Attribute: `printable=0` (erscheint nicht im finalen Druck), `exportable=1`
  (geht ins PDF mit, Druckerei sieht Pfad)
- Neue Blöcke:
  - `FoldLine(start_mm, end_mm, on_layer="Falz")` — strichlierte Linie als
    Polygon mit Spot-Color-Stroke
  - `DieCut(path_mm, on_layer="Stanzkontur")` — geschlossener Pfad für
    Stanzform (Türanhänger: Außenkontur + Türklinken-Loch)

**Begründung:**
- Druckereien erwarten Spot-Color-Pfade für Stanze und Falz; alles andere ist
  Pfusch und macht Templates für ernsthafte Druck-Aufträge unbrauchbar
- Templates werden direkt produktionsreif — kein „Druckerei muss noch hinzufügen"
- Wiederverwendbar für künftige Templates (gefalzte Booklets, andere Stanzformen)

**Risiken:** DSL hat heute kein explizites Layer-Konzept. Falls
`tools/sla_lib/builder/document.py` Layer nicht generisch unterstützt, muss
das in Phase 2 (Block-Library-Erweiterung) ergänzt werden — ist eine wesentliche
DSL-Erweiterung. Research-Phase soll das ausgraben.

---

### D5. Vision-Review: Claude + Codex + Gemini (drei Modelle)

**Entscheidung:** Visuelles Render-Review (Gate 3) sendet jedes Template-PNG an
**alle drei** Vision-fähigen Modelle, vergleichbar mit `/issue:review` für Code.

**Modell-Mapping:**
- **Claude Vision** — direkter Aufruf (gleiche Session oder via Anthropic-API
  in `tools/visual_review.py`)
- **Codex Vision** — `codex exec --image <path> --prompt <file>` oder gleichwertige
  CLI-Form (CLI ist installiert: `/root/.npm-global/bin/codex`)
- **Gemini Vision** — `gemini --image <path> --prompt <file>` (CLI installiert:
  `/root/.npm-global/bin/gemini`)

**Begründung:**
- Drei Modelle vermeiden Tie-Breaker bei 2-Modellen-Disagreement
- Konsistent mit `/issue:review`-Skill (orchestriert Claude + Codex + Gemini)
- Je Modell unterschiedliche „visuelle Augen" (Trainingsdaten, Stil-Bias) →
  bessere Abdeckung von Findings
- Kosten beherrschbar durch Bild-Downscaling (1024 px lange Kante) und
  begrenzten Iterations-Cap (siehe D6)

**Prompt-Template** unter `tools/visual_review/prompt_template.md`:
- Aufgabe explizit: „Vergleiche dieses Template mit den drei bestehenden
  Templates (Postkarte, Plakat, Zeitung) — sieht es **mindestens so gut** aus?
  Wo ist es besser, wo schwächer?"
- Strukturierte Antwort-Schema (JSON oder Markdown-Sections):
  hierarchy_readability, brand_consistency, print_risks, comparison_to_existing,
  blocking_findings, nice_to_have_findings, merge_ready (yes/no)

---

### D6. Konsens-Regel: Einstimmigkeit, Iterations-Cap 3, danach Mensch

**Entscheidung:**
- **Merge-ready erfordert 3/3 Modelle „yes"** (einstimmig).
- **Max. 3 Review→Fix→Re-Review-Iterationen** pro Template.
- Nach 3 Iterationen ohne Konsens: **Mensch-Override** (Issue-Owner) entscheidet
  basierend auf den drei letzten Reports.

**Begründung:**
- Issue-Body sagt explizit „visuelle Qualität nicht verhandelbar" — Einstimmigkeit
  ist die strengere Regel und passt
- Cap verhindert Endlos-Loop bei Modell-Stilbias-Disagreement
- 3 Iterationen geben realistischen Verbesserungs-Spielraum (Iter 1: grobe Findings,
  Iter 2: Feinheiten, Iter 3: Polish), reichen empirisch für das meiste
- Mensch-Override ist Sicherheitsnetz — wenn Modelle nach 3 Pässen nicht
  konvergieren, ist die Frage wahrscheinlich subjektiv, und Mensch entscheidet

**Logging:** Pro Template `reviews/visual-qa-<slug>.md` enthält alle Iterationen
mit Diff zwischen Pässen — Vorher/Nachher sichtbar.

---

### D7. Render-DPI + Side-by-Side-Mechanik

**Entscheidung:**
- **Primäres Render**: 200 DPI PNG via `tools/render.py` (heute 100 DPI Default —
  übersteuern via Flag oder Config)
- **Vision-API-Input**: 1024 px lange Kante, downscaled aus 200 DPI; Aspect-Ratio
  erhalten
- **Side-by-Side**: ein Composite-Grid-PNG (`reviews/all-templates-grid.png`)
  mit allen 8 Templates (3 bestehend + 5 neu) plus Beschriftungen
  → wird mitgeschickt als zweites Bild
- **Detail-Review**: Einzelbild des reviewten Templates in voller 1024px-Auflösung

**Begründung:**
- 200 DPI gibt genug Detail für Typografie-Beurteilung; Downscale auf 1024 px
  reduziert Vision-API-Kosten um ~75% gegenüber 4096 px Vollbild
- Side-by-Side-Composite zwingt Modelle zum direkten Vergleich (vermeidet
  „looks fine" ohne Bezug)
- Einzelbild-Detail erlaubt Findings auf konkrete Bereiche

**Implementierung:**
- `tools/visual_review.py` ruft `tools/render.py --dpi 200` auf
- Composite-Generierung via Pillow (`PIL`), 4-Spalten × 2-Reihen-Grid

---

### D8. Block-Module-Placement: weiterhin `blocks.py` (kein vorzeitiges Split)

**Entscheidung:** Neue Blöcke (`WahlkreuzSymbol`, `FoldedPanel`, `DoorHangerCutout`,
`TableTentFold`, `FoldLine`, `DieCut`) werden in `tools/sla_lib/builder/blocks.py`
ergänzt. Kein Modul-Split jetzt.

**Begründung:**
- Bestehende Konvention; konsistent mit Postkarte/Plakat/Zeitung
- Modul-Split ist legitime Aufgabe für Issue #9 (post-migration-dsl-hygiene), das
  parallel läuft — vorzeitiges Auseinanderziehen produziert Merge-Konflikte
- Falls `blocks.py` >2500 Zeilen wird (heute ~17 Klassen), in #9 strukturiert
  splitten

---

### D9. Retro-Specs durch echtes Reverse-Engineering

**Entscheidung:** Die drei Retro-Specs für die bestehenden Templates werden durch
**vollständiges Reverse-Engineering** geschrieben:
- `meta.yml` lesen → Slot-Definitionen
- `build.py` lesen → tatsächliche Maße, Positionen, Stile
- SLA inspizieren → finale Frame-Geometrie
- ASCII-Skizze auf Basis tatsächlicher Layouts zeichnen

Retro-Specs sind **Validation des Spec-Formats** — wenn das Format echte Templates
nicht ausdrücken kann, ist es nicht gut genug.

**Begründung:**
- Stresst das Spec-Schema (D2) gegen reale Komplexität
- Liefert Vergleichs-Referenz für die fünf neuen Specs (Reviewer in Gate 1
  haben Beispiel-Niveau)
- Hilft Brand-Drift zu erkennen (was steht heute im SLA, was nicht)

---

### D10. EPS-Konvertierung: Ghostscript mit deterministischem Output

**Entscheidung:** EPS → PDF via `gs -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite`,
output `shared/assets/derived/wahlkreuz-kreis.pdf`. Konvertierung idempotent,
Resultat in den Repo committed (kein build-time-magic in CI), damit jeder Build
deterministisch ist.

**Begründung:**
- Determinismus: jeder Build über jede Maschine produziert byte-identisches
  Resultat (Round-Trip-Diff bleibt sauber)
- CI-Lauf braucht kein Ghostscript-Setup wenn PDF schon vorhanden
- Konvertierungs-Skript dokumentiert wie's gemacht wird, Reproduzierbar

---

## Claude's Discretion (research should explore options)

- **DSL-Layer-API-Form** — `Document.add_layer(name, ...)` vs.
  `Layer(...)`-Klasse vs. Layer-im-Frame-Property. Best für `FoldLine`/`DieCut`-
  Anwendung. Research soll prüfen, was im Scribus-1.6-SLA-Schema schon existiert
  und wie Original-Templates Layer nutzen.
- **Spec-YAML-Schema-Strenge** — JSON-Schema mit Validierung im CI vs. nur
  Konvention. Research soll abwägen, ob Validation-Boilerplate sich lohnt.
- **Template-spezifische Block-Naming** — `KandidatPortraitFrame` (zu spezifisch?)
  vs. generischer `PortraitFrame` mit Defaults. Research soll prüfen, ob
  bestehende Blöcke generisch sind oder template-spezifisch.
- **Visual-QA-Composite-Layout** — 4×2-Grid vs. zwei Reihen verschiedener Höhe
  vs. interaktives Tile-Layout. Pillow-basiert. Research soll prüfen ob bestehender
  `tools/gallery_build.py` schon Composite-Logik hat.
- **Iter-Diff-Mechanik in Visual-QA-Reports** — Pillow ImageChops vs.
  before/after side-by-side vs. nur Beschreibungs-Diff. Was ist hilfreichster
  Output für Reviewer?
- **EPS-PDF-Cache-Pfad** — `shared/assets/derived/` (gitignored vs. committed),
  oder `tools/build_cache/`. Research soll Convention für andere generierte
  Assets prüfen.

---

## Deferred (out of scope for this issue)

- **Roll-up-Banner / X-Banner-Templates** — größere Formate, separate Issue
- **Sticker-Sheet-Templates** — andere Druckerei-Anforderungen
- **Visitenkarten-Template** — separate Brand-Surface (Logo-Größenverhältnisse)
- **Falzbogen-Booklet (mehrere A4 gefalzt zu A5-Heft)** — größerer Aufwand,
  separates Issue
- **Live-Editor in der Galerie-Site** — UI-Aufwand massiv, Galerie bleibt
  read-only
- **Spec-Editor-UI** — Specs werden in Markdown geschrieben, kein UI nötig
- **Automated-Brand-Drift-Detection in PRs** — `tools/check_ci.py` reicht für
  jetzt, weiterführende CI ist eigene Aufgabe
- **EPS-Block-Generalisierung für andere Wahl-Symbole** — wenn weitere Symbole
  kommen, dann generalisieren; YAGNI heute
- **Galerie-Filter nach Template-Typ (Postkarte/Flyer/Plakat)** — nice-to-have,
  separates Issue
- **Mehrsprachigkeit (DE/EN-Specs)** — Specs bleiben deutsch, Audience ist
  österreichische Grünen-Gruppen

---

## Cross-References

- Issue #9 (post-migration-dsl-hygiene) läuft parallel; `blocks.py`-Änderungen
  könnten konfligieren. Synchronisation beim Merge: spätere Issue rebased auf
  früheren PR.
- Memory: `feedback_review_in_execute_phase` — `/issue:review` läuft während
  `/issue:execute` (nicht als Vorstufe zu research/plan). Die drei Gates dieses
  Issues sind innerhalb der execute-Phase angesiedelt.
- Memory: `feedback_no_claude_attribution` — keine Claude-Branding in Specs,
  Code, Commits, Reports.
