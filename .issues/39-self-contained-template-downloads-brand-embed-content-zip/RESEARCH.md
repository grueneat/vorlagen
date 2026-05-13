# Research — Issue #39 (brand-embed-only first PR)

**Date:** 2026-05-13
**Scope:** locked by CONTEXT.md to phases A + B + C + F only. No zip (D), no gallery flow (E), no AI watermark (G).
**Confidence:** HIGH on codebase state + inline-embedding mechanics + Scribus path resolution; MEDIUM on derived-asset coverage rule; LOW on cross-template uniformity (other 8 templates may have subtler asset-policy mismatches).

## Summary

Issue #39's first PR fixes one concrete bug and lands the policy enforcement that prevents the bug class:

1. **The bug** — `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla` contains 9 `PFILE` attributes with absolute worktree paths (`/workspace/.worktrees/35-…/shared/assets/…`). On download these paths resolve to nothing. **No other template has this** — the other 8 already use inline embedding.
2. **The fix** — all 9 PFILE entries become `isInlineImage="1"` with `ImageData=` (qCompress base64). The user opens the downloaded SLA standalone and the brand assets render. Content (portrait, photo) slots become EMPTY in the downloaded SLA but the gallery preview still renders them via the on-disk source files (Scribus `chdir`s to SLA directory on openDoc; demo content is referenced via repo-relative paths from there).
3. **The policy** — `templates/<slug>/meta.yml::asset_policy::embedded` is now mandatory for IDML-sourced templates. `shipped:` must be empty (audit-enforced; schema permissive for forward compat per CONTEXT.md). The audit STOPS render-gallery and idml-import on unclassified or wrongly-classified assets with a clear actionable error.

The largest concrete deliverable is the converter change in `tools/idml_to_dsl.py` (three call-sites that emit absolute paths — lines 1635-1664, 2128-2143, 2157-2170 — must instead read `meta.yml::asset_policy` and emit inline OR relative path). All other deliverables are small (audit tool, CI lint, schema-only CI step, v2 migration).

## Recommendation (primary)

**One PR, six tasks in order:**

1. **Land `tools/asset_policy_audit.py`** as a new sibling of `asset_extraction_audit.py`. Hard-fails on (a) `shipped:` non-empty, (b) any asset in `shared/assets/<slug>/` not in `asset_policy::embedded`, (c) any asset in `asset_policy::embedded` not on disk. Reuses `load_asset_policy()` (already validates schema + disjointness). Wired into `_run_audit` BEFORE A1 inventory + `idml_import_driver._process_one` after asset extraction.
2. **Land `tools/check_no_absolute_paths_in_sla.py`** as a pre-commit + SOP-gates CI lint. Walks `templates/*/template.sla` via lxml, fails on any `PFILE` starting with `/`, `file://`, or `[A-Z]:[\\/]`. (Today this fires on v2-falzflyer; task 1 of the audit doesn't fire because v2 has no `asset_policy` block yet.)
3. **Author `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml::asset_policy`** listing all 12 disk assets under `embedded:` and `shipped: []` explicitly. With the audit landed in task 1, this passes the audit but the SLA still has absolute paths — so the next task must land before commit.
4. **Patch `tools/idml_to_dsl.py`** — 3 call-sites. New behavior: read `meta.yml::asset_policy::embedded` via `load_asset_policy()`, store on `_Ctx.embedded_set`. In `_emit_image_content` (and PDF/vector sibling at 1635-1664), if `basename in ctx.embedded_set`, call `pack_inline_image(path.read_bytes(), ext)` and emit `ImageFrame(inline_image_data=…, inline_image_ext=…)`. Else emit relative path. This change is local; the dataclass + qCompress encoder already exist.
5. **Re-emit v2-falzflyer** via `bin/idml-import --reimport`. The new SLA has 9 inline ImageFrames + 0 absolute paths. Run `bin/render-gallery` to regenerate `preview.pdf`/`page-NN.png`; assert byte-identical (or document drift). Run `tools/lint_inject_consistency.py` to verify inject.yml round-trips.
6. **Reconcile `asset_policy.md` skill doc** (currently shows `plakat-dunkel-fuer-flyer.png` in `shipped:` — needs to flip to `embedded:` to match CONTEXT.md's "all 12 in embedded" rule).

## User Constraints (from CONTEXT.md, verbatim-as-applicable)

- **Scope locked**: phases A + B + C + F. No D (zip), no E (gallery), no G (AI watermark).
- **`shipped:` list MUST be empty** in every committed `meta.yml::asset_policy`. The audit REJECTS non-empty with a clear error pointing at the pending team decision.
- **Schema stays permissive** for forward compat; only the audit enforces the transitional rule.
- **All 12 v2-falzflyer assets go to `embedded:`** including the two `green-pine-trees-…` files and `plakat-dunkel-fuer-flyer.png` (the brand team has approved them shipping inline; they are stock / brand-supplied, not AI-generated).
- **Preview generation stays unchanged**: render pipeline keeps using the on-disk source files for `preview.pdf` / `page-NN.png`. The downloaded SLA is what changes.
- **No `tools/build_template_zip.py`, no gallery flip, no AI watermark logic** in this PR.
- **No `claude` in commits/code/files.**

## Codebase Analysis

See [research/codebase.md](research/codebase.md) for full interfaces with line numbers.

### Build matrix

```
<interfaces>

# EXISTING (reuse, don't rewrite):
tools/sla_lib/builder/primitives.py:759-770   # pack_inline_image (qCompress base64 encoder)
tools/sla_lib/builder/primitives.py:773-858   # ImageFrame dataclass — inline_image_data + inline_image_ext fields
tools/sla_lib/builder/meta_schema.py:174-233  # load_asset_policy() — schema + disjointness validated
shared/asset-policy.schema.yaml               # required: [embedded, shipped]; permissive on values
tools/asset_extraction_audit.py               # sibling pattern for the new audit
tools/render_pipeline.py:662-748              # _run_audit, wire new audit AFTER asset_extraction, BEFORE A1
tools/idml_import_driver.py:187-595           # _process_one, wire new audit after line 458
tools/sla_lib/builder/library.py:436-500      # inject_into_frame — reference for inline-image plumbing
.pre-commit-config.yaml                       # 4 existing local hooks, language: system, pass_filenames: false
.github/workflows/ci.yml:59-70                # SOP-gates step — extend with new lint
templates/infostand-tent-card-a5-quer/build.py:91-95  # hand-authored pack_inline_image proof

# NEW (this PR):
tools/asset_policy_audit.py                   # the audit + cross-check
tools/check_no_absolute_paths_in_sla.py       # pre-commit + CI lint
tests/unit/test_asset_policy_audit.py         # unit tests for the audit
tests/unit/test_check_no_absolute_paths.py    # unit tests for the SLA lint
templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml::asset_policy  # the v2 migration

# MODIFIED:
tools/idml_to_dsl.py                          # 3 emit sites + _Ctx.embedded_set
.claude/skills/idml-import/asset_policy.md    # reconcile with CONTEXT.md (plakat goes to embedded:)
.pre-commit-config.yaml                       # +1 hook entry
.github/workflows/ci.yml                      # +1 line in SOP-gates step
templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla  # 9 absolute paths → 9 inline
templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py      # converter-emitted; 9 ImageFrame calls change

</interfaces>
```

### Phase A converter bug sites (corrected from CONTEXT.md's single-site estimate)

Three sites in `tools/idml_to_dsl.py` emit absolute paths via `Path.resolve()`:

- **Line 1635-1664** — PDF/vector emit branch.
- **Line 2128-2143** — `--asset-map` raster emit branch. **This is the actively-firing one on v2-falzflyer.**
- **Line 2157-2170** — legacy `--assets-dir` emit branch. Has a `relative_to(ROOT)` fallback attempt; the others don't.

Phase A patches all three to read `_Ctx.embedded_set` and emit either inline OR relative.

### Phase F asset count reconciliation (corrected from CONTEXT.md's "12 assets")

`shared/assets/kandidat-falzflyer-din-lang-gruenes-cover-v2/` actually has 12 files on disk, BUT only **9 are PFILE'd** in the SLA:

**Referenced in SLA (9, all become inline)**:
- gruene-logo-bund-weiss-cmyk.png
- social-media-icon-{facebook, instagram, tiktok}.png
- bluesky-weiss.png, mail-weiss.png, website-weiss.png
- plakat-dunkel-fuer-flyer.png
- green-pine-trees-covered-with-fog-crop.png

**On disk but NOT referenced by SLA (3)**:
- social-media-icons-weiss.png (the composite — unused per #38 split into per-icon PNGs)
- green-pine-trees-covered-with-fog-srgb.png (derivative; superseded by `-crop.png`)
- green-pine-trees-covered-with-fog.jpg (original; not referenced)

**Audit decision (planner-level call)**: the asset-policy audit walks **`shared/assets/<slug>/` as truth**, not strictly `links_export.yml`. Every disk file must appear in `embedded:` (or be deleted from disk). The 3 unreferenced files appear in `embedded:` for forward compat — when a future template variant references them, the inline-data branch handles them. The SLA has 9 ImageFrames; the policy has 12 entries; the gap is documented as "policy is a superset of in-use".

Alternative: clean up disk and remove the 3 unused files. Defer to follow-up.

### Phase F template-slug vs IDML-stem-slug mismatch

`templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` (template slug) vs
`shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/` (IDML stem slug — derived from the IDML filename).

The new audit must accept BOTH possible asset-dir locations:
1. `shared/assets/<template-slug>/`  (preferred convention)
2. `shared/assets/<idml-stem-slug>/` (current v2-falzflyer state — historical)

`render_pipeline.py:698` already has a dual-lookup pattern; the new audit follows it.

## Standard Stack (verified installed)

| Library | Version | Use |
|---|---|---|
| jsonschema | 4.26.0 | already used by load_asset_policy() |
| PyYAML | 6.0.3 | already used everywhere |
| lxml | 5.4.0 | SLA parse for check_no_absolute_paths |
| Pillow | 12.2.0 (pinned) | not needed for this PR (no image manipulation, just byte passthrough) |

No new dependencies. Don't introduce: anything.

## Don't Hand-Roll

- **qCompress base64 encoding** — use `pack_inline_image(path.read_bytes(), ext)` from `primitives.py:759`. Already round-trips byte-identically.
- **`ImageFrame` inline emission** — already wired in the dataclass (`primitives.py:773-858`); just populate `inline_image_data=` and `inline_image_ext=`.
- **YAML schema validation** — use `load_asset_policy()`; don't re-implement schema loading.
- **Disjoint-list check** — already in `load_asset_policy()`.
- **Pre-commit hook shape** — use `language: system, pass_filenames: false` per the 4 existing hooks.
- **CI step** — extend the existing SOP-gates step, don't add a new job.
- **Test fixtures** — `tempfile.TemporaryDirectory()` + `_meta_path(root=tmp)`; pass `root=` to all loaders.

## Architecture Patterns

### Converter `_Ctx.embedded_set`

New attribute on `_Ctx`:

```python
@dataclass
class _Ctx:
    ...  # existing fields
    embedded_set: set[str] = field(default_factory=set)  # basenames listed in meta.yml::asset_policy::embedded
```

Populated in `idml_to_dsl.convert()` after the existing meta.yml read:

```python
policy = load_asset_policy(template_id, root=ROOT)
if policy is not None:
    ctx.embedded_set = set(policy.get("embedded", []))
```

Read in all 3 emit sites. Pseudocode:

```python
# inside _emit_image_content (around line 2128):
basename = path.name
if basename in ctx.embedded_set:
    inline = pack_inline_image(path.read_bytes(), ext=path.suffix.lstrip("."))
    kwargs["inline_image_data"] = inline.data
    kwargs["inline_image_ext"] = inline.ext
else:
    # FALLBACK for first PR: should never happen because shipped: is empty
    # and audit catches unclassified. Keep the relative-path emit for
    # forward compat (Phase D/E/G will populate this branch).
    rel = path.relative_to(ROOT)
    kwargs["src"] = f"../../{rel}"  # SLA-relative; templates/<slug>/template.sla → ../../shared/assets/...
```

### `tools/asset_policy_audit.py` outline

```python
"""Audit meta.yml::asset_policy against shared/assets/<slug>/.

Hard-fail conditions:
1. meta.yml::asset_policy is absent (when shared/assets/<slug>/ exists)
2. shipped: list is non-empty
3. asset in shared/assets/<slug>/ not in embedded: list (unclassified)
4. asset in embedded: list not on disk (stale reference)

Opt-out: when shared/assets/<slug>/ does not exist (8 of 9 templates today),
silent-skip with a one-line "no asset directory, skipping" note.
"""

def run_asset_policy_audit(template_slug: str, root: Path) -> dict:
    asset_dir = _find_asset_dir(template_slug, root)
    if asset_dir is None:
        return {"ok": True, "skipped": True, "reason": "no asset directory"}
    policy = load_asset_policy(template_slug, root)
    if policy is None:
        return {"ok": False, "issue": "missing", "message": "..."}
    if policy.get("shipped"):
        return {"ok": False, "issue": "shipped_non_empty", "shipped": policy["shipped"]}
    on_disk = {p.name for p in asset_dir.iterdir() if p.is_file() and p.suffix != ".yml"}
    embedded = set(policy["embedded"])
    unclassified = on_disk - embedded
    stale = embedded - on_disk
    if unclassified or stale:
        return {"ok": False, "issue": "coverage", "unclassified": sorted(unclassified), "stale": sorted(stale)}
    return {"ok": True}
```

Output `build/validation/<slug>/asset_policy_audit.yml`. Wired into `_run_audit` AFTER asset_extraction (line 748+), BEFORE A1 inventory.

### `tools/check_no_absolute_paths_in_sla.py` outline

```python
"""Pre-commit + CI lint. Walks templates/*/template.sla via lxml.
Fails on any PFILE starting with /, file://, or [A-Z]:[\\/].
"""

ABSOLUTE_PFILE_RE = re.compile(r'^(?:/|file://|[A-Za-z]:[\\/])')

def main():
    root = Path(__file__).resolve().parents[1]
    failures = []
    for sla in root.glob("templates/*/template.sla"):
        tree = etree.parse(str(sla))
        for el in tree.iterfind(".//PAGEOBJECT[@PFILE]"):
            pf = el.get("PFILE", "")
            if pf and ABSOLUTE_PFILE_RE.match(pf):
                failures.append((sla, el.sourceline, pf))
    if failures:
        for sla, line, pf in failures:
            print(f"{sla}:{line}: absolute PFILE: {pf}")
        return 1
    return 0
```

CI: add `python3 tools/check_no_absolute_paths_in_sla.py` to the SOP-gates step in `.github/workflows/ci.yml` (no new step, no new job).

Pre-commit: append to `.pre-commit-config.yaml`:

```yaml
- id: check-no-absolute-paths-in-sla
  name: Check no absolute filesystem paths in template.sla files
  entry: python3 tools/check_no_absolute_paths_in_sla.py
  language: system
  pass_filenames: false
```

## Common Pitfalls (from research/pitfalls.md)

See [research/pitfalls.md](research/pitfalls.md) for full catalogue. Top items:

1. **SLA size blowup**: v2 SLA goes from 58 KB to ~18 MB. `plakat-dunkel-fuer-flyer.png` (8.5 MB) + `green-pine-trees-covered-with-fog-crop.png` (4.6 MB) drive ~95% of it. Git tracks SLAs as text (`.gitattributes: text eol=lf`), not LFS — pack/diff cost is real but accepted per CONTEXT.md.
2. **No composite-AI 4x bloat**: build.py already references per-icon PNGs (per #38). The composite `social-media-icons-weiss.png` is on disk but not referenced; goes into `embedded:` for forward compat but doesn't emit a 4x-duplicated ImageData blob.
3. **CONTEXT.md's path-resolution claim was wrong**: Scribus auto-`chdir`s to the SLA's parent on `openDoc()`, not repo root. For first PR (everything inline, `PFILE=""`), this is moot. Document for Phase D/E follow-up.
4. **`asset_policy.md` skill doc disagreement**: currently shows `plakat-dunkel-fuer-flyer.png` in `shipped:`. Flip to `embedded:` in the same PR.
5. **Schema requires `shipped: []` explicitly** (it's a `required` key). Users adding only `embedded:` get a schema error before the audit fires. Document the empty-list requirement in every example.
6. **No tests reference `PFILE=`** in the repo today. `test_image_frame_coverage.py` requires `inline_image_data` and currently implicitly skips v2. Phase C *fixes* a latent test expectation; no test updates needed in this PR.
7. **`reconcile_build_py.py --check` is a pre-commit hook** (shipped in #79). Phase F's re-emit must run reconcile to preserve inject.yml hand-patches.
8. **Cross-cutting AC softening**: "all 9 templates pass the audit" → "all templates with `shared/assets/<slug>/` pass; others silent-skip". Only v2 has an asset dir today.
9. **Audit walks `shared/assets/<slug>/` as truth, not `links_export.yml`** (which only lists IDML-converter Phase-2 outputs, missing the 3 derived files).

## Environment Availability

- **CI** (`.github/workflows/ci.yml`): cheap, no Scribus. New checks fit here (schema validation, grep lint). Full asset_policy_audit (with shared/assets cross-check) needs the assets directory which is in the repo — runs fine in CI.
- **Dev container**: full pipeline including `bin/render-gallery`. Phase F testing happens here.
- **Pre-commit hooks**: existing 4 hooks already in `.pre-commit-config.yaml`; +1 for absolute-paths.

## Project Constraints

- No `CLAUDE.md` repo-wide.
- `.issues/config.yaml`: opus research/plan, sonnet execute; branch `issue/{slug}`.
- Commit format: `39: <type>(<scope>): <subject>`.
- No "claude" in commits/code/files.
- No emoji unless asked.
- Pillow 12.2.0 pinned; SimpleIDML 1.3.1 pinned.

## Sources

| Source | Confidence | Notes |
|---|---|---|
| `tools/idml_to_dsl.py:1635-1664, 2128-2143, 2157-2170` | HIGH | Three converter emit sites |
| `tools/sla_lib/builder/primitives.py:759-770, 773-858` | HIGH | pack_inline_image + ImageFrame plumbing |
| `tools/sla_lib/builder/meta_schema.py:174-233` | HIGH | load_asset_policy validation + disjointness |
| `tools/asset_extraction_audit.py` | HIGH | sibling pattern for new audit |
| `tools/visual_diff.py:179-210` | HIGH | confirms Scribus chdir-to-SLA-dir on openDoc |
| `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla` grep | HIGH | 9 absolute PFILE entries |
| Scribus wiki on PFILE | HIGH | https://wiki.scribus.net/canvas/Correcting_broken_image_file_paths |
| `shared/asset-policy.schema.yaml` | HIGH | required: [embedded, shipped] |
| `templates/infostand-tent-card-a5-quer/build.py:91-95` | HIGH | hand-authored pack_inline_image proof |

## Open Questions for the Planner

1. **Audit truth source**: `shared/assets/<slug>/` (recommended per pitfalls research) vs `links_export.yml`. Recommendation: disk as truth; document the 3 unreferenced files as forward-compat entries.
2. **3 unused v2 assets**: keep on disk (and in `embedded:`) for forward compat, OR delete from disk? Recommendation: keep + document. Cleanup is a separate, smaller PR.
3. **Schema-root for `load_asset_policy()`**: today hardcoded to repo root. Worth a `schema_root` parameter for cleaner test isolation? Recommendation: defer; current tests work via `_meta_path(root=)` + real schema.
4. **Asset-dir slug convention going forward**: template slug vs IDML stem slug. The audit handles both (per `render_pipeline.py:698` pattern). New IDML imports use template slug. v2's mismatch is historical.
5. **Cross-cutting AC**: "all 9 templates pass" — 8 of 9 lack `shared/assets/<slug>/`. Soften to "all templates with asset dirs pass; others silent-skip" per pitfalls research.

## Cross-references

- Issue #38 (PR #79) — `bin/idml-import` + `asset_extraction_audit.py` + SKILL.md scaffold.
- Issue #38 follow-up (PR #82) — P11 added to SKILL.md; `asset_policy.md` policy doc; `load_asset_policy()` loader.
- Pitfalls research: `research/pitfalls.md` (size blowup, schema-required-shipped, skill-doc disagreement, latent test expectation).
- Ecosystem research: `research/ecosystem.md` (qCompress format, Scribus path resolution, jsonschema vs audit enforcement).
- Codebase research: `research/codebase.md` (3 converter sites + audit wire points + asset count reconciliation).
- Memory: `feedback_fix_generator_not_artifact.md` (Phase A patches the converter, not the SLA directly).
- Memory: `feedback_no_claude_attribution.md` (commit hygiene).
