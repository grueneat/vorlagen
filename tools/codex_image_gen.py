#!/usr/bin/env python3
"""Per-template demo-image generator (D11, one-shot).

Reads a template's ``samples/manifest.yml`` and uses the ``codex`` CLI's
DALL·E image-generation capability (per openai/codex#8758) to produce
realistic preview images for templates that have optional image slots.

Authoring-only: this tool runs **once** per template during the issue's
execute phase. The generated JPGs are committed under
``templates/<slug>/samples/`` so the build pipeline never invokes ``codex``.

Manifest format::

    # templates/<slug>/samples/manifest.yml
    images:
      - id: kandidat-portrait
        prompt: |
          Documentary-style portrait photo of a 40s Austrian woman with short
          brown hair and a green blazer, friendly direct gaze, neutral
          light-grey studio backdrop, soft front light. Vertical headshot.
          Natural skin tones. No text overlays. No watermarks.
        output: kandidat-portrait.jpg
        size: 768x1024     # optional, codex-default if omitted

Brand-quality prompt guidance (see also docs/guides):
- Use "documentary" or "photorealistic" framing — not generic "image of …".
- Soft natural light or neutral studio light, never harsh shadows.
- Greens-friendly subjects: candidates (40s+ Austrians, professional but
  approachable), community gatherings, urban gardens, public transport,
  renewable infrastructure.
- Always end with: "No text overlays. No watermarks." (avoids hallucinated
  logos / fake captions baked into the pixels).

Usage::

    tools/codex_image_gen.py templates/<slug>/samples/manifest.yml
    tools/codex_image_gen.py --dry-run <manifest.yml>
    tools/codex_image_gen.py --help

Idempotency: skips an output if it already exists AND its mtime is newer
than the manifest. Pass ``--force`` to overwrite.
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import yaml


def parse_manifest(path: Path) -> dict:
    """Parse a samples/manifest.yml file. Returns the dict."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "images" not in data or not isinstance(data["images"], list):
        raise ValueError(
            f"{path}: missing or invalid `images:` list. "
            f"Expected: images: [{{id, prompt, output, ...}}]"
        )
    return data


def image_needs_regen(manifest_path: Path, output_path: Path) -> bool:
    """Return True if the output is missing OR older than the manifest."""
    if not output_path.exists():
        return True
    return output_path.stat().st_mtime < manifest_path.stat().st_mtime


def codex_login_status() -> str:
    """Return 'ok' or a human-readable error string."""
    if shutil.which("codex") is None:
        return "codex CLI not found on PATH"
    try:
        r = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return "codex login status timed out"
    if r.returncode != 0:
        return f"codex login status failed: {r.stderr.strip() or r.stdout.strip()}"
    out = (r.stdout or "").lower()
    if "logged in" in out or "authenticated" in out:
        return "ok"
    # Not all codex versions print "logged in". Treat any 0-exit as ok.
    return "ok"


def build_codex_prompt(prompt: str, output_abspath: Path, size: str | None) -> str:
    """Construct the prompt string for codex exec.

    The codex CLI's image-generation flow is invoked through a natural-language
    prompt that asks codex to generate an image and write it to a path.
    """
    sz_clause = f" The image size should be {size}." if size else ""
    return (
        f"Please generate a photorealistic image and save it to {shlex.quote(str(output_abspath))}.\n\n"
        f"Image description:\n{prompt.strip()}\n"
        f"{sz_clause}\n"
        f"Use the image generation tool with format=jpg. Save the resulting bytes to the "
        f"path above. Do not write any other files."
    )


def generate_image(prompt: str, output_path: Path, size: str | None) -> int:
    """Invoke codex exec with image-generation prompt. Returns exit code."""
    full_prompt = build_codex_prompt(prompt, output_path.resolve(), size)
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--dangerously-bypass-approvals-and-sandbox",
        full_prompt,
    ]
    print(f"  -> codex exec ... (output={output_path})")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        sys.stderr.write(f"  codex stderr:\n{r.stderr}\n")
        sys.stderr.write(f"  codex stdout:\n{r.stdout}\n")
    return r.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        help="Path to samples/manifest.yml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated; do not invoke codex.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-generate even if the output already exists and is newer than the manifest.",
    )
    args = parser.parse_args(argv)

    if args.manifest is None:
        parser.print_help()
        return 0

    manifest_path = args.manifest
    if not manifest_path.exists():
        sys.stderr.write(f"manifest not found: {manifest_path}\n")
        return 1

    samples_dir = manifest_path.parent
    try:
        manifest = parse_manifest(manifest_path)
    except (ValueError, yaml.YAMLError) as e:
        sys.stderr.write(f"manifest parse error: {e}\n")
        return 1

    images = manifest.get("images", [])
    if not images:
        print("manifest has no images; nothing to do.")
        return 0

    if not args.dry_run:
        status = codex_login_status()
        if status != "ok":
            sys.stderr.write(
                f"codex auth precheck failed: {status}\n"
                f"Run `codex login` first; OAuth credentials live at /root/.codex/auth.json.\n"
            )
            return 1

    fail_count = 0
    skip_count = 0
    write_count = 0

    for entry in images:
        if not isinstance(entry, dict):
            sys.stderr.write(f"manifest entry not a dict: {entry!r}\n")
            fail_count += 1
            continue
        eid = entry.get("id", "<no-id>")
        prompt = entry.get("prompt")
        out_name = entry.get("output")
        size = entry.get("size")
        if not prompt or not out_name:
            sys.stderr.write(f"manifest[{eid}]: missing prompt or output\n")
            fail_count += 1
            continue

        out_path = samples_dir / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not args.force and not image_needs_regen(manifest_path, out_path):
            print(f"[skip] {eid} -> {out_name} (exists, newer than manifest)")
            skip_count += 1
            continue

        print(f"[gen ] {eid} -> {out_name}")
        if args.dry_run:
            print(f"  prompt: {prompt[:80]}...")
            continue

        rc = generate_image(prompt, out_path, size)
        if rc != 0 or not out_path.exists():
            sys.stderr.write(f"  FAIL: codex returned {rc} / output missing\n")
            fail_count += 1
            continue
        sz_kb = out_path.stat().st_size // 1024
        print(f"  wrote {out_name} ({sz_kb} KB)")
        write_count += 1

    print(
        f"\nSummary: {write_count} written, {skip_count} skipped, "
        f"{fail_count} failed (of {len(images)} total)."
    )
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
