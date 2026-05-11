---
id: '36'
title: Visual-diff bbox extractor with slot attribution
status: open
priority: medium
labels:
- visual-qa
- templates
- dsl
source: github
source_id: 73
source_url: https://github.com/GrueneAT/vorlagen/issues/73
---

## Context

The existing `tools/visual_diff.py` already renders a per-page delta PNG via
ImageMagick `compare -fuzz` (white = match, dark = mismatch) and supports
`per_region` tolerance overrides in `diff.yml`. What it doesn't do is
extract bounding boxes from the delta image — that step is still manual:
a human stares at composite-page-NN.png and reports where the drift is.

This issue adds a lightweight bbox-extraction post-processor that
operates on the artifacts `visual_diff.py` already produces, so we get:

- **Cheaper review** — a small JSON / red-overlay we can hand to a vision
  model with the bboxes pre-cropped, instead of asking it to compare two
  full pages pixel-by-pixel
- **Auto-attribution** — each bbox is cross-referenced against the
  template's known slot bboxes (from `meta.yml` + `sla_lib.builder.bbox`)
  so drift can be reported as "P1 Kandidat-Portrait shifted 2.3mm right"
  instead of "page 0 has ~1.4% mismatch"
- **diff.yml seed data** — the JSON output can be turned into a draft
  `per_region:` block for tolerance, closing the loop

## Scope

**New tool: `tools/diff_bbox_extract.py`**

Reads `visual_diff.py`'s existing output dir (the `diff-page-NN.png` files)
and emits:

1. **`diff_bboxes.json`** — list of bbox records:
   ```json
   [
     {
       "page": 0,
       "bbox_mm":  {"x": 12.3, "y": 45.6, "w": 38.0, "h": 28.0},
       "bbox_px":  {"x": 49,   "y": 182,  "w": 152,  "h": 112},
       "mismatch_px": 1842,
       "mismatch_pct_in_bbox": 8.3,
       "attributed_slot": "P1 Kandidat-Portrait",
       "attribution_overlap_pct": 92.0
     },
     ...
   ]
   ```

2. **`diff-page-NN-overlay.png`** (optional) — red-tinted bbox overlay on
   the dsl rendering, for human review.

**Pipeline:**

1. Load `diff-page-NN.png` as grayscale
2. `cv2.threshold` above fuzz noise floor (configurable)
3. Morphological dilate to merge near-pixel clusters into regions
4. `cv2.findContours` + `cv2.boundingRect` → list of bboxes
5. Filter by min area (drop AA noise)
6. Convert px → mm via `25.4 / dpi` (read DPI from `visual_diff.json`)
7. **Slot attribution**: for each bbox, find the template-defined slot
   bbox with the highest IoU; if overlap ≥ threshold, attribute. Slot
   bboxes come from rebuilding the DSL document and calling
   `sla_lib.builder.bbox.frame_bbox_mm()` per anname'd frame (same
   mechanism `audit_alignment.py` uses).

**Wire-up:** `visual_diff.py` should optionally invoke the extractor and
fold `diff_bboxes.json` into `visual_diff.json` as a `per_page.bboxes`
field. Independent invocation also works: feed it an existing out/ dir.

## Acceptance Criteria

- [ ] `tools/diff_bbox_extract.py` exists with the usage documented in its
      docstring (same shape as other tools)
- [ ] Run against any existing template's `visual_diff` output dir produces
      `diff_bboxes.json` plus optional overlay PNGs
- [ ] Slot attribution works for at least one template — verified by a
      deliberate slot-bbox-sized drift in a test (e.g. shifted P1 portrait
      shows up as `attributed_slot: "P1 Kandidat-Portrait"`)
- [ ] Output is stable: same input → same JSON (deterministic ordering,
      no timestamps)
- [ ] `visual_diff.py` optionally invokes it (flag like `--extract-bboxes`),
      and the JSON merges cleanly into `visual_diff.json`
- [ ] Tests cover: noisy-AA filtering, multi-cluster pages, unattributed
      bbox (no slot overlap above threshold)

## Out of scope

- Auto-generating `diff.yml` `per_region:` blocks (separate follow-up if
  attribution proves accurate enough)
- Vision-model invocation with the cropped bboxes — this issue produces
  the data; the consumer (`visual_review.py`) is a follow-up
- Replacing `visual_diff.py`'s composite/montage outputs — those stay
- Re-implementing the diff pixel arithmetic — we operate on existing
  `diff-page-NN.png` only

## References

- Existing tool: `tools/visual_diff.py` (delta PNG output, per_region schema)
- Slot bbox helper: `tools/sla_lib/builder/bbox.py` (`frame_bbox_mm`)
- Existing consumer for similar slot lookups: `tools/audit_alignment.py`
- Related (do not duplicate): `tools/sla_diff.py` (structural XML diff, not pixels)

## Suggested ordering

This is independent of the IDML→DSL converter (issue #35 / GitHub #72)
but its first real test will likely be the new InDesign-imported template
diffed against the bundled `gruenes Cover 2.pdf` baseline. Useful for all
templates regardless — fine to ship in either order.
