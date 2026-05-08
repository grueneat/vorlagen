---
id: '13'
title: Zentralisierte Demo-Bild-Bibliothek + alle Templates auffüllen
status: open
priority: high
labels:
- templates
- demo-content
source: github
source_id: 24
source_url: https://github.com/GrueneAT/vorlagen/issues/24
---

## Kontext

Issue #11 (PR #22) hat das Demo-Image-Framework (Codex-Generation, qr_gen, Symbolfoto-Watermark, conditional inject) etabliert und 6 Bilder + 6 QR-Codes für die 5 neuen Templates generiert. **Dabei wurde D11 von #11 absichtlich „template-spezifisch, kein Cross-Reuse" gewählt.** Diese Entscheidung wird hier reversiert.

Aktueller Zustand der Galerie:

| Template | Demo-Bilder vorhanden? | Empty Slots? |
|---|---|---|
| postkarte-a6-kampagne (production) | nein | ja (Hero, Logo) |
| plakat-a1-hochformat (production) | nein | ggf. |
| zeitung-a4-grun (production) | nein | ja (mehrere Themen-Slots, Cover-Bild, Foto-Spread) |
| themen-plakat-a3-quer (neu) | 1 Themen-Hero + 1 QR | ggf. weitere optional |
| wahlaufruf-postkarte-a6-quer (neu) | 1 QR | keine Bild-Slots |
| wahltag-tueranhaenger (neu) | 1 Portrait + 1 QR | keine offenen |
| infostand-tent-card-a5-quer (neu) | 1 Hintergrund + 1 QR | ggf. |
| kandidat-falzflyer-din-lang (neu) | 1 Portrait + 3 Themen + 2 QR | keine offenen |

5 von 8 Templates haben Bilder, 3 nicht. Die Galerie wirkt dadurch inkonsistent — die Production-Templates wirken im direkten Vergleich „älter / weniger fertig" als die neuen.

Plus: aktuell hat jedes Template einen eigenen `samples/` Ordner. Wenn fünf Templates ein Klimaschutz-Themen-Foto brauchen, würden fünf separate Codex-Generierungen anfallen. Das skaliert nicht.

## Scope

**Zwei eng gekoppelte Lieferungen:**

### A — Zentralisierte Demo-Bild-Bibliothek

- Neuer Pfad: `shared/sample-images/` (oder `shared/demo-content/`) als zentraler Pool für **wiederverwendbare** Demo-Bilder.
- Bilder kategorisiert: `portraits/` (Kandidat:innen-Köpfe), `themen/` (Klimaschutz, Soziales, Bildung, Wirtschaft, Bauernhof, Verkehr, …), `kontext/` (Infostand-Szene, Bürger:innen-Versammlung, Café-Stammtisch, …).
- Manifest pro Bibliothek-Eintrag: Pfad, Codex-Prompt, Beschreibung, Tags („portrait, female, 40s, business-casual"), `synthetic: true`, License-Note.
- Jedes Bild hat den Symbolfoto-Watermark wie heute (per `tools/codex_image_gen.py` post-process).
- Zentraler `shared/sample-images/manifest.yml` listet alle Bilder mit Metadaten, sodass `tools/codex_image_gen.py --regen-all` die ganze Bibliothek bei Bedarf neu generieren kann (deterministisch reproduzierbar).
- Templates referenzieren via relativer Pfad (`shared/sample-images/portraits/maria-beispiel.jpg`) — `pack_inline_image()` macht den Rest.

### B — Alle 8 Templates auffüllen

- Pro Template Slot-Audit: welche image-bearing `ImageFrame`s sind aktuell empty?
- Jeder empty Slot bekommt einen passenden Bild-Vorschlag aus der zentralen Bibliothek. Wenn kein passendes Bild vorhanden, **neues generieren und in die Bibliothek aufnehmen** (nicht template-spezifisch unter `templates/<slug>/samples/`).
- Conditional-inject Pattern aus #11 bleibt: build.py prüft `if (asset.exists()): embed`, sonst leerer Slot. Bibliothek-Pfade sind absolute paths relativ zum Repo-Root, nicht relativ zum Template.
- **Production-Templates (postkarte/plakat/zeitung)** auch — aber **mit Round-Trip-Garantie**: das hash-stabile conditional-inject Pattern (Bild bytes deterministisch in committed PNG) muss sicherstellen dass Original-vs-Built-SLA-Diff grün bleibt. Wenn das nicht möglich ist (z.B. weil die 3 Originals bewusst andere Bytes haben), Original behalten und nur die Galerie-Preview-PNG mit Demo-Inhalt rendern (`<slug>-preview.sla` Pattern wieder einführen, diesmal richtig — anders als #11 wo das Pattern nicht existierte).
- Per-Template `samples/manifest.yml` wird vereinfacht: statt eigener Bilder verweist es auf Bibliothek-Einträge per ID. Beispiel:
  ```yaml
  uses_from_library:
    - id: portrait_maria
      anname: "P1 Kandidat-Portrait"
    - id: themen_klimaschutz_solar
      anname: "P2 Themen Klima"
  ```

### Migration aus #11

- `templates/kandidat-falzflyer-din-lang/samples/portrait-cover.jpg` → `shared/sample-images/portraits/maria-beispiel.jpg`. Falzflyer-Manifest verweist auf Library-ID.
- Andere bestehende Bilder analog.
- Alte template-spezifische `samples/`-Ordner werden entfernt nach Migration; nur Manifest mit Library-Referenzen bleibt im Template.

## Constraints

- **Round-trip-Diff bleibt grün** auf den 3 Production-Templates. Falls die Inkubation in `template.sla` das gefährdet, separater `template-preview.sla` Pfad (siehe unten) — nur Preview-PNG bekommt Demo-Inhalt.
- **D11 von #11 wird hier explizit reversiert** — Bilder werden über Templates hinweg geteilt. Begründung: Skalierung (50 Templates × 6 Bilder × Codex-Cost wäre absurd) und visuelle Konsistenz (gleiche fiktive Person als wiederkehrender „Kandidat:innen-Archetyp" erkennbar).
- **`<slug>-preview.sla` Pfad richtig implementieren** falls für Production-Templates nötig: build.py emittiert zwei SLAs — `template.sla` (clean, slot-based, end-user reads this) und `template-preview.sla` (with library images injected, gallery render reads this). check-stale-previews trackt template.sla SHA, `bin/render-gallery` rendert preview.sla wenn vorhanden.
- **Library-Wachstum auditiert**: jeder neue Bild-Eintrag in der Library braucht Manifest-Eintrag mit Tags + Verwendung-Hinweis. Verhindert Wildwuchs.
- **Symbolfoto-Watermark** auf allen Codex-generierten Bildern weiter Pflicht (EU AI Act).
- **Brand-Konformität**: alle Bilder müssen Quickguide-„Bilder mit grünem Brand-Akzent / Person vor Grün-Hintergrund / Freisteller"-Regel folgen.
- **Keine Claude-Attribution** in commits/code/manifest.

## Acceptance Criteria

- [ ] `shared/sample-images/` existiert mit Unterordner-Struktur (portraits/, themen/, kontext/) und einem zentralen `manifest.yml`
- [ ] Mindestens **2 Portraits** (1m, 1w) + **6 Themen-Bilder** (Klimaschutz, Soziales, Bildung, Wirtschaft, Bauernhof, Verkehr) + **3 Kontext-Bilder** (Infostand, Versammlung, Café) in der Bibliothek
- [ ] Alle Bilder Symbolfoto-Watermarked, JPEG q=80, 1024–2048px lange Kante
- [ ] `tools/codex_image_gen.py` erweitert um Bibliothek-Modus: `--library shared/sample-images/manifest.yml` regeneriert die Bibliothek
- [ ] Bestehende template-spezifische `samples/*.jpg` migriert nach `shared/sample-images/`; alte `samples/`-Ordner enthalten nur noch Manifest-mit-Library-Referenzen + ggf. QR-Codes (die bleiben template-spezifisch wegen URL-Bindung)
- [ ] Alle 8 Templates: jedes empty image slot ist mit einer Bibliothek-Referenz gefüllt ODER bewusst empty gelassen mit Begründung in der Spec
- [ ] `bin/render-gallery <slug>` rendert für alle 8 Templates Previews mit eingebetteten Demo-Bildern; `template.sla` für Production-Templates bleibt round-trip-stabil (separates `template-preview.sla` falls nötig)
- [ ] `tools/check_ci.py` + `tools/sla_diff.py` (round-trip) + `bin/check-stale-previews` grün auf allen 8 Templates
- [ ] Galerie zeigt alle 8 Templates mit konsistenter Demo-Bild-Atmosphäre — Production-Templates wirken nicht mehr „älter"
- [ ] Visual Review (single pass via `tools/visual_review.py --all`): Konsens „all 8 templates merge-ready, gallery konsistent"
- [ ] Library-Manifest dokumentiert pro Bild: Codex-Prompt, Tags, License-Note (synthetisch demo-only)

## Risiken & Open Questions

- **`<slug>-preview.sla` Pattern korrekt aufsetzen** — diesmal richtig. In #11 war das nicht implementiert (nur conditional inject in template.sla). Production-Templates brauchen es wenn round-trip nicht stabil bleibt.
- **Library-Pfad-Resolution** — absolute repo-paths vs. relative-from-template-root. Codex-image-gen muss verstehen wo es schreibt; build.py muss verstehen wo es liest.
- **Image-License**: synthetische Codex-Bilder gelten als generated content; OpenAI-TOS erlaubt kommerzielle Verwendung. Library-manifest dokumentiert das pro Bild explizit.
- **Bestehende Codex-Bilder in `templates/<slug>/samples/` evtl. nicht 100% library-tauglich** — z.B. das Falzflyer-Maria-Beispiel-Portrait ist sehr spezifisch (dunkler Blazer, Café-Hintergrund). Bibliothek-Brauchbar oder neu generieren?
- **Production-Template-Slot-Audit** — postkarte/plakat/zeitung haben evtl. Slots die wir nicht erkannt haben. Discuss-/Research-Phase muss das systematisch durchgehen.
- **Templating-Tags** — wie expressive sollen Tags sein („portrait" vs „portrait/female/40s/casual/austrian"). Trade-off Granularität vs Pflege-Aufwand.

## Phasenvorschlag

1. **Phase 1 — Library-Schema + Migration**
   - Schema für `shared/sample-images/manifest.yml`
   - Bestehende Bilder migrieren
   - `codex_image_gen.py` Library-Modus
2. **Phase 2 — Template-Slot-Audit**
   - Pro Template inventarisieren: welche image-bearing Slots, welche heute empty
   - Mapping: welcher Slot bekommt welches Library-Bild (oder neu generieren)
3. **Phase 3 — Library-Wachstum**
   - Fehlende Bilder via Codex generieren und in Library aufnehmen
4. **Phase 4 — Template-build.py-Updates**
   - Conditional inject auf Library-Pfade umstellen
   - Production-Templates: ggf. `<slug>-preview.sla` Pattern einführen
5. **Phase 5 — Re-render + Visual Review**
   - Alle 8 Templates rerendern
   - Visual review Pass
6. **Phase 6 — PR + Merge**

## Dependencies

- Issue #11 (gemerged) — Codex-Pipeline, qr_gen, Symbolfoto-Watermark, conditional-inject Pattern als Foundation
- **Blockt Issue #12** (Spec-System v2 / Constraint-DSL): user direktiv „mache hier noch einen issue einschub davor". #12 wartet bis dieses Issue gemerged ist.
