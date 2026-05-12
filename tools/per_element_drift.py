#!/usr/bin/env python3
"""Per-element drift attribution — aggregates diff_bboxes.json into per-anname
contribution table. Identifies which template elements account for the most
visual_diff mismatch pixels, so the next converter fix targets the highest-
leverage slots first.

Usage:
    python3 tools/per_element_drift.py \
        --diff-bboxes build/validation/<slug>/diff_bboxes.json \
        --visual-diff build/validation/<slug>/visual_diff.json \
        --out build/validation/<slug>/per_element_drift.yml

Schema: see per_element_drift.yml example in Phase E section of Issue #37.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

UNATTRIBUTED_KEY = "__unattributed__"


def aggregate_per_element(diff_bboxes: dict, visual_diff: dict) -> dict:
    """Group bbox area_px sums per attributed_slot per page; compute percentages."""
    pages_out = []
    for page_idx, page in enumerate(diff_bboxes.get("pages", [])):
        vd_page = visual_diff["pages"][page_idx]
        total_mismatch_px = vd_page.get("mismatch_pixels", 0)
        page_mismatch_pct = vd_page.get("mismatch_pct", 0.0)

        per_slot_px: dict[str, int] = defaultdict(int)
        per_slot_bbox_count: dict[str, int] = defaultdict(int)

        for bbox in page.get("bboxes", []):
            slot = bbox.get("attributed_slot") or UNATTRIBUTED_KEY
            per_slot_px[slot] += bbox.get("area_px", 0)
            per_slot_bbox_count[slot] += 1

        contributions = []
        for slot, px in per_slot_px.items():
            contributions.append(
                {
                    "slot": slot,
                    "mismatch_px_summed": px,
                    "pct_of_page_mismatch": round(px / total_mismatch_px * 100, 2)
                    if total_mismatch_px
                    else 0.0,
                    "pct_of_page_total_drift": round(
                        px / total_mismatch_px * page_mismatch_pct, 3
                    )
                    if total_mismatch_px
                    else 0.0,
                    "bbox_count": per_slot_bbox_count[slot],
                }
            )

        contributions.sort(key=lambda c: -c["mismatch_px_summed"])

        pages_out.append(
            {
                "page": page_idx,
                "total_mismatch_pct": round(page_mismatch_pct, 4),
                "total_mismatch_px": total_mismatch_px,
                "bbox_count": sum(per_slot_bbox_count.values()),
                "top_contributors": contributions[:20],
            }
        )

    return {
        "template": visual_diff.get("template") or diff_bboxes.get("template_slug", ""),
        "pages": pages_out,
    }


def _yaml_dump(payload: dict) -> str:
    """Deterministic YAML: sort_keys, no timestamps, consistent float repr."""
    return yaml.dump(
        payload, sort_keys=True, allow_unicode=True, default_flow_style=False
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Per-element drift attribution from diff_bboxes.json + visual_diff.json.",
    )
    ap.add_argument(
        "--diff-bboxes", type=Path, required=True, help="Path to diff_bboxes.json"
    )
    ap.add_argument(
        "--visual-diff", type=Path, required=True, help="Path to visual_diff.json"
    )
    ap.add_argument(
        "--out", type=Path, required=True, help="Output path for per_element_drift.yml"
    )
    args = ap.parse_args(argv)

    if not args.diff_bboxes.exists():
        print(f"per_element_drift: missing {args.diff_bboxes}", file=sys.stderr)
        return 1
    if not args.visual_diff.exists():
        print(f"per_element_drift: missing {args.visual_diff}", file=sys.stderr)
        return 1

    diff_bboxes = json.loads(args.diff_bboxes.read_text(encoding="utf-8"))
    visual_diff = json.loads(args.visual_diff.read_text(encoding="utf-8"))

    result = aggregate_per_element(diff_bboxes, visual_diff)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(result), encoding="utf-8")

    # Summary line
    for page in result["pages"]:
        top = page["top_contributors"]
        if top:
            leader = top[0]
            print(
                f"[{result['template'] or args.diff_bboxes.parent.name}] "
                f"per_element_drift: top contributor page {page['page'] + 1} is "
                f"{leader['slot']} ({leader['pct_of_page_total_drift']:.1f}pp of page drift)"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
