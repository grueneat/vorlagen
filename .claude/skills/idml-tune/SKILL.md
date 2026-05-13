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
