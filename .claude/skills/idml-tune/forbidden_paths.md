# Stage 2 forbidden paths

The tune agent operates ONLY inside `templates/<slug>/`. Editing any of
the paths below is a Stage-2 violation — the change belongs in Stage 1
(`/idml-scaffold`) because it would alter behaviour for every template,
not just the one being tuned.

## Explicit forbidden list

| Path / glob | Reason |
|---|---|
| `tools/idml_to_dsl.py` | Shared IDML→DSL converter — converter-first changes are Stage 1 only. |
| `tools/idml_to_dsl_patterns/**` | Pattern library is part of the converter surface. |
| `tools/sla_lib/**` | SLA reader / builder primitives are converter infrastructure. |
| `tools/inventory_extract.py` | The gate itself — tuning it would corrupt the gate signal. |
| `tools/inventory_compare.py` | Same — the comparator must stay deterministic. |
| `tools/walkers/**` | The walkers that feed the gate. |
| `tools/reconcile_build_py.py` | inject.yml → build.py materialiser. |
| `tools/sop_lint.py` | Banned-phrase enforcement. |
| `templates/<other-slug>/**` | Stage 2 is bounded to ONE template's directory. |
| `shared/**` | Shared assets — touched by Stage 1 asset extraction only. |
| `bin/**` | Driver entry-points. |

## Permitted edits

Whitelist for Stage 2:

- `templates/<slug>/build.py`
- `templates/<slug>/inject.yml`
- `templates/<slug>/meta.yml::brand_overrides` /
  `meta.yml::non_ci_styles` / `meta.yml::non_ci_colors` /
  `meta.yml::non_ci_layers` (gated by P4 user confirmation)
- `templates/<slug>/TOLERANCES.yml`

## Mechanical enforcement (recommended)

A pre-commit hook can enforce the list:

```
# tools/check_stage2_forbidden_paths.py <changed-files>
# Exit 0 if no changed file matches the forbidden globs above; exit 1 with
# a list of offending paths otherwise.
```

This script itself is OUT OF SCOPE for this PR (issue #40) — it is a
nice-to-have follow-up. The list above is the authoritative spec.

## Escalation procedure

If a tuning need requires editing a forbidden path:

1. Stop the tune loop.
2. Write up the converter or pattern change as a PLAN-level note
   (issue or comment).
3. Return to `/idml-scaffold` with the converter fix.
4. Re-scaffold the template (`bin/idml-import <slug> --reimport
   --scaffold-only`).
5. Resume `/idml-tune <slug>` from a fresh
   `SCAFFOLD_INVENTORY.yml` baseline.
