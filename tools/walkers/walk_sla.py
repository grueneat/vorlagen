"""SLA-side walker for SCAFFOLD_INVENTORY.

Returns the subset of inventory fields that can only be answered from the
rendered ``template.sla``: which PAGEOBJECTs exist (by ANNAME), how many ITEXT
runs each carries, whether PFILE is set, and the set of STYLE/COLOR
definitions.

Pure wrapper around :class:`tools.sla_lib.reader.SLADocument` — no extra lxml
parsing here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.sla_lib.reader import SLADocument


def walk_sla(sla_path: Path) -> dict[str, Any]:
    """Return SLA-side inventory facts keyed for merging into ``Inventory``.

    Output shape::

        {
            "pageobject_count": int,
            "itext_total": int,
            "pfile_count": int,
            "sla_styles": set[str],          # STYLE NAMEs
            "sla_colors": set[str],          # COLOR NAMEs
            "by_anname": {
                "<anname>": {
                    "present": True,
                    "itext_count": int,
                    "pfile": bool,
                    "ptype": str,            # e.g. "Text", "Image", "Polygon"
                },
                ...
            },
            "itext_by_pstyle": {"<style_name>": int},
        }
    """
    doc = SLADocument(sla_path)
    objects = doc.page_objects()
    pageobject_count = len(objects)
    itext_total = 0
    pfile_count = 0
    by_anname: dict[str, dict[str, Any]] = {}
    itext_by_pstyle: dict[str, int] = {}

    for obj in objects:
        anname = obj.attrib.get("ANNAME", "")
        itexts = list(doc.iter_itext(obj))
        itext_total += len(itexts)
        pfile = bool(obj.attrib.get("PFILE", ""))
        if pfile:
            pfile_count += 1
        ptype = obj.attrib.get("PTYPE", "")
        ptype_name = {
            "2": "Image", "4": "Text", "5": "Line", "6": "Polygon",
            "7": "PolyLine", "8": "PathText", "12": "Group",
        }.get(ptype, ptype)
        if anname:
            by_anname[anname] = {
                "present": True,
                "itext_count": len(itexts),
                "pfile": pfile,
                "ptype": ptype_name,
            }
        # PSTYLE attribute on ITEXT/PARA carries the paragraph style name.
        for it in itexts:
            pstyle = it.attrib.get("PSTYLE") or ""
            if not pstyle:
                # PARA siblings can carry PARENT (style ref) — fall back.
                parent = it.getparent()
                if parent is not None:
                    pstyle = parent.attrib.get("PSTYLE") or ""
            if pstyle:
                itext_by_pstyle[pstyle] = itext_by_pstyle.get(pstyle, 0) + 1

    sla_styles = {s.attrib.get("NAME", "") for s in doc.iter_styles() if s.attrib.get("NAME")}
    sla_colors = {c.attrib.get("NAME", "") for c in doc.iter_colors() if c.attrib.get("NAME")}

    return {
        "pageobject_count": pageobject_count,
        "itext_total": itext_total,
        "pfile_count": pfile_count,
        "sla_styles": sla_styles,
        "sla_colors": sla_colors,
        "by_anname": by_anname,
        "itext_by_pstyle": itext_by_pstyle,
    }
