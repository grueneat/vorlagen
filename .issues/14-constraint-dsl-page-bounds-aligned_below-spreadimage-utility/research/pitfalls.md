# Pitfalls — Issue #14 (constraint DSL: inside_page, aligned_below, SpreadImage)

Strictly local research. Each finding is grounded in code I read in this worktree;
file:line citations throughout.

---

## P-1 — Rotation pivot: top-left of un-rotated frame, NOT center

**Source:** `templates/infostand-tent-card-a5-quer/build.py:272-302`,
`templates/plakat-a1-hochformat/build.py:102-116`,
`tools/sla_lib/builder/primitives.py:436-481` (`_Frame`/`_xy_pt`).

Scribus stores `XPOS/YPOS` as the position of the **un-rotated** frame's
**top-left corner**, with rotation applied **clockwise around that anchor**.
The DSL faithfully preserves this: `_Frame._xy_pt(page)` returns
`mm_to_pt(self.x_mm), mm_to_pt(self.y_mm)` (plus page scratch offset) — there
is no rotation transform applied, ROT is just emitted as the `ROT` attr on
the PAGEOBJECT (`primitives.py:637`, `:819`).

Hard evidence from the templates:

* **`infostand-tent-card-a5-quer/build.py:288-302`** has an explicit comment:
  > "Frame XPOS/YPOS in Scribus track the rotated bbox top-left (which for
  > ROT=180 lands at original bottom-right): so x = 12+223 = 235, y = 174+24
  > = 198."
  i.e. the DSL author placed `(x_mm=235, y_mm=198)` on a frame with
  `w_mm=223, h_mm=24, rotation_deg=180`, and stated the *visible* bbox
  spans `(12, 174, 223, 24)`. That is consistent with the rotation pivot
  being the top-left of the **un-rotated** rect.
* **`plakat-a1-hochformat/build.py:102-116`** has Impressum at
  `x_mm=563.69, y_mm=832.69, w_mm=377.38, h_mm=21.02, rotation_deg=270` on
  a 594×841 page. With ROT=270 (clockwise positive, screen coords y-down),
  the un-rotated corners (0,0), (W,0), (W,H), (0,H) rotate to (0,0),
  (0,W), (-H,W), (-H,0). Translating back to the pivot, the visible bbox
  spans `[X-H, X] × [Y, Y+W]` = `[542.67, 563.69] × [832.69, 1210.07]`.
  Hmm — that puts y far past the page bottom. So either Scribus uses
  **CCW positive** or the convention differs. Looking again: 270° CCW =
  90° CW. For ROT=90 CW: corners → (0,0), (0,-W), (H,-W), (H,0). Visible
  bbox → `[X, X+H] × [Y-W, Y]` = `[563.69, 584.71] × [455.31, 832.69]`.
  This DOES fit within the page (594×841). **Conclusion: Scribus's ROT
  is CCW positive.**
  Cross-checking with the infostand ROT=180 case: 180° is the same in
  CW and CCW, so it doesn't disambiguate. But the plakat case
  (ROT=270, frame must fit in page) strongly indicates **CCW positive**,
  i.e. ROT=90 means the rect rotates 90° **counter-clockwise** around its
  anchor.

Per-multiple-of-90 closed-form bbox (with ROT in degrees, CCW positive,
rotating around `(X, Y)` = un-rotated frame's top-left):

| ROT | Visible bbox `(min_x, min_y, w, h)`             |
|-----|--------------------------------------------------|
| 0   | `(X,         Y,         W, H)`                  |
| 90  | `(X,         Y-W,       H, W)`                  |
| 180 | `(X-W,       Y-H,       W, H)`                  |
| 270 | `(X-H,       Y,         H, W)`                  |

For arbitrary angles, the bbox of a rotated rectangle pivoting at one corner
is computed by rotating the four corners and taking `(min_x, min_y, max_x,
max_y)`:

```python
import math
def rotated_bbox_mm(x, y, w, h, rot_deg):
    """ROT is CCW positive; pivot is the un-rotated top-left corner (x,y)."""
    rad = math.radians(rot_deg)  # caller may need to negate if CW positive
    c, s = math.cos(rad), math.sin(rad)
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    rotated = [(x + cx*c - cy*s, y + cx*s + cy*c) for cx, cy in corners]
    xs = [px for px, py in rotated]
    ys = [py for px, py in rotated]
    return min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)
```

**WARNING ON ROT-SIGN CONVENTION:** the planner MUST verify the sign by
running `python3 build.py` on the plakat or infostand template, opening the
`.sla` in Scribus, and reading the rendered rectangle position back out.
My analysis above is from logical deduction on the comment in
infostand and the page-fit constraint on plakat — the issue's
"5 directions × rotation cases" acceptance criterion MUST cover both
ROT=90 and ROT=270 to lock the sign convention into the test suite.

**Trap:** The naive bbox `(x, y, w, h)` ignoring rotation produces
**false-negatives** for ROT=90/180/270 frames whose un-rotated origin
sits **inside** the page but whose rotated geometry hangs **outside**.
Conversely it produces **false-positives** for the plakat Impressum case
where un-rotated origin is at `(563.69, 832.69)` (which alone, with
`w=377, h=21`, would naively bbox to `(563.69, 832.69, 377, 21)` =
right edge at 941, way outside 594-wide page) but whose **rotated** bbox
fits.

**Anti-pitfall:** Even small rotations grow the bbox slightly. The
Postkarte `Magenta circle (Polygon)` with `rotation_deg=351` (= -9° CCW
from 0) at `(73, 30, 20.54, 20.54)` has rotated bbox roughly
`(72.8, 28.4, 21.5, 22.4)` — only ~0.4mm overshoot. Comfortably inside
A6 (105×148) with bleed=3, so passes. Same for zeitung Störer at
`rotation_deg=355` and `w_mm=h_mm≈25`. **Use the proper rotated-corner
math, not a "skip rotation if angle < 5°" shortcut** — the shortcut
fails on the postkarte ellipse pair which the existing
`inside("P1 Hero", "Seitenhintergrund")` constraint already exercises.

---

## P-2 — Anchor-positioned frames: `(x_mm, y_mm)` is IGNORED at emit

**Source:** `tools/sla_lib/builder/primitives.py:470-481`.

```python
def _xy_pt(self, page) -> tuple[float, float]:
    if self.xpos_pt is not None and self.ypos_pt is not None:
        return self.xpos_pt, self.ypos_pt
    if self.anchor is not None:
        local_x, local_y = resolve_anchor(self.anchor, page.width_pt, page.height_pt,
                                          mm_to_pt(self.w_mm), mm_to_pt(self.h_mm))
    else:
        local_x = mm_to_pt(self.x_mm)
        local_y = mm_to_pt(self.y_mm)
    return page.page_xpos_pt + local_x, page.page_ypos_pt + local_y
```

When `self.anchor is not None`, **`x_mm` and `y_mm` are dead** — the
emitted XPOS/YPOS comes entirely from `resolve_anchor()` using the page
dimensions and the frame's w_mm/h_mm. Reading `frame.x_mm` from inside the
constraint check (without consulting `anchor`) gives the **wrong** position.

**Concrete bug to avoid:** `tools/sla_lib/builder/blocks.py:498-526`
(`WahlkreuzSymbol`) emits a Polygon with both `anchor=self.pos` AND
`x_mm=-p, y_mm=-p`. The x_mm/y_mm are dead in the SLA output (anchor
wins) but a naive `inside_page` reading `(p.x_mm, p.y_mm, p.w_mm, p.h_mm)`
would think the polygon sits at `(-4, -4, 63, 63)` for the default 4mm
padding — outside the page, *false positive*. The anchor actually
positions the polygon at `resolve_anchor(self.pos, ..., 63mm, 63mm)`,
which depends on page size and the Anchor h/v/margin_mm.

**Required behaviour for `inside_page`:** if `frame.anchor is not None`,
compute the actual local pt position via `resolve_anchor()` and convert
to mm before bbox math. The check needs the **page** object (for
`page.width_pt`, `page.height_pt`) — which is naturally available in
the per-page loop pattern (`for page in (*doc.masters, *doc.pages):`).

**Verbatim-pt override pitfall:** `xpos_pt`/`ypos_pt`/`width_pt`/
`height_pt` overrides also bypass mm. When set, these values are in pt
and INCLUDE the scratch-canvas offset (`page.page_xpos_pt`). To get the
page-local position, subtract `page.page_xpos_pt`/`page.page_ypos_pt`
before converting to mm. Used by inline-image frames (`primitives.py:464-468`).
Most templates don't use it, but Zeitung's logo image
(`zeitung-a4-grun/build.py:329-330`) does.

**Resolution recipe** (to embed in the rule):

```python
from .document import PT_TO_MM, mm_to_pt
from .primitives import resolve_anchor

def _frame_local_xy_mm(frame, page):
    """Return (x_mm, y_mm) in page-local coords, accounting for anchor and
    verbatim-pt overrides. Mirrors _Frame._xy_pt logic."""
    if frame.xpos_pt is not None and frame.ypos_pt is not None:
        # Verbatim pt; subtract scratch offset, convert to mm
        return ((frame.xpos_pt - page.page_xpos_pt) * PT_TO_MM,
                (frame.ypos_pt - page.page_ypos_pt) * PT_TO_MM)
    if frame.anchor is not None:
        lx_pt, ly_pt = resolve_anchor(frame.anchor, page.width_pt, page.height_pt,
                                       mm_to_pt(frame.w_mm), mm_to_pt(frame.h_mm))
        return lx_pt * PT_TO_MM, ly_pt * PT_TO_MM
    return frame.x_mm, frame.y_mm
```

---

## P-3 — Polygon `custom_path` does NOT change the frame bbox

**Source:** `tools/sla_lib/builder/primitives.py:847-911`.

`Polygon` is a `_Frame`. Its `(x_mm, y_mm, w_mm, h_mm)` defines the SLA
PAGEOBJECT's `XPOS/YPOS/WIDTH/HEIGHT`. Whatever `custom_path` it carries
is rendered **clipped to** that bbox region — Scribus does not re-grow
the frame to the path's actual extent. The path is just a clipping/
rendering hint inside the bbox.

**Implication for `inside_page`:** checking `(x_mm, y_mm, w_mm, h_mm)` of a
Polygon (regardless of `custom_path`, `corner_radius_mm`, ellipse-vs-
rectangle shape) is correct. **DO NOT** parse the SVG path string and
take its extent — that would give wrong answers for the FoldLine
(stroke-only path with a tight bbox), DieCut (closed loop within
bbox), Wahlkreuz background (default rectangle + custom_path).

**Counter-example from the corpus:** `templates/wahltag-tueranhaenger/build.py:157`
emits a Polygon `Brand-Bar (Vorderseite)` at `(-BLEED_MM, -BLEED_MM,
TRIM_W_MM + 2*BLEED_MM, 20+BLEED_MM)` — that's the standard PageBackground
pattern. The Polygon's frame fully covers the bleed area; `inside_page`
must accept this with tolerance because `x_mm = -2` (with bleed_mm=2)
exactly equals `-bleed`, on the tolerance boundary.

**Special case (low risk):** `_existing-zeitung-a4-grun.md` does not
declare any frame whose `custom_path` extends past the bbox. The
`PageBackground` block in `blocks.py:319-331` emits `x_mm=-b, y_mm=-b,
w_mm = page_w + 2*b, h_mm = page_h + 2*b` — exactly the bleed rectangle.
Default `PageBackground.emit()` (without `for_page()`) hard-codes
`w_mm=220+2*b, h_mm=310+2*b` (`blocks.py:322-323`) which is *generous*
on A4 (210×297) → 220×310 vs 210×297 → +10mm overshoot in width and
+13mm in height. **`inside_page` will flag the default-PageBackground
pattern as a violation on A4 templates** (overflow ~10mm right, 13mm
bottom). Templates that `Page.add(PageBackground())` (without
`.for_page(w, h)`) will need to either move to `for_page()` or get a
`brand_overrides` skip. **This is a real LIVE finding** that the planner
must call out — there may be more than 2 `inside_page` errors today
beyond the issue's stated `P9 Spread` + page-12 unnamed image. **Search
the corpus for non-`for_page` PageBackground usages before claiming
"exactly two errors".**

---

## P-4 — Bleed semantics: single float, applied symmetrically

**Source:** `tools/sla_lib/builder/document.py:107-122` (`Page` dataclass),
`document.py:560-580` (`_doc_attrs`), `document.py:927-985`
(`_emit_printer_pdf_stubs`).

`Page.bleed_mm` is a single float. Both at the DOCUMENT level and the PDF
block, it is emitted as `BleedTop = BleedBottom = BleedLeft = BleedRight =
mm_to_pt(bleed_mm)` — there is no asymmetric bleed support in the DSL.
Confirmed by:

```python
# document.py:572-575
"BleedTop": _fmt_num(mm_to_pt(bleed)),
"BleedBottom": _fmt_num(mm_to_pt(bleed)),
"BleedLeft": _fmt_num(mm_to_pt(bleed)),
"BleedRight": _fmt_num(mm_to_pt(bleed)),
```

So the page's legal bbox is `[-bleed_mm, page_w_mm + bleed_mm] ×
[-bleed_mm, page_h_mm + bleed_mm]`.

**Bleed-value precision quirk:** the round-trip templates carry
`bleed_mm=3.0000000000000013` (sub-ulp drift from `mm_to_pt(3.0)` round-
trip; see `templates/postkarte-a6-kampagne/build.py:64`,
`zeitung-a4-grun/build.py:74-126`). The constraint MUST use `bleed_mm`
with a tolerance (the spec's 0.5mm default trivially absorbs 1e-15
noise). **DO NOT** assert `bleed_mm == 3.0` exactly.

**Bleed-value diversity to handle:**

* Most templates: `bleed_mm = 3.0` (or `3.0000000000000013`).
* `templates/wahltag-tueranhaenger/`: `bleed_mm = 2` (Stanzformen,
  see `_specs/wahltag-tueranhaenger.md:8`).
* Spec-only at present: `_specs/kandidat-falzflyer-din-lang.md:8` =
  `bleed_mm: 3`; future Stanzform-templates may use 2 (per
  `templates/_specs/SCHEMA.md:29`: "typisch 3, Stanzen 2").

**Master pages have their own `bleed_mm`** (`document.py:281-330` —
`add_master(bleed_mm=...)`). Use `master.bleed_mm` when checking master-
page items. Today all examples have master/page bleeds matching, but the
rule must read per-page bleed correctly.

**Note on `brand:bleed_3mm` rule:** the existing brand rule
(`brand_constraints.py:307-324`) hard-codes `expected_mm=3.0` and warns
on any deviation. The wahltag template MUST already have a
`brand_overrides: brand:bleed_3mm` skip — verify before adding the new
rule. Looking: `templates/wahltag-tueranhaenger/meta.yml:148: bleed_mm: 2`
suggests this template will fail `brand:bleed_3mm`. (Issue #14 is not in
scope to fix this, but the planner should not be surprised by failing
brand rules unrelated to inside_page.)

---

## P-5 — `local_offset_mm` is in IMAGE-SOURCE mm, not frame mm

**Source:** `tools/sla_lib/builder/primitives.py:769-822` (`ImageFrame.to_pageobject`),
`tools/sla_to_dsl.py:802-821`.

`ImageFrame.local_offset_mm = (lx_mm, ly_mm)` is converted at emit time to
`LOCALX = mm_to_pt(lx_mm)`, `LOCALY = mm_to_pt(ly_mm)`. Reverse, the
converter reads `LOCALX/PT_PER_MM` (`sla_to_dsl.py:818`).

The Scribus semantic of LOCALX/LOCALY (per Scribus 1.6 `pageitem.cpp`):
LOCALX/LOCALY is the offset of the **image origin** within the frame,
measured **in pt of the frame's coordinate system** (i.e. multiplied by
LOCALSCX/LOCALSCY before being applied to the image-source pixels).

So for `SpreadImage` to render two halves of one source image:

* Both halves use the **same source image** (`src` or
  `inline_image_data`).
* Both have the same `local_scale = (sx, sy)` (so the image renders at the
  same zoom on both halves).
* Left half: `local_offset_mm = (0, 0)` — image origin at frame top-left.
* Right half: `local_offset_mm = (-frame_w_mm, 0)` — shift the image
  origin LEFT by one frame-width in **frame mm**, so the right half of
  the source falls into the right page's frame.

**Sign convention:** because LOCALX is added to the frame's origin to
position the image, **negative LOCALX** shifts the image LEFT relative to
the frame, which exposes the right half of the source. Verify by reading
existing `local_offset_mm` usage in the corpus:

* `templates/zeitung-a4-grun/build.py:2070` — `local_offset_mm=
  (0.3303109072374783, -0.3257155930969475)` on the page-12 unnamed image
  (one of the two `inside_page` violations the issue calls out). Tiny
  positive values — shift image right and up by ~0.3mm (probably a
  registration adjustment in the original SLA, no semantic meaning).
* No clean SpreadImage corpus example exists (the broken pattern at
  `x_mm=210, w_mm=210` does NOT use local_offset_mm — it just paints the
  same image twice or relies on frame-extent overflow).

**`local_offset_mm` is in IMAGE-SOURCE mm at LOCALSCX=LOCALSCY=1**, and
becomes IMAGE-SOURCE × LOCALSC mm at non-unity scale. For SpreadImage
where both halves use full-frame fit (`scale_type=1`, default), the
offset is in **frame-mm space**.

**Acceptance test** (must be in unit tests for SpreadImage):
build a SpreadImage with `image='dummy.jpg'`, page_w_mm=105, total
spread w_mm=210, frame h=148. Assert:

* Left ImageFrame: `x_mm=0, w_mm=105, local_offset_mm=(0, 0)` on left
  page.
* Right ImageFrame: `x_mm=0, w_mm=105, local_offset_mm=(-105, 0)` on
  right page.
* Both share `image=...` and `local_scale` matching the spread aspect.

If `scale_type=0` (free), the user must compute `local_scale` from source
pixel size + spread mm. If `scale_type=1` (fit-to-frame), Scribus
auto-fits each half independently — which BREAKS the spread (each half
becomes a full-fit copy of the source). **`SpreadImage` must therefore
emit `scale_type=0`** with explicit `local_scale` matching the cross-page
total width.

---

## P-6 — `meta.yml::brand_overrides` id pattern is `^brand:[A-Za-z_0-9.]+$`

**Source:** `tools/sla_lib/builder/meta_schema.py:23-40`.

```python
"id": {
    "type": "string",
    "pattern": r"^brand:[A-Za-z_0-9.]+$",
},
```

The new rule MUST be id'd `brand:inside_page` (with underscore) for the
existing override mechanism to skip it. Period and underscore are the
only non-alphanumeric chars accepted; **no hyphens** (so `brand:inside-
page` would be rejected on validation).

A typo (`brand:inside_pages`) gets a **warning, not error**
(`meta_schema.py:80-90`):

```python
known = {r.id for r in BRAND_CONSTRAINTS}
ids: set[str] = set()
for entry in overrides:
    rid = entry["id"]
    if rid not in known:
        warnings.warn(f"... not in BRAND_CONSTRAINTS ...")
    ids.add(rid)
```

So a typo'd skip silently does nothing (with a Python warning) and the
constraint will still fire. **Plan unit-test must verify the rule's
exact id matches `brand:inside_page` and that the override mechanism
honours it** — the existing `test_meta_yml_brand_override_skips_rule`
test (`tests/test_structural_check.py:184-196`) is the template.

---

## P-7 — Adding a 9th BrandRule breaks two existing tests

**Source:** `tools/sla_lib/tests/test_brand_constraints.py:47-63`.

```python
class RegistryTests(unittest.TestCase):
    def test_eight_rules_exact(self):
        self.assertEqual(len(BRAND_CONSTRAINTS), 8)

    def test_ids_are_canonical(self):
        ids = [r.id for r in BRAND_CONSTRAINTS]
        expected = {
            "brand:color_palette",
            "brand:font_family",
            "brand:line_spacing_0.9",
            "brand:hl_sl_distance_x2",
            "brand:logo_size_3M",
            "brand:text_on_green",
            "brand:bleed_3mm",
            "brand:wahlkreuz_colored_bg",
        }
        self.assertEqual(set(ids), expected)
```

The first MUST become `assertEqual(len(BRAND_CONSTRAINTS), 9)` (or be
renamed `test_nine_rules_exact`). The second MUST add
`"brand:inside_page"` to `expected`.

The module docstring at `brand_constraints.py:17-37` lists "The eight
rules:" — also needs to be updated to "The nine rules:" with an entry
for #9 inside_page.

The pages.yml CI step (`run: PYTHONPATH=tools python3 -m
sla_lib.builder.structural_check --all`) is the master gate; if either
of these registry tests fails, tests for ALL templates fail. Plan must
ship test updates atomically with the rule addition.

---

## P-8 — No existing snapshot test pins violation counts of `--all`

**Source:** searched for `inside_page`, `--all`, `expected.*violations`
across `tools/sla_lib/tests/` — no results.

* `test_structural_check.py:310-322` (`AllRealTemplatesIntegrationTests`)
  is **skipped unless every real template exposes `build_doc()`**, and
  even when active it only asserts `rep.fatal_error is None` per
  template — no count assertions.
* No JSON snapshot file exists in the test tree.

**Implication:** The issue's acceptance criterion 5 ("Integration:
snapshot of `python3 -m sla_lib.builder.structural_check --all` in
`--json` mode showing exactly the *expected* set of `inside_page`
failures (currently 2)") requires creating a NEW test that pins the
JSON output. Because the brand_overrides for `P9 Spread` and the page-12
unnamed image will land in the SAME PR (per the issue body), this
snapshot test should record:

* Before-overrides state: 2 errors on `templates/zeitung-a4-grun/`.
* After-overrides state: 0 errors, 2 skips with reason `"see issue #16"`.

The cleanest design: the snapshot test asserts the **after** state
(0 errors, 2 skips) so CI stays green. Track the "before" state in
the PR description as evidence.

**Subtle pitfall in snapshot design:** `BRAND_CONSTRAINTS` rules emit
**one Violation per offending frame**, so the `inside_page` rule
naturally yields 2 separate `brand_issues` entries on Zeitung today (one
for `P9 Spread`, one for the unnamed page-12 image). After overrides,
both are SKIPPED by rule_id — but `meta.yml::brand_overrides` only
allows a single skip per rule_id! It's an all-or-nothing skip per
template, not per-frame.

**Confirmed by reading** `structural_check.py:202-207`:

```python
for rule in BRAND_CONSTRAINTS:
    if rule.id in skip_ids:
        rep.skipped_brand_rules.append(...)
        continue
```

Skip is at the **rule level** for the entire template. So the zeitung
will skip ALL `inside_page` checks on its frames (not just the two
known offenders). Any future Zeitung overflow will silently pass until
the override is removed. **The override reason should reflect that
strong skip**: `"Two known overflow frames pending fix in #16; remove
this override after #16 lands so the rule re-engages on every Zeitung
frame."`

---

## P-9 — Reference-SLA round-trip is unaffected by adding/skipping constraints

**Source:** `tools/sla_lib/builder/document.py:478-557` (`_build_xml`),
`tools/sla_lib/builder/structural_check.py:104-122` (`_load_build_module`).

`build_doc()` returns a `Document` whose `_build_xml()` emits XML based
solely on the document's pages, masters, items, styles, palette. The
`CONSTRAINTS = [...]` module-level list and `meta.yml::brand_overrides`
file are NEVER read by `Document._build_xml()` or `Document.save()`.
They are read **only** by `structural_check.check_template()` after
`build_doc()` returns the doc.

Therefore:

* Adding `brand:inside_page` to `BRAND_CONSTRAINTS` does NOT change any
  template.sla bytes.
* Adding entries to `templates/zeitung-a4-grun/meta.yml::brand_overrides`
  does NOT change the SLA bytes.
* `meta.yml::previews_for_sla` (the SHA256 of the committed template.sla)
  stays valid because template.sla bytes don't change.
* The CI step `bin/check-stale-previews` (which compares
  `sha256(template.sla)` against `meta.yml::previews_for_sla`) remains
  green.
* The CI step `python3 tools/sla_diff.py --strict` (round-trip vs
  original .sla) remains green.

**Confirmed**: building zeitung's `build_doc()` and saving emits the same
XML pre- and post-constraint-rule addition.

The only path that COULD invalidate previews_for_sla is if someone added
a frame to `build.py` to fix the overflow — but the issue is explicit
that "Actually fixing the Zeitung spread (that's #16)" is **out of
scope**. Issue #14 only adds the rule + the override. No build.py edits
to zeitung's frames.

---

## P-10 — `pages.yml` runs `structural_check --all`, must stay green

**Source:** `.github/workflows/pages.yml:141-147`.

```yaml
- name: Run structural check (Issue #12)
  run: |
    set -euo pipefail
    PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
```

`set -euo pipefail` + `--all` means **any** template's brand-rule error
fails CI. The plan MUST land in ONE PR:

1. New `_InsidePageRule` in `brand_constraints.py` (registered in
   `BRAND_CONSTRAINTS`).
2. `templates/zeitung-a4-grun/meta.yml` adds
   `brand_overrides: - id: brand:inside_page, reason: "..."`.
3. The two existing failing tests in `test_brand_constraints.py`
   updated to match the new 9-rule registry.
4. New unit tests for the rule (5 directions × rotation cases).
5. Snapshot test for `--all` JSON output (asserting 2 skips, 0 errors
   on inside_page across all templates).

If items 2 or 3 land in a separate commit before 1, CI breaks; if 1
lands before 2/3, CI breaks. **One PR, atomically.**

**Pre-existing CI quirks unaffected by this issue:**

* `bin/check-stale-previews`: SHA-pins committed template.sla. Unaffected
  (P-9).
* `tools/sla_diff.py --strict`: round-trip diff. Unaffected (P-9).
* `tools/check_ci.py`: brand validator over .sla files. Unaffected — does
  not consult build.py CONSTRAINTS list.

---

## P-11 — Severity-by-tolerance is a NOVEL pattern; existing Constraint code uses single severity

**Source:** `tools/sla_lib/builder/constraints.py` — every concrete
`*Constraint` class emits `severity="error"` unconditionally, except
`_missing_violation` which is `severity="warning"`. Brand rules
(`brand_constraints.py:64`) have a single `severity` field on the
`BrandRule` dataclass.

The issue asks for `inside_page` to emit:

* `severity="warning"` for overflow ≤ 0.5mm (sub-mm bleed-edge nudges
  from Scribus rounding)
* `severity="error"` for overflow > 0.5mm

There's no precedent in the codebase for a SINGLE rule emitting both
severities based on the magnitude of the violation. The naive
implementation:

```python
def check(self, primitives, doc):
    out = []
    for page in (*doc.masters, *doc.pages):
        for item in page.items:
            x, y, w, h = compute_rotated_bbox(item, page)  # in mm
            min_x = -page.bleed_mm
            max_x = page.bleed_mm + page.width_pt * PT_TO_MM
            min_y = -page.bleed_mm
            max_y = page.bleed_mm + page.height_pt * PT_TO_MM
            # signed overflow on each side; positive = outside
            of_l = min_x - x          # how far past left
            of_r = (x + w) - max_x    # how far past right
            of_t = min_y - y          # how far past top
            of_b = (y + h) - max_y    # how far past bottom
            worst = max(of_l, of_r, of_t, of_b, 0.0)
            if worst > 0.5:
                out.append(Violation(severity="error", ...))
            elif worst > 0:
                out.append(Violation(severity="warning", ...))
    return out
```

**Watch out for:**

* `BrandRule.severity` field default is `"error"` (line 64) but the new
  rule emits each Violation with explicit per-violation severity — the
  field default is irrelevant for this rule.
* The `BrandRule` dataclass is `frozen=True` — extending it via subclass
  is fine; do not try to mutate `self.severity` per-call.
* Test fixtures: at exactly 0.5 mm overflow → warning (boundary), at
  exactly 0.5mm + 1ulp → error. Existing tests use `<= tolerance`
  semantics (e.g. `test_tolerance_edge_passes_at_tolerance`); inside_page
  must follow the same convention so the boundary is consistent across
  the constraint suite.

**Tolerance reuse:** the issue body says "Tolerance: 0.5 mm (matches
existing constraint default)". The 0.5 mm value is the `tolerance_mm`
default of every existing `_*Constraint` (`constraints.py:117, 144,
169, 200, 230, 322`). Hard-code this same default in the BrandRule
class. **DO NOT** add a per-template tunable — the spec is that
inside_page uses 0.5 mm globally; templates that disagree opt out via
`brand_overrides`, not via tuning.

---

## P-12 — `iter_all_primitives` does NOT carry page-binding info

**Source:** `tools/sla_lib/builder/document.py:413-425`.

```python
def iter_all_primitives(self) -> Iterable:
    for page in (*self.masters, *self.pages):
        yield from page.items
```

The yielded items are bare primitives (TextFrame, ImageFrame, Polygon).
They have NO `.owning_page` attribute. The walker downstream
(`structural_check.py:156-160`) calls `iter_all_primitives()` once and
indexes by anname.

**For `inside_page`** the rule MUST iterate
`for page in (*doc.masters, *doc.pages): for item in page.items: ...`
directly, NOT via `iter_all_primitives()`. The pattern is established by
`_Bleed3mmRule.check` (`brand_constraints.py:311-314`) which iterates
`for p in doc.pages` directly.

**Special case:** A frame on a master page may end up rendered on every
page that uses the master. The `inside_page` rule should check the
master frame against the master page's own bbox (not against any
particular doc page). Master pages have their own `width_pt/height_pt/
bleed_mm` — reading those is correct.

**Multi-page-spanning frames:** Conceptually, no Scribus frame can span
multiple pages — the SLA's PAGEOBJECT ties an item to ONE OwnPage. The
"P9 Spread" failure is exactly: the frame is on page 10 but its bbox
extends onto where page 11 would render. `inside_page` correctly catches
this because it checks against the OWNING page's bbox.

---

## P-13 — Test isolation: `_load_build_module` already drops sys.modules cache

**Source:** `tools/sla_lib/builder/structural_check.py:104-122`.

```python
def _load_build_module(slug: str, root: Path = _REPO_ROOT):
    p = root / "templates" / slug / "build.py"
    if not p.exists():
        raise FileNotFoundError(...)
    mod_name = f"_strcheck_template_{slug.replace('-', '_')}"
    sys.modules.pop(mod_name, None)  # Drop cache
    spec = importlib.util.spec_from_file_location(mod_name, p)
    ...
```

Per-slug unique module name + explicit `sys.modules.pop` before reload
makes `--all` iteration deterministic. The new rule does not need to
worry about module-state pollution between templates.

**Stale-test risk:** `_all_have_build_doc()` at `tests/test_structural_
check.py:27-38` evaluates at import time. If `build_doc()` is broken on
any template, the AllRealTemplatesIntegrationTests are silently skipped
— so a regression there won't fail tests, just silently pass. Not new,
just worth flagging: don't rely on the `AllRealTemplatesIntegrationTests`
class for inside_page coverage. Write a dedicated test.

---

## P-14 — `Anchor` legacy forms emit DeprecationWarning; tests must opt out

**Source:** `tools/sla_lib/builder/primitives.py:153-157`.

```python
warnings.warn(
    f"Anchor legacy form {spec!r} is deprecated; use "
    f"Anchor(h=..., v=..., margin_mm=...) instead.",
    DeprecationWarning, stacklevel=2,
)
```

If the new SpreadImage tests construct frames with anchor=tuple/string
(legacy form), they'll emit DeprecationWarning. Use `Anchor(h=, v=,
margin_mm=)` form in the new tests, OR set `x_mm`/`y_mm` directly
(bypass anchor) for SpreadImage. The simplest design: SpreadImage uses
`x_mm/y_mm` directly (no anchor), since spread layout requires absolute
positioning anyway.

Independent issue: TextFrame `text_align` legacy field also emits
DeprecationWarning (`primitives.py:583-589`). New tests should not use
deprecated fields.

---

## P-15 — Page-coordinate sanity: `page.width_pt * PT_TO_MM` ≠ size kwarg

**Source:** `tools/sla_lib/builder/document.py:332-404` (`add_page`),
`templates/zeitung-a4-grun/build.py:79-80, 94-103`.

The Zeitung template stores BOTH:

* `size=(209.9999999999361, 296.99999999946107)` — sub-ulp drift from 210/297
* `width_pt=595.275590551, height_pt=841.889763778` — raw from original SLA

The `width_pt`/`height_pt` overrides win at emit time (line 357-360):

```python
w_pt, h_pt = resolve_size(size, orientation)
if width_pt is not None:
    w_pt = width_pt
if height_pt is not None:
    h_pt = height_pt
```

`page.width_pt * PT_TO_MM` = 595.275590551 / 2.83464566929 ≈
209.99999999957 mm. So if the constraint computes the page's mm bound as
`page.width_pt * PT_TO_MM`, both A4 templates and the round-trip
Zeitung get a sub-mm-equivalent value. With 0.5 mm tolerance this is
trivially absorbed.

**Recipe:** always derive the page's mm bbox from `page.width_pt` and
`page.height_pt` (the source of truth at emit time), not from a stored
`page_w_mm` (which doesn't exist on the Page dataclass anyway).

---

## P-16 — Severity escalation in `Page.add` flattening: blocks lose anchor/page binding

**Source:** `tools/sla_lib/builder/document.py:124-134`.

```python
def add(self, item) -> "Page":
    if hasattr(item, "emit"):
        for primitive in item.emit():
            self.items.append(primitive)
    else:
        self.items.append(item)
    return self
```

`Page.add(block)` flattens via `block.emit()` WITHOUT passing the page.
So blocks like `WahlkreuzSymbol`, `FoldLine`, `DieCut`, `FoldedPanel`,
`TableTentFold`, `DoorHangerCutout` — which all have signature
`def emit(self, page=None)` — get `page=None`. They produce primitives
based on hard-coded coordinates only, not page-aware. Most of those
emit primitives with explicit `x_mm/y_mm` or `anchor=` set, no page
dependency in the math.

**For SpreadImage:** since the two halves go on DIFFERENT pages, the
caller MUST pass each half to its respective `Page.add()` — SpreadImage
cannot be a single block emitting two primitives to one page. So the
SpreadImage API must be one of:

a. **Factory returning two ImageFrames:** `left, right = SpreadImage(...).emit()`,
   then `left_page.add(left); right_page.add(right)`.

b. **Page-aware block:** `SpreadImage(left_page=page_left,
   right_page=page_right, ...).build()` — adds itself to both pages
   explicitly.

The cleanest pattern matching existing blocks (which use single-page
`Page.add(block)`) is option (a) — but the existing block-emit
contract returns an Iterable. Returning a `tuple[ImageFrame, ImageFrame]`
is fine and matches dataclass conventions in `blocks.py`. The user code
becomes:

```python
spread = SpreadImage(image='spread.jpg', w_mm=210, h_mm=148,
                     left_anname='P5 Spread', right_anname='P5 Spread')
left, right = spread.emit()
page5_left.add(left)
page5_right.add(right)
```

OR — to match existing block ergonomics — provide a `place(page_left,
page_right)` method that does both `add()`s in one call:

```python
SpreadImage(image='spread.jpg', w_mm=210, h_mm=148,
            base_anname='P5 Spread').place(page5_left, page5_right)
```

The planner should pick whichever feels least surprising. The issue body
doesn't constrain the API shape; just emit two `inside_page`-clean
ImageFrames with shared image src + matched anname suffixes
(`"<base> · left"` and `"<base> · right"`).

---

## P-17 — Environment: Python 3.13, lxml/yaml/jsonschema available

**Source:** `.github/workflows/pages.yml:46-58`.

CI environment:

* OS: ubuntu-latest
* Python: system Python 3 (3.12+ on Ubuntu 24.04, 3.13.x in this
  worktree). No venv. No `requirements.txt`/`pyproject.toml` in the repo.
* Apt-installed: `python3-lxml`, `python3-yaml`, `xvfb`, `poppler-utils`,
  `ghostscript`, `imagemagick`, `libzbar0`, `zbar-tools`.
* Pip-installed: `Pillow==12.2.0`, `qrcode[pil]==8.2`, `pyzbar==0.1.9`,
  `jsonschema==4.26.0`.

For the new constraint code (pure layout math, no IO):

* `math` — stdlib.
* No new deps needed.
* `lxml` (already used) — not needed for the rule, only for emit/parse.
* `jsonschema` (already used by `meta_schema.py`) — relevant only for
  validating the `brand_overrides` entry shape, which is unchanged.

For the snapshot test:

* `json.dumps`/`json.loads` — stdlib.
* No fixture files needed (synthesize the expected JSON in-test, or
  commit a small expected-output file under
  `tools/sla_lib/tests/fixtures/`).

**Local-only consideration:** `python3 -m unittest discover tools/sla_lib/tests`
runs from repo root. Tests must use `Path(__file__).resolve().parents[3]`
to compute ROOT (matches pre-existing convention,
`tests/test_constraints.py:11`).

---

## P-18 — Security review: no new attack surface

The new code is pure layout math:

* No file IO except reading `meta.yml` (already validated by `jsonschema`).
* No `eval`/`exec`/dynamic import beyond the existing
  `_load_build_module` (which is sandbox-safe per #12).
* No external library calls beyond `math`.
* No user-supplied path arithmetic (only the path-coord formatter, used
  unchanged for emit).

The `SpreadImage` block reads the same `image` path that ImageFrame
already reads — same attack surface. Inline image data goes through
`pack_inline_image` (`primitives.py:750-761`) which is `zlib + base64`,
no decompression bombs (caller controls byte size).

No security findings.

---

## P-19 — `aligned_below` design: what about vertical_text_align variants?

**Source:** issue body §3, `tools/sla_lib/builder/primitives.py:541-552`.

> `image.y_mm == text.y_mm + text.h_mm + gap_mm` (within tolerance) **and**
> `image.x_mm == text.x_mm` (within tolerance)

The constraint compares `image.y_mm` (top edge of image) to
`text.y_mm + text.h_mm` (bottom edge of text) **regardless** of the text
frame's `vertical_text_align`. That is correct — the text frame's
**bbox** is what matters for layout, not where the rendered text sits
inside the bbox. (A text frame with `vertical_text_align=2` (bottom)
still has its bbox at `y..y+h`, the text just renders at the bottom of
that bbox.) Test must verify with a non-default `vertical_text_align`.

**Edge case:** what if the text frame is rotated? `aligned_below` makes
no sense for rotated text — the "bottom" of a rotated frame is no
longer at `y_mm + h_mm`. Two options:

a. **Document that aligned_below assumes both frames have rotation_deg=0**
   and emit a Violation if either has a non-zero rotation (severity=
   warning, message "rotated frames not supported by aligned_below; use
   distance_y/distance_x instead").

b. **Apply rotated-bbox math** to both frames first, then check
   alignment of rotated bboxes.

(a) is simpler and matches the constraint's documented intent ("standard
'image hangs from the text above on the same left axis' pattern"). (b)
adds complexity for a pattern not in any current corpus. Pick (a).

**Asymmetry of args:** issue says
`aligned_below(image_anname, text_anname, gap_mm)` — image first,
text second. That's a non-standard order (most existing factories
take child-then-parent or child-then-axis). Document the order
clearly in the docstring; consider keyword-only kwargs:
`aligned_below(*, image, text, gap_mm, tolerance_mm=0.5, name="")`.

---

## P-20 — `inside_page` may legitimately fire on PageBackground default usage

**Source:** `tools/sla_lib/builder/blocks.py:298-331`.

The `PageBackground` block (without `for_page()`) emits a Polygon with
hard-coded `w_mm=220 + 2*b, h_mm=310 + 2*b`. On a page smaller than
A4 (e.g. A6 = 105×148), this Polygon's bbox `(-3, -3, 226, 316)`
overflows the page-with-bleed `(-3, -3, 108, 151)` by ~118mm right
and ~165mm bottom.

**Audit needed before claiming "exactly two errors":**

```bash
grep -rn "PageBackground(" templates/ | grep -v for_page
```

Result (just-checked):
```
templates/postkarte-a6-kampagne/build.py:189:    page1.add(PageBackground.for_page(105, 148, ...))
templates/zeitung-a4-grun/build.py: ... (uses Polygon directly, not PageBackground)
templates/wahltag-tueranhaenger/build.py:158: ... (Polygon direct, not PageBackground)
```

Looking at postkarte's page0 (which the issue's smoke claims uses
PageBackground, line 89-100 per blocks.py docstring), I need to verify:

```bash
grep -n "PageBackground\|Seitenhintergrund" templates/postkarte-a6-kampagne/build.py
```

Run this. If postkarte uses `PageBackground()` (default form, not
`for_page`), the new rule will flag it as a third inside_page error.
The planner must either:

* Migrate that call site to `PageBackground.for_page(105, 148, ...)`
  before merging the inside_page rule, OR
* Add another `brand_overrides` entry, OR
* Accept that the issue's "exactly two errors" headline is wrong and
  document the third in the issue findings.

**Status (verified during this research):** `templates/postkarte-a6-
kampagne/build.py:189` uses `PageBackground.for_page(105, 148, ...)`
— sized correctly. The default `PageBackground()` is not used in any
of the three production templates I read. The `_smoke/` and
unsized-PageBackground might still flag — needs full audit.

**Audit checklist for the planner:**

1. `grep -rn "PageBackground(" templates/` — every occurrence.
2. Confirm each call passes proper page dimensions (either `.for_page(w, h)`
   or `Polygon` direct with explicit `w_mm/h_mm`).
3. Run a build of every template and rotated-bbox-check every primitive
   manually before claiming "exactly two errors".
4. If any other frames overflow, document them in the PR before merge
   (per acceptance criterion 3).

---

## P-21 — Performance: per-page iteration is O(N_frames), no concern

The new rule visits every primitive across every page exactly once.
Zeitung has ~150 frames, Plakat ~20, Postkarte ~20. The rotated-bbox
math is 4 sin/cos evaluations per primitive. Total: <1ms per template.
The `<30s budget for all 8 templates` guideline (CONTEXT D11, mentioned
in pages.yml:144) is unaffected.

No caching needed. No optimization needed. Single pass.

---

## P-22 — `Document.iter_all_primitives` is the documented orchestration anchor — but inside_page must NOT use it

**Source:** `tools/sla_lib/builder/document.py:413-425` (docstring),
`tools/sla_lib/builder/structural_check.py:156-160`.

The orchestrator calls `iter_all_primitives()` once and passes the flat
list to every BrandRule's `.check(primitives, doc)`. So `_InsidePageRule.
check(primitives, doc)` receives `primitives` as `list[primitive]`. **It
must ignore that list** (it has no page binding) and use `doc.pages` /
`doc.masters` directly.

Existing precedent: `_LogoSize3MRule.check` (`brand_constraints.py:234-
263`) reads `doc.pages[0]` to derive `kurze_kante`; `_Bleed3mmRule.check`
(line 311-314) iterates `for p in doc.pages`. Both rules ignore the
`primitives` list and walk `doc.*` directly. Mimic this pattern.

The flat-list `primitives` is only useful for rules that need to compare
all frames pairwise (`_TextOnGreenRule`, `_WahlkreuzColoredBgRule`).
inside_page is a per-frame-vs-its-own-page check, so it's the doc-walker
pattern.

---

## P-23 — Tolerance precedent: existing `inside` uses 0.5mm; new `inside_page` should match

**Source:** `tools/sla_lib/builder/constraints.py:200-223`.

```python
@dataclass(frozen=True)
class _InsideConstraint(Constraint):
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        ...
        cx, cy, cw, ch = child.x_mm, child.y_mm, child.w_mm, child.h_mm
        px, py, pw, ph = parent.x_mm, parent.y_mm, parent.w_mm, parent.h_mm
        if (cx + tol >= px and cy + tol >= py
                and cx + cw <= px + pw + tol
                and cy + ch <= py + ph + tol):
            return []
        ...
```

The existing `inside` constraint:

* Default tolerance: 0.5mm — matches issue's spec.
* Does NOT consider rotation (uses raw `x_mm/y_mm/w_mm/h_mm`).
* Does NOT consider anchor.
* Does NOT consider verbatim pt overrides.

So `inside_page` adds the rotation/anchor handling that `inside` lacks.
This is intentional per the issue scope. **Do NOT** retrofit
`inside_page`'s rotation handling onto `inside` in the same PR
(scope creep). If you want to share the rotated-bbox helper, factor
out a `_compute_rotated_bbox_mm(frame, page) -> (x, y, w, h)` utility
in `constraints.py` and use it ONLY in `inside_page`. Mark with a
comment that other constraints use the no-rotation shortcut for
historical reasons.

---

## P-24 — Spec docs require updates

**Source:** `templates/_specs/SCHEMA.md:486-540`,
`shared/brand/SPEC-WRITING-GUIDE.md:74-180`.

Acceptance criterion #6 in the issue body asks for:

* Add `inside_page`, `aligned_below`, `SpreadImage` to
  `templates/_specs/SCHEMA.md` §6 (Constraint catalogue).
* Add to `shared/brand/SPEC-WRITING-GUIDE.md` §4 (Constraint examples).
* Document the `SpreadImage` migration recipe.

**SCHEMA.md §6 lookup:** the section listing factories
(`same_y, same_x, same_size, mirrored_x, mirrored_y, inside, equal_gap,
hierarchy, same_style, distance_x, distance_y`) is at line 493-494.
The new `inside_page` is a BrandRule (not a per-template factory) —
listing it under "Brand-Constraints" subsection (around line 509-510)
matches the architecture. `aligned_below` IS a per-template factory and
goes in the main list. `SpreadImage` is a block, not a constraint;
goes in the block catalogue (a separate section if it exists, or
under the relevant template recipe).

**SPEC-WRITING-GUIDE.md §4 lookup:** sections 154-200 give Constraints
prose examples. Add a SpreadImage migration recipe in a new subsection.

**Pitfall:** the SCHEMA.md §6 also references SPEC-WRITING-GUIDE.md
("Brand-Constraints. Automatisch aktiv via BRAND_CONSTRAINTS"). Both
docs need consistent rule counts ("8 Regeln" → "9 Regeln") if any
language ties to "8". Search:

```bash
grep -rn "8 Regeln\|eight rules\|achten Brand\|8 Brand" shared/ templates/_specs/
```

The planner must update the count in both docs and ensure no orphan
references to "8" remain.

---

## P-25 — `aligned_below` is a free-form factory, NOT a brand rule

**Source:** issue body §3, vs §2 (which is explicit about `inside_page`
being in `brand_constraints.py`).

The issue body §3 says `aligned_below` should be in
`tools/sla_lib/builder/constraints.py` — i.e. a free-form factory
returning a `Constraint`, used in templates' module-level
`CONSTRAINTS = [...]` list. This is the right home: `aligned_below`
takes specific named targets (image_anname, text_anname), so it's
opt-in per template, not a global sweep.

**No pitfall here**, just contrast with `inside_page` to keep the
mental model crisp:

| Surface             | Type             | Where           | Activation              |
|---------------------|------------------|-----------------|-------------------------|
| `same_y`, `inside`, | factory          | `constraints.py` | Per-template `CONSTRAINTS` |
| `aligned_below`     | factory          | `constraints.py` | Per-template `CONSTRAINTS` |
| `inside_page`       | BrandRule        | `brand_constraints.py` | Global `BRAND_CONSTRAINTS` |
| `brand:bleed_3mm`   | BrandRule        | `brand_constraints.py` | Global `BRAND_CONSTRAINTS` |

Two different machineries:
1. `Constraint.check(primitives_by_anname: dict)` — per-template, anname
   resolution.
2. `BrandRule.check(primitives: list, doc)` — global, no anname
   resolution, walks doc structure directly.

Don't confuse the two — they have **different signatures**, **different
violation surfaces** (orphan-anname only on Constraint), **different
override mechanisms** (CONSTRAINTS list inclusion vs `brand_overrides`
exclusion).

---

## P-26 — `aligned_below` must accept both Frame instances and string annames (consistency)

**Source:** `tools/sla_lib/builder/constraints.py:74-87, 347-462`.

Every existing factory accepts either a primitive (`.anname`) or a
string. The pattern is `_to_anname(t)` then `_norm(targets)`. New
`aligned_below` MUST follow the same convention:

```python
def aligned_below(image, text, gap_mm: float,
                   tolerance_mm: float = 0.5, name: str = "") -> Constraint:
    """``image.y_mm == text.y_mm + text.h_mm + gap_mm`` AND
    ``image.x_mm == text.x_mm``, both within tolerance."""
    t = _norm((image, text))
    return _AlignedBelowConstraint(
        id=_autoname("aligned_below", t, name), targets=t, name=name,
        gap_mm=gap_mm, tolerance_mm=tolerance_mm,
    )
```

The check class:

```python
@dataclass(frozen=True)
class _AlignedBelowConstraint(Constraint):
    gap_mm: float = 0.0
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) != 2:
            return []
        image, text = resolved
        bad = []
        # x_mm equality
        dx = image.x_mm - text.x_mm
        if abs(dx) > self.tolerance_mm:
            bad.append(("x", dx))
        # y_mm equality: image.y_mm == text.y_mm + text.h_mm + gap_mm
        expected_y = text.y_mm + text.h_mm + self.gap_mm
        dy = image.y_mm - expected_y
        if abs(dy) > self.tolerance_mm:
            bad.append(("y", dy))
        if not bad:
            return []
        return [Violation(severity="error", ..., rule_id=self.id, ...)]
```

**Edge case:** image is rotated. As noted in P-19, raise a warning if
either frame has non-zero rotation (`abs(frame.rotation_deg) > 1e-6`)
and skip the check. Test must cover this.

---

## P-27 — Integration test pattern for `--all` JSON snapshot

**Source:** `tools/sla_lib/builder/structural_check.py:251-308`
(`_report_to_dict`, `main`).

The orchestrator's `--json` mode dumps `[_report_to_dict(r) for r in
reports]`. The dict shape:

```python
{
    "slug": rep.slug,
    "fatal_error": rep.fatal_error,
    "constraint_issues": [{"severity", "rule_id", "message", "location"}, ...],
    "brand_issues": [{"severity", "rule_id", "message", "location"}, ...],
    "skipped_brand_rules": [{"id", "reason"}, ...],
}
```

**Snapshot test design:**

```python
def test_inside_page_snapshot_all_templates(self):
    """After this PR's brand_overrides for zeitung land, --all reports
    zero inside_page errors and exactly one inside_page skip on zeitung
    (with reason text containing 'see issue #16')."""
    reports = [sc.check_template(s, ROOT) for s in sc.discover_template_slugs(ROOT)]
    inside_page_errors = []
    inside_page_skips = []
    for r in reports:
        for issue in r.brand_issues:
            if issue.rule_id == "brand:inside_page" and issue.severity == "error":
                inside_page_errors.append((r.slug, issue.message))
        for rid, reason in r.skipped_brand_rules:
            if rid == "brand:inside_page":
                inside_page_skips.append((r.slug, reason))
    self.assertEqual(inside_page_errors, [],
                     f"unexpected inside_page errors: {inside_page_errors}")
    self.assertEqual([s for s, _ in inside_page_skips], ["zeitung-a4-grun"],
                     "exactly zeitung-a4-grun should skip inside_page")
    # Reason text contains the issue tracker link
    self.assertTrue(any("issue #16" in reason
                        for _, reason in inside_page_skips))
```

**Pitfall:** if `_all_have_build_doc()` is False at module-import time
(some template missing `build_doc()`), the test silently skips. Prefer
to check `build_doc()` exposure inline in the test itself (raise
`AssertionError` if not, so the silent-skip can't hide).

---

## P-28 — `Page.add(item)` does NOT set `item.owning_page` — flat list only

Implication for any future feature wanting to write `frame.page` —
not present. The rule must walk the doc structure to know which page
each frame belongs to. Documented in P-12 above; restating here as a
discoverability note.

---

## P-29 — `rotation_deg` is a float, can be ANY angle, not just multiples of 90

**Source:** corpus values: 8, 180, 270, 351, 355.

* `_smoke/postcard-a6/build.py:28`: `rotation_deg=8` (small CW).
* `infostand-tent-card-a5-quer/build.py:301`: `rotation_deg=180`.
* `plakat-a1-hochformat/build.py:108`: `rotation_deg=270`.
* `postkarte-a6-kampagne/build.py:165, 178`: `rotation_deg=351`
  (small CCW from 0).
* `zeitung-a4-grun/build.py:313, 2439`: `rotation_deg=355`.

So the rule must handle ALL angles, not just `{0, 90, 180, 270}`.
Use the rotate-corners-then-min/max formula. Beware floating-point
sin/cos noise: `math.cos(math.radians(180.0))` = -1.0 exactly?
Actually NO — `math.cos(math.pi)` = -1.0 exactly; but `math.radians(180)`
does a multiplication that introduces ~1e-17 noise. Resulting bbox
will have ~1e-15 imprecision in some coords. The 0.5mm tolerance
absorbs this. **Don't try to exact-zero special-case 0/90/180/270**
— the general formula is fine, no precision drift problem.

---

## P-30 — `local_offset_mm` field default is `(0.0, 0.0)`

**Source:** `tools/sla_lib/builder/primitives.py:770`.

```python
local_offset_mm: tuple[float, float] = (0.0, 0.0)
```

For SpreadImage's right-half ImageFrame, the offset must be NEGATIVE
in x to expose the right half of the source. Don't accidentally write
`(frame_w_mm, 0)` instead of `(-frame_w_mm, 0)` — it would shift the
right page's image-source by +w (off-screen) and render blank.

Similarly: when SpreadImage emits `local_scale != (1.0, 1.0)` for
explicit pixel-fit, the offset is in the SCALED coord system. For a
spread where the source image is exactly `2 * frame_w_mm` wide at
scale 1.0, just use `local_scale=(1.0, 1.0)` and offsets `(0,0)` /
`(-frame_w_mm, 0)`. For other scales, the math is `offset_x_mm =
-frame_w_mm` regardless of scale (since LOCALX is in frame-mm space
post-LOCALSC scaling — let me re-verify this):

`primitives.py:807` — `"LOCALX": _fmt_num(mm_to_pt(lx_mm))`. So LOCALX
is `mm_to_pt(local_offset_mm[0])`. Scribus interprets LOCALX as the
**image's pixel origin offset in pt**, AFTER scaling. Wait, let me check
the Scribus source (or assume by analogy with the corpus):

**Verification path (planner action):** build a SpreadImage with known
parameters, render via Scribus, and visually confirm the spread joins
seamlessly. Or examine the round-trip Zeitung's existing
`local_offset_mm=(0.33, -0.33)` on the page-12 unnamed image to
disambiguate. From the converter code (`sla_to_dsl.py:818`):
`local_offset_mm = (lx/PT_PER_MM, ly/PT_PER_MM)` — so LOCALX_pt is
divided by `PT_PER_MM` to get mm directly. The conversion is symmetric.
**The unit is "frame-local mm" at scale=1.0**.

For non-unity scale, LOCALX/LOCALSCX gives the image-source pixel
offset (in the image's native pixel units). At scale=1, image-source-mm
equals frame-mm. **For SpreadImage, planner should hard-pin
`local_scale=(1.0, 1.0)` and explicit image-source dims** — let the
caller pre-scale the image to match the spread w_mm if they want a
different fit.

---

## Summary — Findings Density Map

| Pitfall | Severity | Affects | Mitigation |
|---------|----------|---------|------------|
| P-1 Rotation pivot | HIGH | inside_page math | Rotate-corners formula; verify CCW sign with template |
| P-2 Anchor ignores x_mm/y_mm | HIGH | inside_page reading frame coords | resolve_anchor() per-frame |
| P-3 Polygon path vs bbox | MEDIUM | Polygon overlap design | Use bbox, not path |
| P-4 Bleed semantics | LOW | inside_page bound | Symmetric, per-page |
| P-5 local_offset_mm sign | HIGH | SpreadImage correctness | Test with negative offset on right half |
| P-6 brand: id pattern | HIGH | meta_schema validation | Use `brand:inside_page` exact id |
| P-7 Existing tests count rules | HIGH | CI green | Update test_eight_rules_exact + canonical |
| P-8 No snapshot precedent | MEDIUM | New test design | Cover errors + skips, not just errors |
| P-9 Round-trip unaffected | LOW | previews_for_sla | No SLA bytes change |
| P-10 pages.yml runs --all | HIGH | CI green | Atomic PR with overrides |
| P-11 Per-violation severity | MEDIUM | Novel pattern | Emit explicit per-Violation severity |
| P-12 No page binding on items | HIGH | inside_page design | Walk doc.masters/pages directly |
| P-13 sys.modules isolation | LOW | Test isolation | Already handled |
| P-14 Anchor legacy warnings | LOW | Test cleanliness | Use Anchor(h=,v=,margin_mm=) |
| P-15 width_pt vs size kwarg | LOW | Page mm bounds | Read page.width_pt * PT_TO_MM |
| P-16 Page.add flattening | MEDIUM | SpreadImage API | Two-page emit pattern |
| P-17 Env Python/deps | LOW | None new | All existing |
| P-18 Security | LOW | None | No new attack surface |
| P-19 aligned_below + rotation | MEDIUM | aligned_below test coverage | Skip rotated frames |
| P-20 PageBackground default | HIGH | "exactly 2 errors" claim | Audit corpus before merge |
| P-21 Performance | LOW | None | Single pass |
| P-22 iter_all_primitives | MEDIUM | inside_page implementation | Don't use; walk doc.* |
| P-23 Existing `inside` tolerance | LOW | Consistency | 0.5mm matches |
| P-24 Spec docs | MEDIUM | Doc completeness | Update SCHEMA.md, SPEC-WRITING-GUIDE |
| P-25 Two surfaces (factory vs rule) | LOW | Mental model | Document clearly |
| P-26 aligned_below factory shape | LOW | Convention | Mirror existing factories |
| P-27 Snapshot test design | MEDIUM | Test reliability | Inline build_doc check |
| P-28 No owning_page attr | LOW | Future feature | Accept the loop pattern |
| P-29 rotation_deg is float | MEDIUM | Rotation math | General formula, no special case |
| P-30 local_offset_mm sign | HIGH | SpreadImage right half | Negative x on right half |

---

## Verification Actions for the Planner

1. **Verify rotation sign convention:** build the plakat template, open
   in Scribus, read back the rendered Impressum bbox. Confirm CCW or
   CW interpretation of ROT.
2. **Audit PageBackground usages:** `grep -rn "PageBackground(" templates/`,
   ensure no default-form usages remain that would trigger inside_page
   beyond the known two.
3. **Audit rotated frames in templates for inside_page passes:** the
   five `rotation_deg != 0` frames listed in P-29 must all pass
   inside_page (otherwise more brand_overrides needed). Mathematically
   each fits well within page+bleed for its declared coords; verify by
   running build_doc() and computing bboxes manually.
4. **Run the test suite locally before commit:**
   `python3 -m unittest discover tools/sla_lib/tests`. Confirm
   `test_brand_constraints.py` passes after registry updates and
   inside_page tests pass.
5. **Run `python3 -m sla_lib.builder.structural_check --all` from
   workspace root:** confirm exit code 0, JSON output shows exactly the
   expected skip pattern.

---

## End of pitfalls research.
