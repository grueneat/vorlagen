# Pitfalls Research — Issue #31 (Click-to-Rank Voting UI)

**Date:** 2026-05-11
**Researcher:** Pitfalls specialist
**Mode:** Read-only

---

## 1. Image-click vs checkmark-click event collision

**Risk:** The image already opens the lightbox on click (shipped in #28 — see `site/src/pages/experiments/[id].astro:451-456`). The new checkmark control is overlaid on the image. Two failure modes:
- (a) **Bubble-through:** Tapping the checkmark also opens the lightbox because the click event bubbles to the image container.
- (b) **Mis-tap:** On mobile, the user reaches for the checkmark but hits the image hit-area → lightbox opens instead of selection.

**Mitigation:**
- The checkmark handler MUST call `event.stopPropagation()` (NOT `preventDefault`) before mutating selection state. Then return.
- The checkmark must sit on top in z-index AND have a 44×44px tap zone (CONTEXT decision #5) physically separated from the image area by ≥4px padding on the inner edge.
- Add `pointer-events: none` on the position-badge sub-element so only the checkmark's actual <button> receives the click.

**Confidence:** HIGH (well-known DOM event pattern; the existing `[id].astro` already uses `addEventListener('click', …)` directly on the image).

---

## 2. `stopPropagation` vs `preventDefault` confusion

**Risk:** Naive fix uses `preventDefault()` — which does nothing for click-bubbling because click has no default action to cancel on a <button>. The lightbox still opens.

**Mitigation:** Use `event.stopPropagation()` on the checkmark click handler. `preventDefault()` is reserved for cases where the element has a default action (form submit, anchor navigation). Document explicitly in the task instructions and add a code comment.

**Confidence:** HIGH.

---

## 3. SortableJS handle overlap with arrow buttons + X button

**Risk:** The ranked-list row contains drag-handle, ▲, ▼, thumbnail, title, X. SortableJS by default makes the entire row draggable, so a tap on ▲ or X may start a drag instead of firing a click. The click event then never fires (or fires after drag-cancel, unreliably).

**Mitigation:** Configure SortableJS with both:
- `handle: '.drag-handle'` — scope drag initiation to the dedicated handle element only.
- `filter: '.arrow-up, .arrow-down, .remove-btn'` + `preventOnFilter: false` — exclude these explicit interactive elements as a belt-and-suspenders defense if a click registers near the handle.

Reference: SortableJS docs explicitly support `handle` + `filter` together. See [SortableJS GitHub](https://github.com/SortableJS/Sortable) and [issue #1621 — handle scoping](https://github.com/SortableJS/Sortable/issues/1621).

**Confidence:** HIGH.

---

## 4. Touch vs scroll disambiguation on mobile

**Risk:** When SortableJS is bound to ranked-list rows AND the page is scrollable, a touch-drag on a row is ambiguous: drag the row or scroll the page? Native default favours scroll, which breaks drag-to-reorder. The inverse is also bad (locking the handle to drag breaks scrolling near it).

**Mitigation:**
- `touch-action: none` CSS on the `.drag-handle` element ONLY (not the row). This tells the browser "this element is gesture-handled by JS." Everywhere else, vertical scroll continues to work.
- SortableJS's `delay: 150` + `delayOnTouchOnly: true` so a quick tap on the handle is treated as a click (not a drag-start).

**Confidence:** HIGH.

---

## 5. localStorage v1 → v2 silent data loss

**Risk:** CONTEXT decision #14 says bump keys from `:v1:` to `:v2:` with no migration. Users with an in-progress vote at deploy time see their selections vanish on next load.

**Mitigation:** On first load of the new page, scan `localStorage` for keys matching `experiment:*:session:v1:*`. If any found:
- `console.log('[exp] migrated from v1 keys; session reset')`
- Delete the v1 keys (CONTEXT decision is explicit — no migration of data, just clean up).
- Optional UI banner: "Voting was upgraded — please re-select your variants." Discretion area per CONTEXT; recommend the banner because silent data loss without feedback is a poor UX.

**Confidence:** HIGH.

---

## 6. Direct-pick / rank schema oneOf trap

**Risk:** Schema accepts both `mode: "rank"` with `ranking` and `mode: "direct-pick"` with `selections`. If both fields are exported (e.g., user toggled modes; export serialised the wrong state), the aggregator may silently pick the wrong one. Loose schemas (anyOf, additionalProperties: true) won't reject.

**Mitigation:** Use a proper JSON-Schema `oneOf` with `mode.const` discriminator:
```yaml
oneOf:
  - properties: { mode: { const: rank }, ranking: { type: array } }
    required: [mode, ranking]
    not: { required: [selections] }
  - properties: { mode: { const: direct-pick }, selections: { type: array } }
    required: [mode, selections]
    not: { required: [ranking] }
```
The aggregator `tools/experiment_results.py` validates against schema BEFORE reading fields. Reject files with both `ranking` AND `selections`.

**Confidence:** HIGH.

---

## 7. SortableJS bundle size + CLS

**Risk:**
- SortableJS is ~12KB gzipped (current npm version: **1.15.7**). Verified `npm view sortablejs version` returns `1.15.7`. Bundle impact is acceptable but should be confirmed in Astro build output.
- Cumulative Layout Shift: when ranked-list rows are inserted/removed without fixed height, the variant grid jumps up/down. Annoying on mobile especially.

**Mitigation:**
- Pin to `sortablejs@1.15.7` in `site/package.json`.
- Astro will tree-shake & bundle into the page JS. Spot-check `astro build` output size after install — log the page-JS size in the implement step.
- Define stable `min-height` on `.ranked-list-row` (suggest 64px to fit 48×48 thumbnail + padding).

**Confidence:** HIGH (version verified live).

---

## 8. Accessibility regression

**Risk:** Each list row has up to 6 controls (drag, ▲, ▼, thumbnail-link, title, X). Screen-reader users will hear all 6 per item — extremely verbose for a 10+ item ranked list.

**Mitigation:**
- Hide the visual drag-handle from screen readers: `aria-hidden="true"`. Arrows ▲/▼ serve the same purpose accessibly.
- Each ▲/▼/X has `aria-label="Move up: <title>"`, `"Move down: <title>"`, `"Remove <title> from ranking"`.
- Wrap list in `<ol role="list">` with `role="listitem"` per row. Position number is implicit from `<ol>` semantics — don't double-announce.
- Checkmark button on cards: `aria-pressed="true/false"` reflecting selected state; `aria-label="Select <title> for ranking"`.

**Confidence:** HIGH (standard WCAG patterns).

---

## 9. Mobile viewport: ranked list pushes variants off-screen

**Risk:** With 10+ ranked items below a 21-variant grid on a 360px-wide phone, the ranked list grows tall and the user constantly scrolls up to grid → down to list → up again. Tedious.

**Mitigation options** (CONTEXT marked this as discretion — recommend one):
- **Sticky export button** at bottom (24px bottom margin) so it's always reachable.
- **Collapsible ranked list** with header "Your ranking (N)" — tap to expand/collapse on mobile.
- Recommend BOTH: sticky export bar + collapsible list. Lowest risk to overall UX, highest payoff.

**Confidence:** MEDIUM (UX judgement call; verify on real phone during T-implement).

---

## 10. Variant grid scroll position lost on list change

**Risk:** Every select/deselect mutates the DOM. If the implementation re-renders the entire page section, scroll position resets to top — user loses place in a 21-variant grid.

**Mitigation:**
- Do NOT re-render the variant grid on add/remove. Only update:
  - The affected variant card's checkmark state + position badge text.
  - The ranked-list `<ol>` element (append/remove the single affected row).
- Use targeted DOM mutations, not innerHTML wipes.
- Position-badge numbers on OTHER cards may need updating when the list reorders — update them in place via `textContent`, not by rebuilding.

**Confidence:** HIGH.

---

## 11. Export filename — special characters in rater name

**Risk:** Filename is `<rater>-<exp-id>-<mode>-<YYYY-MM-DD>.json`. If `rater` contains spaces, slashes, colons, or unicode, the browser may strip or sanitize unpredictably, OR the user (mobile Safari especially) gets a broken filename.

**Mitigation:** Sanitize `rater` and `exp-id` via regex: `replace(/[^a-z0-9_-]/gi, '-').toLowerCase()`. Trim leading/trailing dashes. Empty rater → fallback to `anonymous`. Match the pattern already documented in #29's pitfalls research per the issue body.

**Confidence:** HIGH.

---

## 12. Skill update — broken/dangling references

**Risk:** `.claude/skills/experiments/SKILL.md` (from #30) has versus-mode docs. Removing them must not leave dangling cross-references in other skill sections, rules files, or the top-level SKILL.md index.

**Mitigation:**
- Grep `.claude/skills/experiments/` for `versus|pairwise|tournament` before edit; address all hits.
- Re-read SKILL.md after edit to ensure flow still makes sense (no orphan sections, no "See versus mode below" pointing to deleted content).
- Update rules/*.md if they exist and reference versus.

**Confidence:** HIGH.

---

## 13. Aggregator test fixtures break

**Risk:** Old fixtures in `tools/` or `experiments/_schema/results.example.json` use the pairwise shape. Schema rewrite + aggregator rewrite invalidates them. Tests fail until fixtures are updated.

**Mitigation:**
- Rewrite `experiments/_schema/results.example.json` to the new rank shape.
- Any `tools/experiment_results.py` tests (pytest or doctest) update to new fixtures.
- Add a fresh fixture for `mode: "direct-pick"` so backward-compat path is covered.
- Planner: include "update fixtures and test files" as an explicit task.

**Confidence:** HIGH (results.example.json confirmed present).

---

## 14. Production page byte-stability

**Risk:** This issue only touches `site/`, `experiments/`, `tools/`, `.claude/skills/`. No template builds touched. But — if anything in the Astro build inadvertently rebundles or re-emits production template pages, we risk silent byte changes.

**Mitigation:**
- Before merge: SHA256 spot-check on the production falzflyer-p2, zeitung, plakat PNGs from the gallery against pre-change SHA256.
- The Astro build output for `/experiments/[id]/` will change (expected) — only template-asset PNG/PDF stability matters.

**Confidence:** HIGH.

---

## 15. Environment audit (verified 2026-05-11)

| Item | Status | Notes |
|------|--------|-------|
| Node.js | v26.0.0 available | Far above SortableJS / Astro needs |
| Astro | `^5.0.0` in site/package.json | Active. (Issue body mentions 5.18.1 — minor; major still 5) |
| SortableJS npm | **1.15.7** latest | `npm view sortablejs version` → 1.15.7 |
| Bundle size | ~12KB gzipped | Acceptable for a single page |
| site/package.json | Read | Only `astro` listed; SortableJS will be the second dep |
| experiments page | Exists at `site/src/pages/experiments/[id].astro` | Lightbox at lines 163-635 confirmed |
| Schema dir | `experiments/_schema/` | `results.schema.yaml` + `results.example.json` present |
| Aggregator | `tools/experiment_results.py` | Present |
| Skill | `.claude/skills/experiments/SKILL.md` | Existence assumed from CONTEXT; verify before edit |

**Verdict:** Environment ready. No proxy/registry blockers. SortableJS pin recommended: `"sortablejs": "1.15.7"` (exact, not caret — voting UX is too sensitive to silent minor bumps).

---

## Top 5 Pitfalls (Prioritized by Severity × Likelihood)

1. **Image-click vs checkmark-click collision (#1, #2)** — Highest blast radius. Without `stopPropagation`, every selection click also opens the lightbox. Must be specified in the task instructions verbatim. **CRITICAL.**

2. **SortableJS handle/cancel misconfig (#3)** — If the row is broadly draggable, ▲ ▼ X clicks become drag-starts. Reorder UX breaks. Mitigation is one line of config but must be explicit. **HIGH.**

3. **Schema oneOf discriminator (#6)** — Loose schema causes aggregator to silently miscount. Data corruption is invisible until corpus is wrong. **HIGH.**

4. **localStorage v1→v2 silent loss (#5)** — Real users may have in-progress votes. Communicate via console.log + optional UI banner. **MEDIUM-HIGH** (low blast radius but user-facing).

5. **Mobile touch-action / scroll disambiguation (#4)** — Without `touch-action: none` on the handle, mobile drag never starts reliably. Mobile is the primary use case. **HIGH.**

---

## Sources

- [SortableJS official site](https://sortablejs.github.io/Sortable/) — HIGH confidence
- [SortableJS GitHub repo](https://github.com/SortableJS/Sortable) — HIGH (handle, filter, delay options)
- [SortableJS issue #1621 — handle scoping](https://github.com/SortableJS/Sortable/issues/1621) — MEDIUM
- [sortablejs npm](https://www.npmjs.com/package/sortablejs) — HIGH (version 1.15.7 verified live)
- Codebase: `site/src/pages/experiments/[id].astro:163-635` (lightbox + click handler patterns) — HIGH
- Codebase: `site/package.json` (Astro ^5.0.0, no other deps) — HIGH
- CONTEXT.md decisions #5, #8, #14, #15 — locked
- WCAG 2.1 SC 2.5.5 (Target Size 44×44px) — HIGH
