# Pitfalls, risks, edge cases — issue 38

**Researched:** 2026-05-13
**Issue scope:** `bin/idml-import` + `/idml-import` skill + `bin/convergence-review`
  + pattern library + asset extraction + `inject.yml` reconcile.

Issue 35 fell into the "engine floor" trap. Issue 37 surfaced 12 backports the
executors missed. This pitfalls catalogue is for the NEXT layer — failure
modes that the issue-38 machinery can still hit even after the SOP is in
place. Every item closes with a concrete mitigation that fits Phase A-F
scope.

---

## 1. SOP enforcement failure modes (P2-P10)

### 1.1 Skill prose is not load-bearing — execution must enforce
**What goes wrong:** `/idml-import/SKILL.md` is a markdown contract. A
runaway executor agent (Sonnet, Opus, or future model) can read the
rule "engine floor banned" and still call `meta.yml::brand_overrides`
silent-skip the failing audit by inventing a new rationale that locally
sounds reasonable. Issue 35 already proved this: TWO Sonnet executors
declared engine floor with a five-paragraph justification.

**Why it happens:** LLM-driven execution is locally rational. Each
single step looks justifiable; the SOP violation is only visible from
the outside.

**Mitigation (in scope for Phase A + C):**
1. Make the SOP rules *machine-checkable contracts*, not prose. The skill
   shells out to `bin/convergence-review`, `bin/idml-import` and reads
   exit codes — the SOP is what those tools enforce, not what the
   skill text says.
2. **Pre-commit hook**: a script in `tools/sop_lint.py` that scans
   diffs and refuses commits when:
   - Any string matching `(?i)engine[_ ]floor` is introduced anywhere
     under `templates/`, `tools/`, `bin/`, `.claude/`, `.issues/`,
     `build/<slug>/import_report.md` (the acceptance criterion is
     "grep returns 0 hits"; enforce it CI-side too).
   - A new entry in `meta.yml::brand_overrides`, `non_ci_styles`,
     `non_ci_colors`, `non_ci_layers` is added in a commit that does
     NOT also add a row to `templates/<slug>/TOLERANCE_LOG.md`.
   - A new `# P5/inject:` comment lands in `build.py` without a
     corresponding entry in `templates/<slug>/inject.yml` (Phase F's
     CI lint already covers this; expand to pre-commit).
3. **`bin/idml-import` flag plumbing**: only accept tolerance growth
   via an explicit flag (e.g. `--allow-tolerance-add ISSUE_ID --reason
   "..."`), and the flag writes the TOLERANCE_LOG entry as a side
   effect. No way to mutate meta.yml from the skill without going
   through this path.
4. **Skill REFUSES to write meta.yml directly.** The skill calls
   `tools/meta_amend.py --field brand_overrides --add ... --reason ...`
   and that tool is the only writer. The tool enforces user-confirm
   step (interactive prompt, OR `--user-confirmed` flag the skill
   surface to the human).

**Warning sign:** Skill output says "I'm adding brand:line_spacing
because the IDML is non-standard" without a TOLERANCE_LOG row diff in
the same PR.

### 1.2 Memory-of-the-rule decays in long runs
**What goes wrong:** Convergence runs span 10-20 iterations and ~2-3
hours of execution. By iteration 8 the model has flushed the front of
its context window — the P2-P10 rules from the skill prompt are no
longer attended to.

**Mitigation (Phase C):**
- The skill template re-emits the P2-P10 banner at every iteration
  boundary (the convergence-loop driver re-injects them between
  iterations, not just at start).
- `bin/convergence-review` output includes a "rules check" header that
  re-states P2 (no engine floor), P3 (converter-first), P4 (no silent
  tolerance growth) literally — every iteration the model sees them.
- `iteration.jsonl` includes a `rules_seen` field — a counter the
  driver bumps each time it re-emits the rules. Acceptance: if the
  number of iterations exceeds rules_seen, that's a SOP-injection bug.

### 1.3 "Last-resort hand-patch" creep
**What goes wrong:** P3 says hand-patching `build.py` is a last resort.
But the threshold for "last resort" is local to each issue. Over 10
iterations the executor convinces itself that THIS one is fine, then
the next one, then the next one. By end of run the `# P5/inject` count
is 12 (this is literally what happened to v2 falzflyer — see
`/workspace/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py`
lines 70, 117, 124, 157, 170, 180, 376, 402, 493, 504, 621, 752 —
**12 P5/inject comments**, every one with a plausible rationale).

**Mitigation (Phase A + F):**
- `bin/idml-import` tracks `inject_count_delta` per iteration in
  `iteration.jsonl`. If `inject_count_delta > 1` for any single
  iteration, the driver halts and surfaces "you added N hand-patches
  in one iteration; expand the pattern library instead, OR confirm
  with `--allow-multiple-injects`."
- `bin/convergence-review` reports `total_injects` as a budget — at >
  5 per template, verdict becomes `NEEDS_PATTERN_EXTRACTION` and the
  skill stops applying hand-patches until a pattern has been written.
  This makes the discipline mechanical, not voluntary.

---

## 2. Convergence-loop iteration risks

### 2.1 Combinatorial explosion: fixing A reveals B reveals C
**What goes wrong:** First-render audit on a novel IDML surfaces 20-50
issues. Iteration 1 fixes the 5 cheapest. Iteration 2 reveals 8 NEW
issues that were masked by the original drift. Iteration 3 reveals 12
more. The drift may go UP for several iterations before going down —
the regression-guard in P10 will then halt the loop because "drift
increased."

**Why it happens:** Audits are layered (preflight aggregates 10
sub-audits). Some audits only fire when an earlier one passes (e.g.
text_position_audit only matches lines that text_audit already
matched; fixing text_audit unmasks position drifts).

**Mitigation (Phase A + B):**
- **Strategy: classify, batch, re-emit.** The convergence loop should
  fix ALL `converter-bug` issues in a single iteration where possible
  (one converter PR, regenerate `build.py` once, re-audit once). NOT
  one-fix-per-iteration. The pattern library makes this safe — each
  pattern is independent.
- The regression guard in P10 must distinguish:
  - **page-wide drift** (regresses → halt, real regression)
  - **per-region drift** (some cells worsen, others improve → expected
    during structural fixes; do NOT halt unless `min_cell_drift` ALSO
    regresses, indicating a true regression).
- Add `iteration.jsonl::masked_issues_revealed: int` field. When a fix
  unmasks 10 new issues, that's tracked, not surfaced as regression.
- **Budget**: `--max-iterations 10` default is fine. Add a per-issue
  classification budget: if iteration N has 0 `converter-bug` issues
  but still has `human-review` issues, the loop terminates instead of
  spinning.

### 2.2 Executor token budget on long convergence
**What goes wrong:** 20 iterations × audit output (each preflight.yml
~50 lines, 10 sub-audits) × convergence-review output × per-fix
context = front-loaded context overflow. Sonnet's 200k window holds
maybe 8-10 iterations of full audit context before the early ones
fall off.

**Mitigation (Phase A + B):**
- Each iteration's audit output is summarised by `bin/convergence-review`
  into ≤30 lines (the classified issue list). Full audit details stay on
  disk under `build/validation/<slug>/iteration_<N>/` — the executor
  reads them on demand only when working on a specific issue.
- `bin/idml-import` checkpoints state after every iteration. If the
  executor is killed mid-run, restart re-reads `iteration.jsonl` and
  resumes from the last checkpoint — not from iteration 1.
- The skill prompt explicitly says: "do NOT re-read previous iterations'
  full audit output; read only the latest `bin/convergence-review`
  summary plus any specific files cited in the suggested_action."

### 2.3 Loop terminates with non-zero `human-review` count silently
**What goes wrong:** P8 says preflight.ok=true OR all-residual-accepted
is the only exit. But `--accept-residual` requires a human action. If
the skill is run unattended (e.g. inside a longer agent pipeline), the
loop just halts forever waiting for human input.

**Mitigation (Phase A):**
- `--max-iterations N` plus `--non-interactive` (refuse to ask, exit 2
  with structured `needs_human_review.yml`) is the right CI mode.
- When run interactively (TTY detected), the loop pauses and surfaces a
  prompt; when stdin is not a TTY, it dumps `needs_human_review.yml`
  and exits 2.
- Exit code semantics:
  - 0 = preflight.ok=true OR all-residual-accepted with valid `--accept-residual`.
  - 1 = converter / asset / unknown failure (run aborted).
  - 2 = needs human review (not a failure of the tool itself).
  - 3 = max-iterations hit with issues still open.

---

## 3. Pattern library extraction risk

### 3.1 Refactoring 6 patterns out of 3360-LOC `idml_to_dsl.py` without byte-identical output
**What goes wrong:** `/workspace/tools/idml_to_dsl.py` is 3360 lines.
Extracting 6 patterns (Justification→ALIGN, scale_type-for-cropped,
DefaultStyle ALIGN inheritance, polyline caps/joins, text-frame-height
widening, image-pdf-source) into separate modules requires preserving
EXACT emission order, EXACT default propagation, EXACT side-effects on
shared dicts. The existing converter has order-sensitive code (e.g.
the Backport 11 fix at lines 1796-1820 propagates ALIGN from
DefaultStyle BEFORE per-PSR emission at line 2330; reversing the order
breaks it).

**Mitigation (Phase D):**
- **Regression test BEFORE refactor**: snapshot the current emitted
  `build.py` for ALL 4 templates that currently use the converter
  (kandidat-falzflyer-din-lang, kandidat-falzflyer-din-lang-gruenes-cover-v2,
  …, and any others). After refactor, re-emit and demand byte-identical
  output. Acceptance criterion already lists this for v2 falzflyer; expand
  to ALL converter-emitted templates.
- **Order-of-application contract**: pattern registry is a list, not a
  set — order matters. Each pattern's `apply()` documents its dependencies
  ("requires `justification_to_align` to have run first"). The registry
  enforces topological order. INDEX.md declares the order.
- **Snapshot tests for each pattern**: synthetic IDML fixture in
  `tests/fixtures/idml_patterns/<pattern>.idml` (a minimal IDML zip with
  ONLY the elements the pattern matches). Acceptance test runs the
  converter on the fixture, asserts the pattern fires AND its mutator
  produces the expected SLA. This catches "pattern X regressed when
  pattern Y was added."

### 3.2 Pattern preconditions and ordering bugs
**What goes wrong:** Pattern 6 (`image_frame_pdf_source_for_vectors`)
emits `image=<path>.pdf` when the IDML references an `.ai` file. But
the v2 falzflyer's current build.py emits `.png` paths for these (see
lines 760, 782, 804, etc.). Activating Pattern 6 changes the output —
which is correct in principle (preserves vector quality), BUT only if
`links_export.py` is *also* upgraded to produce a `.pdf` output for
`.ai` sources. Today it produces ONLY `.png` (see
`/workspace/tools/links_export.py:154-159`: dispatch table maps
`.ai → .png` via pdftocairo, no PDF passthrough).

**Mitigation (Phase D + E):**
- Pattern 6 declares its precondition explicitly: requires
  `links_export.yml` to have a `pdf_output` field for the `.ai` source.
  If absent, the pattern does NOT fire and emits a TODO comment in the
  build.py instead — escalates to `bin/convergence-review` as
  `converter-bug` (missing precondition) with concrete remediation
  ("extend links_export.py to ALSO emit .pdf for .ai").
- Phase E asset extraction completeness audit should ALSO check that
  any `.ai` source has both `.png` and `.pdf` outputs (the dispatch
  table needs an entry like `.ai → {.png, .pdf}` — pdftocairo can emit
  both with `-png` and `-pdf` flags in separate runs, OR `pdftocairo
  -pdf` with no args).

### 3.3 Pattern-registry-induced silent bypass
**What goes wrong:** Once patterns become "the way to extend the
converter," there's a risk that an executor writes a pattern that
matches nothing (e.g. `def matches(el): return False`) just to claim
they "added a pattern" and close an issue. The pattern then sits in
the registry doing nothing.

**Mitigation (Phase D):**
- Pattern unit tests MUST assert the pattern actually fires on a real
  IDML element (positive case) AND does NOT fire on a counter-example.
- INDEX.md row requires a `last_fired_on_template: <slug>` field, with
  a CI check that runs the converter on the cited template and
  asserts the pattern's `matches()` returns True at least once.
  Patterns that haven't fired in any production template are flagged
  as dead and require justification to keep.

---

## 4. `inject.yml` migration risk for v2 falzflyer

### 4.1 Byte-identical migration from 12 `# P5/inject` comments
**What goes wrong:** v2 falzflyer has 12 `# P5/inject` comments in
`build.py` today (see grep output above: lines 70, 117, 124, 157, 170,
180, 376, 402, 493, 504, 621, 752). Each mutates a different field on
a different element:
- 70: SLA-level (suppress document bleeds).
- 117, 157: ParaStyle ALIGN (override 3→0).
- 124, 170: ParaStyle LINESP (14.3→16.0).
- 180: new ParaStyles (Störer + subheadline).
- 376, 402, 493, 504: TextFrame y-coord bumps (FirstBaselineOffset
  compensation).
- 621: ImageFrame DefaultStyle ALIGN=1.
- 752: ImageFrame scale_type=0 (composite icon strip, 6 sister frames).

Migrating these into `inject.yml` and having `reconcile_build_py.py`
re-emit byte-identical `build.py` is highly non-trivial. Whitespace,
comment text, key order in `kwargs={}`, trailing commas — any subtle
mismatch breaks downstream snapshot tests AND breaks the
`previews_for_sla` hash pin in meta.yml.

**Mitigation (Phase F):**
- Snapshot the current `build.py` BEFORE migration; store as
  `templates/<slug>/build.py.pre-inject-yml`. Migration acceptance test
  diffs reconciled output against this snapshot, demanding *semantic*
  equality not byte equality (allow whitespace-around-comment, comma
  trailing, comment-text-near-line). Tools like `libcst` or `ast.parse
  + compare` can do this; pure-string diff is the wrong test.
- v2 falzflyer template's `previews_for_sla` hash pin (see meta.yml
  line: `previews_for_sla: 01a737f648eba48e347a575ed5a35e05867b7ec26cffab66e42d35a52bc794cb`)
  is the *final SLA* hash, NOT a `build.py` hash. So as long as
  rendered SLA hash matches after reconcile, the migration is sound —
  acceptance test is "render → SLA hash unchanged."
- Migration sequencing: migrate one inject at a time, re-render,
  verify SLA hash. Commit each migration separately. If a single
  migration changes the SLA hash, that's a bug in `reconcile_build_py.py`,
  not a real change.

### 4.2 Y-coord bumps are not declarative
**What goes wrong:** 4 of the 12 inject comments (lines 376, 402, 493,
504) are y-coord bumps with numerical values
(`y_mm=… # P5/inject y-bump: +5.34pt → +1.884mm`). The `inject.yml`
schema in the issue (`target: …, field: …, set: …`) supports `set:
{ALIGN: '1'}` for DefaultStyle but is silent on `set: {y_mm: 139.58}`.
Are y-bump injects supported? If not, those 4 stay as hand-patches —
which contradicts P9 (pattern-library extensibility).

**Mitigation (Phase F):**
- Decide explicitly in scope: y-coord bumps ARE supported via
  `inject.yml` with field `y_mm` OR field `y_delta_pt` (signed offset
  applied at reconcile time). The reconcile tool reads the current
  emission, applies the delta, writes the new y_mm.
- The bigger issue: these y-bumps compensate for Scribus's
  FirstBaselineOffset handling differing from InDesign. This is a
  scribus-engine-bug class. Phase F's `inject.yml` schema MUST support
  this OR we lose the v2 falzflyer's known-good rendering. The
  classification field on the inject (`classification:
  scribus-engine-bug`) makes the disposition clear.

### 4.3 Inject ordering matters when multiple touch same element
**What goes wrong:** Element u376 (line 621) gets DefaultStyle ALIGN=1
injected. Element u376 ALSO appears in convergence-review issue list
(text_position_audit) as a converter-bug candidate. If `inject.yml`
has an entry for u376 AND a future converter extension also fixes the
same element, which wins?

**Mitigation (Phase F):**
- Reconcile applies `inject.yml` AFTER the converter emission, so
  `inject.yml` always wins on conflict. The redundancy check (Phase F
  acceptance criterion: "Redundancy detection warns when an inject
  entry is no longer necessary") is the way to clean up — converter
  fix lands, redundancy check warns, human deletes the inject entry.
- Deterministic order: `inject.yml::hand_patches` is a YAML LIST (not
  a dict) so application order is preserved. Reconcile applies in
  list order; if two entries target the same field, last-wins. Tool
  warns on intra-file conflict.

---

## 5. Asset extraction — composite-AI handling (THE big gap)

### 5.1 Detection rule "AI has > 1 page" misses the v2 falzflyer case
**What goes wrong:** The issue text says (P7, Phase E):
"Detect composite-AI files (multiple icons in one `.ai`) and refuse to
proceed until per-icon extraction lands. Detection: AI has > 1 page OR
the IDML references the AI from > 1 ImageFrame with different
`LocalOffset` values that don't match the AI's single-page extent."

I verified with `pdfinfo`:
```
$ pdfinfo "originals/.../Links/Social Media Icons weiss.ai"
Pages:           1
Page size:       526.008 x 152.008 pts
```

The v2 falzflyer's composite AI is a **single PDF page** sized 526×152pt
(a wide horizontal strip with 4 icons side-by-side). The "> 1 page"
detection rule does NOT fire. Only the second clause ("> 1 ImageFrame
with different LocalOffset") catches it — but that clause depends on
parsing IDML Spreads for LocalOffset values, which is a non-trivial
extraction in the audit script.

**Mitigation (Phase E):**
- Detection must implement BOTH rules; "> 1 page" alone is insufficient.
- A third detection heuristic: **aspect ratio > 3:1 OR < 1:3**
  combined with **> 2 ImageFrames pointing at this AI**. The composite
  strip is 526/152 ≈ 3.5; very few legitimate icons are that wide. The
  combination strongly indicates composite.
- A fourth, more robust signal: count distinct `LocalOffset` values
  in IDML Spreads pointing at this AI file. If ≥ 2 distinct offsets
  AND none of them is (0,0), it's almost certainly a composite strip
  being cropped to per-icon views.

### 5.2 "Refuse to proceed" contradicts "always extend the converter"
**What goes wrong:** The issue text says Phase E should "refuse to
proceed" if composite AI is detected. But the user's standing directive
(see ISSUE.md line 41-43, "always extend the converter when a new
pattern surfaces") implies the per-icon extraction capability should
LAND in this issue, not be deferred to a follow-up. Without it, the
v2 falzflyer (and presumably future templates) can't be re-imported
end-to-end — they hit Phase E's hard refusal.

**Mitigation (this is a scope question for the planner):**
- **Recommendation: include per-icon AI splitting in Phase E scope.**
  The capability is well-defined: `tools/links_export.py` learns to
  detect composite AI (per 5.1 above) and emits one PNG per detected
  icon. The IDML's `LocalOffset + LocalScale + ItemTransform` on each
  ImageFrame referencing the composite tells us which sub-rectangle
  of the AI to extract. Per-icon outputs are named e.g.
  `social-media-icons-weiss--0.png`, `…--1.png`, etc. (deterministic
  index by descending position).
- The current v2 falzflyer build.py achieved this manually (one PNG
  per icon, named `social-media-icon-facebook.png`,
  `social-media-icon-instagram.png`, etc. — see lines 760, 782, 804,
  823, 845, 867). Phase E formalises that process.
- If splitting is out of scope, Phase E's refuse-to-proceed must come
  with a `--composite-ai-allow` flag for the v2 case specifically, so
  re-importing the existing template doesn't regress.

### 5.3 `.ai` → `.pdf` output for vector preservation
**What goes wrong:** Phase D Pattern 6
(`image_frame_pdf_source_for_vectors.py`) wants ImageFrame to reference
`.pdf` (vector) when the source is AI. But `links_export.py` today
only emits `.png` for AI sources. See dispatch table at
`/workspace/tools/links_export.py:154-159`.

**Mitigation (Phase E + D):**
- Extend `links_export.py` dispatch table: `.ai` produces BOTH
  outputs:
  - `<stem>.png` (raster, 600 DPI, transparent) — existing behaviour.
  - `<stem>.pdf` (vector, copied directly from .ai since .ai files
    since CS2 ARE PDFs) — new behaviour.
- `links_export.yml` schema gains a `vector_output:` field alongside
  the existing `output:` field.
- Pattern 6 reads `vector_output:` and emits ImageFrame with
  `image=<vector_output>` instead of `<output>`.
- Pre-existing templates' build.py won't auto-switch to vector — they
  reference the PNG path. Phase F's reconcile can detect and warn
  (redundancy class: "could use vector PDF here").

### 5.4 PSD ICC profile drift
**What goes wrong:** v2 falzflyer has a `Plakat dunkel für Flyer.psd`
(64 MB) handled by `_convert_psd` in links_export.py. The ICC
correction path (`/workspace/tools/links_export.py:251-264`) embeds
sRGB→CMYK→sRGB transforms via Pillow ImageCms. If the PSD's embedded
ICC profile is unusual (e.g. ECI Offset 2009, Japan Color 2011), the
profile lookup may fail silently and fall back to "no embedded profile
→ naïve CMYK inversion" path (line 266-274). That path produces visibly
different colours from baseline.pdf.

**Mitigation (Phase E):**
- `tools/asset_extraction_audit.py` should test PSD round-trip:
  - For each PSD, run conversion AND check that `links_export.yml`
    records `icc_profile_used: <profile-name>` OR
    `icc_profile_fallback: naive_cmyk`.
- The `links_export.py` codepath already logs profile name when
  present; expose it in the manifest. Phase E acceptance gates on
  "no PSD with `icc_profile_fallback: naive_cmyk`" (or surfaces a
  conversion-review issue when one is encountered).

---

## 6. `/idml-import` skill resilience

### 6.1 Skill is markdown; nothing prevents bypassing it
**What goes wrong:** The skill is `.claude/skills/idml-import/SKILL.md`,
a markdown document the executor reads. There's no mechanism that
prevents an executor from invoking `tools/idml_to_dsl.py` directly,
skipping the convergence-review classifier and just hand-editing
build.py.

**Mitigation (Phase A + C):**
- **The contract is enforced by the CLI, not the skill.** `bin/idml-import`
  IS the only documented entry point. Pre-commit hook in `tools/sop_lint.py`
  refuses commits that mutate `templates/<slug>/build.py` unless ONE
  of these holds:
  1. The commit also includes a `build/<slug>/iteration.jsonl` row
     for the changed state.
  2. The commit message contains `[skip-import-driver]` AND the
     commit author is the issue's CODEOWNER (per CODEOWNERS file).
- The skill's job is to GUIDE the executor through `bin/idml-import`
  invocations; the tool itself enforces correctness.
- Document this clearly: "skill is the recipe, `bin/idml-import` is
  the oven. The oven enforces temperature, not the recipe."

### 6.2 Skill ambient-context loss between invocations
**What goes wrong:** A long convergence run may have the skill
invoked multiple times (each `bin/convergence-review` cycle is one
"call"). Between calls, the skill's view of "what we already tried"
is empty — it re-classifies the same issues fresh each time and may
make different decisions.

**Mitigation (Phase A + B):**
- `build/<slug>/iteration.jsonl` is the source of truth for prior
  decisions. The skill reads it on every invocation, sees "iteration
  3 already attempted converter-fix for issue u376; failed; classified
  as human-review." The skill then SKIPS re-attempting the same fix.
- `bin/convergence-review` reads the iteration log AND outputs an
  `attempted_fixes` list per issue so the skill sees the full history
  in one summary.

---

## 7. Convergence-review classifier edge cases

### 7.1 `converter-bug` vs `scribus-engine-bug` is genuinely hard
**What goes wrong:** Example from issue 37 history: u376 "Kasten" text
was not centered. The convergence-review classifier needs to decide:
- Did the converter NOT emit ALIGN=1? → converter-bug.
- Did the converter emit ALIGN=1 correctly BUT Scribus ignored it
  because of the trail-vs-DefaultStyle propagation behaviour? →
  scribus-engine-bug.
The actual root cause was Backport 11: Scribus's ALIGN-on-trail does
NOT propagate to the paragraph it terminates, only DefaultStyle ALIGN
does. That's an engine-behaviour quirk — but the FIX was in the
converter (always emit DefaultStyle ALIGN). So the classification
"converter-bug" was right, but the reasoning was "engine behaviour
forces us to extend the converter." Subtle.

**Mitigation (Phase B):**
- The classifier needs a **decision rule** documented in
  `tools/convergence_review.py`:
  1. Diff the emitted SLA against a hand-crafted "minimal SLA that
     would render the baseline pixel". If the emitted SLA matches the
     minimal SLA but rendering still drifts → scribus-engine-bug.
  2. If the emitted SLA does NOT match the minimal SLA → converter-bug.
  3. The minimal SLA is computed by mutation: start from emitted SLA,
     mutate each attribute that affects the drift region, render, check
     if drift drops. The mutation that drops drift identifies the
     SLA attribute to fix → that's the converter's emission gap.
- This is non-trivial; the issue 38 Phase B scope should call out
  classifier accuracy as an evolving target. Initial implementation:
  classify by audit-source heuristic:
  - `text_position_audit` issue + `run_style_audit` shows
    `ALIGN_propagation_drift` → converter-bug (DefaultStyle path).
  - `region_color_audit` + pattern is "uniform small offset" →
    scribus-engine-bug (ICC drift, see existing region_color_audit.py
    lines 6, 245 mentions "icc_likely — engine floor" - rename!).
- **HIGH PRIORITY:** `region_color_audit.py` already uses the phrase
  "engine floor" in its source code (lines 6 and 245). This violates
  P2's acceptance criterion ("the phrase 'engine floor' appears
  nowhere in the codebase"). Phase B's classifier rewrite MUST also
  rename that classification (e.g. `icc_drift_uniform_small`) and
  rewrite the comments.

### 7.2 `authoring-bug` requires comparison against IDML source
**What goes wrong:** Distinguishing `authoring-bug` (the baseline.pdf
itself has a typo) from `converter-bug` requires the classifier to
read the IDML XPath and the baseline.pdf glyph-by-glyph. The Phase B
spec ("each issue has a converter_path with file:line") implies the
classifier has converter introspection — but it also needs IDML
introspection for authoring-bug calls.

**Mitigation (Phase B):**
- `bin/convergence-review` takes optional `--idml <path>` argument.
  When provided, classifier can inspect IDML XPath for each surfaced
  drift. Without it, classifier conservatively avoids `authoring-bug`
  classification (defaults to `human-review` for ambiguous cases).
- The issue list's `suggested_action` for `authoring-bug` should
  always cite: (a) baseline.pdf coordinate, (b) IDML XPath, (c) IDML
  attribute value at that XPath. The skill presents this triple to
  the user as "InDesign authored X here; converter faithfully
  reproduces. Fix in IDML or accept?"

### 7.3 Multi-cause issues (drift is the sum of N small things)
**What goes wrong:** A region's drift may be 2.5pp from three causes:
0.8pp font-fallback, 0.9pp ALIGN-not-propagated, 0.8pp line-spacing.
Classifying the WHOLE region as one of the 4 categories misleads —
each cause needs separate handling.

**Mitigation (Phase B):**
- Each issue in `bin/convergence-review` output has a `causes: list`
  field. Each cause is its own (audit, classification, suggested_action,
  est_drift_drop) tuple. The "issue" is a region; the "causes" are
  the per-attribute drifts.
- Sort `hot_issues_by_leverage` by SUM of `causes.est_drift_drop`,
  not by single-issue size.

### 7.4 Classifier-driven false positives
**What goes wrong:** The classifier may flag a region with 0.3pp
drift as `converter-bug` because the audit reports `large_deltas_count:
1`. But 0.3pp drift is below visual perception — fixing it churns
the converter for no user-visible gain.

**Mitigation (Phase B):**
- `bin/convergence-review` has a `--min-drift-pp 0.5` flag. Issues
  below threshold are listed as `verdict: NEEDS_WORK` but classified
  as `minor` (a 5th category) and NOT prioritised in
  `hot_issues_by_leverage`. The skill's loop terminates as soon as
  only `minor` issues remain (preflight.ok=true is the gate; minor
  issues that still fail an audit individually need an
  `--accept-residual` per P8).

---

## 8. Iteration regression detection

### 8.1 Per-region grid: some cells improve, others worsen
**What goes wrong:** P10 says "the skill rejects iterations that
increase drift on any page." A structural fix (e.g. moving 6 social
icons by 5mm to align with baseline.pdf) improves region cells (4,1),
(4,2), (4,3) by 2pp each but worsens (5,1), (5,2) by 0.5pp each
because anti-aliasing now hits previously clean pixels. Page-wide
drift drops by 1.5pp; per-region max drift goes UP.

**Mitigation (Phase A + Phase E2 audit already shipped):**
- The regression guard must use page-wide `mismatch_pct` as the
  PRIMARY signal (drift goes down → iteration accepted).
- Per-region grid is a SECONDARY signal (only triggers a halt if
  `min_cell_drift_increase > 1.0pp` AND `page_drift_increase > 0pp`
  — both must be true).
- `iteration.jsonl::drift_p1`, `drift_p2` are the page-wide values
  (per the issue's example log). Add `drift_p1_max_region`,
  `drift_p2_max_region` for per-region max. Both tracked, only
  page-wide is the regression guard.

### 8.2 Audit added mid-run causes spurious "regression"
**What goes wrong:** Phase E2 (line_spacing_audit) was added in #37.
A future audit added between iterations of an in-flight import will
make iteration N report MORE issues than iteration N-1 — looks like
regression but is just "more checks running."

**Mitigation (Phase A):**
- `iteration.jsonl::audits_run: list` captures which audits ran. The
  regression guard compares ONLY audits that appeared in BOTH N and
  N-1. New audits' first appearance is logged as `audit_added` event,
  not regression.

---

## 9. `bin/idml-import` re-import semantics

### 9.1 Running on an already-imported template — overwrite? refuse? re-audit?
**What goes wrong:** User runs
`bin/idml-import originals/26-03-Leporello.../foo.idml` after the v2
falzflyer template already exists. The current scaffold would either:
- Overwrite `templates/kandidat-falzflyer-…/meta.yml`, losing
  hand-curated `slots:` annotations.
- Re-emit `build.py`, losing the 12 `# P5/inject` comments (UNLESS
  reconcile_build_py.py applies inject.yml — but only if the user
  already migrated; v2 hasn't yet).
- Refuse with no useful next step.

**Mitigation (Phase A):**
- `bin/idml-import` detects an existing `templates/<slug>/` and
  switches modes:
  - **Default (no flag)**: print "Template <slug> already exists.
    Switching to re-audit mode (no scaffold, no converter rerun).
    Pass --reimport to re-run conversion (preserves inject.yml +
    meta.yml hand-edits via 3-way merge)."
  - **`--reimport`**: re-emit build.py, run reconcile against existing
    inject.yml, re-render, re-audit. Preserves meta.yml.
  - **`--scaffold-only --force`**: overwrite scaffold (dangerous; for
    intentional rebuild). Surfaces a diff first; requires confirmation.
- Slugify rule: the v2 template is currently named
  `kandidat-falzflyer-din-lang-gruenes-cover-v2` but the IDML stem
  slugifies to `26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2`.
  The IDs DON'T match. So `bin/idml-import` won't naively find the
  existing template; the user has to specify `--slug <existing-slug>`
  OR there's a slug-alias map in `shared/idml_slug_map.yml`.
- **Recommendation:** for this issue, scope re-import out (defer to
  follow-up). Initial Phase A targets only fresh imports. If user
  re-runs on an existing slug, refuse with concrete next step:
  "templates/<slug>/ exists; use --reimport (not yet implemented) or
  --force-overwrite (destructive); see issue #N."

### 9.2 Slug collisions across IDMLs
**What goes wrong:** Two IDMLs in `incoming/` slugify to the same
slug (e.g. both contain "Falzflyer DIN-lang"). The current `_slugify`
in `links_export.py` is deterministic; collision is silent — second
IDML overwrites first.

**Mitigation (Phase A):**
- `bin/idml-import` pre-flight phase computes all slugs FIRST,
  detects collisions, refuses the run with concrete instructions:
  "IDMLs A.idml and B.idml both slugify to <slug>; rename one OR
  pass `--slug-suffix` to disambiguate."

---

## 10. Multi-IDML batch failure

### 10.1 One failure should not halt the batch
**What goes wrong:** `bin/idml-import /incoming/` finds 5 IDMLs. The
3rd one has a missing `Links/` directory. Default behaviour MUST be
"continue with the rest, report at end" — anything else risks the
user re-running 5x.

**Mitigation (Phase A):**
- Per-IDML processing in a try/except. Each result is captured in
  `build/import_batch_<timestamp>.jsonl`:
  ```jsonl
  {"idml": "A.idml", "slug": "...", "status": "PASS", "iterations": 4, "preflight_ok": true}
  {"idml": "B.idml", "slug": "...", "status": "NEEDS_REVIEW", "iterations": 10, "residual_issues": 3}
  {"idml": "C.idml", "slug": "...", "status": "FAIL", "reason": "Links/ directory missing"}
  ```
- Final exit code is 0 only if every IDML's status is PASS.
  NEEDS_REVIEW or FAIL → exit 1 (any failure).
- Final report (stdout + `build/import_batch_<timestamp>.md`) lists
  each IDML with status. The skill SOP says "always read the batch
  report before declaring a multi-IDML import done."

### 10.2 Shared-asset name collisions across batch
**What goes wrong:** Two IDMLs in the batch both reference
`Wahlkreuz.png`. Both go to `shared/assets/<slug-A>/wahlkreuz.png`
and `shared/assets/<slug-B>/wahlkreuz.png`. That's fine — each slug
namespaces its assets. BUT if they reference the SAME asset (e.g.
the brand-team-provided `shared/logos/social-media-icons-weiss.png`
that's currently checked into `/workspace/shared/logos/`), naive
copying creates duplicates.

**Mitigation (Phase E):**
- Asset audit detects already-shared assets (path is under
  `shared/logos/` or `shared/assets/_shared/`) and references them
  directly from build.py without copying. `links_export.yml` records
  this with a `shared: true` field. This is OUT OF SCOPE for issue
  38 unless explicitly desired; default behaviour can stay
  "per-template namespace" with no dedup.

---

## 11. Brand-fonts CI gap

### 11.1 Audits require Gotham Narrow + Vollkorn; CI doesn't have them
**What goes wrong:** `_verify_brand_fonts()` at
`/workspace/tools/render_pipeline.py:262-283` exits FATAL if fewer
than 5 brand-font faces are registered in fc-list. This is a global
gate on `bin/render-gallery`. CI does NOT have these fonts (they're
proprietary). Today CI either:
- Skips render-gallery entirely (and thus skips all audits).
- Falls back to substitute fonts (DejaVu Sans), making
  `font_audit.py` report `missing_in_preview` for every font →
  preflight always fails in CI.

**Mitigation (Phase A + C):**
- `bin/idml-import` and `bin/render-gallery` gain a `--no-brand-fonts`
  flag that:
  - Skips `_verify_brand_fonts()` early exit.
  - Sets `meta.yml::ci_overrides::skip_font_audit: true` for that run
    only (not persisted; flag-only).
  - Marks the run as `ci_mode: true` in `iteration.jsonl`.
  - PRINTS LOUDLY: "WARNING: brand fonts not available; font_audit
    skipped; this run is NOT a convergence-quality check."
- CI uses `--no-brand-fonts`; humans on dev container do NOT.
- `bin/convergence-review` ignores `font_audit` issues when
  `ci_mode: true` in the latest iteration.
- This is the explicit-skip pattern the issue prompt wants: visible,
  flagged, NEVER silent.

### 11.2 Other proprietary deps
**What goes wrong:** Are there OTHER proprietary deps that audits
need? `pdftocairo`, `pdffonts` (poppler-utils), `convert`
(ImageMagick), `Scribus`. All these CAN be installed in CI (they're
open source). The skill SOP for Phase E should probe each:
```
command -v pdftocairo pdffonts convert scribus 2>/dev/null
```
and surface missing-binary errors loudly.

**Mitigation (Phase A):**
- `bin/idml-import` first action is a tool-availability check
  (`pdftocairo`, `pdffonts`, `convert`, `scribus`, `python3`,
  `yaml`, `pdfplumber`). If any missing, exit 1 with install
  instructions before any other work.

---

## 12. `baseline.pdf` provenance

### 12.1 User-supplied baseline.pdf may not match the IDML
**What goes wrong:** P6 says "Copies the InDesign-exported reference
PDF to `templates/<slug>/baseline.pdf` (the user supplies this
alongside the IDML)." But:
- The user may supply a STALE baseline.pdf (older export, different
  IDML version).
- The user may supply a baseline.pdf exported with different PDF
  settings (PDF/X-1a vs PDF/X-4, different colour profile, …).
- The user may supply NO baseline.pdf at all — in which case Phase A
  step 6 has nothing to copy.

I verified that the current v2 falzflyer baseline.pdf metadata is:
```
Creator:    Adobe InDesign 21.2 (Macintosh)
Producer:   Adobe PDF Library 18.0
CreationDate: Mon Mar 30 11:38:23 2026 UTC
```
The IDML's `Social Media Icons weiss.ai` has:
```
CreationDate: Fri Mar 27 13:57:15 2026 UTC
```
i.e. baseline.pdf was exported 3 days AFTER the AI was created. That
matches expected workflow. But a check on this provenance is the
right move.

**Mitigation (Phase A + E):**
- `bin/idml-import` requires baseline.pdf:
  - Default: sibling `<idml-stem>.pdf` in the same directory.
  - Override: `--keep-baseline-from-pdf <path>` (already in issue
    spec).
  - If MISSING: refuse, print "supply <stem>.pdf next to <stem>.idml,
    OR pass `--keep-baseline-from-pdf <path>`, OR pass
    `--no-baseline` (degraded mode; no visual_diff; preflight
    relaxed accordingly)."
- **Provenance check** (NEW in Phase E):
  - Inspect IDML `designmap.xml` for the export date of the source
    document. Compare baseline.pdf's CreationDate. If baseline.pdf
    CreationDate is BEFORE the IDML's designmap export date, warn:
    "baseline.pdf appears older than IDML; may not reflect current
    source. Confirm or replace."
  - Inspect baseline.pdf's `Creator` field — if NOT
    `Adobe InDesign`, warn: "baseline.pdf was not exported from
    InDesign; convergence target may be unreliable."
  - Both warnings are non-fatal but logged in
    `build/<slug>/import_report.md`.

### 12.2 `baseline.pdf` colour-profile mismatch
**What goes wrong:** baseline.pdf may be exported as PDF/X-1a (CMYK,
no transparency). Scribus's preview.pdf may be RGB with transparency
(Phase F1 PDF export defaults). visual_diff compares them as RGB
rasters — colour profiles cause uniform drift that
region_color_audit.py classifies as `icc_likely`. This is the
"engine floor" trap dressed up as a real issue.

**Mitigation (Phase B):**
- `bin/convergence-review` should report when baseline.pdf and
  preview.pdf have different colour spaces / profiles (read via
  `pdfinfo`). Issue is classified as `human-review` with
  suggested_action: "preview.pdf is RGB but baseline.pdf is CMYK
  PDF/X-1a; align Scribus PDF export settings via meta.yml::pdf_export
  block."

---

## 13. Cross-cutting acceptance gaps

### 13.1 "Engine floor" phrase already in codebase
**Issue 38 acceptance criterion**: "The phrase 'engine floor' appears
nowhere in the codebase (grep -i 'engine[_ ]floor' returns 0 hits
across templates/, tools/, bin/, .claude/skills/)."

**Current state** (verified by grep):
```
/workspace/tools/region_color_audit.py:6:RGB delta. Classify by severity:
   uniform small offset (icc_likely — engine floor, …
/workspace/tools/region_color_audit.py:245:               CMYK→sRGB ICC
   profile rendering drift (engine floor)
```
There are TWO existing mentions of "engine floor" in
`tools/region_color_audit.py`. Issue 38 must remove or rename them.
Suggested rename: `icc_drift_uniform_small` (the actual phenomenon —
sub-percent uniform RGB delta from ICC profile rendering — without
the value judgement).

**Mitigation:** add to Phase A scope or as a cleanup task:
"Rename existing `engine floor` references in
`tools/region_color_audit.py` lines 6 and 245 to
`icc_drift_uniform_small` (with new symbol name in the audit's
`pattern` enum)."

### 13.2 12 templates already have `brand_overrides` and `non_ci_styles`
**What goes wrong:** Pre-existing templates may already have
brand_overrides entries without a TOLERANCE_LOG.md row. The new
pre-commit hook (mitigation 1.1) would reject any future change to
those meta.yml files until a TOLERANCE_LOG is created.

**Mitigation (Phase A + cross-cutting):**
- One-time migration: walk all templates, generate
  `templates/<slug>/TOLERANCE_LOG.md` retroactively from existing
  brand_overrides entries (each entry's `reason` becomes the log
  row's text; date = git-blame date; author = git-blame author).
- The pre-commit lint then only catches FUTURE additions, not
  retroactive baseline.
- Acceptance: "TOLERANCE_LOG.md exists for every template that has
  any brand_overrides / non_ci_* entry."

### 13.3 Path-absoluteness in build.py
**What goes wrong:** Current v2 falzflyer build.py has absolute
worktree paths embedded (see line 760:
`image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/...'`).
This means re-running on a different worktree breaks. `bin/idml-import`
will likely re-emit and break this when running from a fresh worktree.

**Mitigation (Phase A + D):**
- Converter emits REPO-RELATIVE paths
  (`shared/assets/<slug>/<file>.png`) in build.py — NOT absolute
  ones. `bin/render-gallery` resolves them at render time against
  ROOT.
- Audit existing 4 converter-emitted templates and convert any
  absolute-path emissions to repo-relative as a regression fix
  during Phase D refactor.
- Acceptance: "no build.py in templates/ contains a `/workspace/`
  literal or any other absolute path."

---

## Mitigation summary — by phase

| Phase | Pitfall | Mitigation |
|-------|---------|------------|
| A | 1.1 SOP enforcement | Pre-commit hook in `tools/sop_lint.py` rejects `engine floor` phrase + meta.yml tolerance edits without TOLERANCE_LOG row |
| A | 1.2 Context decay | Re-emit P2-P10 rules at every iteration boundary; `rules_seen` counter in iteration.jsonl |
| A | 1.3 Hand-patch creep | Track `inject_count_delta`; halt at `> 1 per iteration` |
| A | 2.1 Combinatorial loop | Page-wide drift as primary regression signal; per-region as secondary |
| A | 2.2 Token budget | Iteration checkpointing; on-demand audit detail reads |
| A | 2.3 Non-interactive exit | Exit codes 0/1/2/3 with semantics; `--non-interactive` mode |
| A | 9.1 Re-import semantics | Detect existing template, refuse with `--reimport` flag for explicit overwrite |
| A | 9.2 Slug collisions | Pre-flight collision detection |
| A | 10.1 Batch failure | Per-IDML try/except; batch report; exit 1 on any failure |
| A | 11.1 Brand fonts CI | `--no-brand-fonts` flag with loud warning |
| A | 11.2 Tool availability | Pre-flight tool probe |
| A | 12.1 Baseline provenance | Sibling-PDF default; provenance warnings on mismatch |
| A | 13.3 Absolute paths | Emit repo-relative paths in build.py |
| B | 7.1 Classifier ambiguity | Minimal-SLA mutation strategy for engine vs converter; rename `engine floor` in region_color_audit.py |
| B | 7.2 authoring-bug needs IDML | `--idml <path>` arg to convergence-review |
| B | 7.3 Multi-cause issues | `causes:` list per issue |
| B | 7.4 False positives | `--min-drift-pp` threshold; `minor` category |
| B | 12.2 Colour profile mismatch | Report space/profile delta as `human-review` |
| C | 1.1 Skill enforcement | Skill calls into tools; tool exit codes are the contract |
| C | 6.2 Ambient-context loss | Skill reads iteration.jsonl on every invocation |
| D | 3.1 Refactor byte-identity | Snapshot tests; semantic-equality comparison; per-template SLA-hash gate |
| D | 3.2 Pattern preconditions | Patterns declare preconditions; missing precondition fails as converter-bug |
| D | 3.3 Dead patterns | INDEX.md `last_fired_on_template` + CI check |
| D | 5.3 Vector AI path | Pattern 6 reads `vector_output:` from links_export.yml |
| E | 5.1 Composite-AI detection | Multi-signal detection (page count OR aspect ratio OR multi-frame multi-offset) |
| E | 5.2 Refuse-vs-extend | RECOMMEND extending Phase E to include per-icon splitting, not just detection |
| E | 5.3 Vector AI output | `links_export.py` dispatch: `.ai → {.png, .pdf}` |
| E | 5.4 PSD ICC fallback | Surface `icc_profile_fallback: naive_cmyk` in asset audit |
| E | 12.1 Baseline provenance | Provenance check audit |
| F | 4.1 Migration byte-identity | Semantic-equality test; commit per-inject; SLA-hash unchanged |
| F | 4.2 Y-bump injects | Schema supports `y_mm` / `y_delta_pt` fields with `classification: scribus-engine-bug` |
| F | 4.3 Inject conflicts | List-order application; last-wins; intra-file conflict warning |
| Cross | 13.1 Engine-floor existing refs | Rename in region_color_audit.py |
| Cross | 13.2 Retroactive TOLERANCE_LOG | One-time migration from existing brand_overrides |

---

## Highest-leverage mitigations (prioritise these)

1. **Pre-commit hook + CI lint as the SOP-enforcement backbone**
   (mitigation 1.1). Without this, every other P2-P10 rule is
   advisory. With this, the rules become mechanical.

2. **Composite-AI splitting in Phase E, not deferred**
   (mitigation 5.2). Without this, v2 falzflyer cannot be re-imported
   end-to-end — the very test case for the new tooling — and the
   user's "always extend the converter" directive is violated.

3. **Rename "engine floor" in `region_color_audit.py`**
   (mitigation 13.1). Acceptance criterion currently fails out-of-the-box.

4. **Page-wide drift as primary regression signal**
   (mitigation 8.1). Otherwise structural fixes look like regressions
   and the convergence loop halts on false positives.

5. **`bin/idml-import` exit code semantics + non-interactive mode**
   (mitigation 2.3). The skill cannot drive the tool without clear
   exit-code contracts.

6. **Iteration checkpointing** (mitigation 2.2). Without it, a
   2-hour convergence run that crashes at iteration 17 loses
   everything. With it, restart resumes at 17.

7. **Existing v2 falzflyer migration to `inject.yml`**
   (mitigation 4.1-4.3). This IS the acceptance test for Phase F.
   Migration must produce identical SLA hash, OR we ship broken
   tooling.
