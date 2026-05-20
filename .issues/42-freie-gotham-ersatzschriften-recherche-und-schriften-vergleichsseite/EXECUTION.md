# Execution: Issue 42 — Freie Gotham-Ersatzschriften + Vergleichsseite

**Started:** 2026-05-20
**Status:** complete
**Branch:** issue/42-freie-gotham-ersatzschriften-recherche-und-schriften-vergleichsseite

## Execution Log

- [x] T1: 5 OFL-Schriften bündeln + Datenquelle anlegen — commit 5b26651
- [x] T2: Font-Tausch-SLA-Postprozessor tools/font_variants.py — commit 3f3e1c8
- [x] T3: Test für den Font-Tausch — commit ad08dad
- [x] T4: Rendering: Vergleichs-Artefakte + Build-Tool — commit 8ba89d5
- [x] T5: Schriften-Vergleichsseite — commit c2f96fe
- [x] T6: Verlinkung von der Startseite — commit 7e57c62
- [x] T7: Build ausführen, verifizieren, Artefakte committen — commit c2c0bd6

## Commands run and results

### Fonts (T1)
- Downloaded the five families from `raw.githubusercontent.com/google/fonts`
  (`ofl/<family>/`). Montserrat / Outfit / Urbanist / Raleway ship there only
  as `[wght]` variable fonts; Barlow Semi Condensed ships static weights.
- `git check-ignore` showed `.gitignore:27 *.ttf` blanket-ignores `.ttf`.
  Added a negation `!shared/fonts/alternatives/**/*.ttf` — the SIL-OFL files
  are intentionally redistributable (CONTEXT.md D4).

### Font instancing (T4 — deviation, see below)
- `tools/font_instantiate.py` pins the `wght` axis of the four VFs to
  Regular/Bold/ExtraBold/Black and rewrites the name table so each weight
  registers as `family=<Base>` / `subfamily=<Weight>`.
- Verified Scribus exposes the static instances: `getFontNames()` lists
  `Montserrat ExtraBold`, `Outfit Black`, … — exactly the names
  `font_variants.py` writes into the SLAs.

### Font substitution (T2)
- `python3 tools/font_variants.py --all` → 5 variant SLAs, 69 references
  each (68 `FONT` attributes + 1 `DOCUMENT/@DFONT`).
- Idempotent: a second run produces byte-identical SLAs (md5 unchanged).
- Each variant: 0 `Gotham Narrow`, `Minion Pro Regular` (×2) and
  `Vollkorn Black Italic` (×5) untouched.

### Tests (T3)
- `python3 -m pytest tools/sla_lib/tests/test_font_variants.py` → 5 passed.
- `python3 -m unittest discover -s tools/sla_lib/tests -p test_font_variants.py`
  → 5 passed (dual-runner gate green).
- Full suite `python3 -m pytest tools/sla_lib/tests/` → 809 passed,
  8 skipped, 0 failed — no regressions.

### Rendering (T4 / T7)
- **Scribus WAS available** in the executor environment — rendering ran.
  (`command -v scribus` came back empty in one shell, but `render_sla_to_pdf`
  drives `xvfb-run scribus …` and succeeded.)
- `python3 tools/fonts_compare_build.py` rendered every variant: per font a
  PDF + 6 thumbnail PNGs + 6 hi-res PNGs under
  `templates/flyer-a6-hochformat-gruenes-cover/fonts/<slug>/`, mirrored to
  `site/public/schriften/<slug>/`, and wrote `site/src/data/schriften.json`.
- `pdffonts` on every variant PDF confirms the intended family is embedded
  across all four weights (e.g. `MontserratRegular/Bold/ExtraBold/Black`),
  no DejaVu fallback. `Vollkorn-BlackItalic` is still embedded as expected.

### Lint / type-check
- `ruff check` on all four new/modified Python files — all checks passed.
- `mypy` on the new files reports only missing-stub `import-not-found`
  notes for `yaml` and `fontTools` (third-party packages without type
  stubs). This is the pre-existing project baseline — `tools/impressum.py`
  (the model for this work) shows the identical `yaml` finding. No project
  `mypy.ini`/config exists.

### Site build (T6 / T7)
- `npx astro build` in `site/` → 27 pages built, `Complete!`, no errors.
- `/schriften/index.html` generated with 30 preview anchors (6 pages ×
  5 fonts) and 6 page sections; the home page and header link to
  `schriften/`.

## Artifact counts

- 5 variant SLAs (one per font), 69 substituted references each.
- 5 PDFs, 30 thumbnail PNGs, 30 hi-res PNGs under `templates/.../fonts/`.
- Same 5 PDFs + 60 PNGs mirrored to `site/public/schriften/`.
- 1 data file `site/src/data/schriften.json` (5 fonts, 6 pages).
- 20 static font TTFs bundled (4 weights × 5 families) + 5 `OFL.txt`.

## Deviations from Plan

### [Rule 3 - Blocker] Variable fonts replaced with static per-weight TTFs

- **Found during:** T4 — first render produced DejaVu Sans fallback for
  Montserrat, Outfit and Raleway.
- **Cause:** PLAN T1 permitted bundling the `[wght]` variable fonts. But
  Scribus exposes a variable font under a single name (its default named
  instance — e.g. `Montserrat Thin`), so the four distinct
  `"<Family> <Weight>"` references in a variant SLA cannot all resolve;
  three of four weights collapse to the default and the comparison loses
  weight differentiation.
- **Fix:** Added `tools/font_instantiate.py`, which instantiates static
  per-weight TTFs from the VFs with `family=<Base>` / `subfamily=<Weight>`
  — the exact shape Barlow Semi Condensed already ships. The four VFs were
  replaced in `shared/fonts/alternatives/<slug>/` by their static weights
  and `alternatives.yml` `files:` lists updated to match.
- **Why this beats a fontconfig alias:** an alias mapping
  `"Montserrat ExtraBold"` → `family=Montserrat + weight=…` makes `fc-match`
  resolve, but Scribus enumerates fonts by their TrueType name table, not
  fontconfig patterns, so it still would not see four weights. Static
  instances are the only robust fix and they keep the renderer
  alias-free. (An alias conf was briefly added then removed once the
  static-instance approach proved out.)
- **Plan impact:** none on scope — still exactly five fonts, still bundled,
  still SIL OFL. PLAN T2's contingency ("create a fontconfig alias if a
  family has no standalone weight family names") is satisfied differently
  but equivalently: the instances themselves carry standalone weight
  family names.

### [Note] T2 commit message wording

- The T2 commit message says "68 references each"; the committed SLAs
  actually carry 69 (the `DFONT` default-font attribute is also remapped,
  added in the same task before commit). The SLAs are correct; only the
  message bullet undercounts by one. Left as-is rather than rewriting
  history.

## Discovered Issues

- `Minion Pro Regular` (Adobe, proprietary) is also referenced by the flyer
  and blocks "freely shareable" the same way Gotham does. Out of scope here
  — already flagged in RESEARCH.md §3 as a follow-up issue.
- The actual swap of Gotham in the production templates is the planned
  follow-up issue (CONTEXT.md D1) — not done here by design.

## Self-Check

- [x] All files from the plan exist (data source, 3 tools, test, page, JSON)
- [x] All 7 task commits exist on the branch
- [x] Full test suite passes (809 passed, 0 failed); dual-runner gate green
- [x] `ruff` clean on all new Python; `mypy` only the pre-existing
      third-party missing-stub notes
- [x] `npx astro build` succeeds — `/schriften/` page generated
- [x] No stubs, TODOs or placeholders in new files
- [x] No leftover debug code
- **Result:** PASSED

**Completed:** 2026-05-20
**Commits:** 7 task commits (5b26651, 3f3e1c8, ad08dad, 8ba89d5, c2f96fe,
7e57c62, c2c0bd6) + this execution log.

## Follow-up — Original column (2026-05-20)

The comparison showed only the five free alternatives. The original flyer
in the proprietary **Gotham Narrow** — the baseline the alternatives are
meant to be measured against — was added as the **first** column.

### What changed

- `tools/fonts_compare_build.py`: the original is a dedicated build-tool
  special case (`ORIGINAL_ENTRY`), **not** an entry in
  `shared/fonts/alternatives.yml`. That file is, by definition, the list of
  *free SIL-OFL* alternatives; Gotham Narrow is neither free nor an
  alternative, so modelling it as a constant keeps the data source honest
  and leaves the five-font test (`test_five_entries_each_complete`,
  expects exactly 5) untouched.
- New `mirror_original()` copies the flyer's own committed `page-NN.png` /
  `-hires` renders and `preview.pdf` verbatim into
  `site/public/schriften/original/` — the original is **never re-rendered**.
- `build_data()` emits the original as the first `fonts` entry and the
  first per-page preview, with an `original: true` flag and no variant SLA.
- `site/src/pages/schriften/index.astro`: legend + grid now render
  Original + 5 alternatives. The original is flagged proprietary with an
  honest German summary; the lightbox switches through all six versions
  per page. Label separator changed from ` — ` to ` · ` so the
  dash-bearing name "Original — Gotham Narrow" is recovered correctly.

### New per-row column count

**6** — one Original (Gotham Narrow) + five free alternatives. 6 flyer
pages × 6 columns = 36 preview thumbnails; the lightbox steps through 6
font versions per page.

### Verification

- `python3 tools/fonts_compare_build.py` → re-emitted variant SLAs
  (idempotent, byte-identical), copied 6 original page renders +
  `preview.pdf`, wrote `schriften.json` (6 columns, original first).
- `ruff check tools/fonts_compare_build.py` → all checks passed.
- `python3 -m pytest tools/sla_lib/tests/test_font_variants.py` → 5 passed;
  `python3 -m unittest discover` → 5 passed (dual-runner gate green).
- `npx astro build` in `site/` → 27 pages, `Complete!`;
  `/schriften/index.html` has 36 `schrift-preview` anchors and a
  `repeat(6, 1fr)` grid.

### Deviations

- The five variant PDFs re-render with a fresh embedded `/CreationDate`
  each run (timestamp-only churn; PNGs stay byte-identical). They were
  reverted so the diff carries only the genuine original-column change —
  the five free fonts' artifacts are visually unchanged.

**Follow-up commits:** e9e4008 (build tool + page), a4bc93e (regenerated
artifacts), + this log update.
