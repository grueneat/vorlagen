"""Brand profile — bundles palette, styles, layers, and Scribus defaults.

Pass ``Document(brand=Brand.gruene_noe())`` to inject all brand defaults into
a document without listing them explicitly. The 113 identical extra_doc_attrs
and 34 identical extra_pdf_attrs keys that were duplicated across every
build.py are now a single source of truth here, loaded from shared/ci-defaults.yml.

Templates override individual keys via extra_doc_attrs= / extra_pdf_attrs= on
the Document constructor — per-template values always win over brand defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .ci import BrandColor, BrandStyle, BrandLayer, load_ci, _CI, CI_YAML_DEFAULT
from .styles import DocumentLayer, ParaStyle, CharStyle

ROOT = Path(__file__).resolve().parents[3]
CI_DEFAULTS_YAML = ROOT / "shared" / "ci-defaults.yml"


def _load_brand_ci(ci_path: Path = CI_YAML_DEFAULT,
                   defaults_path: Path = CI_DEFAULTS_YAML) -> "_BrandData":
    """Load ci.yml + ci-defaults.yml and return raw brand data."""
    ci = load_ci(ci_path)
    with open(defaults_path, "r", encoding="utf-8") as f:
        defs = yaml.safe_load(f)
    return _BrandData(ci=ci, raw_defaults=defs)


@dataclass
class _BrandData:
    ci: _CI
    raw_defaults: dict


@dataclass(frozen=True)
class Brand:
    """A brand profile bundling defaults, palette, styles, layers, and Scribus
    document/PDF-export state for a specific publishing brand.

    Pass to ``Document(brand=...)`` to auto-register:
    - Brand colors (from ci.yml)
    - Brand paragraph and character styles (from ci.yml)
    - Brand layer stack (from ci.yml)
    - 113 identical extra_doc_attrs defaults (from ci-defaults.yml)
    - 34 identical extra_pdf_attrs defaults (from ci-defaults.yml)

    Per-template ``extra_doc_attrs`` / ``extra_pdf_attrs`` on ``Document(...)``
    override the brand defaults (brand values are the floor, not the ceiling).

    ``palette_replaces_ci`` is forced to ``True`` when a Brand is supplied so
    the brand's color registry is the sole emitted palette; templates declare
    additions via ``doc.add_color(...)`` which appends to ``_extra_colors``.

    Note: ``frozen=True`` makes the dataclass immutable (no attribute
    assignment after construction), but the dict fields (colors,
    para_styles, etc.) are still mutable Python dicts and prevent direct
    hashing.  Equality (``==``) compares field-by-field as expected.
    """

    name: str
    short: str
    colors: dict[str, BrandColor]
    para_styles: dict[str, ParaStyle]
    char_styles: dict[str, CharStyle]
    layers: list[DocumentLayer]
    default_doc_attrs: dict[str, str]
    default_pdf_attrs: dict[str, str]
    deffont: str = "Gotham Narrow Book"
    defsize: float = 12.0
    column_gap_default_pt: float = 11.0
    bleed_mm: float = 3.0

    @classmethod
    def gruene_noe(
        cls,
        ci_path: Optional[Path] = None,
        defaults_path: Optional[Path] = None,
    ) -> "Brand":
        """Load the Grüne NÖ brand from shared/ci.yml + shared/ci-defaults.yml.

        Both paths are optional — pass them in tests to point at fixtures.
        """
        _ci_path = Path(ci_path) if ci_path else CI_YAML_DEFAULT
        _defs_path = Path(defaults_path) if defaults_path else CI_DEFAULTS_YAML
        bd = _load_brand_ci(_ci_path, _defs_path)
        ci = bd.ci
        defs = bd.raw_defaults

        # Convert BrandColor entries from ci.yml
        colors: dict[str, BrandColor] = dict(ci.colors)

        # Convert BrandStyle entries from ci.yml into ParaStyle objects
        # (only non-None fields are set; PARENT inheritance follows ci.yml)
        _align_map = {0: 0, 1: 1, 2: 2, 3: 3}
        para_styles: dict[str, ParaStyle] = {}
        for sname, bs in ci.styles.items():
            para_styles[sname] = ParaStyle(
                name=sname,
                parent=bs.parent,
                font=bs.font if bs.font else None,
                fontsize=bs.fontsize,
                align=bs.align,
                linesp=bs.linesp,
                fcolor=bs.fcolor,
                language=bs.language,
            )

        # Default character style — empty (falls back to Scribus defaults)
        char_styles: dict[str, CharStyle] = {}

        # Convert BrandLayer entries from ci.yml into DocumentLayer objects
        layers: list[DocumentLayer] = [
            DocumentLayer(
                name=bl.name,
                visible=bl.visible,
                printable=bl.printable,
                editable=bl.editable,
            )
            for bl in ci.layers
        ]

        # Normalize the default attrs: YAML loads None as Python None, but
        # Scribus expects the string "None" for null-sentinel attributes.
        def _normalize(d: dict) -> dict[str, str]:
            return {k: ("None" if v is None else str(v)) for k, v in d.items()}

        default_doc_attrs = _normalize(defs.get("default_doc_attrs", {}))
        default_pdf_attrs = _normalize(defs.get("default_pdf_attrs", {}))

        return cls(
            name=ci.brand_name,
            short=ci.brand_short,
            colors=colors,
            para_styles=para_styles,
            char_styles=char_styles,
            layers=layers,
            default_doc_attrs=default_doc_attrs,
            default_pdf_attrs=default_pdf_attrs,
            deffont="Gotham Narrow Book",
            defsize=12.0,
            column_gap_default_pt=11.0,
            bleed_mm=3.0,
        )
