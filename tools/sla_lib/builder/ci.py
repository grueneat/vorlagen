"""Brand identity loader — reads shared/ci.yml at import time.

The Color and Style classes are runtime-validated enums populated from
shared/ci.yml. Using ``Color.DUNKELGRUEN`` in DSL code is equivalent to the
string ``"Dunkelgrün"`` — the validator (tools/check_ci.py) ensures the SLA
this DSL emits is brand-consistent.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parents[3]
CI_YAML_DEFAULT = ROOT / "shared" / "ci.yml"

# CMYK conversions
def _cmyk_to_rgb(c: float, m: float, y: float, k: float) -> tuple[int, int, int]:
    """Approximate CMYK→RGB for Scribus internal display only.
    Real print uses ICC; we just need *something* in RGB= for SLA fallback."""
    cf, mf, yf, kf = c / 100.0, m / 100.0, y / 100.0, k / 100.0
    r = round(255 * (1 - cf) * (1 - kf))
    g = round(255 * (1 - mf) * (1 - kf))
    b = round(255 * (1 - yf) * (1 - kf))
    return r, g, b


@dataclass(frozen=True)
class BrandColor:
    """A named color. Either ``cmyk`` or ``rgb_native`` is supplied; emitting
    a CMYK color writes ``SPACE="CMYK"`` with C/M/Y/K integer attributes,
    while a native-RGB color writes ``SPACE="RGB"`` with R/G/B integer attrs.
    """
    name: str
    cmyk: tuple[int, int, int, int] = (0, 0, 0, 0)
    spot: bool = False
    register: bool = False
    role: Optional[str] = None
    rgb_native: Optional[tuple[int, int, int]] = None

    @property
    def rgb(self) -> tuple[int, int, int]:
        if self.rgb_native is not None:
            return self.rgb_native
        return _cmyk_to_rgb(*self.cmyk)

    @property
    def cmyk_hex8(self) -> str:
        """Scribus emits CMYK= as 8 hex chars: CCMMYYKK (each 0..ff)."""
        c, m, y, k = self.cmyk
        return f"{round(c * 255 / 100):02x}{round(m * 255 / 100):02x}{round(y * 255 / 100):02x}{round(k * 255 / 100):02x}"


_ALIGN_MAP = {"left": 0, "center": 1, "right": 2, "block": 3, "justify": 3}


@dataclass(frozen=True)
class BrandStyle:
    name: str
    font: str
    fontsize: float
    align: int = 0  # 0=left, 1=center, 2=right, 3=justify
    parent: Optional[str] = None
    linesp: float = 13.0
    fcolor: str = "Black"
    language: str = "de"


@dataclass(frozen=True)
class BrandLayer:
    name: str
    level: int
    visible: bool = True
    printable: bool = True
    editable: bool = True


@dataclass(frozen=True)
class BrandFont:
    name: str


class _CI:
    """Loaded brand identity. Singleton pattern via load_ci()."""

    def __init__(self, path: Path | str = CI_YAML_DEFAULT) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.brand_name: str = data["brand"]["name"]
        self.brand_short: str = data["brand"]["short"]
        self.colors: dict[str, BrandColor] = {}
        for cname, cdata in data["colors"].items():
            self.colors[cname] = BrandColor(
                name=cname,
                cmyk=tuple(cdata["cmyk"]),
                spot=cdata.get("spot", False),
                register=cdata.get("register", False),
                role=cdata.get("role"),
            )
        self.fonts: list[str] = list(data["fonts"])
        self.styles: dict[str, BrandStyle] = {}
        for sname, sdata in data.get("styles", {}).items():
            align_raw = sdata.get("align", 0)
            align = _ALIGN_MAP[align_raw] if isinstance(align_raw, str) else int(align_raw)
            self.styles[sname] = BrandStyle(
                name=sname,
                font=sdata.get("font", ""),
                fontsize=float(sdata.get("fontsize", 12)),
                align=align,
                parent=sdata.get("parent"),
                linesp=float(sdata.get("linesp", 13)),
                fcolor=sdata.get("fcolor", "Black"),
                language=sdata.get("language", "de"),
            )
        self.layers: list[BrandLayer] = []
        for idx, ldata in enumerate(data.get("layers", [])):
            self.layers.append(BrandLayer(
                name=ldata["name"],
                level=idx,
                visible=bool(ldata.get("visible", True)),
                printable=bool(ldata.get("print", ldata.get("printable", True))),
                editable=bool(ldata.get("edit", ldata.get("editable", True))),
            ))


_CACHED: Optional[_CI] = None


def load_ci(path: Path | str = CI_YAML_DEFAULT) -> _CI:
    """Load and cache the brand identity. Pass a different path to override."""
    global _CACHED
    if _CACHED is None:
        _CACHED = _CI(path)
    return _CACHED


# Public enums — populated by attribute access. We expose strings so
# downstream code can use Color.DUNKELGRUEN as the SLA color name directly.
class _ColorEnum:
    """Provides attribute-style access to brand colors as their SLA names."""
    BLACK = "Black"
    WHITE = "White"
    REGISTRATION = "Registration"
    DUNKELGRUEN = "Dunkelgrün"
    HELLGRUEN = "Hellgrün"
    GELB = "Gelb"
    MAGENTA = "Magenta"

    @classmethod
    def all(cls) -> list[str]:
        return [v for k, v in cls.__dict__.items()
                if not k.startswith("_") and isinstance(v, str)]

    @classmethod
    def get(cls, name: str) -> BrandColor:
        return load_ci().colors[name]


class _StyleEnum:
    """Provides attribute-style access to canonical paragraph style names."""
    HEADLINE_ULTRA = "ci/headline-ultra"
    HEADLINE_EMPHASIS = "ci/headline-emphasis"
    BODY_12 = "ci/body-12"
    BODY_11 = "ci/body-11"
    IMPRESSUM = "ci/impressum"
    STOERER = "ci/stoerer"
    CTA = "ci/cta"

    @classmethod
    def all(cls) -> list[str]:
        return [v for k, v in cls.__dict__.items()
                if not k.startswith("_") and isinstance(v, str)]

    @classmethod
    def get(cls, name: str) -> BrandStyle:
        return load_ci().styles[name]


Color = _ColorEnum
Style = _StyleEnum
