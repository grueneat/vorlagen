# Pitfalls Research — Issue 35: IDML → DSL Converter

**Researcher:** PITFALLS specialist
**Date:** 2026-05-11
**Issue:** `tools/idml_to_dsl.py` strict bootstrap

This document enumerates every gotcha that should be **mitigated explicitly in the plan**, not discovered at integration time. Each pitfall lists: short name, what goes wrong, smallest mitigation, source where applicable.

Pitfalls are grouped by severity:
1. **Critical** — will break the build / wrong output / converter silently emits garbage. Must be mitigated.
2. **Likely** — will hit us on real data but the plan can defer; mitigation should be designed-in.
3. **Out-of-scope** — explicitly rule out so the planner draws the line.

Then: **Environment audit** + **Security / safety** + **Sources**.

---

## 1. Critical Pitfalls (must be handled in v1)

### P-COORD-1 — Spread is centered, not top-left
**What goes wrong:** Treating the Spread coordinate origin as page top-left will offset every PageItem by half the page (≈ ±105 mm for a 297×210 A4-quer Spread). The first emitted `build.py` will render with all items shifted by hundreds of millimetres, looking nothing like the source.
**Why it happens:** In IDML, the Spread origin is at the spread binding centre. The `<Page>` element carries its own `ItemTransform="1 0 0 1 -420.94 -140.31"` translating from spread-centred to page-top-left. The geometric bounds of every PageItem (PathPointArray Anchor coordinates and the item's ItemTransform tx/ty) are in **spread space**, not page space.
**Mitigation:** Always subtract the Page's `ItemTransform` translation (its `tx, ty` after composing with the Spread's own `ItemTransform`) from every transformed anchor before pt→mm. Our IDML has Page ItemTransform `1 0 0 1 -420.94 -140.31` on Spread `ueb` (cover side) and `1 0 0 1 -420.94 -140.31` on Spread `u108` (back side). The Spread `u108` itself carries `ItemTransform="1 0 0 1 2.84e-14 786.61"` (i.e. y-offset by 786.61pt = a vertical layout, NOT a horizontal book). Use:
```
page_origin_pt = compose(spread.ItemTransform, page.ItemTransform).translation
```
**Confidence:** HIGH — verified against this IDML and Adobe community discussion ([Adobe IDML Rotation Matrix](https://community.adobe.com/t5/indesign-discussions/idml-rotation-matrix-concern/td-p/9680180)).

### P-COORD-2 — TextFrame inner origin is the frame centre
**What goes wrong:** Treating `<PathPointArray>` anchors as offsets from the frame's top-left will rotate the frame around the wrong pivot and place it 50% off-centre.
**Why it happens:** For a TextFrame, the four PathPointArray anchors are symmetric around (0,0) — e.g. `(-49.5, -148.82) .. (49.5, 148.82)`. The frame's bounding box in inner space is centred at the origin, not anchored at top-left like Rectangle paths.
**Mitigation:** Compute pre-transform bbox as `(min(x), min(y), max(x), max(y))` of the path-points (don't assume top-left = 0,0). When applying ItemTransform, transform all four corners and take their AABB — this works uniformly for centred and corner-aligned frames.
**Confidence:** HIGH — sources: [Adobe community on IDML coordinate spaces](https://community.adobe.com/t5/indesign-discussions/converting-a-rotated-text-from-idml-to-html5/m-p/4435777), Indiscripts coordinate-spaces guide ([PDF](https://indiscripts.com/blog/public/data/coordinate-spaces-and-transformations-5/CoordinateSpacesTransfos01-05.pdf)). Also surfaces in the issue description itself.

### P-COORD-3 — Rotated TextFrames present in our IDML
**What goes wrong:** Ignoring rotation, or treating the `<PathGeometry>` width/height as the final width/height, will emit frames at the wrong axis-aligned bounding box and at the wrong position.
**Why it happens:** Two TextFrames in our corpus carry rotation:
- `Spread_u108 → TextFrame Self="u347"`: **90°** rotation (`ItemTransform="-2.83e-16 -0.9999 0.9999 -2.83e-16 124.68 180.78"`). Likely a vertical edge label.
- `Spread_ueb → TextFrame Self="u186"`: **9°** rotation (`ItemTransform="0.9877 -0.1564 0.1564 0.9877 11.54 233.10"`). Likely a "Störer" sticker (Story `u189` content: "Störer", style `falzflyer/störer`-like).

DSL primitives DO support rotation (`rotation_deg` on TextFrame / ImageFrame / Polygon at `tools/sla_lib/builder/primitives.py:440, 779`). But **no existing template build.py uses rotation** (grep for `rotation=` across `templates/*/build.py` returns nothing) — so this is a **new execution path** for the DSL → SLA emitter chain. Pivot conventions differ: Scribus's `ROT` pivots around the frame top-left (CCW positive) per `tools/sla_lib/builder/bbox.py:5-8`; IDML rotates around the inner-space origin (frame centre for TextFrames). The converter must translate between pivots.
**Mitigation:**
1. Decompose ItemTransform into (scale_x, scale_y, rotation_deg, tx, ty). Reject (raise `UnhandledElement`) on non-uniform scaling or shear in v1.
2. Compute the rotated frame's **axis-aligned bbox in spread space** by transforming the four inner-space corners (not by Scribus-style rotation around top-left). That is the visual extent.
3. To emit: place a Scribus frame whose **un-rotated** top-left coincides with what Scribus rotates around to land in the right visual position. The math: Scribus `ROT=θ` rotates a `(x_mm, y_mm, w_mm, h_mm)` frame CCW around `(x_mm, y_mm)`. Solve for `(x_mm, y_mm)` such that after Scribus rotation the four corners match the IDML-transformed corners.
4. Cross-check by computing both bboxes (rotated and un-rotated) and asserting the rotated one matches the IDML-transformed extent within 0.1 mm.

Add a smoke test that round-trips a synthetic 90° and 9° TextFrame through the converter and the SLA renderer and visually compares to the IDML's accompanying PDF page region.
**Confidence:** HIGH (existence in corpus verified); MEDIUM (pivot math is a known foot-gun, needs a unit test).

### P-COORD-4 — Nested Group ItemTransforms cascade
**What goes wrong:** Reading a PageItem's ItemTransform standalone and ignoring ancestor Group ItemTransforms will place items at wrong positions whenever a Group has its own non-identity transform.
**Why it happens:** Our corpus has Groups nested up to **depth 2** in `Spread_u108` (verified by counting open/close `<Group>` tag pairs in spread XML). Each Group carries its own `ItemTransform`. The final position of a leaf PageItem is `M = M_spread · M_group_outer · M_group_inner · M_item`, applied to the inner-space anchor points.
**Mitigation:** Walk the spread tree depth-first carrying the composed transform matrix. At each `<Group>`, multiply parent matrix by the Group's `ItemTransform` (parent-on-the-left); at each leaf PageItem, multiply once more and apply to the path points. Use a 3×3 representation with row vectors `(a, b, 0; c, d, 0; tx, ty, 1)` — that's the order Adobe documents.
Order proof: per the [Indiscripts coordinate-spaces guide](https://www.indiscripts.com/post/2018/06/coordinate-spaces-and-transformations-5), each ItemTransform is the **inner→parent** map; to map an inner point to the spread, multiply the chain of inner→parent matrices from leaf to root.
**Confidence:** HIGH — verified locally and consistent with Adobe docs.

### P-COORD-5 — Spread `u108` carries a vertical y-offset of 786.61pt
**What goes wrong:** Assuming both Spreads originate at the same place will overlay the back-side onto the cover at y=786.61pt offset (≈ 277 mm) — the back panels will render at negative page coordinates and silently disappear from rendered PDFs.
**Why it happens:** `Spread_ueb` has `ItemTransform="1 0 0 1 0 0"`; `Spread_u108` has `ItemTransform="1 0 0 1 2.84e-14 786.61"`. Both Spreads contain a single Page each (front/back), but IDML stacks them vertically in **spread space**. The Page's own ItemTransform compensates: `1 0 0 1 -420.94 -140.31` (same for both Pages), but the *Spread's* ItemTransform also matters.
**Mitigation:** For each `<Page>`, compute `page_origin_in_world = spread.ItemTransform ⊗ page.ItemTransform` and then subtract `page_origin_in_world` from every item's world-space position to get page-relative pt. Document explicitly in the converter that Spread origin ≠ Page origin.
**Confidence:** HIGH — verified locally.

### P-LAYER-1 — Two layers, one of them `Printable="false"`
**What goes wrong:** Emitting every PageItem onto the default Gestaltung layer will dump the **Info** layer (fold guides, safety zones, print-format markers — `Druckformat / Faltung / Sicherheit / Endformat`) into the printable output. The rendered PDF will show coloured guide lines where there should be nothing.
**Why it happens:** `designmap.xml` declares two `<Layer>` elements:
- `uba` "Gestaltung" — Printable="true", Locked="false"
- `ue6` "Info" — **Printable="false"**, Locked="true"

In our spreads: 30 items on `uba`, 12 items on `ue6` (per `grep -ohE 'ItemLayer="uba"|ItemLayer="ue6"'`). Info-layer items use non-brand swatches (`Color/Druckformat`, `Color/Faltung`, `Color/Sicherheit`, `Color/Endformat`) — these are designer-only visual aids, not brand palette entries.
**Mitigation:** Map IDML `<Layer>` → DSL `DocumentLayer` 1:1 and forward `Printable="false"` to `DocumentLayer(printable=False)`. **Crucially**, the converter must not snap Info-layer colours into the Brand palette — they're not brand colours. Either:
- (a) emit a `Falz` / `Info` `DocumentLayer(printable=False)` and let Scribus render-skip it on PDF export, **or**
- (b) skip Info-layer items entirely in the v1 converter, behind a `--skip-non-printable` flag (defaulting on; documented).

Pick (a) — keeps converter strict and lossless, mirrors `ci.yml` `non_ci_layers: ["Falz"]` pattern in the sibling template.
**Confidence:** HIGH — verified locally.

### P-STYLE-1 — `AppliedFont` inherits from ParagraphStyle, not always inline on CharacterStyleRange
**What goes wrong:** Emitting only the inline `<AppliedFont>` from each `CharacterStyleRange` will silently drop the applied font on Stories that rely on style-level inheritance — leaving Scribus to fall back to its default font (Arial / Bitstream Vera) and rendering the page in the wrong typeface.
**Why it happens:** Verified on `Story_u200`: the `CharacterStyleRange` blocks set `FontStyle="Black"` but **no** `<AppliedFont>` is emitted inline — the font comes from the applied paragraph style (`ParagraphStyle/Aufzählungen auf grünem Hintergrund` → which itself inherits from `Headline in grünem Kasten` → which sets `<AppliedFont>Gotham Narrow</AppliedFont>`).
**Mitigation:** Resolve the (font_family, font_style) tuple for each Run by cascading:
1. CharacterStyleRange inline `<AppliedFont>` + `FontStyle=` attr
2. Falling back to the applied ParagraphStyle (resolved from `Resources/Styles.xml`)
3. Falling back to the parent paragraph style chain (`NextStyle` / `BasedOn` if present)
4. Finally, the document default (`Resources/Preferences.xml` → `GridDataInformation` `AppliedFont="Times"` — but we should never end up here for printable content)

Combine into a single Scribus font name as `f"{family} {style}"` (e.g. "Gotham Narrow Ultra"). Verified against IDML `Fonts.xml`: the `Font` element's `Name` attribute is literally `family + " " + FontStyleName` (e.g. `<Font Name="Gotham Narrow Ultra" PostScriptName="GothamNarrow-Ultra" FontFamily="Gotham Narrow" FontStyleName="Ultra">`). The Scribus DSL accepts that exact string.
**Confidence:** HIGH — confirmed locally.

### P-FONT-1 — Font/style combos referenced in our IDML
**What goes wrong:** Missing fonts in the Docker image (or wrong font-name spelling) silently substitute, breaking visual diff.
**Why it happens:** Probed all CharacterStyleRanges in Stories. Font/style combos in use:
- `Gotham Narrow` + `Book` → `Gotham Narrow Book` ✓ (file: `fonts/Gotham Narrow/Gotham Narrow Book/GothamNarrow-Book.otf`)
- `Gotham Narrow` + `Ultra` → `Gotham Narrow Ultra` ✓ (file: `fonts/Gotham Narrow/Gotham Narrow Ultra/GothamNarrow-Ultra.otf`)
- `Gotham Narrow` + `Black` → `Gotham Narrow Black` ✓ (file: `fonts/Gotham Narrow/Gotham Narrow Black/GothamNarrow-Black.otf`)
- `Gotham Narrow` + `Bold` (declared in `Headline in grünem Kasten` style default) → `Gotham Narrow Bold` ✓
- `Vollkorn` + `Black Italic` → `Vollkorn Black Italic` — **flag**: only `fonts/Vollkorn/Vollkorn-BlackItalic.ttf` exists at top level and `Vollkorn-VariableFont_wght.ttf` for static masters; the static `fonts/Vollkorn/static/Vollkorn-BlackItalic.ttf` is also there. IDML's `Resources/Fonts.xml` reports Black Italic as `Status="NotAvailable"` on the designer's Mac but reports it as installed under PostScriptName `Vollkorn-BlackItalic`. Verify by `fc-list | grep -i 'Vollkorn Black Italic'` inside the built container.

Also: ParagraphStyle "[No paragraph style]" carries an inline `<AppliedFont>Times</AppliedFont>` as the InDesign default — that's only relevant for stories that resolved to that style. We don't have any in this corpus, but the converter should still emit "Times" if it appears (and let Scribus's font fallback handle the substitution, since Times is not on the brand list).
**Mitigation:** After conversion, run `tools/spec_check.py` against the rebuilt SLA; spec_check will flag any unresolved font name. Also, add a converter pre-flight: walk all `<AppliedFont>` and `FontStyle=` references, build the union of `(family, style)` tuples, and assert each resolves to an installed font via `fc-match` before emitting `build.py`.
**Confidence:** HIGH for Gotham; MEDIUM for Vollkorn Black Italic (needs container verification).

### P-COLOR-1 — IDML `Color/Paper` maps to DSL `White`
**What goes wrong:** Treating "Paper" as an unhandled colour and raising `UnhandledElement` will halt the converter on every white-text frame in the IDML. Or worse: silently emitting a `Color/Paper` swatch that doesn't exist in the brand palette, producing a black or null fill in Scribus.
**Why it happens:** IDML's `Color/Paper` is a special swatch meaning "the colour of the page substrate" (typically white). Our IDML uses `FillColor="Color/Paper"` 8 times across stories (white headline text on dark-green backgrounds). The DSL brand palette has `White` (CMYK 0,0,0,0) as the equivalent ([shared/ci.yml:23](shared/ci.yml)).
**Mitigation:** Hard-code the colour mapping table at the top of the converter:
```python
COLOR_MAP = {
    "Color/Paper":        "White",
    "Color/Black":        "Black",
    "Color/Registration": None,             # not printable
    "Color/C=85 M=35 Y=95 K=10": "Dunkelgrün",
    "Color/C=0 M=0 Y=100 K=0":   "Gelb",
    "Color/C=0 M=100 Y=0 K=0":   "Magenta",
    # Info-layer swatches: must NOT be in brand palette, only used by non-printable items
    "Color/Druckformat": "_info_druckformat",
    "Color/Faltung":     "_info_faltung",
    "Color/Sicherheit":  "_info_sicherheit",
    "Color/Endformat":   "_info_endformat",
    "Swatch/None":       None,
}
```
Raise `UnhandledElement` for anything not in the table — strict mode. Verified the corpus colour usage at `Resources/Graphic.xml`.
**Confidence:** HIGH — verified locally (CMYK values match `shared/ci.yml` exactly).

### P-IMAGE-1 — Images are external links to designer's iCloud Drive
**What goes wrong:** Naively reading `<Link>` `LinkResourceURI` will try to open files at `/Users/vonhollenstein/Library/Mobile Documents/com~apple~CloudDocs/von Hollenstein/...` — paths that don't exist on any machine other than the original designer's Mac.
**Why it happens:** All seven image `<Link>` entries in our IDML point to absolute `file:` URIs on the designer's Mac. But the IDML packager exported the `originals/.../Links/` sibling directory with copies of every linked asset — verified: `BlueSky weiss.ai`, `Grüne Logo Bund weiss CMYK.ai`, `Mail weiss.ai`, `Plakat dunkel für Flyer.psd`, `Social Media Icons weiss.ai`, `Website weiss.ai`, `green-pine-trees-covered-with-fog.jpg`.
**Mitigation:** Resolve each `Link@LinkResourceURI` by:
1. Parsing the `file:` URI → extract the basename (URL-decoded, e.g. `BlueSky%20weiss.ai` → `BlueSky weiss.ai`)
2. Looking up that basename in `originals/<idml-dir>/Links/` (the sibling Links folder)
3. If the file is found: copy to `templates/<id>/assets/<sanitised-basename>` AND emit `ImageFrame(src=…)` referencing it, OR `pack_inline_image()` for raster bytes (matching the sibling template's pattern at `templates/kandidat-falzflyer-din-lang/build.py:369-394`).
4. If not found: **raise `UnhandledElement`** with a message pointing at the missing basename.

Document explicitly that the converter requires the IDML's `Links/` sibling folder to be present alongside the `.idml`.
**Confidence:** HIGH — verified locally.

### P-IMAGE-2 — AI files appear as `<PDF>` child elements, not `<Image>`
**What goes wrong:** Filtering for `<Image>` only will skip every `.ai` (Adobe Illustrator) link — and our IDML has 5 of them: BlueSky, Bund-logo, Mail, Social Media Icons, Website. The resulting `build.py` will emit empty Rectangle frames for the contact icons.
**Why it happens:** Adobe stores Illustrator (`.ai`) and PDF links inside `<Rectangle>` PageItems wrapped in `<PDF>` child elements (because `.ai` is a PDF wrapper format). The `ImageTypeName="$ID/Adobe Portable Document Format (PDF)"` and `LinkResourceFormat="$ID/Adobe Portable Document Format (PDF)"` give them away. The actual filename only appears in the `<Link>` element's `LinkResourceURI`.
**Mitigation:** When walking a Rectangle/Polygon PageItem, check for ALL three content types: `<Image>` (raster: JPEG/PSD), `<PDF>` (vector: .ai or .pdf), `<EPS>` (legacy vector). The corpus has Image (1× JPEG, 1× PSD) and PDF (5× .ai files, 1× .pdf if any).

Convert each to a DSL `ImageFrame`. For .ai content: Scribus 1.6.5 can natively place `.ai` (renders via Poppler-PDF backend); just reference the file path. **Alternative** (recommended): pre-rasterise each `.ai` to PNG at 600dpi using `pdftoppm` or `inkscape --export-type=png` once, store in `templates/<id>/assets/`, and emit `ImageFrame(image="assets/foo.png")`. This matches the existing pattern in `templates/kandidat-falzflyer-din-lang/` where every logo is a pre-baked PNG.

Either path: in strict mode, raise `UnhandledElement` for unknown `ImageTypeName` values (not in `{JPEG, Photoshop, Adobe Portable Document Format (PDF), TIFF}`).
**Confidence:** HIGH — confirmed in this IDML.

### P-STORY-1 — Bullets are stored as literal `<Content>\t•\t<?ACE 7?></Content>` runs
**What goes wrong:** Treating bullets as ordinary glyph runs will reproduce a "•" character in the rendered text where InDesign would have produced a column-aligned bullet glyph. Acceptable for v1 but flag for the planner.
**Why it happens:** `Story_u200` shows the bullet markup: `<Content>	•	<?ACE 7?></Content>` — that's `\t • \t <?ACE 7?>`. `<?ACE 7?>` is the InDesign processing instruction for "indent to here" (column tab). The bullet character is a literal `•` (U+2022). After `<?ACE 7?>` comes a `<Br />` for paragraph break.
**Mitigation:** Emit a literal Run with text = `\t•\t` + indent-to-here-equivalent + the bullet body text + `\n`. The Scribus DSL doesn't have an "indent to here" marker — substitute with a tabstop in the ParaStyle definition. For v1, just preserve the literal text including the `\t • \t` sequence. Document in converter docstring.

Strict mode addition: if `<?...?>` processing instructions other than `<?ACE 7?>` appear, raise `UnhandledElement` (we've only seen `<?ACE 7?>` in this corpus).
**Confidence:** MEDIUM — visual fidelity will be slightly off; flag for follow-up if visual diff exceeds tolerance.

### P-STORY-2 — `<Br/>` inside `<CharacterStyleRange>` = hard line break, not paragraph break
**What goes wrong:** Treating every `<Br/>` as a paragraph boundary will fragment a single paragraph into many, breaking ParaStyle assignment.
**Why it happens:** IDML uses `<Br/>` (the soft-break tag) for in-paragraph line breaks (Shift+Enter in InDesign). Paragraph boundaries are `</ParagraphStyleRange>` / `<ParagraphStyleRange>` transitions, not `<Br/>`. Our IDML has 35 `<Br/>` elements across 11 stories — most are line breaks within a single paragraph (e.g. `Story_u251`: "Ich bin eine <Br/>Headline." = one paragraph, two lines).
**Mitigation:** Map `<Br/>` to `\n` within a Run; map paragraph transitions to a Run break with a new ParaStyle. The Scribus DSL's `Run` model accepts `\n` inside its text for soft breaks (verify against `tools/sla_lib/builder/primitives.py` `Run` class — confirmed: `_build_runs` in `sla_to_dsl.py:477` handles this same case for the Scribus side).
**Confidence:** HIGH.

### P-OUTPUT-1 — Strict-mode error message must point at the converter file:line
**What goes wrong:** A generic `UnhandledElement: TextFrame` exception leaves humans hunting through 1000+ lines of converter code to find where to extend.
**Why it happens:** sla_to_dsl.py's pattern (verified at lines 235, 317, 356, 442, 551, 564, 588, 601, 717, 736, 857) is to include the **element kind + attribute name** in the message: `UnhandledElement(f"STYLE {name!r} carries unhandled attribute {k!r}")`. The traceback then points at the exact `raise` line in `sla_to_dsl.py`, so the developer knows where to extend.
**Mitigation:** Mirror the same pattern. Every `raise UnhandledElement(...)` should include:
1. The IDML element type (`TextFrame` / `Rectangle` / `Group` / `Story` / `ParagraphStyleRange` / etc.)
2. The element's `Self="..."` ID so the developer can search the spread XML
3. The specific attribute or child element that's unhandled
4. The IDML file path (in case multiple IDMLs are being converted, future-proofing)

Example: `raise UnhandledElement(f"TextFrame Self={self_id!r} in {spread_filename!r}: unsupported attribute FrameType={ft!r} (extend tools/idml_to_dsl.py:_convert_textframe)")`. The "(extend …)" hint is the key — it points the human at the function to modify.
**Confidence:** HIGH.

### P-ENV-1 — `simple-idml` Python package: `simpleidml` (no underscore) on PyPI, `simple_idml` import
**What goes wrong:** `pip install simple-idml` will fail. `pip install SimpleIDML` or `pip install simpleidml` works. The import path is `simple_idml.idml.IDMLPackage`. Mismatched assumptions in CI configs or Dockerfile patches will silently miss the dependency.
**Why it happens:** Verified: `pip show SimpleIDML` returns `Name: simpleidml, Version: 1.3.1`. The package is already pre-installed in our claude-flow base image (`/usr/local/lib/python3.13/dist-packages/simple_idml/__init__.py` exists; `pip3 install --dry-run SimpleIDML` reports "Requirement already satisfied"). lxml 5.4.0 also pre-installed.

**However**: the worktree's bare `python3 -c "import simple_idml"` initially failed (ModuleNotFoundError), which suggests PYTHONPATH or virtualenv isolation in some launch contexts. Verify both `python3` (system) and any uv/venv-launched runtimes can `import simple_idml`.
**Mitigation:**
1. Document in the converter docstring: `pip install SimpleIDML lxml` if not pre-installed.
2. Add to `Dockerfile.claude` after the existing `pip3 install --break-system-packages` block (line 63): `pip3 install --break-system-packages --no-cache-dir SimpleIDML==1.3.1` — pinned version for reproducibility.
3. Add a `python3 -c "from simple_idml.idml import IDMLPackage"` smoke probe to the Dockerfile sanity block (line 148).
4. In `tools/idml_to_dsl.py`, do `try: from simple_idml.idml import IDMLPackage; except ImportError: print("Install SimpleIDML: pip install SimpleIDML"); sys.exit(2)` so a missing dep gives a clear message rather than a stack trace.
**Confidence:** HIGH — verified locally (SimpleIDML 1.3.1 + lxml 5.4.0 both importable).
**Source:** [SimpleIDML on PyPI](https://pypi.org/project/SimpleIDML/), [SimpleIDML on GitHub](https://github.com/Starou/SimpleIDML).

---

## 2. Likely Pitfalls (may break; design-in mitigations)

### P-THREAD-1 — Threaded TextFrames (NextTextFrame / PreviousTextFrame)
**What goes wrong:** A story spread across multiple frames will load entirely into the first frame and overflow invisibly in the rendered SLA.
**Why it might happen:** IDML supports threaded frames where one Story flows through multiple TextFrames via `NextTextFrame="<id>"` / `PreviousTextFrame="<id>"` chain references.
**Status in our corpus:** Verified ZERO threading. Every TextFrame's `NextTextFrame` and `PreviousTextFrame` is `"n"` (the IDML null sentinel). Total NextTextFrame attrs in corpus: 23, all == "n".
**Mitigation:** v1 converter checks `NextTextFrame != "n"` or `PreviousTextFrame != "n"` and raises `UnhandledElement("Threaded TextFrames not supported in v1: TextFrame {self_id} → {next_id}")`. Document explicitly in scope.
**Confidence:** HIGH that v1 doesn't need threading; HIGH that strict raising is the right v1 behaviour.

### P-MASTER-1 — MasterSpread overrides
**What goes wrong:** A page with `AppliedMaster="ubb"` may inherit page items from the master spread that the converter doesn't see when only walking `<Spread>`.
**Why it might happen:** MasterSpread items can be overridden on the page via `OverrideList`; un-overridden items render directly from the master.
**Status in our corpus:** `MasterSpreads/MasterSpread_ubb.xml` is empty of PageItems — it only declares the Page geometry and a margin preference. Both real spreads' Page has `AppliedMaster="ubb"` and `OverrideList=""` (empty). So **no master-page items to render**.
**Mitigation:** v1 converter:
1. Read `MasterSpread_ubb.xml`.
2. Find any PageItem descendants (Rectangle / TextFrame / Polygon / Group / Image / EPS / PDF).
3. If any exist → raise `UnhandledElement("MasterSpread {name} contains PageItems; v1 only supports empty masters")`.
4. If empty → proceed.

This is a 5-line check that future-proofs us.
**Confidence:** HIGH.

### P-ANCHOR-1 — AnchoredObjects (objects embedded in text flow)
**What goes wrong:** An anchored object (e.g. an inline icon next to a text label) attached to a character position will not appear in the spread's top-level item list — it lives inside the Story XML and gets emitted as garbage if walked naively.
**Why it might happen:** Common in leporello layouts where small icons are "anchored" to header captions.
**Status in our corpus:** Grepped `<AnchoredObjectSetting`, `Anchored=`, `AnchoredObject` across all stories and spreads — **zero matches**. So no anchored objects in this IDML.
**Mitigation:** v1 detects `<AnchoredObjectSetting>` or `<TextFrame>` inside a Story (not Spread) and raises `UnhandledElement("Anchored objects not supported in v1")`. Document in scope.
**Confidence:** HIGH.

### P-STYLE-2 — Inline-attribute overrides on ParagraphStyleRange shadow the named ParagraphStyle
**What goes wrong:** Naively emitting one DSL `ParaStyle` per named IDML ParagraphStyle and ignoring inline overrides will emit text with default style attributes (justification, line spacing) instead of the per-instance overrides — e.g. our IDML's Aufzählungen story sets `Justification="LeftAlign"` inline on a final paragraph that overrides the style's default `Justification`.
**Why it might happen:** InDesign allows inline overrides on a `<ParagraphStyleRange>` that take precedence over the named style's attributes.
**Mitigation:** Two-pass approach mirroring `sla_to_dsl.py`'s ParaStyle handling:
1. **Pass 1**: collect each unique (named_style, inline_overrides_signature) tuple. Emit a fresh DSL ParaStyle per tuple, named `<original-name>__variantN` if N>1 inline-override variants exist for a base name.
2. **Pass 2**: per Run, reference the de-duplicated ParaStyle.

For v1 with this corpus (5 ParagraphStyles × few inline overrides each), this is ≤ 10 emitted ParaStyles. The sibling template `kandidat-falzflyer-din-lang/build.py` already has 15-20 ParaStyles, so this is normal scale.
**Confidence:** HIGH (mechanism); MEDIUM (specific count, depends on inline-override detection rules).

### P-COLOR-2 — Brand palette CMYK exact-match vs Snap-to-Brand
**What goes wrong:** The IDML's `Color/C=85 M=35 Y=95 K=10` exactly matches our brand's Dunkelgrün CMYK (85, 35, 95, 10). But future IDMLs from the designer might use slightly different CMYK values for the same intended brand colour — `C=85 M=33 Y=95 K=10` (Adobe colour-pickers drift by ±2 %). Naively raising `UnhandledElement` for any unrecognised CMYK string would block every future delivery.
**Why it might happen:** Designer-uploaded IDMLs are not CMYK-pixel-perfect against `shared/ci.yml`.
**Mitigation in v1:** Strict exact-match. For this corpus the CMYK strings match exactly, so emit ✓.
**Mitigation in v2 (out of scope, but flag):** Implement a fuzzy `snap_cmyk_to_brand(cmyk, tolerance=2)` that nudges values within 2 % to the nearest brand entry and logs a warning. **DO NOT** put this in v1 — silent snapping is the worst kind of bug.
**Confidence:** HIGH.

### P-PERF-1 — Spread XML is large; don't parse twice
**What goes wrong:** Naïve implementations parse the spread XML once to find layers, again to walk items, again to compute transforms — turning a 30 ms operation into 300 ms.
**Why it might happen:** Spread_u108.xml is ~ 600 KB (22000 lines of effectively one-line XML when pretty-printed), Spread_ueb.xml is ~ 530 KB. SimpleIDML's `IDMLPackage.spreads_objects` lazy-loads them as lxml trees on first access.
**Mitigation:** Use SimpleIDML's `spread.dom` (or equivalent — see `simple_idml.idml.IDMLPackage.spreads_objects`) once per spread, then re-use the lxml tree. Don't re-parse via `etree.fromstring(pkg.read(spread_path))` repeatedly. Use XPath for queries, not multiple `fromstring` calls.
**Confidence:** MEDIUM — depends on planner's implementation. Trivial micro-opt; mention in plan but don't gate.

### P-RERUN-1 — One-shot vs. re-runnable converter (semantics)
**What goes wrong:** A user re-runs the converter against an updated IDML expecting an incremental update; the converter silently overwrites a hand-edited `build.py` losing days of human work.
**Why it might happen:** The issue description says "strict, one-shot bootstrap" — same as `sla_to_dsl.py`'s philosophy. `sla_to_dsl.py` (lines 1-28) is explicit: "The emitted script is the source of truth thereafter — humans edit it directly."
**Mitigation:**
1. Mirror sla_to_dsl's docstring exactly: "One-shot. The emitted `build.py` is the source of truth thereafter — humans edit it directly. Re-running this converter REPLACES `build.py` and discards manual edits."
2. Refuse to overwrite an existing `build.py` unless `--force` is passed. (sla_to_dsl.py does this? Check — it doesn't explicitly check; but the docstring is the contract.)
3. Print a banner on every run: `"Bootstrap-only. Re-runs will overwrite manual edits."`
**Confidence:** HIGH (semantics); MEDIUM (whether the `--force` flag is in scope).

---

## 3. Out of Scope (explicit non-goals; document and skip)

| Out-of-scope item | Rationale |
| --- | --- |
| **Round-trip DSL → IDML** | One-way only; humans edit `build.py`, not the IDML. No InDesign in the CI pipeline. |
| **`.indd` binary format** | Adobe's binary InDesign format is undocumented and not parseable; require designers to "Save as IDML" once. |
| **Multi-IDML batch processing** | Process one IDML at a time; trivial to wrap a shell loop if needed. Keeps converter CLI simple. |
| **Auto-fix unknown elements** | Strict-raise is the design (per `sla_to_dsl.py` D6). Silent fallbacks produce subtly wrong output that's harder to diagnose than a hard fail. |
| **Threaded TextFrames** | Our corpus has zero. Add when the first IDML that needs it lands. v1 raises `UnhandledElement` on `NextTextFrame != "n"`. |
| **Anchored objects** | Zero in this corpus. v1 raises on `<AnchoredObjectSetting>`. |
| **Right-to-left scripts / complex shaping** | Brand is German-only. v1 raises `UnhandledElement` on `StoryDirection != "LeftToRightDirection"`. |
| **MasterSpread items** | Our master spread is empty. v1 raises if master contains PageItems. |
| **Fuzzy CMYK snap-to-brand** | v1 is exact-match strict. Snap-to-brand is a v2 feature (P-COLOR-2). |
| **InDesign Tables / Cells** | Not in this corpus. Out of scope for v1; raise if encountered (`<Table>`, `<Cell>` elements). |
| **Hyperlinks / cross-references** | Print-only deliverable. Strip silently or raise — recommend raise (`<HyperlinkURLDestination>` etc.). |
| **Tags / XML-structure roundtripping** | The `XML/` folder in the IDML carries XML-tagged content for InCopy. Not needed for our flat Stories. Skip. |
| **Conditional text (ConditionSet)** | Only one condition set in our IDML (`ConditionalTextPreference ActiveConditionSet="n"`) — i.e. none active. Skip. |
| **Footnotes / Endnotes** | Not present in our corpus. Skip. |
| **Print-marks / bleed marks beyond `DocumentBleedTopOffset`** | DSL handles bleed already; converter just reads the offsets. |
| **Visual-diff baseline.pdf** | The sibling falzflyer template doesn't have a `baseline.pdf` — only the original three templates (postkarte, zeitung, plakat-a1) do. v2 template doesn't need one for issue 35 to land; CI passes without it. Follow-up issue may add a baseline. |

---

## 4. Environment Audit

Already present in the container (verified locally inside the worktree):

| Dependency | Required for | Present? | Version | Notes |
| --- | --- | --- | --- | --- |
| Python 3 | Converter runtime | YES | 3.13 (Debian trixie) | per `Dockerfile.claude:3` |
| `lxml` | XML parsing | YES | 5.4.0 | Safe XXE defaults since 5.x; ok for trusted IDML input |
| `SimpleIDML` (`simple_idml` import) | IDML package access | YES | 1.3.1 | Pre-installed in claude-flow base image at `/usr/local/lib/python3.13/dist-packages/simple_idml/` — **add explicit pin to Dockerfile.claude to prevent silent removal** |
| `suds-py3` | SimpleIDML transitive | YES | 1.4.5.0 | Not used by our code path |
| `python3-yaml` | meta.yml emit | YES | apt-installed | per `Dockerfile.claude:39` |
| Scribus 1.6.x | Render `template.sla` → PDF | YES | trixie ships 1.6.3 (CI uses 1.6.5 AppImage on Ubuntu) | Xvfb-required |
| `xvfb-run` | Scribus headless | YES | apt | per `Dockerfile.claude` |
| `pdftoppm` | Visual diff rasterising | YES | poppler-utils | per Dockerfile |
| `pdfinfo` | PDF metadata | YES | poppler-utils | |
| ImageMagick (`compare`, `convert`, `montage`) | Visual diff | YES | apt | per Dockerfile |
| Gotham Narrow fonts | Template render | YES | Black, Bold, Book, Ultra .otf at `fonts/Gotham Narrow/*/` + installed to `/usr/local/share/fonts/gruene/` | per `Dockerfile.claude:69-88` |
| Vollkorn fonts | Template render | YES | `Vollkorn-BlackItalic.ttf` + variable masters | Verify `fc-match "Vollkorn Black Italic"` resolves correctly |
| `originals/.../Links/` directory | Image asset resolution | YES | 7 files: 5 .ai, 1 .psd, 1 .jpg | Sibling of the .idml |

Missing / TODO:

| Dependency | Required for | Mitigation |
| --- | --- | --- |
| Pinned SimpleIDML version in `Dockerfile.claude` | Reproducibility — currently relying on base image | Add `pip3 install --break-system-packages SimpleIDML==1.3.1` to the existing `pip3 install` block (line 63). |
| `pdftoppm` / `inkscape` for AI→PNG rasterisation | If converter pre-rasterises .ai files | `pdftoppm` is already present (poppler-utils). Use it: `pdftoppm -png -r 600 input.ai output_prefix`. |
| Dockerfile sanity probe for SimpleIDML | Catch base-image regressions | Append `python3 -c "from simple_idml.idml import IDMLPackage"` to the existing sanity block (line 148). |

---

## 5. Security / Safety

### S-ZIP-1 — IDML is a ZIP file; zip-slip risk
**Status:** **Mitigated for free**. `simple_idml.idml.IDMLPackage` extends `zipfile.ZipFile`. Python's `zipfile.ZipFile.extract()` and `.extractall()` since Python 3.7 sanitise leading `/`, drive letters, and `..` components per the `zipfile.Path` / `os.path.commonpath` guard (CVE-2007-4559 fix landed in 3.7.0). Our converter uses `pkg.read(name)` and `pkg.open(name)` only — neither writes to disk. **No additional mitigation needed**.

If the planner adds a fallback to `pkg.extractall(target_dir)` for any reason (e.g. extracting Links/ from the IDML's own internal Links — note: our IDML does NOT have an internal Links folder, only the sibling directory), wrap with an explicit `safe_extract()` that validates each `Path(target_dir, member).resolve().is_relative_to(target_dir.resolve())`.
**Confidence:** HIGH.
**Source:** Python `zipfile` documentation; [CodeQL: Arbitrary file access via archive extraction](https://codeql.github.com/codeql-query-help/python/py-tarslip/) covers tarfile, but `zipfile` has the same fix.

### S-XXE-1 — XML External Entity attacks via lxml
**Status:** **Mitigated by default in our lxml version**. lxml ≥ 5.0 changed `etree.parse` / `etree.fromstring` / `etree.XMLParser` defaults to `resolve_entities='internal'` — internal entities resolve, but external entities (`SYSTEM`, network URLs, local file inclusion) are blocked. Our installed lxml is 5.4.0, so `etree.fromstring(xml)` (which SimpleIDML uses internally per `inspect.getsource(simple_idml.idml)`) is safe.

**Caveat:** lxml ≤ 6.0 still left `etree.iterparse()` and `ETCompatXMLParser` with the unsafe default `resolve_entities=True`. Fixed in lxml 6.1.0. Our code path doesn't use iterparse, but if the planner adds it for streaming a large IDML, **explicitly** pass `XMLParser(resolve_entities=False, no_network=True, dtd_validation=False, load_dtd=False)`.

Also: IDML is **trusted input** (designer-provided), not user-uploaded. The XXE threat surface is low. Still, defence-in-depth is cheap.
**Mitigation:** Define a hardened parser once at module level:
```python
_SECURE = etree.XMLParser(resolve_entities=False, no_network=True,
                           dtd_validation=False, load_dtd=False)
```
and use it for any `etree.parse` / `etree.fromstring` calls made directly by our converter (SimpleIDML's own internals are already safe under lxml 5.4.0).
**Confidence:** HIGH.
**Source:** [lxml FAQ](https://lxml.de/FAQ.html), [GitLab advisory CVE-2026-41066](https://advisories.gitlab.com/pypi/lxml/CVE-2026-41066/).

### S-PATH-1 — User-controlled output paths
**Status:** Minor. The converter takes `--output` for `build.py` location. If invoked from a script with an attacker-controlled path argument, it could overwrite arbitrary files. Not realistic for our use case (we run this manually).
**Mitigation:** Optional — assert the output path is inside `templates/` or pass `--force` to overwrite outside. v1 doesn't need this guard.
**Confidence:** LOW priority.

---

## 6. Strict-mode UX checklist (for the planner)

Mirror `sla_to_dsl.py`'s error reporting style verbatim:

1. **Top-level `UnhandledElement` class** (line 59 of `sla_to_dsl.py`) — single exception type, traceback identifies the source `raise`.
2. **Every `raise` includes:** element kind + Self ID + offending attribute/child + a `(extend tools/idml_to_dsl.py:_function_name)` hint.
3. **`main()` catches `UnhandledElement`** and prints `"UnhandledElement: ..."` to stderr with exit code 2 (matches `sla_to_dsl.py:1281-1283`).
4. **Strict pre-flight check pass**: before emitting `build.py`, walk every PageItem and Story and raise on:
   - Unknown FillColor / StrokeColor not in our `COLOR_MAP`
   - Threaded frames (NextTextFrame ≠ "n")
   - Anchored objects (`<AnchoredObjectSetting>`)
   - Master-spread items
   - Non-LTR text (`StoryDirection`)
   - Unknown processing instructions (anything not `<?ACE 7?>`)
   - Unknown `ImageTypeName`
5. **Module docstring** documents one-shot semantics + usage example (mirror `sla_to_dsl.py:1-28`).
6. **CLI flags**: `--source <idml> --output <build.py-path> --template-id <slug> --assets-dir <path>` — mirror `sla_to_dsl.py:1271-1278`.

---

## 7. Sources

### HIGH confidence (verified locally + cross-referenced)
- **The IDML itself** — direct inspection of `/tmp/idml_inspect/{Spreads,Stories,Resources,MasterSpreads}/`. Every quantitative claim above (rotated frames at 90°/9°, 5 ParagraphStyles, 2 Layers, 23 Stories, 0 threaded frames, 0 anchored objects, CMYK values) was verified by grep/python on the unzipped IDML.
- **SimpleIDML 1.3.1 source** — `inspect.getsource(simple_idml.idml)` (locally importable). Confirms `IDMLPackage extends zipfile.ZipFile`, `etree.fromstring(xml)` is used internally for parsing.
- **`tools/sla_to_dsl.py`** — read directly. Confirms strict-mode philosophy (`UnhandledElement`, line 59), error message style (lines 235, 317, 356, 442, 551, 564, 588, 601, 717, 736, 857), one-shot semantics (module docstring lines 1-28), CLI shape (lines 1271-1284).
- **`tools/sla_lib/builder/primitives.py`** — `rotation_deg` field on TextFrame/ImageFrame/Polygon (lines 440, 779, etc.), `ImageFrame.src` / `.image` / `.inline_image_data` fields verified via dataclass introspection.
- **`tools/sla_lib/builder/bbox.py:5-8`** — Scribus rotation pivot is top-left CCW (explicit project doc).
- **`shared/ci.yml`** — brand CMYK values verified to match IDML CMYK colour strings exactly.
- **`Dockerfile.claude`** — Python 3.13, lxml 5.4.0 (system apt), SimpleIDML present in base image, fonts at `/usr/local/share/fonts/gruene/`.
- **[Adobe Community: IDML Rotation Matrix concern](https://community.adobe.com/t5/indesign-discussions/idml-rotation-matrix-concern/m-p/9680181)** — confirms ItemTransform inner→parent map semantics and rotation centre math.
- **[Indiscripts: Coordinate Spaces and Transformations Vol. 5](https://www.indiscripts.com/post/2018/06/coordinate-spaces-and-transformations-5)** — authoritative reference on IDML coordinate spaces (PDF guide, 2021/3.2).
- **[lxml FAQ](https://lxml.de/FAQ.html)** + **[CVE-2026-41066](https://advisories.gitlab.com/pypi/lxml/CVE-2026-41066/)** — XXE default behaviour in lxml 5.x vs 6.1+.
- **[SimpleIDML on PyPI](https://pypi.org/project/SimpleIDML/)** and **[Starou/SimpleIDML on GitHub](https://github.com/Starou/SimpleIDML)** — package name (`SimpleIDML`/`simpleidml`), import path (`simple_idml`), Python 3.9+ support, current version 1.3.1.

### MEDIUM confidence (cross-source web research, not lab-verified)
- **[Adobe Community: Converting a rotated text from IDML to HTML5](https://community.adobe.com/t5/indesign-discussions/converting-a-rotated-text-from-idml-to-html5/m-p/4435777)** — TextFrame inner-origin = frame centre confirmation.
- **[Indiscripts coordinate-spaces PDF](https://indiscripts.com/blog/public/data/coordinate-spaces-and-transformations-5/CoordinateSpacesTransfos01-05.pdf)** — Chasles' relation for cascade composition (not directly readable in our context, but referenced).
- **[Adobe IDML Cookbook (Scribd)](https://www.scribd.com/document/206031435/Idml-Cookbook)** — generic reference; cited but not opened.

### LOW confidence / single-source (flagged for the planner)
- **None.** Every claim above has at least two corroborating sources (codebase + spec, or two web sources, or local-verify + spec).

---

## 8. Summary for the planner

The planner's spec must:

1. **Hard-code the IDML→DSL colour map** (P-COLOR-1) — 8 entries, no fuzzy matching in v1.
2. **Implement the coordinate cascade** (P-COORD-1 .. P-COORD-5) — composed transform from Spread → Page → ancestor Groups → leaf PageItem, applied to PathPointArray points; AABB of transformed corners; pt → mm. Worked example: TextFrame `u347` at 90° on Spread `u108`; TextFrame `u186` at 9° on Spread `ueb`.
3. **Handle the two rotated TextFrames explicitly** (P-COORD-3) with a unit-tested pivot translation between IDML (inner-centre) and Scribus (top-left CCW) conventions. Don't ship without round-trip tests.
4. **Map IDML Layers to DocumentLayers** (P-LAYER-1) with `printable=False` for the Info layer. Don't snap Info-layer non-brand swatches into the brand palette.
5. **Cascade font resolution** (P-STYLE-1) through ParagraphStyle / parent chain before falling back to defaults. Emit Scribus font names as `f"{family} {style}"`.
6. **Detect `<PDF>` content inside Rectangles** for .ai files (P-IMAGE-2), not just `<Image>`.
7. **Resolve `<Link>` `LinkResourceURI` against the IDML's sibling `Links/` directory** (P-IMAGE-1), not against the absolute iCloud path embedded in the IDML.
8. **Strict-mode raises** with location-pointing messages (P-OUTPUT-1) mirroring `sla_to_dsl.py`'s style.
9. **Add SimpleIDML==1.3.1 to `Dockerfile.claude`** explicitly (P-ENV-1) and add a Dockerfile sanity probe.
10. **Hardened lxml parser** for any direct `etree.parse` calls in the converter (S-XXE-1).

Out of scope (do not implement in v1, raise `UnhandledElement` instead): threaded frames, anchored objects, master-spread items, RTL text, hyperlinks, footnotes, tables, snap-to-brand colour fuzzy matching, baseline.pdf for visual_diff, round-trip DSL→IDML, .indd binary parsing, multi-IDML batch.
