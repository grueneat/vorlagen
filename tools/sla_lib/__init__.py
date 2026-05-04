"""SLA file manipulation library — read, edit, and write Scribus 1.6 .sla files."""
from .reader import SLADocument
from .slot import Slot, SlotKind

__all__ = ["SLADocument", "Slot", "SlotKind"]
