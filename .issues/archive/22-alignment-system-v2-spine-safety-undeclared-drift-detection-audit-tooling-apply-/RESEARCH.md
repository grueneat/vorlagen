# RESEARCH — #22: Alignment system v2 — spine-safety + undeclared-drift + audit tooling

**Status:** synthesized from two parallel research dimensions (codebase / pitfalls). Confidence high — every claim verified against source files in this worktree. ISSUE.md text contains two minor errors that this RESEARCH corrects (rule count 9→11 not 9→10; 6 Zeitung pages have wrong `master_name` assignments not surfaced in ISSUE.md).

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for line-level evidence.

---

## Executive summary

The user's framing — *"detect this kind of spill or misalignment automatically; even if it's not defined in the spec, either report warnings or errors in case those alignment configurations aren't defined and mentioned as conditions"* — translates to two new BrandRules + one audit CLI tool, applied first to the three stable production templates (zeitung, postkarte-a6-kampagne, plakat-a1-hochformat). Per-template alignment encoding for V1-bound templates (#17–#21) is **deferred to those issues** — they already prescribe `CONSTRAINTS = [...]` lists.

Both research dimensions converged on three load-bearing decisions the planner must lock before the executor starts:

1. **`Page.is_left` is broken** (hardcoded `False` at `document.py:391-393`). Spine-safety MUST detect facing-page side via `master_name` regex `\b(links|rechts)\b`, with early-exit when `not doc.facing_pages`. 7 of 8 templates have `facing_pages=False` so the early exit cuts noise to ~0.
2. **6 Zeitung pages have wrong `master_name` assignments** (pages 6, 7, 9, 11, 13 marked `links` but should be `rechts`; page 8 marked `rechts` but should be `links`). My earlier sweep that listed "8 spine-touching frames" was therefore incomplete. Phase 2/3 must fix these assignments first.
3. **Issue text says "bump count from 9 to 10"** — wrong. Two rules are added (`brand:spine_safety` + `brand:undeclared_alignment_drift`), so registry count goes **9 → 11**.

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | `brand:spine_safety` lives in `tools/sla_lib/builder/brand_constraints.py` as a `BrandRule` (not a Constraint). | Needs `(primitives, doc)` for `Document.facing_pages` and `Page.master_name`. |
| 2 | `brand:undeclared_alignment_drift` lives in `tools/sla_lib/builder/brand_constraints.py` as a `BrandRule`. | Needs the doc to iterate per-page; needs the per-template `CONSTRAINTS` list to know which pairs are declared. |
| 3 | **CONSTRAINTS-into-BrandRule plumbing — pick option B (signature kwarg).** Modify `BrandRule.check(self, primitives, doc, constraints=None)` so the orchestrator can pass the per-template CONSTRAINTS list. The two new rules accept it; the 9 existing rules ignore it (default `None`). | Codebase agent surfaced 3 options; B is smallest blast-radius. Option A (read attribute on doc) requires a `Document.constraints` field that doesn't exist; option C (singleton context) is global state. |
| 4 | Side detection via `master_name` regex `\b(links\|rechts)\b`. Early exit when `not doc.facing_pages`. Unknown side → emit a single warning per template (not per page). | `Page.is_left` is broken (verified `document.py:391-393`). Word-boundary regex avoids false matches on substrings. |
| 5 | SpreadImage halves are exempted via anname-pattern `r" · (left\|right)$"`. | Simplest approach — no `_Frame` schema change. |
| 6 | Audit tool `tools/audit_alignment.py` mirrors `tools/spec_check.py` CLI shape: `--template <slug>`, `--all`, `--json`, `--md`. Reuses `_load_build_module` from `structural_check.py:104` (with its `sys.modules.pop()` line). | Established pattern; established helper. |
| 7 | Move `_frame_bbox_mm`, `_rotated_bbox`, and `_load_build_module` into shared modules — `tools/sla_lib/builder/bbox.py` + `tools/sla_lib/builder/template_loader.py`. Two new BrandRules + audit tool all consume them. | Pitfalls P-2 + P-18 — modest upfront refactor that pays off immediately. |
| 8 | Severity for `brand:undeclared_alignment_drift` = `warning` by default. Promotion to error per-template via `meta.yml::audit_strict: true` is **deferred** to a follow-up. | Pitfalls Q-2 — avoids retrofit churn. Day 1 the rule is informational. |
| 9 | Pre-apply `brand_overrides[brand:undeclared_alignment_drift]` to: V1-bound templates (`wahlaufruf-postkarte-a6-quer`, `wahltag-tueranhaenger`, `themen-plakat-a3-quer`, `infostand-tent-card-a5-quer`, `kandidat-falzflyer-din-lang`) with reason "see #17/.../21 V1 layout work" AND to `postkarte-a6-kampagne` + `plakat-a1-hochformat` with reason "scheduled for follow-up encoding". Reason: per-template alignment encoding for these is out of scope. | Codebase agent's open-question + pitfalls Q-4 confluence. |
| 10 | CI integration: add `bin/audit-alignment --all` as informational (`|| true`) step in `.github/workflows/pages.yml` after `structural_check --all`. Promotion to fatal is deferred. | Pitfalls P-13 — fatal day-1 breaks every untouched template. |
| 11 | Per-template `meta.yml::audit_tolerances` schema extension is **deferred** to a follow-up. Day 1 uses CLI flags. | Pitfalls Q-2. |
| 12 | Phase 7 (apply to postkarte-a6-kampagne + plakat-a1-hochformat alignment encoding) is **deferred** to a follow-up. This issue covers ZEITUNG only as the applied target. | Token-budget pragmatism + the 6-master-name-assignment fix on Zeitung is already substantial. Postkarte/plakat get the new rules + overrides + audit tooling, but no per-template CONSTRAINTS encoding. |
| 13 | Close GH #39 (u2950 cover polygon) at PR-merge time — superseded by Phase 3 of this issue (Page-1 alignment fix trims u2950). | ISSUE.md "Superseded follow-ups" + pitfalls P-20. |

---

## Scope changes vs. ISSUE.md

| ISSUE.md scope | Status | Why |
|---|---|---|
| Phase 1-6 on Zeitung | **CONFIRMED** with addition: also fix the 6 wrong `master_name` assignments first (codebase agent finding). |
| Phase 4b new rule `brand:undeclared_alignment_drift` | **CONFIRMED** with severity = warning + per-template skip (pitfalls Q-2). |
| Phase 7 on postkarte-a6-kampagne + plakat-a1-hochformat | **NARROWED**: new rules + overrides + audit tooling YES; per-template CONSTRAINTS encoding **deferred** to follow-up. (Locked decision #12.) |
| Phase 8 audit tool + CI step | **CONFIRMED** with informational gate (`|| true`) — promotion to fatal deferred. |
| Issue text: "bump count from 9 to 10" | **CORRECTED**: 9 → 11 (two rules added). |
| Acceptance criterion "All per-template CONSTRAINTS green for all 3 stable templates" | **NARROWED**: Zeitung only encoded; postkarte + plakat get the rules + overrides without encoding. |

---

## User constraints (lifted from ISSUE.md + originating session)

- **No image rendering** during this issue. Code-only verification: `structural_check --all`, `bin/audit-alignment`, `pdfimages -list` (metadata only), unit tests.
- **Atomic PR** — all of: 2 new BrandRules + bbox.py + template_loader.py refactors + audit tool + V1-bound brand_overrides + zeitung CONSTRAINTS encoding + zeitung build.py geometry fixes + zeitung master_name fixes + tests + regen + docs. ~15-20 commits. Pitfalls flag risk of running out of executor usage budget mid-PR — the planner should split tasks small.
- **No new dependencies.** Python 3.13, lxml, PyYAML, jsonschema, Pillow, poppler, ghostscript already pinned.

---

## Codebase Analysis — interfaces

<interfaces>

### Existing infrastructure to extend

```
file: tools/sla_lib/builder/brand_constraints.py
@dataclass(frozen=True)
class BrandRule:
    id: str        # MUST match ^brand:[A-Za-z_0-9.]+$
    description: str

    def check(self, primitives, doc) -> list[Violation]: ...
# 9 rules exist (post-#14): colors, fonts, line_spacing_0.9, line_spacing_1.3_bodytext,
#   hl_sub_gap_2x, m_margin, logo_size_3M, bleed_3mm, inside_page.
# Issue text incorrectly says "9→10"; correct is 9→11.

# Helpers added in #14:
def _frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]: ...
def _rotated_bbox(x, y, w, h, deg): ...
def _InsidePageRule(BrandRule): ...
```

### Spine-safety + undeclared-drift signature change

```
# Locked decision #3: BrandRule.check gains optional constraints kwarg.
@dataclass(frozen=True)
class BrandRule:
    id: str
    description: str

    def check(self, primitives, doc, constraints=None) -> list[Violation]: ...
    # New rules read `constraints` (per-template CONSTRAINTS list);
    # old rules ignore (default None).
# Orchestrator (structural_check.check_template) passes mod.CONSTRAINTS through.
```

### Audit tool architecture

```
file: tools/audit_alignment.py  (NEW — ~250 lines)
# CLI:
#   audit_alignment.py <slug> [--json | --md] [--axis-tol 5.0] [--adjacency-tol 12.0]
#   audit_alignment.py --all [...]
# Library:
#   def audit_template(slug, root, axis_tol_mm=5.0, adjacency_tol_mm=12.0) -> AuditReport
# Output (Markdown):
#   ## templates/<slug>
#   ### Page 1 (cover)
#     - declared adjacencies: 4 pairs
#     - suspicious axis-near pairs (drift > 0.5mm, <= 5mm):
#       * 'P10 Portrait' x=143.4 vs 'Kopie von u2da1 (19)' x=135.3 → drift 8.1mm
#         suggested: same_x("P10 Portrait", "Kopie von u2da1 (19)", name="p11_portrait_col3_axis")
#     - spine-bleed candidates:
#       * 'P1 Hero' x+w=210.0, page is LEFT → use SpreadImage or inset 3mm
```

### `bin/audit-alignment` shim

```
file: bin/audit-alignment  (NEW — ~10 lines, mirror bin/render-gallery shape)
#!/usr/bin/env bash
exec python3 "$(git rev-parse --show-toplevel)/tools/audit_alignment.py" "$@"
```

### Document and Page geometry (relevant for spine-safety)

```
file: tools/sla_lib/builder/document.py
@dataclass
class Document:
    facing_pages: bool          # line ~140
    pages: list[Page]
    masters: list[Page]
    def iter_all_primitives(self): ...   # line ~413

@dataclass
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float
    items: list
    is_master: bool
    is_left: bool               # ALWAYS False on doc pages — see line 391-393
    master_name: str            # canonical side detector
    label: str
    page_xpos_pt: float
    page_ypos_pt: float
```

### Constraint factories (declared-pair extraction)

```
file: tools/sla_lib/builder/constraints.py
# 12 factories. Pair-extraction algorithm:
# - Multi-arity (N targets): C(N, 2) combinations via itertools.combinations
# - Binary: one pair
# - Single-target witnesses (e.g. same_size("X", name=...)): no pair
# Pair set: set[frozenset[str]]  (order-insensitive)

# Multi-arity: same_x, same_y, same_size, equal_gap, hierarchy, same_style
# Binary:      mirrored_x, mirrored_y, inside, distance_x, distance_y, aligned_below
```

### `_load_build_module` (re-used by audit tool)

```
file: tools/sla_lib/builder/structural_check.py:104
def _load_build_module(slug, root):
    # Drops sys.modules cache per-slug → safe re-imports under --all.
    # Audit tool uses verbatim. After locked decision #7, moves to
    # tools/sla_lib/builder/template_loader.py for cleaner reuse.
```

</interfaces>

---

## Standard Stack (verified)

| Item | Value |
|---|---|
| Python | 3.13.5 |
| Test runner | `python3 -m unittest discover tools/sla_lib/tests` |
| Build regen | `python3 templates/<slug>/build.py` (run via `bin/render-gallery <slug> --skip-visual-diff`) |
| Audit | `tools/audit_alignment.py <slug> [--all]` (NEW) + `bin/audit-alignment` shim (NEW) |
| Round-trip diff (CI) | `tools/sla_diff.py --strict --allow-brand-extras` (gated by `meta.yml::sla_diff_strict` per #16) |
| Image inspection | `pdfimages -list` (metadata only — never visual) |
| New deps | none |

---

## Don't Hand-Roll

- `_frame_bbox_mm` and `_rotated_bbox` exist (#14) — use them. Locked decision #7 moves them to a shared `bbox.py` so the audit tool consumes them too.
- `_load_build_module` already drops sys.modules cache per slug — reuse via `template_loader.py` (locked decision #7).
- `Constraint.referenced_annames()` already returns the targets tuple — union via `itertools.combinations` to build the declared-pair set.
- The 9 existing brand rules cover everything else — don't add anything outside spine-safety + undeclared-drift.
- `bin/render-gallery --skip-visual-diff` is the canonical regen command.
- `meta_schema.load_brand_overrides` already validates rule ids — the new rule ids `brand:spine_safety` and `brand:undeclared_alignment_drift` need only be added to `BRAND_CONSTRAINTS` list (the regex `^brand:[A-Za-z_0-9.]+$` accepts both).

---

## Architecture Patterns

### `_SpineSafetyRule` (new, lives in `brand_constraints.py`)

```python
SPINE_SAFETY_INSET_MM = 3.0
SIDE_RX = re.compile(r"\b(links|rechts)\b")
SPREAD_HALF_RX = re.compile(r" · (left|right)$")

@dataclass(frozen=True)
class _SpineSafetyRule(BrandRule):
    inset_mm: float = SPINE_SAFETY_INSET_MM
    tolerance_mm: float = 0.5

    def check(self, primitives, doc, constraints=None) -> list[Violation]:
        # Early exit: no facing pages → rule is no-op
        if not getattr(doc, "facing_pages", False):
            return []
        violations = []
        unknown_pages = []
        for page in doc.pages:
            if page.is_master:
                continue
            m = SIDE_RX.search(page.master_name or "")
            if not m:
                unknown_pages.append(page.label or page.master_name or "<unnamed>")
                continue
            side = m.group(1)  # "links" or "rechts"
            pw_mm = page.width_pt / PT_PER_MM
            for item in page.items:
                if not all(hasattr(item, a) for a in ("x_mm", "y_mm", "w_mm", "h_mm")):
                    continue
                anname = getattr(item, "anname", "") or ""
                # Exempt SpreadImage halves
                if SPREAD_HALF_RX.search(anname):
                    continue
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                # LEFT page: spine is on the right (x = pw_mm).
                # RIGHT page: spine is on the left (x = 0).
                spine_x = pw_mm if side == "links" else 0.0
                if side == "links":
                    distance = abs(spine_x - x1)
                else:
                    distance = abs(x0 - spine_x)
                if distance < self.inset_mm - self.tolerance_mm:
                    violations.append(Violation(
                        severity="warning",
                        rule_id=self.id,
                        message=(
                            f"frame {anname!r} on {side.upper()} page {page.label!r} "
                            f"is {distance:.2f}mm from spine; bleed will cross into the facing page. "
                            f"Use SpreadImage if intentional, or inset {self.inset_mm}mm from the spine side."
                        ),
                        targets=(anname or "<unnamed>",),
                    ))
        if unknown_pages:
            violations.append(Violation(
                severity="warning",
                rule_id=self.id,
                message=(
                    f"facing-page mode but {len(unknown_pages)} page(s) have master_name "
                    f"without 'links'/'rechts': {unknown_pages[:5]}{'...' if len(unknown_pages) > 5 else ''}"
                ),
                targets=tuple(unknown_pages[:5]),
            ))
        return violations
```

### `_UndeclaredDriftRule` (new)

```python
@dataclass(frozen=True)
class _UndeclaredDriftRule(BrandRule):
    axis_tolerance_mm: float = 5.0      # "almost aligned" upper bound
    adjacency_gap_mm: float = 12.0      # "almost stacked" upper bound
    min_drift_mm: float = 0.5           # below this = exact alignment, no warning

    def check(self, primitives, doc, constraints=None) -> list[Violation]:
        constraints = constraints or []
        # Build declared-pair set
        declared: set[frozenset[str]] = set()
        for c in constraints:
            try:
                names = c.referenced_annames()
            except Exception:
                continue
            if len(names) < 2:
                continue
            for a, b in itertools.combinations(names, 2):
                declared.add(frozenset((a, b)))
        violations = []
        for page in doc.pages:
            if page.is_master:
                continue
            items = [p for p in page.items
                     if all(hasattr(p, a) for a in ("x_mm", "y_mm", "w_mm", "h_mm"))
                     and (getattr(p, "anname", "") or "")]
            for P, Q in itertools.combinations(items, 2):
                pa, qa = P.anname, Q.anname
                if frozenset((pa, qa)) in declared:
                    continue
                bbp = _frame_bbox_mm(P, page)
                bbq = _frame_bbox_mm(Q, page)
                if bbp is None or bbq is None:
                    continue
                # Skip rotated frames — bbox math doesn't apply
                if (float(getattr(P, "rotation_deg", 0) or 0) != 0 or
                    float(getattr(Q, "rotation_deg", 0) or 0) != 0):
                    continue
                dx = abs(bbp[0] - bbq[0])
                dy = abs(bbp[1] - bbq[1])
                # Suspicious-axis test
                if self.min_drift_mm < dx < self.axis_tolerance_mm:
                    violations.append(self._mk_violation(P, Q, "x", dx, "same_x"))
                if self.min_drift_mm < dy < self.axis_tolerance_mm:
                    violations.append(self._mk_violation(P, Q, "y", dy, "same_y"))
                # Suspicious-adjacency test (P above Q)
                if bbp[3] < bbq[1]:  # P bottom < Q top
                    gap = bbq[1] - bbp[3]
                    if self.min_drift_mm < gap < self.adjacency_gap_mm and dx < self.axis_tolerance_mm:
                        violations.append(self._mk_violation(
                            P, Q, "adjacency", gap, "aligned_below",
                            extra=f"P below Q (gap {gap:.2f}mm)"
                        ))
        return violations

    def _mk_violation(self, P, Q, kind, drift, suggested, extra=""):
        return Violation(
            severity="warning",
            rule_id=self.id,
            message=(
                f"frames {P.anname!r} and {Q.anname!r} appear visually adjacent "
                f"({kind} drift {drift:.2f}mm){' ' + extra if extra else ''}. "
                f"Either declare with {suggested}({P.anname!r}, {Q.anname!r}, ...) "
                f"in CONSTRAINTS, or fix the geometry."
            ),
            targets=(P.anname, Q.anname),
        )
```

### Audit-tool report shape (Markdown)

```markdown
# audit_alignment report

## templates/zeitung-a4-grun

### Page 1 (cover, RIGHT)
- declared pairs: 0
- spine-safety candidates: 0
- undeclared adjacencies (axis-near):
  * 'Cover Hero' (x=0,y=0,w=210,h=155.6) vs 'u2950' (rotated bbox x=-4.1,y=155.6,w=220.5,h=148.6)
    → y-axis drift: 0.03mm (already aligned)
    → suggested: distance_y('Cover Hero', 'u2950', equals=0.0, name='cover_to_green_flush')
  * ...

### Page 8 (LEFT)
...
```

---

## Common Pitfalls (consolidated; full lists in research/codebase.md and research/pitfalls.md)

### Must-handle (HIGH severity)

1. **`Page.is_left` is broken** — hardcoded False at `document.py:391-393`. Use `master_name` regex (locked decision #4).
2. **6 Zeitung pages have wrong `master_name`** — pages 6, 7, 9, 11, 13 marked `links` but should be `rechts`; page 8 vice versa. Phase 2/3 fixes these BEFORE running the spine-safety rule (otherwise the rule mis-flags or misses bugs).
3. **CONSTRAINTS-into-BrandRule plumbing** — locked decision #3 (kwarg on signature). The orchestrator change is in `structural_check.check_template` — pass `mod.CONSTRAINTS` as the third arg. All 9 existing rules' signatures gain `constraints=None` for forward compatibility (no behavior change).
4. **Anchor-positioned frames** — `_frame_bbox_mm` already handles via `resolve_anchor`. Audit tool MUST use it (don't read raw `x_mm/y_mm`).
5. **Atomic PR ordering**: add new rules to `BRAND_CONSTRAINTS` BEFORE adding `brand_overrides` entries. Otherwise `meta_schema.py::_validate_and_collect_ids` warns "id not in BRAND_CONSTRAINTS".
6. **Rule count** — `test_brand_constraints.py::test_nine_rules_exact` becomes `test_eleven_rules_exact` (rename + bump count).
7. **u2950 ordering**: trim u2950 → verify clean → remove `brand_overrides[brand:inside_page]` → close #39. Reverse order = `--all` red.
8. **`P9 Spread` and `P4 Foto-Spread` rename cascade** — when migrating to `SpreadImage`, the existing `same_size("P9 Spread", ...)` constraint becomes orphan (warning). Update or drop.

### Worth knowing (MEDIUM severity)

9. **False-positive explosion of `brand:undeclared_alignment_drift`** is the #1 design risk. Defenses (already baked in): warning severity, skip rotated frames, skip anonymous frames, page-local iteration, pre-applied overrides for V1-bound + postkarte + plakat templates.
10. **SpreadImage halves intentionally touch the spine** — exempt via anname-pattern (locked decision #5).
11. **Performance** — O(N² per page); ~700 candidate pairs on 14-page Zeitung; <100ms. Fine for `--all` × 8 templates.
12. **CI integration as fatal day-1 breaks every untouched template** — wire as informational with `|| true` (locked decision #10).
13. **`bin/render-gallery` regenerates ~30 files across 3 templates** (template.sla, template-preview.sla, page-NN.png, preview.pdf, meta.yml SHA, site/public mirror).
14. **`pdfimages -list` cross-spread check** — opt-in `--check-pdf` flag for the audit tool. Catches IMAGE leaks but not polygon spine-bleed (the BrandRule covers polygons).

### Informational

15. **Polygon `custom_path`** doesn't change bbox — audit uses bbox (consistent).
16. **Master pages** — include in scan but tag `(master page)` in report.
17. **No new dependencies.**

---

## Per-template state

### `templates/zeitung-a4-grun/`

- 14 pages, facing_pages=True, ~10 primitives/page.
- Existing `CONSTRAINTS = [...]`: empty or minimal — codebase agent confirms no list today.
- Existing `meta.yml::brand_overrides`: `brand:line_spacing_0.9` (#16's reword for `brand:inside_page` referencing #39 — to be removed in this issue once u2950 is trimmed).
- 6 wrong `master_name` assignments (pages 6, 7, 9, 11, 13, 8).
- User-confirmed bugs verified at file:line:
  - Page 1: `Cover Hero` (build.py:235-256) and `u2950` (build.py:246-256, rotated 90°).
  - Page 8: `P7 Portrait` (build.py:1327-1377) and `u918`.
  - Page 10: `P9 Spread` (build.py:1802-1811) and overlapping text columns.
  - Page 11: `P10 Portrait` (build.py:1894-1902).
  - Page 12: unnamed Dunkelgrün (build.py:1952-1961).

### `templates/postkarte-a6-kampagne/`

- 2 pages, single-page (facing_pages=False, spine-safety no-op).
- Existing `CONSTRAINTS = [...]`: present (small).
- This issue: pre-apply `brand_overrides[brand:undeclared_alignment_drift]` with reason "scheduled for follow-up encoding". No CONSTRAINTS encoding.

### `templates/plakat-a1-hochformat/`

- 1 page, single-page (spine-safety no-op).
- Existing `CONSTRAINTS = [...]`: present.
- This issue: pre-apply `brand_overrides[brand:undeclared_alignment_drift]`. No CONSTRAINTS encoding.

### V1-bound templates (5)

- `wahlaufruf-postkarte-a6-quer`, `wahltag-tueranhaenger`, `themen-plakat-a3-quer`, `infostand-tent-card-a5-quer`, `kandidat-falzflyer-din-lang`.
- Pre-apply `brand_overrides[brand:undeclared_alignment_drift]` with reason "see #17/.../21 V1 layout work".
- Their V1 issues prescribe per-template `CONSTRAINTS = [...]` lists; the new rule will catch any drift then.

---

## Environment Availability

- Python 3.13.5 ✓
- `lxml`, `pyyaml`, `jsonschema`, `Pillow`, `poppler` (`pdfimages`/`pdftoppm`/`pdftotext`), `ghostscript`, `Scribus 1.6.5` — all present.
- Network: not needed.
- No new dependencies.

---

## Project Constraints

- **Round-trip faithful** is the contract for the 3 production templates. Zeitung's intentional divergence is gated by `meta.yml::sla_diff_strict: false` (#16). Phase 3's geometry edits add to that divergence.
- **Reference-SLA `previews_for_sla` SHA** is bumped automatically by `bin/render-gallery`.
- **Forbidden actions:** image-pixel inspection, visual_diff comparison, opening PDFs in a viewer for visual review. All verification is code-only.

---

## Sources (with confidence)

- **HIGH:** all interface signatures + line numbers (codebase agent verified file:line).
- **HIGH:** `Page.is_left` broken at `document.py:391-393` (pitfalls agent verified).
- **HIGH:** 6 Zeitung wrong `master_name` assignments (codebase agent grep'd build.py for `master_name=` strings).
- **HIGH:** rule count 9 → 11 (two rules added; pitfalls agent confirmed).
- **HIGH:** all user-reported bugs verified at file:line.
- **MEDIUM:** the heuristic thresholds (axis 5mm, adjacency 12mm) — judgment calls; the audit tool exposes them as CLI flags so they're tuneable.
- **MEDIUM:** locked decision #12 (defer postkarte+plakat encoding) — judgment call from token-budget pragmatism.

---

## Suggested PR shape (planner refines)

~16-18 commits across 8-10 tasks:

1. `feat(builder): extract bbox.py and template_loader.py from existing helpers` (locked decision #7 refactor)
2. `feat(brand_constraints): add BrandRule.check constraints kwarg + orchestrator pass-through` (locked decision #3)
3. `feat(brand): add brand:spine_safety rule`
4. `feat(brand): add brand:undeclared_alignment_drift rule`
5. `test(brand): bump 9-rule count to 11 + add new rules' tests`
6. `chore(templates): pre-apply brand_overrides[brand:undeclared_alignment_drift] to V1-bound + postkarte + plakat`
7. `feat(audit): add tools/audit_alignment.py and bin/audit-alignment`
8. `chore(zeitung): fix 6 wrong master_name assignments`
9. `chore(zeitung): trim u2950 + remove brand:inside_page override + close #39`
10. `feat(zeitung): convert P4 Foto-Spread and P9 Spread to SpreadImage` (with INJECT_MAP + CONSTRAINTS updates)
11. `chore(zeitung): inset spine-touching single-page frames (P1 Hero, P3 Hero, P10 Portrait, P11 Bottom, P13 Hero, page-12 unnamed)`
12. `chore(zeitung): align page-8 portrait, page-10 text-below-spread, page-11 portrait-to-column-3`
13. `feat(zeitung): encode CONSTRAINTS list with all declared adjacencies`
14. `chore(zeitung): regenerate template.sla and gallery via bin/render-gallery --skip-visual-diff`
15. `test(zeitung): update test_zeitung_overflow.py + test_sla_to_dsl.py round-trip allow-list`
16. `ci(pages): add bin/audit-alignment as informational step`
17. `docs: SCHEMA.md §12 + SPEC-WRITING-GUIDE.md catalogue + audit-tool reference`
18. `docs(issues): execution complete`

The planner should split T-tasks fine-grained so partial completion (rules + tool + V1 overrides) is still a useful PR if the executor runs out of usage.

Next: `/issue:plan` turns this into XML-tagged tasks for the executor.
