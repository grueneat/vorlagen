---
id: '11'
title: Demo-Bilder via Codex + QR-Codes für 5 neue Templates
status: open
priority: medium
labels:
- templates
- demo-content
source: github
source_id: 21
source_url: https://github.com/GrueneAT/vorlagen/issues/21
---

## Kontext

PR #20 (Issue #10) hat fünf neue Templates und das Demo-Image-Framework geliefert
(`tools/codex_image_gen.py`, per-template `samples/manifest.yml`, `<slug>-preview.sla`-
Konvention). Während der Implementierung wurde Codex-DALL·E-Generierung **nicht aktiv
ausgeführt** — die Templates sind mit leeren Bild-Slots committed, und die
Galerie-Previews zeigen Platzhalter. Außerdem fehlen funktionierende QR-Codes für
Templates, die einen QR-Slot vorsehen.

Dieses Issue schließt diese Lücke: zwei klar getrennte Bild-Familien für die fünf neuen
Templates erzeugen, committen, in den `<slug>-preview.sla`-Build einhängen und
Galerie-Previews neu rendern.

## Scope — zwei separate Bild-Pipelines

### A — Kandidat-Portraits + Themen-Bilder via Codex DALL·E

Codex unterstützt jetzt DALL·E-Image-Generation ([openai/codex#8758](https://github.com/openai/codex/issues/8758)).
`tools/codex_image_gen.py` ist bereits gebaut und für genau diesen Zweck vorgesehen
(D11 aus Issue #10). Pipeline:

- Pro Template, das Bild-Slots hat, ein `templates/<slug>/samples/manifest.yml` mit
  Prompts und Output-Dateinamen pflegen oder anlegen.
- `python3 tools/codex_image_gen.py templates/<slug>` einmal laufen lassen
  → Demo-Bilder werden in `templates/<slug>/samples/<image>.jpg` geschrieben.
- Bilder committen (sind permanente Repo-Bytes).
- `<slug>-preview.sla`-Build referenziert diese Bilder (Build-Logik existiert bereits).

**Templates mit Portrait/Foto-Bedarf:**
- `kandidat-falzflyer-din-lang` — Kandidat-Portrait (Cover-Panel, ~60×80mm hochformat),
  3 Themen-Fotos für mittlere Spread-Panele (Klimaschutz, Soziales, Bildung — je
  ~85×60mm querformat)
- `themen-plakat-a3-quer` — optional 1 großes Themen-Foto/Hintergrund (z.B.
  Solaranlage, Radweg-Szene), wenn Spec dafür Slot vorgesehen hat
- `infostand-tent-card-a5-quer` — optional Infostand-/Demo-Szene als
  Hintergrund auf einer der zwei sichtbaren Seiten

**Prompt-Qualität:** Codex/DALL·E neigt zu generischen Stockfoto-Looks. Prompts müssen
gezielt sein — Lichtstimmung („warmes Tageslicht, weiche Schatten"), Kameraposition
(„Halbporträt auf Augenhöhe"), Diversity (Geschlecht/Alter/Hautton variieren),
**österreichischer Kontext** (Wiener Café-Hintergrund, Alpenkulisse, niederösterreichische
Dorfstraße — keine US-Suburbia), und **Brand-Farbpalette** (Grünen-Dunkelgrün +
Hellgrün + Akzent-Gelb sollen in der Bildsprache erscheinen, nicht zwingend im Foto
selbst). Prompts werden im manifest.yml dokumentiert, damit künftige Regenerationen
reproduzierbar sind.

**Liability-Hinweis:** Generierte Portraits sind synthetisch (Stable-Diffusion-Style
Personen, keine real existierenden Politiker:innen). Manifest soll explizit vermerken
„synthetisch generiert, nicht reale Person — End-User:innen ersetzen mit echten
Kandidat:innen-Fotos beim Kampagnen-Einsatz". Das schützt vor Persönlichkeitsrechts-
Risiko.

### B — Funktionierende QR-Codes via Library (NICHT via DALL·E)

QR-Codes sind **deterministischer Content**, keine generierten Bilder. DALL·E würde
nicht-scannbare Pseudo-QR-Codes liefern. Stattdessen:

- Neuen Helper `tools/qr_gen.py` (~30 LoC) basierend auf der Python-Library
  `qrcode` (oder System-`qrencode`, falls schon installiert).
- Pro Template, das einen QR-Slot hat, im manifest.yml einen QR-Eintrag mit
  `target_url`, `output_path`, `module_size`, `error_correction_level`, optional
  `embed_logo` (Grünen-Logo in der Mitte).
- Helper rendert PNG (transparent oder weiß-mit-Bleed).
- Bilder committen.

**Templates mit QR-Slot:**
- `wahlaufruf-postkarte-a6-quer` — QR auf Rückseite (Voting-Info-URL)
- `wahltag-tueranhaenger` — QR auf Rückseite (lokale Listen-URL)
- `kandidat-falzflyer-din-lang` — 1–2 QRs auf Closer-Panel
- `infostand-tent-card-a5-quer` — QR auf „Mitmachen"-Seite
- `themen-plakat-a3-quer` — optional QR zur Quelle/Studie

**Demo-URLs:** für Galerie-Previews echt scanbare URLs zur Grünen-Niederösterreich-
Hauptseite (`https://noe.gruene.at/`) oder einer Kampagnen-Landing — damit Reviewer:innen
den QR mit ihrem Handy testen können und sehen „funktioniert echt".

## Constraints

- **Templates bleiben slot-basiert** — keine Hard-References auf Demo-Bilder. Slots in
  `meta.yml` bleiben `optional`. Demo-Bilder gehen nur in den separaten
  `<slug>-preview.sla`-Build, der die Galerie-Preview-PNG erzeugt.
- **One-shot, nicht zur Build-Zeit** — Codex- und QR-Helper laufen während dieses
  Issues, Bilder werden committed, CI/Build ruft sie nie auf.
- **Brand-konform** — keine generischen Stock-Looks; jedes Bild muss aussehen, als
  wäre es für die Grünen NÖ produziert.
- **Reproduzierbar** — manifest.yml dokumentiert Prompt + URL + Settings, sodass
  Re-Generierung gleiche Qualität liefert.
- **Keine Claude-Attribution** in commits/code/manifest.
- **Round-trip + check_ci weiter grün** auf allen 8 Templates.

## Acceptance Criteria

- [ ] `tools/qr_gen.py` existiert, deterministisch, scannbare PNGs, Tests vorhanden
- [ ] `tools/codex_image_gen.py` end-to-end-getestet mit echtem Codex-Call (nicht
      mehr nur dry-run wie in #10)
- [ ] Jedes Template mit Bild- oder QR-Slot hat ein vollständiges
      `templates/<slug>/samples/manifest.yml` mit Prompts/URLs
- [ ] Demo-Portraits + Themen-Bilder generiert für: kandidat-falzflyer-din-lang
      (1 Portrait + 3 Themen), themen-plakat-a3-quer (optional), tent-card (optional)
- [ ] QR-Codes generiert + committed für: wahlaufruf-postkarte, wahltag-tueranhaenger,
      kandidat-falzflyer (1–2), tent-card, themen-plakat (optional)
- [ ] `<slug>-preview.sla` für jedes betroffene Template re-rendered, Galerie-PNG
      aktualisiert, `meta.yml.previews_for_sla`-SHA passt (`bin/check-stale-previews`
      grün)
- [ ] Galerie zeigt die Templates mit echten Bildern und scannbaren QRs
- [ ] Visual-Review-Pass über die aktualisierten Galerie-Previews mit allen drei
      Vision-Modellen — Konsens „mindestens so gut wie ohne Bilder, idealerweise
      sichtbar besser"
- [ ] Keine echten Kandidat:innen-Namen oder Gesichter in den synthetischen
      Portraits; manifest.yml vermerkt „synthetisch, demo-only"
- [ ] PR-Beschreibung enthält Vorher/Nachher der betroffenen Galerie-Previews

## Risiken & Open Questions

- **Codex-DALL·E-Output-Qualität** — variabel; kann sein, dass mehrere Iterationen
  pro Bild nötig sind. Cap: 5 Versuche pro Slot, sonst akzeptieren oder Slot
  leer lassen.
- **QR-Logo-Embed** — fehlertolerant nur mit `error_correction_level=H`; bei
  langen URLs steigt Modulanzahl, Logo-Embed wird kritisch. Test pro QR.
- **Persönlichkeitsrechts-Risiko bei generierten Portraits** — auch synthetische
  Gesichter können „zufällig" wie reale Personen aussehen. Mitigation: explizite
  Demo-only-Markierung im Bild-Footer oder im Galerie-Caption („synthetic,
  demo-only — not a real candidate").
- **Codex-API-Kosten** — DALL·E-Calls kosten. Gesamtkosten für ~5–8 Bilder bei
  einer Standard-Auflösung sollten unter 5€ bleiben; falls deutlich höher, bei
  Issue-Owner nachfragen.

## Phasenvorschlag

1. **Phase 1** — `tools/qr_gen.py` schreiben + Tests (deterministisch, scannbar
   verifizieren via `zbarimg` oder Python-Decode).
2. **Phase 2** — manifest.yml pro Template komplett aufnehmen (Prompts + QR-URLs).
3. **Phase 3** — QR-Codes generieren (deterministisch, schnell).
4. **Phase 4** — Codex-DALL·E-Generierung pro Template, iterativ bis Brand-konform.
5. **Phase 5** — `<slug>-preview.sla` re-rendern, Galerie-Build, Galerie-PNGs
   committen.
6. **Phase 6** — Visual-Review der aktualisierten Previews (Multi-Model), PR.

## Dependencies

- Issue #10 (geliefert in PR #20) — alle Templates, `tools/codex_image_gen.py`,
  manifest-Konvention, `<slug>-preview.sla`-Build-Pfad bereits live.
