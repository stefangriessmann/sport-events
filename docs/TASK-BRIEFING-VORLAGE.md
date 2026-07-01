# Task-Briefing-Vorlage (für Aufgaben an Claude Code)

> Zweck: Eine Aufgabe so übergeben, dass Claude Code **nahtlos** weiterarbeiten kann – ohne Rückfragen und ohne dass etwas Bekanntes wiederholt werden muss.
>
> Claude Code liest die **`CLAUDE.md` im Repo-Root automatisch** (Architektur, goldene Regeln, Deploy, Tests). Du lieferst pro Aufgabe nur das **Delta**.

## Kopiervorlage

```
Ziel: <was soll hinterher anders sein + warum, ein Satz>
Kontext: Lies CLAUDE.md + docs/<relevantes-dokument>.md
Bereich: <Datei/Ordner – oder "bitte selbst lokalisieren">
Fertig, wenn: <Akzeptanzkriterien, z. B. "Tests grün + auf Staging sichtbar">
Regeln: Goldene Regeln aus CLAUDE.md gelten.
Ablauf: Branch staging → ich prüfe → main.
Nicht anfassen: <optional>
```

## Feld-Erklärungen

- **Ziel** – das Ergebnis, nicht der Weg. Beispiel: „UK-Events erscheinen im Länderfilter, damit UK-Nutzer relevante Rides finden."
- **Kontext-Zeiger** – der/die spezifischen `docs/`-Dateien zur Aufgabe. CLAUDE.md verweist auf die großen Konzepte (Vision, Consent, Touren, Design-Briefs).
- **Bereich** – wenn du die Datei kennst, nennen; sonst darf Claude Code sie selbst finden.
- **Definition of Done** – woran *du* Fertigstellung erkennst. Häufig: „Playwright-Tests grün, Feature auf Staging sichtbar."
- **Regeln** – meist reicht der Verweis auf die goldenen Regeln. Die wichtigsten: `index.html` nicht in Daten-Jobs neu erzeugen · keine Tokens im Code · DOM-IDs nicht beiläufig umbenennen (Tests hängen daran).
- **Ablauf** – Standard: erst `staging` (deployt + Tests laufen), Sichtprüfung durch dich, dann `main`.
- **Nicht-Ziele** – was bewusst außen vor bleibt (verhindert Scope-Ausufern).

## Was du NICHT mitschickst

- **Keine Tokens/Secrets** – die liegen in Netlify-Env-Vars bzw. GitHub-Secrets, nicht im Prompt.
- **Keine Wiederholung** von Dingen, die schon in `CLAUDE.md` oder `docs/` stehen – nur darauf verweisen.

## Beispiel (ausgefüllt)

```
Ziel: Spotify-Player pro Tour einbinden ("Sound der Tour"), erst nach Consent ladend.
Kontext: Lies CLAUDE.md + docs/DSGVO-COOKIE-CONSENT-KONZEPT.md + docs/DESIGN-BRIEF-tour-detailseite.md
Bereich: Tour-Detail-Template (bitte selbst lokalisieren)
Fertig, wenn: Platzhalterkachel sichtbar; Player lädt erst nach Klick/Consent; auf Staging sichtbar.
Regeln: Goldene Regeln aus CLAUDE.md gelten. Klick-zum-Laden wie im Consent-Konzept.
Ablauf: Branch staging → ich prüfe → main.
Nicht anfassen: Event-Guide-Datenpipeline.
```
