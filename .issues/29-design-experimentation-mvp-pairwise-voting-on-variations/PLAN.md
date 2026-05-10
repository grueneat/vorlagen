# Plan: Design Experimentation MVP — Pairwise Voting on Variations

- **Slug:** `29-design-experimentation-mvp-pairwise-voting-on-variations`
- **Generated:** 2026-05-10
- **Issue:** `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/ISSUE.md`
- **Research:** `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/RESEARCH.md`
- **Context (locked decisions):** `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/CONTEXT.md`

<objective>
Deliver an end-to-end design experimentation MVP that turns "weak design areas" into corpus growth: (a) a multi-LLM hypothesis generator that produces ≥10 structurally-distinct variations of falzflyer P2 "Mein Plan", (b) a deterministic variant render pipeline that emits in-situ full-page previews, (c) an Astro voting page with direct-pick + versus modes that records two-axis (appeal + transport) votes to localStorage and exports JSON, (d) a results aggregator that ranks variations and surfaces axis disagreement, and (e) a real run by Flo whose top-3 / bottom-3 outcomes are committed back into `design-guide/gruene-corpus.md` with provenance. The feedback loop — not just the tooling — is the deliverable.
</objective>

<acceptance_gate>
**PR is NOT mergeable until ALL of the following are committed in this branch (per CONTEXT.md decision #11):**

1. All unit/integration tests pass: `python3 -m unittest discover tools/sla_lib/tests`.
2. `npm --prefix site run build` exits 0.
3. `experiments/falzflyer-p2-mein-plan/manifest.yml` exists with ≥10 hypotheses, ≥1 wildcard, ≥2 contributing LLMs.
4. `experiments/falzflyer-p2-mein-plan/variants/<slug>/page-01.png` (and `page-01-hires.png`) exist for every variant in the manifest, mirrored to `site/public/experiments/falzflyer-p2-mein-plan/<slug>/`.
5. `experiments/falzflyer-p2-mein-plan/results/flo-<YYYY-MM-DD>.json` is committed (real votes, not synthetic).
6. `design-guide/gruene-corpus.md` is amended with at least 3 winning + 3 losing entries, each tagged `provenance: experiment falzflyer-p2-mein-plan run flo-<YYYY-MM-DD>`.
7. All 8 acceptance-criteria checkboxes from `ISSUE.md` are ticked.

A run that produced no clear winners or no clear losers still satisfies the gate iff the corpus update records that null result with provenance — null results are corpus content too.
</acceptance_gate>

<resolved_uncertainties>
Resolutions of the 7 open uncertainties from RESEARCH.md §"Open Uncertainties". These are LOCKED for this plan; do not relitigate during execution.

1. **Variant SLA scope:** Keep the full 2-page Document, output only `page-01.png` + `page-01-hires.png`. Rationale: zero-cost reuse of `_add_back`, fewer code paths, and the existing render pipeline already supports per-page rasterisation.
2. **Where to factor the hoist:** Create a NEW module `templates/kandidat-falzflyer-din-lang/variant_scaffold.py` exposing `build_variant_front(p2_render_fn) -> Document`. Rationale: keeps the production `build.py` byte-stable, isolates experimental code surface, easier to delete later without touching production templates.
3. **Astro: content collection vs filesystem-direct:** Use a content collection. Rationale: mirrors the templates pattern at `site/src/content.config.ts`, gives type safety and Astro 5 native hot-reload, and removes the need to scan `site/public/` at build time.
4. **Brand-rule enforcement on variants:** Run `inside_page` and structural alignment checks (`audit_alignment` if it can be invoked programmatically — else just `inside_page`). Do NOT run `BRAND_CONSTRAINTS` on variants. Rationale: variants are research artifacts and some hypotheses (e.g., asymmetric-balance, italic-emphasis) deliberately violate brand rules — that's the point. A failed variant is dropped from the bag with a clear log message; voting only happens on variants that fit on the page.
5. **`_verify_brand_fonts`:** YES — `bin/experiment-render` calls it before rendering any variant. Rationale: without it a missing-fonts environment renders DejaVu fallback silently and invalidates the entire run.
6. **LLM mix for hypothesis generation:** `claude --print --output-format json -p <prompt>` (Anthropic via authenticated CLI) + `codex exec` (OpenAI/GPT). `gemini --yolo` is OPTIONAL and run if `shutil.which("gemini")` succeeds. Pipeline runs as long as ≥2 LLMs respond; fails loudly if <2. Rationale: matches `tools/visual_review.py:209-258`, satisfies CONTEXT.md decision #6, no API key management.
7. **Per-axis keyboard shortcut scheme:** `Q` / `W` for axis-A (appeal) left/right; `O` / `P` for axis-T (transport) left/right; `Space` to skip pair; `E` to export. Document the scheme on-page in a small "Shortcuts" panel. Rationale: two-handed parallel input matches the two-axis voting model better than mode-switching with Tab; left-hand vs right-hand mapping keeps the axes spatially separated.
</resolved_uncertainties>

<skills>
The workspace has NO `.claude/skills/` directory at this time (verified 2026-05-10). The plan therefore relies on repo conventions documented in RESEARCH.md and the existing code. Specifically:

- New `.py` files under `tools/` MUST pass `ruff check` and `mypy --strict` if the existing CI gate runs them; mirror style of `tools/visual_review.py` and `tools/render_pipeline.py`.
- New `.astro` / `.ts` files MUST not introduce dependencies; vanilla JS in `<script>` blocks only (mirror `site/src/pages/templates/[...id].astro`).
- Shell shims (`bin/experiment-*`) follow the 14-line shape of `bin/render-gallery`.
</skills>

<context>
Issue: `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/ISSUE.md`
Research synthesis: `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/RESEARCH.md`
Per-area research (depth, optional reads): `research/codebase.md`, `research/ecosystem.md`, `research/pitfalls.md`

Key reference files (executor reads as needed):
- `templates/kandidat-falzflyer-din-lang/build.py` — production builder; lines 329 (`_add_front`) and 432–505 (P2 anatomy) are the refactor + variant target
- `templates/kandidat-falzflyer-din-lang/meta.yml` — `preview_dpi: 100`
- `tools/visual_review.py:209-258` — multi-LLM subprocess pattern (gold reference)
- `tools/visual_diff.py:112-150` — `render_sla_to_pdf`, `rasterise`
- `tools/render_pipeline.py:75-343` — `_scrub_pdf_metadata`, `_verify_brand_fonts`, `_zero_pad_pngs`, DPI constants
- `tools/sla_lib/builder/__init__.py` — DSL public API
- `tools/gallery_build.py` — preview-mirror pipeline reference for `experiment_render.py`'s site-mirror step
- `site/src/pages/templates/[...id].astro` — Astro routing + lightbox idiom to mirror
- `site/src/content.config.ts` — content collection schema to extend
- `bin/render-gallery` — shim shape
- `shared/template-spec.schema.yaml` — jsonschema-in-YAML pattern
- `design-guide/gruene-corpus.md` — corpus update target (§6 P2 critique, §8 failure modes)
- `Dockerfile.claude` — pinned tool versions; brand fonts live here

<interfaces>
<!-- Executor: use these contracts directly. Do not re-derive from source. -->

// === DSL public re-exports — tools/sla_lib/builder/__init__.py:1-9 ===
from sla_lib.builder import (
    Document, Page,                                    // document.py
    Color, Style, load_ci,                             // ci.py
    TextFrame, ImageFrame, Polygon,                    // primitives.py
    Line, Anchor, Run, pack_inline_image,
    ParaStyle, CharStyle, DocumentLayer, SoftShadow,   // styles.py
    Brand,                                             // brand.py
    blocks,                                            // blocks.py — FoldLine, PageBackground
    library,                                           // library.py — load/inject_into_frame
    AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
    GridSpec, GridCell, HierarchyBlock,                // composites.py
    same_y, same_x, same_size, mirrored_x, mirrored_y, // constraints.py
    inside, equal_gap, hierarchy, same_style,
    distance_y, distance_x, aligned_below,
    Constraint, Violation,
    BRAND_CONSTRAINTS, BrandRule,                      // brand_constraints.py
)

// `Document(brand=Brand.gruene_noe(), …)` auto-registers all CI colors,
// paragraph-styles, char-styles, layers (document.py:215-244). Variant
// scripts may add per-variant ParaStyle via doc.add_para_style(...).

// === Render pipeline reusables — tools/visual_diff.py + tools/render_pipeline.py ===
def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None       // visual_diff.py:112
def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path] // visual_diff.py:146
def _scrub_pdf_metadata(p: Path) -> None                            // render_pipeline.py:75
def _verify_brand_fonts() -> None                                   // render_pipeline.py:257 (MUST run)
def _zero_pad_pngs(tdir: Path, prefix: str) -> None                 // render_pipeline.py:343
DEFAULT_DPI = 50                                                    // render_pipeline.py:41
HIRES_DPI = 150                                                     // render_pipeline.py:46
// Falzflyer thumbnail dpi: 100 (templates/kandidat-falzflyer-din-lang/meta.yml:7)

// === Falzflyer P2 anatomy — templates/kandidat-falzflyer-din-lang/build.py:432-491 ===
// PAGEOBJECTs that variants may replace/move/restyle; "P2 " anname prefix MUST be preserved:
//   P2 Top-Band       Polygon Dunkelgrün  (99,  -3, 99,  31)   build.py:434
//   P2 Top-Title      TextFrame "Mein Plan" (105, 8, 87, 14)   build.py:436-443
//   P2 Teaser-Headline TextFrame ".." (105, 38, 87, 22)        build.py:445-453
//   P2 Body-Backing   Polygon Hellgrün    (99,  28, 99, 185)   build.py:455-467
//   P2 Teaser-Body    5 Schlagwort paragraphs (105, 72, 87, 130) build.py:469-491
// CONSTRAINTS coupling P2 → other panels: only same_size("P2 Top-Band", ...) (build.py:966-1024).
// Variants MAY relax this for the variant build (factor accordingly).

// === Multi-LLM subprocess pattern — tools/visual_review.py:209-258 ===
if shutil.which("codex"):
    subprocess.run(
        ["codex", "exec",
         "--skip-git-repo-check",
         "--sandbox", "workspace-write",
         "--dangerously-bypass-approvals-and-sandbox",
         prompt],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
    )

if shutil.which("claude"):
    subprocess.run(
        ["claude", "--print", "--output-format", "json", "-p", prompt],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
    )

if shutil.which("gemini"):
    subprocess.run(
        ["gemini", "--yolo", "-p", prompt],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
    )

// Per-LLM error tolerance: wrap each in try/except Exception; record the
// failure and continue. Fail the run only if FEWER THAN 2 LLMs returned
// parseable output.

// === Astro content collection (existing pattern) — site/src/content.config.ts ===
const templates = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/templates' }),
  schema: z.object({ id: z.string(), version: z.string(), title: z.string(),
                     /* ... permissive z.record(z.any()) for nested ... */ }),
});
export const collections = { templates };

// === Bin shim shape — bin/render-gallery (14 lines verbatim model) ===
#!/usr/bin/env python3
"""bin/<name> — entry point for <module>. Implementation in tools/<module>.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from <module> import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
</interfaces>
</context>

<commit_format>
Format: conventional with numeric-id prefix (per `.issues/config.yaml`).
Pattern: `29: <type>(<scope>): <description>`
Examples:
- `29: feat(experiments): add hypothesis generator (multi-LLM)`
- `29: feat(site): add experiments voting page`
- `29: feat(corpus): record top-3/bottom-3 from falzflyer-p2-mein-plan run`
- `29: test(experiments): wins-ratio + disagreement index`
- `29: chore(experiments): scaffold directories + bin shims`
</commit_format>

<tasks>

<task id="T01" type="auto">
  <name>T01: Scaffold directories, schema stubs, bin shims, route placeholders</name>
  <files>
    experiments/.gitkeep,
    experiments/_schema/.gitkeep,
    tools/experiment_hypothesis_gen.py (stub),
    tools/experiment_render.py (stub),
    tools/experiment_results.py (stub),
    tools/experiment_generate/prompt_template.md (empty placeholder),
    bin/experiment-generate,
    bin/experiment-render,
    bin/experiment-results,
    site/src/pages/experiments/index.astro (placeholder),
    site/src/pages/experiments/[id].astro (placeholder),
    site/src/content/experiments/.gitkeep
  </files>
  <action>
  Create the directory skeleton. Each tools/experiment_*.py stub exports a `def main(argv: list[str]) -> int: raise SystemExit("not implemented")` so the bin shims load. Each bin shim follows the 14-line `bin/render-gallery` pattern (imports `main` from the module under `tools/`). Astro placeholders contain a single `<h1>experiments — TBD</h1>` and a frontmatter import of `getCollection('experiments')` returning empty list. Empty schema directory exists for T03/T04. `tools/experiment_generate/` is a directory containing only `prompt_template.md` (empty) — populated in T06.

  Make all bin shims executable: `chmod +x bin/experiment-generate bin/experiment-render bin/experiment-results`.
  </action>
  <verify>
  <automated>
  test -x bin/experiment-generate && test -x bin/experiment-render && test -x bin/experiment-results
  python3 -c "import sys; sys.path.insert(0, 'tools'); import experiment_hypothesis_gen, experiment_render, experiment_results; print('OK')"
  npm --prefix site run build
  </automated>
  </verify>
  <done>
  Directory tree matches the layout in RESEARCH.md "Manifest / experiment lifecycle"; `npm --prefix site run build` succeeds with placeholder pages rendering; all three bin shims execute and exit non-zero with "not implemented" message.
  </done>
</task>

<task id="T02" type="auto">
  <name>T02: Hoist `_add_front` into `variant_scaffold.py`</name>
  <files>
    templates/kandidat-falzflyer-din-lang/variant_scaffold.py (new),
    tools/sla_lib/tests/test_falzflyer_variant_scaffold.py (new)
  </files>
  <action>
  Per resolved uncertainty #2, create a new module `templates/kandidat-falzflyer-din-lang/variant_scaffold.py`. Do NOT modify `templates/kandidat-falzflyer-din-lang/build.py` — production rendering must remain byte-stable (verify via `bin/render-gallery kandidat-falzflyer-din-lang` after this task; output PNGs must hash-equal pre-task output).

  In `variant_scaffold.py`:
  - Re-implement the side of `_add_front` that builds P1, P3, fold-lines, page background, and the back page wiring — by IMPORTING the relevant private helpers from `templates/kandidat-falzflyer-din-lang/build.py` (e.g. `from build import _add_back, _front_p1, _front_p3, _add_fold_lines` — adjust if those helpers don't exist by introducing a tightly-scoped re-export shim in `build.py` that does NOT change its public behavior).
  - If extracting helpers from `build.py` is not feasible without changing it, take the alternative path: copy the P1/P3/back-page code into `variant_scaffold.py` verbatim and keep the duplication noted as TODO in a comment. Production `build.py` MUST NOT be touched.
  - Define and export:
    ```python
    def render_p2_default(doc: Document, page: Page) -> None:
        # the existing build.py:432-491 code, lifted unchanged
    def build_variant_front(p2_render_fn=render_p2_default) -> Document:
        # builds full 2-page Document; calls p2_render_fn(doc, page0) instead of inline P2
    ```
  - `build_variant_front` returns a fully-built `Document`; the caller saves the SLA.
  - Add a docstring noting that `BRAND_CONSTRAINTS` are NOT auto-applied (per resolved uncertainty #4) and that `inside_page` is the responsibility of the variant render orchestrator.

  Test: `tools/sla_lib/tests/test_falzflyer_variant_scaffold.py` calls `build_variant_front()` (no override), saves to a temp `.sla`, and asserts the file exists and the Document has expected anames including `"P2 Top-Band"`, `"P2 Top-Title"`, `"P2 Teaser-Headline"`, `"P2 Body-Backing"`, and at least one `"P2 Teaser-Body"` PAGEOBJECT.
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_falzflyer_variant_scaffold
  bin/render-gallery kandidat-falzflyer-din-lang   # production unchanged
  </automated>
  </verify>
  <done>
  `variant_scaffold.build_variant_front()` produces a valid 2-page Document with default P2 content; production `build.py` rendering output is byte-identical to pre-task; new test passes.
  </done>
</task>

<task id="T03" type="auto">
  <name>T03: Manifest schema (jsonschema Draft 2020-12, in YAML)</name>
  <files>
    experiments/_schema/manifest.schema.yaml (new),
    tools/sla_lib/tests/test_experiment_manifest_schema.py (new),
    experiments/_schema/manifest.example.yml (new — fixture for tests)
  </files>
  <action>
  Mirror the style of `shared/template-spec.schema.yaml` (Draft 2020-12 in YAML). Top-level fields:
  - `id` (string, kebab-case)
  - `subject` (string, e.g. `falzflyer-p2-mein-plan`)
  - `target_weak_area` (string; references corpus section like `gruene-corpus.md §6`)
  - `contributing_llms` (array of strings, e.g. `["claude:opus", "codex:gpt-5", "gemini"]`)
  - `created` (ISO 8601 date)
  - `prompt_version` (string, hash or semver of the prompt template)
  - `hypotheses` (array, minItems: 10) — each item:
    - `slug` (kebab-case string)
    - `name` (human-readable)
    - `axis_commitments` (array of strings from a controlled vocab: `density`, `hierarchy`, `typography`, `asymmetry`, `photographic-vs-typographic`, `accent-strategy`, `whitespace-strategy`, `voice-formality`, `wildcard`)
    - `rationale` (string, 1–3 sentences)
    - `expected_outcome` (string, 1 sentence)
    - `sources` (array of strings, e.g. `["claude:opus", "gemini"]`) — provenance
    - `builder` (string — relative path to the `.py` file under `variants/`)
    - `wildcard` (boolean; default false; AT LEAST ONE hypothesis MUST be true — enforce with a top-level `contains` clause: `hypotheses` must contain ≥1 item with `wildcard: true`)
  - `additionalProperties: false` at every level.

  Provide `manifest.example.yml` containing 10 dummy hypotheses (one wildcard) that validates against the schema.

  Test loads schema with `yaml.safe_load`, loads example with `yaml.safe_load`, validates via `jsonschema.Draft202012Validator`. Also tests rejection: a copy with 9 hypotheses fails; a copy with 10 hypotheses but no wildcard fails.
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_experiment_manifest_schema
  </automated>
  </verify>
  <done>
  Schema rejects manifests with &lt;10 hypotheses, with no wildcard, with unknown axis_commitments values, or with missing required fields. Example manifest validates.
  </done>
</task>

<task id="T04" type="auto">
  <name>T04: Results JSON schema</name>
  <files>
    experiments/_schema/results.schema.yaml (new),
    tools/sla_lib/tests/test_experiment_results_schema.py (new),
    experiments/_schema/results.example.json (new — fixture)
  </files>
  <action>
  Per CONTEXT.md decision #10. Top-level fields:
  - `experiment_id` (string)
  - `rater` (string, free text; can be `"anonymous"`)
  - `session_start` / `session_end` (ISO 8601 timestamps)
  - `votes` (array) — each item:
    - `pair` (object: `a` (variant slug), `b` (variant slug))
    - `axis` (enum: `appeal`, `transport`)
    - `winner` (string: variant slug, OR `null` if skipped, OR string `"skip"`)
    - `position_a_on_screen` (enum: `left`, `right`)
    - `timestamp` (ISO 8601)
  - `direct_picks` (array of variant slugs marked as favorites in direct-pick mode; may be empty)
  - `wins_ratio_appeal` / `wins_ratio_transport` (object: `<slug>: { wins: int, plays: int }`)
  - `ranking_appeal` / `ranking_transport` (array of slugs, sorted desc)
  - `disagreement_index` (number 0..1, fraction of pairs where appeal-winner ≠ transport-winner)
  - `spearman_appeal_transport` (number -1..1, Spearman rho between the two rankings)

  Provide `results.example.json` with 5 votes, 3 variants, computed aggregates. Test validates the example and asserts the schema rejects a missing `axis`, an unknown enum, or `position_a_on_screen` not in {left,right}.
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_experiment_results_schema
  </automated>
  </verify>
  <done>
  Schema accepts the example; rejects each malformation listed above with a precise JSON Pointer error.
  </done>
</task>

<task id="T05" type="auto">
  <name>T05: Implement `tools/experiment_hypothesis_gen.py` (multi-LLM)</name>
  <files>
    tools/experiment_hypothesis_gen.py (replace stub),
    tools/sla_lib/tests/test_experiment_hypothesis_gen.py (new)
  </files>
  <action>
  Mirror `tools/visual_review.py:209-258`. Public entry point:

  ```python
  def main(argv: list[str]) -> int:
      # CLI: experiment-generate <exp-id> [--subject <subject>] [--prompt <path>]
      #                                   [--n-target 12] [--no-gemini] [--llms claude,codex,gemini]
  ```

  Behaviour:
  1. Parse args. Default `--prompt = tools/experiment_generate/prompt_template.md`. Default `--subject = "falzflyer-p2-mein-plan"`.
  2. Build per-LLM role-primed prompts: prepend `"Role: typography-first designer.\n\n"` for Claude, `"Role: hierarchy-first designer.\n\n"` for Codex, `"Role: asymmetry-first designer.\n\n"` for Gemini (per RESEARCH.md "Hypothesis generation prompt").
  3. For each LLM available via `shutil.which`: run the subprocess command from the `<interfaces>` block above with `timeout=600`, `stdin=subprocess.DEVNULL`, `capture_output=True`. Wrap each in `try/except Exception as e: errors.append(...)` so partial failure does not abort. **Save raw stdout to `experiments/<exp-id>/_llm-raw/<llm>-<timestamp>.txt` BEFORE parsing**, so even malformed responses are auditable.
  4. Tolerant JSON parser: strip Markdown code fences, then extract substring from first `{` to last matching `}`. Validate against an inline `expected_response_schema` (an array of hypothesis objects with `slug`, `name`, `axis_commitments`, `rationale`, `expected_outcome`, `wildcard`).
  5. Merge & dedupe: across all responses, group hypotheses where (a) slug is identical OR (b) `difflib.SequenceMatcher(None, h1.name, h2.name).ratio() >= 0.75`. For each group, keep the longest `rationale`, union the `axis_commitments`, set `sources` to the union of contributing LLMs, set `wildcard` to `any(h.wildcard for h in group)`.
  6. Distinctness check: count groups whose `axis_commitments` overlap by Jaccard ≥0.6 with another group; warn (don't fail) if >50% of groups overlap. Log a per-group axis-commitment table.
  7. Wildcard enforcement: if 0 wildcards in the merged set, append a synthetic `{slug: "wildcard-placeholder", wildcard: true, name: "PLACEHOLDER — replace before render", ...}` and emit a warning telling Flo to manually author one.
  8. Write `experiments/<exp-id>/manifest.yml` (yaml.safe_dump, sort_keys=False) AND `experiments/<exp-id>/manifest.json` (json.dumps with indent=2). Validate the YAML against `experiments/_schema/manifest.schema.yaml` before writing — if validation fails, write to `manifest.draft.yml` and exit nonzero with the JSON Pointer error.
  9. Fail loudly (exit 2) if fewer than 2 LLMs returned parseable output.

  Test (`test_experiment_hypothesis_gen.py`): mock `subprocess.run` with three canned LLM responses (one with overlapping slug to exercise dedup, one Markdown-fenced, one plain JSON) using `unittest.mock.patch`. Assert: 3 LLMs → ≥10 dedup'd hypotheses, manifest validates against schema, raw outputs are written to `_llm-raw/`, sources reflect attribution, wildcard present.
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_experiment_hypothesis_gen
  </automated>
  </verify>
  <done>
  Test passes; given 3 mocked LLM responses, the generator writes a schema-valid `manifest.yml`, mirrors raw outputs to `_llm-raw/`, attributes sources correctly, and exits 0. Given only 1 mocked successful LLM, it exits 2.
  </done>
</task>

<task id="T06" type="auto">
  <name>T06: Author the hypothesis-generation prompt</name>
  <files>
    tools/experiment_generate/prompt_template.md (replace empty),
    tools/sla_lib/tests/test_experiment_prompt_template.py (new)
  </files>
  <action>
  This prompt is the heart of the system. Quality matters more than concision. The prompt MUST contain (per RESEARCH.md "Hypothesis generation prompt" and pitfalls §1):

  1. **Subject context block** (templated by `experiment_hypothesis_gen.py` via simple `{subject}` and `{weak_area_quote}` substitutions): a paragraph stating what region is being varied, the named failure mode from `design-guide/gruene-corpus.md` §2.1 / §6 / §8, and what success looks like.
  2. **Positive examples** (≥4): e.g.
     - GOOD: `cut-to-three-with-body-text` — anatomy commitment, replaces 5 bullets with 3 items + one-sentence body each.
     - GOOD: `privilege-one-item-via-yellow-accent` — accent-strategy commitment, single-item Hellgrün → Gelb swap with explicit hierarchy.
     - GOOD: `vollkorn-italic-priority-emphasis` — typography-strategy commitment.
     - GOOD: `asymmetric-balance-not-centered` — composition commitment.
  3. **Negative examples** (≥4): e.g.
     - BAD: change spacing 8mm → 12mm.
     - BAD: change font size 18pt → 20pt.
     - BAD: rephrase one bullet text.
     - BAD: change Hellgrün hex by 5%.
  4. **Commitment-axis taxonomy** — list of allowed `axis_commitments` values (mirroring T03 schema enum).
  5. **Mandatory wild-card clause** — "exactly one hypothesis MUST set `wildcard: true` and propose something the role-primed designer would not normally suggest."
  6. **Strict JSON output schema** with an example response (one hypothesis filled in fully).
  7. **Anti-collapse instruction:** "Hypotheses must commit on different axis combinations. Two hypotheses with overlapping `axis_commitments` Jaccard >0.6 should not both appear."
  8. Target: produce 8–12 hypotheses per generator (so dedup across 2–3 generators yields 12–24 raw → ≥10 deduped).

  The file is a Markdown document with `{subject}` and `{weak_area_quote}` template tokens. The hypothesis_gen tool replaces them at run time via `str.format` (escape literal braces).

  Test asserts: file exists; contains at least 4 lines starting with `GOOD:` and 4 with `BAD:`; contains the literal token `{subject}` and `{weak_area_quote}`; contains the literal axis-commitments enum values from T03; contains the literal `"wildcard": true`.
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_experiment_prompt_template
  </automated>
  </verify>
  <done>
  Prompt file passes structural assertions; rendered prompt (with substitutions applied) is between 1500 and 5000 tokens (roughly 6000–20000 chars).
  </done>
</task>

<task id="T07" type="auto">
  <name>T07: Implement `tools/experiment_render.py` (variant orchestrator)</name>
  <files>
    tools/experiment_render.py (replace stub),
    tools/sla_lib/tests/test_experiment_render.py (new),
    tools/sla_lib/tests/fixtures/synthetic_variant.py (new)
  </files>
  <action>
  Mirrors the shape of `tools/render_pipeline.py`. Public entry point: `def main(argv: list[str]) -> int:`. CLI: `experiment-render <exp-id> [--only <slug>] [--skip-fonts-check]`.

  Steps:
  1. Load `experiments/<exp-id>/manifest.yml` via `yaml.safe_load`. Validate against `experiments/_schema/manifest.schema.yaml`. Hard-fail with JSON Pointer on schema error.
  2. Run `_verify_brand_fonts()` (from `tools/render_pipeline.py`) UNLESS `--skip-fonts-check` is passed. Exit 3 on failure.
  3. For each hypothesis in `manifest.yml.hypotheses`:
     - Load the variant module via `importlib.util.spec_from_file_location(...)`, looking for a callable `render_p2(doc, page) -> None`.
     - Call `from variant_scaffold import build_variant_front; doc = build_variant_front(variant.render_p2)`.
     - Save SLA to `experiments/<exp-id>/variants/<slug>/template.sla`.
     - Run constraint check: only `inside_page` (per resolved uncertainty #4). If any violation, log "DROP <slug>: <reason>" and continue without rendering. Track dropped variants for the summary.
     - Render to PDF: `render_sla_to_pdf(sla_path, pdf_path)`. Run `_scrub_pdf_metadata(pdf_path)`.
     - Rasterise at preview_dpi=100 → `page-01.png`, then at HIRES_DPI=150 → `page-01-hires.png`. Discard page-02 outputs.
     - Mirror to `site/public/experiments/<exp-id>/<slug>/page-01.png` and `page-01-hires.png` (use `shutil.copy2`).
  4. After all variants: write `experiments/<exp-id>/manifest.json` (Vite-importable JSON copy of the manifest, dropped variants excluded, with each hypothesis enriched by `_previews: { thumb: "/experiments/<exp-id>/<slug>/page-01.png", hires: "/experiments/<exp-id>/<slug>/page-01-hires.png" }`).
  5. Write `site/src/content/experiments/<exp-id>.md` with YAML frontmatter mirroring `manifest.json` (so the Astro content collection in T10 can `getEntry`).
  6. Print a summary: variants rendered, variants dropped, total time, output paths.

  Integration test (`test_experiment_render.py`):
  - Create a synthetic 1-hypothesis manifest under a temp `experiments/test-exp/`.
  - Provide `tools/sla_lib/tests/fixtures/synthetic_variant.py` exposing `render_p2(doc, page)` that adds a single tiny TextFrame.
  - Run `main(["test-exp", "--skip-fonts-check"])`.
  - Assert SLA, PDF, page-01.png exist at the expected paths; assert `site/public/experiments/test-exp/<slug>/page-01.png` was mirrored; assert `site/src/content/experiments/test-exp.md` was written.
  - If `xvfb-run scribus` is not available in the test environment, the test should skip with `unittest.SkipTest("Scribus not available")` rather than fail — but assert SLA write happens before the Scribus call so the build-side logic is still exercised. (Pattern: factor the render loop so SLA-write is separate from PDF-render.)
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_experiment_render
  </automated>
  </verify>
  <done>
  Synthetic variant renders end-to-end (in a Docker-like environment with fonts + Scribus + xvfb) producing SLA + PDF + PNG; mirror to `site/public/` works; `site/src/content/experiments/test-exp.md` is written. In environments without Scribus, the test asserts the pre-Scribus pipeline (manifest validate + module load + SLA write) and skips the PDF/PNG assertions.
  </done>
</task>

<task id="T08" type="auto">
  <name>T08: Implement `tools/experiment_results.py` (aggregation + ranking)</name>
  <files>
    tools/experiment_results.py (replace stub),
    tools/sla_lib/tests/test_experiment_results.py (new)
  </files>
  <action>
  CLI: `experiment-results <exp-id> [<results.json> ...]`. If no results files passed, glob `experiments/<exp-id>/results/*.json`. Multi-rater merging is OUT OF SCOPE per CONTEXT.md "Deferred" — but multiple results files from one rater (re-runs) ARE in scope.

  Steps:
  1. Validate every input JSON against `experiments/_schema/results.schema.yaml`. Fail loudly on any invalid file with a JSON Pointer.
  2. For each axis ∈ {appeal, transport}: aggregate `wins_ratio[<slug>] = wins / plays` (skipping votes with `winner == "skip"` or `null`). Sort to produce `ranking_<axis>` (desc).
  3. Compute `disagreement_index` = (count of pairs where appeal-winner ≠ transport-winner among pairs voted on BOTH axes) / (count of pairs voted on both axes). Pure stdlib, no scipy.
  4. Compute `spearman_appeal_transport` = Spearman rank correlation between the two rankings. Implement inline (no scipy): convert each ranking to ranks, compute Pearson on ranks. Use stdlib `statistics`.
  5. Emit a Markdown summary at `experiments/<exp-id>/results/SUMMARY.md`:
     - Header with rater(s) and dates.
     - Top-5 by appeal, top-5 by transport.
     - Bottom-3 by appeal, bottom-3 by transport.
     - Spearman rho with halo-flag interpretation (>0.85: halo; <0.5: working as intended; in between: ambiguous).
     - Per-pair disagreement table (slug-A, slug-B, appeal-winner, transport-winner) for the top-10 most-disagreed pairs.
     - "Suggested corpus entries" stub: top-3 + bottom-3 with their hypothesis `name` and `rationale`, formatted as Markdown ready to paste into `design-guide/gruene-corpus.md`.

  Tests:
  - Wins-ratio math: 3 variants, 6 votes per axis, hand-computed ratios. Assert exact values.
  - Disagreement index: synthetic results where 2 of 5 dual-axis pairs disagree → expect 0.4.
  - Spearman: identical rankings → 1.0; reversed → -1.0; one specific tied case with hand-computed expected value within 1e-9.
  - Schema validation: feeding malformed JSON exits non-zero.
  - Markdown summary: `SUMMARY.md` is written and contains all six required sections.
  </action>
  <verify>
  <automated>
  python3 -m unittest tools.sla_lib.tests.test_experiment_results
  </automated>
  </verify>
  <done>
  Test asserts exact wins-ratio values, disagreement = 0.4 on the constructed input, Spearman = 1.0 / -1.0 on identical/reversed rankings, schema rejects malformed input. SUMMARY.md is regenerated correctly.
  </done>
</task>

<task id="T09" type="auto">
  <name>T09: Wire bin shims to real implementations</name>
  <files>
    bin/experiment-generate (already created in T01 — verify),
    bin/experiment-render (already created in T01 — verify),
    bin/experiment-results (already created in T01 — verify)
  </files>
  <action>
  The shims were created as stubs in T01. After T05/T07/T08 land their `main()` functions, no further code change is needed — but verify each shim now produces help output instead of "not implemented". If any shim still raises SystemExit early, fix the import path. Add a `--help` flag handler in each tool's `main()` that prints usage and exits 0.
  </action>
  <verify>
  <automated>
  bin/experiment-generate --help && bin/experiment-render --help && bin/experiment-results --help
  </automated>
  </verify>
  <done>
  Each bin shim prints a usage block and exits 0.
  </done>
</task>

<task id="T10" type="auto">
  <name>T10: Add `experiments` content collection</name>
  <files>
    site/src/content.config.ts (modify),
    site/src/content/experiments/.gitkeep (already in T01)
  </files>
  <action>
  Extend `site/src/content.config.ts`. Add an `experiments` collection mirroring the `templates` shape:

  ```ts
  const experiments = defineCollection({
    loader: glob({ pattern: '**/*.md', base: './src/content/experiments' }),
    schema: z.object({
      id: z.string(),
      subject: z.string(),
      target_weak_area: z.string(),
      contributing_llms: z.array(z.string()),
      created: z.string(),
      prompt_version: z.string().optional(),
      hypotheses: z.array(z.any()),
    }),
  });
  export const collections = { templates, experiments };
  ```

  Test by writing a minimal `site/src/content/experiments/test-exp.md` with valid frontmatter (delete after build verification, or keep as a fixture) and running `npm --prefix site run build`.
  </action>
  <verify>
  <automated>
  npm --prefix site run build
  </automated>
  </verify>
  <done>
  `npm run build` succeeds with the `experiments` collection registered; no schema errors.
  </done>
</task>

<task id="T11" type="auto">
  <name>T11: Implement `experiments/index.astro` (list page)</name>
  <files>
    site/src/pages/experiments/index.astro (replace placeholder)
  </files>
  <action>
  Frontmatter: `import { getCollection } from 'astro:content'; const experiments = await getCollection('experiments');`. Render a list of `<a href="/experiments/{exp.data.id}">{exp.data.subject}</a>` with the contributing LLM list and hypothesis count per experiment. Mirror layout patterns from `site/src/pages/templates/index.astro` if it exists; otherwise use a simple `<main>` with the existing site stylesheet.

  No JS needed. Static page.
  </action>
  <verify>
  <automated>
  npm --prefix site run build
  test -f site/dist/experiments/index.html
  </automated>
  </verify>
  <done>
  `/experiments/` page lists every entry under `site/src/content/experiments/`; build output exists.
  </done>
</task>

<task id="T12" type="auto">
  <name>T12: Implement `experiments/[id].astro` (voting page — direct-pick + versus)</name>
  <files>
    site/src/pages/experiments/[id].astro (replace placeholder)
  </files>
  <action>
  This is the largest single artifact. Mirror the dynamic-route + lightbox pattern at `site/src/pages/templates/[...id].astro`.

  Frontmatter:
  - `export async function getStaticPaths()` returns `{ params: { id: exp.data.id }, props: { exp } }` for each entry in the `experiments` collection.
  - Read `props.exp.data.hypotheses` array; the variants and their preview paths are embedded in the manifest.json (mirrored to the markdown frontmatter by `experiment_render`).

  Page structure:
  - Header: experiment id, subject, contributing LLMs, hypothesis count.
  - Mode toggle: two buttons "Direct pick" / "Versus" — controls a CSS class on `<body>`. Default = direct-pick.
  - Direct-pick view: grid of all variants. Each card shows `page-01.png` (clickable for lightbox) + slug + name + axis_commitments + rationale. Star button per card toggles "favorite" → pushes/removes slug into `direct_picks` array in localStorage.
  - Versus view: header showing progress `X / N pairs voted (axis A) | Y / N pairs voted (axis T)` with two `<progress>` bars. Body: two big cards side by side (image as click target). Below each pair: TWO question rows: "Which appeals more?" with two big buttons; "Which transports better?" with two big buttons. Skip button. Auto-advance to next pair when BOTH axes voted (or skip clicked).
  - Keyboard: Q/W = axis-A left/right; O/P = axis-T left/right; Space = skip; E = export.
  - On entering versus mode: build the all-pairs array `[(a,b)]` for `i<j`, Fisher-Yates shuffle (pure JS implementation — DO NOT use `sort(() => Math.random() - 0.5)`). Per pair, randomly assign `position_a_on_screen ∈ {left, right}`.
  - Lightbox: mirror `site/src/pages/templates/[...id].astro:55-90`. Click a card image → fullscreen overlay with `page-01-hires.png`; Esc / click-outside closes.
  - localStorage key: `experiment:{id}:session:v1`. Single object: `{ rater, session_start, votes, direct_picks }`. On each vote: read, push, write. Detect non-persistent storage: `try { localStorage.setItem('__test', '1'); localStorage.removeItem('__test'); } catch { showBanner('Your browser is not persisting state. Export progress frequently.'); }`.
  - Export button (always visible, top-right): builds the full results object including `wins_ratio_*`, `ranking_*`, `disagreement_index`, `spearman_*` (compute client-side; same algorithms as T08 but in JS — duplicate the logic, no shared lib). Then `Blob` + `URL.createObjectURL` + temporary `<a download="{rater}-{id}-{ISO timestamp}.json">` + `revokeObjectURL`. Filename example: `flo-falzflyer-p2-mein-plan-2026-05-10T14-32-00Z.json`.
  - Rater identity: `<input>` field at top, written into localStorage on change. Defaults to "anonymous".
  - On-page Shortcuts panel listing the keyboard scheme.

  No JS framework. Vanilla JS in `<script>` tags. Astro scoped `<style>` for CSS.

  No automated test for this artifact (vanilla JS in static-site context). Verification is via T14's manual smoke + `npm run build` succeeding.
  </action>
  <verify>
  <automated>
  npm --prefix site run build
  # Build must succeed; static HTML for /experiments/[id]/ generated for at least one experiment.
  </automated>
  </verify>
  <done>
  Build succeeds; `/experiments/<id>/index.html` contains both modes; the page has no JavaScript console errors when smoke-tested in T14.
  </done>
</task>

<task id="T13" type="auto">
  <name>T13: Generate the MVP hypothesis manifest</name>
  <files>
    experiments/falzflyer-p2-mein-plan/manifest.yml (new — generated),
    experiments/falzflyer-p2-mein-plan/manifest.json (new — generated),
    experiments/falzflyer-p2-mein-plan/_llm-raw/* (new — preserved)
  </files>
  <action>
  Run `bin/experiment-generate falzflyer-p2-mein-plan --subject falzflyer-p2-mein-plan`. This invokes T05/T06.

  Post-condition manual checks (executor verifies before moving on):
  1. `manifest.yml` validates against `experiments/_schema/manifest.schema.yaml` (script does this; double-check by running `python3 -c "import yaml, jsonschema; ..."`).
  2. `len(hypotheses) >= 10`, `any(h.wildcard for h in hypotheses)` is True.
  3. `len(set().union(*[h.sources for h in hypotheses])) >= 2` (≥2 contributing LLMs).
  4. Visual diff sanity check: at least 6 of the 10 hypotheses must commit on DIFFERENT primary axes (eyeball the `axis_commitments` distribution). If <6, run again with a different seed or augment the prompt — do not advance with a manifest dominated by parameter-tweak variations. (This is the central pitfall from RESEARCH.md §"Common Pitfalls" #1.)
  5. Each hypothesis has a `builder` path pointing to `variants/<slug>.py`; those files DO NOT exist yet — they are written by Sonnet (or by you the executor) in a follow-up bulk-codegen step. Generation step:
     - For each hypothesis in the manifest, write `experiments/falzflyer-p2-mein-plan/variants/<slug>.py` containing a `render_p2(doc, page)` function that implements the described change. Reuse default code from `variant_scaffold.render_p2_default` and modify only what the hypothesis says to change. Each variant ≤80 lines.
     - This is the "Sonnet generates the variations" step from ISSUE.md "Cost-optimisation strategy". The current executor does it directly.

  Each variant file MUST start with a docstring including the hypothesis name + axis_commitments + rationale, so the artifact is self-documenting.
  </action>
  <verify>
  <automated>
  python3 -c "
  import yaml, jsonschema
  m = yaml.safe_load(open('experiments/falzflyer-p2-mein-plan/manifest.yml'))
  schema = yaml.safe_load(open('experiments/_schema/manifest.schema.yaml'))
  jsonschema.Draft202012Validator(schema).validate(m)
  hs = m['hypotheses']
  assert len(hs) >= 10, f'need ≥10, got {len(hs)}'
  assert any(h.get('wildcard') for h in hs), 'need ≥1 wildcard'
  llms = set()
  for h in hs: llms.update(h['sources'])
  assert len(llms) >= 2, f'need ≥2 LLMs, got {llms}'
  axes = set()
  for h in hs: axes.update(h['axis_commitments'])
  assert len(axes) >= 5, f'need ≥5 distinct axes across hypotheses, got {axes}'
  print('manifest OK:', len(hs), 'hypotheses,', len(llms), 'LLMs,', len(axes), 'axes')
  "
  for h in $(python3 -c "import yaml; print('\n'.join(h['slug'] for h in yaml.safe_load(open('experiments/falzflyer-p2-mein-plan/manifest.yml'))['hypotheses']))"); do
    test -f experiments/falzflyer-p2-mein-plan/variants/$h.py || (echo "MISSING: variants/$h.py" && exit 1)
  done
  </automated>
  </verify>
  <done>
  Manifest validates and meets all acceptance bars; variant `.py` files exist for every hypothesis in the manifest; raw LLM outputs preserved under `_llm-raw/`.
  </done>
</task>

<task id="T14" type="auto">
  <name>T14: Render variants and run the end-to-end build</name>
  <files>
    experiments/falzflyer-p2-mein-plan/variants/*/page-01.png (generated),
    experiments/falzflyer-p2-mein-plan/variants/*/page-01-hires.png (generated),
    site/public/experiments/falzflyer-p2-mein-plan/* (mirrored),
    site/src/content/experiments/falzflyer-p2-mein-plan.md (generated)
  </files>
  <action>
  Run `bin/experiment-render falzflyer-p2-mein-plan`. Expected outcomes:
  1. `_verify_brand_fonts()` passes (will fail on a non-Docker host; run inside `Dockerfile.claude` if local fails).
  2. Each variant produces `page-01.png` + `page-01-hires.png` OR is dropped with a clear `inside_page` violation message. Track drops; if >2 drops, investigate whether the geometry constraint inheritance is causing them.
  3. Mirror artifacts to `site/public/experiments/falzflyer-p2-mein-plan/<slug>/`.
  4. `site/src/content/experiments/falzflyer-p2-mein-plan.md` is written by the renderer.
  5. Run `npm --prefix site run build`. Open the resulting site in `npm run preview` (or `npm run dev`) and load `/experiments/falzflyer-p2-mein-plan/`. Smoke-test:
     - Both modes load.
     - Direct-pick: clicking a star toggles favorite (refresh page; star persists).
     - Versus: 5 pairs voted on both axes; refresh page; vote count persists.
     - Export button downloads a JSON file matching the schema; validate via `python3 -c "import json, yaml, jsonschema; jsonschema.Draft202012Validator(yaml.safe_load(open('experiments/_schema/results.schema.yaml'))).validate(json.load(open('Downloads/<file>')))"`.
     - Lightbox opens on image click; Esc closes.
     - Disable localStorage in browser → reload → banner appears.
  6. Document any issues found and fix them before T15.

  This task is partially MANUAL (the smoke test is manual) — but the artifact-existence checks are automated below.
  </action>
  <verify>
  <automated>
  bin/experiment-render falzflyer-p2-mein-plan
  python3 -c "
  import yaml, glob, os
  m = yaml.safe_load(open('experiments/falzflyer-p2-mein-plan/manifest.yml'))
  rendered = set()
  for h in m['hypotheses']:
      slug = h['slug']
      png = f'experiments/falzflyer-p2-mein-plan/variants/{slug}/page-01.png'
      if os.path.exists(png): rendered.add(slug)
  assert len(rendered) >= 8, f'too few rendered: {len(rendered)} of {len(m[\"hypotheses\"])}'
  for slug in rendered:
      assert os.path.exists(f'site/public/experiments/falzflyer-p2-mein-plan/{slug}/page-01.png'), slug
  assert os.path.exists('site/src/content/experiments/falzflyer-p2-mein-plan.md')
  print('rendered:', sorted(rendered))
  "
  npm --prefix site run build
  </automated>
  MANUAL smoke (executor performs and confirms in commit message): both modes load; vote of 5 pairs persists across reload; export downloads schema-valid JSON; lightbox works.
  </verify>
  <done>
  ≥8 of 10+ variants rendered (drops are acceptable iff logged with reason); site builds; manual smoke-test confirmed and noted in the task's commit message.
  </done>
</task>

<task id="T15" type="auto">
  <name>T15: Real run + corpus update (THE acceptance gate)</name>
  <files>
    experiments/falzflyer-p2-mein-plan/results/flo-2026-05-10.json (new — real votes),
    experiments/falzflyer-p2-mein-plan/results/SUMMARY.md (new — generated),
    design-guide/gruene-corpus.md (modify — add top-3 + bottom-3 entries with provenance)
  </files>
  <action>
  This task is mostly MANUAL but the corpus update is the verification gate per CONTEXT.md decision #11.

  1. Flo votes the full session in `/experiments/falzflyer-p2-mein-plan/` (or as many pairs as he wants — he may stop anytime; wins-ratio still works on partial data).
  2. Flo clicks Export → JSON downloads. The executor commits the file as `experiments/falzflyer-p2-mein-plan/results/flo-<YYYY-MM-DD>.json` (filename pattern: ISO date of session).
  3. Run `bin/experiment-results falzflyer-p2-mein-plan`. SUMMARY.md is generated.
  4. Read SUMMARY.md and update `design-guide/gruene-corpus.md`:
     - Add a new subsection (suggested location: after §6, named e.g. `## 6.5 — Experiment results: falzflyer-p2-mein-plan`).
     - For top-3 winners (by appeal, OR by transport — surface BOTH if they differ): add an entry with hypothesis name, axis_commitments, rationale, and a link to `experiments/falzflyer-p2-mein-plan/variants/<slug>/page-01-hires.png`. Tag each entry: `provenance: experiment falzflyer-p2-mein-plan, run flo-<YYYY-MM-DD>, axis: appeal|transport`.
     - Similarly for bottom-3 with the framing "what didn't work and why".
     - If top/bottom rankings disagree across appeal/transport (Spearman <0.5), note it explicitly — disagreement is signal.
     - If the run was inconclusive (e.g., wins-ratio differences <10% across the bag), record THAT as the result with provenance — null results are corpus content per the acceptance gate.
  5. Commit (single commit) the results JSON + SUMMARY.md + corpus update. Commit message: `29: docs(corpus): record top-3/bottom-3 from falzflyer-p2-mein-plan run flo-<YYYY-MM-DD>`.
  6. Tick all 8 acceptance-criteria checkboxes in `ISSUE.md`.
  </action>
  <verify>
  <automated>
  test -f experiments/falzflyer-p2-mein-plan/results/flo-*.json
  python3 -c "
  import json, yaml, jsonschema, glob
  schema = yaml.safe_load(open('experiments/_schema/results.schema.yaml'))
  for p in glob.glob('experiments/falzflyer-p2-mein-plan/results/*.json'):
      jsonschema.Draft202012Validator(schema).validate(json.load(open(p)))
      print('valid:', p)
  "
  test -f experiments/falzflyer-p2-mein-plan/results/SUMMARY.md
  grep -q 'experiment falzflyer-p2-mein-plan' design-guide/gruene-corpus.md
  grep -c 'provenance: experiment falzflyer-p2-mein-plan' design-guide/gruene-corpus.md | awk '$1 >= 6 {exit 0} {exit 1}'
  </automated>
  </verify>
  <done>
  Results JSON validates against schema; SUMMARY.md exists; `design-guide/gruene-corpus.md` contains ≥6 provenance-tagged entries from this run (top-3 + bottom-3); ISSUE.md acceptance criteria all checked. THIS COMPLETES THE ISSUE.
  </done>
</task>

</tasks>

<verification>
After all tasks, run final integration checks:

```bash
# 1. All Python tests
python3 -m unittest discover tools/sla_lib/tests

# 2. Site build
npm --prefix site run build

# 3. Manifest + results validate
python3 -c "
import yaml, json, jsonschema, glob
m_schema = yaml.safe_load(open('experiments/_schema/manifest.schema.yaml'))
r_schema = yaml.safe_load(open('experiments/_schema/results.schema.yaml'))
jsonschema.Draft202012Validator(m_schema).validate(yaml.safe_load(open('experiments/falzflyer-p2-mein-plan/manifest.yml')))
for p in glob.glob('experiments/falzflyer-p2-mein-plan/results/*.json'):
    jsonschema.Draft202012Validator(r_schema).validate(json.load(open(p)))
print('all schemas validate')
"

# 4. Corpus updated
grep -c 'provenance: experiment falzflyer-p2-mein-plan' design-guide/gruene-corpus.md  # expect ≥6

# 5. Production falzflyer rendering unchanged (sanity)
bin/render-gallery kandidat-falzflyer-din-lang
# spot-check templates/kandidat-falzflyer-din-lang/page-01.png matches main
```
</verification>

<success_criteria>
1:1 mapping to ISSUE.md acceptance criteria:

- [x] **AC1: One experiment subject end-to-end (falzflyer P2 "Mein Plan")** — T13 + T14 + T15
- [x] **AC2: 8–12 variations, named hypothesis + one-line rationale per** — T13 (manifest.yml with `name`, `rationale`, `axis_commitments`, `wildcard`)
- [x] **AC3: Each variation rendered as full-page preview (in situ)** — T07 + T14 (`build_variant_front` produces full 2-page Document; only P2 varies)
- [x] **AC4: Static HTML page with both direct-pick and versus modes** — T12
- [x] **AC5: Versus mode randomises left/right + asks both axes separately** — T12 (Fisher-Yates per pair, `position_a_on_screen` randomised, two question rows per pair)
- [x] **AC6: JSON results format with provenance** — T04 schema + T12 export logic + T08 aggregation
- [x] **AC7: Documented workflow** — README/docstring on each tool + T13/T14/T15 lifecycle exercised end-to-end + SUMMARY.md describes the loop
- [x] **AC8: Captured corpus updates from running this MVP at least once with Flo as rater** — T15 (the acceptance gate)
</success_criteria>

<out_of_scope_reminder>
Do NOT implement, even if tempting (per CONTEXT.md "Deferred"):

- Multi-rater real-time merging — MVP merges manually if at all.
- Auto-corpus-update from results — corpus update is manual with rater oversight.
- Generalised any-region generator — MVP is hardcoded to falzflyer P2.
- Hosted/shared deployment — local Astro `dev` / `build` only.
- Adaptive pair sampling (Glicko/Elo).
- Hypothesis prompt-evolution automation — the loop is designed-in (the `_llm-raw/` dir + post-experiment review) but iteration happens after MVP runs.
- Bradley-Terry / Elo ranking — wins-ratio per axis is the MVP. Adding `choix` is forbidden in this issue.
- Image generation via codex/external image models for portrait variations — separate problem; this experiment is layout/typography only.

Keep dependencies at ZERO net new for this issue. Do NOT add `choix`, `rapidfuzz`, `tenacity`, `anthropic`, `openai`, or `google.generativeai` to any requirements file.
</out_of_scope_reminder>
