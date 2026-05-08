# RESEARCH — #14: Constraint DSL: page-bounds, aligned_below, SpreadImage utility

**Status:** synthesised from three parallel research dimensions (codebase / ecosystem / pitfalls). Confidence high on the architectural split, the offending Zeitung lines, the test patterns, the documentation surfaces. Medium on the Scribus rotation-pivot sign convention (one render-verify step before merge).

**Per-dimension reports:** `research/codebase.md`, `research/ecosystem.md`, `research/pitfalls.md`. The planner should read all three; this file is the synthesis.

---

## Summary

The issue extends the constraint DSL with three features. Two of the three independent agents converged on the same architectural split — that split is the load-bearing design decision the planner needs to internalise:

| Feature | Lives in | Why |
|---|---|---|
| `inside_page` | `tools/sla_lib/builder/brand_constraints.py` (as a `BrandRule` with id `brand:inside_page`) | Needs `(primitives, doc)` signature to read `page.width_pt / height_pt / bleed_mm`; the free-form `Constraint.check(primitives_by_anname)` signature has no doc/page access. Brand-rule placement also matches the issue's "global sweep, per-template skip via `meta.yml::brand_overrides`" requirement — the override mechanism exists *only* for brand-prefixed ids. |
| `aligned_below` | `tools/sla_lib/builder/constraints.py` (as a free-form `Constraint`, factory function next to `distance_y`) | Per-template opt-in via the `CONSTRAINTS = [...]` list; only needs anname-keyed primitives, not page geometry. |
| `SpreadImage` | `tools/sla_lib/builder/blocks.py` (new builder block following the `WahlkreuzSymbol` / `FoldedPanel` two-page-emit precedent) | Block utilities live in `blocks.py`; emits two `ImageFrame`s, anname pattern `f"{base} · left"` / `f"{base} · right"`. |

Implementation footprint is roughly: ~120 lines for the new `BrandRule` (rotation-aware bbox math + per-page iteration), ~30 lines for the `aligned_below` factory + dataclass, ~80 lines for `SpreadImage`, plus tests in `tools/sla_lib/tests/` (stdlib `unittest`, not pytest). All in pure Python — no new dependencies.

The acceptance-criteria language about "exactly two `inside_page` errors today" is verified: a code-only sweep (no rendering) found `P9 Spread` (`zeitung-a4-grun/build.py:1802-1811`) and an unnamed full-A4 image (`zeitung-a4-grun/build.py:2061-2071`) and nothing else with > 0.5 mm overflow.

---

## User constraints (lifted from CONTEXT — none was authored; using ISSUE.md text)

- **No image rendering** during this issue. All evaluation is code-only (read SLA / build.py, no PNG diffing). Reason from originating session: token budget at 97% for the week — the encoded constraint must replace the visual review.
- **Encode in code, not in render diffs.** New constraints go through `structural_check`, not visual_diff.
- **Atomic PR.** All five components ship together: the rule, the zeitung override, the existing-test updates, the new tests, and any docs. CI runs `set -euo pipefail` on `structural_check --all` (`.github/workflows/pages.yml:141-147`); a partial PR will turn CI red.
- **No new dependencies** beyond what's already in `pages.yml` (Python 3.13 + lxml + yaml + jsonschema + Pillow). The codebase explicitly opts out of constraint solvers (`composites.py:30`, `brand_constraints.py:5`).

---

## Codebase Analysis — interfaces

<interfaces>

### `Constraint` (free-form, per-template opt-in)

```
file: tools/sla_lib/builder/constraints.py
@dataclass(frozen=True)
class Constraint:
    id: str
    targets: tuple
    name: str = ""

    def check(self, primitives_by_anname: dict) -> list[Violation]: ...
    def referenced_annames(self) -> tuple: return self.targets
```

- Subclasses define their own `check`; factories (`same_y`, `same_x`, `same_size`, `mirrored_x/y`, `inside`, `equal_gap`, `hierarchy`, `same_style`, `distance_x/y`) auto-name via `_autoname(kind, targets, name)`.
- `_resolve(targets, mapping)` returns `(resolved_frames, missing_names)`; missing → single `_missing_violation` with `severity="warning"`.
- **`aligned_below` joins this list** as a new factory + `_AlignedBelowConstraint` dataclass.

### `BrandRule` (global sweep, override-skippable)

```
file: tools/sla_lib/builder/brand_constraints.py  (start of file)
@dataclass(frozen=True)
class BrandRule:
    id: str               # MUST match ^brand:[A-Za-z_0-9.]+$
    description: str

    def check(self, primitives, doc) -> list[Violation]: ...
```

Eight existing rules: `brand:colors`, `brand:fonts`, `brand:line_spacing_0.9`, `brand:line_spacing_1.3_bodytext`, `brand:hl_sub_gap_2x`, `brand:m_margin`, `brand:logo_size_3M`, `brand:bleed_3mm`. **`brand:inside_page` becomes the ninth.**

`structural_check` iterates `BRAND_CONSTRAINTS`, skips ids in `meta.yml::brand_overrides`, calls `rule.check(primitives, doc)`. Each `Violation` has its own severity; per-violation severity (warning vs. error) is novel but not blocked — the existing infrastructure prints whichever severity the rule assigns.

### `Document` and `Page` geometry

```
file: tools/sla_lib/builder/document.py
class Document:
    pages: list[Page]
    masters: list[Page]
    facing_pages: bool
    def iter_all_primitives(self): yield from every page item

class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float
    items: list[Primitive]
    is_master: bool
    master_name: str
    label: str
```

`width_mm = width_pt / 2.83464566929` (this is `PT_TO_MM` in helpers; codebase uses `width_pt` as source of truth, never the size kwarg, which has sub-ulp drift on round-trip templates — pitfall P-15).

### `ImageFrame` and friends

```
file: tools/sla_lib/builder/primitives.py
@dataclass
class ImageFrame:
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float
    rotation_deg: float = 0
    anchor: Optional[Anchor] = None
    anname: str = ""
    image: str = ""
    src: str = ""
    local_scale: tuple[float,float] = (1.0, 1.0)
    local_offset_mm: tuple[float,float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1
    ratio: int = 1
    pic_art: int = 1
    inline_image_data: Optional[bytes] = None
    inline_image_ext: Optional[str] = None
    xpos_pt: Optional[float] = None  # round-trip override
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None
    ...
```

- `_xy_pt()` (line ~ in `_Frame`): if `anchor is not None`, **ignores** `x_mm/y_mm` and uses `resolve_anchor(page.width_pt, page.height_pt, anchor)`. **inside_page bbox math must mirror this.**
- `local_offset_mm` is in **frame-mm at LOCALSCX=1**, NEGATIVE x for "shift the image to the left so the right half shows" — so `SpreadImage` right half passes `local_offset_mm=(-frame_w_mm, 0)`.

</interfaces>

### `structural_check` orchestrator

```
file: tools/sla_lib/builder/structural_check.py
- _load_build_module(slug): unique sys.modules key, drops cache → safe re-imports
- check_template(slug):
    1. mod.build_doc()
    2. iter_all_primitives → primitives_by_anname (anname-keyed)
    3. for c in mod.CONSTRAINTS: c.check(primitives_by_anname)
    4. load_brand_overrides(slug) → skip set
    5. for rule in BRAND_CONSTRAINTS: if not skipped: rule.check(primitives, doc)
- discover_template_slugs() → all templates/<slug>/ with build.py (ex _specs, _smoke)
```

`Page.is_master` exists; the planner must decide whether `brand:inside_page` checks masters or not — recommend **scope to non-masters only** (masters are abstract layout grids, not output pages).

### Test framework

- **stdlib `unittest`**, not pytest (no `pyproject.toml`, no `pytest.ini`, no `conftest.py` — verified by exhaustive find).
- Pattern: `class XTests(unittest.TestCase)`, sys.path preamble at top: `sys.path.insert(0, str(ROOT / "tools"))`.
- CI invocation: `python3 -m unittest discover tools/sla_lib/tests` (`pages.yml:105`).
- Existing files relevant: `test_constraints.py` (factory tests), `test_brand_constraints.py` (rule registry tests — **`test_eight_rules_exact` will break and must update to 9**), `test_blocks.py` (block emit tests).

---

## The two offending Zeitung frames (verified)

```python
# templates/zeitung-a4-grun/build.py:1802-1811 — print page 10
page9.add(ImageFrame(
    x_mm=210.0,  # ← page is 210 mm wide; frame begins AT the right edge
    y_mm=0.0,
    w_mm=210.0,  # ← extends another full page width into nowhere
    h_mm=126.13...,
    layer=...,
    image='',
    line_width_pt=...,
    anname="P9 Spread",
))
```

```python
# templates/zeitung-a4-grun/build.py:2061-2071 — print page 12
page11.add(ImageFrame(
    x_mm=210.0,
    y_mm=-0.18...,
    w_mm=210.8,
    h_mm=297.18...,
    ...
    anname="",  # unnamed
))
```

Both are bbox-on-the-wrong-page bugs in the upstream Scribus original (round-trip-faithful; this template is auto-generated from `gruene-zeitung-vorlage-original.sla`). The fix in #16 will move/split them; **this issue silences them** with a `meta.yml::brand_overrides` entry referencing #16.

There are also two ~0.8 mm right-edge nudges (page 12 + page 14, from float-imprecise bleed math during SLA emit) — those will be flagged as warnings (≤ 0.5 mm tolerance is the cutoff between warning and error per ISSUE acceptance) and are not blocking.

---

## Standard Stack (verified)

| Item | Value | Source |
|---|---|---|
| Python | 3.13 (system, indirect via Scribus 1.6.5 base image) | `Dockerfile.claude:13-15` |
| Test runner | `python3 -m unittest discover tools/sla_lib/tests` | `.github/workflows/pages.yml:105` |
| Lint | none enforced (ruff/mypy in image, no config files) | exhaustive `find` |
| Geometry deps | none, plain `math` | `composites.py:30`, `brand_constraints.py:5` |
| YAML | `pyyaml` (used in `meta_schema.py`) | imports |
| XML | `lxml` (used in reader/editor) | imports |

---

## Don't Hand-Roll

- **Bbox iteration:** `doc.iter_all_primitives()` is already there. New rule walks `(*doc.masters, *doc.pages)` and yields `(page, item)` pairs; do not re-implement.
- **Scribus `LOCALX/LOCALY` emission for `local_offset_mm`:** already wired in `primitives.py:807`. `SpreadImage` only needs to populate the field; it does not need new SLA emit code.
- **`meta.yml::brand_overrides` parsing:** `meta_schema.load_brand_overrides(slug, root)` already returns the skip set. No schema change for `brand:inside_page` (regex `^brand:[A-Za-z_0-9.]+$` already accepts it).
- **Pt → mm conversion:** read `page.width_pt` directly. Do not rely on the `size=(w_mm,h_mm)` kwarg (sub-ulp drift on round-trip).

---

## Architecture Patterns

### `inside_page` as a `BrandRule`

```
file: tools/sla_lib/builder/brand_constraints.py  (NEW — append to BRAND_CONSTRAINTS)

@dataclass(frozen=True)
class _InsidePageRule(BrandRule):
    tolerance_mm: float = 0.5

    def check(self, primitives, doc) -> list[Violation]:
        # IGNORE the flat `primitives` arg — walk doc.pages instead, since
        # only doc-level iteration carries (page, item) pairs.
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue                 # masters are abstract grids
            pw_mm = page.width_pt / PT_PER_MM
            ph_mm = page.height_pt / PT_PER_MM
            bleed = float(page.bleed_mm or 0)
            for item in page.items:
                bbox = _frame_bbox_mm(item, page)  # rotation- + anchor-aware
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                excess = (
                    max(0, x1 - (pw_mm + bleed)),
                    max(0, -(x0 + bleed)),
                    max(0, y1 - (ph_mm + bleed)),
                    max(0, -(y0 + bleed)),
                )
                worst = max(excess)
                if worst <= self.tolerance_mm:
                    continue
                sev = "error" if worst > self.tolerance_mm else "warning"
                # finer split: bleed-edge nudge vs full overflow
                if worst <= 1.0:
                    sev = "warning"
                else:
                    sev = "error"
                violations.append(Violation(
                    severity=sev,
                    rule_id=self.id,
                    message=(
                        f"frame {item.anname!r} bbox {(x0, y0, x1, y1)} "
                        f"exceeds page {page.label or page.master_name} "
                        f"(trim {pw_mm:.1f}x{ph_mm:.1f}, bleed {bleed:.1f}); "
                        f"excess(r/l/b/t)={excess}"
                    ),
                    targets=(item.anname or "<unnamed>",),
                ))
        return violations
```

Plus a helper:

```python
def _frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """(min_x, min_y, max_x, max_y) in page-local mm.

    - Honors anchor-positioned frames (anchor obliterates x_mm/y_mm — mirrors _Frame._xy_pt).
    - Rotation-aware around the frame's top-left corner (x_mm, y_mm).
    - Returns None for non-bbox items (Run, ParaStyle, master-page placeholder, etc.).
    """
    if not all(hasattr(item, a) for a in ("x_mm", "y_mm", "w_mm", "h_mm")):
        return None
    if getattr(item, "anchor", None) is not None:
        # mirror _Frame._xy_pt
        x_pt, y_pt = resolve_anchor(page.width_pt, page.height_pt, item.anchor)
        x_mm, y_mm = x_pt / PT_PER_MM, y_pt / PT_PER_MM
    else:
        x_mm, y_mm = item.x_mm, item.y_mm
    w, h = item.w_mm, item.h_mm
    rot = float(getattr(item, "rotation_deg", 0) or 0)
    return _rotated_bbox(x_mm, y_mm, w, h, rot)


def _rotated_bbox(x, y, w, h, deg):
    if deg == 0:
        return x, y, x + w, y + h
    rad = math.radians(deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
    rx = [px * cos_a - py * sin_a for px, py in pts]
    ry = [px * sin_a + py * cos_a for px, py in pts]
    return x + min(rx), y + min(ry), x + max(rx), y + max(ry)
```

Add `_InsidePageRule(id="brand:inside_page", description="…")` to `BRAND_CONSTRAINTS` list.

### `aligned_below` as a `Constraint`

```
file: tools/sla_lib/builder/constraints.py  (after distance_x)

@dataclass(frozen=True)
class _AlignedBelowConstraint(Constraint):
    gap_mm: float = 0.0
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list[Violation]:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        below, above = resolved  # targets order: (below, above) — image hangs from text
        # Skip if either is rotated (raw bbox math doesn't apply)
        if any(float(getattr(f, "rotation_deg", 0) or 0) != 0 for f in resolved):
            return [Violation(
                severity="warning",
                rule_id=self.id,
                message="rotated frame — aligned_below skipped",
                targets=self.targets,
            )]
        expected_y = above.y_mm + above.h_mm + self.gap_mm
        bad = []
        if abs(below.y_mm - expected_y) > self.tolerance_mm:
            bad.append(("y", below.y_mm, expected_y))
        if abs(below.x_mm - above.x_mm) > self.tolerance_mm:
            bad.append(("x", below.x_mm, above.x_mm))
        if not bad:
            return []
        return [Violation(
            severity="error",
            rule_id=self.id,
            message=f"aligned_below drift > {self.tolerance_mm}mm: {bad}",
            targets=self.targets,
        )]


def aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5,
                  name: str = "") -> Constraint:
    """`below` hangs from `above`: same x, below.y == above.y + above.h + gap."""
    t = _norm((below, above))
    return _AlignedBelowConstraint(
        id=_autoname("aligned_below", t, name), targets=t, name=name,
        gap_mm=gap_mm, tolerance_mm=tolerance_mm,
    )
```

### `SpreadImage` block

```
file: tools/sla_lib/builder/blocks.py  (new class)

@dataclass
class SpreadImage:
    """Two ImageFrames, one per facing page, sharing one source image.

    Right half uses local_offset_mm=(-page_w_mm, 0) so the source image
    "scrolls" left and the right half shows the right half of the picture.
    Both frames are inside_page-clean by construction (each sits at x=0
    on its own page).
    """
    image: str
    page_w_mm: float
    page_h_mm: float
    h_mm: float           # spread height (per-page; both halves identical h)
    y_mm: float = 0.0
    base_anname: str = ""
    scale_type: int = 0
    local_scale: tuple[float, float] = (1.0, 1.0)

    def emit(self) -> tuple[ImageFrame, ImageFrame]:
        left = ImageFrame(
            x_mm=0.0, y_mm=self.y_mm,
            w_mm=self.page_w_mm, h_mm=self.h_mm,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(0.0, 0.0),
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · left" if self.base_anname else "",
        )
        right = ImageFrame(
            x_mm=0.0, y_mm=self.y_mm,
            w_mm=self.page_w_mm, h_mm=self.h_mm,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(-self.page_w_mm, 0.0),  # ← negative x
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · right" if self.base_anname else "",
        )
        return left, right

    def place(self, page_left, page_right) -> tuple[ImageFrame, ImageFrame]:
        """Convenience: emit + add to two pages, return the frames for further use."""
        l, r = self.emit()
        page_left.add(l)
        page_right.add(r)
        return l, r
```

`scale_type=0` is **mandatory** (pitfall P-30): if left as default (1=auto-fit), Scribus auto-fits each half independently and the spread breaks visually.

---

## Common Pitfalls (consolidated; see `research/pitfalls.md` for the 30-item catalogue)

### Must-handle (HIGH severity)

1. **Anchor obliterates `(x_mm, y_mm)`** — `inside_page` must call the same `resolve_anchor` path that `_Frame._xy_pt()` uses, or anchor-positioned frames (e.g. `WahlkreuzSymbol`) get wrong bboxes.
2. **Rotation pivot is the top-left corner**, not the center, and **CCW positive** (deduced from existing rotated frames in plakat — verify with one render before merge).
3. **`local_offset_mm` is NEGATIVE x** for the right half of a spread image. Easy to flip the sign and ship a broken `SpreadImage`.
4. **9-rule registry update** — `tests/test_brand_constraints.py::test_eight_rules_exact` and `test_ids_are_canonical` will break. The module docstring at `brand_constraints.py:17` ("The eight rules:") also needs updating. Atomic update.
5. **Atomic PR** — `pages.yml:141-147` runs `structural_check --all` with `set -euo pipefail`. The PR must include the rule + the zeitung override + the test updates + the new tests, all together, or CI fails on push.
6. **Issue text doc-section references are wrong.** ISSUE.md says "SCHEMA.md §6" and "SPEC-WRITING-GUIDE.md §4" — actual locations are SCHEMA.md §12 (factory list at line ~493-495) and SPEC-WRITING-GUIDE.md §5/§8.

### Worth knowing (MEDIUM severity)

7. **Polygon `custom_path` doesn't change bbox** — `inside_page` uses `(x_mm, y_mm, w_mm, h_mm)`, the path is a clipping hint inside it.
8. **Per-violation severity is novel** — existing constraints emit one severity per check. The new rule emits warning (≤ 0.5–1.0 mm bleed-edge nudge) or error (> 1.0 mm full overflow) per violation. The orchestrator already prints whichever severity comes back; no infra change.
9. **`Page.add(block)` is single-page** — `SpreadImage` must either return `(left, right)` for the caller to add to two pages, or expose a `place(page_left, page_right)` method (recommended; planner: include both `emit()` and `place()`).
10. **`aligned_below` rotation handling** — return a warning Violation with `severity="warning"` and skip the math when either frame is rotated. Don't pretend non-axis-aligned frames have valid `y + h`.
11. **`PageBackground()` default form** emits a 220×310 mm polygon — would overflow A6 by ~118 mm. Production templates all use `.for_page(w, h)` so today nothing breaks, but `grep -rn "PageBackground(" templates/` is a 10-second sanity check before merge.
12. **`ImageFrame.xpos_pt / width_pt` round-trip overrides** bypass the `*_mm` fields. None of today's offending frames use them, so the planner can defer this edge case — but add a docstring note.

### Informational

13. Bleed is symmetric (`page.bleed_mm` is one float, applied to all four sides).
14. `_load_build_module` already drops sys.modules cache per slug — test isolation works.
15. Performance is O(N_frames) per template; sub-millisecond per template; CI budget unaffected.
16. **`SpreadImage` substrate already exists** — `local_offset_mm` and the LOCALX/LOCALY SLA-emit path are wired (`primitives.py:770`, `:807`). Block is pure DSL ergonomics.

---

## Environment Availability

- Python 3.13 ✓
- `lxml`, `pyyaml`, `jsonschema`, `Pillow` already pinned in `pages.yml`.
- No new deps. No new test framework. No lint gate.
- Network: **not needed**. All work is local.

---

## Project Constraints

(From `CLAUDE.md` if present, the issue body, and the originating session.)

- **Brand-rule fidelity** is the contract between brand and build. The 9-rule registry is canonical; do not introduce ad-hoc rules. New rule must follow `brand:<id>` naming and live in `BRAND_CONSTRAINTS`.
- **Three production templates** have committed Reference-SLAs (`zeitung-a4-grun`, `postkarte-a6-kampagne`, `plakat-a1-hochformat`); their `previews_for_sla` SHA stays valid after this issue (constraints are not emitted to the SLA — they're metadata).
- **Round-trip faithful** for those three: Zeitung's two overflowing frames are upstream bugs preserved in our build; the `meta.yml::brand_overrides` skip lets us flag them without breaking the round-trip contract.

---

## Sources (with confidence)

- **HIGH:** all interface signatures + line numbers — direct file reads via the codebase agent.
- **HIGH:** the two Zeitung frame locations (`build.py:1802-1811` and `:2061-2071`) — verified by code-only sweep, not pixel inspection.
- **HIGH:** test framework and CI invocation — `pages.yml` and existing `test_*.py` files read.
- **MEDIUM:** Scribus rotation-pivot sign convention (CCW positive) — deduced from the plakat ROT=270 case. **One render-verify** step before merge: open the emitted plakat in Scribus, confirm the rotated frame lands where the math predicts.
- **MEDIUM (forums) → HIGH (SLA structure):** the "two-frames-with-`local_offset_mm`" idiom is the only structurally clean way to encode a spread image. Scribus forum threads ([scribus-forums #819](https://forums.scribus.net/index.php?topic=819.0), [#2678](https://forums.scribus.net/index.php?topic=2678.0)) confirm GUI users straddle frames, but `PAGEOBJECT.OwnPage` is single-valued in SLA — exactly the `P9 Spread` bug. The split is the answer.

---

## Suggested PR shape (non-prescriptive — planner decides)

1. `feat(constraints): add brand:inside_page rule + rotation-aware bbox helpers`
2. `feat(constraints): add aligned_below factory`
3. `feat(blocks): add SpreadImage builder block`
4. `chore(zeitung): brand_overrides skip for inside_page (see #16)`
5. `test: 9-rule registry update + new constraint/block tests`
6. `docs: SCHEMA.md §12 + SPEC-WRITING-GUIDE.md catalogue entries`

Five-to-six commits on the feature branch. Atomic at the PR level.

Next: `/issue:plan` will turn this into XML-tagged tasks for the executor.
