# Zeitung A4 — band-consistency visual audit

Read each rendered preview page in
`templates/zeitung-a4-grun/page-{01,02,03,04,05,06,07,08,09,10,11,12,13,14}.png`
(zero-padded; 14 pages total). You MUST open each PNG and visually
inspect it. Do not skip any page. Do not infer content from filenames.

## The architecture

Issue #25 pins the OUTER STRUCTURE of every body-pool page so any
LEFT body page can be combined with any RIGHT body page in a printed
spread (Bezirksgruppen shuffle pages freely):

- **HEADER band**: y=20-49 mm. Reserved for page-title content —
  this is the BIG GREEN HEADLINE that introduces the article on the
  page (e.g. "Aufzählungen? Check!", "Personen können näher
  vorgestellt werden"). It IS the page's title; the band is its
  designated zone. **Do NOT flag a big green headline at y≈20-48
  as "body content in header band" — that frame IS the page title
  and is correctly placed.**
- **FREE zone**: y=49-283 mm. Contains body content (3-col text
  grid, sub-article headlines, secondary green headlines mid-page,
  inline images, photo grids). Each page chooses its own free-zone
  layout; that variation is intentional.
- **FOOTER band**: y=283-297 mm. Reserved for the page number /
  small footer text. No body content extends into this zone.
- **L/R margins**: 20 mm on each side. Body content (text + image)
  stays within x=20 to x=190 on every body-pool page.

## Per-frame opt-out (NEW in this iteration)

Pages 1 (cover), 2 (P1 Hero), 10/11 (P9 Spread halves), 14 (back
cover) historically had full-bleed feature treatments that crossed
band boundaries. Those frames are now individually marked
`is_full_bleed=True` in the build script and **the audit-tool does
not check them**. There is no per-page exclusion — every page's
ordinary content frames ARE checked. You should still visually
verify the rule's spirit:

- The full-bleed feature frame on pages 1, 2, 10, 11, 14 may
  legitimately bleed past bands/margins (cover photo, hero photo,
  spread half, back-cover photo). Don't flag them.
- Other content on those same pages (body text, page-title-style
  headlines, decoration polygons) should still respect the bands
  and margins where applicable.

## User-cited fixes — verify these specifically

- **Page 2 P1 Hero**: should match content width (~170 mm =
  x=20 to x=190), NOT extend to full bleed. Confirm the hero
  photo's left and right edges align with the body grid below.
- **Page 10 P9 Spread (left half)** and **Page 11 P9 Spread (right
  half)**: each half should be at content width (x=20 to x=190),
  NOT bleeding past page edges and NOT spilling across the spread
  spine.
- **Page 11 P10 Portrait**: the woman-portrait photo should sit
  INSIDE the right text column (x=135.3 to x=190) and stop ABOVE
  the footer band (y_max ≤ 283), NOT bleed off the bottom or right.
- **Page 12 P11 Bottom**: the photo should sit on the green
  background with NO white borders on left/right. The Dunkelgrün
  polygon now extends down to cover the entire page; the image
  remains at content width but appears ON GREEN.
- **Page 14 P13 Hero**: back-cover photo should have SYMMETRIC
  margins on left and right (both bleed equally, OR both stop at
  the page edge — not asymmetric).

## What to report

For each finding, structure as:

- Page: NN
- Frame (visual location): "<description>"
- What's wrong
- Severity: ERROR (band intrusion / margin overrun on body content
  that should comply) | WARNING (sub-1mm drift)

End with verdict:

```
<verdict value="pass|fail" findings=N>
  <one-paragraph summary>
</verdict>
```

`pass` = no ERROR findings; the user-cited fixes are visible AND
the band model holds for body-pool content. `fail` = any finding
that contradicts the architecture above.

## CRITICAL — DO NOT FLAG

- Big green page-title headlines at y≈20-48 are the HEADER band
  content by design. They are NOT body content drifting into the
  header band.
- Full-bleed feature frames on pages 1, 2, 10, 11, 14 (Cover Hero,
  P1 Hero, P9 Spread halves, P13 Hero) — these are intentional
  per-frame opt-outs.
- Background-decoration polygons (full-bleed Dunkelgrün, Hellgrün,
  Magenta, Gelb fields) — they are background, not content.
- Letterboxing / scale_type issues / INJECT_MAP drift — resolved
  in Issue #24, out of scope here.
- Axis-x / axis-y adjacency drift between unrelated frames —
  covered by `brand:visual_adjacency_drift` (#22/#23), out of
  scope here.
- Z-order, contrast, crop focus, hyphenation, font sizing — out of
  scope.

## Source context

14-page A4 facing-pages newsletter. Pages 210×297 mm with 3 mm
bleed. Read the images fresh; do not consult any rule/audit JSON.

Output the structured per-page list AS YOUR PRIMARY MESSAGE.

Reference: Issue #25.
