---
id: yvz4l
title: Schrift-Tooling auf Raleway nachziehen (Barlow-Reste entfernen, Render-Guard-Bug
  fixen)
status: open
priority: high
labels:
- fonts
- tech-debt
---

## Kontext

Das vorlagen-**Produkt** ist bereits vollständig auf Raleway umgestellt: 0 Barlow-`.sla`, 293 Raleway-`.sla`, ausgelieferte `site/public/templates/**` Barlow-frei, alle `templates/*/build.py` setzen `font='Raleway …'`. Raleway ist im `Dockerfile.claude` installiert und in der Font-Auflösung (`tools/sla_lib/builder/headline.py` `_FONT_FILE_HINTS`) vorhanden.

Die **Tooling-Schicht** ist aber nur halb migriert. Ein blindes „Barlow/Gotham überall entfernen" würde den IDML-Importer und das Ascent-Test-Harness brechen. Diese Aufgabe zieht das Tooling sauber nach.

## Aufgaben

1. **Render-Guard-Bug (funktional, höchste Prio).** `tools/render_pipeline.py:_verify_brand_fonts()` verweigert den Render, wenn fc-list < 5 Faces für `gotham narrow|vollkorn` hat. Es prüft NICHT Raleway → es schützt die ALTE Schrift und gibt falsche Sicherheit (Scribus könnte für Raleway still auf DejaVu zurückfallen, ohne dass der Guard auslöst). Regex auf `raleway|vollkorn` umstellen.

2. **Barlow-Fallback in `headline.py` retten.** Legacy-Einträge `("barlow semi condensed", …)` in `_FONT_FILE_HINTS` entfernen (kein Template nutzt Barlow mehr).

3. **Vendored Barlow entfernen.** `fonts/barlow-semi-condensed/*.ttf` + OFL.txt löschen, Barlow-Install-Block im `Dockerfile.claude` (Zeilen ~117–135) raus, `.gitignore`-Exception-Einträge raus.

4. **Barlow-Testfixtures migrieren.** `tools/sla_lib/tests/test_headline_stack.py` nutzt echtes „Barlow Semi Condensed Black" als bekannte-Ascent-Referenz (`ascent == 1.0em`). Auf Raleway umstellen und Ascent-Assertions auf Raleways tatsächliche Metriken neu kalibrieren. `test_headline_spacing_audit.py` hat den Wert schon auf „Raleway Black" migriert, aber die Variable heißt noch `BARLOW` — umbenennen.

5. **Gotham NICHT entfernen, wo es Input-Handling ist.** `tools/idml_to_dsl.py` (~21 Refs), `tools/sla_to_dsl.py` (`DEFFONT`-Default „Gotham Narrow Book"), `tools/font_audit.py` parsen Quell-IDML/SLA, die in Gotham gesetzt wurden. Diese Referenzen sind funktional für den Import und bleiben. Kalibrierungs-Kommentare zu Gotham sind Fidelity-Historie.

6. **Gotham-Drop-Zone im Dockerfile** (proprietär, nur für Maintainer-Renders der Original-IDML) — entscheiden ob retained; hängt mit Aufgabe 1 + dem Guard zusammen.

## Verifikation (Pflicht)

Repräsentative Templates in Scribus neu rendern und PDFs gegen Baselines vergleichen (pdffonts + pdfplumber-Baseline), bevor gemerged wird. Keine reinen String-Replaces ohne Render-Check — Fidelity-sensibel.
