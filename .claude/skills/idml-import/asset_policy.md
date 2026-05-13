# Asset policy — what gets embedded, what stays in `assets/`

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

Schema (Phase G extends `shipped` entries to support both forms):

```yaml
shipped:
  - photo.jpg                                # plain string = ai_generated: false
  - {name: ai-portrait.jpg, ai_generated: true}  # object form = watermarked at zip-build
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

Every template's `meta.yml` carries an `asset_policy:` block:

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
  shipped:
    - plakat-dunkel-fuer-flyer.png                  # content (portrait)
    - green-pine-trees-covered-with-fog.jpg         # content (page-2 photo, user-replaceable)
```

The two lists must be disjoint AND must cover every asset in
`shared/assets/<slug>/`. `bin/idml-import` audits this — if an asset
is unclassified, the skill STOPS and asks the user which bucket it
belongs in.

Defaults (when the user hasn't classified an asset yet):

- Files matching `*logo*`, `*social-media-icon*`, `wahlkreuz*`,
  `*-weiss.png`, `*-cmyk.png` → presumed brand → embed.
- Files matching `portrait*`, `photo*`, `themen-*`, `kandidat-*` →
  presumed content → ship.
- Anything else → STOP, ask.

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

`templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` has 12+
assets today. The policy split (issue #39 task):

**Embedded** (brand-locked):

- gruene-logo-bund-weiss-cmyk.png
- social-media-icon-{facebook, instagram, tiktok}.png
- bluesky-weiss.png, mail-weiss.png, website-weiss.png
- social-media-icons-weiss.png (composite — kept for reference but
  shouldn't be used directly; composite_ai_split must produce
  per-icon PDFs)
- green-pine-trees-covered-with-fog-crop.png (page-2 decorative
  band, brand-locked)

**Shipped** (user-replaceable):

- plakat-dunkel-fuer-flyer.png (portrait/poster placeholder)
- green-pine-trees-covered-with-fog.jpg (full-bleed image; user
  swaps for their own forest / scene)
- green-pine-trees-covered-with-fog-srgb.png (intermediate; same
  intent as the .jpg — keep both or pick one in #39)

The v2 migration is the proof-of-concept for the policy. Once it
ships, the same rules apply to every future IDML import.

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
