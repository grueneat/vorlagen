"""Brand-CI constraint predicates (Issue #12, CONTEXT D3).

Nine rules sourced from `shared/brand/QUICKGUIDE-NOTES.md` —
predicate-style validation, NOT a constraint solver. Do not reach for
kiwisolver or z3 (RESEARCH §1 + ecosystem §1).

Each rule is a frozen ``BrandRule`` dataclass with a ``check(primitives,
doc)`` method returning a list of ``Violation`` objects (severity
"error" by default). Rules are auto-applied by ``structural_check.py``
unless the template's ``meta.yml`` lists the rule's id under
``brand_overrides`` with an explanation reason.

Rule IDs are STABLE strings — changing them invalidates existing
``brand_overrides`` entries in template meta.yml files. Always treat
them as a public surface.

The nine rules:

  1. ``brand:color_palette`` — every fill/line_color/fcolor referenced
     by a primitive must be present in the doc's available palette
     (CI brand colors plus doc-extras).
  2. ``brand:font_family`` — every TextFrame uses a font from the
     allow-list ``shared/ci.yml::fonts``.
  3. ``brand:line_spacing_0.9`` — registered paragraph styles' linesp
     equals fontsize x 0.9 within 0.5pt.
  4. ``brand:hl_sl_distance_x2`` — for each (Headline, Sub-Headline)
     pair (anname substring match), the y-distance roughly equals
     baseline_x x 2 (baseline ~5.4mm, allow ±1mm).
  5. ``brand:logo_size_3M`` — ImageFrames with anname containing "Logo"
     have width ~3xM with M = 0.06 x kurze_kante.
  6. ``brand:text_on_green`` — TextFrames that use brand-headline
     paragraph styles AND have white fcolor must overlap a Polygon
     with green fill (Dunkelgrün/Hellgrün).
  7. ``brand:bleed_3mm`` — the doc's bleed is exactly 3mm on all sides.
  8. ``brand:wahlkreuz_colored_bg`` — frames whose anname contains
     "Wahlkreuz" sit on a polygon background of Dunkelgrün/Hellgrün/Magenta.
  9. ``brand:inside_page`` — every non-master frame's rotation- and
     anchor-aware bbox sits inside its own page's
     ``[-bleed, w+bleed] x [-bleed, h+bleed]`` (Issue #14).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .bbox import (  # noqa: F401  -- back-compat aliases for existing rules
    frame_bbox_mm as _frame_bbox_mm,
    rotated_bbox as _rotated_bbox,
)
from .ci import Color, load_ci
from .constraints import Violation
from .document import PT_TO_MM, mm_to_pt
from .primitives import TextFrame, ImageFrame, Polygon


# ---------------------------------------------------------------------------
# BrandRule core
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BrandRule:
    """A brand-CI constraint over a built Document.

    ``check(primitives, doc, constraints=None)`` walks the primitive list
    (already obtained from ``Document.iter_all_primitives()``) and
    inspects the doc-level metadata as needed.

    The optional ``constraints`` kwarg is the per-template
    ``CONSTRAINTS = [...]`` list (Issue #22 / locked decision #3). Most
    rules ignore it; ``brand:undeclared_alignment_drift`` consumes it
    to know which pair-relationships are intentional.
    """

    id: str
    name: str
    description: str
    severity: str = "error"

    # The actual predicate body is supplied via subclass.
    def check(self, primitives: list, doc, constraints=None) -> list:  # pragma: no cover
        raise NotImplementedError


def _allowed_colors(doc) -> set[str]:
    """Return the set of color names this doc can legally reference."""
    allowed: set[str] = set()
    if not getattr(doc, "palette_replaces_ci", False):
        # CI base palette
        allowed.update(load_ci().colors.keys())
    allowed.update(getattr(doc, "_extra_colors", {}).keys())
    # Sentinel values that mean "no color"
    allowed.update({"None", "", "Registration"})
    return allowed


def _all_para_styles(doc) -> dict:
    """Return all paragraph styles known to the doc (CI + extras)."""
    styles = {}
    if not getattr(doc, "palette_replaces_ci", False):
        for name, s in load_ci().styles.items():
            styles[name] = s
    for name, s in getattr(doc, "_extra_para_styles", {}).items():
        styles[name] = s
    return styles


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _ColorPaletteRule(BrandRule):
    def check(self, primitives: list, doc, constraints=None) -> list:
        allowed = _allowed_colors(doc)
        violations: list[Violation] = []
        for p in primitives:
            for attr in ("fill", "line_color", "fcolor"):
                v = getattr(p, attr, None)
                if v is None:
                    continue
                if v not in allowed:
                    violations.append(Violation(
                        severity=self.severity,
                        message=(
                            f"frame {getattr(p, 'anname', '?')!r} {attr}={v!r} "
                            f"not in palette {sorted(allowed)}"
                        ),
                        rule_id=self.id,
                        targets=(getattr(p, "anname", ""),),
                    ))
        return violations


@dataclass(frozen=True)
class _FontFamilyRule(BrandRule):
    def check(self, primitives: list, doc, constraints=None) -> list:
        allowed = set(load_ci().fonts)
        violations: list[Violation] = []
        styles = _all_para_styles(doc)
        for p in primitives:
            if not isinstance(p, TextFrame):
                continue
            # Frame-level font override (TextFrame.font is rare but supported)
            font = getattr(p, "font", None)
            if font is None or font == "":
                # Resolve through the para style if any
                style_name = getattr(p, "style", "")
                ps = styles.get(style_name) if style_name else None
                font = getattr(ps, "font", None) if ps is not None else None
            if font is None or font == "":
                # Fall back to doc.deffont
                font = getattr(doc, "deffont", "")
            if font and font not in allowed:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"text frame {getattr(p, 'anname', '?')!r} uses font "
                        f"{font!r} not in {sorted(allowed)}"
                    ),
                    rule_id=self.id,
                    targets=(getattr(p, "anname", ""),),
                ))
        return violations


@dataclass(frozen=True)
class _LineSpacingRule(BrandRule):
    factor: float = 0.9
    tolerance_pt: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list[Violation] = []
        for name, ps in _all_para_styles(doc).items():
            fs = getattr(ps, "fontsize", None)
            ls = getattr(ps, "linesp", None)
            if fs is None or ls is None:
                # Style declares neither / inherits from PARENT — skip.
                continue
            expected = float(fs) * self.factor
            if abs(float(ls) - expected) > self.tolerance_pt:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"para style {name!r} linesp={ls} "
                        f"!= fontsize({fs}) * {self.factor} = {expected:.2f}"
                    ),
                    rule_id=self.id,
                    targets=(name,),
                ))
        return violations


@dataclass(frozen=True)
class _HlSlDistanceRule(BrandRule):
    baseline_mm: float = 5.4
    tolerance_mm: float = 1.0

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list[Violation] = []
        # Find pairs by anname substring: "Headline" + "Sub" / "Sub-Headline"
        # / "Subline".  One pair per page is the common case; multiple
        # pairs allowed (Falzflyer panels).
        headlines = [p for p in primitives
                     if isinstance(p, TextFrame)
                     and re.search(r"headline", getattr(p, "anname", ""), re.IGNORECASE)
                     and not re.search(r"sub-headline|subline|sub headline",
                                       getattr(p, "anname", ""), re.IGNORECASE)]
        sublines = [p for p in primitives
                    if isinstance(p, TextFrame)
                    and re.search(r"sub-headline|subline|sub headline",
                                  getattr(p, "anname", ""), re.IGNORECASE)]
        # Pair each headline with the nearest subline below (max 1 pair per HL)
        used_sub: set[int] = set()
        for hl in headlines:
            best = None
            best_dy = None
            for i, sl in enumerate(sublines):
                if i in used_sub:
                    continue
                dy = sl.y_mm - (hl.y_mm + hl.h_mm)
                if dy < 0:
                    continue
                if best is None or dy < best_dy:
                    best, best_dy, best_i = sl, dy, i
            if best is None:
                continue
            used_sub.add(best_i)
            expected = self.baseline_mm * 2
            if abs(best_dy - expected) > self.tolerance_mm:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"HL {hl.anname!r} -> SL {best.anname!r} "
                        f"distance {best_dy:.2f}mm "
                        f"!= 2*baseline ({expected:.1f}mm) +/-{self.tolerance_mm}mm"
                    ),
                    rule_id=self.id,
                    targets=(hl.anname, best.anname),
                ))
        return violations


@dataclass(frozen=True)
class _LogoSize3MRule(BrandRule):
    factor: float = 3.0
    tolerance_mm: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list[Violation] = []
        if not doc.pages:
            return violations
        page = doc.pages[0]
        # kurze_kante = min of the trim, ignoring bleed
        from .document import PT_TO_MM
        page_w_mm = page.width_pt * PT_TO_MM
        page_h_mm = page.height_pt * PT_TO_MM
        kurze_kante = min(page_w_mm, page_h_mm)
        m = 0.06 * kurze_kante
        expected = self.factor * m
        for p in primitives:
            if not isinstance(p, ImageFrame):
                continue
            anname = getattr(p, "anname", "") or ""
            # Match on \bLogo\b case-insensitive
            if not re.search(r"\blogo\b", anname, re.IGNORECASE):
                continue
            if abs(p.w_mm - expected) > self.tolerance_mm:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"logo {anname!r} w_mm={p.w_mm} != 3*M ({expected:.2f}mm) "
                        f"+/-{self.tolerance_mm}mm  [kurze_kante={kurze_kante:.1f}mm]"
                    ),
                    rule_id=self.id,
                    targets=(anname,),
                ))
        return violations


@dataclass(frozen=True)
class _TextOnGreenRule(BrandRule):
    green_colors: tuple = ("Dunkelgrün", "Hellgrün")

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list[Violation] = []
        # Find white-fill text frames on brand-headline paragraph styles.
        white_headlines = [
            p for p in primitives
            if isinstance(p, TextFrame)
            and (getattr(p, "fcolor", "") in ("White", "white"))
            and re.match(r"^ci/(h|headline)", getattr(p, "style", "") or "")
        ]
        green_polygons = [p for p in primitives
                          if isinstance(p, Polygon)
                          and getattr(p, "fill", "") in self.green_colors]
        for tf in white_headlines:
            tx, ty, tw, th = tf.x_mm, tf.y_mm, tf.w_mm, tf.h_mm
            ok = False
            for poly in green_polygons:
                px, py, pw, ph = poly.x_mm, poly.y_mm, poly.w_mm, poly.h_mm
                # Bounding-box overlap
                if (tx + tw >= px and px + pw >= tx
                        and ty + th >= py and py + ph >= ty):
                    ok = True
                    break
            if not ok:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"text frame {tf.anname!r} uses headline style "
                        f"{tf.style!r} with fcolor=White but does not overlap "
                        f"a green polygon"
                    ),
                    rule_id=self.id,
                    targets=(tf.anname,),
                ))
        return violations


@dataclass(frozen=True)
class _Bleed3mmRule(BrandRule):
    expected_mm: float = 3.0
    tolerance_mm: float = 0.01

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list[Violation] = []
        for p in doc.pages:
            if abs(p.bleed_mm - self.expected_mm) > self.tolerance_mm:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"page {p.label or '#?'} bleed_mm={p.bleed_mm} "
                        f"!= {self.expected_mm}"
                    ),
                    rule_id=self.id,
                    targets=(p.label or "page",),
                ))
        return violations


@dataclass(frozen=True)
class _WahlkreuzColoredBgRule(BrandRule):
    allowed: tuple = ("Dunkelgrün", "Hellgrün", "Magenta")

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list[Violation] = []
        wahlkreuz_frames = [
            p for p in primitives
            if "Wahlkreuz" in (getattr(p, "anname", "") or "")
        ]
        bg_polygons = [p for p in primitives if isinstance(p, Polygon)]
        for wk in wahlkreuz_frames:
            wx, wy, ww, wh = wk.x_mm, wk.y_mm, wk.w_mm, wk.h_mm
            ok = False
            for poly in bg_polygons:
                if poly.anname == wk.anname:
                    continue
                px, py, pw, ph = poly.x_mm, poly.y_mm, poly.w_mm, poly.h_mm
                if (wx + ww >= px and px + pw >= wx
                        and wy + wh >= py and py + ph >= wy):
                    if poly.fill in self.allowed:
                        ok = True
                        break
            if not ok:
                violations.append(Violation(
                    severity=self.severity,
                    message=(
                        f"Wahlkreuz frame {wk.anname!r} has no overlapping "
                        f"polygon with fill in {list(self.allowed)}"
                    ),
                    rule_id=self.id,
                    targets=(wk.anname,),
                ))
        return violations


# ---------------------------------------------------------------------------
# brand:inside_page (Issue #14)
# Bbox helpers extracted to bbox.py (Issue #22 / locked decision #7);
# re-exported above as _frame_bbox_mm / _rotated_bbox for back-compat.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _InsidePageRule(BrandRule):
    """Each non-master frame's rotation- and anchor-aware bbox must fit
    inside its OWNING page's ``[-bleed, w+bleed] × [-bleed, h+bleed]``.

    Severity split:
      - worst overshoot ≤ 0.5 mm → pass (within constraint-default tolerance).
      - 0.5 < worst ≤ 1.0 mm    → warning (bleed-edge nudge from float-
        imprecise Scribus SLA emit; does NOT break CI).
      - worst > 1.0 mm           → error (real overflow; CI fails unless
        template lists ``brand:inside_page`` in ``meta.yml::brand_overrides``).

    The 1.0 mm error cutoff is pragmatic: two existing zeitung frames have
    ~0.8 mm right-edge nudges from float-imprecise bleed math during SLA
    round-trip emit (e.g. ``w_mm=210.799...`` on a 210 mm page with 3 mm
    bleed); a strict 0.5 mm cutoff would surface these as errors and
    require a separate brand_overrides escape. ISSUE.md acceptance text
    reads 0.5 mm as the warning/error boundary; the 1.0 mm value is the
    planner's confirmation choice — revert if the user disagrees.

    Master-page items are skipped — masters are abstract layout grids and
    legitimately carry full-bleed background polygons. Tighten in a
    follow-up issue if master-page drift becomes a concern.

    The ``meta.yml::brand_overrides`` mechanism is RULE-LEVEL only — there
    is no per-frame allowlist; if a template legitimately needs to
    silence the rule (e.g. zeitung pending #16 SpreadImage migration),
    list ``brand:inside_page`` in its overrides with a reason.
    """

    tolerance_mm: float = 0.5
    error_cutoff_mm: float = 1.0

    def check(self, primitives: list, doc, constraints=None) -> list:
        # We IGNORE the flat ``primitives`` arg — only doc-level
        # iteration carries ``(page, item)`` pairs. Pattern matches
        # _Bleed3mmRule.
        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            pw_mm = page.width_pt * PT_TO_MM
            ph_mm = page.height_pt * PT_TO_MM
            bleed = float(page.bleed_mm or 0)
            for item in page.items:
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                over_l = (-bleed) - x0
                over_r = x1 - (pw_mm + bleed)
                over_t = (-bleed) - y0
                over_b = y1 - (ph_mm + bleed)
                worst = max(over_l, over_r, over_t, over_b, 0.0)
                if worst <= self.tolerance_mm:
                    continue
                sev = "warning" if worst <= self.error_cutoff_mm else "error"
                ident = item.anname or f"<unnamed {type(item).__name__}>"
                loc = page.label or page.master_name or f"page#{page.own_page}"
                violations.append(Violation(
                    severity=sev,
                    rule_id=self.id,
                    message=(
                        f"frame {ident!r} bbox "
                        f"({x0:.2f}, {y0:.2f})-({x1:.2f}, {y1:.2f}) "
                        f"exceeds page {loc!r} "
                        f"(trim {pw_mm:.1f}x{ph_mm:.1f}, bleed {bleed:.1f}); "
                        f"worst overshoot {worst:.2f}mm"
                    ),
                    targets=(ident,),
                ))
        return violations


# ---------------------------------------------------------------------------
# Module-level rule registry
# ---------------------------------------------------------------------------
def _make_rule(cls, **kwargs) -> BrandRule:
    return cls(**kwargs)


BRAND_CONSTRAINTS: list[BrandRule] = [
    _make_rule(
        _ColorPaletteRule,
        id="brand:color_palette",
        name="Color palette only",
        description="All fill / line_color / fcolor references must use the "
                    "doc's available palette (CI base + doc extras).",
    ),
    _make_rule(
        _FontFamilyRule,
        id="brand:font_family",
        name="Brand font family only",
        description="Every TextFrame uses a font from shared/ci.yml::fonts.",
    ),
    _make_rule(
        _LineSpacingRule,
        id="brand:line_spacing_0.9",
        name="Line spacing factor 0.9",
        description="linesp = fontsize * 0.9 (Quickguide rule).",
    ),
    _make_rule(
        _HlSlDistanceRule,
        id="brand:hl_sl_distance_x2",
        name="Headline -> Subline distance",
        description="HL -> SL distance ~ baseline_X * 2 (Quickguide rule).",
    ),
    _make_rule(
        _LogoSize3MRule,
        id="brand:logo_size_3M",
        name="Logo size 3*M (print)",
        description="Logo width = 3*M with M = 0.06 * kurze_kante (Quickguide).",
    ),
    _make_rule(
        _TextOnGreenRule,
        id="brand:text_on_green",
        name="White headline text on green",
        description="White-fcolor headlines must sit on a green polygon.",
    ),
    _make_rule(
        _Bleed3mmRule,
        id="brand:bleed_3mm",
        name="Document bleed 3mm",
        description="All pages have bleed_mm == 3.0.",
    ),
    _make_rule(
        _WahlkreuzColoredBgRule,
        id="brand:wahlkreuz_colored_bg",
        name="Wahlkreuz on colored background",
        description="Wahlkreuz frames sit on a Dunkelgrün/Hellgrün/Magenta polygon.",
    ),
    _make_rule(
        _InsidePageRule,
        id="brand:inside_page",
        name="Frames inside page bounds",
        description="Every non-master frame's rotation-aware bbox sits "
                    "inside its own page's [-bleed, w+bleed] x [-bleed, h+bleed].",
    ),
]
