---
review_of: 40-idml-import-two-agent-pipeline-with-script-based-inventory-gate
review_type: issue
review_mode: implementation
reviewed_at: 2026-05-13T21-21-38Z
tool: codex
model: gpt-5.4
duration_seconds: 327
---

<review>

<acceptance_criteria>
<criterion status="not_met" id="1">
  <text>All schema fields in SCAFFOLD_INVENTORY.yml populate for 26-03 leporello.</text>
  <reason>`text_runs.by_paragraph_style` is split into separate IDML-only and build.py-only rows with `sla_itext_count: 0` everywhere, and most paragraph-style joins are left null/false.</reason>
  <evidence>templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml:25-75; templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml:1642-1660; tools/inventory_extract.py:113-123; tools/inventory_extract.py:288-312</evidence>
</criterion>
<criterion status="met" id="2">
  <text>tools/inventory_compare.py exits 0 when comparing leporello against itself.</text>
  <evidence>tools/inventory_compare.py:187-192 returns `0` when there are no missing sections, no extra sections, and no count deltas.</evidence>
</criterion>
<criterion status="met" id="3">
  <text>tools/inventory_compare.py exits 2 when an inventory element is missing.</text>
  <evidence>tools/inventory_compare.py:100-103 and tools/inventory_compare.py:187-188 promote any missing section to exit code 2; tests/unit/test_inventory_gate_mutations.py:141-171 and tests/unit/test_inventory_gate_mutations.py:212-225 assert `rc == 2` for missing text/anname/color mutations.</evidence>
</criterion>
<criterion status="partially_met" id="4">
  <text>tools/inventory_compare.py exits 3 when an unexpected element appears.</text>
  <reason>It only treats extra frame/style/color/asset keys as drift. Count-only drift and flipped boolean fields do not populate `extra`, so they fall through to exit 0.</reason>
  <evidence>tools/inventory_compare.py:91-144 only builds `extra` from key sets; tools/inventory_compare.py:184-192 ignore positive count deltas unless some `extra` key was already recorded.</evidence>
</criterion>
<criterion status="met" id="5">
  <text>The three mutation tests mutate a copy of build.py and assert exit-code 2.</text>
  <evidence>tests/unit/test_inventory_gate_mutations.py:56-69 copies the anchor into a temp directory; tests/unit/test_inventory_gate_mutations.py:76-106 shells out to `inventory_extract.py` and `inventory_compare.py`; tests/unit/test_inventory_gate_mutations.py:143-145, tests/unit/test_inventory_gate_mutations.py:165-166, and tests/unit/test_inventory_gate_mutations.py:214-215 assert `rc == 2`.</evidence>
</criterion>
<criterion status="met" id="6">
  <text>.claude/skills/idml-scaffold/SKILL.md and .claude/skills/idml-tune/SKILL.md exist and reference the inventory CLIs by name.</text>
  <evidence>.claude/skills/idml-scaffold/SKILL.md:36-45 and .claude/skills/idml-tune/SKILL.md:29-40 reference `tools/inventory_extract.py` and `tools/inventory_compare.py`.</evidence>
</criterion>
<criterion status="met" id="7">
  <text>.claude/skills/idml-tune/forbidden_paths.md lists tools/idml_to_dsl.py, tools/sla_lib/**, and other shared converter code.</text>
  <evidence>.claude/skills/idml-tune/forbidden_paths.md:12-22 lists `tools/idml_to_dsl.py`, `tools/idml_to_dsl_patterns/**`, `tools/sla_lib/**`, `tools/walkers/**`, and other shared paths.</evidence>
</criterion>
<criterion status="met" id="8">
  <text>docs/scribus-sla-attribute-semantics.md exists and has sections for the 8 named attributes.</text>
  <evidence>docs/scribus-sla-attribute-semantics.md:17; docs/scribus-sla-attribute-semantics.md:46; docs/scribus-sla-attribute-semantics.md:69; docs/scribus-sla-attribute-semantics.md:101; docs/scribus-sla-attribute-semantics.md:130; docs/scribus-sla-attribute-semantics.md:152; docs/scribus-sla-attribute-semantics.md:189; docs/scribus-sla-attribute-semantics.md:218</evidence>
</criterion>
<criterion status="met" id="9">
  <text>python3 tools/inventory_extract.py --help runs.</text>
  <evidence>tools/inventory_extract.py:459-487 defines a complete argparse CLI with `--slug`, `--templates-dir`, `--originals-dir`, `--repo-root`, and `--output`.</evidence>
</criterion>
<criterion status="met" id="10">
  <text>tools/idml_inventory.py back-compat shim does not break existing callers.</text>
  <evidence>tools/idml_inventory.py:1-14 re-exports all non-dunder names from `tools.walkers.walk_idml_inventory`; tools/render_pipeline.py:780-789 still imports and calls `run_inventory`; tests/unit/test_idml_inventory.py:19-27 still import legacy helpers from `idml_inventory`.</evidence>
</criterion>
<criterion status="partially_met" id="11">
  <text>The Stage-2 forbidden-paths list is documentation only, and the documentation is honest about the lack of enforcement.</text>
  <evidence>.claude/skills/idml-tune/forbidden_paths.md:35-46 explicitly says mechanical enforcement is only “recommended” and the hook script is out of scope for this PR.</evidence>
</criterion>
<criterion status="partially_met" id="12">
  <text>Stage 1 blocks on the structural gate.</text>
  <reason>The scaffold-only path emits `SCAFFOLD_INVENTORY.yml` but explicitly treats extraction failure as non-fatal and never evaluates the gate fields.</reason>
  <evidence>tools/idml_import_driver.py:519-537</evidence>
</criterion>
</acceptance_criteria>

<findings>

<finding severity="high" id="H1">
  <title>Scaffold-only never enforces the Stage-1 structural gate</title>
  <location>tools/idml_import_driver.py:519-537</location>
  <description>The issue contract says Stage 1 blocks when required structure is missing, but the only integration point here just calls `build_inventory()`, writes YAML, and swallows all extraction failures as “non-fatal”. There is no comparison or validation step after emission, so a scaffold with missing IDML runs, missing assets, or broken joins still exits 0. That leaves the advertised two-stage pipeline without an actual Stage-1 gate.</description>
  <fix>After emitting the inventory, evaluate the Stage-1 blockers from the extracted snapshot and return non-zero on failure. If the intent is to defer enforcement, the skill/docs/acceptance table need to be downgraded to match the implemented behavior.</fix>
</finding>

<finding severity="high" id="H2">
  <title>The comparator ignores most of the schema fields that are supposed to be gated</title>
  <location>tools/inventory_compare.py:35-49; tools/inventory_compare.py:91-192; tools/walkers/schema.py:58-133</location>
  <description>`compare()` only checks frame annames, paragraph-style/color/asset IDs, a few numeric counters, and missing build.py words. It never compares `build_py`, `sla_pstyle_present`, `sla_color_present`, `on_disk`, `sla_pageobject_present`, `sla_pfile_present`, or `pdf_image_present`, even though those fields are part of the schema contract. A regression like “same anname still exists, but the SLA object lost its `PFILE`” or “style row still exists, but `sla_pstyle_present` flipped false” will still return exit 0.</description>
  <fix>Extend `compare()` to diff all boolean/value-bearing contract fields, not just key presence. In particular, paragraph-style rows should fail when `build_py` disappears or `sla_pstyle_present` flips false, image/text frames should fail on `sla_*` / `pdf_image_present` regressions, and assets should fail when `on_disk` flips false.</fix>
</finding>

<finding severity="high" id="H3">
  <title>The paragraph-style joins are broken, so the committed baseline ships placeholder rows instead of a usable cross-source matrix</title>
  <location>tools/inventory_extract.py:92-123; tools/inventory_extract.py:288-312; tools/walkers/walk_sla.py:69-78; templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml:25-75; templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml:1642-1660</location>
  <description>The extractor is supposed to populate one per-style row across IDML, build.py, SLA, and PDF. Instead, it unions raw IDML names like `ParagraphStyle/Absatzformat 1` with build.py names like `idml/absatzformat-1`, producing separate rows with zeroes on the opposite side. The same mismatch leaves most `paragraph_styles[].build_py` fields null and most `sla_pstyle_present` fields false in the anchor baseline. The result is a baseline full of placeholders rather than the calibrated inventory the issue asked for.</description>
  <fix>Normalize style identities across all three surfaces before joining. The extractor should map IDML style names to the corresponding build/SLA identifiers and emit one row per logical style with all counts/presence fields populated.</fix>
</finding>

<finding severity="high" id="H4">
  <title>`every_idml_run_present_in_build_py` is not the required set-equality check</title>
  <location>tools/walkers/walk_idml_inventory.py:764-779; tools/inventory_extract.py:125-137</location>
  <description>The design contract requires “set-equality on `(text, font, fontsize)`”, but the IDML walker throws away the detailed `_runs` list and the join code reduces the flag to `sum(build_py_counts) >= total_idml`. That means a template can replace one IDML run with different text or style, keep the count constant, and still report `every_idml_run_present_in_build_py: true`. This is a direct miss on the Stage-1 blocker “Any IDML CharacterStyleRange text content is missing from build.py”.</description>
  <fix>Persist the IDML-side run tuples in the inventory and compare exact counters/sets against the build.py-side `TextRun` tuples when computing the flag or when running `inventory_compare.py`.</fix>
</finding>

<finding severity="medium" id="M1">
  <title>`pdf_image_present` is set from a document-wide “any image exists” check, not from per-frame matching</title>
  <location>tools/inventory_extract.py:190-194; tools/inventory_extract.py:221-248; templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/SCAFFOLD_INVENTORY.yml:780-958</location>
  <description>The planned contract was “found via pdfimages, matched by size/position” per image frame. The implementation instead sets a single `pdf_has_images = len(pdf_images) &gt; 0` flag and copies that boolean into every image-frame row. In the committed baseline, every image frame is marked `pdf_image_present: true`, including the inline composite/icon frames with no `PFILE`, simply because the PDF contains some images somewhere. A single dropped raster placement would therefore be invisible at the extraction layer.</description>
  <fix>Match grouped `pdfimages` rows to image frames by page and geometry, then populate `pdf_image_present` per frame instead of per document.</fix>
</finding>

<finding severity="medium" id="M2">
  <title>The promised position-based fallback for Self-ID drift was never wired up</title>
  <location>tools/inventory_extract.py:167-182</location>
  <description>The issue docs explicitly called out IDML `Self` drift and required a secondary `(kind, round(mm_position, 1))` join. The code defines `_build_pos_index()` for exactly that purpose, but never calls it; all downstream joins still use `bp_*[anname]` lookups only. A re-exported IDML with new `Self` IDs will therefore degrade into blanket missing/extra noise instead of using the documented fallback.</description>
  <fix>Build the per-kind position indexes for the IDML and build.py rows and consult them whenever the primary `anname` lookup misses.</fix>
</finding>

</findings>

<strengths>
<strength>tools/walkers/walk_build_py.py:180 uses `ast.parse` and then `ast.literal_eval`-guarded extraction instead of importing or executing `build.py`, which matches the safety requirement for the AST walker.</strength>
<strength>tools/walkers/walk_sla.py:42-90 reuses `tools.sla_lib.reader.SLADocument` rather than reparsing the SLA ad hoc, which keeps the new walker aligned with the existing reader contract.</strength>
<strength>tests/unit/test_inventory_gate_mutations.py:56-106 mutates a temp copy of the template and shells through the real CLI pair, so the three regression tests exercise the actual extract/compare path instead of a mocked helper.</strength>
</strengths>

<traces>
<trace name="extract flow">
  tools/inventory_extract.py:402-455 → tools/walkers/walk_idml_inventory.py:740-815 → tools/walkers/walk_build_py.py:158-307 → tools/walkers/walk_sla.py:19-90 → tools/walkers/walk_pdf.py:19-43 and tools/walkers/walk_pdf.py:77-117 → tools/walkers/schema.py:159-166
</trace>
<trace name="compare flow">
  tools/inventory_compare.py:226-254 → tools/inventory_compare.py:85-204 → frame key diffs at tools/inventory_compare.py:91-105 → count deltas at tools/inventory_compare.py:64-82 and tools/inventory_compare.py:151-167 → exit code selection at tools/inventory_compare.py:184-192
</trace>
<trace name="driver hook path">
  bin/idml-import:1-11 → tools/idml_import_driver.py:517-537 → tools/inventory_extract.py:402-455
</trace>
<trace name="mutation M1">
  tests/unit/test_inventory_gate_mutations.py:120-151 mutates one `Run(text=...)` to empty, then calls extract at tests/unit/test_inventory_gate_mutations.py:76-93 and compare at tests/unit/test_inventory_gate_mutations.py:95-106, asserting exit code 2 at tests/unit/test_inventory_gate_mutations.py:143-145
</trace>
</traces>

<verdict value="warn" critical="0" high="4" medium="2">
  <blockers>
    <blocker>The Stage-1 scaffold path emits inventory data but does not actually gate on it, so the advertised two-stage pipeline is only partially implemented.</blocker>
    <blocker>The comparator is too weak to enforce large parts of the schema contract, including most SLA/PDF presence booleans.</blocker>
    <blocker>The committed leporello baseline is not a fully populated cross-source inventory because the style joins are broken.</blocker>
  </blockers>
</verdict>

</review>
<verdict value="warn" critical="0" high="4" medium="2">
Significant contract gaps remain in the gate implementation: the scaffold path does not enforce the Stage-1 gate, the comparator ignores much of the schema, and the committed baseline still contains placeholder style rows.

