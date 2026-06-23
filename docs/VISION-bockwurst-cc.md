# bockwurst.cc – Produktvision & Roadmap

> **Stand:** 23.06.2026 · Rekonstruiert aus dem alten Kanban „Bockwurst Projects" (Stand 14.06.2026).
> **Architektur-Entscheidung:** CMS = **TYPO3** (statt des ursprünglich geplanten WordPress).

## Vision

bockwurst.cc ist Stefans persönliche Sport-Plattform („Stefans Rennrad Welt" – Rennrad Chemnitz, Zwift / Team Valhalla) – **mehrere Säulen unter einer Marke**, werbefrei und zweisprachig (DE/EN). Der Event Guide ist die **erste, bereits live laufende Säule**, nicht das Ganze.

## Architektur (zwei Systeme)

- **bockwurst.cc** – Hauptseite auf **TYPO3** (Hetzner VPS). Marke, Profil, Tourenportal, Zwift, 6 Points, Blog/Reichweite.
- **events.bockwurst.cc** – der **Event Guide** (bestehende statische App auf Netlify). Per Subdomain eingebunden, mit Profilkachel zur Hauptseite verzahnt.

## Entscheidung: TYPO3 statt WordPress

Das alte Kanban plante WordPress (Astra/GeneratePress, Rank Math, TranslatePress+DeepL, Borlabs Cookie, LiteSpeed). Neue Richtung **TYPO3** (v13 LTS, Composer-Setup, eigenes Sitepackage mit Fluid/SCSS). TYPO3-Entsprechungen je Karte unten.

## Säulen & Backlog (P = Impact ÷ Komplexität, aus altem Kanban)

### A · Infrastruktur & Domain
| Karte | P | Status | Hinweis (TYPO3-Anpassung) |
|-------|---|--------|---------------------------|
| Domain bockwurst.cc registrieren | 5.0 | in Arbeit (DNS-Regeln gesetzt) | A-Record → Hetzner-VPS; CNAME events → Netlify |
| Hetzner VPS + **TYPO3**-Setup | 2.5 | offen | war: WordPress. CX22, Ubuntu 24.04, Nginx/Apache + SSL, PHP 8.x, MariaDB, Composer-TYPO3 v13 (DDEV optional) |
| Event Guide → events.bockwurst.cc | 1.5 | offen | DNS CNAME → Netlify, Custom Domain, Canonical umstellen |
| Cookie-Consent + YouTube-Einbettung (DSGVO) | 4.0 | offen | TYPO3-Cookie-Consent-Ext statt Borlabs; ermöglicht echten YT-iFrame + Strava-Maps |
| Mehrsprachigkeit DE/EN | 1.5 | offen | TYPO3-natives L10n + DeepL-Ext (z. B. wv_deepltranslate) statt TranslatePress |

### B · Marke & Hauptseite (TYPO3)
| Karte | P | Status | Hinweis |
|-------|---|--------|---------|
| TYPO3-Sitepackage & Design | 2.0 | offen | war: WP-Theme. Fluid/SCSS, bockwurst-Branding, Header/Navigation; TYPO3-SEO (statt Rank Math), GSC |
| Profilseite „Über Bockwurst" | 4.0 | offen | Wer, Rennrad Chemnitz, Zwift/Team Valhalla, Social-Links, 20-Jahre-Geschichte/Fotos |
| Profilkachel auf Event Guide | 2.0 | offen | „Über mich"-Kachel auf events, verlinkt zur Hauptseite |

### C · Tourenportal (TYPO3)
| Karte | P | Status | Hinweis |
|-------|---|--------|---------|
| Strava-API-Integration | 1.3 | offen | OAuth; Aktivitäts-Kachel mit Streckenkarte (Polyline), Distanz, HM, Zeit |
| Tour-Detailseiten-Template | 1.3 | offen | Strava-Karte + YouTube + strukturierter Bericht; Basis für **90+ YouTube-Touren**; erste 3 als Pilot |

### D · Event Guide (events.bockwurst.cc) — laufend
| Karte | P | Status | Hinweis |
|-------|---|--------|---------|
| DE-Event-Guide live (Rad/Tri/Lauf/Freiwasser) | — | erledigt | Relaunch-Design, Daten-Architektur, Tests/CI, Benachrichtigungen, Formular |
| UK-Expansion | — | in Arbeit | Raddaten (Cycling UK + Sportive.com + Dedup) erledigt; Frontend P0 + weitere Sportarten offen. Detail: `docs/UK-EXPANSION-KONZEPT.md` |
| Mammutmärsche – Scraper | 0.7 | erledigt | neue Sportart unter Laufen |
| Inline-Skaten – Tab + Scraper | 1.0 | offen | Quellen: inlineskatemarathon.de, skatefinder |
| Eislaufen – Tab + Scraper | 1.0 | offen | Eisschnelllauf/Eiskunstlauf |
| Quellen-Index & Scraping-Strategie | 1.5 | offen | `data/sources.json`, gestaffelte Crons, rollierend +400 Tage; Länder AT→CH→IT→FR→ES→UK→CZ |

### E · Content & Community
| Karte | P | Status | Hinweis |
|-------|---|--------|---------|
| Zwift-Content-Sektion | 1.5 | offen | Tag/Landingpage, „Setup für Zwift-Rennen", Team Valhalla |
| 6 Points Charity Landingpage | 4.0 | offen | Mallorca-Charity, Markenbotschafter, Anmelde-CTA |

### F · Reichweite & Newsletter
| Karte | P | Status | Hinweis |
|-------|---|--------|---------|
| Reichweite & organisches Wachstum | 1.3 | laufend | SEO/GSC, OG-Tags, FB, Strava-Club, YouTube Shorts, Reddit, Veranstalter-Listung gegen Backlink, Newsletter (Buttondown) |

## Status-Überblick

- **Erledigt:** 28 Karten im alten Kanban + diese Session (Relaunch-Design, Tests/CI, Benachrichtigungen, Formular-Fix, UK-Raddaten Cycling UK + Sportive.com + Dedup).
- **Aktueller Fokus:** Event Guide – UK-Expansion.
- **Größter nächster Sprung für die Hauptseite:** Domain + Hetzner + **TYPO3**-Setup → danach Profilseite & Tourenportal.

## Offene Punkte / zu bestätigen

- TYPO3-Detailentscheidungen (Ext-Auswahl: DeepL, Cookie-Consent; DDEV ja/nein; Hosting Hetzner-Größe).
- Reihenfolge: Event Guide (UK) fertig ziehen vs. parallel Hauptseiten-Fundament (Domain/TYPO3) starten.
