"""Document and Page builder — emits valid Scribus 1.6 SLA XML.

Element ordering inside <DOCUMENT> follows scribus150format_save.cpp:
1. Document attributes + CheckProfile
2. COLOR list (color palette)
3. STYLE / CHARSTYLE / TableStyle / CellStyle definitions
4. LAYERS
5. Printer / PDF / Sections / PageSets
6. MASTERPAGE elements (one per master)
7. PAGE elements (one per doc page)
8. FRAMEOBJECT (inline-embedded items, rare)
9. MASTEROBJECT (items on master pages)
10. PAGEOBJECT (items on doc pages)

The DSL emits this order verbatim. Page items collected on Page objects are
flushed at save() time as PAGEOBJECTs with correct OwnPage / OnMasterPage
binding.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Iterable

from lxml import etree

from .ci import load_ci, BrandColor, BrandStyle, BrandLayer

# Conversion: 1 mm = 2.83464566929... pt (1pt = 1/72in, 1in = 25.4mm)
MM_TO_PT = 72.0 / 25.4
PT_TO_MM = 25.4 / 72.0

# ISO standard page sizes in mm (portrait orientation)
ISO_SIZES_MM: dict[str, tuple[float, float]] = {
    "A0": (841, 1189),
    "A1": (594, 841),
    "A2": (420, 594),
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "A7": (74, 105),
}


def mm_to_pt(value_mm: float) -> float:
    return value_mm * MM_TO_PT


def resolve_size(size: str | tuple[float, float], orientation: str) -> tuple[float, float]:
    """Return (width_pt, height_pt). Accepts ISO name or (w_mm, h_mm) tuple."""
    if isinstance(size, str):
        if size not in ISO_SIZES_MM:
            raise ValueError(f"Unknown page size: {size}")
        w_mm, h_mm = ISO_SIZES_MM[size]
    else:
        w_mm, h_mm = size
    if orientation == "landscape":
        w_mm, h_mm = h_mm, w_mm
    elif orientation != "portrait":
        raise ValueError(f"orientation must be 'portrait' or 'landscape', got {orientation!r}")
    return mm_to_pt(w_mm), mm_to_pt(h_mm)


# ---------------------------------------------------------------------------
# ID generator — items get monotonic IDs at emit time
# ---------------------------------------------------------------------------
class _IdGen:
    def __init__(self, start: int = 100_000_000) -> None:
        self._next = start

    def next(self) -> int:
        v = self._next
        self._next += 1
        return v


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@dataclass
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float = 3.0
    margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10)  # L,R,T,B
    master_name: str = ""    # MNAM — empty resolves to "Normal"
    label: str = ""          # human-readable hint, rendered as a non-printing
                             # TextFrame on Hilfslinien layer when set (since
                             # Scribus has no per-page string label attribute)
    items: list = field(default_factory=list)
    own_page: int = 0        # set by Document at save time
    page_xpos_pt: float = 0  # scratch-canvas offset, set by Document
    page_ypos_pt: float = 0
    is_left: bool = False    # for facing-pages layout
    is_master: bool = False  # True for MasterPage, False for doc page
    master_id: str = ""      # NAM for MASTERPAGE; empty for doc pages

    def add(self, item) -> "Page":
        """Add a primitive or block to this page. Blocks (anything with an
        emit() method that yields primitives) are expanded immediately so
        the per-page item list stays flat for emission. Returns self for
        chaining."""
        if hasattr(item, "emit"):
            for primitive in item.emit():
                self.items.append(primitive)
        else:
            self.items.append(item)
        return self


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------
class Document:
    """A Scribus 1.6 document. Build pages, then call save()."""

    def __init__(self, title: str = "", template_id: str = "",
                 author: str = "Die Grünen Niederösterreich",
                 ci_path: Optional[Path | str] = None) -> None:
        self.title = title
        self.template_id = template_id
        self.author = author
        self.ci = load_ci(ci_path) if ci_path else load_ci()
        self.pages: list[Page] = []
        self.masters: list[Page] = []  # masters use Page structure too
        self.facing_pages: bool = False
        self._idgen = _IdGen()

    # ---- page authoring -------------------------------------------------
    # Scratch-canvas constants matching Scribus's own defaults so a fresh
    # multi-page document opens at the same position Scribus would write itself
    # (no jolt when the user opens then re-saves the file).
    SCRATCH_TOP = 20.0
    SCRATCH_LEFT = 100.0
    GAP_VERTICAL = 40.0  # gap between stacked pages in scratch space

    def add_master(self, name: str = "Normal",
                   size: str | tuple[float, float] = "A4",
                   orientation: str = "portrait",
                   bleed_mm: float = 3.0,
                   margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10),
                   facing: str = "right") -> Page:
        """Define a master page. Items added to it appear on every doc page
        whose master attribute matches `name`. `facing` is 'left' or 'right'
        — controls the LEFT attribute (0=right, 1=left) for facing-pages
        layouts.

        Master pages are stacked off to the side of the doc pages on the
        scratch canvas; Scribus normalises positions on next save.
        """
        if any(m.master_id == name for m in self.masters):
            raise ValueError(f"Master page named {name!r} already exists")
        w_pt, h_pt = resolve_size(size, orientation)
        m = Page(
            width_pt=w_pt, height_pt=h_pt, bleed_mm=bleed_mm, margins_mm=margins_mm,
            master_name="", label=name, own_page=len(self.masters),
            # Place masters in a separate column to the right of doc pages
            page_xpos_pt=self.SCRATCH_LEFT + w_pt + 200,
            page_ypos_pt=self.SCRATCH_TOP + len(self.masters) * (h_pt + self.GAP_VERTICAL),
            is_left=(facing == "left"),
            is_master=True, master_id=name,
        )
        self.masters.append(m)
        return m

    def add_page(self, size: str | tuple[float, float] = "A4",
                 orientation: str = "portrait",
                 bleed_mm: float = 3.0,
                 margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10),
                 master: str = "Normal",
                 label: str = "") -> Page:
        w_pt, h_pt = resolve_size(size, orientation)
        own_page = len(self.pages)
        # Page Y position = ScratchTop + cumulative previous page heights + gaps.
        # Page X position = ScratchLeft (single-page stacking; facing pages use columns).
        page_x = self.SCRATCH_LEFT
        page_y = self.SCRATCH_TOP + own_page * (h_pt + self.GAP_VERTICAL)
        if self.facing_pages:
            # Even index = left column, odd = right column. Two pages per row.
            is_left = (own_page % 2 == 0)
            page_x = self.SCRATCH_LEFT if is_left else self.SCRATCH_LEFT + w_pt
            page_y = self.SCRATCH_TOP + (own_page // 2) * (h_pt + self.GAP_VERTICAL)
        else:
            is_left = False
        page = Page(
            width_pt=w_pt, height_pt=h_pt, bleed_mm=bleed_mm, margins_mm=margins_mm,
            master_name=master, label=label, own_page=own_page,
            page_xpos_pt=page_x, page_ypos_pt=page_y, is_left=is_left,
        )
        self.pages.append(page)
        return page

    # ---- saving ---------------------------------------------------------
    def save(self, path: Path | str) -> None:
        root = self._build_xml()
        tree = etree.ElementTree(root)
        tree.write(str(path), encoding="UTF-8", xml_declaration=True, standalone=False, pretty_print=True)

    # ---- XML emission ---------------------------------------------------
    def _build_xml(self) -> etree._Element:
        if not self.pages:
            raise ValueError("Document has no pages — call add_page() first")

        # Ensure a "Normal" master page exists (any page MNAM that doesn't
        # match a master defaults to "Normal", which must exist).
        if not any(m.master_id == "Normal" for m in self.masters):
            normal = Page(
                width_pt=self.pages[0].width_pt,
                height_pt=self.pages[0].height_pt,
                bleed_mm=self.pages[0].bleed_mm,
                margins_mm=self.pages[0].margins_mm,
                master_name="", label="Normal", own_page=len(self.masters),
                page_xpos_pt=self.SCRATCH_LEFT + self.pages[0].width_pt + 200,
                page_ypos_pt=self.SCRATCH_TOP + len(self.masters) * (self.pages[0].height_pt + self.GAP_VERTICAL),
                is_master=True, master_id="Normal",
            )
            self.masters.insert(0, normal)

        # Use the first page's dimensions as the document defaults (Scribus convention)
        first = self.pages[0]
        page_w_pt = first.width_pt
        page_h_pt = first.height_pt

        root = etree.Element("SCRIBUSUTF8NEW", attrib={"Version": "1.6.5"})
        doc = etree.SubElement(root, "DOCUMENT", attrib=self._doc_attrs(page_w_pt, page_h_pt))

        self._emit_check_profiles(doc)
        self._emit_colors(doc)
        self._emit_styles(doc)
        self._emit_table_cell_stubs(doc)
        self._emit_layers(doc)
        self._emit_printer_pdf_stubs(doc)
        self._emit_sections(doc)
        self._emit_pagesets(doc)

        # 1. MASTERPAGE elements
        for m in self.masters:
            self._emit_masterpage(doc, m)

        # 2. PAGE elements
        for p in self.pages:
            self._emit_page(doc, p)

        # 3. MASTEROBJECTs — items on master pages, bound by OnMasterPage="<NAM>"
        for m in self.masters:
            for item in m.items:
                self._emit_master_item(doc, item, m)

        # 4. PAGEOBJECTs — items on doc pages, bound by OwnPage=<int>
        for p in self.pages:
            # If the page has a label, render it as a non-printing TextFrame
            # on the Hilfslinien layer at the very top of the page so the
            # variant is identifiable when scrolling the document.
            if p.label:
                from .primitives import TextFrame
                hilfslinien_idx = next((i for i, l in enumerate(self.ci.layers)
                                         if l.name == "Hilfslinien"), 3)
                label_frame = TextFrame(
                    x_mm=2, y_mm=2, w_mm=p.width_pt / MM_TO_PT - 4, h_mm=4,
                    text=f"BEISPIELSEITE — {p.label}",
                    style="ci/impressum", fcolor="Magenta",
                    layer=hilfslinien_idx, anname=f"Label: {p.label}",
                )
                self._emit_page_item(doc, label_frame, p)
            for item in p.items:
                self._emit_page_item(doc, item, p)

        return root

    # -- DOCUMENT attribute set ------------------------------------------
    def _doc_attrs(self, w_pt: float, h_pt: float) -> dict[str, str]:
        first = self.pages[0]
        ml, mr, mt, mb = first.margins_mm
        bleed = first.bleed_mm
        return {
            "ANZPAGES": str(len(self.pages)),
            "PAGEWIDTH": f"{w_pt:.6f}",
            "PAGEHEIGHT": f"{h_pt:.6f}",
            "BORDERLEFT": f"{mm_to_pt(ml):.6f}",
            "BORDERRIGHT": f"{mm_to_pt(mr):.6f}",
            "BORDERTOP": f"{mm_to_pt(mt):.6f}",
            "BORDERBOTTOM": f"{mm_to_pt(mb):.6f}",
            "BleedTop": f"{mm_to_pt(bleed):.6f}",
            "BleedBottom": f"{mm_to_pt(bleed):.6f}",
            "BleedLeft": f"{mm_to_pt(bleed):.6f}",
            "BleedRight": f"{mm_to_pt(bleed):.6f}",
            "ORIENTATION": "0",  # 0=portrait, 1=landscape
            "PAGESIZE": "Custom",
            "FIRSTPAGENUM": "1",
            "BOOK": "1" if self.facing_pages else "0",
            "FIRSTLEFT": "0",
            "AUTOSPALTEN": "1",
            "ABSTSPALTEN": "11",
            "UNITS": "1",  # 1=mm
            "TITLE": self.title,
            "AUTHOR": self.author,
            "COMMENTS": f"DSL-built template — {self.template_id}",
            "KEYWORDS": "",
            "PUBLISHER": "",
            "DOCDATE": "",
            "DOCTYPE": "",
            "DOCFORMAT": "",
            "DOCIDENT": "",
            "DOCSOURCE": "",
            "DOCLANGINFO": "",
            "DOCRELATION": "",
            "DOCCOVER": "",
            "DOCRIGHTS": "",
            "DOCCONTRIB": "",
            "DEFFONT": "Gotham Narrow Book",
            "DEFSIZE": "12",
            "DSAVE": "0",
            "AUTOSAVE": "0",
            "AUTOSAVETIME": "10",
            "AUTOSAVECOUNT": "1",
            "AUTOSAVEKEEP": "0",
            "AUTOSAVEINDOCDIR": "1",
            "AUTOSAVEDIR": "",
            "ScratchTop": str(self.SCRATCH_TOP),
            "ScratchLeft": str(self.SCRATCH_LEFT),
            "ScratchRight": "100",
            "ScratchBottom": "20",
            "GapHorizontal": "0",
            "GapVertical": str(self.GAP_VERTICAL),
            "PAGEC": "#ffffff",
            "MARGC": "#0033ff",
            "RANDF": "0",
            "currentProfile": "Default",
        }

    def _emit_check_profiles(self, doc) -> None:
        cp = etree.SubElement(doc, "CheckProfile")
        cp.set("Name", "Default")
        cp.set("ignoreErrors", "0")
        cp.set("autoCheck", "1")
        cp.set("checkGlyphs", "1")
        cp.set("checkOrphans", "1")
        cp.set("checkOverflow", "1")
        cp.set("checkPictures", "1")
        cp.set("checkPartFilledImageFrames", "0")
        cp.set("checkResolution", "1")
        cp.set("checkTransparency", "1")
        cp.set("minResolution", "144")
        cp.set("maxResolution", "4800")
        cp.set("checkAnnotations", "0")
        cp.set("checkRasterPDF", "1")
        cp.set("checkForGIF", "1")
        cp.set("ignoreOffLayers", "0")
        cp.set("checkOffConflictLayers", "0")
        cp.set("checkNotCMYKOrSpot", "0")
        cp.set("checkDeviceColorsAndOutputIntent", "0")
        cp.set("checkFontNotEmbedded", "0")
        cp.set("checkFontIsOpenType", "0")
        cp.set("checkAppliedMasterDifferentSide", "1")
        cp.set("checkEmptyTextFrames", "1")

    def _emit_colors(self, doc) -> None:
        # Scribus 1.6 expects per-channel integer attributes (C/M/Y/K), not
        # a packed hex CMYK= attribute. Verified by comparing emitted SLAs
        # against the existing Postkarte Vorlage.sla (renders correctly).
        for cname, c in self.ci.colors.items():
            el = etree.SubElement(doc, "COLOR")
            el.set("NAME", cname)
            el.set("SPACE", "CMYK")
            cval, mval, yval, kval = c.cmyk
            el.set("C", str(cval))
            el.set("M", str(mval))
            el.set("Y", str(yval))
            el.set("K", str(kval))
            if c.spot:
                el.set("Spot", "1")
            if c.register:
                el.set("Register", "1")

    def _emit_styles(self, doc) -> None:
        # CHARSTYLE block (one default)
        cs = etree.SubElement(doc, "CHARSTYLE")
        cs.set("CNAME", "")
        cs.set("FONT", self.ci.styles.get("ci/default", BrandStyle("ci/default", "Gotham Narrow Book", 12)).font)
        cs.set("FONTSIZE", "12")
        cs.set("FCOLOR", "Black")
        # STYLE blocks (paragraph styles)
        for sname, s in self.ci.styles.items():
            st = etree.SubElement(doc, "STYLE")
            st.set("NAME", sname)
            if s.parent:
                st.set("PARENT", s.parent)
            st.set("ALIGN", str(s.align))
            st.set("LINESP", f"{s.linesp:.6f}")
            st.set("LINESPMode", "2")
            st.set("FONT", s.font)
            st.set("FONTSIZE", f"{s.fontsize:.1f}")
            st.set("FCOLOR", s.fcolor)
            st.set("LANGUAGE", s.language)

    def _emit_table_cell_stubs(self, doc) -> None:
        ts = etree.SubElement(doc, "TableStyle")
        ts.set("NAME", "Default Table Style")
        cs = etree.SubElement(doc, "CellStyle")
        cs.set("NAME", "Default Cell Style")

    def _emit_layers(self, doc) -> None:
        for layer in self.ci.layers:
            el = etree.SubElement(doc, "LAYERS")
            el.set("NUMMER", str(layer.level))
            el.set("LEVEL", str(layer.level))
            el.set("NAME", layer.name)
            el.set("SICHTBAR", "1" if layer.visible else "0")
            el.set("DRUCKEN", "1" if layer.printable else "0")
            el.set("EDIT", "1" if layer.editable else "0")
            el.set("SELECT", "1")
            el.set("FLOW", "1")
            el.set("TRANS", "1")
            el.set("BLEND", "0")
            el.set("OUTL", "0")
            el.set("LAYERC", "#000000")

    def _emit_printer_pdf_stubs(self, doc) -> None:
        # Minimal Printer + PDF blocks Scribus expects to be present
        pr = etree.SubElement(doc, "Printer")
        pr.set("firstUse", "1")
        pdf = etree.SubElement(doc, "PDF")
        pdf.set("Articles", "0")
        pdf.set("Bookmarks", "0")
        pdf.set("Compress", "1")
        pdf.set("CompressMethod", "0")
        pdf.set("Quality", "0")
        pdf.set("EmbedPDF", "0")
        pdf.set("Version", "16")  # PDF 1.6
        pdf.set("Resolution", "300")
        pdf.set("Binding", "0")
        pdf.set("PicRes", "300")
        pdf.set("Grayscale", "0")
        pdf.set("UseProfiles", "0")
        pdf.set("UseProfiles2", "0")
        pdf.set("Intent", "1")
        pdf.set("MirrorH", "0")
        pdf.set("MirrorV", "0")
        pdf.set("openAction", "")
        # DocItemAttributes / TablesOfContents minimal
        etree.SubElement(doc, "DocItemAttributes")
        etree.SubElement(doc, "TablesOfContents")
        etree.SubElement(doc, "NotesStyles")

    def _emit_sections(self, doc) -> None:
        secs = etree.SubElement(doc, "Sections")
        # one numeric section spanning all pages — gives Page Panel "1, 2, 3..." numbering
        s = etree.SubElement(secs, "Section")
        s.set("Number", "0")
        s.set("Name", "Section 1")
        s.set("From", "0")
        s.set("To", str(max(0, len(self.pages) - 1)))
        s.set("Type", "Type_1_2_3")
        s.set("Start", "1")
        s.set("Reversed", "0")
        s.set("Active", "1")
        s.set("FillChar", "")
        s.set("FieldWidth", "0")

    def _emit_pagesets(self, doc) -> None:
        ps = etree.SubElement(doc, "PageSets")
        sets = [
            ("Single Page", "1", "0", []),
            ("Facing Pages", "2", "1", ["Left Page", "Right Page"]),
            ("3-Fold", "3", "0", ["Left Page", "Middle", "Right Page"]),
            ("4-Fold", "4", "0", ["Left Page", "Middle Left", "Middle Right", "Right Page"]),
        ]
        for name, cols, first, page_names in sets:
            s = etree.SubElement(ps, "Set")
            s.set("Name", name)
            s.set("FirstPage", first)
            s.set("Rows", "1")
            s.set("Columns", cols)
            s.set("GapHorizontal", "0")
            s.set("GapBelow", "40")
            s.set("GapVertical", "0")
            for pn in page_names:
                pname = etree.SubElement(s, "PageNames")
                pname.set("Name", pn)

    # -- masterpages and pages -------------------------------------------
    def _emit_masterpage(self, doc, m: Page) -> None:
        attrs = self._page_attrs(m, m.own_page)
        attrs["NAM"] = m.master_id
        attrs["MNAM"] = ""  # masters never reference another master
        attrs["NUM"] = str(m.own_page)
        etree.SubElement(doc, "MASTERPAGE", attrib=attrs)

    def _emit_page(self, doc, p: Page) -> None:
        attrs = self._page_attrs(p, p.own_page)
        attrs["NAM"] = ""  # empty NAM marks doc page (non-empty = master discriminator)
        attrs["MNAM"] = p.master_name or "Normal"
        attrs["NUM"] = str(p.own_page)
        etree.SubElement(doc, "PAGE", attrib=attrs)

    def _emit_master_item(self, doc, item, master: Page) -> None:
        """Same as _emit_page_item but renames the element to MASTEROBJECT
        and binds via OnMasterPage instead of OwnPage."""
        node = item.to_pageobject(self._idgen, master)
        node.tag = "MASTEROBJECT"
        # Replace OwnPage with OnMasterPage="<NAM>"
        if "OwnPage" in node.attrib:
            del node.attrib["OwnPage"]
        node.set("OnMasterPage", master.master_id)
        doc.append(node)

    def _page_attrs(self, p: Page, idx: int) -> dict[str, str]:
        ml, mr, mt, mb = p.margins_mm
        return {
            "PAGEXPOS": f"{p.page_xpos_pt:.6f}",
            "PAGEYPOS": f"{p.page_ypos_pt:.6f}",
            "PAGEWIDTH": f"{p.width_pt:.6f}",
            "PAGEHEIGHT": f"{p.height_pt:.6f}",
            "BORDERLEFT": f"{mm_to_pt(ml):.6f}",
            "BORDERRIGHT": f"{mm_to_pt(mr):.6f}",
            "BORDERTOP": f"{mm_to_pt(mt):.6f}",
            "BORDERBOTTOM": f"{mm_to_pt(mb):.6f}",
            "Size": "Custom",
            "Orientation": "0",
            "LEFT": "1" if p.is_left else "0",
            "PRESET": "0",
            "VerticalGuides": "",
            "HorizontalGuides": "",
            "AGhorizontalAutoGap": "0",
            "AGverticalAutoGap": "0",
            "AGhorizontalAutoCount": "1",
            "AGverticalAutoCount": "1",
            "AGhorizontalAutoRefer": "0",
            "AGverticalAutoRefer": "0",
            "AGSelection": "0 0 0 0",
            "pageEffectDuration": "1",
            "pageViewDuration": "1",
            "effectType": "0",
            "Dm": "0",
            "M": "0",
            "Di": "0",
        }

    # -- per-item emission -----------------------------------------------
    def _emit_page_item(self, doc, item, page: Page) -> None:
        # Each primitive class implements `to_pageobject(idgen, page)` returning
        # an element name + attributes + child elements
        node = item.to_pageobject(self._idgen, page)
        doc.append(node)
