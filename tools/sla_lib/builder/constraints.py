"""Free-form constraint predicates (Issue #12, CONTEXT D2/D5).

A Constraint expresses a geometric/style invariant over a set of
already-constructed primitives. Each factory returns an immutable
Constraint that, when evaluated against a ``primitives_by_anname``
mapping, yields zero or more Violation objects.

Resolution model (RESEARCH "Correction to D5"):

- Each factory accepts targets in TWO forms:

  * a primitive instance with ``.anname`` set — the anname is recorded
  * a string — used as the anname directly

- Evaluation looks up each target by anname in the supplied mapping. A
  missing anname yields a Violation with severity="warning" naming
  the missing target — NOT silently skipped (RESEARCH P-INLINE-FRAME).

- This means Constraints survive the construct-then-add convention even
  when the original Frame instance was discarded after build_doc()
  finished — the orchestrator rebuilds the mapping from the saved
  primitives, and lookup uses anname strings only.

No solver. Plain predicates. See RESEARCH §"Don't Hand-Roll" §3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Violation:
    """A single constraint failure.

    severity: "error" | "warning" | "info"
    rule_id : the constraint's id (e.g. "same_y", "inside")
    message : human-readable description
    targets : tuple of anname strings the constraint references
    """

    severity: str
    message: str
    rule_id: str = ""
    targets: tuple = ()


@dataclass(frozen=True)
class Constraint:
    """A predicate over named primitives.

    Subclassing not required — the factories below return one of the
    concrete Constraint subclasses defined in this module (each with
    its own ``check`` implementation).
    """

    id: str
    targets: tuple
    name: str = ""

    def check(self, primitives_by_anname: dict) -> list:
        raise NotImplementedError

    def referenced_annames(self) -> tuple:
        return self.targets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_anname(t) -> str:
    """Normalize a target to its anname string form.

    Accepts a string (returned as-is) or a primitive with ``.anname``.
    """
    if isinstance(t, str):
        return t
    name = getattr(t, "anname", None)
    if name is None or name == "":
        raise ValueError(
            f"Cannot resolve target {t!r} — has no anname. "
            "Set the frame's anname explicitly or pass an anname string."
        )
    return name


def _resolve(targets: tuple, mapping: dict) -> tuple[list, list]:
    """Look up targets in mapping. Returns (resolved_frames, missing_names)."""
    resolved = []
    missing = []
    for t in targets:
        if t not in mapping:
            missing.append(t)
        else:
            resolved.append(mapping[t])
    return resolved, missing


def _missing_violation(rid: str, targets: tuple, missing: list) -> Violation:
    return Violation(
        severity="warning",
        message=f"references missing anname(s): {sorted(missing)}",
        rule_id=rid,
        targets=targets,
    )


# ---------------------------------------------------------------------------
# Concrete Constraint subclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _SameAxisConstraint(Constraint):
    axis: str = "y"
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) < 2:
            return []
        attr = "y_mm" if self.axis == "y" else "x_mm"
        ref = getattr(resolved[0], attr)
        bad = []
        for r in resolved[1:]:
            v = getattr(r, attr)
            if abs(v - ref) > self.tolerance_mm:
                bad.append((r.anname, v))
        if not bad:
            return []
        msg = (
            f"{attr} drift > {self.tolerance_mm}mm; "
            f"reference={ref}, offenders={bad}"
        )
        return [Violation(severity="error", message=msg, rule_id=self.id, targets=self.targets)]


@dataclass(frozen=True)
class _SameSizeConstraint(Constraint):
    axis: str = "both"  # "both" | "w" | "h"
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) < 2:
            return []
        bad: list[tuple] = []
        ref = resolved[0]
        for r in resolved[1:]:
            if self.axis in ("both", "w") and abs(r.w_mm - ref.w_mm) > self.tolerance_mm:
                bad.append((r.anname, "w", r.w_mm, ref.w_mm))
            if self.axis in ("both", "h") and abs(r.h_mm - ref.h_mm) > self.tolerance_mm:
                bad.append((r.anname, "h", r.h_mm, ref.h_mm))
        if not bad:
            return []
        msg = f"size drift > {self.tolerance_mm}mm: {bad}"
        return [Violation(severity="error", message=msg, rule_id=self.id, targets=self.targets)]


@dataclass(frozen=True)
class _MirroredConstraint(Constraint):
    axis: str = "x"  # "x" = vertical mirror line; "y" = horizontal mirror line
    axis_mm: float = 0.0
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) != 2:
            return []
        a, b = resolved
        if self.axis == "x":
            ca = a.x_mm + a.w_mm / 2.0
            cb = b.x_mm + b.w_mm / 2.0
        else:
            ca = a.y_mm + a.h_mm / 2.0
            cb = b.y_mm + b.h_mm / 2.0
        midpoint = (ca + cb) / 2.0
        if abs(midpoint - self.axis_mm) > self.tolerance_mm:
            return [Violation(
                severity="error",
                message=(
                    f"mirror axis drift > {self.tolerance_mm}mm: "
                    f"midpoint={midpoint}, expected={self.axis_mm}"
                ),
                rule_id=self.id,
                targets=self.targets,
            )]
        return []


@dataclass(frozen=True)
class _InsideConstraint(Constraint):
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        child, parent = resolved
        tol = self.tolerance_mm
        cx, cy, cw, ch = child.x_mm, child.y_mm, child.w_mm, child.h_mm
        px, py, pw, ph = parent.x_mm, parent.y_mm, parent.w_mm, parent.h_mm
        if (cx + tol >= px and cy + tol >= py
                and cx + cw <= px + pw + tol
                and cy + ch <= py + ph + tol):
            return []
        return [Violation(
            severity="error",
            message=(
                f"child {child.anname!r} bbox ({cx},{cy},{cw}x{ch}) "
                f"not inside parent {parent.anname!r} bbox "
                f"({px},{py},{pw}x{ph})"
            ),
            rule_id=self.id,
            targets=self.targets,
        )]


@dataclass(frozen=True)
class _EqualGapConstraint(Constraint):
    axis: str = "y"
    gap_mm: float = 0.0
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) < 2:
            return []
        # Sort by axis for stable evaluation; production templates may
        # have constraint-list-targets in any order.
        attr = "y_mm" if self.axis == "y" else "x_mm"
        size_attr = "h_mm" if self.axis == "y" else "w_mm"
        sorted_frames = sorted(resolved, key=lambda f: getattr(f, attr))
        bad = []
        for a, b in zip(sorted_frames, sorted_frames[1:]):
            gap = getattr(b, attr) - (getattr(a, attr) + getattr(a, size_attr))
            if abs(gap - self.gap_mm) > self.tolerance_mm:
                bad.append((a.anname, b.anname, gap))
        if not bad:
            return []
        return [Violation(
            severity="error",
            message=(
                f"gap drift > {self.tolerance_mm}mm "
                f"(expected {self.gap_mm}mm): {bad}"
            ),
            rule_id=self.id,
            targets=self.targets,
        )]


@dataclass(frozen=True)
class _HierarchyConstraint(Constraint):
    by: str = "fontsize"

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) < 2:
            return []
        values = []
        for r in resolved:
            v = getattr(r, self.by, None)
            if v is None:
                # missing attribute → can't compare; treat as failure
                return [Violation(
                    severity="error",
                    message=f"frame {r.anname!r} missing attribute {self.by!r}",
                    rule_id=self.id,
                    targets=self.targets,
                )]
            values.append(float(v))
        for a, b in zip(values, values[1:]):
            if not (a > b):
                return [Violation(
                    severity="error",
                    message=(
                        f"hierarchy by {self.by!r} not strictly descending: "
                        f"{values}"
                    ),
                    rule_id=self.id,
                    targets=self.targets,
                )]
        return []


@dataclass(frozen=True)
class _SameStyleConstraint(Constraint):
    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        if len(resolved) < 2:
            return []
        ref = getattr(resolved[0], "style", None)
        bad = [(r.anname, getattr(r, "style", None)) for r in resolved[1:]
               if getattr(r, "style", None) != ref]
        if not bad:
            return []
        return [Violation(
            severity="error",
            message=f"style drift: reference={ref!r}, offenders={bad}",
            rule_id=self.id,
            targets=self.targets,
        )]


@dataclass(frozen=True)
class _DistanceConstraint(Constraint):
    axis: str = "y"
    equals: float = 0.0
    tolerance_mm: float = 0.5

    def check(self, primitives_by_anname: dict) -> list:
        resolved, missing = _resolve(self.targets, primitives_by_anname)
        if missing:
            return [_missing_violation(self.id, self.targets, missing)]
        a, b = resolved
        attr = "y_mm" if self.axis == "y" else "x_mm"
        d = abs(getattr(b, attr) - getattr(a, attr))
        if abs(d - self.equals) > self.tolerance_mm:
            return [Violation(
                severity="error",
                message=(
                    f"distance_{self.axis} drift > {self.tolerance_mm}mm: "
                    f"actual={d}, expected={self.equals}"
                ),
                rule_id=self.id,
                targets=self.targets,
            )]
        return []


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------
def _norm(targets) -> tuple:
    return tuple(_to_anname(t) for t in targets)


def _autoname(kind: str, targets: tuple, name: str) -> str:
    if name:
        return f"{kind}:{name}"
    return f"{kind}:{','.join(targets)}"


def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint:
    """All targets must share the same y_mm within tolerance."""
    t = _norm(targets)
    return _SameAxisConstraint(
        id=_autoname("same_y", t, name), targets=t, name=name,
        axis="y", tolerance_mm=tolerance_mm,
    )


def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint:
    """All targets must share the same x_mm within tolerance."""
    t = _norm(targets)
    return _SameAxisConstraint(
        id=_autoname("same_x", t, name), targets=t, name=name,
        axis="x", tolerance_mm=tolerance_mm,
    )


def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5,
              name: str = "") -> Constraint:
    """All targets must share the same width and/or height within tolerance.

    axis="both" requires both w and h match; axis="w" only width;
    axis="h" only height.
    """
    if axis not in ("both", "w", "h"):
        raise ValueError(f"same_size axis must be 'both', 'w', 'h'; got {axis!r}")
    t = _norm(targets)
    return _SameSizeConstraint(
        id=_autoname(f"same_size_{axis}", t, name), targets=t, name=name,
        axis=axis, tolerance_mm=tolerance_mm,
    )


def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5,
               name: str = "") -> Constraint:
    """Left and right's center-x average to ``axis_mm`` within tolerance."""
    t = _norm((left, right))
    return _MirroredConstraint(
        id=_autoname("mirrored_x", t, name), targets=t, name=name,
        axis="x", axis_mm=axis_mm, tolerance_mm=tolerance_mm,
    )


def mirrored_y(top, bottom, axis_mm: float, tolerance_mm: float = 0.5,
               name: str = "") -> Constraint:
    """Top and bottom's center-y average to ``axis_mm`` within tolerance."""
    t = _norm((top, bottom))
    return _MirroredConstraint(
        id=_autoname("mirrored_y", t, name), targets=t, name=name,
        axis="y", axis_mm=axis_mm, tolerance_mm=tolerance_mm,
    )


def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint:
    """Child's bbox is contained within parent's bbox (within tolerance)."""
    t = _norm((child, parent))
    return _InsideConstraint(
        id=_autoname("inside", t, name), targets=t, name=name,
        tolerance_mm=tolerance_mm,
    )


def equal_gap(*targets, axis: str = "y", gap_mm: float, tolerance_mm: float = 0.5,
              name: str = "") -> Constraint:
    """Consecutive gaps between sorted targets equal ``gap_mm`` within tolerance."""
    t = _norm(targets)
    return _EqualGapConstraint(
        id=_autoname(f"equal_gap_{axis}", t, name), targets=t, name=name,
        axis=axis, gap_mm=gap_mm, tolerance_mm=tolerance_mm,
    )


def hierarchy(*targets, by: str = "fontsize", name: str = "") -> Constraint:
    """Targets in declared order have strictly descending ``by`` attribute."""
    t = _norm(targets)
    return _HierarchyConstraint(
        id=_autoname(f"hierarchy_{by}", t, name), targets=t, name=name,
        by=by,
    )


def same_style(*targets, name: str = "") -> Constraint:
    """All targets share an identical ``.style`` attribute."""
    t = _norm(targets)
    return _SameStyleConstraint(
        id=_autoname("same_style", t, name), targets=t, name=name,
    )


def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint:
    """``|a.y_mm - b.y_mm|`` equals ``equals`` within tolerance."""
    t = _norm((a, b))
    return _DistanceConstraint(
        id=_autoname("distance_y", t, name), targets=t, name=name,
        axis="y", equals=equals, tolerance_mm=tolerance_mm,
    )


def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint:
    """``|a.x_mm - b.x_mm|`` equals ``equals`` within tolerance."""
    t = _norm((a, b))
    return _DistanceConstraint(
        id=_autoname("distance_x", t, name), targets=t, name=name,
        axis="x", equals=equals, tolerance_mm=tolerance_mm,
    )
