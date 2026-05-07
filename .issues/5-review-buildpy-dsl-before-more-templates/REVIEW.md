# REVIEW — Review build.py + DSL before more templates

**Issue:** 5-review-buildpy-dsl-before-more-templates
**Reviewed:** 2026-05-07
**Reviewers:** Claude (claude-sonnet-4-6), Codex (gpt-5.4), Gemini (gemini-3.1-pro / default)

---

## Synthesis

### Top-3 cross-area findings all three reviewers converged on

1. **`blocks.py` is aspirational and completely unused in production.** All three reviewers confirmed: all 8 blocks have zero callers in all three production templates. The block layer was designed forward (what we wished templates looked like) rather than backward from the corpus (what idioms actually recur). Replacement with 5 evidence-driven blocks is unambiguously P1.

2. **113 identical `extra_doc_attrs` keys + 34 identical `extra_pdf_attrs` keys across all three templates are the primary LOC and LLM-ergonomics problem.** Codex measured this directly and confirmed RESEARCH.md's counts. The `Brand` profile hoisting these into DSL defaults is universally agreed as P1 Option A.

3. **`palette_replaces_ci=True` hardcoded by the converter defeats `shared/ci.yml` as single source of truth.** All three reviewers flagged this independently. The three templates re-register every CI brand color manually, making drift undetectable and bloating every build.py by 7-8 lines. Flipping to `palette_replaces_ci=False` on the re-authored path is P1.

### Top-3 disagreements and resolution

1. **Claude rated `Line.to_pageobject`'s undefined `clip_edit` attribute as critical (C1); Codex rated it high (H); Gemini didn't catch it in its Area B+C scope.** Resolution: Claude's classification is correct — `Line` is on the public surface, advertised in `docs/dsl-reference.md`, exported by `__init__.py`, but crashes on any `page.add(Line(...)).save()` call. This is a critical bug and must be fixed P1 (simplest path: remove from public surface, document that lines are emitted as `Polygon(custom_path=...)`).

2. **Codex flagged CI path caching (`load_ci()` global singleton) as a high-severity correctness issue; Claude and Gemini did not explicitly raise it.** Resolution: Codex's finding (B-1 in its review: `ci.py:127-135`, first-call cache is path-blind) is valid. Severity downgraded to medium for this issue because no multi-document workflow exists today, but it must be addressed before multi-brand or multi-input adapters land. Filed as P2.

3. **Codex flagged master-page text chain linkage (NEXTITEM/BACKITEM) as a high-severity runtime bug; others didn't call it out.** Resolution: Codex traced `_emit_master_item()` at `document.py:967-976` and confirmed it does not apply chain patching that `_emit_page_item()` does. This is a real gap for any template using chained text on master pages. Zeitung doesn't (masters carry no text chains); but the issue is real. P2 — doesn't block current templates.

---

## Area A — DSL Surface

### P1 Findings (must fix before next template)

| ID | Severity | Title | Location | Reviewer |
|---|---|---|---|---|
| A-1 | **CRITICAL** | `Line.to_pageobject` references undefined `self.clip_edit` | `primitives.py:738` | Claude |
| A-2 | HIGH | `anchor=` API is a four-shaped overload — unpredictable for LLM emission | `primitives.py:106-153` | Claude |
| A-3 | HIGH | `TextFrame` has four overlapping style channels — no canonical choice | `primitives.py:399-425` | Claude |
| A-4 | HIGH | `_Frame` always carries both mm and pt geometry; pt overrides emitted unconditionally | `primitives.py:289-324; sla_to_dsl.py:566-582` | Claude |
| A-7 | MEDIUM | `palette_replaces_ci=True` set in all three templates — undermines `shared/ci.yml` | `templates/*/build.py:24; document.py:637-642` | Claude |
| A-10 | MEDIUM | `clip_edit=True` on rectangular frames requires manual rect-path — 86 frames in Zeitung | `primitives.py:300-310; templates/zeitung...` | Claude |
| A-1 (Codex) | HIGH | Registering one paragraph style disables entire CI style stack | `document.py:678-685` | Codex |

**Detail — A-1 (CRITICAL): `Line.to_pageobject` crashes on any use**

`Line` declares only `x1_mm, y1_mm, x2_mm, y2_mm, color, width_pt, layer, anname`. It does NOT inherit from `_Frame`. Yet `to_pageobject` at `primitives.py:738` reads `self.clip_edit`. Any `page.add(Line(...))` followed by `doc.save(...)` crashes with `AttributeError`. Line is exported (`__init__.py:64`), advertised (`docs/dsl-reference.md:25`), and imported in tests but never exercised against save. The converter deliberately routes SLA PTYPE=5 through `Polygon(custom_path=...)` for this reason.

Fix: Remove `Line` from public surface (`__init__.py`, `docs/dsl-reference.md`, tests). Document that lines are emitted as `Polygon(custom_path=..., line_color=..., fill='None')`. This is already the converter's behavior.

**Detail — A-1 (Codex): Additive paragraph style emission**

`_emit_styles()` at `document.py:678-685` returns as soon as any custom paragraph style exists, stopping CI STYLE emission. This means blocks that reference CI style names (e.g. `ci/headline-ultra`, `ci/impressum`) can produce invalid style references if the document adds even one local style. Fix: make custom paragraph styles additive over the CI stack, not replacing.

**Detail — A-2: Anchor API**

`Anchor = Union[str, tuple]` accepts at minimum: bare strings (`"center"`), 9-way compass (`"top-center"`), tuples (`("center", 30)`), offset strings (`"bottom-20"`). Tuple axis order is `(x_spec, y_spec)` but string compass order is `(v, h)` — directly contradictory. The converter never emits `anchor=` (always uses `x_mm/y_mm`). Fix: collapse to a single typed `Anchor(h=, v=, h_margin_mm=0, v_margin_mm=0)` dataclass form; keep legacy string parsers with `DeprecationWarning`.

**Detail — A-3: TextFrame style channels**

Four channels: `style` (PARENT on DefaultStyle), `trail_style` (PARENT on closing trail), `default_style_attrs` (raw dict), `text_align` (actually vertical alignment on PAGEOBJECT, not horizontal). The name `text_align` is actively misleading. Fix: (1) rename to `vertical_text_align`; (2) document `style` as canonical for paragraph defaults; (3) add runtime warning when `style` AND `default_style_attrs` are both set.

**Detail — A-4: Dual geometry always emitted**

`_Frame` declares `xpos_pt/ypos_pt/width_pt/height_pt` as opt-in overrides. The converter emits BOTH mm and pt on every frame (`sla_to_dsl.py:571-582`). The DSL at `_xy_pt` (line 326) says "pt wins when both are set" — meaning all 125 mm values in existing build.py files are effectively ignored at emit time. Any LLM that edits an `x_mm` value will see no rendered change. Fix: emit pt only when `repr(mm * MM_TO_PT) != repr(xpos_pt)`.

### P2 Findings (should fix soon)

| ID | Severity | Title | Location |
|---|---|---|---|
| A-5 | MEDIUM | `Run` legacy tuple form on public surface — silent key drops | `primitives.py:258-283` |
| A-6 | MEDIUM | `Color`/`Style` enums are plain string class attributes — no validation | `ci.py:140-181` |
| A-8 | MEDIUM | `Document.__init__` kwargs split: LLM-relevant vs byte-equiv hooks undocumented | `document.py:143-159` |
| A-9 | MEDIUM | Validation error messages don't name the offending attribute field | `primitives.py:430-432` |
| A-11 | MEDIUM | `extra_doc_attrs` emitted as one 7KB single-line dict literal — diff-hostile | `sla_to_dsl.py:132` |
| A-16 | MEDIUM | CI YAML "single source of truth" claim undercut by per-template ParaStyle re-declarations | `templates/*/build.py` |
| B-1 (Codex) | HIGH | CI path caching: `load_ci()` global singleton is path-blind | `ci.py:127-135` |
| B-2 (Codex) | HIGH | Master-page text chain NEXTITEM/BACKITEM links never emitted | `document.py:967-976` |

### P3 Findings (nice to have)

| ID | Title | Location |
|---|---|---|
| A-12 | `unit` and `first_page_num` kwargs silently ignored in emit | `document.py:150, 153` |
| A-14 | `Page.label` auto-injects a hidden TextFrame — LLM-hostile side effect | `document.py:485-497` |
| A-15 | `SLAEditor.set_text` destructive fallback loses inline tags | `editor.py:51-70` |

---

## Area B — Converter + Templates

### Measurement verification (all three reviewers confirmed)

| Metric | RESEARCH.md | Verified |
|---|---|---|
| `extra_doc_attrs` keys per template | 136 | 136 (Codex + Gemini confirmed) |
| Identical `extra_doc_attrs` across 3 | 113 | 113 (Codex + Gemini confirmed) |
| `extra_pdf_attrs` keys per template | 45 | 45 (Codex + Gemini confirmed) |
| Identical `extra_pdf_attrs` across 3 | 34 | 34 (Codex + Gemini confirmed) |
| Zeitung `clip_edit=True` + rect-path | 86 | 86 (Gemini confirmed) |
| Zeitung `var='pgno'` frames | 12 | 12 (Gemini confirmed) |
| Blocks used in production | 0 | 0 (all three confirmed) |

### P1 Findings (must fix before next template)

| ID | Severity | Title | Location | Reviewer |
|---|---|---|---|---|
| B-5 | MEDIUM | Aspirational blocks have zero production callers | `blocks.py:1-400` | Codex |
| B-6 | MEDIUM | Dropping pt geometry unconditionally not yet safe without `sla_diff` check | `sla_to_dsl.py:571-582` | Codex |
| B-4 (Gemini) | LOW | `palette_replaces_ci=True` hardcoded in converter | `sla_to_dsl.py:931` | Gemini |

### P2 Findings

| ID | Severity | Title | Location | Reviewer |
|---|---|---|---|---|
| B-3 | MEDIUM | Soft-shadow erase flag doesn't round-trip through converter | `primitives.py:381-390; sla_to_dsl.py:388-399` | Codex |
| B-4 | MEDIUM | Generated templates say "hand-edit build.py" — conflicts with locked AI-authored workflow | `sla_to_dsl.py:1-7; templates/plakat.../build.py:1-2` | Codex |

---

## Area C — Multi-input Adapter Readiness

### P1 Findings

| ID | Severity | Title | Location | Reviewer |
|---|---|---|---|---|
| C-1 (Codex) | MEDIUM | `extra_doc_attrs` semantics understate layout-critical state preserved in the bags | `docs/dsl-reference.md:108-122; sla_to_dsl.py:875-940` | Codex |
| C-2 (Codex) | MEDIUM | Spec/PDF/IDML readiness blocked by API predictability, not feature coverage | `document.py:145-163; primitives.py:258-283` | Codex |

**Summary on multi-input readiness:**

- **PDF input**: `style=None + default_style_attrs={...}` is a valid first-class path today. Absolute `x_mm/y_mm/w_mm/h_mm` is sufficient (Gemini C-1, C-2 confirmed). No DSL gaps block PDF-to-build.py converter once pt-override path is cleaned up.
- **InDesign IDML input**: Named styles map to SLA `paragraph_style`; masterSpreads → masterpage; linked stories → `link_to` chain. `ParaStyle` covers drop caps and baseline offsets. No structural gaps. The master-page chain bug (Codex B-2) blocks fully linked master stories, but that's not a common IDML pattern.
- **Spec input**: RESEARCH.md's proposed `spec.yml` schema is workable. The DSL is representative-enough today. Ergonomics issues (4-channel style, anchor overload) are blockers for clean spec→build.py generation. Fix ergonomics (P1-6) first.

### P2 Findings (from REVIEW, per-reviewer)

Gemini's C-1 and C-2 are confirmations of DSL readiness (PDF path works; absolute mm is sufficient), not issues. Both should be documented in the ADR.

---

## Higher-level construct proposals (concrete API)

### Brand profile

All reviewers converge on **Option A: new `tools/sla_lib/builder/brand.py` frozen dataclass**.

```python
@dataclass(frozen=True)
class Brand:
    name: str
    short: str
    colors: dict[str, BrandColor]
    para_styles: dict[str, ParaStyle]
    char_styles: dict[str, CharStyle]
    layers: list[DocumentLayer]
    default_doc_attrs: dict[str, str]   # 113 identical keys
    default_pdf_attrs: dict[str, str]   # 34 identical keys
    deffont: str = "Gotham Narrow Book"
    defsize: float = 12
    column_gap_default_pt: float = 11.0
    bleed_mm: float = 3.0

    @classmethod
    def gruene_noe(cls) -> "Brand": ...   # loads shared/ci.yml + shared/ci-defaults.yml
```

`Document.__init__` gains `brand: Optional[Brand] = None`. When brand is set: palette auto-registers, CI injected, default attrs merged under `extra_*` overrides.

Worked example — Postkarte before/after: see RESEARCH.md "Worked example" (~−33 lines on setup block alone; the 7KB `extra_doc_attrs` blob vanishes from the diff).

### Blocks: 5 evidence-driven blocks

All three reviewers confirmed 0 production uses of the current 8 blocks, and support the replacement.

Proposed 5 blocks (each with ≥2 corpus occurrences):
1. **`PageNumber`** — `var='pgno'` TextFrame; 12× in Zeitung (`templates/zeitung-a4-grun/build.py`)
2. **`Impressum`** — bottom-of-page legal text; corpus in Postkarte + Zeitung
3. **`PageBackground`** — full-bleed colored Polygon at layer 0; corpus in Postkarte (2 pages) + Zeitung Titelseite
4. **`ContactBlock`** — multi-line contact info; corpus in Postkarte (`templates/postkarte-a6-kampagne/build.py:195-225`)
5. **`ColumnTextStory`** — linked-frame text-flow story; corpus in Zeitung (84 `runs=[ ]` frames with `link_to`)

Claude additionally suggested `MasterpageRectangle` as a 6th. Given the corpus evidence (full-bleed Polygon IS `PageBackground`), `PageBackground` covers this; no 6th block needed.

Old 8 blocks move to `blocks.legacy` for one release.

### Page-template / facing-pages helper

Per RESEARCH.md Recommendation B (and confirmed by all reviewers): `Document.add_facing_pages_masters(name='Inhalt', items_left=[...], items_right=[...])` convenience method. No separate `MasterLayout` dataclass needed — the Zeitung is the only multi-master template, and adding a third abstraction for it alone is over-engineering.

---

## Line-count delta estimates after P1 refactor

| Reviewer | Plakat (235) | Postkarte (437) | Zeitung (3244) |
|---|---|---|---|
| Claude | ~160 | ~260 | ~2200 |
| Codex | 170-190 | 280-330 | 2200-2550 |
| Gemini | not provided | not provided | not provided |
| **Consensus** | **~160-190** | **~260-330** | **~2200-2550** |
| **RESEARCH.md** | ~170-180 | ~250-280 | ~2150-2450 |

Reviewers agree with RESEARCH.md's estimates. Direction is high-confidence; magnitude is medium (±15%). Actual delta will be measured in the migration follow-up issues.

---

## Prioritized P1 backlog (executor implements these in this issue)

The review is authoritative. RESEARCH.md's 6 P1 items are confirmed with one reordering and two clarifications:

1. **[P1-1] `Brand` profile** — new `tools/sla_lib/builder/brand.py` (~120 LOC); `shared/ci-defaults.yml` (113+34 defaults); `Document(brand=...)` kwarg; `palette_replaces_ci=False` default for Brand path. Maps to **Task 3**.

2. **[P1-2] Evidence-driven blocks** — replace `blocks.py` 8 aspirational with 5 corpus-backed blocks; rewrite `test_blocks.py`. Maps to **Task 4**. (Reordered above converter changes because blocks depend on Brand context being clear first.)

3. **[P1-3] Converter leanness** (sub-items):
   - 3a: Emit `brand=Brand.gruene_noe()` and only the 23 differing `extra_doc_attrs` keys + 11 differing `extra_pdf_attrs` keys per template.
   - 3b: Drop redundant `xpos_pt/ypos_pt/width_pt/height_pt` on non-sub-ulp frames; add `--strict-bytes` flag if `sla_diff` byte-equivalence is gated (verify first).
   - 3c: Auto-emit `clip_edit=True` rect-path in DSL — saves ~250 lines on Zeitung.
   Maps to **Task 5**.

4. **[P1-4] DSL ergonomics pass** (critical fix first, then rest):
   - Fix `Line.to_pageobject` AttributeError — **critical**, remove `Line` from public surface (or add `_Frame` fields).
   - Fix additive paragraph-style emission (`_emit_styles` returns early).
   - Fix `anchor=` overload — introduce `Anchor(h=, v=)` dataclass form; deprecate legacy strings.
   - Fix `Run` legacy tuple form — deprecation warning, blocks.py migrates to `Run(...)`.
   - Fix `palette_replaces_ci=True` default for brand path.
   - Fix validation error messages: pass `attr_name` to validators.
   - Rename `text_align` to `vertical_text_align`.
   Maps to **Task 6**.

5. **[P1-5] Multi-input ADR** — write `tools/sla_lib/docs/adr-001-multi-input-readiness.md`. Maps to **Task 7**.

6. **[P1-6] Spec schema** — write `shared/template-spec.schema.yaml` + `docs/spec-input-schema.md`. Maps to **Task 8**.

---

## P2 follow-up issues to file (deferred)

- Fix `load_ci()` global singleton: cache by resolved path (Codex B-1).
- Fix master-page NEXTITEM/BACKITEM chain patching (Codex B-2).
- Fix soft-shadow erase round-trip key mismatch (Codex B-3).
- Fix `unit` and `first_page_num` kwargs silently no-op (Claude A-12).
- Update generated build.py header to reflect AI-authored workflow (Codex B-4).
- Extend `check_ci.py` to validate brand-style PARENT inheritance and font-stack drift (Claude A-16).
- Migration: Rewrite Postkarte A6 onto Brand + blocks (Task 9 follow-up issue).
- Migration: Rewrite Plakat A1 onto Brand + blocks (Task 9 follow-up issue).
- Migration: Rewrite Zeitung A4 onto Brand + blocks (Task 9 follow-up issue).

---

## Gating decision

**Confirmed: no `templates/<id>/build.py` for new templates may land before the P1 hardening items above are merged.**

Evidence: Claude's gating_decision `confirmed`; Codex's gating_decision `confirmed`; Gemini's verdict `warn` (no critical blockers but significant issues).

The critical bug (Line.to_pageobject AttributeError) and the high-severity issues (4-channel style API, unconditional dual geometry, additive style emission) collectively mean the current DSL is not a stable LLM emission target. Any new template authored against the current surface would need re-authoring after P1 lands. The gating policy is correct.

**Confirmed: existing-template rewrites (Postkarte → Plakat → Zeitung) are themselves the migration follow-ups,** filed as separate issues in Task 9 with `depends_on: [5]`. They are NOT blockers for new templates beyond the DSL hardening.

---

## Per-reviewer raw output

### Claude (claude-sonnet-4-6) — Area A, full DSL surface

Saved at: `.issues/5-review-buildpy-dsl-before-more-templates/reviews/review-2026-05-07T10-05-25Z-5-review-buildpy-dsl-before-more-templates-claude.md`

Verdict: **fail** (1 critical, 4 high, 8 medium) — `Line.to_pageobject` crash is the blocker.
Key unique findings: A-1 (Line crash), A-2 (anchor API), A-3 (4 style channels), A-4 (dual geometry), A-7 (palette_replaces_ci), A-10 (clip_edit), A-12 (unit/first_page_num no-op), A-14 (Page.label side effect), A-15 (editor destructive fallback).

### Codex (gpt-5.4) — Full scope (A, B, C)

Saved at: `.issues/5-review-buildpy-dsl-before-more-templates/reviews/review-2026-05-07T09-09-18Z-5-review-buildpy-dsl-before-more-templates-gpt-5-4.md`

Verdict: **warn** (0 critical, 4 high, 7 medium) — significant DSL and builder correctness issues; no new templates before P1 merge.
Key unique findings: load_ci() singleton path-blind (B-1), master-page chain patching gap (B-2), soft-shadow round-trip key mismatch (B-3), generated header text conflict (B-4), CI extra_doc_attrs contract understatement (C-1), multi-input readiness blocked by predictability (C-2).

### Gemini (gemini-3.1-pro-preview / default model) — Areas B+C, converter + multi-input

Saved at: `.issues/5-review-buildpy-dsl-before-more-templates/reviews/review-2026-05-07T10-24-02Z-5-review-buildpy-dsl-before-more-templates-gemini.md`

Note: Gemini's preferred model `gemini-3.1-pro-preview` returned HTTP 429 (no capacity). Review ran on the default available model. Review scope was constrained to Areas B+C.

Verdict: **warn** (0 critical, 0 high, 2 medium) — focused on measurement verification and confirming P1 items.
Key contribution: Independent verification of all RESEARCH.md measurements (136/113/45/34/86/12/0 block usage). Confirmed `palette_replaces_ci=True` issue. Confirmed absolute mm positioning is sufficient for PDF/InDesign paths.

### Consensus

All three reviewers agreed: (1) Brand profile as P1-1 is correct, Option A; (2) blocks replacement as P1-2 is correct; (3) converter leanness (pt strip, clip_edit) as P1-3 is correct with the `--strict-bytes` guard; (4) gating policy is confirmed. Claude found the critical `Line` bug; Codex found the additive-style and master-chain bugs. Combined, the review is highly actionable with no unresolved ambiguity on P1 scope.
