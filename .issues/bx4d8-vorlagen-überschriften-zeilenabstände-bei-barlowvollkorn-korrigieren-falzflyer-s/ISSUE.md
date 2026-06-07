---
id: bx4d8
title: 'Vorlagen: Überschriften-Zeilenabstände bei Barlow/Vollkorn korrigieren, Falzflyer-Social-Icons
  fixen, automatisierter Abstands-Check'
status: done
priority: high
labels:
- templates
- fonts
- visual-qa
- bug
remote:
- source: github
  id: '134'
  url: https://github.com/GrueneAT/vorlagen/issues/134
---

## Kontext

Folge-Korrekturen nach der Schriftumstellung der Vorlagen auf Barlow Semi
Condensed (+ Vollkorn-Akzent), Issue c8bg0 (gemergt/deployed). Beim Einsatz im
Layout sind zwei konkrete Regressionen sichtbar geworden, plus der Wunsch nach
einem automatisierten Abstands-Check für Überschriften.

## Problem 1 — Überschriften-Zeilenabstände zu eng (Barlow/Vollkorn-Mix)

Mehrzeilige Überschriften sind im DSL als **gestapelte Einzelzeilen-Frames**
umgesetzt (IDML-`<Br/>` mit Font-Wechsel pro Zeile, z. B. Barlow + Vollkorn),
mit **pro-Schrift-Baseline-(FLOP)-Korrektur** je Zeile. Diese Korrekturen waren
auf **Gotham** getunt. Mit Barlow (andere Cap-Height/Ascent) stimmen die
vertikalen Abstände nicht mehr:

- Wenn zwischen **Standard-Schrift (Barlow)** und **Vollkorn** gewechselt wird,
  sitzen Zeilen **zu knapp zusammen** — die obere Lücke ist enger als die untere.
- **Konkret:** „**dreizeilige**" (Vollkorn-Zeile, gelb) ist **zu nah an der
  Zeile darüber** („Das ist die"). Sichtbar u. a. in den `*-zweigeteilt`- und
  weiteren Flyer-Templates mit „Das ist die / dreizeilige / Headline".
- Betrifft **mehrere Templates** — systematisch dort, wo Barlow- und
  Vollkorn-Zeilen in einer gestapelten Überschrift gemischt werden.

**Ziel:** Die Zeilenabstände innerhalb mehrteiliger Überschriften ordentlich
ausbalancieren (gleichmäßig, nicht zu nah am oberen Teil), passend zu den
Barlow-/Vollkorn-Metriken — an der Quelle (`build.py` Frame-Y/Leading/FLOP),
nicht im Renderer.

## Problem 2 — Zeitung: Überschriften zu knapp aneinander (Barlow)

In `zeitung-a4` stehen manche Überschriften mit Barlow **zu knapp aneinander**
(Abstände zwischen Überschriften/Überschrift-Teilen zu gering). In c8bg0 wurde
die Leading der `Überschrift Dunkelgrün` von 35→28pt reduziert (gegen Clipping)
— das hat teils zu eng gemacht. Hier die Abstände sauber neu justieren.

## Problem 3 — Falzflyer: Social-Media-Icons werden nicht ordentlich angezeigt

In **manchen Falzflyern** werden die **Social-Media-Icons nicht ordentlich
dargestellt** (z. B. falsches/fehlendes Icon, Platzhalter, Fehlausrichtung). Im
Research die Ursache finden (Asset-Pfad/-Substitution, Icon-Frame, Render) und an
der Quelle beheben.

## Problem 4 — Automatisierter Überschriften-Abstands-Check

Zusätzlich einen **automatisierten Check** bauen, der die Abstände innerhalb von
(mehrteiligen) Überschriften prüft: erkennt Zeilen, die **zu nah** aneinander
sitzen (insb. zu nah am oberen Teil), bzw. ungleichmäßige Zeilenabstände in
gestapelten Überschriften-Frames. Soll in die bestehende Audit-/Validate-Kette
(`bin/validate` / `tools/*audit*`) passen und künftige Schrift-/Layout-Regressionen
früh fangen.

## Vorgehen / Anforderungen

1. **Überschriften-Review mit besonderem Fokus** auf die Abstände zwischen den
   verschiedenen Teilen einer Überschrift — über **alle** Templates, die
   mehrteilige/gestapelte Überschriften haben. **Mehrere visuelle Vergleiche**,
   um sicher zu sein, dass die Abstände im Layout ordentlich sind und nichts zu
   nah am oberen Teil sitzt.
2. Abstände an der Quelle (`templates/*/build.py`: Frame-Y, Leading/`LINESP`,
   FLOP-Baseline-Korrektur) für Barlow/Vollkorn korrigieren; neu rendern.
3. Social-Icon-Defekt in den betroffenen Falzflyern beheben.
4. Automatisierten Überschriften-Abstands-Check implementieren (+ Tests).
5. **Neue Baselines** für die geänderten Templates erst nach bestätigtem
   visuellem Review festschreiben; `text_render_audit` ok, kein Clipping,
   `pdffonts` weiterhin nur Barlow + Vollkorn (kein Fallback).

## Akzeptanzkriterien

- [ ] Mehrteilige Überschriften haben ordentliche, ausgewogene Zeilenabstände (nichts zu nah am oberen Teil); „dreizeilige"-Fall behoben — visuell über alle betroffenen Templates geprüft (mehrere Vergleiche dokumentiert)
- [ ] Zeitung-Überschriften mit Barlow haben saubere Abstände (nicht zu eng)
- [ ] Falzflyer-Social-Icons werden in allen betroffenen Templates korrekt angezeigt
- [ ] Automatisierter Überschriften-Abstands-Check vorhanden (in `tools/` + `bin/validate`-Kette), mit Tests; fängt zu enge/ungleichmäßige Überschriften-Abstände
- [ ] Neue Baselines erzeugt; visual_diff/Tests grün; `pdffonts` nur Barlow + Vollkorn; kein Clipping (`text_render_audit` ok)
- [ ] Kein Werkzeug-Attribut in Commits/Code

## Hinweise

- Fix immer an der **Quelle** (`build.py`/SLA), nie im Renderer (Repo-Prinzip
  `docs/render-fidelity.md`).
- Scribus-Rendering nur im Dev-Container; CI rendert nicht (Staleness-Gate) —
  Baselines/Previews lokal erzeugen und committen.
- Aufsetzend auf c8bg0 (Barlow + echtes Vollkorn bereits committet/installiert).
