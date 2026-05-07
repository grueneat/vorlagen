# Wahlaufruf-Postkarte A6 quer

Zweiseitige Wahlkampf-Postkarte A6 quer (148 × 105 mm) für die Endphase einer Wahl.
Vorderseite Wahlkreuz-Hero, Rückseite 2×2 Info-Grid.

## Wann verwenden?

- Letzte 2–3 Wochen vor einer Wahl. Postwurf, Infostand, Tür-Kampagne.
- Lese-Distanz Hand-Distanz ~30–40 cm.
- Nicht für Themen-Argumentation — dafür gibt es das Themen-Plakat A3.

## Was anpassen?

| Anname | Inhalt |
|---|---|
| `Headline-Wahlaufruf` | „Wähle Grün am [Datum]" — Datum anpassen |
| `Cell 1 / 2 / 3 / 4 — Headline` | Kurze Frage je Zelle |
| `Cell 1 / 2 / 3 / 4 — Body` | 1–2 Sätze Antwort |
| `Impressum` | Mediengesetz-§24-Block |

Spec: [`templates/_specs/wahlaufruf-postkarte-a6-quer.md`](../_specs/wahlaufruf-postkarte-a6-quer.md).

## Wahlkreuz-Symbol — D12-Pflicht

Der Wahlkreuz-Asset (`shared/assets/wahlkreuz.png`) ist ein gelbes Kreuz im weißen
Kreis. Er **muss** auf farbigem Brand-Hintergrund (Dunkelgrün, Hellgrün, oder
Magenta) stehen. Diese Vorlage nutzt **Dunkelgrün** als Vollbild-Hintergrund.

**Wenn du den Hintergrund änderst:** keinesfalls auf Weiß oder Gelb setzen — der
weiße Kreis bzw. das gelbe Kreuz verschwindet.

## Messaging-Legality (NRWO §53)

Der Default-Headline „Wähle Grün am 23. Mai" ist eine Wahlempfehlung. Bei der
Anpassung **nicht** durch direktive Wahlanleitung ersetzen („Mach dein Kreuz bei
den Grünen"). Erlaubt: „Wähle Grün am [Datum]", „Am [Datum] zur Wahl", „Ich wähle
Grün".

## Build

```bash
python3 templates/wahlaufruf-postkarte-a6-quer/build.py
# → templates/wahlaufruf-postkarte-a6-quer/template.sla
```

## Druck-Empfehlung

- **Bleed:** 3 mm
- **Papier:** Bilderdruck matt 300 g/m² (Postkarten-Standard)
- **Druck:** Offset (≥ 500) oder Digital (< 500)
- **DPI:** 300 für eingebettete Bilder
- **CMYK only**

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.
