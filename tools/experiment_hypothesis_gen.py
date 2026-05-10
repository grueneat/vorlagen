"""tools/experiment_hypothesis_gen.py — multi-LLM hypothesis generator (issue #29).

Mirrors the multi-LLM subprocess pattern from tools/visual_review.py:209-258:
``shutil.which`` guards, 600s timeouts, ``stdin=subprocess.DEVNULL``,
per-LLM error tolerance. Raw stdout is preserved to ``_llm-raw/`` for
audit BEFORE parsing so even malformed responses are recoverable.

Run as:

    bin/experiment-generate <exp-id> [--subject <subject>]
                                     [--prompt <path>]
                                     [--n-target 12]
                                     [--llms claude,codex,gemini]
                                     [--no-gemini]

Outputs:

    experiments/<exp-id>/manifest.yml      (validated against schema)
    experiments/<exp-id>/manifest.json     (Vite-importable mirror)
    experiments/<exp-id>/_llm-raw/*.txt    (raw LLM stdouts for audit)

Fails (exit 2) if fewer than 2 LLMs returned parseable hypotheses.
Validates against ``experiments/_schema/manifest.schema.yaml`` before
writing; on schema failure writes ``manifest.draft.yml`` and exits non-zero
with the JSON Pointer.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "experiments" / "_schema" / "manifest.schema.yaml"
DEFAULT_PROMPT_PATH = ROOT / "tools" / "experiment_generate" / "prompt_template.md"

LLM_TIMEOUT_S = 600
DEDUP_NAME_RATIO = 0.75
AXIS_OVERLAP_JACCARD = 0.6

# Per-LLM role priming (per RESEARCH.md "Hypothesis generation prompt").
ROLE_PRIMING = {
    "claude": "Role: typography-first designer.",
    "codex": "Role: hierarchy-first designer.",
    "gemini": "Role: asymmetry-first designer.",
}

# Default subject metadata used when --subject is the canonical falzflyer
# experiment. Other subjects can be supported by extending this dict or
# passing --target-weak-area / --weak-area-quote on the CLI.
SUBJECT_METADATA: dict[str, dict[str, str]] = {
    "falzflyer-p2-mein-plan": {
        "target_weak_area": "gruene-corpus.md §6 — even-spaced peer list (P2 'Mein Plan')",
        "weak_area_quote": (
            "P2 currently presents five short slogans ('Klimaplan jetzt.' / "
            "'Leistbares Wohnen.' / 'Bildung vor Ort.' / 'Lokale Wirtschaft.' / "
            "'Bürgernähe statt Klüngel.') as an even-spaced peer list — five "
            "items that read as roughly equal weight, no hierarchy, no "
            "argument, no entry point. design-guide §6 names this the "
            "'even-spaced peer list' failure mode: the reader's eye gets no "
            "purchase, no item registers, the panel feels like a checklist "
            "rather than a vision. Hypotheses MUST commit to a different "
            "design strategy — not 'tweak the bullet spacing'."
        ),
    },
}


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def render_prompt(template: str, subject: str, weak_area_quote: str) -> str:
    """Substitute {subject} and {weak_area_quote} into the prompt template.

    Other literal braces in the template are preserved by escaping ``{`` /
    ``}`` to ``{{`` / ``}}`` inside non-token regions before ``str.format``.
    """
    # Two-step escape: protect literal braces, restore the named tokens.
    tokens = ("subject", "weak_area_quote")
    safe = template.replace("{", "{{").replace("}", "}}")
    for tok in tokens:
        safe = safe.replace("{{" + tok + "}}", "{" + tok + "}")
    return safe.format(subject=subject, weak_area_quote=weak_area_quote)


# ---------------------------------------------------------------------------
# Multi-LLM subprocess pattern
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


LLM_RUNNERS = {
    "claude": _run_claude,
    "codex": _run_codex,
    "gemini": _run_gemini,
}


# ---------------------------------------------------------------------------
# Tolerant JSON parsing
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json|yaml|yml)?\s*(.*?)```", re.DOTALL)


def extract_json_block(text: str) -> str | None:
    """Return the first JSON object/array substring from text, or None.

    Strategy: prefer fenced code blocks, otherwise scan from the first
    ``{`` or ``[`` to the matching closing ``}`` / ``]`` accounting for
    nesting and string literals. Returns None if no plausible block is
    found.
    """
    if not text:
        return None

    # Claude --output-format json wraps the model's reply in {"result": "...", ...}.
    # If we see that wrapper at the very start, peel it.
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            outer = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            outer = None
        if isinstance(outer, dict) and "result" in outer and isinstance(outer["result"], str):
            inner = extract_json_block(outer["result"])
            if inner is not None:
                return inner

    fences = _FENCE_RE.findall(text)
    candidates = list(fences) + [text]

    for cand in candidates:
        s = cand.strip()
        if not s:
            continue
        for opener, closer in (("[", "]"), ("{", "}")):
            i = s.find(opener)
            if i < 0:
                continue
            depth = 0
            in_str = False
            escape = False
            for j in range(i, len(s)):
                ch = s[j]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == opener:
                        depth += 1
                    elif ch == closer:
                        depth -= 1
                        if depth == 0:
                            return s[i:j + 1]
    return None


def parse_llm_response(text: str) -> list[dict] | None:
    """Best-effort: extract a JSON array of hypothesis objects from text."""
    block = extract_json_block(text)
    if block is None:
        return None
    try:
        data = json.loads(block)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        # The LLM may have wrapped the array in {"hypotheses": [...]}.
        for key in ("hypotheses", "items", "data"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            return None
    if not isinstance(data, list):
        return None
    return [h for h in data if isinstance(h, dict)]


# ---------------------------------------------------------------------------
# Hypothesis normalisation, dedup, distinctness
# ---------------------------------------------------------------------------

ALLOWED_AXES = {
    "density", "hierarchy", "typography", "asymmetry",
    "photographic-vs-typographic", "accent-strategy",
    "whitespace-strategy", "voice-formality", "wildcard",
}


def _slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unnamed"


def _coerce_axes(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [v.strip() for v in re.split(r"[,;]", value) if v.strip()]
    elif isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
    else:
        return []
    out = []
    for raw in items:
        norm = raw.lower().replace(" ", "-").replace("_", "-")
        if norm in ALLOWED_AXES and norm not in out:
            out.append(norm)
    return out


def normalise_hypothesis(raw: dict, source: str) -> dict | None:
    """Coerce one LLM-emitted hypothesis dict into the manifest shape.

    Returns None if the entry is too broken to use (no name AND no slug).
    """
    name = (raw.get("name") or raw.get("title") or "").strip()
    slug = (raw.get("slug") or raw.get("id") or "").strip().lower()
    if not slug and name:
        slug = _slugify(name)
    if not slug:
        return None
    if not name:
        name = slug.replace("-", " ").title()

    rationale = (raw.get("rationale") or raw.get("description") or "").strip()
    expected = (raw.get("expected_outcome") or raw.get("expected") or "").strip()
    axes = _coerce_axes(
        raw.get("axis_commitments")
        or raw.get("axes")
        or raw.get("commitments")
        or []
    )
    wildcard = bool(raw.get("wildcard", False))

    if not axes and wildcard:
        axes = ["wildcard"]
    if not axes:
        return None

    if not rationale:
        rationale = "(no rationale provided by source LLM)"
    if not expected:
        expected = "(no expected outcome provided by source LLM)"

    return {
        "slug": _slugify(slug),
        "name": name,
        "axis_commitments": axes,
        "rationale": rationale,
        "expected_outcome": expected,
        "sources": [source],
        "builder": f"variants/{_slugify(slug)}.py",
        "wildcard": wildcard,
    }


def _name_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def merge_hypotheses(pool: list[dict]) -> list[dict]:
    """Group near-duplicate hypotheses across LLM responses.

    Two hypotheses merge if their slug matches OR their names have a
    SequenceMatcher ratio >= DEDUP_NAME_RATIO. The merged entry keeps
    the longest rationale, unions axis_commitments and sources, and
    flags wildcard if any contributing hypothesis flagged it.
    """
    groups: list[list[dict]] = []
    for h in pool:
        placed = False
        for group in groups:
            head = group[0]
            if head["slug"] == h["slug"] or _name_ratio(head["name"], h["name"]) >= DEDUP_NAME_RATIO:
                group.append(h)
                placed = True
                break
        if not placed:
            groups.append([h])

    merged: list[dict] = []
    for group in groups:
        head = group[0]
        names = {h["name"] for h in group}
        sources: list[str] = []
        axes: list[str] = []
        rationales = []
        expected = []
        wildcard = False
        for h in group:
            for s in h["sources"]:
                if s not in sources:
                    sources.append(s)
            for a in h["axis_commitments"]:
                if a not in axes:
                    axes.append(a)
            rationales.append(h["rationale"])
            expected.append(h["expected_outcome"])
            wildcard = wildcard or h["wildcard"]
        merged.append({
            "slug": head["slug"],
            "name": head["name"] if len(names) == 1 else max(names, key=len),
            "axis_commitments": axes,
            "rationale": max(rationales, key=len),
            "expected_outcome": max(expected, key=len),
            "sources": sources,
            "builder": f"variants/{head['slug']}.py",
            "wildcard": wildcard,
        })
    return merged


def distinctness_warnings(merged: list[dict]) -> list[str]:
    """Pairs whose axis_commitments overlap by Jaccard >= AXIS_OVERLAP_JACCARD."""
    warnings: list[str] = []
    for i, a in enumerate(merged):
        for b in merged[i + 1:]:
            sa = set(a["axis_commitments"])
            sb = set(b["axis_commitments"])
            if not sa or not sb:
                continue
            jaccard = len(sa & sb) / len(sa | sb)
            if jaccard >= AXIS_OVERLAP_JACCARD:
                warnings.append(
                    f"axis-overlap {jaccard:.2f}: {a['slug']!r} <-> {b['slug']!r} "
                    f"({sorted(sa & sb)})"
                )
    return warnings


def ensure_wildcard(merged: list[dict]) -> list[dict]:
    """Append a synthetic wildcard placeholder if none exists."""
    if any(h["wildcard"] for h in merged):
        return merged
    placeholder = {
        "slug": "wildcard-placeholder",
        "name": "PLACEHOLDER — replace before render",
        "axis_commitments": ["wildcard"],
        "rationale": (
            "No LLM produced a wildcard hypothesis. Author one manually "
            "or re-run with a stronger wildcard prompt — the experiment "
            "MUST contain at least one wild-card to surface unexpected "
            "design directions."
        ),
        "expected_outcome": "(replace before rendering)",
        "sources": ["synthetic"],
        "builder": "variants/wildcard-placeholder.py",
        "wildcard": True,
    }
    return merged + [placeholder]


# ---------------------------------------------------------------------------
# Manifest assembly + write
# ---------------------------------------------------------------------------

def build_manifest(
    *,
    exp_id: str,
    subject: str,
    target_weak_area: str,
    contributing_llms: list[str],
    hypotheses: list[dict],
    prompt_version: str,
    notes: str | None = None,
) -> dict:
    manifest: dict[str, Any] = {
        "id": exp_id,
        "subject": subject,
        "target_weak_area": target_weak_area,
        "contributing_llms": contributing_llms,
        "created": datetime.date.today().isoformat(),
        "prompt_version": prompt_version,
    }
    if notes:
        manifest["notes"] = notes
    manifest["hypotheses"] = hypotheses
    return manifest


def validate_manifest(manifest: dict) -> list[jsonschema.ValidationError]:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))


def write_manifest(manifest: dict, exp_dir: Path) -> tuple[Path, Path]:
    exp_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = exp_dir / "manifest.yml"
    json_path = exp_dir / "manifest.json"
    yaml_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return yaml_path, json_path


# ---------------------------------------------------------------------------
# CLI orchestration
# ---------------------------------------------------------------------------

def _save_raw(exp_dir: Path, llm: str, text: str) -> Path:
    raw_dir = exp_dir / "_llm-raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = raw_dir / f"{llm}-{ts}.txt"
    out.write_text(text, encoding="utf-8")
    return out


def _resolve_llms(requested: Iterable[str], no_gemini: bool) -> list[str]:
    out: list[str] = []
    for name in requested:
        if name == "gemini" and no_gemini:
            continue
        if shutil.which(name):
            out.append(name)
    return out


def _prompt_version(prompt_text: str) -> str:
    return "sha256:" + hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:12]


def run_generation(
    *,
    exp_id: str,
    subject: str,
    prompt_path: Path,
    requested_llms: list[str],
    no_gemini: bool,
    n_target: int,
    runner_overrides: dict | None = None,
) -> int:
    """Core orchestration. Returns process-style exit code.

    ``runner_overrides`` lets unit tests inject canned LLM responses
    without invoking real subprocesses.
    """
    runners = dict(LLM_RUNNERS)
    if runner_overrides:
        runners.update(runner_overrides)

    exp_dir = ROOT / "experiments" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)

    meta = SUBJECT_METADATA.get(subject, {})
    target_weak_area = meta.get("target_weak_area", subject)
    weak_area_quote = meta.get(
        "weak_area_quote",
        f"(no recorded weak-area quote for subject {subject!r})",
    )

    template = prompt_path.read_text(encoding="utf-8")
    base_prompt = render_prompt(template, subject=subject,
                                weak_area_quote=weak_area_quote)
    pv = _prompt_version(template)

    if runner_overrides:
        # Tests pass overrides that don't depend on PATH lookups.
        active_llms = [name for name in requested_llms if name in runners]
    else:
        active_llms = _resolve_llms(requested_llms, no_gemini)
    if len(active_llms) < 2:
        print(
            f"FATAL: need at least 2 LLMs on PATH for diversity; got {active_llms}.",
            file=sys.stderr,
        )
        return 2

    raw_pool: list[dict] = []
    contributing: list[str] = []
    errors: list[str] = []
    for llm in active_llms:
        role = ROLE_PRIMING.get(llm, "")
        prompt = f"{role}\n\n{base_prompt}\n\nRespond with a JSON array of hypothesis objects."
        try:
            r = runners[llm](prompt)
            stdout = r.stdout or ""
            _save_raw(exp_dir, llm, stdout)
            parsed = parse_llm_response(stdout)
            if not parsed:
                errors.append(f"{llm}: no parseable hypothesis array in stdout")
                continue
            count_before = len(raw_pool)
            for raw in parsed:
                norm = normalise_hypothesis(raw, source=llm)
                if norm is not None:
                    raw_pool.append(norm)
            if len(raw_pool) > count_before:
                contributing.append(llm)
            else:
                errors.append(f"{llm}: every hypothesis failed normalisation")
        except subprocess.TimeoutExpired:
            errors.append(f"{llm}: timed out after {LLM_TIMEOUT_S}s")
        except Exception as e:  # noqa: BLE001 - per-LLM tolerance pattern
            errors.append(f"{llm}: {e!r}")

    if len(contributing) < 2:
        print(
            f"FATAL: only {len(contributing)} LLM(s) returned parseable "
            f"hypotheses (need >= 2). Errors: {errors}",
            file=sys.stderr,
        )
        return 2

    merged = merge_hypotheses(raw_pool)
    merged = ensure_wildcard(merged)

    warnings = distinctness_warnings(merged)
    if warnings:
        print(
            f"WARN: {len(warnings)} pair(s) have axis_commitments Jaccard "
            f">= {AXIS_OVERLAP_JACCARD}:",
            file=sys.stderr,
        )
        for w in warnings[:10]:
            print(f"  - {w}", file=sys.stderr)

    notes = None
    if errors:
        notes = "Per-LLM issues: " + "; ".join(errors)

    manifest = build_manifest(
        exp_id=exp_id,
        subject=subject,
        target_weak_area=target_weak_area,
        contributing_llms=contributing,
        hypotheses=merged,
        prompt_version=pv,
        notes=notes,
    )

    schema_errors = validate_manifest(manifest)
    if schema_errors:
        draft = exp_dir / "manifest.draft.yml"
        draft.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(
            "FATAL: manifest fails schema validation. "
            f"Wrote draft to {draft.relative_to(ROOT)}.",
            file=sys.stderr,
        )
        for err in schema_errors[:10]:
            ptr = "/" + "/".join(str(p) for p in err.path)
            print(f"  {ptr}: {err.message}", file=sys.stderr)
        return 3

    yml, js = write_manifest(manifest, exp_dir)
    print(f"manifest -> {yml.relative_to(ROOT)} ({len(merged)} hypotheses)")
    print(f"manifest -> {js.relative_to(ROOT)}")
    if errors:
        print(f"NOTE: {len(errors)} non-fatal LLM issue(s) — see manifest.notes",
              file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="experiment-generate",
        description="Multi-LLM hypothesis generator for issue #29 design experimentation.",
    )
    ap.add_argument("exp_id", nargs="?",
                    help="Experiment id (kebab-case), e.g. falzflyer-p2-mein-plan")
    ap.add_argument("--subject", default=None,
                    help="Subject region (default: same as exp_id)")
    ap.add_argument("--prompt", default=str(DEFAULT_PROMPT_PATH),
                    help="Path to the prompt template markdown.")
    ap.add_argument("--n-target", type=int, default=12,
                    help="Target raw count per LLM (post-dedup we expect ~10).")
    ap.add_argument("--llms", default="claude,codex,gemini",
                    help="Comma-separated LLM names (claude, codex, gemini).")
    ap.add_argument("--no-gemini", action="store_true",
                    help="Skip Gemini even if it is on PATH.")
    args = ap.parse_args(argv)

    if not args.exp_id:
        ap.print_help()
        return 0

    exp_id = args.exp_id
    subject = args.subject or exp_id
    requested = [s.strip() for s in args.llms.split(",") if s.strip()]
    return run_generation(
        exp_id=exp_id,
        subject=subject,
        prompt_path=Path(args.prompt),
        requested_llms=requested,
        no_gemini=args.no_gemini,
        n_target=args.n_target,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
