---
id: '42'
title: 'Freie Gotham-Ersatzschriften: Recherche und Schriften-Vergleichsseite'
status: open
priority: high
labels:
- templates
- site
- fonts
source: github
source_id: 122
source_url: https://github.com/GrueneAT/vorlagen/issues/122
---

## Kontext / Problem

Gotham (im Repo „Gotham Narrow Book/Bold/…") ist kommerziell lizenziert und darf
nicht frei mit den Vorlagen weitergegeben werden. Damit die Templates frei
teilbar sind, brauchen wir eine ausreichend ähnliche, **frei (auch kommerziell)
nutzbare** Ersatzschrift.

## Ziel

1. **Exhaustive Recherche** nach freien, Gotham-ähnlichen Schriften (geometrische
   Grotesk; auch eine schmale Variante passend zu „Gotham Narrow"), die für jeden
   Einsatzzweck frei lizenziert sind (z. B. SIL OFL — kommerzielle Nutzung und
   Einbettung erlaubt).
2. **Genau 5 Kandidaten** auswählen.
3. **Separate Website-Seite**, von der Startseite verlinkt — wie „Galerie" und
   „Experimente" —, die die Schriften direkt gegenüberstellt.
4. Den Flyer **„Flyer A6 Hochformat – Grünes Cover"**
   (`flyer-a6-hochformat-gruenes-cover`) mit jeder der 5 Schriften rendern —
   als **PDF** und mit derselben **Vorschau-/Lightbox-Funktion** wie die Galerie.

## Darstellung der Vergleichsseite

- Die Galerie-Logik ist hier anders: jede **Zeile** entspricht **einer Seite**
  des Flyers.
- Pro Zeile stehen **5 Vorschaubilder** nebeneinander = dieselbe Seite in 5
  Font-Varianten.
- Beim Öffnen einer Seite kann man **zwischen den Font-Versionen derselben
  Seite umschalten**.
- Zu **jeder Schrift** gibt es eine kurze Zusammenfassung **auf Deutsch**:
  warum sie Gotham ähnlich ist, ihre Vor- und Nachteile im Vergleich, worin sie
  sich von den anderen unterscheidet und wofür sie sich am besten eignet.

## Umfang (diese Iteration)

- **Nur** Recherche + Vergleichsseite. Der tatsächliche Austausch von Gotham in
  allen Produktions-Templates ist ein **Folge-Issue**, nachdem auf Basis dieser
  Seite eine Schrift gewählt wurde.

## Acceptance Criteria

- [ ] Exhaustive Recherche zu freien Gotham-Alternativen ist dokumentiert; die
      Lizenz jeder Schrift ist explizit geprüft (kommerzielle Nutzung +
      Einbettung erlaubt).
- [ ] Genau 5 freie Schriften sind ausgewählt und begründet (inkl. einer zu
      „Gotham Narrow" passenden schmalen Option).
- [ ] Die Schriftdateien sind frei lizenziert und im Repo eingebunden.
- [ ] Eine eigene Seite ist von der Startseite verlinkt (neben Galerie/
      Experimente) und stellt die Schriften direkt gegenüber.
- [ ] Zu jeder Schrift gibt es eine deutschsprachige Kurz-Zusammenfassung
      (Ähnlichkeit zu Gotham, Vor-/Nachteile, Unterschiede, Einsatzempfehlung).
- [ ] „Flyer A6 Hochformat – Grünes Cover" ist in allen 5 Font-Varianten als
      PDF gerendert.
- [ ] Vorschau-/Lightbox-Funktion wie in der Galerie ist verfügbar.
- [ ] Pro Zeile = eine Flyer-Seite mit 5 Vorschaubildern (je eine Font-Variante).
- [ ] Beim Öffnen einer Seite kann zwischen den Font-Versionen derselben Seite
      umgeschaltet werden.
- [ ] Keine Änderung an den Produktions-Templates (Gotham-Austausch = Folge-Issue).
