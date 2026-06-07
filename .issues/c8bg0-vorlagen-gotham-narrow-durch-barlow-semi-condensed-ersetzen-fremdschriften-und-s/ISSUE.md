---
id: c8bg0
title: 'Vorlagen: Gotham Narrow durch Barlow Semi Condensed ersetzen, Fremdschriften
  und Schriftvergleich entfernen, Baseline-PDFs neu erzeugen'
status: done
ship_state: pr_open
priority: high
labels:
- fonts
- templates
- migration
- design-system
remote:
- source: github
  id: '132'
  url: https://github.com/GrueneAT/vorlagen/issues/132
---

## Kontext

Die Vorlagen (Scribus-`.sla` → PDF-Pipeline, DSL via `templates/*/build.py`)
nutzen aktuell die **proprietäre Schrift Gotham Narrow** (Default
`DFONT="Gotham Narrow Black"`, Stile in *Book/Bold/Black/Ultra*) sowie weitere
Fremdschriften (**Minion Pro**, **Times Roman**, **Tahoma**). Issue #42 hat
freie Ersatzschriften recherchiert und eine Schriften-Vergleichsseite gebaut;
**Barlow Semi Condensed** wurde als Ersatz beschlossen. Dieses Issue ist der in
#42 angekündigte Folge-Schritt: der eigentliche Austausch in allen
Produktions-Templates — analog zum bereits umgesetzten Bildgenerator
(Issue z6qfk dort).

## Ziel

Alle Vorlagen verwenden **ausschließlich Barlow Semi Condensed**. Keine
Fremd-/Proprietärschrift mehr in den Templates. Die Schriften-Vergleichsseite
(„Schriftvergleiche") wird entfernt. Da die alten Baseline-/Ausgangs-PDFs nach
dem Schriftwechsel nicht mehr passen, werden **neue Baseline-PDFs** als
Vergleichsziel erzeugt — erst nachdem visuell bestätigt ist, dass Ausrichtung
und Zentrierung jedes Texts auf jeder Seite korrekt sind.

## Umfang / Vorgehen

### 1. Schriftaustausch in allen Templates
- Default-Schrift `DFONT`/`deffont` `Gotham Narrow Black` → `Barlow Semi Condensed`.
- Alle Font-Referenzen in `templates/*/build.py` (16+ Templates) und in den
  `*-original.sla` ersetzen. Gewicht-Mapping (gleicher Ansatz wie Bildgenerator,
  Barlows verfügbare Schnitte Regular/Bold/ExtraBold/Black):

  | Alt | Neu (Barlow Semi Condensed) |
  | :-- | :-- |
  | Gotham Narrow Book | Regular (400) |
  | Gotham Narrow Bold | Bold (700) |
  | Gotham Narrow Black | Black (900) |
  | Gotham Narrow Ultra | Black (900) |
  | Minion Pro / Times Roman / Tahoma | Barlow Semi Condensed (passender Schnitt) |

- **KORREKTUR (User 2026-06-07): Vollkorn bleibt** — nur **Gotham** wird ersetzt.
  Nach dem Austausch darf keine **Gotham/Minion/Times/Tahoma**-Family mehr in den
  Templates stehen (verifiziert per grep). **Vollkorn Black/Bold Italic bleibt**
  als Akzent/Emphasis (Design-System `--gat-font-emphasis`). Zielbild:
  Barlow (vormals Gotham) + Vollkorn (Akzent).

### 2. Lokale Font-Bereitstellung für Scribus
- Scribus rendert PDFs **lokal** und kann keine Webfont per CDN ziehen — Barlow
  muss als lokale Font-Datei für fontconfig/Scribus verfügbar sein. Barlow ist
  **SIL OFL** und darf daher (wie das bereits vendorisierte Vollkorn) im Repo
  liegen bzw. über `Dockerfile.claude` installiert werden. Das ist die bewusste
  Druck-Pipeline-Ausnahme zur No-Vendoring-Regel (analog Vollkorn hier,
  mupdf/sqlite in gemeindefinanzen) — **kein** Webfont-CDN-Ansatz für die
  PDF-Erzeugung.
- `Dockerfile.claude` Font-Install + fontconfig-Sanity-Check auf Barlow
  erweitern; `fc-match "Barlow Semi Condensed"` muss eine Barlow-TTF liefern.

### 3. Schriftvergleiche entfernen
Die komplette Vergleichs-Feature entfernen (von #42): Astro-Seite
`site/src/pages/schriften/index.astro`, Daten `site/src/data/schriften.json` +
`schriften-bewertung.json`, Build-Tool `tools/fonts_compare_build.py`,
generierte Artefakte `site/public/schriften/` und
`templates/flyer-a6-hochformat-gruenes-cover/fonts/`, Nav-Link zu `/schriften/`,
sowie die nicht mehr benötigten Alternativ-Fonts unter
`shared/fonts/alternatives/` (+ `alternatives.yml`). `tools/font_variants.py`
nur entfernen, wenn nirgends sonst genutzt (sonst behalten).

### 4. Visuelles Review ALLER neu gerenderten Template-Seiten
- Templates neu rendern (`bin/render-gallery`, ggf. ohne Visual-Diff gegen die
  noch alten Baselines), dann **jede gerenderte Seite jedes Templates visuell
  prüfen**: Sitzt jeder Text sauber, stimmt **Zentrierung und Ausrichtung** auf
  der Seite (keine Überläufe, keine verrutschten/abgeschnittenen Texte durch
  Barlows abweichende, schmälere Metrik)?
- **Mehrere visuelle Vergleiche** durchführen, um sicher zu sein. Auffälligkeiten
  (Überlauf/Fehlausrichtung) im Template korrigieren und erneut rendern, bis alle
  Seiten sauber sind.

### 5. Neue Baseline-/Ausgangs-PDFs erzeugen
- **Erst nach** bestätigtem visuellem Review: die neu gerenderten PDFs als neue
  `baseline.pdf` je Template (und die `*-original.pdf`, soweit sinnvoll) als
  künftiges Vergleichsziel festschreiben. Ggf. `TOLERANCES.yml` anpassen.
- Vorschau-Artefakte (PNGs, `preview.pdf`) und Staleness-Metadaten konsistent
  aktualisieren, damit der CI-Stale-Previews-Gate grün ist.

## Akzeptanzkriterien

- [ ] Default-Schrift aller Templates ist Barlow Semi Condensed; `grep -rin "gotham\|minion\|tahoma\|times roman"` über `templates/` und `*.sla` ist sauber (keine Nicht-Barlow-Family mehr)
- [ ] Barlow ist lokal für Scribus/fontconfig bereitgestellt; `fc-match "Barlow Semi Condensed"` liefert eine Barlow-TTF; Renders zeigen Barlow (kein DejaVu-Fallback)
- [ ] Schriftvergleiche-Feature vollständig entfernt (Seite, Daten, Build-Tool, generierte Artefakte, Nav-Link, Alternativ-Fonts) — keine toten Referenzen/Links
- [ ] Alle Templates neu gerendert; **jede Seite visuell geprüft** — Text-Ausrichtung und Zentrierung korrekt, keine Überläufe/Abschnitte (mehrere visuelle Vergleiche dokumentiert)
- [ ] Neue Baseline-PDFs als Vergleichsziel erzeugt; Visual-Diff/Tests laufen gegen die neuen Baselines grün; CI-Stale-Previews-Gate grün
- [ ] Kein Werkzeug-Attribut in Commits/Code; Druck-Pipeline-Font-Ausnahme dokumentiert

## Hinweise / Risiken

- Barlow ist **schmäler** als Gotham Narrow → Zeilenumbrüche, Textbox-Füllung
  und optische Zentrierung verschieben sich; deshalb der Pflicht-Schritt
  „visuelles Review jeder Seite vor Baseline-Festschreibung".
- Kein Re-Litigieren der Schriftwahl (in #42 entschieden: Barlow Semi Condensed).
- Scribus-Rendering ist nur im Dev-Container verfügbar; CI rendert nicht,
  sondern prüft Staleness — die neuen Baselines/Previews müssen lokal erzeugt und
  committet werden.
