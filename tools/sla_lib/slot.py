from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class SlotKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass
class Slot:
    """A named placeholder in a template, identified by ANNAME prefix.

    Convention: ANNAME = "<kind>:<id>" where kind is `text` or `image`.
    Frames without this prefix are not slots and remain untouched.
    """
    kind: SlotKind
    name: str
    page: int
    x_pt: float
    y_pt: float
    w_pt: float
    h_pt: float
    ptype: str
    item_id: str

    @classmethod
    def from_anname(cls, anname: str) -> tuple[SlotKind, str] | None:
        if ":" not in anname:
            return None
        prefix, _, sid = anname.partition(":")
        try:
            return SlotKind(prefix), sid
        except ValueError:
            return None
