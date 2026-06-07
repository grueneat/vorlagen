# CONTEXT — Designentscheidungen

Issue: **c8bg0** — Vorlagen auf Barlow Semi Condensed umstellen, Fremdschriften +
Schriftvergleich entfernen, Baselines neu erzeugen.

Autonom festgehalten (User: „no questions, just do it"). Aufbauend auf der
Architektur-Recherche und dem Vorbild Bildgenerator (Issue z6qfk).

## Entscheidung 1 — Gotham → Barlow ersetzen; Vollkorn BLEIBT (Korrektur)

**KORREKTUR (User, 2026-06-07):** „Die Vollkorn Schrift muss bleiben, nur gothic
muss ersetzt werden aber Vollkorn bleibt." → Es wird **nur Gotham Narrow** durch
Barlow Semi Condensed ersetzt. **Vollkorn bleibt unverändert** als Akzent-/
Emphasis-Schrift (entspricht dem Org-Design-System `--gat-font-emphasis =
"Vollkorn"`). Das Zielbild ist damit Design-System-konform: Barlow für Headlines/
Fließtext (vormals Gotham), Vollkorn für Akzente/Pull-Quotes/Italic.

Gewicht-Mapping (verfügbare Barlow-Schnitte Regular/Bold/ExtraBold/Black):

| Alt | Neu |
| :-- | :-- |
| Gotham Narrow Book | Barlow Semi Condensed Regular (400) |
| Gotham Narrow Bold | Barlow Semi Condensed Bold (700) |
| Gotham Narrow Black | Barlow Semi Condensed Black (900) |
| Gotham Narrow Ultra | Barlow Semi Condensed Black (900) |
| Minion Pro / Times Roman | Barlow Semi Condensed (passender Schnitt) — proprietäre IDML-Reste, nicht Vollkorn |
| **Vollkorn Black/Bold Italic** | **BLEIBT Vollkorn** (unverändert) |

**Frühere (verworfene) Annahme:** In der ersten Fassung wurde Vollkorn
fälschlich mit Barlow ersetzt; das wird zurückgesetzt — Vollkorn-Italic-Akzente
(z. B. gelbe Pull-Quote-Wörter, Zitate) sind wieder Vollkorn Black/Bold Italic.
Tahoma/Minion/Times Roman sind proprietäre IDML-Konvertierungsreste (keine
Marken-/Akzentschriften) und werden weiterhin durch Barlow ersetzt.

## Entscheidung 2 — Lokale Font-Bereitstellung (Druck-Pipeline-Ausnahme)

Scribus rendert PDFs lokal und kann **keinen Webfont per CDN** ziehen (anders als
der Bildgenerator, der zur Laufzeit im Browser lädt). Barlow muss für
fontconfig/Scribus als **lokale TTF** vorliegen. Barlow ist **SIL OFL**, daher
erlaubt es die No-Vendoring-Regel — wie das bereits vendorisierte Vollkorn und
mupdf/sqlite in gemeindefinanzen — als bewusste **Druck-Pipeline-Ausnahme**.

- Barlow-TTFs aus `shared/fonts/alternatives/barlow-semi-condensed/` als
  reguläre Repo-Font bereitstellen (z. B. `fonts/barlow-semi-condensed/`) und
  über `Dockerfile.claude` in fontconfig installieren.
- `Dockerfile.claude` Font-Sanity-Check auf Barlow erweitern; `fc-match
  "Barlow Semi Condensed"` muss eine Barlow-TTF liefern (aktuell DejaVu-Fallback).
- Headless-Rendering nutzt xvfb (Scribus braucht Display) — bestehende Pipeline.

## Entscheidung 3 — Schriftvergleiche vollständig entfernen

Komplettes Feature aus #42 entfernen: `site/src/pages/schriften/index.astro`,
`site/src/data/schriften.json` + `schriften-bewertung.json`,
`tools/fonts_compare_build.py`, generierte Artefakte `site/public/schriften/`
und `templates/flyer-a6-hochformat-gruenes-cover/fonts/`, Nav-Link zu
`/schriften/`, Alternativ-Fonts `shared/fonts/alternatives/` (+ `alternatives.yml`).
`tools/font_variants.py` nur entfernen, wenn nirgends sonst genutzt — sonst
behalten. Keine toten Referenzen/Links zurücklassen.

## Entscheidung 4 — Visuelles Review JEDER Seite vor Baseline-Festschreibung

Da Barlow schmäler als Gotham ist (verschobene Umbrüche/Zentrierung) und der
Vergleich gegen die alten Ausgangs-PDFs nicht mehr passt:

1. Alle Templates neu rendern (`bin/render-gallery`, ggf. ohne Visual-Diff gegen
   alte Baselines).
2. **Jede gerenderte Seite jedes Templates visuell prüfen** (PNG/PDF ansehen):
   Text-Ausrichtung und Zentrierung korrekt? Keine Überläufe/Abschnitte?
   `bin/audit-alignment` / `bin/check-fontsizes` als Hilfsmittel nutzen.
3. **Mehrere visuelle Vergleiche** zur Absicherung. Auffälligkeiten im Template
   fixen, neu rendern, bis alle Seiten sauber sind.

## Entscheidung 5 — Neue Baseline-/Ausgangs-PDFs erst nach Sign-off

Erst nach bestätigtem visuellem Review die neu gerenderten PDFs als neue
`baseline.pdf` je Template (und `*-original.pdf`, soweit sinnvoll) festschreiben.
`TOLERANCES.yml` bei Bedarf anpassen. Previews/PNGs + Staleness-Metadaten
konsistent halten (CI-Stale-Previews-Gate grün). Visual-Diff/Tests laufen danach
gegen die **neuen** Baselines.

## Prozess-Entscheidung — autonom, kein Plan-Gate

Auf Wunsch des Users („no questions, just do it", „/issue:work … und shippe es")
läuft die Pipeline autonom durch (Discuss→Research→Plan→Execute) ohne
interaktives Plan-Review, anschließend `/issue:ship`. Werkzeug-Attribution in
Commits/Code ist verboten.
