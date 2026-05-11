# Ecosystem Research — Issue #31 (rank voting UI)

**Date:** 2026-05-11
**Scope:** New dep is SortableJS only. Existing stack (Astro 5, Python `jsonschema` 4.26.0, Tailwind) unchanged from #29/#30.

## Standard Stack (delta only)

| Library | Version | Purpose | Registry | License | Confidence |
|---------|---------|---------|----------|---------|------------|
| `sortablejs` | **1.15.7** (latest, published 2024-12; npm `latest` tag confirmed 2026-02-11) | Touch-capable drag-to-reorder for the ranked list | npm | MIT | HIGH |

- `main`: `./Sortable.min.js` (UMD)
- `module`: `modular/sortable.esm.js` (ESM — Vite/Astro will pick this)
- Zero runtime deps. ~13 kB min+gzip (well-known figure; bundlephobia 403'd; community reports consistent).
- Pin exact (`"sortablejs": "1.15.7"`), since CONTEXT decision #8 says "Latest stable, pinned."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Touch drag reorder | Custom `pointermove`/HTML5 DnD shim | SortableJS | HTML5 DnD has zero iOS Safari support; SortableJS is the de-facto standard. |
| ARIA live announcements | Custom timer-based queue | A single `aria-live="polite"` div with text swap | Native and well-supported (see WAI-ARIA APG). |
| Discriminated-union validation | Manual if/else | `oneOf` with `properties.mode.const` | Native JSON Schema 2020-12 pattern, supported by `jsonschema` 4.26.0. |
| Borda-style scoring | New formula | `(N-rank)/(N-1)` normalised linear Borda | Already locked in CONTEXT; standard rank-aggregation form. |

## 1. SortableJS in Astro 5

**Integration pattern (HIGH).** Astro 5 + Vite picks ESM via `module` field automatically. Use a **client-side `<script>` inside the `.astro` file** (NOT frontmatter — frontmatter runs at build time on Node where `document` is undefined):

```astro
<script>
  import Sortable from 'sortablejs';
  const list = document.getElementById('ranked-list');
  if (list) {
    new Sortable(list, {
      handle: '.drag-handle',
      animation: 150,
      delayOnTouchOnly: true,
      delay: 150,
      touchStartThreshold: 5,
      ghostClass: 'sortable-ghost',
      onEnd: (evt) => { /* sync state to localStorage */ },
    });
  }
</script>
```

Astro processes `<script>` blocks through Vite, so the `import` resolves and SortableJS is bundled into the page bundle (single small chunk; acceptable for static deploy — no extra HTTP request beyond the existing page bundle). Confidence HIGH per Astro Imports reference docs.

**SSR safety (HIGH):** SortableJS references `document` at construction time, never at import. Importing inside a client `<script>` is safe; do not call `new Sortable()` from frontmatter.

**Must-have options (HIGH, from official README):**
- `handle: '.drag-handle'` — recommended for our row (X / arrows / handle coexist; whole-row drag would conflict with the X click target).
- `animation: 150` — smooths reorder.
- `onEnd(evt)` — fires after drop; `evt.oldIndex` / `evt.newIndex` for state sync.
- `delayOnTouchOnly: true` with `delay: 150` + `touchStartThreshold: 5` — disambiguate scroll vs drag on touch (LOW–MEDIUM tuning; verify on device).
- `ghostClass: 'sortable-ghost'` — style the placeholder.

**Keyboard accessibility (HIGH):** SortableJS has **no built-in keyboard support.** Open issue #1951 ("status on making SortableJs accessible?") still open. CONTEXT decision #7 already mandates arrow buttons as the accessible path — this is the correct and required fallback.

## 2. Arrow-button reorder UX (Tab + Enter)

**Layout pattern (MEDIUM, multiple sources):** handle on the **left**, content in the middle, controls (▲ ▼ X) on the **right**. Matches Material List and iOS reorder convention.

**Live-region announcement (HIGH, WAI-ARIA APG + React Aria):**
- One hidden `<div aria-live="polite" role="status" class="sr-only">` near the list.
- On ▲/▼ press: update text to `"Moved 'Variant title' from position 3 to position 2 of 5."`.
- Use `polite`, never `assertive` (assertive interrupts other speech; over-noisy in repeated reorder).
- Clear/reset after a delay so consecutive moves re-announce reliably.

Arrows should be `<button type="button">`, disabled at boundaries (top item: ▲ disabled; bottom: ▼ disabled). `aria-label="Move 'Title' up"`.

## 3. Touch target sizing

| Standard | Min size | Source |
|----------|----------|--------|
| WCAG 2.2 AA SC 2.5.8 | **24×24 CSS px** (with spacing exception); **44×44 recommended** | W3C |
| WCAG 2.1/2.2 AAA SC 2.5.5 | 44×44 CSS px | W3C |
| Apple HIG | 44×44 pt | Apple |
| Material Design | 48×48 dp | Google |

**Effective floor for our project: 44×44 px** (already locked by CONTEXT #5/#13; matches Apple HIG and WCAG AAA).

**Pattern for visually-smaller checkmark with 44×44 hit zone (HIGH):**

```html
<button type="button" aria-label="Toggle selection"
        class="absolute top-2 right-2 w-11 h-11 flex items-center justify-center
               touch-manipulation"
        onclick="event.stopPropagation(); toggle(slug);">
  <span aria-hidden="true" class="w-8 h-8 rounded-full bg-white/90 ...">✓</span>
</button>
```

Key rules:
- Outer `<button>` is the hit zone (44×44 = `w-11 h-11` in Tailwind).
- Inner `<span>` is the visible 32–36 px circle.
- `event.stopPropagation()` on click prevents the image's lightbox handler from firing (image click is on a sibling/parent — see below).
- `touch-action: manipulation` removes 300 ms tap delay and disables double-tap zoom on the button.

**Preventing lightbox conflict (HIGH):**
1. Button is positioned **absolute** over the image. The image click handler is on the `<img>` (or wrapping `<a>`), not the parent card.
2. Button has higher stacking context (`z-10`) — pointer events land on the button, not the image.
3. Defensive: `event.stopPropagation()` in the button handler so even if events bubble, the image handler isn't triggered.

## 4. JSON Schema oneOf for mode discriminator

**Pattern (HIGH, JSON Schema 2020-12 spec + Ajv docs):**

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
type: object
required: [experiment_id, rater, started_at, exported_at, mode]
properties:
  experiment_id: { type: string }
  rater:         { type: string }
  started_at:    { type: string, format: date-time }
  exported_at:  { type: string, format: date-time }
  mode:          { enum: [rank, direct-pick] }
oneOf:
  - properties:
      mode:    { const: rank }
      ranking: { type: array, items: { type: string }, uniqueItems: true }
    required: [mode, ranking]
  - properties:
      mode:       { const: direct-pick }
      selections: { type: array, items: { type: string }, uniqueItems: true }
    required: [mode, selections]
```

- `properties.mode.const` in each branch acts as the discriminator — exactly one branch validates.
- Python `jsonschema` 4.26.0 supports Draft 2020-12 natively (`Draft202012Validator`).
- Unit test: one passing fixture per branch + one failing fixture (rank with no `ranking` field; direct-pick with `ranking` instead of `selections`).
- Do NOT use OpenAPI's `discriminator` keyword — non-standard outside OpenAPI; pure `oneOf`+`const` is the JSON-Schema-native form and `jsonschema` understands it.

## 5. Schema-version bump etiquette

For a small repo with YAML schemas and no public consumers, the pragmatic pattern:

1. Add a top-level `$comment` or `title` containing `"v2 — rank+direct-pick (replaces v1 pairwise)"`.
2. Bump the localStorage key namespace (already done — `:v2:` per CONTEXT #14).
3. Document the breaking change in `.claude/skills/experiments/SKILL.md` under a `## Schema history` H2 with date + reason + migration note ("no migration; no v1 results were ever committed").
4. Update fixtures and any committed result JSONs in lockstep with the schema commit (single PR atomicity).
5. No formal semver registry needed; the schema title + skill doc + git history are the canonical version surface.

Confidence: MEDIUM — this is best-practice convention rather than a single citable spec.

## 6. Position score formula

**`position_score = (N - rank) / (N - 1)` is a normalised linear Borda count** (HIGH, Wikipedia + Lumen Learning).

- Standard Borda: rank-1 → N-1 points, rank-N → 0.
- Normalised by dividing by `N-1`: rank-1 → 1.0, rank-N → 0.0. Identical to the raw Borda ordering; just rescaled.
- This is the same scheme used in **rank aggregation for information retrieval** (Borda as a rank-aggregation method — see arxiv "Top-k Selection from m-wise Partial Rankings via Borda").
- Defensible and standard. CONTEXT lock is correct.

**Alternatives (briefly, for completeness — NOT to be implemented per CONTEXT):**
- Inverse rank (`1/rank`): exaggerates top of list; less stable for cross-N comparison.
- Exponential decay (`e^-rank`): similar to inverse, more aggressive.
- Plurality (`1` if rank==1 else 0): loses signal below #1.

Normalised linear Borda is the right pick for a small ranked-list voting UX.

**Edge case — variants not in ranking:** `null` per CONTEXT is the correct sentinel (Borda treats unranked as "no information," NOT "lowest"). When aggregating across raters (phase 2), the standard approach is **mean of non-null scores per variant** with a separate "coverage" count so a variant ranked by only one rater isn't compared apples-to-apples with one ranked by all raters.

## 7. iOS Safari + Android Chrome gotchas

**Confirmed issues (HIGH, from SortableJS issue tracker):**

1. **iOS scroll vs drag (issue #1556, #1571):** iOS Safari requires the 500 ms delay for dragging to start without hijacking scroll. Use `delay: 150–250` with `delayOnTouchOnly: true` to keep responsiveness while allowing flick-scroll.
2. **iOS 17.4 `onFilter` regression (issue #2374):** Not relevant to us (we don't use `onFilter`), but worth knowing.
3. **`touch-action: none` is a footgun:** applying it to the container blocks scroll entirely on mobile. Apply ONLY to the drag handle (`.drag-handle { touch-action: none; }`), not to the row or container. Use `touch-action: manipulation` (not `none`) on the checkmark/arrow buttons to remove tap delay without blocking gestures.
4. **Android Chrome:** `delay` reportedly less reliable than iOS — test on a real device. Drag generally starts immediately on Android, which is the desired behaviour.
5. **No conflict with `<select>` / native pickers** on this page — we have no form controls.

**Long-press + browser context menu:** SortableJS's long-press drag does NOT trigger the iOS Safari context menu (link/image preview) when the handle is a non-image, non-link element. Use a `<button>` or `<div role="button">` for the handle.

## 8. Astro 5 + SortableJS bundling

- ESM entry resolves via `module: modular/sortable.esm.js`. Vite picks this automatically.
- Single client bundle per page; Astro will tree-shake unused exports. We import only the default — no plugins.
- Static-deploy compatible (GitHub Pages target). No SSR runtime; Astro is `output: 'static'` for this project.
- **SSR safety reaffirmed:** keep `import Sortable from 'sortablejs'` inside the client `<script>` block; never in frontmatter `---`. SortableJS uses `document` at construction (`new Sortable(el, opts)`), which is fine in browser-only context.

## 9. Selected-state checkmark + position badge

**Recommendation (MEDIUM, design-system precedents from Material, iOS, Tailwind UI):**

**Single combined element** — one filled circle that holds either a check glyph (when first selected) or the position number (after others are added). Pros: one visual focal point, simpler animation, fewer DOM nodes. Cons: glyph swap can be jarring.

**Alternative — two elements (check + small numeric badge):** check stays constant (binary affordance), number badge offset to bottom-right of check. Pros: number always visible; check is unambiguous. Cons: more visual noise.

**Recommended approach for this issue:** **Show the position number once selected** (no separate badge). Empty state = outlined circle; selected state = filled brand green circle with white **number** (1, 2, 3…). The check glyph is implied by the filled state; the number IS the affordance. Saves visual real estate on small thumbnails.

- Size: 32–36 px visible diameter, 44×44 hit zone.
- Filled colour: brand Hellgrün or Dunkelgrün (planner picks per existing palette).
- Position number font: bold, 14–16 px, white.
- Transition: 150 ms ease on background-color + transform: scale(1.05 → 1.0) for tactile feedback.

Precedents: iOS Photos multi-select uses a numbered blue circle with the same approach; Material Lists use leading-avatar selection state; Tailwind UI's "Avatars with status" component uses similar overlay positioning.

## Sources

### HIGH confidence
- npm registry: `npm view sortablejs` → version 1.15.7, main, module, license MIT, no runtime deps (verified 2026-05-11).
- SortableJS README & GitHub repo: https://github.com/SortableJS/Sortable
- SortableJS demos / live API: https://sortablejs.github.io/Sortable/
- Astro Imports reference: https://docs.astro.build/en/guides/imports/
- W3C WCAG 2.2 SC 2.5.8 Target Size (Minimum): https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- WAI-ARIA Authoring Practices, keyboard interface: https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/
- Borda count (Wikipedia): https://en.wikipedia.org/wiki/Borda_count
- Lumen Learning, Borda Count: https://courses.lumenlearning.com/waymakermath4libarts/chapter/borda-count/
- arxiv: Top-k Selection from m-wise Partial Rankings via Borda Counting: https://arxiv.org/pdf/2204.05742
- Ajv JSON Schema docs (oneOf / discriminator): https://ajv.js.org/json-schema.html
- SortableJS issues: #1556 (Android delay), #1571 (Safari 13 drag), #2374 (iOS 17.4 onFilter), #1951 (accessibility status), #2426 (mobile scrolling)

### MEDIUM confidence
- React Aria, accessible drag-and-drop blog: https://react-aria.adobe.com/blog/drag-and-drop
- Smashing Magazine, Dragon Drop accessible list reordering: https://www.smashingmagazine.com/2018/01/dragon-drop-accessible-list-reordering/
- GitHub Engineering, accessible sortable list challenges: https://github.blog/engineering/user-experience/exploring-the-challenges-in-creating-an-accessible-sortable-list-drag-and-drop/
- Primer (GitHub), drag-and-drop accessibility pattern: https://primer.style/accessibility/patterns/drag-and-drop/
- endjin, JSON Schema patterns — polymorphism with discriminators: https://endjin.com/blog/json-schema-patterns-dotnet-polymorphism-with-discriminator-properties
- Salesforce UX, 4 major patterns for accessible drag and drop: https://medium.com/salesforce-ux/4-major-patterns-for-accessible-drag-and-drop-1d43f64ebf09

### LOW confidence (worth validating during T-implement)
- SortableJS minified+gzipped size (~13 kB) — bundlephobia 403'd; estimate from community reports.
- Exact `delay` tuning (150 vs 250 vs 500 ms) for our row layout — verify on real iOS Safari + Android Chrome.
- Two-element vs single-element selected-state checkmark — visual designer call; both are defensible.
