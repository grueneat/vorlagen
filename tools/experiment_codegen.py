"""tools/experiment_codegen.py — multi-LLM variant builder generator (issue #30 T16a).

Closes the gap surfaced in #29 + the T16 architectural finding:
`bin/experiment-generate` produces hypothesis manifest entries with a
``builder: variants/<slug>.py`` field but does NOT create the .py files.
This module reads the manifest, iterates hypotheses, and for each
hypothesis WITHOUT an existing builder asks an LLM (claude + codex;
gemini optional) to author a complete ``render_p2(doc, page) -> None``
module that fits inside the experiment's constraint envelope.

Mirrors ``tools/experiment_hypothesis_gen.py``:

  - ``shutil.which`` guards on the LLM binaries
  - 600s timeout, ``stdin=subprocess.DEVNULL``
  - Raw outputs preserved under ``_llm-raw/codegen/<slug>-<llm>.py``
    BEFORE validation so even rejected modules are auditable
  - Per-LLM error tolerance — if one LLM's output fails envelope
    validation, try the other LLM. Skip the slug if both fail.

Run as:

    bin/experiment-codegen <exp-id> [--only <slug>] [--force]
                                    [--llms claude,codex]

Outputs:

    experiments/<exp-id>/variants/<slug>.py                  (written + validated)
    experiments/<exp-id>/_llm-raw/codegen/<slug>-<llm>.py    (raw audit copies)

Validation per slug:

  1. Module imports cleanly.
  2. Exposes ``render_p2(doc, page) -> None``.
  3. Renders within the variant_scaffold (so it actually runs).
  4. Resulting Document passes ``run_envelope(doc, envelope)`` — the
     same gate ``bin/experiment-render`` enforces. We pre-flight the
     gate so the render stage isn't the first place violations surface.

Default skips slugs that already have a ``.py`` file. ``--force`` regenerates.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from experiment_envelope import (  # noqa: E402
    Envelope,
    format_envelope_markdown,
    load_envelope,
    run_envelope,
)
from sla_lib.builder.constraints import Violation  # noqa: E402

LLM_TIMEOUT_S = 600
DEFAULT_LLMS = ("claude", "codex")

# Slugs preserved verbatim from v1 — they were hand-authored in T11–T13
# of #30 and already pass the envelope. We never overwrite these unless
# --force is set AND they appear in --only.
RETAINED_FROM_V1_SLUGS = frozenset({
    "numbered-priority-list-v2",
    "manifesto-single-statement-v2",
    "dunkelgrun-rules-between-items-v2",
})

# The 3 retained-from-v1 builders live next to the manifest and double
# as reference implementations: the LLM sees them as in-context examples
# of "what a passing variant looks like".
REFERENCE_SLUGS_DEFAULT: tuple[str, ...] = (
    "numbered-priority-list-v2",
    "manifesto-single-statement-v2",
    "dunkelgrun-rules-between-items-v2",
)

# DSL signature summary embedded in the prompt — the LLM doesn't need the
# whole sla_lib; it needs to know the public-surface symbols and the
# scaffold contract. Kept compact so it travels well in LLM context.
DSL_SIGNATURE_SUMMARY = """\
Available DSL symbols (all importable from `sla_lib.builder`):

  - `Document` / `Page` — already constructed by the scaffold; you receive
    `doc` and `page` (page 0 of the falzflyer 2-page document).
  - `TextFrame(x_mm, y_mm, w_mm, h_mm, layer, style, runs, anname)` —
    page.add(TextFrame(...)) to add a text frame. `anname` MUST start
    with the string `"P2 "` (P2 panel under test); the scaffold strips
    pre-existing P2 items before calling render_p2.
  - `Run(text, paragraph_style, separator=None)` — used inside
    `TextFrame(runs=[...])`. `separator="para"` ends a paragraph.
  - `Polygon(x_mm, y_mm, w_mm, h_mm, fill, layer, anname)` — color block.
    Use brand colours: `"Hellgrün"`, `"Dunkelgrün"`, `"Gelb"`, `"Weiß"`.
  - `ParaStyle(name, font, fontsize, linesp, align, fcolor, language)` —
    register custom paragraph styles via `doc.add_para_style(ParaStyle(...))`
    BEFORE adding TextFrames that reference them. Pre-existing production
    styles available without re-registration: `"falzflyer/top-title"`,
    `"falzflyer/teaser-headline"`, `"falzflyer/schlagwort"`.

Layer values: `0` = background polygons, `2` = text. (LAYER_HINTERGRUND=0,
LAYER_TEXT=2 in production.)

Brand fonts that are REGISTERED and SAFE to use (others render fallback):
  `Gotham Narrow Bold`, `Gotham Narrow Book`, `Gotham Narrow Light`,
  `Vollkorn Black Italic` (NOT plain `Vollkorn Black`).

Panel coordinates (P2 area on page 0):

  - The panel occupies x_mm=99..198, y_mm=0..213 on the front page.
  - Recommended layout zones:
      * Top band (Dunkelgrün): x=99, y=-3, w=99, h=31  (production geometry)
      * Top-Title TextFrame "Mein Plan": x=105, y=8, w=87, h=14 in `"falzflyer/top-title"`
      * Teaser-Headline: x=105, y=38, w=87, h=22 in `"falzflyer/teaser-headline"`
      * Body backing (Hellgrün): x=99, y=28, w=99, h=185
      * Body content area: x=105..192 (87mm wide), y=70..200 (~130mm tall)
"""

SCAFFOLD_CONTRACT = """\
Scaffold contract (`templates/kandidat-falzflyer-din-lang/variant_scaffold.py`):

  - The orchestrator calls `build_variant_front(your_render_p2_fn) -> Document`.
  - Production P1 (Cover), P3 (Wahltag) and back-page panels are
    preserved verbatim — DO NOT add items outside the P2 panel.
  - Your `render_p2(doc, page)` function is invoked AFTER the scaffold
    strips items whose `anname` begins with `"P2 "`. Every PAGEOBJECT
    you emit MUST carry an `anname` starting with `"P2 "` — that's how
    the envelope's Layer-1 predicates scope to your panel.
  - You re-emit the production top-band, top-title, teaser-headline and
    body-backing (see reference implementations) — there is no automatic
    inheritance; the strip-and-replace is intentional.
"""

OUTPUT_CONTRACT = """\
Your output MUST be a single complete Python file, beginning with a
module docstring and `from __future__ import annotations`, that:

  1. Imports the DSL symbols it uses from `sla_lib.builder`.
  2. Defines any per-variant `ParaStyle` objects inside `render_p2` via
     `doc.add_para_style(ParaStyle(...))` — DO NOT register globally.
  3. Defines exactly one public function:

         def render_p2(doc, page) -> None:
             ...

     which adds the full P2 panel content (top-band, top-title,
     teaser-headline, body backing, then the hypothesis-specific body).
  4. Uses `anname` strings starting with `"P2 "` for every PAGEOBJECT.
  5. Keeps every frame inside x_mm 99..198, y_mm -3..213.
  6. Respects the constraint envelope above. The render gate will reject
     the variant if it violates any active rule.

Output the Python file and nothing else — no surrounding prose, no
```python fences. If you must add commentary, put it in the module
docstring. The file will be written verbatim to disk and executed.
"""


# ---------------------------------------------------------------------------
# Subprocess fan-out — mirrors experiment_hypothesis_gen.py:135-169
# ---------------------------------------------------------------------------

def _run_claude(prompt: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["claude", "--print", "--output-format", "json", "-p", prompt],
        capture_output=True, text=True, timeout=LLM_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
    )


def _run_codex(prompt: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "codex", "exec",
            "--skip-git-repo-check",
            "--sandbox", "workspace-write",
            "--dangerously-bypass-approvals-and-sandbox",
            prompt,
        ],
        capture_output=True, text=True, timeout=LLM_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
    )


def _run_gemini(prompt: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gemini", "--yolo", "-p", prompt],
        capture_output=True, text=True, timeout=LLM_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
    )


LLM_RUNNERS: dict[str, Callable[[str], subprocess.CompletedProcess]] = {
    "claude": _run_claude,
    "codex": _run_codex,
    "gemini": _run_gemini,
}


# ---------------------------------------------------------------------------
# Output extraction
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.DOTALL)


def extract_python_block(text: str) -> str | None:
    """Return the Python source from an LLM response.

    Strategies (tried in order):
      1. Unwrap `claude --output-format json` envelope by parsing the
         outer JSON and recursing into `result`.
      2. Return the contents of the first ```python (or unlabeled) fence.
      3. Fall back to the raw text if it already looks like Python (has
         a `def render_p2` and an `import` line).
    """
    if not text:
        return None

    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            import json
            outer = json.loads(stripped)
        except (ValueError, Exception):  # noqa: BLE001
            outer = None
        if isinstance(outer, dict) and isinstance(outer.get("result"), str):
            inner = extract_python_block(outer["result"])
            if inner is not None:
                return inner

    fences = _FENCE_RE.findall(text)
    for cand in fences:
        s = cand.strip()
        if "def render_p2" in s:
            return s

    if "def render_p2" in text and ("import" in text or "from " in text):
        # Codex sometimes returns the file inline without a fence.
        return text.strip()

    return None


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def _read_reference_files(
    exp_dir: Path, slugs: tuple[str, ...] = REFERENCE_SLUGS_DEFAULT,
) -> str:
    """Concatenate the reference variant builders into a single Markdown blob.

    Each reference is fenced separately so the LLM sees them as distinct
    examples rather than one monolithic file.
    """
    parts: list[str] = []
    for slug in slugs:
        py = exp_dir / "variants" / f"{slug}.py"
        if not py.exists():
            continue
        parts.append(f"### Reference: `{slug}`\n")
        parts.append("```python")
        parts.append(py.read_text(encoding="utf-8").rstrip())
        parts.append("```")
        parts.append("")
    return "\n".join(parts) if parts else "(no reference files available)"


def render_prompt(
    *,
    hypothesis: dict,
    envelope: Envelope,
    references_blob: str,
    dsl_signature: str = DSL_SIGNATURE_SUMMARY,
    scaffold_contract: str = SCAFFOLD_CONTRACT,
    output_contract: str = OUTPUT_CONTRACT,
) -> str:
    """Assemble the codegen prompt for one hypothesis.

    The prompt is composed (not template-substituted) to keep the
    structure explicit and reduce the brittleness of {token} matching
    on a file that contains Python source.
    """
    envelope_md = format_envelope_markdown(envelope)
    axes = ", ".join(f"`{a}`" for a in hypothesis.get("axis_commitments", []))
    return f"""You are authoring a Python variant builder for a design experiment.

Read the hypothesis, the constraint envelope, the scaffold contract, and
the reference implementations. Then emit a complete Python file that
implements the hypothesis as a `render_p2(doc, page)` function.

## Hypothesis

- **slug:** `{hypothesis['slug']}`
- **name:** {hypothesis.get('name', '')}
- **axis commitments:** {axes}
- **wildcard:** {hypothesis.get('wildcard', False)}

**Rationale**

{hypothesis.get('rationale', '(none provided)')}

**Expected outcome**

{hypothesis.get('expected_outcome', '(none provided)')}

## Constraint envelope (HARD floor — render gate enforces)

{envelope_md}

## DSL signature

{dsl_signature}

## Scaffold contract

{scaffold_contract}

## Reference implementations (3 hand-authored variants that pass the envelope)

{references_blob}

## Output contract

{output_contract}
"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class CodegenValidationError(RuntimeError):
    """Raised when a generated module fails import/render/envelope checks."""


def _ensure_scaffold_loaded():
    """Load the variant_scaffold module exactly once."""
    if "variant_scaffold" in sys.modules:
        return sys.modules["variant_scaffold"]
    scaffold_path = (
        ROOT / "templates" / "kandidat-falzflyer-din-lang" / "variant_scaffold.py"
    )
    spec = importlib.util.spec_from_file_location(
        "variant_scaffold", scaffold_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["variant_scaffold"] = module
    spec.loader.exec_module(module)
    return module


def validate_variant_module(
    *,
    py_path: Path,
    slug: str,
    envelope: Envelope,
) -> list[Violation]:
    """Import the file, render it via the scaffold, run the envelope.

    Returns the violation list. Empty list means PASS; non-empty means
    REJECT this codegen output.

    Raises ``CodegenValidationError`` for hard failures (import error,
    missing render_p2, scaffold crash) — the caller treats these the
    same as envelope violations: try the other LLM.
    """
    if not py_path.exists():
        raise CodegenValidationError(f"py file not written: {py_path}")

    scaffold = _ensure_scaffold_loaded()

    # Fresh module name per attempt so re-validation of the same slug
    # under a different LLM picks up the new source.
    mod_name = f"_codegen_{slug}_{py_path.stat().st_mtime_ns}"
    spec = importlib.util.spec_from_file_location(mod_name, py_path)
    if spec is None or spec.loader is None:
        raise CodegenValidationError(f"could not load spec for {py_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001 — surface every import failure
        raise CodegenValidationError(f"import error: {e!r}") from e

    if not hasattr(module, "render_p2"):
        raise CodegenValidationError(
            f"module does not expose render_p2(doc, page); got: "
            f"{sorted(n for n in dir(module) if not n.startswith('_'))}"
        )

    try:
        doc = scaffold.build_variant_front(module.render_p2)
    except Exception as e:  # noqa: BLE001 — scaffold can fail in many ways
        raise CodegenValidationError(f"scaffold/render crashed: {e!r}") from e

    return run_envelope(doc, envelope)


# ---------------------------------------------------------------------------
# Per-slug orchestration
# ---------------------------------------------------------------------------

def _save_raw(exp_dir: Path, slug: str, llm: str, text: str) -> Path:
    raw_dir = exp_dir / "_llm-raw" / "codegen"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = raw_dir / f"{slug}-{llm}-{ts}.py"
    out.write_text(text, encoding="utf-8")
    return out


def generate_for_slug(
    *,
    exp_dir: Path,
    hypothesis: dict,
    envelope: Envelope,
    references_blob: str,
    llms: list[str],
    runner_overrides: dict[str, Callable] | None = None,
    log: Callable[[str], None] = print,
) -> tuple[Path | None, list[str]]:
    """Try each LLM in order; first one that validates wins.

    Returns ``(written_path_or_None, errors)``. ``errors`` is the list of
    per-LLM rejection reasons (empty if first LLM succeeded). The caller
    treats ``None`` path as "skip this slug, both LLMs failed".
    """
    runners = dict(LLM_RUNNERS)
    if runner_overrides:
        runners.update(runner_overrides)

    slug = hypothesis["slug"]
    target = exp_dir / "variants" / f"{slug}.py"
    target.parent.mkdir(parents=True, exist_ok=True)

    prompt = render_prompt(
        hypothesis=hypothesis,
        envelope=envelope,
        references_blob=references_blob,
    )

    errors: list[str] = []
    for llm in llms:
        if llm not in runners:
            errors.append(f"{llm}: no runner available")
            continue
        try:
            log(f"  [{slug}] {llm}: calling ({len(prompt)} chars prompt)")
            r = runners[llm](prompt)
            stdout = r.stdout or ""
        except subprocess.TimeoutExpired:
            errors.append(f"{llm}: timed out after {LLM_TIMEOUT_S}s")
            continue
        except Exception as e:  # noqa: BLE001 — per-LLM tolerance
            errors.append(f"{llm}: subprocess raised {e!r}")
            continue

        _save_raw(exp_dir, slug, llm, stdout)

        py_src = extract_python_block(stdout)
        if not py_src:
            errors.append(f"{llm}: no Python block found in response")
            continue

        target.write_text(py_src, encoding="utf-8")

        try:
            violations = validate_variant_module(
                py_path=target, slug=slug, envelope=envelope,
            )
        except CodegenValidationError as e:
            errors.append(f"{llm}: {e}")
            target.unlink(missing_ok=True)
            continue

        if violations:
            head = "; ".join(
                f"{v.rule_id}: {v.message}" for v in violations[:3]
            )
            errors.append(f"{llm}: envelope: {head}")
            target.unlink(missing_ok=True)
            continue

        log(f"  [{slug}] {llm}: OK")
        return target, errors

    return None, errors


# ---------------------------------------------------------------------------
# Top-level CLI orchestration
# ---------------------------------------------------------------------------

def _load_manifest(exp_dir: Path) -> dict:
    yml = exp_dir / "manifest.yml"
    if not yml.exists():
        raise FileNotFoundError(f"manifest not found: {yml}")
    return yaml.safe_load(yml.read_text(encoding="utf-8"))


def _resolve_llms(requested: list[str], runner_overrides: dict | None) -> list[str]:
    if runner_overrides:
        return [name for name in requested if name in runner_overrides]
    return [name for name in requested if shutil.which(name)]


def run_codegen(
    *,
    exp_id: str,
    only: str | None = None,
    force: bool = False,
    llms: tuple[str, ...] = DEFAULT_LLMS,
    runner_overrides: dict[str, Callable] | None = None,
    log: Callable[[str], None] = print,
) -> int:
    """Drive codegen for all (or one) hypotheses. Returns exit code.

    Exit codes:
      0  no fatal errors (individual slug failures are non-fatal)
      4  experiment directory or manifest missing
      7  constraints.yml missing or invalid
      8  no LLMs available on PATH
    """
    exp_dir = ROOT / "experiments" / exp_id
    if not exp_dir.exists():
        print(f"FATAL: experiments/{exp_id}/ not found", file=sys.stderr)
        return 4
    try:
        manifest = _load_manifest(exp_dir)
    except FileNotFoundError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 4

    try:
        envelope = load_envelope(exp_dir)
    except FileNotFoundError as e:
        print(f"FATAL envelope: {e}", file=sys.stderr)
        return 7
    except Exception as e:  # noqa: BLE001
        print(f"FATAL envelope: {e}", file=sys.stderr)
        return 7

    active_llms = _resolve_llms(list(llms), runner_overrides)
    if not active_llms:
        print(
            f"FATAL: none of the requested LLMs are available: {list(llms)}",
            file=sys.stderr,
        )
        return 8

    references_blob = _read_reference_files(exp_dir)

    hypotheses: list[dict] = manifest.get("hypotheses", []) or []
    if only:
        hypotheses = [h for h in hypotheses if h["slug"] == only]
        if not hypotheses:
            print(f"FATAL: --only {only!r} not in manifest", file=sys.stderr)
            return 4

    generated: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, list[str]]] = []

    for h in hypotheses:
        slug = h["slug"]
        target = exp_dir / "variants" / f"{slug}.py"
        if target.exists() and not force:
            log(f"  [{slug}] skip (exists; --force to regenerate)")
            skipped.append(slug)
            continue
        if slug in RETAINED_FROM_V1_SLUGS and not force:
            log(f"  [{slug}] skip (retained-from-v1; --force to regenerate)")
            skipped.append(slug)
            continue

        path, errs = generate_for_slug(
            exp_dir=exp_dir,
            hypothesis=h,
            envelope=envelope,
            references_blob=references_blob,
            llms=active_llms,
            runner_overrides=runner_overrides,
            log=log,
        )
        if path is None:
            log(f"FAIL {slug}: all {len(active_llms)} LLM(s) failed")
            for err_msg in errs:
                log(f"  - {err_msg}")
            failed.append((slug, errs))
        else:
            generated.append(slug)

    log(
        f"\ncodegen {exp_id}: {len(generated)} written, "
        f"{len(skipped)} skipped, {len(failed)} failed",
    )
    if failed:
        log("failed slugs (no builder written):")
        for slug, _ in failed:
            log(f"  - {slug}")
    return 0


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="experiment-codegen",
        description=(
            "Multi-LLM variant-builder generator for design experiments. "
            "Reads manifest.yml, emits experiments/<exp>/variants/<slug>.py "
            "for every hypothesis without an existing builder."
        ),
    )
    ap.add_argument("exp_id", nargs="?",
                    help="Experiment id (kebab-case), e.g. falzflyer-p2-mein-plan-v2")
    ap.add_argument("--only", default=None,
                    help="Only generate this slug.")
    ap.add_argument("--force", action="store_true",
                    help="Regenerate even when a .py file already exists.")
    ap.add_argument("--llms", default=",".join(DEFAULT_LLMS),
                    help="Comma-separated LLM names (claude, codex, gemini).")
    args = ap.parse_args(argv)

    if not args.exp_id:
        ap.print_help()
        return 0

    llms = tuple(s.strip() for s in args.llms.split(",") if s.strip())
    return run_codegen(
        exp_id=args.exp_id,
        only=args.only,
        force=args.force,
        llms=llms,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


__all__ = [
    "CodegenValidationError",
    "DEFAULT_LLMS",
    "DSL_SIGNATURE_SUMMARY",
    "OUTPUT_CONTRACT",
    "REFERENCE_SLUGS_DEFAULT",
    "RETAINED_FROM_V1_SLUGS",
    "SCAFFOLD_CONTRACT",
    "extract_python_block",
    "generate_for_slug",
    "main",
    "render_prompt",
    "run_codegen",
    "validate_variant_module",
]


def _read_yaml(path: Path) -> Any:  # pragma: no cover - convenience
    return yaml.safe_load(path.read_text(encoding="utf-8"))
