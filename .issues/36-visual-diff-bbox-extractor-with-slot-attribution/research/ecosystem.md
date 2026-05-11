# Ecosystem Research — Issue 36 (visual-diff bbox extractor)

**Researched:** 2026-05-11
**Confidence:** HIGH

## TL;DR

- **Container has only Pillow 12.2.0.** No `cv2`, no `numpy`, no `skimage` installed. Confirmed via `python3 -c "import …"` and `pip3 list`.
- **Recommend `opencv-python-headless==4.13.0.92` + `numpy>=2`** added to `Dockerfile.claude` next to the existing `pip3 install` block.
- Adds ~51 MB to image (35 MB opencv wheel + 15.7 MB numpy). scikit-image alternative is ~65 MB and pulls scipy — heavier with no benefit for this use case.
- Algorithm is canonical OpenCV: `threshold → getStructuringElement → dilate → findContours(RETR_EXTERNAL) → boundingRect → filter by area`.
- IoU math is 5 lines, hand-write inline. Do NOT pull a second lib for that.
- Red overlay PNG: use Pillow `ImageDraw.rectangle(outline=(255,0,0), width=2)` — Pillow already in stack, no extra dep.

## Recommended Stack

| Library | Version | License | Role | Confidence | Source |
|---|---|---|---|---|---|
| `opencv-python-headless` | `4.13.0.92` | Apache-2.0 | threshold, dilate, findContours, boundingRect | HIGH | PyPI, released 2026-02-05 |
| `numpy` | `>=2,<3` (transitive, resolves to 2.4.4) | BSD-3 | array backend for cv2 | HIGH | PyPI; pulled by opencv |
| `Pillow` | `12.2.0` (already pinned) | HPND | red bbox overlay drawing, PNG IO | HIGH | already in Dockerfile.claude |

**Why opencv-python-headless and not opencv-python:** project runs in CI / headless containers, never calls `cv2.imshow()`. Headless variant drops Qt + X11 dependencies → smaller image, fewer apt installs needed. PyPI page (Feb 2026) and the project's [issue tracker](https://github.com/opencv/opencv-python/issues/467) both explicitly recommend headless for Docker/server use.

**Why not scikit-image:** It would work (`skimage.measure.label` + `regionprops` does the same job), but its install footprint is ~65 MB (skimage 13 MB + scipy 33 MB + numpy 16 MB + imageio/tifffile/networkx) vs ~51 MB for opencv+numpy. OpenCV's `findContours` is also the more idiomatic / better-documented choice for this exact algorithm.

**Why not pure Pillow + numpy:** would need to hand-roll connected-component labelling. That's the textbook "don't hand-roll" case — even a naive flood-fill implementation is ~50 lines, slower, and likely buggy on edge cases. Not worth it to save 35 MB.

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Verdict |
|---|---|---|---|
| `opencv-python-headless` | `scikit-image` | +30% install size, drags scipy | rejected |
| `opencv-python-headless` | Pillow + numpy + custom CC labelling | hand-roll a well-solved algorithm | rejected |
| `opencv-python-headless` | `opencv-python` (non-headless) | pulls Qt + X11 libs, larger image | rejected (we are headless) |

## Algorithm Cheat Sheet (paste into PLAN)

```python
import cv2
import numpy as np
from PIL import Image, ImageDraw

# ---------- Step 1: load diff PNG as grayscale ----------
# diff-page-NN.png from ImageMagick `compare -fuzz`:
#   white (255) = pixels matched within fuzz tolerance
#   dark        = mismatched pixels (darker = bigger delta)
img = cv2.imread(str(diff_png_path), cv2.IMREAD_GRAYSCALE)  # uint8, shape=(H,W)

# ---------- Step 2: invert + threshold above fuzz noise floor ----------
# Invert so mismatches become bright (255), matches become 0.
# Threshold value: dark pixels in the original = small numbers, so after
# inversion they become large. fuzz_pct=25 means matches are within ~25% L*,
# so the noise floor sits roughly at gray ~200 (post-invert ~55). Use
# threshold=50 as a conservative default; expose as --threshold flag.
inverted = cv2.bitwise_not(img)
_, mask = cv2.threshold(inverted, 50, 255, cv2.THRESH_BINARY)
# mask: uint8 binary image, 255 where there's a real diff, 0 elsewhere

# ---------- Step 3: morphological dilate to merge near-pixel clusters ----------
# 5x5 ellipse is OpenCV's canonical "merge nearby specks" kernel (per
# docs.opencv.org/4.x morphology tutorial). For 96–300 DPI page renders,
# 5x5 collapses character-level AA noise into glyph-cluster blobs. Bump
# to 7x7 or 9x9 for higher DPI if clusters fragment. Expose as flag.
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
dilated = cv2.dilate(mask, kernel, iterations=1)

# ---------- Step 4: find external contours ----------
# RETR_EXTERNAL = top-level contours only (no nested holes). We want one
# bbox per visible drift region, not a bbox per inner hole.
# CHAIN_APPROX_SIMPLE compresses straight runs — fine, we only need bbox.
contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# ---------- Step 5: bounding rect + filter by min area ----------
# At 96 DPI, 1 mm² ≈ 14 px². Drop anything smaller than ~50 px² (≈ 3.5 mm²)
# to kill residual AA islands. Expose --min-area-px.
MIN_AREA_PX = 50
raw_bboxes = []
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if w * h < MIN_AREA_PX:
        continue
    # mismatch_px = count of nonzero pixels inside this bbox in the ORIGINAL
    # (post-threshold, pre-dilate) mask — dilation expanded the cluster so
    # use `mask`, not `dilated`, for the real mismatch pixel count.
    crop = mask[y:y+h, x:x+w]
    mismatch_px = int(np.count_nonzero(crop))
    raw_bboxes.append({
        "x": x, "y": y, "w": w, "h": h,
        "mismatch_px": mismatch_px,
        "mismatch_pct_in_bbox": round(100.0 * mismatch_px / (w * h), 2),
    })

# ---------- Step 6: px → mm via DPI ----------
# DPI is in visual_diff.json (e.g. 96 for --ci, 300 for print-quality).
PX_TO_MM = 25.4 / dpi
def px_to_mm(v): return round(v * PX_TO_MM, 2)

# ---------- Step 7: slot attribution via IoU ----------
# Slot bboxes come from tools/sla_lib/builder/bbox.frame_bbox_mm() in mm.
# Convert slot mm → px to compare in same coordinate space, OR convert
# diff px → mm and compare in mm. Prefer mm (matches DSL semantics).
def iou(a, b):
    """a, b are dicts with x, y, w, h (same units)."""
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"]+a["w"], a["y"]+a["h"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2-ix1), max(0, iy2-iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = a["w"]*a["h"] + b["w"]*b["h"] - inter
    return inter / union

def coverage_of_a_inside_b(a, b):
    """How much of bbox a falls inside b. Use for 'tiny diff inside big slot' case."""
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"]+a["w"], a["y"]+a["h"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]
    iw = max(0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0, min(ay2, by2) - max(ay1, by1))
    a_area = a["w"] * a["h"]
    return 0.0 if a_area == 0 else (iw * ih) / a_area

# Attribution rule (HIGH confidence: this is the textbook approach):
#   For each diff_bbox, score against every slot_bbox using BOTH:
#     - IoU (handles "diff and slot are roughly the same size")
#     - coverage_of_diff_in_slot (handles "tiny diff inside big slot")
#   Pick the slot with the highest coverage_of_diff_in_slot; if that
#   value is ≥ 0.5, attribute. Report IoU as a secondary diagnostic.
#   Threshold of 0.5 (50% of diff bbox lies inside slot) is a sane default
#   for "this drift is clearly inside this slot." Expose as flag.
```

### Why coverage, not pure IoU, for attribution

A 5 mm² portrait shift inside a 50 mm × 70 mm portrait slot:
- intersection = 5 mm² (the whole diff)
- union = 5 + 3500 − 5 = 3500 mm²
- **IoU = 0.0014** → looks like no match!
- **coverage_of_diff_in_slot = 5 / 5 = 1.0** → correctly attributes

For drift bboxes that span multiple slots, pick the slot with highest coverage. For drift bboxes that span outside any slot, coverage of best slot < 0.5 → leave as `attributed_slot: null`. This is the case the acceptance criteria call "unattributed bbox (no slot overlap above threshold)".

### Stable ordering

```python
# Sort by (page, y, x) for deterministic JSON output across runs:
bboxes.sort(key=lambda b: (b["page"], b["bbox_px"]["y"], b["bbox_px"]["x"]))
# JSON dump with sort_keys + indent for stable text diff:
json.dumps(out, sort_keys=True, indent=2)
```

## Determinism Notes

- `cv2.threshold` — deterministic (pure pixel-wise integer compare). HIGH.
- `cv2.dilate` with a fixed kernel — deterministic (integer convolution). HIGH.
- `cv2.findContours` — deterministic given **identical input image bytes**. The 2019 GitHub issue [opencv#15404](https://github.com/opencv/opencv/issues/15404) ("returns different results on same image") was closed as `invalid tracker / question` — reporter's "same image" wasn't byte-identical (loaded with different flags). On byte-identical input, output contour list is identical run-to-run on the same OpenCV build. HIGH.
- `cv2.boundingRect` — deterministic (extremum scan over contour points). HIGH.
- **Caveat:** OpenCV major-version upgrade *could* change the contour traversal order. Pin the version (`opencv-python-headless==4.13.0.92`) so test snapshots stay stable. Re-snapshot on intentional upgrades.
- **Sort the final bbox list** by `(page, y, x)` regardless — defensive against any future ordering change in the lib.

## Install Footprint

| Item | Size | Notes |
|---|---|---|
| `opencv-python-headless==4.13.0.92` wheel (arm64) | 35.0 MB | confirmed via `pip3 install --dry-run` |
| `numpy==2.4.4` wheel (arm64) | 15.7 MB | confirmed; transitive dep of cv2 |
| **Total added to image** | **~51 MB** | one new layer in `Dockerfile.claude` |
| System libs needed | none beyond glibc | headless wheel statically links FFmpeg etc.; **no apt-get additions required** |

### Dockerfile change (single block, append to existing pip install)

```dockerfile
RUN pip3 install --break-system-packages --no-cache-dir \
        'qrcode[pil]==8.2' \
        'pyzbar==0.1.9' \
        'pillow==12.2.0' \
        'jsonschema==4.26.0' \
        'opencv-python-headless==4.13.0.92' \
        'numpy==2.4.4'
```

(Or split into a second `RUN pip3 install ...` — preserves layer cache for unrelated rebuilds. Planner's call.)

### Don't-hand-roll

| Problem | Don't build | Use instead |
|---|---|---|
| Connected-component / contour labelling | custom flood-fill | `cv2.findContours` |
| Morphological dilation | manual kernel convolution | `cv2.dilate` + `cv2.getStructuringElement` |
| Binary thresholding | `np.where(arr > t, 255, 0)` (works but slower) | `cv2.threshold` |
| Image load/save | none — Pillow already fine | `cv2.imread`/`cv2.imwrite` OR `PIL.Image.open` (either OK) |

### Do hand-roll (5 lines each, no extra lib)

| Problem | Why hand-roll |
|---|---|
| IoU | trivial integer arithmetic; pulling a lib for this is silly |
| Coverage-of-A-in-B | same, and it's the *better* metric for slot attribution |
| px↔mm conversion | one multiplication |
| Stable JSON sort + dump | stdlib `json.dumps(sort_keys=True, indent=2)` |

## Red-overlay PNG generation

Use Pillow (already in stack — no second image lib needed):

```python
from PIL import Image, ImageDraw
base = Image.open(dsl_render_png).convert("RGB")
draw = ImageDraw.Draw(base, "RGBA")
for b in bboxes:
    x, y, w, h = b["bbox_px"]["x"], b["bbox_px"]["y"], b["bbox_px"]["w"], b["bbox_px"]["h"]
    draw.rectangle([x, y, x+w, y+h], outline=(255, 0, 0, 255), width=2)
    # Optional fill tint:
    draw.rectangle([x, y, x+w, y+h], fill=(255, 0, 0, 40))
base.save(out_dir / f"diff-page-{n:02d}-overlay.png")
```

(Could equally use `cv2.rectangle` on a numpy array — works fine, no preference. Pillow keeps it consistent with `tools/qr_gen.py` and the rest of the codebase.)

## Sources

### HIGH confidence

- [PyPI: opencv-python-headless 4.13.0.92](https://pypi.org/project/opencv-python-headless/) — version, license, headless rationale, release date 2026-02-05
- [OpenCV imgproc shape docs (4.x)](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html) — `findContours` returns `(contours, hierarchy)`, `RETR_EXTERNAL` for top-level only, `boundingRect` returns `(x,y,w,h)`
- [OpenCV morphology tutorial (4.x)](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html) — `getStructuringElement(MORPH_ELLIPSE, (5,5))` is the canonical "merge nearby pixels" kernel
- [opencv-python issue #467](https://github.com/opencv/opencv-python/issues/467) — never mix `opencv-python` and `opencv-python-headless` (same `cv2` namespace)
- Container probe: `pip3 list` confirms Pillow 12.2.0 only; numpy/cv2/skimage absent
- Container probe: `pip3 install --dry-run` confirms exact wheel sizes and transitive deps

### MEDIUM confidence

- [opencv#15404](https://github.com/opencv/opencv/issues/15404) closed as `invalid tracker/question` — reasonable inference that `findContours` is deterministic on byte-identical input, but OpenCV does not publish a formal determinism guarantee. Mitigated by pinning the version and sorting final output.
- [PyImageSearch IoU tutorial](https://pyimagesearch.com/2016/11/07/intersection-over-union-iou-for-object-detection/) — standard IoU formula reference, widely cited

### LOW confidence (defaults to validate empirically)

- `threshold=50` post-invert — guess based on `fuzz_pct=25` default. Acceptance test should iterate on a real diff-page-NN.png to confirm.
- `MIN_AREA_PX=50` for AA-noise filter — at 96 DPI this is ~3.5 mm², feels reasonable but no authoritative source. Expose as flag; tune on real templates.
- `coverage_threshold=0.5` for slot attribution — chosen for clear semantics ("half the drift is inside this slot"). Expose as flag; the test with "shifted P1 portrait" will validate.
- `dilate kernel=5×5 ellipse` — OpenCV's tutorial uses 5×5 examples but doesn't claim optimality. Document and expose as `--dilate-kernel-px`.

## Open Questions for Planner

1. **DPI source:** the existing `visual_diff.json` includes DPI per the issue description ("read DPI from `visual_diff.json`") — planner should confirm by reading current `visual_diff.py` output schema. If DPI isn't in there, it must be added (small change to `visual_diff.py`) or passed via CLI flag.
2. **Slot bbox unit:** `frame_bbox_mm()` returns mm (per its name). Attribution should run in mm-space (convert diff bboxes once with `25.4/dpi`, do all IoU in mm). Confirm in codebase research.
3. **Pin numpy explicitly?** opencv pulls `numpy>=2`. Project hasn't pinned numpy before. Recommend pinning `numpy==2.4.4` for byte-deterministic output (same rationale as the Pillow 12.2.0 pin in the existing Dockerfile comment for issue #13).
