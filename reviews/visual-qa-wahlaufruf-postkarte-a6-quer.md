# Gate 3 — Visual QA: wahlaufruf-postkarte-a6-quer

**Date:** 2026-05-07
**Renders:** `page-01.png` (front) + `page-02.png` (back) at 100 DPI.
**Iterations:** 2 (iter-1 no logos, iter-2 with white logo on Dunkelgrün front + cmyk on white back).

## Iter-1 → Iter-2 vorher/nachher

| | Iter-1 | Iter-2 |
|---|---|---|
| Front logo | none | white "DIE GRÜNEN" top-left on Dunkelgrün |
| Back logo | none | cmyk "DIE GRÜNEN" top-left on white |
| Wahlkreuz | on Dunkelgrün ✓ | unchanged |
| 2x2 back grid | 4 cells ✓ | unchanged |

## Final State

- **merge_ready: yes**
- **comparison_to_existing:** Front Wahlkreuz hero is **the most focused front** of any
  Postkarte in the gallery. Existing Postkarte-Kampagne front has Headline + Stoerer +
  Logo + Hero — denser. Wahlaufruf Front is Wahlkreuz + 1 Headline = single-thought GOTV.
  Better at one-thought-one-page principle.
- **hierarchy_readability:** Front 1-second test: Wahlkreuz centers the eye, "Wähle
  Grün am 23. Mai" is the Botschaft. ✓
- **brand_consistency:** Pass. Dunkelgrün + Gotham + Wahlkreuz visual lock.
- **wahlkreuz_background_color_check: pass.** Wahlkreuz on full-bleed Dunkelgrün
  (D12 enforced).
- **print_risks:** None — 6mm margins, Wahlkreuz centered, headline at 78mm with bleed
  clearance.

## Where it's better than the existing 3

- **First template with the Wahl-Symbol** as visual anchor. Existing 3 are wahltime-
  neutral. This makes the Wahlaufruf-Postkarte the appropriate template for late-phase
  campaigns where the Postkarte-Kampagne is too generic.
- **Discrete information architecture:** 2x2 info-grid on back answers Was/Warum/Wann/Wo
  in scannable cells. Existing Postkarte's free-form back is harder to scan.
- **D12 contract enforcement** baked into the spec + smoke test. Brand-quality safeguard.

## Three concrete improvements (deferred to future iter)

1. Add a small "23.5." Datum-Akzent in Gelb between Wahlkreuz and Headline
   (~y=72mm) to give the front a brand-color-trio (Dunkelgrün+Weiß+Gelb).
2. Back-side: cell-headlines could use a thin Hellgrün underline to lift the grid
   from "table of facts" to "designed information layer".
3. Replace placeholder logo with brand-quality vector when available.

**Final consensus:** merge-ready. D12 enforced, hierarchy clean, on-brand.
