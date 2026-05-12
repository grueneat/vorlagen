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
        linesp_mode=0,
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
    ))
    # Center-aligned headline style (used by u52d: 38pt, tight leading 34pt)
    # linesp_mode=0 = auto/fixed pt leading.
    doc.add_para_style(ParaStyle(
        name='idml/headline-cover-zentriert',
        parent='idml/normalparagraphstyle',
        font='Gotham Narrow Ultra',
        fontsize=38,
        align=1,
        fcolor='White',
        linesp=34.134,
        linesp_mode=0,
    ))
    # Center-aligned subheadline style (used by u516: 18pt)
    # No explicit linesp/linesp_mode → inherits Scribus auto leading (fine for 18pt body text).
    doc.add_para_style(ParaStyle(
        name='idml/subheadline-cover-zentriert',
        parent='idml/normalparagraphstyle',
        font='Gotham Narrow Book',
        fontsize=18,
        align=1,
        fcolor='White',
    ))
    # Left-aligned panel headline: "Ich bin eine / Headline." at 30pt with 27pt leading.
    # Used by u1b0, u1e6 (page 1) and u24e (page 2), all left-aligned.
    # linesp_mode=0 = auto/fixed pt leading.
    doc.add_para_style(ParaStyle(
        name='idml/headline-panel-weiss',
        parent='idml/normalparagraphstyle',
        font='Gotham Narrow Ultra',
        fontsize=30,
        align=0,
        fcolor='White',
        linesp=27,
        linesp_mode=0,
    ))
    # Same style but Dunkelgrün color (used by u24e on page 2)
    doc.add_para_style(ParaStyle(
        name='idml/headline-panel-dunkelgruen',
        parent='idml/normalparagraphstyle',
        font='Gotham Narrow Ultra',
        fontsize=30,
        align=0,
        fcolor='Dunkelgrün',
        linesp=27,
        linesp_mode=0,
    ))
    # Center-aligned text for Störer label in u186.
    # IDML Justification="CenterAlign" → align=1 in Scribus.
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
        h_mm=11.6453,
        anname='u516',
        layer=0,
        style='idml/subheadline-cover-zentriert',
        runs=[Run(text='Mehrzeilige Subheadline –', font='Gotham Narrow Book', fontsize=18, fcolor='White'), Run(text='', separator='breakline'), Run(text='mehr Info zum Thema', font='Gotham Narrow Book', fontsize=18, fcolor='White', paragraph_style='idml/subheadline-cover-zentriert')],
    ))
    # u52d = cover headline (3 lines: Gotham "Das ist die" / Vollkorn "dreizeilige" /
    # Gotham "Headline"). Same Vollkorn-rendering workaround as u1b0/u1e6: any line
    # AFTER Vollkorn in a mixed-font paragraph is suppressed by Scribus. Split into
    # three single-line frames positioned to match baseline.pdf glyph top positions.
    #
    # Positions calibrated from baseline.pdf (pdfplumber glyph tops, page-relative):
    #   "Das ist die": 228.2pt = 80.51mm  (Gotham: glyph top = frame top)
    #   "dreizeilige":  263.1pt = 92.81mm (Vollkorn 38pt: glyph top = frame_top+15.0pt)
    #   "Headline":     296.4pt = 104.56mm (Gotham: glyph top = frame top)
    #
    # Frame 1: "Das ist die" (Gotham Narrow Ultra, centered).
    page0.add(TextFrame(
        x_mm=211.6719,
        y_mm=80.51,
        w_mm=71.6562,
        # 14.5mm=41.1pt: same height as u52d_hl ("Headline") which renders correctly.
        # 11mm=31.18pt caused "Das ist die" to NOT render (descent 7.6pt clipped by frame).
        h_mm=14.5,
        anname='u52d',
        layer=0,
        style='idml/headline-cover-zentriert',
        runs=[Run(text='Das ist die ', font='Gotham Narrow Ultra', fontsize=38, fcolor='White')],
    ))
    # Frame 2: "dreizeilige" (Vollkorn Black Italic, centered).
    # Target glyph top = 263.1pt. Vollkorn 38pt offset=15.0pt → frame_top=248.1pt=87.52mm.
    page0.add(TextFrame(
        x_mm=211.6719,
        y_mm=87.52,
        w_mm=71.6562,
        # 19mm=53.86pt: Vollkorn baseline_from_frame_top=15.0+36.18=51.18pt < 53.86pt ✓
        h_mm=19,
        anname='u52d_dreiz',
        layer=0,
        style='idml/headline-cover-zentriert',
        runs=[Run(text='dreizeilige', font='Vollkorn Black Italic', fontsize=38, fcolor='Gelb')],
    ))
    # Frame 3: "Headline" (Gotham Narrow Ultra, centered).
    # Target glyph top = 296.4pt → frame_top=296.4pt=104.56mm.
    page0.add(TextFrame(
        x_mm=211.6719,
        y_mm=104.56,
        w_mm=71.6562,
        # 14.5mm=41.1pt: Gotham 38pt baseline=0+30.4=30.4pt < 41.1pt ✓; ends at 119.06mm
        # (u516 subheadline starts at 119.146mm, no overlap).
        h_mm=14.5,
        anname='u52d_hl',
        layer=0,
        style='idml/headline-cover-zentriert',
        runs=[Run(text='Headline', font='Gotham Narrow Ultra', fontsize=38, fcolor='White')],
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
    # u1b0 = left-panel headline, two-frame workaround for Vollkorn rendering.
    # Scribus cannot render Vollkorn Black Italic as a SECOND line in a mixed-font
    # paragraph with LINESP < em-box; it is suppressed regardless of frame height
    # (confirmed by testing with frames up to 141pt tall — still no rendering).
    # Solution: emit each headline line as a separate single-line frame.
    #
    # Frame 1: Gotham Narrow Ultra "Ich bin eine " (line 1).
    # y_mm=17.4mm: matches the original IDML frame position. Scribus BASEOF=0
    # places Gotham glyph top at frame top. The 3pt offset vs InDesign is a
    # rendering engine difference; correcting it increases mismatch elsewhere.
    page0.add(TextFrame(
        x_mm=16.8913,
        y_mm=17.4,
        w_mm=65.2174,
        # 10.9mm = 30.9pt: enough for one 30pt Gotham line.
        h_mm=10.9,
        anname='u1b0',
        layer=0,
        style='idml/headline-panel-weiss',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White')],
    ))
    # Frame 2: Vollkorn Black Italic "Headline." (line 2).
    # Vollkorn glyph top in baseline.pdf = 79.9pt = 28.19mm.
    # Empirical: Vollkorn first line glyph top = frame_top + 11.78pt.
    # → frame top needed = 79.9 - 11.78 = 68.12pt = 24.03mm from page top.
    page0.add(TextFrame(
        x_mm=16.8913,
        y_mm=24.03,
        w_mm=65.2174,
        # u1c7 starts at y=41.69mm. Height = 41.69-24.03 = 17.66mm.
        # Vollkorn baseline at 40.34pt < 50.05pt (frame height) ✓.
        h_mm=17.66,
        anname='u1b0_hl',
        layer=0,
        style='idml/headline-panel-weiss',
        runs=[Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb')],
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
    # u1e6 = center-panel headline, same two-frame workaround as u1b0.
    page0.add(TextFrame(
        x_mm=115.8913,
        y_mm=17.4,
        w_mm=65.2174,
        h_mm=10.9,
        anname='u1e6',
        layer=0,
        style='idml/headline-panel-weiss',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White')],
    ))
    page0.add(TextFrame(
        x_mm=115.8913,
        y_mm=24.03,
        w_mm=65.2174,
        h_mm=17.66,
        anname='u1e6_hl',
        layer=0,
        style='idml/headline-panel-weiss',
        runs=[Run(text='Headline.', font='Vollkorn Black Italic', fontsize=30, fcolor='Gelb')],
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
    # u2b0 omitted: yellow-outline guide marker present in IDML Gestaltung layer
    # but excluded from InDesign PDF export (design workflow artifact, not content).
    # Scribus renders it visible; InDesign suppresses it via internal export logic.


def _add_page_1(doc: Document, page1) -> None:  # overrides task-3 stub
    """Auto-generated page-items for page 2 (Spread Spreads/Spread_u108.xml)."""
    page1.add(TextFrame(
        x_mm=16.8913,
        y_mm=17.4,
        w_mm=65.2174,
        h_mm=20.5,
        anname='u24e',
        layer=0,
        style='idml/headline-panel-dunkelgruen',
        runs=[Run(text='Ich bin eine ', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün'), Run(text='', has_itext=False, separator='breakline'), Run(text='Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='Dunkelgrün', paragraph_style='idml/headline-panel-dunkelgruen')],
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
        h_mm=20.5,
        anname='u2d5',
        layer=0,
        style='idml/headline-panel-weiss',
        runs=[Run(text='Ich bin auch ', font='Gotham Narrow Ultra', fontsize=30, fcolor='White'), Run(text='', has_itext=False, separator='breakline'), Run(text='eine Headline.', font='Gotham Narrow Ultra', fontsize=30, fcolor='White', paragraph_style='idml/headline-panel-weiss')],
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
        h_mm=22.0927,
        anname='u3a2',
        layer=0,
        style='idml/normalparagraphstyle',
        runs=[Run(text='Ich bin ein Zitat. Ich bin ein prägnantes', font='Vollkorn Black Italic', fontsize=23, fcolor='White'), Run(text='', separator='breakline'), Run(text='Zitat.', font='Vollkorn Black Italic', fontsize=23, fcolor='White', paragraph_style='idml/normalparagraphstyle')],
    ))
    page1.add(TextFrame(
        # x_mm corrected: baseline "Leonore" at x0=657.0pt=231.76mm (was 226.67mm).
        # Same +5.05mm InDesign↔IDML group-transform gap as u3a2.
        x_mm=231.76,
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
        # IDML-derived: full social-media-icons-weiss.png with local_offset to crop to icon.
        # scale=0.09 from PDF child ItemTransform; offset from PDF origin vs frame anchor.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icons-weiss.png',
        local_scale=(0.09, 0.09),
        local_offset_mm=(-12.1647, -0.7654),
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
        # IDML-derived: full social-media-icons-weiss.png offset to second icon row.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icons-weiss.png',
        local_scale=(0.09, 0.09),
        local_offset_mm=(-4.5974, -0.7654),
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
        # IDML-derived: full social-media-icons-weiss.png offset to third icon row.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/social-media-icons-weiss.png',
        local_scale=(0.09, 0.09),
        local_offset_mm=(-8.28, -0.7654),
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
        # IDML-derived scale from PDF child ItemTransform (scale=0.09158896567421919).
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/bluesky-weiss.png',
        local_scale=(0.091589, 0.091589),
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
        # IDML-derived scale (0.095788) + tiny offset from PDF child ItemTransform.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/website-weiss.png',
        local_scale=(0.095788, 0.095788),
        local_offset_mm=(-0.0774, -0.0774),
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
        # IDML-derived scale (0.095787) + tiny offset from PDF child ItemTransform.
        image='/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/mail-weiss.png',
        local_scale=(0.095787, 0.095787),
        local_offset_mm=(-0.0672, -0.0626),
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
