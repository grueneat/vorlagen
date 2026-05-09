# Zeitung A4 — visual alignment audit (all 14 pages)

Read each rendered preview page in
`templates/zeitung-a4-grun/page-{01,02,03,04,05,06,07,08,09,10,11,12,13,14}.png`
(zero-padded; 14 pages total). You MUST open each PNG file and visually
inspect it. Do not skip pages. Do not infer content from filenames.

For EACH page, enumerate every alignment defect you observe. Report
neutrally — do not assume any particular defect class is more or less
likely. Use this Markdown structure per finding:

- Page: NN
- Type: bleed-gap | letterbox | flush-mismatch | column-axis-drift | spread-seam | partial-overlap | other
- Frames involved: <verbal description by visual position; frame names if recognizable from layout>
- What's wrong: <one factual sentence>
- Drift estimate: <X mm if measurable, else "qualitative">
- Severity: ERROR (visible after print cut) | WARNING (visible but not catastrophic)

If a page has no defects, write `- Page: NN — clean`.

End the report with a single verdict block:

<verdict value="pass|fail" critical=N high=N medium=N>

`pass` = no ERROR findings; `fail` = at least one ERROR finding.

Source context: this template is a 14-page A4 facing-pages newsletter.
Pages are 210x297 mm with 3 mm bleed on all outer edges. Inner edges
(spine) are at the page boundary. Facing-pages spreads share content
across two pages.

Output the structured list AS YOUR PRIMARY MESSAGE; do not just save
to disk. Do NOT consult any rule/audit JSON; read the images fresh.
