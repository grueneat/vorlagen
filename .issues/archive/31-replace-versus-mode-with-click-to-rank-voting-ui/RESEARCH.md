# Research Synthesis — Issue #31

Three parallel sub-agents researched codebase / ecosystem / pitfalls. Full outputs in `research/codebase.md`, `research/ecosystem.md`, `research/pitfalls.md`. This synthesis is what the planner reads first.

**Overall confidence: HIGH.** One new dependency (SortableJS 1.15.7), zero peer deps. Voting page anatomy fully mapped to exact line ranges. Lightbox / checkmark coexistence solved by the existing event-listener placement.

---

## User Constraints (from CONTEXT.md — locked, verbatim)

1. **Versus mode deleted entirely.** Voting page exposes `direct-pick` + new `rank` only. Rank is default on load when ≥3 variants.
2. **Image keeps lightbox click behavior.** Selection is via a dedicated checkmark control top-right of each variant card. Checkmark is filled green when selected + position number badge.
3. **Checkmark touch target ≥44×44px** (WCAG AA). Visible size can be smaller (32×32) with padding for hit zone.
4. **Ranked list below grid** with position number + title + thumbnail + ▲/▼ + drag handle + X per row.
5. **SortableJS + ▲/▼ arrows both implemented.** Arrows are the accessible/primary path; drag is tactile secondary.
6. **New ranking JSON format only.** Old pairwise schema deleted. Shape: `{experiment_id, rater, started_at, exported_at, mode, ranking: [slug,...]}`. Direct-pick uses `selections` instead of `ranking`, schema `oneOf` discriminates by `mode.const`.
7. **Aggregator simplified.** `position_score = (N - rank) / (N - 1)`. Drop dual-axis (Spearman, disagreement). Direct-pick fallback: `position_score = 1.0` per selection.
8. **localStorage key bumped to v2.** No v1 migration — clear + console.log on first load.
9. **Mobile responsive verified against real phone screen.**

---

## Summary

**Primary recommendation:** the entire change is bounded — one Astro page, one schema, one aggregator, one skill. The voting page diff has known line ranges; the schema is rewritten end-to-end; the aggregator deletes 4 functions and rewrites 2; the skill loses its versus section.

**Three new artifacts:**
- `sortablejs@1.15.7` added to `site/package.json` dependencies.
- New rank-mode HTML + CSS + JS block in `site/src/pages/experiments/[id].astro` (replaces the versus block at lines 106–160 + 297–449 + 510–569).
- New aria-live region for screen-reader announcements ("Moved X from position 3 to 2 of 5").

**Five edits to shipped code:**
- `site/src/pages/experiments/[id].astro` — delete versus paths; add rank UI + script; switch from `<script is:inline>` IIFE to `import Sortable from 'sortablejs'` in a bundled `<script>` block. Mode selector defaults to `rank`.
- `experiments/_schema/results.schema.yaml` — rewrite end-to-end as `oneOf` over `{mode: "rank", ranking: [...]}` and `{mode: "direct-pick", selections: [...]}` with `mode.const` discriminators and `not: required` on the opposite field per branch.
- `tools/experiment_results.py` — delete `wins_ratio`, `ranking`, `disagreement_index`, `spearman_correlation` (lines 59–146); rewrite `aggregate()` and `render_summary()`; keep `_load_hypotheses`, `_load_dropped`, dropped section (255–270), dual-section corpus stub (273–296).
- `tools/sla_lib/tests/test_experiment_results.py` — delete `WinsRatioTest`, `DisagreementTest`, `SpearmanTest` (52–188); keep `DroppedAndCorpusStubTest` (257–303); add `RankAggregationTest`.
- `.claude/skills/experiments/SKILL.md` — full pass to remove versus references, document rank as primary mode, update `/experiments capture` section for new SUMMARY.md format.

**Most consequential finding (codebase):** the image's click listener is attached to the `<img>` element itself (line 245), not to a parent container. That means a sibling `<button class="checkmark">` cannot bubble through it — the click coexistence is structurally safe by accident of the existing code. `stopPropagation` on the checkmark is still recommended defensively (per pitfalls research §1-2), but the failure mode the user worried about ("clicking checkmark also opens gallery") is not architecturally possible if the checkmark is a sibling button, not an overlay child of the `<img>`.

**Most consequential finding (pitfalls):** SortableJS handle/cancel misconfig is the #2 risk after the click collision. Default behavior makes the entire row draggable, which means tapping ▲/▼/X would initiate a drag instead of firing the button click. Mitigation: `handle: '.drag-handle'` + `filter: '.arrow-up,.arrow-down,.remove-btn'`. Hard-required configuration.

**Most consequential finding (ecosystem):** SortableJS has no native keyboard reorder support (open issue #1951). The CONTEXT-locked arrow buttons aren't just a redundancy — they're the only accessible path. `aria-live="polite"` region announces each move ("Moved 'X' from position 3 to 2 of 5"). Never use `assertive`.

---

## Codebase Analysis

### Surgical change map for `site/src/pages/experiments/[id].astro` (645 lines)

| Lines | Today | Action |
|---|---|---|
| 1-25 | frontmatter + getStaticPaths | keep |
| 26-95 | base layout + variant grid markup | keep, add checkmark `<button>` per card |
| 98-104 | direct-pick HTML | keep |
| 106-160 | versus mode HTML (block + keyboard hint + axis questions) | **DELETE** |
| 162-169 | lightbox markup | keep |
| 170-228 | direct-pick CSS + star button | keep (and copy the pattern for checkmark) |
| 230-295 | direct-pick JS (state, localStorage `session.direct_picks`, export) | keep |
| 297-449 | versus JS (pair generator, two-axis voting, keyboard Q/W/O/P/Space/E) | **DELETE** |
| 451-509 | shared utilities (Fisher-Yates shuffle, position randomization) | move what rank needs, delete rest |
| 510-569 | versus localStorage save/restore | **DELETE** |
| 571-608 | export controller (mode-aware) | refactor to handle `rank` mode |
| 609-635 | lightbox click handlers | keep |
| 637-645 | mode switcher init | refactor: drop "versus" option, default to "rank" |

**New code to add** (replacing the deleted blocks):
- Rank mode HTML: ranked list `<ol>` below grid, each `<li>` with drag-handle, ▲, ▼, thumbnail, title, X.
- Rank mode CSS: row layout, drag handle visual, selected-state on grid card (checkmark filled + position badge).
- Rank mode JS: `import Sortable from 'sortablejs'`, state shape `session.ranking: string[]`, click-checkmark handler, SortableJS init with `handle: '.drag-handle'` + `filter: '.arrow-up,.arrow-down,.remove-btn'` + `delayOnTouchOnly: true, delay: 150, touchStartThreshold: 5`, `aria-live="polite"` updates per move, export.

### Lightbox coexistence (verified safe)

<interfaces>
// site/src/pages/experiments/[id].astro:245 — existing image click handler
img.addEventListener('click', () => openLightbox(img.src.replace('.png', '-hires.png')));

// A sibling button on the same card does NOT inherit this listener:
// <div class="variant-card">
//   <img onclick={lightbox} />        ← click listener here
//   <button class="checkmark"></button>  ← click here does NOT bubble to img
// </div>
//
// Defensive belt-and-suspenders (recommended anyway):
checkmark.addEventListener('click', (ev) => {
    ev.stopPropagation();
    toggleSelection(slug);
});
</interfaces>

### Aggregator delete + keep map (`tools/experiment_results.py`, 467 lines)

<interfaces>
// DELETE (versus-mode artifacts)
def compute_wins_ratio(...) -> dict        // lines 59-86
def compute_ranking(...) -> list           // lines 88-104
def compute_disagreement_index(...) -> int // lines 106-122
def compute_spearman_correlation(...) -> float  // lines 124-146

// KEEP verbatim
def _load_hypotheses(exp_dir: Path) -> list  // ~line 200
def _load_dropped(exp_dir: Path) -> list     // ~line 220
def render_dropped_section(...) -> str       // lines 255-270
def render_corpus_stub(...) -> str           // lines 273-296 (dual section: v1+v2)

// REWRITE
def aggregate(results_paths: list[Path]) -> dict  // ~line 300
def render_summary(agg: dict, exp_dir: Path) -> str  // ~line 380

// NEW
def compute_position_scores(ranking: list[str], all_slugs: list[str]) -> dict[str, float | None]
    """position_score = (N - rank) / (N - 1) for rank in [0, N-1]; None for unranked."""

def compute_position_scores_for_direct_pick(selections: list[str], all_slugs: list[str]) -> dict[str, float | None]
    """1.0 for selected, None for unselected (used in direct-pick fallback)."""
</interfaces>

### Brand color tokens (verified at `site/src/layouts/Base.astro:12-17`)

```css
:root {
  --gruen-dunkel: #2a734f;
  --gruen-hell: #6abf2c;
  --gelb: #ffed00;
  --magenta: #e6007e;
}
```

Use `var(--gruen-hell)` for filled checkmark background. `var(--gruen-dunkel)` for the position-number badge text on the filled checkmark.

---

## Standard Stack (verified)

| Tool | Version | New? | Source |
|---|---|---|---|
| **SortableJS** | **1.15.7** | **NEW** | [npm](https://www.npmjs.com/package/sortablejs), MIT, zero runtime deps |
| Astro | 5.18.1 | unchanged | site/package.json |
| jsonschema | 4.26.0 | unchanged | Dockerfile.claude |
| PyYAML | 6.0.3 | unchanged | Dockerfile.claude |

**Net new dependencies for this MVP: ONE.** SortableJS — ~13kb min+gzip, bundled into the page JS by Astro/Vite, static-deploy safe.

---

## Don't Hand-Roll

| Problem | Use instead |
|---|---|
| Drag-drop reorder | SortableJS 1.15.7 with `handle: '.drag-handle'` + `filter: '.arrow-up,.arrow-down,.remove-btn'` |
| Keyboard reorder | Hand-roll ▲/▼ arrow buttons. SortableJS has no keyboard support (open issue #1951); CONTEXT mandates this. |
| Schema discriminator | JSON Schema Draft 2020-12 `oneOf` with `properties.mode.const` + `not: required` on opposite field |
| Position-score formula | `(N - rank) / (N - 1)` — normalized linear Borda count, standard rank-aggregation form |
| Screen-reader move announcements | Single `<div aria-live="polite">` updated on each move ("Moved 'X' from position 3 to 2 of 5"). Never `assertive`. |
| Touch target sizing | Outer `<button>` 44×44px hit zone; inner visible 32-36px element via padding |
| Mobile drag tuning | `delayOnTouchOnly: true, delay: 150, touchStartThreshold: 5` + `touch-action: none` on `.drag-handle` ONLY (never row or container) |
| Filename sanitization | `[a-z0-9_-]` whitelist; non-matching → `-` |

---

## Architecture Patterns

### Variant card structure (new markup, sibling to image not child)

```html
<div class="variant-card" data-slug="numbered-priority-list-v2">
  <img src="..." onclick="lightbox()" />        <!-- image click → lightbox (UNCHANGED) -->
  <button class="checkmark"                      <!-- SIBLING button → toggle selection -->
          aria-label="Select numbered-priority-list-v2"
          aria-pressed="false">
    <span class="checkmark-visual"></span>       <!-- visible icon (32-36px) -->
    <span class="position-badge" hidden></span>  <!-- "1", "2", ... when selected -->
  </button>
</div>
```

### Ranked list row structure

```html
<ol id="ranked-list" aria-label="Your ranked choices">
  <li data-slug="..." class="ranked-row">
    <span class="drag-handle" aria-hidden="true">⋮⋮</span>
    <button class="arrow-up" aria-label="Move up">▲</button>
    <button class="arrow-down" aria-label="Move down">▼</button>
    <img class="thumbnail" src="..." aria-hidden="true" />
    <span class="title">numbered-priority-list-v2</span>
    <button class="remove-btn" aria-label="Remove from ranking">×</button>
  </li>
</ol>
<div id="rank-live-region" aria-live="polite" aria-atomic="true" class="sr-only"></div>
```

### Results JSON shape (new)

```json
{
  "experiment_id": "falzflyer-p2-mein-plan-v2",
  "rater": "flo",
  "started_at": "2026-05-11T12:00:00Z",
  "exported_at": "2026-05-11T12:18:00Z",
  "mode": "rank",
  "ranking": ["numbered-priority-list-v2", "manifesto-single-statement-v2", "..."]
}
```

Direct-pick variant uses `"mode": "direct-pick"` + `"selections": [...]` instead of `ranking`. Schema `oneOf` enforces.

---

## Common Pitfalls (Top 5)

1. **Image-click vs checkmark-click collision (CRITICAL).** Architecturally safe given the lightbox listener attaches to `<img>` directly and the checkmark will be a sibling `<button>`, but add `stopPropagation` defensively. `preventDefault` is the wrong fix (it doesn't stop bubbling).

2. **SortableJS handle/cancel misconfig (HIGH).** Default behavior makes the entire row draggable. Without `handle: '.drag-handle'` + `filter: '.arrow-up,.arrow-down,.remove-btn'`, tapping ▲/▼/X initiates a drag instead of clicking. Hard-required config.

3. **Schema `oneOf` discriminator (HIGH).** Naive `oneOf` matches loosely. Pattern: each branch declares `properties.mode.const: "rank"` (or `"direct-pick"`) AND `not: {required: [<opposite-field>]}` so an ambiguous file with both `ranking` and `selections` is rejected. Aggregator validates BEFORE reading.

4. **localStorage v1→v2 silent data loss (MEDIUM-HIGH).** In-progress votes in old keys disappear at deploy time. Mitigation: on page load, scan for `experiment:*:session:v1:*` keys, `console.log` migration note, delete them. Optional UI banner.

5. **Mobile scroll-vs-drag disambiguation (HIGH).** `touch-action: none` on `.drag-handle` ONLY — applying it to row or container kills scroll. Combined with `delay: 150, delayOnTouchOnly: true, touchStartThreshold: 5` so a slow finger movement scrolls but a sustained press initiates drag. Mobile is the primary use case; this isn't optional.

Plus 10 more pitfalls in `research/pitfalls.md` (touch target enforcement, ARIA live region politeness, bundle size verification, CLS from list inserts, scroll-position preservation, rater-name sanitization, etc.).

---

## Environment Audit

Verified on 2026-05-11:

- Node v26.0.0, npm 11.12.1 — installable
- Astro 5.18.1 in `site/package.json` — unchanged
- `sortablejs@1.15.7` available on npm — MIT license, zero peer deps, ESM+CJS+UMD shipped
- jsonschema 4.26.0 in Dockerfile.claude — Draft 2020-12 supported (already used by manifest + constraints schemas)
- All voting infrastructure from #29/#30 is now on main (`9f1bbac`, `6db6b521`)
- `tools/experiment_results.py` exists with 467 lines; test file at `tools/sla_lib/tests/test_experiment_results.py`
- `.claude/skills/experiments/SKILL.md` exists (1310 words per #30 EXECUTION)
- `experiments/_schema/results.schema.yaml` exists with the pairwise shape

**No blockers.**

---

## Project Constraints

- No `CLAUDE.md` at workspace root — repo conventions documented in `README.md`.
- Astro build flow: `npm --prefix site run build`. Pages live in `site/src/pages/`, layouts in `site/src/layouts/`, content collections in `site/src/content.config.ts`.
- Existing JS convention is `<script is:inline>` IIFE blocks. SortableJS forces a shift to `import` inside a bundled `<script>` block — Astro handles this transparently. Both patterns can coexist on the same page; the rank block uses `import`, the lightbox block stays inline.
- CSS convention: scoped styles inside `.astro` files via `<style>` blocks. Brand colors as CSS custom properties on `:root` in `Base.astro`.
- Touch-target floor: WCAG 2.2 AA Level requires ≥24×24 ([SC 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)); CONTEXT locks ≥44×44 per CONTEXT decision 5 (matches WCAG AAA + Apple HIG + Material).

---

## Sources

### HIGH confidence (direct inspection)

- `site/src/pages/experiments/[id].astro:1-645` (full voting page anatomy)
- `site/src/layouts/Base.astro:12-17` (brand CSS custom properties)
- `tools/experiment_results.py:1-467` (aggregator structure)
- `tools/sla_lib/tests/test_experiment_results.py:52-303` (test fixtures and which to delete vs keep)
- `experiments/_schema/results.schema.yaml` (current pairwise shape — to be rewritten)
- `.claude/skills/experiments/SKILL.md` (versus mode references to remove)

### HIGH confidence (external)

- [SortableJS 1.15.7 on npm](https://www.npmjs.com/package/sortablejs) — version, license, peer deps
- [SortableJS docs](https://sortablejs.github.io/Sortable/) — handle, filter, delay, touch options
- [SortableJS issue #1951 — keyboard support](https://github.com/SortableJS/Sortable/issues/1951) (open, no native a11y)
- [SortableJS issue #1621 — handle scoping](https://github.com/SortableJS/Sortable/issues/1621)
- [JSON Schema 2020-12 conditional patterns](https://json-schema.org/understanding-json-schema/reference/conditionals)
- [WCAG 2.2 Target Size (Minimum) — SC 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [WCAG 2.2 Target Size (Enhanced) — SC 2.5.5 AAA](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced)
- [Apple HIG: Touch targets](https://developer.apple.com/design/human-interface-guidelines/inputs/touch-bar)
- [Astro client-side scripts](https://docs.astro.build/en/guides/client-side-scripts/)
- Borda count formulation — Wikipedia + standard rank-aggregation literature

### MEDIUM confidence

- SortableJS exact bundle size (~13 kB min+gzip estimated; bundlephobia 403 on lookup)
- `delay` ms tuning — 150ms balances responsiveness and accidental drag, but per-device feel may vary
- Whether to render the position badge as a child of the checkmark or as a separate adjacent element (visual judgment)
