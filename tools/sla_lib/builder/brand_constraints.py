"""Brand-CI constraint predicates (Issue #12 + #14 + #22 + #23).

Predicate-style validation, NOT a constraint solver. Do not reach for
kiwisolver or z3 (RESEARCH §1 + ecosystem §1).

Each rule is a frozen ``BrandRule`` dataclass with a
``check(primitives, doc, constraints=None)`` method returning a list
of ``Violation`` objects (severity "error" by default). Rules are
auto-applied by ``structural_check.py`` unless the template's
``meta.yml`` lists the rule's id under ``brand_overrides`` with an
explanation reason.

Rule IDs are STABLE strings — changing them invalidates existing
``brand_overrides`` entries in template meta.yml files. Always treat
them as a public surface.

The sixteen rules (post-#25):

  1. ``brand:color_palette``
  2. ``brand:font_family``
  3. ``brand:line_spacing_0.9``
  4. ``brand:hl_sl_distance_x2``
  5. ``brand:logo_size_3M``
  6. ``brand:text_on_green``
  7. ``brand:bleed_3mm``
  8. ``brand:wahlkreuz_colored_bg``
  9. ``brand:inside_page`` (Issue #14)
 10. ``brand:spine_safety`` (Issue #22)
 11. ``brand:bleed_coverage`` (Issue #23) — full-width frames must
     extend to outer bleed on facing-pages docs.
 12. ``brand:image_text_overlap`` (Issue #23) — text and
     image/filled-polygon must not partially overlap.
 13. ``brand:cover_extent_match`` (Issue #23) — vertically touching
     full-width frames must share outer-bbox extents.
 14. ``brand:visual_adjacency_drift`` (Issue #23) — replaces
     brand:undeclared_alignment_drift from #22 with 4-axis checks
     (left/right/top/bottom) plus declaration-disagreement detection.
 15. ``brand:image_fills_frame`` (Issue #24) — INJECT_MAP target drift
     and aspect-mismatch letterboxing.
 16. ``brand:band_consistency`` (Issue #25) — body-pool pages confine
     content to header/free/footer bands and L/R margins per
     meta.yml::body_block_margins (the unified body-pool model).
"""
from __future__ import annotations

import itertools
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
    rules ignore it; ``brand:visual_adjacency_drift`` consumes it to
    know which pair-relationships are intentional AND to re-execute
    each declaration against the actual geometry to detect declarations
    that disagree with their own tolerance (Issue #23 locked decision #5).
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
# brand:spine_safety (Issue #22)
# ---------------------------------------------------------------------------
SPINE_SAFETY_INSET_MM = 3.0

# Side detector for facing-pages templates. ``Page.is_left`` is hardcoded
# False on doc pages (document.py:391-393), so we MUST detect side via
# ``master_name``. Word-boundary regex avoids substring false matches on
# future template names. Case-insensitive so "Links"/"Rechts"/"LINKS" all
# work.
SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)

# SpreadImage halves intentionally touch the spine (each half is a
# full-page-width frame at x=0 on its own page). The blocks.SpreadImage
# emitter names them ``<base> · left`` / ``<base> · right`` (middle-dot
# ' · '). NOTE: do NOT reuse this anname suffix for non-SpreadImage
# frames — the rule will erroneously skip them.
SPREAD_HALF_RX = re.compile(r" · (left|right)$")


@dataclass(frozen=True)
class _SpineSafetyRule(BrandRule):
    """Spine-safety on facing-pages docs.

    On a facing-pages document, a non-SpreadImage frame whose spine-side
    edge is within ``inset_mm`` of the spine causes Scribus's bleed to
    leak across the spine into the facing page. This rule warns so the
    template author can either inset the frame or migrate to
    ``SpreadImage`` for an intentional spread.

    Side detection: ``master_name`` regex ``\\b(links|rechts)\\b`` (case
    insensitive). ``Page.is_left`` is broken (hardcoded False at
    ``document.py:391-393``) — DO NOT use it.

    Scope:
      - Single-page docs (``facing_pages=False``) → no-op (early return).
      - Master pages → skipped.
      - Frames with spread-half anname suffix (`` · left``/`` · right``)
        → skipped (intentional spread).
      - Pages with master_name not matching either side → ONE warning
        per such page (so the bug surfaces, but doesn't silently skip).

    Severity = warning (heuristic; the user may intentionally bleed
    backgrounds across the spine via SpreadImage). Per-template opt-out
    via ``meta.yml::brand_overrides[brand:spine_safety]``.
    """

    inset_mm: float = SPINE_SAFETY_INSET_MM
    tolerance_mm: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        # Early exit: spine-safety only matters on facing-pages docs.
        if not getattr(doc, "facing_pages", False):
            return []
        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            # Skip the cover page (own_page == 0). In facing-pages mode
            # Scribus's PageSet "Facing Pages" with FirstPage=1 places
            # page 0 ALONE in the right column (verified at
            # document.py:376-378). With no facing left page, a spine-
            # touching frame on the cover doesn't leak anywhere.
            if page.own_page == 0:
                continue
            m = SIDE_RX.search(page.master_name or "")
            if not m:
                loc = (page.label or page.master_name
                       or f"page#{page.own_page}")
                violations.append(Violation(
                    severity="warning",
                    rule_id=self.id,
                    message=(
                        f"page {loc!r} uses master_name "
                        f"{page.master_name!r} which does not match "
                        f"'links'/'rechts'; spine-safety could not be "
                        f"evaluated"
                    ),
                    targets=(page.master_name or "",),
                ))
                continue
            side = m.group(1).lower()
            pw_mm = page.width_pt * PT_TO_MM
            for item in page.items:
                anname = getattr(item, "anname", "") or ""
                # Exempt SpreadImage halves — intentional spine touch.
                if SPREAD_HALF_RX.search(anname):
                    continue
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, _y0, x1, _y1 = bbox
                if side == "links":
                    # LEFT page: spine is on the right (x = pw_mm).
                    gap = pw_mm - x1
                    if gap < self.inset_mm - self.tolerance_mm:
                        ident = anname or f"<unnamed {type(item).__name__}>"
                        violations.append(Violation(
                            severity="warning",
                            rule_id=self.id,
                            message=(
                                f"frame {ident!r} on LEFT page "
                                f"{page.master_name!r} has right edge "
                                f"x={x1:.2f}mm within "
                                f"{self.inset_mm:.1f}mm of spine "
                                f"(page_w={pw_mm:.2f}mm); Scribus bleed "
                                f"will leak across to the facing RIGHT "
                                f"page. Use SpreadImage if intentional, "
                                f"or inset the frame's right edge by "
                                f">={self.inset_mm:.1f}mm."
                            ),
                            targets=(ident,),
                        ))
                else:  # "rechts"
                    # RIGHT page: spine is on the left (x = 0).
                    if x0 < self.inset_mm - self.tolerance_mm:
                        ident = anname or f"<unnamed {type(item).__name__}>"
                        violations.append(Violation(
                            severity="warning",
                            rule_id=self.id,
                            message=(
                                f"frame {ident!r} on RIGHT page "
                                f"{page.master_name!r} has left edge "
                                f"x={x0:.2f}mm within "
                                f"{self.inset_mm:.1f}mm of spine; "
                                f"Scribus bleed will leak across to the "
                                f"facing LEFT page. Use SpreadImage if "
                                f"intentional, or inset the frame's left "
                                f"edge by >={self.inset_mm:.1f}mm."
                            ),
                            targets=(ident,),
                        ))
        return violations


# ---------------------------------------------------------------------------
# brand:bleed_coverage (Issue #23)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _BleedCoverageRule(BrandRule):
    """Outer-edge bleed coverage on facing-pages documents.

    For each non-master page, identifies *full-width* frames
    (``w >= full_width_threshold * page_w``) that are not
    anchor-positioned, not rotated, and not SpreadImage halves. Each
    must extend to its OUTER bleed edge:

      - LEFT page  (master_name contains "links"):  ``x0 <= -bleed + tol``
      - RIGHT page (master_name contains "rechts"): ``x1 >= page_w + bleed - tol``
      - COVER       (own_page == 0): both edges treated as outer.

    Severity = ``error`` — leaving a white margin on the outer edge
    after print cut is a print-cut hazard.

    Locked decision #1: cutoff is 0.95 * page_w (NOT 0.7 from ISSUE.md).
    0.7 produces 19 false positives on Zeitung (the body grid at
    20mm margin = 0.81 ratio). 0.95 dissolves the per-frame
    ``(no-bleed)`` exemption tag — interior margin polygons (e.g.
    Zeitung u918, w/page=0.81) fall below the cutoff naturally.

    Skips:
      - Single-page docs (``facing_pages=False``) → early return.
      - Master pages.
      - SpreadImage halves (anname suffix `` · left``/`` · right``).
      - Rotated frames (rotation != 0).
      - Anchor-positioned frames.
      - Pages whose master_name doesn't match links/rechts (cover handled
        via own_page=0 special-case; other unknown sides are
        spine_safety's territory).

    Per-template opt-out via ``meta.yml::brand_overrides[brand:bleed_coverage]``.
    """

    full_width_threshold: float = 0.95   # locked decision #1
    tolerance_mm: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        if not getattr(doc, "facing_pages", False):
            return []
        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            own_page = getattr(page, "own_page", None)
            m = SIDE_RX.search(page.master_name or "")
            pw_mm = page.width_pt * PT_TO_MM
            bleed = float(page.bleed_mm or 0)
            for item in page.items:
                anname = getattr(item, "anname", "") or (
                    f"<unnamed {type(item).__name__} "
                    f"y={getattr(item, 'y_mm', 0):.1f}>"
                )
                # SpreadImage halves are spread-intentional.
                if SPREAD_HALF_RX.search(anname):
                    continue
                if float(getattr(item, "rotation_deg", 0) or 0) != 0:
                    continue
                if getattr(item, "anchor", None) is not None:
                    continue
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, _y0, x1, _y1 = bbox
                w = x1 - x0
                if w < self.full_width_threshold * pw_mm:
                    continue   # not full-width
                if own_page == 0:
                    # Cover (own_page=0): RIGHT-alone, both edges outer.
                    if x0 > -bleed + self.tolerance_mm:
                        violations.append(self._mk_violation(
                            "LEFT (cover)", anname, page,
                            x0, x0 - (-bleed), -bleed,
                        ))
                    if x1 < pw_mm + bleed - self.tolerance_mm:
                        violations.append(self._mk_violation(
                            "RIGHT (cover)", anname, page,
                            x1, (pw_mm + bleed) - x1, pw_mm + bleed,
                        ))
                    continue
                if not m:
                    # spine_safety emits its own unknown-side warning.
                    continue
                side = m.group(1).lower()
                if side == "links":
                    if x0 > -bleed + self.tolerance_mm:
                        violations.append(self._mk_violation(
                            "LEFT", anname, page,
                            x0, x0 - (-bleed), -bleed,
                        ))
                else:  # rechts
                    if x1 < pw_mm + bleed - self.tolerance_mm:
                        violations.append(self._mk_violation(
                            "RIGHT", anname, page,
                            x1, (pw_mm + bleed) - x1, pw_mm + bleed,
                        ))
        return violations

    def _mk_violation(self, side, anname, page, actual, drift, expected):
        loc = page.label or page.master_name or f"page#{page.own_page}"
        return Violation(
            severity="error",
            rule_id=self.id,
            message=(
                f"frame {anname!r} on {side} page {loc!r}: outer edge at "
                f"{actual:.2f}mm but should be at {expected:.2f}mm "
                f"(missing {drift:.2f}mm of bleed coverage). Either fix "
                f"geometry to extend to outer bleed OR add to "
                f"meta.yml::brand_overrides[brand:bleed_coverage] with reason."
            ),
            targets=(anname,),
        )


# ---------------------------------------------------------------------------
# brand:image_text_overlap (Issue #23)
# ---------------------------------------------------------------------------
# Fills considered "filled polygons" for overlap-with-text purposes.
# Decorative outlines (None / "" / "Black") are NOT in scope.
FILLED_POLYGON_FILLS = ("Dunkelgrün", "Hellgrün", "Magenta", "Gelb")


@dataclass(frozen=True)
class _ImageTextOverlapRule(BrandRule):
    """Text and image/filled-polygon must not partially overlap.

    For each non-master page, iterates every (shape, text) pair where
    *shape* is either an ``ImageFrame`` or a filled ``Polygon`` (fill
    in ``FILLED_POLYGON_FILLS``). Allowed configurations:

      - Zero overlap (disjoint bounding boxes).
      - Text fully contained in shape (caption-on-photo).
      - Shape fully contained in text (drop-cap; rare).

    Forbidden: any partial overlap (text crossing the shape boundary).

    Severity = ``error``.

    Locked decision #2: scope MUST include filled Polygons. The
    documented page-10 Zeitung bug is Polygon×Text (Dunkelgrün card
    overlapping body-text columns). Limiting to ImageFrame would miss
    the documented case.

    Per-template opt-out via
    ``meta.yml::brand_overrides[brand:image_text_overlap]`` for
    templates with intentional decorative overlaps.
    """

    tolerance_mm: float = 0.1

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            shapes: list = []
            texts: list = []
            for item in page.items:
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                if isinstance(item, ImageFrame):
                    shapes.append((item, bbox, "image"))
                elif (isinstance(item, Polygon)
                        and getattr(item, "fill", None)
                        in FILLED_POLYGON_FILLS):
                    shapes.append((item, bbox, "filled-polygon"))
                elif isinstance(item, TextFrame):
                    texts.append((item, bbox))
            for shape, sbox, kind in shapes:
                sx0, sy0, sx1, sy1 = sbox
                for txt, tbox in texts:
                    tx0, ty0, tx1, ty1 = tbox
                    ox0 = max(sx0, tx0)
                    oy0 = max(sy0, ty0)
                    ox1 = min(sx1, tx1)
                    oy1 = min(sy1, ty1)
                    if (ox1 - ox0 <= self.tolerance_mm
                            or oy1 - oy0 <= self.tolerance_mm):
                        continue
                    txt_inside = (
                        sx0 - self.tolerance_mm <= tx0
                        and tx1 <= sx1 + self.tolerance_mm
                        and sy0 - self.tolerance_mm <= ty0
                        and ty1 <= sy1 + self.tolerance_mm
                    )
                    shape_inside = (
                        tx0 - self.tolerance_mm <= sx0
                        and sx1 <= tx1 + self.tolerance_mm
                        and ty0 - self.tolerance_mm <= sy0
                        and sy1 <= ty1 + self.tolerance_mm
                    )
                    if txt_inside or shape_inside:
                        continue
                    txt_name = getattr(txt, "anname", "") or "<unnamed text>"
                    shape_name = (getattr(shape, "anname", "")
                                  or f"<unnamed {kind}>")
                    loc = (page.label or page.master_name
                           or f"page#{page.own_page}")
                    violations.append(Violation(
                        severity="error",
                        rule_id=self.id,
                        message=(
                            f"text {txt_name!r} partially overlaps {kind} "
                            f"{shape_name!r} on page {loc!r}: intersection "
                            f"{ox1-ox0:.1f}x{oy1-oy0:.1f}mm. Either contain "
                            f"text fully inside, move out, or shrink shape."
                        ),
                        targets=(txt_name, shape_name),
                    ))
        return violations


# ---------------------------------------------------------------------------
# brand:cover_extent_match (Issue #23)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _CoverExtentMatchRule(BrandRule):
    """Vertically touching full-width frames must share outer-bbox extents.

    For each non-master page, for each pair of *full-width* frames
    (``w >= full_width_threshold * page_w``) whose bounding boxes
    vertically touch (one's bottom == other's top within
    ``touch_tolerance_mm``), assert their outer-bbox extents match
    (left edges within ``extent_tolerance_mm`` AND right edges within
    ``extent_tolerance_mm``).

    Severity = ``warning`` initially per ISSUE.md "WARNING initially,
    ERROR after audit". Issue #23 keeps WARNING; promote in follow-up.

    Catches the page-1 Zeitung bug: ``Cover Hero`` (x=0..210) shares
    its top edge with ``u2950`` (Dunkelgrün band, x=-3..213) but their
    outer extents differ → 3mm white margin appears at the cut.
    """

    full_width_threshold: float = 0.95
    touch_tolerance_mm: float = 0.5
    extent_tolerance_mm: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            pw_mm = page.width_pt * PT_TO_MM
            wide: list = []
            for item in page.items:
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, _y0, x1, _y1 = bbox
                if (x1 - x0) >= self.full_width_threshold * pw_mm:
                    wide.append((item, bbox))
            for i, (a_item, abox) in enumerate(wide):
                for b_item, bbox in wide[i + 1:]:
                    ax0, ay0, ax1, ay1 = abox
                    bx0, by0, bx1, by1 = bbox
                    touch = (
                        abs(ay1 - by0) < self.touch_tolerance_mm
                        or abs(by1 - ay0) < self.touch_tolerance_mm
                    )
                    if not touch:
                        continue
                    if (abs(ax0 - bx0) <= self.extent_tolerance_mm
                            and abs(ax1 - bx1) <= self.extent_tolerance_mm):
                        continue
                    a_n = (getattr(a_item, "anname", "")
                           or f"<unnamed {type(a_item).__name__}>")
                    b_n = (getattr(b_item, "anname", "")
                           or f"<unnamed {type(b_item).__name__}>")
                    loc = (page.label or page.master_name
                           or f"page#{page.own_page}")
                    violations.append(Violation(
                        severity="warning",
                        rule_id=self.id,
                        message=(
                            f"frames {a_n!r} (x:{ax0:.1f}..{ax1:.1f}) and "
                            f"{b_n!r} (x:{bx0:.1f}..{bx1:.1f}) touch "
                            f"vertically on page {loc!r} but their outer-"
                            f"bbox extents differ. Either make them share "
                            f"extents (left+right) OR override via meta.yml."
                        ),
                        targets=(a_n, b_n),
                    ))
        return violations


# ---------------------------------------------------------------------------
# brand:visual_adjacency_drift (Issue #23, replaces #22's
# brand:undeclared_alignment_drift)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _VisualAdjacencyDriftRule(BrandRule):
    """Heuristic detector for undeclared visual adjacency — 4-axis.

    Replaces #22's brand:undeclared_alignment_drift with broader
    detection (locked decisions #3 + #5):

      - **4-axis** drift checks (dx_left, dx_right, dy_top, dy_bottom)
        instead of just (dx_left, dy_top). Catches the Zeitung
        page-8 right-edge mismatch invisible to the prior rule.
      - **Declaration-disagreement detection**: rather than silently
        dropping pairs that appear in CONSTRAINTS, the rule re-runs
        ``c.check(primitives_by_anname)`` on each declaration. If the
        constraint's own tolerance is breached by actual geometry,
        the rule emits "declaration ... disagrees with actual geometry"
        — breaking the encode-and-silence escape (the constraint's
        own tolerance becomes the audit boundary).

    Default thresholds:
      - axis_drift_min_mm   = 0.5  (avoid float-noise warnings)
      - axis_drift_max_mm   = 25.0 (was 5.0 — page-8 5.6mm missed)
      - adjacency_gap_min_mm = 0.5
      - adjacency_gap_max_mm = 30.0 (was 12.0)

    Severity = ``warning`` (heuristic; can false-positive). Per-template
    opt-out via ``meta.yml::brand_overrides[brand:visual_adjacency_drift]``.

    Skips:
      - Master pages.
      - Primitives without anname.
      - Rotated frames (rotation_deg != 0).
    """

    axis_drift_min_mm: float = 0.5
    axis_drift_max_mm: float = 25.0
    adjacency_gap_min_mm: float = 0.5
    adjacency_gap_max_mm: float = 30.0

    def check(self, primitives: list, doc, constraints=None) -> list:
        constraints = constraints or []
        # Build declared-pair → list-of-constraints map. We need the
        # actual declarations (not just frozenset membership) so the
        # disagreement check can re-execute each constraint.
        declared: dict = {}
        for c in constraints:
            try:
                names = [n for n in c.referenced_annames() if n]
            except Exception:
                continue
            if len(names) < 2:
                continue
            for a, b in itertools.combinations(names, 2):
                if a != b:
                    declared.setdefault(frozenset((a, b)), []).append(c)

        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            spatial = []
            for item in page.items:
                an = getattr(item, "anname", "") or ""
                if not an:
                    continue
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                if float(getattr(item, "rotation_deg", 0) or 0) != 0:
                    continue
                spatial.append((an, item, bbox))

            for i, (pa, p_item, pbox) in enumerate(spatial):
                for qa, q_item, qbox in spatial[i + 1:]:
                    px0, py0, px1, py1 = pbox
                    qx0, qy0, qx1, qy1 = qbox
                    pair_key = frozenset((pa, qa))
                    pair_decls = declared.get(pair_key, [])

                    if pair_decls:
                        # Disagreement check: re-run each declaration
                        # against the actual primitives. If the
                        # constraint's own tolerance is breached, surface
                        # a warning. This breaks encode-and-silence at
                        # the declaration's tolerance boundary.
                        primitives_by_anname = {pa: p_item, qa: q_item}
                        for c in pair_decls:
                            try:
                                inner_viols = c.check(primitives_by_anname)
                            except Exception:
                                inner_viols = []
                            for iv in inner_viols:
                                violations.append(Violation(
                                    severity="warning",
                                    rule_id=self.id,
                                    message=(
                                        f"declaration "
                                        f"{getattr(c, 'name', c.id)!r} for "
                                        f"pair ({pa!r}, {qa!r}) disagrees "
                                        f"with actual geometry: {iv.message}. "
                                        f"Either fix declaration or fix "
                                        f"geometry."
                                    ),
                                    targets=(pa, qa),
                                ))
                        # Don't ALSO fire heuristic on declared pairs.
                        continue

                    # 4-axis heuristic checks (locked decision #3).
                    dx_left = abs(px0 - qx0)
                    dx_right = abs(px1 - qx1)
                    dy_top = abs(py0 - qy0)
                    dy_bottom = abs(py1 - qy1)
                    fired = False
                    for axis_label, drift, suggested in (
                        ("axis-x-left", dx_left,
                         "same_x (left edges)"),
                        ("axis-x-right", dx_right,
                         "same_x_right (right edges)"),
                        ("axis-y-top", dy_top,
                         "same_y (top edges)"),
                        ("axis-y-bottom", dy_bottom,
                         "same_y_bottom (bottom edges)"),
                    ):
                        if (self.axis_drift_min_mm < drift
                                < self.axis_drift_max_mm):
                            violations.append(self._mk(
                                pa, qa, axis_label, drift, suggested,
                            ))
                            fired = True
                            break
                    if fired:
                        continue
                    # Stacked-adjacency: P above Q with small gap,
                    # sharing left or right edge.
                    if py1 < qy0:
                        gap = qy0 - py1
                        if (self.adjacency_gap_min_mm < gap
                                < self.adjacency_gap_max_mm
                                and (dx_left < self.axis_drift_max_mm
                                     or dx_right < self.axis_drift_max_mm)):
                            violations.append(self._mk(
                                pa, qa, "adjacency-y", gap, "aligned_below",
                            ))
        return violations

    def _mk(self, pa, qa, kind, drift, suggested):
        return Violation(
            severity="warning",
            rule_id=self.id,
            message=(
                f"frames {pa!r} and {qa!r} appear visually adjacent "
                f"({kind} drift {drift:.2f}mm). Either declare "
                f"{suggested}({pa!r}, {qa!r}, ...) in CONSTRAINTS, "
                f"OR fix geometry to share the axis."
            ),
            targets=(pa, qa),
        )


# ---------------------------------------------------------------------------
# brand:image_fills_frame (Issue #24)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _ImageFillsFrameRule(BrandRule):
    """Image content fills frame extent.

    Catches the regression class where an ImageFrame's rendered-content
    extent (computed from ``scale_type`` + ``local_scale`` + asset native
    dims via PIL or qCompress decode) is smaller than the frame's outer
    extent — leaving white pillarbox/letterbox margins inside the frame.

    Two failure modes:

      1. INJECT_MAP target drift (the post-#22/#23 Zeitung regression
         class): ``library.inject_into_frame`` was called with a
         ``target_w_mm/target_h_mm`` smaller than the actual
         ``frame.w_mm/h_mm`` (e.g. literal target tuples that drifted
         out of sync after a frame-extent edit). The cropped JPEG
         renders at the OLD target size; the frame's outer N mm shows
         frame ``fill`` (white).
      2. Aspect-mismatch letterboxing on ``scale_type=1, ratio=1``
         frames: Scribus computes ``s = min(frame_w/native_w,
         frame_h/native_h)`` (qMin) and centers; aspect-mismatched
         assets leave white margins on the long axis.

    Severity: ``error`` if the frame's rotation-aware bbox touches the
    page bleed (``±bleed`` on any edge), else ``warning``. The bleed-
    touching variant is visible after print cut and counts as a fatal
    print defect; interior letterboxing is visible but recoverable in
    review.

    Skips:
      - Master pages (no rendered content).
      - Image-less frames (``not (item.image or item.src or
        item.inline_image_data)``) — solid-fill polygons-as-frames.
        The 3 unnamed Dunkelgrün polygons on Zeitung pages 12/13/14 +
        any other template's image-less ImageFrame.
      - ``scale_type=1, ratio=0`` (stretch fills exactly — no letterbox
        possible).

    Tolerance: ``max(tolerance_mm, tolerance_ratio_pct/100 *
    max(item.w_mm, item.h_mm))`` — 1% of the long side, floor 0.5 mm.

    Per-template skip via
    ``meta.yml::brand_overrides[brand:image_fills_frame]``.
    """

    tolerance_ratio_pct: float = 1.0   # 1% of longer frame side
    tolerance_mm: float = 0.5          # absolute floor
    # On scale_type=0, the user can deliberately render an asset at a
    # non-unity ``local_scale`` to inset it inside a larger frame
    # (e.g. icons/logos in an oversized hit-area). The "image fills
    # frame" expectation only applies when the user did NOT manually
    # downscale via local_scale. Frames whose effective local_scale
    # diverges from 1.0 by more than this fraction are exempted.
    # ``inject_into_frame`` always leaves local_scale=(1.0, 1.0) so
    # the INJECT_MAP-drift class is unaffected by this carve.
    nonunity_local_scale_threshold: float = 0.05

    def check(self, primitives: list, doc, constraints=None) -> list:
        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            for item in page.items:
                if not isinstance(item, ImageFrame):
                    continue
                # SKIP image-less ImageFrames (solid-fill polygons-as-
                # frames). Per locked decision #3 (Issue #24).
                has_image = bool(
                    item.image or item.src
                    or getattr(item, "inline_image_data", None)
                )
                if not has_image:
                    continue
                # SKIP frames where the user explicitly downscaled via
                # local_scale (e.g. icons in oversized hit-areas, logos
                # at intentional inset). The "fills frame" expectation
                # only applies when local_scale ~ 1.0, which is exactly
                # what ``inject_into_frame`` produces.
                if item.scale_type == 0:
                    scx, scy = item.local_scale
                    thr = self.nonunity_local_scale_threshold
                    if (abs(scx - 1.0) > thr or abs(scy - 1.0) > thr):
                        continue
                aw_px, ah_px, dpi = self._resolve_asset(item, doc)
                if aw_px is None:
                    violations.append(self._asset_warning(item))
                    continue
                rw, rh = self._rendered_extent_mm(item, aw_px, ah_px, dpi)
                if rw is None:
                    # scale_type=1, ratio=0 (stretch) — fills exactly.
                    continue
                gap_w = item.w_mm - rw
                gap_h = item.h_mm - rh
                long_side = max(item.w_mm, item.h_mm)
                tol = max(
                    self.tolerance_mm,
                    self.tolerance_ratio_pct / 100.0 * long_side,
                )
                if gap_w <= tol and gap_h <= tol:
                    continue
                bbox = _frame_bbox_mm(item, page)
                pw_mm = page.width_pt * PT_TO_MM
                ph_mm = page.height_pt * PT_TO_MM
                bleed = float(getattr(page, "bleed_mm", None) or 3.0)
                sev = (
                    "error"
                    if self._is_full_bleed(bbox, bleed, pw_mm, ph_mm)
                    else "warning"
                )
                ident = (item.anname
                         or f"<unnamed y={item.y_mm:.1f}>")
                violations.append(Violation(
                    rule_id=self.id,
                    severity=sev,
                    targets=(ident,),
                    message=(
                        f"frame {item.anname!r} "
                        f"({item.w_mm:.1f}x{item.h_mm:.1f}mm) renders "
                        f"{rw:.1f}x{rh:.1f}mm — "
                        f"{gap_w:.1f}x{gap_h:.1f}mm white margin. "
                        f"Either: update INJECT_MAP target to "
                        f"({item.w_mm:.3f}, {item.h_mm:.3f}); or "
                        f"library.compute_aspect_fill(...) for "
                        f"non-INJECT path."
                    ),
                ))
        return violations

    def _resolve_asset(self, item, doc):
        """Resolve (asset_w_px, asset_h_px, dpi) for an ImageFrame.

        Returns ``(None, None, 300)`` on any failure — caller emits one
        warning per missing asset (not silent skip). Per pitfalls §1.
        """
        import base64
        import struct
        import zlib
        from io import BytesIO
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except ImportError:  # pragma: no cover
            return (None, None, 300)
        try:
            if getattr(item, "inline_image_data", None):
                raw = base64.b64decode(item.inline_image_data)
                # qCompress prefix: 4-byte big-endian uncompressed-length.
                if len(raw) < 4:
                    return (None, None, 300)
                _ = struct.unpack(">I", raw[:4])[0]
                img_bytes = zlib.decompress(raw[4:])
                im = Image.open(BytesIO(img_bytes))
                w_px, h_px = im.size
                dpi_pair = im.info.get("dpi", (300, 300))
                try:
                    dpi = int(dpi_pair[0]) or 300
                except (TypeError, ValueError):
                    dpi = 300
                return (w_px, h_px, dpi)
            img_path = item.image or item.src
            if not img_path:
                return (None, None, 300)
            from pathlib import Path
            p = Path(img_path)
            if not p.is_absolute():
                root = getattr(doc, "_template_root", None)
                if root is not None:
                    p = Path(root) / img_path
                else:
                    p = Path.cwd() / img_path
            if not p.exists():
                return (None, None, 300)
            im = Image.open(p)
            # Defensive: honor EXIF orientation for end-user assets.
            try:
                im = ImageOps.exif_transpose(im)
            except Exception:
                pass
            w_px, h_px = im.size
            dpi_pair = im.info.get("dpi", (300, 300))
            try:
                dpi = int(dpi_pair[0]) or 300
            except (TypeError, ValueError):
                dpi = 300
            return (w_px, h_px, dpi)
        except (FileNotFoundError, OSError, ValueError, UnidentifiedImageError):
            return (None, None, 300)
        except Exception:
            return (None, None, 300)

    def _rendered_extent_mm(self, item, aw_px, ah_px, dpi):
        """Return (rendered_w_mm, rendered_h_mm) per Scribus draw matrix.

        Three-branch dispatch (pitfalls §17):
          - scale_type=0: ScaleAuto. Image renders at native_mm * LOCALSCX.
          - scale_type=1, ratio=1: Manual + preserve aspect. qMin scale,
            centered letterbox INSIDE the frame.
          - scale_type=1, ratio=0: Manual stretch. Fills exactly — no
            letterbox; return (None, None) so caller skips.
        """
        scx, scy = item.local_scale
        nat_w_mm = aw_px * 25.4 / dpi
        nat_h_mm = ah_px * 25.4 / dpi
        if item.scale_type == 0:
            return (nat_w_mm * scx, nat_h_mm * scy)
        if item.scale_type == 1 and item.ratio == 1:
            s = min(item.w_mm / nat_w_mm, item.h_mm / nat_h_mm)
            return (nat_w_mm * s, nat_h_mm * s)
        # scale_type=1, ratio=0 → stretch fills.
        return (None, None)

    def _is_full_bleed(self, bbox, bleed, pw_mm, ph_mm) -> bool:
        """True if any bbox edge is within 0.5mm of the page bleed.

        Uses the rotation-aware bbox from ``frame_bbox_mm`` — never raw
        ``item.x_mm + item.w_mm``. Per pitfalls §7.
        """
        if bbox is None:
            return False
        x0, y0, x1, y1 = bbox
        # Outer-bleed edges: x=-bleed (left), x=pw+bleed (right),
        # y=-bleed (top), y=ph+bleed (bottom). Frame edges at x=0 / pw
        # are NOT outer-bleed; only frames extending into ±bleed count.
        eps = 0.5
        if x0 <= -bleed + eps:
            return True
        if x1 >= pw_mm + bleed - eps:
            return True
        if y0 <= -bleed + eps:
            return True
        if y1 >= ph_mm + bleed - eps:
            return True
        return False

    def _asset_warning(self, item):
        ident = item.anname or f"<unnamed y={item.y_mm:.1f}>"
        return Violation(
            rule_id=self.id,
            severity="warning",
            targets=(ident,),
            message=(
                f"asset missing/corrupt for {item.anname!r} "
                f"(image={item.image!r}); cannot verify "
                f"image_fills_frame"
            ),
        )


# ---------------------------------------------------------------------------
# brand:band_consistency (Issue #25)
# ---------------------------------------------------------------------------
# Default brand-color fills considered background decoration. Frames whose
# fill is in this set AND have no image content are exempt from the band
# rule (they can extend full-bleed for visual decoration). Templates may
# override the list via ``meta.yml::body_block_margins.background_decoration.fills``.
_DEFAULT_BG_DECORATION_FILLS = (
    "Dunkelgrün", "Hellgrün", "Magenta", "Gelb", "White",
)


def _is_background_decoration(item, bg_fills) -> bool:
    """Solid-fill polygon OR image-less ImageFrame with brand-color fill.

    Decoration frames extend full-bleed in any band/margin without firing
    the band-consistency rule. Per Issue #25 §3.
    """
    fill = getattr(item, "fill", None)
    if fill not in bg_fills:
        return False
    if isinstance(item, Polygon):
        return True
    if isinstance(item, ImageFrame):
        has_image = bool(
            item.image or item.src
            or getattr(item, "inline_image_data", None)
        )
        return not has_image
    return False


@dataclass(frozen=True)
class _BandConsistencyRule(BrandRule):
    """Body-pool pages confine content to header/free/footer bands + L/R margins.

    The model (Issue #25 §1, §3): every body-pool page in a multi-page
    publication shares the same OUTER STRUCTURE — a header band at the
    top (page #/breadcrumb), a free zone in the middle (where each page's
    own content lives), a footer band at the bottom (page number/colophon),
    and L/R outer/inner margins. The free zone is flexible (any internal
    layout — 3-col text grid, image-top, image-bottom, photo grid). The
    OUTER STRUCTURE is rigid and guarantees that any LEFT body page can be
    paired with any RIGHT body page without breaking spread combinability.
    Bezirksgruppen shuffle pages freely; this rule keeps spreads coherent.

    Two frame classes:
      - **Content frames** (subject to bands + margins): all ``TextFrame`` +
        ``ImageFrame`` instances WITH image content (``image`` / ``src`` /
        ``inline_image_data`` set).
      - **Background decoration** (EXEMPT): ``Polygon`` with brand-color
        fill, image-less ``ImageFrame`` with brand-color fill. These can
        extend full-bleed; they are decoration, not content.

    Excluded feature pages: pages with hero treatments that legitimately
    bleed past the bands (cover photos, edge-to-edge spreads, back covers)
    are listed in ``meta.yml::body_block_margins.excluded_pages`` (1-indexed)
    and exempt from the rule.

    Severity = ERROR for both band intrusion AND margin drift (band
    intrusion breaks combinability; margin drift breaks visual consistency
    — same severity simplifies the model). Tolerance = 0.5 mm default.

    Skips:
      - Templates without ``meta.yml::body_block_margins`` (opt-out via
        absent meta key — the rule is silently a no-op).
      - Master pages.
      - Pages whose 1-indexed number is in ``excluded_pages``.
      - Pages whose ``master_name`` doesn't match ``links``/``rechts``
        (spine_safety covers unknown sides separately).
      - Background decoration frames (per ``_is_background_decoration``).
      - Anchor-positioned frames (mirrors ``_BleedCoverageRule``'s anchor
        skip — inline icons / logos / wahlkreuz markers anchored to text
        runs are positioned relative to the run, not to the page).
      - Frames without spatial extent (``frame_bbox_mm`` returns ``None``).

    Per-template skip via
    ``meta.yml::brand_overrides[brand:band_consistency]``.
    """

    tolerance_mm: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        from sla_lib.builder.meta_schema import load_band_spec
        slug = getattr(doc, "template_id", "") or ""
        if not slug:
            return []
        spec = load_band_spec(slug)
        if spec is None:
            return []   # opt-out via missing meta key

        excluded = set(spec.get("excluded_pages", []))
        bands = spec["bands"]
        margins = spec["margins"]
        bg_fills = set(spec.get("background_decoration", {}).get(
            "fills", list(_DEFAULT_BG_DECORATION_FILLS)))

        header_y_top = bands["header"]["y_top_mm"]
        header_y_bot = bands["header"]["y_bottom_mm"]
        footer_y_top = bands["footer"]["y_top_mm"]
        footer_y_bot = bands["footer"]["y_bottom_mm"]
        # free zone = (header_y_bot, footer_y_top)

        violations: list = []
        for page in doc.pages:
            if page.is_master:
                continue
            page_num = page.own_page + 1   # 1-indexed for users
            if page_num in excluded:
                continue   # feature page

            # Determine page side
            m = SIDE_RX.search(page.master_name or "")
            if not m:
                continue   # spine_safety covers unknown sides
            side = "left" if m.group(1).lower() == "links" else "right"
            side_margins = margins[side]
            outer_mm = side_margins["outer_mm"]
            inner_mm = side_margins["inner_mm"]
            pw_mm = page.width_pt * PT_TO_MM

            if side == "left":
                # LEFT page: outer = left edge, inner = right edge (spine).
                allowed_x_min = outer_mm
                allowed_x_max = pw_mm - inner_mm
            else:
                # RIGHT page: outer = right edge, inner = left edge (spine).
                allowed_x_min = inner_mm
                allowed_x_max = pw_mm - outer_mm

            for item in page.items:
                # Skip background decoration (exempt by design).
                if _is_background_decoration(item, bg_fills):
                    continue
                # Skip anchor-positioned frames (positioned relative to a
                # text run, not the page — mirrors _BleedCoverageRule).
                if getattr(item, "is_anchor_positioned", False):
                    continue
                if getattr(item, "anchor", None) is not None:
                    continue
                # Skip frames with no spatial extent.
                bbox = _frame_bbox_mm(item, page)
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                anname = getattr(item, "anname", "") or ""
                # Vertical bounds: frame must lie entirely within ONE of
                # the three bands (header / free / footer). Frames that
                # straddle a band boundary fail.
                in_header = (
                    y0 >= header_y_top - self.tolerance_mm
                    and y1 <= header_y_bot + self.tolerance_mm
                )
                in_footer = (
                    y0 >= footer_y_top - self.tolerance_mm
                    and y1 <= footer_y_bot + self.tolerance_mm
                )
                in_free = (
                    y0 >= header_y_bot - self.tolerance_mm
                    and y1 <= footer_y_top + self.tolerance_mm
                )
                if not (in_header or in_footer or in_free):
                    violations.append(Violation(
                        severity="error",
                        rule_id=self.id,
                        message=(
                            f"frame {anname!r} on page {page_num} "
                            f"({side}) bbox y=[{y0:.1f}, {y1:.1f}] "
                            f"crosses band boundary. Bands: header "
                            f"[{header_y_top}, {header_y_bot}], "
                            f"free [{header_y_bot}, {footer_y_top}], "
                            f"footer [{footer_y_top}, {footer_y_bot}]. "
                            f"Either confine to one band, OR list page "
                            f"in excluded_pages, OR mark frame as "
                            f"background_decoration."
                        ),
                        targets=(anname or f"<unnamed p{page_num} y={y0:.1f}>",),
                    ))
                # Horizontal bounds: applied ONLY to free-zone content.
                # Header/footer band frames have their own band-specific
                # design (page numbers traditionally sit in the outer-
                # margin alley below body content; breadcrumbs may extend
                # past body margins for design reasons). The body-margin
                # spec applies to body content, not band content.
                if not in_free:
                    continue
                if (x0 < allowed_x_min - self.tolerance_mm
                        or x1 > allowed_x_max + self.tolerance_mm):
                    violations.append(Violation(
                        severity="error",
                        rule_id=self.id,
                        message=(
                            f"frame {anname!r} on page {page_num} "
                            f"({side}) bbox x=[{x0:.1f}, {x1:.1f}] "
                            f"exceeds margin spec [{allowed_x_min:.1f}, "
                            f"{allowed_x_max:.1f}] (outer={outer_mm}mm, "
                            f"inner={inner_mm}mm)."
                        ),
                        targets=(anname or f"<unnamed p{page_num} x={x0:.1f}>",),
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
    _make_rule(
        _SpineSafetyRule,
        id="brand:spine_safety",
        name="Spine-safety on facing pages",
        description=(
            "On facing-pages docs, non-SpreadImage frames must inset "
            "at least 3mm from the spine; otherwise Scribus extends the "
            "bleed across the spine into the facing page."
        ),
        severity="warning",
    ),
    _make_rule(
        _BleedCoverageRule,
        id="brand:bleed_coverage",
        name="Outer-edge bleed coverage on facing-pages",
        description=(
            "Full-width frames (w >= 0.95 * page_w) on facing-pages docs "
            "must extend to the outer bleed (LEFT page: x <= -bleed; "
            "RIGHT page: x+w >= page_w + bleed; cover own_page=0 treats "
            "both edges as outer). SpreadImage halves and rotated frames "
            "are exempt; per-template skip via "
            "meta.yml::brand_overrides[brand:bleed_coverage]."
        ),
    ),
    _make_rule(
        _ImageTextOverlapRule,
        id="brand:image_text_overlap",
        name="Text and image/filled-polygon partial overlap",
        description=(
            "Text and image-or-filled-polygon must not partially overlap. "
            "Allowed: zero overlap, text fully inside shape (caption-on-"
            "photo), shape fully inside text (drop-cap). Filled polygons "
            "are those with fill in {Dunkelgrün, Hellgrün, Magenta, Gelb}."
        ),
    ),
    _make_rule(
        _CoverExtentMatchRule,
        id="brand:cover_extent_match",
        name="Vertically touching full-width frames share extents",
        description=(
            "Pairs of full-width frames (w >= 0.95 * page_w) that "
            "vertically touch (one's bottom == other's top within 0.5mm) "
            "must share outer-bbox extents (left+right within 0.5mm). "
            "Catches the cover-image vs full-bleed-band mismatch class."
        ),
        severity="warning",
    ),
    _make_rule(
        _VisualAdjacencyDriftRule,
        id="brand:visual_adjacency_drift",
        name="Visual adjacency drift (4-axis + declaration disagreement)",
        description=(
            "Pairs of frames that appear visually aligned/adjacent on any "
            "of 4 axes (left/right/top/bottom edges) but are not declared "
            "in the template's CONSTRAINTS list. Declarations are "
            "re-executed against the actual geometry — declarations whose "
            "own tolerance is breached emit a 'declaration disagrees' "
            "warning (breaks the encode-and-silence escape). Heuristic; "
            "warning-only by default."
        ),
        severity="warning",
    ),
    _make_rule(
        _ImageFillsFrameRule,
        id="brand:image_fills_frame",
        name="Image content fills frame extent",
        description=(
            "Each ImageFrame's rendered-content extent (computed from "
            "scale_type + local_scale + asset native dims) must reach "
            "the frame's outer extent within tolerance (1%% of long "
            "side, floor 0.5mm). Catches INJECT_MAP target drift after "
            "frame extents change (the post-#22/#23 Zeitung regression "
            "class) and aspect-mismatch letterboxing on "
            "scale_type=1+ratio=1. Severity ERROR for full-bleed frames "
            "(rotation-aware bbox touches +/-bleed); WARNING otherwise. "
            "Image-less frames (solid-fill polygons) are skipped. "
            "Per-template skip via "
            "meta.yml::brand_overrides[brand:image_fills_frame]."
        ),
        # Per-violation severity is computed dynamically in check() via
        # _is_full_bleed. Registry severity is "error" so any violation
        # that escapes the bleed-carve still fails structural_check.
        severity="error",
    ),
    _make_rule(
        _BandConsistencyRule,
        id="brand:band_consistency",
        name="Body-pool pages confine content to header/free/footer "
             "bands and L/R margins (Issue #25)",
        description=(
            "Content frames (text + content-bearing image) must stay "
            "inside the bands and margins declared in "
            "meta.yml::body_block_margins. Background decoration "
            "(solid-fill polygons, image-less brand-color frames) "
            "is exempt. Pages listed in excluded_pages are exempt. "
            "Templates without body_block_margins are skipped."
        ),
    ),
]
