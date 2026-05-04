"""Slot-based editing of SLA documents.

Strategy:
- Text slot: replace concatenated text content while preserving the FIRST
  ITEXT run's formatting attributes (font, size, color). Removes any
  additional ITEXT runs in the StoryText so the new text inherits the
  formatting cleanly. Soft-hyphens in the source are dropped.
- Image slot: set PFILE attribute on the PAGEOBJECT (PTYPE=2) to a relative
  or absolute path. Caller is responsible for ensuring the file exists.

This is the deliberately-narrow MVP. Multi-run formatted text replacement,
inline images and table edits come later.
"""
from __future__ import annotations
from pathlib import Path

from lxml import etree

from .reader import SLADocument


class SLAEditor:
    def __init__(self, doc: SLADocument):
        self.doc = doc

    # -------- text ---------------------------------------------------------

    def set_text(self, slot_name: str, value: str) -> bool:
        """Replace text in a slot, preserving per-line formatting when possible.

        Strategy:
        1. If the new value has exactly as many lines as there are ITEXT runs
           in the StoryText, replace each run's `CH` in order. This preserves
           per-paragraph styling (e.g. headline lines alternating white/yellow).
        2. Otherwise, fall back to wiping all ITEXT/breakline siblings and
           emitting a single uniform run with the first ITEXT's formatting,
           with breaklines between lines. Mixed-style formatting is lost in
           this fallback.
        """
        anname = f"text:{slot_name}"
        frame = self.doc.find_by_anname(anname)
        if frame is None:
            return False
        story = frame.find("StoryText")
        if story is None:
            return False

        itexts = story.findall("ITEXT")
        new_lines = value.split("\n")

        if itexts and len(itexts) == len(new_lines):
            # Run-preserving replacement
            for it, line in zip(itexts, new_lines):
                it.set("CH", line)
            return True

        # Fallback: uniform replacement
        proto_attrs = dict(itexts[0].attrib) if itexts else {}
        for child in list(story):
            if child.tag in ("ITEXT", "breakline", "tab", "trail"):
                story.remove(child)
        for i, line in enumerate(new_lines):
            it = etree.SubElement(story, "ITEXT")
            for k, v in proto_attrs.items():
                if k != "CH":
                    it.set(k, v)
            it.set("CH", line)
            if i < len(new_lines) - 1:
                etree.SubElement(story, "breakline")
        return True

    # -------- image --------------------------------------------------------

    def set_image(self, slot_name: str, image_path: str | Path) -> bool:
        anname = f"image:{slot_name}"
        frame = self.doc.find_by_anname(anname)
        if frame is None or frame.attrib.get("PTYPE") != "2":
            return False
        # PFILE is relative-or-absolute; we store absolute and let Scribus
        # resolve. For repo-relative assets, callers should pass a path
        # relative to the SLA file's directory.
        frame.set("PFILE", str(image_path))
        # Reset crop/scale to fit defaults — Scribus recomputes on load.
        frame.set("LOCALSCX", "1")
        frame.set("LOCALSCY", "1")
        frame.set("LOCALX", "0")
        frame.set("LOCALY", "0")
        return True

    # -------- bulk fill ----------------------------------------------------

    def fill(self, data: dict) -> dict[str, str]:
        """Apply a {slot_name: value} mapping; returns per-slot status."""
        status: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(v, str):
                status[k] = "text:ok" if self.set_text(k, v) else "text:not-found"
            elif isinstance(v, dict) and v.get("type") == "image":
                ok = self.set_image(k, v["path"])
                status[k] = "image:ok" if ok else "image:not-found"
        return status

    # -------- write --------------------------------------------------------

    def write(self, path: str | Path) -> None:
        self.doc.write(path)
