# Scribus SLA attribute semantics

A catalog of the Scribus SLA attributes the IDML→Scribus converter writes,
documenting their empirically observed behavior. Every entry tells you:

1. Where the attribute appears (`PAGEOBJECT` attr, child element, or `STYLE`).
2. The values we have observed in the wild and what they mean.
3. The converter file / line where we emit it (so you can grep back to source).
4. A "wrong-behavior" anti-example from past sessions and the resolution.

Treat this as authoritative for what the converter ships TODAY. New
behavior must be added here before it is added to the converter — that
keeps lore from being re-derived every session.

---

## SCALETYPE

**Where:** `PAGEOBJECT` attribute on image-bearing frames (`PTYPE=2` and
`PTYPE=12` Group children that carry image content).

**Values observed:**

- `SCALETYPE="0"` — *ScaleAuto*. Scribus scales the image to fit the
  frame; LOCALSCX / LOCALSCY are ignored for scaling but still affect
  cropping offsets. Used for content photos that should fill the
  frame.
- `SCALETYPE="1"` — *Free scaling*. The image renders at
  `native_mm * LOCALSCX`. Used for vector glyphs, icons, and any place
  where the image's intrinsic size matters.

**Emit site:** `tools/sla_lib/builder/primitives.py:827` —
`"SCALETYPE": str(self.scale_type)`. Also `library.py:419` (auto-fit
helpers) and `library.py:496` (the ScaleAuto branch).

**Anti-example:** Early in the 26-03 Leporello session we set
`SCALETYPE=1` everywhere because "free scaling is the safer default".
This made white-on-transparent RGBA PNGs INVISIBLE — the alpha channel
sampled at the wrong sub-pixel grid. Fix: every PNG with alpha that
needs to fill a frame uses `SCALETYPE=0`; only PDF-source frames where
the scale is hand-tuned use `SCALETYPE=1`. See
`primitives.py:781-789`.

---

## FLOP

**Where:** Text frame `DefaultStyle` attribute (under `PAGEOBJECT[PTYPE=4]`).

**Values observed:**

- `FLOP="0"` — *baseline-aligned*. Glyph ascender height drops below
  the first line; visual top of text sits below the frame's `YPOS`.
- `FLOP="1"` — *cap-height-aligned*. First line's cap height is flush
  with `YPOS`. This is the value the converter currently emits.

**Emit site:** `tools/sla_lib/builder/primitives.py:639` —
literal `"FLOP": "1"` in the default-style attribute block.

**Anti-example:** Headlines in the 26-03 Leporello "green box" looked
1–2 pt shifted up from the InDesign baseline. The cause was actually
the IDML's own positioning — not FLOP — but the team spent two
iterations toggling FLOP between 0 and 1 chasing it. Lesson: FLOP is
template-wide, not per-frame; if a single headline is off, the issue
is the frame's `YPOS` or the paragraph style's `LINESPMode`, not FLOP.

---

## LINESPMode

**Where:** Paragraph-level attribute on `STYLE`, `DefaultStyle`, and
`PARA` children of an `ITEXT`.

**Values observed:**

- `LINESPMode="0"` — *auto*. Scribus computes line spacing from font
  metrics. The default for most paragraph styles.
- `LINESPMode="1"` — *fixed*. Use the `LINESP` attribute as line
  spacing in points, ignoring font metrics. The most common explicit
  override.
- `LINESPMode="2"` — *baseline-grid*. Snap each line to the document
  baseline grid. Rarely used.
- `LINESPMode="3"` — *baseline*. Use the maximum ascender + descender
  across the line as line spacing. Not used by the converter.

**Emit site:** `tools/sla_lib/builder/primitives.py:55` — the
`PARAGRAPH_OVERRIDE_ATTRS` set lists `LINESP` and `LINESPMode`. Run
emit at `primitives.py:679` for `default_linesp_mode`.

**Anti-example:** Multi-line subheadlines on Leporello page 0 looked
overspaced. The fix attempted in commit X was to set
`LINESPMode="1"` with `LINESP="14"` globally — which over-tightened
quotes elsewhere. The right move was to scope the override to the
`runs[].paragraph_attrs={"LINESPMode": "2", "LINESP": "18.96..."}`
trail-attrs on that specific TextFrame (see leporello build.py line
229). LINESPMode is paragraph-scoped; never apply it template-wide
without measurement.

---

## HCMS

**Where:** `PAGEOBJECT` attribute on image frames (`PTYPE=2`).

**Values observed:**

- `HCMS="0"` — *honor color management* (CMS active, profiles applied).
  The default Scribus uses when an image carries a recognised ICC
  profile.
- `HCMS="1"` — *bypass CMS*. The image is rendered through Scribus's
  pass-through path, no profile conversion. The converter currently
  does not set `HCMS` explicitly — Scribus inherits its document-level
  CMS preference.

**Emit site:** Currently NOT explicit in `tools/sla_lib/builder/primitives.py`
— relies on Scribus default. When we DO want to force pass-through
(e.g. composite-AI splits where the PDF is already in target color),
the convention is to add `HCMS="1"` to the frame's attrs block.

**Anti-example:** CMYK photos on Leporello page 1 looked dull in the
preview.pdf. The user thought the converter was applying double
CMS. Fix wasn't HCMS — it was the source `.jpg` carrying an Adobe RGB
profile that Scribus correctly converted to sRGB for display. Setting
`HCMS="1"` would have HIDDEN the color, not fixed it. Lesson: HCMS is
not a "make this look right" knob; it's a "skip Scribus CMS entirely"
escape hatch.

---

## PRFILE

**Where:** `PAGEOBJECT` attribute on image frames (`PTYPE=2`).

**Values observed:**

- `PRFILE="sRGB display profile (ICC v2.2)"` — the converter's literal
  default. Scribus interprets it as "use the sRGB profile shipped
  with Scribus". The string must match a profile Scribus has in its
  library, otherwise the frame falls back to the document profile.

**Emit site:** `tools/sla_lib/builder/primitives.py:830` —
`"PRFILE": "sRGB display profile (ICC v2.2)"`.

**Anti-example:** Earlier we tried `PRFILE=""` (empty) hoping Scribus
would auto-detect. Result: the embedded JPEG profile was used — fine
for sRGB-tagged photos, wrong for CMYK PSDs (which got rendered as
RGB). Always set PRFILE explicitly; Scribus uses it as the *source*
profile for the image data.

---

## LOCALSCX

**Where:** `PAGEOBJECT` attribute on image frames (`PTYPE=2`). Paired
with `LOCALSCY`.

**Values observed:**

- `LOCALSCX="1.0"` — image renders at its native pixel-to-pt ratio
  (1 pixel = 1 pt at 72 dpi). The frame's `WIDTH`/`HEIGHT` may be
  larger than the rendered image.
- `LOCALSCX="0.5"` — image renders at half its native pt size. With
  `SCALETYPE=1` this scales the image inside the frame; with
  `SCALETYPE=0` it only affects the *crop offset* coordinate space
  (see "scale base" note below).
- Fractional values like `0.430959` are typical for IDML imports —
  IDML's `ItemTransform` matrix scale gets translated to LOCALSCX
  directly.

**Scale base:** When `SCALETYPE=0` (ScaleAuto), Scribus uses the
image's NATIVE intrinsic size as the base for LOCALSCX, not the
frame's size. So `LOCALSCX=1.0` + auto-scale puts the image at native
size and lets Scribus then scale-to-fit. The `local_offset_mm` value
in our builder is "mm at LOCALSCX=1", not "mm of the displayed image"
— see `library.py:522` for the explicit comment.

**Emit site:** `tools/sla_lib/builder/primitives.py:823` —
`"LOCALSCX": _fmt_num(scx)`.

**Anti-example:** The 26-03 Leporello had every social-media icon
mispositioned by 100–200% of its width. The fix involved Pattern 9
adjusting frame height; the LOCALSCX was correct all along. Lesson:
LOCALSCX is the IDML transform scale, NOT the visual size — verify
with `_fmt_num(0.430959)` matching the IDML's `ItemTransform`
mm-to-mm ratio before adjusting.

---

## EMBEDDED

**Where:** `PAGEOBJECT` child element `<ImageEffect EMBEDDED="..."/>`,
and an attribute on the `PAGEOBJECT` itself when the image data is
inlined.

**Values observed:**

- `EMBEDDED="0"` — image is REFERENCED by `PFILE` only; the bytes live
  on disk. The default for content photos and AI vector splits.
- `EMBEDDED="1"` — image bytes are inlined as base64 inside the SLA
  via `<ImageData>` or `ImageFrame.inline_image_data`. Used for brand
  assets that MUST travel with the SLA (P11: embedded bucket).

**Emit site:** `tools/sla_lib/builder/primitives.py:848` —
`attrs["EMBEDDED"] = "0"` (the default branch); the embedded-true
branch lives in the inline-image emit path (see `Run.inline_image_data`
handling).

**Anti-example:** Brand-team rule P11 (asset_policy.md): embedded
brand assets ship inlined; content assets ship as external `PFILE`
references. Early iterations on Leporello had `gruene-logo` as a
PFILE reference, which meant the SLA broke when copied to a customer
machine. Fix: classify in `meta.yml::asset_policy::embedded:` and let
the builder inline it. The `EMBEDDED` attribute is a function of the
asset_policy bucket, not an opinion the converter forms per-frame.

---

## Frame rotation (w/h swap)

**Where:** `PAGEOBJECT` `ROT=` attribute (rotation in degrees,
positive counter-clockwise). Paired with `WIDTH` / `HEIGHT` that DO
NOT swap when `ROT=90` or `ROT=270`.

**Values observed:**

- `ROT="0"` — no rotation. Width = horizontal extent.
- `ROT="90"` / `ROT="270"` — rotated 90° (sideways). **Scribus stores
  `WIDTH` and `HEIGHT` in the frame's LOCAL coordinate system, NOT
  the page system.** A 90°-rotated 100×30 frame has `WIDTH=100`,
  `HEIGHT=30` in the SLA, but visually occupies a 30×100 page rect.
- `ROT="180"` — upside down. Width / height are unchanged.

**Emit site:** `tools/sla_lib/builder/primitives.py:836` —
`"ROT": _fmt_num(self.rotation_deg)`. See also `primitives.py:645`
for TextFrame, `:899` for Image, `:1000` for Polygon.

**Anti-example:** The Zeitung's hero panel `u2950` is rotated 90° —
build-side `frame_bbox_mm` originally returned the LOCAL bbox, which
broke the brand-bleed coverage test (the bleed-covered area was the
LOCAL extent, not the rotated visual extent). Fix:
`frame_bbox_mm(frame, page)` was extended to compute a rotation-aware
visual bbox by transforming the four corners. See
`sla_lib/tests/test_zeitung_geometry.py:168`. Lesson: **never assume
WIDTH==visual-width when ROT != 0**; always use the
rotation-aware helper for any geometry that must reason about page
coordinates.

---

## How to extend this catalog

When the converter starts writing a new attribute or you observe a
non-obvious Scribus behavior:

1. Add a new section here using the template above (Where / Values
   observed / Emit site / Anti-example).
2. Pin the emit site with a `tools/...:LINE` reference so grep finds
   the implementation.
3. Capture at least ONE empirically-tested anti-example: a thing we
   tried that didn't work and why. This is the catalog's primary
   value — Scribus's "what each attribute does" is opaque in places
   and the corpus of bad attempts is more useful than the docs.
4. Reference this doc from any new `inject.yml` `reason` field that
   mentions the attribute, so future readers find the catalog
   immediately.

This catalog is the alternative to re-deriving SLA behavior each
session.
