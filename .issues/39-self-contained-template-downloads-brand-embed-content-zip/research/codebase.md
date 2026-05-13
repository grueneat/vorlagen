# Codebase research — issue #39 (brand-embed-only first PR)

**Scope reminder.** Per CONTEXT.md, the first PR for issue #39 implements
Phases **A + B + C + F** only. Phase D (zip), Phase E (gallery), and
Phase G (AI watermark) are deferred. The committed `asset_policy::shipped`
list MUST be empty in every template; every asset goes into `embedded:`.
The schema still accepts the `shipped` key for forward compatibility,
but the audit REJECTS non-empty values.

This document is the codebase findings only. Ecosystem and pitfalls
research live in sibling files.

All paths in this document are absolute and rooted at `/workspace/`.

---

## 1. What's already on `main` (from PR #82 + earlier)

### 1.1 Policy doc + schema + loader

| Artifact | Path | LOC | Status |
|----------|------|----:|--------|
| Skill principle P11 | `/workspace/.claude/skills/idml-import/SKILL.md` (lines 210–215) | (~7) | landed |
| Policy rationale | `/workspace/.claude/skills/idml-import/asset_policy.md` | 178 | landed |
| JSON-Schema | `/workspace/shared/asset-policy.schema.yaml` | 46 | landed |
| Loader + disjointness | `/workspace/tools/sla_lib/builder/meta_schema.py::load_asset_policy` | 60 | landed |

The schema requires BOTH `embedded` and `shipped` keys at the top level
(see schema line 25: `required: [embedded, shipped]`). Each is a list
of strings (`uniqueItems: true`). Disjointness is enforced *outside*
JSON-Schema, inside `load_asset_policy()` (lines 224–232) — fires
`ValueError` with a clear message that points at
`asset_policy.md`.

The loader also lazy-loads the schema from disk (line 213–215) — no
import-time penalty. **Per-asset cross-check** (every entry in
`links_export.yml` ⇔ one of the two buckets) is intentionally NOT in
the loader — its docstring (lines 192–193) points at the to-be-built
`tools/asset_policy_audit.py`.

### 1.2 Inline-embedding primitive (already there, used by hand-authored templates)

`/workspace/tools/sla_lib/builder/primitives.py::pack_inline_image` (lines 759–770):

```python
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).

    Scribus's inline ImageData attribute is qCompress-encoded:
    base64( 4-byte big-endian uncompressed-length prefix + zlib_compress(image_bytes) ).
    Naive base64 of raw bytes makes Scribus abort with qUncompress: Z_DATA_ERROR.

    Returns (qcompressed_b64, ext) — pass to ImageFrame as
    inline_image_data=..., inline_image_ext=ext.
    """
```

`ImageFrame` dataclass (primitives.py lines 773–858) accepts
`inline_image_data` + `inline_image_ext`. When `inline_image_data is
not None` the emitted PAGEOBJECT carries:

- `PFILE=""` (empty)
- `Pagenumber="0"`
- `isInlineImage="1"`
- `inlineImageExt="png"` (or `jpg`)
- `ImageData="<the qCompress b64 blob>"`
- `EMBEDDED="0"`

This is the format Scribus 1.6 reads and `tools/sla_to_dsl.py::_capture_inline_image`
(lines 203–216) round-trips verbatim.

**Proof it works today:** `templates/infostand-tent-card-a5-quer/build.py`
(lines 91–95, 122–142) hand-authors `_logo_inline()` which calls
`pack_inline_image(LOGO_GRUENE_WEISS.read_bytes(), "png")` and passes
`inline_image_data=logo_data, inline_image_ext=logo_ext` to
`ImageFrame()`. The resulting `template.sla` has 6 PAGEOBJECTs with
`isInlineImage="1"` and `PFILE=""` (confirmed by inspection — no
absolute paths in that template).

The Phase C IDML converter rewrite emits the same shape, but driven by
`meta.yml::asset_policy::embedded`.

### 1.3 Asset-extraction audit (Phase E in #38; the wrong-named "Phase E")

| Artifact | Path | LOC |
|----------|------|----:|
| Audit module | `/workspace/tools/asset_extraction_audit.py` | 442 |
| `_run_audit` integration | `/workspace/tools/render_pipeline.py` lines 693–748 | — |
| Unit tests | `/workspace/tests/unit/test_asset_extraction_audit.py` | 200+ |
| Integration tests | `/workspace/tests/integration/test_asset_audit_wired_into_run_audit.py` | — |

What it does today (lines 236–359):

- Walks an IDML for every `<Link LinkResourceURI=…>`.
- Asserts each link basename is present in the sibling `Links/`
  directory.
- Asserts each link basename has a matching entry in
  `links_export.yml::assets`.
- Composite-AI detection (page_count > 1, aspect_ratio > 3.0, distinct
  ItemTransform offsets ≥ 2).
- Writes `build/validation/<slug>/asset_audit.yml`.

What it does NOT do today (and is the gap Phase B needs to close):

- Does NOT read `meta.yml::asset_policy`.
- Does NOT cross-check that the union of `embedded ∪ shipped` covers
  every entry in `links_export.yml::assets`.
- Does NOT check `shipped:` is empty (the first-PR rule).
- Does NOT fire if `meta.yml::asset_policy` is missing.

`_run_audit` (render_pipeline.py line 662) is the orchestration point.
The current order (top-down through that function):

1. Asset-extraction audit (lines 693–748).
2. A1 inventory (lines 750–769).
3. A2 baseline text audit (lines 771–792).
4. A3 baseline image audit (lines 794–817).
5. D6 font audit, D7 text-render audit, D8 text-position audit, etc.

The issue spec says Phase B's `asset_policy_audit` must run BEFORE A1
(line 110). The new audit slots in immediately AFTER the existing
`asset_extraction_audit` block (after line 748, before line 750) so
`asset_policy` is checked once `links_export.yml` has been validated.

### 1.4 IDML import driver (`bin/idml-import`)

| Artifact | Path | LOC |
|----------|------|----:|
| Shim | `/workspace/bin/idml-import` | 13 |
| Driver | `/workspace/tools/idml_import_driver.py` | 708 |

Pipeline (driver `_process_one`, lines 374–595):

1. Tool availability (`shutil.which scribus/pdftocairo/...`) — line 395.
2. Slug derive — line 402.
3. Existing-template detection (refuse without `--reimport`) — line 406.
4. Brand-fonts gate — line 415.
5. Baseline.pdf resolution — line 431.
6. Asset extraction (`links_export.export(...)`) — line 446.
7. **Asset-extraction audit** (`asset_extraction_audit.audit(...)`) — line 458.
   Hard-fails on `not report["ok"]` (line 466).
8. Scaffold (`_scaffold_template_dir`) — line 476. Currently writes a
   bare `meta.yml` with `{id, version, title, format, build}` (lines
   194–204) — no `asset_policy:` block.
9. Convert (`_run_converter` → `tools/idml_to_dsl.py`) — line 480.
10. Convergence loop or `--scaffold-only` halt — lines 492–595.

Phase B wants the audit to STOP and ask the user before writing
`meta.yml::asset_policy`. **Two integration points** open up:

- **Step 7.5 (new):** After `asset_extraction_audit` passes, run
  `asset_policy_audit` on the *target* `meta.yml`. If it's absent or
  incomplete, refuse to scaffold; print a heuristic-guessed split and
  exit non-zero with instructions for the user to add the section.
- **Step 8 (modify):** `_scaffold_template_dir` (line 187) gains an
  `asset_policy` block populated from the heuristic guess, but
  **commented out** — the user must uncomment after review. This is
  the lightest-touch option; the alternative ("prompt interactively")
  doesn't fit the existing `--non-interactive` CLI mode (line 681) and
  forces a TTY assumption that breaks CI.

Recommendation for Phase B prompt UX: **hard-fail with a clear "add
this block to meta.yml" message** rather than implementing
interactive input. The driver already has `--non-interactive` as the
de-facto CI mode (test_idml_import_v2_falzflyer.py line 69 sets it),
and the existing flow exits non-zero with stderr instructions when an
upstream audit fails (e.g. line 467–473 for missing assets). A
follow-up issue can add interactive scaffold-helper UX without
blocking #39.

### 1.5 Converter — where the absolute-path bug lives

| File | Lines | Notes |
|------|-------|-------|
| `/workspace/tools/idml_to_dsl.py` | 3357 total | Phase A2/A3 fixes here |
| `_emit_image_content` | 2071–2176 | the raster image emission site |
| `_emit_pageitem` PDF branch | 1620–1665 | the vector-logo (`<PDF>`) emission site |
| `_emit_image_frame_call` | 2002–2065 | builds the `kwargs` dict for `ImageFrame(...)` |
| `_Ctx` dataclass | 677–716 | converter shared state (no `asset_policy` field yet) |
| `convert()` | 3081–3224 | top-level pipeline; CLI loads asset_map, calls `_emit_pages` |

**The bug, exact lines.** Two sites resolve to absolute paths:

`/workspace/tools/idml_to_dsl.py` line 2128–2143 (asset-map path; this
is the one that fires for v2-falzflyer):

```python
# 1. Asset-map lookup (Phase 2 path).
if ctx.asset_map:
    mapped = ctx.asset_map.get(basename)
    if mapped:
        # Resolve relative asset_map paths to absolute so Scribus finds
        # the file regardless of the working directory at render time.
        abs_mapped = str(Path(mapped).resolve()) if not Path(mapped).is_absolute() else mapped
        _emit_image_frame_call(
            ctx.out, x_mm, y_mm, w_mm, h_mm, rot,
            self_id, layer_idx, image_path=abs_mapped, ctx=ctx,
            local_scale=local_scale, local_offset_pt=local_offset_pt,
        )
        return
```

`/workspace/tools/idml_to_dsl.py` line 2157–2170 (legacy `--assets-dir`
fallback; not used for v2-falzflyer but still emits absolute paths):

```python
asset_path = ctx.assets_dir / basename
if not asset_path.exists():
    ctx.missing_assets.append(str(asset_path))
    return
# Absolute path so Scribus resolves the file at render time regardless of cwd.
emit_path = str(asset_path.resolve())
try:
    # Also try repo-relative for human readability in the emitted source.
    rel_path = asset_path.resolve().relative_to(ROOT)
    emit_path = str(rel_path).replace("\\", "/")
except ValueError:
    # Asset is outside the repo root; fall back to absolute path string.
    emit_path = str(asset_path.resolve())
```

`/workspace/tools/idml_to_dsl.py` line 1635–1664 (PDF/vector logo
branch — same pattern, also emits absolute paths):

```python
if mapped:
    # Resolve relative asset_map paths to absolute.
    abs_mapped = (
        str(Path(mapped).resolve())
        if not Path(mapped).is_absolute()
        else mapped
    )
    ...
    _emit_image_frame_call(
        out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
        image_path=abs_mapped, ctx=ctx,
        local_scale=pdf_local_scale, local_offset_pt=pdf_local_offset,
    )
```

**ROOT constant.** `idml_to_dsl.py` line 125 defines
`ROOT = _THIS.parent.parent` where `_THIS = Path(__file__).resolve()`.
ROOT is always `/workspace/` regardless of worktree (it resolves
through symlinks).

**Path resolution for `image=` in build.py.** The emitted build.py
generates an `ImageFrame(image='<path>', …)`. Inside `primitives.py`
line 811: `pfile = "" if is_inline else (self.image or self.src)`. The
value is written verbatim into PFILE. Scribus then reads PFILE
relative to the SLA file's directory (see §2.4 below).

### 1.6 The v2-falzflyer template (the proof case)

`/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/`:

| File | Notes |
|------|-------|
| `template.sla` | 9 PAGEOBJECTs with `PFILE="/workspace/.worktrees/35-…/shared/assets/26-03-leporello-…/<name>.png"` — all 9 absolute |
| `build.py` | 9 `ImageFrame(image='/workspace/…/<name>.png', …)` calls — 9 absolute path literals |
| `meta.yml` | NO `asset_policy:` block today |
| `baseline.pdf` | InDesign-authored convergence target; do not touch |
| `inject.yml` | 6 entries for Patterns 1/3/7 etc. — unaffected by issue #39 |
| `diff.yml` | render-pipeline config; unaffected |
| `preview.pdf`, `page-01*.png`, `page-02*.png` | Re-generated by render-gallery |
| `TOLERANCE_LOG.md` | brand_overrides growth log; unaffected |

Confirmed via `grep -c "PFILE=" template.sla`: **9 PFILE entries**, **all
9 absolute**. Of 8 other committed templates, ZERO have absolute paths
(checked all `/workspace/templates/*/template.sla`).

The 9 PFILE basenames (sorted):

1. `bluesky-weiss.png`
2. `green-pine-trees-covered-with-fog-crop.png`
3. `gruene-logo-bund-weiss-cmyk.png`
4. `mail-weiss.png`
5. `plakat-dunkel-fuer-flyer.png`
6. `social-media-icon-facebook.png`
7. `social-media-icon-instagram.png`
8. `social-media-icon-tiktok.png`
9. `website-weiss.png`

### 1.7 v2-falzflyer's shared-asset directory

`/workspace/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/`
(note: directory name is the *IDML stem slug*, NOT the template slug):

| File | Bytes | Notes |
|------|------:|-------|
| `bluesky-weiss.png` | 29 217 | brand |
| `green-pine-trees-covered-with-fog-crop.png` | 4 608 235 | brand (decorative crop, used on page 2) |
| `green-pine-trees-covered-with-fog-srgb.png` | 6 985 953 | content (not PFILE'd today) |
| `green-pine-trees-covered-with-fog.jpg` | 6 896 771 | content (not PFILE'd today) |
| `gruene-logo-bund-weiss-cmyk.png` | 49 604 | brand |
| `links_export.yml` | 1 655 | manifest |
| `mail-weiss.png` | 25 524 | brand |
| `plakat-dunkel-fuer-flyer.png` | 8 558 653 | content (placeholder portrait) |
| `social-media-icon-facebook.png` | 28 688 | brand |
| `social-media-icon-instagram.png` | 48 436 | brand |
| `social-media-icon-tiktok.png` | 37 070 | brand |
| `social-media-icons-weiss.png` | 116 981 | composite reference (not PFILE'd today; kept for `composite_ai_split` provenance) |
| `website-weiss.png` | 40 426 | brand |

**12 PNG/JPG files** — matches the CONTEXT.md "all 12 assets" list. Total
**~27.4 MB** of pixel data. The "every asset → inline" rule under
CONTEXT.md balloons the SLA file from ~430 KB to ~37 MB (qCompress
adds a small base64 + zlib overhead; expect ~30–40 MB total). See
ecosystem research for whether Scribus handles a 30-40 MB SLA without
issues.

**Naming-slug mismatch alert.** Template slug is
`kandidat-falzflyer-din-lang-gruenes-cover-v2` but the asset directory
is `26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2` (the IDML
filename slug). The converter resolves this via the
`links_export.yml::assets[<basename>].output` field, which is
`shared/assets/26-03-leporello-…/<file>` (repo-relative). The
`asset_policy::embedded` list is by *basename* (not full path), so
the mismatch doesn't affect Phase B. But the audit must look up
`links_export.yml` at the IDML's slug path, not the template's slug
path. `render_pipeline.py` line 699 already searches
`shared/assets/<template_id>/links_export.yml` first, then falls back
to `idml_source.parent / "links_export.yml"` — the second path won't
find anything because the IDML lives in `originals/` not `shared/`.
The asset-policy audit needs the same dual-lookup OR a one-time
relocate of the assets to the template-slug dir; recommend keeping the
dual-lookup pattern to avoid touching all the existing references.

### 1.8 v2-falzflyer's links_export.yml

`/workspace/shared/assets/26-03-leporello-…/links_export.yml` has only
**7 entries** (the original IDML-linked basenames before extension
remap):

- `BlueSky weiss.ai` → `bluesky-weiss.png`
- `Grüne Logo Bund weiss CMYK.ai` → `gruene-logo-bund-weiss-cmyk.png`
- `Mail weiss.ai` → `mail-weiss.png`
- `Plakat dunkel für Flyer.psd` → `plakat-dunkel-fuer-flyer.png`
- `Social Media Icons weiss.ai` → `social-media-icons-weiss.png`
- `Website weiss.ai` → `website-weiss.png`
- `green-pine-trees-covered-with-fog.jpg` → `…/green-pine-trees-…jpg`

5 files in the directory are NOT in this manifest:
`social-media-icon-{facebook,instagram,tiktok}.png`, `bluesky-weiss.png`
(wait — that IS in the manifest), and `green-pine-trees-…crop.png`,
`-srgb.png`. The 3 social-media-icons (FB/IG/TT) and the
`bluesky-weiss.png` come from a different source (the `composite_ai_split`
tool emits per-icon PDFs/PNGs from `Social Media Icons weiss.ai`).

**Implication for Phase B's coverage check.** "Every asset in
`links_export.yml` appears in exactly one of `embedded`/`shipped`" is
the wrong invariant under the current asset model. The right
invariant is "every basename that appears as PFILE in `template.sla`
(post-emit) must be in `asset_policy::embedded` (first PR) OR
`shipped:` (future PRs)". A cleaner phrasing for the audit:
**iterate `meta.yml::asset_policy::embedded ∪ shipped` and assert
each basename exists on disk under
`shared/assets/<template-id-or-idml-slug>/<basename>`**. Then
separately assert "no PFILE in `template.sla` references a basename
outside `asset_policy`" (a post-emit check, after Phase C lands).
This phrases the invariant in terms the user can act on without
needing to know the composite_ai_split machinery.

### 1.9 Other 8 templates and their asset patterns

Quick scan of `templates/*/template.sla`:

| Template | PFILE count | Absolute paths | Notes |
|----------|------------:|---------------:|-------|
| `infostand-tent-card-a5-quer` | 6 | 0 | All inline (`isInlineImage="1"`) — hand-authored |
| `kandidat-falzflyer-din-lang` (v1) | 8 | 0 | (existing template — patterns TBD) |
| `kandidat-falzflyer-din-lang-gruenes-cover-v2` | **9** | **9** | the bug |
| `plakat-a1-hochformat` | 3 | 0 | |
| `postkarte-a6-kampagne` | 8 | 0 | |
| `themen-plakat-a3-quer` | 3 | 0 | |
| `wahlaufruf-postkarte-a6-quer` | 4 | 0 | |
| `wahltag-tueranhaenger` | 5 | 0 | |
| `zeitung-a4-grun` | 21 | 0 | |

**Only v2-falzflyer is affected by Phase A's path bug.** The other 8
templates either inline assets already (infostand) or reference
something that round-trips clean through `sla_to_dsl`. **Phase F's
re-emit + byte-identity test must therefore focus on v2-falzflyer
only**; the 8 other templates should be exempt from the cross-cutting
"every template needs an `asset_policy:` block" requirement at this
stage. (CONTEXT.md doesn't insist on retrofitting them.)

The cross-cutting AC `[ ]` "All 9 existing templates pass the new
audit" in ISSUE.md needs softening: it specifies an
`--asset-policy-skip` opt-out for non-IDML-sourced templates. The
planner should encode this opt-out as either (a) the audit treats
`meta.yml` without an `asset_policy:` block as a soft-skip when there
is no companion `links_export.yml`, OR (b) a per-template
`asset_policy_skip: true` opt-in. The CONTEXT.md is silent on this;
default recommendation is (a) — skip silently when no
`links_export.yml` exists, fail loudly when one does. (a) requires
zero changes to existing templates.

### 1.10 Test infrastructure

| Suite | Path | Pattern |
|-------|------|---------|
| Unit — asset audit | `/workspace/tests/unit/test_asset_extraction_audit.py` | In-memory IDML via `_make_idml(tmp_path, spread_xml)` using `io.BytesIO` + `zipfile.ZipFile`. ~30 fixtures. Drop-in template for `test_asset_policy_audit.py`. |
| Unit — meta_schema | `/workspace/tests/unit/test_idml_*.py` (various) | Pytest tmp_path; writes a `meta.yml` to a fake template dir. |
| Integration — v2 driver | `/workspace/tests/integration/test_idml_import_v2_falzflyer.py` | Subprocess-spawns `bin/idml-import`; skips when `originals/` absent. Asserts artifact existence + exit codes. |
| Integration — render | `/workspace/tests/integration/test_render_pipeline_e2e.py`, `test_v2_falzflyer_build_byte_identity.py` | byte-identity tests for re-emission |
| Integration — converter | `/workspace/tests/integration/test_idml_to_dsl_smoke.py` | Runs `idml_to_dsl.py` against the v2-falzflyer IDML when `originals/` is symlinked. |

**Recommended test additions for issue #39:**

- `tests/unit/test_asset_policy_audit.py`: in-memory tmp_path with a
  fake `meta.yml` + `links_export.yml`; assert each invariant fires the
  right error. Pattern: copy `test_asset_extraction_audit.py` and adapt.
- `tests/unit/test_idml_to_dsl_relative_path.py` OR extend an existing
  pattern test: in-memory IDML with one `<Link>`; assert emitted
  build.py contains `image='shared/assets/<slug>/<basename>'` and NEVER
  contains `/workspace/`.
- `tests/integration/test_idml_to_dsl_inline_emission.py`: with a
  `meta.yml::asset_policy::embedded=[<basename>]`, assert emitted SLA
  has `isInlineImage="1"` + `PFILE=""` for that frame; with the same
  basename in `shipped` (forward-compat), assert relative path
  (deferred until Phase D — for the first PR, expect a hard-error
  message about non-empty `shipped:`).
- `tests/integration/test_v2_falzflyer_inline_round_trip.py`:
  re-emit v2-falzflyer + assert 12 `isInlineImage="1"` PAGEOBJECTs
  (per CONTEXT.md "every asset → inline"), 0 absolute paths, no
  references to `shared/assets/...` in PFILE.

### 1.11 CI + pre-commit

| File | Path | Role for issue #39 |
|------|------|--------------------|
| Pre-commit | `/workspace/.pre-commit-config.yaml` | Add `tools/check_no_absolute_paths_in_sla.py` hook |
| Workflow | `/workspace/.github/workflows/ci.yml` (lines 59–70) | Add the same script to the "SOP gates" step |

The pre-commit config (lines 11–28) uses a uniform "system-language,
`pass_filenames=false`" pattern for every existing SOP hook. The new
`check_no_absolute_paths_in_sla.py` follows the same shape:

```yaml
- id: check-no-absolute-paths-in-sla
  name: Reject absolute filesystem paths in committed template.sla files
  entry: python3 tools/check_no_absolute_paths_in_sla.py
  language: system
  pass_filenames: false
```

The CI workflow's "SOP gates" step (ci.yml lines 59–70) runs all four
existing SOP linters via `set -e`. The new check slots in as the 5th
line:

```yaml
python3 tools/check_no_absolute_paths_in_sla.py
```

### 1.12 The `check_no_absolute_paths_in_sla.py` shape

Doesn't exist yet — confirmed via `grep -r check_no_absolute_paths`
returning only ISSUE.md references. Minimal shape (per other SOP
linters in `/workspace/tools/sop_lint.py`, `check_overrides_growth.py`,
`lint_inject_consistency.py`):

```python
#!/usr/bin/env python3
"""Grep-ban absolute paths in committed template.sla files (issue #39 Phase A).

Walks templates/*/template.sla and asserts no PFILE attribute begins with
/workspace/, /home/, /root/, /tmp/, /var/, or /private/var/ (macOS).
Exits 1 on any match; prints the offending file + line for human
remediation.
"""
```

The patterns to grep are conventional UNIX/macOS absolute-path
prefixes; the issue spec mentions `/workspace/`, `/home/`, `/root/`,
`/tmp/`. Recommend adding `/private/var/` (macOS temporary dirs) and
`/Users/` (macOS home) for robustness — these are common when an
authoring user re-emits from a non-container environment.

---

## 2. Open questions resolved by reading the code

### 2.1 Does Scribus accept a 30-40 MB SLA?

Not directly answered by codebase; ecosystem researcher will check.
Existing inlined templates (`infostand-tent-card-a5-quer`,
`postkarte-a6-kampagne`) inline ~50-100 KB logos — far smaller than
the 8.6 MB `plakat-dunkel-fuer-flyer.png` alone. Worth probing for the
upper bound. (Note: Scribus internally decompresses qCompress into a
QPixmap. Memory pressure during render is the realistic concern, not
file size.)

### 2.2 Does the converter handle "every asset → inline" mode today?

Partially. `_emit_image_content` (line 2071) has two branches:
asset-map and legacy `--assets-dir`. Neither currently calls
`pack_inline_image`. **Phase C needs a third branch:** when
`meta.yml::asset_policy::embedded` contains the basename, read the
file bytes from disk and emit:

```python
ImageFrame(
    x_mm=…, y_mm=…, w_mm=…, h_mm=…,
    inline_image_data=<qCompress-b64>,
    inline_image_ext=<png|jpg>,
    …
)
```

Under the first-PR rule (`shipped:` empty, every asset → embedded),
this branch fires for every `<Image>` and `<PDF>`. The other branches
(asset-map / legacy) become unreachable for IDML-imports where
`asset_policy` is present. **They MUST stay** for backward-compat
with existing templates that have no `asset_policy:` block — those
keep their current behavior (relative repo-paths under Phase A's
fix).

### 2.3 Where does the converter learn the asset_policy?

Today, `idml_to_dsl.py` doesn't know about `meta.yml`. The `convert()`
signature (line 3081) takes `(source, output, template_id, assets_dir,
…)` but never reads `templates/<template_id>/meta.yml`. **Phase C
needs to add a `meta.yml` read** — either in `convert()` itself
(simplest) or in `_emit_image_content` (lazier but uglier). Cleanest:

- `convert()` reads `meta.yml::asset_policy` at start, stores
  `embedded_set: set[str]` and `shipped_set: set[str]` on `_Ctx`.
- `_emit_image_content` checks `basename in ctx.embedded_set` → inline
  emit; `basename in ctx.shipped_set` → relative emit (deferred, raises
  in first PR); else → existing asset-map / legacy paths.

The `_Ctx` dataclass (lines 677–716) already has `asset_map:
dict[str, str]` so the pattern is established.

### 2.4 Scribus PFILE relative-path resolution rule

`/workspace/tools/visual_diff.py::render_sla_to_pdf` lines 179–210 has
the canonical comment:

> Scribus on Ubuntu CI exits 0 without writing the PDF if the output
> path is relative (it changes cwd internally on openDoc), so we
> resolve to absolute paths and assert the output exists afterwards.

**Scribus changes its working directory to the SLA file's parent dir
on `openDoc()`.** Therefore, a PFILE like `shared/assets/<slug>/foo.png`
inside `templates/<slug>/template.sla` resolves to
`templates/<slug>/shared/assets/<slug>/foo.png` — which doesn't exist.

**Critical correction to CONTEXT.md.** CONTEXT.md lines 110–117 say:

> The preview pipeline `cd`s into `templates/<slug>/` and runs Scribus,
> so relative paths resolve against the repo root the same way they
> always have.

This is **incorrect**. Scribus's auto-`chdir` makes the parent dir of
the SLA the effective base. Two consequences:

1. **For the first-PR (Phase A) brand-embed-only flow:** ALL assets
   are inline (`PFILE=""`), so PFILE path resolution doesn't matter
   for the downloaded SLA. **The user's plan still works** because
   the brand-embed-only rule sidesteps relative-path issues
   entirely.
2. **For the preview-render pipeline:** since the committed SLA after
   Phase C has every PAGEOBJECT either inline OR (forward-compat
   `shipped:`) relative, AND `shipped:` is empty in the first PR,
   the preview pipeline reads ONLY inline images. Relative
   resolution doesn't fire. **CONTEXT.md's claim is moot for the first
   PR**; it becomes wrong when Phase D ships and `shipped` is
   non-empty. The planner should flag this for the Phase D follow-up
   PR — the design says "relative paths" but the implementation will
   need either (a) `<slug>.zip::assets/<name>` with PFILE
   `assets/<name>` (resolves against the SLA's parent in the
   unzipped tree), OR (b) a working-dir helper that Scribus respects.
   This is a deferred concern; capture it here for the planner to
   call out as a Phase D risk.

### 2.5 Why a 12-asset inline embed isn't insane

The `infostand-tent-card-a5-quer/template.sla` is **214 KB** with 6
inline PNGs (small icons + QR). The v2-falzflyer with 12 inline
assets totaling ~27 MB source pixels will produce roughly 30-40 MB
SLA (qCompress is zlib-level-6 over PNG bytes, which are already
compressed — expect minimal compression gain). Scribus 1.6 opens
that fine in our experience with the gallery; the concern is
download size + git LFS pressure. The CONTEXT.md says this is the
chosen tradeoff for the first PR, so no scope to debate here.

### 2.6 The reconciler interaction

`/workspace/tools/reconcile_build_py.py` (340 LOC, function `reconcile`
at line 184) applies `inject.yml::injects[].set:` / `delta:` to a
generated `build.py.generated` to produce `build.py`. ISSUE.md Phase
C.2 says the reconciler must NOT let an inject change an asset's
embed/ship bucket. That's a guardrail against authors using
`inject.yml::injects[].field: image` to flip from `inline_image_data`
to `image` (or vice versa). Investigation of `reconcile_build_py.py`:

```bash
grep -nE "image=|inline_image" /workspace/tools/reconcile_build_py.py
# (no matches — the reconciler doesn't special-case image fields)
```

The reconciler is field-agnostic: it can target ANY kwarg of ANY DSL
call. So an inject CAN today flip an `ImageFrame(image='…')` into
`ImageFrame(inline_image_data='…')` by setting both fields.

**For the first PR, this is a non-issue:** every asset is inline by
the converter, so there's nothing for an inject to "flip". The
guardrail in ISSUE.md C.2 is a follow-up concern (Phase D land).
Recommend the planner flag this as "verify after Phase D lands; no
action needed for first PR".

### 2.7 The `bin/render-gallery <slug> --audit-strict` regression test

`bin/render-gallery` (`/workspace/bin/render-gallery`, 14 LOC) shims to
`render_pipeline.py::main`. The `--audit-strict` flag (line 1397) makes
the pipeline exit non-zero if any audit recorded an issue. The
integration test is `tests/integration/test_render_pipeline_e2e.py`
which probes (a) build.py is regenerated, (b) preview.pdf exists,
(c) audits run. For issue #39, the new regression test asserts:

- After Phase A/C lands and v2-falzflyer is re-emitted, the committed
  `template.sla` has 12 inline images (assert via
  `grep -c 'isInlineImage="1"'`) and 0 absolute paths (assert via
  `grep -cE 'PFILE="(/workspace|/home|/root|/tmp)' == 0`).
- Re-running the gallery render is byte-identical at preview.pdf
  level (qCompress is deterministic; PNG-from-inline-blob renders
  identically to PNG-from-disk for the same bytes).

---

## 3. Phase-by-phase recap with file pointers

### Phase A — Path canonicalisation

1. **Converter fix** (3 sites in `idml_to_dsl.py`):
   - Lines 1635–1665 (PDF/vector branch): remove the
     `Path(mapped).resolve()` call; if `mapped` is already
     repo-relative (the case for `links_export.yml::output`), pass it
     through unchanged. If somehow absolute, `relative_to(ROOT)` it;
     refuse to emit absolute.
   - Lines 2128–2143 (asset-map raster branch): same fix.
   - Lines 2157–2170 (legacy `--assets-dir` branch): drop the
     `try/except` fallback to absolute. Emit `relative_to(ROOT)` or
     raise.
2. **Migration of v2-falzflyer's committed SLA + build.py:** re-emit
   via `bin/idml-import --reimport` after the converter fix. Verify
   `grep "PFILE=\"/" template.sla` returns 0 lines.
3. **CI lint** (new file): `tools/check_no_absolute_paths_in_sla.py`
   walks `templates/*/template.sla`, greps for `PFILE="/`, exits 1
   on any match. Wire into `.pre-commit-config.yaml` + `ci.yml`.

### Phase B — Asset classification + meta.yml plumbing

1. **New file: `tools/asset_policy_audit.py`** (~150 LOC):
   - CLI: `--slug <id> --repo-root <path>` (or `--meta <path>
     --links-export <path>`).
   - Reads `templates/<slug>/meta.yml::asset_policy` via
     `meta_schema.load_asset_policy(slug)`.
   - Reads `shared/assets/<slug-or-idml-slug>/links_export.yml` and
     also checks files present in the directory (PR adds explicit
     basenames, not just IDML-linked names).
   - Asserts `policy is not None` (else hard-fail with instruction to
     add the block).
   - Asserts every basename in `links_export.yml::assets[*].output`
     basename appears in `embedded ∪ shipped`. **OR** every file in
     `shared/assets/<dir>/` (excluding `links_export.yml`) appears in
     the policy.
   - Asserts every entry in `embedded ∪ shipped` exists on disk.
   - **First-PR rule:** if `len(shipped) > 0`, hard-fail with the
     exact wording from CONTEXT.md lines 56–59. (Schema still allows
     the key for forward compatibility.)
   - Writes `build/validation/<slug>/asset_policy_audit.yml` with
     `ok: bool, missing_in_policy: [...], missing_on_disk: [...],
     shipped_nonempty_violation: bool`.
2. **Wire into `_run_audit`** (`render_pipeline.py` line 662): insert
   immediately after line 748 (after `asset_extraction_audit`),
   before line 750 (A1 inventory). Pattern mirrors the existing
   block exactly (try/except, append to `issue_parts`, log on
   stderr).
3. **Wire into `bin/idml-import`** (`idml_import_driver.py` line 458,
   right after `asset_extraction_audit`): run the new audit on the
   target template's `meta.yml`. If the policy is missing or the
   first-PR shipped-empty rule is violated, exit non-zero with a
   message that points the user at the heuristic-guessed split.
4. **Heuristic guesser** (helper inside `asset_policy_audit.py` OR
   in `idml_import_driver.py`): given a list of basenames, emit a
   YAML snippet the user can paste. Regex rules from `asset_policy.md`
   lines 107–113 (`*logo*`, `*social-media-icon*`, `wahlkreuz*`,
   `*-weiss.png`, `*-cmyk.png` → embed). Per CONTEXT.md, every
   asset → embedded in the first PR, so the heuristic always proposes
   `embedded:`; the user just confirms by copy-pasting.

### Phase C — SLA inline-embedding emission

1. **Add `meta.yml::asset_policy` read to converter:**
   `idml_to_dsl.py::convert()` (line 3081) gains a step that, given a
   `template_id`, loads `templates/<template_id>/meta.yml::asset_policy`
   via `from sla_lib.builder.meta_schema import load_asset_policy`
   (line 174 of meta_schema.py). Store `ctx.embedded_set` and
   `ctx.shipped_set` on `_Ctx`. **Both default to `None`** —
   distinguish "no policy block, use legacy behavior" from "policy
   block exists, enforce it".
2. **Add a third branch to `_emit_image_content`** (line 2071):
   ```python
   if ctx.embedded_set is not None and basename in ctx.embedded_set:
       # Phase C: inline.
       file_bytes = (ROOT / mapped).read_bytes()  # mapped is repo-relative
       ext = Path(basename).suffix.lstrip(".").lower()
       blob, ext_norm = pack_inline_image(file_bytes, ext)
       _emit_image_frame_call(
           ctx.out, x_mm, y_mm, w_mm, h_mm, rot,
           self_id, layer_idx,
           image_path="",  # PFILE stays empty when inline
           inline_data=blob, inline_ext=ext_norm,
           ctx=ctx, …
       )
       return
   ```
   The kwargs build flow at lines 2029–2033 already handles the
   `inline_data is not None` case (sets `inline_image_data` /
   `inline_image_ext`).
3. **Add `pack_inline_image` to the converter's import**
   (`idml_to_dsl.py` line 118 already imports it — re-use).
4. **Same third branch in the PDF/vector path** (line 1635–1665).
5. **Re-emission idempotency:** with all assets in `embedded:`, the
   converter output is deterministic (qCompress level 6 + zlib are
   deterministic). The re-emit-and-diff test asserts byte-identical
   build.py output across runs.

### Phase F — v2-falzflyer migration

1. **Author the `asset_policy:` block** in
   `/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml`.
   Per CONTEXT.md (lines 70–82), the 12 entries go into `embedded:`,
   `shipped:` is `[]`:

   ```yaml
   asset_policy:
     embedded:
       - gruene-logo-bund-weiss-cmyk.png
       - social-media-icon-facebook.png
       - social-media-icon-instagram.png
       - social-media-icon-tiktok.png
       - bluesky-weiss.png
       - mail-weiss.png
       - website-weiss.png
       - social-media-icons-weiss.png
       - green-pine-trees-covered-with-fog-crop.png
       - green-pine-trees-covered-with-fog-srgb.png
       - green-pine-trees-covered-with-fog.jpg
       - plakat-dunkel-fuer-flyer.png
     shipped: []
   ```

   The placement is anywhere top-level; recommend after `description:`
   and before `build:` for readability. The loader doesn't care about
   key order.

2. **Re-emit `build.py` + `template.sla`** by running
   `bin/idml-import <idml> --reimport --non-interactive
   --allow-composite-ai --no-brand-fonts` (matching the existing
   integration test invocation at line 63–73 of
   `test_idml_import_v2_falzflyer.py`).

3. **Verification asserts:**
   - `grep -c 'isInlineImage="1"' templates/.../template.sla == 9`
     (NOT 12 — the 3 unreferenced assets in `embedded` don't get
     emitted as PAGEOBJECTs since they're not in the IDML).
   - `grep -cE 'PFILE="/' templates/.../template.sla == 0`.
   - `grep -c 'image=' templates/.../build.py == 0` AND
     `grep -c 'inline_image_data=' templates/.../build.py == 9`.

   **Note on the "12 inline images" claim in the task prompt:** the
   IDML only references 9 of the 12 assets at the PAGEOBJECT level.
   The other 3 (`social-media-icons-weiss.png`,
   `green-pine-trees-covered-with-fog-srgb.png`,
   `green-pine-trees-covered-with-fog.jpg`) are present in
   `shared/assets/<slug>/` for composite_ai_split provenance or as
   alternate-format originals, but not directly PFILE'd in the SLA.
   The `embedded:` list still contains all 12 (Phase B's "every asset
   on disk must be classified" rule), but only 9 produce PAGEOBJECTs.

4. **preview.pdf byte-diff:** the existing pipeline produces
   `preview.pdf` + `page-01-hires.png` + `page-02-hires.png`. Compare
   pre-migration preview.pdf to post-migration. Inlining the PNG
   bytes (which are byte-identical to the on-disk file) should
   produce a byte-identical PDF, since Scribus's rasteriser reads
   the same QPixmap either way. Document any drift in
   EXECUTION.md per ISSUE.md F.3.

---

## 4. Pointers to ecosystem & pitfalls research

Ecosystem researcher: confirm Scribus 1.6 inline-image upper bound +
qCompress determinism (issue 35 was already tripped by qCompress's
behavior — see primitives.py line 762 comment about
`qUncompress: Z_DATA_ERROR`).

Pitfalls researcher: probe whether 30-40 MB SLAs cause LFS or git
performance pain; check Scribus QPixmap memory pressure during render
of 12 inlined images; verify `pdftocairo` handles big SLAs cleanly.

---

## 5. <interfaces>

```python
# From /workspace/tools/sla_lib/builder/meta_schema.py (lines 174-233)

def load_asset_policy(slug: str, root: Path | None = None) -> dict | None:
    """Return the parsed ``asset_policy`` block, or ``None`` if absent.

    Reads templates/<slug>/meta.yml. Returns None when the file is
    absent OR the asset_policy: key is missing.

    Validates against shared/asset-policy.schema.yaml. Enforces:
      - Required keys: embedded (list[str]), shipped (list[str]).
      - Lists are uniqueItems.
      - Lists are DISJOINT (not in jsonschema; raises ValueError).

    The asset-existence cross-check (basename ⇔ links_export.yml)
    lives in tools/asset_policy_audit.py per issue #39 (NOT here, to
    keep this loader pure-Python with no asset-fs dependency).

    Returns: dict with keys {'embedded': list[str], 'shipped': list[str]}
             or None.
    Raises: ValueError on YAML parse error, schema violation, or
            disjoint-violation.
    """

def load_brand_overrides(slug: str, root: Path | None = None) -> set[str]: ...
def load_band_spec(slug: str, root: Path | None = None) -> dict | None: ...
def load_sla_diff_strict(slug: str, root: Path | None = None) -> bool: ...
```

```python
# From /workspace/tools/sla_lib/builder/primitives.py (lines 759-770, 773-858)

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).

    Returns (qcompressed_b64, ext) — pass to ImageFrame as
      inline_image_data=qcompressed_b64, inline_image_ext=ext.
    Scribus expects:
      base64( 4-byte BE uncompressed-length prefix + zlib_compress(image_bytes, 6) ).
    Deterministic given the same input bytes.
    """

@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE path (absolute or relative-to-SLA)
    image: str = ""           # alias for src; converter prefers `image=`
    layer: int = 1
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 0       # 0 = fit-to-frame; 1 = free scaling
    ratio: int = 1
    pic_art: int = 1
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    inline_image_data: Optional[str] = None  # qCompress-base64 blob
    inline_image_ext: Optional[str] = None   # e.g. "png", "jpg"

    def to_pageobject(self, idgen, page) -> etree._Element:
        # Behavior when inline_image_data is set:
        #   PFILE=""; Pagenumber="0"; isInlineImage="1";
        #   inlineImageExt=<ext>; ImageData=<blob>; EMBEDDED="0"
        # Behavior when inline_image_data is None:
        #   PFILE=self.image or self.src (verbatim)
        ...
```

```python
# From /workspace/tools/idml_to_dsl.py (lines 677-716, 2002-2065, 2071-2176, 3081-3224)

@dataclass
class _Ctx:
    pkg: Any  # IDMLPackage
    template_id: str
    assets_dir: Path
    out: PythonRepr = field(default_factory=PythonRepr)
    doc_prefs: dict[str, Any] = field(default_factory=dict)
    layers: list[dict[str, Any]] = field(default_factory=list)
    layer_id_to_idx: dict[str, int] = field(default_factory=dict)
    printable_layer_ids: set[str] = field(default_factory=set)
    color_map: dict[str, str] = field(default_factory=dict)
    paragraph_style_map: dict[str, str] = field(default_factory=dict)
    paragraph_styles: dict[str, dict[str, Any]] = field(default_factory=dict)
    unmapped_logos: list[tuple[str, str]] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    logo_map: dict[str, str] = field(default_factory=dict)
    asset_map: dict[str, str] = field(default_factory=dict)         # basename → repo-rel output path
    unmapped_assets: list[tuple[str, str]] = field(default_factory=list)
    emitted_self_ids: set[str] = field(default_factory=set)
    skipped_with_reason: list[dict] = field(default_factory=list)
    # ── Phase C ADD (issue #39): ──
    # embedded_set: Optional[set[str]] = None  # populated from meta.yml::asset_policy::embedded
    # shipped_set:  Optional[set[str]] = None  # populated from meta.yml::asset_policy::shipped

    def record_skipped(self, self_id: str, reason: str) -> None: ...


def _emit_image_frame_call(
    out: PythonRepr,
    x_mm: float, y_mm: float, w_mm: float, h_mm: float,
    rot: float,
    self_id: str, layer_idx: int,
    image_path: str,
    ctx: _Ctx,
    inline_data: Optional[str] = None,
    inline_ext: Optional[str] = None,
    local_scale: Optional[tuple[float, float]] = None,
    local_offset_pt: Optional[tuple[float, float]] = None,
) -> None:
    """Append a page.add(ImageFrame(...)) call to ctx.out.

    Already supports inline_data + inline_ext kwargs (lines 2031-2033) —
    Phase C just needs to call this with those args populated.
    """


def _emit_image_content(
    out: PythonRepr,
    rect: Any, img: Any,
    x_mm: float, y_mm: float, w_mm: float, h_mm: float, rot: float,
    self_id: str, layer_idx: int,
    ctx: _Ctx,
    frame_tl_anchor: Optional[tuple[float, float]] = None,
) -> None:
    """Emit a raster <Image> as an ImageFrame. Current branches:
        1. ctx.asset_map (Phase 2 manifest) by basename → emits image='<abs>'
        2. ctx.assets_dir / basename (legacy) → emits image='<abs>' (with relative attempt)
    Issue #39 Phase A: drop the .resolve() — emit repo-relative.
    Issue #39 Phase C: add branch 0 that fires when basename ∈ ctx.embedded_set
                       and emits inline_image_data instead.
    """


def convert(source: Path, output: Path, template_id: str, assets_dir: Path,
            logo_map_path: Optional[Path] = None,
            asset_map_path: Optional[Path] = None,
            allow_dropped_pageitems: bool = False) -> None:
    """Strict 7-phase IDML → DSL build.py converter.
    Issue #39 Phase C: load meta.yml::asset_policy here and store on ctx.
    """
```

```python
# From /workspace/tools/asset_extraction_audit.py (lines 236-359)

def audit(
    slug: str,
    idml_path: Path,
    links_export_yml: Path,
    repo_root: Path,
    *,
    allow_composite_ai: bool = False,
    out_dir: Path | None = None,
) -> dict:
    """Run the asset-extraction audit. Returns the dict also written to
    build/validation/<slug>/asset_audit.yml.

    Schema of returned dict:
      template: str
      ok: bool
      links_total: int
      links_resolved: int
      links_converted: int
      links_missing: list[str]      # basename present in IDML, missing from Links/
      links_unconverted: list[str]  # present in Links/, missing from manifest
      composite_ai_detected: list[{path, page_count, aspect_ratio, distinct_offsets_count, signals}]
      warnings: list[str]  # only present when allow_composite_ai downgraded findings
    """
```

```python
# From /workspace/tools/render_pipeline.py (lines 662-748)

def _run_audit(tdir: Path, meta: dict, args) -> tuple[int, str]:
    """Run the audit chain: asset_extraction → A1 inventory → A2 text →
    A3 image → D6 font → D7 text-render → D8 text-position → …

    Issue #39 Phase B: insert asset_policy_audit between asset_extraction
    (line 748) and A1 inventory (line 750).

    Returns (audit_issue_count, summary_line).
    """
```

```python
# From /workspace/tools/idml_import_driver.py (lines 187-210, 374-595, 603-686)

def _scaffold_template_dir(slug: str, baseline_src: Path, tdir: Path) -> None:
    """Create templates/<slug>/{meta.yml, diff.yml, baseline.pdf}.
    Currently writes a 5-key meta.yml (id, version, title, format, build).
    Issue #39 Phase B may add an asset_policy: (commented-out heuristic)
    or leave it untouched and require the user to add the block manually.
    """

def _process_one(idml_path: Path, args, *, build_root, templates_root, assets_root) -> int:
    """Main driver pipeline. Order:
      1-5. Pre-flight + slug + brand-fonts + baseline.
      6.   Asset extraction (links_export.export).
      7.   Asset-extraction audit (line 458).
      ── Issue #39 Phase B: NEW STEP 7.5 — asset_policy_audit ──
      8.   Scaffold (_scaffold_template_dir).
      9.   Convert (_run_converter → idml_to_dsl.py).
      10.  Convergence loop or --scaffold-only halt.
    """

def _build_parser() -> argparse.ArgumentParser:
    """CLI flags currently exposed:
      path: positional, multi-value (IDML files or dirs)
      --accept-residual: append-many
      --dry-run, --max-iterations, --keep-baseline-from-pdf
      --scaffold-only, --reimport
      --no-brand-fonts, --allow-composite-ai, --non-interactive
    """
```

```python
# From /workspace/tools/sla_to_dsl.py (lines 203-216, 620-640)

def _capture_inline_image(elem: etree._Element) -> tuple[str, str]:
    """Capture (base64_image_data, ext) verbatim from an
    isInlineImage=1 PAGEOBJECT. Does NOT decode. Round-trip safe."""

# sla_to_dsl emits:
#   ImageFrame(inline_image_data=<verbatim_b64>, inline_image_ext=<ext>)
# This means re-emitting via build.py produces byte-identical SLA
# attribute (the b64 string never changes), guaranteeing Phase F's
# byte-identity round-trip for inline images.
```

```python
# From /workspace/tools/links_export.py (lines 69-105)

@dataclass(frozen=True)
class AssetEntry:
    original_basename: str   # NFC-normalised
    output_rel: str          # repo-relative POSIX path: shared/assets/<slug>/<file>
    kind: str                # vector_ai | raster_psd | raster_jpg | raster_png
    recipe: str              # human-readable conversion command
    vector_output_rel: str | None = None  # PDF copy for vector preservation

@dataclass(frozen=True)
class ExportResult:
    out_dir: Path
    manifest_path: Path
    # plus entries... (read manifest_path's links_export.yml for full list)

def export(links_dir: Path, out_dir: Path, *, quiet: bool = False) -> ExportResult: ...

# Manifest YAML shape:
# assets:
#   "<NFC-normalised original basename>":
#     kind: vector_ai | raster_psd | raster_jpg | raster_png
#     output: shared/assets/<slug>/<output-basename>    # repo-relative
#     recipe: <command string>
```

---

## 6. File-tree summary

```
/workspace/
├── .claude/skills/idml-import/
│   ├── SKILL.md                            (P11 lines 210-215)
│   └── asset_policy.md                     (178 lines, policy rationale)
├── .github/workflows/ci.yml                (line 59-70: SOP gates; +1 line for Phase A)
├── .pre-commit-config.yaml                 (+1 hook for Phase A)
├── bin/
│   ├── idml-import                         (13-line shim → tools/idml_import_driver.py)
│   └── render-gallery                      (15-line shim → tools/render_pipeline.py)
├── shared/
│   ├── asset-policy.schema.yaml            (46 lines, JSON-Schema)
│   └── assets/
│       └── 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/
│           ├── links_export.yml            (7-entry manifest)
│           ├── bluesky-weiss.png + 11 more (12 image files total, ~27 MB)
├── templates/
│   └── kandidat-falzflyer-din-lang-gruenes-cover-v2/
│       ├── build.py                        (9 absolute-path image= calls — FIX)
│       ├── template.sla                    (9 absolute PFILE — FIX)
│       ├── meta.yml                        (NO asset_policy: block — AUTHOR)
│       └── (baseline.pdf, inject.yml, diff.yml, preview.pdf, page-*.png)
├── tests/
│   ├── unit/test_asset_extraction_audit.py (~200 LOC; template for test_asset_policy_audit.py)
│   └── integration/
│       ├── test_idml_import_v2_falzflyer.py
│       ├── test_idml_to_dsl_smoke.py
│       ├── test_v2_falzflyer_build_byte_identity.py
│       └── test_render_pipeline_e2e.py
└── tools/
    ├── asset_extraction_audit.py           (442 LOC; extend OR sibling-file the policy audit)
    ├── idml_import_driver.py               (708 LOC; wire policy audit into _process_one)
    ├── idml_to_dsl.py                      (3357 LOC; Phase A 3 sites + Phase C inline branch)
    ├── render_pipeline.py                  (1537 LOC; wire policy audit into _run_audit)
    ├── reconcile_build_py.py               (340 LOC; field-agnostic, no special-casing needed)
    ├── sla_lib/builder/
    │   ├── meta_schema.py                  (loader at line 174-233)
    │   └── primitives.py                   (ImageFrame + pack_inline_image at line 759)
    └── (NEW) asset_policy_audit.py         (~150 LOC; Phase B; sibling to asset_extraction_audit.py)
    └── (NEW) check_no_absolute_paths_in_sla.py  (~50 LOC; Phase A; sibling SOP linter)
```

---

## 7. Phase B file-placement recommendation: sibling, not extension

The prompt asks: extend `tools/asset_extraction_audit.py` or sibling
`tools/asset_policy_audit.py`?

**Recommend SIBLING (`tools/asset_policy_audit.py`).** Reasons:

1. **Different inputs.** `asset_extraction_audit.py` takes an IDML +
   manifest + Links/. The policy audit takes `meta.yml` +
   `links_export.yml` (no IDML needed). Conflating them forces
   either-or argument handling.
2. **Different failure semantics.** Asset-extraction audit can
   warn-via-`--allow-composite-ai`. Policy audit is strict: missing
   policy = hard fail; non-empty `shipped:` = hard fail (first PR).
   Mixing the two warning levels muddies the API.
3. **Different invocation timing.** Asset-extraction audit runs once
   at IDML scaffold time (`bin/idml-import` line 458). Policy audit
   runs on every render-gallery cycle (every iteration of the
   convergence loop). Co-locating makes the order ambiguous.
4. **Tests live separately.** `test_asset_extraction_audit.py` is
   already 200+ LOC; doubling it forces test-file sprawl. A sibling
   `test_asset_policy_audit.py` is cleaner.
5. **The pattern is well-established.** `font_audit.py`,
   `line_spacing_audit.py`, `region_color_audit.py`,
   `text_position_audit.py`, etc. are all sibling files — each owns
   one audit dimension. Phase B fits the same shape.

Counter-argument: if Phase B's audit is < 80 LOC, the sibling overhead
is more than the dedup gain. Mitigation: keep
`asset_policy_audit.py` minimal (load policy, walk basenames, emit
yml) and lift any helper that's shared with `asset_extraction_audit.py`
(e.g. NFC basename normalisation) into a third module
(`tools/_asset_helpers.py`). Don't expand `asset_extraction_audit.py`
to host the policy logic.

---

## 8. Risks the planner needs to flag

1. **Scribus relative-path resolution.** CONTEXT.md misstates that
   relative paths resolve "against the repo root". They resolve
   against the SLA's parent directory. For the first PR (all assets
   inline) this is invisible; for Phase D it becomes a design
   constraint. Planner: note this in PLAN.md so the future-Phase-D
   author doesn't get bitten.
2. **30-40 MB SLA file.** Inlining all 12 v2-falzflyer assets pushes
   `template.sla` from ~430 KB to ~30-40 MB. Git history will
   accumulate ~30 MB per re-emit. Recommend the planner ask:
   - Is git-LFS already in use? (Don't think so — check `.gitattributes`.)
   - Acceptable bloat for the convergence loop's 5-10 iterations
     before stabilising?
   - Mitigation: in the convergence-loop window, set the policy
     `embedded:` to `[]` and let the legacy relative-path emit; only
     flip to full inline for the final commit. NOT in CONTEXT.md
     scope; flag as a follow-up.
3. **Naming-slug mismatch.** Template slug
   `kandidat-falzflyer-din-lang-gruenes-cover-v2` vs asset-dir slug
   `26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2`. The
   audit's lookup path must handle both. Existing dual-lookup in
   `render_pipeline.py` line 698 is the template; replicate it.
4. **Cross-cutting AC ambiguity.** ISSUE.md cross-cutting AC says "all
   9 templates pass the new audit". 8 of 9 templates have NO
   `links_export.yml` (they predate the IDML-import flow). Default
   behavior: skip silently when no manifest exists. CONTEXT.md is
   silent; planner must lock this decision.
5. **Existing v2-falzflyer brand_overrides + inject.yml.** Re-emitting
   build.py rewires the image= → inline_image_data= for 9 frames.
   The existing 6 inject.yml entries target text/PSR fields, not
   ImageFrame fields (confirmed via reading the meta.yml +
   brand_overrides list). Should not conflict, but planner should
   ask EXECUTION.md to verify by running
   `tools/lint_inject_consistency.py` after the re-emit.
6. **`_scaffold_template_dir` doesn't write `asset_policy:`.**
   Currently (line 194–204) it writes a 5-key meta.yml. If Phase B
   adds the heuristic-guessed block as a *commented-out* template, the
   user's only manual step is to uncomment. If Phase B leaves it
   untouched, the user must hand-author from scratch. Recommend the
   commented-out template approach (lower-friction) but flag the
   tradeoff in PLAN.md.
