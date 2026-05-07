# Wahltag-Türanhänger

Vertikaler Türanhänger (105 × 250 mm) mit 35-mm-Loch-Stanzform für die
Tür-Kampagne am Wahltag-Vorabend.

## Wann verwenden?

- Tür-Kampagne am Tag vor / am Wahltag.
- Lese-Distanz Vorbeigehen ~30 cm.
- Personalisiert auf eine Kandidatin / einen Kandidaten.

## Was anpassen?

| Anname | Inhalt |
|---|---|
| `Headline-Wahltag` | 2-zeilige Hauptbotschaft |
| `Sub-Headline` | „Wähle Grün." (1 Zeile) |
| `Bullet-Liste` | 3 Stichpunkte zur Botschaft |
| `Kandidat-Portrait` | Foto der Kandidatin/des Kandidaten |
| `Kandidat-Name` | Vor- und Nachname |
| `Kandidat-Position` | Funktion + Region |
| `Kontakt-URL` | Persönliche oder Bezirks-URL |
| `Kontakt-Info` | E-Mail + Telefon |
| `Impressum` / `Impressum (back)` | Mediengesetz §24 |

Spec: [`templates/_specs/wahltag-tueranhaenger.md`](../_specs/wahltag-tueranhaenger.md).

## Stanzkontur (wichtig für die Druckerei)

Der Türanhänger hat eine **Stanzkontur** (Außenrahmen + 35-mm-Loch oben mittig).
Die Stanzkontur liegt auf einem eigenen Layer namens „Stanzkontur" mit der Spot-
Color „Stanzkontur" (CMYK 0/100/0/0). Im finalen Druck erscheint dieser Pfad
**nicht** (Layer hat `printable=False`), aber die Druckerei sieht die
Schneid-Anweisung im PDF-Export.

**Druckerei-Variante:** Falls die Druckerei „CutContour" als Spot-Color-Name
fordert (Pantone-Druckereien international), in der SLA in Scribus die Spot-
Color umbenennen — auf Klima-/Bezirks-Druckereien in Österreich heißt sie
„Stanzkontur" (Default).

## Wahlkreuz auf Hellgrün-Band

Diese Vorlage nutzt **Hellgrün** als Hintergrund hinter dem Wahlkreuz (D12-
Pflicht: nicht Weiß, nicht Gelb). Der Hellgrün-Streifen integriert das
Wahlkreuz-Symbol visuell in den oberen Inhalts-Bereich.

## Build

```bash
python3 templates/wahltag-tueranhaenger/build.py
# → templates/wahltag-tueranhaenger/template.sla
```

## Druck-Empfehlung

- **Trim:** 105 × 250 mm
- **Bleed:** 2 mm (knapper als 3 mm wegen Stanze)
- **Loch:** 35 mm Ø, zentriert horizontal, 25 mm vom Top
- **Papier:** Karton 250–300 g/m² (Steifigkeit für Türklinken-Aufhängung)
- **Druck:** Offset oder Digital + Stanze separat
- **DPI:** 300 für eingebettete Bilder
- **CMYK only**, Stanzkontur als Spot-Color

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.
