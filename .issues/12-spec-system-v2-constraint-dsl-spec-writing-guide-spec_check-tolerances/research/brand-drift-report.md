# structural_check report

## templates/infostand-tent-card-a5-quer
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'tent/headline' linesp=40 != fontsize(36) * 0.9 = 32.40
- ERROR brand:line_spacing_0.9: para style 'tent/body' linesp=18 != fontsize(14) * 0.9 = 12.60
- ERROR brand:line_spacing_0.9: para style 'tent/impressum' linesp=6 != fontsize(5) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'tent/cta' linesp=14 != fontsize(11) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'tent/termine' linesp=13 != fontsize(10) * 0.9 = 9.00
- PASS brand:hl_sl_distance_x2: ok
- ERROR brand:logo_size_3M: logo 'Logo Grüne (panel A)' w_mm=36 != 3*M (37.80mm) +/-0.5mm  [kurze_kante=210.0mm]
- ERROR brand:logo_size_3M: logo 'Logo Grüne (panel B)' w_mm=36 != 3*M (37.80mm) +/-0.5mm  [kurze_kante=210.0mm]
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 15 errors, 0 warnings, 0 skipped, 6 passes

## templates/kandidat-falzflyer-din-lang
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'falzflyer/cand-name' linesp=27 != fontsize(24) * 0.9 = 21.60
- ERROR brand:line_spacing_0.9: para style 'falzflyer/slogan' linesp=17 != fontsize(14) * 0.9 = 12.60
- ERROR brand:line_spacing_0.9: para style 'falzflyer/teaser-headline' linesp=22 != fontsize(18) * 0.9 = 16.20
- ERROR brand:line_spacing_0.9: para style 'falzflyer/teaser-body' linesp=14 != fontsize(11) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'falzflyer/closer-headline' linesp=26 != fontsize(22) * 0.9 = 19.80
- ERROR brand:line_spacing_0.9: para style 'falzflyer/closer-datum' linesp=18 != fontsize(14) * 0.9 = 12.60
- ERROR brand:line_spacing_0.9: para style 'falzflyer/closer-url' linesp=14 != fontsize(11) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'falzflyer/thema-headline' linesp=20 != fontsize(16) * 0.9 = 14.40
- ERROR brand:line_spacing_0.9: para style 'falzflyer/thema-body' linesp=11 != fontsize(9) * 0.9 = 8.10
- ERROR brand:line_spacing_0.9: para style 'falzflyer/contact-headline' linesp=20 != fontsize(16) * 0.9 = 14.40
- ERROR brand:line_spacing_0.9: para style 'falzflyer/contact-body' linesp=12 != fontsize(10) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'falzflyer/impressum' linesp=8 != fontsize(6) * 0.9 = 5.40
- PASS brand:hl_sl_distance_x2: ok
- ERROR brand:logo_size_3M: logo 'P1 Logo Grüne' w_mm=20 != 3*M (37.80mm) +/-0.5mm  [kurze_kante=210.0mm]
- ERROR brand:logo_size_3M: logo 'P2 Logo (klein)' w_mm=16 != 3*M (37.80mm) +/-0.5mm  [kurze_kante=210.0mm]
- ERROR brand:logo_size_3M: logo 'P6 Logo Grüne' w_mm=17 != 3*M (37.80mm) +/-0.5mm  [kurze_kante=210.0mm]
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 23 errors, 0 warnings, 0 skipped, 6 passes

## templates/plakat-a1-hochformat
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'Headlineweiß' linesp=150 != fontsize(160) * 0.9 = 144.00
- ERROR brand:line_spacing_0.9: para style 'Überschrift gelb' linesp=150 != fontsize(160) * 0.9 = 144.00
- ERROR brand:line_spacing_0.9: para style 'Impressum' linesp=20 != fontsize(20) * 0.9 = 18.00
- PASS brand:hl_sl_distance_x2: ok
- PASS brand:logo_size_3M: ok
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 11 errors, 0 warnings, 0 skipped, 7 passes

## templates/postkarte-a6-kampagne
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'Fließtext' linesp=13 != fontsize(12) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'Impressum' linesp=6 != fontsize(5) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'Schrift rosa Kreis' linesp=11 != fontsize(10) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'Headline sehr wichtig' linesp=23 != fontsize(27) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'Kontaktmöglichkeiten' linesp=10 != fontsize(8) * 0.9 = 7.20
- ERROR brand:line_spacing_0.9: para style 'Vollkorn Headline sehr wichtig' linesp=23 != fontsize(27) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'Unterüberschrift' linesp=16 != fontsize(13) * 0.9 = 11.70
- PASS brand:hl_sl_distance_x2: ok
- PASS brand:logo_size_3M: ok
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 15 errors, 0 warnings, 0 skipped, 7 passes

## templates/themen-plakat-a3-quer
### CONSTRAINTS
- PASS same_y:beleg_headlines_row: ok
- PASS same_y:beleg_bodies_row: ok
- PASS distance_y:hl_to_sub: ok
- PASS distance_y:beleg1_hd_to_body: ok
- PASS same_style:beleg_hd_style_consistent: ok
- PASS same_style:beleg_body_style_consistent: ok
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'themen-plakat/headline' linesp=64 != fontsize(60) * 0.9 = 54.00
- ERROR brand:line_spacing_0.9: para style 'themen-plakat/sub' linesp=22 != fontsize(18) * 0.9 = 16.20
- ERROR brand:line_spacing_0.9: para style 'themen-plakat/beleg-headline' linesp=27 != fontsize(24) * 0.9 = 21.60
- ERROR brand:line_spacing_0.9: para style 'themen-plakat/beleg-body' linesp=16 != fontsize(13) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'themen-plakat/source' linesp=12 != fontsize(10) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'themen-plakat/impressum' linesp=8 != fontsize(7) * 0.9 = 6.30
- ERROR brand:hl_sl_distance_x2: HL 'Headline These' -> SL 'Sub-Headline' distance 2.00mm != 2*baseline (10.8mm) +/-1.0mm
- ERROR brand:logo_size_3M: logo 'Logo Grüne (top-left)' w_mm=32 != 3*M (53.46mm) +/-0.5mm  [kurze_kante=297.0mm]
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 16 errors, 0 warnings, 0 skipped, 11 passes

## templates/wahlaufruf-postkarte-a6-quer
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'wahlaufruf/headline' linesp=27 != fontsize(24) * 0.9 = 21.60
- ERROR brand:line_spacing_0.9: para style 'wahlaufruf/cell-headline' linesp=16 != fontsize(14) * 0.9 = 12.60
- ERROR brand:line_spacing_0.9: para style 'wahlaufruf/cell-body' linesp=11 != fontsize(9) * 0.9 = 8.10
- ERROR brand:line_spacing_0.9: para style 'wahlaufruf/impressum' linesp=7 != fontsize(6) * 0.9 = 5.40
- PASS brand:hl_sl_distance_x2: ok
- ERROR brand:logo_size_3M: logo 'Logo Grüne (weiss)' w_mm=35 != 3*M (18.90mm) +/-0.5mm  [kurze_kante=105.0mm]
- ERROR brand:logo_size_3M: logo 'Logo Grüne (Bund-Dunkel)' w_mm=18 != 3*M (18.90mm) +/-0.5mm  [kurze_kante=105.0mm]
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 14 errors, 0 warnings, 0 skipped, 6 passes

## templates/wahltag-tueranhaenger
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- ERROR brand:font_family: text frame 'Kandidat-Position' uses font 'Gotham Narrow Book Italic' not in ['Gotham Narrow Black', 'Gotham Narrow Bold', 'Gotham Narrow Book', 'Gotham Narrow Ultra', 'Vollkorn Black Italic']
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/headline' linesp=30 != fontsize(28) * 0.9 = 25.20
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/sub' linesp=22 != fontsize(18) * 0.9 = 16.20
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/body' linesp=14 != fontsize(11) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/cand-name' linesp=16 != fontsize(14) * 0.9 = 12.60
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/cand-pos' linesp=12 != fontsize(10) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/url' linesp=14 != fontsize(11) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'tueranhaenger/impressum' linesp=7 != fontsize(6) * 0.9 = 5.40
- ERROR brand:hl_sl_distance_x2: HL 'Headline-Wahltag' -> SL 'Sub-Headline' distance 4.00mm != 2*baseline (10.8mm) +/-1.0mm
- ERROR brand:logo_size_3M: logo 'Logo Grüne (weiss, top)' w_mm=35 != 3*M (18.90mm) +/-0.5mm  [kurze_kante=105.0mm]
- ERROR brand:logo_size_3M: logo 'Logo Grüne (weiss, back-band)' w_mm=35 != 3*M (18.90mm) +/-0.5mm  [kurze_kante=105.0mm]
- ERROR brand:logo_size_3M: logo 'Logo Grüne (Bund-Dunkel, back)' w_mm=18 != 3*M (18.90mm) +/-0.5mm  [kurze_kante=105.0mm]
- PASS brand:text_on_green: ok
- ERROR brand:bleed_3mm: page #? bleed_mm=2.0 != 3.0
- ERROR brand:bleed_3mm: page #? bleed_mm=2.0 != 3.0
- ERROR brand:wahlkreuz_colored_bg: Wahlkreuz frame 'Hellgrün-Band (Wahlkreuz)' has no overlapping polygon with fill in ['Dunkelgrün', 'Hellgrün', 'Magenta']

Result: 23 errors, 0 warnings, 0 skipped, 2 passes

## templates/zeitung-a4-grun
### CONSTRAINTS
- (no CONSTRAINTS list, or empty)
### BRAND_CONSTRAINTS
- PASS brand:color_palette: ok
- PASS brand:font_family: ok
- ERROR brand:line_spacing_0.9: para style 'ci/default' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/headline-ultra' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/headline-vollkorn-italic' linesp=23.0 != fontsize(27.0) * 0.9 = 24.30
- ERROR brand:line_spacing_0.9: para style 'ci/body-12' linesp=13.0 != fontsize(12.0) * 0.9 = 10.80
- ERROR brand:line_spacing_0.9: para style 'ci/body-11' linesp=12.0 != fontsize(11.0) * 0.9 = 9.90
- ERROR brand:line_spacing_0.9: para style 'ci/impressum' linesp=6.0 != fontsize(5.0) * 0.9 = 4.50
- ERROR brand:line_spacing_0.9: para style 'ci/stoerer' linesp=11.0 != fontsize(10.0) * 0.9 = 9.00
- ERROR brand:line_spacing_0.9: para style 'ci/cta' linesp=13.0 != fontsize(13.0) * 0.9 = 11.70
- ERROR brand:line_spacing_0.9: para style 'Titelseite Header' linesp=46 != fontsize(55) * 0.9 = 49.50
- ERROR brand:line_spacing_0.9: para style 'Impressum' linesp=9 != fontsize(8) * 0.9 = 7.20
- ERROR brand:line_spacing_0.9: para style 'Schrift Störer  ' linesp=13 != fontsize(19) * 0.9 = 17.10
- ERROR brand:line_spacing_0.9: para style 'Überschrift Dunkelgrün' linesp=35 != fontsize(40) * 0.9 = 36.00
- ERROR brand:line_spacing_0.9: para style 'Bildunterschrift weiß' linesp=12 != fontsize(10) * 0.9 = 9.00
- PASS brand:hl_sl_distance_x2: ok
- PASS brand:logo_size_3M: ok
- PASS brand:text_on_green: ok
- PASS brand:bleed_3mm: ok
- PASS brand:wahlkreuz_colored_bg: ok

Result: 13 errors, 0 warnings, 0 skipped, 7 passes

