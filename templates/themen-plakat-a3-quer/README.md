# Themen-Plakat A3 quer

Argumentations-Plakat A3 quer (420 × 297 mm) für Sachthemen-Aufhänge in
Gemeindeämtern, Lokalen und auf Infotafeln.

## Wann verwenden?

- Sachthema außerhalb des Wahlkampfs (z.B. „Klimaschutz ist Wirtschaftspolitik",
  „Was unsere Heizungsförderung leistet").
- Lese-Distanz ~50 cm – 1.5 m.
- Soll überzeugen, nicht aufrufen — daher kein Wahlkreuz, kein Stoerer.

## Was anpassen?

In Scribus öffnen → die folgenden Frame-Annames anklicken und Text/Bild
ersetzen:

| Anname | Inhalt |
|---|---|
| `Headline These` | Hauptthese, 1 Zeile |
| `Sub-Headline` | Kontext: Region + Datum |
| `Beleg 1 / 2 / 3 — Headline` | Kennzahl-Anker je Spalte |
| `Beleg 1 / 2 / 3 — Body` | 3–5 Sätze Begründung |
| `Quelle` | Wissenschaftliche / behördliche Quelle |
| `Impressum` | Mediengesetz-§24-Block |
| `Logo Grüne (top-left)` | (optional) Logo, sonst leer |

Spec: [`templates/_specs/themen-plakat-a3-quer.md`](../_specs/themen-plakat-a3-quer.md).

## Build

```bash
python3 templates/themen-plakat-a3-quer/build.py
# → templates/themen-plakat-a3-quer/template.sla
```

## Druck-Empfehlung

- **Bleed:** 3 mm allseitig
- **Papier:** Bilderdruck matt 170 g/m² oder Plakatpapier blueback 135 g/m²
- **Druck:** Offset (≥ 100 Stück) oder Großformat-Digital (< 100)
- **DPI:** 300 für eingebettete Bilder
- **CMYK only**, ICC-Profil PSO Uncoated ISO12647 (ECI)

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.
Inhalte (Texte, Belege, Quellen) sind Verantwortung der Endnutzer:innen.
