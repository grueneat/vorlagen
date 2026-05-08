"""Composite blocks for constraint-by-construction (Issue #12, CONTEXT D1).

A composite is a layout intent expressed as a *constructor* — its emit()
method yields the children with their layout-defining coordinate forced
to a single value (so the constraint holds *by construction*, not by
post-hoc validation). Free-form predicates in ``constraints.py`` cover
the cases that don't naturally express as a composite.

Hard rules:

- Children are NEVER mutated. Each composite uses ``dataclasses.replace``
  to produce a *new* frame instance with the layout-defining field
  overridden (RESEARCH P-COMPOSITE-MUTATION).
- emit() signature matches ``blocks.py`` (yields primitives via a
  generator; ``Page.add`` flushes the generator at insertion time).
- A composite may emit zero or more children depending on whether a
  child is None (HierarchyBlock allows None subline / body). Composites
  do NOT inject Polygon/background frames; they only pass through their
  inputs.
- Composites operate on dataclass primitives (TextFrame, ImageFrame,
  Polygon — all subclassing _Frame). They work on any dataclass with
  the relevant field; no isinstance check.

This module is intentionally separate from ``blocks.py`` (RESEARCH
P-COMPOSITE-NAMING). ``blocks.py`` contains evidence-driven *content*
blocks (PageNumber, Impressum, ...) that emit canonical frame
arrangements. Composites are *layout-arrangement* helpers that are
agnostic of content.

No constraint solver. No kiwisolver. No z3. Predicates only — see
RESEARCH §"Don't Hand-Roll" §3.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# AlignedRow / AlignedColumn
# ---------------------------------------------------------------------------
@dataclass
class AlignedRow:
    """Force every child to share the same y_mm.

    Use case: rows of belege, rows of panel-headers, table-of-contents
    bars. Children's heights, widths, x positions, and styles are NOT
    touched — only y_mm.

    Empty children list yields nothing.
    """

    y_mm: float = 0.0
    children: list = field(default_factory=list)
    name: str = ""

    def emit(self, page=None) -> Iterable:
        for child in self.children:
            yield dataclasses.replace(child, y_mm=self.y_mm)


@dataclass
class AlignedColumn:
    """Force every child to share the same x_mm.

    Use case: stacked panel-elements that must stay in a vertical
    column.
    """

    x_mm: float = 0.0
    children: list = field(default_factory=list)
    name: str = ""

    def emit(self, page=None) -> Iterable:
        for child in self.children:
            yield dataclasses.replace(child, x_mm=self.x_mm)


# ---------------------------------------------------------------------------
# MirroredPair
# ---------------------------------------------------------------------------
@dataclass
class MirroredPair:
    """Yield (left, right) where right is repositioned so its center
    mirrors left's center across an axis.

    axis="x" means a vertical mirror line at x = ``axis_mm``: the
    center-x of left and the center-x of right average to ``axis_mm``.

    axis="y" means a horizontal mirror line at y = ``axis_mm``: the
    center-y of left and the center-y of right average to ``axis_mm``.

    Width/height/style of right are NOT touched — only the position
    along the mirror axis. The other-axis position of right is also
    left untouched (mirror is one-axial; pair the composite with
    ``same_y`` / ``same_x`` from constraints.py if needed).
    """

    left: object = None
    right: object = None
    axis_mm: float = 0.0
    axis: str = "x"  # "x" = vertical mirror line; "y" = horizontal mirror line
    name: str = ""

    def emit(self, page=None) -> Iterable:
        if self.left is None or self.right is None:
            return
        if self.axis not in ("x", "y"):
            raise ValueError(f"MirroredPair.axis must be 'x' or 'y', got {self.axis!r}")
        yield self.left
        if self.axis == "x":
            # vertical mirror line at axis_mm; new right.x so centers average
            # to axis_mm: new_x + w/2 = 2*axis_mm - (left.x + left.w/2)
            new_x = (
                2 * self.axis_mm
                - (self.left.x_mm + self.left.w_mm / 2.0)
                - self.right.w_mm / 2.0
            )
            yield dataclasses.replace(self.right, x_mm=new_x)
        else:
            # horizontal mirror line at axis_mm
            new_y = (
                2 * self.axis_mm
                - (self.left.y_mm + self.left.h_mm / 2.0)
                - self.right.h_mm / 2.0
            )
            yield dataclasses.replace(self.right, y_mm=new_y)


# ---------------------------------------------------------------------------
# EqualGapStack
# ---------------------------------------------------------------------------
@dataclass
class EqualGapStack:
    """Stack children along an axis with a uniform gap between consecutive
    children.

    axis="y" stacks vertically: child[i].y_mm = start + sum(prev.h_mm + gap).
    axis="x" stacks horizontally: child[i].x_mm = start + sum(prev.w_mm + gap).

    The non-stack-axis position is left untouched.
    """

    gap_mm: float = 0.0
    children: list = field(default_factory=list)
    axis: str = "y"
    start_mm: float = 0.0
    name: str = ""

    def emit(self, page=None) -> Iterable:
        if self.axis not in ("x", "y"):
            raise ValueError(f"EqualGapStack.axis must be 'x' or 'y', got {self.axis!r}")
        cursor = self.start_mm
        for child in self.children:
            if self.axis == "y":
                yield dataclasses.replace(child, y_mm=cursor)
                cursor += child.h_mm + self.gap_mm
            else:
                yield dataclasses.replace(child, x_mm=cursor)
                cursor += child.w_mm + self.gap_mm


# ---------------------------------------------------------------------------
# GridSpec / GridCell
# ---------------------------------------------------------------------------
@dataclass
class GridSpec:
    """Compute (x, y, w, h) of a cell on an N-column M-row grid.

    Margin is the outer padding (page edge to grid). Gutter is the gap
    between cells. ``page_w_mm`` / ``page_h_mm`` define the outer extents.

    A cell at (row, col) with optional spans returns top-left x/y plus
    width/height covering the spanned columns/rows including inner
    gutters.
    """

    cols: int = 1
    rows: int = 1
    gutter_mm: float = 10.0
    margin_mm: float = 12.0
    page_w_mm: float = 0.0
    page_h_mm: float = 0.0

    def cell_xy(
        self,
        row: int,
        col: int,
        span_cols: int = 1,
        span_rows: int = 1,
    ) -> tuple[float, float, float, float]:
        if self.cols < 1 or self.rows < 1:
            raise ValueError("GridSpec.cols and rows must be >= 1")
        if not (0 <= col < self.cols) or not (0 <= row < self.rows):
            raise ValueError(f"GridSpec cell ({row},{col}) out of range "
                             f"({self.rows}x{self.cols})")
        usable_w = self.page_w_mm - 2 * self.margin_mm - (self.cols - 1) * self.gutter_mm
        usable_h = self.page_h_mm - 2 * self.margin_mm - (self.rows - 1) * self.gutter_mm
        cell_w = usable_w / self.cols
        cell_h = usable_h / self.rows
        x = self.margin_mm + col * (cell_w + self.gutter_mm)
        y = self.margin_mm + row * (cell_h + self.gutter_mm)
        w = span_cols * cell_w + (span_cols - 1) * self.gutter_mm
        h = span_rows * cell_h + (span_rows - 1) * self.gutter_mm
        return (x, y, w, h)


@dataclass
class GridCell:
    """Place a child inside a GridSpec cell, forcing x/y/w/h to match.

    Note: Width/height are forced too — this is intentional. A grid
    placement IS a sizing decision. If the caller wants to keep the
    child's intrinsic w/h, use plain frame placement, not GridCell.
    """

    grid: GridSpec = None  # type: ignore[assignment]
    row: int = 0
    col: int = 0
    child: object = None
    span_cols: int = 1
    span_rows: int = 1
    name: str = ""

    def emit(self, page=None) -> Iterable:
        if self.child is None or self.grid is None:
            return
        x, y, w, h = self.grid.cell_xy(self.row, self.col, self.span_cols, self.span_rows)
        yield dataclasses.replace(self.child, x_mm=x, y_mm=y, w_mm=w, h_mm=h)


# ---------------------------------------------------------------------------
# HierarchyBlock
# ---------------------------------------------------------------------------
@dataclass
class HierarchyBlock:
    """Emit headline + optional subline + optional body in declared order.

    Validates fontsize order if both endpoints' fontsizes are
    resolvable (the head's fontsize > sub's fontsize > body's fontsize).
    Raises ValueError on bad order. Frames without a fontsize attribute
    (e.g. ImageFrame) skip the check.

    None for subline or body is allowed — partial hierarchies (e.g.
    headline-only) emit just the present frames.
    """

    headline: object = None
    subline: Optional[object] = None
    body: Optional[object] = None
    name: str = ""

    @staticmethod
    def _fontsize(frame) -> Optional[float]:
        if frame is None:
            return None
        # Many TextFrames carry .fontsize; ParaStyle attaches one too.
        fs = getattr(frame, "fontsize", None)
        if fs is None:
            return None
        try:
            return float(fs)
        except (TypeError, ValueError):
            return None

    def emit(self, page=None) -> Iterable:
        present = [f for f in (self.headline, self.subline, self.body) if f is not None]
        # Validate fontsize order on resolvable pairs only.
        sizes = [self._fontsize(f) for f in present]
        # Check strict-descending where both neighbors have a fontsize.
        for a, b in zip(sizes, sizes[1:]):
            if a is not None and b is not None and not (a > b):
                raise ValueError(
                    f"HierarchyBlock fontsize order violated: "
                    f"{a} > {b} expected (got {a} <= {b})"
                )
        for f in present:
            yield f
