# Plan: Stricter alignment validation + actually fix Zeitung geometry (not encode-and-silence)

<objective>
Build the alignment detector FIRST until it independently catches every visible Zeitung alignment failure (TDD-for-rules), THEN fix the Zeitung geometry the detector reports — never the other way around. This means: 4 new BrandRules (`brand:bleed_coverage`, `brand:image_text_overlap`, `brand:cover_extent_match`, `brand:portrait_column_alignment` — *deferred to T07/T08 per RESEARCH.md scope*) plus a replacement of `brand:undeclared_alignment_drift` with the broader-scope `brand:visual_adjacency_drift` (4-axis checks + declaration-disagreement detection); tightened `tools/audit_alignment.py` defaults + tolerance-suspicion findings; pre-applied `brand_overrides` for non-Zeitung templates so `--all` stays green mid-PR; a `SpreadImage.outer_bleed_mm` parameter so P9 Spread halves can extend to bleed; a hard verification gate via Codex visual review cross-checked against the audit JSON; THEN coincident Zeitung geometry fix + removal of 11 encode-and-silence CONSTRAINTS; THEN relationship-pinning invariant tests; THEN render-gallery + meta.yml SHA bump.

Why it matters: #22 added 2 alignment rules and an audit tool but the executor reported "0 suspicious adjacencies / structural_check green" while the Zeitung still has the same alignment failures the audit was meant to catch. Root cause: thresholds too loose (5 mm axis / 12 mm adjacency missed the page-8 5.6 mm case), scope too narrow (Polygon×Text page-10 bug invisible because rule only checked Image×Text), single-axis check (page-8 right-edge mismatch invisible because rule only checked left edges), and an `aligned_below(..., gap_mm=4.00, tolerance_mm=4.0)` escape hatch let the executor declare lazy adjacencies to silence warnings. This issue makes validation strict by default AND fixes the geometry — the rules become the test suite for the geometry, the geometry becomes the test suite for the rules.

Scope IN: 4 new BrandRules + 1 replacement (rename `_UndeclaredDriftRule` → `_VisualAdjacencyDriftRule`); audit tool default tightening + `tolerance_mm > 1.0` suspicion finding; pre-applied `brand_overrides[brand:image_text_overlap]` on 6 non-Zeitung templates with reason "scheduled for follow-up audit per #23"; `SpreadImage.outer_bleed_mm` param; **Phase 3b verification gate** (audit JSON + Codex visual review cross-check via `issue-cli review-exec --tool codex`); Zeitung Phase 4 geometry fix coincident with Phase 5 dropping 11 encode-and-silence CONSTRAINTS (atomic single commit); relationship-pinning invariant tests in NEW `tools/sla_lib/tests/test_zeitung_geometry.py`; `bin/render-gallery zeitung-a4-grun --skip-visual-diff` + meta.yml SHA bump.

Scope OUT: any rule code that hardcodes Zeitung-specific anname matches or coordinate constants (rules MUST be generic); per-frame `(no-bleed)` exemption tag (dissolved by 0.95 cutoff per locked decision #1 — u918 falls below cutoff naturally); a NEW CI step for `bin/audit-alignment --strict` (locked decision #14 — `brand:bleed_coverage` and `brand:image_text_overlap` are severity=ERROR so they fail through the existing `structural_check --all` step); fixup PR for #17 (postkarte V1, already merged) — out of scope, file follow-up; visual-pixel comparison by Claude (Codex CLI is the visual review channel); promoting `tools/audit_alignment.py` CI step to fatal (informational stays informational per pitfalls #F5); re-authoring Zeitung's design (geometry-drift fixes only).

No CONTEXT.md exists for this issue — decisions are per RESEARCH.md's 15-item locked-decision table (which itself records 4 design tightenings + 2 ISSUE.md numerical corrections vs. the original ISSUE.md). Where research conflicts with ISSUE.md, RESEARCH.md wins.
</objective>

<context>
Issue: @.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/ISSUE.md
Research: @.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/RESEARCH.md
Pitfalls research: @.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/research/pitfalls.md

<interfaces>
<!-- Executor: use these contracts directly. Do not re-explore the codebase for them. -->

# tools/sla_lib/builder/brand_constraints.py — current (post-#22)
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]: ...
# Locked decision #4: signature ALREADY accepts constraints kwarg (added in #22).
# No plumbing change. New rule reads it; existing rules ignore.

# Current registry: 11 rules (post-#22). After #23: 14 rules.
#   Replace _UndeclaredDriftRule → _VisualAdjacencyDriftRule (1:1)
#   Add _BleedCoverageRule, _ImageTextOverlapRule, _CoverExtentMatchRule
#   (Image-in-container-flush + Portrait-column-alignment from ISSUE.md
#    are FOLDED INTO the 4-axis VisualAdjacencyDrift rule's broader scope
#    per locked decisions #1+#3 — verified by RESEARCH.md probes that
#    page-8 P7 Portrait + page-11 P10 Portrait are caught by 4-axis drift
#    once the right-edge axis is checked. No separate rule classes.)

# Existing helpers (post-#22, reusable verbatim)
# tools/sla_lib/builder/bbox.py:30-74
def rotated_bbox(x, y, w, h, deg) -> tuple[min_x, min_y, max_x, max_y]
def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]   # rotation-aware

# tools/sla_lib/builder/template_loader.py:21-39
def load_build_module(slug, root) -> module                                     # drops sys.modules cache

# tools/sla_lib/builder/brand_constraints.py:466-473 (regex helpers)
SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)
SPREAD_HALF_RX = re.compile(r" · (left|right)$")

# tools/sla_lib/builder/primitives.py — primitive types touched by new rules
class ImageFrame:    anname, x_mm, y_mm, w_mm, h_mm, rotation_deg, anchor, scale_type, local_scale, local_offset_mm, image
class TextFrame:     anname, x_mm, y_mm, w_mm, h_mm, rotation_deg, anchor, ...
class Polygon:       anname, x_mm, y_mm, w_mm, h_mm, rotation_deg, anchor, fill, ...
PT_TO_MM = 0.3527777777777778

# tools/sla_lib/builder/constraints.py — Constraint base + factories
@dataclass(frozen=True)
class Constraint:
    id: str
    targets: tuple
    name: str = ""
    def check(self, primitives_by_anname: dict) -> list[Violation]: ...
    def referenced_annames(self) -> tuple: return self.targets
# 12 factories: same_x, same_y, same_size, same_style, equal_gap, hierarchy,
#   mirrored_x, mirrored_y, inside, aligned_below, distance_x, distance_y.

# tools/sla_lib/builder/document.py — facing-pages surface
class Document: facing_pages: bool; pages: list[Page]; ...
class Page: width_pt; height_pt; bleed_mm; items; is_master; master_name; label
# Page.is_left is HARDCODED False on every doc page (document.py:391-393).
# DO NOT trust it. Use SIDE_RX on master_name instead.
# Cover semantics: own_page=0 = RIGHT-alone, no facing LEFT (document.py:376-378
# + brand_constraints.py:514-520 special-case it).

# tools/sla_lib/builder/blocks.py:686-740 — SpreadImage (Issue #14, extended in #23)
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
    outer_bleed_mm: float = 0.0   # NEW in T05
    # After T05 emit() math:
    #   left:  x=-outer_bleed, w=page_w + outer_bleed,
    #          local_offset_mm=(0, 0)
    #   right: x=0, w=page_w + outer_bleed,
    #          local_offset_mm=(-(page_w + outer_bleed), 0)

# tools/audit_alignment.py:317-328 — current CLI
# slug | --all, --json, --md PATH, --output-dir DIR,
# --axis-tol-mm FLOAT (default 5.0), --adjacency-tol-mm FLOAT (default 12.0)
# After T04: defaults bumped to 25.0 / 30.0; --strict mode emits ERRORs;
# output adds tolerance_mm > 1.0 suspicion findings.

# tools/sla_lib/builder/structural_check.py — orchestrator (post-#22, unchanged for #23)
# At line ~190: violations = rule.check(primitives, doc, constraints=constraint_list)
# Exits 1 on any error-severity violation across any template; warnings tolerated.
# Locked decision #14: this IS the strict CI gate for #23. No new CI step needed.

# tests/test_brand_constraints.py:51 — registry count canary
def test_eleven_rules_exact(self):
    self.assertEqual(len(BRAND_CONSTRAINTS), 11)
    expected = {... 11 rule ids ...}
# After T03 → test_fourteen_rules_exact, count=14, expected set updated.

# .github/workflows/pages.yml:149-165 — CI ordering (unchanged for #23)
# - "Run structural check (Issue #12)" at L149-155 — strict, exits 1 on errors.
# - "Run alignment audit (Issue #22, informational)" at L157-165 — `|| true`,
#   stays informational. NO new step in #23.

# templates/zeitung-a4-grun/build.py — geometry edit targets (line refs from
# pitfalls.md §A15 + RESEARCH.md):
# L235  : Cover Hero ImageFrame call (Phase 4: x=0,w=210 → x=-3,w=216)
# L246  : u2950 Polygon (already trimmed in #22 — DO NOT re-edit)
# L457-470: P1 Hero block (Phase 4: x=0,w=207 → x=-3,w=210)
# L978-987: P4 Foto-Spread block (Phase 4: x=3,w=207 → x=3,w=210 — RESEARCH.md
#   corrects ISSUE.md's wrong "x=0,w=213"; RIGHT page outer at x=210, spine inset)
# L1327 : u918 Polygon (DO NOT move — fix the portrait, not the card)
# L1368 : P7 Portrait ImageFrame (Phase 4: w=54.7 with right=190 flush u918)
# L1799-1808: Kopie von u1529 polygon (DO NOT move — fix text columns)
# L1845-1852: P9 SpreadImage call (Phase 4: add outer_bleed_mm=3.0)
# L1894 : P10 Portrait ImageFrame (Phase 4: w=66.6 → w=77.7 — RESEARCH.md
#   corrects ISSUE.md's wrong w=74.7; w=77.7 reaches right=213 = bleed)
# L1952 : page-12 unnamed Dunkelgrün (Phase 4: x=0,w=207 → x=-3,w=210)
# L2101-2129: P11 Bottom + adjacent unnamed bands
# L2620-2735: CONSTRAINTS list — Phase 5 removal targets (11 widened-tolerance
#   entries; see pitfalls.md §A1 lines 2656/2668/2693-2710/2719-2725)

# templates/zeitung-a4-grun/meta.yml — SHA bump target
# previews_for_sla: <SHA>   # bumped by bin/render-gallery in T09
# sla_diff_strict: false    # geometry edits accepted

# bin/audit-alignment — existing 14-line shim (post-#22)
# bin/render-gallery <slug> --skip-visual-diff — regenerates artifacts + bumps SHA
# bin/check-stale-previews — exits 1 if meta.yml SHA != template.sla SHA
</interfaces>

Key files (with line-level evidence in pitfalls.md):
@tools/sla_lib/builder/brand_constraints.py — 11 existing rules (BrandRule + _UndeclaredDriftRule at L595, registry at L716, registry list ends L785).
@tools/sla_lib/builder/bbox.py — frame_bbox_mm + rotated_bbox (post-#22 refactor).
@tools/sla_lib/builder/blocks.py:686-740 — SpreadImage emit math.
@tools/sla_lib/builder/constraints.py:319-357 — _AlignedBelowConstraint.check (basis for c.check disagreement loop).
@tools/sla_lib/builder/document.py:376-378 — own_page=0 cover semantics.
@tools/sla_lib/builder/structural_check.py — orchestrator (already passes constraints kwarg).
@tools/audit_alignment.py — current CLI + report shape.
@tools/sla_lib/tests/test_brand_constraints.py:51 — registry count canary (11 → 14).
@tools/sla_lib/tests/test_brand_undeclared_drift.py — rename target → test_brand_visual_adjacency_drift.py.
@tools/sla_lib/tests/test_zeitung_overflow.py:107,19 — uses _UndeclaredDriftRule class + id (rename target).
@templates/zeitung-a4-grun/build.py — geometry edit targets (lines listed in <interfaces>).
@templates/zeitung-a4-grun/meta.yml — previews_for_sla SHA target.
@templates/{postkarte-a6-kampagne,plakat-a1-hochformat,infostand-tent-card-a5-quer,wahltag-tueranhaenger,themen-plakat-a3-quer,kandidat-falzflyer-din-lang}/meta.yml — pre-apply image_text_overlap override (T02). NOT wahlaufruf-postkarte-a6-quer (already merged in #17 — handle via separate fixup PR).
@.github/workflows/pages.yml:149-155 — existing strict structural_check step (NO new step in #23).
@bin/render-gallery — final SHA-bump pipeline.
@bin/check-stale-previews — CI gate enforcing SHA consistency.
</context>

<commit_format>
Format: conventional with issue-id prefix (per `.issues/config.yaml`).
Example: `23: feat(brand): replace UndeclaredDrift with VisualAdjacencyDrift + add 3 new BrandRules`
Pattern: `23: <type>(<scope>): <subject>`
Types: feat, fix, test, refactor, docs, chore, ci.
Scopes used in this plan: brand, builder, brand_constraints, blocks, audit, zeitung, templates, meta, ci, docs, issues.
One commit per task (T01-T10). T07 is intentionally a single atomic commit covering Phase 4 geometry + Phase 5 CONSTRAINTS removal (locked decision #10).
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="false">
<name>T01: Add 4 new BrandRules + replace UndeclaredDrift with VisualAdjacencyDrift</name>
<files>tools/sla_lib/builder/brand_constraints.py</files>
<depends-on>none</depends-on>
<behavior>
After T01, `BRAND_CONSTRAINTS` contains 14 rules (was 11):
- DROPPED: `_UndeclaredDriftRule` / id `brand:undeclared_alignment_drift` (5 mm axis / 12 mm adjacency / left+top axes only).
- ADDED 1:1 REPLACEMENT: `_VisualAdjacencyDriftRule` / id `brand:visual_adjacency_drift` — 4-axis checks (dx_left, dx_right, dy_top, dy_bottom), thresholds 25 mm axis / 30 mm adjacency, declaration-disagreement check via re-running `c.check()` against the actual primitives. Severity stays `warning`.
- ADDED: `_BleedCoverageRule` / id `brand:bleed_coverage` — facing-pages only, full-width cutoff 0.95 × page_w (locked decision #1, NOT 0.7 from ISSUE.md), severity `error`. Skips own_page=0 (cover) AND the right side detection special-cases cover with both outer edges. Skips SpreadImage halves via SPREAD_HALF_RX, skips rotated frames, skips anchor-positioned frames.
- ADDED: `_ImageTextOverlapRule` / id `brand:image_text_overlap` — scope (ImageFrame OR filled-Polygon, TextFrame) where filled = `fill not in (None, "", "None")` (locked decision #2 — Polygon×Text scope is mandatory; page-10 bug is Polygon×Text). Allowed: zero overlap, text fully contained in shape, or shape fully contained in text. Forbidden: partial overlap. Severity `error`.
- ADDED: `_CoverExtentMatchRule` / id `brand:cover_extent_match` — for pairs where both frames have `w > 0.95 × page_w` AND vertically touch (|A.bottom - B.top| < 0.5 mm), assert outer-bbox extents match (left edges within 0.5 mm AND right edges within 0.5 mm). Severity `warning` initially (per ISSUE.md "WARNING initially, ERROR after audit" — keep WARNING in T01; promote later if #23 follow-up needs).

ISSUE.md proposed two MORE rules: `brand:image_in_container_flush` and `brand:portrait_column_alignment`. RESEARCH.md folds both into the 4-axis VisualAdjacencyDrift rule (locked decision #3 — once the rule checks dx_right and dy_bottom, page-8 P7 Portrait's right-edge mismatch with u918 IS detected; page-11 P10 Portrait's right-edge-not-at-bleed is caught by `brand:bleed_coverage` only IF the portrait passes the 0.95 cutoff — but P10 is w/page=0.32, well below cutoff). The geometric-outcome test in T08 pins the P10 right-edge-at-bleed invariant directly; T07's geometry fix puts it at bleed. **Do NOT add separate _ImageInContainerFlush or _PortraitColumnAlignment rule classes** — RESEARCH.md verified they would be Zeitung-specific without adding generic detection power.

All rule code is GENERIC — no Zeitung-specific anname matches or coordinate constants. Per locked decision #3 / user direction "the rules must be generic — they MUST work on any template, not be hardcoded with Zeitung-specific anname matches or coordinate constants. Tune by adjusting thresholds + detection logic, not by special-casing."
</behavior>
<action>
Read `tools/sla_lib/builder/brand_constraints.py` end-to-end first to internalize the existing 11-rule pattern (frozen dataclass, `check(self, primitives, doc, constraints=None)`, helper imports from `bbox.py` and `primitives.py`). Then:

**Step 1.** DELETE `_UndeclaredDriftRule` class (L595-707) AND its `BRAND_CONSTRAINTS` registry entry (L785). Do NOT delete the `SIDE_RX`/`SPREAD_HALF_RX` regex helpers at L466-473 — the new `_BleedCoverageRule` and `_VisualAdjacencyDriftRule` reuse them.

**Step 2.** ADD `_BleedCoverageRule` (severity=error). Skeleton from RESEARCH.md "Architecture patterns" §_BleedCoverageRule (consume verbatim):

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
            # Cover (own_page=0): RIGHT-alone, both edges are outer.
            # Mirror _SpineSafetyRule's own_page=0 special-case.
            own_page = getattr(page, "own_page", None)
            m = SIDE_RX.search(page.master_name or "")
            pw_mm = page.width_pt * PT_TO_MM
            bleed = float(page.bleed_mm or 0)
            for item in page.items:
                anname = getattr(item, "anname", "") or f"<unnamed {type(item).__name__} y={getattr(item, 'y_mm', 0):.1f}>"
                if SPREAD_HALF_RX.search(anname):
                    continue   # SpreadImage halves are spread-intentional
                if float(getattr(item, "rotation_deg", 0) or 0) != 0:
                    continue
                if getattr(item, "anchor", None) is not None:
                    continue
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, _y0, x1, _y1 = bbox
                w = x1 - x0
                if w < self.full_width_threshold * pw_mm:
                    continue   # not full-width; per RESEARCH.md A2 cutoff dissolves (no-bleed) tag need
                if own_page == 0:
                    # Cover: both outer edges
                    if x0 > -bleed + self.tolerance_mm:
                        violations.append(self._mk("LEFT (cover)", anname, page, x0, x0 - (-bleed), -bleed))
                    if x1 < pw_mm + bleed - self.tolerance_mm:
                        violations.append(self._mk("RIGHT (cover)", anname, page, x1, (pw_mm + bleed) - x1, pw_mm + bleed))
                    continue
                if not m:
                    continue   # spine_safety emits its own unknown-side warning
                side = m.group(1).lower()
                if side == "links":
                    if x0 > -bleed + self.tolerance_mm:
                        violations.append(self._mk("LEFT", anname, page, x0, x0 - (-bleed), -bleed))
                else:  # rechts
                    if x1 < pw_mm + bleed - self.tolerance_mm:
                        violations.append(self._mk("RIGHT", anname, page, x1, (pw_mm + bleed) - x1, pw_mm + bleed))
        return violations

    def _mk(self, side, anname, page, actual, drift, expected) -> Violation:
        return Violation(
            severity="error",
            rule_id=self.id,
            message=(
                f"frame {anname!r} on {side} page {page.label or page.master_name!r}: "
                f"outer edge at {actual:.2f}mm but should be at {expected:.2f}mm "
                f"(missing {drift:.2f}mm of bleed coverage). "
                f"Either fix geometry to extend to outer bleed OR add to "
                f"meta.yml::brand_overrides[brand:bleed_coverage] with reason."
            ),
            targets=(anname,),
        )
```

**Step 3.** ADD `_ImageTextOverlapRule` (severity=error). Skeleton from RESEARCH.md "Architecture patterns" §_ImageTextOverlapRule (consume verbatim, including the `FILLED_POLYGON_FILLS` constant):

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
                            f"text {getattr(txt, 'anname', '<unnamed>')!r} partially overlaps "
                            f"{kind} {getattr(shape, 'anname', '<unnamed>')!r} on page "
                            f"{page.label or page.master_name!r}: intersection "
                            f"{ox1-ox0:.1f}x{oy1-oy0:.1f}mm. Either contain text fully "
                            f"inside, move out, or shrink shape."
                        ),
                        targets=(getattr(txt, 'anname', ''), getattr(shape, 'anname', '')),
                    ))
        return violations
```

**Step 4.** ADD `_CoverExtentMatchRule` (severity=warning). Skeleton:

```python
@dataclass(frozen=True)
class _CoverExtentMatchRule(BrandRule):
    full_width_threshold: float = 0.95
    touch_tolerance_mm: float = 0.5
    extent_tolerance_mm: float = 0.5

    def check(self, primitives, doc, constraints=None) -> list:
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            pw_mm = page.width_pt * PT_TO_MM
            wide = []
            for item in page.items:
                bbox = frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                if (x1 - x0) >= self.full_width_threshold * pw_mm:
                    wide.append((item, bbox))
            for i, (a_item, abox) in enumerate(wide):
                for b_item, bbox in wide[i + 1:]:
                    ax0, ay0, ax1, ay1 = abox
                    bx0, by0, bx1, by1 = bbox
                    # Vertically touching: A.bottom ≈ B.top OR B.bottom ≈ A.top
                    touch = (
                        abs(ay1 - by0) < self.touch_tolerance_mm
                        or abs(by1 - ay0) < self.touch_tolerance_mm
                    )
                    if not touch:
                        continue
                    if (abs(ax0 - bx0) <= self.extent_tolerance_mm
                            and abs(ax1 - bx1) <= self.extent_tolerance_mm):
                        continue
                    a_n = getattr(a_item, "anname", "") or f"<unnamed {type(a_item).__name__}>"
                    b_n = getattr(b_item, "anname", "") or f"<unnamed {type(b_item).__name__}>"
                    violations.append(Violation(
                        severity="warning",
                        rule_id=self.id,
                        message=(
                            f"frames {a_n!r} (x:{ax0:.1f}..{ax1:.1f}) and {b_n!r} "
                            f"(x:{bx0:.1f}..{bx1:.1f}) touch vertically on page "
                            f"{page.label or page.master_name!r} but their outer-bbox "
                            f"extents differ. Either make them share extents (left+right) "
                            f"OR override via meta.yml."
                        ),
                        targets=(a_n, b_n),
                    ))
        return violations
```

**Step 5.** ADD `_VisualAdjacencyDriftRule` (severity=warning, 4-axis check + declaration-disagreement). Skeleton from RESEARCH.md "Architecture patterns" §_VisualAdjacencyDriftRule (consume verbatim, including `import itertools` at module top if not already imported):

```python
@dataclass(frozen=True)
class _VisualAdjacencyDriftRule(BrandRule):
    axis_drift_min_mm: float = 0.5
    axis_drift_max_mm: float = 25.0
    adjacency_gap_min_mm: float = 0.5
    adjacency_gap_max_mm: float = 30.0

    def check(self, primitives, doc, constraints=None) -> list:
        constraints = constraints or []
        # Build declared-pair → list-of-constraints map (need declarations
        # to re-check disagreement, not just frozenset membership)
        declared: dict = {}
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
                        # Disagreement check: re-run each declaration against the
                        # actual primitives. If the constraint's own tolerance is
                        # breached, surface a warning. This breaks encode-and-silence
                        # at the declaration's tolerance boundary (locked decision #5).
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
                    fired = False
                    for axis_label, drift, suggested in [
                        ("axis-x-left", dx_left, "same_x (left edges)"),
                        ("axis-x-right", dx_right, "same_x_right (right edges)"),
                        ("axis-y-top", dy_top, "same_y (top edges)"),
                        ("axis-y-bottom", dy_bottom, "same_y_bottom (bottom edges)"),
                    ]:
                        if self.axis_drift_min_mm < drift < self.axis_drift_max_mm:
                            violations.append(self._mk(pa, qa, axis_label, drift, suggested))
                            fired = True
                            break
                    if fired:
                        continue
                    # Stacked-adjacency: P above Q with small gap, sharing left or right edge
                    if py1 < qy0:
                        gap = qy0 - py1
                        if (self.adjacency_gap_min_mm < gap < self.adjacency_gap_max_mm
                                and (dx_left < self.axis_drift_max_mm or dx_right < self.axis_drift_max_mm)):
                            violations.append(self._mk(pa, qa, "adjacency-y", gap, "aligned_below"))
        return violations

    def _mk(self, pa, qa, kind, drift, suggested) -> Violation:
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

**Step 6.** Update the `BRAND_CONSTRAINTS` registry list (currently L716-785 with 11 entries). Order new entries thematically near related rules (e.g., bleed_coverage near _Bleed3mmRule, image_text_overlap near _TextOnGreenRule, cover_extent_match near _SpineSafetyRule, visual_adjacency_drift in place of _UndeclaredDriftRule). Each entry follows the existing pattern:

```python
_BleedCoverageRule(
    id="brand:bleed_coverage",
    name="Outer-edge bleed coverage on facing-pages",
    description=(
        "Full-width frames (w >= 0.95 * page_w) on facing-pages documents must "
        "extend to the outer bleed (LEFT page: x <= -bleed; RIGHT page: x+w >= page_w + bleed). "
        "Cover (own_page=0) treats both edges as outer. SpreadImage halves and rotated frames "
        "are exempt; per-template skip via meta.yml::brand_overrides[brand:bleed_coverage]."
    ),
    severity="error",
),
# ... and similarly for the other 3 entries ...
```

The replacement entry for VisualAdjacencyDrift uses `severity="warning"` and reuses the description shape from the dropped UndeclaredDrift entry but states 4-axis + 25/30 mm thresholds + declaration-disagreement.

**Step 7.** Verify imports at top of file — the new rules use `ImageFrame`, `TextFrame`, `Polygon` from `.primitives`, plus `itertools` (stdlib). Add as needed.

Final registry length: **14 rules**. T03 updates the test canary.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "from sla_lib.builder.brand_constraints import BRAND_CONSTRAINTS; ids = [r.id for r in BRAND_CONSTRAINTS]; assert len(ids) == 14, f'expected 14 rules got {len(ids)}: {ids}'; assert 'brand:undeclared_alignment_drift' not in ids, 'old rule still present'; expected_new = {'brand:bleed_coverage', 'brand:image_text_overlap', 'brand:cover_extent_match', 'brand:visual_adjacency_drift'}; missing = expected_new - set(ids); assert not missing, f'missing: {missing}'; print('OK: 14 rules,', sorted(ids))" 2>&1</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 -c "import importlib; m = importlib.import_module('sla_lib.builder.brand_constraints'); print('imports OK')" 2>&1</automated>
<manual>Read T01's diff. Confirm: NO Zeitung-specific anname matches (e.g. 'Cover Hero', 'u918', 'P7 Portrait') anywhere in the rule code. NO hardcoded coordinate constants tied to specific frames. Rules read primitives + bbox + page metadata only.</manual>
</verify>
<done>
- `_UndeclaredDriftRule` class deleted; `brand:undeclared_alignment_drift` no longer in registry.
- `_VisualAdjacencyDriftRule` class added with 4-axis check + declaration-disagreement loop.
- `_BleedCoverageRule`, `_ImageTextOverlapRule`, `_CoverExtentMatchRule` classes added.
- `BRAND_CONSTRAINTS` length is 14; rule ids include the 4 expected new ones; `brand:undeclared_alignment_drift` is absent.
- Module imports cleanly (no SyntaxError, no NameError, no ImportError).
- All rule code is GENERIC — zero Zeitung-specific anname/coordinate references.
- (T03 test bump comes in T03; T01 may temporarily break `test_eleven_rules_exact` — that's accepted within T01-T03 atomic group.)
</done>
<dont>
- Don't use 0.7 cutoff for `_BleedCoverageRule` — RESEARCH.md A2 verified that 0.7 produces 19 false positives (body-text grid at 20 mm margin = 0.81 width ratio). Use 0.95.
- Don't add `(no-bleed)` per-frame exemption tag (locked decision #1 dissolves it — u918 falls below the 0.95 cutoff naturally).
- Don't separate "image-text overlap" from "polygon-text overlap" into two rules (anti-pattern F4 in pitfalls.md). One rule, broader scope.
- Don't add `_ImageInContainerFlushRule` or `_PortraitColumnAlignmentRule` from ISSUE.md — folded into VisualAdjacencyDrift's 4-axis check + T08 invariant tests (per locked decision #3).
- Don't use `page.is_left` (hardcoded False on doc pages — pitfall B4). Use `SIDE_RX.search(page.master_name)`.
- Don't hardcode any anname or coordinate from the Zeitung in rule logic. The audit + Codex visual review (T06) is what proves the rules are general enough to catch the Zeitung's specific bugs.
- Don't promote `_CoverExtentMatchRule` to severity=error in T01 — it's WARNING per ISSUE.md "WARNING initially, ERROR after audit". Keep WARNING.
- Don't break `aligned_below` / `same_y` / etc. constraint factories. The `c.check(primitives_by_anname)` re-execution in VisualAdjacencyDrift relies on their existing `check()` semantics (constraints.py:319-357 etc.).
- Don't import anything from outside `sla_lib.builder.*` and stdlib. No new dependencies (locked: see RESEARCH.md "User constraints").
</dont>
</task>

<task id="T02" type="auto" tdd="false">
<name>T02: Pre-apply brand_overrides[brand:image_text_overlap] to 6 non-Zeitung templates</name>
<files>templates/postkarte-a6-kampagne/meta.yml, templates/plakat-a1-hochformat/meta.yml, templates/infostand-tent-card-a5-quer/meta.yml, templates/wahltag-tueranhaenger/meta.yml, templates/themen-plakat-a3-quer/meta.yml, templates/kandidat-falzflyer-din-lang/meta.yml</files>
<depends-on>T01</depends-on>
<behavior>
Each of the 6 listed templates' `meta.yml::brand_overrides` gains an entry:

```yaml
- id: brand:image_text_overlap
  reason: "scheduled for follow-up audit per #23 — caption-on-photo / decorative overlaps audited at time of #23, not yet reviewed for fix-vs-override classification."
```

Without this, T01's new ERROR-severity `brand:image_text_overlap` rule fires on:
- postkarte-a6-kampagne page 1: 3 cases (P1 Hero ↔ unnamed at 91 %, two small overlaps at 16-20 %).
- plakat-a1-hochformat page 1: 3 cases (77 / 19 / 8 %).
- infostand-tent-card-a5-quer page 1: rotated Logo Grüne ↔ rotated Headline Panel B (63 %).
- (wahltag-tueranhaenger / themen-plakat-a3-quer / kandidat-falzflyer-din-lang: 0 cases observed in pitfalls.md A3 probe BUT still pre-apply override defensively because the new 4-axis VisualAdjacencyDrift may surface something on re-audit. Override id matches one rule only; cost is one yaml line per template.)

Per locked decision #12: without the pre-applied overrides, `structural_check --all` exits 1 mid-PR after T01 lands, breaking every subsequent task's verify command. Pre-applying = atomic safety.

DO NOT touch `templates/wahlaufruf-postkarte-a6-quer/meta.yml`. Per #17 (already merged): single-page template, no facing-page bleed concerns, no documented image_text overlaps from pitfalls.md probe. Pitfall A14 + RESEARCH.md "Pre-applied overrides for 6 non-Zeitung templates" + user instruction explicitly excludes it. The follow-up fixup PR for #17 (out of scope for #23) re-audits with the new stricter rules and adds an override only if needed.

DO NOT pre-apply `brand:bleed_coverage` overrides. The rule's `if not getattr(doc, "facing_pages", False): return []` early-exit means non-facing-pages templates (all 6 listed are single-page or non-facing) are exempt naturally — no override needed.

DO NOT pre-apply `brand:cover_extent_match` overrides. The rule's "both frames must be wide AND vertically touching" gate is narrow enough that pitfalls.md A4 verified zero violations on Zeitung other than the documented case; the 6 non-Zeitung templates either have no full-width pairs at all (pitfalls.md probe didn't surface any) or the pairs don't touch vertically. Add overrides ONLY if T06 verification gate surfaces false positives mid-PR — until then, leave alone.

DO NOT pre-apply `brand:visual_adjacency_drift` overrides. Per pitfalls.md A11 the rule produces ~38 warnings on postkarte at the new thresholds; per pitfalls.md A11 mitigation choice (b) "Keep severity=warning, accept the audit-report noise as 'reviewer reads if interested'. Since the rule is warning-only it doesn't fail CI." — warnings don't fail `structural_check --all`. No override needed.
</behavior>
<action>
For each of the 6 meta.yml files, locate the existing `brand_overrides:` list (each template already has one — verified via grep — typically 1-2 entries like `brand:line_spacing_0.9`). Append the new entry preserving YAML indentation conventions of that file. Example for `templates/postkarte-a6-kampagne/meta.yml`:

```yaml
brand_overrides:
  - id: brand:line_spacing_0.9
    reason: "..."
  # NEW (Issue #23):
  - id: brand:image_text_overlap
    reason: "scheduled for follow-up audit per #23 — caption-on-photo / decorative overlaps audited at time of #23, not yet reviewed for fix-vs-override classification."
```

Read each file FIRST to check existing indentation style and existing override count. Use the `Edit` tool to insert one entry per file (six edits total, one per file).

After all 6 edits, run `python3 -c "import yaml; ..."` for each to verify YAML still parses.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && for f in templates/postkarte-a6-kampagne/meta.yml templates/plakat-a1-hochformat/meta.yml templates/infostand-tent-card-a5-quer/meta.yml templates/wahltag-tueranhaenger/meta.yml templates/themen-plakat-a3-quer/meta.yml templates/kandidat-falzflyer-din-lang/meta.yml; do python3 -c "import yaml; d = yaml.safe_load(open('$f')); ids = [o['id'] for o in d.get('brand_overrides', [])]; assert 'brand:image_text_overlap' in ids, f'missing in $f: {ids}'; print('$f OK', ids)"; done</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "import yaml; d = yaml.safe_load(open('templates/wahlaufruf-postkarte-a6-quer/meta.yml')); ids = [o['id'] for o in d.get('brand_overrides', [])]; assert 'brand:image_text_overlap' not in ids, f'should NOT be set on wahlaufruf-postkarte: {ids}'; print('wahlaufruf-postkarte correctly untouched:', ids)"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -10; echo "EXIT=$?"</automated>
<manual>Read git diff. Confirm: 6 yaml files modified, each gains exactly one `brand:image_text_overlap` override entry; reason text references #23; `wahlaufruf-postkarte-a6-quer/meta.yml` is untouched.</manual>
</verify>
<done>
- 6 meta.yml files have `brand:image_text_overlap` in brand_overrides with reason text referencing #23.
- `templates/wahlaufruf-postkarte-a6-quer/meta.yml` is unmodified (verified by negative assertion).
- All 6 yaml files parse cleanly (no syntax errors).
- `python3 -m sla_lib.builder.structural_check --all` exits 0 — no template fails ERROR-severity rules. (Zeitung itself may still fail `brand:bleed_coverage` / `brand:image_text_overlap` until T07 — that's expected; structural_check exit will be addressed by ordering: T01-T05 land first, then T06 gate, then T07 fix.)
- WAIT: Zeitung will fail `brand:bleed_coverage` after T01+T02 land because Zeitung is the bug-target. Two options: (a) also pre-apply `brand:bleed_coverage` and `brand:image_text_overlap` overrides on Zeitung itself with reason "to be fixed in T07 of #23" and remove them in T07, or (b) accept that `structural_check --all` is RED between T01 and T07 (atomic ordering means T07 must land BEFORE next push to remote). **Use option (a)**: pre-apply Zeitung overrides too, reason "scheduled for fix in T07 of #23"; T07 removes them coincident with the geometry fix. This keeps every commit green. Add the same two override entries to `templates/zeitung-a4-grun/meta.yml` in T02 with the explicit "scheduled for fix in T07" reason, and T07's done-list requires their removal.
</done>
<dont>
- Don't touch `templates/wahlaufruf-postkarte-a6-quer/meta.yml` — handled by separate fixup PR per locked decision #12.
- Don't pre-apply `brand:bleed_coverage` to non-facing-pages templates — rule self-exits via `facing_pages` check. Override is no-op + clutter.
- Don't pre-apply `brand:cover_extent_match` defensively. Pitfalls A4 verified zero false positives on Zeitung; non-Zeitung templates lack full-width pairs. If T06 surfaces false positives, add override mid-PR.
- Don't write a new `reason:` block longer than one line — meta.yml convention is single-line reasons.
- Don't add `brand:visual_adjacency_drift` overrides — it's warning-only, doesn't fail CI.
</dont>
</task>

<task id="T03" type="auto" tdd="true">
<name>T03: Rule unit tests + bump registry count test 11→14</name>
<files>tools/sla_lib/tests/test_brand_constraints.py, tools/sla_lib/tests/test_brand_visual_adjacency_drift.py (RENAMED from test_brand_undeclared_drift.py), tools/sla_lib/tests/test_brand_bleed_coverage.py (NEW), tools/sla_lib/tests/test_brand_image_text_overlap.py (NEW), tools/sla_lib/tests/test_brand_cover_extent_match.py (NEW), tools/sla_lib/tests/test_zeitung_overflow.py</files>
<depends-on>T01</depends-on>
<behavior>
Unit tests for each new rule using SYNTHETIC mini-docs only (no real-template coordinates). Each new rule has positive (rule fires correctly) and negative (rule doesn't fire when it shouldn't) cases. Renames of `test_brand_undeclared_drift.py` references and updates `test_eleven_rules_exact` → `test_fourteen_rules_exact`.

Per locked decision #13: NO real-template coordinate pinning here — that's T08's job and uses a totally different file (`test_zeitung_geometry.py`). T03 is about rule semantics in isolation.

The renamed `test_brand_visual_adjacency_drift.py` reuses the spirit of `test_brand_undeclared_drift.py` (test the rule fires + can be silenced via constraints) but ADDS:
- A test for each of the 4 axes (dx_left, dx_right, dy_top, dy_bottom) — synthetic mini-doc with 2 frames whose only mismatch is on that axis.
- A test for declaration-disagreement (synthetic mini-doc + an `aligned_below(A, B, gap_mm=2.0, tolerance_mm=0.5)` constraint that disagrees with actual geometry by 3 mm — rule must emit a "declaration disagrees" warning).
- A test that a tight `tolerance_mm=0.5` declaration matching actual geometry produces zero warnings.
</behavior>
<action>
**Step 1.** UPDATE `tools/sla_lib/tests/test_brand_constraints.py`:
- L51 `test_eleven_rules_exact` → `test_fourteen_rules_exact`.
- L54 `assertEqual(len(BRAND_CONSTRAINTS), 11)` → `assertEqual(len(BRAND_CONSTRAINTS), 14)`.
- L58 `expected = {...}` set: REMOVE `"brand:undeclared_alignment_drift"`, ADD `"brand:visual_adjacency_drift"`, `"brand:bleed_coverage"`, `"brand:image_text_overlap"`, `"brand:cover_extent_match"` — final set has 14 ids.
- L29 `from sla_lib.builder.brand_constraints import _UndeclaredDriftRule` → import the new class names if any test references them; otherwise just drop the import.

**Step 2.** RENAME `test_brand_undeclared_drift.py` → `test_brand_visual_adjacency_drift.py`. Update inside the file:
- All 11 occurrences of `brand:undeclared_alignment_drift` → `brand:visual_adjacency_drift`.
- All references to `_UndeclaredDriftRule` → `_VisualAdjacencyDriftRule`.
- Class-level docstring: "Tests for brand:visual_adjacency_drift (Issue #23, replaced brand:undeclared_alignment_drift from #22)."
- ADD 4 new test methods (4-axis coverage):

```python
def test_axis_x_left_drift_fires(self):
    """Two frames whose only mismatch is left-edge x-coordinate within (0.5, 25) mm."""
    # synthetic Document with 2 ImageFrames at x=20 vs x=23 (drift=3mm),
    # both at y=50, w=40, h=40 — no other mismatches.
    # rule.check returns one warning with axis='axis-x-left'.

def test_axis_x_right_drift_fires(self):
    """Page-8-style: same left edge but different right edges → drift detected."""
    # frames at x=20 w=40 vs x=20 w=43 → right edges 60 vs 63, drift=3mm.

def test_axis_y_top_drift_fires(self):
    """Same x but different y_top → drift detected."""

def test_axis_y_bottom_drift_fires(self):
    """Same x and y_top but different heights → bottom edges differ."""

def test_declaration_disagreement_emits_warning(self):
    """aligned_below(A, B, gap_mm=2.0, tolerance_mm=0.5) but actual gap=5mm → warning."""
    # constraint declared; actual geometry violates the constraint's own tolerance.
    # _VisualAdjacencyDriftRule.check(primitives, doc, constraints=[c])
    # should emit warning with rule_id='brand:visual_adjacency_drift' and
    # message containing "declaration ... disagrees with actual geometry".

def test_tight_declaration_matching_geometry_produces_no_warning(self):
    """aligned_below(A, B, gap_mm=2.0, tolerance_mm=0.5) and actual gap=2.0mm → silent."""
```

**Step 3.** CREATE `tools/sla_lib/tests/test_brand_bleed_coverage.py` (NEW). Use synthetic Document + Page + ImageFrame primitives:

```python
"""Tests for brand:bleed_coverage (Issue #23, locked decision #1: 0.95 cutoff).

Generic tests — no real-template coordinates. Each test constructs a minimal
Document/Page/ImageFrame combination to verify rule semantics in isolation.
"""
import unittest
from sla_lib.builder.brand_constraints import BRAND_CONSTRAINTS, _BleedCoverageRule
from sla_lib.builder.primitives import ImageFrame
# ... helper to build a minimal Document with facing_pages=True ...

class BleedCoverageTests(unittest.TestCase):
    def test_facing_pages_false_returns_zero_violations(self):
        """Single-page documents are exempt (rule is facing-pages-only)."""
    def test_full_width_left_page_short_of_bleed_fires_error(self):
        """LEFT page, w/page=0.99 (>=0.95 cutoff), x=0 (not -3) → ERROR."""
    def test_left_page_at_bleed_passes(self):
        """LEFT page, x=-3, w=210+3 → no violation."""
    def test_right_page_short_of_bleed_fires_error(self):
        """RIGHT page, x+w=210 (not 213) → ERROR."""
    def test_below_cutoff_w_ratio_skipped(self):
        """w/page=0.81 (u918-shaped) → not flagged. Locked decision #1: 0.95 dissolves the (no-bleed) tag."""
    def test_rotated_frame_skipped(self):
        """rotation_deg=90 → skipped, no violation."""
    def test_anchor_positioned_skipped(self):
        """anchor=Anchor(...) → skipped."""
    def test_spread_half_anname_skipped(self):
        """anname='X · left' or 'X · right' → skipped (SPREAD_HALF_RX)."""
    def test_cover_own_page_zero_both_edges_checked(self):
        """own_page=0 + frame at x=0,w=210 → BOTH outer-edge errors (LEFT cover + RIGHT cover)."""
    def test_unnamed_frame_still_flagged(self):
        """anname='' → violation message uses '<unnamed ImageFrame y=...>'."""
```

**Step 4.** CREATE `tools/sla_lib/tests/test_brand_image_text_overlap.py` (NEW):

```python
class ImageTextOverlapTests(unittest.TestCase):
    def test_zero_overlap_passes(self):
        """ImageFrame and TextFrame with disjoint bboxes → no violation."""
    def test_text_fully_inside_image_passes(self):
        """Text bbox contained in image bbox (caption-on-photo) → no violation."""
    def test_image_fully_inside_text_passes(self):
        """Drop-cap-style: image inside text → no violation."""
    def test_partial_overlap_image_text_fires_error(self):
        """ImageFrame overlapping TextFrame at boundary → ERROR."""
    def test_partial_overlap_filled_polygon_text_fires_error(self):
        """Page-10-bug class: filled Polygon (Dunkelgrün) ↔ TextFrame partial overlap → ERROR. Locked decision #2."""
    def test_polygon_with_unfilled_skipped(self):
        """Polygon with fill=None or fill='' or fill='None' → not in scope."""
    def test_polygon_with_other_color_skipped(self):
        """Polygon fill='Black' (not in FILLED_POLYGON_FILLS) → not in scope (decorative outlines)."""
    def test_overlap_below_tolerance_skipped(self):
        """Intersection 0.05 mm < 0.1 tolerance → skipped (numerical noise)."""
```

**Step 5.** CREATE `tools/sla_lib/tests/test_brand_cover_extent_match.py` (NEW):

```python
class CoverExtentMatchTests(unittest.TestCase):
    def test_two_full_width_touching_frames_with_matching_extents_pass(self):
        """A bottom == B top within 0.5 mm AND outer-bbox extents match → no violation."""
    def test_touching_frames_with_mismatched_left_edge_warn(self):
        """Page-1 Cover Hero ↔ u2950 class: A.left=0 vs B.left=-3 → WARNING."""
    def test_touching_frames_with_mismatched_right_edge_warn(self):
        """A.right=210 vs B.right=213 → WARNING."""
    def test_non_touching_frames_skipped(self):
        """A.bottom and B.top differ by >0.5 mm → no warning even with mismatched extents."""
    def test_non_full_width_pair_skipped(self):
        """Both frames w/page=0.5 → not flagged (cutoff 0.95)."""
```

**Step 6.** UPDATE `tools/sla_lib/tests/test_zeitung_overflow.py:107,19`:
- L19: `from sla_lib.builder.brand_constraints import _UndeclaredDriftRule` → `_VisualAdjacencyDriftRule`.
- L107: occurrences of `'brand:undeclared_alignment_drift'` → `'brand:visual_adjacency_drift'`.
- Verify test still passes (the test logic — that the rule fires on Zeitung — remains valid; only the rule name changed).

For each new test file, follow the existing pattern from `test_brand_undeclared_drift.py` for synthetic-doc helpers (build a minimal Document with one Page containing the test primitives, no full template loading).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -m unittest discover tools/sla_lib/tests -v 2>&1 | tail -30; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -m unittest tools.sla_lib.tests.test_brand_constraints.RegistryTests.test_fourteen_rules_exact -v 2>&1 | tail -10</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && ls tools/sla_lib/tests/test_brand_visual_adjacency_drift.py tools/sla_lib/tests/test_brand_bleed_coverage.py tools/sla_lib/tests/test_brand_image_text_overlap.py tools/sla_lib/tests/test_brand_cover_extent_match.py 2>&1; test ! -e tools/sla_lib/tests/test_brand_undeclared_drift.py && echo "old file deleted OK" || echo "FAIL: old file still exists"</automated>
<manual>Read each new test file. Confirm: zero references to actual Zeitung anname strings ("Cover Hero", "u2950", "P7 Portrait", "u918", "P10 Portrait", "Kopie von u1529"). All test data uses synthetic anname strings like "frame_a", "img_1", "text_left".</manual>
</verify>
<done>
- `test_brand_constraints.py::test_fourteen_rules_exact` passes (asserts 14 rules + 4 new ids present + drift renamed).
- `test_brand_undeclared_drift.py` no longer exists.
- `test_brand_visual_adjacency_drift.py` exists with renamed contents + 4-axis tests + declaration-disagreement test + tight-declaration-silence test.
- 3 NEW test files exist for bleed_coverage, image_text_overlap, cover_extent_match — each ≥ 5 test methods covering positive + negative cases.
- `test_zeitung_overflow.py` references updated to new rule id/class.
- `python3 -m unittest discover tools/sla_lib/tests` exits 0.
- ALL test data is synthetic; zero real-template anname strings.
</done>
<dont>
- Don't pin any real-template coordinate in T03 tests (e.g. `assertEqual(x_mm, 135.3)`). Pin the relationship the rule encodes — e.g. "left edge drift between two synthetic frames in (0.5, 25) range" — not the absolute number.
- Don't reuse the SAME synthetic frame as both image and text in image_text_overlap tests. The rule iterates `(shapes, texts)` lists separately.
- Don't import from real templates (no `from templates.zeitung_a4_grun.build import ...`). Synthetic only.
- Don't forget to update `test_zeitung_overflow.py` — its references to `_UndeclaredDriftRule` will break the test suite if left.
</dont>
</task>

<task id="T04" type="auto" tdd="false">
<name>T04: Tighten audit_alignment.py defaults + add tolerance-suspicion findings</name>
<files>tools/audit_alignment.py</files>
<depends-on>T01</depends-on>
<behavior>
After T04, `tools/audit_alignment.py`:
- Default thresholds bumped: `--axis-tol-mm 25.0` (was 5.0), `--adjacency-tol-mm 30.0` (was 12.0). Matches `_VisualAdjacencyDriftRule` defaults from T01.
- New `--strict` flag: when present, the report emits ALL findings as ERROR-severity (vs. mixed warning/info). This is the "audit clean" gate: `bin/audit-alignment <slug> --strict` exits 1 on any finding. Used in T06 verification gate.
- New `--json` output mode (already exists per RESEARCH.md L143; verify and don't regress).
- New tolerance-suspicion findings (locked decision #6): for each Constraint in `mod.CONSTRAINTS` whose `tolerance_mm > 1.0` (where applicable — `_SameAxisConstraint`, `_AlignedBelowConstraint` have it; not all factories do), emit a finding "constraint X (tolerance_mm=Y, gap_mm=Z) is suspicious — was geometry intent or spec drift? Consider tightening to tolerance_mm=0.5 or fixing geometry." Severity = "info" (or "warning" in `--strict`). NOT a `BrandRule` violation — lives only in audit-tool output.
- Audit output adds "OR fix geometry" suggestions: not just "declare with `same_x(A, B)`" but also a paired hint "OR fix geometry: A.x=N, B.x=N" using the actual coordinates from the bbox.
</behavior>
<action>
Read `tools/audit_alignment.py` end-to-end first (CLI entry at L317-328 per RESEARCH.md). Then:

**Step 1.** Update default values:

```python
# CLI flag definitions (~L300-315):
parser.add_argument("--axis-tol-mm", type=float, default=25.0,
                    help="Axis-alignment drift tolerance (mm). Default 25.0 "
                         "matches brand:visual_adjacency_drift; was 5.0 pre-#23.")
parser.add_argument("--adjacency-tol-mm", type=float, default=30.0,
                    help="Adjacency gap tolerance (mm). Default 30.0; was 12.0 pre-#23.")
parser.add_argument("--strict", action="store_true",
                    help="Treat all findings as ERROR-severity. Exits 1 on any finding. "
                         "Used by Phase 3b verification gate (Issue #23).")
```

**Step 2.** Implement `--strict` exit-code logic. After the audit walks all templates, if `args.strict` and any finding was emitted (from any template), exit with code 1; else exit 0. The existing `--all` behavior aggregates per-template reports — `--strict` adds a final post-walk count.

**Step 3.** Add tolerance-suspicion findings to the per-template walk. After enumerating constraints, for each `c in mod.CONSTRAINTS`:

```python
# Locked decision #6: tolerance_mm > 1.0 is "suspicious" — flag for review.
tol = getattr(c, "tolerance_mm", None)
if tol is not None and tol > 1.0:
    finding = {
        "kind": "tolerance-suspicion",
        "severity": "warning" if args.strict else "info",
        "constraint_id": c.id,
        "constraint_name": getattr(c, "name", c.id),
        "tolerance_mm": tol,
        "targets": list(getattr(c, "targets", ())),
        "message": (
            f"constraint {getattr(c, 'name', c.id)!r} declared with "
            f"tolerance_mm={tol:.2f} (>1.0 mm). Was the geometry intent fuzzy "
            f"or did the spec drift to absorb misalignment? Consider tightening "
            f"to tolerance_mm=0.5 (default) or fixing the geometry."
        ),
    }
    findings.append(finding)
```

Also add `gap_mm > 30.0` suspicion (mirror logic; getattr `gap_mm`).

**Step 4.** Augment heuristic suggestions. Where the audit currently emits `"Declare with same_x(A, B)"`, augment with the geometric-outcome alternative:

```python
# When emitting suspicious-axis-pair finding:
suggestion = (
    f"Declare with {factory_name}({pa!r}, {qa!r}) in CONSTRAINTS "
    f"(tolerance_mm=0.5), OR fix geometry: set {pa}.{axis_attr}={target_val:.2f}mm "
    f"and {qa}.{axis_attr}={target_val:.2f}mm to share the axis."
)
```

The `target_val` is the average of the two actual values, or whichever is the dominant edge in context — judgment call. The point: every suggestion now offers BOTH options (encode OR fix), explicit per locked decision #14 in RESEARCH.md.

**Step 5.** JSON output mode: confirm `--json` already exists (per RESEARCH.md L143). If yes, ensure the new tolerance-suspicion findings + augmented suggestions are present in the JSON. If `--json` doesn't yet exist as a structured-output mode, add it: write a JSON list of finding dicts to stdout (or to `--output-dir/<slug>.json` if combined with `--output-dir`).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 tools/audit_alignment.py --help 2>&1 | grep -E "(axis-tol-mm|adjacency-tol-mm|strict|json)" | head -10</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun 2>&1 | grep -i "tolerance" | head -5</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && mkdir -p reviews && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --json > reviews/audit-zeitung-test.json 2>&1 && python3 -c "import json; d = json.load(open('reviews/audit-zeitung-test.json')); print('valid JSON,', len(d), 'top-level entries' if isinstance(d, list) else 'top-level keys:', list(d.keys()) if isinstance(d, dict) else 'list')" 2>&1; rm -f reviews/audit-zeitung-test.json</automated>
<manual>Read sample audit output for Zeitung. Confirm: (a) tolerance_mm > 1.0 findings appear (Zeitung has 8 widened-tolerance entries per pitfalls A1, all should be flagged); (b) heuristic suggestions include both "declare with X" AND "OR fix geometry"; (c) `--strict` exits 1 because Zeitung is the bug-target until T07 lands.</manual>
</verify>
<done>
- `tools/audit_alignment.py --help` shows new defaults (25.0 axis, 30.0 adjacency) + `--strict` flag.
- `--strict` mode exits 1 when findings exist (returns 1 on Zeitung pre-T07; will return 0 post-T07).
- `--json` mode produces parseable JSON containing findings list.
- Tolerance-suspicion findings appear in audit output for Zeitung's 8+ widened CONSTRAINTS.
- Each heuristic finding includes BOTH "declare" and "OR fix geometry" suggestion lines.
- T03 unit tests still pass (no regression on rule code).
</done>
<dont>
- Don't change the report's Markdown structure beyond additive edits — RESEARCH.md L143 confirms `--md PATH` and human-readable Markdown is the default; preserve compatibility with downstream readers (`build/audit/<slug>.md` artifact).
- Don't make `--strict` change rule-execution behavior. Rules emit their own severities; `--strict` only changes the audit-tool's exit code policy and how it labels its OWN findings (tolerance-suspicion, heuristic-suggestion).
- Don't promote the audit-tool CI step to fatal in T04 (locked decision #14 — the existing `structural_check --all` step is the gate; the audit step stays informational with `|| true`).
- Don't add `bleed_coverage` or `image_text_overlap` checks to the audit tool itself — those are BrandRule-driven; the audit tool's role is the heuristic adjacency report + tolerance-suspicion. Keep concerns separate.
</dont>
</task>

<task id="T05" type="auto" tdd="true">
<name>T05: Add SpreadImage outer_bleed_mm parameter</name>
<files>tools/sla_lib/builder/blocks.py, tools/sla_lib/tests/test_spread_image.py (UPDATE OR NEW)</files>
<depends-on>none</depends-on>
<behavior>
After T05, `SpreadImage` block has an `outer_bleed_mm: float = 0.0` parameter. When non-zero:
- LEFT half: `x_mm = -outer_bleed_mm`, `w_mm = page_w_mm + outer_bleed_mm`, `local_offset_mm = (0.0, 0.0)`.
- RIGHT half: `x_mm = 0.0`, `w_mm = page_w_mm + outer_bleed_mm`, `local_offset_mm = (-(page_w_mm + outer_bleed_mm), 0.0)` — adjusted from `(-page_w_mm, 0)` so the source-image scroll accounts for the additional bleed area.

Per pitfalls.md A8 / locked decision #11: `local_offset_mm` math correctness is load-bearing. Without the adjustment, the source image's scroll would skip the bleed area on the right page and visible content would shift left.

Default `outer_bleed_mm=0.0` preserves existing call sites (only zeitung uses SpreadImage today; verified `grep -rn SpreadImage templates/` → only zeitung).
</behavior>
<action>
RED: Write tests in `tools/sla_lib/tests/test_spread_image.py` (UPDATE if exists, else NEW):

```python
class SpreadImageOuterBleedTests(unittest.TestCase):
    def test_default_outer_bleed_zero_unchanged(self):
        """Existing behavior: outer_bleed_mm=0.0 → halves at x=0, w=page_w; right local_offset=(-page_w, 0)."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0, base_anname="P9 Spread")
        left, right = s.emit()
        self.assertAlmostEqual(left.x_mm, 0.0)
        self.assertAlmostEqual(left.w_mm, 210.0)
        self.assertAlmostEqual(right.x_mm, 0.0)
        self.assertAlmostEqual(right.w_mm, 210.0)
        self.assertAlmostEqual(right.local_offset_mm[0], -210.0)

    def test_outer_bleed_3_shifts_left_half_left(self):
        """outer_bleed_mm=3.0 → LEFT x=-3, w=213."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0, base_anname="X", outer_bleed_mm=3.0)
        left, _right = s.emit()
        self.assertAlmostEqual(left.x_mm, -3.0)
        self.assertAlmostEqual(left.w_mm, 213.0)
        self.assertAlmostEqual(left.local_offset_mm[0], 0.0)

    def test_outer_bleed_3_extends_right_half_to_bleed(self):
        """outer_bleed_mm=3.0 → RIGHT x=0, w=213, local_offset_mm=(-213, 0)."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0, base_anname="X", outer_bleed_mm=3.0)
        _left, right = s.emit()
        self.assertAlmostEqual(right.x_mm, 0.0)
        self.assertAlmostEqual(right.w_mm, 213.0)
        self.assertAlmostEqual(right.local_offset_mm[0], -213.0)

    def test_anname_suffix_preserved(self):
        """SPREAD_HALF_RX-friendly suffixes still applied."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0, base_anname="P9 Spread", outer_bleed_mm=3.0)
        left, right = s.emit()
        self.assertEqual(left.anname, "P9 Spread · left")
        self.assertEqual(right.anname, "P9 Spread · right")
```

GREEN: Update `SpreadImage` dataclass in `tools/sla_lib/builder/blocks.py` (L686-740 per RESEARCH.md). Skeleton from RESEARCH.md "Architecture patterns" §SpreadImage extension (consume verbatim):

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
            h_mm=self.h_mm,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(0.0, 0.0),
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · left" if self.base_anname else "",
        )
        right = ImageFrame(
            x_mm=0.0, y_mm=self.y_mm,
            w_mm=self.page_w_mm + b,
            h_mm=self.h_mm,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(-(self.page_w_mm + b), 0.0),
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · right" if self.base_anname else "",
        )
        return left, right
```

REFACTOR: Confirm existing call site in `templates/zeitung-a4-grun/build.py:1845-1852` doesn't pass `outer_bleed_mm` yet (default 0.0 keeps current behavior). T07 will set `outer_bleed_mm=3.0` at that call site.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -m unittest tools.sla_lib.tests.test_spread_image -v 2>&1 | tail -20</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5; echo "EXIT=$?"</automated>
</verify>
<done>
- `SpreadImage.outer_bleed_mm: float = 0.0` field exists.
- 4 new tests in `test_spread_image.py` pass (default zero, left shifted, right extended, anname suffix preserved).
- Default `outer_bleed_mm=0.0` preserves prior behavior (existing zeitung P9 Spread call site unchanged for now).
- `python3 -m unittest discover tools/sla_lib/tests` exits 0.
- `structural_check --all` exits 0 (T05 is independent of geometry; default 0.0 keeps zeitung output identical).
</done>
<dont>
- Don't get the `local_offset_mm` direction wrong (pitfalls B10 — this is the highest-risk arithmetic in T05). The math: source-image native width = `2 * page_w + 2 * outer_bleed` (the source must include bleed margin on both sides of the spine). RIGHT half scrolls source by `-(page_w + outer_bleed)` so the visible portion aligns with the right page including bleed. Verify by inspection: `right.local_offset_mm[0] == -(page_w_mm + outer_bleed_mm)`.
- Don't make `outer_bleed_mm` mandatory — must default 0.0 to preserve existing call sites.
- Don't change `y_mm`, `h_mm`, or any vertical math — bleed extension is horizontal only for spread-page semantics.
- Don't import `outer_bleed_mm` into the `SpreadImage` constructor signature in non-keyword position — keep all params keyword-only-friendly via dataclass defaults.
</dont>
</task>

<task id="T06" type="checkpoint:human-verify" tdd="false">
<name>T06: Phase 3b verification gate — Codex visual review + audit cross-check</name>
<files>reviews/audit-zeitung.json (NEW artifact), reviews/zeitung-visual-*/ (NEW Codex artifact), prompts/zeitung-visual-audit.md (NEW prompt)</files>
<depends-on>T01, T02, T03, T04, T05</depends-on>
<behavior>
Per user direction "build the validation script first until it finds all of those issues by itself" + "review visually if necessary [via Codex] but make sure the script finds these issues in a generic way":

This task is the **build-detector-first contract gate**. T01-T05 land first; T06 verifies the audit catches everything Codex sees BEFORE T07 fixes any geometry. If the audit misses anything Codex sees, the executor RETURNS to T01 and strengthens the rule (without hardcoding Zeitung-specific anname/coords). Iterate until the audit's findings are a superset of Codex's findings for Zeitung.

T06 emits no production code — it's a verification ritual + documentation step. Outputs:
1. `reviews/audit-zeitung.json` — the strict audit output.
2. `reviews/zeitung-visual-<timestamp>/` — Codex's visual review report (created by `issue-cli review-exec`).
3. A short note appended to EXECUTION.md (full EXECUTION.md is T10): "T06 Phase 3b verification: audit catches all N Codex-identified issues; proceed to T07."

ITERATION CONTRACT: if Codex identifies an issue the audit JSON doesn't list, the executor MUST stop, return to T01, modify the rule logic (NOT add Zeitung-specific special cases), re-run T01-T05 verifies, then re-run T06. This may consume multiple iterations. Document each iteration's outcome in EXECUTION.md (kept brief: rule-tightening rationale + Codex finding that triggered it).
</behavior>
<action>
**Step 1.** Create the Codex prompt at `prompts/zeitung-visual-audit.md` (NEW file):

```markdown
# Zeitung visual alignment audit

Read the rendered preview pages at `templates/zeitung-a4-grun/page-1.png` through `page-14.png` and identify alignment issues per page. For each issue produce a structured Markdown entry:

- Page: NN
- Type: bleed-gap | flush-mismatch | partial-overlap | column-axis-drift | spread-seam | other
- Frames involved (best-effort identification by visual position): "<description>"
- What's wrong: short factual description (e.g., "image leaves 3 mm white margin on right edge after print cut")
- Severity: ERROR (visible after print cut) | WARNING (visible but not catastrophic)

Focus on:
1. Full-width frames that don't extend to the bleed (3 mm outside the page edge) on outer edges.
2. Image frames inside colored polygons that are NOT flush with the polygon edges (asymmetric inset = drift).
3. Text frames that partially overlap colored polygons (text crossing the polygon boundary).
4. Adjacent frames whose edges should align (left/right/top/bottom) but visibly drift.
5. Spread images whose seam at the spine doesn't line up correctly.

Do NOT verify against any rule output — read the images fresh. Output only the structured list. Save to `reviews/zeitung-visual-<timestamp>/zeitung-alignment-issues.md`.

Reference: Issue #23 in `.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/`.
```

**Step 2.** Run the audit and capture JSON:

```bash
cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen
mkdir -p reviews
PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict --json > reviews/audit-zeitung.json
# (--strict will exit 1 because Zeitung still has bugs — capture stderr; that's expected pre-T07.)
```

**Step 3.** Run Codex visual review via the existing review-exec tool:

```bash
cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen
issue-cli review-exec \
    --tool codex \
    --prompt prompts/zeitung-visual-audit.md \
    --name zeitung-visual \
    --review-type topic \
    --review-mode topic \
    --output-dir reviews/
# Produces reviews/zeitung-visual-<timestamp>/ with the report.
```

**Step 4.** Cross-check. Read both outputs:
- `reviews/audit-zeitung.json` — list of audit findings (rule_id, targets, message).
- `reviews/zeitung-visual-<timestamp>/*.md` — list of Codex findings (page, type, what's wrong).

For each Codex finding, confirm there is a corresponding audit finding (by page number + frame description). Build a mapping table in EXECUTION.md draft:

| Codex finding (page, type) | Audit finding (rule_id, targets) | match? |
|---|---|---|
| 1, bleed-gap (Cover Hero) | brand:bleed_coverage, ('Cover Hero',) | YES |
| 1, flush-mismatch (Cover/u2950) | brand:cover_extent_match, ('Cover Hero', 'u2950') | YES |
| 8, flush-mismatch (P7 Portrait/u918) | brand:visual_adjacency_drift axis-x-right, ('P7 Portrait', 'u918') | YES |
| ... | ... | ... |

If any row is `NO` (audit misses what Codex sees):
1. STOP. Do not proceed to T07.
2. Return to T01. Identify the GENERIC rule logic gap that caused the miss.
3. Modify the rule (e.g., expand axis check, tune threshold, broaden scope) WITHOUT adding any Zeitung-specific anname or coordinate constant.
4. Re-run T01's verify, then T03 (test changes if rule semantics changed), then T04 (audit defaults still match), then T05 (no impact).
5. Re-run T06 from Step 2.

Acceptable iteration count: 1-3 rounds. If the executor needs more than 3 rounds, report the gap to the user (Codex sees something inherently Zeitung-specific that no generic rule can catch — escalate for design discussion).

If all rows are `YES` (audit ≥ Codex):
1. Append to draft EXECUTION.md: "T06 Phase 3b verification: audit catches all N Codex-identified issues across pages [list]. Iteration count: M. Proceed to T07."
2. The 6 Required-Detection cases from ISSUE.md must all be present:
   - Page 1 Cover Hero ≠ u2950 outer extent → `brand:cover_extent_match` OR `brand:bleed_coverage`
   - Pages 2,5,10,11,12,13,14 (×11 frames) full-width inset → `brand:bleed_coverage`
   - Page 8 P7 Portrait not flush with u918 (3.4 mm right + 5.6 mm top) → `brand:visual_adjacency_drift` (4-axis: dx_right + dy_top)
   - Page 8 P7 Portrait left edge doesn't match column-3 above → `brand:visual_adjacency_drift` (axis-x-left)
   - Page 10 text columns partially overlap green polygon `Kopie von u1529` → `brand:image_text_overlap`
   - Page 11 P10 Portrait right edge 8.1 mm short of bleed → covered by T08 invariant test (P10 below 0.95 cutoff so not bleed_coverage); audit's tolerance-suspicion or visual_adjacency_drift may surface it; if not, T07 fixes it directly per ISSUE.md Phase 4.
3. Commit the audit JSON + Codex review folder + prompt file with `23: docs(reviews): T06 Phase 3b verification — audit catches all N Codex-identified Zeitung issues`.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && test -f reviews/audit-zeitung.json && python3 -c "import json; d = json.load(open('reviews/audit-zeitung.json')); print('audit JSON entries:', len(d) if isinstance(d, list) else len(d.get('findings', d.get('violations', []))))"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && ls reviews/zeitung-visual-*/ 2>&1 | tail -10</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && test -f prompts/zeitung-visual-audit.md && wc -l prompts/zeitung-visual-audit.md</automated>
<manual>Open `reviews/audit-zeitung.json` and the Codex report. Build the cross-check table inline. Confirm every Codex finding has a matching audit finding. If not, STOP and return to T01 — do not proceed to T07. Document the iteration in the running EXECUTION.md draft (full EXECUTION.md created in T10).</manual>
</verify>
<done>
- `reviews/audit-zeitung.json` exists with non-empty findings list.
- `reviews/zeitung-visual-<timestamp>/` directory exists with Codex's report.
- `prompts/zeitung-visual-audit.md` exists.
- Cross-check table documented in EXECUTION.md draft: every Codex visual finding has at least one matching audit finding.
- All 6 Required-Detection cases from ISSUE.md (RESEARCH.md too) appear in audit JSON.
- Iteration count documented (expected 1-3; if >3, escalation note to user).
</done>
<dont>
- Don't proceed to T07 if the audit misses anything Codex sees. STOP and return to T01.
- Don't strengthen rules by hardcoding Zeitung anname/coordinate constants. Strengthen by adjusting thresholds, expanding axis coverage, broadening primitive-type scope. The rules must work on any template.
- Don't skip the Codex visual review. Direct Claude image-read is the FALLBACK only (per ISSUE.md), not the primary verification channel — token budget matters.
- Don't commit `reviews/audit-zeitung-test.json` from T04's verify step; that was a throwaway. Use the strict-mode JSON from T06 Step 2.
- Don't use `--review-mode pr` — this is a topic review of the worktree, not a PR review.
- Don't leave `reviews/audit-zeitung.json` un-committed — it's the audit ground-truth artifact for the PR.
- If T06 surfaces a bug class no generic rule catches AFTER 3 iterations, file the case to user as out-of-scope for #23 — DO NOT solve by hardcoding.
</dont>
</task>

<task id="T07" type="auto" tdd="false">
<name>T07: Zeitung Phase 4 geometry fix + drop 11 encode-and-silence CONSTRAINTS (atomic single commit)</name>
<files>templates/zeitung-a4-grun/build.py, templates/zeitung-a4-grun/meta.yml</files>
<depends-on>T06</depends-on>
<behavior>
Single atomic commit covering Phase 4 (geometry fixes) + Phase 5 (CONSTRAINTS removal). Per locked decision #10: these MUST be coincident — geometry fix without CONSTRAINTS removal leaves widened-tolerance declarations that the audit flags as suspicious; CONSTRAINTS removal without geometry fix surfaces drift warnings the audit was meant to silence. Atomic.

After T07:

**Geometry fixes (apply with the CORRECTED coordinates from RESEARCH.md, NOT the wrong values from ISSUE.md):**
- Cover Hero (page 1): `(x=0, w=210)` → `(x=-3, w=216)` — extends to both outer edges (own_page=0 cover, no spine).
- P1 Hero (page 2, LEFT): `(x=0, w=207)` → `(x=-3, w=210)` — LEFT-page outer = bleed-extended; spine inset preserved at x+w=207 (page_w − margin).
- P4 Foto-Spread (page 5, RIGHT): `(x=3, w=207)` → `(x=3, w=210)` — RESEARCH.md correction: keep spine inset x=3, extend to RIGHT bleed x+w=213. (ISSUE.md said `(x=0, w=213)` — wrong; that would put the spine edge at x=0 inside the spine.)
- P9 Spread (pages 10/11): change call site to `SpreadImage(..., outer_bleed_mm=3.0)` — produces LEFT half `(x=-3, w=213)` and RIGHT half `(x=0, w=213, local_offset_mm=(-213, 0))`. T05 implements the math; T07 just sets the param.
- Page 12 unnamed Dunkelgrün + P11 Bottom (LEFT): each `(x=0, w=207)` → `(x=-3, w=210)`.
- Page 13 unnamed (RIGHT): mirror — `(x=3, w=207)` → `(x=3, w=210)`.
- Page 14 P13 Hero + unnamed (LEFT): each `(x=0, w=207)` → `(x=-3, w=210)`.
- Page 8 P7 Portrait + u918 alignment: portrait `(x=135.3, y=200.6, w=51.3, h=76.4)` → `(x=135.3, y=195, w=54.7, h=82)` — top flush with u918 top (y=195), right flush with u918 right (x+w=190 = u918.x+u918.w). Aligns left with column-3 above (x=135.3, w=54.7).
- Page 10 text columns vs Polygon `Kopie von u1529`: text columns y_mm currently extend down to ~252 overlapping the green card (y=175-277). Recommended: text columns end at y=171 (4 mm gap above green card top y=175). Pin the relationship via `aligned_below(green_card, text_col, gap_mm=4.0, tolerance_mm=0.5)` declaration in CONSTRAINTS — this is an INTENTIONAL adjacency, not encode-and-silence (gap is 4 mm by design). After fix: `brand:image_text_overlap` reports zero violations on the page-10 pair.
- P10 Portrait (page 11): `(x=135.3, y=202.6, w=66.6, h=94.4)` → `(x=135.3, y=202.6, w=77.7, h=94.4)` — RESEARCH.md correction: `w=77.7` (not ISSUE.md's wrong w=74.7) reaches right=213 = outer bleed. Column-x preserved.

**CONSTRAINTS removal — 11 encode-and-silence entries (lines from pitfalls.md A1):**
- L2656: `same_y("u165", "u1d9", tolerance_mm=1.0, ...)` — only widening if drift exceeds default 0.5; verify.
- L2668: `same_y("u1529", "u1544", tolerance_mm=4.0, ...)` — REMOVE.
- L2693-2694: `same_y("Kopie von u2d5c (12)", "Kopie von u2da1 (12)", tolerance_mm=2.0, ...)` — REMOVE if geometry can be tightened, else keep with tolerance_mm=0.5.
- L2695-2696: similar pair — REMOVE or tighten.
- L2700: `same_y("Kopie von u1529", "Kopie von u1544", tolerance_mm=4.0, ...)` — REMOVE.
- L2707-2708: `same_y(..., tolerance_mm=1.5, ...)` — REMOVE or tighten.
- L2709-2710: similar — REMOVE or tighten.
- L2719-2725: 4 entries with tolerance_mm in {1.0, 2.0} — REMOVE, fix geometry, OR keep with tolerance_mm=0.5.

The decision REMOVE-vs-TIGHTEN per entry depends on whether the underlying geometry can be made exact. Heuristic: if the constraint targets text baselines (which have intentional column-grid drift from font metrics), tighten to 0.5 and accept the warning if it fires; if it targets frame-positions that ARE under our control, fix geometry and remove.

Per "F1 anti-pattern" in pitfalls.md: NEVER set `tolerance_mm > 1.0` post-T07. If a declaration needs >1.0 mm, the geometry is wrong — fix it instead.

**Override removal (coincident with the atomic commit):**
- `templates/zeitung-a4-grun/meta.yml`: REMOVE the two T02-pre-applied "scheduled for fix in T07 of #23" overrides for `brand:bleed_coverage` and `brand:image_text_overlap`. After T07 the geometry is clean and Zeitung passes both rules naturally.
</behavior>
<action>
Read the relevant sections of `templates/zeitung-a4-grun/build.py` first (lines listed in `<interfaces>`). Note: the file is auto-generated from upstream SLA but with `sla_diff_strict: false` (meta.yml:20) so manual edits are accepted.

**Step 1.** Apply geometry edits per the behavior list. Use the Edit tool, one frame at a time, citing line numbers from the current file. For SpreadImage:

```python
# Before (templates/zeitung-a4-grun/build.py:1845-1852):
# (whatever current call site is — find it with grep)
SpreadImage(
    image="...",
    page_w_mm=210.0,
    page_h_mm=297.0,
    h_mm=126.13,
    base_anname="P9 Spread",
    # ... other params ...
)

# After:
SpreadImage(
    image="...",
    page_w_mm=210.0,
    page_h_mm=297.0,
    h_mm=126.13,
    base_anname="P9 Spread",
    outer_bleed_mm=3.0,   # Issue #23: extend halves to outer bleed
    # ... other params ...
)
```

For page-10 text-column-vs-green-card: identify the text column frames (likely `Kopie von u2d5c (13)`, `Kopie von u2da1 (16)` per pitfalls A3) and adjust their `y_mm` and `h_mm` so `y_mm + h_mm <= 171` (4 mm above green card top y=175). Then ADD an `aligned_below` declaration to CONSTRAINTS:

```python
aligned_below("Kopie von u1529", "Kopie von u2d5c (13)",
              gap_mm=4.0, tolerance_mm=0.5,
              name="p10_text_above_greencard"),
```

(Note the targets here: `aligned_below(below, above)` — pass the ABOVE frame as the second arg per `tools/sla_lib/builder/constraints.py` factory signature.)

**Step 2.** Drop the 11 encode-and-silence CONSTRAINTS entries (pitfalls.md A1). For each entry: read the geometry it targets; if the geometry is now correct (post-Step 1), DELETE the entry; if the geometry still drifts > 0.5 mm AND the drift is intentional (text-baseline column grid), KEEP the entry but tighten `tolerance_mm` to match the actual drift (≤ 1.0 mm hard ceiling per anti-pattern F1).

Concrete starting point: DELETE all entries with `tolerance_mm >= 4.0` outright (those are the most egregious — L2668, L2700). Re-run audit after the deletes. For each warning that surfaces, decide REMOVE-vs-TIGHTEN per the heuristic above.

**Step 3.** Remove the two T02-applied overrides from `templates/zeitung-a4-grun/meta.yml` (the ones with reason "scheduled for fix in T07 of #23"). Keep other pre-existing overrides (`brand:line_spacing_0.9` etc.).

**Step 4.** Iteratively run `bin/audit-alignment zeitung-a4-grun --strict` and `python3 -m sla_lib.builder.structural_check zeitung-a4-grun`. Both must exit 0. If `--strict` reports findings, address them: fix geometry, remove a CONSTRAINTS entry, or in rare cases add a tightly-scoped declaration (`tolerance_mm <= 1.0`).

**Step 5.** Single atomic commit: stage all of build.py + meta.yml in one commit. DO NOT split into "geometry first, CONSTRAINTS removal second" — that creates an intermediate state where audit explodes with newly-surfaced warnings. Atomic per locked decision #10.

NOTE: `bin/render-gallery` runs in T09. T07 leaves `templates/zeitung-a4-grun/template.sla` and `page-NN.png` files untouched — `bin/check-stale-previews` will FAIL after T07 commits because the SHA in meta.yml no longer matches the upstream SLA (which itself is unchanged, but build.py emits a different template.sla now). That's why T09 is the SHA-bump task. T07's commit will leave CI red briefly between T07 and T09 — acceptable in atomic-PR ordering since they land together.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun 2>&1 | tail -10; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict 2>&1 | tail -15; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "import yaml; d = yaml.safe_load(open('templates/zeitung-a4-grun/meta.yml')); ids = [o['id'] for o in d.get('brand_overrides', [])]; assert 'brand:bleed_coverage' not in ids and 'brand:image_text_overlap' not in ids, f'T02 overrides still present: {ids}'; print('OK, T07 overrides removed:', ids)"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "import re; src = open('templates/zeitung-a4-grun/build.py').read(); hits = re.findall(r'tolerance_mm\s*=\s*([0-9.]+)', src); high = [h for h in hits if float(h) > 1.0]; print('tolerance_mm > 1.0 count:', len(high), high if high else 'none')"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5; echo "EXIT=$?"</automated>
</verify>
<done>
- `bin/audit-alignment zeitung-a4-grun --strict` exits 0 (zero ERROR-severity findings on Zeitung after fix).
- `structural_check zeitung-a4-grun` exits 0 (Zeitung passes all 14 BrandRules naturally, without overrides for bleed_coverage / image_text_overlap).
- Zeitung's `brand_overrides` no longer contains `brand:bleed_coverage` or `brand:image_text_overlap`.
- `tolerance_mm > 1.0` count in zeitung build.py is 0 (anti-pattern F1 enforced).
- Geometry fixes use CORRECTED values per RESEARCH.md (P4 Foto-Spread `x=3,w=210`; P10 Portrait `w=77.7`).
- SpreadImage call site uses `outer_bleed_mm=3.0`.
- 11 encode-and-silence CONSTRAINTS removed or tightened to `tolerance_mm <= 1.0`.
- `structural_check --all` exits 0 across all 9 templates.
- Single atomic commit (one git commit covers ALL geometry + CONSTRAINTS edits + meta.yml override removal).
</done>
<dont>
- Don't pin absolute coordinates in this task in any way that bakes them into the build.py beyond the necessary geometry. The geometry IS the coordinate; T08's invariant tests pin the relationships, not the absolute numbers.
- Don't widen tolerance to silence — fix geometry. Anti-pattern F1.
- Don't split T07 into two commits ("geometry first" + "CONSTRAINTS later"). Atomic.
- Don't run `bin/render-gallery` in T07. That's T09. T07 leaves the .sla and .png artifacts untouched (CI gate is briefly red between T07 and T09 — accepted).
- Don't use ISSUE.md's wrong values: P4 Foto-Spread is `(x=3, w=210)` NOT `(x=0, w=213)`; P10 Portrait is `w=77.7` NOT `w=74.7`. RESEARCH.md "Locked decisions" #9 explicitly corrects.
- Don't move u2950 (already trimmed in #22) or u918 (the cards are correct; the portraits drift, not the cards).
- Don't add `aligned_below` constraints with `tolerance_mm > 1.0`. If you find yourself wanting to, the geometry is wrong — fix it.
- Don't remove the page-10 `aligned_below(green_card, text_col, gap_mm=4.0, tolerance_mm=0.5)` after adding it — it encodes intentional design, not silence.
</dont>
</task>

<task id="T08" type="auto" tdd="true">
<name>T08: Add invariant tests in test_zeitung_geometry.py (relationships, not coordinates)</name>
<files>tools/sla_lib/tests/test_zeitung_geometry.py (NEW)</files>
<depends-on>T07</depends-on>
<behavior>
NEW test file with ≥ 15 invariant-pinning tests covering the relationships established in T07. Per locked decision #7: pin RELATIONSHIPS (frame_a.right == frame_b.right) NOT absolute coordinates (frame_a.right == 213.0). Float-imprecise SLA round-trip (`Cover Hero.w_mm = 209.9999999999361`) makes coordinate-pinning brittle; relationships survive any future Phase 4 retuning.

Per RESEARCH.md "Architecture patterns" §Geometric outcome tests — consume the skeleton verbatim. The test loads zeitung's actual `build_doc()` output and pins the relationships established by T07.
</behavior>
<action>
RED: Write tests that fail BEFORE T07's geometry fix (in principle — T08 lands AFTER T07 so the tests pass on first run; the RED step is mental verification: "would this test have caught the bug pre-T07?").

GREEN: Tests pass on first run because T07 already fixed the geometry.

Helper module structure:

```python
"""Invariant tests for Zeitung geometry — pin RELATIONSHIPS, not coordinates.

Per Issue #23 locked decision #7. Float-imprecise SLA round-trip
(Cover Hero.w_mm = 209.9999999999361) makes coordinate-pinning brittle.
These tests survive any future legitimate Phase 4 retuning that preserves
the alignment intent.
"""
import unittest
from pathlib import Path
from sla_lib.builder.template_loader import load_build_module
from sla_lib.builder.bbox import frame_bbox_mm

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_zeitung_doc():
    mod = load_build_module("zeitung-a4-grun", _REPO_ROOT)
    return mod.build_doc()


def _frame_by_anname(doc, anname):
    """Return (item, page) tuple. Raises if not found."""
    for page in doc.pages:
        if page.is_master:
            continue
        for item in page.items:
            if getattr(item, "anname", "") == anname:
                return item, page
    raise AssertionError(f"frame {anname!r} not found in zeitung doc")


class CoverExtentMatchTests(unittest.TestCase):
    def test_cover_hero_outer_extent_matches_u2950(self):
        """Page 1: Cover Hero outer-bbox extents == u2950 outer-bbox extents."""
        doc = _load_zeitung_doc()
        ch, p_ch = _frame_by_anname(doc, "Cover Hero")
        u, p_u = _frame_by_anname(doc, "u2950")
        ch_bbox = frame_bbox_mm(ch, p_ch)
        u_bbox = frame_bbox_mm(u, p_u)   # rotation-aware (u2950 is rotated 90°)
        self.assertAlmostEqual(ch_bbox[0], u_bbox[0], delta=0.5)   # left edges
        self.assertAlmostEqual(ch_bbox[2], u_bbox[2], delta=0.5)   # right edges


class P7PortraitFlushWithU918Tests(unittest.TestCase):
    def test_p7_portrait_top_flush_with_u918(self):
        doc = _load_zeitung_doc()
        portrait, p_pt = _frame_by_anname(doc, "P7 Portrait")
        u918, p_u = _frame_by_anname(doc, "u918")
        pt_bbox = frame_bbox_mm(portrait, p_pt)
        u_bbox = frame_bbox_mm(u918, p_u)
        self.assertAlmostEqual(pt_bbox[1], u_bbox[1], delta=0.5)   # top edges

    def test_p7_portrait_right_flush_with_u918(self):
        doc = _load_zeitung_doc()
        portrait, p_pt = _frame_by_anname(doc, "P7 Portrait")
        u918, p_u = _frame_by_anname(doc, "u918")
        pt_bbox = frame_bbox_mm(portrait, p_pt)
        u_bbox = frame_bbox_mm(u918, p_u)
        self.assertAlmostEqual(pt_bbox[2], u_bbox[2], delta=0.5)   # right edges


class P10PortraitOuterBleedTests(unittest.TestCase):
    def test_p10_portrait_right_at_outer_bleed(self):
        """Page 11 RIGHT page: P10 Portrait right edge at page_w + bleed = 213 mm."""
        doc = _load_zeitung_doc()
        portrait, page = _frame_by_anname(doc, "P10 Portrait")
        bbox = frame_bbox_mm(portrait, page)
        from sla_lib.builder.primitives import PT_TO_MM
        expected_right = page.width_pt * PT_TO_MM + float(page.bleed_mm or 0)
        self.assertAlmostEqual(bbox[2], expected_right, delta=0.5)


class OuterBleedGapFramesTests(unittest.TestCase):
    """11 frames identified in pitfalls.md A2 must extend to outer bleed."""
    # One test per frame — use parameterised pattern OR explicit per-frame methods.

    def _assert_at_outer_bleed(self, anname, side):
        from sla_lib.builder.primitives import PT_TO_MM
        doc = _load_zeitung_doc()
        item, page = _frame_by_anname(doc, anname)
        bbox = frame_bbox_mm(item, page)
        bleed = float(page.bleed_mm or 0)
        pw = page.width_pt * PT_TO_MM
        if side in ("left", "both"):
            self.assertAlmostEqual(bbox[0], -bleed, delta=0.5,
                                   msg=f"{anname} left edge not at -bleed: {bbox[0]}")
        if side in ("right", "both"):
            self.assertAlmostEqual(bbox[2], pw + bleed, delta=0.5,
                                   msg=f"{anname} right edge not at pw+bleed: {bbox[2]}")

    def test_cover_hero_both_outer_edges(self):
        self._assert_at_outer_bleed("Cover Hero", "both")

    def test_p1_hero_left_outer(self):
        self._assert_at_outer_bleed("P1 Hero", "left")

    def test_p4_foto_spread_right_outer(self):
        self._assert_at_outer_bleed("P4 Foto-Spread", "right")

    def test_p9_spread_left_at_outer_bleed(self):
        self._assert_at_outer_bleed("P9 Spread · left", "left")

    def test_p9_spread_right_at_outer_bleed(self):
        self._assert_at_outer_bleed("P9 Spread · right", "right")

    def test_p11_bottom_left_outer(self):
        self._assert_at_outer_bleed("P11 Bottom", "left")

    def test_p13_hero_left_outer(self):
        self._assert_at_outer_bleed("P13 Hero", "left")

    # Plus tests for the 3 unnamed Dunkelgrün polygons on pages 12/13/14.
    # Since they're unnamed, identify them by class + page + bbox-shape signature.
    # Implement a helper:
    def _assert_unnamed_polygon_at_outer_bleed(self, page_label, expected_y_range, side):
        # find Polygon on page_label whose y0 is in expected_y_range
        ...


class Page10TextColumnsAboveGreenCardTests(unittest.TestCase):
    def test_text_columns_end_above_green_card(self):
        """Page 10: text columns 'Kopie von u2d5c (13)' and 'Kopie von u2da1 (16)' end >= 4mm above 'Kopie von u1529' top."""
        doc = _load_zeitung_doc()
        green, p_g = _frame_by_anname(doc, "Kopie von u1529")
        green_top = frame_bbox_mm(green, p_g)[1]
        for col_anname in ("Kopie von u2d5c (13)", "Kopie von u2da1 (16)"):
            col, p_c = _frame_by_anname(doc, col_anname)
            col_bottom = frame_bbox_mm(col, p_c)[3]
            self.assertLess(col_bottom, green_top - 0.5,
                msg=f"{col_anname} bottom {col_bottom} not above green card top {green_top}")
```

Aim for ≥ 15 test methods total across the classes (count: 1 + 2 + 1 + 11 outer-bleed + 1-2 page-10 = 16-17 tests).

Verify a quick manual sanity check: does the executor have access to all the annames listed? If `P9 Spread · left` doesn't exist (because base_anname="P9 Spread" produces a different suffix), adjust the test annames to match the actual SpreadImage emit names. T05's tests confirm the suffix format is `{base_anname} · left` and `{base_anname} · right`.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -m unittest tools.sla_lib.tests.test_zeitung_geometry -v 2>&1 | tail -30; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -5; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "import re; src = open('tools/sla_lib/tests/test_zeitung_geometry.py').read(); n_tests = len(re.findall(r'def test_', src)); assert n_tests >= 15, f'expected ≥15 tests, got {n_tests}'; print(f'OK: {n_tests} tests')"</automated>
<manual>Read the test file. Confirm: zero `assertAlmostEqual(x_mm, 213.0)` style absolute-coordinate assertions; all assertions are relationship-style (`assertAlmostEqual(a.bbox[0], b.bbox[0], delta=0.5)`) or computed-from-page (`page.width_pt * PT_TO_MM + bleed`).</manual>
</verify>
<done>
- `tools/sla_lib/tests/test_zeitung_geometry.py` exists with ≥ 15 test methods.
- All tests pass (T07's geometry fix makes them GREEN).
- Tests pin RELATIONSHIPS, not absolute coordinates (verified by manual diff inspection).
- Tests cover: cover_extent_match, P7 Portrait flush, P10 Portrait at bleed, all 11 outer-bleed-gap frames (named + unnamed polygons), page-10 text-columns-above-green-card.
- `python3 -m unittest discover tools/sla_lib/tests` exits 0.
</done>
<dont>
- Don't pin absolute coordinates (`self.assertEqual(frame.x_mm, -3.0)`). Pin relationships (`self.assertAlmostEqual(a_bbox[0], b_bbox[0], delta=0.5)`) or page-derived constants (`page.width_pt * PT_TO_MM + page.bleed_mm`).
- Don't use `assertEqual` on float values from SLA round-trip — float-imprecision (`209.9999999999361 != 210.0`). Use `assertAlmostEqual` with `delta=0.5` (mm) or `places=1`.
- Don't look up frames by index in `page.items` — order is not stable. Look up by `anname` via `_frame_by_anname` helper.
- Don't access `frame.x_mm` directly for rotated frames (e.g. u2950) — use `frame_bbox_mm(item, page)` which handles rotation.
- Don't import from `templates.zeitung_a4_grun.build` directly. Use `load_build_module("zeitung-a4-grun", _REPO_ROOT)` so the test path matches how `structural_check` loads it (handles sys.modules cache properly).
- Don't write tests that load every page just to check one frame — `_frame_by_anname` walks all pages but cheap; for performance, cache the `doc` in a class-level `setUpClass` if test count grows.
</dont>
</task>

<task id="T09" type="auto" tdd="false">
<name>T09: Regenerate template.sla + gallery + bump previews_for_sla SHA</name>
<files>templates/zeitung-a4-grun/template.sla, templates/zeitung-a4-grun/template-preview.sla, templates/zeitung-a4-grun/meta.yml, templates/zeitung-a4-grun/preview.pdf, templates/zeitung-a4-grun/page-*.png, templates/zeitung-a4-grun/baseline.pdf, site/public/templates/zeitung-a4-grun/template.sla, site/public/templates/zeitung-a4-grun/preview.pdf, site/public/templates/zeitung-a4-grun/page-*.png</files>
<depends-on>T07, T08</depends-on>
<behavior>
After T09:
- `templates/zeitung-a4-grun/template.sla` regenerated to reflect T07's build.py edits.
- `templates/zeitung-a4-grun/page-*.png` regenerated (14 pages).
- `templates/zeitung-a4-grun/preview.pdf` regenerated.
- `templates/zeitung-a4-grun/meta.yml::previews_for_sla` SHA updated to match the new template.sla.
- `site/public/templates/zeitung-a4-grun/` mirror updated automatically by `bin/render-gallery`.
- `bin/check-stale-previews` exits 0.

This is the canonical render-gallery + SHA-bump step (locked decision #15). Same pattern as #16/#17/#22.
</behavior>
<action>
**Step 1.** Run the render-gallery pipeline:

```bash
cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen
bin/render-gallery zeitung-a4-grun --skip-visual-diff
```

`--skip-visual-diff` is mandatory — `sla_diff_strict: false` means visual diff is informational, but skipping it speeds the run. Internally `bin/render-gallery` already prefixes Scribus invocations with `xvfb-run -a` (verified `visual_diff.py:133`); no manual Xvfb prep needed. Scribus 1.6.5 + brand fonts (42 face entries) verified in pitfalls Section E.

**Step 2.** Verify the regen produced expected outputs:

```bash
ls -la templates/zeitung-a4-grun/template.sla templates/zeitung-a4-grun/preview.pdf templates/zeitung-a4-grun/page-*.png templates/zeitung-a4-grun/baseline.pdf
ls -la site/public/templates/zeitung-a4-grun/
```

Expected: ~14 page-NN.png files in both source and mirror, plus template.sla, preview.pdf, baseline.pdf in source.

**Step 3.** Verify `meta.yml::previews_for_sla` was updated:

```bash
grep "previews_for_sla:" templates/zeitung-a4-grun/meta.yml
# Should be a SHA hash, NOT the old hash from before T07.
```

If `bin/render-gallery` didn't update the SHA automatically (it should — `render_pipeline.py:_update_meta_hash` per pitfalls A15), run:

```bash
PYTHONPATH=tools python3 -c "
import hashlib
sha = hashlib.sha256(open('templates/zeitung-a4-grun/template.sla', 'rb').read()).hexdigest()
print('SHA256:', sha)
# Then update meta.yml manually if needed.
"
```

**Step 4.** Verify `bin/check-stale-previews` is happy:

```bash
bin/check-stale-previews
echo "EXIT=$?"
# Must be 0.
```

**Step 5.** Stage all regenerated artifacts and commit:

```bash
git add \
  templates/zeitung-a4-grun/template.sla \
  templates/zeitung-a4-grun/template-preview.sla \
  templates/zeitung-a4-grun/meta.yml \
  templates/zeitung-a4-grun/preview.pdf \
  templates/zeitung-a4-grun/page-*.png \
  templates/zeitung-a4-grun/baseline.pdf \
  site/public/templates/zeitung-a4-grun/template.sla \
  site/public/templates/zeitung-a4-grun/preview.pdf \
  site/public/templates/zeitung-a4-grun/page-*.png
git status -s | wc -l   # expected ~25-30 files staged
git commit -m "23: chore(zeitung): regenerate template.sla + gallery + bump previews_for_sla SHA"
```

If `bin/render-gallery` fails with `qt.qpa.xcb` errors, prefix with `xvfb-run -a` (already done internally, but worth fallback). If it fails with font errors, verify `fc-list | grep -ci "gotham narrow|vollkorn"` returns ≥ 5 (per pitfalls Section E ≥ 42 verified in this dev container).

If `bin/render-gallery` fails for a non-environmental reason (e.g. an SLA that won't open), DO NOT proceed. The geometry from T07 may be invalid — read the build.py output, run `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` for diagnostic, fix the issue in T07's commit (amend? no — per the no-amend rule, create a fixup commit), then re-run T09.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && bin/check-stale-previews; echo "EXIT=$?"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && ls templates/zeitung-a4-grun/page-*.png 2>&1 | wc -l</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && ls site/public/templates/zeitung-a4-grun/page-*.png 2>&1 | wc -l</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "import yaml, hashlib; m = yaml.safe_load(open('templates/zeitung-a4-grun/meta.yml')); meta_sha = m.get('previews_for_sla', ''); actual_sha = hashlib.sha256(open('templates/zeitung-a4-grun/template.sla', 'rb').read()).hexdigest(); print('meta:', meta_sha[:16] + '...'); print('actual:', actual_sha[:16] + '...'); assert meta_sha == actual_sha, 'SHA mismatch — bin/render-gallery did not bump'; print('SHAs match OK')"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -5; echo "EXIT=$?"</automated>
<manual>Visually inspect `templates/zeitung-a4-grun/page-1.png`, `page-8.png`, `page-10.png`, `page-11.png`, `page-12.png`. Confirm: (1) cover hero extends to all 4 outer edges of the printable area, (2) page-8 P7 portrait flush top+right with the green card, (3) page-10 text columns end above the green card with no overlap, (4) page-11 portrait right edge at the bleed (no white margin), (5) page-12 dark green band extends to outer edge.</manual>
</verify>
<done>
- `bin/check-stale-previews` exits 0.
- 14 page-NN.png files exist in both `templates/zeitung-a4-grun/` and `site/public/templates/zeitung-a4-grun/`.
- `meta.yml::previews_for_sla` SHA matches actual `template.sla` SHA.
- `structural_check --all` exits 0 across all templates.
- `git status` shows the regenerated artifacts staged and committed.
</done>
<dont>
- Don't hand-copy `site/public/templates/zeitung-a4-grun/` files. `bin/render-gallery` mirrors automatically (anti-pattern F6 in pitfalls).
- Don't omit `--skip-visual-diff`. `sla_diff_strict: false` means visual diff doesn't fail CI but it's still slow; skip for the regen step.
- Don't run `bin/render-gallery` without `xvfb-run` prefix manually — the script handles it internally. If it complains, the env is broken, not the script.
- Don't commit before SHA verification. `meta.yml::previews_for_sla` must match `sha256(template.sla)`.
- Don't include `.npy` or `.pyc` or `__pycache__` artifacts that might appear in `templates/zeitung-a4-grun/`. `git status -s | grep zeitung` should show only the listed files.
</dont>
</task>

<task id="T10" type="auto" tdd="false">
<name>T10: EXECUTION.md final summary + status flip</name>
<files>.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/EXECUTION.md (NEW), .issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/ISSUE.md (status flip)</files>
<depends-on>T09</depends-on>
<behavior>
After T10:
- `EXECUTION.md` exists, summarising the work done across T01-T09 with line/file references and any T06-iteration notes.
- ISSUE.md frontmatter `status: open` → `status: in-review` (or whatever the project convention is — check ISSUE.md template; default `in-review` matches PR-pending).
- All acceptance criteria from ISSUE.md mapped to the task that completed them.
- A "Closes #44 in PR description" note (NOT a `git commit -m "closes #44"` — the PR description handles that; ISSUE.md mentions GH issue #44 as `source_url` already).
</behavior>
<action>
Create `.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/EXECUTION.md`:

```markdown
# EXECUTION — Issue #23: Stricter alignment validation + actually fix Zeitung

**Worktree:** `/root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen`
**Branch:** `issue/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen`
**Closes:** GitHub issue #44.

## Summary

Built the alignment detector first (T01-T05), verified it catches every visible Zeitung issue via Codex visual review cross-check (T06), then fixed the Zeitung geometry the detector reports (T07), pinned the relationships in invariant tests (T08), regenerated the gallery + bumped SHAs (T09).

## Tasks

### T01: Add 4 new BrandRules + replace UndeclaredDrift with VisualAdjacencyDrift
Files: `tools/sla_lib/builder/brand_constraints.py`.
Result: registry 11 → 14 rules. New: `brand:bleed_coverage` (ERROR, 0.95 cutoff), `brand:image_text_overlap` (ERROR, Image+filled-Polygon×Text scope), `brand:cover_extent_match` (WARNING). Replacement: `brand:visual_adjacency_drift` (4-axis check + declaration-disagreement, replaces brand:undeclared_alignment_drift). Generic rules; zero Zeitung-specific anname/coords.

### T02: Pre-applied brand_overrides to 6 non-Zeitung templates + Zeitung-temporary
Files: 6 non-Zeitung meta.yml + zeitung-a4-grun/meta.yml.
Result: postkarte/plakat/infostand/wahltag/themen-plakat/kandidat-falzflyer have `brand:image_text_overlap` override with reason "scheduled for follow-up audit per #23". Zeitung temporarily has both `brand:bleed_coverage` and `brand:image_text_overlap` overrides with reason "scheduled for fix in T07 of #23" — REMOVED in T07. wahlaufruf-postkarte-a6-quer untouched per locked decision #12.

### T03: Rule unit tests + bump registry count test 11 → 14
Files: `tools/sla_lib/tests/test_brand_constraints.py`, renamed `test_brand_undeclared_drift.py` → `test_brand_visual_adjacency_drift.py`, NEW `test_brand_bleed_coverage.py`, `test_brand_image_text_overlap.py`, `test_brand_cover_extent_match.py`, updated `test_zeitung_overflow.py`.
Result: ≥ 4 test methods per new rule using synthetic mini-docs. 4-axis tests + declaration-disagreement test for VisualAdjacencyDrift. `test_fourteen_rules_exact` passes.

### T04: Tighten audit_alignment.py defaults + tolerance-suspicion findings
Files: `tools/audit_alignment.py`.
Result: defaults bumped to `--axis-tol-mm 25.0 --adjacency-tol-mm 30.0`. New `--strict` flag. New tolerance-suspicion findings (`tolerance_mm > 1.0` flagged as suspicious). Heuristic suggestions paired with "OR fix geometry" alternative.

### T05: SpreadImage outer_bleed_mm parameter
Files: `tools/sla_lib/builder/blocks.py`, `tools/sla_lib/tests/test_spread_image.py`.
Result: `outer_bleed_mm: float = 0.0` field; emit() math adjusts left x= -bleed, right local_offset_mm = -(page_w + bleed). Default 0.0 preserves existing behavior.

### T06: Phase 3b verification gate (Codex visual review + audit cross-check)
Files: `prompts/zeitung-visual-audit.md`, `reviews/audit-zeitung.json`, `reviews/zeitung-visual-<timestamp>/`.
Result: Audit JSON contains all N findings Codex's visual review identified (cross-check table below). Iteration count: M.

| Codex finding (page, type, what's wrong) | Audit finding (rule_id, targets) | match? |
|---|---|---|
| ... | ... | YES |
| ... | ... | YES |

Iterations: <details on rule strengthening if applicable; otherwise "0 iterations needed">.

### T07: Zeitung Phase 4 geometry fix + drop 11 encode-and-silence CONSTRAINTS (atomic)
Files: `templates/zeitung-a4-grun/build.py`, `templates/zeitung-a4-grun/meta.yml`.
Result: Cover Hero (-3, 216), P1 Hero (-3, 210), P4 Foto-Spread (3, 210), P9 Spread outer_bleed_mm=3.0, P11 Bottom etc., page 8 P7 Portrait flush with u918, page 10 text columns above green card, P10 Portrait w=77.7 (right at bleed). 11 widened-tolerance CONSTRAINTS removed; remaining have `tolerance_mm <= 1.0`. T02-applied Zeitung overrides removed. Atomic single commit per locked decision #10.

### T08: Invariant tests in test_zeitung_geometry.py
Files: `tools/sla_lib/tests/test_zeitung_geometry.py` (NEW).
Result: 16+ relationship-pinning tests (NOT coordinate-pinning). All pass.

### T09: Regenerate template.sla + gallery + SHA bump
Files: `templates/zeitung-a4-grun/template.sla`, `meta.yml`, page-*.png, preview.pdf, baseline.pdf, site/public/ mirror.
Result: `bin/check-stale-previews` exits 0. Gallery regenerated; SHA bumped.

## Acceptance criteria mapping

- [x] `brand:bleed_coverage` exists with ERROR severity + skip mechanism → T01.
- [x] `brand:visual_adjacency_drift` replaces `brand:undeclared_alignment_drift` (4-axis + declaration-disagreement) → T01.
- [x] `brand:image_text_overlap` exists with full test coverage → T01 + T03.
- [x] `brand:cover_extent_match` exists with full test coverage → T01 + T03.
- [x] `tools/audit_alignment.py` defaults tightened + `--strict` flag added → T04.
- [x] `tools/sla_lib/tests/test_zeitung_geometry.py` exists, ≥ 15 tests, all pass after T07 → T08.
- [x] Zeitung's 11 outer-bleed-gap frames fixed (geometry, not encoded) → T07; verified by `bin/audit-alignment zeitung-a4-grun` zero `brand:bleed_coverage` ERRORs.
- [x] Page-1 Cover Hero shares outer-bbox extent with u2950 → T07; verified by `brand:cover_extent_match` zero violations + T08 invariant test.
- [x] Page-8 P7 Portrait flush with u918 → T07; verified by T08 invariant tests.
- [x] Page-10 text/card overlap resolved → T07; verified by `brand:image_text_overlap` zero violations.
- [x] Page-11 P10 Portrait outer edge at bleed → T07; verified by T08 invariant test.
- [x] All Zeitung CONSTRAINTS that previously silenced misalignments removed → T07; remaining have `tolerance_mm <= 1.0`.
- [x] `python3 -m sla_lib.builder.structural_check --all` exits 0 → verified post-T07.
- [x] `python3 -m unittest discover tools/sla_lib/tests` exits 0 → verified post-T08.
- [x] `bin/check-stale-previews` exits 0 → verified post-T09.
- [x] CI green (validated locally; PR will validate in GitHub Actions).
- [ ] User-confirmed pages 1, 8, 10, 11, 12 visually re-checked by human reviewer in PR — out of executor scope.

## Open follow-ups

- File a fixup PR for #17 (postkarte V1, already merged) to re-audit with the new stricter rules. Out of scope for #23 per locked decision #12.
- The 6 pre-applied `brand:image_text_overlap` overrides on non-Zeitung templates should be reviewed in follow-up audits (postkarte/plakat/infostand caption-on-photo cases — likely intentional but unaudited).
```

After writing EXECUTION.md, flip ISSUE.md frontmatter `status: open` → `status: in-review`. Then commit:

```bash
git add .issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/EXECUTION.md \
        .issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/ISSUE.md
git commit -m "23: docs(issues): execution log + status flip to in-review"
```
</action>
<verify>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && test -f .issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/EXECUTION.md && wc -l .issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/EXECUTION.md</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && python3 -c "import yaml; src = open('.issues/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen/ISSUE.md').read(); fm = yaml.safe_load(src.split('---')[1]); print('status:', fm.get('status'))"</automated>
<automated>cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen && git log --oneline -15</automated>
</verify>
<done>
- EXECUTION.md exists with summary, per-task notes, T06 cross-check table, full acceptance-criteria mapping.
- ISSUE.md `status` flipped to `in-review`.
- All 10 task commits visible in `git log` with `23:` prefix and conventional-commit format.
- Final repo state: all tests green, structural_check green, render-gallery green.
</done>
<dont>
- Don't include "claude" or "AI-assisted" mentions in EXECUTION.md (per `feedback_no_claude_attribution.md` user feedback in MEMORY.md).
- Don't close GH issue #44 from a commit message — let the PR description handle "Closes #44". A `git commit -m "closes #44"` would close it on push without a PR review.
- Don't add new sections to EXECUTION.md beyond Summary / Tasks / Acceptance criteria mapping / Open follow-ups. Keep it terse — PR reviewer reads it.
- Don't flip status to `closed` or `done` in T10 — that happens at PR-merge by the issue lifecycle hooks. `in-review` is the correct PR-pending state.
</dont>
</task>

</tasks>

<verification>
After all tasks complete, run final checks:

1. **Full test suite:**
   ```
   cd /root/workspace/.worktrees/23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen
   python3 -m unittest discover tools/sla_lib/tests
   ```
   Must exit 0.

2. **Structural check across all templates (THE CI gate per locked decision #14):**
   ```
   PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
   ```
   Must exit 0. Zeitung passes all 14 BrandRules naturally (no `brand:bleed_coverage` or `brand:image_text_overlap` override). Other 6 templates skip `brand:image_text_overlap` via override; wahlaufruf-postkarte-a6-quer untouched.

3. **Audit tool clean on Zeitung:**
   ```
   PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict
   echo "EXIT=$?"
   ```
   Must exit 0 (zero ERROR-severity findings on Zeitung).

4. **Audit tool runs across all templates:**
   ```
   mkdir -p build/audit
   PYTHONPATH=tools python3 tools/audit_alignment.py --all --output-dir build/audit/
   ls build/audit/
   ```
   Eight or nine `<slug>.md` files produced.

5. **Stale-previews gate:**
   ```
   bin/check-stale-previews
   echo "EXIT=$?"
   ```
   Must exit 0.

6. **Geometry invariant tests pass:**
   ```
   python3 -m unittest tools.sla_lib.tests.test_zeitung_geometry -v
   ```
   ≥ 15 tests, all green.

7. **No tolerance_mm > 1.0 in zeitung CONSTRAINTS:**
   ```
   python3 -c "import re; src = open('templates/zeitung-a4-grun/build.py').read(); hits = [float(h) for h in re.findall(r'tolerance_mm\s*=\s*([0-9.]+)', src)]; assert all(h <= 1.0 for h in hits), f'violation of anti-pattern F1: {[h for h in hits if h > 1.0]}'; print('OK; max tolerance_mm:', max(hits) if hits else 0)"
   ```

8. **YAML lint of pages.yml:**
   ```
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml').read())"
   ```
   No exception. (No edits to pages.yml in #23 per locked decision #14, but verify.)

9. **Git status sanity:**
   ```
   git status -s
   ```
   Expected: empty (all changes committed).

10. **Commit history sanity:**
    ```
    git log --oneline 23:..HEAD 2>/dev/null || git log --oneline -15
    ```
    Should show 10 task commits + the planning commits, all with `23:` prefix.

11. **Codex review artifact present:**
    ```
    ls reviews/zeitung-visual-*/  reviews/audit-zeitung.json  prompts/zeitung-visual-audit.md
    ```
    All three exist (T06 artifacts).
</verification>

<success_criteria>
Mapping to ISSUE.md acceptance criteria (incorporating RESEARCH.md tightenings):

- [x] **`brand:bleed_coverage` exists with full test coverage; severity=ERROR; per-template skip mechanism documented.** → T01 + T03 (test_brand_bleed_coverage.py).
- [x] **`brand:visual_adjacency_drift` replaces `brand:undeclared_alignment_drift` (broader thresholds + 4-axis + declaration-disagreement detection).** → T01 + T03.
- [x] **`brand:image_text_overlap` exists with full test coverage** (RESEARCH.md scope: ImageFrame OR filled-Polygon × TextFrame). → T01 + T03 (test_brand_image_text_overlap.py).
- [x] **`brand:cover_extent_match` exists with full test coverage.** → T01 + T03 (test_brand_cover_extent_match.py).
- [x] **`tools/audit_alignment.py` default thresholds tightened; `--strict` flag added.** → T04.
- [x] **`tools/sla_lib/tests/test_zeitung_geometry.py` exists, ≥ 15 tests, all pass after T07** (RESEARCH.md correction: pin RELATIONSHIPS not coordinates). → T08.
- [x] **Zeitung's 11 outer-bleed-gap frames are fixed (geometry, not encoded).** → T07; verified by `bin/audit-alignment zeitung-a4-grun --strict` zero ERRORs.
- [x] **Page-1 Cover Hero shares outer-bbox extent with u2950.** → T07 + T08 invariant test.
- [x] **Page-8 P7 Portrait flush with u918.** → T07 + T08 invariant test.
- [x] **Page-10 text/card overlap resolved.** → T07; verified by `brand:image_text_overlap` zero violations + T08 invariant test.
- [x] **Page-11 P10 Portrait outer edge at bleed.** → T07; verified by T08 invariant test.
- [x] **All Zeitung CONSTRAINTS that previously silenced misalignments are REMOVED.** → T07; remaining declarations have `tolerance_mm <= 1.0`.
- [x] **`python3 -m sla_lib.builder.structural_check --all` exits 0.** → verification step 2.
- [x] **`python3 -m unittest discover tools/sla_lib/tests` exits 0.** → verification step 1.
- [x] **`bin/check-stale-previews` exits 0.** → T09 + verification step 5.
- [x] **CI green** (validated locally; PR validates remotely).
- [ ] **User-confirmed pages 1, 8, 10, 11, 12 of Zeitung visually re-checked by human reviewer in PR.** → out of executor scope (PR review).

Locked-decision conformance self-check (against RESEARCH.md 15-item table):
- D1 (0.95 cutoff, no `(no-bleed)` tag) → T01.
- D2 (image_text_overlap scope = ImageFrame OR filled-Polygon × TextFrame) → T01 + T03.
- D3 (4-axis check) → T01 + T03 (4 axis tests).
- D4 (constraints kwarg already accepted) → T01 (no plumbing change needed).
- D5 (c.check disagreement loop) → T01 (declaration-disagreement test in T03).
- D6 (tolerance-suspicion finding in audit) → T04.
- D7 (relationship-pinning tests, not coordinate-pinning) → T08.
- D8 (drop 11 encode-and-silence CONSTRAINTS) → T07.
- D9 (corrected coords: P4 Foto-Spread x=3,w=210; P10 Portrait w=77.7) → T07.
- D10 (atomic-PR ordering: T01-T05 → T06 gate → T07 atomic geometry+CONSTRAINTS → T08 tests → T09 regen) → task ordering.
- D11 (SpreadImage outer_bleed_mm) → T05.
- D12 (pre-apply brand:image_text_overlap to 6 non-Zeitung templates) → T02.
- D13 (NEW test_zeitung_geometry.py file) → T08.
- D14 (no new CI step; existing structural_check --all is the gate) → no edits to .github/workflows/pages.yml.
- D15 (render-gallery + SHA bump as last commit before EXECUTION.md) → T09 → T10.

Critical-finding self-check:
- Build-detector-first ordering enforced: T01-T05 land before T06; T06 is a true gate (returns to T01 if audit misses anything Codex sees) → T06 done-list.
- Atomic ordering of T07: geometry fix + CONSTRAINTS removal + Zeitung-override removal in ONE commit → T07 done-list.
- Generic rules only — no Zeitung anname/coordinate constants in rule code → T01 manual verify + T01 dont-list.
- Tests pin relationships, not coordinates → T08 dont-list + manual verify.
- Pre-applied overrides for 6 non-Zeitung templates with reason "scheduled for follow-up audit per #23" + Zeitung-temporary overrides removed in T07 → T02 + T07.
- ISSUE.md numerical corrections applied: P4 Foto-Spread `(x=3, w=210)` not `(x=0, w=213)`; P10 Portrait `w=77.7` not `w=74.7` → T07 dont-list explicitly forbids the wrong values.
- 11 → 14 rule registry count bumped → T03 (`test_fourteen_rules_exact`).
- `bin/render-gallery` + SHA bump as last code commit before EXECUTION.md → T09 → T10.
- `aligned_below(green_card, text_col, gap_mm=4.0, tolerance_mm=0.5)` declaration encodes intentional adjacency, NOT silences drift → T07 (in T07's CONSTRAINTS edit).
</success_criteria>

<risks_and_verification>

## Risks and verification checkpoints

**Build-detector-first contract (load-bearing, locked decision #10):**
- T01-T05 land BEFORE T06. T06 is a true gate, not a doc-stub.
- T06's verification cycle iterates rule-strengthening + re-audit until the audit JSON is a superset of Codex's visual findings. If after 3 iterations Codex still sees something the audit misses, ESCALATE to user — do not solve by Zeitung-specific hardcoding.
- T07 only runs after T06 passes. If T06 doesn't pass, T07 is blocked.
- The user direction "build the validation script first until it finds all of those issues by itself" is a hard precondition, not a recommendation.

**Atomic ordering of T07 (locked decision #10, anti-pattern F1):**
- T07's commit MUST cover: build.py geometry + CONSTRAINTS removal + meta.yml override removal — all in one atomic commit.
- Splitting creates intermediate states where:
  - Geometry fixed but CONSTRAINTS still widened → audit's tolerance-suspicion findings explode.
  - CONSTRAINTS removed but geometry unchanged → BrandRules ERROR-out.
  - Override removed but geometry unfixed → `structural_check` exits 1.
- One-commit-per-task here means one big commit with multiple file changes; that's fine, atomic > granular.

**Codex CLI availability (T06 prerequisite):**
- Verified path: `/root/.npm-global/bin/codex` exists in this dev container.
- `issue-cli review-exec --tool codex` is the canonical invocation per existing `reviews/sonnet-vs-opus-2026-05-07/` and other prior runs.
- If `codex` is unavailable, the FALLBACK is direct Claude image read (Read tool on `templates/zeitung-a4-grun/page-{1,8,10,11,12}.png`) per ISSUE.md Phase 3b "fallback if Codex disagrees with audit". This consumes more tokens — use only if Codex is genuinely broken.

**`bin/render-gallery` regenerates ~30 files; SHA bump enforced (locked decision #15, pitfalls A15):**
- T09 dirties ~25-30 files (template.sla + template-preview.sla + meta.yml + preview.pdf + 14 page-*.png + baseline.pdf + 14 mirror PNGs).
- ALL must be staged in T09's commit. `git status -s | wc -l` should be ≥ 25 after `bin/render-gallery`.
- The mirror to `site/public/templates/zeitung-a4-grun/` is automatic via `_mirror_to_site_public` (anti-pattern F6 — don't hand-copy).
- If the SHA isn't bumped, `bin/check-stale-previews` exits 1 and CI fails. T09 verify step 4 catches this.

**Pre-applied overrides for 6 non-Zeitung templates (locked decision #12, pitfall A14):**
- `templates/wahlaufruf-postkarte-a6-quer/meta.yml` is NOT touched. #17 already merged; needs separate fixup PR.
- The 6 templates that DO get the override: postkarte-a6-kampagne, plakat-a1-hochformat, infostand-tent-card-a5-quer, wahltag-tueranhaenger, themen-plakat-a3-quer, kandidat-falzflyer-din-lang.
- Reason text MUST reference #23 explicitly (provides traceability for the follow-up audit).
- Zeitung itself ALSO gets temporary `brand:bleed_coverage` + `brand:image_text_overlap` overrides in T02 (reason "scheduled for fix in T07 of #23") — REMOVED in T07. Without this, every commit between T01 and T07 is RED.

**T06 might surface issues the audit misses (locked decision #10 contingency):**
- The user direction "if issues are missed: strengthen the rules" is the contract.
- The executor STOPS at T06, returns to T01, modifies the rule code generically (not by hardcoding Zeitung), re-runs T01 verifies, then re-runs T06.
- Each iteration documented in EXECUTION.md (T10) draft. Final iteration count visible in EXECUTION.md.
- Acceptable iteration count: 1-3. > 3 → escalate to user (likely a design issue, not a rule-tuning issue).

**`brand:visual_adjacency_drift` audit-output volume (pitfalls A11):**
- New thresholds (25 mm axis / 30 mm adjacency) produce ~38+ warnings per non-Zeitung template at audit time.
- Severity is `warning`, not `error` — does NOT fail `structural_check --all`. CI stays green.
- Audit-tool report volume is high BUT informational; reviewers can ignore unless investigating.

**Tolerance-suspicion finding may reveal more bugs than expected (locked decision #6):**
- Zeitung has 8 widened-tolerance entries pre-T07 (verified pitfalls A1).
- Audit-tool finding "tolerance_mm > 1.0 is suspicious" surfaces all 8.
- T07 removes them. After T07, zero tolerance-suspicion findings on Zeitung.

**Float-imprecise SLA round-trip (pitfall B1, locked decision #7):**
- `Cover Hero.w_mm = 209.9999999999361` — pin relationships not coordinates in T08.
- `assertAlmostEqual` with `delta=0.5` (mm) is the convention.

**Test count drift (pitfalls B section):**
- `test_eleven_rules_exact` → `test_fourteen_rules_exact` in T03. If a future rule lands AFTER #23 merges, that test must bump again. Acceptable — explicit count is the canary.

**SpreadImage outer_bleed_mm math correctness (pitfall B10, A8):**
- The `local_offset_mm = -(page_w + outer_bleed)` math on the right half is the highest-risk arithmetic. If wrong, the source image scrolls past the bleed area and visible content shifts left.
- T05's tests pin the math at param level; T07 sets `outer_bleed_mm=3.0` at the call site; T09's render-gallery + manual visual inspection of `page-10.png` + `page-11.png` is the final check.

**Token-budget partial-completion fallback:**
- If the executor runs out of usage before T10, work landed up to T07-T08 is still useful: rules + audit + tests + Zeitung geometry are all green; T09 (render-gallery) + T10 (EXECUTION.md) can be a follow-up commit-batch.
- T07 is the highest-value single commit. If you must stop, stop AFTER T07's commit lands (atomic, doesn't break CI when paired with T02's pre-applied overrides — though `bin/check-stale-previews` fails until T09 runs).

**`Page.is_left` is broken (pitfall B4, recurring blind spot):**
- ALL position-detection logic in T01 uses `master_name` regex via SIDE_RX.
- Anyone reading the new rules might be tempted to "fix" them to use `page.is_left` — T01's dont-list explicitly forbids this. Pitfall is verified at `document.py:391-393` (hardcoded False).

</risks_and_verification>
