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
`PARA`/`<trail>` children of an `ITEXT`.

**Values observed (Scribus 1.6.5):**

| Value | Documented as | Empirical behaviour (issue #40-followup measurements) |
|---:|---|---|
| `0` | *auto/font-metric* | Font-metric rendering when no LINESP is set; when LINESP is set, the value is honoured but with a font-family-dependent offset (Gotham Narrow Ultra: rendered = LINESP + ~7pt; Vollkorn Black Italic: rendered = LINESP exactly; pure single-font Gotham frames: rendered = LINESP exactly). |
| `1` | *fixed (LINESP literal)* | When emitted by the converter as default (no LINESP attr), Scribus renders at font-metric. Behaviour with explicit LINESP not separately measured — the converter uses `0` for explicit overrides. |
| `2` | *baseline-grid* | **Broken with sub-metric LINESP.** Renders at ~font-metric × 1.5 regardless of the LINESP value (LINESP=27 and LINESP=21 both rendered at 46.23pt for 30pt Gotham Narrow Ultra). Possibly snaps to the document baseline grid but ignores per-paragraph LINESP. Never use LINESPMode=2 with sub-metric LINESP. |
| `3` | *max ascender+descender* | Not used by the converter; not separately measured. |

**Empirical sim data (Gotham Narrow Ultra 30pt, mixed-font 2-line frame, baseline gap = 27.66pt):**

| LINESPMode | LINESP | Rendered |
|---:|---:|---:|
| 1 | — | 34.30 |
| 0 | 27.0 | 34.23 |
| 0 | 24.0 | 31.23 |
| 0 | **21.0** | **27.99** ✓ |
| 0 | 18.0 | 24.99 |
| 2 | 27.0 | 46.23 |
| 2 | 21.0 | 46.23 (LINESP ignored) |

For Vollkorn Black Italic 23pt (baseline 20.48): `LINESPMode=0 +
LINESP=20.48` → renders exactly 20.48pt. For pure single-font Gotham
frames (no mixed Vollkorn line): `LINESPMode=0 + LINESP=27` → renders
exactly 27pt.

**Emit site:** `tools/sla_lib/builder/primitives.py:55` — the
`PARAGRAPH_OVERRIDE_ATTRS` set lists `LINESP` and `LINESPMode`. Run
emit at `primitives.py:679` for `default_linesp_mode`.

**Converter rule** (`tools/idml_to_dsl.py:2887` / `:3037`): emit
`LINESPMode=1` when the IDML CSR `<Properties><Leading>` is below
fontsize × 1.45, otherwise `LINESPMode=2 + LINESP=<authored>`. This
preserves the existing rendering for the common case where authored
Leading is generous. Per-Run overrides for sub-metric leadings (where
LINESPMode=2 is broken) live in `templates/<slug>/build.py` with
`# P5/inject` comments — see `templates/26-03-leporello-…/build.py`
for the worked example.

**Inconsistent-pattern check:** `<para>` and `<trail>` inside the same
PAGEOBJECT MUST agree on (LINESPMode, LINESP). When the trail set
`LINESPMode=2 + LINESP=X` but intermediate `<para>` separators set
`LINESPMode=1` (no LINESP), Scribus uses the `<para>`'s rule and the
trail's LINESP doesn't take effect. `_psr_trail_attrs_for_story` now
mirrors `_walk_story`'s downgrade rule to keep both consistent.
`tools/line_spacing_full_audit.py --probe <anname>` surfaces the per-
frame `<para>`/`<trail>` LINESPMode+LINESP table and flags
inconsistencies.

**Anti-example:** Multi-line headlines on the 26-03 Leporello cover
rendered at +18pt drift when the converter emitted `LINESPMode=2 +
LINESP=27` (sub-metric for Gotham Narrow Ultra 30pt). Reverting to
`LINESPMode=1` (auto) brought drift back to +10pt; using
`LINESPMode=0 + LINESP=21` (empirically calibrated) closed it to
+0.5pt. LINESPMode is paragraph-scoped; never apply it template-wide
without measurement via `tools/line_spacing_sim.py`.

**Mixed-font frames are a special case:** Scribus's per-line font
metrics dominate, so no single (LINESPMode, LINESP) reconciles
Gotham→Vollkorn→Gotham transitions. The fix is to split the frame
into single-line TextFrames at calibrated y_mm positions (see
`templates/26-03-leporello-…/build.py` u16c → u16c, u16c_l2,
u16c_l3).

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

## Image visibility — SCALETYPE=1 + RGBA white-on-transparent

**Where:** ImageFrame `PAGEOBJECT` with `isInlineImage="1"` and
ImageData carrying a RGBA PNG that's mostly white-on-transparent.

**The bug:** Scribus 1.6.5 silently renders such frames as fully
transparent when ALL of:

1. `SCALETYPE="1"` (free scaling)
2. `LOCALSCX`/`LOCALSCY` ≤ ~0.10 (high downscale)
3. Source PNG is RGBA mostly transparent with white-only pixels (no
   colour data, only alpha-modulated white).

The Scribus CMYK conversion path mishandles such PNGs at small render
sizes and outputs zero ink. Documented in
`tools/sla_lib/builder/primitives.py:807-813`.

**Confirmed cases (26-03 Leporello):**

- `u141` (DIE GRÜNEN logo): 17.8×15.6 mm frame, composite PNG 4384×?
  RGBA at LOCALSCX=0.447, SCALETYPE=1 → 0% ink in preview, 43% in
  baseline. Fixed by switching to `image=gruene-logo-bund-weiss-cmyk.png`
  + `scale_type=0`.
- `u3e7/u3f0/u3f5` (left-column social media icons): 3.35×3.30 mm
  frames, composite PNG 4384×1267 RGBA at LOCALSCX=0.09, SCALETYPE=1
  → 0% ink in preview. Fixed by switching to per-icon PNGs
  (`social-media-icon-facebook.png`, etc.) + `scale_type=0`.

**Mitigation when a Phase E5 `image_frame_visibility_audit` run
reports `invisible_in_preview`:**

1. Switch from `inline_image_data` to a direct `image=` path
   referencing a per-icon asset file.
2. Set `scale_type=0` (fit-to-frame) so Scribus doesn't take the
   SCALETYPE=1 code path that triggers the bug.
3. Drop `local_offset_mm` — the per-icon file doesn't need cropping.
4. Re-render and re-run the visibility audit to confirm ratio > 0.30.

**Detection:** `tools/image_frame_visibility_audit.py` (Phase E5)
flags any frame where preview ink density < 30 % of baseline ink
density. The pre-existing `image_audit` reports COUNT mismatches
between `pdfimages -list` and build.py `ImageFrame` calls but
doesn't check per-frame visibility — the new audit closes that gap.

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
