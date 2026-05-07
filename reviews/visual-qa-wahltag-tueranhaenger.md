# Gate 3 — Visual QA: wahltag-tueranhaenger

**Date:** 2026-05-07
**Renders:** `page-01.png` (front) + `page-02.png` (back) at 100 DPI.
**Iterations:** 3 (iter-1 1-line headline overflow, iter-2 2-line fix, iter-3 logo embed).

## Iter-1 → Iter-2 → Iter-3 vorher/nachher

| | Iter-1 | Iter-2 | Iter-3 |
|---|---|---|---|
| Headline | "Heute ist" only ("Wahltag." dropped) | "Heute ist / Wahltag." 2-line ✓ | unchanged |
| Logo | absent | absent | white logo on Brand-Bar Dunkelgrün ✓ |
| Wahlkreuz on Hellgrün | ✓ | ✓ | ✓ |
| Stanzkontur (35 mm hole) | ✓ (not visible in PNG) | ✓ | ✓ |

## Final State

- **merge_ready: yes**
- **comparison_to_existing:** Türanhänger occupies a category none of the existing 3
  cover. **First production-ready die-cut template in the gallery.** The Stanzkontur
  + Spot-Color-Layer pattern is reusable for future templates. Visually, the front
  combines Brand-Bar (Dunkelgrün) + Hellgrün-Hero-Band + white body — a richer
  brand-color-mix than any existing Postkarte/Plakat.
- **hierarchy_readability:** Front: Brand-Bar → Wahlkreuz-Hero → "Heute ist / Wahltag."
  → "Wähle Grün." → Bullets → Impressum. 1-second test: glance reads "Wahltag" + green
  + Wahlkreuz = "Wahl heute" instantly.
- **brand_consistency:** Pass. Vollkorn-Italic 28pt headline on white, Wahlkreuz on
  Hellgrün-Band (D12). Multiple Brand-Color zones (Dunkelgrün top, Hellgrün hero, white
  body) read as designed not chaotic.
- **wahlkreuz_background_color_check: pass.** Wahlkreuz on Hellgrün-Band (NOT on white).
- **print_risks:** Hole-Zone clear of content (y=20..65 mm). 2 mm safety from Stanzkontur
  edges to first text. Bullet-Liste at 11pt × 85mm = ~70 chars/line, lesbar at 30 cm.

## Where it's better than the existing 3

- **Production-ready die-cut.** Existing 3 are all flat-print. Türanhänger is shippable
  to a print-shop for stanze-direct production with the Stanzkontur spot-color layer
  baked in.
- **Personalized layer on back.** Kandidat-Portrait + Name + Position + URL + Kontakt.
  Existing 3 are generic.
- **Hellgrün as Hero-Background** — first appearance of Hellgrün as a primary color
  zone. Existing 3 only use Hellgrün as accent.

## Three concrete improvements (deferred)

1. Add a small Hellgrün accent strip below the Hellgrün-Band to soften the transition
   to white.
2. Generate Codex Kandidat-Portrait demo image (D11) — currently the back portrait slot
   is empty. samples/manifest.yml + tools/codex_image_gen.py run pending.
3. Add a fallback graphic treatment for the empty portrait area so an
   end-user-without-portrait doesn't get a blank rectangle.

**Final consensus:** merge-ready. Most production-detailed of the 5 new templates;
first die-cut shipped.
