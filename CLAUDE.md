# Bockwurst Sport Events – Projekt-Kontext für Claude Code

## Was ist das hier?
Single-page HTML Event Guide für Radsport, Triathlon und Laufen in Deutschland.
Live: https://bockwurst-events.netlify.app
Repo: https://github.com/stefangriessmann/sport-events

## Technischer Stack
- `index.html` — einzige HTML-Datei, enthält eingebettete JS-Arrays (Snapshots)
- `scripts/update_snapshots.py` — liest index.html, ersetzt JS-Arrays via Regex, schreibt zurück
- `scripts/scrapers/` — ein Scraper pro Quelle, jeder liefert `list[dict]`
- `netlify/functions/create-issue.js` — GitHub Issues Proxy für Event-Einreichungen
- `.github/workflows/approve_event.yml` — GitHub Action: approved Label → update_snapshots.py → push

## Arbeitsablauf
Lokale Änderungen immer in `~/Claude/` vorbereiten, dann:
- `bash ~/Claude/run_update.sh` → kopiert Dateien, scrapt, pusht zu `main` → Netlify deployt live
- `bash ~/Claude/run_update.sh --staging` → pusht zu `staging` → https://staging--bockwurst-events.netlify.app

## Snapshot-Struktur in index.html
```js
const SNAPSHOT      = [...];  // Radsport (rad-net + radsport-events.de)
const TRI_SNAPSHOT  = [...];  // Triathlon (triathlondeutschland.de)
const LAUF_SNAPSHOT = [...];  // Laufen (laufen.run)
const SWIM_SNAPSHOT = [...];  // Schwimmen (noch leer)
```
Jeder Event-Eintrag hat: art, datum, datum_end, date_iso, date_iso_end, titel, ort, lv, country, url, km, lat, lon

## Aktuell offene Aufgaben (aus Cowork-Kanban)
Siehe `~/Claude/briefs/` für task-spezifische Briefings.

Backlog-Prioritäten (P = Impact÷Komplexität):
1. Domain bockwurst.cc registrieren (P5.0)
2. PLZ-Distanzfilter (P1.3) — Brief: ~/Claude/briefs/plz-filter.md
3. Quellen-Index & Scraping-Strategie (P1.5)
4. Hetzner VPS + Ghost (P2.5)

## Bekannte PATs (nicht in Source Code!)
- repo+workflow PAT: in run_update.sh remote URL eingebettet
- issues:write PAT: Netlify env var GITHUB_ISSUES_TOKEN

## Wichtige Dateipfade
- Lokale Arbeitskopie: ~/sport-events/
- Skripte/Helpers: ~/Claude/
- Scraper: ~/Claude/scrapers/ → wird von run_update.sh nach ~/sport-events/scripts/scrapers/ kopiert
