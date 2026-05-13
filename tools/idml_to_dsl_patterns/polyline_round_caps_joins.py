"""Map IDML EndCap / EndJoin to Scribus PLINEEND / PLINEJOIN.

IDML names (e.g. "RoundEndCap") -> Scribus integer values that the
sla_lib.builder.PolyLine primitive understands (Qt::PenCapStyle and
Qt::PenJoinStyle).

Default values (ButtEndCap=0, MiterEndJoin=0) are omitted by the
converter on purpose — Scribus's PolyLine emits the absence of the
attribute as the default, so emitting "0" would produce noise in the SLA.
"""
from __future__ import annotations

from .base import Pattern


CAP_MAP: dict[str, int] = {
    "ButtEndCap": 0,
    "ProjectingEndCap": 16,
    "RoundEndCap": 32,
}

JOIN_MAP: dict[str, int] = {
    "MiterEndJoin": 0,
    "BevelEndJoin": 64,
    "RoundEndJoin": 128,
}


class PolylineRoundCapsJoins:
    id = "polyline_round_caps_joins"
    description = "Map IDML EndCap/EndJoin to Scribus PLINEEND/PLINEJOIN"
    applies_to = "PolyLine"

    def matches(self, idml_element) -> bool:
        if not hasattr(idml_element, "get"):
            return False
        return bool(
            idml_element.get("EndCap") in CAP_MAP
            or idml_element.get("EndJoin") in JOIN_MAP
        )

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        if not hasattr(idml_element, "get"):
            return
        end_cap = idml_element.get("EndCap", "")
        end_join = idml_element.get("EndJoin", "")
        if end_cap in CAP_MAP and CAP_MAP[end_cap] != 0:
            kwargs["line_cap"] = CAP_MAP[end_cap]
        if end_join in JOIN_MAP and JOIN_MAP[end_join] != 0:
            kwargs["line_join"] = JOIN_MAP[end_join]
