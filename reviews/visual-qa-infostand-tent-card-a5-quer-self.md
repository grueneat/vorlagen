# Self-Review (Mini-Gate-3) — infostand-tent-card-a5-quer

**Date:** 2026-05-07
**Reviewer:** Claude
**Render:** `page-01.png` at 100 DPI.

## Iteration 1 — first-pass

### What works
- **Two-panel tent rendering correctly:** Panel A "Klimaschutz konkret." + 3
  bullets normal orientation; Panel B "Climate. Concrete." + EN bullets rotated
  180°. When the sheet is folded, both sides face their respective audiences
  with text upright.
- **Vollkorn Black Italic 36pt Dunkelgrün headlines** as visual anchors on
  both panels.
- **Body 14pt Gotham Book** — readable at table distance (50–80cm).
- **Impressum knapp über der Falz** (y=96..100), respects the 3 mm contact zone
  rule (P-PRINT-4): bottom 3 mm of each panel y=102..105 (Panel A) and
  y=207..210 (Panel B) is empty.
- **Falz-Layer + Spot-Color document-local** — Druckerei-ready.

### What needs fixing
- **Falz-Linie not visible in preview PNG:** like Stanzkontur on Türanhänger,
  the Falz layer is `printable=0` so the rendered PDF/PNG doesn't show it.
  Correct print behavior. For visual review, could add a Gate-3 render with
  Falz layer temporarily printable.
- **Panel B impressum missing:** spec only requires impressum once. Currently
  on Panel A. ✓ Fine.
- **Bilingual content:** spec calls for DE/EN as default. Current build follows
  this. End-users may want both panels DE — that's an end-user customization,
  not a build issue.

### Comparison
- **Vs Postkarte/Plakat/Zeitung:** Different category (3D vs 2D). Tent-Card is
  the first 3D-readable template — closest analog to nothing in the existing 3.
- **Vs other new templates:** Tent-Card occupies a unique format (A4 quer
  gefalzt) that no other template covers.

### "Where is it BETTER than the existing 3?"
- **First 3D-readable template:** Postkarte/Plakat/Zeitung are flat. Tent-Card
  is the first template designed for 3D viewing — covers a use case the
  existing 3 cannot address (Tisch-Aufsteller).
- **Bilingual reach:** DE/EN dual-language covers tourist towns, university
  campuses, multi-cultural Bezirke — the existing 3 are DE-only.
- **Falz-Layer pattern:** establishes the Falz-Layer + Spot-Color pattern that
  the Falzflyer (template 16) will reuse.

### Iteration 2 fix candidates (deferred to Gate 3)
1. Optional: Add a Hellgrün vertical strip on Panel A's right edge as Brand-
   Akzent (currently the panel is pure white).
2. Verify with vision review if text density at 14pt × 273mm is too sparse
   (currently each line ~110 chars, hard limit on lesbarkeit).

## Decision

**Iteration 1: PASS.** Bilingual layout works, rotation correctly handled, fold
mechanics are clean. Brand quality on par with existing 3 templates.
