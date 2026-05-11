# Codebase research — Issue #31

## 1. `site/src/pages/experiments/[id].astro` — full structure

File: 645 lines, single self-contained Astro page. One `<Base>` slot, one `<script id="exp-data" type="application/json">` payload, one `<script is:inline>` IIFE.

### 1a. Frontmatter (lines 1–51)
- `getStaticPaths` loads `getCollection('experiments')`; falls back to a `placeholder` route when none exist (lines 5–16).
- Props: `{ exp }`. Derived: `expId`, `subject`, `hypotheses[]`, `llms[]`, `totalPairs = n*(n-1)/2` (line 31–33; **versus-only**).
- `variantsForJs` (lines 37–50) shapes the JSON injected to the client: `{ slug, name, axis_commitments[], rationale, expected_outcome, wildcard, thumb, hires }`. Thumb and hires resolve via `h._previews.thumb`/`.hires` or fall back to `/experiments/<expId>/<slug>/page-01[-hires].png`.

### 1b. HTML structure (lines 52–169)
- Header line (id, hypothesis count, LLMs) — lines 61–64.
- `#exp-banner` non-persistent-localStorage warning — lines 67–70. **Keep.**
- Toolbar (lines 72–86): rater input `#exp-rater`, two mode buttons `#exp-mode-direct` + `#exp-mode-versus`, `#exp-export`. Class `.exp-mode-btn` on both mode buttons.
- `<details>` shortcut help labeled "Versus-Mode" — lines 88–96. **Versus-only, delete.**
- `<section id="exp-direct" class="exp-mode">` with `#exp-direct-grid` — lines 98–104.
- `<section id="exp-versus" class="exp-mode">` — lines 106–160. Contains `<progress id="exp-progress-appeal">`, `<progress id="exp-progress-transport">`, `#exp-pair-area` with two `.exp-card[data-side]` divs each holding `.exp-card-img` + `.exp-card-name`, four `.exp-vote-btn[data-axis][data-side]` buttons, and `#exp-skip`. **Entire section is versus-only — delete.**
- Lightbox markup `#exp-lightbox` / `#exp-lightbox-close` / `#exp-lightbox-label` / `#exp-lightbox-image` — lines 162–169. **Keep, shared.**

### 1c. Inline script (lines 177–642)
Loaded via `<script is:inline>`. Mirror of `templates/[...id].astro:55–90` pattern. Structure (with delete vs keep markings):

- Storage helpers + `STORAGE_KEY = 'experiment:'+EXP_ID+':session:v1'` — lines 178–211. **Key changes to `v2:<mode>` per CONTEXT decision #14. Storage-detection logic stays.**
- `session` object shape: `{ rater, session_start, votes[], direct_picks[] }` — line 213–218. **Replace with mode-shaped session.**
- Rater field wiring — lines 221–228. **Keep.**
- `renderDirect()` — lines 230–295. **Keep, refactor:** star button at lines 252–266 (`★`/`☆` glyphs, color `#dca400` selected / `#888` empty, font-size 1.4em, no fixed touch target). Image click → `openLightbox(v.hires, v.name)` — line 245–247.
- Versus mode body — lines 297–449:
  - `fisherYates()` (298–304) — **delete** (rank doesn't need shuffling; if needed elsewhere later, lift before delete).
  - `buildPairs()` + `pairQueue` (305–322) — **delete.**
  - `pairState`, `leftCard`/`rightCard` queries, `currentPair()`, `variantForSide()`, `showPair()`, `recordVote()`, `advanceIfBothAxesDone()`, `skipPair()`, `updateProgress()` — **delete (lines 324–435).**
  - `.exp-vote-btn` handler (438–447), `#exp-skip` handler (448–449) — **delete.**
  - Lightbox handlers on `.exp-card`s (452–459) — **delete (versus cards gone).**
- `setMode()` — lines 462–476. **Refactor** to handle `direct` + `rank` only; remove `versus` branch and the `versusBtn`.
- Keyboard handler — lines 479–504. **Delete versus shortcuts (Q/W/O/P/Space).** Keep `E` → export (the only general shortcut).
- `winsRatio`, `ranking`, `disagreementIndex`, `spearman` — lines 510–569. **Delete all** (CONTEXT decision #11: position_score replaces these).
- `doExport()` — lines 571–606. **Rewrite.** Currently emits `{experiment_id, rater, session_start, session_end, votes, direct_picks, wins_ratio_appeal, wins_ratio_transport, ranking_appeal, ranking_transport, disagreement_index, spearman_appeal_transport}` and writes `<rater>-<expId>-<ts>.json`. New shape per CONTEXT #10 and filename per CONTEXT #15 (`<rater>-<exp-id>-<mode>-<YYYY-MM-DD>.json`).
- Lightbox open/close/click/keydown — lines 609–635. **Keep.** Lightbox closes on `Escape`, on click of `lightbox` itself, on click of `lightImg`, or via `#exp-lightbox-close`. Body overflow toggled.
- Boot (lines 638–640): `renderDirect(); updateProgress(); setMode('direct');`. **Refactor:** `setMode('rank')` becomes default when `VARIANTS.length >= 3` (CONTEXT #2).

### 1d. Lightbox click attachment
The lightbox is opened from two places today:
1. The direct-pick `<img>` (line 240–247): click on the image element directly → `openLightbox(v.hires, v.name)`.
2. The versus card `.exp-card-img` (line 456–458): same pattern.

For rank mode the checkmark must NOT bubble to the image click. Pattern to use: the image element keeps its own listener; the checkmark is a sibling positioned-absolute element (not nested inside the `<img>`, since `<img>` cannot contain children anyway). The checkmark `<button>` calls `ev.stopPropagation()` in its own handler to prevent the image-click handler from firing — except the image's listener is on the `<img>` itself, not the card, so the button being a sibling and a different element already means no collision. The relevant pattern: `card` wraps `<img>` + `<button class="checkmark">`, both as direct children. Image click handler attaches only to `<img>`; checkmark click handler attaches to `<button>`. No event delegation in current code — every handler is direct attach in `renderDirect`. Mirror that. `templates/[...id].astro:77` uses `ev.preventDefault()` on an `<a>` wrapper; this file does not (img has no default click action).

## 2. Direct-pick mode anatomy (to keep + visually align)

- Selection state: `session.direct_picks: string[]` — unordered, slug strings. `indexOf` for membership; `splice`/`push` for toggle (lines 254–263).
- localStorage key today: `experiment:<expId>:session:v1`. **Will bump to `:v2:direct-pick` per CONTEXT #14.**
- Export JSON today (line 580–593): includes `direct_picks: []` alongside versus fields. **Replace with mode-specific shape:** `{ experiment_id, rater, started_at, exported_at, mode: "direct-pick", selections: [slug, ...] }` (CONTEXT #10).
- Visual treatment of the star (line 252–257): `<button>` with `★`/`☆` text, no border, font-size `1.4em`, color `#dca400` selected / `#888` empty. Touch target = whatever the glyph + font-size renders to (roughly 22×22px — fails WCAG ≥44×44px). **The new checkmark must satisfy ≥44×44px (CONTEXT #5); applying the same standard to the existing star is in the planner's discretion.**

## 3. Versus mode anatomy (to be deleted in full)

Exclusively-versus DOM:
- `#exp-mode-versus` button (line 80–81).
- `<details>` shortcut help (lines 88–96).
- `<section id="exp-versus">` and everything inside (lines 106–160): `#exp-progress-appeal`, `#exp-progress-transport`, `#exp-progress-appeal-label`, `#exp-progress-transport-label`, `#exp-pair-area`, `.exp-card[data-side]`, `.exp-card-img`, `.exp-card-name`, `.exp-vote-btn`, `#exp-appeal-left`, `#exp-appeal-right`, `#exp-transport-left`, `#exp-transport-right`, `#exp-skip`.

Exclusively-versus JS (within the IIFE):
- `fisherYates`, `buildPairs`, `pairQueue`, `pairIdx`, `pairState`, `leftCard`, `rightCard`, `leftImg`, `rightImg`, `leftName`, `rightName`, `currentPair`, `variantForSide`, `showPair`, `recordVote`, `advanceIfBothAxesDone`, `skipPair`, `updateProgress`, `winsRatio`, `ranking`, `disagreementIndex`, `spearman` (lines 297–569 minus what's stated below).
- localStorage `votes[]` field of `session` (line 217).
- The `.exp-vote-btn` query + handler (438–447).
- `#exp-skip` handler (448–449).
- The `[leftCard, rightCard].forEach(...)` lightbox wiring (452–459).
- Keyboard cases `q`/`w`/`o`/`p`/` ` (lines 491–500).

Shared utilities (lift, do not delete):
- `nowISO` (line 212) — still needed for timestamps.
- `storageOK` + `loadSession`/`saveSession` (lines 188–210) — still needed.
- `openLightbox`/`closeLightbox` and lightbox DOM (lines 609–635) — keep verbatim.

Keyboard shortcuts taxonomy:
- Q/W/O/P/Space → versus-only — DELETE.
- E → export, general — KEEP. The handler at lines 482, 487, 502 already runs `doExport()` regardless of mode.

## 4. Lightbox coexistence with checkmark (CONTEXT #3, #4)

The image keeps its own `click` listener that opens the lightbox (line 245–247). The new checkmark is a separate `<button>` placed top-right corner of the card, absolute-positioned over the image. Because the image's listener is attached to the `<img>` element itself (not the parent card), a click on the button does NOT bubble through the image — the click never hits `<img>`. No `stopPropagation()` strictly needed, but defensively call `ev.stopPropagation()` in the checkmark handler in case future refactors move the listener to the card. The card itself has no click listener today; only the `<img>` and the existing star button do.

For touch overlap: position the checkmark inside the card but offset from the image edge by a small margin (CSS `top: 8px; right: 8px;`), with the button's visible size ~32×32px and a `padding` that makes the tap zone ≥44×44px. The image still occupies most of the card, so accidental zooms when reaching the checkmark are unlikely as long as the checkmark sits at the corner.

Lightbox close paths that must keep working: click on `lightbox` background (628–630), click on `lightImg` (628–630), `#exp-lightbox-close` button (632), `Escape` keydown (633–635). None of these reference rank/direct state — fully orthogonal.

## 5. Astro 5 client-side script + SortableJS conventions

- This repo uses inline `<script is:inline>` blocks (line 177 in `[id].astro`, line 55 in `templates/[...id].astro`). No external JS modules are imported anywhere in `site/src/`. `astro:content` is used for content collections in frontmatter; that is Astro-internal.
- There is no existing precedent for importing an npm JS library client-side. **SortableJS will be the first.** Two acceptable patterns:
  1. **Recommended:** drop `is:inline`, use a regular `<script>` block with `import Sortable from 'sortablejs';` at the top. Astro will bundle it. The script keeps its IIFE pattern; just remove `is:inline`. This requires `sortablejs` in `site/package.json` dependencies.
  2. **Alternative:** keep `is:inline` and load Sortable from a CDN via a `<script src="https://cdn.jsdelivr.net/.../Sortable.min.js">` tag. CONTEXT #8 says "Add to `site/package.json`" — option 1 is the right call.
- `site/package.json` (line 1–16): currently lists only `astro: ^5.0.0`. Add `sortablejs: "^1.15.7"` (latest stable verified via `npm view sortablejs version` → `1.15.7`). SortableJS has zero peer dependencies and zero runtime deps.

<interfaces>
// From npm sortablejs@1.15.7
import Sortable from 'sortablejs';
new Sortable(el: HTMLElement, options: {
  animation?: number;          // ms
  handle?: string;             // CSS selector for drag handle
  ghostClass?: string;
  chosenClass?: string;
  dragClass?: string;
  onEnd?: (evt: { oldIndex: number, newIndex: number, item: HTMLElement }) => void;
  onUpdate?: (evt: { oldIndex: number, newIndex: number, item: HTMLElement }) => void;
}): Sortable;
// methods: .destroy(), .option(name, value?), .toArray(): string[]
</interfaces>

## 6. `experiments/_schema/results.schema.yaml` (159 lines)

Current shape (lines 30–158): top-level required = `experiment_id, rater, session_start, session_end, votes, direct_picks, wins_ratio_appeal, wins_ratio_transport, ranking_appeal, ranking_transport, disagreement_index, spearman_appeal_transport`. `additionalProperties: false`.

`votes[]` (lines 48–88): each = `{ pair: {a, b}, axis: enum[appeal,transport], winner: string|null, position_a_on_screen: enum[left,right], timestamp }`.

Per CONTEXT #9, this schema is REWRITTEN to drop the entire pairwise shape. New schema covers `mode: "rank"` (with `ranking: string[]`) and `mode: "direct-pick"` (with `selections: string[]`). Plus `experiment_id`, `rater`, `started_at`, `exported_at`. Use `oneOf` on `mode` to switch between `ranking` and `selections`. Example file at `experiments/_schema/results.example.json` (current contents at lines 1–58 of that file) must be rewritten.

## 7. `tools/experiment_results.py` (467 lines)

Structure:
- `_load_schema`, `validate_results` (lines 43–52) — keep, retarget at new schema.
- `_is_skip` (59–60) — **delete** (no skip semantics in rank).
- `wins_ratio` (63–82) — **delete or replace** with `position_score(ranking, total)`.
- `ranking` (85–91) — **delete** (rank export already carries order).
- `disagreement_index` (94–127) — **delete** (single-axis).
- `spearman_correlation` (130–146) — **delete** (single-axis).
- `aggregate` (153–207) — **rewrite** to read mode-shaped JSON. Concatenation semantics for multi-file: rank mode = stitch by rater session, direct-pick mode = union selections. Returns aggregate object exposing per-variant `position_score: float | null` plus `top_3`, `bottom_3`.
- `_halo_flag`, `_ratio_line`, `render_summary` (214–377) — **rewrite.** Keep section structure: header, "Variants dropped during render" (255–270, preserves `_dropped` rendering — needs to stay verbatim), "Corpus update stub" with the two pre-labeled subsections (273–296, **keep verbatim**), top-3 / bottom-3 (re-shape from "by appeal"/"by transport" to a single combined ranking), "Per-pair disagreement" (319–331 — **delete**), "Suggested corpus entries" with winners/losers (334–371 — re-shape to single axis).
- `_load_hypotheses`, `_load_dropped` (384–409) — **keep.**
- `main` (412–462) — **keep skeleton**; update the printed summary line to reference position_score / top-3 instead of disagreement+spearman.

Backward-compat fallback for `direct-pick` (CONTEXT #11): `position_score = 1.0` for every selected variant, `null` for unselected. Top-3 by selection count — same dict-of-sets aggregation.

Tests at `tools/sla_lib/tests/test_experiment_results.py` (308 lines):
- `WinsRatioTest` (52–110) — **delete entire class.**
- `DisagreementTest` (113–156) — **delete.**
- `SpearmanTest` (159–188) — **delete.**
- `AggregateAndSummaryTest` (191–254) — **rewrite** for new aggregate(); the "render_summary contains required sections" set must be updated to new section headers.
- `DroppedAndCorpusStubTest` (257–303) — **keep** (dropped + dual-section corpus stub assertions are mode-independent).
- Helper `_vote()` and `_payload()` (21–49) — **rewrite** as `_rank_payload()` / `_direct_payload()`.

Tests at `tools/sla_lib/tests/test_experiment_results_schema.py` (99 lines):
- `test_example_validates` (41–47) — keep, retargets the rewritten `results.example.json`.
- `test_rejects_missing_axis`, `test_rejects_unknown_axis_enum`, `test_rejects_unknown_position` (49–65) — **delete** (no axis, no position).
- `test_rejects_missing_required_top_level` (67–71) — keep, update field name (`disagreement_index` → e.g. `mode`).
- `test_rejects_disagreement_index_out_of_range`, `test_rejects_spearman_out_of_range` (73–83) — **delete.**
- `test_accepts_null_winner_for_skipped_pair` (85–89) — **delete.**
- `test_rejects_unknown_top_level_field` (91–95) — keep.
- New tests: mode=rank validates; mode=direct-pick validates; oneOf rejects ranking+selections together; ranking items are strings.

<interfaces>
// From tools/experiment_results.py (after rewrite)
def validate_results(payload: dict) -> list[ValidationError]
def position_score(ranking: list[str], slug: str) -> float | None    # (N-rank)/(N-1); None if not in list
def aggregate(results_files: list[Path]) -> dict
  # returns: {experiment_id, rater, started_at, exported_at, mode, ranking|selections, _scores: dict[slug, float|None], _top_3: list[str], _bottom_3: list[str]}
def render_summary(agg: dict, *, hypotheses=None, dropped=None) -> str
def _load_hypotheses(exp_id: str) -> dict[str, dict]   # unchanged
def _load_dropped(exp_id: str) -> list[dict]           # unchanged
</interfaces>

## 8. `.claude/skills/experiments/SKILL.md` (195 lines)

Four-verb dispatch table at lines 22–32. Sections in order: `## new` (54–72), `## generate` (76–90), `## render` (94–113), `## capture` (117–132). v1 lessons (135–154), corpus-update merge gate (158–167), pre-flight checks per verb (171–175), out-of-scope (181–194).

Versus-mode-specific text to update:
- Frontmatter `description` line 5: "pairwise voting" → change to "ranking-based voting" or similar.
- `## capture` step 2 (lines 121–128): mentions "Top-5 / Bottom-3 by appeal and by transport", "Spearman ρ(appeal, transport) and halo flag", "Per-pair disagreement table". **Rewrite** to "Top-3 / Bottom-3 by position score", remove Spearman+disagreement lines. The dual-section corpus stub (`### From v1` / `### From v2`) stays — corpus-merge-gate is mode-independent.
- v1 lessons line 146 ("Position bias. Voters favour the left-presented variant in an A/B pair.") and line 148 ("per-pair randomization in the Astro voting page") — rewrite or drop; no more A/B pairs.
- Out-of-scope line 192–193 ("Adaptive pair sampling (Glicko/Elo) and Bradley-Terry / Elo ranking") — keep or rephrase (still out of scope for ranked-list mode).

Direct-pick is not mentioned in SKILL.md today — it's described only on the voting page itself. **Add** a one-paragraph note on rank-mode as the primary UX (CONTEXT #1) and the new schema-bump breaking-change disclaimer (CONTEXT #9).

## 9. `site/package.json`

```json
{ "name": "gruene-vorlagen-galerie", "version": "0.1.0", "private": true, "type": "module",
  "scripts": { "dev": "astro dev", "build": "astro build", "preview": "astro preview", "check": "astro check" },
  "dependencies": { "astro": "^5.0.0" } }
```

Add: `"sortablejs": "^1.15.7"` (verified latest via `npm view sortablejs version` on 2026-05-11). Zero peer deps, zero runtime deps. CONTEXT #8 says "pinned" — use `1.15.7` exactly (no caret) if literal-pinning is desired; team style elsewhere uses `^5.0.0` carets, so `^1.15.7` follows that convention. Planner picks.

## 10. Brand color tokens

From `shared/ci.yml:30–37` (CMYK source of truth):
- `Dunkelgrün`: CMYK `[85, 35, 95, 10]`, role `brand-primary`.
- `Hellgrün`: CMYK `[69, 0, 100, 0]`, role `brand-secondary`.

Web hex equivalents from `site/src/layouts/Base.astro:12–17` (CSS variables):
- `--gruen-dunkel: #2a734f;`
- `--gruen-hell: #6abf2c;`
- `--gelb: #ffeb00;`
- `--magenta: #e6177e;`

The site uses CSS custom properties already. **Use `var(--gruen-hell)` for the filled checkmark** (vibrant, "yes I picked this" affordance); position-number badge in `var(--gruen-dunkel)` for contrast against the green. Outlined (unselected) checkmark: stroke `var(--gruen-dunkel)` on a white/semi-transparent circle for visibility over arbitrary image content.

## 11. CSS conventions

- Global stylesheet via `<style is:global>` in `site/src/layouts/Base.astro:10–38`. Defines the four brand vars and base typography. **All pages can reference `var(--gruen-*)`.**
- Page-level styles in `experiments/[id].astro` are inline on every element (no `<style>` block on that page). `templates/[...id].astro` follows the same inline-on-element pattern (lines 35–38, 50–52).
- No scoped `<style>` blocks anywhere in `site/src/pages/`. No external CSS files referenced.
- For the new rank UI, two acceptable patterns:
  1. **Recommended:** add a single `<style>` block (not `is:global`) to the experiments page for the checkmark, badge, and ranked-list rows. Astro auto-scopes it. Inline-style precedent gets unwieldy for hover/focus/active pseudo-classes and `@media` queries (which the mobile responsiveness requires).
  2. Continue inlining and emit pseudo-class CSS via a `<style is:global>` block.
- Either way, the rank list rows ARE generated by JS (the inline IIFE), so the styles must be reachable from raw class names — `<style scoped>` works with classes added by JS as long as Astro emits the scoped class attribute matching. Use a `<style is:global>` block to avoid that subtlety, or use only inline `style="..."` strings in the JS builders. The existing direct-pick `renderDirect()` uses inline `style.cssText` per element (lines 238, 244, 251, 257); follow that pattern for consistency.

## 12. Touch target / accessibility precedent

- Lightbox close `#exp-lightbox-close` (line 164–165): `padding: 0.5rem 1rem`, font-size `1rem`. At default 16px root, that's ~32×24px content + 8×16px padding → ~48×40px visible. Width ≥44, height marginal. Likely passes WCAG ≥44×44 on common UAs.
- Direct-pick star `<button>` (line 252–257): no padding, font-size `1.4em` → ~22×22px tap area. **Fails WCAG ≥44×44.** The replacement checkmark is held to a stricter standard by CONTEXT #5.
- ARIA: only `star.setAttribute('aria-label', ...)` (line 256) and `aria-label` on the templates page lightbox link (`templates/[...id].astro:36`). The `#exp-lightbox-close` lacks an `aria-label` here (the templates version has one). **New rank UI should add `aria-label` on checkmark, arrows (▲/▼), drag-handle, and X-remove.** `aria-pressed` (toggle state) on the checkmark button is appropriate.
- Keyboard: tab order today flows naturally through buttons and inputs. The keyboard listener at lines 479–504 short-circuits on `INPUT` focus (line 480), but should similarly skip when arrow buttons inside the ranked list are focused (no global Up/Down hijacking). Drag-handle should be focusable and operable via Space/Enter (SortableJS doesn't ship keyboard reorder; arrows-button is the accessibility path per CONTEXT #7).

## Surgical change map (for the planner)

| File | Lines | Action |
|------|-------|--------|
| `site/src/pages/experiments/[id].astro` | 79–81 | Replace `#exp-mode-versus` button with `#exp-mode-rank`; reorder so rank is first |
| `site/src/pages/experiments/[id].astro` | 88–96 | Delete versus-mode shortcut `<details>` |
| `site/src/pages/experiments/[id].astro` | 98–104 | Keep direct-pick section; restyle star button later per discretion |
| `site/src/pages/experiments/[id].astro` | 106–160 | Delete versus section entirely; insert new rank section (grid + ranked-list panel) |
| `site/src/pages/experiments/[id].astro` | 162–169 | Keep lightbox markup verbatim |
| `site/src/pages/experiments/[id].astro` | 177 | Drop `is:inline` (or keep + use CDN); if using npm Sortable, switch to bundled `<script>` with `import Sortable from 'sortablejs'` |
| `site/src/pages/experiments/[id].astro` | 185 | Bump STORAGE_KEY to `experiment:<expId>:session:v2:<mode>` |
| `site/src/pages/experiments/[id].astro` | 213–218 | Replace session shape; gate by mode |
| `site/src/pages/experiments/[id].astro` | 230–295 | `renderDirect()` — keep; add 44×44 hit-zone restyle on star (planner discretion) |
| `site/src/pages/experiments/[id].astro` | 297–449 | Delete versus block; insert `renderRank()` builder + ranked-list builder + SortableJS init |
| `site/src/pages/experiments/[id].astro` | 462–476 | `setMode()` — accept `direct` \| `rank`; remove `versus` |
| `site/src/pages/experiments/[id].astro` | 479–504 | Keyboard handler — keep `E`, delete Q/W/O/P/Space |
| `site/src/pages/experiments/[id].astro` | 506–569 | Delete winsRatio/ranking/disagreement/spearman |
| `site/src/pages/experiments/[id].astro` | 571–606 | `doExport()` — rewrite to new shape + filename |
| `site/src/pages/experiments/[id].astro` | 609–635 | Keep lightbox handlers verbatim |
| `site/src/pages/experiments/[id].astro` | 638–640 | Boot — default `setMode('rank')` when `VARIANTS.length >= 3`, else `'direct'` |
| `site/package.json` | 12–14 | Add `"sortablejs": "^1.15.7"` to dependencies |
| `experiments/_schema/results.schema.yaml` | 1–159 | Rewrite entire file for the two-mode shape (oneOf on `mode`) |
| `experiments/_schema/results.example.json` | 1–58 | Rewrite as a rank example |
| `tools/experiment_results.py` | 39–146 | Delete wins_ratio, ranking, disagreement, spearman, _is_skip |
| `tools/experiment_results.py` | 153–207 | Rewrite `aggregate()` |
| `tools/experiment_results.py` | 214–377 | Rewrite `render_summary()`; preserve `## Variants dropped during render` (255–270) and `## Corpus update stub` (273–296) blocks |
| `tools/experiment_results.py` | 384–409 | Keep `_load_hypotheses`, `_load_dropped` |
| `tools/experiment_results.py` | 455–461 | Update final `print(...)` line |
| `tools/sla_lib/tests/test_experiment_results.py` | 21–188 | Replace WinsRatio/Disagreement/Spearman tests with position_score + aggregate tests |
| `tools/sla_lib/tests/test_experiment_results.py` | 191–254 | Rewrite AggregateAndSummary for new shape |
| `tools/sla_lib/tests/test_experiment_results.py` | 257–303 | Keep DroppedAndCorpusStubTest |
| `tools/sla_lib/tests/test_experiment_results_schema.py` | 49–89 | Delete axis/position/spearman/disagreement rejection tests; add mode/ranking/selections tests |
| `.claude/skills/experiments/SKILL.md` | 5 | Adjust frontmatter `description` to drop "pairwise" |
| `.claude/skills/experiments/SKILL.md` | 121–128 | Rewrite `## capture` step 2 for position-score top-3/bottom-3 |
| `.claude/skills/experiments/SKILL.md` | 146–148 | Drop/rephrase position-bias bullet (no more A/B pairs) |
| `.claude/skills/experiments/SKILL.md` | (new) | Add rank-mode-primary-UX note + breaking-change schema disclaimer |

No changes needed to: `site/src/layouts/Base.astro`, `site/src/pages/templates/[...id].astro`, `site/src/pages/experiments/index.astro`, the experiment manifest/constraint schemas, `tools/experiment_envelope.py`, `tools/experiment_render.py`, or any of the bin scripts.
