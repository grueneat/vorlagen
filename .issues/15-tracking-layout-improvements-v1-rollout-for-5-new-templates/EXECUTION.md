# Execution: Tracking — V1 rollout closure

**Started:** 2026-04-26 (rollout kickoff)
**Closed:** 2026-05-09
**Status:** complete

## Rollout sequence — all 5 implementations merged

| Order | Template | GitHub | Local | PR | Variant | Notes |
|:---:|---|---|---|---|---|---|
| 1 | `wahlaufruf-postkarte-a6-quer` | #32 | #17 | #44 | "Symbol-Tight" | ParaStyle migration template |
| 2 | `wahltag-tueranhaenger` | #33 | #18 | #46 | "Composed Hero" | Stat-card pattern |
| 3 | `themen-plakat-a3-quer` | #34 | #19 | #49 | "Evidence Cards" | aspect_fill fix |
| 4 | `infostand-tent-card-a5-quer` | #36 | #20 | #52 | "Hero Band" | First multi-panel + rotation contract |
| 5 | `kandidat-falzflyer-din-lang` | #37 | #21 | #53 | "Falz-Rhythm" + M-Basis fix | 6 panels, 22 CONSTRAINTS, M-Basis Trim-konform documented |

## Open questions resolution

| # | Question | Resolution |
|:---:|---|---|
| 1 | M-Basis-Konflikt for kandidat-falzflyer | RESOLVED in #21: rule at `brand_constraints.py:262` already correct (Trim-konform); 3 logos resized; build.py header comment updated |
| 2 | infostand-tent-card Falz-Spotcolor | RESOLVED in #20: Falz LAYER integrity asserted via lxml XPath in geometry test |
| 3 | wahltag-tueranhaenger Stanzkontur layer | RESOLVED in #18 (no spot-layer writes; geometry test asserts) |
| 4 | `samples/themen-wirtschaft.jpg` asset gap | RESOLVED via discovery in #21 research: `themen_wirtschaft_handwerk` already exists in library; no #13 dependency |
| 5 | ParaStyle migration policy | RESOLVED: add new `*-on-green` styles in parallel; mutate old style in same commit when shape stable; no deprecation marker |
| 6 | Diff-Stabilität vs Reference-SLAs | RESOLVED: 5 new templates have no committed reference; layout changes free per V1 brief |

## Acceptance criteria

- [x] Open questions 1-6 answered
- [x] All five #17-#21 issues merged with green `structural_check --all`
- [x] `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 has session-history rows per template (5 rows total; final V1-rollout-complete row appended in #21)
- [x] `improvements/HANDOFF.md` updated with PR links per template; V1 sequence marked COMPLETE

## Final verification (across all 5 templates)

| Check | Result |
|---|---|
| `python3 -m unittest discover tools/sla_lib/tests` | 754 OK (post-#21 baseline) |
| `python3 -m sla_lib.builder.structural_check --all` | 0 errors across 8 templates |
| `bin/check-stale-previews` | exit 0 |
| Geometry test files | 5 (one per V1 template) |

## Self-Check

- [x] All 5 V1 implementations merged
- [x] All systemic findings (Logo-Drift, HL/Sub-Gap, *-on-green ParaStyles) addressed across the suite
- [x] No "claude" / AI-attribution anywhere
- **Result:** PASSED
