# Zeitung A4 — band-consistency visual audit

Read each rendered preview page in
`templates/zeitung-a4-grun/page-{01,02,03,04,05,06,07,08,09,10,11,12,13,14}.png`
(zero-padded; 14 pages total). You MUST open each PNG and visually
inspect it. Do not skip any page. Do not infer content from filenames.

For each page, verify the band model:

- HEADER band: y=20-49 mm. Should contain ONLY the page number, date,
  breadcrumb header. No body content (text columns, column body) should
  appear above y=49.
- FOOTER band: y=283-297 mm. Should contain ONLY the page number /
  small footer text. No body content (full-width photos, body text)
  should appear below y=283.
- LEFT/RIGHT margins: 20 mm on each side. Body content (text + image)
  should not extend past x=20 or x=190.
- BACKGROUND DECORATION: full-bleed Dunkelgrün or Hellgrün polygons
  CAN extend past these bands — they are decoration, not content. Do
  NOT flag them.
- FEATURE PAGES (1, 2, 10, 11, 14): excluded from the band rule. These
  are cover, hero spread, and back. Do NOT flag content extents on
  these pages.

For each finding on the body-pool pages (3, 4, 5, 6, 7, 8, 9, 12, 13),
report:

- Page: NN
- Frame (visual location): "<top-half image | bottom-band photo |
  middle text-column | etc>"
- What's wrong: brief factual description
- Likely y or x value (estimated from PNG)
- Severity: ERROR (extends into header/footer band, breaks
  combinability) | WARNING (margin drift < 5mm)

Spread-baseline check: for each spread (LEFT + RIGHT pair), verify
that:

- Headlines (top of body content in free zone) start at the same y on
  both pages.
- Page numbers / footers are at the same y on both pages.

End with verdict:

```
<verdict value="pass|fail" body_pool_findings=N spread_baseline_findings=N>
  <one-paragraph summary>
</verdict>
```

`pass` = no ERROR findings on body-pool pages; `fail` = at least one
ERROR finding on a body-pool page.

CRITICAL — DO NOT RE-REPORT prior-issue defect classes:

- Do NOT report letterboxing, full-bleed gap, or scale_type mismatch
  ("white margin where photo doesn't reach edge") — these are
  resolved in Issue #24.
- Do NOT report INJECT_MAP target drift — also resolved in #24.
- Do NOT report axis-x/axis-y same-axis drift between adjacent frames
  (covered by #22/#23 brand:visual_adjacency_drift; out of scope here).
- Do NOT report z-order, contrast, crop_focus, hyphenation, or
  font-size — out of scope for #25.

Source context: this template is a 14-page A4 facing-pages newsletter.
Pages are 210x297 mm with 3 mm bleed. Inner edges (spine) at the page
boundary. Issue #25 introduces a band-consistency rule that pins the
OUTER STRUCTURE (header band + free zone + footer band + L/R margins)
of every body-pool page so any LEFT page can pair with any RIGHT page.
Variation in the free zone (3-col text grid / image-top / image-bottom
/ photo grid) is intentional; only band intrusion + margin drift on
body content is in scope.

Output the structured per-page list AS YOUR PRIMARY MESSAGE. Do not
just save to disk. Do NOT consult any rule/audit JSON; read the images
fresh.

Reference: Issue #25.
