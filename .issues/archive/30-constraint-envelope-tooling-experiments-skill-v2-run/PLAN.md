# Plan: Encode constraint envelope in experiment tooling + author experiments skill (v2 run)

- **Issue slug:** `30-constraint-envelope-tooling-experiments-skill-v2-run`
- **Generated:** 2026-05-10
- **Planner model:** opus
- **Worktree root:** `/root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run/`

<objective>
Ship a constraint envelope (schema + default YAML + loader/wrapper) that is enforced on every variant in `tools/experiment_render.py` (replacing the wrong "inside_page only" gate), thread the envelope plus v1 anti-examples into the hypothesis-generation prompt, author the first project-local skill at `.claude/skills/experiments/SKILL.md` (via the global `generate-skill` skill), correct the source-of-truth docs, and run a v2 experiment (`experiments/falzflyer-p2-mein-plan-v2/`) end-to-end on the **information density + form** axis with ≥10 envelope-respecting variants. The mandatory verification deliverable — Flo's voting session + dual-section corpus update — closes both this issue (#30) and issue #29's deferred T15 in one merge gate.
</objective>

<acceptance_gate>
Restated from `ISSUE.md` — all 10 must be true at merge:

1. `.claude/skills/experiments/SKILL.md` exists, authored via `generate-skill`, three-layer model + four subcommands + v1 lessons documented.
2. `experiments/_schema/constraints.schema.yaml` exists and validates with `jsonschema` Draft 2020-12.
3. `experiments/_constraints/falzflyer-default.yml` exists, lists all 16 `BRAND_CONSTRAINTS` ids + the 22 Layer-1 thresholds from `design-guide/README.md:24-46`.
4. `tools/experiment_hypothesis_gen.py` consumes envelope and threads it into the prompt (4 substitution tokens, not 2).
5. `tools/experiment_generate/prompt_template.md` includes envelope section + v1 anti-examples token + extended final-check bullet.
6. `tools/experiment_render.py` gates every variant on the envelope; failed variants logged with structured violations and dropped (mirror `inside_page` pattern).
7. `design-guide/README.md` reversed-framing paragraph committed (Layer-1 + 16 `BRAND_CONSTRAINTS` named as the experiment constraint envelope); `tools/experiment_render.py` docstrings at lines 11–14 and 135–137 also corrected.
8. `experiments/falzflyer-p2-mein-plan-v2/` v2 run rendered end-to-end with ≥10 variants, all respecting envelope (0 dropped, or all drops explicitly logged with structured violations).
9. Flo votes a v2 session, results JSON committed under `experiments/falzflyer-p2-mein-plan-v2/results/flo-<DATE>.json`.
10. `design-guide/gruene-corpus.md` amended with **two clearly-labelled sections** — v1 envelope-necessity meta-lesson (closes #29 T15) + v2 density+form top-3/bottom-3 findings (closes #30) — both with provenance. **This single deliverable closes BOTH issues.**
</acceptance_gate>

<resolved_uncertainties>

RESEARCH.md surfaced four MEDIUM-confidence items. Each is resolved here so the executor does not need to interpret.

### R1 — Multi-verb skill dispatch convention

**Resolution:** Single `SKILL.md` with positional-arg branching on `$1`. The executor's `generate-skill` invocation MUST start with a WebFetch of `https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices` to re-verify; if Anthropic has since published a separate-skill-per-verb pattern, the executor surfaces it and the planner is re-engaged. Until that fetch returns contradicting evidence, single-skill four-verb branching is what we ship.

**Rationale:** Three converging signals — ecosystem.md §1 (official docs show one-skill-many-verbs in the `pdf-processing` example), codebase.md §6 (10 globally-installed skills all single-file, no plugin API), CONTEXT decision 11 ("Each subcommand dispatches to the existing `bin/experiment-*` tools. The skill is the process-doc + entry point + dispatch layer"). `argument-hint: "[new|generate|render|capture] <experiment-id>"` puts verbs into autocomplete.

### R2 — Layer-1 row count (22 vs 21)

**Resolution:** The envelope YAML enumerates the **22** thresholds the planner counted directly from `design-guide/README.md:24-46`. Plan and code reference the table by its **line range** (`design-guide/README.md:24-46`), not by a row count, to make the artefact unambiguous and resilient to future row additions. `falzflyer-default.yml` carries `layer1:` keys matching codebase.md §7's full enumeration (22 keys).

**Rationale:** Direct file count is HIGH-confidence evidence; the issue-prose "21" and CONTEXT decision 3 "21-row table" both predate the recount and are stale by one row. Line-range citation removes ambiguity for all future readers.

### R3 — Three retained concepts' inferred envelope violations

**Resolution:** The executor MUST visually inspect each of the three v1 retained concepts' rendered PNGs (`experiments/falzflyer-p2-mein-plan/variants/<slug>/page-01.png` if present, else re-render via `bin/experiment-render falzflyer-p2-mein-plan --only <slug>`) **before** drafting the v1 anti-example tags for those three slugs (T06) and **before** re-implementing them inside the envelope (T11/T12/T13). If a PNG is missing or unreadable, the executor halts T06/T11/T12/T13 and surfaces to the planner; do NOT guess.

The planner's best-effort inferred violations, to be confirmed/overridden by the executor's visual check:

| slug | inferred primary violation | rationale source |
|---|---|---|
| `numbered-priority-list` | All 5 numerals at constant 28pt — no rank-weighted scale (the very lever v2 wants to test for hierarchy-within-density) | codebase.md §5 + variant code re-read |
| `manifesto-single-statement` | Likely a fonts/text-on-green compatibility issue (Vollkorn Black + footer band); geometry already in-envelope | codebase.md §5 |
| `asymmetric-editorial-rules` | 5 rows × 22mm = 110mm of content packed too tightly into the 130mm panel-height available — `negative_space_pct ≥ 30` likely failing (≈15% whitespace actual) | codebase.md §5 calculation |

Each retained-concept anti-example tag in T06 carries an **extra suffix**: `(concept retained, see PLAN.md T11/T12/T13 — this anti-example is the broken v1 implementation, not the idea)`.

### R4 — Where the envelope check sits in the render pipeline

**Resolution:** Pre-Scribus, post-`build_variant_front`, post-`_verify_brand_fonts` — i.e. exactly the slot `_inside_page_violations(doc)` occupies today at `tools/experiment_render.py:165` inside `_build_variant_sla`. The envelope is loaded **once per run** in `run_render` (after `_verify_brand_fonts` at line ~271, before the variant loop), passed into `_build_variant_sla` as an `envelope: Envelope` parameter, and consumed by the new `_envelope_violations(doc, envelope)` at line 165.

**Rationale:** Mirrors the existing pattern (CONTEXT decision 13 mandates "mirror the inside_page drop pattern"); the unit-test escape hatch `skip_scribus` exercises this path so envelope checks are testable without GUI Scribus; loading once amortises YAML parsing across N variants.

### R5 — Drop & regeneration policy

**Resolution:** Auto-retry **OFF** for the v2 run. CONTEXT.md (15 locked decisions) does not specify auto-retry; pitfalls.md §4 surfaces it as planner discretion. To keep the v2 deliverable scope tight and the merge gate transparent, the v2 run runs hypothesis generation **once**, drops violators, and surfaces drops in `manifest.json::_dropped` + SUMMARY.md. If <10 variants pass envelope, the executor halts and surfaces to Flo (human-review gate). The `constraints.schema.yaml` still defines `regeneration: {auto_retry_max: int, drop_threshold_pct: float}` keys (defaults `0` and `40`) so a future experiment can switch them on without schema churn — but v2 ships with `auto_retry_max: 0`.

**Rationale:** Auto-retry-with-feedback adds a non-trivial implementation surface (feedback-prompt synthesis, retry bookkeeping, the convergence-to-safety risk pitfalls.md §4 names); keeping v2 single-shot lets the v2 ranking measure what the LLMs actually emit on first attempt, which is the more honest signal for the corpus.

### R6 — Three retained concepts' axis-commitment relabel (from pitfalls.md §5 + §6)

**Resolution:** Reframe each retained concept's `axis_commitments` so **primary is density+form**, secondary axes acknowledged. Wording for each retained-concept hypothesis in v2's manifest:

- `numbered-priority-list-v2`: `axis_commitments: [density, form, hierarchy]` (primary = density: 5 items; form = list with size-graded items; hierarchy is acknowledged as inherent-to-the-form, not as the primary lever).
- `manifesto-single-statement-v2`: `axis_commitments: [density, form]` (primary = density: 1 item; form = single editorial sentence vs. list).
- `dunkelgrun-rules-between-items-v2`: `axis_commitments: [density, form]` (primary = density: item count = 3 in the re-implementation; form = thin-rule separator vs. block separator).

This is recorded in T11/T12/T13's variant manifest stub and surfaced in SUMMARY.md per pitfalls.md §5.

</resolved_uncertainties>

<skills>
Read and follow these skills during execution:

- `@/root/.claude/skills/python/SKILL.md` — MANDATORY for every `.py` file touched in T03, T05, T08, T09, T11, T12, T13. Enforces ruff + mypy. The executor invokes `Skill(command="python")` before editing any `.py`.
- `@/root/.claude/skills/generate-skill/SKILL.md` — MANDATORY for T14 (authoring `.claude/skills/experiments/SKILL.md`). The executor invokes `Skill(command="generate-skill")` at the start of T14, performs the mandatory WebFetch first, and follows the 6-step authoring workflow.

Note: `.claude/skills/` does NOT yet exist in this workspace — `experiments` will be the **first** project-local skill. The executor creates the directory.

</skills>

<context>

- Issue: @.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/ISSUE.md
- Context decisions (15 locked): @.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/CONTEXT.md
- Research synthesis: @.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/RESEARCH.md
- Codebase research depth: @.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/research/codebase.md
- Ecosystem research depth: @.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/research/ecosystem.md
- Pitfalls research depth: @.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/research/pitfalls.md

### Key files the executor will modify or read

| Path | Role |
|---|---|
| `tools/sla_lib/builder/brand_constraints.py` | Source of the 16 `BRAND_CONSTRAINTS`, `BrandRule` dataclass, `Violation` import |
| `tools/sla_lib/builder/constraints.py` | `Violation` dataclass definition |
| `tools/sla_lib/builder/structural_check.py:166-204` | Existing brand-rule loop pattern to mirror in `experiment_envelope.py` |
| `tools/experiment_render.py:11-14, 130-143, 150-208, 270-272, 289-303, 337-341` | Gate slot + drop loop + docstring reversal targets |
| `tools/experiment_hypothesis_gen.py:50, 62-77, 84-95, 231-235, 473-474, 506-528` | Token surface, role priming, `SUBJECT_METADATA`, axis vocabulary |
| `tools/experiment_generate/prompt_template.md` | 3 insertion points (lines 29/31, 54/56, ~100) |
| `tools/experiment_results.py` | SUMMARY.md surfacing site for dropped variants |
| `experiments/_schema/manifest.schema.yaml` | `_dropped` item shape extension |
| `experiments/_schema/` | New `constraints.schema.yaml` |
| `experiments/_constraints/` | NEW directory — `falzflyer-default.yml` |
| `experiments/falzflyer-p2-mein-plan/variants/` | Read-only — v1 concepts referenced for anti-examples |
| `experiments/falzflyer-p2-mein-plan-v2/` | NEW — created in T15/T16 |
| `design-guide/README.md:24-46` | Layer-1 table — additive paragraph below |
| `design-guide/gruene-corpus.md` §6 | One-line cross-reference |
| `.claude/skills/experiments/SKILL.md` | NEW — first project-local skill |
| `shared/ci.yml` | Read-only — fonts/palette source-of-truth (verify Vollkorn Black before T12) |
| `bin/experiment-generate`, `bin/experiment-render`, `bin/experiment-results` | Existing entry points; do NOT change |

### `<interfaces>` — copied verbatim from RESEARCH.md

<interfaces>
// tools/sla_lib/builder/brand_constraints.py:64-87
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"   # "error" | "warning"
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]: ...

BRAND_CONSTRAINTS: list[BrandRule]  // 16 frozen instances; registry order stable

// tools/sla_lib/builder/constraints.py — Violation shape
@dataclass
class Violation:
    severity: str       // "error" | "warning"
    rule_id: str
    message: str
    targets: tuple[str, ...] = ()

// tools/experiment_render.py:130-143 — REPLACE this function entirely (rename + extend signature)
def _inside_page_violations(doc) -> list:
    from sla_lib.builder import BRAND_CONSTRAINTS
    rule = next((r for r in BRAND_CONSTRAINTS if r.id == "brand:inside_page"), None)
    if rule is None:
        return []
    primitives = list(doc.iter_all_primitives()) if hasattr(doc, "iter_all_primitives") else []
    return [v for v in rule.check(primitives, doc) if v.severity == "error"]

// tools/experiment_render.py:289-303 — extend drop log + manifest entry
for h in hypotheses:
    slug = h["slug"]
    try:
        sla_path, violations = _build_variant_sla(hypothesis=h, exp_dir=exp_dir, scaffold=scaffold)
    except Exception as e:
        dropped.append((slug, f"build error: {e}"))
        continue
    if violations:
        messages = "; ".join(v.message for v in violations[:3])
        dropped.append((slug, f"envelope: {messages}"))   // was "inside_page"
        continue

// tools/experiment_render.py:337-341 — manifest shape (v2 schema bump adds structured violations)
manifest_out["_dropped"] = [
    {"slug": s, "reason": r, "violations": [...]} for (s, r) in dropped
]

// tools/experiment_hypothesis_gen.py:84-95 — current 2-token render_prompt; v2 extends to 4 tokens
def render_prompt(template: str, subject: str, weak_area_quote: str) -> str:
    tokens = ("subject", "weak_area_quote")
    safe = template.replace("{", "{{").replace("}", "}}")
    for tok in tokens:
        safe = safe.replace("{{" + tok + "}}", "{" + tok + "}")
    return safe.format(subject=subject, weak_area_quote=weak_area_quote)

// generate-skill — author tool, 6-step workflow
// /root/.claude/skills/generate-skill/SKILL.md
//   1. WebFetch https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices  (MANDATORY first action)
//   2. Examples-first (2-5 concrete usage examples)
//   3. Plan progressive disclosure (Level 1 frontmatter / Level 2 SKILL.md / Level 3 references/)
//   4. Initialize via scripts/init_skill.py
//   5. Edit imperatively
//   6. Validate via scripts/validate.sh (wc -w < 5000)

// .claude/skills/experiments/SKILL.md frontmatter the executor will ship
---
name: experiments
description: |
  Run constraint-envelope design experiments with pairwise voting.
  Auto-activates on /experiments <verb> where <verb> in {new, generate, render, capture}.
  Encodes the three-layer model (envelope / variation surface / implementation),
  the corpus-update merge gate, and v1's failure-mode lessons.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
argument-hint: "[new|generate|render|capture] <experiment-id>"
---
</interfaces>

</context>

<commit_format>
Format: conventional with numeric-id prefix (per `.issues/config.yaml`).
Pattern: `30: {type}({scope}): {description}`
Examples:
- `30: feat(experiments): add constraints schema + falzflyer envelope default`
- `30: fix(experiment-render): gate every variant on envelope, not inside_page only`
- `30: docs(design-guide): name Layer-1 + BRAND_CONSTRAINTS as experiment envelope`

One commit per task is the target. Use HEREDOC for multi-line bodies.
</commit_format>

<tasks>

<task id="T01" name="add-constraints-schema">
  <action>
  Create `experiments/_schema/constraints.schema.yaml`. JSON Schema Draft 2020-12, mirroring `experiments/_schema/manifest.schema.yaml` style (`$schema: "https://json-schema.org/draft/2020-12/schema"`).

  Top-level shape (use `type: object`, `additionalProperties: false` at the top level for forward-compat noise control):

  - `extends?` — string, optional, relative path to a parent envelope (e.g. `../_constraints/falzflyer-default.yml`). Used for per-experiment overrides.
  - `brand_rules` — `array of string`, `uniqueItems: true`, `enum`-restricted to the 16 known ids (`brand:color_palette`, `brand:font_family`, `brand:line_spacing_0.9`, `brand:hl_sl_distance_x2`, `brand:logo_size_3M`, `brand:text_on_green`, `brand:bleed_3mm`, `brand:wahlkreuz_colored_bg`, `brand:inside_page`, `brand:spine_safety`, `brand:bleed_coverage`, `brand:image_text_overlap`, `brand:cover_extent_match`, `brand:visual_adjacency_drift`, `brand:image_fills_frame`, `brand:band_consistency` — from `tools/sla_lib/builder/brand_constraints.py:1525-1680`).
  - `layer1` — `object`, properties = the 22 keys enumerated in research/codebase.md §7 (`body_min_pt`, `caption_impressum_min_pt`, `body_line_length_chars`, `headline_size_jump_x`, `headline_max_words`, `body_contrast_ratio`, `display_contrast_ratio_18pt_plus`, `type_families_per_panel`, `type_sizes_per_panel`, `alignment_systems_per_panel`, `negative_space_pct`, `dominant_element_optical_weight_pct`, `face_crop_fill_pct`, `ctas_per_panel`, `non_green_accent_colors_per_piece`, `forbidden_primary_colors`, `margin_M_formula`, `logo_size_print`, `logo_size_digital`, `logo_clear_space`, `type_on_white_plate_forbidden`, `brand_colors_only`). Each property defines its value-type appropriately (`integer` / `number` / `string` / `array` / `boolean` per the threshold).
  - `relax` — `array of objects`, each `{id: string, rationale: string}`. `id` MUST be one of the 16 brand rule ids OR one of the 22 layer1 keys, prefixed `layer1:` (e.g. `layer1:negative_space_pct`).
  - `tested_axis` — `string`, required (e.g. `"density+form"`).
  - `regeneration` — `object`, optional. Properties: `auto_retry_max` (integer, default `0`), `drop_threshold_pct` (number, default `40`). Per R5 above, v2 ships with defaults.

  Cite `tools/sla_lib/builder/brand_constraints.py:1525-1680` and `design-guide/README.md:24-46` in the schema's top-level `description` so future readers know where the enums came from.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  python3 -c "
  import yaml, json
  from jsonschema import Draft202012Validator
  s = yaml.safe_load(open('experiments/_schema/constraints.schema.yaml'))
  Draft202012Validator.check_schema(s)
  print('SCHEMA OK')
  "
  ```
  Exit code 0; stdout contains `SCHEMA OK`.
  </verify>
  <done>`experiments/_schema/constraints.schema.yaml` exists; `Draft202012Validator.check_schema()` passes; enum lists for `brand_rules` and `relax.id` cover all 16 + 22 known ids.</done>
</task>

<task id="T02" name="add-falzflyer-default-envelope">
  <action>
  Create `experiments/_constraints/falzflyer-default.yml`. New directory `experiments/_constraints/` (does not exist today — verified by environment audit).

  Contents:

  - Header comment block: "Default constraint envelope for falzflyer experiments. See `design-guide/README.md:24-46` (Layer-1 deterministic rules) and `tools/sla_lib/builder/brand_constraints.py:1525-1680` (16 BRAND_CONSTRAINTS). All listed rules are floor; per-experiment `constraints.yml` MAY relax named rules via the `relax:` list with rationale."
  - `extends:` — omit (this IS the root default).
  - `brand_rules:` — list all 16 ids verbatim from `BRAND_CONSTRAINTS` registry order.
  - `layer1:` — flatten the 22 thresholds from research/codebase.md §7 with explicit values (e.g. `body_min_pt: 10`, `body_line_length_chars: {min: 45, max: 75, ideal: 66}`, `headline_size_jump_x: 2.5`, `negative_space_pct: 30`, `brand_colors_only: ["Dunkelgrün", "Hellgrün", "Gelb", "Magenta"]`, `forbidden_primary_colors: ["SPD-red", "AfD/CDU-blue", "FDP-yellow-saturated", "Linke-magenta"]`, etc.). Keep YAML readable; one comment per row citing source (`# hcd #12` or `# CD-Quickguide`).
  - `relax: []` — empty by default.
  - `tested_axis: "default"` — placeholder (each per-experiment `constraints.yml` overrides).
  - `regeneration: {auto_retry_max: 0, drop_threshold_pct: 40}` — per R5.

  The file MUST validate against the schema from T01.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  python3 -c "
  import yaml
  from jsonschema import Draft202012Validator
  schema = yaml.safe_load(open('experiments/_schema/constraints.schema.yaml'))
  inst = yaml.safe_load(open('experiments/_constraints/falzflyer-default.yml'))
  errs = sorted(Draft202012Validator(schema).iter_errors(inst), key=lambda e: list(e.path))
  for e in errs: print('ERR:', list(e.path), e.message)
  assert not errs, f'{len(errs)} validation errors'
  assert len(inst['brand_rules']) == 16
  assert len(inst['layer1']) == 22
  print('ENVELOPE DEFAULT OK')
  "
  ```
  Exit code 0; stdout contains `ENVELOPE DEFAULT OK`.
  </verify>
  <done>`experiments/_constraints/falzflyer-default.yml` exists, validates against the schema, lists 16 brand_rules + 22 layer1 keys; `relax: []`; `regeneration.auto_retry_max: 0`.</done>
</task>

<task id="T03" name="implement-experiment-envelope-py">
  <action>
  Invoke `Skill(command="python")` BEFORE editing any `.py`.

  Create `tools/experiment_envelope.py`. Light wrapper composing existing `BRAND_CONSTRAINTS` + new Layer-1 predicates.

  Public surface:

  ```python
  from dataclasses import dataclass
  from pathlib import Path
  from sla_lib.builder.constraints import Violation
  from sla_lib.builder import BRAND_CONSTRAINTS

  @dataclass(frozen=True)
  class Envelope:
      brand_rules: tuple[str, ...]          # ids from the 16
      layer1: dict[str, object]              # thresholds verbatim from YAML
      relax: tuple[tuple[str, str], ...]     # (id, rationale)
      tested_axis: str
      regeneration: dict[str, object]

  def load_envelope(exp_dir: Path) -> Envelope: ...
  def run_envelope(doc, envelope: Envelope) -> list[Violation]: ...
  def format_envelope_markdown(envelope: Envelope) -> str: ...
  ```

  Implementation rules:

  - `load_envelope(exp_dir)`: reads `exp_dir / "constraints.yml"`. If the file has `extends: <relpath>`, resolves relative to the file and merges (per-experiment values override default's; `relax` and `brand_rules` overlays follow shallow-override on rule-id maps — Ansible idiom per RESEARCH.md "Don't Hand-Roll"). Validates the merged structure against `experiments/_schema/constraints.schema.yaml` using `Draft202012Validator.iter_errors()`; raises `EnvelopeValidationError` listing all errors on failure (don't return half-built envelopes). Returns a frozen `Envelope`.

  - `run_envelope(doc, envelope)`: composes two checks, returns one merged `list[Violation]`.
    1. **Brand-rules check.** For each `rule_id` in `envelope.brand_rules` AND NOT in `envelope.relax` ids: pull `rule` from `BRAND_CONSTRAINTS` by id, call `rule.check(primitives, doc)` where `primitives = list(doc.iter_all_primitives()) if hasattr(doc, 'iter_all_primitives') else []`, append all returned `Violation`s with `severity == "error"`. (Mirror `tools/sla_lib/builder/structural_check.py:183-203`'s exception-catching pattern — wrap each `rule.check` call in `try/except` and emit a synthetic `Violation(severity="error", rule_id=rule_id, message=f"rule check raised: {e!r}")` so a buggy rule never silently passes a variant.)
    2. **Layer-1 predicates check.** Implement new predicate functions (one per Layer-1 key the brand_constraints code doesn't already cover): `body_min_pt`, `body_line_length_chars`, `headline_size_jump_x`, `headline_max_words`, `body_contrast_ratio`, `display_contrast_ratio_18pt_plus`, `type_families_per_panel`, `type_sizes_per_panel`, `alignment_systems_per_panel`, `negative_space_pct`, `dominant_element_optical_weight_pct`, `face_crop_fill_pct`, `ctas_per_panel`. (The remaining 9 Layer-1 keys — `margin_M_formula`, `logo_size_print`/`_digital`/`_clear_space`, `type_on_white_plate_forbidden`, `brand_colors_only`, `forbidden_primary_colors`, `non_green_accent_colors_per_piece`, `caption_impressum_min_pt` — mirror existing `BRAND_CONSTRAINTS` (color_palette, text_on_green, logo_size_3M); for those, the predicate is a thin pass-through that emits no extra violations beyond the brand-rule check.)
    Each predicate signature: `def _check_<key>(doc, threshold) -> list[Violation]`. Predicates skipped if `f"layer1:{key}"` is in the `relax` id set.
    Return value: all violations from steps 1 + 2 merged, deduped by `(rule_id, message)`.

  - `format_envelope_markdown(envelope)`: produces a human-readable Markdown summary suitable for threading into the hypothesis-generation prompt. Sections: "Brand rules (16 ids, enforced)", "Layer-1 thresholds", "Relaxations (named)", "Tested axis", "Regeneration policy". Use bullet lists, not tables (the LLM context window prefers bullets for variable-width tokens). 200–500 words target.

  Add unit tests in `tools/sla_lib/tests/test_experiment_envelope.py`:

  1. `test_load_envelope_default_only` — `extends:` resolution disabled; loads `experiments/_constraints/falzflyer-default.yml`, asserts `len(brand_rules) == 16`, `len(layer1) == 22`.
  2. `test_load_envelope_with_extends_and_relax` — synthesises a tmp `constraints.yml` extending the default with `relax: [{id: brand:band_consistency, rationale: "test"}]`; asserts the loaded `relax` tuple has one element and that the merged `brand_rules` still contains all 16 (the relax is a runtime skip, not a list-removal).
  3. `test_load_envelope_validation_failure` — synthesises a malformed YAML missing `tested_axis`; expects `EnvelopeValidationError` listing the missing field.
  4. `test_run_envelope_synthetic_doc_passes` — builds a minimal-but-valid `Document` (use `templates/kandidat-falzflyer-din-lang/variant_scaffold.py::build_variant_front` with a no-op `render_p2`); asserts `run_envelope` returns an empty list (no envelope violations on a no-op-variant doc).
  5. `test_run_envelope_synthetic_doc_violates_inside_page` — places a primitive that overflows panel bounds; asserts `run_envelope` returns at least one `Violation` whose `rule_id == "brand:inside_page"`.
  6. `test_run_envelope_layer1_body_min_pt_violation` — places a 9pt text frame; asserts a Layer-1 `body_min_pt` violation with severity error.
  7. `test_format_envelope_markdown_shape` — asserts the rendered Markdown contains the strings "Brand rules", "Layer-1", "Tested axis", and at least one rule id (e.g. `brand:inside_page`).

  Run `ruff check tools/experiment_envelope.py tools/sla_lib/tests/test_experiment_envelope.py` and `mypy tools/experiment_envelope.py` per the python skill before committing.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check tools/experiment_envelope.py tools/sla_lib/tests/test_experiment_envelope.py && \
  mypy tools/experiment_envelope.py && \
  python3 -m unittest tools.sla_lib.tests.test_experiment_envelope -v
  ```
  Exit code 0; all 7 tests pass.
  </verify>
  <done>`tools/experiment_envelope.py` exposes `load_envelope`, `run_envelope`, `format_envelope_markdown`, `Envelope`, `EnvelopeValidationError`; 7 unit tests pass; ruff + mypy clean.</done>
</task>

<task id="T04" name="bump-manifest-schema">
  <action>
  Edit `experiments/_schema/manifest.schema.yaml`. Extend the `_dropped` item shape to support structured violations.

  Current shape (from research/codebase.md §3): `_dropped: list[{slug: str, reason: str}]`.

  New shape (additive, backward-compatible — old entries still validate):
  ```yaml
  _dropped:
    type: array
    items:
      type: object
      required: [slug, reason]
      additionalProperties: false
      properties:
        slug: {type: string}
        reason: {type: string}
        violations:
          type: array
          items:
            type: object
            required: [rule_id, message, severity]
            additionalProperties: false
            properties:
              rule_id: {type: string}
              message: {type: string}
              severity: {enum: [error, warning]}
              targets: {type: array, items: {type: string}}
  ```

  `violations` is **optional** so v1's manifest.json (lacking the field) still validates — confirm by running schema validation against `experiments/falzflyer-p2-mein-plan/manifest.json` after the edit.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  python3 -c "
  import json, yaml
  from jsonschema import Draft202012Validator
  s = yaml.safe_load(open('experiments/_schema/manifest.schema.yaml'))
  Draft202012Validator.check_schema(s)
  v1 = json.load(open('experiments/falzflyer-p2-mein-plan/manifest.json'))
  errs = list(Draft202012Validator(s).iter_errors(v1))
  for e in errs: print('ERR:', list(e.path), e.message)
  assert not errs, f'v1 manifest no longer validates: {len(errs)} errors'
  print('MANIFEST SCHEMA OK + v1 BACKWARD-COMPAT OK')
  "
  ```
  Exit code 0; stdout contains the OK message.
  </verify>
  <done>`experiments/_schema/manifest.schema.yaml` extends `_dropped` with optional `violations` array; v1's `experiments/falzflyer-p2-mein-plan/manifest.json` still validates.</done>
</task>

<task id="T05" name="wire-envelope-into-experiment-render">
  <action>
  Invoke `Skill(command="python")` BEFORE editing.

  Edit `tools/experiment_render.py`:

  1. **Replace `_inside_page_violations` (lines 130–143) with `_envelope_violations`.** Signature: `def _envelope_violations(doc, envelope: Envelope) -> list[Violation]`. Body: `return run_envelope(doc, envelope)`. Add the import `from experiment_envelope import Envelope, load_envelope, run_envelope` at the top of the module (mirror existing import style — namespace `experiment_envelope` lives next to `experiment_render.py` in `tools/`).

  2. **Update `_build_variant_sla` (lines 150–208).** Add `envelope: Envelope` keyword parameter. Replace the call at line 165 `violations = _inside_page_violations(doc)` with `violations = _envelope_violations(doc, envelope)`.

  3. **Update `run_render` (around lines 248–305).** After the existing `_verify_brand_fonts()` check at line ~271, load the envelope once: `envelope = load_envelope(exp_dir)` (where `exp_dir = ROOT / "experiments" / exp_id`). If `constraints.yml` is missing in the experiment directory, raise with a clear error message: `FileNotFoundError(f"{exp_dir}/constraints.yml missing — run 'experiments new' first.")` and return exit code `7` (new code for "envelope missing"). Pass `envelope=envelope` to every `_build_variant_sla` call in the per-variant loop (line ~292).

  4. **Update the drop loop (lines 289–303).** Change the drop log message format from `"DROP {slug}: inside_page — {messages}"` to `"DROP {slug}: envelope — {rule_id}: {message}; ..."` (use the first 3 violations' `rule_id: message` pairs). Update the `dropped.append((slug, f"envelope: {messages}"))` line accordingly. Keep `dropped` as `list[tuple[str, str, list[Violation]]]` (extend the tuple to carry the structured violations through to manifest write-out).

  5. **Update the manifest write-out (lines 337–341).** Emit `violations` per dropped entry:
     ```python
     manifest_out["_dropped"] = [
         {"slug": s, "reason": r, "violations": [
             {"rule_id": v.rule_id, "message": v.message, "severity": v.severity, "targets": list(v.targets)}
             for v in vs
         ]}
         for (s, r, vs) in dropped
     ]
     ```

  6. **Docstring corrections (per R3 / pitfalls research §1):**
     - Lines 11–14: delete the bullet that says "Constraint check: only `brand:inside_page` (per CONTEXT.md resolved uncertainty 4 — variants are research artifacts, brand rules are not enforced; structural fit-on-page is)". Replace with: "Constraint check: full envelope (`tools/experiment_envelope.py::run_envelope` over the 16 BRAND_CONSTRAINTS + 22 Layer-1 thresholds + the experiment's declared relaxations). Variants whose rendered artifact violates the envelope are dropped from the voting bag with a structured `_dropped` entry. See `.claude/skills/experiments/SKILL.md` for the methodology."
     - Lines 135–137 (the `_envelope_violations` function-level docstring, post-rename): replace "no other brand rule runs on variants" with "runs every envelope rule against the post-build Document, pre-Scribus."

  7. **Add a new exit code 7** to `run_render` for the "envelope missing" case. Document the exit codes in the module docstring (`0` ok / `3` brand-fonts gate failed / `4` manifest schema invalid / `5` variant module load error / `6` reserved / `7` envelope missing).

  After edits: `ruff check tools/experiment_render.py` and `mypy tools/experiment_render.py`.

  **Integration test** — add `tools/sla_lib/tests/test_experiment_render_envelope.py`:

  - `test_render_drops_variant_violating_envelope` — sets up a tmp experiment dir with a `constraints.yml` extending the default and a single variant whose `render_p2` places a 9pt text frame; calls `run_render(exp_id=<tmpname>, skip_scribus=True)`; asserts `manifest.json::_dropped` contains one entry with the variant's slug, `reason` starting with `envelope:`, and `violations` array containing a `body_min_pt` violation.
  - `test_render_passes_variant_within_envelope` — same setup but with a no-op `render_p2`; asserts `_dropped` is empty.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check tools/experiment_render.py tools/sla_lib/tests/test_experiment_render_envelope.py && \
  mypy tools/experiment_render.py && \
  python3 -m unittest tools.sla_lib.tests.test_experiment_render_envelope -v
  ```
  Exit code 0; both tests pass.
  </verify>
  <done>`tools/experiment_render.py` gates every variant on full envelope (not just `inside_page`); structured `violations` written to manifest; docstrings at lines 11-14 + 135-137 corrected; 2 integration tests pass.</done>
</task>

<task id="T06" name="add-v1-anti-examples-file">
  <action>
  **First, verify R3.** For each of the 3 retained-concept slugs (`numbered-priority-list`, `manifesto-single-statement`, `asymmetric-editorial-rules`), check whether `experiments/falzflyer-p2-mein-plan/variants/<slug>/page-01.png` exists and is readable. If any PNG is missing, re-render that variant via `bin/experiment-render falzflyer-p2-mein-plan --only <slug>` (this is read-only with respect to source; just regenerates the PNG). Then visually inspect each PNG and update R3's inferred-violation table if reality differs from the planner's guess.

  Create `tools/experiment_generate/v1_anti_examples.md`. One entry per v1 variant — 12 entries total. Each entry has the shape:

  ```markdown
  ### v1-<slug>

  - **Concept:** <one-line description (from research/codebase.md §5)>
  - **Why disqualified:** <rule_id>: <one-line failure description>
  - **DO NOT REPEAT:** <one-line, imperative — what specifically not to do>
  ```

  Source the 12 concepts + likely violations from research/codebase.md §5 table. For the three retained concepts, **append** an extra italicised line:

  > _Concept retained for v2 (`<v2-slug>-v2`) with envelope-respecting re-implementation per PLAN.md T11/T12/T13. This anti-example is about the v1 broken IMPLEMENTATION, not the idea._

  The three retained slugs and their v2 counterparts:
  - `numbered-priority-list` → `numbered-priority-list-v2` (T11)
  - `manifesto-single-statement` → `manifesto-single-statement-v2` (T12)
  - `asymmetric-editorial-rules` → `dunkelgrun-rules-between-items-v2` (T13)

  Header of the file (above the 12 entries):

  ```markdown
  # v1 anti-examples — DO NOT REPEAT

  These are the 12 hypotheses from `experiments/falzflyer-p2-mein-plan/` (v1, 2026-04 run).
  v1's failure mode: every variant violated the constraint envelope because the render gate only
  enforced `brand:inside_page`, not the 16 BRAND_CONSTRAINTS + 22 Layer-1 thresholds. v2's
  gate (T05) closes that loop. The 12 v1 hypotheses are listed below as named anti-examples;
  v2's hypothesis-generation prompt threads this file in (token `{v1_anti_examples}`) so the
  generator avoids re-emitting the broken implementations.
  ```

  Keep total length ≤ 2,500 words; the file is read into the prompt context.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  python3 -c "
  import re
  txt = open('tools/experiment_generate/v1_anti_examples.md').read()
  entries = re.findall(r'^### v1-([a-z0-9-]+)', txt, re.M)
  expected = ['asymmetric-editorial-rules','cut-to-three-with-body','first-person-commitments','handwritten-protest-aesthetic','luxurious-whitespace-two-items','manifesto-single-statement','numbered-priority-list','quote-from-resident','staggered-block-accent','vollkorn-italic-cornerstone','weighted-hero-lead','yellow-accent-privileged-item']
  assert sorted(entries) == sorted(expected), f'missing: {set(expected)-set(entries)}'
  for s in ['numbered-priority-list','manifesto-single-statement','asymmetric-editorial-rules']:
      block = txt.split(f'### v1-{s}')[1].split('### ')[0]
      assert 'Concept retained for v2' in block, f'{s} missing retained marker'
  words = len(txt.split())
  assert words <= 2500, f'too long: {words} words'
  print('ANTI-EXAMPLES OK', len(entries), 'entries,', words, 'words')
  "
  ```
  Exit code 0; stdout shows `12 entries`.
  </verify>
  <done>`tools/experiment_generate/v1_anti_examples.md` contains 12 entries (one per v1 variant); 3 retained concepts carry the "concept retained for v2" suffix; file is ≤ 2500 words; R3 visual-check pass logged or PNGs re-rendered.</done>
</task>

<task id="T07" name="extend-prompt-template">
  <action>
  Edit `tools/experiment_generate/prompt_template.md` (107 lines, read in full before editing). Three insertion points per research/codebase.md §4:

  1. **Between line 29 and 31 (after "What counts as structurally distinct", before "Examples"):** insert a new section `## Constraint envelope (HARD floor)` containing the `{constraint_envelope}` token verbatim on its own line. Preamble paragraph above the token: "Every hypothesis MUST respect every rule below. These are not suggestions; they are gate conditions enforced post-render. Verbal claims of compliance carry no weight; only the rendered artifact does. If a hypothesis requires violating one of these rules to express the tested axis, it MUST appear under `relax:` in the experiment's `constraints.yml` with rationale — otherwise it will be dropped at render."

  2. **Between line 54 and 56 (after good/bad Examples, before Anti-collapse):** insert a new section `## v1 anti-examples — DO NOT REPEAT` containing the `{v1_anti_examples}` token verbatim on its own line. Preamble paragraph above the token: "The following 12 hypotheses were generated for v1 (`experiments/falzflyer-p2-mein-plan/`). Each violated the constraint envelope. The current generation MUST NOT re-emit these specific failure modes. Three of the 12 carry a `Concept retained for v2` note — the broken implementation is the anti-example; the planner has re-implemented those concepts inside the envelope as separate variants. Do not propose the broken versions."

  3. **In the "Final check" section (around line ~100):** add a new bullet `6.` reading: `Does every hypothesis respect the constraint envelope (margins ≥6mm, body ≥10pt, contrast ≥4.5:1, all 16 BRAND_CONSTRAINTS)? If unsure, prefer a more conservative density choice.` Renumber any existing bullet that follows.

  Do NOT touch the existing two tokens (`{subject}`, `{weak_area_quote}`) — they keep working.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  python3 -c "
  txt = open('tools/experiment_generate/prompt_template.md').read()
  for tok in ['{subject}', '{weak_area_quote}', '{constraint_envelope}', '{v1_anti_examples}']:
      assert tok in txt, f'missing token {tok}'
  assert '## Constraint envelope (HARD floor)' in txt
  assert '## v1 anti-examples' in txt
  assert 'respect the constraint envelope' in txt.lower() or 'respect the envelope' in txt.lower()
  print('PROMPT TEMPLATE OK')
  "
  ```
  Exit code 0.
  </verify>
  <done>Prompt template carries 4 substitution tokens, the envelope section, the anti-examples section, and the envelope bullet in Final check.</done>
</task>

<task id="T08" name="wire-envelope-into-hypothesis-gen">
  <action>
  Invoke `Skill(command="python")` BEFORE editing.

  Edit `tools/experiment_hypothesis_gen.py`:

  1. **Extend `render_prompt` (lines 84–95):** the tokens tuple grows from `("subject", "weak_area_quote")` to `("subject", "weak_area_quote", "constraint_envelope", "v1_anti_examples")`. Signature becomes `def render_prompt(template: str, subject: str, weak_area_quote: str, constraint_envelope: str, v1_anti_examples: str) -> str`. The `.format(...)` call expands accordingly. All four tokens are required parameters; no defaults (a missing envelope is a programming error to surface loudly).

  2. **Update `run_generation` (around lines 506–528):** after loading the template, BEFORE the first `render_prompt` call:
     ```python
     from experiment_envelope import load_envelope, format_envelope_markdown
     envelope = load_envelope(exp_dir)
     envelope_md = format_envelope_markdown(envelope)
     anti_examples_path = ROOT / "tools" / "experiment_generate" / "v1_anti_examples.md"
     v1_anti_examples = anti_examples_path.read_text(encoding="utf-8")
     ```
     Then pass `constraint_envelope=envelope_md, v1_anti_examples=v1_anti_examples` to every `render_prompt(...)` call.

  3. **Extend `SUBJECT_METADATA` (lines 62–77).** Add a new entry for `falzflyer-p2-mein-plan-v2`:
     ```python
     "falzflyer-p2-mein-plan-v2": {
         "subject": "<copy from v1 entry, identical subject framing — falzflyer P2 'Mein Plan' panel>",
         "target_weak_area": "design-guide/gruene-corpus.md §2.2 — Information density discipline",
     },
     ```
     (Per CONTEXT decision 7, the weak-area pointer is §2.2.)

  4. **Bump prompt-version hashing (`_prompt_version` at lines 473–474).** Today it hashes the template text only. Extend it to also hash the envelope Markdown + the anti-examples text concatenated, so any future change to `falzflyer-default.yml` or `v1_anti_examples.md` bumps the version. Signature stays the same; the additional inputs are read inside `_prompt_version` (pull `ROOT` paths from module-level constants).

  5. **Unit test** — extend (or create) `tools/sla_lib/tests/test_experiment_hypothesis_gen.py`:
     - `test_render_prompt_substitutes_all_four_tokens` — passes synthetic strings for each token, asserts all four appear in the rendered output and the literal `{` from the source template was preserved where it should be (the existing brace-escape pattern at line 88).
     - `test_subject_metadata_has_v2` — asserts `"falzflyer-p2-mein-plan-v2" in SUBJECT_METADATA` and its `target_weak_area` mentions §2.2.

  After edits: `ruff check tools/experiment_hypothesis_gen.py tools/sla_lib/tests/test_experiment_hypothesis_gen.py` and `mypy tools/experiment_hypothesis_gen.py`.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check tools/experiment_hypothesis_gen.py tools/sla_lib/tests/test_experiment_hypothesis_gen.py && \
  mypy tools/experiment_hypothesis_gen.py && \
  python3 -m unittest tools.sla_lib.tests.test_experiment_hypothesis_gen -v
  ```
  Exit code 0; both new tests pass.
  </verify>
  <done>`render_prompt` accepts 4 tokens; `run_generation` loads envelope + anti-examples before each invocation; `SUBJECT_METADATA` has the v2 entry pointing at §2.2; `_prompt_version` hashes envelope + anti-examples; tests pass.</done>
</task>

<task id="T09" name="surface-drops-and-corpus-stub-in-results">
  <action>
  Invoke `Skill(command="python")` BEFORE editing.

  Edit `tools/experiment_results.py`. Two additions:

  1. **New "## Variants dropped during render" section in SUMMARY.md.** Read `experiments/<exp>/manifest.json::_dropped` (may be missing or empty — treat both as "no drops"). For each entry, emit a Markdown subsection with the slug as a heading, the `reason` as a one-line summary, and a bullet list of `violations` (each as `- <severity>: <rule_id> — <message>`). If `_dropped` is empty, emit a single line: "_No variants dropped — all hypotheses passed the envelope._".

  2. **Dual-section corpus stub.** Add a new section near the end of SUMMARY.md titled `## Corpus update stub (to be amended into design-guide/gruene-corpus.md)`. Two clearly-labelled sub-sections:
     - `### From v1 (envelope necessity)` — pre-filled paragraph: "_v1 (`falzflyer-p2-mein-plan`, 2026-04) revealed that variants violated basic spacing/margin rules because the render gate enforced only `brand:inside_page`, not the full 16 BRAND_CONSTRAINTS + Layer-1 thresholds. v2's gate (`tools/experiment_envelope.py::run_envelope`) closes that loop. Methodology lesson: every design experiment respects a constraint envelope by default; the tested axis is the only declared relaxation. See `.claude/skills/experiments/SKILL.md` for the corrected process._"
     - `### From v2 (density+form findings)` — pre-filled scaffold: "_Top-3 (by Bradley-Terry-style win-rate): [VARIANT-1] / [VARIANT-2] / [VARIANT-3]. Bottom-3: [...]. Spearman halo flag: [...]. To be filled in by the executor of T17 after Flo's voting session._"

  Place the new sections BEFORE any existing "Top-3 / Bottom-3" voting tally (if present in current SUMMARY.md generation) and AFTER the per-variant rendering metadata.

  Unit test — extend `tools/sla_lib/tests/test_experiment_results.py` (create if missing):
  - `test_summary_includes_dropped_section` — synthesises a tmp experiment dir with a manifest containing one `_dropped` entry; runs the SUMMARY.md generator; asserts the section header + the dropped slug + at least one violation line appears.
  - `test_summary_includes_corpus_stub` — asserts both sub-section headings appear.

  Ruff + mypy clean per python skill.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check tools/experiment_results.py && \
  mypy tools/experiment_results.py && \
  python3 -m unittest tools.sla_lib.tests.test_experiment_results -v
  ```
  Exit code 0; both tests pass.
  </verify>
  <done>`tools/experiment_results.py` emits "Variants dropped during render" + dual-section corpus stub in SUMMARY.md; 2 tests pass.</done>
</task>

<task id="T10" name="update-design-guide-docs">
  <action>
  Two minor edits, both ADDITIVE (per research/codebase.md §8 — the "wrong framing" is NOT in `design-guide/README.md` today; the edit is naming the envelope, not reversing existing prose).

  1. **`design-guide/README.md`:** Below the Layer-1 deterministic-rules table (after line 46), insert a new paragraph (around 100 words):

     > **The Layer-1 deterministic rules ARE the constraint envelope for design experiments.** A hypothesis testing one design axis (e.g. information density, hierarchy strategy, typographic voice) MUST respect every other Layer-1 rule. Variants violating the envelope are dropped, not voted on. The 16 `BRAND_CONSTRAINTS` (defined in `tools/sla_lib/builder/brand_constraints.py`) are part of this envelope. The earlier framing — that experiment variants are "research artifacts" exempt from brand rules — was wrong; it conflated "a hypothesis tests one axis" with "a hypothesis ignores all axes". See `.claude/skills/experiments/SKILL.md` for the full methodology and the `/experiments` workflow.

     Cross-reference in the README's table-of-contents / "How to use this file" section (if one exists) to point at `.claude/skills/experiments/SKILL.md`.

  2. **`design-guide/gruene-corpus.md` §6:** Add a single line:

     > _Process note: the first experiment run (`experiments/falzflyer-p2-mein-plan`, v1, 2026-04) produced variants violating basic spacing/margin rules because the constraint envelope wasn't enforced. The corrected process — Layer-1 + 16 BRAND_CONSTRAINTS as floor, the tested axis as the only declared relaxation — is encoded in `.claude/skills/experiments/SKILL.md`._

     Place this one-liner at the end of §6 or wherever §6's prose has a natural seam (the executor reads §6 in full and picks the cleanest insertion point).

  No source-code changes here — the corresponding source-code docstring reversal already lives in T05 (`experiment_render.py:11-14, 135-137`).
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  grep -q "ARE the constraint envelope for design experiments" design-guide/README.md && \
  grep -q ".claude/skills/experiments" design-guide/README.md && \
  grep -q ".claude/skills/experiments" design-guide/gruene-corpus.md && \
  echo "DESIGN-GUIDE EDITS OK"
  ```
  Exit code 0.
  </verify>
  <done>`design-guide/README.md` names Layer-1 + 16 BRAND_CONSTRAINTS as the experiment envelope and cross-references the skill; `gruene-corpus.md` §6 carries the one-liner process note.</done>
</task>

<task id="T11" name="reimplement-numbered-priority-list-v2">
  <action>
  Invoke `Skill(command="python")` BEFORE editing.

  Prerequisite: T15 has created `experiments/falzflyer-p2-mein-plan-v2/` (or this task creates the directory if T15 runs after — see T15 note). For now, create the directory and the variant file directly.

  Create `experiments/falzflyer-p2-mein-plan-v2/variants/numbered-priority-list-v2.py`. Concept retained from v1: numbered 1–5 list with weighted typographic scale per rank — eye lands on #1 first by design.

  Implementation specifics:

  - Re-read `experiments/falzflyer-p2-mein-plan/variants/numbered-priority-list.py` as the structural baseline. Keep the same 5-row layout, the same `exp/numbered/numeral` and `exp/numbered/text` para styles, the same thin 0.4mm Dunkelgrün rules between rows. The CHANGE is the per-rank font sizes.

  - **Weighted scale:** numerals at rank 1..5 take sizes `36, 30, 24, 20, 16 pt` (or — if the body envelope of `body_min_pt ≥ 10` would be violated by the smallest text size — picks the next-larger geometric series `40, 32, 26, 21, 17 pt`). Body text per row stays a constant Gotham Narrow Bold 14pt (≥10pt body floor). Decision: use `36/30/24/20/16` as the primary; the smallest is 16pt which clears the 10pt floor and the 8pt caption floor with margin.

  - **Layout math:** 5 rows in a 130mm-available panel height with proportional row heights matching the weighted scale (e.g. `row_heights = [32, 28, 24, 22, 20]` mm summing to 126mm; row_gaps embedded in those heights as internal padding). Negative-space check: ≥30% — 126mm of content in 130mm available leaves only 3% above content; the panel TOP and BOTTOM margins must contribute the remaining whitespace. Confirm by running T05's envelope gate.

  - `axis_commitments`: per R6, primary=density, secondary=form, tertiary=hierarchy. Embed as a top-of-file docstring comment.

  - Export: `def render_p2(doc, page) -> None:` matching `templates/kandidat-falzflyer-din-lang/variant_scaffold.py::build_variant_front`'s expected callable shape.

  Add a smoke test `tools/sla_lib/tests/test_v2_numbered_priority_list.py`:
  - Builds the variant via the scaffold's `build_variant_front`, runs `run_envelope(doc, load_envelope(<v2 exp dir>))`, asserts zero violations of severity `"error"`.

  Ruff + mypy clean per python skill.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check experiments/falzflyer-p2-mein-plan-v2/variants/numbered-priority-list-v2.py tools/sla_lib/tests/test_v2_numbered_priority_list.py && \
  mypy experiments/falzflyer-p2-mein-plan-v2/variants/numbered-priority-list-v2.py && \
  python3 -m unittest tools.sla_lib.tests.test_v2_numbered_priority_list -v
  ```
  Exit code 0; smoke test passes (zero envelope violations).
  </verify>
  <done>`numbered-priority-list-v2.py` exists with rank-weighted scale `36/30/24/20/16pt`, axis_commitments docstring, smoke test passes envelope gate.</done>
</task>

<task id="T12" name="reimplement-manifesto-single-statement-v2">
  <action>
  Invoke `Skill(command="python")` BEFORE editing.

  Pre-flight: read `shared/ci.yml` and verify `Vollkorn Black` (or the exact Postscript name used in v1's variant) is registered under `fonts:`. If not registered, halt and surface to planner — the variant requires that face and cannot be shipped without it. Do NOT add fonts to `shared/ci.yml` from this task (font registration is out of scope per the OUT_OF_SCOPE list — strictly the envelope work).

  Create `experiments/falzflyer-p2-mein-plan-v2/variants/manifesto-single-statement-v2.py`. Concept retained from v1: one editorial sentence owns the panel.

  Implementation specifics:

  - Structural baseline: re-read `experiments/falzflyer-p2-mein-plan/variants/manifesto-single-statement.py`. Keep the single statement frame at `x=105 y=72 w=87 h=120` (already inside the envelope by geometry: 72+120=192 < 213mm panel-height).
  - Statement copy: keep v1's "Mödling muss vorangehen — beim Klima, beim Wohnen, beim Zuhören." (or update for the v2 SUBJECT if `SUBJECT_METADATA` evolves the subject — the executor checks both and picks the one matching the v2 subject).
  - Para style: `exp/manifesto/statement` at Vollkorn Black 30pt (preserve from v1; envelope-compliant since 30pt > 10pt body floor by an order of magnitude). Body line-length check: at 30pt in 87mm width, the line breaks naturally — confirm via envelope gate's `body_line_length_chars` predicate.
  - Optional footer: if v1's variant included a `Gotham Narrow Book 10pt` footer that sat on green, REMOVE it (likely the v1 envelope failure per R3 inference) OR move it onto a white plate above the footer band (which collides with `text_on_green` / `type_on_white_plate_forbidden` — so simply remove). Verify the absence of footer doesn't break the scaffold's expectations (re-read scaffold first).
  - `axis_commitments`: primary=density (1 item), secondary=form (sentence vs. list).
  - `render_p2(doc, page)` export.

  Smoke test `tools/sla_lib/tests/test_v2_manifesto_single_statement.py`:
  - Build + envelope-gate; assert zero `severity="error"` violations.

  Ruff + mypy clean.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check experiments/falzflyer-p2-mein-plan-v2/variants/manifesto-single-statement-v2.py tools/sla_lib/tests/test_v2_manifesto_single_statement.py && \
  mypy experiments/falzflyer-p2-mein-plan-v2/variants/manifesto-single-statement-v2.py && \
  python3 -m unittest tools.sla_lib.tests.test_v2_manifesto_single_statement -v
  ```
  Exit code 0.
  </verify>
  <done>`manifesto-single-statement-v2.py` exists with Vollkorn Black 30pt single-statement (verified in `shared/ci.yml`), envelope gate passes, smoke test green.</done>
</task>

<task id="T13" name="reimplement-dunkelgrun-rules-between-items-v2">
  <action>
  Invoke `Skill(command="python")` BEFORE editing.

  Create `experiments/falzflyer-p2-mein-plan-v2/variants/dunkelgrun-rules-between-items-v2.py`. Concept retained from v1's `asymmetric-editorial-rules`: left-aligned items separated by thin Dunkelgrün rules, editorial-magazine register.

  Implementation specifics:

  - Structural baseline: `experiments/falzflyer-p2-mein-plan/variants/asymmetric-editorial-rules.py`. Para style `exp/editorial/item` (Gotham Narrow Bold 18pt), items at `x=105 ...`, thin 0.4mm Dunkelgrün polygon rules at `y+row_h-4`.
  - **Reduce row count from 5 to 3.** Rationale: v1's 5 rows × 22mm = 110mm of content in 130mm-available leaves ~15% whitespace; envelope requires `negative_space_pct ≥ 30`. With 3 rows × ~22mm = 66mm of content, the remaining 64mm of panel height is empty — about 49% whitespace, comfortably above 30%.
  - Keep the 0.4mm Dunkelgrün thin rule between rows (2 rules total for 3 items). Keep the right-third intentionally empty (the "asymmetric" half of the original concept).
  - `axis_commitments`: primary=density (3 items), secondary=form (thin-rule separator).
  - `render_p2(doc, page)` export.

  Smoke test `tools/sla_lib/tests/test_v2_dunkelgrun_rules_between_items.py`:
  - Build + envelope-gate; assert zero `severity="error"` violations, **including** the `negative_space_pct` predicate.

  Ruff + mypy clean.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  ruff check experiments/falzflyer-p2-mein-plan-v2/variants/dunkelgrun-rules-between-items-v2.py tools/sla_lib/tests/test_v2_dunkelgrun_rules_between_items.py && \
  mypy experiments/falzflyer-p2-mein-plan-v2/variants/dunkelgrun-rules-between-items-v2.py && \
  python3 -m unittest tools.sla_lib.tests.test_v2_dunkelgrun_rules_between_items -v
  ```
  Exit code 0.
  </verify>
  <done>`dunkelgrun-rules-between-items-v2.py` exists, 3 rows (reduced from 5), envelope gate passes including `negative_space_pct ≥ 30`.</done>
</task>

<task id="T14" name="author-experiments-skill">
  <action>
  Invoke `Skill(command="generate-skill")`. The generate-skill skill's MANDATORY first step is a WebFetch of `https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices` — do that first. Re-validate R1 (multi-verb dispatch convention): if the doc shows a separate-skill-per-verb pattern, halt and re-engage the planner; otherwise proceed with single-skill four-verb branching.

  Create `.claude/skills/experiments/SKILL.md`. New directory — this is the FIRST project-local skill in the workspace (environment audit confirmed `.claude/skills/` does not exist).

  Use `/root/.claude/skills/generate-skill/scripts/init_skill.py` to scaffold the directory layout if the generate-skill workflow drives that step.

  **Frontmatter (mandatory):**
  ```yaml
  ---
  name: experiments
  description: |
    Run constraint-envelope design experiments with pairwise voting. Auto-activates
    on /experiments <verb> where <verb> in {new, generate, render, capture}. Encodes
    the three-layer model (envelope / variation surface / implementation), the
    corpus-update merge gate, and v1's failure-mode lessons.
  allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
  argument-hint: "[new|generate|render|capture] <experiment-id>"
  ---
  ```

  **Body sections (≤500 lines, ≤5000 words total — measured by `wc -w`):**

  1. **Three-layer model** (one section, ~100 words). Envelope / Variation surface / Implementation. Cross-reference `experiments/_schema/constraints.schema.yaml` and `tools/experiment_envelope.py`.

  2. **Four subcommand dispatch.** A short "When invoked as `/experiments <verb> <id>`, branch on $1:" section, followed by four `## /experiments <verb>` sections.

     - `## /experiments new <subject>` — scaffolds a new experiment dir: `experiments/<subject>/{constraints.yml, manifest.yml stub, variants/}`. `constraints.yml` is created by copying `experiments/_constraints/falzflyer-default.yml` and prompting for the `tested_axis` value. Pre-flight: verify `experiments/_constraints/falzflyer-default.yml` exists; verify `tools/experiment_envelope.py` importable; verify the subject id isn't already taken.
     - `## /experiments generate <id>` — runs `bin/experiment-generate <id>` (multi-LLM hypothesis generation with envelope threaded into the prompt). Pre-flight: verify `<id>/constraints.yml` exists and `tested_axis` is declared (not the default placeholder). Post-step: verify the generated `manifest.yml` has ≥10 hypotheses + ≥1 wildcard.
     - `## /experiments render <id>` — runs `bin/experiment-render <id>`. Pre-flight: verify brand fonts on PATH (`fc-list | grep gruene`). Post-step: print the `_dropped` summary; if drop rate >40%, surface to user and halt before continuing to voting page.
     - `## /experiments capture <id>` — runs `bin/experiment-results <id>`. Post-step: prompt the user (Flo) to amend `design-guide/gruene-corpus.md` with the dual-section update (v1 envelope-necessity lesson + v2 substantive findings) using the SUMMARY.md stub as the source.

  3. **v1 lessons section** (the durable carrier per CONTEXT decision 12). Bullet list, ~250 words:
     - Envelope conflation — v1 enforced only `inside_page`, missed the other 15 brand rules + 22 Layer-1 thresholds. Fixed: `tools/experiment_envelope.py::run_envelope` enforces all of them.
     - Mode collapse — multi-LLM dedup via Jaccard ≥0.6 (already in `experiment_hypothesis_gen.py:50`). Mitigation: required wild-card hypothesis per generation.
     - Halo-effect handling — voters tend to rank by overall polish, not the tested axis. Mitigation: declared `axis_commitments` per hypothesis; SUMMARY.md surfaces axis-balance before voting.
     - Position bias — voters favour left-presented variant in A/B pair. Mitigation: per-pair randomization in the Astro voting page.
     - Why all 16 BRAND_CONSTRAINTS are floor by default — the variation surface tests ONE axis; everything else is constraint. Relaxations MUST be explicit in `constraints.yml::relax`.

  4. **Process-doc references** (Level 3, on-demand). Optionally bundle:
     - `references/three-layer-model.md` — fuller treatment for executors who need depth.
     - `references/v1-lessons.md` — fuller post-mortem.
     - `references/anti-examples-format.md` — template for future per-experiment anti-examples files.

  5. **Corpus-update merge gate.** A short section restating: the corpus update is the merge gate. No experiment merges without a Flo voting session + a dual-section corpus amendment. Cross-reference the issue:* skills pattern.

  **Voice:** imperative ("To do X, run Y"), third-person in description.

  **Validation:** `bash /root/.claude/skills/generate-skill/scripts/validate.sh .claude/skills/experiments/SKILL.md` (the script checks YAML frontmatter, word count, references-depth).

  **Smoke check:** state in conversation `/experiments new test-subject` and verify the skill activates (Claude responds with the scaffold workflow). If invocation fails to activate, surface to the planner.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  test -f .claude/skills/experiments/SKILL.md && \
  bash /root/.claude/skills/generate-skill/scripts/validate.sh .claude/skills/experiments/SKILL.md && \
  W=$(wc -w < .claude/skills/experiments/SKILL.md) && \
  test "$W" -le 5000 && \
  echo "SKILL OK ($W words)"
  ```
  Exit code 0; `validate.sh` passes; word count ≤ 5000.
  </verify>
  <done>`.claude/skills/experiments/SKILL.md` exists with frontmatter + four subcommand sections + v1 lessons + corpus-gate note; `validate.sh` passes; `wc -w` ≤ 5000.</done>
</task>

<task id="T15" name="generate-v2-hypotheses">
  <action>
  Create `experiments/falzflyer-p2-mein-plan-v2/constraints.yml`. Content:

  ```yaml
  extends: ../_constraints/falzflyer-default.yml
  tested_axis: "density+form"
  relax: []
  regeneration:
    auto_retry_max: 0
    drop_threshold_pct: 40
  brand_rules:   # overlay — all 16 inherited from default; listed here for explicitness
    - brand:color_palette
    - brand:font_family
    - brand:line_spacing_0.9
    - brand:hl_sl_distance_x2
    - brand:logo_size_3M
    - brand:text_on_green
    - brand:bleed_3mm
    - brand:wahlkreuz_colored_bg
    - brand:inside_page
    - brand:spine_safety
    - brand:bleed_coverage
    - brand:image_text_overlap
    - brand:cover_extent_match
    - brand:visual_adjacency_drift
    - brand:image_fills_frame
    - brand:band_consistency
  layer1: {}   # inherits all 22 thresholds verbatim from falzflyer-default.yml
  ```

  Validate against `constraints.schema.yaml` before running generation.

  Then run:
  ```bash
  bin/experiment-generate falzflyer-p2-mein-plan-v2
  ```

  Multi-LLM run (claude + codex + gemini; gemini optional). Target: ≥12 hypotheses total (3 retained from T11/T12/T13 — to be re-injected by the executor into the manifest post-generation since the LLMs won't re-emit them given the anti-examples warning — plus ≥9 fresh density+form hypotheses).

  **Retained-concept injection:** After `bin/experiment-generate` produces `manifest.yml`, manually splice in the 3 retained-concept hypotheses with their `axis_commitments` per R6 (numbered-priority-list-v2, manifesto-single-statement-v2, dunkelgrun-rules-between-items-v2). Each gets a hypothesis object with `slug`, `description`, `axis_commitments`, `source: "retained-from-v1"`. The variant Python file is already in place from T11/T12/T13.

  **Envelope-text check** (catches the "verbal compliance only" failure mode from pitfalls.md §3): for each generated hypothesis, scan the description text for terms that would imply envelope violation (e.g. "5mm margin", "8pt body", "text on white") and surface them. This is a pre-render best-effort filter — the authoritative gate is at render-time. Implement as a one-shot script `tools/experiment_generate/_check_hypothesis_text.py` invoked after generation (does NOT need to be a permanent tool; OK to leave as a per-run script).

  Verify: the manifest validates against the bumped `manifest.schema.yaml` from T04.
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  test -f experiments/falzflyer-p2-mein-plan-v2/constraints.yml && \
  test -f experiments/falzflyer-p2-mein-plan-v2/manifest.yml && \
  python3 -c "
  import yaml, json
  from jsonschema import Draft202012Validator
  s = yaml.safe_load(open('experiments/_schema/manifest.schema.yaml'))
  m = yaml.safe_load(open('experiments/falzflyer-p2-mein-plan-v2/manifest.yml'))
  errs = list(Draft202012Validator(s).iter_errors(m))
  for e in errs: print('ERR:', list(e.path), e.message)
  assert not errs, f'manifest invalid: {len(errs)} errors'
  hs = m.get('hypotheses', [])
  assert len(hs) >= 12, f'too few hypotheses: {len(hs)}'
  slugs = [h['slug'] for h in hs]
  for s in ['numbered-priority-list-v2','manifesto-single-statement-v2','dunkelgrun-rules-between-items-v2']:
      assert s in slugs, f'retained {s} missing'
  print('HYPOTHESES OK', len(hs))
  "
  ```
  Exit code 0; ≥12 hypotheses; all three retained slugs present.
  </verify>
  <done>`experiments/falzflyer-p2-mein-plan-v2/constraints.yml` + `manifest.yml` exist; manifest validates; ≥12 hypotheses including the 3 retained-concept slugs.</done>
</task>

<task id="T16" name="render-v2-variants-end-to-end">
  <action>
  Run:
  ```bash
  bin/experiment-render falzflyer-p2-mein-plan-v2
  ```

  Expected outcome: all 12+ variants pass the envelope gate (since T11/T12/T13 are pre-validated; T15's fresh 9 were generated under envelope-aware prompting). If any drop, examine the `_dropped` entries — drops are acceptable per acceptance criterion #8 ("all drops explicitly logged with reasons") but the count of passing variants must be **≥ 10**. If < 10 pass, halt and surface to the planner (do NOT silently bypass).

  Mirror the rendered artifacts to `site/public/experiments/falzflyer-p2-mein-plan-v2/<slug>/` (the `_mirror_to_public` step in `experiment_render.py` does this automatically).

  Then build the Astro site to verify the voting page integrates:
  ```bash
  npm --prefix site run build
  ```

  Production-template regression check (acceptance gate ⑪): re-render an unrelated production template (e.g. `templates/kandidat-falzflyer-din-lang/` itself, separate from experiments) and confirm the output is byte-identical to the previously-committed reference (use `git diff` against the previously-rendered PDF/PNG in `site/public/templates/`).
  </action>
  <verify>
  ```bash
  cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run && \
  bin/experiment-render falzflyer-p2-mein-plan-v2 && \
  python3 -c "
  import json
  m = json.load(open('experiments/falzflyer-p2-mein-plan-v2/manifest.json'))
  dropped = m.get('_dropped', [])
  rendered = len(m.get('variants', [])) if 'variants' in m else (len(m.get('hypotheses',[])) - len(dropped))
  assert rendered >= 10, f'only {rendered} rendered, need ≥10'
  for d in dropped:
      assert 'reason' in d and 'violations' in d, f'drop missing structured fields: {d}'
  print(f'RENDER OK: {rendered} rendered, {len(dropped)} dropped (all structured)')
  " && \
  npm --prefix site run build
  ```
  Exit code 0; ≥10 variants rendered; all drops have structured `violations`; Astro build succeeds.
  </verify>
  <done>`experiments/falzflyer-p2-mein-plan-v2/` end-to-end rendered with ≥10 variants; any drops logged with structured violations; Astro `npm run build` clean; production template re-render is byte-stable.</done>
</task>

<task id="T17" name="manual-flo-voting-and-corpus-update" type="checkpoint:human-verify">
  <action>
  **THIS TASK IS MANUAL — flag as PENDING in EXECUTION.md, not COMPLETE.** The executor does NOT close this task autonomously; it is the merge gate per CONTEXT.md decision 15 and pitfalls.md §5.

  Runbook (the executor writes this section into EXECUTION.md verbatim as a handoff):

  1. Open `https://<site>/experiments/falzflyer-p2-mein-plan-v2/` (or whichever localhost URL the Astro dev server uses).
  2. Read the SUMMARY.md stub at `experiments/falzflyer-p2-mein-plan-v2/SUMMARY.md` BEFORE voting — verify the variant set is density+form-balanced (check the `axis_commitments` column).
  3. Run a complete pairwise voting session (Flo, single rater per CONTEXT — multi-rater merging is out of scope). Aim for full coverage of all C(N, 2) pairs.
  4. Export results JSON via the Astro page's "Export" button to `experiments/falzflyer-p2-mein-plan-v2/results/flo-<YYYY-MM-DD>.json`.
  5. Run `bin/experiment-results falzflyer-p2-mein-plan-v2` to aggregate into the final SUMMARY.md.
  6. Amend `design-guide/gruene-corpus.md` with the dual-section corpus update:
     - **Part 1** (closes #29 T15): v1 meta-lesson on envelope necessity. Verbatim text already drafted in SUMMARY.md's corpus stub (T09).
     - **Part 2** (closes #30 substantively): v2 density+form findings. Top-3 by win-rate, bottom-3 by loss-rate, Spearman halo flag if applicable. Provenance: link to `experiments/falzflyer-p2-mein-plan-v2/results/flo-<DATE>.json` and the SUMMARY.md.
  7. Commit the results JSON + the amended `gruene-corpus.md` as a single commit: `30+29: docs(corpus): close envelope-necessity + v2 density+form findings`.
  8. Final acceptance-gate verification — run the verification gate's full checklist (below).

  **No automated verify for this task.** The executor surfaces the runbook and the issue stays open until Flo confirms completion.
  </action>
  <verify>
  Manual. The executor states in their final report: "T17 PENDING — runbook handed off to Flo. Final commit lands after voting session + corpus amendment."
  </verify>
  <done>EXECUTION.md carries the runbook; results JSON path is reserved; `design-guide/gruene-corpus.md` carries both sections (Part 1 + Part 2) after Flo's session; final commit lands closing both #30 and #29-T15.</done>
</task>

</tasks>

<tests_strategy>

| Task | Test layer | What it proves |
|---|---|---|
| T01 | Schema self-check (`Draft202012Validator.check_schema`) | The schema itself is valid Draft 2020-12 |
| T02 | YAML validates against T01 schema | The default envelope is a legal instance |
| T03 | 7 unit tests on `experiment_envelope.py` | Loader / runner / formatter behave; predicates fire on synthetic-doc violations |
| T04 | Schema validates; v1 manifest still validates | Backward-compatible bump |
| T05 | 2 integration tests on render gate | Variant violating envelope is dropped with structured violations; clean variant passes |
| T06 | Anti-examples file structure check | 12 entries, 3 retained-concept markers, ≤2500 words |
| T07 | Token presence check | All 4 tokens substitutable; envelope + anti-examples sections present |
| T08 | 2 unit tests on hypothesis-gen | 4-token render_prompt; v2 SUBJECT_METADATA entry |
| T09 | 2 unit tests on results | Dropped-variants section + dual-section corpus stub |
| T10 | grep-based content check | New paragraph in README + cross-reference in gruene-corpus §6 |
| T11–T13 | Smoke test per retained variant | Each variant builds without envelope violations |
| T14 | `validate.sh` + word count | Skill validates per generate-skill conventions |
| T15 | Manifest schema validation + slug check | ≥12 hypotheses including 3 retained |
| T16 | End-to-end render + Astro build | ≥10 variants rendered with structured drops; site builds |
| T17 | MANUAL | Flo voting + corpus update; merge gate |

**Coverage philosophy:** every task that adds code carries automated verification at the same commit. T17 is the only MANUAL task and is flagged explicitly.

</tests_strategy>

<verification>

After all tasks (excluding T17), the executor runs the **acceptance-gate verification checklist**:

```bash
cd /root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run

# 1. Unit + integration tests
python3 -m unittest discover tools/sla_lib/tests -v

# 2. Static checks
ruff check tools/ experiments/falzflyer-p2-mein-plan-v2/variants/
mypy tools/experiment_envelope.py tools/experiment_render.py tools/experiment_hypothesis_gen.py tools/experiment_results.py

# 3. Site build
npm --prefix site run build

# 4. Skill validation
bash /root/.claude/skills/generate-skill/scripts/validate.sh .claude/skills/experiments/SKILL.md
test $(wc -w < .claude/skills/experiments/SKILL.md) -le 5000

# 5. v2 render verification
python3 -c "
import json
m = json.load(open('experiments/falzflyer-p2-mein-plan-v2/manifest.json'))
dropped = m.get('_dropped', [])
rendered = len(m.get('variants', [])) if 'variants' in m else (len(m.get('hypotheses',[])) - len(dropped))
assert rendered >= 10, f'only {rendered} rendered'
for d in dropped:
    assert 'violations' in d
print(f'v2 OK: {rendered} rendered, {len(dropped)} drops structured')
"

# 6. Production-template byte-stability — confirm no regression
git diff --stat -- 'site/public/templates/'
# Expect: empty diff (no production-template re-render churn)

# 7. Acceptance gate (#30 + #29-T15)
# 7a. Skill file exists
test -f .claude/skills/experiments/SKILL.md
# 7b. Constraints schema exists
test -f experiments/_schema/constraints.schema.yaml
# 7c. Default envelope exists
test -f experiments/_constraints/falzflyer-default.yml
# 7d. v2 experiment directory rendered
test -d experiments/falzflyer-p2-mein-plan-v2/variants/
# 7e. Design-guide README names envelope
grep -q "ARE the constraint envelope for design experiments" design-guide/README.md
# 7f. Source-code docstrings corrected
! grep -q "no other brand rule runs on variants" tools/experiment_render.py
```

**Done checklist (merge gate — #30 + #29-T15):**
- [ ] All unit/integration tests pass (`python3 -m unittest discover tools/sla_lib/tests`)
- [ ] `ruff` + `mypy` clean across all modified `.py` files
- [ ] `npm --prefix site run build` succeeds
- [ ] `.claude/skills/experiments/SKILL.md` exists, validates via `generate-skill/scripts/validate.sh`, ≤ 5000 words
- [ ] `experiments/falzflyer-p2-mein-plan-v2/` v2 run rendered end-to-end with ≥ 10 variants; 0 dropped (or all drops logged with structured violations)
- [ ] Flo voting session + corpus update committed — **closes both #30 and #29 T15**
- [ ] Production falzflyer template rendering byte-stable (no regression to existing templates — `git diff site/public/templates/` empty)

</verification>

<success_criteria>

These map 1:1 to ISSUE.md's 10 acceptance criteria and the dual-closure merge gate:

1. `.claude/skills/experiments/SKILL.md` authored via `generate-skill`, three-layer model + 4 subcommands + v1 lessons. [T14]
2. `experiments/_schema/constraints.schema.yaml` validates with `jsonschema` Draft 2020-12. [T01]
3. `experiments/_constraints/falzflyer-default.yml` lists 16 BRAND_CONSTRAINTS + 22 Layer-1 thresholds. [T02]
4. `tools/experiment_hypothesis_gen.py` consumes envelope, threads it into 4-token prompt. [T08]
5. `tools/experiment_generate/prompt_template.md` includes envelope section + v1 anti-examples token. [T07]
6. `tools/experiment_render.py` gates every variant on full envelope; failed variants logged with structured violations. [T05]
7. `design-guide/README.md` names Layer-1 + 16 BRAND_CONSTRAINTS as the experiment constraint envelope; source-code docstrings corrected. [T05, T10]
8. `experiments/falzflyer-p2-mein-plan-v2/` v2 run rendered end-to-end with ≥ 10 variants, all respecting envelope. [T11–T16]
9. Flo votes a v2 session, results JSON committed. [T17 MANUAL]
10. `design-guide/gruene-corpus.md` amended with **dual sections** (v1 envelope-necessity lesson + v2 density+form findings) — **this closes BOTH #29 T15 AND #30**. [T17 MANUAL]

</success_criteria>

<out_of_scope>

Per CONTEXT.md "Deferred" section + ISSUE.md "Out of scope (phase 2)" — the executor MUST NOT do any of the following:

- Generalising envelope to non-falzflyer templates (zeitung, poster, postkarte). The `falzflyer-default.yml` is the only envelope this issue ships.
- Multi-rater merging (Flo is the only rater for v2).
- Auto-corpus-update from results (still manual via the runbook in T17; the skill captures the manual workflow).
- Hypothesis-prompt evolution beyond v1 anti-examples (full prompt evolution is a separate issue once ≥2 experiments have run).
- Adaptive pair sampling (Glicko/Elo).
- Bradley-Terry / Elo ranking.
- Hierarchy strategy as a separate v3 experiment, headline tone as a v4 — acknowledged but out-of-scope.
- Adding fonts to `shared/ci.yml` (font registration is its own concern; T12 verifies Vollkorn Black exists, does not add).
- Touching `bin/experiment-*` entry-point scripts (they already work; the skill dispatches to them).

If a task seems to require any of the above, halt and surface to the planner — do NOT silently expand scope.

</out_of_scope>
