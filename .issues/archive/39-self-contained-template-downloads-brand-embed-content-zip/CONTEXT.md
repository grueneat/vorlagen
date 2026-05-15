# Context decisions — issue #39

User-locked decisions before research/plan/execute. These constrain
the scope of the FIRST PR for issue #39. Subsequent PRs may extend.

## Scope of the first PR

**The full content of every template is EMBEDDED inline in the SLA.**
Brand assets AND content assets all ship as `ImageFrame(inline_image_data=…)`.
There are no `shipped:` files, so there is NO zip packaging in the
first PR.

### In scope

- **Phase A — Path canonicalisation.** Strip absolute worktree paths
  from committed `template.sla` files; rewrite to repo-relative.
  Land the CI lint that grep-bans absolute paths going forward.
  (Bug fix: today's downloads are broken regardless of policy.)
- **Phase B — Asset classification audit.** `meta.yml::asset_policy`
  enforcement + `tools/asset_policy_audit.py` wired into `_run_audit`
  BEFORE A1 inventory. `bin/idml-import` stops on unclassified
  assets and asks the user. **First-PR rule:** every asset must
  end up in `embedded:`. The `shipped:` list MUST be empty.
- **Phase C — SLA inline-embedding emission.** Converter emits
  `ImageFrame(inline_image_data=…, inline_image_ext=…)` for every
  asset (since every asset is `embedded:` in the first PR).
- **Phase F — v2-falzflyer migration.** Author `asset_policy` for
  v2-falzflyer with all 12 assets in `embedded:`. Re-emit; verify
  the downloaded `template.sla` opens standalone on a clean
  checkout with no missing references.

### Out of scope (deferred to follow-up PRs)

- **Phase D — ZIP build pipeline.** Not needed: there are no
  shipped files until the brand team decides to include content
  assets in the download. When that decision lands, the zip
  pipeline becomes necessary; until then, the bare `template.sla`
  download (now self-contained via inline embedding) is enough.
- **Phase E — Gallery download flow change.** The gallery
  (`site/public/`) currently links to the bare SLA. Keeping that
  unchanged — the bare SLA is now self-contained.
- **Phase G — AI-generated and additional assets.** The brand team
  has not decided whether the zip should include:
  1. AI-generated demo assets (with or without the proposed
     diagonal red `KI-GENERIERT MUSS ERSETZT WERDEN` watermark), AND/OR
  2. Additional supplementary assets (extra portraits, alternative
     photo backgrounds, swappable demo content beyond the minimum
     the template needs to render).
  Until that decision, no AI / supplementary assets ship at all.

## Implementation rules the planner must encode

1. **`shipped:` list MUST be empty** in every committed
   `meta.yml::asset_policy`. The audit REJECTS non-empty `shipped:`
   for now with:
   > "Shipped assets are pending brand-team review. The first PR
   > for issue #39 only supports `embedded:`. Move the asset to
   > `embedded:` (it will be inlined in the SLA) or remove it from
   > the template until the brand team decides on the zip flow."
2. The `asset_policy` schema still ACCEPTS the `shipped:` key (for
   forward compatibility). Just the audit rejects non-empty values.
3. Subsequent PRs (when the team decides) lift the rejection AND
   implement Phase D zip + Phase E gallery + Phase G watermarking.

## v2-falzflyer migration specifics

All 12 assets currently in `shared/assets/<slug>/` go into
`embedded:`:

- gruene-logo-bund-weiss-cmyk.png
- social-media-icon-facebook.png
- social-media-icon-instagram.png
- social-media-icon-tiktok.png
- bluesky-weiss.png
- mail-weiss.png
- website-weiss.png
- social-media-icons-weiss.png (composite reference)
- green-pine-trees-covered-with-fog-crop.png
- green-pine-trees-covered-with-fog-srgb.png
- green-pine-trees-covered-with-fog.jpg
- plakat-dunkel-fuer-flyer.png

The two `green-pine-trees-…` (.png crop + .jpg full) and the
`plakat-dunkel-…` are not AI-generated, so they don't trigger any
watermark question. They're stock / brand-supplied content; brand
team has already approved them shipping inline.

## Why split the work this way

- **Phase A is a real bug** (downloads broken regardless of policy)
  and ships independently.
- **Phases B/C/F deliver a working self-contained download today**
  without depending on a still-pending team decision.
- **Phases D/E/G are blocked** on a decision: "do we ship
  user-replaceable assets at all, AI or otherwise?" When the answer
  is yes, all three phases land in one follow-up PR (so users see
  the zip + gallery + watermark together, not in three confusing
  steps).

## Preview generation stays unchanged

The render pipeline produces `preview.pdf` + `page-NN.png` from
the same committed `template.sla`. Since brand assets are inlined
and content assets keep referencing the on-disk `shared/assets/<slug>/`
files (now via REPO-RELATIVE paths), the preview pipeline keeps
rendering the full template — AI / demo / content imagery included.

Concretely:

- `template.sla` references brand assets inline (no path needed)
  and content assets via relative paths like
  `shared/assets/<slug>/<basename>` (resolved against the repo
  root when the SLA opens from `templates/<slug>/`).
- The preview pipeline `cd`s into `templates/<slug>/` and runs
  Scribus, so relative paths resolve against the repo root the
  same way they always have. **No two-mode build, no special
  preview-only build path.**
- The downloaded `template.sla` opens standalone if AND ONLY IF
  the user keeps the `shared/assets/<slug>/` directory alongside
  it. (For the first PR this is OK — the brand-embed-only scope
  means most assets are inline; the remaining content references
  are noted in the SLA but the user is expected to replace them.)
- Once the team decides on shipping content assets (Phase D zip),
  the zip contains both the SLA and `shared/assets/<slug>/`, so
  the relative paths resolve inside the unzipped tree.

## What NOT to do

- Do NOT build `tools/build_template_zip.py` in this PR.
- Do NOT change `site/public/templates/<slug>/` download targets.
- Do NOT implement AI watermarking machinery.
- Do NOT auto-classify any asset as `shipped:` or `ai_generated:`.
  Every asset goes in `embedded:`.
- Do NOT silently exclude unclassified assets. The audit STOPS and
  asks; the user puts them in `embedded:`.
- Do NOT change preview generation. AI-generated images (and all
  other content assets) continue to appear in preview.pdf /
  page-NN.png the way they do today.
