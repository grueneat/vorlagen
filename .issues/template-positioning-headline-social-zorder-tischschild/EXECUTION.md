# Execution — template-positioning-headline-social-zorder-tischschild

## Tasks

- [x] **Cover-Headlines zentrieren** — `flyer-a6-hochformat-gruenes-cover`,
  `flyer-a6-hochformat-quadrat-im-bild`, `flyer-a6-querformat-quadrat-im-bild`.
  Die `headline_stack`-Frames waren bereits auf Seiten- bzw. Kasten-Mitte
  zentriert, der Text aber links-bündig (`align`-Default `"0"`) → wirkte „zu weit
  links". Fix: `align='1'` an den drei Cover-Aufrufen. `headline_stack` wendet
  ALIGN jetzt auf jede Zeile mehrzeiliger Stacks an (am `<trail>`, da
  Single-Line-Frames die Paragraph-Ausrichtung dort tragen); links (`"0"`)
  bleibt erststeilig → bestehende Templates byte-stabil.

- [x] **Falzflyer-Social-Icons (linke Spalte) fixen** —
  `falzflyer-z-falz-6-seitig-gruenes-cover-2` und `-portraet`. Die drei Icons
  (Facebook/Instagram/TikTok) waren als eingebetteter Composite-Strip
  (`inline_image_data`) hinterlegt, der in Scribus 1.6.x unsichtbar rendert. Auf
  Einzel-Crop-Referenzen (`image=` + `scale_type=0`) umgestellt — wie bei den
  bereits gefixten `gruenes-cover`/`zweigeteiltes-cover`. Crops nach
  `shared/assets/<template>/crops/social/` kopiert.

- [x] **Gelbe Akzente vor den Text** — 82 dekorative `fill='Gelb'`-Shapes
  (Unterstriche/Kreise/Squiggles) über alle Flyer/Falzflyer von Layer 0 auf die
  oberste Druck-Ebene (Text=2) gehoben. Liegen jetzt vor dem Text und sind in
  Scribus auswählbar.

- [x] **Tischschild entfernen** — `tischschild-a5-quer` komplett entfernt:
  Template-Verzeichnis, `_specs`, Smoke-/Geometrie-Tests, Galerie-Eintrag
  (Content-Collection + `PRIMARY_ORDER`), `visual_review.py`-Listen und die
  gerenderten Vorschau-Artefakte.

- [x] **Neu gerendert + Gates** — `template.sla`, Vorschau-PDFs/PNGs, `meta.yml`
  und die Bundesland-Impressum-Downloads aller 12 geänderten Templates neu
  gerendert/abgeleitet.

## Verification

- `sop_lint`, `lint_inject_consistency`, `check_no_absolute_paths_in_sla`: OK
- `bin/check-stale-previews`: OK (Vorschauen ↔ template.sla konsistent)
- `structural_check --all`: 0 errors (nur vorbestehende zeitung-Warnungen)
- `out_of_bounds_audit --all`: exit 0 (nur vorbestehende Vollflächen-WARNs)
- `pytest tools/sla_lib/tests/`: 801 passed, 7 skipped
- `pytest tests/unit/`: 738 passed, 9 skipped
- Visuell bestätigt: zentrierte Headlines, sichtbare linke Social-Icons,
  gelbe Akzente vor dem Text.

## Notes / Follow-ups

- Auf dem grünen Cover liegt der gelbe Ring nun auch vor dem magenta „Störer"
  (Nebeneffekt der Layer-Anhebung; Layer trennt Text/Grafik nicht). Bei Bedarf
  per Einzel-Umsortierung hinter den Störer legbar.
- Weitere konkret „falsch positionierte" gelbe Akzente bräuchten Template+Seite,
  da das Fidelity-System sie sonst als baseline-treu behandelt.
- `site/public/templates/*/template.sla` bleiben (repo-weit) untracked; die
  tatsächlichen Downloads sind die committeten Impressum-Varianten.
