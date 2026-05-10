# Research Synthesis — Issue #29

Three parallel sub-agents researched codebase / ecosystem / pitfalls. Their full outputs live in `research/codebase.md`, `research/ecosystem.md`, `research/pitfalls.md`. This synthesis is what the planner reads first.

**Overall confidence: HIGH.** Zero new dependencies needed. Existing patterns cover every locked decision in CONTEXT.md.

---

## User Constraints (from CONTEXT.md — locked, verbatim)

1. Per-variant Python file at `experiments/<exp-id>/variants/<hypothesis-slug>.py`. Self-contained, imports shared falzflyer scaffolding so only P2 differs.
2. Voting UI in existing Astro site: `site/src/pages/experiments/index.astro` + `site/src/pages/experiments/[id].astro`.
3. All-pairs randomized-order versus mode. N(N-1)/2 pairs; rater can stop anytime; wins-ratio over completed pairs.
4. Two-axis voting per pair (appeal A + transport T) on same screen, two clicks. Left/right randomized per pair.
5. Variations rendered in situ (full DIN-lang front side P1+P2+P3 with P2 varying), never floating on white.
6. **Pure multi-LLM hypothesis generation, no Flo review at generation stage.** ≥2 independent LLMs; prompt enforces structural distinctness with positive/negative examples; auto dedup with attribution; Flo enters at voting; post-experiment hypothesis review feeds prompt evolution.
7. MVP subject: falzflyer P2 "Mein Plan" panel.
8. ≥10 variations.
9. localStorage during session + explicit JSON export.
10. Results JSON with provenance (rater, timestamps, pair entries with axis, winner, position, computed wins-ratio per axis, ranking per axis, disagreement index).
11. **Mandatory deliverable: at least one experiment run with Flo as rater + corpus updates committed (top-3 + bottom-3 with provenance).**

---

## Summary

**Primary recommendation:** the MVP is almost entirely a composition of existing patterns in this repo. The plan should focus on three additions and four refactors, not on building from scratch.

**Three new files at the system level:**
- `tools/experiment_hypothesis_gen.py` — multi-LLM hypothesis generation (clone of `tools/visual_review.py:209-258`, parameterized for hypothesis prompts and JSON output).
- `tools/experiment_render.py` — variant rendering orchestrator (mirrors `tools/render_pipeline.py` shape, reuses `render_sla_to_pdf` + `rasterise` from `visual_diff.py`).
- `tools/experiment_results.py` — vote-results aggregation and ranking (wins-ratio per axis, disagreement index; no library needed).

**Four refactors of existing code:**
- Factor `_add_front` in `templates/kandidat-falzflyer-din-lang/build.py:329` to accept a `p2_render_fn` callable so variants override only P2.
- Add an `experiments` content collection to `site/src/content.config.ts` (mirroring the templates collection).
- Add `experiments/[id].astro` and `experiments/index.astro` routes (mirroring `templates/[...id].astro` exactly — same dynamic-route + lightbox idiom).
- Extend or clone `tools/gallery_build.py` to mirror experiment artifacts into `site/public/experiments/<id>/` and write `site/src/content/experiments/<id>.md`.

**Most consequential finding:** the workspace already has a multi-LLM orchestration pattern at `tools/visual_review.py:213-258` — subprocess to `codex exec` and `gemini --yolo`, Claude (Opus) inline by the orchestrator agent, with `shutil.which()` guards, 600s timeouts, and per-LLM error tolerance. CONTEXT.md decision 6 says "mirror this." The ecosystem researcher confirms: no Python LLM SDKs needed; the `claude` CLI (2.1.132) at `/root/.local/bin/claude` is already authenticated, no API key management needed in the repo. Three independent generators at hand: this session's Opus (orchestrator), `codex` CLI 0.128.0, `gemini` CLI 0.41.2.

**Highest-priority pitfall:** hypothesis "structural distinctness" is the central failure mode — without designed-in countermeasures the MVP produces a confidence-creating local optimum (the user's named risk). Mitigations must be in the prompt (positive+negative examples, mandatory commitment-axis taxonomy, role priming across LLMs), in the pipeline (post-generation distinctness validation, mandatory wild-card hypothesis), and in the manifest schema (axis tags per hypothesis enabling auto-detection of duplicates).

---

## Codebase Analysis

### DSL builder public API

<interfaces>
// tools/sla_lib/builder/__init__.py:1-9 — canonical public re-exports
from sla_lib.builder import (
    Document, Page,                                    // document.py
    Color, Style, load_ci,                             // ci.py
    TextFrame, ImageFrame, Polygon,                    // primitives.py
    Line, Anchor, Run, pack_inline_image,
    ParaStyle, CharStyle, DocumentLayer, SoftShadow,   // styles.py
    Brand,                                             // brand.py
    blocks,                                            // blocks.py — FoldLine, PageBackground, …
    library,                                           // library.py — load/inject_into_frame
    AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
    GridSpec, GridCell, HierarchyBlock,                // composites.py
    same_y, same_x, same_size, mirrored_x, mirrored_y, // constraints.py
    inside, equal_gap, hierarchy, same_style,
    distance_y, distance_x, aligned_below,
    Constraint, Violation,
    BRAND_CONSTRAINTS, BrandRule,                      // brand_constraints.py
)
</interfaces>

`Document(brand=Brand.gruene_noe(), …)` auto-registers all CI colors, paragraph-styles, char-styles, layers (`document.py:215-244`). Variant scripts can rely on this and just add their own per-variant `ParaStyle` instances via `doc.add_para_style(...)`. Full interface signatures in `research/codebase.md` §1.

### Falzflyer P2 anatomy (the experiment subject)

P2 occupies x=99..198 mm on the FRONT page. Five named PAGEOBJECTs at `templates/kandidat-falzflyer-din-lang/build.py:432-491`:

| anname | type | x,y,w,h (mm) | citation |
|---|---|---|---|
| `P2 Top-Band` | Polygon Dunkelgrün | (99, -3, 99, 31) | build.py:434 |
| `P2 Top-Title` | TextFrame "Mein Plan" | (105, 8, 87, 14) | build.py:436-443 |
| `P2 Teaser-Headline` | TextFrame "Was ich für Mödling will" | (105, 38, 87, 22) | build.py:445-453 |
| `P2 Body-Backing` | Polygon Hellgrün | (99, 28, 99, 185) | build.py:455-467 |
| `P2 Teaser-Body` | 5 Schlagwort paragraphs | (105, 72, 87, 130) | build.py:469-491 |

The five paragraphs ("Klimaplan jetzt." / "Leistbares Wohnen." / "Bildung vor Ort." / "Lokale Wirtschaft." / "Bürgernähe statt Klüngel.") are exactly the corpus §2.1 / §6 / §8.3 "even-spaced peer list" failure mode. P1 and P3 are independent (no anames cross-referenced). P2 has zero entries in `CONSTRAINTS` (build.py:966-1024) except `same_size("P2 Top-Band", …)` coupling Top-Band geometry to P1/P4/P5 — which means a variant that *changes* P2's geometry is structurally legal as long as the Top-Band stays 99×31, OR the constraint is relaxed for variants.

### Recommended factoring (planner work)

Hoist `_add_front` to accept a `p2_render_fn` callable. Per-variant files define a `render_p2(doc, page0)` and call a shared `build_variant_front(p2_render_fn) -> Document` helper. Two viable shapes — both flagged in `research/codebase.md` §13:

1. New module `templates/kandidat-falzflyer-din-lang/variant_scaffold.py` exposing the factory.
2. Refactor `_add_front` in-place; variants import it from `build.py`.

Option 1 is cleaner. Planner's call.

### Render pipeline (reuse, don't reinvent)

<interfaces>
// tools/visual_diff.py — public, reusable
def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None       // line 112
def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path] // line 146

// tools/render_pipeline.py — internal but reusable
def _scrub_pdf_metadata(p: Path) -> None                            // line 75
def _verify_brand_fonts() -> None                                   // line 257 — MUST run, else DejaVu fallback
def _zero_pad_pngs(tdir: Path, prefix: str) -> None                 // line 343
DEFAULT_DPI = 50                                                    // line 41
HIRES_DPI = 150                                                     // line 46
</interfaces>

Pipeline: `python3 build.py` → SLA → `xvfb-run scribus` → PDF → `_scrub_pdf_metadata` (deterministic) → `pdftoppm -r <dpi> -png` → page-NN.png. Falzflyer uses `preview_dpi: 100` from meta.yml:7 for thumbnails. **Variant rendering must run inside the Dockerfile.claude container** — `_verify_brand_fonts()` hard-fails on <5 brand-font fc-list matches.

### Astro routing pattern (mirror exactly)

The dynamic-route + content-collection + lightbox idiom at `site/src/pages/templates/[...id].astro:1-105` is what the experiments routes mirror. Vanilla JS in `<script is:inline>` blocks (lines 55-90) is sufficient for localStorage, DOM events, JSON, click-through, escape-key — no React/Vue/Svelte needed. Existing schema at `site/src/content.config.ts:4-23` is permissive (`z.record(z.any())`). Add new `experiments` collection mirroring this shape.

### Manifest format

Mirror `templates/<x>/meta.yml` idioms (snake_case, list-of-mappings, top-level scalars). Do NOT force `shared/template-spec.schema.yaml` shape — that's for `templates/<x>/spec.yml`, not for experiment metadata. Recommended shape in `research/codebase.md` §5; ecosystem researcher recommends generating `manifest.json` alongside `manifest.yml` so Vite imports JSON natively (no `js-yaml` dep).

### LLM access pattern (CRITICAL)

<interfaces>
// tools/visual_review.py:209-258 — the gold reference

if shutil.which("codex"):
    r = subprocess.run(
        ["codex", "exec",
         "--skip-git-repo-check",
         "--sandbox", "workspace-write",
         "--dangerously-bypass-approvals-and-sandbox",
         "-i", str(detail), "-i", str(grid),    // optional image inputs
         prompt],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
    )

if shutil.which("gemini"):
    r = subprocess.run(
        ["gemini", "--yolo", "-p", f"{prompt}\n\n…"],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
    )

// Claude (Opus) — inline by the orchestrator agent (visual_review.py:252-254 comment).
// For experiment hypothesis generation, that's THIS session's agent runner.
</interfaces>

Failure tolerance pattern: `except Exception as e: sections.append(f"<LLM> error: {e}")` — keep going with the LLMs that did respond. The pipeline runs as long as ≥1 LLM succeeds.

**For Anthropic-only hypothesis generation in subprocess form**, use `claude --print --output-format json -p "<prompt>"` — the `claude` CLI 2.1.132 at `/root/.local/bin/claude` is already authenticated. This is the recommended path for non-orchestrator-inline Claude calls — avoids introducing API key management.

---

## Standard Stack (Verified)

| Tool / Library | Version | Already installed? | Purpose |
|---|---|---|---|
| Astro | `^5.0.0` (5.18.1) | yes (`site/package.json`) | Static site framework |
| PyYAML | 6.0.3 | yes (Dockerfile.claude) | manifest.yml load — `safe_load` only |
| jsonschema | 4.26.0 | yes (Dockerfile.claude:80) | Manifest validation, Draft 2020-12 |
| Pillow | 12.2.0 | yes (Dockerfile.claude:79) | Image post-processing if needed |
| `codex` CLI | 0.128.0 | yes (PATH) | Hypothesis generation — second LLM (GPT-5.x backed) |
| `gemini` CLI | 0.41.2 | yes (PATH) | Hypothesis generation — third LLM |
| `claude` CLI | 2.1.132 | yes (`/root/.local/bin/claude`) | Anthropic LLM access without API keys |
| Scribus 1.6.x + `pdftoppm` | system | yes | Variant rendering pipeline |
| ImageMagick | system | yes | Optional grid composites |

**Net new dependencies for MVP: ZERO.**

---

## Don't Hand-Roll

| Problem | Use instead | Why |
|---|---|---|
| YAML parsing | `yaml.safe_load` | repo pattern; never `yaml.load` without Loader |
| Manifest schema validation | `jsonschema` Draft 2020-12, mirror `shared/template-spec.schema.yaml` | repo pattern; precise JSON Pointer errors |
| Multi-LLM orchestration | `subprocess.run` against `codex` / `gemini` / `claude` CLIs | mirror `tools/visual_review.py`; no key mgmt |
| Browser file download | `Blob` + `URL.createObjectURL` + temporary `<a download>` + `URL.revokeObjectURL` | standard pattern, no library |
| Random pair shuffle | Fisher-Yates on a copy of pairs | naive `sort(() => Math.random() - 0.5)` is biased |
| Wins-ratio | `Map<variantId, {wins, plays}>` accumulator, sort `wins/plays` desc | trivial; Bradley-Terry deferred per CONTEXT discretion |
| Variant rendering | Reuse `render_sla_to_pdf`, `rasterise`, `_verify_brand_fonts`, `_scrub_pdf_metadata` | existing pipeline is deterministic by design |
| `bin/experiment-*` script shape | 14-line shim mirroring `bin/render-gallery:1-14` | existing convention |
| Dedup of ~24 hypotheses | `difflib.SequenceMatcher` ratio ≥ 0.75 + slug equality | stdlib; RapidFuzz / embeddings overkill at this scale |

**Deferred (phase 2, do NOT add now):** `choix` (Bradley-Terry), Anthropic/OpenAI/Google Python SDKs, `tenacity`, `rapidfuzz`.

---

## Architecture Patterns

### Variant authoring

- One Python file per variant under `experiments/<exp-id>/variants/<slug>.py`.
- Each variant: `def render_p2(doc: Document, page: Page) -> None`, then a thin entry point that calls a shared factory `build_variant_front(p2_render_fn) -> Document`.
- Variant adds its own `ParaStyle`s before adding TextFrames, namespaced like `exp-<slug>/<style-name>` to avoid collisions.
- Variant anames keep the `P2 ` prefix (e.g., `"P2 (yellow-accent) — top item"`) so audit_alignment / spec_check don't false-positive.

### Manifest / experiment lifecycle

```
experiments/<exp-id>/
├── manifest.yml              # human-edited or LLM-generated; validated via jsonschema
├── manifest.json             # auto-generated by experiment_render for Astro/Vite import
├── variants/
│   ├── <slug-1>.py
│   ├── <slug-1>/             # rendered artifacts: page-01.png, page-01-hires.png, template.sla
│   └── …
├── results/
│   └── flo-2026-05-10.json   # rater-named exports; multi-rater merge is phase 2
└── _llm-raw/                 # raw LLM outputs preserved for audit / post-experiment review
```

Lifecycle:
1. `bin/experiment-generate <exp-id> --subject falzflyer-p2-mein-plan` → calls 2+ LLMs, dedupes, writes `manifest.yml` + `_llm-raw/`.
2. (Optional) Flo edits `manifest.yml` to prune.
3. `bin/experiment-render <exp-id>` → for each variant: build SLA, render PDF + PNGs at preview_dpi=100 + hires_dpi=150, mirror artifacts to `site/public/experiments/<exp-id>/<slug>/`, generate `manifest.json`, write `site/src/content/experiments/<exp-id>.md`.
4. `npm run build` (or `dev`) → Astro reads experiments collection, generates voting page.
5. Flo votes → localStorage persists state → "Export results" downloads `flo-<date>.json`.
6. `bin/experiment-results <exp-id> <results.json>` → computes wins-ratio per axis, disagreement index, ranking; emits a markdown summary.
7. Manual: amend `design-guide/gruene-corpus.md` with top-3 + bottom-3 + provenance. Commit results JSON + corpus update together.

### Voting UI

- Two routes: `experiments/index.astro` (list of experiments) and `experiments/[id].astro` (single experiment).
- Two modes on the same page: **direct pick** (all variants in a grid, click favorites) and **versus** (Fisher-Yates-shuffled all-pairs sequence, two-axis voting per pair).
- Vanilla JS in `<script>` tags inside the `.astro` file (mirroring lightbox at `templates/[...id].astro:55-90`).
- localStorage key: `experiment:<exp-id>:session:v1` — single-key write per vote.
- Export button: Blob + `URL.createObjectURL` + temporary `<a download="<rater>-<timestamp>.json">` + revoke.
- Progress bar: `X / 45 pairs voted` per axis. Skip button per pair. Big clickable cards (image is the click target). Keyboard shortcuts: `Q`/`W` for axis-A left/right, `O`/`P` for axis-T left/right (or `←`/`→` with `Tab` to switch axis — pick one, document it).

### Hypothesis generation prompt

The prompt MUST contain (per pitfalls research §2):
- Concrete positive AND negative examples ("BAD: change spacing 8mm → 12mm; GOOD: cut 5 items → 3 items + body").
- Mandatory **commitment-axis taxonomy** — each hypothesis must declare which design axes it commits on (density / hierarchy / typography / asymmetry / photographic-vs-typographic / accent-strategy / ...).
- Role priming per LLM (Opus = "typography-first designer"; Codex = "hierarchy-first designer"; Gemini = "asymmetry-first designer") to push divergent modes.
- Required fields per hypothesis: `slug`, `name`, `axis_commitments`, `rationale`, `expected_outcome`, `wildcard: bool` (at least one variant must be `wildcard: true`).
- Strict JSON output schema; tolerant parser strips Markdown fences and extracts first `{` to last `}`.

---

## Common Pitfalls (Top 5)

1. **Hypothesis "structural distinctness" is the central failure mode.** Without designed-in countermeasures (positive+negative examples, commitment-axis taxonomy, multi-LLM with role priming, post-generation distinctness validation, mandatory wild-card hypothesis), 10 variations collapse to 3 hypothesis families × parameter tweaks → confidence-creating local optimum → system worse than nothing. Verify before voting.

2. **`inside_page` and structural-check gates apply to variants.** Archived issue #16 showed frame-overflow bugs render silently. Each variant must pass `inside_page` + `audit_alignment` + `spec_check` before entering the bag. Failed variants are dropped with a clear log message — they don't get to vote. Recommendation from codebase research: variants are research artifacts; *don't* run `BRAND_CONSTRAINTS` (some hypotheses deliberately violate brand rules — that's a feature). Planner's call to confirm policy.

3. **localStorage is fragile.** Private/incognito wipes on close; Safari ITP evicts after 7 days; users clear data. Vote payload is small (~12 KB / 50 votes) so quota is non-issue. Mitigation: detect non-persistent storage on load, show non-dismissable banner if absent, surface "Export progress" button prominently (not buried). The JSON file is the durable record; localStorage is convenience only.

4. **Two-axis disagreement is the signal — never compute composite ranking.** Two separate rankings (`ranking_appeal`, `ranking_transport`) plus disagreement index per pair. Per-variant axis dispersion (rank on A vs rank on T) is preserved. Halo effect exists and is real — *measure* it via Spearman correlation between A-rank and T-rank (>0.85 = halo flag, <0.5 = working as intended), don't try to eliminate it. Auto-resolution would erase the corpus-update content the system was built to surface.

5. **Corpus-update deliverable is the verification gate.** PR not mergeable until `design-guide/gruene-corpus.md` has top-3 + bottom-3 entries with provenance and the results JSON is committed. Done-checklist on the issue: (a) tooling tests pass, (b) one experiment ran end-to-end, (c) corpus updated with provenance, (d) results JSON committed.

Full pitfall list with confidence ratings in `research/pitfalls.md`.

---

## Open Uncertainties (planner resolves)

1. **Variant SLA scope:** full 2-page Document with only page-01 rasterized, OR new `build_variant_front_only(...)` 1-page entrypoint? Recommendation: keep 2-page (cheap, reuses everything), only output page-01.png. Verify Scribus renders correctly. (codebase §13.1)

2. **Where to factor the hoist:** new `templates/kandidat-falzflyer-din-lang/variant_scaffold.py` vs. in-place refactor of `_add_front`. Recommendation: new module. (codebase §13.2)

3. **Astro: content collection vs filesystem-direct.** Recommendation: content collection (codebase-native; mirrors templates pattern). (codebase §13.3)

4. **Brand-rule enforcement on variants.** Recommendation: variants are research artifacts; don't run `BRAND_CONSTRAINTS` per-variant; do run `inside_page` and structural alignment. (codebase §13.4 + pitfalls §4.1)

5. **`bin/experiment-render` runs `_verify_brand_fonts`.** Recommendation: yes — without it, variants render with DejaVu fallback and votes are invalidated. (codebase §13.5)

6. **LLM mix for hypothesis generation.** Recommendation: orchestrator-inline Opus (this session) + `codex` CLI + optionally `gemini` CLI. Multi-LLM is quality not correctness — pipeline runs if ≥1 succeeds. (codebase §13.6 + pitfalls §7.5)

7. **Per-axis keyboard shortcut scheme** (Q/W + O/P vs ←/→/Tab). Pick one, document it.

---

## Environment Audit

Verified locally on 2026-05-10:

| Tool | Version | Status |
|---|---|---|
| python3 | 3.13.5 | OK (no `python` symlink — use `python3` explicitly) |
| node | v26.0.0 | OK |
| npm | 11.12.1 | OK |
| Astro | 5.18.1 (site/node_modules) | OK |
| Scribus | system, requires `xvfb-run` | OK |
| `pdftoppm` (poppler) | system | OK |
| `codex` CLI | 0.128.0 | OK on PATH |
| `gemini` CLI | 0.41.2 | OK on PATH |
| `claude` CLI | 2.1.132 | OK at /root/.local/bin/claude |
| `gh` | 2.92.0 | OK |
| `issue-cli` | present | OK |
| Brand fonts (fc-list) | 42 face entries | OK — Gotham Narrow + Vollkorn full set at /usr/local/share/fonts/gruene/ |
| `anthropic` / `openai` / `google.generativeai` Python SDKs | not installed | not needed (CLI subprocess pattern) |
| ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY | unset | not needed (CLI auth handles it) |
| `.env` files | none | not needed |
| `experiments/` directory | does not exist | greenfield |
| `site/src/content/experiments/` | does not exist | greenfield |
| `site/src/pages/experiments/` | does not exist | greenfield |

**No blockers.** Everything required by CONTEXT.md decisions is present.

---

## Project Constraints

- **No `CLAUDE.md` at workspace root.** No project-level Claude directives beyond CONTEXT.md and `README.md`. (codebase §0)
- Build flow: `python3 templates/<id>/build.py` → SLA → `xvfb-run scribus tools/_export_pdf.py` → PDF, OR `bin/render-gallery` for the full pipeline. (`README.md:163-180`)
- Brand fonts NOT in repo — render hard-fails without them, gate at `tools/render_pipeline.py:257-278`. Variant rendering must run in Dockerfile.claude container.
- DPI conventions: local 150 dpi, CI 96 dpi for `visual_diff`. Falzflyer thumbnail 100 dpi (meta.yml:7), hires 150 dpi.
- Anname strings are case-sensitive identifiers with em-dash literal U+2014. Variants targeting P2 keep the `P2 ` prefix in their anames.
- German file/key naming preferred for brand-touching artifacts; variant slugs / hypothesis IDs can stay English (existing convention).

---

## Sources

### HIGH confidence (verified by direct inspection)

- `templates/kandidat-falzflyer-din-lang/build.py:432-505` (P2 anatomy)
- `tools/visual_review.py:209-258` (multi-LLM orchestration pattern — gold reference)
- `tools/visual_diff.py:112-150` (`render_sla_to_pdf`, `rasterise`)
- `tools/render_pipeline.py:75-343` (PDF metadata scrub, brand-font verification, zero-pad helpers)
- `tools/sla_lib/builder/__init__.py:1-9` (DSL public API)
- `site/src/pages/templates/[...id].astro:1-105` (Astro routing + lightbox pattern)
- `site/src/content.config.ts:4-23` (content-collection schema)
- `tools/gallery_build.py:1-136` (preview mirror pipeline)
- `bin/render-gallery:1-14` (shim pattern)
- `shared/template-spec.schema.yaml` (jsonschema-in-YAML pattern)
- `Dockerfile.claude` (pinned dependency versions)
- Local environment audit (commands run 2026-05-10)
- `design-guide/gruene-corpus.md` §6 / §2.1 / §8 (failure mode named)

### HIGH confidence (verified external)

- [Astro docs: Scripts and event handling](https://docs.astro.build/en/guides/client-side-scripts/)
- [Astro 5.0 announcement](https://astro.build/blog/astro-5/)
- [MDN: Storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)
- [WebKit ITP — Updates to Storage Policy](https://webkit.org/blog/14403/updates-to-storage-policy/)
- [Anthropic Claude API model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)
- [PyYAML deprecation wiki — `yaml.load`](https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation)
- [`choix` on PyPI 0.4.1](https://pypi.org/project/choix/) (deferred)

### MEDIUM confidence (research-grade, judgment-based mitigations)

- LLM-judge position bias: [arXiv 2406.07791v5](https://arxiv.org/html/2406.07791v5), [IJCNLP 2025](https://aclanthology.org/2025.ijcnlp-long.18.pdf)
- Halo effect on simultaneous multi-criterion rating: [Jeon & Lee, *Language Testing in Asia* 2020](https://link.springer.com/article/10.1186/s40468-020-00115-0), [PMC 11614318 (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11614318/)
- LLM mode collapse: [arXiv 2505.18949](https://arxiv.org/html/2505.18949v1) (Diversity Collapse), [arXiv 2510.01171](https://arxiv.org/html/2510.01171v1) (Verbalized Sampling)
- AllOurIdeas pairwise UX patterns: [github.com/allourideas](https://github.com/allourideas)
- Pairwise comparison fatigue threshold (~30-50 pairs): convention, not measured here

### LOW confidence

- Astro 5.18.1 hot-reload missing content-collection changes (anecdotal)
- Specific magnitude of human position bias (5-10 percentage points) — order-of-magnitude only
- Pairwise fatigue inflection point — convention, not measured for our specific setup
