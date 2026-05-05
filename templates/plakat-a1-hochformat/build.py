# Auto-generated from plakat-a1-hochformat-original.sla by tools/sla_to_dsl.py.
# Hand-edit thereafter; this file is the source of truth.

from pathlib import Path

from sla_lib.builder import (
    Document, TextFrame, ImageFrame, Polygon, Run,
    DocumentLayer, ParaStyle, CharStyle, SoftShadow,
)

HERE = Path(__file__).resolve().parent

doc = Document(
    title='',
    template_id='plakat-a1-hochformat',
    author='',
    facing_pages=False,
    column_gap_default_pt=11,
    deffont='Gotham Narrow Black',
    defsize=12,
    first_page_num=1,
    palette_replaces_ci=True,
    extra_doc_attrs={'ALAYER': '0', 'AUTOL': '100', 'BaseC': '#c0c0c0', 'CPICT': 'None', 'CSPICT': 'None', 'DCOL': '1', 'DGAP': '0', 'DIIm': '0', 'DISc': '1', 'DPIn': 'sRGB display profile (ICC v2.2)', 'DPIn2': 'sRGB display profile (ICC v2.2)', 'DPIn3': 'PSO Uncoated ISO12647 (ECI)', 'DPInCMYK': 'PSO Uncoated ISO12647 (ECI)', 'DPPr': 'PSO Uncoated ISO12647 (ECI)', 'DPSFo': '0', 'DPSo': '0', 'DPbla': '1', 'DPgam': '0', 'DPuse': '1', 'EmbeddedPath': '0', 'EndArrow': '0', 'FirstLineOffset': '1', 'GRAB': '4', 'GUIDELOCK': '0', 'GridType': '0', 'GuideC': '#000080', 'GuideRad': '10', 'HalfRes': '1', 'MAJGRID': '100.001', 'MAJORC': '#00ff00', 'MINGRID': '20.001', 'MINORC': '#00ff00', 'PASPECT': '1', 'PICTSCX': '1', 'PICTSCY': '1', 'PICTSSHADE': '100', 'POLYC': '4', 'POLYCUR': '0', 'POLYF': '0.502', 'POLYIR': '0', 'POLYOCUR': '0', 'POLYR': '0', 'POLYS': '0', 'PRESET': '0', 'PSCALE': '1', 'SHOWBASE': '0', 'SHOWControl': '0', 'SHOWFRAME': '1', 'SHOWGRID': '0', 'SHOWGUIDES': '0', 'SHOWLAYERM': '0', 'SHOWLINK': '0', 'SHOWMARGIN': '0', 'SHOWPICT': '1', 'SUBJECT': '', 'SnapToElement': '0', 'SnapToGrid': '0', 'SnapToGuides': '0', 'StartArrow': '0', 'StrikeThruPos': '-1', 'StrikeThruWidth': '-1', 'StrokeText': 'Black', 'TabFill': '', 'TabWidth': '36', 'TextBackGround': 'None', 'TextBackGroundShade': '100', 'TextDistBottom': '0', 'TextDistLeft': '0', 'TextDistRight': '0', 'TextDistTop': '0', 'TextLineColor': 'None', 'TextLineShade': '100', 'TextPenShade': '100', 'TextStrokeShade': '100', 'UnderlinePos': '-1', 'UnderlineWidth': '-1', 'VHOCH': '33', 'VHOCHSC': '66', 'VKAPIT': '75', 'VTIEF': '33', 'VTIEFSC': '66', 'arcStartAngle': '30', 'arcSweepAngle': '300', 'calligraphicPenAngle': '0', 'calligraphicPenFillColor': 'Black', 'calligraphicPenFillColorShade': '100', 'calligraphicPenLineColor': 'Black', 'calligraphicPenLineColorShade': '100', 'calligraphicPenLineWidth': '1', 'calligraphicPenStyle': '1', 'calligraphicPenWidth': '10', 'constrain': '15', 'dispX': '10.001', 'dispY': '10.001', 'renderStack': '2 0 4 3 1', 'rulerMode': '1', 'rulerXoffset': '0', 'rulerYoffset': '0', 'showcolborders': '1', 'showrulers': '1', 'spiralEndAngle': '1080', 'spiralFactor': '1.2', 'spiralStartAngle': '0'},
    layers=[
        DocumentLayer(name='Hintergrund', visible=True, printable=True, editable=True, flow=True, transparent=1, blend=0, outline=False, layer_color='#000000'),
    ],
)

doc.add_color('Black', cmyk=(0, 0, 0, 100))
doc.add_color('Dunkelgrün', cmyk=(85, 35, 95, 10))
doc.add_color('Gelb', cmyk=(0, 0, 100, 0))
doc.add_color('Registration', cmyk=(100, 100, 100, 100), register=True)
doc.add_color('White', cmyk=(0, 0, 0, 0))

doc.add_char_style(CharStyle(name='Default Character Style', font='Gotham Narrow Black', fcolor='Black', fontfeatures='', features='inherit', language='de', scolor='Black', bgcolor='None', fontsize=12, kern=0, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, fshade=100, hyph_word_min=3, sshade=100, bgshade=100, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1, scaleh=100, scalev=100, baseline_offset=0, is_default=True))
doc.add_para_style(ParaStyle(name='Default Paragraph Style', bcolor='None', bullet='0', linesp=15, space_before_pt=0, space_after_pt=0, first_indent_pt=0, left_indent_pt=0, right_indent_pt=0, paragraph_effect_offset=0, align=0, linesp_mode=0, drop_lines=2, hyph_consecutive_lines=2, direction=0, bshade=100, numeration=0, drop_cap=False, is_default=True))
doc.add_para_style(ParaStyle(name='Headlineweiß', font='Gotham Narrow Ultra', fcolor='White', language='de', fontfeatures='-clig', features='', fontsize=160, linesp=150, kern=1, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, align=0, linesp_mode=0, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1, baseline_offset=0))
doc.add_para_style(ParaStyle(name='Überschrift gelb', font='Vollkorn Black Italic', fcolor='Gelb', language='de', bcolor='None', fontfeatures='-clig', features='', fontsize=160, linesp=150, space_after_pt=0, kern=2.5, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, align=0, linesp_mode=0, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1))
doc.add_para_style(ParaStyle(name='Fließtext', font='Gotham Narrow Book', fcolor='White', language='de', fontfeatures='-clig', fontsize=50, linesp_mode=1))
doc.add_para_style(ParaStyle(name='Impressum', font='Gotham Narrow Book', language='de', fontfeatures='-clig', fontsize=20, linesp=20, linesp_mode=0))

doc.add_master(
    name='Normal',
    size=(594, 841),
    bleed_mm=3,
    margins_mm=(14.111111, 14.111111, 14.111111, 14.111111),
    facing='right',
)

page0 = doc.add_page(
    size=(594, 841),
    bleed_mm=3,
    margins_mm=(14.111111, 14.111111, 14.111111, 14.111111),
    master='Normal',
)

page0.add(TextFrame(
    x_mm=0,
    y_mm=413.939413,
    w_mm=594,
    h_mm=427.060587,
    layer=0,
    fill='Dunkelgrün',
    line_width_pt=1,
    col_gap_mm=0,
))

page0.add(TextFrame(
    x_mm=32.620624,
    y_mm=442.891248,
    w_mm=491.280275,
    h_mm=244.271193,
    layer=0,
    line_width_pt=1,
    trail_style='Headlineweiß',
    col_gap_mm=0,
    runs=[
        Run(text='Hier steht ', separator='para', paragraph_style='Headlineweiß'),
        Run(text='ei\xadne gro\xadße ', separator='para', paragraph_style='Überschrift gelb'),
        Run(text='vier\xadzei\xadli\xadge ', separator='para', paragraph_style='Headlineweiß'),
        Run(text='Ü\xadber\xadschrift ', separator='para', paragraph_style='Headlineweiß'),
        Run(text='in Baden.'),
    ],
))

page0.add(TextFrame(
    x_mm=563.693455,
    y_mm=832.688889,
    w_mm=377.37599,
    h_mm=21.0235,
    layer=0,
    rotation_deg=270,
    line_width_pt=1,
    trail_style='Impressum',
    col_gap_mm=0,
    runs=[
        Run(text='Impressum:', font='Gotham Narrow Bold', fcolor='White', fshade=100),
        Run(text=' Medieninhaber und Herausgeber: Die Grünen Niederösterreich, Daniel-GranStraße 48, 3100 St. Pölten. ·  Druck: Druckerei mit Postanschrift · Evtl. Hinweis auf Umweltzeichens wenn zutreffend', fcolor='White', fshade=100),
    ],
))

page0.add(TextFrame(
    x_mm=32.620624,
    y_mm=772.916477,
    w_mm=306.776147,
    h_mm=34.488073,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext',
    col_gap_mm=0,
    runs=[
        Run(text='Anmeldung unter: gruene.at/tour'),
    ],
))

page0.add(TextFrame(
    x_mm=32.620624,
    y_mm=700.391743,
    w_mm=233.027523,
    h_mm=41.797558,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext',
    col_gap_mm=0,
    runs=[
        Run(text='Freitag, 20. Februar', separator='para', paragraph_style='Fließtext'),
        Run(text='18:00 - 21:00'),
    ],
))

page0.add(TextFrame(
    x_mm=277.66201,
    y_mm=700.391743,
    w_mm=235.940367,
    h_mm=41.797558,
    layer=0,
    line_width_pt=1,
    trail_style='Fließtext',
    col_gap_mm=0,
    runs=[
        Run(text='Wirtshaus im Batzenhäusl', separator='para', paragraph_style='Fließtext'),
        Run(text='Theaterplatz 9, 2500 Baden'),
    ],
))

page0.add(ImageFrame(
    x_mm=0,
    y_mm=0,
    w_mm=594,
    h_mm=413.939413,
    layer=0,
    image='',
    line_width_pt=1,
))

page0.add(ImageFrame(
    x_mm=0.494343,
    y_mm=574.742843,
    w_mm=372.80288,
    h_mm=133.46549,
    layer=0,
    image='assets/frame_01.png',
    line_width_pt=1,
    local_scale=(0.978485, 0.978485),
))

page0.add(ImageFrame(
    x_mm=451.44,
    y_mm=35.64,
    w_mm=107.1,
    h_mm=107.1,
    layer=0,
    image='assets/frame_02.png',
    line_width_pt=1,
    local_scale=(0.12432, 0.12432),
))

doc.save(HERE / "template.sla")
print(f"OK: {HERE / "template.sla"}")
