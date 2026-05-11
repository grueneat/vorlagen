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
- #29: Pairwise-Voting MVP (Hypothesen → Varianten → Render → Voting → Aggregator)
- #30: Constraint Envelope + `experiments` Skill + v2 Lauf
- #31: Click-to-Rank Voting-UI (Versus-Modus entfernt)
- #32: Tent-Card-Panel-Orientierung + Galerie-Dedup + Experiments-Nav-Link
- #33: E-Mail-Einreichung (mailto + Zwischenablage + Inline-Ansicht)

Das MVP funktioniert technisch, ist aber für den Produktiveinsatz durch echte Grüne-Kandidat:innen, Designer:innen und externe Voter:innen noch nicht bereit. Dieses Issue beschreibt die nächste Stufe — vom MVP zum produktionsreifen System.

## Vision

Ein System, das von echten Grüne-Kampagnen genutzt wird, um Design-Entscheidungen für Kandidat:innen-Materialien zu treffen. Mehrere Personen pro Experiment stimmen ab, Ergebnisse fließen in echte gedruckte Materialien ein, der Korpus wächst kontinuierlich.

## Kern-Anforderung: ALLES AUF DEUTSCH

Das ist die wichtigste Anforderung dieses Issues. Aktuell ist vieles auf Englisch oder gemischt:
- Experiment-Titel (z. B. "Falzflyer P2 'Mein Plan' — pairwise voting") → komplett deutsch
- Variant-Slugs (kebab-case englisch wie `numbered-priority-list-v2`) → bleiben technisch englisch (sind Identifier), aber **angezeigte Namen müssen deutsch sein** (z. B. "Nummerierte Prioritäten mit gewichteter Skala")
- Hypothesen-Beschreibungen / Rationales → deutsch
- Variant-Inhalte (Headlines, Body, Captions) → komplett deutsch (Panel A bereits DE, Panel B aktuell EN — angleichen)
- Voting-Seite UI (Titel, Buttons, Toasts, ARIA-Labels) → komplett deutsch
- E-Mail-Body-Vorlage ("Hi Flo, Here's my ranking…") → deutsch
- E-Mail-Subject-Template → deutsch
- `.claude/skills/experiments/SKILL.md` → bleibt englisch (technische Doku für Claude); ABER eine zweite, deutsche Bedienungsanleitung für Nicht-Techniker:innen wird zusätzlich erstellt
- `design-guide/README.md` und `design-guide/gruene-corpus.md` → komplett deutsch (aktuell gemischt)
- SUMMARY.md (Aggregator-Ausgabe) → deutsch
- Astro-Site Header / Landing / Card-Beschreibungen → komplett deutsch
- Hypothesen-Generierungs-Prompts → werden in deutsch geschrieben, generieren deutsche Hypothesen-Texte
- Codegen-Prompts → Variant-Inhalte müssen deutsch sein

## Inhaltliche Bereiche

### A. Vollständige Lokalisierung (Kern)

Alles user-facing auf deutsch. Sub-Punkte:

1. UI-Strings auf Voting-Seite — alle Buttons, Toasts, Hilfetexte, Platzhalter, ARIA-Labels.
2. Hypothesen-Metadaten — `name`, `rationale`, `expected_outcome` in Manifest auf deutsch (`name_de`, `rationale_de` Felder ODER ersetzen der bestehenden englischen Felder).
3. Hypothesen-Generierung — Prompt-Templates auf deutsch, LLMs generieren deutsche Hypothesen.
4. Codegen-Prompts — Variant-Inhalte (Headlines, Body) auf deutsch.
5. E-Mail-Body-Template — auf deutsch (z. B. "Hallo Flo, mein Ranking für …").
6. E-Mail-Subject-Template — auf deutsch (z. B. `[Stimme] <experiment-name> — <wähler:in>`).
7. Aggregator-Ausgabe (`SUMMARY.md`) — auf deutsch.
8. Design-Guide-Dokumente — auf deutsch (sowohl `README.md` als auch `gruene-corpus.md`).
9. Astro-Site-Chrome (Header-Links, Landing-Page-Texte, Footer) — auf deutsch.
10. Bedienungsanleitung für Nicht-Techniker:innen — deutsche Dokumentation, wie man eine Stimme abgibt (verlinkt auf der Voting-Seite).

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
3. Optionale Veröffentlichung: Astro-Site-Landing zeigt eine Liste aller AKTIVEN (nicht abgeschlossenen, nicht archivierten) Experimente, damit Interessierte sie finden.
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

Eine separate, schlanke Anleitung (~1-2 Seiten als MD oder als Astro-Seite), die folgendes erklärt:
1. Was ist diese Abstimmung? (Kontext)
2. Wie stimme ich ab? (Schritt für Schritt mit Screenshots)
3. Wie wird mein Ergebnis verwendet? (Transparenz: deine Stimme fließt in den Design-Korpus für zukünftige Kandidat:innen-Materialien ein)
4. Wer steht dahinter? (Florian / Grüne NÖ)
5. Datenschutz: was wird gespeichert, was nicht.

Verlinkt von der Voting-Seite ("Erste Mal hier? → Anleitung").

### H. (Optional, niedrige Priorität) Datenschutz / Hinweise

1. Datenschutzhinweis auf der Voting-Seite (kurzes Banner: "Deine Stimme wird per E-Mail an Florian Motlik / Grüne NÖ gesendet").
2. Optional: anonyme Stimmen ohne Wähler:in-Feld erlauben.

## Acceptance Criteria

Phase 1 — Lokalisierung (CRITICAL):
- [ ] Alle UI-Strings auf der Voting-Seite (Voting-Page, Experiments-Index, Galerie-Landing, Header-Nav) sind deutsch
- [ ] Alle Hypothesen-Metadaten im Manifest haben deutsche Anzeigenamen + Beschreibungen
- [ ] Hypothesen-Generierungs-Prompts erzeugen deutsche Hypothesen-Texte
- [ ] Codegen produziert Variants mit deutschem Content (Headlines, Body)
- [ ] E-Mail-Body + Subject Template auf deutsch
- [ ] Aggregator-Ausgabe (SUMMARY.md) auf deutsch
- [ ] `design-guide/README.md` und `design-guide/gruene-corpus.md` auf deutsch
- [ ] Nicht-Techniker-Anleitung auf deutsch erstellt und verlinkt

Phase 2 — Multi-Rater:
- [ ] Aggregator handhabt N Rater pro Experiment
- [ ] SUMMARY.md zeigt mittleren Rang, Stimmenanzahl, Disagreement pro Variante

Phase 3 — Lifecycle:
- [ ] `bin/experiment-list/-close/-archive` implementiert
- [ ] Manifest hat `status`-Feld
- [ ] Voting-Seite zeigt Status

Phase 4 — Sharing:
- [ ] "Experiment teilen" Button mit mailto-Einladung
- [ ] QR-Code auf Voting-Seite
- [ ] Aktive Experimente auf Galerie-Landing sichtbar

Phase 5 — Ops Tooling:
- [ ] `bin/experiment-stats <id>` implementiert
- [ ] Skill-Verb `/experiments stats` ergänzt

Phase 6 — E-Mail-Parsing-Robustheit:
- [ ] Aggregator handhabt FW:-Mails, Quoted-Printable, Signaturen, Threaded Replies, Multipart
- [ ] Unit-Tests für jeden dieser Fälle

Phase 7 — Verifikation:
- [ ] Reales Experiment mit ≥3 Rater:innen läuft komplett durch
- [ ] Korpus-Update wird tatsächlich von der Aggregation gespeist
- [ ] Mindestens eine echte Kandidat:innen-Material-Variante wird aus dem Korpus abgeleitet (auch wenn nur als Mock — Beweis, dass der Loop schließt)

## Out of Scope (bewusst nicht enthalten)

- Server-side State / Real-time Multi-Rater Sync (mailto bleibt)
- Mehrsprachigkeit über deutsch hinaus
- Auth / Login / User-Accounts
- Mobile App (nur die Astro-Seite, mobile-responsive)
- WhatsApp Business API
- Automatische E-Mail-Abruf (IMAP) — manuelles Speichern + `--from-emails` bleibt
- Vollständiger Ersatz des CD-Quickguides als Autorität — der Korpus ergänzt, ersetzt nicht
- Automatisches Anwenden des Korpus auf neue Templates — Korpus ist Referenz für Mensch + LLM, nicht automatisierter Generator

## Dependencies

#29 + #30 + #31 + #32 + #33 (alle gemerged).

## Priorität

High. Dies ist der Sprung vom Forschungs-MVP zum echten produktiven System.

## Notizen für Discuss/Plan-Phase

- Die 7 Phasen oben sind grobe Gruppen — Discuss + Plan brechen sie in atomare Tasks auf.
- Phase 1 (Lokalisierung) ist nicht-verhandelbar und sollte zuerst kommen, da sie am sichtbarsten ist.
- Multi-Rater (Phase 2) und Lifecycle (Phase 3) sind eng gekoppelt — möglicherweise in einer gemeinsamen Implementierungsphase.
- Phase 7 (echtes Experiment mit 3 Rater:innen) ist das Merge-Gate, mirror das T-final-Muster aus #29/#30/#31.
