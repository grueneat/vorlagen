# Pitfalls Research — Issue #30 Constraint Envelope + Experiments Skill (v2 run)

**Researcher:** PITFALLS sub-agent
**Date:** 2026-05-10
**Scope:** Risks, edge cases, environment audit for v2 — encoding the constraint envelope into experiment tooling, authoring the experiments skill, running falzflyer-p2-mein-plan-v2 end-to-end on the density+form axis.

This pitfalls layer has unusual leverage: v1 already shipped, the failure mode is named (envelope vs. variation surface conflation), and v2's job is to not reinvent it. Where v1's pitfalls were predictive, v2's are post-mortem-informed.

---

## 1. v1 Pitfalls — what got flagged vs. what actually bit

**Risk:** Treating v1's pitfalls research as exhaustive when the actual v1 failure mode was UNFLAGGED in it.

**v1 pitfalls.md flagged extensively** — structural distinctness (mode collapse, §2.1–2.4), local optimum (§3), `inside_page` gate (§4.1), localStorage fragility (§5), two-axis disagreement (§6), multi-LLM coordination (§7). Mitigations were sound on these axes.

**v1 pitfalls.md UNFLAGGED — the actual bug:** Section 4.1 said "every variant must be `inside_page`-validated against panel bounds. Don't skip the existing structural-check gates." Correct, but **`inside_page` is one of 16 BRAND_CONSTRAINTS plus ~21 Layer-1 deterministic rules.** v1 pitfalls didn't generalise: it flagged the geometric overflow gate but didn't say "every brand+Layer-1 rule is a gate." The shipped `tools/experiment_render.py` (verified by inspection — only references `brand:inside_page`, line 10 + 130–140) gates on `inside_page` ALONE. The other 15 brand rules and all 21 Layer-1 rules were not gates — variants violated margins, type-on-green, body-size minimums, and went to vote anyway.

**Why v1 pitfalls missed it:** the framing in v1 CONTEXT.md decision #4 said "don't run BRAND_CONSTRAINTS on variants" and the pitfalls researcher accepted it as a locked decision rather than challenging it. **Generalised lesson: pitfalls research must challenge locked decisions when they encode an obvious category error**, not merely operate within them. CONTEXT.md decisions are inputs to be stress-tested, not floors.

**Failure mode:** v2 inherits the same "respect what's locked" stance and misses the next category error. Specific risk: CONTEXT.md decision #5 names "density+form" as a single axis, but density and form are two levers that may turn out to be entangled with hierarchy strategy — see §5 below.

**Mitigation:** treat every section of CONTEXT.md as a hypothesis the planner is allowed to surface as "Tier-1 question," not as immutable. Surface concerns; let the planner decide whether to honour or push back.

**Confidence:** HIGH on the diagnosis (v1 render code verified); MEDIUM on the generalised lesson (one data point so far).

---

## 2. Envelope bypass via clever variant code or LLM prompt-injection

**Risk:** A variant Python file, by accident or by design, could disable or circumvent the envelope check. Or the hypothesis-generation LLM could be prompted (by adversarial input or prompt drift) to emit a builder that suppresses the gate.

**Failure mode:** Variant claims "I respect the envelope" in its self-report or manifest entry, the gate trusts the self-report, the rendered output actually violates the envelope, voters see broken designs again.

**Mitigation — the gate must validate the RENDERED OUTPUT, not the variant module's self-report:**

- **Gate placement: post-render, pre-vote.** After the variant builder produces the SLA Document (or the rendered PDF/PNG), the gate inspects the *built artifact* and checks every envelope rule against it. The gate code lives in `tools/experiment_render.py` and consumes the envelope YAML as data, not the variant's claims.
- **Variant code never gets to set "envelope_passed: true".** The manifest entry for each variant includes a `_dropped` array (already established in v1 — verified in `experiment_render.py` lines 295–305) with the list of violations the GATE found. Variant builder can't write to this field.
- **No `# noqa` for envelope.** Variant builder code is not allowed to import from `experiment_render` or call any "skip_envelope" affordance. If such an affordance exists in the code, it's a bug to delete.
- **The render gate must run even when `--skip-envelope` is passed.** A debug flag for the rendering tool is acceptable for engineer-debugging only; the merge gate (Tier-1 deliverable AC: "0 dropped or all drops logged") forbids the flag from being used in the final v2 run. CI / the issue's done-checklist verifies the final run had no skip flag.

**Generalisation:** the "trust the artifact, not the producer" principle applies to LLM hypotheses too — see §3.

**Confidence:** HIGH.

---

## 3. LLM "respects" envelope verbally but Claude's variant code drifts outside it

**Risk:** The hypothesis-generation prompt threads the envelope into the LLM's context. The LLM emits a hypothesis that says "respects ≥6mm panel margin, body ≥10pt, type-on-green." Then the variant Python builder is written by a *different* invocation of Claude (the executor implementing the hypothesis), and that code drifts: a 4mm margin happens because the layout math was easier; body ends up at 9pt because of overflow handling; type lands on white because the builder forgot to add the green Farbfläche.

**This is the v1 failure mode in micro:** verbal compliance, code non-compliance.

**Failure mode:** The hypothesis text in the manifest looks compliant; the rendered artifact is not. Without post-render gating, the gap is invisible. With post-render gating, the variant is dropped — but if 4 of 12 variants fail this way, see §4.

**Mitigation (already specified in CONTEXT.md decision #13, but the planner must not weaken it):**

- **The render-time gate is the only gate that matters.** The hypothesis text being well-written is necessary but not sufficient. Verbal compliance buys nothing if the artifact violates.
- The hypothesis-generation prompt should set expectations: "the generated hypothesis WILL be code-checked at render. Verbal claims of compliance carry no weight; only the rendered artifact does."
- The skill SKILL.md should make this explicit so future executors don't try to argue with the gate ("but my hypothesis SAYS it respects margins"). The gate is the source of truth.

**Generalisation:** anywhere LLM text could be construed as compliance evidence, the system must convert "text says X" into "code/artifact actually does X" before trusting.

**Confidence:** HIGH.

---

## 4. Envelope is too restrictive — too many variants drop, ranking can't compute

**Risk:** Of 12 generated hypotheses, 8 drop on envelope violation. The remaining 4 cannot produce a meaningful pairwise tournament — too few variants, single-axis dominance, ranking is noise.

**Failure mode 1 (catastrophic):** v2 ships <6 variants past the gate. The acceptance criterion "≥10 variants, all respecting envelope" fails. Issue is not mergeable. Time spent regenerating eats the schedule.

**Failure mode 2 (subtle):** v2 ships exactly 10 variants because regeneration was forced until 10 passed, but the regeneration converged on safe choices that don't span the density+form axis — the ranking is technically valid but uninformative.

**Mitigation (planner must specify a regeneration policy):**

- **Auto-retry with feedback:** when a variant drops, the regeneration prompt receives the specific envelope violations the artifact had ("body text was 8pt, envelope requires ≥10pt; type sat on white at panel position X, envelope requires green Farbfläche") so the next round addresses them concretely. Don't regenerate blind.
- **Cap retries (e.g., max 2 regeneration rounds per variant).** After cap, the variant is permanently dropped and replaced from a fresh hypothesis. Not infinite retries — that risks Failure mode 2.
- **Drop budget threshold.** If >40% of initial variants drop, halt the run and surface to Flo: "envelope is too tight for the chosen axis, OR hypotheses are systematically violating one specific rule — review before continuing." This is the human-review gate.
- **Document the regeneration policy in the skill.** The skill's `/experiments render` step explains the auto-retry-with-feedback flow; the threshold; the human-review escalation. Future runs follow the same protocol.
- **Surface drops in SUMMARY.md.** Even successful runs surface what was dropped and why, so the user can read the envelope's behaviour as data ("envelope rejected 2 variants for type-on-white; this is the system working").

**Confidence:** HIGH on the risk; MEDIUM on the specific thresholds (40% / 2-retries) — these are conventions not measured.

---

## 5. v2 axis (density+form) overlaps v1's hidden axes — accidental hierarchy testing

**Risk:** Several v1 variants varied content (manifesto, quote, numbered, weighted) AND broke spacing simultaneously — they were mixing axes. v2's density+form axis reuses some content moves (1-item manifesto, 5-item Schlagwort, numbered priority list per CONTEXT.md decision #5) and risks the same conflation: a hypothesis that varies item count (density) ALSO varies hierarchy strategy (numbered scale, weighted size), and the ranking can't distinguish "ranking is about density" from "ranking is about hierarchy."

**Failure mode:** Top-3 turns out to share a hierarchy pattern (e.g., all use yellow-circle privileged-item) more than they share a density pattern. The corpus update would mis-attribute the win to density+form when hierarchy was the real driver.

**Mitigation:**

- **The hypothesis-generation prompt MUST require declared `axis_commitment`** for each hypothesis. The v1 manifest already has this field (verified — `axis_commitments: [density, hierarchy]` exists in current manifest.json). v2 must enforce: every hypothesis declares its primary commitment as `density+form`. Hypotheses whose primary commitment is `hierarchy` or `typography` are rejected at the hypothesis-validation step, not generated-and-dropped-later.
- **Reject mixed-primary hypotheses.** A hypothesis can have secondary axis commitments, but if its primary isn't density+form, it doesn't belong in this experiment. "Numbered with weighted scale per rank" must commit primarily to density (1–5 items) with hierarchy as a secondary expression of that density — not the other way around.
- **In SUMMARY.md, show per-variant axis-commitment list** so the user can verify the bag is density+form-balanced before voting.
- **Document the axis-policing principle in the skill:** future experiments must specify a single primary axis, and the hypothesis prompt enforces it. The lesson "v1 mixed axes invisibly" is captured.

**Confidence:** HIGH on the risk; HIGH on the axis-commitment-declaration mitigation (already structurally available in the manifest schema).

---

## 6. Three retained v1 concepts don't fit cleanly into density+form

**Risk:** Per CONTEXT.md decision #8, three v1 concepts are LOCKED retentions for v2:
1. **Numbered 1–5 with weighted scale per rank** — this is hierarchy strategy as much as density (5 items = density choice; weighted scale = hierarchy choice).
2. **Single editorial manifesto sentence** — density (1 item) AND form (sentence-form vs. list-form). Fits the axis cleanly.
3. **Left-aligned items separated by thin Dunkelgrün rules** — form (visual separator) but item count is also varied, so density too.

**Concept #1 is the cleanest mismatch:** "weighted scale per rank" is exactly the hierarchy lever, not a density lever.

**Failure mode:** Planner forces all three under "density+form" framing without acknowledging the strain. Either (a) the variants implement the concepts as if they were density+form variants, but the hierarchy lever dominates and pollutes the ranking (see §5), or (b) the planner relaxes the axis purity to accommodate, and v2 becomes a multi-axis experiment again.

**Mitigation — planner must reconcile this. Options to surface as a Tier-1 question:**

- **Option A: Reframe each retained concept's primary commitment as density+form.** Numbered 1–5 with weighted scale becomes "5 items, density-medium, form: list with size-graded items." Hierarchy is acknowledged as inherent-to-the-form, not as the primary axis. Hypothesis text must be edited to make this framing explicit so voters / the corpus-update reader don't misinterpret.
- **Option B: Accept that the three retained concepts are off-axis "user-pick" variants** and label them as such in the manifest (e.g., `axis_commitments: [hierarchy, density]` with primary=hierarchy for the numbered one). The voting bag includes them but the ranking analysis treats them separately — they don't compete on the density+form axis with the other 9. The corpus update notes "three variants were retained from v1 as concept-checks; they're ranked alongside but not commensurable with the density+form variants."
- **Option C: Drop one or two of the retained concepts** if they truly don't fit. CONTEXT.md decision #8 calls them "LOCKED retentions per user direction" — only Flo can authorise drop.

**Recommendation:** Surface as Tier-1 question. Default to Option A (reframe) because it preserves the user's lock while constraining axis purity. Option B is acceptable; Option C requires user re-authorisation.

**Confidence:** HIGH that this needs reconciliation; MEDIUM on which option is correct (depends on user intent).

---

## 7. Skill becomes documentation theater (written but never invoked)

**Risk:** A SKILL.md is authored. The pipeline ships. Subsequent experiments are run by invoking `bin/experiment-*` directly because that's faster, the skill never gets used, and the lessons in it decay out of memory.

**Failure mode:** v3 is run without the skill. The next person (including future-Flo) reinvents v1's mistakes because the skill captured the lessons but the skill wasn't the entry point.

**Mitigation:**

- **The skill MUST be the canonical entry point.** `bin/experiment-*` are invoked BY the skill, not by humans directly. Document this norm in SKILL.md: "do not invoke `bin/experiment-*` directly except for engineer-debugging; for any real experiment run, start from `/experiments new`."
- **The skill's commands must do MORE than dispatch.** Each `/experiments <verb>` step should add value the bin tool doesn't: pre-flight checks (verify envelope file exists; warn if axis_commitment looks off-axis; surface drop budget), post-step assertions (after `render`, confirm ≥10 variants passed; after `capture`, confirm SUMMARY.md mentions axis purity). If the skill is just a thin wrapper, it'll get bypassed.
- **README and corpus reference the skill as the entry point.** `design-guide/README.md` and `design-guide/gruene-corpus.md §6` (per AC) point readers at `.claude/skills/experiments/SKILL.md` for the methodology, not at the bin scripts.
- **The done-checklist in PRs that touch experiments asks: "did you start from `/experiments new`?"** Cultural enforcement.

**Confidence:** HIGH.

---

## 8. Invariant drift between render-gate code and envelope spec

**Risk:** The envelope is specified in `experiments/_constraints/falzflyer-default.yml` as data ("min body 10pt, panel margin ≥6mm, type-on-green required"). The render gate code in `tools/experiment_render.py` checks compliance. If the YAML envelope is updated (e.g., min body raised to 11pt) but the gate's hardcoded threshold isn't (still 10pt), variants pass that should drop. Worse: thresholds drift in opposite directions and no one notices.

**Failure mode:** v3 raises an envelope rule, gate doesn't enforce it, broken variants ship to vote, the v1 failure repeats with new symptoms.

**Mitigation:**

- **Render gate must LOAD the envelope YAML and execute checks dynamically** — no hardcoded thresholds in the gate code. The gate is a generic engine that reads rules from the envelope file and applies them to the rendered Document.
- **The constraint engine reuses existing `tools/sla_lib/builder/brand_constraints.py` rule definitions** (already exists — verified by inspection). The envelope YAML lists rule IDs (`brand:inside_page`, `brand:logo_size_3M`, `brand:bleed_3mm`, etc.) and any per-experiment relaxations; the engine looks up rule definitions by ID and applies them. This means: no rule logic is duplicated between envelope-engine and brand-constraints; if a brand-constraint rule changes, the envelope follows automatically.
- **Layer-1 deterministic rules from `design-guide/README.md` (the 21-row table) need to be lifted into machine-checkable form.** Currently they're documentation, not enforced code. Either (a) the planner adds Layer-1 rule implementations to `brand_constraints.py` (preferred — keeps everything in one rule registry), or (b) a separate `layer1_rules.py` registry is added with the same shape. Either way, the envelope YAML references these rules by ID, never by reproducing thresholds.
- **Tests verify the engine round-trips:** unit test loads a known-valid envelope YAML, builds a known-violating Document, runs the gate, asserts the violation is reported with the right rule ID. Test suite must cover: (a) all 16 BRAND_CONSTRAINTS rule IDs resolve, (b) Layer-1 rule IDs resolve, (c) per-experiment relaxation list correctly disables only the named rules, (d) malformed envelope YAML fails fast with clear error.

**Confidence:** HIGH on the risk; HIGH on the dynamic-loading mitigation.

---

## 9. v2 still produces bad variants because it's the same LLMs as v1

**Risk:** v2's hypothesis generation calls the same Claude (Opus) and same Codex models that produced v1's variants. Same training data, same priors, same blind spots. Anti-examples and envelope threading help but don't change the underlying generator distribution.

**Failure mode:** Despite the envelope and the anti-examples, v2 hypotheses cluster around the same regions of design space as v1 — same density tendencies, same form tendencies, same "safe middle." The ranking is technically valid but the corpus update is repeating insights v1 already surfaced.

**Mitigation:**

- **Role priming differently for v2.** v1 (per its prompt template) used "as a typography-first designer" and "as a hierarchy-first designer." v2 should explicitly use density+form-anchored priming: "as an editor optimising for one-thing-per-panel transport," "as a magazine art-director optimising for whitespace+density," "as a Grüne flyer designer who has read `design-guide/gruene-corpus.md §2.1–2.2` and is responding directly to its lessons." Different framings push different modes.
- **Anchor explicitly in the corpus.** v2's hypothesis prompt should require each hypothesis to cite the corpus section it's responding to (e.g., "this hypothesis tests §2.2 information density discipline by going below the recommended 30–60 word range" or "this responds to §8 weakness #3 even-spaced peer lists by privileging one item visually"). Forces hypotheses to be argumentative against the corpus, not generic.
- **Use the envelope as a leverage point.** Because every hypothesis must respect the envelope (16 brand rules + Layer-1), the hypothesis space is *constrained* in a way v1's wasn't. This compresses LLM divergence and forces the variation onto the declared axis. Counter-intuitively, the envelope is what makes the LLMs stop being mediocre on the wrong axis — it fences off the easy-wrong moves.
- **Lean on multi-LLM diversity.** v1's `_llm-raw/` directory is preserved (per CONTEXT.md discretion item) and used as v2's anti-example set. The v2 prompt explicitly says "do not repeat any of these specific implementations." If two of three LLMs converge on a region of v1, that region is anti-example-marked.

**Confidence:** MEDIUM-HIGH. Mitigations are well-grounded but the underlying problem (same priors) is fundamental — v2 is necessarily a perturbation of v1's generator distribution, not a fresh draw.

---

## 10. Skill slash-command dispatch — multi-verb shape verification

**Risk:** CONTEXT.md decision #10 specifies four subcommands: `/experiments new`, `/experiments generate`, `/experiments render`, `/experiments capture`. If Claude Code's skill system doesn't natively support multi-verb dispatch (i.e., a skill named `experiments` with sub-verbs parsed from the slash command), the entire skill shape is wrong and the planner must reshape.

**Findings (verified via Anthropic Claude Code skills docs + community references):**

- A skill at `.claude/skills/<name>/SKILL.md` creates `/<name>` as the slash command. Verified per [Claude Code Docs — Extend Claude with skills](https://code.claude.com/docs/en/skills) and [Claude Code Skills: Complete Guide](https://claude-world.com/articles/skills-guide/).
- **There is no native "subcommand syntax" in slash-command invocation.** Multi-verb behaviour is handled inside the SKILL.md content — Claude reads the user's argument string after `/<name>` and interprets it. So `/experiments new falzflyer-p2-density-form` works because the skill parses "new <subject>" from its arguments and dispatches accordingly within SKILL.md instructions.
- This means CONTEXT.md decision #10's four-subcommand shape IS supported, but as a **documented convention inside SKILL.md**, not as a Claude Code primitive. The skill must include verb-parsing logic in its instructions: "if the first argument is `new`, do X; `generate`, do Y; `render`, do Z; `capture`, do W."

**Failure mode 1:** Planner assumes native subcommand routing exists, designs SKILL.md without explicit verb-parsing instructions, the skill fails to dispatch correctly when invoked.

**Failure mode 2:** Planner over-engineers — splits into four separate skills (`/experiments-new`, `/experiments-generate`, etc.) when a single skill with verb-dispatch is the cleaner shape.

**Mitigation:**

- **Single skill `experiments` with explicit verb-parsing in SKILL.md.** Match the shape of existing repo skills (e.g., `issue:*` referenced in CONTEXT.md) — verify the planner's reading of how those skills handle multi-verb. The codebase researcher should pull the pattern.
- **Document the verb-dispatch contract in SKILL.md** so it's discoverable: "this skill responds to four verbs: new, generate, render, capture. Pass the verb as the first argument." Include a usage examples block in the YAML frontmatter description so autonomous invocation also works.
- **Fail-fast on unknown verb.** If `/experiments foo` is called, SKILL.md instructs Claude to print "unknown verb 'foo'; expected one of: new, generate, render, capture" — don't silently fall through.
- **`generate-skill` skill is the right authoring tool** (per CONTEXT.md decision #11). It will handle the YAML+content shape correctly; planner shouldn't hand-author SKILL.md.

**Confidence:** HIGH on the dispatch shape being supported; MEDIUM on the exact convention (verify against existing repo skills before authoring).

---

## 11. Test/verification gaps unique to this issue

**Risk:** v1's test gap was "no end-to-end run," fixed by AC #11 (corpus update). v2 has additional test gaps unique to the envelope+skill scope that the planner must explicitly cover.

**Required test layers (planner spec):**

| Layer | Test | Why |
|---|---|---|
| Unit | Constraint loader: parse a known-valid `falzflyer-default.yml`, return list of rule references | Schema regressions caught at unit level |
| Unit | Schema validator: reject malformed envelope YAML (missing axis declaration, unknown rule ID, malformed relaxation) with clear error | Forms the gate's first defense |
| Unit | Envelope-check function: synthetic Document with known violations → gate reports correct rule IDs and messages | Core gate logic correctness |
| Unit | Per-experiment relaxation: envelope with `relax: [brand:band_consistency]` correctly disables that rule and only that rule | Prevents over-relaxation |
| Integration | Render a deliberately-violating variant (body 8pt, type on white) → gate drops it, manifest `_dropped` array contains the violations | End-to-end of the gate |
| Integration | Render a known-good variant → gate passes, manifest entry includes `envelope_passed: true` (or equivalent) | Negative control |
| Integration | Skill dispatch: invoke `/experiments new test-subject` in a dry-run mode, assert directory scaffolded, `constraints.yml` created with default envelope | Skill correctness |
| End-to-end | Full v2 run: hypothesis-gen → render → vote → capture → corpus update. This IS the AC #11 deliverable. | The merge gate. |

**Inherently manual:**

- Flo's voting (cannot be automated)
- Flo's review of axis purity in the manifest before voting (eyeballing required)
- Corpus update interpretation (judgment call)

**Confidence:** HIGH.

---

## 12. Corpus update language conflates v1+v2 lessons

**Risk:** Per AC #10, the corpus update must close BOTH issue #29's deferred T15 (v1 results) AND issue #30's verification gate (v2 results). Logistically this is a single corpus amendment. Rhetorically, it's easy to blur "v1 lesson" with "v2 lesson" and write something muddled.

**Failure mode:** The corpus reader (future-Flo, future-Claude) cannot tell which insight came from which experiment. The provenance is lost. Future experiments anchor on a blurred lesson.

**Mitigation:**

- **The corpus update is structured as two clearly-labelled parts:**
  - **Part A — from v1: what we learned about envelope necessity.** This is the meta-lesson: "first experiment violated basic design rules because the envelope wasn't enforced; the fix was to make brand+Layer-1 rules a floor for all variants." This belongs as a §6/§9 entry naming `experiments/falzflyer-p2-mein-plan` (v1) as the source.
  - **Part B — from v2: which density+form approach wins/loses on appeal+transport.** This is the substantive lesson: top-3 + bottom-3 with their density+form characterisations. This belongs as a §2.1 / §2.2 entry naming `experiments/falzflyer-p2-mein-plan-v2` as the source, with results JSON path cited.
- **Each entry includes provenance:** experiment ID, run date, voter (Flo), variant count post-envelope, drop count, results JSON path. Standard pattern from CONTEXT.md decision #11 of issue #29.
- **The skill's `/experiments capture` step should template this two-part corpus update** so future runs follow the same structure. Don't leave it to ad-hoc writing each time.
- **Reference each part from the other.** Part A says "v1's failure is what motivated v2's envelope; see §2.1 for v2's results." Part B says "v2 was run after v1 because v1 violated envelope; see §6 for the meta-lesson." Cross-references prevent the blur.

**Confidence:** HIGH.

---

## 13. Environment audit re-check (deltas since #29's research)

All commands run on 2026-05-10 from `/root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run`.

### 13.1 Confirmed unchanged from #29

| Tool | Version | Status |
|---|---|---|
| `python3` | 3.13.5 | unchanged from #29 |
| `pyyaml` | 6.0.3 | unchanged |
| `Pillow` | 12.2.0 | unchanged |
| `claude` (Claude Code CLI) | 2.1.132 | unchanged |
| `codex` | present at `/root/.npm-global/bin/codex` | present (was present in #29) |
| Brand fonts | 42 face entries (Gotham Narrow + Vollkorn variants) | unchanged |
| `xvfb-run` + Scribus headless pipeline | functional | unchanged |
| LLM API keys (`ANTHROPIC_API_KEY`, etc.) | UNSET | unchanged — same `claude` CLI subprocess pattern applies |

### 13.2 New / verified for #30

| Item | State | Notes |
|---|---|---|
| `jsonschema` (Python module + CLI) | **4.26.0 / `/usr/local/bin/jsonschema`** | Required for AC #2 ("schema validates with jsonschema"). Available. No install needed. |
| `.claude/skills/` directory | **DOES NOT EXIST** in worktree or main `.claude/` | Confirmed (verified by `ls`). The `experiments` skill will be the first skill in this repo. No prior pattern to copy from this repo. |
| `experiments/_constraints/` | **DOES NOT EXIST** | New directory required by AC #2/#3. Greenfield. |
| `experiments/_schema/manifest.schema.yaml` | EXISTS (from #29) | Pattern to mirror for `constraints.schema.yaml`. |
| `tools/experiment_render.py` | EXISTS — only enforces `brand:inside_page` | Verified by direct grep. v2 must extend this gate to all envelope rules. |
| `tools/sla_lib/builder/brand_constraints.py` | EXISTS — defines `BRAND_CONSTRAINTS` registry | Confirmed entry point for envelope rule definitions. Layer-1 rules likely need to be added here. |
| `tools/experiment_generate/prompt_template.md` | EXISTS | Must be extended with envelope + v1 anti-examples per AC #5. |
| `experiments/falzflyer-p2-mein-plan/` (v1 dir) | EXISTS — has `manifest.json`, `_llm-raw/`, `variants/` | Available for v2 to reference as anti-example source. |
| `bin/experiment-*` (generate/render/results) | All three exist | The skill dispatches to these. |

### 13.3 No regressions detected

Nothing has degraded since #29's environment audit. All tooling required for v2 is present. No new installs needed beyond what the planner chooses for envelope-engine code.

**Confidence:** HIGH.

---

## Top 5 Pitfalls to Address (Prioritised)

1. **Envelope gate must validate the rendered artifact, not the variant's self-report, AND must load rules dynamically from the envelope YAML — no hardcoded thresholds.** This is the single fix that prevents v1's failure mode from recurring. Combines pitfalls §2 + §8. The render gate reads the envelope YAML, looks up rule definitions in `BRAND_CONSTRAINTS` + Layer-1 registry, applies them to the built Document, and drops violators with rule-IDed violations. Variant code never gets to claim compliance.

2. **The hypothesis prompt must enforce primary axis = density+form, and the planner must reconcile the three retained v1 concepts against this axis.** Combines pitfalls §5 + §6. Without axis policing, v2 reproduces v1's invisible mixing — a "density" experiment that's actually about hierarchy. The numbered-with-weighted-scale retention is the cleanest test case: surface as a Tier-1 question and require explicit reframing or off-axis labelling before generation.

3. **Drop policy and regeneration policy must be specified, not improvised.** Pitfalls §4. Auto-retry-with-feedback (max 2 rounds, with specific violations fed to the LLM); halt at >40% drop with human review; SUMMARY.md surfaces drops as data. Without this, the AC "≥10 variants, 0 dropped" becomes a permathreshold that's gamed by regenerating until safe — destroying the experiment's signal.

4. **The skill must be the canonical entry point, not a wrapper around bin tools.** Pitfalls §7 + §10. SKILL.md uses verb-dispatch convention (verified shape per Claude Code docs); README and corpus point at the skill; PR done-checklists ask "did you start from `/experiments new`?"; each skill verb adds value (pre-flight checks, post-step assertions) the bin tool doesn't. Otherwise the lesson decays and v3 reinvents v1's mistake.

5. **The corpus update is structured as two clearly-labelled parts (v1 meta-lesson + v2 substantive results), with cross-references and per-experiment provenance.** Pitfalls §12. Without this discipline, future readers can't separate "envelope necessity" from "density+form findings" — the blur destroys the corpus's utility.

---

## Sources

### HIGH confidence (verified by direct inspection or first-party docs)

- v1 pitfalls research: `/root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run/.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/research/pitfalls.md` (read in full)
- v1 render gate code: `tools/experiment_render.py` (verified — gates only on `brand:inside_page`, lines 10, 127–142, 295–305)
- v1 manifest format: `experiments/falzflyer-p2-mein-plan/manifest.json` (verified — `axis_commitments` field exists)
- Brand constraints registry: `tools/sla_lib/builder/brand_constraints.py` (verified by directory listing)
- Schema patterns: `experiments/_schema/manifest.schema.yaml` and `manifest.example.yml` (existing patterns to mirror)
- `design-guide/gruene-corpus.md` §0, §2.1, §2.2, §6, §8, §9 (read in full)
- ISSUE.md and CONTEXT.md for issue #30 (read in full)
- Environment audit commands run 2026-05-10 (see §13)
- [Claude Code Docs — Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Claude Code Skills: Complete Guide to Slash Commands (claude-world.com)](https://claude-world.com/articles/skills-guide/)
- [Claude Code Customization (alexop.dev)](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)

### MEDIUM confidence

- The "40% drop budget" threshold and "max 2 regeneration retries" are conventions, not measured. Planner may calibrate.
- The verb-dispatch convention for multi-verb skills is documented but the exact contract (whether autonomous invocation works the same as explicit `/experiments new ...`) has minor variance across community write-ups.
- The recommendation to add Layer-1 rules to `brand_constraints.py` (vs. a separate registry) is a code-shape preference; both work.

### LOW confidence (needs validation)

- That role-priming differently in v2 will materially change LLM output distribution from v1 — plausible from prior diversity-collapse research but unverified for this specific generator pair on this specific axis.
- That the envelope's compression of hypothesis space will reduce mode collapse rather than amplify it — argued in §9 but not measured.

---

## Metadata

**Research date:** 2026-05-10
**Issue:** 30 — Encode constraint envelope in experiment tooling + author experiments skill (v2 run)
**Slug:** `30-constraint-envelope-tooling-experiments-skill-v2-run`
**Sub-agent:** PITFALLS
**Output file:** `.issues/30-constraint-envelope-tooling-experiments-skill-v2-run/research/pitfalls.md`
**Predecessor pitfalls research:** `.issues/29-…/research/pitfalls.md` (read and cross-referenced)
