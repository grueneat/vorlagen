# Research: Vorlagen auf Barlow Semi Condensed umstellen, Fremdschriften + Schriftvergleich entfernen, Baselines neu erzeugen

**Researched:** 2026-06-07
**Issue:** c8bg0
**Confidence:** HIGH (font swap, provisioning, render workflow, removal map all verified end-to-end on the live dev container; one residual risk class = baseline/tolerance regeneration)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (do NOT re-litigate)
1. **One font: Barlow Semi Condensed; everything else out.** All templates use
   *only* Barlow Semi Condensed. Weight mapping (Barlow cuts Regular/Bold/ExtraBold/Black):
   | Alt | Neu |
   | :-- | :-- |
   | Gotham Narrow Book | Barlow Semi Condensed Regular (400) |
   | Gotham Narrow Bold | Barlow Semi Condensed Bold (700) |
   | Gotham Narrow Black | Barlow Semi Condensed **Black** (900) |
   | Gotham Narrow Ultra | Barlow Semi Condensed **Black** (900) |
   | Minion Pro / Times Roman / Tahoma | Barlow Semi Condensed (passender Schnitt) |
   | **Vollkorn (Black/Bold Italic)** | **Barlow Semi Condensed** (Black; ggf. Italic falls Akzent nötig) |
   - **Vollkorn is replaced too** — explicit user instruction ("alle anderen Schriften raus").
     Do not re-litigate. If a cursive accent is needed, a Barlow-Italic TTF must be pulled in
     (NONE exists locally today — see Risk R6).
2. **Local font provisioning = deliberate print-pipeline exception to no-vendoring.**
   Barlow is SIL OFL; provision it as a local TTF for fontconfig/Scribus via `Dockerfile.claude`.
   No CDN/webfont for PDF generation. `fc-match "Barlow Semi Condensed"` must return a Barlow TTF.
3. **Remove the whole Schriftvergleiche feature** (page, data, build tool, generated artifacts,
   nav link, alternative fonts). `tools/font_variants.py` only removed if used nowhere else.
4. **Visual review of EVERY rendered page before baseline sign-off.** Barlow is narrower →
   shifted line-breaks/centering. Multiple visual passes; fix template, re-render until clean.
   `bin/audit-alignment` / `bin/check-fontsizes` as helpers.
5. **New baselines only after sign-off.** Promote freshly-rendered PDFs to `baseline.pdf`
   (and `*-original.pdf` where sensible). Adjust `TOLERANCES.yml`. Keep previews/PNGs +
   staleness metadata consistent (CI stale-previews gate green).

### Claude's Discretion
- Exact fontconfig provisioning details (alias-vs-none), Dockerfile sanity-check shape.
- Whether/how to adjust per-template `TOLERANCES.yml` and whether to rebaseline the 3 `*-original.sla`.
- Whether to delete `font_variants.py`/`font_instantiate.py` (gated on usage — see findings).

### Deferred Ideas (OUT OF SCOPE)
- Re-choosing the font (decided in #42).
- Pulling a Barlow italic (only IF an accent actually needs it; otherwise skip).

### Process
- Autonomous pipeline, no plan-gate. No tool attribution in commits/code (CLAUDE.md hard rule).
</user_constraints>

## Summary

The swap is mechanical and **end-to-end verified on the live container**: I patched
`postkarte-a6-kampagne/build.py` to Barlow, ran `build.py` → `template.sla`, rendered with the
sanctioned `xvfb-run … scribus -g -ns -py tools/_export_pdf.py` pipeline, and `pdffonts` shows
all three Barlow weights embedded with **zero DejaVu fallback**. Scribus enumerates the four
Barlow faces under exactly the strings the build code must use — `Barlow Semi Condensed
Regular / Bold / Black / ExtraBold` (confirmed via `scribus.getFontNames()`). The only
provisioning step needed is installing the four committed Barlow TTFs into fontconfig; **no
fontconfig family-alias is required for Scribus** (unlike Vollkorn) because Scribus reads the
TTF name table directly and "Barlow Semi Condensed Black" already resolves natively.

Fonts live in three layers that all must be changed: (a) the per-template `build.py` files
(16 of them — 7 distinct non-Barlow family strings, ~1100 references), (b) the three top-level
`*-original.sla` InDesign-derived oracles, and (c) **two library-level defaults** the prior map
missed: `tools/sla_lib/builder/brand.py` (`deffont="Gotham Narrow Book"`) and the brand
allow-list `shared/ci.yml::fonts`. The committed `template.sla` files regenerate from `build.py`,
so editing build.py is the source-of-truth edit; sla_diff will NOT block the swap (all 3
templates with an `original_sla` already have `sla_diff_strict: false`; the other 13 are DSL-only
with no original).

The hard part is **not** the swap — it is step 4/5: Barlow's narrower metric shifts line-wrap and
centering, which invalidates the existing per-template `TOLERANCES.yml` drift budgets (they encode
Gotham-vs-InDesign cross-renderer wrap deltas). New baselines must be promoted from the freshly
rendered previews after page-by-page visual review, and tolerances re-derived. CI never renders —
it only runs the SHA-based stale-previews gate (auto-updated by `render-gallery`) plus a
non-blocking brand validator — so all baselines/previews are produced locally and committed.

**Primary recommendation:** (1) Add the 4 Barlow TTFs to the Docker font install + Barlow
sanity-check (no alias). (2) Replace the 7 font strings in all 16 build.py + 3 original.sla +
`brand.py` deffont + `shared/ci.yml` per the locked weight map. (3) `bin/render-gallery
--skip-visual-diff` to rebuild all template.sla/PDF/PNGs (meta SHAs auto-update). (4) Visual-review
all ~72 pages, fix overflow/centering, re-render. (5) Promote previews → baselines, re-derive
`TOLERANCES.yml`, then `bin/render-gallery` (no skip) + `bin/check-stale-previews` must be green.
(6) Delete the whole Schriftvergleiche feature incl. its unit test.

## Codebase Analysis

### Relevant Code
| File | Purpose | Relevance |
|------|---------|-----------|
| `templates/<slug>/build.py` (16) | DSL source of truth → emits `template.sla` | **Primary edit target** (font= / deffont=) |
| `gruene-zeitung-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `postkarte-vorlage-original.sla` | InDesign-derived oracle SLAs (top of repo) | Edit FONT/DFONT; sla_diff oracles |
| `tools/sla_lib/builder/brand.py:74,145` | `Brand.deffont = "Gotham Narrow Book"` library default | **Must change to Barlow** (prior map missed this) |
| `shared/ci.yml` (lines 47-52 `fonts:`, 61-113 `styles:`) | Brand allow-list + ci/* style fonts | Update to Barlow (validator informational but should be correct) |
| `tools/sla_lib/builder/brand_constraints.py:170` | `_FontFamilyRule` checks Run fonts ∈ ci.yml::fonts | Drives the allow-list; non-blocking in CI |
| `Dockerfile.claude:96-118` | Font install + Vollkorn alias + sanity-check | **Add Barlow install + sanity-check** |
| `shared/fonts/alternatives/barlow-semi-condensed/*.ttf` | 4 committed Barlow TTFs (OFL) | Source of the provisioned fonts |
| `tools/render_pipeline.py` / `bin/render-gallery` | Render orchestration; auto-updates meta SHAs | The render command |
| `tools/visual_diff.py:render_sla_to_pdf` (~line 195-210) | `xvfb-run … scribus -g -ns -py tools/_export_pdf.py` | Headless render mechanics |
| `bin/check-stale-previews` / `tools/check_stale_previews.py` | SHA(template.sla)==meta gate (CI gate) | Auto-green after re-render |
| `templates/<slug>/meta.yml` | `build_py_sha256`, `previews_for_sla`, `sla_diff_strict`, `original_sla` | Auto-updated by render-gallery |
| `templates/<slug>/baseline.pdf` + `diff.yml` + `TOLERANCES.yml` | Visual-diff target + tolerances | **Rebaseline + re-derive tolerances** |
| `docs/render-fidelity.md:108-151` | Documented rebaseline procedure | Baseline-promotion recipe |

### Interfaces
<interfaces>
// ── EXACT Scribus font names (verified via scribus.getFontNames() on the container) ──
// These are the strings build.py/SLA must reference. Scribus reads the TTF name
// table directly; once installed in fontconfig these four resolve natively.
"Barlow Semi Condensed Regular"
"Barlow Semi Condensed Bold"
"Barlow Semi Condensed Black"
"Barlow Semi Condensed ExtraBold"   // available but UNUSED under the CONTEXT weight map

// ── Barlow TTF name tables (fc-scan) — explains fc-match behaviour ──
// BarlowSemiCondensed-Regular.ttf : family="Barlow Semi Condensed"            style="Regular"
// BarlowSemiCondensed-Bold.ttf    : family="Barlow Semi Condensed"            style="Bold"
// BarlowSemiCondensed-Black.ttf   : family="Barlow Semi Condensed,Barlow Semi Condensed Black" style="Black,Regular"
// BarlowSemiCondensed-ExtraBold.ttf: family="Barlow Semi Condensed,Barlow Semi Condensed ExtraBold" style="ExtraBold,Regular"
// fc-match consequence (no alias): "Barlow Semi Condensed Black"/"…ExtraBold" → resolve;
//   "Barlow Semi Condensed Regular"/"…Bold" → DejaVu fallback at fc-match level.
//   But Scribus does NOT use fc-match family lookup for these — it scans the name
//   table — so all four render correctly. (Verified by pdffonts on a real render.)

// ── Document / Brand DSL (tools/sla_lib/builder/) ──
// document.py:152
def Document(..., deffont: str = "Gotham Narrow Book", defsize: int = ..., ...)
// brand.py:74,145
@dataclass class Brand: deffont: str = "Gotham Narrow Book"   // ← change to Barlow Regular
Brand.gruene_noe()  // factory used by all build.py; sets deffont="Gotham Narrow Book"

// styles.py:41,108 / primitives.py:322 — font carried on:
class CharStyle:  font: Optional[str]
class ParaStyle:  font: Optional[str]
class TextFrame:  font: Optional[str]
class Run:        font: Optional[str]   // a text-bearing Run's own font wins

// ── ci.yml schema (shared/ci.yml) — the brand allow-list ──
fonts: [ "Gotham Narrow Book", "Gotham Narrow Bold", "Gotham Narrow Black",
         "Gotham Narrow Ultra", "Vollkorn Black Italic" ]   // ← replace with Barlow set
styles: ci/default, ci/headline-ultra, ci/headline-vollkorn-italic, ci/body-12,
        ci/body-11, ci/impressum, ci/stoerer, ci/cta   // each has a font: field to update

// ── Headless render contract (tools/visual_diff.py) ──
def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None
//   → xvfb-run -a --server-args="-screen 0 1024x768x24" \
//       scribus -g -ns -py tools/_export_pdf.py <sla_abs> <pdf_abs>
//   tools/_export_pdf.py: scribus.openDoc(in); PDFfile().save() → out (silent font sub on miss)

// ── render-gallery CLI (tools/render_pipeline.py main) ──
bin/render-gallery [TEMPLATE_ID] [--skip-visual-diff] [--visual-diff-warning-only]
                   [--dry-run] [--audit] [--audit-strict]
//   no TEMPLATE_ID → all renderable templates; auto-updates meta.yml
//   build_py_sha256 + previews_for_sla after each render.

// ── stale gate (tools/check_stale_previews.py) ──
bin/check-stale-previews   // FAIL if sha256(build.py)!=meta.build_py_sha256
                           //      or sha256(template.sla)!=meta.previews_for_sla
</interfaces>

### Font-string inventory (VERIFIED, with counts)

**In `templates/*/build.py` (16 files), distinct `font=`/`deffont=` strings:**
| Font string | refs (build.py) | Maps to |
|-------------|-----------------|---------|
| `Gotham Narrow Book` | 612 | Barlow Semi Condensed Regular |
| `Gotham Narrow Ultra` | 118 | Barlow Semi Condensed Black |
| `Gotham Narrow Black` | 82 | Barlow Semi Condensed Black |
| `Vollkorn Black Italic` | 53 | Barlow Semi Condensed Black |
| `Gotham Narrow Bold` | 39 | Barlow Semi Condensed Bold |
| `Minion Pro Regular` | 16 | Barlow Semi Condensed Regular |
| `Times Roman` | 8 | Barlow Semi Condensed Regular |
| `Vollkorn Bold Italic` | 2 | Barlow Semi Condensed Bold (or Black) |
- `deffont='Gotham Narrow Black'` explicitly set in 3 build.py: `postkarte-a6-kampagne:34`,
  `zeitung-a4:34`, `plakat-a1-hochformat:33`. The other 13 inherit `Brand.gruene_noe()` deffont.
- **No Tahoma** appears as a template font anywhere (Tahoma is only a *negative example* in the
  comparison feature). Acceptance-criterion grep for "tahoma" over `templates/`/`*.sla` is already
  clean of font usage.

**In all template `*.sla` (`template.sla` + 3 top-level `*-original.sla`), distinct FONT/DFONT:**
| FONT string | count |
|-------------|-------|
| `Gotham Narrow Book` | 746 |
| `Gotham Narrow Ultra` | 174 |
| `Gotham Narrow Black` | 93 |
| `Vollkorn Black Italic` | 78 |
| `Gotham Narrow Bold` | 70 |
| `Minion Pro Regular` | 16 |
| `Times Roman` | 8 |
| `Vollkorn Bold Italic` | 2 |
| `Gotham Narrow Ultra Italic` | 1 (in `postkarte-vorlage-original.sla` only) |
| `DFONT="Gotham Narrow Book"` | 13 |
| `DFONT="Gotham Narrow Black"` | 9 |
- **Correction to prior map:** DFONT is NOT uniformly "Gotham Narrow Black" — `template.sla`
  files carry `DFONT="Gotham Narrow Book"` too. And there is **one extra family
  string — `Gotham Narrow Ultra Italic`** (postkarte original) the map didn't list.
- The committed `template.sla` files regenerate from `build.py`, so they are NOT hand-edited;
  re-running `render-gallery` rewrites them. Only the 3 `*-original.sla` need direct SLA edits.

### Reusable Components
- `bin/render-gallery` (render all/one), `bin/check-stale-previews` (SHA gate),
  `bin/audit-alignment` (Issue #22 alignment audit, informational), `bin/check-fontsizes`
  (fractional FONTSIZE regression in PAGEOBJECT subtrees), `tools/font_audit.py`
  (pdffonts preview-vs-baseline; flags silent fallback/missing variants).
- `docs/render-fidelity.md:108-151` "Rebaselining a template's baseline.pdf (gated procedure)".

### Potential Conflicts
- `tools/sla_diff.py` compares `FONT` attributes (`_DEFAULTSTYLE_ATTRS`/`_ITEXT_ATTRS` both
  include "FONT", lines ~818-821). **But** the 3 templates with an `original_sla`
  (postkarte/plakat/zeitung-a4) **all set `sla_diff_strict: false`** → sla_diff is SKIPPED in
  CI for them, and the other 13 have no original → no sla_diff at all. So sla_diff will NOT
  block the swap. (Still, editing the `*-original.sla` fonts to match keeps the oracle honest.)
- `_FontFamilyRule` (brand_constraints) flags any rendered Run whose font ∉ `ci.yml::fonts`. It
  runs in CI via `check_ci.py` but with `|| true` (informational). Update `ci.yml::fonts` anyway.

## Standard Stack
| Library | Version | Purpose | Why Standard | Confidence |
|---------|---------|---------|--------------|------------|
| Barlow Semi Condensed | static OFL TTFs (Regular/Bold/ExtraBold/Black) already in repo | The single template font | Locked in #42; OFL → print-pipeline vendoring OK | HIGH |
| Scribus | 1.6.5 (container) | Headless SLA→PDF render | Existing pipeline | HIGH |
| fontconfig + xvfb-run | container | Font resolution + headless display | Existing pipeline | HIGH |
| poppler `pdffonts`/`pdftoppm` | container | Embedded-font audit + rasterise | Existing pipeline | HIGH |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Install Barlow via `COPY fonts/` drop-zone | `COPY shared/fonts/alternatives/barlow-semi-condensed` (committed) | Drop-zone is gitignored/user-supplied; the committed alternatives dir is in-repo and reproducible → **prefer copying from a committed path** (or move TTFs to a committed `fonts/barlow-semi-condensed/`). |
| No fontconfig alias (Scribus resolves natively) | Add Barlow family-aliases like Vollkorn | Verified unnecessary for Scribus; an alias is only cosmetic for `fc-match` parity. **Recommend: no alias.** |

## Don't Hand-Roll
| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Render SLA→PDF headless | Custom scribus invocation | `tools/visual_diff.py::render_sla_to_pdf` / `bin/render-gallery` | Handles abs-paths, xvfb, env, output assertion |
| Detect DejaVu/missing-font fallback | Manual pdffonts parsing | `tools/font_audit.py` (Phase D6, run via `render-gallery --audit`) | Already flags silent fallback |
| Keep stale gate green | Hand-edit meta SHAs | `bin/render-gallery` auto-updates `build_py_sha256` + `previews_for_sla` | Deterministic, scrubbed PDFs |
| Promote baseline | Ad-hoc cp | `docs/render-fidelity.md:118-131` recipe (render → pdffonts check → `bin/validate`) | Documented gated procedure |

## Architecture Patterns

### Recommended Approach (ordered)
1. **Provision Barlow (Dockerfile.claude:96-108).** Ensure the 4 Barlow TTFs land in
   `/usr/local/share/fonts/gruene/`. Simplest: copy from the committed
   `shared/fonts/alternatives/barlow-semi-condensed/` (or relocate to a committed
   `fonts/barlow-semi-condensed/`). Extend the post-install sanity grep to also require Barlow
   faces (e.g. `fc-list | grep -ci 'barlow semi condensed'` ≥ 4) and add a
   `fc-match "Barlow Semi Condensed" | grep -qi barlow` assertion. **No alias conf needed.**
   *(On the live container the fonts are already installed from my session; the Dockerfile change
   makes it reproducible.)*
2. **Swap font strings.** In all 16 build.py: replace the 7 strings per the weight map (incl. the
   3 explicit `deffont='Gotham Narrow Black'` → Barlow Black). Change `brand.py` `deffont` default
   (×2). In the 3 `*-original.sla`: replace FONT/DFONT incl. the lone `Gotham Narrow Ultra Italic`.
   Update `shared/ci.yml::fonts` + the `ci/*` style `font:` fields.
3. **Rebuild & render.** `bin/render-gallery --skip-visual-diff` (skip diff vs the now-stale
   Gotham baselines). This regenerates every `template.sla`, `preview.pdf`, page PNGs, and
   auto-updates meta SHAs. Optionally `--audit` to get the pdffonts font_audit per template.
4. **Visual review (~72 pages, 16 templates).** Inspect every page PNG. Use `bin/audit-alignment`
   and `bin/check-fontsizes` as helpers. Fix overflow/centering in the build.py (frame sizes,
   leading, fontsize) and re-render until clean. Multiple passes (criterion: "mehrere visuelle
   Vergleiche dokumentiert").
5. **Promote baselines + re-derive tolerances.** After sign-off, set each `baseline.pdf` to the
   freshly rendered output, regenerate the committed page PNGs, re-derive each `TOLERANCES.yml`
   (the old Gotham-vs-InDesign wrap budgets no longer apply), then run `bin/render-gallery`
   WITHOUT `--skip-visual-diff` and `bin/check-stale-previews` — both must be green.
6. **Remove Schriftvergleiche** (see removal list).

### Anti-Patterns to Avoid
- **Editing `template.sla` directly** — it is generated from build.py; the next render overwrites
  it. Edit build.py (and the 3 hand-authored `*-original.sla`).
- **Adding a fontconfig alias for Barlow** — unnecessary; Scribus resolves natively (verified).
- **Promoting baselines before visual review** — explicitly forbidden by Decision 4/5.
- **Hand-editing meta.yml SHAs** — let `render-gallery` write them, else stale gate flaps.
- **Leaving old `TOLERANCES.yml` budgets** — they encode Gotham wrap drift; will mis-classify
  the new (different) cross-renderer drift.

## Common Pitfalls

### fc-match misleads for Regular/Bold
**What goes wrong:** `fc-match "Barlow Semi Condensed Regular"` and `"… Bold"` return DejaVu, so a
naive Dockerfile sanity-check on those exact strings fails even though rendering is fine.
**Why:** fontconfig treats "Regular"/"Bold" as style suffixes that don't match a *family*; the
Black/ExtraBold TTFs ship a *secondary family* name so they resolve, Regular/Bold don't.
**How to avoid:** Sanity-check on `fc-match "Barlow Semi Condensed"` (resolves to Barlow Regular)
and a face count, NOT on the per-weight strings. Trust the pdffonts render audit for fallback.
**Warning signs:** Sanity-check passes/fails inconsistently across weight strings.

### template.sla edits silently reverted
**What goes wrong:** Editing `template.sla` fonts; next `render-gallery` rebuilds from build.py and
drops the edit, then stale gate / visual review sees Gotham again.
**How to avoid:** Edit build.py only (and the 3 `*-original.sla`).

### Baseline/tolerance drift after narrower metric
**What goes wrong:** Barlow wraps lines differently → existing `TOLERANCES.yml` `max_issues`
budgets (text-position/line-count/wrap, e.g. flyer-a6-hochformat-gruenes-cover has structural
budgets up to 260) are now wrong; visual_diff against old baselines is meaningless.
**How to avoid:** Render with `--skip-visual-diff` first; promote new baselines; re-derive
tolerances from the new render's audits; only then enable visual_diff.

### Vollkorn-italic accent has no local Barlow italic
**What goes wrong:** Vollkorn Black/Bold Italic (55 build.py refs) provided a *cursive accent*;
mapping to Barlow Black loses the italic. If a slanted accent is required, **no Barlow italic TTF
exists locally** (`find -iname '*barlow*italic*'` → none).
**How to avoid:** Decision 1 accepts upright Barlow Black for the accent. Only if visual review
deems an italic essential, pull `BarlowSemiCondensed-Italic`/`-BlackItalic` from Google Fonts
(OFL) into the same dir + Dockerfile install. Flag to user; do not silently add.

### CI does not render — local artifacts are the contract
**What goes wrong:** Expecting CI to regenerate baselines/previews. It does NOT: `pages.yml`
runs `check-stale-previews` (SHA) + `gallery_build.py` (copies committed bytes) + Astro build;
`ci.yml` runs SOP lints + unit tests. All renders are local.
**How to avoid:** Generate + commit every template.sla/preview.pdf/PNG/baseline.pdf + meta SHAs
locally; verify `bin/check-stale-previews` is green before pushing.

### Removing font_variants.py breaks its unit test
**What goes wrong:** `tools/sla_lib/tests/test_font_variants.py` imports font_variants; CI's
`python3 -m unittest discover tools/sla_lib/tests` (pages.yml) then fails.
**How to avoid:** Delete that test alongside `font_variants.py`/`font_instantiate.py`.

## Schriftvergleiche removal — full dangling-reference map (every site cited)
| Item | Path | Action |
|------|------|--------|
| Astro page | `site/src/pages/schriften/index.astro` | delete |
| Data | `site/src/data/schriften.json`, `site/src/data/schriften-bewertung.json` | delete |
| Build tool | `tools/fonts_compare_build.py` | delete |
| Variant SLA writer | `tools/font_variants.py` | delete (used ONLY by fonts_compare; grep clean elsewhere) |
| Variable→static instancer | `tools/font_instantiate.py` | delete (only referenced by fonts_compare/font_variants) |
| Unit test | `tools/sla_lib/tests/test_font_variants.py` | delete (or it fails CI's unittest discover) |
| Generated previews | `site/public/schriften/` (barlow/montserrat/original/outfit/raleway/tahoma/urbanist) | delete |
| Self-hosted webfonts | `site/public/fonts/` (5 alt families) | delete |
| Per-template comparison fonts | `templates/flyer-a6-hochformat-gruenes-cover/fonts/` (outfit/urbanist/barlow/montserrat/raleway/tahoma incl. `*.sla`/PNGs) | delete |
| Alternatives data + fonts | `shared/fonts/alternatives.yml`, `shared/fonts/alternatives/` (incl. tahoma/, and barlow-semi-condensed/ — but **keep the 4 Barlow TTFs**: relocate to the print-font dir first) | delete dir AFTER relocating Barlow |
| Nav link | `site/src/layouts/Base.astro:54` `<li><a href={url('schriften/')}>Freie Schriften</a></li>` | remove `<li>` |
| Homepage CTA | `site/src/pages/index.astro:56-59` (`url('schriften/')` CTA card) | remove block |
| CSS (Schriften-specific) | `site/src/styles/app.css` — Schriften blocks at ~188, 243, 356, 441, 517 (Vergleichsseite / Bewertungstabelle / Font-Karten / Switcher-Tabs / Empfehlung-Callout) | remove those blocks |
| Lightbox Schriften-Switcher | `site/src/components/Lightbox.astro` (Schriften-Switcher panel hooks, ~25, 192) + the switcher JS in `schriften/index.astro` | remove schriften-specific switcher; keep generic Lightbox |
| `.gitignore` font-comparison exceptions | `.gitignore:30-44` (alternatives `*.ttf` allow, tahoma re-exclude, `site/public/fonts` allow) | prune now-dead rules |
| Comment refs (non-blocking) | `site/src/pages/templates/[...id].astro:62` ("schriften" in a modal comment), `zeitung-a4.md:284` (unrelated "Schriften" word) | cosmetic; tidy stray comments only |

- **No build/CI script imports the schriften data** (`gallery_build.py`, `package.json`, CI
  workflows, pre-commit are all clean of schriften/fonts_compare/alternatives) — confirmed by grep.

## Template / page inventory (visual-review scope)
**16 renderable templates** (have build.py; all `previews_for_sla`-tracked). 15 have a
`baseline.pdf`; **`tischschild-a5-quer` is DSL-only with NO baseline.pdf** (renders 1 page, no
visual_diff). **~72 total pages** to review:
| Template | Pages | baseline.pdf | original_sla | sla_diff_strict |
|----------|------:|:---:|:---:|:---:|
| flyer-a6-hochformat-gruenes-cover | 6 | Y | – | (default) |
| flyer-a6-hochformat-portraet | 6 | Y | – | – |
| flyer-a6-hochformat-quadrat-im-bild | 6 | Y | – | – |
| flyer-a6-hochformat-zweigeteilt | 6 | Y | – | – |
| flyer-a6-querformat-gruenes-cover | 6 | Y | – | – |
| flyer-a6-querformat-portraet | 4 | Y | – | – |
| flyer-a6-querformat-quadrat-im-bild | 6 | Y | – | – |
| flyer-a6-querformat-zweigeteilt | 6 | Y | – | – |
| falzflyer-z-falz-6-seitig-gruenes-cover | 2 | Y | – | – |
| falzflyer-z-falz-6-seitig-gruenes-cover-2 | 2 | Y | – | – |
| falzflyer-z-falz-6-seitig-portraet | 2 | Y | – | – |
| falzflyer-z-falz-6-seitig-zweigeteiltes-cover | 2 | Y | – | – |
| plakat-a1-hochformat | 1 | Y | `plakat-a1-hochformat-original.sla` | false |
| postkarte-a6-kampagne | 2 | Y | `postkarte-vorlage-original.sla` | false |
| zeitung-a4 | 9 | Y | `gruene-zeitung-vorlage-original.sla` | false |
| tischschild-a5-quer | 1 | **N** | – | – |
- `falzflyer-*` PNG count is 2 each (cover render); page counts above are from `pdfinfo
  baseline.pdf` / meta `pages:`. `templates/zeitung-a4-grun/` is a stale `__pycache__` only (no
  build.py) — ignore. `templates/_smoke/`, `templates/_specs/` are fixtures — not in the
  production render set.

## Render + baseline workflow (exact, ordered commands)
```bash
# 0. (one-time, baked into Dockerfile.claude for reproducibility) install Barlow:
#    install shared/fonts/alternatives/barlow-semi-condensed/*.ttf → /usr/local/share/fonts/gruene/
#    fc-cache -f ; fc-match "Barlow Semi Condensed"   # must show a Barlow TTF

# 1. render ONE template (after build.py edit), skipping the stale-baseline diff:
bin/render-gallery flyer-a6-hochformat-gruenes-cover --skip-visual-diff
#    (rebuilds template.sla, preview.pdf, page-NN.png[+-hires], updates meta SHAs)

# 2. render ALL templates:
bin/render-gallery --skip-visual-diff
#    add --audit to also run the pdffonts font_audit (catches DejaVu fallback)

# 3. inspect a render's embedded fonts (no DejaVu expected):
pdffonts templates/<id>/preview.pdf | grep -iE 'barlow|dejavu|gotham|vollkorn|minion'

# 4. alignment / fontsize helpers during visual review:
bin/audit-alignment --all
bin/check-fontsizes templates/<id>/template.sla

# 5. promote-to-baseline (per docs/render-fidelity.md:118-131):
#    DSL-only templates (13): the freshly rendered preview.pdf IS the new reference →
cp templates/<id>/preview.pdf templates/<id>/baseline.pdf
#    original_sla templates (postkarte/plakat/zeitung): render the *-original.sla
#    (after its FONT/DFONT edits) straight to baseline.pdf:
xvfb-run -a --server-args="-screen 0 1024x768x24" \
  scribus -g -ns -py tools/_export_pdf.py <id>-original.sla templates/<id>/baseline.pdf

# 6. re-derive tolerances, then a clean render (diff now runs vs NEW baselines):
bin/render-gallery            # no --skip-visual-diff
bin/check-stale-previews      # must exit 0 (auto-green from step 2's meta updates)

# 7. local CI mirror before push:
bin/validate                  # sla_diff (skipped where strict=false) + visual_diff
bin/ci-local                  # mirrors pages.yml build-job gates
```
- **Headless display:** every Scribus call goes through `xvfb-run -a
  --server-args="-screen 0 1024x768x24"` (Scribus needs a display). Already encapsulated in
  `render_sla_to_pdf`.
- **CI gates (no rendering):** `ci.yml` = SOP lints (`sop_lint.py`, `lint_inject_consistency.py`,
  `check_no_absolute_paths_in_sla.py`) + `pytest tests/unit/`. `pages.yml` = build `_smoke/`,
  `gallery_build.py`, Astro build, `unittest discover tools/sla_lib/tests`, **`check-stale-previews`**
  + `sla_diff --strict` (SKIPPED for all 3 strict=false templates). The **stale-previews SHA gate**
  is the one that must be green; it auto-syncs when you re-render.

## Environment Availability
| Dependency | Required By | Available | Version | Notes |
|------------|------------|-----------|---------|-------|
| scribus | render | YES | 1.6.5 | `/usr/bin/scribus` |
| xvfb-run | headless render | YES | – | `/usr/bin/xvfb-run` |
| pdffonts/pdftoppm/pdfinfo | audit/rasterise | YES | poppler | – |
| fc-match/fc-scan/fc-list | font resolution | YES | fontconfig | Barlow not yet in fontconfig until installed |
| Barlow TTFs | render | YES (committed) | 4 static cuts | `shared/fonts/alternatives/barlow-semi-condensed/` |
| otfinfo | name-table inspection | NO | – | used fc-scan instead (sufficient) |
| Barlow Italic TTF | optional accent | **NO** | – | pull from Google Fonts only if review demands it |
| node/npm | Astro site build | (pages.yml installs) | 20 | site build runs in CI, not needed for font swap |

## Project Constraints (from CLAUDE.md)
- **No vendoring of third-party deps** — except the deliberate print-pipeline font exception:
  Barlow (SIL OFL) installed locally for Scribus is allowed, exactly like the existing Vollkorn
  vendoring. Document the exception in the commit/PR (acceptance criterion).
- **No tool attribution** — no "claude"/"Generated with"/`Co-Authored-By` in commits, code, or
  comments. Applies to every artifact in this issue.
- No workspace-level extra `CLAUDE.md` rules beyond the above; the repo has no own CLAUDE.md.

## Sources
### HIGH confidence
- Live codebase analysis: grep counts, `meta.yml`/`ci.yml`/`Dockerfile.claude` reads,
  `tools/render_pipeline.py`, `tools/visual_diff.py`, `tools/check_stale_previews.py`,
  `tools/sla_diff.py`, `tools/sla_lib/builder/{brand,document,brand_constraints}.py`.
- **End-to-end render test on the container:** patched postkarte build.py → build.py →
  `render_sla_to_pdf` → `pdffonts` showed BarlowSemiCondensed-{Regular,Bold,Black} embedded,
  no DejaVu. `scribus.getFontNames()` confirmed the four Barlow face names.
- `fc-scan`/`fc-match` on the 4 Barlow TTFs (name tables + resolution behaviour).
- CI workflow reads: `.github/workflows/ci.yml`, `.github/workflows/pages.yml`, `bin/ci-local`,
  `bin/validate`, `docs/render-fidelity.md`.
### MEDIUM confidence
- Schriftvergleiche dangling-reference map (grep over `site/`, `tools/`, CI) — comprehensive but
  the planner should re-grep `schriften`/`alternatives` once after deletion to confirm zero refs.
### LOW confidence (needs validation)
- Exact final shape of new `TOLERANCES.yml` budgets — depends on the actual Barlow render drift,
  which is only knowable after step 3/4. Treat as "re-derive empirically", not a fixed edit.

## Metadata
**Confidence breakdown:** Font inventory HIGH (greps). Provisioning HIGH (render + fc tests).
Render/baseline workflow HIGH (code + docs + live run). Removal map MEDIUM (grep — re-verify post-delete).
Tolerance regeneration LOW (empirical, post-render).
**Research date:** 2026-06-07
**Sub-agents used:** none (single-researcher deep verification of an existing architecture map)
**Raw research files:** inline (no `.issues/<slug>/research/` split needed)
