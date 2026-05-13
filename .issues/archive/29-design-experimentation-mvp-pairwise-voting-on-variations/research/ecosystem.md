# Ecosystem Research — Issue #29 (Design Experimentation MVP)

**Researched:** 2026-05-10
**Researcher:** ECOSYSTEM specialist
**Scope:** Standard libraries, patterns, and best practices verified against current sources for the pairwise-voting MVP described in ISSUE.md and locked by CONTEXT.md.

---

## TL;DR — Standard Stack (Verified Versions)

| Library / Tool | Version | Purpose | Why Standard | Source |
|----------------|---------|---------|--------------|--------|
| Astro | `^5.0.0` (already installed) | Static site framework hosting voting UI | Already in `site/package.json`; no upgrade needed for MVP | [`site/package.json`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/site/package.json) — verified locally |
| Vanilla JS via `<script>` in `.astro` | n/a | Voting UI interactivity (no framework) | Existing pattern at [`site/src/pages/templates/[...id].astro`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/site/src/pages/templates/[...id].astro) (lightbox lines 41+); zero deps; matches CONTEXT decision 12 ("vanilla JS + Astro client island is sufficient — no Svelte/React needed for MVP") | [Astro: Scripts and event handling](https://docs.astro.build/en/guides/client-side-scripts/) |
| PyYAML | `6.0.3` (already installed via `python3-yaml` from Debian trixie + already used repo-wide) | Manifest load (`manifest.yml`) | Locked into Dockerfile.claude; already used by `tools/codex_image_gen.py`, `tools/check_ci.py`, `tools/qr_gen.py`. Use `yaml.safe_load` only. | [PyYAML 6.0 docs](https://pyyaml.org/wiki/PyYAMLDocumentation), local `pip3 list` |
| jsonschema | `4.26.0` (already installed) | Manifest schema validation | Already pinned in `Dockerfile.claude` for `shared/sample-images/manifest.yml` validation. Reuse for `experiments/<id>/manifest.yml`. | [`Dockerfile.claude:80`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/Dockerfile.claude) |
| Pillow | `12.2.0` (already installed) | Image post-processing if needed | Already pinned in Dockerfile for byte-deterministic output. | `Dockerfile.claude:79` |
| ImageMagick (`montage`, `convert`) | system | Optional grid composites for direct-pick mode | Already used by `tools/visual_review.py` and `tools/visual_diff.py`. Not strictly needed if direct-pick uses CSS grid in browser. | `Dockerfile.claude:57` |
| Scribus 1.6.x + `pdftoppm` | system | Variant rendering pipeline | Existing pipeline. **No alternative needed** for MVP; falzflyer P2 already builds via `templates/kandidat-falzflyer-din-lang/build.py:432–505`. | `Dockerfile.claude:48-55` |
| `codex` CLI | `0.128.0` | Hypothesis generation — second LLM (OpenAI/GPT-5.x backed) | Already on PATH; existing pattern in `tools/visual_review.py:213` invokes via `subprocess`. Avoids managing OPENAI_API_KEY directly. | local probe; `tools/visual_review.py` |
| `gemini` CLI | `0.41.2` | Hypothesis generation — third LLM | Already on PATH; existing pattern in `tools/visual_review.py:240`. | local probe; `tools/visual_review.py` |
| `claude` CLI | `2.1.132` (Claude Code) | Inline LLM access — orchestrator (Opus) | Inline by the orchestrator agent rather than subprocess in the existing `tools/visual_review.py:252-254`. | local probe |

**No new Python dependencies are required for the MVP.** The repo's existing toolchain (PyYAML + jsonschema + Pillow + subprocess to CLIs) covers every locked decision in CONTEXT.md.

---

## Don't Hand-Roll (Library Required)

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing of `manifest.yml` | Custom parser | `yaml.safe_load` (PyYAML 6.0.3) | Existing repo pattern; safe by default; never `yaml.load(...)` without `Loader=`. |
| Schema validation of `manifest.yml` | Ad-hoc dict checks | `jsonschema` 4.26.0 with a `experiments/_schema/manifest.schema.yaml` (Draft 2020-12), mirroring [`shared/template-spec.schema.yaml`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/shared/template-spec.schema.yaml) | Existing repo pattern; failures get a precise JSON Pointer location. |
| Multi-LLM orchestration | New SDK code | `subprocess.run` against `codex` and `gemini` CLIs (Claude Opus inline by the orchestrator agent) | **Mirror `tools/visual_review.py` exactly** — that's the workspace's existing pattern (CONTEXT.md decision 6). No new SDK auth / token mgmt. |
| File download from browser | Mailto / form post | `Blob` + `URL.createObjectURL` + temporary `<a download>` click + `URL.revokeObjectURL` | Standard pattern, no library needed; works without server. |
| Random pair sequencing | `Math.random()` shuffle in place | Fisher-Yates shuffle (10 lines) seeded from `crypto.getRandomValues` | Naive `sort(() => Math.random() - 0.5)` is biased — a *specific* known pitfall (see Pitfalls research). |
| Wins-ratio ranking on partial pairs | "Roll your own with for-loops" | Plain `Map<variantId, {wins, plays}>` accumulator, `wins/plays` for each axis, sort descending, ties broken by total plays | Wins-ratio is trivial; Bradley-Terry is **deferred** per CONTEXT.md discretion §1. |
| Optional Bradley-Terry (phase 2) | Custom MM/Newton iterator | `choix` 0.4.1 — `choix.ilsr_pairwise(n_items, data)` or `choix.mm_pairwise(...)` | If we ever bring BT forward, `choix` is the standard pip-installable library. |

---

## 1. Pairwise Voting / Ranking Algorithms

### Wins-ratio (the MVP default — locked)

**Known weakness for ~10 items × 45 pairs from one rater:** wins-ratio gives equal weight to every match, so a variant that lost only to the eventual #1 looks the same as one that lost to the eventual #10. With dense N=10 / 45-pair tournaments and a single rater, this is acceptable: every variant plays every other, the systematic bias from "easy schedule" disappears. The remaining issue is **transitivity violations** (A>B, B>C, C>A), where wins-ratio still produces *some* total order but doesn't expose the cycle. For MVP this is fine; surface the pair-level data in the JSON export so downstream analysis can detect cycles.

Confidence: **HIGH** (basic combinatorics; no source needed).

### Bradley-Terry MLE — deferred but ready

`choix` 0.4.1 (Aug 2025, MIT, Python ≥3.10) is the standard Python implementation. Key API: `choix.ilsr_pairwise(n_items, data)` (Iterative Luce Spectral Ranking — typically converges in 5–20 iterations for sparse comparison data) or `choix.mm_pairwise(n_items, data)` (Minorization-Maximization). Both return a vector of "strengths" (log-domain skill parameters); the ranking is `argsort(-strengths)`. With 45 pairs from one rater on 10 variants, MLE *will* converge but the strength estimates have wide CIs — wins-ratio is roughly as informative for a single rater. BT pays off only when (a) we have multiple raters, (b) some pairs are missing, or (c) we want proper uncertainty bounds.

**Recommendation:** keep `choix` out of MVP requirements. If/when phase 2 lands multi-rater merging, add `choix==0.4.1` as a dependency.

Confidence: **HIGH** (verified on PyPI + project docs).

### Elo / Glicko

Elo is a streaming/online wins-ratio analog with K-factor; not relevant for MVP because we present every pair already (no need to schedule "who plays who"). Glicko adds a rating-deviation parameter for time decay — overkill for a single-session experiment. **Skip both.** Wins-ratio per axis is the right MVP choice.

Confidence: **HIGH**.

### Open-source pairwise voting prior art

- **AllOurIdeas** ([`github.com/allourideas/allourideas.org`](https://github.com/allourideas/allourideas.org)) — the canonical academic open-source pairwise wikisurvey tool (Salganik et al., Princeton). Status: maintenance ended several years ago. UX patterns worth borrowing: explicit "I can't decide" / skip button (we should consider this), large clickable cards (not radio buttons), keyboard shortcuts (←/→ to vote, Space to skip).
- **Pairwise.vote** ([`pairwise.vote`](https://www.pairwise.vote/)) — modern commercial alternative using BudgetBox aggregation. Not open source; UX reference only.
- **OpinionX** ([Pairwise comparison guide](https://www.opinionx.co/blog/pairwise-comparison)) — useful taxonomy of pairwise comparison methods (good background reading; nothing to copy).

**Recommendation:** copy AllOurIdeas's "skip" affordance and keyboard navigation, but don't import any code (Ruby, abandoned).

Confidence: **MEDIUM** (sources verified; "patterns worth borrowing" is a design judgement).

---

## 2. Astro 5 Client Islands and Interactive UI Patterns

### Verification of Astro version

`site/package.json` declares `"astro": "^5.0.0"` (verified locally). Astro 5 stable shipped December 2024; Astro 6 beta released January 2026 ([Astro 5.0 announcement](https://astro.build/blog/astro-5/), [DEV: Astro in 2026](https://dev.to/polliog/astro-in-2026-why-its-beating-nextjs-for-content-sites-and-what-cloudflares-acquisition-means-6kl)). **No upgrade needed** for MVP — Astro 5 is plenty.

### Vanilla JS vs. framework components

**Recommendation: vanilla JS in `<script>` tags inside `.astro` files.** No React/Vue/Svelte. Justification:
- Existing pattern at `site/src/pages/templates/[...id].astro` (the lightbox added in #28) does exactly this — sets data attributes on anchors, attaches click handlers in a `<script>` tag.
- CONTEXT.md decision 12 explicitly endorses vanilla JS for MVP.
- Astro docs confirm: "for vanilla JavaScript specifically, elements rendered by a UI framework may not be available yet when a `<script>` tag executes." We aren't rendering with frameworks, so this caveat doesn't apply ([Astro client-side scripts](https://docs.astro.build/en/guides/client-side-scripts/)).

**Pattern to use:**
```astro
---
// frontmatter: data fetched at build time
import manifestData from '../../experiments/falzflyer-p2-mein-plan/manifest.yml';
---
<div id="versus-mode" data-pairs={JSON.stringify(pairs)}>...</div>
<script>
  // module-scoped; bundled by Vite; runs once per page
  const root = document.getElementById('versus-mode')!;
  const pairs = JSON.parse(root.dataset.pairs!);
  // ...
</script>
```

### State management

| Option | Use For | Verdict |
|--------|---------|---------|
| `localStorage` | Vote progress, rater identity, last-shown pair | **PRIMARY** (CONTEXT.md decision 9) |
| In-memory module state | Current session pair index, position-randomization seed | Yes (transient) |
| `IndexedDB` | n/a for MVP | Skip — overkill for ~50 vote records (~5 KB JSON) |
| `sessionStorage` | n/a | Skip — we explicitly *want* refresh-survival |

### Per-page client scripts vs. `client:load` components

- **Per-page `<script>` in `.astro`**: ✅ use this. Bundled by Astro, hoisted to `<head>` by default, scoped to the page.
- **`client:load`/`client:visible` directives**: ❌ unnecessary — those are for hydrating *framework components* (React/Vue/Svelte). We have none.

### Loading the manifest

**At build time** (recommended): import the YAML as a module via Astro's frontmatter and a YAML loader (or read it via Node's `fs` at build):
```astro
---
import { readFileSync } from 'node:fs';
import yaml from 'js-yaml';  // would need adding — OR write a small helper
const manifest = yaml.load(readFileSync('experiments/.../manifest.yml', 'utf-8'));
---
```
**Cleaner alternative:** generate `experiments/<id>/manifest.json` as part of the experiment-build pipeline (`tools/experiment_render.py`), then import the JSON directly with `import manifest from '.../manifest.json'`. **Recommended** — JSON imports work natively in Vite/Astro, no `js-yaml` dep, and the build pipeline already runs Python so YAML→JSON is one line.

Confidence: **HIGH** (existing pattern + verified Astro docs).

---

## 3. localStorage and Browser Persistence

### Quotas and edge cases

- **Quota:** 5 MiB per origin in all major browsers (verified [MDN: Storage quotas](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)). For ~50 votes × ~200 bytes = **10 KB** — quota is non-issue.
- **Private/incognito:** localStorage works but is wiped on tab close. Acceptable; rater can still export to JSON before closing.
- **Safari ITP eviction:** "If an origin has no user interaction (click or tap) in the last seven days, its data created from script will be deleted" ([WebKit: Updates to Storage Policy](https://webkit.org/blog/14403/updates-to-storage-policy/)). For our use case (rater clicks through pairs in a single session, then explicitly exports), this is harmless — they will have interacted. Document it: "Don't leave votes unexported for >7 days on Safari."
- **`QuotaExceededError`:** wrap writes in try/catch and show a "please export now" warning. Trivial.

### Pattern: auto-save state, explicit export to file

Recommended structure:
1. On every vote: write the *full* session state object to `localStorage` under one key (e.g. `experiment:falzflyer-p2-mein-plan:session:v1`) — single-key write avoids partial-update races.
2. On page load: read that key, hydrate UI state, resume where the rater left off.
3. "Export results" button: stringify the same object → `Blob([json], { type: 'application/json' })` → `URL.createObjectURL(blob)` → temporary `<a download="rater-name-timestamp.json" href={url}>` click → `URL.revokeObjectURL(url)`.

Confidence: **HIGH** ([MDN: Storage quotas](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria), [WebKit policy](https://webkit.org/blog/14403/updates-to-storage-policy/), [DEV: localStorage best practices](https://dev.to/tene/localstorage-vs-indexeddb-javascript-guide-storage-limits-best-practices-fl5)).

### File API export — pitfalls

- **Always `URL.revokeObjectURL` after the click** — otherwise blob URLs leak memory until tab close.
- **Some browsers ignore `download` attribute** for cross-origin anchors. Use a same-origin blob URL — that just works.
- **Filename sanitisation:** rater identity goes in the filename. Strip `/`, `\`, `:`, `?`, `*`, `<`, `>`, `|` and trim to ~80 chars. Naive concatenation produces unsavable filenames on Windows shares.
- **JSON size:** at ~10 KB no compression needed; avoid `gzip` complexity.

Confidence: **HIGH**.

---

## 4. Multi-LLM Coordination for Hypothesis Generation

### Existing workspace pattern (CRITICAL — read first)

`tools/visual_review.py` is the workspace's reference multi-LLM orchestrator:

| Aspect | What it does | What we copy |
|--------|--------------|--------------|
| Codex (GPT) | `subprocess.run(["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", "--dangerously-bypass-approvals-and-sandbox", "-i", img1, "-i", img2, prompt])` (visual_review.py:213-225) | Same call shape (drop `-i` if no images). Capture stdout, save to file. |
| Gemini | `subprocess.run(["gemini", "--yolo", "-p", prompt])` (visual_review.py:240-244) | Same. Note `--yolo` flag is the existing convention here. |
| Claude (Opus) | "handled inline by the orchestrator agent" — the comment at visual_review.py:252-254 explicitly punts to the agent runner | For hypothesis generation, this means the `issue:work` orchestrator agent (which runs Opus 4.7) generates one hypothesis set as part of the prep phase; the subprocess CLIs generate the others. |
| Timeout | 600 s per call | Match — hypothesis generation is short prose, but match for consistency. |
| Failure handling | `except Exception as e: sections.append(f"Codex error: {e}\n\n")` — keep going with the LLMs that did respond | **CRITICAL**: same pattern. If Gemini is down, Opus + Codex still produces a valid hypothesis pool. |

**Recommendation:** the new `tools/experiment_hypothesis_gen.py` should be a near-clone of `visual_review.py`'s LLM-dispatch logic, but parameterized for "generate ≥12 hypotheses for subject X" prompts and JSON-output (not Markdown) parsing.

### Verified model IDs (May 2026)

| Provider | Model | ID | Source |
|----------|-------|-----|--------|
| Anthropic | Opus 4.7 | `claude-opus-4-7` (or pinned snapshot e.g. `claude-opus-4-7-20260416`) | [Claude API model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions); environment context confirms Opus 4.7 |
| Anthropic | Sonnet 4.6 | `claude-sonnet-4-6` | Same |
| Anthropic | Haiku 4.5 | `claude-haiku-4-5` | Same |
| OpenAI | GPT-5.5 (latest) | `gpt-5.5` (or `gpt-5.5-2026-04-23` snapshot) | [OpenAI: Using GPT-5.5](https://developers.openai.com/api/docs/guides/latest-model) |
| OpenAI | GPT-5.4 | `gpt-5.4` | [GPT-5.4 model card](https://developers.openai.com/api/docs/models/gpt-5.4) |
| Google | Gemini (latest) | invoked via `gemini` CLI's default — no model ID needed in our subprocess pattern | local CLI 0.41.2 |

**Note:** since CONTEXT.md decision 6 mandates "≥2 independent generators", the practical mix is **Opus (inline) + Codex CLI (GPT-5.x backed)**, with optional Gemini as a third. The model IDs above only matter if we ever switch to direct Python SDK calls. The CLI subprocess pattern hides them.

### Python SDK details (only if we move off CLIs in phase 2)

- **anthropic** Python SDK 0.100.0 (May 6, 2026 — [PyPI](https://pypi.org/project/anthropic/)). Has `AsyncAnthropic` for async, native `max_retries` (default 2, exponential backoff), retries 408/409/429/5xx automatically ([SDK docs](https://platform.claude.com/docs/en/api/sdks/python), [DeepWiki](https://deepwiki.com/anthropics/anthropic-sdk-python/4.2-synchronous-and-asynchronous-clients)).
- **openai** Python SDK supports Pydantic models for structured outputs ([OpenAI structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)).
- **Tenacity** is *not* needed when using SDKs — they retry natively. It would be needed only if we wrote raw `httpx` calls.

**Don't add these to MVP requirements.** The CLI subprocess pattern is the existing repo style; stay there.

### Output structuring for hypothesis lists

**Recommendation:** the hypothesis-generation prompt should ask each LLM for **strict JSON** in a fixed schema:

```json
{
  "hypotheses": [
    {
      "slug": "privilege-one-item-via-yellow-accent",
      "name": "Privilege one item via yellow accent",
      "rationale": "One sentence on what this tests and why.",
      "anatomy": "What changes structurally vs. baseline (typography, spacing, balance, content count)."
    }
  ]
}
```
Then `json.loads(stdout.strip())` after the subprocess call. If the LLM wraps it in `\`\`\`json ... \`\`\`` fences, strip those. This is the same pattern `tools/visual_review.py:166-181` uses (its prompt asks for "Strict JSON" in code fences).

### Cost / token budget

Rough estimate: 12 hypotheses × ~200 tokens each + ~1500-token prompt = **~4 K output tokens × 2 models = ~8 K tokens total** for one experiment's hypothesis-generation phase. At Opus 4.7 + GPT-5.5 prices, well under $1/experiment. **No budget concerns.**

Confidence: **HIGH** (verified patterns + verified models + simple math).

---

## 5. Hypothesis Dedup / Merging

For ~24 raw hypotheses (12 from each of 2 LLMs):

**Recommendation: minimal slug-based dedup + manual inspection in the manifest, no embeddings.**

1. Each LLM produces a kebab-case slug per hypothesis (the prompt enforces this — see §4).
2. Normalize slugs (`re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`).
3. Group by exact-match slug — collapse and tag with both source LLMs (a confidence signal per CONTEXT.md decision 6).
4. For "near-miss" overlaps (e.g., `cut-to-three-items` vs `reduce-to-three-with-body`), use a **string similarity threshold via `difflib.SequenceMatcher` ratio ≥ 0.75**. Surface candidates as warnings; let the orchestrator agent (Opus) merge them in the manifest write-out step.

**Why not RapidFuzz or embeddings:**
- 24 hypotheses × pairwise = 276 comparisons. `difflib` does this in <10 ms. RapidFuzz is overkill ([DEV: RapidFuzz vs difflib](https://dev.to/mrquite/smart-text-matching-rapidfuzz-vs-difflib-ge5)) — fast for >>10K records, no advantage at this scale.
- Embedding-based dedup (sentence-transformers, OpenAI embeddings) requires *another* dependency / API call for ~24 short strings. Diminishing returns.

`difflib` is in the Python stdlib — **zero new dependencies.**

Confidence: **HIGH**.

---

## 6. YAML / Manifest Schema Validation

### Existing repo pattern (REUSE)

`shared/template-spec.schema.yaml` is the canonical example: JSON Schema (Draft 2020-12) authored *in YAML* (so human-editable), validated via:

```python
import yaml, jsonschema, pathlib
schema = yaml.safe_load(pathlib.Path('shared/template-spec.schema.yaml').read_text())
spec   = yaml.safe_load(pathlib.Path('templates/X/spec.yml').read_text())
jsonschema.validate(spec, schema)
```

(Comment block at `shared/template-spec.schema.yaml:1-12`.)

**Recommendation: mirror this exactly for `experiments/<id>/manifest.yml`.** Author `experiments/_schema/manifest.schema.yaml` listing required fields:
- `experiment.id`, `experiment.subject`, `experiment.target_weak_area`, `experiment.contributing_llms` (≥2)
- `hypotheses[]` with `slug`, `name`, `rationale`, `anatomy`, `sources[]` (which LLMs)
- `rendering.image_size`, `rendering.template`, `rendering.varying_region`

PyYAML 6.0.3 — always `yaml.safe_load`, never `yaml.load(stream)` without a Loader (security advisory: `yaml.load` defaults were unsafe pre-6.0; even now, never use `Loader=Loader` on untrusted input) ([PyYAML deprecation wiki](https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation)).

Confidence: **HIGH** (existing repo pattern, verified locally).

---

## 7. Image / Preview Rendering Ergonomics

### Existing pipeline (KEEP)

Verified in `Dockerfile.claude:48-55` and existing template builds:
1. Python `tools/render.py` produces SLA via `sla_lib`.
2. `xvfb-run scribus --no-gui` exports SLA → PDF.
3. `pdftoppm` (poppler-utils) rasterizes PDF → PNG at two DPI levels.

**For variants in this issue:** each `experiments/<id>/variants/<slug>.py` imports the falzflyer scaffolding (CONTEXT decision 1), produces a SLA, then runs the same Scribus+pdftoppm path. The build pipeline already exists; we just need a per-variant wrapper.

### Cleaner alternatives investigated

| Alternative | Verdict for MVP |
|-------------|-----------------|
| **Inkscape CLI** (`inkscape --export-type=png`) | Skip — Inkscape can't render `.sla` files. The whole pipeline is Scribus-native. |
| **ImageMagick `convert` from PDF** | Already a fallback, slower than pdftoppm, sometimes lossier. Stay with pdftoppm. |
| **Direct Cairo/PIL rendering** | Would mean reimplementing the layout engine. Massively more work than the locked architecture. Skip. |

**Recommendation:** keep the existing Scribus → PDF → PNG path. No new tools. The `tools/experiment_render.py` orchestrator wraps existing `tools/render.py` per variant.

### Image dimensions for preview

Verified locally via Pillow:
- `templates/kandidat-falzflyer-din-lang/page-01.png`: **1241 × 898 px** (thumbnail, ~50–100 dpi)
- `templates/kandidat-falzflyer-din-lang/page-01-hires.png`: **1861 × 1347 px** (hi-res, 150 dpi per [`site/src/pages/templates/[...id].astro:25-27`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/site/src/pages/templates/[...id].astro))

**Recommendation for variant images:** match these two sizes exactly (CONTEXT.md discretion §6: "Variant image dimensions: match the existing gallery preview sizes"). Use the thumbnail in the versus-mode side-by-side viewport (~600 px each, 2-up) and link to the hi-res for click-to-zoom (mirroring issue #28 lightbox pattern). For "design comparison" preview tasks in research, ~1500–2000 px wide is the typical web-rendered comparison size — our 1861 px hi-res hits that range. **No need to deviate.**

Confidence: **HIGH** (verified locally + existing pattern).

---

## 8. JSON Results Format Conventions

**Finding: no industry-standard schema exists for pairwise vote records.** Searches for any standardised vote-record JSON schema returned only product-specific exports (Pairwise.vote, OpinionX, etc.). This is a "no need to align with anything" finding.

**Recommendation: use the schema defined in CONTEXT.md decision 10 verbatim.** It already names every required field (rater, timestamps, per-pair entries with axis, position, computed wins-ratio, computed ranking, disagreement index). Document it in `experiments/_schema/results.schema.yaml` so multiple raters' files are interoperable.

**Compression / size:** ~50 votes × ~250 bytes = ~12 KB per rater-export. No compression needed; gzip would shave to ~3 KB, but `.json` files are easier to inspect and merge by hand. Skip compression.

**Multi-rater merge tool (phase 2):** when it lands, it's a 30-line Python script: read N JSONs, concatenate `pair_votes[]`, recompute aggregate wins-ratio per axis, output a merged file. No library needed.

Confidence: **MEDIUM** (negative claim verified by absence in search results; positive claim is straightforward).

---

## 9. Vanilla JS Pairwise UIs in the Wild — UX Patterns to Adopt

| Tool | Open source? | Pattern worth copying |
|------|--------------|----------------------|
| [AllOurIdeas](https://github.com/allourideas/allourideas.org) | Yes (Ruby, abandoned) | Big clickable cards (not radio buttons), keyboard shortcuts (←/→/Space), explicit "I can't decide" / skip button. **Copy these affordances; don't import code.** |
| [Pairwise.vote](https://www.pairwise.vote/) | No | Mobile-first 2-up layout with large tap zones; consider for our UI even though we're desktop-primary. |
| [OpinionX taxonomy](https://www.opinionx.co/blog/pairwise-comparison) | No (article) | Distinguishes "force-choice" vs "free-pick with skip" — the issue's two-axis pattern is a force-choice variant. |
| **A/B design-test tools** (UsabilityHub / Lyssna, Maze) | No | UX teaches: keep one screen per task, commit on click (no submit button), show progress bar (#completed / #total pairs), allow "back" only briefly. We should add a pair counter and a progress bar. |

**Specific UX recommendations for our voting page:**
1. **Big clickable cards, full-image as the click target** — hover state shows a thin border, click commits.
2. **Both axis questions visible simultaneously** — two click-rows under the pair, not sequential screens (matches CONTEXT decision 4: "two clicks per pair").
3. **Progress bar** showing `X / 45 pairs voted` per axis (45 pairs × 2 axes = 90 clicks; surface this).
4. **Keyboard shortcuts** for power-rating: `Q`/`W` for axis-A left/right; `O`/`P` for axis-T left/right (or `←`/`→` for current axis with `Tab` to switch axis — pick whichever feels right in usability).
5. **"Skip pair" affordance** — rater can mark a pair as "can't decide" instead of forcing a choice. AllOurIdeas does this; we should too.
6. **Show the variant slug + hypothesis name on hover** — rater might want to know what they're voting on after the fact, but should not see it during the pair (avoid biasing).

Confidence: **MEDIUM** (UX recommendations are judgment calls grounded in cited prior art).

---

## 10. Standard Versions to Lock — Summary Table

This is the consolidated lock-list the planner should pin:

| Library / Tool | Version | Already Installed? | Pin Location |
|----------------|---------|--------------------|--------------|
| Astro | `^5.0.0` | Yes (`site/package.json`) | No change |
| PyYAML | `6.0.3` | Yes (Debian trixie via Dockerfile.claude) | No change — existing pin |
| jsonschema | `4.26.0` | Yes (Dockerfile.claude:80) | No change |
| Pillow | `12.2.0` | Yes (Dockerfile.claude:79) | No change — only used if image post-processing needed |
| `codex` CLI | `0.128.0` | Yes (PATH) | No change |
| `gemini` CLI | `0.41.2` | Yes (PATH) | No change |
| `claude` CLI | `2.1.132` | Yes (PATH) | No change |
| Scribus | 1.6.x (system, Debian trixie) | Yes (Dockerfile.claude:48) | No change |
| poppler-utils (`pdftoppm`) | system | Yes | No change |
| ImageMagick | system | Yes | No change |
| **`choix`** (deferred) | `0.4.1` | No | Don't add — reserve for phase-2 BT |
| **`anthropic` SDK** (deferred) | `0.100.0` | No | Don't add — CLI subprocess pattern is the workspace standard |
| **`openai` SDK** (deferred) | latest | No | Don't add — same |
| **`tenacity`** (deferred) | latest | No | Don't add — SDKs / CLIs retry natively |
| **`rapidfuzz`** (deferred) | latest | No | Don't add — `difflib` covers MVP dedup |

**Net new dependencies for MVP: ZERO.** The existing toolchain covers every locked decision.

---

## Sources

### HIGH confidence (verified)
- [`site/package.json`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/site/package.json) — local read
- [`Dockerfile.claude`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/Dockerfile.claude) — local read
- [`tools/visual_review.py`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/tools/visual_review.py) — existing multi-LLM orchestration pattern (CRITICAL reference)
- [`shared/template-spec.schema.yaml`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/shared/template-spec.schema.yaml) — existing schema pattern
- [`site/src/pages/templates/[...id].astro`](file:///root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations/site/src/pages/templates/[...id].astro) — existing vanilla-JS-in-Astro pattern (lightbox)
- [Astro: Scripts and event handling](https://docs.astro.build/en/guides/client-side-scripts/)
- [Astro: Islands architecture](https://docs.astro.build/en/concepts/islands/)
- [Astro 5.0 announcement](https://astro.build/blog/astro-5/)
- [MDN: Storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)
- [WebKit: Updates to Storage Policy (ITP)](https://webkit.org/blog/14403/updates-to-storage-policy/)
- [Anthropic Claude API model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)
- [Anthropic Python SDK on PyPI](https://pypi.org/project/anthropic/) — version 0.100.0 verified
- [OpenAI: Latest model (GPT-5.5)](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenAI: Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [choix on PyPI](https://pypi.org/project/choix/) — 0.4.1 verified
- [choix project docs](http://choix.lum.li/)
- [PyYAML 6.0 deprecation wiki](https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation)
- [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)

### MEDIUM confidence (verified by multiple sources)
- [DEV: localStorage vs IndexedDB best practices](https://dev.to/tene/localstorage-vs-indexeddb-javascript-guide-storage-limits-best-practices-fl5)
- [DEV: RapidFuzz vs Difflib comparison](https://dev.to/mrquite/smart-text-matching-rapidfuzz-vs-difflib-ge5)
- [AllOurIdeas GitHub org](https://github.com/allourideas)
- [Pairwise.vote (commercial UX reference)](https://www.pairwise.vote/)
- [OpinionX: Pairwise comparison guide](https://www.opinionx.co/blog/pairwise-comparison)
- [Astro in 2026 (DEV)](https://dev.to/polliog/astro-in-2026-why-its-beating-nextjs-for-content-sites-and-what-cloudflares-acquisition-means-6kl)

### LOW confidence (used only as background, not basis for any recommendation)
- None — every recommendation has at least HIGH or MEDIUM evidence.

---

## Confidence Ratings — Per Area

| Area | Level | Notes |
|------|-------|-------|
| 1. Pairwise voting algorithms | **HIGH** | Wins-ratio recommendation matches CONTEXT.md; choix verified on PyPI; combinatoric reasoning is unambiguous. |
| 2. Astro 5 client islands | **HIGH** | Existing repo pattern + verified Astro docs; no novelty. |
| 3. localStorage / browser persistence | **HIGH** | MDN + WebKit official sources; quotas / pitfalls well-documented. |
| 4. Multi-LLM coordination | **HIGH** | Existing `tools/visual_review.py` is the gold reference; model IDs verified against vendor docs. |
| 5. Hypothesis dedup | **HIGH** | difflib in stdlib + scale argument is mathematically simple. |
| 6. YAML / schema validation | **HIGH** | Existing repo pattern at `shared/template-spec.schema.yaml`. |
| 7. Image / preview rendering | **HIGH** | Existing pipeline + image dimensions verified locally. |
| 8. JSON results format | **MEDIUM** | "No standard exists" is a negative claim, harder to verify exhaustively, but multiple searches confirm absence of a consolidated pairwise-vote schema. |
| 9. Vanilla-JS UI prior art | **MEDIUM** | UX recommendations are judgement; cited examples are real but pattern-borrowing is subjective. |
| 10. Standard versions to lock | **HIGH** | Every version verified against PyPI / npm / vendor docs / local probes. |

**Overall confidence: HIGH.** The MVP can be planned and built with zero new dependencies and the existing repo's multi-LLM orchestration pattern.
