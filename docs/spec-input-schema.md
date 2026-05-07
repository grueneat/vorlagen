# Spec input schema — LLM consumption guide

**If you are an LLM authoring a `build.py` from a spec file, follow this contract.**

The spec file (`spec.yml`) describes a template in a brand-neutral, human-readable form.
Your job is to translate it into a valid `build.py` using the `sla_lib` DSL.
This document maps every spec key to the DSL construct it resolves to.

Schema: `shared/template-spec.schema.yaml` (JSON Schema draft-2020-12 in YAML).

---

## Worked example

Below is a complete 50-line spec for a Postkarte A6 equivalent template, followed by the
corresponding `build.py` setup block (~18 lines using `Brand`).

### Input: spec.yml (~50 lines)

```yaml
template:
  id: postkarte-a6-demo
  title: "Postkarte A6 Kampagne (demo)"
  size: A6
  orientation: portrait
  facing_pages: false
  bleed_mm: 3

brand: gruene-noe

styles:
  headline-weiss:
    parent: ci/headline-ultra
    fontsize: 27
    fcolor: White
    align: 1
  kontakt:
    parent: ci/impressum
    fontsize: 8

pages:
  - layout: cover
    background: Dunkelgrün
    headline:
      style: headline-weiss
      lines:
        - { text: "Bei dir wachsen", color: White }
        - { text: "die Sorgen,", color: Gelb }
        - { text: "nicht die Steuern.", color: White }
    impressum:
      text: "Medieninhaber: Grüne NÖ, Neue Herrengasse 10/2, 3100 St. Pölten"
    page_number: false

  - layout: back
    contact:
      lines:
        - "Maria Musterfrau"
        - "Gemeinderätin, Musterstadt"
        - "maria@gruene-noe.at"
      pos:
        anchor: bottom-left
    page_number: false

layouts:
  cover:
    page_background: { color: Dunkelgrün }
    headline_pos:
      anchor: top-center
    impressum_pos:
      anchor: bottom-center
  back:
    contact_pos:
      anchor: bottom-left
```

### Output: build.py setup block (~18 lines)

```python
from sla_lib.builder import Document, Page, Brand, Color
from sla_lib.builder import ParaStyle, CharStyle, TextFrame, Run, Anchor
from sla_lib.builder import blocks

doc = Document(
    brand=Brand.gruene_noe(),
    title="Postkarte A6 Kampagne (demo)",
    template_id="postkarte-a6-demo",
    facing_pages=False,
    extra_doc_attrs={
        "FIRSTNUM": "1",
    },
)

doc.add_para_style(ParaStyle(
    name="headline-weiss",
    PARENT="Headline sehr wichtig",
    fontsize=27,
    fcolor="White",
    align=1,
))
doc.add_para_style(ParaStyle(
    name="kontakt",
    PARENT="ci/impressum",
    fontsize=8,
))
```

The `brand=Brand.gruene_noe()` call injects the 113 identical `extra_doc_attrs` keys,
the 34 identical `extra_pdf_attrs` keys, the 7 CI colors, the 8 CI paragraph styles, and
the 4-layer stack automatically.  You only add what differs.

---

## Spec-key to DSL-construct mapping table

| Spec key | DSL construct | Notes |
|---|---|---|
| `template.id` | `Document(template_id=...)` | Slug used in gallery paths |
| `template.title` | `Document(title=...)` | Human label |
| `template.size` | `doc.add_page(size=..., ...)` | `"A6"` → `size="A6"` |
| `template.orientation` | `doc.add_page(orientation=...)` | `"portrait"` or `"landscape"` |
| `template.facing_pages` | `Document(facing_pages=...)` | Bool |
| `template.bleed_mm` | `doc.add_page(bleed_mm=...)` | Per-page override or `Document` default |
| `brand: gruene-noe` | `Document(brand=Brand.gruene_noe())` | Only value today |
| `styles.<name>` | `doc.add_para_style(ParaStyle(name=<name>, PARENT=<parent>, ...))` | Only changed fields |
| `styles.<name>.parent` | `ParaStyle(PARENT=...)` | Reference a CI style or another template style |
| `styles.<name>.fcolor` | `ParaStyle(fcolor=...)` | Must be a registered colour name |
| `pages[].layout` | Named layout from `layouts:` applied as defaults | Python function in `build.py` |
| `pages[].background` | `page.add(blocks.PageBackground(color=..., ...))` | Full-bleed Polygon at layer 0 |
| `pages[].headline.lines[]` | `TextFrame(runs=[Run(text=..., fcolor=..., separator="para"), ...])` | One Run per line |
| `pages[].headline.style` | `Run(paragraph_style=<style>)` on each run | Applied at paragraph break |
| `pages[].body` | `blocks.ColumnTextStory(...)` or single `TextFrame` | ColumnTextStory when columns > 1 |
| `pages[].impressum` | `page.add(blocks.Impressum(text=..., pos=...))` | Impressum block |
| `pages[].contact.lines[]` | `page.add(blocks.ContactBlock(lines=[...], pos=...))` | ContactBlock |
| `pages[].page_number: true` | `page.add(blocks.PageNumber(pos=...))` | PageNumber block |
| `pages[].page_number: false` | (omit block) | No page number on this page |
| Symbolic colour `brand.primary` | `"Dunkelgrün"` | Resolve at emit time to `Color.DUNKELGRUEN` |
| Symbolic colour `brand.secondary` | `"Hellgrün"` | |
| Symbolic colour `brand.accent` | `"Gelb"` | |
| `layouts.<name>` | Python function `def apply_<name>_layout(page, ...)` in `build.py` | Not a DSL construct |

---

## Validation guidance

The schema is strict (`additionalProperties: false` at every level).
An LLM emitting spec.yml should:

1. Validate the YAML parses cleanly: `python3 -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('spec.yml').read_text())"`
2. Validate against the schema before passing to the converter:
   ```python
   import yaml, jsonschema, pathlib
   schema = yaml.safe_load(pathlib.Path("shared/template-spec.schema.yaml").read_text())
   spec   = yaml.safe_load(pathlib.Path("spec.yml").read_text())
   jsonschema.validate(spec, schema)   # raises jsonschema.ValidationError on failure
   ```
3. The error message from jsonschema names the offending key and the allowed values,
   matching the pattern used by the DSL's own `__post_init__` validators.

Common mistakes:
- Colour names must match `Document.add_color()` registrations exactly (case-sensitive).
  CI colours registered by `Brand.gruene_noe()`: `Black`, `White`, `Registration`,
  `Dunkelgrün`, `Hellgrün`, `Gelb`, `Magenta`.
- `styles.<name>.parent` must reference a CI style (`ci/<name>`) or another style
  defined in the same spec.  Forward references within `styles:` are resolved by the
  converter; cycles are rejected.
- `pages[].headline.lines[].style` references a paragraph style defined in `styles:` or
  in the brand CI stack (prefix `ci/`).
- `layouts` keys must match the `^[a-z][a-z0-9_-]*$` pattern.

---

## Named layouts

Named layouts (`layouts:`) declare default block positions.  They are **not** a DSL
construct — the spec→build.py converter renders each layout as a Python function in
`build.py`:

```python
def apply_cover_layout(page: Page, **slots) -> None:
    page.add(blocks.PageBackground(
        color=slots.get("background", Color.DUNKELGRUEN),
        bleed_mm=3,
    ))
    if "headline" in slots:
        page.add(TextFrame(
            anchor=Anchor(h="center", v="top", margin_mm=10),
            runs=slots["headline"],
        ))
    if "impressum" in slots:
        page.add(blocks.Impressum(
            text=slots["impressum"]["text"],
            anchor=Anchor(h="center", v="bottom", margin_mm=5),
        ))
```

The layout function is called for each page that references it:

```python
page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
apply_cover_layout(page,
    background="Dunkelgrün",
    headline=[
        Run(text="Bei dir wachsen", fcolor="White", separator="para"),
        Run(text="die Sorgen,",     fcolor="Gelb",  separator="para"),
        Run(text="nicht die Steuern.", fcolor="White", separator="para"),
    ],
    impressum={"text": "Medieninhaber: Grüne NÖ, ..."},
)
```

Named layouts are versioned as part of `build.py` source — no separate versioning scheme
is needed.  **Open question (P3):** if layouts are shared across multiple templates, move
them to `shared/layouts/<name>.py`.

---

## DSL blocks used by spec output

| Block | When emitted | Corpus evidence |
|---|---|---|
| `blocks.PageBackground` | `pages[].background` is set | Postkarte 2×, Zeitung Titelseite |
| `blocks.PageNumber` | `pages[].page_number: true` | 12× in Zeitung |
| `blocks.Impressum` | `pages[].impressum` is set | Postkarte, Zeitung |
| `blocks.ContactBlock` | `pages[].contact` is set | Postkarte |
| `blocks.ColumnTextStory` | `pages[].body.columns >= 2` | 84× in Zeitung |

All five blocks are defined in `tools/sla_lib/builder/blocks.py` and accept `Brand` for
default-value resolution.

---

## What spec input cannot express

The spec schema is intentionally minimal.  Use the DSL directly in `build.py` for:

- **Sub-frame-level geometry** (exact `x_mm/y_mm/w_mm/h_mm` on a specific element).
- **Multiple images** per page (use `ImageFrame` directly).
- **Master pages** (use `doc.add_master()` and `doc.add_facing_pages_masters()`).
- **Soft shadows** (`_Frame.soft_shadow=SoftShadow(...)`).
- **Corner radius** (`_Frame.corner_radius_mm=...`).
- **Per-frame clipping paths** (`_Frame.custom_path=...`).
- **Inline images in text** (`ImageFrame` embedded in a story via `Run`).

These are `build.py`-level details; the spec captures content and layout intent,
not fine-grained rendering instructions.
