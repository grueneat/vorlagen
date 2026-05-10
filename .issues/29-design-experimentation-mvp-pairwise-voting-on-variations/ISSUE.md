---
id: '29'
title: Design experimentation MVP — pairwise voting on variations to grow the design
  corpus
status: in_progress
priority: high
labels:
- enhancement
- templates
- visual-qa
source: github
source_id: 58
source_url: https://github.com/GrueneAT/vorlagen/issues/58
---

## Context

This workspace produces flyers, falzflyer, posters, and zeitungen for Bündnis 90/Die Grünen candidates. A core constraint surfaced in conversation: the LLM lacks reliable design taste, and the only way to fix this is to import taste from outside via a human-rated reference corpus (`design-guide/`, layered as deterministic rules + LLM-judgment rubric + corpus, with the corpus as ground truth).

The corpus is currently small and has named gaps (per-Land aesthetic, photography brief, density tolerance per format, tagline question — see `design-guide/gruene-corpus.md` §9). It also names recurring failure modes (`§8`) and gives a direct critique of the current `kandidat-falzflyer/page-01.png` (`§6`) — including the canonical "even-spaced peer list" failure on P2.

The proposed solution: a design experimentation system that industrialises taste import — generate structurally-different variations of a known weak region, render them in situ, and let humans rank them via pairwise voting. Results feed back as new corpus entries and new/strengthened rules in the design guide.

## Two non-negotiable nuances from Flo

1. **Variations must be LARGE/MEANINGFUL, not parameter tweaks.** 20 small variations of a taste-poor baseline produce a tournament that picks the least-bad of N mediocre options (local optimum). Every variation must map to a *named hypothesis* from the corpus or HCD principles, spanning a real design space (different commitments, structurally distinct alternatives).

2. **Experiments specifically target weak areas of the design guidelines.** The output of an experiment is new corpus entries + new/strengthened rules. The system is a tool for filling holes in the guide — choose experiment subjects where rules don't yet exist or are uncertain, not where rules are already strong.

## Solution sketch

1. Pick a weak-area subject (MVP: falzflyer P2 "Mein Plan" panel — already diagnosed in corpus §6, failure mode named in §2.1 / §8).
2. Generate 8–12 variations, each anchored to a named hypothesis (e.g., `privilege-one-item-via-yellow-accent`, `cut-to-three-with-body-text`, `sentence-form-not-bullets`, `size-jump-2.5x-on-one-item`, `asymmetric-balance-not-centered`, `vollkorn-italic-emphasis-on-priority-item`).
3. Render each variation as a full-page preview image (in situ — whole page with one region varying, not floating on white). Context changes the verdict.
4. Static HTML "experiments" page with two voting modes:
   - **Direct pick** — see all variations side-by-side, choose favorites
   - **Versus mode** — random pairs, pick winner per pair, Bradley-Terry / tournament produces a ranked output
5. Per pair, ask **both axes separately**: "which appeals more?" and "which transports the information better?" — answers can disagree and the disagreement itself is information.
6. Randomize left/right position per pair to neutralise position bias.
7. Results downloaded as a JSON file (vote pairs, timestamps, rater identity, computed ranking) — shareable so multiple humans can rate, results merged later.
8. Top 3 + bottom 3 captured into the corpus with provenance tags. Both wins and losses are useful — "what didn't work" is as informative as "what did."

## Cost-optimisation strategy

- **Opus** designs the experiment: which weak-area to target, what hypotheses span the design space, what each variation tests, what we expect to learn.
- **Sonnet** generates the variations: cheap to crank out renders once specs are precise enough not to require taste judgement.
- This keeps judgement spending where it pays off (experiment design) and execution cheap.

## Acceptance Criteria

- [ ] One experiment subject implemented end-to-end: the falzflyer P2 "Mein Plan" panel
- [ ] 8–12 variations, each anchored to a named hypothesis from corpus / HCD principles, with a one-line rationale per variation in a manifest
- [ ] Each variation rendered as a full-page preview image (in situ, not floating)
- [ ] Static HTML page with both direct-pick and versus modes
- [ ] Versus mode randomises left/right positions and asks both axes (appeal + transport) separately
- [ ] JSON results format with provenance tagging (rater identity, timestamps, vote pairs, computed ranking)
- [ ] Documented workflow: starting an experiment → voting → exporting results → feeding results back into corpus / design-guide
- [ ] Captured corpus updates from running this MVP experiment at least once with Flo as rater (the deliverable includes new corpus entries — proves the feedback loop)

## Out of scope (phase 2)

- Multi-rater real-time merging (MVP exports/imports JSON manually)
- Auto-corpus-update from results (manual for MVP)
- Generalised generator/manifest for any region (MVP can be hardcoded to one panel; generalisation is a follow-up issue)
- Hosted/shared deployment (MVP is local static page)

## Dependencies

None. `design-guide/` exists with `gruene-corpus.md`, `hcd-principles.md`, and `README.md` (three-layer framing). Falzflyer template exists at `templates/kandidat-falzflyer-din-lang/`.

## Rationale (why this is high priority)

This is the highest-leverage tool we could build for design quality across all templates. Every other improvement is either (a) one-off (specific template fix) or (b) capped by my taste, which is the named bottleneck. This system attacks the bottleneck directly and compounds with every experiment run. The design-guide/ artefacts are useful but static — the experiment system is what makes them grow.
