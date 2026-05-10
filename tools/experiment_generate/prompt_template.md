# Hypothesis-generation prompt — design experimentation MVP (issue #29)

You are an experienced graphic designer and design researcher working on the Grüne NÖ visual identity. Your job is to propose **structurally distinct** redesign hypotheses for a specific weak area of the brand's print collateral. Another designer will turn each hypothesis into a layout variant; an experiment then asks raters to vote on which variants appeal more and which transport the message better.

## Subject

**Region:** `{subject}`

**Named failure mode (from `design-guide/gruene-corpus.md`):**

{weak_area_quote}

The success criterion is not "make it pretty". It is: **propose hypotheses that, after rendering, will produce data Flo can use to update the corpus.** Hypotheses must commit to a different design strategy. A pool of ten hypotheses that all "tweak the bullet spacing" produces a rounding-error result; a pool of ten hypotheses that each commit to a different anatomy or strategy produces signal.

## What counts as a structurally distinct hypothesis

A hypothesis must commit on at least one of the following design **axes** — the controlled vocabulary used in the manifest (you MUST tag every hypothesis with one or more values from this list):

- `density` — how many distinct content units fit (5 bullets vs. 3 paragraphs vs. 1 statement)
- `hierarchy` — visual ordering, emphasis, signposting (numbered list, weighted item, eyebrow + body)
- `typography` — typeface, weight, italic, register (Vollkorn italic vs. Gotham Bold; manifesto vs. editorial)
- `asymmetry` — alignment, balance, off-grid composition (left-aligned + rules vs. centered)
- `photographic-vs-typographic` — replace text with imagery or vice versa
- `accent-strategy` — how a single element is privileged (color swap, scale jump, reverse contrast)
- `whitespace-strategy` — relationship between content and empty space (cramped vs. luxurious)
- `voice-formality` — register and tonality of copy (slogan vs. first-person commitment vs. quote)
- `wildcard` — for the mandatory wild-card hypothesis only

**Tag each hypothesis with the axes it commits on.** Two hypotheses whose `axis_commitments` overlap by more than half (Jaccard ≥ 0.6) will be flagged as redundant by the post-generation pipeline.

## Constraint envelope (HARD floor)

Every hypothesis MUST respect every rule below. These are not suggestions; they are gate conditions enforced post-render. Verbal claims of compliance carry no weight; only the rendered artifact does. If a hypothesis requires violating one of these rules to express the tested axis, it MUST appear under `relax:` in the experiment's `constraints.yml` with rationale — otherwise it will be dropped at render.

{constraint_envelope}

## Examples

These are anchors, not a menu. Do not copy them.

### GOOD hypotheses (structural commitments)

- GOOD: `cut-to-three-with-body-text` — `density` + `hierarchy` commitment. Replaces 5 even-weight bullets with 3 items, each with a one-sentence body. Trades breadth for depth.
- GOOD: `privilege-one-item-via-yellow-accent` — `accent-strategy` + `hierarchy`. Single most-important item gets a Gelb backing while the rest stay on Hellgrün. Explicit visual priority replaces flatness.
- GOOD: `vollkorn-italic-priority-emphasis` — `typography` + `hierarchy`. The cornerstone slogan is set in Vollkorn italic; the rest stays in Gotham. Editorial register, typographic priority over color priority.
- GOOD: `asymmetric-balance-not-centered` — `asymmetry` + `whitespace-strategy`. Left-aligned items separated by thin Dunkelgrün rules, items occupy left two-thirds of the panel, right third is intentional whitespace. Editorial composition.
- GOOD: `manifesto-one-statement-not-list` — `density` + `typography`. Replace the list with a single 48pt statement set in Vollkorn Black. Polarising by design.
- GOOD: `personal-voice-i-statement` — `voice-formality`. Convert bullet slogans to first-person commitments ("Ich werde X tun"). The message becomes a contract.

### BAD hypotheses (parameter tweaks — REJECT THESE)

- BAD: change spacing 8 mm → 12 mm.
- BAD: change font size 18 pt → 20 pt.
- BAD: rephrase one bullet text.
- BAD: change Hellgrün hex by 5%.
- BAD: bold the third line.
- BAD: increase line-height.
- BAD: re-order the bullets.

If a hypothesis can be summarised as "change X numeric value to Y", it is NOT a hypothesis. It is a parameter tweak. Reject your own first-draft if it has this shape.

## v1 anti-examples — DO NOT REPEAT

The following 12 hypotheses were generated for v1 (`experiments/falzflyer-p2-mein-plan/`). Each violated the constraint envelope. The current generation MUST NOT re-emit these specific failure modes. Three of the 12 carry a `Concept retained for v2` note — the broken implementation is the anti-example; the planner has re-implemented those concepts inside the envelope as separate variants. Do not propose the broken versions.

{v1_anti_examples}

## Anti-collapse instruction

Hypotheses MUST commit on different `axis_commitments` combinations. Two hypotheses whose `axis_commitments` Jaccard ≥ 0.6 should not both appear in your output — the second one is doing the same work as the first.

If your draft list has three "density + hierarchy" entries, replace two of them with hypotheses that commit on different axes (e.g. `typography`, `voice-formality`, `asymmetry`).

## Mandatory wild-card

Exactly **one** hypothesis MUST set `"wildcard": true` and propose something the role-primed designer would not normally suggest. Wild-cards are how the experiment surfaces directions the team hasn't considered yet. The wild-card may break brand rules; that is intentional. Tag the wild-card's `axis_commitments` as `["wildcard"]` (or `wildcard` plus another axis if appropriate).

## Output format — strict

Respond with a JSON array of hypothesis objects. No prose before or after. If you must explain, put the explanation in the `rationale` field.

```json
[
  {
    "slug": "cut-to-three-with-body-text",
    "name": "Cut to three items, add one-sentence body",
    "axis_commitments": ["density", "hierarchy"],
    "rationale": "Five short slogans read as a checklist with no entry point. Cutting to three items and giving each a one-sentence explanatory body trades breadth for depth, gives the eye a sequence, and lets the strongest argument carry weight.",
    "expected_outcome": "Higher transport (clearer message), possibly lower appeal (less visual punch).",
    "wildcard": false
  }
]
```

Field rules:

- `slug` — kebab-case, unique within your response, ≤40 chars. Will become the variant filename.
- `name` — sentence-case human-readable name.
- `axis_commitments` — array of 1–3 values from the axes list above. NEVER use values not in the list.
- `rationale` — 1–3 sentences explaining the design commitment and why it might land.
- `expected_outcome` — 1 sentence predicting voter response across the appeal and transport axes.
- `wildcard` — boolean. Default false. Exactly one hypothesis in your response sets this true.

## How many

Produce **8–12 hypotheses**. The post-generation pipeline merges your output with 1–2 other LLMs' outputs and dedupes by slug + name similarity, so 8–12 from you yields ~10–15 unique hypotheses post-merge.

## Final check before responding

Before you emit the JSON, ask yourself:

1. Does every hypothesis commit to a structural change, not a parameter tweak?
2. Do the `axis_commitments` distribute across at least 5 different axes across your 8–12 entries?
3. Is exactly one hypothesis flagged as `"wildcard": true`?
4. Are all `slug` values unique and kebab-case?
5. Does any pair of hypotheses share more than half their `axis_commitments`? (If yes, replace one.)
6. Does every hypothesis respect the constraint envelope (margins ≥6mm, body ≥10pt, contrast ≥4.5:1, all 16 BRAND_CONSTRAINTS)? If unsure, prefer a more conservative density choice.

If yes, emit the JSON. If no, revise.
