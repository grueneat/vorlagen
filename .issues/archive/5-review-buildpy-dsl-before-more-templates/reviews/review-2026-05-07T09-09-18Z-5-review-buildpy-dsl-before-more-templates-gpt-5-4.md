---
review_of: 5-review-buildpy-dsl-before-more-templates
review_type: issue
review_mode: implementation
reviewed_at: 2026-05-07T09-09-18Z
tool: codex
model: gpt-5.4
duration_seconds: 385
---

<review>

<acceptance_criteria>
<criterion status="not_met" id="1">
  <text>/issue:review run completed against this issue with all three reviewers (Claude, Codex, Gemini) reading the actual code.</text>
  <evidence>.issues/5-review-buildpy-dsl-before-more-templates/ISSUE.md:65-70; .issues/5-review-buildpy-dsl-before-more-templates/PLAN.md:164-218 require a three-reviewer /issue:review output, but the branch under review only contains planning artifacts and this single-reviewer artifact.</evidence>
</criterion>
<criterion status="not_met" id="2">
  <text>Review report committed under .issues/5-.../REVIEW.md (or wherever /issue:review writes it) summarizing findings per area A–E.</text>
  <evidence>.issues/5-review-buildpy-dsl-before-more-templates/ISSUE.md:65-70; .issues/5-review-buildpy-dsl-before-more-templates/PLAN.md:165-218 define REVIEW.md as Task 1 output, and no corresponding reconciled REVIEW.md artifact exists in the reviewed branch state.</evidence>
</criterion>
<criterion status="partially_met" id="3">
  <text>Concrete API proposal for Brand, content blocks, and page-template layer — each with API sketch and a worked example showing how the existing Postkarte (smallest) collapses onto it.</text>
  <evidence>.issues/5-review-buildpy-dsl-before-more-templates/RESEARCH.md documents proposals and examples for Brand / blocks / layout, but they remain research notes rather than an accepted review artifact or reconciled API contract.</evidence>
</criterion>
<criterion status="met" id="4">
  <text>Line-count delta estimate for applying the new constructs to all three existing templates (especially Zeitung's 3244 lines).</text>
  <evidence>.issues/5-review-buildpy-dsl-before-more-templates/RESEARCH.md includes explicit line-count estimates for all three templates; those estimates are plausible against the current template sizes at templates/plakat-a1-hochformat/build.py:1-235, templates/postkarte-a6-kampagne/build.py:1-437, templates/zeitung-a4-grun/build.py:1-3244.</evidence>
</criterion>
<criterion status="not_met" id="5">
  <text>Prioritized list of follow-up issues filed (or queued) so the DSL hardening work is properly sequenced.</text>
  <evidence>.issues/5-review-buildpy-dsl-before-more-templates/ISSUE.md:65-70; .issues/5-review-buildpy-dsl-before-more-templates/PLAN.md:228-240 defer follow-up issue creation to later tasks, so this criterion is not satisfied yet.</evidence>
</criterion>
<criterion status="partially_met" id="6">
  <text>No templates/&lt;id&gt;/build.py for new templates may land before the agreed P1 hardening items from this review are merged. (Gating decision documented in the issue.)</text>
  <evidence>.issues/5-review-buildpy-dsl-before-more-templates/CONTEXT.md and .issues/5-review-buildpy-dsl-before-more-templates/PLAN.md:150-163 state the gate, but the authoritative review artifact that should confirm or challenge it had not been produced before this review.</evidence>
</criterion>
</acceptance_criteria>

<findings>

<finding severity="high" id="A-1" area="A">
  <title>Registering one paragraph style disables the entire CI style stack</title>
  <location>tools/sla_lib/builder/document.py:678-685</location>
  <description>_emit_styles() returns as soon as any custom paragraph style exists, so the document stops emitting every CI STYLE entry. That breaks the advertised compose layer because the stock blocks depend on CI names such as ci/headline-ultra, ci/impressum, ci/stoerer, and ci/body-12 at tools/sla_lib/builder/blocks.py:35-392. A document that adds one local style and one reusable block can therefore emit invalid style references.</description>
  <fix>Make custom paragraph styles additive over the CI stack, or introduce an explicit replacement mode. The default path should always preserve the shared CI styles.</fix>
  <priority>P1</priority>
</finding>

<finding severity="high" id="A-2" area="A">
  <title>The public Line primitive is broken at runtime and effectively dead</title>
  <location>tools/sla_lib/builder/primitives.py:711-753</location>
  <description>Line.to_pageobject() reads self.clip_edit even though Line does not define that attribute, so normal use raises AttributeError. The DSL reference still advertises Line at docs/dsl-reference.md:18-22, builder exports it at tools/sla_lib/builder/__init__.py:52-72, and tests import it at tools/sla_lib/tests/test_builder.py:20 without ever exercising it. Meanwhile the converter never emits Line, mapping Scribus PTYPE 5 to Polygon(custom_path=...) instead at tools/sla_to_dsl.py:738-753. This is a broken public API surface and redundant concept.</description>
  <fix>Either repair and test Line end-to-end, or remove it from the public surface and standardize on Polygon/custom_path for line-like shapes.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="A-3" area="A">
  <title>Anchor ergonomics are inconsistent with the published contract</title>
  <location>tools/sla_lib/builder/primitives.py:111-153</location>
  <description>resolve_anchor() only accepts top-level strings of the form vertical-horizontal plus center, but the docs describe offset strings such as bottom-20 at docs/dsl-reference.md:27-31. That offset form only works inside tuple axes via _resolve_axis(). The string path can also fail with KeyError instead of a clear validation message when a component is misspelled. This is not LLM-friendly because two visually similar spellings have materially different semantics.</description>
  <fix>Unify parsing so both top-level and tuple anchors support the same grammar, and raise explicit ValueError messages naming the offending attribute and accepted forms.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="A-4" area="A">
  <title>The DSL keeps too many overlapping paragraph-style channels</title>
  <location>tools/sla_lib/builder/primitives.py:49-82</location>
  <description>PARAGRAPH_OVERRIDE_ATTRS, DEFAULTSTYLE_OVERRIDE_ATTRS, VAR_OVERRIDE_ATTRS, style names, text_align, and legacy Run tuple coercion collectively create multiple ways to express paragraph styling. The closed override sets are defensible, but the public API still asks the caller to choose among several partially overlapping channels. That is manageable for handwritten code and brittle for future PDF/spec/IDML emitters.</description>
  <fix>Reduce the surface to one primary paragraph-style path plus one typed override path, then demote the legacy tuple Run path to compatibility-only status.</fix>
  <priority>P2</priority>
</finding>

<finding severity="high" id="B-1" area="B">
  <title>CI override path is stateful and ignores the requested ci_path after first use</title>
  <location>tools/sla_lib/builder/ci.py:127-135</location>
  <description>load_ci() caches a single global _CACHED instance regardless of path. Document.__init__ accepts ci_path at tools/sla_lib/builder/document.py:145-163, but once any document has loaded the default CI file, every later document reuses that first instance. That makes ci_path non-deterministic in multi-document processes and undermines the proposed multi-brand/input future.</description>
  <fix>Cache by resolved path or remove the global singleton from the public constructor path.</fix>
  <priority>P1</priority>
</finding>

<finding severity="high" id="B-2" area="B">
  <title>Chained text frames on master pages never emit NEXTITEM/BACKITEM links</title>
  <location>tools/sla_lib/builder/document.py:372-420, 967-976, 1011-1028</location>
  <description>_preallocate_chain_ids() reserves IDs for both masters and pages, but only _emit_page_item() patches NEXTITEM and BACKITEM. _emit_master_item() renames the node to MASTEROBJECT and appends it without chain wiring. The result is an inconsistent runtime path: page chains work, master-page chains silently lose linkage.</description>
  <fix>Apply the same chain patching logic to master items, or reject chained TextFrames on masters with explicit validation.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="B-3" area="B">
  <title>Soft-shadow erase flag does not round-trip through the converter</title>
  <location>tools/sla_lib/builder/primitives.py:381-390; tools/sla_to_dsl.py:388-399</location>
  <description>The builder emits SOFTSHADOWERASE, but the converter reads SOFTSHADOWERASEDBYOBJECT. A document using erase=True therefore round-trips back to erase=False. Tests only assert emission at tools/sla_lib/tests/test_dsl_extensions.py:409-414 and miss the conversion path.</description>
  <fix>Read the emitted key, add a regression test through sla_to_dsl, and only keep alternate legacy keys if Scribus actually produces them in source files.</fix>
  <priority>P2</priority>
</finding>

<finding severity="medium" id="B-4" area="B">
  <title>The converter and emitted templates still tell humans to hand-edit build.py, which conflicts with the locked workflow</title>
  <location>tools/sla_to_dsl.py:1-7, 945-947; templates/plakat-a1-hochformat/build.py:1-2</location>
  <description>The converter header and generated template header both say the emitted build.py is hand-edited thereafter. PLAN Task 1 and the hard constraints explicitly forbid manual template.sla edits and position build.py as generated DSL that future automation will harden. Keeping the human-hand-edit instruction in generated files will produce the wrong operating model for later contributors and agents.</description>
  <fix>Replace the generated header text with the actual workflow language used in CONTEXT/PLAN, including the render-fidelity gate.</fix>
  <priority>P2</priority>
</finding>

<finding severity="medium" id="B-5" area="B">
  <title>The current blocks layer is not evidence-driven and has no production caller</title>
  <location>tools/sla_lib/builder/blocks.py:1-400</location>
  <description>The three production templates do not import blocks at all, while only smoke tests and test_blocks.py use them. The tests in tools/sla_lib/tests/test_blocks.py:1-131 validate object counts and a few labels, not whether the block surface matches recurring production idioms. RESEARCH is correct that the current layer is aspirational rather than corpus-backed.</description>
  <fix>Replace the current block set with helpers derived from repeated patterns in the existing templates, and validate them by rewriting copies of the existing templates or representative fragments under render-diff tests.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="B-6" area="B">
  <title>Dropping pt geometry unconditionally is not yet safe for the converter path</title>
  <location>tools/sla_to_dsl.py:571-582</location>
  <description>Every converted frame currently carries both mm and pt geometry because _convert_pageobject() emits x_mm/y_mm/w_mm/h_mm and xpos_pt/ypos_pt/width_pt/height_pt together. That is redundant API surface, but it exists to preserve byte-level positioning against existing source files. PLAN already flags the risk at .issues/5-review-buildpy-dsl-before-more-templates/PLAN.md:157-163, and the code under review gives no proof that stripping pt geometry is byte-equivalent across sla_diff-sensitive fixtures.</description>
  <fix>Keep the simplification as a P1 goal, but gate it behind measured sla_diff coverage or a strict-bytes mode rather than removing the pt path globally in one step.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="C-1" area="C">
  <title>Documented extra_doc_attrs semantics understate how much layout-critical state the converter preserves</title>
  <location>docs/dsl-reference.md:108-122; tools/sla_to_dsl.py:875-940</location>
  <description>The docs describe extra_doc_attrs as metadata-like leftovers, but the converter preserves many page and rendering related keys, and the three production templates all carry 136 extra_doc_attrs plus 45 extra_pdf_attrs. My measurement matches RESEARCH: 113 doc keys and 34 pdf keys are identical across all three templates, with differences limited to a smaller tail of document-specific values. That means these bags are currently part of the real rendering contract, not a harmless escape hatch.</description>
  <fix>Promote the shared subset into a typed brand/document profile and narrow the remaining per-template extras to genuinely document-specific values.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="C-2" area="C">
  <title>Spec/PDF/IDML readiness is blocked more by API predictability than by raw feature coverage</title>
  <location>tools/sla_lib/builder/document.py:145-163; tools/sla_lib/builder/primitives.py:258-283, 295-753</location>
  <description>The DSL already supports absolute mm coordinates, optional style names, and typed paragraph/character style objects, so the minimum representational power for PDF/spec ingestion exists. The harder problem is predictability: too many constructor kwargs, multiple style channels, legacy Run tuple coercion, and ambiguous anchor forms. IDML-style constructs such as named styles and linked stories are partly represented, but master/page chain asymmetry and CI-path statefulness make the current contract harder to target safely from a converter.</description>
  <fix>Prioritize ergonomics and determinism over adding more primitives. A small typed schema for brand/layout/text plus a clearer frame contract will do more for multi-input readiness than another escape hatch.</fix>
  <priority>P1</priority>
</finding>

</findings>

<strengths>
<strength>The closed override sets in tools/sla_lib/builder/primitives.py:49-82 are a good constraint. They prevent an unbounded raw-attrs escape hatch while still covering the attributes the current converter knows how to preserve.</strength>
<strength>The render-fidelity discipline is well documented in docs/render-fidelity.md and docs/diff-tolerance.md, and PLAN.md correctly treats visual equivalence as the real safety rail for future refactors.</strength>
<strength>The converter is intentionally conservative about unsupported data. convert() and its helpers keep strict handling for unsupported attributes in tools/sla_to_dsl.py:301-350 and 840-1182 rather than silently discarding unknown Scribus state.</strength>
</strengths>

<traces>
<trace name="SLA → build.py conversion">SLADocument parsing feeds convert() at tools/sla_to_dsl.py:840-1182. Document-level leftovers are collected at 875-940, page/master structures are iterated around 1051-1125, and each PAGEOBJECT is lowered through _convert_pageobject() at 554-771, which also expands StoryText through _build_runs() at 416-550.</trace>
<trace name="build.py → Document.emit() → SLA XML">Each template constructs a Document and pages directly in templates/postkarte-a6-kampagne/build.py and peers, then Document.save() at tools/sla_lib/builder/document.py:365-370 calls _build_xml() at 423-501. XML emission then flows through _emit_styles/_emit_colors/_emit_page/_emit_page_item and related helpers at 631-910 and 1011-1028.</trace>
<trace name="clip_edit=True frame → XML emit">The converter captures CLIPEDIT plus path/copath into clip_edit/custom_path in _convert_pageobject() at tools/sla_to_dsl.py:587-597. Emission writes CLIPEDIT from TextFrame/ImageFrame/Polygon in tools/sla_lib/builder/primitives.py:451, 601, and 669, while _apply_shape_attrs() at 346-376 serializes the custom rect path that most Zeitung frames carry.</trace>
</traces>

<p1_assessment>
<item id="1" verdict="kept">Brand profile: kept. The shared 113 doc attrs and 34 pdf attrs across all three templates justify hoisting, and Option A is stronger than extending ci.py because the data is broader than colors/styles alone.</item>
<item id="2" verdict="reordered">Strip pt overrides: reordered behind deterministic regression proof. The simplification is desirable, but byte-equivalence risk is real and should be gated by sla_diff evidence or a strict-bytes converter mode.</item>
<item id="3" verdict="kept">Replace blocks.py: kept. The current block set has no production caller, so the replacement should be evidence-driven from recurring template idioms rather than expanded in place.</item>
<item id="4" verdict="demoted">Auto-emit clip_edit rect-path: demoted from unconditional P1 change to a guarded optimization. The Zeitung corpus has many rect-path clip frames, but not every clip_edit frame is safely derivable from width/height alone.</item>
<item id="5" verdict="kept">Spec schema: kept. A minimal schema is needed now so later PDF/spec/IDML adapters target a stable contract instead of today’s overlapping constructor channels.</item>
<item id="6" verdict="kept">DSL ergonomics pass: kept. Anchor normalization, Line cleanup, additive style emission, validation quality, and style-channel reduction are all real preconditions for letting more templates or converters target this API safely.</item>
</p1_assessment>

<line_count_estimates>
<template name="plakat-a1-hochformat" current="235" estimated_after_p1="170-190" confidence="medium"/>
<template name="postkarte-a6-kampagne" current="437" estimated_after_p1="280-330" confidence="medium"/>
<template name="zeitung-a4-grun" current="3244" estimated_after_p1="2200-2550" confidence="low"/>
</line_count_estimates>

<gating_decision>
<decision>confirmed</decision>
<reasoning>The reviewed code still has multiple P1 defects in the public DSL and builder runtime, and the current abstraction layer is not yet stable enough for more generated templates. The gate in ISSUE/CONTEXT is correct: adding more templates before the P1 hardening lands would multiply migration cost and converter ambiguity.</reasoning>
</gating_decision>

<verdict value="warn" critical="0" high="4" medium="7">
  <blockers>
    <blocker>Additive paragraph-style emission is required before reusable blocks and local styles can coexist safely.</blocker>
    <blocker>The public Line primitive is broken and should be fixed or removed before further DSL expansion.</blocker>
    <blocker>ci_path must become deterministic; the current singleton cache invalidates multi-brand or multi-input workflows.</blocker>
    <blocker>Master-page text chains need explicit NEXTITEM/BACKITEM support or validation before linked-story support is considered stable.</blocker>
  </blockers>
</verdict>

</review>
<verdict value="warn" critical="0" high="4" medium="7">
Significant DSL and builder correctness issues remain; no new templates should land until the P1 hardening pass is merged and verified against render-fidelity gates.
</verdict>

