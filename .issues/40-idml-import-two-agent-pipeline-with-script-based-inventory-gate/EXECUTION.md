# Execution log

**Started:** 2026-05-13T20:25:51Z
**Status:** complete
**Branch:** issue/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate
**Worktree:** /workspace/.worktrees/40-idml-import-two-agent-pipeline-with-script-based-inventory-gate

## Task 1: Inventory schema sketch (dataclasses, no extractor logic)
- Status: ✓ done
- Commit: 89145d8 "40: feat(inventory): add SCAFFOLD_INVENTORY.yml dataclass schema"
- Verify: pass — `from tools.walkers.schema import Inventory, to_yaml, from_yaml; inv = Inventory(...); assert from_yaml(to_yaml(inv)).template == 'x'` returned OK. Nested round-trip with TextRunBucket, Frames, ColorEntry, AssetEntry, WordsBlock also verified.

## Task 2: IDML walker — rename idml_inventory.py and extend
- Status: ✓ done
- Commit: ce5f1de "40: refactor(inventory): rename idml_inventory.py to walkers/ + add walk_idml"
- Verify: pass — anchor leporello yields 36 text-runs (>=20), 6 paragraph styles (==6), 15 colors (==15), 22 text / 10 image / 15 polygon / 12 group frames, 20 assets. Existing `tests/unit/test_idml_inventory.py` still passes via the back-compat shim.
- Notes: composite_ai_split.yml has a flat `{ai_basename, pages_emitted}` shape — the implementation initially assumed a nested `{parent: {parts}}` and was corrected. Asset walker also handles links_export.yml's `{<original.ai>: {output, vector_output}}` shape.

## Task 3: SLA walker — thin wrapper over SLADocument
- Status: ✓ done
- Commit: 7e85ca0 "40: feat(inventory): add SLA walker — thin wrapper over SLADocument"
- Verify: pass — anchor SLA yields PAGEOBJECT=83, ITEXT=69, PFILE=3, STYLE=14, COLOR=10. No direct lxml.etree.parse — only via SLADocument.

## Task 4: PDF walker — reuse existing audit helpers
- Status: ✓ done
- Commit: 3ac4302 "40: feat(inventory): add PDF walker — words + grouped raster placements"
- Verify: pass with plan-correction — anchor preview/baseline yield 444 words (NFC + ligature-folded via `tools.text_render_audit.extract_pdf_words`). Plan asserted 450 (raw `pdftotext | wc -w`); the 444 number is what the audit tool we reuse actually produces. 6 logical images (grouped from 13 raw rows; smask pairs collapsed per RESEARCH.md pitfall #4), within the [5, 13] band.
- Notes: **[Rule 1 - Plan correction]** Plan's hard-coded 450 was wrong given the implementation reuses `extract_pdf_words` (normalised). 444 is the actual count; documented in the commit message.

## Task 5: build.py walker — AST-based
- Status: ✓ done
- Commit: 3586f98 "40: feat(inventory): add AST-based build.py walker"
- Verify: pass with plan-correction — anchor leporello yields 23 text_frames, 10 image_frames, 16 polygon_frames, 34 manual PolyLines, 6 add_para_style, 3 add_color. text_runs is 57 (not >=90); the plan said >=90 based on a 104-`Run(`-call count, but 47 of those are empty-text paragraph separators (`separator='para'`). 57 = non-empty Run() texts, which is what the gate needs for set-equality. parse_warnings=[] (anchor is 100% literal-kwarg).
- Notes: **[Rule 1 - Plan correction]** Plan's `>=90` text-run assertion was based on raw `Run(` count, not non-empty-text Run() count. Empty Run entries are paragraph separators — including them would inflate without adding gate signal. Adjusted verify to `>=50`.
- inline_image_data correctly hashed (sha256 + byte-length); no base64 leaked into row.

## Task 6: Orchestrator — inventory_extract.py
- Status: ✓ done
- Commit: 953fdae "40: feat(inventory): add inventory_extract.py orchestrator"
- Verify: pass — `python3 tools/inventory_extract.py --slug 26-03-leporello-...` writes a valid SCAFFOLD_INVENTORY.yml. 23 text_frames, 10 image_frames, 6 paragraph_styles, 15 colors, 20 assets, words.preview_pdf_count=444. `--templates-dir`, `--originals-dir`, `--repo-root`, `--output` flags all work. `--output -` writes to stdout. Composite-AI parents appear with `referenced_from_frames: [u3e7, u3f0, u3f5]` sourced from composite_ai_split.yml::pages_emitted[].idml_anname (build.py uses inline_image_data so basename join would have missed them).

## Task 7: Comparator — inventory_compare.py with exit codes 0/2/3
- Status: ✓ done
- Commit: 8e0c552 "40: feat(inventory): add inventory_compare.py with 0/2/3 exit codes"
- Verify: pass — self-compare of leporello inventory exits 0; mutation (drop a build_py_run text) exits 2 with the dropped word under text_runs.missing.
- Notes: schema extended with `text_runs.build_py_runs` (flat list of TextRun) so the comparator can surface "dropped word" mutations.

## Task 8: Driver integration — emit inventory in --scaffold-only path
- Status: ✓ done
- Commit: ffcea42 "40: feat(driver): emit SCAFFOLD_INVENTORY.yml in --scaffold-only path"
- Verify: pass — `python3 tools/idml_import_driver.py --help` shows both `--scaffold-only` and `--no-inventory`; inventory_extract is referenced inside the scaffold-only branch. tests/unit/test_idml_import_driver.py (19 tests) still pass.

## Task 9: Calibration — generate and commit SCAFFOLD_INVENTORY.yml
- Status: ✓ done
- Commit: 1f8e90c "40: chore(calibration): commit SCAFFOLD_INVENTORY.yml for 26-03 leporello"
- Verify: pass — `inventory_compare.py --expected templates/26-03-.../SCAFFOLD_INVENTORY.yml --actual <(extract)` exits 0. Leading comment block on file documents source path, regeneration recipe, and hand-verification numbers.
- Notes: The anchor itself is untracked in main checkout (`/workspace/templates/26-03-leporello-.../`), so the baseline lives at `<worktree>/templates/26-03-leporello-.../SCAFFOLD_INVENTORY.yml` AND is mirrored at `/workspace/templates/26-03-leporello-.../SCAFFOLD_INVENTORY.yml` so default-path runs pick it up. Both copies are byte-identical.

## Task 10: Mutation tests — confirm gate catches regressions
- Status: ✓ done
- Commit: 3b542d3 "40: test(inventory): mutation tests confirm gate catches regressions"
- Verify: pass under BOTH pytest and unittest discover. 3 tests: M1 drop Run text, M2 rename anname='u514', M3 drop add_color — each asserts exit 2 with the dropped element reported in the correct missing section.
- Notes: Tests live at `tests/unit/test_inventory_gate_mutations.py` (plan said `tests/` which doesn't match the repo's `tests/unit/` convention; the actual location matches `test_idml_inventory.py` etc.).

## Task 11: Skill split — duplicate idml-import into idml-scaffold + idml-tune
- Status: ✓ done
- Commit: 29fd56f "40: docs(skills): split idml-import into idml-scaffold + idml-tune"
- Verify: pass — both new SKILL.md files exist, reference both inventory CLIs; idml-tune lists forbidden paths including the converter and sla_lib. Sub-docs redistributed per Decisions table.

## Task 12: SOP rewrite in idml-tune
- Status: ✓ done
- Commit: f80fd64 "40: docs(idml-tune): mark banned phrases ADVISORY; inventory gate is HARD"
- Verify: pass — `Per-iteration inventory gate`, `HARD precondition`, `exit code != 0`, `inventory_compare.py`, and `ADVISORY` all present in idml-tune/SKILL.md. CONTEXT.md §Gate behavior Stage 2 rules included verbatim.

## Task 13: Semantics catalog — docs/scribus-sla-attribute-semantics.md
- Status: ✓ done
- Commit: fc393a5 "40: docs(sla): add scribus-sla-attribute-semantics.md catalog"
- Verify: pass — all 8 H2 sections present (SCALETYPE, FLOP, LINESPMode, HCMS, PRFILE, LOCALSCX, EMBEDDED, Frame rotation). 268 lines (target 250-400). Each section names the emit site and includes an empirically-tested anti-example.

## Task 14: Deprecate old idml-import skill — redirect stub
- Status: ✓ done
- Commits: 357da07 "40: docs(idml-import): reduce SKILL.md to a 42-line redirect stub" + 75a1886 "40: test(skills): update skill structure tests for the import->scaffold/tune split"
- Verify: pass — idml-import/SKILL.md is 42 lines (<60), references both new skills; sub-docs kept on disk. `tools/sop_lint.py --help` exits 0 (the linter doesn't actually take flags — it just runs).
- Notes: **[Rule 1 - Plan correction]** Stub at 42 lines satisfies <60. `tests/unit/test_skill_idml_import_structure.py` had to be updated (per Principle 5: fix what you break) to validate the new layout — was 7 tests against the OLD SKILL.md structure (P1-P10 block, banned phrases in idml-import itself), now 22 parametrised tests across all three skill dirs.

## Verification results

### Final verification block (per PLAN.md)
- `python3 tools/inventory_extract.py --slug 26-03-leporello-...` → exit 0 ✓
- `python3 tools/inventory_compare.py --expected <baseline> --actual <fresh>` → exit 0 ✓
- `pytest tests/unit/test_inventory_gate_mutations.py` → 3 passed ✓
- `python3 -m unittest discover tests/unit -p 'test_inventory_gate_mutations.py'` → 3 OK ✓
- `python3 tools/idml_import_driver.py --help` → exits 0, shows --scaffold-only + --no-inventory ✓
- `bin/idml-import --help` → exits 0 ✓
- `python3 tools/sop_lint.py --help` → exits 0 ✓

### Repo-wide pytest tests/unit/
- 530 passed, 2 skipped, 12 subtests passed, **1 failed (pre-existing)**.
- Pre-existing failure: `tests/unit/test_idml_strict_mode.py::test_missing_asset_map_raises` — the test expects stderr to mention `--asset-map` but converter's earlier `--assets-dir does not exist` error fires first when run from the worktree (no `originals/` subdir relative to worktree CWD). The same test passes from `/workspace` checkout where `originals/` exists. This is an environment artifact, not a regression I introduced (confirmed via `git stash` on clean tree before any of my work).

## Deviations from plan

### [Rule 1 - Plan correction] Word count is 444 not 450 (Task 4)
- Plan's verify asserted `preview_pdf_count == 450` (raw `pdftotext | wc -w` count)
- The walker uses the existing `tools.text_render_audit.extract_pdf_words` which applies NFC + ligature folding + word-character-only regex, yielding 444 tokens
- Fix: kept the normalised count (matches what every other audit tool uses for consistency). Documented in commit message and the SCAFFOLD_INVENTORY.yml header.

### [Rule 1 - Plan correction] text_runs count is 57 not 90+ (Task 5)
- Plan asserted `len(text_runs) >= 90` based on a 104-`Run(`-call count
- 47 of those 104 are paragraph-separator Run() entries with empty text (separator='para', has_itext=False)
- Including empty-text runs would inflate the set without adding gate signal
- Fix: kept the non-empty-text filter (57 rows). Adjusted verify to `>=50`.

### [Rule 1 - Plan correction] tests/ layout is tests/unit/ (Task 10)
- Plan's verify referenced `tests/test_inventory_gate_mutations.py`
- Repo convention is `tests/unit/test_*.py` (every other unit test lives there)
- Placed under `tests/unit/`; verify runs match.

### [Principle 5 - Fix what you break] Updated skill structure tests (Task 14)
- Task 14 stubbing idml-import/SKILL.md broke 2 pre-existing assertions in `tests/unit/test_skill_idml_import_structure.py` (P1-P10 markers, "Banned phrases" section)
- Per Principle 5, these tests reflected the OLD layout that Task 14 deliberately changed
- Replaced them with 22 parametrised tests validating the NEW layout across all three skill dirs
- Net result: more coverage, all green.

## Discovered issues (not in scope)

1. **`test_idml_strict_mode.py::test_missing_asset_map_raises` fails in worktree env.** The converter's default `--assets-dir` is a relative path that doesn't exist in the worktree (sparse-checkout `originals/`). Test passes from `/workspace`. Either (a) the default should be removed / made absolute, or (b) the test should set `--assets-dir` explicitly. Out of scope for #40.

2. **`bin/idml-import` non-scaffold loop path was not exercised by the integration suite.** `tests/integration/test_idml_to_dsl_smoke.py` returned 4 skipped (env-gated). The driver `--scaffold-only` smoke is covered by unit tests; the full convergence loop is not. Out of scope for #40.

3. **`text_runs.every_idml_run_present_in_build_py` is a count heuristic, not a set check.** Inventory schema doesn't retain per-CSR text content on the IDML side, so this flag is computed as `sum(bp_counts) >= total_idml`. A proper set check would need a top-level `idml_runs:` list. Documented in code comments; v2 enhancement.

## Self-check

- [x] All files from plan exist (see commit messages for each task)
- [x] All commits exist on branch — 15 task commits + 4 issue-doc commits = 19 total on this branch
- [x] Full verification suite passes (1 pre-existing failure documented above)
- [x] No stubs/TODOs/placeholders in shipped code (verified with grep)
- [x] No leftover debug code (no `print(...)` or `breakpoint()` outside the existing audit pipeline)
- **Result:** PASSED

## Final commit list

```
75a1886 40: test(skills): update skill structure tests for the import->scaffold/tune split
357da07 40: docs(idml-import): reduce SKILL.md to a 42-line redirect stub
fc393a5 40: docs(sla): add scribus-sla-attribute-semantics.md catalog
f80fd64 40: docs(idml-tune): mark banned phrases ADVISORY; inventory gate is HARD
29fd56f 40: docs(skills): split idml-import into idml-scaffold + idml-tune
3b542d3 40: test(inventory): mutation tests confirm gate catches regressions
1f8e90c 40: chore(calibration): commit SCAFFOLD_INVENTORY.yml for 26-03 leporello
ffcea42 40: feat(driver): emit SCAFFOLD_INVENTORY.yml in --scaffold-only path
8e0c552 40: feat(inventory): add inventory_compare.py with 0/2/3 exit codes
953fdae 40: feat(inventory): add inventory_extract.py orchestrator
3586f98 40: feat(inventory): add AST-based build.py walker
3ac4302 40: feat(inventory): add PDF walker — words + grouped raster placements
7e85ca0 40: feat(inventory): add SLA walker — thin wrapper over SLADocument
ce5f1de 40: refactor(inventory): rename idml_inventory.py to walkers/ + add walk_idml
89145d8 40: feat(inventory): add SCAFFOLD_INVENTORY.yml dataclass schema
```

15 code/doc commits on top of the 4 issue artifact commits (ISSUE.md, CONTEXT.md, RESEARCH.md, PLAN.md).

## Acceptance criteria status

| Criterion | Status |
|---|---|
| All `SCAFFOLD_INVENTORY.yml` schema fields populate for 26-03 leporello | ✓ — `parse_warnings=[]`, every documented field has content |
| `inventory_compare.py` exits 0 when comparing leporello against itself | ✓ — verified in Task 9 final run |
| Mutation: drop a word → exit 2 | ✓ — M1 test passes under both pytest and unittest |
| Mutation: rename anname → exit 2 | ✓ — M2 test passes |
| Mutation: drop color → exit 2 | ✓ — M3 test passes |
| `.claude/skills/idml-scaffold/SKILL.md` + `idml-tune/SKILL.md` exist | ✓ — both files, both reference inventory CLIs |
| `docs/scribus-sla-attribute-semantics.md` exists with 8 named sections | ✓ — 268 lines, all 8 sections |
| `python3 tools/inventory_extract.py --slug 26-03-leporello-...` runs and emits valid YAML | ✓ — exit 0, valid YAML |
| All existing tests still pass | ✓ — 530 pass, 1 pre-existing failure documented |

**Duration:** 2026-05-13T20:25:51Z → 2026-05-13T~21:10Z, ~45 minutes
**Commits:** 15 on the branch (this issue's work)

## Follow-up issues I would open

1. **`tools/check_stage2_forbidden_paths.py` pre-commit hook** — referenced from `forbidden_paths.md` as a nice-to-have. A pre-commit check that fails if any changed file matches the Stage-2 forbidden globs would mechanically enforce what the skill currently asks the agent to self-police.

2. **Per-paragraph-style PDF word counts via pdfplumber** — currently `pdf_word_count` is 0 in every `by_paragraph_style` bucket because v1 schema doesn't do the bbox-in-frame join. RESEARCH.md flagged this as a v2 extension; the schema field is reserved.

3. **Inventory baseline for the other 11 templates in the worktree** — only leporello has a calibrated `SCAFFOLD_INVENTORY.yml`. The other templates (infostand-tent-card, kandidat-falzflyer, plakat, etc.) need baseline snapshots before the gate becomes useful for them. Out of scope for #40 per CONTEXT.md "Non-goals".

4. **Fix `--assets-dir` default in `tools/idml_to_dsl.py`** — current relative-path default makes `test_idml_strict_mode.py::test_missing_asset_map_raises` fail in the worktree env. Default should be `None` with a clearer required-flag error.

5. **Replace the "every_idml_run_present_in_build_py" heuristic with a real set check.** Add an `idml_runs:` field to the IDML-side schema and do strict set equality. Today's flag is a count comparison and can hide ordering / mismatched-style bugs.
