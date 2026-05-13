# Pitfalls Research — Issue 36 Visual-diff bbox extractor

**Researcher mandate:** every edge case in the pipeline `delta PNG → bbox JSON → slot attribution → overlay PNG → visual_diff.json merge` so the plan can mitigate them up front.

All findings below are grounded in: (a) actual delta PNGs produced by `tools/visual_diff.py` runs in `/root/workspace/build/validation/`, (b) synthetic deltas generated with the in-container ImageMagick 7.1.1, (c) reading `tools/visual_diff.py` + `tools/sla_lib/builder/bbox.py` + `tools/audit_alignment.py`, and (d) the container Dockerfile.claude package list. Confidence HIGH unless flagged otherwise.

---

## Critical Pitfalls (must-handle — breaks correctness if ignored)

### CP-1. Delta PNG is **RGBA, not grayscale**
- **What goes wrong.** The issue body says "Load `diff-page-NN.png` as grayscale" but the file ImageMagick 7 actually writes is `sRGB + alpha (4 channels, depth 8)`. Verified on real artefacts at `/root/workspace/build/validation/postkarte-a6-kampagne/diff-page-01.png` (mode `RGBA`, dominant colour `(210, 227, 215)` = baseline showing through at reduced opacity), and on a synthetic delta where the mismatched pixels come out as `(199, 23, 35, 255)` — the IM7 default `-highlight-color`, which is a saturated red. Matched pixels are NOT pure white either: they are the baseline image lightened with an alpha overlay, so the "match" luminance hovers around 220, not 255.
- **Why it matters.** Naïve `Image.open(path).convert("L")` then `pixel < 128` will misclassify the lightened-baseline pixels (luminance ~220) as match (good) but the threshold value needs to sit somewhere around 150–200, not 64 like a typical binary mask. Also, anyone who assumes "white = match, black = mismatch" (which is the standard IM6 + `-compose Src` behaviour in older docs) will produce a mask that is the inverse of what's intended.
- **Smallest mitigation.** Read as RGB (drop alpha — alpha=255 everywhere in tested artefacts), convert to grayscale via PIL `.convert("L")`, then threshold at a configurable value with default ≈ 200 (treat anything *darker than 200* as mismatch). Document the rationale in the docstring. Verify by re-running on `build/validation/postkarte-a6-kampagne/diff-page-01.png` (passing page → expect 0 bboxes after min-area filter).

### CP-2. cv2 / numpy / scipy / skimage are **not installed in the container**
- **What goes wrong.** Issue body references `cv2.threshold`, `cv2.findContours`, `cv2.boundingRect`. None of `cv2`, `numpy`, `scipy`, `skimage` is importable in the Dockerfile.claude container. Only `PIL` 12.2.0 is available. `Dockerfile.claude` lines 76–80 pin `pillow`, `qrcode[pil]`, `pyzbar`, `jsonschema` — no scientific Python stack.
- **Why it matters.** Plan must either (a) add `opencv-python-headless` + `numpy` to the Dockerfile and accept the ~80 MB install/rebuild, OR (b) avoid the dependency entirely. The repo's culture (single-binary CLI tools, minimal pip surface) favours (b).
- **Smallest mitigation.** Use ImageMagick's built-in `-connected-components 8` operator as the bbox backend. The 4th sub-section below documents this. ImageMagick 7.1.1 is already installed (verified `/usr/bin/compare` + `/usr/bin/convert`), supports `-define connected-components:verbose=true` to print bounding boxes in the form `widthxheight+x+y`, and ships `-morphology Dilate Square:N` for the cluster-merge step. No new Python deps required. This also keeps the tool consistent with `visual_diff.py`'s reliance on the ImageMagick stack (`compare`, `montage`, `convert`).

### CP-3. ImageMagick `connected-components` always emits a "background" object that must be discarded
- **What goes wrong.** Every invocation lists object id `0` covering the entire image (e.g. `0: 465x628+0+0 234.6,317.5 286979 graya(255,…)`) — that's the matched (white-ish) background, not a real cluster. If the extractor doesn't drop it, every page produces one giant page-sized bbox.
- **Smallest mitigation.** After parsing the verbose output, drop any object whose bounding box covers ≥95% of the page area (or whose mean-color is bright). Confirmed empirically: real mismatch objects come back as `graya(0, …)` (dark), background as `graya(255, …)` (light). Parse the `mean-color` column.

### CP-4. Page-edge / registration artefacts produce 1×N strips at the corners
- **What goes wrong.** Empirical test: a synthetic 3-cluster delta produced the 3 expected bboxes plus 8 spurious `1x11+34+0`, `1x11+431+0`, `11x1+0+34` etc. — thin strips along the page edge from pdftoppm + IM `compare` antialiasing at the page border. With `min-area=10` they survive; with `min-area=50` they are filtered.
- **Smallest mitigation.** Default `min-area` to **100 px²** (configurable). This kills the corner strips while still keeping a 10×10 mm slot drift visible at 96 dpi (10mm ≈ 38px → 1444 px²). Document the threshold explicitly in the docstring and in `diff.yml` schema docs. A noisy-AA test fixture should assert that a 1×11 corner strip is filtered out.

### CP-5. Threshold + dilate ordering controls under-merge vs over-merge — picking wrong defaults is irreversible
- **What goes wrong.**
  - **Too aggressive dilate** (e.g. Square:10): two physically distinct slots that both drifted into the gutter between them merge into a single mega-bbox. Slot attribution then matches *both* slots with low IoU and either picks the wrong one or reports `null`.
  - **Too conservative dilate** (e.g. Square:1 or none): a single drifted slot whose drift is patchy (e.g. text frame where 3 of 5 lines moved) yields 3 small bboxes attributed to the same slot, with mismatch_pct_in_bbox computed against tiny crops. Human review sees 3 red rectangles where there should be 1.
- **Smallest mitigation.** Default `dilate-kernel` to **Square:3** (3-pixel structuring element). At 96 dpi that is ~0.8mm — enough to merge font-stroke gaps within a glyph but not so big it bridges adjacent slots whose typical gap is ≥5mm. Make it overridable per template via `diff.yml` (`visual_diff.bbox.dilate_px: 3`, `visual_diff.bbox.min_area_px: 100`, `visual_diff.bbox.threshold: 200`). Validate empirically on the first template that exhibits drift (issue #35 / Cover 2 case).

### CP-6. `frame_bbox_mm` ignores `xpos_pt` / `width_pt` verbatim-pt overrides — attribution will be wrong on templates that use them
- **What goes wrong.** `tools/sla_lib/builder/bbox.py` lines 16, 56–60 explicitly document the limitation: when a frame uses `xpos_pt`/`width_pt` (pt-precision verbatim values) instead of `x_mm`/`w_mm`, the helper falls back to the mm value, which can be off by sub-mm. The bbox extractor inherits this. For most templates this is irrelevant (the two known offenders — zeitung P9 spread, unnamed page-12 image — both use `*_mm`), but issue #35's IDML→DSL converter will likely emit verbatim-pt frames for everything to preserve InDesign precision.
- **Why it matters.** A drift bbox sitting on top of a `xpos_pt`-positioned slot may report `attribution_overlap_pct: 65%` instead of 95%, fall below the attribution threshold, and emit `attributed_slot: null`. The slot is then reported as un-attributed even though it visually overlaps.
- **Smallest mitigation.** Document the limitation in the new tool's docstring (mirror bbox.py's wording). Accept it for v1. Add a follow-up issue (not this one) to widen `frame_bbox_mm` to honour pt overrides. As a defensive measure in v1: when attribution IoU is in the 50–80% band (suspicious zone), include the top-3 candidate slots in the JSON output (`"attribution_candidates": [{slot, iou}, …]`) so the human reviewer can disambiguate.

### CP-7. Page numbering convention is split between filenames and JSON — wiring mistakes guaranteed
- **What goes wrong.** Three numbering conventions coexist:
  1. `visual_diff.py` writes `diff-page-{NN}.png` 1-indexed, **always** zero-padded to 2 digits via Python f-string `:02d` (line 231).
  2. `visual_diff.json`'s `page_index` is 0-indexed (line 266 + 293).
  3. `pdftoppm` produces `baseline-page-{N}.png` 1-indexed with **variable padding** — 1 digit for ≤9-page docs (verified: `postkarte` has `baseline-page-1.png`), 2 digits for 10+-page docs (verified: `zeitung` has `baseline-page-09.png`).
- **Why it matters.** Reading "delta for page 0" from `visual_diff.json` requires `idx + 1` then `:02d` to find the file. Reading "the underlying dsl raster for page 0" requires `idx + 1` and matching the variable-padded glob. Hardcoding either pattern leads to FileNotFoundError on edge templates.
- **Smallest mitigation.** Use the `delta_png` field that's already in `visual_diff.json` (line 273: `delta_png=str(diff_png.relative_to(out_dir))`) instead of re-deriving the filename. For the dsl-page underlay (overlay PNG), glob for `dsl-page-{idx+1}.png` and `dsl-page-{idx+1:02d}.png`, pick whichever exists. The JSON output uses `page` to mean **0-indexed page_index** to match the existing convention.

### CP-8. visual_diff.json merge must NOT rename existing fields
- **What goes wrong.** `tools/visual_diff.py` `write_reports()` (lines 281–308) currently emits a stable schema consumed by `visual_diff.html` and by anything downstream that reads the JSON (`per_page[i].mismatch_pixels`, `.mismatch_pct`, `.threshold_pct`, `.fuzz_pct`, `.composite`, `.delta_png`, `.pass`, `.regions`). Issue body line 92: "the JSON merges cleanly into visual_diff.json".
- **Why it matters.** Renaming `regions` → `bboxes`, or top-leveling the bbox list, breaks the HTML report writer and any external consumer.
- **Smallest mitigation.** Add ONE new field per page: `"bboxes": [ {bbox_mm, bbox_px, mismatch_px, mismatch_pct_in_bbox, attributed_slot, attribution_overlap_pct, attribution_candidates?} ]`. Leave every existing field byte-identical when `--extract-bboxes` is off. Add a unit test that round-trips a `visual_diff.json` with bbox extraction disabled and asserts schema equality against a frozen fixture.

### CP-9. Deterministic output requires explicit ordering at three points
- **What goes wrong.** ImageMagick `-connected-components` emits objects in a sort order controlled by `-define connected-components:sort=area` (default: decreasing area). Python `dict.items()` is insertion-ordered (≥3.7). But (a) two clusters with **identical area** can swap order between IM versions / runs; (b) `glob()` is filesystem-ordered (not always lexical); (c) float→str conversions of mm values are platform-dependent at the last digit.
- **Why it matters.** Acceptance criterion: "same input → same JSON (deterministic ordering, no timestamps)". Tests will flake without explicit handling.
- **Smallest mitigation.**
  - Sort bbox records lexically by `(page, bbox_px.y, bbox_px.x, bbox_px.w, bbox_px.h)` after parsing the IM verbose output — pixel coords are integers, no FP drift.
  - Round mm values to **0.1 mm** in the JSON (1 decimal place) — well below the 25.4/96 ≈ 0.265 mm raster precision at 96 dpi, so this is information-preserving.
  - Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for serialisation (matches `visual_diff.py`'s existing pattern at line 308 minus `sort_keys`, which we add).
  - File enumeration: derive from `visual_diff.json["pages"][i]["delta_png"]` (deterministic order), not from `glob.glob("diff-page-*.png")`.

---

## Likely Pitfalls (may-break — design-decision territory)

### LP-1. Stacked slots with overlapping bboxes pick the wrong attribution
- **What goes wrong.** A typical page (e.g. zeitung P1) has a large background Polygon ("Hellgrün band") with a Text frame and an ImageFrame layered on top, all returning a bbox from `frame_bbox_mm`. A drift bbox covering the headline text overlaps **both** the text frame (small, ~95% IoU) and the band polygon (large, ~15% IoU). Naive "max IoU" picks text frame (correct). But if the drift is large enough to extend past the text frame into the band, IoU for the text drops below the band's — and we'd attribute the drift to the band polygon, which is wrong (the visible problem is the text, the band is just the canvas behind it).
- **Why it matters.** "P1 Hellgrün-Band shifted 4mm" is technically true but unhelpful — humans want "P1 Headline shifted 4mm".
- **Smallest mitigation.** Two-step attribution:
  1. Filter candidate slots to those where `IoU(bbox, slot) ≥ attribution_threshold` (default 0.5).
  2. Among candidates, pick the one with **smallest slot area** (rationale: smaller slot = more specific attribution; the background band is always bigger than the foreground content).
  3. Also emit `attribution_candidates: [{slot, iou, slot_area_mm2}, …]` so the reviewer can override.
  - Document this heuristic in the docstring; it's the kind of thing that will need to be revisited based on early outputs.

### LP-2. Unnamed primitives in `iter_all_primitives()` shouldn't break attribution
- **What goes wrong.** `audit_alignment.py` lines 248–250 already handles this: `if not an: continue`. But the bbox extractor uses ALL placed frames as attribution candidates, not just `anname'd` ones. Some templates have anonymous frames (e.g. master-page decorative shapes). They have valid bboxes but no human-readable name.
- **Why it matters.** Attribution emits `attributed_slot: ""` (empty string) or crashes on `None.lower()`, depending on implementation.
- **Smallest mitigation.** Mirror `audit_alignment._audit_doc` lines 247–254 exactly: skip frames where `getattr(item, "anname", "")` is empty. For anonymous frames in the candidate set, synthesise a fallback name `f"<unnamed p{page_idx+1} x={x_mm:.0f} y={y_mm:.0f}>"` matching the existing convention in `_BandConsistencyRule` (audit_alignment.py line 359-363). This keeps the JSON valid and lets reviewers locate the frame.

### LP-3. Rotated slots match the axis-aligned bbox, not the slot's true polygon
- **What goes wrong.** `frame_bbox_mm` returns the AABB of a rotated rectangle. For a 45°-rotated slot, the AABB is up to 1.414× larger than the true slot. A drift bbox inside the slot's bounding rectangle but outside its rotated polygon would IoU-match, but visually the drift is in empty page space next to the slot.
- **Why it matters.** False-positive attributions on rotated slots. The known case is the plakat-a1-hochformat Impressum frame at ROT=270 (bbox.py line 9). At 90°/270° rotations the AABB equals the rotated polygon (no error). At arbitrary angles, error grows.
- **Smallest mitigation.** Accept the AABB approximation for v1 — the prompt explicitly says "Rotated slots: `frame_bbox_mm` returns the axis-aligned rotated bbox — that's correct for our IoU math." Flag in the docstring that arbitrary-angle slots may produce loose attribution. Add a note in the output JSON when the matched slot has `rotation_deg != 0`: `"slot_rotation_deg": 270` so reviewers can mentally adjust.

### LP-4. `fuzz_pct` is already baked into the delta — the extractor's threshold operates on top of that
- **What goes wrong.** Reading the issue body and the prompt suggests the extractor needs to know the `fuzz_pct` to set its threshold accordingly. But `compare -fuzz X%` already saturates within-tolerance pixels to the "match" highlight (lightened baseline in IM7). By the time we open `diff-page-NN.png`, fuzz is already applied — the only pixels still showing mismatch colour are those exceeding the fuzz envelope.
- **Why it matters.** Trying to "subtract" fuzz_pct from the threshold is double-counting. Worse, reading per-page fuzz from `visual_diff.json` and adjusting threshold per page introduces template-specific tuning surface where none is needed.
- **Smallest mitigation.** The extractor's threshold is FIXED (default 200 / configurable), independent of fuzz_pct. Document this clearly. Per-template overrides go via `diff.yml` `visual_diff.bbox.threshold` if a template legitimately needs different sensitivity — but expect to never need it.

### LP-5. Red-overlay PNG underlay choice: dsl render vs baseline render vs delta
- **What goes wrong.** The issue body says "red-tinted bbox overlay on the dsl rendering". But which raster? `dsl-page-{NN}.png` (the produced output) is the natural choice ("where did we drift TO"); `baseline-page-{NN}.png` would show "where it should have been". Drawing on the delta itself is unhelpful — it's already a delta.
- **Why it matters.** Choosing the wrong underlay confuses reviewers. Drawing on the dsl render shows "your output has drift HERE"; drawing on baseline shows "baseline has features HERE that your output diverges from" — subtly different mental models.
- **Smallest mitigation.** Underlay = `dsl-page-{NN}.png` (the DSL output). This matches the workflow: "look at what the pipeline produced and see where it differs from the source of truth". Document the choice. Output filename `diff-page-{NN}-overlay.png` (per issue body) sits alongside `composite-page-{NN}.png` — does NOT replace it (issue body line 102: "Replacing visual_diff.py's composite/montage outputs — those stay").

### LP-6. Overlay drawing on a colour-managed PNG can shift colours
- **What goes wrong.** Pillow's `ImageDraw.rectangle(..., outline=(255,0,0), width=3)` draws sRGB red. If the underlay PNG has an embedded ICC profile (pdftoppm output may), saving the output without preserving the profile can shift the underlay's colours slightly, even though only the rectangle pixels changed.
- **Why it matters.** Cosmetic — but for byte-deterministic output (acceptance criterion: "same input → same JSON, no timestamps"), the PNG bytes must also be reproducible.
- **Smallest mitigation.** Read with `Image.open(...).convert("RGB")` (drops profile), draw, save as PNG with `optimize=False` and explicit `pnginfo=None` to avoid metadata that depends on time. Verify byte-identical output across two runs in a test.

### LP-7. Multi-bbox-per-slot is not idempotent under `--extract-bboxes` re-runs
- **What goes wrong.** If the extractor is run twice — once standalone, once via `visual_diff.py --extract-bboxes` — and the second run writes `bboxes` into `visual_diff.json` while the first wrote `diff_bboxes.json` (standalone artefact), the two files can drift if defaults change between runs. The truth source is unclear.
- **Smallest mitigation.** Always write `diff_bboxes.json` as the canonical bbox artefact. When `visual_diff.py --extract-bboxes` is set, the wiring code in `visual_diff.py` runs `diff_bbox_extract.extract(...)` synchronously, captures the in-memory bbox list, AND folds it into `visual_diff.json` at write time. Don't re-read `diff_bboxes.json` to merge — that creates the dual-truth bug.

### LP-8. `iter_all_primitives()` walks masters too — masters share with all pages
- **What goes wrong.** A frame on a master page (e.g. page-number block, decorative border) is "present" on every page that inherits the master. If the extractor enumerates frames via `doc.iter_all_primitives()` without filtering by `own_page`, it'll attribute drift on page 5 to a master-page slot, with the slot bbox sitting on the master (own_page=0 or marked `is_master=True`).
- **Smallest mitigation.** Filter slot candidates per-page: only consider items where `item` is on `doc.pages[page_idx]` (i.e. `page.is_master is False` and `item in page.items`). Mirror `audit_alignment.py` lines 240–254 pattern.

---

## Out-of-Scope (explicit, with rationale)

The following are NOT this issue. The plan should not include tasks for them; if research surfaces them, mention as follow-ups only.

| Item | Why out of scope |
|---|---|
| Auto-generating `diff.yml` `per_region:` blocks from bbox output | Issue body line 98-99: explicit follow-up; depends on attribution accuracy proving out empirically first. |
| Vision-model invocation on cropped bboxes (the consumer `visual_review.py`) | Issue body line 100-101: "this issue produces the data; the consumer is a follow-up". |
| Replacing `visual_diff.py`'s composite/montage outputs | Issue body line 102: "those stay". The overlay PNG sits *alongside*, not instead of, the existing composite-page-NN.png. |
| Re-implementing the diff pixel arithmetic | Issue body line 103: "we operate on existing `diff-page-NN.png` only". The extractor reads what `compare` already produced. |
| Widening `frame_bbox_mm` to honour `xpos_pt`/`width_pt` overrides | Pre-existing limitation in bbox.py (line 13-16). Issue #36 inherits it. Track separately if attribution accuracy on issue #35-converted templates proves insufficient. |
| Per-region `diff.yml` tolerance schema changes | The `visual_diff.bbox.{threshold,min_area_px,dilate_px}` config keys are NEW but additive — no schema migration. Don't touch the existing `per_region` schema. |

---

## Environment Audit

| Dependency | Required by | Available in container? | Version | Fallback / mitigation |
|---|---|---|---|---|
| `python3` | tool entrypoint | YES | 3.13.5 | n/a |
| `PIL` (Pillow) | reading delta PNG, drawing red overlay, byte-deterministic save | YES | 12.2.0 (pinned in Dockerfile.claude L79) | n/a |
| `compare` (ImageMagick) | already produces the delta we consume — not invoked by extractor | YES | 7.1.1-43 | n/a |
| `convert` (ImageMagick) | bbox extraction via `-connected-components 8 -define connected-components:verbose=true` and `-morphology Dilate` | YES | 7.1.1-43 | n/a |
| `numpy` | NOT NEEDED if we use IM `-connected-components` path | NO | n/a | Avoid the dep; use IM operator. |
| `cv2` (opencv-python) | issue body suggests this but it's not strictly needed | NO | n/a | Avoid the dep; use IM operator. |
| `scipy.ndimage` (label / find_objects) | alternative pure-Python bbox-from-mask | NO | n/a | Avoid the dep; use IM operator. |
| `skimage.measure.regionprops` | alternative | NO | n/a | Avoid the dep. |
| `yaml` (PyYAML) | reading `diff.yml` config | YES (via `python3-yaml`, Dockerfile.claude L51) | system | n/a |
| `xvfb-run + scribus` | needed by audit_alignment / build_doc-load path when bbox extractor wants slot bboxes from rebuilding the doc | YES (via Dockerfile.claude L43-62) | Scribus 1.6.x | NB: the slot enumeration path does NOT need Scribus — it imports the build.py module via `load_build_module` and calls `build_doc()` in-process. No Scribus invocation needed for `tools/diff_bbox_extract.py` itself. Only `visual_diff.py`'s render step needs Scribus, and that's pre-existing. |

**CI estimate.** The bbox extractor processes N delta PNGs per template, each ≤ ~1MB. `convert ... -connected-components` on a 465×628 RGBA PNG: <100ms on the test machine. For 14-page Zeitung: <2s wall clock. Adds <5s per template to the existing visual_diff CI gate (which is already minutes due to Scribus rendering). Negligible.

**Coordination with ecosystem fork.** The ecosystem sub-agent is investigating "should we add cv2 / opencv-python-headless to the container?". Recommendation from this fork: NO — use ImageMagick's built-in connected-components instead. The capability is there, the binary is installed, no rebuild required. If the ecosystem fork concludes otherwise (e.g. cv2 has features we genuinely need beyond bbox extraction), revisit.

---

## Sources

### HIGH confidence (direct file inspection / in-container probe)
- `/root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution/tools/visual_diff.py` lines 153–276 — the existing pipeline this extractor wires into; confirmed AE metric, fuzz-pct usage, JSON schema fields, page-index conventions.
- `/root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution/tools/sla_lib/builder/bbox.py` lines 16, 56–60 — verbatim `xpos_pt`/`width_pt` limitation already documented.
- `/root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution/tools/audit_alignment.py` lines 240–254 — canonical pattern for per-page slot enumeration with anname filtering.
- `/root/workspace/build/validation/postkarte-a6-kampagne/diff-page-01.png` — real delta PNG, confirmed RGBA / sRGB / lightened-baseline + alpha behaviour via `identify -format` and PIL inspection.
- In-container `convert -size 50x50 ... compare -metric AE -fuzz 25% ... delta.png` synthesis — confirmed mismatched pixels render as `(199, 23, 35, 255)` (IM7 default red highlight); confirmed grayscale conversion produces luminance ≈77 for mismatch vs ≈221 for matched-baseline.
- `convert delta.png -colorspace Gray -threshold 80% -define connected-components:verbose=true -connected-components 8` — verified output format (`id: WxH+x+y centroid area mean-color`), background-object behaviour (id 0 = page-sized graya(255,…)), corner-strip false positives (8 strips at 1×11 / 11×1 in synthetic test).
- `/root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution/Dockerfile.claude` lines 76–80 — package pinning shows no numpy/cv2/scipy/skimage; only Pillow + qrcode + pyzbar + jsonschema.
- Container probe: `python3 -c "import cv2"` → ModuleNotFoundError; `compare --version` → ImageMagick 7.1.1-43; `python3 --version` → 3.13.5.
- Page-padding observation: `build/validation/postkarte-a6-kampagne/baseline-page-1.png` (1-digit) vs `build/validation/zeitung-a4-grun/baseline-page-09.png` (2-digit) — confirms pdftoppm variable-width padding.

### MEDIUM confidence (official docs, recent)
- [ImageMagick Connected Components Labeling docs](https://imagemagick.org/script/connected-components.php) — confirms `-define connected-components:area-threshold=N`, `-define connected-components:verbose=true`, output format, `mean-color`, `sort` parameter.
- [ImageMagick discussion #5163](https://github.com/ImageMagick/ImageMagick/discussions/5163) — usage patterns for connected-components verbose output parsing.
- [Pillow 12.2 Image module docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) — confirms `mode='RGBA'` semantics, `convert('L')` luminance formula `L = R*299/1000 + G*587/1000 + B*114/1000`.

### LOW confidence (single source, not directly verified for our case)
- ImageMagick output ordering across versions: no authoritative statement that `-connected-components` ordering is byte-stable across IM minor versions. Mitigated by re-sorting in our parser (CP-9 above) — we don't rely on IM's order.

