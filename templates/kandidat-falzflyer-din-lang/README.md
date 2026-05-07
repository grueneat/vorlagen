# Kandidat-Falzflyer DIN-lang

3-fach gefalzter A4-quer-Kandidaten-Flyer (297 × 210 mm) für Personalisierung
im Wahlkampf.

## Wann verwenden?

- Bezirks-/Kommunal-/Landtagswahlkampf, personalisiert auf eine Kandidatin /
  einen Kandidaten.
- Verteilung: Tür-Kampagne, Infostand, Postwurf, Veranstaltungs-Auslage.
- Lese-Distanz Hand ~30–40 cm.

## Falz-Mechanik

**Zickzackfalz (Z-fold/accordion)**: 6 Panele à 99 mm.

```
GESCHLOSSEN:        Nur Panel 1 (Cover) sichtbar.
ERSTES AUFKLAPPEN:  Panel 1 + Panel 2 nebeneinander.
VOLLES AUFKLAPPEN:  Alle 3 Front-Panele + Back-Panele 4-6 sichtbar.
ZUFALTEN:           Panel 3 (Closer mit Wahlkreuz) ist die letzte Botschaft.
```

Falz-Linien bei x=99 mm und x=198 mm auf einem eigenen **Falz-Layer** mit der
Spot-Color „Falz" (CMYK 100/0/0/0). Druckerei sieht die Falz-Anweisung; im
finalen Druck nicht sichtbar.

## Was anpassen?

### Front

| Anname | Inhalt |
|---|---|
| `P1 Kandidat-Portrait` | Foto (vertikal, 87×105 mm) |
| `P1 Kandidat-Name` | Vor- und Nachname |
| `P1 Slogan` | 2 Zeilen Slogan |
| `P2 Teaser-Headline` | „Was ich für [Region] will" o.ä. |
| `P2 Teaser-Body` | 4–6 Sätze Vorstellung |
| `P3 Closer-Headline` | „Wähle Grün am [Datum]" |
| `P3 Datum-Akzent` | Volles Datum als Gelb-Akzent |
| `P3 URL` | Persönliche oder Bezirks-URL |

### Back

| Anname | Inhalt |
|---|---|
| `P4 Thema 1 — Headline/Body` | Thema 1 (z.B. Klima) |
| `P4 Thema 2 — Headline/Body` | Thema 2 (z.B. Wohnen) |
| `P5 Thema 3 — Headline/Body` | Thema 3 (z.B. Bildung) |
| `P5 Thema 4 — Headline/Body` | Thema 4 (z.B. Wirtschaft) |
| `P6 Kontakt-Headline/Adresse/Email-Tel` | Kontakt-Modul |
| `P6 QR-Code` | QR zur Kandidaten-Webseite |
| `P6 Impressum` | Mediengesetz §24 |

Spec: [`templates/_specs/kandidat-falzflyer-din-lang.md`](../_specs/kandidat-falzflyer-din-lang.md).

## Wahlkreuz auf Dunkelgrün-Closer

Panel 3 ist Vollbild-Dunkelgrün — der Wahlkreuz integriert sich visuell ins
Closer-Panel. D12-Pflicht erfüllt: Wahlkreuz auf farbigem Brand-Hintergrund.

**Wichtig bei Anpassung:** Panel 3 NIEMALS auf Weiß ändern (Wahlkreuz-Kreis
verschwindet) und NIEMALS auf Gelb (Wahlkreuz-Kreuz verschwindet).

## Build

```bash
python3 templates/kandidat-falzflyer-din-lang/build.py
# → templates/kandidat-falzflyer-din-lang/template.sla
```

## Druck-Empfehlung

- **Trim:** 297 × 210 mm
- **Bleed:** 3 mm allseitig
- **Falz:** Zickzackfalz, je 99 mm (x=99 + x=198)
- **Papier:** Bilderdruck matt 130–170 g/m²
- **Druck:** Offset (≥ 500) oder Digital (< 500)
- **Falzung:** maschinell empfohlen

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.
