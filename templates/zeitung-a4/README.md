# Grüne Zeitung A4 — Skelett-Vorlage

Mehrseitige Zeitungsvorlage mit allen typischen Layout-Varianten in **einer einzigen SLA-Datei**.

## So nutzt du die Vorlage

1. `template.sla` in Scribus öffnen.
2. Im **Page-Panel** (Fenster → Seitenbedienpanel) siehst du eine pinke Beschriftung pro Beispielseite — z.B. "BEISPIELSEITE — Beispiel: Hauptartikel 3-spaltig" am oberen Seitenrand.
3. **Beispielseite duplizieren** (Rechtsklick im Page-Panel → "Seite kopieren" → an gewünschter Position einfügen).
4. **Inhalte ersetzen** — die Frames sind beschriftet (Object Properties → ANNAME), z.B. "Headline 4-zeilig (Brand-Wechselfarbe)" oder "Bildunterschrift Foto-Doppelseite". Klick auf einen Frame zeigt seinen Namen rechts unten.
5. **Beispielseite-Beschriftungen löschen** — die pinken Hinweise oben (Layer "Hilfslinien") werden im PDF-Export sowieso nicht gedruckt; wer mag, blendet den Layer aus oder löscht die Frames.
6. **Nicht benötigte Beispielseiten löschen** — wenn du nur 4 Seiten brauchst, wirf die anderen weg.
7. Reihenfolge per Drag-and-Drop im Page-Panel anpassen.

## Master-Pages

Über **Bearbeiten → Musterseiten** sind diese verfügbar:

| Name | Verwendung |
|---|---|
| `Normal` | Default — leere Seite |
| `rechts-3col` | Rechte Innenseite mit 3-Spalten-Raster |
| `links-3col` | Linke Innenseite mit 3-Spalten-Raster |
| `titelseite` | Cover-Layout (Hero-Bereich oben) |
| `foto-spread` | Vollbild-Fotoseite ohne Hilfsraster |
| `impressum-master` | Rückseite mit großzügigem Impressum-Bereich |

Master per Page-Panel auf Seiten anwenden: Rechtsklick auf Seite → "Musterseite anwenden".

## Beispielseiten in dieser Vorlage

1. **Titelseite (Cover)** — Hero-Headline, Masthead, Störer, Inhalts-Teaser
2. **Hauptartikel 3-spaltig** — Großer Artikel mit Bild und 3-Spalten-Body
3. **Drei kleine Artikel** — Themenseite mit drei nebeneinanderstehenden Teasern
4. **Foto-Doppelseite (links)** — Vollbild-Foto mit Bildunterschrift-Block
5. **Foto-Doppelseite (rechts)** — Fortsetzung mit Pull-Quote
6. **Veranstaltungskalender** — Liste von 5 Events mit Datum/Ort
7. **Interview-Layout** — Portrait + Q&A-Block
8. **Kommentar mit Pull-Quote** — Genre-Markup, Pull-Quote, 2-Spalten-Body
9. **Impressum + Postvermerk** — Rückseite

## Vorlagen-Generierung (für Maintainer:innen)

`template.sla` wird aus `build.py` über die DSL erzeugt:

```bash
python3 templates/zeitung-a4/build.py
```

Wer das Layout strukturell ändern will (z.B. neue Beispielseite, Master-Page-Anpassung) editiert `build.py` und re-generiert. Wer nur Inhalte ändert oder eine konkrete Ausgabe baut, arbeitet direkt in Scribus an der `template.sla`.

## Bekannte Abweichungen vom Original-SLA

`gruene-zeitung-vorlage-original.sla` enthält zwei Bildrahmen, die der
Scribus-Autor versehentlich um 210 mm nach rechts (auf den Off-Page-
Scratch-Canvas) plaziert hat — sie rendern im Original-PDF nichts
Sichtbares (verifiziert via `pdfimages -list`):

- `P9 Spread` (build.py:1802, war `x_mm=210` auf `page9`) → korrigiert
  auf `x_mm=0` auf derselben Seite. `anname` bleibt erhalten, damit
  `INJECT_MAP` und `CONSTRAINTS` weiter aufgelöst werden. Issue #16.
- Unbenannter Vollseiten-Dunkelgrün-Rahmen (build.py:2061, war
  `page11.add(...)` mit `x_mm=210`) → verschoben zu `page12.add(...)`
  mit `x_mm=0` (gedruckte Seite 13, dem ursprünglich gemeinten Ziel).
  Issue #16.

Daher weicht `template.sla` an diesen zwei Stellen bewusst vom
Original-SLA ab. Der Round-Trip-Check `tools/sla_diff.py --strict`
ist für diese Vorlage entsprechend deaktiviert
(`meta.yml::sla_diff_strict: false`); `tools/render_pipeline.py`
überspringt den Strict-Diff für Templates mit diesem Flag.

Eine dritte, davon unabhängige Überfüllung — der gedrehte
Cover-Polygon `u2950` (build.py:246-256, ~4.17 mm Bottom-Overshoot) —
bleibt vorerst durch den `brand_overrides[brand:inside_page]`-Eintrag
abgedeckt und wird in GH #39 separat behoben.

## Brand

Alle Farben und Schriften referenzieren `shared/ci.yml`. Direkt-Edits an Stilen in der SLA werden vom CI-Validator (`tools/check_ci.py`) als Drift gemeldet.

## LANGUAGE-Vererbung auf STYLE-Ebene

Die ursprüngliche Zeitungsvorlage setzt `LANGUAGE="de"` nur auf 13 von 23 Paragraphenstilen. Die anderen 10 Stile (z.B. `Fließtext`, `Fließtext weiß`, `Fließtext in grünem Kasten`) erben über `PARENT` oder verlassen sich auf den Dokument-Default (DEFLANG="de"). Der DSL-Konverter (`tools/sla_to_dsl.py`) übernimmt dieses Muster verbatim — `ParaStyle.language` ist `None` für die 10 Stile, die das Original nicht setzt.

Die Hyphenation in den `Fließtext*`-Spalten (vgl. Seite 3/4 der gerenderten PDF) ist im DSL-Output identisch mit der Originalvorlage; das Auslassen von `LANGUAGE` führt nicht zu Drift, weil der Default greift. Sollte sich das in einem zukünftigen Scribus-Upgrade ändern, muss der Konverter auf "alle 23 Stile auf `language='de'` setzen" umgestellt werden.
