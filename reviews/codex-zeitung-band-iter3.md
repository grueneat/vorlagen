---
review_of: zeitung-band-consistency-iter3
review_type: visual
review_topic: "Zeitung A4 band-consistency audit (Issue #25 post-user-feedback verification)"
reviewed_at: 2026-05-09
tool: codex
codex_cli_version: codex-cli 0.128.0
prompt_path: prompts/zeitung-band-consistency-audit.md
images_attached: 14
---

## Codex output (verbatim)

- Page 01: No findings. Cover hero is an intentional full-bleed opt-out; other cover content appears contained and the footer area remains clear.
- Page 02: No findings. The P1 hero photo is not full bleed; its left and right edges align with the body content width below.
- Page 03: No findings. Header-band title is correctly placed; free-zone text and bottom image stay inside the body area and above the footer band.
- Page 04: No findings. Header-band title is correct; right-column image and lower green text card stay within content width and clear the footer.
- Page 05: No findings. Header-band title is correct; the bottom photo sits at content width and remains above the footer band.
- Page 06: No findings. Header-band title is correct; the lower-right image and its caption remain inside the free zone and do not enter the footer band.
- Page 07: No findings. Header-band title is correct; mid-page green box and lower article block stay within the body grid.
- Page 08: No findings. Header-band title is correct; the lower profile block and portrait stay within content width and above the footer.
- Page 09: No findings. Header-band title is correct; quote cards and body text remain within the intended free-zone structure.
- Page 10: No findings. The left P9 spread half is content-width, not page-bleed, and does not spill toward the spine; other body elements remain compliant.
- Page 11: No findings. The right P9 spread half is content-width, not page-bleed, and does not spill toward the spine. The portrait photo is contained within the right text column and stops above the footer band.
- Page 12: No findings. The bottom photo sits on the green background with no white side borders; page content remains visually consistent with the band model.
- Page 13: No findings. White-on-green page treatment remains structurally compliant; no body content appears to intrude into the footer band.
- Page 14: No findings. Back-cover hero is an intentional opt-out and appears symmetrically placed left/right; upper content remains properly contained.

```xml
<verdict value="pass" findings="0">
  All 14 PNG previews were visually inspected. No ERROR or WARNING findings are visible against the Issue #25 band-and-margin model. The user-cited fixes appear to be in place: page 2 hero is content-width, pages 10 and 11 spread halves are content-width and do not cross the spine, the page 11 portrait is contained within the right column and above the footer, page 12's bottom photo sits on green without white side borders, and page 14's back-cover hero appears horizontally symmetric.
</verdict>
```

## Architectural change addressed by iter3

Iter1/iter2 used per-page `excluded_pages: [1, 2, 10, 11, 14]` to silence the band rule on feature pages. The user pointed out this was a per-page escape hatch — the rule should TEST every page. Iter3 verifies the post-user-feedback state:

1. `excluded_pages` removed from the schema, rule, and Zeitung meta.yml.
2. Per-frame opt-in `is_full_bleed=True` added to `_Frame` primitive.
3. Both `_BandConsistencyRule` and `_SpineSafetyRule` now skip frames where `is_full_bleed=True`.
4. Six user-cited geometry fixes applied:
   - Page 2 P1 Hero: x=20, w=170 (was -3 to 207).
   - Pages 10/11 P9 Spread halves: each at x=20, w=170 (was full-bleed).
   - Page 11 P10 Portrait: x=135.3, w=54.67, y_max≤283 (was full-bleed bottom + right).
   - Page 12 Dunkelgrün polygon extended down to y=297, P11 Bottom kept at content width (no white side borders, no spine bleed).
   - Page 14 P13 Hero + Dunkelgrün: symmetric bleed both sides (x=-3, w=216).
   - Cover (page 1) and back (page 14) feature frames opt out per-frame via `is_full_bleed=True`.

## Cross-check vs audit JSON (post-fix)

`bin/audit-alignment zeitung-a4-grun --json` reports **0 band_consistency_warnings** across all 14 pages. `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` exits 0. Audit-tool and Codex both agree.

## Iter3 supersedes iter2

The iter2 deferral to #26 (Codex prompt clarification for "page-title in header band vs body in header band") is RESOLVED by iter3's revised prompt, which explicitly calls out the page-title-in-header-band convention. Iter3 reads cleanly without confusion.

## Iteration count

3 of 2-budget — iter3 was added in response to the user's post-iter2 feedback that pages 2/10/11/12/14 had visible geometry bugs and that `excluded_pages` was an inappropriate workaround. Iter3 confirms the architectural fix.
