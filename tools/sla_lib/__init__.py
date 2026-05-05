"""SLA file manipulation library — read, edit, and emit Scribus 1.6 .sla files.

This package provides three layers:

1. :mod:`sla_lib.reader` — :class:`SLADocument` parses an existing .sla and
   exposes pages, page-objects, slots, and helpers. Read-only by intent.
2. :mod:`sla_lib.editor` — :class:`SLAEditor` writes back to a parsed
   document: text-slot replacement (run-preserving where possible), image
   slot replacement, and bulk fill from a slot dict. Used by the legacy
   render pipeline.
3. :mod:`sla_lib.builder` — DSL for emitting new SLA files from scratch.
   Public surface: :class:`Document`, :class:`Page`, :class:`Color`,
   :class:`Style`, primitives :class:`TextFrame`, :class:`ImageFrame`,
   :class:`Polygon`, :class:`Line`, and the :mod:`sla_lib.builder.blocks`
   compose-level blocks.

Brand consistency
-----------------
Templates emitted via the builder reference colors and styles by name from
``shared/ci.yml``. The standalone validator ``tools/check_ci.py`` flags drift
between any SLA and that file, and is the primary safety net against the
RGB-Green-style accidents documented in `.research/01-sla-format.md`.
"""
from .reader import SLADocument
from .slot import Slot, SlotKind

__all__ = ["SLADocument", "Slot", "SlotKind"]
