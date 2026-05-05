# Scribus 1.6 Multi-Page Documents and Master Pages

Research date: 2026-05-04
Scope: structural rules for multi-page SLA files with multiple master pages, focused on what `sla_lib.builder` must emit so that the file remains valid after a user reorders, duplicates, or deletes pages in Scribus's GUI.
Primary sources: `scribusproject/scribus` branch `Version16x` — `scribus/plugins/fileloader/scribus150format/scribus150format.cpp` (loader), `…/scribus150format_save.cpp` (writer), `scribus/scribusdoc.cpp` (`movePage`, `reformPages`), `scribus/pageitem.h` (`ItemType` enum). Concrete document: `/root/workspace/Grüne Zeitung Vorlage Scribus.sla` (14 pages, 2 masters, Scribus 1.6.5).

---

## 1. Element model: how pages and masters are stored

Inside `<DOCUMENT>` the writer emits, in this order (`writeContent`, save.cpp:1672):

1. `<MASTERPAGE>` — one per master page, *empty* element (no children).
2. `<PAGE>` — one per document page, *empty* element.
3. `<FRAMEOBJECT>` — inline-frame items (embedded in text).
4. `<MASTEROBJECT>` — items that live on a master page.
5. `<PAGEOBJECT>` — items that live on a document page.

Items are *never* nested inside their page; they are siblings of the page elements and bind to a page by attribute. This is critical for the DSL: emitting items in any order is fine, but binding attributes must be correct.

### MASTERPAGE attributes (writer, save.cpp:1702-1742)

Mandatory: `PAGEXPOS`, `PAGEYPOS`, `PAGEWIDTH`, `PAGEHEIGHT`, `BORDERLEFT/RIGHT/TOP/BOTTOM`, `NUM`, **`NAM`** (master name — empty NAM is logged as `corrupted masterpage with empty name detected` and dropped), `MNAM` (always empty for masters), `Size`, `Orientation`, `LEFT`, `PRESET`, `VerticalGuides`, `HorizontalGuides`, `AGhorizontalAutoGap`, `AGverticalAutoGap`, `AGhorizontalAutoCount`, `AGverticalAutoCount`, `AGhorizontalAutoRefer`, `AGverticalAutoRefer`, `AGSelection`, `pageEffectDuration`, `pageViewDuration`, `effectType`, `Dm`, `M`, `Di`. NAM must be unique — it is the only stable identifier.

`LEFT`: `0` = right-hand master, `1` = left-hand master. Scribus does **not** enforce that a left master is applied only to a left-positioned doc page (the Grüne Zeitung has 4 right-positioned pages with `MNAM="Neue Musterseite links"` — loads without error). Empty/absent `MNAM` on a `<PAGE>` resolves to the implicit `"Normal"` master (load.cpp:4005).

### PAGE attributes

Same set as MASTERPAGE, but `NAM` is *empty* on a doc page (the loader uses non-empty NAM as the masterpage discriminator, load.cpp:3994-4002) and `MNAM` is the **string lookup** of which master to apply. There is **no per-page label**. Page Panel labels ("1, 2, 3" / "i, ii, iii") are derived from `<Sections>` (Type one of `Type_1_2_3` / `Type_i_ii_iii` / `Type_I_II_III` / `Type_a_b_c` / `Type_A_B_C` / `Type_None` / …). Sections only label *segments*; per-page text labels are not in the format.

### MASTEROBJECT vs PAGEOBJECT

Both elements share the same item attribute set written by `SetItemProps` (save.cpp:2624). The differences are:

| Aspect | MASTEROBJECT | PAGEOBJECT |
|---|---|---|
| Stored in | `MasterItems` | `DocItems` |
| Binds to page via | `OnMasterPage="<NAM>"` (string) | `OwnPage=<int>` (page index, 0-based) |
| Rendered when | applied master (`MNAM`) of any doc page = `OnMasterPage` | doc page index = `OwnPage` |
| Behaviour at render | drawn under doc-page items, every page that references the master | drawn once for its specific page |

Master objects are *not copied* into pages. Scribus iterates `MasterItems`, renders the ones whose `OnMasterPage` matches the current page's `MNAM`, then renders `DocItems` whose `OwnPage` matches. So a logo placed on master "rechts" appears under all 7 pages with `MNAM="Neue Musterseite rechts"`.

---

## 2. OwnPage stability across page reorder

`scribusdoc.cpp:6032 reformPages(moveObjects)` (called after every `movePage`/`addPage`/`deletePage`) walks every item and rewrites `OwnPage` based on a `pageTable[oldOwnPage].newPg` map (line 6148). It also moves the item by the X/Y offset delta so the item stays on its conceptual page. Consequence: **Scribus always renumbers `OwnPage` to remain positional 0..N-1 in current page order.** External tools that hold "page 3 = imprint" by remembering OwnPage=3 lose their reference whenever the user drags pages around. The DSL therefore must not surface raw OwnPage; instead, items should be addressed by item-name (`ANNAME`) or, where the user re-saves, only by reading `<PAGE NUM=…>` order at parse time.

`MNAM` on a `<PAGE>` is *not* renumbered — it is a string lookup and survives reorder. Master-page selection per page is therefore the only stable per-page property the user authors.

---

## 3. Facing pages, page sets

Two attributes on `<DOCUMENT>` matter:

- `BOOK` — integer index into the `<PageSets>` list. `0` = Single Page, `1` = Facing Pages, `2` = 3-Fold, `3` = 4-Fold (save.cpp:338, the index is `pagePositioning()`). The Grüne Zeitung sets `BOOK="1"`.
- `FIRSTLEFT` — only honoured when `BOOK != 0`; `1` means the document begins on a left-hand page, `0` means it begins on a right-hand page (load.cpp:1716-1719). The writer in 1.6.x doesn't always emit it; the same information sits in `<PageSets><Set Name="Facing Pages" FirstPage="1" .../>` as the **per-pageSet first-page index** (`FirstPage=1` => first column is right). The Grüne Zeitung uses `FirstPage="1"`, so page 0 sits in the right column (PAGEXPOS≈695), page 1 in the left column (PAGEXPOS≈100).

The full PageSets block must be present even for single-page documents; the loader hard-fails on a missing default set. The writer always emits all four (Single, Facing, 3-Fold, 4-Fold) unconditionally.

`PAGEXPOS`/`PAGEYPOS` on each `<PAGE>` are the absolute scratch-canvas coordinates and are recomputed by `reformPages()` from the page-set columns × `GapHorizontal`/`GapVertical`. The DSL does not need to compute these correctly on first save — Scribus normalises them on next open/save. Setting them roughly right keeps the file readable in older builds.

---

## 4. Layers

`<LAYERS>` is a flat list, one element per layer (save.cpp:1184). Attributes:

`NUMMER` (id, 0-based, used by `LAYER=` on items), `LEVEL` (z-stack, 0 = bottom), `NAME`, `SICHTBAR` (visible, 0/1), `DRUCKEN` (printable, 0/1), `EDIT` (editable, 0/1), `SELECT` (selectable in GUI, 0/1), `FLOW` (text flow, 0/1), `TRANS` (opacity 0-1), `BLEND` (blend-mode int), `OUTL` (outline-only mode, 0/1), `LAYERC` (marker colour `#rrggbb`).

Recommended editor-friendly stack for templates (LEVEL ascending, drawn bottom→top):

| LEVEL | NAME | SICHTBAR | DRUCKEN | EDIT | Purpose |
|---|---|---|---|---|---|
| 0 | Hintergrund | 1 | 1 | 0 | Master-page colour blocks, locked from accidental edit |
| 1 | Bilder | 1 | 1 | 1 | Image frames |
| 2 | Text | 1 | 1 | 1 | Editable text |
| 3 | Hilfslinien | 1 | **0** | 1 | Visible grid/note polygons that don't print |

Setting `DRUCKEN=0` on the Hilfslinien layer is the standard trick to show structural hints to the editor without leaking them into the PDF.

---

## 5. Concrete structure snippets

### (a) 2-master, 4-page facing-page document (skeleton)

```xml
<DOCUMENT ANZPAGES="4" PAGEWIDTH="595.276" PAGEHEIGHT="841.890"
          BORDERLEFT="59.528" BORDERRIGHT="59.528" BORDERTOP="59.528" BORDERBOTTOM="59.528"
          BOOK="1" FIRSTNUM="1" PAGESIZE="A4" ORIENTATION="0"
          ScratchLeft="100" ScratchTop="20" GapHorizontal="0" GapVertical="40" UNITS="1">
  <LAYERS NUMMER="0" LEVEL="0" NAME="Hintergrund" SICHTBAR="1" DRUCKEN="1" EDIT="1"
          SELECT="0" FLOW="0" TRANS="1" BLEND="0" OUTL="0" LAYERC="#000000"/>
  <PageSets>
    <Set Name="Single Page"  FirstPage="0" Rows="1" Columns="1"/>
    <Set Name="Facing Pages" FirstPage="1" Rows="1" Columns="2">
      <PageNames Name="Left Page"/><PageNames Name="Right Page"/>
    </Set>
    <Set Name="3-Fold" FirstPage="0" Rows="1" Columns="3">…</Set>
    <Set Name="4-Fold" FirstPage="0" Rows="1" Columns="4">…</Set>
  </PageSets>
  <Sections>
    <Section Number="0" Name="Hauptteil" From="0" To="3" Type="Type_1_2_3"
             Start="1" Reversed="0" Active="1" FillChar="0" FieldWidth="0"/>
  </Sections>

  <MASTERPAGE NUM="0" NAM="rechts" MNAM="" LEFT="0" Size="A4" Orientation="0" PRESET="0"
              PAGEXPOS="100" PAGEYPOS="20" PAGEWIDTH="595.276" PAGEHEIGHT="841.890"
              BORDERLEFT="59.528" BORDERRIGHT="59.528" BORDERTOP="59.528" BORDERBOTTOM="59.528"
              VerticalGuides="" HorizontalGuides="" AGSelection="0 0 0 0"
              AGhorizontalAutoGap="0" AGverticalAutoGap="0"
              AGhorizontalAutoCount="0" AGverticalAutoCount="0"
              AGhorizontalAutoRefer="0" AGverticalAutoRefer="0"
              pageEffectDuration="1" pageViewDuration="1" effectType="0" Dm="0" M="0" Di="0"/>
  <MASTERPAGE NUM="1" NAM="links"  MNAM="" LEFT="1" … />

  <PAGE NUM="0" NAM="" MNAM="rechts" LEFT="0" PAGEXPOS="695.276" PAGEYPOS="20" …/>
  <PAGE NUM="1" NAM="" MNAM="links"  LEFT="0" PAGEXPOS="100"     PAGEYPOS="901.890" …/>
  <PAGE NUM="2" NAM="" MNAM="rechts" LEFT="0" PAGEXPOS="695.276" PAGEYPOS="901.890" …/>
  <PAGE NUM="3" NAM="" MNAM="links"  LEFT="0" PAGEXPOS="100"     PAGEYPOS="1783.780" …/>

  <MASTEROBJECT OnMasterPage="rechts" OwnPage="-2" LAYER="0" PTYPE="4" XPOS="…" YPOS="…" …/>
  <PAGEOBJECT   OwnPage="0"                          LAYER="2" PTYPE="4" XPOS="…" YPOS="…" …/>
</DOCUMENT>
```

### (b) Master page with a 3-column grid

Express column guides as a space-separated list of x-coordinates from page origin in `VerticalGuides`. For a 595.276pt-wide page, 59.528pt margins, 3 columns with 12pt gutter: column tracks start/end at `59.528, 232.34, 244.34, 351.92, 363.92, 535.748` — but Scribus distinguishes content edges from gutter edges. The simplest editor-readable encoding is the four *gutter* edges:

```xml
<MASTERPAGE NUM="0" NAM="rechts" …
            VerticalGuides="232.34 244.34 351.92 363.92"
            HorizontalGuides=""/>
```

Alternatively use the auto-grid (`AGhorizontalAutoCount`, `AGverticalAutoCount`, `AGhorizontalAutoGap`) which Scribus's Manage Guides dialog edits.

### (c) Helper guide polygons on a hidden-from-print layer

```xml
<LAYERS NUMMER="3" LEVEL="3" NAME="Hilfslinien" SICHTBAR="1"
        DRUCKEN="0" EDIT="1" SELECT="1" FLOW="0"
        TRANS="1" BLEND="0" OUTL="0" LAYERC="#00aa00"/>
<MASTEROBJECT OnMasterPage="rechts" LAYER="3" PTYPE="6" …
              path="M0 0 L595 0 L595 841 L0 841 Z" .../>
```

---

## 6. Findings from the Grüne Zeitung SLA (14 pages, 2 masters)

1. **Two masters, asymmetric naming.** `NAM="Neue Musterseite rechts"` (LEFT=0, NUM=0) and `NAM="Neue Musterseite links"` (LEFT=1, NUM=1). Both have `MNAM=""`. Both have `VerticalGuides=""` and `HorizontalGuides=""` — *no* guides are stored on the master pages.
2. **MNAM is misapplied on 4 pages.** Pages 6, 9, 10, 13 sit in the right-hand column (PAGEXPOS≈695) but reference `MNAM="Neue Musterseite links"`. Scribus loads this without complaint; the user has been editing pages individually and the master assignment drifted.
3. **Per-page guides instead of per-master.** Pages 1, 3, 5, 6, 8, 9, 11, 12, 13 each carry the *same* `VerticalGuides="59.5276 535.748 "` and `HorizontalGuides="493.862 "`. Page 0 has its own custom guide set. None of these are inherited from masters — they were duplicated by hand. This is exactly the type of authoring drift our DSL should prevent by writing guides only on masters.
4. **`LEFT="0"` on every doc page.** The per-PAGE `LEFT` attribute is informational; the actual side is determined by PageSets columns and the master's own `LEFT`. So setting `LEFT=0` on every doc page is normal and works.
5. **Items use a single layer.** `LAYERS` has only `NAME="Ebene 1"` (NUMMER=0); all 140 PAGEOBJECTs and 5 FRAMEOBJECTs have `LAYER="0"`. There is no Hintergrund/Bilder/Text/Hilfslinien split — every kind of content lives on the same layer. This is editor-hostile (you can't lock backgrounds) and is one of the structural problems the new template generation should fix.
6. **FRAMEOBJECT items are inline.** All five `FRAMEOBJECT` entries have `OwnPage="-1"` and carry `InID="<int>"`. They're referenced from text runs by that InID, not by OwnPage. The DSL must not assign them a real page.
7. **PageSets contains all four standard sets.** Even though the document is facing-pages-only, the file contains Single Page, Facing Pages, 3-Fold, 4-Fold. Don't strip these on round-trip.
8. **Sections is single, simple.** `<Section Number="0" Name="Abschnitt 1" From="0" To="13" Type="Type_1_2_3" Start="1" Active="1"/>` — 14 pages, numbered 1..14 in the Page Panel.

---

## 7. Pitfalls when generating multi-page SLA programmatically

1. **`ItemID` is `qHash(item) & 0x7FFFFFFF`** (save.cpp:2627). Pointer-derived, unstable across runs. Cross-references — `NEXTITEM`, `BACKITEM` (linked text-frame chain), `WeldSource`/`Target`, bookmark `Element`, note `myID`/`MasterID` — all use ItemID. The DSL must assign deterministic ItemIDs at emit-time and route every cross-reference through the same allocator. Reusing Scribus's runtime hash is impossible because we don't have its address space.
2. **`OwnPage` is positional and renumbered.** Never store user-meaningful identity in OwnPage. The DSL's "page identity" must be either (a) a label encoded in the PAGE element via a synthetic guide-text annotation, or (b) the master assignment via `MNAM`, or (c) a name in `ANNAME` on a sentinel item.
3. **Empty `NAM` on `<MASTERPAGE>` makes the loader silently drop the master.** All linked PAGE elements then resolve to "Normal", which breaks layout. The DSL must reject empty/duplicate master names early.
4. **`MNAM` is a free-form string lookup.** Typos produce Scribus's fallback (master "Normal"), which the writer creates implicitly. Validate that every PAGE.MNAM exists in the MASTERPAGE NAM set.
5. **`LAYER=<NUMMER>` references on items.** If you re-emit `LAYERS` with different `NUMMER` values, every item's LAYER attribute breaks. Keep NUMMER stable across regenerations.
6. **`PageSets` is required and the `BOOK` index must be valid.** `BOOK=1` with only the Single Page set in PageSets crashes the loader. Always emit all four standard sets.
7. **`Sections` From/To must cover [0, ANZPAGES-1]** without overlap; gaps make the Page Panel show blank labels.
8. **Master items have `OwnPage=-2`** as a sentinel after load (load.cpp:4103). Some tools normalise that on save. Don't write `-2` defensively unless emulating the exact runtime invariant — `OnMasterPage="<NAM>"` is the load-bearing attribute.
9. **`PAGEXPOS`/`PAGEYPOS` drift.** Computed from `ScratchLeft`, `GapHorizontal`, `GapVertical`, page index, and PageSet columns. If you hand-compute, leave a 0.001pt tolerance — Scribus's `reformPages` will normalise on next save.
10. **Inline frames live in `FRAMEOBJECT` with `OwnPage=-1` and `InID=<qHash>`.** Text runs reference them via `<var>` markers. Generating an inline frame with a real OwnPage moves it onto a doc page and breaks the text it was embedded in.

---

## 8. Recommended DSL surface

Two builder methods, parameter-rich enough that templates with the Grüne Zeitung's complexity can be expressed without escape-hatches.

```python
def add_master(
    name: str,                       # NAM, must be unique, non-empty; the only stable id
    *,
    side: Literal["left", "right"] = "right",  # → LEFT (left=1, right=0)
    width: Length | None = None,                # default = doc PAGEWIDTH
    height: Length | None = None,
    margins: Margins | None = None,             # default = doc margins
    column_grid: ColumnGrid | None = None,      # writes VerticalGuides + auto-guide attrs
    baseline_grid: BaselineGrid | None = None,  # writes HorizontalGuides
    bleed: Bleed | None = None,                 # rarely per-master
    page_size: str = "A4",
    orientation: Literal[0, 1] = 0,
) -> Master: ...
```

```python
def add_page(
    *,
    master: str | Master,            # MNAM lookup; required (no implicit "Normal")
    label: str | None = None,        # informational; encoded as a Section if it changes the run, otherwise stored as ANNAME on a sentinel guide on the Hilfslinien layer
    section: str | None = None,      # creates/extends a <Section>; controls Page-Panel numbering style
    side: Literal["left", "right", "auto"] = "auto",  # "auto" infers from BOOK + index + FirstPage
    extra_guides: GuideSet | None = None,  # per-page overrides; discouraged, prefer master-level
    page_size: str | None = None,    # override doc default (rare)
    orientation: Literal[0, 1] | None = None,
) -> Page: ...
```

Notes on the surface:

- **`master` must accept the Master object**, not just a string, so refactors stay type-safe and the DSL can verify the master exists before emitting.
- **Page identity in the DSL is the returned `Page` handle**, not its index. Items are added via `page.add_text(...)`, `page.add_image(...)`, which compile down to `<PAGEOBJECT OwnPage=<resolved-index>>`. The index is computed at emit-time from page order, never stored on the Page handle.
- **`label`** has no first-class home in the SLA, so the DSL fakes it: it stores the label in `ANNAME` of an invisible 0×0 polygon on the Hilfslinien layer, with `OnMasterPage=""` and the page index encoded. On reparse, the DSL recovers the label by reading those sentinels. This survives `movePage` because Scribus carries the sentinel polygon along with the page.
- **`section`** changes the Page Panel numbering. When two consecutive pages have different `section` values, the DSL emits a new `<Section Type=…>`.
- **`side="auto"`** reads the document's BOOK + first-page setting; for facing pages the first emitted page lands in the column dictated by `<Set Name="Facing Pages" FirstPage>`.
- **No raw `OwnPage` parameter is exposed.** The DSL never lets the user write OwnPage; it derives it from emit-order and lets Scribus renumber on next save.
- **Master assignments should be configured on a per-spread basis, not per page**, so the DSL accepts `add_spread(left=..., right=...)` as sugar over two `add_page` calls.

---

## 9. Executive summary (300 words)

Scribus 1.6's SLA stores pages and items as siblings inside `<DOCUMENT>`. `<MASTERPAGE NAM="…">` defines a master; `<PAGE MNAM="…">` references one by string lookup. Empty `MNAM` resolves to the implicit master "Normal". Items live separately: `<MASTEROBJECT OnMasterPage="…">` for master-bound items, `<PAGEOBJECT OwnPage=N>` for page-bound items. Master items are not duplicated per page — Scribus walks `MasterItems` per render, drawing those whose `OnMasterPage` matches the current page's `MNAM`. Inline frames are `<FRAMEOBJECT OwnPage="-1">` and are referenced by their `InID` (a qHash of the original pointer).

`OwnPage` is positional and is rewritten by `reformPages()` after every page reorder; the DSL must never expose it as identity. `MNAM` is the only stable per-page property the user authors. Facing pages live behind `BOOK` (an index into `<PageSets>`) plus the per-set `FirstPage` flag. The full PageSets block (Single, Facing, 3-Fold, 4-Fold) must be emitted; the loader requires it.

There is **no per-page label** in the format. Page Panel labels are derived from `<Sections>` (numbering style + start), so custom labels must be faked via sentinel `ANNAME`-tagged guide polygons on a `DRUCKEN=0` layer.

The Grüne Zeitung file shows several authoring anti-patterns: 4 pages have the wrong-side master applied; guides are duplicated on every page instead of being defined on masters; everything sits on a single "Ebene 1" layer. The new DSL should prevent all three: enforce master-side consistency, push guides up to masters, and emit a 4-layer stack (Hintergrund/Bilder/Text/Hilfslinien) by default.

DSL surface: `add_master(name, *, side, width, height, margins, column_grid, baseline_grid, …)` and `add_page(*, master, label, section, side="auto", extra_guides=None, …)`. Both return handles; OwnPage is computed at emit-time. ItemIDs must come from a deterministic in-DSL allocator since `qHash(pointer)` is unreproducible.
