# Asset policy — brand embedded, content external, nothing shipped

> **Active rule (brand-team decision 2026-05-13, locked):** brand-locked
> assets are EMBEDDED inline in the SLA. Content / AI / supplementary
> assets are referenced via repo-relative paths but NOT bundled (the
> SLA references them, the render pipeline resolves them from
> `shared/assets/<slug>/` for preview generation, the downloaded SLA
> shows missing-image placeholders the user replaces with their own
> content). NO ZIP. NO BUNDLED CONTENT.

## Three buckets

Every template's `meta.yml::asset_policy` classifies each asset into
one of three buckets:

### `embedded:` — brand-locked, inlined in the SLA

These are part of the template's identity and must never change
without brand-team sign-off:

- Party / organisation logos (`gruene-logo-*`, `bund-logo-*`, …)
- Social-media icon glyphs (`social-media-icon-facebook.png`,
  `bluesky-weiss.png`, etc.)
- Decorative background polygons / textures that define a panel
- Brand-locked illustrations (`wahlkreuz.*`, fold-mark crosshatches)

The converter emits these as
`ImageFrame(inline_image_data=…, inline_image_ext=…)` via
`tools/sla_lib/builder/primitives.py::pack_inline_image`. They become
part of the SLA's bytes; the downloaded file is self-contained for
brand.

### `external:` — content referenced, not bundled

User-replaceable content the SLA references via a path relative to
the SLA's directory:

- Candidate portraits, headshots
- AI-generated demo illustrations
- Stock photo backgrounds the user would swap for their own
- Anything brand-team has NOT signed off as brand-locked

The converter emits these as
`ImageFrame(image='../../shared/assets/<asset-dir>/<basename>')`. When
Scribus opens the SLA at `templates/<slug>/template.sla` it `chdir`s
to the SLA's parent, then resolves the path to
`shared/assets/<asset-dir>/<basename>` — the preview pipeline finds
the file and renders the demo content.

When the user downloads the SLA standalone, the relative path
resolves to nothing (no `../../shared/assets/…` alongside their
download) — Scribus shows a missing-image placeholder where each
external asset should be. The user replaces with their own image.

This matches the brand-team's intent: **content assets and AI
imagery must NEVER ship to print without explicit human replacement.**
Not bundling them is the strongest possible enforcement of that rule.

### `shipped:` — reserved (must be empty)

Reserved for a hypothetical future zip-packaging flow. Brand-team
has decided NOT to ship content assets at all, so this list MUST be
empty in every committed template. The schema accepts non-empty
values for forward compatibility; `tools/asset_policy_audit.py`
rejects them with an actionable error message.

## Schema

```yaml
# shared/asset-policy.schema.yaml — jsonschema Draft 2020-12
asset_policy:
  embedded: [list of basenames]   # required, may be empty
  external: [list of basenames]   # required, may be empty
  shipped:  [list of basenames]   # required, MUST be empty (audit-enforced)
```

The three lists are PAIRWISE DISJOINT — no basename in more than one
bucket. Together `embedded ∪ external` must cover every asset on
disk in `shared/assets/<slug>/` that the SLA actually references.

## Where the classification lives

Each template's `meta.yml` carries an `asset_policy:` block:

```yaml
asset_policy:
  embedded:
    - gruene-logo-bund-weiss-cmyk.png
    - social-media-icon-facebook.png
    - social-media-icon-instagram.png
    - bluesky-weiss.png
    # ...brand assets...
  external:
    - plakat-dunkel-fuer-flyer.png         # content placeholder
    - green-pine-trees-covered-with-fog-crop.png  # photo placeholder
  shipped: []
```

`tools/asset_policy_audit.py` enforces:

1. **Coverage** — every disk file is in `embedded:` OR `external:`.
2. **Disjoint** — same basename in only one bucket.
3. **Shipped-empty** — non-empty `shipped:` rejected with the
   brand-team-decision error message.

## Auto-classification heuristic

When the user hasn't classified an asset yet, `bin/idml-import` MAY
suggest a bucket based on filename:

- `*logo*`, `*social-media-icon*`, `wahlkreuz*`, `*-weiss.png`,
  `*-cmyk.png` → presume **embedded** (brand).
- `portrait*`, `photo*`, `themen-*`, `kandidat-*`, `*ai-*`,
  `*generated-*` → presume **external** (content).
- Anything else → STOP, ask.

The skill MAY auto-classify based on the regex but MUST surface the
proposed classification for user confirmation before writing it to
`meta.yml`. No silent classification.

## v2-falzflyer (the canonical case)

`templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` references
12 assets in `shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/`:

```yaml
asset_policy:
  embedded:                                          # 8 brand-locked
    - bluesky-weiss.png
    - gruene-logo-bund-weiss-cmyk.png
    - mail-weiss.png
    - social-media-icon-facebook.png
    - social-media-icon-instagram.png
    - social-media-icon-tiktok.png
    - social-media-icons-weiss.png
    - website-weiss.png
  external:                                          # 4 content / photos
    - green-pine-trees-covered-with-fog-crop.png    # page-2 page-background photo
    - green-pine-trees-covered-with-fog-srgb.png    # derivative (kept for build reproducibility)
    - green-pine-trees-covered-with-fog.jpg         # source (kept for reference)
    - plakat-dunkel-fuer-flyer.png                  # cover placeholder
  shipped: []
```

Resulting SLA: 7 inline ImageFrames (one anname per logo / icon) +
2 PFILE references (the 2 actually-referenced photos at u2cd and
u3a0; the other 2 are derived / unused). SLA size: 391 KB
(down from 18 MB when content was inlined under PR #83's transitional
embed-everything rule). Self-contained for brand; placeholder for
content.

## Preview render: AI substitution for `external:` assets

**Active rule (locked 2026-05-14):** in the preview pipeline (gallery
thumbnails + click-through hires), every `external:` ImageFrame gets
its PFILE substituted with a library AI image cropped to the frame's
exact dimensions. The committed `template.sla` (what the user
downloads) still references the original external path — substitution
only happens in `template-preview.sla` / `build_preview()`.

Why:
- Scribus 1.6.x has no native aspect-FILL ("cover") mode. Frames
  whose source asset doesn't match the frame's aspect render either
  with letterbox/pillarbox (aspect-fit, SCALETYPE=0) or off-frame
  (SCALETYPE=1 + IDML-derived LOCALSCX). Both look broken in previews.
- Pre-cropping the library image to the frame's exact W×H via
  `tools/sla_lib/builder/library.py::inject_into_frame` produces a
  source image whose aspect matches the frame, so SCALETYPE=0 fills
  cleanly with no gap and no crop guesswork.
- The library is already AI-generated, watermarked ("Symbolfoto —
  KI-generiert"), and indexed by topic/tags — `shared/sample-images/`.

How it's wired:
- IDML-imported templates that have `external:` content frames emit a
  `build_preview()` function in `build.py` that walks each external
  ImageFrame, selects a library image (by tag match — `themen`,
  `portrait`, `kontext` — or explicit `meta.yml::frame_library_map`
  override), and calls `inject_into_frame(frame, img, target_w_mm,
  target_h_mm)`.
- `_select_render_source` in `tools/render_pipeline.py` prefers
  `template-preview.sla` over `template.sla` when present, so the
  gallery render picks up the AI-substituted variant automatically.
- If a library image at the exact size doesn't exist, the build
  generates one via `tools/codex_image_gen.py` (cached under
  `shared/sample-images/<topic>-<W>×<H>.jpg`) — same prompt as the
  source library entry, regenerable from manifest.

Brand-team safety:
- Library images are watermarked permanently (R-WATERMARK-CROP) so an
  accidental "this looks production-ready" gallery shot is impossible.
- Brand `embedded:` assets are never substituted — only `external:`.
- The downloaded SLA still has `external:` PFILE pointing at the
  original asset (or no asset, if `shipped: []` is enforced) — the
  user still gets a "your content goes here" placeholder.

## What does NOT happen

- The skill does NOT silently embed AI imagery into the **committed**
  `template.sla` — that's still the brand-team-locked surface. AI
  substitution lives only in the preview variant.
- The skill does NOT silently ship content (no zip) — users still
  get the BRAND template and put their own content in.
- The skill does NOT skip the classification step — every asset must
  land in `embedded:` or `external:`.
- The skill does NOT crop demo images on-the-fly with empirical
  `local_offset_mm` guesses. Use `inject_into_frame` so the source
  matches the frame and Scribus's aspect-fit fills cleanly. The
  "crop the IDML's literal local_offset" branch is the old approach
  and is deprecated for `external:` assets.

## Rationale

Three groups of stakeholders are protected by the bucket structure:

- **Brand team:** brand assets are unchangeable in the user's hands.
  Inlining via base64 is the strongest possible enforcement.
- **Designers / template users:** they get a template that opens and
  shows brand exactly, with explicit "your content goes here"
  placeholders where their own portraits / photos belong.
- **Print operators:** they never receive an SLA where placeholder
  AI content ships as real content — the SLA simply doesn't carry
  the placeholders.

The split matches the actual editing intent and is enforced
mechanically (audit + converter); no documentation that gets ignored.
