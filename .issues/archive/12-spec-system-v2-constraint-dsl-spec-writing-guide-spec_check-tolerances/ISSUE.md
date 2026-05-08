---
id: '12'
title: 'Spec-System v2: Constraint-DSL + Spec-Writing-Guide + spec_check tolerances'
status: open
ship_state: merged
priority: high
labels:
- spec
- dsl
- architecture
source: github
source_id: 23
source_url: https://github.com/GrueneAT/vorlagen/issues/23
---

## Kontext

Mit Issue #10 (PR #20) und Issue #11 (PR #22) ist das Vorlagen-System auf 8 Templates plus
Spec-Format plus Visual-QA-Pipeline angewachsen. In der Iterations-Erfahrung der letzten
beiden Issues haben sich drei strukturelle Lücken gezeigt:

1. **Constraints leben heute in Specs als Prosa, nicht überprüfbar.** „Headlines liegen
   auf gleicher Y-Achse" steht im Spec-Markdown, aber wenn build.py die Werte um 0.5mm
   verschiebt, fällt das nur visuell auf. Multi-Model-Vision-Reviews sind teuer, langsam
   und unzuverlässig (Halluzinationen, Stilbias). Strukturelle Eigenschaften wie
   Alignment, Symmetrie, Hierarchie, Containment sollten **deterministisch im Code
   prüfbar** sein.
2. **Brand-CI-Regeln sind heute implizit.** Der CD-Quickguide (`shared/brand/CD-
   Quickguide.pdf`) definiert harte Regeln (M=0.06×kurze-Kante, Logo=3×M, „Typografie
   immer auf Grün", Schriftgröße×0.9 Zeilenabstand). Aktuell muss Reviewer:in das im
   Kopf haben — das skaliert nicht.
3. **Spec-Schreiben ist ad-hoc.** Es gibt SCHEMA.md (Format) aber keinen
   How-to-Guide („welche Fragen MUSS eine Spec beantworten? welche Sektionen sind
   Pflicht? wie schreibt man jeden Abschnitt gut?"). Aus Issue #10/#11 sind
   Erfahrungen entstanden, was in Specs typischerweise unklar/lückenhaft ist —
   das Wissen sollte explizit dokumentiert sein.

Plus eine kleinere Aufgabe aus dem Issue-#10-Post-Merge-Audit:
4. **`tools/spec_check.py` Toleranzen** — heute zu strikt (1mm), flagged sub-mm-
   Refinements aus den Build-Loop-Iterationen als „drift" obwohl es Normalverhalten
   ist. Tolerance-Tuning nötig.

Diese vier hängen zusammen — sie bilden zusammen „Spec-System v2".

## Scope (eine konsolidierte Lieferung, vier Sub-Bereiche)

### A — Constraint-DSL als Single Source of Truth

**Single source of truth:** Constraints leben **ausschließlich im Code** (build.py).
Spec-Markdown beschreibt Intent in Prosa, referenziert Constraints per Name, dupliziert
aber keine Daten. Damit unmöglich zu drift'en.

Zwei sich verstärkende Mechanismen:

**(1) Composite-Blöcke** erzwingen Constraints konstruktiv (Verstoß API-unmöglich):
- `AlignedRow(y_mm=N)` — Kinder teilen y_mm
- `AlignedColumn(x_mm=N)` — Kinder teilen x_mm
- `MirroredPair(left, right, axis_mm)` — symmetrisches Paar
- `EqualGapStack(gap_mm, axis)` — Kinder gleichmäßig verteilt
- `GridCell(grid, row, col)` — Koordinaten aus Grid abgeleitet
- `HierarchyBlock(headline, subline, body)` — Schriftgröße-Reihenfolge erzwungen

**(2) Free-form Constraints** für Fälle ohne passenden Composite:
```python
CONSTRAINTS = [
    same_y(themen_h1, themen_h2, themen_h3),
    mirrored_x(p4_back, p6_back, axis_mm=148.5),
    inside(qr_code, panel_closer),
    same_style(headline_a, headline_b),
    distance_y(headline, subline, equals=baseline_x*2),
    equal_gap(themen_thumbs, axis="y", gap_mm=8),
]
```

**(3) Brand-Constraints** automatisch aus `shared/ci.yml` + Quickguide-Notes:
- `logo_size: logo.width == M*3` (print) / `M*2.5` (digital), `M = 0.06 × kurze_kante`
- `text_on_green: brand_typography.background ∈ {Dunkelgrün, Hellgrün}`
- `line_spacing: text.linesp == text.fontsize × 0.9`
- `hl_sl_spacing: distance_y(headline, subline) == X*2`
- `color_palette: all_colors ∈ ci.yml palette`
- `font_family: all_fonts ∈ {Gotham Narrow Ultra/Book, Vollkorn Black Italic}`
- `bleed: trim has 3mm bleed all sides`
- `spot_naming: spot_colors_named ∈ {Falz, Stanzkontur}`

**Validation:** `tools/structural_check.py` importiert build.py, läuft build, geht
über emittierte Primitives, evaluiert CONSTRAINTS-Liste + Brand-Constraints.
Failures gehen nach stderr + non-zero exit. CI fail bei Verstoß.

**Migration:** alle 8 existierenden Templates auf Composite-Blöcke + CONSTRAINTS-
Listen umgestellt. Bestehende build.py-Tests bleiben grün.

### B — Spec-Writing-Guide

Neuer Authoring-Guide unter `shared/brand/SPEC-WRITING-GUIDE.md` (oder
`templates/_specs/`). Klärt:

**Welche Fragen MUSS eine Spec beantworten** — strukturiert nach Pflicht/Empfohlen/
Optional:

*Funktional (Pflicht):*
- Zielgruppe? Verwendungs-Situation?
- Hauptbotschaft? Lesbarkeits-Kriterium (1-Sek-Test)?
- Welche Aktion(en) sollen Empfänger:innen ausführen?
- Druck-Output (Format, Materialität, Stanzform, Falz)?

*Visuell (Pflicht):*
- Layout-Philosophie?
- Hierarchie-Order?
- Hero-Brand-Farbe + Akzente?
- Typo-Mischung?
- Wahlkreuz mit Hintergrund-Vertrag?
- Bilder Pflicht/optional/verboten?
- Whitespace-Charakter?

*Strukturell (Pflicht):*
- Trim + Bleed + Falz/Stanze in mm
- Slot-Liste: anname, Position, Maße, Style-Ref, Pflicht/optional, Max-Chars
- Lese-Reihenfolge
- Cross-Element + Cross-Page Beziehungen (in Prosa, Code-Constraint-Refs)

*Constraints-Sektion (Pflicht):*
- Prosa-Beschreibung WAS gilt + WARUM
- Verweis auf Code-Constraints per Name (`siehe CONSTRAINTS["themen_row_alignment"]`)
- Brand-Constraints-Abweichungen (falls Template bewusst lockert)

*Druckpraxis (Empfohlen):*
- Spot-Colors verwendet
- Min-DPI für Bilder
- Druckerei-Anforderungen

*Endnutzer:innen-Workflow (Empfohlen):*
- Welche Slots werden am häufigsten ersetzt?
- Welche Slots dürfen NICHT angefasst werden?
- Geschätzter Anpassungs-Aufwand
- Realistische Text-Längen
- Beispieltexte

*Robustheit (Optional):*
- Verhalten bei Übertext-Slot
- Layout-brechende Slot-Combos
- Anti-Patterns / häufige Fehler

*Provenance (Optional):*
- Owner, Review-Datum, Version

Plus pro Sektion: Mini-Anleitung + Beispiel aus den 8 existierenden Specs +
Anti-Pattern.

Plus: Worked example (ein Slot-Layout in der Spec → Code-Constraint mit benanntem
Identifier → Spec-Prosa die darauf verweist → was der Constraint-Checker prüft).

Plus: Review-Checkliste (10-15 Fragen vor Implementation-Freigabe).

Plus: Common pitfalls aus Issue #10/#11.

### C — Alignment-Konvention im SCHEMA.md dokumentieren

Update `templates/_specs/SCHEMA.md` um die neue Constraint-Konvention:
- Wie Specs die `constraints:`-Sektion in Prosa schreiben (NICHT als parallele YAML)
- Wie Verweise auf Code-Constraints per Name funktionieren
- Welche Brand-Constraints automatisch aktiv sind und nicht in der Spec wiederholt
  werden müssen

### D — `tools/spec_check.py` Tolerance-Tuning

Aktuell strikt 1mm-Toleranz für Slot-Position-Drift. Sub-mm-Refinements aus Build-Loop-
Iterationen werden als drift geflagged obwohl Normalverhalten. Reduzieren auf:
- 0.5mm Toleranz für Slot-Position
- Drift unter Toleranz: **info-only** (nicht-blocking)
- Drift über Toleranz: **error**
- Plus: Spec versioniert Slot-Position als Floats mit 1 Dezimalstelle (statt Integer-mm)
  damit Spec-Source-of-Truth präzise sein kann

## Constraints

- **Backwards-compatibility:** Refactor existierender Templates auf Composite-Blöcke
  darf SLA-Output NICHT ändern (Round-Trip-Diff bleibt grün auf den 3 production-
  Templates; previews_for_sla SHA stabil auf den 5 neuen).
- **Composite-Blöcke** kommen als Erweiterung in `tools/sla_lib/builder/blocks.py`
  bzw. neuem `tools/sla_lib/builder/composites.py` — keine Brüche an existierender
  Public API (`__init__.py`).
- **Constraint-Identifiers** (Namen wie `themen_row_alignment`) müssen über Templates
  hinweg konsistent benannt werden wo zutreffend (cross-template Vokabular).
- **Spec-Writing-Guide** folgt selbst dem eigenen Schema (meta-konsistent).
- **Kein Claude-Branding** in Code/Specs/Commits/Tools.
- **Bestehende Tests** bleiben grün; neue Tests für Composite-Blöcke + structural_check
  + brand-constraint-evaluator.
- **CI-Performance:** structural_check soll <5s pro Template laufen — Constraint-
  Evaluation darf nicht zum Bottleneck werden.

## Acceptance Criteria

- [ ] **Constraint-DSL — Composite-Blöcke**: AlignedRow, AlignedColumn, MirroredPair,
      EqualGapStack, GridCell, HierarchyBlock als `@dataclass`-Composites mit
      `emit(self, page) -> Iterable[primitive]` API. Min. 6 unit-tests pro Block.
- [ ] **Constraint-DSL — Free-form Constraints**: same_y/same_x/same_size,
      mirrored_x/mirrored_y, inside, same_style, distance_y/x, equal_gap,
      hierarchy als Funktionen die zu module-level CONSTRAINTS-Liste hinzugefügt
      werden. Min. 4 unit-tests pro Constraint.
- [ ] **Brand-Constraints aus ci.yml + Quickguide-Notes** abgeleitet, automatisch
      auf jedes Template angewandt. Min. 8 globale Brand-Constraints (Liste in §A).
- [ ] **`tools/structural_check.py`** existiert, importiert build.py-Module, läuft
      Build, walkt Primitives, evaluiert CONSTRAINTS + Brand-Constraints, gibt
      strukturierten Markdown-Report aus, exit 0 bei Pass / 1 bei Fail.
- [ ] **Wired into `bin/validate`** — CI failed bei Constraint-Verletzung auf
      jedem Template.
- [ ] **Refactor der 8 existierenden Templates** auf Composite-Blöcke wo passend +
      CONSTRAINTS-Listen für free-form. SLA-Output bleibt byte-stabil (round-trip
      grün, previews_for_sla SHA unverändert).
- [ ] **Spec-Writing-Guide** unter `shared/brand/SPEC-WRITING-GUIDE.md` mit allen
      Sektionen aus §B; selbst dem eigenen Schema folgend.
- [ ] **SCHEMA.md** aktualisiert mit Constraint-Verweis-Konvention (§C).
- [ ] **`tools/spec_check.py` Tolerance-Tuning** (§D) — 0.5mm Toleranz, info/error-
      Trennung, Spec-Slot-Floats statt Integers, mit Tests.
- [ ] **Visual review pass** über alle 8 Templates nach Refactor — keine sichtbaren
      Regressionen vs. main-state.
- [ ] **CI green** — alle Tests passing, structural_check green, spec_check green,
      check-stale-previews green.

## Risiken & Open Questions

- **Composite-Block-API-Form** — wie elegant lässt sich `AlignedRow` mit dem
  bestehenden `page.add(...)`-Pattern integrieren? Discuss-Phase entscheidet.
- **Brand-Constraint-Identifier-Schema** — wie referenzieren Specs Brand-
  Constraints per Name? Globaler Namespace vs. namespacing.
- **Refactor-Aufwand der 8 Templates** — pro Template ca. 30-60 min Aufwand, plus
  Test-Verification. Insgesamt ~1 Tag Refactor-Arbeit.
- **Identifizier-Resolution** — Constraints in build.py referenzieren Frame-Objekte
  per Variable; wie werden sie in `tools/structural_check.py` aufgelöst? Vor
  oder nach `page.add()`?
- **Brand-Constraint-Override-Mechanismus** — wenn ein Template bewusst Brand-Regel
  bricht (z.B. monochrome poster ohne Grün-Akzent), wie elegant überschreiben?

## Phasenvorschlag

1. **Phase 1 — Constraint-DSL Design** (discuss + plan)
   - API für Composite-Blöcke (form, naming, integration mit page.add)
   - API für free-form Constraints (Funktionen vs. Klassen, Identifier-Auflösung)
   - Brand-Constraint-Schema (was wird auto-extracted aus ci.yml/Quickguide-Notes)
   - Override-Mechanismus
2. **Phase 2 — DSL-Implementierung**
   - Composite-Blöcke + Tests
   - Free-form Constraints + Tests
   - Brand-Constraint-Evaluator + Tests
   - tools/structural_check.py + CI-Wiring
3. **Phase 3 — Template-Refactor**
   - Pro Template (8 total): Composite-Use + CONSTRAINTS-List
   - Round-trip / SHA-Stabilität verifizieren
4. **Phase 4 — Spec-Writing-Guide + SCHEMA-Update + spec_check-Tuning**
   - Guide-Dokument
   - SCHEMA-Update
   - spec_check Toleranzen
5. **Phase 5 — Review + Ship**
   - Final visual review (Spot-check, jetzt deutlich kleiner weil Constraint-Layer
     viel abdeckt)
   - PR + Merge

## Dependencies

- Issue #10 (gemerged) — DSL-Foundation, blocks-Pattern
- Issue #11 (gemerged) — Demo-Content-Framework, codex_image_gen, qr_gen, pyzbar,
  Pillow als reguläre Deps. CI-Fix für Production-Templates-not-rebuilding.
- `shared/brand/CD-Quickguide.pdf` + `shared/brand/QUICKGUIDE-NOTES.md` (gemerged in #11) —
  Quelle für die 8 Brand-Constraints.
