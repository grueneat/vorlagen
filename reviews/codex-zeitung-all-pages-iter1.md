---
review_of: zeitung-all-pages-iter1
review_type: topic
review_mode: topic
review_topic: "Zeitung A4 visual alignment audit (Issue #24 pre-fix baseline)"
reviewed_at: 2026-05-09T17-07-56Z
tool: codex
model: gpt-5.4
duration_seconds: 267
---

<verdict value="warn" critical="0" high="0" medium="4">
Four visible image-fill defects remain, all presenting as white vertical bands where photo content does not reach the expected frame edge; no cut-line failure was observed, but the affected pages would still read as visibly misaligned in the rendered layout.
</verdict>

## Cross-check vs. audit JSON

Codex's run produced a single verdict block summarising the visual
inspection ("Four visible image-fill defects remain, all presenting as
white vertical bands where photo content does not reach the expected
frame edge"). It did not enumerate per-page; the model summarised the
class.

The audit JSON at `reviews/audit-zeitung-pre-fix.json` enumerates the
same defect class at the per-frame level — 9 individual `[ERROR]` /
`[WARNING]` `image_extent_warnings` entries from the new
`brand:image_fills_frame` rule:

| Audit JSON entry (page / frame / gap) | Class |
|---|---|
| page 0 `Cover Hero` (216.0x155.6mm renders 210.0x155.6mm — 6.0mm white margin) | bleed-gap (ERROR) |
| page 1 `P1 Hero` (210.0x130.2mm renders 207.0x130.2mm — 3.0mm white margin) | bleed-gap (ERROR) |
| page 4 `P4 Foto-Spread` (210.0x108.1mm renders 207.0x108.1mm — 3.0mm white margin) | bleed-gap (ERROR) |
| page 7 `P7 Portrait` (54.7x82.0mm renders 51.3x76.4mm — 3.4x5.6mm white margin) | letterbox (WARNING; interior) |
| page 9 `P9 Spread · left` (213.0x126.1mm renders 210.0x126.1mm — 3.0mm white margin) | bleed-gap (ERROR) |
| page 10 `P9 Spread · right` (213.0x126.1mm renders 210.0x126.1mm — 3.0mm white margin) | bleed-gap (ERROR) |
| page 10 `P10 Portrait` (77.7x94.4mm renders 66.6x94.4mm — 11.1mm white margin) | bleed-gap (ERROR) |
| page 11 `P11 Bottom` (210.0x83.3mm renders 207.0x83.3mm — 3.0mm white margin) | bleed-gap (ERROR) |
| page 13 `P13 Hero` (210.0x147.4mm renders 207.0x147.4mm — 3.0mm white margin) | bleed-gap (ERROR) |

**Mapping verdict:** Codex's "white vertical bands where photo content
does not reach the expected frame edge" describes EXACTLY the
INJECT_MAP-drift class that `brand:image_fills_frame` catches. The
audit's 9 enumerated frames are the per-frame breakdown of what
Codex summarised. No class-(b) MISSING entries (a letterbox/extent
variant the rule didn't catch). No class-(c) findings (z-order /
contrast / crop_focus / hyphenation / font-size — Codex did not
surface any).

**GATE DECISION:** PROCEED to T05. The new
`brand:image_fills_frame` rule detects every defect class Codex sees
on the pre-fix Zeitung renderings; T05's one-loop INJECT_MAP fix
addresses all 9 enumerated frames atomically.

**Iteration count:** 1 (no iter1b strengthening needed). 1 of 2-cycle
Codex budget consumed (locked decision #10).
