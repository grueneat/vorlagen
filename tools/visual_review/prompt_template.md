# Visual QA — Issue #11 Demo Content (Codex portraits + QR codes)

You are reviewing the rendered preview of a Grünen template that has been
populated with demo content (Codex-generated portraits/themen-photos
watermarked with "Symbolfoto — KI-generiert" + branded QR codes encoding
real noe.gruene.at URLs).

The 5 templates this PR populates are:
1. `kandidat-falzflyer-din-lang` — A4 quer 6-panel falzflyer with 1 portrait + 3 themen-photos + 2 QRs on the closer panel
2. `themen-plakat-a3-quer` — A3 quer plakat with 1 themen-hero photo + 1 corner QR
3. `tischschild-a5-quer` — A4 quer tent-card with 1 hintergrund photo + 1 QR (enlarged 14→17 mm)
4. `wahlaufruf-postkarte-a6-quer` — A6 quer postkarte with 1 back-side QR
5. `wahltag-tueranhaenger` — 105×250 mm türanhänger with 1 back-side QR

Compared to the previous version (placeholder slots, empty image
frames, no QR codes), is this template now visibly better? Or worse?

## Question 1 — Improvement vs prior placeholder version

Sehen die neuen Templates mit echten Bildern + funktionalen QRs sichtbar
besser aus als die Platzhalter-Version? Wo am stärksten? Falls nein,
was stört?

## Question 2 — Portrait + Themen-Fotos (falzflyer specifically)

Falls das Template ein Portrait oder Themen-Fotos hat:
- Brand-konform (österreichischer Kontext, nicht US-Suburbia, nicht Stockfoto-generisch)?
- Diversity über Themen-Fotos hinweg?
- "Symbolfoto — KI-generiert" Watermark legibel ABER unaufdringlich?

## Question 3 — QR codes

Falls das Template einen QR-Code hat:
- Visuell gut integriert in das Brand-Layout?
- Logo-Embed funktioniert (sichtbar zentriert, nicht visuell zu stark)?
- Größe stimmt (im finalen Druck scannbar)?
- Position sinnvoll (Lesefluss nicht unterbrochen)?

## Question 4 — Galerie-Wirkung gesamt

- Wirkt das Template jetzt "kampagnenreif"?
- Gibt es störende Layout-Probleme die durch das Hinzufügen der Slots entstanden sind?

## Output (strict JSON)

```json
{
  "verdict": "ship | iterate | block",
  "improvement_vs_placeholder": "<paragraph>",
  "portrait_photos_quality": "<paragraph or 'n/a'>",
  "qr_integration": "<paragraph or 'n/a'>",
  "blockers": ["..."],
  "iterate_suggestions": ["..."],
  "ship_strengths": ["..."]
}
```
