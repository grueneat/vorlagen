---
id: f7yk1
title: Migration auf design-system v2.0/v2.1 (Token-Drift beheben, Lightbox-Dedup,
  Massen-Inline-Styles raus)
status: open
priority: medium
labels:
- migration
- design-system
- umbrella
remote:
- source: github
  id: '126'
  url: https://github.com/GrueneAT/vorlagen/issues/126
---

Migration der Vorlagen-Site auf das Gruene-AT-Design-System (v2.0/v2.1). Heute komplett DS-unverbunden — lokale Custom-Vars (`--gruen-dunkel: #2a734f`, `--gruen-hell`, `--gelb`, `--magenta`) **mit nachweisbarer Drift zum DS** (`--gat-color-dunkelgruen: #2c6e40`). Astro-Stack mit 3 Hauptseiten (Galerie/Templates, Experiments/Voting, Schriften-Vergleich). 3x duplizierte Lightbox-Implementierung.

Umbrella-Migrationsticket. Bezugnehmend auf Cross-Repo-Audit (2026-05-23). Siehe `notes/audit.md` fuer den vollstaendigen Befund + `https://github.com/GrueneAT/design-system/issues/13` fuer die DS-v2.1-Welle.

## Migrations-Phasen

### Phase 0 — Quick-Wins (unabhaengig, sofort umsetzbar)

1. **DS-CSS-Link einbinden** — in `Base.astro` als globaler `<link>`.
2. **Lokale Farb-Vars find-replace** — `--gruen-dunkel` → `var(--gat-color-dunkelgruen)`, `--gruen-hell` → `var(--gat-color-hellgruen)`, `--gelb` → `var(--gat-color-gelb)`, `--magenta` → `var(--gat-color-magenta)`. Drift sofort weg.
3. **DS-Logo per CDN** — eigene Logo-Asset-Kopie loeschen.
4. **Header umstellen** — bestehende Header-Implementation durch `.gat-header --dunkel` ersetzen (Quick-Win, ~30 Zeilen weg).
5. **`.gat-skiplink`** ergaenzen.
6. **Zwei verschiedene `--gruen-hell`-Hex-Werte im selben Dokument** (`#6abf2c` vs Fallback `#c9d400`) bereinigen — beide auf `var(--gat-color-hellgruen)`.

### Phase 1 — Warten auf DS-v2.1 (extern)

Dieses Repo bekommt v2.1 automatisch durch CDN-Refresh, sobald `grueneat/design-system#13` gemerged ist. v2.1 liefert: `.gat-input`-Familie, `.gat-modal`, `.gat-callout`-/-`.gat-tag`-Modifier.

### Phase 2 — Voll-Migration (nach DS-v2.1)

1. **Modal/Lightbox** — die 3-fach duplizierte Lightbox-Implementierung konsolidieren auf `.gat-modal`. Eine Loesung statt drei.
2. **Status-Lozenges** (success/warning/danger) auf `.gat-tag --ok/--warn/--error` umstellen.
3. **Toast-Container** — wenn `.gat-toast` in v2.2 landet, dort migrieren; sonst lokal als `.app-toast` umbenennen.
4. **Vergleichstabelle** mit Sticky-Col — wenn `.gat-table` in v2.2 landet, dort migrieren.
5. **CTA-Banner-Link** als `.gat-callout` mit Link-Modifier.
6. **Breadcrumb** — wenn `.gat-breadcrumb` in v2.3 landet, dort migrieren.
7. **Galerie-Karten/Grid** — auf `.gat-card`-Komposition pruefen.
8. **App-spezifisch als `.app-*`** umbenennen: `.variant-card`, `.checkmark`, `.ranked-row`, `.sortable-list`, Voting-Engine, Schriften-Vergleichs-Logik, Drag-Handle-Touch-Action, localStorage-Privatmodus-Banner.
9. **Hartkodierte Drift normalisieren**: 12+ Status-Hex, 15 Ad-hoc-Greys auf DS-Tokens, Radien-Streuung (4/6/8/9/50%) auf `--gat-radius-sm/-md`, 3 Box-Shadow-Varianten auf `--gat-web-shadow`.
10. **Headlines** bekommen `.gat-headline`-Klasse statt `color: var(--gruen-dunkel)` per Tag-Selector.
11. **Massen-Inline-Styles** in `Base.astro` und Page-Astros aufloesen — minus ~350 Zeilen.
12. **Print-Page-Tokens** (DIN-A4/A3/A5) — wenn diese in v3.0 ins DS kommen, dort migrieren; sonst hier als Audit-Befund-Vorlage fuer DS dokumentieren.
13. **Doku-Abschluss**: `notes/iteration-abschluss.md`.

## Akzeptanzkriterien

### Phase 0
- [ ] `<link>` auf DS-CSS in `Base.astro`
- [ ] `--gruen-*`/`--gelb`/`--magenta` ueberall als `var(--gat-color-*)` aliased
- [ ] DS-Logo per CDN, lokale Asset-Kopie geloescht
- [ ] Header ist `.gat-header --dunkel`
- [ ] `.gat-skiplink` ergaenzt
- [ ] Zwei verschiedene `--gruen-hell`-Werte vereinheitlicht

### Phase 2 (nach DS-v2.1)
- [ ] Lightbox 3x-Duplikat konsolidiert auf `.gat-modal`
- [ ] Status-Lozenges auf `.gat-tag`-Modifier
- [ ] App-spezifische Klassen sind `.app-*`-Namespace
- [ ] Hartkodierte Hex/Radien/Shadows durch DS-Tokens ersetzt
- [ ] Massen-Inline-Styles minimal (`Base.astro` schlanker)
- [ ] `notes/iteration-abschluss.md` dokumentiert Migration

### Querschnitt
- [ ] `grep -rE "claude|Generated with|Co-Authored-By" .` liefert 0
- [ ] Keine neuen Vendoring-Verzeichnisse
- [ ] Konsumenten-URL als Quelle
- [ ] Pages-Deploy nach Merge funktioniert
- [ ] Branch zurueck auf `main`-Familie (heute auf `feat/schriften-tahoma-entscheidung`)

## Constraints

- **Kein Vendoring.**
- **Keine Werkzeug-Attribution.**
- **Phase 0 zuerst.** Phase 2 wartet auf DS-v2.1-Release.
- **`Base.astro`** ist der zentrale Hebel — Aenderungen dort propagieren ueber alle Seiten.

## Hintergrund

Aus dem Cross-Repo-Audit: 10 DS-Aufnahme-Kandidaten, 5 Hybrid, 4 app-spezifisch. **Konkrete Token-Drift nachgewiesen**: `--gruen-dunkel: #2a734f` (lokal) ≠ `--gat-color-dunkelgruen: #2c6e40` (DS). Phase 0 zieht das sofort wieder zusammen. Siehe `notes/audit.md` + `notes/SYNTHESIS.md`.
