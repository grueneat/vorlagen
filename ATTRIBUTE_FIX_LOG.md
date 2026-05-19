# IDML Attribute Fix Log

Disposition of every Tier-A attribute from `ATTRIBUTE_COVERAGE.md` (109 total)
after triage against actual rendering impact on the 8 batch templates.

The audit's "Tier A" criterion is "present with a varying value across the
batch". That is necessary but **not sufficient** for a rendering impact: a
`ParagraphBorder*LineWeight` only matters if a paragraph actually enables a
border; a `FrameFittingOption/*Crop` is redundant when the converter already
derives the crop from the `<Image>` geometry; an `Ink` screening angle is a
print-production attribute Scribus does not model. Each row below records the
disposition and the one-line reason.

## Summary

| Disposition | Count |
|---|---:|
| `fixed` | 5 |
| `not-impactful-for-these-templates` | 91 |
| `unsupported-in-SLA` | 13 |
| **Total** | **109** |

A 6th attribute, `ParagraphStyle/SpaceBefore` (Tier **B** — constant 0 across
the batch), is also now consumed by the same parse/resolve/emit path as
`SpaceAfter`. It emits nothing on this batch (every value is 0) but is correct
for any future template that sets it.

## `fixed` (5)

| Element / Attribute | Rendering change produced |
|---|---|
| `ParagraphStyle/SpaceAfter` | Body style `Fließtext auf weißem Hintergrund` carries `SpaceAfter=5.669pt`; emitted as SLA STYLE `NACH`, inserting the paragraph gap InDesign shows in `baseline.pdf` (previously missing — paragraphs ran together). |
| `BlendingSetting/Opacity` | Object opacity (Impressum text frames at 70%, one image rectangle at 90%/81%) → SLA `TransValue`/`TransValueS` (`1 - opacity`); the Impressum text now renders semi-transparent instead of fully opaque. |
| `TextFramePreference/VerticalJustification` | `CenterAlign` (every Impressum frame) → SLA PAGEOBJECT `ALIGN=1`, vertically centring the text block in the frame instead of pinning it to the top. |
| `TextFramePreference/TextColumnCount` | `TextColumnCount=2` on the Querformat body / bullet-list frames → SLA `COLUMNS=2`; body text now flows in two columns matching `baseline.pdf` (was a single wide column). |
| `TextFramePreference/TextColumnGutter` | The inter-column gutter for the multi-column frames above → SLA `COLGAP` (points → mm). Only emitted when `TextColumnCount > 1`. |

## `unsupported-in-SLA` (13)

Scribus/SLA has no representation for these; forcing them would be wrong.
Logged rather than fixed.

| Element / Attribute(s) | Reason |
|---|---|
| `Ink/Angle`, `Ink/Frequency`, `Ink/NeutralDensity`, `Ink/TrapOrder` (4) | Print-production halftone screening + ink-trapping parameters; not a page-render concern and Scribus does not model per-ink screening/trapping. |
| `FlexLayoutAttributeOption/FlexGapColumn`, `FlexGapRow`, `FlexPaddingTop`, `FlexPaddingBottom`, `FlexPaddingLeft`, `FlexPaddingRight` (6) | InDesign flex-layout (auto-arranged frames). Scribus has no flex layout; frame positions are already resolved to absolute geometry by the time the converter reads them, so the flex parameters describe nothing renderable. |
| `Gradient/Type`, `GradientStop/Location`, `GradientStop/Midpoint` (3) | Gradient definitions exist in Resources but no page item uses a `Gradient/*` fill (the radial-gradient backgrounds are placed as pre-rendered PNGs). No SLA gradient to emit. (`GradientStop/StopColor` is also unused — see not-impactful.) |

## `not-impactful-for-these-templates` (91)

Grouped by reason. Bucket headings give the row count in that bucket; the
buckets sum to 91.

### Disabled-feature serialised defaults (33)

InDesign serialises every paragraph-border / shading / rule / drop-cap /
text-stroke attribute on every style even when the *enabling* flag
(`ParagraphBorderOn`, `ParagraphShadingOn`, `RuleAbove`, `RuleBelow`,
`DropCapLines`, a non-`Swatch/None` `StrokeColor`) is off. Verified across all
9 IDMLs: **no used paragraph style or PSR ever enables any of these features**,
so the weights/radii/colours paint nothing.

- `ParagraphStyle`: `ParagraphBorderBottomLeftCornerRadius`,
  `ParagraphBorderBottomLineWeight`, `ParagraphBorderBottomRightCornerRadius`,
  `ParagraphBorderLeftLineWeight`, `ParagraphBorderRightLineWeight`,
  `ParagraphBorderTopLeftCornerRadius`, `ParagraphBorderTopLineWeight`,
  `ParagraphBorderTopRightCornerRadius`,
  `ParagraphShadingBottomLeftCornerRadius`,
  `ParagraphShadingBottomRightCornerRadius`,
  `ParagraphShadingTopLeftCornerRadius`, `ParagraphShadingTopRightCornerRadius`,
  `RuleAboveLineWeight`, `RuleBelowLineWeight`, `StrokeWeight`,
  `MiterLimit`, `DropcapDetail` (17) — borders/shading/rules/drop-cap/text-stroke
  all disabled; `StrokeWeight`/`MiterLimit` matter only with a visible text
  stroke and `StrokeColor` resolves to `Swatch/None` on every used style.
- `ParagraphStyleRange`: `ParagraphBorderBottomLeftCornerRadius`,
  `ParagraphBorderBottomLineWeight`, `ParagraphBorderBottomRightCornerRadius`,
  `ParagraphBorderLeftLineWeight`, `ParagraphBorderRightLineWeight`,
  `ParagraphBorderTopLeftCornerRadius`, `ParagraphBorderTopLineWeight`,
  `ParagraphBorderTopRightCornerRadius`,
  `ParagraphShadingBottomLeftCornerRadius`,
  `ParagraphShadingBottomRightCornerRadius`,
  `ParagraphShadingTopLeftCornerRadius`, `ParagraphShadingTopRightCornerRadius`,
  `RuleAboveLineWeight`, `RuleBelowLineWeight` (14) — same disabled features,
  PSR-level.
- `CharacterStyleRange`: `StrokeWeight`, `MiterLimit`, `KentenFontSize`,
  `RubyFontSize` (4) — no CSR ever sets a non-`Swatch/None` `StrokeColor`, so
  the text outline is never painted; Kenten/Ruby are CJK emphasis/annotation
  features with no occurrences in this Latin-text corpus.
- `Polygon/MiterLimit` (1) — only affects a stroked corner; the simple polygons
  with a varying miter value carry no visible stroke.

Bucket total: 17 + 14 + 4 + 1 = **36**.

### Inert or authoring-only typographic attributes (8)

- `ParagraphStyle/Hyphenation`, `ParagraphStyle/HyphenationZone`,
  `ParagraphStyleRange/HyphenationZone` (3) — every *used* body style resolves
  to `Hyphenation=false`; the render is hyphenation-off by default (no
  `AutomaticHyphenation`), so it already matches. Emitting nothing is correct.
- `ParagraphStyle/SplitColumnInsideGutter`,
  `ParagraphStyleRange/SplitColumnInsideGutter` (2) — gutter for the
  split-column paragraph feature; no paragraph uses split columns.
- `ParagraphStyle/DiacriticPosition`,
  `ParagraphStyle/TreatIdeographicSpaceAsSpace` (2) — OpenType-diacritic and
  CJK-spacing settings; the corpus is Latin German text with no combining
  diacritics or ideographic spaces.
- `GridDataInformation/FontStyle` (1) — frame-grid metadata (`Regular`/`Roman`);
  no template uses a frame grid for layout (`StoryPreference/FrameType` is
  `TextFrameType`).

### Crop / image metadata already covered by geometry (8)

- `FrameFittingOption/BottomCrop`, `TopCrop`, `LeftCrop`, `RightCrop`,
  `FittingAlignment`, `FittingOnEmptyFrame` (6) — the converter already
  reproduces the InDesign image crop from the `<Image>` `ItemTransform` +
  the frame `PathPointArray` (`_aspect_crop_image`). `FrameFittingOption`
  records the same auto-fit result; re-deriving from it would be redundant and
  could conflict. `FittingOnEmptyFrame` is an authoring-time rule (what happens
  when a *new* image is dropped in) with no static-render effect.
- `Image/EffectivePpi` (1) — the placed image's effective resolution; a
  reported value, not a layout input. Image size/placement comes from the
  frame geometry.
- `Image/ImageTypeName` (1) — the source format tag (`$ID/JPEG` /
  `$ID/Photoshop`); the converter resolves the linked asset by its URI, not by
  this tag.

### Empty master spreads — master application produces nothing (7)

Every `MasterSpreads/*.xml` is verified empty (the converter already asserts
this). Applying a master that carries no page items emits nothing.

- `Page/AppliedMaster`, `Page/AppliedAlternateLayout`, `Page/LayoutRule` (3)
- `MasterSpread/PageCount` (1)
- `Spread/BindingLocation`, `Spread/PageCount` (2)
- `MarginPreference/ColumnsPositions` (1) — page-level column-guide positions;
  a non-printing layout aid (see margins below).

### Non-printing layout aids (9)

InDesign guides / margins — non-printing aids that never appear in the
rendered PDF. Page items are placed by absolute geometry, not relative to
margins, so they do not move.

- `MarginPreference/Top`, `Bottom`, `Left`, `Right` (4) — page margin guides.
- `Guide/Location`, `Guide/Orientation` (2) — ruler guides.
- `GraphicLine/ItemTransform` (1) — the Leporello fold/Falz lines on the
  non-printable "Info" layer; the converter already skips `GraphicLine` on
  non-printable layers by design.
- `Polygon/FillTint` (1) — `FillTint=50` on the Leporello die-line markers,
  which use the `Druckformat` *spot* colour on the non-printable "Info" layer
  and a zero-width stroke; not rendered content.
- `Color/Visible` (1) — swatch visibility in the InDesign Swatches panel
  (authoring UI), not a render attribute.

### Metadata / structure with no render effect (5)

- `GraphicLayer/CurrentVisibility`, `GraphicLayer/OriginalVisibility` (2) —
  layer visibility *inside* placed Photoshop/Illustrator assets; the asset is
  extracted as a flat raster, so internal graphic-layer state is already baked
  in. All IDML layout `Layer` elements are `Visible=true`.
- `StoryPreference/FrameType`, `StoryDirection`, `StoryOrientation` (3) —
  story-direction metadata; all stories are left-to-right horizontal
  `TextFrameType`, which is what the converter assumes.

### Object styles / content type — already resolved per-item (18)

The converter reads fill/stroke/geometry directly off each page item, so the
object-style indirection and content-type tags carry no additional render
information for this batch.

- `ObjectStyle/AppliedParagraphStyle`, `EnableStoryOptions`,
  `EnableTextFrameAutoSizingOptions`, `EnableTextFrameBaselineOptions`,
  `EnableTextFrameColumnRuleOptions`, `EnableTextFrameFootnoteOptions`,
  `EnableTextFrameGeneralOptions`, `StrokeColor`, `StrokeWeight` (9) — these
  describe the `[Normal …]` / `[None]` object styles; the items that reference
  them carry their own fill/stroke, which the converter reads directly.
- `Rectangle/AppliedObjectStyle`, `Rectangle/ContentType` (2) — `[None]` /
  `[Normal Graphics Frame]` object-style reference and the
  Graphic/Unassigned content tag; no extra render data beyond the item's own
  attributes.
- `TextFrame/AppliedObjectStyle` (1) — as above, for text frames.
- `TextFrame/StrokeWeight` (1) — `0` or `1`; the corpus text frames have no
  visible border (`StrokeColor` resolves to none / the frame fill is the
  visible element).
- `TextFramePreference/ColumnRuleStrokeColor`,
  `TextFramePreference/ColumnRuleStrokeWidth` (2) — the rule drawn *between*
  text columns; `EnableTextFrameColumnRuleOptions` is off, so no column rule is
  painted even on the 2-column frames.
- `TextFramePreference/TextColumnFixedWidth` (1) — the fixed per-column width;
  Scribus derives column width from frame width ÷ column count + gutter, so
  the fixed width is redundant once `TextColumnCount` + `TextColumnGutter`
  (both `fixed`) are emitted.
- `GradientStop/StopColor` (1) — gradient stop colour; no page item uses a
  gradient fill (see unsupported `Gradient/Type`).
- `AnchoredObjectSetting/VerticalAlignment` (1) — default anchored-object
  vertical alignment; verified there are **zero** anchored/inline objects in
  any story, so it applies to nothing.

Bucket totals: 36 + 8 + 8 + 7 + 9 + 5 + 18 = **91**.
