# CONTEXT — Designentscheidungen

Issue: **c8bg0** — Vorlagen auf Barlow Semi Condensed umstellen, Fremdschriften +
Schriftvergleich entfernen, Baselines neu erzeugen.

Autonom festgehalten (User: „no questions, just do it"). Aufbauend auf der
Architektur-Recherche und dem Vorbild Bildgenerator (Issue z6qfk).

## Entscheidung 1 — Eine Schrift: Barlow Semi Condensed, alles andere raus

Alle Templates verwenden ausschließlich **Barlow Semi Condensed**. Sämtliche
Nicht-Barlow-Families werden aus `templates/*/build.py` und den `*-original.sla`
entfernt und ersetzt. Gewicht-Mapping (verfügbare Barlow-Schnitte
Regular/Bold/ExtraBold/Black):

| Alt | Neu |
| :-- | :-- |
| Gotham Narrow Book | Barlow Semi Condensed Regular (400) |
| Gotham Narrow Bold | Barlow Semi Condensed Bold (700) |
| Gotham Narrow Black | Barlow Semi Condensed Black (900) |
| Gotham Narrow Ultra | Barlow Semi Condensed Black (900) |
| Minion Pro / Times Roman / Tahoma | Barlow Semi Condensed (passender Schnitt) |
| **Vollkorn (Black/Bold Italic)** | **Barlow Semi Condensed** (Black, ggf. Italic falls Akzent nötig) |

**Vollkorn-Hinweis:** Vollkorn ist eine freie Akzentschrift und im Org-Design-System
als `--gat-font-emphasis` vorgesehen. Der User hat aber explizit „alle anderen
Schriften raus" verlangt → Vollkorn wird in den Templates **ebenfalls durch
Barlow ersetzt**. Bewusste Entscheidung gemäß Auftrag; nicht im Research
re-litigieren. (Falls ein kursiver Akzent gebraucht wird: Barlow-Italic-TTF
nachziehen.)

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
