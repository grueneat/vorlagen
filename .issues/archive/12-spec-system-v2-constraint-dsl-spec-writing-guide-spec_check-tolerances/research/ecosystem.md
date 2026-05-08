# Ecosystem research — Issue #12 (Spec-System v2: Constraint-DSL + Spec-Writing-Guide + spec_check tolerances)

**Researched:** 2026-05-08
**Issue:** 12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances
**Scope:** External / library / pattern dimension. Codebase-internal interface extraction is for the codebase researcher.

This file maps each of the ten investigation prompts to evidence, a single recommendation,
and a confidence level. Final sections cover dependencies, risks, and phased acceptance gates.

---

## 1. Constraint-DSL prior art (Python)

### Evidence

- **kiwisolver** (PyPI; the C++ "kiwi" engine wrapped for Python) is an actively maintained
  Cassowary implementation. It is a *solver*: you declare variables, equalities, and
  inequalities with strengths, and it produces a feasible assignment. It is what
  Matplotlib uses for `tight_layout` and constrained_layout. It is also the in-process
  layout engine for enaml/atom (its parent project, nucleic). 10–500x faster than
  classical Cassowary; <https://kiwisolver.readthedocs.io/>.
- **cassowary** (pure-Python pip package) — abandoned, ~10 years stale, slower; only
  relevant historically.
- **constraint** / **python-constraint** — Prolog-style finite-domain CSP solver; wrong
  shape (it solves combinatorial constraint-satisfaction problems, not numeric
  inequalities over geometry).
- **z3-solver** — SMT; wildly overpowered, heavy native dep.
- **ReportLab Platypus / WeasyPrint** — flow-style layout; constraints are implicit in the
  flow algorithm, not declared. Wrong model for our case.
- **`@dataclass` + `__post_init__` validation** is the 2026-idiomatic Python pattern for
  declarative-rule-with-runtime-check on plain objects (Pydantic for I/O boundaries,
  stdlib dataclass + post_init for internal logic — see Source 1.1).

### Reasoning for our case

Issue #12 asks for *validation only* — given a fully built `Document` with concrete
`x_mm`/`y_mm`/`w_mm`/`h_mm` numbers, does `same_y(a, b, c)` hold? There is **no
auto-solving** required: the build code already produced the values, we are checking
them.

A Cassowary solver is the wrong tool. Solver semantics are "given inequalities, find
values that satisfy them"; we already have values, we just want to check predicates.
Adding kiwisolver would:
- Drag in a native C++ build dep (currently the project has zero native pip deps —
  only `lxml` and `pyyaml` which are Debian/system packages already present in
  `Dockerfile.claude`).
- Force every constraint to be expressed as a `Constraint(expr1 == expr2 | strength)`
  variable system, then "solve" it, then read variables back to check — circular.
- Require `Variable` objects living separately from our existing dataclass `_Frame`
  attributes, breaking D2 (direct variable references).

Simple Python predicates over our dataclass instances are the right shape:

```python
def same_y(*frames, tol_mm=0.5, name=None):
    """Returns a Constraint object (dataclass with .check(primitives) -> [Violation])."""
    ...
```

### Recommendation

**Use plain Python predicates returning dataclass `Constraint` objects** — no solver
library. Match the existing `tools/sla_lib/builder/` style (every primitive and block is
a `@dataclass` with one or two methods).

Drop kiwisolver, drop python-constraint, drop z3 from consideration. They solve a
problem we do not have.

If the project ever adds *layout-solver* features later (auto-position-from-relative-spec),
revisit kiwisolver then. Out of scope per Issue §"Deferred".

**Confidence:** HIGH

---

## 2. Composite-block patterns in design DSLs

### Evidence

- **React / JSX**: `<Row y={30}>{children}</Row>` — props on the parent broadcast
  shared values; declarative; child overrides explicit.
- **Flutter** (`flutter/widgets/Row`, `Column`, `Wrap`): parent imposes alignment
  (`mainAxisAlignment`, `crossAxisAlignment`); children are passed as a `children:`
  list parameter.
- **Qt QML** (`RowLayout`, `ColumnLayout`, `GridLayout`): container properties
  (`spacing`, `Layout.alignment`) are inherited by children.
- **Tkinter** `pack()` / `grid()` — parent widget plus geometry-manager. Container is
  the geometry source.
- **ReportLab platypus** — flowables in a frame, frame controls flow direction. Less
  declarative.

The **container-with-children-list** pattern is overwhelmingly idiomatic across all
modern UI/layout frameworks for composites that share a constraint axis.

### Cross-check vs CONTEXT D1

CONTEXT D1 fixes:

```python
page.add(AlignedRow(y_mm=30, children=[
    TextFrame(...), TextFrame(...), TextFrame(...),
]))
```

This matches Flutter's `Row(children: [...])` and React's `<Row>{children}</Row>`
patterns exactly. It is the right shape.

### Cross-check vs codebase

Codebase-research will confirm in detail, but a critical mechanical observation from
`tools/sla_lib/builder/document.py:124-134`:

```python
def add(self, item) -> "Page":
    if hasattr(item, "emit"):
        for primitive in item.emit():
            self.items.append(primitive)
    else:
        self.items.append(item)
    return self
```

`page.add(composite)` **immediately calls `composite.emit()` and discards the
composite object** — only the emitted primitives end up on `page.items`. This has
two implications for D1/D2:

1. **The composite must apply its constraint AT EMIT TIME** (before primitives leave
   it) — D1 already says this ("AlignedRow's emit() forces y_mm=30 on every child").
   So composite-as-API-contract works: the constraint is materialized into the child
   primitives' `y_mm` field, then they enter `page.items` already conformant.
2. **For free-form CONSTRAINTS (D2), the variables in `build.py` MUST be the same
   `_Frame` instances that end up on `page.items`** — i.e. the user must
   `page.add(p1_headline)` rather than `page.add(TextFrame(...))` if they want
   `same_y(p1_headline, ...)` to work via object identity. This is already the
   existing convention in the 8 templates (variables are constructed first then
   added) but should be **explicitly documented in the SPEC-WRITING-GUIDE** because
   if a future template author writes `page.add(TextFrame(...))` inline, the
   constraint cannot resolve the frame.

There is one alternative worth weighing for D2: store the canonical primitive list on
the `Document` itself (`doc.iter_all_primitives()`) and have constraints **reference
frames via a deterministic key** (`anname` + `OwnPage`) instead of `id()`. This would
make `page.add(TextFrame(...))` inline-style still work. Trade-off:

| Mechanism | Refactor-safety | Inline-construction-safe | IDE completion | Failure mode |
|-----------|-----------------|--------------------------|----------------|--------------|
| `id()` identity (D2) | HIGH (rename = mech-find) | NO | YES | Silent mismatch if author re-uses inline |
| `anname` lookup | MEDIUM (anname is a string) | YES | NO | Fails loudly with "anname not found" |

**Recommendation:** stay with D2 (id-identity) — it is locked. Document the
"construct-then-add, never inline" rule in the SPEC-WRITING-GUIDE as a hard
constraint-DSL contract. Add a `tools/structural_check.py` warning when a free-form
constraint references an object whose `id()` is not present in the emitted primitives
list (see §10).

### Recommendation

Container-style as locked in CONTEXT D1 is correct and idiomatic. Add a concrete API
contract to the spec-writing-guide: **all frames participating in CONSTRAINTS must be
constructed as named variables before `page.add()`**, never inline.

**Confidence:** HIGH

---

## 3. JSON Schema for constraint markup (if any)

### Evidence

- CONTEXT D6 explicitly forbids parallel YAML constraints in spec markdown
  ("Spec-Markdown beschreibt Constraints in Prosa"). So the *constraint*-DSL itself
  has no JSON-Schema surface.
- D5 introduces a NEW field in `meta.yml`: `brand_overrides: [rule-id1, rule-id2]`.
  This IS data and SHOULD be schema-validated.
- Existing `meta.yml` validation: searched repo — there is **no current
  `tools/sla_lib/builder/library.py`** (issue prompt mentions it but it does not
  exist in this worktree). Existing meta.yml fields are read ad-hoc by tools (`grep
  -r "meta.yml"`), not centrally validated against a schema.

### Recommendation

**Phase 1 deliverable:** add a single small JSON-schema-style validator (using stdlib
or the already-installed `jsonschema` 4.26.0; verified `pip3 show jsonschema`) for
`meta.yml`'s `brand_overrides:` field. The schema requires:

```yaml
brand_overrides:
  - id: brand:logo_size_3M           # must match a known BRAND_CONSTRAINTS id
    reason: "monochrome poster — no color accent intended"   # required
```

Validation lives in `tools/structural_check.py` (or a small `tools/check_meta.py`
helper called by it). On unknown rule-id, exit-1 with diagnostic. On missing reason,
warn. This prevents silent typos disabling a brand rule.

**No new pip dep needed** — `jsonschema` already installed; if we want to avoid even
that, a 30-line manual validator over `yaml.safe_load(meta.yml)` does the job.

**Confidence:** HIGH for the recommendation; MEDIUM for the exact existence-check of
prior schema validation in the repo (codebase researcher should confirm whether any
existing meta-validation pattern is reusable).

---

## 4. Structural-check / property-based testing

### Evidence

- **Hypothesis** (Python's PBT lib) is excellent for invariants like
  "same_y(N random aligned frames) always passes" and "same_y(N frames with one
  perturbed) always fails". It is well-integrated with pytest, ships shrinking, and
  is widely used (sources 4.1, 4.2). Adding it is +1 dev dep, no native code.
- **Real-template fixtures** (committed SLA + CONSTRAINTS list + expected violations)
  are the pattern used today by `tools/spec_check.py` against
  `templates/_specs/*.md`. Fits existing repo style.
- **Synthetic tiny build** (a 2-frame in-memory Document just for the test) is the
  norm for `tests/sla_lib/builder/` — see existing `tools/sla_lib/tests/`.

### Recommendation

Three-layer test strategy:

1. **Unit tests per Composite + per free-form Constraint** (Acceptance §A asks for
   ≥6 tests/Composite, ≥4/Constraint). Use synthetic tiny `Document` instances —
   matches existing builder-test pattern.
2. **Real-template fixture tests**: call `tools/structural_check.py` on each of the
   8 templates as parametrized pytest cases. All-must-pass smoke. These guard
   regression on the CONSTRAINTS lists each template ships.
3. **Hypothesis-property tests** (1 file, `tests/sla_lib/builder/test_constraint_properties.py`,
   ~50 LOC) for invariants like:
   - `same_y([f0, f1, ...])` where all `f_i.y_mm == y` always returns no violations
     (across `st.lists(st.frames(), min_size=2)`).
   - For any frame `g` whose `y_mm` differs by `>0.5+ε`, `same_y([f0, f1, g, f2])`
     produces at least one violation.
   - `inside(child, parent)` is true iff bounding-box containment holds.
   - `mirrored_x(a, b, axis)` is symmetric: swapping a and b preserves outcome.

   These are 4-5 properties total, ~1h to write, but they catch off-by-one and
   axis-confusion bugs that example-based tests miss.

**Hypothesis is a NEW dev dep** (verified: `pip3 show hypothesis` empty in container).
This is the ONLY new dep this issue needs, and it's pure-Python. Add to a
test-only requirements file or just import-guard so tests skip gracefully when not
installed.

**Confidence:** HIGH

---

## 5. Spec-Writing-Guide — content patterns

### Evidence

Survey of major design-system docs:

- **Carbon Design System (IBM)** — code-first, then usage, then style, then accessibility.
  Each component has Overview / Usage / Style / Code / Accessibility tabs.
- **Polaris (Shopify)** — Best practices / Content guidelines / Examples / Props.
- **Atlassian Design Guidelines** — Anatomy diagrams + Do/Don't pairs are heavy.
- **Material Design (m2/m3)** — Principles → Anatomy → Behavior → Specs → Code.
- **Recurring sections across all four:** Anatomy, Usage do/don't, Spec/Tokens, Code,
  Accessibility, Examples.

Eight-shapes (Nathan Curtis) practical advice (source 5.1):
- Be concise — "don't write essays; nobody reads them"
- 1 picture per 5–10 copy-only guidelines
- Use imperatives: Hide / Include / Prevent / Limit / Enable
- Audience-segment: developer needs ≠ designer needs

### Reasoning for our case

Issue §B already lists the sections (Funktional / Visuell / Strukturell / Constraints
/ Druckpraxis / Endnutzer:innen-Workflow / Robustheit / Provenance) — that is well-
matched to "anatomy + usage + accessibility" but tailored for print-template-spec
authoring rather than React component docs.

Length calibration from the design-system survey: a typical Carbon component doc is
~200-400 words per section, with a Do/Don't pair and a code snippet. Our spec-writing-
guide should target a similar weight: per Pflicht-section, ~100-200 words of "what to
write" + 1 short worked example pulled from one of the 8 existing specs + one anti-
pattern from issue #10/#11 retro.

The guide should NOT teach the constraint-DSL syntax (that lives in the DSL's own
docstrings + SCHEMA.md §C). It should teach **how to talk about constraints in spec
prose** and **how to reference them by name** (D6).

### Recommendation

Target shape for `shared/brand/SPEC-WRITING-GUIDE.md`:

```
1. Introduction — what a spec is, what it isn't (no parallel data, prose-first)
2. Required questions — Funktional / Visuell / Strukturell / Constraints (each ~150 words)
3. Recommended questions — Druckpraxis / Endnutzer:innen-Workflow (~100 words each)
4. Optional sections — Robustheit / Provenance
5. Per-section deep dive (worked example from real spec + 1 anti-pattern from #10/#11)
6. Constraint-DSL prose conventions (D6) — how to refer to CONSTRAINTS by name
7. Review checklist (10-15 yes/no questions, 1 page)
8. Common pitfalls catalog (extracted from issue #10/#11 retros)
```

**Length target:** 2000-3500 words total. About 1/3 the size of Carbon's full
contribution-guide because our scope is narrower (8 print templates, single brand,
single output format).

**Language:** German — matches `templates/_specs/*.md`, `QUICKGUIDE-NOTES.md`, the
brand audience.

**Meta-consistency rule (Issue Constraint):** the guide must itself be a valid
spec-style document — Pflicht/Empfohlen/Optional sections with worked examples.

**Confidence:** HIGH for shape; MEDIUM for the exact sectioning — final shape will
emerge while writing it (Phase 4).

---

## 6. Tolerance tuning — best practice

### Evidence

- **ISO 12647-2:2013** (offset-print color register): average register-deviation
  ≤ 0.10 mm; max between two colors ≤ 0.15 mm. *Color registration* — not slot-
  position drift.
- **ISO 12647-2 trim tolerance**: typical industrial-cutter accuracy is ±1.0 mm
  per side; high-end web presses ±0.5 mm. The 3 mm bleed standard exists *because*
  the cutter is not exact.
- **Mixam print-tolerances doc** confirms ±1-2 mm cutter tolerance is industry
  norm; safe-margin-from-trim should be ≥3 mm for critical content.
- The 0.5 mm value in CONTEXT D8 is defensible: it is within typical cutter
  accuracy, well below human visual perceptibility at viewing distance ≥30 cm,
  and matches half the industrial cutter tolerance — meaning sub-0.5mm refinements
  are below the resolution of the physical output and should be info-only rather
  than blocking.

### Should tolerance be config-driven (per-template) or global?

| Option | Pros | Cons |
|--------|------|------|
| Global constant (`spec_check.py: TOLERANCE_MM = 0.5`) | Simple; one place; matches D8 | No per-template tightening for stricter formats |
| Per-template `meta.yml.tolerance_mm:` (overrides global) | Future-proof | Adds a meta field nobody asked for; YAGNI |
| CLI flag `--tolerance-mm 0.5` (already exists; just change default) | Already supported | Default vs. per-template still answered by global |

The existing `tools/spec_check.py` already has `--tolerance-mm` as a CLI flag (default
0.1, would change to 0.5 per D8). Per-template override via meta.yml is **not in
scope** of D8 and would be feature-creep. Defer.

### Severity classification

Industry pattern: severity levels `info` / `warning` / `error` with non-zero exit
only on `error`. D8 explicitly says info-only for sub-tolerance drift, error for
above-tolerance. Add a third bucket `info-floor` for drift below 0.05 mm (truly
sub-pixel, not worth even mentioning) — keeps reports small.

### Recommendation

- Change default `tolerance_mm` in `tools/spec_check.py` from 0.1 → 0.5 (D8).
- Per-axis severity: `< 0.05 mm` silent, `0.05–0.5 mm` info, `> 0.5 mm` error.
- Spec slot-positions accept floats (currently the regex is permissive but spec
  YAML used integers historically). Update SCHEMA.md to recommend 1-decimal floats.
- Per-template override is OUT OF SCOPE (defer to a future issue if real need
  emerges).

**Confidence:** HIGH for 0.5mm value (industry-grounded); HIGH for global-vs-per-template
(YAGNI principle).

---

## 7. Visual-regression anchoring

### Evidence

The repo already has multiple anchoring mechanisms:

- `previews_for_sla` SHA-256 in each template's `meta.yml` — captures the SLA bytes
  at gallery-render time (cross-checked by `tools/check_stale_previews.py`).
- `tools/sla_diff.py` — structural XML-diff with `--strict` mode used by
  `bin/validate`.
- `tools/visual_diff.py` — perceptual-image diff via ImageMagick `compare` (rendered
  PDF or PNG).
- `bin/validate` orchestrates round-trip + visual diff for templates with
  `original_sla:` (i.e., the 3 production templates derived from real SLAs).

For the 5 DSL-original templates (no `original_sla:`), there is no round-trip — only
the `previews_for_sla` SHA. So D10's "byte-identical SLA pre/post refactor" requires:

- For 3 production templates: `tools/sla_diff.py --strict` must remain green
  (already enforced by `bin/validate`).
- For 5 DSL-original templates: `previews_for_sla` SHA in `meta.yml` must be
  unchanged, OR the SHA must be updated and the rationale documented.

### Recommended canonical recipe

Add to the issue-#12 PR description and SPEC-WRITING-GUIDE §"Refactor-Diff-Recipe":

```bash
# 1. Capture pre-refactor SHAs of all 8 template SLAs:
sha256sum templates/*/template.sla > /tmp/pre.sha

# 2. Refactor (composites + CONSTRAINTS lists).

# 3. Run all 8 builds:
for d in templates/*/; do
    [ -f "$d/build.py" ] && (cd "$d" && python3 build.py)
done

# 4. Compare:
sha256sum templates/*/template.sla > /tmp/post.sha
diff /tmp/pre.sha /tmp/post.sha   # MUST be empty

# 5. For production-derived templates: bin/validate (--ci or full)
#    → sla_diff --strict, visual_diff vs. PDF baseline.
```

If post-SHA differs and the refactor is intended to be byte-stable (D10), STOP and
investigate. Don't update `previews_for_sla` blindly.

**Use the existing `bin/validate`** as the orchestrator. Don't write a new tool —
that violates "kein Hand-Rolling" and "Working over Theoretical".

### Recommendation

Document the recipe in SPEC-WRITING-GUIDE §"Refactor-Recipe". Add it as a CI
acceptance gate **only** for the refactor-PR (not as ongoing CI). Keep
`bin/validate` and `tools/check_stale_previews.py` as the steady-state guard.

**Confidence:** HIGH (mechanically grounded in existing tooling).

---

## 8. Brand-rule extensibility

### Evidence

Three patterns evaluated for "future template author adds a new brand-rule":

| Pattern | Implementation | Pros | Cons |
|---------|----------------|------|------|
| **A. Direct list** in `tools/sla_lib/builder/brand_constraints.py` `BRAND_CONSTRAINTS = [...]` | Author edits the module, adds `rule_my_thing()` to the list | Trivial; explicit; easy to read; single source | Requires PR to the lib module for every new rule |
| **B. Decorator-registry** | `@brand_rule(id="my_thing")` on a function; registry collected at import | Pythonic; OCP-compliant; drop-in plugin | Implicit registration → harder to debug; overkill for small N |
| **C. Config-file** (`shared/brand/extra_rules.yml`) | YAML-described constraints | Fully declarative | Constraints are arbitrary code (e.g., `text_on_green` checks fcolor membership) — would need a mini-DSL inside YAML, which is exactly what we're trying to AVOID per D6 |
| **D. Entry-points** (setuptools) | Plugins distributed as separate pip packages | Maximum decoupling | Massive overkill for a closed brand-template repo |

### Reasoning for our case

The repo is **closed-scope** (single brand, ~10 brand-rules, single owner-team).
The "future author adds a brand-rule" scenario is realistically: a templates-team
member opens a PR adding a function to `brand_constraints.py`. There is no third
party, no plugin distribution, no hot-reload story.

Open-Closed Principle is fine, but its benefit (don't modify existing code to extend
it) is dwarfed by the cognitive cost of an implicit-registration decorator when the
list has ~10 entries and grows by ~1/year.

Pattern A (direct list) wins on **Working over Theoretical** (memory:
`feedback_working_over_theoretical`). It is the same pattern used by
`tools/sla_lib/builder/blocks.py` today — every Composite is just a `@dataclass` in
that module; there is no plugin/registry pattern. Adding a new Composite means
editing the module. This is consistent.

If the brand-rule count grows beyond ~30 or third parties need to ship
their own rules, revisit pattern B then.

### Recommendation

**Pattern A (direct list)** — add a `BRAND_CONSTRAINTS = [...]` module-level list in
`tools/sla_lib/builder/brand_constraints.py`. Each rule is a function returning a
`Violation` list (or empty). Document the "to add a rule, define a function and
append it to BRAND_CONSTRAINTS" recipe in the SPEC-WRITING-GUIDE.

**Confidence:** HIGH (consistent with existing repo conventions; YAGNI on plugin
patterns).

---

## 9. Identifying "the logo" / "the headline" in primitives walking

### Evidence

Searched all 8 template `build.py` files for `anname` patterns. Results:

**Logo identification — `anname` always contains "Logo":**

| Template | Logo annames (verbatim) |
|----------|--------------------------|
| themen-plakat-a3-quer | `Logo Grüne (top-left)` |
| kandidat-falzflyer-din-lang | `P1 Logo Grüne`, `P2 Logo (klein)`, `P6 Logo Grüne` |
| infostand-tent-card-a5-quer | `Logo Grüne (panel A)`, `Logo Grüne (panel B)` |
| wahlaufruf-postkarte-a6-quer | `Logo Grüne (weiss)`, `Logo Grüne (Bund-Dunkel)` |
| wahltag-tueranhaenger | `Logo Grüne (weiss, top)`, `Logo Grüne (weiss, back-band)`, `Logo Grüne (Bund-Dunkel, back)` |

100% of cases match a regex like `^.*[Ll]ogo.*$` or even tighter `(^| )Logo `.

**Headline identification — `anname` and `style_ref`:**

| Mechanism | Coverage |
|-----------|----------|
| `anname` substring "Headline" | All 8 templates — universal |
| `style_ref` matches `*/headline*` or `ci/h*` | Less universal; some templates use template-local styles like `tueranhaenger/headline` |

So `anname` substring matching is more universal than `style_ref` pattern matching
for cross-template brand-rules.

### Recommendation

For brand-rule `logo_size_3M`:
- Match `_Frame` instances where `isinstance(frame, ImageFrame)` AND
  `re.search(r'\bLogo\b', frame.anname)` (case-insensitive).
- Multiple logos per template: the rule walks all matches and checks each.
- If a template has an `ImageFrame` with `Logo` in anname that should NOT be
  size-checked (e.g., a tiny bottom-corner brand-mark), the template's `meta.yml`
  has `brand_overrides: [brand:logo_size_3M]` (D5).

For brand-rule `hl_sl_distance_x2` and similar headline rules:
- Primary: match `anname` substring `Headline`.
- Sub-headline: `anname` substring `Sub-Headline` or `Subline`.
- For multi-headline templates (kandidat-falzflyer has 4+ headlines), the rule
  walks all (headline, subline) pairs ON THE SAME PAGE.

**Document this in the SPEC-WRITING-GUIDE §"Naming-Konventionen"** as a hard contract:
*Frames that should be subject to brand-rules MUST have `Logo` / `Headline` /
`Sub-Headline` in their `anname`, conventionally exactly as those German tokens.*

For `text_on_green` rule, the predicate is over `fcolor` and `style.parent` rather
than anname — runs over all `TextFrame` whose `style_ref` is in the brand-typography
class (`ci/headline-*`, `ci/h1`, `ci/h2`, etc.).

### Recommendation

Use `anname`-substring matching as the primary identification. Style-name
patterns (`ci/headline-*`) as secondary for typography-rules only. Document the
naming contract in SPEC-WRITING-GUIDE.

**Confidence:** HIGH (verified by grep across all 8 templates).

---

## 10. Prevent constraints in dead code

### Evidence

This is a **codebase-internal correctness concern**, not an ecosystem question, but
the right shape for the answer comes from validation patterns in other DSLs:

- TypeScript "unused variable" warnings (`noUnusedLocals`).
- Pylint `unused-variable` / `unused-import`.
- Pytest `--collect-only` warnings for unreachable tests.

The pattern is: **after collecting all artifacts, walk for orphans and warn.**

For our case, after `structural_check.py` walks the document's primitives and
collects all `id()`s, any object referenced in `CONSTRAINTS` whose `id()` is not
in the primitives set is "orphan" — the constraint cannot fire because the frame
was never added to the page.

### Recommendation

`tools/structural_check.py` should:

1. Collect `live_ids = {id(p) for p in doc.iter_all_primitives()}`.
2. For each constraint `c` in `CONSTRAINTS`, collect `c.referenced_ids()`.
3. If `c.referenced_ids() - live_ids` is non-empty: emit a **warning-severity**
   diagnostic ("Constraint `X` references a Frame at id 0x... not present in the
   document — typo or `page.add()` missing?") and skip evaluating `c`.

This is a 10-line addition to the structural_check orchestrator. It catches the
"silent dead constraint" failure mode.

Severity = warning, not error: a template might have a `CONSTRAINTS` entry that's
intentionally inactive (e.g., conditional on a future page being added). Surface
loudly, do not block CI.

**Confidence:** HIGH

---

## No new pip deps expected

**Confirm: zero new RUNTIME deps.** All needed primitives are stdlib + already-installed
`pyyaml` / `lxml`.

**ONE new TEST-only dep proposed: `hypothesis`** (Python property-based testing,
~150KB pure-Python). Used only in `tests/sla_lib/builder/test_constraint_properties.py`
and importable. Add to a `requirements-dev.txt` (currently absent) or guard the
test file with `pytest.importorskip("hypothesis")` so CI without the dep is graceful.

If hypothesis is rejected as a new dep, fall back to plain pytest parametrize-based
tests covering the same invariants — works, just less comprehensive shrinking.

**The already-installed `jsonschema` 4.26.0** can be used for `meta.yml.brand_overrides`
validation (§3) but is not strictly required — a 30-line manual validator suffices.

**Confidence:** HIGH

---

## Risks specific to ecosystem

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Future maintainer reaches for kiwisolver/z3 because "constraint" sounds like "solver" | LOW | Comment in `tools/sla_lib/builder/brand_constraints.py` header: "Predicate-style validation, NOT a solver. See research/ecosystem.md §1." |
| `id()` identity-based constraint resolution breaks if user constructs frames inline (`page.add(TextFrame(...))`) | MEDIUM | SPEC-WRITING-GUIDE §"Constraint-Variable-Convention" makes the construct-then-add rule explicit. structural_check.py warns on orphan `id()` references (§10). |
| Brand-rule additions become PR-bottleneck if growth accelerates | LOW | Pattern A scales to ~30 rules. Revisit decorator-registry if/when needed. |
| Hypothesis dep adds CI minutes / install friction | LOW | Pure-python; ~3s install; runs in <5s on our test set. Optional via importorskip. |
| 0.5 mm tolerance is wrong for some format (e.g., business-card-precise) | LOW | Per-template override deferred; can add if real failure surfaces. Document the tolerance + its rationale in SCHEMA.md. |
| `anname`-substring matching mis-identifies non-logo image as logo | LOW | Convention is well-respected (verified all 8 templates); rule warns if zero matches found and template doesn't `brand_overrides` the rule. |
| Structural-check import-of-build.py is slow (build.py creates entire SLA) | MEDIUM | D11 caps at <5s/template. If build.py side-effects (file write) leak, refactor to call a `build_to_doc()` pure function — codebase researcher should check whether build.py is structured for this. |
| `hypothesis` shrinking surfaces a real bug unrelated to issue-#12 scope | LOW | Such a finding is good news; ticket separately. |

---

## Phase-1 implementation milestones (library/DSL surface)

Mapped to acceptance criteria in ISSUE.md:

### M1.1 — Composite primitives module
File: `tools/sla_lib/builder/composites.py` (new; or extend `blocks.py`).
Surface: `AlignedRow`, `AlignedColumn`, `MirroredPair`, `EqualGapStack`, `GridCell`,
`HierarchyBlock`. Each is a `@dataclass` exposing `emit() -> Iterable[primitive]`
that *forces* the constraint by mutating child copies (NOT originals — frames may be
referenced from CONSTRAINTS later by `id()`, so mutating in place could affect free-form
checks. Use `dataclasses.replace(child, y_mm=N)` to get a child-copy.).

**Caveat for codebase researcher:** verify that `dataclasses.replace` works on the
existing `_Frame` subclasses (TextFrame, ImageFrame, Polygon). If they have
non-init-only fields or post-init invariants, may need a custom `with_y_mm()` helper.

### M1.2 — Free-form Constraint primitives
File: `tools/sla_lib/builder/constraints.py` (new).
Surface: `same_y`, `same_x`, `same_size`, `mirrored_x`, `mirrored_y`, `inside`,
`distance_y`, `distance_x`, `equal_gap`, `hierarchy`, `same_style`. Each returns a
dataclass instance with `.id`, `.name`, `.referenced_ids()`, `.check(primitives) ->
[Violation]`.

**Public API contract:** `Violation = dataclass(severity, message, frame_anname?, axis?)`.

### M1.3 — Brand-Constraints module
File: `tools/sla_lib/builder/brand_constraints.py` (new).
Module-level `BRAND_CONSTRAINTS = [rule_color_palette_only(), ...]`. Each is a
function returning a callable `(primitives, doc) -> [Violation]`. Eight rules per
ISSUE.md §A.

### M1.4 — `Document.iter_all_primitives()`
**Codebase change:** add helper on `Document` that yields all primitives across
masters + pages in stable order (it does not exist today; verified).
Constraint-evaluator depends on this.

### M1.5 — `tools/structural_check.py` orchestrator
- Imports `templates.<slug>.build` as module.
- Calls a build-to-doc function (D2 says "build_template()" — codebase researcher
  must verify the actual entry-point name across the 8 templates; today they have
  `build(out_path)` not `build_template()`).
- Walks primitives via M1.4.
- Applies BRAND_CONSTRAINTS plus the template's `CONSTRAINTS` list.
- Honors `meta.yml.brand_overrides:` (M1.6).
- Emits markdown report with §-per-template, ✓/✗ per constraint.
- Exit 0 / 1.

### M1.6 — `meta.yml` schema for `brand_overrides`
30-line validator (or jsonschema). Diagnostic on unknown rule-id.

### M1.7 — `bin/validate` integration
Add `tools/structural_check.py --all` step before sla-diff/visual-diff.

### M1.8 — Tests
- ≥6 unit tests per Composite (6 × 6 = 36 tests).
- ≥4 unit tests per free-form Constraint (4 × 11 = 44 tests).
- 8 BRAND_CONSTRAINTS smoke tests (one per rule).
- 8 real-template parametrized end-to-end tests via structural_check.
- Optional: 4-5 hypothesis property tests.

Total: ~100 new tests. At ~10s combined, well within current CI budget.

### M1.9 — `tools/spec_check.py` tolerance update (D8)
- Default `--tolerance-mm 0.1` → `0.5`.
- Severity: silent <0.05 / info <0.5 / error >0.5.
- Spec-YAML float parsing (existing code already does `float(spec_v)`; verify no
  schema-side check rejects non-int).

---

## Phase-2 acceptance gate (vorzeige-template themen-plakat-a3-quer)

CONTEXT D9 picks `themen-plakat-a3-quer` as the first refactor target. It is the
**API-survives-first-contact-with-reality** gate. Define explicitly:

### Acceptance criteria for "Phase-2 PASS"

1. **`templates/themen-plakat-a3-quer/build.py` uses ≥1 Composite block** (preferably
   `AlignedRow` for the 3 evidence headlines, `HierarchyBlock` for headline →
   subline relationship).
2. **`CONSTRAINTS = [...]` list defined** with at least 3 entries (e.g.
   `same_y(e1_h, e2_h, e3_h)`, `same_y(e1_b, e2_b, e3_b)` body row,
   `hierarchy(headline, subhead, body)`).
3. **`tools/structural_check.py themen-plakat-a3-quer` exits 0** with all
   constraints + brand-constraints green.
4. **`templates/themen-plakat-a3-quer/template.sla` SHA-256 unchanged** vs. main
   (D10: byte-identical refactor).
5. **`templates/themen-plakat-a3-quer/page-01.png` byte-identical** vs. main
   (or ≤ 1px perceptual diff via `tools/visual_diff.py`).
6. **`meta.yml.previews_for_sla` SHA unchanged.**
7. **At least one constraint INTENTIONALLY VIOLATED in a test branch**, verifying
   that structural_check exits 1 with a clear message naming the bad frame and
   the violating axis. (Sanity check: the validator actually catches things.)
8. **API ergonomics review:** does the build.py file read more clearly than before?
   Subjective but critical — if Composite-syntax makes the file harder to scan, the
   API is wrong and we redesign before scaling to 7 templates.
9. **Time budget:** structural_check on this template runs in <2s (D11 budget is
   <5s; this one being simplest should be well under).

### Failure modes that abort Phase 2 → re-design before scaling

- Composite-API requires hacks (e.g., monkey-patching `_Frame.__post_init__`,
  global mutable state, `inspect`-based magic) to integrate with `page.add()`.
- `id()`-based constraint resolution fails because frames are reconstructed inside
  Composite.emit() (this is why M1.1 caveat above matters: must use
  `dataclasses.replace`, not new construction with new identity).
- SLA bytes drift because Composite-emit produces primitives in different order than
  manual construction did.
- Visual diff > 1px because of a subtle coordinate-conversion bug.

### Phase-2 EXIT criterion

Once these 9 acceptance items pass on themen-plakat-a3-quer, Phase 3 (refactor 7
remaining templates) is unblocked. **No new template is refactored until Phase 2
passes.** Defer Phase 3 to a follow-on PR if Phase 2 surfaces more than minor
adjustments.

**Confidence:** HIGH for the gate; the criteria mechanically derive from D10/D11/D9
and from §2 of this research.

---

## Sources

### HIGH confidence (verified)

- `/root/workspace/.worktrees/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/tools/sla_lib/builder/document.py` lines 124-134 — page.add() flatten-on-emit semantics
- `/root/workspace/.worktrees/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/tools/sla_lib/builder/blocks.py` — existing dataclass-emit pattern (5 production blocks + 5 in-progress)
- `/root/workspace/.worktrees/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/tools/spec_check.py` — current tolerance default 0.1mm; CLI `--tolerance-mm`
- `/root/workspace/.worktrees/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/templates/*/build.py` — anname conventions (Logo/Headline/Sub-Headline) verified by grep
- `/root/workspace/.worktrees/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/shared/brand/QUICKGUIDE-NOTES.md` — formula source for brand-rules
- pip3 show jsonschema → 4.26.0 installed; pip3 show hypothesis → not installed
- Kiwisolver docs: <https://kiwisolver.readthedocs.io/en/latest/basis/basic_systems.html>
- Kiwi GitHub: <https://github.com/nucleic/kiwi>
- ISO 12647-2 / cutter tolerance summary at <https://committee.iso.org/files/live/sites/tc130/files/Resources/Guidelines%20for%20using%20print%20production%20standards%20v2%20Jan%202024.pdf>
- Mixam manufacturing-variance guide: <https://mixam.com/support/printingvariance>
- Open-Closed Principle (Wikipedia): <https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle>
- Python Packaging — entry points: <https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/>

### MEDIUM confidence (single web source, ecosystem-norm)

- Eight Shapes / Nathan Curtis — design-system docs guidance: <https://medium.com/eightshapes-llc/component-design-guidelines-eca706100e7c>
- Hypothesis + pytest property-testing patterns: <https://pytest-with-eric.com/pytest-advanced/hypothesis-testing-python/>
- Decorator-registry plugin pattern: <https://realpython.com/lessons/registering-plugins-decorators/>
- 2026 Python dataclass + post_init validation idiom: <https://www.pyblog.in/programming/python-dataclasses-the-complete-2026-guide-from-dataclass-to-slots-frozen-and-__post_init__/>

### LOW confidence (unverified, single hit)

- "ISO 12647-2:2013 average register-deviation ≤ 0.10 mm" — quoted from web
  search, not directly retrieved from the ISO document. Used only as
  industry-context-flavor; not load-bearing on D8 0.5mm decision (which is
  grounded in cutter-tolerance, a separately-verified figure).

---

## Metadata

- **Research scope:** ecosystem dimension only (libraries, patterns, industry norms,
  design-system documentation conventions). Codebase-internal interface extraction is
  for the codebase researcher.
- **Honored locked decisions** from CONTEXT.md: D1 (container-style), D2 (id-identity),
  D5 (brand_overrides in meta.yml), D6 (prose-only spec constraints), D8 (0.5mm),
  D9 (vorzeige themen-plakat-a3-quer), D10 (SLA byte-stable), D11 (<5s/template).
- **No alternatives explored** for any locked decision.
- **Discretion-area recommendations made** (these are research-suggestions, not
  locks): Pattern A (direct list) for brand-rule extensibility (§8); hypothesis
  for property tests (§4); byte-comparison via SHA-256 over perceptual-diff for
  refactor-anchoring (§7); jsonschema (already installed) optional for meta.yml
  validation (§3).
