# Research Synthesis — 12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances

Synthesized 2026-05-08 from two parallel research streams + post-rebase verification.

**Pre-analysis note:** The worktree was originally based on stale main (before PRs #20/#22/#25/#26/#27). After rebase onto current `origin/main`:
- `tools/sla_lib/builder/library.py` is present (from #13)
- All 3 production templates have `def build_template()` + `def build_preview()` (from #13's split)
- Codebase research's "module-level execution" finding is now obsolete — corrected below.

**Confidence: HIGH** for foundational decisions. Three corrections to CONTEXT.md emerge from research.

---

## Corrections to CONTEXT.md

### Correction to D2 — Free-form Constraint identifier resolution

**Original D2 implication:** structural_check resolves frame references via Python `id()`.

**Corrected:** `id()`-based resolution **breaks** when authors construct frames inline (`page.add(TextFrame(...))`). The Python object created inline doesn't survive past `page.add()` because `Page.add()` calls `emit()` immediately (verified `tools/sla_lib/builder/document.py:124-134`).

**Two-part fix:**
1. **Construct-then-add convention** documented in SPEC-WRITING-GUIDE: always do
   ```python
   p1_headline = TextFrame(...)   # construct
   page.add(p1_headline)          # THEN add
   CONSTRAINTS = [same_y(p1_headline, p2_headline, p3_headline)]
   ```
2. **structural_check warns on orphan refs** — a Constraint references a frame that's not in the emitted primitives. Catches authors who break the convention.

**Composite blocks** must use `dataclasses.replace(child, y_mm=...)` not in-place mutation, so that free-form CONSTRAINTS referencing the same children continue to resolve correctly. Verified ecosystem.md §2.

### Correction to D5 — Constraint resolution: anname-based, not id()

After ecosystem §2 and codebase mechanics, **the cleanest resolution mechanism is by `anname` matching**, not Python `id()`. Reasons:
- `anname` is the user-facing identifier already, used in spec slot tables, gallery, `tools/spec_check.py`
- Survives the `page.add() → emit()` pathway (anname is on the emitted primitive)
- IDE-friendly enough — anname strings match a known set per template

**Constraint API (revised):**
```python
# Variables hold Frame objects locally for IDE convenience
p1_headline = TextFrame(anname="P1 Headline", x_mm=15, y_mm=30, ...)
page.add(p1_headline)

# CONSTRAINTS reference by anname (string) for resolution stability
CONSTRAINTS = [
    same_y("P1 Headline", "P2 Headline", "P3 Headline", name="themen_row_y"),
    inside("QR-Code", "Panel-Closer"),
]
```

OR keep variable references as syntactic sugar that under-the-hood reads `frame.anname`:
```python
CONSTRAINTS = [
    same_y(p1_headline, p2_headline, p3_headline, name="themen_row_y"),
]
# constraint records frames' anname at construction time, looks up by anname later
```

**Decision (locks revised D2/D5):** allow BOTH forms. `same_y(*frames)` accepts either Frame objects (records `.anname`) or strings (anname directly). Resolution uses `anname`.

### Correction to D9 — `themen-plakat-a3-quer` is the right Phase 2 vorzeige

Codebase agent verified: ~13 emitted primitives (the simplest of the 5 new templates), natural `AlignedRow` for the 3-column belege grid (lines 130 + 152 in current build.py). API can be calibrated on this template; refactor target produces SHA-stable SLA bytes (or minimal documented shift).

### New: D13 — Unified `build_doc()` import contract for structural_check

The 8 templates today have asymmetric entry points:
- 5 new: `def build(out_path) -> None` (writes file, no return)
- 3 production (post-#13): `def build_template() -> Document`, `def build_preview() -> Document`

`structural_check.py` needs to import a build module and get a `Document` back **without filesystem side effects**. Solution: add `def build_doc() -> Document` to all 8 templates as the canonical structural-check entry point.

- For 5 new templates: refactor `build(out_path)` to call `build_doc()` then save: `def build(out_path): build_doc().save(out_path)`. `build_doc()` returns the Document.
- For 3 production templates: alias `build_doc = build_template`. (`build_preview` is the gallery-render path; structural_check focuses on `build_template` because constraints apply to the clean end-user template.)

Backward-compatible: `if __name__ == "__main__"` blocks unchanged.

---

## Summary

A medium-large issue. New module `tools/sla_lib/builder/structural_check.py` (~200 LoC), new module `tools/sla_lib/builder/brand_constraints.py` (~150 LoC, 8 rules), new module `tools/sla_lib/builder/composites.py` (~250 LoC, 6 composite blocks). Plus free-form constraint primitives (~150 LoC). Plus one DSL extension: `Document.iter_all_primitives()` (small additive method). Plus refactor of 8 templates' build.py for `build_doc()` contract and Phase-2 vorzeige composite-use. Plus `tools/spec_check.py` tolerance tuning. Plus `shared/brand/SPEC-WRITING-GUIDE.md`.

Backward-compat: SLA bytes byte-stable across all 8 templates. CI: +15-20s. No new runtime deps; `hypothesis` proposed test-only.

---

## Codebase Touchpoints (verified post-rebase)

| File | Lines | Role |
|---|---|---|
| `tools/sla_lib/builder/__init__.py` | additive | export new composites + constraint factories + `iter_all_primitives` |
| `tools/sla_lib/builder/primitives.py` | unchanged | base classes, `_Frame`, `TextFrame`, `ImageFrame` |
| `tools/sla_lib/builder/blocks.py` | unchanged | existing live blocks pattern (`@dataclass + emit()`) |
| `tools/sla_lib/builder/composites.py` | NEW (~250 LoC) | `AlignedRow`, `AlignedColumn`, `MirroredPair`, `EqualGapStack`, `GridCell`, `HierarchyBlock` |
| `tools/sla_lib/builder/constraints.py` | NEW (~150 LoC) | factory functions: `same_y`, `same_x`, `same_size`, `mirrored_x/y`, `inside`, `equal_gap`, `hierarchy`, `same_style`, `distance_y/x` |
| `tools/sla_lib/builder/brand_constraints.py` | NEW (~150 LoC) | 8 brand-rule predicates per CONTEXT D3, plus `BRAND_CONSTRAINTS` module-level list |
| `tools/sla_lib/builder/structural_check.py` | NEW (~200 LoC) | orchestrator: imports build module, runs `build_doc()`, walks primitives, evaluates constraints, emits markdown report |
| `tools/sla_lib/builder/document.py` | small additive | `Document.iter_all_primitives() -> Iterable[primitive]` walking master pages, layers, groups |
| `tools/sla_lib/tests/test_composites.py` | NEW | unit tests per composite |
| `tools/sla_lib/tests/test_constraints.py` | NEW | unit tests per free-form constraint |
| `tools/sla_lib/tests/test_brand_constraints.py` | NEW | unit tests per brand rule |
| `tools/sla_lib/tests/test_structural_check.py` | NEW | integration test on synthetic build + on themen-plakat |
| `tools/spec_check.py` | edit | tolerance 0.1mm → 0.5mm (codebase verified actual default — ISSUE.md says 1mm but real default is 0.1mm). Add info/error severity. Float-coordinates accepted in YAML schema. |
| `templates/_specs/SCHEMA.md` | edit | section on `constraints:` prose convention; floats accepted in slot table |
| `shared/brand/SPEC-WRITING-GUIDE.md` | NEW (~2500 words German) | per ecosystem §5 structure |
| `templates/themen-plakat-a3-quer/build.py` | edit (vorzeige) | `build_doc()` factor + use 2× AlignedRow + CONSTRAINTS list |
| `templates/<other-7>/build.py` | edit (Phase 3) | `build_doc()` contract + composites where natural + CONSTRAINTS lists |
| `templates/<all-8>/meta.yml` | maybe edit | `brand_overrides:` list per template if rules need explicit waiver (research expects 4-5 templates need overrides) |
| `.github/workflows/pages.yml` | tiny edit | run `tools/sla_lib/builder/structural_check.py` per template after `tools/check_ci.py` |

### `<interfaces>` for new modules

```python
# tools/sla_lib/builder/composites.py

@dataclass
class AlignedRow:
    """Children share y_mm. emit() returns iterable of children with y forced."""
    y_mm: float
    children: list[Frame]
    name: str = ""  # optional, for structural_check identification
    
    def emit(self, page) -> Iterable:
        for child in self.children:
            forced = dataclasses.replace(child, y_mm=self.y_mm)
            yield forced

@dataclass
class AlignedColumn:
    """Children share x_mm."""
    x_mm: float
    children: list[Frame]
    name: str = ""
    def emit(self, page) -> Iterable: ...

@dataclass
class MirroredPair:
    """Two children mirrored around vertical or horizontal axis."""
    left: Frame
    right: Frame
    axis_mm: float
    axis: str = "x"  # "x" = vertical mirror, "y" = horizontal mirror
    name: str = ""
    def emit(self, page) -> Iterable: ...

@dataclass
class EqualGapStack:
    """Children spaced uniformly along axis."""
    gap_mm: float
    children: list[Frame]
    axis: str = "y"  # "y" = vertical stack, "x" = horizontal
    start_mm: float = 0.0
    name: str = ""
    def emit(self, page) -> Iterable: ...

@dataclass
class GridSpec:
    """Defines a grid: page-aware columns/rows + gutter + margin."""
    cols: int
    rows: int
    gutter_mm: float = 10.0
    margin_mm: float = 12.0
    page_w_mm: float = 0.0  # auto-fill from page
    page_h_mm: float = 0.0

@dataclass
class GridCell:
    """A child positioned at (row, col) of a grid."""
    grid: GridSpec
    row: int
    col: int
    child: Frame
    span_cols: int = 1
    span_rows: int = 1
    def emit(self, page) -> Iterable: ...

@dataclass
class HierarchyBlock:
    """Headline > Subline > Body with enforced font-size descending order."""
    headline: TextFrame
    subline: TextFrame | None
    body: TextFrame | None
    name: str = ""
    def emit(self, page) -> Iterable: ...
    # raises ConstraintViolation if fontsize_headline <= fontsize_subline
```

```python
# tools/sla_lib/builder/constraints.py

@dataclass(frozen=True)
class Constraint:
    """Base: a structural assertion over emitted primitives."""
    name: str  # human-readable
    targets: tuple[str, ...]  # anname strings
    
    def check(self, primitives: dict[str, Primitive]) -> list[Violation]:
        """Return list of Violation messages. Empty = pass."""

# Factory functions return Constraint subclasses
def same_y(*targets: str | Frame, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def same_x(*targets: str | Frame, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def same_size(*targets: str | Frame, axis: str = "both", tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def mirrored_x(left: str | Frame, right: str | Frame, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def mirrored_y(top: str | Frame, bottom: str | Frame, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def inside(child: str | Frame, parent: str | Frame, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def equal_gap(*targets: str | Frame, axis: str = "y", gap_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def hierarchy(*targets: str | Frame, by: str = "fontsize", name: str = "") -> Constraint: ...
def same_style(*targets: str | Frame, name: str = "") -> Constraint: ...
def distance_y(a: str | Frame, b: str | Frame, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...
def distance_x(a: str | Frame, b: str | Frame, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint: ...

# All accept either string anname or Frame object (extracts .anname)
```

```python
# tools/sla_lib/builder/brand_constraints.py

@dataclass(frozen=True)
class BrandRule:
    id: str  # canonical id e.g. "brand:logo_size_3M"
    name: str  # human-readable
    description: str  # what it checks, citing Quickguide
    severity: str = "error"  # "error" | "warning" | "info"
    
    def check(self, doc: Document, primitives: list[Primitive]) -> list[Violation]: ...

BRAND_CONSTRAINTS: list[BrandRule] = [
    rule_color_palette_only(),
    rule_font_family_only(),
    rule_line_spacing_factor_0_9(),
    rule_hl_sl_distance_x2(),
    rule_logo_size_3M(),
    rule_text_on_green(),
    rule_bleed_3mm(),
    rule_wahlkreuz_colored_bg(),
]
```

```python
# tools/sla_lib/builder/structural_check.py

@dataclass
class CheckIssue:
    severity: str  # "error" | "warning" | "info"
    rule_id: str
    message: str
    location: str  # e.g. "templates/foo/build.py CONSTRAINTS[2]"

@dataclass
class TemplateReport:
    slug: str
    constraint_issues: list[CheckIssue]
    brand_issues: list[CheckIssue]
    
    @property
    def has_errors(self) -> bool: ...
    
    def to_markdown(self) -> str: ...

def check_template(slug: str) -> TemplateReport:
    """Import templates/<slug>/build.py, call build_doc(), walk primitives,
    evaluate template's CONSTRAINTS list + BRAND_CONSTRAINTS, return report."""

def main(argv: list[str] | None = None) -> int:
    """CLI: structural_check <slug>... | --all. Exit 1 on any error."""
```

```python
# tools/sla_lib/builder/document.py — additive

class Document:
    def iter_all_primitives(self) -> Iterable[Primitive]:
        """Walk all pages, master pages, and groups. Returns flat iterable
        of primitives with their anname (where set)."""
```

### `<interfaces>` for the build_doc() contract (D13)

```python
# templates/<slug>/build.py — uniform pattern

def build_doc() -> Document:
    """Return the constructed Document (no save). Called by structural_check."""
    doc = Document(...)
    # ... build composition
    return doc

def build(out_path: str | Path = HERE / "template.sla") -> Path:
    """Build + save. Existing CLI entry point for end users."""
    doc = build_doc()
    doc.save(out_path)
    return Path(out_path)

# Production templates:
def build_template() -> Document:
    """Clean version, no library demo content."""
    return build_doc()

def build_preview() -> Document:
    """Gallery preview, with library demo content injected."""
    doc = build_template()
    # inject library content
    return doc

if __name__ == "__main__":
    build()  # for new templates
    # or both for production:
    # build_template().save(HERE / "template.sla")
    # build_preview().save(HERE / "template-preview.sla")
```

---

## Brand-rule sketches (8 rules)

Per codebase agent: 4-5 rules will surface KNOWN drift on the 8 templates. Plan needs `meta.yml.brand_overrides:` discipline.

| Rule | Predicate | Drift expected? |
|---|---|---|
| `brand:color_palette` | every primitive's fcolor/pcolor ∈ {Black, White, Registration, Dunkelgrün, Hellgrün, Gelb, Magenta} ∪ template-local spot colors (Falz, Stanzkontur) | None expected |
| `brand:font_family` | every TextFrame/Run uses `Gotham Narrow Ultra/Book` or `Vollkorn Black Italic` (per ci.yml) | Türanhänger uses an Italic — possibly drift |
| `brand:line_spacing_0.9` | every paragraph style: `linesp == fontsize × 0.9 ± 0.1` | Türanhänger headline drift expected |
| `brand:hl_sl_distance_x2` | for templates with HL+SL pair (style names match `ci/h*` and `ci/sub*`): distance_y == X × 2 | Türanhänger drift expected |
| `brand:logo_size_3M` | M = 0.06 × kurze_kante; Logo (anname matches "Logo*") width == 3M (or 2.5M for digital) ± 0.5mm | 3 of 8 templates over tolerance |
| `brand:text_on_green` | every TextFrame using a brand style that has fcolor != white must sit on a green-fill polygon or page background. (Approximation: if fcolor == white, the immediate background should be Dunkelgrün/Hellgrün.) | 4 of 8 templates have body-on-white — expected to flag |
| `brand:bleed_3mm` | document config bleed = 3mm all sides | None expected |
| `brand:wahlkreuz_colored_bg` | any block using `WahlkreuzSymbol` has its `background_color` field ∈ {Dunkelgrün, Hellgrün, Magenta} | None expected (D12 already enforced from #10) |

**Override mechanism:** `meta.yml.brand_overrides: ["brand:logo_size_3M", "brand:hl_sl_distance_x2"]` — each entry must have an explanation comment in YAML. structural_check skips listed rules for the template, but logs the skip in the report.

---

## spec_check tolerance update (D8 corrected)

**Codebase verification:** ISSUE.md says "today 1mm" — actual default in `tools/spec_check.py:178` is **0.1mm**. ISSUE.md inaccurate.

Decision: target **0.5mm** for both the floor and the info/error split:
- < 0.05 mm → silent (within Pillow/Scribus rounding, not informative)
- 0.05 mm – 0.5 mm → **info** (logged but non-blocking)
- > 0.5 mm → **error** (CI fail)

Plus: spec YAML accepts floats with 1 decimal place (e.g. `x_mm: 12.5`).

---

## Spec-Writing-Guide content (D6)

Target: `shared/brand/SPEC-WRITING-GUIDE.md`, ~2500 German words. Structure per ecosystem §5:

1. **Purpose** — wer schreibt Specs, wie werden sie gelesen
2. **Pflicht-Sektionen** (must-have)
   - Funktional: Audience, Use-case, CTA, Druck-Output
   - Visuell: Layout-Philosophie, Hierarchie-Order, Brand-Akzente, Hero-Color
   - Strukturell: Trim/Bleed/Falz mm, Slot-Tabelle, Lese-Reihenfolge
   - Constraints (Prosa): wie referenziert Spec die CONSTRAINTS list im build.py
3. **Empfohlen-Sektionen**
   - Druckpraxis (Spot-Colors, Min-DPI, Druckerei-Anforderungen)
   - Endnutzer:innen-Workflow (welche Slots häufig ersetzt, welche nie)
4. **Optional-Sektionen**
   - Robustheit (Übertext-Verhalten, häufige Fehler)
   - Provenance (owner, version)
5. **Wie schreibt man jeden Abschnitt gut?** — Mini-Anleitung + Beispiel + Anti-Pattern
6. **Construct-then-add Konvention** — wichtig für CONSTRAINTS list, mit Beispiel
7. **Worked example** — eine Slot-Beschreibung in der Spec → Code-Constraint mit benanntem Identifier → Spec-Prosa die per Name referenziert
8. **Review-Checklist** — 10-15 Fragen vor Implementation-Freigabe
9. **Common pitfalls** — aus Erfahrung mit #10/#11/#13

---

## Backward-Compat Anchoring (D10)

Recipe per ecosystem §7:

```bash
# Pre-refactor: capture SHAs
for slug in $(ls templates/ | grep -v _smoke); do
    sha256sum templates/$slug/template.sla
done > /tmp/pre-refactor-shas.txt

# Post-refactor:
python3 templates/<slug>/build.py
sha256sum templates/<slug>/template.sla
# Must match pre-refactor SHA. If different, structural_check is OK
# but the bytes drifted — investigate composite emit() ordering or
# dataclasses.replace() handling.
```

For 3 production templates, additionally:
```bash
python3 tools/sla_diff.py --strict --allow-brand-extras \
  --left "<slug>-original.sla" --right "templates/<slug>/template.sla"
# Must remain green (critical=0).
```

`bin/check-stale-previews` enforces this in CI via `meta.yml::previews_for_sla`.

---

## CI Integration

`.github/workflows/pages.yml` — add structural_check after existing brand-validator:

```yaml
- name: Run structural check
  run: |
    set -euo pipefail
    for tdir in templates/*/; do
      slug=$(basename "$tdir")
      [ "$slug" = "_smoke" ] && continue
      python3 -m sla_lib.builder.structural_check "$slug" || exit 1
    done
```

Performance budget per ecosystem §10: Zeitung is largest (~870 primitives), structural_check + brand_constraints ≈ 1s. 8 templates × ~1s = ~8s additional. Within <30s total CI overhead per ecosystem §1.

---

## Standard Stack (verified)

| Tool | Version | Status |
|---|---|---|
| Python | 3.13 | unchanged |
| jsonschema | 4.26.0 | already installed (#11/#13) |
| Pillow | 12.2.0 | unchanged |
| qrcode[pil] | 8.2 | unchanged |
| pyzbar | 0.1.9 | unchanged |
| **hypothesis** | latest | **NEW (test-only, optional via `pytest.importorskip`)** |

No new runtime deps.

---

## Don't Hand-Roll

- **Don't write a constraint solver.** Predicates over emitted primitives are sufficient.
- **Don't add Brand-rule registry-via-decorator.** Direct list in `BRAND_CONSTRAINTS` matches `BLOCKS` pattern (open-closed via list extension).
- **Don't add `iter_all_primitives` walking by hand each call.** Cache the walk in `Document` if performance demands.
- **Don't write a spec linter from scratch.** Extend existing `tools/spec_check.py` with float-aware tolerance.
- **Don't reinvent slot-anname-resolution.** Use the existing `anname` discipline that `tools/spec_check.py` already follows.

---

## Architecture Patterns (locked)

1. **Pure-metadata constraints** — `CONSTRAINTS` list and `BRAND_CONSTRAINTS` are PURE-METADATA. They influence validation, never SLA bytes. Refactor PR must produce byte-identical output across all 8 templates.
2. **One module per concern** — `composites.py` (constructive), `constraints.py` (free-form), `brand_constraints.py` (brand-level), `structural_check.py` (orchestration). Co-located in `tools/sla_lib/builder/` so import cycles are avoidable.
3. **Anname is the universal identifier** — used by spec_check, library, anyway; structural_check picks it up.
4. **Iter-all-primitives is the orchestration anchor** — single walking method on Document that everyone consumes.
5. **`build_doc()` contract** — uniform import target for any tool that needs the structured Document without filesystem effects.
6. **Severity buckets** — error / warning / info / silent, per ecosystem §6.
7. **Override discipline** — meta.yml.brand_overrides with mandatory comment, jsonschema-validated.

---

## Common Pitfalls (top 10)

| # | ID | Risk | L | I | Mitigation |
|---|---|---|---|---|---|
| 1 | P-INLINE-FRAME | Authors construct Frame inline `page.add(TextFrame(...))` → CONSTRAINTS reference dies | HIGH | HIGH | SPEC-WRITING-GUIDE documents construct-then-add convention; structural_check warns on orphan refs |
| 2 | P-COMPOSITE-MUTATION | Composite emit() mutates child in-place, breaks free-form constraints referencing same child | MEDIUM | HIGH | Use `dataclasses.replace()` not in-place mutation in composites.py |
| 3 | P-SHA-DRIFT | Refactor causes SLA bytes to change | MEDIUM | HIGH | Deterministic emit ordering; pre-vs-post SHA compare in CI; per-template gate |
| 4 | P-BRAND-DRIFT-DISCOVERY | brand_constraints surfaces 4-5 templates with KNOWN drift; PR fails CI | CONFIRMED | MEDIUM | Phase-3 work includes brand_overrides per affected template with explanation comments |
| 5 | P-IDENTIFY-LOGO | Logo identification by anname pattern fails for templates that don't follow "Logo *" convention | LOW | MEDIUM | Codebase agent confirmed all 8 follow the convention. Verify per template in Phase 3. |
| 6 | P-PROD-IMPORT-SIDE-EFFECTS | Old production templates execute at module level; importlib triggers save | RESOLVED | HIGH | Already fixed by #13 (build_template/build_preview split present after rebase) |
| 7 | P-ITER-PRIMITIVES-MISSING | `Document.iter_all_primitives()` doesn't exist | CONFIRMED | LOW | Add as small method in Phase 1; tests inline |
| 8 | P-SPECCHECK-MISMATCH | spec_check.py default 0.1mm not 1mm; ISSUE wrong | CONFIRMED | LOW | Targeted fix to 0.5mm + info/error split per D8-corrected |
| 9 | P-COMPOSITE-NAMING | Composites in blocks.py vs new composites.py module | LOW | LOW | New `composites.py` per RESEARCH; blocks.py stays for non-composite blocks |
| 10 | P-HYPOTHESIS-DEP | Adding hypothesis as test dep breaks containers without it | LOW | LOW | Test-only via `pytest.importorskip("hypothesis")`. Optional. |

---

## Plan Inputs (what PLAN.md must absorb)

1. **One small DSL extension**: `Document.iter_all_primitives()` method
2. **Three new modules**: `composites.py`, `constraints.py`, `brand_constraints.py`
3. **One new orchestrator**: `structural_check.py` + CI wiring
4. **Refactor of all 8 templates**: `build_doc()` contract (5 new templates need new function; 3 production aliased)
5. **Phase 2 Vorzeige**: themen-plakat-a3-quer composite refactor with SHA-stable assertion
6. **Phase 3 fan-out**: 7 remaining templates
7. **`tools/spec_check.py` tolerance tuning**: 0.1mm → 0.5mm + info/error
8. **Updates to `templates/_specs/SCHEMA.md`** — constraints prose convention, float-aware slot table
9. **New `shared/brand/SPEC-WRITING-GUIDE.md`** — ~2500 German words
10. **Tests**: composites, constraints, brand_constraints, structural_check, plus property tests via hypothesis (test-only dep)
11. **CI workflow**: structural_check step
12. **Backward-compat verification**: pre-vs-post SHA + production round-trip

## Phase Order

1. **Phase 1 — DSL Foundation**
   - `Document.iter_all_primitives()`
   - `composites.py` + tests
   - `constraints.py` + tests
   - `brand_constraints.py` + tests (8 rules)
   - `structural_check.py` + tests
   - JSON schema for `meta.yml.brand_overrides:` (extend library.py validator or add new)
2. **Phase 2 — `build_doc()` contract on all 8 templates** (additive only, no SLA bytes change)
   - 5 new templates: extract `build_doc()` function
   - 3 production templates: alias `build_doc = build_template`
   - Tests pass; SHA-stable
3. **Phase 3 — Themen-Plakat vorzeige**
   - Refactor with composites; add CONSTRAINTS list; SHA-stable
   - Validate API, document any rough edges
4. **Phase 4 — Brand-Constraint discovery + override application**
   - Run structural_check on all 8; record drift
   - Add `brand_overrides` to affected meta.yml files with explanation
   - Round-trip diff still green
5. **Phase 5 — Fan-out: refactor 7 remaining templates**
   - Each template: composite-use where natural + CONSTRAINTS list + meta.yml overrides
   - SHA-stable per template
6. **Phase 6 — spec_check tolerance + SCHEMA + SPEC-WRITING-GUIDE**
   - tools/spec_check.py tolerance to 0.5mm + info/error
   - templates/_specs/SCHEMA.md update
   - shared/brand/SPEC-WRITING-GUIDE.md author
7. **Phase 7 — CI integration + Final verify**
   - .github/workflows/pages.yml step
   - All tests + structural_check + spec_check + sla_diff green
   - Visual review (single pass): SHA-stable confirms no visual regression
8. **Phase 8 — Ship + merge**
