# Zeitung visual alignment audit

Read the rendered preview pages at `templates/zeitung-a4-grun/page-01.png`
through `page-14.png` (zero-padded filenames; 14 pages total) and
identify alignment issues per page. You MUST open each PNG file and
visually inspect it — do not skip pages.

For each issue produce a structured Markdown entry:

- Page: NN
- Type: bleed-gap | flush-mismatch | partial-overlap | column-axis-drift | spread-seam | other
- Frames involved (best-effort identification by visual position): "<description>"
- What's wrong: short factual description (e.g., "image leaves 3 mm white margin on right edge after print cut")
- Severity: ERROR (visible after print cut) | WARNING (visible but not catastrophic)

Focus on:
1. Full-width frames that don't extend to the bleed (3 mm outside the page edge) on outer edges.
2. Image frames inside colored polygons that are NOT flush with the polygon edges (asymmetric inset = drift).
3. Text frames that partially overlap colored polygons (text crossing the polygon boundary).
4. Adjacent frames whose edges should align (left/right/top/bottom) but visibly drift.
5. Spread images whose seam at the spine doesn't line up correctly.

KNOWN issues (from prior audit) to specifically check for visually:
- Page 1: cover image vs full-bleed Dunkelgrün band on top — does the
  cover image extend to the same outer edges as the band?
- Page 8: portrait photo on the right side, sitting inside a Dunkelgrün
  card — is the portrait flush with all 4 edges of the card, or are
  there asymmetric gaps?
- Page 10: lower half has a Dunkelgrün card; do the body-text columns
  end above the card or do they overlap into it?
- Page 11: portrait photo bottom-right — does it extend all the way to
  the right print edge (outer bleed) or does it stop short?
- Pages 2, 5, 12, 13, 14: full-width image frames or colored bands —
  do they reach the outer edge (LEFT page → left edge; RIGHT page →
  right edge)?

Do NOT verify against any rule output — read the images fresh. Output
the structured list AS YOUR PRIMARY MESSAGE (do not just save to disk).

Reference: Issue #23 in
`.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/`.
