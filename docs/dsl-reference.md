# DSL Reference

Public API exported by `tools/sla_lib/builder/__init__.py`. The DSL is the
*only* sanctioned path for writing new SLA files — direct XML manipulation is
not supported.

## Top-level

| Symbol | Purpose |
|---|---|
| `Brand` | Brand profile — bundles palette, styles, layers, and Scribus doc/PDF defaults. Pass to `Document(brand=...)`. |
| `Document` | The root document object. Build pages, then call `save()`. |
| `Page` | Returned by `Document.add_page()` / `add_master()`. Add primitives via `page.add(...)`. |
| `DocumentLayer` | Per-document layer override (replaces the CI 4-layer brand stack). |
| `ParaStyle` | Per-document paragraph style. Optional fields use `None` to mean "inherit". |
| `CharStyle` | Per-document character style. |
| `SoftShadow` | Frame-level soft-shadow effect (`_Frame.soft_shadow=...`). |

## Frame primitives

| Class | PTYPE | Purpose |
|---|---|---|
| `TextFrame` | 4 | Text content. Use `style=...` for the paragraph default style; `runs=[Run(...)]` for per-run formatting. |
| `ImageFrame` | 2 | Bitmap image. Use `image=...` (relative path) for the file. |
| `Polygon` | 6 | Vector shape — `shape="rectangle"` (default), `"ellipse"`, or arbitrary path via `custom_path=...`. |
| `Line` | 5 | Convenience for a 2-point line. |

All frames inherit `_Frame` and accept:

- `x_mm`, `y_mm`, `w_mm`, `h_mm` — geometry (mm)
- `anchor` — alternative to xy: `"top-center"`, `"bottom-20"`, `("center", 30)`, etc.
- `rotation_deg`, `layer`, `anname`
- `clip_edit` — mark the frame as having a custom clip region (CLIPEDIT=1)
- `custom_path` — emit FRTYPE=3 with verbatim path data
- `corner_radius_mm` — emit FRTYPE=2 with RADRECT (rounded rectangles)
- `soft_shadow` — frame-level shadow effect
- `fill_rule` — for FRTYPE=3 paths (0=nonzero, 1=evenodd)

### Clip-rect auto-generation (`TextFrame`)

When `TextFrame(clip_edit=True)` is used **without** an explicit `custom_path=`
and without a `corner_radius_mm`, the DSL automatically emits FRTYPE=3 with a
canonical axis-aligned rectangle path matching the frame dimensions. This is
the correct Scribus encoding for text frames that have `CLIPEDIT=1` but no
special clip shape.

```python
# DSL auto-emits FRTYPE=3 + rect path — no custom_path= needed:
TextFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=40, clip_edit=True)

# Explicit custom_path= overrides the auto-generated rect path:
TextFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=40, clip_edit=True,
          custom_path="M0 0 C40 0 80 20 80 40 L0 40 Z")
```

The converter (`tools/sla_to_dsl.py`) detects CLIPEDIT=1 + FRTYPE=3 frames
whose stored path is already a rectangle and **omits** `custom_path=` from the
emitted build.py — the DSL regenerates the path automatically. Only non-rect
bezier paths and non-rectangular polygons are emitted verbatim.

## `Run` — per-run text formatting

```python
TextFrame(runs=[
    Run(text="Bei dir wachsen", fcolor="White", fshade=100,
        separator="para", paragraph_style="Headline sehr wichtig"),
    Run(text="die Sorgen,", separator="para",
        paragraph_style="Vollkorn Headline sehr wichtig"),
])
```

Fields:

- `text`, `font`, `fontsize`, `fcolor`, `fshade`, `fontfeatures`, `features`, `kern`
- `char_style` — references a registered `CharStyle` (CPARENT)
- `paragraph_style` — PARENT on the trailing `<para/>` element (style for the
  paragraph just ENDED at this run)
- `separator` — `"para"` / `"breakline"` / `"tab"` / `"breakcol"` / `"breakframe"`
- `var` — `"pgno"` inserts `<var name="pgno"/>` (auto page-number)

## Soft hyphens (`\xad`)

The DSL passes Unicode soft hyphens (`U+00AD`, `\xad`) through verbatim. They
are an **escape hatch** for words Scribus's German hyphenation dictionary
gets wrong, e.g. compound nouns or proper names where the auto-hyphen falls
on a syllable boundary you want to override.

```python
Run(text="vier\xadzei\xadli\xadge")  # Forces "vier-zei-li-ge"
```

Avoid soft hyphens for routine line-break control — let the hyphenation
engine do its job. The Plakat A1 reproduction uses 7 occurrences total
across 3 long words; the Zeitung uses 0.

## Brand — single source of truth for all CI documents

`Brand.gruene_noe()` loads the Grüne NÖ identity from `shared/ci.yml` +
`shared/ci-defaults.yml` and bundles:

- **Palette** — 7 CI colors (Black, White, Registration, Dunkelgrün, Hellgrün, Gelb, Magenta)
- **Paragraph styles** — `ci/default`, `ci/headline-ultra`, `ci/headline-vollkorn-italic`, `ci/body-12`, `ci/body-11`, `ci/impressum`, `ci/stoerer`, `ci/cta`
- **Layer stack** — Hintergrund, Text, Hilfslinien, Bilder (4 layers)
- **113 `extra_doc_attrs`** — locale defaults, ICC profile names, Scribus runtime state
- **34 `extra_pdf_attrs`** — PDF export profile (ICC intents, spot colour, compression)

Pass it to `Document(brand=...)` and the brand injects everything automatically.
Templates declare only their *additions* via `doc.add_color(...)` and
`doc.add_para_style(...)`. Per-template `extra_doc_attrs=` / `extra_pdf_attrs=`
override brand defaults (template values win).

```python
doc = Document(
    brand=Brand.gruene_noe(),        # injects palette, styles, layers, 113+34 attrs
    title="Postkarte",
    template_id="postkarte-a6-kampagne",
    facing_pages=False,
    column_gap_default_pt=11,
    deffont="Gotham Narrow Book",
    defsize=12,
    hcms=True,
    extra_doc_attrs={                # only the ~23 keys that differ per template
        "PEN": "Dunkelgrün", ...
    },
    extra_pdf_attrs={                # only the ~11 keys that differ per template
        "UseSpotColors": "1", ...
    },
)
# Template-specific additions (brand CI colors are already registered):
doc.add_color("HellgrünTransparent", rgb=(178, 212, 113))
doc.add_para_style(ParaStyle(name="Headline sehr wichtig",
    font="Gotham Narrow Ultra", fontsize=27, fcolor="White",
    align=1, linesp=23, language="de"))
doc.add_char_style(CharStyle(name="Default Character Style",
    font="Gotham Narrow Black", fontsize=12, is_default=True))
```

## Document-level overrides (without Brand)

When `brand=` is not supplied, the full set of doc/PDF attrs must be listed
explicitly. This mode exists for one-off scripts and the test suite.

```python
doc = Document(
    title="Standalone",
    template_id="standalone-test",
    facing_pages=False,
    palette_replaces_ci=True,        # only emit registered colors
    layers=[DocumentLayer(name="Hintergrund")],
    extra_doc_attrs={                # all 113 keys must be listed
        "ALAYER": "0", "AUTOL": "100", "BaseC": "#c0c0c0", ...
    },
)
doc.add_color("Green", rgb=(153, 102, 51))
```

## Linked text-frame chains

```python
a = TextFrame(x_mm=10, y_mm=10, w_mm=60, h_mm=60, anname="col-a")
b = TextFrame(x_mm=80, y_mm=10, w_mm=60, h_mm=60, anname="col-b")
c = TextFrame(x_mm=150, y_mm=10, w_mm=60, h_mm=60, anname="col-c")
a.link_to(b).link_to(c)         # fluent chain
page.add(a); page.add(b); page.add(c)
```

The DSL pre-allocates ItemIDs in chain order before emit so NEXTITEM and
BACKITEM resolve correctly. Add the frames to the page in chain order so
the pre-allocator sees them in the right sequence.

## What is NOT in the public surface

Per CONTEXT.md D2, the DSL has typed APIs for every Scribus concept the
three reference originals use; no `raw_attrs={}` escape hatch is exposed
for general use. The converter (`tools/sla_to_dsl.py`) uses the typed
APIs exclusively when emitting `build.py`, raising `UnhandledElement` if
it hits a Scribus attribute the DSL can't express.

`Document(extra_doc_attrs={...})` is the one general dict-shaped pass-
through, and is intentionally narrow: it only adds DOCUMENT-level
attributes (locale defaults, ICC profile names, etc.) that don't affect
layout or content. It does not let frames or styles take ad-hoc
attributes.
