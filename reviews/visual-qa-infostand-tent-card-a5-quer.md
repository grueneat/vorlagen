# Gate 3 — Visual QA: infostand-tent-card-a5-quer

**Date:** 2026-05-07
**Render:** `page-01.png` at 100 DPI (single page, both panels visible flat).
**Iterations:** 3 (iter-1 spec-mismatch geometry 273mm; iter-2 corrected to 223mm + Panel B coords; iter-3 logos embedded).

## Iter-1 → Iter-2 → Iter-3 vorher/nachher

| | Iter-1 | Iter-2 | Iter-3 |
|---|---|---|---|
| Headline width | 273 mm (full-width, no logo room) | 223 mm (room for logo) ✓ | 223 mm |
| Panel B coords | x=285 (off-page) | x=235 (post-rotation bbox) ✓ | unchanged |
| Logo Panel A | none | none | cmyk top-left ✓ |
| Logo Panel B | none | none | cmyk bottom (rotated) ✓ |
| Falz-Linie | y=105 ✓ | ✓ | ✓ |

## Final State

- **merge_ready: yes**
- **comparison_to_existing:** Tent-Card is the **only 3D-readable template** in the
  gallery. Existing 3 are flat. Closest analog is the Plakat (which is also one-sided
  but printed flat). Tent-Card's bilingual DE/EN layout covers tourist towns and
  university campuses — a use case the existing 3 cannot.
- **hierarchy_readability:** Panel A: Logo + Headline + 3 bullets + Impressum. Panel B:
  rotated mirror in English. 1-second test on each panel passes — "Klimaschutz konkret"
  reads from the front, "Climate. Concrete." from the back.
- **brand_consistency:** Pass. Same Vollkorn-Black-Italic 36pt headline, Gotham 14pt
  body, Dunkelgrün/Black color discipline.
- **wahlkreuz_background_color_check: n/a** (no Wahlkreuz on this template by design).
- **print_risks:** Bottom 3 mm contact zone clear (Impressum at y=96..100 mm, well above
  the y=102..105 contact zone). Falz-Linie at y=105 on Falz-Layer (printable=False) —
  Druckerei sees the path as fold-instruction. ImageMagick `pdftotext` extraction confirms
  both DE and EN bullets render correctly.

## Where it's better than the existing 3

- **First 3D template:** Tisch-Aufsteller use case for Infostand / Pfarrkaffee / Veranstaltung-
  Tisch. Existing 3 cannot do this.
- **Bilingual reach:** DE/EN dual-language out of the box. Existing 3 are DE-only.
- **Falz-Layer pattern:** establishes the Falz spot-color document-local pattern. Reused
  by the Falzflyer template.

## Three concrete improvements (deferred)

1. Optional Hellgrün accent on Panel A right edge to lift the all-white panel from
   "blank canvas" to "designed".
2. Body 14pt × 223mm gives ~110 chars/line — bullets save lesbarkeit but a single
   sentence body would benefit from a smaller frame width.
3. Add a fallback for end-users who only want one language: spec could note
   "duplicate Panel A content if DE-only is desired".

**Final consensus:** merge-ready. First 3D-readable template; bilingual layout works;
fold mechanics correct.
