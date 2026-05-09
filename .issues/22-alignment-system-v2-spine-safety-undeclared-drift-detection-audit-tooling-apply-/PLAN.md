# Plan: Alignment system v2 — spine-safety + undeclared-drift detection + audit tooling + apply to Zeitung

<objective>
Add two new BrandRules (`brand:spine_safety`, `brand:undeclared_alignment_drift`) plus a `tools/audit_alignment.py` CLI/library, refactor shared helpers (`bbox.py`, `template_loader.py`), pre-apply per-template overrides for V1-bound + postkarte + plakat, then encode + fix the Zeitung's intended alignment relationships so each image renders on exactly ONE page (no spine-bleed). Two distinct production-template alignment bugs (spine-bleed across spreads + undeclared drift between text/image/polygon frames) become mechanically detectable, and the Zeitung — the only target encoded in this issue — becomes the worked example.

Why it matters: post-#16 the user identified two bug *classes* (not specific frames); ISSUE #22 captures the user framing — the template either *declares* its alignment intent in `CONSTRAINTS = […]` or the new rule warns. This is the foundation for all future per-template alignment audits (#17–#21 will re-use these rules; postkarte+plakat encoding follows in a successor issue).

Scope IN: 2 new BrandRules with full test coverage; refactor of bbox + template_loader helpers; `tools/audit_alignment.py` + `bin/audit-alignment` shim; pre-applied `brand_overrides[brand:undeclared_alignment_drift]` to 7 templates (5 V1-bound + postkarte-a6-kampagne + plakat-a1-hochformat); fix 6 wrong `master_name` assignments in zeitung; trim u2950 polygon + remove its inside_page override + close GH #39 at PR-merge; convert P4 Foto-Spread + P9 Spread to SpreadImage; inset spine-touching single-page frames in zeitung; encode zeitung CONSTRAINTS list; regen template.sla + gallery; update tests + CI step + SCHEMA + SPEC-WRITING-GUIDE docs.

Scope OUT: per-template CONSTRAINTS encoding for postkarte-a6-kampagne and plakat-a1-hochformat (locked decision #12, deferred); V1 templates' alignment encoding (#17–#21 own that); `meta.yml::audit_strict` + `meta.yml::audit_tolerances` schema extensions (locked decisions #8, #11, deferred); promoting `bin/audit-alignment` from informational to fatal CI (locked decision #10, deferred); per-template visual review by Claude (token budget — human reviewer in PR).
</objective>

<context>
Issue: @.issues/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply-/ISSUE.md
Research: @.issues/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply-/RESEARCH.md
Codebase research: @.issues/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply-/research/codebase.md
Pitfalls research: @.issues/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply-/research/pitfalls.md

<interfaces>
<!-- Executor: use these contracts directly. RESEARCH.md has line-level evidence; quoted skeletons below are authoritative. -->

# tools/sla_lib/builder/brand_constraints.py — current
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc) -> list[Violation]: ...

BRAND_CONSTRAINTS: list[BrandRule] = [...]   # 9 rules today

# Helpers used by _InsidePageRule (Issue #14):
def _rotated_bbox(x: float, y: float, w: float, h: float, deg: float) -> tuple[float, float, float, float]: ...
def _frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]: ...

# tools/sla_lib/builder/structural_check.py — current
def _load_build_module(slug: str, root: Path = _REPO_ROOT): ...                    # at line 104
def check_template(slug: str, root: Path = _REPO_ROOT) -> TemplateReport: ...      # at line 137
# In check_template (line ~209):  violations = rule.check(primitives, doc)

# tools/sla_lib/builder/constraints.py — declared-pair source
@dataclass(frozen=True)
class Constraint:
    id: str
    targets: tuple
    name: str = ""
    def check(self, primitives_by_anname: dict) -> list[Violation]: ...
    def referenced_annames(self) -> tuple: return self.targets

# 12 factories: same_x, same_y, same_size, same_style, equal_gap, hierarchy,
#   mirrored_x, mirrored_y, inside, aligned_below, distance_x, distance_y.
# Pair extraction: itertools.combinations(c.referenced_annames(), 2);
#   key by frozenset({a, b}) for symmetry.

# tools/sla_lib/builder/document.py — facing-page surface
class Document:
    facing_pages: bool
    pages: list[Page]
    masters: list[Page]
    def iter_all_primitives(self): ...

@dataclass
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float
    items: list
    is_master: bool
    is_left: bool          # ALWAYS False on doc pages — DO NOT TRUST
    master_name: str       # canonical side detector — match \b(links|rechts)\b
    label: str

# tools/sla_lib/builder/blocks.py — SpreadImage (Issue #14)
def SpreadImage(left_anname, right_anname, image: str, page_w_mm: float, h_mm: float, ...) -> Block: ...
# Emits two ImageFrames named f"{base} · left" and f"{base} · right";
# left half on LEFT page (x=0, w=page_w_mm), right half on RIGHT page
# (x=0, w=page_w_mm, local_offset_mm=(-page_w_mm, 0)).

# tools/sla_lib/builder/meta_schema.py — overrides surface
def load_brand_overrides(slug: str, root=None) -> set[str]: ...
# Validates {id, reason}; warns if id not in BRAND_CONSTRAINTS.

# After T01 refactor (Locked decision #7):
# tools/sla_lib/builder/bbox.py — public bbox API
def rotated_bbox(x, y, w, h, deg) -> tuple[float, float, float, float]: ...
def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]: ...
# Re-exported from brand_constraints.py as _rotated_bbox / _frame_bbox_mm
# for back-compat (no test churn).

# After T02 refactor (Locked decision #7):
# tools/sla_lib/builder/template_loader.py
def load_build_module(slug: str, root: Path) -> module: ...
# Re-exported from structural_check.py as _load_build_module for back-compat.

# After T03 plumbing (Locked decision #3):
@dataclass(frozen=True)
class BrandRule:
    def check(self, primitives, doc, constraints=None) -> list[Violation]: ...
# All 9 existing rules add `constraints=None` kwarg; ignore it.
# structural_check.check_template passes constraint_list as the 3rd arg:
#   violations = rule.check(primitives, doc, constraints=constraint_list)
</interfaces>

Key files:
@tools/sla_lib/builder/brand_constraints.py — 562-line module; BrandRule + 9 existing rules + bbox helpers (lines 371-418).
@tools/sla_lib/builder/structural_check.py — orchestrator; `_load_build_module` at L104, rule invocation at L209.
@tools/sla_lib/builder/constraints.py — Constraint base + 12 factories + Violation dataclass.
@tools/sla_lib/builder/document.py — Document/Page; `Page.is_left` hardcoded False at L391-393 (DO NOT TRUST).
@tools/sla_lib/builder/blocks.py — SpreadImage at L687; emits "X · left"/"X · right" annames.
@tools/sla_lib/builder/meta_schema.py — `load_brand_overrides` at L52; warns on unknown id.
@tools/sla_lib/tests/test_brand_constraints.py — registry test L48-65 (9 rules → 11).
@tools/sla_lib/tests/test_zeitung_overflow.py — `test_inside_page_finds_only_u2950_without_override` L40-62 (asserts 1 error → 0 after trim).
@tools/sla_lib/tests/test_constraints_inside_page.py — copy this test file shape for new rules.
@templates/zeitung-a4-grun/build.py — 2563 lines. Master defs L71-92; page defs L94-233 (6 wrong `master=` assignments at L158, L168, L188, L198, L208, L228); CONSTRAINTS L2542-2556; user-bug locations: Cover Hero L235, u2950 L246, P7 Portrait L1368, u918 L1327, P9 Spread L1802, P10 Portrait L1894, page-12 unnamed L1952.
@templates/zeitung-a4-grun/meta.yml — `brand_overrides[brand:inside_page]` L39-47 (remove after u2950 trim).
@templates/postkarte-a6-kampagne/build.py — L425 single-witness CONSTRAINTS.
@templates/plakat-a1-hochformat/build.py — L254 single-witness CONSTRAINTS.
@bin/check-stale-previews — copy this 14-line shim shape for `bin/audit-alignment`.
@.github/workflows/pages.yml — structural_check step at L149-155 (audit step appended after).
@templates/_specs/SCHEMA.md — §12 brand catalogue (bump 9 → 11).
@shared/brand/SPEC-WRITING-GUIDE.md — rule catalogue (add new rules + audit-tool reference).
</context>

<commit_format>
Format: conventional with issue-id prefix
Example: `22: feat(brand): add brand:spine_safety rule`
Pattern: `22: <type>(<scope>): <subject>`
Types: feat, fix, test, refactor, docs, chore, ci.
Scopes used in this plan: brand, builder, brand_constraints, audit, zeitung, postkarte, plakat, templates, ci, docs, issues.
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="false">
<name>T01: Refactor — extract bbox helpers to tools/sla_lib/builder/bbox.py</name>
<files>tools/sla_lib/builder/bbox.py (NEW), tools/sla_lib/builder/brand_constraints.py</files>
<depends-on>none</depends-on>
<action>
Locked decision #7. Move `_frame_bbox_mm` (brand_constraints.py L393-418) and `_rotated_bbox` (L371-390) into a new module `tools/sla_lib/builder/bbox.py` as PUBLIC names `frame_bbox_mm` and `rotated_bbox` (no leading underscore). Re-import from `brand_constraints.py` as the underscore-prefixed names so the existing `_InsidePageRule` continues working unchanged.

`tools/sla_lib/builder/bbox.py` skeleton:
```python
"""Public bbox API for BrandRule + audit_alignment (Issue #22).

Extracted from brand_constraints.py L371-418. Two helpers:
- rotated_bbox(x, y, w, h, deg): axis-aligned bbox after CCW rotation
  around the top-left corner. Pivot convention matches Scribus ROT.
- frame_bbox_mm(item, page): page-local mm bbox honouring anchor + rotation.
  Returns None for primitives without spatial extent (Run, ParaStyle).

Limitation: verbatim-pt overrides (xpos_pt / width_pt etc.) are NOT honored;
falls back to *_mm. Carry the same caveat from the original docstring.
"""
from __future__ import annotations
import math
from typing import Optional
from .primitives import resolve_anchor, mm_to_pt, PT_TO_MM


def rotated_bbox(x, y, w, h, deg) -> tuple[float, float, float, float]:
    ...   # verbatim move from brand_constraints.py L371-390

def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    ...   # verbatim move from brand_constraints.py L393-418
```

In `brand_constraints.py` delete the in-file definitions (L371-418) and replace with:
```python
from .bbox import (   # noqa: F401  -- back-compat aliases for existing rules
    frame_bbox_mm as _frame_bbox_mm,
    rotated_bbox as _rotated_bbox,
)
```
near the top of the bbox-helpers section. The `_InsidePageRule` continues to call `_frame_bbox_mm(item, page)` unchanged.

Read the top-of-file imports in `brand_constraints.py` first; if `math` / `resolve_anchor` / `mm_to_pt` / `PT_TO_MM` / `Optional` are no longer referenced after deletion, drop them.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest discover tools/sla_lib/tests 2>&1 | tail -5</automated>
</verify>
<done>
- `tools/sla_lib/builder/bbox.py` exists with public `frame_bbox_mm` + `rotated_bbox`.
- `brand_constraints.py` re-exports them as `_frame_bbox_mm` + `_rotated_bbox`.
- All existing tests pass (especially `test_constraints_inside_page.py`, `test_zeitung_overflow.py`).
- `python3 -m sla_lib.builder.structural_check --all` exits 0 (no behavior change).
</done>
<dont>
- Don't drop the underscore aliases in brand_constraints.py — `test_zeitung_overflow.py:26` imports `_InsidePageRule` directly; other consumers may import the underscored helpers.
- Don't change bbox math semantics. This is a pure relocation.
</dont>
</task>

<task id="T02" type="auto" tdd="false">
<name>T02: Refactor — extract _load_build_module to tools/sla_lib/builder/template_loader.py</name>
<files>tools/sla_lib/builder/template_loader.py (NEW), tools/sla_lib/builder/structural_check.py</files>
<depends-on>T01</depends-on>
<action>
Locked decision #7. Move `_load_build_module` (structural_check.py L104-122) into `tools/sla_lib/builder/template_loader.py` as PUBLIC `load_build_module(slug, root)`. Re-import from `structural_check.py` as the underscored alias.

`tools/sla_lib/builder/template_loader.py` skeleton:
```python
"""Public template-loader for structural_check + audit_alignment (Issue #22).

Extracted from structural_check.py L104-122. The sys.modules.pop() pattern
is critical — it prevents cross-template cache contamination when --all
iterates (P-9 in research/pitfalls.md).
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def load_build_module(slug: str, root: Path = _REPO_ROOT):
    """Load templates/<slug>/build.py via importlib with sys.modules eviction."""
    ...   # verbatim copy of _load_build_module body
```

In `structural_check.py`, replace the L104-122 body with:
```python
from .template_loader import load_build_module as _load_build_module  # noqa: F401
```
Keep `_REPO_ROOT` defined where it currently lives in `structural_check.py` (other functions use it). `template_loader.py` defines its own copy of `_REPO_ROOT` so the helper stays self-contained.

Tests that imported `_load_build_module` from `structural_check` (e.g. `test_structural_check.py`) keep working through the re-export.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_structural_check 2>&1 | tail -5 && python3 -c "from sla_lib.builder.template_loader import load_build_module; print('OK')" 2>&1 | tail -3</automated>
</verify>
<done>
- `tools/sla_lib/builder/template_loader.py` exists with public `load_build_module`.
- `structural_check.py` re-exports as `_load_build_module`.
- `python3 -m sla_lib.builder.structural_check --all` exits 0 unchanged.
</done>
<dont>
- Don't change the sys.modules.pop() ordering — it's load-bearing for `--all`.
- Don't remove the `_load_build_module` alias — downstream tests import it.
</dont>
</task>

<task id="T03" type="auto" tdd="false">
<name>T03: Plumbing — add `constraints=None` kwarg to BrandRule.check + orchestrator pass-through</name>
<files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/builder/structural_check.py</files>
<depends-on>T02</depends-on>
<action>
Locked decision #3 (Option B — signature kwarg). Modify the `BrandRule` base class signature and ALL 9 existing rule subclasses' `check()` methods to accept an optional `constraints=None` kwarg. The 9 existing rules ignore it (default `None`); the two new rules (T04, T05) consume it.

In `brand_constraints.py`:
- Update each of the 9 subclasses' `check()` signature from `def check(self, primitives, doc)` to `def check(self, primitives, doc, constraints=None)`. Body unchanged. Add `# constraints: unused` comment-line where natural.
- Affected classes: `_ColorPaletteRule`, `_FontFamilyRule`, `_LineSpacingRule`, `_HlSlDistanceRule`, `_LogoSize3MRule`, `_TextOnGreenRule`, `_Bleed3mmRule`, `_WahlkreuzColoredBgRule`, `_InsidePageRule`. Use grep `def check(self, primitives` to enumerate.

In `structural_check.py::check_template` at L209, change the call site:
```python
# WAS: violations = rule.check(primitives, doc)
violations = rule.check(primitives, doc, constraints=constraint_list)
```
`constraint_list` is already in scope (defined at L163 as `getattr(mod, "CONSTRAINTS", []) or []`).

Verify the 9 existing rules' tests still pass (no behavior change).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_brand_constraints tools.sla_lib.tests.test_constraints_inside_page tools.sla_lib.tests.test_structural_check 2>&1 | tail -5</automated>
</verify>
<done>
- All 9 existing rules' `check()` accept `constraints=None` (default).
- Orchestrator passes `constraints=constraint_list` at the rule.check() call site.
- All existing brand-rule tests pass; structural_check --all exits 0.
</done>
<dont>
- Don't omit the kwarg on any existing rule — the base class signature change is enforced by the orchestrator's call.
- Don't change `_InsidePageRule` or other rules' actual behavior — just signature.
- Don't introduce a `Document.constraints` attribute (rejected; locked decision #3 picks Option B over Option A).
</dont>
</task>

<task id="T04" type="auto" tdd="true">
<name>T04: Add brand:spine_safety BrandRule + tests</name>
<files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/tests/test_brand_spine_safety.py (NEW)</files>
<depends-on>T03</depends-on>
<behavior>
- On a `facing_pages=True` doc, a non-SpreadImage frame on a LEFT page (master_name matches `\blinks\b`) whose right edge is within `inset_mm - tolerance_mm` of the spine (x = page_w) → emit warning.
- Same for RIGHT pages (master_name matches `\brechts\b`): left edge within tol of x=0.
- SpreadImage halves (anname matches ` · (left|right)$`) are exempt.
- Single-page doc (`facing_pages=False`) → no-op (early return).
- Page with master_name not matching either side → emit ONE warning per such page (so the bug surfaces but doesn't silently skip).
- Rotated frame uses `frame_bbox_mm` axis-aligned bbox (not raw x_mm/w_mm).
- is_master pages skipped.
</behavior>
<action>
RED: Create `tools/sla_lib/tests/test_brand_spine_safety.py` mirroring `test_constraints_inside_page.py`. Implement these 8 test cases (mapping to behavior list; test #8 is the rotated-frame case):

Helpers at file top:
```python
def _facing_doc():
    d = Document(title="t", template_id="t", facing_pages=True)
    d.add_master(name="Neue Musterseite rechts", facing="right")
    d.add_master(name="Neue Musterseite links",  facing="left")
    d.add_page(size="A4", master="Neue Musterseite rechts")  # pages[0] = right
    d.add_page(size="A4", master="Neue Musterseite links")   # pages[1] = left
    return d

def _single_doc():
    d = Document(title="t", template_id="t")  # facing_pages=False default
    d.add_page(size="A4")
    return d

def _find_rule(rid): ...   # copy from test_brand_constraints.py
```

Tests:
1. `test_left_page_right_edge_at_spine_warns`: pages[1].add(ImageFrame(x=0, y=0, w=210, h=100, anname="P1 Hero")) → 1 warning.
2. `test_right_page_left_edge_at_spine_warns`: pages[0].add(ImageFrame(x=0, ...)) → 1 warning.
3. `test_left_page_right_edge_well_inside_passes`: w=200 (10mm inset) → 0.
4. `test_right_page_left_edge_well_inside_passes`: x=10 (10mm inset) → 0.
5. `test_single_page_doc_is_no_op`: `facing_pages=False`, frame at spine → 0.
6. `test_spread_image_halves_skipped`: ImageFrame anname="P4 Foto-Spread · left" on LEFT page → 0.
7. `test_unknown_master_emits_one_warning_per_page`: master="weird" (no links/rechts) → 1 warning per page; assert message contains `"could not be evaluated"`.
8. `test_rotated_polygon_uses_bbox_not_raw`: Polygon at x=180, y=0, w=100, h=10, rotation_deg=90 (rotated bbox right edge approaches spine) on a LEFT page → 1 warning. Verifies `frame_bbox_mm` is used instead of raw x+w.

GREEN: Implement `_SpineSafetyRule` in `brand_constraints.py` using the skeleton from RESEARCH.md L210-275 (verbatim — quoted below):

```python
import re
SPINE_SAFETY_INSET_MM = 3.0
SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)
SPREAD_HALF_RX = re.compile(r" · (left|right)$")

@dataclass(frozen=True)
class _SpineSafetyRule(BrandRule):
    inset_mm: float = SPINE_SAFETY_INSET_MM
    tolerance_mm: float = 0.5

    def check(self, primitives, doc, constraints=None) -> list[Violation]:
        if not getattr(doc, "facing_pages", False):
            return []
        violations: list[Violation] = []
        for page in doc.pages:
            if page.is_master:
                continue
            m = SIDE_RX.search(page.master_name or "")
            if not m:
                violations.append(Violation(
                    severity="warning", rule_id=self.id,
                    message=(
                        f"page {page.label or page.master_name or page.own_page!r} "
                        "uses a master that doesn't match links/rechts; "
                        "spine-safety could not be evaluated"
                    ),
                    targets=(page.master_name or "",),
                ))
                continue
            side = m.group(1).lower()
            pw_mm = page.width_pt * PT_TO_MM
            for item in page.items:
                anname = getattr(item, "anname", "") or ""
                if SPREAD_HALF_RX.search(anname):
                    continue
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, _, x1, _ = bbox
                if side == "links":
                    gap = pw_mm - x1
                    if gap < self.inset_mm - self.tolerance_mm:
                        violations.append(Violation(
                            severity="warning", rule_id=self.id,
                            message=(
                                f"frame {anname or '<unnamed>'!r} on LEFT page "
                                f"{page.master_name!r} has right edge "
                                f"{x1:.2f}mm within {self.inset_mm}mm of spine "
                                f"({pw_mm:.2f}mm); Scribus bleed will leak "
                                "across to the facing RIGHT page"
                            ),
                            targets=(anname or "",),
                        ))
                else:  # "rechts"
                    if x0 < self.inset_mm - self.tolerance_mm:
                        violations.append(Violation(
                            severity="warning", rule_id=self.id,
                            message=(
                                f"frame {anname or '<unnamed>'!r} on RIGHT page "
                                f"{page.master_name!r} has left edge "
                                f"{x0:.2f}mm within {self.inset_mm}mm of spine; "
                                "Scribus bleed will leak across to the facing "
                                "LEFT page"
                            ),
                            targets=(anname or "",),
                        ))
        return violations
```

Add to `BRAND_CONSTRAINTS` registry (append after `_InsidePageRule`):
```python
_make_rule(
    _SpineSafetyRule,
    id="brand:spine_safety",
    name="Spine-safety on facing pages",
    description=(
        "On facing-pages docs, non-SpreadImage frames must inset >=3mm "
        "from the spine; otherwise Scribus bleed leaks across the spread."
    ),
),
```

REFACTOR: keep regex constants module-level (frozen dataclasses can't carry mutable defaults).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_brand_spine_safety -v 2>&1 | tail -15</automated>
</verify>
<done>
- `_SpineSafetyRule` class added with the exact skeleton above.
- Rule registered in `BRAND_CONSTRAINTS` (now 10 entries; T06 bumps test counter).
- 8 tests in `test_brand_spine_safety.py` all pass.
- Imports of `_SpineSafetyRule` work from outside the module.
</done>
<dont>
- Don't trust `Page.is_left` — it's hardcoded False on doc pages (document.py L391-393).
- Don't read raw `item.x_mm` / `item.w_mm` for the bbox — use `_frame_bbox_mm(item, page)` always (anchor + rotation aware).
- Don't substring-match `"links" in name` — use the word-boundary regex `\blinks\b`; future template names may embed substrings.
- Don't forget the `facing_pages=False` early exit; it's the noise-killer for 7 of 8 templates.
- Don't omit `constraints=None` from the signature — T03's plumbing requires it.
</dont>
</task>

<task id="T05" type="auto" tdd="true">
<name>T05: Add brand:undeclared_alignment_drift BrandRule + tests</name>
<files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/tests/test_brand_undeclared_drift.py (NEW)</files>
<depends-on>T04</depends-on>
<behavior>
- For each page, iterate every pair of named primitives (`anname != ""`, both have `frame_bbox_mm() is not None`).
- Skip pairs already declared in the per-template `constraints` list (frozenset key, symmetric).
- Skip pairs where either frame is rotated (`rotation_deg != 0`).
- Suspicious-axis-x: `min_drift_mm < |a.x0 - b.x0| < axis_tolerance_mm` → warning, suggest `same_x`.
- Suspicious-axis-y: same on y → warning, suggest `same_y`.
- Suspicious-adjacency: A above B (`a.y1 < b.y0`) with gap in (min_drift, adjacency_gap_mm) AND `|a.x0 - b.x0| < axis_tolerance_mm` → warning, suggest `aligned_below`.
- Per-template skip via `meta.yml::brand_overrides[brand:undeclared_alignment_drift]` (handled by orchestrator).
- is_master pages skipped; primitives without anname skipped.
</behavior>
<action>
RED: Create `tools/sla_lib/tests/test_brand_undeclared_drift.py`. Test cases (use the same `_facing_doc` / `_single_doc` helpers as T04 — copy or import via `from .test_brand_spine_safety import _facing_doc`):

1. `test_axis_near_pair_without_constraint_warns`: two ImageFrames on same page at x=10 and x=12 (drift 2mm) → 1 warning whose message contains `"same_x"`.
2. `test_axis_near_pair_with_same_x_constraint_silent`: same frames; rule called with `constraints=[same_x("A","B")]` → 0 warnings.
3. `test_far_apart_no_warning`: frames at x=10 and x=100 (drift 90mm > axis_tol 5mm) → 0.
4. `test_stacked_near_with_aligned_below_silent`: A above B at x=10 with gap 4mm + `aligned_below("B","A",gap_mm=4)` → 0.
5. `test_stacked_near_without_constraint_warns`: same geometry, no constraint → 1 warning whose message contains `"aligned_below"`.
6. `test_rotated_frame_skipped`: pair with one rotated → 0.
7. `test_master_page_skipped`: pair on master page only → 0.
8. `test_anonymous_frame_skipped`: pair where one has `anname=""` → 0.

Use `_find_rule("brand:undeclared_alignment_drift")` to locate the registered rule; use `from sla_lib.builder.constraints import same_x, aligned_below` for the constraint factories.

GREEN: Implement `_UndeclaredDriftRule` in `brand_constraints.py` using the skeleton from RESEARCH.md L281-348 (verbatim):

```python
import itertools

@dataclass(frozen=True)
class _UndeclaredDriftRule(BrandRule):
    axis_tolerance_mm: float = 5.0
    adjacency_gap_mm: float = 12.0
    min_drift_mm: float = 0.5

    def check(self, primitives, doc, constraints=None) -> list[Violation]:
        constraints = constraints or []
        declared: set[frozenset[str]] = set()
        for c in constraints:
            try:
                names = c.referenced_annames()
            except Exception:
                continue
            names = [n for n in names if n]
            if len(names) < 2:
                continue
            for a, b in itertools.combinations(names, 2):
                if a != b:
                    declared.add(frozenset((a, b)))
        violations: list[Violation] = []
        for page in doc.pages:
            if page.is_master:
                continue
            spatial = []
            for item in page.items:
                an = getattr(item, "anname", "") or ""
                if not an:
                    continue
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                spatial.append((an, item, bbox))
            for i, (pa, p_item, p_bbox) in enumerate(spatial):
                for qa, q_item, q_bbox in spatial[i + 1:]:
                    if frozenset((pa, qa)) in declared:
                        continue
                    if (float(getattr(p_item, "rotation_deg", 0) or 0) != 0
                            or float(getattr(q_item, "rotation_deg", 0) or 0) != 0):
                        continue
                    px0, py0, px1, py1 = p_bbox
                    qx0, qy0, qx1, qy1 = q_bbox
                    dx = abs(px0 - qx0)
                    dy = abs(py0 - qy0)
                    if self.min_drift_mm < dx < self.axis_tolerance_mm:
                        violations.append(self._mk(pa, qa, "axis-x", dx, "same_x"))
                        continue
                    if self.min_drift_mm < dy < self.axis_tolerance_mm:
                        violations.append(self._mk(pa, qa, "axis-y", dy, "same_y"))
                        continue
                    if py1 < qy0:
                        gap = qy0 - py1
                        if (self.min_drift_mm < gap < self.adjacency_gap_mm
                                and dx < self.axis_tolerance_mm):
                            violations.append(self._mk(
                                pa, qa, "adjacency-y", gap, "aligned_below",
                                extra=f"P below Q (gap {gap:.2f}mm)",
                            ))
        return violations

    def _mk(self, pa, qa, kind, drift, suggested, extra=""):
        return Violation(
            severity="warning",
            rule_id=self.id,
            message=(
                f"frames {pa!r} and {qa!r} appear visually adjacent "
                f"({kind} drift {drift:.2f}mm){' ' + extra if extra else ''}. "
                f"Either declare with {suggested}({pa!r}, {qa!r}, ...) in "
                f"CONSTRAINTS, or fix the geometry."
            ),
            targets=(pa, qa),
        )
```

Add to `BRAND_CONSTRAINTS` registry (after `_SpineSafetyRule`):
```python
_make_rule(
    _UndeclaredDriftRule,
    id="brand:undeclared_alignment_drift",
    name="Undeclared alignment drift",
    description=(
        "Pairs of frames that appear visually aligned/adjacent but are "
        "not declared in the template's CONSTRAINTS list. Heuristic; "
        "warning-only by default."
    ),
),
```
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_brand_undeclared_drift -v 2>&1 | tail -15</automated>
</verify>
<done>
- `_UndeclaredDriftRule` added; rule registered (BRAND_CONSTRAINTS now 11).
- 8 test cases pass.
- `constraints` kwarg path verified by test #2 (passes constraints=[same_x("A","B")]).
</done>
<dont>
- Don't iterate across pages — pair scope is page-local (P-5: SpreadImage halves on different pages would otherwise false-positive).
- Don't use unordered tuples for the declared set — use `frozenset` so `(A,B) == (B,A)` (P-4 mitigation).
- Don't try to extract pairs from BRAND_CONSTRAINTS' rules — they don't expose `referenced_annames()`. Skip via `try/except` (already in skeleton).
- Don't compute drift on rotated frames — bbox math is misleading; skip silently (P-3 mitigation #2).
- Don't include single-target witness constraints (`same_size("X")`) — they yield no pair (`len(names) < 2` guard).
</dont>
</task>

<task id="T06" type="auto" tdd="false">
<name>T06: Bump registry test count 9 → 11; add new rule IDs to canonical set</name>
<files>tools/sla_lib/tests/test_brand_constraints.py</files>
<depends-on>T05</depends-on>
<action>
In `test_brand_constraints.py` L48-65 (`RegistryTests`):

- Rename `test_nine_rules_exact` → `test_eleven_rules_exact`. Body: `self.assertEqual(len(BRAND_CONSTRAINTS), 11)`.
- In `test_ids_are_canonical`, add to the `expected` set: `"brand:spine_safety"`, `"brand:undeclared_alignment_drift"`.

Also extend the imports at L16-28 to include the two new classes (so they're discoverable via this test module):
```python
from sla_lib.builder.brand_constraints import (
    BRAND_CONSTRAINTS, BrandRule,
    _ColorPaletteRule, _FontFamilyRule, _LineSpacingRule,
    _HlSlDistanceRule, _LogoSize3MRule, _TextOnGreenRule,
    _Bleed3mmRule, _WahlkreuzColoredBgRule, _InsidePageRule,
    _SpineSafetyRule,             # NEW (T04)
    _UndeclaredDriftRule,         # NEW (T05)
)
```
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_brand_constraints.RegistryTests -v 2>&1 | tail -10</automated>
</verify>
<done>
- `RegistryTests.test_eleven_rules_exact` passes.
- `test_ids_are_canonical` passes with the 11-element expected set.
- `python3 -m unittest discover tools/sla_lib/tests` exits 0.
</done>
<dont>
- Don't leave the old `test_nine_rules_exact` name — rename it for clarity (avoid magic-number drift).
</dont>
</task>

<task id="T07" type="auto" tdd="false">
<name>T07: Pre-apply brand_overrides[brand:undeclared_alignment_drift] to 7 templates</name>
<files>templates/wahlaufruf-postkarte-a6-quer/meta.yml, templates/wahltag-tueranhaenger/meta.yml, templates/themen-plakat-a3-quer/meta.yml, templates/infostand-tent-card-a5-quer/meta.yml, templates/kandidat-falzflyer-din-lang/meta.yml, templates/postkarte-a6-kampagne/meta.yml, templates/plakat-a1-hochformat/meta.yml</files>
<depends-on>T05</depends-on>
<action>
Locked decision #9 + P-12 (rules MUST exist in `BRAND_CONSTRAINTS` BEFORE overrides are added — T04+T05 satisfy this; T07 runs after).

In each of the 7 `meta.yml` files, append to the existing `brand_overrides:` list (or create the list if absent) a single entry. Read each meta.yml first to see its existing `brand_overrides:` shape; preserve YAML style (existing entries use `>-` folded scalar — match it).

For the 5 V1-bound templates use the template-specific issue number in the `reason` text:
- `wahlaufruf-postkarte-a6-quer` → #17
- `wahltag-tueranhaenger` → #18
- `themen-plakat-a3-quer` → #19
- `infostand-tent-card-a5-quer` → #20
- `kandidat-falzflyer-din-lang` → #21

Pattern (substitute the right issue number):
```yaml
brand_overrides:
  # ... existing entries ...
  - id: brand:undeclared_alignment_drift
    reason: >-
      V1 layout work in #<NN> owns alignment encoding. Re-enable once
      V1 lands and a CONSTRAINTS list captures the declared adjacencies.
```

For `postkarte-a6-kampagne` and `plakat-a1-hochformat`:
```yaml
brand_overrides:
  # ... existing entries ...
  - id: brand:undeclared_alignment_drift
    reason: >-
      Per-template alignment encoding scheduled for the #22 follow-up.
      Spine-safety is a no-op (single-page template) and the new rule
      infrastructure ships globally in #22; CONSTRAINTS encoding for
      this template is deferred.
```

After all 7 edits run `structural_check --all`. Should exit 0 with `brand:undeclared_alignment_drift` listed under `skipped_brand_rules` for the 7 templates and ACTIVE on zeitung (will produce warnings on zeitung pre-T13/T14 — that's expected mid-PR; warnings don't fail CI).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -20</automated>
</verify>
<done>
- Each of 7 meta.yml files has `brand_overrides[brand:undeclared_alignment_drift]` with the right reason text.
- `structural_check --all` exits 0 (warnings on zeitung are expected; only errors fail).
- No `UserWarning: brand_override id ... not in BRAND_CONSTRAINTS` (T04+T05 registered it).
</done>
<dont>
- Don't add the override to `zeitung-a4-grun/meta.yml` — zeitung is the encoded target (T14).
- Don't omit the reason text — `meta_schema._BRAND_OVERRIDE_SCHEMA` requires `{id, reason}`.
- Don't run T07 before T04+T05 — `meta_schema._validate_and_collect_ids` warns when override id is unknown.
</dont>
</task>

<task id="T08" type="auto" tdd="true">
<name>T08: Add tools/audit_alignment.py + bin/audit-alignment shim + tests</name>
<files>tools/audit_alignment.py (NEW), bin/audit-alignment (NEW), tools/sla_lib/tests/test_audit_alignment.py (NEW)</files>
<depends-on>T05, T02, T01</depends-on>
<behavior>
- Library API: `audit_template(slug, root, axis_tol_mm=5.0, adjacency_tol_mm=12.0) -> TemplateAuditReport`; `audit_all(root) -> list[TemplateAuditReport]`; `report_to_markdown(rep)`; `report_to_json(rep)`. Plus `_audit_doc(doc, constraints, axis_tol_mm, adjacency_tol_mm) -> TemplateAuditReport` for synthetic-doc tests.
- CLI: `audit_alignment.py <slug> [--json | --md FILE.md] [--all] [--output-dir DIR] [--axis-tol-mm 5.0] [--adjacency-tol-mm 12.0]`. Exit 0 always (informational).
- Per page: enumerate primitives via `frame_bbox_mm`, compute declared pairs from `mod.CONSTRAINTS`, run the same heuristic as `_UndeclaredDriftRule`, also flag spine-safety candidates (re-using `_SpineSafetyRule` outputs).
- Markdown report includes ready-to-paste `same_x(...)`, `same_y(...)`, `aligned_below(...)` skeletons (per P-14).
</behavior>
<action>
RED: Create `tools/sla_lib/tests/test_audit_alignment.py`. Tests:

1. `test_synthetic_doc_flags_axis_near_pair`: build synthetic Document with two ImageFrames at x=10/x=12 same page; call `_audit_doc(doc, constraints=[], axis_tol_mm=5.0, adjacency_tol_mm=12.0)`; assert exactly one suspicious pair on page 1.
2. `test_synthetic_doc_with_same_x_constraint_silent`: same doc + constraints=[same_x("A","B")]; assert zero suspicious pairs.
3. `test_audit_all_enumerates_all_templates`: `audit_all(root=ROOT)` returns one `TemplateAuditReport` per slug under `templates/` (excluding `_specs`/`_smoke`); assert `len(reports) == len(discover_template_slugs(ROOT))`.
4. `test_json_output_is_valid_dict`: `report_to_json(rep)` returns a dict with keys `slug`, `facing_pages`, `pages`, `fatal_error`.
5. `test_md_output_is_parseable`: `report_to_markdown(rep)` returns a string starting with `"# audit_alignment"`; when there's a suspicious pair, contains a `same_x(` or `aligned_below(` skeleton.
6. `test_cli_exits_zero_on_warnings`: `from audit_alignment import main; assert main(["zeitung-a4-grun", "--md", "/tmp/r.md"]) == 0` even when warnings present.

GREEN: Implement `tools/audit_alignment.py`. Mirror `tools/spec_check.py` shape. Skeleton:

```python
#!/usr/bin/env python3
"""audit_alignment — alignment-audit CLI + library (Issue #22).

CLI:
  python3 tools/audit_alignment.py <slug> [--json | --md FILE.md]
  python3 tools/audit_alignment.py --all [--output-dir build/audit/]
  --axis-tol-mm <float>       (default 5.0)
  --adjacency-tol-mm <float>  (default 12.0)
Always exits 0 (informational).
"""
from __future__ import annotations
import argparse
import itertools
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from sla_lib.builder.template_loader import load_build_module
from sla_lib.builder.structural_check import discover_template_slugs
from sla_lib.builder.bbox import frame_bbox_mm
from sla_lib.builder.brand_constraints import (
    _SpineSafetyRule, SIDE_RX,
)

DEFAULTS = dict(axis_tol_mm=5.0, adjacency_tol_mm=12.0, min_drift_mm=0.5)


@dataclass
class SuspiciousPair:
    a: str
    b: str
    kind: str        # "axis-x" | "axis-y" | "adjacency-y"
    delta_mm: float
    suggested: str   # ready-to-paste 'same_x("A", "B", name="p1_x")'


@dataclass
class PageAuditReport:
    page_idx: int
    page_label: str
    master_name: str
    side: Optional[str]
    n_primitives: int
    declared_pairs: list[tuple[str, str]] = field(default_factory=list)
    suspicious_pairs: list[SuspiciousPair] = field(default_factory=list)
    spine_warnings: list[str] = field(default_factory=list)


@dataclass
class TemplateAuditReport:
    slug: str
    facing_pages: bool
    pages: list[PageAuditReport] = field(default_factory=list)
    fatal_error: Optional[str] = None


def _build_declared(constraints) -> set[frozenset[str]]:
    declared = set()
    for c in constraints or []:
        try:
            names = [n for n in c.referenced_annames() if n]
        except Exception:
            continue
        if len(names) < 2:
            continue
        for a, b in itertools.combinations(names, 2):
            if a != b:
                declared.add(frozenset((a, b)))
    return declared


def _audit_doc(doc, constraints, axis_tol_mm: float, adjacency_tol_mm: float,
               slug: str = "<doc>") -> TemplateAuditReport:
    declared = _build_declared(constraints)
    rep = TemplateAuditReport(
        slug=slug,
        facing_pages=getattr(doc, "facing_pages", False),
    )
    spine_rule = _SpineSafetyRule(
        id="brand:spine_safety", name="", description="",
    )
    spine_violations = spine_rule.check(
        list(doc.iter_all_primitives()), doc, constraints=constraints,
    )
    for idx, page in enumerate(doc.pages):
        if page.is_master:
            continue
        m = SIDE_RX.search(page.master_name or "")
        side = m.group(1).lower() if m else None
        spatial = []
        for item in page.items:
            an = getattr(item, "anname", "") or ""
            if not an:
                continue
            bbox = frame_bbox_mm(item, page)
            if bbox is None:
                continue
            spatial.append((an, item, bbox))
        page_rep = PageAuditReport(
            page_idx=idx,
            page_label=page.label or page.master_name or f"page#{idx}",
            master_name=page.master_name or "",
            side={"links": "left", "rechts": "right"}.get(side or ""),
            n_primitives=len(spatial),
        )
        for i, (pa, _, _) in enumerate(spatial):
            for qa, _, _ in spatial[i + 1:]:
                if frozenset((pa, qa)) in declared:
                    page_rep.declared_pairs.append((pa, qa))
        for i, (pa, p_item, p_bbox) in enumerate(spatial):
            for qa, q_item, q_bbox in spatial[i + 1:]:
                if frozenset((pa, qa)) in declared:
                    continue
                if (float(getattr(p_item, "rotation_deg", 0) or 0) != 0
                        or float(getattr(q_item, "rotation_deg", 0) or 0) != 0):
                    continue
                px0, py0, px1, py1 = p_bbox
                qx0, qy0, qx1, qy1 = q_bbox
                dx = abs(px0 - qx0); dy = abs(py0 - qy0)
                if DEFAULTS["min_drift_mm"] < dx < axis_tol_mm:
                    page_rep.suspicious_pairs.append(SuspiciousPair(
                        a=pa, b=qa, kind="axis-x", delta_mm=dx,
                        suggested=f'same_x("{pa}", "{qa}", name="p{idx+1}_x")',
                    ))
                    continue
                if DEFAULTS["min_drift_mm"] < dy < axis_tol_mm:
                    page_rep.suspicious_pairs.append(SuspiciousPair(
                        a=pa, b=qa, kind="axis-y", delta_mm=dy,
                        suggested=f'same_y("{pa}", "{qa}", name="p{idx+1}_y")',
                    ))
                    continue
                if py1 < qy0:
                    gap = qy0 - py1
                    if (DEFAULTS["min_drift_mm"] < gap < adjacency_tol_mm
                            and dx < axis_tol_mm):
                        page_rep.suspicious_pairs.append(SuspiciousPair(
                            a=pa, b=qa, kind="adjacency-y", delta_mm=gap,
                            suggested=(
                                f'aligned_below("{qa}", "{pa}", '
                                f'gap_mm={gap:.2f}, name="p{idx+1}_below")'
                            ),
                        ))
        rep.pages.append(page_rep)
    # Spine warnings — best-effort: attach to first page (precise targeting
    # not required; the message text already names the page).
    if spine_violations and rep.pages:
        for v in spine_violations:
            rep.pages[0].spine_warnings.append(v.message)
    return rep


def audit_template(slug: str, root: Path = REPO_ROOT,
                   axis_tol_mm: float = DEFAULTS["axis_tol_mm"],
                   adjacency_tol_mm: float = DEFAULTS["adjacency_tol_mm"]) \
                   -> TemplateAuditReport:
    try:
        mod = load_build_module(slug, root)
        doc = mod.build_doc()
    except Exception as e:
        return TemplateAuditReport(slug=slug, facing_pages=False,
                                   fatal_error=f"build failed: {e!r}")
    constraints = getattr(mod, "CONSTRAINTS", []) or []
    return _audit_doc(doc, constraints, axis_tol_mm, adjacency_tol_mm, slug)


def audit_all(root: Path = REPO_ROOT) -> list[TemplateAuditReport]:
    return [audit_template(slug, root) for slug in discover_template_slugs(root)]


def report_to_markdown(rep: TemplateAuditReport) -> str:
    lines = [f"# audit_alignment: {rep.slug}", "",
             f"facing_pages: {rep.facing_pages}",
             f"pages: {len(rep.pages)}", ""]
    if rep.fatal_error:
        lines.append(f"FATAL: {rep.fatal_error}")
        return "\n".join(lines)
    lines += [
        "```python",
        "from sla_lib.builder.constraints import (",
        "    same_x, same_y, aligned_below, inside, distance_x,",
        "    distance_y, equal_gap, same_size,",
        ")",
        "```", "",
    ]
    for pr in rep.pages:
        lines.append(
            f"## Page {pr.page_idx + 1} "
            f"(master: {pr.master_name!r}, side: {pr.side or 'n/a'})"
        )
        lines.append(f"- primitives: {pr.n_primitives}")
        lines.append(f"- declared pairs: {len(pr.declared_pairs)}")
        if pr.suspicious_pairs:
            lines.append(f"- suspicious-undeclared adjacencies "
                         f"({len(pr.suspicious_pairs)}):")
            for sp in pr.suspicious_pairs:
                lines.append(
                    f"  - {sp.kind} drift {sp.delta_mm:.2f}mm: "
                    f"`{sp.a}` ↔ `{sp.b}`"
                )
                lines.append(f"    - suggested: `{sp.suggested}`")
        if pr.spine_warnings:
            lines.append(f"- spine-safety candidates ({len(pr.spine_warnings)}):")
            for sw in pr.spine_warnings:
                lines.append(f"  - {sw}")
        lines.append("")
    return "\n".join(lines)


def report_to_json(rep: TemplateAuditReport) -> dict:
    return {
        "slug": rep.slug,
        "facing_pages": rep.facing_pages,
        "fatal_error": rep.fatal_error,
        "pages": [
            {
                "page_idx": pr.page_idx,
                "page_label": pr.page_label,
                "master_name": pr.master_name,
                "side": pr.side,
                "n_primitives": pr.n_primitives,
                "declared_pairs": [[a, b] for a, b in pr.declared_pairs],
                "suspicious_pairs": [
                    {"a": sp.a, "b": sp.b, "kind": sp.kind,
                     "delta_mm": sp.delta_mm, "suggested": sp.suggested}
                    for sp in pr.suspicious_pairs
                ],
                "spine_warnings": pr.spine_warnings,
            }
            for pr in rep.pages
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="audit_alignment")
    ap.add_argument("slug", nargs="?", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", default=None,
                    help="write Markdown report to PATH instead of stdout")
    ap.add_argument("--output-dir", default=None,
                    help="--all: write per-template Markdown reports here")
    ap.add_argument("--axis-tol-mm", type=float, default=DEFAULTS["axis_tol_mm"])
    ap.add_argument("--adjacency-tol-mm", type=float, default=DEFAULTS["adjacency_tol_mm"])
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ns = ap.parse_args(argv)
    if ns.all:
        reps = audit_all(ns.root)
        if ns.output_dir:
            Path(ns.output_dir).mkdir(parents=True, exist_ok=True)
            for rep in reps:
                (Path(ns.output_dir) / f"{rep.slug}.md").write_text(
                    report_to_markdown(rep), encoding="utf-8")
        else:
            for rep in reps:
                print(report_to_markdown(rep))
                print()
        return 0
    if not ns.slug:
        ap.error("slug or --all required")
    rep = audit_template(ns.slug, ns.root,
                         axis_tol_mm=ns.axis_tol_mm,
                         adjacency_tol_mm=ns.adjacency_tol_mm)
    if ns.json:
        print(json.dumps(report_to_json(rep), indent=2, ensure_ascii=False))
    elif ns.md:
        Path(ns.md).write_text(report_to_markdown(rep), encoding="utf-8")
    else:
        print(report_to_markdown(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Create `bin/audit-alignment` (mirror `bin/check-stale-previews` exactly):
```python
#!/usr/bin/env python3
"""bin/audit-alignment — alignment-audit shim (Issue #22).

See tools/audit_alignment.py for implementation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from audit_alignment import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```
Run `chmod +x bin/audit-alignment` after writing.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_audit_alignment -v 2>&1 | tail -15 && bin/audit-alignment zeitung-a4-grun 2>&1 | head -10</automated>
</verify>
<done>
- `tools/audit_alignment.py` exists with library + CLI per behavior block.
- `bin/audit-alignment` exists, executable, runs `main()`.
- `tools/sla_lib/tests/test_audit_alignment.py` has 6 tests, all pass.
- `bin/audit-alignment zeitung-a4-grun` produces a non-empty Markdown report and exits 0.
</done>
<dont>
- Don't re-implement `_load_build_module` — import from `template_loader` (P-9: sys.modules cache poisoning).
- Don't read raw `item.x_mm` — use `frame_bbox_mm` (P-1: anchor + rotation invisibility).
- Don't make CLI exit non-zero on warnings — locked decision #10 says informational only.
- Don't put `pdfimages -list` cross-spread check in the BrandRule path; if you add it later (out of scope here), gate behind explicit `--check-pdf` flag (P-10).
</dont>
</task>

<task id="T09" type="auto" tdd="false">
<name>T09: Fix 6 wrong master_name assignments in zeitung build.py</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T08</depends-on>
<action>
Per the per-page table in research/codebase.md §3 + RESEARCH.md "Locked decisions" #4 / "Critical findings" — six page additions in zeitung carry the wrong master. The grep evidence (verified line numbers):
- L158: `master='Neue Musterseite links'` → should be `'Neue Musterseite rechts'` (page 7).
- L168: `master='Neue Musterseite rechts'` → should be `'Neue Musterseite links'` (page 8).
- L188: `master='Neue Musterseite links'` → should be `'Neue Musterseite rechts'` (page 10).
- L208: `master='Neue Musterseite links'` → should be `'Neue Musterseite rechts'` (page 12).
- L228: `master='Neue Musterseite links'` → should be `'Neue Musterseite rechts'` (page 14).
- Plus page 9 (the 6th case from RESEARCH.md): re-grep the file before editing — RESEARCH.md says pages 6, 7, 9, 11, 13 should be `rechts` and page 8 should be `links`. Cross-reference the printed `pageN` index against print page number when editing (zeitung uses 1-indexed print pages but 0-indexed `pages[]`).

Workflow:
1. Re-run grep `grep -n "d.add_page\|master='Neue Musterseite" templates/zeitung-a4-grun/build.py` and confirm the 16 lines (2 master defs + 14 page-add invocations).
2. For each of the 6 wrong assignments, swap `'Neue Musterseite links' ↔ 'Neue Musterseite rechts'`.
3. After all 6 edits, run `python3 templates/zeitung-a4-grun/build.py` to regenerate template.sla in-place. Then `structural_check zeitung-a4-grun` — confirm no NEW errors (pre-existing inside_page warning still expected — T10 trims u2950).

Note: `meta.yml::sla_diff_strict: false` already opted out of strict round-trip diff (per #16) — these master assignments will diverge from upstream Scribus original, which is fine.

This MUST land BEFORE T10 (which removes the inside_page override) and before T14 (CONSTRAINTS encoding) so spine-safety has correct sides to evaluate against.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun 2>&1 | tail -20</automated>
</verify>
<done>
- 6 master assignments corrected to match the table in research/codebase.md §3.
- `structural_check zeitung-a4-grun` exits 0 (warnings on spine_safety / inside_page acceptable mid-PR).
- `python3 -c "from sla_lib.builder.template_loader import load_build_module; m = load_build_module('zeitung-a4-grun'); d = m.build_doc(); print([(i, p.master_name) for i, p in enumerate(d.pages)])"` reports the correct alternation.
</done>
<dont>
- Don't change the master DEFINITIONS at L71-92 — only the page-level `master=` keyword on the relevant `add_page` calls.
- Don't run T10 (remove inside_page override) before T09 lands; T10 also depends on T11/T12/T13 geometry fixes silencing residual inside_page errors.
</dont>
</task>

<task id="T10" type="auto" tdd="false">
<name>T10: Trim u2950 cover polygon to fit page+bleed</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T09</depends-on>
<action>
Per RESEARCH.md "Critical findings" + ISSUE.md ¶ "Trim u2950 polygon" + the `meta.yml` note pointing at GH #39.

`u2950` is at L246-256 in `templates/zeitung-a4-grun/build.py`: rotated polygon at `(x=216.41, y=155.567, w=148.602, h=220.489, rotation_deg=90, fill='Dunkelgrün')`. Rotation-aware bbox: `(-4.08, 155.57)→(216.41, 304.17)` — overshoots the page bottom (300) by 4.17mm and the right bleed (213) by 3.41mm.

Trim so the rotated bbox fits within `[-3, 213] × [152.57, 303]` (page+bleed). Conservative choice: keep the rotation_deg=90 + the fill, but reduce `h_mm` from 220.489 → 213.49 (down by 7mm) so the rotated bbox max-x becomes 209.41 instead of 216.41 (well within +bleed=213). And reduce `w_mm` from 148.602 → 147.43 (down by 1.17mm) so the rotated bbox max-y becomes 303 exactly.

Confirm geometry mathematically: the rotated bbox of a rect (x, y, w, h, deg=90) around the top-left corner is:
- min_x = x - h, max_x = x
- min_y = y, max_y = y + w
So set h_mm such that `x - h_mm >= -3` (currently 216.41 - h >= -3 → h <= 219.41 — tight, but we want to clear the right bleed too). Set w_mm such that `y + w_mm <= 303` (currently 155.567 + w <= 303 → w <= 147.43).

After trimming:
1. Run `python3 templates/zeitung-a4-grun/build.py`.
2. Verify with the in-test rule (no override): `python3 -c "from sla_lib.builder.template_loader import load_build_module; m = load_build_module('zeitung-a4-grun'); d = m.build_doc(); from sla_lib.builder.brand_constraints import _InsidePageRule; r = _InsidePageRule(id='brand:inside_page', name='', description=''); v = r.check(list(d.iter_all_primitives()), d); errors = [x for x in v if x.severity == 'error']; print('ERRORS:', len(errors), errors)"` — should print 0 errors.

Trimming may surface other Page-1 cover alignment issues; if `same_size("Cover Hero", "u2950", axis="w")` becomes desired (per ISSUE.md Phase 2 example), encode it in T14.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -c "
import sys; sys.path.insert(0, 'tools')
from sla_lib.builder.template_loader import load_build_module
from sla_lib.builder.brand_constraints import _InsidePageRule
m = load_build_module('zeitung-a4-grun')
d = m.build_doc()
r = _InsidePageRule(id='brand:inside_page', name='', description='')
v = r.check(list(d.iter_all_primitives()), d)
errors = [x for x in v if x.severity == 'error']
print('inside_page errors after u2950 trim:', len(errors))
for e in errors: print(' -', e.targets, e.message[:80])
assert len(errors) == 0, f'still have {len(errors)} errors'
" 2>&1 | tail -10</automated>
</verify>
<done>
- u2950's `w_mm` and `h_mm` reduced so rotated bbox fits within page+bleed.
- In-process `_InsidePageRule(id='brand:inside_page', ...)` reports zero errors on zeitung WITHOUT the override.
- `python3 templates/zeitung-a4-grun/build.py` runs without exception.
</done>
<dont>
- Don't change `rotation_deg` or fill — semantic shape stays the same.
- Don't change the polygon's `(x, y)` — keep top-left anchor.
- Don't remove the `brand_overrides[brand:inside_page]` here; T16 removes it AFTER T11/T12/T13 also pass clean.
</dont>
</task>

<task id="T11" type="auto" tdd="false">
<name>T11: Convert P4 Foto-Spread + P9 Spread to SpreadImage</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T10</depends-on>
<action>
Per ISSUE.md Phase 3 + RESEARCH.md "Pitfalls #8" (P4 + P9 rename cascade).

Both `P4 Foto-Spread` (currently the page-4/5 spread) and `P9 Spread` (current single-page frame at build.py L1802 — #16's misfix) are intended TWO-PAGE spreads. Replace each with a `SpreadImage` block from `tools/sla_lib/builder/blocks.py`.

For `P4 Foto-Spread` (locate in build.py via grep `P4 Foto-Spread`):
- Replace the existing single-page ImageFrame (or pair) with a SpreadImage block call:
  ```python
  from sla_lib.builder.blocks import SpreadImage
  spread = SpreadImage(
      left_anname="P4 Foto-Spread · left",
      right_anname="P4 Foto-Spread · right",
      image="<existing image path>",
      page_w_mm=210.0,
      h_mm=<existing h>,
  )
  # Add the LEFT half to the LEFT page (idx 3 = print page 4) and the
  # RIGHT half to the RIGHT page (idx 4 = print page 5):
  page3.add(spread.left_half())
  page4.add(spread.right_half())
  ```
  (Read blocks.py L687+ for the exact SpreadImage API and helper-method names; if SpreadImage exposes a single `add_to(left_page, right_page)` method, use that instead.)

For `P9 Spread` (build.py L1802-1811):
- Same pattern. Identify the partner page (the one that currently renders blank because #16 moved this frame to a single page). Add `· left` to the LEFT-side page and `· right` to the RIGHT-side page.

Update `INJECT_MAP` at the bottom of build.py: any old `INJECT_MAP['P9 Spread'] = ...` must split into `INJECT_MAP['P9 Spread · left']` and `INJECT_MAP['P9 Spread · right']` (likely both pointing at the same image).

Update the existing `same_size("P9 Spread", ...)` orphan-witness anchor in CONSTRAINTS (build.py L2542-2556): EITHER drop it (witness only — not load-bearing per RESEARCH.md "Pitfalls #8") OR rewrite to `same_size("P9 Spread · left", "P9 Spread · right", axis="w")`. Recommendation: drop it; T14 encodes proper spread-pair constraints.

Same for any pre-existing `same_size("P4 Foto-Spread", ...)` witness.

After this task, page-10 text columns (currently overlapping P9 Spread per ISSUE.md page-10 bug) STILL overlap — T13 fixes that.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 templates/zeitung-a4-grun/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun 2>&1 | tail -25 && PYTHONPATH=tools python3 -c "
import sys; sys.path.insert(0, 'tools')
from sla_lib.builder.template_loader import load_build_module
m = load_build_module('zeitung-a4-grun')
d = m.build_doc()
names = {getattr(p, 'anname', '') for p in d.iter_all_primitives() if getattr(p, 'anname', '')}
for x in ['P4 Foto-Spread · left', 'P4 Foto-Spread · right', 'P9 Spread · left', 'P9 Spread · right']:
    print(f'{x!r}: present={x in names}')
"</automated>
</verify>
<done>
- `P4 Foto-Spread · left` and `· right` annames exist in the doc.
- `P9 Spread · left` and `· right` annames exist.
- INJECT_MAP updated to reference the new annames.
- `structural_check zeitung-a4-grun` does not regress (no new errors).
- `brand:spine_safety` does NOT flag the new SpreadImage halves (anname-pattern exemption from T04).
</done>
<dont>
- Don't preserve the old single-page `P9 Spread` anname — it goes orphan in CONSTRAINTS.
- Don't add the converted spread as TWO independent ImageFrames at the same `(x=0, y=0)` on the same page — that recreates the bug. Each half goes on its OWN page (LEFT half on LEFT page, RIGHT half on RIGHT page).
- Don't change the image path — only the framing.
</dont>
</task>

<task id="T12" type="auto" tdd="false">
<name>T12: Inset spine-touching single-page frames in zeitung</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T11</depends-on>
<action>
Per ISSUE.md Phase 3 ("Inset spine-touching single-page frames"). For each frame below, set `w_mm = 207` (preserves left axis at x=0, leaves 3mm spine safety on the right edge — facing-page LEFT pages have spine on right). For the page-12 unnamed Dunkelgrün polygon (L1952-1961), set `w_mm = 207` (down from 210.80).

Frames to inset (locate by grep + verify file:line — RESEARCH.md per-template-state cites all of these):
- `P1 Hero` on page 2 (LEFT): w_mm 210 → 207. Build.py around L500 (grep `P1 Hero`).
- `P3 Hero` on page 4 (LEFT): w_mm 74.67 → 71.67. Build.py around L900 (grep `P3 Hero`).
- `P10 Portrait` on page 11 (LEFT): w_mm 66.6 → 63.6 (alignment fix in T13 may further refine this; this task does the inset only).
- `P11 Bottom` on page 12 (LEFT): w_mm 210 → 207.
- `P13 Hero` on page 14 (LEFT): w_mm 210 → 207.
- Unnamed Dunkelgrün polygon on page 12 (build.py L1952-1961): w_mm 210.80 → 207.

For each: keep `x_mm = 0`, only change `w_mm`. Keep `h_mm` and other attributes unchanged.

Workflow per frame:
1. Grep for the anname (or for the page-12 unnamed polygon, find by `fill='Dunkelgrün'` near L1952).
2. Edit only `w_mm=...`.
3. Re-run `structural_check zeitung-a4-grun` after each block of edits.

After this task `brand:spine_safety` should report 0 warnings on zeitung (modulo any new master_name issues T09 surfaced).
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 templates/zeitung-a4-grun/build.py && PYTHONPATH=tools python3 -c "
import sys; sys.path.insert(0, 'tools')
from sla_lib.builder.template_loader import load_build_module
from sla_lib.builder.brand_constraints import _SpineSafetyRule
m = load_build_module('zeitung-a4-grun')
d = m.build_doc()
r = _SpineSafetyRule(id='brand:spine_safety', name='', description='')
v = r.check(list(d.iter_all_primitives()), d)
print('spine_safety violations:', len(v))
for x in v: print(' -', x.targets, x.message[:80])
assert len(v) == 0, f'still have {len(v)} spine warnings'
" 2>&1 | tail -10</automated>
</verify>
<done>
- 6 frames re-sized per the list above.
- `_SpineSafetyRule.check()` returns zero violations on the loaded doc.
- `structural_check zeitung-a4-grun` exits 0.
</done>
<dont>
- Don't change `x_mm` — keep frames left-aligned at x=0.
- Don't change h_mm — only width matters for spine safety.
- Don't inset SpreadImage halves from T11 — they're exempted by anname-pattern.
</dont>
</task>

<task id="T13" type="auto" tdd="false">
<name>T13: Page-specific alignment fixes (page 8 portrait, page 10 text-below-spread, page 11 portrait-to-column-3)</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T12</depends-on>
<action>
Per ISSUE.md Phase 3 (3 user-confirmed bugs) + research/codebase.md §6.

1. **Page 8 (`P7 Portrait`, build.py L1368-1377):** Currently at `x=134.65`. The right-column text axis above is at `x=135.3`. Set `x_mm = 135.3` (drift from 134.65; ~0.65mm). This aligns the portrait's left edge with the column-3 text axis.
   - If T12 already touched `P7 Portrait`, re-confirm; if not, only the `x_mm` change here.

2. **Page 10 (text columns overlap P9 Spread):** After T11 the spread now lives across pages 9+10 as `P9 Spread · left` (page 10 LEFT) at `(x=0, y=0, w=210, h=126.14)`. The text columns `Kopie von u2d5c (13)` and similar (L1686+) currently start at `y=49.5` — they overlap. Move the affected text columns' `y_mm` from `49.5` → `130.14` (4mm gap below the spread's bottom edge `y=126.14`). Grep `Kopie von u2d5c (13)` and `u2da1 (16)` (and any other column on page 10's `pages[9]`) to find them.

3. **Page 11 (`P10 Portrait`, build.py L1894-1902):** Currently at `x=143.41` (8.11mm right of column-3 axis at `x=135.3`). Set `x_mm = 135.3`. This may cascade with T12's width change — if T12 set w_mm to 63.6, recompute: the portrait's right edge becomes `135.3 + 63.6 = 198.9`, well clear of spine. Confirm.

Workflow:
1. Grep `P7 Portrait`, `P10 Portrait`, `Kopie von u2d5c \(13\)`, `u2da1 \(16\)` to locate.
2. Apply edits.
3. Run `python3 templates/zeitung-a4-grun/build.py`.
4. Run `bin/audit-alignment zeitung-a4-grun --md /tmp/zeitung-audit.md` and inspect — pages 8, 10, 11 should show the now-declared adjacencies as `declared pairs` count > 0 once T14 encodes CONSTRAINTS, but for now the text columns / portraits should at least no longer flag as `axis-x drift` of 8mm or as overlapping.

After T13, `brand:undeclared_alignment_drift` warnings on Zeitung will still be many — T14 silences them by encoding the relationships.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 templates/zeitung-a4-grun/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun 2>&1 | tail -15</automated>
</verify>
<done>
- `P7 Portrait` x_mm = 135.3.
- Page-10 text columns y_mm relocated to start below `y=126.14` (after spread bottom + gap).
- `P10 Portrait` x_mm = 135.3.
- `python3 templates/zeitung-a4-grun/build.py` succeeds.
- `structural_check zeitung-a4-grun` exits 0.
</done>
<dont>
- Don't move the text columns up over P9 Spread — that recreates the original bug.
- Don't shrink P9 Spread half height to "fit" the text — the spread is the priority; text reflows below.
- Don't change `w_mm` of the portrait frames — T12 set them; T13 only adjusts `x_mm`.
</dont>
</task>

<task id="T14" type="auto" tdd="false">
<name>T14: Encode CONSTRAINTS list for zeitung</name>
<files>templates/zeitung-a4-grun/build.py</files>
<depends-on>T13, T08</depends-on>
<action>
Per ISSUE.md Phase 2 + RESEARCH.md per-template-state.

Run `bin/audit-alignment zeitung-a4-grun --md /tmp/zeitung-audit.md` and read the report. For each suspicious-undeclared adjacency the executor judges to be INTENTIONAL alignment, paste the suggested skeleton into the `CONSTRAINTS = [...]` list at build.py L2542-2556. For pairs the executor judges to be COINCIDENTAL or genuine bugs, fix the geometry (more `T13`-style edits) instead of declaring.

Replace the existing `CONSTRAINTS = [...]` list (currently 9 single-target witnesses per RESEARCH.md per-template-state) with a richer list capturing the declared adjacencies. Use these factories from `sla_lib.builder.constraints`:
- `aligned_below(below_anname, above_anname, gap_mm=..., name=...)`
- `same_x(*annames, name=...)`
- `same_y(*annames, name=...)`
- `inside(child_anname, parent_anname, name=...)`
- `distance_y(a, b, equals=..., name=...)`
- `same_size(*annames, axis=..., name=...)`
- `equal_gap(*annames, axis="x" or "y", gap_mm=..., name=...)`

Cover Page 1 (per ISSUE.md Phase 2 example):
```python
distance_y("Cover Hero", "u2950", equals=0.0, tolerance_mm=0.5,
           name="cover_top_to_green_bottom_flush"),
same_size("Cover Hero", "u2950", axis="w", tolerance_mm=0.5,
          name="cover_top_bottom_share_width"),
```
(After T10 trim, u2950's rotated-bbox-w should now match Cover Hero's w_mm=210; verify in audit report.)

Page 8 (per T13 edits):
```python
same_x("P7 Portrait", "<column-3 text frame anname above>",
       name="p8_portrait_col3_axis"),
inside("P7 Portrait", "u918", name="p8_portrait_inside_green_band"),
```

Page 10:
```python
aligned_below("Kopie von u2d5c (13)", "P9 Spread · left", gap_mm=4.0,
              name="p10_text_below_spread_left"),
aligned_below("u2da1 (16)", "P9 Spread · left", gap_mm=4.0,
              name="p10_text2_below_spread"),
```

Page 11:
```python
same_x("P10 Portrait", "<column-3 text frame above on p11>",
       name="p11_portrait_col3_axis"),
aligned_below("P10 Portrait", "<text frame anname above>", gap_mm=11.6,
              name="p11_portrait_below_text"),
```

Encode all other declared adjacencies the audit surfaces (column grids → `equal_gap`; same-row text frames → `same_y`; etc.). Iterate: paste a constraint, re-run `bin/audit-alignment zeitung-a4-grun --md ...`, the suspicious count drops; repeat until report is clean.

For ColumnTextStory chains (P-7), encode ONE `equal_gap("col1", "col2", "col3", axis="x", gap_mm=...)` per page rather than three pairwise `same_x` constraints — the pair-extraction expands C(3,2)=3 declared pairs from a single 3-target equal_gap.

End-state criterion: `bin/audit-alignment zeitung-a4-grun` reports zero suspicious-undeclared adjacencies. `structural_check zeitung-a4-grun` reports zero `brand:undeclared_alignment_drift` warnings, zero `brand:spine_safety` warnings, zero `brand:inside_page` errors.

This is the largest single task. Split into multiple commits if helpful (one per page is reasonable: 14 commits → too many; one per "all relationships on page N pasted" is fine — group 2-3 pages per commit). Each interim commit must keep `structural_check` green.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 templates/zeitung-a4-grun/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check zeitung-a4-grun 2>&1 | tail -25 && bin/audit-alignment zeitung-a4-grun 2>&1 | grep -c "suspicious-undeclared adjacencies" || echo "zero suspicious sections"</automated>
</verify>
<done>
- `templates/zeitung-a4-grun/build.py::CONSTRAINTS` is a list with 10+ entries (one per declared relationship).
- `structural_check zeitung-a4-grun`: zero `brand:undeclared_alignment_drift` warnings, zero `brand:spine_safety` warnings, zero `inside_page` errors.
- `bin/audit-alignment zeitung-a4-grun --md` reports zero suspicious-undeclared adjacencies.
- All CONSTRAINTS entries reference EXISTING annames (no missing-anname warnings).
</done>
<dont>
- Don't paste skeletons blindly — each constraint encodes a real authoring intent. If the audit suggests `same_x("A", "B")` and the alignment is actually coincidental, FIX the geometry by changing one frame's x_mm so the drift exceeds 5mm, rather than declaring.
- Don't keep the orphan single-target `same_size("X")` witness anchors from the previous CONSTRAINTS — they served only as anname-rename canaries; the new declared-pair entries are richer.
- Don't add CONSTRAINTS that reference pre-T11 annames (`P9 Spread`, `P4 Foto-Spread` without ` · left`/`· right` suffix) — they're orphan after T11.
</dont>
</task>

<task id="T15" type="auto" tdd="false">
<name>T15: Regenerate template.sla + gallery via bin/render-gallery --skip-visual-diff</name>
<files>templates/zeitung-a4-grun/template.sla, templates/zeitung-a4-grun/template-preview.sla, templates/zeitung-a4-grun/preview.pdf, templates/zeitung-a4-grun/page-*.png, templates/zeitung-a4-grun/meta.yml (previews_for_sla SHA), site/public/templates/zeitung-a4-grun/* (mirrors)</files>
<depends-on>T14</depends-on>
<action>
Run:
```
bin/render-gallery zeitung-a4-grun --skip-visual-diff
```
This:
1. Re-emits `template.sla` and `template-preview.sla` via `python3 templates/zeitung-a4-grun/build.py`.
2. Renders `preview.pdf` via Scribus headless (xvfb-run).
3. Rasterizes 14 `page-NN.png` files via pdftoppm.
4. Updates `meta.yml::previews_for_sla` SHA to match the new template.sla.
5. Mirrors all artifacts to `site/public/templates/zeitung-a4-grun/`.

After:
1. Check `git status -s | grep zeitung-a4-grun` — expect ~30 files dirty (14 PNGs in template dir + 14 PNGs in site/public mirror + template.sla + preview.pdf + meta.yml SHA).
2. `pdfimages -list templates/zeitung-a4-grun/preview.pdf` — verify NO image object appears on more than one page (acceptance criterion). One-liner check:
   ```
   pdfimages -list templates/zeitung-a4-grun/preview.pdf \
     | awk 'NR>2 {print $2}' | sort | uniq -c \
     | awk '$1 > 1 {print "WARN: image obj appears on " $1 " pages"}'
   ```
   Should print nothing. (Note: column index for `num` may differ across poppler versions; verify with `pdfimages -list --help` first.)
3. `bin/check-stale-previews` exits 0.

Commit all dirty files in ONE commit: `22: chore(zeitung): regen template.sla + gallery after alignment encoding`.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && bin/render-gallery zeitung-a4-grun --skip-visual-diff 2>&1 | tail -10 && bin/check-stale-previews 2>&1 | tail -5 && pdfimages -list templates/zeitung-a4-grun/preview.pdf | awk 'NR>2 {print $2}' | sort | uniq -c | awk '$1 > 1 {print "FAIL: image obj on " $1 " pages"}' | tee /tmp/spine-leak.txt; test ! -s /tmp/spine-leak.txt && echo "PASS: no cross-spread image leakage"</automated>
</verify>
<done>
- `bin/render-gallery zeitung-a4-grun --skip-visual-diff` exits 0.
- `bin/check-stale-previews` exits 0.
- `pdfimages -list templates/zeitung-a4-grun/preview.pdf` shows each image object on exactly ONE page (zero cross-spread leakage). Capture verbatim output for EXECUTION.md.
- Roughly 30 files dirty under `templates/zeitung-a4-grun/` and `site/public/templates/zeitung-a4-grun/`.
</done>
<dont>
- Don't omit `--skip-visual-diff` — visual_diff requires baseline PNGs the worktree doesn't have.
- Don't manually edit any of the regen artifacts — the build pipeline owns them.
- Don't skip the pdfimages check — it's an acceptance criterion.
</dont>
</task>

<task id="T16" type="auto" tdd="false">
<name>T16: Remove brand:inside_page override + update tests + close GH #39 at PR-merge</name>
<files>templates/zeitung-a4-grun/meta.yml, tools/sla_lib/tests/test_zeitung_overflow.py, tools/sla_lib/tests/test_sla_to_dsl.py</files>
<depends-on>T15</depends-on>
<action>
Locked decision #13 + ISSUE.md "Superseded follow-ups" + RESEARCH.md "Pitfalls #16" (sequencing).

1. **Remove the `brand:inside_page` override** from `templates/zeitung-a4-grun/meta.yml` L39-47. Keep `brand:line_spacing_0.9` (unrelated). After edit, `meta.yml::brand_overrides` contains only the `brand:line_spacing_0.9` entry.

2. **Update `tools/sla_lib/tests/test_zeitung_overflow.py`**:
   - Rename `test_inside_page_finds_only_u2950_without_override` → `test_inside_page_zero_errors_after_u2950_trim`.
   - Body assertion: `self.assertEqual(len(errors), 0)` (was `1`). Update docstring to reflect that #39 is closed and u2950 was trimmed in #22.
   - Update `test_inside_page_passes_with_override` → rename to `test_inside_page_passes_after_override_removed`. Body: assert no `brand:inside_page` errors AND assert `'brand:inside_page'` is NOT in `report.skipped_brand_rules` (override was removed).
   - Add a new test: `test_spine_safety_zero_warnings_on_zeitung` — load doc, run `_SpineSafetyRule`, assert zero violations.
   - Add a new test: `test_undeclared_drift_zero_warnings_on_zeitung` — load doc, run `_UndeclaredDriftRule` with `constraints=mod.CONSTRAINTS`, assert zero violations.

3. **Update `tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip` allow-list** (if it exists; grep for it). The new diverging frames from T09-T13 (master_name flips, u2950 trim, P4/P9 → SpreadImage, inset frames, page-8/10/11 alignment fixes) need to be added to the round-trip-divergence allow-list. If the test gates on `meta.yml::sla_diff_strict: false` it may not need allow-list changes — read first; expand only if specific frames show up as test failures.

4. **Close GH #39 at PR merge time** — add the closing reference to the PR body or a commit footer. Workflow:
   - In the commit message for this task, add: `Closes #39 — superseded by #22 Phase 3 (u2950 trim + override removal).`
   - The execute-stage can close #39 via `gh issue close 39 --reason "not planned" --comment "Superseded by #22 — u2950 polygon was trimmed and the brand:inside_page override removed in this PR."` after the PR merges. This step is documented in EXECUTION.md follow-ups, not auto-run mid-PR.

Run full tests after edits.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -m unittest tools.sla_lib.tests.test_zeitung_overflow -v 2>&1 | tail -15 && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all 2>&1 | tail -10</automated>
</verify>
<done>
- `meta.yml::brand_overrides[brand:inside_page]` removed; only `brand:line_spacing_0.9` remains.
- `test_zeitung_overflow.py` updated with renamed + new assertions, all pass.
- `test_sla_to_dsl.py::ZeitungRoundTrip` (if affected) updated and passing.
- `structural_check --all` exits 0 with zero `brand:inside_page` errors on zeitung WITHOUT the override.
- Commit message references "Closes #39".
</done>
<dont>
- Don't run T16 before T10/T15 — removing the override before u2950 is trimmed AND the gallery regen lands sends `structural_check --all` red.
- Don't close #39 via `gh` mid-PR — wait until after merge (atomic-PR principle; execution log records the action).
- Don't remove the `brand:line_spacing_0.9` override — out of scope; that's typography drift, separate concern.
</dont>
</task>

<task id="T17" type="auto" tdd="false">
<name>T17: Add bin/audit-alignment as informational CI step in pages.yml</name>
<files>.github/workflows/pages.yml</files>
<depends-on>T08</depends-on>
<action>
Locked decision #10. After the existing `Run structural check (Issue #12)` step at L149-155 in `.github/workflows/pages.yml`, add a new step:

```yaml
      - name: Run alignment audit (Issue #22, informational)
        run: |
          set -euo pipefail
          mkdir -p build/audit
          PYTHONPATH=tools python3 tools/audit_alignment.py --all \
            --output-dir build/audit/ || true
          # `|| true` keeps audit informational; promotion to fatal deferred
          # per Issue #22 locked decision #10 (RESEARCH.md L34).

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: audit-alignment-report
          path: build/audit/
```

The `|| true` is load-bearing — without it, any heuristic warning fails CI. Promotion to fatal is a follow-up issue once enough templates are clean.

Position the step BEFORE `actions/upload-pages-artifact@v3` (L157) so the audit runs in the build-validation lane.

Verify YAML syntax via `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml').read())"`.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && python3 -c "import yaml; data = yaml.safe_load(open('.github/workflows/pages.yml').read()); print('YAML OK; jobs:', list(data['jobs'].keys()))" && grep -n "audit_alignment\|audit-alignment" .github/workflows/pages.yml<verify>
<automated>python3 -c "import yaml; data = yaml.safe_load(open('.github/workflows/pages.yml').read()); print('YAML OK; jobs:', list(data['jobs'].keys()))" && grep -n "audit_alignment\|audit-alignment" .github/workflows/pages.yml</automated>
</verify>
<done>
- New step "Run alignment audit (Issue #22, informational)" exists in pages.yml after the structural-check step.
- Step uses `|| true` to stay non-fatal.
- New `actions/upload-artifact@v4` step uploads `build/audit/` as `audit-alignment-report`.
- YAML parses cleanly.
</done>
<dont>
- Don't omit `|| true` — promotion to fatal is locked-deferred (decision #10).
- Don't move the upload-pages-artifact step — only insert before it.
- Don't run the audit step BEFORE structural_check — structural_check is the gate; audit is supplementary.
</dont>
</task>

<task id="T18" type="auto" tdd="false">
<name>T18: Update SCHEMA.md + SPEC-WRITING-GUIDE.md docs (rule count 9 → 11 + audit-tool reference)</name>
<files>templates/_specs/SCHEMA.md, shared/brand/SPEC-WRITING-GUIDE.md</files>
<depends-on>T05, T08</depends-on>
<action>
Two doc updates.

1. **`templates/_specs/SCHEMA.md` §12 brand catalogue** (grep for "brand:inside_page" or "BRAND_CONSTRAINTS" to find the catalogue section):
   - Bump any "9 rules" / "nine BrandRules" mentions to "11 rules".
   - Add catalogue entries for the new rules:
     ```markdown
     ### `brand:spine_safety` (warning)
     Spine-safety on facing-pages docs. A non-SpreadImage frame on a LEFT page
     whose right edge is within 3mm of the spine (or RIGHT-page left edge
     within 3mm of x=0) emits a warning — Scribus extends the bleed across
     the spine into the facing page. SpreadImage halves (anname matching
     ` · (left|right)$`) are exempt. Rule no-ops on `facing_pages=False`
     docs.

     ### `brand:undeclared_alignment_drift` (warning)
     Heuristic detector for pairs of frames that appear visually
     aligned/adjacent but are not declared in the template's
     `CONSTRAINTS = […]` list. Defaults: 0.5mm < axis drift < 5mm or
     0.5mm < adjacency gap < 12mm. Skips rotated frames, anonymous
     frames, master pages, and pairs declared via any constraint factory.
     Per-template opt-out via `meta.yml::brand_overrides[brand:undeclared_alignment_drift]`.
     ```

2. **`shared/brand/SPEC-WRITING-GUIDE.md`** — add a section near the existing brand-rule catalogue:
   ```markdown
   ## Auditing alignment

   `tools/audit_alignment.py` (run via `bin/audit-alignment <slug>`) emits
   a per-template Markdown report listing:
   - Page-by-page primitive inventory (count + side detection).
   - Suspicious-undeclared adjacencies with ready-to-paste constraint
     skeletons (e.g. `same_x("A", "B", name="p1_x")`).
   - Spine-safety candidates (frames within 3mm of the spine on
     facing-page docs).

   Workflow for encoding a template's CONSTRAINTS:
   1. Run `bin/audit-alignment <slug> --md report.md`.
   2. For each suspicious pair the audit surfaces, decide: declare
      (paste the suggested skeleton into `CONSTRAINTS = [...]`) or fix
      geometry (the alignment is unintended).
   3. Re-run; iterate until report is clean.

   `bin/audit-alignment --all` runs across all templates. CI runs this
   informationally (artifact uploaded; never fails the build). Promotion
   to fatal is deferred until all production templates are encoded.
   ```

3. Bump any "9 BrandRules" / "9 brand rules" references throughout the
   guide to "11".

Use grep to find all references: `grep -rn "9 rules\|9 BrandRules\|nine rules\|brand:inside_page" templates/_specs/SCHEMA.md shared/brand/SPEC-WRITING-GUIDE.md`.
</action>
<verify>
<automated>cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply- && grep -c "brand:spine_safety" templates/_specs/SCHEMA.md shared/brand/SPEC-WRITING-GUIDE.md && grep -c "brand:undeclared_alignment_drift" templates/_specs/SCHEMA.md shared/brand/SPEC-WRITING-GUIDE.md && grep -c "audit_alignment\|audit-alignment" shared/brand/SPEC-WRITING-GUIDE.md</automated>
</verify>
<done>
- `templates/_specs/SCHEMA.md` §12 lists `brand:spine_safety` and `brand:undeclared_alignment_drift` with descriptions.
- `shared/brand/SPEC-WRITING-GUIDE.md` documents `tools/audit_alignment.py` workflow + the two new rules.
- All "9 rules" / "nine rules" references bumped to "11".
- Both docs grep-match the new rule ids ≥ 1 each.
</done>
<dont>
- Don't add an `audit_strict` field reference — locked decision #8 defers it.
- Don't add `audit_tolerances` schema docs — locked decision #11 defers it.
- Don't promise "CI fails on drift warnings" — locked decision #10 keeps it informational day-1.
</dont>
</task>

</tasks>

<verification>
After all tasks complete, run final checks:

1. **Full test suite:**
   ```
   cd /root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply-
   python3 -m unittest discover tools/sla_lib/tests
   ```
   Must exit 0.

2. **Structural check across all templates:**
   ```
   PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
   ```
   Must exit 0. Zeitung: zero `brand:inside_page` errors, zero `brand:spine_safety` warnings, zero `brand:undeclared_alignment_drift` warnings. 7 other templates: `brand:undeclared_alignment_drift` listed under skipped (override).

3. **Audit tool clean on Zeitung:**
   ```
   bin/audit-alignment zeitung-a4-grun
   ```
   Report shows zero "suspicious-undeclared adjacencies" sections.

4. **Audit tool runs across all templates:**
   ```
   bin/audit-alignment --all --output-dir build/audit/
   ls build/audit/
   ```
   Eight `<slug>.md` files produced.

5. **Stale-previews gate:**
   ```
   bin/check-stale-previews
   ```
   Must exit 0.

6. **PDF cross-spread leakage:**
   ```
   pdfimages -list templates/zeitung-a4-grun/preview.pdf \
     | awk 'NR>2 {print $2}' | sort | uniq -c \
     | awk '$1 > 1 {print "FAIL: image obj appears on " $1 " pages"}'
   ```
   Must print nothing (zero cross-spread image leakage). Capture verbatim into EXECUTION.md.

7. **YAML lint of pages.yml:**
   ```
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml').read())"
   ```

8. **Git status sanity:**
   ```
   git status -s
   ```
   Expected: ~30 files dirty under `templates/zeitung-a4-grun/` and `site/public/templates/zeitung-a4-grun/` (regen artifacts), plus the source-code edits across `tools/sla_lib/builder/`, `tools/audit_alignment.py`, `tools/sla_lib/tests/`, 8 `meta.yml` files (zeitung override removal + 7 override additions), `.github/workflows/pages.yml`, `templates/_specs/SCHEMA.md`, `shared/brand/SPEC-WRITING-GUIDE.md`.

9. **Optional manual checkpoint** (out of executor scope; PR reviewer): visual inspection of `templates/zeitung-a4-grun/page-{1,8,10,11,12}.png` to confirm the user-reported bugs are gone.
</verification>

<success_criteria>
Mapping to ISSUE.md acceptance criteria (final list, post-Phase 8):

- [x] **`brand:spine_safety` and `brand:undeclared_alignment_drift` exist as new BrandRules with full test coverage.** → T04 + T05 + T06.
- [x] **`tools/audit_alignment.py` exists, has CLI + library API, has tests.** → T08.
- [x] **`--all` reports zero errors and zero warnings on `templates/zeitung-a4-grun`** (postkarte + plakat narrowed per locked decision #12 — they get the new rules + overrides; per-template encoding deferred to follow-up). → T07 + T14 + T17.
- [x] **`pdfimages -list templates/zeitung-a4-grun/preview.pdf` shows each image on exactly ONE page (no cross-spread sharing).** → T11 (SpreadImage migration) + T12 (inset) + T15 (regen) + verification step #6.
- [x] **Per-template `CONSTRAINTS = [...]` list is present for Zeitung, capturing all detected adjacencies** (postkarte + plakat narrowed per locked decision #12). → T14.
- [x] **`bin/audit-alignment` produces clean report for Zeitung** (postkarte + plakat overridden, not encoded). → T08 + T14.
- [x] **All tests pass: `python3 -m unittest discover tools/sla_lib/tests`.** → verification step #1.
- [x] **CI green; gallery regenerated; `previews_for_sla` SHAs bumped.** → T15 + T17.
- [ ] **User-reported pages 1, 8, 10, 11, 12 of Zeitung visually inspected by a human reviewer in the PR.** → out of executor scope; verification step #9 notes.
- [x] **SCHEMA.md §12 + SPEC-WRITING-GUIDE.md updated with the two new rules + audit-tool reference + worked migration recipe.** → T18.
- [x] **Brief §10 Session-History row added.** → handled by execute-stage's EXECUTION.md update (out of plan scope).

Locked-decision conformance self-check:
- D1, D2 (rules in `brand_constraints.py` as BrandRule) → T04, T05.
- D3 (constraints kwarg signature, Option B) → T03.
- D4 (master_name regex, facing_pages early-exit, unknown-side per-page warning) → T04.
- D5 (SpreadImage halves exempt via anname-pattern) → T04 (regex `SPREAD_HALF_RX`).
- D6 (audit CLI mirrors spec_check, reuses load_build_module) → T08.
- D7 (refactor bbox + template_loader) → T01, T02.
- D8 (warning severity for undeclared_drift; audit_strict deferred) → T05 + T18.
- D9 (pre-applied overrides for 7 templates) → T07.
- D10 (CI informational with || true) → T17.
- D11 (audit_tolerances deferred) → T18 dont-list.
- D12 (Phase 7 narrowed: only Zeitung encoded) → T07 + T14.
- D13 (close GH #39 at PR-merge) → T16.

Critical-finding self-check:
- Rule count 9 → 11 (not 9 → 10) → T06.
- 6 wrong master_name assignments fixed BEFORE running spine-safety → T09 (precedes T10–T17 audit/encoding).
- Atomic-PR ordering rules → overrides → trim → remove override → close #39 → T04+T05 (rules) → T07 (overrides) → T10 (trim) → T16 (remove override + close).
- `Page.is_left` not trusted → T04 dont-list + T04 implementation uses regex.
- New rules use `_frame_bbox_mm` (`bbox.frame_bbox_mm` after T01) → T04 + T05 + T08.
</success_criteria>

<risks_and_verification>

## Risks and verification checkpoints

**Atomic-PR ordering** (load-bearing, P-12 + P-16):
- T04+T05 add rules to BRAND_CONSTRAINTS BEFORE T07 adds overrides. If reversed, `meta_schema._validate_and_collect_ids` warns "id not in BRAND_CONSTRAINTS" for every load.
- T09 (master_name fix) BEFORE T10/T11/T12/T13 (geometry edits) — spine-safety needs correct sides before any inset is meaningful.
- T10 (u2950 trim) BEFORE T16 (override removal). Verified by T10's in-process check that returns 0 errors WITHOUT the override.
- T11 (SpreadImage migration) BEFORE T14 (CONSTRAINTS) — CONSTRAINTS references the new `· left`/`· right` annames.
- T15 (regen) BEFORE T16 (remove override). The regen produces the artifact tree that the test relies on.
- Close #39 ONLY after PR merge (T16's gh-close note). Mid-PR, a stale #39 is fine — the rule + override removal is the actual fix.

**Heuristic-threshold tunability** (P-3, P-15):
- The audit tool's `--axis-tol-mm` and `--adjacency-tol-mm` flags let the executor tune per-call if T14 surfaces too many false-positives. Default 5mm/12mm matches ISSUE.md verbatim. If the audit emits >50 suspicious pairs on Zeitung after T13, narrow `--axis-tol-mm` to 3mm or `--adjacency-tol-mm` to 8mm before pasting skeletons; document the tuning in EXECUTION.md.
- `meta.yml::audit_tolerances` schema extension is locked-deferred (D11); per-template tuning happens via CLI flags only in this PR.

**u2950 trim cascade** (P-16):
- Trimming u2950 may surface new Page-1 alignment issues now visible because `inside_page` no longer suppresses the cover. T14 encodes these in CONSTRAINTS as the audit surfaces them. Specifically: the `same_size("Cover Hero", "u2950", axis="w")` and `distance_y("Cover Hero", "u2950", equals=0.0)` constraints from ISSUE.md Phase 2 are RED before T10 trim (u2950's bbox-w was 220.49 ≠ Cover Hero's 210), GREEN after.

**`bin/render-gallery` artifact volume** (P-15 + research/codebase.md §7):
- T15 dirties ~30 files (14 page-NN.png + mirrors + template.sla + preview.pdf + meta.yml SHA). Verify with `git status -s | wc -l` after T15 — expect >25. ALL must be staged for the regen commit.
- The mirror to `site/public/templates/zeitung-a4-grun/` happens automatically via `_mirror_to_site_public`. Don't hand-copy.

**Test count drift** (P-11):
- T06 bumps `test_nine_rules_exact` → `test_eleven_rules_exact`. If a future rule lands AFTER #22 merges, that test must bump again. Acceptable — explicit count is the canary.

**SpreadImage exemption brittleness** (P-19):
- T04's regex `r" · (left|right)$"` exempts SpreadImage halves. If a future template uses anname suffix like `" · footer"`, the regex won't false-match (only "left"/"right"). If a SpreadImage author uses a non-SpreadImage block but copies the naming convention, the rule will erroneously skip those frames — document this in T04's implementation comment ("SpreadImage halves are identified by anname suffix; do not reuse this suffix for non-spread frames").

**`Page.is_left` is broken** (P-2 — recurring blind spot):
- ALL position-detection logic in T04, T05, T08 uses `master_name` regex. Anyone reading the new rules might be tempted to "fix" them to use `page.is_left` — the dont-lists in T04, T05 explicitly forbid this. Pitfall is verified at document.py L391-393 (hardcoded False).

**Atomicity of T14** (largest single task):
- T14 may take multiple commits (one per page or per logical group). Each interim commit must keep `structural_check zeitung-a4-grun` green — DO NOT push any commit that adds CONSTRAINTS referencing missing annames (orphan warnings break the trust the audit-iteration loop needs).

**CI step ordering in pages.yml** (T17):
- The new audit step runs AFTER `structural_check --all`. If structural-check fails (which it shouldn't post-#22), the audit step is skipped via `set -euo pipefail` in the prior step's `run:` (separate steps are isolated, so actually the audit runs anyway). The `|| true` is what makes the audit informational — keep it.

**Token-budget partial-completion fallback** (P-15):
- If the executor runs out of usage before T14, the work landed up to T13 is still useful: rules + audit tool + V1 overrides + zeitung master/u2950/spread fixes are all green, only the CONSTRAINTS encoding is incomplete. The remaining work splits cleanly into a follow-up PR.

</risks_and_verification>
