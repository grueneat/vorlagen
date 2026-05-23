# Iteration-Abschluss — DS-Migration GrueneAT/vorlagen

Stand: 2026-05-23 · Issue #126 · Phase 0 + Phase 2 abgeschlossen.

## Was geliefert wurde

### Phase 0 (merged via #127, on `main`)

- `<link rel="stylesheet">` auf `https://grueneat.github.io/design-system/design-system.css` in `Base.astro` — kein Vendoring, CDN-Bezug.
- Lokale Marken-Vars `--gruen-dunkel`/`--gruen-hell`/`--gelb`/`--magenta` umgehängt auf `var(--gat-color-*)`. Drift sofort gestoppt.
- Header umgestellt auf `.gat-header --dunkel`; eigene Header-CSS-Implementation (~30 Zeilen) entfernt.
- Logo per CDN aus `design-system/assets/gruene-logo.svg`; lokale Asset-Kopie entfernt.
- `.gat-skiplink` „Zum Hauptinhalt springen" als A11y-Verbesserung.

### Phase 2 (dieser Branch — `issue/...-phase2`)

8 atomare Commits, jeder mit grünem Build (27 Seiten):

1. **Lightbox-Konsolidierung** — die drei lokal duplizierten Implementierungen (templates/[...id].astro, experiments/[id].astro, schriften/index.astro) zusammengeführt auf `<dialog class="gat-modal gat-modal--wide gat-modal--blur">` über `components/Lightbox.astro`. Focus-Trap/Esc/Backdrop kommen vom `<dialog>`-Element. Trigger-Wiring per `data-lightbox-*`-Attributen, programmatischer Direkt-Öffner (`openAt`) für JSON-gerenderte Karten, `lightbox:render`-Event-Hook für den Schriften-Switcher.
2. **Status-Tags** — Empfehlung/Zweitwahl/Davon-abraten + Ja/Nein-Bewertungen auf `.gat-tag --ok/--info/--error` umgestellt. Begleitend Border/Background-Hex auf `--gat-web-hairline`/`--gat-web-surface-sunk` reduziert.
3. **Callouts** — Index-CTA-Banner als `.app-cta`-Variante, Schriften-Empfehlungs-Stapel als `.gat-callout --success/--info/--danger`, Privatmodus-Banner + „Renderings fehlen"-Hinweis als `.gat-callout --warn`.
4. **App-Namespace** — alle Voting-Engine-spezifischen Klassen (`.variant-card`, `.checkmark*`, `.position-badge`, `.ranked-row`, `.drag-handle`, `.arrow-up/down`, `.remove-btn`, `.rank-empty`, `.thumbnail`, `.title`, `.vote-submission`, `.sr-only`) auf `.app-*`-Namespace umbenannt. Direct-Pick-Karten-Builder zieht jetzt aus `app.css` statt aus 7 `cssText`-Strings im JS.
5. **Token-Drift** — 12+ Status-Hex, 15 Ad-hoc-Greys, Radien (4/6/8/9/50%-Streuung) und 3 Box-Shadow-Varianten durchgehend auf `var(--gat-color-*)`/`var(--gat-web-*)`/`var(--gat-web-radius-*)`/`var(--gat-web-shadow)` zurückgeführt. `Base.astro` lokale Vars (`--bg`/`--text`/`--muted`) jetzt Aliase auf DS-Web-Tokens.
6. **Headlines** — globaler Tag-Selector `h1, h2, h3 { color: var(--gruen-dunkel) }` entfernt; alle 22 Headlines bekommen explizit `class="gat-headline"`. DS-Klasse in `app.css` so überschrieben, dass nur die Farbe greift (nicht die H1-Größe).
7. **Massen-Inline-Styles** — verbleibende Inline-Style-Blöcke in den Page-Astros in semantische `.app-*`-Klassen in `src/styles/app.css` extrahiert.
8. **Doku** — diese Datei.

## Was bewusst NICHT in dieser Phase ist

Diese Punkte aus dem Issue-Audit warten auf DS-v2.2/v2.3-Releases bzw. erfordern eigene Tickets:

- **Toast-Container** als `.gat-toast` (lokal als `.app-toast --ok|--error` umgesetzt).
- **Vergleichstabelle Sticky-Col** auf `.gat-table` (lokal als `.app-eval-table*` umgesetzt; sticky-Verhalten unverändert).
- **Breadcrumb** auf `.gat-breadcrumb` (lokal als `.app-breadcrumb` umgesetzt).
- **Print-Page-Tokens** für DIN-A4/A3/A5 — kommen vermutlich in DS-v3.0, dann hier migrieren.

## App-Klassen-Inventur — Doppel-Pflege weg

| Vor (lokal, gemischter Namespace) | Nach (DS oder `.app-*`)                           |
|----------------------------------|---------------------------------------------------|
| 3x Lightbox-Implementation       | 1x `components/Lightbox.astro` (`.gat-modal`)     |
| `.variant-card`                  | `.app-variant-card`                               |
| `.checkmark` / `.checkmark-visual` / `.position-badge` | `.app-checkmark*` / `.app-position-badge` |
| `.ranked-row` / `.arrow-up/down` / `.remove-btn` / `.thumbnail` / `.title` | `.app-ranked-row` / `.app-arrow-up/down` / `.app-remove-btn` / `.app-thumbnail` / `.app-title` |
| `.drag-handle` / `.rank-empty` / `.sr-only` / `.vote-submission` | `.app-drag-handle` / `.app-rank-empty` / `.app-sr-only` / `.app-vote-submission` |
| `.preview-link` (inline)         | `.app-lightbox-trigger`                           |
| `.schrift-preview` (inline)      | `.app-schrift-preview` (Daten-Attribut-Trigger)   |
| 3x „weiße Karte mit Box-Shadow"  | 1x `.app-card` + `.app-card-grid`                 |
| 2x index-CTA-Banner-Hex          | 1x `.app-cta`                                     |
| Status-Lozenges hand-Hex         | `.gat-tag --ok/--info/--error/--warn`             |

## Inline-Styles-Diff (Zeilen weg)

Gegen `origin/main` (Phase 0 als Baseline):

| Datei                                | Vorher | Nachher | Diff   |
|--------------------------------------|-------:|--------:|-------:|
| `pages/experiments/[id].astro`       |   1195 |     934 |   −261 |
| `pages/templates/[...id].astro`      |    155 |      80 |    −75 |
| `pages/schriften/index.astro`        |    483 |     421 |    −62 |
| `pages/index.astro`                  |    102 |      96 |     −6 |
| `pages/typ/[category].astro`         |     70 |      67 |     −3 |
| `pages/experiments/index.astro`      |     58 |      55 |     −3 |
| `components/Breadcrumb.astro`        |     22 |      22 |      0 |
| `layouts/Base.astro`                 |     60 |      64 |     +4 |
| **Summe Page-Astros**                | **2145** | **1739** | **−406** |

Konzentriert ausgelagert nach:
- `components/Lightbox.astro` (207 Zeilen — eine Lösung statt drei)
- `styles/app.css` (~913 Zeilen — durchgängig DS-Token-basiert)

Issue-Ziel war −350 in den Page-Astros — übererfüllt mit −406.

## Build-Status

- 27 Seiten bauen sauber (`npm run build` in `site/`)
- Keine TypeScript-Diagnostics, keine Astro-Warnings
- Keine neuen Vendoring-Verzeichnisse — DS-CSS, DS-Logo, Schriften per CDN/SIL-OFL self-hosted

## Querschnitt-Akzeptanz

- [x] Werkzeug-Attribution-Scan über die Diff liefert nichts
- [x] Keine neuen Vendoring-Verzeichnisse
- [x] Konsumenten-URL (`https://grueneat.github.io/design-system/`) als einzige Quelle
- [x] Pages-Deploy nach Phase-0-Merge funktioniert; Phase-2-Merge folgt
