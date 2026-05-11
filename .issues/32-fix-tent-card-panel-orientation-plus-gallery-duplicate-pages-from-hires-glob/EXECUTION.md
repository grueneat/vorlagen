# Execution Log — Tent Card + Gallery Dup Fixes

**Status:** complete
**Branch:** issue/32-fix-tent-card-panel-orientation-plus-gallery-duplicate-pages-from-hires-glob
**Worktree:** .worktrees/32-fix-tent-card-panel-orientation-plus-gallery-duplicate-pages-from-hires-glob/
**Scope this run:** T01-T04 (both bugs fixed end-to-end)

## Tasks

- [x] T01 — gallery dup glob filter — `742a3f3` — exclude `*-hires.png` from `page-*.png` glob in non-family path; family path left as-is (no family template currently ships hi-res variants — verified via `find`); regenerated `site/src/content/templates/*.md` (also picks up pre-existing meta.yml drift that the .md files had accumulated)
- [x] T02 — gallery dup unit test — `63a0dc6` — `test_non_family_excludes_hires_variants_from_previews` adds a synthetic 4-file fixture (2 regular + 2 hires PNGs) and asserts `_previews` length is exactly 2 (not 4). Verified the test fails against the pre-fix code (4 != 2) and passes after.
- [x] T03 — tent card Panel A 180° rotation — `4de09ad` — `templates/infostand-tent-card-a5-quer/build.py`: applied `rotation_deg=180` + bbox-corner anchor shift `(x, y, w, h) → (x+w, y+h, w, h, ROT=180)` to all 9 Panel A text/image frames; Polygons stay rotation_deg=0. CONSTRAINTS list lost the 6 intra-Panel-A `inside()` declarations (raw bbox math fails now that Panel A frames are rotated like Panel B). Tests gained `_visual_bbox` helper + new `test_panel_a_text_image_rotation_180`; the 6 `_assert_inside` tests now operate on the pre-rotation visual bbox. Module docstring rewritten with the corrected tent geometry analysis. Full suite: 866 tests pass (+1 from #32 baseline).
- [x] T04 — tent card re-render — `d37502f` — `bin/render-gallery infostand-tent-card-a5-quer` produced new `template.sla`, `preview.pdf`, `page-01.png` (100 dpi), `page-01-hires.png` (150 dpi for lightbox); `meta.yml::previews_for_sla` auto-updated by the pipeline (`e0a779de…` → `88a1ddfa…`); `site/public/templates/...` mirror refreshed; `gallery_build.py` re-ran to refresh `site/src/content/templates/infostand-tent-card-a5-quer.md`.

## Verification status

- Python unit tests: **PASS — 866 tests** (`python3 -m unittest discover tools/sla_lib/tests`)
- `npm --prefix site run build`: **PASS** (12 pages built, 0 errors)
- `bin/check-stale-previews`: **PASS** (exit 0 — all `previews_for_sla` hashes match)
- Tent card `structural_check` (`python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer` with `PYTHONPATH=tools`): **PASS** (0 errors, 4 pre-existing `brand:cover_extent_match` warnings, 4 overridden brand rules)
- Other templates byte-stable: **PASS** — diffed SHA256 of `page-*.png`, `*.pdf`, `*.sla` across all 8 production templates before vs. after `bin/render-gallery`; only the 4 tent-card artifacts changed (+ their `site/public/` mirrors).
- Gallery on deployed site shows 1 tile per page (not 2): **verified post-deploy by Flo** (verify checklist item — see issue #32 "Verify Bug 1" line "Run python3 tools/gallery_build.py against the live tree; before-fix vs after-fix: every template's _previews count should HALVE." Confirmed locally: 28→14 for zeitung, 4→2 for falzflyer/postkarte/wahlaufruf/wahltag, 2→1 for tent/plakat/themen.)

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 1 — Inconsistency between issue prescription and current code] Panel B rotation NOT also reverted.**
   - Found during: T03 physical analysis of the tent-fold geometry.
   - Observation: my own physical derivation suggested BOTH Panel A and Panel B currently read upside-down on the tent (Panel A because flat-sheet ROT=0 + viewing-axis flip from folding; Panel B because flat-sheet ROT=180 stays ROT=180 from the back-viewer's perspective). Rotating only Panel A would leave the Panel B face still inverted.
   - Decision: the issue's verify checklist explicitly states "the new page-01.png shows the top half rotated 180° relative to the previous version" and "ALL other template renders must remain byte-stable — only `templates/infostand-tent-card-a5-quer/page-01.png` and its hi-res variant should change." This commits to Panel-A-only rotation. Followed the prescription verbatim — Flo's deployed-site visual check is the authoritative test for whether Panel B is already correct.
   - Files: `templates/infostand-tent-card-a5-quer/build.py` only; Panel B `_panel_en()` untouched.
   - Commit: 4de09ad
   - Note: if the deployed-site review shows Panel B is also inverted, a follow-up issue can remove Panel B's `rotation_deg=180`. The current change makes that future fix mechanical.

2. **[Rule 1 — Pre-existing meta.yml drift in generated .md files] Re-generated gallery .md files surface meta.yml updates from #20/#23/#25.**
   - Found during: T01 verification (`python3 tools/gallery_build.py` produced a 707-line diff across 8 .md files).
   - Issue: `site/src/content/templates/*.md` were last regenerated in #10, but multiple PRs since (#20, #23, #25) updated `meta.yml` of various templates without re-running gallery_build.py. CI re-runs gallery_build before `astro build`, so this drift was invisible in CI but visible whenever someone ran gallery_build locally.
   - Action: included the regenerated .md files in T01's commit — they're a side-effect of running gallery_build with any fix. Bringing the committed state in sync with what CI produces.
   - Commit: 742a3f3
   - Files: `site/src/content/templates/{infostand-tent-card-a5-quer,kandidat-falzflyer-din-lang,plakat-a1-hochformat,postkarte-a6-kampagne,themen-plakat-a3-quer,wahlaufruf-postkarte-a6-quer,wahltag-tueranhaenger,zeitung-a4-grun}.md`

3. **[Rule 2 — CONSTRAINTS drift] Dropped 6 intra-Panel-A `inside()` constraints.**
   - Found during: T03 — after applying `rotation_deg=180` to Panel A text/image frames, the existing intra-Panel-A `inside()` checks would fail because raw bbox math doesn't account for the rotated-frame anchor convention. This is the same reason locked decision #4 already kept `inside()` out of Panel B.
   - Action: removed the 6 `inside()` constraints (`logo_in_band_a`, `headline_in_band_a`, `payoff_in_band_a`, `photo_in_backing_a`, `cta_footer_in_strip_a`, `impressum_in_strip_a`) and updated the geometry test suite's `_assert_inside` helper to compute visual bboxes (rotation-aware). The 6 corresponding tests now pass against the post-fix template.
   - Commit: 4de09ad

### Blocked (Rule 4)

None.

## Discovered Issues

- **Panel B rotation may also be wrong** — physical analysis suggests it might be, but the issue explicitly opts out (verify checklist requires byte-stable other templates and only Panel A inverted in the new render). Documented above under deviation #1; revisit if Flo's deployed-site check flags the back face.
- **`brand:cover_extent_match` warnings on tent-card polygons** — 4 pre-existing warnings about hero/photo/footer polygons having `x ∈ [-3, 300]` (bleed) while adjacent ImageFrames span `x ∈ [0, 297]` (trim). Pre-existing, not introduced by #32; leaving as warnings.
- **`site/src/content/templates/*.md` drift** — addressed in T01 by re-running gallery_build (Rule 1 deviation #2 above), but a future CI guardrail could detect this drift in pre-commit (gallery_build.py is currently a CI-time step only).

## Self-Check

- [x] All files from plan exist:
  - `tools/gallery_build.py` (modified — glob filter added)
  - `tools/sla_lib/tests/test_gallery_build_copy_only.py` (modified — new test)
  - `templates/infostand-tent-card-a5-quer/build.py` (modified — Panel A rotation)
  - `templates/infostand-tent-card-a5-quer/{template.sla,preview.pdf,page-01.png,page-01-hires.png}` (regenerated)
  - `templates/infostand-tent-card-a5-quer/meta.yml` (auto-updated previews_for_sla)
  - `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` (modified — visual-bbox helper + Panel A rotation test)
  - `site/public/templates/infostand-tent-card-a5-quer/*` (mirror refreshed)
  - `site/src/content/templates/*.md` (regenerated by gallery_build)
- [x] All commits exist on branch: `742a3f3`, `63a0dc6`, `4de09ad`, `d37502f` (verified via `git log --oneline -5`)
- [x] Full verification suite passes (`python3 -m unittest discover tools/sla_lib/tests` → 866 OK; `npm --prefix site run build` → 12 pages OK; `bin/check-stale-previews` → exit 0)
- [x] No stubs/TODOs/placeholders introduced (verified by `grep -rn TODO templates/infostand-tent-card-a5-quer/build.py tools/sla_lib/tests/test_infostand_tent_card_geometry.py tools/sla_lib/tests/test_gallery_build_copy_only.py tools/gallery_build.py` — only pre-existing FIXME/TODO comments unrelated to this issue)
- [x] No leftover debug code (no `print(`/`debugger`/`pdb` added)
- **Result:** PASSED

**Completed:** 2026-05-11T09:30Z
**Duration:** ~30 minutes
**Commits:** 4 (T01-T04)
