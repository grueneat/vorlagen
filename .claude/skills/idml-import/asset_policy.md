# Asset policy — what gets embedded, what stays in `assets/`

> **Active rule (issue #39, first PR — landed):** every asset goes in
> `embedded:`. The `shipped:` list MUST be empty in every committed
> `meta.yml::asset_policy`. The audit (`tools/asset_policy_audit.py`)
> rejects non-empty `shipped:` with a clear message pointing at this rule.
> The eventual `embedded:` / `shipped:` split described below becomes
> active in a follow-up PR after the brand-team decision on Phase D (zip),
> Phase E (gallery flip), and Phase G (AI watermark). Until then, treat
> every example showing `shipped:` entries as **eventual; not yet active**.
> See `.issues/39-…/CONTEXT.md` for the single source of truth on the
> first-PR scope lock.

Downloadable templates must be self-contained. Templates today reference
assets via absolute worktree paths (`/workspace/.worktrees/…/shared/assets/…`),
which break the moment a user downloads the SLA. Every committed
`template.sla` must use **repo-relative** paths, and every downloadable
artifact must carry the files those paths resolve to.

This document is the policy. The implementation is tracked in issue #39.

## Two asset classes

The skill classifies every IDML-referenced asset into one of two buckets:

### Brand assets — **embedded inline in the SLA**

These are part of the template's identity and must never change without
brand-team sign-off:

- Party / organisation logos (`gruene-logo-*`, `bund-logo-*`, …)
- Social-media icon glyphs (`social-media-icon-facebook.png`,
  `bluesky-weiss.png`, etc.)
- Decorative background polygons / textures that define a panel
  (e.g. the green crinkled-paper background of v2-falzflyer page 2)
- Brand-locked illustrations (`wahlkreuz.*`, fold-mark crosshatches)
- Any asset listed in `shared/logos/` or marked
  `kind: brand` in `links_export.yml`

These are **embedded inline** in the SLA via
`ImageFrame(inline_image_data=…, inline_image_ext=…)` (`primitives.py`
already supports this — see `pack_inline_image()`). The user cannot
accidentally remove or replace them.

### Content assets — **shipped in `<slug>.zip::assets/`**

These are template-specific demo content the user is expected to
replace:

- Candidate portraits (`portraits/*.jpg`)
- AI-generated demo illustrations (**watermarked** — see below)
- Photo backgrounds the user would swap for their own
- QR codes, addresses, captions tied to a specific campaign

**AI-generated subset — strict red watermark required.**

Content assets that are AI-generated MUST carry a diagonal red
watermark `KI-GENERIERT MUSS ERSETZT WERDEN` running across the
image when shipped. The source file at
`shared/assets/<slug>/<basename>` stays clean (the rendering
pipeline uses it); the watermark is applied at zip-build time by
`tools/watermark_ai_image.py` (issue #39 Phase G).

The watermark is opt-out-free: every `shipped` asset flagged
`ai_generated: true` is watermarked. Users see the demo placeholder
status loudly the moment they open the zip. The brand-team rule
behind this is: AI imagery must NEVER ship to print without explicit
human review and replacement.

Schema (Phase G — **eventual; not yet active** — extends `shipped`
entries to support both forms):

```yaml
# EVENTUAL Phase G shape — DO NOT use today. The first-PR rule
# requires `shipped: []` and the schema as committed only accepts the
# `list[str]` form. Phase G extends both the schema and the audit.
asset_policy:
  embedded: [...]
  shipped:                                       # ← eventual; today is `shipped: []`
    - photo.jpg                                  # plain string = ai_generated: false
    - {name: ai-portrait.jpg, ai_generated: true}  # object form = watermarked
```

These ship in a ZIP next to the SLA with a documented folder
convention. The SLA references them via **relative paths**:

```
<slug>.zip
├── template.sla
├── assets/
│   ├── portrait.jpg
│   ├── photo-1.jpg
│   └── README.txt        # explains the convention
```

The SLA's `PFILE` attribute becomes `assets/portrait.jpg` (relative to
the SLA file). Users replace the file at that path with their own image.

## Where the classification lives

Every template's `meta.yml` carries an `asset_policy:` block. Under
the first-PR rule (issue #39), every asset goes in `embedded:` and the
`shipped:` list MUST be empty:

```yaml
asset_policy:
  embedded:
    - gruene-logo-bund-weiss-cmyk.png
    - social-media-icon-facebook.png
    - social-media-icon-instagram.png
    - social-media-icon-tiktok.png
    - bluesky-weiss.png
    - mail-weiss.png
    - website-weiss.png
    - green-pine-trees-covered-with-fog-crop.png    # decorative background
    - plakat-dunkel-fuer-flyer.png                  # content (poster placeholder)
    - green-pine-trees-covered-with-fog.jpg         # content (page-2 photo)
  shipped: []
```

The two lists must be disjoint AND must cover every asset in
`shared/assets/<slug>/`. `bin/idml-import` audits this — if an asset
is unclassified, the skill STOPS and asks the user which bucket it
belongs in. **First-PR (issue #39) constraint:** every asset must
land in `embedded:`. The audit rejects non-empty `shipped:` with the
message pointing at this rule. The schema (`shared/asset-policy.schema.yaml`)
stays permissive (forward-compat); the audit enforces emptiness.

Defaults (when the user hasn't classified an asset yet) — **eventual
rule, not yet active**:

- Files matching `*logo*`, `*social-media-icon*`, `wahlkreuz*`,
  `*-weiss.png`, `*-cmyk.png` → presumed brand → embed.
- Files matching `portrait*`, `photo*`, `themen-*`, `kandidat-*` →
  presumed content → ship.
- Anything else → STOP, ask.

**Today (first PR), the `ship` column is empty;** every heuristic
result lands in `embedded:`. The `ship` column becomes active when
Phase D (zip pipeline) / Phase E (gallery flip) / Phase G (AI
watermark) land in a follow-up PR.

The skill MAY auto-classify based on the regex above but MUST surface
the proposed classification for user confirmation before writing it
to `meta.yml`.

## When the skill enforces the policy

`bin/idml-import` runs an asset-policy check during Step 1
(asset extraction):

1. Read `shared/assets/<slug>/links_export.yml` for the asset list.
2. Read `templates/<slug>/meta.yml::asset_policy`.
3. **STOP** if any asset is unclassified — present the regex-guessed
   bucket to the user, get explicit yes/no.
4. After classification: emit SLA with **relative paths** to shipped
   assets and **inline data** for embedded ones.
5. The build step produces `templates/<slug>/<slug>.zip` containing
   the SLA + the `assets/` directory.

## Migration of v2-falzflyer (the seed case)

`templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` has 12
assets in `shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/`.
The first-PR policy (issue #39) puts ALL of them in `embedded:`; the
`shipped:` list is empty:

```yaml
asset_policy:
  embedded:
    - bluesky-weiss.png
    - green-pine-trees-covered-with-fog-crop.png
    - green-pine-trees-covered-with-fog-srgb.png
    - green-pine-trees-covered-with-fog.jpg
    - gruene-logo-bund-weiss-cmyk.png
    - mail-weiss.png
    - plakat-dunkel-fuer-flyer.png
    - social-media-icon-facebook.png
    - social-media-icon-instagram.png
    - social-media-icon-tiktok.png
    - social-media-icons-weiss.png
    - website-weiss.png
  shipped: []
```

The v2 migration is the proof-of-concept for the policy. Once Phase D /
E / G land, the photo (`green-pine-trees-…fog.jpg`) and the plakat
(`plakat-dunkel-fuer-flyer.png`) move to `shipped:` — but that is
**eventual; not yet active**. For the first PR they live in `embedded:`.

The 3 files that aren't directly PFILE'd from the IDML
(`social-media-icons-weiss.png` — the composite reference;
`green-pine-trees-covered-with-fog-srgb.png` — derivative;
`green-pine-trees-covered-with-fog.jpg` — the original photo) are
listed in `embedded:` for forward-compat: the audit walks the
filesystem as truth and requires every disk file to be classified.

## What does NOT happen

- The skill does NOT silently embed everything (would balloon SLA
  files into 10MB blobs that are painful to edit).
- The skill does NOT silently ship everything (loses brand integrity
  — users could replace the Grüne logo with anything).
- The skill does NOT skip the classification step (every asset
  must end up in `embedded:` or `shipped:`).

## Rationale

The policy split matches the actual editing intent. Brand assets are
part of the template identity and editing them is a brand-team
decision, not an end-user one. Content assets are exactly what the
end user came here to swap. Encoding the split mechanically in
`meta.yml` keeps the discipline as code, not as documentation that
gets ignored. Issue #39 ships the implementation; this document
ships the policy.

## Related

- `tools/asset_policy_audit.py` — enforces this policy at build time.
  Hard-fails on shipped-non-empty (first-PR rule), missing-policy-
  when-assets-on-disk, and coverage drift (unclassified or stale
  basenames). Silent-skip when no `shared/assets/<slug>/` exists.
- `tools/check_no_absolute_paths_in_sla.py` — Phase A guard. Rejects
  every committed `template.sla` whose `PFILE` attribute is absolute
  (`/...`, `file://...`, Windows drive letters).
- `shared/asset-policy.schema.yaml` — the schema (JSON Schema draft
  2020-12). Permissive on `shipped:` for forward compat; the audit
  enforces emptiness for the first PR per CONTEXT.md.
- `.issues/39-…/CONTEXT.md` — single source of truth for the
  first-PR scope lock. The eventual `embedded:` / `shipped:` split
  + the AI watermark machinery move from "eventual" to "active" only
  in the follow-up PR.
- `tools/sla_lib/builder/meta_schema.py::load_asset_policy` — the
  read-only loader the audit + converter both consume.
- `tools/sla_lib/builder/primitives.py::pack_inline_image` — the
  qCompress-encoder behind `ImageFrame(inline_image_data=…)`.
