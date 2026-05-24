# DS v2.2-Adoption — Tabelle + Toast

Stand: 2026-05-24 · Branch `issue/v22a-vorlagen-adopt-table-toast` ·
Folge-Ticket nach DS-Migration Phase 2.

## Kontext

Cross-Reference: `.issues/archive/f7yk1-migration-auf-design-system-v20v21-token-drift-beheben-lightbox-dedup-massen-inl/notes/iteration-abschluss.md`
Abschnitt „Was bewusst NICHT in dieser Phase ist".

Dort waren drei Punkte als „warten auf DS-Releases" markiert:

1. Toast-Container → `.gat-toast` (DS v2.2) — **hier umgesetzt**
2. Vergleichstabelle Sticky-Col → `.gat-table` (DS v2.2) — **hier umgesetzt**
3. Breadcrumb → `.gat-breadcrumb` (DS v2.3) — **nicht in v2.2**, weiter
   lokal als `.app-breadcrumb`, Migration sobald DS v2.3 erscheint.

## Was geliefert wurde

### Toast (`experiments/[id].astro` + `app.css`)

- Markup: ein einzelnes `<div class="gat-toast">` mit `<div class="gat-toast__body">` in einer `<div class="gat-toaster">`-Region.
- JS-Helper `showToast()` wechselt nur noch die Klasse zwischen
  `gat-toast--success` und `gat-toast--error` und schaltet `display`
  zwischen `none` und `flex`.
- Lokale CSS-Regel `.app-toast` (15 Zeilen) entfallen, war Platzhalter
  bis DS v2.2.

### Bewertungstabelle (`schriften/index.astro` + `app.css`)

- `<div class="gat-table-scroll">` + `<table class="gat-table gat-table--sticky-col gat-table--compact gat-table--zebra">` ersetzen den
  `.app-eval-table-wrap` + `.app-eval-table*`-Stack (~50 Zeilen CSS).
- Erste Spalte bleibt beim Quer-Scroll sichtbar (DS deckt
  `tbody td:first-child`).
- Zebra-Streifen, kompaktes Padding, Hairlines und Header-Typografie
  kommen jetzt aus dem DS.
- Row-Header bleiben `<th scope="row">` für die A11y-Semantik. Eine
  kleine seitenlokale Klasse `.app-eval-rowhead-sticky` ergänzt das
  Sticky-Verhalten dort, weil der DS-Selektor nur `td:first-child`
  abdeckt. Sobald DS einen Row-Header-Modus liefert, kann auch das
  weg.
- Verbleibende seitenlokale Mini-Helpers: `.app-eval-rowhead-hint`
  (Untertitel im Row-Header), `.app-eval-col-tag` (Lozenge im
  Spalten-Header), `.app-eval-rating*` (Drei-Dot-Rating-Glyph). Alle
  schmal, keine Duplikate mit DS-Bausteinen.

### Ausgelassen / nicht anwendbar

- **`.gat-dropzone`** — die Vorlagen-Site hat keinen Upload-Flow, daher
  keine Adoption.
- **`.gat-toolbar`** — der einzige Bar-artige Block (`.app-exp-toolbar`
  im Voting) ist eine flache Steuerleiste am Seitenanfang, kein
  klebriger Action-Bar am unteren Rand. `.gat-toolbar` ist `position:
  sticky; bottom: 0` mit Toolbar-Schatten — semantisch nicht
  passend. Übersprungen.
- **`.gat-table__num`** — die Bewertungstabelle hat keine rein
  numerischen Spalten (Ratings sind Glyph-Symbole, Ja/Nein sind
  Tags). Kein Bedarf.

## Build / Live-Verify

- `cd site && npm ci && npm run build` — 27 Seiten weiter grün.
- Live-Verify nach Pages-Deploy: `/schriften/` mit sticky-Col-Zebra-
  Tabelle, Toast-Pfad nur bei vorhandenen Experimenten testbar.
