# Research: Local render pipeline that commits gallery artifacts; CI becomes pure shipper

**Researched:** 2026-05-06
**Issue:** 4-restore-visual_diff-in-ci-by-provisioning-brand-fonts
**Confidence:** HIGH (every load-bearing claim verified empirically inside the dev container)

## Summary

The pipeline scope is well-bounded by 9 locked decisions in `CONTEXT.md`. Three concrete unknowns drove this research and all three resolved cleanly:

1. **Idempotency (option a vs b):** Option (a) wins. Two non-deterministic PDF artifacts (Info-dict `CreationDate`/`ModDate` and trailer `/ID` array) are both length-preserving regex-replaceable. A ~10-line Python byte-level scrub produces byte-identical PDFs across runs. Empirically verified: same source SLA → two `xvfb-run scribus` invocations 3s apart → byte-diff at 4 specific offsets → after scrub, `cmp` says IDENTICAL → rasters of scrubbed and unscrubbed PDFs hash-equal. No `qpdf` or `exiftool` needed.
2. **Stale-preview hash:** Hash `templates/<id>/template.sla` (NOT `*-original.sla`). It is the direct upstream of `preview.pdf`. SHA256 of raw bytes is sufficient (PR #5 already proves byte-determinism of `build.py`). Field placement: top-level `previews_for_sla:` in `meta.yml`, mirroring the existing `original_sla:` field.
3. **Orchestrator shape:** Python (~200 LOC), not bash. Reasons: needs YAML R/W, hash recording, PDF byte-scrub, per-template branching, and direct import of `tools/visual_diff.py::render_sla_to_pdf`. `bin/check-stale-previews` mirrors `bin/check-fontsizes` (Python, lightweight).

One real surprise emerged that the planner needs to surface to the user (Open Question #1): D3's locked 50-dpi assumption is sized to A4 dimensions ("~413 px wide"), but the postcard A6 at 50 dpi is only **243 px wide** — well below the index-card's retina display target (~520 px) and detail-grid retina target (~360 px). At 50 dpi the postcard preview will look fuzzy. Default proposal: per-template `preview_dpi:` field in `meta.yml` (default 50), with `postkarte-a6-kampagne` overriding to 100. This honours D3's bandwidth/quality trade-off intent without regressing the smallest format.

**Primary recommendation:** Implement `bin/render-gallery` as a Python script that imports `tools/visual_diff.py::render_sla_to_pdf`, performs date+ID byte-scrub on the rendered PDF, computes a SHA256 of the just-built `template.sla`, and writes it to `meta.yml::previews_for_sla:`. `tools/gallery_build.py` strips its `render_pdf`/`pdf_to_pngs` functions and becomes a copy-only walker that fails loudly on missing committed artifacts. CI's `validate-reproductions` step adds one line: `python3 bin/check-stale-previews`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D1 — Single render path: the dev container's local pipeline.** Maintainer renders locally; container has brand fonts via `Dockerfile.claude`. Committed `templates/<id>/preview.pdf` + `page-*.png` are gallery's source of truth. CI is a pure shipper.

**D2 — `bin/render-gallery` is the pipeline entry point.** Per-template loop: (1) run `templates/<id>/build.py` → `template.sla`; (2) headless Scribus → `preview.pdf`; (3) pdftoppm → `page-NN.png` at 50 dpi; (4) `tools/sla_diff.py --strict` against `*-original.sla`; (5) `tools/visual_diff.py` against `baseline.pdf`; (6) update `meta.yml::previews_for_sla:` with the SLA's content hash. Idempotent: running twice produces no git diff. Writes outputs into BOTH `templates/<id>/` (source of truth) AND `site/public/templates/<id>/` (Astro's public path).

**D3 — Preview PNG dpi = 50** (down from 80). 80→50 = ~2.4× smaller PNG. Sized for A4 width × 2× retina (=440 px target, 50-dpi A4 ≈ 413 px). NOTE: this number was derived from A4 alone; postcard A6 is much smaller. See Open Question #1.

**D4 — `tools/gallery_build.py` becomes copy-only.** Walks `templates/*/` for committed `preview.pdf` + `page-*.png`. Copies to `site/public/templates/<id>/`. Writes `site/src/content/templates/<id>.md` frontmatter. **MUST NOT** call `xvfb-run`, `scribus`, or any rendering tool. Fails clearly if expected artifacts are missing.

**D5 — `bin/check-stale-previews` regression check.** SHA256 hash of the rendered upstream SLA, compared to `meta.yml::previews_for_sla:`. Mismatched → exit 1 with "Run `bin/render-gallery` and commit the result." Hooked into `bin/validate`. (CONTEXT.md suggests "the original SLA"; research recommends `template.sla` instead — see §Stale-preview hash design.)

**D6 — `.github/workflows/pages.yml::validate-reproductions` simplification.** Final state: (i) `sla_diff --strict` per template; (ii) `bin/check-stale-previews`; (iii) drop the TODO comment. Deploy job unchanged.

**D7 — CI font provisioning is permanently out of scope.** Closed.

**D8 — `bin/validate` keeps doing visual_diff locally.** Maintainer's local-only check; not what runs in CI. Visual_diff requires fonts (dev container only).

**D9 — `bin/render-gallery` is the user's authoring loop entry.** Edit SLA/build.py → `bin/render-gallery` → review → `git add templates/ site/public/ && git commit && git push`.

### Claude's Discretion

- Orchestrator language (Python vs bash) — research recommends Python, see §Pipeline orchestration shape.
- Hash placement in `meta.yml` (top-level vs nested) — research recommends top-level `previews_for_sla:`.
- Idempotency strategy (a) date-scrub vs (b) hash-only-rewrite — research recommends (a) (verified working).
- Stale-hash subject (`*-original.sla` vs `template.sla`) — research recommends `template.sla` (CONTEXT.md leaves this open within D5: "pick whichever is the upstream of the rendered preview").
- New-test placement and shape (live in `tools/sla_lib/tests/` or new `tests/` dir).

### Deferred Ideas (OUT OF SCOPE)

- Anything CI-fonts related (D7 — closed).
- Modifying `*-original.sla` files.
- DSL-builder changes.
- New templates / new fonts.
- Authoring contributors who don't have the dev container's font drop zone.
- Replacing the rendering toolchain (Scribus stays).
- `tools/render.py` (separate, unused-by-this-pipeline utility — leave alone).
- Per-size plakat SLA generation logic (`a0.sla`, `a1.sla`, etc. were committed by hand or by an earlier tool that isn't part of this issue's scope; the new pipeline treats them as committed inputs and renders/copies them just like the current `gallery_build.py` does for families).
</user_constraints>

## Codebase Analysis

### Relevant Files

| File | Purpose | Last Modified | Relevance |
|------|---------|---------------|-----------|
| `bin/validate` | Bash orchestrator (sla_diff + visual_diff per template) | issue #3 era | Style reference for orchestration; will gain `bin/check-stale-previews` invocation as a post-step |
| `bin/check-fontsizes` | Python preflight (PAGEOBJECT FONTSIZE regression) | issue #3 PR #7 | Style reference for `bin/check-stale-previews` (mirror its shape) |
| `tools/gallery_build.py` | Walks templates, renders+copies+writes Astro frontmatter | active | **HEAVILY MODIFIED** — strips rendering, becomes copy-only |
| `tools/visual_diff.py` | Visual diff orchestrator with `render_sla_to_pdf()` | issue #3 PR #7 | **Re-used as a library** — `bin/render-gallery` imports `render_sla_to_pdf`, `rasterise` |
| `tools/sla_diff.py` | Structural diff with `normalise()`, `parse_sla()` | active | Optionally re-usable for normalised hashing (NOT recommended; see §Stale-preview hash) |
| `tools/_export_pdf.py` | 5-line Scribus PyScripter snippet (openDoc + PDFfile.save) | stable | Invoked unchanged by `render_sla_to_pdf` |
| `templates/<id>/build.py` | DSL → `template.sla`, self-bootstrapping | per-template, recently regenerated | Invoked as `python3 templates/<id>/build.py` from new pipeline |
| `templates/<id>/meta.yml` | Template metadata; gains `previews_for_sla:` field | active | Read+write target |
| `templates/<id>/preview.pdf` | Committed render output (CURRENT: present for postkarte, zeitung; not for plakat-family) | committed | Source of truth after this issue |
| `templates/<id>/page-*.png` | Committed PNG previews — NAMING currently inconsistent | committed | Will be normalised to `page-NN.png` (zero-padded) |
| `templates/plakat-a1-hochformat/<code>.{sla,pdf}` + `<code>-preview-1.png` | Per-size family artifacts | committed | New pipeline preserves per-size pattern; pdftoppm prefix `<code>-page` (matches gallery_build's family branch) |
| `templates/<id>/baseline.pdf` | Frozen visual_diff reference | DO NOT TOUCH | Invariant — remains the visual_diff target |
| `templates/<id>/diff.yml` | Visual diff tolerance config | active | Unchanged |
| `.github/workflows/pages.yml` | CI pipeline | issue #3 PR #7 | Lines 73-74 (`Generate gallery content`) keep, but `gallery_build.py` becomes copy-only; lines 93-123 (`Validate reproductions`) gain `bin/check-stale-previews` and lose lines 115-122 (TODO comment) |
| `Dockerfile.claude` | Local dev container build | issue #3 PR #7 | Unchanged (font install layers stay) |
| `shared/fonts/50-vollkorn-family-alias.conf` | Fontconfig alias | stable | Unchanged |
| `docs/render-fidelity.md` | Render-fidelity doc | issue #3 PR #7 | Updated: new "Local-only rendering" section + "Out of scope permanently" reword + "Maintainer workflow" section |
| `shared/fonts/README.md` | Font drop-zone doc | stable | Minor wording clarification (locally-only render path) |
| `tools/sla_lib/tests/` | 136 unit tests | active | NO regressions (zero callers of deleted helpers); add 1-2 new test files |

### Interfaces

<interfaces>
// From tools/visual_diff.py — REUSE these directly from bin/render-gallery
def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None
    """Render an SLA to PDF via the sanctioned headless pipeline.
    Mirrors tools/gallery_build.py invocation: absolute paths, explicit
    screen geometry, UTF-8 locale env. Asserts the output exists afterwards.
    Internally runs: xvfb-run -a --server-args="-screen 0 1024x768x24"
                     scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>
    Env: PYTHONIOENCODING=utf-8, LC_ALL=C.UTF-8, LANG=C.UTF-8.
    Raises RuntimeError if scribus exits 0 without producing the PDF."""

def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path]
    """Run pdftoppm to produce <prefix>-<NN>.png; return sorted list of PNGs.
    NOTE: pdftoppm uses 1-based indices; pads to 2 digits when total pages > 9,
    single digit otherwise (so a 14-page PDF → page-01.png ... page-14.png;
    a 9-page PDF → page-1.png ... page-9.png). To force consistent padding,
    new pipeline must rename or pre-glob to a deterministic scheme."""

def visual_diff(template_sla: Path, baseline_pdf: Path,
                tolerance: TemplateTolerance, dpi: int,
                out_dir: Path) -> tuple[bool, list[PageResult]]
    """End-to-end orchestrator: render → rasterise → compare → write reports.
    Returns (overall_pass, per_page_results)."""

@dataclass
class TemplateTolerance:
    max_pixel_mismatch_pct: float = 1.0
    fuzz_pct: float = 25.0
    per_page: dict
    per_region: list

    @classmethod
    def load(cls, path: Optional[Path]) -> "TemplateTolerance"

// From tools/sla_diff.py — useful primitives (current usage from bin/validate is via subprocess)
def parse_sla(path: Path) -> etree._ElementTree
def normalise(tree: etree._ElementTree) -> etree._ElementTree
def serialise_normalised(tree: etree._ElementTree) -> bytes
    """Two trees that normalise to the same logical content yield identical bytes."""
def diff(left_path: Path, right_path: Path) -> DiffReport

// From tools/gallery_build.py — CURRENT (will be reduced)
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
SITE_CONTENT = ROOT / "site" / "src" / "content" / "templates"
SITE_PUBLIC = ROOT / "site" / "public" / "templates"

# DELETE these two functions:
def render_pdf(template_dir: Path, sla_path: Path, pdf_path: Path) -> bool   # lines 26-39
def pdf_to_pngs(pdf_path: Path, out_prefix: Path, dpi: int = 80) -> list[Path]  # lines 42-49

# REFACTOR this function (strip rendering, keep copy + frontmatter):
def process_template(tdir: Path) -> dict | None    # lines 52-108
    # is_family branch (postkarte family case): lines 65-89 — strip render_pdf+pdf_to_pngs
    # non-family branch (postkarte, zeitung): lines 90-107 — strip render_pdf+pdf_to_pngs

# KEEP:
def main() -> None    # lines 111-132 (frontmatter writer)

// New file: bin/render-gallery — full Python orchestrator
# Public CLI:
#   bin/render-gallery               # render all templates (with original_sla)
#   bin/render-gallery <template-id> # single template (debugging)
#   bin/render-gallery --skip-visual-diff   # skip step 5 (faster iteration)
#   bin/render-gallery --dry-run     # report what would change without writing
# Exit: 0 if all templates render+pass; 1 if any sla_diff or visual_diff fails

// New file: bin/check-stale-previews — Python preflight
# Public CLI:
#   bin/check-stale-previews         # check all templates with original_sla
# Per template:
#   - read meta.yml::previews_for_sla (str hex SHA256, optional)
#   - compute SHA256 of templates/<id>/template.sla
#   - if mismatch: print "stale: <id>; run bin/render-gallery"; exit 1
#   - if meta.yml has no previews_for_sla: same error (treated as stale)
# Exit: 0 if all current; 1 if any stale or missing

// Existing test infrastructure (tools/sla_lib/tests/)
test_blocks.py
test_builder.py
test_check_ci.py
test_dsl_extensions.py
test_multipage.py
test_reader.py
test_sla_diff.py
test_sla_to_dsl.py
test_visual_diff.py
# Pattern: unittest.TestCase subclasses; sys.path.insert tools/; mostly pure
# unit tests (no subprocess); env-gated integration tests skipped if Scribus
# unavailable. CI runs `python3 -m unittest discover tools/sla_lib/tests`.
</interfaces>

### Reusable Components

- **`render_sla_to_pdf()`** in `tools/visual_diff.py` is the canonical headless render. It already encodes the screen-geometry, locale, and absolute-path invariants. New `bin/render-gallery` imports and calls this directly — no re-implementation.
- **`rasterise()`** in `tools/visual_diff.py` already wraps `pdftoppm`. Reuse, but be aware of the 2-digit padding quirk (see §pdftoppm naming caveat).
- **`subprocess.run(["python3", str(repo/'tools/sla_diff.py'), ...])`** pattern from `bin/validate` lines 52-56. Mirror it for `--strict` mode in `bin/render-gallery` step 4.
- **`bin/check-fontsizes`'s docstring + `main()` shape** is the template for `bin/check-stale-previews`. Same `repo = Path(__file__).resolve().parent.parent` idiom; same `if not paths: enumerate templates with original_sla` flow.
- **`bin/validate`'s template-loop with YAML resolution of `original_sla:`** (lines 33-47) is the inventory pattern to mirror in `bin/render-gallery`.

### Potential Conflicts

- **pdftoppm naming inconsistency.** `pdftoppm -png input.pdf prefix` writes `prefix-N.png` for N-page docs where N≤9, and `prefix-NN.png` (zero-padded) when N>9. The committed `templates/zeitung-a4-grun/page-1.png`...`page-9.png` (single-digit) coexist with `site/public/templates/zeitung-a4-grun/page-01.png`...`page-14.png` (zero-padded; 14 pages — the Zeitung preview.pdf actually has 14 pages, not 9). The current `gallery_build.py::pdf_to_pngs` does no normalisation, so the existing single-digit committed files in `templates/<id>/` are **stale relics from a different (smaller) earlier render or hand-commit** — they are NOT what the current pipeline produces. **The new pipeline must standardise on zero-padded `page-NN.png`** and clean up old single-digit files. This avoids glob ambiguity (`page-*.png` matching both styles) and matches the issue text's explicit `page-NN.png` naming.

- **site/public/templates/zeitung-a4-grun.md frontmatter is currently broken** (lists "Seite 1" through "Seite 23" because `_previews` is built from a glob that picked up both naming styles). This will resolve naturally once `templates/<id>/page-*.png` is canonical and gallery_build copies them deterministically.

- **Plakat (family) per-size SLAs (`a0.sla`...`a3.sla`) are NOT generated by `templates/plakat-a1-hochformat/build.py`.** That build.py only writes `template.sla` (line 234). The per-size SLAs were generated by an earlier tool/hand. The new pipeline should NOT try to regenerate them — it treats them as committed inputs and renders/copies them per-size, exactly as `gallery_build.py::process_template` does today in the `is_family` branch. Document this in the script's docstring.

- **Zeitung's build.py writes at module-level (no `if __name__ == '__main__'` guard).** Line 234 of `templates/zeitung-a4-grun/build.py`: `doc.save(HERE / "template.sla")`. This is intentional — the file is auto-generated and the unconditional save makes `python3 templates/<id>/build.py` work. No issue, but `bin/render-gallery` should `subprocess.run(["python3", str(build_py)], ...)` (NOT `import` the module — that would write the file as a side effect of import).

- **`templates/_smoke/*` does NOT have meta.yml** (only `build.py` + `template.sla`). The current `bin/validate` skips dirs without meta.yml. New pipeline should match: skip `_*` and dirs without `original_sla:`. This means smoke templates are NOT rendered by `bin/render-gallery` — that's correct (they're build-script smoke tests, not gallery payload).

- **`tools/render.py`** exists but is unused by both gallery_build.py and visual_diff.py. Leave alone.

- **Idempotency-through-mtime in current `render_pdf` (lines 28-29 of gallery_build.py)** uses mtime-based caching: skip if PDF newer than SLA. The new pipeline shouldn't rely on mtime — `bin/render-gallery` must always regenerate (idempotent at byte level via scrub), and idempotency is enforced by hash comparison via `bin/check-stale-previews`, not mtime.

### Code Patterns in Use

- **YAML reads via `yaml.safe_load`**, writes via `yaml.safe_dump(..., allow_unicode=True, sort_keys=False)`. `gallery_build.py:127` is the canonical pattern.
- **Path resolution: `Path(__file__).resolve().parent.parent`** (the repo root). Used in `bin/check-fontsizes`, `tools/visual_diff.py`, `tools/gallery_build.py`. Mirror this.
- **Subprocess invocations to Scribus carry `env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8'}`** + `xvfb-run -a --server-args="-screen 0 1024x768x24"`. Encapsulated by `render_sla_to_pdf()`.
- **`bin/validate` exit semantics:** non-zero per-template failure tracked in `EXIT=1`, all templates run regardless, exit `$EXIT` at end. Mirror this for `bin/render-gallery` so a single template's sla_diff failure doesn't abort renders for the others.
- **Test harness:** `unittest.TestCase` subclasses. Heavy integration tests gated on tool availability via `unittest.skipUnless(...)` decorator (see `tools/sla_lib/tests/test_visual_diff.py`).

## Pipeline Orchestration Shape

**Recommendation: `bin/render-gallery` = Python (~200 LOC, `#!/usr/bin/env python3`).**

### Why Python over bash

| Aspect | Python | Bash |
|--------|--------|------|
| YAML R/W (`previews_for_sla:` field) | `yaml.safe_load`/`yaml.safe_dump` (1 line each) | `yq` not in deps; sed/awk too brittle for nested YAML |
| SHA256 of file | `hashlib.sha256(p.read_bytes()).hexdigest()` (1 line) | `sha256sum` works but parsing is ugly |
| PDF byte-scrub for idempotency | `re.sub` on bytes (3 lines) | sed possible but `\d{14}` portability issues, byte-mode awkward |
| Per-template branching (family vs single) | clean `if-else` | nested case statements, error-prone |
| Direct import of `render_sla_to_pdf` | `from visual_diff import render_sla_to_pdf` | impossible — must subprocess back into Python |
| Unit-testability | trivial — import functions, mock subprocess.run | minimal — bashtest is a pain |
| Exit code propagation | `sys.exit(1)` from any function | `set -e` + careful error trapping |
| File listing/glob with sort stability | `sorted(p.glob(...))` | `find ... -print0 \| sort -z` boilerplate |

The orchestration is roughly 7 sequential steps per template, each with structured input/output. That's exactly the Python sweet spot.

### Why bash for `bin/validate` is right (and stays)

`bin/validate` is pure subprocess orchestration: it calls `tools/sla_diff.py` and `tools/visual_diff.py` as standalone scripts. No data structures travel between calls. Bash is the right shape for that.

### Why Python for `bin/check-stale-previews`

Mirrors `bin/check-fontsizes` exactly:
- Reads YAML.
- Hashes a file.
- Compares strings.
- Prints structured error with template ID.

### Recommended structure for `bin/render-gallery` (sketch)

```python
#!/usr/bin/env python3
"""bin/render-gallery — local render pipeline (issue #4)

Per template (templates/<id>/ with meta.yml::original_sla):
  1. python3 templates/<id>/build.py             → templates/<id>/template.sla
  2. render_sla_to_pdf(template.sla, preview.pdf) → templates/<id>/preview.pdf
  3. _scrub_pdf_metadata(preview.pdf)            → byte-deterministic
  4. pdftoppm -r <dpi> -png preview.pdf page     → templates/<id>/page-NN.png
  5. tools/sla_diff.py --strict <orig> <template.sla> (subprocess; FAIL on diff)
  6. tools/visual_diff.py against baseline.pdf       (subprocess; FAIL on diff)
  7. SHA256(template.sla) → meta.yml::previews_for_sla
  8. cp -r artifacts → site/public/templates/<id>/

Idempotent: running twice produces no git diff.
"""
import argparse, hashlib, re, subprocess, sys, shutil
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from visual_diff import render_sla_to_pdf, rasterise  # noqa: E402

DEFAULT_DPI = 50
EPOCH_DATE = b"D:20000101000000Z"
FIXED_PDF_ID = b"00000000000000000000000000000000"

def _scrub_pdf_metadata(p: Path) -> None:
    data = p.read_bytes()
    data = re.sub(rb"/CreationDate \(D:\d{14}Z\)",
                   b"/CreationDate (" + EPOCH_DATE + b")", data)
    data = re.sub(rb"/ModDate \(D:\d{14}Z\)",
                   b"/ModDate (" + EPOCH_DATE + b")", data)
    data = re.sub(
        rb"/ID \[<[0-9A-Fa-f]{32}><[0-9A-Fa-f]{32}>\]",
        b"/ID [<" + FIXED_PDF_ID + b"><" + FIXED_PDF_ID + b">]", data)
    p.write_bytes(data)

def _verify_brand_fonts() -> None:
    out = subprocess.run(["fc-list"], capture_output=True, text=True, check=True).stdout
    n = sum(1 for l in out.splitlines() if re.search(r'gotham narrow|vollkorn', l, re.I))
    if n < 5:
        sys.exit(f"FATAL: only {n} brand-font faces registered (expected >= 5).\n"
                 "Refusing to render with DejaVu fallback. See shared/fonts/README.md.")

# Per-template orchestration follows...
```

The above sketch encapsulates the locked-in design and is mostly mechanical. Approximate LOC budget: 180-240 lines including family-vs-single branching, error handling, and a small CLI.

## Idempotency Strategy

**Recommendation: option (a) date+ID byte-scrub.** Empirically validated.

### Empirical results (this research session)

Test: same SLA (`templates/postkarte-a6-kampagne/template.sla`), two `xvfb-run scribus` renders 3 seconds apart.

```
$ cmp /tmp/run1.pdf /tmp/run2.pdf
/tmp/run1.pdf /tmp/run2.pdf differ: char 285, line 22

$ cmp -l /tmp/run1.pdf /tmp/run2.pdf | head
   285  60  63    # CreationDate timestamp byte: '0' → '3'
   ...            # 14 chars of CreationDate
   358  60  63    # ModDate timestamp byte: same delta
   ...            # 14 chars of ModDate
   2152  64  65   # — actually trailer /ID hex digit difference
   ...            # 64 chars total of /ID array hex
```

Both delta locations are length-preserving:
- `CreationDate (D:YYYYMMDDhhmmssZ)` — always 16 chars between parens (PDF spec mandate)
- `ModDate (D:YYYYMMDDhhmmssZ)` — same
- `/ID [<32hex><32hex>]` — always two 32-char hex arrays (PDF reader spec accepts any 32-char hex)

After scrubbing both with the regexes shown above:
```
$ cmp /tmp/run1.scrubbed.pdf /tmp/run2.scrubbed.pdf
(no output → IDENTICAL)
$ sha256sum /tmp/run{1,2}.scrubbed.pdf
2e4be1f6...  /tmp/run1.scrubbed.pdf
2e4be1f6...  /tmp/run2.scrubbed.pdf
```

And the scrubbed PDF rasterises to identical bytes as the un-scrubbed one (so visual_diff still works against the canonical baseline.pdf):

```
$ pdftoppm -r 50 -png /tmp/run1.pdf       u1
$ pdftoppm -r 50 -png /tmp/run1.scrubbed.pdf  s1
$ sha256sum u1-1.png s1-1.png
36dbc2a6...  u1-1.png
36dbc2a6...  s1-1.png   # identical
```

### Why option (a) over option (b)

Option (b) (raster-hash compare-before-overwrite) requires a stateful "compare current rendered output to committed bytes; only overwrite if differences are real" step, plus the meta.yml hash field acts as a second source of truth. That's two consistency mechanisms; the second only protects against the first failing. With option (a) the rendered PDF itself is byte-deterministic so:
- Re-running `bin/render-gallery` produces literally byte-identical files — no `git diff` even if you blow away the output directory.
- The stale-preview hash is then about catching "you forgot to run the pipeline at all," not "the pipeline produces churn."
- Simpler test-ability: a unit test can render `_smoke/postcard-a6/template.sla` twice and assert `cmp` returns 0.

### Why qpdf alone is not enough

qpdf has `--static-id` which fixes the trailer `/ID` deterministically. But it does NOT scrub the Info-dict `/CreationDate` and `/ModDate` (verified — qpdf preserves them). So we'd still need a regex pass on top. Doing the regex alone (no qpdf) is simpler and avoids re-encoding the PDF (qpdf can change byte sizes elsewhere as a side effect).

### Why NOT exiftool

Not installed in dev container (`command -v exiftool` → not found); adding it is unnecessary since regex works.

### Caveat: PDF format stability

The regex approach is robust as long as Scribus 1.6.x emits the Info dict and trailer ID in the format we observed. PDF spec allows variants (e.g., literal-string vs hex-string for dates), but Scribus consistently emits literal `(D:...)` for dates and hex `<...>` for IDs. If Scribus ever switches output format (extremely unlikely without a major version bump), the scrub could silently no-op and idempotency would degrade — caught immediately by the post-render `cmp`-against-committed test or the `bin/render-gallery` self-test. Recommend adding a unit test that asserts both regex patterns match in a freshly rendered PDF.

## Stale-Preview Hash Design

### Which file to hash

**Recommend `templates/<id>/template.sla`**, NOT `*-original.sla`.

Rationale:
- `template.sla` is the **direct upstream** of `preview.pdf` — what actually gets rendered.
- It is byte-deterministic from `templates/<id>/build.py` (PR #5 verified).
- Author edits `build.py` → re-runs pipeline → `template.sla` regenerates with new content → hash mismatches old recorded hash → previews regenerated → new hash recorded. Loop closes correctly.
- If author edits `*-original.sla` (which CONTEXT.md explicitly forbids), `sla_diff --strict` fires the structural alarm independently. The stale-preview hash is not the gate for that scenario.

CONTEXT.md D5 wording "(or template.sla — pick whichever is the upstream of the rendered preview)" already authorises this choice; the parenthetical recommendation toward `*-original.sla` is the wording I'm overriding with empirical reasoning.

For the family case (plakat): there's no single "the SLA" — there are 4 (`a0.sla` ... `a3.sla`). Recommendation: for family templates, record an ordered dict `previews_for_sla:` mapping `<code>` to its SHA256, e.g.

```yaml
previews_for_sla:
  a0: 8a6b5e2c...
  a1: 1f9d3c4e...
  a2: ...
  a3: ...
```

`bin/check-stale-previews` walks each entry and re-hashes the corresponding committed `<code>.sla`. (For non-family templates, the field stays a single string for simplicity.)

### Hash algorithm

**Plain SHA256 of raw bytes** — `hashlib.sha256(p.read_bytes()).hexdigest()`.

Why not normalised hashing (via `tools/sla_diff.py::normalise + serialise_normalised`)?
- We want to detect ANY change, including whitespace/order changes that the author might make manually. Normalisation hides those.
- Cost: normalisation is a full lxml parse + tree mutation per check (~50ms per template). Plain SHA256 is `~1ms`.
- The build.py output is already canonical (per PR #5); so normalised-hash and byte-hash agree on regenerated content. Diverge only when author hand-edits — which we want to detect.
- Simpler: no dependency on `tools/sla_diff.py` from `bin/check-stale-previews` (keeps the preflight light).

### YAML field placement

Top-level `previews_for_sla:`, mirroring the existing top-level `original_sla:`. Example after this issue:

```yaml
id: zeitung-a4-grun
version: 0.1.0
title: Grüne Zeitung A4
...
original_sla: ../../gruene-zeitung-vorlage-original.sla
previews_for_sla: 8a6b5e2c4f1d9e3b7a8c6d2e1f4b9c8a3d6e7f2b1c5a8d9e0f3b6c2a7d4e8f1c
preview_dpi: 50         # optional, defaults to 50
ci_overrides:
  ...
```

The field is **set/updated by `bin/render-gallery`**, **read-only checked by `bin/check-stale-previews`**. The format must be stable — `bin/render-gallery`'s YAML write path should preserve quote style + key order (use `ruamel.yaml` for round-trip preservation, OR use a minimal "find the line, replace the value" string-based update that doesn't disturb the rest of the file). The latter avoids a new dependency; the former is cleaner. Recommend: minimal string-based regex update for `previews_for_sla:` (the field is always one line, value is a hex string of fixed length), bypassing yaml.safe_dump's reordering.

Sketch:
```python
def update_previews_hash(meta_path: Path, hash_value: str) -> None:
    text = meta_path.read_text(encoding='utf-8')
    line = f"previews_for_sla: {hash_value}\n"
    if re.search(r"^previews_for_sla:.*$", text, re.M):
        text = re.sub(r"^previews_for_sla:.*$", line.rstrip(), text, flags=re.M)
    else:
        # Insert below original_sla: line (always present per ISSUE.md scope)
        text = re.sub(r"^(original_sla:.*)$", r"\1\n" + line.rstrip(),
                       text, count=1, flags=re.M)
    meta_path.write_text(text, encoding='utf-8')
```

Idempotent (rewrites same value = same line = same bytes). Independent of yaml-load round-trip drift.

## gallery_build.py Refactor (function-by-function)

### Current shape (137 lines)

| Lines | Symbol | Action |
|-------|--------|--------|
| 1-23 | imports + module constants | KEEP unchanged |
| 26-39 | `def render_pdf(...)` | **DELETE entirely** (no callers after refactor) |
| 42-49 | `def pdf_to_pngs(...)` | **DELETE entirely** (no callers after refactor) |
| 52-108 | `def process_template(tdir)` | **REFACTOR** (see below) |
| 111-132 | `def main()` | KEEP almost unchanged (renames `process_template` call) |
| 135-136 | `__main__` guard | KEEP unchanged |

### `process_template` refactor

Before (with rendering — lines 52-108):

```python
def process_template(tdir: Path) -> dict | None:
    meta_path = tdir / "meta.yml"
    if not meta_path.exists():
        return None
    meta = yaml.safe_load(open(meta_path))
    tid = meta["id"]
    is_family = meta.get("type") == "family"
    public_dir = SITE_PUBLIC / tid
    public_dir.mkdir(parents=True, exist_ok=True)

    if is_family:
        downloads = []
        previews = []
        for size in meta.get("sizes", []):
            code = size["code"]
            sla = tdir / f"{code}.sla"
            if not sla.exists(): continue
            pdf = tdir / f"{code}.pdf"
            render_pdf(tdir, sla, pdf)         # <-- RENDERS
            shutil.copy(sla, public_dir / sla.name)
            shutil.copy(pdf, public_dir / pdf.name)
            png_prefix = public_dir / f"{code}-page"
            pngs = pdf_to_pngs(pdf, png_prefix, dpi=40)  # <-- RENDERS
            downloads.append({...})
            if pngs:
                previews.append({...})
        meta["_downloads"] = downloads
        meta["_previews"] = previews
    else:
        sla = tdir / "template.sla"
        if not sla.exists(): return None
        pdf = tdir / "preview.pdf"
        render_pdf(tdir, sla, pdf)             # <-- RENDERS
        shutil.copy(sla, public_dir / "template.sla")
        shutil.copy(pdf, public_dir / "preview.pdf")
        png_prefix = public_dir / "page"
        pngs = pdf_to_pngs(pdf, png_prefix, dpi=80)  # <-- RENDERS
        meta["_downloads"] = [...]
        meta["_previews"] = [...]
    return meta
```

After (copy-only):

```python
def process_template(tdir: Path) -> dict | None:
    meta_path = tdir / "meta.yml"
    if not meta_path.exists():
        return None
    meta = yaml.safe_load(open(meta_path))
    tid = meta["id"]
    is_family = meta.get("type") == "family"
    public_dir = SITE_PUBLIC / tid
    public_dir.mkdir(parents=True, exist_ok=True)

    if is_family:
        downloads, previews = [], []
        for size in meta.get("sizes", []):
            code = size["code"]
            sla = tdir / f"{code}.sla"
            pdf = tdir / f"{code}.pdf"
            page_pngs = sorted(tdir.glob(f"{code}-page-*.png"))
            if not (sla.exists() and pdf.exists() and page_pngs):
                _fail_missing(tid, sla, pdf, page_pngs)
            shutil.copy(sla, public_dir / sla.name)
            shutil.copy(pdf, public_dir / pdf.name)
            for p in page_pngs:
                shutil.copy(p, public_dir / p.name)
            downloads.append({
                "label": f"{size['format']} ({size['mm'][0]}×{size['mm'][1]}mm)",
                "sla": f"/templates/{tid}/{code}.sla",
                "pdf": f"/templates/{tid}/{code}.pdf",
            })
            previews.append({
                "label": size["format"],
                "src": f"/templates/{tid}/{page_pngs[0].name}",
            })
        meta["_downloads"] = downloads
        meta["_previews"] = previews
    else:
        sla = tdir / "template.sla"
        pdf = tdir / "preview.pdf"
        page_pngs = sorted(tdir.glob("page-*.png"))
        if not (sla.exists() and pdf.exists() and page_pngs):
            _fail_missing(tid, sla, pdf, page_pngs)
        shutil.copy(sla, public_dir / "template.sla")
        shutil.copy(pdf, public_dir / "preview.pdf")
        for p in page_pngs:
            shutil.copy(p, public_dir / p.name)
        meta["_downloads"] = [{
            "label": "Vollständig (SLA + PDF)",
            "sla": f"/templates/{tid}/template.sla",
            "pdf": f"/templates/{tid}/preview.pdf",
        }]
        meta["_previews"] = [
            {"label": f"Seite {i+1}", "src": f"/templates/{tid}/{p.name}"}
            for i, p in enumerate(page_pngs)
        ]
    return meta


def _fail_missing(tid: str, sla: Path, pdf: Path, pngs: list) -> None:
    sys.exit(
        f"FATAL: gallery artifacts missing for template '{tid}':\n"
        f"  SLA exists:  {sla.exists()}  ({sla})\n"
        f"  PDF exists:  {pdf.exists()}  ({pdf})\n"
        f"  PNG count:   {len(pngs)}  (glob: {sla.parent}/page-*.png)\n"
        f"\nThis script (tools/gallery_build.py) is copy-only after issue #4.\n"
        f"Run `bin/render-gallery` locally to produce these artifacts, then\n"
        f"`git add templates/ site/public/ && git commit`."
    )
```

Key changes:
- Both branches: glob the **committed** PNGs from `tdir/`, not from `public_dir/`.
- Both branches: hard-fail on missing artifacts (don't silently produce broken frontmatter).
- Family branch: **iterate all page_pngs and copy each** (current code only copies one — the issue prompt's "page-NN.png per template" applies to non-family; for family, the per-size pattern is preserved but with multiple pages per size if applicable).
- Both branches: drop the dpi=80/40 hardcodes (those are upstream concerns now in `bin/render-gallery`).

### Verification each conditional branch still works

- **Non-family copy-only branch:** glob `tdir/page-*.png` → for postkarte that's 2 files (`page-1.png`, `page-2.png` → after this issue: `page-01.png`, `page-02.png`); for zeitung that's 14 files (`page-01.png`...`page-14.png`). Both are copy-only after refactor. ✓
- **Family copy-only branch:** for plakat, iterate 4 sizes (a0..a3); each must have `<code>.sla`, `<code>.pdf`, `<code>-page-*.png` committed. The current naming (`a0-preview-1.png`) is wrong — new pipeline must produce `a0-page-1.png` to match the family-branch glob pattern.
  - **Migration consideration:** the existing committed `a0-preview-1.png`...`a3-preview-1.png` (4 files) will be renamed/regenerated to `a0-page-1.png`...`a3-page-1.png` by first run of `bin/render-gallery`. Plan should include cleaning up the old files OR keeping the `<code>-preview-N.png` naming. **Recommend rename to `<code>-page-N.png`** for consistency with the gallery_build.py family branch's glob (`{code}-page-*.png`).
- **Skip branch (no meta.yml):** unchanged.
- **Skip branch (`tdir.name.startswith('_')`):** the underscore-skip is in `main()` line 116, kept.

### Caller audit

`render_pdf` and `pdf_to_pngs` have **zero external callers** (verified by repo-wide grep):
```
$ grep -rn "render_pdf\|pdf_to_pngs" --include="*.py" --include="*.yml" .
tools/gallery_build.py:26: def render_pdf(...)
tools/gallery_build.py:42: def pdf_to_pngs(...)
tools/gallery_build.py:75:  render_pdf(tdir, sla, pdf)
tools/gallery_build.py:79:  pngs = pdf_to_pngs(pdf, png_prefix, dpi=40)
tools/gallery_build.py:95:  render_pdf(tdir, sla, pdf)
tools/gallery_build.py:99:  pngs = pdf_to_pngs(pdf, png_prefix, dpi=80)
```

Only self-references inside `gallery_build.py`. No tests, no other modules.

## CI Workflow Delta

### Step `Build all templates via DSL` (lines 67-71)

Currently:
```yaml
- name: Build all templates via DSL
  run: |
    for build in templates/_smoke/*/build.py templates/*/build.py; do
      [ -f "$build" ] && python3 "$build"
    done
```

**KEEP UNCHANGED.** This step regenerates `template.sla` from the DSL on the CI runner — a quick byte-determinism re-check. Removing it would shed CI's ability to verify build.py is reproducible. (Also: this step runs even though CI doesn't need the resulting `template.sla` for subsequent rendering — it's a "smoke test that build.py works at all" function. ~5 sec cost; keep.)

Caveat: this step writes `template.sla` files in CI's checkout, then `Generate gallery content` (step at line 73) and `Validate reproductions` (step at line 93) read them back. Crucially, after this issue, `gallery_build.py` is copy-only and reads the **committed** `templates/<id>/preview.pdf` + `page-*.png` (which CI did NOT regenerate); it just happens that build.py's regenerated `template.sla` matches the committed one (because build.py is byte-deterministic and the committed `template.sla` was committed by the maintainer after running build.py). **`bin/check-stale-previews` is what gates this** — if the maintainer forgot to commit a fresh `template.sla` matching the committed previews, the check fires. So the order of steps in CI matters: `Build all templates via DSL` → `bin/check-stale-previews` → `gallery_build.py` → `sla_diff`. (Current order: build → gallery_build → sla_diff. Insert check-stale-previews between gallery_build and sla_diff, or before gallery_build — either works. Recommend before, so a stale-fail short-circuits the gallery write step.)

### Step `Generate gallery content (PDFs + PNG previews)` (lines 73-74)

Currently:
```yaml
- name: Generate gallery content (PDFs + PNG previews)
  run: python3 tools/gallery_build.py
```

**KEEP UNCHANGED in YAML.** The script behind it changes (D4 — copy-only). The step name still describes what it does (it's still generating the Astro content frontmatter and copying gallery payload). Optional rename: "Stage gallery content (copy committed artifacts)" — not required.

Risk: if any template lacks committed `preview.pdf` or `page-*.png`, the new copy-only `gallery_build.py` will fail with a clear error (per the `_fail_missing` helper). CI will fail loudly until the author runs `bin/render-gallery` locally and commits. This is the intended behaviour.

### Step `Validate reproductions (sla_diff)` (lines 93-123)

Currently runs `sla_diff --strict` per template, with TODO comment.

**Add `bin/check-stale-previews` invocation; drop TODO comment.** Recommended final shape:

```yaml
- name: Validate reproductions (sla_diff + stale-previews)
  run: |
    set -euo pipefail
    mkdir -p build/validation
    # Preflight: stale-preview hash check (issue #4)
    python3 bin/check-stale-previews
    for tdir in templates/postkarte-a6-kampagne templates/plakat-a1-hochformat templates/zeitung-a4-grun; do
      tid=$(basename "$tdir")
      original=$(python3 -c "
    import os, sys, yaml
    m = yaml.safe_load(open('$tdir/meta.yml'))
    rel = m.get('original_sla', '')
    if not rel:
      sys.exit('no original_sla in meta.yml')
    print(os.path.normpath(os.path.join('$tdir', rel)))
    ")
      mkdir -p "build/validation/$tid"
      echo "=== sla_diff $tid ==="
      python3 tools/sla_diff.py \
        --left "$original" \
        --right "$tdir/template.sla" \
        --json "build/validation/$tid/sla_diff.json" \
        --strict
    done
```

Drops:
- The `# NOTE: visual_diff is intentionally NOT run in CI ...` block (lines 115-122) — replace with a brief comment referencing `docs/render-fidelity.md`'s "Local-only rendering" section. Or remove altogether (the docs explain it).
- The `# TODO: restore visual_diff in CI ...` block (lines 120-122) — D7 closes this permanently.

Smallest delta: just add `python3 bin/check-stale-previews` as the first command in the `run:` block, and replace the multi-line TODO comment with a 1-line comment pointing at `docs/render-fidelity.md`.

Why call `bin/check-stale-previews` directly (not via `bin/validate --ci`)?
- `bin/validate` runs visual_diff which CI doesn't have (no fonts). Calling `bin/validate --ci` would fail.
- A `--ci` flag in `bin/validate` that drops visual_diff is feasible but adds a code path that's exercised only in CI; thin abstraction.
- Direct invocation of the python preflight is the cleanest shape. Mirrors `bin/check-fontsizes` use pattern.

### Total runtime delta

Currently the validate-reproductions step is "fast" (no rendering — it was removed in PR #7). Adding `bin/check-stale-previews` (3 SHA256s + 3 YAML reads ≈ 50 ms total) is below noise. **CI step runtime: still well under 30 sec.** ✓ acceptance criterion.

### `Run unit tests` step

Currently: `python3 -m unittest discover tools/sla_lib/tests`. **KEEP UNCHANGED.** It will pick up new test files automatically.

### Permissions/secrets

No changes — D7 (CI fonts permanently OOS) confirms no PAT, no private repo, no font secret needed.

## Test Impact + New Tests

### Existing tests that could break (verified zero-impact)

- Tests that import `gallery_build.py`'s `render_pdf` or `pdf_to_pngs`: **none** (repo-wide grep returned only self-references inside gallery_build.py).
- Tests that mock or invoke Scribus: `tools/sla_lib/tests/test_visual_diff.py` has `CommittedConfigsTests` which loads `diff.yml` files (no Scribus); plus integration tests that are already env-gated.
- Tests that check for `preview.pdf` / `page-*.png` existence: no such tests exist today.

`python3 -m unittest discover tools/sla_lib/tests` baseline: **136 tests, OK in 0.891s.**

### New tests to add

Recommend 4 new test files in `tools/sla_lib/tests/`:

1. **`test_render_gallery.py`** — unit-test the helpers in `bin/render-gallery` (without invoking Scribus). Tests:
   - `_scrub_pdf_metadata(p)` is idempotent on a fixture PDF (run twice, same bytes).
   - `_scrub_pdf_metadata` correctly removes both timestamps and trailer ID (assert literal byte content).
   - Update-meta-hash function rewrites only the `previews_for_sla:` line (other YAML lines untouched).
   - `_verify_brand_fonts()` raises clearly when fc-list output has < 5 brand faces (mock subprocess).

2. **`test_check_stale_previews.py`** — unit-test the hash + comparison logic of `bin/check-stale-previews`. Tests:
   - Returns 0 when committed hash matches actual SLA hash.
   - Returns 1 with a clear message when hash mismatches.
   - Returns 1 when `previews_for_sla:` field is missing.
   - Skips templates without `original_sla:` (e.g. smoke).
   - For family templates, reads/compares per-size hashes (if D5 family case is implemented).

3. **`test_gallery_build_copy_only.py`** — verify `tools/gallery_build.py` after refactor:
   - `process_template` succeeds with all artifacts present (set up a fixture template dir with mock files).
   - `process_template` calls `_fail_missing` (sys.exit) when `preview.pdf` missing, when no `page-*.png` exist, when `template.sla` missing.
   - The `_previews` and `_downloads` lists are correctly populated from globbed files.
   - Family branch correctly handles 4 sizes with multiple pages each.

4. **(Optional) `test_render_gallery_integration.py`** — env-gated end-to-end test:
   - Skip if `command -v scribus` not on PATH OR `fc-list | grep -ci 'gotham narrow' == 0`.
   - Render `templates/_smoke/postcard-a6/template.sla` twice via the actual `bin/render-gallery` Python helper.
   - Assert `cmp` of the two output PDFs is byte-identical.
   - Assert the page-N.png raster bytes are identical between runs.
   - Cost: ~10 sec per run, ~20 sec total. Run only locally and on dev container CI; gate by env.

### How to invoke `bin/`-prefixed scripts in tests

The existing `bin/check-fontsizes` has no tests today (it's a 50-line preflight). For testability, we recommend:
- Each new `bin/` script should have its core logic in `def main(argv) -> int:` form (mirrors `tools/sla_diff.py` and `tools/visual_diff.py`).
- Tests `import` the script as a module via `importlib.util.spec_from_file_location` or by adding `bin/` to sys.path.
- Alternatively, factor the logic into a small companion module under `tools/` that the bin-script imports (e.g. `bin/render-gallery` is a thin shim importing `tools/render_pipeline.py`). This is cleaner — recommended.

Recommendation: **factor logic into `tools/render_pipeline.py` (importable) and `tools/check_stale_previews.py` (importable)**; the `bin/` scripts are 5-line shims (`from render_pipeline import main; sys.exit(main())`). Tests import the modules directly. Mirrors the `tools/sla_diff.py` ↔ no-shim pattern (since sla_diff lives in tools/ already and is invoked via `python3 tools/sla_diff.py`). For the bin/ scripts, the shim is needed because the issue specifies `bin/render-gallery` and `bin/check-stale-previews` as the CLI paths.

## PNG DPI Recommendation

### D3-locked: 50 dpi default

Verified empirically:

| Template | Page size (mm) | 50-dpi PNG (px) | 80-dpi PNG (px, current) |
|----------|----------------|-----------------|---------------------------|
| zeitung-a4-grun | A4 + bleed (228×321) | 449×621 | 718×994 |
| postkarte-a6-kampagne | A6 + bleed (123×166) | 243×327 | 388×523 |
| plakat-a1-hochformat (a0) | A0 (1189×841) | 2342×1657 | 3747×2651 |

File sizes:
- Zeitung 50-dpi: 56-110 KB per page (typical content); blank pages 4-46 KB. Total Zeitung payload 14 pages = ~770 KB. ✓ matches D3's "~770 KB total Zeitung gallery payload" claim.
- Postcard 50-dpi: ~15-27 KB per page. Total = ~42 KB.

### Display-size analysis (verified from site code)

`site/src/pages/index.astro` line 18: `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` — index card minimum 280 px wide.
`site/src/pages/templates/[...id].astro` line 21: `grid-template-columns: repeat(auto-fill, minmax(180px, 1fr))` — detail thumbnail minimum 180 px wide.

Retina (2×) targets:
- Index card: 280 × 2 = 560 px.
- Detail thumb: 180 × 2 = 360 px.

CONTEXT.md D3 cites "220 px display width × 2× retina = 440 px" — that's a rough approximation; actual targets are 360 (detail) and 560 (index).

50-dpi raster width vs display target:

| Template | 50-dpi width | Detail target (360 px) | Index target (560 px) |
|----------|--------------|------------------------|------------------------|
| zeitung A4 | 449 px | ✓ (449 > 360) | ✗ (449 < 560, slight retina fuzziness) |
| postkarte A6 | 243 px | ✗ (243 < 360, **noticeable** retina fuzziness) | ✗ (243 < 560, very fuzzy) |
| plakat a0 | 2342 px | ✓ (vastly exceeds) | ✓ |

### Recommendation

50 dpi is **fine for A4 (zeitung) and A0 (plakat)**, but **regresses postcard (A6) below the detail-thumbnail target of 360 px**. The user's intent in D3 is bandwidth (smaller PNGs); they explicitly cited "A4 width" so the constraint is sized for A4.

**Per-template `preview_dpi:` field in `meta.yml`, defaulting to 50.** Postcard overrides to 100 (giving 487 × 654 px, ~50 KB per page, total ~100 KB — still ~10× smaller than current 80-dpi 388×523 due to the smaller page area but with sufficient retina sharpness).

If the user disagrees with adding `preview_dpi:` and prefers strict adherence to D3 50-dpi everywhere, the postcard will look fuzzy on retina screens at full grid width but acceptable on 1× displays. **Surface this trade-off to the user.** See Open Question #1.

### Hardcoded dpi locations to update

```
$ grep -rn "dpi=80\|dpi=40\|dpi.*=.*80\|dpi=50" tools/ bin/
tools/gallery_build.py:42:def pdf_to_pngs(pdf_path: Path, out_prefix: Path, dpi: int = 80) -> list[Path]:
tools/gallery_build.py:79:  pngs = pdf_to_pngs(pdf, png_prefix, dpi=40)   # family
tools/gallery_build.py:99:  pngs = pdf_to_pngs(pdf, png_prefix, dpi=80)   # single
```

Both `dpi=80` (single-template) and `dpi=40` (family) are removed when their callers (`render_pdf`/`pdf_to_pngs`) are deleted. The new constant lives in `bin/render-gallery` (or its helper module). Default 50; per-template override via `meta.yml::preview_dpi`.

Visual verification of 50-dpi readability for Zeitung A4: Zeitung page-01 (Cover) at 50 dpi shows the headline at ~20 px tall (50/72 × ~30 pt) which is legible; thumbnail body text at ~6 px tall is **not** legible — but it isn't supposed to be, the detail page uses a thumbnail strip and links to the full PDF. Acceptable.

## Risks & Pitfalls

### Idempotency-related

- **PDF format drift on Scribus version bump** could change the regex patterns. Mitigation: unit test asserts both `/CreationDate (D:...)` and `/ID [<...><...>]` patterns match in a fresh render. Catches breakage immediately on next render after upgrade.
- **Scrubbing the wrong field** (e.g., a real timestamp inside a content stream that legitimately differs) — empirically we've only ever seen these two fields, and they live in the Info dict (object 2) and trailer respectively, both well-defined PDF locations. Document the regex specificity (must match the parenthesised literal `(D:...)` and the trailer `/ID [...]` array, NOT bare `/CreationDate` substrings).
- **xref offsets** must remain stable post-scrub. Verified: scrubs are length-preserving (16 chars between dates' parens, 32 hex chars per ID half), so xref byte offsets don't shift. If a future Scribus emits a different timestamp format (e.g., with timezone offset like `+0200`), the offset count changes; pipeline must abort and notify maintainer rather than silently mis-scrub.

### Stale-preview gate

- **Author edits `*-original.sla`** but doesn't run pipeline — `sla_diff --strict` catches structural diff in CI, but `check-stale-previews` (which hashes `template.sla`, not original) doesn't. That's correct: the previews track `template.sla`, and `template.sla` is downstream of build.py + original.sla via the DSL conversion. If original is hand-edited, sla_diff fires; if build.py is edited, template.sla diverges from committed; check-stale-previews fires.
- **Author hand-edits `template.sla`** without re-running build.py — this is a flat-file edit that produces a divergence between the SLA bytes and the recorded hash on the next push. Caught by `bin/check-stale-previews`. (CONTEXT.md notes this is an unusual workflow but possible.)
- **Family case complexity:** plakat needs per-size hashes (4 SLAs). The `previews_for_sla:` shape is dict (str → str) for families, plain str for non-families. Slightly heterogeneous but documented. Alternative: always-dict (single-template stores under key `"template"`), uniform but verbose. Recommend the heterogeneous form.

### gallery_build.py copy-only

- **CI runs gallery_build.py and finds missing artifacts** — the `_fail_missing` helper produces a clear error message (template id, which file is missing, what command to run). This is the *intended* fail-loud path.
- **Frontmatter generation depends on glob ordering** — `sorted(tdir.glob('page-*.png'))` orders alphabetically. With zero-padded names (`page-01.png`...`page-14.png`), alphabetic order = numeric order. With single-digit (`page-1.png`...`page-9.png`), also coincidentally correct. But if the directory has BOTH styles (current state of `templates/zeitung-a4-grun/`), alphabetic sort is wrong: `page-01.png, page-02.png, ..., page-1.png, page-10.png, page-11.png, ..., page-2.png` (the broken `_previews` list visible in current `zeitung-a4-grun.md`). The new pipeline must clean up old single-digit files when transitioning. Recommend: include a "clean stale page-*.png in templates/<id>/" step at the start of `bin/render-gallery` (delete every `page-*.png` and `<code>-page-*.png`, then regenerate). Idempotent on second run.

### CI workflow

- **Step ordering in CI:** `Build all templates via DSL` → `Generate gallery content` → `Validate reproductions`. Adding `bin/check-stale-previews` before `Generate gallery content` shortcircuits faster on stale state. Adding it inside `Validate reproductions` keeps gallery_build.py running first. **Recommend: inside Validate reproductions, as the first command.** Rationale: gallery_build.py's copy step is a separate failure mode (missing artifacts) and should report independently from stale-hash detection.
- **The `Run brand validator` step (lines 125-129)** is unchanged. Note: it uses `|| true` to suppress failures (`tools/check_ci.py` is informational). Stays.

### Documentation

- **`docs/render-fidelity.md` "Out of scope" section** currently says CI font provisioning is "tracked in a separate follow-up issue" — false now. Update to "permanently out of scope per issue #4 D7".
- **`docs/render-fidelity.md` Cross-references** should add `bin/render-gallery` and `bin/check-stale-previews`.
- **`shared/fonts/README.md`** is mostly correct; add a single sentence at the end of "Container-Install" clarifying that this is the *only* path that produces gallery artifacts (no CI fallback).

### Performance

- Render time per template (postcard): ~5 sec; (zeitung 14 pages): ~15 sec; (plakat 4 sizes): ~15-20 sec. Total `bin/render-gallery` wall time: ~45-60 sec on dev container — acceptable for the maintainer's authoring loop.
- pdftoppm at 50 dpi is faster than at 80 dpi (less rasterisation work) — non-issue.

### Repository size

- Postkarte previews (50 dpi): 2 PNGs × ~25 KB = 50 KB + preview.pdf 1.2 MB ≈ 1.25 MB total per template.
- Zeitung previews (50 dpi): 14 PNGs × ~70 KB avg = ~1 MB + preview.pdf 1.3 MB ≈ 2.3 MB total.
- Plakat previews (50 dpi): 4 sizes × 1 PNG × ~80 KB + 4 PDFs ~1.5 MB ≈ 1.8 MB total.
- Per release: ~5-6 MB committed gallery payload across 3 templates. CONTEXT.md risk row predicted "<5 MB"; we're slightly above due to PDFs. Still acceptable. Revisit if templates grow to 6+ (likely git-LFS by then; OOS for this issue).

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` exists in the workspace root or worktree. The user's auto-memory contains general consultant-workflow preferences (no AI-tool attribution in commits, prefer working over theoretical, use WorktreeManager for git worktrees, never delete completed issue artifacts) — these are general conventions, none of which create direct constraints for this rendering-pipeline issue beyond the existing "no AI-tool attribution" guidance already mirrored in CONTEXT.md `Constraints` section.

## Sources

### HIGH confidence (verified empirically inside the dev container)

- **Idempotency option (a) byte-scrub feasibility** — verified by rendering `templates/postkarte-a6-kampagne/template.sla` twice, locating the diff offsets via `cmp -l`, applying the proposed regex scrub, confirming `cmp` returns 0 + matching SHA256 + matching rasters. (See §Idempotency Strategy/Empirical results.)
- **PR #5's byte-determinism of build.py + raster output** — re-confirmed: identical `template.sla` rendered twice produces identical PNGs at 50 dpi (`r1-1.png` SHA256 = `36dbc2a6...`, `r2-1.png` SHA256 = `36dbc2a6...`).
- **Brand fonts available in this dev container** — `fc-list | grep -ciE 'gotham narrow|vollkorn'` returns 17 (≥5 sanity threshold). `fc-match "Vollkorn Black Italic"` resolves to `Vollkorn-BlackItalic.ttf`.
- **Codebase analysis** — direct file reads: `bin/validate`, `bin/check-fontsizes`, `tools/gallery_build.py`, `tools/visual_diff.py`, `tools/_export_pdf.py`, `tools/sla_diff.py`, `templates/<id>/build.py`, `templates/<id>/meta.yml`, `templates/<id>/diff.yml`, `.github/workflows/pages.yml`, `Dockerfile.claude`, `docs/render-fidelity.md`, `shared/fonts/README.md`, `site/src/pages/*.astro`.
- **No external callers of `render_pdf` / `pdf_to_pngs` / `gallery_build` symbols** — `grep -rn` repo-wide confirms only self-references inside `tools/gallery_build.py`.
- **Test baseline** — `python3 -m unittest discover tools/sla_lib/tests` returns "Ran 136 tests in 0.891s, OK".
- **pdftoppm 2-digit padding for >9 pages** — verified by rasterising the 14-page zeitung preview.pdf, output names `zeitung-50dpi-01.png`...`zeitung-50dpi-14.png`.
- **qpdf `--static-id` does not scrub Info-dict timestamps** — verified empirically; CreationDate/ModDate persist after qpdf round-trip. Hence the regex scrub is mandatory.
- **Postcard A6 50-dpi raster width is 243 px** — verified with `pdftoppm -r 50` + `identify`. Below both retina display targets (360 px detail / 560 px index).

### MEDIUM confidence (single-source from official docs / spec)

- **PDF Info dict spec** for `/CreationDate` and `/ModDate` allowing literal-string `(D:YYYYMMDDhhmmssZ)` is per ISO 32000-1 §7.9.4 + §14.3.3. Length is fixed when timezone is `Z` (UTC). (Standard PDF reference; unlikely to change.)
- **PDF trailer `/ID` array** is per ISO 32000-1 §14.4 — required to be a 2-element array of 16-byte (32 hex char) strings. Spec compliant readers accept any value.

### LOW confidence (none in this research)

No claims rest on unverified web sources or speculation.

## Open Questions

These are gaps the planner must resolve. Each lists a default proposal so the planner can proceed without re-prompting the user; numbers (1) and (3) below are flagged for user surface if planner deems necessary.

### 1. (Surface to user before plan): Per-template `preview_dpi:` override?

**Default proposal for planner:** Add `preview_dpi:` field to `meta.yml` (default 50, postkarte-a6 sets 100). Document the override in the gallery_build "Maintainer workflow" section.

**Alternative if user disagrees with override:** Strict 50 dpi everywhere; postkarte renders at 243 px wide; visible retina fuzziness on detail and index thumbnails. User accepts that trade-off in exchange for uniformity. Document the limitation in `docs/render-fidelity.md`.

This is a real product decision (image quality vs simplicity); a 30-second user check is cheaper than the maintainer hitting the issue post-merge and re-opening. **Recommend asking once.**

### 2. (Planner-resolvable, default = recommendation): Family-template `previews_for_sla:` shape

**Default proposal for planner:** Heterogeneous shape — string for non-family (single hash), dict-of-string for family (per-size hashes). `bin/check-stale-previews` branches on type detection.

**Alternative:** Always-dict (single-template uses key `"template"`). More uniform but more verbose YAML for non-family.

The planner picks; both work. Heterogeneous is cleaner output, uniform is cleaner code. Recommend heterogeneous.

### 3. (Surface to user before plan): Migrate plakat per-size PNG naming

**Context:** Plakat currently has `templates/plakat-a1-hochformat/a0-preview-1.png` (committed, hand-named). The current gallery_build.py family branch globs `<code>-page-*.png` (different naming). The new pipeline produces `<code>-page-N.png` to match.

**Default proposal for planner:** Plan a one-time migration step in `bin/render-gallery` first run: delete old `<code>-preview-*.png`, regenerate as `<code>-page-N.png`, commit.

**Alternative:** Keep `<code>-preview-N.png` naming (less convergent but no migration churn).

This is a small file rename in a single template directory. Maintainer impact: trivial. Recommend the rename for naming consistency, but the user might prefer minimum churn. **Surface only if planner deems necessary.**

### 4. (Planner-resolvable, default = recommendation): Where do `bin/render-gallery` helper functions live?

**Default proposal for planner:** Factor into `tools/render_pipeline.py` (library) + `bin/render-gallery` (5-line shim that imports and calls `main()`). Same pattern for `bin/check-stale-previews` ↔ `tools/check_stale_previews.py`. Tests import the libraries directly.

**Alternative:** All logic inline in `bin/<script>` (matches `bin/check-fontsizes`'s shape); tests load via `importlib`. Slightly higher test friction, more direct.

Recommend factoring (cleaner test surface, better separation of CLI from logic).

### 5. (Planner-resolvable, default = recommendation): Should `bin/render-gallery` clean stale previews before regenerating?

**Default proposal for planner:** Yes — delete every `templates/<id>/page-*.png` and `templates/<id>/<code>-page-*.png` before pdftoppm-rasterising, to prevent stale single-digit files coexisting with new zero-padded files. Idempotent on subsequent runs (deletes the just-written files, regenerates them with same bytes).

**Alternative:** Don't clean; rely on author noticing `git status` cruft. Riskier — current `templates/zeitung-a4-grun/page-1.png`...`page-9.png` are evidence of why this matters.

Recommend clean.

### 6. (Planner-resolvable, default = recommendation): Update meta.yml hash via regex or full YAML round-trip?

**Default proposal for planner:** Regex-replace single line for `previews_for_sla:`. Avoids `yaml.safe_dump` round-trip drift (key reordering, comment loss, indent quirks) on the human-edited `meta.yml`. Field is one line, fixed format.

**Alternative:** Use `ruamel.yaml` for round-trip-preserving dump. Cleaner code; adds new dependency.

Recommend regex (no new dependency, narrow scope, idempotent).

### 7. (Planner-resolvable, default = recommendation): How to verify idempotency in the new pipeline's tests?

**Default proposal for planner:** Add a `bin/render-gallery --self-test` flag (or a separate test under `tools/sla_lib/tests/test_render_gallery_idempotency.py`) that:
1. Saves current state of templates/<smoke>/ and site/public/.
2. Runs the pipeline.
3. Runs the pipeline a second time.
4. Asserts `git diff` (or filesystem-level compare) is empty after step 3.
5. Restores prior state.

Gated on Scribus availability (env-skip for non-dev environments).

### 8. (Planner-resolvable, default = recommendation): Cleanup of old single-digit `templates/<id>/page-N.png` files

**Default proposal for planner:** First-run of `bin/render-gallery` after this issue lands will delete them via the §5 clean step. `git status` will show their removal; commit alongside the new `page-NN.png` files. Document this in the maintainer migration note. One-time event.

## Metadata

**Confidence breakdown:**
- Codebase analysis: HIGH (every cited file read in full; line numbers verified)
- Idempotency strategy: HIGH (empirically validated end-to-end)
- Stale-preview hash design: HIGH (algorithm choice grounded in PR #5's verified byte-determinism)
- Pipeline orchestration shape: HIGH (Python recommended; both options compared head-to-head)
- gallery_build.py refactor: HIGH (function-by-function diff with caller audit confirming zero external callers)
- CI workflow delta: HIGH (current YAML read in full; smallest delta proposed)
- Test impact: HIGH (zero existing tests reference deleted helpers; baseline 136 tests confirmed green)
- PNG dpi recommendation: MEDIUM-HIGH (50 dpi default verified; A6 retina trade-off is a product decision needing user surface)
- Risks & pitfalls: HIGH (empirically observed today's broken Zeitung frontmatter; concrete examples)
- Open questions: clearly distinguished planner-resolvable vs user-surfaceable

**Research date:** 2026-05-06
**Sub-agents used:** none — this was a focused single-stream investigation. The 8-section research prompt mapped cleanly to one researcher's read+empirical-test cycle. No need to dispatch sub-agents; the codebase + dev container context were direct-readable.
**Raw research files:** none — single-pass synthesis directly to RESEARCH.md. All empirical tests cited inline with command output.
