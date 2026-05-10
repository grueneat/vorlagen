# Codebase Research — Issue #30 (constraint envelope + experiments skill v2)

Worktree root: `/root/workspace/.worktrees/30-constraint-envelope-tooling-experiments-skill-v2-run/`. All file:line citations are relative to that root.

Scope decision (HIGH): issue #29's tooling has shipped *into this worktree* (the worktree's branch carries it) but is NOT yet merged to `main` — `main`'s `tools/` has no `experiment_*.py` and no `experiments/` directory (verified via `git log --oneline` showing latest commit is `64b002a 28: Gallery clickable hi-res preview thumbnails`). For research and planning purposes, we treat the worktree's own `tools/experiment_*.py`, `experiments/_schema/`, and `experiments/falzflyer-p2-mein-plan/` as the available baseline, because that is the state the v2 work composes on top of. PR #59 is the upstream merge bringing #29 into main.

---

## 1. `tools/sla_lib/builder/brand_constraints.py` — the 16 BRAND_CONSTRAINTS

File is 1681 lines. Module docstring at lines 1–43 enumerates exactly 16 rules (HIGH confidence, count matches CONTEXT decision 1). Registry at `BRAND_CONSTRAINTS = [...]` lines 1525–1680.

**Core type** (`brand_constraints.py:64–87`):

```python
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"
    def check(self, primitives: list, doc, constraints=None) -> list:
        # returns list[Violation]
```

`Violation` is imported from `.constraints` (`brand_constraints.py:56`); shape includes `severity`, `rule_id`, `message`, `targets` (used at `structural_check.py:107–112`). HIGH confidence on signature.

**The 16 rules** (id → registry line → implementation class line):

| # | rule id | registry line | impl class line | severity (registry default) | floor for v2? |
|---|---------|--------------|-----------------|-----------------------------|---------------|
| 1 | `brand:color_palette` | 1526 | `_ColorPaletteRule` 117 | error | yes |
| 2 | `brand:font_family` | 1533 | `_FontFamilyRule` 140 | error | yes |
| 3 | `brand:line_spacing_0.9` | 1539 | `_LineSpacingRule` 172 | error | yes |
| 4 | `brand:hl_sl_distance_x2` | 1545 | `_HlSlDistanceRule` 199 | error | yes |
| 5 | `brand:logo_size_3M` | 1551 | `_LogoSize3MRule` 249 | error | yes (named in ISSUE.md §B) |
| 6 | `brand:text_on_green` | 1557 | `_TextOnGreenRule` 286 | error | yes (named in ISSUE.md §B) |
| 7 | `brand:bleed_3mm` | 1563 | `_Bleed3mmRule` 326 | error | yes (named in ISSUE.md §B) |
| 8 | `brand:wahlkreuz_colored_bg` | 1569 | `_WahlkreuzColoredBgRule` 347 | error | yes |
| 9 | `brand:inside_page` | 1575 | `_InsidePageRule` 388 | error | yes (named — already enforced today) |
| 10 | `brand:spine_safety` | 1582 | `_SpineSafetyRule` 482 | warning | yes (warning-only, but still enforced) |
| 11 | `brand:bleed_coverage` | 1593 | `_BleedCoverageRule` 608 | error | yes |
| 12 | `brand:image_text_overlap` | 1606 | `_ImageTextOverlapRule` 731 | error | yes |
| 13 | `brand:cover_extent_match` | 1617 | `_CoverExtentMatchRule` 825 | warning | yes (named in ISSUE.md §B) |
| 14 | `brand:visual_adjacency_drift` | 1629 | `_VisualAdjacencyDriftRule` 900 | warning | likely (consult planner; warning) |
| 15 | `brand:image_fills_frame` | 1644 | `_ImageFillsFrameRule` 1062 | error (dynamic) | yes |
| 16 | `brand:band_consistency` | 1666 | `_BandConsistencyRule` 1341 | error | yes (named in ISSUE.md §B) |

CONTEXT decision 1 says **all 16** are floor by default; per-experiment `constraints.yml` may name relaxations explicitly.

**Today's invocation pattern** (`structural_check.py:166–204`): orchestrator imports `from .brand_constraints import BRAND_CONSTRAINTS`, then for each `rule` in the list calls `rule.check(primitives, doc, constraints=constraint_list)`. Skip-list comes from `meta.yml::brand_overrides` via `meta_schema.load_brand_overrides(slug, root)` (`structural_check.py:168–172`). Rule check exceptions are caught and surfaced as `severity="error"` issues (`structural_check.py:191–196`).

<interfaces>
// tools/sla_lib/builder/brand_constraints.py
@dataclass(frozen=True)
class BrandRule:
    id: str
    name: str
    description: str
    severity: str = "error"  # "error" | "warning"
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]: ...

BRAND_CONSTRAINTS: list[BrandRule]  # the 16 frozen instances; registry order is stable.

// tools/sla_lib/builder/constraints.py — Violation shape used by every rule
@dataclass
class Violation:
    severity: str       # "error" | "warning"
    rule_id: str
    message: str
    targets: tuple[str, ...] = ()
</interfaces>

---

## 2. `tools/sla_lib/builder/structural_check.py` — the existing CI gate

File: 297 lines. Read end-to-end. Entry point: `check_template(slug, root) -> TemplateReport` (`structural_check.py:118`). Orchestrator imports template's `build.py`, calls `build_doc()`, walks primitives, runs CONSTRAINTS list then BRAND_CONSTRAINTS minus override skip-list.

Key pattern the planner will mirror (CONTEXT decision 13 says envelope-gating in `experiment_render.py` should "mirror the inside_page drop pattern"):

```python
# structural_check.py:183–203 — the loop variants must mirror
for rule in BRAND_CONSTRAINTS:
    if rule.id in skip_ids:                          # ← per-template skip
        rep.skipped_brand_rules.append((rule.id, reason))
        continue
    try:
        violations = rule.check(primitives, doc, constraints=constraint_list)
    except Exception as e:
        rep.brand_issues.append(CheckIssue(severity="error", ..., message=f"rule check raised: {e!r}"))
        continue
    if not violations:
        rep.brand_issues.append(CheckIssue(severity="pass", rule_id=rule.id, message="ok"))
    else:
        for v in violations:
            rep.brand_issues.append(_violation_to_issue(v, rule.id))
```

`CheckIssue` (`structural_check.py:44–50`): `severity` ∈ {"error","warning","info","pass","skip"}, `rule_id`, `message`, `location`. `TemplateReport.has_errors` walks all issues and returns true on any `severity == "error"` (`structural_check.py:62–68`).

`_inside_page` is NOT a separate function in `structural_check.py` — `inside_page` is just one rule among the 16, and structural_check fires it via the same `for rule in BRAND_CONSTRAINTS` loop. The "inside_page drop pattern" as referenced in CONTEXT decision 13 actually lives in `tools/experiment_render.py` (next section), not in `structural_check.py`.

---

## 3. `tools/experiment_render.py` — the existing variant render gate

File: 394 lines. Read end-to-end. Today it gates only on `brand:inside_page` per the wrong CONTEXT decision #4 from issue #29 (see §8 below).

**The current gate to mirror & extend**:

```python
# tools/experiment_render.py:130–143
def _inside_page_violations(doc) -> list:
    from sla_lib.builder import BRAND_CONSTRAINTS
    rule = next((r for r in BRAND_CONSTRAINTS if r.id == "brand:inside_page"), None)
    if rule is None:
        return []
    primitives = list(doc.iter_all_primitives()) if hasattr(doc, "iter_all_primitives") else []
    return [v for v in rule.check(primitives, doc) if v.severity == "error"]
```

**Per-variant pipeline** (`experiment_render.py:150–208`, function `_build_variant_sla`):

1. Load variant module: `_load_variant_module(...)` (`exp_render.py:89–112`). Variants must expose `render_p2(doc, page) -> None`.
2. Build doc: `doc = scaffold.build_variant_front(variant_module.render_p2)` (`exp_render.py:164`).
3. Run gate: `violations = _inside_page_violations(doc)` (`exp_render.py:165`). If non-empty → return; caller drops.
4. Save SLA: `doc.save(sla_path)` (`exp_render.py:170`).

**Drop loop in `run_render`** (`experiment_render.py:289–303`):

```python
for h in hypotheses:
    slug = h["slug"]
    try:
        sla_path, violations = _build_variant_sla(hypothesis=h, exp_dir=exp_dir, scaffold=scaffold)
    except Exception as e:
        print(f"DROP {slug}: build error — {e}", file=sys.stderr)
        dropped.append((slug, f"build error: {e}"))
        continue
    if violations:
        messages = "; ".join(v.message for v in violations[:3])
        print(f"DROP {slug}: inside_page — {messages}", file=sys.stderr)
        dropped.append((slug, f"inside_page: {messages}"))
        continue
    # ... raster + mirror to public ...
```

**Drop manifest output** (`experiment_render.py:337–341` — confirms CONTEXT decision 14 shape):

```python
manifest_out["_dropped"] = [
    {"slug": s, "reason": r} for (s, r) in dropped
]
(exp_dir / "manifest.json").write_text(json.dumps(manifest_out, indent=2, ensure_ascii=False), encoding="utf-8")
```

So `_dropped` today is `list[{slug:str, reason:str}]`. v2 needs to extend `reason` with structured `violations: [...]` per CONTEXT 14 — minor schema bump in `experiments/_schema/manifest.schema.yaml`. The frontmatter writer already strips `_dropped` from the Astro page (`experiment_render.py:351`), so SUMMARY.md surfacing happens elsewhere (in `tools/experiment_results.py` → see §10).

**Scribus gate already in place** before render (`experiment_render.py:270–272`): `if not skip_fonts_check: _verify_brand_fonts()`. The discretion question "must envelope check come after `_verify_brand_fonts()`?" — yes, the existing pre-Scribus gate runs at `run_render` line 271, well before the per-variant loop, so envelope checks at line ~292 already inherit that ordering.

**Slot for the envelope gate**: replace the `_inside_page_violations(doc)` call at `experiment_render.py:165` with `_envelope_violations(doc, envelope)` where `envelope` is loaded once per run from the experiment's `constraints.yml` (per §11 below). Keep the function-level seam — the unit-test escape hatch `skip_scribus` (`experiment_render.py:248,305`) exercises the pre-Scribus pipeline including the gate, so the gate must stay pre-Scribus.

<interfaces>
// tools/experiment_render.py — public surface
def run_render(*, exp_id: str, only: str | None = None,
               skip_fonts_check: bool = False, skip_scribus: bool = False) -> int

def _build_variant_sla(*, hypothesis: dict, exp_dir: Path, scaffold) -> tuple[Path, list[Violation]]
def _inside_page_violations(doc) -> list[Violation]   # ← REPLACE / RENAME for envelope
def _load_variant_module(exp_dir, hypothesis, scaffold_module) -> ModuleType
def _load_scaffold() -> ModuleType
def _render_variant_pngs(*, sla_path: Path, variant_dir: Path) -> tuple[Path, Path]
def _mirror_to_public(variant_dir: Path, public_dir: Path) -> None

# Constants
ROOT = Path(__file__).resolve().parent.parent
PREVIEW_DPI = 100
SCHEMA_PATH = ROOT / "experiments" / "_schema" / "manifest.schema.yaml"
VARIANT_SCAFFOLD_PATH = ROOT / "templates" / "kandidat-falzflyer-din-lang" / "variant_scaffold.py"

# Exit codes used today: 0 ok, 3 brand-fonts gate failed, 4 manifest schema invalid,
# 5 variant module load error in --only mode. v2 may want a 6 for "all variants
# violated envelope" — TBD by planner.
</interfaces>

---

## 4. `tools/experiment_hypothesis_gen.py` + `tools/experiment_generate/prompt_template.md`

File: 649 lines. Read end-to-end. Prompt template: 107 lines (read end-to-end).

**Existing prompt-render path** (`experiment_hypothesis_gen.py:84–95`):

```python
def render_prompt(template: str, subject: str, weak_area_quote: str) -> str:
    # Two-step escape: protect literal braces, restore the named tokens.
    tokens = ("subject", "weak_area_quote")
    safe = template.replace("{", "{{").replace("}", "}}")
    for tok in tokens:
        safe = safe.replace("{{" + tok + "}}", "{" + tok + "}")
    return safe.format(subject=subject, weak_area_quote=weak_area_quote)
```

So the substitution surface today is exactly two named tokens: `{subject}` and `{weak_area_quote}`. v2 adds new tokens — minimum two — `{constraint_envelope}` and `{v1_anti_examples}`. Add them to the `tokens` tuple at line 91 and to the `render_prompt` call sites (`experiment_hypothesis_gen.py:507–508`, `:528`).

**Where the prompt is composed** (`experiment_hypothesis_gen.py:506–528`):

```python
template = prompt_path.read_text(encoding="utf-8")
base_prompt = render_prompt(template, subject=subject, weak_area_quote=weak_area_quote)
pv = _prompt_version(template)
# ... for each LLM ...
role = ROLE_PRIMING.get(llm, "")
prompt = f"{role}\n\n{base_prompt}\n\nRespond with a JSON array of hypothesis objects."
```

`_prompt_version` (`experiment_hypothesis_gen.py:473–474`) hashes the **template** text only, not the substituted prompt. v2 should change the template (so the hash bumps automatically), and probably extend the version line to embed the constraints-yml hash too — discretion for the planner.

**Envelope-loading touchpoint**: a new helper, e.g. `_load_envelope(exp_dir: Path) -> dict` reading `experiments/<exp>/constraints.yml` → format as Markdown via a renderer like `_format_envelope_markdown(env: dict) -> str`. Both run before `render_prompt` at line 507. The Markdown is what gets substituted into the new `{constraint_envelope}` token.

**Existing prompt structure to extend without rewriting** (prompt_template.md):

| Section | lines | role |
|---------|-------|------|
| Preamble + role framing | 1–3 | identity |
| Subject + named failure mode | 5–13 | injects `{subject}`, `{weak_area_quote}` |
| What counts as structurally distinct | 15–29 | axis vocabulary (the `ALLOWED_AXES` set, `experiment_hypothesis_gen.py:231-235`) |
| Examples (good/bad) | 31–54 | inline anchors — NOT a menu |
| Anti-collapse instruction | 56–60 | Jaccard ≥0.6 enforcement (matches `AXIS_OVERLAP_JACCARD = 0.6`, `exp_hypothesis_gen.py:50`) |
| Mandatory wild-card | 62–64 | one-of-N |
| Output format (JSON shape) | 66–90 | strict |
| How many | 92–94 | 8–12 |
| Final check | 96–106 | self-review |

Cleanest extension points (preserving the existing structure):

- **Insert "Constraint envelope (HARD floor)" section between current §"What counts as structurally distinct" (line 29) and §"Examples" (line 31)** so envelope is upstream of examples and re-anchored in the final-check.
- **Insert "v1 anti-examples — DO NOT REPEAT" section between §"Examples" (after line 54) and §"Anti-collapse" (before line 56)** so anti-examples sit next to existing BAD list. Per CONTEXT discretion, prefer separate file `tools/experiment_generate/v1_anti_examples.md` referenced from the template via a new `{v1_anti_examples}` token, kept loadable by the python loader.
- **Add an envelope-aware bullet to "Final check"** (line 100): "6. Does every hypothesis respect the constraint envelope (margins ≥6mm, body ≥10pt, contrast ≥4.5:1, all 16 BRAND_CONSTRAINTS)?"

**`SUBJECT_METADATA`** (`experiment_hypothesis_gen.py:62–77`) — only `falzflyer-p2-mein-plan` is registered today. v2 will register `falzflyer-p2-mein-plan-v2` (or `falzflyer-p2-density-form` per CONTEXT discretion). The `target_weak_area` for v2 should reference §2.2 ("Information density discipline") per CONTEXT decision 7.

<interfaces>
// tools/experiment_hypothesis_gen.py
def render_prompt(template: str, subject: str, weak_area_quote: str) -> str
def run_generation(*, exp_id, subject, prompt_path, requested_llms, no_gemini,
                   n_target, runner_overrides=None) -> int
def build_manifest(*, exp_id, subject, target_weak_area, contributing_llms,
                   hypotheses, prompt_version, notes=None) -> dict
def normalise_hypothesis(raw: dict, source: str) -> dict | None
def merge_hypotheses(pool: list[dict]) -> list[dict]
def distinctness_warnings(merged: list[dict]) -> list[str]
def parse_llm_response(text: str) -> list[dict] | None
def extract_json_block(text: str) -> str | None
def validate_manifest(manifest: dict) -> list[jsonschema.ValidationError]
def write_manifest(manifest: dict, exp_dir: Path) -> tuple[Path, Path]

ALLOWED_AXES: set[str] = {
    "density", "hierarchy", "typography", "asymmetry",
    "photographic-vs-typographic", "accent-strategy",
    "whitespace-strategy", "voice-formality", "wildcard",
}
ROLE_PRIMING: dict[str, str] = {"claude": "...", "codex": "...", "gemini": "..."}
SUBJECT_METADATA: dict[str, dict[str, str]]    # add v2 entry here
LLM_TIMEOUT_S = 600
DEDUP_NAME_RATIO = 0.75
AXIS_OVERLAP_JACCARD = 0.6
DEFAULT_PROMPT_PATH = ROOT / "tools" / "experiment_generate" / "prompt_template.md"
</interfaces>

---

## 5. The 12 v1 variants — one-line description + envelope violation

All under `experiments/falzflyer-p2-mein-plan/variants/`. Each variant exports `render_p2(doc, page) -> None` and is invoked through `variant_scaffold.build_variant_front`. Failure-mode column inferred from variant code; planner / executor should re-verify against rendered PNGs at `experiments/falzflyer-p2-mein-plan/variants/<slug>/page-01.png` if they exist.

| slug | one-line description | likely envelope violation (anti-example tag) |
|------|----------------------|----------------------------------------------|
| asymmetric-editorial-rules | Left-aligned items + thin Dunkelgrün rules in the left two-thirds; right third intentional whitespace | Items at `x=105..160` width 55mm — verify negative-space discipline; the 0.4mm thin rule is decorative non-content polygon — `band_consistency` may flag it |
| cut-to-three-with-body | 3 items, each with a one-sentence explanatory body | `body ≥10pt` and line-length ≤75ch needs verification at chosen body size |
| first-person-commitments | "Ich werde…" first-person bullets | Density same as v1 even-spaced peer list — no hierarchy; `hl_sl_distance_x2` likely OK but bullets may be ≤10pt |
| handwritten-protest-aesthetic | Wildcard: handwritten-style margin notes overlay | likely `font_family` (non-brand font), `text_on_green` (margin notes off backing), `image_text_overlap` |
| luxurious-whitespace-two-items | 2 items, generous whitespace | only 2 items risks under-density; whitespace pattern likely OK |
| manifesto-single-statement | ONE 30pt Vollkorn Black manifesto sentence | `hl_sl_distance_x2` not applicable; check Vollkorn Black is a brand-listed font; line length per `body line length ≥45 chars` if treated as body |
| numbered-priority-list | Numbered 1..5 with thin Dunkelgrün rules between rows | `numeral` style at 28pt + `text` at 16pt — verify ≤3 type sizes per panel; thin rule polygons may trip `band_consistency` |
| quote-from-resident | Verbatim resident quote leads, candidate reply below | voice/typography mix — verify ≤2 type families |
| staggered-block-accent | Odd-indexed slogans on small Dunkelgrün blocks | `text_on_green` should be OK; `image_text_overlap` if blocks partially overlap text |
| vollkorn-italic-cornerstone | Vollkorn italic for one cornerstone slogan, rest Gotham | ≤2 type families OK if Gotham + Vollkorn count as 2; verify italic is in `shared/ci.yml::fonts` |
| weighted-hero-lead | One hero promise + four supporters in compact list | hierarchy executed via size jump — verify `headline ≥2.5×` body |
| yellow-accent-privileged-item | One item on Gelb backing, rest on Hellgrün | `non-green accents ≤2` OK; `text_on_green` rule applies — verify white-on-Gelb isn't used |

**Three retained concepts (CONTEXT decision 8)**:

- `numbered-priority-list.py` (read in full): two new para styles `exp/numbered/numeral` (Vollkorn Black Italic 28pt) and `exp/numbered/text` (Gotham Narrow Bold 16pt); 5 rows at `y0=70`, `row_h=26`, with thin 0.4mm Dunkelgrün polygons between rows except the last (`numbered-priority-list.py:75–80`). v2 retention requires "weighted scale per rank" — i.e. numerals shrink from #1 to #5; current code uses constant 28pt. Planner-level: change `fontsize` per index, derived from a published scale.
- `manifesto-single-statement.py` (read in full): one large `exp/manifesto/statement` para style at Vollkorn Black 30pt, single `Run` text "Mödling muss vorangehen — beim Klima, beim Wohnen, beim Zuhören.", placed at `x=105 y=72 w=87 h=120` (`manifesto-single-statement.py:51–58`). Includes a small Vollkorn Black 30pt body `h_mm=120` and a Gotham Narrow Book 10pt footer. v2 retention requires the **execution** corrected within envelope — i.e. confirm 30pt is ≥10pt body floor (yes, comfortably), confirm `h_mm=120` doesn't overrun the 213mm-tall panel (it doesn't: 72+120=192 < 213), confirm Vollkorn Black is in `shared/ci.yml`. Existing layout already respects most envelope constraints; the v1 issue was probably the Vollkorn weight + footer text-on-green compatibility, not basic geometry.
- `asymmetric-editorial-rules.py` (read in full): single para style `exp/editorial/item` (Gotham Narrow Bold 18pt), 5 rows at `y0=75 row_h=22`, items at `x=105 y=y w=55 h=14`, thin 0.4mm rules at `y+row_h-4` (`asymmetric-editorial-rules.py:55–72`). v2 retention requires the rule pattern but with proper margin to panel edge (currently x=105 means 6mm in from the inside edge of panel x=99, which is ≥6mm minimum margin — likely OK); the issue may have been that 5 items × 22mm row_h = 110mm of content with the right third unused, which is correct *intent* but the rendered image needs visual review.

---

## 6. Skill authoring conventions (`generate-skill` output shape)

`.claude/skills/` does NOT exist in the workspace root or in this worktree (`ls .claude/` returned `scheduled_tasks.lock` only). HIGH confidence: there's no local skill precedent. The global skills live at `/root/.claude/skills/<skill>/` (10 of them: `adf-author`, `containerize`, `generate-skill`, `git-committer`, `makefile`, `orchestrator`, `python`, `python-runner`, `terraform`, `work-summary`).

**`generate-skill` is the authoring tool.** Read in full at `/root/.claude/skills/generate-skill/SKILL.md`. Auto-activates on user signals "create a skill", "make a new skill". The 6-step workflow it produces:

1. Examples-first (2–5 concrete usage examples).
2. Plan structure with progressive disclosure: **Level 1** YAML frontmatter (~100 words), **Level 2** SKILL.md (≤5k words), **Level 3** bundled resources `scripts/`, `references/`, `assets/` (unlimited).
3. Initialize directory: `<root>/.claude/skills/<skill-name>/{SKILL.md, scripts/, references/, assets/}`.
4. Edit using imperative style ("To do X, do Y"), bundled resources in subdirs.
5. Validation: `wc -w SKILL.md` ≤5k words, YAML frontmatter complete, 1-level-deep references only.
6. Iterate.

**Mandatory YAML frontmatter shape** (from `/root/.claude/skills/generate-skill/SKILL.md:1-5`):

```yaml
---
name: skill-name              # lowercase, hyphens, gerund preferred
description: Comprehensive description (what + when + auto-activation cues)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob   # subset of available tools
---
```

**Mandatory step in `generate-skill`** (lines 7–25): WebFetch `https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices` BEFORE any skill work. Planner should specify the executor performs this fetch as the first task.

**Multi-verb dispatch (`/experiments new`, `/experiments generate`, etc.)**: I found no documented convention for slash-command sub-verbs in either the global skills or the workspace-local `.claude/`. MEDIUM-LOW confidence on the exact mechanism. Worth checking via the WebFetch in step 1 of `generate-skill`. From inspection of `/root/.claude/skills/orchestrator/SKILL.md` and `/root/.claude/skills/work-summary/SKILL.md` (both read for pattern hunting), the pattern is: SKILL.md describes a workflow, and Claude reads the user's `/<skill>` invocation + first argument. The skill's body branches on the first positional argument (e.g. "if user says `/experiments new`, do A; if `/experiments generate`, do B"). This is a soft convention, not a hard one — confirmation needed during planning.

**Recommendation for the planner**: don't try to invent a new dispatch pattern. Author the skill so its SKILL.md explicitly enumerates the four subcommands (`new`, `generate`, `render`, `capture`) with a "when invoked as `/experiments <verb>`, do ..." section per CONTEXT decision 10. Each subcommand body dispatches to the existing `bin/experiment-*` tool already shipped. Multi-verb dispatch is just imperative branching in SKILL.md; there's no plugin API to register against (HIGH confidence — no such API was found in any of the existing global skills).

---

## 7. `design-guide/README.md` — Layer-1 deterministic rules table

File: 102 lines. Read end-to-end. Layer-1 table at lines 24–46. Below is the verbatim mapping the planner should transform into `experiments/_constraints/falzflyer-default.yml`. Source citations are the README's own column.

| rule key | threshold | source |
|---|---|---|
| body_min_pt | ≥10 (prefer 11) | hcd #12 |
| caption_impressum_min_pt | ≥8 | hcd #12 |
| body_line_length_chars | 45–75 (66 ideal) | hcd #11 |
| headline_size_jump_x | ≥2.5× | hcd #10 |
| headline_max_words | ≤7 (~35 chars) | hcd #9 |
| body_contrast_ratio | ≥4.5:1 | hcd #13 |
| display_contrast_ratio_18pt_plus | ≥3:1 | hcd #13 |
| type_families_per_panel | ≤2 | hcd #5 |
| type_sizes_per_panel | ≤3 | hcd #5 |
| alignment_systems_per_panel | ≤2 | hcd #22 |
| negative_space_pct | ≥30 | hcd #3 |
| dominant_element_optical_weight_pct | ≥40 | hcd #1 |
| face_crop_fill_pct | ≥60 (when face is primary) | hcd #8 |
| ctas_per_panel | exactly 1 (if any) | hcd #14 |
| non_green_accent_colors_per_piece | ≤2 | hcd #6 |
| forbidden_primary_colors | SPD-red, AfD/CDU-blue, FDP-yellow-saturated, Linke-magenta | hcd #6 |
| margin_M_formula | M = 0.06 × short_edge_of_trim | CD-Quickguide |
| logo_size_print | 3 × M | CD-Quickguide |
| logo_size_digital | 2.5 × M | CD-Quickguide |
| logo_clear_space | 1 × M each side | CD-Quickguide |
| type_on_white_plate_forbidden | true | CD-Quickguide §7 |
| brand_colors_only | {Dunkelgrün, Hellgrün, Gelb, Magenta} | CD-Quickguide |

That is **22 rows total** (21 design-rules + the 5 CD-Quickguide rules where the last 5 overlap into the table). Issue prose says "21-row table" and CONTEXT decision 3 says "21-row table". Counting the table in the source: 16 hcd rows + 6 CD-Quickguide rows = **22 rows**. MEDIUM-confidence note: there is a one-row discrepancy between the issue prose and the actual file. Planner should pick a count and document the choice; I'd recommend referencing "the Layer-1 table at design-guide/README.md:24-46" so the count is unambiguous.

Several of these directly mirror existing BRAND_CONSTRAINTS (e.g. brand_colors_only ↔ `brand:color_palette`; type-on-white-plate-forbidden ↔ `brand:text_on_green`; logo_size_print ↔ `brand:logo_size_3M`). The envelope yaml should reference the existing rule id where one exists, only adding NEW thresholds that the brand_constraints code doesn't yet enforce (body_min_pt, body_line_length_chars, headline_size_jump_x, headline_max_words, contrast ratios, type_families_per_panel, type_sizes_per_panel, alignment_systems_per_panel, negative_space_pct). The latter list is likely the "new envelope rules to implement" set for the planner.

---

## 8. The wrong CONTEXT decision #4 from issue #29 — exact wording

**Important**: scanning #29's CONTEXT.md showed no numbered "decision 4" matching the issue prose. Issue #30's prose says CONTEXT.md decision #4 said "don't run BRAND_CONSTRAINTS on variants…" — but #29's CONTEXT.md has no such bullet. The actual wrong framing lives in **#29's RESEARCH.md and PLAN.md** as "resolved uncertainty 4". HIGH confidence on the locations:

- `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/RESEARCH.md:248`:
  > Recommendation from codebase research: variants are research artifacts; *don't* run `BRAND_CONSTRAINTS` (some hypotheses deliberately violate brand rules — that's a feature). Planner's call to confirm policy.

- `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/RESEARCH.md:268`:
  > 4. **Brand-rule enforcement on variants.** Recommendation: variants are research artifacts; don't run `BRAND_CONSTRAINTS` per-variant; do run `inside_page` and structural alignment.

- `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/PLAN.md:33`:
  > 4. **Brand-rule enforcement on variants:** Run `inside_page` and structural alignment checks (`audit_alignment` if it can be invoked programmatically — else just `inside_page`). Do NOT run `BRAND_CONSTRAINTS` on variants. Rationale: variants are research artifacts and some hypotheses (e.g., asymmetric-balance, italic-emphasis) deliberately violate brand rules — that's the point. A failed variant is dropped from the bag with a clear log message; voting only happens on variants that fit on the page.

- `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/PLAN.md:229`:
  > Add a docstring noting that `BRAND_CONSTRAINTS` are NOT auto-applied (per resolved uncertainty #4) and that `inside_page` is the responsibility of the variant render orchestrator.

- `.issues/29-design-experimentation-mvp-pairwise-voting-on-variations/PLAN.md:415`:
  > Run constraint check: only `inside_page` (per resolved uncertainty #4). If any violation, log "DROP <slug>: <reason>" and continue without rendering.

- `tools/experiment_render.py:11–14` (the source-code echo of the wrong framing):
  ```
  3. Constraint check: only ``brand:inside_page`` (per CONTEXT.md
     resolved uncertainty 4 — variants are research artifacts, brand
     rules are not enforced; structural fit-on-page is). Variants whose
     bbox overshoots the page are dropped from the bag with a clear
     'DROP <slug>: <reason>' log message.
  ```

- `tools/experiment_render.py:135–137` (in `_inside_page_violations`'s docstring):
  ```
  Pulls the InsidePageRule out of BRAND_CONSTRAINTS by id so we don't
  re-implement the bbox math. Per CONTEXT.md resolved uncertainty 4
  no other brand rule runs on variants.
  ```

**`design-guide/README.md` does NOT yet contain any wrong framing about variants** (verified via `grep -n "experiments\|variant" design-guide/README.md` returning nothing). The "reverse the framing in `design-guide/README.md`" task per ISSUE.md §D is therefore **additive**: insert an explicit Layer-1-as-experiment-envelope section, not a literal text reversal. Recommended text shape (corrected framing):

> Layer-1 deterministic rules ARE the constraint envelope for design experiments. A hypothesis that tests one design axis (e.g. information density) MUST respect every other Layer-1 rule. Variants that violate Layer-1 are dropped, not voted on. The 16 `BRAND_CONSTRAINTS` are part of this envelope. The earlier framing — that variants are "research artifacts" exempt from brand rules — was wrong; it conflated "a hypothesis tests one axis" with "a hypothesis ignores all axes". See `.claude/skills/experiments/SKILL.md` for the full methodology.

The planner should also bump the docstrings at `tools/experiment_render.py:11–14` and `:135–137` to remove the "no other brand rule runs on variants" claim.

---

## 9. `generate-skill` invocation pattern (for execution, not research)

`generate-skill` is itself a skill (HIGH — `/root/.claude/skills/generate-skill/SKILL.md`), and it auto-activates on signals like "create a skill" / "make a new skill for…" (`generate-skill/SKILL.md:347-358`). It takes no formal CLI arguments — the executor invokes it conversationally inside the agent loop by stating intent ("create a skill at `.claude/skills/experiments/` for design experimentation"), at which point Claude (with this skill's allowed-tools) executes the 6-step workflow.

Practical executor steps (all in-conversation, no shell):

1. State intent: "Create a new skill at `.claude/skills/experiments/` named `experiments`."
2. Provide the 2–5 concrete usage examples from CONTEXT decision 10 (the four `/experiments <verb>` subcommands).
3. Provide the design constraints: it must be ≤5k words; it must ship the three-layer model; v1 lessons are mandatory content per CONTEXT decision 12.
4. The skill produces: `.claude/skills/experiments/SKILL.md` with YAML frontmatter + body; optionally `references/` for the v1 lessons + retained-concepts spec; optionally `scripts/` if the planner wants a CLI dispatcher (probably not needed since `bin/experiment-*` already exists).
5. Validation step (per `generate-skill/SKILL.md:271-309`): `wc -w` < 5000.

No formal `--help` invocation; the skill's instructions ARE the help. Output shape is fully described in `generate-skill/SKILL.md:376-410`.

---

## 10. Lift from #29's RESEARCH.md / PLAN.md — relevant `<interfaces>`

`.issues/29-.../RESEARCH.md` and `.issues/29-.../PLAN.md` both exist in this worktree — not yet archived. Lift the still-relevant ones (HIGH confidence on these because the source code matches today):

<interfaces>
// tools/experiment_results.py — companion to render; the SUMMARY.md surface lives here
def aggregate_session_to_summary(exp_id: str, session_paths: list[Path]) -> Path
# Reads voting results JSONs (one per rater), aggregates per-pair tallies,
# writes SUMMARY.md to experiments/<exp-id>/SUMMARY.md.
# Per CONTEXT decision 14, the dropped-variants block belongs in SUMMARY.md
# (not in the Astro voting page). Planner should specify the SUMMARY section
# header e.g. "## Variants dropped during render" with the {slug, violations[]}
# rows from manifest.json::_dropped.

// tools/render_pipeline.py — re-used helpers (already imported by experiment_render.py)
HIRES_DPI: int = 150
def _scrub_pdf_metadata(path: Path) -> None
def _verify_brand_fonts() -> None
def _zero_pad_pngs(dir: Path, prefix: str) -> None

// templates/kandidat-falzflyer-din-lang/variant_scaffold.py
def build_variant_front(render_p2_callable: Callable[[Document, Page], None]) -> Document
# Used by experiment_render.py:164. Builds the full 2-page falzflyer doc;
# variant supplies only the P2 panel. Read this file before extending.

// experiments/_schema/manifest.schema.yaml — manifest contract today
# Required: id, subject, target_weak_area, contributing_llms (≥2),
#           created, prompt_version, hypotheses (≥10 + ≥1 wildcard).
# v2 needs to add an optional "_dropped" property (already written by render
# pipeline at experiment_render.py:339-341) with shape:
#   _dropped: list[{slug: str, reason: str, violations?: list[Violation-as-dict]}]

// shared/ci.yml — palette + fonts + paragraph styles authoritative source
# Loaded by sla_lib.builder.ci.load_ci(); used by all brand rules.
# Variant code adds para-styles via doc.add_para_style(ParaStyle(...));
# brand:font_family checks against this set.
</interfaces>

---

## 11. Composition Map — where each MVP component slots in

Everything below is the composition the planner specifies; nothing here introduces new top-level subsystems.

```
ENVELOPE SCHEMA
  experiments/_schema/constraints.schema.yaml          [NEW]
  - JSON Schema Draft 2020-12 (mirror manifest.schema.yaml style)
  - Top-level: { brand_rules: list[str], layer1: dict, relax: list[{id, rationale}], tested_axis: str }
       │
       ▼
ENVELOPE DEFAULT
  experiments/_constraints/falzflyer-default.yml       [NEW]
  - brand_rules: all 16 ids from BRAND_CONSTRAINTS
  - layer1: the 22 (or 21) thresholds from §7
       │
       ▼
PER-EXPERIMENT YAML
  experiments/<exp>/constraints.yml                     [NEW per experiment]
  - inherits from falzflyer-default.yml
  - declares tested_axis: "density+form"
  - declares relax: []  (v2 adds none)
       │
       ▼
LOADER + ENVELOPE OBJECT
  tools/experiment_envelope.py                          [NEW]
  - load_envelope(exp_dir: Path) -> Envelope
  - run_envelope(doc, envelope: Envelope) -> list[Violation]
  - format_envelope_markdown(envelope) -> str         (for prompt thread)
  Lightest wrapper composing existing BRAND_CONSTRAINTS + new layer1 predicates.
  Per CONTEXT discretion: prefer THIS wrapper over editing brand_constraints.py
  (keeps the 16 frozen and lets v2 add new rules without churning the registry).
       │                                       │
       │                                       ▼
       │                          PROMPT TEMPLATE THREAD
       │                          tools/experiment_generate/prompt_template.md   [EDIT]
       │                          - new section "Constraint envelope (HARD floor)"
       │                            inserted between line 29 and 31
       │                          - new {constraint_envelope} token
       │                          - new section "v1 anti-examples — DO NOT REPEAT"
       │                            referencing tools/experiment_generate/v1_anti_examples.md  [NEW]
       │                          - new {v1_anti_examples} token
       │                          - new bullet 6 in "Final check"
       │                          tools/experiment_hypothesis_gen.py             [EDIT]
       │                          - render_prompt() learns 4 tokens (now: subject, weak_area_quote,
       │                                                                 constraint_envelope, v1_anti_examples)
       │                          - SUBJECT_METADATA gets v2 entry
       │                          - run_generation loads envelope before render_prompt
       ▼
RENDER GATE
  tools/experiment_render.py                           [EDIT]
  - rename _inside_page_violations → _envelope_violations(doc, envelope)
  - load envelope once in run_render before the per-variant loop
  - call _envelope_violations at line 165 (replacing today's inside_page-only call)
  - drop log: "DROP {slug}: envelope — {rule_id}: {message}; …"
  - dropped manifest entry: {slug, reason, violations: [{rule_id, message, severity}, ...]}
       │
       ▼
DROP LOG
  experiments/<exp>/manifest.json::_dropped            [SCHEMA BUMP]
  experiments/_schema/manifest.schema.yaml             [EDIT]
  - extend _dropped item shape to include `violations` array
       │
       ▼
SUMMARY.md SURFACING
  tools/experiment_results.py                          [EDIT]
  - new section header "## Variants dropped during render"
  - lists each dropped variant with violations table
  - distinct from voting tallies; pre-vote artifact
       │
       ▼
SKILL CARRIER
  .claude/skills/experiments/SKILL.md                  [NEW — authored via generate-skill]
  - YAML frontmatter (name: experiments; description: covers when invoked,
    auto-activates on /experiments verb)
  - Three-layer model + four subcommand sections
  - References to existing bin/experiment-* tools
  - Lessons section: mode collapse, halo, position bias, why all 16 BRAND_CONSTRAINTS are floor

DOC CORRECTION
  design-guide/README.md                               [EDIT]
  - new paragraph below Layer-1 table naming Layer-1 + 16 BRAND_CONSTRAINTS as the experiment
    constraint envelope; explicit reversal of the "research artifacts" framing per §8 above
  design-guide/gruene-corpus.md §6                     [EDIT — minor]
  - one-line note: "first experiment run produced variants violating spacing/margins; fixed in
    .claude/skills/experiments"

VERIFICATION RUN (mandatory deliverable, ISSUE.md §E)
  experiments/falzflyer-p2-mein-plan-v2/               [NEW directory]
    constraints.yml, manifest.yml, manifest.json, variants/*.py
  - ≥10 variants, all passing envelope OR all drops logged with rationale
  - Flo session voted, results JSON committed
  - design-guide/gruene-corpus.md amended with top-3 + bottom-3 + provenance
```

End of codebase research.
