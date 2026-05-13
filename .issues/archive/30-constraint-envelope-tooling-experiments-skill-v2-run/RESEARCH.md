# Research Synthesis — Issue #30

Three parallel sub-agents researched codebase / ecosystem / pitfalls. Full outputs live in `research/codebase.md`, `research/ecosystem.md`, `research/pitfalls.md`. This synthesis is what the planner reads first.

**Overall confidence: HIGH.** Zero new dependencies. Every locked decision in CONTEXT.md composes against existing code with clearly-identified slots.

---

## User Constraints (from CONTEXT.md — locked, verbatim)

1. **All 16 `BRAND_CONSTRAINTS` enforced as floor by default** for every variant. Per-experiment `constraints.yml` declares the tested axis and may explicitly relax named rules with rationale. Implicit relaxations forbidden.
2. **Layer-1 deterministic rules from `design-guide/README.md`** (the table at lines 24–46) are part of the envelope alongside `BRAND_CONSTRAINTS`.
3. **Reverses CONTEXT decision #4 from issue #29.** Variants are research artifacts ABOUT one axis; the envelope is enforced.
4. **v2 tested axis: information density + form.** Hypotheses span 1-item manifesto → 3-item list with body → 5-item sparse → quote/testimony → paragraph-form → numbered-with-scale. Everything except content density/form is constraint.
5. **Three v1 concepts retained as "concept retained, execution re-implemented":** numbered with weighted scale per rank; single editorial manifesto sentence; left-aligned items separated by thin Dunkelgrün rules. Remaining ~9 fresh for density+form.
6. **All 12 v1 variants embedded as named "do-not-repeat these failure modes" anti-examples** in the v2 generation prompt — including the three retained, tagged "concept retained, broken implementation here is the anti-example, not the idea."
7. **Skill at `.claude/skills/experiments/SKILL.md`** with four subcommand verbs (`new` / `generate` / `render` / `capture`) dispatching to existing `bin/experiment-*` tools. Authored via `generate-skill`.
8. **Gate location: `tools/experiment_render.py`** mirrors the existing `inside_page` drop pattern. Dropped variants in `manifest.json::_dropped` with structured violations, excluded from voting, surfaced in SUMMARY.md.
9. **v2 run end-to-end + corpus update is the mandatory merge gate** — closes both #30's gate AND issue #29's deferred T15 in one move.

---

## Summary

**Primary recommendation:** the MVP is again almost entirely composition of existing pieces. The plan covers three additions, six edits, and one new skill.

**Three new artifacts:**
- `experiments/_schema/constraints.schema.yaml` (JSON Schema Draft 2020-12).
- `experiments/_constraints/falzflyer-default.yml` (the 16 `BRAND_CONSTRAINTS` + the 22 Layer-1 rules from `design-guide/README.md:24–46`).
- `tools/experiment_envelope.py` — light wrapper that composes `BRAND_CONSTRAINTS` + new Layer-1 predicates, exposes `load_envelope()`, `run_envelope(doc, envelope) -> list[Violation]`, `format_envelope_markdown(envelope) -> str`.

**Six edits to shipped code:**
- `tools/experiment_render.py:165` — replace `_inside_page_violations(doc)` with `_envelope_violations(doc, envelope)` (the single line that fixes the v1 failure mode).
- `tools/experiment_render.py:289–303` — drop log + manifest entry extended with structured `violations: [{rule_id, message, severity}]`.
- `tools/experiment_render.py:11–14` and `:135–137` — docstrings corrected (delete "no other brand rule runs on variants").
- `tools/experiment_hypothesis_gen.py:84–95` — `render_prompt()` token surface grows from 2 to 4 (adds `{constraint_envelope}`, `{v1_anti_examples}`).
- `tools/experiment_generate/prompt_template.md` — three insertion points; envelope between current §"What counts as structurally distinct" (line 29) and §"Examples" (line 31); v1 anti-examples between §"Examples" (after line 54) and §"Anti-collapse" (before line 56); new bullet 6 in §"Final check".
- `experiments/_schema/manifest.schema.yaml` — extend `_dropped` item shape to include `violations` array.

**One new skill:**
- `.claude/skills/experiments/SKILL.md` authored via the existing `generate-skill` skill (`/root/.claude/skills/generate-skill/`). Multi-verb dispatch is **one** skill with `$1` arg branching — verified via ecosystem research and confirmed by codebase pattern-hunt across the 10 globally-installed skills. No formal subcommand API exists.

**Documentation corrections (not "reversals"):**
- `design-guide/README.md` gets an **additive** paragraph below Layer-1 table — the wrong framing isn't in this file (file is greenfield re experiments; `grep -n "experiments\|variant" design-guide/README.md` returns nothing). The reversal target is in #29's RESEARCH.md / PLAN.md and the source-code docstrings cited above.
- `design-guide/gruene-corpus.md` §6 gets a one-line cross-reference to `.claude/skills/experiments`.

**Most consequential finding** (from pitfalls research): v1's pitfalls research flagged `inside_page` as a gate but **didn't generalize**. The existing render gate enforces only `brand:inside_page` (verified by grep). The other 15 `BRAND_CONSTRAINTS` + 22 Layer-1 rules were never gates — that's the exact category error this issue exists to fix, and the fix is a single-line change at `experiment_render.py:165` paired with the envelope schema + loader.

---

## Codebase Analysis

### The 16 BRAND_CONSTRAINTS — verified registry

`tools/sla_lib/builder/brand_constraints.py` is 1681 lines. Module docstring lines 1–43 enumerates exactly 16 rules. Registry at `BRAND_CONSTRAINTS = [...]` lines 1525–1680.

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

// tools/sla_lib/builder/constraints.py - Violation shape
@dataclass
class Violation:
    severity: str       // "error" | "warning"
    rule_id: str
    message: str
    targets: tuple[str, ...] = ()
</interfaces>

**The 16 rules** (id, registry line, default severity — all are floor for v2):

| # | id | registry line | severity | Layer-1 mirror? |
|---|---|---|---|---|
| 1 | `brand:color_palette` | 1526 | error | mirrors `brand_colors_only` |
| 2 | `brand:font_family` | 1533 | error | (covered by ≤2 type families) |
| 3 | `brand:line_spacing_0.9` | 1539 | error | (no L1 mirror) |
| 4 | `brand:hl_sl_distance_x2` | 1545 | error | (no L1 mirror) |
| 5 | `brand:logo_size_3M` | 1551 | error | mirrors `logo_size_print` |
| 6 | `brand:text_on_green` | 1557 | error | mirrors `type_on_white_plate_forbidden` |
| 7 | `brand:bleed_3mm` | 1563 | error | (CD-Quickguide) |
| 8 | `brand:wahlkreuz_colored_bg` | 1569 | error | — |
| 9 | `brand:inside_page` | 1575 | error | (already enforced today) |
| 10 | `brand:spine_safety` | 1582 | warning | — |
| 11 | `brand:bleed_coverage` | 1593 | error | — |
| 12 | `brand:image_text_overlap` | 1606 | error | — |
| 13 | `brand:cover_extent_match` | 1617 | warning | — |
| 14 | `brand:visual_adjacency_drift` | 1629 | warning | — |
| 15 | `brand:image_fills_frame` | 1644 | error | — |
| 16 | `brand:band_consistency` | 1666 | error | — |

### Existing gate pattern (in shipped `tools/experiment_render.py`)

<interfaces>
// tools/experiment_render.py:130-143 — REPLACE this
def _inside_page_violations(doc) -> list:
    from sla_lib.builder import BRAND_CONSTRAINTS
    rule = next((r for r in BRAND_CONSTRAINTS if r.id == "brand:inside_page"), None)
    if rule is None:
        return []
    primitives = list(doc.iter_all_primitives()) if hasattr(doc, "iter_all_primitives") else []
    return [v for v in rule.check(primitives, doc) if v.severity == "error"]

// experiment_render.py:289-303 — extend drop log + manifest entry
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

// experiment_render.py:337-341 — manifest shape (v2 schema bump adds structured violations)
manifest_out["_dropped"] = [
    {"slug": s, "reason": r, "violations": [...]} for (s, r) in dropped
]
</interfaces>

### Existing prompt-template extension points

`tools/experiment_generate/prompt_template.md` — 107 lines. Token substitution surface today is exactly `{subject}` + `{weak_area_quote}` (`experiment_hypothesis_gen.py:84-95`). v2 adds `{constraint_envelope}` + `{v1_anti_examples}` to the tokens tuple at line 91 and to the call sites at lines 507-528.

Insertion points (preserves existing structure):
- "Constraint envelope (HARD floor)" between line 29 and 31 — upstream of examples.
- "v1 anti-examples — DO NOT REPEAT" between line 54 (after good/bad examples) and line 56 (before anti-collapse). Source from new file `tools/experiment_generate/v1_anti_examples.md` to keep template clean.
- Bullet 6 in "Final check" (line ~100): "Does every hypothesis respect the constraint envelope?"

### Three retained v1 concepts — current code and corrections needed

All under `experiments/falzflyer-p2-mein-plan/variants/`.

**`numbered-priority-list.py`** — current: 5 rows at constant 28pt with thin 0.4mm Dunkelgrün rules. **v2 correction:** weighted scale per rank — numerals shrink from #1 to #5 on a published progression (planner picks: e.g., 36/30/24/20/16pt or harmonic series). Other elements held within envelope.

**`manifesto-single-statement.py`** — current: one Vollkorn Black 30pt sentence at `x=105 y=72 w=87 h=120` ("Mödling muss vorangehen — beim Klima, beim Wohnen, beim Zuhören."). Geometry already respects basic envelope (72+120=192 < 213mm panel). v1's broken implementation likely Vollkorn weight + footer text-on-green compatibility. **v2 correction:** verify Vollkorn Black is in `shared/ci.yml::fonts`; re-render under envelope gate.

**`asymmetric-editorial-rules.py`** — current: 5 items Gotham Narrow Bold 18pt at `x=105` (6mm in from inside-panel edge), thin 0.4mm Dunkelgrün rules between rows. Layout intent already respects most envelope rules. **v2 correction:** verify negative-space ≥30% (5 rows × 22mm = 110mm of content in 130mm available leaves only 15% whitespace below — likely the v1 fail). Reduce row count to 3 OR reduce row height so whitespace target is met.

### Skill authoring

<interfaces>
// /root/.claude/skills/generate-skill/SKILL.md — author tool
// 6-step process:
//   1. Examples-first (2-5 concrete usage examples)
//   2. Plan progressive disclosure (Level 1 frontmatter / Level 2 SKILL.md / Level 3 references/)
//   3. Initialize via scripts/init_skill.py
//   4. Edit imperatively
//   5. Validate via scripts/validate.sh (wc -w < 5000)
//   6. Iterate
// MANDATORY first action: WebFetch
//   https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices

// .claude/skills/experiments/SKILL.md frontmatter
---
name: experiments
description: |
  Run constraint-envelope design experiments with pairwise voting.
  Auto-activates on /experiments <verb> where <verb> ∈ {new, generate, render, capture}.
  Encodes the three-layer model (envelope / variation surface / implementation),
  the corpus-update merge gate, and v1's failure-mode lessons.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
argument-hint: "[new|generate|render|capture] <experiment-id>"
---

// Verified: no formal subcommand API exists in Claude Code.
// Multi-verb pattern is single SKILL.md branching on $1 positional arg.
// Confirmed by inspection of /root/.claude/skills/{orchestrator,work-summary,...}
</interfaces>

Full file inventory + composition map in `research/codebase.md` §11.

---

## Standard Stack

**Net new dependencies for MVP: ZERO.** Everything composes against tooling already in `Dockerfile.claude` or shipped by issue #29.

| Tool / Library | Version | Status |
|---|---|---|
| PyYAML | 6.0.3 | already pinned, `safe_load` only |
| jsonschema | 4.26.0 | already pinned, Draft 2020-12 |
| Astro | 5.18.1 | already installed |
| `claude` CLI | 2.1.132 | already authenticated |
| `codex` CLI | 0.128.0 | already authenticated |
| `gemini` CLI | 0.41.2 | already authenticated (optional in mix) |
| `generate-skill` workspace skill | global | invoked via Skill tool |
| Scribus 1.6 + xvfb-run + pdftoppm | system | shipped |

---

## Don't Hand-Roll

| Problem | Use instead |
|---|---|
| Constraint solver | Extend the predicate-style `BrandRule` (see `tools/sla_lib/builder/brand_constraints.py:64-87`). The module docstring explicitly says "do not reach for kiwisolver or z3." |
| YAML schema validation | `jsonschema.Draft202012Validator.iter_errors()` (returns full error list, not just first) |
| Constraint inheritance/override | Shallow override on rule-id map with explicit `extends:` + named `relax:` list (Helm / Ansible idiom). |
| Anti-example format in prompt | `slug + violation + rule-id` triples with rationale. **Not** bare negations — NeQA research shows negation-only prompts degrade at scale. |
| Multi-verb skill dispatch | Single `SKILL.md` branching on `$1`. No plugin API to register against. |
| Drop-loop pattern | Mirror `experiment_render.py:289-303` exactly (already there for `inside_page`). |
| Render gate trust model | Validate the rendered artifact (the `Document` post-build), **not** the variant module's self-report. Variant code could in principle disable a check; the gate must run post-build, pre-Scribus. |

---

## Architecture Patterns (Composition Map)

```
ENVELOPE SCHEMA       experiments/_schema/constraints.schema.yaml         [NEW]
       ↓
ENVELOPE DEFAULT      experiments/_constraints/falzflyer-default.yml      [NEW]
       ↓                  - brand_rules: all 16 ids
       ↓                  - layer1: the 22 thresholds from design-guide/README.md:24-46
PER-EXPERIMENT YAML   experiments/falzflyer-p2-mein-plan-v2/constraints.yml [NEW]
       ↓                  - extends falzflyer-default.yml
       ↓                  - tested_axis: density+form
       ↓                  - relax: []
LOADER + WRAPPER      tools/experiment_envelope.py                        [NEW]
       │              - load_envelope(exp_dir) -> Envelope
       │              - run_envelope(doc, envelope) -> list[Violation]
       │              - format_envelope_markdown(envelope) -> str
       ├──────────────────┐
       ▼                  ▼
RENDER GATE          PROMPT THREAD
  experiment_render.py    experiment_hypothesis_gen.py             [EDIT]
  :165 replace            :84-95 render_prompt() learns 4 tokens
  :289-303 drop log       :507-528 load envelope before render_prompt
  :11-14, :135-137        SUBJECT_METADATA gets v2 entry
    docstring fix         prompt_template.md gets 3 inserts        [EDIT]
                          v1_anti_examples.md NEW
       │
       ▼
DROP LOG              experiments/<exp>/manifest.json::_dropped   [SCHEMA BUMP]
       ↓              manifest.schema.yaml extends _dropped item
SUMMARY SURFACING     experiment_results.py                       [EDIT]
                      new "## Variants dropped during render" section

SKILL CARRIER         .claude/skills/experiments/SKILL.md         [NEW via generate-skill]

DOC CORRECTION        design-guide/README.md                      [ADDITIVE PARA]
                      design-guide/gruene-corpus.md §6            [ONE-LINE NOTE]
                      experiment_render.py docstrings             [REVERSAL]
                      .issues/29/RESEARCH.md + PLAN.md            [HISTORICAL — leave]

VERIFICATION RUN      experiments/falzflyer-p2-mein-plan-v2/      [GENERATED]
                      results/flo-<DATE>.json                     [VOTING SESSION]
                      design-guide/gruene-corpus.md amended       [MERGE GATE]
```

---

## Common Pitfalls (Top 5)

From `research/pitfalls.md`:

1. **Render gate must validate the artifact, not trust the variant's self-report, and load rules dynamically from the envelope YAML — no hardcoded thresholds.** Single fix that prevents v1's exact failure recurring and prevents invariant drift between YAML and code.

2. **Reconcile the three retained v1 concepts with v2's declared density+form axis.** Numbered-with-weighted-scale tests hierarchy strategy as much as density; manifesto tests density (1 item) AND form (sentence); dunkelgrün-rules tests form (separator) but also density. **Mitigation:** the hypothesis prompt requires declared `axis_commitment` per hypothesis; the planner specifies each retained concept's primary axis explicitly so the LLM-as-judge dedup step doesn't kick them out.

3. **Drop and regeneration policy specified explicitly.** Auto-retry with feedback ("regenerate hypothesis N — violated rule X with message Y"), max 2 rounds, halt + human review at >40% drop rate. Without this, "0 dropped" gets gamed by the LLM producing maximally-safe (low-information) variants. Add as a config knob in `constraints.yml` with sensible defaults.

4. **Skill is the canonical entry point, not a wrapper.** Each verb in `SKILL.md` includes pre-flight checks (envelope exists, axis declared, brand fonts on PATH) and post-step assertions. README + design-guide point at the skill. `bin/experiment-*` should not be invoked directly except for debugging.

5. **Corpus update is TWO clearly-labeled parts.** Part 1: v1 meta-lesson on envelope necessity (closes #29 T15). Part 2: v2 substantive density+form findings (closes #30). Cross-referenced with provenance. The `/experiments capture` verb produces a templated SUMMARY.md with both sections pre-stubbed so the lesson doesn't blur.

---

## Environment Audit

Verified on 2026-05-10 (no regressions since #29):

- `python3` 3.13.5, `node` v26.0.0, `npm` 11.12.1, `gh` 2.92.0 — all OK
- `scribus` system + `xvfb-run` available
- `claude` CLI 2.1.132, `codex` CLI 0.128.0, `gemini` CLI 0.41.2 — all on PATH, authenticated
- Brand fonts: 42 face entries in fc-list at `/usr/local/share/fonts/gruene/`
- `PyYAML` 6.0.3, `jsonschema` 4.26.0, `Pillow` 12.2.0 — pinned via Dockerfile.claude
- `.claude/skills/` does NOT exist in workspace — `experiments` will be the first local skill
- `experiments/_constraints/` does NOT exist — greenfield
- `experiments/_schema/manifest.schema.yaml` exists (shipped by #29) — extend, don't replace
- v1 dir `experiments/falzflyer-p2-mein-plan/` + `_llm-raw/` outputs preserved on the worktree branch (was on main after #29 merge)
- `/root/.claude/skills/generate-skill/` confirmed, full SKILL.md readable, `scripts/init_skill.py` and `scripts/validate.sh` shipped

**No blockers.**

---

## Project Constraints

- **No `CLAUDE.md` at workspace root.** No project-level Claude directives beyond CONTEXT.md and `README.md`.
- Build flow unchanged from #29: `python3 templates/<id>/build.py` → SLA → `xvfb-run scribus` → PDF → `pdftoppm` PNG.
- Brand fonts NOT in repo — render hard-fails without them, gate at `tools/render_pipeline.py:257-278`. Variant rendering must run in Dockerfile.claude container.
- **Layer-1 table is 22 rows, not 21 as the issue prose claims** (16 hcd rules + 6 CD-Quickguide rules in `design-guide/README.md:24-46`). Planner: reference the line range, not the count, to avoid ambiguity.
- Anname strings are case-sensitive identifiers with em-dash literal U+2014. Variants targeting P2 keep the `P2 ` prefix.
- Existing convention: `main(argv=None) -> int` entry-points so `bin/<name>` shim works; YAML-first config; honest exit codes (0 pass / 1 fail); fail loudly to stderr.

---

## Sources

### HIGH confidence (verified by direct inspection)
- `tools/sla_lib/builder/brand_constraints.py:1-43, 64-87, 1525-1680` (the 16 rules + BrandRule contract)
- `tools/sla_lib/builder/structural_check.py:118, 166-204` (existing brand-rule loop pattern)
- `tools/sla_lib/builder/constraints.py` (Violation dataclass)
- `tools/experiment_render.py:11-14, 130-143, 150-208, 270-272, 289-303, 337-341` (gate slot + drop loop + docstring reversal target)
- `tools/experiment_hypothesis_gen.py:50, 62-77, 84-95, 231-235, 473-474, 506-528` (token surface, role priming, SUBJECT_METADATA, axis vocabulary)
- `tools/experiment_generate/prompt_template.md:1-107` (3 insertion points)
- `experiments/falzflyer-p2-mein-plan/variants/{numbered-priority-list,manifesto-single-statement,asymmetric-editorial-rules}.py` (retained concepts code, end-to-end)
- `/root/.claude/skills/generate-skill/SKILL.md` (6-step authoring process)
- `design-guide/README.md:24-46` (Layer-1 table, 22 rows)
- `.issues/29-.../RESEARCH.md:248,268` and `PLAN.md:33,229,415` (wrong framing source — historical)
- Local environment audit commands run 2026-05-10

### HIGH confidence (verified external)
- [Claude Code skills docs](https://code.claude.com/docs/en/skills) — auto-discovery, no registry, multi-verb via `$1`
- [Skill authoring best practices (Anthropic)](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — referenced by generate-skill
- [skill-development SKILL.md (anthropics/claude-code)](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/skill-development/SKILL.md)
- [JSON Schema conditionals](https://json-schema.org/understanding-json-schema/reference/conditionals)
- [python-jsonschema validate](https://python-jsonschema.readthedocs.io/en/stable/validate/)
- [Why positive prompts outperform negative (Gadlet)](https://gadlet.com/posts/negative-prompting/)
- [Ansible variable precedence](https://docs.ansible.com/ansible/latest/reference_appendices/general_precedence.html)

### MEDIUM confidence
- Multi-verb skill dispatch is convention not API — surfaced by ecosystem and codebase research; no contradicting evidence found but no canonical Anthropic doc explicitly authorizes it either. Worth re-validating during the executor's first `generate-skill` WebFetch.
- Layer-1 table row count: prose says 21, file has 22. Confirmed by direct count.
- The three retained concepts' specific envelope violations are *inferred* from variant code; verifying against the rendered PNGs is recommended before committing to the corrections in §"Three retained v1 concepts."
