---
review_of: zeitung-band-consistency-iter4
review_type: visual
review_topic: "Zeitung A4 band-consistency audit (Issue #25 follow-up: page-10 col-3, page-11 portrait, page numbers)"
reviewed_at: 2026-05-09
tool: codex
codex_cli_version: codex-cli 0.128.0
prompt_path: prompts/zeitung-band-consistency-audit.md
images_attached: 14
---

## Codex output (verbatim)

- Page: 01
  - No findings. Cover hero is an intentional full-bleed opt-out; remaining cover content reads as intentional and non-problematic.

- Page: 02
  - No findings. The P1 hero photo stops at the body content width and visually aligns with the text grid below; it does not run full bleed left/right.

- Page: 03
  - No findings. Header-band title is correctly used; body text, mid-page headline, and bottom image remain inside the free zone and side margins.

- Page: 04
  - No findings. Header-band title is correct; image and green text box stay within the free zone and content width.

- Page: 05
  - No findings. Header-band title is correct; lower photo stays within content width and above the footer band.

- Page: 06
  - No findings. Header-band title is correct; lower-right image sits inside the body grid and remains above the footer band.

- Page: 07
  - No findings. Header-band title is correct; green list box and lower article block remain within the free zone and side margins.

- Page: 08
  - No findings. Header-band title is correct; bottom profile module and portrait stay within content width and above the footer band.

- Page: 09
  - No findings. Header-band title and secondary headline are correctly placed; quote boxes and body columns remain within the intended structure.

- Page: 10
  - No findings. The left-half spread image is content-width only, not page-edge bleed, and does not spill toward the spine.

- Page: 11
  - No findings. The right-half spread image is content-width only, not page-edge bleed, and does not spill toward the spine. The lower-right portrait sits inside the right text column and remains above the footer band.

- Page: 12
  - No findings. The bottom photo sits on the green background with no visible white side borders; the page-wide dark green field correctly carries behind it.

- Page: 13
  - No findings. White-on-green article layout respects the page structure; no body content appears to intrude into the footer band.

- Page: 14
  - No findings. Back-cover hero appears symmetrically treated left/right; no asymmetric side margin issue is visible.

```xml
<verdict value="pass" findings="0">
  All 14 PNG previews were opened and visually inspected. I found no band intrusions or side-margin overruns in ordinary body content. The user-cited fixes are visible: page 2 hero is constrained to body width, pages 10 and 11 spread halves are content-width and do not cross the spine, page 11's lower-right portrait remains inside the right column and above the footer, page 12's bottom photo sits cleanly on the full-page green background without white side borders, and page 14's back-cover hero appears left/right symmetric. The band model holds for the body-pool pages.
</verdict>
```

## What changed since iter3

Iter3 ran after the architectural change (excluded_pages -> per-frame is_full_bleed) but BEFORE the page-10 col-3 widening, the page-11 portrait vertical-extent fix, and the page-11/12 page-number fixes. Iter4 verifies that those follow-up fixes hold.

## Cross-check vs audit JSON

`bin/audit-alignment zeitung-a4-grun --json` reports **0 band_consistency_warnings** across all 14 pages. `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` exits 0. Audit-tool and Codex agree.

## Gate decision

PASS. Issue #25 is structurally complete: every page is tested by the band rule (no per-page exclusion); per-frame opt-outs (`is_full_bleed=True`) exist where the design needs them and are visible at the frame definition; the user-cited geometry bugs are fixed; Codex visual review verdict is `pass`.
