# Design Guide

A working reference for design decisions in this workspace (flyers, falzflyer, posters, zeitungen for Bündnis 90/Die Grünen candidates).

## The two axes

Every design here is judged on exactly two outcomes:

1. **Human appeal (A)** — does it feel good to look at and want to engage with
2. **Information transport (T)** — does the message land cleanly in the time a real reader gives it

Process metrics (grid followed, brand rules met, intent articulated) are *instrumentation*. They do not substitute for a verdict on those two outcomes. A draft can pass every internal check and still fail both axes — only a human verdict closes the loop.

## The three layers

The guide is structured as three layers of decreasing reliability. Trust the earlier layers more than the later ones.

### Layer 1 — Deterministic rules (highest trust)

Numeric thresholds and brand constraints that can be checked mechanically. A draft that violates one of these is wrong; the rule is not the question. Extract below; full reasoning in [`hcd-principles.md`](hcd-principles.md) and [`gruene-corpus.md`](gruene-corpus.md) §0.

These are the candidates for encoding into linting/CI tooling.

| Rule | Threshold | Source |
|---|---|---|
| Body text minimum size | ≥ 10pt, prefer 11pt | hcd #12 |
| Captions / Impressum minimum | ≥ 8pt | hcd #12 |
| Body line length | 45–75 chars (66 ideal) | hcd #11 |
| Headline size jump over body | ≥ 2.5× | hcd #10 |
| Headline length | ≤ 7 words / ~35 chars | hcd #9 |
| Body contrast (WCAG AA) | ≥ 4.5:1 | hcd #13 |
| Display contrast ≥ 18pt | ≥ 3:1 | hcd #13 |
| Type families per panel | ≤ 2 | hcd #5 |
| Type sizes per panel | ≤ 3 | hcd #5 |
| Alignment systems per panel | ≤ 2 | hcd #22 |
| Negative space per panel | ≥ 30% | hcd #3 |
| Dominant element optical weight | ≥ 40% | hcd #1 |
| Face crop fill (when face is primary) | ≥ 60% of frame | hcd #8 |
| CTAs per panel | exactly 1 (if any) | hcd #14 |
| Non-green accent colors per piece | ≤ 2 | hcd #6 |
| Forbidden primary colors | SPD-red, AfD/CDU-blue, FDP-yellow-saturated, Linke-magenta | hcd #6 |
| Margin (M) | `0.06 × short edge of trim` | CD-Quickguide |
| Logo size | `3 × M` print / `2.5 × M` digital | CD-Quickguide |
| Logo clear-space | `1 × M` on every side | CD-Quickguide |
| Type on white plate | forbidden — type lives on green | CD-Quickguide §7 |
| Brand colors | only Dunkelgrün, Hellgrün, Gelb, Magenta | CD-Quickguide |

**The Layer-1 deterministic rules ARE the constraint envelope for design experiments.** A hypothesis testing one design axis (e.g. information density, hierarchy strategy, typographic voice) MUST respect every other Layer-1 rule. Variants violating the envelope are dropped, not voted on. The 16 `BRAND_CONSTRAINTS` (defined in `tools/sla_lib/builder/brand_constraints.py`) are part of this envelope. The earlier framing — that experiment variants are "research artifacts" exempt from brand rules — was wrong; it conflated "a hypothesis tests one axis" with "a hypothesis ignores all axes". See `.claude/skills/experiments/SKILL.md` for the full methodology and the `/experiments` workflow.

### Layer 2 — LLM-judgment rubric (medium trust)

Soft principles that need pattern matching against the corpus. I can apply these but my judgment on each is *less* reliable than the deterministic rules above. The Quick Decision Checklist at the end of [`hcd-principles.md`](hcd-principles.md) is the working version of this layer.

Key calls in this layer:

- **Asymmetric balance over centered symmetry** (hcd #2)
- **Environmental candid portraits over studio crops** (corpus §5, hcd #7)
- **Gaze direction into the layout, never off the page** (hcd #4)
- **Hierarchy via contrast, not variety** (hcd #10)
- **Proximity grouping, not drawn boxes** (hcd #20)
- **Figure-ground clarity at every point** (hcd #21)
- **Repetition across multi-panel pieces** (hcd #24)
- **Tone-match between headline format and body format** (corpus §2.3)
- **One-thing-per-surface commitment** (corpus §2.1, §6)
- **Anti-chartjunk: every graphic carries information** (hcd #15)

If I cannot point to a corpus example or a numeric rule supporting a placement decision, the placement is a guess — flag it rather than ship it.

### Layer 3 — The corpus (ground truth)

[`gruene-corpus.md`](gruene-corpus.md) is the human-validated reference set. It documents what the party's design language *actually does* in real campaigns (2021 + 2025 federal, regional posters, flyers, social, Böll-Stiftung publications) and judges each pattern on the two axes. It also contains a direct critique of the current `kandidat-falzflyer/page-01.png` against the corpus (§6) and a list of recurring strengths (§7) and failure modes (§8).

This is the layer the other two derive from. When the rules and the corpus disagree, **the corpus wins** — rules are a compression of what the corpus shows works, and compressions lose information.

## Workflow

**When designing a new piece:**
1. Pick the closest reference in the corpus (§1–§5). Adapt, do not compose from scratch.
2. Apply Layer 1 rules as a non-negotiable floor.
3. Apply Layer 2 rubric as guidance — note any decision I cannot ground in corpus or rule.
4. Ship a draft to Flo with a short "what I attempted" note on each axis. Frame attempts as hypotheses, not success claims.
5. Flo's verdict is the source of truth. Capture every verdict (positive or negative) into the corpus as a new rated entry — that is how the corpus grows.

**When reviewing an existing piece:**
1. Run the deterministic checks first. Stop and fix any failure before continuing.
2. Walk the Quick Decision Checklist in `hcd-principles.md`.
3. Compare to the closest corpus reference. Where does the draft over- or under-commit relative to that reference?
4. Surface findings to Flo with corpus citations.

## Open gaps that need user-rated examples

These are calls the corpus cannot yet answer; they need 5–10 user-rated examples each to close. From `gruene-corpus.md` §9:

- **Per-Land aesthetic differences** — Bavaria vs. NRW vs. Berlin Grüne posters look subtly different. Which posture do we adopt for Mödling-style local materials?
- **Photography commissioning brief** — environmental candid is observed but not specified. Lens, light, gaze direction need user-rated portrait examples.
- **Information density tolerance per format** — DIN-lang panel vs. A4 zeitung. User-rated existing pages would calibrate this.
- **Tagline question** — does this workspace need a unifying tagline (the role "Ein Mensch. Ein Wort." plays at federal scale) across all candidate templates, or is each piece ungrouped?

## What is NOT in this guide

- Per-piece sign-off authority — that is Flo's verdict, full stop.
- A canonical layout for any specific template — the corpus shows directions, not destinations.
- Anything not anchored in the two axes. Aesthetic preferences without an appeal-or-transport justification are out of scope.
