"""26-03-flyer-a6-hochformat-quadrat-in-bild — DSL build entry point.

Auto-generated from 26-03-Flyer A6 Hochformat Quadrat in Bild.idml by tools/idml_to_dsl.py.
Hand-edit thereafter; this file is the source of truth.

NOTE: bleed_mm=0 below — emit a trim-only MediaBox so the rendered
PDF compares directly against the InDesign baseline (which exports
with trim-only by default). For print prep, restore the IDML's
authored bleed (preserved in IDML preferences).

Falz lines are NOT emitted by the converter — add manually post-bootstrap
matching templates/kandidat-falzflyer-din-lang/build.py: import FoldLine
from sla_lib.builder.blocks and instantiate at panel boundaries x=99/198 mm.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))

from sla_lib.builder import (  # noqa: E402
    Brand,
    Document,
    DocumentLayer,
    TextFrame,
    ImageFrame,
    Polygon,
    PolyLine,
    Run,
    ParaStyle,
    Anchor,
    pack_inline_image,
)

INJECT_MAP: dict[str, str] = {}

def _add_styles(doc: Document) -> None:
    """Paragraph styles — populated by tools/idml_to_dsl.py Phase G."""
    # (no paragraph styles in this task-3 skeleton)
    return None

def _add_page_0(doc: Document, page) -> None:
    """Render page 1 items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def _add_page_1(doc: Document, page) -> None:
    """Render page 2 items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def _add_page_2(doc: Document, page) -> None:
    """Render page 3 items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def _add_page_3(doc: Document, page) -> None:
    """Render page 4 items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def _add_page_4(doc: Document, page) -> None:
    """Render page 5 items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def _add_page_5(doc: Document, page) -> None:
    """Render page 6 items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def build_template() -> Document:
    """Return a clean Document with all frames defined.

    Emitted by tools/idml_to_dsl.py from the source IDML; hand-edit as needed.
    """
    doc = Document(
        brand=Brand.gruene_noe(),
        title='26-03-flyer-a6-hochformat-quadrat-in-bild',
        template_id='26-03-flyer-a6-hochformat-quadrat-in-bild',
        author="Die Grünen Niederösterreich",
        facing_pages=False,
        layers=[
            DocumentLayer(name='Ebene 1'),
        ],
        extra_doc_attrs={
            'DPIn':  'ISO Coated v2 300% (basICColor)',
            'DPIn2': 'ISO Coated v2 300% (basICColor)',
        },
        extra_pdf_attrs={
            'cropMarks': '0',
            'bleedMarks': '0',
        },
    )

    # add_styles(doc) - paragraph styles (Phase G, task 5)
    _add_styles(doc)

    doc.add_master(
        name="Normal",
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
    )

    page0 = doc.add_page(
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page1 = doc.add_page(
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page2 = doc.add_page(
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page3 = doc.add_page(
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page4 = doc.add_page(
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page5 = doc.add_page(
        size=(105, 148.00000000000003),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )

    _add_page_0(doc, page0)
    _add_page_1(doc, page1)
    _add_page_2(doc, page2)
    _add_page_3(doc, page3)
    _add_page_4(doc, page4)
    _add_page_5(doc, page5)

    return doc


def _add_styles(doc: Document) -> None:  # overrides task-3 stub
    """Auto-generated paragraph styles from the source IDML."""
    doc.add_para_style(ParaStyle(
        name='idml/no-paragraph-style',
        font='Minion Pro Regular',
        fontsize=12,
        align=0,
        fcolor='Black',
        linesp=17.4,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/fliesstext-auf-gruenem-hintergrund',
        parent='idml/no-paragraph-style',
        font='Gotham Narrow Book',
        fontsize=11,
        align=3,
        fcolor='White',
        linesp=14.3,
        tab_stops=((15, 0),),
    ))
    doc.add_para_style(ParaStyle(
        name='idml/headline-in-gruenem-kasten',
        parent='idml/no-paragraph-style',
        font='Gotham Narrow Bold',
        fontsize=12,
        align=1,
        fcolor='White',
        linesp=12,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle',
        parent='idml/no-paragraph-style',
        font='Minion Pro Regular',
        fontsize=12,
        align=0,
        fcolor='Black',
        linesp=17.4,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/aufzaehlungen-auf-gruenem-hintergrund',
        parent='idml/fliesstext-auf-gruenem-hintergrund',
        font='Gotham Narrow Book',
        fontsize=11,
        align=0,
        fcolor='White',
        linesp=14.3,
        tab_stops=((5, 0), (13, 0)),
        left_indent_pt=13,
        first_indent_pt=-13,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/fliesstext-auf-weissem-hintergrund',
        parent='idml/fliesstext-auf-gruenem-hintergrund',
        font='Gotham Narrow Book',
        fontsize=11,
        align=3,
        fcolor='Dunkelgrün',
        linesp=14.3,
        space_after_pt=5.6693,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/zwischenueberschrift-auf-weissem-hintergrund',
        parent='idml/fliesstext-auf-weissem-hintergrund',
        font='Gotham Narrow Bold',
        fontsize=11,
        align=3,
        fcolor='Dunkelgrün',
        linesp=14.3,
    ))
    return None


def _add_page_0(doc: Document, page0) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 1 (Spread Spreads/Spread_ud0.xml)."""
    page0.add(ImageFrame(
        x_mm=-2.48,
        y_mm=-3,
        w_mm=111,
        h_mm=154,
        anname='u132c',
        layer=0,
        image='../../shared/assets/26-03-flyer-a6-hochformat-quadrat-in-bild/crops/green-pine-trees-covered-with-fog-u132c.png',
    ))
    page0.add(Polygon(
        x_mm=21,
        y_mm=42.5,
        w_mm=63,
        h_mm=63,
        anname='u1334',
        layer=0,
        fill='Dunkelgrün',
    ))
    page0.add(ImageFrame(
        x_mm=46.83,
        y_mm=87.8146,
        w_mm=11.34,
        h_mm=9.9634,
        anname='u1336',
        layer=0,
        # frame_visibility (L-014 worked example): the DIE GRUENEN logo is
        # a small RGBA white-on-transparent PNG. Scribus 1.6.x renders the
        # inline_image_data form fully transparent for SCALETYPE=1 small
        # frames (image_frame_visibility_audit: u1336 visibility_ratio 0.0).
        # Reference the asset directly with scale_type=0 (fit-to-frame) so it
        # renders inside the green box. Re-applies the prior tune's documented
        # fix dropped by the combined-fidelity re-import. See TOLERANCE_LOG.md.
        image='../../shared/assets/26-03-flyer-a6-hochformat-quadrat-in-bild/gruene-logo-bund-weiss-cmyk.png',
        scale_type=0,
    ))
    # h_mm widened 31.2959mm→67.0278mm: Scribus clips lines when frame_h < 4 explicit lines × line height (leading=32.12pt; IDML overflows silently)
    page0.add(TextFrame(
        x_mm=23.2731,
        y_mm=50.222,
        w_mm=58.4538,
        h_mm=67.0278,
        anname='u133f',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Das ist eine', font='Gotham Narrow Ultra', fontsize=31, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}, separator='para'), Run(text='dreizeilige', font='Vollkorn Black Italic', fontsize=31, fcolor='Gelb'), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}, separator='para'), Run(text='Headline', font='Gotham Narrow Ultra', fontsize=31, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))
    page0.add(Polygon(
        x_mm=70.0307,
        y_mm=26.1542,
        w_mm=27.8451,
        h_mm=27.8451,
        anname='u1357',
        layer=0,
        rotation_deg=-18,
        fill='Magenta',
        shape='ellipse',
    ))
    # h_mm widened 4.1291mm→10.4069mm: Scribus clips lines when frame_h < effective line height (leading=13.17pt; IDML overflows silently)
    page0.add(TextFrame(
        x_mm=73.5,
        y_mm=35.2318,
        w_mm=27.8451,
        h_mm=10.4069,
        anname='u1358',
        layer=0,
        rotation_deg=-9,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Störer', font='Gotham Narrow Ultra', fontsize=15, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'})],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))
    page0.add(Polygon(
        x_mm=-20,
        y_mm=81.35,
        w_mm=6.3,
        h_mm=6.3,
        anname='u136f',
        layer=0,
        fill='Magenta',
    ))


def _add_page_1(doc: Document, page1) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 2 (Spread Spreads/Spread_u11d.xml)."""
    page1.add(Polygon(
        x_mm=-3,
        y_mm=-3,
        w_mm=216,
        h_mm=154,
        anname='u11e1',
        layer=0,
        fill='Dunkelgrün',
    ))
    page1.add(PolyLine(
        x_mm=14.8006,
        y_mm=89.8339,
        w_mm=19.1982,
        h_mm=0.9961,
        sla_path='M53.27 0.659 C46.44 0.3189 39.6 0.02792 32.77 0 C25.93 -0.02797 19.1 0.1069 12.26 0.1673 C10.36 0.184 8.457 0.2086 6.555 0.2411 C5.584 0.2577 4.612 0.2715 3.641 0.2866 C2.671 0.3018 1.692 0.2773 0.729 0.3876 C0.3111 0.4355 -0.02705 0.7777 0 1.213 C0.02884 1.676 0.404 1.917 0.8258 1.942 C1.695 1.994 2.568 1.934 3.437 1.907 C4.287 1.881 5.136 1.855 5.986 1.837 C7.705 1.801 9.425 1.771 11.15 1.747 C14.55 1.701 17.95 1.72 21.35 1.78 C28.19 1.902 35.04 2.151 41.88 2.366 C45.72 2.486 49.57 2.639 53.41 2.824 C53.97 2.851 54.48 2.212 54.42 1.674 C54.35 1.035 53.88 0.6893 53.27 0.659 C53.27 0.659 53.27 0.659 53.27 0.659 Z',
        line_color='None',
        line_width_pt=0,
        anname='u11e3',
        layer=0,
        fill='Gelb',
    ))
    page1.add(PolyLine(
        x_mm=80.869,
        y_mm=41.8,
        w_mm=11.749,
        h_mm=3.8145,
        sla_path='M10.73 0.01935 C10.76 0.0419 10.79 0.02812 10.81 0.065 C10.89 0.06586 10.98 0.1012 11.06 0.08221 C11.07 0.08597 11.09 0.09143 11.1 0.09335 C11.77 0.187 12.44 0.3362 13.11 0.4828 C14.03 0.6846 14.94 0.9255 15.86 1.173 C16.17 1.256 16.48 1.346 16.79 1.433 C16.73 1.484 16.67 1.477 16.62 1.475 C16.09 1.465 15.56 1.463 15.04 1.486 C13.98 1.534 12.92 1.659 11.86 1.808 C10.93 1.939 10.01 2.101 9.082 2.318 C7.965 2.58 6.85 2.886 5.74 3.269 C4.53 3.686 3.33 4.186 2.16 4.942 C1.635 5.28 1.117 5.648 0.6262 6.16 C0.3609 6.437 0.1521 6.825 0 7.34 C-0.08241 7.62 -0.07121 7.923 0.03886 8.156 C0.08782 8.26 0.1376 8.363 0.1971 8.444 C0.7716 9.225 1.415 9.665 2.087 9.96 C2.1 9.97 2.112 9.983 2.125 9.989 C2.677 10.23 3.235 10.4 3.799 10.49 C4.578 10.62 5.359 10.68 6.14 10.7 C7.136 10.73 8.132 10.73 9.128 10.75 C9.152 10.79 9.181 10.77 9.207 10.77 C9.446 10.78 9.684 10.78 9.922 10.79 C9.96 10.79 9.999 10.77 10.03 10.81 C12.26 10.81 14.48 10.81 16.71 10.81 C16.73 10.78 16.76 10.79 16.78 10.79 C17.02 10.78 17.26 10.78 17.5 10.77 C17.52 10.77 17.56 10.79 17.58 10.75 C18.61 10.71 19.64 10.67 20.67 10.6 C21.68 10.53 22.7 10.48 23.71 10.39 C24.86 10.3 26.01 10.19 27.15 10.05 C27.33 10.03 27.51 9.992 27.69 9.96 C27.69 9.96 27.68 9.954 27.68 9.954 C27.68 9.953 27.68 9.953 27.68 9.953 C27.68 9.955 27.69 9.958 27.69 9.96 C27.7 9.963 27.71 9.97 27.73 9.967 C28.13 9.893 28.54 9.836 28.94 9.74 C29.72 9.553 30.5 9.373 31.27 9.068 C31.75 8.879 32.23 8.666 32.69 8.36 C32.81 8.28 32.94 8.207 33.04 8.048 C33.16 7.935 33.24 7.738 33.3 7.535 C33.42 7.196 33.43 6.812 33.22 6.558 C33.19 6.521 33.16 6.477 33.13 6.44 C32.83 6.082 32.51 5.864 32.18 5.652 C31.39 5.139 30.58 4.777 29.77 4.45 C29.43 4.312 29.08 4.173 28.73 4.064 C28.71 4.02 28.67 4.028 28.65 3.999 C28.72 4.005 28.79 4.019 28.87 4.03 C28.89 4.033 28.91 4.033 28.91 3.98 C28.91 3.932 28.89 3.916 28.87 3.922 C28.83 3.91 28.8 3.898 28.76 3.886 C27.97 3.643 27.19 3.323 26.4 3.083 C25.85 2.914 25.29 2.708 24.73 2.578 C24.08 2.427 23.43 2.222 22.78 2.095 C22.39 2.02 22 1.9 21.61 1.845 C21.14 1.779 20.66 1.719 20.19 1.636 C19.44 1.506 18.7 1.251 17.95 1.067 C17.28 0.9015 16.61 0.738 15.93 0.5967 C15.31 0.4676 14.7 0.3591 14.08 0.2749 C13.58 0.2068 13.08 0.1353 12.57 0.1016 C12.55 0.09492 12.54 0.08337 12.52 0.08221 C12.5 0.08133 12.49 0.08047 12.48 0.07957 C12.41 0.06857 12.34 0.06674 12.27 0.06645 C11.91 0.04402 11.56 0.02194 11.21 0 C11.21 0 11.2 0 11.2 0 C11.04 0 10.88 0 10.72 0 C10.72 0.00885 10.73 0.01457 10.73 0.01935 Z M30.99 5.767 C31.48 6 31.98 6.237 32.45 6.6 C32.55 6.673 32.64 6.768 32.72 6.906 C32.8 7.056 32.79 7.175 32.7 7.278 C32.5 7.487 32.28 7.599 32.07 7.72 C31.39 8.101 30.7 8.322 30 8.508 C28.62 8.875 27.24 9.079 25.86 9.24 C24.04 9.451 22.22 9.549 20.4 9.667 C17.16 9.877 13.93 9.899 10.7 9.874 C9.059 9.861 7.423 9.837 5.786 9.809 C4.982 9.796 4.178 9.734 3.377 9.587 C2.698 9.462 2.026 9.252 1.374 8.844 C1.142 8.699 0.9249 8.49 0.732 8.188 C0.5211 7.859 0.52 7.61 0.7257 7.267 C0.845 7.068 0.9904 6.958 1.12 6.796 C1.146 6.777 1.172 6.762 1.196 6.739 C1.445 6.505 1.697 6.287 1.957 6.108 C2.899 5.458 3.86 4.93 4.837 4.532 C5.859 4.116 6.888 3.787 7.921 3.504 C8.516 3.341 9.113 3.192 9.71 3.067 C10.34 2.934 10.98 2.82 11.61 2.707 C12.29 2.586 12.97 2.504 13.65 2.426 C14.38 2.342 15.12 2.275 15.85 2.248 C17.03 2.204 18.2 2.214 19.37 2.244 C19.45 2.246 19.52 2.249 19.59 2.268 C19.97 2.368 20.35 2.479 20.74 2.576 C21.44 2.754 22.14 2.984 22.84 3.172 C23.05 3.23 23.27 3.311 23.48 3.335 C23.66 3.388 23.83 3.444 24.01 3.493 C24.4 3.602 24.79 3.707 25.18 3.813 C25.69 3.949 26.19 4.088 26.69 4.219 C27.12 4.331 27.55 4.467 27.98 4.605 C28.99 4.931 29.99 5.298 30.99 5.767 Z M27.64 3.674 C27.63 3.671 27.63 3.668 27.62 3.665 C27.63 3.668 27.63 3.671 27.64 3.673 C27.64 3.673 27.64 3.673 27.64 3.674 Z M26.76 3.393 C26.76 3.393 26.76 3.393 26.76 3.393 C26.74 3.401 26.72 3.391 26.71 3.402 C26.72 3.407 26.74 3.412 26.76 3.417 C26.74 3.424 26.72 3.405 26.71 3.402 C26.34 3.3 25.97 3.194 25.6 3.096 C25.42 3.05 25.25 2.985 25.08 2.969 C25.06 2.968 25.05 2.948 25.03 2.937 C25.04 2.924 25.04 2.916 25.05 2.911 C25.05 2.911 25.05 2.911 25.05 2.911 C25.08 2.89 25.12 2.924 25.15 2.9 C25.23 2.971 25.33 2.927 25.42 2.954 C25.82 3.078 26.22 3.189 26.63 3.304 C26.68 3.318 26.72 3.389 26.78 3.362 C26.77 3.38 26.77 3.388 26.76 3.393 Z',
        line_color='None',
        line_width_pt=0,
        anname='u11e4',
        layer=0,
        fill='Gelb',
    ))
    page1.add(TextFrame(
        x_mm=95,
        y_mm=82.6,
        w_mm=10,
        h_mm=53.4,
        anname='u11fd',
        layer=0,
        rotation_deg=-90,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Impressum: xxxxxx', font='Gotham Narrow Book', fontsize=6, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'})],
        trail_attrs={'LINESPMode': '1'},
        vertical_text_align=1,
        fill_opacity=0.7,
    ))
    # h_mm widened 17.9915mm→33.1611mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    page1.add(TextFrame(
        x_mm=15,
        y_mm=15,
        w_mm=75,
        h_mm=33.1611,
        anname='u1214',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    # h_mm widened 93.9094mm→97.3667mm: Scribus clips lines when frame_h < 17 explicit lines × line height (leading=14.30pt; IDML overflows silently)
    page1.add(TextFrame(
        x_mm=15,
        y_mm=42,
        w_mm=75,
        h_mm=97.3667,
        anname='u1242',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Tinvend igenis ute voloria qui cus et ut optate vendam ilis voloriaspita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Lia vellam, conemporro moditatque nimil maxim voluptur, quidessi re none tem issi iuntem ressiti orerovi tectotmusa qui tota nis quam quis et ilis voloriaspita dis quaturem. Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
    ))
    page1.add(Polygon(
        x_mm=-26,
        y_mm=35,
        w_mm=6.3,
        h_mm=6.3,
        anname='u125a',
        layer=0,
        fill='Magenta',
    ))


def _add_page_2(doc: Document, page2) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 3 (Spread Spreads/Spread_u11d.xml)."""
    page2.add(Polygon(
        x_mm=-108,
        y_mm=-3,
        w_mm=216,
        h_mm=154,
        anname='u11e1_p1',
        layer=0,
        fill='Dunkelgrün',
    ))
    page2.add(PolyLine(
        x_mm=48.7981,
        y_mm=45.3856,
        w_mm=25.0055,
        h_mm=1.1564,
        sla_path='M70.35 1.964 C68.11 1.678 65.86 1.509 63.61 1.328 C61.38 1.148 59.14 0.9852 56.9 0.8385 C52.35 0.5406 47.8 0.3467 43.25 0.2093 C38.76 0.07378 34.27 0.003983 29.77 0 C25.28 -0.004017 20.78 0.06575 16.29 0.1586 C11.78 0.2518 7.274 0.4107 2.768 0.565 C2.496 0.5742 2.225 0.5846 1.953 0.5935 C1.667 0.6029 1.383 0.6656 1.101 0.7124 C0.7816 0.7651 0.5038 0.8699 0.2861 1.122 C0.09529 1.343 -0.03504 1.693 0 1.988 C0.08303 2.687 0.606 3.065 1.275 3.088 C1.547 3.098 1.822 3.121 2.093 3.102 C2.393 3.081 2.694 3.048 2.994 3.021 C3.549 2.972 4.105 2.924 4.661 2.877 C5.787 2.782 6.914 2.682 8.042 2.613 C10.27 2.477 12.5 2.357 14.72 2.254 C19.23 2.044 23.73 1.931 28.24 1.888 C32.73 1.846 37.22 1.87 41.71 1.96 C46.2 2.049 50.69 2.227 55.17 2.421 C59.68 2.615 64.03 2.867 68.51 3.193 C69.09 3.236 69.68 3.252 70.27 3.278 C70.6 3.292 70.87 2.952 70.88 2.656 C70.9 2.347 70.69 2.006 70.35 1.964 C70.35 1.964 70.35 1.964 70.35 1.964 Z',
        line_color='None',
        line_width_pt=0,
        anname='u11e2',
        layer=0,
        fill='Gelb',
    ))
    page2.add(PolyLine(
        x_mm=48.6007,
        y_mm=23.0943,
        w_mm=25.399,
        h_mm=1.8007,
        sla_path='M71.71 1.309 C71.48 1.028 70.78 0.6713 70.19 0.6043 C69.76 0.5556 69.33 0.4789 68.9 0.454 C68.65 0.4395 68.39 0.4452 68.13 0.44 C67.57 0.4284 67.01 0.4167 66.45 0.405 C65.42 0.3839 64.4 0.3627 63.38 0.3416 C61.28 0.2981 59.18 0.295 57.08 0.281 C52.85 0.253 48.62 0.2251 44.4 0.1971 C35.99 0.1414 27.58 0.1281 19.18 0.09774 C14.44 0.08063 9.698 0.06433 4.959 0 C3.721 -0.01687 2.481 0.1757 1.543 0.6207 C0.7097 1.016 0.02788 1.688 0 2.291 C-0.02984 2.939 0.2922 3.628 1.169 4.106 C1.468 4.244 1.767 4.381 2.067 4.519 C2.749 4.758 3.498 4.893 4.313 4.925 C5.453 5.028 6.64 5.047 7.791 5.104 C8.614 5.145 9.615 5.012 10.39 4.767 C16.72 4.619 23.05 4.517 29.38 4.394 C37.74 4.232 46.1 4.056 54.45 3.869 C56.77 3.817 59.08 3.766 61.4 3.714 C63.89 3.658 66.39 3.539 68.88 3.447 C69.01 3.443 69.14 3.44 69.27 3.434 C69.32 3.425 69.37 3.415 69.42 3.406 C69.56 3.387 69.71 3.368 69.85 3.349 C70.96 3.203 71.97 2.692 72 2.052 C72.01 1.795 71.91 1.543 71.71 1.309 Z',
        line_color='None',
        line_width_pt=0,
        anname='u11e5',
        layer=0,
        fill='Gelb',
    ))
    page2.add(TextFrame(
        x_mm=15,
        y_mm=42,
        w_mm=75,
        h_mm=66.1513,
        anname='u11e6',
        layer=0,
        style='idml/aufzaehlungen-auf-gruenem-hintergrund',
        runs=[Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Scim rem ', font='Gotham Narrow Black'), Run(text='utas si vellaccum eatus\u2028nullquae cum et arum vendellab iditatequi aut qui beat audit re.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Tissi iuntem ressiti ', font='Gotham Narrow Black'), Run(text='orerovi tectotmusaqui tota nis quam.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Uaerum ium ', font='Gotham Narrow Black'), Run(text='verior alicide liquuntio. ', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Ur, omniet ', font='Gotham Narrow Book'), Run(text='vello modi ', font='Gotham Narrow Black'), Run(text='aceprate pem ssi iuntem ilis', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Lia vellam, conemporro ', font='Gotham Narrow Book'), Run(text='moditatque', font='Gotham Narrow Black'), Run(text=' nimil maxim voluptur.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', separator='tab')],
    ))
    # h_mm widened 17.9915mm→24.6944mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    # P5/playbook y_mm_shift.py: y_mm 15.0 → 15.5 (calibration probe (+0.5mm))
    page2.add(TextFrame(
        x_mm=15,
        y_mm=15.5,
        w_mm=75,
        h_mm=24.6944,
        anname='u122b',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin auch ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    page2.add(PolyLine(
        x_mm=39.8935,
        y_mm=105.0041,
        w_mm=25.2129,
        h_mm=30.6143,
        sla_path='M38.25 46.19 C41.59 46.19 44.29 43.44 44.29 40.06 C44.29 36.68 41.59 33.93 38.25 33.93 C34.91 33.93 32.21 36.68 32.21 40.06 C32.21 43.44 34.91 46.19 38.25 46.19 Z M35.62 30.75 L31.13 24.52 L42.38 0 L47.73 0.867 L43.34 32.04 M47.85 41.92 L55.48 41.01 L71.47 62.73 L68.12 67 L42.98 48.05 M31.87 47.19 L28.81 54.24 L1.992 57.1 L0 52.06 L29.03 39.89 M35.25 50.19 L33.01 77.34 M41.29 50.92 L43.82 81.21 L49.88 81.21 L49.88 86.78 M39.19 81.21 L26.65 81.21 L26.65 86.78',
        line_color='Gelb',
        line_width_pt=2.1637499928474426,
        anname='u1259',
        layer=0,
        line_cap=32,
        line_join=128,
    ))
    page2.add(Polygon(
        x_mm=118.7,
        y_mm=35,
        w_mm=6.3,
        h_mm=6.3,
        anname='u125b',
        layer=0,
        fill='Magenta',
    ))


def _add_page_3(doc: Document, page3) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 4 (Spread Spreads/Spread_u68d.xml)."""
    page3.add(Polygon(
        x_mm=15,
        y_mm=98.1368,
        w_mm=75,
        h_mm=37.8632,
        anname='u1268',
        layer=0,
        fill='Dunkelgrün',
    ))
    page3.add(PolyLine(
        x_mm=14.506,
        y_mm=47.3934,
        w_mm=51.5317,
        h_mm=2.1749,
        sla_path='M70.19 4.383 C72.31 4.171 74.24 3.63 76.29 3.164 C79.16 2.512 82.04 2.042 84.99 2.353 C94.37 3.343 98.88 5.684 109 4.719 C111.5 4.475 113.9 4.356 116.5 4.435 C116.5 4.435 129.1 4.825 129.1 4.825 C129.1 4.825 131.5 4.855 131.5 4.855 C131.5 4.855 137.7 4.95 137.7 4.95 C138.9 4.968 142.3 4.622 143.3 4.218 C143.6 4.092 143.9 3.759 144.3 3.718 C145 3.62 145.6 3.357 146.1 2.701 C145.4 2.525 143.1 3.142 142.1 3.085 C142.1 3.085 134.9 2.66 134.9 2.66 C134.9 2.66 126.6 2.052 126.6 2.052 C120.5 1.609 114.2 0.678 108.2 1.983 C107.5 2.136 106.7 2.307 106 2.316 C99.47 2.398 99.6 1.837 93.7 0.8447 C93.7 0.8447 90.66 0.3331 90.66 0.3331 C88.9 0.03632 87.18 -0.02579 85.38 0 C80.22 0.07407 77.99 0.6821 73.1 1.781 C70.4 2.388 67.75 2.631 64.98 2.83 C60.62 3.143 56.45 2.731 52.24 1.622 C50.76 1.232 49.35 1.125 47.85 0.9266 C47.26 0.8476 46.64 0.5876 46.02 0.6315 C45.16 0.6926 44.32 0.5718 43.44 0.5838 C41.01 0.6171 38.67 1.072 36.3 1.581 C33.88 2.098 31.56 2.431 29.1 2.591 C24.32 2.901 22.2 1.694 17.71 1.572 C16.73 1.545 15.73 1.505 14.76 1.607 C11.71 1.926 8.859 2.893 6.093 4.127 C5.54 4.374 5.033 4.379 4.465 4.252 C3.666 4.073 0.3352 3.206 0 4.192 C-0.06165 4.373 0.05411 4.854 0.2021 4.981 C1.864 6.4 4.047 6.795 6.168 6.165 C7.179 5.865 8.257 5.671 9.231 5.304 C11.01 4.632 12.66 4.054 14.62 4.015 C16.72 3.973 18.7 4.114 20.83 4.324 C25.94 4.83 31.04 4.663 36.07 3.604 C40 2.777 42.13 1.966 46.31 2.774 C56.15 4.678 59.95 5.406 70.19 4.383 Z',
        line_color='None',
        line_width_pt=0,
        anname='u126c',
        layer=0,
        fill='Gelb',
    ))
    page3.add(PolyLine(
        x_mm=14.506,
        y_mm=47.3934,
        w_mm=51.5317,
        h_mm=2.1749,
        sla_path='M70.19 4.383 C59.95 5.406 56.15 4.678 46.31 2.774 C42.13 1.966 40 2.777 36.07 3.604 C31.04 4.663 25.94 4.83 20.83 4.324 C18.7 4.114 16.72 3.973 14.62 4.015 C12.66 4.054 11.01 4.632 9.231 5.304 C8.257 5.671 7.179 5.865 6.168 6.165 C4.047 6.795 1.864 6.4 0.2021 4.981 C0.05411 4.854 -0.06165 4.373 0 4.192 C0.3352 3.206 3.666 4.073 4.465 4.252 C5.033 4.379 5.54 4.374 6.093 4.127 C8.859 2.893 11.71 1.926 14.76 1.607 C15.73 1.505 16.73 1.545 17.71 1.572 C22.2 1.694 24.32 2.901 29.1 2.591 C31.56 2.431 33.88 2.098 36.3 1.581 C38.67 1.072 41.01 0.6171 43.44 0.5838 C44.32 0.5718 45.16 0.6926 46.02 0.6315 C46.64 0.5876 47.26 0.8476 47.85 0.9266 C49.35 1.125 50.76 1.232 52.24 1.622 C56.45 2.731 60.62 3.143 64.98 2.83 C67.75 2.631 70.4 2.388 73.1 1.781 C77.99 0.6821 80.22 0.07407 85.38 0 C87.18 -0.02579 88.9 0.03632 90.66 0.3331 C90.66 0.3331 93.7 0.8447 93.7 0.8447 C99.6 1.837 99.47 2.398 106 2.316 C106.7 2.307 107.5 2.136 108.2 1.983 C114.2 0.678 120.5 1.609 126.6 2.052 C126.6 2.052 134.9 2.66 134.9 2.66 C134.9 2.66 142.1 3.085 142.1 3.085 C143.1 3.142 145.4 2.525 146.1 2.701 C145.6 3.357 145 3.62 144.3 3.718 C143.9 3.759 143.6 4.092 143.3 4.218 C142.3 4.622 138.9 4.968 137.7 4.95 C137.7 4.95 131.5 4.855 131.5 4.855 C131.5 4.855 129.1 4.825 129.1 4.825 C129.1 4.825 116.5 4.435 116.5 4.435 C113.9 4.356 111.5 4.475 109 4.719 C98.88 5.684 94.37 3.343 84.99 2.353 C82.04 2.042 79.16 2.512 76.29 3.164 C74.24 3.63 72.31 4.171 70.19 4.383 Z',
        line_color='None',
        line_width_pt=0,
        anname='u126e',
        layer=0,
        fill='Gelb',
    ))
    page3.add(TextFrame(
        x_mm=95,
        y_mm=82.6,
        w_mm=10,
        h_mm=53.4,
        anname='u126f',
        layer=0,
        rotation_deg=-90,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Impressum: xxxxxx', font='Gotham Narrow Book', fontsize=6, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'})],
        trail_attrs={'LINESPMode': '1'},
        vertical_text_align=1,
        fill_opacity=0.7,
    ))
    page3.add(PolyLine(
        x_mm=50.0921,
        y_mm=82.6,
        w_mm=21.211,
        h_mm=5.1895,
        sla_path='M19.38 0.02632 C19.42 0.057 19.48 0.03826 19.52 0.08843 C19.67 0.0896 19.82 0.1376 19.97 0.1119 C19.99 0.117 20.01 0.1244 20.04 0.127 C21.25 0.2545 22.46 0.4574 23.66 0.6569 C25.32 0.9314 26.98 1.259 28.63 1.595 C29.19 1.709 29.75 1.831 30.31 1.95 C30.21 2.019 30.1 2.009 30 2.007 C29.05 1.993 28.1 1.99 27.15 2.022 C25.23 2.087 23.32 2.257 21.41 2.46 C19.74 2.638 18.07 2.859 16.4 3.154 C14.38 3.51 12.37 3.927 10.36 4.447 C8.179 5.015 6.012 5.695 3.899 6.723 C2.952 7.184 2.016 7.684 1.131 8.381 C0.6516 8.757 0.2745 9.285 0 9.986 C-0.1488 10.37 -0.1286 10.78 0.07015 11.1 C0.1585 11.24 0.2485 11.38 0.3558 11.49 C1.393 12.55 2.554 13.15 3.768 13.55 C3.79 13.56 3.812 13.58 3.835 13.59 C4.832 13.92 5.841 14.14 6.858 14.27 C8.265 14.44 9.675 14.53 11.09 14.56 C12.88 14.6 14.68 14.6 16.48 14.62 C16.52 14.68 16.57 14.65 16.62 14.66 C17.05 14.66 17.48 14.67 17.91 14.68 C17.98 14.68 18.05 14.65 18.12 14.71 C22.13 14.71 26.15 14.71 30.17 14.71 C30.2 14.66 30.25 14.68 30.29 14.68 C30.72 14.67 31.15 14.66 31.59 14.66 C31.64 14.65 31.69 14.68 31.74 14.62 C33.6 14.57 35.46 14.52 37.31 14.42 C39.14 14.32 40.98 14.25 42.81 14.14 C44.88 14.01 46.95 13.87 49.02 13.68 C49.34 13.65 49.66 13.59 49.98 13.55 C49.98 13.55 49.98 13.54 49.98 13.54 C49.98 13.54 49.98 13.54 49.98 13.54 C49.98 13.54 49.98 13.55 49.98 13.55 C50.01 13.55 50.03 13.56 50.06 13.56 C50.79 13.46 51.52 13.38 52.24 13.25 C53.65 13 55.06 12.75 56.46 12.34 C57.33 12.08 58.18 11.79 59.02 11.37 C59.24 11.26 59.47 11.16 59.65 10.95 C59.86 10.79 60.01 10.53 60.13 10.25 C60.33 9.79 60.35 9.268 59.97 8.921 C59.92 8.871 59.86 8.812 59.81 8.762 C59.27 8.274 58.69 7.977 58.1 7.689 C56.67 6.991 55.21 6.499 53.74 6.054 C53.12 5.866 52.5 5.677 51.87 5.53 C51.83 5.468 51.77 5.48 51.72 5.441 C51.85 5.449 51.98 5.468 52.11 5.483 C52.15 5.487 52.19 5.487 52.19 5.415 C52.19 5.349 52.16 5.328 52.12 5.336 C52.05 5.32 51.99 5.303 51.92 5.287 C50.5 4.956 49.09 4.521 47.67 4.195 C46.66 3.964 45.66 3.685 44.66 3.508 C43.48 3.302 42.31 3.023 41.13 2.851 C40.42 2.748 39.72 2.585 39.02 2.51 C38.16 2.42 37.3 2.338 36.45 2.226 C35.1 2.048 33.76 1.702 32.41 1.452 C31.2 1.226 29.98 1.004 28.76 0.8118 C27.65 0.6361 26.53 0.4886 25.42 0.374 C24.51 0.2813 23.61 0.184 22.7 0.1382 C22.67 0.1291 22.63 0.1134 22.6 0.1119 C22.57 0.1106 22.55 0.1095 22.52 0.1083 C22.4 0.09329 22.27 0.0908 22.14 0.09041 C21.51 0.05989 20.87 0.02985 20.23 0 C20.23 0 20.23 0 20.23 0 C19.93 0 19.64 0 19.35 0 C19.36 0.01204 19.37 0.01982 19.38 0.02632 Z M55.95 7.846 C56.84 8.163 57.73 8.486 58.59 8.98 C58.76 9.079 58.93 9.207 59.06 9.396 C59.21 9.599 59.2 9.762 59.03 9.902 C58.67 10.19 58.28 10.34 57.89 10.5 C56.67 11.02 55.42 11.32 54.16 11.57 C51.68 12.07 49.18 12.35 46.69 12.57 C43.4 12.86 40.11 12.99 36.82 13.15 C30.99 13.44 25.15 13.47 19.31 13.43 C16.35 13.42 13.4 13.38 10.45 13.35 C8.994 13.33 7.543 13.24 6.097 13.04 C4.871 12.87 3.658 12.59 2.48 12.03 C2.061 11.83 1.67 11.55 1.322 11.14 C0.9409 10.69 0.9388 10.35 1.31 9.887 C1.526 9.616 1.788 9.467 2.023 9.246 C2.068 9.22 2.116 9.199 2.16 9.168 C2.608 8.849 3.063 8.553 3.532 8.31 C5.235 7.426 6.968 6.707 8.732 6.166 C10.58 5.6 12.44 5.153 14.3 4.767 C15.37 4.545 16.45 4.343 17.53 4.173 C18.67 3.992 19.82 3.836 20.96 3.682 C22.19 3.518 23.41 3.406 24.64 3.3 C25.97 3.186 27.29 3.095 28.62 3.058 C30.74 2.998 32.86 3.012 34.97 3.053 C35.11 3.056 35.24 3.06 35.37 3.086 C36.06 3.222 36.75 3.373 37.43 3.504 C38.7 3.746 39.96 4.059 41.23 4.316 C41.62 4.394 42 4.505 42.39 4.537 C42.71 4.609 43.03 4.686 43.35 4.753 C44.05 4.9 44.76 5.044 45.47 5.188 C46.37 5.373 47.28 5.561 48.19 5.74 C48.96 5.892 49.74 6.077 50.51 6.265 C52.33 6.708 54.15 7.208 55.95 7.846 Z M49.9 4.998 C49.89 4.994 49.88 4.99 49.86 4.986 C49.88 4.99 49.89 4.994 49.9 4.997 C49.9 4.997 49.9 4.998 49.9 4.998 Z M48.31 4.616 C48.31 4.616 48.31 4.616 48.31 4.617 C48.28 4.628 48.25 4.613 48.22 4.628 C48.25 4.635 48.28 4.642 48.31 4.649 C48.28 4.658 48.25 4.632 48.22 4.628 C47.55 4.489 46.88 4.346 46.21 4.212 C45.9 4.15 45.59 4.062 45.27 4.039 C45.24 4.037 45.22 4.011 45.19 3.996 C45.2 3.977 45.21 3.967 45.23 3.96 C45.23 3.96 45.23 3.96 45.23 3.96 C45.28 3.932 45.35 3.978 45.4 3.945 C45.56 4.042 45.72 3.982 45.88 4.019 C46.61 4.188 47.34 4.339 48.07 4.494 C48.17 4.514 48.25 4.611 48.34 4.575 C48.33 4.599 48.32 4.61 48.31 4.616 Z',
        line_color='None',
        line_width_pt=0,
        anname='u1286',
        layer=0,
        fill='Gelb',
    ))
    # h_mm widened 17.9915mm→24.6944mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    # P5/playbook y_mm_shift.py: y_mm 15.0 → 15.5927 (uniform +-1.68pt × sign=-1 → +0.5927mm)
    page3.add(TextFrame(
        x_mm=15,
        y_mm=15.5927,
        w_mm=75,
        h_mm=24.6944,
        anname='u1287',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    # h_mm widened 47.4622mm→57.8556mm: Scribus clips lines when frame_h < 10 explicit lines × line height (leading=14.30pt; IDML overflows silently)
    page3.add(TextFrame(
        x_mm=15,
        y_mm=39.2915,
        w_mm=75,
        h_mm=57.8556,
        anname='u129e',
        layer=0,
        style='idml/fliesstext-auf-weissem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Tinvend igenis ', font='Gotham Narrow Bold', paragraph_style='idml/zwischenueberschrift-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', paragraph_style='idml/zwischenueberschrift-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Ute voloria qui cus et ut optate vendam ilmolo ipsum fuga. volorro qui optate nis eaquamus.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Licatissi iuntem ressiti orerovi tectouuntur eriatur. Oditibust, quis et qui iminum fugiae no nonsed quae non et quaturem. ctouuntur eriatur, sit, quattatib. Nam quatur.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund')],
    ))
    # h_mm widened 18.2386mm→29.6333mm: Scribus clips lines when frame_h < 5 explicit lines × line height (leading=14.30pt; IDML overflows silently)
    # P5/playbook y_mm_shift.py: y_mm 111.4614 → 111.9614 (calibration probe (+0.5mm))
    page3.add(TextFrame(
        x_mm=19.97,
        y_mm=111.9614,
        w_mm=65,
        h_mm=29.6333,
        anname='u12e4',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Nequia volupti omnienthicipsa dem eossece atiati dollit odit ipientus et ut labora quis ducipiciis ex et hille ntiandi non re ped exceptatur? Sed quia.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'})],
    ))
    # h_mm widened 3.3866mm→8.6078mm: Scribus clips lines when frame_h < effective line height (leading=12.00pt; IDML overflows silently)
    # P5/playbook y_mm_shift.py: y_mm 104.4368 → 103.5901 (uniform ++2.40pt × sign=-1 → -0.8467mm)
    page3.add(TextFrame(
        x_mm=19.75,
        y_mm=103.5901,
        w_mm=65,
        h_mm=8.6078,
        anname='u12fb',
        layer=0,
        style='idml/headline-in-gruenem-kasten',
        runs=[Run(text='Headline in einem grünen Kasten ', font='Gotham Narrow Bold', paragraph_style='idml/headline-in-gruenem-kasten', paragraph_attrs={'ALIGN': '1'})],
    ))
    page3.add(Polygon(
        x_mm=-19.45,
        y_mm=107.75,
        w_mm=3.6,
        h_mm=3.6,
        anname='u1312',
        layer=0,
        fill='Gelb',
    ))
    page3.add(Polygon(
        x_mm=-20.8,
        y_mm=32.9915,
        w_mm=6.3,
        h_mm=6.3,
        anname='u1313',
        layer=0,
        fill='Magenta',
    ))
    page3.add(Polygon(
        x_mm=-20.8,
        y_mm=98.1368,
        w_mm=6.3,
        h_mm=6.3,
        anname='u1314',
        layer=0,
        fill='Magenta',
    ))
    page3.add(Polygon(
        x_mm=-20.8,
        y_mm=129.7,
        w_mm=6.3,
        h_mm=6.3,
        anname='u1315',
        layer=0,
        fill='Magenta',
    ))


def _add_page_4(doc: Document, page4) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 5 (Spread Spreads/Spread_u68d.xml)."""
    page4.add(ImageFrame(
        x_mm=0,
        y_mm=-3,
        w_mm=108,
        h_mm=62.0333,
        anname='u1260',
        layer=0,
        image='../../shared/assets/26-03-flyer-a6-hochformat-quadrat-in-bild/crops/green-pine-trees-covered-with-fog-u1260.png',
    ))
    page4.add(PolyLine(
        x_mm=23.8023,
        y_mm=87.5834,
        w_mm=17.252,
        h_mm=3.7129,
        sla_path='M30.59 9.721 C35.25 9.784 38.8 9.734 42.33 9.314 C43.6 9.163 44.85 8.892 46.09 8.606 C46.63 8.479 47.16 8.222 47.62 7.945 C48.39 7.487 48.44 6.983 47.77 6.445 C47.32 6.086 46.81 5.771 46.28 5.5 C44.89 4.792 43.37 4.314 41.83 3.87 C38.04 2.771 34.12 2.064 30.15 1.567 C25.64 1.003 21.1 0.7645 16.54 0.8757 C13.18 0.9576 9.84 1.185 6.521 1.625 C4.648 1.874 2.776 2.119 0.9031 2.366 C0.8791 2.369 0.8554 2.374 0.8313 2.376 C0.3409 2.429 0.05023 2.325 0 2.079 C-0.04903 1.838 0.1749 1.674 0.6868 1.596 C3.89 1.102 7.09 0.5904 10.34 0.3296 C13.83 0.04918 17.33 -0.08999 20.84 0 C26.8 0.1527 32.66 0.8143 38.42 2.083 C40.7 2.585 42.95 3.173 45.08 4.006 C46.06 4.39 46.99 4.871 47.9 5.362 C48.29 5.574 48.63 5.892 48.9 6.212 C49.51 6.926 49.45 7.714 48.69 8.32 C48.24 8.672 47.7 8.967 47.14 9.195 C45.83 9.736 44.39 9.965 42.94 10.13 C38.3 10.68 33.63 10.72 28.95 10.52 C27.06 10.45 25.16 10.38 23.27 10.26 C20.82 10.11 18.37 9.95 15.93 9.725 C13.63 9.514 11.34 9.256 9.067 8.935 C7.78 8.753 6.516 8.438 5.269 8.113 C4.679 7.959 4.105 7.693 3.611 7.386 C2.507 6.699 2.449 5.752 3.392 4.918 C3.949 4.425 4.656 4.117 5.401 3.861 C7.069 3.289 8.819 2.948 10.59 2.686 C13.04 2.324 15.52 2.2 18.01 2.307 C18.63 2.334 18.91 2.473 18.88 2.745 C18.85 2.993 18.59 3.106 18.01 3.122 C16.52 3.164 15.04 3.161 13.56 3.255 C11.03 3.416 8.548 3.819 6.168 4.558 C5.627 4.726 5.092 4.942 4.619 5.211 C3.524 5.833 3.564 6.446 4.73 6.957 C5.282 7.199 5.88 7.388 6.48 7.541 C8.366 8.021 10.31 8.305 12.27 8.483 C15.99 8.823 19.72 9.149 23.45 9.402 C26.19 9.589 28.94 9.651 30.59 9.721 Z',
        line_color='None',
        line_width_pt=0,
        anname='u1269',
        layer=0,
        fill='Gelb',
    ))
    # h_mm widened 57.5516mm→63.5000mm: Scribus clips lines when frame_h < 11 explicit lines × line height (leading=14.30pt; IDML overflows silently)
    # h_mm widened 63.5mm→71.0mm: Scribus wraps this body frame to 12 lines vs
    # InDesign's 11 (cross-renderer wrap drift); at the IDML h_mm the last line
    # ("...sed maioriat fuga.") falls below the frame and clips. IDML overflows
    # silently. Re-applies the prior tune's documented fix dropped by the
    # combined-fidelity re-import. See TOLERANCE_LOG.md.
    page4.add(TextFrame(
        x_mm=15,
        y_mm=65.3333,
        w_mm=75,
        h_mm=71.0,
        anname='u12b5',
        layer=0,
        style='idml/fliesstext-auf-weissem-hintergrund',
        runs=[Run(text='Ea doluptatas suntota consequi acero dollani storae sitatus maximi, sita sam qui iminum fugiae no nonsed quae non porum fugiat harum que nihil ipsam is id quis eri om:', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Ed ex explabo reicia debis volorrum et aut exerrovit que nonseque rerupt etur, volesteae non porum fugiat harum que.', font='Gotham Narrow Book'), Run(text='', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Nam quatur', font='Gotham Narrow Bold', paragraph_style='idml/zwischenueberschrift-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', paragraph_style='idml/zwischenueberschrift-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Licatissi iuntem ressiti orerovi tectouuntur eriatur, sit, quat eriatur, sit, quateri imi, sed maioriat fuga.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'})],
    ))
    # h_mm widened 17.9915mm→24.6944mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    page4.add(TextFrame(
        x_mm=15,
        y_mm=34.7418,
        w_mm=75,
        h_mm=24.6944,
        anname='u12cc',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin auch ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    page4.add(Polygon(
        x_mm=119.8,
        y_mm=52.7,
        w_mm=6.3,
        h_mm=6.3,
        anname='u1316',
        layer=0,
        fill='Magenta',
    ))
    page4.add(Polygon(
        x_mm=115.3,
        y_mm=59,
        w_mm=6.3,
        h_mm=6.3,
        anname='u1317',
        layer=0,
        fill='Magenta',
    ))


def _add_page_5(doc: Document, page5) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 6 (Spread Spreads/Spread_uddd.xml)."""
    page5.add(ImageFrame(
        x_mm=-3,
        y_mm=-3,
        w_mm=111,
        h_mm=154,
        anname='u137f',
        layer=0,
        image='../../shared/assets/26-03-flyer-a6-hochformat-quadrat-in-bild/crops/leonore-sitzend-kopie-u137f.png',
    ))
    # noinject: u1386 is the IDML-placed radial-gradient vignette overlay (Schwarzer Verlauf radial.psd) — genuine template content, not a demo placeholder, so library substitution does not apply.
    page5.add(ImageFrame(
        x_mm=-3,
        y_mm=66.75,
        w_mm=111,
        h_mm=84.25,
        anname='u1386',
        layer=0,
        fill_opacity=0.9,
        image='../../shared/assets/26-03-flyer-a6-hochformat-quadrat-in-bild/schwarzer-verlauf-radial.png',
        local_scale=(0.126873, 0.126873),
        scale_type=1,
    ))
    page5.add(Polygon(
        x_mm=-15.9,
        y_mm=119.8456,
        w_mm=3.6,
        h_mm=3.6,
        anname='u138e',
        layer=0,
        fill='Gelb',
    ))
    page5.add(Polygon(
        x_mm=-15.9,
        y_mm=94.1631,
        w_mm=3.6,
        h_mm=3.6,
        anname='u138f',
        layer=0,
        fill='Gelb',
    ))
    # h_mm widened 22.0927mm→37.9236mm: Scribus clips lines when frame_h < 3 explicit lines × line height (leading=20.48pt; IDML overflows silently)
    page5.add(TextFrame(
        x_mm=8.88,
        y_mm=97.7631,
        w_mm=87.24,
        h_mm=37.9236,
        anname='u1390',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin ein Zitat. Ich bin ein prägnantes', font='Vollkorn Black Italic', fontsize=23, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}, separator='para'), Run(text='Zitat.', font='Vollkorn Black Italic', fontsize=23, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))
    # h_mm widened 3.1044mm→8.0081mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
    page5.add(TextFrame(
        x_mm=31.6686,
        y_mm=123.4456,
        w_mm=41.6629,
        h_mm=8.0081,
        anname='u13a7',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Leonore Gewessler', font='Gotham Narrow Book', fontsize=11, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'})],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))
    page5.add(PolyLine(
        x_mm=46.2825,
        y_mm=84.1365,
        w_mm=12.4619,
        h_mm=9.9219,
        sla_path='M20.18 28.13 C29.1 27.38 35.33 23.63 35.33 12.9 C35.33 12.9 35.33 0 35.33 0 C35.33 0 19.57 0 19.57 0 C19.57 0 19.57 16.13 19.57 16.13 C19.57 16.13 26.18 16.13 26.18 16.13 C26.02 19.35 23.77 21.53 18.9 22.27 C18.9 22.27 20.18 28.13 20.18 28.13 Z M1.275 28.13 C10.13 27.38 16.35 23.63 16.35 12.9 C16.35 12.9 16.35 0 16.35 0 C16.35 0 0.675 0 0.675 0 C0.675 0 0.675 16.13 0.675 16.13 C0.675 16.13 7.2 16.13 7.2 16.13 C7.125 19.35 4.8 21.53 0 22.27 C0 22.27 1.275 28.13 1.275 28.13 Z',
        line_color='White',
        line_width_pt=0.75,
        anname='u13be',
        layer=0,
    ))

def build_preview() -> Document:
    """Inject demo library images for gallery PNG render (#24 idiom).

    Pre-crops each library image to LIVE frame dimensions via
    library.inject_into_frame. INJECT_MAP starts empty; humans wire it up.
    """
    doc = build_template()
    if not INJECT_MAP:
        return doc
    from sla_lib.builder import library  # noqa: E402
    for page in doc.pages:
        for item in page.items:
            if not isinstance(item, ImageFrame):
                continue
            lib_id = INJECT_MAP.get(item.anname)
            if not lib_id:
                continue
            img = library.load(lib_id, optional=True)
            if img is None:
                continue
            library.inject_into_frame(
                item, img,
                target_w_mm=item.w_mm,
                target_h_mm=item.h_mm,
            )
    return doc


# Alias for audit_alignment.py / spec_check (they expect build_doc).
build_doc = build_template


def build(out_path: str | Path = HERE / "template.sla") -> Path:
    doc = build_preview()
    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    path = build()
    print(f"OK: saved {path}")
