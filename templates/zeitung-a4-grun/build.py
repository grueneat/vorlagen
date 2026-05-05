# Auto-generated from gruene-zeitung-vorlage-original.sla by tools/sla_to_dsl.py.
# Hand-edit thereafter; this file is the source of truth.

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))

from sla_lib.builder import (  # noqa: E402
    Document, TextFrame, ImageFrame, Polygon, Run,
    DocumentLayer, ParaStyle, CharStyle, SoftShadow,
)

doc = Document(
    title='',
    template_id='zeitung-a4-grun',
    author='',
    facing_pages=True,
    column_gap_default_pt=12,
    deffont='Gotham Narrow Black',
    defsize=12,
    first_page_num=1,
    palette_replaces_ci=True,
    hcms=True,
    extra_doc_attrs={'ALAYER': '0', 'AUTOL': '100', 'BaseC': '#c0c0c0', 'CPICT': 'None', 'CSPICT': 'None', 'DCOL': '1', 'DGAP': '0', 'DIIm': '0', 'DISc': '1', 'DPIn': 'sRGB display profile (ICC v2.2)', 'DPIn2': 'sRGB display profile (ICC v2.2)', 'DPIn3': 'PSO Uncoated ISO12647 (ECI)', 'DPInCMYK': 'PSO Uncoated ISO12647 (ECI)', 'DPPr': 'PSO Uncoated ISO12647 (ECI)', 'DPSFo': '0', 'DPSo': '0', 'DPbla': '1', 'DPgam': '0', 'DPuse': '1', 'EmbeddedPath': '0', 'EndArrow': '0', 'FirstLineOffset': '1', 'GRAB': '4', 'GUIDELOCK': '0', 'GridType': '0', 'GuideC': '#000080', 'GuideRad': '9', 'HalfRes': '1', 'MAJGRID': '100.00062992126', 'MAJORC': '#00ff00', 'MINGRID': '20.0012598425197', 'MINORC': '#00ff00', 'PASPECT': '1', 'PICTSCX': '1', 'PICTSCY': '1', 'PICTSSHADE': '100', 'POLYC': '4', 'POLYCUR': '0', 'POLYF': '0.502045814642449', 'POLYIR': '0', 'POLYOCUR': '0', 'POLYR': '0', 'POLYS': '0', 'PRESET': '0', 'PSCALE': '1', 'SHOWBASE': '1', 'SHOWControl': '0', 'SHOWFRAME': '1', 'SHOWGRID': '0', 'SHOWGUIDES': '0', 'SHOWLAYERM': '0', 'SHOWLINK': '0', 'SHOWMARGIN': '0', 'SHOWPICT': '1', 'SUBJECT': '', 'SnapToElement': '0', 'SnapToGrid': '0', 'SnapToGuides': '0', 'StartArrow': '0', 'StrikeThruPos': '-1', 'StrikeThruWidth': '-1', 'StrokeText': 'Black', 'TabFill': '', 'TabWidth': '36', 'TextBackGround': 'None', 'TextBackGroundShade': '100', 'TextDistBottom': '0', 'TextDistLeft': '0', 'TextDistRight': '0', 'TextDistTop': '0', 'TextLineColor': 'None', 'TextLineShade': '100', 'TextPenShade': '100', 'TextStrokeShade': '100', 'UnderlinePos': '-1', 'UnderlineWidth': '-1', 'VHOCH': '33', 'VHOCHSC': '66', 'VKAPIT': '75', 'VTIEF': '33', 'VTIEFSC': '66', 'arcStartAngle': '30', 'arcSweepAngle': '300', 'calligraphicPenAngle': '0', 'calligraphicPenFillColor': 'Black', 'calligraphicPenFillColorShade': '100', 'calligraphicPenLineColor': 'Black', 'calligraphicPenLineColorShade': '100', 'calligraphicPenLineWidth': '1', 'calligraphicPenStyle': '1', 'calligraphicPenWidth': '10', 'constrain': '15', 'dispX': '10.0006299212598', 'dispY': '10.0006299212598', 'renderStack': '2 0 4 1 3', 'rulerMode': '1', 'rulerXoffset': '0', 'rulerYoffset': '0', 'showcolborders': '1', 'showrulers': '1', 'spiralEndAngle': '1080', 'spiralFactor': '1.2', 'spiralStartAngle': '0'},
    extra_pdf_attrs={'CMethod': '0', 'Clip': '0', 'Encrypt': '0', 'FontEmbedding': '0', 'ImageP': 'Adobe RGB (1998)', 'ImagePr': '0', 'InfoString': 'Grüne Zeitung Vorlage Scribus.sla', 'Intent': '1', 'Intent2': '0', 'PageLayout': '0', 'PassOwner': '', 'PassUser': '', 'Permissions': '-4', 'PresentMode': '0', 'PrintP': 'PSO Uncoated ISO12647 (ECI)', 'RGBMode': '0', 'RecalcPic': '1', 'RotateDeg': '0', 'SolidP': 'Adobe RGB (1998)', 'Thumbnails': '0', 'UseLayers': '0', 'UseLpi': '0', 'UseProfiles': '0', 'UseProfiles2': '1', 'UseSpotColors': '1', 'Version': '10', 'colorMarks': '0', 'displayBookmarks': '0', 'displayFullscreen': '0', 'displayLayers': '0', 'displayThumbs': '0', 'doMultiFile': '0', 'docInfoMarks': '0', 'firstUse': '0', 'fitWindow': '0', 'hideMenuBar': '0', 'hideToolBar': '0', 'openAfterExport': '0', 'rangeSel': '0', 'rangeTxt': '', 'registrationMarks': '0'},
    layers=[
        DocumentLayer(name='Ebene 1', visible=True, printable=True, editable=True, flow=False, transparent=1, blend=0, outline=False, layer_color='#000000'),
    ],
)

doc.add_color('Black', cmyk=(0, 0, 0, 100))
doc.add_color('Dunkelgrün', cmyk=(85, 35, 95, 10))
doc.add_color('Gelb', cmyk=(0, 0, 100, 0))
doc.add_color('Green', rgb=(0, 255, 0))
doc.add_color('Hellgrün', cmyk=(69, 0, 100, 0))
doc.add_color('Magenta', cmyk=(0, 100, 0, 0))
doc.add_color('Registration', cmyk=(100, 100, 100, 100), register=True)
doc.add_color('White', cmyk=(0, 0, 0, 0))

doc.add_char_style(CharStyle(name='Default Character Style', font='Gotham Narrow Book', fcolor='Black', fontfeatures='-clig', features='inherit', language='de', scolor='Black', bgcolor='None', fontsize=12, kern=0, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, fshade=100, hyph_word_min=3, sshade=100, bgshade=100, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1, scaleh=100, scalev=100, baseline_offset=0, is_default=True))
doc.add_para_style(ParaStyle(name='Default Paragraph Style', font='Gotham Narrow Book', bcolor='None', fontfeatures='-clig', bullet='0', linesp=15, space_before_pt=0, space_after_pt=5, first_indent_pt=0, left_indent_pt=0, right_indent_pt=0, paragraph_effect_offset=0, align=0, linesp_mode=0, drop_lines=2, hyph_consecutive_lines=2, direction=0, bshade=100, numeration=0, drop_cap=False, is_default=True))
doc.add_para_style(ParaStyle(name='[No paragraph style]', font='Gotham Narrow Book', fcolor='Black', features='inherit', parent='Default Paragraph Style', fontsize=12, space_before_pt=0, space_after_pt=0, first_indent_pt=0, left_indent_pt=0, right_indent_pt=0, txt_underline_pos=-0.1, txt_strike_pos=-0.1, align=0, linesp_mode=1, drop_lines=0, baseline_offset=0, drop_cap=False))
doc.add_para_style(ParaStyle(name='Titelseite Header', font='Gotham Narrow Ultra', fcolor='Gelb', language='de', fontfeatures='-clig', features='', fontsize=55, linesp=46, space_before_pt=5, space_after_pt=5, min_word_track=1, kern=1, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, align=1, linesp_mode=2, scalev=100, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1, keep_together=False))
doc.add_para_style(ParaStyle(name='Monat/Ausgabe', font='Gotham Narrow Black', fcolor='White', language='de', fontfeatures='-clig', fontsize=13, kern=0, linesp_mode=2))
doc.add_para_style(ParaStyle(name='Zustellerhinweis (Post)', font='Gotham Narrow Book', fcolor='Black', language='de', fontfeatures='-clig', fontsize=6, align=0, linesp_mode=2, fshade=100))
doc.add_para_style(ParaStyle(name='Impressum', font='Gotham Narrow Book', fcolor='White', language='de', fontfeatures='-clig', fontsize=8, linesp=9))
doc.add_para_style(ParaStyle(name='Copyright', font='Gotham Narrow Book', language='de', fontfeatures='-clig', fontsize=5.5))
doc.add_para_style(ParaStyle(name='Seitenzahl', font='Gotham Narrow Black', fcolor='Dunkelgrün', fontfeatures='-clig'))
doc.add_para_style(ParaStyle(name='Fließtext ', space_after_pt=0, min_word_track=1, min_glyph_shrink=0.95, max_glyph_extend=1, align=3, linesp_mode=2, hyph_consecutive_lines=3, hyph_word_min=3, keep_lines_start=0, direction=0, keep_together=False))
doc.add_para_style(ParaStyle(name='Schrift Störer  ', font='Gotham Narrow Ultra', fcolor='White', fontfeatures='-clig', fontsize=19, linesp=13, space_before_pt=0, align=1))
doc.add_para_style(ParaStyle(name='Inhaltsheadline Titelseite', font='Gotham Narrow Ultra', fcolor='White', fontfeatures='-clig', linesp=11, space_before_pt=0, space_after_pt=0, linesp_mode=2))
doc.add_para_style(ParaStyle(name='Überschrift weiß', font='Gotham Narrow Ultra', fcolor='White', language='de', fontfeatures='-clig', fontsize=40, space_after_pt=0, linesp_mode=2))
doc.add_para_style(ParaStyle(name='Überschrift Dunkelgrün', font='Gotham Narrow Ultra', fcolor='Dunkelgrün', language='de', fontfeatures='-clig', fontsize=40, linesp=35, space_after_pt=0, linesp_mode=0))
doc.add_para_style(ParaStyle(name='Bildunterschrift weiß', font='Gotham Narrow Book', fcolor='White', language='de', fontfeatures='-clig', fontsize=10, linesp=12))
doc.add_para_style(ParaStyle(name='Fließtext weiß', font='Gotham Narrow Book', fcolor='White', language='de', fontfeatures='-clig', space_after_pt=0, min_word_track=1, min_glyph_shrink=0.95, align=3, linesp_mode=2))
doc.add_para_style(ParaStyle(name='Fließtext in grünem Kasten', fcolor='White', language='de', fontsize=11, min_word_track=1, min_glyph_shrink=0.95, align=3, linesp_mode=1))
doc.add_para_style(ParaStyle(name='Headline in grünem Kasten', font='Gotham Narrow Bold', fcolor='White', language='de', fontfeatures='-clig', space_after_pt=0, align=1, linesp_mode=2))
doc.add_para_style(ParaStyle(name='Zwischenüberschrift', font='Gotham Narrow Bold', fcolor='Dunkelgrün', language='de', fontfeatures='-clig', space_before_pt=11.34, space_after_pt=0, linesp_mode=2))
doc.add_para_style(ParaStyle(name='Einleitungstext', font='Gotham Narrow Black', fontfeatures='-clig', parent='Zwischenüberschrift'))
doc.add_para_style(ParaStyle(name='Zwischenüberschrift weiß', font='Gotham Narrow Black', fcolor='White', fontfeatures='-clig', parent='Zwischenüberschrift'))
doc.add_para_style(ParaStyle(name='Zitat weißer Text', font='Vollkorn Black Italic', fcolor='White', language='de', fontfeatures='-clig', fontsize=14, align=1))
doc.add_para_style(ParaStyle(name='Zitat grüner Text', fcolor='Dunkelgrün', parent='Zitat weißer Text'))
doc.add_para_style(ParaStyle(name='NormalParagraphStyle', font='Gotham Narrow Black', features='inherit', linesp_mode=1))

doc.add_master(
    name='Neue Musterseite rechts',
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    facing='right',
)
doc.add_master(
    name='Neue Musterseite links',
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    facing='left',
)

page0 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite rechts',
)
page1 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page2 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite rechts',
)
page3 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page4 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite rechts',
)
page5 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page6 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page7 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite rechts',
)
page8 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page9 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page10 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page11 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page12 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)
page13 = doc.add_page(
    size=(210, 297),
    bleed_mm=3,
    margins_mm=(21, 21, 21, 21),
    master='Neue Musterseite links',
)

page0.add(ImageFrame(
    x_mm=0,
    y_mm=0,
    w_mm=210,
    h_mm=155.566972,
    layer=0,
    image='',
    line_width_pt=1,
))

page0.add(Polygon(
    x_mm=216.413539,
    y_mm=155.566972,
    w_mm=148.602369,
    h_mm=220.489286,
    layer=0,
    rotation_deg=90,
    anname='u2950',
    custom_path='M0 0 L0 625.009 L421.235 625.009 L421.235 0 L0 0 Z',
    fill_rule=0,
    fill='Dunkelgrün',
))

page0.add(TextFrame(
    x_mm=26,
    y_mm=179.819127,
    w_mm=158,
    h_mm=41.766984,
    layer=0,
    anname='u2989',
    custom_path='M0 0 L0 118.395 L447.874 118.395 L447.874 0 L0 0 Z',
    fill_rule=0,
    trail_style='Titelseite Header',
    text_align=1,
    col_gap_mm=1.357825,
    runs=[
        Run(text='Zeitungs', separator='para', paragraph_style='Titelseite Header'),
        Run(text='name'),
    ],
))

page0.add(TextFrame(
    x_mm=77.875,
    y_mm=224.573358,
    w_mm=54.25,
    h_mm=24.700917,
    layer=0,
    anname='u29b9',
    custom_path='M0 0 L0 70.0188 L153.779 70.0188 L153.779 0 L0 0 Z',
    fill_rule=0,
    trail_style='Fließtext ',
    trail_attrs={'ALIGN': '0'},
    col_gap_mm=4.233333,
    runs=[
        Run(text='Hier steht eine erste', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Inhaltsheadline', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius', fcolor='White', fshade=100),
    ],
))

page0.add(Polygon(
    x_mm=164.827502,
    y_mm=186.969049,
    w_mm=36.198843,
    h_mm=34.601351,
    layer=0,
    fill='Magenta',
    line_color='Magenta',
    line_width_pt=1,
    shape='ellipse',
))

page0.add(TextFrame(
    x_mm=166.189395,
    y_mm=195.995622,
    w_mm=31.905403,
    h_mm=24.779996,
    layer=0,
    rotation_deg=355,
    line_width_pt=1,
    col_gap_mm=0,
    runs=[
        Run(text='Hier', separator='para', paragraph_style='Schrift Störer  '),
        Run(text='steht ein', separator='para', paragraph_style='Schrift Störer  '),
        Run(text='Störer.', separator='para', paragraph_style='Schrift Störer  '),
    ],
))

page0.add(ImageFrame(
    x_mm=86.1,
    y_mm=138.199949,
    w_mm=37.8,
    h_mm=37.8,
    layer=0,
    image='assets/frame_01.png',
    line_width_pt=1,
    local_scale=(0.043878, 0.043878),
))

page0.add(TextFrame(
    x_mm=199.472222,
    y_mm=293.607761,
    w_mm=102.998165,
    h_mm=8.222917,
    layer=0,
    rotation_deg=270,
    line_width_pt=1,
    col_gap_mm=0,
    runs=[
        Run(text='zugestellt durch: ÖSTERREICHISCHE POST AG ', fcolor='White', fshade=50, separator='para', paragraph_style='Zustellerhinweis (Post)'),
    ],
))

page0.add(TextFrame(
    x_mm=19.75,
    y_mm=225,
    w_mm=54.25,
    h_mm=24.507303,
    layer=0,
    anname='u14c',
    custom_path='M0 0 L0 69.4696 L153.78 69.4696 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Hier steht eine erste', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Inhaltsheadline', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß', paragraph_attrs={'ALIGN': '0'}),
    ],
))

page0.add(TextFrame(
    x_mm=136,
    y_mm=224.573358,
    w_mm=54.25,
    h_mm=25.633028,
    layer=0,
    anname='u1c1',
    custom_path='M0 0 L0 72.6606 L153.78 72.6606 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Hier steht eine erste', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Inhaltsheadline', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', fcolor='White', fshade=100, separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '0'}),
    ],
))

page0.add(TextFrame(
    x_mm=19.75,
    y_mm=252.303633,
    w_mm=54.25,
    h_mm=23.536315,
    layer=0,
    anname='u165',
    custom_path='M0 0 L0 66.7172 L153.78 66.7172 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Hier steht eine erste', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Inhaltsheadline', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', fcolor='White', fshade=100, separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '0'}),
    ],
))

page0.add(TextFrame(
    x_mm=77.875,
    y_mm=251.837578,
    w_mm=54.25,
    h_mm=24.00237,
    layer=0,
    anname='u1aa',
    custom_path='M0 0 L0 68.0383 L153.78 68.0383 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Hier steht eine erste', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Inhaltsheadline', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', fcolor='White', fshade=100, separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '0'}),
    ],
))

page0.add(TextFrame(
    x_mm=136,
    y_mm=251.60455,
    w_mm=54.25,
    h_mm=24.235398,
    layer=0,
    anname='u1d9',
    custom_path='M0 0 L0 68.6988 L153.78 68.6988 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Hier steht eine erste', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Inhaltsheadline', separator='para', paragraph_style='Inhaltsheadline Titelseite', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', fcolor='White', fshade=100, separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '0'}),
    ],
))

page0.add(TextFrame(
    x_mm=163.164227,
    y_mm=7.744484,
    w_mm=38.682569,
    h_mm=12.117431,
    layer=0,
    line_width_pt=1,
    trail_style='Monat/Ausgabe',
    col_gap_mm=0,
    runs=[
        Run(text='Ausgabe 03/26'),
    ],
))

page1.add(ImageFrame(
    x_mm=0,
    y_mm=0,
    w_mm=210,
    h_mm=130.207312,
    layer=0,
    custom_path='M0 0 L0 369.092 L595.275 369.092 L595.275 0 L0 0 Z',
    fill_rule=0,
    image='',
))

page1.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

_chain1_0 = TextFrame(
    x_mm=20,
    y_mm=130.75,
    w_mm=54.666,
    h_mm=146.25,
    layer=0,
    anname='Kopie von u2f23',
    custom_path='M0 0 L0 414.565 L154.958 414.565 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur aliandaeptas es re iliaes dolupta Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. ', fontsize=12, separator='para', paragraph_style='Einleitungstext'),
        Run(text='Rio beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sum quodicimodit duciend uciandant, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt ut ulpa plique pero to este vel estem volum quatiisque autae. Elictus reic to cullandi dolorem quis erspit volore eatument quis acest, sit, nulliqu isimet quaeper itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpa dolor aut lamusciis ideles atatem quodiatet qui consedi temqui il ex et reiusaectem qui nem et doluptata illa pratur moluptatia sande dolo temolor esseque comnihi litios re is modignis ad essi quo excepero voluptatur simus, net dollaci accatem oluptas di ad quatum quatium as vit as enem sam, imendi quatus etus nam sam quiam, as prae niaturiorro opta senis voluptas quae dolorum quis andi doloritatet paritati dunto bearchil ma num faceria erspern amenihilla dite abo. Ipiendiam qui berum nos aut quiation et et de volorpo ssequo culles cone etur sim ut utescimendi as idem aute re prerum natet, sin pos dolum est, ius, test endi coribus et voluptat.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto ad essi quo excepero voluptatur simus, net dollaci accate im audam adist ratius, sitatur?', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas quae dolorum quis andi doloritatet paritati ecullitatem hillendi nonsed magnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari arum volupis dolent mosapie nduciliant apid qui odis ilit, sant sus mindaes verum,  ad essi quo excepero voluptatur simus, net dollaci accatecusciditibus abo. Nam unt aut ab id mi, omnimin esti senis voluptas quae dolorum quis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=12),
        Run(text=' nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
    ],
)
page1.add(_chain1_0)

_chain1_1 = TextFrame(
    x_mm=77.671696,
    y_mm=130.75,
    w_mm=54.666,
    h_mm=146.25,
    layer=0,
    anname='Kopie von u2f23 (2)',
    custom_path='M0 0 L0 414.565 L154.958 414.565 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page1.add(_chain1_1)

_chain1_2 = TextFrame(
    x_mm=135.343393,
    y_mm=130.75,
    w_mm=54.666,
    h_mm=146.25,
    layer=0,
    anname='Kopie von u2f23 (3)',
    custom_path='M0 0 L0 414.565 L154.958 414.565 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page1.add(_chain1_2)

page1.add(TextFrame(
    x_mm=20,
    y_mm=78.212817,
    w_mm=172.855945,
    h_mm=48.236697,
    layer=0,
    line_width_pt=1,
    trail_style='Überschrift weiß',
    col_gap_mm=0,
    runs=[
        Run(text='Eine Überschrift, die in einem Bild platziert wird - sie ist weiß'),
    ],
))

_chain0_0 = TextFrame(
    x_mm=20.001,
    y_mm=51.414651,
    w_mm=54.665896,
    h_mm=98.829412,
    layer=0,
    anname='u2d5c',
    custom_path='M0 0 L0 280.146 L154.958 280.146 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    trail_style='Fließtext ',
    col_gap_mm=4.233333,
    runs=[
        Run(text='Wir bleiben für Sie am Ball: ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Im Herbst haben wir uns mit Roman Gräbner, dem Hochwasserschutz-Verantwortlichen, intensiv über den Fortschritt der Renaturierung in Wöllersdorf informiert und ausgetauscht.', separator='para', paragraph_style='Fließtext '),
        Run(text='Warum ist uns dieses Projekt wichtig?', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Indem wir der Natur Raum geben, sich eigenständig zu entfalten, gewinnt die Uferzone in Wöllersdorf einen bedeutenden ökologischen Mehrwert. Diese Landschaft ist nicht nur ein Gewinn für die Artenvielfalt, sondern wertet auch unser Ortsbild maßgeblich auf und leistet einen wesentlichen Beitrag zum modernen Hochwasserschutz.', separator='para', paragraph_style='Fließtext '),
        Run(text='Da dieser Bereich zudem einer der wenigen freien Zugänge zum Wasser ist, hat das Projekt für unsere Gemeinde eine ganz besondere Bedeutung.', separator='para', paragraph_style='Fließtext '),
        Run(text='Wie geht es weiter?', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Gemeinsam mit dem Leiter der ökologischen Baubegleitung haben wir vereinbart, im Frühjahr eine weitere Begehung durchzuführen. Sobald die erste Wachstumsphase einsetzt, wird der natürliche Bewuchs evaluiert. Wo nötig, werden gezielte Ufer- und Böschungsbepflanzungen ergänzt, um die Stabilität und die biologische Vielfalt an der Piesting weiter zu fördern.', separator='para', paragraph_style='Fließtext '),
        Run(text='Wir halten Sie über die weitere Entwicklung natürlich auf dem Laufenden!', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta ', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
        Run(text='nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.'),
    ],
)
page2.add(_chain0_0)

_chain0_1 = TextFrame(
    x_mm=77.667,
    y_mm=51.414651,
    w_mm=54.665896,
    h_mm=98.829342,
    layer=0,
    anname='u2da1',
    custom_path='M0 0 L0 280.146 L154.958 280.146 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page2.add(_chain0_1)

_chain0_2 = TextFrame(
    x_mm=135.333,
    y_mm=51.414651,
    w_mm=54.665896,
    h_mm=98.829301,
    layer=0,
    anname='Kopie von u2da1',
    custom_path='M0 0 L0 280.146 L154.958 280.146 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page2.add(_chain0_2)

page2.add(TextFrame(
    x_mm=20.001,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Ohne Bild im Hintergrund sind Überschriften grün'),
    ],
))

page2.add(TextFrame(
    x_mm=195.482953,
    y_mm=285.108333,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (2)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page2.add(TextFrame(
    x_mm=19.295444,
    y_mm=157.558917,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Zwischen Überschrift und Text ist ein Abstand'),
    ],
))

_chain2_0 = TextFrame(
    x_mm=20.001,
    y_mm=190.3,
    w_mm=54.666,
    h_mm=86.7,
    layer=0,
    anname='Kopie von u2d5c',
    custom_path='M0 0 L0 245.764 L154.958 245.764 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta ', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes  ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus debis et odi quia dit ommolor epedit hilitis qui optatus..', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
        Run(text='', separator='para', paragraph_style='Fließtext '),
        Run(text='', separator='para', paragraph_style='Fließtext '),
    ],
)
page2.add(_chain2_0)

_chain2_1 = TextFrame(
    x_mm=77.667,
    y_mm=190.3,
    w_mm=54.666,
    h_mm=26.098138,
    layer=0,
    anname='Kopie von u2d5c (2)',
    custom_path='M0 0 L0 73.979 L154.958 73.979 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
)
page2.add(_chain2_1)

_chain2_2 = TextFrame(
    x_mm=135.333,
    y_mm=190.3,
    w_mm=54.666,
    h_mm=26.7,
    layer=0,
    anname='Kopie von u2d5c (3)',
    custom_path='M0 0 L0 75.6851 L154.958 75.6851 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
)
page2.add(_chain2_2)

page2.add(ImageFrame(
    x_mm=77.667,
    y_mm=219,
    w_mm=112.332,
    h_mm=58,
    layer=0,
    image='',
    line_width_pt=1,
))

page3.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (3)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

_chain3_0 = TextFrame(
    x_mm=20,
    y_mm=49.531174,
    w_mm=54.665739,
    h_mm=100.713016,
    layer=0,
    anname='Kopie von u2d5c (4)',
    custom_path='M0 0 L0 285.486 L154.958 285.486 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori debis et odi quia dit ommolor epedit hilitis qui optatus.', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
    ],
)
page3.add(_chain3_0)

_chain3_1 = TextFrame(
    x_mm=77.666,
    y_mm=49.531174,
    w_mm=54.665739,
    h_mm=100.712681,
    layer=0,
    anname='Kopie von u2da1 (2)',
    custom_path='M0 0 L0 285.485 L154.958 285.485 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page3.add(_chain3_1)

_chain3_2 = TextFrame(
    x_mm=135.332,
    y_mm=110.817413,
    w_mm=54.666,
    h_mm=39.426587,
    layer=0,
    anname='Kopie von u2da1 (3)',
    custom_path='M0 0 L0 111.76 L154.958 111.76 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page3.add(_chain3_2)

page3.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Überschriften können dunkelgrün sein'),
    ],
))

page3.add(ImageFrame(
    x_mm=135.332,
    y_mm=49.531174,
    w_mm=74.668,
    h_mm=58.158089,
    layer=0,
    image='',
    line_width_pt=1,
))

page3.add(TextFrame(
    x_mm=20,
    y_mm=153.5,
    w_mm=168.234111,
    h_mm=15.108239,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Oder nur einzeilig'),
    ],
))

page3.add(TextFrame(
    x_mm=20,
    y_mm=168.711111,
    w_mm=54.666,
    h_mm=108.954008,
    layer=0,
    anname='Kopie von u2d5c (5)',
    custom_path='M0 0 L0 308.847 L154.958 308.847 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vell', separator='para', paragraph_style='Fließtext '),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
    ],
))

page3.add(Polygon(
    x_mm=77.8,
    y_mm=175,
    w_mm=112.199914,
    h_mm=102.00005,
    layer=0,
    anname='u1529',
    custom_path='M0 0 L0 289.134 L318.047 289.134 L318.047 0 L0 0 Z',
    fill_rule=0,
    fill='Dunkelgrün',
))

page3.add(TextFrame(
    x_mm=86.399993,
    y_mm=197.961972,
    w_mm=94.999927,
    h_mm=73.320233,
    layer=0,
    anname='u152b',
    custom_path='M0 0 L0 207.837 L269.291 207.837 L269.291 0 L0 0 Z',
    fill_rule=0,
    columns=2,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Nequia volupti omnienthi-cipsa dem eossece atiati dollit oditius nonsequunt aspietGenti rerchil igendis santem assum verum qui re culparuntia nonsecab iuntioriost, temporum re periberum endit officil il id et faceatem quatusdanto con pero id quati quunt fuga. Ut inctotas corion reptatiis modit ditae ex excest mo beriost quam ad que senis est undus iunti doluptas re occus et ut oditat et voluptatecte por atis etur soluptur, id qui nost faccate culparum re aperum re sin nem necto ipitatat volut et moluptasimus num eatur ad eiuscil ignihil idus di nosanis unt fugia audis sam, cuptaqu issunto essinctem. Itae parum audae comni cumque pos poris dio ipit doles est, ulparibusam est alignis as ipientus et ut labora quis ducipiciis ex et hilluptam, corecullo to doluptas earum natem a idebite ntiandi non re ped exceptatur? Sed quia.', separator='para', paragraph_style='Fließtext in grünem Kasten'),
    ],
))

page3.add(TextFrame(
    x_mm=86.399993,
    y_mm=178.628422,
    w_mm=94.999927,
    h_mm=16.544954,
    layer=0,
    anname='u1544',
    custom_path='M0 0 L0 46.8991 L269.291 46.8991 L269.291 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Headline in einem grünen Kasten. Kann auch mehrzeilig sein, aber achte auf den Abstand ', separator='para', paragraph_style='Headline in grünem Kasten'),
        Run(text='zum Text.', separator='para', paragraph_style='Headline in grünem Kasten'),
    ],
))

page4.add(TextFrame(
    x_mm=195.482953,
    y_mm=285.108333,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (5)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page4.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.610527,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Bitte nur zweizeilige Headlines'),
    ],
))

_chain4_0 = TextFrame(
    x_mm=20,
    y_mm=49.298147,
    w_mm=54.666466,
    h_mm=136.554386,
    layer=0,
    anname='Kopie von u2d5c (6)',
    custom_path='M0 0 L0 387.083 L154.96 387.083 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    trail_style='Fließtext ',
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta ', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, c', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.'),
    ],
)
page4.add(_chain4_0)

_chain4_1 = TextFrame(
    x_mm=77.666767,
    y_mm=49.298147,
    w_mm=54.666466,
    h_mm=136.553932,
    layer=0,
    anname='Kopie von u2da1 (4)',
    custom_path='M0 0 L0 387.082 L154.96 387.082 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page4.add(_chain4_1)

_chain4_2 = TextFrame(
    x_mm=135.333534,
    y_mm=49.298147,
    w_mm=54.666466,
    h_mm=136.553932,
    layer=0,
    anname='Kopie von u2da1 (5)',
    custom_path='M0 0 L0 387.082 L154.96 387.082 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page4.add(_chain4_2)

page4.add(ImageFrame(
    x_mm=0,
    y_mm=188.881633,
    w_mm=210,
    h_mm=108.118367,
    layer=0,
    image='',
    line_width_pt=1,
))

page5.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (4)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page5.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Hier steht eine ziemlich lange Headline'),
    ],
))

_chain5_0 = TextFrame(
    x_mm=20.097222,
    y_mm=50.748258,
    w_mm=54.666466,
    h_mm=226.897604,
    layer=0,
    anname='Kopie von u2d5c (7)',
    custom_path='M0 0 L0 643.174 L154.96 643.174 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta ', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, c', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', separator='para', paragraph_style='Fließtext '),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
    ],
)
page5.add(_chain5_0)

_chain5_1 = TextFrame(
    x_mm=77.763989,
    y_mm=50.748258,
    w_mm=54.666466,
    h_mm=123.433384,
    layer=0,
    anname='Kopie von u2da1 (6)',
    custom_path='M0 0 L0 349.89 L154.96 349.89 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page5.add(_chain5_1)

_chain5_2 = TextFrame(
    x_mm=135.430756,
    y_mm=50.748258,
    w_mm=54.666466,
    h_mm=123.899439,
    layer=0,
    anname='Kopie von u2da1 (7)',
    custom_path='M0 0 L0 351.211 L154.96 351.211 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page5.add(_chain5_2)

page5.add(ImageFrame(
    x_mm=77.763989,
    y_mm=176.744945,
    w_mm=112.333233,
    h_mm=84.122936,
    layer=0,
    image='',
    line_width_pt=1,
))

page5.add(TextFrame(
    x_mm=77.763989,
    y_mm=263.705556,
    w_mm=112.333233,
    h_mm=14.645862,
    layer=0,
    line_width_pt=1,
    trail_style='Bildunterschrift weiß',
    col_gap_mm=0,
    runs=[
        Run(text='Wenn wir das Bild näher beschreiben wollen, können wir das machen. Falls der Text unter einem Bild auf weißem Hintergrund erscheinen soll, dann gerne in dunkelgrün.', fcolor='Dunkelgrün', fshade=100),
    ],
))

page6.add(TextFrame(
    x_mm=20,
    y_mm=37.161459,
    w_mm=54.665739,
    h_mm=127.466055,
    layer=0,
    anname='Kopie von u2d5c (8)',
    custom_path='M0 0 L0 361.321 L154.958 361.321 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=12, separator='para', paragraph_style='Fließtext '),
    ],
))

page6.add(Polygon(
    x_mm=77.5,
    y_mm=37.161459,
    w_mm=112.500128,
    h_mm=123.838373,
    layer=0,
    anname='u6ad',
    custom_path='M0 0 L0 351.038 L318.898 351.038 L318.898 0 L0 0 Z',
    fill_rule=0,
    fill='Dunkelgrün',
))

page6.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Aufzählungen? Check!'),
    ],
))

page6.add(TextFrame(
    x_mm=20,
    y_mm=172.55,
    w_mm=170.000128,
    h_mm=27.730725,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Die Beiträge sollten in 3 Spalten angelegt sein'),
    ],
))

_chain6_0 = TextFrame(
    x_mm=20,
    y_mm=205.174303,
    w_mm=54.666423,
    h_mm=73.636697,
    layer=0,
    anname='Kopie von u2d5c (10)',
    custom_path='M0 0 L0 208.734 L154.96 208.734 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011911,
    text_align=3,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext ', paragraph_attrs={'ALIGN': '3'}),
    ],
)
page6.add(_chain6_0)

_chain6_1 = TextFrame(
    x_mm=77.666722,
    y_mm=205.174303,
    w_mm=54.666423,
    h_mm=73.636452,
    layer=0,
    anname='Kopie von u2da1 (8)',
    custom_path='M0 0 L0 208.733 L154.96 208.733 L154.96 0 L0 0 Z',
    fill_rule=0,
    text_align=3,
    col_gap_mm=4.233333,
)
page6.add(_chain6_1)

_chain6_2 = TextFrame(
    x_mm=135.333444,
    y_mm=204.708248,
    w_mm=54.666684,
    h_mm=74.102613,
    layer=0,
    anname='Kopie von u2da1 (9)',
    custom_path='M0 0 L0 210.054 L154.96 210.054 L154.96 0 L0 0 Z',
    fill_rule=0,
    text_align=3,
    col_gap_mm=4.233333,
)
page6.add(_chain6_2)

page6.add(TextFrame(
    x_mm=86.25,
    y_mm=62.852513,
    w_mm=95,
    h_mm=94.147487,
    layer=0,
    anname='u6d0',
    custom_path='M0 0 L0 266.875 L269.291 266.875 L269.291 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Nequia volupti omnienthicipsa dem eossece atiati dollit oditius nonsequunt aspietGenti rerchil igendis santem assum.', separator='breakline'),
        Run(text='• verum qui re culparuntia nonsecab iuntioriost', separator='breakline'),
        Run(text='• temporum re periberum endit officil il id et faceatem    quatusdanto con ', separator='breakline'),
        Run(text='• pero id quati quunt fuga. Ut inctotas corion reptatiis modit ditae ex excest mo beriost quamad que senis est undus iunti doluptas re occus et ut oditat et voluptatecte por', separator='breakline'),
        Run(text='• atis etur soluptur, id qui nost faccate culparum re aperum re sin nem necto ipitatat volut et moluptasimus num ', separator='breakline'),
        Run(text='• eatur ad eiuscil ignihil idus di nosanis unt fugia audis sam, cuptaqu issunto essinctem. ', separator='para', paragraph_style='Fließtext in grünem Kasten'),
        Run(text='', separator='breakline'),
        Run(text='Itae pm est alignis as ipientus et ut labora quis ducipiciis ex et hilluptam, corecullo to doluptas earum natem a idebite ntiandi non re ped exceptatur? Sed quia.', separator='para', paragraph_style='Fließtext in grünem Kasten'),
    ],
))

page6.add(TextFrame(
    x_mm=86.25,
    y_mm=43,
    w_mm=95,
    h_mm=17.697239,
    layer=0,
    anname='u6e8',
    custom_path='M0 0 L0 50.1655 L269.291 50.1655 L269.291 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Grüne Kästen eignen sich hervorragend für Aufzählungen und Listen. Im Text unten sind die Tabulatoren schon eingestelt.', separator='para', paragraph_style='Headline in grünem Kasten'),
    ],
))

page6.add(TextFrame(
    x_mm=195.482953,
    y_mm=285.108333,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (8)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page7.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Personen können näher vorgestellt werden'),
    ],
))

_chain7_0 = TextFrame(
    x_mm=20.097222,
    y_mm=50.748258,
    w_mm=54.666444,
    h_mm=140.251742,
    layer=0,
    anname='Kopie von u2d5c (9)',
    custom_path='M0 0 L0 397.564 L154.96 397.564 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta ', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, c', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat ', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
    ],
)
page7.add(_chain7_0)

_chain7_1 = TextFrame(
    x_mm=77.763989,
    y_mm=50.748258,
    w_mm=54.666444,
    h_mm=139.493027,
    layer=0,
    anname='Kopie von u2da1 (10)',
    custom_path='M0 0 L0 395.413 L154.96 395.413 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page7.add(_chain7_1)

_chain7_2 = TextFrame(
    x_mm=135.430756,
    y_mm=50.748258,
    w_mm=54.666444,
    h_mm=139.726054,
    layer=0,
    anname='Kopie von u2da1 (11)',
    custom_path='M0 0 L0 396.074 L154.96 396.074 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page7.add(_chain7_2)

page7.add(Polygon(
    x_mm=20,
    y_mm=195,
    w_mm=170,
    h_mm=82,
    layer=0,
    anname='u918',
    custom_path='M0 0 L0 232.441 L481.89 232.441 L481.89 0 L0 0 Z',
    fill_rule=0,
    fill='Dunkelgrün',
))

page7.add(TextFrame(
    x_mm=44.013587,
    y_mm=199,
    w_mm=68.277064,
    h_mm=16.408257,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext in grünem Kasten',
    trail_attrs={'ALIGN': '1'},
    col_gap_mm=0,
    runs=[
        Run(text='Vorname Nachname', separator='para', paragraph_style='Headline in grünem Kasten'),
        Run(text='Funktion, Gemeinde'),
    ],
))

page7.add(TextFrame(
    x_mm=27.763889,
    y_mm=217.738532,
    w_mm=100.77646,
    h_mm=51.524975,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext in grünem Kasten',
    col_gap_mm=0,
    runs=[
        Run(text='Aianeptas es re iliaes dolupta Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, cEm aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quoEm aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quoEm aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quoEm aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quoEm aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quoEm aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autemvolorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.On porecae. Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?Gentorrum eum re re dusIum rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatemhillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.'),
    ],
))

page7.add(ImageFrame(
    x_mm=134.654085,
    y_mm=200.647222,
    w_mm=51.345915,
    h_mm=76.352778,
    layer=0,
    image='',
    line_width_pt=1,
))

page7.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (6)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page8.add(TextFrame(
    x_mm=20,
    y_mm=37.161459,
    w_mm=54.665739,
    h_mm=93.838541,
    layer=0,
    anname='Kopie von u2d5c (11)',
    custom_path='M0 0 L0 265.999 L154.958 265.999 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=12, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=12, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=12, separator='para', paragraph_style='Fließtext '),
    ],
))

page8.add(Polygon(
    x_mm=135.333444,
    y_mm=37.161459,
    w_mm=54.666684,
    h_mm=50.017807,
    layer=0,
    anname='Kopie von u6ad',
    custom_path='M0 0 L0 141.783 L154.961 141.783 L154.961 0 L0 0 Z',
    fill_rule=0,
    fill='Dunkelgrün',
))

page8.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Beitrag mit Zitat'),
    ],
))

page8.add(TextFrame(
    x_mm=20,
    y_mm=137.716233,
    w_mm=170.000128,
    h_mm=27.031193,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Ein weiterer Beitrag mit Zitat, aber anders'),
    ],
))

_chain8_0 = TextFrame(
    x_mm=20,
    y_mm=167.404587,
    w_mm=54.666423,
    h_mm=111.406413,
    layer=0,
    anname='Kopie von u2d5c (12)',
    custom_path='M0 0 L0 315.798 L154.96 315.798 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011911,
    trail_style='Fließtext ',
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
        Run(text='auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped...nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.'),
    ],
)
page8.add(_chain8_0)

_chain8_1 = TextFrame(
    x_mm=77.666722,
    y_mm=169.268807,
    w_mm=54.666423,
    h_mm=64.731193,
    layer=0,
    anname='Kopie von u2da1 (12)',
    custom_path='M0 0 L0 183.49 L154.96 183.49 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page8.add(_chain8_1)

_chain8_2 = TextFrame(
    x_mm=135.333444,
    y_mm=169,
    w_mm=54.666684,
    h_mm=109.810861,
    layer=0,
    anname='Kopie von u2da1 (13)',
    custom_path='M0 0 L0 311.274 L154.96 311.274 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page8.add(_chain8_2)

page8.add(TextFrame(
    x_mm=195.482953,
    y_mm=285.108333,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (9)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page8.add(TextFrame(
    x_mm=77.666767,
    y_mm=37.161459,
    w_mm=54.666466,
    h_mm=93.838541,
    layer=0,
    anname='Kopie von u2da1 (14)',
    custom_path='M0 0 L0 265.999 L154.96 265.999 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta ', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, c', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
    ],
))

page8.add(TextFrame(
    x_mm=135.333444,
    y_mm=91.466972,
    w_mm=54.666684,
    h_mm=39.533028,
    layer=0,
    anname='Kopie von u2da1 (15)',
    custom_path='M0 0 L0 112.062 L154.96 112.062 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
    ],
))

page8.add(TextFrame(
    x_mm=85.192594,
    y_mm=246.776351,
    w_mm=39.614679,
    h_mm=24.700917,
    layer=0,
    line_width_pt=1,
    trail_style='Zitat grüner Text',
    col_gap_mm=0,
    runs=[
        Run(text='Ich bin ein Zitat. Ich bin ein prägnantes Zitat.'),
    ],
))

page8.add(TextFrame(
    x_mm=82.27975,
    y_mm=272.558333,
    w_mm=45.440367,
    h_mm=4.844954,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext in grünem Kasten',
    trail_attrs={'ALIGN': '1'},
    col_gap_mm=0,
    runs=[
        Run(text='Leonore Gewessler', fcolor='Hellgrün', fshade=100),
    ],
))

page8.add(ImageFrame(
    x_mm=99.167605,
    y_mm=236.465112,
    w_mm=11.664657,
    h_mm=10.468221,
    layer=0,
    image='assets/frame_02.png',
    line_width_pt=1,
    local_scale=(0.027554, 0.027554),
))

page8.add(TextFrame(
    x_mm=142.859446,
    y_mm=51.69024,
    w_mm=39.614679,
    h_mm=24.700917,
    layer=0,
    line_width_pt=1,
    trail_style='Zitat weißer Text',
    col_gap_mm=0,
    runs=[
        Run(text='Ich bin ein Zitat. Ich bin ein prägnantes Zitat.'),
    ],
))

page8.add(TextFrame(
    x_mm=139.946602,
    y_mm=78.530556,
    w_mm=45.440367,
    h_mm=4.844954,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext in grünem Kasten',
    trail_attrs={'ALIGN': '1'},
    col_gap_mm=0,
    runs=[
        Run(text='Leonore Gewessler', fcolor='White', fshade=100),
    ],
))

page8.add(ImageFrame(
    x_mm=156.834286,
    y_mm=41.712684,
    w_mm=11.665,
    h_mm=9.7986,
    layer=0,
    image='assets/frame_03.png',
    line_width_pt=1,
    local_scale=(0.027555, 0.027555),
))

page9.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (7)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

_chain9_0 = TextFrame(
    x_mm=20,
    y_mm=49.531174,
    w_mm=54.665739,
    h_mm=122.281679,
    layer=0,
    anname='Kopie von u2d5c (13)',
    custom_path='M0 0 L0 346.626 L154.958 346.626 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', fontsize=11.7, separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', fontsize=11.7, separator='para', paragraph_style='Fließtext '),
    ],
)
page9.add(_chain9_0)

_chain9_1 = TextFrame(
    x_mm=77.666,
    y_mm=49.531174,
    w_mm=54.665739,
    h_mm=122.747734,
    layer=0,
    anname='Kopie von u2da1 (16)',
    custom_path='M0 0 L0 347.947 L154.958 347.947 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page9.add(_chain9_1)

_chain9_2 = TextFrame(
    x_mm=135.332,
    y_mm=49.240376,
    w_mm=54.666,
    h_mm=229.299083,
    layer=0,
    anname='Kopie von u2da1 (17)',
    custom_path='M0 0 L0 649.979 L154.958 649.979 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page9.add(_chain9_2)

page9.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=27.963305,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift Dunkelgrün',
    col_gap_mm=0,
    runs=[
        Run(text='Hier noch ein Beispiel, das alle Stücke spielt'),
    ],
))

page9.add(Polygon(
    x_mm=20,
    y_mm=175,
    w_mm=112.199914,
    h_mm=102.00005,
    layer=0,
    anname='Kopie von u1529',
    custom_path='M0 0 L0 289.134 L318.047 289.134 L318.047 0 L0 0 Z',
    fill_rule=0,
    fill='Dunkelgrün',
))

page9.add(TextFrame(
    x_mm=28.599993,
    y_mm=197.961972,
    w_mm=94.999927,
    h_mm=73.320233,
    layer=0,
    anname='Kopie von u152b',
    custom_path='M0 0 L0 207.837 L269.291 207.837 L269.291 0 L0 0 Z',
    fill_rule=0,
    columns=2,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Nequia volupti omnienthi-cipsa dem eossece atiati dollit oditius nonsequunt aspietGenti rerchil igendis santem assum verum qui re culparuntia nonsecab iuntioriost, temporum re periberum endit officil il id et faceatem quatusdanto con pero id quati quunt fuga. Ut inctotas corion reptatiis modit ditae ex excest mo beriost quam ad que senis est undus iunti doluptas re occus et ut oditat et voluptatecte por atis etur soluptur, id qui nost faccate culparum re aperum re sin nem necto ipitatat volut et moluptasimus num eatur ad eiuscil ignihil idus di nosanis unt fugia audis sam, cuptaqu issunto essinctem. Itae parum audae comni cumque pos poris dio ipit doles est, ulparibusam est alignis as ipientus et ut labora quis ducipiciis ex et hilluptam, corecullo to doluptas earum natem a idebite ntiandi non re ped exceptatur? Sed quia.', fontsize=11, separator='para', paragraph_style='Fließtext in grünem Kasten'),
    ],
))

page9.add(TextFrame(
    x_mm=28.599993,
    y_mm=178.628422,
    w_mm=94.999927,
    h_mm=16.544954,
    layer=0,
    anname='Kopie von u1544',
    custom_path='M0 0 L0 46.8991 L269.291 46.8991 L269.291 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Headline in einem grünen Kasten. Kann auch mehrzeilig sein, aber achte auf den Abstand ', fontsize=12, separator='para', paragraph_style='Headline in grünem Kasten'),
        Run(text='zum Text.', fontsize=12, separator='para', paragraph_style='Headline in grünem Kasten'),
    ],
))

page9.add(ImageFrame(
    x_mm=210,
    y_mm=0,
    w_mm=210,
    h_mm=126.139459,
    layer=0,
    image='',
    line_width_pt=1,
))

_chain10_0 = TextFrame(
    x_mm=20,
    y_mm=133.363312,
    w_mm=54.666423,
    h_mm=62.636688,
    layer=0,
    anname='Kopie von u2d5c (14)',
    custom_path='M0 0 L0 177.553 L154.96 177.553 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011911,
    trail_style='Fließtext ',
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
        Run(text='auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped...'),
    ],
)
page10.add(_chain10_0)

_chain10_1 = TextFrame(
    x_mm=77.666722,
    y_mm=132.198174,
    w_mm=54.666423,
    h_mm=146.801826,
    layer=0,
    anname='Kopie von u2da1 (18)',
    custom_path='M0 0 L0 416.131 L154.96 416.131 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page10.add(_chain10_1)

_chain10_2 = TextFrame(
    x_mm=135.333444,
    y_mm=132,
    w_mm=54.666684,
    h_mm=59,
    layer=0,
    anname='Kopie von u2da1 (19)',
    custom_path='M0 0 L0 167.244 L154.96 167.244 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page10.add(_chain10_2)

page10.add(TextFrame(
    x_mm=20,
    y_mm=242.65322,
    w_mm=54.666423,
    h_mm=36.602335,
    layer=0,
    anname='Kopie von u2d5c (15)',
    custom_path='M0 0 L0 103.755 L154.96 103.755 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011911,
    trail_style='Fließtext ',
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext '),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext '),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext '),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext '),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext '),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext '),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext '),
        Run(text='auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext '),
        Run(text='Magnatet, as erfero cum que maximintem est exped...'),
    ],
))

page10.add(ImageFrame(
    x_mm=143.411908,
    y_mm=202.572486,
    w_mm=66.588092,
    h_mm=94.427514,
    layer=0,
    image='',
    line_width_pt=1,
))

page10.add(TextFrame(
    x_mm=27.525872,
    y_mm=209.029128,
    w_mm=39.614679,
    h_mm=24.700917,
    layer=0,
    line_width_pt=1,
    trail_style='Zitat grüner Text',
    col_gap_mm=0,
    runs=[
        Run(text='Ich bin ein Zitat. Ich bin ein prägnantes Zitat.'),
    ],
))

page10.add(TextFrame(
    x_mm=24.613028,
    y_mm=235.516667,
    w_mm=45.440367,
    h_mm=4.844954,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext in grünem Kasten',
    trail_attrs={'ALIGN': '1'},
    col_gap_mm=0,
    runs=[
        Run(text='Leonore Gewessler', fcolor='Hellgrün', fshade=100),
    ],
))

page10.add(ImageFrame(
    x_mm=41.500883,
    y_mm=198.71789,
    w_mm=11.664657,
    h_mm=10.468221,
    layer=0,
    image='assets/frame_04.png',
    line_width_pt=1,
    local_scale=(0.027554, 0.027554),
))

page11.add(ImageFrame(
    x_mm=0,
    y_mm=-0.180716,
    w_mm=210.799064,
    h_mm=213.919266,
    layer=0,
    image='',
    fill='Dunkelgrün',
    line_width_pt=1,
))

page11.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (10)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

_chain11_0 = TextFrame(
    x_mm=20,
    y_mm=49.531174,
    w_mm=54.665739,
    h_mm=155.585358,
    layer=0,
    anname='Kopie von u2d5c (16)',
    custom_path='M0 0 L0 441.03 L154.958 441.03 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori ', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Haribusam alit quo', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext weiß'),
    ],
)
page11.add(_chain11_0)

_chain11_1 = TextFrame(
    x_mm=77.666,
    y_mm=49.531174,
    w_mm=54.665739,
    h_mm=155.119303,
    layer=0,
    anname='Kopie von u2da1 (20)',
    custom_path='M0 0 L0 439.709 L154.958 439.709 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page11.add(_chain11_1)

_chain11_2 = TextFrame(
    x_mm=135.332,
    y_mm=49.240376,
    w_mm=54.666,
    h_mm=154.244963,
    layer=0,
    anname='Kopie von u2da1 (21)',
    custom_path='M0 0 L0 437.228 L154.958 437.228 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page11.add(_chain11_2)

page11.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=35.279835,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift weiß',
    col_gap_mm=0,
    runs=[
        Run(text='Weiße Headlines auf grünem Hintergrund'),
    ],
))

page11.add(ImageFrame(
    x_mm=0,
    y_mm=213.73855,
    w_mm=210,
    h_mm=83.26145,
    layer=0,
    image='',
    line_width_pt=1,
))

page11.add(ImageFrame(
    x_mm=210,
    y_mm=-0.180716,
    w_mm=210.799064,
    h_mm=297.180716,
    layer=0,
    image='',
    fill='Dunkelgrün',
    line_width_pt=1,
    local_offset_mm=(0.330311, -0.325716),
))

_chain12_0 = TextFrame(
    x_mm=20,
    y_mm=37.802771,
    w_mm=54.665739,
    h_mm=99.036697,
    layer=0,
    anname='Kopie von u2d5c (17)',
    custom_path='M0 0 L0 280.734 L154.958 280.734 L154.958 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011899,
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Aianeptas es re iliaes dolupta', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Quaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori nonectiistis milit ratur aut alistori vellori nonectiistis milit ratur aut ', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Haribusam alit quo', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Haribusam alit quo doluptatem nonectiistis milit ratur aut alistori vellori bearum sim asimoditate isit ut aut quidunt uer itatiur apienem et ius pera cone liti autem volorporrum rectur? Taectiat adit, officipis debis et odi quia dit ommolor epedit hilitis qui optatus.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur?', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.', separator='para', paragraph_style='Fließtext weiß'),
    ],
)
page12.add(_chain12_0)

_chain12_1 = TextFrame(
    x_mm=77.666,
    y_mm=37.802771,
    w_mm=54.665739,
    h_mm=95.197229,
    layer=0,
    anname='Kopie von u2da1 (22)',
    custom_path='M0 0 L0 269.851 L154.958 269.851 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page12.add(_chain12_1)

_chain12_2 = TextFrame(
    x_mm=135.332,
    y_mm=37,
    w_mm=54.666,
    h_mm=94.479835,
    layer=0,
    anname='Kopie von u2da1 (23)',
    custom_path='M0 0 L0 267.816 L154.958 267.816 L154.958 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page12.add(_chain12_2)

page12.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=17.569743,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift weiß',
    col_gap_mm=0,
    runs=[
        Run(text='Beitrag in weiß'),
    ],
))

page12.add(TextFrame(
    x_mm=195.482953,
    y_mm=285.108333,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (11)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page12.add(TextFrame(
    x_mm=20,
    y_mm=137.716233,
    w_mm=170.000128,
    h_mm=34.283767,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift weiß',
    col_gap_mm=0,
    runs=[
        Run(text='Ein weiterer Beitrag in weiß mit Zitat in weiß'),
    ],
))

_chain13_0 = TextFrame(
    x_mm=20,
    y_mm=170.628459,
    w_mm=54.666423,
    h_mm=109.988991,
    layer=0,
    anname='Kopie von u2d5c (18)',
    custom_path='M0 0 L0 311.78 L154.96 311.78 L154.96 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1.011911,
    trail_style='Fließtext weiß',
    col_gap_mm=4.233333,
    runs=[
        Run(text='Perem la posseditatur ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Aianeptas es re iliaes doluptaQuaecep erfernatur adit, volut faciend estibusda pediosaes minctem oditatur? Qui as et inimus. io beat fugitatia qui od magnihi lluptam usciatio. Optatinverit am laborporrum quas atur, conet et de officte nihicab orrorrum ut debis eium endes nonsent.Em aut vid que vellacc aborisi tatiur sunt, commolupitia as voluptas min natincium quat hilit, sit elestiasiti re ma non comnim diam is inctotat.Haribusam alit quo doluptatem.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='On porecae. ', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Et od eseque eos alic temperaectem ratumqu iandae parum, ulpat am laborporrum quas atur, conet et de officte nihicab orr dolor aut lamusciis ideles atatem quodiatet qui consedi t ex et reiienem et ius pera cone liti auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.Magnatet, as erfero cum que maximintem est exped molestiusti audis sedem corporemped que lanto im audam adist ratius, sitatur? nonectiistis milit ratur aut alistori vellori.', separator='para', paragraph_style='Fließtext weiß'),
        Run(text='Gentorrum eum re re dus', separator='para', paragraph_style='Zwischenüberschrift weiß'),
        Run(text='Ium rerit dolendaerest hicilig endenimped qsenis voluptas qut am laborporrum quas atur, conet et de officte niuis andi doloritatet paritati ecullitatem hillendi nonsed mm quodiatet qui consedi t ex et reiiagnihil idigenimusae et, voluptur? Quia dolupta ipident.Ari abo. Nam unt aut ab uis andi doloritatet paritati dist, qui aligeni mendita eceribus, occullo incium utem expland.auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.Magnatet, as erfero cum que maximintem est exped...xpland.auusaectem qui nem et doluptata illa pratur moluptatia sande xceper.Magnatet, as erfero cum que maximintem '),
    ],
)
page12.add(_chain13_0)

_chain13_1 = TextFrame(
    x_mm=77.666722,
    y_mm=169.268807,
    w_mm=54.666423,
    h_mm=64.731193,
    layer=0,
    anname='Kopie von u2da1 (24)',
    custom_path='M0 0 L0 183.49 L154.96 183.49 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page12.add(_chain13_1)

_chain13_2 = TextFrame(
    x_mm=135.333444,
    y_mm=169,
    w_mm=54.666684,
    h_mm=109.810861,
    layer=0,
    anname='Kopie von u2da1 (25)',
    custom_path='M0 0 L0 311.274 L154.96 311.274 L154.96 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=4.233333,
)
page12.add(_chain13_2)

page12.add(TextFrame(
    x_mm=85.192594,
    y_mm=246.776351,
    w_mm=39.614679,
    h_mm=24.700917,
    layer=0,
    line_width_pt=1,
    trail_style='Zitat weißer Text',
    col_gap_mm=0,
    runs=[
        Run(text='Ich bin ein Zitat. Ich bin ein prägnantes Zitat.'),
    ],
))

page12.add(TextFrame(
    x_mm=82.27975,
    y_mm=272.205556,
    w_mm=45.440367,
    h_mm=4.844954,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext in grünem Kasten',
    trail_attrs={'ALIGN': '1'},
    col_gap_mm=0,
    runs=[
        Run(text='Leonore Gewessler', fcolor='White', fshade=100),
    ],
))

page12.add(ImageFrame(
    x_mm=99.167433,
    y_mm=236.798795,
    w_mm=11.665,
    h_mm=9.7986,
    layer=0,
    image='assets/frame_05.png',
    line_width_pt=1,
    local_scale=(0.027555, 0.027555),
))

page13.add(ImageFrame(
    x_mm=0,
    y_mm=149.636725,
    w_mm=210,
    h_mm=147.363275,
    layer=0,
    image='',
    line_width_pt=1,
))

page13.add(ImageFrame(
    x_mm=0,
    y_mm=-0.180716,
    w_mm=210.799064,
    h_mm=152.613771,
    layer=0,
    image='',
    fill='Dunkelgrün',
    line_width_pt=1,
    local_offset_mm=(1.093935, -0.760576),
))

page13.add(TextFrame(
    x_mm=8.51073,
    y_mm=283.697222,
    w_mm=12.775464,
    h_mm=9.480248,
    layer=0,
    anname='Kopie von u2d45 (12)',
    custom_path='M0 0 L0 26.8732 L36.2139 26.8732 L36.2139 0 L0 0 Z',
    fill_rule=0,
    line_width_pt=1,
    col_gap_mm=3.207462,
    runs=[
        Run(text='', var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))

page13.add(TextFrame(
    x_mm=20,
    y_mm=20,
    w_mm=169.998,
    h_mm=35.279835,
    layer=0,
    line_width_pt=1,
    default_linesp_mode=2,
    trail_style='Überschrift weiß',
    col_gap_mm=0,
    runs=[
        Run(text='Wichtiges zuletzt:'),
    ],
))

page13.add(TextFrame(
    x_mm=20,
    y_mm=41.202778,
    w_mm=54.25,
    h_mm=34.564222,
    layer=0,
    anname='Kopie von u14c',
    custom_path='M0 0 L0 97.9774 L153.78 97.9774 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Zum Beispiel Events', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Datum, Uhrzeit', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Location, Ort', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß'),
    ],
))

page13.add(TextFrame(
    x_mm=20,
    y_mm=80.713889,
    w_mm=54.25,
    h_mm=34.564222,
    layer=0,
    anname='Kopie von u14c (2)',
    custom_path='M0 0 L0 97.9774 L153.78 97.9774 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Zum Beispiel Events', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Datum, Uhrzeit', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Location, Ort', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß'),
    ],
))

page13.add(TextFrame(
    x_mm=77.873869,
    y_mm=41.202778,
    w_mm=54.25,
    h_mm=34.564222,
    layer=0,
    anname='Kopie von u14c (3)',
    custom_path='M0 0 L0 97.9774 L153.78 97.9774 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Zum Beispiel Events', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Datum, Uhrzeit', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Location, Ort', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß'),
    ],
))

page13.add(TextFrame(
    x_mm=77.873869,
    y_mm=80.713889,
    w_mm=54.25,
    h_mm=34.564222,
    layer=0,
    anname='Kopie von u14c (4)',
    custom_path='M0 0 L0 97.9774 L153.78 97.9774 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Zum Beispiel Events', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Datum, Uhrzeit', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Location, Ort', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß'),
    ],
))

page13.add(TextFrame(
    x_mm=135.54,
    y_mm=41.202778,
    w_mm=54.25,
    h_mm=34.564222,
    layer=0,
    anname='Kopie von u14c (5)',
    custom_path='M0 0 L0 97.9774 L153.78 97.9774 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Zum Beispiel Events', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Datum, Uhrzeit', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Location, Ort', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß'),
    ],
))

page13.add(TextFrame(
    x_mm=135.54,
    y_mm=80.713889,
    w_mm=54.25,
    h_mm=34.564222,
    layer=0,
    anname='Kopie von u14c (6)',
    custom_path='M0 0 L0 97.9774 L153.78 97.9774 L153.78 0 L0 0 Z',
    fill_rule=0,
    col_gap_mm=3.867223,
    runs=[
        Run(text='Zum Beispiel Events', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Datum, Uhrzeit', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Location, Ort', separator='para', paragraph_style='Headline in grünem Kasten', paragraph_attrs={'ALIGN': '0'}),
        Run(text='Nequia volupti omnient hicipsa dem eossece atiati dollit oditius nonsequunt aspiet', separator='para', paragraph_style='Fließtext weiß'),
    ],
))

page13.add(Polygon(
    x_mm=167.296947,
    y_mm=130.877383,
    w_mm=36.198843,
    h_mm=34.601351,
    layer=0,
    fill='Magenta',
    line_color='Magenta',
    line_width_pt=1,
    shape='ellipse',
))

page13.add(TextFrame(
    x_mm=168.65884,
    y_mm=139.903955,
    w_mm=31.905403,
    h_mm=24.779996,
    layer=0,
    rotation_deg=355,
    line_width_pt=1,
    col_gap_mm=0,
    runs=[
        Run(text='Hier', separator='para', paragraph_style='Schrift Störer  '),
        Run(text='steht ein', separator='para', paragraph_style='Schrift Störer  '),
        Run(text='Störer.', separator='para', paragraph_style='Schrift Störer  '),
    ],
))

page13.add(ImageFrame(
    x_mm=9.835481,
    y_mm=115.355556,
    w_mm=31.74327,
    h_mm=32.145084,
    layer=0,
    image='assets/frame_06.png',
    line_width_pt=1,
    local_scale=(0.189833, 0.189833),
))

page13.add(TextFrame(
    x_mm=54.864813,
    y_mm=118.886801,
    w_mm=103.46422,
    h_mm=30.471532,
    layer=0,
    line_width_pt=1,
    trail_style='Impressum',
    col_gap_mm=0,
    runs=[
        Run(text='Impressum', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Medieninhaber u. Herausgeber: Die Grünen Niederösterreich, Daniel Gran Straße 48, 3100 St. Pölten • Redaktion: Ortsgruppe + Anschrift •  Verteilt durch Firma/Post • Erscheinungstermin: April 2026 • Druck: Druckerei + Postanschrift • Fotos:wenn nicht anders angegeben: Name'),
    ],
))

_chain0_0.link_to(_chain0_1)
_chain0_1.link_to(_chain0_2)
_chain1_0.link_to(_chain1_1)
_chain1_1.link_to(_chain1_2)
_chain2_0.link_to(_chain2_1)
_chain2_1.link_to(_chain2_2)
_chain3_0.link_to(_chain3_1)
_chain3_1.link_to(_chain3_2)
_chain4_0.link_to(_chain4_1)
_chain4_1.link_to(_chain4_2)
_chain5_0.link_to(_chain5_1)
_chain5_1.link_to(_chain5_2)
_chain6_0.link_to(_chain6_1)
_chain6_1.link_to(_chain6_2)
_chain7_0.link_to(_chain7_1)
_chain7_1.link_to(_chain7_2)
_chain8_0.link_to(_chain8_1)
_chain8_1.link_to(_chain8_2)
_chain9_0.link_to(_chain9_1)
_chain9_1.link_to(_chain9_2)
_chain10_0.link_to(_chain10_1)
_chain10_1.link_to(_chain10_2)
_chain11_0.link_to(_chain11_1)
_chain11_1.link_to(_chain11_2)
_chain12_0.link_to(_chain12_1)
_chain12_1.link_to(_chain12_2)
_chain13_0.link_to(_chain13_1)
_chain13_1.link_to(_chain13_2)

doc.save(HERE / "template.sla")
print(f"OK: {HERE / "template.sla"}")
