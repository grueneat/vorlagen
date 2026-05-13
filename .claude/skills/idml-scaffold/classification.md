# /idml-import — Issue classification rules

The classifier in `tools/convergence_review.py` reads every audit yml/json
under `build/validation/<slug>/` and produces one issue dict per drift
signal. Each issue is labelled with one of five classifications:

| Label | Skill response |
|-------|----------------|
| `converter-bug` | EXTEND the converter (`tools/idml_to_dsl.py` or a pattern in `tools/idml_to_dsl_patterns/`). |
| `scribus-engine-bug` | Document in `inject.yml` with `classification: scribus-engine-bug`; accept residual via `--accept-residual <id>` after user confirmation. |
| `authoring-bug` | Surface to the user. The IDML or `baseline.pdf` itself is inconsistent. The skill does NOT auto-fix authoring issues. |
| `human-review` | Surface to the user with a triage prompt. Default when signals are ambiguous (P8: bias to `human-review`). |
| `minor` | `est_drift_drop < --min-drift-pp` (default 0.5pp). Filtered out of the hot-issues list. Still recorded for completeness. |

## Decision rules

These are the same rules `tools/convergence_review.py` applies; the
skill should agree with the tool's verdict, not second-guess it.

| Signal | Classification | Confidence |
|---|---|---|
| `region_color_audit::icc_likely` + brand-color region (mean_delta <= 5.0) | scribus-engine-bug | HIGH |
| `region_color_audit::fill_likely` + mean_delta > 5.0 | converter-bug | HIGH |
| `text_position_audit::large_deltas` + IDML XPath shows mixed Justification (via `--idml`) | converter-bug | MEDIUM |
| `text_position_audit::large_deltas` WITHOUT `--idml` available | human-review | SAFE FALLBACK |
| `per_element_drift::top_contributors` slot has local_offset != 0 AND local_scale != 1 (Backport-10 family) | scribus-engine-bug | HIGH |
| `diff_bboxes::drift_type == "missing"` + slot NOT in `inventory.yml::elements_emitted` | converter-bug | HIGH |
| `font_audit::missing_in_preview` non-empty | converter-bug | MEDIUM |
| `run_style_audit::style_drifts` + `drift.fontname` non-empty | converter-bug | HIGH |
| `line_spacing_audit::drifts` with `abs(delta_pt) > 0.5` | converter-bug | MEDIUM |
| `asset_audit::links_missing` non-empty | authoring-bug | HIGH |
| `asset_audit::links_unconverted` non-empty | converter-bug | HIGH (re-run `tools/links_export.py`) |
| `asset_audit::composite_ai_detected` non-empty | converter-bug | HIGH (run `tools/composite_ai_split.py`) |
| Everything else | human-review | SAFE FALLBACK |

## Why `human-review` is the default

P8: in #35, two Sonnet executors over-confidently labelled drifts as
a false convergence plateau when in fact they were converter bugs
(Backports 9 and 10 went unfixed for hours). The classifier's bias is
now to STOP and surface ambiguous signals to a human rather than
guess.

The cost of a false `converter-bug` label is bounded (the user can
re-classify). The cost of a false `scribus-engine-bug` label, or
declaring a non-existent convergence plateau, is unbounded (the
convergence loop terminates with the bug unfixed). Bias accordingly.

## When to use `--idml` for classifier introspection

Some classifications need the source IDML to disambiguate:

- `text_position_audit::large_deltas` without IDML defaults to
  `human-review` because the classifier can't tell whether the drift
  is from a mixed-Justification paragraph (converter-bug) or
  intentional authoring (authoring-bug).
- `run_style_audit::style_drifts` could benefit from knowing whether
  the IDML's FontName matches the expected baseline.

Pass `--idml <path>` to `bin/convergence-review` to enable these
upgrades.

## Leverage scoring

`est_drift_drop` estimates how much page-wide mismatch fixing this
issue would remove, using `per_element_drift::top_contributors`:

```
est_drift_drop = min(
    sum(top_contributors[slot].pct_of_page_mismatch),
    per_element_drift[page].total_mismatch_pct,
)
```

Sort key for the issue list: `(-est_drift_drop, severity_rank, slot)`.
Severity rank: scribus-engine-bug < converter-bug < authoring-bug <
human-review < minor.

The leverage-sort means the skill should ALWAYS address the top issue
first. If the top issue is `human-review`, surface that BEFORE working
on a lower-leverage `converter-bug`.

## Termination conditions

- All open issues classified `minor` => `bin/convergence-review`
  returns verdict `PASS`.
- All open issues are `authoring-bug` => verdict `BLOCKED_BY_AUTHORING`.
  User must fix the IDML / baseline.pdf.
- Mix => verdict `NEEDS_WORK`. Skill must iterate Step 4 or Step 5.
