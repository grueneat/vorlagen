# Execution: Zentralisierte Demo-Bild-Bibliothek + alle Templates auffüllen

**Started:** 2026-05-08T08:07:00Z
**Status:** complete
**Branch:** issue/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen

## Execution Log

- [x] Task 1: Pin Pillow + add jsonschema in Dockerfile and CI workflow — commit b5e7d10
- [x] Task 2: Refactor add_demo_watermark to be importable from library module — commit ba7915c
- [x] Task 3: Implement library module + JSON schema + tests (foundation) — commit 31e1a81
- [x] Task 4: Add --library flag to codex_image_gen.py + library-mode manifest parser — commit 3500aa8
- [x] Task 5: Migrate 7 existing images via git mv + assemble shared/sample-images/manifest.yml — commit 79c6bc6
- [x] Task 6: Generate 6 new Codex images for library — commit 64ee842
  - All 6 generated on first attempt (no retries needed). Cost ~$0.48 total.
  - Sizes: gemeindebau=290KB, erwachsenenbildung=154KB, handwerk=199KB,
    radweg=253KB, versammlung=261KB, stammtisch=128KB.
- [x] Task 7: Refactor 5 new templates' build.py to use library.load() — commit b35e061
- [x] Task 8: Patch render_pipeline.py to prefer template-preview.sla — commit b96f802
- [x] Task 9: Refactor postkarte-a6-kampagne build.py with build_template/build_preview split — commit b060d75
- [x] Task 10: Refactor plakat-a1-hochformat build.py with build_template/build_preview split — commit 4e26e03
- [x] Task 11: Refactor zeitung-a4-grun build.py with build_template/build_preview split — commit 5efb8b4
  - 11 ImageFrame slots gained annames so build_preview() can locate them
    (sla_diff treats ANNAME as INFO; round-trip stays green).
- [x] Task 12: Final cross-cutting verification — commit 5c9d1ce (gallery render pass)
  - All 8 builds OK; 3 production round-trips GREEN; check-stale-previews clean;
    321 unit tests pass; bin/render-gallery 8/8 OK.
- [x] Task 13: Visual review pass — commit 614438d (reviews/library-content-iter1.md)
- [ ] Task 14: Push branch and open PR (next)

Plus a chore-level rebuild commit:
- 84707e3: rebuild templates after full 13-image library available

## Verification Results

**Tests:** 321 passed, 0 failed
- 17 new tests in test_library.py
- 11 new tests in test_codex_image_gen.py (apply_watermark_to_image,
  parse_library_manifest, regen_library)
- 2 new tests in test_render_pipeline.py (_select_render_source)
- All pre-existing tests still pass

**Linter:** N/A (project doesn't enforce ruff/flake8 in CI)

**Types:** N/A (no mypy gate in CI)

**Round-trip diff (3 production templates, --strict --allow-brand-extras):**
- postkarte-a6-kampagne: 0 critical, 0 warnings, 3 INFO (anname-differs) — green
- plakat-a1-hochformat: 0 critical, 0 warnings, 1 INFO (anname-differs) — green
- zeitung-a4-grun: 0 critical, 0 warnings, 18 INFO (anname-differs) — green

**bin/check-stale-previews:** clean for all 8 templates.

**bin/render-gallery:** 8/8 OK; production templates correctly render from
template-preview.sla per the new pipeline patch.

**library.validate_manifest():** [] (empty error list — schema-clean).

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 3 — Blocker] Worktree git registry recreated twice during execution**
   - The corruption noted in `feedback_worktree_prune_corrupts_others` triggered
     midway through Task 5. Repaired by recreating
     `.git/worktrees/<slug>/{HEAD,commondir,gitdir,refs,logs}` from scratch and
     running `git reset --mixed HEAD` to restore the index. No commits lost.

2. **[Rule 3 — Blocker] kontext_infostand_szene mtime-regen race**
   - Background codex regen ran longer than the manifest mtime touch I applied
     before kicking it off; once the manifest got Edit-tool-modified at 08:34
     (entries 8-13 added), the manifest mtime moved past the existing 08:30
     image mtimes, so codex regenerated `kontext/infostand-szene.jpg` from the
     new prompt rather than skipping the migrated bytes.
   - Restored from git (`git checkout HEAD -- shared/sample-images/kontext/infostand-szene.jpg`),
     then rebuilt all 8 templates with full library and committed final SLA
     bytes.
   - Documented as RESEARCH §8.6 caveat — manifest mtime triggers regen.

### Blocked (Rule 4)

None.

## Discovered Issues

- The codex log file (`/tmp/codex-13-libgen.log`) only flushed at process end
  due to tee buffering; not a real bug, just observation.
- `tools/visual_review.py` requires external vision-model auth which isn't
  available in this container; ran a programmatic surrogate check (watermark
  band visible on every library image) and manual inspection of rendered
  page-*.png — verdict: merge-ready.

## Self-Check

- [x] All files from plan exist (library.py, manifest.yml, 13 JPGs,
      template-preview.sla × 3, samples/manifest.yml × 4 new dirs)
- [x] All commits exist on branch (14 issue commits + 4 pre-issue artifact
      commits)
- [x] Full verification suite passes (321 tests, round-trip green, render
      green, brand CI green)
- [x] No stubs/TODOs/placeholders in shipped code
- [x] No leftover debug code (no `print` outside __main__, no breakpoints)
- **Result:** PASSED

**Completed:** 2026-05-08T08:55:00Z (approximately)
**Duration:** ~48 minutes
**Commits:** 14 issue-prefixed commits on branch (plus 4 pre-issue setup commits)
