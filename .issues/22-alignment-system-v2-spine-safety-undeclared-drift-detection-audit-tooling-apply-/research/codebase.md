# Codebase Research — Issue #22 (alignment system v2)

**Scope:** map every existing surface this issue must extend or reuse:
the `BrandRule` registry, the `Constraint` factory list and its
`referenced_annames()` plumbing, the `iter_all_primitives` orchestrator,
`Document.facing_pages` + `Page.master_name` (spine side detection),
the per-template state of the three stable templates, the `_load_build_module`
loader the audit tool will reuse, the `bin/render-gallery` regen flow,
and the existing test/CI surface.

**Worktree audited:** `/root/workspace/.worktrees/22-alignment-system-v2-spine-safety-undeclared-drift-detection-audit-tooling-apply-`. All file:line references are anchored to that tree (HEAD = current branch).

**No `tools/audit_alignment.py` or `bin/audit-alignment` exists today** — both are net-new files this issue lands. Confirmed via `ls` (Bash, missing-file error). HIGH confidence.

---

## 1. Interface inventory (`<interfaces>` blocks)

The planner can write Phase 4/4b/8 tasks directly off these signatures — the executor will not need to re-read `brand_constraints.py` or `constraints.py` to add the two new rules and the audit tool.

```text
<interfaces>
// From tools/sla_lib/builder/brand_constraints.py — BrandRule registry surface

# Base class (line 57-73). Frozen dataclass; subclasses override check().
@dataclass(frozen=True)
class BrandRule:
    id: str           # canonical rule id, e.g. "brand:spine_safety"
    name: str         # short human label
    description: str  # one-line description, used in markdown reports
    severity: str = "error"   # default; rules can emit per-violation severity
    def check(self, primitives: list, doc) -> list[Violation]: ...

# Registry (line 505-562). Module-level list; structural_check.py iterates it.
BRAND_CONSTRAINTS: list[BrandRule] = [ ... 9 rules today ... ]

# Bbox helpers shared with the new rules — already used by _InsidePageRule.
def _rotated_bbox(x: float, y: float, w: float, h: float, deg: float) \
    -> tuple[float, float, float, float]                              # line 371
def _frame_bbox_mm(item, page) \
    -> Optional[tuple[float, float, float, float]]                    # line 393
    # Returns page-local (x0, y0, x1, y1) in mm, honouring anchor + rotation.
    # Returns None for non-spatial primitives (Run, ParaStyle).
    # Limitation (line 397-405): verbatim-pt overrides (xpos_pt/width_pt etc.)
    # are NOT honored — falls back to *_mm. Today the two zeitung offenders
    # use *_mm directly so it's safe; widen if a future template trips this.

# Existing rule subclass shape — pattern for the two new rules:
@dataclass(frozen=True)
class _InsidePageRule(BrandRule):                                      # line 424
    tolerance_mm: float = 0.5
    error_cutoff_mm: float = 1.0
    def check(self, primitives: list, doc) -> list[Violation]:
        # IGNORES the flat `primitives` arg (line 459). Walks
        # `for page in doc.pages: if page.is_master: continue;
        #  for item in page.items: ... _frame_bbox_mm(item, page) ...`.
        # Pattern matches _Bleed3mmRule. New rules follow this shape.

# Violation (from constraints.py, line 35-48):
@dataclass(frozen=True)
class Violation:
    severity: str                 # "error" | "warning" | "info"
    message: str
    rule_id: str = ""
    targets: tuple = ()           # tuple of anname strings
```

```text
<interfaces>
// From tools/sla_lib/builder/constraints.py — declared-pair plumbing

@dataclass(frozen=True)
class Constraint:                                                     # line 51
    id: str                       # e.g. "same_x:p11_portrait_col3_axis"
    targets: tuple                # tuple of anname strings (already _norm'd)
    name: str = ""
    def check(self, primitives_by_anname: dict) -> list[Violation]: ...
    def referenced_annames(self) -> tuple:                            # line 67
        return self.targets       # default: every Constraint subclass
                                  # uses targets verbatim today.

# Concrete subclasses + factories (line 114-519).
# Each factory normalizes targets via _norm() (line 389) -> tuple of anname
# strings; the constraint stores the normalized tuple in `targets`, so
# `referenced_annames()` returns annames directly. CRITICAL: this is the
# pair-set source for the undeclared-drift rule.

# 11 factories live in constraints.py:
def same_y(*targets, tolerance_mm=0.5, name="") -> _SameAxisConstraint  # line 399
def same_x(*targets, tolerance_mm=0.5, name="") -> _SameAxisConstraint  # line 408
def same_size(*targets, axis="both", tolerance_mm=0.5, name="") -> _SameSizeConstraint  # 417
def mirrored_x(left, right, axis_mm, tolerance_mm=0.5, name="") -> _MirroredConstraint  # 433
def mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="") -> _MirroredConstraint  # 443
def inside(child, parent, tolerance_mm=0.5, name="") -> _InsideConstraint               # 453
def equal_gap(*targets, axis="y", gap_mm, tolerance_mm=0.5, name="") -> _EqualGapConstraint  # 462
def hierarchy(*targets, by="fontsize", name="") -> _HierarchyConstraint                 # 472
def same_style(*targets, name="") -> _SameStyleConstraint                               # 481
def distance_y(a, b, equals, tolerance_mm=0.5, name="") -> _DistanceConstraint          # 489
def distance_x(a, b, equals, tolerance_mm=0.5, name="") -> _DistanceConstraint          # 498
def aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="") -> _AlignedBelowConstraint  # 507
```

```text
<interfaces>
// From tools/sla_lib/builder/document.py — facing-pages + master-side surface

class Document:                                                       # line 140
    facing_pages: bool = False    # ctor kwarg; line 167
    pages: list[Page]
    masters: list[Page]
    def iter_all_primitives(self) -> Iterable:                        # line 413
        # Yields every primitive across master pages and doc pages, in
        # stable order: masters first, then pages; per-page items in
        # page.items order. NO (page, item) pairing — rules that need
        # the page do their own `for page in doc.pages` walk
        # (see _InsidePageRule, _Bleed3mmRule).

@dataclass
class Page:                                                           # line 106
    width_pt: float
    height_pt: float
    bleed_mm: float = 3.0
    master_name: str = ""         # MNAM — the master that PROVIDES this
                                  # page's grid. CRITICAL for spine-safety:
                                  # zeitung uses 'Neue Musterseite rechts'
                                  # / 'Neue Musterseite links' — substring
                                  # match for "links"/"rechts" decides side.
                                  # Empty string means master = "Normal".
    label: str = ""               # human-readable, rendered as Hilfslinien
    items: list                   # page-bound primitives (Frame, Polygon,
                                  # ImageFrame). Blocks were expanded at
                                  # add() time so this list is flat.
    own_page: int = 0             # set at save time
    is_left: bool = False         # informational only; per build/document.py
                                  # line 386-396, every doc page in zeitung
                                  # gets is_left=False (Scribus convention);
                                  # spine-safety MUST NOT trust this bit,
                                  # MUST use master_name substring.
    is_master: bool = False       # True for Page returned by add_master(),
                                  # False for add_page(). Skip masters
                                  # (matches _InsidePageRule line 463).
    master_id: str = ""           # NAM, set on the MASTERPAGE itself.

# Master vs doc page distinction:
# - doc.masters: list[Page]  — Page entries with is_master=True, master_id="<NAM>"
# - doc.pages:   list[Page]  — Page entries with is_master=False, master_name="<MNAM>"
# - iter_all_primitives() concatenates masters first, then pages.
```

```text
<interfaces>
// From tools/sla_lib/builder/primitives.py — frame geometry surface

@dataclass
class _Frame:                                                         # line 433
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 50
    h_mm: float = 30
    anchor: Optional[Anchor] = None     # if set, x_mm/y_mm are stale
    rotation_deg: float = 0
    layer: int = 2
    anname: str = ""                    # KEY for declared-pair lookup;
                                        # primitives without anname must
                                        # be SKIPPED in undeclared-drift
                                        # (no way to declare them).
    custom_path: Optional[str] = None
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    xpos_pt: Optional[float] = None     # verbatim-pt override
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None

@dataclass
class TextFrame(_Frame): ...            # line 540 — adds text/runs/style/fcolor/etc.
@dataclass
class ImageFrame(_Frame):               # line 765 — image + scale_type + local_*
    scale_type: int = 1                 # 0=free, 1=auto-fit (SpreadImage uses 0)
    local_offset_mm: tuple = (0, 0)     # SpreadImage right half = (-page_w, 0)
    local_scale: tuple = (1, 1)
    local_rotation_deg: float = 0.0
    fill: Optional[str] = None
@dataclass
class Polygon(_Frame):                  # line 848
    fill: str = "Black"                 # PCOLOR — green-poly detection
    fill_shade: int = 100

# anchor handling: _Frame._xy_pt() at line 470. _frame_bbox_mm in
# brand_constraints.py mirrors it for anchor+rotation-aware bbox.
```

```text
<interfaces>
// From tools/sla_lib/builder/structural_check.py — orchestrator the audit reuses

def _load_build_module(slug: str, root: Path = _REPO_ROOT) -> module  # line 104
    # Imports templates/<slug>/build.py via importlib, with sys.modules
    # pop to avoid cross-contamination on --all iteration. The audit tool
    # MUST reuse this — do not re-implement.

def check_template(slug: str, root: Path = _REPO_ROOT) -> TemplateReport  # line 137
    # Loads build.py, calls build_doc(), iterates CONSTRAINTS + BRAND_CONSTRAINTS.
    # Mirror its shape; the audit tool emits a different report type but
    # the same load → build_doc → primitives_by_anname pipeline.

def discover_template_slugs(root: Path = _REPO_ROOT) -> list[str]     # line 232
    # Sorted directory walk under templates/, excluding _specs and _smoke,
    # requiring build.py. Reuse for --all.

@dataclass
class CheckIssue:                                                     # line 45
    severity: str           # "error" | "warning" | "info" | "pass" | "skip"
    rule_id: str
    message: str
    location: str = ""

# CLI shape (line 272+):  python3 -m sla_lib.builder.structural_check
#   <slug>      OR  --all
#   --json
#   --root <path>
# Exit code 1 if any error-severity issue surfaces; warnings never fail CI.

# Constraint evaluation pattern at line 162-183:
constraint_list = getattr(mod, "CONSTRAINTS", []) or []
for c in constraint_list:
    ref = set(c.referenced_annames())          # <-- declared-pair source
    present = set(primitives_by_anname)
    missing = ref - present
    if missing: ... emit warning ...; continue
    violations = c.check(primitives_by_anname)
    ...
```

```text
<interfaces>
// From tools/sla_lib/builder/meta_schema.py — per-template overrides surface

def load_brand_overrides(slug: str, root: Path | None = None) -> set[str]  # line 52
    # Reads templates/<slug>/meta.yml, returns set of brand-rule IDs to skip.
    # Validates {id, reason} JSON-schema shape (line 23-40); warns on unknown
    # ids (line 113-120).

def load_sla_diff_strict(slug: str, root: Path | None = None) -> bool  # line 74
    # Reads top-level sla_diff_strict (default True). Used by render_pipeline.
```

---

## 2. Mapping every factory to its declared pair-set (algorithm for undeclared-drift)

`Constraint.referenced_annames()` returns `self.targets` — a tuple of `anname` strings already normalized via `_norm()`. The 11 factories produce these target tuples:

| Factory | Target arity | `referenced_annames()` returns | Pair-set expansion |
|---|---|---|---|
| `same_x(*targets)` | N≥2 | `(a, b, c, …)` | all C(N,2) unordered pairs |
| `same_y(*targets)` | N≥2 | `(a, b, c, …)` | all C(N,2) unordered pairs |
| `same_size(*targets)` | N≥2 | `(a, b, c, …)` | all C(N,2) unordered pairs |
| `same_style(*targets)` | N≥2 | `(a, b, c, …)` | all C(N,2) unordered pairs |
| `equal_gap(*targets)` | N≥2 | `(a, b, c, …)` | all C(N,2) unordered pairs |
| `hierarchy(*targets)` | N≥2 | `(a, b, c, …)` | all C(N,2) unordered pairs |
| `mirrored_x(left, right)` | 2 | `(left, right)` | `{(left, right)}` |
| `mirrored_y(top, bottom)` | 2 | `(top, bottom)` | `{(top, bottom)}` |
| `inside(child, parent)` | 2 | `(child, parent)` | `{(child, parent)}` |
| `aligned_below(below, above)` | 2 | `(below, above)` | `{(below, above)}` |
| `distance_x(a, b)` | 2 | `(a, b)` | `{(a, b)}` |
| `distance_y(a, b)` | 2 | `(a, b)` | `{(a, b)}` |

**Algorithm:** for each constraint `c` in template's `CONSTRAINTS`, compute `itertools.combinations(c.referenced_annames(), 2)` and store each pair as a *frozenset of two annames* (so `{A, B}` and `{B, A}` collide). Union across all constraints to build `declared_pairs: set[frozenset[str]]`.

**Edge cases:**
- `same_size("Cover Hero")` (N=1, anchor-only constraint as used in `templates/zeitung-a4-grun/build.py:2545`) yields zero pairs — that's fine; an anchor-witness contributes nothing to the declared-pair set.
- A constraint with a missing anname (orphan) yields a target tuple anyway; the union still happens (we still credit declared intent even if the geometry refers to a renamed frame).
- BrandRule constraints (the 9 in `BRAND_CONSTRAINTS`) do NOT carry per-pair targets in their dataclass; their targets are computed at `check()` time. Per ISSUE.md ¶ "For BrandRule constraints (which don't have `referenced_annames`), we union the targets too if they expose them" — this is a NO-OP today (no BrandRule exposes target pairs), and the planner can defer this to a follow-up. **Recommendation: ignore BrandRule pair contributions in V1; the issue's wording allows it ("if they expose them"). This avoids retrofitting BRAND_CONSTRAINTS.**

HIGH confidence on the factory mapping (verified against `constraints.py:114-519`). MEDIUM confidence on the BrandRule carve-out (matches my reading of ISSUE.md but planner may want to reconsider).

---

## 3. Spine-safety algorithm

**Inputs:**
- `doc.facing_pages: bool` — if False, the rule is a NO-OP. Single-page templates (postkarte, plakat) never hit this branch.
- `page.master_name: str` — populated for doc pages (matches `MNAM`). For zeitung the strings are `'Neue Musterseite rechts'` and `'Neue Musterseite links'`. Substring match (case-insensitive) on `"links"` / `"rechts"` decides side.
- `page.is_master: bool` — True for the entries in `doc.masters`; skip them (master polygons routinely sit at full bleed and would falsely trip).

**Side detection:**

```python
def _spine_side(page) -> Optional[str]:
    """Return "left", "right", or None if undetermined."""
    if page.is_master:
        return None
    name = (page.master_name or "").lower()
    if "links" in name:
        return "left"
    if "rechts" in name:
        return "right"
    return None  # unknown — emit a single warning per page, then skip
```

**Per-frame check (mirrors `_InsidePageRule` shape, walks `doc.pages` directly, ignores the flat `primitives` arg):**

```python
def check(self, primitives, doc):
    violations = []
    if not getattr(doc, "facing_pages", False):
        return violations
    pw_mm = doc.pages[0].width_pt * PT_TO_MM
    tol = self.tolerance_mm  # default 3.0 mm — the ISSUE.md threshold

    for page in doc.pages:
        if page.is_master:
            continue
        side = _spine_side(page)
        if side is None:
            # Unknown side: emit ONE warning per page so we never silently skip.
            violations.append(Violation(
                severity="warning", rule_id=self.id,
                message=f"page {page.label or page.master_name or page.own_page!r} "
                        "uses a master that doesn't match links/rechts; "
                        "spine-safety could not be evaluated",
                targets=(page.master_name or "",),
            ))
            continue
        for item in page.items:
            # SpreadImage halves are intentionally spine-touching; skip them.
            # Identification: ImageFrame whose anname ends with " · left" or
            # " · right" (per blocks.py SpreadImage line 722,731 naming).
            if isinstance(item, ImageFrame):
                an = (item.anname or "")
                if an.endswith(" · left") or an.endswith(" · right"):
                    continue
            bbox = _frame_bbox_mm(item, page)
            if bbox is None:
                continue
            x0, _, x1, _ = bbox
            if side == "left":
                # Spine is on the RIGHT edge: x1 must NOT be within `tol` of pw_mm.
                gap = pw_mm - x1
                if gap < tol:
                    violations.append(Violation(
                        severity="warning", rule_id=self.id,
                        message=(
                            f"frame {item.anname or '<unnamed>'!r} on LEFT page "
                            f"{page.master_name!r} has right edge {x1:.2f}mm "
                            f"within {tol}mm of spine ({pw_mm:.2f}mm); Scribus "
                            f"bleed will leak across to the facing RIGHT page"
                        ),
                        targets=(item.anname or "",),
                    ))
            else:  # side == "right"
                # Spine is on the LEFT edge: x0 must NOT be within `tol` of 0.
                if x0 < tol:
                    violations.append(Violation(
                        severity="warning", rule_id=self.id,
                        message=(
                            f"frame {item.anname or '<unnamed>'!r} on RIGHT page "
                            f"{page.master_name!r} has left edge {x0:.2f}mm "
                            f"within {tol}mm of spine; Scribus bleed will leak "
                            f"across to the facing LEFT page"
                        ),
                        targets=(item.anname or "",),
                    ))
    return violations
```

**Key zeitung context the planner needs:**

The 14 zeitung pages (pages 0–13) carry these `master_name` values (verified at `templates/zeitung-a4-grun/build.py:94-233`):

| Page idx | print page | `master_name` | Computed side | Notes |
|---|---|---|---|---|
| 0 | 1 | `Neue Musterseite rechts` | right | cover; correct |
| 1 | 2 | `Neue Musterseite links`  | left  | correct |
| 2 | 3 | `Neue Musterseite rechts` | right | correct |
| 3 | 4 | `Neue Musterseite links`  | left  | correct |
| 4 | 5 | `Neue Musterseite rechts` | right | correct |
| 5 | 6 | `Neue Musterseite links`  | left  | correct |
| 6 | 7 | `Neue Musterseite links`  | left  | **WRONG — should be rechts** |
| 7 | 8 | `Neue Musterseite rechts` | right | **WRONG — should be links** |
| 8 | 9 | `Neue Musterseite links`  | left  | correct |
| 9 | 10 | `Neue Musterseite links` | left  | **WRONG — should be rechts** |
| 10 | 11 | `Neue Musterseite links`| left  | correct |
| 11 | 12 | `Neue Musterseite links`| left  | **WRONG — should be rechts** |
| 12 | 13 | `Neue Musterseite links`| left  | correct |
| 13 | 14 | `Neue Musterseite links`| left  | **WRONG — should be rechts** |

This is itself an authoring bug in the upstream SLA the executor will need to address as part of Phase 2/3 — either fix the master assignments OR (safer for round-trip) keep them but rely on `is_left` set via `Document.add_page`. **CRITICAL: `Page.is_left` (line 120 / line 386-396) is NOT used by `Document.facing_pages` to decide side; per the doc-comment, "Templates that rely on facing-page side use master_name lookup, not the per-page LEFT bit." So the spine-safety rule MUST use `master_name`, and the zeitung's broken master assignments will surface as side mis-classifications.** Recommend the planner treat "fix master assignments" as part of Phase 2/3 with explicit per-page table.

HIGH confidence on the algorithm + side detection. HIGH confidence on the master-misassignment finding (verified file:line each page).

---

## 4. Algorithm: `brand:undeclared_alignment_drift`

Pseudo-code, tuned to the surfaces above. Iterates `doc.pages` (mirrors `_InsidePageRule`), with per-page filter to avoid cross-page false positives.

```python
@dataclass(frozen=True)
class _UndeclaredAlignmentDriftRule(BrandRule):
    axis_threshold_mm:       float = 5.0     # "almost aligned" upper bound
    adjacency_threshold_mm:  float = 12.0    # "almost stacked" upper bound
    noise_floor_mm:          float = 0.5     # below this, treat as IDENTICAL
                                              # (already covered by inside_page
                                              # tolerance; not a drift signal)

    def check(self, primitives, doc):
        violations = []

        # 1) Build declared-pair set across this template's CONSTRAINTS list.
        #    NOTE: this rule lives in BRAND_CONSTRAINTS, but it needs the
        #    template's CONSTRAINTS list. structural_check.py loads
        #    CONSTRAINTS via mod.CONSTRAINTS (line 163). For the BrandRule
        #    to access it, we either:
        #      (a) attach `_constraints` as a doc attribute at build_doc()
        #          time (requires touching every template), OR
        #      (b) re-load the template module via _load_build_module from
        #          inside the rule (cleaner but couples rule to disk path), OR
        #      (c) [RECOMMENDED] structural_check.py passes CONSTRAINTS to
        #          rules that opt-in. Plumb it via a new BrandRule.check
        #          signature kwarg `constraints: list[Constraint] = ()`,
        #          default empty so existing rules ignore it. The
        #          orchestrator at structural_check.py:209 calls
        #          rule.check(primitives, doc); add `constraints=constraint_list`
        #          and have the new rule accept it.
        declared = set()  # set[frozenset[str, str]]
        constraints = getattr(self, "_constraints_for_check", None) or []
        for c in constraints:
            names = c.referenced_annames()
            for a, b in itertools.combinations(names, 2):
                if a and b and a != b:
                    declared.add(frozenset((a, b)))

        # 2) Per-page pairwise scan.
        for page in doc.pages:
            if page.is_master:
                continue

            # Spatial primitives only; need x/y/w/h.
            spatial = []
            for item in page.items:
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                an = item.anname or ""
                if not an:
                    continue   # cannot be declared; per ISSUE.md skip
                spatial.append((an, item, bbox))

            for i, (a_name, a_item, a_bbox) in enumerate(spatial):
                for b_name, b_item, b_bbox in spatial[i+1:]:
                    if frozenset((a_name, b_name)) in declared:
                        continue
                    drift = _compute_drift(a_bbox, b_bbox)
                    if drift is None:
                        continue   # not adjacent / not nearly aligned
                    violations.append(Violation(
                        severity=self.severity,
                        rule_id=self.id,
                        message=(
                            f"frames {a_name!r} and {b_name!r} on page "
                            f"{page.label or page.own_page!r} appear visually "
                            f"adjacent ({drift.kind} drift {drift.delta_mm:.2f}mm "
                            f"< {drift.threshold_mm}mm). Either declare via "
                            f"{drift.suggestion} or fix geometry."
                        ),
                        targets=(a_name, b_name),
                    ))
        return violations
```

**`_compute_drift(a_bbox, b_bbox)`** (returns a small `Drift` namedtuple or None):

```python
# bbox = (x0, y0, x1, y1) mm
def _compute_drift(a, b, axis_th=5.0, adj_th=12.0, noise=0.5):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b

    # 1) Suspicious-x-axis: |ax0 - bx0| in (noise, axis_th)
    dx_left = abs(ax0 - bx0)
    if noise < dx_left < axis_th:
        return Drift("axis-x", dx_left, axis_th, "same_x(A, B)")
    # also right edges, top edges, bottom edges:
    dx_right = abs(ax1 - bx1)
    if noise < dx_right < axis_th:
        return Drift("axis-x-right", dx_right, axis_th, "same_size + same_x")
    dy_top = abs(ay0 - by0)
    if noise < dy_top < axis_th:
        return Drift("axis-y", dy_top, axis_th, "same_y(A, B)")
    dy_bot = abs(ay1 - by1)
    if noise < dy_bot < axis_th:
        return Drift("axis-y-bottom", dy_bot, axis_th, "same_size + same_y")

    # 2) Suspicious-adjacency-y (A above B):  by0 - ay1 in (noise, adj_th)
    if ay1 < by0:
        gap = by0 - ay1
        if noise < gap < adj_th:
            # also require horizontal proximity (same column-ish)
            if abs(ax0 - bx0) < axis_th:
                return Drift("adjacency-y", gap, adj_th,
                             f"aligned_below(B, A, gap_mm={gap:.1f})")
    if by1 < ay0:
        gap = ay0 - by1
        if noise < gap < adj_th:
            if abs(ax0 - bx0) < axis_th:
                return Drift("adjacency-y", gap, adj_th,
                             f"aligned_below(A, B, gap_mm={gap:.1f})")
    # symmetric x-adjacency for side-by-side frames
    # ... mirror of above on x-axis ...

    # 3) Containment-near: A is mostly-but-not-fully inside B (>=80% area).
    a_area = max(0.0, ax1-ax0) * max(0.0, ay1-ay0)
    if a_area > 0:
        ix0 = max(ax0, bx0); ix1 = min(ax1, bx1)
        iy0 = max(ay0, by0); iy1 = min(ay1, by1)
        i_area = max(0.0, ix1-ix0) * max(0.0, iy1-iy0)
        ratio = i_area / a_area
        if 0.8 <= ratio < 1.0:
            return Drift("containment-near", (1.0 - ratio) * 100, 20.0,
                         "inside(A, B)")
    return None
```

**Per-template tolerance overrides** — `meta.yml::audit_tolerances`:

```yaml
audit_tolerances:
  axis_threshold_mm: 5.0          # default
  adjacency_threshold_mm: 12.0    # default
  noise_floor_mm: 0.5             # default
```

Read in `meta_schema.py` (new function `load_audit_tolerances(slug)`); attach to the rule when structural_check builds it. **Recommendation: defer per-template tolerance overrides to Phase 8 (audit-tool only) — the BrandRule itself uses fixed defaults; the audit tool reads `meta.yml` and applies overrides when running the heuristic stand-alone. Reason: the brand-rule needs to be deterministic across CI runs; per-template knobs invite "adjust until green" anti-pattern.**

HIGH confidence on the pair-set algorithm. MEDIUM confidence on the per-edge thresholds (5mm/12mm match ISSUE.md verbatim but real templates may need calibration; expect Phase 7 tuning). MEDIUM confidence on the `_constraints_for_check` plumbing approach — this is the cleanest of three options; the planner should confirm before executor implements.

**Critical wiring detail:** `BrandRule.check(primitives, doc)` does NOT receive the template's `CONSTRAINTS` list today. Either change the BrandRule signature (cleanly, defaulting kwarg) and update `structural_check.py:209` to pass it, OR have `structural_check.py` set `rule._constraints_for_check = constraint_list` before each call. Both work; the kwarg approach is more honest and doesn't mutate frozen-dataclass instances. **Recommend the planner pick one explicitly.**

---

## 5. Audit-tool architecture (`tools/audit_alignment.py` + `bin/audit-alignment`)

**Reuse pattern (mirror `tools/spec_check.py`):**

```python
# tools/audit_alignment.py
from sla_lib.builder.structural_check import _load_build_module, discover_template_slugs
from sla_lib.builder.brand_constraints import _frame_bbox_mm
from sla_lib.builder import constraints as cs

# Library API:
@dataclass
class PageAuditReport:
    page_idx: int
    page_label: str
    master_name: str
    side: Optional[str]                         # "left"|"right"|None
    n_primitives: int
    declared_pairs: list[tuple[str, str]]
    suspicious_pairs: list[SuspiciousPair]      # the heuristic hits
    spine_warnings: list[str]                   # if facing_pages
    suggested_constraints: list[str]            # python-source skeletons

@dataclass
class TemplateAuditReport:
    slug: str
    facing_pages: bool
    pages: list[PageAuditReport]
    fatal_error: Optional[str] = None

def audit_template(slug: str, root: Path = REPO_ROOT,
                   tolerances: AuditTolerances = DEFAULT_TOLERANCES) \
                   -> TemplateAuditReport: ...

def audit_all(root: Path = REPO_ROOT) -> list[TemplateAuditReport]: ...

def report_to_markdown(rep: TemplateAuditReport) -> str: ...
def report_to_json(rep: TemplateAuditReport) -> dict: ...

# CLI:
#   python3 tools/audit_alignment.py <slug>     # default Markdown to stdout
#   python3 tools/audit_alignment.py --all
#   python3 tools/audit_alignment.py <slug> --json
#   python3 tools/audit_alignment.py <slug> --md FILE.md
#   python3 tools/audit_alignment.py --all --output-dir build/audit/
#   --tolerance-axis-mm <float>          # default 5.0
#   --tolerance-adjacency-mm <float>     # default 12.0
#   --noise-floor-mm <float>             # default 0.5
# Exit code: 0 always (informational), or 1 only with --strict flag.
```

**Bin shim:**

```python
#!/usr/bin/env python3
# bin/audit-alignment — alignment audit (Issue #22 entry point).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from audit_alignment import main
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

This mirrors `bin/render-gallery` and `bin/check-stale-previews` exactly (verified file shapes above).

**Markdown report shape (per template):**

```markdown
# audit_alignment: zeitung-a4-grun

facing_pages: true
pages: 14, primitives total: 318

## Page 1 (master: Neue Musterseite rechts, side: right)
- Primitives: 14
- Declared pairs (from CONSTRAINTS): []
- Suspicious-undeclared adjacencies:
  - "Cover Hero" ↔ "u2950": adjacency-y drift 0.00mm; suggest:
    `aligned_below("u2950", "Cover Hero", gap_mm=0.0, name="cover_top_to_green_bottom_flush")`
  - ... etc
- Spine-safety: clean
## Page 2 (master: ..., side: left)
- ...
```

**JSON shape:** dict with `slug, facing_pages, pages: [{page_idx, primitives, declared_pairs, suspicious_pairs: [{a, b, kind, delta_mm, suggested_constraint}], spine_warnings, ...}]`. Gives planners + LLMs structured input.

HIGH confidence on the architecture; pattern is a literal mirror of `tools/spec_check.py` + `tools/sla_lib/builder/structural_check.py`.

---

## 6. Per-template state of the three stable templates

### `templates/zeitung-a4-grun/`

- **build.py:** 2563 lines. 112 `pageN.add(...)` invocations across 14 doc pages + 2 masters.
- **`facing_pages=True`** (line 32). Two masters: `'Neue Musterseite rechts'` (line 71-81) and `'Neue Musterseite links'` (line 82-92).
- **CONSTRAINTS list** (line 2542-2556): 9 entries, ALL `same_size("X")` single-target anchors. They serve only as orphan-detection warnings on rename, NOT actual alignment relationships. **The pair-set is empty today** — every cross-frame relationship is undeclared.
- **`meta.yml::brand_overrides`:** `brand:line_spacing_0.9` (typography drift) + `brand:inside_page` (residual u2950 polygon overflow, tracked in #39 — this issue supersedes #39 per ISSUE.md ¶ "Superseded follow-ups").
- **User-confirmed bug locations** (verified file:line):
  - **Page 1 (page0):** `Cover Hero` at `(x=0, y=0, w=210.0, h=155.567)` — file build.py:235-244. `u2950` at `(x=216.41, y=155.567, w=148.602, h=220.489, rotation_deg=90)` — file build.py:246-256. Rotated bbox: `(-4.08, 155.57, 216.41, 304.17)`. Confirmed: extends past left bleed (-3) by 1.08mm (within tolerance), past right bleed by 0.41mm, past page bottom (300+3=303) by 1.17mm. Width relationship: Cover Hero w=210, u2950 rotated bbox-w = 220.49. **Not flush, not same-width.**
  - **Page 8 (page7):** `P7 Portrait` at `(x=134.65, y=200.65, w=51.35, h=76.35)` — file build.py:1368-1377. `u918` at `(x=20.0, y=195.0, w=170.0, h=82.0)` — file build.py:1327-1336. Inset gaps: top=200.65-195.0=5.65mm; right=190.0-186.0=4.0mm; left=134.65-20.0=114.65mm; bottom=277.0-277.0=0.0mm. Confirmed: not flush, no declared `inside` relationship.
  - **Page 10 (page9):** `P9 Spread` at `(x=0, y=0, w=210, h=126.14)` — file build.py:1802-1811. Text columns `Kopie von u2d5c (13)` etc. start at y=49.5 (visible from line ranges 1686+). **Confirmed: text columns overlap image** (49.5 < 126.14). Per #16 (lines 1802 anname comment), P9 Spread was moved to page-local origin then; ISSUE.md says this fix was wrong — it should be a `SpreadImage` block instead.
  - **Page 11 (page10):** `P10 Portrait` at `(x=143.41, y=202.57, w=66.59, h=94.43)` — file build.py:1894-1902. The right-column text axis above (column-3 in 3-column grid) is at x=135.3 per the ISSUE.md grid description. Confirmed: 143.41 - 135.3 = 8.11mm horizontal drift.
  - **Page 12 (page11):** ImageFrame at `(x=0, y=-0.18, w=210.80, h=213.92, fill='Dunkelgrün')` — file build.py:1952-1961. No anname (unnamed Dunkelgrün). Width 210.80 > page 210 by 0.80mm right-edge bleed-nudge (within `_InsidePageRule.error_cutoff_mm=1.0`, surfaces as warning today).
- **The user-named bugs are real and visible at the cited file:line ranges.** HIGH confidence.

### `templates/postkarte-a6-kampagne/`

- **build.py:** 436 lines. 18 page additions across 2 doc pages (page0=Vorderseite, page1=Rückseite).
- **`facing_pages=False`** (line 32). Single master `'Normal'` (line 61-72).
- **CONSTRAINTS list** (line 425-429): one entry — `inside("P1 Hero", "Seitenhintergrund", name="hero_inside_page_bg")`. Pair-set: `{(P1 Hero, Seitenhintergrund)}`.
- **Annames present:** P1 Hero (page0, line 105), Seitenhintergrund (likely from `PageBackground.for_page` block — confirm at runtime). Other annames: Logo, Headline (from slot annames in meta.yml::slots).
- **Spine-safety impact:** zero (single-page template). Rule will short-circuit.
- **Audit will find:** likely 5–10 suspicious adjacencies between headline / hero / logo / impressum / QR. **The fix is to encode the intentional ones via CONSTRAINTS, not hand-edit geometry.**

### `templates/plakat-a1-hochformat/`

- **build.py:** 266 lines. 9 page additions on a single page (page0).
- **`facing_pages=False`** (line 31). Single master `'Normal'` (line 50).
- **CONSTRAINTS list** (line 254-259): one entry — `same_size("Hero", name="hero_anname_anchor")`. Pair-set: empty (single-target witness).
- **Annames present:** "Hero" (line 170), plus implicit annames in some other frames. Most of page0's primitives are anonymous (TextFrames without `anname=`) — see file.py:73-205.
- **Spine-safety impact:** zero (single-page A1 template).
- **Audit will find:** few suspicious adjacencies (only 9 primitives, most anonymous so they fall outside the algorithm's "must have anname" filter). The fix is largely "give the unnamed frames annames so they CAN be declared."

HIGH confidence on the per-template state. MEDIUM confidence on the predicted audit hit-counts.

---

## 7. The "regen" operation

`bin/render-gallery [<id>] [--skip-visual-diff] [--dry-run]` is a Python shim that delegates to `tools/render_pipeline.py::main` (bin/render-gallery file:1-13).

**What `_orchestrate_single` does** (verified at `tools/render_pipeline.py:467-507`) for a single-SLA template (postkarte, zeitung):

1. Calls `build.py` (already done by `_orchestrate_template` upstream — line 580).
2. `render_sla_to_pdf(template-preview.sla, preview.pdf)` via Scribus headless.
3. `_scrub_pdf_metadata(preview.pdf)` — byte-deterministic.
4. **Deletes ALL `page-*.png` in tdir** (line 485-486) — clean slate.
5. `rasterise(preview.pdf, tdir / 'page', dpi)` via pdftoppm — produces `page-1.png`...
6. `_zero_pad_pngs(tdir, 'page')` — renames `page-1.png → page-01.png` for stable sort.
7. `_run_sla_diff_strict(...)` — UNLESS `meta.yml::sla_diff_strict: false` (zeitung opts out). Raises on mismatch.
8. `_run_visual_diff(...)` — SKIPPED when `--skip-visual-diff` is passed (which the issue mandates: "bin/render-gallery --skip-visual-diff to regen").
9. `_sha256_of(template.sla)` → `_update_meta_hash(meta.yml, h)` updates `previews_for_sla:` field.
10. `_mirror_to_site_public(tdir, public_dir, family=False)` copies page-*.png + preview.pdf + template.sla into `site/public/templates/<id>/`.

**Files that get dirty per template after `bin/render-gallery <id> --skip-visual-diff`:**

| File | Why dirty |
|---|---|
| `templates/<id>/template.sla` | Re-emitted by `build.py` |
| `templates/<id>/template-preview.sla` | Re-emitted by `build.py::build_preview()` |
| `templates/<id>/preview.pdf` | Re-rendered from preview SLA |
| `templates/<id>/page-NN.png` | Re-rasterised (NB: ALL existing page-*.png deleted first) |
| `templates/<id>/meta.yml` | `previews_for_sla:` SHA bumped to match new template.sla |
| `site/public/templates/<id>/template.sla` | Mirror |
| `site/public/templates/<id>/preview.pdf` | Mirror |
| `site/public/templates/<id>/page-NN.png` | Mirror |

For the three stable templates, that's ~30 files dirty after `bin/render-gallery --skip-visual-diff` for all three. (Zeitung alone has 14 PNGs; postkarte 2; plakat 1.)

`bin/check-stale-previews` validates `SHA256(template.sla) == meta.yml::previews_for_sla` for any template that has `original_sla:` or `previews_for_sla:` in meta.yml. After regen this passes; if you skip regen after editing build.py, it fails (expected).

HIGH confidence; verified file:line.

---

## 8. Test patterns

**For `brand:spine_safety`** — copy the `class XTests(unittest.TestCase)` shape from `tools/sla_lib/tests/test_constraints_inside_page.py` (a clean Issue #14 example). Six test cases per ISSUE.md ¶ "6 cases (LEFT/RIGHT × within-tol/outside-tol × non-facing no-op)":

```python
# tools/sla_lib/tests/test_brand_spine_safety.py
"""Tests for brand:spine_safety (Issue #22)."""
from __future__ import annotations
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document
from sla_lib.builder.primitives import ImageFrame, Polygon
from sla_lib.builder.brand_constraints import (
    BRAND_CONSTRAINTS, _SpineSafetyRule,
)


def _find_rule(rid):
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _facing_doc():
    """A4 facing-pages doc with one left + one right page."""
    d = Document(title="t", template_id="t", facing_pages=True)
    d.add_master(name="rechts", size="A4", facing="right")
    d.add_master(name="links",  size="A4", facing="left")
    d.add_page(size="A4", master="rechts")  # cover, right
    d.add_page(size="A4", master="links")   # left page (facing)
    return d


def _single_doc():
    d = Document(title="t", template_id="t", facing_pages=False)
    d.add_page(size="A4")
    return d


class SpineSafetyRuleTests(unittest.TestCase):
    def test_left_page_right_edge_at_spine_warns(self):
        d = _facing_doc()
        # Page 1 (left): right edge x=210 = spine — within 3mm of pw_mm=210.
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100,
                                   anname="P1 Hero"))
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")

    def test_right_page_left_edge_at_spine_warns(self):
        d = _facing_doc()
        # Page 0 (right): left edge x=0 = spine.
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100,
                                   anname="P0 Hero"))
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)

    def test_left_page_right_edge_well_inside_passes(self):
        d = _facing_doc()
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=200, h_mm=100,
                                   anname="P1 Hero"))  # 10mm inset
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_right_page_left_edge_well_inside_passes(self):
        d = _facing_doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=0, w_mm=200, h_mm=100,
                                   anname="P0 Hero"))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_single_page_doc_is_no_op(self):
        d = _single_doc()
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100,
                                   anname="P0 Hero"))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_spread_image_halves_skipped(self):
        d = _facing_doc()
        # SpreadImage emits two ImageFrames named "X · left" and "X · right".
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100,
                                   anname="P4 Foto-Spread · right"))
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100,
                                   anname="P4 Foto-Spread · left"))
        rule = _find_rule("brand:spine_safety")
        # SpreadImage halves are intentional spine-touchers; skip.
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_unknown_master_emits_one_warning_per_page(self):
        d = Document(title="t", template_id="t", facing_pages=True)
        d.add_master(name="weird", size="A4", facing="right")
        d.add_page(size="A4", master="weird")
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100,
                                   anname="X"))
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertIn("could not be evaluated", vs[0].message)
```

**For `brand:undeclared_alignment_drift`** — same skeleton, plus the test cases from ISSUE.md Phase 4b (5 cases). The new test file should also bump `RegistryTests.test_nine_rules_exact` (currently `test_brand_constraints.py:49`) to `test_eleven_rules_exact` and add the two new IDs to `test_ids_are_canonical` (line 52-65).

HIGH confidence on the test-pattern (verified copy of test_constraints_inside_page.py shape).

---

## 9. CI integration (`.github/workflows/pages.yml`)

`pages.yml` (verified line 148-156):

```yaml
- name: Run structural check (Issue #12)
  run: |
    set -euo pipefail
    PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
```

This already runs the new BrandRules automatically once they land in `BRAND_CONSTRAINTS` — the orchestrator iterates the registry. No CI change needed for the rules themselves.

For `bin/audit-alignment`, **add a new step AFTER the structural-check step**:

```yaml
- name: Run alignment audit (Issue #22, informational)
  run: |
    set -euo pipefail
    mkdir -p build/audit
    PYTHONPATH=tools python3 tools/audit_alignment.py --all \
      --output-dir build/audit/ || true
    # `|| true` keeps audit informational; promotion to fatal deferred per ISSUE.md.

- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: audit-alignment-report
    path: build/audit/
```

The `|| true` matches ISSUE.md ¶ "Wired into `.github/workflows/pages.yml` as a non-fatal step (informational only initially; promotion to fatal once all production templates are clean)."

**Severity propagation:** the existing `structural_check.py:312` returns exit code 1 only on `error`-severity issues. Both new rules emit `warning`-severity by default — they will surface in the report but not fail CI. That's exactly what ISSUE.md asks for ("Severity = warning by default (heuristic rules can false-positive)") and matches existing `_InsidePageRule` pattern (warnings for sub-1mm bleed nudges, errors for >1mm overflows).

HIGH confidence; verified file:line.

---

## 10. Per-template `meta.yml` extensions (audit tolerances)

`meta.yml` already has these fields per template:
- `brand_overrides:` (validated by `meta_schema.py::load_brand_overrides`)
- `sla_diff_strict:` (validated by `load_sla_diff_strict`)
- `previews_for_sla:` (managed by render_pipeline)
- `original_sla:`, `ci_overrides:`, `slots:`, `preflight:`, etc.

**Recommendation: defer `audit_tolerances:` to a follow-up.** Reasons:

1. The two BrandRules use FIXED defaults (5mm axis, 12mm adjacency, 0.5mm noise floor) so CI is deterministic. Per-template knobs in BrandRules invite "adjust until green" — bad for our spine safety + drift detection guarantees.
2. The audit tool itself can read tolerances from CLI flags (`--tolerance-axis-mm` etc.) for ad-hoc per-template runs. That covers the "I want to audit zeitung at 3mm threshold" use case without a meta.yml schema extension.
3. If we DO need per-template overrides later, the schema extension is mechanical — add an `_AUDIT_TOLERANCES_SCHEMA` to `meta_schema.py`, mirror `load_sla_diff_strict`'s pattern, return a dataclass.

**If the planner disagrees and wants schema extension in this issue**, here's the proposed schema:

```python
_AUDIT_TOLERANCES_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "axis_threshold_mm":      {"type": "number", "minimum": 0.5, "maximum": 20.0},
        "adjacency_threshold_mm": {"type": "number", "minimum": 0.5, "maximum": 50.0},
        "noise_floor_mm":         {"type": "number", "minimum": 0.0, "maximum": 5.0},
    },
}

def load_audit_tolerances(slug, root=None) -> dict:
    """Return per-template audit tolerances (defaults applied for missing keys)."""
    p = _meta_path(slug, root)
    defaults = {"axis_threshold_mm": 5.0,
                "adjacency_threshold_mm": 12.0,
                "noise_floor_mm": 0.5}
    if not p.exists():
        return defaults
    data = yaml.safe_load(p.read_text("utf-8")) or {}
    if "audit_tolerances" not in data:
        return defaults
    overrides = data["audit_tolerances"] or {}
    jsonschema.validate(instance=overrides, schema=_AUDIT_TOLERANCES_SCHEMA)
    return {**defaults, **overrides}
```

MEDIUM confidence (recommendation grounded in the meta_schema patterns; the choice itself is judgement).

---

## 11. Reusable Components (Don't rebuild)

| Need | Reuse | File:line |
|---|---|---|
| Load template build.py + call build_doc() | `_load_build_module(slug, root)` | structural_check.py:104 |
| Iterate all primitives across pages | `doc.iter_all_primitives()` | document.py:413 |
| Compute anchor- + rotation-aware bbox | `_frame_bbox_mm(item, page)` | brand_constraints.py:393 |
| Discover slug list under templates/ | `discover_template_slugs(root)` | structural_check.py:232 |
| Read brand_overrides from meta.yml | `load_brand_overrides(slug, root)` | meta_schema.py:52 |
| Read sla_diff_strict from meta.yml | `load_sla_diff_strict(slug, root)` | meta_schema.py:74 |
| Constraint id, name, targets, check() | `Constraint` base + 12 factories | constraints.py:51-519 |
| Violation dataclass | `Violation` | constraints.py:35 |
| BrandRule base + decorator pattern | `BrandRule` + `_make_rule()` | brand_constraints.py:57, 501 |
| Test fixtures for synthetic Documents | `_doc()` / `_doc_with()` helpers | test_brand_constraints.py:31, test_constraints_inside_page.py:29 |
| SpreadImage block (P9 Spread fix) | `SpreadImage(image, page_w_mm, page_h_mm, h_mm)` | blocks.py:687 |
| CLI shape mirror | `tools/spec_check.py::main` | spec_check.py:205 |
| Bin shim shape mirror | `bin/render-gallery`, `bin/check-stale-previews` | (verified above) |

---

## 12. Potential Conflicts

- **`brand_overrides` for `brand:inside_page`** in zeitung's meta.yml (line 28-37) currently silences the residual u2950 cover-polygon overflow. Phase 3 of this issue trims u2950 (per ISSUE.md ¶ "Trim u2950 polygon to fit page bounds"). Once trimmed, the override should be REMOVED from zeitung/meta.yml. Failure to remove it leaves the rule silenced and any future overflow goes undetected. **Planner: add explicit "remove override" step.**
- **Master misassignments** (six pages have wrong master in zeitung; see Section 3 table). Renaming master_name on those pages will cascade through `tools/sla_diff.py --strict` because the SLA emit changes. Zeitung already has `sla_diff_strict: false` so this is fine, but the executor must be aware.
- **`P9 Spread` rename when migrating to SpreadImage:** the SpreadImage block emits frames named `"P9 Spread · left"` and `"P9 Spread · right"`. The existing CONSTRAINTS entry `same_size("P9 Spread", name="p9_spread_anchor")` (build.py:2555) will go orphan-warning. Update it to two anchors, or drop it (not load-bearing; it's a witness only).
- **`P4 Foto-Spread` migration to SpreadImage** is also implied by ISSUE.md Phase 3 ("Convert P4 Foto-Spread (intended spread) to SpreadImage(...)"). Same rename cascade as P9.
- **`test_zeitung_overflow.py::test_inside_page_finds_only_u2950_without_override`** (line 41-62): asserts there's exactly 1 inside_page error (the u2950 polygon). Phase 3 trims u2950 → this test must be updated to assert ZERO. ISSUE.md says "Update `tools/sla_lib/tests/test_zeitung_overflow.py` — assert zero `inside_page` errors AND zero `brand:spine_safety` warnings AND all per-template CONSTRAINTS green."
- **`test_brand_constraints.py::test_nine_rules_exact`** (line 49-50) and `test_ids_are_canonical` (line 52-65) hard-code 9 rules + their IDs. ISSUE.md ¶ "Update `tools/sla_lib/tests/test_brand_constraints.py` — bump count from 9 to 10." But this issue adds TWO rules (spine_safety + undeclared_alignment_drift), so the count goes 9→11, and the canonical ID set gains both. ISSUE.md text says "10" but is wrong by one — flag this for the planner to confirm.

---

## 13. Code Patterns in Use

- **BrandRule subclass pattern:** frozen dataclass extending `BrandRule`, override `check(primitives, doc)`. Two new rules follow this exactly.
- **Per-page iteration in BrandRule:** `for page in doc.pages: if page.is_master: continue; for item in page.items: ...` — see `_InsidePageRule.check` lines 462-468 and `_Bleed3mmRule.check` lines 318-322. Both new rules MUST follow this (the flat `primitives` arg loses page context).
- **Constraint factory pattern:** factory normalizes targets via `_norm()`, returns a frozen `_*Constraint` instance with `id, targets, name`. The audit tool consumes `Constraint.referenced_annames()` purely as a tuple of strings; doesn't need to introspect the subclass.
- **Test layout:** `tools/sla_lib/tests/test_*.py` with `unittest.TestCase` classes, `sys.path.insert(0, str(ROOT / "tools"))` for imports, helper `_doc()` / `_find_rule()` functions at file top.
- **Bin shim:** thin Python script in `bin/`, prepends `tools/` to `sys.path`, imports + delegates to `tools/<module>.main()`.
- **CLI argparse + `--all` + `--json`:** `structural_check.py:272-312` and `spec_check.py:205-248` both follow this. The audit tool should mirror.

---

## Summary for the planner

The infrastructure to add the two new BrandRules is **lightweight and pattern-matched**: each rule is ~60-100 lines (subclass + check + tests) following the exact shape of the 9 existing rules and Issue #14's `_InsidePageRule`. The biggest design decision is **how the undeclared-drift rule accesses the template's CONSTRAINTS list** — recommend the kwarg-on-check signature change (cleanest, no mutation, opt-in).

The audit tool is a **straight mirror of `tools/spec_check.py`** with library + CLI surface, reusing `_load_build_module`, `discover_template_slugs`, `_frame_bbox_mm`, and `Constraint.referenced_annames()`. ~250 lines total.

The biggest mechanical work is **Phase 2 (encode CONSTRAINTS)** for zeitung. The audit tool's output gives the executor a starting list of suggested constraint skeletons; the executor reviews + edits build.py (Phase 3) until every CONSTRAINT is green.

The user-confirmed bugs at pages 1, 8, 10, 11, 12 of zeitung are **all real** at the cited file:line ranges. The cleanup also surfaces a structural problem I noted in Section 3: **6 of 14 zeitung pages have the wrong `master_name` assignment** (left where right is expected, or vice-versa). The planner should call out master-fixup as part of Phase 2/3.

For postkarte and plakat, the audit will find a small number of suspicious pairs (single-page templates, few primitives, mostly anonymous). Phase 7 work for those is mechanical: name the unnamed frames, declare 2-5 constraints each, regen.

CI integration is one new informational step (≤10 lines of YAML) that runs `tools/audit_alignment.py --all` non-fatally and uploads the report as an artifact.

