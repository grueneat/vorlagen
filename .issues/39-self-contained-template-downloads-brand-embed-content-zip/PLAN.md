# Plan: Self-contained template downloads — brand embed (first PR, scope-locked)

<objective>
**What this plan accomplishes.** Ship the first PR for issue #39: make every
committed `templates/<slug>/template.sla` self-contained (no absolute paths, no
external file references for brand assets) by inline-embedding every IDML-import
asset into the SLA via `ImageFrame(inline_image_data=..., inline_image_ext=...)`.
The proof case is `kandidat-falzflyer-din-lang-gruenes-cover-v2`: today its
`template.sla` carries 9 absolute worktree paths (`PFILE="/workspace/.worktrees/35-…/…"`)
that resolve to nothing the moment a user downloads it. After this PR it has 9
`isInlineImage="1"` PAGEOBJECTs and 0 absolute paths.

**Why it matters.** The download is broken today regardless of any future
embed-vs-ship policy. Phase A (path canonicalisation) fixes the bug. Phase B
(asset_policy audit) prevents it recurring. Phase C (inline emission in the
converter) is the only mechanism that produces a self-contained SLA. Phase F
(v2-falzflyer migration) is the proof point. The skill doc (`asset_policy.md`)
must be reconciled in the same PR or future agents will copy the example
showing `shipped:` entries, hit the audit's "shipped must be empty for now"
rejection, and reach for silent workarounds.

**Scope (locked by CONTEXT.md — DO NOT EXPAND).** Phases **A + B + C + F only**.
Out of scope and MUST NOT appear in any task: **Phase D** (`tools/build_template_zip.py`,
zip pipeline), **Phase E** (gallery download flow flip from SLA to zip),
**Phase G** (AI watermark machinery, `tools/watermark_ai_image.py`, schema
extension to `oneOf: [string, object]`, `ai_generated:` field, the `KI-GENERIERT
MUSS ERSETZT WERDEN` overlay). The `shipped:` list MUST be empty in every
committed `meta.yml::asset_policy`. The audit rejects non-empty `shipped:` with
the verbatim CONTEXT.md message; the schema stays permissive for forward compat.

**7 tasks in dependency order:**
1. `tools/asset_policy_audit.py` — new audit (Phase B).
2. `tools/check_no_absolute_paths_in_sla.py` — pre-commit + CI lint (Phase A guard).
3. `templates/<v2>/meta.yml::asset_policy` — author the 12-entry `embedded:` block (Phase F prep).
4. `tools/idml_to_dsl.py` — 3 emit-site patch for inline embedding (Phase A + C).
5. v2-falzflyer re-emission — run `bin/idml-import --reimport`; verify SLA inline + lint passes (Phase F).
6. `.claude/skills/idml-import/asset_policy.md` — reconcile with CONTEXT.md (skill-doc drift fix).
7. `tests/integration/test_idml_import_v2_falzflyer_inline.py` — end-to-end gate.

CONTEXT.md exists and is authoritative — no decisions made on heuristic.
</objective>

<skills>
Read and follow these skills during execution:
- @.claude/skills/idml-import/SKILL.md (principle P11 — self-contained downloads)
- @.claude/skills/idml-import/asset_policy.md (the file Task 6 reconciles; read both before and after)
- @.claude/skills/idml-import/inject_protocol.md (Phase F re-emission must preserve inject.yml)

No new skills are introduced by this PR.
</skills>

<context>
**Issue inputs (read in full):**
- @.issues/39-self-contained-template-downloads-brand-embed-content-zip/ISSUE.md
- @.issues/39-self-contained-template-downloads-brand-embed-content-zip/CONTEXT.md (SCOPE LOCK — single source of truth)
- @.issues/39-self-contained-template-downloads-brand-embed-content-zip/RESEARCH.md
- @.issues/39-self-contained-template-downloads-brand-embed-content-zip/research/codebase.md (file-level findings + line numbers)
- @.issues/39-self-contained-template-downloads-brand-embed-content-zip/research/pitfalls.md (15 named pitfalls + mitigations)

**Memory references (binding rules):**
- `feedback_fix_generator_not_artifact.md` — Phase A patches `tools/idml_to_dsl.py`,
  NOT the committed `template.sla` directly. Task 5 re-emits the SLA by running
  the converter; the executor MUST NOT hand-edit `template.sla` to clear
  absolute paths.
- `feedback_no_claude_attribution.md` — no "claude" in commits, code, files, or
  PR descriptions. Commit subjects use `39: <type>(<scope>): <subject>`.
- `feedback_font_fidelity_check.md` — Phase F preview comparison must run
  `pdffonts` on both old and new `preview.pdf`. A missing variant = converter
  regression, not "engine floor".
- `feedback_idml_leading_vs_rendered.md` — irrelevant to this issue but kept in
  mind because Phase F touches the same template that surfaced the drift.

**Key files to read at execution start (do not skip):**
- @tools/sla_lib/builder/meta_schema.py (lines 174–233: `load_asset_policy`)
- @tools/sla_lib/builder/primitives.py (lines 759–770: `pack_inline_image`; 773–858: `ImageFrame`)
- @tools/asset_extraction_audit.py (the sibling-pattern template for Task 1)
- @tools/idml_to_dsl.py (lines 677–716: `_Ctx`; 1620–1665, 2071–2176: the 3 emit sites)
- @tools/render_pipeline.py (lines 662–748: `_run_audit` wire-in point)
- @tools/idml_import_driver.py (lines 187–595: `_process_one`, wire-in after asset extraction)
- @shared/asset-policy.schema.yaml (the schema — DO NOT MODIFY in this PR)
- @templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml (the target of Task 3)
- @templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla (the SLA Task 5 re-emits; do not hand-edit)
- @templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/inject.yml (13 entries; Task 5 must preserve via reconcile)
- @templates/infostand-tent-card-a5-quer/build.py (lines 91–95, 122–142: working `pack_inline_image` reference)
- @shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/ (the 12 source files Task 3 enumerates)
- @.pre-commit-config.yaml (Task 2 appends a 5th hook)
- @.github/workflows/ci.yml (lines 59–70: SOP-gates step; Task 2 appends 1 line)

**Worktree note.** Executor runs in
`/workspace/.worktrees/39-self-contained-template-downloads-brand-embed-content-zip/`
on branch `issue/39-self-contained-template-downloads-brand-embed-content-zip`
branched from `origin/main` (which already carries the #79 + #80 + #82 work,
including `load_asset_policy()`, the asset_policy schema, and the policy
skill doc). When the prompt or memory refers to "ROOT" in `tools/idml_to_dsl.py`
(line 125: `ROOT = _THIS.parent.parent`), that resolves through the worktree's
own root symlink — NOT `/workspace/`. Always use `Path(__file__).resolve()`
chains or `load_asset_policy(slug, root=worktree_root)`, never hard-coded
`/workspace/`.

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

# From /workspace/tools/sla_lib/builder/meta_schema.py (lines 174-233)
def load_asset_policy(slug: str, root: Path | None = None) -> dict | None:
    """Return the parsed ``asset_policy`` block, or ``None`` if absent.

    Reads templates/<slug>/meta.yml. Returns None when the meta.yml file
    does not exist OR the `asset_policy:` key is missing.

    Validates against shared/asset-policy.schema.yaml. Enforces:
      - Required keys: embedded (list[str]), shipped (list[str]).
      - Lists are uniqueItems.
      - Lists are DISJOINT (not in jsonschema; raises ValueError on overlap).

    The asset-existence cross-check (basename <-> shared/assets/<slug>/)
    lives in tools/asset_policy_audit.py per issue #39 (NOT here, to
    keep this loader pure-Python with no asset-fs dependency).

    Returns: dict with keys {"embedded": list[str], "shipped": list[str]}
             or None.
    Raises: ValueError on YAML parse error, schema violation, disjoint
            violation. Each raise carries a clear actionable message.
    """

# From /workspace/tools/sla_lib/builder/primitives.py (lines 759-770)
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).

    Returns (qcompressed_b64_string, ext_lowercased).
    Scribus expects:
      base64( 4-byte BIG-ENDIAN uncompressed-length prefix + zlib_compress(image_bytes, 6) ).
    Deterministic given the same input bytes (zlib level 6, stdlib zlib).
    Naive base64-of-raw-bytes makes Scribus abort with `qUncompress: Z_DATA_ERROR`.
    """

# From /workspace/tools/sla_lib/builder/primitives.py (lines 773-858)
@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE path (relative-to-SLA or absolute)
    image: str = ""           # alias for src; converter prefers image=
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

    # Emitter behavior:
    #   inline_image_data is None  -> PAGEOBJECT has PFILE=<image or src>
    #   inline_image_data set      -> PFILE=""; Pagenumber="0"; isInlineImage="1";
    #                                 inlineImageExt=<ext>; ImageData=<blob>;
    #                                 EMBEDDED="0"

# From /workspace/tools/idml_to_dsl.py (line 125, 677-716)
ROOT = _THIS.parent.parent  # resolves through symlinks; in the worktree this is the worktree root

@dataclass
class _Ctx:
    pkg: Any
    template_id: str
    assets_dir: Path
    out: PythonRepr = field(default_factory=PythonRepr)
    # ... many existing fields ...
    asset_map: dict[str, str] = field(default_factory=dict)   # basename -> repo-rel output path
    # NEW (issue #39 Task 4):
    # embedded_set: set[str] = field(default_factory=set)     # basenames in meta.yml::asset_policy::embedded

# From /workspace/tools/idml_to_dsl.py (lines 2002-2065)
def _emit_image_frame_call(
    out: PythonRepr,
    x_mm: float, y_mm: float, w_mm: float, h_mm: float,
    rot: float,
    self_id: str, layer_idx: int,
    image_path: str,
    ctx: _Ctx,
    inline_data: Optional[str] = None,   # ALREADY SUPPORTED — Task 4 just calls with this populated
    inline_ext: Optional[str] = None,    # ALREADY SUPPORTED — Task 4 just calls with this populated
    local_scale: Optional[tuple[float, float]] = None,
    local_offset_pt: Optional[tuple[float, float]] = None,
) -> None:
    """Append a page.add(ImageFrame(...)) call to ctx.out.
    When inline_data is not None, image_path is set to "" in the emitted
    kwargs and inline_image_data=, inline_image_ext= are populated.
    """

# Phase A bug sites in /workspace/tools/idml_to_dsl.py — Task 4 patches all three:
#   Lines 1635-1664  -> PDF/vector logo emit branch
#   Lines 2128-2143  -> asset-map raster emit branch (the actively-firing one on v2-falzflyer)
#   Lines 2157-2170  -> legacy --assets-dir fallback emit branch

# From /workspace/tools/render_pipeline.py (lines 662-748)
def _run_audit(tdir: Path, meta: dict, args) -> tuple[int, str]:
    """Audit chain. Current order (top-down inside this function):
       asset_extraction_audit (lines 693-748) ->
       A1 inventory (lines 750-769) ->
       A2 baseline text audit (lines 771-792) ->
       A3 baseline image audit (lines 794-817) -> ...
    Task 1: insert asset_policy_audit AFTER asset_extraction_audit (post-line 748)
            and BEFORE A1 inventory (pre-line 750).
    Returns (audit_issue_count, summary_line)."""

# From /workspace/tools/idml_import_driver.py (lines 374-595, especially line 458)
def _process_one(idml_path: Path, args, *, build_root, templates_root, assets_root) -> int:
    """Driver pipeline. Order:
      1-5. Pre-flight + slug + brand-fonts + baseline.
      6.   Asset extraction (links_export.export, line 446).
      7.   Asset-extraction audit (line 458; hard-fails on not ok).
      ── Issue #39 Task 1: NEW STEP 7.5 — asset_policy_audit ──
      8.   _scaffold_template_dir (line 476; do NOT modify in this PR).
      9.   _run_converter -> tools/idml_to_dsl.py (line 480).
      10.  Convergence or --scaffold-only halt.
    """

# v2-falzflyer asset directory (NOTE: directory name is the IDML-stem-slug, NOT the template slug)
# /workspace/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/
# Contains 12 files (excluding links_export.yml):
#   bluesky-weiss.png                                   29217 bytes (brand)
#   green-pine-trees-covered-with-fog-crop.png        4608235 bytes (content; PFILE'd on page 2)
#   green-pine-trees-covered-with-fog-srgb.png        6985953 bytes (derivative; not PFILE'd)
#   green-pine-trees-covered-with-fog.jpg             6896771 bytes (original; not PFILE'd)
#   gruene-logo-bund-weiss-cmyk.png                     49604 bytes (brand)
#   mail-weiss.png                                      25524 bytes (brand)
#   plakat-dunkel-fuer-flyer.png                      8558653 bytes (content; PFILE'd)
#   social-media-icon-facebook.png                      28688 bytes (brand)
#   social-media-icon-instagram.png                     48436 bytes (brand)
#   social-media-icon-tiktok.png                        37070 bytes (brand)
#   social-media-icons-weiss.png                       116981 bytes (composite; NOT PFILE'd; kept for provenance)
#   website-weiss.png                                   40426 bytes (brand)

# Asset-dir dual lookup pattern (render_pipeline.py:698) — Task 1 audit follows this:
#   shared/assets/<template_slug>/   (preferred convention going forward)
#   shared/assets/<idml_stem_slug>/  (historical — v2-falzflyer's case)
</interfaces>

**Call-site enumeration.** Issue #39 introduces no new CLI flag and no new
subcommand. Task 2 introduces `tools/check_no_absolute_paths_in_sla.py` as a
standalone script; Task 1 introduces `tools/asset_policy_audit.py` as both a
library function (`run_asset_policy_audit`) and CLI entry point. Both are
new files — no existing invocations to update. Both are wired into existing
chains:
- `tools/check_no_absolute_paths_in_sla.py`: appended to `.pre-commit-config.yaml`
  (Task 2) AND appended to `.github/workflows/ci.yml` SOP-gates step (Task 2).
  No other invocation surfaces.
- `tools/asset_policy_audit.py`: called from `tools/render_pipeline.py::_run_audit`
  (Task 1) AND `tools/idml_import_driver.py::_process_one` (Task 1). No other
  invocation surfaces.

Greps run during planning (zero adjacent surfaces beyond the wire-ins above):
```
grep -rn "asset_policy_audit" /workspace --include='*.py' --include='*.yml' --include='*.yaml' --include='Makefile'
grep -rn "check_no_absolute_paths_in_sla" /workspace --include='*.py' --include='*.yml' --include='*.yaml' --include='Makefile'
```
Both return only ISSUE.md / RESEARCH.md references — no existing call sites.
</context>

<commit_format>
**Format (from `.issues/config.yaml`):** conventional with numeric issue prefix.
**Pattern:** `39: <type>(<scope>): <subject>`
**Types used in this PR:** `feat`, `fix`, `chore`, `docs`, `test`.

**Per-task examples (use these or close variants):**
- Task 1: `39: feat(asset_policy_audit): coverage cross-check + shipped-empty rule`
- Task 2: `39: feat(check_no_absolute_paths_in_sla): pre-commit + CI lint`
- Task 3: `39: chore(v2-falzflyer): meta.yml asset_policy authoring`
- Task 4: `39: fix(idml_to_dsl): inline-embed assets listed in asset_policy::embedded`
- Task 5: `39: chore(v2-falzflyer): re-emit SLA with inline brand assets`
- Task 6: `39: docs(skill): reconcile asset_policy.md with CONTEXT.md`
- Task 7: `39: test(integration): bin/idml-import e2e on v2-falzflyer inline`

**HARD RULE (from `feedback_no_claude_attribution.md`):** never include "claude"
in commit subject, commit body, code, filenames, PR title, or PR description.
This applies verbatim. Do not write "generated by Claude", "co-authored-by
Claude", or similar in any artifact.

**One commit per task** (7 commits total). Pre-commit hooks must pass on each
commit; do not skip with `--no-verify`.
</commit_format>

<tasks>

<task type="auto">
  <name>Task 1: Land `tools/asset_policy_audit.py` (Phase B)</name>
  <files>tools/asset_policy_audit.py, tests/unit/test_asset_policy_audit.py, tools/render_pipeline.py, tools/idml_import_driver.py</files>
  <action>
**Create `tools/asset_policy_audit.py`** as a sibling of `tools/asset_extraction_audit.py`.
Do NOT extend the existing audit (per RESEARCH.md §7: different inputs, different
failure semantics, different invocation timing). Pattern after the existing
sibling: top-of-file docstring, `audit(...)` function returning a result dict,
optional CLI under `if __name__ == "__main__"`.

**Public API:**
```python
def run_asset_policy_audit(
    template_slug: str,
    root: Path,
    *,
    out_dir: Path | None = None,
) -> dict:
    """Audit meta.yml::asset_policy against shared/assets/<slug>/.

    Resolves the asset directory using the dual-lookup pattern from
    render_pipeline.py:698:
      1. shared/assets/<template_slug>/         (preferred)
      2. shared/assets/<idml_stem_slug>/        (historical; derive from meta.yml::build::source or links_export.yml provenance)

    Hard-fail conditions (returns ok=False with `issue` key set):
      (a) shipped: list is non-empty
      (b) shared/assets/<slug>/ exists AND meta.yml::asset_policy is absent (missing)
      (c) asset in shared/assets/<slug>/ NOT in embedded: list (unclassified)
      (d) asset in embedded: list NOT on disk at shared/assets/<slug>/ (stale)

    Silent-skip (returns ok=True, skipped=True):
      No shared/assets/<slug>/ directory exists for this template. (8 of 9
      templates today fall into this branch; only v2-falzflyer has an asset
      directory.)

    Writes build/validation/<slug>/asset_policy_audit.yml when out_dir is provided.

    Returns:
      {"ok": bool, "skipped": bool (optional), "issue": str (optional),
       "shipped": [...], "unclassified": [...], "stale": [...], "asset_dir": str | None}
    """
```

**Module-level error messages as `const` (per pitfalls.md §10):**
```python
_SHIPPED_REJECTED_MSG = (
    "Shipped assets are pending brand-team review. The first PR "
    "for issue #39 only supports `embedded:`. Move the asset to "
    "`embedded:` (it will be inlined in the SLA) or remove it from "
    "the template until the brand team decides on the zip flow."
)
_MISSING_POLICY_MSG = (
    "meta.yml::asset_policy is required when shared/assets/<slug>/ exists. "
    "Add an `asset_policy:` block listing every file in shared/assets/<slug>/ "
    "under `embedded:`. See .claude/skills/idml-import/asset_policy.md."
)
# _UNCLASSIFIED_MSG / _STALE_MSG follow the same shape; include the offending basenames.
```

The `_SHIPPED_REJECTED_MSG` MUST be the verbatim text from CONTEXT.md lines
56–59 (issue prompt repeats it). Use it as the `message` key in the result
dict when `issue == "shipped_non_empty"`. The audit MUST NOT modify
`shared/asset-policy.schema.yaml` — the schema stays permissive (allows
non-empty `shipped:`); only this audit rejects.

**Helper for asset-dir resolution:**
```python
def _find_asset_dir(template_slug: str, root: Path) -> Path | None:
    """Dual lookup. First try shared/assets/<template_slug>/. If absent,
    derive the IDML-stem slug from templates/<slug>/meta.yml::build::source
    or from links_export.yml provenance and try shared/assets/<idml_stem>/.
    Return the first directory that exists, or None.

    For v2-falzflyer this resolves to
    shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/.
    """
```

**Treat `links_export.yml` and `*.yml` as NON-assets when walking the asset
directory.** Per pitfalls.md §5 (composite-AI handling: per-icon PNGs are on
disk but not in `links_export.yml`), the audit uses the FILESYSTEM as truth:
every `*.png` / `*.jpg` / `*.psd` / `*.eps` / `*.svg` / `*.tif` in the asset
dir is an asset; everything else (`*.yml`, `*.md`) is metadata.

**`load_asset_policy()` import:**
```python
from sla_lib.builder.meta_schema import load_asset_policy
```
This already validates schema + disjointness; the audit does NOT re-implement
either. If `load_asset_policy` raises `ValueError` (schema violation, disjoint
overlap), the audit propagates the exception unchanged — the caller (CLI or
`_run_audit` wrapper) catches and treats it as a hard fail.

**CLI entry point:**
```bash
python3 tools/asset_policy_audit.py --slug <template_slug>
```
Exits 0 on ok=True or skipped=True, exits 2 on user-fixable issues
(unclassified, stale, missing), exits 3 on policy-broken (shipped_non_empty).

**Wire-in #1 — `tools/render_pipeline.py::_run_audit`:**
Insert immediately AFTER the existing `asset_extraction_audit` block (the block
that ends around line 748) and BEFORE the A1 inventory call (line ~750). Follow
the existing block's pattern exactly: try/except, append to `issue_parts`, log
on stderr. The new block reads:
```python
# Issue #39 Phase B — asset_policy audit (post-extraction, pre-A1).
try:
    policy_audit = run_asset_policy_audit(
        meta["id"], root=ROOT, out_dir=tdir / "build" / "validation",
    )
    if not policy_audit.get("ok"):
        issue_parts.append(f"asset_policy: {policy_audit.get('issue')}")
        # ... follow asset_extraction_audit's logging cadence ...
except ValueError as exc:
    issue_parts.append(f"asset_policy: schema-error: {exc}")
```
Verify the order by re-reading lines 693–748 before editing; the existing
asset_extraction_audit shape is the template.

**Wire-in #2 — `tools/idml_import_driver.py::_process_one`:**
Insert immediately AFTER the asset_extraction_audit call (line ~458, which
hard-fails on `not report["ok"]`) and BEFORE the scaffold call (line ~476).
This is the "Step 7.5" in the codebase research's pipeline. Pattern:
```python
# Issue #39 Phase B — refuse to scaffold if asset_policy isn't valid.
policy_audit = run_asset_policy_audit(slug, root=workspace_root)
if not policy_audit.get("ok") and not policy_audit.get("skipped"):
    print(f"asset_policy_audit failed: {policy_audit}", file=sys.stderr)
    return 2
```
The driver's existing exit-code discipline is 0=ok, 1=tool error, 2=audit
fail; match it.

**Tests in `tests/unit/test_asset_policy_audit.py`:**
Use `tempfile.TemporaryDirectory()` + `load_asset_policy(slug, root=Path(tmp))`
pattern from `tests/unit/test_asset_extraction_audit.py`. Each test builds a
fake root containing:
```
<tmp>/shared/asset-policy.schema.yaml  (symlink or copy from repo)
<tmp>/templates/<slug>/meta.yml
<tmp>/shared/assets/<slug>/<file1>.png   (1-byte dummy content; we test
                                          the audit, not the byte content)
```

Cover all 6 cases:
1. **Happy path:** policy lists every disk file in `embedded:`, `shipped: []`.
   Expect `ok=True, skipped=False`.
2. **Silent skip:** no `shared/assets/<slug>/`. Expect `ok=True, skipped=True`.
3. **Missing policy:** asset dir exists, meta.yml has no `asset_policy:` block.
   Expect `ok=False, issue="missing"`, error message contains "shared/assets".
4. **Shipped non-empty:** asset dir exists, policy lists 1 file in `shipped:`.
   Expect `ok=False, issue="shipped_non_empty"`, `message == _SHIPPED_REJECTED_MSG`
   (verbatim).
5. **Unclassified:** asset dir has 2 files, policy lists 1 in `embedded:`.
   Expect `ok=False, issue="coverage"`, `unclassified=[<the missing basename>]`.
6. **Stale:** policy lists a file in `embedded:` that doesn't exist on disk.
   Expect `ok=False, issue="coverage"`, `stale=[<the absent basename>]`.

Also: a "no double-counting" test where the asset dir contains a `links_export.yml`
file — the audit must NOT treat `links_export.yml` as an asset (assert it's
neither in `unclassified` nor required in `embedded:`).

**What NOT to do in this task:**
- Do NOT modify `shared/asset-policy.schema.yaml` (CONTEXT.md rule 2: schema
  stays permissive).
- Do NOT modify `tools/sla_lib/builder/meta_schema.py::load_asset_policy`.
- Do NOT change `tools/asset_extraction_audit.py` (sibling, not extension).
- Do NOT add interactive prompting to `bin/idml-import` (per RESEARCH.md
  §1.4: hard-fail with actionable message; interactive UX is a follow-up).
- Do NOT write an `asset_policy:` block into `meta.yml` (Task 3 does that
  manually for v2-falzflyer; the audit is read-only).
  </action>
  <verify>
  <automated>pytest tests/unit/test_asset_policy_audit.py -q && python3 -m unittest discover tests/unit -q && python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2; echo "Expected exit 2 or 3 here (v2 has no asset_policy yet); Task 3 makes it 0."</automated>
  </verify>
  <done>
  - `tools/asset_policy_audit.py` created with `run_asset_policy_audit(slug, root, *, out_dir)` exported.
  - `_SHIPPED_REJECTED_MSG` is the verbatim CONTEXT.md text.
  - `tests/unit/test_asset_policy_audit.py` covers all 6 cases (happy, skip, missing, shipped-non-empty, unclassified, stale) plus the `links_export.yml` non-asset case.
  - Wired into `tools/render_pipeline.py::_run_audit` AFTER asset_extraction_audit, BEFORE A1 inventory.
  - Wired into `tools/idml_import_driver.py::_process_one` AFTER asset extraction (post line ~458), BEFORE scaffold (pre line ~476).
  - `pytest tests/unit/test_asset_policy_audit.py -q` passes.
  - `python3 -m unittest discover tests/unit -q` passes.
  - `tools/sop_lint.py` passes (no "engine floor" introduced).
  - `shared/asset-policy.schema.yaml` is unchanged.
  - `tools/sla_lib/builder/meta_schema.py` is unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Land `tools/check_no_absolute_paths_in_sla.py` (Phase A guard)</name>
  <files>tools/check_no_absolute_paths_in_sla.py, tests/unit/test_check_no_absolute_paths_in_sla.py, .pre-commit-config.yaml, .github/workflows/ci.yml</files>
  <action>
**Create `tools/check_no_absolute_paths_in_sla.py`** as a SOP-style linter
(pattern after `tools/sop_lint.py`, `tools/lint_inject_consistency.py`,
`tools/check_overrides_growth.py` — all `language: system`, `pass_filenames: false`).

**Behaviour:** Walk `templates/*/template.sla` via `lxml`. For every
`PAGEOBJECT` element with a `PFILE` attribute, fail if `PFILE` matches the
regex:
```python
ABSOLUTE_PFILE_RE = re.compile(r"^(?:/|file://|[A-Za-z]:[\\/])")
```
This catches:
- Unix absolute paths (`/workspace/...`, `/home/...`, `/root/...`, `/tmp/...`,
  `/var/...`, `/private/var/...`, `/Users/...`)
- `file://` URIs
- Windows drive letters (`C:\`, `C:/`)

Per pitfalls.md §7, the broad regex is intentional — every variant must be
caught even though `/workspace/` is the only one we've seen in practice.

**Empty PFILE is OK** — `isInlineImage="1"` frames have `PFILE=""` per
`primitives.py:811`. The regex `^/...` doesn't match the empty string, so
this is automatic, but add an explicit early-continue for clarity:
```python
if not pfile:
    continue
```

**Output format (grep-style, one line per failure):**
```
<sla-path>:<line>: absolute PFILE: <pfile-value>
```
The line number comes from `etree.parse(...)` + `el.sourceline` (lxml-only,
not stdlib ET). The script returns exit code 1 on any failure, 0 on no
failures.

**CLI entry point:**
```python
def main(argv: list[str] | None = None) -> int:
    """Walk templates/*/template.sla; fail on any absolute PFILE.
    Returns 0 if clean, 1 if any failures.
    """
    root = Path(__file__).resolve().parents[1]  # repo root
    failures: list[tuple[Path, int, str]] = []
    for sla in sorted(root.glob("templates/*/template.sla")):
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

if __name__ == "__main__":
    sys.exit(main())
```

**Pre-commit hook entry (append to `.pre-commit-config.yaml`):**
Place AFTER the existing four SOP hooks (sop_lint, check_overrides_growth,
lint_inject_consistency, reconcile-build-py-check). Use the same shape as
the existing hooks:
```yaml
  - id: check-no-absolute-paths-in-sla
    name: Reject absolute filesystem paths in committed template.sla files
    entry: python3 tools/check_no_absolute_paths_in_sla.py
    language: system
    pass_filenames: false
    always_run: true
```

**CI workflow entry (append one line to `.github/workflows/ci.yml`):**
Locate the SOP-gates step around lines 59–70. Append `python3 tools/check_no_absolute_paths_in_sla.py`
as a new line inside the existing `run:` block (it's a `set -e` script).
Do NOT add a new step or new job.

**Tests in `tests/unit/test_check_no_absolute_paths_in_sla.py`:**
Use `tempfile.TemporaryDirectory()` + write synthetic SLA fragments via
`lxml.etree`. Each test patches `Path(__file__).resolve().parents[1]` via a
helper that overrides the search root (cleaner: factor `main()` to accept a
`root: Path` argument with a default of `Path(__file__).resolve().parents[1]`,
then test by passing `root=tmp`).

Cover (per pitfalls.md §7):
1. **Unix absolute** (`PFILE="/workspace/foo.png"`) → exit 1, message contains the path.
2. **Other Unix roots** (`PFILE="/home/x/y.png"`, `PFILE="/Users/u/p.png"`,
   `PFILE="/var/tmp/q.png"`, `PFILE="/private/var/z.png"`) → all exit 1.
3. **file:// URI** (`PFILE="file:///workspace/foo.png"`) → exit 1.
4. **Windows drive** (`PFILE="C:\\foo.png"`, `PFILE="D:/bar.png"`) → exit 1.
5. **Empty PFILE** (`PFILE=""` with `isInlineImage="1"`) → exit 0.
6. **Relative PFILE** (`PFILE="assets/foo.png"`, `PFILE="../shared/x.png"`) → exit 0.
7. **No SLAs at all** (empty templates/ dir) → exit 0.
8. **Multiple failures** (2 templates, 1 absolute each) → exit 1, both reported.

**What NOT to do:**
- Do NOT also check `ICCProfile=` or other `*FILE=` attributes (pitfalls.md §7
  mention is defensive but out of scope; `PFILE` is the only attribute the
  converter emits with a path today).
- Do NOT silently strip absolute paths — refuse them; let the user (or Task 5's
  re-emit) fix the source.
- Do NOT add `tools/check_sla_size.py` (pitfalls.md §2 mitigation; out of
  scope per CONTEXT.md — that's a Phase D-era concern).
  </action>
  <verify>
  <automated>pytest tests/unit/test_check_no_absolute_paths_in_sla.py -q && python3 -m unittest discover tests/unit -q && python3 tools/check_no_absolute_paths_in_sla.py; echo "Expected exit 1 here (v2-falzflyer SLA still has 9 absolute paths); Task 5 makes it 0."</automated>
  </verify>
  <done>
  - `tools/check_no_absolute_paths_in_sla.py` created; uses lxml for line-numbered output.
  - Regex catches Unix absolute, file://, Windows drives; allows empty + relative.
  - `tests/unit/test_check_no_absolute_paths_in_sla.py` covers 8 cases (unix variants, file URI, windows, empty, relative, no-SLAs, multiple).
  - `.pre-commit-config.yaml` has the 5th `repo: local` hook with `language: system, pass_filenames: false`.
  - `.github/workflows/ci.yml` SOP-gates step has one new line; no new step / no new job.
  - `pytest tests/unit/test_check_no_absolute_paths_in_sla.py -q` passes.
  - `python3 -m unittest discover tests/unit -q` passes.
  - At this task's end, the lint FAILS on the repo (v2-falzflyer still has 9 absolute PFILEs). Document this in the EXECUTION.md note: "lint intentionally red after Task 2; goes green after Task 5."
  </done>
</task>

<task type="auto">
  <name>Task 3: Author v2-falzflyer `meta.yml::asset_policy` (Phase F preparation)</name>
  <files>templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml</files>
  <action>
**Append an `asset_policy:` block** to
`templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml`. Place it
after the existing `description:` (or `title:`) field and before `build:` for
readability. The loader (`load_asset_policy`) doesn't care about key order.

**Exact block (12 entries in `embedded:`, `shipped: []`):**
```yaml
asset_policy:
  embedded:
    - bluesky-weiss.png
    - green-pine-trees-covered-with-fog-crop.png
    - green-pine-trees-covered-with-fog-srgb.png
    - green-pine-trees-covered-with-fog.jpg
    - gruene-logo-bund-weiss-cmyk.png
    - mail-weiss.png
    - plakat-dunkel-fuer-flyer.png
    - social-media-icon-facebook.png
    - social-media-icon-instagram.png
    - social-media-icon-tiktok.png
    - social-media-icons-weiss.png
    - website-weiss.png
  shipped: []
```

**Notes for the executor:**
- All 12 source files in
  `shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/`
  appear in `embedded:`, including the 3 that aren't directly PFILE'd in the
  SLA today (`social-media-icons-weiss.png`, `green-pine-trees-covered-with-fog-srgb.png`,
  `green-pine-trees-covered-with-fog.jpg`) — per RESEARCH.md and pitfalls.md §5,
  the audit treats the disk as truth and requires every on-disk asset to be
  classified.
- Entries are sorted alphabetically (deterministic for diff / round-trip).
- The list is YAML-style "list of strings" (NOT objects; the object form
  `{name: ..., ai_generated: ...}` is Phase G — explicitly OUT OF SCOPE for
  this PR per CONTEXT.md).
- `shipped: []` MUST be the literal empty list with the key present. Per
  pitfalls.md §15, the schema requires both `embedded` and `shipped` keys;
  an absent `shipped:` would fail schema validation before the audit even
  fires.

**Self-check at task end:**
Run `python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2`
and verify it exits 0 (ok). The SLA still has 9 absolute paths at this point
(Task 4 fixes the converter, Task 5 re-emits the SLA), so
`tools/check_no_absolute_paths_in_sla.py` still fails — that is expected.

**What NOT to do:**
- Do NOT change any other field in `meta.yml` (id, title, version, format,
  build, brand_overrides, baseline_pdf_sha, previews_for_sla, etc.).
- Do NOT modify `inject.yml`.
- Do NOT add any AI-related fields (no `ai_generated:`, no `watermark:`).
- Do NOT delete or modify any of the 12 files in
  `shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/`.
- Do NOT touch `links_export.yml` (it stays as-is; the audit walks the
  filesystem as truth).
  </action>
  <verify>
  <automated>python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2 && python3 -c "from sla_lib.builder.meta_schema import load_asset_policy; p = load_asset_policy('kandidat-falzflyer-din-lang-gruenes-cover-v2'); assert p is not None and len(p['embedded']) == 12 and p['shipped'] == [], p"</automated>
  </verify>
  <done>
  - `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml` has an `asset_policy:` block with exactly 12 sorted basenames in `embedded:` and `shipped: []`.
  - `python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2` exits 0.
  - `load_asset_policy('kandidat-falzflyer-din-lang-gruenes-cover-v2')` returns the expected dict (schema-valid, disjoint).
  - No other field in `meta.yml` changes.
  - `tools/check_no_absolute_paths_in_sla.py` STILL FAILS (this is intentional; Task 5 fixes it).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Patch `tools/idml_to_dsl.py` — 3 emit sites for inline embedding (Phase A + C)</name>
  <files>tools/idml_to_dsl.py, tests/unit/test_idml_to_dsl_inline_embedding.py</files>
  <action>
**Goal:** the converter consults `meta.yml::asset_policy::embedded` and emits
`ImageFrame(inline_image_data=..., inline_image_ext=...)` for every basename
listed there. This task fuses Phase A (drop absolute paths) and Phase C
(inline embed) — they share the same call sites.

**RED — write tests first** in `tests/unit/test_idml_to_dsl_inline_embedding.py`:

Use a synthetic IDML fixture pattern (in-memory `io.BytesIO` + `zipfile.ZipFile`
per `tests/unit/test_asset_extraction_audit.py::_make_idml`). The IDML contains
ONE spread with ONE `<Image>` link to a synthetic 1x1 PNG. Tests assert:

1. **Embedded asset emits inline:** with `meta.yml::asset_policy::embedded:
   [test-asset.png]`, the emitted `build.py` contains
   `inline_image_data="..."` and `inline_image_ext="png"` for that image and
   does NOT contain `image='/.../test-asset.png'`.
2. **Embedded asset's bytes round-trip:** `pack_inline_image(<original
   bytes>, "png")` produces the same `(data, ext)` pair that the build.py
   call carries.
3. **No policy → relative path emit (Phase A behaviour):** when
   `meta.yml::asset_policy` is absent, the converter emits a repo-relative
   path (e.g. `image='shared/assets/<slug>/test-asset.png'`), NEVER an
   absolute path starting with `/`.
4. **No policy → still no absolute paths anywhere:** assert the entire
   generated `build.py` text does not contain `/workspace/`, `/home/`,
   `/tmp/`, `/root/`, `file://`, or `[A-Z]:[\\/]`.
5. **First-PR forward-compat fallback:** with policy
   `embedded: [test-asset.png], shipped: []`, the converter inlines.
   (The non-embedded "should emit relative" branch is forward-compat for
   Phase D; document in a test docstring that it's unreachable in this PR
   because the audit catches unclassified before the converter runs.)

**GREEN — implement** the three edits in `tools/idml_to_dsl.py`:

**Edit 1 — `_Ctx` dataclass** (lines 677–716): add a new field:
```python
embedded_set: set[str] = field(default_factory=set)
```
Position it next to `asset_map: dict[str, str]` (line ~696 in current file)
for readability. Use `field(default_factory=set)` not `set()` (mutable default
trap).

**Edit 2 — `convert()` function** (lines 3081–3224): after the existing
`meta.yml`-derived setup (find the block that reads `template_id` or loads
existing build inputs), add:
```python
from sla_lib.builder.meta_schema import load_asset_policy
# (already imported elsewhere in idml_to_dsl.py; verify and re-use the import)

policy = load_asset_policy(template_id, root=ROOT)
if policy is not None:
    ctx.embedded_set = set(policy.get("embedded", []))
# When policy is None (no meta.yml or no asset_policy: block), embedded_set
# stays empty -> every emit takes the relative-path branch (Phase A safety net).
```

**Edit 3a — PDF/vector branch** (lines 1635–1664). Current code resolves
`mapped` to an absolute path. Replace with:
```python
if mapped:
    basename = Path(mapped).name
    abs_mapped = Path(mapped) if Path(mapped).is_absolute() else (ROOT / mapped)
    if basename in ctx.embedded_set:
        # Phase C: inline.
        from sla_lib.builder.primitives import pack_inline_image
        blob, ext_norm = pack_inline_image(
            abs_mapped.read_bytes(),
            abs_mapped.suffix.lstrip(".").lower(),
        )
        _emit_image_frame_call(
            out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
            image_path="",
            inline_data=blob, inline_ext=ext_norm,
            ctx=ctx,
            local_scale=pdf_local_scale, local_offset_pt=pdf_local_offset,
        )
    else:
        # Phase A: repo-relative emit (forward-compat for Phase D shipped:).
        try:
            rel = abs_mapped.relative_to(ROOT)
        except ValueError as exc:
            raise RuntimeError(
                f"Asset {abs_mapped} is outside repo root {ROOT}; "
                "refusing to emit absolute path (issue #39 Phase A)."
            ) from exc
        _emit_image_frame_call(
            out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
            image_path=str(rel).replace("\\", "/"),
            ctx=ctx,
            local_scale=pdf_local_scale, local_offset_pt=pdf_local_offset,
        )
```

**Edit 3b — asset-map raster branch** (lines 2128–2143). Same pattern, but
for the raster path (the actively-firing branch on v2-falzflyer). Mirror Edit
3a's structure exactly.

**Edit 3c — legacy `--assets-dir` raster branch** (lines 2157–2170). Same
pattern; drop the existing `str(asset_path.resolve())` fallback. If
`asset_path` is outside `ROOT`, raise `RuntimeError` — never emit absolute.

**REFACTOR — extract helper:**
After all three branches use the same logic, lift the inline-vs-relative
decision into a small helper at module level:
```python
def _emit_image_or_inline(
    out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
    *, abs_path: Path, ctx: _Ctx, local_scale=None, local_offset_pt=None,
) -> None:
    """Issue #39: emit inline_image_data when basename in embedded_set,
    else repo-relative path. Never emit absolute paths.
    Raises RuntimeError if abs_path is outside ROOT.
    """
    basename = abs_path.name
    if basename in ctx.embedded_set:
        from sla_lib.builder.primitives import pack_inline_image
        blob, ext_norm = pack_inline_image(
            abs_path.read_bytes(), abs_path.suffix.lstrip(".").lower()
        )
        _emit_image_frame_call(
            out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
            image_path="", inline_data=blob, inline_ext=ext_norm,
            ctx=ctx, local_scale=local_scale, local_offset_pt=local_offset_pt,
        )
        return
    try:
        rel = abs_path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"Asset {abs_path} outside repo root {ROOT}; refusing to emit "
            "absolute path (issue #39 Phase A)."
        ) from exc
    _emit_image_frame_call(
        out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
        image_path=str(rel).replace("\\", "/"),
        ctx=ctx, local_scale=local_scale, local_offset_pt=local_offset_pt,
    )
```
All three call sites then become a one-liner call to `_emit_image_or_inline`.

**Determinism note:** `pack_inline_image` uses `zlib.compress(..., 6)`. Per
pitfalls.md §12, Python stdlib zlib level 6 is deterministic for fixed input
bytes. Re-emitting the same source PNG produces a byte-identical inline blob.
This is what makes Task 5's "re-emit + commit" stable.

**Do NOT call `Path.resolve()` or `Path.absolute()` on asset paths anywhere
in this PR.** The helper above uses `ROOT / mapped` (for relative inputs)
and `Path(mapped)` (for already-absolute inputs); both preserve repo
locality. `Path.resolve()` rewrites through symlinks and the worktree's
`/workspace/.worktrees/.../shared` is exactly the surface that produced the
original bug.

**What NOT to do:**
- Do NOT touch `_emit_image_frame_call` (lines 2002–2065) — it already
  supports `inline_data`/`inline_ext` kwargs. Task 4 just CALLS it with those
  args populated.
- Do NOT modify `tools/sla_lib/builder/primitives.py`.
- Do NOT modify `tools/sla_lib/builder/meta_schema.py`.
- Do NOT change the converter's CLI surface (`--asset-map`, `--assets-dir`,
  `--allow-dropped-pageitems` flags remain unchanged).
- Do NOT bake the policy into the asset_map manifest — `meta.yml::asset_policy`
  is the only source of truth.
  </action>
  <verify>
  <automated>pytest tests/unit/test_idml_to_dsl_inline_embedding.py -q && python3 -m unittest discover tests/unit -q && python3 -m unittest discover tools/sla_lib/tests -q && pytest tests/ -q -k "idml_to_dsl or asset_policy or converter"</automated>
  </verify>
  <done>
  - `tools/idml_to_dsl.py` has a new `_Ctx.embedded_set: set[str]` field.
  - `convert()` populates `ctx.embedded_set` from `load_asset_policy(template_id, root=ROOT)`.
  - All 3 emit sites (lines 1635–1664, 2128–2143, 2157–2170) route through `_emit_image_or_inline`.
  - The helper emits `inline_data=blob, inline_ext=ext_norm` when basename ∈ `embedded_set`.
  - The helper emits a repo-relative path otherwise; raises `RuntimeError` if outside ROOT.
  - ZERO calls to `Path.resolve()` or `Path.absolute()` on asset paths remain in `idml_to_dsl.py` (`grep -nE "\.resolve\(\)|\.absolute\(\)" tools/idml_to_dsl.py | grep -i asset` returns empty).
  - `tests/unit/test_idml_to_dsl_inline_embedding.py` covers: embedded → inline, embedded → byte round-trip, no-policy → relative, no-policy → no absolute paths, first-PR forward-compat note.
  - `pytest tests/unit/test_idml_to_dsl_inline_embedding.py -q` passes.
  - `python3 -m unittest discover tests/unit -q` passes.
  - `python3 -m unittest discover tools/sla_lib/tests -q` passes (the existing converter test suite stays green).
  - At this task's end, the converter is patched but no template has been re-emitted yet — `tools/check_no_absolute_paths_in_sla.py` still fails on the committed v2-falzflyer SLA. Task 5 fixes that.
  </done>
</task>

<task type="auto">
  <name>Task 5: Re-emit v2-falzflyer with `bin/idml-import --reimport` (Phase F)</name>
  <files>templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py.generated, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-01-hires.png, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/page-02-hires.png, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml, templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/TOLERANCE_LOG.md, EXECUTION.md</files>
  <action>
**Goal:** Re-emit v2-falzflyer's `build.py` + `template.sla` so the SLA has 9
`isInlineImage="1"` PAGEOBJECTs and 0 absolute PFILEs. **Per
`feedback_fix_generator_not_artifact.md`: this is done by re-running the
converter (Task 4's fix), NEVER by hand-editing the SLA.**

**Pre-flight measurement (capture for EXECUTION.md):**
```bash
du -b templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla
cp templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf /tmp/preview-pre-39.pdf
pdffonts /tmp/preview-pre-39.pdf > /tmp/pdffonts-pre-39.txt
grep -c 'PFILE="/' templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla  # expect 9
grep -c 'isInlineImage="1"' templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla  # expect 0
```
Record the bytes-count + 9/0 baseline in EXECUTION.md.

**Locate the IDML source.** The IDML file lives at
`originals/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2.idml` (or
equivalent — verify via `meta.yml::build::source` and `find originals/ -name
'*leporello*' -type f`). If `originals/` is symlinked into the worktree (test
patterns rely on this), the symlink is set up by the executor's worktree
init.

**Run the re-import:**
```bash
bin/idml-import originals/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2.idml \
    --reimport \
    --non-interactive \
    --allow-composite-ai \
    --no-brand-fonts
```
Flags match the existing integration test invocation at
`tests/integration/test_idml_import_v2_falzflyer.py:63–73`.

**Verify after re-import (each `grep` MUST match the expected count):**
```bash
# 1. SLA has 9 inline images.
grep -c 'isInlineImage="1"' templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla
# Expected: 9

# 2. SLA has 0 absolute paths.
grep -cE 'PFILE="(/|file://|[A-Za-z]:[\\/])' templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla
# Expected: 0

# 3. build.py has 9 inline_image_data= calls.
grep -c 'inline_image_data=' templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py
# Expected: 9

# 4. build.py has 0 absolute path literals.
grep -cE "image='(/|file://|[A-Za-z]:[\\/])" templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py
# Expected: 0

# 5. Lint passes.
python3 tools/check_no_absolute_paths_in_sla.py
# Expected: exit 0
```

**Inject preservation (per pitfalls.md §4):** The v2 template has 13
hand-patches in `inject.yml`. The re-import flow auto-runs
`tools/reconcile_build_py.py`. After re-emission, run:
```bash
python3 tools/lint_inject_consistency.py
python3 tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2 --check
```
Both must exit 0. If either fails, STOP and fix the converter (Task 4) — do
NOT delete entries from `inject.yml` to make the check pass. The 13 inject
entries target ParaStyle / TextFrame / ImageFrame `scale_type` fields, none of
which conflict with Task 4's `inline_image_data=` additions. Per pitfalls.md
§4 item 4, the `u3e7` `scale_type=0` inject may now be marked "redundant" by
the reconciler — that warning is non-fatal; keep the inject entry for
audit-trail (do not remove).

**Render & preview check:**
```bash
bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit-strict
```
This regenerates `preview.pdf` + `page-01-hires.png` + `page-02-hires.png` and
runs the full audit chain (which now includes Task 1's asset_policy_audit
BEFORE A1). Exit code must be 0.

**Visual diff (per `feedback_font_fidelity_check.md`):**
```bash
# Font check first — never trust a preview diff without pdffonts.
pdffonts templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf > /tmp/pdffonts-post-39.txt
diff /tmp/pdffonts-pre-39.txt /tmp/pdffonts-post-39.txt
# Expected: identical (no font fallback regression).

# Raster diff (PPS similarity per page).
python3 tools/visual_diff.py \
    templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf \
    /tmp/preview-pre-39.pdf \
    --raster
# Document any non-byte-identical pages in EXECUTION.md per ISSUE.md F.3.
```

**Post-emission measurement (record in EXECUTION.md):**
```bash
du -b templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla
# Expected: ~18-40 MB (was ~58 KB; per pitfalls.md §2). Document the exact
# byte-delta so reviewers see the cost of the embed-everything decision.
```

Append a row to
`templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/TOLERANCE_LOG.md` of
kind `sla-size-bloat` recording the pre/post sizes per pitfalls.md §2.

**Update EXECUTION.md** (the artifact the executor writes during execution; if
it doesn't exist yet, create it at `.issues/39-.../EXECUTION.md`) with:
- Pre-emission SLA byte count, post-emission SLA byte count, delta.
- Pre-emission PFILE count (9 absolute), post-emission PFILE count (0 absolute, 9 empty + 9 inline).
- `pdffonts` diff result (expected: identical).
- `tools/visual_diff.py --raster` PPS per page (expected: ≥99.5%; document any drift).
- The full numbered checklist of commands run.

**Update `meta.yml::previews_for_sla` SHA.** The current SHA (per
`templates/<v2>/meta.yml`) is for the broken-absolute-path SLA. After
re-emission, regenerate the SHA via
`python3 tools/regen_previews_for_sla_sha.py kandidat-falzflyer-din-lang-gruenes-cover-v2`
(or whatever the existing tool name is — check `tools/` for the SHA-pinning
helper). If no such helper exists, compute manually:
```bash
python3 -c "import hashlib, pathlib; p = pathlib.Path('templates/kandidat-falzflyer-din-lang-gruenes-cover-v2'); h = hashlib.sha256((p/'preview.pdf').read_bytes()).hexdigest(); print(h)"
```
and update the SHA in `meta.yml::previews_for_sla`. Be transparent in
EXECUTION.md about which approach was used.

**What NOT to do:**
- Do NOT hand-edit `template.sla`. (`feedback_fix_generator_not_artifact.md`.)
- Do NOT hand-edit `build.py` to replace `image='/abs/path'` with
  `inline_image_data='...'`. Re-emit instead.
- Do NOT delete entries from `inject.yml` to make reconcile pass.
- Do NOT remove any of the 12 source files from `shared/assets/<idml-slug>/`.
- Do NOT mutate any other template's SLA (this PR touches v2-falzflyer
  ONLY).
- Do NOT bypass `--audit-strict` if `bin/render-gallery` fails. If the audit
  surfaces a drift, document it and decide explicitly: accept (with
  TOLERANCE_LOG row) or fix the converter (back to Task 4).
  </action>
  <verify>
  <automated>grep -c 'isInlineImage="1"' templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla | grep -q '^9$' && python3 tools/check_no_absolute_paths_in_sla.py && python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2 && python3 tools/lint_inject_consistency.py && python3 tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2 --check && bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit-strict</automated>
  </verify>
  <done>
  - `templates/<v2>/template.sla` has exactly 9 `isInlineImage="1"` PAGEOBJECTs.
  - `templates/<v2>/template.sla` has 0 absolute PFILE values (regex `^(/|file://|[A-Za-z]:[\\/])`).
  - `templates/<v2>/build.py` has 9 `inline_image_data=` ImageFrame calls and 0 absolute-path literals.
  - `tools/check_no_absolute_paths_in_sla.py` exits 0 against the repo.
  - `tools/asset_policy_audit.py --slug <v2>` exits 0.
  - `tools/lint_inject_consistency.py` exits 0.
  - `tools/reconcile_build_py.py <v2> --check` exits 0.
  - `bin/render-gallery <v2> --audit-strict` exits 0.
  - `pdffonts preview.pdf` is identical pre/post (no font fallback regression).
  - `meta.yml::previews_for_sla` SHA is updated to match the new `preview.pdf`.
  - `templates/<v2>/TOLERANCE_LOG.md` has a new `sla-size-bloat` row recording pre/post bytes.
  - EXECUTION.md documents the full re-emission sequence + measurements.
  - SLA never hand-edited (verified by reviewing the git diff: changes to `template.sla` only appear via re-emit-produced commit).
  </done>
</task>

<task type="auto">
  <name>Task 6: Reconcile `.claude/skills/idml-import/asset_policy.md` with CONTEXT.md</name>
  <files>.claude/skills/idml-import/asset_policy.md</files>
  <action>
**Goal:** The skill doc currently shows `plakat-dunkel-fuer-flyer.png` (and
possibly `green-pine-trees-covered-with-fog.jpg`) in `shipped:`. CONTEXT.md
locks the first-PR rule that ALL 12 v2-falzflyer assets go in `embedded:`
and `shipped:` MUST be empty. Without reconciling, future agents copy the
skill example, hit the audit's rejection, and reach for silent workarounds
(per pitfalls.md §1).

**Add a top-of-file banner** (above the existing content):
```markdown
> **Active rule (issue #39, first PR — landed):** all assets go in `embedded:`.
> The `shipped:` list MUST be empty in every committed `meta.yml::asset_policy`.
> The audit (`tools/asset_policy_audit.py`) rejects non-empty `shipped:` with
> a clear message pointing at this rule. The eventual `embedded:` / `shipped:`
> split described below becomes active in a follow-up PR after the brand-team
> decision on Phase D (zip) / Phase E (gallery flip) / Phase G (AI watermark).
> Until then, treat every example showing `shipped:` entries as
> "eventual; not yet active".
```

**Flip the v2-falzflyer migration recipe** (the section that currently shows
`plakat-dunkel-fuer-flyer.png` in `shipped:`). Replace the example with the
12-entry `embedded:` block from Task 3:
```yaml
asset_policy:
  embedded:
    - bluesky-weiss.png
    - green-pine-trees-covered-with-fog-crop.png
    - green-pine-trees-covered-with-fog-srgb.png
    - green-pine-trees-covered-with-fog.jpg
    - gruene-logo-bund-weiss-cmyk.png
    - mail-weiss.png
    - plakat-dunkel-fuer-flyer.png
    - social-media-icon-facebook.png
    - social-media-icon-instagram.png
    - social-media-icon-tiktok.png
    - social-media-icons-weiss.png
    - website-weiss.png
  shipped: []
```

**Mark every other `shipped:` example in the file** with a clear "eventual;
not yet active" comment so future readers don't accidentally use it. The
heuristic-classification table (`*logo*` → embed, `portrait*` → ship, etc.)
stays — it describes the EVENTUAL classification rule. Add a sentence under
the table: "Today (first PR), the `ship` column is empty; every heuristic
result lands in `embedded:`. The `ship` column becomes active when Phase D /
E / G lands."

**Always show `shipped: []` (empty list, present key)** in every example,
per pitfalls.md §15 (schema requires both keys; absent `shipped:` fails
schema validation BEFORE the audit's "must be empty" check).

**Cross-reference the audit tool:**
Add a "Related" section at the bottom (or extend an existing one) with:
- `tools/asset_policy_audit.py` — enforces this policy at build time.
- `tools/check_no_absolute_paths_in_sla.py` — Phase A guard.
- `shared/asset-policy.schema.yaml` — the schema (permissive on shipped:; audit enforces emptiness for first PR).
- Issue #39 / CONTEXT.md — single source of truth for the first-PR scope lock.

**Do NOT delete the eventual-state documentation.** Phase D/E/G follow-up
agents need to know what the eventual split looks like. The banner +
"eventual" markers preserve the doc as a transitional artifact.

**SKILL.md P11 audit:** Quickly verify
`.claude/skills/idml-import/SKILL.md`'s P11 entry (lines 210–215) is
consistent with the banner. If P11 still implies `shipped:` is active, add a
one-line note pointing at the banner in `asset_policy.md`. Do NOT rewrite
P11 — the principle's text describes the eventual rule, which is still
correct as the target state.

**What NOT to do:**
- Do NOT modify `shared/asset-policy.schema.yaml` (CONTEXT.md rule 2).
- Do NOT add AI-watermark documentation (Phase G is out of scope).
- Do NOT add zip-pipeline documentation (Phase D is out of scope).
- Do NOT remove the heuristic-classification table.
- Do NOT add "claude" anywhere (per `feedback_no_claude_attribution.md`).
  </action>
  <verify>
  <automated>grep -c "shipped: \[\]" .claude/skills/idml-import/asset_policy.md | awk '$1 > 0 {exit 0} {exit 1}' && ! grep -q "shipped:$" .claude/skills/idml-import/asset_policy.md && grep -q "Active rule (issue #39" .claude/skills/idml-import/asset_policy.md && grep -q "plakat-dunkel-fuer-flyer.png" .claude/skills/idml-import/asset_policy.md</automated>
  </verify>
  <done>
  - `.claude/skills/idml-import/asset_policy.md` has a top-of-file "Active rule (issue #39, first PR)" banner.
  - The v2-falzflyer migration recipe lists all 12 assets in `embedded:` and `shipped: []`.
  - Every example in the file shows `shipped: []` (empty list, present key) — no example shows `shipped:` followed by a newline-with-entries.
  - Every legacy example showing a non-empty `shipped:` is annotated "eventual; not yet active".
  - The heuristic-classification table stays, with a clarifying sentence about the first-PR rule.
  - A "Related" section cross-references `tools/asset_policy_audit.py`, `tools/check_no_absolute_paths_in_sla.py`, `shared/asset-policy.schema.yaml`, and CONTEXT.md.
  - `shared/asset-policy.schema.yaml` is unchanged.
  - `.claude/skills/idml-import/SKILL.md` P11 either stays unchanged or gains a one-line cross-reference; the principle text describing the eventual rule is preserved.
  - No mention of "claude" in any committed file.
  </done>
</task>

<task type="auto">
  <name>Task 7: End-to-end integration test — `bin/idml-import` on v2-falzflyer with inline embed</name>
  <files>tests/integration/test_idml_import_v2_falzflyer_inline.py</files>
  <action>
**Goal:** Lock in the end-to-end behaviour from Task 5. A future regression
that re-introduces absolute paths or silently drops inline embedding is
caught by CI, not by visual inspection of a downloaded SLA.

**Pattern:** model after the existing
`tests/integration/test_idml_import_v2_falzflyer.py` (which subprocess-spawns
`bin/idml-import` and asserts artifact existence + exit codes). Add a new
sibling file `tests/integration/test_idml_import_v2_falzflyer_inline.py`
that:

1. **Skips when originals are absent.** Use the existing skip-guard:
   ```python
   ORIGINALS = ROOT / "originals" / "26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2.idml"
   pytestmark = pytest.mark.skipif(not ORIGINALS.exists(), reason="originals/ not symlinked in this env")
   ```
2. **Runs the re-import** in a `tempfile.TemporaryDirectory()` copy of the
   relevant repo subtree (or via `tmp_path` and a clone of the worktree's
   `templates/<v2>/`, `shared/assets/<v2-asset-dir>/`, and the meta.yml +
   asset_policy block — pattern after `test_idml_import_v2_falzflyer.py`'s
   approach, do not invent a new fixture style).
3. **Asserts post-conditions:**
   - `subprocess.run(["bin/idml-import", ..., "--reimport", "--non-interactive", "--allow-composite-ai", "--no-brand-fonts"])` exit code == 0.
   - `build/<slug>/preflight.yml::ok == True` (parse the YAML; assert `ok=True`).
   - The re-emitted `template.sla` contains exactly 9 `isInlineImage="1"` substrings.
   - The re-emitted `template.sla` contains 0 `PFILE` values matching the absolute-path regex (re-use `tools.check_no_absolute_paths_in_sla.ABSOLUTE_PFILE_RE` import).
   - The re-emitted `build.py` contains 9 `inline_image_data=` substrings.
   - The re-emitted `build.py` contains 0 string literals matching `image='(/|file://|[A-Za-z]:[\\/])`.
4. **Sanity check on inline blob round-trip:** read one inline blob from the
   SLA, decode it via `tools.sla_lib.builder.primitives.unpack_inline_image`
   (or equivalent reverse helper — if no such function exists, decode
   inline manually: base64-decode, strip the 4-byte big-endian prefix,
   zlib-decompress, hash). Compare the hash to `sha256` of the on-disk
   source PNG. They MUST match (zlib determinism per pitfalls.md §12).

**Use the dual-runner verify pattern** (pytest + unittest) because CI runs
both. Place this test under `tests/integration/`, not `tools/sla_lib/tests/`,
to match the existing v2-falzflyer integration test's location.

**Mark it slow / network-free.** Add `@pytest.mark.integration` if the repo's
pytest config uses that marker (check `tests/conftest.py` and `pyproject.toml`
or `setup.cfg`). If no such marker exists, skip the decorator — the
skipif-on-originals guard is sufficient.

**Cleanup:** the test must NOT mutate the worktree's committed
`templates/<v2>/` files. All re-import work happens in a tmp dir; assertions
read tmp-dir artifacts.

**What NOT to do:**
- Do NOT call out to GitHub / network / cloud services.
- Do NOT depend on `bin/render-gallery` (it requires Scribus + pdftocairo;
  the existing `test_idml_import_v2_falzflyer.py` already covers that path
  with the skip guards in place). This new test focuses on `bin/idml-import`
  output specifically.
- Do NOT re-run the test in a loop or with random inputs.
- Do NOT modify any existing integration test.
  </action>
  <verify>
  <automated>pytest tests/integration/test_idml_import_v2_falzflyer_inline.py -q && python3 -m unittest discover tests/integration -q</automated>
  </verify>
  <done>
  - `tests/integration/test_idml_import_v2_falzflyer_inline.py` created.
  - Test skips cleanly when `originals/` is absent (so CI without IDMLs still runs).
  - Test asserts: `bin/idml-import` exit code 0; `preflight.yml::ok == True`; 9 inline images in SLA; 0 absolute PFILE; 9 `inline_image_data=` in build.py; 0 absolute-path literals in build.py.
  - Test asserts inline-blob round-trip: decoded inline data matches source PNG sha256.
  - `pytest tests/integration/test_idml_import_v2_falzflyer_inline.py -q` passes (or skips when originals absent).
  - `python3 -m unittest discover tests/integration -q` passes.
  - Existing `tests/integration/test_idml_import_v2_falzflyer.py` is unchanged.
  </done>
</task>

</tasks>

<verification>
After all 7 tasks land, run these aggregate checks in order. Each must exit 0.

```bash
# 1. Pre-commit hooks (covers Task 2 lint, sop_lint, reconcile-check, etc.)
pre-commit run --all-files

# 2. Full unit + integration test suite — both runners (pytest + unittest)
pytest tests/ -q
python3 -m unittest discover tests/unit -q
python3 -m unittest discover tests/integration -q
python3 -m unittest discover tools/sla_lib/tests -q

# 3. SOP gates (mirrors CI)
python3 tools/sop_lint.py
python3 tools/check_overrides_growth.py
python3 tools/lint_inject_consistency.py
python3 tools/reconcile_build_py.py kandidat-falzflyer-din-lang-gruenes-cover-v2 --check
python3 tools/check_no_absolute_paths_in_sla.py

# 4. Asset-policy audit on the only template with shared/assets today
python3 tools/asset_policy_audit.py --slug kandidat-falzflyer-din-lang-gruenes-cover-v2

# 5. End-to-end render with audit gate
bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2 --audit-strict

# 6. Lint surface for grep-bans (defensive — should yield zero results)
grep -rE 'PFILE="(/|file://|[A-Za-z]:[\\/])' templates/  # expect 0 hits
grep -nE "\.resolve\(\)|\.absolute\(\)" tools/idml_to_dsl.py | grep -iE "asset|image|mapped"  # expect 0 hits

# 7. Verify no 'claude' attribution anywhere new
git diff origin/main -- '*.py' '*.md' '*.yml' '*.yaml' | grep -i 'claude' | grep -v '^---' | grep -v '^+++'  # expect 0 hits in additions
```

CI (`.github/workflows/ci.yml`) automatically runs items 1, 3, 4 on every push.
Items 2, 5, 7 run in the dev container before pushing the PR.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria (Phase A + B + C + F only; D / E / G
are explicitly out of scope per CONTEXT.md).

**Phase A — Path canonicalisation (ISSUE.md lines 278–281):**
- [x] No committed `template.sla` contains an absolute filesystem path
      (`grep -cE 'PFILE="(/|file://|[A-Za-z]:[\\/])' templates/` returns 0). — Task 5.
- [x] `tools/check_no_absolute_paths_in_sla.py` fires in CI (pre-commit + SOP-gates step). — Task 2.
- [x] `tools/idml_to_dsl.py` never emits absolute paths (Task 4 helper raises
      `RuntimeError` if asset is outside ROOT; no `Path.resolve()` on asset paths). — Task 4.

**Phase B — Classification (ISSUE.md lines 283–289):**
- [x] `tools/asset_policy_audit.py` exists and wires into `_run_audit` BEFORE
      A1 inventory (positioned after `asset_extraction_audit`, before A1 — Task 1).
- [x] Schema validation rejects malformed `asset_policy:` blocks (via
      `load_asset_policy()` — already on main; this PR does NOT modify the schema).
- [x] `bin/idml-import` stops on unclassified assets and asks for user
      confirmation (Task 1 wires the audit into `_process_one` post line 458;
      hard-fail with `_MISSING_POLICY_MSG` / `_UNCLASSIFIED_MSG` / `_SHIPPED_REJECTED_MSG`).

**Phase C — Inline embedding (ISSUE.md lines 291–294):**
- [x] Embedded assets land via `ImageFrame(inline_image_data=...)` (Task 4
      `_emit_image_or_inline` helper).
- [x] Shipped assets emit `image='assets/<basename>'` — **DEFERRED** to Phase D
      follow-up. For first PR, `shipped:` is empty and the audit catches
      anything classified there; the converter's relative-path branch exists
      for forward compat but is unreachable in this PR.
- [x] Re-emission of an existing template is idempotent (Task 5 verifies via
      re-emit; zlib determinism per pitfalls.md §12 guarantees byte-identity).

**Phase F — v2-falzflyer (ISSUE.md lines 306–311, modified per CONTEXT.md):**
- [x] `meta.yml::asset_policy` authored correctly with 12 entries in
      `embedded:`, `shipped: []` (Task 3).
- [x] Re-emitted SLA has 9 inline brand assets (NOT 12 — only 9 are PFILE'd
      from the IDML; the other 3 are forward-compat entries) and 0 references
      to external paths (Task 5).
- [x] `<slug>.zip` exists — **N/A, Phase D out of scope.** The downloaded
      artifact is the bare `template.sla`, self-contained via inline embedding.
- [x] preview.pdf diff is byte-identical OR documented (Task 5 runs
      `tools/visual_diff.py --raster` + `pdffonts`, documents in EXECUTION.md).

**Cross-cutting (ISSUE.md lines 332–337, modified per CONTEXT.md + RESEARCH.md):**
- [x] All templates pass the new audit (v2-falzflyer passes after Task 3;
      the other 8 templates lack `shared/assets/<slug>/` and silent-skip per
      Task 1's audit logic — see pitfalls.md §11 for the rationale).
- [x] `bin/idml-import` end-to-end test re-imports v2-falzflyer and produces
      a working SLA (Task 7).

**Phases D / E / G — explicitly OUT OF SCOPE:**
- ZIP build pipeline (`tools/build_template_zip.py`) — deferred to follow-up PR.
- Gallery download flow flip — deferred.
- AI watermarking + schema oneOf extension + `ai_generated:` field — deferred.

**User directives encoded:**
- `shipped:` list empty in every committed `meta.yml::asset_policy` (Task 1 audit + Task 3 authoring).
- Schema stays permissive (Task 1 does NOT modify `shared/asset-policy.schema.yaml`; the audit enforces the transitional rule).
- "Fix the generator, not the artifact" (Task 4 patches the converter; Task 5 re-emits the SLA via automation, never hand-edits).
- "No `claude` in commits/code/files" (verbatim in `<commit_format>`; verification step 7 greps the diff).
</success_criteria>

<deliverables>
**New files (4):**
- `tools/asset_policy_audit.py` — the audit + cross-check (Task 1).
- `tools/check_no_absolute_paths_in_sla.py` — pre-commit + CI lint (Task 2).
- `tests/unit/test_asset_policy_audit.py` — 6-case audit coverage (Task 1).
- `tests/unit/test_check_no_absolute_paths_in_sla.py` — 8-case lint coverage (Task 2).
- `tests/unit/test_idml_to_dsl_inline_embedding.py` — 5-case inline embed test (Task 4).
- `tests/integration/test_idml_import_v2_falzflyer_inline.py` — e2e gate (Task 7).

**Modified files (8):**
- `tools/idml_to_dsl.py` — 3 emit sites + `_Ctx.embedded_set` + helper (Task 4).
- `tools/render_pipeline.py` — wire asset_policy_audit into `_run_audit` (Task 1).
- `tools/idml_import_driver.py` — wire asset_policy_audit into `_process_one` (Task 1).
- `.pre-commit-config.yaml` — add 5th SOP hook (Task 2).
- `.github/workflows/ci.yml` — add lint to SOP-gates step (Task 2).
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/meta.yml` — `asset_policy:` block (Task 3).
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py` — re-emitted (Task 5).
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py.generated` — re-emitted (Task 5).
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/template.sla` — re-emitted, 9 inline (Task 5).
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/preview.pdf` + `page-NN-hires.png` — re-rendered (Task 5).
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/TOLERANCE_LOG.md` — size-bloat row (Task 5).
- `.claude/skills/idml-import/asset_policy.md` — banner + reconciled examples (Task 6).
- `EXECUTION.md` (in `.issues/39-.../`) — re-emission measurements (Task 5).

**Unchanged (do NOT modify in this PR):**
- `shared/asset-policy.schema.yaml` (CONTEXT.md rule 2 — stays permissive).
- `tools/sla_lib/builder/meta_schema.py` (`load_asset_policy` is correct as-is).
- `tools/sla_lib/builder/primitives.py` (`pack_inline_image` + `ImageFrame` are correct as-is).
- `tools/asset_extraction_audit.py` (sibling, not extension).
- Any of the 8 templates other than `kandidat-falzflyer-din-lang-gruenes-cover-v2`.
- `inject.yml` (preserved by reconcile in Task 5; do NOT delete entries).
- `links_export.yml` (the audit walks the filesystem as truth; manifest stays as-is).

**Out of scope (deferred to follow-up PR after brand-team decision):**
- Phase D: `tools/build_template_zip.py`, zip packaging, `<slug>.zip` artifacts.
- Phase E: Gallery flip from bare SLA to zip download.
- Phase G: `tools/watermark_ai_image.py`, schema oneOf extension for
  `ai_generated:` objects, `KI-GENERIERT MUSS ERSETZT WERDEN` overlay.

**Commit sequence (7 commits, one per task, in dependency order):**
1. `39: feat(asset_policy_audit): coverage cross-check + shipped-empty rule`
2. `39: feat(check_no_absolute_paths_in_sla): pre-commit + CI lint`
3. `39: chore(v2-falzflyer): meta.yml asset_policy authoring`
4. `39: fix(idml_to_dsl): inline-embed assets listed in asset_policy::embedded`
5. `39: chore(v2-falzflyer): re-emit SLA with inline brand assets`
6. `39: docs(skill): reconcile asset_policy.md with CONTEXT.md`
7. `39: test(integration): bin/idml-import e2e on v2-falzflyer inline`
</deliverables>
