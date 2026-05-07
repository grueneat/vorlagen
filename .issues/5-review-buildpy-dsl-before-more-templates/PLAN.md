# PLAN — Review build.py + DSL before more templates

## Goal recap

Land a hardened DSL surface (`tools/sla_lib/`) and a leaner emitter (`tools/sla_to_dsl.py`) so the next templates land on shared primitives instead of duplicating ~150 inline `extra_*_attrs` keys per template. The work is gated on a multi-LLM review (Claude + Codex + Gemini) that reads the actual code and reconciles RESEARCH.md's recommendations. This issue ships: REVIEW.md, a reconciled P1 list, the `Brand` profile, evidence-driven blocks, a leaner converter, an LLM-emission ergonomics pass, a multi-input ADR, a spec-file schema sketch, and three follow-up issue files for the existing-template migrations. Migrations themselves are deferred. Visual diff against the committed `templates/<id>/baseline.pdf` is the correctness gate per CONTEXT.md.

<objective>
What this plan accomplishes: harden the DSL + converter surface so templates 4..N can be authored against `Brand` + a small set of evidence-driven blocks, with the 113/34 identical `extra_doc_attrs`/`extra_pdf_attrs` keys hoisted out of every `build.py` and the spec→build.py path unblocked by a published schema.
Why it matters: three current `build.py` files (235, 437, 3244 LOC) re-emit the same brand defaults, the same per-frame geometry kwargs, and the same rect-as-clip-path noise. Each new template calcifies the duplication. The DSL is also unverified for the future PDF / InDesign / spec input paths; this issue closes that gap before more templates land.
Scope IN: review (Task 1), reconciliation (Task 2), `Brand` profile (Task 3), evidence-driven blocks (Task 4), converter leanness (Task 5), DSL ergonomics (Task 6), multi-input ADR (Task 7), spec schema (Task 8), follow-up issue files (Task 9), acceptance check (Task 10).
Scope OUT (per CONTEXT.md): rewrites of the three existing templates (separate follow-up issues), PDF/InDesign/spec converter implementations, render-pipeline changes, gallery / Pages publication changes.
</objective>

<context>
Issue: @.issues/5-review-buildpy-dsl-before-more-templates/ISSUE.md
Context: @.issues/5-review-buildpy-dsl-before-more-templates/CONTEXT.md
Research: @.issues/5-review-buildpy-dsl-before-more-templates/RESEARCH.md

Key files (executor will read these as needed):
@tools/sla_lib/builder/__init__.py — public surface re-exports (73 LOC)
@tools/sla_lib/builder/primitives.py — `_Frame`, `TextFrame`, `ImageFrame`, `Polygon`, `Line`, `Run`, `Anchor` (753 LOC)
@tools/sla_lib/builder/document.py — `Document`, `Page`, XML emit pipeline (1028 LOC)
@tools/sla_lib/builder/styles.py — `DocumentLayer`, `ParaStyle`, `CharStyle`, `SoftShadow` (140 LOC)
@tools/sla_lib/builder/ci.py — `BrandColor`, `BrandStyle`, `_CI` loader, `Color`/`Style` enums (181 LOC)
@tools/sla_lib/builder/blocks.py — 8 aspirational blocks, currently unused (400 LOC)
@tools/sla_lib/{editor,reader,slot}.py — legacy slot-fill render pipeline + parser
@tools/sla_to_dsl.py — SLA → build.py emitter (1203 LOC)
@tools/check_ci.py — brand validator (265 LOC)
@shared/ci.yml — brand single-source-of-truth (128 LOC)
@templates/plakat-a1-hochformat/build.py — 235 LOC
@templates/postkarte-a6-kampagne/build.py — 437 LOC
@templates/zeitung-a4-grun/build.py — 3244 LOC
@docs/dsl-reference.md, @docs/render-fidelity.md, @docs/diff-tolerance.md

<interfaces>
<!-- Executor: use these contracts directly. RESEARCH.md has the full corpus measurements; this block is the contract surface tasks 3 to 6 modify. -->

From tools/sla_lib/builder/__init__.py (current public surface):
  Document, Page, TextFrame, ImageFrame, Polygon, Line, Run, Anchor,
  ParaStyle, CharStyle, DocumentLayer, SoftShadow, Color, Style, load_ci, blocks

From tools/sla_lib/builder/document.py:
  class Document:
      def __init__(
          self, *, title: str = "", template_id: str, author: str = "",
          facing_pages: bool = False, column_gap_default_pt: float = 11.0,
          deffont: str = "Gotham Narrow Black", defsize: float = 12,
          first_page_num: int = 1, palette_replaces_ci: bool = False,
          hcms: bool = True,
          doc_page_width_pt: Optional[float] = None,
          doc_page_height_pt: Optional[float] = None,
          extra_doc_attrs: Optional[dict[str, str]] = None,
          extra_pdf_attrs: Optional[dict[str, str]] = None,
          layers: Optional[list[DocumentLayer]] = None,
          # ... 18 kwargs total
      ): ...
      def add_color(self, name: str, *, cmyk=None, rgb=None, register: bool = False) -> None: ...
      def add_para_style(self, style: ParaStyle) -> None: ...
      def add_char_style(self, style: CharStyle) -> None: ...
      def add_master(self, master_obj) -> None: ...
      def add_page(self, *, master: Optional[str] = None, ...) -> Page: ...
      def emit(self) -> str: ...   # SLA XML

From tools/sla_lib/builder/ci.py:
  CI_YAML_DEFAULT = ROOT / "shared" / "ci.yml"
  @dataclass(frozen=True)
  class BrandColor: name: str; cmyk: tuple[int,int,int,int]; rgb: tuple[int,int,int]; ...
  @dataclass(frozen=True)
  class BrandStyle: name: str; ...
  def load_ci(path: Path = CI_YAML_DEFAULT) -> _CI: ...
  class Color: DUNKELGRUEN = "Dunkelgrün"; HELLGRUEN = "Hellgrün"; GELB = "Gelb"; ...
  class Style: ...

From tools/sla_lib/builder/primitives.py (current frame surface — *_pt overrides emitted by every converter call today, becomes opt-in in Task 5):
  @dataclass
  class TextFrame:
      x_mm: Optional[float] = None; y_mm: Optional[float] = None
      w_mm: Optional[float] = None; h_mm: Optional[float] = None
      xpos_pt: Optional[float] = None; ypos_pt: Optional[float] = None
      width_pt: Optional[float] = None; height_pt: Optional[float] = None
      anchor: Optional[Anchor] = None
      style: Optional[str] = None; trail_style: Optional[str] = None
      default_style_attrs: Optional[dict[str, str]] = None
      text_align: Optional[int] = None
      runs: Sequence[Run] = ()
      clip_edit: bool = False; custom_path: Optional[str] = None; fill_rule: int = 1
      # plus columns, col_gap_mm, default_linesp_mode, line_width_pt, etc.
      def link_to(self, other: "TextFrame") -> None: ...

From tools/sla_to_dsl.py (entrypoint):
  def convert(sla_path: Path, out_path: Path, template_id: str,
              assets_dir: Optional[Path] = None) -> None: ...

From shared/ci.yml structure (used by Task 3 to derive brand defaults):
  colors:
    - name: Dunkelgrün
      cmyk: [85, 35, 95, 10]
      role: brand-primary
    # ... Hellgrün, Gelb, Magenta, Black, White, Registration
  styles:
    paragraph: { ... }
    character: { ... }

New surface introduced in this issue (Task 3 implements):
  # tools/sla_lib/builder/brand.py
  @dataclass(frozen=True)
  class Brand:
      name: str
      short: str
      colors: dict[str, BrandColor]
      para_styles: dict[str, ParaStyle]
      char_styles: dict[str, CharStyle]
      layers: list[DocumentLayer]
      default_doc_attrs: dict[str, str]   # the 113 identical keys
      default_pdf_attrs: dict[str, str]   # the 34 identical keys
      deffont: str = "Gotham Narrow Book"
      defsize: float = 12
      column_gap_default_pt: float = 11.0
      bleed_mm: float = 3.0
      @classmethod
      def gruene_noe(cls) -> "Brand": ...
  # Document(__init__) gains: brand: Optional[Brand] = None
  # When brand is set: palette/styles/layers auto-register;
  # default_doc_attrs/default_pdf_attrs are merged with extra_*_attrs (extra_* overrides brand).

Counts to honor (from RESEARCH.md, HIGH confidence — verify in Task 1, do not retake from scratch in Tasks 3 to 5):
  extra_doc_attrs: 136 keys per template, 113 identical across all 3
  extra_pdf_attrs: 45 keys per template, 34 identical across all 3
  Per-frame kwargs: 8 (x_mm, y_mm, w_mm, h_mm, xpos_pt, ypos_pt, width_pt, height_pt)
  clip_edit + verbatim rect-path: 86 of 98 page-frames in Zeitung
  var='pgno' page-number frames: 12 in Zeitung
</interfaces>
</context>

<commit_format>
Format: conventional with issue prefix
Prefix: `5:` (numeric issue id)
Pattern: `5: <type>(<scope>): <description>`
Examples:
  5: docs(review): add REVIEW.md from /issue:review run
  5: feat(sla_lib): add Brand profile hoisting common doc/pdf attrs
  5: refactor(sla_to_dsl): drop redundant pt geometry kwargs on non-byte-critical frames
  5: feat(sla_lib): replace aspirational blocks with five evidence-driven blocks
  5: docs(spec): add template-spec.schema.yaml for spec to build.py path
  5: chore(issues): create follow-up migration issues for postkarte/plakat/zeitung
Allowed types: feat, fix, refactor, docs, test, chore.
Per-task `<commit_message>` below is the exact message the executor must use.
</commit_format>

<constraints_to_flag>
HARD ORDERING:
1. Task 1 (`/issue:review`) MUST run first. The executor MUST NOT begin Tasks 3 to 10 before REVIEW.md exists AND Task 2 has produced a reconciled P1 list. RESEARCH.md is the planner's input; REVIEW.md is the executor's input for implementation.
2. Visual-diff equivalence against `templates/<id>/baseline.pdf` is the correctness gate. If a refactor changes the rendered output by even 1 pixel, it must be either reverted or have its tolerance documented in REVIEW.md (and per `docs/diff-tolerance.md`).
3. The executor MUST NOT migrate the existing three templates inside this issue. Task 9 only creates the follow-up issue files; the actual rewrites happen in those follow-ups.
4. No `template.sla` hand-edits. Templates regenerate from `build.py` only.
5. No "claude" attribution in commits, code, or files (per user memory).
6. Closed override sets stay closed (`PARAGRAPH_OVERRIDE_ATTRS`, `DEFAULTSTYLE_OVERRIDE_ATTRS`, `VAR_OVERRIDE_ATTRS`, `PAGEOBJECT_HANDLED_PRIM`). No `raw_attrs` escape hatch on frames/styles/runs.
7. Every code task ends with `pytest tools/sla_lib/tests -x` AND `bin/validate --ci` green before commit. Cumulative test runtime is acceptable; do not skip.
8. Task 5's drop of pt-geometry kwargs may regress `tools/sla_diff.py` byte-equivalence. Per RESEARCH.md "Risks", run `pytest tools/sla_lib/tests/test_sla_to_dsl.py tools/sla_lib/tests/test_sla_diff.py -x` first to confirm whether `sla_diff` byte-equivalence is gated. If yes, gate the strip with a `--strict-bytes` converter flag instead of removing it unconditionally.
</constraints_to_flag>

<tasks>

<task id="1" type="auto">
  <name>Task 1: Run /issue:review and produce REVIEW.md</name>
  <files>.issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/ISSUE.md
    .issues/5-review-buildpy-dsl-before-more-templates/CONTEXT.md
    .issues/5-review-buildpy-dsl-before-more-templates/RESEARCH.md
    Code surface (~8970 LOC) — reviewers MUST read these directly, NOT receive diffs in prompt:
      tools/sla_lib/builder/{__init__,primitives,document,styles,ci,blocks}.py
      tools/sla_lib/{editor,reader,slot}.py
      tools/sla_to_dsl.py
      tools/check_ci.py
      shared/ci.yml
      templates/plakat-a1-hochformat/build.py
      templates/postkarte-a6-kampagne/build.py
      templates/zeitung-a4-grun/build.py
      docs/dsl-reference.md, docs/render-fidelity.md, docs/diff-tolerance.md
    Secondary context (read on demand):
      tools/sla_lib/tests/{test_blocks,test_builder,test_dsl_extensions,test_sla_to_dsl,test_multipage}.py
  </inputs>
  <outputs>.issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md</outputs>
  <action>
  Invoke `/issue:review 5-review-buildpy-dsl-before-more-templates` to orchestrate Claude + Codex + Gemini per `claude/commands/issue/review-orchestrator.md`. Each reviewer reads the actual code (no diffs/snippets in prompt — see user memory `feedback_review_no_code_in_prompt.md` and `feedback_thorough_reviews.md`).

  Split the review into the three areas defined in RESEARCH.md "Review-execution scaffolding":
    A. DSL surface — `tools/sla_lib/builder/*.py`, `tools/sla_lib/{editor,reader,slot}.py`, `docs/dsl-reference.md`. Brief: audit LLM-emission ergonomics; flag positional traps, redundant channels (`style` vs `default_style_attrs`), validation gaps; propose typed APIs for any closed override sets the corpus needs but the DSL lacks. NO render-pipeline changes.
    B. Converter + templates — `tools/sla_to_dsl.py` + the three `templates/*/build.py`. Brief: audit duplication (verify the 113/34 identical-attr counts and the 86-frames-with-rect-clip-path count from RESEARCH.md), identify hoisting opportunities, propose a higher-level construct surface drawn ONLY from idioms that recur in the existing three templates, estimate line-count delta per template after refactor.
    C. Multi-input-readiness — DSL files + `shared/ci.yml`, plus implicit research on PDF/IDML/spec inputs. Brief: enumerate what each input carries / loses / blocks; propose a minimum spec-file schema. Do NOT design the converters themselves.

  Each reviewer outputs P1 (must-fix-before-next-template), P2 (should-fix-soon), P3 (nice-to-have) items with `file:line` citations.

  REVIEW.md sections (per RESEARCH.md "Where REVIEW.md goes"):
    - Synthesis (top-3 cross-area findings + top-3 disagreements + resolution)
    - Area A — DSL surface (per reviewer × P1/P2/P3 with file:line)
    - Area B — Converter + templates
    - Area C — Multi-input adapter readiness
    - Higher-level construct proposals (concrete API for Brand, blocks, MasterLayout helper)
    - Line-count delta estimates per template
    - Prioritized P1 backlog (Task 2 reconciles this)
    - P2 follow-up issues to file
    - Gating decision (confirm: no new templates land before P1 merges; existing-template rewrites are themselves the migration follow-ups)
    - Per-reviewer raw output (Claude / Codex / Gemini transcripts, untouched)

  CRITICAL: REVIEW.md must explicitly address each P1 candidate from RESEARCH.md "Recommendations to the planner" (items 2 to 6) — kept, reordered, demoted, or replaced. The review is allowed to override RESEARCH.md.
  </action>
  <verify>
    <automated>test -s .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md && grep -q "^## Synthesis" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md && grep -q "^## Area A" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md && grep -q "^## Area B" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md && grep -q "^## Area C" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md && grep -q "^## Prioritized P1 backlog" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md && grep -q "^## Per-reviewer raw output" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md</automated>
  </verify>
  <done>
    - REVIEW.md exists at the locked path with all required sections
    - All three reviewers (Claude, Codex, Gemini) contributed (per-reviewer raw output present)
    - Each P1 candidate from RESEARCH.md (Brand profile, drop redundant pt geometry, replace blocks.py, auto-emit clip_edit rect path, spec schema) is explicitly addressed (kept / reordered / demoted / replaced) in the Prioritized P1 backlog
    - Gating decision section confirms the two CONTEXT.md gates
  </done>
  <commit_message>5: docs(review): add REVIEW.md from /issue:review run</commit_message>
</task>

<task id="2" type="auto">
  <name>Task 2: Reconcile P1 list against RESEARCH.md</name>
  <files>.issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md
    .issues/5-review-buildpy-dsl-before-more-templates/RESEARCH.md
  </inputs>
  <outputs>.issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md</outputs>
  <action>
  Parse REVIEW.md's "Prioritized P1 backlog" and produce the definitive ordered P1 list as `REVIEW-P1.md`. The review is authoritative — it may reorder, demote, replace, or add P1 items vs RESEARCH.md.

  REVIEW-P1.md format:

  ```markdown
  # P1 Reconciled — issue 5

  Source: REVIEW.md (authoritative) + RESEARCH.md (planner input).

  ## Final P1 list (executor implements in this order)
  1. <P1 item> — maps to Task <N> in PLAN.md. Source: REVIEW.md sec <X>. Notes: ...
  2. ...

  ## Items demoted from RESEARCH.md
  - <item> — reason (review found risk / lower value / different sequencing)

  ## Items added by REVIEW.md not in RESEARCH.md
  - <item> — Task <N> covers it / file follow-up / merge into existing task

  ## Items kept verbatim from RESEARCH.md
  - <item> — Task <N>

  ## Mapping to PLAN.md tasks
  | P1 # | Task in PLAN | If review demands extra task | Notes |
  |---|---|---|---|
  | 1 | Task 3 (Brand profile) | — | … |
  | 2 | Task 4 (evidence-driven blocks) | — | … |
  | 3 | Task 5 (converter leanness) | — | … |
  | 4 | Task 6 (DSL ergonomics) | — | If review escalates a P2 to P1, document here. |
  | 5 | Task 7 (multi-input ADR) | — | … |
  | 6 | Task 8 (spec schema) | — | … |
  ```

  If REVIEW.md introduces a P1 item that requires a NEW task not in this PLAN: STOP. Report to the user that the plan needs an additional task and ask before continuing. Do NOT silently expand scope.

  If REVIEW.md demotes a planned task (e.g. blocks layer becomes P2): mark the task as "skipped per REVIEW.md" in REVIEW-P1.md AND in the task's commit when reached (e.g. an empty commit `5: chore(blocks): defer per REVIEW.md` is acceptable, or simply skip and note in EXECUTION.md).
  </action>
  <verify>
    <automated>test -s .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md && grep -q "Final P1 list" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md && grep -q "Mapping to PLAN.md tasks" .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md</automated>
  </verify>
  <done>
    - REVIEW-P1.md exists with all four sections
    - Every P1 item maps to a Task ID in this PLAN OR is explicitly flagged as needing a new task (executor halts in that case)
    - Demoted/added items are documented with reasons
  </done>
  <commit_message>5: docs(review): reconcile P1 list from REVIEW.md against RESEARCH.md</commit_message>
</task>

<task id="3" type="auto">
  <name>Task 3: Implement Brand profile that hoists 113+34 identical attrs</name>
  <files>tools/sla_lib/builder/brand.py, tools/sla_lib/builder/__init__.py, tools/sla_lib/builder/document.py, tools/sla_lib/builder/ci.py, shared/ci-defaults.yml, tools/sla_lib/tests/test_brand.py</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md (authoritative for naming/shape if review converged differently from RESEARCH.md)
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md
    tools/sla_lib/builder/{ci,document,styles}.py
    shared/ci.yml
    templates/{plakat-a1-hochformat,postkarte-a6-kampagne,zeitung-a4-grun}/build.py — to extract the 113 identical extra_doc_attrs and 34 identical extra_pdf_attrs (verify counts match RESEARCH.md before proceeding)
  </inputs>
  <outputs>
    tools/sla_lib/builder/brand.py (NEW, ~120 LOC)
    shared/ci-defaults.yml (NEW — the 113 + 34 identical extras as data)
    tools/sla_lib/builder/document.py (Document gains brand kwarg)
    tools/sla_lib/builder/__init__.py (export Brand)
    tools/sla_lib/builder/ci.py (load_ci helper extended OR Brand reads ci.yml directly — review decides per CONTEXT discretion)
    tools/sla_lib/tests/test_brand.py (NEW unit tests)
  </outputs>
  <action>
  Implement RESEARCH.md "Higher-level construct proposals -> Brand-level construct -> Option A" — recommended unless REVIEW.md converged on B or C.

  1. Extract identical attrs:
     - Read all three `templates/*/build.py` and parse the `extra_doc_attrs={...}` and `extra_pdf_attrs={...}` literals.
     - Confirm the counts: 136 keys per template / 113 identical across all 3 in `extra_doc_attrs`; 45 / 34 in `extra_pdf_attrs`. If mismatch with RESEARCH.md, halt and report.
     - Write the 113 identical doc-attr key/value pairs to `shared/ci-defaults.yml` under `default_doc_attrs:`. Write the 34 identical pdf-attr pairs under `default_pdf_attrs:`.

  2. Create `tools/sla_lib/builder/brand.py` (frozen dataclass `Brand` per the interface block above):
     - `Brand.gruene_noe()` classmethod loads `shared/ci.yml` (palette + brand styles + layers) AND `shared/ci-defaults.yml` (default_doc_attrs + default_pdf_attrs).
     - Brand.colors / .para_styles / .char_styles / .layers / .default_doc_attrs / .default_pdf_attrs all populated.
     - `bleed_mm=3.0` default (matches all three templates after rounding sub-ulp jitter).
     - Brand is frozen, hashable, comparable.

  3. Wire `Brand` into `Document.__init__`:
     - Add `brand: Optional[Brand] = None` kwarg (after the existing kwargs; non-breaking).
     - When `brand` is set:
        - Auto-register `brand.colors` (skip any name already in palette to avoid double-registration).
        - Auto-register `brand.para_styles` and `brand.char_styles` (same skip logic).
        - Auto-register `brand.layers`.
        - Merge `brand.default_doc_attrs` UNDER `extra_doc_attrs` (extra_doc_attrs wins on conflict). Same for pdf_attrs.
        - Default `palette_replaces_ci=False` if brand is set (do NOT change the default for the no-brand path — keep backward compat for the existing converter output).
     - When `brand` is None: no behavior change (every existing test must still pass without modification).

  4. Tests in `tools/sla_lib/tests/test_brand.py` (>=6 cases):
     - `test_brand_loads_gruene_noe()` — Brand.gruene_noe().colors contains {Black, Dunkelgrün, Gelb, Hellgrün, Magenta, White, Registration} with correct CMYK.
     - `test_brand_default_doc_attrs_count()` — len == 113.
     - `test_brand_default_pdf_attrs_count()` — len == 34.
     - `test_document_with_brand_auto_registers_palette()` — Document(brand=Brand.gruene_noe()).emit() contains all brand colors in COLOR list.
     - `test_extra_attrs_override_brand_defaults()` — Document(brand=..., extra_doc_attrs={'PEN': 'Magenta'}).emit() shows PEN='Magenta', not the brand default.
     - `test_no_brand_unchanged()` — Document() without brand emits identical SLA to pre-change pre-baseline (sla_diff byte-identical).

  5. Do NOT update `tools/sla_to_dsl.py` to emit `brand=` yet — that is Task 5. Document this in the task commit.

  6. Do NOT migrate the three existing templates onto Brand — that is the deferred follow-up issue (Task 9 files it).
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && pytest tools/sla_lib/tests/test_brand.py -x -v && pytest tools/sla_lib/tests -x && bin/validate --ci</automated>
  </verify>
  <done>
    - `tools/sla_lib/builder/brand.py` exists and exports `Brand`
    - `Brand.gruene_noe()` returns a populated profile with 113 default_doc_attrs and 34 default_pdf_attrs
    - `Document(brand=...)` auto-registers palette/styles/layers and merges defaults
    - `extra_*_attrs` overrides brand defaults (escape hatch preserved per CONTEXT.md D6)
    - All existing tests pass unchanged (no-brand path is byte-identical)
    - `bin/validate --ci` green for all three templates
  </done>
  <commit_message>5: feat(sla_lib): add Brand profile hoisting common doc/pdf attrs</commit_message>
</task>

<task id="4" type="auto" tdd="true">
  <name>Task 4: Replace blocks.py with five evidence-driven blocks</name>
  <files>tools/sla_lib/builder/blocks.py, tools/sla_lib/builder/__init__.py, tools/sla_lib/tests/test_blocks.py</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md (block list authoritative)
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md
    tools/sla_lib/builder/blocks.py — existing 8 blocks (400 LOC), all unused per RESEARCH.md
    templates/postkarte-a6-kampagne/build.py — Impressum, ContactBlock, PageBackground, StoererBadge corpus
    templates/zeitung-a4-grun/build.py — PageNumber (12x), ColumnTextStory (multi-frame chains), PageBackground (Titelseite)
    templates/plakat-a1-hochformat/build.py — Headline corpus
    tools/sla_lib/tests/test_blocks.py — current tests against the 8 aspirational blocks
  </inputs>
  <outputs>
    tools/sla_lib/builder/blocks.py (rewritten, <=350 LOC)
    tools/sla_lib/builder/__init__.py (export new block names)
    tools/sla_lib/tests/test_blocks.py (rewritten against the 5 new blocks)
  </outputs>
  <action>
  RED -> GREEN -> REFACTOR per RESEARCH.md "Higher-level construct proposals -> Content blocks -> Option A" — unless REVIEW.md converged on a different block list or count.

  Default block list (override only if REVIEW.md says so):
    - `PageNumber`     — `var='pgno'` text frame; >=12 occurrences in Zeitung
    - `Impressum`      — bottom-of-page legal text; corpus in Postkarte + Zeitung
    - `PageBackground` — full-bleed colored polygon at layer 0; corpus in Postkarte (page0/page1) + Zeitung Titelseite
    - `ContactBlock`   — multi-line contact info; corpus in Postkarte
    - `ColumnTextStory`— linked-frame text-flow story; corpus in Zeitung (84 `runs=[ ]` frames)

  Each block MUST:
    - Have >=2 verified occurrences in the existing corpus (cite file:line in module-level docstring of each block).
    - Be a frozen-ish dataclass that emits 1-N PAGEOBJECTs when added to a Page (`page.add(Block(...))`).
    - Honor brand defaults from `Brand` (e.g. `Impressum.fontsize=None` means inherit `brand.para_styles['Impressum'].fontsize`).
    - Use `Anchor` for positioning where the corpus uses anchors; allow `(x_mm, y_mm)` for absolute.

  RED phase — write tests in `tools/sla_lib/tests/test_blocks.py` BEFORE implementation:
    - `test_pagenumber_emits_var_pgno()` — `Page.add(PageNumber(pos=...))` produces a TextFrame with a Run `var='pgno'`, separator='para', paragraph_style='Seitenzahl'.
    - `test_impressum_default_text()` — produces a TextFrame with `trail_style='Impressum'`, default fcolor inherits from brand.
    - `test_pagebackground_full_bleed()` — produces a Polygon at layer 0 covering page width+bleed × height+bleed, fill=brand.primary by default.
    - `test_contactblock_lines()` — N `handles` produces N runs separated by para breaks.
    - `test_columntextstory_chain()` — N frames + M runs links the frames via link_to and distributes runs.
    - For each block: `test_<block>_round_trips_through_emit()` — Block -> Document.emit() -> string is non-empty and parseable as XML.
    - `test_legacy_blocks_removed()` — `from sla_lib.builder.blocks import Headline4Line` raises ImportError (or deprecation warning if review chose legacy compat path).

  GREEN phase — implement the 5 blocks. Each block is <=80 LOC. Total file <=350 LOC.

  REFACTOR phase — extract `_resolve_pos` and brand-default lookup into shared helpers if duplication appears.

  Migration of existing templates onto these blocks is OUT OF SCOPE — Task 9 files the migration follow-ups.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && pytest tools/sla_lib/tests/test_blocks.py -x -v && pytest tools/sla_lib/tests -x && bin/validate --ci</automated>
  </verify>
  <done>
    - `blocks.py` contains exactly the 5 blocks from REVIEW.md (default: PageNumber, Impressum, PageBackground, ContactBlock, ColumnTextStory)
    - Each block's docstring cites >=2 corpus occurrences (file:line)
    - `test_blocks.py` covers each block's emit, brand-default inheritance, and round-trip through `Document.emit()`
    - All existing non-blocks tests pass
    - `bin/validate --ci` green for all three templates (existing templates do NOT use blocks yet — they should pass unchanged)
  </done>
  <commit_message>5: feat(sla_lib): replace aspirational blocks with five evidence-driven blocks</commit_message>
</task>

<task id="5" type="auto">
  <name>Task 5: Converter leanness — emit Brand and drop redundant geometry</name>
  <files>tools/sla_to_dsl.py, tools/sla_lib/tests/test_sla_to_dsl.py, tools/sla_lib/builder/document.py, docs/dsl-reference.md</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md (authoritative for the strip strategy)
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md
    tools/sla_to_dsl.py (1203 LOC) — particularly `_resolve_xy_pt` (~lines 364-374) and `_convert_pageobject` (~lines 570-582)
    tools/sla_lib/builder/brand.py (from Task 3)
    templates/{plakat,postkarte,zeitung}/template.sla — re-converted to verify output shape
  </inputs>
  <outputs>
    tools/sla_to_dsl.py (smaller emit footprint; new `--strict-bytes` flag if needed per Risk in RESEARCH.md)
    tools/sla_lib/tests/test_sla_to_dsl.py (updated assertions for the new emit shape)
    tools/sla_lib/builder/document.py (auto-emit clip rect-path for clip_edit=True frames)
    docs/dsl-reference.md (document the --strict-bytes flag and clip-rect auto-emit)
  </outputs>
  <action>
  Three changes, in this sub-order. Each sub-step is its OWN dry-run-then-commit cycle (do not bundle them — the Risks section in RESEARCH.md notes that 5b may regress sla_diff byte-equivalence). These three commits all use the Task-5 commit_message stub with a short suffix (5a/5b/5c).

  5a. Emit `brand=Brand.gruene_noe()` and only the differing extras:
      - Convert each template via `tools/sla_to_dsl.py` to a tmp build.py.
      - The generated `Document(...)` call uses `brand=Brand.gruene_noe()` and only the 23 differing `extra_doc_attrs` keys + 11 differing `extra_pdf_attrs` keys per RESEARCH.md.
      - Switch `palette_replaces_ci=True` to `palette_replaces_ci=False` for templates whose only color additions are CI brand colors (Plakat: 5 colors, all CI; Postkarte: 8 colors incl. one template-specific Green; Zeitung: 8 colors). Per RESEARCH.md Risk 2, verify `Black` CMYK matches across all templates before flipping (it does, all three use 0,0,0,100).
      - Run the three templates' generated build.py through render+visual_diff. MUST diff clean against `templates/<id>/baseline.pdf`.

  5b. Drop redundant `xpos_pt/ypos_pt/width_pt/height_pt`:
      - First, run `pytest tools/sla_lib/tests/test_sla_to_dsl.py tools/sla_lib/tests/test_sla_diff.py -x` to check whether `sla_diff` byte-equivalence is gated. RESEARCH.md flags this as the unresolved risk (LOW confidence).
      - If `sla_diff` only checks visual output: drop the 4 pt-overrides on every frame whose mm coords fully recover the original SLA's pt values within float roundtrip tolerance (~6 decimal places). Keep them only where the original SLA stored sub-ulp-precision values (Zeitung's ~6 inline-image frames where HEIGHT='27.7755590551181').
      - If `sla_diff` byte-equivalence IS gated: add a `--strict-bytes` CLI flag to `tools/sla_to_dsl.py` that retains the old behavior (emit all 8 kwargs); without the flag, drop the pt-overrides. Update `tools/sla_lib/tests/test_sla_diff.py` to pass `--strict-bytes`. Document the flag in `docs/dsl-reference.md`.
      - Visual diff MUST stay clean.

  5c. Auto-emit `clip_edit=True`'s associated rect-path:
      - In `tools/sla_lib/builder/document.py`'s `_apply_shape_attrs` (or equivalent), when a frame has `clip_edit=True` AND `custom_path is None`, emit the verbatim rectangle path `M0 0 L<w> 0 L<w> <h> L0 <h> L0 0 Z` and `fill_rule=0` automatically.
      - In `tools/sla_to_dsl.py`, when reading SLA frames with `clip_edit=True` AND `custom_path` matches the canonical rect path: omit `custom_path=` and `fill_rule=` from the emitted call.
      - Verify Zeitung re-conversion: 86 frames lose 2 lines each (net ~170 LOC drop on Zeitung, MEDIUM confidence per RESEARCH.md).
      - Visual diff MUST stay clean.

  After all three sub-steps, re-convert all three templates and confirm:
    - Plakat shrinks from 235 -> ~170-180 LOC
    - Postkarte shrinks from 437 -> ~250-280 LOC
    - Zeitung shrinks from 3244 -> ~2150-2450 LOC
    - Visual diff clean for all three vs baselines
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && pytest tools/sla_lib/tests/test_sla_to_dsl.py tools/sla_lib/tests/test_sla_diff.py -x -v && pytest tools/sla_lib/tests -x && bin/validate --ci && bin/render-gallery && python -c "import pathlib; sizes = {t: len(pathlib.Path(f'templates/{t}/build.py').read_text().splitlines()) for t in ('plakat-a1-hochformat', 'postkarte-a6-kampagne', 'zeitung-a4-grun')}; print(sizes); assert sizes['plakat-a1-hochformat'] < 220 and sizes['postkarte-a6-kampagne'] < 380 and sizes['zeitung-a4-grun'] < 2700, sizes"</automated>
  </verify>
  <done>
    - Converter emits `brand=Brand.gruene_noe()` for all three templates
    - Differing extras only (<=23 doc-attrs, <=11 pdf-attrs per template)
    - Redundant pt-geometry kwargs dropped (with `--strict-bytes` flag if sla_diff requires it)
    - `clip_edit=True` no longer requires explicit `custom_path` for rectangles
    - All three templates re-render visually-clean against committed baselines
    - LOC reductions match RESEARCH.md estimates within +/-20%
  </done>
  <commit_message>5: refactor(sla_to_dsl): drop redundant pt geometry kwargs and emit Brand</commit_message>
</task>

<task id="6" type="auto">
  <name>Task 6: DSL LLM-emission ergonomics</name>
  <files>tools/sla_lib/builder/primitives.py, tools/sla_lib/builder/document.py, tools/sla_lib/__init__.py, docs/dsl-reference.md, tools/sla_lib/tests/test_dsl_extensions.py</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md (authoritative for which ergonomics fixes are P1)
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md
    RESEARCH.md "Ergonomics findings for LLM emission"
  </inputs>
  <outputs>
    tools/sla_lib/builder/primitives.py (anchor surface, Run legacy-tuple deprecation, optional Line removal)
    tools/sla_lib/builder/document.py (validation messages)
    docs/dsl-reference.md (ergonomics rules documented)
    tools/sla_lib/tests/test_dsl_extensions.py (new validation tests)
  </outputs>
  <action>
  Apply the ergonomics findings flagged HIGH-confidence in RESEARCH.md "Ergonomics findings for LLM emission". The exact subset is whatever REVIEW.md elevated to P1 (some of these items may be demoted to P2 follow-up — Task 2 captured that decision).

  Default targets (drop or move to P2 follow-up if REVIEW.md disagrees):
    1. Anchor — single canonical form. Today: strings (`"top-center"`, `"bottom-20"`), tuples (`("center", 30)`, `("right-15", "bottom-4")`) all valid. Action: introduce `Anchor(h='center', v='bottom', margin_mm=20)` as the canonical form (named-args, no positional). Keep string/tuple parsers as legacy adapters with a deprecation warning. Document in `docs/dsl-reference.md`.
    2. `Run` legacy tuple form. `Run((text, dict, sep))` (primitives.py:258-283) — keep for blocks.py internals only; emit a `DeprecationWarning` for any non-internal caller. Don't remove yet (the converter may still use it).
    3. `TextFrame.style` vs `trail_style` vs `default_style_attrs` vs `text_align`. Document the precedence rules in `docs/dsl-reference.md` (no API change — REVIEW.md may demand consolidation, in which case escalate to a new task and halt). Add a runtime warning when more than one is set on the same frame.
    4. `Color` / `Style` enums. Confirm they are class-attribute strings; document that the converter emits plain strings (`"Dunkelgrün"`) and the enums exist for blocks/templates code. No removal.
    5. `Line` primitive. Per RESEARCH.md, `Line` is dead from the converter's perspective (Polygons with custom_path are emitted instead). Document this in `docs/dsl-reference.md` ("Line is for spec-input authoring; SLA round-trip emits Polygon"). No removal.
    6. Validation messages. Where `__post_init__` raises today, ensure the message names the offending attribute and the closed set it violated (helps an LLM emitter recover).

  Tests in `test_dsl_extensions.py`:
    - `test_anchor_named_args_form()` — `Anchor(h='center', v='bottom', margin_mm=20)` works.
    - `test_anchor_legacy_string_warns()` — `Anchor.from_legacy('bottom-20')` emits DeprecationWarning.
    - `test_run_legacy_tuple_warns()` — `Run(('text', {}, 'para'))` emits DeprecationWarning.
    - `test_textframe_multi_style_channel_warns()` — setting `style` AND `default_style_attrs` on the same TextFrame emits a warning.
    - `test_para_override_attrs_error_message_names_attr()` — invalid override key raises with the bad key + the closed set name in the message.

  No changes to `extra_*_attrs` (escape hatches preserved per CONTEXT.md D6) and no changes to closed override sets (must stay closed per CONTEXT.md).
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && pytest tools/sla_lib/tests/test_dsl_extensions.py -x -v && pytest tools/sla_lib/tests -x && bin/validate --ci</automated>
  </verify>
  <done>
    - `Anchor(h=, v=, margin_mm=)` named-args form works; legacy string form deprecated
    - `Run` legacy tuple emits DeprecationWarning
    - Validation error messages name the offending attribute and the closed set
    - `docs/dsl-reference.md` documents the canonical anchor form, the multi-style-channel precedence, and the Line/Polygon convention
    - All existing tests still pass; new tests green
    - `bin/validate --ci` green for all three templates
  </done>
  <commit_message>5: refactor(sla_lib): apply LLM-emission ergonomics findings to DSL surface</commit_message>
</task>

<task id="7" type="auto">
  <name>Task 7: Multi-input readiness ADR</name>
  <files>tools/sla_lib/docs/adr-001-multi-input-readiness.md</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md (Area C is authoritative)
    RESEARCH.md "Multi-input adapter requirements on the DSL"
    tools/sla_lib/builder/*.py (verify the gaps the ADR claims)
  </inputs>
  <outputs>tools/sla_lib/docs/adr-001-multi-input-readiness.md (NEW; ~150 LOC of markdown)</outputs>
  <action>
  Write ADR-001 capturing what the DSL guarantees for the three deferred input paths. NOT the converters themselves — purely the DSL-side contract. This is the document the future PDF/InDesign/spec converter issues will reference.

  ADR sections (mandatory):
    - Title — ADR-001: Multi-input readiness for sla_lib DSL
    - Status — Accepted (this issue)
    - Context — three deferred input paths; CONTEXT.md decision 3
    - DSL contract for SLA input (current path) — closed override sets stay closed; inline-image base64 round-trip preserved; pt-geometry overrides opt-in via `--strict-bytes`; ItemID chain pre-allocation preserved; HCMS/PDF ICC pass-through preserved.
    - DSL contract for PDF input — what PDF carries (per-glyph fonts/sizes/colors), what it loses (paragraph-style identity, frame extents, story chains, named brand colors); DSL guarantees: `style=None + default_style_attrs={...}` is a valid first-class path; absolute mm coords are always sufficient (anchor not required); brand-color snap-to-nearest is the converter's job, DSL accepts CMYK strings.
    - DSL contract for InDesign IDML input — IDML named styles map to SLA `paragraph_style`/`char_style`; masterspread -> masterpage; ParentStory -> link_to chain; CharacterStyleRange -> Run runs; declared gap: drop caps and paragraph rules use existing `ParaStyle.drop_cap` / `paragraph_effect_offset` (verify by grep against existing test corpus).
    - DSL contract for spec input — points to `shared/template-spec.schema.yaml` (Task 8); brand symbolic refs (`brand.primary`) resolve to `Color.DUNKELGRUEN`; named layouts live in template's own `build.py` as Python functions, NOT a new DSL construct.
    - Closed override sets — invariants — list the four closed sets (PARAGRAPH_OVERRIDE_ATTRS, DEFAULTSTYLE_OVERRIDE_ATTRS, VAR_OVERRIDE_ATTRS, PAGEOBJECT_HANDLED_PRIM); converters must extend them via PR review, never silently drop.
    - Open gaps — items REVIEW.md flagged that this issue could not close (list any). Each gets a P2/P3 follow-up issue scheduled in Task 9.
    - Consequences — DSL changes are now gated on multi-input compatibility; future input converter issues reference this ADR rather than re-debating contract.

  ADR is documentation only — no code or test changes.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && test -s tools/sla_lib/docs/adr-001-multi-input-readiness.md && grep -q "^## Status" tools/sla_lib/docs/adr-001-multi-input-readiness.md && grep -q "PDF" tools/sla_lib/docs/adr-001-multi-input-readiness.md && grep -q -E "IDML|InDesign" tools/sla_lib/docs/adr-001-multi-input-readiness.md && grep -q "spec" tools/sla_lib/docs/adr-001-multi-input-readiness.md && grep -q -i "closed override" tools/sla_lib/docs/adr-001-multi-input-readiness.md</automated>
  </verify>
  <done>
    - ADR-001 exists with all mandatory sections
    - Each of the three deferred input paths has an explicit DSL contract
    - Closed override sets are listed and the invariant is stated
    - Open gaps (if any from REVIEW.md) are enumerated and have a Task 9 follow-up plan
  </done>
  <commit_message>5: docs(sla_lib): add ADR-001 multi-input readiness contract</commit_message>
</task>

<task id="8" type="auto">
  <name>Task 8: Spec-file schema + LLM consumption guide</name>
  <files>shared/template-spec.schema.yaml, docs/spec-input-schema.md</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md
    RESEARCH.md "Spec input — proposed spec schema sketch"
  </inputs>
  <outputs>
    shared/template-spec.schema.yaml (NEW — JSON Schema in YAML form, sketches the spec contract)
    docs/spec-input-schema.md (NEW — explainer for an LLM emitter)
  </outputs>
  <action>
  Write the spec-file schema sketch from RESEARCH.md "Multi-input adapter requirements -> Spec input" as a real schema file. NOT a converter implementation (deferred per CONTEXT.md).

  `shared/template-spec.schema.yaml` — JSON Schema (draft-2020-12) expressed in YAML:
    - Top-level `$schema`, `type: object`, `additionalProperties: false`.
    - Required top-level keys: `template`, `brand`, `pages`.
    - `template`: `id`, `title`, `size` (enum: A0|A1|A2|A3|A4|A5|A6 or custom width/height), `orientation` (portrait|landscape), `facing_pages` (bool), `bleed_mm` (number, default 3).
    - `brand`: string referencing a Brand profile name (today: `gruene-noe`).
    - `styles`: optional dict of template-specific paragraph/character styles, each with a `parent` referencing a CI style (e.g. `ci/headline-ultra`) and override fields.
    - `pages`: array of page objects, each with `layout` (named layout from `layouts:` block), and content slots (`headline`, `body`, `impressum`, `page_number`, etc.).
    - `layouts`: optional dict of named reusable page layouts.
    - Symbolic color refs (`brand.primary`) allowed wherever a color is expected.

  `docs/spec-input-schema.md` — human + LLM explainer:
    - 1-page intro: "If you are an LLM authoring a `build.py` from a spec file, follow this contract."
    - Worked example: a 50-line spec.yml that produces a Postkarte-equivalent template. Match the "After Option A" example in RESEARCH.md (~18 lines of `Document(...)` setup) so the LLM sees the input/output mapping.
    - Mapping table: spec key -> DSL construct (`pages[].layout=cover` -> `Page` + `PageBackground` block + page setup; `pages[].headline.lines[]` -> `TextFrame` with N `Run` children; etc.).
    - Validation guidance: schema is strict (`additionalProperties: false`); LLM emits valid YAML that yq can lint before the converter runs.
    - Open question: how named layouts are versioned. Note as P3 follow-up.

  Schema must be loadable by `yaml.safe_load` and validatable by `jsonschema` (don't run validation here — that's converter's job — but the file must parse).
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && python -c "import yaml, pathlib; s = yaml.safe_load(pathlib.Path('shared/template-spec.schema.yaml').read_text()); assert s['type'] == 'object', s; assert 'template' in s.get('required', []), s; assert 'pages' in s['properties'], list(s['properties'])" && test -s docs/spec-input-schema.md && grep -q -E "spec.yml|spec.yaml" docs/spec-input-schema.md && grep -q "brand" docs/spec-input-schema.md</automated>
  </verify>
  <done>
    - `shared/template-spec.schema.yaml` parses as YAML and is a valid JSON-Schema-shaped object
    - Top-level `required` lists `template`, `brand`, `pages`
    - `docs/spec-input-schema.md` includes the 50-line worked example and a spec-key-to-DSL mapping table
    - No converter implementation introduced (deferred per CONTEXT.md)
  </done>
  <commit_message>5: docs(spec): add template-spec.schema.yaml for spec to build.py path</commit_message>
</task>

<task id="9" type="auto">
  <name>Task 9: Create follow-up migration issues</name>
  <files>.issues/&lt;next-id&gt;-rewrite-postkarte-onto-brand-blocks/ISSUE.md, .issues/&lt;next-id+1&gt;-rewrite-plakat-onto-brand-blocks/ISSUE.md, .issues/&lt;next-id+2&gt;-rewrite-zeitung-onto-brand-blocks/ISSUE.md</files>
  <inputs>
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md
    .issues/5-review-buildpy-dsl-before-more-templates/REVIEW-P1.md
    Outputs of Tasks 3-8 (Brand, blocks, leaner converter, ADR, spec schema)
  </inputs>
  <outputs>
    Three new issue directories under `.issues/`, each with an `ISSUE.md` (YAML frontmatter + body), created via `issue-cli store create`. Issue IDs allocated by `issue-cli store next-id`.
    NO GitHub mirroring in this task (deferred to user via `/issue:ship` or `/issue:new` with --sync-github later).
  </outputs>
  <action>
  Create three issue files for the existing-template migrations, in the size order CONTEXT.md mandates: Postkarte first (smallest, highest signal-to-noise), then Plakat, then Zeitung.

  Use `issue-cli store create` for each. Workflow per issue:
    1. Allocate id: `ID=$(issue-cli store next-id)`.
    2. Slug: `rewrite-<template>-onto-brand-blocks` (e.g. `rewrite-postkarte-onto-brand-blocks`).
    3. Run: `issue-cli store create --id "$ID" --slug "<slug>" --priority high --labels "dsl,refactor,migration" --body "$(cat body.md)" "<title>"`.
    4. Confirm directory exists: `.issues/$ID-<slug>/ISSUE.md`.

  Each issue's body (use a HEREDOC):
    - Goal: rewrite `templates/<id>/build.py` onto `Brand.gruene_noe()` + the 5 evidence-driven blocks landed in issue #5.
    - Why now: gating from issue #5 — no new templates land before P1 hardening merges; this is one of the agreed migration follow-ups (per CONTEXT.md decision 4).
    - Inputs: the existing committed `templates/<id>/template.sla` + `baseline.pdf`; the new `Brand` + blocks from issue #5.
    - Approach: re-run `tools/sla_to_dsl.py` against the existing template.sla AFTER issue #5 lands. The emitter now produces a slim `build.py` using `brand=Brand.gruene_noe()`, dropped pt-geometry, and `clip_edit=True` without explicit rect-paths. Where idioms map to blocks (PageNumber, PageBackground, ContactBlock, Impressum, ColumnTextStory), hand-edit the generated `build.py` to use the block (or re-run with a converter flag if Task 5 added one). Visual diff vs baseline.pdf is the gate.
    - Acceptance:
        - `tools/visual_diff.py` clean against `templates/<id>/baseline.pdf` (within `docs/diff-tolerance.md` thresholds).
        - `pytest tools/sla_lib/tests -x` green.
        - `bin/validate --ci` green for ALL templates (no regression on the other two).
        - `build.py` line count <= the per-template estimate from RESEARCH.md (Postkarte <=280, Plakat <=180, Zeitung <=2400) — verify and document the actual number.
        - `tools/check_ci.py` clean.
    - Non-goals: no visual changes; no template.sla hand-edits; no further DSL changes (those go back to issue #5 successors).
    - Depends on: issue #5 (this PLAN.md) merged.

  Three concrete issues:
    1. Title: "Rewrite Postkarte A6 onto Brand + blocks" (slug `rewrite-postkarte-onto-brand-blocks`).
    2. Title: "Rewrite Plakat A1 onto Brand + blocks" (slug `rewrite-plakat-onto-brand-blocks`).
    3. Title: "Rewrite Zeitung A4 onto Brand + blocks" (slug `rewrite-zeitung-onto-brand-blocks`).

  In each issue's frontmatter, set `depends_on: [5]` so the dependency is explicit.

  Do NOT call `issue-cli sync github create` — GitHub mirroring is deferred to the user (per task brief).
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && ls -d .issues/*rewrite-postkarte-onto-brand-blocks .issues/*rewrite-plakat-onto-brand-blocks .issues/*rewrite-zeitung-onto-brand-blocks && for d in .issues/*rewrite-postkarte-onto-brand-blocks .issues/*rewrite-plakat-onto-brand-blocks .issues/*rewrite-zeitung-onto-brand-blocks; do test -s "$d/ISSUE.md" && grep -q "depends_on" "$d/ISSUE.md" && grep -q "Brand" "$d/ISSUE.md" || { echo "FAIL: $d"; exit 1; }; done && echo "all three follow-up issues present"</automated>
  </verify>
  <done>
    - Three follow-up issue directories exist with ISSUE.md files
    - Each ISSUE.md has YAML frontmatter (id, title, status=open, priority, labels, depends_on=[5])
    - Each body covers Goal / Why / Inputs / Approach / Acceptance / Non-goals / Depends-on
    - No GitHub sync performed (user does that via `/issue:ship` later)
  </done>
  <commit_message>5: chore(issues): create follow-up migration issues for postkarte/plakat/zeitung</commit_message>
</task>

<task id="10" type="auto">
  <name>Task 10: Acceptance check against ISSUE.md</name>
  <files>.issues/5-review-buildpy-dsl-before-more-templates/EXECUTION.md</files>
  <inputs>
    All artifacts produced by Tasks 1-9
    .issues/5-review-buildpy-dsl-before-more-templates/ISSUE.md (acceptance criteria)
  </inputs>
  <outputs>.issues/5-review-buildpy-dsl-before-more-templates/EXECUTION.md (executor self-verification record)</outputs>
  <action>
  Verify each of the six acceptance criteria from ISSUE.md against the produced artifacts. Write the result to EXECUTION.md as a checked list:

    - [ ] `/issue:review` run completed with all three reviewers — verify by `grep "Per-reviewer raw output" REVIEW.md && grep -E "Claude|Codex|Gemini" REVIEW.md`.
    - [ ] Review report committed under `.issues/5-.../REVIEW.md` summarizing findings per area A-E — verify by section grep (Areas A/B/C are mandatory; D/E may be merged into B per RESEARCH.md split — note the mapping in EXECUTION.md).
    - [ ] Concrete API proposal for `Brand`, content blocks, and page-template layer — verify Brand exists (Task 3), 5 blocks exist (Task 4), MasterLayout/facing-pages helper position (per RESEARCH.md Recommendation B kept it as a `Document.add_facing_pages_masters` convenience — verify either is present in REVIEW.md proposal section).
    - [ ] Line-count delta estimate for applying the new constructs — verify by REVIEW.md "Line-count delta estimates" section AND actual measurements in Task 5 verify block.
    - [ ] Prioritized list of follow-up issues filed — verify by `ls .issues/*rewrite-*-onto-brand-blocks/ISSUE.md | wc -l` == 3, plus any P2 issue files Task 9 created from REVIEW.md "P2 follow-up issues to file".
    - [ ] No new templates land before P1 hardening merges — gating decision documented in REVIEW.md "Gating decision" section AND restated in EXECUTION.md.

  Run the final repo-wide verification:
    - `pytest tools/sla_lib/tests -x` green
    - `bin/validate --ci` green
    - `bin/render-gallery` green
    - `tools/check_ci.py` clean for all three existing templates

  EXECUTION.md format:

  ```markdown
  # EXECUTION — Review build.py + DSL before more templates

  ## Acceptance check
  - [x] criterion 1 — evidence: <file:line or grep result>
  - [x] criterion 2 — evidence: ...
  ...

  ## Verification commands run
  | Command | Result | Notes |
  |---|---|---|
  | `pytest tools/sla_lib/tests -x` | PASS | N tests |
  | `bin/validate --ci` | PASS | all three templates |
  | `bin/render-gallery` | PASS | rendered to build/gallery |
  | `tools/check_ci.py` | PASS | no critical findings |

  ## Artifacts produced
  - REVIEW.md, REVIEW-P1.md, brand.py, ci-defaults.yml, blocks.py (rewritten), sla_to_dsl.py (refactored), document.py (clip auto-emit), adr-001-multi-input-readiness.md, template-spec.schema.yaml, spec-input-schema.md, three follow-up issue files
  - LOC measurements: plakat <num>, postkarte <num>, zeitung <num> (compare to pre-issue 235/437/3244)

  ## Open items deferred to follow-ups
  - <list any P2 items from REVIEW.md and link to filed issues>
  ```
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates && test -s .issues/5-review-buildpy-dsl-before-more-templates/EXECUTION.md && grep -q "Acceptance check" .issues/5-review-buildpy-dsl-before-more-templates/EXECUTION.md && grep -q "Verification commands run" .issues/5-review-buildpy-dsl-before-more-templates/EXECUTION.md && pytest tools/sla_lib/tests -x && bin/validate --ci</automated>
  </verify>
  <done>
    - EXECUTION.md exists with acceptance check, verification commands, and artifact list
    - All six ISSUE.md acceptance criteria are checked off with evidence
    - Final pytest + bin/validate --ci green
    - Any P2 items deferred are linked to filed follow-up issues
  </done>
  <commit_message>5: chore(issues): record acceptance verification for issue 5</commit_message>
</task>

</tasks>

<verification>
After all tasks, the executor runs the final repo-wide checks (already part of Task 10's verify, restated for the orchestrator):

```bash
cd /root/workspace/.worktrees/5-review-buildpy-dsl-before-more-templates
pytest tools/sla_lib/tests -x                                  # full DSL test suite
bin/validate --ci                                              # sla_diff + visual_diff for all templates
bin/render-gallery                                             # full gallery render
python tools/check_ci.py templates/plakat-a1-hochformat        # brand validator
python tools/check_ci.py templates/postkarte-a6-kampagne
python tools/check_ci.py templates/zeitung-a4-grun
```

All four must succeed before the issue is shippable.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:

1. `/issue:review` run completed with Claude + Codex + Gemini reading the actual code -> Task 1 produces REVIEW.md with all three reviewers' raw output.
2. Review report committed under `.issues/5-.../REVIEW.md` summarizing findings per area A-E -> Task 1 produces sections for Areas A/B/C (D = construct proposals + E = backlog are folded into Areas A/B/C per RESEARCH.md's three-area split).
3. Concrete API proposal for `Brand`, content blocks, and page-template layer with API sketch and worked example -> Tasks 3 (Brand), 4 (5 blocks), 6 (DSL ergonomics + masterpage convenience) — REVIEW.md captures the API sketches, code lands the implementation.
4. Line-count delta estimate for all three existing templates -> Task 5 verify block measures actual LOC after re-conversion (Plakat <220, Postkarte <380, Zeitung <2700) and writes the numbers to EXECUTION.md.
5. Prioritized list of follow-up issues filed -> Task 9 creates Postkarte/Plakat/Zeitung migration issues; any P2 items from REVIEW.md also get filed as follow-ups.
6. No `templates/<id>/build.py` for new templates may land before P1 hardening items merge -> Gating decision documented in REVIEW.md and restated in EXECUTION.md (Task 10).

Quantitative success bars (verifiable, mostly enforced in Task 5 / Task 10 verify blocks):
- `extra_doc_attrs` per template <= 23 keys (down from 136); `extra_pdf_attrs` <= 11 keys (down from 45).
- Visual diff clean for all three existing templates against committed baselines.
- Postkarte LOC < 380 (down from 437); Plakat LOC < 220 (down from 235); Zeitung LOC < 2700 (down from 3244).
- All `pytest tools/sla_lib/tests` green at every commit boundary.
- Three follow-up issue files exist with `depends_on: [5]`.
- ADR-001 + spec schema published; both deferred-converter input paths have a stable DSL contract documented.
</success_criteria>
