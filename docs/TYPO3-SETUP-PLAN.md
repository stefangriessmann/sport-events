# bockwurst.cc – TYPO3-Setup-Plan (Säule A: Infrastruktur & Fundament)

> Stand: 2026-07-01 · Status: **Plan zur Abnahme** (noch nichts gebaut/gebucht).
> Entscheidungen dieser Runde: TYPO3 **v14 LTS**, Vorgehen **lokal mit DDEV zuerst**, Hosting **noch offen – wird hier empfohlen**, Wunsch: **weg vom kostenpflichtigen Netlify-Abo**.
> Bezug: `VISION-bockwurst-cc.md`, `INHALTS-STRUKTUR-KONZEPT-bockwurst-cc.md`, `DSGVO-COOKIE-CONSENT-KONZEPT.md`.

## 0. Recherchierte Fakten (aktuell, Juli 2026)

| Thema | Ergebnis | Konsequenz |
|---|---|---|
| **TYPO3 v14 LTS** | v14.3.0 released 21.04.2026; Bugfixes bis 31.12.2027, Security bis 30.06.2029 | Aktuelle LTS → richtige Wahl für einen Neustart |
| **PHP** | v14 braucht **PHP ≥ 8.2** (8.3/8.4/8.5 unterstützt) | Host/DDEV auf PHP 8.3 oder 8.4 |
| **sg_cookie_optin** | **8.0.3 (10.06.2026)** unterstützt `^13.4 || ^14.0` → **v14 OK** | Offener Consent-Prüfpunkt erledigt ✅ |
| **DeepL (`web-vision/deepltranslate-core`)** | v14-Support **im Werden** (6.0.0-dev nutzt v14, „respects v14 translation workflow"); stabil noch nicht final | DE/EN-Automatik **später**; Start ggf. manuell übersetzt oder mit dev-Version |
| **Hetzner Cloud** | Preise April+Juni 2026 angehoben; CX22 (2 vCPU/4 GB/40 GB NVMe) im niedrigen einstelligen €-Bereich/Monat | CX22 als Einstieg realistisch (Details in §4) |

## 1. Zielbild

Zwei-System-Architektur unter einer Marke:
- **bockwurst.cc** → TYPO3 v14 (Hauptseite: Marke, Profil, Tourenportal, Zwift, 6 Points, Blog).
- **events.bockwurst.cc** → der bestehende statische Event-Guide.

**Netlify-Ausstieg (neuer Wunsch):** Der Event-Guide soll **weg vom kostenpflichtigen Netlify-Abo**. Optionen in §5 — favorisiert: alles auf **einen** Hetzner-VPS konsolidieren.

## 2. Vorgehen (bestätigt: lokal-zuerst)

```
Lokal (DDEV) bauen  →  in Git versionieren  →  auf Hetzner-VPS deployen
```
Vorteile: reproduzierbar, kein Risiko für Live-Infra, gleiche PHP-/DB-Version wie Produktion. DDEV liefert PHP, Composer, MariaDB, Webserver **in Containern** – auf dem Windows-Host wird **kein** PHP/Composer gebraucht.

**Host-Voraussetzungen (lokal):** Docker Desktop (installiert, muss gestartet werden) + DDEV (noch zu installieren, am besten unter WSL2 – WSL2 ist vorhanden). Das ist der erste konkrete Setup-Schritt nach Plan-Abnahme.

## 3. Hosting-Auswahl (Hilfe zur Entscheidung)

TYPO3 braucht: PHP 8.2+, MariaDB/MySQL, Webserver (nginx/Apache), Composer, HTTPS. Drei Wege:

| Weg | Was | Für/Wider | Kosten (grob) |
|---|---|---|---|
| **A) Hetzner Cloud VPS (self-managed)** *(Vision-Wahl)* | CX22/CAX selbst einrichten (Ubuntu 24.04, nginx, PHP-FPM, MariaDB, Certbot) | + volle Kontrolle, günstig, kann Event-Guide **mit**hosten (Netlify raus) · − du/wir sind Admin (Updates, Security, Backups) | ~5–8 €/Monat + Domain |
| **B) Managed TYPO3-Hosting** (z. B. Mittwald, jweiland, Deployer-Hoster) | TYPO3-optimierte Umgebung, Updates/Backups inklusive | + wenig Sysadmin, TYPO3-Support · − teurer, weniger frei, Event-Guide-Konsolidierung schwieriger | ~15–40 €/Monat |
| **C) Hetzner Webhosting** (Shared) | Klassisches Webhosting-Paket mit PHP 8.x/MariaDB | + billig, gemanagt · − oft kein Composer-Deploy/SSH-Komfort, für TYPO3 v14 eng | ~5–10 €/Monat |

**Empfehlung: A) Hetzner Cloud VPS** – passt zur Vision, ist am günstigsten und erlaubt, **den Event-Guide gleich mitzuhosten** (→ Netlify-Abo weg). Größe:
- **Start: CX22** (2 vCPU, 4 GB RAM, 40 GB NVMe) – reicht für TYPO3 + statischen Event-Guide bei kleinem Traffic.
- **Alternative CAX11/CAX21** (ARM/Ampere) – oft besseres Preis-Leistung; nur prüfen, ob alle Extensions ARM-tauglich sind (bei TYPO3/PHP i. d. R. unkritisch).
- Hochskalieren (CPX) jederzeit möglich, falls Traffic wächst.
- **Standort:** Deutschland (Nürnberg/Falkenstein) – DSGVO-nah, niedrige Latenz.

> Sysadmin-Realität: Weg A heißt, wir richten Server, TLS, Backups und Updates selbst ein. Das ist gut automatisierbar (Setup-Skript, unattended-upgrades, Backup-Cron), aber es ist laufende Verantwortung. Wenn du das **nicht** willst, ist B (Managed) der bequemere, teurere Weg – dann bleibt der Event-Guide separat.

## 4. Netlify-Ausstieg – entschieden: Cloudflare Pages

**Grund fürs Netlify-Abo (geklärt):** Viele Deployments (Bugfixes nach Launch) haben die Build-Credits aufgefressen. Der Event-Guide hat **keinen Build-Schritt**, trotzdem zählt bei Netlify jeder Deploy. Lösung: ein statischer Host **ohne** Build-Minuten-Modell.

**Domain liegt bei Cloudflare** → ideale, kostenlose Lösung:

- **Event-Guide → Cloudflare Pages** (kostenlos): verbindet sich mit dem GitHub-Repo `sport-events`, Auto-Deploy bei Push, **unbegrenzte Deployments, keine Build-Credits**, Custom Domain `events.bockwurst.cc`, TLS gratis.
- **Formular-Funktion `create-issue` → Cloudflare Pages Function / Worker** (Free-Tier): ersetzt die Netlify-Funktion; `GITHUB_ISSUES_TOKEN` als Worker-Secret.
- **DNS (schon bei Cloudflare):** `bockwurst.cc` A-Record → VPS-IP; `events.bockwurst.cc` → Cloudflare Pages.
- **Scraper-Cron bleibt in GitHub Actions** – unabhängig vom Hosting.
- Ergebnis: **Netlify komplett raus, 0 €.**

*(Alternativ als schneller Zwischenschritt: Netlify-Abo auf Free herunterstufen. Aber da die Deploy-Häufigkeit das Problem war und Cloudflare schon da ist, gehen wir direkt auf Pages.)*

## 5. TYPO3-Projekt – Aufbau (lokal, DDEV)

Schritte (nach Plan-Abnahme, ich führe dich durch bzw. mache es mit dir):

1. **Voraussetzungen:** Docker Desktop starten; DDEV installieren (WSL2).
2. **Neues Repo** `bockwurst-cc` (eigenes Git-Repo, getrennt vom `sport-events`).
3. **DDEV-Projekt** initialisieren: `ddev config` (Projekttyp `typo3`, docroot `public`, PHP 8.3, MariaDB, webserver nginx-fpm).
4. **Composer-TYPO3 v14** aufsetzen:
   ```
   ddev composer create "typo3/cms-base-distribution:^14"
   ddev exec vendor/bin/typo3 setup   # non-interaktiv möglich
   ```
5. **Sitepackage-Extension** anlegen (`packages/bockwurst_sitepackage/`) – Struktur in §6.
6. **Basis-Konfiguration:** Site-Konfiguration (`config/sites/main/config.yaml`), Root-Page, TypoScript/TSconfig, Fluid-Templates.
7. Lokal aufrufen: `https://bockwurst-cc.ddev.site`.

## 6. Sitepackage-Struktur (Fluid/SCSS, Branding)

```
packages/bockwurst_sitepackage/
├── composer.json
├── ext_emconf.php
├── Configuration/
│   ├── Sets/Bockwurst/           # TYPO3 v14 "Site Sets" (löst statische TS-Includes ab)
│   │   ├── config.yaml
│   │   ├── setup.typoscript
│   │   └── constants.typoscript
│   ├── TsConfig/Page/
│   └── Services.yaml
├── Resources/
│   ├── Private/
│   │   ├── Templates/ Layouts/ Partials/   # Fluid
│   │   └── Scss/ (→ Build zu Public/Css)
│   └── Public/
│       ├── Css/ JavaScript/ Images/
│       └── Fonts/                 # selbst gehostete woff2 (kein Google Fonts – wie Event-Guide)
└── ...
```
- **v14-Neuerung:** „Site Sets" statt der alten statischen TypoScript-Includes – der Plan nutzt Site Sets.
- **SCSS-Build:** klein halten (z. B. `ddev`-Task oder npm im Sitepackage), Ergebnis committed.
- **Branding:** bockwurst-Design an den bestehenden Event-Guide angelehnt (Farbwelt, selbst gehostete Schriften).

## 7. Extensions (v14-Kompatibilität geprüft)

| Zweck | Extension | v14 | Hinweis |
|---|---|---|---|
| Cookie-Consent / externe Medien | `sgalinski/sg-cookie-optin` **8.0.3** | ✅ `^14.0` | Klick-zum-Laden für YT/Spotify/Karten (siehe Consent-Konzept) |
| SEO | **TYPO3-Core `seo`** | ✅ | statt Rank Math (WP); XML-Sitemap, Meta, hreflang |
| DE/EN-Automatik | `web-vision/deepltranslate-core` | ⚠️ dev | v14-Support im Werden → Phase später; Start manuell/dev |
| (optional) Consent-Alternativen | `content_consent`, `media2click` | ✅ | Fallback, falls sg_cookie_optin-Detail hakt |

## 8. Mehrsprachigkeit DE/EN

- TYPO3-**natives** L10n: zweite Site-Language `en` in der Site-Config, hreflang über Core-`seo`.
- Übersetzung: zunächst **manuell** (Inhalte einmalig), DeepL-Automatik nachrüsten, sobald `deepltranslate-core` für v14 stabil ist.
- Passt zur INHALTS-Entscheidung „DE-Start, EN gleich mit".

## 9. Deployment (lokal → VPS) – späterer Schritt

1. VPS provisionieren (Hetzner CX22, Ubuntu 24.04), Basis-Härtung (SSH-Key-only, Firewall, unattended-upgrades).
2. Stack: nginx + PHP-FPM 8.3 + MariaDB + Composer + Certbot (Let's Encrypt).
3. Deploy: Git-basiert (`git pull` + `composer install --no-dev` + `typo3 cache:flush` + DB-Migration) – als Skript/Webhook oder GitHub Action mit SSH-Deploy.
4. DNS: A-Record `bockwurst.cc` → VPS; `events.bockwurst.cc` → je nach Netlify-Entscheidung (CNAME Netlify **oder** auf denselben VPS).
5. TLS via Certbot für beide Hostnamen.
6. Backups: DB-Dump + Files nach Hetzner Storage Box / S3, per Cron.

## 10. Phasen-Roadmap

- **Phase 0 – Fundament (jetzt):** DDEV + TYPO3 v14 + Sitepackage lokal lauffähig; Git-Repo `bockwurst-cc`.
- **Phase 1 – Inhalte-Grundgerüst:** Seitenbaum (Start, Über Bockwurst, Touren, Zwift, 6 Points, Recht), Navigation, Footer, DE/EN-Skelett, Consent installiert.
- **Phase 2 – Hosting live:** VPS buchen + einrichten, Domain/TLS, erstes Deploy von bockwurst.cc.
- **Phase 3 – Netlify-Ausstieg:** Event-Guide auf VPS (Option 2) oder Netlify Free (Option 1); Formular-Funktion ersetzen.
- **Phase 4 – Tourenportal & Co.:** Tour-Detailseiten (Strava+YouTube, consent-gated), Startseite, 6-Points-Landingpage.
- **Phase 5 – DeepL-Automatik**, Blog, Reichweite.

## 11. Entscheidungen (Stand 2026-07-01)

1. **Hosting-Weg:** ✅ **Self-managed Hetzner-VPS** (entschieden 2026-07-01). Günstig + volle Kontrolle; Wartung wird automatisiert (unattended-upgrades, Backup-Cron, Ein-Befehl-Deploy), damit der laufende Aufwand klein bleibt.
2. **VPS-Größe:** ✅ **CX22** (x86, 2 vCPU/4 GB/40 GB, DE). Sparvariante CAX11 (ARM) möglich. *(Gilt, falls Weg = VPS.)*
3. **Netlify:** ✅ Kostenpflichtig wegen vieler Deploy-Credits → gelöst via **Cloudflare Pages** (§4), Abo entfällt.
4. **Domain:** ✅ `bockwurst.cc` bei **Cloudflare** registriert → DNS + Pages + TLS dort.
5. **Repo:** ✅ neues GitHub-Repo `stefangriessmann/bockwurst-cc` (bestätigt), wird bei Phase-0-Start angelegt.

## 12. Kostenüberblick (grob, monatlich)

| Posten | Weg A (VPS) | Weg B (Managed) |
|---|---|---|
| Server | ~5–8 € (CX22) | ~15–40 € |
| Domain `.cc` | ~1–2 € (Jahres-/12) | dito |
| Netlify | 0 € (Free) bzw. entfällt | 0 €/entfällt |
| DeepL API | nutzungsabhängig, später | dito |
| **Summe** | **~6–10 €** | **~16–42 €** |

## Quellen

- TYPO3 v14 LTS: https://get.typo3.org/release-notes/14.0.0 · https://news.typo3.com/article/typo3-v14-lts-the-next-generation
- sg_cookie_optin (v14): https://packagist.org/packages/sgalinski/sg-cookie-optin
- DeepL v14: https://github.com/web-vision/deepltranslate-core · https://docs.typo3.org/p/web-vision/deepltranslate-core/main/en-us/Editor/Usage/Index.html
- Hetzner Cloud/Preise: https://www.hetzner.com/cloud/ · https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
