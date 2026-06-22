# Bockwurst Sport Events – Projektkontext für Agenten

> Schlanker Einstieg. Die vollständige technische Referenz steht in
> **[`docs/TECHNISCHE-DOKUMENTATION.md`](docs/TECHNISCHE-DOKUMENTATION.md)** – bei Detailfragen dort nachsehen.

## Was ist das?
Werbefreier Event-Guide für Rennrad, Triathlon, Schwimmen und Laufen in Deutschland.
- Live: https://bockwurst-events.netlify.app/event-guide
- Staging: https://staging--bockwurst-events.netlify.app/event-guide
- Repo: https://github.com/stefangriessmann/sport-events

## Architektur in drei Sätzen
- `index.html` ist eine statische Single-Page-App ohne Build-Schritt; sie lädt die Eventdaten zur Laufzeit per `fetch` aus `data/*.json`.
- Die Eventdaten pflegt ein wöchentlicher GitHub-Actions-Cronjob (`weekly_update.yml` → `scripts/update_data.py`), der nur `data/*.json` schreibt.
- Hosting ist Netlify; Push auf `main` deployt Live, Push auf `staging` deployt Staging.

## Goldene Regeln
1. **`index.html` ist ein festes Design-Artefakt.** Nur ein gezielter Entwickler-Commit ändert es. **Kein Scraping-/Daten-Job darf `index.html` neu erzeugen** – genau das hat früher das Design zurückgesetzt.
2. **Eventdaten nur über `scripts/update_data.py`** nach `data/*.json` schreiben. Das alte `scripts/update_snapshots.py` (eingebettete Snapshots in `index.html`) ist abgelöst und wird von keinem Workflow mehr genutzt.
3. **Keine Tokens im Quellcode.** Sie gehören in Netlify-Env-Vars (`GITHUB_ISSUES_TOKEN`) bzw. GitHub-Secrets (`RESEND_API_KEY`).
4. **DOM-IDs nicht beiläufig umbenennen** – die Playwright-Tests (`tests/bockwurst.spec.js`, 76 Stück) hängen daran. Bei Änderungen Tests mitziehen.
5. Schriften sind **selbst gehostet** (`assets/fonts/`, kein Google Fonts) – wegen „kein Tracking".

## Wichtige Dateien
- `index.html` – die App (Design + Logik, lädt `data/*.json`)
- `scripts/update_data.py` – Daten-Orchestrator (Scraper → `data/*.json`)
- `scripts/scrapers/` – ein Scraper pro Quelle (`fetch(year) -> list[dict]`)
- `netlify/functions/create-issue.js` – Formular-POST → GitHub-Issue
- `.github/workflows/` – `weekly_update` (Daten), `e2e` (Tests), `approve_event` (Freigabe), `monthly-update`
- `data/*.json` + `data/meta.json` – Eventdaten (vom Cronjob gepflegt)

## Deploy
```bash
git checkout staging && git pull
git commit -am "…"
git push origin staging          # → Staging + E2E-Tests
git checkout main && git merge --ff-only staging && git push origin main
```
Voraussetzung für die schreibenden Workflows: **Settings → Actions → General → Workflow permissions = „Read and write permissions"**.

## Tests
```bash
npm install -D @playwright/test && npx playwright install chromium
BASE_URL=https://staging--bockwurst-events.netlify.app npx playwright test tests/bockwurst.spec.js
```

## Mehr Details
Alles Weitere – Daten-Pipeline, Freigabe-Flow, Benachrichtigungen, Troubleshooting, bekannte Altlasten – in **[`docs/TECHNISCHE-DOKUMENTATION.md`](docs/TECHNISCHE-DOKUMENTATION.md)**.
