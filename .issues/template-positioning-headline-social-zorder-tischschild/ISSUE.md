---
id: mvsaj
title: 'Vorlagen-Positionierung: Headlines zentrieren, Falzflyer-Social-Icons, gelbe
  Akzente vor den Text, Tischschild entfernen'
status: done
priority: medium
labels:
- templates
- layout
---

Mehrere Positionierungs- und CI-Korrekturen an den Scribus-Vorlagen (gemeldet im Review):

- Cover-Headline "Ich bin eine Headline" sitzt zu weit links bei flyer-a6-hochformat-gruenes-cover sowie hochformat- und querformat-quadrat-im-bild.
- Social-Media-Icons der linken Spalte (3 Stück) in manchen Falzflyern weiterhin falsch; Fix der anderen Falzflyer ueberall nachziehen.
- Gelbe Unterstriche/Kreise teils falsch positioniert und liegen hinter dem Text (in Scribus nicht auswaehlbar) -> vor den Text legen.
- Tischschild passt nicht ins aktuelle CI -> komplett aus den Vorlagen entfernen.

## Acceptance Criteria
- [x] Cover-Headlines der drei Flyer mittig zum zentrierten Kontext (Subheadline/Logo bzw. gruener Kasten)
- [x] Linke Social-Spalte (Facebook/Instagram/TikTok) in allen Falzflyern korrekt sichtbar
- [x] Gelbe Akzente liegen vor dem Text und sind in Scribus auswaehlbar
- [x] tischschild-a5-quer vollstaendig entfernt (Template, Tests, Galerie, Vorschauen)
