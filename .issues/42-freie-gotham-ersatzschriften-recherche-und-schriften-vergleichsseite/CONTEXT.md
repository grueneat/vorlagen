# CONTEXT — Issue 42: Freie Gotham-Ersatzschriften + Vergleichsseite

> Discuss-Phase. `/issue:work` wurde mit der Vorgabe gestartet, **ohne
> Rückfragen** durchzulaufen („context should be clear enough"). Entscheidungen
> daher autonom; Umfang exakt wie in den `/issue:new`-Antworten.

## Problem (aus ISSUE.md)
Gotham Narrow ist proprietär (Hoefler & Co.) und liegt nur in einer gitignorierten
Drop-Zone (`/root/workspace/fonts/`). Solange die Vorlagen Gotham brauchen, lassen
sie sich nicht frei weitergeben. Es braucht freie, ausreichend ähnliche Ersatz-
schriften und eine Entscheidungsgrundlage, um eine davon zu wählen.

## Entscheidungen

### D1 — Umfang
Nur **Recherche + Vergleichsseite** (User-Antwort). Der echte Austausch von Gotham
in den Produktions-Templates ist ein Folge-Issue. Diese Iteration ändert **keine**
Produktions-`build.py`/`template.sla`.

### D2 — Anzahl & Auswahl
**Genau 5** freie Schriften (User-Antwort). Auswahl + Begründung: siehe RESEARCH.md
(Montserrat, Outfit, Urbanist, Raleway, Barlow Semi Condensed) — alle SIL OFL,
kommerzielle Nutzung und Einbettung erlaubt.

### D3 — Mechanismus Font-Tausch
**SLA-Postprocessing** analog zum Impressum-Tool aus Issue 41: das committete
`templates/flyer-a6-hochformat-gruenes-cover/template.sla` wird kopiert und die
`FONT="…"`-Attribute (sowie Font-Referenzen in den Stildefinitionen) per Mapping
umgeschrieben. Kein Parametrisieren der `build.py`, kein Eingriff in die DSL.

### D4 — Schriftdateien werden im Repo gebündelt
Anders als Gotham **dürfen** OFL-Schriften redistribuiert werden. Die 5 Familien
werden in `shared/fonts/alternatives/<slug>/` eingecheckt (inkl. `OFL.txt`).
Damit ist die Vergleichsseite reproduzierbar und der Renderer findet die Schriften.

### D5 — Vergleichsseite
Neue Seite unter `site/src/pages/schriften/`, von `index.astro` aus verlinkt —
analog zur „Design-Experimente"-Karte. Darstellung: **eine Zeile pro Flyer-Seite**
(der Flyer hat 6 Seiten), je Zeile **5 Vorschaubilder** (eine pro Schrift). Beim
Öffnen einer Seite Lightbox mit Umschaltung **zwischen den 5 Font-Versionen
derselben Seite** (Wiederverwendung des Lightbox-Musters aus Issue #28).

### D6 — Gerenderte Artefakte
Pro Schrift: eine Variant-SLA, ein **PDF** und Seiten-**PNGs** (+ hires), erzeugt
von einem neuen Build-Tool. Rendering braucht Scribus + die installierten
Schriften (lokaler `bin/render-gallery`-Pfad). Ist Scribus in der Executor-Umgebung
nicht verfügbar, werden Tooling + Variant-SLAs + Seite committet und der
Render-Schritt klar als Maintainer-Schritt markiert (wie `gallery_build.py`
copy-only ist).

### D7 — Deutsche Kurz-Zusammenfassung je Schrift
Pflicht laut User-Nachtrag: je Schrift ein deutscher Text — Ähnlichkeit zu Gotham,
Vor-/Nachteile im Vergleich, Unterschiede, Einsatzempfehlung. Liegt in
`shared/fonts/alternatives.yml` und wird auf der Seite angezeigt.

### D8 — Layout-Treue
Die Alternativen haben andere Metriken als Gotham Narrow → Text kann umbrechen/
überlaufen. Das ist **gewollt sichtbar** (genau das soll der Vergleich zeigen).
Kein per-Font-Layout-Tuning in dieser Iteration.

### D9 — Gewichts-Mapping
Gotham Narrow Book → Regular · Bold → Bold · Black → ExtraBold · Ultra → Black
(Feinschliff dem Executor überlassen, Empfehlung in RESEARCH.md).

## Bewusst verschoben
- Austausch von Gotham in den echten Templates (Folge-Issue).
- Per-Font-Layout-Anpassung / Overflow-Korrektur.
- Weitere Templates außer `flyer-a6-hochformat-gruenes-cover`.
