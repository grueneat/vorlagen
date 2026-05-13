# CONTEXT — Design Decisions

Captured before research/planning. Research and planner MUST follow the locked decisions; the discretion section is open for the planner to refine; deferred items are explicitly out of scope.

## Decisions (locked — research/planner must follow)

### Constraint envelope: scope and default position

1. **All 16 `BRAND_CONSTRAINTS` are enforced as floor by default for every variant.** This is the simplest mental model and matches the issue's foundational principle: "the axis being tested is the only relaxation; everything else is constraint."

2. **Per-experiment `constraints.yml` declares the single tested axis and explicitly lists which floor rules (if any) are relaxed for THIS experiment.** Relaxations must be named (e.g., `relax: [brand:band_consistency]` with a one-line rationale). Implicit relaxations are forbidden.

3. **The envelope also incorporates `design-guide/README.md` Layer-1 deterministic rules** (the 21-row table) — minimum body size, line length, contrast, type families, alignment systems, etc. — same enforcement pattern.

4. **Reverses CONTEXT decision #4 from issue #29:** that decision said "don't run `BRAND_CONSTRAINTS` on variants — some hypotheses deliberately violate brand rules." That was wrong. The correction must be explicit in `design-guide/README.md` so the same mistake isn't reinvented.

### v2 experiment: declared variation axis

5. **v2's tested axis: Information density + form.** Hypotheses span the range of how much content fits on the P2 panel readably and in what form:
   - 1-item manifesto (single sentence, large)
   - 3-item list with short body per item
   - 5-item sparse Schlagwort list (with proper spacing this time)
   - Single quote / testimony format
   - Paragraph-form (no list)
   - Two-tier (one privileged item + supporting items)
   - Numbered priority list with body
   - etc.

6. **Everything except content density/form is constraint** — margins, spacing, body size, hierarchy execution quality, contrast, brand colors, photographic + typographic conventions. All variants render at the same overall quality bar; only the content density+form varies.

7. **Why this axis:** directly tests `design-guide/gruene-corpus.md` §2.2 ("Information density discipline") which is one of the corpus's documented gaps. v2's outcome — top-3 + bottom-3 + Spearman halo flag — is corpus content that closes a real §9 gap.

### v1 hypothesis reuse

8. **Three v1 concepts are explicitly retained for v2 as "concept retained, execution re-implemented within envelope":**
   - **Numbered 1–5 with weighted scale per rank** (descends from v1 `numbered-priority-list`) — numbered list 1–5 where typographic weight/size scales with rank position, so the eye lands on #1 first by design.
   - **Single editorial manifesto sentence** (descends from v1 `manifesto-single-statement`) — replace the list with one long-form editorial sentence that owns the panel.
   - **Left-aligned items separated by thin Dunkelgrün rules** (descends loosely from v1 `asymmetric-editorial-rules`) — items stack left-aligned with thin horizontal Dunkelgrün rules as separators, editorial-magazine register.
   
   These three are LOCKED retentions per user direction. The remaining ~9 hypotheses for v2 are fresh, generated for the density+form axis. Total target: ~12 variants.

9. **All 12 v1 variants are embedded in the v2 hypothesis-generation prompt as named "do-not-repeat these specific failure modes" anti-examples.** This closes the prompt-evolution loop CONTEXT #6 from issue #29 specified but never executed. Anti-example format per variant: slug + the specific envelope-violation that disqualifies it. **The three retained concepts also appear in the anti-example list** — explicitly tagged "concept retained as a separate retried-with-envelope variant; this anti-example is about the v1 broken IMPLEMENTATION specifically, not the idea." The prompt instructs the generator: "do not repeat the broken implementation; the retained variants will be re-implemented separately by the planner."

### Skill shape

10. **`.claude/skills/experiments/SKILL.md` ships with four subcommands** matching the experiment workflow:
    - `/experiments new <subject>` — scaffold experiment directory, generate `constraints.yml` from default + declare the tested axis
    - `/experiments generate <id>` — multi-LLM hypothesis generation with envelope threaded into prompt
    - `/experiments render <id>` — render all variants, gate against envelope, drop violations with log
    - `/experiments capture <id>` — aggregate results, write SUMMARY.md, prompt corpus update
    
11. **Each subcommand dispatches to the existing `bin/experiment-*` tools** (already shipped by issue #29). The skill is the process-doc + entry point + dispatch layer. Authoring uses the existing `generate-skill` skill.

12. **The skill documents v1's lessons explicitly:** mode collapse mitigations, halo effect handling, position bias randomization, why all 16 BRAND_CONSTRAINTS are floor by default, why v1 failed and v2's design corrects it. Future-Claude reads the skill, not memory, to follow the methodology.

### Variant validation gate

13. **`tools/experiment_render.py` is the gate location.** Mirrors the existing `inside_page` drop pattern. Each variant: build SLA → run envelope check (constraint engine evaluating all 16 BRAND_CONSTRAINTS + Layer-1 deterministic rules + the experiment's declared envelope) → if violations: drop variant, log clearly, EXCLUDE from voting bag. Variants that pass all checks proceed to rasterise.

14. **Drops are visible:** `manifest.json` includes a `_dropped` array (already established in issue #29) with `slug`, `violations: [...]`, `reason` per dropped variant. The voting page does NOT show dropped variants; the SUMMARY.md surfaces them in a separate section so the user can see what the LLMs proposed but the envelope rejected.

### v2 verification gate (mandatory deliverable)

15. **The v2 experiment must run end-to-end before issue #30 is mergeable:**
    - ≥10 rendered variants in `experiments/falzflyer-p2-mein-plan-v2/`, ALL respecting envelope (0 dropped, or all drops explicitly logged with reasons)
    - Flo votes a session, results JSON committed
    - `design-guide/gruene-corpus.md` amended with v2 top-3 + bottom-3 + provenance
    - This single deliverable closes BOTH issue #30's verification gate AND issue #29's deferred T15

## Claude's Discretion (research/planner explores)

- Exact constraint-engine integration point: extend existing `tools/sla_lib/builder/brand_constraints.py` / `structural_check.py` vs. new `tools/experiment_envelope.py` wrapper that composes the existing rules. Prefer the lightest wrapper.
- `constraints.yml` schema: hierarchical (separate sections for brand_rules / layer1_rules / experiment_specific) vs. flat. Mirror existing `meta.yml` style.
- How the skill subcommands handle missing arguments (interactive prompts vs. fail-fast usage message). Match `issue:*` skill conventions.
- Where v1 anti-examples live: inline in `prompt_template.md` or in a separate `tools/experiment_generate/v1_anti_examples.md` referenced by the prompt. Prefer separate file so the anti-example set grows over time without bloating the prompt template.
- Whether the envelope check needs `_verify_brand_fonts()` to pass first (probably yes — same reasoning as render pipeline) or can run pre-Scribus on the in-memory Document.
- Naming: `falzflyer-p2-mein-plan-v2` vs `falzflyer-p2-density-form` (the latter is more semantic; the v2 reference is implicit). Planner picks; defaults to `-v2` for continuity with issue #29 messaging.
- Whether to retain v1's `_llm-raw/` outputs by copying them as a "prior generation" reference next to v2's manifest.

## Deferred (out of scope for this issue — phase 2 / separate issue)

- Generalising the constraint envelope to non-falzflyer templates (zeitung, poster, postkarte). The falzflyer-default is the only envelope this issue ships; templates beyond falzflyer are follow-up issues.
- Hierarchy strategy as a separate v3 experiment, headline tone as a v4 (acknowledged in CONTEXT.md Q2 but out-of-scope for this PR).
- Multi-rater real-time merging.
- Auto-corpus-update from results (still manual; the skill captures the manual workflow).
- Hypothesis-prompt evolution beyond v1 anti-examples (full prompt evolution is a separate issue once we've run ≥2 experiments).
- Adaptive pair sampling (Glicko/Elo).
- Bradley-Terry / Elo ranking.
