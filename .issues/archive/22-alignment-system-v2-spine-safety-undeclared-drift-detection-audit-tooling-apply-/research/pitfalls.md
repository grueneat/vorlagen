# PITFALLS Research — Issue #22 (alignment-system v2)

**Researched:** 2026-05-09
**Scope:** What goes wrong, what breaks, environmental constraints, and prescriptive
mitigations for `brand:spine_safety` + `brand:undeclared_alignment_drift` +
`tools/audit_alignment.py` + per-template encoding for zeitung/postkarte/plakat.

This file is the PITFALLS sub-research feeding RESEARCH.md. Verified against
working tree at `.worktrees/22-…/`. Confidence levels: HIGH = verified by
reading source, MEDIUM = inferred from project conventions, LOW = needs
planner judgement.

---

## Executive summary

Three new pitfall classes dominate this issue:

1. **False-positive explosion in `brand:undeclared_alignment_drift`.** Heuristic
   pair-iteration on a 14-page document with ~870 primitives can emit dozens of
   warnings on the first run. Severity must default to `warning` (not `error`),
   thresholds must be tunable per template, and V1-bound templates must be
   pre-overridden so they don't drown the report on day 1.
2. **Anchor + rotation invisibility.** Reading raw `x_mm/y_mm` for adjacency
   tests will produce false positives for anchor-positioned frames (Wahlkreuz,
   logo) and rotated frames (Zeitung `u2950`). The audit MUST reuse
   `_frame_bbox_mm` from `brand_constraints.py` — the same helper that fixed
   `brand:inside_page` in Issue #14.
3. **Facing-page side detection is master-name dependent.** `Page.is_left` is
   declared on `Page` (document.py:120) but `add_page()` hard-codes it to
   `False` for doc pages even in facing-pages mode (document.py:391-393). The
   ONLY reliable signal for "is this page on the LEFT of a spread?" is
   `master_name` substring matching `links` / `rechts`. Substring matching is
   fragile — use word-boundary regex.

A single PR with two new BrandRules + audit tool + 3 templates encoded + tests
+ regen + docs is large (~15-20 commits). The agent may run out of usage
budget mid-execution; the planner must split tasks small (≤200 lines/commit)
so partial completion can land cleanly.

---

## Critical Pitfalls

### P-1. Audit reads raw `x_mm`/`y_mm` instead of resolved bbox (anchors + rotation)

**What goes wrong:** A frame with `anchor=Anchor(h="center", v="bottom")` carries
dummy `x_mm=0, y_mm=0` in the Frame dataclass. Its actual emitted position
comes from `resolve_anchor()` at SLA-emit time. If the audit's adjacency check
reads `frame.x_mm` directly, every anchor-positioned frame appears at `(0, 0)`
and clusters with every other anchored frame on every page → massive false
positives. Same for rotated polygons (`u2950` at rotation_deg=90 has bbox
extending below `y_mm + h_mm`).

**Why it happens:** The DSL splits position into three layers:
- `x_mm/y_mm` — for non-anchored, non-rotated frames; the actual position.
- `anchor` — for anchor-positioned frames; resolved at emit time against the
  page dimensions and the frame's own `w_mm/h_mm`.
- `rotation_deg` — rotates around the top-left corner CCW; the axis-aligned
  bbox after rotation differs from `(x, y, w, h)`.

Issue #14 already solved this for `brand:inside_page` by introducing
`_frame_bbox_mm(item, page) → (x0, y0, x1, y1)` and `_rotated_bbox(...)` in
`tools/sla_lib/builder/brand_constraints.py:371-418`. The new audit /
`brand:undeclared_alignment_drift` rule MUST reuse the same helper, NOT
reinvent it.

**How to avoid:**
1. Promote `_frame_bbox_mm` from "private to brand_constraints.py" to a
   shared helper. Either:
   - Move it (and `_rotated_bbox`) into a small `tools/sla_lib/builder/bbox.py`
     module and re-export from `brand_constraints.py` for back-compat, OR
   - Keep it in `brand_constraints.py` and import it from
     `audit_alignment.py` (`from sla_lib.builder.brand_constraints import
     _frame_bbox_mm`). The leading underscore is a problem — rename to
     `frame_bbox_mm` and `rotated_bbox` to mark them as the public bbox API.
2. Use `_frame_bbox_mm(item, page)` to derive `(x0, y0, x1, y1)` for every
   primitive in adjacency / drift checks. NEVER read `item.x_mm` etc.
   directly in the audit.
3. Document this in the audit tool's docstring: "All position math goes
   through `frame_bbox_mm()`. Do not regress to raw `x_mm`."

**Warning signs:** Audit report flags pairs like `("Wahlkreuz Symbol", "Logo")`
on every page (both have anchors → both report `(0, 0)` → axis-near). If
seen, the audit is bypassing the bbox helper.

**Confidence:** HIGH (verified by reading `brand_constraints.py` _Frame and
_InsidePageRule, and Issue #14 RESEARCH P-2 referenced in the dispatch
brief).

---

### P-2. Facing-page side detection via `Page.is_left` is BROKEN — must use `master_name`

**What goes wrong:** A naive `if page.is_left:` check misses every doc page in
facing-pages mode because `Document.add_page()` hard-codes `is_left = False`
(document.py:391-393). The Zeitung's 14 doc pages all have `is_left=False`
even though half of them sit on the LEFT of a spread.

**Why it happens:** `is_left` is correctly set on Master pages (`add_master`
line 326: `is_left=(facing == "left")`), but `add_page` deliberately writes
`LEFT="0"` on every doc page in the emitted SLA — verified against
`gruene-zeitung-vorlage-original.sla` per the docstring at document.py:386-393.
The actual side comes from `master_name` matching the assigned master. The
two masters in Zeitung are named:
- `'Neue Musterseite rechts'` → sits on the RIGHT side of spread → spine on
  its **left** edge.
- `'Neue Musterseite links'`  → sits on the LEFT side of spread → spine on
  its **right** edge.

The Cover (page 0) is on `rechts` master and stands alone on the right
column (the page-set's FirstPage="1" puts the cover on the right).

**How to avoid:**
1. **Side-detection helper** — add to bbox.py or directly in the spine-safety
   rule:
   ```python
   import re
   _SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)

   def page_facing_side(page) -> str | None:
       """Return 'left', 'right', or None for a doc page in facing-pages mode."""
       m = _SIDE_RX.search(page.master_name or "")
       if not m:
           return None
       return "left" if m.group(1).lower() == "links" else "right"
   ```
2. Word-boundary regex (`\b`) is critical. Substring `'links' in
   page.master_name` would match a hypothetical master named
   `'rechts-spalte links'` on both sides. The Zeitung's two masters happen
   to use the words at the end so substring would work today, but writing
   the rule against future templates we don't control is safer with `\b`.
3. **Spine-safety rule must early-exit** when `not doc.facing_pages` —
   single-page docs cannot have spine. Pre-empts every false positive on
   plakat / postkarte / wahltag / etc. (7 of 8 templates).

**Warning signs:** Audit report contains `brand:spine_safety` warnings on
plakat-a1-hochformat or postkarte-a6-kampagne. Both have `facing_pages=False`
(verified) — any warning there means the rule isn't gating on
`doc.facing_pages`.

**Confidence:** HIGH (verified by reading `add_page` source, master setup in
zeitung build.py, and the comment block at document.py:386-393).

---

### P-3. False-positive explosion of `brand:undeclared_alignment_drift`

**What goes wrong:** O(N²) pair iteration on Zeitung's 14 pages with up to ~70
primitives per page (it's a journalism layout — many text columns, captions,
small shapes) emits 50+ warnings on first run before any encoding. The
warnings hide real issues, the executor pastes skeletons blindly to silence
them, and the rule's signal-to-noise ratio collapses.

**Why it happens:** Heuristics over geometry will always over-fire. The
acceptable thresholds (`axis_threshold_mm=5`, `adjacency_threshold_mm=12`)
match real "almost-aligned" cases, but real layouts have many "intentionally
not aligned" pairs (a caption next to a portrait, both at "roughly column-3"
but with intentional inset).

**How to avoid (defense in depth):**

1. **Severity = warning by default, not error.** Per ISSUE.md Phase 4b
   step 4: "Severity = warning by default (heuristic rules can false-
   positive)." Encoded in the rule, never overridden. Templates can elevate
   to error via per-template opt-in (`meta.yml::audit_strict: true`) once
   their alignments are fully encoded.

2. **Skip pairs where at least one primitive is rotated.** Rotated bbox
   adjacency math is a separate concern; conservative early-out matches what
   `aligned_below` does (constraints.py:336-343 returns `severity="warning"`
   and skips when either frame is rotated). The audit/drift rule does the
   same: skip silently — the rotated frame's adjacency is already too noisy
   to flag.

3. **Skip pairs where one primitive has no `anname`.** Unnamed frames can't
   be referenced in CONSTRAINTS, so a "declare via `same_x(...)`" suggestion
   is unactionable. Require `frame.anname != ""` on both sides of any
   flagged pair. This drops a lot of converter-generated unnamed
   sub-primitives in the Zeitung (e.g. `<unnamed Polygon>` accents).

4. **Skip pairs where one primitive has no spatial extent** (Run, ParaStyle,
   etc.) — `_frame_bbox_mm()` returns `None` for these; honor it.

5. **Page-local only.** Pairs across pages are never adjacent. Iterate per
   page. (For spine-bleed across pages: separate rule.)

6. **Skip pairs that overlap by >50%.** Containment-near is a separate
   check; "almost aligned" only fires for non-overlapping pairs.

7. **Master-page items: report but tag.** Master polygons (full-bleed
   backgrounds) appear on every doc page that uses the master. Don't
   double-flag — iterate masters separately and tag the report section as
   `(master page)` so the executor doesn't paste the same constraint 14
   times.

8. **Per-template overrides for V1-bound templates.** Pre-apply
   `brand_overrides[brand:undeclared_alignment_drift]` to:
   - `wahlaufruf-postkarte-a6-quer` (#17)
   - `wahltag-tueranhaenger` (#18)
   - `themen-plakat-a3-quer` (#19)
   - `infostand-tent-card-a5-quer` (#20)
   - `kandidat-falzflyer-din-lang` (#21)

   Reason text: `"V1 layout work in #17–#21 owns alignment encoding;
   re-enable once V1 lands."` Without this, the new rule trips on EVERY
   template under `--all` and the agent loses an entire iteration to
   triaging unrelated warnings.

9. **Tunable thresholds in rule constructor.** Defaults `axis_threshold_mm=5`
   and `adjacency_threshold_mm=12`. Templates with extreme grids (e.g.
   plakat-a1-hochformat, large-format posters) may want wider thresholds —
   expose as kwargs on the rule dataclass so a future override mechanism
   (per-template tuning, not just on/off) can land in a follow-up issue
   without changing the rule's contract.

10. **De-dupe pairs.** The pair set is unordered: `(A, B)` == `(B, A)`. Use
    `frozenset({A.anname, B.anname})` as the key when checking against
    declared pairs. Iterate `for i, P in enumerate(prims): for Q in
    prims[i+1:]:` to avoid emitting the pair twice.

**Warning signs:**
- First run on Zeitung emits >100 warnings → thresholds too loose, or audit
  isn't filtering rotated/anonymous frames.
- Audit emits warnings for V1-bound templates → overrides not applied.
- Audit emits warnings on a clean template with all relationships encoded →
  declared-pair extraction is incomplete (see P-7).

**Confidence:** HIGH (the false-positive math is straightforward; the
defense-in-depth list draws on Issue #14's experience with `brand:inside_page`
needing a similar warning/error split).

---

### P-4. Declared-pair extraction must handle multi-arity Constraints correctly

**What goes wrong:** The drift rule needs to know "is this pair already
declared in CONSTRAINTS?" so it doesn't re-flag known relationships. Naive
extraction:
```python
declared = {(c.targets[0], c.targets[1]) for c in CONSTRAINTS}
```
breaks for:
- 3+ target constraints (`same_x(A, B, C)` → declared = `{(A,B)}`, missing
  `(A,C)` and `(B,C)`).
- Single-target witness constraints (`same_size("Cover Hero")` — used in
  every existing template as orphan-warning anchors; targets has one
  element; pair extraction crashes with `IndexError`).
- BrandRule constraints (`brand:inside_page` etc.) which expose `id` but no
  `referenced_annames()` method.

**Why it happens:** `Constraint.referenced_annames()` exists
(constraints.py:67-68) but returns the full target tuple. BrandRule has no
such method — it operates over the full primitive list.

**How to avoid:**
```python
from itertools import combinations

def declared_pairs(constraint_list) -> set[frozenset[str]]:
    """Build the set of declared adjacency pairs from a CONSTRAINTS list."""
    pairs: set[frozenset[str]] = set()
    for c in constraint_list:
        if not hasattr(c, "referenced_annames"):
            continue  # BrandRule etc. — global rules, no pair semantics
        names = [n for n in c.referenced_annames() if n]  # filter empty
        if len(names) < 2:
            continue  # single-target witnesses contribute no pair
        for a, b in combinations(names, 2):
            pairs.add(frozenset({a, b}))
    return pairs
```
Then `if frozenset({P.anname, Q.anname}) in declared: continue` in the
adjacency loop.

**Important nuances:**
- `aligned_below(below, above, gap_mm)` is directional in geometry but the
  pair `{below, above}` is symmetric for "is the relationship declared?"
  purposes. The drift rule treats declared = "the system knows about this
  pair", regardless of direction. Confirmed by the dispatch brief #8.
- `inside(child, parent)` similarly — the declared pair is `{child, parent}`,
  unordered.
- `mirrored_x/y(left, right, axis_mm)` — pair is `{left, right}`.
- BrandRule constraints don't enumerate pairs (their checks are global, not
  pairwise) — exclude them. This means a `brand:wahlkreuz_colored_bg`
  warning that the Wahlkreuz overlaps a green polygon does NOT count as
  "this pair is declared". That's correct — global brand rules don't
  declare per-template alignment intent.

**Warning signs:** Audit reports a pair the executor JUST encoded in
CONSTRAINTS. Either `referenced_annames()` returns something other than what
was passed, or single-target constraints are crashing the extractor.

**Confidence:** HIGH (verified by reading `Constraint.referenced_annames()`
and the existing `same_size("X", name=...)` single-target pattern in every
production template).

---

### P-5. SpreadImage's two halves are NOT a drift pair

**What goes wrong:** `SpreadImage.emit()` returns two ImageFrames named
`"P9 Spread · left"` and `"P9 Spread · right"` (blocks.py:714-733). Each
sits at `x_mm=0` on its own page, both with the same `w_mm=210`. They are
"axis-aligned on x" by construction. If the audit iterates the full
`doc.iter_all_primitives()` and considers them a candidate pair, it flags a
nonsense warning ("P9 Spread · left and P9 Spread · right share x — declare
with `same_x(...)`").

**Why it happens:** SpreadImage's two halves live on different pages (left
on page N, right on page N+1). If the audit iterates per-page (per P-3
mitigation #5), this case CAN'T fire — they're never on the same page.

**How to avoid:** **Iterate per page**, not per document. Page-local pair
iteration kills this case naturally. Add a defensive comment in the audit:
```python
# Per-page iteration: SpreadImage halves on different pages never form a pair.
for page in doc.pages:
    items = [it for it in page.items if frame_bbox_mm(it, page) is not None]
    for i, P in enumerate(items):
        for Q in items[i+1:]:
            ...
```

**Warning signs:** Audit warning naming `· left` / `· right` from the same
SpreadImage. If seen, the iteration accidentally crossed page boundaries.

**Confidence:** HIGH (verified by reading SpreadImage source and the
ISSUE.md text re: P9 Spread).

---

### P-6. Polygon `custom_path` shape is ignored — bbox is the rectangle

**What goes wrong:** Polygons can carry a `custom_path` (clipping mask, e.g.
the Wahlkreuz cross or a logo cutout). Authors might assume the audit reads
the path geometry; it doesn't.

**Why it doesn't happen:** Per Issue #14 RESEARCH P-3, the bbox is derived
from `(x_mm, y_mm, w_mm, h_mm)` not the path. The audit follows the same
rule. Don't over-engineer.

**How to avoid:** Document this explicitly in the audit's docstring:
> Bbox = the frame's `(x, y, w, h)` rectangle (rotation- and anchor-aware).
> The polygon's `custom_path` (clip region) is NOT considered for
> adjacency. This matches the rest of the constraint system. To express
> path-shaped adjacency, encode it manually with `inside(...)` against a
> polygon with a tighter rectangle.

**Confidence:** HIGH (verified against _InsidePageRule docstring and
constraints.py _InsideConstraint).

---

### P-7. Composite blocks emit multiple primitives — adjacency between siblings is by design

**What goes wrong:** `ColumnTextStory` (blocks.py:445) emits a chain of
linked TextFrames. They sit at column-grid positions (`x=20, 77.7, 135.3`)
and share `y_mm` by construction (intentional: they're a 3-column flow).
Without filtering, the audit floods with warnings:
"Kopie von u2d5c (13) and Kopie von u2da1 (16) share y on page 5 — declare
with `same_y(...)`".

That's technically correct (they DO share y), but it's noise: ColumnTextStory
sets the alignment programmatically; encoding it in CONSTRAINTS is
busywork.

**How to avoid (two complementary approaches):**

1. **Composite-aware suppression list** — add a `audit_skip_classes` setting
   in the audit tool for primitive types that come from blocks where
   adjacency is structural (not authoring-intent). Day 1: hard-code an empty
   list; the planner / executor extends it as patterns emerge.
2. **Anname-prefix suppression** — provide a per-template
   `meta.yml::audit_skip_anname_prefixes: ["Kopie von "]` to silence the
   converter-generated chain frames. Caveat: prefix-based suppression hides
   real bugs; use sparingly.
3. **Recommend the executor encode ONE constraint per ColumnTextStory** —
   `equal_gap("col1", "col2", "col3", axis="x", gap_mm=...)` covers all
   pairs at once. The audit's pair-extractor (P-4) yields `{col1,col2},
   {col1,col3}, {col2,col3}` from the single constraint, silencing all
   three pair warnings.

**Warning signs:** Audit emits 3+ warnings per page that all reference
"Kopie von u…" frames. Recommend approach #3 (encode the column grid as
`equal_gap`).

**Confidence:** MEDIUM — tradeoffs depend on how aggressively the planner
wants the audit to suppress structural patterns vs. flag everything for
human review. Default: don't suppress; let the executor encode `equal_gap`
to silence them. Cleaner downstream.

---

### P-8. CI integration as a fatal step day-1 will break CI on every untouched template

**What goes wrong:** Adding `python3 tools/audit_alignment.py --all` as a
fatal step (exit 1 on any drift warning) to `.github/workflows/pages.yml`
breaks CI on the first push for every template that hasn't been audited
(which is 7 of 8 — only Zeitung after Phase 1-3 is clean per ISSUE.md
Phase 7).

**Why it happens:** Heuristic warnings are by definition a starting point;
CI fail on day 1 means every PR landing other work has to first triage
audit warnings.

**How to avoid (per ISSUE.md Phase 8):**
1. **Wire as informational only.** The CI step prints the report to stdout
   (visible in build logs / PR Checks tab) but `exit 0` always.
   ```yaml
   - name: Run audit_alignment (informational)
     run: |
       PYTHONPATH=tools python3 tools/audit_alignment.py --all || true
       # || true makes the step non-fatal even if exit code != 0
   ```
2. **Promote to fatal in a follow-up issue** once all production templates
   are clean. Track this as Issue #22.1 ("promote audit_alignment to fatal
   CI") in the EXECUTION.md follow-up list.
3. **Per-template `meta.yml::brand_overrides[brand:undeclared_alignment_drift]`**
   already exists as the per-template opt-out — V1-bound templates use it
   until #17–#21 land, AND the BrandRule itself can be globally disabled
   via this mechanism on the per-template level once the rule is integrated
   in `BRAND_CONSTRAINTS`.
4. **Two distinct concerns:**
   - The `brand:undeclared_alignment_drift` BrandRule runs as part of
     `structural_check` and surfaces under that exit code. By default it's
     `severity="warning"` so it doesn't fail CI even without an override.
   - The standalone `tools/audit_alignment.py` CLI emits a richer Markdown
     report (with skeletons + page-by-page inventory) and is wired
     separately as informational. The two share the same heuristic but
     serve different audiences.

**Warning signs:** Pages.yml CI breaks on first push for templates the agent
didn't touch. If seen, audit step is fatal when it should be informational.

**Confidence:** HIGH (verified by reading existing pages.yml and the
ISSUE.md Phase 8 explicit instruction).

---

### P-9. `_load_build_module` sys.modules cache poisoning when audit re-imports per template

**What goes wrong:** `tools/audit_alignment.py` walks N templates and imports
each `templates/<slug>/build.py`. Naive `import templates.zeitung_a4_grun.build`
or `importlib.import_module(...)` caches the module in `sys.modules`. The
NEXT template loaded gets a stale `build_doc()` — particularly bad when two
templates share a top-level constant name (e.g. both define `CONSTRAINTS`).

**Why it happens:** Python's import system de-duplicates by module name. If
the audit uses a stable module name pattern like `templates.<slug>.build`,
each call to `import_module` after the first returns the cached module —
NOT a fresh evaluation.

**How to avoid:** **Reuse the existing `_load_build_module` helper from
`structural_check.py:104-122`.** It already solves this:
```python
mod_name = f"_strcheck_template_{slug.replace('-', '_')}"
sys.modules.pop(mod_name, None)  # drop any cached module
spec = importlib.util.spec_from_file_location(mod_name, p)
mod = importlib.util.module_from_spec(spec)
sys.modules[mod_name] = mod
spec.loader.exec_module(mod)
```
The audit tool should `from sla_lib.builder.structural_check import
_load_build_module` (or refactor the helper to a shared module like
`tools/sla_lib/builder/_template_loader.py` with a public name
`load_build_module(slug, root)` and import from both places).

**Refactor recommendation:** Move `_load_build_module` to a small new module
`tools/sla_lib/builder/template_loader.py` (no underscore prefix; public
API), and import it from both `structural_check.py` and
`audit_alignment.py`. Bonus: easier to unit-test in isolation.

**Warning signs:** Audit reports identical "missing anname" warnings across
multiple templates with anname strings that only exist in ONE of them. If
seen, sys.modules caching is bleeding state across templates.

**Confidence:** HIGH (verified by reading `_load_build_module` source and
its explicit comment "to avoid sys.modules cross-contamination when --all
iterates").

---

### P-10. `pdfimages -list` cross-spread detection is template-specific and slow

**What goes wrong:** ISSUE.md Phase 6 + acceptance criteria require
`pdfimages -list templates/zeitung-a4-grun/preview.pdf` to show each image
on exactly ONE page (no cross-spread sharing). This is the GROUND TRUTH for
spine-bleed: if a single image obj appears on pages 2+3, it leaks across
the spine. The original Zeitung had three such leaks (objs 42, 84, 97 per
ISSUE.md "Why" §1).

**Why it's a pitfall:** This check is:
- **Slow** on a 14-page document with ~50 images (~5-10 seconds).
- **Poppler-dependent** (already installed in CI per pages.yml:50, and
  locally — `/usr/bin/pdfimages 25.03.0` verified). Not new dep, but still
  a runtime requirement.
- **PDF-only** — operates on rendered output, not the SLA. Requires the
  preview to have been re-rendered AFTER any geometry fixes. Stale previews
  give stale results.
- **Single-template** — runs on one slug at a time; running across `--all`
  multiplies cost.

**How to avoid:**
1. **Audit tool flag `--check-pdf`** — gated behind explicit opt-in,
   defaults OFF. Document why: "slow (~10s/template), requires preview to be
   rebuilt; use only on the templates you've just edited."
2. **Don't put it in the BrandRule.** `brand:spine_safety` operates on the
   built Document (no PDF needed). PDF verification is a SEPARATE step in
   `audit_alignment.py`'s report (and a manual acceptance check per
   ISSUE.md). Don't conflate.
3. **Wire the manual `pdfimages -list` verification into EXECUTION.md** as
   a final acceptance check the executor runs after Phase 5 regen.
4. **Algorithm for cross-spread detection:**
   ```bash
   pdfimages -list preview.pdf | awk 'NR>2 {print $1, $2}' | sort | uniq -c \
     | awk '$1 > 1 {print "image obj " $3 " appears on " $1 " pages"}'
   ```
   But beware: column 2 is `num` (page); column 1 is `count`/`page` depending
   on poppler version. Verify with `pdfimages -list --help` on the local
   poppler before scripting.

**Caveat:** `pdfimages -list` enumerates IMAGES per page. A spine-bleed
caused by a NON-IMAGE element (e.g. a Polygon background extending across
the spread) does not show up as a duplicated image. The audit's
`brand:spine_safety` rule covers polygons too; `pdfimages -list` only
catches the image case. They are complementary, not redundant.

**Warning signs:** Acceptance criteria check fails despite audit reporting
clean. If seen, polygon spine-bleed exists but isn't caught by the
image-only PDF check; rely on the BrandRule's coverage.

**Confidence:** HIGH (verified `pdfimages` is installed locally + in CI;
ISSUE.md Phase 6 explicit).

---

### P-11. Test count for `test_brand_constraints.py::test_nine_rules_exact` will break

**What goes wrong:** `tests/test_brand_constraints.py:50` asserts
`len(BRAND_CONSTRAINTS) == 9`. Adding two new BrandRules (spine_safety +
undeclared_alignment_drift) makes it 11. The test fails on first push if not
updated.

**Why it happens:** Number-of-rules guard test exists to catch accidental
removal of rules. Adding rules requires bumping the constant.

**How to avoid:** Update the test in the same commit that adds the new
rules:
```python
def test_eleven_rules_exact(self):  # rename for clarity
    self.assertEqual(len(BRAND_CONSTRAINTS), 11)

def test_ids_are_canonical(self):
    expected = {
        "brand:color_palette",
        "brand:font_family",
        "brand:line_spacing_0.9",
        "brand:hl_sl_distance_x2",
        "brand:logo_size_3M",
        "brand:text_on_green",
        "brand:bleed_3mm",
        "brand:wahlkreuz_colored_bg",
        "brand:inside_page",
        "brand:spine_safety",                # NEW
        "brand:undeclared_alignment_drift",  # NEW
    }
    self.assertEqual(set(ids), expected)
```
Plus `test_nine_rules_exact` should be renamed to remove the magic number,
or replaced with a more descriptive test name. Already covered in
ISSUE.md Phase 5 "Update `tools/sla_lib/tests/test_brand_constraints.py` —
bump count from 9 to 10" (slightly stale: should be 11 not 10, since
ISSUE.md Phase 4 + 4b add TWO rules).

**Note on ISSUE.md error:** The acceptance text says "bump count from 9 to
10", but Phase 4 adds `spine_safety` (rule #10) AND Phase 4b adds
`undeclared_alignment_drift` (rule #11). The planner should correct this
to "bump count from 9 to 11" in the plan.

**Confidence:** HIGH (verified `test_brand_constraints.py:50` and counted
the new rules).

---

### P-12. `meta.yml::brand_overrides` schema accepts the new rule IDs

**What goes wrong:** `meta_schema.py:_BRAND_OVERRIDE_SCHEMA` validates the
brand_overrides shape; the regex `^brand:[A-Za-z_0-9.]+$` accepts new
IDs. BUT `_validate_and_collect_ids()` (line 109-121) emits a WARNING
when an override id is not in `BRAND_CONSTRAINTS`. If templates declare
`brand:undeclared_alignment_drift` BEFORE the rule is added to
`BRAND_CONSTRAINTS`, every load emits a warning.

**Why it happens:** The audit/override registration is order-dependent. The
planner's task ordering must add the new rules to `BRAND_CONSTRAINTS` BEFORE
adding `brand_overrides` entries to V1-bound templates.

**How to avoid:** Sequence tasks correctly:
1. T-X: add `_SpineSafetyRule` + `_UndeclaredAlignmentDriftRule` to
   `BRAND_CONSTRAINTS` registry — rules exist with default severity
   "warning".
2. T-Y: add `brand_overrides` to V1-bound templates (#17–#21 slugs).
3. T-Z: add encoding to zeitung / postkarte / plakat to satisfy the new
   rules.

Tasks Y and Z can run in parallel after X. Task X must come first.

**Warning signs:** `python3 -m sla_lib.builder.structural_check --all` emits
`UserWarning: brand_override id 'brand:undeclared_alignment_drift' is not in
BRAND_CONSTRAINTS` for V1-bound templates. If seen, task ordering was
inverted.

**Confidence:** HIGH (verified `_validate_and_collect_ids` source).

---

### P-13. ISSUE.md says `audit_strict: true` per-template — but no such field exists yet

**What goes wrong:** The dispatch brief #15 suggests "template-level opt-in
to elevate to error for templates that have completed their alignment
encoding (via `meta.yml::audit_strict: true`)". `meta_schema.py` currently
validates only `brand_overrides`, `sla_diff_strict`. A NEW key
`audit_strict` requires:
- New schema entry in `meta_schema.py`.
- New loader function `load_audit_strict(slug, root) -> bool` (default
  False).
- The drift BrandRule reads it via `getattr(doc, 'audit_strict', False)` or
  the audit tool reads the meta.yml directly.

**Why it's a pitfall:** Adding a new meta.yml field is small (~30 lines)
but easy to miss. Without it, "elevate to error for clean templates" can't
be done at all, and the planner has no migration path from
"informational on day 1" → "fatal once clean".

**How to avoid:** Defer this decision. Day-1 the rule is `severity="warning"`,
period. The promotion-to-fatal path becomes a follow-up issue once 3
templates are clean (i.e., once the executor has data to back the
threshold tuning). ISSUE.md Phase 8 explicitly says: "promotion to fatal
once all production templates are clean" — this is a follow-up, not part
of this PR.

**Recommendation to planner:** DO NOT add `audit_strict` in this PR. Stick
with two states:
- `severity="warning"` always (default).
- Per-template skip via existing `brand_overrides` mechanism.

The third state ("error for clean templates") deserves its own follow-up
issue once we have evidence about which thresholds are right.

**Confidence:** MEDIUM — judgement call; the dispatch brief mentioned
`audit_strict` as a suggestion but ISSUE.md doesn't require it.

---

### P-14. Suggested-skeleton output must be syntactically-valid Python, not pseudocode

**What goes wrong:** ISSUE.md Phase 8 + dispatch brief #16 require the
audit tool to emit "suggested constraint skeletons the executor can paste".
A naive output like:
```
"Frames `Hero Image` and `Body Text Col 1` differ by 1.2mm in x — declare with same_x"
```
is unactionable: the executor has to re-derive the function call form,
the import, the name kwarg.

**How to avoid:** Output ready-to-paste Python:
```markdown
- **page 5, axis-x drift 1.2 mm**: `'Hero Image'` and `'Body Text Col 1'`
  ```python
  from sla_lib.builder.constraints import same_x
  same_x("Hero Image", "Body Text Col 1", name="p5_hero_col1_x")
  ```
```

Auto-name pattern (matches existing convention in `_autoname()`):
`{factory_kind}({a}, {b}, name="p{N}_{a_slug}_{b_slug}_{axis}")` where
slugs lowercase + underscore the anname.

The choice of factory depends on the heuristic that fired:
- Suspicious-axis-x → suggest `same_x(...)`.
- Suspicious-axis-y → suggest `same_y(...)`.
- Suspicious-adjacency (P below Q with small gap) → suggest
  `aligned_below(P, Q, gap_mm=<measured>)`.
- Containment-near (P mostly inside Q) → suggest `inside(P, Q)`.

The audit MUST output the import line at the top of each report (or in a
"How to apply these" preamble), not per-skeleton — keeps the report
readable.

**Edge case:** annames containing special characters (the Zeitung has
`'Kopie von u2d5c (13)'` — contains spaces, parens). Python string
literals handle them fine — just always use `"..."` quotes (not bare
identifiers). The auto-generated `name=` kwarg slugs them via
`re.sub(r'\W+', '_', anname).strip('_').lower()`.

**Confidence:** MEDIUM — the audit-tool output format isn't constrained by
existing code; this is a recommendation. Planner can adjust skeleton
format.

---

### P-15. Atomic PR is large — agent may run out of usage mid-execution

**What goes wrong:** Per past experience (and the dispatch brief #17), this
PR is ~15-20 commits:
- 2 new BrandRules + tests (3 commits)
- audit_alignment.py + tests (2 commits)
- pre-applied overrides for 5 V1 templates (1 commit)
- 3 stable templates encoded + geometry fixed (3-6 commits)
- regen of all 3 (1 commit, but big)
- doc updates (SCHEMA.md, SPEC-WRITING-GUIDE.md, READMEs) (2-3 commits)
- bin/audit-alignment + CI integration (1 commit)
- closing #39 (1 commit, just the gh CLI call in EXECUTION.md)
- session-history row (1 commit)

If the agent's usage budget runs out at commit 12, the work landed so far
is partial: BrandRules + tests + audit tool may be fine, but only 1 of 3
templates encoded.

**How to avoid:**
1. **Order tasks so partial completion is still useful.** Sequence:
   - First: BrandRules + tests + audit tool + V1 overrides. After this
     subset, CI is clean (rules exist, drift is warning-level, V1 templates
     opted out, no new errors anywhere). All other work can resume in a
     follow-up PR.
   - Second: per-template encoding (zeitung > postkarte > plakat by user
     priority — Zeitung has the most known bugs).
   - Third: regen + doc.
2. **Keep each commit ≤200 lines diff.** Per-template encoding splits to
   one commit per page (Zeitung has 14 pages → up to 14 commits, each
   small).
3. **Mark optional work in the plan.** PDF verification (`--check-pdf`),
   `bin/audit-alignment` ergonomics, and SCHEMA.md doc updates can land in
   a follow-up if budget runs out. The MUST-LAND core is: 2 rules + audit
   tool + V1 overrides + zeitung encoded.
4. **Per-template `brand_overrides` for `brand:undeclared_alignment_drift`
   on postkarte + plakat** until they're encoded — same pattern as V1
   templates. Lets zeitung-only PR land cleanly even if postkarte/plakat
   encoding gets deferred.

**Warning signs:** Plan has 25+ tasks. If seen, split into two issues
(#22a "infrastructure" + #22b "per-template apply").

**Confidence:** HIGH — past experience cited in the dispatch brief.

---

### P-16. Closing #39 (u2950 polygon) prematurely breaks Zeitung's brand_overrides

**What goes wrong:** Zeitung's current `meta.yml` has
`brand_overrides[brand:inside_page]` with reason "Tracked separately in GH
#39. Removing this override requires resolving #39 first (do not delete
pre-emptively — `structural_check --all` will go red)."

ISSUE.md says #39 is superseded by Phase 3 of this issue (Page-1 alignment
audit will trim u2950). If Phase 3 actually trims u2950 to fit, the
override CAN be removed (and SHOULD be — orphan overrides obscure real
violations). BUT: removing the override WITHOUT trimming u2950 first sends
`structural_check --all` red on the next CI run.

**How to avoid:** Tasks must run in this order:
1. Phase 3 task: edit zeitung build.py to trim u2950 (and any other Phase
   3 fixes).
2. Run `structural_check zeitung-a4-grun` locally — verify
   `brand:inside_page` reports zero violations even WITHOUT the override.
3. Remove `brand_overrides[brand:inside_page]` from zeitung meta.yml.
4. Re-run `structural_check --all` — confirm exit 0.
5. Close #39 as duplicate.

If steps reverse, CI breaks. The plan must enforce this order with a
single task or explicit sequencing.

**Warning signs:** First push after merge fails on `brand:inside_page`
violation for zeitung. If seen, override was removed before u2950 was
trimmed.

**Confidence:** HIGH (verified meta.yml content + ISSUE.md "Superseded
follow-ups" section).

---

### P-17. `Page.master_name` for the auto-injected "Normal" master is empty

**What goes wrong:** `Document._build_xml()` (document.py:491-502) auto-
injects a `Normal` master with `master_name=""` when no masters are defined.
Templates with `facing_pages=False` use this. But also: `add_page(master=...)
` defaults to `master='Normal'`. So a doc page can have
`master_name='Normal'` (when explicit) OR could be linked to the implicit
master. The spine-safety rule's master-name regex `r"\b(links|rechts)\b"`
returns None for "Normal" (and for empty) — that's correct behavior; the
rule should also early-exit when `not doc.facing_pages` (per P-2 mitigation
#3).

**Why it's a pitfall:** Adding the regex check WITHOUT the
`facing_pages` guard means single-page docs with non-Zeitung masters
silently get `side=None` and the rule no-ops correctly. But code review
might think the rule is broken because it never fires on plakat/postkarte.
Belt-and-suspenders: ALWAYS gate on `doc.facing_pages` first.

**Confidence:** HIGH (verified document.py:491-502 + add_page default).

---

### P-18. Test isolation — synthetic Documents in the new tests must use facing_pages=True

**What goes wrong:** Templates of `_doc_with(...)` in `test_constraints_inside_page.py`
use `facing_pages=False` by default. Copy-pasting that helper for
spine-safety tests means EVERY test case gets `facing_pages=False`, the
rule no-ops, and the tests pass for the wrong reason.

**How to avoid:** Provide a dedicated helper in
`test_brand_spine_safety.py`:
```python
def _facing_doc(size="A4", bleed_mm=3.0, masters=("rechts", "links")):
    """Doc with facing_pages=True and two masters named for sides."""
    d = Document(title="t", template_id="t", facing_pages=True)
    d.add_master(name=f"Neue Musterseite {masters[0]}", facing="right")
    d.add_master(name=f"Neue Musterseite {masters[1]}", facing="left")
    return d

def _add_left_page(d, **kwargs):
    return d.add_page(master=f"Neue Musterseite links", **kwargs)
def _add_right_page(d, **kwargs):
    return d.add_page(master=f"Neue Musterseite rechts", **kwargs)
```
Then test cases like:
- LEFT page with frame `x=0, w=210` → spine on RIGHT edge → flush →
  warning.
- LEFT page with frame `x=0, w=205` → 5mm gap from spine → no warning.
- RIGHT page with frame `x=0, w=210` → spine on LEFT edge → flush →
  warning.
- non-facing doc with frame `x=0, w=210` → no warning (early exit).
- LEFT page with `SpreadImage·left` (anname contains "Spread" or known marker)
  → no warning (intentional spread).

**Confidence:** HIGH — pattern matches existing test_constraints_inside_page.

---

### P-19. SpreadImage frames intentionally touch the spine — must be exempt from spine-safety

**What goes wrong:** `SpreadImage.emit()` produces two `ImageFrame` halves
each at `x_mm=0, w_mm=page_w_mm` on facing pages. The LEFT half on the
LEFT page touches the spine on its RIGHT edge by design (it's a SPREAD —
the image continues onto the next page). Spine-safety rule would flag both
halves as violations, defeating the purpose.

**How to avoid:** Per ISSUE.md Phase 4 the rule says "non-`SpreadImage`
ImageFrame". The rule needs a way to identify SpreadImage halves at check
time. Options:

1. **Anname pattern.** SpreadImage names them `f"{base} · left"` and
   `f"{base} · right"`. Detect via `re.search(r" · (left|right)$",
   anname)`. Brittle if base names contain " · " naturally.
2. **Pair detection.** A SpreadImage half has a partner on the adjacent
   facing page with the same `image=` field. The rule iterates
   `doc.pages`; for a flagged frame, check whether the adjacent page has
   another ImageFrame with `image == this.image` AND opposite side. If
   yes, both are spread halves; skip.
3. **Marker attribute.** Add `_is_spread_half: bool = False` to
   `_Frame`, set by `SpreadImage.emit()`. Cleanest but invasive (changes
   the dataclass).
4. **Check `local_offset_mm`.** SpreadImage right halves have
   `local_offset_mm=(-page_w_mm, 0)`. Right halves with this offset are
   spread halves. Doesn't catch left halves directly though.

**Recommendation:** Option 1 (anname pattern) for day 1 — simplest, no
changes to `_Frame`. Option 3 in a follow-up if pair detection becomes
needed for templates that use spread variants. Document the anname-pattern
escape clearly:
> Frames whose anname matches `r" · (left|right)$"` are treated as
> SpreadImage halves and exempted from `brand:spine_safety`. Use this
> suffix convention when authoring spreads outside the SpreadImage block
> too.

**Test coverage:** One spine-safety test where a frame has the SpreadImage
name pattern and gets exempted; one where it has a similar but
non-matching name and still gets flagged.

**Confidence:** MEDIUM — anname-pattern is fragile but matches the
SpreadImage block's emission convention; alternative (pair detection)
adds complexity. Planner can choose.

---

### P-20. `bin/audit-alignment` shim — what's the contract with the existing `bin/` scripts?

**What goes wrong:** ISSUE.md Phase 8 requires `bin/audit-alignment` for
ergonomics. Existing scripts in `bin/`:
- `bin/check-fontsizes` — likely a one-liner Python wrapper
- `bin/check-stale-previews` — same
- `bin/render-gallery` — same
- `bin/validate` — same

The convention isn't documented; the planner needs to inspect one to
match.

**How to avoid:** Read `bin/check-stale-previews` (smallest one likely)
and copy the pattern. Probably:
```bash
#!/usr/bin/env bash
exec env PYTHONPATH=tools python3 -m audit_alignment "$@"
```
or
```bash
#!/usr/bin/env bash
exec env PYTHONPATH=tools python3 tools/audit_alignment.py "$@"
```

Make sure the script is `chmod +x`. Test locally with
`bin/audit-alignment --all`.

**Confidence:** MEDIUM — convention is conventional, but verify by
reading an existing script before authoring.

---

## Security Concerns

This issue does not introduce new external inputs (no network, no user
data). The audit tool reads template build.py via importlib (already done
by structural_check; no new attack surface). `pdfimages -list` invocation
takes a controlled file path, not user input. **No new security concerns.**

**Confidence:** HIGH.

---

## Edge Cases

| # | Edge Case | Handling |
|---|-----------|----------|
| 1 | Frame with `anchor=None` AND `xpos_pt`/`ypos_pt` verbatim overrides | Per `_frame_bbox_mm` docstring (line 393-405): verbatim overrides are NOT honored; rule falls back to `*_mm`. Two known offenders use `x_mm`/`w_mm` directly so this is safe today. The audit MUST inherit the same limitation; if a future template uses verbatim overrides, both inside_page AND drift report stale positions. Planner should track in a follow-up. |
| 2 | Frame with `rotation_deg=360` | Mathematically same as 0; `_rotated_bbox` handles it (cos/sin produce identity). No special case needed. |
| 3 | Frame with `rotation_deg=89.5` (near-90 not exact) | `_rotated_bbox` computes via cos/sin — works for any angle. Bbox slightly larger than 90° case due to corner intrusion; this is correct geometry. |
| 4 | Frames with empty anname (`anname=""`) | Drop from pair iteration (per P-3 mitigation #3). They can't be referenced in CONSTRAINTS, so suggesting a skeleton is unactionable. Inside_page handles them (uses `<unnamed Polygon>` placeholder); drift skips. |
| 5 | Two pages same idx (shouldn't happen, but) | Iterate `doc.pages` order; idx is informational. No special handling needed. |
| 6 | Template has no CONSTRAINTS list | `getattr(mod, 'CONSTRAINTS', [])` returns []. Declared-pair set is empty. EVERY axis-near pair is flagged. Templates without CONSTRAINTS should opt out via `brand_overrides`. |
| 7 | Template with CONSTRAINTS that all reference missing annames | structural_check already emits "warning: references missing anname(s)" per constraint. Audit's declared-pair extractor works on the targets regardless of presence — pairs are still considered "declared". This is correct: a constraint declared for an anname that doesn't exist is the user's bug; the audit shouldn't compound by flagging the absent frame's neighbors as undeclared. |
| 8 | Two frames at exactly same position (pixel-perfect overlap) | `(P.x - Q.x) == 0` and `gap == 0` — the heuristic's lower bound (`> 0.5mm`) excludes this. Caller assumption: identical-position frames are intentional (e.g. SpreadImage halves on same page should never happen, but if they do, it's deliberate stacking). |
| 9 | A frame's bbox crosses page bounds but the frame is "intended bleed" | Already handled by `brand:inside_page` (severity warning if 0.5-1.0mm, error >1mm). Drift rule operates on bbox center / edge — page-bounds crossing doesn't change adjacency math. |
| 10 | `master_name` is an empty string OR contains both "links" and "rechts" | Regex `\b(links\|rechts)\b` returns the FIRST match. If both present, the first wins. Templates shouldn't name masters this way; audit can warn if `master_name` matches both. |

**Confidence:** HIGH (each case verified against source).

---

## Environment Availability

| Dependency | Required By | Installed (local) | Version | CI Available |
|------------|-------------|-------------------|---------|---------------|
| Python 3.13 | All | YES (`/usr/bin/python3 3.13.5`) | 3.13.5 | YES (apt python3) |
| `lxml` | sla_lib | YES | (system pkg) | YES (`python3-lxml`) |
| `PyYAML` | meta.yml + audit | YES (apt `python3-yaml`) | system | YES (`python3-yaml`) |
| `jsonschema` | meta_schema | YES (pip `4.26.0`) | 4.26.0 | YES (pip) |
| `poppler-utils` (pdfimages) | optional `--check-pdf` flag | YES (`/usr/bin/pdfimages 25.03.0`) | 25.03.0 | YES (apt `poppler-utils`) |
| Scribus 1.6.5 | render-gallery (regen step) | YES (`/usr/bin/scribus`, but needs Xvfb) | 1.6.x | NO — CI pages.yml uses pre-rendered baselines, NOT Scribus |
| Xvfb | Scribus headless | YES (`xvfb-run`) | system | NO (CI doesn't render) |
| Ghostscript | render pipeline | YES (`/usr/bin/gs 10.05.1`) | 10.05.1 | YES (apt `ghostscript`) |
| ImageMagick | visual_diff | (assumed yes; not probed) | n/a | YES (apt `imagemagick`) |
| `Pillow`, `qrcode`, `pyzbar` | tools/qr_gen.py (unrelated to this issue) | YES (pip) | 12.2.0/8.2/0.1.9 | YES (pip) |

**No new dependencies required.** All needed libraries already in the
toolchain.

**Bash command for env verification:**
```bash
python3 -c "import yaml, jsonschema, lxml; print('OK')" \
  && which pdfimages && pdfimages -v 2>&1 | head -1 \
  && which scribus && which gs
```

**Confidence:** HIGH (verified via Bash probes).

---

## Performance Notes

| Operation | Cost | Within Budget? |
|-----------|------|----------------|
| `_frame_bbox_mm` per primitive | O(1), ~5 µs | YES |
| Per-page pair iteration on Zeitung (~70 prims/page worst) | O(N²) = 2,400 pairs/page × 14 pages = ~34k pairs | YES (<200ms) |
| Across all templates `--all` | 8 templates × ~5k pairs = ~40k total | YES (<1s) |
| `pdfimages -list` on a 14-page Zeitung preview.pdf | ~5-10s | OK as opt-in flag |
| Full `audit_alignment.py --all --check-pdf` | 8 × 10s = ~80s | Acceptable for opt-in |
| Existing `structural_check --all` baseline | per pages.yml comment "<30s for all 8 templates" | New rules add ~1s — well within |

The audit's hot path is bbox computation, which is already used by
`brand:inside_page` without performance concerns. Adding two new BrandRules
on top doesn't change asymptotics. Confidence: HIGH.

---

## Sources

### HIGH confidence

- `tools/sla_lib/builder/brand_constraints.py` — read end-to-end. _Frame
  bbox helpers, _InsidePageRule pattern, BRAND_CONSTRAINTS registry.
- `tools/sla_lib/builder/document.py` — read carefully for Page, Document,
  facing_pages, master ordering, add_page is_left forcing, scratch-canvas
  layout. Key references: lines 120, 326, 366-393.
- `tools/sla_lib/builder/constraints.py` — read for Constraint dataclass,
  factory pattern, referenced_annames(), _AlignedBelowConstraint.
- `tools/sla_lib/builder/structural_check.py` — read for _load_build_module
  pattern, CONSTRAINTS evaluation flow, brand_overrides skip mechanism.
- `tools/sla_lib/builder/blocks.py` — SpreadImage at lines 681-740.
- `tools/sla_lib/builder/meta_schema.py` — schema, validate function,
  warning emission.
- `tools/sla_lib/builder/primitives.py` — Anchor + resolve_anchor (line 232).
- `tools/sla_lib/tests/test_brand_constraints.py` — line 50 nine-rules test.
- `templates/zeitung-a4-grun/build.py` — lines 32, 71-92, 94-233, 1802-1811,
  2542-2556 (facing config, masters, page order, P9 Spread, CONSTRAINTS).
- `templates/zeitung-a4-grun/meta.yml` — brand_overrides for inside_page +
  line_spacing_0.9 with the #39 dependency note.
- `templates/postkarte-a6-kampagne/build.py` line 425, `templates/plakat-
  a1-hochformat/build.py` line 254 — current single-witness CONSTRAINTS.
- `.github/workflows/pages.yml` lines 50-58, 130-156 — CI deps + structural
  check step.
- `Dockerfile.claude` lines 12-15, 51, 74-80 — Python deps, jsonschema 4.26.0.
- Local Bash probes: `pdfimages 25.03.0`, `Python 3.13.5`, `gs 10.05.1`,
  `xvfb-run` available, `yaml/jsonschema/lxml import OK`.

### MEDIUM confidence

- Composite-aware suppression list (P-7) — judgement call; depends on
  how the planner wants to handle ColumnTextStory adjacency floods.
- Suggested-skeleton format (P-14) — recommendation, not constrained by
  existing code.
- `bin/audit-alignment` shim contract (P-20) — convention inferred from
  existence of similar scripts; planner should verify by reading one.
- SpreadImage exemption strategy (P-19) — three options with tradeoffs;
  anname-pattern recommended but not the only valid choice.
- `audit_strict: true` future-state (P-13) — recommendation to defer.

### LOW confidence (needs validation)

- None significant. All major pitfalls are verified against source code.

---

## Summary table — top 10 pitfalls by impact

| # | Pitfall | Severity | Mitigation |
|---|---------|----------|------------|
| 1 | Audit reads raw `x_mm`/`y_mm` (anchor + rotation invisible) | CRITICAL | Reuse `_frame_bbox_mm` from brand_constraints.py |
| 2 | `Page.is_left` is broken on doc pages — must use master_name regex | CRITICAL | Word-boundary regex `\b(links\|rechts)\b` |
| 3 | False-positive explosion of drift rule | HIGH | Severity=warning + skip rotated/anonymous + per-template overrides for V1 templates |
| 4 | Declared-pair extraction misses multi-arity / single-arity / BrandRule | HIGH | itertools.combinations + frozenset symmetry + len>=2 guard + skip BrandRule |
| 5 | CI integration as fatal day-1 breaks every untouched template | HIGH | Wire as informational with `\|\| true`; promote to fatal in follow-up |
| 6 | `_load_build_module` sys.modules cache poisoning | MEDIUM | Reuse the existing helper with sys.modules.pop() |
| 7 | Test count `nine_rules_exact` will break | MEDIUM | Update test to 11 rules + canonical id set |
| 8 | brand_overrides schema warning when rule doesn't exist yet | MEDIUM | Sequence tasks: add rules to BRAND_CONSTRAINTS BEFORE V1 overrides |
| 9 | Closing #39 (u2950) prematurely sends CI red | MEDIUM | Sequence: trim u2950 → verify → remove override → verify --all → close #39 |
| 10 | SpreadImage frames need exemption from spine-safety | MEDIUM | Anname-pattern check `r" · (left\|right)$"` exempts SpreadImage halves |

---

## Open questions for planner

1. **Suppression of ColumnTextStory adjacency floods (P-7).** Default to
   noisy (let executor encode `equal_gap`)? Or build suppression-list
   infrastructure now? Recommendation: noisy; encode `equal_gap` per
   ColumnTextStory in zeitung CONSTRAINTS.
2. **`audit_strict: true` field (P-13).** Add now or defer to follow-up?
   Recommendation: defer.
3. **Refactor `_frame_bbox_mm` to public helper module (P-1, P-9).**
   Worth it for a 2-LOC import? Recommendation: yes — the underscore
   prefix lies (the helper IS the public bbox API for any new rule).
   Move to `tools/sla_lib/builder/template_loader.py` + a new
   `tools/sla_lib/builder/bbox.py`. Small refactor commit.
4. **Per-template override semantics for postkarte/plakat (P-15).** If
   per-template encoding is deferred to follow-up, do those templates
   need brand_overrides for `brand:undeclared_alignment_drift` too?
   Recommendation: yes, with reason "see #22 follow-up: per-template
   encoding pending."

---

## "What might I have missed?" review

- **Translation of German anname strings**: not a concern; annames are
  arbitrary strings handled byte-identically.
- **Float-imprecise drift in adjacency thresholds**: 5mm threshold is
  20× the ulp scale (~0.01mm). Float drift won't sneak past the threshold.
- **Threading/concurrency**: structural_check is single-threaded; audit
  follows. No race conditions.
- **Encoding errors in markdown report**: anname strings include UTF-8
  (German umlauts). Markdown handles UTF-8 by default; no special
  handling needed beyond `print()` to UTF-8 stdout.
- **Test runner double-evaluation**: unittest discovery doesn't share
  state between test modules; tests are independent.
- **`--all` flag conflict with structural_check vs audit_alignment**: both
  CLIs use `--all`. Different binaries, no conflict.
- **`gh issue close 39 --reason duplicate`**: requires the agent to have
  `gh` access. Already used elsewhere in the toolchain. Confirm during
  execution.
- **YAML quoting of brand_overrides reason text containing `#22`**: the
  `#` character starts a YAML comment OUTSIDE strings; INSIDE the existing
  `>-` folded block scalar pattern, it's safe. Already proven in the
  zeitung meta.yml `#39` reference.
- **MAP.md staleness**: no MAP.md exists in this worktree. Skipped.
- **CLAUDE.md**: no workspace CLAUDE.md exists at the repo root in this
  worktree. Skipped.
- **`.claude/skills/`**: directory does not exist. Skipped.

---

End of pitfalls research.
