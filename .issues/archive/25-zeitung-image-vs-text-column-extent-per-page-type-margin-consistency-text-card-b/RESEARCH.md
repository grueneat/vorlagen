# RESEARCH — #25: Zeitung band-consistency model + per-page-type margin spec + content vs decoration

**Status:** Architecture fully locked through extended user dialogue. **The original ISSUE.md scope evolved substantially — RESEARCH.md is now the authoritative spec.** This document is self-contained — readable cold without any conversation context. The original research/codebase.md and research/pitfalls.md remain on disk for line-level evidence but their algorithms (`brand:image_within_text_block`, `brand:document_margins_consistent`, `brand:text_card_size_consistent`) are SUPERSEDED by the band-consistency model below.

**Audience:** the planner agent for #25, and any future maintainer picking up this work cold.

---

## 1. Executive summary — the problem and the architectural answer

### The problem

After #24 fixed INJECT_MAP drift (images now fill their frames), the user observed that Zeitung still has alignment issues per-page. Direct probe confirmed real drift on a handful of pages. But more importantly: the user articulated a harder architectural constraint that reframes the entire fix:

> "I can't force pairing when giving this to hundreds of people, they will randomly combine left and right pages layouts… they can just copy and edit each page and move them around for their own local newspaper they do."

Bezirksgruppen take the Zeitung template and **shuffle pages freely** to assemble their local newsletter. Any LEFT page might end up next to any RIGHT page in the printed spread. So the template's job is to provide a **library of combinable parts**, not a fixed magazine layout.

### The architectural answer: the band model

Every body-pool page has the same OUTER STRUCTURE:

```
y=-3  ─────────────  BLEED top
y=20  ─────────────
                     HEADER band  (page #, date, breadcrumb)  — same y-range across all body pages
y=49  ─────────────
                     FREE ZONE  — each page does its own thing
                     (text grid / image-top / image-bottom / photo grid / ...)
                     CONTENT must stay INSIDE this band
y=283 ─────────────
                     FOOTER band  (page number)  — same y-range across all body pages
y=297 ─────────────
                     BLEED bottom
```

**LEFT body pages**: outer-margin = 20 mm (left edge), inner-margin = 20 mm (right edge / spine).
**RIGHT body pages**: outer-margin = 20 mm (right edge), inner-margin = 20 mm (left edge / spine).

(Currently symmetric 20/20 for Zeitung. The model supports asymmetric inner≠outer for templates that introduce gutter inset later.)

Inside the free zone, **anything goes**: 3-column text grid, image at top + body below, image at bottom + body above, single-column feature, photo grids — any internal arrangement is allowed AS LONG AS:
1. No content (text/image with content) extends above y=49 or below y=283.
2. No content extends past the L/R margins (x<20 or x>190).
3. The header band y=20-49 contains only the breadcrumb header.
4. The footer band y=283-297 contains only the page number / colophon.

### Two frame classes

The rule distinguishes:

1. **Content frames** (subject to bands + margins):
   - All `TextFrame` instances
   - `ImageFrame` instances with actual image content (`image` set, `src` set, OR `inline_image_data` non-None)

2. **Background decoration** (EXEMPT — can be full-bleed any color):
   - `Polygon` instances with solid fill (no image content)
   - Image-less `ImageFrame` instances with brand-color fill (`fill in {Dunkelgrün, Hellgrün, Magenta, Gelb, White}`)

This means a body page can be **white-bg** (no decoration), **Dunkelgrün-bg** (full-bleed Dunkelgrün polygon), **Hellgrün-bg** (Hellgrün polygon), **Gelb-bg** (future), **photo-bg** (future) — all of which combine freely with each other in a spread because the content positions are identical.

### Excluded feature pages

Some pages have hero treatments that legitimately bleed past the bands (full-bleed cover photo, edge-to-edge spread images, back-cover colophon). These are listed in `meta.yml::excluded_pages` and exempt from the band rule.

For Zeitung specifically, feature pages are:
- **Page 1** (cover) — Cover Hero full-bleed with masthead overlay
- **Page 2** (P1 Hero) — full-bleed photo extending y=0-130 above the header band
- **Pages 10 + 11** (P9 Spread halves) — full-bleed spread photo across both pages
- **Page 14** (back) — feature/colophon treatment

All other pages (3, 4, 5, 6, 7, 8, 9, 12, 13) are body-pool pages and must conform to the band model.

### Combinability guarantee

Any two body-pool pages of the matching side can pair into a spread. The reader's eye sees:
- Page numbers at the same y on both pages ✓
- Headlines (top of body content) aligned at y=49 on both pages ✓
- Body content extending to no later than y=283 on both pages ✓
- L/R margins symmetric across the spread ✓

Variation in the free zone (one page is text-heavy, other has a photo) is part of the design — the OUTER STRUCTURE keeps it coherent.

---

## 2. The 6 Zeitung drift fixes

Direct probe on post-#24 main produced this comprehensive list. These are ALL the drift items #25 fixes; everything else is intentional design.

| # | Page | Type | Drift | Fix |
|---|---|---|---|---|
| 1 | 4 | LEFT body | Body-block X off-center: col-3 truncated to h=39 mm so detector sees block ending at x=132 instead of x=190 | Either restore col-3 to full height (h≈100 mm) OR explicitly define a 2-column body layout — planner decides per visual review |
| 2 | 5 | RIGHT body | `P4 Foto-Spread` extends y=189-297 — y_bottom intrudes into footer band y=283-297 | Crop photo to y_bottom=283 |
| 3 | 7 | RIGHT body | Body content starts at y=37 — intrudes into header band y=20-49 | Move all body frames down to y=49+ |
| 4 | 9 | RIGHT body | Body content starts at y=37 (same drift as page 7) | Move all body frames down to y=49+ |
| 5 | 10 | LEFT body | Body-block X off-center: detector sees block at x=135-185 instead of x=20-190 | Investigate which body frames are present (post-spread page 10 has a single column at x=135 below the spread photo above); may be 2-column variant |
| 6 | 13 | RIGHT body | Body content starts at y=37 (same as 7, 9) | Move all body frames down to y=49+ |

**Pages NOT in the drift list** (expected previously, now confirmed valid):
- Pages 12, 13 with full-bleed Dunkelgrün backgrounds — backgrounds are decoration, exempt from band rule. Body content on these pages still respects bands.
- Pages 4, 8, 12 with image-bottom layout — image inside free zone, body wraps; fine as long as image stays within y=49-283.
- Page 5's P4 Foto-Spread at y=189 — fine, just needs y_bottom crop.

---

## 2b. Interfaces

<interfaces>

```python
# tools/sla_lib/builder/brand_constraints.py
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]: ...
# Registry currently 15 rules (post-#24); #25 adds 1 → 16.

# tools/sla_lib/builder/bbox.py
def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """Page-local bbox honoring anchor + rotation. Returns None for items
    without spatial extent. Used by every spatial BrandRule."""

# tools/sla_lib/builder/document.py
@dataclass
class Page:
    width_pt: float; height_pt: float; bleed_mm: float
    items: list; is_master: bool; master_name: str; own_page: int
    page_xpos_pt: float; page_ypos_pt: float
class Document:
    pages: list[Page]; masters: list[Page]; facing_pages: bool
    template_id: str   # used by load_band_spec to find meta.yml

# tools/sla_lib/builder/meta_schema.py — to be EXTENDED in #25
def load_brand_overrides(slug, root=None) -> set[str]: ...
def load_band_spec(slug, root=None) -> dict | None: ...   # NEW per §4

# tools/sla_lib/builder/primitives.py
class _Frame: x_mm, y_mm, w_mm, h_mm, anchor, rotation_deg, anname, layer
class TextFrame(_Frame): style, fcolor, font, runs, ...
class ImageFrame(_Frame):
    src, image, fill, scale_type, ratio, local_scale, local_offset_mm,
    inline_image_data, inline_image_ext
class Polygon(_Frame): fill, line_color, line_width_pt, ...

# Existing side-detection helper from #22
SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)
```

</interfaces>

## 3. New BrandRule: `brand:band_consistency`

Replaces the originally-proposed three rules (`image_within_text_block`, `document_margins_consistent`, `text_card_size_consistent`). Single rule, simpler model.

### Rule semantics

```python
@dataclass(frozen=True)
class _BandConsistencyRule(BrandRule):
    """Body-pool pages have content (text + content-bearing image frames)
    confined to the header/free/footer bands and L/R margins specified in
    meta.yml::body_block_margins.

    Excluded pages and background-decoration frames are exempt.
    """
    tolerance_mm: float = 0.5

    def check(self, primitives, doc, constraints=None) -> list[Violation]:
        from sla_lib.builder.meta_schema import load_band_spec
        slug = getattr(doc, "template_id", "") or ""
        if not slug:
            return []
        spec = load_band_spec(slug)
        if spec is None:
            return []   # opt-out via missing meta key

        excluded = set(spec.get("excluded_pages", []))
        bands = spec["bands"]
        margins = spec["margins"]
        bg_fills = set(spec.get("background_decoration", {}).get(
            "fills", ["Dunkelgrün", "Hellgrün", "Magenta", "Gelb", "White"]))

        header_y_top = bands["header"]["y_top_mm"]
        header_y_bot = bands["header"]["y_bottom_mm"]
        footer_y_top = bands["footer"]["y_top_mm"]
        footer_y_bot = bands["footer"]["y_bottom_mm"]
        # free zone = (header_y_bot, footer_y_top)

        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            page_num = page.own_page + 1   # 1-indexed for users
            if page_num in excluded:
                continue   # feature page

            # Determine page side
            from sla_lib.builder.brand_constraints import SIDE_RX
            m = SIDE_RX.search(page.master_name or "")
            if not m:
                continue   # spine_safety covers unknown sides
            side = "left" if m.group(1).lower() == "links" else "right"
            side_margins = margins[side]
            outer_mm = side_margins["outer_mm"]
            inner_mm = side_margins["inner_mm"]
            pw_mm = page.width_pt * PT_TO_MM

            if side == "left":
                # LEFT page: outer = left edge, inner = right edge (spine)
                allowed_x_min = outer_mm
                allowed_x_max = pw_mm - inner_mm
            else:
                # RIGHT page: outer = right edge, inner = left edge (spine)
                allowed_x_min = inner_mm
                allowed_x_max = pw_mm - outer_mm

            for item in page.items:
                # Skip background decoration
                if _is_background_decoration(item, bg_fills):
                    continue
                # Skip frames with no spatial extent
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                # Check vertical bounds (must be inside free zone OR
                # in the appropriate header/footer band)
                anname = getattr(item, "anname", "") or ""
                # Header-band frames: text frames whose y0 is in header band
                # are accepted (they ARE the header). Same for footer.
                in_header = y0 >= header_y_top - self.tolerance_mm and \
                            y1 <= header_y_bot + self.tolerance_mm
                in_footer = y0 >= footer_y_top - self.tolerance_mm and \
                            y1 <= footer_y_bot + self.tolerance_mm
                in_free = y0 >= header_y_bot - self.tolerance_mm and \
                          y1 <= footer_y_top + self.tolerance_mm
                if not (in_header or in_footer or in_free):
                    violations.append(Violation(
                        severity="error",
                        rule_id=self.id,
                        message=(
                            f"frame {anname!r} on page {page_num} "
                            f"({side}) bbox y=[{y0:.1f}, {y1:.1f}] "
                            f"crosses band boundary. Bands: header "
                            f"[{header_y_top}, {header_y_bot}], "
                            f"free [{header_y_bot}, {footer_y_top}], "
                            f"footer [{footer_y_top}, {footer_y_bot}]. "
                            f"Either confine to one band, OR list page "
                            f"in excluded_pages, OR mark frame as "
                            f"background_decoration."
                        ),
                        targets=(anname or f"<unnamed y={y0:.1f}>",),
                    ))
                # Check horizontal bounds
                if x0 < allowed_x_min - self.tolerance_mm or \
                        x1 > allowed_x_max + self.tolerance_mm:
                    violations.append(Violation(
                        severity="error",
                        rule_id=self.id,
                        message=(
                            f"frame {anname!r} on page {page_num} "
                            f"({side}) bbox x=[{x0:.1f}, {x1:.1f}] "
                            f"exceeds margin spec [{allowed_x_min:.1f}, "
                            f"{allowed_x_max:.1f}] (outer={outer_mm}mm, "
                            f"inner={inner_mm}mm)."
                        ),
                        targets=(anname or f"<unnamed x={x0:.1f}>",),
                    ))
        return violations


def _is_background_decoration(item, bg_fills) -> bool:
    """Solid-fill polygon OR image-less ImageFrame with brand-color fill."""
    fill = getattr(item, "fill", None)
    if fill not in bg_fills:
        return False
    if isinstance(item, Polygon):
        return True
    if isinstance(item, ImageFrame):
        has_image = bool(item.image or item.src or
                         getattr(item, "inline_image_data", None))
        return not has_image
    return False
```

### What the rule catches in Zeitung

After Zeitung's 6 drift fixes land, the rule reports zero ERRORs. Before the fixes, it reports:
- Page 4: body block doesn't span 20-190 (exact violation message depends on which frames are present)
- Page 5: P4 Foto-Spread y_bottom=297 > footer band top=283
- Page 7: Body text frames y_top=37 < header band bottom=49
- Page 9: same as page 7
- Page 10: similar to page 4 — body block X drift
- Page 13: same as page 7

### What the rule does NOT catch (intentional)

- Pages 12 + 13 with full-bleed Dunkelgrün polygons → those polygons are background decoration, exempt.
- Pages 8 + 12 with image-bottom layouts → image is inside free zone, OK.
- Different content variants per page (text-grid vs photo-grid vs image-top vs image-bottom) → all OK as long as content stays in free zone.

---

## 4. `meta.yml` schema extension

Add `body_block_margins` field with this shape:

```yaml
body_block_margins:
  bands:
    header:
      y_top_mm: 20.0
      y_bottom_mm: 49.0
    footer:
      y_top_mm: 283.0
      y_bottom_mm: 297.0
  margins:
    left:
      outer_mm: 20.0
      inner_mm: 20.0
    right:
      outer_mm: 20.0
      inner_mm: 20.0
  background_decoration:
    fills: [Dunkelgrün, Hellgrün, Magenta, Gelb, White]
  excluded_pages: [1, 2, 10, 11, 14]   # 1-indexed
```

### Schema in `tools/sla_lib/builder/meta_schema.py`

```python
_BAND_SPEC_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["bands", "margins"],
    "properties": {
        "bands": {
            "type": "object",
            "additionalProperties": False,
            "required": ["header", "footer"],
            "properties": {
                "header": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["y_top_mm", "y_bottom_mm"],
                    "properties": {
                        "y_top_mm": {"type": "number"},
                        "y_bottom_mm": {"type": "number"},
                    },
                },
                "footer": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["y_top_mm", "y_bottom_mm"],
                    "properties": {
                        "y_top_mm": {"type": "number"},
                        "y_bottom_mm": {"type": "number"},
                    },
                },
            },
        },
        "margins": {
            "type": "object",
            "additionalProperties": False,
            "required": ["left", "right"],
            "properties": {
                "left": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["outer_mm", "inner_mm"],
                    "properties": {
                        "outer_mm": {"type": "number"},
                        "inner_mm": {"type": "number"},
                    },
                },
                "right": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["outer_mm", "inner_mm"],
                    "properties": {
                        "outer_mm": {"type": "number"},
                        "inner_mm": {"type": "number"},
                    },
                },
            },
        },
        "background_decoration": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "fills": {"type": "array", "items": {"type": "string"}},
            },
        },
        "excluded_pages": {
            "type": "array",
            "items": {"type": "integer", "minimum": 1},
        },
    },
}

def load_band_spec(slug: str, root: Path | None = None) -> dict | None:
    """Return parsed body_block_margins dict, or None if absent.
    Raises ValueError on schema violation."""
    p = _meta_path(slug, root)
    if not p.exists():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"meta.yml at {p} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        return None
    spec = data.get("body_block_margins")
    if spec is None:
        return None
    try:
        jsonschema.validate(instance=spec, schema=_BAND_SPEC_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(
            f"meta.yml body_block_margins at {p} malformed: {e.message} "
            f"(at path {list(e.absolute_path)})"
        ) from e
    return spec
```

### Zeitung's `meta.yml` addition

```yaml
body_block_margins:
  bands:
    header: {y_top_mm: 20.0, y_bottom_mm: 49.0}
    footer: {y_top_mm: 283.0, y_bottom_mm: 297.0}
  margins:
    left:  {outer_mm: 20.0, inner_mm: 20.0}
    right: {outer_mm: 20.0, inner_mm: 20.0}
  background_decoration:
    fills: [Dunkelgrün, Hellgrün, Magenta, Gelb, White]
  excluded_pages: [1, 2, 10, 11, 14]
```

---

## 5. Audit-tool wire-in

`tools/audit_alignment.py::_audit_doc()` already follows the pattern at lines 186-215 for `_SpineSafetyRule` and `_ImageFillsFrameRule`. Mirror that block for `_BandConsistencyRule`:

```python
# Issue #25: band consistency (replaces 3 originally-planned rules)
band_by_target: dict = {}
if check_brand_rules:
    from sla_lib.builder.brand_constraints import _BandConsistencyRule
    rule = _BandConsistencyRule(id="brand:band_consistency",
                                name="", description="")
    for v in rule.check(list(doc.iter_all_primitives()),
                        doc, constraints=constraints):
        for t in v.targets:
            band_by_target.setdefault(t, []).append(
                f"[{v.severity.upper()}] {v.message}"
            )
```

Add `band_consistency_warnings: list = field(default_factory=list)` to `PageAuditReport` (after `image_extent_warnings` at line 83). Distribute per-page in the existing `:303-323` loop. Include in `_report_has_findings` for `--strict` exit code semantics.

Markdown formatter at `:384-440` adds a "Band consistency" section per page.

---

## 6. Pre-applied overrides for non-Zeitung templates

The new rule applies globally. Other templates haven't been audited under the band model yet. Pre-apply overrides on these 7 templates so `--all` stays green during T01 of the PR:

| Template | meta.yml path |
|----------|---------------|
| infostand-tent-card-a5-quer | `templates/infostand-tent-card-a5-quer/meta.yml` |
| kandidat-falzflyer-din-lang | `templates/kandidat-falzflyer-din-lang/meta.yml` |
| plakat-a1-hochformat | `templates/plakat-a1-hochformat/meta.yml` |
| postkarte-a6-kampagne | `templates/postkarte-a6-kampagne/meta.yml` |
| themen-plakat-a3-quer | `templates/themen-plakat-a3-quer/meta.yml` |
| wahlaufruf-postkarte-a6-quer | `templates/wahlaufruf-postkarte-a6-quer/meta.yml` |
| wahltag-tueranhaenger | `templates/wahltag-tueranhaenger/meta.yml` |

Append to each template's `brand_overrides:` list:

```yaml
- id: brand:band_consistency
  reason: >-
    Scheduled for follow-up audit per #25 — band-consistency check added
    in #25 needs per-template body_block_margins spec authoring; deferred
    to follow-up issue. Zeitung is the only template with verified body-pool
    band model post-#25.
```

These templates can adopt the band model in follow-up issues as needed.

---

## 7. Codex visual review (verification gate)

Per #23/#24 pattern, the executor runs Codex visual review at the verification gate. NEW prompt for #25 distinct from #23 (alignment) and #24 (INJECT_MAP):

`prompts/zeitung-band-consistency-audit.md`:

```markdown
# Zeitung A4 — band-consistency visual audit

Read each rendered preview page in
`templates/zeitung-a4-grun/page-{01..14}.png` (zero-padded).
You MUST open each PNG and visually inspect it. Do not skip any page.

For each page, verify the band model:

- HEADER band: y=20-49 mm. Should contain ONLY the page number, date,
  breadcrumb header. No body content should appear above y=49.
- FOOTER band: y=283-297 mm. Should contain ONLY the page number /
  small footer text. No body content should appear below y=283.
- LEFT/RIGHT margins: 20 mm on each side. Body content (text + image)
  should not extend past x=20 or x=190.
- BACKGROUND DECORATION: full-bleed Dunkelgrün or Hellgrün polygons
  CAN extend past these bands — they are decoration, not content. Do
  not flag them.
- FEATURE PAGES (1, 2, 10, 11, 14): excluded from the band rule.
  Cover, hero spread, back. Do not flag content extents on these pages.

For each finding on body-pool pages (3, 4, 5, 6, 7, 8, 9, 12, 13),
report:

- Page: NN
- Frame (visual location): "<top-half image | bottom-band photo |
  middle text-column | etc>"
- What's wrong: brief factual description
- Likely y or x value (estimated from PNG)
- Severity: ERROR (extends into header/footer band, breaks combinability)
  | WARNING (margin drift &lt; 5mm)

Spread-baseline check: for each spread (LEFT + RIGHT pair), verify
that:
- Headlines (top of body content in free zone) start at the same y on
  both pages.
- Page numbers / footers are at the same y on both pages.

End with verdict:

<verdict value="pass|fail" body_pool_findings=N spread_baseline_findings=N>
  <one-paragraph summary>
</verdict>

Reference: Issue #25.
```

Cross-check Codex output against `bin/audit-alignment zeitung-a4-grun --json`. If Codex finds something audit misses, return to T01 to strengthen rule.

Iteration budget: 2 (pre-fix + post-fix). If post-fix Codex still flags, defer to #26.

---

## 8. Geometric invariant tests

Extend `tools/sla_lib/tests/test_zeitung_geometry.py` with a `BandConsistencyInvariantTests` class (replaces the originally-planned three test classes for image-within-text-block, margin consistency, text-card consistency).

```python
class BandConsistencyInvariantTests(unittest.TestCase):
    """Band-consistency model: every body-pool page has content within
    the header/free/footer bands and L/R margins. Background decoration
    is exempt; feature pages are exempt."""

    BODY_POOL_PAGES = [3, 4, 5, 6, 7, 8, 9, 12, 13]
    HEADER_Y_TOP = 20.0
    HEADER_Y_BOT = 49.0
    FOOTER_Y_TOP = 283.0
    FOOTER_Y_BOT = 297.0
    PAGE_W = 210.0
    LEFT_MARGIN = 20.0
    RIGHT_MARGIN = 20.0

    def _content_frames(self, page):
        """TextFrames + ImageFrames with image content."""
        from sla_lib.builder.primitives import TextFrame, ImageFrame
        for item in page.items:
            if isinstance(item, TextFrame):
                yield item
            elif isinstance(item, ImageFrame):
                has_image = bool(item.image or item.src or
                                 getattr(item, "inline_image_data", None))
                if has_image:
                    yield item

    def test_no_body_content_in_header_band(self):
        doc = _doc()
        for pn in self.BODY_POOL_PAGES:
            page = doc.pages[pn - 1]
            for item in self._content_frames(page):
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                # Frame's bbox must NOT overlap header band y=20-49 unless
                # it's a HEADER frame (entirely inside header band).
                y0, y1 = bbox[1], bbox[3]
                if y0 < self.HEADER_Y_BOT and y1 > self.HEADER_Y_BOT:
                    self.fail(
                        f"page {pn}: frame {item.anname!r} y=[{y0}, {y1}] "
                        f"crosses header-band boundary y={self.HEADER_Y_BOT}"
                    )

    def test_no_body_content_in_footer_band(self):
        # Mirror test for footer band
        ...

    def test_body_content_within_left_margin(self):
        # x bounds for LEFT body pages
        ...

    def test_body_content_within_right_margin(self):
        # x bounds for RIGHT body pages
        ...

    def test_specific_drift_fixes(self):
        """Pin the 6 specific drift fixes from this issue."""
        doc = _doc()
        # Page 5: P4 Foto-Spread y_bottom <= 283
        f, p = _frame_by_anname(doc, "P4 Foto-Spread")
        bbox = frame_bbox_mm(f, p)
        self.assertLessEqual(bbox[3], self.FOOTER_Y_TOP + 0.5)
        # Pages 7, 9, 13: body top >= 49
        for pn in (7, 9, 13):
            page = doc.pages[pn - 1]
            for item in self._content_frames(page):
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                # Body frames should be at y >= 49
                if isinstance(item, TextFrame) and item.w_mm < 60 and item.h_mm > 30:
                    self.assertGreaterEqual(bbox[1], self.HEADER_Y_BOT - 0.5,
                        f"page {pn}: body frame {item.anname!r} y_top={bbox[1]} "
                        f"intrudes into header band")
        # Pages 4, 10: body block x extent
        # (specifics depend on Phase 4 fix decisions)
```

These tests fail BEFORE the geometry fixes land; pass AFTER.

---

## 9. Per-page body-block extent observed (post-#24 main, before #25 fixes)

Captured 2026-05-09 via direct probe. For reference during planning.

| Page | Type | x_block | y_block (T, B) | Margin | Top | Bot | Notes |
|------|------|---------|----------------|--------|-----|-----|-------|
| 1 | cover | n/a | n/a | n/a | n/a | n/a | excluded — cover hero |
| 2 | LEFT (feature) | 20-190 | 130.7-277 | 20/20 | 130.7 | 20 | excluded — P1 Hero feature |
| 3 | RIGHT body | 20-190 | 51-277 | 20/20 | 51.4 | 20 | clean ✓ |
| 4 | LEFT body | 20-132 (col-3 short) | 49.5-277 | 20/77.7 (drift) | 49.5 | 19.3 | DRIFT (X) |
| 5 | RIGHT body | 20-190 | 49-185 + photo y=189-297 | 20/20 | 49.3 | 111 | DRIFT (P4 Foto-Spread into footer band) |
| 6 | LEFT body | 20.1-190.1 | 50.7-277.6 | 20/20 | 50.7 | 19.4 | clean ✓ |
| 7 | RIGHT body | 20-190 | 37-279 | 20/20 | 37 | 18 | DRIFT (T into header band) |
| 8 | LEFT body | 20.1-190.1 | 50.7-191 + image-bottom | 20/20 | 50.7 | 106 | clean ✓ (image inside free zone) |
| 9 | RIGHT body | 20-190 | 37-279 | 20/20 | 37 | 18 | DRIFT (T into header band) |
| 10 | LEFT (feature) | 20-185 | 130-280 | varies | n/a | n/a | excluded — P9 Spread half feature |
| 11 | RIGHT (feature) | 20-190 | 132-279 | 20/20 | 132 | 18 | excluded — P9 Spread half feature |
| 12 | LEFT body | 20-190 | 49-205 + image-bottom | 20/20 | 49.2 | 92 | clean ✓ (Dunkelgrün bg is decoration) |
| 13 | RIGHT body | 20-190 | 37-281 | 20/20 | 37 | 16.4 | DRIFT (T into header band) |
| 14 | back (feature) | n/a | n/a | n/a | n/a | n/a | excluded — feature/colophon |

Drift summary: pages 4, 5, 7, 9, 10, 13 (six pages, six fixes).

Spread-baseline mismatch (post-fix): all spreads of body-pool pages will share T=49 baseline ✓.

---

## 10. PR shape (planner refines)

Per locked atomic ordering (rules → audit wire-in → overrides → meta.yml → Codex pre-fix → fix Zeitung → regen → invariant tests → Codex post-fix):

1. **T01: feat(brand): add `brand:band_consistency` rule + `meta_schema.load_band_spec`**
   - New BrandRule per §3 skeleton + new schema function per §4.
   - Unit tests in NEW `tools/sla_lib/tests/test_brand_band_consistency.py` with synthetic mini-docs.
   - Update `test_brand_constraints.py::RegistryTests` 15 → 16.
2. **T02: feat(audit): wire band_consistency into audit_alignment**
   - Per §5 wire-in.
   - Update `test_audit_alignment.py`.
3. **T03: chore(meta): pre-apply overrides on 7 non-Zeitung templates**
   - Per §6.
4. **T04: chore(zeitung): add body_block_margins spec to meta.yml**
   - Per §4 Zeitung-specific addition.
   - Verify `structural_check zeitung` exits 1 (intentional pre-fix RED window — drift surfaces as ERRORs).
5. **T05: docs(reviews): Codex visual audit pre-fix baseline (verification gate)**
   - Run Codex per §7 prompt; output to `reviews/codex-zeitung-band-iter1.md`.
   - Cross-check vs audit JSON. STOP-and-iterate if Codex finds something audit misses.
6. **T06: chore(zeitung): apply 6 geometry fixes**
   - Per §2 table. Atomic single commit.
   - After commit: `structural_check zeitung` returns to exit 0.
7. **T07: chore(zeitung): regenerate template.sla + gallery via bin/render-gallery + SHA bump**
   - `bin/render-gallery zeitung-a4-grun --skip-visual-diff`.
   - Verify `bin/check-stale-previews` exit 0.
8. **T08: test(zeitung): add BandConsistencyInvariantTests**
   - Per §8 skeleton. ≥6 tests covering the band/margin invariants.
9. **T09: docs(reviews): Codex visual audit post-fix verification + EXECUTION.md**
   - Re-run Codex; verdict pass with zero ERRORs.
   - If still flags, defer to #26.
   - Final EXECUTION.md commit; status flip.

11–12 commits total including artifact commits.

---

## 11. What was discarded vs the original ISSUE.md and earlier research drafts

The user dialogue revealed that the 3-rule model from the earlier research synthesis was over-engineered for the actual problem. **DISCARDED:**

- **`brand:image_within_text_block`**: covered by the unified band-consistency rule.
- **`brand:document_margins_consistent`**: covered by the unified band-consistency rule.
- **`brand:text_card_size_consistent`**: not needed. Pages 12-14 green-bg variation is decoration, exempt.
- **Per-spread layout-match enforcement**: contradicts the user-shuffle requirement.
- **Layout-variant catalog (standard/compact/image-top/image-bottom)**: replaced by free-zone tolerance + feature-page exclusion.
- **Compact RIGHT layout (T=37) on pages 7/9/13**: was an accidental drift, not a deliberate variant. Fix to T=49.
- **`brand:facing_page_margins_consistent` from ISSUE.md**: subsumed.

The codebase agent's earlier line-level analysis (`research/codebase.md`) and pitfalls agent's findings (`research/pitfalls.md`) remain on disk; the parts about asset paths, audit-tool integration patterns, test patterns, Codex prompt format, atomic-PR ordering, env audit are STILL VALID. Only the rule-design portions are superseded by §3 above.

---

## 12. Open questions for the planner / executor

Three small decision points that need resolution during planning or execution:

1. **Page 4 col-3 truncation fix**: page 4 has col-3 at h=39mm (vs cols 1+2 at h=100mm). Either (a) restore col-3 to full height (matches 3-col body grid expectation), or (b) declare page 4 as a 2-column variant inside the free zone (still combinable; just an internal layout choice). Visual review or design-doc check needed. Either way, the band-consistency rule passes (content stays in free zone).

2. **Page 10 body-block X drift**: detector saw block at x=135-185 instead of x=20-190. Investigate — page 10 is currently EXCLUDED (P9 Spread feature) so this may be moot. Confirm that page 10's status as feature page is correct before fixing.

3. **`brand:band_consistency` severity for header/footer band intrusion vs margin drift**: ERROR for both (current spec)? Or ERROR for band intrusion, WARNING for margin drift (more graceful)? Recommend ERROR for both — band intrusion breaks combinability; margin drift breaks visual consistency. Same severity simplifies the model.

---

## 13. Future extensibility (from user dialogue)

The architecture deliberately supports:

- **New body-pool page variants**: just author a new `page<N>.add(...)` block with content in bands+margins. Auto-validated. No code change.
- **New background-color variants** (Hellgrün, Gelb, photo-bg): add a full-bleed Polygon/ImageFrame with the bg color. Listed in `background_decoration.fills`. Combinable with everything else.
- **New feature pages**: append to `excluded_pages` list. Done.
- **New page-types** (e.g., insert pages with custom margins): add a new entry to `body_block_margins.margins` (e.g., `insert: {outer_mm: 15, inner_mm: 15}`). Other types unaffected.
- **Asymmetric inner≠outer margins** (gutter inset for perfect-bound editions): just change `outer_mm`/`inner_mm` values per side. Rule auto-validates.
- **Multi-language editions**: same architecture, different content. Bands/margins apply identically.

The model intentionally separates STRUCTURAL invariants (bands, margins, exclusions) from STYLISTIC choices (colors, content, layout). Bezirksgruppen own the stylistic layer; the architecture guarantees the structural layer.

---

## 14. Acceptance criteria (final, supersedes ISSUE.md)

- [ ] `brand:band_consistency` exists with full test coverage; severity ERROR for band/margin violations; per-template skip via `meta.yml::brand_overrides`.
- [ ] `meta.yml` schema extended with `body_block_margins` field (bands + margins + background_decoration + excluded_pages).
- [ ] Zeitung's `meta.yml::body_block_margins` populated per §4.
- [ ] Zeitung's 6 drift fixes applied per §2 table.
- [ ] 7 non-Zeitung templates have pre-applied `brand_overrides[brand:band_consistency]` skip.
- [ ] `python3 -m sla_lib.builder.structural_check --all` exit 0.
- [ ] `bin/audit-alignment zeitung-a4-grun --strict` exit 0.
- [ ] `python3 -m unittest discover tools/sla_lib/tests` exit 0.
- [ ] Codex visual review iter1 (pre-fix) cross-checked vs audit JSON.
- [ ] Codex visual review iter2 (post-fix) verdict = pass with zero band ERRORs.
- [ ] Geometric invariant tests in `test_zeitung_geometry.py::BandConsistencyInvariantTests` pin all 6 fixes.
- [ ] `bin/render-gallery zeitung-a4-grun --skip-visual-diff` regenerates template.sla + page-NN.png + meta.yml SHA.
- [ ] `bin/check-stale-previews` exit 0.
- [ ] Registry count test bumps 15 → 16.

---

## 15. Files touched (planner inventory)

- `tools/sla_lib/builder/brand_constraints.py` — add `_BandConsistencyRule` class + register
- `tools/sla_lib/builder/meta_schema.py` — add `_BAND_SPEC_SCHEMA` + `load_band_spec`
- `tools/sla_lib/tests/test_brand_band_consistency.py` — NEW
- `tools/sla_lib/tests/test_brand_constraints.py` — bump registry count 15 → 16
- `tools/audit_alignment.py` — wire rule into `_audit_doc()`
- `tools/sla_lib/tests/test_audit_alignment.py` — extend
- `templates/zeitung-a4-grun/meta.yml` — add `body_block_margins` block
- `templates/zeitung-a4-grun/build.py` — apply 6 drift fixes (pages 4, 5, 7, 9, 10, 13)
- `templates/zeitung-a4-grun/template.sla` + `template-preview.sla` + `page-*.png` + `preview.pdf` — regenerated artifacts
- 7 non-Zeitung `templates/*/meta.yml` — add override entry
- `tools/sla_lib/tests/test_zeitung_geometry.py` — add `BandConsistencyInvariantTests`
- `prompts/zeitung-band-consistency-audit.md` — NEW
- `reviews/codex-zeitung-band-iter1.md` — Codex pre-fix output
- `reviews/codex-zeitung-band-iter2.md` — Codex post-fix output
- `.issues/25-…/EXECUTION.md` — NEW
- `.issues/25-…/ISSUE.md` — status flip done

---

## 16. Confidence

- **HIGH** on the architectural model (band-consistency, content vs decoration, per-page-type margins, feature-page exclusion). Validated through extended user dialogue covering: combinability requirement, copy-and-rearrange user model, future bg variants, asymmetric margin support, page-type taxonomy (cover/feature/body-LEFT/body-RIGHT/back).
- **HIGH** on the 6 specific Zeitung drift fixes (verified via direct probe of post-#24 main).
- **HIGH** on the rule algorithm + meta_schema extension.
- **MEDIUM** on Codex prompt design (new prompt; pattern follows #23/#24).
- **MEDIUM** on per-template override list (pre-apply on all 7 non-Zeitung templates is conservative; specific templates may have valid band-consistency already and not need the override — verify in T03).

The architecture is intentionally MORE LENIENT than the originally-proposed three-rule model. It accepts more variation (different background colors, different free-zone content arrangements, different feature pages) while still guaranteeing the combinability property the user requires.

---

**End of RESEARCH.md.** The planner agent has everything needed to write PLAN.md with XML-tagged tasks for the executor. The executor has everything needed to implement without re-deriving the architecture.
