#!/usr/bin/env python3
"""Generic, template-agnostic SLA post-processor for per-Bundesland impressum.

Templates carry an impressum placeholder (``Impressum: xxxxxx``). This tool
finds the text frame holding it and substitutes a Landesorganisation-specific
impressum line. Detection is at frame level — a ``PAGEOBJECT`` whose
concatenated ``ITEXT/@CH`` text contains the word "Impressum" — so it works
across all slot variants (single run, split runs, paragraph-separated) and
needs no per-template knowledge.

CLI:
  python3 tools/impressum.py --all
      For every templates/<id>/template.sla emit
      templates/<id>/impressum/<slug>.sla for each Bundesland.
  python3 tools/impressum.py <sla> <slug>
      Single case — writes <sla-dir>/impressum/<slug>.sla.

The substitution is purely textual: frame geometry, page layout and fold
logic are untouched. SLA encoding is UTF-8.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "shared" / "impressum" / "bundeslaender.yml"
TEMPLATES_DIR = ROOT / "templates"

# Character attributes copied from the original first ITEXT onto the new run.
# Everything except CH (the text content itself) is carried over verbatim.
_CARRIED_SKIP = {"CH"}


def load_bundeslaender(path: str | Path | None = None) -> dict:
    """Load the impressum data source.

    Returns ``{"default": <slug>, "bundeslaender": [<entry>, ...]}``.
    Default path: ``<repo>/shared/impressum/bundeslaender.yml``.
    """
    p = Path(path) if path is not None else DATA_PATH
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "bundeslaender" not in data:
        raise RuntimeError(f"invalid impressum data source: {p}")
    return data


def _entry_for(data: dict, slug: str) -> dict:
    """Resolve a Bundesland entry by slug, falling back to ``default``."""
    by_slug = {e["slug"]: e for e in data["bundeslaender"]}
    if slug in by_slug:
        return by_slug[slug]
    default = data.get("default")
    if default in by_slug:
        return by_slug[default]
    raise RuntimeError(f"unknown Bundesland slug '{slug}' and no valid default")


def _frame_text(pageobject: ET.Element) -> str:
    """Concatenate all ITEXT/@CH content within a PAGEOBJECT's story."""
    return "".join(it.get("CH", "") for it in pageobject.iter("ITEXT"))


def find_impressum_frames(root: ET.Element) -> list[ET.Element]:
    """Return PAGEOBJECT elements identified as impressum frames.

    A frame is an impressum frame when 'impressum' (case-insensitive) appears
    either in its concatenated ITEXT/@CH text — so split-run placeholders are
    caught — or in its ANNAME (the frame name set in InDesign/Scribus). The
    ANNAME fallback covers templates whose impressum frame already carries a
    rendered text without the literal word (e.g. tischschild-a5-quer).
    """
    frames = []
    for po in root.iter("PAGEOBJECT"):
        anname = (po.get("ANNAME") or "").lower()
        if "impressum" in _frame_text(po).lower() or "impressum" in anname:
            frames.append(po)
    return frames


def _impressum_text(entry: dict) -> str:
    """Build the full impressum string for one Bundesland entry."""
    text = "Impressum: " + entry["impressum"]
    druck = (entry.get("druck") or "").strip()
    if druck:
        text += " " + druck
    return text


def _rewrite_story(frame: ET.Element, text: str) -> None:
    """Replace a frame's story runs with a single impressum ITEXT.

    The new ITEXT inherits the character attributes of the frame's first
    existing ITEXT. All existing ITEXT and para nodes are dropped; structural
    nodes such as StoryText/DefaultStyle/trail are preserved so the Scribus
    story stays valid.
    """
    story = frame.find("StoryText")
    if story is None:
        # Some SLAs nest ITEXT directly; operate on the frame itself.
        story = frame

    first_itext = story.find("ITEXT")
    carried = {}
    if first_itext is not None:
        carried = {
            k: v for k, v in first_itext.attrib.items() if k not in _CARRIED_SKIP
        }

    # Find an insertion index: keep leading non-text nodes (DefaultStyle),
    # remove ITEXT and para, keep a trailing trail/para structural node.
    children = list(story)
    insert_at = len(children)
    for i, child in enumerate(children):
        if child.tag in ("ITEXT", "para"):
            insert_at = i
            break

    for child in children:
        if child.tag in ("ITEXT", "para"):
            story.remove(child)

    new_itext = ET.Element("ITEXT", carried)
    new_itext.set("CH", text)
    story.insert(insert_at, new_itext)

    # Scribus stories terminate paragraphs with a <para> before <trail>.
    # If a <trail> exists, place the closing <para> right before it; else
    # append the <para> at the end.
    trail = story.find("trail")
    if trail is not None:
        trail_idx = list(story).index(trail)
        story.insert(trail_idx, ET.Element("para"))
    else:
        story.append(ET.Element("para"))


def apply_impressum(sla_path: str | Path, out_path: str | Path, entry: dict) -> int:
    """Substitute the impressum text in every impressum frame of an SLA.

    Parses ``sla_path``, rewrites each impressum-bearing frame's story to a
    single run carrying the Bundesland impressum, and writes ``out_path``.
    Returns the number of frames replaced. Raises ``RuntimeError`` when no
    impressum frame is found.
    """
    tree = ET.parse(str(sla_path))
    root = tree.getroot()

    frames = find_impressum_frames(root)
    if not frames:
        raise RuntimeError(f"no impressum frame found in {sla_path}")

    text = _impressum_text(entry)
    for frame in frames:
        _rewrite_story(frame, text)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(out), encoding="UTF-8", xml_declaration=True)
    return len(frames)


def _process_one(sla: Path, slug: str, data: dict, out_path: Path | None = None) -> Path:
    """Apply one Bundesland to one SLA; return the output path."""
    entry = _entry_for(data, slug)
    if out_path is None:
        out_path = sla.parent / "impressum" / f"{slug}.sla"
    apply_impressum(sla, out_path, entry)
    return out_path


def _run_all(data: dict) -> int:
    """Emit per-Bundesland SLAs for every template. Returns exit code."""
    slugs = [e["slug"] for e in data["bundeslaender"]]
    count = 0
    for tdir in sorted(TEMPLATES_DIR.iterdir()):
        if not tdir.is_dir() or tdir.name.startswith("_"):
            continue
        sla = tdir / "template.sla"
        if not sla.exists():
            continue
        for slug in slugs:
            entry = _entry_for(data, slug)
            out = tdir / "impressum" / f"{slug}.sla"
            n = apply_impressum(sla, out, entry)
            count += 1
            print(f"[impressum] {tdir.name}/{slug}.sla — {n} frame(s)")
    print(f"[impressum] {count} SLA variant(s) written")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    data = load_bundeslaender()
    valid = {e["slug"] for e in data["bundeslaender"]}

    if args == ["--all"]:
        return _run_all(data)

    if len(args) == 2:
        sla = Path(args[0])
        slug = args[1]
        if slug not in valid:
            print(
                f"FATAL: unknown Bundesland slug '{slug}'. "
                f"Known: {', '.join(sorted(valid))}",
                file=sys.stderr,
            )
            return 1
        if not sla.exists():
            print(f"FATAL: SLA not found: {sla}", file=sys.stderr)
            return 1
        out = _process_one(sla, slug, data)
        print(f"[impressum] {out}")
        return 0

    print(
        "usage:\n"
        "  tools/impressum.py --all\n"
        "  tools/impressum.py <template.sla> <bundesland-slug>",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
