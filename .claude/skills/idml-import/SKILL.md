---
name: idml-import
description: |
  DEPRECATED — split into idml-scaffold (Stage 1, structural scaffold) and
  idml-tune (Stage 2, per-template visual polish). This stub redirects
  callers to the new skills. Kept on disk so existing /idml-import
  references resolve. Issue #40 made the split.
allowed-tools: Read, Skill
argument-hint: "[deprecated — use /idml-scaffold or /idml-tune]"
---

# /idml-import — DEPRECATED → use /idml-scaffold or /idml-tune

The IDML import skill has been split per issue #40:

| Stage | New skill | Goal |
|---|---|---|
| 1. Scaffold | `.claude/skills/idml-scaffold/SKILL.md` | Every IDML element emitted; `SCAFFOLD_INVENTORY.yml` committed. MAY touch `tools/idml_to_dsl.py`. |
| 2. Tune | `.claude/skills/idml-tune/SKILL.md` | Per-template polish under the inventory gate; forbidden paths enforced. |

## Sub-doc redistribution

| Doc | New home |
|---|---|
| `asset_policy.md`, `classification.md`, `pattern_library.md` | `.claude/skills/idml-scaffold/` |
| `inject_protocol.md`, `tolerance_protocol.md` | `.claude/skills/idml-tune/` |
| (new) `forbidden_paths.md` | `.claude/skills/idml-tune/` |

The originals are kept here for back-compat (any external link pointing
at `.claude/skills/idml-import/<doc>.md` still resolves). Hard-delete
is deferred.

## Migration

- Fresh import → `/idml-scaffold <idml-or-slug>`.
- Tuning an already-scaffolded template → `/idml-tune <slug>`.
- Old "review only" verb → read `build/<slug>/import_report.md` and
  `build/validation/<slug>/preflight.yml` directly; both new skills
  reference the same artifacts.

See also: `tools/inventory_extract.py`, `tools/inventory_compare.py`,
`docs/scribus-sla-attribute-semantics.md`.
