# /idml-import — Tolerance growth protocol (P4)

P4: no silent tolerance growth. `meta.yml::brand_overrides` (and
`non_ci_styles`, `non_ci_colors`, `non_ci_layers`) additions are
GATED by user confirmation + a `TOLERANCE_LOG.md` row.

Issue #35 added 5 brand_overrides silently, masking real converter
bugs that were later fixed in #76/#77. Issue #38 makes this
mechanical: `tools/check_overrides_growth.py` runs on commit and
refuses additions without justification.

## The skill MUST NOT

- Add a `brand_overrides` entry without prompting the user.
- Add an entry with a generic `reason` like "needed for this template".
- Modify `meta.yml` to grow a tolerance list without writing the
  TOLERANCE_LOG.md row in the SAME edit.

## The skill MAY

- REMOVE tolerance entries when the underlying bug is fixed
  (TOLERANCE_LOG row is preserved; new entry documents the removal).
- Suggest a tolerance entry to the user when:
  1. The drift signal is classified `scribus-engine-bug` AND
  2. No converter-fix path exists (the rule is upstream Scribus) AND
  3. The drift is sub-percent and bounded (not a regression risk).

## Confirmation flow

When the skill identifies a candidate tolerance entry:

```
The converter has produced a render with a {N}-unit RGB delta on
{slot} on page {page} that the classifier labels {scribus-engine-bug}.
The drift appears to be {ICC-profile rendering / Aki composition / ...}
which is upstream Scribus and not fixable in the converter.

I propose adding the following entry to templates/{slug}/meta.yml:

  brand_overrides:
    - id: brand:{rule_id}
      reason: {one-paragraph rationale citing the audit + signal + why
              converter-extension is closed}

And the matching row in templates/{slug}/TOLERANCE_LOG.md:

  ## brand:{rule_id} — {today} — {one-line summary}
  Reason: {expanded rationale}.
  Follow-up: {tracking issue URL or "engine-bug; no upstream issue yet"}.

Confirm? (yes / no / edit)
```

The user MUST type "yes" verbatim. Anything else => no mutation.

## Writing the TOLERANCE_LOG.md row

Schema (markdown, append-only):

```markdown
## brand:<rule_id> — <YYYY-MM-DD> — <one-line summary>

Reason: <paragraph explaining why the converter cannot fix this; cite
the audit (region_color_audit, font_audit, line_spacing_audit, etc.),
the IDML attribute that produces the drift, and the upstream-Scribus
issue / authoring concern that closes the converter path>.

Follow-up: <link to GitHub issue tracking the fix, OR "engine-bug; no
upstream issue yet", OR "authoring; baseline.pdf needs re-export">.
```

The `check_overrides_growth.py` lint matches via substring on the rule
id. The id appearing anywhere in TOLERANCE_LOG.md passes the gate; the
prose form above is the convention for clarity.

## When TOLERANCE_LOG.md is missing

If the template doesn't have a TOLERANCE_LOG.md yet, create one with
this header before adding the first row:

```markdown
# Tolerance Log — <slug>

Documents every entry in meta.yml::brand_overrides, non_ci_styles,
non_ci_colors, non_ci_layers with the rationale for why the converter
cannot fix the underlying drift.

Append-only. Remove entries via a new row at the bottom that says
"REMOVED <rule_id> — <date>: <reason fix landed>".
```

## When `inject.yml` is the right home instead

If the proposed override would change a build.py emission (not a
tolerance threshold), use `inject.yml` per `inject_protocol.md`
INSTEAD of `meta.yml::brand_overrides`. The inject entry's `reason`
field satisfies the same justification gate (and
`check_overrides_growth.py` accepts an inject entry as the
justification target).

## See also

- `tools/check_overrides_growth.py` — the lint.
- `inject_protocol.md` — when to use inject.yml vs brand_overrides.
- `classification.md` — when scribus-engine-bug is the correct label.
