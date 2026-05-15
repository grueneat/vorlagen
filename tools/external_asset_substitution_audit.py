#!/usr/bin/env python3
"""External-asset substitution audit — fails when a frame using an
`external:` (placeholder) asset is NOT in INJECT_MAP and lacks an
explicit `# noinject:` justification.

Closes the L-016 gap: opt-in INJECT_MAP let placeholder content slip
through to gallery previews. Every external-asset frame must either
be substituted with a library AI image OR justify the exclusion in
a way the audit can read.

Algorithm:
  1. Read meta.yml::asset_policy::external — set of asset basenames
     classified as "placeholder content".
  2. Read build.py:
     - Parse INJECT_MAP entries (anname → library_id mappings)
     - Parse `# noinject: <reason>` markers above frames
     - Parse every ImageFrame's anname + image= path
  3. For each ImageFrame whose image= asset is in the external bucket:
     - PASS if anname ∈ INJECT_MAP
     - PASS if frame has `# noinject:` marker
     - FAIL otherwise

Output: build/validation/<slug>/external_asset_substitution_audit.yml
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _parse_inject_map(build_text: str) -> set[str]:
    """Extract anname keys from `INJECT_MAP = {...}`."""
    m = re.search(r"INJECT_MAP\s*:\s*dict\[[^\]]*\]\s*=\s*\{([^}]*)\}", build_text, re.DOTALL)
    if not m:
        return set()
    body = m.group(1)
    return set(re.findall(r'"([^"]+)"\s*:', body))


def _parse_image_frames(build_text: str) -> list[dict]:
    """For each `pageN.add(ImageFrame(...))` extract anname, image= path,
    and any `# noinject:` marker on the line(s) immediately above."""
    frames = []
    pat = re.compile(
        r"((?:^[ \t]*#[^\n]*\n)*)"  # optional comment lines above
        r"^[ \t]*page\d+\.add\(ImageFrame\("
        r"((?:(?!\)\)).)*?)"
        r"\)\)\n",
        re.MULTILINE | re.DOTALL,
    )
    for m in pat.finditer(build_text):
        comments = m.group(1)
        body = m.group(2)
        anname_m = re.search(r"anname='(\w+)'", body)
        if not anname_m:
            continue
        image_m = re.search(r"image='([^']*)'", body)
        if not image_m:
            continue  # skip frames without image= ref (inline data)
        noinject_m = re.search(r"# noinject:\s*(.*)$", comments, re.MULTILINE)
        frames.append({
            "anname": anname_m.group(1),
            "image_basename": Path(image_m.group(1)).name,
            "noinject_reason": noinject_m.group(1).strip() if noinject_m else None,
        })
    return frames


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", type=Path, default=ROOT / "templates")
    ap.add_argument("--out-yaml", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args(argv)

    template_dir = args.templates_dir / args.slug
    meta_path = template_dir / "meta.yml"
    build_path = template_dir / "build.py"
    if not meta_path.exists() or not build_path.exists():
        print("SKIPPED: missing meta.yml or build.py", file=sys.stderr)
        return 0

    meta = yaml.safe_load(meta_path.read_text()) or {}
    external_assets = set(meta.get("asset_policy", {}).get("external", []))
    if not external_assets:
        print("SKIPPED: no external: assets declared", file=sys.stderr)
        return 0

    build_text = build_path.read_text()
    inject_map = _parse_inject_map(build_text)
    frames = _parse_image_frames(build_text)

    findings = []
    for f in frames:
        if f["image_basename"] not in external_assets:
            continue  # brand-embedded asset — not a substitution candidate
        if f["anname"] in inject_map:
            continue  # explicitly substituted
        if f["noinject_reason"]:
            continue  # explicitly justified exclusion
        findings.append({
            "anname": f["anname"],
            "image_basename": f["image_basename"],
            "verdict": "missing_substitution_or_justification",
            "fix": (
                f"Add to INJECT_MAP: \"{f['anname']}\": \"<library_id>\" "
                f"OR add a comment line `# noinject: <reason>` immediately "
                f"above the `pageN.add(ImageFrame(...))` for {f['anname']}."
            ),
        })

    out = {
        "slug": args.slug,
        "summary": {
            "external_assets": len(external_assets),
            "image_frames_using_external": sum(
                1 for f in frames if f["image_basename"] in external_assets
            ),
            "in_inject_map": sum(
                1 for f in frames
                if f["image_basename"] in external_assets and f["anname"] in inject_map
            ),
            "noinject_justified": sum(
                1 for f in frames
                if f["image_basename"] in external_assets and f["noinject_reason"]
            ),
            "missing": len(findings),
        },
        "findings": findings,
        "ok": len(findings) == 0,
    }
    if args.out_yaml:
        args.out_yaml.parent.mkdir(parents=True, exist_ok=True)
        args.out_yaml.write_text(yaml.safe_dump(out, sort_keys=False))
    if args.out_md:
        lines = [f"# External asset substitution audit — {args.slug}", ""]
        s = out["summary"]
        lines.append(f"- external assets declared: {s['external_assets']}")
        lines.append(f"- frames using external: {s['image_frames_using_external']}")
        lines.append(f"- in INJECT_MAP: {s['in_inject_map']}")
        lines.append(f"- explicitly noinject: {s['noinject_justified']}")
        lines.append(f"- **missing: {s['missing']}**")
        for f in findings:
            lines.append("")
            lines.append(f"### {f['anname']} ({f['image_basename']})")
            lines.append(f"- {f['verdict']}")
            lines.append(f"- LLM ACTION: {f['fix']}")
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text("\n".join(lines))

    print(f"external-asset-substitution-audit: {len(findings)} missing")
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
