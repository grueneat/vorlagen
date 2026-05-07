---
review_of: 5-review-buildpy-dsl-before-more-templates
review_type: issue
tool: gemini
area: B+C
---

<review>
<findings>
<finding severity="medium" id="B-1" area="B">
  <title>Redundant PT overrides in converter output</title>
  <location>tools/sla_to_dsl.py:364-374, 570-582</location>
  <description>The converter currently emits both mm and pt geometry on every frame. For AI-authored templates gated by visual diff, the pt overrides are noise and make the build.py harder to read/edit.</description>
  <fix>Implement --strict-bytes flag and drop xpos_pt/ypos_pt/width_pt/height_pt by default unless bit-exactness is required.</fix>
  <priority>P1</priority>
</finding>

<finding severity="low" id="B-2" area="B">
  <title>Unused blocks in blocks.py</title>
  <location>tools/sla_lib/builder/blocks.py</location>
  <description>All 8 existing blocks are unused in the three production templates. They were designed "forward" rather than "backward" from the corpus.</description>
  <fix>Replace with 5 evidence-driven blocks (PageNumber, Impressum, PageBackground, ContactBlock, ColumnTextStory) based on actual template idioms.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="B-3" area="B">
  <title>Giant extra_doc_attrs and extra_pdf_attrs literals</title>
  <location>templates/*/build.py</location>
  <description>Templates carry ~136 extra_doc_attrs and ~45 extra_pdf_attrs keys, with high duplication (113 and 34 identical keys respectively). This creates massive diff noise.</description>
  <fix>Introduce a Brand profile that hoists identical defaults; emit only the diff in build.py.</fix>
  <priority>P1</priority>
</finding>

<finding severity="low" id="B-4" area="B">
  <title>palette_replaces_ci=True hardcoded in converter</title>
  <location>tools/sla_to_dsl.py:931</location>
  <description>The converter hardcodes palette_replaces_ci=True, which suppresses ci.yml and forces manual re-registration of brand colors. This defeats the single-source-of-truth model.</description>
  <fix>Flip to palette_replaces_ci=False for re-authored templates and rely on CI-injected colors.</fix>
  <priority>P1</priority>
</finding>

<finding severity="low" id="B-5" area="B">
  <title>clip_edit=True rect path duplication</title>
  <location>templates/zeitung-a4-grun/build.py</location>
  <description>86 frames in Zeitung use clip_edit=True with a verbatim rectangle path in custom_path. This is redundant structural noise.</description>
  <fix>Modify the DSL to auto-emit the rectangle path when clip_edit=True is set on a rectangular frame.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="C-1" area="C">
  <title>DSL supports style=None for PDF recovery</title>
  <location>tools/sla_lib/builder/primitives.py:440-442, 483-496</location>
  <description>PDF recovery often loses style names. The DSL already supports style=None with default_style_attrs overrides, which is a valid primary path for PDF-to-DSL conversion.</description>
  <fix>Keep this path and document it for the PDF converter implementation.</fix>
  <priority>P2</priority>
</finding>

<finding severity="low" id="C-2" area="C">
  <title>x_mm/y_mm/w_mm/h_mm sufficiency</title>
  <location>tools/sla_lib/builder/primitives.py:334-343</location>
  <description>Absolute mm positioning is sufficient for all frame types even without anchor support, which is necessary for PDF/InDesign inputs where anchors might not be easily recoverable.</description>
  <fix>Ensure absolute positioning remains first-class in the DSL.</fix>
  <priority>P2</priority>
</finding>
</findings>

<measurement_verification>
<count name="extra_doc_attrs_per_template">136</count>
<count name="identical_extra_doc_attrs">113</count>
<count name="extra_pdf_attrs_per_template">45</count>
<count name="identical_extra_pdf_attrs">34</count>
<count name="zeitung_clip_edit_rect_frames">86</count>
<count name="zeitung_pgno_frames">12</count>
<count name="blocks_used_in_production">0</count>
</measurement_verification>

<p1_assessment>
<item id="2" verdict="kept">Strip pt overrides safety (with --strict-bytes flag for bit-exact requirement)</item>
<item id="3" verdict="kept">Replace blocks.py evidence-driven (crucial for migration)</item>
<item id="4" verdict="kept">Auto-emit clip_edit rect-path safety (major LOC reduction for Zeitung)</item>
</p1_assessment>

<verdict value="warn" critical="N" high="N" medium="Y">
  <blockers></blockers>
</verdict>
</review>
