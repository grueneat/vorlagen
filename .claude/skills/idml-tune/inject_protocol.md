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

## Known limitation — reconciler doesn't reach nested dict paths

`tools/reconcile_build_py.py` matches `field=value` at the top level of
the call (`_apply_set` regex pat). It cannot dive into
`paragraph_attrs={'LINESPMode': '0', 'LINESP': '21'}` to swap one
member.

As a result, **per-Run paragraph_attrs overrides for line spacing**
(the canonical use case from issue #40 follow-up) live INLINE in
`build.py` with a `# P5/inject` comment. They will be wiped on a
clean re-import. Track each one in `TOLERANCE_LOG.md` with the
empirical drift measurement and the sim command used to derive the
value, so the override can be re-applied.

Worked example: `templates/26-03-leporello-…/build.py` u1b0/u1e6/u24e/
u2d5/u3a2/u155 carry inline `paragraph_attrs={'LINESPMode': '0',
'LINESP': '<value>'}` and `trail_attrs={'LINESPMode': '0', 'LINESP':
'<value>'}`. Each block has a `# P5/inject` comment citing
`tools/line_spacing_sim.py` and the per-frame drift.

Follow-up: extend the reconciler to support one of:

1. Dotted-path field resolution: `field: paragraph_attrs.LINESPMode`
2. Per-Run targeting via index: `target.run_index: 0`
3. Per-Run targeting via text prefix: `target.run_text_startswith:
   "Ich bin eine"`
4. A dict-merge section: `runs_paragraph_attrs: { u1b0_run_0: {...} }`

Tracking issue: TBD.

## See also

- `shared/inject.schema.yaml` — schema definition.
- `tools/reconcile_build_py.py` — the applier.
- `tools/lint_inject_consistency.py` — the CI gate.
- `pattern_library.md` — the preferred alternative when the rule is
  structural.
- `tolerance_protocol.md` — when meta.yml::brand_overrides is the
  right home instead.
- `SKILL.md` §"Per-frame line-spacing protocol" — the per-frame
  measurement and tuning loop that produces the values which then
  feed back into inline build.py overrides or (once the reconciler
  is extended) inject.yml entries.
