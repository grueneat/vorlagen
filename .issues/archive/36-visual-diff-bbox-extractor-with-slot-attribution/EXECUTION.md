# Execution: Visual-diff bbox extractor with slot attribution

**Started:** 2026-05-11
**Status:** complete
**Branch:** worktree-agent-a5fe140ce16395d13 (nested agent worktree under issue/36-...; harness merges back)

## Execution Log

- [x] Task 1: Bootstrap `tools/diff_bbox_extract.py` — CLI + error class, no logic yet
  - Commit: `428ae26` 36: feat(visual-diff): bootstrap diff_bbox_extract.py CLI + DiffBBoxError
  - Files: `tools/diff_bbox_extract.py`
- [x] Task 2: ImageMagick connected-components shell-out + parse
  - Commit: `f55971b` 36: feat(visual-diff): extract_bboxes_px via IM HSL-saturation thresholding
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
  - Deviation: [Rule 1 - Bug] Switched IM threshold pipeline from
    `-colorspace Gray -threshold 90% -negate` (plan-prescribed) to
    `-colorspace HSL -channel G -separate +channel -threshold 30%`. The
    luma path mis-classified the baseline-tinted matched area (e.g.
    pixel `(210,227,215)` luma ~218 < 229.5) as diff, producing a single
    226897-px "background" bbox per page on the real
    `build/validation/postkarte-a6-kampagne/diff-page-01.png` fixture.
    HSL saturation cleanly separates the saturated red overlay (high S)
    from the tinted-matched pixels (S near 0). Matches RESEARCH.md
    pitfalls guidance ("Use threshold ~200 on red channel, OR check IM's
    mean-color column directly when using the connected-components
    path"). The locked decision #2 spirit ("threshold for non-white
    pixels in red-on-white RGBA delta") is preserved — just via a
    different IM primitive.
- [x] Task 3: DPI lookup + px to mm conversion
  - Commit: `fb7a4c7` 36: feat(visual-diff): load_dpi() + px_to_mm_bbox() with 0.1mm rounding
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 4: Slot loader using `load_build_module` + `frame_bbox_mm`
  - Commit: `f8a236e` 36: feat(visual-diff): load_template_slots() reusing audit_alignment idiom
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 5: Slot attribution math + candidates list
  - Commit: `2b7b511` 36: feat(visual-diff): slot attribution math + top-3 candidates
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 6: JSON assembly + determinism guarantees
  - Commit: `886b3c7` 36: feat(visual-diff): extract_all + write_json pipeline (determinism)
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 7: Red-overlay PNG output (`--overlay-out`)
  - Commit: `acec0c5` 36: feat(visual-diff): --overlay-out writes red bbox outlines on dsl PNGs
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 8: CLI end-to-end integration test on real visual_diff.py output dir
  - Commit: `6420f35` 36: test(visual-diff): integration tests against real postkarte fixture
  - Files: `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 9: Wire `--extract-bboxes` flag into `tools/visual_diff.py`
  - Commit: `7e2d0d7` 36: feat(visual-diff): wire --extract-bboxes flag in visual_diff.py
  - Files: `tools/visual_diff.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 10: Strict-mode UX + edge cases
  - Commit: `0741cd5` 36: feat(visual-diff): strict-mode UX in main() + edge-case tests
  - Files: `tools/diff_bbox_extract.py`, `tools/sla_lib/tests/test_diff_bbox_extract.py`
- [x] Task 11: Documentation: module docstring + defaults reference + visual_diff.py note
  - Commit: `c05e03d` 36: docs(visual-diff): expand diff_bbox_extract docstring with JSON schema
  - Files: `tools/diff_bbox_extract.py` (visual_diff.py docstring was updated in task 9)
- [x] Task 12: End-to-end smoke + ISSUE.md acceptance-criteria pass
  - No new code; verification only. All checks below passed.

## Verification Results

**Unit tests (`python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract`):**
38 tests, 0 failures, 0 errors, runtime ~4.3 s.

**Full test suite (`python3 -m unittest discover tools/sla_lib/tests/`):**
917 tests, 0 failures, 0 errors, 11 skipped, runtime ~24.6 s.

**End-to-end smoke (`postkarte-a6-kampagne`):**

| Step | Result |
|---|---|
| `python3 tools/visual_diff.py … --ci --out build/validation/postkarte-a6-kampagne/` | exit 1 (tolerance violation expected, artifacts written) |
| `python3 tools/diff_bbox_extract.py build/validation/postkarte-a6-kampagne/ --template-slug postkarte-a6-kampagne --overlay-out` | exit 0, 30 bboxes across 2 pages, 30/30 attributed |
| `diff_bboxes.json` schema | `{dpi, template_slug, pages}` top-level; per-page `{page, delta_png, bboxes}`; per-bbox `{bbox_px, bbox_mm, area_px, mismatch_pct_in_bbox, attributed_slot, attribution_overlap_pct, attribution_candidates}` ✓ |
| `diff-page-{01,02}-overlay.png` | present, RGBA, correct dimensions ✓ |
| Two-run byte-equal: `sha256sum diff_bboxes.json` × 2 | `7b862cd7decfa06c380f81da2d224e7d63d5242ccaeb1463419e490b2ff645a1` × 2 ✓ |
| `--json-out /tmp/db1.json` + `--json-out /tmp/db2.json` + `diff` | empty (byte-equal) ✓ |
| Wrapped: `tools/visual_diff.py … --extract-bboxes --template-slug postkarte-a6-kampagne` | merged `visual_diff.json` has `pages[*].bboxes`; existing keys preserved ✓ |

**Acceptance criteria (ISSUE.md):**
- [x] `tools/diff_bbox_extract.py` exists with documented usage
- [x] Run against existing template's visual_diff output dir produces `diff_bboxes.json` + optional overlay PNGs
- [x] Slot attribution works for at least one template (postkarte-a6-kampagne: 30/30 bboxes attributed to "Seitenhintergrund" with "P1 Hero" as second candidate)
- [x] Output deterministic (byte-equal on re-run, sha-confirmed)
- [x] `visual_diff.py --extract-bboxes` merges JSON cleanly
- [x] Tests cover noisy-AA filtering (`test_below_min_area_filtered`), multi-cluster pages (`test_two_separated_rects_two_bboxes`, `test_extract_all_sorts_bboxes_by_y_then_x`), and unattributed bbox (`test_attribute_no_match_below_threshold`)

**Other invariants:**
- No new runtime dependencies (no Dockerfile.claude or requirements.txt change)
- All commits prefixed `36: <type>(<scope>): <subject>` per `.issues/config.yaml`
- No TODOs / FIXMEs / debug code in the new modules

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 1 - Bug] Switched IM threshold from luma to HSL saturation (task 2)**
   - Found during: Task 2 empirical fixture validation
   - Issue: The plan baked in `-colorspace Gray -threshold 90% -negate`,
     but the real `diff-page-01.png` from `compare -metric AE -fuzz 25%`
     has matched-but-tinted background pixels around luminance 215
     (below 90% of 255 = 229.5). The luma threshold therefore classified
     the entire matched area as a single 226897-px diff blob, breaking
     the extractor on real input.
   - Fix: Use HSL saturation channel thresholding at 30% —
     `convert ... -colorspace HSL -channel G -separate +channel -threshold 30%`.
     Saturation is high for the red overlay and ~0 for both pure-white
     and grey-tinted matched pixels, so the discriminator is clean.
   - Files: `tools/diff_bbox_extract.py`
   - Commit: `f55971b`
   - Sanity check: yields 19 sensibly-sized bboxes on page 01 (largest
     79×80 px, smallest at min_area_px=100), 11 on page 02; ALL attributed
     on the real postkarte fixture; byte-equal on re-run.
   - Aligned with: RESEARCH.md pitfalls table ("Use threshold ~200 on red
     channel, OR check IM's mean-color column directly when using the
     connected-components path"). Locked decision #2's spirit
     ("threshold for non-white pixels in red-on-white RGBA delta") is
     preserved, just via a different IM primitive.

### Blocked (Rule 4)

None.

## Discovered Issues

- The postkarte-a6-kampagne template only has two named slots
  (`Seitenhintergrund` covering the whole page and `P1 Hero` covering
  most of the body). Every extracted bbox attributes to
  `Seitenhintergrund` at 100% coverage because the background slot
  encompasses every other slot. This is accurate to the template's slot
  geometry but means the dataset isn't a strong stress-test for the
  smaller-slot tie-break logic. A template with more granular named
  slots (e.g. `kandidat-falzflyer` which has distinct `P1 Top-Band`,
  `P1 Headline`, `P1 Kandidat-Portrait`, etc.) would exercise the
  attribution math more thoroughly. Recommend running the extractor
  against the kandidat-falzflyer build in a follow-up validation.
- ResearchMd suggested making `mismatch_pct_in_bbox` honour
  `area_px / (w_px * h_px) * 100` (density of diff inside the bbox).
  Implemented as documented. On the real fixture this lands around
  60-80% for most bboxes, which makes sense for solid glyph drift but
  could surface as a future per-region threshold knob.

## Environment notes

- ImageMagick 7.1.1-43 Q16 aarch64, Pillow 12.2.0, PyYAML 6.0.3,
  scribus, pdftoppm all present in container.
- Running in nested agent worktree at `.claude/worktrees/agent-a5fe140ce16395d13/`
  under the issue worktree; orchestrator harness merges results back to
  `issue/36-visual-diff-bbox-extractor-with-slot-attribution`.

## Self-Check

- [x] All files from plan exist (`tools/diff_bbox_extract.py` 638 lines,
  `tools/sla_lib/tests/test_diff_bbox_extract.py` 733 lines,
  `tools/visual_diff.py` modified)
- [x] All 11 commits exist on branch (verified via `git log --oneline`)
- [x] Full verification suite passes (38/38 new tests + 917/917 discover)
- [x] No stubs/TODOs/placeholders/HACK/FIXME/XXX in new files
- [x] No leftover debug code (no `console.log` / `breakpoint()` / `pdb`)
- [x] Python `py_compile` clean on all three touched modules
- [x] No new runtime dependencies (Dockerfile.claude untouched)
- **Result:** PASSED

**Completed:** 2026-05-11
**Duration:** single session
**Commits:** 11 (428ae26..c05e03d)
