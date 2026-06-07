# Execution: Vorlagen — Überschriften-Zeilenabstände (Barlow/Vollkorn), Falzflyer-Social-Icons, Abstands-Audit

**Started:** 2026-06-07
**Status:** complete (all 6 tasks done; baselines promoted after human visual sign-off;
follow-up: zweigeteiltes-cover left social-icon defect fixed + re-promoted — commit d89019e)
**Branch:** issue/bx4d8-vorlagen-überschriften-zeilenabstände-bei-barlowvollkorn-korrigieren-falzflyer-s

## Execution Log

- [x] Task 0: Verify post-c8bg0 font state (setup gate)
  - Worktree HEAD `006be5c` on branch `issue/bx4d8-...`; c8bg0 (`0ce7fec`) IS an ancestor of HEAD.
  - `fc-match "Barlow Semi Condensed"` → BarlowSemiCondensed-Regular.ttf; `fc-match "Vollkorn"` → Vollkorn-BoldItalic.ttf (no DejaVu for the family queries).
  - `zeitung-a4/build.py:66` `Überschrift Dunkelgrün`: font='Barlow Semi Condensed Black', fontsize=40, **linesp=28** (the c8bg0-cut value, confirms post-c8bg0).
  - `fonts/vollkorn/` present (Vollkorn-BlackItalic.ttf, Vollkorn-BoldItalic.ttf).
  - Canonical build.py uses Barlow (22×), zero Gotham literals.
  - `pdffonts` on existing canonical preview.pdf → ONLY BarlowSemiCondensed (Black/Bold/Regular) + Vollkorn (BlackItalic/BoldItalic). Zero DejaVu/Gotham.
  - **Important env note:** the bash CWD must be the worktree absolute path; `cd /workspace/vorlagen` lands in the MAIN checkout (branch `main`, pre-c8bg0). All commands use the worktree path.
- [x] Task 1: Metric-driven stacked-headline baseline corrector — commit 1dfb02f
  - `tools/sla_lib/builder/headline.py`: `headline_stack` + `font_ascent_pt/mm`,
    cached fontTools hhea reader with deterministic repo-font fallback.
  - TDD: 13 tests prove even baselines for the mixed-font dreizeilige case.
  - pytest + unittest discover both green; ruff clean.
- [x] Task 2: Regenerate stacked headlines in 12 templates — commit de1af7f
  - Migrated all 28 stacked groups (4 falzflyers + 8 A6 flyers) to `headline_stack`
    via an AST-based one-off migration; added `layer=` param to the helper.
  - Canonical uaf8: inter-baseline gaps now 27.0pt / 27.0pt (was 7.94mm-top vs
    11.11mm-bottom visible). Round-trip structure intact (39 PAGEOBJECTs, identical
    anname set); only Vollkorn sub-line YPOS moved.
  - 26-03-* mirror templates do not exist (renamed to German in #118) — nothing to mirror.
- [x] Task 3a: zeitung-a4 Überschrift Dunkelgrün leading 28→30pt — commit 65ce5e5
  - 30pt clip-safe (+1.3pt margin in the 79.3pt frame; 31pt only +0.3pt, 32pt clips).
    Chose 30 over the plan's start-at-31 because 31 sits at the clipping edge.
  - text_render_audit: headlines render in full; residual word-match drift is vs the
    not-yet-promoted 28pt baseline (Task 6), NOT clipping (verified words present in
    preview text). text_render_strict=false → non-blocking.
- [x] Task 3b: falzflyer social icons — DEFECT FOUND + FIXED (corrects earlier finding) — commit d89019e
  - **Correction:** the earlier "no defect" conclusion was WRONG for
    zweigeteiltes-cover. The Scribus-SCALETYPE invisibility angle was a red herring;
    the real defect is a DATA error in the LEFT social column.
  - Root cause: in `falzflyer-z-falz-6-seitig-zweigeteiltes-cover/build.py` the three
    LEFT-column social ImageFrames (u3e7 `@diegruenen`, u3f0 `@diegruenen`,
    u3f5 `@diegruenenaustria`) all carried the SAME inline blob — the uncropped
    4-icon composite strip (sha(b64) `f580200d`, from "Social Media Icons weiss.ai")
    pasted whole into each frame 3×, instead of three distinct per-handle glyphs.
    The RIGHT column (u477/u4a2/u4da → b4c9b1f6/1ed9c0fe/8695b0a7, the gruene.at
    bluesky/globe/envelope) was already correct.
  - Reference: `gruenes-cover/build.py` renders the SAME left column correctly by
    referencing three distinct CROP PNGs (facebook/instagram/tiktok-weiss) via
    `image=` + `scale_type=0` — NOT inline blobs. The composite never got split
    into per-handle crops for zweigeteiltes-cover (it still carries the stale
    `composite_ai_split.yml`, which gruenes-cover lacks).
  - Per-handle mapping applied (wrong → correct):
    - u3e7 `@diegruenen`         : f580200d (composite) → social-facebook-weiss.png
    - u3f0 `@diegruenen`         : f580200d (composite) → social-instagram-weiss.png
    - u3f5 `@diegruenenaustria`  : f580200d (composite) → social-tiktok-weiss.png
  - Fix: copied the three correct crop PNGs from gruenes-cover into
    `shared/assets/.../zweigeteiltes-cover/crops/social/` and swapped the three
    inline-blob ImageFrames to `image=<crop> + scale_type=0`, exactly mirroring
    gruenes-cover. Frame GEOMETRY (x/y/w/h/anname) unchanged. Right column,
    headlines, everything else untouched.
  - Verify (visual, page-02-hires): LEFT column now shows three DISTINCT correct
    icons — Facebook / Instagram / TikTok — each beside its handle, byte-identical
    to gruenes-cover's left column. Right column (bluesky/globe/envelope → gruene.at)
    unchanged. Headline spacing from Tasks 1-3 intact.
  - Propagation: the same swap flows through all 9 impressum aggregate SLAs
    (each embeds the full template); inline-image count per aggregate 8 → 5.
  - Gates (zweigeteiltes-cover): render-gallery visual_diff PASS; text_render_audit
    ok=true (2337/2337 chars, 0 missing); check-stale-previews exit 0; pdffonts
    baseline+preview ONLY Barlow+Vollkorn (zero DejaVu/Gotham); headline_spacing_audit
    OK (3 stacks, pixel); audit-alignment exit 0. Unit suites: pytest 824 passed/8
    skipped + unittest discover OK (both runners green).
  - Known non-fatal: audit-alignment emits 3 `[WARNING] asset missing/corrupt` for
    the new social crops — a FALSE POSITIVE from the audit's CWD-relative path
    resolution (`_template_root` is None, so `../../shared` resolves against
    `/workspace/vorlagen` = main checkout where the worktree-only crops don't yet
    exist). Scribus resolves PFILE relative to the SLA file, finds the worktree
    crops, and renders the icons correctly. Resolves on merge. Non-blocking (RC=0).
  - The OTHER 3 falzflyers (gruenes-cover, gruenes-cover-2, portraet) were NOT
    touched — only zweigeteiltes-cover had the duplicated-blob defect.
- [x] Task 4: headline_spacing_audit.py + wiring + tests — commit 5fb4237
  - `tools/headline_spacing_audit.py`: groups stacks by stem from template.sla
    (SLADocument), static (FLOP=1 + fontTools ascent) + pixel (E4 ink-top) paths,
    flags too_tight / uneven / top_gap_collapse; YAML + non-zero exit.
  - Fixed an E4 regression my Task-2 migration caused: added
    `parse_textframes_from_sla` to `line_spacing_pixel_audit` and preferred it in
    E4 main (headline_stack frames aren't literal in build.py).
  - Wired into `bin/validate` (static) + `tools/audit_alignment.py --all`
    (so `bin/audit-alignment` and CI's render-free run gate on it).
  - Call-site enumeration: only additional invokers are `.github/workflows/pages.yml`
    and `bin/ci-local`, both via `audit_alignment.py --all` (now covered); no
    Makefile target. TDD: 7 tests; dual runner + ruff green.
- [x] Task 5: Re-render all affected templates + measure + lock thresholds — commit (this)
  - Re-rendered all 12 stacked-headline templates + zeitung-a4 + 4 falzflyers headless
    (xvfb Scribus) → fresh preview.pdf + page PNGs. `bin/check-stale-previews` exit 0.
  - GATES (all changed templates): `text_render_audit` clip-free; `pdffonts` shows
    ONLY Barlow + Vollkorn (zero DejaVu/Gotham); static + pixel `headline_spacing_audit`
    pass on all 12.
  - Measured before/after pixel ink-top gaps (canonical uaf8, linesp 27pt):
    PRE 7.96mm top / 11.01mm bottom (ratio 0.72, collapsed) → POST 10.16mm top /
    8.81mm bottom (ratio 1.15). Static baselines exactly even (27.0/27.0pt).
  - LOCKED audit thresholds from corrected renders: min_ratio 0.80 (min corrected
    ink-top ratio 0.832), even_tol 0.18 (max corrected ink spread 0.154); pre-fix
    geometry still flagged by all three checks.
  - Tuning: zeitung-a4 leading set to 30pt (Task 3a) after measuring 31 sits at the
    +0.3pt clip edge; stacked linesp kept at the IDML design leading (helper makes
    gaps even at that leading — no per-template nudge needed; all pass).
  - NO baselines promoted, NO diff.yml/TOLERANCES.yml touched.
- [x] Task 6: Human visual sign-off + baseline promotion + final gates — commit e350858
  - Human visual sign-off received from the main agent: the "dreizeilige" gaps are
    now balanced, zeitung headlines clear. Promotion gate (CONTEXT.md decision 5) met.
  - Promoted 13 baselines (preview.pdf → baseline.pdf):
    - 12 DSL stacked-headline templates (8 A6 flyers + 4 z-falz falzflyers):
      `cp preview.pdf baseline.pdf` — these have NO template-preview.sla, so
      preview.pdf IS the template.sla render (baseline == template.sla render).
    - zeitung-a4 (original_sla, HAS template-preview.sla): baseline rendered from
      `template.sla` via `xvfb-run scribus -g -ns -py tools/_export_pdf.py
      templates/zeitung-a4/template.sla templates/zeitung-a4/baseline.pdf`
      (NOT template-preview.sla), per the c8bg0-established path.
  - diff.yml / TOLERANCES.yml NOT touched — Scribus renders deterministically, drift
    is ~0% vs the new baselines (visual_diff PASS on every changed template). No
    tolerance loosening. preview.pdf / page-*.png already committed in Task 5 and
    byte-identical after the deterministic re-render (no change to stage).
  - Only change committed: the 13 baseline.pdf files (e350858).

## Key findings (Task 0 measurement basis)

- The current build.py `y_mm` for stacked headlines were generated by `tools/idml_to_dsl.py::_emit_mixed_font_headline` using a hardcoded `_FONT_FLOP_ASCENT_RATIO = {"vollkorn": 0.15}` (fraction-of-fontsize correction relative to line-1 font).
- Real font ascents (fontTools, hhea.ascent / unitsPerEm):
  - Barlow Semi Condensed (all weights): **1.000**
  - Vollkorn (Black/Bold Italic): **0.952**
  - Gotham Narrow (all weights): **0.800**
- The old 0.15 ratio matches `ascent(Vollkorn) − ascent(Gotham) = 0.952 − 0.800 = 0.152` → confirms **Scribus FLOP=1 uses hhea.ascent**. With Barlow (1.000) as the new line-1 reference, the Vollkorn correction must change from "−0.15·s (up)" to a metric-derived `ascent(Barlow) − ascent(Vollkorn) = +0.048·s` → Vollkorn moves slightly DOWN, not up. That sign flip is exactly why the top gap collapsed (7.94mm vs 11.11mm) on the dreizeilige case.

## Verification Results

**Unit tests:** pytest 824 passed / 8 skipped; `python3 -m unittest discover
tools/sla_lib/tests` exit 0 (both runners green). New: 13 headline_stack +
7 headline_spacing_audit tests. No stray `import pytest` in unittest files.
**Ruff:** new files clean; no new lint errors introduced in edited legacy files.
**pdffonts:** all 13 changed templates show ONLY Barlow + Vollkorn (zero DejaVu/Gotham).
**text_render_audit:** all 12 stacked templates `ok: true` (clip-free); zeitung-a4
non-blocking word-drift vs the not-yet-promoted baseline (text_render_strict=false).
**headline_spacing_audit:** static + pixel pass on all 12; flags the pre-fix
geometry on all three checks.
**bin/audit-alignment --all:** zero headline-spacing violations.
**bin/check-stale-previews:** exit 0.
**bin/validate (pre-promotion):** NOT green — sla_diff/visual_diff compared against
the pre-fix baselines; resolved by the Task-6 baseline promotion.

## Task 6 — Final gate results (post-promotion, against the new baselines)

**Baselines promoted:** 13 (12 DSL stacked-headline templates + zeitung-a4). Only
the 13 `baseline.pdf` files changed; diff.yml/TOLERANCES.yml untouched (drift ~0%).

- **bin/render-gallery (full):** RC=0. 16 `visual_diff (150dpi): PASS`, ZERO
  FAIL/DRIFT/Traceback. (One transient `scribus exited 0 but produced no PDF` on
  falzflyer-z-falz-6-seitig-zweigeteiltes-cover during the nested visual_diff render
  on the first attempt — a Scribus-under-xvfb flush hiccup, NOT a geometry drift;
  passed cleanly on retry and on the final full clean run.)
- **bin/check-stale-previews:** exit 0.
- **bin/validate:** exit 1 — EXPECTED. The only sla_diff FAILs are the 3 original_sla
  templates (plakat, postkarte, zeitung-a4), all carrying `sla_diff_strict: false`.
  zeitung-a4's lone sla_diff `critical` is a pre-existing round-trip divergence
  (PAGEOBJECT[35] FONTSIZE=32 ITEXT, present at the branch base 006be5c). The ONLY
  template.sla delta my work introduced is `LINESP 28→30` on `Überschrift Dunkelgrün`,
  which shows up as an `info`-level diff. visual_diff PASS on ALL templates; the new
  static headline_spacing gate in bin/validate passes.
- **bin/audit-alignment --all:** exit 0. New `headline_spacing` audit reports OK for
  all 12 stacked templates (3 stacks each on the 4 falzflyers, 2 stacks each on the
  8 A6 flyers). Pre-existing zeitung page-14 band-boundary `[ERROR]` lines are
  non-fatal aggregate findings, unrelated to headline spacing (overall exit 0).
- **text_render_audit (--preview/--baseline):** ok=True, `missing_in_preview: {}`
  (zero clipping) on ALL 13 changed templates — including zeitung-a4, whose Task-5
  residual word-drift was purely vs the not-yet-promoted 28pt baseline and is now
  fully resolved by the 30pt baseline promotion.
- **pdffonts:** all 13 baselines AND all 13 previews show ONLY Barlow + Vollkorn —
  zero DejaVu / Gotham (26 PDFs checked). (Scribus's stderr "subset list: DejaVu
  Sans Book" warning is substitution chatter; no DejaVu is embedded — pdffonts
  confirms.)
- **headline_spacing_audit (static + pixel):** exit 0 on all 12 stacked templates.
- **Tests (both runners):** pytest 824 passed / 8 skipped (34 subtests); `python3 -m
  unittest discover tools/sla_lib/tests` → Ran 832 tests, OK (skipped=8).

**Working tree:** clean except the known untracked
`site/public/templates/*/template.sla` gallery byproducts (13 of them).

## Deviations from Plan

### Auto-handled / notable

1. **[Setup] Worktree CWD must be the worktree absolute path.** `cd /workspace/vorlagen`
   lands in the MAIN checkout (branch `main`, pre-c8bg0). All commands use the worktree
   path; from there the branch is `issue/bx4d8-…` and c8bg0 is an ancestor (post-c8bg0).

2. **[Rule 1 - Regression] E4 split-headline detection broke after the Task-2 migration.**
   `line_spacing_pixel_audit.parse_textframes_from_build_py` (AST) no longer sees
   headline_stack-emitted frames. Fixed by adding `parse_textframes_from_sla` and
   preferring it in E4 `main` — restores split-group detection AND serves the new audit.

3. **[Task 3b - CORRECTED: defect found + fixed] zweigeteiltes-cover left social icons.**
   SUPERSEDES the earlier "no defect reproduces" conclusion, which was wrong. The
   SCALETYPE invisibility angle was a red herring. The actual defect was a DATA error:
   the three LEFT-column social ImageFrames (u3e7/u3f0/u3f5) all carried the SAME
   uncropped composite-strip inline blob (`f580200d`) instead of distinct facebook/
   instagram/tiktok glyphs. Fixed by mirroring gruenes-cover (the correct reference):
   per-handle crop PNGs via `image=` + `scale_type=0`. Commit d89019e. The other 3
   falzflyers were verified visually as already-correct and were NOT changed.

4. **[Task 3a - tuning] zeitung-a4 leading set to 30pt, not the plan's start-at-31.**
   Measured: 31pt sits at the +0.3pt clip edge in the 79.3pt frame; 30pt gives +1.3pt
   margin while staying looser than the too-tight 28. Claude's-discretion empirical value
   the plan explicitly allows.

5. **[Task 5 - threshold lock] Audit floors locked at min_ratio 0.80 / even_tol 0.18**
   (not the plan's draft 0.85 / 0.15). Even BASELINES yield mildly uneven INK-TOP gaps
   from the Barlow/Vollkorn cap-height delta; the corrected minimum ink-top ratio is 0.832
   and max spread 0.154, so the locked floors clear the cap-height artifact while still
   flagging the pre-fix collapse. This IS the plan's "lock the floor from corrected gaps."

## Discovered Issues

- Pre-existing F401 (unused `Anchor`, `pack_inline_image`) in the generated template
  build.py files and `asdict` in line_spacing_pixel_audit.py — out of scope, not touched.
- The converter `tools/idml_to_dsl.py::_emit_mixed_font_headline` still carries the old
  hardcoded `_FONT_FLOP_ASCENT_RATIO = {"vollkorn": 0.15}`. The templates no longer use
  its output for stacked headlines (they call headline_stack), but if a template is ever
  re-bootstrapped from IDML the converter would re-emit the stale constant. Folding the
  metric helper into the converter is a sensible follow-up (out of this issue's scope).

## Self-Check

- [x] All files from plan exist (headline.py, headline_spacing_audit.py, both test files)
- [x] All commits exist on the branch (1dfb02f, de1af7f, 65ce5e5, 5fb4237, 830b486, e350858)
- [x] All 13 promoted baselines committed (e350858); diff.yml/TOLERANCES.yml untouched
- [x] Full pytest + unittest discover pass (both runners, post-commit)
- [x] No stubs/TODOs/placeholders in new code
- [x] No leftover debug code (only intentional sys.stderr/stdout CLI output)
- [x] No tool attribution in commits/code
- [x] Working tree clean except known untracked site/public/*/template.sla byproducts
- **Result:** PASSED (all 6 tasks complete)

**Completed:** 2026-06-07
**Commits:** 6 source/baseline commits (1dfb02f, de1af7f, 65ce5e5, 5fb4237, 830b486,
e350858) + EXECUTION.md docs commits.
