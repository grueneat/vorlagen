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
