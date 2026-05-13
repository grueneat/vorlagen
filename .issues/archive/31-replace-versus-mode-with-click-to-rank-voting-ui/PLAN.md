# Plan: Replace versus mode with click-to-rank voting UI

- **Slug:** `31-replace-versus-mode-with-click-to-rank-voting-ui`
- **Generated:** 2026-05-11
- **Source issue:** GH #62 / repo issue id `31`

<objective>
Deliver a click-to-rank voting UX that replaces the existing versus (pairwise) mode wholesale on `site/src/pages/experiments/[id].astro`. Voters click a dedicated checkmark control on each variant card (image click remains a lightbox open), variants appear as an ordered list below the grid that reorders via ▲/▼ arrow buttons (accessible primary path) and SortableJS drag-drop (tactile secondary path), and the page exports a new ranking-shape JSON. The `experiments/_schema/results.schema.yaml` and `tools/experiment_results.py` aggregator are rewritten end-to-end for the new shape — pairwise / versus code is deleted, not kept for backward compat. The `.claude/skills/experiments/SKILL.md` is rewritten to document rank as the primary mode. The merge of this issue closes the deferred T15 of #29, T17 of #30, AND #31's own corpus-update deliverable in one shot via a final dual-section corpus amendment (v1 envelope-necessity finding + v2 density+form finding) backed by a Flo-voted rank-mode session.
</objective>

<acceptance_gate>
Merge requires all 10 ISSUE.md acceptance criteria pass:

1. Rank mode implemented in `site/src/pages/experiments/[id].astro`.
2. Click-image-to-add (via dedicated checkmark control) works on desktop and mobile.
3. Ranked list below variants shows position + title + thumbnail + remove button per row.
4. Reorder works via both drag-drop AND up/down arrows.
5. localStorage persists ranking across reload (key `experiment:<id>:session:v2:rank`).
6. Export JSON has the new shape and validates against the rewritten schema.
7. `tools/experiment_results.py` aggregates the new ranking format; SUMMARY.md still produces top-3 / bottom-3 + dual-section corpus stub.
8. `.claude/skills/experiments/SKILL.md` updated; rank documented as primary mode.
9. Mobile-responsive — verified at ≥360px viewport.
10. T-final: Flo votes a v2 session in rank mode → JSON committed → `design-guide/gruene-corpus.md` amended with dual-section update. This single corpus amendment closes #29 T15 + #30 T17 + #31 corpus deliverable in one go.
</acceptance_gate>

<resolved_uncertainties>
RESEARCH.md surfaced a small set of MEDIUM-confidence items. Each is resolved here so the executor does not stop to deliberate.

1. **SortableJS bundle size (~13 kB min+gzip estimated)** — do NOT attempt to verify pre-build (bundlephobia returned 403 during research). Verify post-build instead by inspecting `npm --prefix site run build` output and the emitted `dist/_astro/*.js` sizes (T11 checklist). Acceptable if total page JS payload grows by ≤ 20 kB gzipped.

2. **SortableJS `delay` tuning (touch)** — start at `delay: 150, delayOnTouchOnly: true, touchStartThreshold: 5`. If the mobile-verify pass (T11) shows accidental drags on scroll, raise `delay` to `200`. If sustained-press feels sluggish, lower to `120`. Document the final value chosen in EXECUTION.md.

3. **Position badge: child of checkmark vs sibling** — RESOLVED in favor of **child of the checkmark `<button>`**, as an inner `<span class="position-badge">`. Rationale: tighter visual coupling (badge moves with checkmark), a single accessible target (`<button>` owns aria-pressed + aria-label including position), and the existing markup pattern in RESEARCH.md already shows the child layout. The badge is `hidden` until selected; the visual is absolutely positioned within the `<button>`.

4. **Direct-pick star-button accessibility gap** — DEFERRED to a separate issue. Scope of #31 is rank mode + schema/aggregator + skill update; the existing direct-pick path stays functionally identical. If T07's CSS overlap with star button is trivial, the executor MAY clean it up in passing, but no new behavior or a11y refactor of the star control lands here.

5. **Astro script convention shift** — RESEARCH.md notes the rank block must use `import Sortable from 'sortablejs'` inside a bundled `<script>` block (not `<script is:inline>`). The existing lightbox block stays `is:inline`. Both patterns coexist on the same page; Astro/Vite bundles only the non-inline block. No further mitigation needed.

6. **Whether to keep any versus utilities (Fisher-Yates shuffle, etc.)** — RESOLVED: rank mode does NOT need pair generation or position randomization. Delete the shared utility block in full (RESEARCH.md surgical map line 451-509). If rank needs a shuffle for tie-break visualization later, it can re-add a 4-line inline implementation.

7. **Schema oneOf discriminator pattern (HIGH-risk per pitfalls #3)** — Each branch declares both `properties.mode.const` AND `not: {required: [<opposite-field>]}` so a file with both `ranking` and `selections` is rejected. T03 codifies the test for this.

8. **localStorage v1 cleanup** — RESOLVED: on first load of new code, scan for `experiment:*:session:v1:*` keys, `console.log` a single migration note, delete them. No UI banner (CONTEXT decision 14 keeps it console-only).

9. **Export button placement on mobile** — RESOLVED: in-flow at the bottom of the ranked list (not sticky). Sticky-bottom adds CSS complexity and conflicts with iOS Safari's chrome behavior; deferred indefinitely.

10. **Title dedupe on variant card** — RESOLVED: keep the variant title on each card AND in each ranked-list row (RESEARCH.md card pattern includes only the image and checkmark; titles already exist on the cards in the current page). Cleanup of card chrome is out of scope.
</resolved_uncertainties>

<skills>
Read and follow these skills during execution:

- `@.claude/skills/python/SKILL.md` — applies to `tools/experiment_results.py` rewrite (T04) and the aggregator tests (T05). Python edits must follow repo Python conventions surfaced in this skill.

No other repo-local skill is enforcement-relevant. The voting page work is Astro/JS with no dedicated skill; brand-color, ARIA, and SortableJS guidance are inlined in the interfaces and tasks below.

Note: `.claude/skills/experiments/SKILL.md` is the **target** of edits in T12 — it is NOT a skill the planner or executor invokes during execution. Treat it as a documentation artifact.
</skills>

<context>
Issue: @.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/ISSUE.md
Context (locked decisions): @.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/CONTEXT.md
Research synthesis: @.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/RESEARCH.md
Research depth (codebase / ecosystem / pitfalls):
- @.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/research/codebase.md
- @.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/research/ecosystem.md
- @.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/research/pitfalls.md

Key files:
@site/src/pages/experiments/[id].astro — 645-line voting page; surgical change map in RESEARCH.md
@site/src/layouts/Base.astro — brand CSS custom properties at lines 12-17
@site/package.json — add `sortablejs@1.15.7` here
@experiments/_schema/results.schema.yaml — rewritten end-to-end in T03
@tools/experiment_results.py — 467-line aggregator; delete 4 fns + rewrite 2 + add 2 (T04)
@tools/sla_lib/tests/test_experiment_results.py — delete 3 test classes, add 1, keep DroppedAndCorpusStubTest
@.claude/skills/experiments/SKILL.md — full pass to rewrite versus → rank (T12)

<interfaces>
<!-- Executor: use these contracts directly. Do not re-derive from the codebase. -->

// ============================================================
// Variant card markup (NEW — sibling button, not overlay child of <img>)
// site/src/pages/experiments/[id].astro
// ============================================================
<div class="variant-card" data-slug="numbered-priority-list-v2">
  <img src="..." />  <!-- existing click handler at line 245 → lightbox UNCHANGED -->
  <button class="checkmark"
          aria-label="Select numbered-priority-list-v2"
          aria-pressed="false"
          type="button">
    <span class="checkmark-visual" aria-hidden="true"></span>  <!-- 32-36px visible -->
    <span class="position-badge" aria-hidden="true" hidden></span>  <!-- "1", "2", ... -->
  </button>
  <!-- existing title element stays where it is -->
</div>

// Defensive click handler (pitfall #1):
checkmark.addEventListener('click', (ev) => {
    ev.stopPropagation();
    toggleSelection(slug);
});

// ============================================================
// Ranked list markup (NEW — below the variant grid)
// ============================================================
<ol id="ranked-list" aria-label="Your ranked choices">
  <li data-slug="numbered-priority-list-v2" class="ranked-row">
    <span class="drag-handle" aria-hidden="true">⋮⋮</span>
    <button class="arrow-up" aria-label="Move up" type="button">▲</button>
    <button class="arrow-down" aria-label="Move down" type="button">▼</button>
    <img class="thumbnail" src="..." aria-hidden="true" />
    <span class="title">numbered-priority-list-v2</span>
    <button class="remove-btn" aria-label="Remove from ranking" type="button">×</button>
  </li>
  <!-- more rows -->
</ol>
<div id="rank-live-region" aria-live="polite" aria-atomic="true" class="sr-only"></div>

// ============================================================
// SortableJS init (HARD-REQUIRED config per pitfalls #2 + #5)
// ============================================================
import Sortable from 'sortablejs';

new Sortable(document.getElementById('ranked-list'), {
  handle: '.drag-handle',                              // only the handle initiates drag
  filter: '.arrow-up,.arrow-down,.remove-btn',         // these never initiate drag
  preventOnFilter: true,
  animation: 150,
  delay: 150,                                          // ms — see resolved uncertainty #2
  delayOnTouchOnly: true,                              // desktop = instant; touch = delayed
  touchStartThreshold: 5,                              // px finger jitter tolerance
  onEnd: (evt) => {
    persistRanking();
    announceMove(evt.item.dataset.slug, evt.oldIndex, evt.newIndex, ranking.length);
  },
});

// CSS: touch-action: none ON .drag-handle ONLY. Never on .ranked-row or .ranked-list.

// ============================================================
// Lightbox click pattern (UNCHANGED — line 245 in current file)
// ============================================================
img.addEventListener('click', () => openLightbox(img.src.replace('.png', '-hires.png')));
// Sibling <button class="checkmark"> click does NOT bubble through <img>. Safe by structure.

// ============================================================
// Results JSON shape (NEW)
// ============================================================
{
  "experiment_id": "falzflyer-p2-mein-plan-v2",
  "rater": "flo",
  "started_at": "2026-05-11T12:00:00Z",
  "exported_at": "2026-05-11T12:18:00Z",
  "mode": "rank",
  "ranking": ["numbered-priority-list-v2", "manifesto-single-statement-v2", "..."]
}
// Direct-pick variant uses "mode": "direct-pick" + "selections": [...] instead of "ranking".

// ============================================================
// Aggregator function signatures (tools/experiment_results.py)
// ============================================================
// DELETE (lines 59-146)
def compute_wins_ratio(...) -> dict: ...
def compute_ranking(...) -> list: ...
def compute_disagreement_index(...) -> int: ...
def compute_spearman_correlation(...) -> float: ...

// KEEP verbatim
def _load_hypotheses(exp_dir: Path) -> list: ...          # ~line 200
def _load_dropped(exp_dir: Path) -> list: ...             # ~line 220
def render_dropped_section(...) -> str: ...               # lines 255-270
def render_corpus_stub(...) -> str: ...                   # lines 273-296 (dual-section v1+v2)

// REWRITE
def aggregate(results_paths: list[Path]) -> dict: ...     # ~line 300
def render_summary(agg: dict, exp_dir: Path) -> str: ...  # ~line 380

// NEW
def compute_position_scores(ranking: list[str], all_slugs: list[str]) -> dict[str, float | None]:
    """position_score = (N - rank) / (N - 1) for rank in [0, N-1] over the ranked list of length N.
    Variants in all_slugs but not in ranking get None (excluded, not zero)."""

def compute_position_scores_for_direct_pick(selections: list[str], all_slugs: list[str]) -> dict[str, float | None]:
    """1.0 for each selected slug; None for unselected. Direct-pick fallback path."""

// ============================================================
// Brand color tokens (Base.astro:12-17)
// ============================================================
:root {
  --gruen-dunkel: #2a734f;
  --gruen-hell:   #6abf2c;
  --gelb:         #ffed00;
  --magenta:      #e6007e;
}
// Use var(--gruen-hell) for filled checkmark background; var(--gruen-dunkel) for position-badge text.

// ============================================================
// Schema discriminator pattern (oneOf + mode.const + not:required)
// ============================================================
oneOf:
  - properties:
      mode: { const: "rank" }
      ranking: { type: array, items: { type: string } }
    required: [experiment_id, rater, started_at, exported_at, mode, ranking]
    not: { required: [selections] }
  - properties:
      mode: { const: "direct-pick" }
      selections: { type: array, items: { type: string } }
    required: [experiment_id, rater, started_at, exported_at, mode, selections]
    not: { required: [ranking] }
</interfaces>
</context>

<commit_format>
Format: conventional with numeric issue-id prefix (per `.issues/config.yaml`).
Pattern: `31: {type}({scope}): {description}`
Examples:
- `31: feat(experiments): replace versus mode with click-to-rank voting`
- `31: chore(deps): add sortablejs@1.15.7 to site`
- `31: refactor(tools): rewrite experiment_results aggregator for rank shape`
- `31: docs(skill): rewrite experiments SKILL for rank as primary mode`
- `31: chore: update gruene-corpus.md with v1 + v2 dual-section findings`
</commit_format>

<tasks>

<task id="T01" name="install-sortablejs" type="auto">
  <action>
  Install SortableJS 1.15.7 as a pinned dependency in the `site/` workspace.
  Run: `npm --prefix site install sortablejs@1.15.7`.
  After install, confirm `site/package.json` `dependencies` block contains `"sortablejs": "1.15.7"` (exact pin, no `^`/`~`). If npm wrote a caret, edit the line to be exact.
  Smoke-test import resolves: `node -e "require('sortablejs')"` (resolves the CJS entry) inside the site dir.
  Do NOT yet touch `site/src/pages/experiments/[id].astro` — that's T06+.
  </action>
  <verify>
  <automated>
  grep -E '"sortablejs": "1\.15\.7"' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/package.json
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && node -e "require('sortablejs'); console.log('ok')"
  </automated>
  </verify>
  <done>SortableJS 1.15.7 installed and pinned exactly in `site/package.json`; resolves at runtime.</done>
</task>

<task id="T02" name="delete-versus-mode" type="auto">
  <action>
  Delete all versus-mode code paths from `site/src/pages/experiments/[id].astro`. Use the surgical map from RESEARCH.md:

  - **HTML lines 106-160** — versus block (pair display + keyboard hint + axis questions): delete entirely.
  - **JS lines 297-449** — versus pair generator + two-axis voting + Q/W/O/P/Space/E keyboard handler: delete entirely.
  - **Shared utilities lines 451-509** — Fisher-Yates shuffle, position randomization, pair generation helpers used ONLY by versus: delete entirely. Rank mode does not need them (resolved uncertainty #6).
  - **JS lines 510-569** — versus localStorage save/restore: delete entirely.
  - **Mode switcher lines 637-645** — drop the `"versus"` option from the mode selector init. Keep `"direct-pick"` for now; `"rank"` will be added in T06.
  - **Export controller lines 571-608** — strip the `versus` branch but leave `direct-pick` intact. Leave a `// TODO: rank mode wires in here at T10` comment at the point where the new branch will go.

  After deletion, the page MUST still build cleanly (proves there are no orphan references to deleted symbols from the surviving direct-pick code path).
  Do NOT add rank-mode markup or JS in this task — that's T06+.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build 2>&1 | tee /tmp/t02-build.log
  test "${PIPESTATUS[0]}" -eq 0
  ! grep -E 'versus|pairwise|compute_wins|disagreement' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  </automated>
  </verify>
  <done>`[id].astro` is versus-free, only `direct-pick` mode remains functional; `npm --prefix site run build` exits 0.</done>
</task>

<task id="T03" name="rewrite-results-schema" type="auto">
  <action>
  Rewrite `experiments/_schema/results.schema.yaml` end-to-end. The new schema is a JSON Schema Draft 2020-12 document with a top-level `oneOf` discriminating on `mode.const` (per pitfalls #3 + interfaces above):

  - Common required: `experiment_id` (string), `rater` (string), `started_at` (date-time string), `exported_at` (date-time string), `mode` (enum: `"rank" | "direct-pick"`).
  - Branch A (rank): `mode.const = "rank"`, requires `ranking` (array of strings, items unique), forbids `selections` via `not: {required: [selections]}`.
  - Branch B (direct-pick): `mode.const = "direct-pick"`, requires `selections` (array of strings, items unique), forbids `ranking` via `not: {required: [ranking]}`.

  Delete the existing pairwise shape entirely — no backward compat (CONTEXT decision 9).

  Add a new test file (or extend existing if one covers this schema):
  `tools/sla_lib/tests/test_experiment_results_schema.py` with four test cases:
  1. Valid rank file passes.
  2. Valid direct-pick file passes.
  3. Ambiguous file (both `ranking` AND `selections`) is REJECTED.
  4. Missing-mode file is REJECTED.
  5. Unknown-mode value (e.g. `"versus"`) is REJECTED.

  Use the existing `jsonschema` library (4.26.0, already in `Dockerfile.claude`) — the same one used by manifest + constraints schemas.
  </action>
  <verify>
  <automated>
  python3 -c "import yaml; yaml.safe_load(open('/root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/experiments/_schema/results.schema.yaml'))"
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui && python3 -m unittest tools.sla_lib.tests.test_experiment_results_schema -v
  </automated>
  </verify>
  <done>`results.schema.yaml` accepts new rank + direct-pick shapes, rejects ambiguous/legacy files; schema tests all pass.</done>
</task>

<task id="T04" name="rewrite-aggregator" type="auto">
  <action>
  Rewrite `tools/experiment_results.py` per the interface signatures above.

  - **Delete** (lines 59-146): `compute_wins_ratio`, `compute_ranking`, `compute_disagreement_index`, `compute_spearman_correlation`. Also remove any imports they relied on (scipy, statistics) that no longer have callers.
  - **Keep verbatim**: `_load_hypotheses`, `_load_dropped`, `render_dropped_section` (255-270), `render_corpus_stub` (273-296).
  - **Add** two new functions with exact signatures:
    - `compute_position_scores(ranking: list[str], all_slugs: list[str]) -> dict[str, float | None]`:
      For each `slug` in `ranking` at index `i` (0-based), `score = (N - 1 - i) / (N - 1)` where `N = len(ranking)`. Top-ranked → 1.0, bottom-ranked → 0.0. Edge case: `N == 1` → the single ranked slug gets 1.0 (avoid div-by-zero). Slugs in `all_slugs` not in `ranking` → `None`.
    - `compute_position_scores_for_direct_pick(selections: list[str], all_slugs: list[str]) -> dict[str, float | None]`:
      1.0 for each slug in `selections`; `None` otherwise.
  - **Rewrite** `aggregate(results_paths: list[Path]) -> dict`:
    - For each results file: parse JSON, validate against the rewritten schema (use `jsonschema.validate`), branch on `mode`.
    - For `rank` files: call `compute_position_scores`.
    - For `direct-pick` files: call `compute_position_scores_for_direct_pick`.
    - Aggregate per-slug scores across raters: mean of non-None scores. Count of raters per slug.
    - Return `{ "per_slug": {slug: {"mean_score": float, "n_raters": int}}, "raters": [...], "modes_seen": ["rank", ...] }`.
  - **Rewrite** `render_summary(agg, exp_dir) -> str`:
    - Sort slugs by `mean_score` descending (None last).
    - Output top-3 + bottom-3 sections.
    - Append dropped section via `render_dropped_section`.
    - Append corpus stub via `render_corpus_stub` (unchanged dual-section v1+v2 output).

  Run the aggregator end-to-end on a hand-crafted fixture to smoke-test, then move on to T05 for proper tests.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui && python3 -c "
  from tools.experiment_results import compute_position_scores, compute_position_scores_for_direct_pick
  assert compute_position_scores(['a','b','c','d'], ['a','b','c','d','e']) == {'a':1.0, 'b':2/3, 'c':1/3, 'd':0.0, 'e':None}
  assert compute_position_scores(['only'], ['only','x']) == {'only':1.0, 'x':None}
  assert compute_position_scores_for_direct_pick(['a','c'], ['a','b','c']) == {'a':1.0, 'b':None, 'c':1.0}
  print('aggregator-smoke-ok')
  "
  ! grep -E 'compute_wins_ratio|compute_disagreement_index|compute_spearman' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/tools/experiment_results.py
  </automated>
  </verify>
  <done>Aggregator computes linear Borda position scores from rank files and 1.0/None fallback from direct-pick files; versus functions purged; smoke assertions pass.</done>
</task>

<task id="T05" name="rewrite-aggregator-tests" type="auto">
  <action>
  Update `tools/sla_lib/tests/test_experiment_results.py`:

  - **Delete**: `WinsRatioTest`, `DisagreementTest`, `SpearmanTest` (lines 52-188 per RESEARCH map).
  - **Keep**: `DroppedAndCorpusStubTest` (lines 257-303) verbatim.
  - **Add `RankAggregationTest`** with cases:
    - Single-rater rank of 4 variants produces expected linear Borda scores `{a:1.0, b:0.667, c:0.333, d:0.0}` (within 1e-6 tolerance).
    - Two raters with same ranking → mean equals individual.
    - Two raters with disjoint rankings of the same slugs → mean averages correctly.
    - Slug present in `all_slugs` but absent from every `ranking` → `None` in `per_slug`.
    - Single-variant ranking (`N=1`) → 1.0 (no div-by-zero).
    - Empty ranking → all slugs `None`.
  - **Add `DirectPickFallbackTest`** with cases:
    - One rater selects 2 of 4 slugs → 1.0 / 1.0 / None / None.
    - Two raters select overlapping subsets → mean of 1.0s, None for never-selected.
  - **Add `MixedModeAggregationTest`** (single rater per mode, same experiment): rank result + direct-pick result combine correctly; `modes_seen` carries both.

  Run the full test suite for the tools package to confirm nothing else broke.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui && python3 -m unittest tools.sla_lib.tests.test_experiment_results -v
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui && python3 -m unittest discover tools/sla_lib/tests -v
  </automated>
  </verify>
  <done>Versus tests removed; rank + direct-pick + mixed-mode tests pass; `DroppedAndCorpusStubTest` still passes; full tools test suite green.</done>
</task>

<task id="T06" name="add-rank-mode-html" type="auto">
  <action>
  Add rank-mode HTML to `site/src/pages/experiments/[id].astro`. Reference the variant-card and ranked-list markup in `<interfaces>` above.

  - In the existing variant grid loop (around lines 26-95), add a `<button class="checkmark">` SIBLING to the `<img>` per card. Mandatory attributes: `type="button"`, `aria-label="Select <slug>"`, `aria-pressed="false"`. Children: `<span class="checkmark-visual" aria-hidden="true">` and `<span class="position-badge" aria-hidden="true" hidden>` (badge is child of button per resolved uncertainty #3).
  - Add a new `<ol id="ranked-list" aria-label="Your ranked choices">` BELOW the variant grid. It starts empty; rows are injected by JS in T08. Include the empty-state placeholder `<p class="rank-empty" id="rank-empty">No variants ranked yet — click a checkmark to add.</p>` next to the `<ol>`.
  - Add the live region: `<div id="rank-live-region" aria-live="polite" aria-atomic="true" class="sr-only"></div>`. Politeness MUST be `polite`, never `assertive` (pitfalls a11y note).
  - Add an export button below the ranked list: `<button id="export-rank" type="button">Export ranking JSON</button>`.
  - Update the mode switcher init (the block left by T02 at ~line 637) to:
    - Add `"rank"` as the first option.
    - Default to `"rank"` when the page has ≥3 variants (CONTEXT decision 2). Determine variant count from the existing data shape — likely a frontmatter or generated array. If <3 variants, default to `"direct-pick"`.
  - Do NOT add JS handlers in this task — wire the markup only. The site MUST still build.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build
  grep -E 'class="checkmark"' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E 'id="ranked-list"' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E 'aria-live="polite"' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  </automated>
  </verify>
  <done>Variant cards now carry sibling checkmark buttons, ranked-list placeholder is present below the grid, live region exists, mode switcher exposes "rank" and defaults to it for ≥3 variants. Build is green.</done>
</task>

<task id="T07" name="add-rank-mode-css" type="auto">
  <action>
  Add scoped `<style>` rules inside `site/src/pages/experiments/[id].astro` for rank mode.

  - `.checkmark` button: position absolute top-right of `.variant-card`; 44×44px hit zone (`min-width: 44px; min-height: 44px; padding: 6px;`); transparent background by default; rounded; outline-only `.checkmark-visual` icon at 32-36px. Hover state subtle. Focus visible.
  - `.checkmark[aria-pressed="true"]`: filled background `var(--gruen-hell)`; `.checkmark-visual` becomes white check; `.position-badge` is unhidden, displays the rank number in `var(--gruen-dunkel)` text on white circular pill in the top-left of the button.
  - `.ranked-row`: grid or flex row with reserved fixed height (e.g. `min-height: 56px`) to prevent CLS on insert (pitfalls a11y note). Order: drag-handle | arrows | thumbnail | title | remove-btn. `align-items: center`.
  - `.drag-handle`: 44×44px tap zone; `cursor: grab`; **`touch-action: none` ONLY on `.drag-handle`** — never on `.ranked-row` or `#ranked-list` (pitfalls #5).
  - `.arrow-up`, `.arrow-down`, `.remove-btn`: 44×44px tap zone each; visible 32px icon centered.
  - `.thumbnail`: 48×48px max.
  - `.position-badge`: small circular pill 18×18px, white background, `var(--gruen-dunkel)` text, bold, centered numeric.
  - `.sr-only`: standard screen-reader-only utility class (`position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0);`).
  - **Mobile (`@media (max-width: 640px)`):** variant grid collapses to 1-2 columns; ranked-list `<ol>` is full-width; row layout stays the same.

  Use brand CSS custom properties exclusively for colored elements — no hex values for green.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build
  grep -E 'var\(--gruen-hell\)' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E 'touch-action:\s*none' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E 'min-width:\s*44px|min-height:\s*44px' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  </automated>
  </verify>
  <done>Rank-mode CSS uses brand tokens, touch targets are ≥44×44, `touch-action: none` is scoped to `.drag-handle` only, mobile media query collapses the variant grid. Build is green.</done>
</task>

<task id="T08" name="add-rank-mode-js-selection-state" type="auto">
  <action>
  Add a bundled (non-`is:inline`) `<script>` block to `site/src/pages/experiments/[id].astro` that handles rank-mode SELECTION + STATE.

  - At the top of the block: `import Sortable from 'sortablejs';` (the import lives here for tree-shake correctness; the actual SortableJS init lands in T09).
  - State shape: `let ranking: string[] = [];` (in-memory mirror of localStorage).
  - localStorage key: `experiment:<experiment-id>:session:v2:rank`. Store `{started_at, ranking}`.
  - **On page load (rank mode init):**
    1. Scan all keys matching `experiment:*:session:v1:*`. For each match: `console.log('Migrating from v1 schema — clearing stale key:', key)` and `localStorage.removeItem(key)`. Single migration note per stale key (pitfall #4 + resolved uncertainty #8).
    2. Read existing v2 ranking from localStorage if present; restore into `ranking` array and rehydrate UI (mark checkmarks aria-pressed=true, inject ranked rows).
    3. Sanitize the rater-name input on read/write (`[a-z0-9_-]` whitelist; non-matching → `-`).
  - **Checkmark click handler** (per `<interfaces>` above):
    ```
    checkmark.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const slug = card.dataset.slug;
      if (ranking.includes(slug)) {
        ranking = ranking.filter(s => s !== slug);
      } else {
        ranking.push(slug);  // append to bottom
      }
      refreshRankUI();
      persistRanking();
    });
    ```
  - `refreshRankUI()` MUST:
    - Set `aria-pressed` on each card's checkmark to reflect `ranking.includes(slug)`.
    - Update `.position-badge` text + `hidden` state per card.
    - Rebuild `<ol id="ranked-list">` rows (drag-handle, arrows, thumbnail, title, remove-btn) in current `ranking` order.
    - Toggle the `#rank-empty` placeholder.
    - **Reserve row heights** to prevent CLS on insert (pitfalls a11y note); the row min-height in T07 CSS handles this.
  - `persistRanking()` writes the current `{started_at, ranking}` payload to localStorage.

  Do NOT implement reorder via arrows/drag in this task — that's T09. Do NOT wire export — that's T10.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build
  grep -E "import Sortable from 'sortablejs'" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E "session:v2:rank" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E "session:v1" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E "stopPropagation" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  </automated>
  </verify>
  <done>Checkmark clicks toggle slugs in/out of `ranking`, UI reflects state, localStorage v2 round-trips, v1 keys are detected and cleared with a console.log on first load. Build is green.</done>
</task>

<task id="T09" name="add-rank-mode-js-reorder" type="auto">
  <action>
  Implement reorder in `site/src/pages/experiments/[id].astro` rank-mode script block.

  - **Arrow buttons (▲/▼) per row** — primary accessible path (CONTEXT decision 7):
    - Click ▲: swap with previous neighbor in `ranking`; no-op if already top.
    - Click ▼: swap with next neighbor; no-op if already bottom.
    - After swap: `refreshRankUI()` + `persistRanking()` + announce via `#rank-live-region`.
    - Announcement format: `"Moved '<slug>' from position <old1based> to <new1based> of <N>"`. Politeness: `polite` (live region already declared). Update text content (don't replace the node) — keeps SR queue stable.
  - **SortableJS init** — tactile secondary path. Use the exact init config in `<interfaces>`:
    - `handle: '.drag-handle'` + `filter: '.arrow-up,.arrow-down,.remove-btn'` + `preventOnFilter: true` (pitfall #2 — HARD-REQUIRED).
    - `animation: 150, delay: 150, delayOnTouchOnly: true, touchStartThreshold: 5`.
    - `onEnd(evt)`:
      - Compute new `ranking` order by reading `data-slug` from each `<li>` in DOM order.
      - `persistRanking()`.
      - Announce via the same `announceMove(slug, oldIndex, newIndex, N)` helper used by arrows.
  - **Re-init SortableJS after each `refreshRankUI()`** — because the rebuilt `<ol>` is a fresh DOM. Best path: keep a single `sortableInstance` reference, call `.destroy()` before re-init, OR mutate rows in place without rebuilding the `<ol>`. Implementer's choice; pick whichever is simpler given how `refreshRankUI` is structured. Document the choice in EXECUTION.md.

  - **Remove-btn (X) per row** — wire here as part of reorder semantics (it's symmetric with checkmark-toggle):
    - Click X: remove the slug from `ranking`, `refreshRankUI()`, `persistRanking()`, announce `"Removed '<slug>' from position <pos>"`.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build
  grep -E "handle:\s*'\.drag-handle'" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E "filter:\s*'\.arrow-up" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E "delayOnTouchOnly" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E "rank-live-region" /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  </automated>
  </verify>
  <done>▲/▼ buttons, SortableJS drag, and X remove all reorder/remove correctly; every change persists to localStorage and announces via the polite live region; SortableJS handle + filter config matches pitfall #2 mitigation. Build is green.</done>
</task>

<task id="T10" name="add-rank-mode-js-export" type="auto">
  <action>
  Wire the export button (`#export-rank`) in the rank-mode script block.

  - On click:
    1. Sanitize rater name: `[a-z0-9_-]` whitelist; non-matching → `-`. If empty after sanitization, `prompt` for it once (existing direct-pick path has a similar pattern — match it).
    2. Build payload: `{ experiment_id, rater, started_at, exported_at: new Date().toISOString(), mode: "rank", ranking }`.
    3. Trigger download: filename `<rater>-<experiment_id>-rank-<YYYY-MM-DD>.json`. Use the same blob-download utility the existing direct-pick exporter uses; do NOT introduce a new helper.
  - **Edge cases (defensive):**
    - Rater not entered → prompt; if user cancels, abort with `console.log` and no error UI (keep parity with existing direct-pick UX).
    - Empty `ranking` → still allow export, but `console.warn('Exporting empty ranking')` (the aggregator handles empty rankings — see T05 test case).
    - Reload mid-session → handled by T08's restore step; no extra work here.
  - **Refactor the existing export controller** (the place T02 left a `// TODO: rank mode wires in here at T10`): branch on `currentMode`. The rank branch builds the new shape; the direct-pick branch is unchanged.

  After this task, the rank-mode UI is end-to-end functional: select → reorder → export.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build
  grep -E 'mode:\s*"rank"' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  grep -E '\-rank-\$\{|-rank-' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  ! grep -E 'TODO: rank mode wires in here' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/\[id\].astro
  </automated>
  </verify>
  <done>Export button produces a valid rank-shape JSON file with sanitized filename; export controller cleanly branches on mode; the T02 TODO marker is resolved. Build is green.</done>
</task>

<task id="T11" name="mobile-verification" type="checkpoint:human-verify">
  <action>
  Run `npm --prefix site run preview` (or `astro preview`) and open the deployed experiments page at `http://localhost:<port>/experiments/falzflyer-p2-mein-plan-v2/` (or whichever experiment is currently rendered) in a mobile-sized viewport. Use either a real phone connected on LAN OR the browser devtools mobile emulation at 360×640.

  Manual checklist — record results in EXECUTION.md:

  - [ ] Variant grid collapses to 1-2 columns at 360px width without overflow.
  - [ ] Checkmark hit zone is comfortable to tap (≥44×44 — confirm via devtools accessibility inspector or by tapping without missing).
  - [ ] Tapping the image opens the lightbox; tapping the checkmark toggles selection without opening the lightbox (pitfall #1 verified live).
  - [ ] Drag works on touch: long-press the `⋮⋮` handle, drag to reorder, drop. Items DO reorder; scrolling the page works when finger starts on a row body (not the handle).
  - [ ] ▲/▼ arrows work on touch — single tap moves the row; no accidental drag (pitfall #2 verified live).
  - [ ] X remove works on touch — single tap removes the row.
  - [ ] Ranked list scrolls naturally below the grid; export button is reachable.
  - [ ] aria-live announcements fire in a screen reader (VoiceOver iOS or TalkBack Android) on arrow-press and drop-end.
  - [ ] Reload mid-session restores ranking from localStorage v2.

  If any item fails: tune SortableJS `delay` (try 200ms first, then 120ms — see resolved uncertainty #2), adjust CSS, retry. Document the final `delay` value chosen.

  No automated tooling is in this repo for headless mobile verification; this task is intentionally manual. The executor records pass/fail per item in EXECUTION.md and only proceeds to T12 once all items pass.
  </action>
  <verify>
  <automated>
  # Automated check confirms a verification block exists in EXECUTION.md once filled in:
  grep -E '## T11.*Mobile|mobile-verification' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/.issues/31-replace-versus-mode-with-click-to-rank-voting-ui/EXECUTION.md 2>/dev/null || echo "EXECUTION.md T11 block missing — executor must fill it"
  </automated>
  </verify>
  <done>All 9 manual checklist items pass on a 360×640 viewport; final `delay` value documented in EXECUTION.md.</done>
</task>

<task id="T12" name="update-experiments-skill" type="auto">
  <action>
  Full rewrite pass on `.claude/skills/experiments/SKILL.md`:

  - Remove ALL versus-mode references from prose, examples, and the `/experiments capture` subsection.
  - Document rank as the primary voting mode. Describe the checkmark control, the ranked list below the grid, the dual reorder paths (▲/▼ and SortableJS drag).
  - Update the `/experiments capture` section: the aggregator now consumes the new ranking JSON shape (or direct-pick fallback); SUMMARY.md output structure is top-3 / bottom-3 + dropped section + dual-section corpus stub.
  - Update the results JSON shape example to the new rank shape (per `<interfaces>` above).
  - Note the breaking schema change explicitly (CONTEXT decision 9): "v1 pairwise results files are no longer processable; the schema bump is intentional, no migration tool ships."
  - Re-validate skill word count: must stay ≤ 5000 words (per skill convention). Run `wc -w` on the file; trim long-form prose if needed.

  Do NOT touch any other skill or any non-skill doc in this task.
  </action>
  <verify>
  <automated>
  ! grep -i -E 'versus|pairwise|disagreement|spearman' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/.claude/skills/experiments/SKILL.md
  grep -i -E 'rank.*primary|primary.*rank|click-to-rank' /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/.claude/skills/experiments/SKILL.md
  test $(wc -w < /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/.claude/skills/experiments/SKILL.md) -le 5000
  </automated>
  </verify>
  <done>SKILL.md is versus-free, documents rank as primary, shows the new JSON shape, and stays ≤ 5000 words.</done>
</task>

<task id="T13" name="verify-template-byte-stability" type="auto">
  <action>
  Sanity-check that all the editor surgery above did not perturb any production template rendering. The voting page edits and the aggregator rewrite are entirely outside `templates/`, but the rule is: re-verify byte-stability after any structural change in the repo.

  Compute SHA256 of the production template page-01.png artifacts for each shipped template and compare against `git show main:<path>`:
  - `templates/kandidat-falzflyer-din-lang/page-01.png`
  - `templates/kandidat-zeitung/page-01.png` (if present)
  - `templates/kandidat-plakat/page-01.png` (if present)
  - Any other `templates/*/page-01.png` discovered via glob.

  If any artifact differs: investigate. The expected outcome is byte-stable (no template code path was touched), so a diff would indicate accidental contamination (e.g. an unrelated git checkout).

  Document the SHA comparison results in EXECUTION.md.
  </action>
  <verify>
  <automated>
  cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui && for f in $(find templates -name 'page-01.png' 2>/dev/null); do
    NOW=$(sha256sum "$f" | awk '{print $1}')
    OLD=$(git show "main:$f" 2>/dev/null | sha256sum | awk '{print $1}')
    if [ "$NOW" != "$OLD" ]; then echo "DIFFER: $f (NOW=$NOW OLD=$OLD)"; exit 1; else echo "ok: $f"; fi
  done
  </automated>
  </verify>
  <done>All production template `page-01.png` artifacts match their `main` counterparts byte-for-byte; SHA comparisons logged.</done>
</task>

</tasks>

<verification>
After all tasks T01-T13, run the final acceptance gate:

```bash
# Tools side
cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui && python3 -m unittest discover tools/sla_lib/tests -v

# Site side
cd /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site && npm run build

# Skill word count
wc -w /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/.claude/skills/experiments/SKILL.md

# Versus / pairwise / disagreement greps come back EMPTY across the touched files
! grep -r -i -E 'versus|pairwise|compute_wins|disagreement|spearman' \
    /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/site/src/pages/experiments/ \
    /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/tools/experiment_results.py \
    /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/.claude/skills/experiments/SKILL.md \
    /root/workspace/.worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/experiments/_schema/results.schema.yaml
```

**Bundle size gate**: inspect `site/dist/_astro/*.js` after build; verify the rank-page chunk is ≤ 20 kB gzipped (`gzip -c <file> | wc -c`). SortableJS itself is ~13 kB gzipped per ecosystem research.

**Deferred to T-final (issue closure):** Flo runs a real rank-mode voting session on the v2 experiment, exports JSON, runs `bin/experiment-results` (or the equivalent capture command per the rewritten SKILL.md), and amends `design-guide/gruene-corpus.md` with the dual-section update (v1 envelope-necessity finding + v2 density+form finding). This single commit closes the deferred corpus deliverables of #29 T15 + #30 T17 + #31's own acceptance criterion 10 in one shot.

Done-checklist for merge:
- [ ] All unit tests pass: `python3 -m unittest discover tools/sla_lib/tests`
- [ ] `npm --prefix site run build` exits 0
- [ ] Site renders and operates on a phone (manual smoke verified at T11)
- [ ] Versus mode entirely removed from page + skill + aggregator + schema
- [ ] Direct-pick mode still works (unchanged code path)
- [ ] SortableJS bundle size verified ≤ 20 kB gzipped after build
- [ ] Production falzflyer + zeitung + plakat `page-01.png` byte-stable (T13)
- [ ] T-final (separate commit): Flo's rank-session JSON committed; `design-guide/gruene-corpus.md` amended with dual-section v1+v2 findings — closes #29 T15 + #30 T17 + #31 deliverable
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:

1. Rank mode implemented in `site/src/pages/experiments/[id].astro` → T02, T06–T10.
2. Click-image-to-add (via checkmark control) works on desktop + mobile → T06 (markup), T08 (handler), T11 (mobile verify).
3. Ranked list with position + title + thumbnail + remove button → T06 (markup), T07 (CSS), T08 (refresh), T09 (X handler).
4. Reorder via drag-drop AND up/down arrows → T09 (both paths).
5. localStorage persists ranking across reload (`session:v2:rank`) → T08 (state + restore).
6. Export JSON validates against extended schema → T10 (export), T03 (schema).
7. `tools/experiment_results.py` aggregates new format; SUMMARY.md unchanged shape → T04, T05.
8. `.claude/skills/experiments/SKILL.md` documents rank as primary → T12.
9. Mobile-responsive verified → T11.
10. Flo's rank session + dual-section corpus amendment → T-final (deferred outside the executor's tactical task list; this is the merge gate before closing the PR; explicitly noted in `<verification>` above).
</success_criteria>

<out_of_scope>
Restated from CONTEXT.md `## Deferred` plus planner-added:
- Re-introducing dual-axis (appeal + transport) inside rank mode.
- Multi-rater real-time merging.
- Adaptive sampling.
- Auto-corpus-update from results.
- Versus mode revival (deleted entirely; if pairwise data becomes valuable later, a separate clean issue revives it without touching the old code path).
- Migrating v1 pairwise JSON results to the new format (none committed; no migration tool ships).
- Mobile gestures beyond drag (no swipe-to-remove, no long-press menus).
- **Planner-added:** ranking + direct-pick UI polish for consistency (e.g. star-button accessibility refactor, resolved-uncertainty #4) — separate issue.
- **Planner-added:** cross-rater merging logic (the aggregator combines scores via simple mean — anything fancier is a future issue).
- **Planner-added:** Sticky-bottom export button on mobile — kept in-flow.
</out_of_scope>
