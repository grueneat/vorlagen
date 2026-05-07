# Gate 1 Spec Review — Reviewer Prompt

You are reviewing **9 spec documents** in `templates/_specs/` of the repo at the current
working directory. Read them yourself — do not request diffs.

Files to review:
- `templates/_specs/SCHEMA.md` — the spec format itself
- `templates/_specs/_existing-postkarte-a6-kampagne.md` — retro-spec (existing template)
- `templates/_specs/_existing-plakat-a1-hochformat.md` — retro-spec (existing template)
- `templates/_specs/_existing-zeitung-a4-grun.md` — retro-spec (existing template)
- `templates/_specs/themen-plakat-a3-quer.md` — new spec
- `templates/_specs/wahlaufruf-postkarte-a6-quer.md` — new spec
- `templates/_specs/wahltag-tueranhaenger.md` — new spec
- `templates/_specs/infostand-tent-card-a5-quer.md` — new spec
- `templates/_specs/kandidat-falzflyer-din-lang.md` — new spec

## Review Criteria, In Priority Order

**1. VISUAL QUALITY IS THE PRIMARY CRITERION.** Are the specs precise enough that two
implementer:innen would produce templates of equal visual quality?

**2.** Do the new specs propose layouts AT LEAST AS GOOD as the three retro-specs
(postkarte / plakat / zeitung)? Where is each new spec better, where weaker?

**3.** Hierarchy: Headline > Sub > Body > Akzent > Impressum on brand-niveau in every spec?

**4.** Typography mixing, whitespace, color use specified to brand level?

**5.** Risks: slots too tight, text lengths unrealistic, EPS scale undefined, fold/cut
dimensions inconsistent?

**6.** Does each Wahlkreuz spec correctly cite **D12 background-color contract** (Wahlkreuz
must be on Dunkelgruen / Hellgruen / Magenta — NEVER on White, NEVER on Gelb)?

**7.** Coordinate origin = trim top-left in every spec? Falz/Stanze positions consistent?

**8.** Messaging legality (NRWO §53, Mediengesetz §24) addressed in Wahlaufruf templates?

## Output Format (strict)

Write a Markdown report with one section per spec file plus a final consensus section.
For each spec:

```markdown
### <filename>

- **merge_ready:** yes | no | unclear
- **strengths:** <bullet list of what is well-specified>
- **blocking_findings:** <numbered list, each: "BLK-N: <issue>"; empty if none>
- **nice_to_have:** <bullet list of advisory items>
- **comparison_to_existing:** <2-3 sentences — where this new spec is better/equivalent/weaker than the retro-specs as a baseline>
```

End with:

```markdown
## Consensus

- **Total blocking findings:** N
- **Specs not merge_ready:** [list]
- **Recommendation:** ALL_MERGE_READY | ITERATE_REQUIRED
- **Summary verdict:** <one paragraph>
```

Be specific. "Headline too small" is unhelpful; "Themen-Plakat headline at 36pt is below
A3-distance threshold; recommend 60pt minimum" is helpful. Cite line numbers or section
headings when pointing at problems.

Do NOT request changes to be made. Only report findings.
