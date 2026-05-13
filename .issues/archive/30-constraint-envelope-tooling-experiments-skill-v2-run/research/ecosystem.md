# Ecosystem research — Issue #30 (constraint envelope + experiments skill)

Researched: 2026-05-10. Most of the rendering / voting / multi-LLM stack was locked by issue #29's RESEARCH.md; this file covers only the new ground: skill authoring, constraint-engine integration, and constrained-generation prompt patterns.

---

## 1. Claude Code skill authoring — official conventions

**Confidence: HIGH** (Anthropic platform docs + Claude Code docs, fetched 2026-05-10).

### Where skills live & how they are discovered

- Project skills live at `.claude/skills/<skill-name>/SKILL.md`; personal skills at `~/.claude/skills/<skill-name>/SKILL.md`. ([Claude Code skills docs](https://code.claude.com/docs/en/skills))
- Discovery is automatic: "Claude Code scans these directories and reads a brief description from each Skill" at session startup, giving Claude "a lightweight index of available capabilities". No registry, no manual install. ([Claude Code skills docs](https://code.claude.com/docs/en/skills))
- Live change detection: adding/editing a skill under `.claude/skills/` "takes effect within the current session without restarting" — only top-level dir creation needs a restart. ([Claude Code skills docs](https://code.claude.com/docs/en/skills))
- The directory name is the slash command: `.claude/skills/experiments/SKILL.md` → `/experiments`. ([Claude Code skills docs](https://code.claude.com/docs/en/skills))

### Frontmatter (verified, current)

Required: `description`. Optional: `name`, `allowed-tools`, `model`, `disable-model-invocation`, `user-invocable`, `argument-hint`, `arguments`, `effort`, `context`, `agent`, `paths`, `hooks`. Validation: `name` ≤64 chars, lowercase+hyphens; `description` ≤1024 chars (combined with `when_to_use` capped at 1536). ([Claude Code frontmatter reference](https://code.claude.com/docs/en/skills); [Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))

### Multi-verb dispatch — the question Issue #30 asked

There is **no separate-skill-per-verb pattern** in the official docs. Two idiomatic options, both supported:

1. **One skill, verb dispatch in the body.** The skill takes `$ARGUMENTS` (or `$0`, `$1` for positional indexing), and the body branches on the first arg. `argument-hint: "[new|generate|render|capture] <id>"` shows users the verbs in autocomplete. This is what `/experiments` should do — one skill, four verbs in body. ([Pass arguments to skills](https://code.claude.com/docs/en/skills))
2. **Multiple sibling skills in a domain prefix.** E.g. `experiments-new`, `experiments-generate` — each its own dir + SKILL.md. The Anthropic skill repo and bundled skills (`/simplify`, `/debug`, `/loop`) all use single-skill granularity. The `issue:*` family in this workspace uses **colon-namespaced single skills** (`issue-new`, `issue-research` etc., not literal colons in directory names — colons aren't allowed in directory names; the colon in `/issue:research` is implemented either as `issue-research` directory OR as a single `issue` skill with a verb arg). The docs don't actually mention colon namespacing — that's a community pattern.

**Recommendation for #30:** Single skill `.claude/skills/experiments/SKILL.md`, verb dispatch via `$1` (first positional arg = verb), supporting files in `references/` for per-verb detail. This matches the `pdf-processing` worked example in the official docs and keeps the four verbs visible as one cohesive workflow. Confirmed pattern from PDF skill in best-practices doc.

### Body length & structure

- Hard target: **<500 lines** for SKILL.md body, **<5k words / ~5k tokens** total. ([Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))
- Progressive disclosure (3 levels): metadata always loaded → SKILL.md body loaded when triggered → references/scripts loaded on-demand by Claude.
- One level deep only — `SKILL.md → references/X.md` is allowed; `references/X.md → references/Y.md` is **not** because Claude will partial-read with `head -100`. ([Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))
- **Imperative voice required**: "To do X, run Y" not "You should do X". Third person in description: "This skill … " not "Use this skill …". ([Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))

### Skill content lifecycle (matters for our process-doc skill)

Once invoked, SKILL.md content "enters the conversation as a single message and stays there for the rest of the session. Claude Code does not re-read the skill file on later turns" — so write standing instructions, not one-time steps. After auto-compaction, the most-recent invocation's first 5,000 tokens are re-attached, with a 25k combined budget across all skills. ([Skill content lifecycle](https://code.claude.com/docs/en/skills))

---

## 2. The `generate-skill` skill in this workspace

**Confidence: HIGH** (read directly from `/root/.claude/skills/generate-skill/`).

Located at `/root/.claude/skills/generate-skill/` (personal scope). Frontmatter:

```yaml
name: generate-skill
description: MUST BE USED when creating new Claude Code skills or refactoring existing skills. Automatically references latest official documentation for skill authoring best practices...
allowed-tools: Read, Write, Edit, MultiEdit, Bash, Grep, Glob, WebFetch
```

It encodes Anthropic's 6-step workflow with a Phase-0 decision gate (skill vs agent vs command), bundles five reference files (`BEST-PRACTICES.md`, `DECISION-FRAMEWORK.md`, `EXAMPLES.md`, `PROGRESSIVE-DISCLOSURE.md`, `TEMPLATES.md`, `COMPARISON.md`) and two scripts (`scripts/init_skill.py`, `scripts/validate.sh`). The MANDATORY first step is `WebFetch` of the latest best-practices doc, then read the bundled references.

**How to invoke for our case:** Trigger the skill (e.g. say "create a skill for the experiments workflow"), it auto-fetches the doc, asks for 2-5 concrete examples, plans the structure, runs `scripts/init_skill.py` to scaffold, writes SKILL.md + bundled resources, then runs `scripts/validate.sh` for word-count / structure / reference checks. The skill expects the planner to provide the 2-5 examples and the verb list up front so it doesn't re-derive them.

**Implication for #30 plan:** Don't write the experiments skill by hand. Run `/generate-skill` (or invoke the skill via natural-language trigger) with: the 4 verbs, the 3-layer model summary, 2-5 example interactions per verb, the bundled-resources plan (e.g. `references/v1-lessons.md`, `references/three-layer-model.md`, `references/anti-examples.md`).

---

## 3. Skills best practices — what makes a good process-encoding skill

**Confidence: HIGH** (Anthropic best-practices doc, fetched 2026-05-10).

For methodology skills like ours:

- **Workflow/checklist pattern is officially endorsed.** The doc shows a "Research synthesis workflow" example with a copyable checklist as a code block — Claude copies it into its response and checks items off. Use this for `/experiments new`, `/experiments render`, etc. ([Workflows and feedback loops](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))
- **Conditional workflow pattern** (decision-tree branching by verb) is also documented — perfect for our verb dispatch.
- **Feedback-loop pattern** (run validator → fix → repeat) — applies directly to envelope gating in `/experiments render`.
- **Specificity matching:** for our gate (envelope check) prefer **low-freedom** ("Run exactly this script: `python tools/experiment_render.py …`. Do not modify the command."). For hypothesis generation prefer **medium freedom** (template + parameters). For envelope authorship: **high freedom** (text instructions).
- **Avoid time-sensitive info.** Don't put "as of v1 …" in body; put it in `references/v1-lessons.md` with a "## Old patterns" section.
- **Three evaluations recommended** before sharing the skill. For #30: "scaffold a new experiment", "render a v2 batch", "capture corpus update" — three eval scenarios.

---

## 4. JSON Schema 2020-12 + python-jsonschema 4.26.0

**Confidence: HIGH** (existing repo deps verified: `jsonschema 4.26.0`, `PyYAML 6.0.3`; official schema docs).

The repo already uses Draft 2020-12 — see `experiments/_schema/manifest.schema.yaml` line 12: `$schema: "https://json-schema.org/draft/2020-12/schema"`. **Mirror this style for `constraints.schema.yaml`.**

### Conditional patterns for "rule X applies UNLESS relaxed"

Two viable encodings ([JSON Schema conditionals](https://json-schema.org/understanding-json-schema/reference/conditionals); [if applicator 2020-12](https://www.learnjsonschema.com/2020-12/applicator/if/)):

- **`if`/`then`/`else`**: classic conditional. "If `relax` does not include `brand:band_consistency`, then `band_consistency.enforced` must be true."
- **`allOf` with conditionals**: cleaner for many independent rules — one `allOf` entry per BRAND_CONSTRAINT.

For our case the schema is mostly **structural** (validates the shape of `constraints.yml`: which keys exist, which values are allowed, which `relax` ids resolve to known rule ids). The actual envelope-enforcement-with-relaxations logic lives in Python (`tools/experiment_envelope.py` or extension of `structural_check.py`), not in JSON Schema. Use `enum` for the rule-id list (single source of truth, derived from `BRAND_RULES` IDs in `brand_constraints.py`).

### Validation API

Use `Draft202012Validator(schema).iter_errors(instance)` to get **all** errors (not just first). This matches `_render_helpers.py` patterns elsewhere in repo. ([python-jsonschema validate docs](https://python-jsonschema.readthedocs.io/en/stable/validate/))

```python
from jsonschema import Draft202012Validator
errors = sorted(Draft202012Validator(schema).iter_errors(cfg), key=lambda e: e.path)
```

---

## 5. Constraint inheritance / override patterns

**Confidence: MEDIUM** (industry practice, Ansible+Hiera+Helm docs).

The closest mainstream analog is **Ansible group_vars / role defaults** ([Ansible variable precedence](https://docs.ansible.com/ansible/latest/reference_appendices/general_precedence.html)): defaults provide the floor, group_vars override per environment, host_vars override per host, extra-vars wins. Helm `values.yaml` + `--set` follows the same shape: deep merge with user override winning.

**Pattern to adopt for `_constraints/falzflyer-default.yml` → per-experiment `constraints.yml`:**

- `falzflyer-default.yml` is the floor (named rule list with `enforced: true`).
- Per-experiment `constraints.yml` declares `extends: falzflyer-default` (explicit, like Helm sub-charts) and a `relax:` list that maps `rule-id → rationale`.
- Loader does a **shallow** override (rule-id → rule-config map merge) — NOT deep-merge a single mega-tree. Shallow keeps the audit trail clean: every relaxation is a named entry in `relax:`. This matches CONTEXT decision #2 ("relaxations must be named").

---

## 6. Constrained-generation prompt engineering

**Confidence: MEDIUM-HIGH** (Anthropic + recent constrained-decoding research; design-specific guidance is HIGH-confidence anti-pattern, MEDIUM on positive technique).

### Phrasing hard constraints

- **Use "MUST" and "MUST NOT".** Strong modal verbs measurably improve compliance. ([Lakera prompt engineering guide 2026](https://www.lakera.ai/blog/prompt-engineering-guide))
- **Avoid bare negation; prefer positive directives plus "do not" qualifiers.** Research finds negation-only instructions degrade as models scale (NeQA benchmark). ([Why positive prompts outperform negative ones — Gadlet](https://gadlet.com/posts/negative-prompting/)) Concretely: "Body text MUST be ≥10pt" not "Body text must not be smaller than 10pt".
- **Constraint placement: at the top.** Constraints should appear before the creative ask, not after. (Standard Anthropic prompt-engineering guidance.)
- **Group MUST and MAY into a two-column block.** Issue #30's draft already nails the format — keep it. Example from issue body: "MUST respect: ≥6mm panel margin, ≥30% negative space, body ≥10pt; MAY vary: hierarchy, density, item count, accent strategy".
- **Hard constraints in prompts are not formal guarantees.** Soft (prompt-level) constraints + post-hoc validation (our envelope gate) is the documented pattern; pure prompt-level constraints lack feasibility guarantees in combinatorial settings. ([Hard Constraints Meet Soft Generation, arXiv 2025](https://arxiv.org/html/2602.01090); [Dataiku structured generation guide](https://www.dataiku.com/stories/blog/your-guide-to-structured-text-generation)) **This is why the gate at render time is non-negotiable.**

### Negative / anti-examples

Industry guidance is split:
- Negative *instructions* ("don't say X") underperform. ([Gadlet](https://gadlet.com/posts/negative-prompting/))
- Negative *examples with rationale* ("here's a v1 variant slug + the specific envelope-violation it committed; do NOT replicate") work as **boundary-setting** alongside positive examples. The same source: "Positive examples define the center of the target, negative examples define the edges."

**For #30:** Format each v1 anti-example as `slug + violation reason + rule-id`, not "this is bad, don't do it." Tag retained-concept anti-examples explicitly per CONTEXT decision #9 ("concept retained as a separate retried-with-envelope variant; this anti-example is about the v1 broken IMPLEMENTATION specifically, not the idea"). This is the format that has both rationale AND boundary-setting properties.

---

## 7. Skill discovery — final answer

**Confidence: HIGH.** Auto-discovery, no registry. Once `.claude/skills/experiments/SKILL.md` is committed, the next session sees `/experiments`. Live-change detection picks up edits within the current session. The slash command name is the directory name. ([Claude Code skills docs](https://code.claude.com/docs/en/skills))

Note the colon namespacing in this workspace's `issue:*` skills is implemented at the file system as either single-dir (e.g. `issue-research/`) or as a verb-dispatching `issue/` skill — not as a literal `issue:research/` directory (colons aren't valid in many filesystems). Verify by looking at `.claude/skills/` once it exists; for our case, single `experiments/` directory with verb dispatch is canonical.

---

## Standard Stack — new dependencies only (most locked by #29)

| Library / Tool | Version | Purpose | Why standard | Confidence |
|---|---|---|---|---|
| `jsonschema` | 4.26.0 (already pinned) | Validate `constraints.yml` against `constraints.schema.yaml` (Draft 2020-12) | Already in repo; `Draft202012Validator.iter_errors` is the canonical multi-error API | HIGH |
| `PyYAML` | 6.0.3 (already pinned) | Load YAML envelopes & schemas | Already in repo; mirrors `manifest.schema.yaml` style | HIGH |
| `generate-skill` skill | personal scope, present | Author the experiments SKILL.md per Anthropic's 6-step process | Documented in this workspace; skips all rediscovery | HIGH |
| Claude Code skills system | built-in | Auto-discover `.claude/skills/experiments/` | Native; no install step | HIGH |

**No new package additions required.** Everything else (Pillow, Ghostscript, Scribus, the multi-LLM CLI plumbing) was locked by issue #29.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Validating `constraints.yml` shape | Ad-hoc Python checks | `jsonschema.Draft202012Validator(schema).iter_errors(cfg)` | Already in repo; gives full error list for clear logs | 
| YAML inheritance / merge | Custom dict-merge | Shallow override on rule-id map (not deep-merge); explicit `extends:` + `relax:` keys | Matches Helm/Ansible idiom; auditable; CONTEXT #2 demands named relaxations |
| Skill scaffolding | Hand-written SKILL.md from scratch | Invoke `generate-skill` skill with verb list + 3-5 examples | Encodes Anthropic 6-step + word-count + structure validation |
| Constraint solver | Don't reach for `kiwisolver`, `z3`, `python-constraint` | Predicate-style `BrandRule` (already in `tools/sla_lib/builder/brand_constraints.py`) — extend, don't replace | Repo already locked this in issue #12+#22 RESEARCH; brand_constraints.py header literally says "do not reach for kiwisolver or z3" |
| Constrained decoding for hypotheses | Custom logit masking | Soft-constrain via prompt + post-hoc envelope gate at render | Soft-prompt + validate is the documented pattern; hard decoding doesn't fit our multi-LLM-via-CLI architecture |
| Negative-prompt anti-examples | Bare "don't do X" instructions | `slug + violation + rule-id` triples (boundary-setting with rationale) | Negation-only known to degrade with scale (NeQA); rationale-tagged negatives work |
| Verb dispatch in skill | One skill per verb | Single `experiments/` skill, branch on `$1` in body, `argument-hint: "[new|generate|render|capture] <id>"` | Mirrors official `pdf-processing` example; matches autocomplete UX |
| Word-count enforcement | Eyeball the SKILL.md | Run `generate-skill/scripts/validate.sh` | Already validates <5k words, structure, references one-level-deep |

---

## Sources

### HIGH confidence
- [Claude Code skills docs](https://code.claude.com/docs/en/skills)
- [Skill authoring best practices (Anthropic)](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [skill-development SKILL.md (anthropics/claude-code GitHub)](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/skill-development/SKILL.md)
- [JSON Schema conditionals reference](https://json-schema.org/understanding-json-schema/reference/conditionals)
- [`if` applicator 2020-12](https://www.learnjsonschema.com/2020-12/applicator/if/)
- [python-jsonschema validate docs](https://python-jsonschema.readthedocs.io/en/stable/validate/)
- Local read: `/root/.claude/skills/generate-skill/SKILL.md` + bundled references (BEST-PRACTICES, EXAMPLES, TEMPLATES, DECISION-FRAMEWORK, PROGRESSIVE-DISCLOSURE)
- Local read: `tools/sla_lib/builder/brand_constraints.py` (16 BrandRule IDs verified)
- Local read: `experiments/_schema/manifest.schema.yaml` (Draft 2020-12 style precedent)

### MEDIUM confidence
- [Ansible variable precedence](https://docs.ansible.com/ansible/latest/reference_appendices/general_precedence.html)
- [Lakera prompt engineering guide 2026](https://www.lakera.ai/blog/prompt-engineering-guide)
- [Why positive prompts outperform negative ones (Gadlet)](https://gadlet.com/posts/negative-prompting/)
- [Hard Constraints Meet Soft Generation (arXiv 2025)](https://arxiv.org/html/2602.01090)
- [Dataiku — structured text generation](https://www.dataiku.com/stories/blog/your-guide-to-structured-text-generation)
- [Controlling your LLM: Constrained Generation (Docherty, Medium)](https://medium.com/@docherty/controlling-your-llm-deep-dive-into-constrained-generation-1e561c736a20)

### LOW confidence (flagged)
- The exact filesystem layout of this workspace's `issue:*` skills (colon vs hyphen) — couldn't find a `.claude/skills/` directory in the worktree; `issue:*` may be implemented as plain commands in `.claude/commands/` (which still work per Claude Code docs). Planner should `ls .claude/commands/` and `ls .claude/skills/` in the main checkout before deciding the experiments skill layout.

---

## Confidence breakdown

| Area | Level | Reason |
|---|---|---|
| Skill authoring conventions | HIGH | Official platform + Claude Code docs verified 2026-05-10 |
| `generate-skill` workspace skill | HIGH | Read source directly |
| Skill best practices for process docs | HIGH | Workflow/checklist + conditional + feedback-loop patterns documented |
| Constraint envelope schema (Draft 2020-12) | HIGH | jsonschema 4.26 verified; existing repo precedent |
| YAML inheritance for envelope/relax | MEDIUM | Industry idiom (Helm/Ansible), not bound to one canonical doc |
| Constrained-generation prompt patterns | MEDIUM-HIGH | Anti-pattern is HIGH (negation degrades); positive technique MEDIUM (best-practice level, not benchmarked for design tasks specifically) |
| Skill auto-discovery | HIGH | Documented native behavior |
