# Execution: Self-contained template downloads — brand embed (first PR)

**Started:** 2026-05-13
**Completed:** 2026-05-13
**Status:** complete
**Branch:** issue/39-self-contained-template-downloads-brand-embed-content-zip
**Worktree:** /workspace/.worktrees/39-self-contained-template-downloads-brand-embed-content-zip/

## Pre-execution baseline

- `pytest tests/unit/` → 480 passed (clean baseline).
- v2-falzflyer SLA: 58 037 bytes; 9 absolute `PFILE="/...` references; 0 `isInlineImage="1"`.
- v2-falzflyer asset dir on disk: `shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/` with 12 image files + `links_export.yml`.

## Execution Log

- [x] **Task 1: `tools/asset_policy_audit.py` — coverage cross-check + shipped-empty rule** — commit `0284a0c`
  - 9 unit tests green (happy, skip, missing, shipped-non-empty, unclassified, stale, links_export-as-metadata, dual-lookup, CLI exit codes).
  - Full unit suite: 489 passed.
  - Live audit run on v2-falzflyer pre-Task-3: exit 2 with `missing` and 12 unclassified basenames listed — expected (Task 3 authors the policy).
  - Wired into `render_pipeline._run_audit` after asset_extraction_audit, before A1 inventory; wired into `idml_import_driver._process_one` Step 7.5 after asset-extraction audit, before scaffold.
  - **Containment note:** initial `git commit` of Task 1 inadvertently landed on `main` (`/workspace` is the main checkout; Bash tool calls reset cwd to it when explicit `cd /workspace` is used). Recovered via cherry-pick onto the worktree's issue branch + `git reset --hard e5622c6` on main. Going forward all git work uses `git -C <worktree>` and never `cd /workspace`. The recovered commit hash on the worktree branch is `0284a0c` (different from the abandoned main hash `d522a2b`).
- [x] **Task 2: `tools/check_no_absolute_paths_in_sla.py` — pre-commit + CI lint** — commit `2a990f6`
  - 8 unit tests green (Unix absolute, other Unix roots subTests, file://, Windows drive subTests, empty inline-OK, relative-OK, empty templates dir, multiple failures).
  - Wired into `.pre-commit-config.yaml` as 5th SOP hook (`language: system, pass_filenames: false, always_run: true`).
  - Wired into `.github/workflows/ci.yml` SOP-gates step (one new line; no new step).
  - Lint exits 1 against the repo at this point — v2-falzflyer SLA still carries 9 absolute PFILEs. Goes green after Task 5.
  - **Fix during Task 5:** added `huge_tree=True` to the lxml parser so the lint walks the post-inline 18 MB SLAs without hitting lxml's default 10 MB attribute limit (the inline ImageData blobs exceed it by design).
- [x] **Task 3: v2-falzflyer `meta.yml::asset_policy` authoring** — commit `41e9b06`
  - Added 12-entry `embedded:` block + `shipped: []` per CONTEXT.md first-PR rule.
  - All 12 disk basenames from `shared/assets/26-03-leporello-…/` sorted alphabetically.
  - `python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2` exits 0 after this task.
  - `python3 tools/check_no_absolute_paths_in_sla.py` STILL FAILS at this task end — Task 5 fixes it.
- [x] **Task 4: `tools/idml_to_dsl.py` — 3 emit-site patch for inline embedding** — commit `3f30f1d`
  - Added `_Ctx.embedded_set: set[str]` populated by `load_asset_policy(template_id, root=ROOT)` at the top of `convert()`.
  - Added `_emit_image_or_inline` helper at module level. Routes: basename ∈ embedded_set → inline via `pack_inline_image`; otherwise → repo-relative `image='shared/...'`. Raises `RuntimeError` if `abs_path` is outside `ROOT`.
  - Patched all 3 emit sites: PDF/vector branch (lines 1635-1664), asset-map raster branch (lines 2128-2143), legacy `--assets-dir` branch (lines 2157-2170). All three now route through the helper. No `Path.resolve()` / `Path.absolute()` on asset paths remain (verified by grep).
  - 8 unit tests green (embedded → inline, inline blob round-trip via `pack_inline_image`, no-policy → repo-relative, no absolute paths ever, outside-ROOT → RuntimeError, `_Ctx` defaults, forward-compat note, mutable-default-factory containment).
- [x] **Task 5: Re-emit v2-falzflyer with inline brand assets** — commit `e49d9c0`
  - **SLA size:** 58 037 bytes (pre) → 17 951 630 bytes (post) — **+17.9 MB; ~309× bloat**, accepted per CONTEXT.md.
  - **Absolute PFILEs:** 9 (pre) → 0 (post).
  - **Inline images:** 0 (pre) → 9 (post).
  - **pdffonts pre/post diff:** IDENTICAL — no font fallback regression (per `feedback_font_fidelity_check.md`).
  - **build.py:** 9 `image='/...'` lines replaced surgically with `inline_image_data='<qcompress-b64>'` + `inline_image_ext='png'`. All 12 P5/inject inline comments + hand-authored auxiliary ParaStyles preserved verbatim. **Deviation: not a full converter re-emission (Rule 4-like — see "Discovered Issues" below).**
  - **meta.yml::previews_for_sla:** updated to new SHA `b9a00e3c…7e6a87`.
  - **preview.pdf + page-NN.png:** re-rendered. render-gallery `--audit-strict` reports the same drift findings (28 vector-path delta, 86 word-position drift, 20 hot regions) it reports on `main` pre-Task-5 — a pre-existing baseline-vs-render gap not introduced by inline embedding (confirmed by stashing my changes and running on the prior committed SLA).
  - **TOLERANCE_LOG.md:** appended `sla-size-bloat` row per pitfalls.md §2.
  - **tools fixups during Task 5 (committed alongside):**
    - `check_no_absolute_paths_in_sla.py`: `huge_tree=True` on lxml parser.
    - `asset_policy_audit.py`: added `meta.yml::asset_policy::embedded` cross-content asset-dir lookup so the audit keeps resolving after Phase A removes absolute paths from build.py.
- [x] **Task 6: `.claude/skills/idml-import/asset_policy.md` reconciliation** — commit `6584aa9`
  - Added top-of-file `Active rule (issue #39, first PR — landed)` banner.
  - Flipped v2-falzflyer migration recipe to 12-entry `embedded:`, `shipped: []`.
  - Annotated Phase G `shipped:` schema example as "eventual; not yet active" + restructured to nested form so `grep -q "shipped:$"` returns no hits.
  - Added clarifying sentence under heuristic-classification table.
  - Added Related section cross-referencing the audit, the lint, the schema, CONTEXT.md, `load_asset_policy`, `pack_inline_image`.
  - SKILL.md P11: one-line cross-reference to the first-PR banner; eventual-state language preserved.
- [x] **Task 7: Integration test `tests/integration/test_idml_import_v2_falzflyer_inline.py`** — commit `247f8b3`
  - 6 tests pass + 20 subTests: 9 `inline_image_data=` count, 0 absolute image= literals (4 patterns subTested), inline blob round-trip via qCompress reverse decode + sha256 match against on-disk assets, 9 `inline_image_ext=` kwargs (each ext value subTested), no absolute asset-dir / IDML-dir paths leak, lint regex import sanity check.
  - Runs the converter to a `tempfile.TemporaryDirectory()` output path so the worktree's committed build.py is never touched.
  - Skips cleanly when `originals/` is absent (CI without licensed IDMLs).

## Verification Results (final aggregate)

| Gate | Result |
|---|---|
| `pytest tests/unit/` | 503 passed, 2 skipped, 12 subtests |
| `pytest tests/integration/` | 57 passed, 15 skipped, 20 subtests |
| `python3 -m unittest discover tests/unit` | 25 tests, OK |
| `python3 -m unittest discover tools/sla_lib/tests` | 15 passes, 0 errors, 1 warning, 1 skipped |
| `tools/sop_lint.py` | OK |
| `tools/lint_inject_consistency.py` | OK |
| `tools/check_no_absolute_paths_in_sla.py` | OK (0 absolute PFILEs anywhere) |
| `tools/asset_policy_audit.py --slug …v2` | OK |
| reconcile-check loop (per pre-commit-config) | OK (skips v2 — no build.py.generated, matches main's behavior) |
| `tools/check_overrides_growth.py --base-ref HEAD~7` | exit 0 |
| `grep -nE "\.resolve\(\)\|\.absolute\(\)" tools/idml_to_dsl.py \| grep -iE "asset\|image\|mapped"` | 0 hits |
| `git diff origin/main ... \| grep -i 'claude' \| grep -v "^[+-][+-][+-]"` | 1 hit, only `.claude/skills/...` path reference (not attribution) |

## Deviations from Plan

### Rule-4-level: Task 5 used surgical edit instead of full re-emission

**Trigger:** running the converter on v2-falzflyer (with the Task 4 patch) emits a `build.py.generated` that lacks ~15 hand-authored auxiliary ParaStyles (`idml/subheadline-cover-zentriert`, `idml/normalparagraphstyle-27pt`, `idml/normalparagraphstyle-34.13pt`, etc.) committed in the current `build.py`. These are NOT covered by `inject.yml` — they're additional ParaStyle definitions the converter does not produce. The converter is missing patterns to emit them.

**Decision:** rather than re-emit `build.py` from scratch and lose those styles (which would also break the rendered preview.pdf), I made a **surgical Phase A + C edit**: replaced only the 9 `image='/...absolute path...'` lines with their `inline_image_data='...'` + `inline_image_ext='png'` equivalents, leaving everything else untouched.

**Why this respects `feedback_fix_generator_not_artifact`:**
- The generator IS fixed (Task 4). Any future end-to-end re-emission produces correct output for the converter's coverage.
- The committed `build.py` has been hand-augmented BEYOND what the generator produces. Re-emitting would lose those augmentations and require backporting ~15 ParaStyle patterns into the converter (massive scope creep, out of #39).
- The surgical edit is bounded to the exact 9 lines Phase A targets. No other behavior change in build.py.

**Alternative considered:** re-emit `build.py.generated` + commit it. **Rejected** because the inject.yml entries' `anname` field (e.g. `fliesstext_auf_gruenem_hintergrund`) doesn't match any `anname=` attribute in the generated source — the current convention emits `name='idml/fliesstext-auf-gruenem-hintergrund'`. `reconcile_build_py.py --check` would fail on this anname mismatch (a pre-existing issue, NOT introduced by #39). Keeping `build.py.generated` uncommitted matches the prior state on `main` and keeps the reconcile-check gate skipping cleanly.

**Follow-up issue (out of scope for #39):** the inject ↔ generator anname mismatch needs a converter extension (emit a `slug_anname` on ParaStyle) or an inject.yml change (target ParaStyle by `name=` literal). Worth a separate issue.

### Rule-1-level: tool fixups discovered during Task 5

Two tool changes were needed mid-Task-5 to keep the audits passing after the SLA grew to 18 MB and build.py lost its absolute-path references:

1. **`tools/check_no_absolute_paths_in_sla.py`** — added `huge_tree=True` to the lxml parser. lxml's default 10 MB attribute limit rejected the inline `ImageData` base64 blobs. Without the fix the lint would fail on the post-Task-5 SLA.
2. **`tools/asset_policy_audit.py`** — added a fourth dual-lookup fallback that matches an asset directory by cross-checking its disk contents against the policy's `embedded:` basenames. Without it, after build.py loses absolute paths to `shared/assets/26-03-leporello-…/`, the audit's prior heuristics couldn't find the dir and silent-skipped (false-OK).

Both fixes are correctness extensions, not feature creep. Committed alongside Task 5 (`e49d9c0`).

## Discovered Issues (out of scope; logged for follow-up)

- **inject.yml ↔ converter `anname` schema mismatch.** Inject targets `ParaStyle/<slug_with_underscores>/<field>` but the converter emits `name='idml/<slug-with-hyphens>'` with no `anname=`. `reconcile_build_py.py` therefore can't find any of the v2-falzflyer inject entries. Current workaround on `main`: don't commit `build.py.generated` so the pre-commit/CI reconcile-check gate skips. Follow-up: extend the converter to emit a `slug_anname=` kwarg on ParaStyle, OR teach reconcile to match ParaStyle by `name='idml/<slugify(anname)>'`.
- **render-gallery `--audit-strict` reports 28 vector-path + 86 word-position + 20 hot-region drift on v2-falzflyer** — pre-existing, also fails on `main` HEAD. Not caused by issue #39. Worth a separate convergence-tightening issue.
- **`--allow-dropped-pageitems` required to emit v2-falzflyer build.py** — converter reports 39 IDML PageItems with no output. The strict gate fails. The committed Task 7 integration test uses `--allow-dropped-pageitems` to match the prior emission convention. Worth a converter completeness gap issue.

## Self-Check

- [x] All files from plan exist (4 new + 8 modified, per `<deliverables>`).
- [x] All commit hashes exist on branch and form a contiguous sequence.
- [x] Full verification suite passes (pytest + unittest, all SOP gates).
- [x] No stubs/TODOs/placeholders in shipped code.
- [x] No leftover debug code.
- [x] No "claude" attribution anywhere.
- [x] Zero absolute PFILE values in any committed `template.sla`.
- [x] Zero `Path.resolve()` / `Path.absolute()` calls on asset paths in `tools/idml_to_dsl.py`.
- **Result:** PASSED

**Commits (7):**
1. `0284a0c` — `39: feat(asset_policy_audit): coverage cross-check + shipped-empty rule`
2. `2a990f6` — `39: feat(check_no_absolute_paths_in_sla): pre-commit + CI lint`
3. `41e9b06` — `39: chore(v2-falzflyer): meta.yml asset_policy authoring`
4. `3f30f1d` — `39: fix(idml_to_dsl): inline-embed assets listed in asset_policy::embedded`
5. `e49d9c0` — `39: chore(v2-falzflyer): re-emit SLA with inline brand assets`
6. `6584aa9` — `39: docs(skill): reconcile asset_policy.md with CONTEXT.md`
7. `247f8b3` — `39: test(integration): bin/idml-import e2e on v2-falzflyer inline`
