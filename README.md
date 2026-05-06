# Grüne Vorlagen — Scribus Template Authoring System

Versionierte, brand-konsistente Skelett-Vorlagen für Postkarten, Plakate und Zeitungen der Grünen NÖ. Andere Gruppierungen laden sie aus der **GitHub Pages Galerie**, öffnen sie in **Scribus**, passen Inhalte an und drucken.

## Was steckt drin

```
templates/
├── postkarte-a6-kampagne/    # 2-seitige A6-Postkarte
│   ├── build.py              # DSL-Definition (source of truth)
│   ├── template.sla          # build artifact, in Scribus zu öffnen
│   ├── meta.yml              # Metadaten + Slot-Hinweise
│   └── README.md
├── plakat-a1-hochformat/     # A1 Veranstaltungs-Plakat (faithful DSL reproduction)
│   ├── build.py              # DSL-Definition (source of truth)
│   ├── template.sla          # build artifact, in Scribus zu öffnen
│   ├── meta.yml
│   └── README.md
└── zeitung-a4-grun/          # 9 Beispielseiten in einer Multi-Page-SLA
    ├── build.py
    ├── template.sla          # 9 Pages × 6 Master-Pages
    ├── meta.yml
    └── README.md
```

## Drei Zugänge

### 1. Inhaltliche Anpassung (für Endnutzer:innen)

In Scribus öffnen, im Page-Panel die gewünschte Beispielseite duplizieren, Inhalte ersetzen, ungenutztes löschen, PDF exportieren. Pinke Beschriftungen am Seitenrand erklären, welche Variante was zeigt — werden im PDF-Export nicht gedruckt (Hilfslinien-Layer).

Die einzelnen Templates haben jeweils eine `README.md` mit Schritt-für-Schritt-Anleitung.

### 2. Strukturelle Vorlagenanpassung (für Maintainer:innen)

Neue Beispielseite oder Layout-Variante hinzufügen → editiere `build.py` der jeweiligen Vorlage:

```python
from sla_lib.builder import Document, Color, Style, blocks, Polygon

doc = Document(title="...", template_id="...")
doc.add_master(name="rechts-3col", size="A4")
page = doc.add_page(size="A4", master="rechts-3col",
                    label="Beispiel: neue Layout-Variante")
page.add(blocks.Headline4Line(...))
page.add(blocks.ArticleBody(columns=3, ...))
doc.save("template.sla")
```

`build.py` ausführen → SLA wird neu emittiert. Das Layout ist im Code versioniert; Brand-Stile kommen aus `shared/ci.yml`.

### 3. Ganz neue Vorlage erstellen

Lege ein neues `templates/<id>/build.py` an mit `Document(...)` + `add_page` + Blocks aus der Library. Schreibe `meta.yml` mit Slot-Beschreibungen und einen `README.md` für die Galerie. CI rendert beim nächsten Push automatisch Vorschau-PDFs und deployed die Galerie.

## Architektur

| Schicht | Verantwortung | Pfad |
|---|---|---|
| **Brand** | Single source of truth für Farben/Fonts/Stile | `shared/ci.yml` |
| **Validator** | Drift-Detection gegen die SLA | `tools/check_ci.py` |
| **DSL** | Typed Python API → valides Scribus 1.6 SLA-XML | `tools/sla_lib/builder/` |
| **Blocks** | Wiederverwendbare Compose-Bausteine | `tools/sla_lib/builder/blocks.py` |
| **Renderer** | Headless Scribus → PDF (Xvfb) | `tools/render.py` |
| **Galerie-Build** | Templates → Astro-Content + PNG-Previews | `tools/gallery_build.py` |
| **Galerie-Site** | Astro statisch, deployed auf GitHub Pages | `site/` |
| **CI** | Build + Validate + Deploy | `.github/workflows/pages.yml` |

## Round-trip Validation

Die drei Galerie-Vorlagen werden gegen ihre Originale (an Workspace-Root: `postkarte-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `gruene-zeitung-vorlage-original.sla`) validiert — strukturell und visuell.

### Strukturell — `tools/sla_diff.py`

Vergleicht zwei SLAs nach einer 10-Schritte-Normalisierungs-Pipeline (volatile-Attrs strippen, ItemID renumbern, page-local Koordinaten, Float-Rundung, Attribut-Sortierung). Liefert dreistufige Severity (`critical` / `warning` / `info`), Markdown- oder JSON-Reporter.

```bash
python3 tools/sla_diff.py \
  --left postkarte-vorlage-original.sla \
  --right templates/postkarte-a6-kampagne/template.sla \
  --strict
# Exit 0 → reproduktion strukturell faithful
# Exit 1 → critical oder warning vorhanden (mit --strict)
```

### Visuell — `tools/visual_diff.py`

Rendert beide SLAs zu PDF (Scribus + Xvfb), rasterisiert per Page (pdftoppm), per-pixel diff via ImageMagick `compare`, plus Composite (baseline | dsl | delta) zur visuellen Inspektion.

```bash
python3 tools/visual_diff.py \
  templates/postkarte-a6-kampagne/template.sla \
  --baseline templates/postkarte-a6-kampagne/baseline.pdf \
  --tolerance templates/postkarte-a6-kampagne/diff.yml \
  --dpi 96 \
  --out build/postkarte/
```

DPI: `--dpi 150` lokal, `--dpi 96` in CI (CONTEXT.md D4). Toleranzen pro Template in `templates/<id>/diff.yml` — Schema in [docs/diff-tolerance.md](docs/diff-tolerance.md).

### Komplette Validierung

```bash
bin/validate
```

oder

```bash
make validate    # falls Makefile vorhanden
```

Beides ruft `sla_diff` + `visual_diff` für alle drei Templates auf und gibt Exit 0 wenn alles innerhalb der Toleranzen.

### Konverter `tools/sla_to_dsl.py` — One-Shot Bootstrap

Erzeugt initial `templates/<id>/build.py` aus einer existierenden SLA. **Nicht** Teil der CI-Pipeline. Wird einmal manuell laufen gelassen, danach ist `build.py` die Source of Truth und wird von Hand editiert.

```bash
python3 tools/sla_to_dsl.py \
  postkarte-vorlage-original.sla \
  templates/postkarte-a6-kampagne/build.py \
  --template-id postkarte-a6-kampagne \
  --assets-dir templates/postkarte-a6-kampagne/assets/
```

### Rebaselining (wenn sich das Original oder Scribus-Toolchain ändert)

```bash
rm templates/<id>/baseline.pdf
xvfb-run -a scribus -g -ns -py tools/_export_pdf.py \
    <updated-original>.sla \
    templates/<id>/baseline.pdf
git add templates/<id>/baseline.pdf
git commit -m "rebaseline <id>: <reason>"
```

Details in [docs/diff-tolerance.md](docs/diff-tolerance.md) §"Rebaselining workflow".

## Wo Forschung und Entscheidungen dokumentiert sind

`.research/` enthält die initiale Tiefenrecherche:

- `00-synthesis.md` — Architektur und Roadmap
- `01-sla-format.md` — SLA-XML-Schema-Doku (mit allen Stolperfallen)
- `02-tooling-ecosystem.md` — Stack-Vergleich Scribus / Typst / LaTeX / WeasyPrint
- `03-validation-distribution.md` — Preflight, Visual-Diff, GitHub Pages
- `04-scribus-multipage-masters.md` — Master-Pages-Mechanik

Plus die Issue-Dokumentation in `.issues/1-scribus-template-authoring-pipeline/`:

- `ISSUE.md` — Scope, Akzeptanzkriterien
- `CONTEXT.md` — was im Discuss geklärt wurde
- `RESEARCH.md` — DSL-Design-Patterns
- `PLAN.md` — die 29 Tasks
- `EXECUTION.md` — was abgehakt wurde

## Lokal entwickeln

Voraussetzungen: Scribus 1.6.x (Debian trixie oder neuer), Python 3.11+, lxml, PyYAML, Node 20+ für die Galerie.

```bash
# Eine Vorlage rendern
python3 templates/postkarte-a6-kampagne/build.py
xvfb-run -a scribus -g -ns -py tools/_export_pdf.py \
  templates/postkarte-a6-kampagne/template.sla /tmp/preview.pdf

# Oder über die Sammel-Pipeline
python3 tools/gallery_build.py    # rendert alle + erzeugt site/src/content/

# Galerie-Site bauen
cd site && npm install && npm run build
# Output: site/dist/
```

Tests:
```bash
python3 -m unittest discover tools/sla_lib/tests
```

## Lizenz / Credits

- Templates und Brand: © Die Grünen Niederösterreich
- Brand-Schriften (Gotham Narrow, Vollkorn Black Italic): proprietäre Lizenzen — **nicht** im Repo gebündelt. Müssen lokal installiert sein, sonst substituiert der Renderer mit DejaVu (sichtbar in PDF-Vorschau).
- Pipeline-Code: TBD-Lizenz
