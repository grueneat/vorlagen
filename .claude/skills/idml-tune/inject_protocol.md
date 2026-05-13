# /idml-import — inject.yml protocol (P5)

P5: hand-patches are declarative, not inline.

Pre-issue-#38, the v2 falzflyer template carried 14 `# P5/inject`
comments inline in `build.py`. These were the converter-emitted code
PLUS hand-edits, mixed together, with no schema and no reconcile path.
After re-running the converter, the hand-edits were lost.

Issue #38 introduces:

- `shared/inject.schema.yaml` — JSON schema for the declarative form.
- `tools/reconcile_build_py.py` — applies inject entries to
  `build.py.generated` => `build.py`.
- `tools/lint_inject_consistency.py` — CI gate enforcing 1:1 mapping.

## When to use inject.yml

Use inject.yml when ALL of the following hold:

1. The drift is template-specific (one weird frame, not a structural
   pattern). If it's structural, use `pattern_library.md` instead.
2. The fix can be expressed as `set:` (absolute override) or `delta:`
   (additive offset) on a single field.
3. The rule has a non-trivial `reason` (>= 10 chars, citing the audit
   signal and the upstream cause).
4. A `follow_up_issue` exists (or `null` with explicit justification —
   e.g. "Scribus engine bug; no upstream issue yet").

## inject.yml entry — example

```yaml
hand_patches:
  - target:
      element: TextFrame
      anname: u376
    field: y_mm
    delta: +1.884
    classification: scribus-engine-bug
    reason: >-
      Scribus FirstBaselineOffset rendering differs from InDesign by
      +5.34pt (+1.884mm); y-coord bumped to match baseline.pdf.
      Tracking as engine-bug; no upstream Scribus issue yet.
    follow_up_issue: null
```

Schema reference: `shared/inject.schema.yaml` (Draft 2020-12).

## The skill's workflow

1. Identify the affected element by `(slot, page)` from the audit.
   Cross-reference to the IDML `Self` id (the `anname` in build.py).
2. Decide `set:` vs `delta:`:
   - `set:` — replace the kwarg's value entirely. Use for ALIGN,
     SCALETYPE, fixed line spacing, etc.
   - `delta:` — additive offset. Use for y-coord bumps, x-coord
     bumps, line-spacing fine-tuning.
3. Write the entry with a complete `reason`. The skill MUST cite:
   - The audit that surfaced the drift.
   - The IDML attribute that produces the drift (when known).
   - The upstream cause (engine bug, authoring choice, both).
4. Run `python3 tools/reconcile_build_py.py <slug>` to apply.
5. Verify `tools/lint_inject_consistency.py` passes.
6. Re-render via `bin/render-gallery <slug> --audit-strict` and
   confirm the drift dropped.

## Redundancy detection

When the converter is later extended (a new pattern lands), an
inject.yml entry may become redundant — the converter now emits the
same value the inject was overriding.

`tools/reconcile_build_py.py` emits a warning to stderr when an
inject's `set:` value equals the converter-emitted value in
`build.py.generated`:

```
inject entry at line N is redundant; the converter now emits the same
value. Consider removing it.
```

The skill should:

1. Verify the warning is real (read the line; compare the kwargs).
2. Open a follow-up issue (or update the entry's `follow_up_issue`)
   noting the converter fix that obsoleted the entry.
3. Remove the inject entry in a separate commit so the redundancy
   removal is bisectable.

## Cross-reference: converter-extension TODO

Every inject entry classified `converter-bug` is a future converter
extension waiting to be written. The skill MUST surface this:

> "Adding an inject.yml entry classified `converter-bug` is a debt.
> Track the corresponding converter-extension TODO at: <issue URL>.
> If no issue exists yet, propose one."

Issue #38 P3 task 17 migrated the existing 14 inline P5 comments in v2
falzflyer's build.py to inject.yml. Use that migration as a worked
example.

## See also

- `shared/inject.schema.yaml` — schema definition.
- `tools/reconcile_build_py.py` — the applier.
- `tools/lint_inject_consistency.py` — the CI gate.
- `pattern_library.md` — the preferred alternative when the rule is
  structural.
- `tolerance_protocol.md` — when meta.yml::brand_overrides is the
  right home instead.
