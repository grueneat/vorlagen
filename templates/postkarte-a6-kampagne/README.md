# Postkarte A6 — Kampagne

Zweiseitige Kampagnen-Postkarte. Vorderseite trägt die Hauptbotschaft, Rückseite Erklärtext + QR + Impressum.

## Slots

Siehe `meta.yml`. Schnell-Übersicht:

| Slot | Typ | Format-Hinweis |
|---|---|---|
| `headline` | text | **Genau 4 Zeilen** — sonst geht die alternierende Weiß/Gelb-Färbung verloren |
| `stoerer` | text | **Genau 3 Zeilen** für Störer-Kreis |
| `cta` | text | 1 Zeile, Petition-CTA unter Headline |
| `body` | text | Mehrzeiliger Erklärtext, Rückseite |
| `social` | text | 4 Zeilen Social-Handles |
| `url` | text | URL unter QR-Code |
| `impressum` | text | Impressum-Block |
| `hero` | image | optional |
| `logo` | image | gesperrt — `shared/logos/...` |
| `qr` | image | wird aus `url` generiert (Pipeline) |

## Bekannte Limits (v0-Editor)

- Mehrzeilige Slots **müssen** die gleiche Zeilenzahl wie das Original haben, sonst fällt der Editor auf eine Single-Style-Strategie zurück und Mixed-Formatting (z.B. abwechselnde Farbe) geht verloren.
- Bilder im `hero`-Slot werden noch nicht skaliert/zugeschnitten — Bildverhältnis muss zu `aspect: "2:3"` passen.

## Rendern

```bash
python3 tools/render.py templates/postkarte-a6-kampagne --sample klimaschutz
# → build/postkarte-a6-kampagne__klimaschutz/postkarte-a6-kampagne__klimaschutz.pdf
```

## Samples

- `klimaschutz.json` — Klima-Kampagne
- `wohnen.json` — Wohnen-Kampagne
