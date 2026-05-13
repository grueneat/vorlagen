# Pitfalls and edge cases — issue #39 (brand-embed-only scope)

**Scope:** Phase A (path canonicalisation) + Phase B (asset_policy audit, FORCE empty `shipped:`) + Phase C (inline-embed every asset) + Phase F (v2-falzflyer migration). Phases D/E/G deferred per CONTEXT.md.

**Confidence breakdown** — HIGH for items grounded in code/file inspection (#1, #2, #4, #5, #6, #8, #10, #11, #12); MEDIUM for items relying on Scribus behavior docs (#3, #9); LOW for items projecting from third-party sources (#13).

This file contains specific failure modes for the first PR. Each item is grounded in concrete evidence from `/workspace/tools/`, `/workspace/templates/`, `/workspace/shared/` and pairs with a mitigation that lands IN the first-PR scope.

---

## 1. `shipped:` rejection awkwardness — silent-embed temptation

**Confidence:** HIGH (grounded in CONTEXT.md and skill doc).

**What goes wrong:** The schema at `/workspace/shared/asset-policy.schema.yaml` accepts `shipped:` as a `required` key (line 27 of the YAML), so users authoring a new `meta.yml::asset_policy` will see the key in the schema and the example in `/workspace/.claude/skills/idml-import/asset_policy.md` lines 88-97 (which shows BOTH `embedded:` and `shipped:` with real entries — `plakat-dunkel-fuer-flyer.png` is in `shipped:` per the doc). Users will copy the example, hit the audit's "shipped must be empty for now" rejection, and reach for the easiest unblock: silently move the asset to `embedded:`, accepting the multi-MB inline bloat just to ship.

**Why it happens:** The audit error message is the only signal between schema-permissive and runtime-strict; a terse `ValueError("shipped not allowed")` does not direct the user to context.

**How to avoid (in-scope mitigation):**

1. The audit error message must be VERBATIM the text already mandated by CONTEXT.md (rule #1, lines 56-59). Drop it into `tools/asset_policy_audit.py` as a constant `_SHIPPED_REJECTED_MSG`; raise `ValueError(_SHIPPED_REJECTED_MSG)` not a one-liner.
2. The message references issue #39 and the brand-team deferral so the user understands this is temporary policy, not permanent rule.
3. Update `/workspace/.claude/skills/idml-import/asset_policy.md` (lines 88-97 and lines 138-156) to add a banner "**First-PR rule (issue #39):** `shipped:` MUST be empty. Every asset goes in `embedded:`. The example below shows the eventual split; today's audit rejects any `shipped:` entry." Don't remove the eventual-state example because that breaks forward-compat understanding.
4. Update the schema description text at `/workspace/shared/asset-policy.schema.yaml` line 33-37 to add `Note: first-PR rule per issue #39 — must be an empty list. Forward-compat key only.` This is a docstring-only change; jsonschema still accepts non-empty (and the audit rejects).

**Warning signs (post-merge):** PR diffs that move an asset previously in `shipped:` to `embedded:` with no `meta.yml::brand_overrides` justification entry. Add a soft heuristic to `tools/check_overrides_growth.py` (already present at `/workspace/tools/check_overrides_growth.py`) that warns on `asset_policy::embedded` list growth.

---

## 2. Inline embedding SLA-size blowup — v2 jumps 58KB → ~18MB, a 316x increase

**Confidence:** HIGH (computed from on-disk file sizes).

**What goes wrong:** Measured per-file:

| Asset | Raw bytes | After qCompress+base64 (≈zlib-on-already-compressed + ×1.37) |
|-------|----------:|------:|
| `plakat-dunkel-fuer-flyer.png` | 8,558,653 | ~11.7 MB |
| `green-pine-trees-covered-with-fog-crop.png` | 4,608,235 | ~6.3 MB |
| `gruene-logo-bund-weiss-cmyk.png` | 49,604 | ~68 KB |
| `social-media-icon-instagram.png` | 48,436 | ~66 KB |
| `website-weiss.png` | 40,426 | ~55 KB |
| `social-media-icon-tiktok.png` | 37,070 | ~51 KB |
| `bluesky-weiss.png` | 29,217 | ~40 KB |
| `social-media-icon-facebook.png` | 28,688 | ~39 KB |
| `mail-weiss.png` | 25,524 | ~35 KB |
| **Sum of 9 referenced assets** | **13,425,853 (12.8 MB)** | **~18.4 MB** |

Current v2 SLA is **58,037 bytes**. The post-Phase-C size is ~316× the current. The next-biggest committed SLA (v1 kandidat-falzflyer at 927 KB with 8 inline images) is ~20× smaller than what v2 will become. The two giants `plakat-dunkel-fuer-flyer.png` (8.5 MB) and `green-pine-trees-covered-with-fog-crop.png` (4.6 MB) account for ~95 % of the bloat.

**Why it happens (concrete):** Both are content/photo-grade rasters, not brand glyphs. They were authored in the IDML as full-bleed page-2 elements. The skill doc at `/workspace/.claude/skills/idml-import/asset_policy.md` lines 158-165 even WARNS against this exact failure mode (`would balloon SLA files into 10MB blobs that are painful to edit`). CONTEXT.md overrides that caution explicitly for the first PR because shipping a working download today beats waiting on the brand decision.

**Git history bloat (HIGH):** SLAs are tracked as `text eol=lf` per `/workspace/.gitattributes` line 1, NOT as LFS. The diff cost on each re-emit is proportional to the embedded base64 (every re-emit invalidates the inline blob because qCompress isn't deterministic across image-content changes). Round-trip churn on `tools/idml_to_dsl.py` extensions in subsequent issues will inflate the pack file with ~18MB-per-change.

**How to avoid (in-scope mitigation):**

1. **Document the size jump in EXECUTION.md.** Phase F's preview-diff step (per ISSUE.md line 311) must include the size delta as a recorded number, not a hand-wave. Write `du -b templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla` before/after and put both numbers in `EXECUTION.md` as a TOLERANCE_LOG row of kind `sla-size-bloat`.
2. **Add `*.sla` to LFS in `.gitattributes`** as part of this PR. The line `*.sla   filter=lfs diff=lfs merge=lfs -text` (REPLACING the existing `*.sla         text eol=lf` line). Without LFS, the v2 SLA's 18MB will appear in every pack on clone. Audit risk: this changes diff behaviour (Scribus SLAs become opaque blobs for line-diff purposes); the existing `tools/sla_diff.py` already parses the XML, so functional diffing keeps working.
3. **Re-validate ALL existing SLAs.** v1-falzflyer (927 KB), zeitung-a4-grun (540 KB), infostand-tent-card-a5-quer (461 KB) currently inline 8/6/6 images respectively as text-tracked files. Decision: either accept the existing text-tracked baseline OR migrate everything to LFS at once. Per `feedback_working_over_theoretical.md`, the working state is "everything text-tracked"; switching to LFS is a bigger surface. **Concrete suggestion:** keep text-tracked for now but add a CI lint `tools/check_sla_size.py` that warns (not fails) above 5MB and FAILS above 20MB.
4. **Defer the two giant photos** — `plakat-dunkel-fuer-flyer.png` (8.5 MB) and `green-pine-trees-covered-with-fog-crop.png` (4.6 MB) are exactly the assets CONTEXT.md says are "stock / brand-supplied content; brand team has already approved them shipping inline" (lines 84-86). So the user has signed off on the 18MB outcome. **Mitigation is to document, not to argue with the decision.**

**Warning signs:** GitHub PR diff view times out on the SLA; `git status` slows down; clone bandwidth complaint.

---

## 3. Preview-pipeline assumption: cwd-resolution of relative PFILE paths is brittle

**Confidence:** MEDIUM (grounded in tool source comments + Scribus docs; not directly tested with relative PFILE in this codebase).

**What goes wrong:** CONTEXT.md lines 110-115 asserts: "`template.sla` references brand assets inline (no path needed) and content assets via relative paths like `shared/assets/<slug>/<basename>` (resolved against the repo root when the SLA opens from `templates/<slug>/`)." That statement is provably incomplete:

- `/workspace/tools/render_pipeline.py:179-210` explicitly notes (line 183-187): "Scribus on Ubuntu CI exits 0 without writing the PDF if the output path is relative (it changes cwd internally on openDoc), so we resolve to absolute paths". This is a known Scribus bug: cwd is unstable inside `scribus.openDoc()`. Relative PFILE paths inside the SLA are thus resolved against an UNKNOWN cwd at render time, not the SLA's own directory and not the original CLI cwd.
- The Scribus wiki ([fileproblems.html](https://fossies.org/linux/scribus/doc/en/fileproblems.html), [Correcting_broken_image_file_paths](https://wiki.scribus.net/canvas/Correcting_broken_image_file_paths)) claims paths are stored relative to the SLA file. Empirically this is the GUI-open behavior. The Scripter `openDoc()` path is different.

But — **for the brand-embed-only first PR, every asset is `embedded:` and the SLA contains NO `PFILE=` strings pointing to external files** (per the audit's force-empty-`shipped:` rule). So this pitfall only applies to the audit's edge-case behavior:

**Edge case in scope:** What if `links_export.yml` has an entry the user EXPLICITLY tries to move to `shipped:` (which the audit rejects)? The error must not let the user "work around" the rejection by leaving the asset entirely OUT of the policy — that would make `_emit_image_content` (line 2128-2143 of `idml_to_dsl.py`) follow the legacy `assets_dir / basename` path (line 2157), which absolute-resolves at line 2163. The bug returns.

**How to avoid (in-scope mitigation):**

1. **Strict coverage rule in `asset_policy_audit.py`:** Every entry in `shared/assets/<slug>/links_export.yml::assets[*].output` MUST appear in EITHER `embedded:` OR `shipped:`. (For first-PR, `shipped:` is empty, so effectively all must be in `embedded:`.) Missing-from-policy → audit FAIL with a clear actionable error.
2. **Strict converter coupling:** `tools/idml_to_dsl.py::_emit_image_content` must check `meta.yml::asset_policy` and:
   - If `basename in embedded:` → emit `pack_inline_image(image_bytes, ext)` via existing primitive at `/workspace/tools/sla_lib/builder/primitives.py:759`.
   - If `basename in shipped:` → for first-PR, the audit has already failed before reaching here (non-empty shipped rejected). Defensive: still raise `UnhandledElement(f"shipped: not yet supported in first-PR for {basename}; see issue #39")`.
   - If `basename` is in NEITHER list → raise `UnhandledElement(...)` with the message "asset X unclassified; bin/idml-import should have stopped before this point".
3. **Drop the absolute-path fallback** at `idml_to_dsl.py:2163-2170`: with the strict policy gate above, the fallback branch is unreachable. Leaving dead code that emits absolute paths is the exact bug Phase A is fixing.
4. **For Phase A's standalone-without-Phase-B period** (if the PR lands as 3 sub-phases per ISSUE.md): the converter must default to repo-relative paths even when `meta.yml::asset_policy` is missing. The relative-path branch at lines 2165-2170 (`asset_path.resolve().relative_to(ROOT)`) is already there but unreachable when `--asset-map` is supplied. Fix line 2133 (`abs_mapped = str(Path(mapped).resolve()) if not Path(mapped).is_absolute() else mapped`) to use the same `relative_to(ROOT)` logic.

**Sources:**
- [Scribus wiki — Correcting broken image file paths](https://wiki.scribus.net/canvas/Correcting_broken_image_file_paths) — paths stored relative to SLA file in GUI workflow.
- [Scribus fileproblems doc](https://fossies.org/linux/scribus/doc/en/fileproblems.html) — recommends co-located images for portability.
- `/workspace/tools/render_pipeline.py:182-187` — codebase-internal note on openDoc cwd instability.

---

## 4. v2-falzflyer's 13 hand-patches via inject.yml — re-emission flow

**Confidence:** HIGH (grounded in `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml` and `/workspace/tools/reconcile_build_py.py`).

**What goes wrong:** v2-falzflyer has 13 hand-patches in `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml` (I counted). They include:

- `useDocBleeds` SLA-level override
- 4 ParaStyle align/linesp overrides (`fliesstext_auf_gruenem_hintergrund`, `absatzformat_1`, `aufzaehlungen_auf_gruenem_hintergrund`, `subheadline_cover_zentriert`)
- 4 TextFrame y-coordinate deltas (`u1c7`, `u1fd`, `u265`, `u295` — FirstBaselineOffset compensation)
- 1 TextFrame `default_style_attrs={ALIGN:1}` (`u376`)
- 1 ImageFrame `scale_type=0` (`u3e7`) for composite-AI sub-icon visibility

Phase F requires `bin/idml-import --reimport`. The flow is: converter emits `build.py.generated`, then `tools/reconcile_build_py.py` applies `inject.yml` to produce `build.py`. Investigating `reconcile_build_py.py` lines 50-330:

- The reconciler is regex-based per its own docstring (line 190): "the current `tools/reconcile_build_py.py` regex-based applier cannot safely round-trip; those are marked with `follow_up_issue`".
- It locates `(element=, anname=...)` constructor calls and patches `field=value` kwargs.

**Risk:** When Phase C changes ImageFrame call shape from `image='/abs/path.png'` to `inline_image_data=<base64>, inline_image_ext='png'`, the `u3e7` inject entry `field: scale_type, set: 0` may no longer be locatable by the regex if the constructor's kwarg layout changes substantially. The reconciler does NOT yet handle the `scale_type` kwarg being on a different line than `image=`.

**How to avoid (in-scope mitigation):**

1. **Run `reconcile_build_py.py --check` BEFORE and AFTER Phase C** as a CI gate. Both must pass.
2. **Add a Phase F sub-task:** After re-emission, run `python3 tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2` and assert `build.py` contains all 13 inject markers (`# P5/inject (from inject.yml line N)`). If any are missing, the reconciler dropped them silently — abort.
3. **Pre-emit invariant test:** add `tests/test_v2_reimport_preserves_injects.py` that snapshots `inject.yml` line count vs `# P5/inject` marker count in the resulting `build.py`. Asserts equality.
4. **For `u3e7`'s `scale_type=0` injection in particular:** the converter must keep emitting `scale_type=0` for ALL ImageFrame calls (it's the converter default per `/workspace/tools/sla_lib/builder/primitives.py:789`), so the inject's `set: 0` will be a "redundant inject" warning. That's recoverable (the warning is non-fatal per `reconcile_build_py.py:286-287`).
5. **No silent re-base of inject.yml.** The Phase F migration must NOT delete entries from `inject.yml` just because they happen to coincide with converter output. Each entry has a `classification` and `reason`; removal requires explicit `follow_up_issue` cross-link.

---

## 5. Composite-AI handling: ALREADY SPLIT — but the audit logic must understand it

**Confidence:** HIGH (verified from file inventory).

**What was assumed wrong in the prompt:** The user's prompt claims "v2-falzflyer's `social-media-icons-weiss.png` is a composite (4 icons in one strip). The current emit references the composite via per-icon crops (LocalOffset). With inline embedding, every reference to the composite embeds the FULL composite into the SLA at each ImageFrame. That's 4x the data."

This is INCORRECT for the current state. I verified directly:

- `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` references **per-icon** PNGs by basename: `social-media-icon-facebook.png`, `social-media-icon-instagram.png`, `social-media-icon-tiktok.png`, `bluesky-weiss.png`, `website-weiss.png`, `mail-weiss.png` (9 unique image paths total).
- The composite strip `social-media-icons-weiss.png` exists in `/workspace/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/` (116 KB) but is **NOT referenced from build.py** (`grep -c social-media-icons-weiss` in build.py returns 1 occurrence — it's only the comment at line 752).
- The split into per-icon PNGs already happened (issue #38 P5 work). Each ImageFrame gets one ~30-50 KB PNG, not a slice of a 116 KB composite.

So the 4x-bloat pitfall the prompt anticipated does NOT exist; the actual risk is different:

**Actual pitfall:** The composite file is on disk and in `links_export.yml::assets["Social Media Icons weiss.ai"]::output` (verified at `/workspace/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/links_export.yml:18-20`) but is NEVER referenced by build.py. The strict `asset_policy_audit.py` (per ISSUE.md Phase B.1 acceptance criterion: "every asset in `links_export.yml` appears in exactly one of `embedded`/`shipped`") will FORCE `social-media-icons-weiss.png` into one bucket. Per CONTEXT.md it must be `embedded:`. But embedding it inline produces ~160 KB of base64-bloat for an asset that no ImageFrame loads. **Dead-weight embed.**

Additionally: 3 derivative files exist on disk but NOT in `links_export.yml`:
- `social-media-icon-facebook.png`, `-instagram.png`, `-tiktok.png` (the pdftocairo splits of the composite)
- They ARE referenced from build.py.

So `shared/assets/<v2>/` (12 files), `build.py` (9 referenced), and `links_export.yml` (7 entries — counting the .ai → .png outputs) have THREE different sets. The audit's exact rules must reconcile this.

**How to avoid (in-scope mitigation):**

1. **Define "asset universe" as `links_export.yml::assets[*].output`** (per ISSUE.md Phase B.1) **PLUS files at `shared/assets/<slug>/*` that are not `links_export.yml`**. The audit must walk the directory and reconcile both sets.
2. **For the v2-falzflyer composite specifically:** `social-media-icons-weiss.png` should be `embedded:` per CONTEXT.md line 75 ("social-media-icons-weiss.png (composite reference)") but NOT emitted as an ImageFrame in the SLA. The audit's coverage rule is "is in policy" (yes), not "is loaded by SLA" (no). The composite is policy-cataloged for traceability even if it's not used. This is fine — the inline bloat is small (~160 KB; the composite is tiny next to the two giants).
3. **For the per-icon PNGs (`-facebook.png`, etc.):** they exist on disk and are referenced by build.py. The audit must accept them. Two options:
   - **Option A (cleaner):** generate `links_export.yml` entries for the derivative per-icon PNGs (a side-effect of `composite_ai_split.py`).
   - **Option B (less invasive for first-PR):** the audit reconciles by `shared/assets/<slug>/` filesystem walk, not strictly by `links_export.yml`. Then per-icon PNGs are in scope automatically.
   - **Recommended for first PR:** Option B. Add to ISSUE.md Phase B as a clarification.
4. **Documentation:** the audit's error messages must distinguish:
   - "asset X is on disk but not in policy" (most-common case)
   - "asset Y is in policy but not on disk" (likely typo)
   - "asset Z is in links_export.yml but missing from policy" (subset of "on disk but not in policy" when the asset is a converter output)

---

## 6. Test breakage: PFILE-substring assertions break, but `inline_image_data` assertions PASS

**Confidence:** HIGH (verified by grep across `tools/sla_lib/tests/`).

**What goes wrong:** I checked all 30 test files in `/workspace/tools/sla_lib/tests/`. Findings:

- ZERO tests assert against the literal string `PFILE=`. Searched: `grep -rln 'PFILE' /workspace/tools/sla_lib/tests/` returns no hits.
- 15+ tests already use `inline_image_data` as the assertion target. Including v1 kandidat-falzflyer (`test_kandidat_falzflyer_geometry.py:230-238`) which expects `pack_inline_image(expected.read_bytes(), "png")` byte-equality.
- `test_image_frame_coverage.py:88` requires every ImageFrame in the parsed Document tree to "bind image content via inline_image_data". Today this passes only because v1-falzflyer + 7 other templates already have inline_image_data set. v2-falzflyer is the OUTLIER that currently FAILS this invariant.

So Phase C's inline-everything move actually *fixes* a latent invariant the test suite already expects. **The test suite is already wired for the post-Phase-C world.** This is good news — the pre-existing test bed protects the migration.

**Two concrete tests will need new content for v2:**

1. **`test_kandidat_falzflyer_variant_scaffold.py`** (in `/workspace/tools/sla_lib/tests/test_falzflyer_variant_scaffold.py`) — likely asserts v2 ImageFrame structure; will need updated expectations after Phase C. Investigate during planning.
2. **No new test for v2 inline-image byte-identity** exists today (parallel to v1's at `test_kandidat_falzflyer_geometry.py:230-238`). The Phase F migration should add `test_v2_falzflyer_geometry.py::test_inline_image_byte_identity` that does the same check for v2.

**How to avoid (in-scope mitigation):**

1. **Run the full test suite before and after Phase C.** Specifically:
   - `python3 -m pytest tools/sla_lib/tests/test_image_frame_coverage.py -x` — should now PASS for v2 (was failing implicitly because v2 isn't covered in tests today).
   - `python3 -m pytest tools/sla_lib/tests/test_falzflyer_variant_scaffold.py -x` — update expectations if needed.
2. **Add a Phase F test** mirroring v1's: `test_v2_falzflyer_geometry.py` that verifies inline_image_data byte-identity for the 9 referenced assets.
3. **Audit test for v2:** add `test_asset_policy_audit_v2.py` that runs the audit against v2's policy + links_export.yml and verifies it passes (after migration) AND that any rejection scenario (non-empty `shipped:`, missing classification, in-policy-not-on-disk) raises the expected error message.

---

## 7. The grep-ban on absolute paths needs a regex broad enough to catch path variants

**Confidence:** HIGH (regex specification).

**What goes wrong:** ISSUE.md Phase A.3 specifies: "grep-bans `/workspace/`, `/home/`, `/root/`, `/tmp/` prefixes in `PFILE=` attributes". Three holes in that:

1. **Windows-style paths** (`C:\` or `C:/`) if someone runs the converter on Windows. Low likelihood but the ban is cheap to extend.
2. **`file://` URIs.** SLA can in principle carry `PFILE="file:///workspace/..."`. The string `/workspace/` would still match, but if someone slipped a `file:///home/user/...`, the existing ban catches `/home/`.
3. **Other Unix system prefixes** (`/var/`, `/opt/`, `/Users/` on macOS, `/private/var/` on macOS too).

The grep should be a single regex that matches "any PFILE value whose first path segment starts with `/`, `[A-Z]:\`, or `file://`":

```
PFILE="(/|file://|[A-Za-z]:[\\/])
```

**How to avoid (in-scope mitigation):**

1. **Use a broad regex in `tools/check_no_absolute_paths_in_sla.py`:**
   ```python
   _ABS_PFILE = re.compile(r'PFILE="(/|file://|[A-Za-z]:[\\/])')
   ```
   This catches Unix-absolute (any prefix), file URIs, and Windows drive letters. Rejects with the offending file + line number.
2. **Inline path check applies to `ICCProfile=` and other `*FILE=` attributes too.** Audit `tools/sla_lib/builder/primitives.py` for emitter sites that take paths and could leak; ICC profile paths likely also need the same check (`PRFILE="sRGB display profile (ICC v2.2)"` is a NAME, not a path, so it's safe — but if a custom ICC profile is added, it would be a path). Defensive: lint all `PFILE=`, `LDFILE=` (Document linked file), and audit one-time during this PR for other attributes that could carry paths.
3. **Add a positive-test:** `tests/test_check_no_absolute_paths.py` synthesizes SLA fragments with each path variant and asserts the linter catches all of them. Pin the regex behavior.
4. **Skip inline-image SLAs in the LINT but not in the assertion of "any path is repo-relative":** an SLA with `isInlineImage="1"` has `PFILE=""` (empty string per `/workspace/tools/sla_lib/builder/primitives.py:811`) — the regex `r'PFILE="(/|...)' ` does NOT match the empty string, so this is already safe.

---

## 8. `--reimport` flow: build.py.generated regeneration must precede reconcile

**Confidence:** HIGH (verified from `reconcile_build_py.py` and `bin/idml-import`).

**What goes wrong:** Per `/workspace/tools/reconcile_build_py.py:185-203`, the reconciler reads `build.py.generated` and writes `build.py`. The converter (`idml_to_dsl.py`) emits `build.py.generated`. So Phase F's `bin/idml-import --reimport` flow is:

```
1. tools/idml_to_dsl.py … → build.py.generated   (new shape: inline_image_data=...)
2. tools/asset_policy_audit.py                    (passes if policy is correct)
3. tools/reconcile_build_py.py kandidat-…-v2     → build.py (applies 13 injects)
4. python build.py                                → template.sla   (now inline)
5. bin/render-gallery                             → preview.pdf, page-NN.png
6. tools/check_no_absolute_paths_in_sla.py        → 0 hits
```

**Specific risks:**

1. Per the pre-commit config at `/workspace/.pre-commit-config.yaml:23-26`, `reconcile-build-py-check` runs on EVERY commit. If Phase A is committed without Phase B+C, the reconciler will detect that `build.py` no longer matches `build.py.generated` (because Phase A modified `idml_to_dsl.py` to emit relative paths in `build.py.generated`, so `build.py` is stale until re-reconciled). Fix: re-run reconcile after Phase A's converter change, commit the resulting `build.py.generated` + `build.py` together.

2. The `inject.yml` entry for `u3e7`'s `scale_type=0` is REDUNDANT after Phase C: the converter already emits `scale_type=0` per `/workspace/tools/sla_lib/builder/primitives.py:789`. After Phase C, `reconcile_build_py.py` will warn "redundant inject" (line 286-287). Acceptable — keep the inject for audit-trail reasons; the warning is non-fatal.

3. The `inject.yml` entry classified `composite_ai_split` (it claims issue #38 Task 14 obsoletes it). If Phase F doesn't also obsolete it cleanly, the `follow_up_issue` should be set to `#38` explicitly. Verify the existing entry's `follow_up_issue: null` is still correct after Phase F.

**How to avoid (in-scope mitigation):**

1. **Document the sequence** in EXECUTION.md as a numbered checklist (steps 1-6 above). The planner should make this explicit.
2. **CI must run both** `tools/asset_policy_audit.py` (Phase B) and `tools/check_no_absolute_paths_in_sla.py` (Phase A) on every commit so a partial landing trips early.
3. **Local sanity test:** after Phase F's re-emission, manually `python templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` and verify the output SLA has 0 `PFILE="/...` matches and 9 `isInlineImage="1"` matches (matching the build.py image= count).

---

## 9. Path-relative resolution: irrelevant for first-PR (all embedded), but documenting for completeness

**Confidence:** MEDIUM.

**What goes wrong:** The user's prompt pitfall #9 covers a real ambiguity in Scribus's PFILE resolution: GUI-open uses SLA-directory-relative paths, but Scripter `openDoc()` uses cwd-relative (per the comment in `/workspace/tools/render_pipeline.py:182-187`). This is a known gap that bites Phase D's `shipped:` flow.

For first-PR (Phase A/B/C/F) it is NOT an active failure mode because all assets are `embedded:` — the SLA carries NO `PFILE=<path>` external references. After Phase C and the audit pass, the only non-empty `PFILE=` strings should be the empty-string default emitted alongside `isInlineImage="1"` (per `/workspace/tools/sla_lib/builder/primitives.py:811`).

**How to avoid (in-scope mitigation):**

1. **Explicitly assert PFILE-emptiness in the first-PR audit.** Add to `tools/check_no_absolute_paths_in_sla.py` (or a sibling lint) a second check: for first-PR-era templates, every PAGEOBJECT with `PTYPE="2"` (ImageFrame) must have either `PFILE=""` or `isInlineImage="1"`. Reject any external PFILE because no `shipped:` is allowed yet.
2. **Defer Scribus-cwd documentation to issue #39's follow-up PR for Phases D/E**, but capture the open question in RESEARCH.md so the planner remembers.
3. **For the few external-PFILE templates that exist today** (none after Phase F's v2 migration — verified by grep, only v2 currently has external PFILE): there's no migration needed.

---

## 10. Audit cross-check rules: enumerate the four failure cases explicitly

**Confidence:** HIGH (specification clarification).

**What goes wrong:** ISSUE.md Phase B.1 specifies four conditions for the audit but is light on error messages. Concretely the audit must distinguish:

1. **`shipped` non-empty** → FAIL with the CONTEXT.md verbatim message.
2. **Asset in `embedded:` but NOT on disk at `shared/assets/<slug>/<basename>`** → FAIL with "asset X is in policy but not on disk; rerun `tools/links_export.py` OR remove from policy".
3. **Asset on disk OR in `links_export.yml` but NOT in policy** → FAIL with "asset Y is unclassified; add it to `embedded:` (the first-PR rule places all assets inline)".
4. **Asset in both `embedded:` AND `shipped:`** → already caught by `load_asset_policy()` (line 226-232 of `meta_schema.py`), `ValueError` raised at load time.

**How to avoid (in-scope mitigation):**

1. **Each error message must be a `const` at module top** of `tools/asset_policy_audit.py`. They're user-facing strings — pin them.
2. **Tests:** `tests/test_asset_policy_audit.py` runs each failure case against a fixture template and asserts both (a) exit code != 0, (b) the message matches verbatim. Without verbatim match, the user-facing UX silently drifts.
3. **Exit-code discipline:** the audit uses exit code 2 for "user-fixable" (unclassified, missing-on-disk) and exit code 3 for "policy-broken" (non-empty shipped). The skill / `bin/idml-import` can then offer different remediation prompts based on the exit code.
4. **Audit ordering:** `_run_audit` in `/workspace/tools/render_pipeline.py:662` runs MULTIPLE audits sequentially. ISSUE.md Phase B.1 says "wired into `_run_audit` BEFORE A1 inventory" — verify this is BEFORE asset_extraction_audit (Phase E, which currently runs first per the comment at line 693). Order: asset_policy_audit → asset_extraction_audit → A1 inventory. Add a comment block to render_pipeline.py explaining the ordering rationale.

---

## 11. Phase B's "every template passes the audit" cross-cutting AC — 8 templates need backfilled policies

**Confidence:** HIGH (verified by inventory).

**What goes wrong:** ISSUE.md cross-cutting AC: "All 9 existing templates pass the new audit (after a `meta.yml::asset_policy` block is authored for each, or via an `--asset-policy-skip` opt-out for non-IDML-sourced templates that don't have a Links/ directory)."

I verified: only ONE template has a `shared/assets/<slug>/links_export.yml` (`26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2`). The other 8 templates use inline embedding entirely (no shared/assets directory). So:

- **8 templates have NO `links_export.yml`** → they have no IDML-import flow → the audit must offer an `--asset-policy-skip` (or equivalent) opt-out per the AC.
- **OR** authoring a trivial `asset_policy::embedded:` block listing the inline-image basenames in their `build.py` (but those are referenced via `pack_inline_image(...)` from on-disk files like `shared/logos/...`, not from `shared/assets/<slug>/`).

**How to avoid (in-scope mitigation):**

1. **Make the audit OPT-IN per-template.** A template lacking `shared/assets/<slug>/` AND lacking `meta.yml::asset_policy` is skipped silently (logged at INFO level).
2. **A template with `shared/assets/<slug>/` MUST have `meta.yml::asset_policy`** (no silent skip). The presence of the shared/assets directory is the gate.
3. **For v2-falzflyer (the only one with shared/assets):** the audit runs strictly. For the other 8 (inline-only with no shared/assets/): the audit is a no-op.
4. **Test:** `test_asset_policy_audit_inline_only.py` confirms the no-op path for a template that has inline images but no `shared/assets/<slug>/`.
5. **Do NOT add `--asset-policy-skip` flag** unless absolutely necessary. The directory-presence gate is cleaner than a per-template opt-out flag.

---

## 12. `tools/links_export.py` keeps maintaining the manifest, but the SLA no longer references it

**Confidence:** HIGH (confirmed by reading idml_to_dsl.py + links_export.py).

**What goes wrong:** Per the user's prompt pitfall #3, `links_export.py` still runs (to build the manifest for the audit), but the SLA no longer references shared/assets via PFILE (all inline after Phase C). This creates an apparent disconnect:

- `shared/assets/<v2>/links_export.yml` keeps existing (12 files in shared/assets/, 7 in the manifest)
- `template.sla` has 0 PFILE references to shared/assets after Phase C
- The links are still loaded inline via the converter's `pack_inline_image()` call which reads bytes from disk at `idml_to_dsl.py` emit time

The `shared/assets/<slug>/` directory becomes a build-time-only resource (the converter reads bytes, embeds them, and the resulting SLA is self-contained).

**Implication for git:** `shared/assets/<v2>/*.png` files (totaling ~21 MB) STILL live in the repo because:
1. The converter needs them at emit time (Phase C reads file bytes for `pack_inline_image`).
2. Re-emission for any downstream issue needs the source files.
3. They're inputs, not outputs.

**Implication for users:** A user downloading `template.sla` does NOT need the `shared/assets/` directory. The brand-embed-only scope is fully self-contained on the user side. Per CONTEXT.md line 122, this is intentional.

**How to avoid (in-scope mitigation):**

1. **Add a note to `/workspace/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/links_export.yml`** (or a sibling `README.md`): "These files are source assets for the converter. After Phase C of issue #39, the SLA carries them inline; the user-facing download is self-contained. These files remain in the repo as build-time inputs for re-emission."
2. **Confirm the converter walks `shared/assets/<slug>/`** at emit time, reading raw bytes for `pack_inline_image`. This is currently NOT how `_emit_image_content` works (it just emits the path string). Phase C must add the byte-read step. Concrete code path: `idml_to_dsl.py:2128-2143` (asset_map hit) and 2157-2170 (legacy fallback) both need a branch that, when `basename in policy.embedded`, reads `(ctx.assets_dir / basename).read_bytes()` and calls `pack_inline_image(bytes, ext)` to emit `inline_image_data=...`.
3. **Document the new converter signature**: Phase C requires the converter to accept (or read) the asset_policy block so it knows which assets to inline. The simplest path: pass `meta.yml::asset_policy` into the converter as a CLI flag or via an `--asset-policy` argument that points at the meta.yml. Verify the existing `idml_import_driver.py` flow passes meta-derived data to the converter; if not, add the wiring.
4. **Determinism:** `pack_inline_image` uses `zlib.compress(image_bytes, 6)` per `/workspace/tools/sla_lib/builder/primitives.py:769`. zlib level 6 is deterministic for fixed input bytes and zlib version. Pin `zlib` version awareness — Python's stdlib zlib is deterministic across CPython 3.10+; document this in EXECUTION.md.

---

## 13. preview.pdf byte-equivalence after Phase C is UNLIKELY

**Confidence:** LOW (Scribus rendering behavior; speculative based on user prompt's wording).

**What goes wrong:** ISSUE.md Phase F.3 AC: "preview.pdf diff is byte-identical OR documented." The "OR documented" hedge exists for good reason. Scribus's PDF backend renders inline-base64 PNGs through a different code path than PNG-on-disk references (the inline path uses an in-memory QImage decode; the on-disk path uses Scribus's file-based image loader). Both should produce the same final raster, but:

- ICC profile re-attachment may differ (`PRFILE="sRGB display profile (ICC v2.2)"` is the same in both cases, but the source PNG's embedded ICC might be re-encoded differently).
- PDF compression / image-object ordering can shift even when raster content is identical (PDF object IDs differ).
- Metadata like `/CreationDate` or `/Producer` can shift (but tools/render_pipeline.py canonicalises XMP per line 182-211).

Per `feedback_font_fidelity_check.md` (in CLAUDE.md memory): "When diffing PDFs, run pdffonts on both first. Missing variants in preview = silent fallback = converter bug, not 'engine floor'."

Per `feedback_verify_reference_before_trusting.md`: "Measure any new 'reference'/'canonical' source against actual ground truth FIRST."

**How to avoid (in-scope mitigation):**

1. **Before Phase F runs, capture the CURRENT v2 preview.pdf** (it's stale — built before the migration). Use `cp templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf /tmp/preview-pre-39.pdf`.
2. **Render the post-migration preview** and compare with `tools/visual_diff.py --raster`.
3. **For non-byte-identical results:** document in TOLERANCE_LOG.md a `phase-c-inline-bloat` row with the per-page PPS metric (pixel-similarity-score from `tools/visual_diff.py`). Acceptance threshold: ≥99.5 % per-page (the existing converter convergence target).
4. **Run `pdffonts` on both** preview PDFs to detect font-fallback regression. The migration must not silently change font fallback behaviour.
5. **DO NOT skip the comparison** by re-pinning `previews_for_sla` in meta.yml until both raster + font checks pass. The current `previews_for_sla` SHA is `01a737f648eba48e347a575ed5a35e05867b7ec26cffab66e42d35a52bc794cb` per `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml:14` — that SHA is for the absolute-path-bug SLA, so it's GOING to change.

---

## 14. Skill doc and CONTEXT.md ALREADY disagree — must reconcile in the same PR

**Confidence:** HIGH (textual comparison).

**What goes wrong:** `/workspace/.claude/skills/idml-import/asset_policy.md` lines 88-97 example shows `plakat-dunkel-fuer-flyer.png` AND `green-pine-trees-covered-with-fog.jpg` in `shipped:`. CONTEXT.md says ALL 12 v2 assets go in `embedded:` (lines 67-86). The skill doc must be updated in the same PR to either:

- Reflect the first-PR rule (all embedded, shipped is empty) AS THE CURRENT POLICY, with a "future" section showing the eventual split.
- Be updated to a TRANSITIONAL form with explicit "first-PR" / "after Phases D/E/G" markers throughout.

Without this, future agents/users reading the skill will follow the skill's example, hit the audit rejection, and reach for silent-embed (see pitfall #1).

**How to avoid (in-scope mitigation):**

1. **Update `/workspace/.claude/skills/idml-import/asset_policy.md`** in the same PR. Add a banner at the top:
   ```markdown
   > **Active rule (issue #39, first PR):** all assets go in `embedded:`.
   > The `shipped:` list MUST be empty. The eventual split described below
   > becomes active in a follow-up PR after the brand-team decision.
   ```
2. **Mark every `shipped:` example** with `# eventual; not yet active`.
3. **Re-export the SKILL.md index entry** for P11 to mention the first-PR rule.
4. **Audit `.claude/skills/idml-import/SKILL.md` P11**: if it has a one-line summary, that must also reflect the active rule.
5. **DO NOT delete** the eventual-state example. It's documentation that survives this PR.

---

## 15. The schema is `required: [embedded, shipped]` — empty `shipped: []` is required, not optional

**Confidence:** HIGH (read /workspace/shared/asset-policy.schema.yaml).

**What goes wrong:** `/workspace/shared/asset-policy.schema.yaml:27` declares `required: [embedded, shipped]`. So a meta.yml with ONLY `embedded:` (no `shipped:` key at all) fails schema validation BEFORE the audit's "shipped must be empty" check. Users will write:

```yaml
asset_policy:
  embedded:
    - asset1.png
    - asset2.png
```

…and get a schema error "shipped is required". That's a CONFUSING error message for first-PR users who know `shipped:` is forbidden non-empty.

**How to avoid (in-scope mitigation):**

1. **Update `/workspace/.claude/skills/idml-import/asset_policy.md`** to ALWAYS show `shipped: []` in examples (empty list, present key).
2. **Update the meta.yml example** to include `shipped: []` explicitly.
3. **Defensive: `load_asset_policy()` in `/workspace/tools/sla_lib/builder/meta_schema.py:174` already returns the validated dict.** Verify the jsonschema's `required` is met by `shipped: []` (empty list passes `type: array`, `uniqueItems: true`). It does.
4. **The audit checks `len(policy.get("shipped", [])) == 0`**, not `"shipped" in policy`. Both are equivalent here because schema-required.

---

## Summary of mitigations that MUST land in the first PR

| # | Mitigation | Code/Doc landing point |
|---|------------|----------------------|
| 1 | `_SHIPPED_REJECTED_MSG` const with CONTEXT.md verbatim text | `tools/asset_policy_audit.py` |
| 1 | Skill doc + schema docstring updates for first-PR rule | `.claude/skills/idml-import/asset_policy.md`, `shared/asset-policy.schema.yaml` |
| 2 | SLA size delta recorded in EXECUTION.md + TOLERANCE_LOG | `templates/<v2>/TOLERANCE_LOG.md`, EXECUTION.md |
| 2 | `tools/check_sla_size.py` warn>5MB fail>20MB | new CI tool |
| 3 | Drop converter's absolute-path fallback at lines 2163-2170 of `idml_to_dsl.py` | `tools/idml_to_dsl.py` |
| 3 | Strict converter coupling to `asset_policy` (embed vs shipped vs unclassified) | `tools/idml_to_dsl.py::_emit_image_content` |
| 4 | `reconcile_build_py.py --check` runs as gate before+after Phase C | CI / pre-commit (already wired) |
| 4 | Test: inject.yml line count == `# P5/inject` marker count in build.py | new `tests/test_v2_reimport_preserves_injects.py` |
| 5 | Audit uses fs-walk of `shared/assets/<slug>/` as truth, not links_export.yml strictly | `tools/asset_policy_audit.py` |
| 5 | Composite + per-icon PNG handling: split files audit-OK; composite-OK-as-embedded | tests, audit logic |
| 6 | New `test_v2_falzflyer_geometry.py::test_inline_image_byte_identity` | new test |
| 6 | Run `test_image_frame_coverage.py` after Phase C — should now pass for v2 | CI |
| 7 | Broader regex in `tools/check_no_absolute_paths_in_sla.py` | new tool |
| 7 | Positive-test verifying regex catches all variants | new test |
| 8 | Sequence in EXECUTION.md: converter → audit → reconcile → build → render → lint | docs |
| 9 | Audit also asserts PTYPE=2 ImageFrame has either `PFILE=""` or `isInlineImage="1"` | `tools/check_no_absolute_paths_in_sla.py` (extend) |
| 10 | Four-distinct-error-message audit with `const` strings + tests | `tools/asset_policy_audit.py` + tests |
| 10 | Audit ordering: asset_policy_audit BEFORE asset_extraction_audit | `tools/render_pipeline.py::_run_audit` |
| 11 | Audit skip when no `shared/assets/<slug>/` directory | `tools/asset_policy_audit.py` |
| 12 | Converter reads bytes from disk for embedded assets, calls `pack_inline_image()` | `tools/idml_to_dsl.py::_emit_image_content` |
| 13 | Run `pdffonts` + `tools/visual_diff.py --raster` before declaring Phase F done | EXECUTION.md checklist |
| 14 | Update `asset_policy.md` skill doc with first-PR banner | `.claude/skills/idml-import/asset_policy.md` |
| 15 | Examples always show `shipped: []` (empty list, present key) | docs, examples |

---

## Risks that should be CALLED OUT in PLAN.md but DEFERRED to follow-up PRs

| Item | Why deferred | Track via |
|------|--------------|----------|
| Scribus PFILE cwd-vs-SLA-dir ambiguity at render time | Only matters when `shipped:` becomes non-empty (Phases D/E) | Note in RESEARCH.md only |
| LFS migration for SLA files | Decision pending; current text-tracking works for 8 of 9 templates | Defer if Phase F SLA stays <20MB (which it won't — 18MB is the projected size, very close to the limit) |
| AI watermarking + composite-AI handling for ZIP-shipped assets | Phase G — deferred per CONTEXT.md | Issue #39 follow-up PR |
| Gallery download-link change | Phase E — deferred per CONTEXT.md | Issue #39 follow-up PR |
| Zip-build pipeline | Phase D — deferred per CONTEXT.md | Issue #39 follow-up PR |

---

## Sources

### HIGH confidence (codebase analysis)

- `/workspace/.issues/39-self-contained-template-downloads-brand-embed-content-zip/CONTEXT.md`
- `/workspace/.issues/39-self-contained-template-downloads-brand-embed-content-zip/ISSUE.md`
- `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla`
- `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py`
- `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml`
- `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml`
- `/workspace/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/links_export.yml`
- `/workspace/shared/asset-policy.schema.yaml`
- `/workspace/.claude/skills/idml-import/asset_policy.md`
- `/workspace/tools/idml_to_dsl.py` (lines 2120-2176, 1620-1665, 2163-2170)
- `/workspace/tools/sla_lib/builder/primitives.py:759-858`
- `/workspace/tools/sla_lib/builder/meta_schema.py:174-233`
- `/workspace/tools/reconcile_build_py.py`
- `/workspace/tools/render_pipeline.py:179-210, 662-720`
- `/workspace/tools/visual_diff.py:175-211`
- `/workspace/.pre-commit-config.yaml`
- `/workspace/.gitattributes`
- `/workspace/tools/sla_lib/tests/test_image_frame_coverage.py`
- `/workspace/tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py:230-238`

### MEDIUM confidence (Scribus docs)

- [Scribus wiki — Correcting broken image file paths](https://wiki.scribus.net/canvas/Correcting_broken_image_file_paths)
- [Scribus fileproblems doc](https://fossies.org/linux/scribus/doc/en/fileproblems.html)

### LOW confidence (extrapolated)

- Pitfall #13 (preview.pdf byte-equivalence) — projected from Scribus rendering pipeline knowledge; should be verified empirically during Phase F.
