# RESEARCH — #24: Zeitung remaining alignment (INJECT_MAP drift, not letterboxing) + Codex audit

**Status:** synthesized from two parallel research dimensions (codebase / pitfalls). Confidence high — root cause verified by direct runtime probe + cross-checked against existing Codex review output. **The ISSUE.md "Why" was wrong about the root cause** — RESEARCH.md corrects it.

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for full detail.

---

## Executive summary — the root cause is INJECT_MAP drift, NOT scale_type letterboxing

ISSUE.md framed the bug as "13 ImageFrames use `scale_type=1, ratio=1` and Scribus letterboxes". **Both research agents independently verified this is wrong:**

- `library.inject_into_frame()` already hard-pins `frame.scale_type = 0` for every preview-injected frame (`tools/sla_lib/builder/library.py:500`).
- `crop_for_frame` produces a JPEG sized exactly to the INJECT_MAP `(target_w_mm, target_h_mm)` at 300 DPI; with `scale_type=0` + `LOCALSCX=1`, the JPEG renders at its JFIF density = target mm exactly.
- **The actual bug:** `INJECT_MAP[anname]` in `templates/zeitung-a4-grun/build.py:2570-2599` declares targets that are **3–11 mm SMALLER** than the actual frame dims for 7 of 10 named photo entries. #22 (T12 spine inset) and #23 (T07 outer-bleed extension) changed the frames' `w_mm`/`h_mm` without updating INJECT_MAP. The rendered image content lands at the OLD target size, leaving the frame's outer 3–11 mm as white margin.

Verified drift table (from codebase agent §4):

| Frame | Frame `(w, h)` mm | INJECT_MAP target | Δw mm | Δh mm | Visible symptom |
|---|---|---|---|---|---|
| Cover Hero | 216 × 155.6 | 210 × 155.6 | **+6.0** | -0.03 | 6 mm white pillar right |
| P1 Hero | 210 × 130.2 | 207 × 130.2 | **+3.0** | +0.01 | 3 mm right |
| P3 Hero | 71.7 × 58.2 | 71.7 × 58.2 | -0.03 | -0.04 | clean |
| P4 Foto-Spread | 210 × 108.1 | 207 × 108.1 | **+3.0** | +0.02 | 3 mm right |
| P7 Portrait | 54.7 × 82.0 | 51.3 × 76.4 | **+3.4** | **+5.6** | 3.4 right + 5.6 top/bottom |
| P9 Spread halves | 213 × 126.1 | 210 × 126.1 | **+3.0** | +0.04 | 3 mm right (each half) |
| P10 Portrait | 77.7 × 94.4 | 66.6 × 94.4 | **+11.1** | +0.03 | **11 mm right** |
| P11 Bottom | 210 × 83.3 | 207 × 83.3 | **+3.0** | -0.04 | 3 mm right |
| P13 Hero | 210 × 147.4 | 207 × 147.4 | **+3.0** | -0.04 | 3 mm right |

The existing `reviews/codex-zeitung-visual.md` from #23 confirms ALL 7 user-cited pages with exactly the symptom "white strip on the outer print edge" — not letterboxing. **The data was there; #23's synthesis didn't recognize it as INJECT_MAP drift.** The 3 unnamed Dunkelgrün-fill ImageFrames (pages 12/13/14) are NOT in the rendering pattern (they have no image content, just `fill='Dunkelgrün'`); the new rule must skip them.

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **Primary fix is one-loop change in `build_preview()::INJECT_MAP`** — read live `frame.w_mm` and `frame.h_mm` from each frame instead of literal target tuples. **Single commit, ~30 line diff.** | Both research dimensions converged on this. Root cause is INJECT_MAP drift, not scale_type. |
| 2 | **New rule `brand:image_fills_frame`** (severity ERROR for full-bleed, WARNING otherwise) catches this drift class going forward. Detects: rendered content extent < frame extent, by computing rendered extent from `scale_type` + `local_scale` + asset native dims (via PIL or qCompress decode). Severity = ERROR if frame outer-bbox touches `±bleed`; WARNING otherwise. | Catches the regression class without rendering. Verified algorithm in codebase agent §5. |
| 3 | **Skip frames with no image content** (`image=='' and inline_image_data is None`) — they're solid-fill rectangles. The 3 unnamed Dunkelgrün polygons on Zeitung pages 12/13/14 fall here. | Counting artifact; rule must explicitly skip. |
| 4 | **Codex visual review of all 14 pages** with refined prompt (no priming with expected outcomes per `feedback_review_no_code_in_prompt.md`). Existing `reviews/codex-zeitung-visual.md` is reusable as comparison baseline. | User direction + #23 TDD-for-rules pattern. |
| 5 | **Geometric tests pin RELATIONSHIPS**: rendered-content bbox extent ≈ frame outer extent within 0.5mm. Test class `ImageContentExtentInvariantTests` in `test_zeitung_geometry.py`. NOT absolute coordinates. | #23 invariant-pinning pattern (locked decision #7 from #23). |
| 6 | **Audit tool integration via `_audit_doc()`** (Option A from codebase agent §7) — wire `_ImageFillsFrameRule` into `audit_alignment.py:175` like `_SpineSafetyRule`. Add `--check-image-extent` flag (default ON). | Established pattern. |
| 7 | **Pre-apply `brand_overrides[brand:image_fills_frame]`** on non-Zeitung templates with reason "scheduled for follow-up audit per #24" so `--all` stays green during T01. Apply to: postkarte-a6-kampagne, plakat-a1-hochformat, infostand-tent-card, themen-plakat-a3-quer, kandidat-falzflyer-din-lang, wahltag-tueranhaenger, wahlaufruf-postkarte-a6-quer (7 templates). | Atomic-PR ordering. |
| 8 | **Aspect-fill helper `compute_aspect_fill` lives in `library.py`** alongside `inject_into_frame`/`crop_for_frame`. NOT used in #24's primary fix path (T03's INJECT_MAP update is enough), but provided for future templates that don't use `inject_into_frame`. | Codebase agent §6. |
| 9 | **Atomic-PR ordering** (per pitfalls #4): T01 add rule + helper → T02 audit-tool wire-in → T03 pre-apply non-Zeitung overrides → T04 Codex visual review (verification gate) → T05 fix Zeitung INJECT_MAP (atomic) → T06 regen + SHA bump → T07 invariant tests → T08 EXECUTION.md. | Both research agents agreed on this. |
| 10 | **Codex iteration budget = 2 runs**: pre-fix audit (T04) + post-fix audit (T07b before EXECUTION). If Codex still flags issues post-fix, document and ship; defer to #25. | Pitfalls #6. |
| 11 | **Visual baselines change**: 13 page-NN.png files will visibly shift when INJECT_MAP regenerates assets. Human reviewer rebases in PR review. Document in PR description. | Pitfalls #7. |
| 12 | **Avoid non-unity `local_scale`** in this issue — pitfall P-14 from #22 RESEARCH (unit-bug at `local_offset_mm × LOCALSCX`). Stay with `scale_type=0` + matched JPEG dims (which is what `inject_into_frame` already does). | Pitfalls #4. |
| 13 | **Rule registry count: 14 → 15** after #24. Update `tests/test_brand_constraints.py::RegistryTests::test_fourteen_rules_exact` to `test_fifteen_rules_exact` + bump count + add `"brand:image_fills_frame"` to expected set. | Codebase agent §11. |
| 14 | **Codex prompt is rewritten** (NOT the priming-heavy `prompts/zeitung-visual-audit.md` from #23). New file `prompts/zeitung-all-pages-audit.md` enumerates all 14 pages without expected-outcomes hints. | Codebase agent §9 + `feedback_review_no_code_in_prompt.md`. |
| 15 | **DON'T refactor `inject_into_frame` to read frame dims directly** — too invasive. Stick with the INJECT_MAP loop fix in `build_preview()`. Refactor is deferred future work. | Pitfalls open question; conservative choice. |

---

## Scope changes vs. ISSUE.md

| ISSUE.md | Status | Why |
|---|---|---|
| "13 ImageFrames use scale_type=1, ratio=1 and Scribus letterboxes" | **CORRECTED**: Root cause is INJECT_MAP target dim drift after #22/#23 changed frame extents. `library.inject_into_frame` sets `scale_type=0` already. |
| 13 affected frames | **CORRECTED to 10** photo frames + 3 unnamed Dunkelgrün polygons that don't render images (rule must skip). |
| Phase 4: switch frames to `scale_type=0` with computed `local_scale` | **CHANGED** to: update `INJECT_MAP[anname]` targets to read live `frame.w_mm`/`frame.h_mm`. No `scale_type` change. No `local_scale` math. |
| `compute_aspect_fill` helper as primary fix path | **DEMOTED** to "future helper, not used in this issue". |

---

## User constraints

- **Codex visual review of ALL 14 pages** (per "Review all pages with codex not just the ones I mentioned").
- **Build detector first**: rule + tool wire-in + Codex audit BEFORE touching INJECT_MAP.
- **Generic rule** — works on any template, no Zeitung-specific code.
- **Atomic PR.**
- **No new dependencies.** PIL already in env.

---

## Codebase Analysis — interfaces

<interfaces>

### `ImageFrame` and Scribus emit semantics

```
file: tools/sla_lib/builder/primitives.py:764-841
@dataclass
class ImageFrame(_Frame):
    src: str = ""               # PFILE path
    image: str = ""             # alias for src
    layer: int = 1
    local_scale: tuple[float, float] = (1.0, 1.0)        # LOCALSCX, LOCALSCY
    local_offset_mm: tuple[float, float] = (0.0, 0.0)    # LOCALX, LOCALY
    local_rotation_deg: float = 0.0
    scale_type: int = 1         # SCALETYPE
    ratio: int = 1              # RATIO (preserve aspect with scale_type=1)
    pic_art: int = 1
    fill: Optional[str] = None  # PCOLOR (frame background; solid frames have image='')
    inline_image_data: Optional[str] = None  # qCompress base64
    inline_image_ext: Optional[str] = None
```

**SCALETYPE/RATIO matrix (verified from primitives.py:806-811 + Scribus source):**
- `scale_type=0`: ScaleAuto = fit-to-frame. With `ratio=1`, aspect preserved (letterbox). With `ratio=0`, stretch.
- `scale_type=1, ratio=1`: Manual scale, preserve aspect. Image at `native_px / dpi × 25.4 × local_scale` mm.
- `scale_type=1, ratio=0`: Manual, no aspect (`local_scale=(sx, sy)` independent).

### `library.inject_into_frame` (the path that already sets `scale_type=0`)

```
file: tools/sla_lib/builder/library.py:436-500
def inject_into_frame(frame, img: LibraryImage, *, target_w_mm, target_h_mm,
                       dpi=300, quality=80, apply_watermark=True) -> None:
    # Crops img to target_w/h aspect via crop_for_frame, embeds as inline JPEG.
    # SIDE EFFECTS:
    #   frame.inline_image_data = data
    #   frame.inline_image_ext = "jpg"
    #   frame.scale_type = 0       # ScaleAuto — image fits frame
    #   # Does NOT touch frame.ratio / local_scale / local_offset_mm
```

### `BRAND_CONSTRAINTS` registry (post-#23, 14 rules; 15th joins in #24)

```
file: tools/sla_lib/builder/brand_constraints.py:1052-1171
1.  brand:color_palette
2.  brand:font_family
3.  brand:line_spacing_0.9
4.  brand:hl_sl_distance_x2
5.  brand:logo_size_3M
6.  brand:text_on_green
7.  brand:bleed_3mm
8.  brand:wahlkreuz_colored_bg
9.  brand:inside_page
10. brand:spine_safety
11. brand:visual_adjacency_drift
12. brand:bleed_coverage
13. brand:image_text_overlap
14. brand:cover_extent_match
15. brand:image_fills_frame  # NEW in #24
```

### `audit_alignment.py` integration point

```
file: tools/audit_alignment.py:175-184
# Existing pattern: _SpineSafetyRule wired into _audit_doc().
# Add _ImageFillsFrameRule the same way.
```

</interfaces>

---

## Architecture patterns

### `_ImageFillsFrameRule` (the 15th rule)

Full pseudocode in `research/codebase.md` §5. Highlights:

```python
@dataclass(frozen=True)
class _ImageFillsFrameRule(BrandRule):
    tolerance_ratio_pct: float = 1.0   # 1% of longer side
    tolerance_mm: float = 0.5
    dpi: int = 300

    def check(self, primitives, doc, constraints=None) -> list[Violation]:
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            for item in page.items:
                if not isinstance(item, ImageFrame):
                    continue
                # SKIP solid-fill rectangles
                if not (item.image or item.src or getattr(item, "inline_image_data", None)):
                    continue
                aw_px, ah_px = self._resolve_asset_size(item)
                if aw_px is None:
                    violations.append(Violation(severity="warning", ...))
                    continue
                rendered_w_mm, rendered_h_mm = self._rendered_extent(item, aw_px, ah_px)
                gap_w = item.w_mm - rendered_w_mm
                gap_h = item.h_mm - rendered_h_mm
                tol = max(self.tolerance_mm, self.tolerance_ratio_pct/100 * max(item.w_mm, item.h_mm))
                if gap_w <= tol and gap_h <= tol:
                    continue
                # Letterboxing detected
                bbox = frame_bbox_mm(item, page)
                is_full_bleed = self._is_full_bleed(bbox, ...)
                sev = "error" if is_full_bleed else "warning"
                violations.append(Violation(
                    severity=sev,
                    rule_id=self.id,
                    message=(
                        f"frame {item.anname!r} ({item.w_mm:.1f}×{item.h_mm:.1f}mm) "
                        f"renders {rendered_w_mm:.1f}×{rendered_h_mm:.1f}mm — "
                        f"{gap_w:.1f}×{gap_h:.1f}mm white margin. "
                        f"Either: update INJECT_MAP target to ({item.w_mm:.3f}, {item.h_mm:.3f}); "
                        f"or library.compute_aspect_fill(...) for non-INJECT path."
                    ),
                    targets=(item.anname or f"<unnamed y={item.y_mm:.1f}>",),
                ))
        return violations
```

### INJECT_MAP fix in `build_preview()`

```python
# Before (build.py:2570-2599 today):
INJECT_MAP = {
    "Cover Hero": ("themen_klimaschutz_windrad", 210.0, 155.6),
    "P1 Hero":    ("themen_soziales_gemeindebau", 207.0, 130.2),
    # ... wrong target dims drifted from #22/#23 frame edits
}
for page in doc.pages:
    for item in page.items:
        if isinstance(item, ImageFrame) and item.anname in INJECT_MAP:
            asset_id, tw, th = INJECT_MAP[item.anname]
            library.inject_into_frame(item, library.load(asset_id),
                                       target_w_mm=tw, target_h_mm=th)

# After:
INJECT_MAP = {
    "Cover Hero":        "themen_klimaschutz_windrad",
    "P1 Hero":           "themen_soziales_gemeindebau",
    # ... only asset id, no dims (read from frame)
}
for page in doc.pages:
    for item in page.items:
        if isinstance(item, ImageFrame) and item.anname in INJECT_MAP:
            asset_id = INJECT_MAP[item.anname]
            library.inject_into_frame(item, library.load(asset_id),
                                       target_w_mm=item.w_mm,
                                       target_h_mm=item.h_mm)
```

### Geometric invariant tests

```python
# tools/sla_lib/tests/test_zeitung_geometry.py — append:
class ImageContentExtentInvariantTests(unittest.TestCase):
    """For each fixed frame, rendered content extent ≈ frame outer extent."""
    @classmethod
    def setUpClass(cls):
        cls._preview_doc = _load_zeitung_preview_doc()  # build_preview()

    def _content_extent_mm(self, frame):
        # Decode inline JPEG via PIL → return rendered (w_mm, h_mm) at scale_type=0
        ...

    def _assert_fills_frame(self, anname, tol_mm=0.5):
        item, _ = _frame_by_anname(self._preview_doc, anname)
        cw, ch = self._content_extent_mm(item)
        self.assertAlmostEqual(cw, item.w_mm, delta=tol_mm)
        self.assertAlmostEqual(ch, item.h_mm, delta=tol_mm)

    def test_cover_hero_fills_frame(self): self._assert_fills_frame("Cover Hero")
    def test_p1_hero_fills_frame(self):    self._assert_fills_frame("P1 Hero")
    # ... 8 more tests for the 10 photo frames
```

---

## Common Pitfalls (consolidated)

### Must-handle (HIGH severity)

1. **The "Why" in ISSUE.md is wrong about root cause.** Locked decision #1 corrects it (INJECT_MAP drift, not letterboxing).
2. **Rule must skip image-less ImageFrames** (`image='' and inline_image_data is None`). 3 unnamed Dunkelgrün polygons on pages 12/13/14 fall here.
3. **PIL.Image side effects**: cache native dims per-process; wrap in try/except; missing asset → warning not silent skip.
4. **`is_full_bleed` for severity carve must use `frame_bbox_mm`** (rotation-aware), not raw `x_mm + w_mm`.
5. **Atomic-PR ordering** (locked decision #9): T01-T03 land detector + override before T04 Codex audit; T05 fix Zeitung INJECT_MAP atomic.
6. **`bin/render-gallery zeitung-a4-grun --skip-visual-diff` + meta.yml SHA bump are mandatory at T06.**
7. **Visual baselines change** for 13 PNGs; document for human reviewer.

### Worth knowing (MEDIUM)

8. **Codex iteration budget 2 runs** (pre-fix verification + post-fix verification). Don't iterate further; defer to #25.
9. **Codex prompt rewritten** without priming hints (locked decision #14).
10. **Pre-apply `brand_overrides[brand:image_fills_frame]`** on 7 non-Zeitung templates so `--all` stays green during T01.
11. **No native Scribus "fill/cover" mode** — verified via Scribus source (Mantis #15448 still open). The matched-JPEG-dims approach IS the canonical fix.
12. **DSL unit bug in `local_offset_mm` × LOCALSCX** at non-unity local_scale — avoid non-unity local_scale entirely (locked decision #12).

### Informational

13. **Inline-image dimension probing** via qCompress reverse: `b64decode → strip 4-byte BE length → zlib.decompress → PIL.Image.open(BytesIO)`.
14. **PIL Pillow==12.2.0** verified working on Python 3.13.5.
15. **No new dependencies.**

---

## Suggested PR shape

~10 commits across 8 tasks (per locked decision #9):

1. `T01: feat(brand): add brand:image_fills_frame rule + library.compute_aspect_fill helper` (rule code per RESEARCH.md skeleton; PIL-based asset dim probing; full unit tests with synthetic primitives + qCompress roundtrip)
2. `T02: feat(audit): wire image_fills_frame into audit_alignment + --check-image-extent flag` (Option A from codebase §7)
3. `T03: chore(meta): pre-apply brand_overrides[brand:image_fills_frame] to 7 non-Zeitung templates` (postkarte-a6-kampagne, plakat-a1-hochformat, infostand-tent-card, themen-plakat-a3-quer, kandidat-falzflyer-din-lang, wahltag-tueranhaenger, wahlaufruf-postkarte-a6-quer; reason "scheduled for follow-up audit per #24")
4. `T04: docs(reviews): Codex visual audit of all 14 Zeitung pages — pre-fix baseline` (run `issue-cli review-exec --tool codex` with new `prompts/zeitung-all-pages-audit.md`; output to `reviews/codex-zeitung-all-pages-iter1.md`; cross-check against `bin/audit-alignment zeitung --json`; document any class Codex sees that audit misses → **STOP-and-iterate gate**)
5. `T05: chore(zeitung): fix INJECT_MAP — read live frame.w_mm/h_mm` (atomic single commit; ~30 line diff)
6. `T06: chore(zeitung): regenerate template.sla + gallery via bin/render-gallery + SHA bump`
7. `T07: test(zeitung): ImageContentExtentInvariantTests in test_zeitung_geometry.py` (10 invariant tests for the 10 photo frames; pin RELATIONSHIPS not coordinates)
8. `T07b: docs(reviews): Codex visual audit of all 14 Zeitung pages — post-fix verification` (re-run prompt; output to `reviews/codex-zeitung-all-pages-iter2.md`; verdict "pass" with zero remaining alignment issues from new rule perspective; if still flags, document + defer)
9. `T08: docs(issues): execution complete + status flip`

Plus artifact commits (RESEARCH.md ✓, PLAN.md, EXECUTION.md). 11–12 commits total.

Next: `/issue:plan` turns this into XML-tagged tasks for the executor.
