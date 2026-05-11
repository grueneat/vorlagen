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
    ))
    doc.add_para_style(ParaStyle(
        name='idml/aufzaehlungen-auf-gruenem-hintergrund',
        parent='idml/fliesstext-auf-gruenem-hintergrund',
        font='Gotham Narrow Book',
        fontsize=11,
        align=0,
        fcolor='White',
        linesp=14.3,
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
        h_mm=11.6453,
        anname='u516',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Mehrzeilige Subheadline –', font='Gotham Narrow Book', fontsize=18, fcolor='White'), Run(text='', separator='breakline'), Run(text='mehr Info zum Thema', font='Gotham Narrow Book', fontsize=18, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
    ))
    page0.add(TextFrame(
        x_mm=211.6719,
        y_mm=79.2087,
        w_mm=71.6562,
        h_mm=34.7873,
        anname='u52d',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Das ist die ', font='Gotham Narrow Ultra', fontsize=38, fcolor='White'), Run(text='', separator='breakline'), Run(text='dreizeilige', font='Vollkorn Black Italic', fontsize=38, fcolor='Gelb'), Run(text='', separator='breakline'), Run(text='Headline', font='Gotham Narrow Ultra', fontsize=38, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
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
        h_mm=17.9915,
        anname='u1b0',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', separator='breakline'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
    ))
    page0.add(TextFrame(
        x_mm=16.8913,
        y_mm=41.6915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u1c7',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow'), Run(text='', separator='breakline'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow'), Run(text='', separator='breakline'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='Lia vellam, conemporro modi\u2028tatque nii tectotmusa qui tota nis quam quis quae cum et arum vendellab voloriaspita dis quaturem. Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='Recum doluptae dolupissit porumquis dolut quamet faccae di aut fuga. Bit, unt quatem harum, offic te officit, que praturio eliquo maionsecto velis volut vollitatem ipitae comnim imodignatis estem quat.', font='Gotham Narrow', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
    ))
    page0.add(TextFrame(
        x_mm=115.8913,
        y_mm=17.4,
        w_mm=65.2174,
        h_mm=17.9915,
        anname='u1e6',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', separator='breakline'), Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
    ))
    page0.add(TextFrame(
        x_mm=115.8913,
        y_mm=41.6915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u1fd',
        layer=0,
        style='idml/aufzaehlungen-auf-gruenem-hintergrund',
        runs=[Run(text='\t•\t'), Run(text='Scim rem ', font='Black'), Run(text='utas si vellaccum eatus nullquae cum et arum vendellab iditatequi aut qui beat audit re.'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='\t•\t'), Run(text='Tissi iuntem ressiti ', font='Black'), Run(text='orerovi tectotmusaqui tota nis quam.'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='\t•\t'), Run(text='Uaerum ium ', font='Black'), Run(text='verior alicide liquuntio. '), Run(text='', separator='breakline'), Run(text='\t•\t'), Run(text='vello modi ', font='Black'), Run(text='aceprate pem ssi iuntem ilis'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='\t•\t'), Run(text='moditatque', font='Black'), Run(text=' nimil maxim voluptur.'), Run(text='', separator='breakline'), Run(text='\t'), Run(text='', separator='breakline'), Run(text='', paragraph_style='idml/aufzaehlungen-auf-gruenem-hintergrund', separator='para')],
    ))
    # u184 = Störer group: Magenta oval + "Störer" text overlay.
    # The oval is rotated -18° in IDML but since it's a circle, rotation is visual no-op.
    # Bounding box computed from IDML spread coords → page coords:
    #   oval x=270.42-290.32mm, y=64.53-84.42mm (≈19.9mm diameter circle)
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
        x_mm=269.81,
        y_mm=71.28,
        w_mm=21.11,
        h_mm=6.33,
        anname='u186',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Störer', font='Gotham Narrow Ultra', fontsize=11, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
    ))
    # u2b0 omitted: yellow-outline guide marker present in IDML Gestaltung layer
    # but excluded from InDesign PDF export (design workflow artifact, not content).
    # Scribus renders it visible; InDesign suppresses it via internal export logic.


def _add_page_1(doc: Document, page1) -> None:  # overrides task-3 stub
    """Auto-generated page-items for page 2 (Spread Spreads/Spread_u108.xml)."""
    page1.add(TextFrame(
        x_mm=16.8913,
        y_mm=17.4,
        w_mm=65.2174,
        h_mm=17.9915,
        anname='u24e',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün', paragraph_style='idml/normalparagraphstyle')],
    ))
    page1.add(TextFrame(
        x_mm=16.8913,
        y_mm=41.6915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u265',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='Lia vellam, conemporro modi\u2028Ur, omniet vello modi aceprate pem ssi ir, sit, quatenisto optatib eaquiate rumentios quo oditibust, quis et et quaturem. Et eaque volor, ipis eosenihicto consent. Nam quatur.', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund', separator='breakline')],
    ))
    page1.add(TextFrame(
        x_mm=115.3913,
        y_mm=47.9915,
        w_mm=65.2174,
        h_mm=150.9085,
        anname='u295',
        layer=0,
        style='idml/fliesstext-auf-gruenem-hintergrund',
        runs=[Run(text='Usapiene mporia quisin consequid que in et volor re doleceat laciisci nectur?', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='Tinvend igenis ute voloria qui cus ', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='et ut optate vendam ilis volorias\u2028pita dis at rem et molo ipsum fuga. Et eaque volor, ipis eos sinusae di que parmquas senihicto consent, ut qui doloruptam et volorro qui optate nis eaquamus.', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='Recum doluptae dolupissit porumquis dolut quamet faccae di aut fuga. Bit, unt quatem harum, offic te officit, que praturio eliquo maionsecto velis volut vollitatem ipitae comnim imodignatis estem quat.', font='Gotham Narrow', fcolor='Dunkelgrün'), Run(text='', separator='breakline'), Run(text='', separator='breakline'), Run(text='Recum doluptae dolupissit porumquis dolut quamet faccae di aut fuga. Bit, unt quatem harum, offic te officit, que praturio eliquo maionsecto velis volut vollitatem ipitae comnim imodignatis estem quat.', font='Gotham Narrow', fcolor='Dunkelgrün', paragraph_style='idml/fliesstext-auf-gruenem-hintergrund')],
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
        h_mm=17.9915,
        anname='u2d5',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin auch ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', separator='breakline'), Run(text='eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
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
        w_mm=10,
        h_mm=53.4,
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
        h_mm=23.2833,
        anname='u35f',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='Nequia volupti omnienthicipsa dem eossece atiati dollit odit ipientus et ut labora quis ducipiciis ex et hille ntiandi non re ped exceptatur? Sed quia.', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(TextFrame(
        x_mm=21.6413,
        y_mm=151.7968,
        w_mm=52.6804,
        h_mm=7.6199,
        anname='u376',
        layer=0,
        style='idml/headline-in-gruenem-kasten',
        runs=[Run(text='Headline in einem grünen Kasten ', font='Gotham Narrow', paragraph_style='idml/headline-in-gruenem-kasten')],
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
    ))
    page1.add(TextFrame(
        x_mm=203.88,
        y_mm=97.4809,
        w_mm=87.24,
        h_mm=22.0927,
        anname='u3a2',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin ein Zitat. Ich bin ein prägnantes', font='Vollkorn Black Italic', fontsize=23, fcolor='White'), Run(text='', separator='breakline'), Run(text='Zitat.', font='Vollkorn Black Italic', fontsize=23, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
    ))
    page1.add(TextFrame(
        x_mm=226.6686,
        y_mm=123.1736,
        w_mm=41.6629,
        h_mm=3.1044,
        anname='u3ba',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Leonore Gewessler', font='Gotham Narrow Book', fontsize=11, fcolor='Gelb', paragraph_style='idml/normalparagraphstyle')],
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
    ))
    page1.add(ImageFrame(
        x_mm=211.7191,
        y_mm=185.9694,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u3e7',
        layer=0,
        # Pre-cropped to show the correct icon region (Instagram icon, rows/cols from IDML).
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icon-u3e7-crop.png',
    ))
    page1.add(TextFrame(
        x_mm=217.8791,
        y_mm=186.0667,
        w_mm=26.5209,
        h_mm=3.1044,
        anname='u40c',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@diegruenen', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=211.7191,
        y_mm=191.61,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u3f0',
        layer=0,
        # Pre-cropped to show Facebook icon region from the multi-icon PNG.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icon-u3f0-crop.png',
    ))
    page1.add(TextFrame(
        x_mm=217.8791,
        y_mm=191.6586,
        w_mm=29.1209,
        h_mm=3.2017,
        anname='u412',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@diegruenen', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=211.7191,
        y_mm=197.3258,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u3f5',
        layer=0,
        # Pre-cropped to show TikTok icon region from the multi-icon PNG.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icon-u3f5-crop.png',
    ))
    page1.add(TextFrame(
        x_mm=217.8791,
        y_mm=197.2992,
        w_mm=36.0209,
        h_mm=3.3522,
        anname='u45b',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@diegruenenaustria', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=257.1,
        y_mm=185.9694,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u477',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/bluesky-weiss.png',
    ))
    page1.add(TextFrame(
        x_mm=263.26,
        y_mm=186.0667,
        w_mm=26.4583,
        h_mm=3.1044,
        anname='u47b',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='@gruene.at', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=257.1,
        y_mm=191.61,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u4a2',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/website-weiss.png',
    ))
    page1.add(TextFrame(
        x_mm=263.26,
        y_mm=191.7073,
        w_mm=27.74,
        h_mm=3.1044,
        anname='u4a6',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='gruene.at', paragraph_style='idml/absatzformat-1')],
    ))
    page1.add(ImageFrame(
        x_mm=257.1,
        y_mm=197.3258,
        w_mm=3.3526,
        h_mm=3.299,
        anname='u4da',
        layer=0,
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/mail-weiss.png',
    ))
    page1.add(TextFrame(
        x_mm=263.26,
        y_mm=197.4231,
        w_mm=27.74,
        h_mm=3.1044,
        anname='u4df',
        layer=0,
        style='idml/absatzformat-1',
        runs=[Run(text='gruene.at', paragraph_style='idml/absatzformat-1')],
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
