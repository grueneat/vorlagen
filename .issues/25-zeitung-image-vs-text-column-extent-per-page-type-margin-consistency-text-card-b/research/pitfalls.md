# PITFALLS Research — Issue #25 Zeitung image-vs-text-column extent + per-page-type margin consistency + text-card border variation

**Researched:** 2026-05-09
**Specialist:** PITFALLS
**Confidence:** HIGH (codebase-grounded; same project I co-implemented in #22/#23/#24)

---

## Executive summary

#25 is the third successor in the Zeitung-alignment iteration chain (#22 → #23 → #24 → #25). It introduces three new BrandRules, a new `meta.yml` field (`body_block_margins`), and a fourth round of geometry edits. Most of the **plumbing risk is already de-risked** by #22/#23/#24 (rule structure, audit-tool wire-in pattern, `meta.yml::brand_overrides` pattern, `bin/render-gallery --skip-visual-diff` SHA bump, two-iteration Codex budget, `test_zeitung_geometry.py` invariant pinning style).

The **NEW pitfall surface** is concentrated in three places:

1. **Body-text-block detection heuristic** — distinguishing real body text from cover/caption/decorative text frames. Naive "cluster by left-x" produces false-positive block extents on cover, foto-spread, and cards-only pages.
2. **`body_block_margins` semantics + schema** — the new YAML field needs a JSON schema or it becomes silent typo bait. Per-page exceptions are required (cover ≠ body; foto-spread bypasses the block).
3. **`text_card_size_consistent` clustering** — the issue's grouping key `(fill, anname-pattern, contained-text-style)` is under-specified and vulnerable to multi-text-frame cards and shape-vs-stroke confusion.

Plus the **standard tail of #22/#23/#24 risks**: 7 non-Zeitung templates need pre-applied skip overrides; `_VisualAdjacencyDriftRule` interaction with each new rule; `bin/audit-alignment` wire-in; SCHEMA.md updates; SHA bump; `test_sla_to_dsl.py::ZeitungRoundTrip` allow-list re-tuning.

---

## 1. Body-text-block detection heuristic — HIGH risk

The new `brand:image_within_text_block` rule asserts `image.x ∈ [block_left, block_right]`. The block is **not declared** in build.py — it must be **inferred from text frames** at rule-evaluation time. This inference is the single biggest correctness risk in this issue.

### What goes wrong

Naive clustering by left-edge x-coordinate produces wrong block extents:

- **Page 1 (cover, `page0`)**: NO 3-column body grid. Has cover masthead text + Hero TextFrame `Eine Überschrift, die in einem Bild` (x=20, w=172.86) at y=78.21. Cover text-frame's outer extent = [20, 192.86]. P1 Hero is `(-3, 0, 210)` — extends 23mm past on left, 17mm past on right. If the rule fires here as ERROR, it conflicts with the design intent (full-bleed cover hero is intentional).
- **Page 4 / pages 12 (page11) / page 14 (page13)**: photo-spread + green-card + cards-only pages have text frames whose layouts differ structurally from the 3-column body grid. Naive clustering yields whatever frame happens to be there, not the body block.
- **Caption text frames**: small text frames overlaid on hero images (e.g., `Bildunterschrift weiß` style) often sit at non-body x-positions. They should NOT count.
- **Decorative text frames**: page 1 `Beitrag in weiß` headlines (x=20, w=170) on dark backgrounds. These are full-block-width by design; including them in the cluster is fine for body-block extent computation (they happen to span the block), but they're not "body text".

### How to avoid (recommended detection heuristic)

Filter text frames before clustering. Keep frames where ALL of:

- `width_mm > 30` AND `height_mm > 50` (excludes captions and small headlines)
- `x_mm ≥ -tol` AND `x_mm + w_mm ≤ page_w + tol` (excludes overflow / decorative)
- TextFrame is part of a `ColumnTextStory` group (Zeitung body grids are emitted via `ColumnTextStory(frames=[...], runs=[...])` — see build.py lines 486-532; this is a strong indicator of "body text"). If the rule can't access ColumnTextStory grouping, fallback to: "≥2 frames at distinct x with same w within 1mm" → that's a column grid.

After filter:
- Block left = min(filtered_frames.x_mm)
- Block right = max(filtered_frames.x_mm + filtered_frames.w_mm)
- If <2 filtered frames → no detectable block → **skip rule on this page** (don't false-positive). This is the cover/full-bleed escape.

### Warning signs
- Rule fires on page 1 cover with the recommended Hero geometry → heuristic is wrong (cover should be exempt by lack of detected block, not by override).
- Rule fires on a caption-only page (e.g., foto spread) → heuristic too loose.
- Rule misses an obviously-wrong image extent on pages 2/4/5/10/11 → heuristic too tight.

### Cross-reference with codebase
- `ColumnTextStory` is defined as a composite block: see `tools/sla_lib/builder/blocks/columntext.py` (similar to `SpreadImage` pattern). The block emits multiple TextFrames with shared `runs`. Detection: a TextFrame whose `anname` is one of a series like `Kopie von u2f23` / `Kopie von u2f23 (2)` / `Kopie von u2f23 (3)` (sequential naming in zeitung body) often indicates ColumnTextStory expansion. But this naming-based detection is brittle — recommend the geometric "≥2 frames at distinct x, same w" fallback.

---

## 2. `body_block_margins` field design + meta-schema — HIGH risk

### What goes wrong

The ISSUE.md proposes a new top-level field `body_block_margins` in `meta.yml`:

```yaml
body_block_margins:
  cover: {left_mm: 20, right_mm: 20, top_mm: 20, bottom_mm: 20}
  left:  {outer_mm: 20, inner_mm: 12, top_mm: 20, bottom_mm: 20}
  right: {outer_mm: 20, inner_mm: 12, top_mm: 20, bottom_mm: 20}
```

`tools/sla_lib/builder/meta_schema.py` currently validates ONLY `brand_overrides` and `sla_diff_strict` (lines 23-43). A new field added to meta.yml without a schema entry will:
- Silently accept typos (`body_block_margin` singular, `outer_m` etc.).
- Silently accept wrong types (string instead of number, missing required keys).
- Fail with a confusing error inside the BrandRule's check() instead of at meta.yml load time.

### How to avoid

- **Extend meta_schema.py** with a `_BODY_BLOCK_MARGINS_SCHEMA` and a `load_body_block_margins(slug)` loader function, mirroring `load_brand_overrides` shape. Surface errors at meta.yml load time with the path that's wrong.
- **Schema must be flexible**:
  - Cover: `left_mm`, `right_mm`, `top_mm`, `bottom_mm` (4 symmetric fields)
  - Left/right: `outer_mm`, `inner_mm`, `top_mm`, `bottom_mm` (4 spine-aware fields)
  - All fields required when the section is declared
  - Sections optional (a single-page template only needs `cover`)
- **`except_pages` per-page override** (per the user's flagged risk): the spec needs to support `(except_pages: [N, M])` for legitimate full-bleed-photo pages that bypass the block. Per ISSUE.md user note about cover being structurally different + "some pages with full-bleed photo backgrounds" — this exception MUST be supported.

Recommended schema shape:

```yaml
body_block_margins:
  cover: {left_mm: 20, right_mm: 20, top_mm: 20, bottom_mm: 20}
  left:  {outer_mm: 20, inner_mm: 20, top_mm: 49, bottom_mm: 22}
  right: {outer_mm: 20, inner_mm: 20, top_mm: 49, bottom_mm: 22}
  except_pages: [4, 5]   # foto-spread bypasses (1-indexed print page numbers)
```

### Warning signs
- A test on a synthetic doc passes but the real Zeitung load surfaces a TypeError inside the rule → schema validation missing.
- Adding `inner_mm: "20"` (string) doesn't surface as a meta.yml error → schema not validating types.

### Cross-reference
- See `meta_schema.py:46-72` for the `load_brand_overrides` pattern to mirror.
- `_validate_and_collect_ids` (`meta_schema.py:101-122`) shows the warning-on-unknown pattern; the new loader should warn on unknown sections.

---

## 3. Per-page-type margin spec — page-type detection edge cases — MEDIUM risk

### What goes wrong

The rule classifies pages by:
- `own_page == 0` → cover
- `master_name` matches `\blinks\b` → LEFT
- `master_name` matches `\brechts\b` → RIGHT

This is the SIDE_RX pattern from #22 (`brand_constraints.py:466`). Edge cases:

1. **Foto-spread master `foto-spread`** (Zeitung has this — see meta.yml masters list). Master name doesn't match links/rechts. Currently `_SpineSafetyRule` emits one warning per such page (`brand_constraints.py:521-535`). The new `document_margins_consistent` rule needs the same pattern: emit a warning rather than silently skipping, OR explicitly opt-out via the `except_pages` mechanism.
2. **Master `impressum-master`** (Zeitung last page). Doesn't match links/rechts. Same issue.
3. **Master `titelseite`** for cover. Cover-rule branch is by `own_page==0`, not master_name — works but not symmetric with the other two cases.
4. **Insert pages / panorama pages** (mentioned in the dispatcher). If a future template adds a 2-page panorama (a single image spanning a spread without a master like "links"/"rechts"), classification fails.
5. **Pages without a master** (rare but possible — `master_name == ""`). Same as case 1.

### How to avoid

Document the rule's scope explicitly:

> The rule applies only when `master_name` matches `\b(links|rechts)\b` OR `own_page == 0`. Pages with non-matching masters (foto-spread, impressum-master, etc.) emit ONE warning per such page so the bug surfaces but doesn't silently skip — mirroring `_SpineSafetyRule:521-535`. Templates with intentional non-standard masters add the page to `body_block_margins.except_pages` to opt out of the warning.

Three classification outcomes per page:
- **Classified** (cover/left/right) → check against spec.
- **Excepted** (`own_page in except_pages`) → silent skip.
- **Unclassified** (master not matching, not in except_pages) → ONE warning per page.

### Warning signs
- Foto-spread page (page 4 = `page3`) doesn't show up in audit output → rule silently skipped without warning.
- Impressum page surfaces as a margin violation → master not in scope, page should be in `except_pages`.

### Cross-reference
- Zeitung meta.yml masters: `Normal`, `rechts-3col`, `links-3col`, `titelseite`, `foto-spread`, `impressum-master` (lines 72-78).
- SIDE_RX pattern: `brand_constraints.py:466`.
- Cover detection precedent: `_SpineSafetyRule:519-520` (`own_page == 0`).

---

## 4. `text_card_size_consistent` clustering — HIGH risk

### What goes wrong

ISSUE.md says: "hash polygons by `(fill, anname-pattern, contained-text-style)`, group, then assert size within group." Multiple under-specified pieces:

1. **"contained-text-style"** — what is it? The first text frame's `trail_style`? A polygon may contain MULTIPLE text frames (e.g., page 7 `u918` Dunkelgrün card contains `Headline in grünem Kasten` AND `Fließtext in grünem Kasten` AND a portrait — 3 children). Picking "first" is arbitrary; picking "any" produces non-deterministic groupings.
2. **"anname-pattern"** — Zeitung polygons have annames like `u918`, `u2950`, `Kopie von u1529`, plus unnamed polygons (empty `anname`). Should the pattern strip "Kopie von " prefix? Strip suffix `(N)` enumerator? "anname-pattern" is undefined.
3. **Polygons with NO contained text** — some Dunkelgrün polygons are pure background bands (e.g., the unnamed `page12` Dunkelgrün at x=3, w=210 with NO text inside). They're not "cards" in the green-bordered-card sense. Skip these.
4. **Polygons that contain text spilling beyond their bbox** — caption-on-photo pattern from `meta.yml::brand_overrides[brand:image_text_overlap]` reason. The contained-text relationship may not be strict containment.
5. **Inconsistent `line_width_pt`** — the user flagged "borders inconsistent widths." Does the rule check `line_width_pt` separately from `(w, h)`? ISSUE.md says only `(w, h)` within 1mm. But the user's actual complaint may be border THICKNESS variation, not size variation.
6. **Single-instance groups** — if a polygon appears once across all pages, no comparison possible. Skip cleanly (don't false-positive a group-of-one).

### How to avoid

Recommend the planner pick a more deterministic key:

- **Group key**: `(fill_color, line_color, line_width_pt_rounded_to_0.1, has_contained_text_yes_no)`. Drop "contained-text-style" — it's unstable. Use coarser bucket of "is-this-a-card-vs-pure-background-band" via has-contained-text boolean.
- **Per-group assertion**: `(w_mm, h_mm)` within `tolerance_mm` (default 1.0) of the group's MEDIAN. Median is robust to one outlier; mean drifts.
- **Skip group if size < 2** (single-instance, nothing to compare).
- **Containment detection**: a polygon "contains text" if at least one TextFrame's bbox is ≥80% inside the polygon's bbox (matches `brand_constraints.py:781-786` `txt_inside` heuristic in `_ImageTextOverlapRule`).
- **Add `line_width_pt` to the assertion**: per the user's "border widths differ" note, also assert `line_width_pt` within 0.1pt of group median. Otherwise the rule misses the actual user-flagged bug class.

### Warning signs
- Rule reports a violation on `u918` (page 8 portrait card) compared to `u29c1` etc. (page 12-14 cards) — different design intent (portrait inset vs body card). If groups are misjoined, rule will false-positive.
- Rule misses page 12-14 border-width variation — the actual user complaint.

### Cross-reference
- See `_ImageTextOverlapRule:712-714` for the `FILLED_POLYGON_FILLS = ("Dunkelgrün", "Hellgrün", "Magenta", "Gelb")` precedent for "what is a colored polygon."
- See `brand_constraints.py:781-786` for the bbox-containment detection.

---

## 5. Codex visual review prompt design — MEDIUM risk

### What goes wrong

Reusing #24's `prompts/zeitung-all-pages-audit.md` for #25 produces irrelevant findings:

- #24's prompt enumerates `letterbox` as a primary category — that class is RESOLVED. New prompt should drop it or signal "should be 0" expected.
- #24's prompt asks Codex to enumerate "every alignment defect" generically — produces overlapping findings with #23's classes (bleed-gap, flush-mismatch, partial-overlap, spread-seam).
- The user has narrowed scope to **3 specific bug classes** for #25. The prompt MUST narrow Codex's search scope or it'll surface noise the rules can't act on.

### How to avoid

Write a new prompt `prompts/zeitung-image-vs-text-extent.md` (per ISSUE.md Phase 1 wording) that asks for ONLY these three classes, in this exact order:

1. **Image-frame wider than underlying text-column block** — for each non-cover page, does any image frame's horizontal extent exceed the body-text block's left/right extent? (Body block is the column grid; ~170mm wide for 3-column.) Report frame name + estimated drift in mm.
2. **Per-spread L/R margin asymmetry** — pair each LEFT page with its facing RIGHT page (pages 2+3, 4+5, 6+7, 8+9, 10+11, 12+13). Are outer/inner margins mirrored? Report page pair + estimated asymmetry.
3. **Green-bordered text-card width inconsistency** — across pages 12, 13, 14, are the green-stroke cards (Dunkelgrün outline OR fill) the same `(w, h)` and the same border thickness?

Forbid Codex from re-listing #23/#24 classes:

> Do NOT report letterboxing, full-bleed gap, scale_type mismatch, or INJECT_MAP issues — these are resolved in prior issues.

End with the structured verdict block (matches #24 prompt pattern).

### Warning signs
- Codex output mentions "letterbox" or "INJECT_MAP" → prompt failed to narrow scope, expect noise.
- Codex output flags issues on cover (page 1) for image-vs-text-block → cover is structurally exempt; planner must address in heuristic, not in prompt.

### Cross-reference
- See `prompts/zeitung-all-pages-audit.md` for the structural pattern (verdict block format).
- See `reviews/codex-zeitung-all-pages-iter2.md` for the actual Codex output format and the verdict block shape (`<verdict value="..." critical="N" high="N" medium="N">`).

---

## 6. Pre-applied overrides for 7 non-Zeitung templates — LOW risk (mechanical)

### What goes wrong

If the new rules ship without pre-applied skip overrides on the other 7 templates, `bin/audit-alignment --strict --all` exits non-zero on commit-#1 of the rule-code task, breaking CI for the duration of the PR.

### How to avoid

Apply the `meta.yml::brand_overrides` skip for all 7 in the same atomic commit as the rule code, with reason "scheduled for follow-up audit per #25" — exact pattern from #24 T03 (commit `24e854b`).

7 templates needing skip overrides for `brand:image_within_text_block`, `brand:document_margins_consistent`, `brand:text_card_size_consistent`:
- postkarte-a6-kampagne
- plakat-a1-hochformat
- infostand-tent-card-a5-quer
- themen-plakat-a3-quer
- kandidat-falzflyer-din-lang
- wahltag-tueranhaenger
- wahlaufruf-postkarte-a6-quer

**Sub-pitfall**: All 7 are `facing_pages=False` single-page templates. For `document_margins_consistent`:
- The "left/right" sections of the spec only apply to facing-pages docs. Document this in the schema.
- Single-page templates need ONLY a `cover` spec (or skip entirely).
- If single-page templates skip via `brand_overrides`, the cover-margin check is also skipped, which is fine for now (per ISSUE.md "scheduled for follow-up audit").

### Cross-reference
- `templates/<slug>/meta.yml::brand_overrides` pattern: see `templates/postkarte-a6-kampagne/meta.yml` (already lists 4 brand:* overrides).
- All 7 are `facing_pages=False` confirmed: see `grep facing_pages templates/*/build.py` → only `zeitung-a4-grun/build.py:34` is `True`.

### Warning signs
- CI red after T01 (rule code) lands → pre-applied overrides missed.
- A template's `meta.yml` has `brand_overrides` listing the new rule with no reason → schema fails (reason is required, see `meta_schema.py:34-37`).

---

## 7. Existing `brand:visual_adjacency_drift` overlap — MEDIUM risk

### What goes wrong

`brand:visual_adjacency_drift` (#23, brand_constraints.py:887) emits a warning when two frames are "almost aligned" on x or y by 0.5–25 mm. The new `brand:image_within_text_block` rule asserts image edges == text-block edges (within 0.5mm). **For the same image-vs-text-block pair**:

- If image extent is OFF by 0.5–25 mm → BOTH rules fire.
- The user receives two warnings for one bug. Confusing; may suggest the rules disagree.

Plus: `_VisualAdjacencyDriftRule` re-runs declared CONSTRAINTS to check disagreement (`brand_constraints.py:964-991`). If `image_within_text_block` is implemented as a constraint+rule pair, the re-run could mask its own emission.

### How to avoid

- `brand:image_within_text_block` is the **stricter** variant (must be EQUAL not just NEAR). It fires on (block_left, image_left) at threshold 0.5mm.
- `brand:visual_adjacency_drift` continues to fire on (block_left, image_left) at threshold 0.5–25 mm range — **but only if the pair is not already declared via CONSTRAINTS**.
- **Mitigation**: implement `image_within_text_block` purely as a BrandRule (no per-template Constraint declaration). Don't add the (image, text-block) pair to declared_pairs. Both rules fire on geometrically-bad pairs. Document this overlap in the rule docstrings as INTENDED (image_within_text_block = strict; adjacency_drift = heuristic). User reads both warnings as one finding from two perspectives.

Alternative: planner may decide to make `image_within_text_block` suppress `visual_adjacency_drift` for the same pair. If so, the suppression must be encoded in the adjacency-drift rule (not the new rule), to avoid coupling. Recommend NOT suppressing — two warnings on real bugs is a feature, not noise, since both rules have different prevention strategies.

### Warning signs
- Audit JSON shows the same (image, text-frame) pair in both `image_extent_warnings` and `suspicious_pairs`. Expected; document.

### Cross-reference
- `_VisualAdjacencyDriftRule.check()`: `brand_constraints.py:924-1029`.
- Locked-pattern declaration loop: `brand_constraints.py:929-939`.

---

## 8. Atomic-PR ordering — HIGH risk

### What goes wrong

Out-of-order commits trigger CI failures or leave intermediate states with broken assumptions:

- Rule code committed BEFORE pre-applied overrides → CI red on every other template until override commit lands.
- Rule code committed BEFORE `body_block_margins` field exists in Zeitung meta.yml → rule has no spec to check, may crash or skip silently.
- Codex pre-fix audit committed BEFORE rules are wired into `bin/audit-alignment` → Codex output can't be cross-checked against audit JSON.
- Geometry fix committed BEFORE Codex pre-fix audit → no baseline to compare against; can't claim "Codex flagged X, fix made it pass."
- SHA bump committed BEFORE geometry fix → SHA matches old PNGs; PNG/SLA mismatch breaks `bin/check-stale-previews`.
- Invariant tests committed BEFORE geometry fix → tests fail in the commit they're added.

### How to avoid

Use the EXACT ordering from #24 (which was correct):

1. **T01** — rule code in `brand_constraints.py` + unit tests using synthetic mini-docs (test_brand_image_within_text_block.py, test_brand_document_margins_consistent.py, test_brand_text_card_size_consistent.py). Registry 15 → 18. NO real-template coordinate pinning.
2. **T02** — wire rules into `audit_alignment.py` (the `_audit_doc` function lines 133-216 — add `image_extent_warnings` analog buckets per new rule), JSON output extension, Markdown output extension. Add `--check-document-margins` / `--check-text-cards` flags mirroring `--check-image-extent` (`audit_alignment.py:540-545`).
3. **T03** — pre-applied `brand_overrides` skip for the 7 non-Zeitung templates with reason "scheduled for follow-up audit per #25".
4. **T04** — extend `meta_schema.py` with `body_block_margins` schema; add `load_body_block_margins(slug)` loader. Add Zeitung's `body_block_margins` to its meta.yml. **At this point no `except_pages` configured** — get audit output to drive the value.
5. **T05** — Codex pre-fix audit. Save to `.issues/<slug>/reviews/` AND `reviews/codex-zeitung-image-vs-text-iter1.md` (per ISSUE.md). Cross-check: every Codex finding maps to a rule-emitted violation. If gap → strengthen rule (T01 redo), document in EXECUTION.md.
6. **T06** — fix Zeitung geometry per `bin/audit-alignment` findings AND Codex iter1 findings. One commit per fix-class (image-vs-text-block, margin-spec compliance, text-card-size). Update `body_block_margins.except_pages` if needed.
7. **T07** — `bin/render-gallery zeitung-a4-grun --skip-visual-diff` regen + meta.yml SHA bump. SLA, preview SLA, PNGs, SHA all in one commit so `check-stale-previews` exit 0 holds atomically.
8. **T08** — invariant tests in `test_zeitung_geometry.py`. These were red before T06; green now. Add: per-page `image.outer_x_extent ≈ text_block.outer_x_extent` (skip cover/foto-spread), per-spread outer/inner margin mirroring, per-polygon-group size invariance.
9. **T09** — Codex post-fix audit (iter2). Verdict pass with ≤1 medium finding (deferred to #26 if class-(d) emerges).
10. **T10** — EXECUTION.md, status flip via issue-cli (not file edit — per #24 pattern).

### Warning signs
- A commit lands with `bin/audit-alignment --strict` exiting 1 → ordering broken.
- `bin/check-stale-previews` exits 1 inside the PR → SHA bump committed in wrong order.

### Cross-reference
- #24 EXECUTION.md task table for the proven 8-task ordering pattern. New issue has 10 tasks because it adds: (a) new schema field (T04), (b) two iterations of Codex (already in #24 pattern at T05+T08).

---

## 9. Visual-baselines change — MEDIUM risk (human reviewer awareness)

### What goes wrong

Geometry fixes change pixel content on ~5 pages of Zeitung previews (per ISSUE.md image-vs-text-block fix list: pages 2, 4, 5, 10, 11). The PR will show a large `templates/zeitung-a4-grun/page-*.png` diff. Reviewer might:

- Assume the change is regression rather than intentional fix.
- Miss that the SHA bump is required (commit `bin/check-stale-previews` would catch but adds friction).
- Approve without visually inspecting the new PNGs vs previous.

### How to avoid

- EXECUTION.md must include a "Visual baselines change" section listing exactly which `page-N.png` files changed and why (link to Codex iter1 + iter2 outputs).
- PR description must include a side-by-side image grid for the changed pages (use `reviews/all-templates-grid.png` style).
- Per #22 acceptance criterion 13 + #23 acceptance criterion 14: "User-confirmed pages 1, 8, 10, 11, 12 of Zeitung visually re-checked by human reviewer in PR." Include same line for #25 with new page list (likely 2, 4, 5, 10, 11, 12, 13, 14).

### Warning signs
- PR has a visible PNG diff but no EXECUTION.md note explaining why.
- Reviewer blocks on "looks different" — they didn't have the explanation upfront.

---

## 10. Margin spec values — current Zeitung is uniform 20mm — MEDIUM risk

### What the user actually has

Per dispatcher item 10 + verified against build.py lines 489-516:

- **Body text columns** sit at x=20, 77.67, 135.34 each w=54.67. Block extent = [20, 190]. Right margin = 210 - 190 = 20mm. Left margin = 20mm.
- **Cover** is separate; its margin is structurally different (full-bleed Hero).
- **No traditional inner-vs-outer asymmetry** — current Zeitung is uniformly 20mm on both spine and outer.

The user's original ISSUE.md text suggests inner < outer ("typical: cover symmetric, body pages have inner < outer for spine"), but the **current geometry is uniform 20mm**.

### What goes wrong

If the planner pins `body_block_margins.left.inner_mm = 12` to match the ISSUE.md example, every left-page audit fires false positives because actual geometry has inner=20.

### How to avoid

**Decision (per dispatcher item 10)**: pin uniform 20mm spec for the current Zeitung:

```yaml
body_block_margins:
  cover: {left_mm: 20, right_mm: 20, top_mm: 20, bottom_mm: 22}
  left:  {outer_mm: 20, inner_mm: 20, top_mm: 49, bottom_mm: 22}
  right: {outer_mm: 20, inner_mm: 20, top_mm: 49, bottom_mm: 22}
  except_pages: []   # may add foto-spread page if needed
```

(The 49mm top is body-text-y at 49.5; 22mm bottom is page_h - text-h end ≈ 297 - 275.) These exact values must be confirmed by the planner reading actual coordinates from build.py at PLAN time, NOT taken from ISSUE.md.

Document in the rule docstring + meta.yml comment:

> The Zeitung is currently symmetric (inner=outer=20mm). The rule supports inner≠outer for templates that introduce spine asymmetry later; this template does not (yet).

### Warning signs
- Audit reports "inner_mm=20 expected 12" on every left page → spec pinned to ISSUE.md example instead of measured geometry.

### Cross-reference
- Body grid coordinates: `templates/zeitung-a4-grun/build.py:489-516` (page0 example), repeated identically for each non-foto-spread page.
- Body text top y: 49.5 on most pages; 130.14 on pages 9/10 (post-#22 T13 fix below P9 Spread).

---

## 11. `bin/render-gallery zeitung-a4-grun --skip-visual-diff` + SHA bump — LOW risk (mechanical)

### What goes wrong

- Forgetting `--skip-visual-diff` flag → render pipeline tries to compare against an outdated PNG snapshot from the prior SHA, fails on byte diff.
- Bumping SHA without re-rendering PNGs → PNG/SLA mismatch breaks `bin/check-stale-previews`.
- Re-rendering only PNG without updating `template.sla` and `template-preview.sla` → stale SHA on a now-different SLA.

### How to avoid

The single command does all four:
1. Re-renders `template.sla` from build.py.
2. Re-renders `template-preview.sla` (the one with INJECT_MAP populated).
3. Re-renders all 14 `page-*.png`.
4. Updates `meta.yml::previews_for_sla` SHA to the new SHA256 of `template.sla`.

Verify atomicity: `bin/check-stale-previews` MUST exit 0 in the same commit as the geometry fix + render-gallery output.

### Cross-reference
- See `tools/render_pipeline.py:5-7` ("SHA256(template.sla) → meta.yml::previews_for_sla").
- See `tools/render_pipeline.py:649-654` for the `--skip-visual-diff` flag.

### Warning signs
- `bin/check-stale-previews` red → SHA in meta.yml ≠ SHA256(template.sla on disk).

---

## 12. `brand:image_text_overlap` interaction — MEDIUM risk

### What goes wrong

When an image frame shrinks to fit inside a text column (e.g., page 11 P10 Portrait shrinks from full-bleed 77.7mm to single-column 54.7mm), it may:

- Now PARTIALLY overlap text frames in adjacent rows that weren't previously overlapping (the smaller portrait sits within the column-3 text frame's bbox region).
- `brand:image_text_overlap` (severity ERROR, `brand_constraints.py:718-805`) will fire.
- Atomic ordering: this surfaces in T06 (geometry fix) and must be fixed in the same task — don't ship a fix that creates a new ERROR.

### How to avoid

- Before applying P10 Portrait shrink, compute new bbox vs existing text-frame bboxes in same page region.
- If overlap detected, also adjust the text-frame `h_mm` to end above the new portrait y (mirrors page-9/10 fix from #23 T07 — see `brand_constraints.py:32-44` reason for `Kopie von u2d5c (13)` shrink).
- Run `bin/audit-alignment zeitung-a4-grun --strict` between sub-fixes within T06 to catch overlap creation early.

### Warning signs
- Post-T06 audit reports new `brand:image_text_overlap` ERROR on a page that was clean before.

### Cross-reference
- The page-10 precedent: `meta.yml:32-44` documents the prior fix (`Kopie von u2d5c (13)` h_mm shrunk to end above the green card).
- `_ImageTextOverlapRule.check()`: `brand_constraints.py:745-805`.

---

## 13. #19's logo letterbox WARNING — out of scope confirmation

### What goes wrong

#19's EXECUTION.md flagged a "logo letterbox WARNING" as out-of-scope (the logo image inside its frame letterboxes due to aspect mismatch — same class as #24's INJECT_MAP issue but on a non-Zeitung template). #25 could fix it via `compute_aspect_fill` on the logo (helper exists in `library` per #24 T01 commit message), but:

- Doing so blurs scope between #25 (Zeitung-image-vs-text-block) and a global logo-letterbox sweep.
- Risks scope-creep to all V1-bound templates that have the same logo pattern.

### How to avoid

Document explicitly in #25 RESEARCH.md and PLAN.md that the logo-letterbox WARNING from #19 is NOT in scope. Defer to a #19 follow-up issue. The new `brand:image_within_text_block` rule does NOT apply to logos (logos are anchor-positioned via `is_anchor_positioned` flag — same skip pattern as `_BleedCoverageRule`).

### Cross-reference
- `_BleedCoverageRule` skips anchor-positioned frames: `brand_constraints.py:621` ("Anchor-positioned frames").
- The new rule should mirror this skip.

---

## 14. Multi-iteration Codex budget — LOW risk (precedent set)

### What goes wrong

Per #23/#24 pattern (locked decision #10 in #24): max 2 Codex iterations (pre-fix + post-fix). If post-fix Codex still flags issues, defer to next issue.

For #25, this means:
- iter1 (pre-fix) drives geometry fix scope.
- iter2 (post-fix) verifies clean.
- If iter2 still surfaces a class the new rules don't catch, defer to #26.

### How to avoid

- Declare the 2-iteration budget in PLAN.md as a locked decision, mirroring #24 locked decision #10.
- Don't iterate beyond 2; ship + defer per established protocol (`reviews/codex-zeitung-all-pages-iter2.md` pattern).

### Cross-reference
- #24 locked decision: documented in `reviews/codex-zeitung-all-pages-iter2.md:53-55` ("2 cycles of 2 budgeted").

---

## Environment availability audit

| Dependency | Required by | Available | Version | Notes |
|------------|------------|-----------|---------|-------|
| Python | All | YES | 3.13.5 | |
| Pillow (PIL) | image asset reading (existing #24 pattern) | YES | 12.2.0 | |
| jsonschema | meta.yml schema validation | YES | 4.26.0 | Already used in `meta_schema.py` |
| PyYAML | meta.yml parse | YES | 6.0.3 | Already used |
| scribus | render pipeline (template.sla → PDF/PNG) | YES | `/usr/bin/scribus` | Used by `bin/render-gallery` |
| codex CLI | Codex visual review | YES | codex-cli 0.128.0 | Resolved via `/root/.npm-global/bin/codex` |
| gh CLI | (PR creation only) | YES | 2.92.0 | |
| issue-cli | review-exec dispatch | YES | `/usr/local/bin/issue-cli` | `review-exec` subcommand confirmed |

No installation required. All tools the issue depends on are present.

---

## Sources

### HIGH confidence (codebase verification)
- `tools/sla_lib/builder/brand_constraints.py` (1443 lines) — read structure + key sections.
- `tools/sla_lib/builder/meta_schema.py` (123 lines) — full read.
- `tools/audit_alignment.py` (590 lines) — read structure + main wiring.
- `templates/zeitung-a4-grun/build.py` (2773 lines) — sampled key sections (P1 Hero, P10 Portrait, P7 Portrait, body text columns, page12/13 Dunkelgrün band, CONSTRAINTS list).
- `templates/zeitung-a4-grun/meta.yml` — full read.
- `templates/<7 others>/meta.yml` — partial read (brand_overrides section).
- `tools/sla_lib/tests/test_zeitung_geometry.py` — read header + test class names.
- `prompts/zeitung-all-pages-audit.md` — full read (#24's prompt, the precedent).
- `reviews/codex-zeitung-all-pages-iter2.md` — read first 60 lines (verdict format + 2-iter budget precedent).
- `.issues/archive/24-*/EXECUTION.md` — sampled (deferred class-(c) → #25 confirmation).
- `.issues/archive/22-*/ISSUE.md` + `archive/23-*/ISSUE.md` — full read.

### MEDIUM confidence
- "Body text frame width > 30mm AND height > 50mm" — heuristic threshold proposed by reasoning from observed Zeitung body text geometry (54.67mm × 146mm); not a documented project convention.
- "Foto-spread master needs except_pages" — design choice based on master_name not matching links/rechts; alternative is to add it to SIDE_RX, but that conflates spread with side detection.

### LOW confidence
- "User has no traditional inner-vs-outer-margin asymmetry yet" — based on dispatcher input (item 10) + body-grid coordinate inspection. The user's CONTEXT may differ; planner should re-confirm via build.py audit at PLAN time.
- "Logo letterbox WARNING out of scope" — based on #19's deferral pattern, not on a re-read of #19's EXECUTION.md.

---

## Open questions for the planner

1. **`body_block_margins` precise field shape**: ISSUE.md proposes 4 fields per section but doesn't decide between absolute `left_mm`/`right_mm` (cover) and spine-aware `outer_mm`/`inner_mm` (left/right). Recommend the planner finalize the schema in PLAN.md with both shapes + a `except_pages` array.
2. **`text_card_size_consistent` group key precise shape**: planner must decide between (a) fill+stroke+line_width grouping vs (b) the ISSUE.md's "fill + anname-pattern + contained-text-style" — recommend (a).
3. **Should `image_within_text_block` rule fire on cover (severity WARNING per ISSUE.md)?** — recommend: skip cover entirely (no detected block on the cover page → silent skip), let the user opt-in cover via a future spec field. Avoids the structural-difference false-positive.
4. **Is the user OK with two warnings per bug (image_within_text_block + visual_adjacency_drift)?** — recommend yes; document.
5. **Anchor-positioned image frames**: same skip pattern as `_BleedCoverageRule`? Recommend yes (logos and inline icons should never be checked against text-block extent).

---

## Ready for synthesis

Pitfalls research complete. Synthesizer should fold these into RESEARCH.md's `## Common Pitfalls` and `## Project Constraints` sections, plus the open questions into the planner's "decisions to lock" list.
