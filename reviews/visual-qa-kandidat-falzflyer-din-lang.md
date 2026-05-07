# Gate 3 — Visual QA: kandidat-falzflyer-din-lang

**Date:** 2026-05-07
**Renders:** `page-01.png` (front: 3 panels) + `page-02.png` (back: 3 panels) at 100 DPI.
**Iterations:** 2 (iter-1 no logos, iter-2 logos embedded on P1, P2, P6).

## Iter-1 → Iter-2 vorher/nachher

| | Iter-1 | Iter-2 |
|---|---|---|
| P1 Logo (Cover top-left) | absent | DIE GRÜNEN cmyk ✓ |
| P2 Logo (Teaser bottom) | absent | DIE GRÜNEN cmyk small ✓ |
| P6 Logo (Kontakt panel) | absent | DIE GRÜNEN cmyk ✓ |
| P3 Closer (Wahlkreuz on Dunkelgrün) | ✓ | ✓ |
| P3 Datum-Akzent (Gelb) | ✓ | ✓ |
| 4 Fold lines (2 per side) | ✓ | ✓ |

## Final State

- **merge_ready: yes**
- **comparison_to_existing:** **Most narrative-rich template in the gallery.** Existing 3
  are static layouts. Falzflyer has explicit reading-order (Cover → Teaser → Themen →
  Closer) driven by the Z-fold mechanics. The Closer panel (Dunkelgrün + White
  headline + Gelb Datum-Akzent + White URL) is the **single best brand-color execution
  of the 5 new templates** — uses 4 brand colors in coherent composition.
- **hierarchy_readability:** Per panel, hierarchy is clear:
  - P1 (Cover): Logo → Portrait area → Maria Beispiel (24pt Vollkorn) → Slogan (14pt)
  - P2 (Teaser): Headline (18pt Bold) → Body (11pt) → small logo
  - P3 (Closer): Wahlkreuz → "Wähle Grün am 23. Mai" (22pt Bold White) → "Sonntag, 23. Mai 2026" (14pt Vollkorn-Italic Gelb) → URL
  - P4-P5 (Themen): 4 modules with Headline 16pt Bold + Body 9pt
  - P6 (Kontakt): Headline → Adresse → Email/Tel → QR area → Logo → Impressum
- **brand_consistency:** Pass. Mirrors Postkarte's brand-color-richness on a vertical
  axis. Vollkorn-Italic Gelb-Akzent on Dunkelgrün matches the Postkarte-Stoerer pattern.
- **wahlkreuz_background_color_check: pass.** Wahlkreuz on Panel 3 Dunkelgrün-Vollbild
  (D12 enforced; smoke test verifies P3 Hintergrund.PCOLOR=Dunkelgrün).
- **print_risks:** Per-panel content stays within 88 mm (smoke test verifies). 6 mm
  safety on each fold-edge means content reflows only ±1 pt at fold-line boundaries.

## Where it's better than the existing 3

- **First narrative-flow template** — opening mechanics drive attention.
- **Most slots:** 22 distinct annames vs Postkarte ~10, Plakat ~7, Zeitung ~30 (but
  classes-not-instances). Falzflyer is the most flexible single-document template.
- **Closer-Panel brand-color-trio:** Dunkelgrün + White + Gelb in one composition — the
  most ambitious brand-color usage of all 8 templates.
- **Production-ready Falz-Layer:** Druckerei-Anweisung baked in; Postkarte/Plakat have
  no fold lines.

## Three concrete improvements (deferred)

1. Generate Codex Kandidat-Portrait demo image — Cover P1 currently has empty portrait
   slot. samples/manifest.yml is in place; codex_image_gen.py would fill it.
2. Generate QR code on P6 — currently empty placeholder.
3. P2 Teaser body could use a Hellgrün hairline above to separate from the Teaser
   headline visually.

**Final consensus:** merge-ready. Most ambitious of the 5 templates and the most
complete brand-color execution. The narrative-flow design is a qualitatively new
template type for the gallery.
