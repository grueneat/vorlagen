# Self-Review (Mini-Gate-3) — wahlaufruf-postkarte-a6-quer

**Date:** 2026-05-07
**Reviewer:** Claude (this session)
**Render:** `templates/wahlaufruf-postkarte-a6-quer/page-01.png` and `page-02.png` at 100 DPI.

## Iteration 1 — first-pass critique

### What works
- **D12 enforced:** Wahlkreuz on Dunkelgrün-Vollbild — white circle clearly visible
  around the yellow cross. Brand-Symbol intact.
- **Front 1-Sekunden-Test passes:** instantly recognizable as Grünen-Wahlaufruf:
  Wahlkreuz central, "Wähle Grün am 23. Mai" in white below. No ambiguity.
- **Back 1-Sekunden-Test passes:** 2x2 grid with Dunkelgrün cell-headlines reads
  as info-card. Each cell answers a question.
- **Hierarchy:** Headline 24pt > Cell-Headline 14pt > Cell-Body 9pt > Impressum 6pt.
- **Color discipline:** White on Dunkelgrün (front), Dunkelgrün on White (back), no
  random colors.

### What could be stronger
- **Front feels slightly empty:** the Wahlkreuz at 55mm sits in the upper-right
  third; the headline is at the bottom. There's a 7mm gap between them but the
  upper-left corner has just the (hidden) logo slot. Consider:
  - Add a small "23.5." date prominently somewhere on the front.
  - Or add a thin Hellgrün or Magenta accent above/below the headline.
- **Back grid:** cell-headline (14pt) and cell-body (9pt) are both left-aligned in
  Dunkelgrün/Black — clean, but lacks a visual rhythm element. The Postkarte
  baseline has Magenta-Stoerer; this back is purely informational.
- **No logo present:** the spec calls for `Logo Grüne (weiss)` top-left on front
  and `Logo Grüne (cmyk)` top-left on back. Like Themen-Plakat, the
  `shared/logos/` dir doesn't exist in this repo. Build skips logo if missing.

### Comparison to existing baseline
- **Vs Postkarte (existing):** Front of this Wahlaufruf is more focused — single
  symbol + single sentence. Existing Postkarte has Hauptbotschaft + Stoerer +
  Logo + Hero Image — denser but more dispersed. **Wahlaufruf is better at the
  one-thought-one-page** principle for late-phase GOTV.
- **Vs Plakat A1:** Plakat is event-focused; Wahlaufruf is wahlkampf-focused.
  Different axis of comparison.
- **Vs Zeitung:** Zeitung is news-format, Wahlaufruf is direct-mail. Not
  comparable.

### "Where is it BETTER than the existing 3?"
- **First-Wahlkreuz template:** the existing 3 templates have NO direct
  Wahl-Symbol — all are wahltime-neutral. This is the first template in the
  gallery that says "Wahl ist jetzt".
- **D12 contract enforced:** the WahlkreuzSymbol block (and direct integration
  here) enforce the colored-background rule. This is a brand-quality safeguard
  that would be impossible to replicate in the Postkarte's free-form approach.
- **Discrete information architecture on back:** 2x2 grid with consistent cell
  format is a teaching tool — answers "Was/Warum/Wann/Wo" — Postkarte has free-
  form back. **Better for late-phase GOTV** where readers scan, not read.

### Iteration 2 fix candidates (deferred to Gate 3)
1. Add the date "23.5." as a Gelb-Akzent text on the front, between the Wahlkreuz
   and the headline (~y=72mm).
2. Verify (in Gate 3 with vision review) whether the layout feels too sparse on
   the front.

## Decision

**Iteration 1: PASS.** Core Brand-quality criteria met (D12, hierarchy, on-brand
typography, two-page consistency). Minor density concerns deferred to Gate 3.

This template is a **calibration win** for the Wahlkreuz embedding workflow:
- pack_inline_image works through the build path
- D12 background-color contract enforced via direct Polygon
- Smoke test verifies inline-image bytes round-trip to source asset (verifies
  qCompress encoder correctness end-to-end)
