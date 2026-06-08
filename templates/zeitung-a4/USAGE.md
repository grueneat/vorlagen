# So nutzt du die Zeitungs-Vorlage

Die Vorlage ist eine mehrseitige A4-Zeitung mit fertigen Beispielseiten für
alle typischen Layouts — Titelseite, Artikel, Foto-Doppelseite, Interview,
Veranstaltungskalender, Impressum. Du baust deine Ausgabe, indem du die
passenden Beispielseiten übernimmst und die Inhalte ersetzt.

## Schritt für Schritt

1. **Vorlage öffnen** — `template.sla` mit [Scribus](https://www.scribus.net)
   öffnen (kostenlos für Windows, macOS und Linux). Die oben verlinkten
   Schriften vorher installieren.
2. **Beispielseiten ansehen** — im Seitenbedienpanel (*Fenster →
   Seitenbedienpanel*) trägt jede Beispielseite oben eine pinke Beschriftung,
   z. B. „Beispiel: Hauptartikel 3-spaltig". So erkennst du, welche Seite welches
   Layout zeigt.
3. **Seiten übernehmen** — die Beispielseiten, die du brauchst, im
   Seitenbedienpanel duplizieren (Rechtsklick → *Seite kopieren*) und an die
   gewünschte Position einfügen. Nicht benötigte Seiten löschen.
4. **Inhalte ersetzen** — Texte überschreiben, Fotos austauschen. Klick auf
   einen Rahmen zeigt unten rechts seinen Namen (z. B. „Headline 4-zeilig" oder
   „Bildunterschrift") — so findest du, was wofür gedacht ist.
5. **Reihenfolge anpassen** — Seiten per Drag-and-Drop im Seitenbedienpanel
   sortieren.
6. **Pinke Hinweise entfernen** — die Beispielseiten-Beschriftungen liegen auf
   dem Layer „Hilfslinien" und werden im PDF ohnehin nicht gedruckt; wer mag,
   blendet den Layer aus oder löscht die Hinweise.
7. **Impressum prüfen** — der Impressums-Block ist gesetzlich vorgeschrieben.
   Angaben ergänzen, nicht löschen.
8. **Als PDF exportieren** — *Datei → Exportieren → Als PDF speichern*. Fertig
   für die Druckerei.

## Verfügbare Beispielseiten

1. **Titelseite** — Hero-Headline, Masthead, Störer, Inhalts-Teaser
2. **Hauptartikel 3-spaltig** — großer Artikel mit Bild und 3-Spalten-Text
3. **Drei kleine Artikel** — Themenseite mit drei Teasern nebeneinander
4. **Foto-Doppelseite (links)** — Vollbild-Foto mit Bildunterschrift
5. **Foto-Doppelseite (rechts)** — Fortsetzung mit Pull-Quote
6. **Veranstaltungskalender** — Liste von Events mit Datum und Ort
7. **Interview-Layout** — Porträt plus Frage-Antwort-Block
8. **Kommentar mit Pull-Quote** — zweispaltig mit hervorgehobenem Zitat
9. **Impressum + Postvermerk** — Rückseite

## Eigene Seiten anlegen

Brauchst du eine leere Seite in einem bestimmten Raster, kannst du beim Anlegen
einer Seite eine Musterseite (*Bearbeiten → Musterseiten*) wählen:

| Musterseite | Verwendung |
|---|---|
| `titelseite` | Cover-Layout mit Hero-Bereich oben |
| `rechts-3col` | rechte Innenseite, 3-Spalten-Raster |
| `links-3col` | linke Innenseite, 3-Spalten-Raster |
| `foto-spread` | Vollbild-Fotoseite |
| `impressum-master` | Rückseite mit Impressum-Bereich |

Musterseite zuweisen: im Seitenbedienpanel Rechtsklick auf die Seite →
*Musterseite anwenden*.
