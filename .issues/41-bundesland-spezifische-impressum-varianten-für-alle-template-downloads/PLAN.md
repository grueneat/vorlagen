# PLAN — Issue 41: Bundesland-spezifische Impressum-Varianten

> v1 / iterativer erster Wurf (siehe CONTEXT.md). Mechanismus generisch über
> alle Templates; bewusst verschoben: per-Bundesland-PDFs, Overflow-Handling.
> Quelle der Fakten: RESEARCH.md. Diese Datei IST der Auftrag an den Executor.

## Konventionen
- Arbeitsverzeichnis: das Issue-Worktree, Branch `issue/41-bundesland-…`.
- Commits atomar, Conventional-Commit + `41:`-Präfix (Repo-Konvention).
- Keine „claude"-Attribution in Commits/Code/Kommentaren.
- Python: PEP 8, knappe Kommentare; `ruff`/`mypy` falls im Repo vorhanden.
- Nach den Code-Tasks: `python3 tools/impressum.py --all` und
  `python3 tools/gallery_build.py` laufen lassen; erzeugte Artefakte committen.

---

<task id="T1" title="Zentrale Impressum-Datenquelle anlegen">
Lege `shared/impressum/bundeslaender.yml` mit **exakt** folgendem Inhalt an:

```yaml
# shared/impressum/bundeslaender.yml
#
# Impressum-Bausteine je Landesorganisation der Grünen.
# Quelle: jeweilige <land>.gruene.at/impressum-Seite, Stand 2026-05-20.
#
# MAINTAINER: Diese Angaben sind rechtspflichtig (österr. Mediengesetz §§ 24/25).
# Vor Veröffentlichung juristisch verifizieren — Adressen/Namen können sich ändern.
#
# Schema:
#   default:       slug des Fallback-Bundeslandes (hat immer ein gültiges Impressum)
#   bundeslaender: Liste mit slug, name, impressum (1 Zeile), druck (separat, optional), quelle
default: noe
bundeslaender:
  - slug: bgld
    name: Burgenland
    impressum: "Die Grünen – Die Grüne Alternative Burgenland, Hauptstraße 38/Top 5, 7000 Eisenstadt"
    druck: ""
    quelle: "https://burgenland.gruene.at/impressum"
  - slug: ktn
    name: Kärnten
    impressum: "Die Grünen Kärnten – Landesorganisation, Bahnhofstraße 38a, 9020 Klagenfurt"
    druck: ""
    quelle: "https://kaernten.gruene.at/impressum"
  - slug: noe
    name: Niederösterreich
    impressum: "Die Grünen Niederösterreich, Daniel-Gran-Straße 48, 3100 St. Pölten"
    druck: ""
    quelle: "https://noe.gruene.at/impressum"
  - slug: ooe
    name: Oberösterreich
    impressum: "Die Grünen – Die Grüne Alternative Oberösterreich, Landgutstraße 17, 4040 Linz"
    druck: ""
    quelle: "https://ooe.gruene.at/impressum"
  - slug: sbg
    name: Salzburg
    impressum: "Die Grünen Salzburg, Glockengasse 6, 5020 Salzburg"
    druck: ""
    quelle: "https://salzburg.gruene.at/impressum"
  - slug: stmk
    name: Steiermark
    impressum: "Die Grünen Steiermark, Kaiserfeldgasse 5–7, 8010 Graz"
    druck: ""
    quelle: "https://stmk.gruene.at/impressum"
  - slug: tirol
    name: Tirol
    impressum: "Die Grünen – Die Grüne Alternative Tirol, Müllerstraße 7, 6020 Innsbruck"
    druck: ""
    quelle: "https://tirol.gruene.at/impressum"
  - slug: vbg
    name: Vorarlberg
    impressum: "Die GRÜNEN – Grüne Alternative Vorarlberg, St.-Anna-Straße 1/Top 7, 6900 Bregenz"
    druck: ""
    quelle: "https://vorarlberg.gruene.at/impressum"
  - slug: wien
    name: Wien
    impressum: "Die Grünen – Grüne Alternative Wien, Würtzlerstraße 3/3, 1030 Wien"
    druck: ""
    quelle: "https://wien.gruene.at/impressum"
```

Commit: `41: feat(impressum): add Bundesland impressum data source`
</task>

<task id="T2" title="SLA-Impressum-Postprozessor tools/impressum.py">
Neue Datei `tools/impressum.py`. Funktionen:

- `load_bundeslaender(path=None) -> dict` — lädt die YAML; gibt
  `{"default": slug, "bundeslaender": [..]}` zurück. Default-Pfad:
  `<repo>/shared/impressum/bundeslaender.yml`.
- `find_impressum_frames(root) -> list` — nimmt das geparste SLA-`ElementTree`-
  Root, liefert alle `PAGEOBJECT`-Elemente, deren konkatenierter `ITEXT/@CH`-Text
  (case-insensitive) den Teilstring `impressum` enthält.
- `apply_impressum(sla_path, out_path, entry) -> int` — parst die SLA, ersetzt
  in **jedem** Impressum-Frame die gesamte Story durch **einen** `ITEXT`-Run mit
  dem Text `"Impressum: " + entry["impressum"]` (plus `" " + entry["druck"]`
  falls `druck` nicht leer). Der neue `ITEXT` übernimmt die Zeichenattribute
  (FONT, FONTSIZE, FCOLOR, FONTSET, … alle Attribute außer `CH`) des **ersten**
  bestehenden `ITEXT` des Frames. Alle bisherigen `ITEXT`- und `para`-Kindknoten
  des Frames werden entfernt, danach der neue `ITEXT` + ein abschließendes
  `para`-Element eingefügt (Story-Konvention von Scribus beibehalten — am
  Original-Frame ablesen). Schreibt nach `out_path`. Rückgabe: Anzahl ersetzter
  Frames. Wirf `RuntimeError`, wenn 0 Frames gefunden wurden.
- CLI `main()`:
  - `python3 tools/impressum.py --all` — walkt `templates/*/`, nimmt je Template
    `template.sla` (überspringt Verzeichnisse mit Präfix `_` und solche ohne
    `template.sla`), erzeugt `templates/<id>/impressum/<slug>.sla` für **jedes**
    Bundesland. Gibt pro Datei eine Zeile aus.
  - `python3 tools/impressum.py <sla> <slug>` — Einzelfall, schreibt nach stdout-
    Pfad bzw. `<sla-dir>/impressum/<slug>.sla`.
  - Unbekannter slug → Fehler. Fehlt für ein Bundesland ein Datensatz, greift
    der `default` (relevant nur konzeptionell; alle 9 sind vorhanden).

XML-Handling mit `xml.etree.ElementTree`. SLA-Encoding ist UTF-8; beim Schreiben
`encoding="UTF-8"`, `xml_declaration=True`. Keine Scribus-Abhängigkeit.

Commit: `41: feat(impressum): SLA impressum substitution tool`
</task>

<task id="T3" title="Test für den Postprozessor">
Lege einen Test an (Ort an bestehendem Testlayout orientieren — `tools/sla_lib/tests/`
oder `tests/`). Mindestens:
- `load_bundeslaender()` liefert 9 Einträge und einen gültigen `default`.
- `apply_impressum` auf eine reale `template.sla` (z. B.
  `templates/flyer-a6-querformat-portraet/template.sla`) ersetzt ≥1 Frame, und
  die erzeugte SLA enthält den Bundesland-Impressumstext und **nicht mehr**
  `xxxxxx`.
- `apply_impressum` wirft, wenn die SLA keinen Impressum-Frame hat (synthetische
  Mini-SLA oder Monkeypatch).

Test grün laufen lassen. Commit: `41: test(impressum): cover substitution tool`
</task>

<task id="T4" title="Render-Pipeline: per-Bundesland-SLAs erzeugen">
In `tools/render_pipeline.py` nach dem Schritt `build.py → template.sla`
(und vor/nach dem PDF-Schritt) einen Aufruf ergänzen, der für das Template alle
per-Bundesland-SLAs nach `templates/<id>/impressum/<slug>.sla` schreibt
(`impressum.apply_impressum` wiederverwenden). Idempotent halten (gleicher Input
→ gleicher Output, kein Git-Diff bei Doppellauf). Der Schritt darf den
bestehenden PDF/PNG/Diff-Fluss nicht verändern. Wenn die Pipeline-Struktur den
Hook erschwert, genügt es, `tools/impressum.py --all` als eigenständigen
Pipeline-Schritt aufzurufen.

Commit: `41: feat(render): emit per-Bundesland impressum SLAs`
</task>

<task id="T5" title="gallery_build.py: Downloads je Bundesland">
`tools/gallery_build.py`, Non-Family-Zweig: zusätzlich `templates/<id>/impressum/*.sla`
nach `site/public/templates/<id>/impressum/` kopieren. `meta["_downloads"]` so
aufbauen, dass es **eine Zeile pro Bundesland** ist:
```python
{"label": "<Bundesland-Name>", "bundesland": "<slug>",
 "sla": f"/templates/{tid}/impressum/<slug>.sla"}
```
Reihenfolge = Reihenfolge in `bundeslaender.yml`. Den bisherigen generischen
`template.sla`-Download **entfernen** (nur impressumtragende Varianten dürfen
erreichbar sein). `preview.pdf` weiterhin kopieren; den Pfad als
`meta["_preview_pdf"] = f"/templates/{tid}/preview.pdf"` für die gemeinsame
Vorschau bereitstellen. `_previews` (PNGs) unverändert lassen.
Fehlen die `impressum/*.sla`, mit klarer FATAL-Meldung abbrechen (analog
`_fail_missing`) und auf `bin/render-gallery` bzw. `tools/impressum.py --all`
verweisen.

Commit: `41: feat(gallery): per-Bundesland downloads in gallery build`
</task>

<task id="T6" title="Astro-Content-Schema anpassen">
`site/src/content.config.ts`: das Schema für `_downloads`-Einträge so erweitern,
dass `bundesland` (string, optional) und ein optionaler `pdf` erlaubt sind, und
ein optionales `_preview_pdf` (string) am Template. Bestehende Felder nicht
brechen. Falls `_downloads` dort gar nicht typisiert ist (nur lose), minimal
ergänzen, ohne andere Templates zu stören.

Commit: `41: feat(site): allow Bundesland fields in template schema`
</task>

<task id="T7" title="Download-Liste je Bundesland auf der Template-Seite">
`site/src/pages/templates/[...id].astro`, `<h2>Download</h2>`-Block:
- Statt SLA+PDF pro Zeile: eine gruppierte Liste „SLA je Bundesland" —
  je `_downloads`-Eintrag eine Zeile `<li>{d.label}: <a href={url(d.sla)}>SLA herunterladen</a></li>`.
- Über der Liste ein kurzer Hinweis: „Bitte die Vorlage mit dem Impressum eures
  Bundeslandes herunterladen." (deutscher Text, zur restlichen Seite passend).
- Die gemeinsame Vorschau-PDF separat verlinken, wenn `t.data._preview_pdf`
  gesetzt ist (`<a href={url(t.data._preview_pdf)}>Vorschau-PDF</a>`).
- Keine impressumlose `template.sla`-Verlinkung mehr.
Statische Astro-Seite, kein Framework — Stil der bestehenden Inline-Struktur folgen.

Commit: `41: feat(site): grouped per-Bundesland download list`
</task>

<task id="T8" title="Artefakte erzeugen, Galerie bauen, verifizieren">
- `python3 tools/impressum.py --all` ausführen → `templates/*/impressum/<slug>.sla`
  für alle 16 Templates × 9 Bundesländer.
- `python3 tools/gallery_build.py` ausführen → `site/src/content/templates/*.md`
  + `site/public/templates/*/impressum/*.sla` aktualisiert.
- Verifizieren: `grep -rl "xxxxxx" templates/*/impressum/` liefert **nichts**;
  jede erzeugte SLA enthält einen Impressumstext. Stichprobe: in einer
  `tirol.sla` steht „Innsbruck", in einer `noe.sla` „St. Pölten".
- Die erzeugten `templates/*/impressum/*.sla`, die aktualisierten Site-Dateien
  und `site/public/...` committen.
Commit(s): `41: chore(impressum): generate Bundesland SLA variants` und
`41: chore(gallery): rebuild gallery with Bundesland downloads`
</task>

## Abnahmekriterien-Mapping
- Zentrale Datenquelle alle 9 + dokumentiert → T1.
- Standardtext-Fallback (`default: noe`) → T1, T2.
- Druckhinweis getrennt (`druck`-Feld) → T1, T2.
- Auto-Slot-Erkennung über „Impressum" in allen Templates → T2.
- Varianten je Bundesland gerendert (SLA) → T4, T8.
- Keine Variante mit `xxxxxx` → T8 (grep-Gate).
- Website-Downloads je Bundesland, keine impressumlose Option → T5, T7.
- Nur einmal gewendet (Geometrie unverändert) → T2 (rein textuelle Substitution).
