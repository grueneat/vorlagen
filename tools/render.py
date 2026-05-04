#!/usr/bin/env python3
"""Headless SLA → PDF render via Scribus 1.6 + Xvfb.

Usage:
    tools/render.py templates/postkarte-a6-kampagne
    tools/render.py templates/postkarte-a6-kampagne --sample klimaschutz
    tools/render.py path/to/template.sla --out build/foo.pdf

If a template directory is given, looks for template.sla and meta.yml; for a
named --sample, applies samples/<name>.json via sla_lib before rendering.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.editor import SLAEditor  # noqa: E402

SCRIBUS_PY = r"""
import scribus, sys, os
infile = sys.argv[1]
outfile = sys.argv[2]
profile = sys.argv[3] if len(sys.argv) > 3 else "screen"
scribus.openDoc(infile)
pdf = scribus.PDFfile()
pdf.file = outfile
# Defaults are RGB / screen; for press the renderer image must hold ICC profiles
# and the Scripter snippet should set pdf.Version, pdf.UseProfiles*, pdf.Intent etc.
# Stub for now — full PDF/X-4 wiring is renderer Phase A.6.
if profile == "pdfx4":
    pdf.Version = 14   # PDF/X-4 (constant in Scribus Scripter)
    pdf.Compress = 1
    pdf.UseProfiles = 1
    pdf.UseProfiles2 = 1
pdf.save()
print("RENDER_OK", outfile)
"""


def render_sla(sla_path: Path, pdf_path: Path, profile: str = "screen") -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as t:
        t.write(SCRIBUS_PY)
        script = t.name
    try:
        cmd = [
            "xvfb-run", "-a", "--server-args=-screen 0 1024x768x24",
            "scribus", "-g", "-ns",
            "-py", script,
            str(sla_path), str(pdf_path), profile,
        ]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8",
               "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not pdf_path.exists():
            sys.stderr.write(r.stdout + "\n" + r.stderr + "\n")
            raise RuntimeError(f"Scribus render failed for {sla_path}")
    finally:
        os.unlink(script)


def resolve_inputs(target: Path, sample: str | None) -> tuple[Path, Path, dict | None]:
    if target.is_file() and target.suffix == ".sla":
        return target, target, None
    if not target.is_dir():
        raise SystemExit(f"Not a template dir or .sla file: {target}")
    sla = target / "template.sla"
    if not sla.exists():
        raise SystemExit(f"Missing {sla}")
    if sample is None:
        return sla, target, None
    sample_file = target / "samples" / f"{sample}.json"
    if not sample_file.exists():
        raise SystemExit(f"Missing sample {sample_file}")
    return sla, target, json.loads(sample_file.read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description="Render SLA → PDF headless.")
    ap.add_argument("target", type=Path, help="template dir or .sla file")
    ap.add_argument("--sample", help="sample name in samples/<name>.json")
    ap.add_argument("--out", type=Path, help="output PDF path")
    ap.add_argument("--profile", default="screen", choices=["screen", "pdfx4"])
    args = ap.parse_args()

    sla, tdir, data = resolve_inputs(args.target, args.sample)

    work_sla = sla
    if data is not None:
        # Build dir under build/<template-id>__<sample>/
        slug = f"{tdir.name}__{args.sample}"
        out_dir = ROOT / "build" / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        work_sla = out_dir / "template.sla"
        doc = SLADocument(sla)
        ed = SLAEditor(doc)
        status = ed.fill(data)
        ed.write(work_sla)
        print(f"[fill] {slug}: {status}")
        out_pdf = args.out or (out_dir / f"{slug}.pdf")
    else:
        out_pdf = args.out or (ROOT / "build" / f"{tdir.name}.pdf")

    render_sla(work_sla, out_pdf, profile=args.profile)
    print(f"[render] {out_pdf} ({out_pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
