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

## Defined render → audit → remediation loop — MANDATORY

The Stage-2 workflow is a **closed loop** between two tools. The LLM's
role is to point at a template and watch the loop run. There is no
ad-hoc per-frame iteration; each remediation is encoded in
`tools/playbooks/*.py`.

```
bin/tune-render <slug>     → render + full audit chain (transactional)
                              · on green: artifacts promoted to templates/<slug>/
                              · on red:   artifacts moved to build/staging/<slug>/,
                                          templates/<slug>/ restored from snapshot,
                                          site/public mirror deleted, exit 2
bin/tune-fix    <slug>     → read failed-audit reports, apply playbooks,
                              re-invoke bin/tune-render in a loop until
                              preflight is green or no playbook can advance
```

### Failure-driven remediation contract

When `bin/tune-render` exits 2:

1. The render output is **NOT** in `templates/<slug>/`. Looking at
   `templates/<slug>/preview.pdf` shows the PRE-render state.
2. The failed render is in `build/staging/<slug>/` (read-only inspect).
3. The audit reports are in `build/validation/<slug>/`.
4. The directive is exactly: `bin/tune-fix <slug>`.

Do NOT cherry-pick artifacts out of `build/staging/` into
`templates/<slug>/`. Do NOT edit `template.sla` directly. The next
`bin/tune-render` will re-snapshot and either green or move it back
to staging — surgical edits to the failed-render output are lost.

### bin/tune-fix playbooks

| Audit | Playbook | Action |
|---|---|---|
| `systematic_text_audit` | `tools/playbooks/line_spacing.py` | Run `line_spacing_sim` per actionable frame, apply best (LINESPMode, LINESP) candidate |
| `structural_check` (rotation) | `tools/playbooks/constraint_violation.py` | Adopt reference rotation onto offenders |
| `structural_check` (distance/gap/inside) | `tools/playbooks/constraint_violation.py` | ESCALATE — layout intent decision |

When `bin/tune-fix` exits 2, the residual is **not addressable by an
existing playbook**. The right next action is one of:

- Author a new playbook in `tools/playbooks/` covering the audit
  signature, then re-invoke `bin/tune-fix`. The playbook becomes
  the durable fix; the next falz template that hits the same class
  reuses it.
- Escalate to Stage 1 when the issue is converter-level (e.g.
  FrameFittingOption translation, ParaStyle font emission).

Hand-patches to `build.py` without an audit signal regress on the
next render. The defined loop is the safety net; bypassing it
guarantees regressions.

### When you add a NEW audit

Wire it into `tools/render_pipeline.py` Phase E6+. Have it write
`build/validation/<slug>/<audit>.yml` with `ok: bool, issues: int,
detail: str`. Have `_build_preflight` consume it. Then write the
matching playbook in `tools/playbooks/<audit>.py` exposing
`apply(slug, repo, dry_run) -> (n_changes, log)`. Register in
`bin/tune-fix::PLAYBOOKS`. The closed loop now handles your audit
without any LLM-side recipe — point at a template, the loop drives
it green or escalates with a specific signature.

### Legacy direct-tool calls (DO NOT USE)

The following must NOT be called by the skill — they bypass the
transactional gate:

- `render_sla_to_pdf()` / `rasterise()` from `tools/visual_diff.py`
- `python3 templates/<slug>/build.py` directly
- `bin/render-gallery <slug>` directly (use `bin/tune-render` instead)
- Editing `template.sla` directly

**The audit tools (E4 line_spacing_pixel_audit, E5
image_frame_visibility_audit) ENFORCE this — they exit non-zero
with "STALE: …" if their inputs are older than build.py.** The LLM
can't "forget" a re-render step and still see green audit numbers:
any skipped step makes the next audit fail loudly with
`Fix: bin/tune-render <slug>` in the error.

NEVER call directly:

- `render_sla_to_pdf()` / `rasterise()` from `tools/visual_diff.py`
- `python3 templates/<slug>/build.py` (use `bin/tune-render` which
  also rasterises + updates the hash + runs audits)

If a step in the canonical flow is unsuitable for some reason, the
skill MUST surface the unmet need to the user and pause — not silently
skip. (The freshness gate makes "silent skip" impossible by exiting
non-zero on the next audit.)

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
- `tools/image_frame_visibility_audit.py` — **the per-image-frame
  visibility check.** Compares ink-pixel density inside each
  ImageFrame's bbox between baseline.pdf and preview.pdf. Flags
  frames where preview is mostly background (icon embedded but
  not rendering). Catches the known Scribus 1.6.x bug where
  SCALETYPE=1 + small frame + RGBA white-on-transparent PNG
  renders fully transparent. Runs as Phase E5 in the audit chain.
  When a frame is flagged `invisible_in_preview`, switch from
  `inline_image_data` to a direct `image=` reference and set
  `scale_type=0` (fit-to-frame). See the 26-03 Leporello u141
  (DIE GRÜNEN logo) and u3e7/u3f0/u3f5 (left-column social icons)
  for worked examples.
- `tools/per_region_regression_check.py` — **iteration-over-
  iteration per-frame regression check.** Runs as Phase E6.
  Maintains `build/<slug>/per_region_history.jsonl` (committed
  to git) with one entry per audit run carrying every frame's
  line-spacing drift + image visibility ratio. Compares the
  current run against the previous entry; flags any frame where
  `abs(line_spacing_drift)` increased by ≥0.5pt or
  `image_visibility_ratio` dropped by ≥0.1. **This is the
  guard against fixing one frame and silently regressing another**
  — E2-E5 each compare against baseline.pdf within ONE iteration,
  E6 compares iteration N vs iteration N-1.
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
- `templates/<slug>/meta.yml::frame_library_map` — per-frame mapping
  from anname → `shared/sample-images/manifest.yml` ID for preview
  AI substitution (see "Demo image substitution" below).
- `templates/<slug>/TOLERANCES.yml` — explicit per-element visual
  trade-offs with justifications.

## Demo image substitution — preview render only (active 2026-05-14)

**DO NOT** try to fix demo image crop/scale with empirical
`local_offset_mm` + `local_scale` guesses. Scribus 1.6.x has no native
aspect-FILL mode, so any IDML-imported demo photo whose aspect doesn't
match its frame renders with letterbox/pillarbox or off-frame. The
crop-tuning loop never converges and produces brittle per-frame magic
numbers.

**DO** swap demo (`external:`) ImageFrame sources with library AI
images cropped to the frame's exact W×H at preview-render time. The
committed `template.sla` keeps its external PFILE reference (user's
download is unchanged); `template-preview.sla` carries the
AI-substituted inline image for the gallery render.

Pattern (matches `zeitung`, `postkarte`, `plakat` `build_preview()`):

```python
from sla_lib.builder.library import load as load_library, inject_into_frame

def build_preview(doc):
    """Per-template gallery render: substitute external assets with library AI."""
    # ... build doc as usual, then:
    for frame in doc.frames_by_anname():  # or similar lookup
        if frame.anname in meta["frame_library_map"]:
            img_id = meta["frame_library_map"][frame.anname]
            img = load_library(img_id)
            inject_into_frame(
                frame, img,
                target_w_mm=frame.w_mm,
                target_h_mm=frame.h_mm,
            )
    return doc
```

`inject_into_frame` does the right thing in one call: centre-crops the
library image to the frame's aspect (honouring `crop_focus` saliency
anchor), packs the JPEG via `pack_inline_image`, sets `scale_type=0`
(ScaleAuto). The result fills the frame with no gap and no
`local_offset_mm` guesswork.

If a library entry whose tags fit doesn't exist, see
`shared/sample-images/manifest.yml` to add one (regenerable via
`tools/codex_image_gen.py`). Brand `embedded:` assets are NEVER
substituted — only `external:`.

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

When line spacing drifts, follow this loop. **The canonical signal is
`line_spacing_pixel_audit.yml` (Phase E4).** The legacy
`line_spacing_audit.yml` (Phase E2) is **deprecated as a primary
signal** — its pdfplumber clustering is wrong for narrow leadings (the
threshold mis-merges adjacent small-font lines). E2 still runs and
writes a YAML, but it carries `informational_only: true`, no longer
appears in preflight `issue_parts`, and `_build_preflight` records it
with `ok: true` regardless of its internal `ok` flag. Use it only for
trend-watching, never as a per-frame decision basis (F-017).

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
