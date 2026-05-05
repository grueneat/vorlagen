# DSL Reference

Public API exported by `tools/sla_lib/builder/__init__.py`. The DSL is the
*only* sanctioned path for writing new SLA files — direct XML manipulation is
not supported.

## Top-level

| Symbol | Purpose |
|---|---|
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
- `custom_path` — emit FRTYPE=3 with verbatim path data
- `corner_radius_mm` — emit FRTYPE=2 with RADRECT (rounded rectangles)
- `soft_shadow` — frame-level shadow effect
- `fill_rule` — for FRTYPE=3 paths (0=nonzero, 1=evenodd)

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

## Document-level overrides

```python
doc = Document(
    title="Postkarte",
    template_id="postkarte-a6-kampagne",
    facing_pages=False,
    column_gap_default_pt=11,
    deffont="Gotham Narrow Book",
    defsize=12,
    palette_replaces_ci=True,        # only emit registered colors
    layers=[DocumentLayer(name="Hintergrund")],
    extra_doc_attrs={                # converter pass-through
        "ALAYER": "0", "AUTOL": "100", "BaseC": "#c0c0c0", ...
    },
)
doc.add_color("Green", rgb=(153, 102, 51))
doc.add_para_style(ParaStyle(name="Headline sehr wichtig",
    font="Gotham Narrow Ultra", fontsize=27, fcolor="White",
    align=1, linesp=23, language="de"))
doc.add_char_style(CharStyle(name="Default Character Style",
    font="Gotham Narrow Black", fontsize=12, is_default=True))
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
