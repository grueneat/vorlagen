"""kandidat-falzflyer-din-lang-gruenes-cover-v2 — DSL build entry point.

Auto-generated from 26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml by tools/idml_to_dsl.py.
Hand-edit thereafter; this file is the source of truth.

NOTE: bleed_mm=2.0 below matches the IDML verbatim. Brand standard
is 3.0 mm; coerce only after team review.

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
    """Page 1 page items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def _add_page_1(doc: Document, page) -> None:
    """Page 2 page items — populated by tools/idml_to_dsl.py Phase H."""
    # (no page items in this task-3 skeleton)
    return None

def build_template() -> Document:
    """Return a clean Document with all frames defined.

    Emitted by tools/idml_to_dsl.py from the source IDML; hand-edit as needed.
    """
    doc = Document(
        brand=Brand.gruene_noe(),
        title='kandidat-falzflyer-din-lang-gruenes-cover-v2',
        template_id='kandidat-falzflyer-din-lang-gruenes-cover-v2',
        author="Die Grünen Niederösterreich",
        facing_pages=False,
        layers=[
            DocumentLayer(name='Gestaltung'),
            DocumentLayer(name='Info', printable=False, editable=False),
        ],
        extra_pdf_attrs={
            'cropMarks': '0',
            'bleedMarks': '0',
            # P5/inject: suppress document bleeds in PDF export to match baseline.pdf trim box.
            'useDocBleeds': '0',
        },
    )

    # add_styles(doc) - paragraph styles (Phase G, task 5)
    _add_styles(doc)

    doc.add_master(
        name="Normal",
        size=(297, 210),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
    )

    page0 = doc.add_page(
        size=(297, 210),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )
    page1 = doc.add_page(
        size=(297, 210),
        bleed_mm=0,
        margins_mm=(0.0, 0.0, 0.0, 0.0),
        master="Normal",
    )

    _add_page_0(doc, page0)
    _add_page_1(doc, page1)

    return doc


def _add_styles(doc: Document) -> None:  # overrides task-3 stub
    """Auto-generated paragraph styles from the source IDML."""
    doc.add_para_style(ParaStyle(
        name='idml/no-paragraph-style',
        font='Times Roman',
        fontsize=12,
        align=0,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/fliesstext-auf-gruenem-hintergrund',
        parent='idml/no-paragraph-style',
        font='Gotham Narrow Book',
        fontsize=11,
        align=3,
        fcolor='White',
        linesp=14.3,
        linesp_mode=0,
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
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle',
        parent='idml/no-paragraph-style',
        font='Times Roman',
        fontsize=12,
        align=0,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/absatzformat-1',
        parent='idml/fliesstext-auf-gruenem-hintergrund',
        font='Gotham Narrow Book',
        fontsize=11,
        align=3,
        fcolor='White',
        linesp=14.3,
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/aufzaehlungen-auf-gruenem-hintergrund',
        parent='idml/fliesstext-auf-gruenem-hintergrund',
        font='Gotham Narrow Book',
        fontsize=11,
        align=0,
        fcolor='White',
        linesp=14.3,
        linesp_mode=0,
        tab_stops=((5, 0), (13, 0)),
        # Hanging indent: first line at 0pt from frame, text wraps at 13pt
        # (matches InDesign bullet layout: •tab→5pt bullet tab→13pt text).
        first_indent_pt=-13,
        left_indent_pt=13,
    ))
    # P5/inject: custom styles for Störer label and subheadline.
    # Re-emit drops these styles (not in IDML style map); restore here.
    doc.add_para_style(ParaStyle(
        name='idml/subheadline-cover-zentriert',
        parent='idml/normalparagraphstyle',
        font='Gotham Narrow Book',
        fontsize=18,
        align=1,
        fcolor='White',
    ))
    # Phase H: per-leading style variants for LINESP from IDML CSR Properties/Leading.
    # LINESPMode=0 is Scribus "Auto" mode: when LINESP is explicit, Scribus applies it as
    # the fixed leading value. This matches the reference falzflyer/ci styles (all LINESPMode=0).
    # For LINESP < fontsize (e.g. 27pt for 30pt text), Scribus may fall back to auto-leading —
    # the IDML target is a best-effort approximation; overlap is prevented by using <breakline>
    # separators (single paragraph) instead of <para> separators (multiple paragraphs).
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle-27pt',
        parent='idml/normalparagraphstyle',
        linesp=27.0,
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/subheadline-cover-zentriert-18.96pt',
        parent='idml/subheadline-cover-zentriert',
        linesp=18.96350262577446,
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle-34.13pt',
        parent='idml/normalparagraphstyle',
        linesp=34.13430472639402,
        linesp_mode=0,
        align=1,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle-20.48pt',
        parent='idml/normalparagraphstyle',
        linesp=20.480582835836415,
        linesp_mode=0,
        align=1,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/normalparagraphstyle-14.3pt',
        parent='idml/normalparagraphstyle',
        linesp=14.3,
        linesp_mode=0,
        align=1,
    ))
    doc.add_para_style(ParaStyle(
        name='idml/stoerer-center',
        parent='idml/normalparagraphstyle',
        font='Gotham Narrow Ultra',
        fontsize=11,
        align=1,
        fcolor='White',
    ))
    return None


def _add_page_0(doc: Document, page0) -> None:  # overrides task-3 stub
    """Auto-generated page-items for page 1 (Spread Spreads/Spread_ueb.xml)."""
    page0.add(Polygon(
        x_mm=-1.8236,
        y_mm=-1.8236,
        w_mm=298.8236,
        h_mm=213.6472,
        anname='u1ae',
        layer=0,
        fill='Dunkelgrün',
    ))
    page0.add(ImageFrame(
        x_mm=273.24,
        y_mm=6.429,
        w_mm=17.82,
        h_mm=15.6052,
        anname='u141',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/gruene-logo-bund-weiss-cmyk.png',
        # Scribus SCALETYPE=1 does NOT auto-scale external PNGs; renders at natural pt/px.
        # natural_h_pt = 826px × (72/600) = 99.12pt; frame_h_pt = 15.6052mm × 2.83465 = 44.235pt
        # LOCALSCX = frame_h_pt / natural_h_pt = 44.235 / 99.12 = 0.44628
        scale_type=0,
        local_scale=(0.44628, 0.44628),
    ))
    page0.add(Polygon(
        x_mm=198.3236,
        y_mm=214.5,
        w_mm=6.3,
        h_mm=6.3,
        anname='u151',
        layer=0,
        fill='Magenta',
    ))
    page0.add(Polygon(
        x_mm=307.25,
        y_mm=203.7,
        w_mm=6.3,
        h_mm=6.3,
        anname='u513',
        layer=0,
        fill='Magenta',
    ))
    page0.add(TextFrame(
        x_mm=204.08,
        y_mm=119.146,
        w_mm=86.84,
        # h_mm: LINESP=18.96pt (from IDML CSR Leading), LINESPMode=0 in style.
        # IDML <Br/> → Scribus <breakline>: single paragraph, all lines share LINESP.
        # Frame: line 1 baseline ≈ ascender from frame top, line 2 baseline = line 1 + 18.96.
        # Line 2 bottom ≈ line2_baseline + descender ≈ (ascender + 18.96) + 4 ≈ 37pt from frame top.
        # Using 15.0mm (42.52pt) for margin.
        h_mm=15.0,
        anname='u516',
        layer=0,
        style='idml/subheadline-cover-zentriert-18.96pt',
        runs=[Run(text='Mehrzeilige Subheadline –', font='Gotham Narrow Book', fontsize=18, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='mehr Info zum Thema', font='Gotham Narrow Book', fontsize=18, fcolor='White')],
    ))
    page0.add(TextFrame(
        x_mm=211.6719,
        y_mm=79.2087,
        w_mm=71.6562,
        # h_mm: LINESP=34.13pt (IDML CSR Leading), LINESPMode=0, ALIGN=1 (CenterAlign in IDML).
        # IDML <Br/> → Scribus <breakline>: single paragraph, all 3 lines share LINESP=34.13.
        # Line 3 baseline ≈ 2×34.13 = 68.26pt from line 1. Bottom ≈ 68.26 + 38 = 106.26pt.
        # Need frame h ≥ 106.26pt = 37.5mm. Using 41.5mm (117.63pt) for margin.
        h_mm=41.5,
        anname='u52d',
        layer=0,
        style='idml/normalparagraphstyle-34.13pt',
        runs=[Run(text='Das ist die ', font='Gotham Narrow Ultra', fontsize=38, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='dreizeilige', font='Vollkorn Black Italic', fontsize=38, fcolor='Gelb'), Run(text='', has_itext=False, separator='breakline'), Run(text='Headline', font='Gotham Narrow Ultra', fontsize=38, fcolor='White')],
    ))
    page0.add(Polygon(
        x_mm=270.42,
        y_mm=64.53,
        w_mm=19.9,
        h_mm=19.9,
        anname='u185',
        layer=0,
        fill='Magenta',
        shape='ellipse',
    ))
    page0.add(TextFrame(
        # IDML u186 Störer text: Justification="CenterAlign" → use center-aligned style.
        # Baseline PDF: "Störer" at x0=274.66mm (within 269.81-290.92mm frame → centered).
        x_mm=269.81,
        y_mm=71.28,
        w_mm=21.11,
        h_mm=6.33,
        anname='u186',
        layer=0,
        style='idml/stoerer-center',
        runs=[Run(text='Störer', font='Gotham Narrow Ultra', fontsize=11, fcolor='White', paragraph_style='idml/stoerer-center')],
    ))
    page0.add(Polygon(
        x_mm=308.75,
        y_mm=186.6,
        w_mm=5.15,
        h_mm=5.15,
        anname='u19d',
        layer=0,
        fill='Dunkelgrün',
    ))
    page0.add(Polygon(
        x_mm=291.06,
        y_mm=-12.375,
        w_mm=5.94,
        h_mm=6.429,
        anname='u1ac',
        layer=0,
        fill='Magenta',
    ))
    page0.add(Polygon(
        x_mm=301.875,
        y_mm=0,
        w_mm=5.94,
        h_mm=6.429,
        anname='u1ad',
        layer=0,
        fill='Magenta',
    ))
    page0.add(TextFrame(
        x_mm=16.8913,
        y_mm=17.4,
        w_mm=65.2174,
        # h_mm: LINESP=27pt (IDML CSR Leading), LINESPMode=0. IDML <Br/> → Scribus <breakline>.
        # Vollkorn Black Italic line 2 may use larger auto-leading than Gotham Ultra.
        # Measured: Gotham line 2 fits in 22.0mm; Vollkorn gets clipped. Using 25.0mm.
        h_mm=25.0,
        anname='u1b0',
        layer=0,
        style='idml/normalparagraphstyle-27pt',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb')],
    ))
    page0.add(TextFrame(
        x_mm=16.8913,
        y_mm=41.6915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u1c7',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow Book'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow Book'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Lia vellam, conemporro modi\u2028tatque nii tectotmusa qui tota nis quam quis quae cum et arum vendellab voloriaspita dis quaturem. Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow Book'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Recum doluptae dolupissit porumquis dolut quamet faccae di aut fuga. Bit, unt quatem harum, offic te officit, que praturio eliquo maionsecto velis volut vollitatem ipitae comnim imodignatis estem quat.', font='Gotham Narrow Book', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
    ))
    page0.add(TextFrame(
        x_mm=115.8913,
        y_mm=17.4,
        w_mm=65.2174,
        # h_mm: LINESP=27pt (IDML CSR Leading), LINESPMode=0. IDML <Br/> → Scribus <breakline>.
        # Vollkorn Black Italic line 2 may use larger auto-leading. Using 25.0mm like u1b0.
        h_mm=25.0,
        anname='u1e6',
        layer=0,
        style='idml/normalparagraphstyle-27pt',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb')],
    ))
    page0.add(TextFrame(
        x_mm=115.8913,
        y_mm=41.6915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u1fd',
        layer=0,
        style='idml/aufzaehlungen-auf-gruenem-hintergrund',
        # Runs: each bullet is its own <para>, not a <breakline>-within-one-para.
        # This matches the original SLA structure: para separators between bullets so
        # FIRST=-13/INDENT=13 hanging indent applies independently to each bullet.
        # Tab chars use separator='tab' to emit <tab FEATURES="inherit"/> which
        # honours paragraph-style tab stops (5pt, 13pt).
        runs=[
            # Bullet 1
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='•', font='Gotham Narrow Book'),
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='Scim rem ', font='Gotham Narrow Black'),
            Run(text='utas si vellaccum eatus nullquae cum et arum vendellab iditatequi aut qui beat audit re.', font='Gotham Narrow Book'),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            # Bullet 2
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='•', font='Gotham Narrow Book'),
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='Tissi iuntem ressiti ', font='Gotham Narrow Black'),
            Run(text='orerovi tectotmusaqui tota nis quam.', font='Gotham Narrow Book'),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            # Bullet 3
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='•', font='Gotham Narrow Book'),
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='Uaerum ium ', font='Gotham Narrow Black'),
            Run(text='verior alicide liquuntio. ', font='Gotham Narrow Book'),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            # Bullet 4 (no double-blank after bullet 3 in original IDML)
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='•', font='Gotham Narrow Book'),
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='Ur, omniet ', font='Gotham Narrow Book'),
            Run(text='vello modi ', font='Gotham Narrow Black'),
            Run(text='aceprate pem ssi iuntem ilis', font='Gotham Narrow Book'),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            # Bullet 5
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='•', font='Gotham Narrow Book'),
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='Lia vellam, conemporro ', font='Gotham Narrow Book'),
            Run(text='moditatque', font='Gotham Narrow Black'),
            Run(text=' nimil maxim voluptur.', font='Gotham Narrow Book'),
            # Trailing: end of bullet 5, then tab-only para (from IDML Br/Content=tab/Br)
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
            Run(text='', font='Gotham Narrow Book', separator='tab'),
            Run(text='', has_itext=False, separator='para', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', paragraph_attrs={'LINESPMode': '1'}),
        ],
    ))
    page0.add(PolyLine(
        x_mm=123.5071,
        y_mm=127.9561,
        w_mm=48.9858,
        h_mm=59.48,
        sla_path='M74.32 89.74 C80.8 89.74 86.06 84.41 86.06 77.83 C86.06 71.26 80.8 65.93 74.32 65.93 C67.83 65.93 62.58 71.26 62.58 77.83 C62.58 84.41 67.83 89.74 74.32 89.74 Z M69.21 59.74 L60.47 47.63 L82.33 0 L92.74 1.684 L84.21 62.24 M92.97 81.45 L107.8 79.68 L138.9 121.9 L132.3 130.2 L83.51 93.36 M61.92 91.68 L55.98 105.4 L3.87 110.9 L0 101.1 L56.4 77.51 M68.49 97.5 L64.13 150.3 M80.22 98.93 L85.14 157.8 L96.9 157.8 L96.9 168.6 M76.14 157.8 L51.78 157.8 L51.78 168.6',
        line_color='Gelb',
        line_width_pt=4.203916263369494,
        anname='u2b0',
        layer=0,
    ))


def _add_page_1(doc: Document, page1) -> None:  # overrides task-3 stub
    """Auto-generated page-items for page 2 (Spread Spreads/Spread_u108.xml)."""
    page1.add(TextFrame(
        x_mm=16.8913,
        y_mm=17.4,
        w_mm=65.2174,
        # h_mm: LINESP=27pt (IDML CSR Leading), LINESPMode=0. IDML <Br/> → Scribus <breakline>.
        h_mm=22.0,
        anname='u24e',
        layer=0,
        style='idml/normalparagraphstyle-27pt',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='breakline'), Run(text='Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün')],
    ))
    page1.add(TextFrame(
        x_mm=16.8913,
        y_mm=41.6915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u265',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Lia vellam, conemporro modi\u2028Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
    ))
    page1.add(TextFrame(
        x_mm=115.3913,
        y_mm=47.9915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u295',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Recum doluptae dolupissit porumquis dolut quamet faccae di aut fuga. Bit, unt quatem harum, offic te officit, que praturio eliquo maionsecto velis volut vollitatem ipitae comnim imodignatis estem quat.', font='Gotham Narrow Book', fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='', has_itext=False, separator='para', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund'), Run(text='Recum doluptae dolupissit porumquis dolut quamet faccae di aut fuga. Bit, unt quatem harum, offic te officit, que praturio eliquo maionsecto velis volut vollitatem ipitae comnim imodignatis estem quat.', font='Gotham Narrow Book', fcolor='Dunkelgrün', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
    ))
    page1.add(ImageFrame(
        x_mm=99.1764,
        # y_mm=-0.01: Scribus 1.6.x silently drops image frames whose YPOS
        # equals the page PAGEYPOS exactly (an off-by-epsilon rendering bug).
        # A 0.01mm negative offset places the frame 0.003pt above the page
        # edge — imperceptible in print — and bypasses the Scribus bug.
        # IDML source: u2cd, y=0 on page 2.
        y_mm=-0.01,
        w_mm=99,
        h_mm=41.6915,
        anname='u2cd',
        layer=0,
        # Scribus cannot render CMYK JPEG directly; use ICC-converted sRGB PNG
        # without embedded iCCP chunk (Scribus 1.6.x rejects PNGs with iCCP).
        # Pre-cropped to the exact InDesign-visible region (source rows 578-1071,
        # cols 0-2381 of the 2598×1732 original), so LOCALX=0/LOCALY=0 from the
        # top-left of the crop shows exactly what InDesign's FrameFittingOption did.
        # LOCALSCX: scale to fit 240.72pt natural height → 118.18pt frame height.
        #   natural_h_pt = 1003px × (72/300) = 240.72pt
        #   LOCALSCX = frame_h_pt / natural_h_pt = 118.18 / 240.72 = 0.4909
        # SCALETYPE=0 ("Free Scaling") respects LOCALSCX and LOCALY.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/green-pine-trees-covered-with-fog-crop.png',
        scale_type=0,
        local_scale=(0.4909, 0.4909),
    ))
    page1.add(TextFrame(
        x_mm=110.5,
        y_mm=17.4,
        w_mm=75,
        # h_mm: LINESP=27pt (IDML CSR Leading), LINESPMode=0. IDML <Br/> → Scribus <breakline>.
        # Single paragraph; both lines share LINESP=27pt.
        h_mm=22.0,
        anname='u2d5',
        layer=0,
        style='idml/normalparagraphstyle-27pt',
        runs=[Run(text='Ich bin auch ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White')],
    ))
    page1.add(Polygon(
        x_mm=-17.3,
        y_mm=35.3915,
        w_mm=6.3,
        h_mm=6.3,
        anname='u2ef',
        layer=0,
        fill='Magenta',
    ))
    page1.add(Polygon(
        x_mm=-21.8,
        y_mm=41.6915,
        w_mm=6.3,
        h_mm=6.3,
        anname='u2f0',
        layer=0,
        fill='Magenta',
    ))
    page1.add(Polygon(
        x_mm=16.8913,
        y_mm=145.4968,
        w_mm=65.2174,
        h_mm=47.1032,
        anname='u346',
        layer=0,
        fill='Dunkelgrün',
    ))
    page1.add(TextFrame(
        x_mm=188,
        y_mm=139.2,
        # w_mm/h_mm: for rotated TextFrames Scribus uses the PRE-rotation width as
        # the text column width. IDML local frame: 151.37pt wide × 28.35pt tall,
        # rotated -90°. Converter currently emits post-rotation visual bbox (10×53.4mm),
        # swapping w/h so Scribus text-column width = 53.4mm (pre-rotation extent).
        # At 53.4mm column width, 'Impressum: xxxxxx' fits on one line at 6pt.
        # Without this fix Scribus wraps at 10mm → splits 'Impressum' mid-word.
        w_mm=53.4,
        h_mm=10,
        anname='u347',
        layer=0,
        rotation_deg=-90,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Impressum: xxxxxx', font='Gotham Narrow Book', fontsize=6, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle')],
    ))
    page1.add(TextFrame(
        x_mm=21.8196,
        y_mm=163.0167,
        w_mm=52.6804,
        # h_mm widened 23.2833mm→25.2236mm: IDML overset text (151 chars, ~5 lines
        # estimated at 11pt 0.40× ratio, leading=14.30pt; Scribus clips, InDesign
        # overflows silently). Baseline shows 5 lines; last line 're ped exceptatur?
        # Sed quia.' was missing in preview because 23.28mm only holds 4.62 lines.
        h_mm=25.2236,
        anname='u35f',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='Nequia volupti omnienthicipsa dem eossece atiati dollit odit ipientus et ut labora quis ducipiciis ex et hille ntiandi non re ped exceptatur? Sed quia.', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(TextFrame(
        x_mm=21.6413,
        y_mm=151.7968,
        w_mm=52.6804,
        # h_mm widened 7.6199mm→8.4667mm: IDML overset text (32 chars, ~2 lines
        # estimated at 12pt 0.40× ratio, leading=12.00pt; Scribus clips, InDesign
        # overflows silently). 'Kasten' (line 2 of 'Headline in einem grünen / Kasten')
        # was missing in preview because 7.62mm = 21.6pt holds only 1.8 lines at 12pt.
        h_mm=8.4667,
        anname='u376',
        layer=0,
        style='idml/headline-in-gruenem-kasten',
        runs=[Run(text='Headline in einem grünen Kasten ', font='Gotham Narrow Bold', paragraph_style='idml/headline-in-gruenem-kasten')],
    ))
    page1.add(Polygon(
        x_mm=-15.75,
        y_mm=186.3,
        w_mm=6.3,
        h_mm=6.3,
        anname='u394',
        layer=0,
        fill='Magenta',
    ))
    page1.add(Polygon(
        x_mm=-14.125,
        y_mm=145.4968,
        w_mm=6.3,
        h_mm=6.3,
        anname='u397',
        layer=0,
        fill='Magenta',
    ))
    page1.add(Polygon(
        x_mm=-14.4,
        y_mm=159.4167,
        w_mm=3.6,
        h_mm=3.6,
        anname='u398',
        layer=0,
        fill='Gelb',
    ))
    page1.add(ImageFrame(
        x_mm=198,
        y_mm=-0.1874,
        w_mm=99,
        h_mm=210.3748,
        anname='u3a0',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/plakat-dunkel-fuer-flyer.png',
        # SCALETYPE=1 (manual scale), aspect-FILL ("cover") mode.
        # Scribus 1.6 semantics:
        #   SCALETYPE=0 = ScaleAuto (auto-fits WITHIN frame; ignores LOCALSCX)
        #   SCALETYPE=1 = manual (LOCALSCX applied directly; treats image as 72dpi, 1px=1pt)
        # PNG is 3894×2598px; at 72dpi: natural_w=3894pt, natural_h=2598pt.
        # Frame: 99×210.3748mm = 280.63×596.34pt.
        # Fill (cover): scale to LARGEST axis ratio:
        #   sx = 280.63/3894 = 0.07207  (fills width, h=187.2pt << 596.34pt)
        #   sy = 596.34/2598 = 0.22954  (fills height, w=893.8pt >> 280.63pt)
        # s = 0.22954 → rendered 893.8×596.34pt; center horizontally:
        #   LOCALX = -(893.8-280.63)/2 = -306.60pt = -108.16mm
        scale_type=1,
        local_scale=(0.229538, 0.229538),
        local_offset_mm=(-108.1596, 0.0),
    ))
    page1.add(TextFrame(
        # x_mm corrected: IDML-derived x=203.88mm but baseline PDF renders "Ich" at
        # x0=592.3pt=208.93mm — 14.4pt=5.05mm difference. This gap is an InDesign↔IDML
        # rendering discrepancy (u3a1 Group transform not fully propagating to final
        # x in IDML export). Applying baseline-measured position.
        x_mm=208.93,
        y_mm=97.4809,
        w_mm=87.24,
        # h_mm: LINESP=20.48pt (IDML CSR Leading), LINESPMode=0, ALIGN=1 (CenterAlign in IDML).
        # IDML <Br/> → Scribus <breakline>: single paragraph. Para 1 wraps (87mm frame, 23pt).
        # Total 3 visual lines: if LINESP honored, baselines at 20.48, 40.96, 61.44pt.
        # Bottom ≈ 61.44 + 23 = 84.44pt = 29.8mm. If LINESP < fontsize=23 → auto ~23pt leading.
        # Total 3 lines at 23pt: bottom ≈ 3×23 = 69pt = 24.3mm. Using 26.0mm (73.70pt) ✓
        h_mm=26.0,
        anname='u3a2',
        layer=0,
        style='idml/normalparagraphstyle-20.48pt',
        runs=[Run(text='Ich bin ein Zitat. Ich bin ein prägnantes', font='Vollkorn Black Italic', fontsize=23, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='Zitat.', font='Vollkorn Black Italic', fontsize=23, fcolor='White')],
    ))
    page1.add(TextFrame(
        # x_mm corrected: baseline "Leonore" at x0=657.0pt=231.76mm (was 226.67mm).
        # Same +5.05mm InDesign↔IDML group-transform gap as u3a2.
        # h_mm widened 3.1044mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        x_mm=231.76,
        y_mm=123.1736,
        w_mm=41.6629,
        h_mm=5.0447,
        anname='u3ba',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Leonore Gewessler', font='Gotham Narrow Book', fontsize=11, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
        trail_attrs={'ALIGN': '1'},
    ))
    page1.add(Polygon(
        x_mm=241.2825,
        y_mm=83.8543,
        w_mm=12.4619,
        h_mm=9.9219,
        anname='u3d1',
        layer=0,
        fill='None',
        line_color='White',
        line_width_pt=0.75,
        # Path data sourced from reference SLA (local-pt coords, Gänsefüsschen shape).
        # Two closed Bezier sub-paths: left " and right " quotation mark symbols.
        custom_path=(
            "M20.175 28.125 C29.1 27.375 35.325 23.625 35.325 12.9 "
            "L35.325 0 L19.575 0 L19.575 16.125 L26.175 16.125 "
            "C26.025 19.35 23.775 21.525 18.9 22.275 L20.175 28.125 Z "
            "M1.275 28.125 C10.125 27.375 16.35 23.625 16.35 12.9 "
            "L16.35 0 L0.675 0 L0.675 16.125 L7.2 16.125 "
            "C7.125 19.35 4.8 21.525 0 22.275 L1.275 28.125 Z"
        ),
    ))
    page1.add(ImageFrame(
        x_mm=211.7191,
        y_mm=185.9694,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u3e7',
        layer=0,
        # social-media-icons-weiss.ai is a composite strip (526pt wide) rendered as a
        # single PNG by pdftocairo. InDesign uses the AI ArtBox coordinate space to
        # position each icon, but the IDML PDF-child tx offsets (-122, -100, -111pt)
        # all cluster within the first icon of the strip → Scribus shows the same
        # leftmost fragment for all 3 frames. Fix: use individually pre-cropped PNGs
        # (one per icon, 948×932px) scaled to fit the 3.35×3.3mm frame by height.
        # Scale = frame_h_pt / crop_h_pt = 9.351pt / 111.84pt ≈ 0.083615.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icon-u3e7-crop.png',
        local_scale=(0.083615, 0.083615),
    ))
    page1.add(TextFrame(
        x_mm=217.8791,
        y_mm=186.0667,
        w_mm=26.5209,
        # h_mm widened 3.1044mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        h_mm=5.0447,
        anname='u40c',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@diegruenen', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=211.7191,
        y_mm=191.61,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u3f0',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icon-u3f0-crop.png',
        local_scale=(0.083615, 0.083615),
    ))
    page1.add(TextFrame(
        x_mm=217.8791,
        y_mm=191.6586,
        w_mm=29.1209,
        # h_mm widened 3.2017mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        h_mm=5.0447,
        anname='u412',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@diegruenen', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=211.7191,
        y_mm=197.3258,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u3f5',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icon-u3f5-crop.png',
        local_scale=(0.083615, 0.083615),
    ))
    page1.add(TextFrame(
        x_mm=217.8791,
        y_mm=197.2992,
        w_mm=36.0209,
        # h_mm widened 3.3522mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        h_mm=5.0447,
        anname='u45b',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@diegruenenaustria', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=257.1,
        y_mm=185.9694,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u477',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/bluesky-weiss.png',
        local_scale=(0.091589, 0.091589),
    ))
    page1.add(TextFrame(
        x_mm=263.26,
        y_mm=186.0667,
        w_mm=26.4583,
        # h_mm widened 3.1044mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        h_mm=5.0447,
        anname='u47b',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@gruene.at', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=257.1,
        y_mm=191.61,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u4a2',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/website-weiss.png',
        local_scale=(0.095788, 0.095788),
        local_offset_mm=(-0.0774, -0.0774),
    ))
    page1.add(TextFrame(
        x_mm=263.26,
        y_mm=191.7073,
        w_mm=27.74,
        # h_mm widened 3.1044mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        h_mm=5.0447,
        anname='u4a6',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='gruene.at', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=257.1,
        y_mm=197.3258,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u4da',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/mail-weiss.png',
        local_scale=(0.095787, 0.095787),
        local_offset_mm=(-0.0672, -0.0626),
    ))
    page1.add(TextFrame(
        x_mm=263.26,
        y_mm=197.4231,
        w_mm=27.74,
        # h_mm widened 3.1044mm→5.0447mm: Scribus clips lines when frame_h < effective line height (leading=14.30pt; IDML overflows silently)
        h_mm=5.0447,
        anname='u4df',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='gruene.at', font='Gotham Narrow Book', paragraph_style='idml/absatzformat-1')],
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
