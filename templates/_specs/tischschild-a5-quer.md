# Spec: Infostand-Tent-Card A5 quer (V1 "Hero Band")

```yaml
id: tischschild-a5-quer
title: Infostand-Tent-Card A5 quer
format: A4 quer (297×210) gefalzt zu A5-Tent
trim_mm: [297, 210]
bleed_mm: 3
pages: 1
fold_type: tent
fold_positions_mm: [105]   # horizontal fold at y=105 mm (mittig)
cut_type: none
audience: [bezirksgruppe, ortsgruppe, infostand-helfer]
```

## Audience und Layout-Philosophie

**Infostand-Tisch-Aufsteller** (Tent-Card / Table-Tent): Bezirks-/Ortsgruppen stellen
die Karte am Infostand, am Pfarrkaffee-Tisch oder bei Veranstaltungen auf. Selbsttragend
durch eine horizontale Falzung in der Mitte: das A4-quer-Blatt wird zu einem A5-quer-Tent
gefalzt, das aus beiden Richtungen sichtbar ist.

Lese-Distanz **Tisch-Augen-Distanz** ~50–80 cm.

**Layout-Philosophie (V1 — "Hero Band"):** Vierte von fünf V1-Implementierungen; **erstes
multi-panel Template** im Repository. V1 etabliert den Rotation-Contract für Multi-Panel-
Vorlagen, der in #21 (kandidat-falzflyer) wiederverwendet wird. Beide Panele (Panel A DE,
Panel B EN) lesen je nach Tisch-Seite. Das Build-Skript emittiert beide Panele aus einer
einzelnen Quelle: zwei Builder-Helper `_panel_de()` (aufrecht) und `_panel_en()` (rotiert
180° via per-Frame-Mathematik).

V1 ersetzt das V0-Layout (Logo + Headline + 3 Bullets + CTA + Termine + Impressum) durch
ein **Hero-Band-orientiertes** Layout: Dunkelgrün-Hero-Streifen am Apex, Foto-Backing,
weiße Info-Zone (QR + Bullets + Termine), Hellgrün-Footer-Strip an der Falz mit CTA-URL
+ Impressum. V2 ("Side-By-Side Pillar") + V3 ("Pure Type") sind Backlog (eigene Issues).

V1 nutzt das post-#24 INJECT_MAP-Idiom für `Hintergrund-Mitmachen` (`build_template` +
`build_preview`-Split, `library.inject_into_frame(target_w_mm=item.w_mm,
target_h_mm=item.h_mm)` mit LIVE Frame-Dimensionen).

## Layout — Flach (Page 1, vor dem Falzen)

```text
   <-------------------297mm----------------->
  +-------------------------------------------+   ↑      Panel A (DE, aufrecht)
  | ███████████  HERO-BAND DUNKELGRÜN  ███████|   |
  | █  L = Logo                Headline 26pt █|   | y=-3..42 (Hero-Band, full-bleed)
  | █  (38×30)                  WHITE         █|   |
  | █                           Pay-off 16pt  █|   | y=39 → Photo-Backing top
  | █                           GELB Italic   █|   |
  | ███████████████████████████████████████████|   |
  | ░░░░░░░░░░  Photo (Backing Dunkelgrün)  ░░|   |  y=39..72 (Photo + Backing)
  | ░░ Hintergrund-Mitmachen (full-bleed 9:1)░░|  |
  | ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|   |
  |                                           |   |  y=78..94 (white info zone)
  | [QR]  • Bullet 1            • Termin 1    |   |  QR(12,78,17×17), bullets(32..142),
  | 17×17 • Bullet 2            • Termin 2    |   |  termine(152..285)
  |                                           |   |  y=95..105 (Footer-Strip Hellgrün)
  | ▓▓ FOOTER-STRIP HELLGRÜN ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ |   |
  | ▓ gruene-noe.at/mitmachen     Impressum ▓ |   |
  +- - - - - - - - - - - - - - - - - - - - - -+   |
  |        ← MITTELFALZ y=105 mm →            |   |  ↕ y=105 (Falz Spot-Color, LAYER=3)
  +- - - - - - - - - - - - - - - - - - - - - -+   |
  | ▓▓ FOOTER-STRIP HELLGRÜN (rotiert 180°) ▓ |   |  y=105..115 (mirror of Panel A)
  |                                           |   |
  | • Termin 1            • Bullet 1   [QR]   |   |  y=132..148 (info zone, ROT=180)
  | • Termin 2            • Bullet 2   17×17  |   |
  |                                           |   |  y=138..171 (Photo-Backing B)
  | ░░ Photo (Hintergrund-Mitmachen Panel B) ░|   |  y=171..213 (Hero-Band B)
  | ████████ HERO-BAND DUNKELGRÜN B (180°) ███|   |
  | █     Pay-off (Italic Gelb 180°)        █ |   |
  | █     Headline 26pt White (180°)        █ |   | 210mm
  | █                              L = Logo █ |   |
  | ███████████████████████████████████████████|   |
  +-------------------------------------------+   ↓      Panel B (EN, rotiert 180°)

Mirror-Achse: y=105 (Mittelfalz). Polygons rotation_deg=0 (Rechtecke); Text/Image-
Frames rotation_deg=180 mit bbox-corner SLA-Math (x_panel_a + w, 210 − y_panel_a).
Beim Falzen kippt Panel B nach hinten und liest aufrecht für die andere Tisch-Seite.
```

## Slots (Panel A — DE, aufrecht, rotation_deg=0)

| Anname (real) | Type | SLA-Coords (x, y, w, h) | Layer | Style/Asset |
|---|---|---|---|---|
| `Hero-Band Panel A` | Polygon | (-3, -3, 303, 42) | 0 (Hintergrund) | fill=Dunkelgrün |
| `Logo Grüne (panel A)` | ImageFrame | (12, 6, 38, 30) | 1 (Bilder) | shared/logos/gruene-weiss.png |
| `Headline Panel A` | TextFrame | (55, 9, 230, 18) | 2 (Text) | tent/headline (26pt White) |
| `Pay-off Panel A` | TextFrame | (55, 27, 230, 8) | 2 (Text) | tent/payoff (16pt Italic Gelb) |
| `Photo-Backing Panel A` | Polygon | (-3, 39, 303, 33) | 0 (Hintergrund) | fill=Dunkelgrün |
| `Hintergrund-Mitmachen` | ImageFrame | (0, 39, 297, 33) | 1 (Bilder) | INJECT_MAP "kontext_infostand_szene" |
| `QR-Code (mitmachen, panel A)` | ImageFrame | (12, 78, 17, 17) | 1 (Bilder) | samples/qr-mitmachen.png (D1-konform) |
| `Body Panel A` | TextFrame | (32, 78, 110, 16) | 2 (Text) | tent/body (12pt, 2 Bullets) |
| `Termine Panel A` | TextFrame | (152, 78, 133, 16) | 2 (Text) | tent/termine (9pt, 2 Zeilen) |
| `Footer-Strip Panel A` | Polygon | (-3, 95, 303, 10) | 0 (Hintergrund) | fill=Hellgrün |
| `CTA-Footer Panel A` | TextFrame | (12, 97, 200, 6) | 2 (Text) | tent/cta-footer (11pt White Bold) |
| `Impressum (Tent)` | TextFrame | (215, 97, 80, 6) | 2 (Text) | tent/impressum (6pt White right-align) |
| `Mittelfalz (horizontal)` | Polygon | (0, 105, 297, 0) | 3 (Falz) | fill=Falz Spot-Color, DRUCKEN=0 |

## Slots (Panel B — EN, rotation_deg=180 für Text/Image, 0 für Polygons)

SLA-Math: `Text/Image at Panel-A-LOCAL (x, y, w, h) → SLA (x+w, 210-y, w, h, ROT=180)`;
`Polygon at Panel-A-LOCAL (x, y, w, h) → SLA (x, 210-y-h, w, h, ROT=0)`.

| Anname (real) | Type | SLA-Coords (x, y, w, h) | rotation_deg | Layer | Style/Asset |
|---|---|---|---|---|---|
| `Hero-Band Panel B` | Polygon | (-3, 171, 303, 42) | 0 | 0 | fill=Dunkelgrün |
| `Logo Grüne (panel B)` | ImageFrame | (50, 204, 38, 30) | 180 | 1 | shared/logos/gruene-weiss.png |
| `Headline Panel B` | TextFrame | (285, 201, 230, 18) | 180 | 2 | tent/headline |
| `Pay-off Panel B` | TextFrame | (285, 183, 230, 8) | 180 | 2 | tent/payoff |
| `Photo-Backing Panel B` | Polygon | (-3, 138, 303, 33) | 0 | 0 | fill=Dunkelgrün |
| `Hintergrund-Mitmachen Panel B` | ImageFrame | (297, 171, 297, 33) | 180 | 1 | INJECT_MAP |
| `QR-Code (mitmachen, panel B)` | ImageFrame | (29, 132, 17, 17) | 180 | 1 | samples/qr-mitmachen.png |
| `Body Panel B` | TextFrame | (142, 132, 110, 16) | 180 | 2 | tent/body |
| `Termine Panel B` | TextFrame | (285, 132, 133, 16) | 180 | 2 | tent/termine |
| `Footer-Strip Panel B` | Polygon | (-3, 105, 303, 10) | 0 | 0 | fill=Hellgrün |
| `CTA-Footer Panel B` | TextFrame | (212, 113, 200, 6) | 180 | 2 | tent/cta-footer |
| `Impressum (Tent, panel B)` | TextFrame | (295, 113, 80, 6) | 180 | 2 | tent/impressum |

Die beiden Hellgrün-Footer-Strips (Panel A 95..105 + Panel B 105..115) abutten an der
Falz und bilden ein 20 mm breites Hellgrün-Band quer über den Apex.

## ParaStyles (V1 — 6 Styles, alle MUTATIONS+ADDS aus V0)

| Name | Font | Size | Linesp | Align | Fcolor | Verwendung |
|---|---|---|---|---|---|---|
| `tent/headline` | Vollkorn Black Italic | 26 | 23.4 | 0 (left) | White | Headline auf Hero-Band |
| `tent/body` | Gotham Narrow Book | 12 | 15.6 | 0 (left) | Black | Bullets in white zone |
| `tent/termine` | Gotham Narrow Book | 9 | 11.7 | 0 (left) | Black | Termine in white zone |
| `tent/impressum` | Gotham Narrow Book | 6 | 7.8 | 2 (right) | White | Impressum in Hellgrün-Footer |
| `tent/payoff` | Vollkorn Black Italic | 16 | 14.4 | 0 (left) | Gelb | Pay-off auf Hero-Band |
| `tent/cta-footer` | Gotham Narrow Bold | 11 | 14 | 0 (left) | White | CTA-URL in Hellgrün-Footer |

`tent/cta` (V0) wurde entfernt — kein V1-Frame referenziert ihn.

## Constraints — V1 strukturelle Invarianten (Code: `build.py::CONSTRAINTS`)

22 Einträge gruppiert nach Kategorie. Code lebt in
`templates/tischschild-a5-quer/build.py::CONSTRAINTS`.

### Panel A intra-panel containment (rotation_deg=0; raw bbox math gilt)

- `inside("Logo Grüne (panel A)", "Hero-Band Panel A")` — Logo sitzt im Hero-Band.
- `inside("Headline Panel A", "Hero-Band Panel A")` — Headline sitzt im Hero-Band.
- `inside("Pay-off Panel A", "Hero-Band Panel A")` — Pay-off sitzt im Hero-Band.
- `inside("Hintergrund-Mitmachen", "Photo-Backing Panel A")` — Foto im Backing.
- `inside("CTA-Footer Panel A", "Footer-Strip Panel A")` — CTA-URL im Footer.
- `inside("Impressum (Tent)", "Footer-Strip Panel A")` — Impressum im Footer.

### Panel A intra-panel adjacency

- `aligned_below("Photo-Backing Panel A", "Hero-Band Panel A", gap_mm=0.0)` —
  Photo-Backing schließt direkt unter Hero-Band an.
- `same_x("Hero-Band Panel A", "Photo-Backing Panel A", "Footer-Strip Panel A")` —
  Alle drei full-bleed Polygons teilen die linke Kante (x=-3).
- `same_y("Body Panel A", "Termine Panel A")` — Bullets + Termine teilen die Top-Y-Achse.
- `same_size("Body Panel A", "Termine Panel A", axis="h")` — gleiche Höhe.

### Panel B intra-panel (nur same-rotation-state Paare)

- `same_y("Body Panel B", "Termine Panel B")` — beide ROT=180.
- `same_size("Body Panel B", "Termine Panel B", axis="h")`.

(`inside` cross-panel oder zwischen rotated/unrotated Frames ist NICHT erlaubt — raw
bbox math fails on rotation mismatch. Locked decision #4 in RESEARCH.md.)

### Cross-panel Spiegelung an der Apex-Achse y=105 (Polygons, beide ROT=0)

- `mirrored_y("Hero-Band Panel A", "Hero-Band Panel B", axis_mm=105.0)`.
- `mirrored_y("Photo-Backing Panel A", "Photo-Backing Panel B", axis_mm=105.0)`.
- `mirrored_y("Footer-Strip Panel A", "Footer-Strip Panel B", axis_mm=105.0)`.
- `same_size(<3 Polygon-Paare>)` — gleiche Größe pro Paar.

### Cross-panel Style-Konsistenz (rotation-invariant)

- `same_style` für Headline / Pay-off / Body / Termine / CTA-Footer / Impressum
  zwischen Panel A und Panel B. Style-Resolver matcht auf den ParaStyle-Namen, der
  rotation-unabhängig ist.

## Brand overrides (post-V1; 4 KEPT)

| ID | Reason (2026-05-09) |
|---|---|
| `brand:line_spacing_0.9` | Body 1.3× und Termine 1.3× und CTA-Footer 1.27× linesp ratios sind intentional Quickguide-body convention; tent/headline at 26/23.4=0.9 IS conformant. |
| `brand:visual_adjacency_drift` | V1 CONSTRAINTS captures Panel-A and cross-panel adjacencies. Combinatorial intra-Panel-B warnings on rotated text/polygon pairs deferred. |
| `brand:band_consistency` | Tent-card has no body-pool model; rule no-ops by design. |
| `brand:image_fills_frame` | Logo asset gruene-weiss.png (3.5:1 wordmark) intentionally letterboxed in 38×30 mm V1 logo frame (1.27:1) — wordmark renders 38×10.86 mm centered. Photo INJECT_MAP fills exactly via LIVE frame dims. Restoring would require commissioning bund-weiss.png 1:1 OR resizing logo frame; both deferred. |

V0-Overrides REMOVED in V1: `brand:logo_size_3M` (38mm passes 3M ± tol),
`brand:image_text_overlap` (V1 text fully inside polygons).

## Falz-Mechanik

Die Karte wird **horizontal in der Mitte** (y=105 mm) gefalzt. Panel A oben (DE)
liest normal, Panel B unten (EN) ist um 180° gedreht — beim Falzen kippt Panel B
nach hinten und die Schrift steht korrekt aufrecht für eine Person, die das
Tent von der anderen Seite sieht.

Die Falz-Linie liegt auf einem eigenen **Falz-Layer** (`LAYER=3`) mit der
Spot-Color „Falz" (CMYK 100/0/0/0). Sie erscheint im Druck nicht (Layer-DRUCKEN=0),
aber die Druckerei sieht den Pfad als Falz-Anweisung. Die `test_falz_layer_integrity`-
Smoke-Assertion stellt sicher, dass NUR `Mittelfalz (horizontal)` auf LAYER=3 liegt
(keine V1-Polygons leaken).

## Druck-Empfehlung

- **Trim:** 297 × 210 mm
- **Bleed:** 3 mm allseitig
- **Fold:** y = 105 mm (mittig horizontal)
- **Papier:** Karton 250–300 g/m² (Steifigkeit für Frei-Stand)
- **Druck:** Digital oder Offset (≥ 100)
- **DPI:** 300 für eingebettete Bilder
