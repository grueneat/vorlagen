# CONTEXT — Designentscheidungen

Issue: **bx4d8** — Überschriften-Abstände (Barlow/Vollkorn) korrigieren,
Falzflyer-Social-Icons fixen, automatisierter Abstands-Check.

Autonom festgehalten. Aufsetzend auf c8bg0 (Barlow + echtes Vollkorn, gemergt).

## Entscheidung 1 — Überschriften-Abstände an der Quelle korrigieren

Mehrteilige Überschriften sind gestapelte Einzelzeilen-Frames mit pro-Schrift-
Baseline-(FLOP)-Korrektur + IDML-Leading, getunt für Gotham. Mit Barlow/Vollkorn
sitzen Zeilen zu eng (oben enger als unten; „dreizeilige" zu nah an der oberen
Zeile). **Fix an der Quelle** (`templates/*/build.py`: Frame-Y-Positionen,
`LINESP`/Leading, FLOP-Baseline-Korrektur), nie im Renderer (Repo-Prinzip
`docs/render-fidelity.md`). Ziel: gleichmäßige, ausgewogene Zeilenabstände,
nichts zu nah am oberen Teil — passend zu Barlow-Cap-Height/Ascent und der
Vollkorn-Akzentzeile.

## Entscheidung 2 — Zeitung-Abstände nachjustieren

`zeitung-a4`: die in c8bg0 reduzierte Leading (`Überschrift Dunkelgrün` 35→28pt,
gegen Clipping) hat teils zu eng gemacht. Abstände sauber neu einstellen — Balance
zwischen „kein Clipping" und „nicht zu eng". `text_render_audit` muss ok bleiben.

## Entscheidung 3 — Falzflyer-Social-Icons reparieren

Ursache der fehlerhaften Icon-Darstellung im Research bestimmen (Asset-Pfad/
-Substitution, Icon-Frame-Geometrie, Render) und an der Quelle beheben. Betrifft
nur manche Falzflyer — genaue Liste im Research.

## Entscheidung 4 — Automatisierter Überschriften-Abstands-Check (neu)

Neues Audit-Tool (z. B. `tools/headline_spacing_audit.py`), das gestapelte
Überschriften-Frames prüft: misst die vertikalen Abstände zwischen den Zeilen
einer Überschrift und flaggt **zu enge** / **ungleichmäßige** Abstände (insb. zu
nah am oberen Teil). Integration in die Audit-/`bin/validate`-Kette, mit Tests.
Soll künftige Schrift-/Layout-Regressionen früh fangen. Genaue Heuristik/
Schwellen im Research/Plan festlegen (auf Basis der korrekten, neu gerenderten
Abstände).

## Entscheidung 5 — Visuelles Review mit Fokus + Baselines danach

- **Besonderer Fokus** auf Überschriften und die Abstände zwischen Überschriften-
  Teilen, über **alle** Templates mit mehrteiligen Überschriften. **Mehrere
  visuelle Vergleiche** (durch mich), bis die Abstände im Layout ordentlich sind.
- **Neue Baselines** erst nach bestätigtem visuellem Review. `pdffonts` weiterhin
  nur Barlow + Vollkorn (kein Fallback), kein Clipping.
- Kein Werkzeug-Attribut in Commits/Code; autonom (kein Plan-Gate).
