# /idml-import — Pattern library workflow

P3: converter-first remediation. When the classifier surfaces a
`converter-bug`, the default action is to EXTEND the pattern library at
`tools/idml_to_dsl_patterns/`, not to hand-patch `build.py`.

This file is the SOP the skill follows when adding a new pattern or
widening an existing one.

## When to add a new pattern

- The IDML attribute that drives the bug is structural (every template
  with that attribute combination will hit the same drift).
- The fix is a deterministic mapping from IDML to SLA (no per-template
  measurements required).
- The same fix would apply to at least two templates (or could plausibly
  apply if the template existed).

When the fix is template-specific (one weird frame in one IDML), prefer
an `inject.yml` entry via `inject_protocol.md`.

## Anatomy of a pattern

Every pattern lives in `tools/idml_to_dsl_patterns/<id>.py` and exposes:

```python
class MyPattern:
    id = "my_pattern"
    description = "One-line human-readable description"
    applies_to = "TextFrame"   # or ImageFrame, PolyLine, ...

    def matches(self, idml_element) -> bool:
        ...

    def apply(self, kwargs: dict, idml_element, context=None) -> None:
        ...
```

`matches()` must be cheap (called on every element); `apply()` mutates
the converter's kwargs dict in-place.

## Adding a pattern — checklist

1. Copy `tools/idml_to_dsl_patterns/justification_to_align.py` as a
   starting point. Adapt the class.
2. Add the import + instance to `tools/idml_to_dsl_patterns/__init__.py::PATTERNS`.
   Order matters: later patterns override earlier kwargs. Use the
   `depends_on` attribute (informational) to document dependencies.
3. Add a row to `tools/idml_to_dsl_patterns/INDEX.md` with the
   regression test path and the template-of-record.
4. Write a unit test at `tests/unit/test_pattern_<id>.py`. Cover at
   minimum:
   - **Positive case:** the pattern fires and mutates kwargs correctly.
   - **Negative case:** matches() returns False, apply() is a no-op.
   - **Metadata:** id, description, applies_to.
   - **Registered:** `pattern_by_id(<id>)` returns the instance.
5. Run `tests/integration/test_v2_falzflyer_build_byte_identity.py`.
   It re-emits v2 falzflyer's build.py and asserts byte-equal to the
   pre-refactor snapshot. **Byte-identity is the contract.** If your
   pattern changes the emitted output for v2 falzflyer, either:
   - The change is intentional and you UPDATE the snapshot in the
     same commit, with a clear note in the commit message, OR
   - The change is unintentional and you've broken the converter.
     Fix or revert.

## Anti-patterns

- **"Added a pattern that matches nothing"** (RESEARCH.md 3.3): if the
  unit test asserts only that `apply()` is callable, the pattern is
  not exercised. The positive test MUST assert kwargs mutated for a
  realistic input.
- **"Pattern silently overwrites earlier kwargs"**: if your pattern
  sets `kwargs["x"]` and an earlier pattern set the same key, document
  this in `depends_on` AND a comment in the docstring.
- **"Pattern fires on every element"**: `matches()` should be selective.
  An always-True `matches()` plus per-call branching in `apply()` makes
  the pattern hard to reason about.
- **"Pattern requires context but doesn't check"**: if your pattern
  needs `context["paragraph_styles"]`, defensively check for the key
  and emit a `_todo` marker when missing — never raise.

## Updating an existing pattern

When widening an existing pattern (e.g. JustificationToAlign needs to
accept an 8th Justification value):

1. Edit `matches()` / `apply()` / the relevant map.
2. ADD a new unit test for the new case (do not modify existing tests).
3. Re-run the byte-identity test. The existing v2 falzflyer build.py
   should be unaffected by the widening (the new case wasn't in v2 to
   begin with). If it IS affected, that's a regression — investigate.
4. Add a row to the pattern's INDEX.md entry noting the widening
   (template that triggered it).

## See also

- `tools/idml_to_dsl_patterns/INDEX.md` — the catalogue.
- `tools/idml_to_dsl_patterns/base.py` — the Pattern Protocol.
- `tests/integration/test_v2_falzflyer_build_byte_identity.py` — the
  byte-identity contract.
- `inject_protocol.md` — the P5 fallback when a pattern is not the
  right tool.
