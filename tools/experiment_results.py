"""tools/experiment_results.py — results aggregation + ranking (issue #29).

CLI: ``experiment-results <exp-id> [<results.json> ...]``. If no result
files are passed, the tool globs ``experiments/<exp-id>/results/*.json``.

Multi-rater merging is OUT OF SCOPE per CONTEXT.md "Deferred". Multiple
result files from the same rater (re-runs) ARE in scope: their votes
concatenate into a single tally.

Outputs:
  - ``experiments/<exp-id>/results/SUMMARY.md`` — human-readable tally
    + Spearman halo flag + per-pair disagreement table + corpus-update
    stub for top-3 / bottom-3.

The math (wins-ratio, Spearman, disagreement) is pure stdlib — no
scipy, no numpy. Implementations are duplicated client-side in the
voting page so the export-button preview matches what this aggregator
will compute downstream.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import json
import statistics
import sys
from pathlib import Path
from typing import Iterable

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
# Aggregation primitives
# ---------------------------------------------------------------------------

def _is_skip(winner) -> bool:
    return winner is None or winner == "skip"


def wins_ratio(votes: Iterable[dict], axis: str) -> dict[str, dict[str, int]]:
    """Per-variant {wins, plays} accumulator for one axis."""
    acc: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"wins": 0, "plays": 0}
    )
    for v in votes:
        if v.get("axis") != axis:
            continue
        a = v["pair"]["a"]
        b = v["pair"]["b"]
        winner = v.get("winner")
        if _is_skip(winner):
            continue
        if winner not in (a, b):
            # Defensive: ill-formed vote payload — surface but don't crash.
            continue
        acc[a]["plays"] += 1
        acc[b]["plays"] += 1
        acc[winner]["wins"] += 1
    return {slug: dict(d) for slug, d in acc.items()}


def ranking(wins: dict[str, dict[str, int]]) -> list[str]:
    """Sort slugs desc by wins/plays, tie-break by total plays then slug."""
    def score(slug):
        w = wins[slug]
        ratio = w["wins"] / w["plays"] if w["plays"] else 0.0
        return (-ratio, -w["plays"], slug)
    return sorted(wins.keys(), key=score)


def disagreement_index(votes: list[dict]) -> tuple[float, list[dict]]:
    """Return (index, per_pair_table).

    Index: fraction of pairs voted on BOTH axes where appeal-winner !=
    transport-winner. Pairs voted on only one axis are excluded.
    """
    by_pair: dict[tuple[str, str], dict[str, str | None]] = {}
    for v in votes:
        a = v["pair"]["a"]
        b = v["pair"]["b"]
        key = tuple(sorted((a, b)))
        winner = v.get("winner")
        if _is_skip(winner):
            continue
        slot = by_pair.setdefault(key, {})
        slot[v["axis"]] = winner

    table: list[dict] = []
    dual = 0
    disagree = 0
    for (a, b), axes in by_pair.items():
        if "appeal" not in axes or "transport" not in axes:
            continue
        dual += 1
        if axes["appeal"] != axes["transport"]:
            disagree += 1
        table.append({
            "a": a,
            "b": b,
            "appeal_winner": axes["appeal"],
            "transport_winner": axes["transport"],
            "agree": axes["appeal"] == axes["transport"],
        })
    return (disagree / dual if dual else 0.0), table


def spearman_correlation(rank_a: list[str], rank_b: list[str]) -> float:
    """Spearman rank correlation between two ordered slug lists.

    Uses Pearson correlation on the ranks; pure stdlib (statistics).
    Returns 0.0 when either ranking is empty.
    """
    common = [s for s in rank_a if s in rank_b]
    if len(common) < 2:
        return 0.0
    rank_pos_a = {slug: i for i, slug in enumerate(rank_a) if slug in rank_b}
    rank_pos_b = {slug: i for i, slug in enumerate(rank_b) if slug in rank_a}
    xs = [rank_pos_a[s] for s in common]
    ys = [rank_pos_b[s] for s in common]
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return 0.0


# ---------------------------------------------------------------------------
# Aggregator (one or many result files for a single rater session)
# ---------------------------------------------------------------------------

def aggregate(results_files: list[Path]) -> dict:
    """Merge votes across files, recompute everything from scratch.

    Returns a dict in the shape of the results schema. Even if the
    input files already carried wins_ratio/ranking, we recompute so
    multi-file aggregation is correct.
    """
    if not results_files:
        raise ValueError("aggregate() requires at least 1 results file")

    # Load + validate each.
    payloads = []
    for p in results_files:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        errors = validate_results(data)
        if errors:
            ptr = "/" + "/".join(str(s) for s in errors[0].path)
            raise ValueError(f"{p}: schema invalid at {ptr}: {errors[0].message}")
        payloads.append(data)

    head = payloads[0]
    raters = sorted({p["rater"] for p in payloads})
    starts = sorted(p["session_start"] for p in payloads)
    ends = sorted(p["session_end"] for p in payloads)
    votes: list[dict] = []
    direct_picks: list[str] = []
    for p in payloads:
        votes.extend(p["votes"])
        for d in p.get("direct_picks", []):
            if d not in direct_picks:
                direct_picks.append(d)

    wa = wins_ratio(votes, "appeal")
    wt = wins_ratio(votes, "transport")
    ra = ranking(wa)
    rt = ranking(wt)
    di, pair_table = disagreement_index(votes)
    sp = spearman_correlation(ra, rt)

    return {
        "experiment_id": head["experiment_id"],
        "rater": ", ".join(raters),
        "session_start": starts[0],
        "session_end": ends[-1],
        "votes": votes,
        "direct_picks": direct_picks,
        "wins_ratio_appeal": wa,
        "wins_ratio_transport": wt,
        "ranking_appeal": ra,
        "ranking_transport": rt,
        "disagreement_index": round(di, 6),
        "spearman_appeal_transport": round(sp, 6),
        "_per_pair_disagreement": pair_table,
    }


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------

def _halo_flag(spearman: float) -> str:
    if spearman > 0.85:
        return "halo (raters mostly used appeal as a proxy for transport)"
    if spearman < 0.5:
        return "working as intended (axes capture distinct signals)"
    return "ambiguous (mild halo)"


def _ratio_line(slug: str, wins: dict[str, dict[str, int]]) -> str:
    w = wins.get(slug, {"wins": 0, "plays": 0})
    if w["plays"] == 0:
        return f"  - `{slug}` — 0/0"
    return f"  - `{slug}` — {w['wins']}/{w['plays']} ({w['wins']/w['plays']:.0%})"


def render_summary(
    aggregated: dict,
    *,
    hypotheses: dict[str, dict] | None = None,
) -> str:
    hypotheses = hypotheses or {}
    out: list[str] = []
    out.append(f"# Results — {aggregated['experiment_id']}")
    out.append("")
    out.append(f"**Rater:** {aggregated['rater']}")
    out.append(f"**Sessions:** {aggregated['session_start']} → {aggregated['session_end']}")
    out.append(f"**Votes:** {len(aggregated['votes'])}")
    out.append(
        f"**Spearman ρ(appeal, transport):** "
        f"{aggregated['spearman_appeal_transport']:.3f} — "
        f"{_halo_flag(aggregated['spearman_appeal_transport'])}"
    )
    out.append(f"**Disagreement index:** {aggregated['disagreement_index']:.3f}")
    out.append("")

    out.append("## Top 5 by appeal")
    for slug in aggregated["ranking_appeal"][:5]:
        out.append(_ratio_line(slug, aggregated["wins_ratio_appeal"]))
    out.append("")

    out.append("## Top 5 by transport")
    for slug in aggregated["ranking_transport"][:5]:
        out.append(_ratio_line(slug, aggregated["wins_ratio_transport"]))
    out.append("")

    out.append("## Bottom 3 by appeal")
    for slug in aggregated["ranking_appeal"][-3:][::-1]:
        out.append(_ratio_line(slug, aggregated["wins_ratio_appeal"]))
    out.append("")

    out.append("## Bottom 3 by transport")
    for slug in aggregated["ranking_transport"][-3:][::-1]:
        out.append(_ratio_line(slug, aggregated["wins_ratio_transport"]))
    out.append("")

    out.append("## Per-pair disagreement (top 10)")
    pair_table = aggregated.get("_per_pair_disagreement", [])
    disagree = [p for p in pair_table if not p["agree"]]
    if not disagree:
        out.append("(none — all dual-axis pairs agreed)")
    else:
        out.append("| variant A | variant B | appeal winner | transport winner |")
        out.append("|---|---|---|---|")
        for row in disagree[:10]:
            out.append(
                f"| `{row['a']}` | `{row['b']}` | "
                f"`{row['appeal_winner']}` | `{row['transport_winner']}` |"
            )
    out.append("")

    out.append("## Suggested corpus entries")
    out.append("")
    out.append("Paste the relevant entries into `design-guide/gruene-corpus.md` "
               "with provenance tagging (per CONTEXT.md decision 11).")
    out.append("")
    out.append("### Winners (top 3)")
    for axis, ranking_list in (
        ("appeal", aggregated["ranking_appeal"]),
        ("transport", aggregated["ranking_transport"]),
    ):
        out.append(f"#### Top-3 by {axis}")
        for slug in ranking_list[:3]:
            h = hypotheses.get(slug, {})
            out.append(
                f"- **{h.get('name', slug)}** "
                f"(`{slug}`, axes: `{', '.join(h.get('axis_commitments', []))}`)\n"
                f"  - rationale: {h.get('rationale', '(unknown)')}\n"
                f"  - provenance: experiment {aggregated['experiment_id']}, "
                f"run {aggregated['rater']}, axis: {axis}"
            )
        out.append("")

    out.append("### Losers (bottom 3)")
    for axis, ranking_list in (
        ("appeal", aggregated["ranking_appeal"]),
        ("transport", aggregated["ranking_transport"]),
    ):
        out.append(f"#### Bottom-3 by {axis}")
        for slug in ranking_list[-3:][::-1]:
            h = hypotheses.get(slug, {})
            out.append(
                f"- **{h.get('name', slug)}** "
                f"(`{slug}`, axes: `{', '.join(h.get('axis_commitments', []))}`)\n"
                f"  - rationale: {h.get('rationale', '(unknown)')}\n"
                f"  - provenance: experiment {aggregated['experiment_id']}, "
                f"run {aggregated['rater']}, axis: {axis} (loser)"
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="experiment-results",
        description="Aggregate voting results into rankings + SUMMARY.md.",
    )
    ap.add_argument("exp_id", nargs="?", help="Experiment id.")
    ap.add_argument("results", nargs="*",
                    help="Optional results JSON paths; default globs "
                         "experiments/<exp_id>/results/*.json.")
    args = ap.parse_args(argv)

    if not args.exp_id:
        ap.print_help()
        return 0

    exp_id = args.exp_id
    if args.results:
        files = [Path(p) for p in args.results]
    else:
        files = sorted(
            Path(p) for p in glob.glob(
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
    summary_md = render_summary(agg, hypotheses=hyps)

    out_dir = ROOT / "experiments" / exp_id / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "SUMMARY.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    print(
        f"results -> {summary_path.relative_to(ROOT)} "
        f"({len(agg['votes'])} votes, "
        f"{len(agg['ranking_appeal'])} variants, "
        f"disagreement {agg['disagreement_index']:.2f}, "
        f"spearman {agg['spearman_appeal_transport']:.2f})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
