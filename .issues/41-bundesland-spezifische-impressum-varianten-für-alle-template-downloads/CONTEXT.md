# CONTEXT — Issue 41: Bundesland-spezifische Impressum-Varianten

> Discuss-Phase. Der User hat `/issue:work` mit der Vorgabe gestartet, **keine
> Rückfragen** zu stellen und **gute Defaults** zu wählen; ausdrücklich:
> „it can be iterative, so a simple first implementation is fine". Die folgenden
> Entscheidungen sind daher autonom getroffen und für einen schlanken v1 ausgelegt.

## Problem (aus ISSUE.md)

Templates tragen einen Impressum-Platzhalter (`Impressum: xxxxxx`). Die Website
bietet pro Vorlage genau einen Download ohne korrektes, landesspezifisches
Impressum. Personen könnten versehentlich eine Vorlage ohne gültiges Impressum
verwenden.

## Graubereiche & getroffene Entscheidungen

### D1 — Wo wird ersetzt: build.py-DSL vs. SLA-Postprocessing?
**Entscheidung: SLA-Postprocessing auf Frame-Ebene.** Die `build.py`-Skripte sind
pro Template verschieden (3 Slot-Varianten: `Impressum: xxxxxx`, `Impressum:`,
`Impressum`). Eine generische, template-unabhängige Erkennung „Textframe enthält
das Wort *Impressum*" — exakt wie vom User beschrieben — lässt sich nur am
gerenderten Artefakt (`template.sla`, Scribus-XML) zuverlässig umsetzen. So
bleibt der Mechanismus für alle 16 Templates und künftige Templates gleich.

### D2 — Abdeckung
**Entscheidung: alle 9 Bundesländer + Standard-Fallback** (User-Antwort in
`/issue:new`). Fallback-Bundesland = **Niederösterreich (`noe`)**. Findet die
Pipeline für ein Bundesland keinen Datensatz, gilt der `default`-Eintrag —
es entsteht nie eine impressumlose Variante.

### D3 — Datenquelle
**Entscheidung:** zentrale, gepflegte YAML-Datei `shared/impressum/bundeslaender.yml`.
Die Impressum-Texte wurden in der Research-Phase aus den `<land>.gruene.at/impressum`
-Seiten (Stand 2026-05) zusammengetragen — siehe RESEARCH.md. Sie sind als
**Medieninhaberin & Herausgeberin**-Zeile nach österr. Mediengesetz formuliert.
Da es um rechtspflichtige Angaben geht, trägt die Datei einen sichtbaren
`# MAINTAINER: vor Veröffentlichung juristisch verifizieren`-Header
(Liability-Grenze: das Produkt befüllt, prüft aber nicht rechtsverbindlich).

### D4 — Druckhinweis separat
**Entscheidung:** eigenes Feld `druck:` pro Bundesland-Eintrag, defaultmäßig leer.
Wenn gesetzt, wird es als getrennter Absatz **nach** dem Impressum angehängt.
Kein eigenes UI in v1.

### D5 — Umfang der gerenderten Artefakte (v1-Schnitt)
**Entscheidung:** v1 erzeugt pro Template und Bundesland eine **`.sla`-Variante**
(`templates/<id>/impressum/<slug>.sla`). Das ist das „Template-File", das der
User meint. **Keine** 9×16 PDF/PNG-Neurenderung in v1 — das Layout ist identisch,
nur der 6-pt-Impressumstext ändert sich; die bestehende gemeinsame `preview.pdf`
bleibt als Vorschau. Per-Bundesland-PDFs sind ein iteratives Folge-Increment.

### D6 — „nur einmal gewendet"
Die Substitution ist **rein textuell** — Frame-Geometrie, Seitenanordnung und
Wende-/Falzlogik bleiben unangetastet. Damit bleibt „nur einmal gewendet"
automatisch erhalten.

### D7 — Website
**Entscheidung:** der Download-Abschnitt listet pro Vorlage **eine SLA pro
Bundesland** (einfache gruppierte Liste, alphabetisch). Der generische
impressumlose `template.sla`-Download wird von der Seite **entfernt** — nur
impressumtragende Varianten sind erreichbar (Kernanforderung). `preview.pdf`
bleibt als gemeinsame Vorschau verlinkt.

## Bewusst verschoben (iterativ, NICHT in v1)
- Per-Bundesland gerenderte PDFs/PNGs.
- Textüberlauf-Behandlung / Frame-Resize bei langem Impressum.
- Eigenständige Druckerei-Auswahl-UI.
- Verifikations-Workflow für die Rechtstexte.
