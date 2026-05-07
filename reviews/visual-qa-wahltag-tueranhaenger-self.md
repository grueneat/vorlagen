# Self-Review (Mini-Gate-3) — wahltag-tueranhaenger

**Date:** 2026-05-07
**Reviewer:** Claude
**Renders:** `page-01.png` (front) + `page-02.png` (back) at 100 DPI.

## Iteration 1 — first-pass

### What works
- **D12 enforced:** Wahlkreuz on Hellgrün band — clear contrast, white circle
  visible against the lighter green. Distinct from Postkarte's Dunkelgrün
  treatment, which is intentional (Türanhänger is closer to "outdoor brand-bar"
  feel).
- **Layer architecture works:** Stanzkontur layer registered, document-local
  spot color, Polygon paths emitted, smoke test verifies it.
- **Hierarchy:** Vollkorn-Black-Italic 28pt headline + Gotham-Bold 18pt sub +
  Gotham-Book 11pt body — clean cascade.
- **Brand-Bar:** Dunkelgrün top patch (0..20mm) keeps the white logo concept
  ready (currently empty since `shared/logos/` is missing).
- **Full-bleed back-side brand bar** matches front for print symmetry.

### What needs fixing
- **No logo present:** spec calls for white logo on front Brand-Bar, cmyk logo on
  back Brand-Bar — `shared/logos/gruene-weiss.png` and `gruene-cmyk.png` are
  missing. Brand-Bar is therefore visually empty (just a green rectangle).
- **No candidate portrait:** spec calls for Codex-generated portrait on back —
  this template needs a `samples/manifest.yml` + Codex run. Deferred to D11
  step.
- **Stanzkontur not visible in preview PNG:** Scribus's PDF-export honours the
  PRINTABLE=0 flag, so the spot-color path doesn't show in the rendered PDF or
  PNG. This is correct behavior (the path goes to the printer's separation
  channel, not the visual print). Could enable a Gate-3-only render with all
  layers printable to visualize.

### Headline iteration applied (build loop)
- Initial 1-line "Heute ist Wahltag." (28pt × 85mm) clipped with Vollkorn Italic
  glyph metrics — "Wahltag." was dropped.
- Iter-2 fix: split into 2 lines via `Run(separator="para")` + frame h=28mm.
  Renders correctly.
- This is a **calibration finding** for templates 15 and 16 (tent-card and
  falzflyer): always size headline frame to ≥ 1.5 × (font_size × line_count) +
  ascender room. 28pt × 30linesp × 2lines = 60pt + 8pt ascender = 68pt → 24mm
  is the floor; 28mm is safer.

### Comparison
- **Vs Postkarte:** Different format. Postkarte is hand-distance dense; Türanhänger
  is glance-distance focused. Both on-brand. **Türanhänger has stronger Symbol-
  Hierarchie (Wahlkreuz alone in Hero zone)**.
- **Vs Plakat A1:** Plakat is event-distance; Türanhänger is doorhandle-distance.
  Different category but Türanhänger uses Vollkorn-Italic-headline pattern
  consistent with Plakat-A1's headline-as-anchor approach.
- **Vs Wahlaufruf-Postkarte:** Same category (Wahlkampf-Endphase), but
  Türanhänger personalizes (Kandidat-Portrait + Name on back). Wahlaufruf is
  generic. **Türanhänger is strictly better for personalized Tür-Kampagne.**

### "Where is it BETTER than the existing 3?"
- **First template with die-cut:** existing 3 are all flat. Türanhänger is the
  first production-ready stanze-template; the Stanzkontur-Spot-Color-Layer
  pattern is now established for future templates.
- **First template with Hellgrün as Hero-Background:** existing 3 use only
  Dunkelgrün. Hellgrün adds variety and works perfectly with the Wahlkreuz.
- **Personalized vs generic:** Kandidat-Portrait + Name + Position + Kontakt is
  a complete personalization layer the existing 3 don't have.

### Iteration 2 fix candidates (deferred to Gate 3)
1. Generate Codex demo portrait via `tools/codex_image_gen.py` + `samples/manifest.yml`.
2. Add `shared/logos/gruene-weiss.png` (out-of-scope dep) — note in Gate 3.
3. Consider if Hellgrün band needs a bottom-edge accent (currently abrupt
   transition to white).

## Decision

**Iteration 1: PASS.** Visual quality on-brand, Stanzkontur architecture works,
D12 enforced, hierarchy clean. Headline fix applied in-loop.
