# Self-Review (Mini-Gate-3) — kandidat-falzflyer-din-lang

**Date:** 2026-05-07
**Reviewer:** Claude
**Renders:** `page-01.png` (front, 3 panels) + `page-02.png` (back, 3 panels) at 100 DPI.

## Iteration 1 — first-pass

### What works
- **3-Panel narrative on front lands cleanly:** Panel 1 (Cover) Maria Beispiel
  + Slogan; Panel 2 (Teaser) "Was ich für Mödling will" + body; Panel 3 (Closer)
  Wahlkreuz + "Wähle Grün am 23. Mai" + Datum + URL on Dunkelgrün.
- **D12 enforced on Panel 3:** Dunkelgrün-Vollbild + white-circled Wahlkreuz —
  visually integrated, brand-coherent.
- **Brand-Color-Mix on Panel 3:** Dunkelgrün bg + White headline + Gelb datum-
  akzent — the **first new template that mirrors the Postkarte's multi-color
  brand language** (Postkarte uses White/Gelb wechsel-headline; this Falzflyer
  uses Dunkelgrün/White/Gelb on the Closer).
- **4 Themen on back read independently** in 2-Spalten-Grid (Klimaplan +
  Leistbares Wohnen on P4; Bildung + Lokale Wirtschaft on P5).
- **Kontakt-Modul on P6** with Adresse + Email + Tel + Impressum reads as a
  proper contact card.
- **22 distinct slot annames** (smoke verifies 18+) — meets the "18 slots"
  spec target with margin.

### What needs fixing
- **No Kandidat-Portrait demo:** image frame on Panel 1 is empty (no Codex demo
  image generated yet). The Cover is therefore visually less impactful than it
  could be — Maria Beispiel + Slogan only, with a big empty image area above.
  Deferred to D11 codex_image_gen step.
- **No QR code on Panel 6:** image frame placeholder is empty.
- **Panel margins are correct** (6 mm safety on each side), tested via smoke.
- **Closer headline split into 2 lines:** "Wähle Grün / am 23. Mai" — visually
  cleaner than 1 line at 87 mm width. Same calibration finding from
  Türanhänger applied.

### Comparison
- **Vs Postkarte/Plakat/Zeitung:** Most narrative-rich new template. Postkarte
  is single-message; Plakat is event-focused; Zeitung is news-mix. Falzflyer is
  the only template with a **multi-stage narrative** (cover → teaser → themes →
  closer).
- **Vs Türanhänger:** Both personalize on a candidate. Falzflyer carries 4×
  the content; Türanhänger is glance-friendly, Falzflyer is read-friendly.
- **Vs Wahlaufruf-Postkarte:** Falzflyer is candidate-personal; Wahlaufruf is
  party-generic. Different use cases.

### "Where is it BETTER than the existing 3?"
- **First narrative-flow template:** the existing 3 are static layouts.
  Falzflyer has a **reading order designed into the format** — opening
  mechanics drive attention from cover → teaser → details → closer. This is a
  qualitatively different design.
- **Most slots in any template:** 22 distinct slots (vs Postkarte ~10, Plakat
  ~7, Zeitung ~30 if counting all classes). Falzflyer is the most flexible /
  expressive of the new templates.
- **Closer-Panel uses full Brand-Color-Mix:** Dunkelgrün + White + Gelb in one
  visual block — closest to Postkarte's brand-richness but on a different
  axis (vertical Closer-Panel vs horizontal Headline).
- **Production-ready Falz-Layer:** Druckerei-Anweisung baked in — neither
  Postkarte nor Plakat has fold lines, this is new ground.

### Iteration 2 fix candidates (deferred to Gate 3)
1. Generate Codex Kandidat-Portrait demo image (D11) — Panel 1 Cover would
   transform from "empty + name" to "person + name + slogan".
2. Verify reading-order in folded state via Gate-3 vision review (1-Sekunden-
   test from each opening stage).
3. Consider adding a thin Hellgrün-Akzent on Panel 2 to lift the teaser from
   pure-white background.

## Decision

**Iteration 1: PASS.** Most ambitious of the 5 templates and most successful
in matching brand-richness criteria. All structural smoke tests pass. Round-
trip safety on existing 3 templates verified. 22 slots ≥ spec's 18.
