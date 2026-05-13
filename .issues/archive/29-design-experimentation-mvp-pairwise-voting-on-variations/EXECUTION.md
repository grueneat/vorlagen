# Execution Log — Design Experimentation MVP

**Status:** complete
**Branch:** issue/29-design-experimentation-mvp-pairwise-voting-on-variations
**Worktree:** .worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/
**Started:** 2026-05-10T16:19:11Z
**Completed (T01–T14):** 2026-05-10T16:56:00Z
**Scope this run:** T01–T14 (T15 = human voting session, deferred to Flo)

## Tasks

- [x] T01 — Scaffold directories, bin shims, route placeholders — `2112f2b`
- [x] T02 — Hoist `_add_front` into `variant_scaffold.py` — `4eace8d`
- [x] T03 — Manifest schema (jsonschema Draft 2020-12) — `5b4e223`
- [x] T04 — Results JSON schema — `10120b0`
- [x] T05 — Implement `tools/experiment_hypothesis_gen.py` (multi-LLM) — `7d8045a`
- [x] T06 — Author the hypothesis-generation prompt — `c701569`
- [x] T07 — Implement `tools/experiment_render.py` (variant orchestrator) — `8cf49f1`
- [x] T08 — Implement `tools/experiment_results.py` (aggregation + ranking) — `f79649f`
- [x] T09 — Wire bin shims to real implementations — verified after T05/T07/T08; no separate commit needed (bin shims unchanged from T01)
- [x] T10 — Add `experiments` content collection — `99ef73f`
- [x] T11 — Implement `experiments/index.astro` (list page) — `4bf741b`
- [x] T12 — Implement `experiments/[id].astro` (voting page) — `653f5f0`
- [x] T13 — Generate the MVP hypothesis manifest + variant builders — `d038852`
- [x] T14 — Render variants and run end-to-end build — `0793cb7`
- [ ] T15 — handed off to user for voting session (corpus update is the merge gate)

## Verification status

- All Python unit/integration tests: **PASS** (835 tests, 11 skipped, 0 failed)
- `npm --prefix site run build`: **PASS** (12 pages built, includes the falzflyer voting page)
- One full hypothesis-gen + render run: **PASS** (claude + codex + gemini all responded; 12/12 variants rendered, 0 dropped on inside_page)
- Smoke vote round-trip: **PASS** (synthesised a results JSON via the same algorithms used by the export button; validated against `experiments/_schema/results.schema.yaml`)
- Production falzflyer rendering byte-stable: **PASS** (`af443213…` template.sla SHA256 unchanged before/after T02 + after T14; `34730f1e…` page-01.png unchanged; `ae5af4c6…` page-02.png unchanged — verified via `bin/render-gallery kandidat-falzflyer-din-lang`)

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 1 — Bug fix in tools/experiment_render.py]** Stale `page-*.png` from a previous render were silently kept by `_zero_pad_pngs` because the rename is a one-way no-op when the zero-padded target already exists. This left re-renders pointing at stale `page-1.png` while pdftoppm wrote a fresh `page-01.png` that was never picked up. `_render_variant_pngs` now deletes stale `page-*.png` before re-running pdftoppm. Discovered when iterating on `manifesto-single-statement` font-size; a re-render of the variant produced a new SLA but left the old PNG in place. (Commit `0793cb7`)

2. **[Rule 1 — Bug fix in templates/kandidat-falzflyer-din-lang/variant_scaffold.py]** Original implementation called `build_template()` which does NOT inject library images. Result: variants rendered with empty P1 Kandidat-Portrait, P4 Klima-Photo, P5 Bildung-Photo frames. Switched to `build_preview()` so INJECT_MAP runs as in production. The variant's P2 strip-and-replace happens AFTER injection, so P2 image frames (none in production) wouldn't be affected. (Commit `d038852`)

3. **[Rule 2 — Trim manifest after generation]** `bin/experiment-generate` produced 29 deduped hypotheses, more than the plan's 8-12 target. Trimmed manifest down to 12 hypotheses (one per major axis combination, all 3 LLMs represented, 1 wildcard) so the executor could implement detailed variant builders for all of them without exceeding the "≤80 lines per variant" budget. The 17 dropped hypotheses are preserved verbatim in `experiments/falzflyer-p2-mein-plan/_llm-raw/` for future runs. (Commit `d038852`)

### Blocked (Rule 4)

None.

## Discovered Issues

- The hypothesis-generation prompt's anti-collapse instruction landed 20 axis-overlap warnings (Jaccard ≥ 0.6) across the 29 raw hypotheses. The dedup grouped on slug + name similarity but not on `axis_commitments` overlap, so semantically-overlapping pairs (e.g., `manifesto-single-statement` ↔ `manifesto-one-statement`) survived dedup. After trimming to 12 the warnings drop to 4, all between hypotheses that ARE genuinely different despite axis overlap (e.g., a typography-+-hierarchy `numbered-priority-list` vs a typography-+-hierarchy `vollkorn-italic-cornerstone` — both axes match, but the design commitment is different). Logged for future post-experiment prompt evolution.
- `manifesto-single-statement` initial 44pt font-size overflowed the 87mm-wide P2 panel; tightened to 30pt. Smaller-than-expected font for a "manifesto" hypothesis is itself signal — the panel doesn't have room for genuine 48pt manifesto type.

## Handoff to user (T15)

Flo, here's what's ready and what you need to do:

**What's ready (you can vote):**
- Open the site locally: `npm --prefix site run dev` (or `npm --prefix site run preview` after `build`).
- Navigate to `/experiments/falzflyer-p2-mein-plan/`. You'll see 12 hypothesis variants rendered as full-page previews with P1 Cover, P2 (varied per hypothesis), and P3 Wahltag in situ.
- Two voting modes: **Direct-Pick** (star your favorites) and **Versus** (66 randomised pairs, two-axis voting per pair). Keyboard shortcuts: `Q`/`W` for Appeal left/right, `O`/`P` for Transport left/right, `Space` to skip a pair, `E` to export.
- Set the **Rater** field at the top to `flo` so the export filename + provenance tags are tagged correctly.
- localStorage persists votes across reloads. If you see a red banner about non-persistent storage, hit Export often — the JSON file is the durable record.

**What you need to do (T15 — the merge gate):**

1. **Vote.** As many pairs as you have patience for. The aggregator computes wins-ratio over completed pairs; you do NOT need to finish all 66 pairs. (45 pairs = ~6 per variant per axis is plenty.)

2. **Click Export JSON.** Save the file as `flo-2026-05-10.json` (or whatever today's date is) into `experiments/falzflyer-p2-mein-plan/results/` (create that directory).

3. **Run the aggregator.** From the worktree root:
   ```bash
   bin/experiment-results falzflyer-p2-mein-plan
   ```
   It writes `experiments/falzflyer-p2-mein-plan/results/SUMMARY.md` with rankings, the Spearman halo flag, the disagreement table, and a "Suggested corpus entries" stub formatted to paste straight into the corpus.

4. **Update the corpus.** Open `design-guide/gruene-corpus.md`, scroll to §6 (the falzflyer P2 critique), and amend it with at least the top-3 winners and bottom-3 losers from SUMMARY.md. Tag each entry: `provenance: experiment falzflyer-p2-mein-plan, run flo-<YYYY-MM-DD>, axis: appeal|transport`. If appeal and transport rankings disagree (Spearman < 0.5), surface BOTH rankings — disagreement is signal. If the run is inconclusive (wins-ratio differences < 10%), record THAT as the result with provenance — null results are corpus content per the acceptance gate.

5. **Commit** the results JSON + SUMMARY.md + corpus update together:
   ```bash
   git add experiments/falzflyer-p2-mein-plan/results/ design-guide/gruene-corpus.md
   git commit -m "29: docs(corpus): record top-3/bottom-3 from falzflyer-p2-mein-plan run flo-<DATE>"
   ```

6. **Tick the 8 acceptance-criteria checkboxes** in `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/ISSUE.md` and amend or add a final commit with that change.

That closes the merge gate (CONTEXT.md decision 11). The PR is ready to ship after step 6.
