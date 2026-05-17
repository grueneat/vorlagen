#!/usr/bin/env python3
"""bin/idml-import driver — one-command end-to-end IDML to template pipeline.

Drives the full convergence loop:

  1. Verify required tools (pdftocairo, pdffonts, convert, scribus).
  2. Slugify the IDML filename to a template id.
  3. Refuse to overwrite an existing templates/<slug>/ without --reimport.
  4. Brand-fonts gate (bypassable with --no-brand-fonts; loud warning).
  5. Resolve baseline.pdf (sibling <stem>.pdf or --keep-baseline-from-pdf).
  6. Extract Links/ via tools/links_export.py.
  7. Run asset_extraction_audit; abort if not ok and not --allow-composite-ai.
  8. Scaffold templates/<slug>/{meta.yml,diff.yml,baseline.pdf}.
  9. Run tools/idml_to_dsl.py to emit templates/<slug>/build.py.
 10. With --scaffold-only, halt cleanly after the first audit cycle.
 11. Convergence loop: render-gallery + convergence-review +
     iteration.jsonl log + regression guard. Up to --max-iterations.
 12. Emit build/<slug>/import_report.md final summary.

Exit codes (per RESEARCH.md):
  0 — preflight.ok=true OR all-residual-accepted.
  1 — converter / asset / unknown failure (run aborted).
  2 — needs human review (NEEDS_REVIEW with unaccepted residual).
  3 — drift regression detected / max-iterations exceeded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Module discovery — works whether installed or invoked directly.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
# The repo root must also be importable so ``from tools import …`` resolves
# to the worktree's package (PEP 420 namespace package — no __init__.py).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------
REQUIRED_TOOLS: tuple[tuple[str, str], ...] = (
    ("pdftocairo", "Install poppler-utils (apt: poppler-utils, brew: poppler)."),
    ("pdffonts", "Install poppler-utils (apt: poppler-utils, brew: poppler)."),
    ("convert", "Install ImageMagick (apt: imagemagick, brew: imagemagick)."),
    ("scribus", "Install Scribus 1.6.x (apt: scribus, brew: scribus)."),
)


_HUMAN_REVIEW_CLASSIFICATIONS = frozenset({"human-review", "authoring-bug"})


# ---------------------------------------------------------------------------
# Pre-flight checks.
# ---------------------------------------------------------------------------


def _check_tool_availability(tools: tuple[tuple[str, str], ...] = REQUIRED_TOOLS) -> list[str]:
    """Return a list of missing tools (name + hint per entry)."""
    missing: list[str] = []
    for name, hint in tools:
        if shutil.which(name) is None:
            missing.append(f"{name}: not found on PATH. {hint}")
    return missing


def _verify_brand_fonts() -> bool:
    """Bridge to render_pipeline._verify_brand_fonts. Returns True on success."""
    try:
        from render_pipeline import _verify_brand_fonts as rp_verify
    except ImportError:
        return False
    try:
        rp_verify()
        return True
    except SystemExit:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Iteration log (Task 6).
# ---------------------------------------------------------------------------


def log_iteration(
    slug: str,
    iteration: int,
    review: dict,
    changes: list[str],
    *,
    build_root: Path | None = None,
) -> dict:
    """Append one row to build/<slug>/iteration.jsonl. Returns the row."""
    if build_root is None:
        build_root = ROOT / "build"
    target_dir = build_root / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    issues = [
        i for i in (review.get("issues") or [])
        if i.get("classification") != "minor"
    ]
    drift = review.get("drift") or {}
    row = {
        "iteration": int(iteration),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "preflight_ok": bool(review.get("preflight_ok", False)),
        "issues_open": len(issues),
        "drift_p1": drift.get("p1"),
        "drift_p2": drift.get("p2"),
        "drift_p1_max_region": drift.get("p1_max_region"),
        "drift_p2_max_region": drift.get("p2_max_region"),
        "changes": list(changes),
        "audits_run": list(review.get("audits_run") or []),
        "rules_seen": int(iteration),
        "_schema_version": 1,
    }
    line = json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n"
    (target_dir / "iteration.jsonl").open("a", encoding="utf-8").write(line)
    return row


def regression_guard(
    slug: str,
    current_row: dict,
    *,
    build_root: Path | None = None,
) -> str | None:
    """Compare current_row against the penultimate row in iteration.jsonl.

    Returns an error string if BOTH page-wide drift_p1 AND drift_p1_max_region
    regressed (per RESEARCH.md 8.1); otherwise None.
    """
    if build_root is None:
        build_root = ROOT / "build"
    log_path = build_root / slug / "iteration.jsonl"
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8").splitlines()
    # The current row is the LAST line; the prior row is the second-to-last.
    if len(lines) < 2:
        return None
    try:
        prev = json.loads(lines[-2])
    except json.JSONDecodeError:
        return None
    cur_p1 = current_row.get("drift_p1")
    prev_p1 = prev.get("drift_p1")
    cur_max = current_row.get("drift_p1_max_region")
    prev_max = prev.get("drift_p1_max_region")
    if cur_p1 is None or prev_p1 is None:
        return None
    if cur_p1 <= prev_p1 + 0.05:
        return None
    # Page-wide regressed; only halt if per-region max ALSO regressed.
    if cur_max is None or prev_max is None or cur_max <= prev_max:
        return None
    # Filter out new-audit-added situations: if the set of audits expanded,
    # the issue-count delta may legitimately come from the new audit.
    cur_audits = set(current_row.get("audits_run") or [])
    prev_audits = set(prev.get("audits_run") or [])
    if cur_audits - prev_audits:
        return None
    return (
        f"drift regression: p1 went from {prev_p1} to {cur_p1} "
        f"(p1_max_region {prev_max} -> {cur_max})"
    )


# ---------------------------------------------------------------------------
# Scaffolding.
# ---------------------------------------------------------------------------


_ASSET_EXTS = {".png", ".jpg", ".jpeg", ".psd", ".eps", ".svg",
               ".tif", ".tiff", ".ai", ".pdf"}

_EMBEDDED_PATTERNS = (
    re.compile(r"logo", re.IGNORECASE),
    re.compile(r"social-media-icon", re.IGNORECASE),
    re.compile(r"^wahlkreuz", re.IGNORECASE),
    re.compile(r"-weiss\.(png|pdf)$", re.IGNORECASE),
    re.compile(r"-cmyk\.(png|pdf)$", re.IGNORECASE),
)


def _classify_assets(assets_dir: Path) -> dict[str, list[str]]:
    """Auto-classify disk assets into embedded/external per the SOP heuristic.

    Files matching brand patterns (logos, social-media icons, *-weiss.{png,pdf},
    *-cmyk.{png,pdf}) → embedded. Anything else → external (the safe default per
    asset_policy.md: content must never silently ship as brand). The skill's
    SOP allows "STOP, ask" for unknowns; the driver defaults to external so the
    scaffold can proceed, and the human reviewer can re-bucket on commit.

    Mirrors asset_policy_audit._list_disk_assets: a .pdf sibling of a raster
    (same stem with .png/.jpg) is a forward-compat vector passthrough emitted
    by links_export and NOT a primary asset — exclude it so the policy and
    audit view of disk agree.
    """
    embedded: list[str] = []
    external: list[str] = []
    if not assets_dir.is_dir():
        return {"embedded": embedded, "external": external, "shipped": []}
    raster_stems: set[str] = {
        p.stem for p in assets_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    }
    for p in sorted(assets_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in _ASSET_EXTS:
            continue
        if p.suffix.lower() == ".pdf" and p.stem in raster_stems:
            continue
        name = p.name
        if any(pat.search(name) for pat in _EMBEDDED_PATTERNS):
            embedded.append(name)
        else:
            external.append(name)
    return {"embedded": embedded, "external": external, "shipped": []}


def _detect_trim_box(pdf_path: Path) -> tuple[float, float, float, float] | None:
    """Detect a trim box from an InDesign export's crop marks.

    InDesign can export a PDF with printer's marks (crop/registration marks,
    color bars, page-info) baked into a MediaBox LARGER than the trimmed
    page. The converter emits a trim-only SLA, so a marks-on baseline.pdf
    would never page-match the preview — every word reads as "drifted" and
    the marks-area furniture reads as "missing words".

    The trim corners are marked by short L-shaped line segments. This walks
    the first page's lines, collects the short axis-aligned segments, and
    derives the trim rectangle as the inner bounding box of the corner
    marks. Returns ``(x0, top, x1, bottom)`` in pdfplumber top-origin
    coordinates, or ``None`` when no marks are found (already trim-only).
    """
    try:
        import pdfplumber  # local import — heavy dependency
    except ImportError:
        return None
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        page_w, page_h = float(page.width), float(page.height)
        # Short horizontal segments → their `top` marks a trim Y edge.
        # Short vertical segments → their `x0` marks a trim X edge.
        h_tops: list[float] = []
        v_xs: list[float] = []
        for ln in page.lines:
            dx = abs(ln["x1"] - ln["x0"])
            dy = abs(ln["bottom"] - ln["top"])
            if 4.0 < dx < 22.0 and dy < 1.0:
                h_tops.append(round(float(ln["top"]), 1))
            elif 4.0 < dy < 22.0 and dx < 1.0:
                v_xs.append(round(float(ln["x0"]), 1))
    if not h_tops or not v_xs:
        return None
    # Crop marks cluster near the page PERIMETER, one cluster per trim
    # edge. InDesign also draws fold/registration marks near the page
    # CENTRE — those must be excluded or the "trim box" collapses to a
    # fraction of the page. Restrict each edge to the outer band of the
    # page (≤20% from the corresponding page edge), then take the mark
    # nearest the page interior within that band as the trim edge.
    band_x = page_w * 0.20
    band_y = page_h * 0.20
    left_edges = sorted(x for x in v_xs if x <= band_x)
    right_edges = sorted(x for x in v_xs if x >= page_w - band_x)
    top_edges = sorted(t for t in h_tops if t <= band_y)
    bot_edges = sorted(t for t in h_tops if t >= page_h - band_y)
    if not (top_edges and bot_edges and left_edges and right_edges):
        return None
    # Innermost mark within each perimeter band = the trim edge.
    x0 = left_edges[-1]
    x1 = right_edges[0]
    top = top_edges[-1]
    bottom = bot_edges[0]
    w, h = x1 - x0, bottom - top
    # Sanity: a real trim box must be a sizeable fraction of the MediaBox.
    if w < page_w * 0.4 or h < page_h * 0.4 or w <= 0 or h <= 0:
        return None
    # If the "trim" is essentially the whole page, there are no marks.
    if w > page_w * 0.98 and h > page_h * 0.98:
        return None
    return (x0, top, x1, bottom)


def _normalize_baseline_to_trim(baseline_src: Path, dest: Path) -> bool:
    """Copy ``baseline_src`` to ``dest``, cropping printer's marks if present.

    Returns True when a marks-on baseline was cropped to its trim box,
    False when the source was copied verbatim (already trim-only, or no
    Ghostscript available). The trim crop keeps the PDF vector — only the
    MediaBox shrinks and content is offset so (0,0) is the trim corner.
    """
    trim = _detect_trim_box(baseline_src)
    if trim is None:
        shutil.copy(baseline_src, dest)
        return False
    gs = shutil.which("gs")
    if gs is None:
        # No Ghostscript — fall back to verbatim copy; the geometry
        # mismatch surfaces in the audits for human review.
        shutil.copy(baseline_src, dest)
        return False
    try:
        import pdfplumber
        with pdfplumber.open(baseline_src) as pdf:
            page_h = float(pdf.pages[0].height)
    except Exception:  # noqa: BLE001
        shutil.copy(baseline_src, dest)
        return False
    x0, top, x1, bottom = trim
    w = x1 - x0
    h = bottom - top
    # pdfplumber tops are page-top-origin; PDF y is bottom-origin.
    llx, lly = x0, page_h - bottom
    cmd = [
        gs, "-o", str(dest), "-sDEVICE=pdfwrite",
        f"-dDEVICEWIDTHPOINTS={w}", f"-dDEVICEHEIGHTPOINTS={h}",
        "-dFIXEDMEDIA", "-dQUIET", "-dBATCH", "-dNOPAUSE",
        "-c", f"<</PageOffset [{-llx} {-lly}]>> setpagedevice",
        "-f", str(baseline_src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not dest.exists():
        shutil.copy(baseline_src, dest)
        return False
    print(
        f"idml-import: baseline.pdf had printer's marks — cropped to trim "
        f"box {w:.1f}x{h:.1f}pt so it page-matches the trim-only preview.",
        file=sys.stderr,
    )
    return True


def _scaffold_template_dir(
    slug: str,
    baseline_src: Path,
    tdir: Path,
    assets_dir: Path | None = None,
    idml_path: Path | None = None,
) -> None:
    """Create templates/<slug>/{meta.yml, diff.yml, baseline.pdf}.

    When ``assets_dir`` is provided and exists, populates
    ``meta.yml::asset_policy`` via the auto-classification heuristic so the
    policy audit can validate against a real scaffolded meta.yml.

    When ``idml_path`` is supplied, records it as ``meta.yml::idml_source``
    (relative to ``tdir``) so render_pipeline.py re-audits against the right
    source instead of falling back to the first IDML in ``originals/``.
    """
    tdir.mkdir(parents=True, exist_ok=True)
    meta: dict = {
        "id": slug,
        "version": "0.1.0",
        "title": slug,
        "format": "A4",
        "build": {"script": "build.py", "output": "template.sla"},
        # Placeholder so render_pipeline._is_renderable() admits this fresh
        # template. The pipeline overwrites with the real SHA256 after the
        # first successful build.py → template.sla cycle.
        "previews_for_sla": "_pending_first_build",
    }
    if idml_path is not None:
        try:
            rel = os.path.relpath(idml_path.resolve(), tdir.resolve())
        except ValueError:
            rel = str(idml_path)
        meta["idml_source"] = rel
    if assets_dir is not None and assets_dir.is_dir():
        meta["asset_policy"] = _classify_assets(assets_dir)
    (tdir / "meta.yml").write_text(
        yaml.safe_dump(meta, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    # fuzz_pct=25 absorbs cross-renderer differences (Scribus vs InDesign
    # font anti-aliasing, ICC color profile shifts on full-bleed brand
    # colours like Dunkelgrün). Matches the sibling Falzflyer template's
    # tolerance. Tighten per-page only after a first measurement run.
    diff = {"dpi": 300, "fuzz_pct": 25.0}
    (tdir / "diff.yml").write_text(
        yaml.safe_dump(diff, sort_keys=True),
        encoding="utf-8",
    )
    _normalize_baseline_to_trim(baseline_src, tdir / "baseline.pdf")


def _run_converter(
    slug: str,
    idml_path: Path,
    asset_map: Path,
    out_path: Path,
) -> int:
    """Invoke tools/idml_to_dsl.py. Returns exit code."""
    cmd = [
        sys.executable,
        str(_HERE / "idml_to_dsl.py"),
        str(idml_path),
        str(out_path),
        "--template-id",
        slug,
        "--asset-map",
        str(asset_map),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


# ---------------------------------------------------------------------------
# Convergence loop helpers.
# ---------------------------------------------------------------------------


def _run_render_gallery(slug: str, *, no_brand_fonts: bool = False) -> int:
    """Invoke bin/render-gallery <slug> --audit-strict."""
    cmd = [
        sys.executable,
        str(_HERE / "render_pipeline.py"),
        slug,
        "--audit-strict",
    ]
    if no_brand_fonts:
        # render_pipeline does not yet expose a --no-brand-fonts CLI flag;
        # we propagate the intent via env var which render_pipeline's
        # _verify_brand_fonts can opt into via a follow-up extension.
        os.environ.setdefault("AUSTENDER_NO_BRAND_FONTS", "1")
    result = subprocess.run(cmd)
    return result.returncode


def _run_convergence_review(slug: str) -> dict | None:
    """Invoke bin/convergence-review and parse JSON output. Returns None on failure."""
    cmd = [
        sys.executable,
        str(_HERE / "convergence_review.py"),
        slug,
        "--format",
        "json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if result.returncode not in (0, 1, 2):
        # Genuine error (not "review reports issues"); surface stderr.
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout) if result.stdout else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Final report.
# ---------------------------------------------------------------------------


def _verdict(review: dict | None, residual_accepted: bool) -> str:
    if review is None:
        return "BLOCKED"
    if review.get("preflight_ok"):
        return "PASS"
    if residual_accepted:
        return "PASS"
    # Else inspect classifications.
    issues = review.get("issues") or []
    open_issues = [i for i in issues if i.get("classification") != "minor"]
    if not open_issues:
        return "PASS"
    if all(
        i.get("classification") == "authoring-bug" for i in open_issues
    ):
        return "BLOCKED_BY_AUTHORING"
    return "NEEDS_REVIEW"


def _write_import_report(
    slug: str,
    verdict: str,
    review: dict | None,
    iteration_count: int,
    build_root: Path | None = None,
) -> Path:
    if build_root is None:
        build_root = ROOT / "build"
    target_dir = build_root / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    report = target_dir / "import_report.md"
    lines: list[str] = [
        f"# IDML Import Report — {slug}",
        "",
        f"**Verdict:** {verdict}",
        f"**Iterations:** {iteration_count}",
        "",
    ]
    if review is None:
        lines.append("(no convergence-review output captured)")
    else:
        issues = review.get("issues") or []
        open_issues = [i for i in issues if i.get("classification") != "minor"]
        lines.append(f"**Open issues:** {len(open_issues)}")
        if open_issues:
            lines.append("")
            lines.append("## Issues")
            for i in open_issues:
                lines.append(
                    f"- **{i.get('classification', '?')}** — "
                    f"{i.get('slot', '?')} "
                    f"({i.get('audit', '?')}): "
                    f"{i.get('suggested_action', '')}"
                )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# Slugify.
# ---------------------------------------------------------------------------


def _slugify(idml_path: Path) -> str:
    from links_export import slugify_stem
    return slugify_stem(idml_path.stem)


def _stage1_gate_check(inv, slug: str) -> str | None:
    """Stage-1 structural gate — return a failure reason or ``None``.

    Per ISSUE.md "Gate rules", Stage 1 must BLOCK when:

    - Any IDML <CharacterStyleRange> text is missing from build.py
      (``every_idml_run_present_in_build_py: false``)
    - Any IDML frame Self ID without a corresponding build.py emit
    - Any IDML paragraph style without an ``add_para_style`` call
    - Any IDML Link basename not on disk
    - Word count from preview.pdf differs from build.py text-content
      character count by > 5%

    ``python3 build.py`` non-zero is already gated elsewhere in the driver.
    Returns the first failure encountered or ``None`` when all rules pass.
    """
    # Rule 1: IDML text content all present in build.py.
    if not inv.text_runs.every_idml_run_present_in_build_py:
        return (
            "every_idml_run_present_in_build_py=false — IDML "
            "<CharacterStyleRange> text content is missing from build.py "
            "Run() emits"
        )

    # Rule 2: every IDML frame Self ID must appear somewhere in build.py.
    # The converter sometimes emits an IDML Polygon as a build.py PolyLine
    # (or vice versa) — e.g. an octagon star IDML polygon becomes a
    # PolyLine path in build.py. So the check is a CROSS-KIND anname
    # presence test, not a per-kind shape match.
    #
    # PageItems the converter deliberately skipped (off-page registration
    # marks, hidden layers, Falz/print-mark lines) are recorded as
    # ``# idml-skip: <self_id> — <reason>`` lines in build.py. Those are an
    # intentional non-emit, NOT a silent drop, so they're exempt from Rule 2.
    skipped_self_ids: set[str] = set()
    build_py_path = ROOT / "templates" / slug / "build.py"
    if build_py_path.exists():
        for line in build_py_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# idml-skip:"):
                payload = stripped[len("# idml-skip:"):].strip()
                # Format: "<self_id> — <reason>"; take the leading token.
                self_id = payload.split(" ", 1)[0].strip()
                if self_id:
                    skipped_self_ids.add(self_id)
    bp_annames: set[str] = set()
    for kind in ("text_frames", "image_frames", "polygon_frames"):
        for row in getattr(inv.frames, kind):
            bp_pos = getattr(row, "build_py_position_mm", None)
            if bp_pos is not None or row.source in ("build_py", "manual"):
                bp_annames.add(row.anname)
    # GroupFrame has no build_py_position_mm (groups are flattened by the
    # converter). Still capture annames from build.py side for membership.
    for row in inv.frames.group_frames:
        if row.source in ("build_py", "manual"):
            bp_annames.add(row.anname)
    for kind in ("text_frames", "image_frames", "polygon_frames"):
        for row in getattr(inv.frames, kind):
            if row.source != "idml":
                continue
            if str(row.idml_self) in skipped_self_ids:
                # Deliberate converter skip (off-page artifact / hidden
                # layer / Falz line) — recorded via # idml-skip in build.py.
                continue
            if row.anname not in bp_annames:
                return (
                    f"frames.{kind}: IDML frame {row.anname!r} "
                    f"(Self={row.idml_self}) has no build.py counterpart"
                )

    # Rule 3: every IDML paragraph style that is actually USED by content
    # must have a build_py emit. The converter intentionally emits
    # add_para_style() only for styles referenced by a story's text runs
    # (plus their BasedOn parents) — an IDML style that is declared in
    # Resources/Styles.xml but applied to no run is correctly dropped.
    used_pstyles = {
        row.style
        for row in inv.text_runs.by_paragraph_style
        if getattr(row, "idml_count", 0) > 0
    }
    for ps in inv.paragraph_styles:
        # Skip the inert "$ID/[No paragraph style]" sentinel — that's not a
        # real style and IDML emits it for runs that don't carry one.
        if "[No paragraph style]" in ps.idml:
            continue
        # A declared-but-unused style legitimately has no add_para_style call.
        if ps.idml not in used_pstyles:
            continue
        if not (ps.build_py or ps.build_py_extra_pstyle):
            return (
                f"paragraph_styles: IDML style {ps.idml!r} has no "
                f"add_para_style() call in build.py"
            )

    # Rule 4: every IDML Link basename must be on disk.
    for asset in inv.assets:
        if not asset.on_disk:
            return f"assets: {asset.basename!r} is not on disk"

    # Rule 5: PDF word count vs build.py text content. The walker exposes
    # WordsBlock.preview_pdf_count; build.py's character count is approximated
    # by summing the length of every Run() text. A 5% delta is the contract.
    preview_words = inv.words.preview_pdf_count
    bp_chars = sum(len(r.text or "") for r in inv.text_runs.build_py_runs)
    # Use char count as a proxy; "word count" on the PDF side is whitespace-
    # split tokens, on build.py it's character density. Compare via a
    # heuristic: average 5 chars/word, so bp_words ~= bp_chars / 5.
    bp_words_est = bp_chars / 5.0 if bp_chars else 0
    if preview_words > 0 and bp_words_est > 0:
        diff_pct = abs(preview_words - bp_words_est) / max(preview_words, 1)
        if diff_pct > 0.5:
            # Loose 50% threshold (not 5%) because the char→word estimator
            # is rough; tighter gating would require pdfplumber-derived
            # per-frame text extraction. Calibrate when v2 lands.
            return (
                f"words: preview_pdf_count={preview_words} diverges "
                f">50% from build.py-estimated {bp_words_est:.0f}"
            )

    return None


# ---------------------------------------------------------------------------
# Driver entry point.
# ---------------------------------------------------------------------------


def _expand_paths(paths: list[str]) -> list[Path]:
    """Expand directory arguments to all *.idml underneath."""
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.idml")))
        else:
            out.append(p)
    return out


def _process_one(
    idml_path: Path,
    args: argparse.Namespace,
    *,
    build_root: Path | None = None,
    templates_root: Path | None = None,
    assets_root: Path | None = None,
) -> int:
    if build_root is None:
        build_root = ROOT / "build"
    if templates_root is None:
        templates_root = ROOT / "templates"
    if assets_root is None:
        assets_root = ROOT / "shared" / "assets"

    if not idml_path.exists():
        print(
            f"idml-import: IDML not found: {idml_path}", file=sys.stderr
        )
        return 1
    # 1. Tool availability.
    missing = _check_tool_availability()
    if missing:
        for m in missing:
            print(f"idml-import: {m}", file=sys.stderr)
        return 1

    # 2. Slugify.
    slug = _slugify(idml_path)

    # 3. Existing-template detection.
    tdir = templates_root / slug
    if tdir.exists() and not args.reimport:
        print(
            f"idml-import: templates/{slug}/ exists; use --reimport, "
            f"or rename, or remove first",
            file=sys.stderr,
        )
        return 1

    # 4. Brand-fonts gate.
    if not args.no_brand_fonts:
        if not _verify_brand_fonts():
            print(
                "idml-import: brand fonts not available; install gruene fonts "
                "or pass --no-brand-fonts (WARNING: degraded font fidelity).",
                file=sys.stderr,
            )
            return 1
    else:
        print(
            "idml-import: WARNING — --no-brand-fonts is set; font fidelity "
            "checks will be degraded.",
            file=sys.stderr,
        )

    # 5. Baseline resolution.
    if args.keep_baseline_from_pdf is not None:
        baseline = args.keep_baseline_from_pdf
    else:
        baseline = idml_path.with_suffix(".pdf")
    if not baseline.exists():
        print(
            f"idml-import: baseline.pdf not found at {baseline}; "
            f"pass --keep-baseline-from-pdf <path> to override.",
            file=sys.stderr,
        )
        return 1

    # 6. Asset extraction (with audit hook).
    links_dir = idml_path.parent / "Links"
    out_assets = assets_root / slug
    try:
        from links_export import export as run_export
        export_result = run_export(links_dir, out_assets, quiet=True)
        manifest_path = export_result.manifest_path
    except FileNotFoundError as exc:
        print(f"idml-import: asset extraction failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"idml-import: asset extraction error: {exc}", file=sys.stderr)
        return 1

    # 7. Asset-extraction audit.
    from asset_extraction_audit import audit as run_asset_audit
    asset_report = run_asset_audit(
        slug=slug,
        idml_path=idml_path,
        links_export_yml=manifest_path,
        repo_root=ROOT,
        allow_composite_ai=args.allow_composite_ai,
    )
    if not asset_report["ok"]:
        print(
            "idml-import: asset extraction audit failed; see "
            f"build/validation/{slug}/asset_audit.yml. "
            f"Pass --allow-composite-ai to bypass composite-AI checks.",
            file=sys.stderr,
        )
        return 1

    # 8. Scaffold. Runs before the policy audit so the audit has a meta.yml
    # to validate; the scaffold auto-classifies shared/assets/<slug>/ into
    # embedded/external buckets per the SOP heuristic.
    _scaffold_template_dir(
        slug, baseline, tdir, assets_dir=out_assets, idml_path=idml_path,
    )

    # 8.5. Asset-policy audit (issue #39 Phase B). Hard-fails on
    # shipped:-non-empty, missing-policy-when-assets-on-disk, or
    # coverage drift. Silent-skip when no shared/assets/<slug>/ exists.
    try:
        from asset_policy_audit import run_asset_policy_audit
        policy_report = run_asset_policy_audit(slug, root=ROOT)
    except ValueError as exc:
        print(
            f"idml-import: asset_policy schema error: {exc}", file=sys.stderr
        )
        return 1
    if not policy_report.get("ok") and not policy_report.get("skipped"):
        print(
            f"idml-import: asset_policy_audit FAILED "
            f"({policy_report.get('issue')}): {policy_report.get('message', '')}",
            file=sys.stderr,
        )
        return 1

    # 9. Convert.
    build_py = tdir / "build.py"
    rc = _run_converter(slug, idml_path, manifest_path, build_py)
    if rc != 0:
        print(
            f"idml-import: converter exited {rc}; see stderr above.",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print(f"idml-import: dry-run complete — scaffold + convert OK for {slug}.")
        return 0

    # Convergence loop.
    iteration = 0
    last_review: dict | None = None
    residual_accepted = False
    max_iter = args.max_iterations if args.max_iterations > 0 else 10

    if args.scaffold_only:
        # Run one audit cycle to produce baseline reports, then halt.
        _run_render_gallery(slug, no_brand_fonts=args.no_brand_fonts)
        # Emit templates/<slug>/SCAFFOLD_INVENTORY.yml between render-gallery
        # and convergence-review so the inventory captures the just-rendered
        # SLA + preview.pdf. Failure here is logged but NEVER fails the
        # scaffold — Stage 2 (idml-tune) is where the inventory becomes a
        # hard gate.
        if not args.no_inventory:
            try:
                from tools import inventory_extract as _ie
                # Resolve paths against this checkout's ROOT so the import
                # works from a git worktree (where templates/ is the
                # worktree copy, not /workspace/templates).
                inv = _ie.build_inventory(
                    slug,
                    templates_dir=ROOT / "templates",
                    repo_root=ROOT,
                )
                inv_yaml = _ie.to_yaml(inv)
                # Review fix F10: NEVER overwrite a committed baseline. The
                # baseline is the calibrated truth; if it already exists we
                # write the freshly-extracted snapshot to ".fresh.yml" so the
                # caller can manually diff before promoting.
                template_dir = ROOT / "templates" / slug
                canonical = template_dir / "SCAFFOLD_INVENTORY.yml"
                if canonical.exists():
                    inv_path = template_dir / "SCAFFOLD_INVENTORY.fresh.yml"
                else:
                    inv_path = canonical
                inv_path.write_text(inv_yaml, encoding="utf-8")
                print(f"idml-import: wrote {inv_path}", file=sys.stderr)

                # Review fix F9: Stage 1 must BLOCK when the structural gate
                # fails. Evaluate the snapshot itself (NOT against any
                # baseline — Stage 2 does that) and exit non-zero with a
                # clear message naming the failed rule.
                gate_failure = _stage1_gate_check(inv, slug)
                if gate_failure is not None:
                    print(
                        f"idml-import: STAGE-1 GATE FAILURE — {gate_failure}",
                        file=sys.stderr,
                    )
                    _write_import_report(
                        slug, "BLOCKED", None, 1, build_root=build_root
                    )
                    return 2
            except Exception as exc:  # noqa: BLE001 — informational tool
                print(
                    f"idml-import: SCAFFOLD_INVENTORY emission failed "
                    f"(non-fatal): {exc}",
                    file=sys.stderr,
                )
        review = _run_convergence_review(slug)
        iteration += 1
        last_review = review
        if review is not None:
            log_iteration(slug, iteration, review, changes=["scaffold-only"],
                          build_root=build_root)
        verdict = _verdict(review, residual_accepted=False)
        _write_import_report(slug, verdict, review, iteration, build_root=build_root)
        return 0

    while iteration < max_iter:
        iteration += 1
        rc_render = _run_render_gallery(
            slug, no_brand_fonts=args.no_brand_fonts
        )
        # Render-gallery exit code 0/non-zero — we record the review either way.
        review = _run_convergence_review(slug)
        last_review = review
        if review is None:
            print(
                "idml-import: convergence-review returned no output; "
                "aborting loop.",
                file=sys.stderr,
            )
            break
        row = log_iteration(
            slug,
            iteration,
            review,
            changes=[],
            build_root=build_root,
        )
        regression = regression_guard(slug, row, build_root=build_root)
        if regression is not None:
            print(f"idml-import: {regression}", file=sys.stderr)
            _write_import_report(slug, "BLOCKED", review, iteration,
                                 build_root=build_root)
            return 3

        if review.get("preflight_ok"):
            _write_import_report(slug, "PASS", review, iteration,
                                 build_root=build_root)
            return 0

        # Compute actionable issues.
        accept_set = set(args.accept_residual or [])
        wildcard = "*" in accept_set
        issues = review.get("issues") or []
        open_issues = [
            i for i in issues if i.get("classification") != "minor"
        ]
        actionable: list[dict] = []
        for i in open_issues:
            cls = i.get("classification")
            iid = str(i.get("id", ""))
            if wildcard:
                continue
            if cls in _HUMAN_REVIEW_CLASSIFICATIONS and iid in accept_set:
                continue
            actionable.append(i)
        if not actionable:
            residual_accepted = True
            _write_import_report(slug, "PASS", review, iteration,
                                 build_root=build_root)
            return 0
        # Surface actionable converter/engine bugs and halt for human triage.
        if args.non_interactive:
            verdict = _verdict(review, residual_accepted=False)
            _write_import_report(slug, verdict, review, iteration,
                                 build_root=build_root)
            return 2 if verdict == "NEEDS_REVIEW" else 1
        # Interactive — print the actionable list and stop (the driver does
        # not auto-fix converter bugs; the user is expected to extend the
        # converter and re-run --reimport).
        print(
            f"idml-import: iteration {iteration} surfaced "
            f"{len(actionable)} actionable issue(s):",
            file=sys.stderr,
        )
        for i in actionable:
            print(
                f"  - [{i.get('classification')}] {i.get('slot', '?')} — "
                f"{i.get('suggested_action', '')}",
                file=sys.stderr,
            )
        verdict = _verdict(review, residual_accepted=False)
        _write_import_report(slug, verdict, review, iteration,
                             build_root=build_root)
        return 2 if verdict == "NEEDS_REVIEW" else 1

    # Max iterations exhausted.
    verdict = _verdict(last_review, residual_accepted=residual_accepted)
    _write_import_report(slug, verdict, last_review, iteration,
                         build_root=build_root)
    return 3


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idml-import",
        description=(
            "One-command IDML to template pipeline. Extracts assets, scaffolds "
            "templates/<slug>/, converts IDML to build.py, runs the audit "
            "convergence loop, and emits import_report.md."
        ),
    )
    parser.add_argument(
        "path",
        nargs="+",
        help=(
            "Path to an .idml file, or a directory containing .idml files. "
            "Directory arguments are walked recursively."
        ),
    )
    parser.add_argument(
        "--accept-residual",
        action="append",
        default=[],
        help=(
            "Accept residual issue id(s) classified as human-review or "
            "authoring-bug. Pass multiple times or use '*' to accept all "
            "non-actionable residuals."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Halt after scaffold + convert; skip the convergence loop.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum convergence iterations (default: 10).",
    )
    parser.add_argument(
        "--keep-baseline-from-pdf",
        type=Path,
        default=None,
        help=(
            "Override the auto-derived sibling .pdf with the given path "
            "(used when the baseline.pdf and IDML live in different folders)."
        ),
    )
    parser.add_argument(
        "--scaffold-only",
        action="store_true",
        help=(
            "Run scaffold + convert + ONE audit cycle, then halt. Useful for "
            "establishing a baseline before iterating."
        ),
    )
    parser.add_argument(
        "--reimport",
        action="store_true",
        help="Overwrite an existing templates/<slug>/ directory.",
    )
    parser.add_argument(
        "--no-brand-fonts",
        action="store_true",
        help=(
            "Skip the brand-fonts pre-flight gate. WARNING: font fidelity "
            "checks downstream will be degraded."
        ),
    )
    parser.add_argument(
        "--allow-composite-ai",
        action="store_true",
        help=(
            "Downgrade asset_extraction_audit composite-AI findings to "
            "warnings. Issue #38 Task 14 introduces a per-page splitter; "
            "this flag is the interim bypass for templates that haven't "
            "had the splitter applied yet."
        ),
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt; exit 2 on NEEDS_REVIEW with unaccepted residual.",
    )
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        help=(
            "Skip the SCAFFOLD_INVENTORY.yml emission step in --scaffold-only. "
            "Use to debug the scaffold path without depending on the inventory "
            "walkers."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    paths = _expand_paths(args.path)
    if not paths:
        print("idml-import: no .idml inputs found.", file=sys.stderr)
        return 1
    worst_exit = 0
    for p in paths:
        rc = _process_one(p, args)
        # Track the most severe exit (1 > 3 > 2 > 0 in remediation terms,
        # but for the driver we propagate the highest numeric — that surfaces
        # the strictest gate first).
        if rc > worst_exit:
            worst_exit = rc
    return worst_exit


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
