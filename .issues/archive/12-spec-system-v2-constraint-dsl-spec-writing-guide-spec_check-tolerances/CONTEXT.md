# Design Decisions — 12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances

Captured 2026-05-08. Locked decisions binding for research, plan, execute.

## Decisions (locked)

### D1. Composite-Block API: Container-Style

```python
# Composites are blocks emitting iterable of primitives, like existing PageBackground.
# Container variant accepts children at construction:
page.add(AlignedRow(y_mm=30, children=[
    TextFrame(x_mm=15, w_mm=80, h_mm=10, anname="P1 Headline", style="ci/h2"),
    TextFrame(x_mm=110, w_mm=80, h_mm=10, anname="P2 Headline", style="ci/h2"),
    TextFrame(x_mm=205, w_mm=80, h_mm=10, anname="P3 Headline", style="ci/h2"),
]))
# At emit time: AlignedRow's emit() forces y_mm=30 on every child, regardless of
# what was passed. Constraint enforced by construction.
```

**Available composites (Phase A):**
- `AlignedRow(y_mm, children)` — children share y
- `AlignedColumn(x_mm, children)` — children share x
- `MirroredPair(left, right, axis_mm)` — symmetric pair around vertical/horizontal axis
- `EqualGapStack(gap_mm, axis="y"|"x", children)` — children spaced uniformly
- `GridCell(grid, row, col, child)` — coords derived from grid-spec
- `HierarchyBlock(headline, subline, body)` — guarantees fontsize ordering

**Begründung:** Konsistent mit bestehendem `PageBackground.for_page()` Pattern.
Container-Style ist deklarativ; Constraints werden zum API-Vertrag, nicht zur
nachträglichen Verifikation. Composites erscheinen als single-`page.add()`-Call,
saubere visual semantics in build.py.

### D2. Free-form Constraint-Identifier: Direkte Variable-Referenzen

```python
# In build.py:
p1_headline = TextFrame(x_mm=15, y_mm=30, w_mm=80, h_mm=10, anname="P1 Headline", style="ci/h2")
p2_headline = TextFrame(x_mm=110, y_mm=30, w_mm=80, h_mm=10, anname="P2 Headline", style="ci/h2")
p3_headline = TextFrame(x_mm=205, y_mm=30, w_mm=80, h_mm=10, anname="P3 Headline", style="ci/h2")
page.add(p1_headline)
page.add(p2_headline)
page.add(p3_headline)

CONSTRAINTS = [
    same_y(p1_headline, p2_headline, p3_headline),
    mirrored_x(p4_back, p6_back, axis_mm=148.5),
    inside(qr_code, panel_closer),
    distance_y(headline, subline, equals=20.0),  # 20mm
]
```

`structural_check.py` walkt die emittierten primitives nach `python3 build.py` und
matched über Object-Identity (`id(frame)` of constructed-but-emitted Frames is
stable within a single build run). CONSTRAINTS list ist module-level — `import
build; build.CONSTRAINTS` für structural_check.

**Begründung:** Native Python idioms, IDE-completion, Tippfehler bei Identifier-
Refactoring direkt sichtbar. Strings als anname-Refs wären weniger refactor-
sicher.

**Identifier-Auflösung:** structural_check.py importiert build.py als Modul, ruft
`build.build_template()` (oder ähnlich) das die Frames als Side-Effekt emittiert,
sammelt CONSTRAINTS list. Frame-Objekte werden über ihre `id()` (Python object
identity) wiedergefunden. Funktioniert weil derselbe Frame-Object beide in
`page.add(frame)` UND in CONSTRAINTS auftaucht.

### D3. Brand-Constraints automatisch via structural_check.py

```python
# tools/sla_lib/builder/brand_constraints.py — module-level rules
BRAND_CONSTRAINTS = [
    rule_color_palette_only(),
    rule_font_family_only(),
    rule_line_spacing_factor_0_9(),
    rule_hl_sl_distance_x2(),
    rule_logo_size_3M(),
    rule_text_on_green(),  # for brand typography styles
    rule_bleed_3mm(),
    rule_wahlkreuz_colored_background(),  # D12 from #10
]

# tools/sla_lib/builder/structural_check.py
def check_template(slug):
    build_module = importlib.import_module(f"templates.{slug}.build")
    doc = build_module.build_template()  # or build_preview()
    primitives = list(doc.iter_all_primitives())
    
    # Apply BRAND_CONSTRAINTS automatically
    for rule in BRAND_CONSTRAINTS:
        violations = rule(primitives, doc)
        report_violations(slug, rule.id, violations)
    
    # Apply template's own CONSTRAINTS list
    for constraint in getattr(build_module, "CONSTRAINTS", []):
        violations = constraint.check(primitives)
        report_violations(slug, constraint.id, violations)
```

**Override-Mechanismus:** `meta.yml` darf `brand_overrides: [rule-id1]` haben um
spezifische Brand-rules für ein Template zu deaktivieren (mit Begründung in YAML
comment). Defaults greifen auf jedes Template ohne explizite Deklaration.

**Begründung:** Templates müssen NICHTS deklarieren um brand-konform zu sein —
das ist die Grundannahme. Override ist explicit-opt-out, nicht implicit-opt-in.

### D4. Migration-Reihenfolge: DSL-Lib first, dann Vorzeige-Template, dann skalieren

**Phase 1 — DSL-Foundation:**
- Composite-Blocks (AlignedRow, AlignedColumn, MirroredPair, EqualGapStack, GridCell, HierarchyBlock)
- Free-form Constraint primitives (same_y, same_x, same_size, mirrored_x/y, inside, distance_y/x, equal_gap, hierarchy, same_style)
- Brand-Constraints module mit ~10 Regeln aus Quickguide
- structural_check.py orchestrator
- Wired into bin/validate

**Phase 2 — Vorzeige-Template (themen-plakat-a3-quer):**
- Refactor 1 Template (simpelster Layout: 3-Spalten-Argumentation)
- Validate die Composite-API auf realer Anwendung
- Eventuelle API-Anpassungen
- Visual-Regression-Test: gerendetes PNG byte-identisch zu vor-Refactor

**Phase 3 — Restliche 7 Templates (4 neue + 3 production):**
- Pro Template: Composite-Use wo passend, CONSTRAINTS für free-form
- Round-trip diff bleibt grün auf 3 production-Templates
- Visual-PNG byte-identisch (oder mit dokumentierter Verbesserung)

**Phase 4 — Spec-Writing-Guide + SCHEMA-Update + spec_check tolerances:**
- shared/brand/SPEC-WRITING-GUIDE.md
- templates/_specs/SCHEMA.md update mit constraint-prosa-Konvention
- tools/spec_check.py 0.5mm Toleranz + info-vs-error Trennung

**Phase 5 — Review + Ship**

**Begründung:** Vorzeige-Refactor (Phase 2) liefert real-world API-Validation
bevor Breite. Iteration auf einem Template kostet 30-60 min; auf 8 Templates 4-8h.
Frühe Korrektur spart spätere Schmerzen.

### D5. Constraint-Naming und ID-Konventionen

Jeder Constraint hat:
- **Implicit ID** (Python identifier of the variable holding the Constraint object), e.g. `themen_row_alignment = same_y(...)`
- **Optional name kwarg** für structural_check-Output, defaults to inferred from constructor args
- **Source-line in build.py** für Trace-Output bei Violation

```python
themen_row_alignment = same_y(p1_headline, p2_headline, p3_headline,
                              name="themen_row")
CONSTRAINTS = [themen_row_alignment, ...]
```

Brand-Constraints haben statische IDs:
- `brand:color_palette` → only ci.yml palette
- `brand:font_family` → only Gotham/Vollkorn
- `brand:line_spacing_0.9`
- `brand:hl_sl_distance_x2`
- `brand:logo_size_3M`
- `brand:text_on_green`
- `brand:bleed_3mm`
- `brand:wahlkreuz_colored_bg`

Templates referenzieren Brand-IDs in `meta.yml.brand_overrides:` Liste.

### D6. Spec-Markdown beschreibt Constraints in Prosa

```markdown
## Layout Constraints

The 3 themen-headlines on the inner spread share the same y-axis to read as
a triadic argument. The two back panels are mirrored around the fold center
to remain legible when folded. See CONSTRAINTS list in build.py for the
machine-checkable form.

Brand constraints all standard apply (no overrides).
```

Spec-Markdown referenziert CONSTRAINTS by name (`themen_row_alignment`) wo
nützlich. Spec-Writing-Guide (§B Liefergegenstand) dokumentiert die Konvention.

### D7. structural_check.py Output-Format

Markdown report (matching visual_review.py style):

```markdown
# structural_check report

## templates/themen-plakat-a3-quer

### CONSTRAINTS
- ✓ themen_row_alignment (same_y on 3 frames)
- ✗ inside(qr_code, panel_closer): qr_code at (245, 195) is OUTSIDE panel_closer (210-300, 200-280)

### BRAND_CONSTRAINTS
- ✓ brand:color_palette
- ✓ brand:font_family
- ✗ brand:logo_size_3M: logo width 18mm, expected 17.82±0.5mm (M=5.94 × 3 = 17.82)

Result: 2 violations, 8 passes
```

Exit-code: 0 if all passes, 1 if any violation. CI-friendly.

### D8. spec_check.py tolerance-tuning

- Slot-Position-Toleranz: 1mm → **0.5mm**
- Drift unter Toleranz → **info-only** (current message style + drift-mm dokumentiert)
- Drift über Toleranz → **error** (exit 1, current behavior)
- Spec-YAML akzeptiert `x_mm: 12.5` (float, 1 dec) statt nur `x_mm: 12` (int)

### D9. Vorzeige-Template-Auswahl: themen-plakat-a3-quer

Begründung:
- Simpelste Layout-Struktur unter den 5 neuen Templates (3-Spalten-Argumentation)
- Wenige Slots (~10) → schnelle Iteration auf Composite-API
- Round-Trip-frei (DSL-original) → kein Risiko auf Production-Diff
- Hat schon gute visuelle Hierarchie → Constraints werden klar (same_y auf 3 stat-Headlines, hierarchy Block für Headline > Subline > Body)

### D10. Backward-Compatibility — kein SLA-Output-Drift

Refactor-PR muss SLA-Bytes byte-identisch lassen (alle 8 Templates'
`previews_for_sla` SHA unverändert). Composite-Blöcke emittieren dieselben
Primitives wie heute manuell konstruiert. structural_check.py + CONSTRAINTS-
Lists sind PURE-METADATA — beeinflussen Output nicht.

Acceptance-Test: vor-Refactor SHA == nach-Refactor SHA für alle 8 templates.

### D11. CI-Performance: <5s pro Template für structural_check

structural_check importiert build.py (cached after first run), walkt primitives
(in-memory list iteration), evaluiert constraints (each constraint is a Python
predicate over primitives). Should be <1s per template typically. CI total <30s
für 8 templates.

### D12. spec_check und structural_check sind komplementär

- **spec_check**: Slot-table-vs-Build drift (anname-existence, position, dimensions). Datafocus.
- **structural_check**: Constraint-violations (same_y, brand-rules). Behavior-focus.

Beide laufen in CI über `bin/validate`. Beide schreiben markdown-Reports unter
`reports/` für Debug.

---

## Claude's Discretion (research/plan can decide)

- **Composite-Block-class hierarchy**: shared base class `Composite(emit())` vs. duck-typing
- **Constraint-class hierarchy**: dataclass per primitive vs. shared `Constraint(check())` interface
- **Brand-rule extensibility**: how a future template-author adds a new brand-rule. Plugin-via-decorator vs. config-file.
- **Spec-Writing-Guide-Sektionen Granularität**: pro Template-Kategorie unterschiedliche Pflicht-Sektionen?
- **Visual-Regression-Test**: byte-comparison vs. perceptual-diff (existing tools/visual_diff.py).
- **Override-Granularität in meta.yml**: per brand-rule-id vs. per slot vs. per page.
- **spec_check delta-output**: only-show-diff vs. always-show-all-slots.

---

## Deferred (out of scope)

- Brand-rules editor UI
- Constraint-language extensions (e.g. arithmetic expressions, conditional rules)
- Auto-fix mode (constraint detects violation → suggests/applies fix to build.py)
- Constraint inheritance (template inherits constraints from parent template)
- Visual-Linting (constraints over rendered PNGs, not SLA primitives)
- Performance optimizations beyond <5s/template target
- Migration of templates/_smoke/ legacy templates

---

## Cross-References

- Issue #11 (gemerged) — Demo-Image-Framework, library, watermark
- Issue #13 (gemerged) — Centralized library, scale_type=0, crop_focus
- DESIGN-SYSTEM-BRIEF (gemerged) — Quickguide-Referenz, Prompt-Patterns für Claude Design
- Quickguide rules (in shared/brand/QUICKGUIDE-NOTES.md) — Source-of-truth für brand_constraints.py
- Memory: `feedback_no_claude_attribution`, `feedback_review_in_execute_phase`
