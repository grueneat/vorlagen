# Scribus 1.6.x SLA File Format — Engineering Reference

Research date: 2026-05-04
Scope: depth survey for building tooling that reads, writes, edits, validates, and AI-augments `.sla` template files. Primary sources: Scribus master branch (`github.com/scribusproject/scribus`, master = 1.7.x dev with the canonical 1.5.0 reader/writer that 1.6.x also uses), wiki references, ScribusGenerator, PyScribus, justsolve archive team. The official wiki (`wiki.scribus.net`) is currently behind an Anubis challenge that blocks server-side fetches; canonical truth therefore lives in source.

The single most important takeaway: **the file format has no published schema. The source code is the spec.** The two files that matter are:

- `scribus/plugins/fileloader/scribus150format/scribus150format_save.cpp` — writer (~3000 LOC). This is what 1.5.x AND 1.6.x produce.
- `scribus/plugins/fileloader/scribus150format/scribus150format.cpp` — reader (~7600 LOC).
- `scribus/pageitem.h` — `ItemType` and `ItemFrameType` enums.
- `scribus/units.h` — internal unit ratios.
- 1.7.x ships a parallel `scribus171format/` plugin, currently a fork of the 150 plugin (issue 17474).

---

## 1. Top-level XML structure

The root is `<SCRIBUSUTF8NEW>` (older variants `SCRIBUSUTF8` 1.3.4–1.4 and `SCRIBUS` 1.2). Hierarchy as written by `scribus150format_save.cpp`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SCRIBUSUTF8NEW Version="1.5.8">          <!-- 150 plugin always writes 1.5.8 -->
  <DOCUMENT ANZPAGES="1" PAGEWIDTH="595.275590551181" PAGEHEIGHT="841.88976377..." ...>
    <CheckProfile .../>            <!-- preflight profiles, multiple -->
    <COLOR NAME="Black" SPACE="CMYK" C="0" M="0" Y="0" K="100"/>
    <Gradient Name="..." Ext="...">
      <CSTOP RAMP="0" NAME="Black" SHADE="100" TRANS="1"/>
    </Gradient>
    <HYPHEN><EXCEPTION WORD="..." HYPHENATED="..."/></HYPHEN>
    <STYLE NAME="Default Paragraph Style" ALIGN="0" LINESP="15" .../>
    <CHARSTYLE CNAME="..." FONT="..." FONTSIZE="12"/>
    <TableStyle NAME="..."/>
    <CellStyle NAME="..."/>
    <LAYERS NUMMER="0" LEVEL="0" NAME="Background" SICHTBAR="1" .../>
    <Printer .../>
    <PDF .../>
      <LPIline Color="..." Frequency="..." Angle="..." SpotFunction="..."/>
      <Fonts Name="..."/>
      <Subset Name="..."/>
      <Effekte pageEffectDuration="..." .../>
    <DocItemAttributes><ItemAttribute Name=".." Type=".." Value=".." .../></DocItemAttributes>
    <TablesOfContents><TableOfContents .../></TablesOfContents>
    <Sections><Section Number="0" Name="0" From="0" To="0" Type="Type_1_2_3" Start="1" .../></Sections>
    <Marks/>
    <NotesStyles/>
    <NotesFrames/>
    <Notes/>
    <PageSets>
      <Set Name="Single Page" FirstPage="0" Rows="1" Columns="1">
        <PageNames Name="..."/>
      </Set>
    </PageSets>
    <Pattern Name="..." width="..." height="...">
      <PatternItem .../>     <!-- nested page items -->
    </Pattern>

    <MASTERPAGE PAGEXPOS="..." PAGEYPOS="..." PAGEWIDTH="..." PAGEHEIGHT="..."
                BORDERLEFT="..." NUM="0" NAM="Normal" MNAM="" Size="A4"
                Orientation="0" LEFT="0" PRESET="0" .../>
    <PAGE PAGEXPOS="..." PAGEYPOS="..." NUM="0" NAM="" MNAM="Normal" .../>

    <FRAMEOBJECT InID="..." XPOS="..." YPOS="..." PTYPE="4" .../>   <!-- inline frames -->
    <MASTEROBJECT XPOS="..." YPOS="..." PTYPE="..." OnMasterPage="Normal" .../>
    <PAGEOBJECT  XPOS="..." YPOS="..." PTYPE="4" WIDTH="..." HEIGHT="..." OwnPage="0" ItemID="..." ANNAME="..." NEXTITEM="-1" BACKITEM="-1" LAYER="0" ...>
      <StoryText>
        <DefaultStyle PARENT="Default Paragraph Style"/>
        <ITEXT FONT="Arial Regular" FONTSIZE="12" CH="Hello world"/>
        <para PARENT="Heading 1"/>
        <ITEXT CH="More text"/>
        <trail/>
      </StoryText>
    </PAGEOBJECT>
  </DOCUMENT>
</SCRIBUSUTF8NEW>
```

Element order matters in practice (some loaders are strict). `WritePages` is called twice (master, then doc), then `WriteObjects` four times in the order `Frame`→`Master`→`Page`→`(pattern items already inline)`. Element relationships:

- **SCRIBUSUTF8NEW** — root, holds `Version` attribute. Writer also produces `<SCRIBUSELEMUTF8>` for clipboard fragments and `<ScribusStory>` for story exports, and `<SCRIBUSCOLORS>` for palette files. Treat them as different schemas; tooling should reject anything that is not `SCRIBUSUTF8NEW` for documents.
- **DOCUMENT** — single child. Carries 100+ attributes covering page geometry, type prefs, CMS, hyphenation, autosave, scratch, snap, baseline.
- **MASTERPAGE / PAGE** — same attribute set; differ only in element name.
- **PAGEOBJECT / MASTEROBJECT / FRAMEOBJECT / PatternItem / ITEM** — all the same shape. Difference is the container they live in. PAGEOBJECTs are siblings of PAGE elements directly under DOCUMENT, NOT children of PAGE. Linkage to a page is via the `OwnPage` attribute (zero-based page index).
- **STYLE** = paragraph style, **CHARSTYLE** = character style. Both can have `PARENT`. Inside `<StoryText>`, `<DefaultStyle>` and `<para>`/`<trail>` carry inline paragraph-style attribute overrides.

## 2. PAGEOBJECT PTYPE — full enum table

From `scribus/pageitem.h`, `enum ItemType` (lines ~171-191):

| PTYPE | Name | Notes |
|---|---|---|
| 1 | ItemType1 | reserved/legacy |
| 2 | ImageFrame | `PFILE` references the image |
| 3 | ItemType3 | reserved/legacy |
| 4 | TextFrame | StoryText child |
| 5 | Line | uses `WIDTH`+rotation, no `HEIGHT` semantics |
| 6 | Polygon | closed |
| 7 | PolyLine | open |
| 8 | PathText | text on a path (StoryText + path) |
| 9 | LatexFrame | render frame (LaTeX/gnuplot/POV) |
| 10 | OSGFrame | 3D model (PRC inside PDF) |
| 11 | Symbol | Scrapbook symbol instance, references Pattern |
| 12 | Group | container for grouped items |
| 13 | RegularPolygon | `polyCorners`/`polyFactor` driven |
| 14 | Arc | `arcStartAngle`/`arcSweepAngle` |
| 15 | Spiral | `spiralStartAngle`/`spiralEndAngle`/`spiralFactor` |
| 16 | Table | uses `<TableData>` + `<Cell>` children |
| 17 | NoteFrame | auto-generated endnote/footnote frame |
| 99 | Multiple | UI-only sentinel, never written to disk |

Companion enum **FRTYPE** (`enum ItemFrameType`, pageitem.h ~217): `-1`=Unspecified, `0`=Rectangle, `1`=Ellipse, `2`=Round, `3`=Other (custom path; the `path=` and `copath=` SVG-like data describe the actual shape).

## 3. Coordinate system, units, rotation, bleed

**Internal storage is always points (1pt = 1/72 inch) regardless of the document's `UNITS` attribute.** `UNITS` only controls UI display and ruler. A4 width therefore serializes as `595.275590551181` (210 mm × 72 / 25.4). `UNITS` enum (`scribus/units.h`):

```
SC_PT/SC_POINTS=0  SC_MM=1  SC_IN=2  SC_PICAS=3  SC_CM=4  SC_CICERO=5  SC_DEG=6  SC_PERCENT=7
```

Page geometry on `<PAGE>` / `<MASTERPAGE>`:
- `PAGEXPOS`, `PAGEYPOS` — page origin in the document scratch space (a vast multi-page coordinate space, not page-local).
- `PAGEWIDTH`, `PAGEHEIGHT` — trim size in points.
- `BORDERLEFT`/`RIGHT`/`TOP`/`BOTTOM` — margins.

Page-object geometry on `<PAGEOBJECT>`:
- `XPOS`, `YPOS` — **scratch-space coordinates, NOT page-relative**. Effective page-relative position = `XPOS − PAGEXPOS`, `YPOS − PAGEYPOS`. `OwnPage` tells you which page index it belongs to. (Exception: when written to clipboard fragments — `ItemSelectionElements` — coordinates ARE page-relative.)
- `WIDTH`, `HEIGHT` — bounding box in points.
- `ROT` — degrees, clockwise. Pivot is the top-left corner of the unrotated bbox at `(XPOS,YPOS)`. Omitted when 0.
- `gXpos/gYpos/gWidth/gHeight` — group-relative geometry, used when item is inside a Group.
- `path=` and `copath=` — SVG-ish path data ("M x y L x y …Z") describing the shape and the clip path; recomputed automatically from WIDTH/HEIGHT/FRTYPE for default rectangles/ellipses, but stored verbatim for FRTYPE=3 (custom).

Bleed lives on DOCUMENT: `BleedTop`, `BleedLeft`, `BleedRight`, `BleedBottom` (points). The Printer block has a separate set of bleeds for output.

## 4. Text storage model

Text lives under `<StoryText>` inside the owning `<PAGEOBJECT>` (or `<MASTEROBJECT>`). The writer in `Scribus150Format::writeITEXTs` (save.cpp:1812-1949) emits a flat sequence of typed elements that, when concatenated in order, reconstruct the story:

- `<DefaultStyle PARENT="…" …/>` — the story-level default paragraph style (only in StoryText).
- `<ITEXT FONT=… FONTSIZE=… FCOLOR=… CH="…"/>` — a run of characters with a single CharStyle. A new ITEXT is started whenever the CharStyle changes or a special character interrupts.
- `<para …/>` — paragraph break. Carries the paragraph style for the paragraph that just ENDED.
- `<trail …/>` — the paragraph style for trailing chars after the last ` ` (story does not end with a paragraph break). Always emitted in that case.
- `<tab/>`, `<breakline/>` (line break, `U+2028`), `<breakcol/>`, `<breakframe/>`, `<nbhyphen/>`, `<nbspace/>`, `<zwspace/>`, `<zwnbspace/>` — control characters, each may carry a CharStyle.
- `<var name="pgno"/>` and `<var name="pgco"/>` — page number / page count placeholder.
- `<MARK label=… type=…/>` — index marks, footnote/endnote anchors, variable references.
- `<ITEXT Unicode="9999" .../>` (no CH) — fallback for any control char Scribus cannot represent literally; soft hyphens are emitted by duplicating `­` inside CH (see `textWithSoftHyphens`).

CharStyle attributes (`putCStyle`, save.cpp:933-989) — only written when not inheriting:
`CPARENT, FONT, FONTSIZE, FONTFEATURES, FEATURES, FCOLOR, FSHADE, SCOLOR, SSHADE, BGCOLOR, BGSHADE, TXTSHX, TXTSHY, TXTOUT, TXTULP, TXTULW, TXTSTP, TXTSTW, SCALEH, SCALEV, BASEO, KERN, wordTrack, LANGUAGE, HyphenChar, HyphenWordMin, SHORTCUT`. `FEATURES` is a space-joined list of flags like `inherit underlinewords smallcaps superscript`.

ParagraphStyle attributes (`putPStyle`, save.cpp:807-905):
`NAME, PARENT, DefaultStyle, ALIGN, DIRECTION, LINESPMode, LINESP, INDENT, RMARGIN, FIRST, VOR (gap before), NACH (gap after), DROP, DROPLIN, Bullet, BulletStr, Numeration, Numeration*, OpticalMargins, HyphenConsecutiveLines, HyphenationMode, MinWordTrack, MinGlyphShrink, MaxGlyphExtend, KeepLinesStart, KeepLinesEnd, KeepWithNext, KeepTogether, BCOLOR, BSHADE, PSHORTCUT`, plus `<Tabs Type Pos Fill/>` children for tab stops, plus all CharStyle attributes for the paragraph's own char style (flat).

**Inheritance**: `PARENT` is the name of the parent style; resolution is "value missing on this style → inherit from parent → fall back to Default…". The `is*Inherit` flag pattern in code is precisely why most attributes are conditionally written: a missing attribute IS the signal of inheritance, NOT an explicit empty value. Tooling that round-trips must respect this — emitting unchanged inherited values forces them to override and silently changes layout.

## 5. Image frames

`PAGEOBJECT PTYPE="2"` (and the image-bearing variants `PathText`, `OSGFrame`, `LatexFrame`):

- `PFILE` — primary path. Written via `Path2Relative(item->Pfile, baseDir)` (save.cpp:2845): if the SLA's directory is a parent of the image, a relative path is emitted, otherwise an absolute one. Tooling that moves SLAs around MUST rewrite `PFILE` or copy assets relative-aware.
- `PFILE2`, `PFILE3` — auxiliary paths (used by some plugins, e.g. mask/preview).
- `PRFILE` — embedded ICC color profile filename for the image.
- `IRENDER` — rendering intent (default 1, omitted when 1).
- `EPROF` — embedded profile name pulled out of the image at import.
- `EMBEDDED` — `0` if `UseEmbedded` is false (do not honor in-image profile).
- `LOCALSCX/LOCALSCY` — image-in-frame scale (1.0 = native).
- `LOCALX/LOCALY` — image offset within the frame in points.
- `LOCALROT` — image rotation inside the frame.
- `RATIO` — keep aspect.
- `SCALETYPE` — 0=free, 1=preserve aspect to frame.
- `PICART` — show image (1) vs. only frame (0).
- `COMPRESSIONMETHOD` / `COMPRESSIONQUALITY` — only when overridden.
- `Pagenumber` — page index for multi-page images (PDF/PSD).
- `ImageClip` — name of the embedded clipping path used.
- `ImageRes` — low-res preview type.

**Inline (embedded) images**: when `item->isInlineImage` is true, `PFILE=""`, `isInlineImage="1"`, `inlineImageExt="png"` (or whatever), and `ImageData="<base64 of qCompress(file)>"` (save.cpp:2832-2843). `qCompress` is Qt's wrapper around zlib with a 4-byte big-endian length prefix prepended — not a raw deflate stream. Round-tripping requires Qt-compatible decompress.

## 6. Master pages

- `<MASTERPAGE>` carries the same attributes as `<PAGE>` plus `NAM="<master name>"` (the name PageItem rows reference).
- A `<PAGE>` references its master via `MNAM="<master name>"` (empty string = no master).
- Master content lives in `<MASTEROBJECT>` siblings, identified by `OnMasterPage="<master name>"` plus their own `OwnPage` index in MasterPages.
- `LEFT` on PAGE/MASTERPAGE is the page-position-in-spread (0=left, 1=right, …) governed by `<Set>` in `<PageSets>`.
- Pages know nothing about their objects directly — there is no parent/child XML link; the engine walks all `MASTEROBJECT`s and matches by `OnMasterPage`. Tooling that rearranges pages must rewrite `OwnPage` indices on every PAGEOBJECT.

## 7. Versioning & compat

There are five format eras (per justsolve.archiveteam.org/wiki/Scribus): 1.2.x, 1.3-1.3.3.x, 1.3.4-1.4, 1.5-1.6, 1.7-1.8.

- **1.5/1.6 share the writer plugin (`scribus150format`)**. The 150 writer hard-codes `Version="1.5.8"` in its header (`scribus150format.h:253`: `QString saveOldVersion {"1.5.8"};`). Both 1.5.x and 1.6.x produce strings starting with `1.5.` or `1.6.` (the loader regex accepts either: `Version="1.5.[0-9]"|Version="1.6.[0-9]"`, save.cpp:151). 1.6.x uses the same plugin with a different runtime version string.
- **1.7+** has its own `scribus171format/` plugin (issue 17474). It emits `Version=ScribusAPI::getVersion()` (i.e. live runtime version) and writes a superset format that 1.5/1.6 cannot read. 1.7 can save back to 1.5–1.6 format using the older plugin.
- **1.4 → 1.5 was the breaking change**: 1.4 readers cannot open 1.5+ at all. There is no automatic downgrade. ScribusGenerator and most tooling target 1.5 specifically because it is the broadest stable target.
- **Forward compat is brittle**: unknown elements/attributes are silently dropped on save. So if 1.7 introduces a new element, opening + saving in 1.6 strips it permanently.

For a 1.6.x-targeted tool, treat **1.5.0 plugin source as the spec** and write `Version="1.6.x"` (any 1.6.y string passes the regex).

## 8. Gotchas for programmatic editing

- **Floats**: Scribus uses Qt's default `QString::number(double)` — about 15 significant digits, no fixed precision. You will see values like `595.275590551181`. Don't normalize; the loader is tolerant but reviewers comparing diffs will hate it. Preserve original strings where possible.
- **Inheritance is implicit**: if your editor blindly emits every attribute (e.g. by reading into a struct then writing the struct), you BREAK style inheritance. CharStyle/ParagraphStyle attributes must only be written when they actually differ from the parent. Same for many PAGEOBJECT attributes (`SHADE`, `SHADE2`, `PLINEART`, `RADRECT`, `ROT` — all only written when non-default).
- **Auto-recomputed fields on next save**:
  - `path=` / `copath=` — overwritten from FRTYPE+WIDTH+HEIGHT for FRTYPE 0/1/2.
  - `gXpos/gYpos/gWidth/gHeight` — recomputed from group bbox.
  - `NEXTITEM`/`BACKITEM` — recomputed by walking `qHash(item) & 0x7FFFFFFF`. `ItemID` is also `qHash(item) & 0x7FFFFFFF`, NOT a stable persistent identifier — it changes on reload because qHash uses memory addresses for non-string types in some paths.
- **Item linkage by ItemID** (text-frame chains, welds): if you renumber `ItemID`s you MUST update every `NEXTITEM`/`BACKITEM`/`WeldSource`/`WeldID` in lockstep. There is no symbolic linking.
- **`OwnPage`** must point to a valid page index after any page reordering.
- **No XML signing**, no checksum, no integrity field. The file is a plain UTF-8 XML stream.
- **Not strictly XML-valid** in some 1.4-era files (per multiple sources): mismatched entity escaping in older versions. 1.5+ uses Qt's `QXmlStreamWriter` which is well-formed.
- **Soft hyphens** appear inline in `CH` as the Unicode character (U+00AD). To represent a literal SHY in source text, the writer DUPLICATES it (`textWithSoftHyphens`, save.cpp:1779). Editors that strip control chars will eat them.
- **`AUTOTEXT="1"`** on DOCUMENT means automatic text-frame chains are in use; do not casually delete linked frames.
- **Locale**: numbers always use `.` as decimal separator (Qt's QXmlStreamWriter uses C locale). Do not use locale-aware parsers.

## 9. Validation / canonical reference

There is **no published XSD or RNG schema**. A 2012 GSoC project ("GSoC 2012 Scribus XML File Format") proposed a Relax-NG-based modular replacement; it was never merged. The closest public spec attempts are:
- Wiki page `File_Format_Specification_for_Scribus_1.4` and `..._1.5` (currently behind Anubis but indexed in caches).
- PyScribus (`framagit.org/etnadji/pyscribus`) — Python library that implements partial parse/emit; treats SLA via dataclass-per-element. Now inactive (last release 2023-08).
- ScribusGenerator (`berteh/ScribusGenerator`) — production-grade template-substitution tool, processes the XML with regex+ElementTree. Useful as a real-world parser reference.

For correctness, validate by **round-tripping through Scribus headless** (`scribus -g -py …` or `sla2pdf`) and diffing AST vs. on-disk. The loader is the only authority.

Canonical source paths inside `scribusproject/scribus`:

| Concern | Path |
|---|---|
| ItemType / FRTYPE enums | `scribus/pageitem.h` (~ln 171-225) |
| Writer (1.5/1.6) | `scribus/plugins/fileloader/scribus150format/scribus150format_save.cpp` |
| Reader (1.5/1.6) | `scribus/plugins/fileloader/scribus150format/scribus150format.cpp` |
| Writer (1.7+) | `scribus/plugins/fileloader/scribus171format/scribus171format_save.cpp` |
| Units | `scribus/units.h` (`enum scUnit`) |
| Master pages | `scribus/scpage.h`, `scribus/scribusdoc.cpp` |
| StoryText | `scribus/text/storytext.cpp` |
| 1.4 reader (legacy) | `scribus/plugins/fileloader/scribus134format/` |

## 10. Compressed / legacy variants

- **`.sla`** — uncompressed UTF-8 XML (current default).
- **`.sla.gz`** — gzip-compressed `.sla`. Detected by file extension only (`fileName.right(2) == "gz"`, save.cpp:132). Stream wrapped in `QtIOCompressor` (a Qt zlib wrapper) with `GzipFormat`. It's a regular gzip file — `gunzip` works.
- **`.scd`** — legacy Scribus 1.0/1.2-era document. Same SLA-style XML but with an older root element (`SCRIBUS` and earlier). The 150 loader's `fmt.fileExtensions` list still claims it (`"sla" << "sla.gz" << "scd" << "scd.gz"`, load.cpp:123) but actual support comes from older format plugins (`scribus12format`, `scribus134format`).
- **`.scd.gz`** — gzip variant of the above.
- **No proprietary container, no chunk format, no Office-style ZIP**: a single file, optionally gzipped. Embedded images are inlined as base64-of-qCompress inside the XML, so SLAs can be self-contained but get large.

---

## Quick reference: minimal valid 1.6 SLA template skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SCRIBUSUTF8NEW Version="1.6.1">
 <DOCUMENT ANZPAGES="1" PAGEWIDTH="595.275590551181" PAGEHEIGHT="841.889763779527"
           BORDERLEFT="40" BORDERRIGHT="40" BORDERTOP="40" BORDERBOTTOM="40"
           BleedTop="0" BleedLeft="0" BleedRight="0" BleedBottom="0"
           ORIENTATION="0" PAGESIZE="A4" UNITS="0" FIRSTNUM="1" BOOK="0"
           DFONT="Arial Regular" DSIZE="12" DCOL="1" DGAP="0" GROUPC="1" ALAYER="0">
  <COLOR NAME="Black" SPACE="CMYK" C="0" M="0" Y="0" K="100"/>
  <COLOR NAME="None"  SPACE="RGB"  R="255" G="255" B="255"/>
  <STYLE NAME="Default Paragraph Style" DefaultStyle="1" ALIGN="0" LINESPMode="0" LINESP="15"/>
  <CHARSTYLE CNAME="Default Character Style" DefaultStyle="1" FONT="Arial Regular" FONTSIZE="12"/>
  <LAYERS NUMMER="0" LEVEL="0" NAME="Background" SICHTBAR="1" DRUCKEN="1" EDIT="1" SELECT="1" FLOW="1" TRANS="1" BLEND="0" OUTL="0" LAYERC="#000000"/>
  <PageSets><Set Name="Single Page" FirstPage="0" Rows="1" Columns="1"><PageNames Name="Page"/></Set></PageSets>
  <Sections><Section Number="0" Name="0" From="0" To="0" Type="Type_1_2_3" Start="1" Reversed="0" Active="1" FillChar="0" FieldWidth="0"/></Sections>
  <PAGE PAGEXPOS="100" PAGEYPOS="20" PAGEWIDTH="595.28" PAGEHEIGHT="841.89"
        BORDERLEFT="40" BORDERRIGHT="40" BORDERTOP="40" BORDERBOTTOM="40"
        NUM="0" NAM="" MNAM="Normal" Size="A4" Orientation="0" LEFT="0" PRESET="0"/>
  <MASTERPAGE PAGEXPOS="100" PAGEYPOS="20" PAGEWIDTH="595.28" PAGEHEIGHT="841.89"
              BORDERLEFT="40" BORDERRIGHT="40" BORDERTOP="40" BORDERBOTTOM="40"
              NUM="0" NAM="Normal" MNAM="" Size="A4" Orientation="0" LEFT="0" PRESET="0"/>
  <PAGEOBJECT XPOS="140" YPOS="60" PTYPE="4" WIDTH="400" HEIGHT="100"
              FRTYPE="0" CLIPEDIT="0" PWIDTH="0" PCOLOR="None" PCOLOR2="None"
              OwnPage="0" ItemID="1" ANNAME="title" NEXTITEM="-1" BACKITEM="-1" LAYER="0">
   <StoryText>
    <DefaultStyle PARENT="Default Paragraph Style"/>
    <ITEXT FONT="Arial Regular" FONTSIZE="24" CH="%VAR_title%"/>
    <trail/>
   </StoryText>
  </PAGEOBJECT>
 </DOCUMENT>
</SCRIBUSUTF8NEW>
```

That is a complete, openable 1.6 template. Variables (`%VAR_*%`) are ScribusGenerator convention, not part of the format itself — Scribus stores them as literal text inside `CH`.

## Recommended tooling architecture (informational)

1. **Parser**: `lxml.etree` with `remove_blank_text=False`, preserve attribute order and original number strings (use `lxml`'s default — it preserves text). Do NOT round-trip via Python's stdlib `xml.etree` — it loses attribute order in older versions and reorders namespaces.
2. **Model**: typed dataclasses per element (PageObject, Story, Run, Style). Track which attributes were present in source vs. defaulted; only re-emit the present ones to preserve inheritance semantics.
3. **Validation**: keep a hand-rolled schema derived from `scribus150format_save.cpp` (it is structurally exhaustive). PyScribus's class hierarchy is a reasonable starting point.
4. **Conformance test**: round-trip through real Scribus with `scribus -g -py - <<<'…'` or `sla2pdf` to verify the file still renders identically.
5. **Cost-aware strategy**: most edits (text substitution, color swap) only touch leaf attributes; LLM doesn't need to see the full XML — extract a structural index plus the addressable runs.
