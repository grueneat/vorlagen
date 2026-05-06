---
issue: 4-restore-visual_diff-in-ci-by-provisioning-brand-fonts
phase: plan
generated: 2026-05-05
---

# PLAN — Local render pipeline that commits gallery artifacts; CI becomes pure shipper

## Executor briefing

You are persisting **Option B** ("CI as pure shipper") from issue #3's wrap-up: the maintainer renders all gallery artifacts locally in the dev container, commits them, and CI ships them unmodified. CI never invokes Scribus, never installs brand fonts, and never rasterises. The current `validate-reproductions` step shrinks to `sla_diff --strict` + a stale-preview hash gate.

**Five things change concretely:**

1. **New `bin/render-gallery`** — Python orchestrator (~250 LOC) that, per template directory under `templates/<id>/` with `meta.yml::original_sla`, runs `build.py` → `render_sla_to_pdf` → byte-scrubs PDF metadata → rasterises to `page-NN.png` at the meta-configured dpi → runs `sla_diff --strict` + `visual_diff` → updates `meta.yml::previews_for_sla` with the SLA's SHA256 → mirrors artifacts to `site/public/templates/<id>/`. Idempotent (running twice → no git diff).
2. **New `bin/check-stale-previews`** — Python preflight (mirrors `bin/check-fontsizes`'s shape) that hashes each committed `templates/<id>/template.sla` (or per-size SLA for plakat) and compares to `meta.yml::previews_for_sla`. Mismatch → exits 1 with a clear "run `bin/render-gallery` and commit" message. Hooked into `bin/validate` as a preflight AND into the CI workflow's validate step.
3. **`tools/gallery_build.py` becomes copy-only** — `render_pdf()` (lines 26-39) and `pdf_to_pngs()` (lines 42-49) are deleted. `process_template()` is refactored to glob committed `templates/<id>/preview.pdf` + `page-*.png`, fail loudly via `_fail_missing` helper if absent, copy to `site/public/templates/<id>/`, and write Astro frontmatter. Never calls xvfb/scribus/pdftoppm.
4. **`.github/workflows/pages.yml::Validate reproductions (sla_diff)`** — adds `python3 bin/check-stale-previews` as the first command in the `run:` block; drops the multi-line "TODO: restore visual_diff in CI" comment block (current lines 115-122) and replaces with a one-line pointer to `docs/render-fidelity.md`. No other workflow changes.
5. **All gallery artifacts regenerated via the new pipeline** — Phase 6 runs `bin/render-gallery` from a clean state to populate `templates/<id>/preview.pdf`, `page-NN.png` (zero-padded, 2 digits), `<code>.pdf` + `<code>-page-N.png` for plakat sizes, plus `meta.yml::previews_for_sla` hashes. Stale single-digit `templates/zeitung-a4-grun/page-{1..9}.png` are deleted by the pipeline; broken Zeitung frontmatter (currently lists 23 pages) resolves naturally to 14.

Plus durable plumbing:

- `tools/render_pipeline.py` (new library) — holds the helper functions used by `bin/render-gallery` (PDF metadata scrub, brand-font verifier, per-template orchestrator, meta.yml hash-line writer). The `bin/render-gallery` script is a 5-line shim that imports `main()`. Same pattern for `tools/check_stale_previews.py` ↔ `bin/check-stale-previews`. This makes the helpers unit-testable without invoking the bin shim.
- New unit tests under `tools/sla_lib/tests/`: `test_render_pipeline.py` (idempotency of `_scrub_pdf_metadata`, `_verify_brand_fonts` failure mode, meta.yml hash-line rewrite for str + dict), `test_check_stale_previews.py` (clean/stale/missing-field cases for non-family + family), `test_gallery_build_copy_only.py` (success path + `_fail_missing` invocations).
- `templates/postkarte-a6-kampagne/meta.yml` gets a new `preview_dpi: 100` field (overrides the default 50). RESEARCH.md §PNG DPI Recommendation: at 50 dpi, A6 rasterises to 243 px wide — below both the 360 px detail-thumbnail target and 560 px index-card target. Postcard at 100 dpi → 487 px wide, ~50 KB per page. Other templates use the default 50 dpi (zeitung A4 = 449 px, plakat A0 = 2342 px).
- `docs/render-fidelity.md` — new "Local-only rendering: why CI never renders templates" section; rewords "CI font provisioning" subsection from "tracked in follow-up issue" → "permanently out of scope (issue #4 D7)"; adds "Maintainer workflow" section (edit → render-gallery → review → commit → push).
- `shared/fonts/README.md` — minor wording at end of "Container-Install" clarifying this is the *only* path that produces gallery artifacts (no CI fallback).

**Read first, in order:**

1. `.issues/4-restore-visual_diff-in-ci-by-provisioning-brand-fonts/ISSUE.md` — eleven acceptance criteria.
2. `.issues/4-restore-visual_diff-in-ci-by-provisioning-brand-fonts/CONTEXT.md` — D1–D9 locked decisions (non-negotiable).
3. `.issues/4-restore-visual_diff-in-ci-by-provisioning-brand-fonts/RESEARCH.md` — 936 lines, exhaustive codebase trace + empirically-validated idempotency strategy; authoritative for paths, line numbers, and byte-scrub regexes.

**Load-bearing source (do not rewrite, only edit listed regions):**

- `tools/visual_diff.py` — `render_sla_to_pdf(sla_path, pdf_path)` and `rasterise(pdf_path, prefix, dpi)` are imported by the new pipeline. Do NOT modify these functions.
- `tools/gallery_build.py` (currently 137 lines) — heavy refactor in Phase 4. Lines 26-49 deleted; lines 52-108 (`process_template`) replaced with copy-only logic; lines 111-132 (`main`) untouched.
- `bin/validate` (81 lines) — extend with one preflight invocation between current lines 30 and 32 (after `check-fontsizes` preflight, before per-template loop). No other changes.
- `bin/check-fontsizes` (79 lines) — read as the canonical Python-bin-script pattern. Do NOT modify.
- `.github/workflows/pages.yml::Validate reproductions (sla_diff)` (lines 93-123) — surgically add one preflight command + 2-line comment, remove the 9-line TODO block. No other workflow changes.
- `templates/<id>/meta.yml` for all three real templates — gain top-level `previews_for_sla:` field (string for postkarte/zeitung, dict-of-string for plakat). `preview_dpi:` added to postkarte-a6-kampagne only.
- `templates/<id>/template.sla` — committed; the new pipeline regenerates it via `python3 templates/<id>/build.py` at the start of each render. Build.py is byte-deterministic (PR #5 verified).
- `templates/plakat-a1-hochformat/{a0,a1,a2,a3}.sla` — committed inputs, NOT regenerated by build.py (RESEARCH.md §Potential Conflicts). Treated as committed inputs by the pipeline; rendered/copied per-size exactly as `gallery_build.py::process_template` does today in the `is_family` branch.
- `templates/<id>/baseline.pdf` — frozen visual_diff reference. **DO NOT TOUCH.**
- `tools/_export_pdf.py`, `tools/sla_diff.py`, `tools/sla_lib/`, `Dockerfile.claude`, `shared/fonts/50-vollkorn-family-alias.conf` — invoked unchanged.

**Resolutions for RESEARCH.md's 8 open questions** (do not re-surface — bake in):

1. **Pipeline language:** Python (matches `tools/` and meets the YAML R/W + import-`render_sla_to_pdf` requirements). ~200-250 LOC.
2. **Idempotency strategy:** option (a) — strip the `/CreationDate` + `/ModDate` PDF Info-dict fields and the trailer `/ID` array via the regex byte-scrub the researcher empirically validated (RESEARCH.md §Idempotency Strategy/Empirical results). Apply the scrub to the produced PDF before committing.
3. **Hash strategy for stale-preview:** SHA256 of raw `templates/<id>/template.sla` bytes (the direct upstream of `preview.pdf`). Plain hash, no SLA-normalisation. For plakat: per-size SHA256 of `<code>.sla`.
4. **Hash placement in meta.yml:** top-level `previews_for_sla:` field — string for single-page templates (postkarte, zeitung); dict-of-`{<size_code>: <hash>}` for plakat (the family case with multiple sizes).
5. **Per-template preview dpi:** introduce `preview_dpi:` field in `templates/<id>/meta.yml`. Default = 50. Override = 100 for `postkarte-a6-kampagne` only. Plakat A1 + Zeitung A4 use the default 50.
6. **Plakat per-size PNG naming:** each size gets `<code>-page-N.png` (matches the existing `gallery_build.py::process_template` family-branch glob `{code}-page-*.png`). Each size also gets `<code>.pdf` (already committed). The hash field becomes `previews_for_sla: {a0: <hash>, a1: <hash>, a2: <hash>, a3: <hash>}`. **Migration:** existing committed `a{0..3}-preview-1.png` files get renamed (delete-and-regenerate) to `a{0..3}-page-1.png`.
7. **Page-number padding:** ALWAYS zero-pad to 2 digits regardless of page count (`page-01.png`...`page-14.png`). pdftoppm pads to 2 digits when total pages > 9; for ≤9 pages, the new pipeline post-renames `page-N.png` → `page-0N.png`. Existing single-digit `page-{1..9}.png` relics in zeitung-a4-grun get cleaned up by the new pipeline (deleted before rasterising).
8. **`bin/check-stale-previews` invocation in CI:** call it directly as the first command in `.github/workflows/pages.yml::Validate reproductions (sla_diff)`'s `run:` block (BEFORE the per-template `sla_diff` loop). Direct invocation is the cleanest shape; mirrors `bin/check-fontsizes` use pattern. Also wire into `bin/validate` as a preflight (between `check-fontsizes` and the per-template loop) so local runs gate on it too.

**Honour without restating:**

- D1 — single render path: dev container's local pipeline.
- D2 — `bin/render-gallery` is the pipeline entry point; per-template loop with the 6 steps in CONTEXT.md plus the meta.yml hash update.
- D3 — preview PNG dpi 50 default; postcard override 100 (per resolution 5).
- D4 — `tools/gallery_build.py` becomes copy-only; never calls Scribus or pdftoppm.
- D5 — `bin/check-stale-previews` is a CI gate (and a `bin/validate` preflight).
- D6 — `.github/workflows/pages.yml::validate-reproductions` simplification: add stale-previews check, drop the multi-line TODO comment.
- D7 — CI font provisioning is permanently out of scope.
- D8 — `bin/validate` keeps doing visual_diff locally (unchanged behaviour aside from the new preflight call).
- D9 — maintainer workflow: edit → `bin/render-gallery` → review → commit → push.

**Constraints (CONTEXT.md):**

- Do NOT edit `*-original.sla` files at workspace root — issue #3 established those as canonical input.
- Do NOT regress the `bin/validate` 0-px standard from PR #7. After `bin/render-gallery` runs, all 17 pages must still be byte-equivalent to the user's reference Scribus 1.6.4 exports.
- Do NOT remove existing tests. PR #7's 136-test baseline stays green; add new tests for the new components.
- Do NOT touch `templates/<id>/baseline.pdf` (frozen visual_diff reference).
- Do NOT touch `Dockerfile.claude` or `shared/fonts/50-vollkorn-family-alias.conf` (issue #3 plumbing; out of scope here).
- No AI-tool attribution anywhere (commits, code, file names — per `feedback_no_claude_attribution.md` in user memory).

**Commit format** (per `.issues/config.yaml::commits.format=conventional`, `prefix=true`): Conventional commits with numeric issue-id prefix. Examples:
- `4: feat(pipeline): add bin/render-gallery local orchestrator`
- `4: refactor(gallery): make tools/gallery_build.py copy-only`
- `4: feat(ci): hook bin/check-stale-previews into validate-reproductions`
- `4: docs(render): document local-only rendering architecture`

## Reusable verification helpers

These are referenced by name from individual tasks. The executor copies them inline.

<helper id="render_twice_byte_compare">
Verify that two consecutive runs of the pipeline on the same source produce zero git diff.

```bash
TID="$1"
git status --porcelain templates/$TID/ | wc -l > /tmp/before.cnt
bin/render-gallery "$TID"
A=$(sha256sum templates/$TID/*.pdf | sort | sha256sum)
bin/render-gallery "$TID"
B=$(sha256sum templates/$TID/*.pdf | sort | sha256sum)
[ "$A" = "$B" ] && echo "IDEMPOTENT" || { echo "DRIFT" >&2; exit 1; }
git diff templates/$TID/ | head -40
[ -z "$(git diff templates/$TID/)" ] && echo "ZERO DIFF" || { echo "GIT DRIFT" >&2; exit 1; }
```
</helper>

<helper id="render_sla_to_pdf_smoke">
Smoke-test that `_scrub_pdf_metadata` produces byte-identical PDFs across two real Scribus renders.

```bash
python3 - <<'PY'
import sys, hashlib, tempfile
from pathlib import Path
sys.path.insert(0, "tools")
from visual_diff import render_sla_to_pdf
from render_pipeline import _scrub_pdf_metadata

sla = Path("templates/postkarte-a6-kampagne/template.sla")
with tempfile.TemporaryDirectory() as td:
    p1, p2 = Path(td)/"r1.pdf", Path(td)/"r2.pdf"
    render_sla_to_pdf(sla, p1); _scrub_pdf_metadata(p1)
    render_sla_to_pdf(sla, p2); _scrub_pdf_metadata(p2)
    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2, f"DRIFT after scrub: {h1} != {h2}"
    print(f"IDEMPOTENT: sha256={h1}")
PY
```
</helper>

<helper id="reference_pdf_byte_compare">
Confirm regenerated `preview.pdf` (or per-size `.pdf` for plakat) byte-equivalences the user's reference PDFs in `/root/workspace/originals/` at 0% fuzz raster comparison. Used by Phase 6 regression gate and Phase 9 final check.

```bash
mkdir -p "$OUT_DIR"
for pair in \
    "templates/zeitung-a4-grun/preview.pdf:/root/workspace/originals/Grüne Zeitung Vorlage Scribus.pdf:zeitung" \
    "templates/postkarte-a6-kampagne/preview.pdf:/root/workspace/originals/Postkarte Vorlage.pdf:postkarte" \
    "templates/plakat-a1-hochformat/a1.pdf:/root/workspace/originals/Plakat A1 Hochformat_Vorlage.pdf:plakat-a1"; do
  IFS=":" read -r ours theirs tag <<< "$pair"
  out="$OUT_DIR/$tag"; mkdir -p "$out"
  pdftoppm -r 96 -png "$ours" "$out/ours"
  pdftoppm -r 96 -png "$theirs" "$out/theirs"
  worst=0
  for f in "$out"/theirs-*.png; do
    page=${f##*/theirs-}
    diff_count=$(compare -metric AE -fuzz 0% "$f" "$out/ours-$page" "$out/diff-$page" 2>&1 || true)
    echo "$tag page-$page: $diff_count px"
    [ "$diff_count" -gt "$worst" ] 2>/dev/null && worst=$diff_count
  done
  echo "$tag worst-page mismatch: $worst px"
done
```

Set `OUT_DIR=build/phase6-regression` for Phase 6, `OUT_DIR=build/phase9-final` for Phase 9. Expect 0 px on every page across all 17 pages (zeitung 14 + postkarte 2 + plakat-A1 1).
</helper>

## Phase gates summary

| Phase | Goal | Gate (must be GREEN to advance) |
|---|---|---|
| 0 | Pipeline skeleton + helper module + PDF metadata scrub | helper `render_sla_to_pdf_smoke` reports IDEMPOTENT; `bin/render-gallery --help` works; `_scrub_pdf_metadata` unit tests pass; ≥146 unit tests total. |
| 1 | Per-template orchestrator (non-family + family); 50-dpi PNG; zero-padded names; stale-file cleanup | `bin/render-gallery` succeeds for all 3 templates; helper `render_twice_byte_compare` IDEMPOTENT for postkarte AND zeitung AND plakat; old single-digit `page-N.png` and `<code>-preview-N.png` relics deleted; `git diff` after second run = empty. |
| 2 | `previews_for_sla:` hash field handling + postcard `preview_dpi: 100` | All 3 meta.yml have correct-shape `previews_for_sla` (str/dict); postcard meta has `preview_dpi: 100`; postcard PNGs ~487 px wide; second pipeline run = no meta.yml diff. |
| 3 | `bin/check-stale-previews` + `bin/validate` preflight wiring | Clean state → exit 0; 3 synthetic stale states (non-family hash mismatch, family per-size hash mismatch, missing field) → exit 1 with template-specific message; `bin/validate` invokes preflight; ≥153 unit tests. |
| 4 | `tools/gallery_build.py` copy-only refactor | `render_pdf` and `pdf_to_pngs` deleted; `process_template` is copy-only with `_fail_missing` helper; runs cleanly without xvfb/scribus on PATH; ≥159 unit tests; existing 136 baseline still green. |
| 5 | `.github/workflows/pages.yml` simplification | Workflow YAML parses; `bin/check-stale-previews` invoked at top of `Validate reproductions` step; multi-line TODO comment dropped; deploy + setup steps untouched. |
| 6 | Regenerate ALL gallery artifacts via the new pipeline + regression check vs PR #7's 0-px standard | helper `reference_pdf_byte_compare` reports 0 px on all 17 pages; `bin/render-gallery` second run = no git diff; `bin/validate` exits 0; stale single-digit relics cleaned up. |
| 7 | `docs/render-fidelity.md` + `shared/fonts/README.md` updates | "Local-only rendering" + "Maintainer workflow" sections present; "permanently out of scope" wording in place; cross-links resolve. |
| 8 | End-to-end demo (synthetic edit → render → validate → revert) | Local demo green; clean state restored after revert; push procedure documented in EXECUTION.md. |
| 9 | Final verification — all 11 acceptance criteria | All AC checks pass; ≥159 tests OK; 0-px regression check on all 17 pages; `bin/validate` + `bin/check-stale-previews` exit 0; `bin/render-gallery` second run = no git diff. |

Each phase's tasks are below. **Do not advance past a phase whose gate is red.** `risk="high"` tasks need explicit verification before marking done.

## Phases

<phase id="0" name="Pipeline skeleton + PDF metadata scrub helper">

Stand up the orchestrator's spine before fleshing out per-template logic. The byte-scrub function is the highest-risk piece of the whole issue (RESEARCH.md §Idempotency Strategy/Empirical results validates it works, but the production implementation must match the verified regex exactly). Verify on one template (postkarte) before the per-template loop in Phase 1.

**RESEARCH.md anchors:** §Idempotency Strategy (lines 298-360, including empirically-derived regexes), §Pipeline Orchestration Shape (lines 214-296, including a code sketch), §Interfaces (lines 88-180).

<task id="0.1" name="Create tools/render_pipeline.py with helper functions" risk="high">
**Files:** `tools/render_pipeline.py` (new, ~120 LOC at this stage; will grow in Phase 1).

**Action:** Create the importable library that `bin/render-gallery` will shim. Implement these functions following the sketch at RESEARCH.md lines 247-296:

- Module top: `#!/usr/bin/env python3` shebang; docstring explaining role; imports (`argparse, hashlib, os, re, subprocess, sys`, `pathlib.Path`, `yaml`); module constants `ROOT = Path(__file__).resolve().parent.parent`, `DEFAULT_DPI = 50`, `EPOCH_DATE = b"D:20000101000000Z"`, `FIXED_PDF_ID = b"00000000000000000000000000000000"`.
- `sys.path.insert(0, str(ROOT / "tools"))`; `from visual_diff import render_sla_to_pdf, rasterise`.
- `_scrub_pdf_metadata(p: Path) -> None` — replace the three non-deterministic PDF artifacts with fixed length-preserving values. Use these three regex substitutions on `p.read_bytes()` then `p.write_bytes(data)`:
  - `re.sub(rb"/CreationDate \(D:\d{14}Z\)", b"/CreationDate (" + EPOCH_DATE + b")", data)`
  - `re.sub(rb"/ModDate \(D:\d{14}Z\)", b"/ModDate (" + EPOCH_DATE + b")", data)`
  - `re.sub(rb"/ID \[<[0-9A-Fa-f]{32}><[0-9A-Fa-f]{32}>\]", b"/ID [<" + FIXED_PDF_ID + b"><" + FIXED_PDF_ID + b">]", data)`
- `_verify_brand_fonts() -> None` — runs `subprocess.run(["fc-list"], capture_output=True, text=True, check=True)`, counts lines matching `r"gotham narrow|vollkorn"` case-insensitively. If `< 5`, `sys.exit(...)` with the FATAL message from RESEARCH.md lines 286-291 (mentions DejaVu fallback refusal + `shared/fonts/README.md`).
- `_sha256_of(p: Path) -> str` — `hashlib.sha256(p.read_bytes()).hexdigest()`.
- `_update_meta_hash(meta_path: Path, value) -> None` — regex line-replace for `previews_for_sla:`. If `value` is `str`, build single-line block `f"previews_for_sla: {value}"`. If `dict`, build multi-line YAML mapping (`previews_for_sla:` then `  <code>: <hash>` per sorted key). If field exists, replace via `re.sub(r"^previews_for_sla:.*?(?=^\S|\Z)", block + "\n", text, flags=re.M | re.S)`. If absent, insert below `original_sla:` line via `re.sub(r"^(original_sla:.*)$", r"\1\n" + block, text, count=1, flags=re.M)`. Bypass `yaml.safe_dump` to avoid key reordering / comment loss.
- `_read_template_meta(tdir: Path) -> dict` — `yaml.safe_load((tdir / "meta.yml").read_text(encoding="utf-8"))`.
- `_orchestrate_template(tdir, args) -> int` — stub raising `NotImplementedError("filled in Phase 1")`.
- `main(argv=None) -> int` — argparse with optional positional `template_id`, `--skip-visual-diff` (action="store_true"), `--dry-run`. Calls `_verify_brand_fonts()` first. Iterates `templates/*/` (single-template if `template_id` arg given), skipping dirs without `meta.yml` or without `original_sla`. Calls `_orchestrate_template(tdir, args)` per template; tracks per-template return codes; final exit is non-zero if any template failed.
- `if __name__ == "__main__": sys.exit(main())`.

**Verify:**
- `python3 -c "import sys; sys.path.insert(0, 'tools'); import render_pipeline; print(render_pipeline.DEFAULT_DPI)"` prints `50`.
- helper `render_sla_to_pdf_smoke` reports `IDEMPOTENT: sha256=...`.
- `python3 tools/render_pipeline.py --help` prints argparse usage.

**Done:**
- `tools/render_pipeline.py` exists with the 6 helpers + `main()` skeleton.
- `_scrub_pdf_metadata` empirically produces byte-identical PDFs across two real Scribus renders.
- `_verify_brand_fonts` exits cleanly in the running dev container (≥17 brand-font faces present per RESEARCH.md sources).
</task>

<task id="0.2" name="Create bin/render-gallery shim">
**Files:** `bin/render-gallery` (new, executable, ~10 lines).

**Action:** Five-line Python shim:

```python
#!/usr/bin/env python3
"""bin/render-gallery — local render pipeline (issue #4 entry point).

See tools/render_pipeline.py for implementation. This shim keeps the
helpers unit-testable from tools/sla_lib/tests/.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from render_pipeline import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`chmod +x bin/render-gallery`.

**Verify:**
- `bin/render-gallery --help` prints argparse usage.
- `bin/render-gallery nonexistent-template` exits non-zero with "no such template directory:".
- `bin/render-gallery postkarte-a6-kampagne` raises `NotImplementedError` (expected at this phase; Phase 1 fills `_orchestrate_template`).

**Done:**
- `bin/render-gallery` exists, executable bit set, `--help` works, shim correctly forwards to `tools/render_pipeline.main`.
</task>

<task id="0.3" name="Add tools/sla_lib/tests/test_render_pipeline.py with byte-scrub idempotency tests" risk="high">
**Files:** `tools/sla_lib/tests/test_render_pipeline.py` (new).

**Action:** Three test classes, all Scribus-free (operate on hand-crafted PDF byte strings). Mirror the `unittest.TestCase` pattern from existing `tools/sla_lib/tests/test_*.py`. Add `sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))` at module top.

- `ScrubPdfMetadataTests` — fixture method `_make_pdf_with_metadata(p, ts, idhex)` writes a hand-crafted minimal PDF byte string containing `/CreationDate (D:{ts}Z)`, `/ModDate (D:{ts}Z)`, `/ID [<{idhex}><{idhex}>]`. Tests:
  - `test_scrub_replaces_creation_and_mod_date` — after scrub, both timestamps are `EPOCH_DATE`; original timestamp string absent.
  - `test_scrub_replaces_trailer_id` — after scrub, `/ID` array is `FIXED_PDF_ID` × 2.
  - `test_scrub_is_idempotent` — running twice produces same bytes; running on already-scrubbed PDF is a no-op.
  - `test_scrub_is_length_preserving` — `len(p.read_bytes())` unchanged after scrub (xref offsets depend on this).
- `UpdateMetaHashTests` — fixture method `_meta_with(*, has_field, family=False)` builds a synthetic meta.yml string. Tests:
  - `test_inserts_below_original_sla_when_missing` — string-form value, no existing field; verify `previews_for_sla:` line directly follows `original_sla:` line.
  - `test_replaces_existing_str_value` — overwrites in place; old hash absent from text.
  - `test_writes_dict_for_family` — passes `{"a0": "1"*64, "a1": "2"*64}`; verify multi-line YAML mapping written; `ci_overrides:` and other keys still present.
  - `test_does_not_disturb_unrelated_lines` — every line from original input still appears in output.
- `Sha256OfTests` — `test_known_hash` — write `b"hello\n"` to a file, assert SHA256 matches `5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03`.

Total ≥10 tests.

**Verify:**
- `python3 -m unittest tools.sla_lib.tests.test_render_pipeline -v` passes all tests.
- `python3 -m unittest discover tools/sla_lib/tests` reports ≥146 tests, OK.

**Done:**
- ≥10 unit tests covering scrub idempotency, length preservation, hash field insertion/replacement (str + dict), unrelated-line preservation, sha256.
- Test discovery shows ≥146 tests OK.
</task>

<gate>
- helper `render_sla_to_pdf_smoke` reports IDEMPOTENT.
- `bin/render-gallery --help` prints argparse usage; `bin/render-gallery postkarte-a6-kampagne` exits with `NotImplementedError`.
- `python3 -m unittest discover tools/sla_lib/tests` reports ≥146 tests, OK.
</gate>

</phase>

<phase id="1" name="Per-template orchestrator + 50-dpi PNG + plakat per-size">

Fill in `_orchestrate_template`. Per-template flow per CONTEXT.md D2 + RESEARCH.md §Pipeline Orchestration Shape: build → render → scrub → rasterise → sla_diff → visual_diff → hash → mirror.

The plakat (family) branch needs special handling: 4 size SLAs (`a0.sla`...`a3.sla`) are committed inputs (NOT regenerated by build.py per RESEARCH.md §Potential Conflicts), each gets its own `<code>.pdf`, single PNG `<code>-page-1.png`, and per-size hash entry in `meta.yml::previews_for_sla`.

**RESEARCH.md anchors:** §Pipeline Orchestration Shape (lines 214-296), §Potential Conflicts (lines 190-204) for plakat per-size + pdftoppm padding, §Open Questions 5 (clean stale previews) and 7 (idempotency check), §gallery_build.py Refactor function-by-function (lines 432-590) for the family-branch shape.

<task id="1.1" name="Implement non-family branch of _orchestrate_template (postkarte, zeitung)" risk="high">
**Files:** `tools/render_pipeline.py` (replace `NotImplementedError` body with full implementation; add helper functions).

**Action:** Replace `_orchestrate_template` with a dispatcher (calls `_orchestrate_single` if `meta.get("type") != "family"`, else `_orchestrate_family`). Implement these new helpers in the same module:

- `_orchestrate_template(tdir, args)`:
  1. Read meta via `_read_template_meta(tdir)`; resolve `tid = meta["id"]`, `is_family = meta.get("type") == "family"`.
  2. Compute `site_public_dir = ROOT / "site" / "public" / "templates" / tid`; `mkdir(parents=True, exist_ok=True)`.
  3. Run `python3 templates/<id>/build.py` via `subprocess.run` with `check=True`, `cwd=str(ROOT)`, env including `PYTHONIOENCODING=utf-8`, `LC_ALL=C.UTF-8`, `LANG=C.UTF-8` (mirrors the encoding env in `tools/visual_diff.py::render_sla_to_pdf`).
  4. Dispatch: `_orchestrate_single(tdir, meta, site_public_dir, args)` or `_orchestrate_family(...)`. Return its exit code.

- `_orchestrate_single(tdir, meta, public_dir, args) -> int`:
  1. Resolve `template_sla = tdir / "template.sla"`, `preview_pdf = tdir / "preview.pdf"`.
  2. Call `render_sla_to_pdf(template_sla, preview_pdf)` (imported from `visual_diff`).
  3. Call `_scrub_pdf_metadata(preview_pdf)`.
  4. Read `dpi = int(meta.get("preview_dpi", DEFAULT_DPI))`.
  5. Clean stale `for stale in tdir.glob("page-*.png"): stale.unlink()`.
  6. Call `rasterise(preview_pdf, tdir / "page", dpi)`.
  7. Call `_zero_pad_pngs(tdir, prefix="page")` (helper below).
  8. Run sla_diff via `_run_sla_diff_strict(tid, tdir, meta)`; on non-zero return, propagate.
  9. If not `args.skip_visual_diff`, run visual_diff via `_run_visual_diff(tid, tdir, meta)`; propagate.
  10. If not `args.dry_run`, compute `h = _sha256_of(template_sla)` and `_update_meta_hash(tdir / "meta.yml", h)`.
  11. If not `args.dry_run`, call `_mirror_to_site_public(tdir, public_dir, family=False)`.
  12. Print summary line; `return 0`.

- `_zero_pad_pngs(tdir, prefix)` — for each `tdir.glob(f"{prefix}-?.png")` (single-digit suffix), rename to `{prefix}-0{N}.png` if target doesn't exist. Forces consistent 2-digit padding when pdftoppm produces single-digit names (≤9 pages).

- `_run_sla_diff_strict(tid, tdir, meta) -> int` — resolve `original_abs = (tdir / meta["original_sla"]).resolve()`. `subprocess.run(["python3", str(ROOT/"tools/sla_diff.py"), "--left", str(original_abs), "--right", str(tdir/"template.sla"), "--strict"], capture_output=True, text=True)`. On non-zero, write stdout/stderr to sys.stderr with `[<tid>] sla_diff FAILED:` prefix. Return `r.returncode`.

- `_run_visual_diff(tid, tdir, meta) -> int` — if `baseline.pdf` and `diff.yml` exist in `tdir`, run `python3 tools/visual_diff.py <template_sla> --baseline <baseline> --tolerance <diff.yml> --dpi 150 --out build/validation/<tid>/`. Same error-propagation pattern. Return 0 if files missing (skip).

- `_mirror_to_site_public(tdir, public_dir, *, family)` — wipe regular files in `public_dir` (don't touch subdirs); recreate. For non-family: copy `template.sla`, `preview.pdf`, all `page-*.png`. For family: copy `*.sla`, `*.pdf`, `*-page-*.png` files. Use `shutil.copy`.

**Verify:**
- `bin/render-gallery postkarte-a6-kampagne` exits 0 and produces:
  - `templates/postkarte-a6-kampagne/preview.pdf` (~1.2 MB).
  - `templates/postkarte-a6-kampagne/page-01.png`, `page-02.png` (postcard has 2 pages).
  - `meta.yml::previews_for_sla` updated with 64-char hex SHA256.
  - `site/public/templates/postkarte-a6-kampagne/{template.sla, preview.pdf, page-01.png, page-02.png}`.
- `bin/render-gallery zeitung-a4-grun` exits 0; produces `preview.pdf` + 14 PNGs `page-01.png` ... `page-14.png` (zero-padded); old `page-1.png` ... `page-9.png` deleted (verify via `git status`); meta.yml updated.
- helper `render_twice_byte_compare postkarte-a6-kampagne` reports IDEMPOTENT + ZERO DIFF.
- helper `render_twice_byte_compare zeitung-a4-grun` reports IDEMPOTENT + ZERO DIFF.

**Done:**
- Non-family branch fully implemented.
- 50/100 dpi honoured per-template (via meta.yml lookup).
- Zero-padded `page-NN.png` consistent across both templates.
- Idempotency verified via second-run-no-diff.
</task>

<task id="1.2" name="Implement family branch (plakat per-size)" risk="high">
**Files:** `tools/render_pipeline.py` (add `_orchestrate_family` function).

**Action:** Plakat is structurally different: 4 committed `<code>.sla` files (a0..a3), each rendered to its own `<code>.pdf`, single page → `<code>-page-1.png`, and 4 hashes recorded under `previews_for_sla` as a dict.

`_orchestrate_family(tdir, meta, public_dir, args) -> int`:

1. Read `sizes = meta.get("sizes", [])`. If empty, exit 1 with error.
2. Read `dpi = int(meta.get("preview_dpi", DEFAULT_DPI))`.
3. Clean stale per-size PNGs: delete `tdir.glob("*-preview-*.png")` (old hand-named relics) AND `tdir.glob("*-page-*.png")` (current names).
4. Initialise `hashes: dict[str, str] = {}`.
5. For each `size` in `sizes`:
   - Resolve `code = size["code"]`, `sla = tdir / f"{code}.sla"`, `pdf = tdir / f"{code}.pdf"`.
   - If `sla` doesn't exist, write error to stderr and return 1.
   - Call `render_sla_to_pdf(sla, pdf)`.
   - Call `_scrub_pdf_metadata(pdf)`.
   - Call `rasterise(pdf, tdir / f"{code}-page", dpi)`.
   - Call `_zero_pad_pngs(tdir, prefix=f"{code}-page")` (single-page, but apply for consistency).
   - Record `hashes[code] = _sha256_of(sla)`.
6. Run sla_diff via `_run_sla_diff_strict(tid, tdir, meta)` (fires against `template.sla` ↔ `original_sla` — same as non-family).
7. If not `args.skip_visual_diff`, run visual_diff via `_run_visual_diff(...)` (fires against `baseline.pdf` which is `template.sla`-rendered, NOT per-size).
8. If not `args.dry_run`, `_update_meta_hash(tdir / "meta.yml", hashes)` (passes the dict).
9. If not `args.dry_run`, `_mirror_to_site_public(tdir, public_dir, family=True)`.
10. Print summary line per size + final OK; `return 0`.

Symmetry note: hashing happens after rendering succeeds; meta.yml field stores dict (not str); mirror copies all `<code>.{sla,pdf}` + `<code>-page-*.png` to `site/public/templates/<id>/`.

**Verify:**
- `bin/render-gallery plakat-a1-hochformat` exits 0 and produces:
  - 4× `templates/plakat-a1-hochformat/{a0,a1,a2,a3}.pdf` (each ~1-2 MB).
  - 4× `{a0,a1,a2,a3}-page-1.png` (single-page per size).
  - Old `{a0,a1,a2,a3}-preview-1.png` deleted (verify via `git status`).
  - `meta.yml::previews_for_sla` is a YAML mapping with 4 keys, each → 64-char hex.
- helper `render_twice_byte_compare plakat-a1-hochformat` reports IDEMPOTENT + ZERO DIFF.
- `python3 -c "import yaml; m=yaml.safe_load(open('templates/plakat-a1-hochformat/meta.yml')); assert isinstance(m['previews_for_sla'], dict); assert set(m['previews_for_sla'].keys()) == {'a0','a1','a2','a3'}; print('OK')"` prints OK.

**Done:**
- Family branch produces all 4 size artifacts deterministically.
- meta.yml stores per-size hashes as dict.
- Stale `-preview-*.png` cleaned up; new `-page-N.png` written.
- Idempotency verified.
</task>

<task id="1.3" name="Wire --dry-run, --skip-visual-diff, summary into main()">
**Files:** `tools/render_pipeline.py` (extend `main()`).

**Action:** The argparse skeleton already has `--skip-visual-diff` and `--dry-run`. The orchestrators (Tasks 1.1, 1.2) already honour both. This task:

- After the per-template loop in `main()`, print a summary block: count of templates processed, per-template OK/FAIL status, "(dry-run — no files written)" if `args.dry_run`. Use a 64-char `=` separator line.
- Sample output:
  ```
  ================================================================
  render-gallery summary: 3 templates
    postkarte-a6-kampagne                    OK
    zeitung-a4-grun                          OK
    plakat-a1-hochformat                     OK
  ```

**Verify:**
- `bin/render-gallery --dry-run postkarte-a6-kampagne` runs without modifying `meta.yml` or `site/public/templates/postkarte-a6-kampagne/`. Verify with `git status` after.
- `bin/render-gallery --skip-visual-diff postkarte-a6-kampagne` completes faster (no visual_diff in stdout).
- Summary block printed at end of every run.

**Done:**
- Both flags work as specified.
- Summary block appears at end of every run.
</task>

<gate>
- All 3 templates render to completion via `bin/render-gallery <tid>`.
- Plakat dict-form `previews_for_sla:` correctly written to meta.yml.
- helper `render_twice_byte_compare` reports IDEMPOTENT + ZERO DIFF for all 3.
- Old single-digit `page-N.png` (zeitung) and `<code>-preview-N.png` (plakat) relics deleted.
- `--dry-run` and `--skip-visual-diff` both work.
</gate>

</phase>

<phase id="2" name="Hash field handling in meta.yml + postcard preview_dpi">

Verify `_update_meta_hash` round-trips on real meta.yml files; add `preview_dpi: 100` to postcard.

**RESEARCH.md anchors:** §Stale-Preview Hash Design (lines 362-431), §PNG DPI Recommendation (lines 727-781).

<task id="2.1" name="Verify meta.yml hash-field round-trip on all 3 real templates">
**Files:** none modified beyond Phase 1's pipeline output (verification only).

**Action:** Validate that the pipeline's output is well-formed YAML with the correct shape per template:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
for tid, expect_type in [
    ("postkarte-a6-kampagne", str),
    ("zeitung-a4-grun", str),
    ("plakat-a1-hochformat", dict),
]:
    p = Path(f"templates/{tid}/meta.yml")
    m = yaml.safe_load(p.read_text())
    assert "previews_for_sla" in m, f"{tid}: missing previews_for_sla"
    val = m["previews_for_sla"]
    assert isinstance(val, expect_type), \
        f"{tid}: expected {expect_type.__name__}, got {type(val).__name__}"
    if isinstance(val, str):
        assert len(val) == 64, f"{tid}: expected 64-char hex, got {len(val)}"
    else:
        for code, h in val.items():
            assert len(h) == 64, f"{tid}/{code}: expected 64-char hex"
    print(f"{tid}: OK")
PY
```

If any template fails, return to Phase 1 and fix `_update_meta_hash` or `_orchestrate_family`.

Then confirm idempotency of the meta.yml round-trip: re-run `bin/render-gallery`; `git diff templates/<id>/meta.yml` for all 3 = empty.

**Verify:**
- All 3 templates have correct-shape `previews_for_sla` field.
- `git diff` on all 3 meta.yml files after a second pipeline run = empty.

**Done:**
- All 3 meta.yml files round-trip cleanly.
- Field shape matches expected type (str / dict-of-str).
</task>

<task id="2.2" name="Add postkarte-a6-kampagne meta.yml::preview_dpi: 100">
**Files:** `templates/postkarte-a6-kampagne/meta.yml`.

**Action:** Insert one line — `preview_dpi: 100` — anywhere top-level (e.g., directly below `pages: 2`). RESEARCH.md §PNG DPI Recommendation: A6 at 50 dpi is 243 px wide, below the 360 px detail-thumbnail target. At 100 dpi → 487 px wide, ~50 KB per page (still ~10× smaller than the legacy 80-dpi 132 KB).

The pipeline reads this with `meta.get("preview_dpi", DEFAULT_DPI)` (already wired in Phase 1), so the field automatically takes effect on next render.

Do NOT add `preview_dpi` to `zeitung-a4-grun` or `plakat-a1-hochformat` — defaults work for both per RESEARCH.md §PNG DPI Recommendation table.

**Verify:**
- `python3 -c "import yaml; m=yaml.safe_load(open('templates/postkarte-a6-kampagne/meta.yml')); assert m.get('preview_dpi') == 100; print('OK')"` prints OK.
- Run `bin/render-gallery postkarte-a6-kampagne`; `identify templates/postkarte-a6-kampagne/page-01.png` shows width ~487 px (was ~243 at 50 dpi).
- Other templates' PNG sizes unchanged.

**Done:**
- Postcard meta.yml has `preview_dpi: 100`.
- Postcard PNGs render at 100 dpi (~487 px wide).
</task>

<gate>
- All 3 templates' meta.yml have well-formed `previews_for_sla:` field (str for postkarte/zeitung, dict for plakat).
- Second pipeline run on unchanged source = no meta.yml git diff.
- Postcard meta.yml has `preview_dpi: 100`; postcard PNGs ~487 px wide.
</gate>

</phase>

<phase id="3" name="bin/check-stale-previews + bin/validate preflight wiring">

Mirror `bin/check-fontsizes`'s shape: a thin Python preflight that hashes each template's `template.sla` (or per-size `<code>.sla` for plakat) and compares against the recorded `meta.yml::previews_for_sla` hash, exiting 1 with a clear "run `bin/render-gallery`" message on mismatch.

**RESEARCH.md anchors:** §Stale-Preview Hash Design (lines 362-431), §Test Impact + New Tests (lines 678-725), `bin/check-fontsizes` source as the structural template.

<task id="3.1" name="Create tools/check_stale_previews.py + bin/check-stale-previews shim" risk="high">
**Files:**
- `tools/check_stale_previews.py` (new, ~80 LOC).
- `bin/check-stale-previews` (new, executable, ~10 lines).

**Action:** Create the library following `bin/check-fontsizes`'s shape (Python script, `def main(argv) -> int`, `if __name__ == "__main__": sys.exit(main())`).

Implement these functions in `tools/check_stale_previews.py`:

- `_sha256_of(p: Path) -> str` — same as `tools/render_pipeline.py::_sha256_of`. (Don't import to keep `check_stale_previews` standalone-importable for tests.)
- `_check_template(tdir: Path) -> list[str]` — returns list of error messages; empty list = clean. Logic:
  - If no `meta.yml`, return `[]`.
  - `meta = yaml.safe_load(...)`. If `original_sla` not in meta, return `[]` (skips smoke templates).
  - `tid = meta["id"]`, `is_family = meta.get("type") == "family"`, `recorded = meta.get("previews_for_sla")`.
  - If `recorded is None`: return single-error list `[f"stale: {tid}; previews_for_sla missing in meta.yml — run bin/render-gallery and commit the result"]`.
  - Family branch: assert `recorded` is a dict; for each size in `meta.get("sizes", [])`: hash `tdir / f"{code}.sla"`, compare to `recorded.get(code)`. Append error per mismatched size with the `stale: {tid}/{code}; SLA hash mismatch...` message.
  - Non-family branch: assert `recorded` is a str; hash `tdir / "template.sla"`, compare to `recorded`. Append error if mismatched.
  - All error messages include "Run bin/render-gallery and commit the result." for actionable guidance.
- `main(argv=None) -> int` — iterate `ROOT / "templates" / <subdir>`, skip `_*` and dirs without meta.yml, accumulate errors from `_check_template`. If any errors, print to stderr (header + per-error indent) plus footer guidance "Fix by running locally: bin/render-gallery && git add ... && git commit". Return 1 on errors, 0 otherwise.

`bin/check-stale-previews` shim:

```python
#!/usr/bin/env python3
"""bin/check-stale-previews — gallery preview staleness gate (issue #4)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from check_stale_previews import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`chmod +x bin/check-stale-previews`.

**Verify:**
- `bin/check-stale-previews` exits 0 against current state (post-Phase 1).
- Synthetic stale test 1 (non-family hash mismatch): `echo " " >> templates/postkarte-a6-kampagne/template.sla`; `bin/check-stale-previews` exits 1 with "stale: postkarte-a6-kampagne; template.sla hash mismatch ..." Revert.
- Synthetic stale test 2 (family per-size): `echo " " >> templates/plakat-a1-hochformat/a2.sla`; `bin/check-stale-previews` exits 1 with "stale: plakat-a1-hochformat/a2; SLA hash mismatch ..." Revert.
- Synthetic stale test 3 (missing field): manually delete `previews_for_sla:` line(s) from postcard meta.yml; `bin/check-stale-previews` exits 1 with "previews_for_sla missing in meta.yml". Revert.

**Done:**
- Both files exist, executable.
- Clean state → exit 0; 3 synthetic stale variants → exit 1 with template-specific messages.
</task>

<task id="3.2" name="Wire bin/check-stale-previews into bin/validate as a preflight">
**Files:** `bin/validate` (extend with one new preflight invocation between current lines 30 and 32).

**Action:** Insert this block after `echo` on line 30 and before `EXIT=0` on line 32:

```bash
echo "=== preflight: bin/check-stale-previews ==="
if ! "$ROOT/bin/check-stale-previews"; then
    echo "preflight FAILED — gallery previews are stale; refusing to validate" >&2
    exit 1
fi
echo "preflight: PASS"
echo
```

The visual_diff per-template loop (lines 32 onwards) stays untouched.

**Verify:**
- `bin/validate` runs cleanly post-Phase 1 (exits 0).
- Synthetic stale test: mutate `templates/postkarte-a6-kampagne/template.sla` via `echo " " >>`; `bin/validate` exits 1 at the new preflight (without entering the per-template loop). Revert.

**Done:**
- `bin/validate` includes new preflight as the second check (after `check-fontsizes`, before per-template loop).
- Stale state short-circuits before per-template work runs.
</task>

<task id="3.3" name="Add tools/sla_lib/tests/test_check_stale_previews.py">
**Files:** `tools/sla_lib/tests/test_check_stale_previews.py` (new).

**Action:** Hand-craft fixture template directories using `tempfile.TemporaryDirectory`; drive `_check_template` directly. Mirror the `unittest.TestCase` shape from existing tests. ≥7 tests:

- `test_clean_non_family` — synthetic non-family meta with valid hash; `_check_template` returns `[]`.
- `test_stale_non_family` — synthetic non-family meta with wrong hash; returns 1 error containing "template.sla hash mismatch" and "bin/render-gallery".
- `test_missing_field` — synthetic non-family meta without `previews_for_sla`; returns 1 error containing "previews_for_sla missing".
- `test_clean_family` — synthetic family meta with 2 sizes (a0, a1) and matching hashes; returns `[]`.
- `test_stale_family_one_size` — clean family fixture, then mutate `a1.sla` bytes; returns 1 error containing "a1; SLA hash mismatch".
- `test_skip_no_original_sla` — meta without `original_sla`; returns `[]` (skip).
- `test_skip_no_meta_yml` — empty dir without meta.yml; returns `[]`.

Helper method `_make_template(tmpdir, *, family, has_field, valid)` builds the synthetic fixture by writing `meta.yml` + `template.sla` (or `a0.sla`, `a1.sla` for family).

**Verify:**
- `python3 -m unittest tools.sla_lib.tests.test_check_stale_previews -v` — all ≥7 tests pass.
- `python3 -m unittest discover tools/sla_lib/tests` — total ≥153, OK.

**Done:**
- ≥7 unit tests covering clean/stale/missing-field for both family + non-family.
- Discovery shows ≥153 tests.
</task>

<gate>
- `bin/check-stale-previews` exits 0 against current state; 3 synthetic stale variants → exit 1.
- `bin/validate` includes the new preflight; stale state short-circuits.
- `python3 -m unittest discover tools/sla_lib/tests` ≥153 tests, OK.
</gate>

</phase>

<phase id="4" name="tools/gallery_build.py copy-only refactor">

Strip `render_pdf()` and `pdf_to_pngs()`; refactor `process_template()` to consume committed artifacts; add `_fail_missing` helper.

**RESEARCH.md anchors:** §gallery_build.py Refactor function-by-function (lines 432-590), §Caller audit (lines 578-590) confirms zero external callers of the deleted functions.

<task id="4.1" name="Delete render_pdf and pdf_to_pngs functions" risk="high">
**Files:** `tools/gallery_build.py` (delete lines 26-49 + unused imports).

**Action:**
1. Delete `def render_pdf(template_dir, sla_path, pdf_path)` (lines 26-39).
2. Delete `def pdf_to_pngs(pdf_path, out_prefix, dpi=80)` (lines 42-49).
3. Remove unused imports: `import os`, `import subprocess` (only used by deleted functions). Add `import sys` (needed by Phase 4.2 for `_fail_missing`'s `sys.exit`). `shutil`, `pathlib.Path`, `yaml` stay.

After deletion, the module top is:

```python
#!/usr/bin/env python3
"""Walk templates/, copy gallery artifacts to site/public/templates/<id>/, and
write Astro frontmatter for each.

Issue #4: rendering moved to bin/render-gallery (which the maintainer runs
locally before committing). This script is now copy-only and fails loudly if
expected committed artifacts are missing for a template — that signals the
maintainer forgot to run bin/render-gallery before pushing.
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
SITE_CONTENT = ROOT / "site" / "src" / "content" / "templates"
SITE_PUBLIC = ROOT / "site" / "public" / "templates"
```

**Verify:**
- `grep -n "def render_pdf\|def pdf_to_pngs" tools/gallery_build.py` returns nothing.
- `grep -rn "render_pdf\|pdf_to_pngs" --include='*.py' --include='*.yml' .` returns zero references repo-wide.
- `python3 -c "import sys; sys.path.insert(0, 'tools'); import gallery_build; assert not hasattr(gallery_build, 'render_pdf'); assert not hasattr(gallery_build, 'pdf_to_pngs'); print('OK')"` prints OK.

**Done:**
- Both functions removed.
- Unused imports trimmed.
- Repo-wide grep returns zero references.
</task>

<task id="4.2" name="Refactor process_template to copy-only with _fail_missing helper" risk="high">
**Files:** `tools/gallery_build.py` (replace lines 52-108 with copy-only logic; add `_fail_missing`).

**Action:** Read RESEARCH.md lines 494-561 for the exact shape. Replace `process_template` with copy-only logic. The refactored version:

- Adds module-level `_fail_missing(tid, sla, pdf, pngs)` function: `sys.exit(...)` with FATAL message (template id, file existence flags, glob pattern, runbook pointer to `bin/render-gallery`).
- `process_template(tdir)`:
  - Read `meta.yml` (return None if absent — preserves smoke-template skip).
  - Determine `is_family = meta.get("type") == "family"`.
  - Make `public_dir = SITE_PUBLIC / tid; public_dir.mkdir(parents=True, exist_ok=True)`.
  - **Family branch:** for each size, glob committed `<code>.sla`, `<code>.pdf`, sorted `<code>-page-*.png` from `tdir/`. If any missing, call `_fail_missing(tid, sla, pdf, page_pngs)`. Else copy each to `public_dir`. Build `_downloads` (one per size) and `_previews` (one per size, using first PNG's name) lists.
  - **Non-family branch:** glob `template.sla`, `preview.pdf`, sorted `page-*.png`. Same fail-fast pattern. Copy to `public_dir`. Build `_downloads` (single entry) and `_previews` (one entry per page, with `Seite {N+1}` labels).
  - Returns `meta` dict for `main()` to write frontmatter.
- `main()` (lines 111-132) untouched — iterates templates, calls `process_template`, writes Astro frontmatter, embeds README.md per template.

The shape mirrors RESEARCH.md's "After" example at lines 494-560. Both branches: glob from `tdir/`, NOT from `public_dir/` (changes from current code). Both branches: hard-fail on missing artifacts. Family branch: iterate ALL `page_pngs` per size (current code only copied one). Both branches: drop the `dpi=80/40` hardcodes (no longer applicable).

**Verify:**
- `python3 tools/gallery_build.py` runs without error against post-Phase-1 state. Output: 3 lines like `[gallery] postkarte-a6-kampagne → site/src/content/templates/postkarte-a6-kampagne.md`.
- `site/public/templates/postkarte-a6-kampagne/{template.sla, preview.pdf, page-01.png, page-02.png}` exist.
- `site/public/templates/zeitung-a4-grun/{template.sla, preview.pdf, page-01.png ... page-14.png}` exist.
- `site/public/templates/plakat-a1-hochformat/{a0,a1,a2,a3}.{sla,pdf}` + `{a0,a1,a2,a3}-page-1.png` exist.
- `site/src/content/templates/zeitung-a4-grun.md` frontmatter `_previews` lists exactly 14 entries (was previously broken with 23).
- Synthetic missing-artifact test: `mv templates/postkarte-a6-kampagne/preview.pdf /tmp/`; `python3 tools/gallery_build.py` exits 1 with `FATAL: gallery artifacts missing for template 'postkarte-a6-kampagne': ... Run \`bin/render-gallery\``. Restore.
- Verify gallery_build runs in env without xvfb/scribus on PATH: `PATH=/usr/bin:/bin python3 tools/gallery_build.py` exits 0 (proves it does no rendering).

**Done:**
- `process_template` is copy-only with `_fail_missing` helper.
- Both family and non-family branches handle multiple PNGs and fail loudly on missing artifacts.
- Astro frontmatter `_previews` correctly enumerates committed pages.
- gallery_build.py works in env without Scribus.
</task>

<task id="4.3" name="Add tools/sla_lib/tests/test_gallery_build_copy_only.py">
**Files:** `tools/sla_lib/tests/test_gallery_build_copy_only.py` (new).

**Action:** Hand-craft fixture template directories with synthetic meta.yml + (optionally absent) artifacts. Use `unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", ...)` to redirect output. ≥6 tests:

- `test_non_family_success` — fixture with all artifacts present; `process_template` returns dict with `_previews` (length 2 — postcard has 2 pages); `site_public/template.sla`, `preview.pdf`, `page-01.png`, `page-02.png` all exist after.
- `test_non_family_missing_pdf_fails` — fixture without preview.pdf; `process_template` raises `SystemExit` with "FATAL" + "preview.pdf" in message.
- `test_non_family_missing_pngs_fails` — fixture without page-*.png; raises `SystemExit`.
- `test_family_success` — fixture with `a0.sla`, `a0.pdf`, `a0-page-1.png`; returns dict with `_previews` length 1 + label `"A0"`; site_public has the 3 files.
- `test_family_missing_pdf_fails` — fixture missing `a0.pdf`; raises `SystemExit`.
- `test_skip_no_meta_yml` — empty dir; `process_template` returns None.

**Verify:**
- `python3 -m unittest tools.sla_lib.tests.test_gallery_build_copy_only -v` — all ≥6 tests pass.
- `python3 -m unittest discover tools/sla_lib/tests` — total ≥159, OK.

**Done:**
- ≥6 unit tests covering success path + 4 failure paths.
- Discovery shows ≥159 tests.
</task>

<gate>
- `tools/gallery_build.py` no longer references `render_pdf`, `pdf_to_pngs`, `subprocess`, `os`, or `xvfb`.
- `python3 tools/gallery_build.py` runs to completion in env without Scribus on PATH.
- `_fail_missing` invoked correctly when artifacts absent.
- `python3 -m unittest discover tools/sla_lib/tests` ≥159 tests, OK.
- `site/src/content/templates/zeitung-a4-grun.md` frontmatter shows `_previews` with 14 entries (not the previous broken 23).
</gate>

</phase>

<phase id="5" name=".github/workflows/pages.yml simplification">

Add the stale-previews preflight; drop the multi-line "TODO: restore visual_diff" comment block. No other workflow changes.

**RESEARCH.md anchors:** §CI Workflow Delta (lines 592-666).

<task id="5.1" name="Add bin/check-stale-previews invocation; drop TODO comment block">
**Files:** `.github/workflows/pages.yml` (modify lines 93-123).

**Action:** Three concrete edits inside the `Validate reproductions (sla_diff)` step:

1. Rename step `name:` to `Validate reproductions (sla_diff + stale-previews)`.
2. Insert two new lines BEFORE the `for tdir in ...` loop:
   - A 2-line comment: `# Preflight: gallery previews must match committed template.sla bytes.` and `# See docs/render-fidelity.md "Local-only rendering" — CI never renders templates.`
   - The invocation: `python3 bin/check-stale-previews`
3. Delete the entire 9-line `# NOTE:` + `# TODO:` block (current lines 115-122) inside the for-loop body. The for-loop body otherwise unchanged: still resolves `original_sla` from meta.yml, still runs `python3 tools/sla_diff.py ... --strict`.

The `Run brand validator` step (lines 125-129), `actions/upload-pages-artifact` step, the `deploy` job, and ALL other steps stay UNCHANGED.

**Verify:**
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml'))"` parses cleanly.
- `grep -c "bin/check-stale-previews" .github/workflows/pages.yml` = 1.
- `grep -c "TODO: restore visual_diff" .github/workflows/pages.yml` = 0.
- `grep -c "NOTE: visual_diff is intentionally NOT run" .github/workflows/pages.yml` = 0.
- `git diff main -- .github/workflows/pages.yml` shows changes ONLY in the lines 93-123 region.

**Done:**
- Workflow parses; new preflight in place; old TODO block removed.
- Step name updated.
- All other steps untouched.
</task>

<gate>
- `.github/workflows/pages.yml` parses cleanly.
- `bin/check-stale-previews` invoked at top of `Validate reproductions (...)` step.
- 9-line TODO comment block removed.
- `git diff` shows changes ONLY in lines 93-123 region.
</gate>

</phase>

<phase id="6" name="Regenerate all gallery artifacts via the new pipeline + regression check">

Run `bin/render-gallery` from a clean state, regenerate every artifact, confirm byte-equivalence to the user's reference PDFs (the standard PR #7 established).

**RESEARCH.md anchors:** §Codebase Analysis (lines 64-87) for relevant files, §Performance + Repository size (lines 814-822).

<task id="6.1" name="Clean tree + bin/render-gallery from scratch" risk="high">
**Files:** all `templates/<id>/preview.pdf`, `<id>/page-*.png`, `<id>/*.pdf` (plakat sizes), `<id>/*-page-*.png`, `<id>/meta.yml::previews_for_sla` (regenerated).

**Action:**

```bash
# Sanity check: brand fonts present.
fc-list | grep -ciE 'gotham narrow|vollkorn'   # expect ≥17

# Belt-and-braces: explicitly delete stale single-digit / hand-named files
# in case Phase 1's pipeline runs left any (the orchestrators clean these
# at start, but a manual clean here ensures the regression check starts
# from a known baseline).
rm -f templates/zeitung-a4-grun/page-?.png   # single-digit relics
rm -f templates/plakat-a1-hochformat/*-preview-*.png   # old hand-named relics

# Full pipeline run.
time bin/render-gallery

# Show what changed.
git status --short templates/ site/public/
git diff --stat templates/ site/public/ | head -20
```

Expect:
- `bin/render-gallery` exits 0.
- Wall time ~45-60 sec (per RESEARCH.md §Performance).
- Zeitung: 14 new `page-NN.png` files + 9 deleted single-digit relics + modified preview.pdf.
- Plakat: 4 modified `<code>.pdf` + 4 new `<code>-page-1.png` + 4 deleted `<code>-preview-1.png`.
- Postcard: modified preview.pdf + 2 new/modified `page-0N.png`.
- All 3 meta.yml files have `previews_for_sla:` updated.

**Verify:**
- All expected artifacts produced (zeitung 14 pages + postkarte 2 + plakat 4 sizes × 1 page each).
- `git diff --stat` shows only expected files.
- `bin/render-gallery` exit 0 (means sla_diff and visual_diff both passed for all 3 templates).

**Done:**
- All gallery artifacts regenerated from clean state.
- Stale single-digit `page-N.png` and `<code>-preview-N.png` relics deleted.
- Pipeline exited cleanly.
</task>

<task id="6.2" name="Idempotency regression: second run = no diff" risk="high">
**Files:** none modified (verification).

**Action:**

```bash
bin/render-gallery
git diff templates/ site/public/
[ -n "$(git diff templates/ site/public/)" ] && { echo "REGRESSION: not idempotent" >&2; exit 1; }
echo "IDEMPOTENT (second run produced no diff)"
```

If non-empty diff: return to Phase 0/1 and investigate which file is non-deterministic (likely PDF — scrub mis-applied — or meta.yml — hash-update mis-applied).

**Verify:**
- `git diff templates/ site/public/` after second `bin/render-gallery` run = empty.
- SHA256 of any preview.pdf identical between two runs (`sha256sum templates/postkarte-a6-kampagne/preview.pdf`).

**Done:**
- Second run = zero git diff.
- Pipeline confirmed idempotent end-to-end.
</task>

<task id="6.3" name="Reference-PDF regression check (PR #7's 0-px standard)" risk="high">
**Files:** none modified (verification).

**Action:** Run helper `reference_pdf_byte_compare` with `OUT_DIR=build/phase6-regression`. Confirms each regenerated `preview.pdf` (or `a1.pdf` for plakat) raster-equivalents the user's frozen reference PDFs in `/root/workspace/originals/` at 0% fuzz across all 17 pages.

If any page is >0 px: re-check `fc-list` (fonts loaded?), confirm Scribus version unchanged from PR #7, inspect `build/phase6-regression/<tag>/diff-page-N.png` visually. This is the load-bearing acceptance criterion #11 in ISSUE.md.

**Verify:** All pages report 0 px mismatch.

**Done:**
- 0-px regression check passes for all 17 pages.
- PR #7's standard preserved.
</task>

<task id="6.4" name="Final bin/validate exits 0">
**Files:** none modified (verification).

**Action:** `bin/validate`. Invokes the full chain: `bin/check-fontsizes` preflight → `bin/check-stale-previews` preflight → per-template `sla_diff --strict` + `visual_diff at 150 dpi`.

**Verify:**
- Exit 0.
- All 3 templates report `sla_diff: PASS` and `visual_diff (150dpi): PASS`.
- Both preflights show "PASS".

**Done:** `bin/validate` green end-to-end.
</task>

<gate>
- `bin/render-gallery` exits 0 from clean tree; produces all expected artifacts.
- Second run produces zero git diff (idempotent).
- All 17 pages 0-px raster-equivalent to user's reference PDFs.
- `bin/validate` exits 0.
- Stale single-digit `page-N.png` and `<code>-preview-N.png` relics no longer in tree.
</gate>

</phase>

<phase id="7" name="Documentation">

Add the "Local-only rendering" architectural section, reword "CI font provisioning" from in-progress → permanently out of scope, document the maintainer workflow.

**RESEARCH.md anchors:** §CI Workflow Delta (lines 592-666), CONTEXT.md D6 + D7 + D9.

<task id="7.1" name="Add 'Local-only rendering' + 'Maintainer workflow' to docs/render-fidelity.md">
**Files:** `docs/render-fidelity.md`.

**Action:** Read the current file (created by issue #3 PR #7). Add two new sections before the existing "Out of scope" section:

**Section "Local-only rendering: why CI never renders templates"** — covers (read CONTEXT.md "Why" section + ISSUE.md "Reasoning trail" for the substance):
- Single render path = no drift.
- Why this trade-off was chosen over CI font provisioning (Option A reject) or hybrid render (Option C reject).
- Stale-preview gate: `bin/check-stale-previews` is a CI gate; mismatched hashes fail with actionable message.

**Section "Maintainer workflow"** — the 5-step authoring loop (CONTEXT.md D9):
1. Edit a template's SLA or build script.
2. Run `bin/render-gallery` from dev container's repo root.
3. Review resulting `preview.pdf` + `page-NN.png` locally.
4. `git add templates/ site/public/ && git commit && git push`.
5. CI runs structural gate + stale-preview check; if green, GitHub Pages deploy fires.

Include a per-template artifacts table (postkarte: preview.pdf + page-01..02 at 100 dpi; zeitung: preview.pdf + page-01..14 at 50 dpi; plakat: 4× `<code>.pdf` + 4× `<code>-page-1.png` at 50 dpi). Mention the `preview_dpi:` meta.yml field. Mention idempotency: pipeline strips non-deterministic PDF metadata via length-preserving regex byte-scrub.

Then update the existing "Out of scope" section: change the "CI font provisioning" entry from "tracked in a separate follow-up issue" → "permanently out of scope per issue #4 D7 (Local-only rendering pipeline)". Cross-link to the new "Local-only rendering" section.

Add a "See also" footer:
- `bin/render-gallery` — local pipeline entry point.
- `bin/check-stale-previews` — staleness preflight.
- `bin/validate` — full local validation.

**Verify:**
- `grep -c "Local-only rendering" docs/render-fidelity.md` ≥ 1.
- `grep -c "Maintainer workflow" docs/render-fidelity.md` ≥ 1.
- `grep -c "permanently out of scope" docs/render-fidelity.md` ≥ 1.
- `grep -c "bin/render-gallery" docs/render-fidelity.md` ≥ 2.
- `grep -c "bin/check-stale-previews" docs/render-fidelity.md` ≥ 1.

**Done:**
- New sections present.
- Old "tracked in follow-up" wording replaced.
- Cross-references in place.
</task>

<task id="7.2" name="Update shared/fonts/README.md to clarify local-only path">
**Files:** `shared/fonts/README.md`.

**Action:** Read current file. At end of "Container-Install" section, add a one-paragraph note clarifying that the brand fonts here are required for `bin/render-gallery` (the local pipeline), CI never installs these fonts and never renders templates, this is the *only* path that produces gallery artifacts. Cross-link to `docs/render-fidelity.md` "Local-only rendering" section.

**Verify:**
- `grep -c "Local-only rendering" shared/fonts/README.md` ≥ 1.
- `grep -c "only path" shared/fonts/README.md` ≥ 1.
- `grep -c "bin/render-gallery" shared/fonts/README.md` ≥ 1.

**Done:**
- Note paragraph added; cross-link in place.
</task>

<gate>
- `docs/render-fidelity.md` has new "Local-only rendering" + "Maintainer workflow" sections.
- "CI font provisioning permanently out of scope" wording in place.
- `shared/fonts/README.md` clarifies local-only path.
- Cross-references resolve.
</gate>

</phase>

<phase id="8" name="End-to-end demo (synthetic edit → render → validate → revert)">

Acceptance criterion in ISSUE.md: "One end-to-end demo: edit a template SLA (e.g. minor headline change), run `bin/render-gallery`, commit, push → CI passes → Pages deploy reflects the change visually."

We can't push and trigger CI from inside the planning loop, but we can do the local half (mutate → fail-stale → render → clean → validate → revert) and document the full procedure for the user-driven push half.

**RESEARCH.md anchors:** CONTEXT.md D9 maintainer workflow.

<task id="8.1" name="Synthetic template edit + render + validate + revert">
**Files:** none committed (`templates/postkarte-a6-kampagne/template.sla` is mutated then reverted).

**Action:**

```bash
# Mutate template.sla (synthetic 1-byte change to simulate "SLA changed
# without re-rendering").
echo " " >> templates/postkarte-a6-kampagne/template.sla

# Stale check should now fire.
bin/check-stale-previews && { echo "BUG: should have failed" >&2; exit 1; }
echo "stale check correctly fired"

# Run pipeline — it regenerates template.sla from build.py (overwriting the
# mutation), re-renders preview.pdf, re-rasterises PNGs, updates meta.yml hash.
bin/render-gallery postkarte-a6-kampagne

# Stale check should now pass.
bin/check-stale-previews
echo "stale check now clean"

# Full validate.
bin/validate

# Revert any residual changes.
git checkout -- templates/postkarte-a6-kampagne/ site/public/templates/postkarte-a6-kampagne/

# Confirm clean tree.
git status --short templates/postkarte-a6-kampagne/ site/public/templates/postkarte-a6-kampagne/
[ -z "$(git status --porcelain templates/postkarte-a6-kampagne/ site/public/templates/postkarte-a6-kampagne/)" ] \
    && echo "CLEAN" || { echo "DIRTY" >&2; exit 1; }
```

Note: a realistic maintainer edit would be in `build.py` (e.g., change a German placeholder string), not directly to `template.sla`. The 1-byte append is a quick stand-in that exercises the same staleness gate.

**Verify:**
- `bin/check-stale-previews` exits 1 on mutated state with "stale: postkarte-a6-kampagne; template.sla hash mismatch".
- `bin/render-gallery postkarte-a6-kampagne` exits 0.
- `bin/check-stale-previews` exits 0 post-render.
- `bin/validate` exits 0.
- After `git checkout`, tree is clean.

**Done:**
- Maintainer-loop demo executed end-to-end locally.
- Stale gate fires correctly; pipeline clears stale state.
- Revert produces clean tree.
</task>

<task id="8.2" name="Document the demo + push procedure in EXECUTION.md">
**Files:** `.issues/4-restore-visual_diff-in-ci-by-provisioning-brand-fonts/EXECUTION.md` (the executor will be writing this file as the standard issue:work execution log; append a new section).

**Action:** At end of EXECUTION.md, add `## Final acceptance demo` section recording:
- The local half executed during Phase 8.1 (mutated → stale check fired → render → clean → validate → revert; all green).
- The push half is user-driven once the PR merges to `main`. Document expected behaviour: push triggers `.github/workflows/pages.yml` → `Validate reproductions` step runs `bin/check-stale-previews` (clean) + `sla_diff --strict` (clean) → Astro build → Pages deploy fires.
- 8-step push-demo procedure for the user to optionally exercise (create test branch → edit `templates/postkarte-a6-kampagne/build.py` string → regenerate template.sla → commit WITHOUT running render-gallery → push → CI fails at stale-previews preflight → run `bin/render-gallery` locally → commit regenerated artifacts → push → CI passes → Pages deploy → cleanup test branch).

**Verify:**
- `grep -c "Final acceptance demo" .issues/4-*/EXECUTION.md` ≥ 1.
- 8-step push procedure documented.

**Done:**
- EXECUTION.md "Final acceptance demo" section in place.
- Local demo + push procedure both documented.
</task>

<gate>
- Local demo executed: stale-fire → render → clean → validate → revert all green.
- EXECUTION.md documents the procedure for user-driven push demo.
- Tree clean (no uncommitted changes after revert).
</gate>

</phase>

<phase id="9" name="Final verification">

Run all 11 acceptance criteria checks; record results in EXECUTION.md.

**RESEARCH.md anchors:** ISSUE.md "Acceptance Criteria" (lines 99-111).

<task id="9.1" name="Acceptance criteria checklist" risk="high">
**Files:** none modified (verification).

**Action:** Run the following checks. Each maps to one ISSUE.md acceptance criterion. Capture pass/fail in EXECUTION.md. The script is deliberately a single block so the executor can copy-paste:

```bash
set -uo pipefail
echo "==== Acceptance Criteria Checks ===="

# AC1: bin/render-gallery exists, documented, deterministic.
test -x bin/render-gallery && echo "AC1.exists: OK" || echo "AC1.exists: FAIL"
bin/render-gallery --help | head -1 | grep -q "render-gallery" && echo "AC1.help: OK"

# AC2: Running bin/render-gallery twice produces no git diff.
bin/render-gallery >/dev/null
[ -z "$(git diff templates/ site/public/)" ] && echo "AC2.idempotent: OK" || echo "AC2.idempotent: FAIL"

# AC3: Preview PNG dpi reduced. Zeitung 50 dpi, postcard 100 dpi.
zeitung_w=$(identify -format '%w' templates/zeitung-a4-grun/page-01.png)
[ "$zeitung_w" -ge 440 ] && [ "$zeitung_w" -le 460 ] \
    && echo "AC3.zeitung_50dpi: OK ($zeitung_w px)" \
    || echo "AC3.zeitung_50dpi: FAIL ($zeitung_w px, expected ~449)"
postcard_w=$(identify -format '%w' templates/postkarte-a6-kampagne/page-01.png)
[ "$postcard_w" -ge 480 ] && [ "$postcard_w" -le 500 ] \
    && echo "AC3.postcard_100dpi: OK ($postcard_w px)" \
    || echo "AC3.postcard_100dpi: FAIL ($postcard_w px, expected ~487)"
zeitung_kb=$(du -ck templates/zeitung-a4-grun/page-*.png | tail -1 | awk '{print $1}')
[ "$zeitung_kb" -lt 1100 ] \
    && echo "AC3.zeitung_payload: OK ($zeitung_kb KB)" \
    || echo "AC3.zeitung_payload: FAIL ($zeitung_kb KB, expected <1100)"

# AC4: tools/gallery_build.py copy-only.
grep -E "^def render_pdf|^def pdf_to_pngs" tools/gallery_build.py >/dev/null \
    && echo "AC4.copy_only: FAIL" || echo "AC4.copy_only: OK"
grep -E "subprocess|xvfb|scribus" tools/gallery_build.py >/dev/null \
    && echo "AC4.no_render: FAIL" || echo "AC4.no_render: OK"

# AC5: bin/check-stale-previews works.
test -x bin/check-stale-previews && echo "AC5.exists: OK"
bin/check-stale-previews && echo "AC5.clean: OK" || echo "AC5.clean: FAIL"
echo " " >> templates/postkarte-a6-kampagne/template.sla
bin/check-stale-previews 2>&1 | grep -q "stale: postkarte-a6-kampagne" \
    && echo "AC5.fires: OK" || echo "AC5.fires: FAIL"
git checkout -- templates/postkarte-a6-kampagne/template.sla

# AC6: bin/validate invokes check-stale-previews as preflight.
grep -q "check-stale-previews" bin/validate \
    && echo "AC6.wired: OK" || echo "AC6.wired: FAIL"

# AC7: CI workflow updated.
grep -q "bin/check-stale-previews" .github/workflows/pages.yml \
    && echo "AC7.ci_wired: OK" || echo "AC7.ci_wired: FAIL"
grep -q "TODO: restore visual_diff" .github/workflows/pages.yml \
    && echo "AC7.todo_dropped: FAIL" || echo "AC7.todo_dropped: OK"

# AC8: deploy job unchanged. (Manual visual review.)
echo "AC8.deploy_unchanged: visual review of git diff"

# AC9: docs.
grep -q "Local-only rendering" docs/render-fidelity.md \
    && echo "AC9.docs: OK" || echo "AC9.docs: FAIL"
grep -q "permanently out of scope" docs/render-fidelity.md \
    && echo "AC9.permanently_oos: OK" || echo "AC9.permanently_oos: FAIL"

# AC10: end-to-end demo documented.
grep -q "Final acceptance demo" .issues/4-*/EXECUTION.md \
    && echo "AC10.demo: OK" || echo "AC10.demo: FAIL"

# AC11: 17 pages still 0-px equivalent to user's reference PDFs.
# (Run helper reference_pdf_byte_compare with OUT_DIR=build/phase9-final.)
echo "AC11: see helper output above"

# Bonus: full unit-test discovery green.
python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -3
```

Then run helper `reference_pdf_byte_compare` with `OUT_DIR=build/phase9-final` and verify 0 px on all 17 pages (acceptance criterion 11).

**Verify:** Every `AC*.NAME: OK` line printed; no FAIL. Helper reports 0 px on all 17 pages. Discovery shows ≥159 tests OK.

**Done:**
- All 11 acceptance criteria verified PASS.
- Unit-test discovery shows ≥159 tests, OK.
- 0-px regression check passes for all 17 pages.
</task>

<task id="9.2" name="Final summary + tree state confirmation">
**Files:** none modified (final summary).

**Action:**

```bash
git status --short
echo "---"
echo "Total tests: $(python3 -m unittest discover tools/sla_lib/tests 2>&1 | grep -E '^Ran' | awk '{print $2}')"
echo "Total gallery payload: $(du -ck site/public/templates/ | tail -1 | awk '{print $1}') KB"
```

Expected `git status` shows:
- New files: `bin/render-gallery`, `bin/check-stale-previews`, `tools/render_pipeline.py`, `tools/check_stale_previews.py`, 3 new test files in `tools/sla_lib/tests/`.
- Modified: `tools/gallery_build.py`, `bin/validate`, `.github/workflows/pages.yml`, `docs/render-fidelity.md`, `shared/fonts/README.md`, all 3 `templates/<id>/meta.yml`, regenerated `templates/<id>/preview.pdf` + per-size `<code>.pdf` (plakat).
- New: regenerated `templates/<id>/page-NN.png`, `<code>-page-N.png` (plakat); regenerated `site/public/templates/<id>/*` mirrors.
- Deleted: stale `templates/zeitung-a4-grun/page-{1..9}.png` and `templates/plakat-a1-hochformat/{a0..a3}-preview-1.png`.

Total tests ≥159 (was 136 baseline + ~10 render_pipeline + ~7 check_stale_previews + ~6 gallery_build_copy_only).
Total gallery payload ~5-6 MB (per RESEARCH.md §Repository size estimate).

**Verify:**
- Tree state matches expected manifest.
- No stray files from `build/` accidentally tracked (`build/` is gitignored — verify with `git check-ignore build/`).

**Done:**
- Final summary recorded in EXECUTION.md.
- Tree state confirmed correct for commit.
</task>

<gate>
- All 11 acceptance criteria from ISSUE.md verified PASS.
- Unit-test discovery ≥159 tests, OK.
- 0-px regression check on all 17 pages.
- `bin/validate` exit 0; `bin/check-stale-previews` exit 0; `bin/render-gallery` second run = no git diff.
- Workflow YAML well-formed; tree state matches expected manifest.
</gate>

</phase>

## Files touched (manifest)

**New files:**

- `bin/render-gallery` — Python shim, ~10 lines, executable.
- `bin/check-stale-previews` — Python shim, ~10 lines, executable.
- `tools/render_pipeline.py` — orchestrator library, ~250 LOC.
- `tools/check_stale_previews.py` — staleness gate library, ~80 LOC.
- `tools/sla_lib/tests/test_render_pipeline.py` — ≥10 unit tests.
- `tools/sla_lib/tests/test_check_stale_previews.py` — ≥7 unit tests.
- `tools/sla_lib/tests/test_gallery_build_copy_only.py` — ≥6 unit tests.

**Modified files:**

- `tools/gallery_build.py` — delete `render_pdf` (lines 26-39) + `pdf_to_pngs` (lines 42-49); refactor `process_template` (lines 52-108) to copy-only with `_fail_missing` helper. Net: ~137 LOC → ~95 LOC.
- `bin/validate` — add `bin/check-stale-previews` preflight invocation (~7 lines between current lines 30 and 32). Net: 81 → ~88 LOC.
- `.github/workflows/pages.yml` — modify `Validate reproductions` step: rename, add preflight + 2-line comment, drop 9-line TODO comment block.
- `templates/postkarte-a6-kampagne/meta.yml` — add `preview_dpi: 100`; pipeline adds `previews_for_sla:` on first run.
- `templates/zeitung-a4-grun/meta.yml` — pipeline adds `previews_for_sla:` (str) on first run.
- `templates/plakat-a1-hochformat/meta.yml` — pipeline adds `previews_for_sla:` (dict) on first run.
- `docs/render-fidelity.md` — add "Local-only rendering" + "Maintainer workflow" sections; reword "Out of scope" CI fonts entry.
- `shared/fonts/README.md` — add "only path" clarification.

**Regenerated content (touched by pipeline):**

- `templates/postkarte-a6-kampagne/preview.pdf`, `page-01.png`, `page-02.png`.
- `templates/zeitung-a4-grun/preview.pdf`, `page-01.png` ... `page-14.png`.
- `templates/plakat-a1-hochformat/{a0,a1,a2,a3}.pdf`, `{a0,a1,a2,a3}-page-1.png`.
- `site/public/templates/<id>/*` — mirrors of the above.
- `site/src/content/templates/<id>.md` — Astro frontmatter (regenerated by `gallery_build.py::main`); zeitung's `_previews` resolves from broken-23 → correct-14 entries.

**Deleted files:**

- `templates/zeitung-a4-grun/page-1.png` ... `page-9.png` (single-digit relics, replaced by zero-padded `page-01..14`).
- `templates/plakat-a1-hochformat/{a0,a1,a2,a3}-preview-1.png` (old hand-named relics, replaced by `<code>-page-1.png`).

**Untouched (load-bearing — must NOT change):**

- `tools/visual_diff.py`, `tools/sla_diff.py`, `tools/_export_pdf.py`, `tools/sla_to_dsl.py` — invoked unchanged.
- `tools/sla_lib/`, `tools/render.py` (separate utility) — untouched.
- `bin/check-fontsizes` — untouched (read as pattern reference only).
- `Dockerfile.claude` — untouched.
- `shared/fonts/50-vollkorn-family-alias.conf` — untouched.
- `templates/<id>/build.py` for all 3 templates — untouched (issue #3 territory).
- `templates/<id>/baseline.pdf` — untouched (frozen visual_diff reference).
- `templates/<id>/diff.yml` — untouched.
- `*-original.sla` at workspace root — untouched (canonical inputs from issue #3).
- `templates/_smoke/*` — untouched (no `original_sla` field; pipeline skips).

## Out of scope (preserved from CONTEXT.md)

- **D7 — CI font provisioning is permanently out of scope.** No PAT, no private repo, no font secret. The `docs/render-fidelity.md` rewording in Phase 7 makes this final.
- Modifying `*-original.sla` files (issue #3 canonical inputs).
- DSL-builder changes (`tools/sla_to_dsl.py` + `tools/sla_lib/builder/`) — separate issue territory.
- New templates / new fonts.
- Authoring contributors who don't have the dev container's font drop zone.
- Replacing the rendering toolchain (Scribus stays).
- `tools/render.py` (separate, unused-by-this-pipeline utility — leave alone).
- Per-size plakat SLA generation (`a0.sla`...`a3.sla` are committed inputs; the new pipeline renders them but does NOT regenerate them via `build.py`).
- Migrating to a paid private GitHub Pages tier.

## Acceptance crosswalk

Map each ISSUE.md acceptance criterion to phase + task. Phase 9.1 verifies each terminally.

| # | ISSUE.md acceptance criterion | Phase / task |
|---|---|---|
| 1 | `bin/render-gallery` exists, documented, deterministic | 0.2 (shim) + 1.1-1.3 (orchestrator) + 6.1 (full deterministic run) |
| 2 | Running `bin/render-gallery` twice produces no git diff | 0.1 (scrub) + 1.1-1.2 (per-template idempotency) + 6.2 (end-to-end) |
| 3 | Preview PNG dpi reduced; size targets hit; crisp at 220 px | 1.1 (rasterise at meta-dpi) + 2.2 (postcard 100 dpi) + 6.1 |
| 4 | `tools/gallery_build.py` copy-only; fails clearly on missing artifacts | 4.1 (delete render functions) + 4.2 (refactor + `_fail_missing`) + 4.3 (tests) |
| 5 | `bin/check-stale-previews` exists, hash-detects mismatch, clear message | 3.1 + 3.3 (tests) |
| 6 | `bin/validate` invokes `check-stale-previews` as preflight | 3.2 |
| 7 | `.github/workflows/pages.yml::validate-reproductions` runs sla_diff + check-stale-previews; <30s | 5.1 |
| 8 | `.github/workflows/pages.yml::deploy` continues to work | 5.1 (verify deploy job untouched) + 8.2 (push half user-driven) |
| 9 | `docs/render-fidelity.md` describes local-only architecture; CI-fonts permanently OOS | 7.1 |
| 10 | One end-to-end demo: edit SLA → render → commit → push → CI passes → Pages deploy reflects | 8.1 (local) + 8.2 (push procedure documented) |
| 11 | All 17 pages still byte-equivalent to user's Scribus 1.6.4 reference exports | 6.3 + 9.1 (final confirmation) |
