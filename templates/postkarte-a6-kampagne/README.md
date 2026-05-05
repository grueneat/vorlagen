# Kampagnen-Postkarte A6

Zweiseitige A6-Postkarte für Kampagnen, Petitionen, Events.

## So nutzt du die Vorlage

1. `template.sla` in Scribus öffnen.
2. Pinke Beschriftungen am oberen Seitenrand zeigen "Vorderseite" / "Rückseite" — werden im PDF nicht gedruckt (Hilfslinien-Layer).
3. Frames sind beschriftet: Headline, Störer-Text, Erklärtext, URL, Impressum, etc. Klick auf einen Frame zeigt seinen Namen rechts unten in den Object Properties.
4. Inhalte ersetzen, Logo bei Bedarf einsetzen, QR-Code unter `[QR-Code (wird aus URL generiert)]` als Bild platzieren.
5. PDF exportieren — fertig.

## Slots

Siehe `meta.yml`. Beispiel:

| Slot | ANNAME (im Scribus sichtbar) | Hinweis |
|---|---|---|
| `headline` | Headline 4-zeilig (Brand-Wechselfarbe) | 4 Zeilen, alternierend Weiß/Gelb |
| `stoerer` | Störer-Text 3-zeilig | 3 Zeilen im Magenta-Kreis |
| `body` | Erklärtext Rückseite | Mehrzeiliger Erklärtext |
| `url` | Kampagnen-URL | unter dem QR-Code |
| `impressum` | Impressum (1-zeilig) | gesetzlich vorgeschrieben |
| `logo` | Logo Grüne (weiss, zentriert) | Bild aus shared/logos/ |

## Vorlagen-Generierung

`template.sla` ist aus `build.py` über die DSL erzeugt:

```bash
python3 templates/postkarte-a6-kampagne/build.py
```
