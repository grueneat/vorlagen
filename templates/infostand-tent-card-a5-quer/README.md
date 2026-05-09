# Infostand-Tent-Card A5 quer

A4 quer (297 × 210 mm) gefalzt zu einem A5-Tisch-Aufsteller (A5-Tent).
Selbsttragend, beidseitig sichtbar.

## Wann verwenden?

- Infostand am Markt / am Hauptplatz / am Pfarrkaffee.
- Tischaufsteller bei Veranstaltungen ohne Plakatständer.
- Lese-Distanz Tisch-Augen ~50–80 cm.

## Was anpassen?

| Anname | Inhalt |
|---|---|
| `Headline Panel A` | Hauptbotschaft (DE), 1 Zeile |
| `Body Panel A` | 3 Bullets unter Headline Panel A |
| `Headline Panel B` | Sekundär-Botschaft (EN oder zweite DE-Botschaft) |
| `Body Panel B` | 3 Bullets unter Headline Panel B |
| `Impressum (Tent)` | Mediengesetz §24 |

Spec: [`templates/_specs/infostand-tent-card-a5-quer.md`](../_specs/infostand-tent-card-a5-quer.md).

## Falz-Mechanik

Die Karte wird **horizontal in der Mitte** (y=105 mm) gefalzt. Panel A (oben)
liest normal, Panel B (unten) ist um 180° gedreht — beim Falzen kippt Panel B
nach hinten und die Schrift steht korrekt aufrecht für eine Person, die das
Tent von der anderen Seite sieht.

Die Falz-Linie liegt auf einem eigenen **Falz-Layer** mit der Spot-Color
„Falz" (CMYK 100/0/0/0). Sie erscheint im Druck nicht (Layer-DRUCKEN=0), aber
die Druckerei sieht den Pfad als Falz-Anweisung.

**Druckerei-Hinweis:** Bei 250–300 g/m² Karton kann die Falz manuell mit dem
Falzbein gemacht werden (kein Perforieren erforderlich). Bei dickerem Karton
maschinelle Perforation empfehlen.

## Demo-Bilder (synthetisch, KI-generiert)

Die Galerie-Preview zeigt ein synthetisches Hintergrund-Foto
(`samples/hintergrund-mitmachen.jpg`, Infostand-Szene mit Personen
am Tisch) und einen Demo-QR-Code (`samples/qr-mitmachen.png`,
Demo-URL `https://noe.gruene.at/mitmachen/`, 17 mm — D1-konform).

Das Foto trägt das EU-AI-Act-konforme Caption-Watermark
„**Symbolfoto — KI-generiert**" am unteren Bildrand und ist im
Manifest mit `synthetic: true` markiert. **Vor Kampagnen-Einsatz
durch ein reales Infostand-Foto + die echte Bezirks-/Listen-URL
ersetzen** — siehe `samples/manifest.yml`.

## Build

```bash
python3 templates/infostand-tent-card-a5-quer/build.py
# → templates/infostand-tent-card-a5-quer/template.sla
```

## Druck-Empfehlung

- **Trim:** 297 × 210 mm
- **Bleed:** 3 mm allseitig
- **Fold:** y = 105 mm (mittig horizontal)
- **Papier:** Karton 250–300 g/m² (Steifigkeit für Frei-Stand)
- **Druck:** Digital oder Offset (≥ 100)
- **DPI:** 300 für eingebettete Bilder

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.

## V1 Layout: Hero Band (2026-05-09)

V1 etabliert den Rotation-Contract für Multi-Panel-Templates (wiederverwendet
in #21 kandidat-falzflyer): Panel A (DE) bleibt aufrecht, Panel B (EN) ist
um 180° gedreht — beim Falzen lesen beide Tisch-Seiten korrekt.

### Layout zones

Panel A (y=0..105 mm, mirror um y=105 für Panel B):

- **Hero-Band** Dunkelgrün full-bleed an der Apex-Seite (y=-3..42; oberer Streifen).
  Enthält Logo (links 38×30) + Headline 26pt White + Pay-off 16pt Italic Gelb.
- **Photo-Backing** Dunkelgrün full-bleed (y=39..72) — Sicherheit falls Foto fehlt.
- **Photo-Band** `Hintergrund-Mitmachen` 297×33 (y=39..72) — full-bleed 9:1-Slab durch
  Tisch + Personen via build_preview INJECT_MAP + library.inject_into_frame.
- **Weiße Info-Zone** (y=78..94): QR-Code links (12, 78, 17×17) + Bullets (32..142)
  + Termine (152..285).
- **Footer-Strip** Hellgrün full-bleed an der Falz (y=95..105). Enthält
  CTA-Footer URL (links) + Impressum 6pt White (rechts).
- **Mittelfalz** y=105 Spot-Color "Falz" (LAYER=3, DRUCKEN=0).

Panel B spiegelt um y=105: Polygons rotation_deg=0 (Rechtecke), Text/Image-Frames
rotation_deg=180 mit bbox-corner SLA-Math `(x+w, 210-y, w, h)`. Die beiden
Hellgrün-Footer-Strips abutten an der Falz und bilden ein 20 mm-Band über
den Apex (y=95..115 ungefaltet).

### QR module-size decision

QR-Code bleibt **17×17 mm** in der weißen Info-Zone (Panel A: (12, 78, 17, 17);
Panel B: (29, 132, 17, 17, ROT=180)). Die kodierte URL `https://noe.gruene.at/mitmachen/`
(32 Zeichen, error-correction H) ergibt QR-v4 (33 Module). Bei 17 mm Frame-Breite:
17/33 ≈ **0.515 mm/Modul** — D1-konform (≥ 0.5 mm Mindestmodulgröße).

Reduktion auf 14 mm würde 0.424 mm/Modul ergeben (D1-Verletzung); Reduktion auf
QR-v3 (29 Module) erfordert URL-Verkürzung (out of scope, Brand-Stewardship-
Koordination separat). **Footer-Strip beherbergt nur CTA-Footer + Impressum —
QR liegt NICHT im Footer-Strip.**

### Logo aspect note

Logo-Asset `shared/logos/gruene-weiss.png` (413×118 px, 3.5:1 wordmark "DIE GRÜNEN",
weiß-auf-transparent). V1 Logo-Frame ist 38×30 mm (1.27:1). Scribus auto-fit
(`scale_type=0, ratio=1`) preserves aspect → das Wordmark rendert mit **38×10.86 mm**
zentriert im 30 mm hohen Frame, mit ca. 9.5 mm vertikalem Atemraum oben + unten.

Die Brand-Regel `brand:logo_size_3M` operiert auf `frame.w_mm` (38 mm ≈ 3M ± 0.2 mm ✓).
Die 30 mm Frame-Höhe balanciert den Headline+Pay-off-Stack rechts (y=9..35 = 26 mm hoch).
Eine künftige Iteration könnte ein `bund-weiss.png` mit echter 3M-Höhe in Auftrag geben
oder das Logo-Frame auf 38×11 mm verkleinern (exakte Wordmark-Aspect); V1 akzeptiert
die 10.86 mm gerenderte Höhe und überschreibt `brand:image_fills_frame` für die
Logo-Letterbox.

### Photo crop note

Quell-Asset `kontext_infostand_szene` (1536×1024, 1.5:1) wird in `build_preview()`
auf 9:1 zugeschnitten via `library.inject_into_frame(target_w_mm=item.w_mm,
target_h_mm=item.h_mm)` mit LIVE Frame-Dimensionen (post-#24-Idiom). Manifest
`crop_focus: [0.50, 0.55]` zentriert den Crop horizontal mittig + minimal unter
der vertikalen Mitte (Tisch + Personen). Akzeptabel für Demo; Produktions-
Aspect-Optimierung getrackt in #13.

### Build & verify

```bash
python3 templates/infostand-tent-card-a5-quer/build.py
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer
python3 -m unittest tools.sla_lib.tests.test_infostand_tent_card_geometry
```
