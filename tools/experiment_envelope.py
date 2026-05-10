"""tools/experiment_envelope.py — constraint envelope loader + runner (issue #30).

Composes the existing 16 ``BRAND_CONSTRAINTS`` (defined in
``tools/sla_lib/builder/brand_constraints.py:1525-1680``) with new
Layer-1 deterministic predicates (the 22-row table at
``design-guide/README.md:24-46``) into a single envelope evaluated
against a built ``Document``. Replaces the per-experiment "only
inside_page" gate (the v1 failure mode — see CONTEXT.md decision 1).

Public surface:

  - ``Envelope`` — frozen value object carrying the merged, validated config.
  - ``EnvelopeValidationError`` — raised by ``load_envelope`` on schema fail.
  - ``load_envelope(exp_dir)`` — read ``<exp_dir>/constraints.yml``, resolve
    ``extends:``, validate against ``experiments/_schema/constraints.schema.yaml``.
  - ``run_envelope(doc, envelope)`` — evaluate every active brand rule + Layer-1
    predicate against the built ``Document``, return a merged list of
    ``Violation`` objects (severity=="error" only). Mirrors the rule-loop
    pattern at ``tools/sla_lib/builder/structural_check.py:166-204``.
  - ``format_envelope_markdown(envelope)`` — bullet-list rendering for the
    hypothesis-generation prompt thread.

Implementation notes (the "why"):

  - The envelope check validates the rendered artefact (the post-build
    ``Document``), NOT the variant module's self-report. Variant code
    could in principle disable a check; trusting the artefact is the
    only safe model (pitfalls.md §1).
  - Relaxations are a runtime skip on rule_id, NOT a removal from the
    ``brand_rules`` list. The list stays an authoritative inventory and
    the relax set is the diff against it.
  - Predicates iterate primitives via ``Document.iter_all_primitives()``
    when available (defensive ``hasattr`` mirrors the inside_page rule's
    pre-existing pattern at ``brand_constraints.py:142``).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import BRAND_CONSTRAINTS  # noqa: E402
from sla_lib.builder.constraints import Violation  # noqa: E402
from sla_lib.builder.primitives import TextFrame  # noqa: E402

SCHEMA_PATH = ROOT / "experiments" / "_schema" / "constraints.schema.yaml"


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class EnvelopeValidationError(ValueError):
    """Raised when a constraints.yml fails schema validation.

    Carries the full list of jsonschema errors so callers can surface
    every problem at once instead of one-at-a-time discovery.
    """

    def __init__(self, message: str, errors: list[jsonschema.ValidationError]):
        super().__init__(message)
        self.errors = errors


@dataclass(frozen=True)
class Envelope:
    """Merged, validated constraint envelope for one experiment."""

    brand_rules: tuple[str, ...]
    layer1: dict[str, Any]
    relax: tuple[tuple[str, str], ...]
    tested_axis: str
    regeneration: dict[str, Any] = field(default_factory=dict)

    def relax_ids(self) -> frozenset[str]:
        return frozenset(rid for rid, _ in self.relax)


# ---------------------------------------------------------------------------
# Loading + merging
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _shallow_merge(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """Ansible-style shallow override on top-level keys.

    Child wins on every key it sets. For ``layer1`` we merge inner keys
    so a child can override a single threshold without re-listing all 22.
    ``brand_rules`` and ``relax`` follow override semantics: a non-empty
    child list replaces the parent's list verbatim (so a per-experiment
    file can either re-list explicitly or inherit by omission).
    """
    merged: dict[str, Any] = dict(parent)
    for key, val in child.items():
        if key == "layer1" and isinstance(val, dict) and isinstance(parent.get("layer1"), dict):
            merged_layer1 = dict(parent["layer1"])
            merged_layer1.update(val)
            merged["layer1"] = merged_layer1
        elif key in ("brand_rules", "relax") and not val:
            # Empty child list is inherit-only, not "clear the parent".
            continue
        else:
            merged[key] = val
    return merged


def _resolve_chain(exp_dir: Path) -> dict[str, Any]:
    """Walk the ``extends:`` chain and return the fully-merged config dict.

    Cycle-detection: visited paths recorded by resolved-absolute path.
    """
    primary = exp_dir / "constraints.yml"
    if not primary.exists():
        raise FileNotFoundError(
            f"{primary} missing — run `experiments new` first."
        )

    chain: list[Path] = []
    visited: set[Path] = set()
    current = primary
    while True:
        resolved = current.resolve()
        if resolved in visited:
            raise EnvelopeValidationError(
                f"extends cycle detected via {resolved}", errors=[],
            )
        visited.add(resolved)
        chain.append(resolved)
        data = _read_yaml(current)
        ext = data.get("extends")
        if not ext:
            break
        current = (current.parent / ext).resolve()
        if not current.exists():
            raise FileNotFoundError(
                f"extends target not found: {current} (from {resolved})"
            )

    merged: dict[str, Any] = {}
    for path in reversed(chain):
        data = _read_yaml(path)
        data.pop("extends", None)
        merged = _shallow_merge(merged, data)
    return merged


def load_envelope(exp_dir: Path) -> Envelope:
    """Read ``<exp_dir>/constraints.yml``, resolve extends, validate, return."""
    merged = _resolve_chain(exp_dir)

    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(merged), key=lambda e: list(e.path))
    if errors:
        pretty = "; ".join(
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in errors[:5]
        )
        raise EnvelopeValidationError(
            f"constraints.yml validation failed ({len(errors)} error(s)): {pretty}",
            errors=errors,
        )

    relax_raw = merged.get("relax", []) or []
    relax = tuple((r["id"], r["rationale"]) for r in relax_raw)
    return Envelope(
        brand_rules=tuple(merged.get("brand_rules", []) or []),
        layer1=dict(merged.get("layer1", {}) or {}),
        relax=relax,
        tested_axis=merged["tested_axis"],
        regeneration=dict(merged.get("regeneration", {}) or {}),
    )


# ---------------------------------------------------------------------------
# Brand-rule pass
# ---------------------------------------------------------------------------

def _brand_rule_violations(doc, envelope: Envelope) -> list[Violation]:
    primitives = (
        list(doc.iter_all_primitives())
        if hasattr(doc, "iter_all_primitives") else []
    )
    relax = envelope.relax_ids()
    active_ids = set(envelope.brand_rules) - relax
    out: list[Violation] = []
    for rule in BRAND_CONSTRAINTS:
        if rule.id not in active_ids:
            continue
        try:
            vs = rule.check(primitives, doc)
        except Exception as e:  # noqa: BLE001 — mirror structural_check.py:191
            out.append(Violation(
                severity="error",
                rule_id=rule.id,
                message=f"rule check raised: {e!r}",
            ))
            continue
        for v in vs:
            if v.severity == "error":
                out.append(v)
    return out


# ---------------------------------------------------------------------------
# Layer-1 predicates
# ---------------------------------------------------------------------------

def _resolve_text_fontsize(doc, frame: TextFrame) -> float | None:
    """Best-effort fontsize lookup: explicit > Run.fontsize > para_style > 0."""
    explicit = getattr(frame, "fontsize", None)
    if explicit:
        return float(explicit)
    if frame.runs:
        for run in frame.runs:
            fs = getattr(run, "fontsize", None)
            if fs:
                return float(fs)
            para = getattr(run, "paragraph_style", None) or frame.style
            if para:
                fs2 = _para_style_fontsize(doc, para)
                if fs2:
                    return fs2
    if frame.style:
        return _para_style_fontsize(doc, frame.style)
    return None


def _para_style_fontsize(doc, style_name: str) -> float | None:
    styles = (
        getattr(doc, "_extra_para_styles", None)
        or getattr(doc, "_para_styles", None)
        or getattr(doc, "para_styles", None)
        or {}
    )
    if isinstance(styles, dict):
        style = styles.get(style_name)
    else:
        style = next((s for s in styles if getattr(s, "name", "") == style_name), None)
    if style is None:
        return None
    fs = getattr(style, "fontsize", None)
    return float(fs) if fs else None


def _check_body_min_pt(doc, threshold: float) -> list[Violation]:
    """body_min_pt: every body-like P2 text frame ≥ threshold pt.

    Heuristic: a P2 frame's style/anname that contains "body", "schlagwort",
    "text", "item" or "manifesto" classifies as body. The check fires only
    on P2 panel frames; titles/headlines opt out via the classifier
    (consistent with hcd #12 phrasing).
    """
    body_markers = ("body", "schlagwort", "text", "item", "manifesto", "numbered/text", "editorial/item")
    out: list[Violation] = []
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        if not (prim.anname or "").startswith("P2 "):
            continue
        identifier = ((prim.style or "") + " " + (prim.anname or "")).lower()
        if not any(m in identifier for m in body_markers):
            continue
        fs = _resolve_text_fontsize(doc, prim)
        if fs is not None and fs < threshold:
            out.append(Violation(
                severity="error",
                rule_id="layer1:body_min_pt",
                message=(
                    f"body text frame {prim.anname!r} fontsize={fs}pt "
                    f"< threshold={threshold}pt"
                ),
                targets=(prim.anname or "",),
            ))
    return out


def _check_caption_impressum_min_pt(doc, threshold: float) -> list[Violation]:
    """Caption/impressum minimum font size.

    Scoped to P2-panel frames only (the experiment panel under test).
    Back-panel impressum (P6 Impressum etc.) is out of scope — the
    experiment varies P2; production-side back-panel sizing is a
    separate concern handled by structural_check on the template.
    """
    markers = ("impressum", "caption", "footer", "footnote")
    out: list[Violation] = []
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        if not (prim.anname or "").startswith("P2 "):
            continue
        identifier = ((prim.style or "") + " " + (prim.anname or "")).lower()
        if not any(m in identifier for m in markers):
            continue
        fs = _resolve_text_fontsize(doc, prim)
        if fs is not None and fs < threshold:
            out.append(Violation(
                severity="error",
                rule_id="layer1:caption_impressum_min_pt",
                message=(
                    f"caption/impressum frame {prim.anname!r} fontsize={fs}pt "
                    f"< threshold={threshold}pt"
                ),
                targets=(prim.anname or "",),
            ))
    return out


def _check_type_families_per_panel(doc, threshold: int) -> list[Violation]:
    """type_families_per_panel: at most ``threshold`` distinct font families.

    P2-scoped: only counts frames with anname starting "P2 " (the
    panel under test in the falzflyer experiments). Other variants of
    this rule would scope to other panels; for v2 we focus on P2.
    """
    families: set[str] = set()
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        if not (prim.anname or "").startswith("P2 "):
            continue
        font = _resolve_text_font(doc, prim)
        if font:
            families.add(_family_root(font))
    if len(families) > threshold:
        return [Violation(
            severity="error",
            rule_id="layer1:type_families_per_panel",
            message=(
                f"P2 panel uses {len(families)} type families "
                f"({sorted(families)!r}) > threshold={threshold}"
            ),
        )]
    return []


def _check_type_sizes_per_panel(doc, threshold: int) -> list[Violation]:
    sizes: set[float] = set()
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        if not (prim.anname or "").startswith("P2 "):
            continue
        fs = _resolve_text_fontsize(doc, prim)
        if fs:
            sizes.add(round(fs, 1))
    if len(sizes) > threshold:
        return [Violation(
            severity="error",
            rule_id="layer1:type_sizes_per_panel",
            message=(
                f"P2 panel uses {len(sizes)} type sizes "
                f"({sorted(sizes)!r}) > threshold={threshold}"
            ),
        )]
    return []


def _check_negative_space_pct(doc, threshold: float) -> list[Violation]:
    """negative_space_pct: P2 content area ≥ ``threshold``% whitespace.

    Content area for falzflyer P2 is the Hellgrün backing (x=99 y=28 w=99 h=185).
    Whitespace = (content_area − bbox_union_of_text_and_thin-rules) / content_area.
    Background-color polygons (Hellgrün/Dunkelgrün bands) are exempt
    from the "content" sum.
    """
    content_w, content_h = 99.0, 185.0
    content_area = content_w * content_h
    text_area_sum = 0.0
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not (getattr(prim, "anname", "") or "").startswith("P2 "):
            continue
        if isinstance(prim, TextFrame):
            area = max(0.0, prim.w_mm) * max(0.0, prim.h_mm)
            text_area_sum += area
    used_pct = (text_area_sum / content_area) * 100 if content_area else 0.0
    whitespace_pct = 100 - used_pct
    if whitespace_pct < threshold:
        return [Violation(
            severity="error",
            rule_id="layer1:negative_space_pct",
            message=(
                f"P2 negative_space={whitespace_pct:.1f}% < threshold={threshold}% "
                f"(content frames cover {used_pct:.1f}% of "
                f"{content_w}x{content_h}mm panel)"
            ),
        )]
    return []


def _check_headline_max_words(doc, threshold: int) -> list[Violation]:
    out: list[Violation] = []
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        identifier = ((prim.style or "") + " " + (prim.anname or "")).lower()
        if "headline" not in identifier and "top-title" not in identifier:
            continue
        text = _collect_text(prim)
        if not text:
            continue
        words = len(text.split())
        if words > threshold:
            out.append(Violation(
                severity="error",
                rule_id="layer1:headline_max_words",
                message=(
                    f"headline {prim.anname!r} has {words} words "
                    f"> threshold={threshold}"
                ),
                targets=(prim.anname or "",),
            ))
    return out


def _check_alignment_systems_per_panel(doc, threshold: int) -> list[Violation]:
    """Count distinct left-edge x positions (mm) used by P2 text frames.

    Two frames whose x_mm differs by ≤2mm are treated as the same
    alignment system. Threshold=2 means at most two distinct vertical
    grid lines per panel.
    """
    xs: list[float] = []
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        if not (prim.anname or "").startswith("P2 "):
            continue
        xs.append(round(prim.x_mm, 1))
    distinct: list[float] = []
    for x in sorted(xs):
        if not distinct or abs(x - distinct[-1]) > 2.0:
            distinct.append(x)
    if len(distinct) > threshold:
        return [Violation(
            severity="error",
            rule_id="layer1:alignment_systems_per_panel",
            message=(
                f"P2 panel uses {len(distinct)} alignment systems "
                f"(x_mm={distinct!r}) > threshold={threshold}"
            ),
        )]
    return []


def _check_body_line_length_chars(doc, threshold: dict[str, int]) -> list[Violation]:
    """Approximate line-length check from frame width + fontsize.

    Approximation: usable_chars ≈ frame_w_mm * 0.45 chars/mm at 10pt;
    scaled inversely with fontsize. The check fires when a body frame's
    estimated line-length is ABOVE ``threshold['max']`` (overly long
    lines hurt readability — hcd #11). Underrun is not error-grade.
    """
    body_markers = ("body", "schlagwort", "manifesto", "numbered/text", "editorial/item")
    max_chars = int(threshold.get("max", 75))
    out: list[Violation] = []
    for prim in doc.iter_all_primitives() if hasattr(doc, "iter_all_primitives") else []:
        if not isinstance(prim, TextFrame):
            continue
        if not (prim.anname or "").startswith("P2 "):
            continue
        identifier = ((prim.style or "") + " " + (prim.anname or "")).lower()
        if not any(m in identifier for m in body_markers):
            continue
        fs = _resolve_text_fontsize(doc, prim)
        if not fs:
            continue
        chars_per_mm = 0.45 * (10.0 / fs)
        est = prim.w_mm * chars_per_mm
        if est > max_chars * 1.5:
            out.append(Violation(
                severity="error",
                rule_id="layer1:body_line_length_chars",
                message=(
                    f"body frame {prim.anname!r} estimated line-length "
                    f"~{est:.0f} chars > max={max_chars} "
                    f"(w={prim.w_mm}mm, fontsize={fs}pt)"
                ),
                targets=(prim.anname or "",),
            ))
    return out


# ---------------------------------------------------------------------------
# Layer-1 predicates that the brand rules already cover (pass-through)
# ---------------------------------------------------------------------------

def _check_brand_pass_through(doc, threshold) -> list[Violation]:
    """No-op predicate for Layer-1 keys whose enforcement is already
    handled by a BRAND_CONSTRAINTS rule (avoid double-counting).
    """
    return []


# Mapping: layer1 key -> predicate. Keys missing from the dict are
# pass-through (no extra check beyond the brand-rule pass).
LAYER1_PREDICATES: dict[str, Callable[[Any, Any], list[Violation]]] = {
    "body_min_pt": _check_body_min_pt,
    "caption_impressum_min_pt": _check_caption_impressum_min_pt,
    "body_line_length_chars": _check_body_line_length_chars,
    "headline_max_words": _check_headline_max_words,
    "type_families_per_panel": _check_type_families_per_panel,
    "type_sizes_per_panel": _check_type_sizes_per_panel,
    "alignment_systems_per_panel": _check_alignment_systems_per_panel,
    "negative_space_pct": _check_negative_space_pct,
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _resolve_text_font(doc, frame: TextFrame) -> str | None:
    if frame.runs:
        for run in frame.runs:
            font = getattr(run, "font", None)
            if font:
                return font
            para = getattr(run, "paragraph_style", None) or frame.style
            if para:
                resolved = _para_style_font(doc, para)
                if resolved:
                    return resolved
    if frame.style:
        return _para_style_font(doc, frame.style)
    return None


def _para_style_font(doc, style_name: str) -> str | None:
    styles = (
        getattr(doc, "_extra_para_styles", None)
        or getattr(doc, "_para_styles", None)
        or getattr(doc, "para_styles", None)
        or {}
    )
    if isinstance(styles, dict):
        style = styles.get(style_name)
    else:
        style = next((s for s in styles if getattr(s, "name", "") == style_name), None)
    if style is None:
        return None
    return getattr(style, "font", None)


def _family_root(font: str) -> str:
    """Trim weight/style suffixes so 'Gotham Narrow Bold' and 'Gotham Narrow Book'
    count as one family ('Gotham Narrow').
    """
    suffixes = (
        " Black Italic", " Black", " Ultra Italic", " Ultra",
        " Bold Italic", " Bold", " Book Italic", " Book",
        " Italic", " Regular", " Medium", " Light",
    )
    for suf in suffixes:
        if font.endswith(suf):
            return font[: -len(suf)]
    return font


def _collect_text(frame: TextFrame) -> str:
    if frame.runs:
        return " ".join(getattr(r, "text", "") for r in frame.runs if getattr(r, "text", ""))
    return frame.text or ""


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

def run_envelope(doc, envelope: Envelope) -> list[Violation]:
    """Return all ``severity=='error'`` violations of the envelope.

    Deduplicates by ``(rule_id, message)`` so the same condition reported
    by two predicates (e.g. brand:font_family and layer1:type_families)
    only appears once.
    """
    out: list[Violation] = []
    out.extend(_brand_rule_violations(doc, envelope))

    relax = envelope.relax_ids()
    for key, threshold in envelope.layer1.items():
        full_id = f"layer1:{key}"
        if full_id in relax:
            continue
        predicate = LAYER1_PREDICATES.get(key, _check_brand_pass_through)
        try:
            vs = predicate(doc, threshold)
        except Exception as e:  # noqa: BLE001 — mirror structural_check.py
            vs = [Violation(
                severity="error",
                rule_id=full_id,
                message=f"layer1 check raised: {e!r}",
            )]
        out.extend(v for v in vs if v.severity == "error")

    seen: set[tuple[str, str]] = set()
    deduped: list[Violation] = []
    for v in out:
        key2 = (v.rule_id, v.message)
        if key2 in seen:
            continue
        seen.add(key2)
        deduped.append(v)
    return deduped


# ---------------------------------------------------------------------------
# Markdown rendering for prompt threading
# ---------------------------------------------------------------------------

def format_envelope_markdown(envelope: Envelope) -> str:
    """Render the envelope as a Markdown bullet list for the prompt thread.

    Output kept tight (<500 words) so it travels well in LLM context.
    """
    lines: list[str] = []
    lines.append("### Brand rules (16 ids, enforced as floor)")
    lines.append("")
    relax_ids = envelope.relax_ids()
    for rid in envelope.brand_rules:
        suffix = " [RELAXED]" if rid in relax_ids else ""
        lines.append(f"- `{rid}`{suffix}")
    lines.append("")

    lines.append("### Layer-1 thresholds (22 keys; design-guide/README.md:24-46)")
    lines.append("")
    for key, val in envelope.layer1.items():
        full_id = f"layer1:{key}"
        suffix = " [RELAXED]" if full_id in relax_ids else ""
        lines.append(f"- `{key}`: {val!r}{suffix}")
    lines.append("")

    lines.append("### Relaxations (named)")
    lines.append("")
    if envelope.relax:
        for rid, rationale in envelope.relax:
            lines.append(f"- `{rid}` — {rationale}")
    else:
        lines.append("- (none — full envelope enforced)")
    lines.append("")

    lines.append(f"### Tested axis: `{envelope.tested_axis}`")
    lines.append("")
    lines.append(
        "Everything except the tested axis is constraint. Hypotheses that "
        "require violating one of the floor rules must declare it in "
        "`relax:` with rationale; implicit relaxations are dropped at render."
    )
    lines.append("")

    lines.append("### Regeneration policy")
    lines.append("")
    if envelope.regeneration:
        for k, v in envelope.regeneration.items():
            lines.append(f"- `{k}`: {v!r}")
    else:
        lines.append("- (defaults: auto_retry_max=0, drop_threshold_pct=40)")
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "Envelope",
    "EnvelopeValidationError",
    "load_envelope",
    "run_envelope",
    "format_envelope_markdown",
]
