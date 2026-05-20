# PLAN — Issue 42: Freie Gotham-Ersatzschriften + Vergleichsseite

> Diese Datei IST der Auftrag an den Executor. Fakten: RESEARCH.md.
> Entscheidungen/Umfang: CONTEXT.md. Umfang bewusst eng: nur Vergleichsseite,
> nur das Template `flyer-a6-hochformat-gruenes-cover`, kein Eingriff in
> Produktions-Templates.

## Konventionen
- Arbeitsverzeichnis: Issue-Worktree, Branch `issue/42-freie-gotham-…`.
- Atomare Commits, Conventional-Commit + `42:`-Präfix.
- Keine „claude"/AI-Attribution irgendwo.
- Python: PEP 8, knappe Kommentare; `ruff`/`mypy` falls vorhanden.
- Reuse, wo möglich: das Impressum-SLA-Postprocessing aus Issue 41
  (`tools/impressum.py`) ist das Vorbild für den Font-Tausch.

---

<task id="T1" title="5 OFL-Schriften bündeln + Datenquelle anlegen">
Die 5 in RESEARCH.md §2 gewählten Familien sind **SIL OFL** und dürfen im Repo
liegen. Für jede Familie unter `shared/fonts/alternatives/<slug>/` ablegen:
- die statischen `.ttf` der vier benötigten Schnitte (Regular, Bold, ExtraBold,
  Black) — Bezug aus `github.com/google/fonts` Pfad `ofl/<familie>/`
  (raw.githubusercontent.com). Variable Fonts sind ok, falls keine statischen
  Schnitte vorliegen — dann die `[wght]`-VF übernehmen.
- die zugehörige `OFL.txt`.

slugs: `montserrat`, `outfit`, `urbanist`, `raleway`, `barlow-semi-condensed`.

Datenquelle `shared/fonts/alternatives.yml` anlegen — Schema:
```yaml
# Freie, SIL-OFL-lizenzierte Gotham-Alternativen für die Schriften-Vergleichsseite.
# Quelle/Begründung: .issues/42-…/RESEARCH.md
target: "Gotham Narrow"           # die zu ersetzende proprietäre Schrift
flyer: flyer-a6-hochformat-gruenes-cover
fonts:
  - slug: montserrat
    name: Montserrat
    license: SIL OFL 1.1
    source: "https://github.com/google/fonts/tree/main/ofl/montserrat"
    family: "Montserrat"          # fontconfig-Family-Name
    weights:                       # Gotham-Narrow-Schnitt -> Ersatz-Schnitt
      Book: Regular
      Bold: Bold
      Black: ExtraBold
      Ultra: Black
    summary: >-
      <deutsche Kurz-Zusammenfassung — VERBATIM aus RESEARCH.md §2, Eintrag 1>
  - slug: outfit
    ...
```
Die `summary`-Texte **wörtlich** aus RESEARCH.md §2 (die 5 nummerierten Einträge:
Warum ähnlich / Vorteile / Nachteile / Unterschied / Einsatz) übernehmen.
Das `weights`-Mapping je Schrift gemäß RESEARCH.md §2 (Empfehlungstabelle); pro
Schrift an die tatsächlich vorhandenen Schnitte anpassen.

Commit: `42: feat(fonts): bundle 5 OFL Gotham alternatives + data source`
</task>

<task id="T2" title="Font-Tausch-SLA-Postprozessor tools/font_variants.py">
Neue Datei `tools/font_variants.py`. Wie `tools/impressum.py` arbeitet es auf
der Scribus-SLA-XML.
- `load_alternatives(path=None) -> dict` — lädt `shared/fonts/alternatives.yml`.
- `apply_font(sla_path, out_path, font_entry) -> int` — parst die SLA, ersetzt
  **jede** Schrift-Referenz der vier `Gotham Narrow <Schnitt>`-Familien durch
  `"<family> <Ersatz-Schnitt>"` gemäß `weights`-Mapping. Zu ersetzen sind:
  `FONT="…"`-Attribute auf `ITEXT`, sowie Font-Referenzen in Stil-Definitionen
  (`<STYLE FONT="…">`, `<CHARSTYLE FONT="…">` o. ä. — alle Attribute namens
  `FONT` mit Wert-Präfix `Gotham Narrow`). **Nicht** anfassen: `Minion Pro
  Regular`, `Vollkorn Black Italic`. Rückgabe: Anzahl ersetzter Referenzen;
  `RuntimeError`, wenn 0.
- CLI: `python3 tools/font_variants.py --all` erzeugt für
  `templates/flyer-a6-hochformat-gruenes-cover/template.sla` je Schrift eine
  Variant-SLA unter
  `templates/flyer-a6-hochformat-gruenes-cover/fonts/<slug>/<slug>.sla`.
  Idempotent (Doppellauf → kein Git-Diff).

Der gewünschte Ziel-Family-Name muss zu dem passen, unter dem fontconfig die
Schrift registriert (T4). Hat eine Familie keine eigenständig registrierten
Schnitt-Familiennamen, in T4 einen fontconfig-Alias analog
`shared/fonts/50-vollkorn-family-alias.conf` anlegen.

Commit: `42: feat(fonts): SLA font-family substitution tool`
</task>

<task id="T3" title="Test für den Font-Tausch">
Test (Ort am bestehenden Layout orientieren, z. B. `tools/sla_lib/tests/`):
- `load_alternatives()` liefert genau 5 Einträge, jeder mit `summary`,
  `weights` (4 Schlüssel) und gebündelten Schriftdateien-Pfaden.
- `apply_font` auf `templates/flyer-a6-hochformat-gruenes-cover/template.sla`
  ersetzt ≥1 Referenz; Ergebnis enthält den neuen Family-Namen und **kein**
  `Gotham Narrow` mehr; `Minion Pro Regular` / `Vollkorn Black Italic` bleiben
  erhalten.
Test grün. Commit: `42: test(fonts): cover font substitution tool`
</task>

<task id="T4" title="Rendering: Vergleichs-Artefakte + Build-Tool">
Neues Tool `tools/fonts_compare_build.py`, das orchestriert:
1. Schriften installieren: die T1-Schriften nach
   `/usr/local/share/fonts/gruene/` kopieren + `fc-cache -f`; bei Bedarf
   fontconfig-Alias für die Ziel-Family-Namen anlegen. `fc-match` zur
   Verifikation. (Gotham bleibt für das Original installiert/irrelevant.)
2. Variant-SLAs erzeugen (T2 wiederverwenden).
3. Je Schrift die Variant-SLA → PDF rendern. Bestehende Render-Helfer
   wiederverwenden: `render_sla_to_pdf` / `rasterise` aus `tools/visual_diff.py`
   (so nutzt es auch `tools/render_pipeline.py`). PDF → Seiten-PNGs (`page-NN.png`)
   + hires-PNGs, analog `render_pipeline.py` (DPI-Konstanten dort).
4. Artefakte ablegen unter
   `templates/flyer-a6-hochformat-gruenes-cover/fonts/<slug>/`
   (`<slug>.pdf`, `<slug>-page-NN.png`, `<slug>-page-NN-hires.png`) und nach
   `site/public/schriften/<slug>/` kopieren.
5. Datendatei `site/src/data/schriften.json` schreiben mit der Struktur, die
   die Seite (T5) braucht: Liste der Schriften (slug, name, summary, license,
   source, pdf-Pfad) und pro Flyer-Seite (1..6) je Schrift der PNG-/hires-Pfad.

**Falls Scribus in der Ausführungsumgebung fehlt** (`command -v scribus` leer):
Schritte 1–2 und 5 trotzdem ausführen (Variant-SLAs + Datendatei mit den
SLA-Pfaden), Schritt 3–4 überspringen und in EXECUTION.md klar als
Maintainer-Schritt (`bin/render-gallery`-Pfad im Dev-Container) vermerken.
Die Seite (T5) muss in beiden Fällen funktionieren (PNG fehlt → SLA-Link/Hinweis).

Commit: `42: feat(fonts): font-comparison render + build tool`
</task>

<task id="T5" title="Schriften-Vergleichsseite">
Neue Seite `site/src/pages/schriften/index.astro`:
- Importiert `site/src/data/schriften.json` (T4) und zeigt:
  - Kopf: kurze deutsche Erklärung (frei lizenzierte Gotham-Alternativen,
    gerendert am Flyer „Flyer A6 Hochformat – Grünes Cover").
  - **Schriften-Legende**: je Schrift Name, Lizenz, Quelle und die deutsche
    `summary`.
  - **Vergleichsraster**: **eine Zeile pro Flyer-Seite** (6 Zeilen). Je Zeile
    **5 Vorschaubilder** nebeneinander (eine Spalte pro Schrift, gleiche
    Reihenfolge wie die Legende), darüber/darunter die Seitennummer.
  - Klick auf ein Vorschaubild → **Lightbox**; in der Lightbox lässt sich
    **zwischen den 5 Schrift-Versionen derselben Flyer-Seite** umschalten
    (Buttons + Pfeiltasten). Lightbox-Muster aus
    `site/src/pages/templates/[...id].astro` (Issue #28) wiederverwenden;
    plain HTML + `is:inline`-Script, kein Framework.
  - Pro Schrift ein Link zum gerenderten **PDF** (bzw. zur Variant-SLA, falls
    kein PDF gerendert wurde).
- `BASE_URL`/`url()`-Helper wie in den anderen Seiten verwenden.
- Falls eine Astro-Content-Collection sauberer ist als der JSON-Import:
  zulässig — dann `site/src/content.config.ts` entsprechend erweitern, ohne
  bestehende Collections zu brechen.

Commit: `42: feat(site): Schriften-Vergleichsseite`
</task>

<task id="T6" title="Verlinkung von der Startseite">
`site/src/pages/index.astro`: neben der „Design-Experimente"-Karte eine
gleichartige hervorgehobene Karte ergänzen, die auf `schriften/` verlinkt
(Titel z. B. „Freie Schriften", Untertitel: Vergleich freier Gotham-Alternativen
am Flyer-Beispiel). Gleicher Stil wie die bestehende Experimente-Karte.

Commit: `42: feat(site): link Schriften-Vergleich from gallery home`
</task>

<task id="T7" title="Build ausführen, verifizieren, committen">
- `python3 tools/font_variants.py --all` und `python3 tools/fonts_compare_build.py`
  ausführen.
- Verifizieren: 5 Variant-SLAs erzeugt; in keiner steht noch `Gotham Narrow`;
  `Minion Pro Regular`/`Vollkorn Black Italic` unverändert vorhanden.
  Wenn gerendert: je Schrift 6 Seiten-PNGs + PDF vorhanden;
  `site/src/data/schriften.json` valide und vollständig.
- Erzeugte Artefakte, Schriftdateien, Seite und `site/public/schriften/`
  committen.
- Falls Astro lokal baubar (`npx astro build` im `site/`): Build prüfen;
  sonst in EXECUTION.md als CI-/Maintainer-Check vermerken.
Commit(s): `42: chore(fonts): generate font-comparison artifacts`
</task>

## Abnahmekriterien-Mapping
- Exhaustive Recherche dokumentiert → RESEARCH.md §2 (Survey-Tabelle + Auswahl).
- Genau 5 freie Schriften, begründet, inkl. schmaler Option (Barlow Semi
  Condensed) → T1 + RESEARCH.md.
- Schriftdateien frei lizenziert + eingebunden → T1.
- Eigene, von der Startseite verlinkte Seite → T5 + T6.
- Deutsche Kurz-Zusammenfassung je Schrift → T1 (`summary`) + T5 (Anzeige).
- Flyer in 5 Font-Varianten als PDF gerendert → T4.
- Vorschau-/Lightbox wie Galerie → T5.
- Zeile = Flyer-Seite, 5 Vorschaubilder je Zeile → T5.
- Umschalten zwischen Font-Versionen derselben Seite → T5 (Lightbox).
- Keine Änderung an Produktions-Templates → Umfang: nur neue Dateien +
  `fonts/`-Unterordner; `build.py`/`template.sla` der Templates unberührt.
