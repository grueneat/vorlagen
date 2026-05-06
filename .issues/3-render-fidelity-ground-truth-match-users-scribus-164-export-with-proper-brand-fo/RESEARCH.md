# Research: Render-fidelity ground truth — match user's Scribus 1.6.4 export with proper brand fonts

**Researched:** 2026-05-06
**Issue:** 3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo
**Confidence:** HIGH (codebase trace), MEDIUM (Dockerfile font wire-up — straightforward but unbuilt)

## Summary

The dev-host has already achieved 0-pixel diff between headless render and the user's Scribus 1.6.4 desktop export, for all 17 pages of all 3 templates, by (a) installing the brand fonts at `/root/.local/share/fonts/gruene/`, (b) adding a fontconfig alias for "Vollkorn Black Italic", and (c) the user fixing a `FONTSIZE="11.7"` typo in their Scribus and re-saving the SLAs into `/root/workspace/originals/`. CONTEXT.md (D1–D7) locks the structural changes needed to persist that state into the repo.

This research covers the codebase trace required to retire the workspace-root `*-original.sla` files and adopt `originals/` as canonical. **The trace is exhaustive** — every Python module, every meta.yml, every README, every test that hardcodes the old paths is enumerated below. Missing one of these breaks the issue.

Three findings extend CONTEXT.md non-trivially:

1. **`templates/zeitung-a4-grun/build.py` was generated from the typo'd SLA and embeds 97 `fontsize=11.7` Run(...) parameters.** It must be regenerated (via `tools/sla_to_dsl.py`) from the corrected SLA, or the `bin/validate --strict` sla_diff step will fail with 14 critical + 97 warning issues. Plakat and Postkarte build.py files are unaffected (sla_diff against corrected `originals/` shows them clean).
2. **The Ubuntu CI Unicode-NFC bug fixed by commit `cdfb92b` will be re-introduced** if `originals/` keeps the umlaut filenames (`Grüne Zeitung Vorlage Scribus.sla` etc.). Recommendation: rename `originals/<name>.sla` files to ASCII (`originals/gruene-zeitung-vorlage-original.sla`, etc.) when bringing them into the worktree, preserving the corrected file contents.
3. **CI font-asymmetry is more severe than CONTEXT.md acknowledges.** Today's diff.yml settings (`max_pixel_mismatch_pct: 1.0, fuzz_pct: 5.0` for Zeitung) cannot survive the new baseline.pdf (font-bundled) being diffed against a CI-side DSL render (font-less). The plan must explicitly de-scope `visual_diff` from CI in this PR, leaving sla_diff as the only structural gate, and document that CI re-enables visual_diff once a follow-up issue provisions fonts there.

**Primary recommendation:** Treat this as four atomic commits in one PR — (1) add `originals/` with ASCII names + delete workspace-root duplicates + update all references, (2) regenerate `templates/zeitung-a4-grun/build.py` via converter and refresh `template.sla`, (3) regenerate the three `templates/<id>/baseline.pdf` files via the font-installed renderer, (4) wire fonts into Dockerfile.claude + add the fontconfig alias + skip visual_diff in CI workflow. Ship `docs/render-fidelity.md` alongside.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D1** — `FONTSIZE=11.7` was an oversight; **SLA already corrected by user** in `originals/Grüne Zeitung Vorlage Scribus.sla`. The committed workspace-root `gruene-zeitung-vorlage-original.sla` is stale and must be replaced (not just edited).
- **D2** — Brand fonts live in `/root/workspace/fonts/` (gitignored). Dockerfile.claude installs them at build time when present; sanity-probes with `fc-list | grep -iE 'gotham narrow|vollkorn'` and fails loudly if missing in a build context that should have had them.
- **D3** — Scribus 1.6.3 (Debian arm64) is the canonical render engine; version-floor concern dropped after D1.
- **D4** — `originals/` is the canonical SLA + reference-PDF location. Workspace-root duplicates are deleted; `templates/<id>/meta.yml` and `bin/validate` updated.
- **D5** — `templates/<id>/baseline.pdf` regenerated from corrected `originals/<>.sla` in the font-installed env. New baseline = byte-equivalent to user's Scribus 1.6.4 export.
- **D6** — `docs/render-fidelity.md` documents fonts/aliases/rebaselining/D1-lesson/out-of-scope items.
- **D7** — **CI font provisioning is OUT of scope** for this issue. Per user direction.

### Claude's Discretion
- Exact Dockerfile font-install layer pattern (bind-mount vs conditional COPY)
- Exact mechanism for skipping visual_diff in CI (delete step, mark continue-on-error, or wrap conditionally)
- Ordering of structural commits within the PR
- Form of the FONTSIZE-typo regression check (CONTEXT.md suggested `bin/validate` warning, but the simple grep is too noisy — see "Risks" below)

### Deferred Ideas (OUT OF SCOPE)
- Bundling Gotham Narrow into the public repo (license-blocked)
- CI font provisioning (separate follow-up)
- ECI ISO Coated v2 / PSO Uncoated ICC profile install
- Building Scribus 1.6.4 from source on arm64
- Migrating off Scribus / replacing toolchain
- Cleanup of older `samples-output/originals/*.pdf` (see Open Question #5 — not addressed by CONTEXT.md)

---

## Codebase Analysis

### Workspace state at research time

Worktree: `/root/workspace/.worktrees/3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo/`

| Path | Tracked | State | Note |
|---|---|---|---|
| `gruene-zeitung-vorlage-original.sla` (root) | yes | **stale** — has 139 `FONTSIZE="11.7"` (97 in PAGEOBJECT ITEXTs, 42 in FRAMEOBJECT pasteboard) | To delete |
| `plakat-a1-hochformat-original.sla` (root) | yes | byte-identical to corrected version | To delete |
| `postkarte-vorlage-original.sla` (root) | yes | byte-identical to corrected version | To delete |
| `originals/` | **NO** (parent workspace, outside worktree) | 3 corrected SLAs + 3 user PDF exports, umlaut-named | Must be added with ASCII names |
| `/root/workspace/fonts/` | NO (gitignored) | 16 Gotham Narrow .otf + Vollkorn-BlackItalic.ttf + full Vollkorn family | Used by container build only |
| `/root/.local/share/fonts/gruene/` | n/a | Live install, 17 files, fc-cache populated | Reproducible from `fonts/` |
| `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf` | n/a | Live install, 16 lines | Reproducible from a copy committed to repo |
| `~/.config/scribus/checkfonts150.xml` | n/a | Auto-generated on first scribus run | Container can't pre-populate |

### Files that hardcode the old workspace-root SLA paths (every reference traced)

The complete set, from `git grep -E '(gruene-zeitung\|plakat-a1-hochformat\|postkarte-vorlage)-original\.sla'` filtered to functional code (excluding `.issues/*/{ISSUE,RESEARCH,PLAN,EXECUTION,CONTEXT}.md` which are historical artifacts and don't need updating):

| File | Lines | Reference type | Update needed |
|---|---|---|---|
| `bin/validate` | shell logic at 33-39 reads `original_sla` from each `meta.yml` and resolves it relative to `templates/<id>/` | indirect via meta.yml | none direct (changes via meta.yml) |
| `tools/sla_to_dsl.py` | 24 (docstring example) | docstring usage example | rewrite path in example |
| `templates/postkarte-a6-kampagne/build.py` | 1 (auto-gen header comment) | informational | regenerate header (or hand-edit comment) |
| `templates/plakat-a1-hochformat/build.py` | 1 (auto-gen header comment) | informational | regenerate header (or hand-edit comment) |
| `templates/zeitung-a4-grun/build.py` | 1 (auto-gen header comment) **+ 97 hardcoded `fontsize=11.7` Run(...) params (lines 1146-1162 and onward)** | hard dependency on stale typo | **regenerate via converter** |
| `templates/zeitung-a4-grun/meta.yml` | 18 (`original_sla:` key) | hard reference | update path |
| `templates/plakat-a1-hochformat/meta.yml` | 16 (`original_sla:` key) | hard reference | update path |
| `templates/postkarte-a6-kampagne/meta.yml` | 25 (`original_sla:` key) | hard reference | update path |
| `tools/sla_lib/tests/test_check_ci.py` | 87, 95, 103 (`ROOT / "<filename>"`) | hard test fixtures | update paths |
| `tools/sla_lib/tests/test_reader.py` | 16, 17, 18 (ORIGINALS list) and 54, 58, 62 (EXPECTED dict keys keyed by basename) | hard test fixtures | update paths AND dict keys |
| `tools/sla_lib/tests/test_sla_diff.py` | 24, 25, 26 (ORIGINALS list) | hard test fixtures | update paths |
| `tools/sla_lib/tests/test_sla_to_dsl.py` | 56, 78, 101, 409 (`ROOT / "<filename>"`) | hard test fixtures | update paths |
| `README.md` | 71, 79, 121 (round-trip section examples) | docs | update paths |
| `tools/check_ci.py` | 16 (docstring usage example mentions umlaut filenames) | docstring | optional rewrite |
| `site/src/content/templates/zeitung-a4-grun.md` | 19 (`original_sla:` frontmatter) | auto-generated by `tools/gallery_build.py` from meta.yml | regenerated automatically; commit the regenerated file |
| `site/src/content/templates/plakat-a1-hochformat.md` | 23 | auto-generated | same |
| `site/src/content/templates/postkarte-a6-kampagne.md` | 20 | auto-generated | same |

**No additional path references found** in: `tools/render.py`, `tools/gallery_build.py` (path-agnostic, walks `templates/`), `tools/visual_diff.py`, `tools/_export_pdf.py`, `tools/sla_diff.py`, `templates/_smoke/*/build.py`, `.github/workflows/pages.yml` (resolves via meta.yml).

### Key code paths and how they're affected

#### `bin/validate` (lines 33-39)
```bash
original=$(python3 -c "
import os, sys, yaml
m = yaml.safe_load(open('$tdir/meta.yml'))
rel = m.get('original_sla', '')
if not rel: sys.exit('no original_sla in $tid meta.yml')
print(os.path.normpath(os.path.join('$tdir', rel)))
")
```
Reads `original_sla` from each `templates/<id>/meta.yml` and resolves relative to the template directory. If meta.yml says `original_sla: ../../originals/gruene-zeitung-vorlage-original.sla`, this resolves to `originals/gruene-zeitung-vorlage-original.sla` from repo root. **No code change needed in `bin/validate` itself** — only in the meta.yml files.

#### `.github/workflows/pages.yml` (lines 100-107)
Same Python heredoc as `bin/validate`. Same — no code change, only meta.yml updates propagate. **However, the visual_diff step (lines 116-121) will catastrophically fail in CI** once baseline.pdf is regenerated with fonts but CI runs DSL renders without fonts — see "CI Workflow Impact" below.

#### `tools/visual_diff.py::render_sla_to_pdf` (lines 112-143)
The render entrypoint used both for baseline regeneration (manual) and for CI's DSL render. Invocation is `xvfb-run -a --server-args="-screen 0 1024x768x24" scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>` plus an absolute-paths assertion.

```
def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None:
    sla_abs = sla_path.resolve(); pdf_abs = pdf_path.resolve()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
    _run([
        "xvfb-run", "-a", "--server-args=-screen 0 1024x768x24",
        "scribus", "-g", "-ns", "-py",
        str(repo / "tools" / "_export_pdf.py"),
        str(sla_abs), str(pdf_abs),
    ], env=env)
```
This is the same plumbing the discuss step used to produce 0-pixel-diff renders. Fit-for-purpose for baseline regeneration. **No code change needed.**

#### `tools/_export_pdf.py` (entire file, 6 lines)
```python
import scribus, sys
infile = sys.argv[1]; outfile = sys.argv[2]
scribus.openDoc(infile)
pdf = scribus.PDFfile()
pdf.file = outfile
pdf.save()
```
Uses Scribus's own PDF settings from the SLA's `<PDF>` element. The third "screen" arg passed by `tools/gallery_build.py` is silently ignored (no-op). PDF output includes non-deterministic CreationDate metadata and a per-run ID — **but visual_diff is raster-based** so it doesn't care. CONTEXT.md confirms byte-identical output at the rasterization layer for two consecutive renders of the same SLA. **No change needed.**

#### `tools/sla_diff.py::drop_frameobjects` (line 248-253)
```python
def drop_frameobjects(tree):
    """Remove FRAMEOBJECT elements (orphan scratch items, OwnPage=-1)."""
    doc = tree.getroot().find("DOCUMENT")
    for el in list(doc.findall("FRAMEOBJECT")):
        doc.remove(el)
```
Critical for the FONTSIZE story: the **42 dormant `FONTSIZE="11.7"` ITEXTs in the corrected `originals/Grüne Zeitung Vorlage Scribus.sla` are inside `<FRAMEOBJECT>` elements** (orphan/pasteboard text frames), not PAGEOBJECTs. `sla_diff.py` drops FRAMEOBJECTs before comparison, so the round-trip diff is unaffected. The renderer also doesn't display FRAMEOBJECTs (they sit on the pasteboard, not pages). This explains why the 0-pixel-diff result holds despite the 42 lingering `FONTSIZE="11.7"` strings — **CONTEXT.md was imprecise** (said "STYLE definitions"); they're actually FRAMEOBJECTs.

#### `tools/check_ci.py`
Inspects only `<COLOR>` and `<STYLE>` elements (lines 116-191). **Never inspects `<ITEXT>` or `FONTSIZE`.** D1's FONTSIZE fix has zero impact on `check_ci.py`'s behavior. No drift expected from this issue.

#### `templates/_smoke/*/build.py`
- `templates/_smoke/postcard-a6/build.py`: uses `Color.DUNKELGRUEN` and `blocks.*` from `sla_lib.builder`. No explicit font references; relies on DSL builder defaults.
- `templates/_smoke/zeitung-mini/build.py`: same pattern, plus `Masthead`, `ContentTeasers`, etc. blocks.

`bin/validate` skips templates without `original_sla:` in their meta.yml — smoke templates have no meta.yml so they're not validated. **No impact from this issue.**

### `<interfaces>` block

```python
# From tools/visual_diff.py
@dataclass
class TemplateTolerance:
    max_pixel_mismatch_pct: float = 1.0
    fuzz_pct: float = 25.0
    per_page: dict = field(default_factory=dict)
    per_region: list = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[Path]) -> "TemplateTolerance"

    def for_page(self, page_index: int) -> tuple[float, float]

@dataclass
class PageResult:
    page_index: int; mismatch_pixels: int; total_pixels: int
    mismatch_pct: float; threshold_pct: float; fuzz_pct: float
    composite: str; delta_png: str; pass_: bool
    region_results: list[dict]

def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None
def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path]
def compare_pages(baseline: Path, dsl: Path, diff_path: Path,
                   fuzz_pct: float) -> tuple[int, int]   # (mismatch_pixels, total_pixels)
def visual_diff(template_sla: Path, baseline_pdf: Path,
                 tolerance: TemplateTolerance, dpi: int,
                 out_dir: Path) -> tuple[bool, list[PageResult]]

# CLI: python3 tools/visual_diff.py <template.sla> --baseline <pdf> --tolerance <yml> --dpi 150 --out <dir>

# From tools/_export_pdf.py — invoked via:
#   xvfb-run -a --server-args="-screen 0 1024x768x24" \
#     scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>
# (third positional arg silently ignored)

# From tools/sla_diff.py
# Pipeline (10 steps):
#   1. parse_sla(path) -> ElementTree
#   2. strip_volatile_doc_attrs(tree)
#   3. renumber_item_ids(tree, start=int)
#   4. drop_frameobjects(tree)              # critical for FONTSIZE story
#   5..10. (page-local coords, float round, attr sort, …)
# CLI: python3 tools/sla_diff.py --left <sla> --right <sla> [--strict] [--json out.json]
# Exit 0 = clean (no critical/warning); 1 with --strict on warning; always 1 on critical

# From tools/sla_to_dsl.py — one-shot bootstrap
# CLI: python3 tools/sla_to_dsl.py <input.sla> <output.build.py> \
#   --template-id <id> --assets-dir <dir>
# Does NOT run in CI. Hand-edit the emitted build.py thereafter.

# From bin/validate (bash)
# Loops every templates/<id>/ dir with meta.yml AND `original_sla:` key.
# For each: sla_diff --strict (always), then visual_diff (if baseline.pdf+diff.yml exist).
# DPI=150 default, --ci flag flips to DPI=96 (matches CI's 96-dpi visual_diff).

# From .github/workflows/pages.yml (validate-reproductions step)
# Same logic as bin/validate but inlined; iterates exactly:
#   templates/postkarte-a6-kampagne, templates/plakat-a1-hochformat, templates/zeitung-a4-grun

# From templates/<id>/meta.yml schema
# id: <slug>
# original_sla: <relative path>           # consumed by bin/validate + workflow
# ci_overrides:
#   non_ci_styles: [<list of style names allowed in this template's SLA but not in shared/ci.yml>]
#   non_ci_colors: [<list of color names allowed in this template's SLA but not in shared/ci.yml>]
# (other keys: title, format, pages, masters, slots, preflight, etc.)

# From templates/<id>/diff.yml schema (consumed by visual_diff)
# visual_diff:
#   max_pixel_mismatch_pct: float    # default 1.0
#   fuzz_pct: float                  # default 25.0 (project cap is 5)
#   per_page: [{page: int, max_pixel_mismatch_pct?, fuzz_pct?}]
#   per_region: [{page, bbox_mm: {x,y,w,h}, max_pixel_mismatch_pct?, fuzz_pct?}]
```

---

## Dockerfile font-install mechanics

### Inputs

- Source files at build time: `/root/workspace/fonts/Gotham Narrow/<weight>/<weight>.otf` (16 files) and `/root/workspace/fonts/Vollkorn/static/Vollkorn-BlackItalic.ttf` (1 file). Build context = the worktree (or whatever `docker build` is pointed at).
- Fontconfig alias content (literal, ~16 lines XML; see live copy at `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf`):
```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test name="family"><string>Vollkorn Black Italic</string></test>
    <edit name="family" mode="assign"><string>Vollkorn</string></edit>
    <edit name="style"  mode="assign"><string>Black Italic</string></edit>
    <edit name="weight" mode="assign"><const>black</const></edit>
    <edit name="slant"  mode="assign"><const>italic</const></edit>
  </match>
</fontconfig>
```

### Layer ordering in `Dockerfile.claude`

Insert AFTER the `apt-get install` block (line 50, before the ImageMagick policy patch on line 54). The font layer must run before the sanity probe at lines 103-105 so that `scribus --version` exercises the populated font cache once. Suggested skeleton (let the planner select between BuildKit bind-mount or conditional COPY):

#### Option A — conditional COPY pattern (no BuildKit required)
```dockerfile
# Brand fonts (gitignored, not part of public repo).
# When the build context contains fonts/, install them into fontconfig.
# When it doesn't (CI / public clones), the COPY of an empty wildcard succeeds
# and the script no-ops. Sanity probe at the end fails-loud if expected fonts
# are missing despite the layer being expected to provide them.
COPY fonts* /tmp/fonts-staging/
RUN set -e; \
    if [ -d /tmp/fonts-staging/Gotham\ Narrow ] || [ -d /tmp/fonts-staging/Vollkorn ]; then \
        mkdir -p /usr/local/share/fonts/gruene; \
        find /tmp/fonts-staging -type f \( -iname '*.otf' -o -iname '*.ttf' \) \
            -exec cp {} /usr/local/share/fonts/gruene/ \;; \
        fc-cache -f; \
        N=$(fc-list | grep -ciE 'gotham narrow|vollkorn'); \
        if [ "$N" -lt 5 ]; then \
            echo "FONT INSTALL FAILED: only $N font faces registered" >&2; \
            exit 1; \
        fi; \
        echo "Brand fonts installed: $N faces"; \
    else \
        echo "No fonts/ in build context — skipping brand-font install (DejaVu fallback)"; \
    fi; \
    rm -rf /tmp/fonts-staging
```
(`COPY fonts*` succeeds whether `fonts/` exists or not because the `*` glob is permissive — but verify with the build before relying on it; the Docker semantics here is environment-dependent. An alternative is a `.dockerignore`-aware unconditional `COPY fonts/ /tmp/fonts-staging/` and let it fail gracefully — but that errors on missing source. Plan should test whichever pattern is chosen.)

#### Option B — BuildKit bind-mount (preferred if base image supports it)
```dockerfile
# syntax=docker/dockerfile:1.6
RUN --mount=type=bind,source=fonts,target=/tmp/fonts-staging,rw=false \
    set -e; \
    if [ -d /tmp/fonts-staging ] && [ "$(ls -A /tmp/fonts-staging 2>/dev/null)" ]; then \
        mkdir -p /usr/local/share/fonts/gruene; \
        find /tmp/fonts-staging -type f \( -iname '*.otf' -o -iname '*.ttf' \) \
            -exec install -m 644 {} /usr/local/share/fonts/gruene/ \;; \
        fc-cache -f; \
        fc-list | grep -ciE 'gotham narrow|vollkorn' | (read N; [ "$N" -ge 5 ] || { echo "FONT INSTALL FAILED: $N faces"; exit 1; }); \
    else \
        echo "fonts/ absent — DejaVu-only image"; \
    fi
```
Bind-mount is cleaner because `fonts/` never enters the image layer. But requires `# syntax=docker/dockerfile:1.6` directive at top and BuildKit-enabled `docker build` (default in modern Docker, off in some CI).

**Recommendation:** Option A (conditional COPY) for portability. The minor cost (a transient image layer holding the staging copy) is acceptable; we delete it before the layer concludes. The base image's `docker build` invocations need not change.

### Fontconfig alias install

Same RUN layer (or a fresh one immediately after):
```dockerfile
# Family-name alias: Scribus references Vollkorn Black Italic as a family;
# the static font registers as family=Vollkorn + style="Black Italic".
COPY shared/fonts/50-vollkorn-family-alias.conf /etc/fonts/conf.d/50-vollkorn-family-alias.conf
RUN fc-cache -f && \
    fc-match "Vollkorn Black Italic" | grep -q "Vollkorn-BlackItalic" || \
        { echo "Vollkorn alias not resolving"; exit 1; }
```
This requires committing the `.conf` file to the repo at `shared/fonts/50-vollkorn-family-alias.conf` (mirror of the live `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf`). System path `/etc/fonts/conf.d/` is appropriate for container-scoped install (vs `~/.config/fontconfig/conf.d/` which is per-user).

### Scribus font cache caveat

`~/.config/scribus/checkfonts150.xml` is a per-user cache that Scribus regenerates on first run after fonts change. The Dockerfile should NOT pre-populate it — the runtime user's HOME (which may differ from build-time root) will own the cache and Scribus will regenerate on first invocation. **This is fine, but document it** in `docs/render-fidelity.md`: "When fonts/ changes, the next render in a fresh container will incur a one-time ~3 sec font-cache rebuild; subsequent renders are fast."

### Image-layer ordering checks

Current layers:
1. apt install Scribus + xvfb + poppler-utils + ghostscript + imagemagick (line 33-50)
2. ImageMagick policy patch (53-57)
3. Optional preflight tools, gated by INSTALL_PREFLIGHT (60-99)
4. Sanity probe: `xvfb-run scribus --version` (line 103-105)
5. WORKDIR + CMD

**Insert the font-install layer between (1) and (2).** Reason: fc-cache requires fontconfig to be installed (which `apt-get install scribus` brings in transitively, but better to be explicit). After install, the sanity probe at (4) implicitly validates that the font cache builds (since Scribus initializes its own font cache from fontconfig).

Worth adding to the sanity-probe RUN: a `fc-list | grep -ciE 'gotham|vollkorn'` print so build logs show font count without explicit failure check (the install RUN already fails-loud if missing-when-expected).

---

## bin/validate change required

**No code change to `bin/validate`.** The script reads `original_sla` from each meta.yml and resolves it relative to `templates/<id>/`. If meta.yml is updated, `bin/validate` follows.

**Optional addition (CONTEXT.md risk-mitigation):** A FONTSIZE-typo regression check. CONTEXT.md proposed `grep 'FONTSIZE="[0-9]*\.[0-9]\+"' originals/*.sla` — but this naively flags 42 false positives in the corrected Zeitung SLA (the dormant FRAMEOBJECT pasteboard text). A precise check needs to limit to PAGEOBJECT subtree:

```python
# tools/check_no_fractional_fontsize.py (new, ~20 lines)
# Walk PAGEOBJECT subtrees only; ignore FRAMEOBJECT / MASTEROBJECT / STYLE elements.
# Fail with non-zero exit if any ITEXT.FONTSIZE has a fractional value.
import sys
from lxml import etree
from pathlib import Path

def main(paths):
    bad = []
    for p in paths:
        tree = etree.parse(str(p))
        doc = tree.getroot().find("DOCUMENT")
        for po in doc.findall("PAGEOBJECT"):
            for it in po.iter("ITEXT"):
                fs = it.get("FONTSIZE", "")
                if "." in fs:
                    bad.append(f"{p}: FONTSIZE={fs!r} on PAGEOBJECT[OwnPage={po.get('OwnPage')}]")
    if bad:
        print("Fractional FONTSIZE found in rendered text:", file=sys.stderr)
        for b in bad: print(f"  {b}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main([Path(p) for p in sys.argv[1:]]))
```
Hook into `bin/validate` (call before the per-template loop) and into the workflow as a separate step. Exits non-zero on regression.

This is "Claude's Discretion" per CONTEXT.md — not strictly required to ship the issue, but cheap insurance.

---

## Test impact assessment

### Tests that depend on stale-path SLA filenames (will fail until paths updated)

- `tools/sla_lib/tests/test_check_ci.py` — `test_postkarte_has_extra_green`, `test_zeitung_has_extra_green`, `test_plakat_has_no_extra_green`
- `tools/sla_lib/tests/test_reader.py` — `ORIGINALS` list; `IteratorTests.EXPECTED` dict (keyed by basename `"postkarte-vorlage-original.sla"` etc.)
- `tools/sla_lib/tests/test_sla_diff.py` — `ORIGINALS` list at module level
- `tools/sla_lib/tests/test_sla_to_dsl.py` — `PostkarteRoundTrip.ORIGINAL`, `PostkarteConverterFreshRun.ORIGINAL`, `PlakatRoundTrip.ORIGINAL`, `ZeitungRoundTrip.ORIGINAL`, plus a `read_bytes()` reference at line 409

**Update strategy:** keep filenames the same (ASCII names) when copying `originals/<umlaut>.sla` → `originals/<ascii>.sla`. This minimizes test churn — only the path prefix changes from `ROOT / "<filename>"` to `ROOT / "originals" / "<filename>"`.

### Tests that depend on baseline.pdf content

None. No tests parse, hash, or pixel-diff the committed `baseline.pdf` files outside of `bin/validate` (a runtime script, not a unit test) and the GitHub workflow's `validate-reproductions` step. Regenerating baselines does NOT invalidate any unit-test fixtures.

### Tests that exercise the converter on an SLA

`test_sla_to_dsl.PostkarteConverterFreshRun.test_fresh_convert_is_clean` runs the full converter against `postkarte-vorlage-original.sla` and asserts the result diffs cleanly against the original. **Will continue passing unchanged** once paths are updated, because the corrected Postkarte SLA is byte-identical to the stale one (Postkarte never had the FONTSIZE typo).

`test_sla_to_dsl.ZeitungRoundTrip.test_diff_against_original_clean` runs `_run_build()` on the committed `templates/zeitung-a4-grun/build.py` (which still embeds 97 `fontsize=11.7`) and diffs against the corrected original (FONTSIZE=12). **Will FAIL** with 14 critical + 97 warning issues until `templates/zeitung-a4-grun/build.py` is regenerated from the corrected SLA. Plan must include this regeneration BEFORE the test suite runs in CI.

### Tests that count FRAMEOBJECTs / iter counts

`test_reader.py::IteratorTests.EXPECTED` defines per-original page/master/layer/color/style/charstyle counts. **None of these are affected by D1's FONTSIZE fix** — the corrected Zeitung still has 14 pages, 2 masters, 1 layer, 8 colors, 23 styles, 1 charstyle (verified by lxml probe). Updates: only the dict keys (basenames) change if filenames change.

### The smoke-template tests

`templates/_smoke/postcard-a6/template.sla` and `templates/_smoke/zeitung-mini/template.sla` are smoke artifacts. No unit tests reference them. `bin/validate` skips them (no meta.yml → no `original_sla:` → skip).

---

## CI workflow impact

### The font-asymmetry problem (severe, planner must address)

Current state and post-issue state:

| | Local dev (container with fonts) | CI (no fonts) |
|---|---|---|
| **Before issue** | DSL render: DejaVu. baseline.pdf: DejaVu. **Diff = clean.** | DSL: DejaVu. baseline: DejaVu. **Diff = clean.** |
| **After issue** | DSL render: real fonts. baseline.pdf: real fonts (regenerated). **Diff = ~3 px.** PASS. | DSL: DejaVu. baseline: real fonts (committed). **Diff = huge mismatch.** **FAIL.** |

The CI's `validate-reproductions` step (`.github/workflows/pages.yml` lines 93-122) runs the same `tools/visual_diff.py` invocation as `bin/validate`. With the new font-bundled baselines, CI will fail the visual_diff for Zeitung especially (multi-column body text amplifies sub-pixel differences to large fractions).

**Options** (planner picks):

1. **Skip visual_diff in CI for now.** Edit `.github/workflows/pages.yml` to omit the visual_diff invocation in the `validate-reproductions` step, leaving sla_diff (structural ground truth) as the gate. Add a comment explaining D7 and a TODO for the follow-up issue. *Recommended.*

2. **Use `continue-on-error: true` on the visual_diff substep.** Lets CI run for visibility but doesn't gate the deploy. Less clean (failures pollute logs).

3. **Render baseline-on-the-fly in CI from the original SLA.** Both sides use the same font-less env; comparison is symmetric. Means CI re-renders the baseline each run. Adds ~2 minutes runtime. The diff is then DSL-vs-original-reproduction, which is what PR #5's standard already does — but loses the "committed baseline = production reference" property locally.

4. **Loosen Zeitung's diff.yml threshold for CI mode (`--dpi 96`).** Old PR #4 state. CONTEXT.md describes that approach as superseded; reverting is regressive.

Option 1 is the cleanest match for D7. Plan should choose it.

### Other CI concerns

- The `Run unit tests` step (line 91) will fail on the test-fixture path changes until updated.
- The `Validate reproductions` step (line 97) iterates explicitly over the three template directories; no path lookups inside, so this works as long as `templates/<id>/meta.yml` updates correctly.
- The `Run brand validator` step (line 132-135) globs `templates/*/template.sla templates/*/*.sla` — does NOT touch the workspace-root SLAs that are being deleted. **No impact.**
- `actions/cache@v4` for the Scribus AppImage (line 35-40) is keyed `scribus-1.6.5-appimage-v1` — unaffected.
- The build context for `Dockerfile.claude` is the worktree root in CI; `fonts/` is gitignored so won't be present. The conditional-COPY layer must no-op gracefully (validated by Option A above).

---

## Risks & pitfalls

### 1. Ubuntu CI Unicode normalization (NFC/NFD) re-introduction
Commit `cdfb92b` renamed the workspace-root SLAs from umlaut to ASCII names because Ubuntu CI runners store filenames in NFD form, breaking Python `Path()` lookups against NFC string literals. CONTEXT.md proposes adopting `originals/Grüne Zeitung Vorlage Scribus.sla` etc. — **this would re-introduce the bug**.

**Mitigation:** Keep ASCII filenames when copying into the worktree. Final paths:
- `originals/gruene-zeitung-vorlage-original.sla` (was `originals/Grüne Zeitung Vorlage Scribus.sla`)
- `originals/plakat-a1-hochformat-original.sla` (was `originals/Plakat A1 Hochformat_Vorlage.sla`)
- `originals/postkarte-vorlage-original.sla` (was `originals/Postkarte Vorlage.sla`)
- And matching for the user's reference PDFs: `originals/*-original.pdf`.

This also keeps test-fixture diffs minimal (only the parent dir prefix changes).

### 2. `templates/zeitung-a4-grun/build.py` regression
The committed build.py was generated when the SLA had FONTSIZE=11.7 typos. It hardcodes 97 `fontsize=11.7` Run(...) parameters across line 1146 onward. After adopting the corrected SLA as canonical, the build.py must be regenerated — otherwise sla_diff fails with 14 critical + 97 warning issues, and visual_diff fails with the body text at 11.7pt vs baseline's 12pt.

**Mitigation:** As part of this issue, run `python3 tools/sla_to_dsl.py originals/gruene-zeitung-vorlage-original.sla templates/zeitung-a4-grun/build.py --template-id zeitung-a4-grun --assets-dir templates/zeitung-a4-grun/assets/`, then `python3 templates/zeitung-a4-grun/build.py` to regenerate `template.sla`. Verify via `python3 tools/sla_diff.py --left originals/gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict` exits 0.

### 3. Vollkorn variable-vs-static substitution
If a future contributor's `fonts/` directory contains the Google Fonts variable Vollkorn instead of the user's static `Vollkorn-BlackItalic.ttf`, glyph metrics differ subtly and renders drift by ~7,000 px on 3 Zeitung pages (per CONTEXT.md drift cause 3). The fontconfig alias maps `Vollkorn Black Italic → Vollkorn / Black Italic` — fontconfig will pick whichever file provides that style. If both variable and static are installed, behavior depends on file ordering, which is non-deterministic.

**Mitigation:** `docs/render-fidelity.md` must explicitly state: install ONLY the static `Vollkorn-BlackItalic.ttf` (don't drop the variable file in alongside). Optionally, a build-time check that asserts `fc-match "Vollkorn:weight=black:slant=italic"` resolves to `Vollkorn-BlackItalic.ttf` (file basename) and not `Vollkorn-Italic[wght].ttf`.

### 4. fontconfig priority numbering
The alias filename `50-vollkorn-family-alias.conf` uses the standard "50-" prefix. Some distros ship higher-priority confs (60-, 70-) that may override it. If Scribus's lookup order doesn't prefer ours, the alias won't apply. Check: live `fc-match "Vollkorn Black Italic"` resolves to `Vollkorn-BlackItalic.ttf` (verified during discuss; the live `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf` is working).

**Mitigation:** Test the full alias chain with `fc-match -v "Vollkorn Black Italic"` in the Dockerfile sanity probe.

### 5. xvfb display collisions on parallel renders
`xvfb-run -a` auto-picks a free display number, but with N parallel invocations there's a small race window. This issue's executor likely runs the three baseline-regenerations sequentially via a script — no problem. If parallelized, occasional flakes are possible.

**Mitigation:** Document that baseline regeneration is sequential. If parallelization is desired, use explicit `-n NUM` per process.

### 6. Build-context `fonts/` absence in CI
CI's `docker build` (or AppImage-based render path that bypasses Docker entirely) won't have `fonts/` in context. The Option A conditional-COPY pattern silently succeeds with empty staging dir. The image then ships with DejaVu only — visual_diff against font-bundled baselines fails (covered in §"CI Workflow Impact").

**Mitigation:** D7 says CI fonts are out of scope. Plan must skip visual_diff in CI. Alternatively, the CI workflow doesn't `docker build` the dev container at all — it apt-installs Scribus directly (`.github/workflows/pages.yml` line 42-65). So Dockerfile.claude is irrelevant for CI; only local dev container uses it. **Confirmed: Dockerfile.claude is dev-only.**

### 7. PDF non-determinism
Scribus emits PDFs with non-deterministic CreationDate metadata and (potentially) font subset prefixes. Empirically, two consecutive renders of the same SLA with the same fonts produce raster-identical output (verified during discuss). visual_diff is raster-based, so PDF byte-level non-determinism doesn't affect the comparison. **Documented in CONTEXT.md, no mitigation needed.**

### 8. CONTEXT.md imprecision: FRAMEOBJECT vs STYLE
CONTEXT.md says the 42 dormant `FONTSIZE="11.7"` are "inside STYLE definitions". They're actually inside `<FRAMEOBJECT>` elements (orphan/pasteboard text frames). `tools/sla_diff.py` drops FRAMEOBJECTs in step 4 of normalization, so structural diff is unaffected; the renderer doesn't show FRAMEOBJECTs, so visual diff is unaffected. **No functional impact**, just a doc-precision note for `docs/render-fidelity.md`.

### 9. Site frontmatter divergence
`site/src/content/templates/<id>.md` files have a YAML frontmatter copy of `original_sla:` from each meta.yml. They're auto-regenerated by `tools/gallery_build.py`. The committed copies will be stale (point at workspace-root) until the next gallery_build run. If `gallery_build.py` runs only in CI (which it does) and CI fails before reaching gallery_build because of the visual_diff catastrophe (Risk in §CI), the committed frontmatter never updates.

**Mitigation:** Run `python3 tools/gallery_build.py` locally as part of this issue's commit and commit the regenerated `site/src/content/templates/*.md`. Or explicitly hand-edit the three files (one-line change each).

---

## docs/render-fidelity.md structure recommendation

Skeleton aligned with CONTEXT.md D6 plus what cross-references should reach into existing code:

```
# Render-fidelity workflow

## Why fonts must be installed (D7 lesson)
- DejaVu fallback drifts ~55,000 px/page. Brand fonts collapse to 0 px diff with the user's Scribus 1.6.4 export.
- The font cache `~/.config/scribus/checkfonts150.xml` regenerates on first scribus run; one-time cost.

## What's installed and where
- `/usr/local/share/fonts/gruene/`: Gotham Narrow (16 .otf) + Vollkorn-BlackItalic.ttf
- `/etc/fonts/conf.d/50-vollkorn-family-alias.conf`: maps "Vollkorn Black Italic" family → Vollkorn/Black Italic
- Source files: `/root/workspace/fonts/` (gitignored; user-controlled)
- Verification: `fc-list | grep -ciE 'gotham narrow|vollkorn'` → 17

## Why static, not variable, Vollkorn
- Static `Vollkorn-BlackItalic.ttf` glyph metrics differ from Google Fonts variable `Vollkorn-Italic[wght].ttf` instantiated at weight=black.
- 7,000 px/page drift with the wrong file. Don't install both.

## The "fix typos at the source, not the renderer" principle (D1)
- The Zeitung had `FONTSIZE="11.7"` on body text — author error (mouse-wheel nudge in Scribus).
- User's Scribus 1.6.4 silently rounds 11.7 → 11.0 in PDF output; our 1.6.3 honored 11.7 literally. The renderer-version difference was a symptom, not the cause.
- Fix: user corrected the SLA in their Scribus (FONTSIZE=12). Don't try to compensate via render-time adjustments.
- 42 lingering FONTSIZE=11.7 strings exist in `<FRAMEOBJECT>` pasteboard frames — irrelevant (not rendered). `tools/sla_diff.py` drops FRAMEOBJECTs in normalization (line 248-253).

## Adding a new font to fonts/
1. Drop the file at `/root/workspace/fonts/<family>/...`
2. Rebuild dev container (`docker build -f Dockerfile.claude .`)
3. `fc-list | grep "<family>"` to verify
4. If Scribus references the font by a non-standard family name, add a fontconfig alias at `shared/fonts/<NN>-<family>-alias.conf` (mirror /etc/fonts/conf.d/ convention).

## Rebaselining a template's baseline.pdf (gated procedure)
[Cross-reference: docs/diff-tolerance.md §Rebaselining workflow]
- WHEN: original SLA changes intentionally, Scribus version bumps, or fonts change.
- HOW: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py originals/<id>-original.sla templates/<id>/baseline.pdf`
- VERIFY: visually compare the new baseline.pdf against `originals/<id>-original.pdf` (user's reference export); pixel-diff via `pdftoppm + compare -fuzz 0%` should be 0 px.

## Verifying a new SLA render matches your desktop Scribus export
1. Drop your reference PDF at `/tmp/desktop.pdf`
2. `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py your.sla /tmp/headless.pdf`
3. `pdftoppm -r 96 -png /tmp/desktop.pdf desktop && pdftoppm -r 96 -png /tmp/headless.pdf headless`
4. `for f in desktop-*.png; do compare -metric AE -fuzz 0% "$f" "${f/desktop/headless}" diff-$f 2>&1; done`
5. Expect 0 per page (or document the drift).

## Out of scope (tracked elsewhere)
- ECI ICC profile install — cosmetic, substitutes are symmetric across desktop/container
- CI font provisioning — separate follow-up issue (after this one ships)
```

---

## Project Constraints (from CLAUDE.md)

No workspace-level `CLAUDE.md` exists at `/root/workspace/.worktrees/3-...-fo/CLAUDE.md`. (User-level `~/.config/claude/projects/-root-workspace/memory/MEMORY.md` exists but holds personal/cross-project notes, not project-specific directives.)

The user-memory contains relevant feedback principles for this work:
- `feedback_no_claude_attribution.md` — Never include "claude" in commits/code/files (commit messages must avoid the tool name)
- `feedback_thorough_reviews.md` — Reviews must be deeply thorough (line-by-line, exhaustive grep, trace runtime paths)
- `feedback_working_over_theoretical.md` — Prefer "working" over "theoretically better"

These translate to: prescriptive plan, exhaustive trace (this RESEARCH.md), no Claude branding in commit messages, and prefer the simplest pattern that works (Option A conditional-COPY over Option B BuildKit bind-mount unless there's a concrete reason to switch).

---

## Sources

### HIGH confidence
- Direct codebase analysis of every file in the worktree at `/root/workspace/.worktrees/3-...-fo/` (verified file existence, line numbers cited inline)
- Live `git grep` traces (full enumeration of SLA-path references)
- Live lxml inspection of `originals/Grüne Zeitung Vorlage Scribus.sla` confirming 42 FONTSIZE=11.7 ITEXTs are inside FRAMEOBJECTs (not PAGEOBJECTs)
- Live `tools/sla_diff.py` execution proving:
  - Postkarte and Plakat: corrected vs stale = clean
  - Zeitung: corrected vs stale = 14 critical + 97 warning (the FONTSIZE typo)
- Live `fc-list | grep -ciE 'gotham narrow|vollkorn'` = 17 confirms current font state
- CONTEXT.md (D1–D7) and ISSUE.md fully read
- `git show cdfb92b` confirming the NFC/NFD ASCII-rename rationale

### MEDIUM confidence
- Dockerfile font-install layer ordering recommendation (Option A vs B) — based on standard Dockerfile patterns; not yet exercised in this codebase. Plan should validate by building.
- Scribus `~/.config/scribus/checkfonts150.xml` per-user-cache regeneration claim — based on observation that the file exists locally with timestamps post-fontfile install; documented in scribus source but not double-checked.
- xvfb-run `-a` parallelism safety — documented in xvfb-run --help; not stress-tested.

### LOW confidence (none flagged)
No findings rest solely on training-era knowledge.

---

## Open questions for the planner

1. **Workspace-root SLA cleanup: `git rm` in this PR, or just stop referencing them?** Recommendation: `git rm` in the same PR — they're stale (Zeitung) or duplicates (Plakat, Postkarte), and leaving them creates two sources of truth. Aligns with CONTEXT.md "What done looks like" #5.

2. **Older `samples-output/originals/{plakat-a1,postkarte,zeitung}-original.pdf` cleanup?** These were committed in the initial repo (May 4) and predate the user's authoritative `originals/<id>-original.pdf` exports. They differ in content and size. Options:
   - Leave them (CONTEXT.md doesn't mention)
   - Delete them (they're now superseded; the planner could include this as cleanup)
   - Move them to `originals/legacy/` for archival
   Recommendation: delete in this PR with a clear commit message; the new `originals/*.pdf` are canonical.

3. **Fontconfig alias commit location?** CONTEXT.md doesn't specify. Options:
   - `shared/fonts/50-vollkorn-family-alias.conf` (consistent with `shared/fonts/README.md` location)
   - `Dockerfile.claude` companion at root
   Recommendation: `shared/fonts/50-vollkorn-family-alias.conf`. The Dockerfile COPYs from there.

4. **CI visual_diff de-scope: edit workflow file or wrap in a continue-on-error?** Recommendation: outright remove the visual_diff invocation from `.github/workflows/pages.yml`'s `validate-reproductions` step in this PR; add a one-line comment with TODO and a reference to the CI-fonts follow-up issue. The follow-up issue restores it.

5. **Should we update `tools/sla_to_dsl.py` line 24 docstring example?** Trivial cosmetic update; recommend yes for consistency. Same for `tools/check_ci.py` line 16 (mentions umlaut filenames).

6. **Should `templates/zeitung-a4-grun/build.py` regeneration go through the converter or be hand-edited?** The converter is documented as the canonical source-of-truth bootstrap; hand-edits work but risk subtle drift if someone later re-runs the converter and overwrites. Recommendation: regenerate via `tools/sla_to_dsl.py` (one shell command), commit the result.

7. **Add a FONTSIZE-typo regression check now or defer?** CONTEXT.md proposes it as a risk-mitigation; my refined version (PAGEOBJECT-scoped lxml walker) is ~20 lines and cheap. Recommendation: include in this PR as `tools/check_no_fractional_fontsize.py` plus a `bin/validate` invocation. Counter-argument: out-of-scope per strict reading of D1-D7. Planner picks.

8. **Is there a precedent for committing the user's reference PDFs alongside the SLAs in `originals/*.pdf`?** They're 1.3 MB / 0.6 MB / 0.5 MB binaries. `.gitattributes` already marks `*.pdf binary`. They're not LFS-tracked. CONTEXT.md D4 says they're committed; recommend confirming the user is OK with these binaries entering main. (No response needed if user confirmed during discuss.)

---

## Metadata

**Confidence breakdown:**
| Area | Level | Reason |
|---|---|---|
| Codebase trace | HIGH | Every file enumerated via git grep; line numbers verified |
| Test impact | HIGH | All test files read; failure modes confirmed via direct sla_diff |
| Dockerfile mechanics | MEDIUM | Standard patterns; no in-repo precedent to copy |
| CI workflow impact | HIGH | Workflow file fully read; failure mode confirmed |
| Risks | HIGH | Each backed by concrete code/git/lxml evidence |

**Research date:** 2026-05-06
**Sub-agents used:** None (single-pass research given tight scope and rich CONTEXT.md). Standalone work integrated into this single document.
**Research files:** `.issues/3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo/research/` (empty — no parallel agents spawned for this scope)
