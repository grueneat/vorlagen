# Scribus Template Pipeline — Architektur und Roadmap

**Stand:** 2026-05-04
**Repo:** `/root/workspace` (vorerst lokal, später GitHub)
**Quellen:** parallele Recherche unter `01-sla-format.md`, `02-tooling-ecosystem.md`, `03-validation-distribution.md` plus eigene Strukturanalyse + lauffähiger PoC.

---

## TL;DR

1. **Stack-Empfehlung:** Scribus 1.6.x (in Docker, headless via Xvfb) als verbindlicher Renderer; **direkter SLA-XML-Edit** mit `lxml` für deterministische Bearbeitung; Scripter nur dort, wo der GUI-State wirklich nötig ist (Reflow, Style-Anwendung). LaTeX/Typst als Sekundärgleis nur prüfen, falls die Zeitung später wirklich textlastig wird — momentan hat Scribus die einzige vollständige PDF/X-4 + CMYK-Pipeline für alle drei Formate.
2. **AI-Pattern:** Mensch baut Templates im GUI, KI füllt strukturierte JSON-Slots in **benannte Frames**. Vision-LLM-as-Judge im Pairwise-Modus gegen ein "Goldenes Master-PDF" (idealerweise InDesign-Export der finalen Vorlage). Keine LLM-generierten SLA-XMLs from-scratch.
3. **Zwei Ebenen Quality Gate:** (a) **Preflight** mit veraPDF + pdfcpu + Custom-Python-Regeln (CMYK-only, Bleed 3mm, Bilder ≥300dpi, Schriften eingebettet); (b) **Visual Regression** als Hybrid — `odiff` (Pixel + AA) für Layout, `dssim` (SSIM) für Fließtext, mit `regions.yml` pro Template.
4. **Distribution:** Astro auf GitHub Pages für die öffentliche Galerie; Cloudflare Pages + Cloudflare Access falls intern. Pro Template: Detail-Seite mit PDF-Preview, PNG-Carousel, Download (PDF + SLA + Assets-Zip), Changelog, Metadaten aus YAML-Sidecar.
5. **Vier Phasen:** A) Repo-Foundation + Renderer-in-Docker + die 3 bestehenden Templates aufräumen → B) Variant-Engine + Preflight + Visual-Diff → C) AI-Slot-Fill + Vision-Judge → D) Galerie-Site + öffentlicher Download.

---

## 1. Was im Repo existiert (Strukturanalyse)

| Template | Format | Seiten | Objekte | Stile | Master | Besonderheit |
|---|---|---|---|---|---|---|
| **Plakat A1 Hochformat** | 594×841mm (A1) | 1 | 9 (6 Text, 3 Bild) | 5 | 1 ("Normal") | Event-Plakat: Datum/Zeit/Ort/Headline-Slot |
| **Postkarte** | 105×148mm (A6) | 2 (Vor/Rück) | 18 (7 Text, 8 Bild, 3 Polygon) | 9 | 1 ("Normal") | Kampagne: Headline + Störer (Badge) + Petition + QR + Impressum |
| **Grüne Zeitung** | 210×297mm (A4) | 14 | 146 (114 Text, 24 Bild, 8 Polygon) | 23 | 2 (links/rechts) | Mehrseitige Zeitung mit Multi-Spalten-Layout, weichen Trennzeichen, Stile mit Vererbung |

**Gemeinsamkeiten:**
- Alle Scribus 1.6.5
- Bleed 3mm (8.504pt) auf allen Seiten
- Brand-Farben: `Dunkelgrün`, `Gelb`, `Hellgrün`, `Magenta`, `Black`, `White` plus `Registration`. Mostly CMYK; **`Green` ist in 2 Templates als RGB hinterlegt — Inkonsistenz, beim Print-Export problematisch** → reparieren.
- Schriften: Gotham Narrow (Book/Bold/Black/Ultra) + Vollkorn Black Italic — **müssen ins Repo gebündelt** (Lizenz prüfen!)
- Image-Frames sind alle leer (`PFILE=""`) → bewusste Platzhalter
- Dieselbe Designsprache, aber **Stile sind nicht vereinheitlicht**: jedes Template definiert "Fließtext" / "Impressum" / "Headline" neu, mit teils abweichenden Werten → Refactor zu einem geteilten **CI-Stylesheet** (siehe Phase A.3).

**Identifizierte Variablen pro Template** (das, was sich beim Re-Use ändert):
- *Plakat:* Datum, Zeit, Veranstaltungsort, Adresse, Headline (4-zeilig), Hauptbild, Sub-Bild, Logo, Anmelde-URL.
- *Postkarte:* Hauptbotschaft (4-zeilig), Störer-Text (3-zeilig), Sub-Headline, Mengentext (variabel viel), Kampagnen-URL/QR, Social-Handles, Impressum.
- *Zeitung:* Titel der Ausgabe ("Zeitungsname"), Monat/Ausgabe, Ortsbezug, alle Artikel (Headline + Text + Bild + ggf. Zitat + Stör-Element), Inhalts-Kästen auf Titelseite, Impressum, Postvermerk.

**PoC-Ergebnis (heute live ausgeführt):** Direkter Edit der SLA via Python-Stdlib + Headless-Render via `xvfb-run scribus -g -ns -py` produziert korrekte PDFs für alle drei Templates. 3 Postkarten-Varianten (Klimaschutz/Wohnen/Bildung) wurden in <30s pro Variante generiert. **Pipeline-Foundation ist verifiziert.**

---

## 2. Zielarchitektur

### 2.1 Repo-Layout

```
.
├── README.md
├── CLAUDE.md                       # Projekt-Memory
├── .github/
│   └── workflows/
│       ├── render.yml              # PR-Render + Preview-Comment
│       ├── preflight.yml           # PDF/X + Custom-Regeln
│       ├── visual-diff.yml         # odiff + dssim Hybrid
│       └── pages.yml               # Astro-Build → Pages-Deploy
├── docker/
│   └── renderer/                   # Scribus 1.6.x + Xvfb + Fonts + ICC, gepinnt
│       └── Dockerfile
├── templates/
│   ├── plakat-a1-event/
│   │   ├── template.sla            # Master-SLA (im GUI editierbar)
│   │   ├── meta.yml                # ID, Version, Tags, Variablen-Schema
│   │   ├── golden/
│   │   │   ├── reference.pdf       # InDesign- oder Approval-Export
│   │   │   └── pages/              # PNG-Raster bei pinned DPI (LFS)
│   │   ├── regions.yml             # Per-Region-Toleranzen für Visual-Diff
│   │   ├── samples/                # Beispiel-Daten (JSON), produzieren Demo-Renders
│   │   │   ├── baden-feb20.json
│   │   │   └── …
│   │   └── README.md
│   ├── postkarte-a6-kampagne/
│   └── zeitung-a4/
├── shared/
│   ├── ci.yml                      # Geteiltes Stylesheet (Farben, Fonts, Stilnamen)
│   ├── fonts/                      # Gotham Narrow*, Vollkorn (LFS)
│   ├── icc/                        # ISOcoatedv2_eci.icc, sRGB IEC61966-2.1
│   └── logos/                      # Grünen-Logos in versch. Farben
├── tools/
│   ├── sla_lib/                    # Python: SLA-XML-Reader/Editor (lxml)
│   │   ├── reader.py
│   │   ├── slot.py                 # Frame-Naming, Slot-Resolution
│   │   ├── editor.py
│   │   └── tests/
│   ├── render.py                   # Headless-Render-CLI (Scribus + Xvfb)
│   ├── preflight.py                # veraPDF + pdfcpu + Custom-Regeln
│   ├── diff.py                     # odiff/dssim Hybrid-Diff
│   ├── ai_fill.py                  # Slot-Fill mit Anthropic SDK + Vision-Judge
│   └── gallery_build.py            # Erzeugt Astro-Content aus templates/
├── site/                           # Astro-Galerie
│   ├── src/content/                # Auto-generated von gallery_build.py
│   └── …
├── tests/
│   ├── unit/                       # SLA-Reader/Editor
│   ├── integration/                # Volle Render-Pipeline pro Template
│   └── visual/                     # Goldene PNGs, Toleranzen
└── .research/                      # Diese Recherche
```

### 2.2 Datenfluss (eine Variante rendern)

```
templates/<id>/template.sla  ──┐
samples/<variant>.json        ──┼─►  sla_lib.editor.fill_slots(...)  ──►  build/<id>__<variant>.sla
shared/ci.yml                 ──┘                                                │
                                                                                  ▼
                                                                       render.py (Scribus + Xvfb)
                                                                                  │
                                                                                  ▼
                                                            build/<id>__<variant>.pdf
                                                                                  │
                                                              ┌───────────────────┼───────────────────┐
                                                              ▼                   ▼                   ▼
                                                    preflight.py      pdftocairo @300dpi      pdfjs-Embed
                                                  (PDF/X-4, CMYK,     pages/*.png             site/static/
                                                   Bleed, Fonts)            │
                                                                            ▼
                                                                  diff.py vs golden/pages/
                                                                            │
                                                                            ▼
                                                                  reports/<id>__<variant>/
                                                                  ├── status.json
                                                                  ├── preflight.txt
                                                                  └── diff/{exp,act,delta}.png
```

### 2.3 SLA-Slot-Konzept (zentrale Entwurfsentscheidung)

Aus der Strukturanalyse: Scribus 1.6 erlaubt es, jedem `PAGEOBJECT` eine **eindeutige `ANNAME`** (Object-Name) zu geben, sichtbar in den Object-Properties. Das ist der saubere Hook für programmatischen Zugriff — **deutlich robuster als String-Matching auf ITEXT-CH**, wie wir es im PoC heute getan haben.

Konvention: Frames, die als Slots dienen, bekommen Namen wie:
```
text:headline           # 4-zeilige Hauptüberschrift
text:date               # Datumsfeld
text:venue              # Ort
image:hero              # Hauptbild
image:logo              # Logo (meist statisch in shared/logos)
text:impressum          # statischer Block, mit Variablen wie {{landesgruppe}}
```

Schema in `meta.yml`:
```yaml
id: plakat-a1-event
version: 1.0.0
format: A1
audience: [bezirksgruppe, landesgruppe]
slots:
  headline: { type: text, lines: 4, max_chars_per_line: 18 }
  date:     { type: text, format: "Wochentag, DD. Monat" }
  time:     { type: text, format: "HH:MM - HH:MM" }
  venue:    { type: text, max_chars: 40 }
  address:  { type: text, max_chars: 50 }
  hero:     { type: image, ratio: "16:9", min_dpi: 300 }
  logo:     { type: image, source: shared/logos/gruene-weiss.png, locked: true }
  url:      { type: text, default: "gruene.at/tour" }
golden:
  reference: golden/reference.pdf
  pages_dpi: 300
preflight:
  profile: pdfx-4
  bleed_mm: 3
  cmyk_only: true
```

**Migration** der drei bestehenden Templates: einmalig durch das Repo gehen, jeden Slot-Frame benennen, die Stilnamen vereinheitlichen, `meta.yml` schreiben. Dann sind die Templates "Repository-ready".

---

## 3. Phasen-Roadmap

### Phase A — Foundation (Woche 1-2)
**Ziel:** Repo + Docker + die 3 Templates so, dass jeder Push in CI rendert.

A.1 `git init`, `.gitattributes` für LFS (Fonts, ICC, golden-PDFs, Beispielbilder), `.gitignore` für `.tmp/` und `build/`.
A.2 **Docker-Image** `renderer/`: Debian 12 oder Ubuntu 24.04, Scribus 1.6.x aus pinned APT (oder offizielle PPA), Xvfb, Poppler, Ghostscript, veraPDF, pdfcpu, qpdf, pdftocairo, plus die Brand-Fonts und ICC-Profile direkt im Image. Image-Tag = SHA der Dockerfile. Push zu `ghcr.io/<org>/scribus-renderer`.
A.3 **`shared/ci.yml`** definieren: alle Brand-Farben in CMYK, Schriftnamen, kanonische Stilnamen ("ci/headline", "ci/body", "ci/impressum"). Skript `tools/apply_ci.py`, das Stile in einer SLA gegen `ci.yml` validiert oder repariert (alte Inkonsistenzen wie RGB-`Green` werden geflaggt).
A.4 **Refactor der 3 Templates**: Stilnamen aufräumen, Frames benennen (`ANNAME`), `meta.yml` schreiben. **Erstes echtes Akzeptanzkriterium:** `tools/render.py templates/postkarte-a6-kampagne` erzeugt das Original-Layout pixel-identisch.
A.5 **`tools/sla_lib/`** als Python-Package — Reader, Editor, Slot-Resolution. Unit-Tests gegen die 3 Templates (lxml-basiert, kein Scribus nötig).
A.6 **`render.py`-CLI** als dünner Wrapper um `xvfb-run scribus -g -ns -py …` plus interner Scripter-Skript für `PDFfile()` mit PDF/X-4 Settings. Caching nach `(sla_hash, ci_hash, renderer_image_hash)`.

**Liefert:** drei Templates rendern reproducible in Docker und CI; Stile-Repo ist die Quelle der Wahrheit.

### Phase B — Varianten + Quality Gates (Woche 3-4)
**Ziel:** Aus einem Template entstehen N Varianten, jede mit Preflight + Visual-Diff.

B.1 **Variant-Engine** (`tools/render.py --variant samples/x.json`): liest `meta.yml`, validiert JSON gegen Slots-Schema, ruft `sla_lib.editor.fill_slots`, rendert.
B.2 **`preflight.py`**: veraPDF mit eigenem Custom-Profil ("Grüne Print 2026") für PDF/X-4 + CMYK + Bleed; pdfcpu für strukturelle Integrität; eigene Python-Regeln über `pdfimages -list` (Bilder ≥300dpi) und `pdfinfo` (Page-Count, Box-Größen).
B.3 **`diff.py`**: `pdftocairo -r 300 -png` der Output- und Golden-PDFs, dann
   - `regions.yml` lesen
   - pro Region entweder `odiff --aa` (Layout) oder `dssim` (Text) ausführen
   - aggregierter `status.json` mit Pass/Fail pro Region
   - Side-by-Side-Composite (`expected | actual | delta`) als PNG.
B.4 **GitHub Actions:** `render.yml` matrix-buildet alle Templates × alle Samples, ruft Preflight + Diff, lädt Artefakte hoch und kommentiert PRs mit einer "sticky" Tabelle (Status × Templates) und eingebettetem Composite-PNG.
B.5 **Approve-Baseline-Workflow:** PR mit Label `approve-baseline` triggert Bot, der `build/.../*.png` nach `templates/<id>/golden/pages/` kopiert und als neuen Commit pusht. Menschlicher Approval bleibt verpflichtend.

**Liefert:** Jede Änderung wird automatisch geprüft, Regressionen sind sichtbar bevor gemerged wird.

### Phase C — KI-Augmentierung (Woche 5-7)
**Ziel:** Inhalte (Texte, Bilder) automatisiert erzeugen oder anreichern; Vision-Judge als Gegenprüfung.

C.1 **`ai_fill.py`** mit Anthropic SDK (Claude 4.x, Prompt-Caching für Template-Anweisungen). Eingabe: Briefing-Text ("Plakat für Klima-Veranstaltung in Wels am 15.6., Headline soll wütend aber konstruktiv sein"). Ausgabe: validiertes JSON für die Slots des Templates. Strikt: LLM darf nur die im Schema deklarierten Slots füllen, nicht Layout ändern.
C.2 **Vision-Judge** (`ai_fill.py --judge`): nimmt Render und das Golden-Reference-PDF, ruft Claude im Pairwise-Modus ("Welches der beiden sieht eher wie eine professionelle Grünen-Kampagne aus, A oder B?"). Pairwise statt absolut, weil VLLM-Judges Pairwise zuverlässiger sind.
C.3 **AI-Bildgenerierung** (optional, Phase C.3 ist klar trennbar): FLUX oder SDXL für Hero-Images, danach **manuelle Review-Stufe** + ImageMagick-Postprocessing nach CMYK. Niemals ungeprüft in Print.
C.4 **Briefing-Datei `briefing.md`** im Repo als alternativer Eingabekanal: Mensch schreibt freie Beschreibung, Bot öffnet PR mit gefülltem Sample-JSON; CI rendert, Vision-Judge kommentiert.
C.5 **Cost-Guardrails:** Tokens pro Lauf logged; Budget-Alarme. Caching der Slots-Schema-Prompts.

**Liefert:** Aus einem 5-Zeilen-Briefing wird automatisch ein PR mit Render und Quality-Report. Mensch entscheidet Approve/Iterate.

### Phase D — Distribution (Woche 8-10)
**Ziel:** Andere Gruppierungen finden, durchsuchen, downloaden Templates.

D.1 **Astro-Site** in `site/` mit Content-Collections aus `templates/*/meta.yml`. Pagefind-Suche (zero-JS). Per-Template-Detail-Seite: PDF eingebettet via `pdfjs-viewer-element`, PNG-Carousel der Seiten, Download-Buttons (PDF, SLA-Source-Zip mit Assets, ggf. IDML-Reference falls vorhanden), Changelog (aus git log gezogen), Tags (Format/Anlass/Sprache/Region).
D.2 **Per-Template OG-Image** automatisch generiert (Cover + Titel + Logo) für Social-Sharing.
D.3 **GitHub Pages Deploy** via `pages.yml`. Falls intern gewünscht: alternativer Deploy auf Cloudflare Pages mit Cloudflare Access (SSO).
D.4 **Release-Cadence:** Per-Template Semver in `meta.yml`. Bot bumpt PATCH bei Render-Output-Änderung, MINOR bei neuen Slots, MAJOR bei Breaking-Schema. Releases als GitHub Releases mit den Assets-Zips.
D.5 **Onboarding-Doku** für Bezirks-/Landesgruppen: "So lädst du dir das Postkarten-Template" + "So füllst du es aus" (mit Hinweis auf Online-Konfigurator als zukünftige D.6).

D.6 (Stretch) **Online-Konfigurator** auf der Galerie-Seite: Webformular pro Slot, schickt JSON an einen kleinen GitHub-Action-trigger oder Cloudflare Worker, dieser ruft die Render-Pipeline und liefert PDF zurück. Der eigentliche Renderer läuft weiter in CI/serverless, nicht im Browser.

**Liefert:** Selbstbedienbarer Vorlagen-Katalog für Multiplikator:innen.

---

## 4. Wichtige Entscheidungen, die jetzt getroffen werden müssen

| Frage | Empfehlung | Konsequenz |
|---|---|---|
| **Renderer-Pinning** | Scribus 1.6.x in Docker, nie auf Contributor-Maschine rendern | Stabile golden PNGs, keine Font-Hinting-Drift |
| **Goldenes Master-Format** | Reference-PDF + 300dpi-PNG-Raster im Repo (LFS) | Diff entkoppelt von Cairo/Poppler-Versions-Drift |
| **Diff-Strategie** | Hybrid: odiff (Layout) + dssim (Text) mit `regions.yml` | Realistische Toleranz, klare Rege-für-Rege Konfiguration |
| **AI-Pattern** | Slot-Fill in benannte Frames + Pairwise Vision-Judge | KI-Layout-Generation reift, aber heute zu unzuverlässig |
| **Galerie-Stack** | Astro auf GitHub Pages (oder Cloudflare Pages + Access) | Schnelles, statisches Deploy; Auth nur falls nötig |
| **Stile-Vereinheitlichung** | `shared/ci.yml` mit Validator | Eine Quelle der Wahrheit für Brand |
| **Schriften-Lizenz** | Vor Phase A.2 prüfen — Gotham ist proprietär (Hoefler & Co.) | Falls Lizenz Repo-Bündelung nicht erlaubt: privates Submodule oder lokale Installation, dokumentieren |
| **Spot-Color "Grünen-Grün"** | Beibehalten als Spot, nicht auf RGB konvertieren | Druckqualität in Offset; AI-Bild-RGB→CMYK kann Brand-Grün niemals exakt treffen |

---

## 5. Risiken & Gegenmaßnahmen

- **Schriftlizenz:** Gotham Narrow ist proprietär. Vor Repo-Push klären — sonst Submodule + private Distribution.
- **Scribus parallel:** Im PoC heute kollidierten parallele `xvfb-run scribus` Aufrufe (ein Render fehlgeschlagen). Lösung: Pro CI-Job ein Container, Scribus immer mit dediziertem `--display`. Nicht im selben Prozess parallelisieren.
- **PyScribus dormant** (letzte Release Aug 2023). Wir nutzen es höchstens als Inspiration; eigener `sla_lib`-Layer mit lxml ist robuster und unter unserer Kontrolle.
- **ScribusGenerator multi-page mode** "works but error-prone" — nicht für die Zeitung verwenden.
- **PDF-Render-Drift:** Bei Renderer-Image-Updates _müssen_ goldene PNGs neu erzeugt werden. Workflow muss das atomar im selben Bot-PR tun.
- **Vision-Judge Halluzinationen:** Niemals als alleiniges Gate. Immer Mensch-Approval bei MAJOR/MINOR.

---

## 6. Sofort-Nächste-Schritte (Aktionsliste)

1. Schrift-Lizenz-Check Gotham Narrow + Vollkorn (Lizenztext beilegen)
2. `git init` + Initial-Commit der drei vorhandenen SLAs + `.research/`
3. **Dockerfile** `docker/renderer/Dockerfile` schreiben (Scribus 1.6.x, Xvfb, Fonts, ICC)
4. `tools/sla_lib/reader.py` als erste Iteration (basiert auf der heute verifizierten Strukturanalyse)
5. Eine der drei Templates (Postkarte, am kleinsten) **als Referenz-Implementierung** komplett durchziehen: Frames benennen, `meta.yml`, `samples/`, `golden/`, in CI rendern. Erst danach die anderen zwei migrieren.
6. **InDesign-Reference-PDFs anfordern** (falls vorhanden) — sonst markieren wir den ersten Scribus-Render als "approved baseline" und nehmen den als Golden.

---

## 7. Schlüssel-Erkenntnisse aus dem SLA-Format-Report (siehe 01-sla-format.md)

Diese Punkte sind harte Constraints fürs `sla_lib` Design — sie sind **nicht offensichtlich aus dem XML** und kommen aus dem Scribus-Source:

- **Keine offizielle XSD/RNG.** Spec ist `scribus150format_save.cpp` (~3000 LOC Writer) im Scribus-Repo. 1.5.x und 1.6.x teilen sich denselben Loader; 1.4 und 1.7 haben jeweils eigene. Wir schreiben `Version="1.6.x"`.
- **PAGEOBJECTs sind Geschwister von PAGE**, nicht Kinder. Zuordnung via `OwnPage` (Zahl) bzw `OnMasterPage` (String).
- **`ItemID` ist instabil** über Reloads (qHash-basiert). Verlinkungen (`NEXTITEM`, `BACKITEM`, Welds) müssen mit ID neu gemappt werden, falls man umbaut. **`ANNAME` ist die einzig stabile menschen- und maschinen-lesbare Handle** — bestätigt unsere Slot-Konvention.
- **Koordinaten:** Immer in Punkten (1pt=1/72 Zoll), unabhängig vom `UNITS`-Attribut. `XPOS`/`YPOS` sind Scratch-Space (über alle Seiten verteilt) — Page-relative = subtract `PAGEXPOS`/`PAGEYPOS`. Bleed liegt auf DOCUMENT-Ebene.
- **Style-Vererbung via `PARENT` ist implizit-by-Abwesenheit.** Wenn ein Child-Style ein Attribut hat, das identisch zum Parent ist, **darf man es nicht emittieren** — sonst überschreibt es die Vererbung leise. Das ist die größte Stolperfalle beim programmatischen Edit; `sla_lib.editor` muss das beachten.
- **Inline-Bilder** sind Base64-von-`qCompress` (Qt-zlib-Wrapper, **nicht** Raw-deflate). Externe Bilder via `PFILE` als relative-zu-SLA oder absolut.
- **Keine Prüfsumme, keine Signatur.** Reines XML — diff-fähig in git, aber auch leicht still kaputt-zu-machen. Round-Trip-Test via Headless-Scribus ist Pflicht.
- **PTYPE-Enum** (`pageitem.h::ItemType`): 2 Image, 4 Text, 5 Line, 6 Polygon, 7 PolyLine, 8 PathText, 9 LaTeX, 10 OSG, 11 Symbol, 12 Group, 13 RegularPolygon, 14 Arc, 15 Spiral, 16 Table, 17 NoteFrame.

## 8. Anhänge

- `01-sla-format.md` — Tiefe SLA-XML-Schema-Doku (~2740 Wörter)
- `02-tooling-ecosystem.md` — Vergleich Scribus vs Typst vs LaTeX vs WeasyPrint, AI-Patterns
- `03-validation-distribution.md` — Visual-Diff, Preflight, Galerie-Architektur
- PoC-Renders: `/root/workspace/.tmp/previews/` (3 Originale + 3 Postkarten-Varianten + 1 Plakat-Variante)
