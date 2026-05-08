---
id: '16'
title: 'Fix Zeitung A4: image frames placed past page boundary spilling into adjacent
  pages'
status: open
priority: high
labels:
- bug
- templates
- test
source: github
source_id: 32
source_url: https://github.com/GrueneAT/vorlagen/issues/32
---

# Fix Zeitung A4: image frames placed past page boundary spilling into adjacent pages

## Why

Direct evidence from `templates/zeitung-a4-grun/build.py` (round-trip-faithful from upstream Scribus):

| Print page | Frame | Bbox in SLA (mm) | Page bbox (mm) | Bug |
|:---:|---|---|---|---|
| 10 | `ImageFrame "P9 Spread"` | `x=210.0, y=0.0, w=210.0, h=126.1` | `0..210 × 0..297` (+3 bleed) | **Entirely past right edge by 207 mm.** Was authored as a spread image meant to span pages 10/11; one frame at `x=210` is the wrong shape for that intent. |
| 12 | unnamed `ImageFrame` | `x=210.0, y=−0.18, w=210.8, h=297.2` | `0..210 × 0..297` | **Full A4 image attached to the wrong page.** Belongs on page 13. |
| 12 | unnamed `ImageFrame` | `x=0, y=−0.2, w=210.8, h=213.9` | (same) | Minor right overflow (0.8 mm) — bleed-edge nudge, low concern but flagged for completeness. |
| 14 | unnamed `ImageFrame` | `x=0, y=−0.2, w=210.8, h=152.6` | (same) | Same minor 0.8 mm right overflow. |

User report: "Zeitung page 5 spills into page 4 / page 2 spills into page 3 / images aren't aligned with the text above". Inspection shows the page-numbering in the user report does not exactly match these findings (the user is likely counting spreads), but the *bug class* is the same and these are the only frames in the entire `templates/` tree whose bbox crosses page bounds (verified by sweeping every page's primitives against `page.width_pt / 2.83464566929` and `page.height_pt / 2.83464566929` ± `bleed_mm`).

## Scope

Mechanical fix — no design rework, no rendering re-evaluation.

1. **Replace `P9 Spread` (page 10, x=210, w=210)** with a `SpreadImage(left=page9, right=page10, ...)` call from #14 emitting two `inside_page`-clean halves, *or* — if the design intent was actually "this image only belongs on page 11, never spreads" — move the frame to page 10 (`page9` 0-indexed) at `x=0, y=0, w=210, h=126.14`. Decision criterion: read the corresponding cell in `gruene-zeitung-vorlage-original.pdf` page 11 vs. 10 (no PNGs, just `pdftotext`/`pdfimages` to confirm where the image data renders). Document the chosen interpretation in `templates/zeitung-a4-grun/README.md`.
2. **Move the page-12 full-A4 unnamed image** to page 13 (`page12` 0-indexed) at `x=0, y=−0.2, w=210.8, h=297.2`. Same decision logic — read PDF metadata, not PNGs.
3. **Trim the 0.8 mm right-edge overflows** on pages 12 and 14: `w=210.8 → 210`. They are residue of float-imprecise bleed handling at SLA emit time; the visual impact is zero but `inside_page` from #14 will flag them as warnings, and we want a clean baseline.
4. **Re-run `python3 -m sla_lib.builder.structural_check --all`** after the edits — `inside_page` errors must drop to zero. Remove the `meta.yml::brand_overrides` skip entries that #14 added with `"see issue #16"`.
5. **Re-run `tools/sla_diff.py`** against `gruene-zeitung-vorlage-original.sla` — round-trip fidelity is the existing contract. The two moved frames will create a controlled diff; document in `diff.yml` that this is intentional (commit msg: `12: fix(zeitung): move misattributed spread/page images to correct page; spread → SpreadImage`).
6. **Add a regression test** in `tools/sla_lib/tests/test_zeitung_overflow.py`: imports `templates.zeitung-a4-grun.build`, runs `inside_page` from #14 against `build_doc()`, asserts zero errors. (One test, no rendering, fast in CI.)
7. **Note in `templates/zeitung-a4-grun/README.md`** that the upstream Scribus original has these placement bugs and the round-trip therefore deliberately diverges from byte-faithful at these two locations.

## Acceptance criteria

- [ ] After this issue's commits, `python3 -m sla_lib.builder.structural_check --all` reports zero `inside_page` errors on `zeitung-a4-grun`.
- [ ] No `meta.yml::brand_overrides` entries remain on `zeitung-a4-grun` referencing this issue.
- [ ] `tools/sla_diff.py templates/zeitung-a4-grun/template.sla gruene-zeitung-vorlage-original.sla` produces a diff limited to: (a) the two moved frames, (b) the 0.8 mm width corrections — with each documented in the commit body and `diff.yml`.
- [ ] `tools/visual_diff.py` (or whatever the gallery `page-NN.png` regen step is wired up as) is re-run and the resulting `page-10.png`, `page-11.png`, `page-12.png`, `page-13.png`, `page-14.png` are visually re-checked **by the human reviewer in the PR**, not by Claude (the task explicitly forbids image inspection by the agent).
- [ ] One new regression test (`test_zeitung_overflow.py`) lives under `tools/sla_lib/tests/`, runs in <2 s, asserts zero `inside_page` errors.

## Open questions / risks

- **Spread intent vs. wrong-page intent for "P9 Spread"** — the anname says "Spread" but the geometry doesn't actually span. Recommend: read original-PDF page 10/11 with `pdfimages` to extract image XObjects, see which page the image renders to, and pick `SpreadImage` (if it renders across) vs. `single move` (if it renders only on one). Document the call in commit msg.
- **Diff-Stabilität gegen Reference-SLA** — `meta.yml::previews_for_sla` records a hash of the upstream original; this issue does **not** change that hash (it changes our build, not the upstream SLA we round-trip from). The diff will surface in `tools/sla_diff.py` and is the intentional payload of this issue.
- **The two minor 0.8 mm overflows** are arguably bleed-related and could be left alone. Recommendation: fix them anyway so `--all` is truly clean and `inside_page` doesn't need a warning-vs-error tolerance carve-out. If the round-trip diff complains, revert these two tiny fixes — we keep the core P9/P11 fix.

## Out of scope

- Any change to `gruene-zeitung-vorlage-original.sla` (it is upstream input; we are the consumer).
- Layout redesign of Zeitung pages — this is a placement bug fix, not a redesign.
- Other templates' overflow fixes — none exist (sweep verified).

## Dependencies

Blocked by: **#14** (needs `inside_page` and `SpreadImage`).

## Labels

bug, layout, zeitung, brand-fidelity
