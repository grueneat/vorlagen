# RESEARCH — Issue 42: Freie Gotham-Ersatzschriften + Vergleichsseite

## 1. Codebase-Befunde

### Schrift-Provisionierung
- `shared/fonts/README.md`: Gotham Narrow ist proprietär, **nicht** im Repo,
  liegt in der gitignorierten Drop-Zone `/root/workspace/fonts/`. Verwendete
  Schnitte: **Book, Bold, Black, Ultra**. Ohne Installation → DejaVu-Fallback.
- Vollkorn (OFL) ist bereits frei eingebunden; Alias via
  `shared/fonts/50-vollkorn-family-alias.conf` (Family-Name-Mapping für fontconfig).
- Schriften werden beim Dev-Container-Build nach `/usr/local/share/fonts/gruene/`
  installiert + `fc-cache -f`.

### Render-Pipeline
- `bin/render-gallery` → `tools/render_pipeline.py`: `build.py → template.sla`,
  `render_sla_to_pdf` (Scribus), `pdftoppm → page-NN.png`, hires-PNGs.
- **CI rendert nicht** — Rendering ist ein lokaler Dev-Container-Schritt;
  `tools/gallery_build.py` ist copy-only.

### Ziel-Template
`templates/flyer-a6-hochformat-gruenes-cover/` — **6 Seiten** (`page-01..06`).
`template.sla` referenziert Schriften über `FONT="…"`-Attribute. Distinkte Fonts:
`Gotham Narrow Book/Bold/Black/Ultra`, `Minion Pro Regular`, `Vollkorn Black Italic`.
→ Font-Tausch betrifft **nur die 4 `Gotham Narrow`-Familien**. `Vollkorn` (frei)
und `Minion Pro Regular` (ebenfalls proprietär, aber **out of scope** — eigenes
Folge-Issue wert) bleiben unangetastet.

### Site-Struktur
- `site/src/pages/index.astro` — Galerie-Startseite; verlinkt `experiments/` über
  eine hervorgehobene Karte (dunkelgrün, `var(--gruen-dunkel)`).
- `site/src/pages/experiments/index.astro` — Listenseite, Astro-Content-Collection.
- `site/src/content.config.ts` — Collections `templates`, `experiments`.
- `BASE_URL` = `/vorlagen/`; `url()`-Helper strippt führende Slashes.
- Lightbox mit Navigation zwischen Previews existiert (Issue #28) in
  `site/src/pages/templates/[...id].astro` — Muster für die Font-Umschaltung.

## 2. Schrift-Recherche (Survey)

Gotham ist eine geometrische Grotesk (Hoefler & Co., inspiriert von New Yorker
Beschilderung). Das Repo nutzt **Gotham Narrow** — eine schmal laufende Fassung.
Untersuchte freie Kandidaten (alle SIL OFL = kommerzielle Nutzung + Einbettung
erlaubt, sofern nicht anders vermerkt):

| Schrift | Geometrisch | Schmal | Schnitte | Bewertung |
| :-- | :-- | :-- | :-- | :-- |
| Montserrat | ✓✓ | – | Thin–Black | engste Gotham-Nähe (~88 %) |
| Outfit | ✓✓ | – | 100–900 | sehr neutral/monolinear |
| Urbanist | ✓✓ | – | Thin–Black + Kursive | modernistisch, variabel |
| Raleway | ✓ | – | 18 Schnitte | elegant, display-stark |
| Barlow Semi Condensed | ✓ | ✓ | Thin–Black | einzige schmale Option |
| Poppins | ✓ | – | Thin–Black | runder, indisch-geprägt |
| Jost* | ✓✓ | – | 100–900 | eher Futura als Gotham |
| Metropolis | ✓✓ | – | 9 + Kursive | Gotham-nah, aber nicht auf Google Fonts |
| Gothic A1 | ✓ | – | 100–900 | brauchbar, weniger markant |

**Auswahl der 5** — Mix aus „größtmöglicher Nähe" + Abdeckung verschiedener
Charaktere, alle mit Gewichten, die Book/Bold/Black/Ultra abdecken:

### Die 5 gewählten Schriften (mit deutschen Kurz-Zusammenfassungen)

1. **Montserrat** — SIL OFL · Google Fonts
   *Warum ähnlich:* geometrische Grotesk, von Plakatschriften aus Buenos Aires
   inspiriert (wie Gotham von New Yorker Beschilderung), sehr nahe Proportionen
   (~88 % Übereinstimmung in Fachvergleichen). *Vorteile:* bekannteste freie
   Gotham-Alternative, 9 Schnitte Thin–Black, sehr breite Sprachunterstützung,
   ausgereift. *Nachteile:* läuft etwas breiter als Gotham Narrow, große x-Höhe,
   keine schmale Variante → Texte können im Layout überlaufen. *Unterschied:*
   der „klassischste", wärmste Gotham-Ersatz. *Einsatz:* Standard-Empfehlung,
   wenn größtmögliche Nähe zu Gotham gewünscht ist.

2. **Outfit** — SIL OFL · Google Fonts
   *Warum ähnlich:* rein geometrische, monolineare Konstruktion mit neutraler
   Anmutung wie Gotham. *Vorteile:* sehr aufgeräumt/modern, gleichmäßige
   Strichstärke, 9 Gewichte (100–900), display-stark. *Nachteile:* monolinear →
   wirkt kühler/technischer, weniger „Charakter"; nicht schmal. *Unterschied:*
   die sachlichste, neutralste Option. *Einsatz:* moderne, klare Gestaltung,
   Headlines und kurze Texte.

3. **Urbanist** — SIL OFL · Google Fonts
   *Warum ähnlich:* modernistische geometrische Grotesk aus elementaren Formen,
   neutral wie Gotham. *Vorteile:* variabler Font, fein abgestufte Gewichte
   Thin–Black plus Kursive, sehr vielseitig. *Nachteile:* geringerer
   Wiedererkennungswert, etwas generisch; nicht schmal. *Unterschied:* am
   stärksten web-/UI-orientiert. *Einsatz:* flexible Nutzung über viele
   Gewichte, gut wenn Kursive gebraucht werden.

4. **Raleway** — SIL OFL · Google Fonts
   *Warum ähnlich:* elegante geometrische Grotesk; gilt in Fachquellen als die
   ähnlichste Gotham-Alternative im Google-Fonts-Verzeichnis; 18 Schnitte
   Thin–Black + Kursive. *Vorteile:* sehr elegant in feinen Schnitten,
   ausdrucksstarke Headlines. *Nachteile:* in feinen Gewichten zerbrechlich,
   markante Detailformen (z. B. „w") → für 6-pt-Kleintext weniger robust; nicht
   schmal. *Unterschied:* die ausdrucksstärkste, „eleganteste" Option.
   *Einsatz:* Headlines, Cover, Display — weniger für Kleinsttext.

5. **Barlow Semi Condensed** — SIL OFL · Google Fonts
   *Warum ähnlich:* leicht schmal laufende Grotesk mit geometrisch-„kalifornischem"
   Charakter; die einzige der fünf, die der schmalen Laufweite von **Gotham
   Narrow** nahekommt. *Vorteile:* schmale Proportionen → beste Layout-Treue zum
   Narrow-Original, sehr großer Schnittumfang Thin–Black, gut lesbar auch klein.
   *Nachteile:* eher grotesk als rein geometrisch → nüchterner; semi-condensed
   wirkt weniger „luftig" als Gotham. *Unterschied:* einzige schmale Variante,
   beste Passung zur bestehenden Geometrie der Vorlagen. *Einsatz:* erste Wahl,
   wenn die Layouts ohne Umbau übernommen werden sollen.

### Gewichts-Mapping (Empfehlung)
| Gotham Narrow | Ersatz-Schnitt |
| :-- | :-- |
| Book | Regular (400) |
| Bold | Bold (700) |
| Black | ExtraBold (800) |
| Ultra | Black (900) |

### Bezugsquelle
Alle 5 Familien liegen unter SIL OFL im Repo `github.com/google/fonts`
(Pfad `ofl/<familie>/`). Die statischen `.ttf` der benötigten Schnitte + die
jeweilige `OFL.txt` werden ins Repo übernommen (D4) — OFL erlaubt Bündelung
ausdrücklich.

## 3. Out-of-scope-Beobachtung
`Minion Pro Regular` (Adobe, proprietär) wird vom Flyer ebenfalls referenziert
und blockiert striktes „frei teilbar" genauso wie Gotham. Eigenes Folge-Issue.
