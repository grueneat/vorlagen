"""26-03-flyer-a6-gruenes-cover — DSL build entry point.

Auto-generated from 26-03-Flyer A6 gruenes Cover.idml by tools/idml_to_dsl.py.
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
        title='26-03-flyer-a6-gruenes-cover',
        template_id='26-03-flyer-a6-gruenes-cover',
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

    doc.add_color('C_88_M_44_Y_100_K_0', cmyk=(88, 44, 100, 0))

    # add_styles(doc) - paragraph styles (Phase G, task 5)
    _add_styles(doc)

    doc.add_master(
        name="Normal",
        size=(148.00000000000003, 105),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
    )

    page0 = doc.add_page(
        size=(148.00000000000003, 105),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page1 = doc.add_page(
        size=(148.00000000000003, 105),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page2 = doc.add_page(
        size=(148.00000000000003, 105),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page3 = doc.add_page(
        size=(148.00000000000003, 105),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page4 = doc.add_page(
        size=(148.00000000000003, 105),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page5 = doc.add_page(
        size=(148.00000000000003, 105),
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
        linesp=17.4,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/fliesstext-auf-gruenem-hintergrund',
        parent='idml/no-paragraph-style',
        font='Gotham Narrow Book',
        fontsize=11,
        align=3,
        fcolor='White',
        linesp=15.999999999999998,
        tab_stops=((15, 0),),
    ))
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle',
        parent='idml/no-paragraph-style',
        font='Minion Pro Regular',
        fontsize=12,
        align=0,
        linesp=17.4,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/aufzaehlungen-auf-gruenem-hintergrund',
        parent='idml/fliesstext-auf-gruenem-hintergrund',
        font='Gotham Narrow Book',
        fontsize=11,
        align=0,
        fcolor='White',
        linesp=15.999999999999998,
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
        linesp=15.999999999999998,
    ))
    return None


def _add_page_0(doc: Document, page0) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 1 (Spread Spreads/Spread_ud0.xml)."""
    page0.add(Polygon(
        x_mm=-3,
        y_mm=-3,
        w_mm=154,
        h_mm=111,
        anname='uad5',
        layer=0,
        fill='Dunkelgrün',
    ))
    page0.add(ImageFrame(
        x_mm=122.8,
        y_mm=6.3,
        w_mm=18.9,
        h_mm=16.551,
        anname='uad7',
        layer=0,
        image='../../shared/assets/26-03-flyer-a6-gruenes-cover/gruene-logo-bund-weiss-cmyk.png',
        scale_type=0,
    ))
    page0.add(Polygon(
        x_mm=-11.6,
        y_mm=81.1907,
        w_mm=5.0876,
        h_mm=5.0876,
        anname='ub2b',
        layer=0,
        fill='Dunkelgrün',
    ))
    page0.add(Polygon(
        x_mm=0,
        y_mm=111.1667,
        w_mm=6.3,
        h_mm=6.3,
        anname='ua79',
        layer=0,
        fill='Magenta',
    ))
    page0.add(Polygon(
        x_mm=-12.5,
        y_mm=98.7,
        w_mm=6.3,
        h_mm=6.3,
        anname='ubcd',
        layer=0,
        fill='Magenta',
    ))
    page0.add(Polygon(
        x_mm=141.7,
        y_mm=-12.5,
        w_mm=6.3,
        h_mm=6.3,
        anname='ub30',
        layer=0,
        fill='Magenta',
    ))
    page0.add(Polygon(
        x_mm=156,
        y_mm=0,
        w_mm=6.3,
        h_mm=6.3,
        anname='ub2f',
        layer=0,
        fill='Magenta',
    ))
    page0.add(PolyLine(
        x_mm=83.281,
        y_mm=70.1158,
        w_mm=12.0417,
        h_mm=33.3215,
        sla_path='M-46.8 -34.13 C-56.32 -33.89 -66.87 -33.08 -77.23 -30.66 C-81.46 -29.67 -85.56 -28.33 -89.38 -26.23 C-91.3 -25.18 -93.05 -23.9 -94.45 -22.2 C-97.25 -18.81 -97.13 -14.74 -94.11 -11.56 C-92.11 -9.459 -89.64 -8.033 -87.05 -6.832 C-81.44 -4.235 -75.49 -2.815 -69.39 -2.078 C-63.54 -1.371 -57.71 -0.4965 -51.83 0 C-39.88 1.009 -28.01 0.5546 -16.28 -2.037 C-12.46 -2.881 -8.778 -4.161 -5.396 -6.183 C-3.248 -7.467 -1.335 -9.029 -0.01946 -11.19 C2.032 -14.57 2.151 -17.98 0 -21.37 C-1.886 -24.35 -4.503 -26.49 -7.642 -28.03 C-11.38 -29.86 -15.36 -30.91 -19.41 -31.73 C-28.08 -33.5 -36.86 -34.18 -46.8 -34.13 Z M-51.2 -3.379 C-56.01 -3.391 -61.96 -3.39 -67.87 -4.143 C-73.79 -4.898 -79.58 -6.198 -85.05 -8.67 C-87.59 -9.817 -90.01 -11.17 -91.96 -13.21 C-94.09 -15.44 -94.13 -17.91 -92.14 -20.25 C-90.86 -21.76 -89.26 -22.86 -87.52 -23.78 C-83.58 -25.86 -79.36 -27.18 -75.01 -28.05 C-58.89 -31.27 -42.66 -32.08 -26.34 -29.84 C-21.19 -29.13 -16.08 -28.15 -11.2 -26.27 C-7.737 -24.94 -4.662 -23.04 -2.463 -19.96 C-0.6168 -17.37 -0.6048 -14.72 -2.358 -12.07 C-3.455 -10.41 -4.957 -9.188 -6.617 -8.133 C-7.176 -7.778 -7.772 -7.553 -8.421 -7.442 C-22.21 -5.087 -36.08 -3.647 -51.2 -3.379 Z M-11.97 -5.715 C-16.8 -3.165 -37.87 -0.5808 -44.63 -1.706 C-33.57 -2.395 -22.74 -3.766 -11.97 -5.715 Z',
        line_color='Black',
        line_width_pt=1,
        anname='ub72',
        layer=0,
        rotation_deg=-90,
    ))
    # h_mm widened 24.1173mm→43.7444mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=36.41pt; IDML overflows silently)
    page0.add(TextFrame(
        x_mm=6.3,
        y_mm=57.0735,
        w_mm=90,
        h_mm=43.7444,
        anname='ub73',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine', font='Gotham Narrow Ultra', fontsize=40, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=40, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    # h_mm widened 12.4217mm→17.3795mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=20.23pt; IDML overflows silently)
    page0.add(TextFrame(
        x_mm=6.3,
        y_mm=86.2783,
        w_mm=90,
        h_mm=17.3795,
        anname='ub92',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin die Subheadline,', font='Gotham Narrow Book', fontsize=19, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='die dazupasst.', font='Gotham Narrow Book', fontsize=19, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    page0.add(Polygon(
        x_mm=70.5307,
        y_mm=43.5612,
        w_mm=27.8451,
        h_mm=27.8451,
        anname='uba9',
        layer=0,
        rotation_deg=-18,
        fill='Magenta',
        shape='ellipse',
    ))
    # h_mm widened 4.1291mm→10.4069mm: Scribus clips lines when frame_h < effective line height (leading=13.17pt; IDML overflows silently)
    page0.add(TextFrame(
        x_mm=74,
        y_mm=52.6388,
        w_mm=27.8451,
        h_mm=10.4069,
        anname='ubaa',
        layer=0,
        rotation_deg=-9,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Störer', font='Gotham Narrow Ultra', fontsize=15, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'})],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))


def _add_page_1(doc: Document, page1) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 2 (Spread Spreads/Spread_u1d1.xml)."""
    page1.add(Polygon(
        x_mm=-3,
        y_mm=-3,
        w_mm=302,
        h_mm=111,
        anname='u676',
        layer=0,
        fill='Dunkelgrün',
    ))
    page1.add(PolyLine(
        x_mm=26.9005,
        y_mm=48.3013,
        w_mm=19.1982,
        h_mm=0.9961,
        sla_path='M53.27 0.659 C46.44 0.3189 39.6 0.02792 32.77 0 C25.93 -0.02797 19.1 0.1069 12.26 0.1673 C10.36 0.184 8.457 0.2086 6.555 0.2411 C5.584 0.2577 4.612 0.2715 3.641 0.2866 C2.671 0.3018 1.692 0.2773 0.729 0.3876 C0.3111 0.4355 -0.02705 0.7777 0 1.213 C0.02884 1.676 0.404 1.917 0.8258 1.942 C1.695 1.994 2.568 1.934 3.437 1.907 C4.287 1.881 5.136 1.855 5.986 1.837 C7.705 1.801 9.425 1.771 11.15 1.747 C14.55 1.701 17.95 1.72 21.35 1.78 C28.19 1.902 35.04 2.151 41.88 2.366 C45.72 2.486 49.57 2.639 53.41 2.824 C53.97 2.851 54.48 2.212 54.42 1.674 C54.35 1.035 53.88 0.6893 53.27 0.659 C53.27 0.659 53.27 0.659 53.27 0.659 Z',
        line_color='Black',
        line_width_pt=1,
        anname='u678',
        layer=0,
    ))
    page1.add(PolyLine(
        x_mm=122.819,
        y_mm=39.5,
        w_mm=11.749,
        h_mm=3.8145,
        sla_path='M10.73 0.01935 C10.76 0.0419 10.79 0.02812 10.81 0.065 C10.89 0.06586 10.98 0.1012 11.06 0.08221 C11.07 0.08597 11.09 0.09143 11.1 0.09335 C11.77 0.187 12.44 0.3362 13.11 0.4828 C14.03 0.6846 14.94 0.9255 15.86 1.173 C16.17 1.256 16.48 1.346 16.79 1.433 C16.73 1.484 16.67 1.477 16.62 1.475 C16.09 1.465 15.56 1.463 15.04 1.486 C13.98 1.534 12.92 1.659 11.86 1.808 C10.93 1.939 10.01 2.101 9.082 2.318 C7.965 2.58 6.85 2.886 5.74 3.269 C4.53 3.686 3.33 4.186 2.16 4.942 C1.635 5.28 1.117 5.648 0.6262 6.16 C0.3609 6.437 0.1521 6.825 0 7.34 C-0.08241 7.62 -0.07121 7.923 0.03886 8.156 C0.08782 8.26 0.1376 8.363 0.1971 8.444 C0.7716 9.225 1.415 9.665 2.087 9.96 C2.1 9.97 2.112 9.983 2.125 9.989 C2.677 10.23 3.235 10.4 3.799 10.49 C4.578 10.62 5.359 10.68 6.14 10.7 C7.136 10.73 8.132 10.73 9.128 10.75 C9.152 10.79 9.181 10.77 9.207 10.77 C9.446 10.78 9.684 10.78 9.922 10.79 C9.96 10.79 9.999 10.77 10.03 10.81 C12.26 10.81 14.48 10.81 16.71 10.81 C16.73 10.78 16.76 10.79 16.78 10.79 C17.02 10.78 17.26 10.78 17.5 10.77 C17.52 10.77 17.56 10.79 17.58 10.75 C18.61 10.71 19.64 10.67 20.67 10.6 C21.68 10.53 22.7 10.48 23.71 10.39 C24.86 10.3 26.01 10.19 27.15 10.05 C27.33 10.03 27.51 9.992 27.69 9.96 C27.69 9.96 27.68 9.954 27.68 9.954 C27.68 9.953 27.68 9.953 27.68 9.953 C27.68 9.955 27.69 9.958 27.69 9.96 C27.7 9.963 27.71 9.97 27.73 9.967 C28.13 9.893 28.54 9.836 28.94 9.74 C29.72 9.553 30.5 9.373 31.27 9.068 C31.75 8.879 32.23 8.666 32.69 8.36 C32.81 8.28 32.94 8.207 33.04 8.048 C33.16 7.935 33.24 7.738 33.3 7.535 C33.42 7.196 33.43 6.812 33.22 6.558 C33.19 6.521 33.16 6.477 33.13 6.44 C32.83 6.082 32.51 5.864 32.18 5.652 C31.39 5.139 30.58 4.777 29.77 4.45 C29.43 4.312 29.08 4.173 28.73 4.064 C28.71 4.02 28.67 4.028 28.65 3.999 C28.72 4.005 28.79 4.019 28.87 4.03 C28.89 4.033 28.91 4.033 28.91 3.98 C28.91 3.932 28.89 3.916 28.87 3.922 C28.83 3.91 28.8 3.898 28.76 3.886 C27.97 3.643 27.19 3.323 26.4 3.083 C25.85 2.914 25.29 2.708 24.73 2.578 C24.08 2.427 23.43 2.222 22.78 2.095 C22.39 2.02 22 1.9 21.61 1.845 C21.14 1.779 20.66 1.719 20.19 1.636 C19.44 1.506 18.7 1.251 17.95 1.067 C17.28 0.9015 16.61 0.738 15.93 0.5967 C15.31 0.4676 14.7 0.3591 14.08 0.2749 C13.58 0.2068 13.08 0.1353 12.57 0.1016 C12.55 0.09492 12.54 0.08337 12.52 0.08221 C12.5 0.08133 12.49 0.08047 12.48 0.07957 C12.41 0.06857 12.34 0.06674 12.27 0.06645 C11.91 0.04402 11.56 0.02194 11.21 0 C11.21 0 11.2 0 11.2 0 C11.04 0 10.88 0 10.72 0 C10.72 0.00885 10.73 0.01457 10.73 0.01935 Z M30.99 5.767 C31.48 6 31.98 6.237 32.45 6.6 C32.55 6.673 32.64 6.768 32.72 6.906 C32.8 7.056 32.79 7.175 32.7 7.278 C32.5 7.487 32.28 7.599 32.07 7.72 C31.39 8.101 30.7 8.322 30 8.508 C28.62 8.875 27.24 9.079 25.86 9.24 C24.04 9.451 22.22 9.549 20.4 9.667 C17.16 9.877 13.93 9.899 10.7 9.874 C9.059 9.861 7.423 9.837 5.786 9.809 C4.982 9.796 4.178 9.734 3.377 9.587 C2.698 9.462 2.026 9.252 1.374 8.844 C1.142 8.699 0.9249 8.49 0.732 8.188 C0.5211 7.859 0.52 7.61 0.7257 7.267 C0.845 7.068 0.9904 6.958 1.12 6.796 C1.146 6.777 1.172 6.762 1.196 6.739 C1.445 6.505 1.697 6.287 1.957 6.108 C2.899 5.458 3.86 4.93 4.837 4.532 C5.859 4.116 6.888 3.787 7.921 3.504 C8.516 3.341 9.113 3.192 9.71 3.067 C10.34 2.934 10.98 2.82 11.61 2.707 C12.29 2.586 12.97 2.504 13.65 2.426 C14.38 2.342 15.12 2.275 15.85 2.248 C17.03 2.204 18.2 2.214 19.37 2.244 C19.45 2.246 19.52 2.249 19.59 2.268 C19.97 2.368 20.35 2.479 20.74 2.576 C21.44 2.754 22.14 2.984 22.84 3.172 C23.05 3.23 23.27 3.311 23.48 3.335 C23.66 3.388 23.83 3.444 24.01 3.493 C24.4 3.602 24.79 3.707 25.18 3.813 C25.69 3.949 26.19 4.088 26.69 4.219 C27.12 4.331 27.55 4.467 27.98 4.605 C28.99 4.931 29.99 5.298 30.99 5.767 Z M27.64 3.674 C27.63 3.671 27.63 3.668 27.62 3.665 C27.63 3.668 27.63 3.671 27.64 3.673 C27.64 3.673 27.64 3.673 27.64 3.674 Z M26.76 3.393 C26.76 3.393 26.76 3.393 26.76 3.393 C26.74 3.401 26.72 3.391 26.71 3.402 C26.72 3.407 26.74 3.412 26.76 3.417 C26.74 3.424 26.72 3.405 26.71 3.402 C26.34 3.3 25.97 3.194 25.6 3.096 C25.42 3.05 25.25 2.985 25.08 2.969 C25.06 2.968 25.05 2.948 25.03 2.937 C25.04 2.924 25.04 2.916 25.05 2.911 C25.05 2.911 25.05 2.911 25.05 2.911 C25.08 2.89 25.12 2.924 25.15 2.9 C25.23 2.971 25.33 2.927 25.42 2.954 C25.82 3.078 26.22 3.189 26.63 3.304 C26.68 3.318 26.72 3.389 26.78 3.362 C26.77 3.38 26.77 3.388 26.76 3.393 Z',
        line_color='Black',
        line_width_pt=1,
        anname='u679',
        layer=0,
    ))
    page1.add(TextFrame(
        x_mm=138,
        y_mm=93,
        w_mm=53.4,
        h_mm=10,
        anname='u693',
        layer=0,
        rotation_deg=-90,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Impressum: xxxxxx', font='Gotham Narrow Book', fontsize=6, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'})],
        trail_attrs={'LINESPMode': '1'},
    ))
    # h_mm widened 17.9915mm→33.1611mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    page1.add(TextFrame(
        x_mm=15,
        y_mm=14.8444,
        w_mm=65.2174,
        h_mm=33.1611,
        anname='u6aa',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    # h_mm widened 53.7551mm→63.5000mm: Scribus clips lines when frame_h < 11 explicit lines × line height (leading=14.30pt; IDML overflows silently)
    page1.add(TextFrame(
        x_mm=15,
        y_mm=39.1359,
        w_mm=118,
        h_mm=63.5,
        anname='u6d8',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Lia vellam, conemporro modi\u2028tatque nii tectotmusa qui tota nis quam quis quae cum et arum vendellab voloriaspita dis quaturem. Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
    ))


def _add_page_2(doc: Document, page2) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 3 (Spread Spreads/Spread_u1d1.xml)."""
    page2.add(PolyLine(
        x_mm=43.002,
        y_mm=69.5001,
        w_mm=25.0055,
        h_mm=1.1564,
        sla_path='M70.35 1.964 C68.11 1.678 65.86 1.509 63.61 1.328 C61.38 1.148 59.14 0.9852 56.9 0.8385 C52.35 0.5406 47.8 0.3467 43.25 0.2093 C38.76 0.07378 34.27 0.003983 29.77 0 C25.28 -0.004017 20.78 0.06575 16.29 0.1586 C11.78 0.2518 7.274 0.4107 2.768 0.565 C2.496 0.5742 2.225 0.5846 1.953 0.5935 C1.667 0.6029 1.383 0.6656 1.101 0.7124 C0.7816 0.7651 0.5038 0.8699 0.2861 1.122 C0.09529 1.343 -0.03504 1.693 0 1.988 C0.08303 2.687 0.606 3.065 1.275 3.088 C1.547 3.098 1.822 3.121 2.093 3.102 C2.393 3.081 2.694 3.048 2.994 3.021 C3.549 2.972 4.105 2.924 4.661 2.877 C5.787 2.782 6.914 2.682 8.042 2.613 C10.27 2.477 12.5 2.357 14.72 2.254 C19.23 2.044 23.73 1.931 28.24 1.888 C32.73 1.846 37.22 1.87 41.71 1.96 C46.2 2.049 50.69 2.227 55.17 2.421 C59.68 2.615 64.03 2.867 68.51 3.193 C69.09 3.236 69.68 3.252 70.27 3.278 C70.6 3.292 70.87 2.952 70.88 2.656 C70.9 2.347 70.69 2.006 70.35 1.964 C70.35 1.964 70.35 1.964 70.35 1.964 Z',
        line_color='Black',
        line_width_pt=1,
        anname='u677',
        layer=0,
    ))
    page2.add(PolyLine(
        x_mm=47.5693,
        y_mm=23.3405,
        w_mm=25.399,
        h_mm=1.8007,
        sla_path='M71.71 1.309 C71.48 1.028 70.78 0.6713 70.19 0.6043 C69.76 0.5556 69.33 0.4789 68.9 0.454 C68.65 0.4395 68.39 0.4452 68.13 0.44 C67.57 0.4284 67.01 0.4167 66.45 0.405 C65.42 0.3839 64.4 0.3627 63.38 0.3416 C61.28 0.2981 59.18 0.295 57.08 0.281 C52.85 0.253 48.62 0.2251 44.4 0.1971 C35.99 0.1414 27.58 0.1281 19.18 0.09774 C14.44 0.08063 9.698 0.06433 4.959 0 C3.721 -0.01687 2.481 0.1757 1.543 0.6207 C0.7097 1.016 0.02788 1.688 0 2.291 C-0.02984 2.939 0.2922 3.628 1.169 4.106 C1.468 4.244 1.767 4.381 2.067 4.519 C2.749 4.758 3.498 4.893 4.313 4.925 C5.453 5.028 6.64 5.047 7.791 5.104 C8.614 5.145 9.615 5.012 10.39 4.767 C16.72 4.619 23.05 4.517 29.38 4.394 C37.74 4.232 46.1 4.056 54.45 3.869 C56.77 3.817 59.08 3.766 61.4 3.714 C63.89 3.658 66.39 3.539 68.88 3.447 C69.01 3.443 69.14 3.44 69.27 3.434 C69.32 3.425 69.37 3.415 69.42 3.406 C69.56 3.387 69.71 3.368 69.85 3.349 C70.96 3.203 71.97 2.692 72 2.052 C72.01 1.795 71.91 1.543 71.71 1.309 Z',
        line_color='Black',
        line_width_pt=1,
        anname='u67b',
        layer=0,
    ))
    page2.add(TextFrame(
        x_mm=15,
        y_mm=39.1359,
        w_mm=118,
        h_mm=53.7551,
        anname='u67c',
        layer=0,
        style='idml/aufzaehlungen-auf-gruenem-hintergrund',
        runs=[Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Scim rem ', font='Gotham Narrow Black'), Run(text='utas si vellaccum eatus nullquae cum et arum vendellab iditatequi aut qui beat audit re.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Tissi iuntem ressiti ', font='Gotham Narrow Black'), Run(text='orerovi tectotmusaqui tota nis quam.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Uaerum ium ', font='Gotham Narrow Black'), Run(text='verior alicide liquuntio. ', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Ur, omniet ', font='Gotham Narrow Book'), Run(text='vello modi ', font='Gotham Narrow Black'), Run(text='aceprate pem ssi iuntem ilis', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='•', font='Gotham Narrow Book'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='Lia vellam, conemporro ', font='Gotham Narrow Book'), Run(text='moditatque', font='Gotham Narrow Black'), Run(text=' nimil maxim voluptur.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para'), Run(text='', font='Gotham Narrow Book', separator='tab'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0'}, separator='para')],
    ))
    # h_mm widened 17.9915mm→24.6944mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    page2.add(TextFrame(
        x_mm=15,
        y_mm=14.8444,
        w_mm=75,
        h_mm=24.6944,
        anname='u6c1',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin auch eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'})],
        trail_attrs={'LINESPMode': '1'},
    ))
    page2.add(PolyLine(
        x_mm=91.8817,
        y_mm=61.8951,
        w_mm=25.2129,
        h_mm=30.6143,
        sla_path='M38.25 46.19 C41.59 46.19 44.29 43.44 44.29 40.06 C44.29 36.68 41.59 33.93 38.25 33.93 C34.91 33.93 32.21 36.68 32.21 40.06 C32.21 43.44 34.91 46.19 38.25 46.19 Z M35.62 30.75 L31.13 24.52 L42.38 0 L47.73 0.867 L43.34 32.04 M47.85 41.92 L55.48 41.01 L71.47 62.73 L68.12 67 L42.98 48.05 M31.87 47.19 L28.81 54.24 L1.992 57.1 L0 52.06 L29.03 39.89 M35.25 50.19 L33.01 77.34 M41.29 50.92 L43.82 81.21 L49.88 81.21 L49.88 86.78 M39.19 81.21 L26.65 81.21 L26.65 86.78',
        line_color='Gelb',
        line_width_pt=2.1637499928474426,
        anname='u6ef',
        layer=0,
        line_cap=32,
        line_join=128,
    ))


def _add_page_3(doc: Document, page3) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 4 (Spread Spreads/Spread_u1dd.xml)."""
    page3.add(PolyLine(
        x_mm=53.1638,
        y_mm=93.15,
        w_mm=22.3105,
        h_mm=5.9,
        sla_path='M-20.38 -0.02993 C-20.43 -0.06481 -20.49 -0.0435 -20.53 -0.1005 C-20.69 -0.1019 -20.84 -0.1565 -21 -0.1272 C-21.03 -0.133 -21.05 -0.1414 -21.08 -0.1444 C-22.35 -0.2893 -23.62 -0.52 -24.89 -0.7468 C-26.64 -1.059 -28.38 -1.432 -30.12 -1.814 C-30.71 -1.943 -31.29 -2.082 -31.88 -2.217 C-31.77 -2.295 -31.66 -2.284 -31.56 -2.282 C-30.55 -2.266 -29.55 -2.262 -28.55 -2.299 C-26.54 -2.372 -24.53 -2.566 -22.52 -2.797 C-20.76 -2.999 -19 -3.25 -17.25 -3.586 C-15.12 -3.991 -13.01 -4.464 -10.9 -5.056 C-8.603 -5.702 -6.324 -6.475 -4.101 -7.644 C-3.105 -8.167 -2.12 -8.736 -1.189 -9.528 C-0.6854 -9.956 -0.2888 -10.56 0 -11.35 C0.1565 -11.79 0.1352 -12.25 -0.07379 -12.62 C-0.1668 -12.78 -0.2613 -12.93 -0.3743 -13.06 C-1.465 -14.27 -2.687 -14.95 -3.963 -15.41 C-3.987 -15.42 -4.01 -15.44 -4.034 -15.45 C-5.083 -15.83 -6.143 -16.08 -7.213 -16.22 C-8.693 -16.42 -10.18 -16.52 -11.66 -16.55 C-13.55 -16.59 -15.44 -16.6 -17.33 -16.63 C-17.38 -16.69 -17.43 -16.66 -17.48 -16.66 C-17.94 -16.67 -18.39 -16.68 -18.84 -16.69 C-18.91 -16.69 -18.99 -16.66 -19.06 -16.72 C-23.28 -16.72 -27.5 -16.72 -31.73 -16.72 C-31.77 -16.67 -31.82 -16.69 -31.86 -16.69 C-32.32 -16.68 -32.77 -16.67 -33.22 -16.66 C-33.28 -16.66 -33.34 -16.69 -33.39 -16.62 C-35.34 -16.57 -37.29 -16.5 -39.25 -16.39 C-41.17 -16.29 -43.1 -16.2 -45.03 -16.07 C-47.21 -15.93 -49.39 -15.76 -51.57 -15.55 C-51.9 -15.52 -52.24 -15.45 -52.57 -15.41 C-52.57 -15.41 -52.57 -15.4 -52.57 -15.4 C-52.57 -15.4 -52.57 -15.39 -52.57 -15.39 C-52.57 -15.4 -52.57 -15.4 -52.57 -15.41 C-52.6 -15.41 -52.63 -15.42 -52.65 -15.42 C-53.42 -15.3 -54.19 -15.21 -54.95 -15.06 C-56.43 -14.78 -57.92 -14.5 -59.39 -14.03 C-60.3 -13.73 -61.2 -13.4 -62.08 -12.93 C-62.31 -12.81 -62.55 -12.69 -62.75 -12.45 C-62.97 -12.27 -63.12 -11.97 -63.24 -11.65 C-63.45 -11.13 -63.48 -10.54 -63.08 -10.14 C-63.02 -10.09 -62.97 -10.02 -62.91 -9.961 C-62.35 -9.407 -61.73 -9.07 -61.11 -8.742 C-59.61 -7.949 -58.07 -7.389 -56.53 -6.883 C-55.88 -6.669 -55.22 -6.455 -54.56 -6.287 C-54.52 -6.217 -54.45 -6.23 -54.4 -6.185 C-54.54 -6.195 -54.68 -6.216 -54.82 -6.234 C-54.85 -6.238 -54.9 -6.238 -54.9 -6.156 C-54.9 -6.081 -54.87 -6.057 -54.82 -6.067 C-54.75 -6.048 -54.68 -6.029 -54.61 -6.011 C-53.12 -5.634 -51.63 -5.14 -50.14 -4.769 C-49.08 -4.507 -48.03 -4.189 -46.97 -3.988 C-45.73 -3.754 -44.5 -3.436 -43.26 -3.241 C-42.52 -3.124 -41.78 -2.939 -41.04 -2.854 C-40.14 -2.752 -39.24 -2.659 -38.34 -2.531 C-36.92 -2.329 -35.51 -1.935 -34.09 -1.651 C-32.81 -1.394 -31.53 -1.141 -30.25 -0.923 C-29.08 -0.7232 -27.91 -0.5555 -26.73 -0.4252 C-25.78 -0.3198 -24.83 -0.2092 -23.88 -0.1571 C-23.84 -0.1468 -23.81 -0.129 -23.77 -0.1272 C-23.74 -0.1258 -23.72 -0.1245 -23.69 -0.1231 C-23.56 -0.1061 -23.43 -0.1032 -23.29 -0.1028 C-22.62 -0.06809 -21.95 -0.03394 -21.28 0 C-21.28 0 -21.28 0 -21.27 0 C-20.97 0 -20.66 0 -20.35 0 C-20.36 -0.01369 -20.37 -0.02254 -20.38 -0.02993 Z M-58.85 -8.92 C-59.79 -9.28 -60.73 -9.648 -61.63 -10.21 C-61.81 -10.32 -61.98 -10.47 -62.13 -10.68 C-62.28 -10.91 -62.27 -11.1 -62.09 -11.26 C-61.71 -11.58 -61.3 -11.75 -60.89 -11.94 C-59.61 -12.53 -58.29 -12.87 -56.97 -13.16 C-54.36 -13.73 -51.73 -14.04 -49.11 -14.29 C-45.65 -14.62 -42.19 -14.77 -38.73 -14.95 C-32.59 -15.28 -26.45 -15.31 -20.31 -15.27 C-17.2 -15.25 -14.1 -15.21 -10.99 -15.17 C-9.46 -15.15 -7.934 -15.06 -6.413 -14.83 C-5.124 -14.64 -3.848 -14.31 -2.609 -13.68 C-2.168 -13.46 -1.756 -13.13 -1.39 -12.67 C-0.9896 -12.16 -0.9874 -11.77 -1.378 -11.24 C-1.605 -10.93 -1.881 -10.76 -2.127 -10.51 C-2.176 -10.48 -2.225 -10.46 -2.272 -10.42 C-2.744 -10.06 -3.222 -9.724 -3.715 -9.448 C-5.506 -8.442 -7.329 -7.626 -9.185 -7.01 C-11.13 -6.366 -13.08 -5.858 -15.04 -5.42 C-16.17 -5.167 -17.3 -4.938 -18.44 -4.744 C-19.64 -4.539 -20.85 -4.361 -22.05 -4.187 C-23.34 -4 -24.63 -3.872 -25.92 -3.752 C-27.31 -3.622 -28.71 -3.519 -30.11 -3.476 C-32.33 -3.408 -34.56 -3.424 -36.79 -3.471 C-36.93 -3.474 -37.07 -3.479 -37.21 -3.508 C-37.93 -3.663 -38.65 -3.835 -39.38 -3.984 C-40.71 -4.259 -42.04 -4.615 -43.37 -4.907 C-43.77 -4.996 -44.18 -5.122 -44.59 -5.159 C-44.92 -5.24 -45.26 -5.328 -45.59 -5.403 C-46.34 -5.571 -47.08 -5.734 -47.82 -5.898 C-48.78 -6.108 -49.73 -6.322 -50.69 -6.525 C-51.5 -6.699 -52.31 -6.909 -53.13 -7.123 C-55.05 -7.626 -56.96 -8.194 -58.85 -8.92 Z M-52.49 -5.682 C-52.47 -5.677 -52.46 -5.673 -52.45 -5.669 C-52.46 -5.673 -52.47 -5.677 -52.49 -5.682 C-52.49 -5.682 -52.49 -5.682 -52.49 -5.682 Z M-50.81 -5.248 C-50.81 -5.248 -50.81 -5.248 -50.81 -5.249 C-50.78 -5.261 -50.75 -5.244 -50.72 -5.262 C-50.75 -5.27 -50.78 -5.278 -50.81 -5.286 C-50.78 -5.296 -50.75 -5.267 -50.72 -5.262 C-50.01 -5.104 -49.31 -4.941 -48.61 -4.789 C-48.28 -4.718 -47.95 -4.618 -47.62 -4.592 C-47.59 -4.59 -47.56 -4.56 -47.53 -4.543 C-47.54 -4.522 -47.56 -4.511 -47.57 -4.503 C-47.57 -4.503 -47.57 -4.502 -47.57 -4.502 C-47.63 -4.47 -47.7 -4.523 -47.76 -4.486 C-47.92 -4.596 -48.09 -4.528 -48.26 -4.57 C-49.03 -4.761 -49.8 -4.933 -50.57 -5.11 C-50.66 -5.132 -50.75 -5.242 -50.85 -5.201 C-50.84 -5.228 -50.83 -5.241 -50.81 -5.248 Z',
        line_color='Black',
        line_width_pt=1,
        anname='u962',
        layer=0,
        rotation_deg=180,
    ))
    # h_mm widened 17.9915mm→24.6944mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    # P5/playbook y_mm_shift.py: y_mm 15.0 → 15.5 (calibration probe (+0.5mm))
    page3.add(TextFrame(
        x_mm=15,
        y_mm=15.5,
        w_mm=118,
        h_mm=24.6944,
        anname='u872',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    # h_mm widened 53.7551mm→63.5000mm: Scribus clips lines when frame_h < 11 explicit lines × line height (leading=14.30pt; IDML overflows silently)
    page3.add(TextFrame(
        x_mm=15,
        y_mm=39.1359,
        w_mm=118,
        h_mm=63.5,
        anname='u92e',
        layer=0,
        style='idml/fliesstext-auf-weissem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow Book'), Run(text='', has_itext=False, paragraph_style='idml/fliesstext-auf-weissem-hintergrund', paragraph_attrs={'ALIGN': '3'}, separator='para'), Run(text='Lia vellam, conemporro modi\u2028tatque nii tectotmusa qui tota nis quam quis quae cum et arum vendellab voloriaspita dis quaturem. Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-weissem-hintergrund')],
    ))
    page3.add(PolyLine(
        x_mm=106.2005,
        y_mm=58.7013,
        w_mm=19.1982,
        h_mm=0.9961,
        sla_path='M53.27 0.659 C46.44 0.3189 39.6 0.02792 32.77 0 C25.93 -0.02797 19.1 0.1069 12.26 0.1673 C10.36 0.184 8.457 0.2086 6.555 0.2411 C5.584 0.2577 4.612 0.2715 3.641 0.2866 C2.671 0.3018 1.692 0.2773 0.729 0.3876 C0.3111 0.4355 -0.02705 0.7777 0 1.213 C0.02884 1.676 0.404 1.917 0.8258 1.942 C1.695 1.994 2.568 1.934 3.437 1.907 C4.287 1.881 5.136 1.855 5.986 1.837 C7.705 1.801 9.425 1.771 11.15 1.747 C14.55 1.701 17.95 1.72 21.35 1.78 C28.19 1.902 35.04 2.151 41.88 2.366 C45.72 2.486 49.57 2.639 53.41 2.824 C53.97 2.851 54.48 2.212 54.42 1.674 C54.35 1.035 53.88 0.6893 53.27 0.659 C53.27 0.659 53.27 0.659 53.27 0.659 Z',
        line_color='Black',
        line_width_pt=1,
        anname='u948',
        layer=0,
    ))
    page3.add(TextFrame(
        x_mm=138,
        y_mm=93.15,
        w_mm=53.4,
        h_mm=10,
        anname='u85a',
        layer=0,
        rotation_deg=-90,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Impressum: xxxxxx', font='Gotham Narrow Book', fontsize=6, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'})],
        trail_attrs={'LINESPMode': '1'},
    ))


def _add_page_4(doc: Document, page4) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 5 (Spread Spreads/Spread_u1dd.xml)."""
    # noinject: green-pine-trees-covered-with-fog.jpg is a CMYK JPEG; Scribus 1.6.x
    # renders CMYK JPEGs blank (links_export.py passes them through unchanged). No
    # converter fix exists — accepted residual, classified authoring-bug.
    page4.add(ImageFrame(
        x_mm=0,
        y_mm=-3,
        w_mm=151,
        h_mm=42.2915,
        anname='u906',
        layer=0,
        image='../../shared/assets/26-03-flyer-a6-gruenes-cover/green-pine-trees-covered-with-fog.jpg',
        scale_type=0,
    ))
    page4.add(Polygon(
        x_mm=160,
        y_mm=32.9915,
        w_mm=6.3,
        h_mm=6.3,
        anname='u92d',
        layer=0,
        fill='Magenta',
    ))
    # h_mm widened 17.9915mm→24.6944mm: Scribus clips lines when frame_h < 2 explicit lines × line height (leading=27.00pt; IDML overflows silently)
    page4.add(TextFrame(
        x_mm=15,
        y_mm=15,
        w_mm=118,
        h_mm=24.6944,
        anname='u90b',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin auch ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '1'}, separator='para'), Run(text='eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'LINESPMode': '1'},
    ))
    page4.add(TextFrame(
        x_mm=15,
        y_mm=45.55,
        w_mm=118,
        h_mm=42.2915,
        anname='u9df',
        layer=0,
        style='idml/aufzaehlungen-auf-gruenem-hintergrund',
        runs=[Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='•', font='Gotham Narrow Book', fcolor='Dunkelgrün', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '2', 'LINESP': '8.0'}), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='Scim rem ', font='Gotham Narrow Black', fcolor='Dunkelgrün'), Run(text='utas si vellaccum eatus nullquae cum et arum vendellab iditatequi aut qui beat audit re.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '2', 'LINESP': '8.0'}, separator='para'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='•', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='Uaerum ium ', font='Gotham Narrow Black', fcolor='Dunkelgrün'), Run(text='verior alicide liquuntio. ', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '2', 'LINESP': '8.0'}, separator='para'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='•', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='Ur, omniet ', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='vello modi ', font='Gotham Narrow Black', fcolor='Dunkelgrün'), Run(text='aceprate pem ssi iuntem ilis', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '2', 'LINESP': '8.0'}, separator='para'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='•', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='Lia vellam, conemporro ', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='moditatque', font='Gotham Narrow Black', fcolor='Dunkelgrün'), Run(text=' nimil maxim voluptur.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '2', 'LINESP': '8.0'}, separator='para'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='•', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', font='Gotham Narrow Bold', fcolor='Dunkelgrün', separator='tab'), Run(text='Ur, omniet vello', font='Gotham Narrow Bold', fcolor='Dunkelgrün'), Run(text=' modi aceprate pem ssi ir, quis et quaturem', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', font='Gotham Narrow Book', fcolor='Dunkelgrün', separator='tab'), Run(text='', has_itext=False, paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'ALIGN': '0', 'LINESPMode': '2', 'LINESP': '8.0'}, separator='para')],
        trail_attrs={'LINESPMode': '2', 'LINESP': '8.0'},
    ))


def _add_page_5(doc: Document, page5) -> None:  # overrides task-3 stub
    """Auto-generated page-items for spread 6 (Spread Spreads/Spread_u781.xml)."""
    page5.add(TextFrame(
        x_mm=-3,
        y_mm=108,
        w_mm=111,
        h_mm=154,
        anname='ubd1',
        layer=0,
        rotation_deg=-90,
        style='idml/normalparagraphstyle',
        text='',
        fill='C_88_M_44_Y_100_K_0',
    ))
    # noinject: 2026-03-leonore-fuer-flyer.png is converted from a CMYK PSD; the
    # links_export.py convert -flatten recipe yields non-ICC CMYK->RGB output that
    # posterizes/discolours the portrait. No converter fix — accepted, authoring-bug.
    page5.add(ImageFrame(
        x_mm=-8.8509,
        y_mm=9.9892,
        w_mm=82.8509,
        h_mm=98.0108,
        anname='ube9',
        layer=0,
        image='../../shared/assets/26-03-flyer-a6-gruenes-cover/2026-03-leonore-fuer-flyer.png',
        local_scale=(0.48994, 0.48994),
        scale_type=1,
        local_offset_mm=(12.6372, 0),
    ))
    # h_mm widened 22.0927mm→37.9236mm: Scribus clips lines when frame_h < 3 explicit lines × line height (leading=20.48pt; IDML overflows silently)
    # P5/playbook y_mm_shift.py: y_mm 44.9809 → 47.0129 (uniform +-5.76pt × sign=-1 → +2.0320mm)
    page5.add(TextFrame(
        x_mm=51.01,
        y_mm=47.0129,
        w_mm=87.24,
        h_mm=37.9236,
        anname='ubf1',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin ein Zitat. Ich bin ein prägnantes', font='Vollkorn Black Italic', fontsize=23, fcolor='White', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}), Run(text='', has_itext=False, paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'}, separator='para'), Run(text='Zitat.', font='Vollkorn Black Italic', fontsize=23, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))
    # h_mm widened 3.1044mm→8.0081mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
    page5.add(TextFrame(
        x_mm=73.7986,
        y_mm=70.6736,
        w_mm=41.6629,
        h_mm=8.0081,
        anname='uc08',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Leonore Gewessler', font='Gotham Narrow Book', fontsize=11, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle', paragraph_attrs={'ALIGN': '1', 'LINESPMode': '1'})],
        trail_attrs={'ALIGN': '1', 'LINESPMode': '1'},
    ))
    page5.add(PolyLine(
        x_mm=88.4125,
        y_mm=31.3543,
        w_mm=12.4619,
        h_mm=9.9219,
        sla_path='M20.18 28.12 C29.1 27.38 35.33 23.62 35.33 12.9 C35.33 12.9 35.33 0 35.33 0 C35.33 0 19.57 0 19.57 0 C19.57 0 19.57 16.12 19.57 16.12 C19.57 16.12 26.18 16.12 26.18 16.12 C26.02 19.35 23.77 21.53 18.9 22.27 C18.9 22.27 20.18 28.12 20.18 28.12 Z M1.275 28.12 C10.13 27.38 16.35 23.62 16.35 12.9 C16.35 12.9 16.35 0 16.35 0 C16.35 0 0.675 0 0.675 0 C0.675 0 0.675 16.12 0.675 16.12 C0.675 16.12 7.2 16.12 7.2 16.12 C7.125 19.35 4.8 21.53 0 22.27 C0 22.27 1.275 28.12 1.275 28.12 Z',
        line_color='White',
        line_width_pt=0.75,
        anname='uc1f',
        layer=0,
    ))
    page5.add(Polygon(
        x_mm=166,
        y_mm=41.4178,
        w_mm=3.6,
        h_mm=3.6,
        anname='uc20',
        layer=0,
        fill='Gelb',
    ))
    page5.add(Polygon(
        x_mm=166,
        y_mm=67.0736,
        w_mm=3.6,
        h_mm=3.6,
        anname='uc26',
        layer=0,
        fill='Gelb',
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


# --- IDML PageItems intentionally not emitted (machine-readable; do not delete) ---
# idml-skip: u6f0 — InDesign design artifact (entirely outside page+bleed)
# idml-skip: u6f2 — InDesign design artifact (entirely outside page+bleed)
# idml-skip: u77f — InDesign design artifact (entirely outside page+bleed)
# idml-skip: u964 — InDesign design artifact (entirely outside page+bleed)
