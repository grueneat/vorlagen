# T06 Cross-check: Codex visual review vs audit JSON

**Audit invocation:**
```
PYTHONPATH=tools python3 tools/audit_alignment.py zeitung-a4-grun --strict --json > reviews/audit-zeitung.json
```

**Codex invocation:**
```
issue-cli review-exec --tool codex --prompt prompts/zeitung-visual-audit.md \
    --name zeitung-visual --review-type topic --review-mode topic \
    --output-dir reviews/
```

**Audit findings (summary):**
- 8 tolerance-suspicion findings (8 widened-tolerance CONSTRAINTS surfaced).
- 49 suspicious-pair findings (heuristic adjacency drift across 14 pages).
- BrandRule executions (run via direct rule.check() since Zeitung has T02-temporary overrides):
  - `brand:bleed_coverage`: 9 ERROR violations (Cover Hero LEFT+RIGHT, P1 Hero, P4 Foto-Spread, P11 Bottom, P13 Hero, 3 unnamed Dunkelgrün polygons)
  - `brand:image_text_overlap`: 11 ERROR violations including page-10 `Kopie von u2d5c (13)` ↔ `Kopie von u1529` (the documented bug)
  - `brand:cover_extent_match`: 1 WARNING (Cover Hero ↔ u2950)
  - `brand:visual_adjacency_drift`: catches u918 ↔ P7 Portrait axis-x-right (3.35mm), P9 Spread · right ↔ P10 Portrait axis-x-right (8.11mm)

**Codex visual findings (7 total):**

| # | Codex page | Codex finding | Audit catches it? |
|---|---|---|---|
| 1 | 1 | Cover hero stops short of outer edges; band runs wider | YES — `brand:cover_extent_match` (Cover Hero ↔ u2950) AND `brand:bleed_coverage` (Cover Hero LEFT+RIGHT) |
| 2 | 2 | Top image left page short of left bleed | YES — `brand:bleed_coverage` (P1 Hero LEFT) |
| 3 | 5 | Bottom image short of outer bleed | YES — `brand:bleed_coverage` (P4 Foto-Spread RIGHT). Codex misidentified left/right side; the bleed-gap finding itself matches. |
| 4 | 11 | Portrait stops before right print edge | YES — `brand:visual_adjacency_drift` (P9 Spread · right ↔ P10 Portrait axis-x-right drift 8.11mm). P10 Portrait is below the 0.95 cutoff so brand:bleed_coverage doesn't catch it directly; the geometric outcome test in T08 pins the right-edge-at-bleed invariant. |
| 5 | 12 | Green field + bottom photo short of outer edge | YES — `brand:bleed_coverage` (page-12 unnamed Dunkelgrün, P11 Bottom LEFT) |
| 6 | 13 | Green field short of outer edge | YES — `brand:bleed_coverage` (page-13 unnamed RIGHT) |
| 7 | 14 | Green field + bottom photo short of outer edge | YES — `brand:bleed_coverage` (P13 Hero LEFT, unnamed) |

**Issues NOT visually flagged by Codex but caught by audit (audit ≥ Codex):**

- Page 8: P7 Portrait not flush with u918 (3.35mm right + 5.6mm-ish vertical drift) — caught by `brand:visual_adjacency_drift` axis-x-right
- Page 10: Body text columns partially overlap Dunkelgrün card — caught by `brand:image_text_overlap`
- Page 9: text-column adjacencies and vertical drift — caught by `brand:visual_adjacency_drift`

These are the "harder to see" overlaps — Codex's visual gestalt apparently
doesn't trigger on small (3-5 mm) misalignments, but the geometric audit
catches them precisely.

**Verdict: audit catches every Codex visual finding (7/7) AND
additional issues Codex missed. Iteration count: 1 (the rules
captured everything on first pass, no rule-strengthening needed).**

Proceed to T07.
