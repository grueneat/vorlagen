#!/usr/bin/env python3
"""scaffold_render — emit template-scaffold.sla with demo images hidden.

The /idml-tune pipeline ships templates with placeholder/demo content
(photos that end users will replace). A second "scaffold" preview helps
the brand team see the structural layout cleanly: demo image frames
render as outlined empty rectangles ("image goes here, this size"),
while brand-embedded assets (logos, icons, social glyphs) stay visible.

Demo/brand classification by path heuristic (issue #55 follow-up):
  - PFILE in ``shared/assets/<template-slug>/`` AND filename does NOT
    contain ``logo`` / ``icon`` / ``wahlkreuz`` → DEMO
  - Anything else (inline images, brand asset paths) → KEEP visible

Demo frames in the scaffold get:
  - PICART="0"            (image hidden)
  - PWIDTH="0.7"          (thin frame border)
  - PCOLOR2="Schwarz"     (black outline)

Usage::

    python3 tools/scaffold_render.py <template.sla> <template-scaffold.sla>

Returns the number of demo frames muted (informational).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from lxml import etree


# A PFILE matching shared/assets/<slug>/ is template-specific demo content
# UNLESS the filename has a brand pattern. Tightening this list past the
# obvious ones can be done per-template via meta.yml if needed.
DEMO_PATH_RE = re.compile(r"shared/assets/([^/]+)/")
BRAND_NAME_RE = re.compile(r"(logo|icon|wahlkreuz)", re.IGNORECASE)


def is_demo_image(pfile: str, template_slug: str) -> bool:
    """True iff ``pfile`` is a demo asset for this template."""
    if not pfile:
        return False
    m = DEMO_PATH_RE.search(pfile)
    if not m or m.group(1) != template_slug:
        return False
    name = pfile.rsplit("/", 1)[-1]
    if BRAND_NAME_RE.search(name):
        return False
    return True


def make_scaffold(template_sla: Path, scaffold_sla: Path) -> int:
    """Read template_sla, write scaffold_sla with demo images muted.

    Returns the number of demo frames that were muted (0 = nothing to do).
    """
    slug = template_sla.parent.name
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(template_sla), parser)
    root = tree.getroot()
    n_demo = 0
    for po in root.iter("PAGEOBJECT"):
        pfile = po.get("PFILE", "")
        if not is_demo_image(pfile, slug):
            continue
        # PICART=0 alone isn't honoured on PDF export in Scribus 1.6.x —
        # the image still renders. Belt-and-suspenders: clear PFILE too so
        # there's nothing to load, AND drop SCALETYPE explicit attrs to
        # avoid stale-state warnings on Scribus reopen.
        po.set("PICART", "0")
        po.set("PFILE", "")
        # 1.0pt dashed outline in a bright neutral so the frame is visible
        # against both light and dark backgrounds. "White" is a Scribus
        # default color name; templates uniformly register it.
        po.set("PWIDTH", "1.0")
        po.set("PCOLOR2", "White")
        po.set("PLINEART", "2")  # dashed
        n_demo += 1
    scaffold_sla.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(scaffold_sla),
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )
    return n_demo


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(__doc__ or "")
        return 2
    template_sla = Path(argv[0]).resolve()
    scaffold_sla = Path(argv[1]).resolve()
    if not template_sla.exists():
        sys.stderr.write(f"scaffold_render: not found: {template_sla}\n")
        return 1
    n = make_scaffold(template_sla, scaffold_sla)
    rel = scaffold_sla
    try:
        rel = scaffold_sla.relative_to(Path.cwd())
    except ValueError:
        pass
    sys.stdout.write(
        f"scaffold_render: {n} demo image frame(s) muted → {rel}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
