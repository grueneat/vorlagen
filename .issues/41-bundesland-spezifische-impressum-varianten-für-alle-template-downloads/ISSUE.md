---
id: '41'
title: Bundesland-spezifische Impressum-Varianten für alle Template-Downloads
status: open
priority: high
labels:
- templates
- site
- impressum
- legal
source: github
source_id: 120
source_url: https://github.com/GrueneAT/vorlagen/issues/120
---

## Kontext / Problem

Aktuell tragen die Template-`build.py`-Skripte einen Impressum-Platzhalter (`Impressum: xxxxxx`). Auf der Website wird pro Vorlage genau ein Download (SLA + PDF) angeboten — ohne korrektes, landesspezifisches Impressum. Personen können so versehentlich eine Vorlage ohne gültiges Impressum verwenden, obwohl ein landesrechtlich vorgeschriebenes Impressum existiert.

## Ziel

Pro Vorlage soll es ausschließlich Download-Varianten **mit korrektem Impressum** geben — eine Variante pro Bundesland. Es darf keine Variante mehr geben, die kein oder ein beliebiges Impressum enthält.

## Anforderungen

- **Impressum-Datenquelle pro Landesorganisation**: Impressum-Bausteine aus den Bundesländer-Websites (`<land>.gruene.at`, z. B. `noe.gruene.at`, `tirol.gruene.at`) ermitteln und als zentrale, gepflegte Datenquelle ablegen (z. B. `shared/impressum/<bundesland>.yml`).
- **Abdeckung**: Alle 9 Bundesländer (Burgenland, Kärnten, Niederösterreich, Oberösterreich, Salzburg, Steiermark, Tirol, Vorarlberg, Wien). Wo kein verwertbares Impressum ermittelt werden kann, gilt ein definierter **Standardtext-Fallback** (z. B. Bundes-Impressum bzw. NÖ als Default).
- **Automatische Slot-Erkennung**: Textframes/Runs, die den Text „Impressum" enthalten (aktuell `Impressum: xxxxxx`), werden generisch über alle `templates/*/build.py` als Impressum-Slot identifiziert und konsistent ersetzt.
- **Druckhinweis separat**: Der Druck-/Herstellerhinweis („wer den Druck macht") ist ein eigenständig ersetzbarer Baustein — getrennt vom Impressum-Text.
- **Mehrfach-Rendering**: Pro Vorlage und Bundesland je eine fertige `.sla`/`.pdf`-Variante rendern (Vorlage mehrfach mit unterschiedlichem Impressum ausgeben).
- **Nur einmal wenden**: Die Vorlage wird weiterhin nur einmal gewendet (kein doppeltes Wenden); Default-Impressum z. B. NÖ oder Standardtext.
- **Website-Downloads pro Bundesland**: Der Download-Bereich bietet pro Vorlage eine Auswahl/Download je Bundesland statt eines generischen Downloads. Nur diese Varianten sind verfügbar — keine Impressum-lose Variante darf erreichbar sein.

## Umsetzungshinweise

- Impressum-Slot-Erkennung generisch (Run-Text enthält „Impressum") über alle Templates.
- Bundesland-Datenquelle zentral pflegen; Render-Pipeline iteriert über Bundesländer.
- Website (`site/src/content/templates/*.md` `_downloads`, `site/src/pages/templates/[...id].astro`) so erweitern, dass Downloads nach Bundesland gruppiert/auswählbar werden.
- Vorarbeit zu Self-Contained-Downloads siehe archiviertes Issue 39.

## Acceptance Criteria

- [ ] Zentrale Impressum-Datenquelle pro Bundesland (alle 9) existiert und ist dokumentiert; Quelle = jeweilige `<land>.gruene.at`-Seite.
- [ ] Standardtext-Fallback ist definiert und greift, wenn für ein Bundesland kein Impressum ermittelbar ist.
- [ ] Druck-/Herstellerhinweis ist ein vom Impressum getrennter, eigenständig ersetzbarer Baustein.
- [ ] Impressum-Slot wird in allen Templates automatisch über den Text „Impressum" erkannt und ersetzt.
- [ ] Für jede Vorlage werden Varianten pro Bundesland gerendert (SLA + PDF), jede mit korrektem Impressum.
- [ ] Keine gerenderte Variante ohne bzw. mit Platzhalter-Impressum (`xxxxxx`) verbleibt.
- [ ] Die Website bietet pro Vorlage Downloads je Bundesland an; keine Impressum-lose Download-Option ist erreichbar.
- [ ] Vorlagen werden weiterhin nur einmal gewendet.
