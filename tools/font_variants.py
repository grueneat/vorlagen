#!/usr/bin/env python3
"""SLA post-processor that swaps the Gotham Narrow font family for a free
SIL-OFL alternative — modelled on tools/impressum.py.

The flyer template references four proprietary Gotham Narrow weights via
``FONT="…"`` attributes (on ``ITEXT`` runs and in ``STYLE``/``CHARSTYLE``
definitions). This tool rewrites every such reference to the matching weight
of a chosen alternative family, leaving the other proprietary font
(``Minion Pro Regular``) and the already-free ``Vollkorn Black Italic``
untouched. The substitution is purely textual: frame geometry, page layout
and styles are otherwise unchanged.

Target weight names are ``"<family> <weight>"`` — e.g. ``Montserrat ExtraBold``
— which is how fontconfig exposes the static instances of the variable fonts
(and the static Barlow files). tools/fonts_compare_build.py installs the
fonts and, where needed, a fontconfig alias so the renderer resolves them.

CLI:
  python3 tools/font_variants.py --all
      For flyer-a6-hochformat-gruenes-cover/template.sla emit one variant SLA
      per alternative under
      templates/flyer-a6-hochformat-gruenes-cover/fonts/<slug>/<slug>.sla.
  python3 tools/font_variants.py <sla> <font-slug>
      Single case — writes <sla-dir>/fonts/<slug>/<slug>.sla.

Idempotent: a second run produces a byte-identical SLA, so no spurious git
diff.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "shared" / "fonts" / "alternatives.yml"
TEMPLATES_DIR = ROOT / "templates"

# Only these four families are swapped. Minion Pro Regular and Vollkorn Black
# Italic are intentionally left in place (see RESEARCH.md §3 / CONTEXT.md D3).
_GOTHAM_PREFIX = "Gotham Narrow "

# Attributes that carry a font-family reference. FONT is used on ITEXT runs
# and STYLE/CHARSTYLE definitions; DFONT is the DOCUMENT element's default
# font. Both must be remapped or the variant SLA keeps a Gotham reference.
_FONT_ATTRS = ("FONT", "DFONT")


def load_alternatives(path: str | Path | None = None) -> dict:
    """Load the font alternatives data source.

    Returns ``{"target": str, "flyer": str, "fonts": [<entry>, ...]}``.
    Default path: ``<repo>/shared/fonts/alternatives.yml``. Raises
    ``RuntimeError`` if the file is missing required keys.
    """
    p = Path(path) if path is not None else DATA_PATH
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "fonts" not in data:
        raise RuntimeError(f"invalid font alternatives data source: {p}")
    return data


def _entry_for(data: dict, slug: str) -> dict:
    """Resolve a font entry by slug."""
    by_slug = {e["slug"]: e for e in data["fonts"]}
    if slug not in by_slug:
        known = ", ".join(sorted(by_slug))
        raise RuntimeError(f"unknown font slug '{slug}'. Known: {known}")
    return by_slug[slug]


def _weight_map(font_entry: dict) -> dict[str, str]:
    """Build the ``"Gotham Narrow <w>" -> "<family> <replacement>"`` map."""
    family = font_entry["family"]
    out: dict[str, str] = {}
    for gotham_weight, replacement in font_entry["weights"].items():
        out[f"{_GOTHAM_PREFIX}{gotham_weight}"] = f"{family} {replacement}"
    return out


def apply_font(
    sla_path: str | Path, out_path: str | Path, font_entry: dict
) -> int:
    """Rewrite every Gotham Narrow font reference in an SLA to ``font_entry``.

    Parses ``sla_path``, replaces the value of every ``FONT`` attribute (on
    any element — ``ITEXT``, ``STYLE``, ``CHARSTYLE``, …) and the document's
    ``DFONT`` default-font attribute whose value starts with
    ``"Gotham Narrow "`` with the mapped ``"<family> <weight>"`` name, and
    writes ``out_path``. ``Minion Pro Regular`` and ``Vollkorn Black Italic``
    references are not matched and stay untouched.

    Returns the number of font references replaced. Raises ``RuntimeError``
    when none were found (the template carries no Gotham Narrow text).
    """
    tree = ET.parse(str(sla_path))
    root = tree.getroot()

    mapping = _weight_map(font_entry)
    replaced = 0
    for el in root.iter():
        for attr in _FONT_ATTRS:
            value = el.get(attr)
            if value is None or not value.startswith(_GOTHAM_PREFIX):
                continue
            new_value = mapping.get(value)
            if new_value is None:
                # A Gotham Narrow weight the data source does not map.
                # Surface it rather than silently leaving a proprietary
                # reference behind.
                raise RuntimeError(
                    f"unmapped Gotham Narrow weight '{value}' "
                    f"in {sla_path} — extend weights for '{font_entry['slug']}'"
                )
            el.set(attr, new_value)
            replaced += 1

    if replaced == 0:
        raise RuntimeError(f"no Gotham Narrow font reference found in {sla_path}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(out), encoding="UTF-8", xml_declaration=True)
    return replaced


def variant_sla_path(template_sla: Path, slug: str) -> Path:
    """Return the variant SLA path for a template SLA and a font slug."""
    return template_sla.parent / "fonts" / slug / f"{slug}.sla"


def comparison_base(data: dict, root: Path = ROOT) -> Path:
    """Resolve the base SLA the alternatives are swapped *from*.

    The font comparison measures the free alternatives against the original
    Gotham Narrow flyer. Production ``template.sla`` has since been switched to
    Barlow Semi Condensed (Issue c8bg0), so the comparison pins its own frozen
    Gotham baseline via the ``base`` key in alternatives.yml. Falls back to the
    flyer's ``template.sla`` when no ``base`` is given (legacy / pre-swap).
    """
    if data.get("base"):
        return root / data["base"]
    return TEMPLATES_DIR / data["flyer"] / "template.sla"


def _process_one(
    sla: Path, slug: str, data: dict, out_path: Path | None = None
) -> Path:
    """Apply one alternative font to one SLA; return the output path."""
    entry = _entry_for(data, slug)
    if out_path is None:
        out_path = variant_sla_path(sla, slug)
    n = apply_font(sla, out_path, entry)
    print(f"[font_variants] {out_path} — {n} reference(s)")
    return out_path


def _run_all(data: dict) -> int:
    """Emit one variant SLA per alternative from the frozen comparison base."""
    flyer = data["flyer"]
    base = comparison_base(data)
    anchor = TEMPLATES_DIR / flyer / "template.sla"
    if not base.exists():
        print(f"FATAL: comparison base SLA not found: {base}", file=sys.stderr)
        return 1
    for entry in data["fonts"]:
        out = variant_sla_path(anchor, entry["slug"])
        _process_one(base, entry["slug"], data, out_path=out)
    print(f"[font_variants] {len(data['fonts'])} variant SLA(s) written")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    data = load_alternatives()
    valid = {e["slug"] for e in data["fonts"]}

    if args == ["--all"]:
        return _run_all(data)

    if len(args) == 2:
        sla = Path(args[0])
        slug = args[1]
        if slug not in valid:
            print(
                f"FATAL: unknown font slug '{slug}'. "
                f"Known: {', '.join(sorted(valid))}",
                file=sys.stderr,
            )
            return 1
        if not sla.exists():
            print(f"FATAL: SLA not found: {sla}", file=sys.stderr)
            return 1
        _process_one(sla, slug, data)
        return 0

    print(
        "usage:\n"
        "  tools/font_variants.py --all\n"
        "  tools/font_variants.py <template.sla> <font-slug>",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
