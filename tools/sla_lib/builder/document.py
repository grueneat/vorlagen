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
from .styles import DocumentLayer, ParaStyle, CharStyle

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


def _fmt_num(value: float) -> str:
    """Format a numeric attribute the way Scribus does: integers stay integers
    (no trailing ``.0``), non-integers print with up to 6 decimals, trailing
    zeros stripped. Round-trip stable across save/reload."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


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
                 ci_path: Optional[Path | str] = None,
                 *,
                 layers: Optional[list[DocumentLayer]] = None,
                 facing_pages: bool = False,
                 column_gap_default_pt: float = 11.0,
                 unit: str = "mm",
                 deffont: str = "Gotham Narrow Book",
                 defsize: float = 12,
                 first_page_num: int = 1,
                 palette_replaces_ci: bool = False,
                 extra_doc_attrs: Optional[dict[str, str]] = None) -> None:
        self.title = title
        self.template_id = template_id
        self.author = author
        self.ci = load_ci(ci_path) if ci_path else load_ci()
        self.pages: list[Page] = []
        self.masters: list[Page] = []  # masters use Page structure too
        self.facing_pages: bool = facing_pages
        self.column_gap_default_pt: float = column_gap_default_pt
        self.unit: str = unit
        self.deffont: str = deffont
        self.defsize: float = defsize
        self.first_page_num: int = first_page_num
        self.palette_replaces_ci: bool = palette_replaces_ci
        # Extra DOCUMENT-level attributes the converter passes through
        # verbatim. Useful for round-tripping locale/runtime fields like
        # ALAYER, AUTOL, BaseC, CPICT, ICC profile names, calligraphic-pen
        # widths, etc. that Scribus assumes present on first read.
        self.extra_doc_attrs: dict[str, str] = dict(extra_doc_attrs) if extra_doc_attrs else {}
        self._idgen = _IdGen()
        # Per-document overrides — empty == fall back to CI defaults.
        self._layers_override: list[DocumentLayer] = list(layers) if layers else []
        self._extra_colors: dict[str, BrandColor] = {}
        self._extra_para_styles: dict[str, ParaStyle] = {}
        self._extra_char_styles: dict[str, CharStyle] = {}

    # ---- per-document palette / style registration ---------------------
    def add_color(self, name: str, *,
                   rgb: Optional[tuple[int, int, int]] = None,
                   cmyk: Optional[tuple[int, int, int, int]] = None,
                   spot: bool = False, register: bool = False) -> None:
        """Register a document-local color. Pass either ``rgb=`` or ``cmyk=``."""
        if (rgb is None) == (cmyk is None):
            raise ValueError("add_color requires exactly one of rgb= or cmyk=")
        if rgb is not None:
            self._extra_colors[name] = BrandColor(
                name=name, cmyk=(0, 0, 0, 0), rgb_native=tuple(rgb),
                spot=spot, register=register,
            )
        else:
            self._extra_colors[name] = BrandColor(
                name=name, cmyk=tuple(cmyk),
                spot=spot, register=register,
            )

    def add_para_style(self, style: ParaStyle) -> None:
        """Register a document-local paragraph style."""
        self._extra_para_styles[style.name] = style

    def add_char_style(self, style: CharStyle) -> None:
        """Register a document-local character style."""
        self._extra_char_styles[style.name] = style

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

    # ---- chain ID pre-allocation ---------------------------------------
    def _preallocate_chain_ids(self) -> None:
        """Walk all TextFrames; for each chain (head with BACKITEM=-1, follow
        next_item until a tail), allocate ItemIDs depth-first per chain so
        NEXTITEM/BACKITEM references resolve at emit time.

        Non-chained frames keep allocating fresh IDs in their natural emit
        order (after MASTEROBJECTs, which are always emitted before
        PAGEOBJECTs).
        """
        from .primitives import TextFrame
        # Collect frames in emit order (masters first, then pages).
        ordered_text_frames: list[TextFrame] = []
        for m in self.masters:
            for it in m.items:
                if isinstance(it, TextFrame):
                    ordered_text_frames.append(it)
        for p in self.pages:
            for it in p.items:
                if isinstance(it, TextFrame):
                    ordered_text_frames.append(it)
        # Build inverse map: target -> source
        prev_for: dict[int, TextFrame] = {}
        for f in ordered_text_frames:
            if f.next_item is not None:
                prev_for[id(f.next_item)] = f
        # Find chain heads (frame whose next_item != None, with no predecessor)
        head_to_chain: list[list[TextFrame]] = []
        seen: set[int] = set()
        for f in ordered_text_frames:
            if f.next_item is None:
                continue
            if id(f) in prev_for:
                continue  # not a head
            if id(f) in seen:
                continue
            chain: list[TextFrame] = []
            cur: Optional[TextFrame] = f
            while cur is not None:
                if id(cur) in seen:
                    break
                seen.add(id(cur))
                chain.append(cur)
                cur = cur.next_item
            head_to_chain.append(chain)
        # Allocate IDs depth-first per chain. The IDs come from the same
        # _IdGen so they remain monotonic and unique.
        for chain in head_to_chain:
            for f in chain:
                f._preallocated_id = self._idgen.next()

    # ---- XML emission ---------------------------------------------------
    def _build_xml(self) -> etree._Element:
        if not self.pages:
            raise ValueError("Document has no pages — call add_page() first")
        # Reset idgen so multiple save() calls produce stable IDs.
        self._idgen = _IdGen()
        # Pre-allocate IDs for chained TextFrames so NEXTITEM/BACKITEM resolve.
        self._preallocate_chain_ids()

        # Ensure a "Normal" master page exists ONLY when no masters are
        # defined at all. Templates that declare their own master(s) (e.g. the
        # Zeitung's 'Neue Musterseite rechts'/'Neue Musterseite links') must
        # not get a third auto-injected 'Normal' master.
        if not self.masters:
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
        attrs = {
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
            "FIRSTPAGENUM": str(self.first_page_num),
            "BOOK": "1" if self.facing_pages else "0",
            "FIRSTLEFT": "0",
            "AUTOSPALTEN": "1",
            "ABSTSPALTEN": f"{self.column_gap_default_pt:g}",
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
            # Both DEFFONT/DEFSIZE (legacy DSL fields) and DFONT/DSIZE
            # (what Scribus actually reads) are emitted; Scribus 1.6 looks
            # for DFONT specifically when rendering text frames whose ITEXT
            # has no explicit FONT.
            "DEFFONT": self.deffont,
            "DEFSIZE": f"{self.defsize:g}",
            "DFONT": self.deffont,
            "DSIZE": f"{self.defsize:g}",
            # Document language — used by hyphenation engine and as the
            # default for paragraph styles that omit LANGUAGE.
            "LANGUAGE": "de",
            # Default character / paragraph fill colors (Scribus expects these)
            "PEN": "Black",
            "BRUSH": "None",
            "PENLINE": "Black",
            "PENTEXT": "Black",
            "PENSHADE": "100",
            "BRUSHSHADE": "100",
            "LINESHADE": "100",
            "PICTSHADE": "100",
            # Misc render flags Scribus checks
            "AUTOMATIC": "1",
            "AUTOCHECK": "0",
            "BASEGRID": "13",
            "BASEO": "0",
            "STIL": "1",
            "STILLINE": "1",
            "WIDTH": "1",
            "WIDTHLINE": "5",
            "GROUPC": "1",
            "HCMS": "0",
            "showBleed": "1",
            "FIRSTNUM": "1",
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
        # Converter pass-through: any DOCUMENT attribute not explicitly handled
        # above gets emitted verbatim. Existing keys win (the DSL's own
        # constants take precedence over surprise overrides).
        for k, v in self.extra_doc_attrs.items():
            attrs.setdefault(k, v)
        return attrs

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
        # Scribus 1.6 expects per-channel integer attributes (C/M/Y/K) for
        # CMYK colors; native-RGB colors emit SPACE="RGB" with R/G/B.
        # When ``palette_replaces_ci=True``, only colors explicitly registered
        # via ``add_color`` are emitted. Otherwise, CI brand colors merge with
        # document-local extras (extras win on name collision).
        if self.palette_replaces_ci:
            all_colors: dict[str, BrandColor] = dict(self._extra_colors)
        else:
            all_colors = dict(self.ci.colors)
            for cname, c in self._extra_colors.items():
                all_colors[cname] = c
        for cname, c in all_colors.items():
            el = etree.SubElement(doc, "COLOR")
            el.set("NAME", cname)
            if c.rgb_native is not None:
                el.set("SPACE", "RGB")
                r, g, b = c.rgb_native
                el.set("R", str(r))
                el.set("G", str(g))
                el.set("B", str(b))
            else:
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
        # If the document registered its own char styles, emit those.
        # Otherwise, fall back to a single empty default CHARSTYLE.
        if self._extra_char_styles:
            for cs_obj in self._extra_char_styles.values():
                self._emit_char_style(doc, cs_obj)
        else:
            cs = etree.SubElement(doc, "CHARSTYLE")
            cs.set("CNAME", "")
            cs.set("FONT", self.ci.styles.get("ci/default",
                BrandStyle("ci/default", "Gotham Narrow Book", 12)).font)
            cs.set("FONTSIZE", "12")
            cs.set("FCOLOR", "Black")

        # If the document registered its own paragraph styles, emit those
        # using only-non-None semantics (PARENT inheritance preserved).
        # Otherwise, fall back to the CI brand style stack as before.
        if self._extra_para_styles:
            for ps in self._extra_para_styles.values():
                self._emit_para_style(doc, ps)
            return
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

    def _emit_char_style(self, doc, cs_obj: CharStyle) -> None:
        cs = etree.SubElement(doc, "CHARSTYLE")
        if cs_obj.is_default:
            cs.set("DefaultStyle", "1")
        cs.set("CNAME", cs_obj.name)
        for kw, attr in (
            ("font", "FONT"),
            ("fcolor", "FCOLOR"),
            ("fontfeatures", "FONTFEATURES"),
            ("features", "FEATURES"),
            ("language", "LANGUAGE"),
            ("scolor", "SCOLOR"),
            ("bgcolor", "BGCOLOR"),
        ):
            v = getattr(cs_obj, kw)
            if v is not None:
                cs.set(attr, v)
        for kw, attr in (
            ("fontsize", "FONTSIZE"),
            ("kern", "KERN"),
            ("txt_underline_pos", "TXTULP"),
            ("txt_underline_width", "TXTULW"),
            ("txt_strike_pos", "TXTSTP"),
            ("txt_strike_width", "TXTSTW"),
        ):
            v = getattr(cs_obj, kw)
            if v is not None:
                cs.set(attr, _fmt_num(v))
        for kw, attr in (
            ("fshade", "FSHADE"),
            ("hyph_word_min", "HyphenWordMin"),
            ("sshade", "SSHADE"),
            ("bgshade", "BGSHADE"),
            ("txt_shadow_x", "TXTSHX"),
            ("txt_shadow_y", "TXTSHY"),
            ("txt_outline", "TXTOUT"),
            ("scaleh", "SCALEH"),
            ("scalev", "SCALEV"),
            ("baseline_offset", "BASEO"),
        ):
            v = getattr(cs_obj, kw)
            if v is not None:
                cs.set(attr, str(v))

    def _emit_para_style(self, doc, ps: ParaStyle) -> None:
        st = etree.SubElement(doc, "STYLE")
        if ps.is_default:
            st.set("DefaultStyle", "1")
        st.set("NAME", ps.name)
        if ps.parent is not None:
            st.set("PARENT", ps.parent)
        # Only-non-None emission preserves PARENT inheritance.
        for kw, attr in (
            ("align", "ALIGN"),
            ("linesp_mode", "LINESPMode"),
            ("drop_lines", "DROPLIN"),
            ("hyph_consecutive_lines", "HyphenConsecutiveLines"),
            ("hyph_word_min", "HyphenWordMin"),
            ("keep_lines_start", "KeepLinesStart"),
            ("direction", "DIRECTION"),
            ("bshade", "BSHADE"),
            ("scalev", "SCALEV"),
            ("fshade", "FSHADE"),
            ("txt_shadow_x", "TXTSHX"),
            ("txt_shadow_y", "TXTSHY"),
            ("txt_outline", "TXTOUT"),
            ("baseline_offset", "BASEO"),
            ("numeration", "Numeration"),
        ):
            v = getattr(ps, kw)
            if v is not None:
                st.set(attr, str(v))
        for kw, attr in (
            ("linesp", "LINESP"),
            ("fontsize", "FONTSIZE"),
            ("space_before_pt", "VOR"),
            ("space_after_pt", "NACH"),
            ("first_indent_pt", "FIRST"),
            ("left_indent_pt", "INDENT"),
            ("right_indent_pt", "RMARGIN"),
            ("min_word_track", "MinWordTrack"),
            ("min_glyph_shrink", "MinGlyphShrink"),
            ("max_glyph_extend", "MaxGlyphExtend"),
            ("kern", "KERN"),
            ("paragraph_effect_offset", "ParagraphEffectOffset"),
            ("txt_underline_pos", "TXTULP"),
            ("txt_underline_width", "TXTULW"),
            ("txt_strike_pos", "TXTSTP"),
            ("txt_strike_width", "TXTSTW"),
        ):
            v = getattr(ps, kw)
            if v is not None:
                st.set(attr, _fmt_num(v))
        for kw, attr in (
            ("font", "FONT"),
            ("fcolor", "FCOLOR"),
            ("language", "LANGUAGE"),
            ("bcolor", "BCOLOR"),
            ("fontfeatures", "FONTFEATURES"),
            ("features", "FEATURES"),
            ("bullet", "Bullet"),
        ):
            v = getattr(ps, kw)
            if v is not None:
                st.set(attr, str(v))
        # Boolean fields become "1"/"0" only when set
        for kw, attr in (
            ("drop_cap", "DROP"),
            ("keep_together", "KeepTogether"),
        ):
            v = getattr(ps, kw)
            if v is not None:
                st.set(attr, "1" if v else "0")

    def _emit_table_cell_stubs(self, doc) -> None:
        ts = etree.SubElement(doc, "TableStyle")
        ts.set("NAME", "Default Table Style")
        cs = etree.SubElement(doc, "CellStyle")
        cs.set("NAME", "Default Cell Style")

    def _emit_layers(self, doc) -> None:
        # If the document declared its own layer stack via Document(layers=[...]),
        # emit those instead of the CI brand stack.
        if self._layers_override:
            for idx, layer in enumerate(self._layers_override):
                el = etree.SubElement(doc, "LAYERS")
                el.set("NUMMER", str(idx))
                el.set("LEVEL", str(idx))
                el.set("NAME", layer.name)
                el.set("SICHTBAR", "1" if layer.visible else "0")
                el.set("DRUCKEN", "1" if layer.printable else "0")
                el.set("EDIT", "1" if layer.editable else "0")
                el.set("SELECT", "1")
                el.set("FLOW", "1" if layer.flow else "0")
                el.set("TRANS", f"{layer.transparent:g}")
                el.set("BLEND", str(layer.blend))
                el.set("OUTL", "1" if layer.outline else "0")
                el.set("LAYERC", layer.layer_color)
            return
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
        # Minimal Printer + PDF blocks Scribus expects to be present.
        # The PDF block includes the document-level bleed (BBottom/BLeft/BRight/
        # BTop) and useDocBleeds=1 so PDF export honours the SLA's bleed setting
        # — without these the rendered PDF page would crop to the trim box and
        # visual_diff would fail with "raster size mismatch" against the
        # baseline (which was rendered from the same SLA-with-bleed source).
        pr = etree.SubElement(doc, "Printer")
        pr.set("firstUse", "1")
        pdf = etree.SubElement(doc, "PDF")
        bleed = self.pages[0].bleed_mm if self.pages else 3.0
        bleed_pt = mm_to_pt(bleed)
        pdf.set("Articles", "0")
        pdf.set("Bookmarks", "0")
        pdf.set("Compress", "1")
        pdf.set("CompressMethod", "0")
        pdf.set("Quality", "0")
        pdf.set("EmbedPDF", "0")
        pdf.set("Version", "16")
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
        # Bleed + marks — drives PDF page-with-bleed dimensions
        pdf.set("BBottom", _fmt_num(bleed_pt))
        pdf.set("BLeft", _fmt_num(bleed_pt))
        pdf.set("BRight", _fmt_num(bleed_pt))
        pdf.set("BTop", _fmt_num(bleed_pt))
        pdf.set("useDocBleeds", "1")
        pdf.set("cropMarks", "1")
        pdf.set("bleedMarks", "1")
        pdf.set("colorMarks", "0")
        pdf.set("docInfoMarks", "0")
        pdf.set("registrationMarks", "0")
        pdf.set("markLength", _fmt_num(bleed_pt))
        pdf.set("markOffset", _fmt_num(bleed_pt))
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
        # Wire NEXTITEM/BACKITEM for chained TextFrames using the preallocated
        # IDs assigned in _preallocate_chain_ids.
        from .primitives import TextFrame
        if isinstance(item, TextFrame):
            if item.next_item is not None and item.next_item._preallocated_id is not None:
                node.set("NEXTITEM", str(item.next_item._preallocated_id))
            # Find back-pointer: any frame whose next_item is this one
            for other_page in self.pages:
                for other in other_page.items:
                    if isinstance(other, TextFrame) and other.next_item is item:
                        if other._preallocated_id is not None:
                            node.set("BACKITEM", str(other._preallocated_id))
                        break
        doc.append(node)
