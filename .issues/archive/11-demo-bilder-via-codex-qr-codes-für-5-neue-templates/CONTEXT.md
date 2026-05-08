# Design Decisions — 11-demo-bilder-via-codex-qr-codes-für-5-neue-templates

Captured 2026-05-08. Locked decisions are binding for research, plan, execute.
Discretion items can be explored by research; deferred items are out of scope.

## Decisions (locked — research/planner must follow)

### D1. QR-Stil: Branded mit Dunkelgrün-Modulen + Logo-Embed

- QR-Module in CMYK `Dunkelgrün` (85/35/95/10) auf weiß.
- Grünen-Sonnenblumen-Logo zentriert, Logo-Bedeckung max ~25% der Code-Fläche.
- `error_correction_level=H` (~30% Wiederherstellungstoleranz) — verkraftet das Logo
  und kleinere Druckbeschädigungen.
- Quiet zone (Mindestabstand zur Layout-Kante) ≥ 4 module breit.
- Module-Größe so wählen, dass im finalen Druck (Postkarte → ~25mm Kantenlänge,
  Falzflyer-Closer → ~30mm) jeder Modul-Punkt mindestens 0.5mm breit ist —
  zuverlässige Smartphone-Scan-Distanz.

**Begründung:** QR-Code wirkt im Brand-Layout zugehörig statt als generischer
Fremdkörper; H-Level Error Correction macht Logo-Embed scan-stabil.
Tests in der Implementation-Phase: scannbar von 30cm und 1m Distanz auf je einem
iOS- und einem Android-Standardscanner.

### D2. Portrait-Stil: Photorealistisch + sichtbare Demo-Markierung

- DALL·E-3 Modell, hohe Qualität.
- Halbportrait (Schulter-aufwärts), warmes Tageslicht, neutraler bis grünlicher
  Hintergrund (out-of-focus, nicht solid).
- Diversity über Kandidat:innen-Set: variierend Alter (30er, 40er, 50er),
  Geschlecht (gemischt), erkennbar mitteleuropäisch — österreichischer Kontext
  („urban Wien", „ländlich NÖ", nicht US-Suburbia).
- **Demo-Markierung sichtbar:** kleines unaufdringliches Caption-Label am unteren
  Bildrand „Symbolfoto — Demo" (nicht verzerrend in Kompositionen, aber für
  Reviewer:innen sichtbar). Plus manifest.yml `synthetic: true` und `note:`-Feld.
- Output: JPG, ~2048px lange Kante, sRGB → Scribus konvertiert nach CMYK beim PDF-
  Export.

**Begründung:** Photorealismus liefert die gewünschte Galerie-Wirkung („sieht aus
wie Kampagnen-Material"); Demo-Caption schützt vor unbeabsichtigter Verwendung als
echtes Politiker:innen-Foto durch nachfolgende Nutzer:innen.

### D3. Demo-URLs: Echte Grünen-NÖ-URLs

- Postkarte → `https://noe.gruene.at/` (Hauptseite, garantiert live)
- Türanhänger → `https://noe.gruene.at/themen/` (Themenübersicht)
- Falzflyer-Closer (1–2 QRs) → je `https://noe.gruene.at/mitmachen/` und
  `https://noe.gruene.at/termine/` — beide live laut [noe.gruene.at](https://noe.gruene.at/)
- Tent-Card-Mitmachen → `https://noe.gruene.at/mitmachen/`
- Themen-Plakat (optional) → `https://noe.gruene.at/themen/klimaschutz/` (research soll prüfen ob URL existiert; sonst nächst-allgemeine Themen-URL)

**Begründung:** Reviewer:innen können scannen und sehen funktionierende Galerie-
Demo. Endnutzer:innen überschreiben die URL beim Kampagnen-Einsatz mit ihrer
Bezirks-/Listen-URL. Pre-flight Phase: `curl -I` auf alle 5 URLs, jede muss 2xx
liefern; falls nicht, in research dokumentieren und auf nächst-allgemeine URL
fallback'en.

### D4. QR-Library: Python `qrcode` (NICHT system-`qrencode`)

- `pip install qrcode[pil]` — dependency wird in `requirements-dev.txt`/wo passend
  ergänzt.
- Reine Python-Implementierung, deterministisch, hat saubere API für Module-Farbe,
  Logo-Embed, Error-Correction-Level.
- System-`qrencode` (CLI) wäre Alternative, aber:
  - Keine deterministischen Farb-Renderings out-of-the-box
  - Logo-Embed erfordert separate Pillow-Schritte sowieso
  - Eine Library-Abhängigkeit (`qrcode`) statt zwei (System-`qrencode` + Pillow) ist
    sauberer

**Pillow:** Für QR-Logo-Composite + Caption-Watermark auf Codex-Portraits brauchen
wir doch Pillow. Issue #10 hatte D7 explizit auf montage statt Pillow gepivot't —
aber für Bild-Manipulation (Logo-Overlay, Text-Watermark) ist Pillow das
Standard-Tool. Wir installieren es jetzt als reguläre Dependency. Der Argument von
Issue #10 (D7) war Composite-Grid-Layout — das geht mit montage. Für Per-Pixel-
Manipulation auf Demo-Bildern ist Pillow richtig. **Wir fügen Pillow als
Dev-Dependency hinzu.**

### D5. Manifest-Schema: erweitern, nicht neu

- Existierendes `templates/<slug>/samples/manifest.yml` (von Issue #10) erweitern,
  keine neue Datei.
- Schema-Erweiterung um:
  - `images:` Liste (Codex-DALL·E-generated)
    - `name`, `prompt`, `size`, `synthetic: true`, `note`, `output_path`,
      `model: dall-e-3`, `quality: hd`
  - `qr_codes:` Liste (qr_gen.py-generated)
    - `name`, `target_url`, `output_path`, `module_color`, `embed_logo`, `error_correction`,
      `module_size_pt` (ableitbar aus `pixel_size` und `dpi`)
- Beide Listen werden von ihrem jeweiligen Tool gelesen; kein Cross-Coupling.
- Existierende Templates ohne manifest.yml bekommen eine angelegt mit nur den
  Slots, die sie tatsächlich brauchen.

### D6. Output-Format & Inline-Embed

- Codex-Portraits: **JPG** (file size, photorealistic content), ~80% Quality.
  Scribus-Inline via existierendem `pack_inline_image()` Helper aus Issue #10.
- QR-Codes: **PNG** (lossless, scannbar wichtig). Ebenfalls inline base64.
- Beide in `<slug>-preview.sla` eingebaut, NICHT in `template.sla` (slot-based-
  Konvention aus Issue #10 bleibt).

### D7. Iterations-Cap pro Codex-Portrait

- Max **5 Generierungs-Versuche** pro Portrait-Slot. Nach 5 Versuchen ohne
  brauchbares Resultat: Slot leer lassen, manifest.yml notiert „generation failed,
  manual fallback needed", Issue-Owner entscheidet später.
- Brauchbarkeitskriterien (im manifest.yml dokumentiert):
  - Halbportrait, kein Ganzkörper, kein Pop-Art-Stil
  - Hintergrund unkonkret (kein Logo, kein erkennbarer Brand-Konkurrent)
  - Kein offensichtlich künstliches Gesicht (Uncanny Valley)
  - Kleidung neutral (kein anderes Parteilogo, keine Sport-Trikots)
- Mensch (Issue-Owner oder PR-Reviewer:in) trifft die finale „brauchbar"-Entscheidung
  beim PR-Merge.

### D8. Anzahl Demo-Bilder pro Template (Scope-Cap)

Um Codex-Kosten und Zeit zu beschränken:
- `kandidat-falzflyer-din-lang`: 1 Portrait + 3 Themen-Bilder = 4 Codex-Calls
- `themen-plakat-a3-quer`: 1 Themen-Bild = 1 Codex-Call
- `infostand-tent-card-a5-quer`: 1 Hintergrund-Foto (optional, low-priority) = 0–1 Calls
- Postkarte/Türanhänger: keine Codex-Calls (nur QR + Wahlkreuz, schon vorhanden)

**Total: 5–6 Codex-DALL·E-Calls.** Bei DALL·E-3 HD ~$0.08 pro Bild → ~$0.50.
Mit Iterationen (Cap 5 Versuche × 6 Bilder × $0.08) maximal ~$2.40. Im Budget.

### D9. QR-Generierungs-Determinismus

- `qr_gen.py` erzeugt byte-identisches PNG bei identischem Input (URL, version,
  error_correction, module_color, embed_logo).
- Tests verifizieren via `hashlib.sha256` über Output-Bytes.
- Verhindert „QR ändert sich bei jedem Build" → Repo-Bytes stabil → Round-Trip-
  Diff bleibt grün.

### D10. Visual-QA Light für dieses Issue

- KEIN volles 3-Gate-Setup wie Issue #10 (overkill für Polish-Issue).
- **Ein einziger Visual-Review-Pass** am Ende über die aktualisierten Galerie-Previews
  via `tools/visual_review.py` (existiert seit #10).
- Fokus: „sehen die neuen Templates mit echten Bildern + funktionalen QRs sichtbar
  besser aus als die Platzhalter-Version?"
- Findings adressieren oder begründen, dann PR.

### D11. Scope-Cleanliness: nur Demo-Content, keine Logo-Replacement

- **NICHT in scope:** Brand-quality DIE GRÜNEN Logos (das war Post-Merge-Followup
  Punkt 1 aus Issue #10) — eigenes Issue.
- **NICHT in scope:** spec_check.py-Toleranz-Tuning (Punkt 3) — eigenes Issue.
- Dieses Issue bleibt fokussiert auf: Codex-Portraits + QR-Codes + Galerie-Refresh.

---

## Claude's Discretion (research should explore options)

- **`qrcode`-Library-Version-Pin** — current stable, reproducible builds.
- **Codex-DALL·E-Prompt-Template-Granularität** — wie viel Detail im Manifest
  reicht, um reproduzierbare Bilder zu bekommen?
- **Caption-Watermark-Position auf Portraits** — unten-rechts mit dunkler
  Halbtransparenz vs unten-Mitte vs als Banner-Overlay. Welche Position stört
  Galerie-Wirkung am wenigsten?
- **Logo-Variante im QR-Center** — vollfarb-Sonnenblume vs monochrom Dunkelgrün-
  Sonnenblume. Welches scannt zuverlässiger?
- **`<slug>-preview.sla`-Build-Trigger** — als separater `bin/`-Script vs. Erweiterung
  von `bin/render-gallery`?
- **Manifest-Validation** — JSON-Schema in `tools/manifest_check.py` oder reicht
  die Self-Validation in den Tools?

---

## Deferred (out of scope for this issue)

- **Logo-Replacement**: Brand-quality Vektor-Logos statt Platzhalter (eigenes Issue).
- **spec_check.py-Tolerance-Tuning** (eigenes Issue).
- **QR-Generation in CI**: bleibt One-shot lokal, wie Codex-Generation.
- **Animated/Lottie/SVG-Demo-Content** — JPG/PNG reicht.
- **Echte Kandidat:innen-Fotos** — Endnutzer:innen liefern selbst.
- **Mehrsprachige Demo-URLs** — DE-only.

---

## Cross-References

- Issue #10 (PR #20, merged) — `tools/codex_image_gen.py` framework, manifest-
  Konvention, `<slug>-preview.sla`-Pattern alle bereits live.
- D11 + D12 aus #10 (Codex-Demo-Image-Generation; Wahlkreuz-Background) — dieses
  Issue ist die Aktivierung von D11 + Erweiterung um QR-Codes.
- Memory: `feedback_no_claude_attribution` — keine Claude-Branding in
  Generated-Content/Code/Commits.
- Memory: `feedback_thorough_reviews` — Visual-Review-Pass am Ende braucht
  Tiefe, nicht nur „sieht ok aus".
