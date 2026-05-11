---
id: '34'
title: MVP zu produktionsreifem Experimentier-System (German-first, multi-rater, lifecycle,
  ops tooling)
status: open
priority: high
labels:
- enhancement
- templates
- visual-qa
- documentation
source: github
source_id: 70
source_url: https://github.com/GrueneAT/vorlagen/issues/70
---

## Context

Issues #29–#33 lieferten ein MVP-Experimentier-System:
- **#29:** Pairwise-Voting MVP (Hypothesen → Varianten → Render → Voting → Aggregator). Hatte einen falschen Constraint-Envelope: Varianten verletzten Basis-Margins/Spacing. Identifizierte 12 v1-Hypothesen als Anti-Examples.
- **#30:** Constraint Envelope + `experiments` Skill + v2 Lauf. Render-Gate gates jede Variante gegen alle 16 `BRAND_CONSTRAINTS` + 22 Layer-1 Regeln. `tools/experiment_envelope.py` + `bin/experiment-codegen`. v2 produzierte 21 valide Varianten (1 gedroppt, 4,5% drop rate).
- **#31:** Click-to-Rank Voting-UI (Versus-Modus entfernt). SortableJS + ▲/▼ Buttons, dedizierter Checkmark-Button (verhindert Lightbox-Click-Konflikt). Single-Axis-Ranking.
- **#32:** Tent-Card-Panel-Orientierung (Panel A rotation_deg=180), Galerie-Dedup (hires aus glob filter), Experiments-Nav-Link. Follow-Up: Panel B un-rotation. Follow-Up: schwarze Falzmarkierung sichtbar.
- **#33:** E-Mail-Einreichung (mailto + Zwischenablage + Inline-Ansicht). Body-Format hybrid: human-readable Liste + `VOTE-JSON-START`/`VOTE-JSON-END` Marker. Aggregator-Flag `--from-emails`. Empfänger hardgecodet `florian.motlik@gruene.at`.

**Stand der Deployments:** Alle 5 MVPs sind gemerged und live auf https://grueneat.github.io/vorlagen/. Voting-Seite funktioniert auf Mobile + Desktop. `experiments`-Skill (`.claude/skills/experiments/SKILL.md`) ist installiert und kapselt den Workflow.

**Stand der Verwendung:** Bisher nur Flo als Rater. Das deferred T-final aus #29/#30/#31/#33 ist immer noch offen — ein echtes End-to-End-Experiment mit Korpus-Update wurde noch nicht durchgeführt. Dieses Issue ist die Voraussetzung dafür.

## Vision

Ein System, das von echten Grüne-Kampagnen genutzt wird, um Design-Entscheidungen für Kandidat:innen-Materialien zu treffen. **Mehrere Personen pro Experiment stimmen ab**, Ergebnisse fließen in echte gedruckte Materialien ein, der Korpus wächst kontinuierlich. Das System ist nutzbar für Nicht-Techniker:innen (Kandidat:innen, Designer:innen, externe Voter:innen), nicht nur für Flo.

## Kern-Anforderung: ALLES AUF DEUTSCH

Das ist die wichtigste Anforderung dieses Issues. Aktuell ist vieles auf Englisch oder gemischt:

| Bereich | Aktuell | Soll |
|---|---|---|
| Experiment-Titel | "Falzflyer P2 'Mein Plan' — pairwise voting" | komplett deutsch |
| Variant-Slugs | `numbered-priority-list-v2` (kebab-case englisch) | **bleiben englisch** (Identifier); Anzeigenamen separat deutsch |
| Hypothesen-Beschreibungen / Rationales | englisch | deutsch |
| Variant-Inhalte (Headlines, Body, Captions) | Panel A: DE; Panel B: EN (Fehler vom v2-Lauf) | komplett deutsch, beide Panels DE |
| Voting-Seite UI (Buttons, Toasts, ARIA-Labels) | gemischt | komplett deutsch |
| E-Mail-Body-Vorlage | "Hi Flo, Here's my ranking…" englisch | deutsch ("Hallo Flo, mein Ranking für …") |
| E-Mail-Subject-Template | `[vote] <id> — <rater>` englisch | deutsch (`[Stimme] <experiment-name> — <wähler:in>`) |
| `.claude/skills/experiments/SKILL.md` | englisch | **bleibt englisch** (technische Doku für Claude); separate deutsche Bedienungsanleitung wird zusätzlich erstellt |
| `design-guide/README.md`, `design-guide/gruene-corpus.md` | gemischt | komplett deutsch |
| SUMMARY.md (Aggregator-Ausgabe) | englisch | deutsch |
| Astro-Site Header / Landing / Card-Beschreibungen | gemischt | komplett deutsch |
| Hypothesen-Generierungs-Prompts | englisch | deutsch (LLMs generieren deutsche Hypothesen-Texte) |
| Codegen-Prompts | englisch | deutsch (Variant-Inhalte müssen deutsch sein) |

**Locked decision (siehe "Offene Entscheidungen" unten):** Manifest-Schema bekommt deutsche Anzeigenamen, **bestehende Felder werden ersetzt** (nicht `_de` Suffix-Felder hinzugefügt). Begründung: Mehrsprachigkeit über deutsch hinaus ist explizit out-of-scope, also kein Bedarf für Locale-Tagging.

## Inhaltliche Bereiche (Phasen)

### A. Vollständige Lokalisierung (Kern)

Alles user-facing auf deutsch. Sub-Punkte:

1. UI-Strings auf Voting-Seite — alle Buttons, Toasts, Hilfetexte, Platzhalter, ARIA-Labels.
2. Hypothesen-Metadaten — `name`, `rationale`, `expected_outcome` in Manifest auf deutsch (Felder werden ersetzt, nicht ergänzt).
3. Hypothesen-Generierung — Prompt-Templates auf deutsch, LLMs generieren deutsche Hypothesen.
4. Codegen-Prompts — Variant-Inhalte (Headlines, Body) auf deutsch.
5. E-Mail-Body-Template — auf deutsch (z. B. "Hallo Flo, mein Ranking für …").
6. E-Mail-Subject-Template — auf deutsch (z. B. `[Stimme] <experiment-name> — <wähler:in>`).
7. Aggregator-Ausgabe (`SUMMARY.md`) — auf deutsch.
8. Design-Guide-Dokumente — auf deutsch (sowohl `README.md` als auch `gruene-corpus.md`).
9. Astro-Site-Chrome (Header-Links, Landing-Page-Texte, Footer) — auf deutsch.
10. Bedienungsanleitung für Nicht-Techniker:innen — siehe Phase G.

### B. Multi-Rater Support

Mehrere Voter:innen pro Experiment. Aggregation über mehrere Stimmen.

1. Aggregator akzeptiert beliebig viele Einreichungen für ein Experiment.
2. Pro Variante: Borda-Mittelwert über alle Rater, Coverage-Count, Stabilitäts-Indikator (verändert sich das Ranking signifikant durch zusätzliche Rater?).
3. Disagreement-Surface: welche Varianten polarisieren stark (hohe Streuung)?
4. SUMMARY.md zeigt: pro Variante mittlerer Rang, beste/schlechteste Position, Anzahl Stimmen.

### C. Experiment-Lifecycle

Klare Phasen: Entwurf → aktiv → abgeschlossen → archiviert.

1. `bin/experiment-list` zeigt alle Experimente mit Status.
2. `bin/experiment-close <id>` markiert ein Experiment als abgeschlossen (keine weiteren Stimmen werden in der Aggregation berücksichtigt; UI zeigt "Abstimmung beendet").
3. `bin/experiment-archive <id>` verschiebt Manifest + Renders + Ergebnisse nach `experiments/_archived/`.
4. Voting-Seite zeigt Status sichtbar (aktiv / beendet / archiviert).
5. Manifest erhält `status` Feld (`draft | active | closed | archived`) und `closed_at` / `archived_at` Timestamps.

### D. Sharing & Discoverability

Einladen von Voter:innen, ohne dass die URL manuell verteilt werden muss.

1. "Experiment teilen" Button auf der Voting-Seite — öffnet mailto: mit vorgefüllter Einladung in deutsch und Voting-URL.
2. QR-Code auf der Voting-Seite (klein, in der Footer-Zeile) — Voter:innen können auf einem Bildschirm scannen und am Handy abstimmen.
3. Optionale Veröffentlichung: Astro-Site-Landing zeigt aktive Experimente (nicht abgeschlossene, nicht archivierte).
4. Aktuelles Voting auf der Galerie-Index-Karte ("Aktuelle Abstimmung: …") wenn ein Experiment offen ist.

### E. Operative Tooling

Befehle, die Nicht-Techniker:innen via SKILL.md aufrufen können — oder Claude für sie ausführt.

1. `bin/experiment-list` — alle Experimente mit Status, Anzahl Stimmen, letzte Aktivität.
2. `bin/experiment-stats <id>` — Schnellblick: Stimmen, Top-3, Bottom-3, Disagreement.
3. `bin/experiment-archive <id>` — siehe C.
4. Skill-Verb `/experiments stats <id>` ergänzt die bestehenden `new|generate|render|capture`.

### F. Robusteres E-Mail-Parsing

Reale E-Mails haben Quirks, die der MVP-Aggregator nicht handhabt:

1. Forwarded Mails (FW:-Präfix, eingebettete Original-Header)
2. Quoted-Printable Encoding (Umlaute werden zu `=C3=BC` usw.)
3. Signature-Blöcke nach dem JSON-Block
4. Threaded Replies (Reply-Bodies mit ">"-Prefix)
5. Multipart-MIME (text/plain + text/html)
6. Whitespace-Variationen rund um die Marker

Der Parser muss diese Fälle aushalten oder mit klaren Fehlermeldungen ablehnen.

### G. Nicht-Techniker-Doku auf deutsch

Eine separate, schlanke Anleitung (~1-2 Seiten), die folgendes erklärt:
1. Was ist diese Abstimmung? (Kontext)
2. Wie stimme ich ab? (Schritt für Schritt mit Screenshots)
3. Wie wird mein Ergebnis verwendet? (Transparenz: deine Stimme fließt in den Design-Korpus für zukünftige Kandidat:innen-Materialien ein)
4. Wer steht dahinter? (Florian / Grüne NÖ)
5. Datenschutz: was wird gespeichert, was nicht.

Verlinkt von der Voting-Seite ("Erste Mal hier? → Anleitung"). **Locked decision (siehe unten):** lebt als Astro-Seite (`/anleitung/`), damit sie via QR-Code linkbar ist.

### H. (Optional, niedrige Priorität) Datenschutz / Hinweise

1. Datenschutzhinweis auf der Voting-Seite (kurzes Banner: "Deine Stimme wird per E-Mail an Florian Motlik / Grüne NÖ gesendet").
2. Anonyme Stimmen ohne Wähler:in-Feld erlauben.

## Acceptance Criteria

**Phase 1 — Lokalisierung (CRITICAL):**
- [ ] Alle UI-Strings auf der Voting-Seite (Voting-Page, Experiments-Index, Galerie-Landing, Header-Nav) sind deutsch
- [ ] Alle Hypothesen-Metadaten im Manifest haben deutsche Anzeigenamen + Beschreibungen
- [ ] Hypothesen-Generierungs-Prompts erzeugen deutsche Hypothesen-Texte
- [ ] Codegen produziert Variants mit deutschem Content (Headlines, Body)
- [ ] E-Mail-Body + Subject Template auf deutsch
- [ ] Aggregator-Ausgabe (SUMMARY.md) auf deutsch
- [ ] `design-guide/README.md` und `design-guide/gruene-corpus.md` auf deutsch
- [ ] Nicht-Techniker-Anleitung auf deutsch erstellt und verlinkt

**Phase 2 — Multi-Rater:**
- [ ] Aggregator handhabt N Rater pro Experiment
- [ ] SUMMARY.md zeigt mittleren Rang, Stimmenanzahl, Disagreement pro Variante

**Phase 3 — Lifecycle:**
- [ ] `bin/experiment-list/-close/-archive` implementiert
- [ ] Manifest hat `status`-Feld
- [ ] Voting-Seite zeigt Status

**Phase 4 — Sharing:**
- [ ] "Experiment teilen" Button mit mailto-Einladung
- [ ] QR-Code auf Voting-Seite
- [ ] Aktive Experimente auf Galerie-Landing sichtbar

**Phase 5 — Ops Tooling:**
- [ ] `bin/experiment-stats <id>` implementiert
- [ ] Skill-Verb `/experiments stats` ergänzt

**Phase 6 — E-Mail-Parsing-Robustheit:**
- [ ] Aggregator handhabt FW:-Mails, Quoted-Printable, Signaturen, Threaded Replies, Multipart
- [ ] Unit-Tests für jeden dieser Fälle

**Phase 7 — Verifikation (das Merge-Gate):**
- [ ] Reales Experiment mit ≥3 Rater:innen läuft komplett durch
- [ ] Korpus-Update wird tatsächlich von der Aggregation gespeist
- [ ] Mindestens eine echte Kandidat:innen-Material-Variante wird aus dem Korpus abgeleitet (auch wenn nur als Mock — Beweis, dass der Loop schließt)

## Out of Scope (bewusst nicht enthalten)

- Server-side State / Real-time Multi-Rater Sync (mailto bleibt das Fundament)
- Mehrsprachigkeit über deutsch hinaus (kein i18n / locale tagging)
- Auth / Login / User-Accounts
- Mobile App (nur die Astro-Seite, mobile-responsive)
- WhatsApp Business API
- Automatischer E-Mail-Abruf (IMAP) — manuelles Speichern + `--from-emails` bleibt
- Vollständiger Ersatz des CD-Quickguides als Autorität — der Korpus ergänzt, ersetzt nicht
- Automatisches Anwenden des Korpus auf neue Templates — Korpus ist Referenz für Mensch + LLM, nicht automatisierter Generator

## Dependencies

#29 + #30 + #31 + #32 + #33 (alle gemerged, alle Live).

## Priorität

High. Sprung vom Forschungs-MVP zum produktiv genutzten System.

---

## Empfohlene Implementierungs-Strategie

**Direktes Execute ist NICHT empfohlen.** Das Issue ist zu groß für einen einzelnen PR (~7 inhaltliche Bereiche, ~25+ atomare Tasks). Stattdessen vorgeschlagene Aufteilung in **4 sequenzielle PRs**, mit der Möglichkeit, jedes PR-Bündel auch als eigenes Issue zu führen, wenn das übersichtlicher ist:

### PR 1: Lokalisierung + Nicht-Techniker-Doku
**Bereiche:** A + G
**Warum zuerst:** sichtbarster Effekt. Eine "echte deutsche Voting-Seite" ist die Voraussetzung dafür, dass externe Voter:innen das System überhaupt nutzen können.
**Scope:** alle UI-Strings auf deutsch, Manifest-Schema mit deutschen Anzeigenamen, Prompt-Templates auf deutsch, Codegen-Prompts auf deutsch (Variants mit deutschem Inhalt), Aggregator-SUMMARY.md auf deutsch, design-guide-Dokumente auf deutsch, neue Astro-Seite `/anleitung/` mit Schritt-für-Schritt-Erklärung.
**Verifikations-Schritt:** v2-Variants neu generieren mit deutschem Content (Panel B muss DE werden, aktuell EN); Voting-Seite optisch deutsch-only.
**Schätzung:** ~10-15 atomare Tasks, mittlere bis große PR.

### PR 2: Multi-Rater + Lifecycle
**Bereiche:** B + C
**Warum gekoppelt:** Multi-Rater braucht das `status`-Feld aus Lifecycle (closed Experimente akzeptieren keine neuen Stimmen mehr); SUMMARY.md-Erweiterung greift in beide Bereiche.
**Scope:** Aggregator-Erweiterung für N Rater, neue Borda-Statistiken (mittlerer Rang, Disagreement, Coverage), Manifest-`status`-Feld, `bin/experiment-list/-close/-archive`, Voting-Seite zeigt Status.
**Verifikations-Schritt:** synthetisches Mehr-Rater-Szenario aggregieren; close + archive durch CLI testen.
**Schätzung:** ~8-12 atomare Tasks.

### PR 3: Sharing + Ops Tooling
**Bereiche:** D + E
**Scope:** "Experiment teilen" mailto-Button, QR-Code (build-time generiert, siehe Entscheidungen unten), aktive Experimente auf Galerie-Landing, `bin/experiment-stats`, Skill-Verb `/experiments stats`.
**Verifikations-Schritt:** QR-Code scannen funktioniert; Galerie zeigt aktives Experiment.
**Schätzung:** ~6-8 atomare Tasks.

### PR 4: E-Mail-Robustheit + Verifikationslauf (das Merge-Gate)
**Bereiche:** F + Phase 7
**Scope:** Aggregator-Erweiterung für reale E-Mail-Quirks, Unit-Tests pro Quirk-Klasse, dann reales Experiment mit ≥3 Rater:innen (Flo + 2 weitere Personen, z.B. Designer:in + Kandidat:in oder zwei Grüne-interne Voter:innen), Korpus-Update aus den Ergebnissen, optional eine Kandidat:innen-Material-Mockup-Variante aus dem aktualisierten Korpus abgeleitet.
**Verifikations-Schritt:** das ist Phase 7 — der Live-Lauf schließt dieses Issue UND alle deferred T-finals aus #29/#30/#31/#33 in einem Commit.
**Schätzung:** ~5-8 atomare Tasks für E-Mail-Robustheit; der Verifikationslauf ist manuell.

### Alternative: Phasen als eigene Issues

Falls die 4-PR-Aufteilung zu groß wirkt, kann jede Phase ihr eigenes Issue (#35-#41) werden, mit #34 als Umbrella-Tracker. Empfehlung: Discuss-Phase entscheidet darüber.

## Offene Entscheidungen für die Discuss-Phase

Tier-1 Entscheidungen, die vor Plan/Execute getroffen werden müssen. Vorschläge mit empfohlener Antwort sind notiert; Discuss-Phase confirmiert oder revidiert.

### 1. Manifest-Schema-Migration: ersetzen vs. ergänzen?
**Frage:** Bekommt das Manifest neue `name_de` / `rationale_de` Felder neben den bestehenden englischen, oder werden die bestehenden Felder durch deutschen Inhalt ersetzt?
**Vorschlag:** **Ersetzen.** Mehrsprachigkeit über deutsch hinaus ist explizit out-of-scope (siehe Out of Scope). Kein Bedarf für Locale-Tagging. Schlanker.
**Konsequenz:** alte v2-Manifeste müssen migriert werden (englische Inhalte → deutsche). Migrations-Script oder einmaliges Manual-Update von `experiments/falzflyer-p2-mein-plan-v2/manifest.yml`.

### 2. Bedienungsanleitung: MD-File oder Astro-Seite?
**Frage:** Wo lebt die deutsche Bedienungsanleitung (Phase G)?
**Vorschlag:** **Astro-Seite** (`/anleitung/`). Begründung: muss via QR-Code linkbar sein, muss mobile-responsive sein, profitiert von der bestehenden Brand-CSS-Custom-Properties.
**Alternative:** MD-File in der Repo-Wurzel — leichter zu schreiben, aber nicht verlinkbar von extern, daher weniger nützlich.

### 3. QR-Code-Generation: clientside vs. build-time?
**Frage:** Wie wird der QR-Code für die Voting-URL erzeugt (Phase D)?
**Vorschlag:** **Build-time** (Python `qrcode` Library → PNG in `site/public/experiments/<id>/qr.png`, hardcoded URL). Begründung: URLs sind deterministisch (kein dynamischer Inhalt), kein Browser-Compute nötig, Bundle bleibt schlank.
**Alternative:** clientside (qrcode.js Library, ~25KB Bundle). Mehr Flexibilität (URL kann clientside variiert werden), aber mehr JS auf Mobile.

### 4. Multi-Rater-Identifikation: wie wird "derselbe Rater" erkannt?
**Frage:** Wenn zwei Stimmen mit `rater: "flo"` kommen — ist das eine Person, die zweimal gestimmt hat, oder zwei Personen mit demselben Vornamen?
**Vorschlag:** **Freier Text als Schlüssel + Best-Effort-Dedup auf Basis identischer Strings, mit Warnung bei mehrdeutigen Fällen.** Aggregator markiert Dubletten zum Review, lehnt nicht automatisch ab.
**Alternative:** E-Mail-Adresse zusätzlich als Identifikator (mehr Friction für Rater).

### 5. Anonyme Stimmen: erlauben?
**Frage:** Soll das `rater`-Feld optional sein? Wie werden anonyme Stimmen im SUMMARY angezeigt?
**Vorschlag:** **Erlauben.** Anzeige: `(anonym)` als Platzhalter. SUMMARY zeigt: "X anonyme Stimmen + Y benannte Stimmen". Phase H, optional aber empfohlen für Discoverability.
**Alternative:** Pflichtfeld — weniger Friktion für Operator (keine Dubletten-Frage), aber höherer Eintrittsbarriere für Voter:innen.

### 6. Experiment-Status-Übergänge: wer triggert?
**Frage:** Wer / was triggert `bin/experiment-close` und `bin/experiment-archive` (Phase C)?
**Vorschlag:** **Skill-Verb (`/experiments close <id>` etc.) plus Audit-Trail im Manifest** (`closed_by`, `closed_at`). Praktisch: Claude im Workspace führt den Befehl auf Flo's Anweisung aus.
**Alternative:** automatischer Timeout (z.B. 14 Tage nach Erstellung) — vermeidet Vergessen, aber rigide.

### 7. Galerie-Landing: alle aktiven Experimente oder nur eines?
**Frage:** Wie viele aktive Experimente werden auf der Galerie-Landing angezeigt (Phase D)?
**Vorschlag:** **Eines, das aktuellste.** Begründung: Landing-Page nicht überladen; das aktuelle Experiment ist meistens das einzig relevante.
**Alternative:** alle aktiven, mit Sortierung nach Datum.

### 8. Datenschutz-Banner: ja/nein, wo?
**Frage:** Wird der Datenschutzhinweis aus Phase H Teil dieses Issues?
**Vorschlag:** **Ja, schlanker Hinweis in der Footer-Zeile** der Voting-Seite mit Link zu `/datenschutz/` (separate Astro-Seite mit Detail-Text). Klein, kein modaler Banner.
**Alternative:** ganz weglassen (Phase H ist optional) — Risiko: DSGVO-Compliance unklar für externe Voter:innen.

### 9. v2-Manifest Migration: Inplace-Edit oder neuer v3?
**Frage:** Wird das bestehende `experiments/falzflyer-p2-mein-plan-v2/manifest.yml` inplace deutsch gemacht (Variants neu rendern), oder wird ein `falzflyer-p2-mein-plan-v3` erstellt?
**Vorschlag:** **Inplace-Edit + Re-Render.** v2 wird zur "ersten produktiv-deutschen Version". Vermeidet Inflation von Experiment-IDs.
**Alternative:** v3 anlegen, v2 archivieren. Mehr Klarheit über die Lokalisierungs-Grenze, aber mehr Setup.

### 10. PR-Aufteilung confirmen
**Frage:** Vier sequenzielle PRs (siehe oben) oder etwas anderes?
**Vorschlag:** **4 PRs wie oben skizziert.**
**Alternativen:** ein Mega-PR (zu groß), oder jede Phase ein eigenes Issue (#35-#41 mit #34 als Umbrella).

---

## Stand der Diskussion (Konversations-Kontext)

Dokumentation der bisherigen Diskussion zwischen Flo und Claude, damit der Kontext beim Wiederaufgreifen klar ist.

### Was bestätigt ist
- **Zufriedenheit mit MVP:** Flo hat die fünf MVP-Issues (#29-#33) als ausreichend für die MVP-Phase markiert. Der Sprung zu Production ist der nächste logische Schritt.
- **Hauptanforderung deutsch:** "ein main thing to enshrine is that everything needs to be in german, the explanation, the titles of the experiments, the emails, … Everything needs to be german." — wortwörtlich. Nicht-verhandelbar.
- **mailto bleibt das Submission-Fundament.** Backend-Optionen (webhook.site, Google Apps Script, Cloudflare Worker) wurden diskutiert und alle verworfen zugunsten von mailto + Zwischenablage + Inline-View (siehe #33). Diese Entscheidung steht.
- **Recipient `florian.motlik@gruene.at`** ist hardcoded für E-Mail-Submission. Bleibt für alle weiteren Phasen so.
- **Skill bleibt englisch:** `.claude/skills/experiments/SKILL.md` ist technische Doku für Claude und bleibt englisch. Deutsche Bedienungsanleitung wird separat erstellt (Phase G).
- **Variant-Slugs bleiben englisch:** sie sind Identifier, kein User-Facing-Content. Anzeigenamen kommen separat deutsch.

### Was offen ist
Die 10 Punkte unter "Offene Entscheidungen für die Discuss-Phase" sind alle noch offen. Vorgeschlagene Antworten sind notiert, aber nicht bestätigt.

### Was bewusst NICHT diskutiert wurde
- Konkrete neue Variant-Hypothesen für die deutsche v2-Version (delegiert an Hypothesen-Generierungs-Pipeline)
- Konkreter Inhalt der Nicht-Techniker-Anleitung (delegiert an Plan-Phase mit Designer-Konsultation)
- Welche externen Voter:innen für Phase 7 angefragt werden (delegiert an Verifikationslauf)
- Detail-Schema-Änderungen am Manifest (delegiert an Plan-Phase)

### Empfohlener nächster Schritt
**`/issue:discuss 34-mvp-zu-produktionsreifem-experimentier-system-german-first-multi-rater-lifecycle`** — die 10 Tier-1-Entscheidungen werden interaktiv durchgegangen, dann `/issue:research` für die Plan-Phase. Empfohlene Strategie: Phase A + G zuerst als eigener PR (oder eigenes Issue), da das der sichtbarste Effekt ist und alle anderen Phasen davon profitieren.

Alternativ: das Issue in 4 kleinere Issues splitten (eines pro PR-Bündel), und dieses #34 als Umbrella-Tracker mit Links zu den Sub-Issues führen.
