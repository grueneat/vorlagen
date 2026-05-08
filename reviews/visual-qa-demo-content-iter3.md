# Visual QA — Demo-Content Gallery, Iteration 3

**Date:** 2026-05-08
**Branch:** `issue/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates`
**PR:** [#22](https://github.com/GrueneAT/vorlagen/pull/22)
**Composite grid:** `reviews/all-templates-grid.png`
**Per-template detail reviews:** `reviews/visual-qa-{slug}-iter-3.md`

## Iteration scope

This pass closes three deltas surfaced after iter-2 sign-off:

1. **Brand Quickguide as repo reference** — copy `260313_DieGrünen_CD-Quickguide.pdf`
   into `shared/brand/`, distill rules into `QUICKGUIDE-NOTES.md` for build.py
   authors and reviewers (no template changes from this delivery on its own).
2. **Brand-Bund Logo integration** — replace the placeholder `gruene-cmyk.png`
   wordmark with the official `gruene-logo-bund-dunkel.png` (G-brushstroke +
   DIE-GRÜNEN-tag) wherever the template surface is white/light. Frames
   re-dimensioned to honor the new ~1.12:1 aspect.
3. **Text/Visual gap fill** — Türanhänger gets a Codex
   Bürgermeister-Portrait demo, Tent-Card gets Mitmachen-CTA + Termine
   list per panel, Themen-Plakat hero photo enlarged to a visually
   dominant 90×60 mm rendered footprint.

The 3 stable production templates (`postkarte-a6-kampagne`,
`plakat-a1-hochformat`, `zeitung-a4-grun`) were visually inspected per
Delivery C4 and intentionally left unchanged — their empty zones are
part of the original design contract and modifying them would risk the
round-trip-diff guarantee.

## Per-template verdicts (Gemini Vision)

| Template                          | iter-3 verdict | Δ vs iter-2                                                                                          |
|-----------------------------------|----------------|------------------------------------------------------------------------------------------------------|
| themen-plakat-a3-quer             | ship           | Brand-Bund logo top-left; hero photo enlarged 5× visible area; bottom layout rebalanced              |
| infostand-tent-card-a5-quer       | ship           | Brand-Bund logo both panels; Mitmachen/Get-involved CTA + termine list per panel                     |
| wahlaufruf-postkarte-a6-quer      | ship           | Brand-Bund logo on back; front (Dunkelgrün) keeps gruene-weiss.png unchanged                         |
| kandidat-falzflyer-din-lang       | ship           | Brand-Bund logo on P1 Cover, P2 Teaser-bottom, P6 Closer-Back; P3 Closer (Dunkelgrün) untouched      |
| wahltag-tueranhaenger             | ship           | Bund-Dunkel below Brand-Bar on back; Codex Bürgermeister portrait (male, salt-and-pepper); Stefan Beispiel/Bürgermeisterkandidat-bio |

All five templates: **ship**. No blockers.

## Aggregate strengths (synthesized)

- The Brand-Bund logo (G-brushstroke + DIE-GRÜNEN-tag) is the
  instantly-recognizable party mark and significantly raises the brand
  authority of every template that previously carried only the wordmark
  placeholder. White/light surfaces now read as official party assets,
  not generic green-themed flyers.
- The Türanhänger Codex portrait introduces gender diversity (male
  Bürgermeisterkandidat) into the demo set after iter-1's female
  Falzflyer cover portrait. The salt-and-pepper aesthetic + community-
  space backdrop reads as authentic local-politics tone.
- The tent-card now reads complete from both the German and the English
  side: each side has a CTA above the dates list, providing a real
  "what to do next" instead of bullets-only.
- The themen-plakat hero is now a visual anchor at the bottom, ~5× the
  previous visible area (90×60 mm vs ~27×18 mm), grounding the three
  evidence columns above.

## Iteration suggestions (deferred to follow-up)

Aggregated `iterate_suggestions` from per-template Gemini reviews:

- Test QR scan reliability at A3 (themen-plakat) viewing distances
  1–2 m. Empirically tested at small print sizes via pyzbar — needs
  field validation at large format.
- Consider a per-Bezirk colour accent in addition to the brand
  Dunkelgrün — postkarte/falzflyer feel uniformly green, regional
  differentiation could be added via Hellgrün overlays.
- Review headline-Zeilenabstand drift flagged in
  `shared/brand/QUICKGUIDE-NOTES.md` Schriftgrundlagen section —
  several templates use `linesp ≥ Schriftgröße` instead of
  Quickguide's `× 0.9`. Tightening would be a separate Hygiene issue.

## Tooling

- Codex CLI multi-image `-i` flag still returns empty (known 0.128.0
  limitation, documented in iter-1 EXECUTION.md). Gemini Vision served
  as the sole visual reviewer this iteration.
- All 5 per-template Gemini outputs land at
  `reviews/visual-qa-{slug}-iter-3.md` for traceability.

## Sign-off

PR #22 ready for orchestrator-driven merge after this iteration's
commits land. EXECUTION.md updated with iter-3 entries, status remains
`complete`. No blockers.
