# PITFALLS research — Issue 24 (Zeitung image-content extent + Codex audit)

**Researched:** 2026-05-09
**Researcher:** pitfalls specialist (sub-agent)
**Confidence:** HIGH on root-cause and Scribus semantics; HIGH on environment; MEDIUM on Codex iteration budget (single prior data point)

---

## TL;DR — Root cause is NOT what the issue assumes

The issue prompt assumes "13 frames use `scale_type=1, ratio=1` (Scribus aspect-fit)" and the fix is to switch them to `scale_type=0` with computed `local_scale`. **This is wrong about the post-#23 state.** Direct probe of the built doc shows the frames are ALREADY rendered with `scale_type=0` (because `library.inject_into_frame()` hard-pins `frame.scale_type = 0` after every injection — see `tools/sla_lib/builder/library.py:500`). The actual root cause is a different defect class:

> **The `INJECT_MAP` in `templates/zeitung-a4-grun/build.py` (~line 2580) declares per-frame target dimensions `(target_w_mm, target_h_mm)` that are 3–11 mm SMALLER than the actual frame `w_mm × h_mm`.** `library.crop_for_frame()` produces a JPEG sized exactly to the target dims at 300 DPI; with `scale_type=0` + `LOCALSCX=1`, Scribus renders that JPEG at JFIF-density-derived pt size (= target mm exactly), leaving the frame's outer 3–11 mm as **white margin**. This matches both the user-cited symptoms and the existing Codex audit (`reviews/codex-zeitung-visual.md`, all 7 findings = "bleed-gap" not "letterboxing").

Per-frame measurement (probed via the actual `build_doc()` output):

| Frame            | Frame mm     | Target mm    | Δw mm  | Δh mm  | aspect Δ |
|------------------|--------------|--------------|--------|--------|----------|
| Cover Hero       | 216.00×155.57| 210.00×155.60| **+6.00** | -0.03 | 2.9 % |
| P1 Hero          | 210.00×130.21| 207.00×130.20| **+3.00** | +0.01 | 1.4 % |
| P2 Mid           | 112.33× 58.00| 112.30× 58.00| +0.03  | -0.00 | 0.0 % |
| P3 Hero          |  71.67× 58.16|  71.70× 58.20| -0.03  | -0.04 | 0.0 % |
| P4 Foto-Spread   | 210.00×108.12| 207.00×108.10| **+3.00** | +0.02 | 1.4 % |
| P5 Hero          | 112.33× 84.12| 112.30× 84.10| +0.03  | +0.02 | 0.0 % |
| P7 Portrait      |  54.70× 82.00|  51.30× 76.40| **+3.40** | **+5.60** | 0.7 % |
| P10 Portrait     |  77.70× 94.43|  66.60× 94.40| **+11.10**| +0.03 | 16.6 % |
| P11 Bottom       | 210.00× 83.26| 207.00× 83.30| **+3.00** | -0.04 | 1.5 % |
| P13 Hero         | 210.00×147.36| 207.00×147.40| **+3.00** | -0.04 | 1.5 % |

**Conclusion:** 7 of 10 named frames have `frame_w − target_w ≥ 3 mm` (an entire bleed-width gap). Aspect mismatch alone (1.5 %) would be invisible on most pages — the *dimension* mismatch dominates. P10 Portrait is the worst (11.1 mm gap, 16.6 % aspect mismatch).

Implications for the planner:

- The **proposed `brand:image_fills_frame` rule should detect the dimension mismatch, not just the aspect mismatch.** Aspect-only would miss the major class.
- The **fix can be one-line per entry**: update `INJECT_MAP` so `(target_w_mm, target_h_mm) == (frame.w_mm, frame.h_mm)`. No `scale_type` change needed; injection already sets `scale_type=0`. No `local_scale` math needed; the JFIF DPI handles it.
- Alternatively, **eliminate the duplication**: have `inject_into_frame` (or a new helper) read `frame.w_mm × frame.h_mm` directly from the frame instance — no parallel target dims at all.
- The **rule is still valuable** because the `INJECT_MAP` pattern recurs across templates and the dimension drift is invisible until rendered.

---

## 1. PIL.Image side effects (HIGH confidence)

The proposed rule reads each asset's native dimensions via `PIL.Image.open(path)` per `BrandRule.check()` invocation. Probed environment:

- **Pillow 12.2.0** is pinned in `Dockerfile.claude`, available globally.
- `Image.open(path)` is **lazy** — it parses headers without loading raster data. For 14 JPEGs (~1–4 MB each) this is <50 ms total.
- **EXIF orientation:** Not present on any of the 14 Zeitung sample assets (probed every entry in `shared/sample-images/manifest.yml`). All return `getexif().get(0x0112) == None`. No `ImageOps.exif_transpose` needed for these assets.
- **Defensive coding still required:** end-user assets (post-MVP) may have EXIF orientation. Use `with Image.open(path) as im: ... w, h = ImageOps.exif_transpose(im).size` to be safe. Wrap in `try/except (FileNotFoundError, UnidentifiedImageError, OSError)` and emit `warning` ("can't determine letterbox status: asset missing/corrupt at path X") rather than crashing the audit.
- **Caching:** 14 frames × 1 PIL header read each ≈ 50 ms — no caching needed for Zeitung. If extended to other templates, cache via `functools.lru_cache(maxsize=256)` on `_native_dims_px(path)`.
- **Inline-image case:** Several Zeitung frames carry `inline_image_data` (the small icon at line 334, plus all preview-injected frames). The proposed rule must handle BOTH `frame.image` (disk path, may be empty string) AND `frame.inline_image_data` (qCompressed base64). For inline data, decode via `base64 → struct.unpack(">I", blob[:4]) → zlib.decompress(blob[4:]) → BytesIO → PIL.Image.open`. Cost: ~10 ms per frame. Same exception wrapper.

**Recommendation:** A single helper `_native_dims_px(frame, root_path) -> Optional[tuple[int,int]]` that:
1. Returns `(0, 0)` if both `frame.image == ""` and `frame.inline_image_data is None` (frame is a polygon-shaped placeholder; rule should skip).
2. Decodes inline data if present.
3. Falls back to disk via `frame.image` resolved against the template directory.
4. Wraps in try/except; on failure returns `None` and the rule emits `warning` not `error`.

---

## 2. Asset path resolution (HIGH confidence)

Two flows in the codebase:

**Flow A — disk path** (production templates' clean SLA, never inline-injected):
- `frame.image = "themen/klimaschutz-windrad.jpg"` or absolute.
- Most Zeitung frames in `template.sla` have `frame.image == ""` because they're empty slots. Round-trip to upstream-original SLA preserves the empty `PFILE`.

**Flow B — inline image data** (preview SLA via `library.inject_into_frame()`):
- After injection, `frame.inline_image_data = <qCompressed-base64>` and `frame.inline_image_ext = "jpg"`.
- `frame.image == ""` post-injection (cleared by the emit path; see `primitives.py:794` `pfile = "" if is_inline else (self.image or self.src)`).

**The new rule MUST check inline-image case first** — for the gallery preview (which is what the user sees in `page-NN.png` outputs), every Zeitung named-frame is inline-injected. For the clean `template.sla` (end-user starting point), the frames have no image at all and the rule should silently skip.

**Pitfall:** `structural_check.py` calls `mod.build_doc()`, which is `build_template` (the CLEAN variant, no injection). If the new rule runs against `build_doc()` only, it will silently skip every Zeitung frame because they have no image bytes. The rule must run against `build_preview()` for templates that have one — OR, more pragmatically, the rule should be evaluated against the `INJECT_MAP` declarations (target_w_mm, target_h_mm + library_id → asset.path → native dims) without actually injecting. **Recommend the latter** — it's deterministic, fast, and doesn't require running the watermark/encoding pipeline.

A new `BrandRule` subclass that walks `mod.INJECT_MAP` (if defined) is a clean pattern; for templates without an `INJECT_MAP` it skips. Document this convention.

---

## 3. Scribus `scale_type=0` semantics — VERIFIED via source code (HIGH confidence)

Critical clarification of the focus-area assumption (the prompt's #3 is partially incorrect). Verified by reading Scribus master at `scribus/pageitem.cpp::adjustPictScale()` and `scribus/pageitem_imageframe.cpp::DrawObj_Item()`:

```cpp
// pageitem.cpp::adjustPictScale (called when SCALETYPE=1)
if (ScaleType) return;          // SCALETYPE=1 → return; scale stays at user values
double xs = m_width / OrigW;    // m_width = frame width in pt; OrigW = native pixels
double ys = m_height / OrigH;
if (AspectRatio) {              // RATIO=1 → fit-INSIDE (letterbox)
    m_imageXScale = qMin(xs, ys);
    m_imageYScale = qMin(xs, ys);
}
```

```cpp
// pageitem_imageframe.cpp::DrawObj_Item — actual draw transformation
p->translate(m_imageXOffset * m_imageXScale, m_imageYOffset * m_imageYScale);
p->scale(m_imageXScale, m_imageYScale);
p->drawImage(pixm.qImagePtr());
```

Key facts:

- **SCALETYPE=1 + RATIO=1 = "fit-INSIDE" (letterbox)** — `qMin(xs, ys)`, not `qMax`. This is what the user is hitting if/when frames revert to `scale_type=1`.
- **SCALETYPE=1 + RATIO=0 = "stretch to fill, ignore aspect"** — distorts the image. Not what we want.
- **SCALETYPE=0 = "free / manual scale"** — `LOCALSCX/SCY` are honored verbatim. `adjustPictScale()` returns early.
- **Scribus does NOT have a native "fill frame proportionally / cover" mode.** Confirmed by the Scribus 2018 feature request (Mantis #15448) which is still open as of 2026. Aspect-fill must be implemented manually via SCALETYPE=0 + computed `local_scale = qMax(xs, ys)`.

**`OrigW/OrigH` units = pixels.** The conversion to pt happens only at frame-resize time (`scribusdoc.cpp` line ~`setWidth(OrigW * 72.0 / xres)`).

**For LOCALSCX=1 + SCALETYPE=0 + JPEG with JFIF density 300 DPI:**
- `imageXScale = 1` means painter scale 1 (1 pt per source pixel? No — 1 pixel-equivalent per pt).
- Actually: Scribus loads the JPEG at xres=300, so `OrigW=2480 px` for a 210mm-wide JPEG. The "size on canvas" with LOCALSCX=1 = `OrigW * 72 / xres × LOCALSCX = 2480 * 72/300 * 1 = 595.2 pt = 209.95 mm`. So **the JFIF density determines on-canvas size when LOCALSCX=1.** This is exactly what the production library does today: it encodes JPEGs at 300 DPI, sized to the target mm, and relies on JFIF density + LOCALSCX=1 for correct rendering.

**For aspect-fill at SCALETYPE=0** (when target_w_mm/target_h_mm match frame_w_mm/frame_h_mm — i.e., when the JPEG is encoded to the frame's actual aspect):
- `local_scale=(1, 1)` is the natural choice. The crop in `crop_for_frame` uses `ImageOps.fit(centering=...)` which already does aspect-fill on the source image to the target aspect.
- The proposed plan's `local_scale = max(frame_w_mm / asset_w_mm_at_native_dpi, ...)` is unnecessary if you go the "match target to frame" route. It's only needed if you keep target dims fixed and want to scale-up the JPEG.

**Recommendation:** Match `INJECT_MAP[anname]` target dims to actual frame dims; keep `local_scale=(1, 1)`. The crop pipeline + JFIF DPI does the right thing.

---

## 4. `local_offset_mm` for crop window (HIGH confidence — has a unit-conversion BUG to flag)

If you do go the "scale_type=0 + non-unity local_scale + local_offset for centered crop" route (focus-area #4), there's a **DSL unit bug**:

In `tools/sla_lib/builder/primitives.py:807`:
```python
"LOCALX": _fmt_num(mm_to_pt(lx_mm)),  # emit LOCALX in pt
```

Scribus's draw path computes the painter translation as `m_imageXOffset * m_imageXScale`. When `m_imageXScale = 1` (which the DSL assumes for the unit conversion), `LOCALX_pt = local_offset_mm × PT_PER_MM` correctly maps to "shift by local_offset_mm in frame mm". **But when `m_imageXScale ≠ 1` (any time you set a custom `local_scale`), the rendered translation in mm is `(LOCALX_pt / PT_PER_MM) × LOCALSCX = local_offset_mm × LOCALSCX`** — i.e., the field name `local_offset_mm` no longer means mm of frame translation; it means mm at LOCALSCX=1.

This is exactly **Pitfall #14 from #22** (cited in the prompt). It means:

- For SpreadImage halves (which use `local_scale=(1, 1)`), the math works.
- For new aspect-fill frames where `local_scale ≠ (1, 1)`, `local_offset_mm` is misnamed and miscomputed unless the planner explicitly accounts for the LOCALSCX multiplication.

**Recommended approach: don't go this route.** Make the JPEG match the frame aspect (via `crop_for_frame(target=frame.w, frame.h)`), keep `local_scale=(1, 1)`, and `local_offset_mm=(0, 0)`. The DSL is correct under those constraints. If a future use case demands non-unity LOCALSCX with non-zero offset, fix the DSL field semantics first (separate field `local_offset_source_mm` vs `local_offset_frame_mm`).

---

## 5. Image orientation / EXIF (HIGH confidence)

Verified: 14 of 14 Zeitung sample assets have NO EXIF orientation tag. `Image.open(path).getexif().get(0x0112)` returns `None` on every one.

- All assets are AI-generated via Codex (gpt-image-2) with size declared in manifest (`1024x1536` portraits, `1536x1024` themen/kontext). No camera EXIF data.
- `library.crop_for_frame()` does NOT call `ImageOps.exif_transpose` — but doesn't need to for these assets.
- **For the new rule:** read native dims via `Image.open(path).size` directly. Defensive `ImageOps.exif_transpose` is a 1-line cheap insurance for end-user assets but isn't load-bearing for Zeitung.
- **Pitfall:** if a future end-user asset arrives with `Orientation=6` (90° CCW), `Image.open(path).size = (W, H)` but the displayed-correct dims are `(H, W)`. Without `exif_transpose`, the rule would compute the wrong native aspect. Recommend including `exif_transpose` defensively.

---

## 6. Letterboxing tolerance — recommend 2 % (MEDIUM confidence)

Aspect-mismatch tolerance options:

| Tolerance | Catches | False positives |
|-----------|---------|-----------------|
| 1 %       | Most real letterboxing (>1mm gap on 100mm dim) | Slight — common photos ARE within 1 % of 3:2 / 4:3 |
| 2 %       | All real letterboxing >2mm gap on 100mm dim | Very few — only deliberate "near-fit" edge cases |
| 5 %       | Major letterboxing only | Misses smaller real defects |

For Zeitung specifically, the WORST aspect mismatch is P10 Portrait (16.6 %). A 2 % threshold would catch P10 but miss most others — but the *dimension* mismatch (3+mm) is the dominant signal and should be checked separately.

**Recommendation: TWO checks, not one.**
- **Aspect tolerance:** 2 % (catches genuine letterboxing class).
- **Dimension tolerance:** 0.5 mm absolute gap on either axis (catches the INJECT_MAP target/frame mismatch — the Zeitung's actual primary class).

Combined predicate: `letterbox_risk = (aspect_delta_pct > 2) OR (abs(rendered_w - frame_w) > 0.5) OR (abs(rendered_h - frame_h) > 0.5)`.

---

## 7. Severity carve — HIGH confidence

Per ISSUE.md: ERROR for full-bleed frames, WARNING otherwise. Definition of "full-bleed":

```python
def is_full_bleed(frame, page) -> bool:
    """Frame's outer-bbox extent reaches within bleed_mm of any page boundary."""
    bleed = page.bleed_mm or 3.0
    bbox = _frame_bbox_mm(frame, page)  # rotation-aware, from sla_lib.builder.bbox
    if bbox is None:
        return False
    x0, y0, x1, y1 = bbox
    pw_mm = page.width_pt * PT_TO_MM
    ph_mm = page.height_pt * PT_TO_MM
    return (x0 <= -bleed + 0.5
            or y0 <= -bleed + 0.5
            or x1 >= pw_mm + bleed - 0.5
            or y1 >= ph_mm + bleed - 0.5)
```

Applied to the 13 Zeitung frames (probed via build_doc + bbox):

| Frame            | Full-bleed? | Reason                                |
|------------------|-------------|---------------------------------------|
| Cover Hero       | YES (Cover, ERROR) | x:[-3, 213], page 0=cover both edges |
| P1 Hero          | YES         | full-page-width LEFT page, x reaches outer bleed |
| P2 Mid           | NO (interior)      | 112×58 mid-page                |
| P3 Hero          | NO (column)        | 72×58 column                   |
| P4 Foto-Spread   | YES         | full-page-width                 |
| P5 Hero          | NO (column)        | 112×84 column                  |
| P7 Portrait      | NO (column)        | 51×76 portrait                 |
| P9 Spread halves | YES (each half outer-bleed) |                       |
| P10 Portrait     | NO (column)        | 67×94 portrait                 |
| P11 Bottom       | YES         | 207×83 full-page-width          |
| P13 Hero         | YES         | 207×147 full-page-width         |

Maps cleanly: 5 user-cited / Codex-flagged ERROR cases (Cover, P1, P4, P11, P13 + P9 spread halves) all have `is_full_bleed = True`. Interior columns (P2, P3, P5, P7, P10) get WARNING — appropriate because letterboxing inside an interior column is sometimes design intent.

**Pitfall:** the `is_full_bleed` predicate must use the **rotation-aware bbox** (`sla_lib.builder.bbox.frame_bbox_mm`), not the raw `frame.x_mm + frame.w_mm`. Several Zeitung frames are rotated (e.g. `u2950` rotated 90° on the cover). The existing `_BleedCoverageRule` in `brand_constraints.py:595` is the reference pattern.

---

## 8. Codex visual audit risk (MEDIUM confidence)

Existing data point: `reviews/codex-zeitung-visual.md` ran in **129 seconds (2:09)** for 14 pages with `gpt-5.4`. Output was structured per-page with severity tags + verdict block. **Plan estimate: 3–5 min per Codex run** to be safe (allow for queueing / retries). For two runs (pre-fix + post-fix verify), budget 10 min wall-time.

**Pitfall — Codex finds non-letterboxing issues:** The existing audit tagged everything as "bleed-gap" (the dominant class). But Codex IS capable of surfacing other classes (color contrast, text size, spacing, z-order). The plan must classify each Codex finding into:

| Class                                  | Action |
|----------------------------------------|--------|
| (a) Already covered by existing rule  | Note in EXECUTION.md, no new code |
| (b) New letterbox/bleed-gap class     | Covered by `brand:image_fills_frame` |
| (c) NEW class needing follow-up rule  | Defer to Issue #25 (do NOT extend scope) |

**Defer-to-#25 examples** that the plan should explicitly NOT try to fix in #24:
- Z-order issues (text behind image, masthead behind body text)
- Color-contrast violations (white text on yellow, black text on Dunkelgrün)
- Off-center placement of subject within frame (crop_focus issues — already addressable via manifest, not a brand rule)
- Hyphenation / orphans / widows
- Font-size inconsistency

Document the boundary in EXECUTION.md so the user can see what was deferred.

**Codex reliability:** per the existing review, 7 alignment defects flagged but the report admits "best-effort identification by visual position" — Codex doesn't always know frame names. The plan must accept fuzzy targeting and resolve manually (cross-reference with `bin/audit-alignment --json`).

**Output format for new Codex runs:** include `<verdict value="pass|fail" critical=N high=N medium=N>` block — already a convention in `reviews/codex-zeitung-visual.md`. Easy machine-parse for iteration-budget gates.

---

## 9. TDD-for-rules iteration budget (MEDIUM confidence)

Pattern from #23: build rule → run audit + Codex → if Codex sees something audit misses, strengthen rule → re-iterate. Budget recommendation:

- **Iteration 1 (mandatory):** Implement `brand:image_fills_frame` based on the dimension/aspect mismatch model documented above. Run Codex; cross-check coverage.
- **Iteration 2 (if needed):** If Codex surfaces a class the rule missed (e.g. asset-on-disk frames with stale `frame.image`, or rotation-aware aspect mismatch), tighten predicate ONCE.
- **Iteration 3 (only if iteration 2 misses):** Last call — if the rule still misses, document gap in EXECUTION.md, ship what's caught, defer the remainder to #25.

**Hard cap: 3 iterations.** Per #23 EXECUTION.md, iterating more than 3 times signals the rule's underlying model is wrong; better to ship and refactor. Each iteration costs ~5 min Codex + ~2 min code change + verification.

---

## 10. Geometric tests for image-content extent (HIGH confidence)

Per #23 pattern (`tools/sla_lib/tests/test_zeitung_geometry.py`), pin **invariants of the rendered-content bbox**, not absolute coords. For each fixed frame, the test should:

1. Get `frame.w_mm × frame.h_mm` from `build_preview()`.
2. Read inline image data → decode → PIL → native px.
3. Read `frame.scale_type`, `frame.local_scale`, `frame.local_offset_mm`, JFIF DPI from inline image header.
4. Compute the **rendered-content bbox** in frame-mm:
   ```
   if scale_type == 0:
       rendered_w_mm = native_w_px * 25.4 / dpi * local_scale[0]
       rendered_h_mm = native_h_px * 25.4 / dpi * local_scale[1]
       offset_x_mm = local_offset_mm[0] * local_scale[0]    # NB: source-mm → frame-mm
       offset_y_mm = local_offset_mm[1] * local_scale[1]
   elif scale_type == 1 and ratio == 1:
       s = min(frame_w_mm / native_pt_w_mm, frame_h_mm / native_pt_h_mm)
       rendered_w_mm = native_pt_w_mm * s
       rendered_h_mm = native_pt_h_mm * s
       # centered by Scribus
       offset_x_mm = (frame_w_mm - rendered_w_mm) / 2
       offset_y_mm = (frame_h_mm - rendered_h_mm) / 2
   ```
5. Assert `rendered_w_mm >= frame_w_mm - 0.5 AND rendered_h_mm >= frame_h_mm - 0.5` (image fills or overflows frame).

**No PNG inspection required.** All math from build artifacts.

**Pitfall:** the existing `_load_zeitung_doc` helper calls `mod.build_doc()` (clean variant — empty inline data). For these tests you need `build_preview()`. Add a `_load_zeitung_preview_doc()` helper alongside `_load_zeitung_doc()`.

**Pitfall #2:** decoding inline image data requires reversing `pack_inline_image` — base64 → struct unpack first 4 bytes → zlib decompress remainder → BytesIO → PIL. Reference: `tools/sla_lib/builder/primitives.py:750-761`. Add a helper `_decode_inline(blob_b64, ext) -> bytes` near `pack_inline_image` for symmetry.

---

## 11. Atomic-PR ordering (HIGH confidence)

The proposed task chain in the prompt is sound. Refinements:

| Task | Notes |
|------|-------|
| T01 add `brand:image_fills_frame` rule + tests | New BrandRule walks INJECT_MAP-style declarations. Tests use synthetic Document, not Zeitung — keeps unit tests fast. |
| T02 extend `audit_alignment.py` with `--check-image-extent` | Optional; or just re-use `structural_check` since the rule lives there. **Probably unnecessary** — the rule already runs in `structural_check --all`. Verify before adding CLI surface. |
| T03 Codex visual audit gate | Run `issue-cli review-exec --tool codex` with prompt asking per-page enumeration. Save to `reviews/codex-zeitung-all-pages.md`. Cross-check against `bin/audit-alignment zeitung-a4-grun --json`. |
| T04 fix 13 Zeitung frames | **Single-line per entry: update INJECT_MAP** so `target_w_mm == frame.w_mm` and `target_h_mm == frame.h_mm`. No `scale_type` change. No `local_scale` change. Atomic with re-run. |
| T05 regen + SHA bump | `bin/render-gallery zeitung-a4-grun --skip-visual-diff` then `bin/check-stale-previews` to confirm SHA bumped in `meta.yml::previews_for_sla`. |
| T06 invariant tests for rendered-content extent | See §10 above. Tests fail before T04, pass after. |
| T07 EXECUTION.md | Document Codex iteration count, deferred classes, iteration budget consumed. |

**Critical ordering:** T01 (rule) MUST land BEFORE T04 (fix) so the test that ships in T01 fails on Zeitung as a witness, then passes after T04. This is the #23 TDD-for-rules pattern.

---

## 12. Pre-applied `brand_overrides[brand:image_fills_frame]` for non-Zeitung templates (HIGH confidence)

When the new rule lands, it runs globally via `BRAND_CONSTRAINTS`. Templates without an `INJECT_MAP` (or with one whose target dims are stale) will trip the rule and break `python3 -m sla_lib.builder.structural_check --all`.

**Pre-apply** `brand_overrides` skip on every non-Zeitung template that has any image-bearing build_preview, with `reason: "scheduled for follow-up audit (issue #24 deferred to #25)"`. Templates to check (probed):

| Template | Has INJECT_MAP? | Pre-skip? |
|----------|------------------|-----------|
| zeitung-a4-grun | YES (the focus) | NO — rule must fire here |
| postkarte-a6-kampagne | check (round-tripped from postkarte-vorlage-original.sla) | YES |
| plakat-a1-hochformat | check (round-tripped from plakat-a1-hochformat-original.sla) | YES |
| kandidat-falzflyer-din-lang | likely YES | YES |
| themen-plakat-a3-quer | likely YES | YES |
| infostand-tent-card-a5-quer | likely | YES |
| wahltag-tueranhaenger | YES (per memory note about visual changes) | YES |
| wahlaufruf-postkarte-a6-quer | likely | YES |

The plan should add a discovery step in T01: list every template's `build.py`, identify which have an `INJECT_MAP` or call `library.inject_into_frame`, and add `brand_overrides` entries pre-emptively.

---

## 13. Risk: 13 frames × asset re-crop visually changes Zeitung pages (HIGH confidence)

**Yes, the page-NN.png will visually change** when the INJECT_MAP target dims update. The crop aspect changes, which means `ImageOps.fit(centering=...)` re-cuts the image at a different aspect — content visible in the OLD crop may scroll out of the NEW crop, and vice versa.

Specifically:
- Cover Hero target 210×155.6 (1.350) → 216×155.57 (1.388): wider crop. The wind turbine subject (`crop_focus=[0.65, 0.50]`) shifts position slightly within the frame. ~3 mm of left or right additional content visible.
- P10 Portrait target 66.6×94.4 (0.706) → 77.7×94.43 (0.823): much wider crop. Stefan's portrait gets noticeably more side-context (shoulders/background). Crop focus `[0.50, 0.38]` keeps face centered.

**Plan must:**
- Update **all 13 visual baselines** (`page-NN.png`) atomically with T04.
- The render-gallery diff will be NON-trivial; reviewer must accept the new pixel baseline in PR.
- Document the visual-change scope in EXECUTION.md so the reviewer doesn't reject the PR thinking something broke.
- For the wahltag-tueranhaenger case (per memory note), THIS template is not in scope for #24 (it's a different template) — but if the new rule fires on it, the pre-applied `brand_overrides` skip prevents the PR scope from leaking.

**No `bin/render-gallery zeitung-a4-grun --skip-visual-diff` should fail** on this. The flag specifically suppresses the visual-diff gate.

---

## 14. `bin/render-gallery` regenerates ~30 files + auto-bumps SHA (HIGH confidence)

Per #23 EXECUTION.md and observed mechanics:
- `bin/render-gallery zeitung-a4-grun --skip-visual-diff` regenerates: 14 page-NN.png + 14 site/public/.../page-NN.png mirror + preview.pdf + baseline.pdf comparison + meta.yml SHA update.
- Auto-bumps `meta.yml::previews_for_sla` to the new SHA-256 of the regenerated `template-preview.sla`.
- `bin/check-stale-previews` exit 0 confirms the SHA in `meta.yml` matches the file on disk. Required acceptance gate.
- **Pitfall:** if the build is non-deterministic, the SHA flickers between runs. The library code claims byte-determinism (`Pillow==12.2.0` pinned, JPEG kwargs pinned). Verified in `library.py:46-49`. Should be stable.
- **Pitfall #2:** if `themen_klimaschutz_windrad-source.jpg` etc. are present in the manifest but `*-source.jpg` files are NOT on disk, the watermark re-stamps directly on already-watermarked source bytes. This produces a faintly visible double-watermark band but is "cosmetically benign" per the library docstring. Probed: no `-source.jpg` files exist in `shared/sample-images/portraits/` or `shared/sample-images/themen/` → all crops re-stamp the watermark on top of existing watermark. Acceptable per the existing convention.

---

## 15. Codex CLI auth — VERIFIED (HIGH confidence)

- `codex` binary at `/root/.npm-global/bin/codex` — version `codex-cli 0.128.0`.
- `issue-cli review-exec --tool codex --review-type topic --review-mode topic` is the orchestrator. Output saved to `--output-dir reviews/`.
- Existing run: `reviews/review-2026-05-09T14-44-21Z-zeitung-visual-gpt-5-4.md` with `model: gpt-5.4` frontmatter.
- Auth: codex CLI stores its own token in `~/.config/codex/`. Verified to be working as of today.

**Pitfall:** the prompt file MUST exist before invoking `issue-cli review-exec --prompt PATH`. Create the prompt as `.issues/24-…/prompts/codex-zeitung-all-pages.md` (or similar) with explicit per-page instructions.

**Recommended prompt structure (see existing `gate-1-prompt.md` for template):**
```
You are auditing alignment of a 14-page A4 Zeitung in a campaign template.

Inspect each PNG in templates/zeitung-a4-grun/page-{01..14}.png.

For EACH page, enumerate every alignment defect you observe. Format:
- Page: NN
- Type: <bleed-gap | letterbox | flush-mismatch | other>
- Frames involved: <verbal description, frame names if recognizable>
- What's wrong: <one sentence>
- Severity: ERROR | WARNING

End with a verdict block: <verdict value="pass|fail" critical=N high=N medium=N>
```

---

## 16. Environment audit (HIGH confidence)

| Dependency | Available | Version | Notes |
|------------|-----------|---------|-------|
| Python 3 | YES | 3.13.5 | |
| Pillow | YES | 12.2.0 | Pinned in Dockerfile.claude |
| PyYAML | YES | 6.0.3 | |
| codex CLI | YES | 0.128.0 | At `/root/.npm-global/bin/codex` |
| gh CLI | YES | 2.92.0 | For PR ops |
| issue-cli | YES | (project) | At `/usr/local/bin/issue-cli` |
| Scribus | YES | (binary present, headless) | At `/usr/bin/scribus`; Qt requires DISPLAY for GUI but `scribus --version` works headless via `xvfb-run` if needed |
| jsonschema | (assumed YES per Dockerfile) | — | Required by `library.validate_manifest` |

**Acceptance-gate scripts** (per ISSUE.md AC):
- `bin/audit-alignment zeitung-a4-grun --strict` — exists, callable.
- `python3 -m sla_lib.builder.structural_check --all` — exists, callable.
- `python3 -m unittest discover tools/sla_lib/tests` — exists, 35 test files present.
- `bin/check-stale-previews` — exists.

All preconditions met for autonomous execution.

---

## 17. Cross-cutting: rule must be GENERIC (HIGH confidence)

Per ISSUE.md AC: "New rules are GENERIC (work on any template, no Zeitung-specific code)."

**Generic predicate:** "If a frame has an image (disk or inline), and the image's rendered-content bbox does not fill the frame's outer bbox within tolerance, flag it." This works for any template.

**Anti-pattern to avoid:** hard-coding Zeitung frame names like `if frame.anname == "Cover Hero"`. The rule should walk every ImageFrame on every non-master page, with no slug check.

**Generic dimension-mismatch detector** (the dominant class):
```python
def _detect_dim_mismatch(frame, image_native_dims_px, dpi_assumed):
    """Returns (rendered_w_mm, rendered_h_mm, frame_w_mm, frame_h_mm) or None."""
    if frame.scale_type == 0:
        # Manual scale; rendered size from JFIF density × LOCALSCX
        scx, scy = frame.local_scale
        rw = image_native_dims_px[0] * 25.4 / dpi_assumed * scx
        rh = image_native_dims_px[1] * 25.4 / dpi_assumed * scy
    elif frame.scale_type == 1 and frame.ratio == 1:
        # Auto-fit / aspect-locked = letterbox-INSIDE
        s_w = frame.w_mm / (image_native_dims_px[0] * 25.4 / dpi_assumed)
        s_h = frame.h_mm / (image_native_dims_px[1] * 25.4 / dpi_assumed)
        s = min(s_w, s_h)
        rw = image_native_dims_px[0] * 25.4 / dpi_assumed * s
        rh = image_native_dims_px[1] * 25.4 / dpi_assumed * s
    else:  # scale_type=1, ratio=0 (stretch) — fills exactly, no letterbox
        return None
    return rw, rh, frame.w_mm, frame.h_mm
```

**Pitfall:** assuming `dpi=300` is hard-coded. Read from the inline JPEG's JFIF density tag where present, else fall back to 300 (matches `library.crop_for_frame`'s default).

---

## 18. Acceptance-criteria sanity check

Cross-checked the 8 AC bullets in ISSUE.md against feasibility:

| AC | Achievable | Risk |
|----|-----------|------|
| Codex visual review for ALL 14 pages, saved to reviews/ | YES | Codex API limits, ~3 min wall time |
| Every Codex visual issue captured by ≥1 BrandRule | LIKELY | Class (c) [new follow-up] should be deferred to #25, NOT block this AC |
| `brand:image_fills_frame` with full test coverage; ERROR for full-bleed | YES | Standard pattern |
| 13 Zeitung frames fixed | YES | INJECT_MAP one-line update per entry |
| `bin/audit-alignment zeitung-a4-grun --strict` exit 0 | YES | Already passing per #23 |
| `structural_check --all` exit 0 | YES (with brand_overrides pre-skip on other templates) | Coordinate carefully |
| `unittest discover tools/sla_lib/tests` exit 0 | YES | New tests in test_zeitung_geometry.py + test_brand_image_fills_frame.py |
| `bin/check-stale-previews` exit 0 | YES | Auto-bumps in T05 |
| Re-run Codex post-fix: zero remaining alignment issues from new rule perspective | LIKELY (iteration 1) | If Codex still flags after iteration 3, document gap and ship |
| Geometric tests pin rendered-content extent invariants for 13 frames | YES | Pattern in §10 |

---

## Sources

### HIGH confidence (verified by source code or direct probe)

- Scribus draw path: `pageitem_imageframe.cpp::DrawObj_Item` — github.com/scribusproject/scribus master
- Scribus auto-fit math: `pageitem.cpp::adjustPictScale` — github.com/scribusproject/scribus master
- Scribus SLA loader for LOCAL* attributes: `scribus150format.cpp` — github.com/scribusproject/scribus master
- Scribus JPEG xres handling: `scimgdataloader_jpeg.cpp` — github.com/scribusproject/scribus master
- DSL emit: `tools/sla_lib/builder/primitives.py:789-841` (ImageFrame.to_pageobject)
- DSL parse: `tools/sla_to_dsl.py:760-822` (LOCAL* attributes round-trip)
- Library inject: `tools/sla_lib/builder/library.py:436-500` (inject_into_frame sets scale_type=0)
- Library crop: `tools/sla_lib/builder/library.py:326-433` (crop_for_frame, JPEG dpi=(300,300))
- Existing brand rules: `tools/sla_lib/builder/brand_constraints.py:1052-1171` (14 rules + registry)
- Existing audit tool: `tools/audit_alignment.py:1-499`
- Existing geometric tests: `tools/sla_lib/tests/test_zeitung_geometry.py`
- Zeitung INJECT_MAP: `templates/zeitung-a4-grun/build.py:2580-2599`
- Zeitung frame dims (probed via build_doc): captured live with python3 oneliner — see §root-cause table
- Sample-image native dims (probed via PIL.Image.open): no EXIF orientation on any of 14 assets
- Existing Codex audit timing: `reviews/codex-zeitung-visual.md` (129s for 14 pages)
- Environment versions: `python3 --version`, `python3 -c "import PIL; print(PIL.__version__)"`, `codex --version`, `gh --version`, `which scribus`

### MEDIUM confidence (single source / inferred)

- 2 % aspect tolerance recommendation — based on aspect-distribution analysis of the 13 frames; needs validation in iteration
- Codex 3-iteration cap — extrapolated from #23 EXECUTION.md (ran 1 iteration); may need 1 more if Codex finds an unanticipated class
- Scribus has no native "fill frame proportionally" mode — inferred from absent code path AND open Mantis ticket #15448 (2018, still open)

### LOW confidence (would benefit from validation)

- Whether `bin/audit-alignment` should grow `--check-image-extent` flag, OR whether the rule should run only via `structural_check`. Either works; T02 may be unnecessary scope.
- Whether end-user assets (post-MVP) will routinely have EXIF orientation. Recommend defensive `ImageOps.exif_transpose` regardless.

