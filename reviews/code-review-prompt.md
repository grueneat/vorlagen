# Gate 2 Code Review — Reviewer Prompt

Review the DSL changes and 5 template builds in this repo. Read the code yourself.

## Files to review (read directly from the repo)

### DSL changes
- `tools/sla_lib/builder/primitives.py` — look at `pack_inline_image` (new) and
  Polygon `dash_pattern` (new attribute).
- `tools/sla_lib/builder/blocks.py` — 6 new blocks (WahlkreuzSymbol, FoldLine,
  DieCut, FoldedPanel, DoorHangerCutout, TableTentFold) + `_path_from_points_mm`
  helper.

### New templates (each has build.py + meta.yml + smoke test)
- `templates/themen-plakat-a3-quer/`
- `templates/wahlaufruf-postkarte-a6-quer/`
- `templates/wahltag-tueranhaenger/`
- `templates/infostand-tent-card-a5-quer/`
- `templates/kandidat-falzflyer-din-lang/`

### Smoke tests
- `templates/_smoke/test_themen_plakat_a3_quer.py`
- `templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py`
- `templates/_smoke/test_wahltag_tueranhaenger.py`
- `templates/_smoke/test_infostand_tent_card_a5_quer.py`
- `templates/_smoke/test_kandidat_falzflyer_din_lang.py`

### Reference (existing templates for comparison)
- `templates/postkarte-a6-kampagne/build.py`
- `templates/plakat-a1-hochformat/build.py` (auto-converted from SLA, large)

## Review Criteria, In Priority Order

1. **VISUAL QUALITY OVER CODE-ELEGANCE.** Look at preview PNGs:
   - `templates/themen-plakat-a3-quer/page-01.png`
   - `templates/wahlaufruf-postkarte-a6-quer/page-0{1,2}.png`
   - `templates/wahltag-tueranhaenger/page-0{1,2}.png`
   - `templates/infostand-tent-card-a5-quer/page-01.png`
   - `templates/kandidat-falzflyer-din-lang/page-0{1,2}.png`
   - And the existing 3 for baseline:
     `templates/postkarte-a6-kampagne/page-0{1,2}.png`,
     `templates/zeitung-a4-grun/page-0{1..14}.png`.
   Are the new templates AT LEAST AS GOOD as the existing 3 visually?

2. DSL patterns consistent with existing 3 templates' build.py?

3. New blocks reusable, with sensible API boundaries?

4. Each template's build.py matches its spec at
   `templates/_specs/<slug>.md` slot-for-slot?

5. Anything missing that undermines visual quality (bleed, default spacing,
   alignment bugs, frame collisions, tight whitespace, font hierarchy off)?

6. Wahlkreuz templates: D12 background-color contract enforced?

7. Round-trip diff of existing 3 templates still green?

8. pack_inline_image: correct qCompress format, used everywhere needed?

9. Smoke tests substantive enough?

## Output Format

Markdown report. For each section (DSL changes, 5 templates) provide:

- **merge_ready:** yes | no | unclear
- **strengths:** bullet list
- **blocking_findings:** numbered list ("BLK-N: ...")
- **nice_to_have:** bullet list
- **comparison_to_existing:** 2-3 sentences

End with consensus block:

```
## Consensus
- **Total blocking findings:** N
- **Recommendation:** ALL_MERGE_READY | ITERATE_REQUIRED
- **Summary verdict:** <one paragraph>
```
