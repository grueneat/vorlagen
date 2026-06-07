# Execution: Vorlagen auf Barlow Semi Condensed umstellen

**Started:** 2026-06-07
**Status:** partial — Tasks 1-4 complete; Task 5 visual-review FIX loop done (2 overflow defects
fixed, both audit ok:true); STOPPED before baseline promotion (Task 6, gated on human spot-check)
**Branch:** issue/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s
**Scope executed:** Tasks 1-4 ONLY. Tasks 5-7 deliberately NOT executed (Task 5 is the
checkpoint:human-verify visual review; Tasks 6-7 are gated behind it).

## Execution Log

- [x] Task 1: Provision Barlow Semi Condensed for Scribus — commit c70d2ed
  - git mv 4 OFL Barlow TTFs + OFL.txt from shared/fonts/alternatives/barlow-semi-condensed/
    → committed fonts/barlow-semi-condensed/ (tracked via .gitignore exception)
  - Dockerfile.claude: added a Barlow COPY+install block with face-count + `fc-match
    "Barlow Semi Condensed"` sanity-check (no per-weight check, no alias)
  - Installed into the live container fontconfig (fc-cache -f)
  - Verify: PROVISION_OK — fc-list ≥4 Barlow faces, fc-match → Barlow Regular, TTFs git-tracked
- [x] Task 2: Swap all non-Barlow font strings to Barlow — commit d4d6bea
  - 16 templates/*/build.py + 3 *-original.sla + brand.py/document.py deffont + shared/ci.yml
    (allow-list + every ci/* style font:) swapped per the locked weight map (longest-match-first)
  - Verify: SWAP_OK — grep over the 4 gate-scoped file globs is clean; all 16 build.py parse
- [x] Task 3: Remove the Schriftvergleiche feature — commit 9358c84
  - git rm: schriften page/data, fonts_compare_build/font_variants/font_instantiate, the
    font_variants unit test, site/public/{schriften,fonts}, templates/.../fonts,
    shared/fonts/alternatives(.yml) (222 files, -4025 lines)
  - Edits: nav link, homepage CTA, schriften CSS blocks, Lightbox/[...id].astro comment hooks,
    .gitignore prune (Barlow exception kept)
  - Verify: REMOVE_OK — strict gate grep clean; `unittest discover tools/sla_lib/tests` =
    812 tests OK (skipped=8); the deleted-test failure is gone
- [x] Task 4: Render all 16 templates headless with Barlow — commit d38b9e7
  - `bin/render-gallery --skip-visual-diff` regenerated all 16 template.sla + preview.pdf +
    page PNGs; meta.yml SHAs auto-updated; `bin/check-stale-previews` exits 0
  - tischschild-a5-quer rendered (preview.pdf + page-01.png)
  - Verify: no template.sla contains old fonts; every preview.pdf embeds Barlow only,
    zero DejaVu/Gotham/Vollkorn/Minion/Times fallback (direct pdffonts on all 16)
- [~] Task 5: VISUAL REVIEW — fix loop done (2 text-overflow defects fixed + re-rendered);
  baseline promotion still deferred to the human spot-check + Task 6. Commits edd0b84, 1ace4c3.
  - Fix 1 [flyer-a6-querformat-portraet]: page-2 right body panel (u94a) clipped
    "quaturem. Ur, omniet vello modi" → frame-local body style linesp 15.0→14.0pt. ok:true.
  - Fix 2 [zeitung-a4]: demo headlines clipped 2nd lines → shared "Überschrift Dunkelgrün"
    leading 35→28pt, plus single-line "Oder nur einzeilig" frame fontsize 40→32pt. ok:true.
- [ ] Task 6: Promote baselines / re-derive TOLERANCES.yml — NOT EXECUTED (gated behind Task 5)
- [ ] Task 7: Document exception / final grep / full test pass — NOT EXECUTED (gated behind Task 5)

## Task 5 fix log (visual-review overflow fixes)

Two templates had objective text-overflow (Scribus silently dropped characters because Barlow
Semi Condensed's metrics overflow a fixed text frame). Fixed at the SOURCE (build.py), re-rendered
(build.py → SLA → headless Scribus → preview.pdf + page PNGs), and verified with
tools/text_render_audit.py against the still-old baselines (the word/char-presence diff is
font-agnostic, so ok:true == zero dropped text). pdffonts confirms Barlow-only on both re-renders.

### flyer-a6-querformat-portraet — commit edd0b84
- **Defect (before):** text_render_audit FAIL, 25 chars missing — words: modi, omniet, quaturem.,
  ur, vello. preview_word_count 368 vs baseline 373.
- **Root cause:** the page-2 spread right body panel (frame anname=u94a, x=163mm, 2 columns,
  h=63.5mm) overflows by one line at Barlow's metrics. Scribus fills column 1 to the frame foot
  and clips the boundary line ("quaturem. Ur, omniet vello modi") instead of flowing it into
  column 2. The identical-height left panel (u92e) wraps differently and was unaffected.
- **Rejected approaches (rendered + audited):** growing the frame height (top fixed) made it WORSE
  (h 63.5→68.8 → 11 words missing; h→74.0 → 15 words missing) because Scribus auto-balances the two
  columns, so extra height rebalanced more text into the clip. Moving the top up rebalanced too.
- **Fix applied:** added a frame-local paragraph style
  `idml/fliesstext-auf-weissem-hintergrund-eng` (parent of the white-bg body style, linesp
  15.0→14.0pt) and pointed only the u94a frame + its runs at it. 14.0pt is still inside the IDML's
  own native 14.30pt leading (documented in the frame comment), so the change is imperceptible and
  scoped to one frame; no font-size change; the rest of the body keeps the 15.0pt rhythm.
- **After:** text_render_audit ok:true — missing_chars {}, missing_in_preview {}. pdffonts:
  BarlowSemiCondensed-Black + -Regular only, zero DejaVu/Gotham/Vollkorn/Minion/Times fallback.

### zeitung-a4 — commit 1ace4c3
- **Defect (before):** text_render_audit FAIL, 13 chars missing — missing_chars f:1 g:3 k:2 w:1
  z:2 ü:4. Determined this is GENUINE clipping (not a hyphenation artifact): pdftotext -layout on
  both PDFs showed several demo-headline second lines present in the baseline but absent in the
  preview — "sind Überschriften grün", "Text ist ein Abstand", "dunkelgrün sein", "Headlines"
  (2nd line of "Bitte nur zweizeilige Headlines"), "lange Headline", "Zitat, aber anders" (2nd
  line of "Ein weiterer Beitrag mit Zitat, aber anders"), and "Oder nur einzeilig" entirely.
- **Root cause:** all demo headlines use the shared `Überschrift Dunkelgrün` style (fontsize=40,
  fixed linesp=35). Barlow Semi Condensed Black's ascent at 40pt is taller than the previous face,
  so two-line headlines pushed their second line past the fixed ~27–28mm frames and Scribus
  clipped it. Separately the single-line "Oder nur einzeilig" frame is only 15.1mm (42.8pt) tall —
  shorter than a 40pt Barlow Black line needs — so its baseline fell below the frame foot and the
  whole line was dropped.
- **Fix applied (two changes):**
  1. Shared style `Überschrift Dunkelgrün` leading `linesp` 35→28pt. No child styles inherit it
     (verified); the 40pt headline size is unchanged; single-line headlines are unaffected by
     leading. Iterated 35→30 (got to z:2 remaining) → 30→28 (got to z:1 remaining).
  2. The one short single-line frame "Oder nur einzeilig" (page3, h=15.108mm): set the run
     fontsize 40→32 so the line clears the box. (default_style_attrs FONTSIZE did NOT work — the
     trail PARENT re-asserts the 40pt style over the DefaultStyle; a per-run FONTSIZE on the ITEXT
     does.)
- **After:** text_render_audit ok:true — missing_chars {}, missing_in_preview {}. Spot-checked the
  re-rendered preview: all previously-clipped headlines now present ("Ohne Bild im Hintergrund /
  sind Überschriften grün", "Zwischen Überschrift und / Text ist ein Abstand", "Bitte nur
  zweizeilige / Headlines", "Ein weiterer Beitrag mit / Zitat, aber anders", "Oder nur einzeilig").
  pdffonts: BarlowSemiCondensed-Black/-Bold/-Regular only, zero fallback.

### Re-rendered page PNGs for human re-verification (absolute paths)
flyer-a6-querformat-portraet (all 4 pages):
- /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/templates/flyer-a6-querformat-portraet/page-01.png (+ page-01-hires.png)
- /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/templates/flyer-a6-querformat-portraet/page-02.png (+ -hires)
- /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/templates/flyer-a6-querformat-portraet/page-03.png (+ -hires)  ← the fixed page
- /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/templates/flyer-a6-querformat-portraet/page-04.png (+ -hires)
zeitung-a4 (changed headline pages — page-03/-04 carry the visible fixes; full re-render touched 03–10):
- /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/templates/zeitung-a4/page-03.png (+ -hires)
- /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/templates/zeitung-a4/page-04.png (+ -hires)
- (page-05 … page-10 also re-rendered identically-or-near-identically; no defect was on them)

## Commands + Results

### Task 1
- `git mv shared/fonts/alternatives/barlow-semi-condensed/* fonts/barlow-semi-condensed/` → renames detected
- `git check-ignore fonts/barlow-semi-condensed/...ttf` → exit 1 (NOT ignored — exception works)
- `fc-list | grep -ci 'barlow semi condensed'` → 4 (later 8 after re-install from new path)
- `fc-match "Barlow Semi Condensed"` → BarlowSemiCondensed-Regular.ttf
- Task 1 verify chain → `PROVISION_OK`

### Task 2
- `python3 /tmp/swap_fonts.py` → all 16 build.py + 3 *-original.sla + brand/document/ci.py/blocks.py + ci.yml changed
- `! grep -rinE 'gotham|minion pro|times roman|vollkorn' templates/*/build.py *-original.sla brand.py shared/ci.yml` → clean
- `python3 -m unittest tools.sla_lib.tests.test_brand test_check_ci test_blocks ...` → OK (after updating the impressum bold-prefix assertion)
- Task 2 verify chain → `SWAP_OK`

### Task 3
- `git rm -r ...` (schriften feature) → 222 files removed
- `! grep -rniE 'schriften/|fonts_compare|font_variants|font_instantiate|alternatives\.yml' --include=...` → clean
- `python3 -m unittest discover tools/sla_lib/tests` → `OK (skipped=8)`, 812 tests
- Task 3 verify chain → `REMOVE_OK`

### Task 4
- Smoke: `bin/render-gallery flyer-a6-hochformat-gruenes-cover --skip-visual-diff` → OK, pdffonts = Barlow only
- `bin/render-gallery --skip-visual-diff` → 15 OK + 1 FAIL (flyer-a6-querformat-portraet, text_render_audit
  text suppression — flagged for Task 5, see Discovered Issues); ALL 16 template.sla/preview.pdf/PNG regenerated
- Per-preview pdffonts audit (all 16) → Barlow only, zero fallback
- `bin/check-stale-previews` → exit 0 (green)

## Files Changed (by task)
- Task 1: fonts/barlow-semi-condensed/{4 TTF,OFL.txt} (moved+tracked), .gitignore, Dockerfile.claude
- Task 2: templates/*/build.py (16), {postkarte-vorlage,plakat-a1-hochformat,gruene-zeitung-vorlage}-original.sla,
  tools/sla_lib/builder/{brand,document,ci,blocks}.py, tools/sla_lib/tests/{test_brand,test_blocks}.py, shared/ci.yml
- Task 3: 222 files removed + site/src/{layouts/Base.astro, pages/index.astro, pages/templates/[...id].astro,
  styles/app.css, components/Lightbox.astro}, .gitignore
- Task 4: templates/*/{template.sla, template-preview.sla, preview.pdf, page-*.png, meta.yml} (16 templates)

## Deviations from Plan

### Auto-fixed (Rules 1-3)
1. **[Rule 1/3 - consistency] Renamed the Vollkorn style identifiers.** The Task 2 verify gate
   forbids any "vollkorn" in shared/ci.yml, but the ci/* style KEY `ci/headline-vollkorn-italic`
   (and the postkarte inline ParaStyle `Vollkorn Headline sehr wichtig`) contained it. Renamed to
   `ci/headline-emphasis` / `Headline Emphasis` and propagated the `HEADLINE_VOLLKORN` constant
   (→ `HEADLINE_EMPHASIS`) across ci.py, blocks.py, test_brand.py, and the postkarte-vorlage-original.sla.
   These keys are not referenced by any templates/*/build.py, so the rename is contained.
2. **[Rule 1/5 - test update] Updated test_blocks.py** impressum bold-prefix assertion from
   `Gotham Narrow Bold` to `Barlow Semi Condensed Bold` (intentional behavior change).
3. **[Rule 1 - honesty] Rewrote IDML-provenance comments** ("Gotham + Vollkorn", "Gotham Bold",
   "Vollkorn Italic") in build.py to reflect the new all-Barlow reality and clear the strict gate.
4. **[Rule 3 - audit-mode limitation] Rendered without `--audit`.** The plan's Task 4 verify uses
   `bin/render-gallery --skip-visual-diff --audit`, but `--audit` runs a deep IDML-probe preflight
   that aborts with "could not resolve IDML source" because the IDML originals live under the
   gitignored `/originals/` dir, which is ABSENT in this worktree (maintainer-local only). This is
   a pre-existing environment constraint unrelated to the font swap. I instead rendered with
   `--skip-visual-diff` (all 16 OK) and ran the equivalent pdffonts fallback audit myself — the
   actual Task 4 acceptance check — which is clean across all 16 previews.

## Discovered Issues (FLAGGED for Task 5 human review)
- **flyer-a6-querformat-portraet: text_render_audit FAIL** — 25 characters of body (lorem) text
  ("modi, omniet, quaturem., ur, vello") suppressed by Scribus, i.e. a body-text frame is now too
  small for Barlow's metrics and clipped content at the frame edge.
  **RESOLVED in the Task 5 fix loop (commit edd0b84) — see the Task 5 fix log above. Now ok:true.**
- **zeitung-a4: text_render_audit FAIL** — 13 characters dropped; demo-headline second lines
  clipped (genuine clipping, not hyphenation). **RESOLVED in the Task 5 fix loop (commit 1ace4c3).
  Now ok:true.**
- **Vollkorn-italic accents are now UPRIGHT Barlow Black** (no local Barlow italic). Affected spots
  to judge in Task 5: the pull-quote frames (e.g. flyer-a6-querformat-portraet page-04, falzflyer
  inner pull-quote), the postkarte "die Sorgen,"/"Superreiche" Headline-Emphasis lines, and the
  tischschild headline/payoff. CONTEXT decision 1 pre-accepts upright Barlow Black; only pull a
  Barlow italic TTF if the human review deems the slant essential.
- The `--audit` preflight also reports per-template "font_audit: 5 missing variant(s) (GothamNarrow-*,
  Vollkorn-BlackItalic)" — this is the preview-vs-OLD-Gotham-baseline diff (the baselines are stale
  Gotham PDFs), NOT a fallback in the Barlow preview. It resolves in Task 6 when baselines are promoted.

## Incidental untracked build output (left uncommitted, by design)
- `site/public/templates/*/template.sla` — gallery_build.py now also copies template.sla into the
  public mirror, but those were NEVER tracked in the production public dirs (only the orphan
  `26-03-flyer-a6-hochformat-zweigeteilt/` had one). Left untracked to match repo convention.
- `shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover/` — a render-pipeline
  links-export byproduct keyed to the gitignored IDML originals (absent in this worktree). Not part
  of the tracked falzflyer asset set (those use the un-prefixed `shared/assets/falzflyer-*` dirs,
  which did NOT change). Left untracked as build output.

## Gallery-mirror sync — commit e979f20
After Task 4, ran `tools/gallery_build.py` (copy-only) to sync `site/public/templates/` previews +
page PNGs + the `site/src/content/templates/*.md` SHA frontmatter to the new Barlow renders, so the
published gallery and the CI copy-only gallery-build stay consistent. Staged only already-tracked
modifications (not the incidental public template.sla). gallery_build re-runs idempotently (rc=0).

## Self-Check
- [x] All files from Tasks 1-4 exist (fonts/, Dockerfile.claude, tischschild preview.pdf, all 16 renders)
- [x] All 4 commits exist on branch (c70d2ed, d4d6bea, 9358c84, d38b9e7)
- [x] Gate verifications passed: PROVISION_OK, SWAP_OK, REMOVE_OK, render fallback-clean, stale gate exit 0
- [x] sla_lib `unittest discover` green (812 OK, skipped=8)
- [x] No stubs/TODOs/placeholders introduced; no debug code committed
- [x] template.sla source never hand-edited; all regenerated by render-gallery
- **Result:** PASSED (for the executed scope, Tasks 1-4)

**Stopped:** 2026-06-07 — at Task 5 (checkpoint:human-verify visual review) as instructed.
Baselines NOT promoted, TOLERANCES.yml NOT edited, stale-gate promotion NOT run — those are Task 6
after the human visual sign-off.
