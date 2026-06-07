# Execution: Vorlagen — Überschriften-Zeilenabstände (Barlow/Vollkorn), Falzflyer-Social-Icons, Abstands-Audit

**Started:** 2026-06-07
**Status:** tasks_0_5_complete (Task 6 pending human visual sign-off)
**Branch:** issue/bx4d8-vorlagen-überschriften-zeilenabstände-bei-barlowvollkorn-korrigieren-falzflyer-s
**Scope:** Tasks 0–5 only. Task 6 (baseline promotion) is GATED on the main agent's focused visual review — NOT done here.

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
- [~] Task 3b: falzflyer social icons — NO SOURCE CHANGE NEEDED (see Deviations)
  - Disambiguated root cause: all 4 falzflyers' inline social-icon frames are
    white-on-transparent RGBA PNGs (colortype 6, opaque pixels pure white) — exactly
    the profile that triggers the Scribus 1.6.x SCALETYPE=1 invisibility bug.
  - BUT every inline frame already emits SCALETYPE=0 (the ImageFrame default, no
    override) — the source-level safeguard from RESEARCH cause (a) is ALREADY in place.
  - Rendered all 4 falzflyers headless: the icons render correctly and visibly
    (Instagram/butterfly, globe, envelope, etc. — see /tmp/icons_region.png inspection),
    and render IDENTICALLY to the committed baseline.pdf. No defect reproduces in the
    post-c8bg0 state. Making a change here would alter working code (rejected).
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
- [ ] Task 6: Human visual sign-off + baseline promotion — PENDING (main agent)

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
**bin/validate:** NOT run to green here — sla_diff/visual_diff compare against the
pre-fix baselines, which the intended geometry change exceeds; that is resolved by
the Task-6 baseline promotion (gated on human sign-off). The headline_spacing static
gate I added to bin/validate passes.

## Deviations from Plan

### Auto-handled / notable

1. **[Setup] Worktree CWD must be the worktree absolute path.** `cd /workspace/vorlagen`
   lands in the MAIN checkout (branch `main`, pre-c8bg0). All commands use the worktree
   path; from there the branch is `issue/bx4d8-…` and c8bg0 is an ancestor (post-c8bg0).

2. **[Rule 1 - Regression] E4 split-headline detection broke after the Task-2 migration.**
   `line_spacing_pixel_audit.parse_textframes_from_build_py` (AST) no longer sees
   headline_stack-emitted frames. Fixed by adding `parse_textframes_from_sla` and
   preferring it in E4 `main` — restores split-group detection AND serves the new audit.

3. **[Task 3b - no defect reproduces] Falzflyer social icons already render correctly.**
   Root cause disambiguated: the icons ARE white-on-transparent RGBA PNGs (the profile
   that triggers the Scribus 1.6.x SCALETYPE=1 invisibility bug), but every inline frame
   already emits SCALETYPE=0 (the ImageFrame default, no override) — the RESEARCH cause-(a)
   safeguard is already in place. Rendered all 4 falzflyers: icons render visibly
   (Instagram/butterfly, globe, envelope) and IDENTICALLY to the committed baseline.pdf.
   No source change made — fixing would alter working code (rejected per honest reporting).

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
- [x] All 5 commits exist on the branch (1dfb02f, de1af7f, 65ce5e5, 5fb4237, 830b486)
- [x] Full pytest + unittest discover pass (both runners)
- [x] No stubs/TODOs/placeholders in new code
- [x] No leftover debug code (only intentional sys.stderr/stdout CLI output)
- [x] No tool attribution in commits/code
- **Result:** PASSED (Tasks 0–5; Task 6 baseline promotion pending human sign-off)

**Tasks 0–5 completed:** 2026-06-07
**Commits:** 5 (+ this EXECUTION.md)
**Task 6:** PENDING — gated on the main agent's focused headline-spacing visual review.
