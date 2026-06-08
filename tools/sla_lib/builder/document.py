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
    (no trailing ``.0``), non-integers print with shortest-round-trip
    precision (Python's ``repr``).

    Using ``repr`` instead of a fixed ``%.6f`` truncation matters for
    inline-image LOCALSCX values like ``0.0438778076573352`` (16 digits in
    the original SLA): truncating to 6 decimals shifts the rendered image
    by ~0.005 px per native pixel, visible at sharp edges (logo outlines)
    in the rendered PDF. Scribus itself emits floats with similar precision
    on save, so this matches the round-trip behaviour and stays bit-stable.
    """
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    # repr() returns the shortest float string that round-trips to the same
    # float on parse; that's exactly what we need to faithfully reproduce
    # the original SLA's precision without inflating attribute lengths for
    # values that have a clean short representation.
    return repr(float(value))


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
                 brand: Optional["Brand"] = None,
                 layers: Optional[list[DocumentLayer]] = None,
                 facing_pages: bool = False,
                 column_gap_default_pt: float = 11.0,
                 unit: str = "mm",
                 deffont: str = "Raleway Regular",
                 defsize: float = 12,
                 first_page_num: int = 1,
                 palette_replaces_ci: bool = False,
                 hcms: bool = False,
                 doc_page_width_pt: Optional[float] = None,
                 doc_page_height_pt: Optional[float] = None,
                 extra_doc_attrs: Optional[dict[str, str]] = None,
                 extra_pdf_attrs: Optional[dict[str, str]] = None) -> None:
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
        # HCMS=1 enables Scribus's color-management-system rendering: CMYK
        # colors are translated through the configured ICC profiles
        # (DPInCMYK / DPPr) on draw + PDF export. With HCMS=0 Scribus uses a
        # naive CMYK→sRGB conversion that produces visibly different RGB
        # values for the same CMYK input. The originals all have HCMS=1, so
        # the converter sets this to True to match the baseline rendering.
        self.hcms: bool = hcms
        # DOCUMENT-level PAGEWIDTH/PAGEHEIGHT override. Scribus stores these
        # twice (DOCUMENT.PAGEWIDTH and per-PAGE PAGEWIDTH), with the
        # DOC-level value sometimes carrying more precision than the PAGE
        # value. The converter captures both so the rebuilt SLA is
        # byte-equivalent at the doc level too.
        self.doc_page_width_pt: Optional[float] = doc_page_width_pt
        self.doc_page_height_pt: Optional[float] = doc_page_height_pt
        # Extra DOCUMENT-level attributes the converter passes through
        # verbatim. Useful for round-tripping locale/runtime fields like
        # ALAYER, AUTOL, BaseC, CPICT, ICC profile names, calligraphic-pen
        # widths, etc. that Scribus assumes present on first read.
        self.extra_doc_attrs: dict[str, str] = dict(extra_doc_attrs) if extra_doc_attrs else {}
        # Extra PDF-element attributes the converter passes through verbatim.
        # The CMS-relevant set (SolidP / ImageP / PrintP / Intent / RGBMode /
        # UseSpotColors / Version / etc.) drives what ICC profile Scribus
        # uses on PDF export; without them, Scribus falls back to a naive
        # CMYK→sRGB conversion that mismatches the baseline rendering.
        self.extra_pdf_attrs: dict[str, str] = dict(extra_pdf_attrs) if extra_pdf_attrs else {}
        self._idgen = _IdGen()
        # Per-document overrides — empty == fall back to CI defaults.
        self._layers_override: list[DocumentLayer] = list(layers) if layers else []
        self._extra_colors: dict[str, BrandColor] = {}
        self._extra_para_styles: dict[str, ParaStyle] = {}
        self._extra_char_styles: dict[str, CharStyle] = {}

        # Brand profile injection.  When a Brand is supplied:
        # - Its colors, para-styles, char-styles, and layers replace the CI
        #   defaults (brand IS the CI; palette_replaces_ci is forced False so
        #   the brand's palette is used as-is without re-listing it).
        # - Its default_doc_attrs / default_pdf_attrs are merged UNDER the
        #   caller-supplied extra_*_attrs (caller wins on conflict).
        # - deffont / defsize / column_gap_default_pt from the brand apply
        #   unless the caller explicitly passed different values.
        # When Brand is None: no behavior change — every existing test passes.
        if brand is not None:
            # Force palette_replaces_ci=True: brand colors ARE the palette.
            # Using _extra_colors as the sole source avoids emitting CI colors
            # twice (brand.colors already IS ci.colors for Grüne NÖ).  Any
            # colors the template adds via doc.add_color() are appended to
            # _extra_colors and appear in the emitted list.
            self.palette_replaces_ci = True
            # Auto-register brand colors as document extras so they appear in
            # the emitted COLOR list.  Skip any already added by the caller.
            for cname, bc in brand.colors.items():
                if cname not in self._extra_colors:
                    self._extra_colors[cname] = bc
            # Auto-register brand para-styles.
            for sname, ps in brand.para_styles.items():
                if sname not in self._extra_para_styles:
                    self._extra_para_styles[sname] = ps
            # Auto-register brand char-styles.
            for csname, cs in brand.char_styles.items():
                if csname not in self._extra_char_styles:
                    self._extra_char_styles[csname] = cs
            # Auto-register brand layers if no caller-supplied override.
            if not self._layers_override:
                self._layers_override = list(brand.layers)
            # Merge brand doc/pdf defaults UNDER caller's extra_*_attrs.
            merged_doc = dict(brand.default_doc_attrs)
            merged_doc.update(self.extra_doc_attrs)  # caller wins
            self.extra_doc_attrs = merged_doc
            merged_pdf = dict(brand.default_pdf_attrs)
            merged_pdf.update(self.extra_pdf_attrs)  # caller wins
            self.extra_pdf_attrs = merged_pdf

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
                   facing: str = "right",
                   page_xpos_pt: Optional[float] = None,
                   page_ypos_pt: Optional[float] = None,
                   width_pt: Optional[float] = None,
                   height_pt: Optional[float] = None) -> Page:
        """Define a master page. Items added to it appear on every doc page
        whose master attribute matches `name`. `facing` is 'left' or 'right'
        — controls the LEFT attribute (0=right, 1=left) for facing-pages
        layouts.

        ``page_xpos_pt`` / ``page_ypos_pt`` override the auto-computed
        scratch-canvas offset (used by the converter for byte-equivalent
        round-trip; see ``add_page`` for why). ``width_pt`` / ``height_pt``
        override the size resolved from ``size``+``orientation`` so the
        original SLA's exact PAGEWIDTH/PAGEHEIGHT values (which often
        carry more precision than ``mm_to_pt(210)`` produces) round-trip
        without rounding drift.

        Master pages are stacked off to the side of the doc pages on the
        scratch canvas; Scribus normalises positions on next save.
        """
        if any(m.master_id == name for m in self.masters):
            raise ValueError(f"Master page named {name!r} already exists")
        w_pt, h_pt = resolve_size(size, orientation)
        if width_pt is not None:
            w_pt = width_pt
        if height_pt is not None:
            h_pt = height_pt
        # Place masters in a separate column to the right of doc pages
        page_x = self.SCRATCH_LEFT + w_pt + 200
        page_y = self.SCRATCH_TOP + len(self.masters) * (h_pt + self.GAP_VERTICAL)
        if page_xpos_pt is not None:
            page_x = page_xpos_pt
        if page_ypos_pt is not None:
            page_y = page_ypos_pt
        m = Page(
            width_pt=w_pt, height_pt=h_pt, bleed_mm=bleed_mm, margins_mm=margins_mm,
            master_name="", label=name, own_page=len(self.masters),
            page_xpos_pt=page_x,
            page_ypos_pt=page_y,
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
                 label: str = "",
                 page_xpos_pt: Optional[float] = None,
                 page_ypos_pt: Optional[float] = None,
                 width_pt: Optional[float] = None,
                 height_pt: Optional[float] = None) -> Page:
        """Add a doc page at the next slot in the scratch canvas.

        ``page_xpos_pt`` / ``page_ypos_pt`` override the auto-computed
        scratch-canvas offset. The converter uses these to round-trip the
        original SLA's exact PAGEXPOS/PAGEYPOS — the auto-computed offset
        rounds to ``SCRATCH_LEFT + w_pt`` (which itself is the DSL's
        ``mm_to_pt(210)`` ≈ 595.2755905511812), but the original SLA
        often carries a slightly different value (e.g.
        ``695.276220472441 = 100.00062992126 + 595.275590551181``). Without
        an override, items round-trip with sub-pixel position drift on
        every page; with the override, PAGEXPOS round-trips exactly and the
        per-frame XPOS does too (the converter computes XPOS from the
        original frame's local-pt coords + the original PAGEXPOS).
        """
        w_pt, h_pt = resolve_size(size, orientation)
        if width_pt is not None:
            w_pt = width_pt
        if height_pt is not None:
            h_pt = height_pt
        own_page = len(self.pages)
        # Single-page stacking: every page sits in the left column, stacked
        # vertically with GapVertical between rows.
        page_x = self.SCRATCH_LEFT
        page_y = self.SCRATCH_TOP + own_page * (h_pt + self.GAP_VERTICAL)
        if self.facing_pages:
            # Facing pages with PageSets <Set Name="Facing Pages" FirstPage="1">
            # — the first doc page sits ALONE in the right column on row 0
            # (cover), then every subsequent pair (1,2), (3,4), ... shares a
            # row with the left page in the left column and the right page in
            # the right column. The Y stride is PageHeight + GapVertical.
            #
            # Row indices: page 0 → row 0 (right, alone); page 1 → row 1 (left);
            # page 2 → row 1 (right); page 3 → row 2 (left); page 4 → row 2 (right); ...
            # Side: page 0 → right; odd index → left; even index (>0) → right.
            if own_page == 0:
                row = 0
                side_left = False  # cover stands on the right column
            else:
                row = ((own_page - 1) // 2) + 1
                side_left = ((own_page - 1) % 2 == 0)
            page_x = (self.SCRATCH_LEFT if side_left
                      else self.SCRATCH_LEFT + w_pt)
            page_y = self.SCRATCH_TOP + row * (h_pt + self.GAP_VERTICAL)
            # The per-PAGE LEFT attribute is informational; the actual side is
            # determined by PageSets columns + master's LEFT. Match the
            # original Scribus convention of writing LEFT="0" on every doc
            # page (verified against gruene-zeitung-vorlage-original.sla, all
            # 14 pages have LEFT="0"). Templates that rely on facing-page side
            # use master_name lookup, not the per-page LEFT bit.
            is_left = False
        else:
            is_left = False
        if page_xpos_pt is not None:
            page_x = page_xpos_pt
        if page_ypos_pt is not None:
            page_y = page_ypos_pt
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

    # ---- structural-check anchor (Issue #12) ----------------------------
    def iter_all_primitives(self) -> Iterable:
        """Yield every primitive across master pages and doc pages, in stable
        order: masters first, then pages; per-page items in ``page.items``
        order (already flattened by ``Page.add`` at insertion time).

        This is the single orchestration anchor used by
        ``tools/sla_lib/builder/structural_check.py`` to walk a built
        Document. No caching, no filtering — KISS. Constraint and
        brand-rule predicates do their own filtering via ``isinstance``
        / anname matching.
        """
        for page in (*self.masters, *self.pages):
            yield from page.items

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

        # Use the first page's dimensions as the document defaults (Scribus
        # convention). The converter overrides these via doc_page_width_pt /
        # doc_page_height_pt for byte-equivalent round-trip — the original
        # SLA's DOCUMENT.PAGEWIDTH may carry more precision than the
        # per-PAGE PAGEWIDTH (Scribus stores them separately on save).
        first = self.pages[0]
        page_w_pt = self.doc_page_width_pt if self.doc_page_width_pt is not None else first.width_pt
        page_h_pt = self.doc_page_height_pt if self.doc_page_height_pt is not None else first.height_pt

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
            "PAGEWIDTH": _fmt_num(w_pt),
            "PAGEHEIGHT": _fmt_num(h_pt),
            "BORDERLEFT": _fmt_num(mm_to_pt(ml)),
            "BORDERRIGHT": _fmt_num(mm_to_pt(mr)),
            "BORDERTOP": _fmt_num(mm_to_pt(mt)),
            "BORDERBOTTOM": _fmt_num(mm_to_pt(mb)),
            "BleedTop": _fmt_num(mm_to_pt(bleed)),
            "BleedBottom": _fmt_num(mm_to_pt(bleed)),
            "BleedLeft": _fmt_num(mm_to_pt(bleed)),
            "BleedRight": _fmt_num(mm_to_pt(bleed)),
            "ORIENTATION": "0",  # 0=portrait, 1=landscape
            "PAGESIZE": "Custom",
            "BOOK": "1" if self.facing_pages else "0",
            # FIRSTPAGENUM/FIRSTLEFT are obsolete legacy fields — Scribus 1.6
            # uses FIRSTNUM instead. Originals don't carry FIRSTPAGENUM or
            # FIRSTLEFT, so the DSL omits them too.
            "AUTOSPALTEN": "1",
            "ABSTSPALTEN": f"{self.column_gap_default_pt:g}",
            "UNITS": "1",  # 1=mm
            "TITLE": self.title,
            "AUTHOR": self.author,
            "COMMENTS": "",
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
            # DFONT/DSIZE are what Scribus 1.6 actually reads when a text
            # frame's ITEXT has no explicit FONT/FONTSIZE. The originals
            # emit only these (no DEFFONT/DEFSIZE), so we follow suit.
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
            "HCMS": "1" if self.hcms else "0",
            "showBleed": "1",
            "FIRSTNUM": "1",
            # AutoSave state — emitted with Scribus's camelCase naming
            # (matches the originals on save). DSAVE and the all-uppercase
            # AUTOSAVE/AUTOSAVECOUNT/... variants are obsolete and dropped.
            "AutoSave": "1",
            "AutoSaveTime": "600000",
            "AutoSaveCount": "1",
            "AutoSaveKeep": "0",
            "AUtoSaveInDocDir": "1",
            "AutoSaveDir": "",
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
        # Converter pass-through: ``extra_doc_attrs`` overrides the DSL's
        # own hardcoded defaults so the rebuilt SLA can preserve quirky
        # doc-level fields verbatim (PENLINE="Green", MARGC="#0000ff",
        # PAGESIZE="A4", camelCase AutoSave variants, etc.). The DSL's
        # defaults are still emitted for keys the converter does NOT
        # provide; only when the converter explicitly captures a value
        # does it replace the default.
        for k, v in self.extra_doc_attrs.items():
            attrs[k] = v
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
                BrandStyle("ci/default", "Raleway Regular", 12)).font)
            cs.set("FONTSIZE", "12")
            cs.set("FCOLOR", "Black")

        # Paragraph-style emission order (additive, Codex A-1 fix):
        #
        # Mirrors _emit_colors: palette_replaces_ci=True (including the brand
        # path, which forces this flag True) means _extra_para_styles is the
        # sole source.  palette_replaces_ci=False means CI brand stack is the
        # base, with _extra_para_styles additive on top (custom style wins on
        # name collision).
        #
        # Pre-fix behavior had an unconditional early `return` after emitting
        # _extra_para_styles regardless of palette_replaces_ci.  This meant
        # a template that added even one custom style (palette_replaces_ci=False)
        # would silently drop the entire CI stack — making the CI styles
        # invisible to Scribus on round-trip.
        if self.palette_replaces_ci:
            # palette_replaces_ci=True: only emit explicitly registered styles.
            # Brand path: brand CI styles are in _extra_para_styles already.
            for ps in self._extra_para_styles.values():
                self._emit_para_style(doc, ps)
        else:
            # palette_replaces_ci=False: CI stack is the base; custom styles
            # are additive (custom name shadows CI name).
            ci_overridden = set(self._extra_para_styles)
            for sname, s in self.ci.styles.items():
                if sname in ci_overridden:
                    continue  # template override takes precedence
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
            for ps in self._extra_para_styles.values():
                self._emit_para_style(doc, ps)

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
        # Tab stops — child <Tabs> elements (Scribus 1.6.x SLA format).
        # Each entry is (position_pt, type): type 0=left, 1=right, 2=center, 3=decimal.
        if ps.tab_stops:
            for pos_pt, tab_type in ps.tab_stops:
                tab_el = etree.SubElement(st, "Tabs")
                tab_el.set("Type", str(tab_type))
                tab_el.set("Pos", _fmt_num(pos_pt))
                tab_el.set("Fill", "")

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
        # Pass-through any extra PDF attributes the converter captured from
        # the original (ICC profile names, Intent2, RGBMode, UseSpotColors,
        # Version, PicRes, useDocBleeds, etc.). The converter's extras win
        # over the DSL defaults — the original's PDF state is what produced
        # the frozen baseline, so faithful round-trip requires honouring it
        # exactly. Bleed dimensions (BBottom/BLeft/BRight/BTop/markLength/
        # markOffset) are still guarded — they are derived from the page's
        # bleed_mm and overriding them via extras would silently
        # de-synchronise the PDF page bbox from the SLA's bleed setting.
        BLEED_GUARDED = {
            "BBottom", "BLeft", "BRight", "BTop",
            "markLength", "markOffset",
        }
        for k, v in self.extra_pdf_attrs.items():
            if k in BLEED_GUARDED:
                continue
            pdf.set(k, v)
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
            "PAGEXPOS": _fmt_num(p.page_xpos_pt),
            "PAGEYPOS": _fmt_num(p.page_ypos_pt),
            "PAGEWIDTH": _fmt_num(p.width_pt),
            "PAGEHEIGHT": _fmt_num(p.height_pt),
            "BORDERLEFT": _fmt_num(mm_to_pt(ml)),
            "BORDERRIGHT": _fmt_num(mm_to_pt(mr)),
            "BORDERTOP": _fmt_num(mm_to_pt(mt)),
            "BORDERBOTTOM": _fmt_num(mm_to_pt(mb)),
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
