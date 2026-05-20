# RESEARCH — Issue 41: Bundesland-spezifische Impressum-Varianten

## 1. Render- & Galerie-Pipeline (Ist-Zustand)

- **`tools/render_pipeline.py`** (CLI: `bin/render-gallery`) — pro Template:
  `build.py → template.sla`, dann `render_sla_to_pdf → preview.pdf`,
  `pdftoppm → page-NN.png`, Diffs, SHA. Familien-Templates (`meta.yml::type:
  family`) rendern pro Größe eigene `<code>.sla/.pdf`. Aktuell hat **kein**
  Template `type: family`.
- **`tools/gallery_build.py`** — *copy-only* nach Issue #4. Kopiert
  `template.sla` + `preview.pdf` + `page-*.png` nach
  `site/public/templates/<id>/` und schreibt `site/src/content/templates/<id>.md`
  mit Frontmatter aus `meta.yml`. Setzt `meta["_downloads"]` und
  `meta["_previews"]`.
  - Non-family-Zweig: `_downloads = [{label:"Vollständig (SLA + PDF)",
    sla:".../template.sla", pdf:".../preview.pdf"}]`.
  - Family-Zweig: `_downloads` = eine Zeile pro Größe — **dieses Muster ist die
    Vorlage für per-Bundesland-Downloads.**
- **`site/src/pages/templates/[...id].astro`** — `<h2>Download</h2>` rendert
  `t.data._downloads.map(d => <li>{d.label}: <a sla>SLA</a> · <a pdf>PDF</a>)`.
- **`site/src/content.config.ts`** — Astro-Content-Collection-Schema; `_downloads`
  ist dort als optionales Feld zu prüfen/erweitern (siehe PLAN).

## 2. Impressum-Slot in den Templates

16 Templates haben „Impressum" in `build.py`. Der Slot erscheint als DSL-`Run`
in drei Ausprägungen:

| Muster | Templates |
| :-- | :-- |
| `Run(text='Impressum: xxxxxx', font='Gotham Narrow Book', fontsize=6, fcolor=White/Dunkelgrün, …)` | alle `flyer-a6-*`, alle `falzflyer-z-falz-6-seitig-*` (je 1–2×) |
| `Run(text='Impressum:', …)` + Folgerun | `plakat-a1-hochformat`, `postkarte-a6-kampagne` |
| `Run(text='Impressum', separator='para', …)` | `zeitung-a4` |

In der gerenderten `template.sla` (Scribus-XML) landet jeder `Run` als
`<ITEXT CH="…"/>` innerhalb eines `<PAGEOBJECT PTYPE="4">` (Textframe).
Absätze trennt Scribus mit `<para …/>`-Elementen im selben Story-Block.
→ Frame-Erkennung: ein `PAGEOBJECT`, dessen zusammengesetzter `ITEXT/@CH`-Text
das Wort „Impressum" enthält, ist der Impressum-Frame.

## 3. Substitutions-Strategie (v1)

`tools/impressum.py`:
1. SLA per `xml.etree.ElementTree` parsen.
2. Über alle `PAGEOBJECT` iterieren; je Frame `ITEXT/@CH` konkatenieren.
   Enthält die Konkatenation `impressum` (case-insensitive) → Treffer.
3. Im Treffer-Frame: Zeichen­attribute des **ersten** `ITEXT` merken
   (FONT, FONTSIZE, FCOLOR, …). Alle bestehenden `ITEXT`/`para`-Textknoten des
   Frames entfernen und durch neue `ITEXT`-Runs ersetzen — eine Zeile je
   Impressum-Zeile, getrennt durch `<para>`-Elemente, mit den gemerkten
   Attributen. `druck` (falls gesetzt) als zusätzlicher Absatz.
4. SLA nach `out_path` schreiben.

Generisch über alle drei Slot-Muster, da auf Frame- statt Run-Ebene gearbeitet
wird. Bekannte v1-Grenze: sehr langer Impressumstext kann den 6-pt-Frame
überlaufen → in CONTEXT.md (D5) als iteratives Increment vermerkt.

## 4. Impressum-Daten je Landesorganisation

Quelle: jeweilige `<land>.gruene.at/impressum`-Seite, abgerufen 2026-05-20.
Formuliert als Mediengesetz-Kurzzeile **Medieninhaberin & Herausgeberin**.
`druck` bleibt leer (separat befüllbar). **MAINTAINER muss die Texte vor
Veröffentlichung juristisch verifizieren** — Adress-/Namensdetails können
sich ändern; einige Seiten nannten weder ZVR-Nr. noch verantwortliche Person.

| slug | Bundesland | Impressum-Zeile | Quelle |
| :-- | :-- | :-- | :-- |
| `bgld` | Burgenland | Die Grünen – Die Grüne Alternative Burgenland, Hauptstraße 38/Top 5, 7000 Eisenstadt | burgenland.gruene.at/impressum |
| `ktn`  | Kärnten | Die Grünen Kärnten – Landesorganisation, Bahnhofstraße 38a, 9020 Klagenfurt | kaernten.gruene.at/impressum |
| `noe`  | Niederösterreich | Die Grünen Niederösterreich, Daniel-Gran-Straße 48, 3100 St. Pölten | noe.gruene.at/impressum |
| `ooe`  | Oberösterreich | Die Grünen – Die Grüne Alternative Oberösterreich, Landgutstraße 17, 4040 Linz | ooe.gruene.at/impressum |
| `sbg`  | Salzburg | Die Grünen Salzburg, Glockengasse 6, 5020 Salzburg | salzburg.gruene.at/impressum |
| `stmk` | Steiermark | Die Grünen Steiermark, Kaiserfeldgasse 5–7, 8010 Graz | stmk.gruene.at/impressum |
| `tirol`| Tirol | Die Grünen – Die Grüne Alternative Tirol, Müllerstraße 7, 6020 Innsbruck | tirol.gruene.at/impressum |
| `vbg`  | Vorarlberg | Die GRÜNEN – Grüne Alternative Vorarlberg, St.-Anna-Straße 1/Top 7, 6900 Bregenz | vorarlberg.gruene.at/impressum |
| `wien` | Wien | Die Grünen – Grüne Alternative Wien, Würtzlerstraße 3/3, 1030 Wien | wien.gruene.at/impressum |

Default-/Fallback-slug: `noe`.

## 5. Betroffene Dateien

- **Neu:** `shared/impressum/bundeslaender.yml`, `tools/impressum.py`,
  `tools/sla_lib/tests/test_impressum.py` (oder bestehender Testort).
- **Geändert:** `tools/render_pipeline.py` (per-Bundesland-SLA-Schritt),
  `tools/gallery_build.py` (`_downloads` je Bundesland),
  `site/src/pages/templates/[...id].astro` (gruppierte Download-Liste),
  `site/src/content.config.ts` (Schema für neue `_downloads`-Form, falls nötig).
- **Erzeugte Artefakte:** `templates/<id>/impressum/<slug>.sla` (16×9).
