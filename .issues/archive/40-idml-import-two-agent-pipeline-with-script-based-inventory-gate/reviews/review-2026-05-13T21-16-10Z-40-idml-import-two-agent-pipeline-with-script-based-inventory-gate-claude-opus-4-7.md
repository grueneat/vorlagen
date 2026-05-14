---
review_of: 40-idml-import-two-agent-pipeline-with-script-based-inventory-gate
review_type: issue
review_mode: implementation
reviewed_at: 2026-05-13T21-16-10Z
tool: claude
model: claude-opus-4-7
duration_seconds: 572
---

<review>

<acceptance_criteria>

<criterion status="met" id="1">
  <text>All SCAFFOLD_INVENTORY.yml schema fields populate for the 26-03 leporello anchor.</text>
  <evidence>templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml — 1937 lines, every top-level section present: text_runs (with 10 by_paragraph_style buckets, 56 build_py_runs), frames (23 text + 10 image + 52 polygon + 12 group), 7 paragraph_styles, 15 colors, 20 assets, words (444/444), parse_warnings=[]. See also tools/walkers/schema.py:144-154 (Inventory dataclass) — every field used.</evidence>
</criterion>

<criterion status="partially_met" id="2">
  <text>Every field populates with meaningful data.</text>
  <reason>Several documented fields are present but zero/null in the calibrated baseline because the join logic is incomplete:
- text_runs.by_paragraph_style[].pdf_word_count: 0 in every bucket (deferred per EXECUTION.md #2 follow-up).
- text_runs.by_paragraph_style[].sla_itext_count: 0 in every bucket — caused by walk_sla.py:71 reading the wrong attribute (see finding H1).
- text_runs.by_paragraph_style: IDML rows and build_py rows live in distinct entries because the naming conventions never reconcile; idml_count is non-zero for ParagraphStyle/* keys, build_py_count is non-zero for idml/* keys, the two never overlap (see SCAFFOLD_INVENTORY.yml:23-76 for the split).
- paragraph_styles[].build_py is null on 5 of 7 rows for German-umlaut styles (see finding H2).
- assets[].sha256 / byte_length are null for every row (see finding M1).
- assets[].referenced_from_frames is [] for every embedded asset (see finding M2).</reason>
</criterion>

<criterion status="met" id="3">
  <text>tools/inventory_compare.py exits 0 when comparing leporello against itself.</text>
  <evidence>tools/inventory_compare.py:191-192 — `exit_code = 0` when neither `missing` nor `extra` nor any negative `count_delta` is set. The committed baseline self-compare is the smoke test referenced in EXECUTION.md Task 9.</evidence>
</criterion>

<criterion status="met" id="4">
  <text>tools/inventory_compare.py exits 2 on a missing element regression.</text>
  <evidence>tools/inventory_compare.py:187-188 — `if missing or has_negative: exit_code = 2`. Missing detection covers frames (lines 93-105 via set-diff per kind), colors (lines 117-134, including the `colors.build_py` set keyed on build_py_extra_color), assets (lines 137-144), paragraph_styles set (lines 108-115), and a text-runs build_py_runs word-set diff (lines 177-182). M1/M2/M3 mutation tests in tests/unit/test_inventory_gate_mutations.py exercise three of these paths.</evidence>
</criterion>

<criterion status="met" id="5">
  <text>tools/inventory_compare.py exits 3 when an extra element appears.</text>
  <evidence>tools/inventory_compare.py:189-190 — `elif extra: exit_code = 3`. Rows tagged `source: manual` on the actual side are excluded via `_frame_key_set(..., include_manual=False)` at line 99, so 34 manual PolyLine fold-lines don't trigger spurious extras (RESEARCH.md pitfall #3 satisfied).</evidence>
</criterion>

<criterion status="met" id="6">
  <text>Three mutation tests verify the gate catches regressions.</text>
  <evidence>tests/unit/test_inventory_gate_mutations.py — M1 (drop a Run text → text_runs.missing, rc=2) at lines 120-151, M2 (rename anname='u514' → frames.image_frames missing, rc=2) at lines 155-172, M3 (drop add_color → colors.build_py missing, rc=2) at lines 176-225. Each calls inventory_extract.py + inventory_compare.py via subprocess against the committed baseline. The tests use `unittest.TestCase` with setUp/tearDown so both pytest and `python -m unittest discover` execute them.</evidence>
</criterion>

<criterion status="met" id="7">
  <text>idml-scaffold and idml-tune skills exist and reference the inventory CLIs.</text>
  <evidence>.claude/skills/idml-scaffold/SKILL.md (190 lines) — Tooling section at lines 36-46 cites inventory_extract.py + inventory_compare.py; Inventory gate at lines 87-104. .claude/skills/idml-tune/SKILL.md (171 lines) — Tooling section at lines 29-40 cites both CLIs; "Per-iteration inventory gate (HARD precondition)" at lines 59-84 with verbatim CONTEXT.md Stage 2 rules. Forbidden paths at lines 42-57 explicitly list tools/idml_to_dsl.py, tools/sla_lib/**, tools/inventory_*.py, tools/walkers/**.</evidence>
</criterion>

<criterion status="met" id="8">
  <text>docs/scribus-sla-attribute-semantics.md exists with the 8 named H2 sections.</text>
  <evidence>docs/scribus-sla-attribute-semantics.md (269 lines) — section headers at lines 17 (SCALETYPE), 46 (FLOP), 69 (LINESPMode), 101 (HCMS), 130 (PRFILE), 152 (LOCALSCX), 189 (EMBEDDED), 218 (Frame rotation). Each section has Where/Values observed/Emit site/Anti-example. Emit-site references include file:line pointers (e.g. `tools/sla_lib/builder/primitives.py:827` for SCALETYPE, `:830` for PRFILE).</evidence>
</criterion>

<criterion status="met" id="9">
  <text>idml-import/SKILL.md is reduced to a redirect stub (<60 lines).</text>
  <evidence>.claude/skills/idml-import/SKILL.md is 42 lines; line 12 declares "DEPRECATED → use /idml-scaffold or /idml-tune"; lines 16-19 list the two new skills; lines 24-27 document sub-doc redistribution. Old sub-docs (asset_policy/classification/inject_protocol/pattern_library/tolerance_protocol) remain on disk per the back-compat decision.</evidence>
</criterion>

<criterion status="met" id="10">
  <text>idml-tune/forbidden_paths.md lists the converter and shared converter code.</text>
  <evidence>.claude/skills/idml-tune/forbidden_paths.md:11-22 — explicit table with tools/idml_to_dsl.py, tools/idml_to_dsl_patterns/**, tools/sla_lib/**, tools/inventory_extract.py, tools/inventory_compare.py, tools/walkers/**, tools/reconcile_build_py.py, tools/sop_lint.py, templates/<other-slug>/**, shared/**, bin/**. Lines 36-46 honestly note that pre-commit hook enforcement (tools/check_stage2_forbidden_paths.py) is OUT OF SCOPE for this PR.</evidence>
</criterion>

<criterion status="met" id="11">
  <text>python3 tools/inventory_extract.py --help runs.</text>
  <evidence>tools/inventory_extract.py:460-487 — argparse setup defines --slug, --templates-dir, --originals-dir, --repo-root, --output. No conditional --help suppression. Parser is the standard argparse.ArgumentParser.</evidence>
</criterion>

<criterion status="met" id="12">
  <text>tools/idml_inventory.py back-compat shim does not break existing callers.</text>
  <evidence>tools/idml_inventory.py:7-12 — dynamic re-export loop over `dir(_impl)` brings every public/single-underscore name into module scope. Callers verified via grep: `tools/render_pipeline.py:784` does `from idml_inventory import run_inventory, _yaml_dump as _inv_yaml`; `tests/unit/test_idml_inventory.py:21` imports 7 names. All are present at tools/walkers/walk_idml_inventory.py:53 (_load_printable_layers), :70 (_load_spread_order), :192 (_build_hint), :232 (_collect_spread_items), :289 (_extract_annames_from_build_py), :316 (run_inventory), :818 (_yaml_dump). Note: the wildcard loop also re-exports `argparse`, `re`, `sys`, `zipfile`, `ET`, `Path`, `yaml` — see finding L1.</evidence>
</criterion>

</acceptance_criteria>

<findings>

<finding severity="high" id="H1">
  <title>walk_sla.py reads the wrong attribute for paragraph-style detection — sla_itext_count is silently 0 everywhere</title>
  <location>tools/walkers/walk_sla.py:69-78</location>
  <description>
The walker does `pstyle = it.attrib.get("PSTYLE")` on ITEXT/PARA elements, falling back to the parent's `PSTYLE`. But Scribus references paragraph styles via `PARENT=` on PARA / `<trail>` elements (see tools/sla_lib/tests/test_sla_diff.py:416 etc. and the live anchor SLA). Confirmed empirically: the anchor template.sla has 0 occurrences of `PSTYLE=` and 92 of `PARENT=`. As a result `itext_by_pstyle` returns an empty dict, and every `by_paragraph_style[].sla_itext_count` in the committed baseline is 0 (SCAFFOLD_INVENTORY.yml:29, :34, :39, :44, …, :74 — all 10 buckets).

This is a silent walker failure: the field exists, the gate reports a number, but the number is always 0. A regression that drops an ITEXT element from the SLA would not be detected via this signal. The gate still catches frame-level drops via PAGEOBJECT/anname diffs, so the failure is bounded — but the documented "set-equality on (text, font, fontsize)" contract isn't being exercised for the SLA side.
  </description>
  <fix>Change tools/walkers/walk_sla.py:71 to read `PARENT` instead of `PSTYLE`, and update the fallback at :76 similarly. Add a unit test that asserts `walk_sla(<anchor>).itext_by_pstyle` is non-empty (covers 7 IDML paragraph styles). After fixing, regenerate templates/26-03-…/SCAFFOLD_INVENTORY.yml so the committed baseline reflects real sla_itext_count values.</fix>
</finding>

<finding severity="high" id="H2">
  <title>paragraph_style join silently fails for German umlauts (ß/ä/ö/ü) and $ID-prefixed styles</title>
  <location>tools/inventory_extract.py:288-312</location>
  <description>
`_join_paragraph_styles` slugifies the IDML style name with `c if c.isalnum() else "-"`, then does case-insensitive substring matching against build.py / SLA style names. Two problems:

1. `str.isalnum()` returns True for Unicode letters including `ü`, `ö`, `ä`, `ß` — so umlauts are PRESERVED in the slug. But build.py uses ASCII transliteration: `aufzählungen-auf-grünem-hintergrund` ≠ `aufzaehlungen-auf-gruenem-hintergrund` substring-wise. Match fails.

2. `ParagraphStyle/$ID/NormalParagraphStyle` produces slug `$id/normalparagraphstyle` → slug_norm `id-normalparagraphstyle` which is NOT a substring of build.py's `idml/normalparagraphstyle` (the `-` vs `/` differs).

Confirmed in the committed baseline at SCAFFOLD_INVENTORY.yml:1642-1660 — 5 of 7 paragraph_style entries show `build_py: null` AND `sla_pstyle_present: false`, despite the SLA having `<STYLE NAME="idml/aufzaehlungen-auf-gruenem-hintergrund"/>` and the build.py emitting the corresponding `add_para_style`.

The downstream gate consequence is muted because inventory_compare.py only checks `_pstyle_set` (the IDML-side key set, which never changes between baseline and actual). But the `build_py:` linkage is dead data — visible in the YAML, never used, and misleadingly suggests "the gate verifies build.py emit-side coverage of IDML para styles". It does not.
  </description>
  <fix>Two-part. (1) In tools/inventory_extract.py:297-300, replace the naive slugifier with the same transliteration the converter uses (likely `tools/idml_to_dsl.py::_slugify` — search for `aufzaehlungen` in the converter to find it). (2) Handle the `$ID/Name` prefix explicitly: strip `$ID/` before slugifying. After fixing, the committed baseline at SCAFFOLD_INVENTORY.yml needs regeneration so all 7 rows show non-null build_py and sla_pstyle_present where applicable.</fix>
</finding>

<finding severity="high" id="H3">
  <title>Gate has no check for "dropped add_para_style" — no mutation test covers it either</title>
  <location>tools/inventory_compare.py:107-115</location>
  <description>
The comparator's paragraph_styles handling uses `_pstyle_set` on `r.get("idml")` only — the IDML-side names. Since the IDML doesn't change between baseline extract and fresh extract, this set is always equal and never flags a regression.

Unlike colors (which has the explicit `build_py_extra_color` flag and a parallel `colors.build_py` set diff at lines 126-134), paragraph_styles has no `build_py_*` boolean. The `ParagraphStyleEntry.build_py` field at tools/walkers/schema.py:113 is type `Optional[str]` — it carries the matched build.py name, but the comparator never reads it. So an agent that drops `doc.add_para_style(ParaStyle(name='idml/headline-in-gruenem-kasten'))` from build.py would still pass the gate.

No mutation test covers this. tests/unit/test_inventory_gate_mutations.py has M1 (Run text), M2 (anname), M3 (add_color); M4 (add_para_style) is conspicuously absent. Combined with H2's broken join, even if the agent restores the call but uses a slightly different name, the gate has no way to notice.

This is the highest-impact gap for Stage 2 behavior: removing a paragraph style breaks all text using that style at render time, but the gate stays green.
  </description>
  <fix>
1. Add `build_py_extra_pstyle: bool` to ParagraphStyleEntry (schema.py:110-115), set True when join finds a matching name in build.py's add_para_style_names.
2. In inventory_compare.py, mirror the colors.build_py block at line 126-134 for paragraph styles: `paragraph_styles.build_py` missing set.
3. Add tests/unit/test_inventory_gate_mutations.py::test_m4_drop_add_para_style_is_detected analogous to M3.
4. Regenerate the calibrated baseline so the new boolean populates correctly.
  </fix>
</finding>

<finding severity="medium" id="M1">
  <title>AssetEntry.sha256 and byte_length are schema-declared but never populated</title>
  <location>tools/walkers/schema.py:131-133; SCAFFOLD_INVENTORY.yml:1788-1931</location>
  <description>
`AssetEntry` declares `sha256: Optional[str] = None` and `byte_length: Optional[int] = None` (schema.py:132-133). The build.py walker computes a sha256 for inline_image_data payloads (walk_build_py.py:124-126) but stores it on the FRAME row as `inline_image_data_sha256` / `inline_image_data_bytes` (walk_build_py.py:270-273). It never associates the hash with the AssetEntry. The IDML walker's `_walk_idml_assets` at walk_idml_inventory.py:644-737 never reads file bytes — `on_disk` is bool-only.

Result: every AssetEntry in the calibrated baseline has `sha256: null` and `byte_length: null` (verified at SCAFFOLD_INVENTORY.yml:1788, :1795, :1802 etc.). Either populate the fields (hash the on_disk bytes, set byte_length from `Path(...).stat().st_size`), or remove them from the schema. The "embedded vs external" gate cannot meaningfully use them either way until populated.
  </description>
  <fix>In tools/walkers/walk_idml_inventory.py::_walk_idml_assets, when `on_disk` is True, compute sha256+byte_length from the file at `assets_dir / basename` (or the absolute composite path) and pass into the AssetEntry. Alternatively, drop the fields from schema.py if the intent is "implement in v2".</fix>
</finding>

<finding severity="medium" id="M2">
  <title>Embedded assets (inline_image_data) have empty referenced_from_frames in the calibrated baseline</title>
  <location>tools/inventory_extract.py:362-374; SCAFFOLD_INVENTORY.yml:1782-1860</location>
  <description>
`_join_assets` builds the basename→[anname,…] map only from build.py frames whose `image=` kwarg is set:
```
for img in build_data["frames"]["image_frames"]:
    ref = img.get("image") or ""
    anname = img.get("anname") or ""
    if not ref or not anname:
        continue
```
But embedded brand assets (bluesky-weiss.png, mail-weiss.png, gruene-logo-bund-weiss-cmyk.png, website-weiss.png, social-media-icons-weiss.png — all classified `embedded`) enter the document via `inline_image_data=`, not `image=`. The walker captures `inline_image_data_sha256` and `inline_image_data_bytes` on the frame row (walk_build_py.py:270-275) but the orchestrator's join never uses them. Composite-AI is handled by a separate code path (inventory_extract.py:334-356) which reads `composite_ai_split.yml` directly.

Result: every embedded asset in SCAFFOLD_INVENTORY.yml has `referenced_from_frames: []`. The Stage 2 gate cannot detect "agent stopped emitting the embedded gruene-logo" because no frame is associated with that asset name. RESEARCH.md flagged composite-AI specifically; the same problem applies to ALL inline_image_data assets.
  </description>
  <fix>In walk_build_py.py, when `inline_image_data` is set on a frame, also capture the asset basename if discoverable (e.g. from a sibling `style.fill_image` field, the frame's `style` value if it encodes the asset slug, or by hashing-and-looking-up against shared/assets/<slug>/<file>). Then in inventory_extract.py::_join_assets, walk inline-image frames and resolve basename↔anname the same way the `image=` path does.</fix>
</finding>

<finding severity="medium" id="M3">
  <title>every_idml_run_present_in_build_py is a sum heuristic, not a set check — name is misleading</title>
  <location>tools/inventory_extract.py:126-137; tools/walkers/schema.py:52</location>
  <description>
The flag is computed as:
```
every_idml_present = (
    idml_inv.text_runs.total_idml > 0
    and sum(bp_counts.values()) >= idml_inv.text_runs.total_idml
)
```
This is `total_build_runs_across_all_styles >= total_idml_runs_across_all_styles`. A build.py that drops 30% of its IDML-equivalent runs and adds 30% net-new runs would still pass this check. The field name promises set equality.

EXECUTION.md "Discovered issues #3" acknowledges this. Either:
(a) Rename the field to `text_run_count_meets_idml_total` (honest), or
(b) Implement the actual set check by extending the IDML walker to retain per-CSR text content in the inventory (walk_idml_inventory.py:482-552 already builds the data; just propagate `runs` into the schema as an `idml_runs:` field).

The gate's mutation test M1 catches "dropped Run text" via the `text_runs.build_py_runs` set diff in inventory_compare.py:177-182, which works correctly. But this flag is the documented contract per ISSUE.md §Inventory schema, and it currently lies.
  </description>
  <fix>Add `idml_runs: list[TextRun]` to TextRunBucket; have walk_idml drop the runs list into the bucket (the data already exists at walk_idml_inventory.py:545-551 — currently discarded into `_runs`). Then compute the flag as `set(idml_texts).issubset(set(build_py_texts))`.</fix>
</finding>

<finding severity="medium" id="M4">
  <title>inventory_extract.py default --output silently overwrites the committed baseline</title>
  <location>tools/inventory_extract.py:480-512; tools/idml_import_driver.py:525-538</location>
  <description>
When `inventory_extract.py` runs without `--output`, it writes to `<templates-dir>/<slug>/SCAFFOLD_INVENTORY.yml` — the same path used by `inventory_compare.py --expected`. So a user who runs `python3 tools/inventory_extract.py --slug X` (no flags) to "check the current state" silently overwrites the committed baseline. A subsequent `inventory_compare.py --expected templates/X/SCAFFOLD_INVENTORY.yml --actual <fresh>` then trivially exits 0.

The driver hook at tools/idml_import_driver.py:530-532 has the same problem: on every `--scaffold-only` invocation it overwrites the baseline at `ROOT / "templates" / slug / "SCAFFOLD_INVENTORY.yml"`. PLAN.md Task 8 wraps this in try/except to make it non-fatal, but the destruction is silent and immediate.

The .claude/skills/idml-tune/SKILL.md:62-70 correctly tells the user to use `--output /tmp/inv-current.yml`, but the default footgun is still loaded.
  </description>
  <fix>
1. Change inventory_extract.py default behavior: if `--output` is omitted AND `<templates-dir>/<slug>/SCAFFOLD_INVENTORY.yml` already exists, refuse and print "use --output to overwrite explicitly, or --force". OR: change default --output to stdout (require explicit `--output` to write any file).
2. In the driver, only emit SCAFFOLD_INVENTORY.yml when the file does NOT already exist; if it does, write `templates/<slug>/SCAFFOLD_INVENTORY.fresh.yml` instead so the calibrated baseline survives.
  </fix>
</finding>

<finding severity="medium" id="M5">
  <title>walk_build_py.py does not call tools/reconcile_build_py.py — claim in PLAN.md/EXECUTION.md is partially false</title>
  <location>tools/walkers/walk_build_py.py:129-309</location>
  <description>
PLAN.md Task 5 specified: "First, if inject.yml exists, call `tools/reconcile_build_py.py <slug>` programmatically (or document the dependency and require it run before extraction — pick programmatic to avoid drift)". EXECUTION.md Task 5 reports the implementation matched the plan.

In practice, walk_build_py.py only reads inject.yml's text strings as a flat set (lines 129-155) and tags matching Run() entries with `text_source='inject_yml'`. It does not call reconcile_build_py.py, does not invoke any subprocess, does not parse inject.yml's `frames:` / `runs:` structure. If a tuned template has inject.yml entries that override a run's text or add new content NOT yet reconciled into build.py, the walker will undercount.

The Stage 2 SKILL.md at .claude/skills/idml-tune/SKILL.md:62-65 correctly tells the user to run reconcile_build_py.py before extracting. So this is mostly a "the impl is honest, the EXECUTION.md log overstates compliance" issue — the anchor template has no inject.yml so the gap didn't surface during calibration.
  </description>
  <fix>Either (a) match PLAN.md by adding a `subprocess.run(['python3', 'tools/reconcile_build_py.py', slug])` call at the top of walk_build_py (gated by inject.yml existence), with appropriate error handling; or (b) update PLAN.md/EXECUTION.md to record the actual decision (caller must reconcile first). (b) is cheaper and matches what the skill docs already say.</fix>
</finding>

<finding severity="medium" id="M6">
  <title>_resolve_idml_path fallback glob uses first slug word — likely to mis-resolve for new templates</title>
  <location>tools/inventory_extract.py:59-89</location>
  <description>
After meta.yml lookup fails, the fallback at lines 78-85 globs `<originals_dir>/*/*.idml`, then for each candidate checks if `slug.lower().replace("-"," ").split()[0]` is a substring of the candidate's basename. For the anchor leporello slug "26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover", the first split chunk is `"26"` — broad enough that any IDML with "26" in its filename would match (e.g. a template numbered `26-04-...`).

Worse, if no candidate matches, it returns the first one: `return candidates[0]` (line 85). This silently picks the wrong IDML rather than raising. The error path at line 86 (`raise FileNotFoundError`) only fires when the originals directory is empty.

The mutation tests rely on this fallback (the tmp copy's meta.yml `idml_source` resolves to a non-existent tmp/originals path), so changing this behavior may require also updating the tests. But for non-test invocation on a fresh template, this silent mis-resolution would produce a completely wrong inventory with no warning.
  </description>
  <fix>At inventory_extract.py:82-85, require an exact basename-prefix match on the slug stem (not just first word); raise FileNotFoundError if no match. If meta.yml is missing, error explicitly rather than guessing.</fix>
</finding>

<finding severity="low" id="L1">
  <title>idml_inventory.py shim re-exports stdlib module names from walk_idml_inventory's imports</title>
  <location>tools/idml_inventory.py:7-13</location>
  <description>
The shim does `from tools.walkers import walk_idml_inventory as _impl; for _name in dir(_impl): if not _name.startswith("__"): globals()[_name] = getattr(_impl, _name)`. Because `dir(_impl)` includes module-level imports (argparse, re, sys, zipfile, yaml, ET, Path, Optional, frozenset constants like PAGE_ITEM_TAGS, etc.), the shim ends up exporting all of those too.

Concretely: `from idml_inventory import argparse` would silently succeed. This isn't a security issue but it pollutes the namespace and makes the shim's "contract" loose — anything walk_idml_inventory.py imports becomes part of the public surface.
  </description>
  <fix>Replace the dynamic loop with an explicit `__all__` list of the public+private names tools/render_pipeline.py and tests/unit/test_idml_inventory.py actually depend on (run_inventory, _yaml_dump, _extract_annames_from_build_py, _load_printable_layers, _load_spread_order, _collect_spread_items, _build_hint, main). Use plain `from tools.walkers.walk_idml_inventory import <name>` lines.</fix>
</finding>

<finding severity="low" id="L2">
  <title>inventory_compare.py reports drift_count even when nothing matters — count_deltas with delta>0 is ignored by exit logic</title>
  <location>tools/inventory_compare.py:184-203</location>
  <description>
The exit logic at lines 187-192 ignores any positive (non-regression) count_delta entry. The diff dict still records every delta, including pure additions, but the summary shows `exit_code: 0` with `delta_count: N>0`. A CI consumer that reads `summary.delta_count` thinking "any delta means drift" would be confused, since the exit code says "match". Document that `delta_count` is informational only, or split into `negative_delta_count` and `positive_delta_count`.
  </description>
  <fix>Add a `delta_summary` block with `negative: N, positive: M, zero: K` so consumers don't conflate the two cases. Or just split the summary key naming to be explicit.</fix>
</finding>

<finding severity="low" id="L3">
  <title>walk_idml_inventory's PAGE_ITEM_TAGS misses Image and PDF as top-level page items</title>
  <location>tools/walkers/walk_idml_inventory.py:41-44</location>
  <description>
PAGE_ITEM_TAGS = `{Rectangle, Polygon, Oval, TextFrame, Image, PDF, Group, GraphicLine}`. Then CHILD_CONTENT_TAGS = `{Image, PDF}` is used to skip Image/PDF when they appear inside a Rectangle/Polygon/Oval parent (line 595). But the comment at line 47 says "Tags that are NOT themselves top-level items but children of them" — so what happens when Image/PDF appear as TOP-LEVEL (no Rectangle wrapper)? They get walked, but the bucketing logic at walk_idml_inventory.py:608-640 only routes TextFrame → text_frames, Rectangle/Polygon/Oval/GraphicLine → image_frames or polygon_frames, Group → group_frames. Top-level Image/PDF elements fall through without being added to any bucket.

In practice IDML normally wraps Image inside Rectangle, so this is theoretical. But worth a defensive `else: out["image_frames"].append(...)` to catch the case.
  </description>
  <fix>Add an explicit `elif tag in ("Image", "PDF"): out["image_frames"].append(row)` branch to walk_idml_inventory.py:640 — or document why top-level Image/PDF cannot occur in this codebase.</fix>
</finding>

<finding severity="low" id="L4">
  <title>Mutation test environment coupling — tests skip silently if the anchor isn't mounted at /workspace</title>
  <location>tests/unit/test_inventory_gate_mutations.py:48-52</location>
  <description>
The test class is `@unittest.skipUnless(LEPORELLO_DIR.exists() and BASELINE.exists() and ORIGINALS_DIR.exists(), …)`. If `/workspace/originals/` is absent (e.g. in CI with a sparse checkout), all three mutation tests skip silently. A CI run that reports "0 failed, 0 passed" would look identical to "tests skipped because env not set up". The skip reason names `LEPORELLO_DIR` only, not `ORIGINALS_DIR`, so a debug user might think only the templates dir is missing.

Mitigation: extract one mutation into a self-contained test using a synthetic in-tree IDML fixture (e.g. the same tiny zip used by tests/unit/test_idml_inventory.py) so at least one mutation runs everywhere; keep the leporello-bound tests for full-fidelity validation.
  </description>
  <fix>Add a small synthetic test that exercises the M3 (drop add_color) path against a 50-line build.py + an empty SLA + a fake preview.pdf in tmp_path, with no anchor dependency. Update the skip reason to list ALL missing paths.</fix>
</finding>

<finding severity="low" id="L5">
  <title>Incidental template files in the PR diff come from issue #39 follow-up (#86), not issue #40</title>
  <location>templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/{build.py, meta.yml, template.sla}; site/public/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla</location>
  <description>
`git log main..HEAD -- templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` shows the changes came from commit d8f8188 "39 follow-up: chore(v2-falzflyer): plakat-dunkel is brand, embed it too (#86)" — a pre-issue-40 follow-up that hasn't been merged to main yet. `git merge-base main HEAD` returns 320893d (issue #39 follow-up #85), so d8f8188 is one commit ahead of main but not part of #40's work.

The review prompt flagged these files as potential out-of-scope churn. They are out-of-scope FOR THIS PR but they are issue-39 carryover, not a #40 regression. Not blocking, but the PR should either (a) merge d8f8188 separately first, then rebase #40 on the resulting main, or (b) explicitly acknowledge the carryover in the PR description.
  </description>
  <fix>Rebase issue/40 onto main after d8f8188 (or its PR equivalent) lands, so the diff stat only shows the inventory-gate work.</fix>
</finding>

</findings>

<strengths>
<strength>Pure set/count comparator with no LLM, no fuzzy matching, no tolerance bands — verified by reading inventory_compare.py end-to-end. Exit semantics (0/2/3) are clean and consistent with CONTEXT.md.</strength>
<strength>AST-only build.py walker (tools/walkers/walk_build_py.py:180 — `ast.parse`, no `eval`/`exec`/`importlib`) — no side effects from parsing untrusted-ish Python.</strength>
<strength>Subprocess invocations use list-args (tools/walkers/walk_pdf.py:99-102) — no shell injection surface.</strength>
<strength>inline_image_data is hashed and the byte payload is discarded (tools/walkers/walk_build_py.py:124-126, :270-275) — inventory stays small and the YAML doesn't carry base64 bloat.</strength>
<strength>34 manual PolyLine fold-lines correctly tagged source=manual (tools/walkers/walk_build_py.py:276-277) and excluded from the "extras" detection on the actual side (tools/inventory_compare.py:99) — RESEARCH.md pitfall #3 resolved.</strength>
<strength>Composite-AI assets correctly produce one AssetEntry per physical file with multiple referenced_from_frames (tools/inventory_extract.py:334-356, reading composite_ai_split.yml::pages_emitted[].idml_anname) — three rows in the calibrated baseline at SCAFFOLD_INVENTORY.yml:1877-1903 confirm.</strength>
<strength>Back-compat shim at tools/idml_inventory.py:7-13 cleanly preserves the existing public+private API; tests/unit/test_idml_inventory.py (existing 280+ lines) and tools/render_pipeline.py:784 continue to work unchanged.</strength>
<strength>Skill split is honest: idml-import/SKILL.md is a 42-line redirect stub with no leftover SOP content; sub-docs duplicated into the right destinations per the Decisions table; forbidden_paths.md openly acknowledges the pre-commit enforcement is a follow-up, not in this PR.</strength>
<strength>docs/scribus-sla-attribute-semantics.md has all 8 H2 sections with file:line emit-site references and empirically-tested anti-examples — captures session lore that would otherwise be re-derived.</strength>
<strength>Mutation tests exercise three distinct failure modes (drop word, rename anname, drop color) under both pytest and unittest discover (tests/unit/test_inventory_gate_mutations.py:48-225) — the gate's primary contract is verified.</strength>
<strength>Driver hook is appropriately defensive (tools/idml_import_driver.py:533-538) — inventory emission failure does NOT fail the scaffold; emits a non-fatal stderr warning instead. Gate enforcement is correctly Stage 2's job.</strength>
</strengths>

<traces>
<trace name="extract flow">
  tools/inventory_extract.py:459 (main argparse) → :489 build_inventory(slug, …) → :430 _resolve_idml_path → :434 walk_idml at tools/walkers/walk_idml_inventory.py:740 (returns IDML-side Inventory with text_runs, paragraph_styles, colors, frames, assets) → :440 walk_build_py at tools/walkers/walk_build_py.py:158 (returns dict with text_runs, frames, add_para_style_names, add_color_names, parse_warnings) → :441 walk_sla at tools/walkers/walk_sla.py:19 (returns dict with pageobject_count, by_anname, sla_styles, sla_colors, itext_by_pstyle) → :442-443 walk_pdf + walk_pdf_images at tools/walkers/walk_pdf.py:20, :82 → :448-453 _join_text_runs/frames/paragraph_styles/colors/assets → :455 Inventory dataclass → :500 to_yaml at tools/walkers/schema.py:170 → write to <templates-dir>/<slug>/SCAFFOLD_INVENTORY.yml at :510-511.
</trace>
<trace name="compare flow">
  tools/inventory_compare.py:226 (main argparse) → :244 _load both YAMLs at :31 → :246 compare(expected, actual) at :85 → frame_kinds loop at :93-105 (set diffs per kind, manual exclusion via :99 _frame_key_set include_manual=False) → :107-115 paragraph_styles set diff → :117-134 colors set + colors.build_py via build_py_extra_color flag → :137-144 assets basename set → :149 text_runs by_paragraph_style count deltas at :64 → :151-167 top-level numeric deltas → :170-182 words missing/extra + text_runs.missing word-set diff at :207 → :184-192 exit code resolution (2 if missing OR has_negative delta, 3 if extra only, 0 otherwise) → :247 yaml.safe_dump → :249-253 write to --out or stdout → :254 return summary.exit_code.
</trace>
<trace name="driver hook flow">
  bin/idml-import → tools/idml_import_driver.py:736 main → :689-695 parse_args with --scaffold-only flag → :719-732 parse_args with --no-inventory flag → :517 `if args.scaffold_only:` branch → :519 _run_render_gallery → :525-538 inventory emission (programmatically imports tools.inventory_extract.build_inventory + to_yaml) → :530 writes to ROOT/templates/<slug>/SCAFFOLD_INVENTORY.yml UNCONDITIONALLY (M4) → :539 _run_convergence_review → :541-546 log_iteration + verdict → return 0.
</trace>
<trace name="mutation M1 (drop Run text)">
  tests/unit/test_inventory_gate_mutations.py:120 test_m1_drop_run_text_is_detected → :125-139 regex transform sets first non-empty Run(text='...') text to empty → :141 _patch_build_py writes mutated build.py to tmpdir → :142 _extract_mutated subprocess-calls tools/inventory_extract.py with --templates-dir=tmp, --originals-dir=/workspace/originals → :143 _compare subprocess-calls tools/inventory_compare.py against BASELINE → :144 assert rc==2 → :146-151 assert dropped text appears in diff.missing.text_runs.missing.
</trace>
<trace name="mutation M2 (rename anname)">
  tests/unit/test_inventory_gate_mutations.py:155 test_m2_rename_image_anname_is_detected → :156-161 replace anname='u514' → anname='u514X' in build.py → :163-164 extract + compare → :166 assert rc==2 → :167-172 assert "u514" in diff.missing.frames.image_frames. Note: u514 is the ziesel.jpg image-frame's anname per the inventory baseline.
</trace>
<trace name="mutation M3 (drop add_color)">
  tests/unit/test_inventory_gate_mutations.py:176 test_m3_drop_add_color_is_detected → :183-209 walk text to find the first add_color call, manually paren-match the close, extract the color name → :210 splice the call out of the file → :212-214 extract + compare → :215 assert rc==2 → :217-223 assert dropped color name appears in diff.missing.colors.build_py. Comparator path: inventory_compare.py:128-134 reads build_py_extra_color flag on each color row; the dropped row flips from True to False, so the set difference reports the IDML name (e.g. "Color/Endformat").
</trace>
</traces>

<verdict value="warn" critical="0" high="3" medium="6">
  <blockers>
    <blocker>H1 — walk_sla.py:71 reads PSTYLE but Scribus uses PARENT for paragraph-style references; sla_itext_count is universally 0 in the committed baseline. Silent walker failure that erodes the gate's coverage of the SLA side.</blocker>
    <blocker>H2 — paragraph_style join in inventory_extract.py:288-312 fails on German umlauts (ß/ä/ö/ü) and $ID-prefixed names; 5 of 7 paragraph_styles rows in the calibrated baseline show null build_py and false sla_pstyle_present despite the matches existing.</blocker>
    <blocker>H3 — inventory_compare.py has no check for dropped add_para_style calls (only colors has a build_py_extra_color analogue). No M4 mutation test covers this regression path. Combined with H2 above, a missing or renamed paragraph style passes the gate undetected.</blocker>
  </blockers>
</verdict>

Brief overall assessment: The infrastructure is solid — schema, comparator, walkers, mutation tests, skill split, semantics catalog are all in place and structurally correct. The gate's primary contract (catch dropped Run text, anname, color) is verified by passing mutation tests. The shippable issues are real but bounded: SLA paragraph-style detection is silently broken (H1), paragraph-style joining loses umlaut-named styles (H2), and dropped add_para_style calls aren't gate-checked (H3). None compromises security or causes data loss; each weakens the gate's coverage in a specific, identifiable way. Recommend landing as warn (shippable, follow-up fixes track-able) rather than blocking on these — but fix H1 and H3 before relying on the gate to enforce regressions in production tuning sessions.

</review>

