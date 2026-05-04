# Grüne Vorlagen — Scribus Template Pipeline

Versionierte Scribus-Vorlagen für Plakate, Postkarten und Zeitungen, mit Pipeline für Variantenerzeugung, Quality-Gates und Distribution.

## Stack

- **Renderer:** Scribus 1.6.x in Docker (Headless via Xvfb)
- **Edit:** Direkter SLA-XML-Edit mit `lxml`, Slot-Konvention via `ANNAME`
- **Variants:** `templates/<id>/samples/<variant>.json` → gefüllte SLA → PDF
- **QA:** `veraPDF` + `pdfcpu` Preflight, `odiff`/`dssim` Visual-Diff vs. golden master
- **Distribution:** Astro auf GitHub Pages (oder Cloudflare Pages + Access)

## Layout

```
templates/<id>/
├── template.sla       # Master, im GUI editierbar
├── meta.yml           # Slot-Schema, Tags, Versions-Info
├── samples/*.json     # Beispieldaten → werden in CI gerendert
├── golden/            # Referenz-PDF + 300dpi-Page-PNGs
└── regions.yml        # Per-Region-Toleranzen für Visual-Diff

shared/
├── ci.yml             # Brand-Stile (Farben, Fonts, kanonische Stilnamen)
├── fonts/             # Brand-Fonts (LFS, Lizenz beachten!)
├── icc/               # Color-Profile
└── logos/             # Statische Logos

tools/
├── sla_lib/           # Python-Package: SLA-Reader, Slot-Editor
├── render.py          # Headless-Render-CLI
├── preflight.py       # PDF/X + Custom-Regeln
├── diff.py            # Visual-Regression
└── ai_fill.py         # Slot-Fill via Claude SDK

site/                  # Astro-Galerie
docker/renderer/       # Pinned Renderer-Image
.research/             # Architektur- und Technik-Recherche
```

## Schnellstart (lokal)

```bash
# In Docker (sobald gebaut)
make render TEMPLATE=postkarte-a6-kampagne SAMPLE=klimaschutz
make preflight TEMPLATE=postkarte-a6-kampagne SAMPLE=klimaschutz
make diff TEMPLATE=postkarte-a6-kampagne SAMPLE=klimaschutz

# Direkt (System hat Scribus 1.6.x + Xvfb installiert)
python3 tools/render.py templates/postkarte-a6-kampagne --sample samples/klimaschutz.json
```

## Roadmap

Phasen siehe `.research/00-synthesis.md`. Aktuell: **Phase A — Foundation**.

## Lizenz / Credits

Templates: © Die Grünen Niederösterreich, Brand-Designsystem.
Pipeline-Code: TBD.
Schriften (Gotham Narrow, Vollkorn): proprietäre Lizenzen — siehe `shared/fonts/LICENSE.md`.
