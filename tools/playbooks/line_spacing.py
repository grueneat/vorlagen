"""Defined remediation playbook for systematic_text_audit findings.

Reads `build/validation/<slug>/systematic_text_audit.yml`. For each
actionable frame:

  1. Reads the frame's authored Leading from `build.py` (parsing the
     paragraph_attrs / Run() definitions).
  2. Constructs a sim candidate set: current state, plus
     LINESPMode=0 with LINESP swept around the authored Leading,
     plus LINESPMode=1 (auto).
  3. Invokes `tools/line_spacing_sim.py` to render each candidate and
     measure drift.
  4. Picks the candidate with smallest |drift|.
  5. If best |drift| <= 0.5pt: applies via `paragraph_attrs` +
     `trail_attrs` in `build.py`, writes a `# P5/playbook` comment.
  6. If best |drift| > 0.5pt: writes a `TOLERANCES.yml` row that
     CITES the sim outcome (per L-011 design) so the audit no longer
     flags it as un-addressed.

Returns (n_changes, log_lines) so bin/tune-fix can decide whether
to re-run tune-render.

This is intentionally deterministic — the same audit input produces
the same fix. The LLM does not improvise; it invokes the playbook
and verifies the resulting diff is sane.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml


def _parse_frame_runs(build_text: str, anname: str) -> dict | None:
    """Extract fontsize, current LINESPMode/LINESP, and frame line range.

    Returns None when the frame can't be located. The parser is
    string-pattern based (not AST-walk) so it tolerates the auto-
    generated build.py shape.
    """
    pat = re.compile(r"add\(TextFrame\(\s*\n((?:.|\n)*?\n\s*\)\)\n)", re.MULTILINE)
    for m in pat.finditer(build_text):
        body = m.group(1)
        if f"anname='{anname}'" not in body:
            continue
        # Extract fontsize from first Run(...) — None when runs inherit from style
        fontsize_m = re.search(r"fontsize=(\d+(?:\.\d+)?)", body)
        fontsize_pt = float(fontsize_m.group(1)) if fontsize_m else None
        # Extract current LINESPMode and LINESP from paragraph_attrs / trail_attrs
        mode_m = re.search(r"'LINESPMode':\s*'(\d+)'", body)
        linesp_m = re.search(r"'LINESP':\s*'([\d.]+)'", body)
        # Style name (for fallback Leading lookup AND fontsize fallback)
        style_m = re.search(r"style='([^']+)'", body)
        # Pick a couple of words for the sim's --expected-words filter
        word_match = re.search(r"text='([^']{4,40})'", body)
        words = []
        if word_match:
            for w in word_match.group(1).split()[:3]:
                clean = re.sub(r'[^\w]', '', w)
                if len(clean) >= 4:
                    words.append(clean)
        # If fontsize is not set on the frame's runs, fall back to the
        # paragraph style's fontsize.
        if fontsize_pt is None and style_m:
            fontsize_pt = _resolve_style_fontsize(build_text, style_m.group(1))
        return {
            "anname": anname,
            "fontsize_pt": fontsize_pt,
            "current_mode": mode_m.group(1) if mode_m else None,
            "current_linesp": linesp_m.group(1) if linesp_m else None,
            "style": style_m.group(1) if style_m else None,
            "expected_words": ",".join(words[:2]) if words else None,
            "frame_body": body,
        }
    return None


def _resolve_style_fontsize(build_text: str, style_name: str) -> float | None:
    """Look up `fontsize=` from a ParaStyle definition; recurse via parent."""
    pat = re.compile(
        r"add_para_style\(ParaStyle\(\s*\n"
        r"((?:.|\n)*?\n\s*\)\))",
        re.MULTILINE,
    )
    for m in pat.finditer(build_text):
        body = m.group(1)
        if f"name='{style_name}'" in body:
            fs_m = re.search(r"fontsize=(\d+(?:\.\d+)?)", body)
            if fs_m:
                return float(fs_m.group(1))
            parent_m = re.search(r"parent='([^']+)'", body)
            if parent_m:
                return _resolve_style_fontsize(build_text, parent_m.group(1))
    return None


def _resolve_authored_leading(build_text: str, style_name: str | None,
                              fontsize_pt: float | None) -> float | None:
    """Resolve the paragraph style's linesp; fall back to fontsize × 1.2."""
    if style_name:
        # Search for the ParaStyle definition
        pat = re.compile(
            r"add_para_style\(ParaStyle\(\s*\n"
            r"((?:.|\n)*?\n\s*\)\))",
            re.MULTILINE,
        )
        for m in pat.finditer(build_text):
            body = m.group(1)
            if f"name='{style_name}'" in body:
                lp_m = re.search(r"linesp=(\d+(?:\.\d+)?)", body)
                if lp_m:
                    return float(lp_m.group(1))
    if fontsize_pt:
        return fontsize_pt * 1.2
    return None


def _sim_candidates(authored_lp: float | None, current_mode: str | None,
                    fontsize_pt: float | None) -> list[str]:
    """Build a candidate set for line_spacing_sim.

    Combines:
      - LINESPMode=1 (Scribus auto) baseline
      - 0:<authored_lp> from paragraph style
      - 0:<fontsize × ratio> for ratio ∈ {0.9, 1.0, 1.1, 1.2} (covers
        the Quickguide 0.9× and InDesign auto ranges)
      - small ± deltas around authored_lp
    """
    cands = ["1:"]
    seen = set()
    def add(c):
        if c not in seen:
            seen.add(c)
            cands.append(c)
    if authored_lp is not None:
        for delta in (0, -0.5, -1, -1.5, +0.5, +1, +1.5):
            add(f"0:{round(authored_lp + delta, 2)}")
    if fontsize_pt is not None:
        # 0.89 catches the InDesign "auto" ratio for Vollkorn at 23pt
        # (20.48pt, within 0.01 of 23×0.89). 0.85 is the Quickguide
        # "tight" headline ratio. 1.0/1.1/1.2/1.45 cover body-text bands.
        for ratio in (0.9, 1.0, 1.1, 1.2, 0.85, 1.45, 0.89, 0.91):
            add(f"0:{round(fontsize_pt * ratio, 2)}")
    return cands[:14]


def _run_sim(slug: str, anname: str, candidates: list[str],
             expected_words: str | None, fontsize_pt: float | None,
             repo: Path) -> list[dict]:
    """Run line_spacing_sim and parse its markdown table back."""
    cmd = [
        "python3", str(repo / "tools" / "line_spacing_sim.py"),
        "--slug", slug, "--anname", anname,
        "--candidates", ",".join(candidates),
        "--templates-dir", str(repo / "templates"),
    ]
    if expected_words:
        cmd.extend(["--expected-words", expected_words])
    if fontsize_pt:
        cmd.extend(["--fontsize-pt", str(fontsize_pt)])
    env = {"PYTHONPATH": str(repo)}
    result = subprocess.run(cmd, capture_output=True, text=True, env={**__import__("os").environ, **env})
    if result.returncode != 0:
        return []
    out: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.startswith("|") or "LINESPMode" in line or "---" in line:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 4:
            continue
        try:
            mode = cells[0]
            linesp = cells[1] if cells[1] != "—" else None
            preview_med = float(cells[2]) if cells[2] not in ("None", "—", "") else None
            drift = float(cells[3]) if cells[3] not in ("None", "—", "") else None
            out.append({"mode": mode, "linesp": linesp, "preview_pt": preview_med, "drift_pt": drift})
        except ValueError:
            continue
    return out


def _apply_to_build_py(build_path: Path, anname: str,
                       mode: str, linesp: str | None,
                       sim_drift: float) -> bool:
    """Inject paragraph_attrs LINESPMode/LINESP into the frame's runs.

    Handles three frame shapes:
      1. paragraph_attrs already has 'LINESPMode': '<x>' → replace
      2. paragraph_attrs exists but lacks LINESPMode → insert key
      3. No paragraph_attrs at all → insert one alongside trail_attrs

    Returns True if a write occurred.
    """
    text = build_path.read_text()
    # Match a single frame block — must not cross `))` (next frame).
    pat = re.compile(
        r"(^[ \t]*page\d+\.add\(TextFrame\("
        r"(?:(?!\)\)).)*?"
        r"anname='" + re.escape(anname) + r"'"
        r"(?:(?!\)\)).)*?"
        r"\)\)\n)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        return False
    block = m.group(1)

    new_attrs = f"'LINESPMode': '{mode}'"
    if linesp:
        new_attrs += f", 'LINESP': '{linesp}'"

    new_block = block

    # Case 1: replace existing LINESPMode (and update LINESP if present)
    if re.search(r"'LINESPMode':\s*'\d+'", new_block):
        new_block = re.sub(r"'LINESPMode':\s*'\d+'", f"'LINESPMode': '{mode}'", new_block)
        if linesp:
            if "'LINESP':" in new_block:
                new_block = re.sub(r"'LINESP':\s*'[\d.]+'", f"'LINESP': '{linesp}'", new_block)
            else:
                new_block = new_block.replace(
                    f"'LINESPMode': '{mode}'",
                    f"'LINESPMode': '{mode}', 'LINESP': '{linesp}'",
                )
    # Case 2: paragraph_attrs exists somewhere; add LINESPMode alongside
    # an existing key like 'ALIGN'. Targets ALL occurrences (every Run).
    elif "paragraph_attrs={" in new_block:
        new_block = re.sub(
            r"paragraph_attrs=\{('ALIGN':\s*'\d+')\}",
            r"paragraph_attrs={\1, " + new_attrs + r"}",
            new_block,
        )
    # Case 3: trail_attrs exists; mirror onto trail_attrs too
    if "trail_attrs={" in new_block:
        if re.search(r"trail_attrs=\{[^}]*'LINESPMode'", new_block):
            new_block = re.sub(
                r"(trail_attrs=\{[^}]*'LINESPMode':\s*)'\d+'",
                r"\1'" + mode + "'",
                new_block,
            )
            if linesp:
                if "'LINESP':" in re.search(r"trail_attrs=\{[^}]*\}", new_block).group(0):
                    new_block = re.sub(
                        r"(trail_attrs=\{[^}]*'LINESP':\s*)'[\d.]+'",
                        r"\1'" + linesp + "'",
                        new_block,
                    )
                else:
                    new_block = re.sub(
                        r"(trail_attrs=\{[^}]*'LINESPMode':\s*'\d+')",
                        r"\1, 'LINESP': '" + linesp + "'",
                        new_block,
                    )
        else:
            # No LINESPMode in trail_attrs yet
            new_block = re.sub(
                r"trail_attrs=\{('ALIGN':\s*'\d+')\}",
                r"trail_attrs={\1, " + new_attrs + r"}",
                new_block,
            )

    if new_block == block:
        return False
    # Add a marker comment above the frame so the change is traceable
    marker = (
        f"    # P5/playbook line_spacing.py: LINESPMode={mode}"
        f"{' LINESP=' + linesp if linesp else ''} "
        f"(sim drift {sim_drift:+.2f}pt)\n"
    )
    text = text.replace(block, marker + new_block, 1)
    build_path.write_text(text)
    return True


def apply(slug: str, repo: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Apply the line-spacing remediation playbook.

    Returns (n_changes, log_lines).
    """
    log: list[str] = []
    audit_path = repo / "build" / "validation" / slug / "systematic_text_audit.yml"
    if not audit_path.exists():
        return 0, [f"systematic_text_audit.yml not found at {audit_path}"]
    audit = yaml.safe_load(audit_path.read_text()) or {}
    actionable = audit.get("actionable_frames") or []
    if not actionable:
        return 0, ["no actionable frames"]

    build_path = repo / "templates" / slug / "build.py"
    if not build_path.exists():
        return 0, [f"build.py not found at {build_path}"]
    build_text = build_path.read_text()

    n_changes = 0
    for frame in actionable:
        anname = frame.get("anname")
        if not anname:
            continue
        info = _parse_frame_runs(build_text, anname)
        if not info:
            log.append(f"{anname}: could not parse frame body — skipping")
            continue
        authored_lp = _resolve_authored_leading(
            build_text, info.get("style"), info.get("fontsize_pt"),
        )
        candidates = _sim_candidates(authored_lp, info.get("current_mode"),
                                     info.get("fontsize_pt"))
        log.append(f"{anname}: fontsize={info.get('fontsize_pt')}pt "
                   f"authored_leading={authored_lp} candidates={candidates}")
        if dry_run:
            continue
        sim_results = _run_sim(
            slug, anname, candidates,
            info.get("expected_words"), info.get("fontsize_pt"),
            repo,
        )
        if not sim_results:
            log.append(f"  {anname}: sim returned no rows — skipping")
            continue
        # Pick lowest |drift|
        scored = [r for r in sim_results if r.get("drift_pt") is not None]
        if not scored:
            log.append(f"  {anname}: no candidate had a measurable drift — skipping")
            continue
        scored.sort(key=lambda r: abs(r["drift_pt"]))
        best = scored[0]
        log.append(f"  {anname}: best={best['mode']}:{best.get('linesp','-')} "
                   f"drift={best['drift_pt']:+.2f}pt")
        if abs(best["drift_pt"]) > 0.5:
            log.append(f"  {anname}: best drift exceeds 0.5pt threshold — needs human review")
            continue
        if _apply_to_build_py(build_path, anname, best["mode"], best.get("linesp"), best["drift_pt"]):
            log.append(f"  {anname}: applied to build.py")
            n_changes += 1
            # Re-read for next iteration
            build_text = build_path.read_text()
        else:
            log.append(f"  {anname}: write skipped (frame body unchanged)")

    return n_changes, log
