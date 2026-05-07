---
id: '10'
title: 5 neue Vorlagen + Spec-System + Visual-QA-Pipeline
status: in_progress
priority: high
labels:
- templates
- spec
- visual-qa
source: github
source_id: 19
source_url: https://github.com/GrueneAT/vorlagen/issues/19
---

## Kontext

Das Vorlagen-System hat heute drei Templates (Postkarte A6, Plakat A1, Zeitung A4). Sie decken zentrale Nutzungsfälle ab, lassen aber ganze Layout-Klassen aus: keine gefalzten Formate, keine Querformate, kein wahlkampf-spezifischer Output, kein Kleinformat zwischen Postkarte und A1, keine 3D-Aufsteller. Das Repo enthält jetzt auch eine `Wahl Kreuz im Kreis.eps` (Adobe Illustrator Vektor, ~270 KB), die als prominentes Wahlaufruf-Element in mehreren neuen Vorlagen direkt eingebettet werden soll, damit Endnutzer:innen sie ohne EPS-Hantierung verwenden können.

Vorgeschlagen sind fünf neue Vorlagen, die jeweils eine **andere Layout-Philosophie** umsetzen:

| # | Slug | Format | Layout-Philosophie | EPS? |
|---|---|---|---|---|
| 1 | `wahlaufruf-postkarte-a6-quer` | A6 quer, 2-seitig | Symbol-zentriert, Info-Grid hinten | ja, Hero |
| 2 | `kandidat-falzflyer-din-lang` | A4 quer, 3-fach gefalzt → 6 Panele | Multi-Panel-Narrativ mit Falz-Logik | ja, Closer-Panel |
| 3 | `themen-plakat-a3-quer` | A3 quer, 1-seitig | Argumentation: These → Belege → Quelle | nein |
| 4 | `wahltag-tueranhaenger` | 105×250 mm, vertikal, mit Türklinken-Stanzform | Schmal-vertikal, Stanzform-Constraint | ja, Hero |
| 5 | `infostand-tent-card-a5-quer` | A4 quer gefalzt → A5-Tent | 3D-doppelseitig sichtbar | optional |

Parallel soll ein **Spec-Format** etabliert werden: ein Markdown/YAML-Dokument je Template, das die visuelle Komposition so präzise beschreibt, dass eine Implementer:in (Mensch oder LLM) das Template ohne Rückfragen bauen kann — Maße in mm, Slot-Positionen, Farb-Rollen, Typ-Hierarchie, Bleed/Trim, EPS-Embedding-Strategie, Textbeispiele.

## Scope

### Lieferung A — Spec-Format und sechs Spec-Dokumente

A1. **Spec-Schema entwerfen** unter `templates/_specs/SCHEMA.md` (oder im `shared/`-Pfad, je nach besserem Ort): Struktur, Pflichtfelder, ASCII-Layout-Skizzen-Konvention, Slot-Tabellen-Konvention, Farb-/Typ-Referenzen aus `shared/ci.yml`.

A2. **Fünf neue Specs** unter `templates/_specs/<slug>.md` für die fünf oben gelisteten Vorlagen — mit:
   - Trim-/Bleed-/Falz-Maßen exakt in mm
   - ASCII-Layout-Skizze beider/aller sichtbaren Seiten
   - Slot-Tabelle (`anname`, Typ, Maße, Farb-Role, Style-Referenz, Beispiel-Inhalt)
   - EPS-Embedding-Strategie (Skalierung, Position, Farbquelle)
   - Beispieltext und realistische Kampagnen-Daten als Platzhalter
   - Audience-Begründung (welche Gruppe nutzt das wann?)
   - Druckhinweise (Stanzform, Falzlinien, Mindest-DPI)

A3. **Eine Retro-Spec** für die drei bestehenden Templates unter `templates/_specs/_existing-templates.md` (oder pro Template ein File `_existing-postkarte-a6-kampagne.md` etc.) — primär als **Referenzbeispiele**, damit das Spec-Format an einem realen, funktionierenden Template validiert ist und neue Specs konsistent geschrieben werden.

### Lieferung B — Implementierung der fünf Templates

B1. Pro Template `templates/<slug>/{build.py, meta.yml, README.md}` im DSL-Stil der bestehenden drei Templates — keine Roh-XML.

B2. Wo nötig **neue Block-Bausteine** in `tools/sla_lib/builder/blocks.py` (z.B. `WahlkreuzSymbol`, `FoldedPanel`, `DoorHangerCutout`, `TableTentFold`) — mit Tests und Dokumentation.

B3. EPS in `shared/assets/wahlkreuz-kreis.eps` ablegen (umbenannt für Filename-Hygiene); aus `Wahl Kreuz im Kreis.eps` an Workspace-Root.

B4. CI-Validierung: `tools/check_ci.py` für jedes neue Template grün, neue Styles/Farben — falls notwendig — über `ci_overrides` dokumentiert.

B5. Galerie-Build (`tools/gallery_build.py`) emittiert für alle fünf Templates Astro-Content + PNG-Previews.

### Lieferung C — Visual-QA-Pipeline

C1. **Automatisierte visuelle Smoke-Tests** unter `tests/visual/` oder `templates/_smoke/` analog zur bestehenden `_smoke`-Struktur: jeder neue Template-Build rendert PDF + PNG, Layout-Brüche werden erkannt (z.B. überlappende Frames, leerer Slot, Text außerhalb Trim).

C2. **Multi-Model-Visual-Review-Skript** (`tools/visual_review.py`): nimmt PNG-Previews der neuen Templates, schickt sie an mindestens zwei externe Modelle (Codex und/oder Gemini, analog zu `/issue:review`), und sammelt strukturiertes Feedback zu:
   - Lesbarkeit der Hierarchie (Headline > Body > Impressum)
   - Brand-Konsistenz (CMYK-Farb-Anmutung, Font-Größen-Verhältnisse)
   - Druckbarkeits-Risiken (Text zu nah am Trim, Bleed fehlt, etc.)
   - Layout-Vergleich zu den bestehenden Templates: ist das neue mindestens auf Augenhöhe?
   Ergebnis als Markdown-Report `reviews/visual-qa-<slug>.md`.

C3. **Iteration**: Findings aus C1+C2 fließen zurück in `build.py`. Pro Template mindestens ein Review-Pass mit dokumentierten Fixes.

C4. **Quality-Gate**: PR wird erst gemerged, wenn pro Template:
   - `make check` und `make build` grün
   - Visual-Smoke-Test grün
   - Multi-Model-Review hat keine "blocking" Findings mehr (Reviewer-Konsens)
   - Optionaler Augen-Vergleich Mensch (mind. 2 Bestätigungen, dass es mindestens so gut wie die bestehenden aussieht)

## Constraints

- **Visuelle Qualität ist nicht verhandelbar.** Die fünf neuen Templates müssen **mindestens auf Augenhöhe** mit Postkarte/Plakat/Zeitung wirken — und das Ziel ist sichtbar besser, weil andere Landesgruppen darauf schauen. Layout-Hierarchie, Typografie, Whitespace, Brand-Anmutung sind die primären Erfolgskriterien — funktionierende Builds allein reichen *nicht*. Reviews und Quality-Gates priorisieren visuelle Qualität explizit über Code-Eleganz.
- **Keine Roh-XML-Edits**: alles via DSL (`tools/sla_lib/builder/`).
- **Brand-Hygiene**: nur `shared/ci.yml`-Farben/Styles. Neue Styles brauchen explizite Begründung in der Spec und müssen entweder in `ci.yml` aufgenommen oder in `meta.yml.ci_overrides` dokumentiert werden.
- **EPS direkt eingebettet**, nicht referenziert — Endnutzer:innen sollen die Vorlage öffnen und drucken können, ohne separate Asset-Pfade pflegen zu müssen.
- **Kostenrahmen** für Multi-Model-Review pro Template-Pass moderat halten; Bilder downscalen auf sinnvolle Auflösung (z.B. 1024 px lange Kante) bevor an externe Modelle geschickt.
- **Kein Claude-Branding** in Commits, Specs, Templates oder Reports (Memory-Regel).
- **Bestehende Tests** bleiben grün; `tools/check_ci.py` und `tools/sla_diff.py` Round-Trip-Validierung der drei Original-Templates darf nicht regressieren.

## Review-Gates (verbindlich, in Reihenfolge)

Drei eigenständige Review-Gates müssen passieren, bevor das Issue als done gilt. Jedes Gate produziert einen versionierten Review-Report; Findings werden adressiert oder begründet abgewiesen, bevor das nächste Gate beginnt.

### Gate 1 — Spec-Review (nach Phase 1, vor Implementierungs-Code)

**Was:** `/issue:review` über die sechs Spec-Dokumente (Schema + 5 neue Specs + 3 Retro-Specs).
**Reviewer:** Claude + Codex + Gemini, koordiniert durch `/issue:review`.
**Fokus (im Review-Prompt explizit zu betonen):**
- Sind die Specs visuell präzise genug, dass zwei verschiedene Implementer:innen das gleiche Template bauen würden?
- Stimmt die Layout-Hierarchie (Headline > Sub > Body > Akzent > Impressum) auf Brand-Niveau der bestehenden drei Templates?
- Ist Typografie-Mengung, Whitespace, Farb-Einsatz so spezifiziert, dass das Ergebnis **mindestens so gut wie die bestehenden Templates** wirkt?
- Risiken: Slots zu eng, Text-Längen unrealistisch, EPS-Skalierung nicht definiert, Falz-/Stanz-Maße inkonsistent?
**Output:** `reviews/spec-review-<run-id>.md`. Findings adressiert oder im Spec begründet abgewiesen, bevor Phase 2 beginnt.

### Gate 2 — Code/Build-Review (nach Phase 3, wenn alle 5 Templates bauen)

**Was:** `/issue:review` über die DSL-Implementierung (build.py + neue Block-Bausteine + meta.yml + Smoke-Tests).
**Reviewer:** Claude + Codex + Gemini.
**Fokus (im Review-Prompt explizit zu betonen):**
- DSL-Patterns konsistent mit den drei bestehenden Templates?
- Sind die neuen Blocks (`WahlkreuzSymbol`, `FoldedPanel`, `DoorHangerCutout`, `TableTentFold`) wiederverwendbar gestaltet, mit klaren API-Grenzen?
- Stimmt die Implementierung mit der jeweiligen Spec überein? Slot-für-Slot Abgleich.
- Fehlt etwas, das visuelle Qualität untergräbt (z.B. fehlende Bleed, Default-Spacing, Alignment-Bugs)?
- Bestehender Round-Trip-Diff der Original-Templates noch grün?
**Output:** `reviews/code-review-<run-id>.md`. Findings adressiert vor Gate 3.

### Gate 3 — Visuelles Render-Review (nach Phase 4, vor Merge)

**Was:** Multi-Model-Visual-QA der **gerenderten PNG-Previews** aller fünf neuen Templates — und ein direkter Side-by-Side-Vergleich zu den drei bestehenden Galerie-Templates. **Dies ist das wichtigste Gate des Issues.**
**Reviewer:** Claude (Vision) + Codex (Vision) + Gemini (Vision) via `tools/visual_review.py`. Plus mindestens ein Mensch-Augenpaar pro Template.
**Fokus (im Review-Prompt explizit, fett, an erster Stelle):**
- **Sieht das gerenderte Template mindestens so gut aus wie die bestehenden Postkarte/Plakat/Zeitung — und wenn ja, gibt es Aspekte, in denen es sichtbar besser ist?** Diese Frage steht über allem.
- Visuelle Hierarchie liest sich auf den ersten Blick richtig (1-Sekunden-Test: was ist die Hauptbotschaft?)
- Brand-Anmutung: Farb-Mix, Typo-Mix, Symbol-Einsatz fühlt sich nach Grünen-CI an, nicht generisch
- Druckbarkeits-Risiken sichtbar (Text zu nah am Trim, Bleed fehlt, schlechter Kontrast, kollidierende Frames, Whitespace-Rhythmus kaputt)
- Konkrete Verbesserungsvorschläge mit Begründung — nicht nur "looks fine"
- Falls ein Modell sagt "schlechter als bestehend", ist das ein Blocker bis adressiert oder in Reviewer-Konsens widerlegt
**Output:** Pro Template ein Report `reviews/visual-qa-<slug>.md` mit Modell-Konsens, Findings, Vorher/Nachher-Bildern nach Iteration. Plus ein Gesamt-Report `reviews/visual-qa-summary.md` mit Side-by-Side-Vergleich aller acht Templates.
**Iteration:** Mindestens **eine Review→Fix→Re-Review-Schleife** pro Template. Wenn der erste Pass „mindestens so gut wie bestehend" nicht eindeutig erfüllt, weiter iterieren bis erfüllt.

## Acceptance Criteria

- [ ] Spec-Schema unter `templates/_specs/SCHEMA.md` existiert und beschreibt Pflichtfelder, ASCII-Layout-Konvention, Slot-Tabellen-Format
- [ ] Fünf neue Spec-Dokumente `templates/_specs/<slug>.md` sind vollständig (alle Pflichtfelder, ASCII-Skizze, Slot-Tabelle, EPS-Strategie wo zutreffend, Druckhinweise)
- [ ] Retro-Specs für die drei bestehenden Templates sind geschrieben und stimmen mit dem heutigen Build überein (Slot-Liste deckt sich mit `meta.yml`)
- [ ] Fünf neue Templates bauen sauber via `python3 build.py`, erzeugen valides Scribus-1.6-SLA, öffnen sich in Scribus ohne Warnung
- [ ] Wahlkreuz-EPS ist in `shared/assets/` abgelegt und in den drei dafür vorgesehenen Templates (Wahlaufruf-Postkarte, Falzflyer, Türanhänger) als sichtbares Element eingebettet
- [ ] `tools/check_ci.py` ist grün für alle fünf neuen Templates
- [ ] `tools/sla_diff.py` Round-Trip auf den drei bestehenden Templates ist weiterhin grün (keine Regression)
- [ ] Visual-Smoke-Test (C1) erkennt mindestens drei künstliche Layout-Brüche (überlappung, fehlender Slot, Text-out-of-bounds) zuverlässig
- [ ] `tools/visual_review.py` ist ausführbar, sendet PNGs an ≥2 externe Modelle, schreibt einen strukturierten Markdown-Report
- [ ] **Gate 1 — Spec-Review** (`/issue:review`) ist gelaufen, Report unter `reviews/spec-review-*.md`, alle Findings adressiert oder begründet abgewiesen, BEVOR Implementierung beginnt
- [ ] **Gate 2 — Code-Review** (`/issue:review`) ist gelaufen, Report unter `reviews/code-review-*.md`, alle Findings adressiert oder begründet abgewiesen, BEVOR Render-Review beginnt
- [ ] **Gate 3 — Visuelles Render-Review** mit Multi-Model-Vision (Claude + Codex + Gemini) ist pro Template gelaufen, Report unter `reviews/visual-qa-<slug>.md`
- [ ] **Gate 3 — Side-by-Side-Konsens**: alle drei Vision-Modelle bestätigen pro Template explizit „mindestens so gut wie die bestehenden drei Templates" — uneinheitliches Urteil ist ein Blocker bis aufgelöst
- [ ] **Mindestens eine** Review→Fix→Re-Review-Schleife pro Template; das Vorher/Nachher ist im jeweiligen `visual-qa-<slug>.md` dokumentiert
- [ ] Gesamt-Report `reviews/visual-qa-summary.md` mit Side-by-Side aller acht Templates und expliziter Empfehlung „merge-ready" pro Template
- [ ] Mensch-Review: mindestens 2 Bestätigungen in PR-Kommentaren „sieht mindestens so gut aus wie die bestehenden drei"
- [ ] Galerie-Build (`tools/gallery_build.py`) emittiert die fünf neuen Templates inklusive PNG-Previews korrekt
- [ ] CI-Workflow `.github/workflows/pages.yml` baut, validiert, deployed alle acht Templates ohne manuellen Eingriff
- [ ] PR-Beschreibung enthält Vorher/Nachher-Galerie-Screenshots aller acht Templates nebeneinander

## Risiken & Open Questions

- **EPS-Embedding in Scribus 1.6** — Scribus unterstützt EPS nativ, aber DSL/`sla_lib/builder` hat aktuell keinen EPS-Block. Eventuell Konversion zu PDF/SVG nötig falls Embedding-Pfad unsauber.
- **Stanzform Türanhänger** — Druckereien erwarten Stanz-Layer als Sonderfarbe (z.B. `Stanzkontur` Spot). DSL-Support für Spot-Color-Path-Layer prüfen.
- **Multi-Model-Review-Kosten** — bei 5 Templates × mehrere Iterationen × 2 Modelle nicht trivial. Ggf. nur bei Final-Pass voll skalieren.
- **Falz-Logik im DSL** — heute hat keine Vorlage Falzlinien. Sauberer Block (`FoldedPanel`) statt Hilfslinien-Hack.
- **Zusammenarbeit mit #9** — `post-migration-dsl-hygiene` läuft parallel; Block-Library-Änderungen können konfligieren. Synchronisation beim Merge.

## Phasenvorschlag

1. **Phase 1 — Spec-Format + Specs (A1, A2, A3)** — Diskussion und Festklopfen, bevor Code geschrieben wird.
2. **→ Gate 1: Spec-Review** (`/issue:review`) — Multi-Model-Review der Spec-Dokumente. Findings adressiert, bevor Phase 3 startet.
3. **Phase 2 — Block-Library-Erweiterung (B2, B3)** — neue Bausteine isoliert testen.
4. **Phase 3 — Template-Implementierung (B1, B4, B5)** — Templates eines nach dem anderen, jedes mit Smoke-Test.
5. **→ Gate 2: Code-Review** (`/issue:review`) — Multi-Model-Review der DSL-Implementierung. Findings adressiert, bevor visuelles Review.
6. **Phase 4 — Visual-QA-Pipeline-Tooling (C1, C2)** — Smoke-Tests + `tools/visual_review.py` aufbauen.
7. **→ Gate 3: Visuelles Render-Review** (Multi-Model-Vision auf gerenderten PNGs + Side-by-Side gegen bestehende Templates). **Mindestens eine** Review→Fix→Re-Review-Schleife pro Template. Das ist das wichtigste Gate.
8. **Phase 5 — Mensch-Review + PR (C3, C4)** — letzte Augen, PR-Beschreibung mit Galerie-Vergleich, Merge.
