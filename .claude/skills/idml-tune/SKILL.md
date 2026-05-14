---
name: idml-tune
description: |
  Stage 2 of the two-agent IDML import pipeline. Per-template iterative
  visual polish bounded to ONE templates/<slug>/ directory. Reads
  SCAFFOLD_INVENTORY.yml as its source of truth and runs the inventory
  gate every iteration; permitted edits are build.py, inject.yml,
  meta.yml::brand_overrides, and TOLERANCES.yml. The converter
  (tools/idml_to_dsl.py) and tools/sla_lib/ are FORBIDDEN. MUST BE USED
  when the user invokes /idml-tune <slug>, asks to tune a template,
  fix per-template visual fidelity, or close residual drift on a
  scaffolded template.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
argument-hint: "<slug>"
---

# /idml-tune — Stage 2: per-template visual polish

Stage 2 of the two-agent IDML import pipeline (issue #40). The
scaffold is already done; this skill iterates on **one** template's
directory to close visual fidelity gaps. **The converter is off-limits
here** — see Forbidden paths below.

| Stage | Skill | Goal |
|---|---|---|
| 1. Scaffold | `/idml-scaffold` | Every IDML element emitted; inventory captured |
| **2. Tune** | `/idml-tune <slug>` (this) | Per-template visual polish under the inventory gate |

## Tooling

- `tools/inventory_extract.py` — produces a fresh `SCAFFOLD_INVENTORY.yml`
  snapshot at any moment.
- `tools/inventory_compare.py` — diffs the freshly-extracted snapshot
  against the committed baseline at `templates/<slug>/SCAFFOLD_INVENTORY.yml`.
  Exit codes: 0 / 2 / 3 (match / regression / drift).
- `tools/reconcile_build_py.py <slug>` — materializes `inject.yml` into
  `build.py`. Run before each iteration's inventory extract so the
  walker sees the canonical reconciled file.
- `tools/line_spacing_pixel_audit.py` — **the authoritative
  per-frame line-spacing measurement.** Renders preview.pdf and
  baseline.pdf at 150 dpi, scans each TextFrame's bbox for ink-top
  pixels, reports per-line drift in points. **Use this before
  trusting any pdfplumber-based number** — pdfplumber reports the
  text-matrix Y the renderer was told to write, NOT where the ink
  actually ends up; the difference is per-font-metric and can be
  >5pt (Vollkorn 23pt: pdfplumber said 0pt drift, pixel said
  -5.28pt). `--probe <anname>` for one-frame JSON output.
- `tools/line_spacing_full_audit.py` — cross-source IDML→build.py→
  SLA table. Use to identify ROOT CAUSE (which layer carries the
  wrong value) once pixel audit confirms a drift exists. Its own
  `--probe <anname>` does word-position via pdfplumber and is
  useful for the text-matrix Y check (informational only).
- `tools/line_spacing_sim.py` — **the empirical leading-value
  discovery tool.** Sweeps `(LINESPMode, LINESP)` candidates,
  renders each via xvfb-run+Scribus, measures the resulting
  baseline-to-baseline gap (pdfplumber-based). For high-fidelity
  empirical search, combine with manual pixel scans.
- `tools/sop_lint.py` — banned-phrase guard. Still runs on Stage 2 output.
- `tools/lint_inject_consistency.py` — inject.yml ↔ build.py 1:1 lint.

## Forbidden paths

The tune agent MUST NOT edit any of:

- `tools/idml_to_dsl.py` — the shared converter
- `tools/idml_to_dsl_patterns/**` — pattern library
- `tools/sla_lib/**` — SLA reader/builder primitives
- `tools/inventory_extract.py` / `tools/inventory_compare.py` — the gate
- Any other template's `templates/<other-slug>/` directory
- Any file under `tools/walkers/`

If a tuning need requires a converter change, ESCALATE: stop, return
to `/idml-scaffold`, fix the converter there. Then re-scaffold and
re-tune.

See `forbidden_paths.md` for the explicit machine-checkable list.

## Per-iteration inventory gate (HARD precondition)

Every Stage-2 iteration MUST begin with:

```
python3 tools/reconcile_build_py.py <slug>
python3 tools/inventory_extract.py --slug <slug> --output /tmp/inv-current.yml
python3 tools/inventory_compare.py \
    --expected templates/<slug>/SCAFFOLD_INVENTORY.yml \
    --actual /tmp/inv-current.yml \
    --out build/validation/<slug>/inventory_diff.yml
```

If exit code != 0, the loop is BLOCKED. The tune agent MUST revert
its last edit and try a different approach. The committed
`SCAFFOLD_INVENTORY.yml` is the source of truth for "what must remain"
— losing an anname, dropping a Run text, or removing a color is a
regression and exits the loop.

Specific blocking rules (CONTEXT.md §Gate behavior, verbatim):

Stage 2 (tuning) **blocks** any iteration that:

- Decreases any `count` field in `inventory_diff`.
- Removes an `anname` from any frame list.
- Drops a word from `preview_pdf_words` present in the prior iteration.

## Permitted edits (whitelist)

Only these paths may be edited in Stage 2:

- `templates/<slug>/build.py` — direct edits permitted, but prefer
  `inject.yml` for declarative overrides.
- `templates/<slug>/inject.yml` — see `inject_protocol.md`.
- `templates/<slug>/meta.yml::brand_overrides`,
  `meta.yml::non_ci_styles`, `meta.yml::non_ci_colors`,
  `meta.yml::non_ci_layers` — gated by P4 (user confirmation +
  `TOLERANCE_LOG.md` row).
- `templates/<slug>/TOLERANCES.yml` — explicit per-element visual
  trade-offs with justifications.

## Step 1 — Classify the open issues

Read `build/<slug>/iteration.jsonl` (latest row's `issues_open`) and
`build/validation/<slug>/preflight.yml`. Invoke
`bin/convergence-review <slug> --format md` for the readable summary.

For each open issue, the classifier produces one of four labels:

| Label | Means | Stage 2 response |
|-------|-------|------------------|
| `converter-bug` | The converter emitted wrong SLA | ESCALATE — Stage 2 can't edit the converter |
| `scribus-engine-bug` | Scribus renders correct SLA incorrectly | Document via `inject.yml`; accept residual |
| `authoring-bug` | The IDML or baseline.pdf is inconsistent | Surface to the user; pause |
| `human-review` | Ambiguous | Surface to the user; pause |

## Step 2 — Per-iteration loop

1. Run the inventory gate (above). If exit != 0 → revert + retry.
2. Pick the WORST element from the diff (largest visual delta on a
   named anname).
3. Apply the smallest possible edit:
   - Prefer `inject.yml` over inline `build.py` edits.
   - Authoring an `inject.yml` entry per `inject_protocol.md`.
4. Re-run `python3 tools/reconcile_build_py.py <slug>` →
   `bin/idml-import <slug>` → inventory gate.
5. Confirm no regression on any prior-passing named element.
6. Repeat.

## Step 3 — Tolerance growth requires user confirmation

P4: `meta.yml::brand_overrides` (and `non_ci_styles`,
`non_ci_colors`, `non_ci_layers`) growth is GATED.

1. The skill surfaces the tolerance rule it wants to add and the
   reason.
2. The user replies "yes, add brand:X with reason Y".
3. The skill writes the `TOLERANCE_LOG.md` row FIRST, then mutates
   `meta.yml`.
4. `tools/check_overrides_growth.py` runs on commit and verifies the
   pair.

See `tolerance_protocol.md` for the exact wording the skill uses for
the confirmation prompt.

## Step 4 — Termination

Tuning is complete when:

- `preflight.yml::ok == true` AND inventory diff exit code is 0, OR
- `--accept-residual` covers every remaining issue AND every accepted
  issue is classified `human-review` or `authoring-bug` (NEVER
  `converter-bug` — those go through `/idml-scaffold`).

## Per-frame line-spacing protocol

When `line_spacing_audit` flags drifts, follow this loop. The clustered
"line-spacing drift" stat in preflight is a SUMMARY signal; never trust
it for a specific frame.

### 1. Direct PIXEL-LEVEL measurement is the only reliable per-frame number

pdfplumber-based measurements (including the audit's clustering AND the
`--probe` mode in `line_spacing_full_audit.py`) report the text-matrix Y
the renderer was told to write. The ACTUAL rendered ink position depends
on per-font ascent metrics — InDesign and Scribus produce different ink
positions for the SAME text-matrix Y on Vollkorn Italic and other deep-
metric fonts. Two PDFs can have identical pdfplumber positions and look
visibly different (issue #40 follow-up: u1b0 pdfplumber 0pt drift but
pixel scan revealed -5.28pt drift on line 2).

**Always start with the pixel audit:**

```
python3 tools/line_spacing_pixel_audit.py \
    --slug <slug> \
    --out-yaml build/validation/<slug>/line_spacing_pixel_audit.yml \
    --out-md  build/validation/<slug>/line_spacing_pixel_audit.md

# Or for one frame:
python3 tools/line_spacing_pixel_audit.py --slug <slug> --probe <anname>
```

Reports per-line ink-top in pt, per-line drift vs baseline, and
CUMULATIVE drift `(last_top - first_top)` in preview vs baseline. For
body text with 11 lines, per-line drift of 0.1pt accumulates to 1pt+;
the pixel audit reports both per-line and cumulative.

If drift is ≥ 1pt on any line, proceed to root-cause analysis with
`line_spacing_full_audit.py` (which shows IDML, build.py, SLA values).

### 2. Empirical (LINESPMode, LINESP) discovery via the simulator

The IDML CSR Leading is the authored value, but Scribus's rendering of
sub-metric LINESPMode/LINESP is non-monotonic and font-dependent — no
single rule predicts the output. Use the simulator:

```
python3 tools/line_spacing_sim.py \
    --slug <slug> --anname <anname> \
    --candidates '1:,0:<X>,0:<X-3>,0:<X-6>,2:<X>' \
    --expected-words "Word1,Word2" --fontsize-pt <pt>
```

`expected_words` filters lines to those matching the frame's content
(prevents adjacent-frame contamination). Picks lowest-drift candidate.

### 3. Apply override

Once the (mode, linesp) is known, override per-frame in
`templates/<slug>/build.py`:

- **`Run().paragraph_attrs`** for intermediate `<para>` separators
- **`TextFrame.trail_attrs`** for the closing `<trail>`

BOTH must carry the SAME (LINESPMode, LINESP) — otherwise Scribus uses
the inconsistent `<para>` rule and the trail's LINESP doesn't take
effect. Add a `# P5/inject` comment citing the sim drift measurement.

The `inject.yml` reconciler currently can't reach nested dict paths
(`paragraph_attrs.LINESPMode`), so the overrides live inline in
build.py. They'll be lost on a clean re-import — track that as a
follow-up; preserve in TOLERANCE_LOG.md.

### 4. Mixed-font frame edge case

When a paragraph contains adjacent CSRs with different fonts (e.g.
Gotham→Vollkorn→Gotham 3-line headline), Scribus's per-line font-metric
model dominates — no single (mode, linesp) reconciles the transitions.

The fix is to split the frame into single-line TextFrames at
calibrated y_mm positions. Get exact positions from baseline.pdf word
tops, then iterate y_mm by ~+2mm until each line's cap-top matches the
baseline cap-top (each font has its own ascender offset from frame
top under FLOP=2). Worked example: `templates/26-03-leporello-…/build.py`
u16c → u16c, u16c_l2, u16c_l3.

### 5. Banned values

- `LINESPMode=2 + LINESP < fontsize × 1.45` — Scribus renders at
  ~font-metric × 1.5 regardless of LINESP value. **Never emit this.**
  Use `LINESPMode=0 + LINESP=<empirical>` or `LINESPMode=1` instead.
- Template-wide ParaStyle `linesp` overrides for headlines — Scribus's
  per-line font metric dominates ParaStyle linesp anyway, and the
  override breaks body text using the same ParaStyle.

## Banned phrases (advisory)

Inherited from Stage 1 — see `idml-scaffold/SKILL.md`. The phrases
catch symptoms (cosmetic over-claims like "false-convergence-plateau",
"good enough", "accept the drift") that the inventory diff does not.

**In Stage 2 these are ADVISORY.** The inventory gate is the only
HARD signal — see "Per-iteration inventory gate" above. Banned
phrases still apply to commit messages, EXECUTION logs, and authored
prose; `tools/sop_lint.py` enforces them on commit.

## See also

- `forbidden_paths.md` — explicit list + enforcement hint.
- `inject_protocol.md` — declarative hand-patch workflow.
- `tolerance_protocol.md` — P4 confirmation flow.
- `.claude/skills/idml-scaffold/SKILL.md` — Stage 1.
- `tools/inventory_compare.py` — the gate.
- `docs/scribus-sla-attribute-semantics.md` — corpus-tested SLA attribute behaviour.
