"""tools/experiment_results.py — results aggregation + ranking (issue #31).

CLI: ``experiment-results <exp-id> [<results.json> ...]``. If no result
files are passed, the tool globs ``experiments/<exp-id>/results/*.json``.

Multi-rater merging combines per-slug position scores by mean across
raters. Variants no rater placed are excluded (mean over Nones, not
zero) so the summary reflects what was actually voted on.

Outputs:
  - ``experiments/<exp-id>/results/SUMMARY.md`` — human-readable tally
    (top-3 / bottom-3) + dropped-variants section + dual-section corpus
    update stub.

The aggregator consumes the rank shape (linear Borda position scores)
and a direct-pick fallback shape (1.0 per selection, None otherwise).
Legacy v1 result files are no longer processable; see issue #31 for
the schema bump.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "experiments" / "_schema" / "results.schema.yaml"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def _load_schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_results(payload: dict) -> list[jsonschema.ValidationError]:
    schema = _load_schema()
    return sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(payload),
        key=lambda e: list(e.path),
    )


# ---------------------------------------------------------------------------
# Position score primitives (linear Borda count, normalised to [0, 1])
# ---------------------------------------------------------------------------


def compute_position_scores(
    ranking: list[str],
    all_slugs: list[str],
) -> dict[str, float | None]:
    """Linear Borda position score for one rater's ranking.

    For each slug at rank index ``i`` in ``ranking`` (0-based) over a
    list of length ``N``:

        score = (N - 1 - i) / (N - 1)

    Top-ranked is 1.0, bottom-ranked is 0.0. With ``N == 1`` the single
    ranked slug gets 1.0 (avoids div-by-zero). Slugs in ``all_slugs``
    that don't appear in ``ranking`` get ``None`` — excluded from
    aggregation rather than treated as zero.
    """
    n = len(ranking)
    scores: dict[str, float | None] = {}
    if n == 0:
        return {slug: None for slug in all_slugs}
    if n == 1:
        ranked = {ranking[0]: 1.0}
    else:
        ranked = {slug: (n - 1 - i) / (n - 1) for i, slug in enumerate(ranking)}
    for slug in all_slugs:
        scores[slug] = ranked.get(slug)
    # Also include any slug that's in ranking but not in all_slugs (defensive).
    for slug, val in ranked.items():
        scores.setdefault(slug, val)
    return scores


def compute_position_scores_for_direct_pick(
    selections: list[str],
    all_slugs: list[str],
) -> dict[str, float | None]:
    """Direct-pick fallback: 1.0 for each selected slug, None otherwise.

    Treats every selection as equally favoured; unselected slugs are
    excluded (None) rather than rated zero.
    """
    selected = set(selections)
    scores: dict[str, float | None] = {}
    for slug in all_slugs:
        scores[slug] = 1.0 if slug in selected else None
    for slug in selected:
        scores.setdefault(slug, 1.0)
    return scores


# ---------------------------------------------------------------------------
# Aggregator (one or many result files; mean of non-None scores per slug)
# ---------------------------------------------------------------------------


def aggregate(results_files: list[Path]) -> dict:
    """Load + validate result files; combine per-slug scores by mean.

    Each input file is validated against the rank/direct-pick schema and
    contributes a single rater's per-slug score map. Across raters the
    aggregator takes the mean of the non-None values per slug. Slugs no
    rater placed remain None in the result so render_summary can omit
    or surface them as desired.
    """
    if not results_files:
        raise ValueError("aggregate() requires at least 1 results file")

    payloads: list[dict] = []
    for path in results_files:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        errors = validate_results(data)
        if errors:
            ptr = "/" + "/".join(str(s) for s in errors[0].path)
            raise ValueError(f"{path}: schema invalid at {ptr}: {errors[0].message}")
        payloads.append(data)

    # Collect every slug seen across rankings + selections.
    all_slugs: list[str] = []
    seen: set[str] = set()
    for payload in payloads:
        for slug in payload.get("ranking", []) or payload.get("selections", []):
            if slug not in seen:
                seen.add(slug)
                all_slugs.append(slug)

    # Per-rater score maps.
    per_rater_scores: list[tuple[str, dict[str, float | None]]] = []
    modes_seen: list[str] = []
    raters: list[str] = []
    for payload in payloads:
        rater = payload["rater"]
        if rater not in raters:
            raters.append(rater)
        mode = payload["mode"]
        if mode not in modes_seen:
            modes_seen.append(mode)
        if mode == "rank":
            scores = compute_position_scores(payload["ranking"], all_slugs)
        elif mode == "direct-pick":
            scores = compute_position_scores_for_direct_pick(
                payload["selections"],
                all_slugs,
            )
        else:  # schema rejects this, but guard defensively
            raise ValueError(f"unknown mode {mode!r} in {payload}")
        per_rater_scores.append((rater, scores))

    # Aggregate by mean of non-None values per slug.
    per_slug: dict[str, dict[str, float | int | None]] = {}
    for slug in all_slugs:
        values: list[float] = [
            s[slug]  # type: ignore[misc]
            for _, s in per_rater_scores
            if s.get(slug) is not None
        ]
        if values:
            per_slug[slug] = {
                "mean_score": sum(values) / len(values),
                "n_raters": len(values),
            }
        else:
            per_slug[slug] = {"mean_score": None, "n_raters": 0}

    starts = sorted(payload["started_at"] for payload in payloads)
    ends = sorted(payload["exported_at"] for payload in payloads)

    return {
        "experiment_id": payloads[0]["experiment_id"],
        "raters": raters,
        "started_at": starts[0],
        "exported_at": ends[-1],
        "modes_seen": modes_seen,
        "all_slugs": all_slugs,
        "per_slug": per_slug,
    }


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------


def _ranked_slugs(agg: dict) -> list[str]:
    """Return slugs sorted by mean_score desc; None last (stable on slug)."""

    def key(slug: str):
        v = agg["per_slug"][slug]["mean_score"]
        # None sorts last; tie-break by slug.
        return (0 if v is None else 1, v if v is not None else 0.0, slug)

    # Sort desc on the score, asc on slug for stability among ties.
    slugs = list(agg["per_slug"].keys())
    return sorted(
        slugs,
        key=lambda s: (
            agg["per_slug"][s]["mean_score"] is None,
            -(agg["per_slug"][s]["mean_score"] or 0.0),
            s,
        ),
    )


def _score_line(slug: str, agg: dict) -> str:
    entry = agg["per_slug"].get(slug, {"mean_score": None, "n_raters": 0})
    score = entry["mean_score"]
    n = entry["n_raters"]
    if score is None:
        return f"  - `{slug}` — (no raters placed this variant)"
    return f"  - `{slug}` — score {score:.3f} (n={n})"


def render_dropped_section(dropped: list[dict] | None) -> list[str]:
    out: list[str] = []
    out.append("## Variants dropped during render")
    out.append("")
    if not dropped:
        out.append("_No variants dropped — all hypotheses passed the envelope._")
    else:
        for entry in dropped:
            slug = entry.get("slug", "<unknown>")
            reason = entry.get("reason", "<no reason>")
            out.append(f"### `{slug}`")
            out.append("")
            out.append(f"- **Reason:** {reason}")
            violations = entry.get("violations", []) or []
            if violations:
                out.append("- **Violations:**")
                for v in violations:
                    out.append(
                        f"  - {v.get('severity', 'error')}: "
                        f"`{v.get('rule_id', '')}` — {v.get('message', '')}"
                    )
            out.append("")
    out.append("")
    return out


def render_corpus_stub() -> list[str]:
    out: list[str] = []
    out.append(
        "## Corpus update stub (to be amended into design-guide/gruene-corpus.md)"
    )
    out.append("")
    out.append("### From v1 (envelope necessity)")
    out.append("")
    out.append(
        "_v1 (`falzflyer-p2-mein-plan`, 2026-04) revealed that variants "
        "violated basic spacing/margin rules because the render gate "
        "enforced only `brand:inside_page`, not the full 16 "
        "BRAND_CONSTRAINTS + Layer-1 thresholds. v2's gate "
        "(`tools/experiment_envelope.py::run_envelope`) closes that loop. "
        "Methodology lesson: every design experiment respects a constraint "
        "envelope by default; the tested axis is the only declared "
        "relaxation. See `.claude/skills/experiments/SKILL.md` for the "
        "corrected process._"
    )
    out.append("")
    out.append("### From v2 (density+form findings)")
    out.append("")
    out.append(
        "_Top-3 (by linear Borda position score across raters): "
        "[VARIANT-1] / [VARIANT-2] / [VARIANT-3]. Bottom-3: [...]. "
        "To be filled in by the executor of T-final after Flo's rank-mode "
        "voting session._"
    )
    out.append("")
    return out


def render_summary(
    aggregated: dict,
    *,
    hypotheses: dict[str, dict] | None = None,
    dropped: list[dict] | None = None,
) -> str:
    hypotheses = hypotheses or {}
    out: list[str] = []
    out.append(f"# Results — {aggregated['experiment_id']}")
    out.append("")
    out.append(f"**Raters:** {', '.join(aggregated['raters'])}")
    out.append(
        f"**Sessions:** {aggregated['started_at']} → {aggregated['exported_at']}"
    )
    out.append(f"**Modes:** {', '.join(aggregated['modes_seen'])}")
    out.append(f"**Variants placed:** {len(aggregated['all_slugs'])}")
    out.append("")

    out.extend(render_dropped_section(dropped))
    out.extend(render_corpus_stub())

    ranked = _ranked_slugs(aggregated)
    placed = [s for s in ranked if aggregated["per_slug"][s]["mean_score"] is not None]

    out.append("## Top 3")
    if not placed:
        out.append("_(no variants placed)_")
    else:
        for slug in placed[:3]:
            out.append(_score_line(slug, aggregated))
    out.append("")

    out.append("## Bottom 3")
    if not placed:
        out.append("_(no variants placed)_")
    else:
        for slug in placed[-3:][::-1]:
            out.append(_score_line(slug, aggregated))
    out.append("")

    out.append("## Suggested corpus entries")
    out.append("")
    out.append(
        "Paste the relevant entries into `design-guide/gruene-corpus.md` "
        "with provenance tagging (per CONTEXT.md decision 11)."
    )
    out.append("")
    out.append("### Winners (top 3)")
    for slug in placed[:3]:
        h = hypotheses.get(slug, {})
        out.append(
            f"- **{h.get('name', slug)}** "
            f"(`{slug}`, axes: `{', '.join(h.get('axis_commitments', []))}`)\n"
            f"  - rationale: {h.get('rationale', '(unknown)')}\n"
            f"  - provenance: experiment {aggregated['experiment_id']}, "
            f"raters: {', '.join(aggregated['raters'])}"
        )
    out.append("")

    out.append("### Losers (bottom 3)")
    for slug in placed[-3:][::-1]:
        h = hypotheses.get(slug, {})
        out.append(
            f"- **{h.get('name', slug)}** "
            f"(`{slug}`, axes: `{', '.join(h.get('axis_commitments', []))}`)\n"
            f"  - rationale: {h.get('rationale', '(unknown)')}\n"
            f"  - provenance: experiment {aggregated['experiment_id']}, "
            f"raters: {', '.join(aggregated['raters'])} (loser)"
        )
    out.append("")

    out.append(
        f"_Generated by `bin/experiment-results` at "
        f"{datetime.datetime.now(datetime.timezone.utc).isoformat()}._"
    )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_hypotheses(exp_id: str) -> dict[str, dict]:
    """Load manifest hypotheses keyed by slug for SUMMARY.md enrichment."""
    yml = ROOT / "experiments" / exp_id / "manifest.yml"
    if not yml.exists():
        return {}
    try:
        m = yaml.safe_load(yml.read_text(encoding="utf-8"))
        return {h["slug"]: h for h in m.get("hypotheses", [])}
    except Exception:  # noqa: BLE001
        return {}


def _load_dropped(exp_id: str) -> list[dict]:
    """Load render-time drop log from manifest.json::_dropped (issue #30).

    Returns empty list when the manifest is missing or has no _dropped key
    (e.g. an aggregation run before render, or an experiment with 0 drops).
    """
    js = ROOT / "experiments" / exp_id / "manifest.json"
    if not js.exists():
        return []
    try:
        m = json.loads(js.read_text(encoding="utf-8"))
        return list(m.get("_dropped", []) or [])
    except Exception:  # noqa: BLE001
        return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="experiment-results",
        description="Aggregate voting results into rankings + SUMMARY.md.",
    )
    ap.add_argument("exp_id", nargs="?", help="Experiment id.")
    ap.add_argument(
        "results",
        nargs="*",
        help="Optional results JSON paths; default globs "
        "experiments/<exp_id>/results/*.json.",
    )
    args = ap.parse_args(argv)

    if not args.exp_id:
        ap.print_help()
        return 0

    exp_id = args.exp_id
    if args.results:
        files = [Path(p) for p in args.results]
    else:
        files = sorted(
            Path(p)
            for p in glob.glob(
                str(ROOT / "experiments" / exp_id / "results" / "*.json"),
            )
        )
    if not files:
        print(f"FATAL: no results files for {exp_id}", file=sys.stderr)
        return 2

    try:
        agg = aggregate(files)
    except ValueError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 3

    hyps = _load_hypotheses(exp_id)
    dropped = _load_dropped(exp_id)
    summary_md = render_summary(agg, hypotheses=hyps, dropped=dropped)

    out_dir = ROOT / "experiments" / exp_id / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "SUMMARY.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    placed = sum(1 for s in agg["per_slug"].values() if s["mean_score"] is not None)
    print(
        f"results -> {summary_path.relative_to(ROOT)} "
        f"({len(agg['raters'])} raters, "
        f"{len(agg['all_slugs'])} variants seen, "
        f"{placed} placed, "
        f"modes: {', '.join(agg['modes_seen'])})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
