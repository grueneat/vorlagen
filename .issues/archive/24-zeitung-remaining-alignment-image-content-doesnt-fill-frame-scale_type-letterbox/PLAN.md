# Plan: Zeitung remaining alignment — INJECT_MAP drift fix + brand:image_fills_frame rule + Codex visual audit of all 14 pages

<objective>
Restore Zeitung's image-content extents (Cover Hero, P1/P4/P9/P11/P13 Hero, P7/P10 Portrait — 7 of 10 named photo frames currently letterbox-leak 3–11 mm of white margin on the bleed side) by repairing the **`INJECT_MAP` drift** in `templates/zeitung-a4-grun/build.py:2570-2599` — NOT by re-encoding `scale_type` (the path the ISSUE.md "Why" assumed). Per the live runtime probe in RESEARCH.md §root-cause, `library.inject_into_frame()` already hard-pins `frame.scale_type = 0`; the bug is that INJECT_MAP target dims drifted out of sync with `frame.w_mm × frame.h_mm` after #22 T12 (spine inset) and #23 T07 (outer-bleed extension). The detector that catches this regression class going forward is a NEW BrandRule **`brand:image_fills_frame`** (severity ERROR for full-bleed frames, WARNING otherwise) that compares each ImageFrame's rendered-content extent (computed from `scale_type` + `local_scale` + asset native dims via PIL or qCompress reverse) to the frame's outer extent and flags >0.5 mm gaps. The detector lands FIRST (T01-T03), then a Codex visual review of all 14 Zeitung pages (T04, the verification gate), then the one-loop INJECT_MAP fix (T05 — atomic, ~30 line diff) + render-gallery + SHA bump (T06), then 10 invariant tests pinning the rendered-content-extent ≈ frame-extent relationship (T07), then a post-fix Codex re-audit (T08).

Why it matters: #23's stricter validation surfaced 7 "bleed-gap" findings on Zeitung that Codex correctly flagged but #23's `brand:bleed_coverage` rule didn't catch — because that rule inspects FRAME extents, and the frames are correct. The actual regression is in the INJECTION layer: the JPEG written into each frame is sized to the OLD target (pre-#22/#23), so the rendered content lands 3–11 mm short of the (now-extended) frame edges, leaving white pillarbox margins. Without a detector in this layer, every future `frame.w_mm` / `frame.h_mm` edit silently desyncs the corresponding `INJECT_MAP[anname]` target. The new rule is GENERIC (works on any template, no Zeitung-specific code) per the user's standing direction. RESEARCH.md (synthesized from two independent dimensions — codebase + pitfalls) verified the root cause via direct probe and corrects the ISSUE.md's "Why" inline.

Scope IN: 1 new BrandRule (`brand:image_fills_frame`); 1 helper (`library.compute_aspect_fill` — provided for future templates, NOT used in #24's primary fix path per locked decision #8); audit-tool wire-in via `_audit_doc()` + `--check-image-extent` flag (default ON); pre-applied `brand_overrides[brand:image_fills_frame]` skip on 7 non-Zeitung templates with reason "scheduled for follow-up audit per #24"; new Codex prompt file `prompts/zeitung-all-pages-audit.md` (no priming hints per `feedback_review_no_code_in_prompt.md`); two Codex runs (pre-fix iter1 verification + post-fix iter2 verification) saved to `reviews/codex-zeitung-all-pages-iter{1,2}.md`; INJECT_MAP one-loop fix (read live `frame.w_mm` / `frame.h_mm` instead of literal target tuples); `bin/render-gallery zeitung-a4-grun --skip-visual-diff` + meta.yml SHA bump; 10 invariant tests in `ImageContentExtentInvariantTests` (test_zeitung_geometry.py) — pin rendered-content-extent ≈ frame-extent relationship per #23 invariant pattern; rule registry count bump 14 → 15 in `test_brand_constraints.py::RegistryTests`; EXECUTION.md.

Scope OUT (explicit per RESEARCH.md "Scope changes vs. ISSUE.md"): switching the 13 frames to non-default `scale_type`/`local_scale` math (root cause is INJECT_MAP drift, not scale_type — locked decision #1); refactor of `inject_into_frame` to read frame dims directly (too invasive — locked decision #15); use of `compute_aspect_fill` in #24's primary fix path (helper provided but not used — locked decision #8); fixes for the 3 unnamed Dunkelgrün polygons on pages 12/13/14 (they're solid-fill rectangles with no image content — rule explicitly skips them per locked decision #3); any non-letterbox class Codex surfaces in T04 (z-order, color contrast, off-center crop_focus, hyphenation — defer to #25 per pitfalls §8 / locked decision #10); promoting `bin/audit-alignment` to fatal CI step (defer per ISSUE.md "Out of scope"); other-template alignment encoding (#19/#20/#21 paused per ISSUE.md); re-authoring Zeitung's design.

No CONTEXT.md exists for this issue — decisions are per RESEARCH.md's 15-item locked-decision table. Where research conflicts with ISSUE.md (specifically ISSUE.md's "13 frames use scale_type=1, ratio=1 and Scribus letterboxes" framing), RESEARCH.md wins. The 13-frame count in ISSUE.md is also corrected: it's 10 photo frames + 3 unnamed Dunkelgrün polygons that don't render images (rule skips them).
</objective>

<context>
Issue: @.issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/ISSUE.md
Research: @.issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/RESEARCH.md
Pitfalls research: @.issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/research/pitfalls.md

<interfaces>
<!-- Executor: use these contracts directly. Do not re-explore the codebase for them. -->

# tools/sla_lib/builder/brand_constraints.py — current (post-#23, 14 rules; 15th joins in #24)
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"   # "error" | "warning"
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]: ...
# Registry pattern (brand_constraints.py:1052):
#   BRAND_CONSTRAINTS: list[BrandRule] = [_make_rule(_ColorPaletteRule, id=..., name=..., description=...), ...]
# Existing 14 rule ids (post-#23):
#   brand:color_palette, brand:font_family, brand:line_spacing_0.9, brand:hl_sl_distance_x2,
#   brand:logo_size_3M, brand:text_on_green, brand:bleed_3mm, brand:wahlkreuz_colored_bg,
#   brand:inside_page, brand:spine_safety, brand:bleed_coverage, brand:image_text_overlap,
#   brand:cover_extent_match, brand:visual_adjacency_drift
# After #24: + brand:image_fills_frame (15 total).

# tools/sla_lib/builder/primitives.py — ImageFrame DSL contract (verbatim slice)
@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE path (absolute or relative-to-SLA)
    image: str = ""           # alias for src; converter prefers `image=`
    layer: int = 1
    local_scale: tuple[float, float] = (1.0, 1.0)        # LOCALSCX, LOCALSCY
    local_offset_mm: tuple[float, float] = (0.0, 0.0)    # LOCALX, LOCALY
    local_rotation_deg: float = 0.0
    scale_type: int = 1       # SCALETYPE  (0=ScaleAuto/fit-to-frame; 1=Manual)
    ratio: int = 1            # RATIO       (1=preserve aspect; 0=stretch)
    pic_art: int = 1          # PICART      (1=visible)
    fill: Optional[str] = None        # PCOLOR (frame background fill; image-less frames carry only fill)
    line_color: Optional[str] = None  # PCOLOR2
    line_width_pt: float = 0          # PWIDTH
    inline_image_data: Optional[str] = None    # qCompress base64 (post-injection)
    inline_image_ext: Optional[str] = None     # "jpg" | "png"

# Inline-image encoding (primitives.py:750-761):
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    blob = struct.pack(">I", len(image_bytes)) + zlib.compress(image_bytes, 6)
    return base64.b64encode(blob).decode("ascii"), ext
# Reverse for tests/rule:
#   raw = base64.b64decode(b64); _len = struct.unpack(">I", raw[:4])[0]
#   img_bytes = zlib.decompress(raw[4:]); PIL.Image.open(BytesIO(img_bytes))

# Scribus SCALETYPE/RATIO matrix (verified pitfalls §3 against scribusproject/scribus master):
#   scale_type=0:           ScaleAuto = fit-to-frame (LOCALSCX/SCY honored verbatim;
#                           with JFIF density 300 + LOCALSCX=1, JPEG renders at JFIF-mm).
#   scale_type=1, ratio=1:  Manual + preserve-aspect = letterbox-INSIDE (qMin(xs, ys)).
#   scale_type=1, ratio=0:  Manual stretch = no aspect, distorts.
# Scribus has NO native "fill / cover" mode (Mantis #15448 still open as of 2026).

# tools/sla_lib/builder/library.py — the path that already sets scale_type=0
def inject_into_frame(frame, img: "LibraryImage", *,
                       target_w_mm: float, target_h_mm: float,
                       dpi: int = 300, quality: int = 80,
                       apply_watermark: bool = True) -> None:
    # Crops img to (target_w_mm × target_h_mm) aspect via crop_for_frame, embeds as inline JPEG.
    # SIDE EFFECTS:
    #   frame.inline_image_data = data
    #   frame.inline_image_ext = ext   # "jpg"
    #   frame.scale_type = 0           # ScaleAuto — image fits frame
    #   # Does NOT touch frame.ratio / local_scale / local_offset_mm
# Crop pipeline (library.py:326-433): JPEG saved with dpi=(300, 300); JFIF density
#   determines on-canvas size when LOCALSCX=1. Bytes-deterministic per Pillow==12.2.0.

# tools/sla_lib/builder/bbox.py — rotation-aware bbox (reuse from #22)
def rotated_bbox(x, y, w, h, deg) -> tuple[min_x, min_y, max_x, max_y]
def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]
# Used to derive is_full_bleed; never use raw item.x_mm + item.w_mm.

# tools/audit_alignment.py — current shape (post-#23)
@dataclass
class PageAuditReport:
    page_idx: int
    page_label: str
    master_name: str
    side: Optional[str]    # "left" | "right" | None
    n_primitives: int
    declared_pairs: list = field(default_factory=list)
    suspicious_pairs: list = field(default_factory=list)
    spine_warnings: list = field(default_factory=list)
    # NEW in T02:
    # image_extent_warnings: list[str] = field(default_factory=list)
@dataclass
class TemplateAuditReport:
    slug: str
    facing_pages: bool
    pages: list = field(default_factory=list)
    fatal_error: Optional[str] = None
    tolerance_suspicions: list = field(default_factory=list)
def _audit_doc(doc, constraints, axis_tol_mm, adjacency_tol_mm, slug="<doc>") -> TemplateAuditReport
def _report_has_findings(rep: TemplateAuditReport) -> bool
# CLI flags: <slug> | --all, --json, --md PATH, --output-dir DIR,
#            --axis-tol-mm 25.0, --adjacency-tol-mm 30.0, --strict
# After T02: + --check-image-extent (default ON, --no-check-image-extent disables).

# tools/sla_lib/builder/document.py — facing-pages surface
class Document: facing_pages: bool; pages: list[Page]; ...
class Page: width_pt; height_pt; bleed_mm; items; is_master; master_name; label; own_page
PT_TO_MM = 0.3527777777777778

# templates/zeitung-a4-grun/build.py — INJECT_MAP edit target (the only build.py edit in #24)
# build_preview() at line 2565+. INJECT_MAP literal at line 2573-2599:
#   "anname" -> ("library_id", target_w_mm, target_h_mm)
# Loop at line 2600-2613:
#   for page in doc.pages:
#       for frame in page.items:
#           if isinstance(frame, ImageFrame) and frame.anname in INJECT_MAP:
#               lib_id, w, h = INJECT_MAP[frame.anname]
#               img = library.load(lib_id, optional=True)
#               if img is None: continue
#               library.inject_into_frame(frame, img, target_w_mm=w, target_h_mm=h)
# T05 changes the value type to a bare string (asset_id) and reads
# target_w_mm=frame.w_mm, target_h_mm=frame.h_mm in the loop body.

# tools/sla_lib/tests/test_zeitung_geometry.py — invariant-pinning conventions (post-#23)
ROOT = Path(__file__).resolve().parents[3]                          # repo root
def _load_zeitung_doc():                                            # build_doc() — clean, no inline data
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.build_doc()
def _frame_by_anname(doc, anname) -> tuple[item, page]
# T07 adds: _load_zeitung_preview_doc() that calls mod.build_preview() (inline-injected variant)
#         + _content_extent_mm(frame) helper that decodes frame.inline_image_data via
#           qCompress-reverse + PIL and returns (rendered_w_mm, rendered_h_mm).

# templates/<slug>/meta.yml — brand_overrides shape (verbatim from
#   templates/postkarte-a6-kampagne/meta.yml:30-49):
#   brand_overrides:
#     - id: brand:<rule_id>
#       reason: >-
#         <multi-line block-scalar reason text — must reference issue # for traceability>
# T03 appends a brand:image_fills_frame entry to 7 non-Zeitung templates' meta.yml.

# tests/test_brand_constraints.py:53 — registry count canary
class RegistryTests(unittest.TestCase):
    def test_fourteen_rules_exact(self):
        self.assertEqual(len(BRAND_CONSTRAINTS), 14)
    def test_ids_are_canonical(self):
        ids = [r.id for r in BRAND_CONSTRAINTS]
        expected = {... 14 rule ids ...}
# T01 renames test_fourteen_rules_exact → test_fifteen_rules_exact, bumps count to 15,
# and adds "brand:image_fills_frame" to the expected set.

# .issues/config.yaml — commit format
# commits: format=conventional, prefix=true → "24: <type>(<scope>): <subject>"
</interfaces>

Key files (with line-level evidence in RESEARCH.md / pitfalls.md):
@tools/sla_lib/builder/brand_constraints.py — 14 existing rules; T01 inserts `_ImageFillsFrameRule` after `_VisualAdjacencyDriftRule` and adds the `_make_rule(...)` registry entry at the end of `BRAND_CONSTRAINTS` (line 1156-1170 region).
@tools/sla_lib/builder/library.py:436-500 — `inject_into_frame` (already sets `scale_type=0`); T01 adds `compute_aspect_fill(frame_w_mm, frame_h_mm, asset_w_px, asset_h_px, dpi=300) -> tuple[float, float]` helper alongside.
@tools/sla_lib/builder/bbox.py — `frame_bbox_mm` + `rotated_bbox` (rotation-aware; required for `is_full_bleed`).
@tools/sla_lib/builder/primitives.py:750-761 — `pack_inline_image` (T07's `_content_extent_mm` reverses this).
@tools/sla_lib/builder/document.py:376-378 — `own_page=0` cover semantics (rule must treat both edges as outer-bleed).
@tools/audit_alignment.py:175-184 — `_SpineSafetyRule` wire-in pattern (T02 mirrors this for `_ImageFillsFrameRule`).
@tools/audit_alignment.py:74-83 — `PageAuditReport` shape; T02 adds `image_extent_warnings: list = field(default_factory=list)`.
@tools/audit_alignment.py:415-424 — `_report_has_findings`; T02 extends to include `image_extent_warnings`.
@tools/audit_alignment.py:439-456 — CLI flags; T02 adds `--check-image-extent` / `--no-check-image-extent`.
@tools/sla_lib/tests/test_brand_constraints.py:53-79 — registry-count canary (14 → 15).
@tools/sla_lib/tests/test_zeitung_geometry.py — invariant-pinning conventions; T07 appends `ImageContentExtentInvariantTests` class.
@templates/zeitung-a4-grun/build.py:2565-2613 — `build_preview()` + `INJECT_MAP`; T05's atomic single-commit edit.
@templates/zeitung-a4-grun/meta.yml — `previews_for_sla` SHA target; auto-bumped by T06.
@templates/{postkarte-a6-kampagne,plakat-a1-hochformat,infostand-tent-card-a5-quer,themen-plakat-a3-quer,kandidat-falzflyer-din-lang,wahltag-tueranhaenger,wahlaufruf-postkarte-a6-quer}/meta.yml — T03 appends `brand:image_fills_frame` skip entry to all 7.
@bin/audit-alignment — 14-line shim (no edit; already calls `tools.audit_alignment.main`).
@bin/render-gallery + @bin/check-stale-previews — T06's regen + SHA-consistency gate.
@prompts/zeitung-visual-audit.md — EXISTS (#23's audit prompt with priming hints); T04 creates a NEW file `prompts/zeitung-all-pages-audit.md` per RESEARCH.md §9 / `feedback_review_no_code_in_prompt.md` — DO NOT reuse the priming-heavy prompt.
@reviews/codex-zeitung-visual.md — EXISTS (#23's Codex audit, the comparison baseline showing all 7 user-cited "white strip on outer print edge" findings); T04 reads it for cross-check.
@reviews/audit-zeitung.json — EXISTS (#23's audit JSON baseline).
</context>

<commit_format>
Format: conventional with issue-id prefix (per `.issues/config.yaml`).
Example: `24: feat(brand): add brand:image_fills_frame rule + library.compute_aspect_fill helper`
Pattern: `24: <type>(<scope>): <subject>`
Types: feat, fix, test, refactor, docs, chore, ci.
Scopes used in this plan: brand, builder, library, audit, brand_constraints, zeitung, templates, meta, reviews, docs, issues.
One commit per task (T01-T08). T05 is intentionally a single atomic commit covering the INJECT_MAP fix only — geometry change with no other scope. T06 is a single atomic commit covering all render-gallery artifacts (SLA + 14 PNGs + meta.yml SHA + mirror PNGs + preview.pdf + baseline.pdf — ≥25 files).
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="false">
<name>T01: Add brand:image_fills_frame rule + library.compute_aspect_fill helper + unit tests + registry-count bump</name>
<files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/builder/library.py, tools/sla_lib/tests/test_brand_image_fills_frame.py, tools/sla_lib/tests/test_brand_constraints.py</files>
<depends-on>none</depends-on>
<behavior>
After T01, `BRAND_CONSTRAINTS` contains 15 rules (was 14):
- ADDED: `_ImageFillsFrameRule` / id `brand:image_fills_frame`. Severity = `error` for full-bleed frames (rotation-aware bbox touches `±bleed`), severity = `warning` otherwise. Per locked decision #2.
- The rule walks every non-master `ImageFrame` and:
  1. Skips solid-fill frames (`not (item.image or item.src or item.inline_image_data)`) — these are the 3 unnamed Dunkelgrün polygons on Zeitung pages 12/13/14 + any other image-less ImageFrame across templates. Per locked decision #3.
  2. Resolves the asset's native pixel dims via PIL (inline path: qCompress reverse → PIL; disk path: PIL on `frame.image` resolved against template root). Wraps in try/except (`FileNotFoundError`, `UnidentifiedImageError`, `OSError`) — on failure emits one `warning` with message "asset missing/corrupt: <reason>" and continues.
  3. Computes rendered-content extent (mm) per Scribus draw semantics:
     - `scale_type=0`: `rw = aw_px * 25.4 / dpi * local_scale[0]`; `rh = ah_px * 25.4 / dpi * local_scale[1]` (DPI from inline JFIF density tag if present, else 300).
     - `scale_type=1, ratio=1`: `s = min(frame.w_mm / native_pt_w_mm, frame.h_mm / native_pt_h_mm)`; rw/rh scaled by s (centered letterbox-INSIDE).
     - `scale_type=1, ratio=0`: rendered = frame extent (stretch fills); skip — no letterbox possible.
  4. Computes gap: `gap_w = item.w_mm - rw`; `gap_h = item.h_mm - rh`; tolerance = `max(0.5, 0.01 * max(item.w_mm, item.h_mm))` (1% of long side, floor 0.5 mm). Per pitfalls §6.
  5. If `gap_w <= tol AND gap_h <= tol`: pass. Otherwise emit Violation with severity from `_is_full_bleed(frame_bbox_mm(item, page), page.bleed_mm or 3.0, page.width_pt × PT_TO_MM, page.height_pt × PT_TO_MM)` (`error` if any outer-bbox edge within 0.5 mm of `±bleed`, else `warning`).
  6. Violation message MUST include: frame anname, frame mm, rendered mm, gap mm, and a fix suggestion: `"update INJECT_MAP target to ({item.w_mm:.3f}, {item.h_mm:.3f}); or library.compute_aspect_fill(...) for non-INJECT path."`
- ADDED helper `library.compute_aspect_fill(frame_w_mm, frame_h_mm, asset_w_px, asset_h_px, dpi=300) -> tuple[float, float]` returning `(local_scale_x, local_scale_y)` for aspect-FILL (qMax) at `scale_type=0`. Both components return the SAME scalar (`max(frame_w_mm / asset_w_mm_at_dpi, frame_h_mm / asset_h_mm_at_dpi)`) — this is the "cover" math Scribus lacks natively. Per locked decision #8: helper is for FUTURE templates; #24's primary fix uses INJECT_MAP regen instead.
- Registry test in `test_brand_constraints.py::RegistryTests`: rename `test_fourteen_rules_exact` → `test_fifteen_rules_exact`, bump `assertEqual(len(BRAND_CONSTRAINTS), 14)` → 15, add `"brand:image_fills_frame"` to the `expected` set in `test_ids_are_canonical`.

NEW unit-test file `tools/sla_lib/tests/test_brand_image_fills_frame.py`. Use synthetic primitives (NOT Zeitung) — keeps unit tests fast (<1 s) and template-agnostic. Cover:
1. `test_empty_image_frame_skipped` — ImageFrame with `image=""` and `inline_image_data=None` → 0 violations (the 3-Dunkelgrün-polygon class).
2. `test_inline_jpeg_matched_dims_passes` — synthesize a tiny JPEG (PIL → BytesIO → bytes), `pack_inline_image` it onto a 100×100 mm frame at scale_type=0, JPEG sized at exactly 100×100 mm at 300 DPI → 0 violations.
3. `test_inline_jpeg_undersized_fails_warning` — same but JPEG sized 95×100 mm (5 mm narrower) on an interior column frame (NOT touching bleed) → 1 violation, severity `warning`, message includes `"5.0×0.0mm white margin"` and the suggested INJECT_MAP fix line.
4. `test_inline_jpeg_undersized_full_bleed_fails_error` — same JPEG but on a frame whose bbox reaches `-bleed` on the left → 1 violation, severity `error`.
5. `test_disk_image_resolved_against_template_root` — `frame.image = "themen/synthetic.jpg"` written to a tmp dir, `doc._template_root` (or equivalent) set to that dir → rule probes the disk path; missing file → 1 `warning`, present + matched dims → 0 violations.
6. `test_scale_type_1_ratio_1_letterbox_inside_detected` — image native 200×100 px on a 50×50 mm frame (aspect mismatch 2:1) at scale_type=1, ratio=1 → letterbox INSIDE produces gap; rule flags it. Per pitfalls §3 + §6 the dual aspect+dim predicate.
7. `test_scale_type_1_ratio_0_stretch_skipped` — same setup but ratio=0 → rule returns no violations (stretch fills exactly per pitfalls §3).
8. `test_compute_aspect_fill_returns_qmax_scalar` — `compute_aspect_fill(100, 100, 1000, 500, dpi=300)` returns `(s, s)` where `s = max(100 / (1000 * 25.4 / 300), 100 / (500 * 25.4 / 300))` (single qMax scalar; verifies cover math). Plus a wider-asset case + a taller-asset case + identity case.
9. `test_qcompress_roundtrip_decode` — encode a known JPEG via `pack_inline_image`, decode via the rule's reverse (or a public helper), assert decoded `Image.size == original.size`. Validates the qCompress-reverse path independent of rule logic.
10. `test_dpi_from_jfif_density` — write a JPEG with non-300 DPI (e.g. 150) via PIL `save(..., dpi=(150, 150))`, encode via `pack_inline_image`, install on a frame whose physical mm match the JPEG at 150 DPI → rule reads JFIF density and computes correct rendered-mm; 0 violations. Falls back to 300 if JFIF missing.

Also a synthetic-primitives Zeitung-equivalent regression: `test_zeitung_pre_fix_inject_map_drift_witnessed` — DO NOT add this in T01. The geometric witness lives in the FAILING T07 invariant tests (which fail before T05 land, pass after). T01's tests are template-agnostic per the "rule is GENERIC" contract.
</behavior>
<action>
Read `tools/sla_lib/builder/brand_constraints.py` end-to-end first to internalize the existing 14-rule pattern (frozen dataclass, `check(self, primitives, doc, constraints=None)`, helper imports from `bbox.py` and `primitives.py`, registry pattern via `_make_rule(...)` at line 1052+). Read `tools/sla_lib/builder/library.py:436-500` to understand `inject_into_frame`. Read `tools/sla_lib/builder/primitives.py:750-761` to internalize `pack_inline_image` (you'll reverse it).

**Step 1.** ADD `_ImageFillsFrameRule` after `_VisualAdjacencyDriftRule` (around line 1050). Skeleton from RESEARCH.md "Architecture patterns" §`_ImageFillsFrameRule` (consume verbatim, then complete):

```python
@dataclass(frozen=True)
class _ImageFillsFrameRule(BrandRule):
    tolerance_ratio_pct: float = 1.0   # 1% of longer frame side
    tolerance_mm: float = 0.5          # absolute floor

    def check(self, primitives, doc, constraints=None):
        from sla_lib.builder.primitives import ImageFrame
        from sla_lib.builder.bbox import frame_bbox_mm
        from sla_lib.builder.document import PT_TO_MM
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            for item in page.items:
                if not isinstance(item, ImageFrame):
                    continue
                # SKIP image-less ImageFrames (solid-fill polygons-as-frames).
                # Per locked decision #3 — covers the 3 unnamed Dunkelgrün
                # polygons on Zeitung pages 12/13/14 + any other template.
                if not (item.image or item.src or item.inline_image_data):
                    continue
                aw_px, ah_px, dpi = self._resolve_asset(item, doc)
                if aw_px is None:
                    violations.append(self._asset_warning(item, dpi))
                    continue
                rw, rh = self._rendered_extent_mm(item, aw_px, ah_px, dpi)
                if rw is None:
                    continue   # stretch (scale_type=1, ratio=0) — fills exactly
                gap_w = item.w_mm - rw
                gap_h = item.h_mm - rh
                long_side = max(item.w_mm, item.h_mm)
                tol = max(self.tolerance_mm,
                          self.tolerance_ratio_pct / 100.0 * long_side)
                if gap_w <= tol and gap_h <= tol:
                    continue
                bbox = frame_bbox_mm(item, page)
                pw_mm = page.width_pt * PT_TO_MM
                ph_mm = page.height_pt * PT_TO_MM
                bleed = float(page.bleed_mm or 3.0)
                sev = ("error" if self._is_full_bleed(bbox, bleed, pw_mm, ph_mm)
                       else "warning")
                violations.append(Violation(
                    rule_id=self.id,
                    severity=sev,
                    targets=(item.anname or f"<unnamed y={item.y_mm:.1f}>",),
                    message=(
                        f"frame {item.anname!r} ({item.w_mm:.1f}x{item.h_mm:.1f}mm) "
                        f"renders {rw:.1f}x{rh:.1f}mm — "
                        f"{gap_w:.1f}x{gap_h:.1f}mm white margin. "
                        f"Either: update INJECT_MAP target to "
                        f"({item.w_mm:.3f}, {item.h_mm:.3f}); or "
                        f"library.compute_aspect_fill(...) for non-INJECT path."
                    ),
                ))
        return violations

    # Helpers _resolve_asset, _rendered_extent_mm, _is_full_bleed, _asset_warning
    # all live below — full implementations per RESEARCH.md §_ImageFillsFrameRule
    # + pitfalls §1 (defensive try/except) + pitfalls §3 (Scribus draw matrix)
    # + pitfalls §17 (generic dimension-mismatch detector).
```

`_resolve_asset(item, doc)` resolves to `(aw_px, ah_px, dpi)`:
- If `item.inline_image_data`: `raw = base64.b64decode(item.inline_image_data); _len = struct.unpack(">I", raw[:4])[0]; img_bytes = zlib.decompress(raw[4:]); im = Image.open(BytesIO(img_bytes))`. `im.size = (w_px, h_px)`. DPI from `im.info.get("dpi", (300, 300))[0]` (defensive: cast to int, fallback 300 if missing/zero).
- Else if `item.image or item.src`: resolve against repo's template root. Use `getattr(doc, "_template_root", None)` if set, else default to `Path.cwd() / "templates" / <slug-from-doc>`. (For Zeitung in T05+T07's runtime, the inline path always wins — disk-path branch is for future templates.) Wrap `Image.open(path)` in try/except. Apply `ImageOps.exif_transpose(im).size` defensively per pitfalls §5.
- On any exception: return `(None, None, 300)` — caller emits one `warning`.

`_rendered_extent_mm(item, aw_px, ah_px, dpi)` → `(rw_mm, rh_mm) or (None, None)` per the 3-branch matrix in pitfalls §17 (verbatim — copy the dispatch).

`_is_full_bleed(bbox, bleed, pw_mm, ph_mm)` — bbox edges within 0.5 mm of any of `[-bleed, 0, pw_mm, ph_mm + bleed]` (rotation-aware bbox already factored in). Per pitfalls §7 reference.

`_asset_warning(item, dpi)` returns `Violation(rule_id=self.id, severity="warning", targets=(item.anname or "...",), message=f"asset missing/corrupt for {item.anname!r} (image={item.image!r}); cannot verify image_fills_frame")`.

**Step 2.** ADD registry entry at end of `BRAND_CONSTRAINTS` (line 1170 region, after `_VisualAdjacencyDriftRule`):

```python
    _make_rule(
        _ImageFillsFrameRule,
        id="brand:image_fills_frame",
        name="Image content fills frame extent",
        description=(
            "Each ImageFrame's rendered-content extent (computed from "
            "scale_type + local_scale + asset native dims) must reach the "
            "frame's outer extent within tolerance (1%% of long side, "
            "floor 0.5mm). Catches INJECT_MAP target drift after frame "
            "extents change (the post-#22/#23 Zeitung regression class) "
            "and aspect-mismatch letterboxing on scale_type=1+ratio=1. "
            "Severity ERROR for full-bleed frames (rotation-aware bbox "
            "touches ±bleed); WARNING otherwise. Image-less frames "
            "(solid-fill polygons) are skipped. Per-template skip via "
            "meta.yml::brand_overrides[brand:image_fills_frame]."
        ),
        severity="error",   # per-violation severity is computed dynamically
                            # in check(); registry severity is the default
                            # for any violation that escapes is_full_bleed
                            # carve-out (none currently).
    ),
```

**Step 3.** ADD `compute_aspect_fill` helper to `library.py` (right after `inject_into_frame` ends at line 500, before `regenerate` at line 503):

```python
def compute_aspect_fill(
    frame_w_mm: float,
    frame_h_mm: float,
    asset_w_px: int,
    asset_h_px: int,
    dpi: int = 300,
) -> tuple[float, float]:
    """Return (local_scale_x, local_scale_y) for aspect-FILL ("cover") at scale_type=0.

    Scribus has no native "fill / cover" image mode (Mantis #15448 still
    open as of 2026-05). Templates that don't use ``inject_into_frame``
    (which crops the asset to the frame aspect via crop_for_frame and
    sidesteps the issue) can use this helper to compute LOCALSCX/SCY for
    an aspect-fill render at scale_type=0.

    Returns the SAME scalar in both components (qMax of the per-axis
    scale ratios). The image will then OVERFLOW the frame on its long
    axis; pair with appropriate ``local_offset_mm`` to choose the crop
    window — but BEWARE pitfall #14 from #22 RESEARCH (DSL unit bug at
    LOCALSCX != 1: ``local_offset_mm`` is mm at LOCALSCX=1, not mm of
    frame translation). Issue #24 does NOT use this helper for Zeitung
    (locked decision #8); Zeitung uses ``inject_into_frame`` which
    pre-crops to the frame aspect.

    Args:
        frame_w_mm, frame_h_mm: target frame dims in mm.
        asset_w_px, asset_h_px: source image native dims in pixels.
        dpi: assumed JFIF density of the source. Default 300 matches
             ``crop_for_frame``'s output.

    Returns:
        ``(s, s)`` where ``s = max(frame_w_mm / asset_w_mm_at_dpi,
        frame_h_mm / asset_h_mm_at_dpi)``.
    """
    asset_w_mm = asset_w_px * 25.4 / dpi
    asset_h_mm = asset_h_px * 25.4 / dpi
    s = max(frame_w_mm / asset_w_mm, frame_h_mm / asset_h_mm)
    return (s, s)
```

**Step 4.** ADD unit-test file `tools/sla_lib/tests/test_brand_image_fills_frame.py` covering the 10 cases listed in <behavior>. Use the existing `_doc()` synthetic-Document helper pattern from `test_brand_constraints.py`. Build inline JPEGs in-memory via PIL → `BytesIO` → `pack_inline_image`. For the "matched dims" test, encode at `dpi=(300, 300)` and size = `(int(100 * 300 / 25.4), int(100 * 300 / 25.4))` px; assert 0 violations. For the "undersized" test, size at 95 mm wide → 5 mm gap → severity assertion. Use `assertAlmostEqual` with `delta=0.5` where comparing computed mm values.

**Step 5.** UPDATE `tools/sla_lib/tests/test_brand_constraints.py::RegistryTests`:
- Rename method `test_fourteen_rules_exact` → `test_fifteen_rules_exact`.
- Bump `self.assertEqual(len(BRAND_CONSTRAINTS), 14)` → `15`.
- Update docstring/comment to mention #24 (the 15th rule).
- In `test_ids_are_canonical`, add `"brand:image_fills_frame",  # Issue #24` to the `expected` set.

**Step 6.** Run T01 verification (see <verify>). All tests must pass. Then commit:
`24: feat(brand): add brand:image_fills_frame rule + library.compute_aspect_fill helper`
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_brand_image_fills_frame -v</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_brand_constraints.RegistryTests -v</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -c "from sla_lib.builder.brand_constraints import BRAND_CONSTRAINTS; ids=[r.id for r in BRAND_CONSTRAINTS]; assert 'brand:image_fills_frame' in ids and len(ids)==15, ids; print('OK', len(ids), 'rules')"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -c "from sla_lib.builder.library import compute_aspect_fill; sx, sy = compute_aspect_fill(100, 100, 1000, 500, dpi=300); assert sx == sy and sx > 1.18 and sx < 1.19, (sx, sy); print('OK', sx)"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -5</automated>
</verify>
<done>
- `BRAND_CONSTRAINTS` has 15 entries; new id `brand:image_fills_frame` is in the set; registry test passes.
- `_ImageFillsFrameRule` correctly skips image-less frames, handles inline + disk paths, computes rendered-extent for all 3 SCALETYPE/RATIO branches, dynamically severities `error` vs `warning` via `_is_full_bleed`.
- `library.compute_aspect_fill(...)` returns `(s, s)` qMax scalar; documented as #24 deferred-use helper.
- All 10 unit tests in `test_brand_image_fills_frame.py` pass; full `unittest discover` exits 0.
- Discovery: full test suite stays green (no regression in the other 14 rules' tests).
</done>
<dont>
- Don't hardcode any Zeitung anname (`"Cover Hero"`, `"P10 Portrait"`, etc.) inside the rule code. Per ISSUE.md AC + locked decision (rule is GENERIC). Match by predicate, not by string.
- Don't refactor `inject_into_frame` to read `frame.w_mm` directly. Per locked decision #15 — too invasive; deferred future work. T05's INJECT_MAP loop change is the right surface.
- Don't use `compute_aspect_fill` in any Zeitung code path in this issue. Per locked decision #8 — helper is for future templates that don't use `inject_into_frame`.
- Don't compute `is_full_bleed` from raw `item.x_mm + item.w_mm` — use `frame_bbox_mm(item, page)` (rotation-aware). Several Zeitung frames are rotated 90°. Per pitfalls §7 + #22 RESEARCH precedent.
- Don't trust `Page.is_left` — it's hardcoded `False` in `document.py:391-393`. The rule doesn't need page-side detection (full-bleed predicate works on either side via `±bleed` symmetry).
- Don't promote the registry severity to `warning` to "be safer" — keep `severity="error"` so `structural_check --all` exits 1 for any non-bleed-carved violation. Severity dynamic carve happens INSIDE `check()` via `_is_full_bleed`.
- Don't omit the `ImageOps.exif_transpose` defensive call on the disk-path branch — pitfalls §5 says it's a 1-line cheap insurance for end-user assets.
- Don't synthesize JPEGs via raw bytes literals in unit tests — use `PIL.Image.new(...) → BytesIO → save(format="JPEG", dpi=(300,300))` so JFIF density tests reflect production encoding.
</dont>
</task>

<task id="T02" type="auto" tdd="false">
<name>T02: Wire _ImageFillsFrameRule into audit_alignment.py + add --check-image-extent CLI flag + extend PageAuditReport</name>
<files>tools/audit_alignment.py, tools/sla_lib/tests/test_audit_alignment.py</files>
<depends-on>T01</depends-on>
<behavior>
After T02:
- `tools/audit_alignment.py:_audit_doc()` calls `_ImageFillsFrameRule(...).check(primitives, doc, constraints=constraints)` after the existing `_SpineSafetyRule` block (line ~175-184). Distributes violations into per-page `image_extent_warnings: list[str]` on each `PageAuditReport`. Per locked decision #6 (Option A from codebase agent §7 — mirrors the spine-safety wire-in pattern verbatim).
- `PageAuditReport` dataclass gains `image_extent_warnings: list = field(default_factory=list)`.
- `_report_has_findings(rep)` returns True if any page has `image_extent_warnings` (so `--strict` exits 1 on any image-extent finding).
- `report_to_markdown()` emits a per-page `### Image-fills-frame warnings (N)` section listing each warning verbatim, after the `spine_warnings` section.
- `report_to_json()` includes per-page `"image_extent_warnings": pr.image_extent_warnings` in the page dict.
- CLI gains `--check-image-extent` (default `True`) and `--no-check-image-extent` (sets `False`). When False, the rule is NOT invoked (skip the loop entirely).
- New unit-test class in `test_audit_alignment.py`: `ImageExtentAuditTests` with at least 3 tests:
  1. `test_audit_doc_emits_image_extent_warnings_when_jpeg_undersized` — synthetic doc with one ImageFrame + undersized inline JPEG → audit report has 1 entry in `pages[0].image_extent_warnings` + `_report_has_findings(rep)` returns True.
  2. `test_audit_doc_skips_check_when_disabled` — call `_audit_doc(..., check_image_extent=False)` → 0 entries.
  3. `test_cli_no_check_image_extent_flag_disables` — invoke `main(["<slug>", "--no-check-image-extent", "--strict"])` against a Zeitung-like fixture (or a small synthetic) where the rule WOULD fire; with the flag, exit 0.
</behavior>
<action>
Read `tools/audit_alignment.py` end-to-end first (it's ~500 lines). Note the `_SpineSafetyRule` wire-in at line 174-184 — that's the canonical pattern to mirror.

**Step 1.** Add field to `PageAuditReport` (line 73-83):
```python
@dataclass
class PageAuditReport:
    page_idx: int
    page_label: str
    master_name: str
    side: Optional[str]
    n_primitives: int
    declared_pairs: list = field(default_factory=list)
    suspicious_pairs: list = field(default_factory=list)
    spine_warnings: list = field(default_factory=list)
    image_extent_warnings: list = field(default_factory=list)   # Issue #24
```

**Step 2.** Extend `_audit_doc()` signature with `check_image_extent: bool = True` keyword. After the spine-rule block (around line 184), add:

```python
    # Issue #24: image-fills-frame check (catches INJECT_MAP drift +
    # aspect-mismatch letterboxing). Per-page distribution mirrors
    # the spine_by_target pattern above.
    image_extent_by_target: dict = {}
    if check_image_extent:
        from sla_lib.builder.brand_constraints import _ImageFillsFrameRule
        rule = _ImageFillsFrameRule(
            id="brand:image_fills_frame", name="", description="",
        )
        for v in rule.check(list(doc.iter_all_primitives()), doc,
                            constraints=constraints):
            for t in v.targets:
                image_extent_by_target.setdefault(t, []).append(
                    f"[{v.severity.upper()}] {v.message}"
                )
```

**Step 3.** Inside the per-page loop (around line 274 where `spine_warnings.extend(...)` happens), add a parallel pop+extend:

```python
        if image_extent_by_target:
            for an in [getattr(it, "anname", "") for it in page.items]:
                if an and an in image_extent_by_target:
                    page_rep.image_extent_warnings.extend(
                        image_extent_by_target.pop(an)
                    )
```

After the page loop (around line 282 where leftover spine warnings get attached to page 0), do the same for image-extent leftovers.

**Step 4.** Update `audit_template()` (the `_audit_doc` caller — find via `grep -n "def audit_template"`) to forward `check_image_extent` if the call site passes it. `audit_all()` should default it to True. Same for any other public entry point.

**Step 5.** Update `_report_has_findings(rep)` (line 415-424):

```python
def _report_has_findings(rep: TemplateAuditReport) -> bool:
    if rep.fatal_error: return True
    if rep.tolerance_suspicions: return True
    for pr in rep.pages:
        if pr.suspicious_pairs or pr.spine_warnings or pr.image_extent_warnings:
            return True
    return False
```

**Step 6.** Update `report_to_markdown()` per-page section to include `image_extent_warnings`. Use the same shape as the spine-warnings block (around line 365-369) — emit `### Image-fills-frame warnings (N)` then a `- ` bullet per entry.

**Step 7.** Update `report_to_json()` to include `"image_extent_warnings": pr.image_extent_warnings` in the per-page JSON dict (around line 408).

**Step 8.** Add CLI flag in `main()` (around line 450-456):

```python
    ap.add_argument(
        "--check-image-extent", dest="check_image_extent",
        action="store_true", default=True,
        help=("Check image-content-fills-frame extent via "
              "brand:image_fills_frame (default: on). Issue #24."),
    )
    ap.add_argument(
        "--no-check-image-extent", dest="check_image_extent",
        action="store_false",
        help="Disable the image-fills-frame check.",
    )
```

Forward `ns.check_image_extent` into `audit_template(...)` / `audit_all(...)` calls.

**Step 9.** ADD unit-test class to `tools/sla_lib/tests/test_audit_alignment.py`. Mirror the existing test patterns; build a synthetic `Document` with a facing-pages `Page` containing one `ImageFrame` with an inline JPEG that's 5 mm undersized vs the frame. Use the same JPEG-synthesis helper from T01's tests (extract a shared helper to `_test_helpers.py` if convenient, or inline-duplicate — both acceptable for this codebase). Assert:
- `audit_template(<synthetic-slug>).pages[0].image_extent_warnings` has 1 entry.
- That entry contains the substring `"5.0x0.0mm white margin"` (or the equivalent format string from T01's rule).
- `_report_has_findings(rep)` returns True.
- With `--no-check-image-extent`, the warning list is empty AND `_report_has_findings` returns False (assuming no other findings).

For the CLI test (test #3), use `audit_alignment.main(["zeitung-a4-grun", "--no-check-image-extent"])` against the live Zeitung — should exit 0 even pre-T05 (rule not invoked). Without `--no-check-image-extent`, the rule fires and reports the 7 INJECT_MAP-drift findings (this is the FAILING WITNESS, by design — T05 fixes it). The test should NOT assert clean output pre-T05; it should assert that the flag controls invocation.

**Step 10.** Verify (see <verify>). Commit:
`24: feat(audit): wire image_fills_frame into audit_alignment + --check-image-extent flag`
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_audit_alignment -v 2>&1 | tail -20</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --no-check-image-extent --strict; echo "EXIT_NOCHECK=$?"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --json 2>/dev/null | python3 -c "import json, sys; d=json.load(sys.stdin); pages=d.get('pages', []); n=sum(len(p.get('image_extent_warnings', [])) for p in pages); print('image_extent_warnings_total:', n)"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -c "import audit_alignment as a; assert hasattr(a.PageAuditReport, '__dataclass_fields__') and 'image_extent_warnings' in a.PageAuditReport.__dataclass_fields__; print('OK')"</automated>
</verify>
<done>
- `PageAuditReport.image_extent_warnings` field present.
- `_audit_doc(..., check_image_extent=True)` populates the field; `False` skips invocation.
- `_report_has_findings` returns True when `image_extent_warnings` non-empty.
- CLI `--check-image-extent` / `--no-check-image-extent` flag works.
- JSON output includes `image_extent_warnings` per page.
- Markdown output includes `### Image-fills-frame warnings` section per page.
- `audit-alignment zeitung-a4-grun --no-check-image-extent --strict` exits 0 PRE-T05 (verifies the gating works).
- `audit-alignment zeitung-a4-grun --strict` (default) exits 1 PRE-T05 with 7 image_extent_warnings findings (the FAILING WITNESS; this is intentional — T05 fixes it). Document this in commit message.
- Unit tests pass.
</done>
<dont>
- Don't change existing CLI behavior for any flag besides `--check-image-extent` / `--no-check-image-extent`. The existing `--axis-tol-mm`, `--adjacency-tol-mm`, `--strict` keep their #23 semantics.
- Don't import `_ImageFillsFrameRule` at module level in `audit_alignment.py` — keep the import inside the `if check_image_extent:` block per the existing pattern (which lazy-imports rules to avoid circular import risk).
- Don't add a separate top-level `image_extent_warnings` on `TemplateAuditReport` — keep them per-page (mirrors `spine_warnings` shape).
- Don't try to fix Zeitung's INJECT_MAP in this task (T05 owns that). T02 expects the audit to FAIL on Zeitung post-T02 — that's the witness the planning relies on.
- Don't combine T02 with T03 — T02 wires the detector, T03 silences it on non-Zeitung templates so `--all` stays green. Separating keeps the bisect-friendly diff.
</dont>
</task>

<task id="T03" type="auto" tdd="false">
<name>T03: Pre-apply brand_overrides[brand:image_fills_frame] to 7 non-Zeitung templates</name>
<files>templates/postkarte-a6-kampagne/meta.yml, templates/plakat-a1-hochformat/meta.yml, templates/infostand-tent-card-a5-quer/meta.yml, templates/themen-plakat-a3-quer/meta.yml, templates/kandidat-falzflyer-din-lang/meta.yml, templates/wahltag-tueranhaenger/meta.yml, templates/wahlaufruf-postkarte-a6-quer/meta.yml</files>
<depends-on>T02</depends-on>
<behavior>
After T03, all 7 non-Zeitung templates carry an explicit `brand:image_fills_frame` skip in `brand_overrides`, with reason text "Scheduled for follow-up audit per #24 — image-fills-frame check added in #24 surfaces letterbox/INJECT_MAP-drift class globally; per-template review for fix-vs-override classification deferred to follow-up issue (#25)." This keeps `python3 -m sla_lib.builder.structural_check --all` exit 0 throughout the PR (Zeitung itself does NOT get a skip — the rule must fire there pre-T05 as the fix witness, and pass post-T05 as the verification).

Per locked decision #7 (atomic-PR ordering). The 7 templates are the exact set per RESEARCH.md §locked-decision #7 and pitfalls §12.
</behavior>
<action>
Read `templates/postkarte-a6-kampagne/meta.yml` (lines 30-49) to confirm the `brand_overrides` shape — it's a YAML list of `{id: brand:..., reason: >- ...}` dicts. Pattern from #23 T02 is the verbatim model.

For EACH of the 7 templates, append the following entry to `brand_overrides` (preserving any existing entries — APPEND only, do not replace):

```yaml
  - id: brand:image_fills_frame
    reason: >-
      Scheduled for follow-up audit per #24 — image-fills-frame check
      added in #24 surfaces letterbox/INJECT_MAP-drift class globally;
      per-template review for fix-vs-override classification deferred
      to follow-up issue (#25). Zeitung is the only template with
      verified clean image-content extents post-#24.
```

YAML emission rules: 4-space indent under `brand_overrides:`; the `reason: >-` block scalar uses 6-space continuation (matches existing entries verbatim). Use the existing entries in `templates/postkarte-a6-kampagne/meta.yml:45-49` as the byte-precise model.

For `templates/wahlaufruf-postkarte-a6-quer/meta.yml` specifically: that template ALREADY has a `brand:image_text_overlap` override (line 31+ per the live grep). Just APPEND `brand:image_fills_frame` after the last existing entry — do NOT touch the existing entries. (Note: #23 noted wahlaufruf was already-merged at #17 time and not given the #23 image_text_overlap override; #24 IS giving it an image_fills_frame override because the rule fires on this template too. Verified live: it already has image_text_overlap from a prior commit — append cleanly.)

For `templates/zeitung-a4-grun/meta.yml`: DO NOT add a `brand:image_fills_frame` skip. The rule MUST fire on Zeitung pre-T05 (the witness) and pass post-T05 (the fix). Verify by greppping `zeitung-a4-grun/meta.yml` for `brand:image_fills_frame` — must return nothing after T03.

Verify (see <verify>). Commit:
`24: chore(meta): pre-apply brand_overrides[brand:image_fills_frame] to 7 non-Zeitung templates`
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && for t in postkarte-a6-kampagne plakat-a1-hochformat infostand-tent-card-a5-quer themen-plakat-a3-quer kandidat-falzflyer-din-lang wahltag-tueranhaenger wahlaufruf-postkarte-a6-quer; do grep -q "brand:image_fills_frame" "templates/$t/meta.yml" && echo "OK $t" || echo "MISSING $t"; done</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && grep -c "brand:image_fills_frame" templates/zeitung-a4-grun/meta.yml; echo "(expect 0; non-zero means Zeitung was wrongly skip-applied)"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && for t in postkarte-a6-kampagne plakat-a1-hochformat infostand-tent-card-a5-quer themen-plakat-a3-quer kandidat-falzflyer-din-lang wahltag-tueranhaenger wahlaufruf-postkarte-a6-quer zeitung-a4-grun; do python3 -c "import yaml; d=yaml.safe_load(open('templates/$t/meta.yml').read()); print('$t', 'parses OK', 'overrides=', [o.get('id') for o in (d.get('brand_overrides') or [])])"; done</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -10; echo "EXIT=$?"</automated>
</verify>
<done>
- All 7 non-Zeitung templates have a `brand:image_fills_frame` entry under `brand_overrides`, with the standard reason text referencing #24 + #25.
- Zeitung's `meta.yml` is UNCHANGED (no `brand:image_fills_frame` entry — the rule must fire there).
- All 8 meta.yml files parse as valid YAML.
- `structural_check --all` exits 0 (the 7 non-Zeitung templates skip the rule via override; Zeitung still has the 7 INJECT_MAP-drift violations BUT they are dynamic-severity warnings on interior frames and dynamic-severity errors on full-bleed frames; the 7 dynamic-severity errors WILL fail structural_check until T05 fixes the INJECT_MAP. **EXPECTED**: structural_check exits 1 on Zeitung between T03 and T05. T05 fixes it.)
- Document in commit message: "Zeitung structural_check is RED until T05 lands — by design (TDD-for-rules witness)."
</done>
<dont>
- Don't add the override to `zeitung-a4-grun/meta.yml`. The rule must fire there as the fix witness.
- Don't change the reason text wording across the 7 templates — keep it verbatim for grep-ability + audit traceability.
- Don't reorder existing `brand_overrides` entries when appending — APPEND only.
- Don't combine this commit with the rule-add (T01) or audit-wire (T02). Bisect-friendly granularity.
- Don't try to make `structural_check --all` exit 0 between T03 and T05 by also adding a Zeitung-temporary override — that would defeat the purpose. The intermediate RED state is intentional and only lives 2 commits.
</dont>
</task>

<task id="T04" type="auto" tdd="false">
<name>T04: Codex visual audit of all 14 Zeitung pages — pre-fix baseline (verification gate)</name>
<files>prompts/zeitung-all-pages-audit.md, reviews/codex-zeitung-all-pages-iter1.md, reviews/audit-zeitung-pre-fix.json</files>
<depends-on>T03</depends-on>
<behavior>
After T04: a NEW Codex prompt (no priming hints per `feedback_review_no_code_in_prompt.md` + locked decision #14) has been authored at `prompts/zeitung-all-pages-audit.md`. Codex has executed the prompt against the existing 14 Zeitung page-NN.png files (the PRE-FIX renderings — INJECT_MAP drift still present). Output saved to `reviews/codex-zeitung-all-pages-iter1.md`. The audit JSON has been captured to `reviews/audit-zeitung-pre-fix.json` for cross-check.

The cross-check produces a verdict:
- If every Codex-flagged alignment defect maps to ONE OR MORE entries in `audit-zeitung-pre-fix.json::pages[*].image_extent_warnings` (or the existing `suspicious_pairs` / `spine_warnings` from #22/#23): PASS — proceed to T05.
- If Codex flags a class the audit MISSES (e.g. a frame whose extent is wrong but `_ImageFillsFrameRule` doesn't catch it; OR a different alignment class entirely like z-order, color-contrast, off-center crop_focus): the executor STOPS, returns to T01, strengthens `_ImageFillsFrameRule` predicate (max 1 strengthening cycle per locked decision #10 / pitfalls §9), then re-runs T04 (iter2 → `reviews/codex-zeitung-all-pages-iter1b.md`).
- After 2 cycles total (iter1 + iter1b) of T04, if Codex STILL surfaces a class the audit misses, document the gap in EXECUTION.md (drafted in T08), classify it per pitfalls §8 (a/b/c table), defer class (c) issues to #25 — DO NOT extend #24 scope further.

The Codex run is invoked via `issue-cli review-exec --tool codex --prompt prompts/zeitung-all-pages-audit.md --name zeitung-all-pages-iter1 --review-type topic --review-mode topic --output-dir reviews/`. Per RESEARCH.md §15: ~3-5 min wall time per run.
</behavior>
<action>
**Step 1.** Author `prompts/zeitung-all-pages-audit.md` from scratch — DO NOT reuse `prompts/zeitung-visual-audit.md` (which has priming hints "KNOWN issues: page 1 cover image vs full-bleed band..." that bias Codex). The new prompt enumerates all 14 pages neutrally:

```markdown
# Zeitung A4 — visual alignment audit (all 14 pages)

Read each rendered preview page in
`templates/zeitung-a4-grun/page-{01,02,03,04,05,06,07,08,09,10,11,12,13,14}.png`
(zero-padded; 14 pages total). You MUST open each PNG file and visually
inspect it. Do not skip pages. Do not infer content from filenames.

For EACH page, enumerate every alignment defect you observe. Report
neutrally — do not assume any particular defect class is more or less
likely. Use this Markdown structure per finding:

- Page: NN
- Type: bleed-gap | letterbox | flush-mismatch | column-axis-drift | spread-seam | partial-overlap | other
- Frames involved: <verbal description by visual position; frame names
  if recognizable from layout>
- What's wrong: <one factual sentence>
- Drift estimate: <X mm if measurable, else "qualitative">
- Severity: ERROR (visible after print cut) | WARNING (visible but not catastrophic)

If a page has no defects, write `- Page: NN — clean`.

End the report with a single verdict block:

<verdict value="pass|fail" critical=N high=N medium=N>

`pass` = no ERROR findings; `fail` = at least one ERROR finding.

Source context: this template is a 14-page A4 facing-pages newsletter.
Pages are 210x297 mm with 3 mm bleed on all outer edges. Inner edges
(spine) are at the page boundary. Facing-pages spreads share content
across two pages.

Output the structured list AS YOUR PRIMARY MESSAGE; do not just save
to disk. Do NOT consult any rule/audit JSON; read the images fresh.
```

**Step 2.** Capture the pre-fix audit JSON for cross-check:
```bash
PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --json > reviews/audit-zeitung-pre-fix.json
```

**Step 3.** Invoke Codex (background-OK):
```bash
issue-cli review-exec \
  --tool codex \
  --prompt prompts/zeitung-all-pages-audit.md \
  --name zeitung-all-pages-iter1 \
  --review-type topic \
  --review-mode topic \
  --topic "Zeitung A4 visual alignment audit (Issue #24 pre-fix baseline)" \
  --output-dir reviews/
```

The output file will land at something like `reviews/review-<timestamp>-zeitung-all-pages-iter1-<model>.md`. Copy/rename it to `reviews/codex-zeitung-all-pages-iter1.md` for stable referencing.

**Step 4.** Cross-check — for each Codex finding (page + type + frame description), verify it has a corresponding entry in:
- `reviews/audit-zeitung-pre-fix.json::pages[idx].image_extent_warnings` (the new T02 channel — should catch every "bleed-gap" / "letterbox" finding), OR
- `pages[idx].suspicious_pairs` (legacy #23 channel for adjacency drift), OR
- `pages[idx].spine_warnings` (legacy #22 channel for spine), OR
- `tolerance_suspicions` (legacy #23 channel).

Document the cross-check inline in `reviews/codex-zeitung-all-pages-iter1.md` by appending a `## Cross-check vs. audit JSON` section listing each Codex finding and its mapping (or "MISSING — class X").

**Step 5.** GATE DECISION:
- If 0 MISSING entries → PROCEED to T05.
- If ≥1 MISSING entries of class (b) (per pitfalls §8 table — letterbox/bleed-gap variant the rule didn't catch) → STOP. Return to T01. Strengthen `_ImageFillsFrameRule.check()` (e.g. lower the tolerance, add aspect-only signal, broaden the inline-data probe). Increment unit tests. Re-run T01 verifies. Re-run T04 with `--name zeitung-all-pages-iter1b` → `reviews/codex-zeitung-all-pages-iter1b.md`. Cross-check again.
- If ≥1 MISSING entries of class (c) (per pitfalls §8 — z-order, color-contrast, off-center, hyphenation, font-size-inconsistency, etc.): document in EXECUTION.md (T08 will draft) and DEFER to #25. Do NOT extend #24 scope. Continue to T05.
- After 2 total Codex cycles (iter1 + optional iter1b), STOP iterating regardless of result. Per locked decision #10.

**Step 6.** Commit:
`24: docs(reviews): Codex visual audit all 14 Zeitung pages — pre-fix baseline (iter1)`

If iter1b ran: include both `reviews/codex-zeitung-all-pages-iter1b.md` AND any rule-strengthening commits BEFORE the T04 commit. The T04 commit is the FINAL pre-fix Codex artifact + cross-check.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && test -f prompts/zeitung-all-pages-audit.md && wc -l prompts/zeitung-all-pages-audit.md</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && test -f reviews/codex-zeitung-all-pages-iter1.md && wc -l reviews/codex-zeitung-all-pages-iter1.md</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && test -f reviews/audit-zeitung-pre-fix.json && python3 -c "import json; d=json.load(open('reviews/audit-zeitung-pre-fix.json')); n=sum(len(p.get('image_extent_warnings', [])) for p in d.get('pages', [])); print('image_extent_warnings_total:', n); assert n >= 5, f'expected >=5 pre-fix warnings, got {n}'"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && grep -q "## Cross-check vs. audit JSON" reviews/codex-zeitung-all-pages-iter1.md && echo "cross-check section present" || echo "MISSING cross-check section"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && grep -E "verdict value" reviews/codex-zeitung-all-pages-iter1.md | head -3</automated>
</verify>
<done>
- `prompts/zeitung-all-pages-audit.md` exists, ~30 lines, no priming hints (does NOT mention "KNOWN issues" or any specific pages 1/8/10/11 priming).
- `reviews/codex-zeitung-all-pages-iter1.md` exists, contains per-page findings for all 14 pages, ends with a `<verdict value=...>` block.
- `reviews/audit-zeitung-pre-fix.json` exists, contains ≥5 image_extent_warnings entries across pages (the pre-fix INJECT_MAP-drift witness; expected ~7 per RESEARCH.md drift table).
- Cross-check section appended to `codex-zeitung-all-pages-iter1.md` mapping each Codex finding to audit JSON (or marking MISSING).
- GATE PASSED: zero class-(b) MISSING entries (or, after iter1b, still zero).
- If iter1b ran: rule-strengthening commit precedes the T04 docs commit.
- If class-(c) findings exist: documented for T08 EXECUTION.md drafting; NOT addressed in #24.
</done>
<dont>
- Don't reuse `prompts/zeitung-visual-audit.md` from #23 — it primes Codex with the user-cited pages list, biasing toward known classes. Per `feedback_review_no_code_in_prompt.md` + locked decision #14.
- Don't include the rule code or the INJECT_MAP table in the Codex prompt. Codex must read the PNGs fresh (per `feedback_review_no_code_in_prompt.md`).
- Don't iterate past 2 Codex cycles. Per locked decision #10 — beyond 2 signals the rule's underlying model is wrong; ship + defer.
- Don't try to "convince" Codex its findings are wrong. If it sees something the audit misses, the audit is the one that needs strengthening (or the finding is class-(c) deferred to #25).
- Don't treat class-(c) findings as blocking. Per pitfalls §8 — z-order/contrast/crop_focus issues are real defects but OUT OF SCOPE for #24 (which is letterbox/extent only).
- Don't hand-edit the Codex output. The raw markdown is the artifact. Append the cross-check section as a clearly-marked `## Cross-check vs. audit JSON` block at the BOTTOM, after Codex's verdict.
- Don't proceed to T05 if the GATE FAILS (class-b MISSING entries persist after 2 cycles). Escalate to user instead — possible new rule class needed.
</dont>
</task>

<task id="T05" type="auto" tdd="false">
<name>T05: Fix Zeitung INJECT_MAP — read live frame.w_mm/h_mm instead of literal targets (atomic ~30-line change)</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T04</depends-on>
<behavior>
After T05: `templates/zeitung-a4-grun/build.py:2573-2613` (the `INJECT_MAP` literal + the loop that consumes it) is rewritten so that EACH entry's value is a bare library asset id (string), and the loop body reads the target dims from the actual frame at injection time:

```python
INJECT_MAP = {
    # anname -> library_id. Target dims are READ FROM THE FRAME at
    # injection time (see loop below). Issue #24 fix: prior to #24 each
    # entry was (lib_id, target_w_mm, target_h_mm) and the literal target
    # tuples drifted out of sync with frame.w_mm / frame.h_mm after #22
    # T12 (spine inset) and #23 T07 (outer-bleed extension), causing
    # rendered content to land 3-11 mm short of frame edges (white
    # pillarbox margins). Reading live frame dims removes the drift
    # surface entirely. The brand:image_fills_frame rule (added in #24)
    # catches future regressions of this class.
    "Cover Hero":          "themen_klimaschutz_windrad",
    "P1 Hero":             "themen_soziales_gemeindebau",
    "P2 Mid":              "themen_bildung_volksschule",
    "P3 Hero":             "themen_wirtschaft_handwerk",
    "P4 Foto-Spread":      "kontext_buergerversammlung",
    "P5 Hero":             "themen_verkehr_radweg",
    "P7 Portrait":         "portrait_maria",
    "P9 Spread · left":    "themen_klimaschutz_solar",
    "P9 Spread · right":   "themen_klimaschutz_solar",
    "P10 Portrait":        "portrait_stefan",
    "P11 Bottom":          "kontext_stammtisch_cafe",
    "P13 Hero":            "kontext_infostand_szene",
}
for page in doc.pages:
    for frame in page.items:
        if isinstance(frame, ImageFrame) and frame.anname in INJECT_MAP:
            lib_id = INJECT_MAP[frame.anname]
            img = library.load(lib_id, optional=True)
            if img is None:
                continue  # library bytes not yet generated
            # inject_into_frame handles crop + pack + sets scale_type=0.
            # Reading frame.w_mm/h_mm live (Issue #24 fix) keeps the
            # injected JPEG's dims in lockstep with the frame extent
            # whenever templates/zeitung-a4-grun/build.py edits the
            # frame geometry. No more INJECT_MAP target drift.
            library.inject_into_frame(
                frame, img,
                target_w_mm=frame.w_mm,
                target_h_mm=frame.h_mm,
            )
```

Pure refactor of the dict literal + loop body. Per locked decisions #1 + #15: NO `scale_type` change, NO `local_scale` change, NO refactor to `inject_into_frame` itself, NO use of `compute_aspect_fill`. Single atomic commit.

Post-T05, `bin/audit-alignment zeitung-a4-grun --strict` MUST exit 0 (zero `image_extent_warnings`).
</behavior>
<action>
Read `templates/zeitung-a4-grun/build.py:2565-2615` first to confirm the current state matches the interfaces snapshot (the file may have minor drift between research and execute).

**Step 1.** REPLACE the `INJECT_MAP` literal (line 2573-2599) and the loop body (line 2600-2613) with the post-fix version above. Preserve:
- The `# anname → ...` style of comments (German UTF-8 OK; existing file is UTF-8).
- The `library.load(lib_id, optional=True)` + `if img is None: continue` early-return for unbuilt library bytes.
- The function structure: `def build_preview():` → `doc = build_template()` → `INJECT_MAP = { ... }` → `for page ... :` → `return doc`.

The 12 INJECT_MAP keys MUST match the existing keys 1:1 (no add, no drop, no rename — verified against the live file). Same library_id values per existing entries: `themen_klimaschutz_windrad`, `themen_soziales_gemeindebau`, `themen_bildung_volksschule`, `themen_wirtschaft_handwerk`, `kontext_buergerversammlung`, `themen_verkehr_radweg`, `portrait_maria`, `themen_klimaschutz_solar` (×2 for the spread halves), `portrait_stefan`, `kontext_stammtisch_cafe`, `kontext_infostand_szene`.

**Step 2.** Verify with the audit:
```bash
PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict
```
MUST exit 0 (zero image_extent_warnings AND zero of the other channels).

**Step 3.** Verify with structural_check:
```bash
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
```
MUST exit 0 (the rule was failing with errors on Zeitung between T03 and T05; T05 makes it green).

**Step 4.** Commit:
`24: chore(zeitung): fix INJECT_MAP — read live frame.w_mm/h_mm instead of literal targets`

Commit message body should reference RESEARCH.md §root-cause and the verified drift table (7 of 10 entries had Δw ≥ 3 mm; P10 Portrait worst at 11 mm).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('z', 'templates/zeitung-a4-grun/build.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
import inspect
src = inspect.getsource(mod.build_preview)
assert 'target_w_mm=frame.w_mm' in src or 'target_w_mm=frame.w_mm,' in src, 'INJECT_MAP loop did not switch to live frame dims'
assert 'INJECT_MAP' in src
print('OK: build_preview reads live frame dims')
"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict; echo "EXIT_AUDIT_STRICT=$?"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --json | python3 -c "import json, sys; d=json.load(sys.stdin); n=sum(len(p.get('image_extent_warnings', [])) for p in d.get('pages', [])); print('post_fix_image_extent_warnings:', n); assert n == 0, f'expected 0 post-fix warnings, got {n}'"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5; echo "EXIT_STRUCTURAL=$?"</automated>
</verify>
<done>
- `templates/zeitung-a4-grun/build.py::build_preview()` INJECT_MAP value type is bare string (not tuple); loop reads `target_w_mm=frame.w_mm, target_h_mm=frame.h_mm`.
- `audit-alignment zeitung-a4-grun --strict` exits 0; image_extent_warnings count is 0.
- `structural_check --all` exits 0 (TODO-RED state from T03 is now resolved).
- Atomic commit covers ONLY `templates/zeitung-a4-grun/build.py`. No other file changes in this commit.
- Existing `INJECT_MAP` 12 anname keys all preserved 1:1 (no add/drop/rename).
- All 12 entries reference unchanged library asset IDs.
</done>
<dont>
- Don't refactor `inject_into_frame` to read frame dims directly. Per locked decision #15 — too invasive; deferred future work. Edit only the call site.
- Don't change `scale_type` or `local_scale` on any frame. The bug is dim-mismatch, not scale-type. Per locked decision #1 + ISSUE.md "Why" correction.
- Don't add per-frame `local_offset_mm` adjustments to "improve crop framing". Out of scope (#24 is extent fix only).
- Don't combine T05 with T06's render-gallery commit. T05 is the geometry-truth change; T06 regenerates artifacts. Atomic separation.
- Don't inline-hardcode the 12 frame dims back into the INJECT_MAP value tuples to "make explicit what dims will be read". The whole point of the fix is to ELIMINATE the parallel target-dim source-of-truth. Read from the frame instance — single source of truth.
- Don't drop the `# Issue #24 fix: ...` explanatory comment in the dict + loop. It's the ONLY signal a future maintainer has that the literal-target pattern was deliberately removed.
- Don't switch to a different library asset ID for any of the 12 entries. Out of scope. (If Codex flagged a content-quality issue with one of the assets in T04, that's a #25 candidate, not a #24 fix.)
</dont>
</task>

<task id="T06" type="auto" tdd="false">
<name>T06: Regenerate template-preview.sla + 14 page-NN.png + meta.yml SHA bump via bin/render-gallery</name>
<files>templates/zeitung-a4-grun/template-preview.sla, templates/zeitung-a4-grun/page-01.png, templates/zeitung-a4-grun/page-02.png, ..., templates/zeitung-a4-grun/page-14.png, templates/zeitung-a4-grun/preview.pdf, templates/zeitung-a4-grun/baseline.pdf, templates/zeitung-a4-grun/meta.yml, site/public/templates/zeitung-a4-grun/page-01.png, ..., site/public/templates/zeitung-a4-grun/page-14.png</files>
<depends-on>T05</depends-on>
<behavior>
After T06: `bin/render-gallery zeitung-a4-grun --skip-visual-diff` has regenerated the full Zeitung gallery against the post-T05 build. Specifically:
- `templates/zeitung-a4-grun/template-preview.sla` — rewritten with new INJECT_MAP-fed inline JPEGs (now sized to frame dims).
- `templates/zeitung-a4-grun/page-{01..14}.png` — re-rendered (visually different from pre-T06; the 7 pages with INJECT_MAP-drift entries now show photo content reaching the bleed edge instead of leaving white pillarbox margins).
- `site/public/templates/zeitung-a4-grun/page-{01..14}.png` — auto-mirrored by `_mirror_to_site_public`.
- `templates/zeitung-a4-grun/preview.pdf` + `baseline.pdf` — re-generated.
- `templates/zeitung-a4-grun/meta.yml::previews_for_sla` — auto-bumped to the new template-preview.sla SHA-256.
- `bin/check-stale-previews` exits 0 (SHA matches file).

Visual baselines change for ~13 of 14 PNGs (the 7 INJECT_MAP-drift fixes propagate through related layout). Per locked decision #11: document scope for human reviewer in T08's EXECUTION.md / PR description.

Per pitfalls §14: render-gallery is byte-deterministic per Pillow==12.2.0 + pinned JPEG kwargs. SHA stable across re-runs.
</behavior>
<action>
**Step 1.** Run the render-gallery pipeline:
```bash
cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox
bin/render-gallery zeitung-a4-grun --skip-visual-diff
```
Expected: ~25-30 file changes (template-preview.sla + 14 page-NN.png + 14 mirror PNGs + preview.pdf + baseline.pdf + meta.yml SHA).

**Step 2.** Verify SHA bump:
```bash
bin/check-stale-previews
echo "EXIT_STALE=$?"
```
Must exit 0.

**Step 3.** Verify post-fix audit still clean:
```bash
PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict
```
Must exit 0 (sanity — post-render-gallery state should match T05's audit result).

**Step 4.** Inspect git status:
```bash
git status -s
```
Should show ≥25 files changed (M only — no untracked PNGs).

**Step 5.** Commit ALL regenerated artifacts atomically:
```bash
git add templates/zeitung-a4-grun/ site/public/templates/zeitung-a4-grun/
git commit -m "24: chore(zeitung): regenerate template-preview.sla + gallery via bin/render-gallery (post-INJECT_MAP fix)"
```

If `bin/render-gallery` produces files outside `templates/zeitung-a4-grun/` and `site/public/templates/zeitung-a4-grun/`, include them too — but typical scope per pitfalls §14 is exactly those two trees.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && bin/check-stale-previews; echo "EXIT_STALE=$?"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && python3 -c "
import yaml, hashlib
m = yaml.safe_load(open('templates/zeitung-a4-grun/meta.yml').read())
recorded = m['previews_for_sla']
actual = hashlib.sha256(open('templates/zeitung-a4-grun/template-preview.sla', 'rb').read()).hexdigest()
assert recorded == actual, f'SHA mismatch: meta={recorded[:12]} file={actual[:12]}'
print('OK SHA matches:', actual[:12])
"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict; echo "EXIT_AUDIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && ls templates/zeitung-a4-grun/page-*.png | wc -l; ls site/public/templates/zeitung-a4-grun/page-*.png 2>/dev/null | wc -l</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && git log --oneline -1</automated>
</verify>
<done>
- `bin/check-stale-previews` exits 0 (SHA in meta.yml matches template-preview.sla on disk).
- All 14 page-NN.png files present in `templates/zeitung-a4-grun/` AND mirrored to `site/public/templates/zeitung-a4-grun/`.
- `audit-alignment zeitung-a4-grun --strict` exits 0 post-render.
- T06's commit covers ONLY render-gallery output (template-preview.sla + 14 PNGs + 14 mirror PNGs + preview.pdf + baseline.pdf + meta.yml SHA bump). No `templates/zeitung-a4-grun/build.py` change.
</done>
<dont>
- Don't run `bin/render-gallery zeitung-a4-grun` without `--skip-visual-diff` — the visual-diff gate is for end-of-PR-review, not mid-pipeline. Per pitfalls §13.
- Don't hand-copy PNGs to `site/public/...` — `_mirror_to_site_public` does it automatically. Per anti-pattern from #23 dont-list.
- Don't commit T06 + T05 together. T05 is the geometry change; T06 is the artifact regeneration. Atomic separation supports git bisect.
- Don't try to "minimize the diff" by leaving some PNGs out — the SHA gate fails if any single regenerated file is missing from the commit. Stage all of them.
- Don't manually edit `meta.yml::previews_for_sla` — `bin/render-gallery` does it. If the SHA gate fails, re-run render-gallery (it's idempotent) rather than hand-patching.
- Don't expect zero PNG diff. 13 of 14 page PNGs visually shift (per pitfalls §13) — that's the FIX landing. Reviewer will accept the new baseline in PR review per locked decision #11.
</dont>
</task>

<task id="T07" type="auto" tdd="true">
<name>T07: Add ImageContentExtentInvariantTests in test_zeitung_geometry.py — pin rendered-content-extent ≈ frame-extent for 10 photo frames</name>
<files>tools/sla_lib/tests/test_zeitung_geometry.py</files>
<depends-on>T06</depends-on>
<behavior>
After T07: `tools/sla_lib/tests/test_zeitung_geometry.py` gains a `_load_zeitung_preview_doc()` helper, a `_content_extent_mm(frame)` helper, and a new `class ImageContentExtentInvariantTests(unittest.TestCase)` with 10 invariant tests — one per named photo frame in the post-T05 INJECT_MAP. Each test asserts `rendered_content_extent_mm ≈ frame_outer_extent_mm` within `delta=0.5` mm. Tests pin RELATIONSHIPS not coordinates per #23 invariant pattern (locked decision #5). The 3 unnamed Dunkelgrün polygons on pages 12/13/14 are NOT in scope (they have no image content; per locked decision #3).

The 10 named frames covered:
1. `Cover Hero` (page 1)
2. `P1 Hero` (page 2)
3. `P2 Mid` (page 3)
4. `P3 Hero` (page 4)
5. `P4 Foto-Spread` (page 5)
6. `P5 Hero` (page 6)
7. `P7 Portrait` (page 8)
8. `P10 Portrait` (page 11)
9. `P11 Bottom` (page 12)
10. `P13 Hero` (page 14)

The 2 SpreadImage halves (`P9 Spread · left` + `P9 Spread · right`) are EXCLUDED from this test class — they're SpreadImage primitives (different geometry contract; verified by #22's `SpreadImage.outer_bleed_mm` math). If you include them, `frame.w_mm` doesn't match the rendered-content extent because of the half-page offset_mm trick. Document the exclusion in a class docstring.

These tests FAIL before T05 lands (proves the fix is real). They PASS after T05+T06 land. T07 lands AFTER T06 so the assertions can rely on the regenerated template-preview.sla (or, equivalently, on `build_preview()` which produces the same inline data in-memory).

TDD framing per `<task tdd="true">`:
- RED: tests as written would FAIL on pre-T05 INJECT_MAP. (Verified by the runtime probe table in RESEARCH.md root-cause section: 7 of 10 frames had `gap_w >= 3 mm`.) The tests are NOT actually run pre-T05 — they're added post-T06 and immediately green.
- GREEN: post-T06 INJECT_MAP fix + render-gallery → all 10 tests pass.
- REFACTOR: extract `_content_extent_mm` helper to module-level so future tests can reuse it.

If a test fails post-T06: that's a verification failure — return to T05 and inspect the specific frame. Likely cause: a frame whose `w_mm × h_mm` is irregular (e.g. a fractional rounding from the upstream original SLA). Loosen `delta=0.5` to `delta=1.0` ONLY if the failure is sub-millimeter and consistently reproducible. Do NOT loosen above 1.0 — that's the threshold for "actually broken" per locked decision #5 + #23 precedent.
</behavior>
<action>
Read `tools/sla_lib/tests/test_zeitung_geometry.py` end-to-end first to internalize the existing helpers (`_load_zeitung_doc`, `_frame_by_anname`, `_unnamed_dunkelgruen_on_page`, `_doc()` cache, the `assertAlmostEqual(..., delta=0.5)` invariant style). Then APPEND (do not modify existing tests):

**Step 1.** Add `_load_zeitung_preview_doc()` helper alongside the existing `_load_zeitung_doc()` (around line 35-43):

```python
def _load_zeitung_preview_doc():
    """Load templates/zeitung-a4-grun/build.py and call build_preview().

    Different from _load_zeitung_doc which calls build_doc() (the clean
    end-user variant with empty inline_image_data on every photo frame).
    build_preview() runs the INJECT_MAP loop, populating inline JPEGs.
    Required for ImageContentExtentInvariantTests below.
    """
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location(
        "zeitung_build_preview", build_py
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_preview()


_PREVIEW_DOC = None


def _preview_doc():
    global _PREVIEW_DOC
    if _PREVIEW_DOC is None:
        _PREVIEW_DOC = _load_zeitung_preview_doc()
    return _PREVIEW_DOC
```

**Step 2.** Add `_content_extent_mm(frame)` helper (module-level, near `_frame_by_anname`):

```python
def _content_extent_mm(frame):
    """Compute (rendered_w_mm, rendered_h_mm) of a frame's inline image.

    Assumes scale_type=0 (the path inject_into_frame sets). Decodes the
    qCompress-encoded inline_image_data (reversing primitives.py's
    pack_inline_image), reads PIL native dims + JFIF density, returns
    rendered mm at scale_type=0 + LOCALSCX/SCY honored.

    For scale_type=1 frames (rare in zeitung post-#23), returns the
    centered-letterbox extent per pitfalls §3 + §10 Scribus draw matrix.
    """
    import base64
    import struct
    import zlib
    from io import BytesIO
    from PIL import Image
    if not frame.inline_image_data:
        raise AssertionError(
            f"frame {frame.anname!r} has no inline_image_data — "
            "ImageContentExtentInvariantTests requires build_preview() output"
        )
    raw = base64.b64decode(frame.inline_image_data)
    _ = struct.unpack(">I", raw[:4])[0]   # uncompressed-length prefix
    img_bytes = zlib.decompress(raw[4:])
    im = Image.open(BytesIO(img_bytes))
    w_px, h_px = im.size
    dpi = int(im.info.get("dpi", (300, 300))[0] or 300)
    scx, scy = frame.local_scale
    if frame.scale_type == 0:
        rw = w_px * 25.4 / dpi * scx
        rh = h_px * 25.4 / dpi * scy
    elif frame.scale_type == 1 and frame.ratio == 1:
        nat_w_mm = w_px * 25.4 / dpi
        nat_h_mm = h_px * 25.4 / dpi
        s = min(frame.w_mm / nat_w_mm, frame.h_mm / nat_h_mm)
        rw = nat_w_mm * s
        rh = nat_h_mm * s
    else:
        # scale_type=1, ratio=0: stretch fills exactly.
        rw = frame.w_mm
        rh = frame.h_mm
    return (rw, rh)
```

**Step 3.** Add the new test class (append at end of file):

```python
class ImageContentExtentInvariantTests(unittest.TestCase):
    """For each fixed photo frame, rendered content extent ≈ frame extent.

    Pinning style: relationship-pinning per #23 locked decision #7
    (and #24 locked decision #5). assertAlmostEqual with delta=0.5 mm.

    Excludes the 2 SpreadImage halves (P9 left/right) — they're
    SpreadImage primitives whose rendered-content extent uses a
    half-page offset_mm trick (see SpreadImage.emit math). The
    inject_into_frame path doesn't apply to them.

    Excludes the 3 unnamed Dunkelgrün polygons on pages 12/13/14 —
    they're solid-fill image-less ImageFrames (the rule in #24 also
    skips them per locked decision #3).

    These 10 tests would FAIL on the pre-#24 INJECT_MAP literal-target
    state (7 of 10 frames had gap_w >= 3mm per RESEARCH.md root-cause
    table); they pass post-T05+T06.
    """

    def _assert_fills_frame(self, anname, tol_mm=0.5):
        doc = _preview_doc()
        item, _page = _frame_by_anname(doc, anname)
        rw, rh = _content_extent_mm(item)
        self.assertAlmostEqual(
            rw, item.w_mm, delta=tol_mm,
            msg=(f"{anname}: rendered_w {rw:.3f} != frame_w {item.w_mm:.3f} "
                 f"(gap {item.w_mm - rw:.3f} mm > tol {tol_mm} mm)"),
        )
        self.assertAlmostEqual(
            rh, item.h_mm, delta=tol_mm,
            msg=(f"{anname}: rendered_h {rh:.3f} != frame_h {item.h_mm:.3f} "
                 f"(gap {item.h_mm - rh:.3f} mm > tol {tol_mm} mm)"),
        )

    def test_cover_hero_fills_frame(self):
        self._assert_fills_frame("Cover Hero")

    def test_p1_hero_fills_frame(self):
        self._assert_fills_frame("P1 Hero")

    def test_p2_mid_fills_frame(self):
        self._assert_fills_frame("P2 Mid")

    def test_p3_hero_fills_frame(self):
        self._assert_fills_frame("P3 Hero")

    def test_p4_foto_spread_fills_frame(self):
        self._assert_fills_frame("P4 Foto-Spread")

    def test_p5_hero_fills_frame(self):
        self._assert_fills_frame("P5 Hero")

    def test_p7_portrait_fills_frame(self):
        self._assert_fills_frame("P7 Portrait")

    def test_p10_portrait_fills_frame(self):
        self._assert_fills_frame("P10 Portrait")

    def test_p11_bottom_fills_frame(self):
        self._assert_fills_frame("P11 Bottom")

    def test_p13_hero_fills_frame(self):
        self._assert_fills_frame("P13 Hero")
```

**Step 4.** Verify (see <verify>). Commit:
`24: test(zeitung): add ImageContentExtentInvariantTests for 10 photo frames`
</action>
<verify>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_zeitung_geometry.ImageContentExtentInvariantTests -v 2>&1 | tail -20</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -c "
from sla_lib.tests.test_zeitung_geometry import _preview_doc, _content_extent_mm, _frame_by_anname
doc = _preview_doc()
for an in ['Cover Hero', 'P1 Hero', 'P2 Mid', 'P3 Hero', 'P4 Foto-Spread', 'P5 Hero', 'P7 Portrait', 'P10 Portrait', 'P11 Bottom', 'P13 Hero']:
    item, _ = _frame_by_anname(doc, an)
    rw, rh = _content_extent_mm(item)
    gap_w = item.w_mm - rw; gap_h = item.h_mm - rh
    print(f'{an:<22} frame={item.w_mm:6.2f}x{item.h_mm:6.2f}  rendered={rw:6.2f}x{rh:6.2f}  gap=({gap_w:+.3f}, {gap_h:+.3f})')
    assert abs(gap_w) <= 0.5 and abs(gap_h) <= 0.5, f'{an} fails'
print('OK all 10 frames')
"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -5</automated>
</verify>
<done>
- `_load_zeitung_preview_doc()` and `_content_extent_mm()` helpers exist at module level in `test_zeitung_geometry.py`.
- `ImageContentExtentInvariantTests` class has exactly 10 tests, one per named photo frame.
- All 10 tests PASS post-T06 (rendered content extent within 0.5 mm of frame extent on every photo frame).
- `unittest discover tools/sla_lib/tests` exits 0.
- Test docstring documents exclusion of SpreadImage halves + image-less Dunkelgrün polygons.
- assertAlmostEqual `delta=0.5` (mm) is the convention; do NOT widen.
</done>
<dont>
- Don't pin absolute coordinates (e.g. `assertEqual(item.x_mm, -3.0)`). Pin RELATIONSHIPS per #23 locked decision #7. The relationship is `rendered ≈ frame_extent`.
- Don't include the 2 SpreadImage halves in this test class. They use `SpreadImage.outer_bleed_mm` math + `local_offset_mm = -(page_w + outer_bleed)` — `frame.w_mm` ≠ rendered extent for them. Out of scope per the test docstring.
- Don't include the 3 unnamed Dunkelgrün polygons. They're image-less; `_content_extent_mm` would raise AssertionError on them. The rule and the tests both skip them per locked decision #3.
- Don't loosen `delta` above 1.0 mm. If a test fails sub-mm, fix the underlying drift; if it fails by mm+, bug — return to T05.
- Don't fall back to building synthetic primitives in this test file. The whole point is to pin the LIVE Zeitung post-fix state. Synthetic-primitives coverage of the rule lives in T01's `test_brand_image_fills_frame.py`.
- Don't replicate `_content_extent_mm` from T01's rule code. Either share via a public helper (e.g. extract to `sla_lib/builder/image_extent.py`) OR keep the test-side copy minimal. Both acceptable — the codebase doesn't have strong "single source of truth for math" conventions yet.
- Don't try to verify scale_type=1+ratio=1 letterbox case with Zeitung. No Zeitung frame has that config post-#24 (every preview-injected frame has scale_type=0). The scale_type=1 branch in `_content_extent_mm` is defensive; T01's rule tests cover it.
</dont>
</task>

<task id="T08" type="auto" tdd="false">
<name>T08: Codex visual audit of all 14 Zeitung pages — POST-FIX verification + EXECUTION.md final + status flip</name>
<files>reviews/codex-zeitung-all-pages-iter2.md, reviews/audit-zeitung-post-fix.json, .issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/EXECUTION.md, .issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/ISSUE.md</files>
<depends-on>T07</depends-on>
<behavior>
After T08:
- Codex has been re-run against the post-T06-regenerated PNGs (`templates/zeitung-a4-grun/page-{01..14}.png`). Output saved to `reviews/codex-zeitung-all-pages-iter2.md`. Cross-checked against `reviews/audit-zeitung-post-fix.json`. Verdict expected: `<verdict value="pass">` with zero ERROR-class findings (zero remaining INJECT_MAP-drift defects from the new rule perspective).
- If Codex still flags class-(b) findings (a letterbox/extent issue the rule doesn't catch): document specifically in EXECUTION.md "Open follow-ups", classify as #25 deferred, ship anyway. Per locked decision #10 — Codex iteration budget is 2 runs total (iter1 in T04 + iter2 here).
- If Codex flags class-(c) findings (z-order, color contrast, off-center crop_focus, hyphenation, font-size inconsistency, etc.) — these have been deferred to #25 since T04. Re-confirm in EXECUTION.md.
- `EXECUTION.md` drafted with: Summary; per-task notes (T01-T08); Codex iteration count (1 or 2 cycles in T04 + 1 in T08); deferred-to-#25 list (if any); acceptance-criteria mapping (each ISSUE.md AC bullet → which task fulfills it); locked-decision conformance self-check (15-item table from RESEARCH.md → which task implements each).
- `ISSUE.md::status` flipped from `open` to `in-review` (PR-pending state; `closed` happens at PR merge via lifecycle hooks).
</behavior>
<action>
**Step 1.** Capture post-fix audit JSON for cross-check:
```bash
PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --json > reviews/audit-zeitung-post-fix.json
```

**Step 2.** Re-run Codex with the SAME prompt as T04 (no priming, no expected-outcomes hints):
```bash
issue-cli review-exec \
  --tool codex \
  --prompt prompts/zeitung-all-pages-audit.md \
  --name zeitung-all-pages-iter2 \
  --review-type topic \
  --review-mode topic \
  --topic "Zeitung A4 visual alignment audit (Issue #24 post-fix verification)" \
  --output-dir reviews/
```
Copy/rename the timestamped output to `reviews/codex-zeitung-all-pages-iter2.md`.

**Step 3.** Cross-check — append `## Cross-check vs. audit JSON (post-fix)` section to `reviews/codex-zeitung-all-pages-iter2.md` mapping each Codex finding (if any) to:
- `audit-zeitung-post-fix.json::pages[*].image_extent_warnings` (should be empty post-T05+T06).
- `pages[*].suspicious_pairs` / `spine_warnings` / `tolerance_suspicions` (legacy channels).

If Codex's verdict block reads `<verdict value="pass" critical=0 high=0 medium=0>` AND `audit-zeitung-post-fix.json` has zero image_extent_warnings: full PASS. Note in EXECUTION.md.

If Codex flags 1+ ERROR finding that the audit MISSES:
- Class-(b) (letterbox/extent variant): document; defer to #25 (per locked decision #10 — beyond 2 cycles is out of budget).
- Class-(c) (z-order, contrast, etc.): document; defer to #25 (per pitfalls §8 + locked decision #10).
- Either way, ship #24. Do NOT iterate further.

**Step 4.** Draft `.issues/24-…/EXECUTION.md` with this structure:

```markdown
# EXECUTION — #24: Zeitung remaining alignment (INJECT_MAP drift fix)

## Summary
Restored Zeitung's image-content extents on the 7 INJECT_MAP-drifted photo
frames (Cover Hero / P1-P13 Hero / P7-P10 Portrait) by reading live frame
dims at injection time instead of literal target tuples that had drifted
out of sync after #22 + #23 frame-extent edits. Added the 15th BrandRule
`brand:image_fills_frame` (severity ERROR for full-bleed, WARNING otherwise)
which catches this regression class going forward. Codex visual audit of
all 14 pages confirms zero remaining alignment defects from the new rule
perspective (1 + 1 cycles consumed of 2-cycle budget).

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| T01 | feat(brand): add brand:image_fills_frame rule + library.compute_aspect_fill helper | 15-rule registry; 10 unit tests; helper deferred-use |
| T02 | feat(audit): wire image_fills_frame into audit_alignment + --check-image-extent flag | PageAuditReport + JSON + Markdown emission; --strict gating |
| T03 | chore(meta): pre-apply brand_overrides[brand:image_fills_frame] to 7 non-Zeitung templates | postkarte/plakat/infostand/themen/falzflyer/wahltag/wahlaufruf |
| T04 | docs(reviews): Codex visual audit all 14 Zeitung pages — pre-fix baseline (iter1) | new prompts/zeitung-all-pages-audit.md (no priming); cross-check vs. audit JSON |
| T05 | chore(zeitung): fix INJECT_MAP — read live frame.w_mm/h_mm | atomic single commit; ~30 line diff |
| T06 | chore(zeitung): regenerate template-preview.sla + gallery via bin/render-gallery | 13 of 14 PNGs visually shifted; SHA bump |
| T07 | test(zeitung): add ImageContentExtentInvariantTests for 10 photo frames | invariant-pinning per #23 #5 pattern |
| T08 | docs(reviews+issues): post-fix Codex audit + EXECUTION.md + status flip | iter2 verdict pass; status -> in-review |

## Codex iteration count
- Pre-fix (T04): 1 cycle (iter1) — verified the audit catches every Codex
  finding of class (b); 0 class-(c) findings; OR documented per case.
- Post-fix (T08): 1 cycle (iter2) — verdict pass.
- Total: 2 cycles of 2 budgeted (locked decision #10 cap).

## Acceptance-criteria mapping (ISSUE.md → task)
- [x] Codex visual review all 14 pages → T04 + T08 (`reviews/codex-zeitung-all-pages-iter{1,2}.md`).
- [x] Every Codex finding captured by ≥1 BrandRule (or deferred to #25) → T01 + cross-check sections in iter1+iter2.
- [x] `brand:image_fills_frame` with full test coverage; severity=ERROR for full-bleed → T01.
- [x] All 13 → 10 letterboxed frames fixed (corrected to 10 photo frames; the 3 unnamed Dunkelgrün polygons are image-less and skipped per locked decision #3) → T05.
- [x] `bin/audit-alignment zeitung-a4-grun --strict` exit 0 → T05 verify.
- [x] `python3 -m sla_lib.builder.structural_check --all` exit 0 → final verification step 2.
- [x] `python3 -m unittest discover tools/sla_lib/tests` exit 0 → final verification step 1.
- [x] `bin/check-stale-previews` exit 0 → T06 verify.
- [x] Re-run Codex post-fix: zero remaining issues from new rule perspective → T08.
- [x] Geometric tests pin rendered-content extent invariants → T07 (10 tests).

## Locked-decision conformance (RESEARCH.md 15-item table → task)
- D1 (INJECT_MAP one-loop fix, not scale_type) → T05.
- D2 (new rule brand:image_fills_frame, dynamic severity) → T01.
- D3 (skip image-less ImageFrames) → T01 + T07 docstring.
- D4 (Codex audit all 14 pages, refined prompt) → T04 + T08.
- D5 (invariant tests pin RELATIONSHIPS) → T07.
- D6 (audit tool wire-in via _audit_doc, Option A) → T02.
- D7 (pre-apply brand_overrides on 7 non-Zeitung templates) → T03.
- D8 (compute_aspect_fill helper, NOT used in primary fix path) → T01.
- D9 (atomic-PR ordering T01-T08) → task ordering.
- D10 (Codex iteration budget 2 runs) → T04 + T08.
- D11 (visual baselines change for 13 PNGs; document) → T06 commit + this EXECUTION.md.
- D12 (avoid non-unity local_scale; stay scale_type=0 + matched JPEG dims) → T05 (no scale change).
- D13 (rule registry 14 → 15) → T01.
- D14 (Codex prompt rewritten without priming) → T04.
- D15 (don't refactor inject_into_frame) → T05 dont-list enforced.

## Open follow-ups (deferred to #25)
- [if applicable] Class-(c) Codex findings from T04/T08: <list each>.
- inject_into_frame refactor to read frame dims directly (per locked decision #15).
- 7 non-Zeitung templates' image_fills_frame audit + override-vs-fix classification (per T03 reason text).

## Visual-baseline note for human reviewer
13 of 14 page-NN.png files visually shift in T06 — this is the FIX landing.
The 7 INJECT_MAP-drift entries (Cover Hero / P1 / P4 / P7 / P10 / P11 / P13)
gain 3-11 mm of additional photo content reaching the bleed edge that was
previously white pillarbox margin. Reviewer should compare against the
pre-T06 baseline (preserved in git history at the commit before T06).
```

**Step 5.** Flip ISSUE.md status:
```bash
python3 -c "
src = open('.issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/ISSUE.md').read()
src = src.replace('status: open', 'status: in-review', 1)
open('.issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/ISSUE.md', 'w').write(src)
"
```

**Step 6.** Final verification (run all 6 acceptance gates from ISSUE.md). Then commit:
`24: docs(reviews+issues): post-fix Codex audit (iter2 pass) + EXECUTION.md + status in-review`
</action>
<verify>
<automated>test -f reviews/codex-zeitung-all-pages-iter2.md && test -f reviews/audit-zeitung-post-fix.json && test -f .issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/EXECUTION.md && wc -l .issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/EXECUTION.md</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && python3 -c "import yaml; src=open('.issues/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox/ISSUE.md').read(); fm=yaml.safe_load(src.split('---')[1]); print('status:', fm.get('status')); assert fm.get('status') == 'in-review'"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && grep -E "verdict value" reviews/codex-zeitung-all-pages-iter2.md | head -3</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && python3 -c "import json; d=json.load(open('reviews/audit-zeitung-post-fix.json')); n=sum(len(p.get('image_extent_warnings', [])) for p in d.get('pages', [])); print('post_fix_image_extent_warnings:', n); assert n == 0"</automated>
<automated>cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox && git log --oneline -10</automated>
</verify>
<done>
- `reviews/codex-zeitung-all-pages-iter2.md` exists with all-14-pages findings + cross-check section + verdict block.
- `reviews/audit-zeitung-post-fix.json` exists with zero image_extent_warnings.
- `EXECUTION.md` exists with Summary, Tasks table, Codex iteration count, AC mapping, locked-decision conformance, open follow-ups, visual-baseline note.
- `ISSUE.md::status` is `in-review`.
- All 8 task commits visible in `git log` with `24:` prefix and conventional-commit format.
- Codex verdict is `pass` (or, if `fail`, every flagged finding is documented as deferred to #25 in EXECUTION.md "Open follow-ups").
</done>
<dont>
- Don't include "claude" or "AI-assisted" mentions in EXECUTION.md (per `feedback_no_claude_attribution.md` user feedback in MEMORY.md).
- Don't close GH issue #47 from a commit message — let the PR description handle "Closes #47" (or `gh pr create --body "Closes #47"`). A `git commit -m "closes #47"` would close it on push without PR review.
- Don't flip status to `closed` or `done` in T08 — that happens at PR-merge by issue lifecycle hooks. `in-review` is the correct PR-pending state.
- Don't iterate Codex past iter2 even if findings remain. Per locked decision #10 — beyond 2 cycles signals the rule's underlying model is wrong; ship + defer.
- Don't add new sections to EXECUTION.md beyond Summary / Tasks / Codex iteration count / Acceptance criteria / Locked-decision conformance / Open follow-ups / Visual-baseline note. Keep it terse — PR reviewer reads it.
- Don't omit the visual-baseline note. Reviewers will be confused why 13 PNGs changed if not told (per locked decision #11).
- Don't backfill the iter1 cross-check section in T08 — that lives in T04's commit. T08 only adds iter2.
</dont>
</task>

</tasks>

<verification>
After all tasks complete, run these final checks:

1. **Full test suite:**
   ```
   cd /root/workspace/.worktrees/24-zeitung-remaining-alignment-image-content-doesnt-fill-frame-scale_type-letterbox
   PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests
   ```
   Must exit 0. Includes the 10 new tests in `test_brand_image_fills_frame.py` + 10 new tests in `ImageContentExtentInvariantTests`.

2. **Structural check across all templates (the strict CI gate):**
   ```
   PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
   ```
   Must exit 0. Zeitung passes all 15 BrandRules naturally (no `brand:image_fills_frame` override). Other 7 templates skip the new rule via override.

3. **Audit tool clean on Zeitung:**
   ```
   PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict
   echo "EXIT=$?"
   ```
   Must exit 0 (zero ERROR/WARNING findings on Zeitung post-T05).

4. **Audit tool with check-image-extent disabled (sanity — flag works):**
   ```
   PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --no-check-image-extent --strict
   echo "EXIT=$?"
   ```
   Must exit 0.

5. **Stale-previews gate:**
   ```
   bin/check-stale-previews
   echo "EXIT=$?"
   ```
   Must exit 0 (T06 SHA bump locked in).

6. **Geometry invariant tests pass:**
   ```
   PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_zeitung_geometry -v
   ```
   ≥ N existing tests + 10 new `ImageContentExtentInvariantTests`, all green.

7. **`brand:image_fills_frame` rule unit tests pass:**
   ```
   PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_brand_image_fills_frame -v
   ```
   10 tests, all green.

8. **Registry count canary green:**
   ```
   PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_brand_constraints.RegistryTests -v
   ```
   `test_fifteen_rules_exact` + `test_ids_are_canonical` pass.

9. **YAML lint on all 8 affected meta.yml files:**
   ```
   for t in postkarte-a6-kampagne plakat-a1-hochformat infostand-tent-card-a5-quer themen-plakat-a3-quer kandidat-falzflyer-din-lang wahltag-tueranhaenger wahlaufruf-postkarte-a6-quer zeitung-a4-grun; do
     python3 -c "import yaml; yaml.safe_load(open('templates/$t/meta.yml').read())" || echo "FAIL $t"
   done
   ```
   No exceptions.

10. **Git status sanity:**
    ```
    git status -s
    ```
    Expected: empty (all changes committed).

11. **Commit history sanity:**
    ```
    git log --oneline -15
    ```
    Should show 8 task commits + the planning commits, all with `24:` prefix.

12. **Codex artifacts present:**
    ```
    ls reviews/codex-zeitung-all-pages-iter1.md reviews/codex-zeitung-all-pages-iter2.md reviews/audit-zeitung-pre-fix.json reviews/audit-zeitung-post-fix.json prompts/zeitung-all-pages-audit.md
    ```
    All five exist.
</verification>

<success_criteria>
Mapping to ISSUE.md acceptance criteria (with RESEARCH.md "Scope changes vs. ISSUE.md" corrections):

- [x] **Codex visual review completed for ALL 14 Zeitung pages, output saved in `reviews/codex-zeitung-all-pages-iter{1,2}.md`** (note: ISSUE.md said singular `codex-zeitung-all-pages.md`; we have iter1 + iter2 per locked decision #10's 2-cycle budget) → T04 + T08.
- [x] **Every visual issue Codex identifies is captured by at least one BrandRule** (existing 14 or new 1) **OR documented as #25-deferred class (c)** → T04 cross-check + T08 verdict; documented in EXECUTION.md.
- [x] **New rules are GENERIC** (work on any template, no Zeitung-specific code) → T01 dont-list enforced; rule walks every ImageFrame on every non-master page with no slug check.
- [x] **`brand:image_fills_frame` (or equivalent) added with full test coverage; severity ERROR for full-bleed frames** → T01 (10 unit tests + dynamic severity via `_is_full_bleed`).
- [x] **All 13 → 10 Zeitung letterboxed frames fixed** (corrected count: 10 photo frames; the 3 unnamed Dunkelgrün polygons are image-less and explicitly skipped per locked decision #3) → T05 (atomic INJECT_MAP one-loop fix). RESEARCH.md "Scope changes" table documents this correction.
- [x] **`scale_type=0` with computed `local_scale`** is NOT the fix path used (locked decision #1: actual root cause is INJECT_MAP target drift, not scale_type letterboxing; `library.inject_into_frame` already sets `scale_type=0`). RESEARCH.md "Scope changes" table documents this correction.
- [x] **`bin/audit-alignment zeitung-a4-grun --strict` exit 0** → T05 verify + final verification step 3.
- [x] **`python3 -m sla_lib.builder.structural_check --all` exit 0** → final verification step 2.
- [x] **`python3 -m unittest discover tools/sla_lib/tests` exit 0** → final verification step 1.
- [x] **`bin/check-stale-previews` exit 0** → T06 verify + final verification step 5.
- [x] **Re-run Codex visual review post-fix: zero remaining alignment issues from the new rule perspective** → T08 (verdict pass; or deferred class-(c) findings documented in EXECUTION.md per locked decision #10).
- [x] **Geometric tests in `test_zeitung_geometry.py` pin rendered-content extent invariants for the 10 fixed frames** (corrected from 13 to 10 — SpreadImage halves and image-less polygons excluded) → T07 (10 invariant tests).
- [ ] **User-confirmed pages 1, 2, 5, 8, 11, 12, 13, 14 of Zeitung visually re-checked by human reviewer in PR** → out of executor scope (PR review).

Critical-finding self-check:
- Build-detector-first ordering enforced: T01-T03 land detector + audit-wire + non-Zeitung overrides BEFORE T04 Codex audit. T04 is a true STOP-and-iterate gate (max 2 cycles per locked decision #10).
- Atomic ordering of T05: INJECT_MAP fix is the ONLY change in that commit (no `scale_type` change, no `local_scale` change, no `inject_into_frame` refactor) → T05 dont-list enforced.
- Generic rule only — no Zeitung anname/coordinate constants in `_ImageFillsFrameRule` code → T01 manual verify + T01 dont-list.
- Tests pin RELATIONSHIPS, not coordinates — `assertAlmostEqual(rendered, frame, delta=0.5)` style → T07 dont-list + manual verify.
- Pre-applied overrides for 7 non-Zeitung templates with reason "scheduled for follow-up audit per #24" → T03.
- Visual baselines change for 13 of 14 PNGs in T06 → documented in EXECUTION.md (T08) per locked decision #11.
- ISSUE.md "Why" correction applied: root cause is INJECT_MAP drift (verified by RESEARCH.md root-cause table), NOT scale_type letterboxing → noted in `<objective>` + EXECUTION.md.
- 14 → 15 rule registry count bumped → T01 (`test_fifteen_rules_exact`).
- `bin/render-gallery` + SHA bump as separate atomic commit (T06) → between T05 and T07.
- Codex iteration budget 2 runs total across T04 + T08; if exceeded, defer to #25 → locked decision #10.
- 10 photo frames covered (not 13 from ISSUE.md) — per RESEARCH.md correction; the 3 unnamed Dunkelgrün polygons are image-less and skipped.
</success_criteria>

<risks_and_verification>

## Risks and verification checkpoints

**Build-detector-first contract (load-bearing, locked decision #9):**
- T01-T03 land BEFORE T04 Codex audit. T04 is a true verification gate, not a doc-stub.
- Between T03 and T05, `structural_check --all` exits 1 on Zeitung (the rule fires with ERROR severity on the 7 full-bleed INJECT_MAP-drift findings). This is the WITNESS. T05 makes it green.
- T05 only runs after T04 passes. If T04's GATE FAILS (Codex sees something the audit misses, after 2 cycles), STOP — escalate to user — possible new rule class needed.

**T04 is a true STOP-and-iterate gate (max 2 cycles per locked decision #10):**
- Iter1 (T04 commit): mandatory.
- Iter1b (between T04 and T05, if iter1 surfaced class-(b) MISSING entries): up to 1 strengthening cycle of `_ImageFillsFrameRule` predicate, then re-run Codex.
- Iter2 (T08): post-fix verification.
- Total budget: 2 Codex runs against the SAME prompt (one pre-fix, one post-fix). If iter1b ran, that's a 3rd run but against the SAME prompt with strengthened rule — that's the 2-cycle budget.
- If still flagging post-iter2: defer to #25, ship #24. Do NOT extend scope.

**Atomic ordering of T05 (locked decision #9):**
- T05's commit covers ONLY `templates/zeitung-a4-grun/build.py::build_preview()`. No other file changes in this commit.
- Splitting the INJECT_MAP fix across commits (e.g. one commit per frame) would create N intermediate states where some frames are fixed and others are still drifted — `audit-alignment --strict` would partially-fail across commits, breaking bisect.
- One-line-per-entry value-type change (tuple → string) + one-line-per-loop-iteration target-dim change is the entire diff. ~30 lines including the INJECT_MAP comment update.

**Codex CLI availability (T04 + T08 prerequisite):**
- Verified path: `/root/.npm-global/bin/codex` (version 0.128.0 per pitfalls §15).
- `issue-cli review-exec --tool codex` is the canonical invocation per existing `reviews/codex-zeitung-visual.md` (ran 129s for 14 pages with `gpt-5.4`).
- If `codex` is unavailable, the FALLBACK is direct Claude image read (Read tool on `templates/zeitung-a4-grun/page-{01..14}.png`) — but this consumes more tokens. Use only if Codex is genuinely broken. Document the substitution in EXECUTION.md.

**`bin/render-gallery` regenerates ~25-30 files in T06 (locked decision #11, pitfalls §14):**
- T06 dirties: `template-preview.sla` + 14 `page-NN.png` + 14 mirror PNGs in `site/public/...` + `preview.pdf` + `baseline.pdf` + `meta.yml::previews_for_sla` SHA bump.
- ALL must be staged in T06's commit. `git status -s | wc -l` should be ≥ 25.
- If the SHA isn't bumped, `bin/check-stale-previews` exits 1 and CI fails. T06 verify catches this.
- Visual baselines change for 13 of 14 PNGs (the 7 INJECT_MAP-drift fixes propagate visually). Reviewer must accept the new pixel baseline in PR review per locked decision #11. Documented in T06 commit message + EXECUTION.md visual-baseline note.

**Pre-applied overrides for 7 non-Zeitung templates (locked decision #7, pitfalls §12):**
- The 7 templates that DO get the override: postkarte-a6-kampagne, plakat-a1-hochformat, infostand-tent-card-a5-quer, themen-plakat-a3-quer, kandidat-falzflyer-din-lang, wahltag-tueranhaenger, wahlaufruf-postkarte-a6-quer.
- Reason text MUST reference #24 + #25 explicitly (provides traceability for the follow-up audit).
- Zeitung itself does NOT get an `image_fills_frame` override — the rule must fire there (witness pre-T05; pass post-T05).
- Without the 7 overrides, every commit between T03 and T05 has structural_check failing on those templates too (in addition to Zeitung). The 7-override pre-apply contains the failure surface to Zeitung only.

**T04 might surface non-letterbox class findings (pitfalls §8):**
- Codex IS capable of flagging z-order issues, color-contrast violations, off-center crop_focus, hyphenation/orphans, font-size inconsistency.
- Per pitfalls §8 + locked decision #10: classify each finding into:
  - (a) Already covered by existing rule → note in EXECUTION.md, no new code.
  - (b) New letterbox/extent class → `brand:image_fills_frame` should catch it; if not, strengthen rule (1 cycle budget).
  - (c) NEW class (z-order, contrast, etc.) → defer to #25, do NOT extend #24 scope.
- Document the classification inline in `reviews/codex-zeitung-all-pages-iter1.md` cross-check section.

**T07 invariant tests pinning (locked decision #5):**
- Tests pin `rendered_content_extent ≈ frame_outer_extent` within `delta=0.5 mm`. NOT absolute coordinates.
- If any test fails post-T06: return to T05 (likely an INJECT_MAP entry was missed in the value-type change, or a frame's `w_mm` is fractional in a way that breaks the JFIF density math). Inspect the specific frame's `inline_image_data` decode + dpi extraction.
- Don't loosen `delta` above 1.0 mm — that's the threshold for "actually broken" per locked decision #5 + #23 precedent.

**Inline-image dimension probing path (pitfalls §13 + RESEARCH.md _ImageFillsFrameRule §_resolve_asset):**
- The qCompress reverse: `base64.b64decode → struct.unpack(">I", raw[:4]) → zlib.decompress(raw[4:]) → BytesIO → PIL.Image.open`.
- This is the SAME math `pack_inline_image` (primitives.py:750-761) does in reverse. Test it independently in T01's `test_qcompress_roundtrip_decode` test case.
- DPI extraction: `im.info.get("dpi", (300, 300))[0]`. Cast to int. Fallback 300 if missing/zero.

**Defensive coding for asset-resolution failures (pitfalls §1):**
- T01's `_resolve_asset` wraps PIL ops in try/except (FileNotFoundError, UnidentifiedImageError, OSError). On failure, returns `(None, None, 300)` and the rule emits ONE `warning` per missing asset (not silent skip).
- Don't crash the audit on missing assets — produce a warning entry instead.

**No new dependencies (locked decision #1 user constraint):**
- PIL/Pillow already in env (Pillow==12.2.0 verified via Dockerfile.claude in pitfalls §16).
- `base64` / `struct` / `zlib` are stdlib.
- No `requests` / `numpy` / image-libs additions.

**`Page.is_left` is broken (pitfalls B4 in #23, recurring blind spot):**
- `_is_full_bleed` predicate uses `frame_bbox_mm` (rotation-aware) against `page.width_pt × PT_TO_MM` and `page.bleed_mm`. Does NOT use `page.is_left`.
- Several Zeitung frames are rotated 90° (e.g. `u2950` on the cover). The bbox math handles this correctly via `rotated_bbox`.

**Token-budget partial-completion fallback:**
- If the executor runs out of usage before T08, work landed up to T05+T06 is the highest-value contribution: rule + audit + Zeitung INJECT_MAP fix + regenerated artifacts + invariant tests are all green.
- T08 (Codex post-fix audit + EXECUTION.md + status flip) is documentation + verification — can be a follow-up commit-batch in a fresh session.
- T05 + T06 + T07 should land together in one session if possible — they're the geometric truth + artifact + test trifecta. Atomic in spirit even though split across 3 commits.

**Float-imprecise SLA round-trip (verified pitfall from #23):**
- `Cover Hero.w_mm = 209.9999999999361` vs `216.000` post-#23 outer-bleed extension.
- T07's `assertAlmostEqual(..., delta=0.5)` accommodates this.
- T05's `target_w_mm=frame.w_mm` passes the float verbatim to `library.inject_into_frame`, which crops the JPEG to the float dim and encodes at 300 DPI. JPEG dims round to nearest pixel (`int(216.000 * 300 / 25.4) = 2551 px`). Slight rounding error (sub-mm) is what the 0.5 mm tolerance absorbs.

**Test count drift (procedural):**
- T01 bumps `test_fourteen_rules_exact` → `test_fifteen_rules_exact`. If a future rule lands AFTER #24 merges, that test must bump again. Acceptable — explicit count is the canary.

**Don't reuse `prompts/zeitung-visual-audit.md` from #23 (load-bearing per locked decision #14):**
- That prompt has priming hints (`KNOWN issues: page 1 ... page 8 ... page 11 ...`) that bias Codex toward the user-cited pages.
- T04 creates a NEW file `prompts/zeitung-all-pages-audit.md` with neutral per-page enumeration — no priming, no expected-outcomes hints.
- Per `feedback_review_no_code_in_prompt.md` user feedback in MEMORY.md.

</risks_and_verification>
