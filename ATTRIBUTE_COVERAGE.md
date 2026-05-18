# IDML Attribute Coverage Audit

Diff of attributes **present** in the batch IDMLs against attributes **consumed** by `tools/idml_to_dsl.py`. Unconsumed attributes are silently dropped by the converter (no `UnhandledElement`).

## Method

- **PRESENT** set: every `(element-tag, attribute-name)` pair found by walking every XML part of each IDML zip. Tags/attrs reduced to local names (namespace stripped).
- **CONSUMED** set: determined by **runtime instrumentation**. The converter parses all XML through one shared `lxml` parser object (`idml_to_dsl._SECURE_XMLPARSER`). The audit attaches a custom element class to that parser; the class's `.get()` records every attribute key read. A real `convert()` is then run per IDML, capturing every attribute read across all 7 converter phases, keyed by the element's real local tag name.
- **Precision**: the CONSUMED set is runtime-observed, not grep-inferred -- no false attribution. **Limitation**: an attribute read only on a branch none of the audited IDMLs trigger would show as unconsumed (code-path coverage, not provably total). The converter has exactly one non-`.get()` attribute access (`child.attrib.values()` at `idml_to_dsl.py:1862`); it is an emptiness *test* on `AnchoredObjectSetting` that reads no specific key, so it consumes nothing semantically and its absence from CONSUMED is correct.

## Scope

- IDMLs audited: **9**
  - `26-03-Flyer A6 Hochformat Portrait.idml`
  - `26-03-Flyer A6 Hochformat Quadrat in Bild.idml`
  - `26-03-Flyer A6 Hochformat gruenes Cover.idml`
  - `26-03-Flyer A6 Hochformat zweigeteilt.idml`
  - `26-03-Flyer A6 Querformat Portrait.idml`
  - `26-03-Flyer A6 Querformat Quadrat in Bild.idml`
  - `26-03-Flyer A6 gruenes Cover.idml`
  - `26-03-Flyer A6 Querformat zweigeteilt.idml`
  - `26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover.idml`
- Distinct `(tag, attr)` pairs present: **2479**
- Consumed by converter: **80**
- Unconsumed (silently dropped): **2399**
  - `significant`: **926** (varying value: **109**, constant value: **817**)
  - `ignorable`: **1473**

### Converter run status

- Full conversions: **8/9**
- **1** IDML(s) failed conversion before completion. The CONSUMED set still includes every attribute read up to the failure point, but code-path coverage for those IDMLs is reduced -- an unconsumed attribute could be a coverage gap rather than a true converter omission. Failures:
  - `26-03-Flyer A6 Hochformat zweigeteilt.idml`: UnhandledElement: Unmapped assets in --asset-map (1 unique):

## Significant unconsumed attributes

These can affect geometry, layout, typography, spacing, colour, stroke, effects, transforms or text flow. **This is the converter fix list.** It is split into two tiers:

- **Tier A -- varying value**: the attribute takes more than one distinct value across the batch, i.e. a designer set it deliberately. Highest-confidence fix targets.
- **Tier B -- constant value**: a single value across the whole batch. Likely (not certainly) an unset InDesign default; kept `significant` under the conservative rule, but lower priority -- verify the value is the inert default before deciding to skip it.

### Tier A -- varying value (109)

#### `AnchoredObjectSetting` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `VerticalAlignment` | layout/visual attribute (name match 'align') | `BottomAlign`, `TopAlign` | 9/9 |

#### `BlendingSetting` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Opacity` | layout/visual attribute (name match 'opacity') | `100`, `70`, `90` | 9/9 |

#### `CharacterStyleRange` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `KentenFontSize` | layout/visual attribute (name match 'size') | `-0.013010114206790767`, `-0.9437175419746042`, `-1.258290055966139`, `-2.934267679305099`, `-3.3572365418469037`, `-3.375`, `-3.667834599131374`, `-3.989399120877444`, ... (+5 more) | 9/9 |
| `MiterLimit` | layout/visual attribute (name match 'miter') | `0.052040456827162976`, `11.737070717220396`, `13.428946167387615`, `13.5`, `14.671338396525496`, `15.957596483509777`, `17.90526155651682`, `18`, ... (+5 more) | 9/9 |
| `RubyFontSize` | layout/visual attribute (name match 'size') | `-0.013010114206790767`, `-0.9437175419746042`, `-1.258290055966139`, `-2.934267679305099`, `-3.3572365418469037`, `-3.375`, `-3.667834599131374`, `-3.989399120877444`, ... (+5 more) | 9/9 |
| `StrokeWeight` | layout/visual attribute (name match 'stroke') | `0.013010114206790744`, `0.9437175419746042`, `1.258290055966139`, `2.934267679305099`, `3.3572365418469037`, `3.375`, `3.667834599131374`, `3.989399120877444`, ... (+5 more) | 9/9 |

#### `Color` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Visible` | layout/visual attribute (name match 'visible') | `false`, `true` | 9/9 |

#### `FlexLayoutAttributeOption` (6)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `FlexGapColumn` | layout/visual attribute (name match 'column') | `0`, `20` | 9/9 |
| `FlexGapRow` | render-relevant element, effect unknown (conservative) | `0`, `20` | 9/9 |
| `FlexPaddingBottom` | render-relevant element, effect unknown (conservative) | `0`, `12` | 9/9 |
| `FlexPaddingLeft` | render-relevant element, effect unknown (conservative) | `0`, `12` | 9/9 |
| `FlexPaddingRight` | render-relevant element, effect unknown (conservative) | `0`, `12` | 9/9 |
| `FlexPaddingTop` | render-relevant element, effect unknown (conservative) | `0`, `12` | 9/9 |

#### `FrameFittingOption` (6)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `BottomCrop` | layout/visual attribute (name match 'crop') | `-0.04997618237507595`, `-0.08547461368664244`, `-0.12000000000000455`, `-0.1814157014156308`, `-0.5564560875857296`, `-0.7339049826186965`, `0`, `0.9933375068581967`, ... (+6 more) | 9/9 |
| `FittingAlignment` | layout/visual attribute (name match 'align') | `CenterAnchor`, `TopLeftAnchor` | 9/9 |
| `FittingOnEmptyFrame` | layout/visual attribute (name match 'fit') | `ContentToFrame`, `FillProportionally`, `None`, `Proportionally` | 9/9 |
| `LeftCrop` | layout/visual attribute (name match 'crop') | `-73.11528950556362`, `0`, `1.3106483741517996`, `106.32129729729738`, `124.87486591948311`, `161.95324675324676`, `173.65909090909093`, `199.75155278343948`, ... (+5 more) | 9/9 |
| `RightCrop` | layout/visual attribute (name match 'crop') | `-73.11528950556374`, `0`, `1.3106483741517678`, `122.35168587268868`, `161.95324675324673`, `173.65909090909088`, `238.34115113599114`, `242.5518592329754`, ... (+6 more) | 9/9 |
| `TopCrop` | layout/visual attribute (name match 'crop') | `-0.5564560875858433`, `0`, `138.70507919650663`, `167.70186336629558`, `192.32135465710394`, `21.26511111111131` | 9/9 |

#### `Gradient` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Type` | render-relevant element, effect unknown (conservative) | `Linear`, `Radial` | 9/9 |

#### `GradientStop` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Location` | render-relevant element, effect unknown (conservative) | `0`, `100` | 9/9 |
| `Midpoint` | layout/visual attribute (name match 'point') | `41.013636363636365`, `50` | 9/9 |
| `StopColor` | layout/visual attribute (name match 'color') | `Color/Black`, `Color/u335`, `Color/u85`, `Color/u97` | 9/9 |

#### `GraphicLayer` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `CurrentVisibility` | render-relevant element, effect unknown (conservative) | `false`, `true` | 9/9 |
| `OriginalVisibility` | render-relevant element, effect unknown (conservative) | `false`, `true` | 9/9 |

#### `GraphicLine` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ItemTransform` | layout/visual attribute (name match 'transform') | `1 0 0 1 14.173228346456654 0`, `1 0 0 1 294.8031496062992 0` | 1/9 |

#### `GridDataInformation` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `FontStyle` | layout/visual attribute (name match 'font') | `Regular`, `Roman` | 9/9 |

#### `Guide` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Location` | unconsumed attribute on a converter-handled element | `131.21574803149608`, `227.3385826771654`, `288.340157480315`, `70.24251968503938` | 2/9 |
| `Orientation` | unconsumed attribute on a converter-handled element | `Horizontal`, `Vertical` | 2/9 |

#### `Image` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EffectivePpi` | layout/visual attribute (name match 'effect') | `286 286`, `314 314`, `390 390`, `396 396`, `429 429`, `437 437`, `467 636`, `540 540`, ... (+7 more) | 9/9 |
| `ImageTypeName` | layout/visual attribute (name match 'image') | `$ID/JPEG`, `$ID/Photoshop` | 9/9 |

#### `Ink` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Angle` | layout/visual attribute (name match 'angle') | `0`, `15`, `45`, `75` | 9/9 |
| `Frequency` | render-relevant element, effect unknown (conservative) | `70`, `70.7107` | 9/9 |
| `NeutralDensity` | render-relevant element, effect unknown (conservative) | `0.16`, `0.61`, `0.6221999999999999`, `0.76`, `1.7`, `1.734` | 9/9 |
| `TrapOrder` | render-relevant element, effect unknown (conservative) | `1`, `2`, `3`, `4`, `5`, `6` | 9/9 |

#### `MarginPreference` (5)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Bottom` | unconsumed attribute on a converter-handled element | `0`, `34.01574803149607` | 9/9 |
| `ColumnsPositions` | layout/visual attribute (name match 'column') | `0 212.59842519685043`, `0 334.48818897637807`, `0 841.8897637795276` | 9/9 |
| `Left` | unconsumed attribute on a converter-handled element | `0`, `42.51968503937008` | 9/9 |
| `Right` | unconsumed attribute on a converter-handled element | `0`, `42.51968503937008` | 9/9 |
| `Top` | unconsumed attribute on a converter-handled element | `0`, `42.51968503937008` | 9/9 |

#### `MasterSpread` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `PageCount` | render-relevant element, effect unknown (conservative) | `1`, `2` | 9/9 |

#### `ObjectStyle` (9)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedParagraphStyle` | render-relevant element, effect unknown (conservative) | `ParagraphStyle/$ID/NormalParagraphStyle`, `ParagraphStyle/$ID/[No paragraph style]` | 9/9 |
| `EnableStoryOptions` | render-relevant element, effect unknown (conservative) | `false`, `true` | 9/9 |
| `EnableTextFrameAutoSizingOptions` | render-relevant element, effect unknown (conservative) | `false`, `true` | 9/9 |
| `EnableTextFrameBaselineOptions` | layout/visual attribute (name match 'baseline') | `false`, `true` | 9/9 |
| `EnableTextFrameColumnRuleOptions` | layout/visual attribute (name match 'column') | `false`, `true` | 9/9 |
| `EnableTextFrameFootnoteOptions` | render-relevant element, effect unknown (conservative) | `false`, `true` | 9/9 |
| `EnableTextFrameGeneralOptions` | render-relevant element, effect unknown (conservative) | `false`, `true` | 9/9 |
| `StrokeColor` | layout/visual attribute (name match 'color') | `Color/Black`, `Swatch/None` | 9/9 |
| `StrokeWeight` | layout/visual attribute (name match 'stroke') | `0`, `1` | 9/9 |

#### `Page` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedAlternateLayout` | unconsumed attribute on a converter-handled element | `n`, `ub4`, `ud6` | 9/9 |
| `AppliedMaster` | unconsumed attribute on a converter-handled element | `n`, `ubb`, `ud7`, `ufc7` | 9/9 |
| `LayoutRule` | layout/visual attribute (name match 'rule') | `Off`, `UseMaster` | 9/9 |

#### `ParagraphStyle` (23)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `DiacriticPosition` | layout/visual attribute (name match 'position') | `OpentypePosition`, `OpentypePositionFromBaseline` | 9/9 |
| `DropcapDetail` | layout/visual attribute (name match 'cap') | `0`, `1` | 9/9 |
| `Hyphenation` | layout/visual attribute (name match 'hyphen') | `false`, `true` | 9/9 |
| `HyphenationZone` | layout/visual attribute (name match 'hyphen') | `108`, `32.88662090941108`, `36` | 9/9 |
| `MiterLimit` | layout/visual attribute (name match 'miter') | `12`, `3.8231238483389807`, `4` | 9/9 |
| `ParagraphBorderBottomLeftCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphBorderBottomLineWeight` | layout/visual attribute (name match 'weight') | `0.9557809620847452`, `1`, `3` | 9/9 |
| `ParagraphBorderBottomRightCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphBorderLeftLineWeight` | layout/visual attribute (name match 'weight') | `0.9557809620847452`, `1`, `3` | 9/9 |
| `ParagraphBorderRightLineWeight` | layout/visual attribute (name match 'weight') | `0.9557809620847452`, `1`, `3` | 9/9 |
| `ParagraphBorderTopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphBorderTopLineWeight` | layout/visual attribute (name match 'weight') | `0.9557809620847452`, `1`, `3` | 9/9 |
| `ParagraphBorderTopRightCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphShadingBottomLeftCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphShadingBottomRightCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphShadingTopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `ParagraphShadingTopRightCornerRadius` | layout/visual attribute (name match 'corner') | `1`, `11.469371545016944`, `12`, `36` | 9/9 |
| `RuleAboveLineWeight` | layout/visual attribute (name match 'weight') | `1`, `3` | 9/9 |
| `RuleBelowLineWeight` | layout/visual attribute (name match 'weight') | `1`, `3` | 9/9 |
| `SpaceAfter` | layout/visual attribute (name match 'space') | `0`, `5.669291338582678` | 9/9 |
| `SplitColumnInsideGutter` | layout/visual attribute (name match 'gutter') | `18`, `5.481103484901845`, `6` | 9/9 |
| `StrokeWeight` | layout/visual attribute (name match 'stroke') | `0.9557809620847452`, `1`, `3` | 9/9 |
| `TreatIdeographicSpaceAsSpace` | layout/visual attribute (name match 'space') | `false`, `true` | 9/9 |

#### `ParagraphStyleRange` (16)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `HyphenationZone` | layout/visual attribute (name match 'hyphen') | `0.468364111444466`, `105.63363645498352`, `121.5`, `132.0420455687294`, `143.61836835158792`, `162`, `176.05606075830588`, `187.79313147552625`, ... (+5 more) | 9/9 |
| `ParagraphBorderBottomLeftCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphBorderBottomLineWeight` | layout/visual attribute (name match 'weight') | `0.039253496214100465`, `0.8779399363784466`, `0.9437175419746042`, `1.1705865818379289`, `1.2486256872937909`, `1.258290055966139`, `2.934267679305099`, `3.375`, ... (+5 more) | 9/9 |
| `ParagraphBorderBottomRightCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphBorderLeftLineWeight` | layout/visual attribute (name match 'weight') | `0.039253496214100465`, `0.8779399363784466`, `0.9437175419746042`, `1.1705865818379289`, `1.2486256872937909`, `1.258290055966139`, `2.934267679305099`, `3.375`, ... (+5 more) | 9/9 |
| `ParagraphBorderRightLineWeight` | layout/visual attribute (name match 'weight') | `0.039253496214100465`, `0.8779399363784466`, `0.9437175419746042`, `1.1705865818379289`, `1.2486256872937909`, `1.258290055966139`, `2.934267679305099`, `3.375`, ... (+5 more) | 9/9 |
| `ParagraphBorderTopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphBorderTopLineWeight` | layout/visual attribute (name match 'weight') | `0.039253496214100465`, `0.8779399363784466`, `0.9437175419746042`, `1.1705865818379289`, `1.2486256872937909`, `1.258290055966139`, `2.934267679305099`, `3.375`, ... (+5 more) | 9/9 |
| `ParagraphBorderTopRightCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphShadingBottomLeftCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphShadingBottomRightCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphShadingTopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `ParagraphShadingTopRightCornerRadius` | layout/visual attribute (name match 'corner') | `0.039253496214100465`, `10.535279236541363`, `11.324610503695256`, `14.047038982055152`, `14.983508247525497`, `15.099480671593675`, `35.2112121516612`, `40.5`, ... (+5 more) | 9/9 |
| `RuleAboveLineWeight` | layout/visual attribute (name match 'weight') | `0.013010114206790767`, `0.8779399363784466`, `0.9437175419746042`, `1.1705865818379289`, `1.2486256872937909`, `1.258290055966139`, `2.934267679305099`, `3.375`, ... (+5 more) | 9/9 |
| `RuleBelowLineWeight` | layout/visual attribute (name match 'weight') | `0.013010114206790767`, `0.8779399363784466`, `0.9437175419746042`, `1.1705865818379289`, `1.2486256872937909`, `1.258290055966139`, `2.934267679305099`, `3.375`, ... (+5 more) | 9/9 |
| `SplitColumnInsideGutter` | layout/visual attribute (name match 'gutter') | `0.07806068524074428`, `17.6056060758306`, `20.25`, `22.007007594788256`, `23.93639472526467`, `27`, `29.342676793051005`, `31.298855245921068`, ... (+5 more) | 9/9 |

#### `Polygon` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `FillTint` | layout/visual attribute (name match 'fill') | `-1`, `50` | 9/9 |
| `MiterLimit` | layout/visual attribute (name match 'miter') | `10`, `20.865903497280705` | 9/9 |

#### `Rectangle` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[None]`, `ObjectStyle/$ID/[Normal Graphics Frame]` | 9/9 |
| `ContentType` | unconsumed attribute on a converter-handled element | `GraphicType`, `Unassigned` | 9/9 |

#### `Spread` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `BindingLocation` | unconsumed attribute on a converter-handled element | `0`, `1` | 9/9 |
| `PageCount` | unconsumed attribute on a converter-handled element | `1`, `2` | 9/9 |

#### `StoryPreference` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `FrameType` | render-relevant element, effect unknown (conservative) | `FrameGridType`, `TextFrameType`, `Unknown` | 9/9 |
| `StoryDirection` | render-relevant element, effect unknown (conservative) | `LeftToRightDirection`, `UnknownDirection` | 9/9 |
| `StoryOrientation` | render-relevant element, effect unknown (conservative) | `Horizontal`, `Unknown` | 9/9 |

#### `TextFrame` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[None]`, `ObjectStyle/$ID/[Normal Graphics Frame]`, `ObjectStyle/$ID/[Normal Text Frame]` | 9/9 |
| `StrokeWeight` | layout/visual attribute (name match 'stroke') | `0`, `1` | 9/9 |

#### `TextFramePreference` (6)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ColumnRuleStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black`, `Color/C=0 M=0 Y=100 K=0`, `Color/C=0 M=100 Y=0 K=0`, `Color/C=85 M=35 Y=95 K=10`, `Swatch/None` | 9/9 |
| `ColumnRuleStrokeWidth` | layout/visual attribute (name match 'stroke') | `0`, `1` | 9/9 |
| `TextColumnCount` | layout/visual attribute (name match 'column') | `1`, `2` | 9/9 |
| `TextColumnFixedWidth` | layout/visual attribute (name match 'column') | `118.09944119712051`, `144`, `151.37007874015754`, `158.740157480315`, `158.74015748031613`, `165.6959389097955`, `184.25196850393698`, `184.25196850393706`, ... (+16 more) | 9/9 |
| `TextColumnGutter` | layout/visual attribute (name match 'gutter') | `0.2737311551730461`, `10.535279236541363`, `10.96220696980369`, `11.324610503695256`, `12`, `13.5`, `14.047038982055152`, `14.983508247525497`, ... (+10 more) | 9/9 |
| `VerticalJustification` | layout/visual attribute (name match 'justif') | `CenterAlign`, `TopAlign` | 9/9 |

### Tier B -- constant value (817)

#### `AnchoredObjectSetting` (11)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AnchorPoint` | layout/visual attribute (name match 'anchor') | `BottomRightAnchor` | 9/9 |
| `AnchorSpaceAbove` | layout/visual attribute (name match 'space') | `0` | 9/9 |
| `AnchorXoffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `AnchorYoffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `AnchoredPosition` | layout/visual attribute (name match 'position') | `InlinePosition` | 9/9 |
| `HorizontalAlignment` | layout/visual attribute (name match 'align') | `LeftAlign` | 9/9 |
| `HorizontalReferencePoint` | layout/visual attribute (name match 'horizontal') | `TextFrame` | 9/9 |
| `LockPosition` | layout/visual attribute (name match 'position') | `false` | 9/9 |
| `PinPosition` | layout/visual attribute (name match 'position') | `true` | 9/9 |
| `SpineRelative` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `VerticalReferencePoint` | layout/visual attribute (name match 'vertical') | `LineBaseline` | 9/9 |

#### `BaselineFrameGridOption` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `BaselineFrameGridIncrement` | layout/visual attribute (name match 'baseline') | `12` | 9/9 |
| `BaselineFrameGridRelativeOption` | layout/visual attribute (name match 'baseline') | `TopOfInset` | 9/9 |
| `StartingOffsetForBaselineFrameGrid` | layout/visual attribute (name match 'baseline') | `0` | 9/9 |
| `UseCustomBaselineFrameGrid` | layout/visual attribute (name match 'baseline') | `false` | 9/9 |

#### `BulletChar` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `BulletCharacterType` | layout/visual attribute (name match 'bullet') | `UnicodeOnly` | 9/9 |
| `BulletCharacterValue` | layout/visual attribute (name match 'bullet') | `8226` | 9/9 |

#### `CellStyle` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedParagraphStyle` | render-relevant element, effect unknown (conservative) | `ParagraphStyle/$ID/[No paragraph style]` | 9/9 |

#### `CharacterStyle` (6)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EmitCss` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `EpubAriaRole` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `ExtendedKeyboardShortcut` | unconsumed attribute on a converter-handled element | `0 0 0` | 9/9 |
| `Imported` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `IncludeClass` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `SplitDocument` | unconsumed attribute on a converter-handled element | `false` | 9/9 |

#### `CharacterStyleRange` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedCharacterStyle` | unconsumed attribute on a converter-handled element | `CharacterStyle/$ID/[No character style]` | 9/9 |
| `DiacriticPosition` | layout/visual attribute (name match 'position') | `OpentypePositionFromBaseline` | 1/9 |
| `KerningMethod` | layout/visual attribute (name match 'kerning') | `$ID/Optical` | 9/9 |
| `OTFContextualAlternate` | unconsumed attribute on a converter-handled element | `false` | 9/9 |

#### `ClippingPathSettings` (10)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedPathName` | layout/visual attribute (name match 'path') | `$ID/` | 9/9 |
| `ClippingType` | render-relevant element, effect unknown (conservative) | `None` | 9/9 |
| `IncludeInsideEdges` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `Index` | render-relevant element, effect unknown (conservative) | `-1` | 9/9 |
| `InsetFrame` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `InvertPath` | layout/visual attribute (name match 'path') | `false` | 9/9 |
| `RestrictToFrame` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `Threshold` | render-relevant element, effect unknown (conservative) | `25` | 9/9 |
| `Tolerance` | render-relevant element, effect unknown (conservative) | `2` | 9/9 |
| `UseHighResolutionImage` | layout/visual attribute (name match 'image') | `true` | 9/9 |

#### `Color` (5)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AlternateColorValue` | layout/visual attribute (name match 'color') | `(empty)` | 9/9 |
| `AlternateSpace` | layout/visual attribute (name match 'space') | `NoAlternateColor` | 9/9 |
| `ConvertToHsb` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `SpotInkAliasSpotColorReference` | layout/visual attribute (name match 'color') | `n` | 1/9 |
| `SwatchCreatorID` | layout/visual attribute (name match 'swatch') | `7937` | 9/9 |

#### `ContourOption` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ContourPathName` | layout/visual attribute (name match 'path') | `$ID/` | 9/9 |
| `ContourType` | render-relevant element, effect unknown (conservative) | `SameAsClipping` | 9/9 |
| `IncludeInsideEdges` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |

#### `FlattenerPreference` (5)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ClipComplexRegions` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `ConvertAllStrokesToOutlines` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `ConvertAllTextToOutlines` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `GradientAndMeshResolution` | layout/visual attribute (name match 'gradient') | `150` | 9/9 |
| `LineArtAndTextResolution` | unconsumed attribute on a converter-handled element | `300` | 9/9 |

#### `FlexLayoutAttributeOption` (7)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AlignContent` | layout/visual attribute (name match 'align') | `FlexStart` | 9/9 |
| `AlignItems` | layout/visual attribute (name match 'align') | `FlexStart` | 9/9 |
| `FlexDirection` | render-relevant element, effect unknown (conservative) | `FlexRow` | 9/9 |
| `FlexHeightMode` | layout/visual attribute (name match 'height') | `FlexAuto` | 9/9 |
| `FlexWidthMode` | layout/visual attribute (name match 'width') | `FlexAuto` | 9/9 |
| `FlexWrap` | layout/visual attribute (name match 'wrap') | `NoWrap` | 9/9 |
| `JustifyContent` | layout/visual attribute (name match 'justif') | `FlexStart` | 9/9 |

#### `FrameFittingOption` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AutoFit` | layout/visual attribute (name match 'fit') | `false` | 9/9 |

#### `Gradient` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `SwatchCreatorID` | layout/visual attribute (name match 'swatch') | `7937` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `false` | 9/9 |

#### `GraphicLayer` (10)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AdjustmentLayer` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `ExportState` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `FXLayer` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `HasExportState` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `HasPrintState` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `HasViewState` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `Locked` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `PrintState` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `SeparatorLayer` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `ViewState` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |

#### `GraphicLayerOption` (1)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `UpdateLinkOption` | render-relevant element, effect unknown (conservative) | `KeepOverrides` | 9/9 |

#### `GraphicLine` (24)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[Normal Graphics Frame]` | 1/9 |
| `ContentType` | unconsumed attribute on a converter-handled element | `Unassigned` | 1/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 1/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 1/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 1/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 1/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 1/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 1/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 1/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 1/9 |
| `GradientStrokeHiliteAngle` | layout/visual attribute (name match 'stroke') | `0` | 1/9 |
| `GradientStrokeHiliteLength` | layout/visual attribute (name match 'stroke') | `0` | 1/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `0` | 1/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 1/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 1/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 1/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 1/9 |
| `LockState` | unconsumed attribute on a converter-handled element | `None` | 1/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 1/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 1/9 |
| `StrokeColor` | layout/visual attribute (name match 'color') | `Color/Faltung` | 1/9 |
| `StrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Canned Dashed 4x4` | 1/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 1/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 1/9 |

#### `GridDataInformation` (8)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `CharacterAki` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `CharacterAlignment` | layout/visual attribute (name match 'align') | `AlignEmCenter` | 9/9 |
| `GridAlignment` | layout/visual attribute (name match 'align') | `AlignEmCenter` | 9/9 |
| `HorizontalScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `LineAki` | unconsumed attribute on a converter-handled element | `9` | 9/9 |
| `LineAlignment` | layout/visual attribute (name match 'align') | `LeftOrTopLineJustify` | 9/9 |
| `PointSize` | layout/visual attribute (name match 'size') | `12` | 9/9 |
| `VerticalScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |

#### `Group` (25)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[None]` | 9/9 |
| `CornerRadius` | layout/visual attribute (name match 'corner') | `0.167` | 1/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `MiterLimit` | layout/visual attribute (name match 'miter') | `10` | 5/9 |
| `Nonprinting` | unconsumed attribute on a converter-handled element | `true` | 1/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `StrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 5/9 |
| `TopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `0.167` | 1/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `Guide` (7)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `FitToPage` | layout/visual attribute (name match 'fit') | `true` | 2/9 |
| `GuideType` | unconsumed attribute on a converter-handled element | `Ruler` | 2/9 |
| `GuideZone` | unconsumed attribute on a converter-handled element | `1` | 2/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 2/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 2/9 |
| `PageIndex` | unconsumed attribute on a converter-handled element | `1` | 2/9 |
| `ViewThreshold` | unconsumed attribute on a converter-handled element | `5` | 2/9 |

#### `Image` (17)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ActualPpi` | unconsumed attribute on a converter-handled element | `300 300` | 9/9 |
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[None]` | 9/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `ImageRenderingIntent` | layout/visual attribute (name match 'rendering') | `UseColorSettings` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `Space` | layout/visual attribute (name match 'space') | `$ID/#Links_CMYK` | 9/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `Ink` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ConvertToProcess` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `InkType` | render-relevant element, effect unknown (conservative) | `Normal` | 9/9 |
| `PrintInk` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |

#### `Link` (15)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AssetID` | unconsumed attribute on a converter-handled element | `$ID/` | 9/9 |
| `AssetURL` | unconsumed attribute on a converter-handled element | `$ID/` | 9/9 |
| `CanEmbed` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `CanPackage` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `CanUnembed` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `ExportPolicy` | unconsumed attribute on a converter-handled element | `NoAutoExport` | 9/9 |
| `ImportPolicy` | unconsumed attribute on a converter-handled element | `NoAutoImport` | 9/9 |
| `LinkClassID` | unconsumed attribute on a converter-handled element | `35906` | 9/9 |
| `LinkClientID` | unconsumed attribute on a converter-handled element | `257` | 9/9 |
| `LinkObjectModified` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `LinkResourceModified` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `PDFIdentifier` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `RenditionData` | unconsumed attribute on a converter-handled element | `Actual` | 9/9 |
| `ShowInUI` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `StoredState` | unconsumed attribute on a converter-handled element | `Normal` | 9/9 |

#### `MarginPreference` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ColumnCount` | layout/visual attribute (name match 'column') | `1` | 9/9 |
| `ColumnDirection` | layout/visual attribute (name match 'column') | `Horizontal` | 9/9 |
| `ColumnGutter` | layout/visual attribute (name match 'gutter') | `12` | 9/9 |

#### `MasterSpread` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ItemTransform` | layout/visual attribute (name match 'transform') | `1 0 0 1 0 0` | 9/9 |
| `OverriddenPageItemProps` | render-relevant element, effect unknown (conservative) | `(empty)` | 9/9 |
| `PrimaryTextFrame` | render-relevant element, effect unknown (conservative) | `n` | 9/9 |
| `ShowMasterItems` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |

#### `NumberingRestartPolicies` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `LowerLevel` | render-relevant element, effect unknown (conservative) | `0` | 9/9 |
| `RestartPolicy` | render-relevant element, effect unknown (conservative) | `AnyPreviousLevel` | 9/9 |
| `UpperLevel` | render-relevant element, effect unknown (conservative) | `0` | 9/9 |

#### `ObjectStyle` (50)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedNamedGrid` | layout/visual attribute (name match 'grid') | `n` | 9/9 |
| `ApplyNextParagraphStyle` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `ArrowHeadAlignment` | layout/visual attribute (name match 'align') | `InsidePath` | 9/9 |
| `BottomLeftCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `BottomLeftCornerRadius` | layout/visual attribute (name match 'corner') | `12` | 9/9 |
| `BottomRightCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `BottomRightCornerRadius` | layout/visual attribute (name match 'corner') | `12` | 9/9 |
| `CornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `CornerRadius` | layout/visual attribute (name match 'corner') | `12` | 9/9 |
| `EmitCss` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |
| `EnableAnchoredObjectOptions` | layout/visual attribute (name match 'anchor') | `false` | 9/9 |
| `EnableExportTagging` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `EnableFill` | layout/visual attribute (name match 'fill') | `true` | 9/9 |
| `EnableFlexLayoutAttributes` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `EnableFrameFittingOptions` | layout/visual attribute (name match 'fit') | `false` | 9/9 |
| `EnableObjectExportAltTextOptions` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `EnableObjectExportEpubOptions` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `EnableObjectExportTaggedPdfOptions` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `EnableParagraphStyle` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `EnableStroke` | layout/visual attribute (name match 'stroke') | `true` | 9/9 |
| `EnableStrokeAndCornerOptions` | layout/visual attribute (name match 'stroke') | `true` | 9/9 |
| `EnableTextWrapAndOthers` | layout/visual attribute (name match 'wrap') | `false` | 9/9 |
| `EnableTransformAttributes` | layout/visual attribute (name match 'transform') | `false` | 9/9 |
| `EndCap` | layout/visual attribute (name match 'cap') | `ButtEndCap` | 9/9 |
| `EndJoin` | layout/visual attribute (name match 'join') | `MiterEndJoin` | 9/9 |
| `EpubAriaLabel` | render-relevant element, effect unknown (conservative) | `(empty)` | 9/9 |
| `EpubAriaLabelSourceType` | render-relevant element, effect unknown (conservative) | `NoneARIALabel` | 9/9 |
| `EpubAriaRole` | render-relevant element, effect unknown (conservative) | `(empty)` | 9/9 |
| `ExtendedKeyboardShortcut` | render-relevant element, effect unknown (conservative) | `0 0 0` | 9/9 |
| `FillColor` | layout/visual attribute (name match 'color') | `Swatch/None` | 9/9 |
| `FillTint` | layout/visual attribute (name match 'fill') | `-1` | 9/9 |
| `GapColor` | layout/visual attribute (name match 'color') | `Swatch/None` | 9/9 |
| `GapTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `IncludeClass` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |
| `LeftArrowHeadScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `LeftLineEnd` | render-relevant element, effect unknown (conservative) | `None` | 9/9 |
| `MiterLimit` | layout/visual attribute (name match 'miter') | `4` | 9/9 |
| `Nonprinting` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `OverprintStroke` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `RightArrowHeadScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `RightLineEnd` | render-relevant element, effect unknown (conservative) | `None` | 9/9 |
| `StrokeAlignment` | layout/visual attribute (name match 'stroke') | `CenterAlignment` | 9/9 |
| `StrokeTint` | layout/visual attribute (name match 'stroke') | `-1` | 9/9 |
| `StrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `TopLeftCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `TopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `12` | 9/9 |
| `TopRightCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `TopRightCornerRadius` | layout/visual attribute (name match 'corner') | `12` | 9/9 |

#### `ObjectStyleContentEffectsCategorySettings` (10)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EnableBevelEmboss` | layout/visual attribute (name match 'bevel') | `true` | 9/9 |
| `EnableDirectionalFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableDropShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableGradientFeather` | layout/visual attribute (name match 'gradient') | `true` | 9/9 |
| `EnableInnerGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableInnerShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableOuterGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableSatin` | layout/visual attribute (name match 'satin') | `true` | 9/9 |
| `EnableTransparency` | layout/visual attribute (name match 'transparen') | `true` | 9/9 |

#### `ObjectStyleFillEffectsCategorySettings` (10)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EnableBevelEmboss` | layout/visual attribute (name match 'bevel') | `true` | 9/9 |
| `EnableDirectionalFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableDropShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableGradientFeather` | layout/visual attribute (name match 'gradient') | `true` | 9/9 |
| `EnableInnerGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableInnerShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableOuterGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableSatin` | layout/visual attribute (name match 'satin') | `true` | 9/9 |
| `EnableTransparency` | layout/visual attribute (name match 'transparen') | `true` | 9/9 |

#### `ObjectStyleObjectEffectsCategorySettings` (10)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EnableBevelEmboss` | layout/visual attribute (name match 'bevel') | `true` | 9/9 |
| `EnableDirectionalFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableDropShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableGradientFeather` | layout/visual attribute (name match 'gradient') | `true` | 9/9 |
| `EnableInnerGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableInnerShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableOuterGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableSatin` | layout/visual attribute (name match 'satin') | `true` | 9/9 |
| `EnableTransparency` | layout/visual attribute (name match 'transparen') | `true` | 9/9 |

#### `ObjectStyleStrokeEffectsCategorySettings` (10)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EnableBevelEmboss` | layout/visual attribute (name match 'bevel') | `true` | 9/9 |
| `EnableDirectionalFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableDropShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableFeather` | layout/visual attribute (name match 'feather') | `true` | 9/9 |
| `EnableGradientFeather` | layout/visual attribute (name match 'gradient') | `true` | 9/9 |
| `EnableInnerGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableInnerShadow` | layout/visual attribute (name match 'shadow') | `true` | 9/9 |
| `EnableOuterGlow` | layout/visual attribute (name match 'glow') | `true` | 9/9 |
| `EnableSatin` | layout/visual attribute (name match 'satin') | `true` | 9/9 |
| `EnableTransparency` | layout/visual attribute (name match 'transparen') | `true` | 9/9 |

#### `Oval` (23)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[Normal Graphics Frame]` | 9/9 |
| `ContentType` | unconsumed attribute on a converter-handled element | `Unassigned` | 9/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 1/9 |
| `MiterLimit` | layout/visual attribute (name match 'miter') | `10` | 9/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `StrokeWeight` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `PDF` (13)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[None]` | 9/9 |
| `CMYKVectorPolicy` | unconsumed attribute on a converter-handled element | `IgnoreAll` | 9/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GrayVectorPolicy` | unconsumed attribute on a converter-handled element | `IgnoreAll` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `ImageTypeName` | layout/visual attribute (name match 'image') | `$ID/Adobe Portable Document Format (PDF)` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `RGBVectorPolicy` | unconsumed attribute on a converter-handled element | `HonorAllProfiles` | 9/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `Page` (8)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedTrapPreset` | unconsumed attribute on a converter-handled element | `TrapPreset/$ID/kDefaultTrapStyleName` | 9/9 |
| `GridStartingPoint` | layout/visual attribute (name match 'point') | `TopOutside` | 9/9 |
| `MasterPageTransform` | layout/visual attribute (name match 'transform') | `1 0 0 1 0 0` | 9/9 |
| `OptionalPage` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OverrideList` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `SnapshotBlendingMode` | layout/visual attribute (name match 'blend') | `IgnoreLayoutSnapshots` | 9/9 |
| `TabOrder` | layout/visual attribute (name match 'border') | `(empty)` | 9/9 |
| `UseMasterGrid` | layout/visual attribute (name match 'grid') | `true` | 9/9 |

#### `ParagraphStyle` (253)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AllowArbitraryHyphenation` | layout/visual attribute (name match 'hyphen') | `false` | 9/9 |
| `AppliedLanguage` | unconsumed attribute on a converter-handled element | `$ID/de_DE_2006` | 9/9 |
| `AutoLeading` | layout/visual attribute (name match 'leading') | `120` | 9/9 |
| `AutoTcy` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `AutoTcyIncludeRoman` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `BaselineShift` | layout/visual attribute (name match 'baseline') | `0` | 9/9 |
| `BulletsAlignment` | layout/visual attribute (name match 'align') | `LeftAlign` | 9/9 |
| `BulletsAndNumberingListType` | layout/visual attribute (name match 'bullet') | `NoList` | 9/9 |
| `BulletsTextAfter` | layout/visual attribute (name match 'bullet') | `^t` | 9/9 |
| `BunriKinshi` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `Capitalization` | layout/visual attribute (name match 'cap') | `Normal` | 9/9 |
| `CharacterAlignment` | layout/visual attribute (name match 'align') | `AlignEmCenter` | 9/9 |
| `CharacterDirection` | unconsumed attribute on a converter-handled element | `DefaultDirection` | 9/9 |
| `CharacterRotation` | layout/visual attribute (name match 'rotation') | `0` | 9/9 |
| `CjkGridTracking` | layout/visual attribute (name match 'tracking') | `false` | 9/9 |
| `Composer` | unconsumed attribute on a converter-handled element | `HL Composer` | 9/9 |
| `DesiredGlyphScaling` | unconsumed attribute on a converter-handled element | `100` | 9/9 |
| `DesiredLetterSpacing` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `DesiredWordSpacing` | unconsumed attribute on a converter-handled element | `100` | 9/9 |
| `DigitsType` | unconsumed attribute on a converter-handled element | `DefaultDigits` | 9/9 |
| `DropCapCharacters` | layout/visual attribute (name match 'cap') | `0` | 9/9 |
| `DropCapLines` | layout/visual attribute (name match 'cap') | `0` | 9/9 |
| `EmitCss` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `EmptyGrepStyles` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `EmptyLineStyles` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `EmptyNestedStyles` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `EndJoin` | layout/visual attribute (name match 'join') | `MiterEndJoin` | 9/9 |
| `EpubAriaRole` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `ExtendedKeyboardShortcut` | unconsumed attribute on a converter-handled element | `0 0 0` | 9/9 |
| `FillTint` | layout/visual attribute (name match 'fill') | `-1` | 9/9 |
| `FirstLineIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `GlyphForm` | unconsumed attribute on a converter-handled element | `None` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `-1` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `-1` | 9/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 9/9 |
| `GridAlignFirstLineOnly` | layout/visual attribute (name match 'align') | `false` | 9/9 |
| `GridGyoudori` | layout/visual attribute (name match 'grid') | `0` | 9/9 |
| `HorizontalScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `HyphenWeight` | layout/visual attribute (name match 'weight') | `5` | 9/9 |
| `HyphenateAcrossColumns` | layout/visual attribute (name match 'column') | `true` | 9/9 |
| `HyphenateAfterFirst` | layout/visual attribute (name match 'hyphen') | `2` | 9/9 |
| `HyphenateBeforeLast` | layout/visual attribute (name match 'hyphen') | `2` | 9/9 |
| `HyphenateCapitalizedWords` | layout/visual attribute (name match 'cap') | `true` | 9/9 |
| `HyphenateLadderLimit` | layout/visual attribute (name match 'hyphen') | `3` | 9/9 |
| `HyphenateLastWord` | layout/visual attribute (name match 'hyphen') | `true` | 9/9 |
| `HyphenateWordsLongerThan` | layout/visual attribute (name match 'hyphen') | `5` | 9/9 |
| `IgnoreEdgeAlignment` | layout/visual attribute (name match 'align') | `false` | 9/9 |
| `Imported` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `IncludeClass` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `Jidori` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `Kashidas` | unconsumed attribute on a converter-handled element | `DefaultKashidas` | 9/9 |
| `KeepAllLinesTogether` | layout/visual attribute (name match 'keep') | `false` | 9/9 |
| `KeepFirstLines` | layout/visual attribute (name match 'keep') | `2` | 9/9 |
| `KeepLastLines` | layout/visual attribute (name match 'keep') | `2` | 9/9 |
| `KeepLinesTogether` | layout/visual attribute (name match 'keep') | `false` | 9/9 |
| `KeepRuleAboveInFrame` | layout/visual attribute (name match 'keep') | `false` | 9/9 |
| `KeepWithNext` | layout/visual attribute (name match 'keep') | `0` | 9/9 |
| `KeepWithPrevious` | layout/visual attribute (name match 'keep') | `false` | 9/9 |
| `KentenAlignment` | layout/visual attribute (name match 'align') | `AlignKentenCenter` | 9/9 |
| `KentenCharacterSet` | unconsumed attribute on a converter-handled element | `CharacterInput` | 9/9 |
| `KentenCustomCharacter` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `KentenFontSize` | layout/visual attribute (name match 'size') | `-1` | 9/9 |
| `KentenKind` | unconsumed attribute on a converter-handled element | `None` | 9/9 |
| `KentenOverprintFill` | layout/visual attribute (name match 'fill') | `Auto` | 9/9 |
| `KentenOverprintStroke` | layout/visual attribute (name match 'stroke') | `Auto` | 9/9 |
| `KentenPlacement` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `KentenPosition` | layout/visual attribute (name match 'position') | `AboveRight` | 9/9 |
| `KentenStrokeTint` | layout/visual attribute (name match 'stroke') | `-1` | 9/9 |
| `KentenTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `KentenWeight` | layout/visual attribute (name match 'weight') | `-1` | 9/9 |
| `KentenXScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `KentenYScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `KerningMethod` | layout/visual attribute (name match 'kerning') | `$ID/Metrics` | 9/9 |
| `KeyboardDirection` | unconsumed attribute on a converter-handled element | `DefaultDirection` | 9/9 |
| `KinsokuHangType` | unconsumed attribute on a converter-handled element | `None` | 9/9 |
| `KinsokuType` | unconsumed attribute on a converter-handled element | `KinsokuPushInFirst` | 9/9 |
| `LastLineIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `LeadingAki` | layout/visual attribute (name match 'leading') | `-1` | 9/9 |
| `LeftIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `Ligatures` | layout/visual attribute (name match 'ligature') | `true` | 9/9 |
| `MaximumGlyphScaling` | unconsumed attribute on a converter-handled element | `100` | 9/9 |
| `MaximumLetterSpacing` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `MaximumWordSpacing` | unconsumed attribute on a converter-handled element | `133` | 9/9 |
| `MergeConsecutiveParaBorders` | layout/visual attribute (name match 'border') | `true` | 9/9 |
| `MinimumGlyphScaling` | unconsumed attribute on a converter-handled element | `100` | 9/9 |
| `MinimumLetterSpacing` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `MinimumWordSpacing` | unconsumed attribute on a converter-handled element | `80` | 9/9 |
| `NoBreak` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `NumberingAlignment` | layout/visual attribute (name match 'align') | `LeftAlign` | 9/9 |
| `NumberingApplyRestartPolicy` | layout/visual attribute (name match 'number') | `true` | 9/9 |
| `NumberingContinue` | layout/visual attribute (name match 'number') | `true` | 9/9 |
| `NumberingExpression` | layout/visual attribute (name match 'number') | `^#.^t` | 9/9 |
| `NumberingLevel` | layout/visual attribute (name match 'number') | `1` | 9/9 |
| `NumberingStartAt` | layout/visual attribute (name match 'number') | `1` | 9/9 |
| `OTFContextualAlternate` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `OTFDiscretionaryLigature` | layout/visual attribute (name match 'ligature') | `false` | 9/9 |
| `OTFFigureStyle` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `OTFFraction` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFHVKana` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFHistorical` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFJustificationAlternate` | layout/visual attribute (name match 'justif') | `false` | 9/9 |
| `OTFLocale` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `OTFMark` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `OTFOrdinal` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFOverlapSwash` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFProportionalMetrics` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFRomanItalics` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFSlashedZero` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFStretchedAlternate` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFStylisticAlternate` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFStylisticSets` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `OTFSwash` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OTFTitling` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OverprintFill` | layout/visual attribute (name match 'fill') | `false` | 9/9 |
| `OverprintStroke` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `PageNumberType` | layout/visual attribute (name match 'number') | `AutoPageNumber` | 9/9 |
| `ParagraphBorderBottomLeftCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphBorderBottomOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphBorderBottomOrigin` | layout/visual attribute (name match 'border') | `DescentBottomOrigin` | 9/9 |
| `ParagraphBorderBottomRightCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphBorderDisplayIfSplits` | layout/visual attribute (name match 'border') | `false` | 9/9 |
| `ParagraphBorderGapOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `ParagraphBorderGapTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `ParagraphBorderLeftOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphBorderOn` | layout/visual attribute (name match 'border') | `false` | 9/9 |
| `ParagraphBorderOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `ParagraphBorderRightOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphBorderStrokeEndCap` | layout/visual attribute (name match 'stroke') | `ButtEndCap` | 9/9 |
| `ParagraphBorderStrokeEndJoin` | layout/visual attribute (name match 'stroke') | `MiterEndJoin` | 9/9 |
| `ParagraphBorderTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `ParagraphBorderTopLeftCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphBorderTopOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphBorderTopOrigin` | layout/visual attribute (name match 'border') | `AscentTopOrigin` | 9/9 |
| `ParagraphBorderTopRightCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphBorderWidth` | layout/visual attribute (name match 'width') | `ColumnWidth` | 9/9 |
| `ParagraphBreakType` | unconsumed attribute on a converter-handled element | `Anywhere` | 9/9 |
| `ParagraphDirection` | unconsumed attribute on a converter-handled element | `LeftToRightDirection` | 9/9 |
| `ParagraphGyoudori` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `ParagraphJustification` | layout/visual attribute (name match 'justif') | `DefaultJustification` | 9/9 |
| `ParagraphKashidaWidth` | layout/visual attribute (name match 'width') | `2` | 9/9 |
| `ParagraphShadingBottomLeftCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphShadingBottomOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphShadingBottomOrigin` | layout/visual attribute (name match 'shading') | `DescentBottomOrigin` | 9/9 |
| `ParagraphShadingBottomRightCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphShadingClipToFrame` | layout/visual attribute (name match 'shading') | `false` | 9/9 |
| `ParagraphShadingLeftOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphShadingOn` | layout/visual attribute (name match 'shading') | `false` | 9/9 |
| `ParagraphShadingOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `ParagraphShadingRightOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphShadingSuppressPrinting` | layout/visual attribute (name match 'shading') | `false` | 9/9 |
| `ParagraphShadingTint` | layout/visual attribute (name match 'tint') | `20` | 9/9 |
| `ParagraphShadingTopLeftCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphShadingTopOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ParagraphShadingTopOrigin` | layout/visual attribute (name match 'shading') | `AscentTopOrigin` | 9/9 |
| `ParagraphShadingTopRightCornerOption` | layout/visual attribute (name match 'corner') | `None` | 9/9 |
| `ParagraphShadingWidth` | layout/visual attribute (name match 'width') | `ColumnWidth` | 9/9 |
| `Position` | layout/visual attribute (name match 'position') | `Normal` | 9/9 |
| `PositionalForm` | layout/visual attribute (name match 'position') | `None` | 9/9 |
| `ProviderHyphenationStyle` | layout/visual attribute (name match 'hyphen') | `HyphAll` | 9/9 |
| `Rensuuji` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `RightIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `RotateSingleByteCharacters` | layout/visual attribute (name match 'rotate') | `false` | 9/9 |
| `RubyAlignment` | layout/visual attribute (name match 'align') | `RubyJIS` | 9/9 |
| `RubyAutoAlign` | layout/visual attribute (name match 'align') | `true` | 9/9 |
| `RubyAutoScaling` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `RubyAutoTcyAutoScale` | layout/visual attribute (name match 'scale') | `true` | 9/9 |
| `RubyAutoTcyDigits` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `RubyAutoTcyIncludeRoman` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `RubyFontSize` | layout/visual attribute (name match 'size') | `-1` | 9/9 |
| `RubyOpenTypePro` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `RubyOverhang` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `RubyOverprintFill` | layout/visual attribute (name match 'fill') | `Auto` | 9/9 |
| `RubyOverprintStroke` | layout/visual attribute (name match 'stroke') | `Auto` | 9/9 |
| `RubyParentOverhangAmount` | unconsumed attribute on a converter-handled element | `RubyOverhangOneRuby` | 9/9 |
| `RubyParentScalingPercent` | unconsumed attribute on a converter-handled element | `66` | 9/9 |
| `RubyParentSpacing` | unconsumed attribute on a converter-handled element | `RubyParent121Aki` | 9/9 |
| `RubyPosition` | layout/visual attribute (name match 'position') | `AboveRight` | 9/9 |
| `RubyStrokeTint` | layout/visual attribute (name match 'stroke') | `-1` | 9/9 |
| `RubyTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `RubyType` | unconsumed attribute on a converter-handled element | `PerCharacterRuby` | 9/9 |
| `RubyWeight` | layout/visual attribute (name match 'weight') | `-1` | 9/9 |
| `RubyXOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `RubyXScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `RubyYOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `RubyYScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `RuleAbove` | layout/visual attribute (name match 'rule') | `false` | 9/9 |
| `RuleAboveGapOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `RuleAboveGapTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `RuleAboveLeftIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `RuleAboveOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `RuleAboveOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `RuleAboveRightIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `RuleAboveTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `RuleAboveWidth` | layout/visual attribute (name match 'width') | `ColumnWidth` | 9/9 |
| `RuleBelow` | layout/visual attribute (name match 'rule') | `false` | 9/9 |
| `RuleBelowGapOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `RuleBelowGapTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `RuleBelowLeftIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `RuleBelowOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `RuleBelowOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `RuleBelowRightIndent` | layout/visual attribute (name match 'indent') | `0` | 9/9 |
| `RuleBelowTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `RuleBelowWidth` | layout/visual attribute (name match 'width') | `ColumnWidth` | 9/9 |
| `ScaleAffectsLineHeight` | layout/visual attribute (name match 'scale') | `false` | 9/9 |
| `ShataiAdjustRotation` | layout/visual attribute (name match 'rotation') | `false` | 9/9 |
| `ShataiAdjustTsume` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `ShataiDegreeAngle` | layout/visual attribute (name match 'angle') | `4500` | 9/9 |
| `ShataiMagnification` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `SingleWordJustification` | layout/visual attribute (name match 'justif') | `FullyJustified` | 9/9 |
| `Skew` | layout/visual attribute (name match 'skew') | `0` | 9/9 |
| `SpaceBefore` | layout/visual attribute (name match 'space') | `0` | 9/9 |
| `SpanColumnMinSpaceAfter` | layout/visual attribute (name match 'space') | `0` | 9/9 |
| `SpanColumnMinSpaceBefore` | layout/visual attribute (name match 'space') | `0` | 9/9 |
| `SpanColumnType` | layout/visual attribute (name match 'column') | `SingleColumn` | 9/9 |
| `SplitColumnOutsideGutter` | layout/visual attribute (name match 'gutter') | `0` | 9/9 |
| `SplitDocument` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `StartParagraph` | unconsumed attribute on a converter-handled element | `Anywhere` | 9/9 |
| `StrikeThroughGapOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `StrikeThroughGapTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `StrikeThroughOffset` | layout/visual attribute (name match 'offset') | `-9999` | 9/9 |
| `StrikeThroughOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `StrikeThroughTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `StrikeThroughWeight` | layout/visual attribute (name match 'weight') | `-9999` | 9/9 |
| `StrikeThru` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `StrokeAlignment` | layout/visual attribute (name match 'stroke') | `OutsideAlignment` | 9/9 |
| `StrokeColor` | layout/visual attribute (name match 'color') | `Swatch/None` | 9/9 |
| `StrokeTint` | layout/visual attribute (name match 'stroke') | `-1` | 9/9 |
| `Tatechuyoko` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `TatechuyokoXOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `TatechuyokoYOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `Tracking` | layout/visual attribute (name match 'tracking') | `0` | 9/9 |
| `TrailingAki` | unconsumed attribute on a converter-handled element | `-1` | 9/9 |
| `Tsume` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `Underline` | layout/visual attribute (name match 'underline') | `false` | 9/9 |
| `UnderlineGapOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `UnderlineGapTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `UnderlineOffset` | layout/visual attribute (name match 'offset') | `-9999` | 9/9 |
| `UnderlineOverprint` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `UnderlineTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `UnderlineWeight` | layout/visual attribute (name match 'weight') | `-9999` | 9/9 |
| `VerticalScale` | layout/visual attribute (name match 'scale') | `100` | 9/9 |
| `Warichu` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `WarichuAlignment` | layout/visual attribute (name match 'align') | `Auto` | 9/9 |
| `WarichuCharsAfterBreak` | unconsumed attribute on a converter-handled element | `2` | 9/9 |
| `WarichuCharsBeforeBreak` | unconsumed attribute on a converter-handled element | `2` | 9/9 |
| `WarichuLineSpacing` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `WarichuLines` | unconsumed attribute on a converter-handled element | `2` | 9/9 |
| `WarichuSize` | layout/visual attribute (name match 'size') | `50` | 9/9 |
| `XOffsetDiacritic` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `YOffsetDiacritic` | layout/visual attribute (name match 'offset') | `0` | 9/9 |

#### `ParagraphStyleRange` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `DropcapDetail` | layout/visual attribute (name match 'cap') | `1` | 1/9 |
| `Hyphenation` | layout/visual attribute (name match 'hyphen') | `false` | 1/9 |
| `ParagraphShadingTint` | layout/visual attribute (name match 'tint') | `-1` | 9/9 |
| `TreatIdeographicSpaceAsSpace` | layout/visual attribute (name match 'space') | `true` | 1/9 |

#### `Polygon` (24)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedObjectStyle` | unconsumed attribute on a converter-handled element | `ObjectStyle/$ID/[None]` | 9/9 |
| `ContentType` | unconsumed attribute on a converter-handled element | `Unassigned` | 9/9 |
| `CornerRadius` | layout/visual attribute (name match 'corner') | `0.167` | 9/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `Nonprinting` | unconsumed attribute on a converter-handled element | `true` | 1/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `TopLeftCornerRadius` | layout/visual attribute (name match 'corner') | `0.167` | 9/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `Rectangle` (22)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `StrokeCornerAdjustment` | layout/visual attribute (name match 'stroke') | `DashesAndGaps` | 1/9 |
| `StrokeDashAndGap` | layout/visual attribute (name match 'stroke') | `12` | 1/9 |
| `StrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Dashed` | 1/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `Spread` (7)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AllowPageShuffle` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `FlattenerOverride` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `PageTransitionDirection` | unconsumed attribute on a converter-handled element | `NotApplicable` | 9/9 |
| `PageTransitionDuration` | unconsumed attribute on a converter-handled element | `Medium` | 9/9 |
| `PageTransitionType` | unconsumed attribute on a converter-handled element | `None` | 9/9 |
| `ShowMasterItems` | unconsumed attribute on a converter-handled element | `true` | 9/9 |
| `SpreadHidden` | layout/visual attribute (name match 'spread') | `false` | 9/9 |

#### `Story` (5)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedNamedGrid` | layout/visual attribute (name match 'grid') | `n` | 9/9 |
| `AppliedTOCStyle` | render-relevant element, effect unknown (conservative) | `n` | 9/9 |
| `IsEndnoteStory` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `TrackChanges` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `UserText` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |

#### `StoryPreference` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `OpticalMarginAlignment` | layout/visual attribute (name match 'margin') | `false` | 9/9 |
| `OpticalMarginSize` | layout/visual attribute (name match 'size') | `12` | 9/9 |

#### `Swatch` (2)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `SwatchCreatorID` | layout/visual attribute (name match 'swatch') | `7937` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `TableStyle` (116)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `BodyRegionCellStyle` | render-relevant element, effect unknown (conservative) | `CellStyle/$ID/[None]` | 9/9 |
| `BottomBorderStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `BottomBorderStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `BottomBorderStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `BottomBorderStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `BottomBorderStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `BottomBorderStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `BottomBorderStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `BottomBorderStrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 9/9 |
| `ClipContentToGraphicCell` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `ClipContentToTextCell` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `ColumnFillsPriority` | layout/visual attribute (name match 'fill') | `false` | 9/9 |
| `EndColumnFillColor` | layout/visual attribute (name match 'color') | `Swatch/None` | 9/9 |
| `EndColumnFillCount` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `EndColumnFillOverprint` | layout/visual attribute (name match 'fill') | `false` | 9/9 |
| `EndColumnFillTint` | layout/visual attribute (name match 'fill') | `100` | 9/9 |
| `EndColumnLineStyle` | layout/visual attribute (name match 'column') | `StrokeStyle/$ID/Solid` | 9/9 |
| `EndColumnStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `EndColumnStrokeCount` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `EndColumnStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `EndColumnStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `EndColumnStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `EndColumnStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `EndColumnStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `EndColumnStrokeWeight` | layout/visual attribute (name match 'stroke') | `0.25` | 9/9 |
| `EndRowFillColor` | layout/visual attribute (name match 'color') | `Swatch/None` | 9/9 |
| `EndRowFillCount` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `EndRowFillOverprint` | layout/visual attribute (name match 'fill') | `false` | 9/9 |
| `EndRowFillTint` | layout/visual attribute (name match 'fill') | `100` | 9/9 |
| `EndRowStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `EndRowStrokeCount` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `EndRowStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `EndRowStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `EndRowStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `EndRowStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `EndRowStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `EndRowStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `EndRowStrokeWeight` | layout/visual attribute (name match 'stroke') | `0.25` | 9/9 |
| `ExtendedKeyboardShortcut` | render-relevant element, effect unknown (conservative) | `0 0 0` | 9/9 |
| `FooterRegionCellStyle` | render-relevant element, effect unknown (conservative) | `n` | 9/9 |
| `FooterRegionSameAsBodyRegion` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |
| `GraphicBottomInset` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `GraphicLeftInset` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `GraphicRightInset` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `GraphicTopInset` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `HeaderRegionCellStyle` | render-relevant element, effect unknown (conservative) | `n` | 9/9 |
| `HeaderRegionSameAsBodyRegion` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |
| `LeftBorderStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `LeftBorderStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `LeftBorderStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `LeftBorderStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `LeftBorderStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `LeftBorderStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `LeftBorderStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `LeftBorderStrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 9/9 |
| `LeftColumnRegionCellStyle` | layout/visual attribute (name match 'column') | `n` | 9/9 |
| `LeftColumnRegionSameAsBodyRegion` | layout/visual attribute (name match 'column') | `true` | 9/9 |
| `RightBorderStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `RightBorderStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `RightBorderStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `RightBorderStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `RightBorderStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `RightBorderStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `RightBorderStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `RightBorderStrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 9/9 |
| `RightColumnRegionCellStyle` | layout/visual attribute (name match 'column') | `n` | 9/9 |
| `RightColumnRegionSameAsBodyRegion` | layout/visual attribute (name match 'column') | `true` | 9/9 |
| `SkipFirstAlternatingFillColumns` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `SkipFirstAlternatingFillRows` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `SkipFirstAlternatingStrokeColumns` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `SkipFirstAlternatingStrokeRows` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `SkipLastAlternatingFillColumns` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `SkipLastAlternatingFillRows` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `SkipLastAlternatingStrokeColumns` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `SkipLastAlternatingStrokeRows` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `SpaceAfter` | layout/visual attribute (name match 'space') | `-4` | 9/9 |
| `SpaceBefore` | layout/visual attribute (name match 'space') | `4` | 9/9 |
| `StartColumnFillColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `StartColumnFillCount` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `StartColumnFillOverprint` | layout/visual attribute (name match 'fill') | `false` | 9/9 |
| `StartColumnFillTint` | layout/visual attribute (name match 'fill') | `20` | 9/9 |
| `StartColumnStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `StartColumnStrokeCount` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `StartColumnStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `StartColumnStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `StartColumnStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `StartColumnStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `StartColumnStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `StartColumnStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `StartColumnStrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 9/9 |
| `StartRowFillColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `StartRowFillCount` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `StartRowFillOverprint` | layout/visual attribute (name match 'fill') | `false` | 9/9 |
| `StartRowFillTint` | layout/visual attribute (name match 'fill') | `20` | 9/9 |
| `StartRowStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `StartRowStrokeCount` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `StartRowStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `StartRowStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `StartRowStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `StartRowStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `StartRowStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `StartRowStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `StartRowStrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 9/9 |
| `StrokeOrder` | layout/visual attribute (name match 'stroke') | `BestJoins` | 9/9 |
| `TextBottomInset` | layout/visual attribute (name match 'inset') | `4` | 9/9 |
| `TextLeftInset` | layout/visual attribute (name match 'inset') | `4` | 9/9 |
| `TextRightInset` | layout/visual attribute (name match 'inset') | `4` | 9/9 |
| `TextTopInset` | layout/visual attribute (name match 'inset') | `4` | 9/9 |
| `TopBorderStrokeColor` | layout/visual attribute (name match 'color') | `Color/Black` | 9/9 |
| `TopBorderStrokeGapColor` | layout/visual attribute (name match 'color') | `Color/Paper` | 9/9 |
| `TopBorderStrokeGapOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `TopBorderStrokeGapTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `TopBorderStrokeOverprint` | layout/visual attribute (name match 'stroke') | `false` | 9/9 |
| `TopBorderStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `TopBorderStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `TopBorderStrokeWeight` | layout/visual attribute (name match 'stroke') | `1` | 9/9 |

#### `TextFrame` (20)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ContentType` | unconsumed attribute on a converter-handled element | `TextType` | 9/9 |
| `FlexItemHeightMode` | layout/visual attribute (name match 'height') | `FlexFixed` | 9/9 |
| `FlexItemWidthMode` | layout/visual attribute (name match 'width') | `FlexFixed` | 9/9 |
| `GradientFillAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteAngle` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillHiliteLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillLength` | layout/visual attribute (name match 'fill') | `0` | 9/9 |
| `GradientFillStart` | layout/visual attribute (name match 'fill') | `0 0` | 9/9 |
| `GradientStrokeAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteAngle` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeHiliteLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeLength` | layout/visual attribute (name match 'stroke') | `0` | 9/9 |
| `GradientStrokeStart` | layout/visual attribute (name match 'stroke') | `0 0` | 9/9 |
| `HorizontalLayoutConstraints` | layout/visual attribute (name match 'horizontal') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `LastUpdatedInterfaceChangeCount` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `LocalDisplaySetting` | unconsumed attribute on a converter-handled element | `Default` | 9/9 |
| `Locked` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `OverriddenPageItemProps` | unconsumed attribute on a converter-handled element | `(empty)` | 9/9 |
| `VerticalLayoutConstraints` | layout/visual attribute (name match 'vertical') | `FlexibleDimension FixedDimension FlexibleDimension` | 9/9 |
| `Visible` | layout/visual attribute (name match 'visible') | `true` | 9/9 |

#### `TextFrameFootnoteOptionsObject` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `EnableOverrides` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `MinimumSpacingOption` | render-relevant element, effect unknown (conservative) | `12` | 9/9 |
| `SpaceBetweenFootnotes` | layout/visual attribute (name match 'space') | `6` | 9/9 |
| `SpanFootnotesAcross` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |

#### `TextFramePreference` (27)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AutoSizingReferencePoint` | layout/visual attribute (name match 'point') | `CenterPoint` | 9/9 |
| `AutoSizingType` | render-relevant element, effect unknown (conservative) | `Off` | 9/9 |
| `ColumnRuleBottomInset` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `ColumnRuleInsetChainOverride` | layout/visual attribute (name match 'inset') | `true` | 9/9 |
| `ColumnRuleOffset` | layout/visual attribute (name match 'offset') | `0` | 9/9 |
| `ColumnRuleOverprintOverride` | layout/visual attribute (name match 'overprint') | `false` | 9/9 |
| `ColumnRuleOverride` | layout/visual attribute (name match 'column') | `false` | 9/9 |
| `ColumnRuleStrokeTint` | layout/visual attribute (name match 'stroke') | `100` | 9/9 |
| `ColumnRuleStrokeType` | layout/visual attribute (name match 'stroke') | `StrokeStyle/$ID/Solid` | 9/9 |
| `ColumnRuleTopInset` | layout/visual attribute (name match 'inset') | `0` | 9/9 |
| `FirstBaselineOffset` | layout/visual attribute (name match 'baseline') | `AscentOffset` | 9/9 |
| `FootnotesEnableOverrides` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `FootnotesMinimumSpacing` | render-relevant element, effect unknown (conservative) | `12` | 9/9 |
| `FootnotesSpaceBetween` | layout/visual attribute (name match 'space') | `6` | 9/9 |
| `FootnotesSpanAcrossColumns` | layout/visual attribute (name match 'column') | `false` | 9/9 |
| `IgnoreWrap` | layout/visual attribute (name match 'wrap') | `false` | 9/9 |
| `MinimumFirstBaselineOffset` | layout/visual attribute (name match 'baseline') | `0` | 9/9 |
| `MinimumHeightForAutoSizing` | layout/visual attribute (name match 'height') | `0` | 9/9 |
| `MinimumWidthForAutoSizing` | layout/visual attribute (name match 'width') | `0` | 9/9 |
| `TextColumnMaxWidth` | layout/visual attribute (name match 'column') | `0` | 9/9 |
| `UseFixedColumnWidth` | layout/visual attribute (name match 'column') | `false` | 9/9 |
| `UseFlexibleColumnWidth` | layout/visual attribute (name match 'column') | `false` | 9/9 |
| `UseMinimumHeightForAutoSizing` | layout/visual attribute (name match 'height') | `false` | 9/9 |
| `UseMinimumWidthForAutoSizing` | layout/visual attribute (name match 'width') | `false` | 9/9 |
| `UseNoLineBreaksForAutoSizing` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `VerticalBalanceColumns` | layout/visual attribute (name match 'column') | `false` | 9/9 |
| `VerticalThreshold` | layout/visual attribute (name match 'vertical') | `0` | 9/9 |

#### `TextWrapOffset` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `Bottom` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `Left` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `Right` | unconsumed attribute on a converter-handled element | `0` | 9/9 |
| `Top` | unconsumed attribute on a converter-handled element | `0` | 9/9 |

#### `TextWrapPreference` (4)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `ApplyToMasterPageOnly` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `Inverse` | unconsumed attribute on a converter-handled element | `false` | 9/9 |
| `TextWrapMode` | layout/visual attribute (name match 'wrap') | `None` | 9/9 |
| `TextWrapSide` | layout/visual attribute (name match 'wrap') | `BothSides` | 9/9 |

#### `TransformAttributeOption` (3)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `TransformAttrLeftReference` | layout/visual attribute (name match 'transform') | `PageEdgeReference` | 9/9 |
| `TransformAttrRefAnchorPoint` | layout/visual attribute (name match 'transform') | `TopLeftAnchor` | 9/9 |
| `TransformAttrTopReference` | layout/visual attribute (name match 'transform') | `PageEdgeReference` | 9/9 |

#### `XmlStory` (5)

| Attribute | Reason | Observed values | IDMLs |
|---|---|---|---|
| `AppliedNamedGrid` | layout/visual attribute (name match 'grid') | `n` | 9/9 |
| `AppliedTOCStyle` | render-relevant element, effect unknown (conservative) | `n` | 9/9 |
| `IsEndnoteStory` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `TrackChanges` | render-relevant element, effect unknown (conservative) | `false` | 9/9 |
| `UserText` | render-relevant element, effect unknown (conservative) | `true` | 9/9 |

## Ignorable unconsumed attributes (summary)

Internal IDs, name-keyed style references, XMP/export/editorial metadata, inert defaults -- no layout/visual/typographic effect.

| Category | Count |
|---|---|
| editing-environment / new-object-default / metadata element | 673 |
| metadata/export/editorial element | 542 |
| internal id / schema / value-type annotation | 258 |

Ignorable attributes span **241** element tags. Top tags by ignorable-attr count:

| Element tag | Ignorable attrs |
|---|---|
| `TextDefault` | 276 |
| `PrintPreference` | 91 |
| `PrintBookletPrintPreference` | 86 |
| `EPubExportPreference` | 67 |
| `HTMLExportPreference` | 39 |
| `TextPreference` | 34 |
| `EPubFixedLayoutExportPreference` | 33 |
| `PageItemDefault` | 33 |
| `FootnoteOption` | 31 |
| `ObjectExportOption` | 27 |
| `IndexOptions` | 22 |
| `Document` | 18 |
| `DocumentPreference` | 18 |
| `ViewPreference` | 17 |
| `BevelAndEmbossSetting` | 16 |

## Sanity check

- `ParagraphStyle/SpaceBefore`: present=True, flagged significant=True -- **OK**
- `ParagraphStyle/SpaceAfter`: present=True, flagged significant=True -- **OK**
