from __future__ import annotations
from pathlib import Path
from typing import Iterator

from lxml import etree

from .slot import Slot, SlotKind

PTYPE_NAMES = {
    "2": "Image", "4": "Text", "5": "Line", "6": "Polygon",
    "7": "PolyLine", "8": "PathText", "9": "LatexFrame",
    "10": "OSGFrame", "11": "Symbol", "12": "Group",
    "13": "RegularPolygon", "14": "Arc", "15": "Spiral",
    "16": "Table", "17": "NoteFrame",
}


class SLADocument:
    """Represents a parsed Scribus .sla document.

    XPOS/YPOS in PAGEOBJECT are scratch-space; subtract PAGEXPOS/PAGEYPOS
    of the owning PAGE to get page-local coordinates. All units are points.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
        self.tree = etree.parse(str(self.path), parser)
        self.root = self.tree.getroot()
        self.doc = self.root.find("DOCUMENT")
        if self.doc is None:
            raise ValueError(f"{path}: not a Scribus SLA (no DOCUMENT element)")

    # ------------- meta ----------------------------------------------------

    @property
    def version(self) -> str:
        return self.root.attrib.get("Version", "")

    @property
    def page_count(self) -> int:
        return int(self.doc.attrib.get("ANZPAGES", "0"))

    @property
    def page_size_pt(self) -> tuple[float, float]:
        return (float(self.doc.attrib["PAGEWIDTH"]),
                float(self.doc.attrib["PAGEHEIGHT"]))

    @property
    def bleed_pt(self) -> dict[str, float]:
        return {k.lower(): float(self.doc.attrib.get(f"Bleed{k}", "0"))
                for k in ("Top", "Bottom", "Left", "Right")}

    # ------------- objects -------------------------------------------------

    def page_objects(self) -> list[etree._Element]:
        return self.doc.findall("PAGEOBJECT")

    def pages(self) -> list[etree._Element]:
        return self.doc.findall("PAGE")

    def find_by_anname(self, anname: str) -> etree._Element | None:
        for o in self.page_objects():
            if o.attrib.get("ANNAME") == anname:
                return o
        return None

    # ------------- slots ---------------------------------------------------

    def slots(self) -> list[Slot]:
        out: list[Slot] = []
        for o in self.page_objects():
            anname = o.attrib.get("ANNAME", "")
            parsed = Slot.from_anname(anname)
            if parsed is None:
                continue
            kind, sid = parsed
            ptype = o.attrib.get("PTYPE", "")
            out.append(Slot(
                kind=kind, name=sid,
                page=int(o.attrib.get("OwnPage", "0")),
                x_pt=float(o.attrib.get("XPOS", "0")),
                y_pt=float(o.attrib.get("YPOS", "0")),
                w_pt=float(o.attrib.get("WIDTH", "0")),
                h_pt=float(o.attrib.get("HEIGHT", "0")),
                ptype=PTYPE_NAMES.get(ptype, ptype),
                item_id=o.attrib.get("ItemID", ""),
            ))
        return out

    # ------------- text helpers -------------------------------------------

    def iter_itext(self, frame: etree._Element) -> Iterator[etree._Element]:
        yield from frame.iter("ITEXT")

    def frame_text(self, frame: etree._Element) -> str:
        return "".join(it.attrib.get("CH", "") for it in self.iter_itext(frame))

    # ------------- writing -------------------------------------------------

    def write(self, path: str | Path) -> None:
        self.tree.write(
            str(path),
            encoding="UTF-8",
            xml_declaration=True,
            standalone=False,
        )
