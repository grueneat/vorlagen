# Plan: Visual-diff bbox extractor with slot attribution

## Objective

Deliver `tools/diff_bbox_extract.py`: a post-processor that reads any
`visual_diff.py` output directory (the `diff-page-NN.png` red-on-white RGBA
delta images), runs ImageMagick connected-components labelling per page,
converts pixel bboxes to mm via the DPI stored in `visual_diff.json`,
attributes each bbox to the nearest template slot (loaded via the same
`load_build_module` + `frame_bbox_mm` path `audit_alignment.py` uses),
and writes a deterministic `diff_bboxes.json` next to the existing delta
PNGs. Optional `--overlay-out` renders red-rectangle outlines on the
`dsl-page-NN.png`. `tools/visual_diff.py` grows an opt-in
`--extract-bboxes` flag that shells out to the extractor after its page
loop and merges the per-page `bboxes` list back into `visual_diff.json`.

**Done when:** running
`python3 tools/diff_bbox_extract.py build/validation/postkarte-a6-kampagne/`
twice produces byte-identical `diff_bboxes.json` files; the JSON validates
against the schema in `## Interfaces`; the merged
`visual_diff.json` produced by `visual_diff.py --extract-bboxes` contains
the new `bboxes` field; all `python3 -m unittest tools.sla_lib.tests.test_diff_bbox_*`
tests pass; every ISSUE.md acceptance-criterion checkbox is ticked.

No CONTEXT.md exists — decisions below come from RESEARCH.md and the
six locked items prefixed by the user.

## Locked Decisions

1. **Connected-components: ImageMagick** (`-connected-components 8 -define connected-components:verbose=true`). Zero new dependencies. Parse text output via regex. Drop id=0 background object (largest, near-white mean-color).
2. **Threshold for non-white pixels in red-on-white RGBA delta**: red channel ≥ 200, or `convert -threshold 90% -negate` IM-side. Validate empirically against `build/validation/postkarte-a6-kampagne/diff-page-01.png` during task 2.
3. **`visual_diff.py --extract-bboxes` wiring**: optional flag, off by default. When set, `visual_diff.py` shells out to the extractor after its existing page loop; the merged JSON ends up in `visual_diff.json`. The extractor stays independently runnable against any existing out/ dir.
4. **Slot attribution metric**: `coverage_of_diff_inside_slot` (area_intersect / area_diff_bbox), not pure IoU. Tie-break among slots with coverage ≥ 0.5 by smaller area (more specific attribution). Emit top-3 `attribution_candidates` so reviewers see alternatives.
5. **Determinism**: (a) sort bboxes by `(page, y_mm, x_mm, w_mm, h_mm)`; (b) round mm to 0.1; (c) `json.dumps(sort_keys=True, indent=2)`.
6. **Test framework**: `unittest.TestCase` (repo idiom), not pytest. Run via `python3 -m unittest discover tools/sla_lib/tests` or per-file. Use `tempfile.mkdtemp()` + `try/finally: shutil.rmtree`. Import bootstrap: `sys.path.insert(0, ROOT/"tools")`.

## Out of Scope

- Auto-generating `diff.yml` `per_region:` blocks from the extracted bboxes (separate follow-up after attribution proves accurate).
- Vision-model invocation on the cropped bboxes — that lives in a future `visual_review.py`.
- Replacing `tools/visual_diff.py`'s composite / montage outputs — those stay.
- Rewriting the diff pixel arithmetic — we operate on existing `diff-page-NN.png` only.
- Adding cv2 / numpy as runtime dependencies (ImageMagick-only path per decision 1).

<skills>
<!-- No repo-local python or git-committer skill exists; `.claude/skills/experiments/`
     is design-experimentation-specific and not relevant here. The executor follows
     the in-repo idioms inlined in <interfaces> and the unittest convention from
     decision 6. No skills to inject. -->
</skills>

## Interfaces

```
# tools/sla_lib/builder/bbox.py  (existing — use; do not modify)
def rotated_bbox(x: float, y: float, w: float, h: float, deg: float
                ) -> tuple[float, float, float, float]:
    """Axis-aligned bbox after CCW rotation around top-left.
    Returns (min_x, min_y, max_x, max_y) — same units as inputs."""

def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """Page-local mm bbox of `item` on `page`, honouring anchor + rotation.
    Returns (min_x, min_y, max_x, max_y) — NOT (x, y, w, h). Callers convert.
    Returns None for primitives without spatial extent.
    Limitation: ignores xpos_pt/width_pt verbatim overrides (bbox.py:13-16)."""
```

```
# tools/audit_alignment.py:52 + :240-254  (existing — import + reuse; do not duplicate)
from sla_lib.builder.template_loader import load_build_module

mod = load_build_module(slug, REPO_ROOT)      # may raise; wrap in try/except
doc = mod.build_preview() if hasattr(mod, "build_preview") else mod.build_doc()
for idx, page in enumerate(doc.pages):
    if page.is_master:
        continue
    for item in page.items:
        if not getattr(item, "anname", None):
            continue
        bbox4 = frame_bbox_mm(item, page)     # (min_x, min_y, max_x, max_y) mm or None
        if bbox4 is None:
            continue
        # convert to (x, y, w, h) mm before storing
```

```
# tools/visual_diff.py — existing JSON schema (visual_diff.py:284-306) — preserve keys verbatim
{
  "template_sla": "...", "baseline_pdf": "...", "dpi": 96,
  "default_threshold_pct": 1.0, "default_fuzz_pct": 25.0, "pass": true,
  "pages": [
    {
      "page": 0,                            # 0-indexed
      "mismatch_pixels": 1234,
      "total_pixels": 1_500_000,
      "mismatch_pct": 0.0823,
      "threshold_pct": 1.0, "fuzz_pct": 25.0,
      "composite": "composite-page-01.png",
      "delta_png":  "diff-page-01.png",      # ALWAYS 2-digit zero-pad (visual_diff.py:231)
      "pass": true,
      "regions": []
    }
  ]
}
```

```
# diff.yml schema — existing per_region: shape; output bboxes MUST be paste-compatible
visual_diff:
  max_pixel_mismatch_pct: 1.0
  fuzz_pct: 25.0
  per_region:
    - page: 1
      bbox_mm: { x: 10, y: 100, w: 50, h: 60 }
      max_pixel_mismatch_pct: 5.0
      fuzz_pct: 30
```

```
# NEW: diff_bboxes.json  — standalone artifact produced by this issue
{
  "dpi": 96,
  "template_slug": "postkarte-a6-kampagne",   # optional; null if --template-slug unset
  "pages": [
    {
      "page": 0,
      "delta_png": "diff-page-01.png",
      "bboxes": [
        {
          "bbox_px": {"x": 49, "y": 182, "w": 152, "h": 112},
          "bbox_mm": {"x": 12.3, "y": 45.6, "w": 38.0, "h": 28.0},
          "area_px": 1842,                    # raw connected-components area
          "mismatch_pct_in_bbox": 8.3,        # area_px / (w_px * h_px) * 100
          "attributed_slot": "P1 Kandidat-Portrait",   # or null
          "attribution_overlap_pct": 92.0,    # coverage_of_diff_inside_slot * 100
          "attribution_candidates": [          # top-3, descending coverage
            {"slot": "P1 Kandidat-Portrait", "coverage_pct": 92.0, "slot_area_mm2": 8700.0},
            {"slot": "P1 Top-Band",           "coverage_pct": 12.0, "slot_area_mm2": 3255.0}
          ]
        }
      ]
    }
  ]
}
```

```
# NEW: when visual_diff.py --extract-bboxes is set, the merged visual_diff.json
# gets an extra "bboxes" field per page (existing keys preserved verbatim):
{
  "dpi": 96, "pages": [
    { "page": 0, "mismatch_pixels": 1234, "...": "...",
      "delta_png": "diff-page-01.png",
      "bboxes": [ /* same shape as diff_bboxes.json pages[i].bboxes */ ]
    }
  ]
}
```

```
# ImageMagick connected-components output  (the line format we parse)
Objects (id: bounding-box centroid area mean-color):
  0: 1240x1754+0+0 619.5,876.7 2174960 srgba(255,255,255,1)   ← background (drop)
  1:    12x18+340+512  345.5,520.5 216 srgba(199,23,35,1)      ← real diff bbox
# regex:
_CC_RE = re.compile(
    r"^\s*(\d+):\s+(\d+)x(\d+)\+(\d+)\+(\d+)\s+[\d.]+,[\d.]+\s+(\d+)\s+(.+)$"
)
# groups: (id, w, h, x, y, area, mean_color_str)
```

```
# Coverage formula (decision 4). Inline; no library.
def coverage_of_diff_inside_slot(diff_bbox, slot_bbox):
    """Both bboxes are dicts {x, y, w, h} in mm.
    Returns intersect_area / diff_area in [0, 1]."""
    ix = max(0.0, min(diff_bbox["x"] + diff_bbox["w"], slot_bbox["x"] + slot_bbox["w"])
                  - max(diff_bbox["x"], slot_bbox["x"]))
    iy = max(0.0, min(diff_bbox["y"] + diff_bbox["h"], slot_bbox["y"] + slot_bbox["h"])
                  - max(diff_bbox["y"], slot_bbox["y"]))
    intersect = ix * iy
    diff_area = diff_bbox["w"] * diff_bbox["h"]
    return (intersect / diff_area) if diff_area > 0 else 0.0
```

**Key files (open these before editing):**
- `tools/visual_diff.py` — visual_diff.py:216-278 (page loop) is where `--extract-bboxes` shell-out goes; visual_diff.py:307-308 is the JSON write site (read existing, merge, rewrite).
- `tools/audit_alignment.py` — audit_alignment.py:52 (`load_build_module` import) + audit_alignment.py:240-254 (iterate pages & extract slot bboxes).
- `tools/sla_lib/builder/bbox.py` — `frame_bbox_mm` source (do not modify).
- `tools/sla_lib/tests/test_audit_alignment.py` lines 1-25 — canonical test-file header / sys.path bootstrap to copy.
- `templates/postkarte-a6-kampagne/build.py` + `meta.yml` — the integration-test target. Its `template.sla` + `baseline.pdf` + `diff.yml` are committed.

## Commit Format

Format: conventional with issue prefix (per `.issues/config.yaml`).
Pattern: `36: <type>(<scope>): <subject>`
Examples:
- `36: feat(visual-diff): add diff_bbox_extract.py with IM connected-components`
- `36: test(visual-diff): cover slot attribution edge cases`
- `36: feat(visual-diff): wire --extract-bboxes flag in visual_diff.py`

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`.

## Tasks

<task id="1" title="Bootstrap diff_bbox_extract.py — CLI + error class, no logic yet">
<action>
Create `tools/diff_bbox_extract.py`. Header convention follows
`tools/visual_diff.py` (shebang, `from __future__ import annotations`,
module docstring with Usage block, dataclasses near top, `main()` +
`if __name__ == "__main__": raise SystemExit(main())`).

Module docstring MUST cover:
- one-paragraph purpose ("post-processor for visual_diff.py delta PNGs")
- Usage block with both invocations:
  ```
  python3 tools/diff_bbox_extract.py <visual-diff-out-dir>
  python3 tools/diff_bbox_extract.py <visual-diff-out-dir> \
      --template-slug postkarte-a6-kampagne \
      --threshold 200 --min-area-px 100 --coverage-threshold 0.5 \
      --overlay-out
  ```
- the four default values (threshold=200, min_area_px=100, coverage_threshold=0.5, dilate disabled v1).
- strict-mode behaviour summary (raise on missing delta PNG / missing dpi; warn on missing slots / build-module load failure — see task 10).

Argparse positional + flags:
- `out_dir: Path` (positional) — the existing `visual_diff.py` output directory.
- `--template-slug STR` (optional; if absent, attribution is skipped).
- `--threshold INT` (default 200; red-channel cutoff per decision 2).
- `--min-area-px INT` (default 100).
- `--coverage-threshold FLOAT` (default 0.5).
- `--overlay-out` (store_true; off by default — when set, write `diff-page-NN-overlay.png` next to deltas).
- `--json-out PATH` (default `<out_dir>/diff_bboxes.json`).

Define an error class at module top:
```python
class DiffBBoxError(RuntimeError):
    """Strict-mode failure (missing delta PNG, missing dpi in visual_diff.json, etc.)."""
```

`main(argv=None) -> int` parses args and currently just `print()`s the parsed
namespace and returns 0. Real logic lands in tasks 2–10.

Add `chmod +x tools/diff_bbox_extract.py` semantics by including the
`#!/usr/bin/env python3` shebang (mirrors visual_diff.py:1).
</action>
<files>
tools/diff_bbox_extract.py
</files>
<verify>
<automated>python3 /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution/tools/diff_bbox_extract.py --help 2>&1 | grep -q "out_dir" && python3 -c "import sys; sys.path.insert(0, '/root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution/tools'); import diff_bbox_extract; assert hasattr(diff_bbox_extract, 'DiffBBoxError'); assert issubclass(diff_bbox_extract.DiffBBoxError, RuntimeError); print('OK')"</automated>
</verify>
<done>`tools/diff_bbox_extract.py` exists, `--help` lists every flag in the action, `DiffBBoxError` importable.</done>
</task>

<task id="2" title="ImageMagick connected-components shell-out + parse">
<action>
Add `extract_bboxes_px(delta_png: Path, threshold: int, min_area_px: int)
-> list[dict]` to `tools/diff_bbox_extract.py`. Returns a list of dicts
`{"x_px": int, "y_px": int, "w_px": int, "h_px": int, "area_px": int,
"mean_color": str}` for each non-background connected component.

Algorithm (decision 1 + decision 2):
1. Run two-stage IM convert via `subprocess.run([...], capture_output=True, text=True, check=True)`:
   ```python
   # Stage A: threshold red-on-white delta to a binary mask.
   # `-threshold 90%` (after grayscale) turns any non-near-white pixel black;
   # `-negate` flips so diff pixels become white (foreground for CC).
   # We can chain it all in one IM call for speed:
   cmd = [
       "convert", str(delta_png),
       "-colorspace", "Gray", "-threshold", "90%", "-negate",
       "-define", "connected-components:verbose=true",
       "-connected-components", "8",
       "info:-",
   ]
   ```
   IM writes the connected-components table to stdout. We do NOT need
   a temporary mask PNG.

2. Parse stdout line-by-line with this regex (already provided in
   `<interfaces>` — define at module scope):
   ```python
   _CC_RE = re.compile(
       r"^\s*(\d+):\s+(\d+)x(\d+)\+(\d+)\+(\d+)\s+[\d.]+,[\d.]+\s+(\d+)\s+(.+)$"
   )
   ```
   Skip the leading `Objects (id: ...)` header line. For each match:
   - drop `id == 0` (background — IM always emits the largest object first;
     after `-negate` it is the black area, mean-color `gray(0)` or
     `srgba(0,0,0,1)` — drop unconditionally on `id == 0`).
   - drop `area < min_area_px`.
   - keep the rest as the result list.

3. Sort the result list by `(y_px, x_px, w_px, h_px)` for deterministic
   ordering. This complements the cross-page sort happening in task 6.

4. If `delta_png` does not exist: raise `DiffBBoxError` with a clear
   "missing delta PNG: <path>" message (strict-mode UX from RESEARCH.md
   `Strict-mode UX` block + locked decision; full strict handling lands
   in task 10 but this hot-path raises now).

5. Validate empirically against
   `build/validation/postkarte-a6-kampagne/diff-page-01.png` if it
   exists locally (it is a generated artifact; if absent run
   `python3 tools/visual_diff.py templates/postkarte-a6-kampagne/template.sla
   --baseline templates/postkarte-a6-kampagne/baseline.pdf
   --tolerance templates/postkarte-a6-kampagne/diff.yml
   --ci --out build/validation/postkarte-a6-kampagne/` first). Expected
   shape: a small handful (≤ ~10) of small bboxes once the page-edge AA
   strip is filtered out via `min_area_px=100`. If the result is
   "every pixel is one giant bbox" the threshold needs lowering — note
   the empirical default in the module docstring.

Add a unit test `tools/sla_lib/tests/test_diff_bbox_extract.py`
using `unittest.TestCase`. Header matches `test_audit_alignment.py:1-25`:
```python
from __future__ import annotations
import sys, tempfile, shutil, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import diff_bbox_extract  # noqa: E402
```

Tests:
- `test_synthetic_red_rect_one_bbox`: Pillow-draw a 200×200 RGBA white image
  with a single 30×20 px rectangle of `(199, 23, 35, 255)` at (50, 60).
  Save to a `tempfile.mkdtemp()` dir. `extract_bboxes_px` returns exactly
  one bbox with `x_px=50, y_px=60, w_px=30, h_px=20` and `area_px=600`.
- `test_two_separated_rects_two_bboxes`: same, two non-adjacent red
  rects → exactly two bboxes, sorted by (y, x).
- `test_below_min_area_filtered`: a 3×3 red rect with `min_area_px=100`
  → empty list.
- `test_missing_delta_raises_DiffBBoxError`: nonexistent path → raises.
- Use `try/finally: shutil.rmtree(tmpdir)`.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -20</automated>
</verify>
<done>All 4 unit tests pass; `extract_bboxes_px` returns sorted list of dicts, drops id=0 and < min_area_px, raises `DiffBBoxError` on missing input.</done>
</task>

<task id="3" title="DPI lookup + px → mm conversion">
<action>
Add to `tools/diff_bbox_extract.py`:

```python
def load_dpi(out_dir: Path) -> int:
    """Read visual_diff.json from out_dir, return its top-level `dpi` int.
    Raises DiffBBoxError if file is missing or `dpi` key is absent."""
```

Implementation:
- `vd_path = out_dir / "visual_diff.json"`
- if not `vd_path.exists()`: `raise DiffBBoxError(f"missing visual_diff.json in {out_dir} — run tools/visual_diff.py first")`
- load JSON; if `"dpi"` not in dict: `raise DiffBBoxError(f"visual_diff.json missing 'dpi' field at {vd_path}")`
- return `int(payload["dpi"])`.

Add:
```python
def px_to_mm_bbox(bbox_px: dict, dpi: int) -> dict:
    """Convert {x_px, y_px, w_px, h_px} pixel bbox to {x, y, w, h} mm bbox,
    rounded to 0.1 mm per determinism decision 5b."""
    mm_per_px = 25.4 / dpi
    return {
        "x": round(bbox_px["x_px"] * mm_per_px, 1),
        "y": round(bbox_px["y_px"] * mm_per_px, 1),
        "w": round(bbox_px["w_px"] * mm_per_px, 1),
        "h": round(bbox_px["h_px"] * mm_per_px, 1),
    }
```

Tests in the same `test_diff_bbox_extract.py`:
- `test_load_dpi_reads_value`: write a `visual_diff.json` with `{"dpi": 96, "pages": []}` to a tmpdir, assert `load_dpi(tmpdir) == 96`.
- `test_load_dpi_missing_file_raises`: empty tmpdir → raises `DiffBBoxError`.
- `test_load_dpi_missing_key_raises`: write `{"pages": []}` (no dpi) → raises.
- `test_px_to_mm_at_96dpi`: a `{x_px:96, y_px:192, w_px:48, h_px:24}` bbox at 96 dpi → `{x:25.4, y:50.8, w:12.7, h:6.4}` (within 0.1 mm rounding).
- `test_px_to_mm_at_150dpi`: same input at 150 dpi → values scale by 96/150.

The round-to-0.1 step is what makes the px-to-mm conversion FP-stable.
Document this in the function docstring.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -25</automated>
</verify>
<done>5 new tests pass; px→mm conversion rounds to 0.1 mm; missing JSON / missing dpi both raise `DiffBBoxError` with helpful messages.</done>
</task>

<task id="4" title="Slot loader using load_build_module + frame_bbox_mm">
<action>
Add to `tools/diff_bbox_extract.py`:

```python
def load_template_slots(template_slug: str) -> dict[int, dict[str, dict]]:
    """For each page index, return a dict {anname: {x, y, w, h} mm}.

    Reuses tools/audit_alignment.py's pattern verbatim. Returns an empty
    dict if the template has no slots or build fails (logged via warn,
    not raised — strict-mode behaviour from RESEARCH.md `Strict-mode UX`).
    Keys are 0-indexed page integers matching visual_diff.json's `page`.
    """
```

Implementation:
- Import (lazily, at top of function so test imports stay cheap):
  ```python
  from sla_lib.builder.template_loader import load_build_module
  from sla_lib.builder.bbox import frame_bbox_mm
  ```
- Resolve repo root: `ROOT = Path(__file__).resolve().parent.parent`
  (matches `audit_alignment.py` convention).
- Wrap the build in try/except:
  ```python
  try:
      mod = load_build_module(template_slug, ROOT)
      doc = mod.build_preview() if hasattr(mod, "build_preview") else mod.build_doc()
  except Exception as e:
      warnings.warn(f"diff_bbox_extract: template '{template_slug}' build failed ({e!r}); skipping attribution")
      return {}
  ```
- Walk pages mirroring audit_alignment.py:240-254:
  ```python
  slots: dict[int, dict[str, dict]] = {}
  for idx, page in enumerate(doc.pages):
      if page.is_master:
          continue
      page_slots: dict[str, dict] = {}
      for item in page.items:
          anname = getattr(item, "anname", None) or ""
          if not anname:
              continue
          b4 = frame_bbox_mm(item, page)         # (min_x, min_y, max_x, max_y) mm
          if b4 is None:
              continue
          min_x, min_y, max_x, max_y = b4
          page_slots[anname] = {
              "x": round(min_x, 1),
              "y": round(min_y, 1),
              "w": round(max_x - min_x, 1),
              "h": round(max_y - min_y, 1),
          }
      if page_slots:
          slots[idx] = page_slots
  return slots
  ```
- The page-index convention here matches `visual_diff.json`'s 0-indexed
  `page` field. NOTE: the file naming (`diff-page-01.png`) is 1-indexed
  via `f"{idx+1:02d}"` (visual_diff.py:231). Document this delta in the
  docstring — file names are 1-based, JSON / slot keys are 0-based.

Tests in `test_diff_bbox_extract.py`:
- `test_load_slots_postkarte`: call `load_template_slots("postkarte-a6-kampagne")`,
  assert returned dict has 2 pages (indices 0 and 1), each with non-empty
  `anname → bbox` mappings, every bbox dict has keys `{x, y, w, h}` of type `float`.
- `test_load_slots_unknown_template_warns_and_returns_empty`: call with
  slug `"definitely-does-not-exist"`, capture warnings via
  `with warnings.catch_warnings(record=True) as w:` — assert at least one
  warning + return value is `{}`.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -25</automated>
</verify>
<done>`load_template_slots("postkarte-a6-kampagne")` returns dict with 2 page entries and named-slot bbox sub-dicts; unknown slug warns and returns `{}`.</done>
</task>

<task id="5" title="Slot attribution math + candidates list">
<action>
Add to `tools/diff_bbox_extract.py`:

```python
def coverage_of_diff_inside_slot(diff_bbox: dict, slot_bbox: dict) -> float:
    """Both bboxes are dicts {x, y, w, h} in mm. Returns intersect_area
    / diff_bbox_area in [0.0, 1.0]. Returns 0.0 if diff_bbox has zero area."""
    ix = max(0.0, min(diff_bbox["x"] + diff_bbox["w"],
                      slot_bbox["x"] + slot_bbox["w"])
                  - max(diff_bbox["x"], slot_bbox["x"]))
    iy = max(0.0, min(diff_bbox["y"] + diff_bbox["h"],
                      slot_bbox["y"] + slot_bbox["h"])
                  - max(diff_bbox["y"], slot_bbox["y"]))
    intersect = ix * iy
    diff_area = diff_bbox["w"] * diff_bbox["h"]
    return (intersect / diff_area) if diff_area > 0 else 0.0


def attribute_diff_bbox(
    diff_bbox: dict, page_slots: dict[str, dict],
    coverage_threshold: float = 0.5,
) -> tuple[Optional[str], float, list[dict]]:
    """Return (attributed_slot_or_None, overlap_pct, top3_candidates).

    candidates list shape (decision 4, top-3, sorted desc by coverage,
    tie-break asc by slot area):
        [{"slot": str, "coverage_pct": float, "slot_area_mm2": float}, ...]
    Attribution returns the first candidate iff its coverage ≥ threshold.
    overlap_pct is `coverage * 100.0` (matches RESEARCH.md schema).
    """
```

Implementation:
- Build list `cands = []` of tuples `(slot_name, coverage, slot_area)`
  for every slot in `page_slots`.
- Sort by `(-coverage, slot_area)` per decision 4 tie-break (smaller area
  wins among ties).
- Format top-3 as the candidate-dict list, rounding `coverage_pct` and
  `slot_area_mm2` to 1 decimal place for determinism.
- attribution := `(top[0]["slot"], top[0]["coverage_pct"])` if top exists
  AND its raw coverage ≥ `coverage_threshold`, else `(None, 0.0)`.
- Return `(slot_or_None, overlap_pct, candidates_top3)`.

Tests in `test_diff_bbox_extract.py`:
- `test_coverage_full_overlap`: diff bbox `{x:10,y:10,w:5,h:5}` inside slot
  `{x:0,y:0,w:50,h:50}` → coverage `1.0`.
- `test_coverage_no_overlap`: disjoint bboxes → `0.0`.
- `test_coverage_partial_50pct`: diff half inside slot → `0.5`.
- `test_coverage_zero_area_diff_returns_zero`: `{x:0,y:0,w:0,h:0}` → `0.0`.
- `test_attribute_picks_smaller_slot_on_tie`: diff bbox fully inside two
  slots (a 30×30 outer "Bg" and a 10×10 inner "Headline"; diff bbox is
  5×5 inside both); both coverages = 1.0 → attribution returns
  `"Headline"` (smaller area wins per decision 4).
- `test_attribute_no_match_below_threshold`: diff bbox 90% outside the
  only slot (coverage 0.1, threshold 0.5) → returns `(None, ..., candidates)`.
- `test_candidates_top3_only`: 5 slots all with non-zero coverage →
  returned candidates list has exactly 3 entries, sorted by `-coverage`
  then by `slot_area_mm2` ascending.
- `test_empty_page_slots_returns_none_attribution`: `page_slots = {}` →
  `(None, 0.0, [])`.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -30</automated>
</verify>
<done>Coverage formula matches decision 4 (intersect / diff_area, not IoU); smaller-area tie-break verified; top-3 candidates returned with correct sort; threshold gating works.</done>
</task>

<task id="6" title="JSON assembly + determinism guarantees">
<action>
Add the top-level pipeline function to `tools/diff_bbox_extract.py`:

```python
def extract_all(
    out_dir: Path,
    *,
    template_slug: Optional[str] = None,
    threshold: int = 200,
    min_area_px: int = 100,
    coverage_threshold: float = 0.5,
) -> dict:
    """Pipeline: iterate visual_diff.json's pages list, run extractor
    per delta PNG, attribute against template slots, return the full
    diff_bboxes.json payload as a dict."""
```

Implementation:
1. `dpi = load_dpi(out_dir)`.
2. Read `out_dir / "visual_diff.json"` for the `pages` list — use it
   to enumerate delta PNGs (decision: DO NOT glob; use the recorded
   `delta_png` field, since file names are 2-digit zero-padded
   regardless of page count — pitfall from RESEARCH.md).
3. `slots = load_template_slots(template_slug) if template_slug else {}`.
4. For each page entry in `visual_diff.json["pages"]`:
   - `page_idx = int(page["page"])`
   - `delta_path = out_dir / page["delta_png"]`
   - `bboxes_px = extract_bboxes_px(delta_path, threshold, min_area_px)`
   - For each px-bbox:
     - `bbox_mm = px_to_mm_bbox(b, dpi)`
     - `w_px = b["w_px"]; h_px = b["h_px"]`
     - `mismatch_pct_in_bbox = round((b["area_px"] / (w_px * h_px)) * 100.0, 1)`
       (area_px is the actual mismatched-pixel count inside the
       w×h bounding rectangle; the ratio tells you density-of-diff inside
       the bbox).
     - `(attr_slot, overlap_pct, candidates) = attribute_diff_bbox(bbox_mm, slots.get(page_idx, {}), coverage_threshold)`
     - Assemble per-bbox record per the `<interfaces>` schema.
   - Append page record `{"page": page_idx, "delta_png": page["delta_png"], "bboxes": [...]}`.
5. Sort the per-page `bboxes` list by `(y, x, w, h)` mm (decision 5a).
6. Build top-level dict `{"dpi": dpi, "template_slug": template_slug,
   "pages": [...]}`. Pages already iterate in 0..N order from
   `visual_diff.json`.

Add `write_json(payload: dict, json_path: Path) -> None`:
```python
def write_json(payload: dict, json_path: Path) -> None:
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
```
`sort_keys=True` is decision 5c.

Wire `main()` so the bootstrap CLI from task 1 now actually runs the
pipeline, writes the JSON, prints `wrote <path> ({n} bboxes across {p} pages)`,
and returns 0 / 1 based on success.

Tests in `test_diff_bbox_extract.py`:
- `test_extract_all_deterministic_byte_equal`: build a synthetic
  `out_dir` (Pillow-drawn delta PNGs for 2 pages + a minimal
  `visual_diff.json` `{"dpi": 96, "pages": [{"page": 0, "delta_png":
  "diff-page-01.png"}, {"page": 1, "delta_png": "diff-page-02.png"}]}`).
  Run `extract_all` twice; serialise both via `write_json` to separate
  temp files; assert the two files are byte-identical
  (`Path.read_bytes()` equality).
- `test_extract_all_sorts_bboxes_by_y_then_x`: page with three red rects
  at varying (x, y) → returned bboxes list is ordered by `(y, x, w, h)`.
- `test_extract_all_no_template_slug_unattributed`: synthetic input, no
  `template_slug` passed → every bbox has `attributed_slot is None` and
  `attribution_candidates == []`.
- `test_extract_all_uses_recorded_delta_filename`: forge a
  `visual_diff.json` with `delta_png: "diff-page-99.png"` (NOT
  page-index-derived) and make sure the file IS read from that path.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -30</automated>
</verify>
<done>`extract_all` produces a dict matching the `<interfaces>` schema; running it twice on the same input writes byte-identical JSON files; bboxes sorted by `(y, x, w, h)`; delta-PNG path is read from `visual_diff.json["pages"][i]["delta_png"]`.</done>
</task>

<task id="7" title="Red-overlay PNG output (--overlay-out)">
<action>
Add to `tools/diff_bbox_extract.py`:

```python
def write_overlay_png(
    src_png: Path, bboxes_px: list[dict], dst_png: Path,
) -> None:
    """Draw red rectangle outlines (no fill) for each px bbox on a copy
    of src_png; save to dst_png. Used to mark diffs on the DSL rendering
    for human review."""
    from PIL import Image, ImageDraw  # lazy import — Pillow only loaded if used
    img = Image.open(src_png).convert("RGBA")
    draw = ImageDraw.Draw(img)
    for b in bboxes_px:
        x, y, w, h = b["x_px"], b["y_px"], b["w_px"], b["h_px"]
        draw.rectangle([x, y, x + w, y + h],
                       outline=(255, 0, 0, 255), width=2)
    dst_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst_png, format="PNG")
```

Wire `--overlay-out` in `extract_all` + `main`:
- When the flag is set, for each page also:
  - Resolve source PNG: prefer `out_dir / f"dsl-page-{idx+1}.png"`
    (1-digit) and fall back to `out_dir / f"dsl-page-{idx+1:02d}.png"`
    (2-digit) — the `dsl-page-` files use VARIABLE padding (visual_diff.py:222
    via pdftoppm). Use `pathlib.Path.exists()` to pick.
  - Destination: `out_dir / f"diff-page-{idx+1:02d}-overlay.png"`
    (mirrors the always-2-digit `diff-page-NN.png` convention from
    visual_diff.py:231).
  - Call `write_overlay_png(src, page_bboxes_px, dst)`.

Note: `extract_all` currently only carries the `bboxes_mm` records — for
the overlay we also need `bboxes_px`. Easiest fix: have `extract_all`
internally keep both, and expose an optional `overlay_out: bool` kw-arg
that triggers the side-effect; the returned JSON dict is unchanged.

Test in `test_diff_bbox_extract.py`:
- `test_overlay_writes_png_with_correct_dimensions`: synthetic
  `dsl-page-1.png` (Pillow-drawn 400×300 RGBA), call
  `write_overlay_png` with one bbox `{x_px:10, y_px:20, w_px:30, h_px:40}`,
  open the output via Pillow, assert mode is RGBA, size unchanged
  (400, 300), and at least one pixel in the rectangle outline area is
  red `(255, 0, 0, 255)`.
- `test_extract_all_overlay_off_by_default`: run `extract_all` without
  `overlay_out=True` → no `*-overlay.png` files written.
- `test_extract_all_overlay_on_creates_files`: run `extract_all` with
  `overlay_out=True` → exactly N `diff-page-NN-overlay.png` files
  written next to the deltas.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -30</automated>
</verify>
<done>`--overlay-out` writes one `diff-page-NN-overlay.png` per page with red rectangle outlines on the DSL rendering; default behaviour writes none; output dimensions preserved.</done>
</task>

<task id="8" title="CLI end-to-end integration test on a real visual_diff.py output dir">
<action>
Add an integration test class `DiffBBoxIntegrationTests(unittest.TestCase)`
to `tools/sla_lib/tests/test_diff_bbox_extract.py`. The goal is to prove
the extractor works against a **real** `visual_diff.py` output directory
for `postkarte-a6-kampagne` — the smallest committed template fixture.

Strategy:
- `setUpClass`: build the `visual_diff` output dir in a class-level tempdir
  by invoking `tools/visual_diff.py`. This is slow (Scribus + pdftoppm
  + IM compare) — gate with `@unittest.skipUnless(shutil.which("scribus") and shutil.which("pdftoppm"), "scribus/pdftoppm not available")`
  so the test stays runnable in restricted environments. Command:
  ```python
  subprocess.run([
      sys.executable, str(ROOT / "tools" / "visual_diff.py"),
      str(ROOT / "templates" / "postkarte-a6-kampagne" / "template.sla"),
      "--baseline", str(ROOT / "templates" / "postkarte-a6-kampagne" / "baseline.pdf"),
      "--tolerance", str(ROOT / "templates" / "postkarte-a6-kampagne" / "diff.yml"),
      "--ci",
      "--out", str(cls.tmp / "vd"),
  ], check=False)  # check=False — visual_diff exits 1 on tolerance violation, that's fine
  ```
  Do NOT regenerate per test method — once per class. `tearDownClass`
  removes the tempdir.

- `test_runs_against_real_output_dir_writes_json`: call
  `diff_bbox_extract.main([str(cls.tmp / "vd"), "--template-slug", "postkarte-a6-kampagne"])`,
  assert exit 0, `diff_bboxes.json` exists in `cls.tmp / "vd"`, JSON loads,
  has top-level keys `{dpi, template_slug, pages}`, `pages` length matches
  `visual_diff.json`'s pages length.

- `test_deterministic_on_real_dir`: call `main` twice with
  `--json-out` pointed to different files; assert both files
  `read_bytes()` are equal.

- `test_overlay_files_produced`: invoke with `--overlay-out`; assert
  `diff-page-01-overlay.png` and `diff-page-02-overlay.png` exist.

- `test_at_least_one_attributed_bbox`: after running, parse
  `diff_bboxes.json`; assert at least one bbox across all pages has
  `attributed_slot is not None` (validates the slot loader is wired
  through the full pipeline). If zero attributions happen for
  postkarte, the test author should add a synthetic diff PNG with a
  bbox deliberately inside a known slot — but the real template should
  hit attribution naturally since postkarte slots cover most of the
  page area.

Notes:
- Run the integration class only when scribus is available; otherwise
  `@skipUnless` makes them green-skipped (logged as `s` in unittest output).
- The unit tests from tasks 2-7 already cover correctness on synthetic
  fixtures; integration just validates the binary against real artifacts.
</action>
<files>
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -20</automated>
</verify>
<done>Integration tests pass (or skip cleanly if Scribus absent); `diff_bboxes.json` produced from a real `postkarte-a6-kampagne` visual_diff dir, at least one bbox attributed to a named slot, byte-equal on re-run.</done>
</task>

<task id="9" title="Wire --extract-bboxes flag into visual_diff.py">
<action>
Modify `tools/visual_diff.py`:

1. Update the module docstring (visual_diff.py:1-22) — add a line in the
   Pipeline list: `7. (optional) Extract bboxes from the per-page delta
   PNG via tools/diff_bbox_extract.py when --extract-bboxes is set;
   merge into visual_diff.json as a per-page 'bboxes' field`. Add the
   `--extract-bboxes` flag to the Usage block.

2. In `main()` argparse (visual_diff.py:344-358), add:
   ```python
   ap.add_argument("--extract-bboxes", action="store_true",
                   help="After comparing, run tools/diff_bbox_extract.py "
                        "and merge per-page bboxes into visual_diff.json")
   ap.add_argument("--template-slug", type=str, default=None,
                   help="Template slug for bbox slot attribution "
                        "(only used with --extract-bboxes)")
   ```

3. After `visual_diff(...)` returns (visual_diff.py:360-361) and the JSON
   has been written by `write_reports`, conditionally invoke the extractor:
   ```python
   if args.extract_bboxes:
       _merge_bboxes_into_visual_diff(args.out, args.template_slug)
   ```
   Add the helper at module scope (do NOT import diff_bbox_extract at
   the top of visual_diff.py — keep visual_diff.py importable without
   diff_bbox_extract being on path):
   ```python
   def _merge_bboxes_into_visual_diff(
       out_dir: Path, template_slug: Optional[str]
   ) -> None:
       """Shell out to diff_bbox_extract.py and merge its JSON into
       visual_diff.json. Backward-compatible: existing keys preserved;
       only adds a per-page 'bboxes' field."""
       extractor = Path(__file__).resolve().parent / "diff_bbox_extract.py"
       cmd = [sys.executable, str(extractor), str(out_dir)]
       if template_slug:
           cmd += ["--template-slug", template_slug]
       _run(cmd)
       bb_path = out_dir / "diff_bboxes.json"
       vd_path = out_dir / "visual_diff.json"
       bb = json.loads(bb_path.read_text(encoding="utf-8"))
       vd = json.loads(vd_path.read_text(encoding="utf-8"))
       # Index extractor's pages by their page index for safe merging.
       bb_by_idx = {int(p["page"]): p.get("bboxes", []) for p in bb["pages"]}
       for page in vd["pages"]:
           page["bboxes"] = bb_by_idx.get(int(page["page"]), [])
       vd_path.write_text(
           json.dumps(vd, indent=2, ensure_ascii=False),
           encoding="utf-8",
       )
   ```
   (Reuses `_run` defined at visual_diff.py:100 for subprocess execution.)

Tests in `tools/sla_lib/tests/test_diff_bbox_extract.py` — new class
`VisualDiffWiringTests`:
- `test_visual_diff_no_flag_unchanged`: copy a pre-generated fixture
  `visual_diff.json` to a tmpdir, simulate the no-flag path
  (no-op import path: import `visual_diff` and assert the default
  argparse namespace has `extract_bboxes is False`). No subprocess.
- `test_merge_function_adds_bboxes_field`: write a minimal
  `visual_diff.json` `{"dpi":96, "pages":[{"page":0, "delta_png":"diff-page-01.png"}]}`
  + a synthetic 200×200 delta PNG with one red rect, into a tmpdir.
  Call `visual_diff._merge_bboxes_into_visual_diff(tmpdir, None)`.
  Re-read `visual_diff.json`; assert `pages[0]["bboxes"]` is a list,
  has ≥1 entry, and existing keys (`page`, `delta_png`) preserved.
- `test_merge_no_template_slug_warns_no_raise`: same as above but with
  `template_slug="not-a-real-template"`; should complete (warn-not-raise)
  and write `attributed_slot: None` everywhere.

Use `tempfile.mkdtemp() + try/finally: shutil.rmtree`.
</action>
<files>
tools/visual_diff.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 tools/visual_diff.py --help 2>&1 | grep -q "extract-bboxes" && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -25</automated>
</verify>
<done>`visual_diff.py --help` lists `--extract-bboxes` and `--template-slug`; default behaviour unchanged when flag absent; with flag, `visual_diff.json` gains a per-page `bboxes` list matching the extractor's output.</done>
</task>

<task id="10" title="Strict-mode UX + edge cases">
<action>
Tighten `tools/diff_bbox_extract.py` strict-mode behaviour to match
RESEARCH.md's `Strict-mode UX` block and decision-tree:

Loud raises (`DiffBBoxError`):
- Delta PNG referenced by `visual_diff.json` is missing on disk.
- `visual_diff.json` itself missing.
- `visual_diff.json` missing `dpi` field.
- IM `convert` invocation returns non-zero (already handled by
  `subprocess.run(..., check=True)` in task 2 — but wrap the
  `CalledProcessError` so the message includes the delta PNG path
  + IM stderr).

Quiet warnings (`warnings.warn(...)`) + continue:
- `--template-slug` set but `load_build_module` fails — emit warning
  `"diff_bbox_extract: template '<slug>' build failed (...); attribution skipped"`
  and continue. Bboxes still emitted with `attributed_slot: null`.
- `--template-slug` set, build succeeds, but page has no `anname`d items —
  per-page `attributed_slot: null` silently (no warning; not an error).
- `--template-slug` NOT set — just attribute as null silently.

Logging: use `warnings.warn` (not `print(file=sys.stderr)`) so tests can
capture via `warnings.catch_warnings(record=True)`. Suppress duplicate
warnings via stacklevel=2.

Add these tests to `test_diff_bbox_extract.py`:
- `test_missing_delta_referenced_by_json_raises`: build a
  `visual_diff.json` whose `delta_png` points to a non-existent file →
  `main()` returns 1 (catches `DiffBBoxError`, prints to stderr, exits
  non-zero — or raises if you prefer; the integration test should
  observe a non-zero exit code either way).
- `test_im_failure_raises_diffbboxerror`: feed a non-PNG file (e.g.
  an empty file ending in `.png`) as the delta PNG so IM fails → raises
  `DiffBBoxError` whose message contains the path AND mentions ImageMagick.
- `test_template_build_failure_emits_warning_not_raise`: `template_slug`
  pointing at a slug whose `build.py` will crash (use a tempdir-built
  fake template if needed — or rely on the slug `"definitely-broken-slug"`
  triggering the not-found path inside `load_template_slots`) →
  `extract_all(...)` returns successfully, all bboxes have
  `attributed_slot is None`, ≥1 warning recorded.
- `test_template_with_no_slots_unattributed_silent`: synthetic build_module
  with one page and no `anname`d items → no warning, every bbox
  `attributed_slot is None`.

Also: in `main()`, wrap `extract_all` in try/except `DiffBBoxError`:
print the error message to stderr, return 1. Other exceptions propagate.
</action>
<files>
tools/diff_bbox_extract.py
tools/sla_lib/tests/test_diff_bbox_extract.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v 2>&1 | tail -30</automated>
</verify>
<done>All strict-mode raises and silent/loud warnings behave as specified; `main()` returns 1 on `DiffBBoxError` with a stderr message containing the offending path.</done>
</task>

<task id="11" title="Documentation: module docstring + defaults reference + visual_diff.py note">
<action>
Polish documentation. No new code — only docstrings.

1. `tools/diff_bbox_extract.py` module docstring (already drafted in
   task 1; expand it now that the full API is known):
   ```python
   """Visual-diff bbox extractor with slot attribution.

   Post-processor on tools/visual_diff.py's output directory: reads each
   diff-page-NN.png (the ImageMagick `compare` delta PNG, mode RGBA,
   mismatch pixels = (199,23,35,255)), runs IM 8-connected-components
   labelling, converts the resulting pixel bboxes to mm via the DPI
   recorded in visual_diff.json, optionally attributes each bbox to a
   template-defined named-frame slot (loaded via the same
   load_build_module + frame_bbox_mm path tools/audit_alignment.py uses),
   and writes a deterministic diff_bboxes.json next to the deltas.

   Defaults (overridable via CLI flags):
     threshold=200            red-channel cutoff; pixels above are "diff"
     min_area_px=100          drop connected components below this area
     coverage_threshold=0.5   minimum coverage_of_diff_inside_slot for
                              attribution (`area_intersect / area_diff_bbox`)

   Output schema (diff_bboxes.json):
     {
       "dpi": 96,
       "template_slug": "<slug>" | null,
       "pages": [
         { "page": <int>, "delta_png": "<file>", "bboxes": [
           { "bbox_px": {x,y,w,h}, "bbox_mm": {x,y,w,h},
             "area_px": <int>, "mismatch_pct_in_bbox": <float>,
             "attributed_slot": "<anname>" | null,
             "attribution_overlap_pct": <float>,
             "attribution_candidates": [
               {"slot": "...", "coverage_pct": <float>, "slot_area_mm2": <float>},
               ... up to 3 ...
             ]
           } ]
         } ]
     }

   Limitations:
     - frame_bbox_mm() ignores xpos_pt/width_pt verbatim overrides
       (bbox.py:13-16); templates that use those will get off attribution.
     - Page-edge antialiasing strips can leak through min_area_px if the
       template has thin border elements; lower min_area_px per template
       in that case.

   Usage:
     # Standalone:
     python3 tools/diff_bbox_extract.py build/<template>/

     # With slot attribution:
     python3 tools/diff_bbox_extract.py build/<template>/ \\
         --template-slug <slug> --overlay-out

     # Via visual_diff.py wrapper (decision 3):
     python3 tools/visual_diff.py <sla> --baseline <pdf> --tolerance <yml> \\
         --extract-bboxes --template-slug <slug> --out build/<template>/
   """
   ```

2. `tools/visual_diff.py` module docstring (visual_diff.py:1-22) — append
   a line under Pipeline:
   `7. (optional, --extract-bboxes) Run tools/diff_bbox_extract.py to
   produce diff_bboxes.json and merge its per-page bboxes back into
   visual_diff.json.`
   And add to the Usage block:
   `    [--extract-bboxes --template-slug <slug>]`

3. Verify the docstrings are syntactically valid by importing the
   modules.
</action>
<files>
tools/diff_bbox_extract.py
tools/visual_diff.py
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -c "import sys; sys.path.insert(0, 'tools'); import diff_bbox_extract, visual_diff; assert 'diff_bboxes.json' in (diff_bbox_extract.__doc__ or ''); assert 'extract-bboxes' in (visual_diff.__doc__ or ''); print('OK')"</automated>
</verify>
<done>Both modules import cleanly; their docstrings document the JSON schema, the four default thresholds, the limitations, and the `--extract-bboxes` flag.</done>
</task>

<task id="12" title="End-to-end smoke + ISSUE.md acceptance-criteria pass">
<action>
Run the full suite end-to-end against the postkarte template and verify
every ISSUE.md acceptance criterion is satisfied. This task contains no
new code — only verification and any tiny fixes the smoke surfaces.

Steps:
1. Generate / refresh the real visual_diff output dir (skip if already
   present and not stale):
   ```bash
   python3 tools/visual_diff.py \
       templates/postkarte-a6-kampagne/template.sla \
       --baseline templates/postkarte-a6-kampagne/baseline.pdf \
       --tolerance templates/postkarte-a6-kampagne/diff.yml \
       --ci --out build/validation/postkarte-a6-kampagne/
   ```
   (May exit 1 on tolerance violation — that's fine; the artifacts are
   what we need.)

2. Run the extractor standalone:
   ```bash
   python3 tools/diff_bbox_extract.py \
       build/validation/postkarte-a6-kampagne/ \
       --template-slug postkarte-a6-kampagne \
       --overlay-out
   ```
   Verify:
   - exit code 0
   - `build/validation/postkarte-a6-kampagne/diff_bboxes.json` exists
   - `build/validation/postkarte-a6-kampagne/diff-page-01-overlay.png` exists
   - `build/validation/postkarte-a6-kampagne/diff-page-02-overlay.png` exists
   - At least one bbox in the JSON has a non-null `attributed_slot`
   - JSON validates against the `<interfaces>` schema (manually inspect
     keys; or write a quick `python3 -c` assertion script).

3. Re-run the extractor; confirm `diff_bboxes.json` is byte-identical:
   ```bash
   sha256sum build/validation/postkarte-a6-kampagne/diff_bboxes.json
   python3 tools/diff_bbox_extract.py build/validation/postkarte-a6-kampagne/ --template-slug postkarte-a6-kampagne
   sha256sum build/validation/postkarte-a6-kampagne/diff_bboxes.json   # → same hash
   ```

4. Run the wrapped invocation end-to-end:
   ```bash
   rm -rf build/validation/postkarte-a6-kampagne/
   python3 tools/visual_diff.py templates/postkarte-a6-kampagne/template.sla \
       --baseline templates/postkarte-a6-kampagne/baseline.pdf \
       --tolerance templates/postkarte-a6-kampagne/diff.yml \
       --extract-bboxes --template-slug postkarte-a6-kampagne \
       --ci --out build/validation/postkarte-a6-kampagne/
   ```
   Verify `visual_diff.json` has the new `bboxes` field per page.

5. Run all unit + integration tests:
   ```bash
   python3 -m unittest tools.sla_lib.tests.test_diff_bbox_extract -v
   python3 -m unittest discover tools/sla_lib/tests/ -v
   ```
   Both green (with integration tests skipped if scribus unavailable).

6. Check ISSUE.md acceptance criteria one-by-one (worth re-pasting here
   to confirm coverage):
   - [x] `tools/diff_bbox_extract.py` exists with documented usage
   - [x] Runs against existing template's visual_diff output dir,
     produces `diff_bboxes.json` + optional overlay PNGs
   - [x] Slot attribution works for postkarte-a6-kampagne (at least one
     bbox attributes to a named slot from `meta.yml`)
   - [x] Output deterministic (byte-equal on re-run, verified step 3)
   - [x] `visual_diff.py --extract-bboxes` invokes it and merges JSON
   - [x] Tests cover noisy-AA filtering (min_area_px), multi-cluster
     pages, unattributed (no slot ≥ threshold)

Final commit grouping (do NOT commit during planning — this is for the
executor):
  - `36: feat(visual-diff): add diff_bbox_extract.py with IM connected-components` (tasks 1-7)
  - `36: feat(visual-diff): wire --extract-bboxes flag in visual_diff.py` (task 9)
  - `36: test(visual-diff): unit + integration coverage for diff_bbox_extract` (tasks 2-10 tests)
  - `36: docs(visual-diff): document --extract-bboxes + JSON schema` (task 11)

If any acceptance criterion fails: fix in place, re-verify, do NOT
commit the failing state.
</action>
<files>
build/validation/postkarte-a6-kampagne/   (generated artifact, do not commit large PNGs)
</files>
<verify>
<automated>cd /root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution && python3 -m unittest discover tools/sla_lib/tests/ 2>&1 | tail -10 && test -f build/validation/postkarte-a6-kampagne/diff_bboxes.json && python3 -c "import json; d=json.load(open('build/validation/postkarte-a6-kampagne/diff_bboxes.json')); assert 'pages' in d and 'dpi' in d; assert any(b.get('attributed_slot') for p in d['pages'] for b in p.get('bboxes',[])), 'no attributions'; print('END-TO-END OK')"</automated>
</verify>
<done>End-to-end smoke passes against `postkarte-a6-kampagne`; `diff_bboxes.json` validates, deterministic, contains ≥1 attributed bbox; `visual_diff.py --extract-bboxes` produces a merged `visual_diff.json` with per-page `bboxes` field; all unit + integration tests green; every ISSUE.md acceptance criterion ticked.</done>
</task>

## Order

Sequential. Each task depends on the previous one:

- **1 → 2 → 3 → 4 → 5 → 6**: standalone extractor builds bottom-up
  (CLI scaffold → IM shell-out → DPI/units → slot loader → attribution
  math → assembly + determinism). Each task adds a layer the next depends
  on; no shortcut.
- **6 → 7**: overlay PNG needs `extract_all` to already produce the
  `bboxes_px` records.
- **6 → 8**: integration test needs the full standalone pipeline.
- **6 → 9**: `visual_diff.py` wiring shells out to the now-complete CLI.
- **9 → 10**: strict-mode + edge cases retrofitted across both code paths.
- **all → 11 → 12**: docs and final smoke.

**Parallelisable:** none in this plan. Each task either lays scaffold or
verifies on the previous layer. (If the executor wanted to overlap, task
7 could happen alongside task 8 — they touch independent helpers — but
the test file is shared, so it's cleaner to do them serially.)

**Blocking:** none. Issue #35 (IDML→DSL converter) is unrelated and not
on this branch (RESEARCH.md confirmed).

## Verification (overall)

After all 12 tasks, the following commands must all succeed:

```bash
# (a) Full unit + integration test sweep
python3 -m unittest discover tools/sla_lib/tests/ -v

# (b) Standalone extractor smoke on real postkarte output
python3 tools/visual_diff.py templates/postkarte-a6-kampagne/template.sla \
    --baseline templates/postkarte-a6-kampagne/baseline.pdf \
    --tolerance templates/postkarte-a6-kampagne/diff.yml \
    --ci --out build/validation/postkarte-a6-kampagne/  # may exit 1; OK
python3 tools/diff_bbox_extract.py build/validation/postkarte-a6-kampagne/ \
    --template-slug postkarte-a6-kampagne --overlay-out
test -f build/validation/postkarte-a6-kampagne/diff_bboxes.json
test -f build/validation/postkarte-a6-kampagne/diff-page-01-overlay.png

# (c) Determinism: two extractor runs → byte-identical JSON
python3 tools/diff_bbox_extract.py build/validation/postkarte-a6-kampagne/ \
    --template-slug postkarte-a6-kampagne \
    --json-out /tmp/db1.json
python3 tools/diff_bbox_extract.py build/validation/postkarte-a6-kampagne/ \
    --template-slug postkarte-a6-kampagne \
    --json-out /tmp/db2.json
diff /tmp/db1.json /tmp/db2.json  # empty diff

# (d) Wrapped invocation produces merged visual_diff.json
rm -rf build/validation/postkarte-a6-kampagne/
python3 tools/visual_diff.py templates/postkarte-a6-kampagne/template.sla \
    --baseline templates/postkarte-a6-kampagne/baseline.pdf \
    --tolerance templates/postkarte-a6-kampagne/diff.yml \
    --extract-bboxes --template-slug postkarte-a6-kampagne \
    --ci --out build/validation/postkarte-a6-kampagne/
python3 -c "import json; d=json.load(open('build/validation/postkarte-a6-kampagne/visual_diff.json')); assert all('bboxes' in p for p in d['pages']); print('wired OK')"

# (e) No new dependencies introduced
git diff main -- Dockerfile.claude requirements.txt 2>/dev/null  # empty
```

**ISSUE.md acceptance checklist (verify before closing):**
- [ ] `tools/diff_bbox_extract.py` exists with documented usage
- [ ] Standalone run produces `diff_bboxes.json` + optional overlays
- [ ] Slot attribution verified on `postkarte-a6-kampagne` (≥1 attributed bbox)
- [ ] Output deterministic (byte-equal on re-run)
- [ ] `visual_diff.py --extract-bboxes` merges JSON into `visual_diff.json`
- [ ] Tests cover: noisy-AA filtering, multi-cluster pages, unattributed bbox
