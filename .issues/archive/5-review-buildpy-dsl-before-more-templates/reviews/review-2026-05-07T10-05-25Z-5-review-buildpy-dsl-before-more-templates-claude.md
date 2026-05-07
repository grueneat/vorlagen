---
review_of: 5-review-buildpy-dsl-before-more-templates
review_type: issue
review_mode: implementation
reviewed_at: 2026-05-07T10-05-25Z
tool: claude
---

<review>

<findings>

<finding severity="critical" id="A-1" area="A">
  <title>Line.to_pageobject references undefined self.clip_edit — AttributeError on emit</title>
  <location>tools/sla_lib/builder/primitives.py:738 (also references at 710-719)</location>
  <description>The `Line` dataclass body (lines 710-719) declares only `x1_mm, y1_mm, x2_mm, y2_mm, color, width_pt, layer, anname`. It does NOT inherit from `_Frame` and does NOT define a `clip_edit` attribute. Yet `to_pageobject` at line 738 reads `attrs["CLIPEDIT"] = "1" if self.clip_edit else "0"`. Any caller that does `page.add(Line(...))` will crash with `AttributeError: 'Line' object has no attribute 'clip_edit'` at save time. The class is exported in `__init__.py:64` and imported by `tests/test_builder.py:20`, but never instantiated — the converter at `sla_to_dsl.py:738-753` deliberately re-routes PTYPE=5 lines through `Polygon(custom_path=...)` because "reconstructing those from a single rotated frame is a fool's errand." So this bug has been latent: Line is on the public surface, advertised in `docs/dsl-reference.md:25`, but unusable. For LLM emission this is a trap — an LLM reading the docs would emit `Line(...)` and crash. Either fix or remove from public surface.</description>
  <fix>Either (a) add `clip_edit: bool = False` to the dataclass and any other `_Frame` fields the to_pageobject method touches, then add a smoke test that round-trips `page.add(Line(0,0,100,0))`; or (b) drop `Line` from the public re-exports (`__init__.py`), from `docs/dsl-reference.md:25`, and from `test_builder.py:20`, and document that PTYPE=5 lines are emitted as `Polygon(custom_path=..., line_color=..., fill='None')`. Option (b) matches the converter's existing strategy and is the lower-risk choice.</fix>
  <priority>P1</priority>
</finding>

<finding severity="high" id="A-2" area="A">
  <title>anchor= API is a four-shaped overload — unpredictable for LLM emission</title>
  <location>tools/sla_lib/builder/primitives.py:106-153</location>
  <description>`Anchor = Union[str, tuple]` accepts at least four distinct shapes: bare strings (`"center"`), 9-way string compass anchors (`"top-center"`, `"bottom-right"`), 2-tuples mixing numbers and direction strings (`("center", 30)`), and string-with-offset spec (`"bottom-20"`, `"right-15"`). The tuple form's axis order is `(x_spec, y_spec)` (line 131), but the string form's compass order is `(v, h)` (line 125: `v, h = parts`). An LLM emitting from a spec brief has no way to choose between these — it must read the resolver to know whether `"top-center"` means top-vertical-center-horizontal or bottom-horizontal-center-vertical. CONTEXT.md D2 mandates "regular, verbose, predictable" — this surface is the opposite. Per the corpus, the converter never emits `anchor=` (it always emits `x_mm/y_mm`), so the entire string-DSL is dead code on the SLA→build.py path; only blocks.py and hand-written specs would use it. For PDF and InDesign input paths the anchor surface is also unusable (those inputs only carry absolute positions).</description>
  <fix>Collapse to a single typed form. Two viable options: (a) drop `anchor=` entirely from the public surface, require `x_mm/y_mm/w_mm/h_mm`. The converter already does this and the LLM emitter can compute anchors directly. (b) Replace string DSL with a typed dataclass `Anchor(h='left'|'center'|'right'|float, v='top'|'center'|'bottom'|float, h_margin_mm=0, v_margin_mm=0)`. Either way: rip out `_resolve_axis` and the 9-way string compass parser. Update `blocks.py` to use the new shape. Update `docs/dsl-reference.md:31` to document one shape only.</fix>
  <priority>P1</priority>
</finding>

<finding severity="high" id="A-3" area="A">
  <title>TextFrame has four overlapping style channels — no canonical choice</title>
  <location>tools/sla_lib/builder/primitives.py:399-425</location>
  <description>`TextFrame` exposes four ways to set text formatting at the frame level: `style` (line 399, PARENT on DefaultStyle), `trail_style` (line 406, PARENT on closing trail), `default_style_attrs` (line 425, raw dict of FONT/FONTSIZE/FCOLOR/...), and `text_align` (line 404, ALIGN attribute on the PAGEOBJECT itself, NOT inside StoryText). On top of this, each `Run` carries `paragraph_style` (the closing `<para>`'s PARENT) and `paragraph_attrs`. An LLM authoring "make this frame use the headline style" has no anchor for the right channel. The converter always emits `style=` from DefaultStyle.PARENT, `trail_style=` from `<trail PARENT=...>`, and `default_style_attrs={...}` from extra DefaultStyle attrs (sla_to_dsl.py:617-640), so all four can co-exist on the same frame. The semantics are: `default_style_attrs` are frame-level paragraph defaults, `style` is the same channel via PARENT, `trail_style` is for the unterminated final paragraph, `text_align` is a vertical-text-align override on the PAGEOBJECT (not the StoryText). Three of the four are paragraph-style channels; one is a vertical-alignment channel. The naming `text_align` is actively misleading — it implies horizontal alignment.</description>
  <fix>(1) Rename `text_align` to `vertical_text_align` (or drop it; only the converter uses it for round-trip and most originals don't carry it). (2) Document that `style` is canonical for paragraph defaults; `trail_style` defaults to `style` when omitted; `default_style_attrs` is for DefaultStyle attrs not exposed by `style` (e.g. inline FONTSIZE override). Add a class-level docstring with this hierarchy. (3) Validate at `__post_init__` that `default_style_attrs` keys do not redundantly carry the same value the registered ParaStyle would set — this is the LLM trap that produces the silent-drop bugs the converter raised on (sla_to_dsl.py:625-635).</fix>
  <priority>P1</priority>
</finding>

<finding severity="high" id="A-4" area="A">
  <title>_Frame always carries both mm and pt geometry — pt overrides are emitted unconditionally by the converter</title>
  <location>tools/sla_lib/builder/primitives.py:289-324; tools/sla_to_dsl.py:566-582</location>
  <description>`_Frame` declares `xpos_pt/ypos_pt/width_pt/height_pt` (lines 321-324) as opt-in sub-ulp-precision overrides for byte-equivalent SLA round-trip. The converter emits BOTH the mm pair AND the pt pair on every frame (sla_to_dsl.py:571-582 unconditionally sets all four pt fields in `common_kwargs`). For 98 Zeitung frames + 18 Postkarte frames + 9 Plakat frames = 125 frames × 4 redundant lines = ~500 lines of dual geometry the LLM emitter has to know to ignore. Worse, it confuses the LLM emitter: which is canonical, mm or pt? The DSL `_xy_pt` method at line 326 says pt wins when both are set ("Verbatim pt overrides bypass the mm ↔ pt round-trip entirely"). So all 125 mm values in the existing build.py files are effectively ignored at emit time — an LLM that edits an mm value will see no rendered change.</description>
  <fix>Make pt overrides truly opt-in. (1) In the converter, only emit `xpos_pt/ypos_pt/width_pt/height_pt` when `_resolve_xy_mm` and `_resolve_xy_pt` would round-trip to different printed reprs (i.e. when `repr(mm * MM_TO_PT) != repr(pt_value)`). For all other frames, emit only `x_mm/y_mm/w_mm/h_mm`. (2) Add a regression test that asserts the converter on each existing template produces visual-diff-clean rebuilt SLAs without any pt overrides on the bulk of frames. (3) Document in `docs/dsl-reference.md` that pt overrides are converter-only; LLM emitters and hand authors should never use them.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="A-5" area="A">
  <title>Run legacy tuple form on public surface — dual API for the same concept</title>
  <location>tools/sla_lib/builder/primitives.py:258-283; blocks.py:50-53, 89, 165-166, 232-233, 247-250</location>
  <description>`_normalise_run` accepts three input shapes for a "run": a `Run` dataclass (canonical), a `(text, dict, sep)` tuple (legacy), or a bare string. The legacy tuple form uses STRING keys in the override dict (`"fcolor"`, `"fontsize"`, ...) — same names as Run dataclass attributes, but a separate, untyped channel. Used today in 6 places inside `blocks.py` (lines 50, 89, 165, 232, 233, 247). The converter NEVER emits the tuple form (sla_to_dsl.py:797-801 uses `Run(...)` constructor). So the tuple form is a "blocks-internal" shortcut, but it's exposed on the public surface and accepts arbitrary string keys with no validation — `(text, {"typo_key": x}, "para")` silently drops the typo. For LLM emission this is a footgun: an LLM that learns the tuple form from blocks.py will mis-spell keys and get silent drift.</description>
  <fix>Either (a) remove the tuple form entirely; rewrite `blocks.py` to use `Run(...)` constructors. The 6 sites are mechanical replacements. Or (b) keep the tuple form but restrict it to a typed shape (e.g. `(str, fcolor=str|None, separator=str|None)`) and document it as blocks-internal — never to be emitted by the converter or used in hand-authored templates. Option (a) is cleaner and matches CONTEXT.md D2's "no clever shortcuts."</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="A-6" area="A">
  <title>Color/Style enums are plain string class attributes — add no validation, only naming</title>
  <location>tools/sla_lib/builder/ci.py:140-181</location>
  <description>`Color.DUNKELGRUEN` evaluates to the string `"Dunkelgrün"`. Same for `Style.HEADLINE_ULTRA == "ci/headline-ultra"`. There is no validation that the string is in the brand palette — `Color.DUNKELGRUEEEEN` would NameError, but `fcolor="Dunkelgrueeen"` (the string) emits silently. The class is hardcoded (line 142-148) and does NOT introspect `shared/ci.yml`. A new color in ci.yml requires a manual edit to `_ColorEnum`. The converter (sla_to_dsl.py:776-783, line 802) emits raw strings (`fill='Dunkelgrün'`), never the enum, so the only consumers are `blocks.py` and hand-written templates. For LLM emission, the enum is no help — the LLM sees `fcolor='Dunkelgrün'` in the corpus and emits the same. The enum is human-authoring sugar in a "DSL optimized for LLM emission, not human reading" (CONTEXT.md D2). Net: enum adds maintenance cost, no safety.</description>
  <fix>(1) Drop `Color`/`Style` from the public re-exports (`__init__.py:50, 59-60`). (2) Update `blocks.py` to use raw strings (already what the corpus uses). (3) Update `docs/dsl-reference.md` to drop enum references. Alternative: keep them but auto-populate from `shared/ci.yml` at module load (call `load_ci()` in `_ColorEnum.__init__`) so a new CI color is auto-exposed. The first option is preferable for LLM-emission alignment.</fix>
  <priority>P2</priority>
</finding>

<finding severity="medium" id="A-7" area="A">
  <title>palette_replaces_ci=True set in all three templates — undermines shared/ci.yml as single source of truth</title>
  <location>templates/postkarte-a6-kampagne/build.py:24 (and the same in plakat + zeitung); tools/sla_lib/builder/document.py:154, 637-642</location>
  <description>All three converted templates pass `palette_replaces_ci=True`, which suppresses the CI brand palette entirely (document.py:637 `all_colors = dict(self._extra_colors)` — empty if no colors registered). Each template then re-registers all 7-8 brand colors via `doc.add_color(...)` calls (postkarte:35-42, identical CMYK across templates). This defeats the purpose of `shared/ci.yml`: there is no longer a single source of truth for brand color values, and a CMYK drift in one template cannot be detected by `tools/check_ci.py` without reading every template's add_color calls. Confirms RESEARCH.md finding §"Drift between the three templates" and §"Round-trip story." The RESEARCH document attributes this to converter byte-equivalence preservation, but functionally this is a real ergonomics regression for LLM emission — the LLM has to learn to copy 7 add_color lines per template rather than `Brand.gruene_noe()`.</description>
  <fix>Switch the converter to default `palette_replaces_ci=False`. Emit only template-LOCAL colors via `add_color`; let the brand palette flow from `shared/ci.yml` automatically. For colors that ARE in CI but the original SLA carried with slightly different CMYK (none today, but future-proof), the converter can emit a `add_color('Dunkelgrün', cmyk=(85,35,95,10))` override which document.py:641 honors. This collapses ~7 lines per template (5+8+8 = 21 lines across the corpus) and makes CI drift detection meaningful again.</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="A-8" area="A">
  <title>Document.__init__ has 18 kwargs; ~5 are converter byte-equivalence hooks an LLM emitter shouldn't see</title>
  <location>tools/sla_lib/builder/document.py:143-159</location>
  <description>The constructor accepts: `title, template_id, author, ci_path, layers, facing_pages, column_gap_default_pt, unit, deffont, defsize, first_page_num, palette_replaces_ci, hcms, doc_page_width_pt, doc_page_height_pt, extra_doc_attrs, extra_pdf_attrs`. Of these, `doc_page_width_pt/doc_page_height_pt` (lines 156-157) are explicitly described in their own comments as "round-trip precision" (lines 180-184), `palette_replaces_ci` (line 154) is the brand-bypass switch, and `extra_doc_attrs/extra_pdf_attrs` (158-159) carry the 113+34 keys identical across templates. For LLM emission from a spec or PDF, none of these five are needed; only `title, template_id, facing_pages, deffont, defsize, layers` matter. Per CONTEXT.md D6 the escape hatch stays, but the constructor surface should make plain which kwargs are LLM-relevant vs byte-equivalence hooks.</description>
  <fix>Group the constructor into two visible halves: (1) primary author-facing kwargs (template_id, title, facing_pages, brand=Brand.gruene_noe(), layers); (2) round-trip-precision kwargs (doc_page_width_pt, doc_page_height_pt, extra_doc_attrs, extra_pdf_attrs, palette_replaces_ci). Group via a module-level docstring and a code-comment block separator. Optionally add `**round_trip_kwargs` to bundle the second group, so build.py files written for new templates need only the first half.</fix>
  <priority>P2</priority>
</finding>

<finding severity="medium" id="A-9" area="A">
  <title>Validation error messages don't name the offending attribute on TextFrame</title>
  <location>tools/sla_lib/builder/primitives.py:430-432, 211-219; helpers at 85-104</location>
  <description>The TextFrame `__post_init__` at lines 430-432 calls `_validate_paragraph_attrs(self.trail_attrs)` and `_validate_defaultstyle_attrs(self.default_style_attrs)`. The helpers raise `ValueError(f"paragraph_attrs contains unsupported keys {bad!r}; allowed keys are ...")` (line 90-93). This says "paragraph_attrs" — but the call site passed `trail_attrs`. An LLM reading the error has no way to know which TextFrame attribute carried the bad keys. Same issue for `_validate_defaultstyle_attrs`: the function says "default_style_attrs" but it is called both for `default_style_attrs` AND would conceivably be called for other DefaultStyle-shaped fields in future. Run.__post_init__ at line 211-219 has the same problem for `paragraph_attrs` (it correctly names `paragraph_attrs`; this one is fine). The trail_attrs case is the bug.</description>
  <fix>Pass an `attr_name` parameter to the validator: `_validate_paragraph_attrs(self.trail_attrs, attr_name="trail_attrs")`. The helper formats `f"{attr_name} contains unsupported keys ..."`. Two-line change in primitives.py. Also extend tests/test_builder.py with one test case per validator path that asserts the error message contains both the attribute name and the bad key list.</fix>
  <priority>P2</priority>
</finding>

<finding severity="medium" id="A-10" area="A">
  <title>clip_edit=True on rectangular frames requires manual rect-path emit — 86 frames in Zeitung carry it</title>
  <location>tools/sla_lib/builder/primitives.py:300-310, 346-376; templates/zeitung-a4-grun/build.py (87 occurrences of clip_edit=True)</location>
  <description>The DSL's `clip_edit` field round-trips Scribus's CLIPEDIT="1" flag, which marks a frame whose clipping path was manually edited. When clip_edit=True, the original SLA also stores the verbatim rectangular path string `"M0 0 L<w> 0 L<w> <h> L0 <h> L0 0 Z"` (formatted via `_format_path_coord`'s `%.6g`, primitives.py:22-34) on the `path`/`copath` attributes. The converter (sla_to_dsl.py:589-593) faithfully captures the path via `custom_path=` and `fill_rule=` kwargs — but for plain rectangular clip-edited frames (the vast majority), the path IS the rect-path the DSL would emit anyway via `_format_rect_path` (primitives.py:37-41). 86 of Zeitung's 98 frames carry this exact pattern: 3 redundant lines of structural noise per frame. An LLM regenerating this template has to learn that clip_edit triggers the path emit; an LLM authoring fresh templates has no idea.</description>
  <fix>In `_apply_shape_attrs` (primitives.py:346-376), when `clip_edit=True` AND `custom_path is None` AND `corner_radius_mm == 0`, use FRTYPE=3 with the auto-generated rect-path (`_format_rect_path(w_pt, h_pt)`) instead of FRTYPE=0 with the same path. This makes `clip_edit=True` self-sufficient for rectangular frames. Update the converter to skip emitting `custom_path=` when the captured path matches the auto-rect-path within `_format_path_coord` precision. Saves ~250 lines on Zeitung. Verified: visual-diff stays clean because the emitted XML is identical (same path/copath/FRTYPE attributes).</fix>
  <priority>P1</priority>
</finding>

<finding severity="medium" id="A-11" area="A">
  <title>Document(extra_doc_attrs=...) emitted as one 7KB single-line dict literal — diff-hostile</title>
  <location>templates/postkarte-a6-kampagne/build.py:28; tools/sla_to_dsl.py:_py_value (line 132-133); _convert_pageobject Document emit path</location>
  <description>The converter formats dicts as single-line literals (`_py_value` at line 132-133: `"{" + ", ".join(...) + "}"`). For `extra_doc_attrs` with 136 keys this produces a single line of ~7000 characters (Postkarte build.py line 28). Any future diff against this line shows "1 line changed" with effectively no signal — every key has to be eyeballed against the previous version. An LLM editing the file has no anchor for which key to change; tooling like git blame, GitHub PR review, and visual diff all show the same blob. Same for `extra_pdf_attrs` (45 keys, line 29). Once the Brand hoist lands (P1-1) the residual diff dict is 23 keys, still long enough to want pretty-printing.</description>
  <fix>Update `_py_value` for dicts to emit one key per line when len(d) > 4: `"{\n        " + ",\n        ".join(f"{_py_value(k)}: {_py_value(v)}" for k, v in d.items()) + "\n    }"`. Re-run the converter on all three templates; visual diff confirms identical render. This is a near-zero-risk converter cleanup that pays off independent of P1-1.</fix>
  <priority>P2</priority>
</finding>

<finding severity="low" id="A-12" area="A">
  <title>`unit` and `first_page_num` Document kwargs unused / partially wired</title>
  <location>tools/sla_lib/builder/document.py:150, 153, 168, 171</location>
  <description>The constructor accepts `unit: str = "mm"` (line 150) and stores it (line 168). The emitter emits a hardcoded `"UNITS": "1"` (document.py:528) regardless of the kwarg. So passing `unit="pt"` does nothing. Similarly `first_page_num` (line 153, 171) is stored but never read by `_doc_attrs` (the emitted FIRSTNUM is hardcoded "1" at line 573). Either wire them or drop them — silent no-op kwargs are LLM traps because an LLM that emits `first_page_num=2` will be confused when the SLA still numbers from 1.</description>
  <fix>(a) Wire: `attrs["UNITS"] = {"mm": "1", "pt": "0"}.get(self.unit, "1")` and `attrs["FIRSTNUM"] = str(self.first_page_num)`. (b) Drop both kwargs from the constructor signature and any tests/doc references. The converter doesn't pass either kwarg, so dropping is safe and minimal.</fix>
  <priority>P3</priority>
</finding>

<finding severity="low" id="A-13" area="A">
  <title>blocks.py is corpus-disconnected — 8 blocks; 0 used by the 3 production templates</title>
  <location>tools/sla_lib/builder/blocks.py (entire file); templates/_smoke/* uses them but production templates do not</location>
  <description>`blocks.py` ships 8 blocks (Headline4Line, StoererBadge, ImpressumLine, ImpressumBlock, SocialHandlesVertical, LogoCorner, EventDetails, Masthead, ContentTeasers, ArticleHeadline, ArticleBody, QuoteSidebar — 12 in fact). Grep confirms none are imported by production templates (postkarte/plakat/zeitung); only `templates/_smoke/postcard-a6/build.py` and `templates/_smoke/zeitung-mini/build.py` reference them. RESEARCH.md §"Existing blocks coverage" confirms: every production build.py is purely primitive-level. Because the converter (sla_to_dsl.py) emits primitives, even after re-conversion these blocks would not be used. The blocks were designed forward (what we wished templates looked like) rather than backward from the corpus (what idioms actually recur). Result: blocks code is technically tested by test_blocks.py but never exercised against real templates → silent quality drift waiting to happen on a bug like A-1 (Line).</description>
  <fix>Replace with 5 evidence-driven blocks per RESEARCH.md proposal: `PageNumber` (12 sites in Zeitung), `Impressum` (3 sites), `PageBackground` (3 sites), `ContactBlock` (1 site, stable shape), `ColumnTextStory` (replaces the link_to chain pattern). Validate by re-authoring Postkarte from primitives → blocks and visual-diffing. Keep the 12 fictional blocks under `blocks.legacy` for one release; mark deprecated. test_blocks.py rewrites to test the 5 new ones (~134 LOC of test changes per RESEARCH).</fix>
  <priority>P1</priority>
</finding>

<finding severity="low" id="A-14" area="A">
  <title>Page.label "BEISPIELSEITE" auto-injection silently consumes ItemID #1 on labeled pages</title>
  <location>tools/sla_lib/builder/document.py:485-497</location>
  <description>When a Page has a `label`, document.py:485-497 auto-injects a non-printing TextFrame on the Hilfslinien layer at the top of the page. This frame consumes one ItemID and one PAGEOBJECT slot before the user's frames. For an LLM regenerating a labeled template, the frame counts won't match the original — the converter never emits labels (it doesn't preserve the BEISPIELSEITE label info), but a fresh hand-spec might. Side-effect-on-emission features like this are LLM-hostile because they are invisible from the constructor call. Low priority because no production template uses labels.</description>
  <fix>Either (a) drop the `label` field entirely (no production template uses it; converter doesn't emit it). Or (b) move label rendering to opt-in via `page.add_label_overlay()` so the side effect is explicit. Option (a) is cleaner.</fix>
  <priority>P3</priority>
</finding>

<finding severity="low" id="A-15" area="A">
  <title>SLAEditor.set_text uses a destructive fallback that loses inline tags — but is on the deprecation path</title>
  <location>tools/sla_lib/editor.py:51-70</location>
  <description>If line counts don't match between input and existing ITEXT runs, the fallback (lines 57-69) wipes ALL ITEXT/breakline/tab/trail children and reconstructs from a single ITEXT's attribs. This loses tabs, separators, and var elements (page-number vars in the Zeitung). Only relevant for the legacy slot-fill render pipeline, not the builder pipeline. Per RESEARCH.md the editor is "internal vs. public boundary" — slot.py + editor.py + reader.py are the legacy slot path. Keep it limited; do not export from the builder package surface. (Already not exported.)</description>
  <fix>Document at the top of editor.py that this is the legacy slot-fill path, kept for backward compat with `tools/render.py`'s slot rendering, and is NOT to be used for build.py-driven templates. Add a one-line module docstring confirming the boundary. No code change.</fix>
  <priority>P3</priority>
</finding>

<finding severity="low" id="A-16" area="A">
  <title>Brand "single source of truth" claim in shared/ci.yml is undermined by every template</title>
  <location>shared/ci.yml (header, lines 1-13); templates/*/build.py extra_doc_attrs lines</location>
  <description>shared/ci.yml header advertises itself as the single source of truth: "All templates emitted by the DSL reference colors and styles by name from this file." But (1) palette_replaces_ci=True bypasses it (A-7), (2) the per-document ParaStyle stack at postkarte:46-54 re-declares every named brand style with explicit fontsize/linesp/fcolor (Headline-sehr-wichtig, Vollkorn-Headline-sehr-wichtig, etc.), so brand drift is per-template, (3) the deffont differs between Plakat ("Gotham Narrow Black"), Postkarte ("Gotham Narrow Black"), and Zeitung ("Gotham Narrow Book") — but ci.yml says ci/default has font "Gotham Narrow Book". The "single source of truth" is currently a single source of advisory text. P1-1 (Brand profile) should make ci.yml authoritative and detect drift via `tools/check_ci.py`.</description>
  <fix>(1) After P1-1, extend `tools/check_ci.py` to verify a template's emitted ParaStyle stack inherits from CI styles and only overrides where intended. (2) Document in CONTEXT.md or a follow-up issue that the existing per-template ParaStyle re-declarations come from the converter capturing original SLA values; future hand-spec inputs go through the Brand profile by default and only diff-from-CI when explicitly named.</fix>
  <priority>P2</priority>
</finding>

</findings>

<strengths>
<strength>Closed override sets (PARAGRAPH_OVERRIDE_ATTRS, DEFAULTSTYLE_OVERRIDE_ATTRS, VAR_OVERRIDE_ATTRS at primitives.py:49-82) are validated in __post_init__ and the converter raises UnhandledElement (sla_to_dsl.py:500-506, 631-635) on any unknown attribute. This is exactly the discipline CONTEXT.md D2 mandates — no `raw_attrs` escape hatch on frames/styles/runs.</strength>
<strength>PARENT-style inheritance is preserved by only-non-None emission of ParaStyle/CharStyle attributes (document.py:742-810). Optional-field discipline in styles.py is rigorous: every field except `name` is `Optional[T] = None`, and the emitter writes only attributes whose value is not None.</strength>
<strength>Run dataclass at primitives.py:159-219 has a clear emission contract (ITEXT → var → separator) documented in the docstring; the var-before-separator ordering is explicit and tested. The validation hook at line 211-219 catches bad var_attrs keys at construction time, not at save time.</strength>
<strength>Inline-image base64 round-trip (primitives.py:576-585; sla_to_dsl.py:142-155) is documented and explained — preserves byte-equivalence and avoids the qCompress/PNG re-encode bug. Good rationale for an unusual choice.</strength>
<strength>ItemID chain pre-allocation (document.py:372-420) walks frames in emit order, builds inverse-map and head-detection, and allocates IDs depth-first per chain. Solves NEXTITEM/BACKITEM resolution cleanly.</strength>
<strength>BLEED_GUARDED set (document.py:903-906) prevents extra_pdf_attrs from accidentally desynchronizing PDF page bbox from SLA bleed. Defensive emission discipline.</strength>
<strength>_fmt_num (document.py:50-72) uses repr() rather than %.6f — preserves shortest-round-trip precision. Documented rationale ties this to a real rendering bug (inline-image LOCALSCX 0.0438778076573352 sub-pixel drift). Concrete connection between the choice and observed visual artifacts.</strength>
<strength>Anchor.fluent link_to() returns the target frame (primitives.py:434-438), enabling `a.link_to(b).link_to(c)` chains. The pattern is small and documented in dsl-reference.md:96-104.</strength>
</strengths>

<traces>
<trace name="build.py → Document.emit() → SLA XML">
1. templates/postkarte-a6-kampagne/build.py:15 — `doc = Document(...)` reaches document.py:143 (__init__).
2. build.py:35-42 — `doc.add_color(...)` × 8, document.py:206-222 stores in `_extra_colors`.
3. build.py:44-54 — `doc.add_para_style(ParaStyle(...))` × 9 stores in `_extra_para_styles` (document.py:224-226).
4. build.py:56-66 — `doc.add_master(...)` returns Page object (document.py:240-289).
5. build.py:68-87 — `doc.add_page(...)` × 2; appends to `pages` (document.py:291-363).
6. build.py:89+ — `page0.add(Polygon(x_mm=…, fill='Dunkelgrün', clip_edit=True, custom_path=None — wait, it's not set, but document doesn't auto-emit rect-path, FRTYPE=0 default goes through _apply_shape_attrs at primitives.py:370-373))`.
7. Save: `doc.save(out)` → `_build_xml` (document.py:423) → `_preallocate_chain_ids` → emit DOCUMENT, COLORs, STYLEs, LAYERs, MASTERPAGE, PAGE, MASTEROBJECTs, PAGEOBJECTs.
8. Each PAGEOBJECT: `item.to_pageobject(idgen, page)` (primitives.py:440 for TextFrame, 587 for ImageFrame, 654 for Polygon). _xy_pt at line 326 reads `xpos_pt/ypos_pt` and bypasses mm if both set.
9. _apply_shape_attrs (primitives.py:346-376) sets FRTYPE/path/copath/fillRule based on custom_path / corner_radius_mm.
10. extra_doc_attrs override (document.py:601-602) silently overwrites any DSL default, including PENLINE/PENTEXT/PENSHADE.
11. extra_pdf_attrs (document.py:907-910) writes PDF block, except for BLEED_GUARDED keys.
12. lxml.etree.ElementTree.write at document.py:369 with pretty_print=True — final XML.

Bug surface from this trace: step 6 emits BOTH x_mm AND xpos_pt for every frame (sla_to_dsl.py:571-582); step 8 ignores x_mm. Hand-edits to x_mm produce no rendered change. (Finding A-4.)
</trace>
</traces>

<p1_assessment>
<item id="1" verdict="kept">Brand profile via Option A (new tools/sla_lib/builder/brand.py dataclass) — CONFIRMED as the primary P1. The dataclass is a clean hoist surface for the 113 identical extra_doc_attrs keys + 34 identical extra_pdf_attrs keys + the brand para/char style stack. Option B (extending _CI in ci.py) conflates "brand identity" with "Scribus-runtime defaults"; Option C (Document reads defaults eagerly) leaks brand-specific defaults into the DSL surface and won't extend cleanly to multi-input adapters. Strong recommendation: A. Worth pairing with finding A-7 (palette_replaces_ci flip) so the brand colors come from CI by default, not from per-template add_color calls.</item>
<item id="2" verdict="kept">Strip pt overrides — CONFIRMED P1, with the guard described in finding A-4. Safe to drop on any frame where `repr(mm * MM_TO_PT) == repr(xpos_pt)` (i.e. mm round-trip is bit-exact). Keep on the ~6-13 inline-image frames that carry sub-ulp precision (HEIGHT="27.7755590551181"-shape values). The visual-diff gate validates render fidelity, not byte equivalence; sla_diff may flag attribute differences but is not the gate. Verify by running `pytest tools/sla_lib/tests/test_sla_to_dsl.py` after the strip and confirming render diffs are within tolerance.</item>
<item id="3" verdict="kept">Replace blocks.py with 5 evidence-driven blocks — CONFIRMED P1. The proposed list (PageNumber, Impressum, PageBackground, ContactBlock, ColumnTextStory) maps directly to ≥2 corpus instances each. Recommend adding a 6th: `MasterpageRectangle` for the full-bleed Polygon-as-page-background pattern recurring on Zeitung Titelseite + 2 of the inner pages. Keep the existing 12 fictional blocks under `blocks.legacy` for one release. Test changes are mechanical (~134 LOC).</item>
<item id="4" verdict="kept">Auto-emit clip_edit rect-path — CONFIRMED P1. See finding A-10. `_apply_shape_attrs` change is ≤6 lines. Saves ~250 lines on Zeitung alone (86 frames × 3 lines). Risk: a frame whose original `custom_path` differs from the auto-rect-path due to `_format_path_coord`'s %.6g rounding — the converter must emit `custom_path=` only when the captured path differs from `_format_rect_path(w_pt, h_pt)` byte-for-byte. Add a regression test on a Zeitung frame that's known to carry a non-rect clip path (e.g. one of the page-mask frames).</item>
<item id="5" verdict="kept">Spec-file schema sketch — CONFIRMED P1, but lower priority than 1-4. The schema sketch in RESEARCH.md is sufficient as `docs/spec-input-schema.md`. No converter implementation needed in this issue (deferred per CONTEXT.md). The schema unblocks downstream issues for spec→build.py, PDF→build.py (which would emit a similar shape), and InDesign→build.py. Recommendation: ship as documentation only, no code; the doc anchors future converter work.</item>
<item id="6" verdict="reordered">DSL ergonomics pass — CONFIRMED P1, but split into discrete sub-items per finding above. Genuinely P1: A-1 (Line bug — must fix before any new template touches Line), A-2 (anchor= overload — must fix before LLM emission targets the API), A-3 (4-channel style API — document the canonical channel; rename text_align), A-5 (drop Run tuple form), A-7 (palette_replaces_ci default flip — pair with #1), A-9 (validation error attr_name). P2 / P3: A-6 (Color/Style enums), A-8 (Document kwargs grouping), A-11 (single-line dict diff hostility), A-12 (unit/first_page_num), A-14 (Page.label), A-15 (editor docstring). The original "DSL ergonomics pass" is correct in spirit; just unbundle into the discrete fixes above.</item>
</p1_assessment>

<line_count_estimates>
<template name="plakat-a1-hochformat" current="235" estimated_after_p1="160" confidence="high"/>
<template name="postkarte-a6-kampagne" current="437" estimated_after_p1="260" confidence="high"/>
<template name="zeitung-a4-grun" current="3244" estimated_after_p1="2200" confidence="medium"/>
</line_count_estimates>

<gating_decision>
<decision>confirmed</decision>
<reasoning>Issue 5's gating policy ("no `templates/<id>/build.py` for new templates may land before the agreed P1 hardening items from this review are merged") is the right call and remains in force. The P1 set (Brand profile, pt-override strip, evidence-driven blocks, clip_edit auto-rect, spec schema, ergonomics pass) is a coherent, dependency-ordered set: each item independently improves LLM-emission quality, and 1+2+3+4 jointly remove ~50% of the per-template noise. New templates landing before these merge would calcify the current copy-paste shape and double the eventual migration work. One critical bug surfaced (A-1, Line.clip_edit AttributeError) is itself a hard gate — Line is exported on the public surface but unusable, so an LLM following docs/dsl-reference.md will produce a crashing template. That fix is mechanical and must land before any documentation aimed at LLM emitters claims a stable Line API. CONTEXT.md migration ordering (Postkarte → Plakat → Zeitung) is also confirmed correct: Postkarte's 437 lines is the highest signal-to-noise validation of the new constructs, and the line-count delta there (~40% reduction) will be the empirical sanity check on the Zeitung magnitude estimate before its 3244 lines are touched.</reasoning>
</gating_decision>

<verdict value="fail" critical="1" high="4" medium="8">
  <blockers>
    <blocker>A-1: `Line.to_pageobject` references undefined `self.clip_edit` (primitives.py:738). Line is exported in `__init__.py:64`, advertised in `docs/dsl-reference.md:25`, and imported by `test_builder.py:20`, but any instantiation+save crashes with AttributeError. Either fix the dataclass (add `clip_edit` and other `_Frame` fields) or remove Line from public surface and the converter docs. Must land before any LLM-emission-facing documentation claims a stable Line API.</blocker>
  </blockers>
</verdict>

</review>
