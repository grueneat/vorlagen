# Auto-generated from postkarte-vorlage-original.sla by tools/sla_to_dsl.py.
# Hand-edit thereafter; this file is the source of truth.

from pathlib import Path

from sla_lib.builder import (
    Document, TextFrame, ImageFrame, Polygon, Run,
    DocumentLayer, ParaStyle, CharStyle, SoftShadow,
)

HERE = Path(__file__).resolve().parent

doc = Document(
    title='',
    template_id='postkarte-a6-kampagne',
    author='',
    facing_pages=False,
    column_gap_default_pt=11,
    deffont='Gotham Narrow Book',
    defsize=12,
    first_page_num=1,
    palette_replaces_ci=True,
    layers=[
        DocumentLayer(name='Hintergrund', visible=True, printable=True, editable=True, flow=True, transparent=1, blend=0, outline=False, layer_color='#000000'),
    ],
)

doc.add_color('Black', cmyk=(0, 0, 0, 100))
doc.add_color('Dunkelgrün', cmyk=(85, 35, 95, 10))
doc.add_color('Gelb', cmyk=(0, 0, 100, 0))
doc.add_color('Green', rgb=(153, 102, 51))
doc.add_color('Hellgrün', cmyk=(69, 0, 100, 0))
doc.add_color('Magenta', cmyk=(0, 100, 0, 0))
doc.add_color('Registration', cmyk=(100, 100, 100, 100), register=True)
doc.add_color('White', cmyk=(0, 0, 0, 0))

doc.add_char_style(CharStyle(name='Default Character Style', font='Gotham Narrow Black', fcolor='Black', fontfeatures='', features='inherit', language='de', scolor='Black', bgcolor='None', fontsize=12, kern=0, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, fshade=100, hyph_word_min=3, sshade=100, bgshade=100, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1, scaleh=100, scalev=100, baseline_offset=0, is_default=True))
doc.add_char_style(CharStyle(name='Default Character Style (2)', font='Gotham Narrow Book', fcolor='Black', fontfeatures='-clig', features='inherit', language='de', scolor='Black', bgcolor='None', fontsize=12, kern=0, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, fshade=100, hyph_word_min=3, sshade=100, bgshade=100, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1, scaleh=100, scalev=100, baseline_offset=0))
doc.add_para_style(ParaStyle(name='Default Paragraph Style', bcolor='None', bullet='0', linesp=15, space_before_pt=0, space_after_pt=0, first_indent_pt=0, left_indent_pt=0, right_indent_pt=0, paragraph_effect_offset=0, align=0, linesp_mode=0, drop_lines=2, hyph_consecutive_lines=2, direction=0, bshade=100, numeration=0, drop_cap=False, is_default=True))
doc.add_para_style(ParaStyle(name='Fließtext', font='Gotham Narrow Book', fcolor='White', language='de', fontfeatures='-clig', fontsize=12, linesp=13, align=1, linesp_mode=0))
doc.add_para_style(ParaStyle(name='Impressum', font='Gotham Narrow Book', language='de', fontfeatures='-clig', fontsize=5, linesp=6))
doc.add_para_style(ParaStyle(name='Default Paragraph Style (2)', font='Gotham Narrow Book', bcolor='None', fontfeatures='-clig', bullet='0', linesp=15, space_before_pt=0, space_after_pt=5, first_indent_pt=0, left_indent_pt=0, right_indent_pt=0, paragraph_effect_offset=0, align=0, linesp_mode=0, drop_lines=2, hyph_consecutive_lines=2, direction=0, bshade=100, numeration=0, drop_cap=False))
doc.add_para_style(ParaStyle(name='Schrift rosa Kreis', font='Gotham Narrow Ultra', fcolor='White', language='de', fontfeatures='-clig', fontsize=10, linesp=11, kern=0, align=1, linesp_mode=0))
doc.add_para_style(ParaStyle(name='Headline sehr wichtig', font='Gotham Narrow Ultra', fcolor='White', language='de', fontfeatures='-clig', features='', fontsize=27, linesp=23, kern=1, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, align=1, linesp_mode=0, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1))
doc.add_para_style(ParaStyle(name='Kontaktmöglichkeiten', font='Gotham Narrow Book', language='de', fontfeatures='-clig', fontsize=8, linesp=10, linesp_mode=0))
doc.add_para_style(ParaStyle(name='Vollkorn Headline sehr wichtig', font='Vollkorn Black Italic', fcolor='Gelb', language='de', fontfeatures='-clig', fontsize=27, linesp=23, align=1, linesp_mode=0))
doc.add_para_style(ParaStyle(name='Unterüberschrift', font='Gotham Narrow Book', fcolor='White', language='de', fontfeatures='-clig', features='', fontsize=13, linesp=16, space_after_pt=0, kern=0, txt_underline_pos=-0.1, txt_underline_width=-0.1, txt_strike_pos=-0.1, txt_strike_width=-0.1, align=1, linesp_mode=0, txt_shadow_x=5, txt_shadow_y=-5, txt_outline=1))

doc.add_master(
    name='Normal',
    size=(105, 148),
    bleed_mm=3,
    margins_mm=(14.111111, 14.111111, 14.111111, 14.111111),
    facing='right',
)

page0 = doc.add_page(
    size=(105, 148),
    bleed_mm=3,
    margins_mm=(14.111111, 14.111111, 14.111111, 14.111111),
    master='Normal',
)
page1 = doc.add_page(
    size=(105, 148),
    bleed_mm=3,
    margins_mm=(14.111111, 14.111111, 14.111111, 14.111111),
    master='Normal',
)

page0.add(Polygon(
    x_mm=-3,
    y_mm=-3,
    w_mm=111,
    h_mm=154,
    layer=0,
    fill='Dunkelgrün',
    line_color='Black',
    line_width_pt=1,
))

page0.add(ImageFrame(
    x_mm=10.5,
    y_mm=10.5,
    w_mm=84,
    h_mm=127,
    layer=0,
    image='',
    line_width_pt=3.835276,
))

page0.add(ImageFrame(
    x_mm=42.182635,
    y_mm=89.391824,
    w_mm=20.545843,
    h_mm=20.905395,
    layer=0,
    image='assets/frame_01.png',
    line_width_pt=1,
    local_scale=(0.048533, 0.048533),
))

page0.add(TextFrame(
    x_mm=6.272653,
    y_mm=45.608312,
    w_mm=92.454694,
    h_mm=47.07156,
    layer=0,
    col_gap_mm=0,
    soft_shadow=SoftShadow(color='Dunkelgrün', blur_radius_pt=8.503937, x_offset_pt=1.984252, y_offset_pt=1.984252, blend_mode=1, opacity=0, shade=100, erase=False, object_trans=False),
    runs=[
        Run(text='Bei dir wachsen', fcolor='White', fshade=100, separator='para'),
        Run(text='die Sorgen,', separator='para'),
        Run(text='bei ihnen', separator='para'),
        Run(text='der Reichtum'),
    ],
))

page0.add(TextFrame(
    x_mm=17.545872,
    y_mm=79.863358,
    w_mm=69.908257,
    h_mm=8.432055,
    layer=0,
    col_gap_mm=0,
    runs=[
        Run(text='Jetzt Petition unterschreiben!'),
    ],
))

page0.add(Polygon(
    x_mm=73.096311,
    y_mm=30.529167,
    w_mm=20.539945,
    h_mm=20.54,
    layer=0,
    rotation_deg=351,
    fill='Magenta',
    line_color='Magenta',
    line_width_pt=1,
    shape='ellipse',
))

page0.add(TextFrame(
    x_mm=74.490137,
    y_mm=34.865453,
    w_mm=19.143301,
    h_mm=11.538116,
    layer=0,
    rotation_deg=351,
    col_gap_mm=0,
    runs=[
        Run(text='Super-', separator='breakline'),
        Run(text='reiche fair ', separator='breakline'),
        Run(text='besteuern'),
    ],
))

page1.add(Polygon(
    x_mm=-3,
    y_mm=-3,
    w_mm=111,
    h_mm=154,
    layer=0,
    fill='Dunkelgrün',
    line_color='Black',
    line_width_pt=1,
))

page1.add(TextFrame(
    x_mm=17,
    y_mm=12.647222,
    w_mm=71,
    h_mm=113.481054,
    layer=0,
    col_gap_mm=0,
    runs=[
        Run(text='Superreiche', separator='para'),
        Run(text='fair besteuern', separator='para'),
        Run(text='Österreich muss sparen. Aber was ', separator='para'),
        Run(text='die Regierung macht, ist unfair: ', separator='para'),
        Run(text='Sie kürzt bei Familien, Kindern und Pensionist:innen. Für dich werden Gebühren und Öffi-Tickets teurer. ', separator='para'),
        Run(text='Aber die Superreichen, die zig ', separator='para'),
        Run(text='Millionen erben, zahlen nichts.', separator='para'),
        Run(text='Wir wollen das ändern.', separator='para'),
        Run(text='Unterschreiben jetzt unsere Petition'),
    ],
))

page1.add(TextFrame(
    x_mm=8.165364,
    y_mm=130.395916,
    w_mm=38.496147,
    h_mm=16.032294,
    layer=0,
    text_align=0,
    col_gap_mm=0,
    runs=[
        Run(text='Facebook Name', fcolor='White', fshade=100, separator='breakline'),
        Run(text='Instagram Name', fcolor='White', fshade=100, separator='breakline'),
        Run(text='Mail-Adresse', fcolor='White', fshade=100, separator='breakline'),
        Run(text='Telefonnummer', fcolor='White', fshade=100),
    ],
))

page1.add(TextFrame(
    x_mm=61.661363,
    y_mm=135.435137,
    w_mm=41.944954,
    h_mm=10.619582,
    layer=0,
    col_gap_mm=0,
    runs=[
        Run(text='Impressum:', font='Gotham Narrow Bold', fcolor='White', features='inherit', fshade=100),
        Run(text=' Medieninhaber und Herausgeber: Die Grünen Niederösterreich, Daniel-GranStraße 48, 3100 St. Pölten. ·  Druck: Druckerei mit Postanschrift · Evtl. Hinweis auf Umweltzeichens wenn zutreffend', fcolor='White', fshade=100),
    ],
))

page1.add(ImageFrame(
    x_mm=5.035675,
    y_mm=130.403037,
    w_mm=2.5,
    h_mm=2.5,
    layer=0,
    corner_radius_mm=1,
    custom_path='M0 2.83465 C0 1.26911 1.26911 0 2.83465 0 L4.25197 0 C5.8175 0 7.08661 1.26911 7.08661 2.83465 L7.08661 4.25197 C7.08661 5.8175 5.8175 7.08661 4.25197 7.08661 L2.83465 7.08661 C1.26911 7.08661 0 5.8175 0 4.25197 L0 2.83465 Z',
    image='assets/frame_02.png',
    line_width_pt=1,
    local_scale=(0.009981, 0.009981),
))

page1.add(ImageFrame(
    x_mm=5.035675,
    y_mm=137.458592,
    w_mm=2.5,
    h_mm=2.5,
    layer=0,
    corner_radius_mm=1,
    custom_path='M0 2.83465 C0 1.26911 1.26911 0 2.83465 0 L4.25197 0 C5.8175 0 7.08661 1.26911 7.08661 2.83465 L7.08661 4.25197 C7.08661 5.8175 5.8175 7.08661 4.25197 7.08661 L2.83465 7.08661 C1.26911 7.08661 0 5.8175 0 4.25197 L0 2.83465 Z',
    image='assets/frame_03.png',
    line_width_pt=1,
    local_scale=(0.009981, 0.009981),
))

page1.add(ImageFrame(
    x_mm=5.035675,
    y_mm=134.145718,
    w_mm=2.5,
    h_mm=2.5,
    layer=0,
    corner_radius_mm=0.82422,
    custom_path='M0 2.33637 C0 1.04603 1.04603 0 2.33637 0 L4.75024 0 C6.04058 0 7.08661 1.04603 7.08661 2.33637 L7.08661 4.75024 C7.08661 6.04058 6.04058 7.08661 4.75024 7.08661 L2.33637 7.08661 C1.04603 7.08661 0 6.04058 0 4.75024 L0 2.33637 Z',
    image='assets/frame_04.png',
    line_width_pt=1,
    local_scale=(0.009981, 0.009981),
))

page1.add(ImageFrame(
    x_mm=5.035675,
    y_mm=140.98637,
    w_mm=2.5,
    h_mm=2.5,
    layer=0,
    corner_radius_mm=1,
    custom_path='M0 2.83465 C0 1.26911 1.26911 0 2.83465 0 L4.25197 0 C5.8175 0 7.08661 1.26911 7.08661 2.83465 L7.08661 4.25197 C7.08661 5.8175 5.8175 7.08661 4.25197 7.08661 L2.83465 7.08661 C1.26911 7.08661 0 5.8175 0 4.25197 L0 2.83465 Z',
    image='assets/frame_05.png',
    line_width_pt=1,
    local_scale=(0.009981, 0.009981),
))

page1.add(ImageFrame(
    x_mm=42.539692,
    y_mm=91.684637,
    w_mm=19.920617,
    h_mm=19.920617,
    layer=0,
    image='assets/frame_06.png',
    line_width_pt=1,
    local_scale=(0.110289, 0.110289),
))

page1.add(TextFrame(
    x_mm=10.904587,
    y_mm=116.197838,
    w_mm=83.190826,
    h_mm=4.427523,
    layer=0,
    col_gap_mm=0,
    runs=[
        Run(text='https://gruene.at/superreichebesteuern/', fontsize=9),
    ],
))

page1.add(ImageFrame(
    x_mm=26.580967,
    y_mm=119.88744,
    w_mm=51.77181,
    h_mm=3.621636,
    layer=0,
    image='assets/frame_07.png',
    line_width_pt=1,
    local_scale=(0.135884, 0.135884),
))

doc.save(HERE / "template.sla")
print(f"OK: {HERE / "template.sla"}")
