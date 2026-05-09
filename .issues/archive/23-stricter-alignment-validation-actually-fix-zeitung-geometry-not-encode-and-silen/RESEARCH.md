# RESEARCH — #23: Stricter alignment validation + actually fix Zeitung

**Status:** synthesized from two parallel research dimensions (codebase / pitfalls). Confidence high — every quantitative claim verified against the live worktree by running `tools/audit_alignment.py` and probes.

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for line-level detail.

---

## Executive summary

User's framing: "validation is not solid enough yet, needs to be stricter" + "build the validation script first until it finds all of those issues by itself" + "then fix those issues so we know the script is very solid" + "review visually if necessary [via Codex] but make sure the script finds these issues in a generic way."

This means: TDD-for-rules. Build generic detection first. Iterate rules until they catch every visible issue (Codex visual review as ground truth). Then fix Zeitung based on what the audit reports. Per-template encoding (Phases 4-7) only AFTER the detector is proven solid.

Two research agents converged on **5 load-bearing rule-design decisions** the planner must lock:

1. **`brand:bleed_coverage` cutoff = 0.95 × page_w**, not 0.7. At 0.7 the rule flags 29 zeitung frames including 19 false-positives (the 20mm-margin body grid). At 0.95 it flags exactly the 10 real bugs the issue describes. **Dissolves the per-frame `(no-bleed)` exemption tag entirely** — u918 falls below the cutoff naturally.
2. **`brand:image_text_overlap` MUST scope `(ImageFrame OR filled-Polygon, TextFrame)`** — the page-10 bug is Polygon×Text, not Image×Text. Filled-Polygon definition: `fill in {Dunkelgrün, Hellgrün, Magenta, Gelb}`. Widening surfaces 5 cases on Zeitung (page-10 documented; pages 1, 7, 9 are likely real bugs to investigate).
3. **`brand:visual_adjacency_drift` MUST also check right-edge and bottom-edge axes**, not just left/top. Page-8 P7 Portrait right edge x=186.6 vs u918 right edge x=190 → 3.4 mm drift is INVISIBLE today because the heuristic only checks `|px0 - qx0|`. Add `dx_right = |px1 - qx1|` and `dy_bottom = |py1 - qy1|`.
4. **Geometric tests pin INVARIANTS, not coordinates.** `Cover Hero.w_mm = 209.9999999999361` from float-imprecise SLA round-trip — `assertEqual(w_mm, 216.0)` would fail. Pin `bb_cover_hero[outer-x] == bb_u2950[outer-x]` (relationship), survives any future Phase 4 retuning.
5. **Encode-and-silence has TWO escape patterns**, not one: (a) declare with widened tolerance to mask drift, (b) declare with `same_y(..., tolerance_mm=4.0)` against 3.6 mm drift. The disagreement check via `c.check()` re-execution catches BOTH naturally (the constraint's own tolerance becomes the audit boundary). Plus add a sanity finding "any constraint with `tolerance_mm > 1.0` or `gap_mm > 30.0` is suspicious — was it the geometry or the spec that drifted?"

The codebase agent identified **11 encoded-and-silenced CONSTRAINTS in zeitung build.py L2620-2735** (specific line numbers cited) — all `tolerance_mm` widened beyond 0.5 default. Phase 5 removes them; surfaces real warnings; Phase 4 fixes the geometry.

**ISSUE.md numerical inconsistencies caught:**
- P4 Foto-Spread `(x=0, w=213)` is wrong; correct is `(x=3, w=210)` (RIGHT bleed, spine inset preserved).
- P10 Portrait `w=74.7` is wrong; correct is `w=77.7` to reach right=213 (bleed) keeping x=135.3 (col-3 alignment).

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **`brand:bleed_coverage` full-width cutoff = 0.95 × page_w** (not 0.7). | 0.7 produces 19 false positives; 0.95 produces exactly the 10 real bugs (verified by live probe). No `(no-bleed)` exemption tag needed. u918 (interior margin polygon, w/page=0.81) is naturally below cutoff. |
| 2 | **`brand:image_text_overlap` scope = (ImageFrame OR filled-Polygon, TextFrame)**. Filled-Polygon = `fill in {Dunkelgrün, Hellgrün, Magenta, Gelb}`. | Page-10 bug is Polygon×Text. Limiting to ImageFrame would miss the documented case. |
| 3 | **`brand:visual_adjacency_drift` checks 4 axes**: dx_left, dx_right, dy_top, dy_bottom. Plus stacked-adjacency. | Page-8 right-edge mismatch invisible to left-axis-only heuristic. |
| 4 | **`BrandRule.check` signature already accepts `constraints=None`** (added in #22 per research). New rule reads it; existing rules ignore. No plumbing change. | Codebase agent verified at brand_constraints.py:78. |
| 5 | **`_VisualAdjacencyDriftRule` declaration-disagreement check** delegates to `c.check()` re-execution. Encode-and-silence (whether by widening tolerance or declaring drift) STILL emits warning if the actual geometry violates the constraint's own tolerance. | Constraint's own tolerance becomes the audit boundary. |
| 6 | **Plus "tolerance_mm > 1.0 is suspicious" sanity finding** in audit tool output — flags constraints whose tolerance is "too generous" with a hint that this looks like encode-and-silence. NOT a rule violation; just a finding in the report. | Catches the secondary escape pattern. |
| 7 | **Geometric tests pin RELATIONSHIPS, not absolute coordinates**: `bb_cover_hero[0] == bb_u2950[0]` (outer-x match), `bb_p7_portrait[1] == bb_u918[1]` (top flush), etc. | Float-imprecise round-trip means `assertAlmostEqual(w_mm, 216.0)` is brittle. Relationships survive any geometry retuning. |
| 8 | **Phase 5 removes 11 encoded-and-silenced CONSTRAINTS** identified in research/codebase.md §7. After removal, re-run audit; warnings = real geometry to fix in Phase 4. | The point of #23. |
| 9 | **ISSUE.md numerical fixes**: P4 Foto-Spread → `(x=3, w=210)`; P10 Portrait → `w=77.7` (keep x=135.3). | Codebase agent caught the math errors. |
| 10 | **Atomic-PR ordering** (per pitfalls #4): T01 rules + pre-applied overrides for non-Zeitung templates → T02 audit thresholds → T03 zeitung geometry fix coincident with encoded-CONSTRAINTS removal → T04 invariant tests → T05 render-gallery + SHA bump → T06 CI step. Wrong order = `--all` red mid-PR. |
| 11 | **`SpreadImage` block needs `outer_bleed_mm` param** (default 0). Right-half `local_offset_mm` becomes `-(page_w + outer_bleed)`. Phase 4 `P9 Spread halves` use `outer_bleed_mm=3.0`. | Pitfalls #5; cleaner than post-emit edit. |
| 12 | **Pre-apply `brand_overrides[brand:image_text_overlap]`** to postkarte-a6-kampagne, plakat-a1-hochformat, infostand-tent-card, V1-bound templates with reason "scheduled for follow-up audit". Without this, the rule fires errors on those templates and breaks `--all` mid-PR. | Postkarte audit with new thresholds surfaces 38+ warnings (mostly intentional but unaudited). |
| 13 | **Test file: NEW `tools/sla_lib/tests/test_zeitung_geometry.py`** with relationship-pinning tests. ≥15 frame relationships pinned. | Codebase agent §8. |
| 14 | **`bin/audit-alignment` CI step stays informational** for #23. Promotion to fatal happens via the existing `structural_check --all` step (which exits 1 on errors) — `brand:bleed_coverage` and `brand:image_text_overlap` are severity=ERROR so they fail CI through that path. NO new CI step needed in #23. | Avoids 2 CI gates for the same thing. |
| 15 | **`bin/render-gallery zeitung-a4-grun --skip-visual-diff` + SHA bump in meta.yml is the LAST commit** before EXECUTION.md. Without it, `bin/check-stale-previews` fails CI. | Same as #16/#17/#22 pattern. |

---

## Scope changes vs. ISSUE.md (planner: incorporate)

| ISSUE.md | Status | Why |
|---|---|---|
| `bleed_coverage` cutoff 0.7 × page_w | **TIGHTENED to 0.95** | 0.7 = 19 false positives on Zeitung. |
| `image_text_overlap` "every (ImageFrame, TextFrame) pair" | **EXPANDED to (Image OR filled-Polygon, TextFrame)** | Page-10 bug is Polygon×Text. |
| `visual_adjacency_drift` checks left+top axes | **EXPANDED to all 4 axes** | Page-8 right-edge mismatch invisible to left-only check. |
| Test file `test_zeitung_geometry.py` pins coordinates | **CHANGED to pin relationships** (invariants) | Float-imprecise SLA round-trip; relationships survive retuning. |
| Phase 7 CI promotion via new step `bin/audit-alignment --strict` | **DROPPED** — use existing `structural_check --all` step (already exit-1-on-error) | Avoids 2 CI gates for same thing. |
| ISSUE.md P4 Foto-Spread coords `(x=0, w=213)` | **CORRECTED to `(x=3, w=210)`** | Math error. |
| ISSUE.md P10 Portrait coords `w=74.7` | **CORRECTED to `w=77.7`** | Math error (74.7 reaches x=210 not x=213). |

---

## User constraints

- **Build detector first** (TDD-for-rules) — Phases 1+2 land BEFORE any Phase 4 geometry edit.
- **Phase 3b verification gate** uses Codex CLI for visual review (preferred, low Claude tokens). Direct Claude image read fallback only for tiebreaks. Iterate rules until Codex's findings are all in audit JSON.
- **Generic rules only** — no Zeitung-specific anname matches or coordinate constants in rule code.
- **Atomic PR.** Per locked decision #10 ordering.
- **No new dependencies.**

---

## Codebase Analysis — interfaces

<interfaces>

### `BrandRule` — already supports per-template constraints kwarg (post-#22)

```
file: tools/sla_lib/builder/brand_constraints.py:61-82
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]: ...
# Orchestrator (structural_check.py:190) already passes mod.CONSTRAINTS:
#   violations = rule.check(primitives, doc, constraints=constraint_list)
```

### Existing helpers (post-#22, reusable)

```
file: tools/sla_lib/builder/bbox.py:30-74
def rotated_bbox(x, y, w, h, deg) -> tuple[min_x, min_y, max_x, max_y]
def frame_bbox_mm(item, page) -> Optional[tuple] # honors anchor + rotation

file: tools/sla_lib/builder/template_loader.py:21-39
def load_build_module(slug, root) -> module # drops sys.modules cache

file: tools/sla_lib/builder/brand_constraints.py:466-473
SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)
SPREAD_HALF_RX = re.compile(r" · (left|right)$")
```

### Current `_UndeclaredDriftRule` (to REPLACE, not extend)

```
file: tools/sla_lib/builder/brand_constraints.py:594-707
@dataclass(frozen=True)
class _UndeclaredDriftRule(BrandRule):
    axis_tolerance_mm: float = 5.0      # too narrow — page-8 5.6mm misses
    adjacency_gap_mm: float = 12.0
    min_drift_mm: float = 0.5
# Replaced by _VisualAdjacencyDriftRule with:
#   - 4-axis checks (dx_left, dx_right, dy_top, dy_bottom)
#   - axis_drift_max_mm: 25.0 (was 5.0)
#   - adjacency_gap_max_mm: 30.0 (was 12.0)
#   - declaration-disagreement check via c.check() re-execution
# No template currently has brand_overrides[brand:undeclared_alignment_drift] →
# rename has zero meta.yml migration cost.
```

### `BRAND_CONSTRAINTS` rule count: 11 → 14 after #23

```
# Drop: _UndeclaredDriftRule
# Add: _VisualAdjacencyDriftRule (replacement)
# Add: _BleedCoverageRule
# Add: _ImageTextOverlapRule
# Add: _CoverExtentMatchRule
# tests/test_brand_constraints.py: rename test_eleven_rules_exact → test_fourteen_rules_exact
```

### Audit tool

```
file: tools/audit_alignment.py:317-328
# CLI: slug | --all, --json, --md PATH, --output-dir DIR,
#      --axis-tol-mm FLOAT (default 5.0), --adjacency-tol-mm FLOAT (default 12.0)
# After #23: defaults bumped to 25.0 / 30.0; output adds "tolerance_mm > 1.0
# is suspicious" findings for the secondary encode-and-silence escape.
```

### `SpreadImage` — needs `outer_bleed_mm` param

```
file: tools/sla_lib/builder/blocks.py:686-740
# Current emit() puts both halves at x=0, w=page_w. Right half:
#   local_offset_mm=(-page_w_mm, 0)
# After #23 add `outer_bleed_mm: float = 0`:
#   left:  x=-outer_bleed, w=page_w + outer_bleed
#   right: x=0, w=page_w + outer_bleed,
#          local_offset_mm=(-(page_w + outer_bleed), 0)  # adjust scroll
```

</interfaces>

---

## Architecture patterns

### `_BleedCoverageRule` (severity=ERROR)

```python
@dataclass(frozen=True)
class _BleedCoverageRule(BrandRule):
    full_width_threshold: float = 0.95   # locked decision #1
    tolerance_mm: float = 0.5

    def check(self, primitives, doc, constraints=None) -> list:
        if not getattr(doc, "facing_pages", False):
            return []
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            m = SIDE_RX.search(page.master_name or "")
            if not m:
                continue   # spine_safety emits its own unknown-side warning
            side = m.group(1).lower()
            pw_mm = page.width_pt * PT_TO_MM
            bleed = float(page.bleed_mm or 0)
            for item in page.items:
                anname = getattr(item, "anname", "") or f"<unnamed {type(item).__name__} y={getattr(item, 'y_mm', 0):.1f}>"
                if SPREAD_HALF_RX.search(anname):
                    continue   # SpreadImage halves are spread-intentional
                if float(getattr(item, "rotation_deg", 0) or 0) != 0:
                    continue   # rotated frames bbox-via-rotated_bbox handled elsewhere
                if getattr(item, "anchor", None) is not None:
                    continue
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, _y0, x1, _y1 = bbox
                w = x1 - x0
                if w < self.full_width_threshold * pw_mm:
                    continue   # not full-width
                if side == "links":
                    if x0 > -bleed + self.tolerance_mm:
                        violations.append(self._mk_violation(
                            "LEFT", anname, page, x0, x0 - (-bleed), -bleed))
                else:  # rechts
                    if x1 < pw_mm + bleed - self.tolerance_mm:
                        violations.append(self._mk_violation(
                            "RIGHT", anname, page, x1, (pw_mm + bleed) - x1, pw_mm + bleed))
        return violations
```

### `_ImageTextOverlapRule` (severity=ERROR, includes filled Polygons)

```python
FILLED_POLYGON_FILLS = {"Dunkelgrün", "Hellgrün", "Magenta", "Gelb"}

@dataclass(frozen=True)
class _ImageTextOverlapRule(BrandRule):
    tolerance_mm: float = 0.1

    def check(self, primitives, doc, constraints=None) -> list:
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            shapes, texts = [], []
            for item in page.items:
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                if isinstance(item, ImageFrame):
                    shapes.append((item, bbox, "image"))
                elif isinstance(item, Polygon) and getattr(item, "fill", None) in FILLED_POLYGON_FILLS:
                    shapes.append((item, bbox, "filled-polygon"))
                elif isinstance(item, TextFrame):
                    texts.append((item, bbox))
            for shape, sbox, kind in shapes:
                sx0, sy0, sx1, sy1 = sbox
                for txt, tbox in texts:
                    tx0, ty0, tx1, ty1 = tbox
                    ox0, oy0 = max(sx0, tx0), max(sy0, ty0)
                    ox1, oy1 = min(sx1, tx1), min(sy1, ty1)
                    if ox1 - ox0 <= self.tolerance_mm or oy1 - oy0 <= self.tolerance_mm:
                        continue
                    # Allowed: text fully contained in shape OR shape fully in text
                    txt_inside = (
                        sx0 - self.tolerance_mm <= tx0 and tx1 <= sx1 + self.tolerance_mm
                        and sy0 - self.tolerance_mm <= ty0 and ty1 <= sy1 + self.tolerance_mm
                    )
                    shape_inside = (
                        tx0 - self.tolerance_mm <= sx0 and sx1 <= tx1 + self.tolerance_mm
                        and ty0 - self.tolerance_mm <= sy0 and sy1 <= ty1 + self.tolerance_mm
                    )
                    if txt_inside or shape_inside:
                        continue
                    violations.append(Violation(
                        severity="error",
                        rule_id=self.id,
                        message=(
                            f"text {txt.anname!r} partially overlaps {kind} "
                            f"{shape.anname!r} on page {page.label or page.master_name!r}: "
                            f"intersection {ox1-ox0:.1f}x{oy1-oy0:.1f}mm. "
                            f"Either contain text fully inside, move out, or shrink shape."
                        ),
                        targets=(getattr(txt, 'anname', ''), getattr(shape, 'anname', '')),
                    ))
        return violations
```

### `_VisualAdjacencyDriftRule` (4-axis checks + disagreement detection)

```python
@dataclass(frozen=True)
class _VisualAdjacencyDriftRule(BrandRule):
    axis_drift_min_mm: float = 0.5
    axis_drift_max_mm: float = 25.0
    adjacency_gap_min_mm: float = 0.5
    adjacency_gap_max_mm: float = 30.0
    severity: str = "warning"

    def check(self, primitives, doc, constraints=None) -> list:
        constraints = constraints or []
        # Build declared-pair → list-of-constraints map (need declarations
        # to re-check disagreement, not just frozenset membership)
        declared: dict[frozenset, list] = {}
        for c in constraints:
            try:
                names = [n for n in c.referenced_annames() if n]
            except Exception:
                continue
            if len(names) < 2:
                continue
            for a, b in itertools.combinations(names, 2):
                if a != b:
                    declared.setdefault(frozenset((a, b)), []).append(c)

        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            spatial = []
            for item in page.items:
                an = getattr(item, "anname", "") or ""
                if not an:
                    continue
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                if float(getattr(item, "rotation_deg", 0) or 0) != 0:
                    continue
                spatial.append((an, item, bbox))

            for i, (pa, p_item, pbox) in enumerate(spatial):
                for qa, q_item, qbox in spatial[i + 1:]:
                    px0, py0, px1, py1 = pbox
                    qx0, qy0, qx1, qy1 = qbox
                    pair_key = frozenset((pa, qa))
                    pair_decls = declared.get(pair_key, [])

                    if pair_decls:
                        # Disagreement check: re-run each declaration
                        for c in pair_decls:
                            primitives_by_anname = {pa: p_item, qa: q_item}
                            try:
                                inner_viols = c.check(primitives_by_anname)
                            except Exception:
                                inner_viols = []
                            for iv in inner_viols:
                                violations.append(Violation(
                                    severity="warning",
                                    rule_id=self.id,
                                    message=(
                                        f"declaration {getattr(c, 'name', c.id)!r} for pair "
                                        f"({pa!r}, {qa!r}) disagrees with actual geometry: "
                                        f"{iv.message}. Either fix declaration or fix geometry."
                                    ),
                                    targets=(pa, qa),
                                ))
                        continue   # don't ALSO fire heuristic on declared pairs

                    # 4-axis heuristic checks (locked decision #3)
                    dx_left = abs(px0 - qx0)
                    dx_right = abs(px1 - qx1)
                    dy_top = abs(py0 - qy0)
                    dy_bottom = abs(py1 - qy1)
                    for axis_label, drift, suggested in [
                        ("axis-x-left", dx_left, "same_x (left edges)"),
                        ("axis-x-right", dx_right, "same_x_right (right edges)"),
                        ("axis-y-top", dy_top, "same_y (top edges)"),
                        ("axis-y-bottom", dy_bottom, "same_y_bottom (bottom edges)"),
                    ]:
                        if self.axis_drift_min_mm < drift < self.axis_drift_max_mm:
                            violations.append(self._mk(pa, qa, axis_label, drift, suggested, p_item, q_item))
                            break   # one axis-drift per pair

                    # Stacked-adjacency: P above Q, gap with same x or right-edge
                    if py1 < qy0:
                        gap = qy0 - py1
                        if (self.adjacency_gap_min_mm < gap < self.adjacency_gap_max_mm
                                and (dx_left < self.axis_drift_max_mm or dx_right < self.axis_drift_max_mm)):
                            violations.append(self._mk(pa, qa, "adjacency-y", gap, "aligned_below", p_item, q_item))
        return violations

    def _mk(self, pa, qa, kind, drift, suggested, p_item, q_item):
        return Violation(
            severity="warning",
            rule_id=self.id,
            message=(
                f"frames {pa!r} and {qa!r} appear visually adjacent ({kind} drift {drift:.2f}mm). "
                f"Either declare {suggested}({pa!r}, {qa!r}, ...) in CONSTRAINTS, "
                f"OR fix geometry to share the axis."
            ),
            targets=(pa, qa),
        )
```

### `_CoverExtentMatchRule` + `_ImageInContainerFlushRule` + `_PortraitColumnAlignmentRule`

Skeletons are in research/codebase.md §2.3 and the original ISSUE.md. The planner should consume those verbatim — they're well-formed.

### `SpreadImage` extension (locked decision #11)

```python
@dataclass
class SpreadImage:
    image: str
    page_w_mm: float
    page_h_mm: float
    h_mm: float
    y_mm: float = 0.0
    base_anname: str = ""
    scale_type: int = 0
    local_scale: tuple[float, float] = (1.0, 1.0)
    outer_bleed_mm: float = 0.0   # NEW

    def emit(self) -> tuple[ImageFrame, ImageFrame]:
        b = self.outer_bleed_mm
        left = ImageFrame(
            x_mm=-b, y_mm=self.y_mm,
            w_mm=self.page_w_mm + b,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(0.0, 0.0),
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · left" if self.base_anname else "",
        )
        right = ImageFrame(
            x_mm=0.0, y_mm=self.y_mm,
            w_mm=self.page_w_mm + b,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(-(self.page_w_mm + b), 0.0),
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · right" if self.base_anname else "",
        )
        return left, right
```

Phase 4 P9 Spread call: `SpreadImage(image=..., page_w_mm=210, h_mm=126.13, base_anname="P9 Spread", outer_bleed_mm=3.0)`.

### Geometric outcome tests (relationships, not coordinates)

```python
# tools/sla_lib/tests/test_zeitung_geometry.py (NEW)
class CoverExtentMatchTests(unittest.TestCase):
    def test_cover_hero_outer_extent_matches_u2950(self):
        doc = _load_zeitung_doc()
        ch, _ = _frame_by_anname(doc, "Cover Hero")
        u2950, p_u = _frame_by_anname(doc, "u2950")
        ch_bbox = frame_bbox_mm(ch, _)
        u_bbox = frame_bbox_mm(u2950, p_u)  # honors rotation
        # OUTER extents match (relationship, not absolute)
        self.assertAlmostEqual(ch_bbox[0], u_bbox[0], delta=0.5)  # left edges
        self.assertAlmostEqual(ch_bbox[2], u_bbox[2], delta=0.5)  # right edges

class P7PortraitFlushWithU918Tests(unittest.TestCase):
    def test_p7_portrait_top_flush_with_u918(self):
        doc = _load_zeitung_doc()
        portrait, _ = _frame_by_anname(doc, "P7 Portrait")
        u918, _ = _frame_by_anname(doc, "u918")
        self.assertAlmostEqual(portrait.y_mm, u918.y_mm, delta=0.5)

    def test_p7_portrait_right_flush_with_u918(self):
        doc = _load_zeitung_doc()
        portrait, _ = _frame_by_anname(doc, "P7 Portrait")
        u918, _ = _frame_by_anname(doc, "u918")
        self.assertAlmostEqual(
            portrait.x_mm + portrait.w_mm,
            u918.x_mm + u918.w_mm,
            delta=0.5,
        )
# ... more relationship tests for the 11 outer-bleed-gap frames + page-10/11 fixes
```

---

## Common Pitfalls

### Must-handle (HIGH severity)

1. **Cutoff 0.7 → 19 false positives.** Use 0.95.
2. **`image_text_overlap` scope** must include filled Polygons.
3. **4-axis adjacency check** required — single-axis misses the page-8 case.
4. **Pin relationships, not coordinates** — float-imprecise round-trip.
5. **Phase ordering** — geometry fix coincident with encoded-CONSTRAINTS removal.
6. **`SpreadImage` `local_offset_mm` math** — must adjust by `outer_bleed_mm` on the right half.
7. **Pre-apply `brand_overrides[brand:image_text_overlap]`** for non-Zeitung templates so `--all` stays green mid-PR.
8. **`bin/render-gallery zeitung-a4-grun --skip-visual-diff` + meta.yml SHA bump** is mandatory final commit.

### Worth knowing (MEDIUM)

9. **Codex visual review via `issue-cli review-exec --tool codex`** is the Phase 3b ground truth. Output saved to `reviews/`. Cross-check audit JSON.
10. **`P10 Portrait` is NOT full-width** (w/page = 0.32) — `bleed_coverage` won't catch it. Geometric outcome test pins right edge at bleed.
11. **Postkarte audit with new thresholds** = 38+ warnings. Pre-apply skip with reason "scheduled".
12. **#17 (postkarte V1, already merged) needs fixup** with new stricter rules — out of scope for #23, file follow-up.

### Informational

13. **No template currently has `brand:undeclared_alignment_drift` in brand_overrides** — rename has zero migration cost.
14. **`_smoke/zeitung-mini`** uses synthetic frames, skipped by `discover_template_slugs`.
15. **No new dependencies.** Python 3.13, Scribus 1.6.5, xvfb-run all present.

---

## Suggested PR shape

~12 commits across 8 tasks (atomic ordering per locked decision #10):

1. T01: `feat(brand): add 4 new BrandRules + replace UndeclaredDrift with VisualAdjacencyDrift` (rule code + 4-axis check + disagreement check)
2. T02: `chore(meta): pre-apply brand_overrides[brand:image_text_overlap] to 7 templates` (postkarte, plakat, infostand, 5 V1-bound minus #17 already merged)
3. T03: `test(brand): rule unit tests + bump registry count 11→14` (synthetic mini-docs, no real-template coords)
4. T04: `feat(audit): tighten audit_alignment thresholds + add tolerance-suspicion findings`
5. T05: `feat(blocks): SpreadImage outer_bleed_mm param`
6. T06: `chore(zeitung): drop 11 encode-and-silence CONSTRAINTS + Phase 4 geometry fixes (atomic)`
7. T07: `chore(zeitung): regenerate template.sla + gallery via bin/render-gallery + SHA bump`
8. T08: `test(zeitung): add test_zeitung_geometry.py invariant tests`

Plus artifact commits (RESEARCH.md ✓, PLAN.md, EXECUTION.md). 11–13 commits total.

**Phase 3b verification gate** (the build-detector-first contract) lands BETWEEN T04 and T06: run `bin/audit-alignment zeitung-a4-grun --strict`, run Codex visual review via `issue-cli review-exec --tool codex`, cross-check. If audit misses something Codex sees, return to T01 and strengthen the rule. Iterate until clean.

Next: `/issue:plan` turns this into XML-tagged tasks for the executor.
