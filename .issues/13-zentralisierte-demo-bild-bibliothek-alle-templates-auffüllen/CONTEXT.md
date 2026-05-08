# Design Decisions — 13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen

Captured 2026-05-08. Locked decisions are binding for research, plan, execute.

## Decisions (locked)

### D1. Library-Struktur: Per-Kategorie-Unterordner + zentrales Master-Manifest

```
shared/sample-images/
├── manifest.yml               # zentral, indexiert alle Bilder
├── portraits/
│   ├── maria-beispiel.jpg
│   └── stefan-beispiel.jpg
├── themen/
│   ├── klimaschutz-solar.jpg
│   ├── klimaschutz-windrad.jpg
│   ├── soziales-gemeindebau.jpg
│   ├── bildung-schule.jpg
│   ├── bildung-volksschule.jpg
│   ├── wirtschaft-handwerk.jpg
│   └── verkehr-radweg.jpg
├── kontext/
│   ├── infostand-szene.jpg
│   ├── buergerversammlung.jpg
│   └── stammtisch-cafe.jpg
└── qr/
    └── (template-spezifisch — siehe D9)
```

**Begründung:** Ordner-Hierarchie reflektiert Verwendung — Authoring findet Bilder
schnell. Master-Manifest zentralisiert Metadaten (Tags, Codex-Prompt, License-Note,
synthetisch-Flag) sodass `tools/codex_image_gen.py --library` die Bibliothek
deterministisch regenerieren kann. Skaliert auf 50+ Bilder ohne Restrukturierung.

**Manifest-Format** (`shared/sample-images/manifest.yml`):
```yaml
images:
  portrait_maria:
    path: portraits/maria-beispiel.jpg
    prompt: |
      Professional half-portrait of a woman in her early 40s,
      shoulder-length brown hair, dark green blazer over white blouse,
      warm Austrian community space background...
    tags: [portrait, female, 40s, kandidatin, austrian]
    synthetic: true
    license_note: "AI-generated demo image; not a real person."
    size: "1024x1536"
    watermark: "Symbolfoto — KI-generiert"

  portrait_stefan:
    path: portraits/stefan-beispiel.jpg
    prompt: |
      Professional half-portrait of a man in his early 50s,
      grey hair, dark sweater, friendly engaged expression...
    tags: [portrait, male, 50s, kandidat, austrian]
    synthetic: true
    license_note: "AI-generated demo image; not a real person."
    # ... etc

  themen_klimaschutz_solar:
    path: themen/klimaschutz-solar.jpg
    # ... etc
```

### D2. Reference-API: `library.load("id")`

Neuer Helper unter `tools/sla_lib/builder/library.py` (oder ähnlich):

```python
from sla_lib.builder import library

# In build.py:
portrait = library.load("portrait_maria")  # returns LibraryImage with .bytes, .path, .meta
if portrait is not None:
    data, ext = pack_inline_image(portrait.bytes, "jpg")
    page.add(ImageFrame(
        x_mm=6, y_mm=28, w_mm=87, h_mm=105,
        inline_image_data=data, inline_image_ext=ext,
        scale_type=0, ratio=1, layer=LAYER_BILDER,
        anname="P1 Kandidat-Portrait",
    ))
```

**API-Klasse:**
```python
@dataclass
class LibraryImage:
    id: str
    path: Path
    bytes: bytes
    meta: dict   # tags, prompt, synthetic, license_note, size

def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]:
    """Resolve a library image by ID. Returns None if optional and missing.
    Raises LibraryError if required and missing — fail-fast at build time."""

def all_images() -> dict[str, LibraryImage]:
    """All known library images, keyed by ID."""

def regenerate(id: str, *, force: bool = False) -> bool:
    """Re-run Codex generation for one image based on manifest prompt.
    Used by tools/codex_image_gen.py --library."""
```

**Begründung:** ID stabil über Pfad-Refactoring; zentrale Validierung beim Build
(unbekannte ID = fail-fast); Templates referenzieren über semantische Namen statt
fragile Pfade. Integration mit `pack_inline_image()` aus #11.

### D3. Production-Templates: `<slug>-preview.sla` separater file

Pattern (richtig diesmal — in #11 nicht implementiert):

```python
# In templates/postkarte-a6-kampagne/build.py (Beispiel):
def build_template():
    """Clean template for end users — slot-based, no demo content."""
    doc = Document(...)
    # ... empty image slots
    return doc

def build_preview():
    """Gallery preview — same as build_template() PLUS library demo content."""
    doc = build_template()
    # inject library images into the empty slots
    ...
    return doc

if __name__ == "__main__":
    build_template().save(HERE / "template.sla")
    build_preview().save(HERE / "template-preview.sla")
```

**Render-Pipeline-Erweiterung** (`tools/render_pipeline.py`):
- Wenn `templates/<slug>/template-preview.sla` existiert → Galerie-PDF/PNG-Render
  daraus.
- Sonst → fallback auf `template.sla`.
- `bin/check-stale-previews` trackt SHA von `template.sla` (clean), NICHT von
  `template-preview.sla` (preview ist abgeleitet).
- `tools/sla_diff.py` Round-Trip prüft `template.sla` (= original-equivalent),
  unverändert.

**Begründung:** Production-Templates behalten Round-Trip-Garantie unverändert;
End-User-Workflow (Vorlage öffnen, eigene Bilder einfügen) bleibt slot-basiert;
Galerie-Wirkung wird konsistent mit Demo-Content. Best-of-both.

### D4. Tags-Schema (semi-strukturiert)

Pflicht-Tag pro Bild: **Kategorie** (`portrait`, `themen`, `kontext`, `qr`).
Empfohlene Tags:
- Portrait: `gender:female|male|nonbinary`, `age:20s|30s|40s|50s|60s+`,
  `setting:office|outdoor|cafe|community`, `kandidat:in?` (boolean implicit by
  `kandidat`/`kandidatin` tag), `austrian` (Brand-Standort)
- Themen: `topic:klimaschutz|soziales|bildung|wirtschaft|verkehr|wohnen|gesundheit`,
  `subtopic:` (z.B. `solar`, `windrad`, `radweg`, `gemeindebau`),
  `composition:landscape|portrait|square`
- Kontext: `scene:infostand|versammlung|stammtisch|kundgebung|wahllokal`

Tags rein zur Discovery, kein Constraint. Library-Suche via `library.find(tags=["portrait", "female"])` als Bonus-API.

### D5. License-Note pro Bild (synthetisch, demo-only)

Jedes Library-Bild hat in seinem Manifest-Eintrag:
```yaml
synthetic: true
license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
```

Der Symbolfoto-Watermark im Bild selbst kommuniziert dasselbe an Endnutzer:innen.

### D6. Regenerate-All-Mechanik

`tools/codex_image_gen.py` erweitert um Library-Modus:
```bash
python3 tools/codex_image_gen.py --library shared/sample-images/manifest.yml
```
- Liest Master-Manifest
- Pro Bild: prüft ob `path` existiert + frischer als manifest mtime → skip; sonst
  regeneriert via Codex
- Watermark wird automatisch nach Generierung angewandt
- `--force` regeneriert alles unabhängig

`--single <id>` regeneriert nur einen Eintrag.

### D7. Aspect-Ratio-Handling beim Embed

Library-Bild wird in seiner nativen Aspect-Ratio gespeichert (z.B. 1024×1536
hochformat für Portrait). Wenn ein Template einen Slot anderer Ratio hat (z.B.
85×60mm querformat themen-thumbnail), **build.py macht das Cropping zur
Build-Zeit** via Pillow:

```python
img = library.load("themen_klimaschutz_solar")
cropped_bytes = library.crop_for_frame(img, target_w_mm=85, target_h_mm=60)
data, ext = pack_inline_image(cropped_bytes, "jpg")
```

`library.crop_for_frame()` macht center-crop auf Ziel-Ratio + Skalierung auf
Drucker-DPI (~300dpi → Pixel-Größe an Frame-mm gekoppelt). Bytes sind
deterministisch.

**Alternative für Spezialfall:** wenn ein Template ein bestimmtes Crop braucht
(z.B. nur Gesicht ohne Hintergrund), Library kann Crop-Hint im Manifest haben
(`crop_box: [x, y, w, h]`) und `library.crop_for_frame(img, hint="face")`
respektiert es.

### D8. Migration aus #11 — keep IDs that exist, rename for consistency

Bestehende Bilder aus #11:
- `templates/kandidat-falzflyer-din-lang/samples/portrait-cover.jpg` → `shared/sample-images/portraits/maria-beispiel.jpg` mit ID `portrait_maria`
- `templates/wahltag-tueranhaenger/samples/portrait-back.jpg` → `shared/sample-images/portraits/stefan-beispiel.jpg` mit ID `portrait_stefan`
- `templates/kandidat-falzflyer-din-lang/samples/themen-klimaschutz.jpg` → `shared/sample-images/themen/klimaschutz-solar.jpg` mit ID `themen_klimaschutz_solar`
- `templates/kandidat-falzflyer-din-lang/samples/themen-soziales.jpg` → `shared/sample-images/themen/soziales-gemeindebau.jpg` mit ID `themen_soziales_gemeindebau`
- `templates/kandidat-falzflyer-din-lang/samples/themen-bildung.jpg` → `shared/sample-images/themen/bildung-volksschule.jpg` mit ID `themen_bildung_volksschule`
- `templates/themen-plakat-a3-quer/samples/themen-hero.jpg` → `shared/sample-images/themen/klimaschutz-windrad.jpg` mit ID `themen_klimaschutz_windrad`
- `templates/infostand-tent-card-a5-quer/samples/hintergrund-mitmachen.jpg` → `shared/sample-images/kontext/infostand-szene.jpg` mit ID `kontext_infostand_szene`

QR-Codes bleiben **template-spezifisch** unter `templates/<slug>/samples/qr-*.png` — sie sind URL-gebunden und nicht cross-template wiederverwendbar.

### D9. QR-Codes bleiben template-spezifisch

QR-Codes kodieren template-spezifische URLs (Postkarte → `noe.gruene.at/`,
Türanhänger → `noe.gruene.at/themen/`, etc.). Cross-Reuse macht keinen Sinn.
Bleiben unter `templates/<slug>/samples/qr-*.png` mit per-template
`qr_codes_manifest.yml`.

### D10. Mindestens 12 Bilder in der Bibliothek nach Migration + Generierung

Nach Migration aus #11 (7 Bilder) + Neu-Generierung (5+ Bilder) ergeben sich
mindestens:

**Portraits (2):** maria-beispiel, stefan-beispiel
**Themen (7+):**
- klimaschutz-solar (Solaranlage auf Hausdach)
- klimaschutz-windrad (existing)
- soziales-gemeindebau
- bildung-volksschule (existing)
- bildung-erwachsenenbildung (NEU)
- wirtschaft-handwerk (NEU)
- verkehr-radweg (NEU)
- (optional weitere)
**Kontext (3):**
- infostand-szene (existing)
- buergerversammlung (NEU)
- stammtisch-cafe (NEU)

Total ~12-13 Bilder. Cost: ~5 neue × $0.08 = $0.40 zusätzlich. Acceptable.

### D11. Production-Templates (postkarte/plakat/zeitung) erstmal `template-preview.sla` ohne Round-Trip-Risiko

Audit per Production-Template welche Slots Demo-Content vertragen würden:

- **postkarte-a6-kampagne**: Hero-Bild-Slot (wenn vorhanden) → Library-Bild;
  ggf. Logo (bleibt brand-Logo)
- **plakat-a1-hochformat**: Hero-Bild-Slot → Library-Bild
- **zeitung-a4-grun**: Cover-Bild + 2-3 Themen-Bilder im Inneren →
  Library-Bilder; Foto-Spread-Seite → 2-4 Library-Bilder

Discuss/Research-Phase ist verantwortlich für detailliertes Slot-Inventar.

### D12. Sequencing-Hinweis: Issue #12 (Spec-System v2) wartet

Per Issue-Body: Issue #12 (Constraint-DSL etc.) wird hier blockiert. Nach Merge
dieser Issue kann #12 starten und gegen die gemigrte Library-Welt refactor'n.

---

## Claude's Discretion

- **Pillow-Crop-Algorithmus** — saliency-aware crop vs simple center-crop. Center-crop reicht zunächst.
- **Library-Helper-Modul-Position** — `tools/sla_lib/builder/library.py` vs `tools/library.py`. Research-Phase entscheidet basierend auf Modul-Konventionen.
- **Tags-Validation** — strict (vordefinierte Liste, fail bei unknown tag) vs. permissive (alle strings ok). Permissive zunächst, hardening später.
- **`<slug>-preview.sla` Hash in meta.yml** — eigenes Feld `previews_for_preview_sla:` oder gar nicht tracken (nicht kritisch). Plan entscheidet.
- **Library-Manifest-Schema-Validation** — JSON Schema vs. ad-hoc Python checks. JSON Schema if jsonschema verfügbar, sonst ad-hoc.

## Deferred

- Image-suchen-UI in der Galerie (Tag-Filter etc.)
- Library-Bilder in Brand-Constraint-Validation einbinden (Issue #12 Sache)
- Echte Kandidat:innen-Fotos (Endnutzer:innen-Aufgabe)
- Stock-Image-Integration aus externen Quellen
- Bibliothek-Versionierung (jedes Bild mit Versionsnummer für reproducibility)

---

## Cross-References

- Issue #11 (gemerged) — Demo-Image-Framework Foundation, Codex-Pipeline, qrcode/Pillow-Deps
- Issue #12 (#23 auf GitHub, OPEN) — wartet bis dies merged
- Memory: `feedback_no_claude_attribution`
