# IDML to DSL Pattern Catalogue

Each row describes a converter-extension pattern that mutates the kwargs
dict for a specific IDML element emission. Patterns are registered in
`__init__.py::PATTERNS` in dependency order; later patterns may override
kwargs set by earlier ones.

Issue #38 ships six extracted patterns + one new pattern. See each
pattern module for the regression test path.

| id | description | source | target | test | last_fired_on_template |
|----|-------------|--------|--------|------|------------------------|
| `justification_to_align` | Map IDML Justification to ALIGN int (Backport 9) | ParaStyle.Justification | PARAGRAPHSTYLE.ALIGN | `tests/unit/test_pattern_justification_to_align.py` | kandidat-falzflyer-din-lang-gruenes-cover-v2 |

## How to add a new pattern

1. Copy the structure from any of the existing pattern modules.
2. Implement `matches(idml_element)` and `apply(kwargs, idml_element, context)`.
3. Add the import + instance to `__init__.py::PATTERNS` in dependency order.
4. Add a row to this catalogue with the regression test path.
5. Write a unit test in `tests/unit/test_pattern_<id>.py` covering at
   minimum: positive case mutates kwargs, negative case is a no-op,
   pattern metadata (id, description, applies_to).
6. Run `tests/integration/test_v2_falzflyer_build_byte_identity.py` (or
   the equivalent template-of-record byte-identity test) to confirm the
   refactor preserved the converter's output exactly.

See `.claude/skills/idml-import/pattern_library.md` for the full
SOP that the skill enforces when adding a pattern.
