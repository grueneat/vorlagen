---
id: '5'
title: Review build.py + DSL before more templates
status: done
priority: high
labels:
- dsl
- review
- refactor
- architecture
source: github
source_id: 9
source_url: https://github.com/GrueneAT/vorlagen/issues/9
---

## Goal

Before adding any further templates to the gallery, run a deep, multi-LLM review of the **DSL surface** (`tools/sla_lib/`), the **converter** (`tools/sla_to_dsl.py`), and the three existing **`templates/*/build.py`** files. The review must yield concrete refactor proposals so the next templates land on a hardened DSL — not on whatever shape the auto-generator happens to emit today.

The review itself is conducted via `/issue:review` (the multi-LLM orchestrator: Claude + Codex + Gemini reading the code directly). This issue tracks the *outputs* of that review and the follow-up DSL/builder changes.

## Why now

- Three `build.py` files exist (Plakat A1: 235 lines, Postkarte A6: 437 lines, Zeitung A4: **3244 lines**). The Zeitung file is auto-generated and effectively unreadable / unmaintainable as hand-edited source-of-truth.
- A large fraction of every `build.py` is verbatim `extra_doc_attrs` / `extra_pdf_attrs` / per-page passthrough — values that should live as Document defaults or be encapsulated in higher-level constructs, not duplicated per template.
- Repeating brand styles, frames, masterpages, badges, and impressum blocks across templates is currently copy-paste. Adding template #4–#10 will calcify the duplication unless we land reusable higher-level constructs first.
- DSL ergonomics directly determine how cheaply local groups (and downstream maintainers) can author new templates — this is the leverage point for the entire gallery roadmap.

## Scope of the review (driven through `/issue:review`)

### A. DSL surface audit (`tools/sla_lib/`)

- `builder/` package — coverage of the SLA feature surface (DOCUMENT, MASTERPAGE, PAGEOBJECT PTYPE 2/4/5, styles, colors, layers, ITEXT runs, PDF export attrs).
- `editor.py`, `reader.py`, `slot.py` — internal vs. public boundary, naming, mutation semantics.
- API ergonomics: required vs. optional args, sensible defaults, named-args explosion, `extra_*_attrs` escape hatches.
- Type safety, dataclass discipline, validation at construction time.

### B. Converter audit (`tools/sla_to_dsl.py`)

- Quality of generated `build.py`: is it human-editable, or write-once?
- How much of the per-template noise (e.g. ~70 `extra_doc_attrs` keys identical across templates) could be hoisted into DSL defaults so generated files stay slim.
- Round-trip story (SLA → build.py → SLA) — which attributes survive, which don't, where it leaks.

### C. Existing `build.py` review

- Plakat A1, Postkarte A6, Zeitung A4: code quality, redundancy, drift between the three.
- Identify the shared idioms that should become higher-level DSL constructs.

### D. Higher-level construct proposal

The user explicitly wants **encapsulated, shareable content pieces** as part of the DSL. Propose a layered design:

- **Brand-level primitives** (single source of truth): `Brand(colors=..., para_styles=..., char_styles=..., default_doc_attrs=...)` so a template doesn't restate every CMYK value or `extra_doc_attrs` key.
- **Composable content blocks** (reusable across templates): `Impressum(...)`, `LogoBadge(...)`, `Headline(...)`, `Stoerer(...)`, `ColumnTextBlock(...)`, `ContactCard(...)` — each emits the right combination of frames + styles.
- **Page templates / layouts**: A `MasterLayout` abstraction so a Postkarte front-side and a Plakat headline area aren't both hand-positioned per template.

Each proposal must include: API sketch, what it replaces in the current `build.py` files, and an estimate of the line-count delta on Zeitung.

### E. Refactor plan

A concrete, prioritized backlog of follow-up issues — DSL changes, converter changes, and `build.py` rewrites — in dependency order. Each item gets a "before/after" diff sketch where useful.

## Acceptance criteria

- [ ] `/issue:review` run completed against this issue with all three reviewers (Claude, Codex, Gemini) reading the actual code.
- [ ] Review report committed under `.issues/5-.../REVIEW.md` (or wherever `/issue:review` writes it) summarizing findings per area A–E.
- [ ] Concrete API proposal for `Brand`, content blocks, and page-template layer — each with API sketch and a worked example showing how the existing Postkarte (smallest) collapses onto it.
- [ ] Line-count delta estimate for applying the new constructs to all three existing templates (especially Zeitung's 3244 lines).
- [ ] Prioritized list of follow-up issues filed (or queued) so the DSL hardening work is properly sequenced.
- [ ] No `templates/<id>/build.py` for new templates may land before the agreed P1 hardening items from this review are merged. (Gating decision documented in the issue.)

## Non-goals

- Not a rewrite of any existing template's *visual* output. Render fidelity must stay byte-equivalent against the committed gallery PDFs.
- Not a port to a different DSL/language. Stay in Python.
- Not a converter rewrite as a precondition — the converter can be hardened iteratively once the DSL surface is settled.

## Pointers

- DSL: `tools/sla_lib/{__init__.py,builder/,editor.py,reader.py,slot.py}`
- Converter: `tools/sla_to_dsl.py`
- Templates: `templates/plakat-a1-hochformat/build.py`, `templates/postkarte-a6-kampagne/build.py`, `templates/zeitung-a4-grun/build.py`
- Render + diff pipeline: `tools/render.py`, `tools/sla_diff.py`, `tools/visual_diff.py`, `bin/render-gallery`
- Background context: archived issues #1, #2 (DSL foundation + faithful reproduction).
