# Visual QA — Issue #11 Demo Content (Iteration 2)

**Date:** 2026-05-08
**Issue:** `11-demo-bilder-via-codex-qr-codes-für-5-neue-templates`
**Iteration:** 2 — re-render after `scale_type=0` fix on photo + QR `ImageFrame`s

## Why iteration 2

Iteration 1 (`reviews/visual-qa-demo-content.md`) declared "ship" on all 5
templates, but visual inspection of the committed `page-*.png` files showed
critical rendering bugs that the vendor reviewers either missed or implied
in iterate-suggestions only:

- **Falzflyer cover portrait** rendered as a hair/shoulder slice — the
  upper-left ~30 % of the source JPG, not a face.
- **Falzflyer themen-photos** rendered as horizontal strips of louvers /
  doorways — top-left native-pixel slices of the source JPGs.
- **Themen-Plakat themen-hero** rendered as a thin colour band — the
  top-left slice of a wind-turbine sunset photo.
- **Tent-Card hintergrund-mitmachen** rendered as a window/door slice.
- **All 6 QR codes** rendered as top-left finder-pattern fragments only —
  unscannable (Tüeranhänger back, Postkarte back, Themen-Plakat quelle,
  Tent-Card mitmachen, Falzflyer mitmachen + termine).

### Root cause

`tools/sla_lib/builder/primitives.py` `ImageFrame.scale_type` defaulted to
`1` (Scribus SCALETYPE 1 = "free scale" with explicit `LOCALSCX/LOCALSCY`).
With `local_scale=(1.0, 1.0)`, Scribus renders the image at one pt per
pixel — a 1024 × 1536 portrait at a 87 × 105 mm frame (246 × 297 pt) shows
only the top-left 246 × 297 pixels = the top of the head and shoulders.
Same for QR PNGs: 410 × 410 px in a 85 × 85 pt frame = top-left finder
pattern only.

The 3 production templates already used `scale_type=0` (Scribus
SCALETYPE 0 = "frame and image scale together", auto-fit) for inline-
image embeds. The 5 new templates introduced in this issue inadvertently
diverged.

## Fix

Two atomic commits:

1. `e40a967` — `11: fix(templates): set scale_type=0 on photo ImageFrames
   so Scribus auto-fits` — the 6 photo ImageFrames (1× portrait + 3×
   themen on Falzflyer, themen-hero on Themen-Plakat, hintergrund-
   mitmachen on Tent-Card, plus the empty Türanhänger Kandidat-Portrait
   slot for forward consistency).
2. `8a40acb` — `11: fix(templates): set scale_type=0 on QR ImageFrames
   so Scribus auto-fits` — the 6 QR ImageFrames. Iteration-1 task spec
   said to leave QRs alone ("their native dimensions match the frame"),
   but visual evidence after the photo fix proved this assumption wrong.
   Treated as Rule-1 auto-fix-bug deviation, documented in EXECUTION.md.
3. `706b8c9` — `11: chore(gallery): re-render 5 templates after
   scale_type=0 fix` — regenerated SLA + preview.pdf + page-*.png +
   site/public mirrors + meta.yml previews_for_sla SHAs. Determinism
   verified by a second render run producing byte-identical output.

## Per-template Verdicts (iteration 2)

| Template | Gemini Verdict | Codex Verdict | Claude (this agent) | Final |
|---|---|---|---|---|
| `themen-plakat-a3-quer` | ship | (empty, known) | ship | **ship** |
| `wahlaufruf-postkarte-a6-quer` | ship | (empty, known) | ship | **ship** |
| `wahltag-tueranhaenger` | ship | (empty, known) | ship | **ship** |
| `infostand-tent-card-a5-quer` | ship | (empty, known) | ship | **ship** |
| `kandidat-falzflyer-din-lang` | ship | (empty, known) | ship | **ship** |

**Codex output:** still empty in all 5 calls — same 0.128.0 multi-image
`-i` limitation as iteration 1. Falls back to Gemini + Claude, which
provide complete structured feedback.

## Visual confirmation (Claude, pixel-level)

Page-by-page inspection of the regenerated PNGs:

- **`kandidat-falzflyer-din-lang/page-01.png`** — P1 portrait now shows
  a recognisable head-and-shoulders "Maria Beispiel" face with the
  "Symbolfoto — KI-generiert" caption band visible at the bottom of
  the portrait. P3 Wahlkreuz unchanged (was always rendering correctly).
- **`kandidat-falzflyer-din-lang/page-02.png`** — Three thematic photos
  visible (P4 Klima rooftop solar / P4 Soziales building interior / P5
  Bildung schoolyard). P6 contains both QR codes (mitmachen + termine)
  with sunflower centres, fully visible and at expected size.
- **`themen-plakat-a3-quer/page-01.png`** — QR-quelle visible top-right
  (sunflower-centred). Themen-hero photo visible bottom of page (wind-
  turbine sunset). The wide-thin 290 × 18 mm frame letterboxes the
  source photo aspect; acceptable per the iteration-1 edge-case note.
- **`infostand-tent-card-a5-quer/page-01.png`** — Hintergrund-Mitmachen
  shows people at an info booth (recognisable scene). QR-mitmachen
  visible at panel-A bottom (17 × 17 mm, sunflower-centred).
- **`wahltag-tueranhaenger/page-02.png`** — QR-back fully visible and
  scannable (30 × 30 mm with sunflower centre). Kandidat-Portrait slot
  remains intentionally empty (no JPG in samples/) as per manifest;
  end-user injection now auto-fits because the slot has explicit
  `scale_type=0`.
- **`wahlaufruf-postkarte-a6-quer/page-02.png`** — QR-back visible at
  bottom-right of contact area, sunflower-centred.

## Aggregate findings

### Improvement vs iteration 1

Iteration 1 was effectively a non-render — broken slices of source
images that none of the vendor reviewers flagged as a rendering bug
(they read the slices as "the documented design"). Iteration 2 is the
first time the demo content actually renders.

### Brand consistency

- All 6 photos carry the "Symbolfoto — KI-generiert" caption band per
  EU AI Act 3-layer disclosure (visible in PNG bottom strip).
- All 6 QRs use Dunkelgrün modules with the sonnenblume-circle logo
  embedded centrally, matching brand palette.
- Wahlkreuz and Logo embeds remain rendered correctly (already on
  `scale_type=0`, untouched).

### Iterate suggestions (non-blocking, deferred to future issues)

From the Gemini reviews:

- 1 pt Dunkelgrün hairline above the Themen-Plakat hero-photo to define
  the footer zone (cosmetic).
- Türanhänger contact-info field width 50 → 55–60 mm to avoid e-mail
  wraps when QR-clearance allows (cosmetic).
- Wahlaufruf-Postkarte: small "23.5." accent between Wahlkreuz and
  headline (cosmetic).
- Türanhänger: future iteration could include a Codex portrait JPG
  in samples/ to demonstrate the personalisation slot.

None of these block merge. Capture as discovered issues for follow-up.

## CI gates (iteration 2)

- `bin/check-stale-previews`: PASS
- `bin/validate`: PASS (sla_diff + visual_diff for the 3 round-trip
  production templates)
- `python3 tools/check_ci.py templates/<slug>/template.sla` — exit 0
  for all 8 templates (warnings only, expected from prior CI baseline)
- `python3 -m pytest tools/sla_lib/tests/ templates/_smoke/` — 338
  passed, 0 failed
- Render determinism: second `bin/render-gallery` run produced
  byte-identical output (no new diffs)

## Decision

**MERGE-READY.** All 5 demo-content templates render correctly, all
QRs are scannable at intended sizes, all photos are appropriate-aspect
fits with EU-AI-Act-compliant watermarks, and CI gates are green.
Outstanding cosmetic suggestions deferred to future issues.
