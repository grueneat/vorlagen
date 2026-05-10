# Pitfalls Research — Issue #29 Design Experimentation MVP

**Researcher:** PITFALLS sub-agent
**Date:** 2026-05-10
**Scope:** Risks, edge cases, common mistakes, environment audit for an MVP that generates structurally-distinct variations of falzflyer P2 and ranks them via pairwise voting on two axes (appeal A / transport T).

---

## 1. Pairwise Voting Bias Risks

### 1.1 Position bias (left/right preference)

**Risk:** Without randomization, raters systematically prefer one screen position. With LLM judges, position bias is a documented and substantial effect; with human raters in two-alternative forced-choice, it is smaller (typically 5–10 percentage points) but non-trivial.
**Failure mode:** A variant that happens to land more often on the favoured side wins on that bias rather than on merit, contaminating the ranking.
**Mitigation:** CONTEXT.md decision #4 already locks per-pair left/right randomization. **This is sufficient *only if* the per-pair randomization is statistically independent and the position is logged in the JSON results so post-hoc bias can be measured.** The results JSON in decision #10 already records `position-on-screen` per vote — keep that field, and add a one-line check that prints "left wins / right wins" totals on export so a raw imbalance is visible to the rater. Position-flipping in 35% of LLM-as-judge cases when a distractor is added (COLM 2025) is the LLM-judge baseline — humans flip less but the recommended *protocol* (randomize per pair, log position) is the same.
**Confidence:** HIGH for "randomize + log is sufficient for MVP." MEDIUM for the magnitude estimate in human raters (most quantified studies are LLM-judge).

### 1.2 Order effects across the session (anchoring)

**Risk:** The first 1–2 pairs anchor what "good" looks like for the rest of the session. If the first pair contrasts a strong vs. weak variant, calibration sticks; if it contrasts two weak variants, the rest of the session is calibrated to a low ceiling.
**Failure mode:** Different rater sessions produce different rankings of the same set because they started on different pairs.
**Mitigation:** All-pairs randomized order (locked in decision #3) is the correct base. Two additional cheap moves: (a) **don't** sort variants alphabetically into the bag — explicitly shuffle the variant list once at session start (Fisher–Yates), (b) consider a small "warm-up" hint in the UI ("first 2–3 pairs help you calibrate; keep going to stabilize the ranking") so the rater is *aware* their early votes are noisier rather than treating them as authoritative.
**Confidence:** MEDIUM. Anchoring is well-documented in psychophysics; the specific mitigation is convention rather than measured effect.

### 1.3 Fatigue at 90 votes per session

**Risk:** With 10 variants × 45 pairs × 2 axes, a single complete session = **90 binary judgments**. The pairwise-comparison literature consistently flags fatigue as a primary threat to reliability; the threshold varies but ~30–50 forced-choice pairs is a commonly-cited inflection point where reliability degrades. 90 is over that line.
**Failure mode:** Late-session pairs are noisier than early-session pairs, which biases the wins-ratio toward whichever variants happened to appear earlier (the inverse of the anchoring problem).
**Mitigation:**
- **Allow stop-anywhere with confidence reporting** (already in decision #3 via "Rater can stop anytime; wins-ratio over completed pairs"). Surface "you have voted on N of M pairs; rankings stabilize after ~30 pairs per axis" in the UI.
- **Two-axis-per-pair (locked) actually halves session length** vs. doing the axes in two sequential sessions, because each pair shows once and asks both questions. Keep this — sequential would mean 90 pair-views, this is 45 pair-views with 2 clicks each.
- **Persist per-pair completion state** (decision #9 localStorage) so the rater can break across multiple sittings without losing progress. This is the real mitigation: 90 votes across 3 sittings of 15 minutes each is comfortable; 90 in one sitting is not.
- **Optionally** in MVP+1, add a balanced-incomplete-block design or adaptive sampling — out of scope per CONTEXT.md "deferred."
**Confidence:** MEDIUM. The 30–50 threshold is convention; the mitigation pattern (chunkable session + stop-anywhere) is universally recommended.

### 1.4 Two-axis cognitive load and contamination

**Risk:** Asking "which appeals more?" + "which transports better?" simultaneously is a textbook setup for halo-effect contamination — the rater forms an overall judgment of variant A vs. B and assigns *both* axes to the same winner.
**Failure mode:** Disagreement-index field in results JSON (decision #10) reads as suspiciously low — either appeal=transport in 90%+ of pairs (real halo effect) or 0% (rater was sequentially flipping a coin, which is the opposite failure). Either pattern means the two axes are not measuring two things.
**Research evidence:** Halo-effect research in writing assessment (Jeon & Lee 2020, *Language Testing in Asia*) explicitly recommends presenting **one rating criterion at a time** to reduce halo contamination — i.e., the literature *prefers sequential* over simultaneous for multi-criterion rating. CONTEXT.md decision #4 explicitly locks simultaneous, accepting this tradeoff.
**Mitigation:** The lock is fine for MVP because:
- Halving session length is worth the halo risk for a one-rater MVP (decision #11 deliberately ships with one rater)
- Disagreement-index is the diagnostic — if appeal and transport agree on >85% of pairs, the next experiment should test sequential to compare; if they disagree on 15–30%, simultaneous is working as intended (the axes are measuring different things)
- **Order the two questions consistently** in the UI (e.g., always show appeal-question first, transport-question second). Random order between questions adds noise without buying anything.
- Surface the disagreement-index prominently in the export view; treat very-low (<5%) and very-high (>50%) disagreement as flags worth discussing post-experiment.
**Confidence:** HIGH on the contamination risk being real; MEDIUM on whether the mitigation is sufficient (true test is to run the experiment and look at the disagreement-index distribution).

### 1.5 Halo effect — visually striking variations winning on transport

**Risk:** A variant with a bold yellow accent or a dramatic size-jump can win the *appeal* axis legitimately and then drag the *transport* axis with it via halo. The user explicitly named this as a concern.
**Failure mode:** Top-3 by transport is identical to top-3 by appeal — the experiment has produced one ranking, not two, and the design-guide rule "transport is a separate axis" gains no evidence.
**Detection:** In the results JSON, compute and surface:
- **Per-variant axis correlation:** does this variant rank similarly on A and T?
- **Disagreement index** at the pair level (already locked in decision #10)
- **Rank-distance metric:** Spearman correlation between A-ranking and T-ranking — values > 0.85 are a halo flag, values < 0.5 mean the two axes are measuring genuinely independent things and the experiment is working
**Mitigation:** Don't *prevent* halo — **measure and surface it**. Halo is data, not noise; if it's high, the corpus update should note "this experiment failed to discriminate the axes; rerun with sequential rating." The MVP's job is to *make halo visible*, not eliminate it.
**Confidence:** HIGH on the existence of the effect; HIGH on the measurement-not-elimination strategy.

---

## 2. Hypothesis-Generation Prompt-Engineering Pitfalls

### 2.1 "Structurally distinct" is hard to enforce in prompts

**Risk:** Saying "produce structurally distinct variations" yields ~70% parameter tweaks (different spacing, different yellow size, different list count) because LLMs default to "safe" variation along measurable dimensions.
**Failure mode:** 10 variations turn out to be 3 hypothesis families × 3–4 parameter tweaks each → tournament picks the median of the dominant family, not the strongest of 10 distinct options. **This is the local-optimum failure the user named.**
**Mitigation patterns** (synthesised from prompt-engineering research and the verbalized-sampling line of work):
- **Positive + negative example pairs in the prompt.** CONTEXT.md decision #6 already requires this. The negative example must be concrete: "BAD: change Schlagwort spacing from 8mm to 12mm — this is a parameter tweak. GOOD: cut from 5 items to 3 items, each with a 2-line body — this is a different commitment about information density."
- **Force a "commitment-axis" taxonomy in the prompt:** require the model to name *which* design axis each hypothesis commits to (e.g., density, hierarchy strategy, typographic emphasis, photographic vs. typographic, asymmetric vs. centered). Hypotheses that share an axis must commit *differently* on that axis (one privileges-one-item-via-yellow, another via-2.5x-size-jump, another via-italic-only — all under "hierarchy strategy" but each with a structurally different lever).
- **Verbalized-sampling-style prompting** (arXiv 2510.01171, 2025): ask the model to verbalize *which mode* each variation belongs to before generating it, and reject duplicates at the mode level not the prose level. Multi-LLM generation (decision #6) helps because models converge on different "modes" by default.
- **Post-generation distinctness check:** after merging across LLMs, run a deduplication pass that compares each pair of hypotheses on the structural axes. If two share all axes, drop one. Ideally an LLM-as-judge step ("are hypothesis A and hypothesis B structurally distinct, or parameter tweaks of each other?") with a Flo-overridable flag.
**Confidence:** HIGH that parameter-tweak collapse will happen without explicit countermeasures. MEDIUM that the listed mitigations are sufficient — needs empirical validation in the first experiment run.

### 2.2 LLM "safe middle-of-the-road" tendency

**Risk:** Asked for variations, instruction-tuned LLMs converge on culturally-neutral, low-commitment options. The "Diversity Collapse" paper (arXiv 2505.18949) shows structured prompts consistently yield lower semantic and topical diversity than simple prompts.
**Failure mode:** All 10 hypotheses are minor refactors of the baseline; none commits boldly enough to be a real design alternative.
**Mitigation:**
- Include explicit permission to be radical: "These hypotheses are *experiments*, not deliverables. A hypothesis that turns out to be wrong is as valuable as one that turns out to be right. Default to bolder commitments than you would normally suggest."
- Include explicit anti-anchoring: "Do not anchor on the current baseline. The baseline is the *worst* of these alternatives; the variations should diverge from it, not improve on it incrementally."
- Multi-LLM (decision #6) helps because mode-collapse is per-model — Opus's safe middle and Codex's safe middle are slightly different.
**Confidence:** MEDIUM-HIGH. Verified across multiple 2025 papers.

### 2.3 Mode collapse across multiple LLMs

**Risk:** Even with independent prompts, two frontier LLMs may converge on very similar hypothesis lists because they share training data and similar instruction-tuning regimes. The independence assumption in decision #6 may be optimistic.
**Failure mode:** "Multi-LLM hypothesis generation" produces 14 hypotheses where 12 of them appear in both lists — feels like coverage but is actually a single perspective with attribution duplicated.
**Mitigation:**
- **Diversify prompt framings across LLMs**, not just identical prompts to multiple endpoints. E.g., Opus gets "as a typography-first designer, propose 6 hypotheses"; Codex gets "as a hierarchy-first designer, propose 6 hypotheses." The role priming actively pushes each model toward a different mode.
- **Track agreement rate as a signal, not noise:** when both models propose the same hypothesis, that's a confidence-signal in the manifest (decision #6 already says this). When models *disagree*, those are the hypotheses most worth running.
- **Use at least one model from a different family** (Codex/GPT vs. Anthropic). Avoid "Opus + Sonnet" — same family, near-identical priors.
**Confidence:** MEDIUM. Mode collapse across families is documented; the mitigation pattern is convention.

### 2.4 Validating distinctness post-generation

**Risk:** Without an explicit check, distinctness is *claimed* by the prompt but not *verified*. The MVP could ship 10 variations and only discover during voting that 4 of them look identical.
**Mitigation:**
- **Post-generation validation step:** an LLM-as-judge pass that, for each pair of hypotheses (45 pairs for 10 variants), answers "structurally distinct: yes/no" with one-line reason. Build this into the manifest pipeline. Flag pairs marked "no" and require manual override or merge.
- **Variant-level structural-axis diff:** auto-generate a comparison matrix from the manifest's named axes. If two variants share the same row across all axes, the dedup gate trips.
- **Visual spot-check before voting:** present all 10 rendered variants on a single page (the direct-pick mode satisfies this) and let Flo eyeball-verify they look different *before* starting the versus mode. The optional Flo-prune step (CONTEXT.md "Optional Flo override") is exactly this.
**Confidence:** HIGH on the need for this gate; MEDIUM on the exact form (which mitigation works best is empirical).

---

## 3. Local Optimum Risk

**Risk (user-named):** "20 variations of taste-poor baseline = least-bad of N mediocre options." A pairwise tournament rigorously picks the best of *what's in the bag*. If everything in the bag is mediocre, the winner is the least-bad mediocre option. This is the textbook MAB exploration-vs-exploitation tradeoff: too much exploitation around one design region = converges on a local optimum; never-explored regions might contain the real maximum.

**Failure mode:** The MVP runs cleanly, produces a ranking, the corpus gets updated — but the corpus update enshrines a local optimum as if it were the global one. Subsequent experiments anchor on it. The system is *worse* than no system, because it produces false confidence.

**Mitigation:**
1. **Span the design space at the hypothesis stage**, not the parameter stage. Decision #6's "structural distinctness" requirement is the primary defence — it forces hypotheses to commit to *different* design philosophies, not different points on the same continuum. This is exploration baked into the hypothesis generation, not added afterward.
2. **Include at least one "wild card" hypothesis per experiment** — a deliberately-out-of-baseline option that the prompt explicitly asks for. E.g., "one hypothesis must abandon the bullet/Schlagwort form entirely (e.g., a single-paragraph body, or three sentence-headlines with body)." A wild card that loses badly is informative; a wild card that wins surprises and resets the design space.
3. **Use the bottom-3 deliberately.** CONTEXT.md decision #11 mandates capturing top-3 *and* bottom-3. Bottom-3 are the explicit "what didn't work" entries — they prevent the corpus from becoming a survivorship-biased archive. The bottom-3 from this experiment are evidence about the *space*, not just about the winners.
4. **Run experiments at the corpus-gap level (decision #7), not the polish level.** The "Mein Plan" panel is a §6/§8/§9-named gap — running an experiment here is by definition exploring an under-mapped region. *Don't* run experiments on already-strong areas; that's where local-optimum risk is highest because the rules are already calibrated.
5. **Spearman-rank against pre-experiment Flo prediction:** Before running the experiment, ask Flo to rank the 10 variants by gut feel. If the post-experiment ranking matches Flo's pre-experiment ranking with Spearman > 0.9, the experiment learned almost nothing — flag for re-design with bolder hypotheses. If correlation is low, the experiment surfaced something Flo didn't already know — high-value run.

**Confidence:** HIGH on the risk; HIGH on (1)–(4); MEDIUM on (5) — it's a useful diagnostic but adds overhead.

---

## 4. Variant Rendering Pitfalls

### 4.1 Scribus rendering — known issues from archived issues

**Risk:** Per archived issues in `.issues/archive/`:
- **#3 / #4** ("render-fidelity ground truth", "local render pipeline that commits gallery artifacts"): Brand fonts (Gotham Narrow) cannot be in CI for licensing reasons; rendering is a *local-only* pipeline. **Implication for MVP: variant rendering must run locally in the dev container; do not assume CI can produce variant PNGs.**
- **#11** ("Demo-Bilder via Codex"): demo image generation was committed-bytes only, not generated on each render. Variant images for the experiment should follow the same convention — render once locally, commit the PNGs.
- **#16** ("Zeitung A4 image frames placed past page boundary"): polygon/frame coords past page bounds silently spill into adjacent pages in PDF output — this bug class exists. For falzflyer P2 variations, every variant must be `inside_page`-validated against the panel's x=99..198 bounds and y=0..213 bounds. The existing `inside_page` check from issue #14 is the gate.
- **#22 / #23 / #24** (alignment system v2, zeitung remaining alignment, scale_type letterbox): variant builds must run through `audit_alignment.py` and `spec_check` before being treated as valid. Don't bypass the existing structural-check gates because "it's just an experiment."

**Failure mode:** Variants render to PDF/PNG without errors but the actual page geometry is wrong (spills, misaligned, undeclared drift). Tournament votes on rendering artifacts rather than design intent. Worst case: a variant wins because its accidental misalignment looks "interesting."
**Mitigation:**
- Each variant build script must call the same `inside_page` and alignment checks the production templates use. **Never give variants a free pass on structural checks.**
- The variant manifest must declare expected geometry; spec_check fails the variant out of the experiment if it drifts. Failed variants are dropped from the bag with a clear log message — they don't get to vote.
- Per archived issue #4 lessons: render PDFs once locally, rasterize to PNG once, commit both. Don't re-render during the Astro build.
**Confidence:** HIGH (direct lessons from archived issues).

### 4.2 Reproducibility (deterministic render)

**Risk:** Same SLA → different PNG bytes across two runs would mean A/B comparisons could be confounded by render noise. Documented sources of nondeterminism: PDF metadata `/CreationDate` and `/ModDate`, font cache state, Scribus internal random ordering of dict keys.
**Failure mode:** Variant looks different on render-1 vs render-2 even with identical input. Rater can't distinguish "is this a real design difference or render noise?"
**Mitigation:** The existing render pipeline (`tools/render.py` + `bin/render-gallery`) already wraps Scribus with `xvfb-run` and produces stable PDFs that `visual_diff` can compare. Per archived issue #4: "running it twice on the same SLA must produce byte-identical output (modulo the verified-non-deterministic PDF metadata layer that visual_diff already ignores)." Extend to PNG rasterization — use a fixed-DPI raster (e.g., 80 dpi like gallery; the existing `gallery_build.py` already standardises this) and commit the PNGs once. Never re-rasterize during voting.
**Confidence:** HIGH. The pipeline is already deterministic-by-design.

### 4.3 Image-size discrepancies between variants

**Risk:** If one variant accidentally renders at a different page size or its preview is cropped/letterboxed differently, the rater is choosing on layout vs. crop, not on the design hypothesis.
**Failure mode:** Variant with the slightly-bigger preview wins on appeal because it looks more confident; the underlying design might be worse. Subtle and hard to detect.
**Mitigation:**
- **All variants render the full DIN-lang front page (P1+P2+P3) at identical dimensions** — locked by CONTEXT.md decision #5 ("variations rendered in situ"). Verify by asserting all PNG widths/heights match in the manifest pipeline.
- The voting UI must display variants at fixed CSS dimensions (e.g., `max-width: 600px; aspect-ratio: 297/210; object-fit: contain`) so even if one PNG is accidentally larger, the displayed size is consistent.
- Use `width` + `height` HTML attrs to prevent CLS (cumulative layout shift) which would also bias quick-glance judgments.
**Confidence:** HIGH.

---

## 5. localStorage / Browser Persistence Edge Cases

### 5.1 Quota exhaustion

**Risk:** localStorage cap is 10 MiB across browsers. The vote-data is small (<100 KB even for 100 pairs), so the *vote data itself* won't hit quota. But if anyone naïvely caches the variant PNGs in localStorage they will (each PNG is ~50–200 KB; 10 of them = 1–2 MiB; multiple experiments stack).
**Mitigation:** **Never put images in localStorage.** Store only the vote pairs, axis, winner, position, timestamp, rater identity. Images load from the static Astro build like any other gallery image.
**Confidence:** HIGH.

### 5.2 Private browsing / incognito

**Risk:** In private/incognito mode, localStorage is treated like sessionStorage — data is wiped when the tab closes. A rater who happens to vote in incognito loses everything.
**Failure mode:** Rater finishes 60 pairs, closes incognito tab to step away, comes back to a blank slate.
**Mitigation:**
- **Detect non-persistent storage on page load** — write a sentinel to localStorage and check `window.sessionStorage === window.localStorage` heuristics, or use `navigator.storage.persisted()` where available.
- **Show a non-dismissable banner** when persistence isn't available: "Voting in private/incognito mode means your votes will be lost when you close the tab. Use export-as-you-go." Surface an "Export progress" button that lets the rater download partial JSON at any time.
- The CONTEXT.md decision #9 phrase "explicit JSON export" already makes this the safety valve — we just need to *advertise* it visibly.
**Confidence:** HIGH on the risk; HIGH on the mitigation.

### 5.3 Safari ITP — 7-day eviction

**Risk:** Safari's Intelligent Tracking Prevention deletes script-writable storage (including localStorage) after 7 days without user interaction with the origin. For local file:// or localhost dev, this generally doesn't apply, but if the experiment is hosted (GitHub Pages, Netlify), Safari users who vote across multiple weeks lose data.
**Failure mode:** Rater starts the experiment Monday, comes back the following Tuesday, all votes gone.
**Mitigation:**
- **Same as 5.2:** make export-as-you-go visible. Rater downloads partial JSON daily; the JSON is the durable artifact, localStorage is just convenience.
- For MVP this is "local Astro dev/build" (CONTEXT.md "Hosted/shared deployment" is deferred), so ITP is mostly a non-issue at MVP scope. **Document it for phase-2** when hosting becomes real.
**Confidence:** HIGH on the risk class; LOW on whether it actually bites the MVP (depends on hosting choice — currently local).

### 5.4 User clears browser data mid-tournament

**Risk:** User runs "Clear browsing data" or a privacy extension wipes localStorage. Same outcome as 5.2/5.3.
**Mitigation:** Same — visible export, frequent reminders, JSON is the durable record.
**Confidence:** HIGH.

### 5.5 Cross-device / cross-browser

**Risk:** Rater votes 30 pairs on laptop, then opens the experiment on phone — phone has no idea about laptop votes (localStorage is per-origin per-device).
**Mitigation:** **Document this** in the workflow, don't try to solve it at MVP scope (multi-rater/multi-device merging is explicitly deferred). Workflow: "Vote on one device per session. Export the JSON when done. Multi-device support is phase 2."
**Confidence:** HIGH.

---

## 6. Two-Axis Disagreement Handling

**Risk:** Appeal and transport will disagree on a non-trivial fraction of pairs (probably 15–35% if the experiment is working). The MVP must handle this without producing a self-contradicting "ranking."

**Failure mode (the worst):** auto-merging A and T into a single composite ranking via average / weighted sum — this destroys the very signal the two-axis design was meant to capture. The user explicitly said "answers can disagree and the disagreement itself is information."

**Mitigation (locked in CONTEXT.md decision #10):**
- **Two separate rankings in the JSON output:** `ranking_appeal: [variantId, ...]` and `ranking_transport: [variantId, ...]`. Never compute a composite.
- **Disagreement index:** count of pairs where A-winner ≠ T-winner. Surface as both a count and a per-pair list (which pairs disagreed). Don't summarize disagreement away — show the rater (and the corpus update) which specific pairs split.
- **Per-variant axis dispersion:** for each variant, record how its A-rank compared to its T-rank. A variant that ranks #2 on A and #8 on T is *interesting* (visually striking but communicates badly, or vice versa) — preserve that signal in the corpus update.
- **Don't auto-resolve.** If a variant wins on A and loses on T, that goes into the corpus as "this variant is appealing but doesn't transport well — visual signature: …" — that's a corpus entry the system was *built to produce*. Auto-resolution would erase it.
- The corpus capture step (the manual one in the MVP workflow) is responsible for *interpreting* disagreement, not the tooling.

**Confidence:** HIGH.

---

## 7. Multi-LLM Coordination Pitfalls

### 7.1 Rate limits and retries

**Risk:** Independent calls to multiple LLMs can hit per-key rate limits, especially if the experiment retries on bad output. Failed calls block the experiment.
**Mitigation:**
- **Sequential generation, not parallel.** Two LLMs × ~5–10 hypotheses each is a small enough generation budget that sequential is fine and avoids burst-rate-limit issues.
- Implement basic retry-with-exponential-backoff on transient errors (network, 429, 5xx). Don't retry on 400 (bad prompt) — surface and abort.
- Cache generated hypothesis sets to disk on first success — re-runs of the manifest pipeline read from cache, don't re-call the LLM. This also saves money and makes the experiment reproducible (decision #6 mentions "post-experiment hypothesis review" — needs the original outputs preserved).
**Confidence:** HIGH.

### 7.2 Schema variance across LLM outputs

**Risk:** Different models (Opus, GPT, Gemini) format JSON differently, hallucinate extra keys, omit required keys, return prose with embedded JSON blocks rather than pure JSON. Prompt-engineering tooling (promptfoo, dspy) treats this as a primary failure mode.
**Failure mode:** Pipeline crashes on a `KeyError` mid-generation, losing the partial output.
**Mitigation:**
- **Schema-validate aggressively.** Use a JSON schema (or pydantic if SDK available; see env audit — pydantic likely needs install) for the hypothesis output: `{slug: str, name: str, axis_commitments: {density|hierarchy|typography|...}, rationale: str, expected_outcome: str}`. Anything that fails the schema gets one retry with the validation error fed back ("your previous output failed validation: <error>; please return valid JSON matching this schema") then is dropped.
- **Tolerant JSON parsing:** strip leading/trailing prose, extract first `{` to last `}`, parse. If models insist on Markdown code fences, strip them before parsing.
- Log every raw LLM output to disk for debugging, even on success.
**Confidence:** HIGH.

### 7.3 One LLM failing should not block the experiment

**Risk:** If 2 of 2 LLMs are required and one fails, the experiment can't run.
**Mitigation:** Treat LLMs as `≥1 required, ≥2 preferred`. The pipeline runs as long as one LLM succeeds; if only one runs, the manifest documents that and notes the reduced diversity. Multi-LLM is a *quality* requirement, not a *correctness* one.
**Confidence:** HIGH.

### 7.4 Token budget reasoning

**Risk:** ~12 hypotheses × N models is very cheap (each hypothesis ~500 tokens out, prompt ~2k tokens in). Total: ~30–60k tokens per experiment, even with N=3 models — Opus pricing makes this <$2/experiment. Variant rendering is *not* an LLM cost — it's Scribus rendering, which is free locally. **The cost concern in the issue is overstated; this is not a budget pitfall.**
**Confidence:** HIGH.

### 7.5 API key access pattern (existing repo)

**Finding from environment audit (§9):** No `.env` file in workspace, no `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` in environment, no Anthropic/OpenAI/Google SDK installed in the system Python. The Anthropic CLI binary `/root/.local/bin/claude` (Claude Code 2.1.132) **is** available. **The repo currently does not have an established LLM-API key access pattern** — there are no `os.environ['ANTHROPIC_API_KEY']` references in `tools/` or `bin/`.

**Implication:** The MVP needs to *establish* the LLM access pattern, not inherit one. Options (in order of MVP-ergonomic):
1. **Use the `claude` CLI as a subprocess** — it's already authenticated, no new key management. Run `claude --print --output-format json -p "<prompt>"` from the hypothesis-generation tool. Trade-off: less ergonomic than SDK, but zero new infrastructure.
2. **Install `anthropic` Python SDK + `.env` pattern** — standard, but introduces key management to a repo that has avoided it.
3. **Use `issue:review` external-LLM tools** — CONTEXT.md mentions this as one option for the second model; appears to already exist in the workflow.

**Recommendation:** Surface this as a Tier-1 question for the planner. The simplest MVP path is option (1), using `claude` for the Anthropic-family generation and `issue:review` (whatever it currently uses) for the second model. Don't introduce key management into the repo unless the planner can confirm an existing pattern this researcher missed.
**Confidence:** HIGH on the gap; MEDIUM on the recommendation (planner should verify).

---

## 8. Astro 5 / Static-Site Deployment Pitfalls

### 8.1 Build-time vs. runtime data

**Risk:** Astro 5 default is fully static — `getCollection()` and `getStaticPaths()` run at *build time*, not runtime. If the experiment manifest is generated dynamically (e.g., LLM call during `astro build`), it must complete before the build finishes, and the build fails if the LLM call fails.
**Failure mode:** Site is broken because hypothesis generation flaked.
**Mitigation:**
- **Generate the manifest *before* `astro build`.** The hypothesis-generation pipeline runs as a separate `bin/experiment-generate` step, writes `experiments/<id>/manifest.yml` and the rendered PNGs to `site/public/experiments/<id>/`, *then* `astro build` runs and reads the static manifest as a content collection. This matches the existing `bin/render-gallery` → `astro build` pattern (archived issue #4).
- **Add an `experiments` content collection** to `site/src/content.config.ts` so each experiment's manifest is type-safe and discoverable by Astro's collection API. Schema: `{id, subject, target_weak_area, contributing_llms, hypotheses: [{slug, name, axes, rationale, image_path}]}`.
- The Astro 5.10 "live content collections" feature is **experimental** — don't use it for MVP. Stay on the standard build-time content layer.
**Confidence:** HIGH.

### 8.2 Image paths under static base paths

**Risk:** If the site deploys under a base path (e.g., GitHub Pages at `/vorlagen/`), absolute image paths in voting UI break.
**Mitigation:** Use Astro's `import.meta.env.BASE_URL` or import images via `import` statements (Vite handles base path) rather than hardcoded `/experiments/foo.png` strings. Existing gallery code likely already does this — copy the pattern.
**Confidence:** HIGH.

### 8.3 Hot-reload with content collections

**Risk:** Astro hot-reload sometimes misses content-collection changes — adding/changing a hypothesis in the manifest may require a full server restart during dev. Annoying but not blocking.
**Mitigation:** Document the workflow ("if you change manifest.yml, restart `npm run dev`"). Not worth fighting for MVP.
**Confidence:** MEDIUM (anecdotal, not measured here).

### 8.4 Astro version

**Audited:** `site/node_modules/astro/package.json` reports **5.18.1**. Modern, supports content collections via the new content-layer API. No upgrade needed.
**Confidence:** HIGH.

---

## 9. Environment Audit

All commands run on 2026-05-10 from the worktree at `/root/workspace/.worktrees/29-design-experimentation-mvp-pairwise-voting-on-variations`.

### 9.1 Core tooling

| Tool | Path | Version | Status |
|---|---|---|---|
| `python3` | `/usr/bin/python3` | **3.13.5** | OK |
| `python` | — | — | **Missing** (only `python3` symlink). Scripts must use `#!/usr/bin/env python3` or explicit `python3` in shebangs. |
| `node` | `/usr/local/bin/node` | **v26.0.0** | OK |
| `npm` | `/usr/local/bin/npm` | **11.12.1** | OK |
| `scribus` | `/usr/bin/scribus` | (Qt error in non-X env) | OK headlessly via `xvfb-run` (existing pattern in `tools/render.py:56`) |
| `xvfb-run` | `/usr/bin/xvfb-run` | present | OK — required for Scribus headless |
| `gh` | `/usr/bin/gh` | **2.92.0 (2026-04-28)** | OK |
| `issue-cli` | `/usr/local/bin/issue-cli` | (subcommands: worktree, store, config, validate, naming, sync, pr, slugify, review-exec) | OK |
| `docker` | — | — | **Missing** — not needed for MVP since rendering runs locally in this dev container |
| `claude` (Claude Code CLI) | `/root/.local/bin/claude` | **2.1.132** | OK — viable LLM access route given no API keys in env |

### 9.2 Python packages relevant to MVP

```
$ python3 -c "import anthropic"        → ModuleNotFoundError
$ python3 -c "import openai"           → ModuleNotFoundError
$ python3 -c "import google.generativeai" → ModuleNotFoundError
$ python3 -c "import yaml"             → pyyaml 6.0.3   ✓
$ python3 -c "import jinja2"           → ModuleNotFoundError
$ python3 -c "import PIL"              → Pillow 12.2.0  ✓
$ python3 -c "import click"            → ModuleNotFoundError
```

**No virtual environments at `.venv`, `venv`, or `build/.venv`.** All Python runs use system `python3` directly. Existing tools (`tools/sla_lib`, `tools/render.py`, `tools/gallery_build.py`) work with this minimal set (`pyyaml`, `Pillow`, plus the local `sla_lib` package).

**Implication for MVP:** if hypothesis generation uses Python LLM SDKs, install will be needed. Avoid by routing through the `claude` CLI as a subprocess (per §7.5). For results aggregation, `pyyaml` + stdlib `json` are sufficient — no new deps.

### 9.3 Brand fonts

```
$ fc-list | grep -ciE 'gotham narrow|vollkorn'  → 42
```

42 brand-font face entries registered in fontconfig at `/usr/local/share/fonts/gruene/`. Includes:
- Gotham Narrow Ultra, Book, Medium, Bold, Black, Light, Thin (+ italics)
- Vollkorn Regular, Bold, ExtraBold, Black, Italic variants (static + variable)

**Verdict:** brand fonts are present and discoverable — Scribus rendering will use them, no DejaVu fallback. The `fc-list | grep -ciE 'gotham narrow|vollkorn' >= 30` gate from `bin/render-gallery` (archived issue #4) passes comfortably.
**Confidence:** HIGH.

### 9.4 Astro site

- `/root/workspace/site/package.json` — `astro@^5.0.0`
- `/root/workspace/site/node_modules/astro/package.json` — installed version `5.18.1`
- `/root/workspace/site/src/content.config.ts` — single `templates` collection via glob loader; **no `experiments` collection yet** (would need to be added)
- `/root/workspace/site/src/pages/` — `index.astro`, `templates/[...id].astro` (catch-all for templates); **no `experiments/` route yet**
- `/root/workspace/site/dist/` exists (last build present)

**Verdict:** Astro project is healthy. Adding `experiments` collection + routes is greenfield, not retrofit.

### 9.5 LLM API access

```
ANTHROPIC_API_KEY: UNSET
OPENAI_API_KEY: UNSET
GEMINI_API_KEY: UNSET
GOOGLE_API_KEY: UNSET
.env files: none in /root/workspace
grep -rE "ANTHROPIC_API_KEY|OPENAI_API_KEY" tools/ bin/ → no matches
```

**Verdict:** The repo has no existing LLM-key pattern. The viable MVP routes are (in order):
1. `claude` CLI subprocess (already authenticated; Claude Code v2.1.132 at `/root/.local/bin/claude`)
2. `issue:review` external-LLM tooling (mentioned in CONTEXT.md decision #6 as an option for the second model — exists in the workflow per the issue-cli `review-exec` subcommand)
3. Adding a Python SDK + `.env` pattern (only if 1 and 2 are insufficient — this introduces key management)

**Recommendation:** Planner should anchor on (1) + (2) for MVP and avoid (3).

### 9.6 Falzflyer template + build pipeline

- `templates/kandidat-falzflyer-din-lang/build.py` — exists, P2 panel logic at lines ~432–505 (verified by reading lines 425–510). Currently emits a 5-Schlagwort list ("Klimaplan jetzt." / "Leistbares Wohnen." / etc.) on a Hellgrün backing — this is exactly the §2.1/§8 "even-spaced peer list" failure mode the experiment targets.
- `tools/sla_lib/` — DSL with `Brand`, `Document`, `TextFrame`, `ImageFrame`, `Polygon`, `Run`, `ParaStyle`, `aligned_below`, etc. Variants will compose against this same DSL.
- `tools/render.py` — Scribus headless via `xvfb-run`. Variant rendering can reuse this.
- `tools/gallery_build.py` — copy-only build step that consumes committed PDFs/PNGs. Variant pipeline must commit rendered PNGs into the right place before `astro build` runs.
- `bin/render-gallery` — orchestrator. Variant rendering needs an analogous `bin/experiment-render` (CONTEXT.md "Tooling layout" already anticipates this).
- **`/root/workspace/experiments/` does NOT exist yet** — this directory will be created by the MVP.

**Confidence:** HIGH (all paths verified by direct inspection).

### 9.7 Missing tooling — remediation summary

| Missing | Required for MVP? | Remediation |
|---|---|---|
| `anthropic` Python SDK | **No** if using `claude` CLI subprocess | `pip3 install anthropic` only if planner picks SDK route |
| `openai` Python SDK | No | only if Codex/GPT generation chosen and SDK preferred over CLI |
| `jinja2` | No | only if templating is needed for prompts; `str.format` is sufficient |
| `click` | No | argparse (stdlib) is fine, matches existing tools |
| `docker` | No | not used by render pipeline |
| `python` symlink | No | use `python3` explicitly |
| LLM API keys | **Depends** | use `claude` CLI to avoid key management entirely |

**No blocker.** Everything required by CONTEXT.md decisions exists; SDK-vs-CLI for LLM access is a planner decision, not a missing dependency.

---

## 10. Test / Verification Gaps

### 10.1 What the acceptance criteria require

- [ ] **"Captured corpus updates from running this MVP experiment at least once with Flo as rater"** — this is mandatory in CONTEXT.md decision #11. The deliverable is *not* the tooling alone; it's tooling + at least one completed run + corpus updates committed.

### 10.2 Automated tests (low cost, high value)

| Layer | Test | Why |
|---|---|---|
| Unit | `compute_wins_ratio(votes_per_axis)` returns correct ranking for synthetic ballots | Math must be right; trivially testable |
| Unit | Disagreement-index calc — synthetic case with known A/T splits | Math must be right |
| Unit | Schema validator for hypothesis-LLM output — accepts valid, rejects malformed | Pipeline robustness |
| Unit | Manifest YAML round-trip (load → modify → save → reload) | Catches subtle YAML quirks |
| Integration | "render one variant end-to-end" — invokes `tools/render.py`, asserts PNG exists at expected path with non-zero size | Catches Scribus / xvfb regressions |
| Integration | `inside_page` validation passes for every variant in the experiment | Prevents archived-issue-#16-style overflow bugs |
| Integration | `astro build` succeeds with the experiments collection populated | Catches Astro schema errors |

### 10.3 Inherently manual

- The actual voting (Flo as rater) — cannot be automated
- The corpus update interpreting the ranking — interpretation requires Flo's design judgment
- "Are these hypotheses *actually* structurally distinct?" — best handled by Flo eyeballing the manifest before voting

### 10.4 End-to-end validation gate

**Risk:** Easy to ship "the system works" without ever running it. The corpus-update deliverable is the gate that prevents this.
**Mitigation:**
- The PR for issue #29 is not mergeable until `design-guide/gruene-corpus.md` has been amended with this experiment's outcomes (top-3 + bottom-3 + provenance).
- The `experiments/<id>/results-flo-<date>.json` file is committed alongside the corpus update — the JSON is the audit trail.
- A "Done" checklist on the issue must include: (a) tooling tests pass, (b) one experiment ran end-to-end, (c) corpus updated with provenance, (d) results JSON committed.
**Confidence:** HIGH.

---

## 11. Security / Privacy

### 11.1 Rater identity in JSON

**Risk:** CONTEXT.md decision #10 includes "rater identity (free text, can be anonymous)" in the JSON. If results are shared (even just committed to the repo, since this is a public Grüne workspace), the rater's name leaks.
**Mitigation:**
- Make the rater-identity field **optional and free-form** (already the design — "can be anonymous"). UI should default to empty and show a hint "leave blank for anonymous; use a handle if you want to merge results across sessions later."
- Document a "redact before sharing" step in the workflow: if the JSON is committed to the public repo, scrub identifying info first. A simple `tools/results_redact.py` could replace the rater field with a hash for public sharing while preserving cross-session tracking.
- For MVP single-rater with just Flo, this is low-risk — Flo is the maintainer and the public-repo author. Document for phase-2 multi-rater.
**Confidence:** HIGH.

### 11.2 localStorage scope

**Note:** localStorage is per-origin and not transmitted with HTTP requests. Safe for vote storage. No CSRF or XSS-relevant data flows out of localStorage as long as the export is a manual user-initiated download. **No mitigation needed beyond standard XSS hygiene** in the Astro voting page (don't `innerHTML` user input; use `textContent` or Astro's safe-by-default rendering).
**Confidence:** HIGH.

### 11.3 LLM API key handling

**Existing pattern:** None. See §7.5 and §9.5 — no `.env`, no environment-set keys, no SDK references in `tools/` or `bin/`.
**Surfaced as:** Tier-1 question for planner. Recommend `claude` CLI subprocess to avoid introducing key management.
**Confidence:** HIGH on the gap; MEDIUM on the recommended mitigation (planner should verify).

---

## 12. Lessons from Archived Issues

Quick scan of `.issues/archive/` for relevant precedent:

| Archived issue | Lesson for MVP |
|---|---|
| **#3** Render-fidelity ground truth | Brand fonts (Gotham Narrow) cannot be in CI for licensing — local-only render. Variant rendering must run locally. |
| **#4** Local render pipeline that commits artifacts | The pipeline pattern is: build → render → rasterize → commit → Astro reads committed bytes. Variants must follow this exact pattern; do not render at Astro build time. The `fc-list \| grep -ciE 'gotham narrow\|vollkorn' >= 30` gate is the guard against accidental DejaVu fallback. |
| **#11** Demo-Bilder via Codex | Demo images committed as bytes, not generated each run. Variant PNGs follow the same convention — render once, commit. |
| **#12** Spec system v2 — constraint DSL | Variants must declare their geometry via the existing constraint DSL; spec_check must pass. |
| **#14** `inside_page`, `aligned_below`, SpreadImage utility | The geometric-validity primitives variants must respect. |
| **#16** Zeitung A4 frames past page boundary | Polygon/frame coords past page bounds silently spill into adjacent panels. **Every P2 variant must `inside_page`-validate against panel bounds (x=99..198, y=0..213).** Don't skip this gate "because it's just an experiment." |
| **#22** Alignment system v2 | Spine-safety + undeclared-drift detection apply to variants too. |
| **#23 / #24** Stricter alignment validation; image content doesn't fill frame | Variants that abandon the existing alignment system need explicit declaration; don't drift silently. |
| **#26** Falzflyer symmetric thema panels + Hellgrün bar fix | The current P2 baseline (the "even-spaced peer list" of 5 Schlagworte) is exactly the failure the experiment targets — confirms experiment subject choice. |
| **#27** Falzflyer redesign — bund logo + full-bleed portrait + 1-thema-per-panel | Recent bias is toward "1-thema-per-panel" commitment — hypothesis generation should be aware that this is a *recently surfaced* design value, and at least one variant should test "explicit 1-thing-on-P2" against the existing 5-Schlagwort list. |

**No archived issue contradicts the MVP design.** Several reinforce specific decisions (rendering pipeline, structural-check gates, fonts).

---

## Top 5 Pitfalls to Address in MVP (Prioritised)

1. **Hypothesis "structural distinctness" is the central failure mode.** If 10 variations turn out to be 3 hypothesis families × 3 parameter tweaks, the MVP produces a confidence-creating local optimum and the system is *worse than nothing*. Mitigation must be designed in, not bolted on: positive+negative examples in prompts, mandatory commitment-axis taxonomy, multi-LLM with diverse role priming, post-generation distinctness validation, and at least one wild-card hypothesis per experiment. **Verify before voting.**

2. **`inside_page` and structural-check gates must apply to variants.** Archived issue #16 showed that frame-overflow bugs render silently. Tournament voting on a variant that has accidental geometry drift means voting on bugs, not design. Each variant must pass the existing `inside_page` + `audit_alignment` + `spec_check` gates before entering the bag. Failed variants are dropped from the experiment with a clear log message.

3. **localStorage is fragile; export-as-you-go must be visible.** Private/incognito mode wipes on close; Safari ITP evicts after 7 days; users clear data. The vote data is small enough that the rater downloading partial JSON every session is the right pattern. UI must surface "Export progress" prominently, not bury it in a settings menu. The JSON file is the durable record; localStorage is only convenience.

4. **Two-axis disagreement is the signal, not noise — never compute a composite ranking.** The MVP must produce two separate rankings (appeal + transport) and a disagreement index, never a weighted average. Auto-resolution would erase the very corpus-update content the system was built to surface ("this variant is appealing but doesn't transport well — visual signature: …" is exactly the kind of corpus entry that justifies the system existing).

5. **The corpus-update deliverable is the verification gate, not a nice-to-have.** Without an actual run feeding top-3 + bottom-3 back into `design-guide/gruene-corpus.md`, the issue is incomplete. The PR is not mergeable until the corpus is amended with provenance and the results JSON is committed alongside. A done-checklist on the issue should make this explicit so the feedback loop is proven, not just built.

---

## Sources

### HIGH confidence
- Direct repo inspection: `templates/kandidat-falzflyer-din-lang/build.py`, `tools/render.py`, `tools/gallery_build.py`, `site/package.json`, `site/src/content.config.ts`
- Archived issues: `.issues/archive/3-…`, `…/4-…`, `…/11-…`, `…/14-…`, `…/16-…`, `…/22-…`, `…/26-…`, `…/27-…`
- Direct env audit: shell commands run on 2026-05-10 (see §9)
- `design-guide/README.md` and `design-guide/gruene-corpus.md` §6, §8, §9
- Astro 5 official docs: [Content Collections](https://docs.astro.build/en/guides/content-collections/), [Astro 5.0 announcement](https://astro.build/blog/astro-5/)
- WebKit ITP storage policy: [Updates to Storage Policy (WebKit)](https://webkit.org/blog/14403/), [MDN Storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)

### MEDIUM confidence
- Position bias in pairwise judgment: ["Judging the Judges" (COLM 2025, arXiv 2406.07791v5)](https://arxiv.org/html/2406.07791v5), [A Systematic Study of Position Bias in LLM-as-a-Judge (IJCNLP 2025)](https://aclanthology.org/2025.ijcnlp-long.18.pdf) — both are LLM-judge-focused but the "randomize + log" mitigation generalises
- Halo-effect on simultaneous multi-criterion rating: [Effects of rating criteria order on halo (Jeon & Lee, *Language Testing in Asia* 2020)](https://link.springer.com/article/10.1186/s40468-020-00115-0), [A Constant Error, Revisited (PMC 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11614318/)
- Mode collapse in LLM generation: [Diversity Collapse (arXiv 2505.18949, 2025)](https://arxiv.org/html/2505.18949v1), [Verbalized Sampling (arXiv 2510.01171, 2025)](https://arxiv.org/html/2510.01171v1)
- Pairwise comparison fatigue / scalability: [Pairwise Comparison (1000minds)](https://www.1000minds.com/decision-making/pairwise-comparison), [Bramley — Paired Comparison Methods (UK gov, 2007)](https://assets.publishing.service.gov.uk/media/5a80d75940f0b62305b8d734/2007-comparability-exam-standards-i-chapter7.pdf)
- Multi-armed bandit / exploration vs exploitation: [Multi-armed bandit (Wikipedia)](https://en.wikipedia.org/wiki/Multi-armed_bandit), [AB Tasty — MAB guide](https://www.abtasty.com/glossary/multi-armed-bandit/)

### LOW confidence (needs validation)
- The "30–50 pair fatigue inflection" is convention rather than measured-here
- The Astro hot-reload "missed content-collection changes" claim is anecdotal — not verified against a current 5.18.1 changelog
- The 5–10 percentage-point human position bias estimate is order-of-magnitude only; specific magnitude depends on the rater pool and stimulus type

---

## Metadata

**Research date:** 2026-05-10
**Issue:** 29 — Design experimentation MVP — pairwise voting on variations to grow the design corpus
**Slug:** `29-design-experimentation-mvp-pairwise-voting-on-variations`
**Sub-agent:** PITFALLS
**Output file:** `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/research/pitfalls.md`
