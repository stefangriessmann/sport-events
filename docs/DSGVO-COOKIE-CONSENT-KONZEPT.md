# DSGVO · Cookie-Consent & externe Inhalte – Konzept (bockwurst.cc / TYPO3)

> Stand: 24.06.2026 · Säule: Infrastruktur & Domain (TYPO3-Fundament) · Quelle-Verweise: VISION-bockwurst-cc.md, TECHNISCHE-DOKUMENTATION.md
>
> **Kein Rechtsrat.** Dieses Dokument beschreibt das technische und konzeptionelle Vorgehen. Die rechtliche Bewertung (Datenschutzerklärung, Auftragsverarbeitung) gehört vor dem Launch in fachkundige Hände.

## 1. Ziel

Einen Consent-Layer **einmal sauber** aufsetzen, damit externe Inhalte überall einheitlich, rechtssicher und optisch ansprechend eingebunden werden: YouTube-Videos, Spotify-Player, Karten und alles, was später dazukommt. Der Nutzer entscheidet, der Inhalt lädt erst nach Zustimmung – und das fühlt sich nicht wie eine Hürde an, sondern wie ein gestalteter Teil der Seite.

Das Prinzip steckt schon im Tour-Detail-Design: Statt eines sofort ladenden iframes zeigt die Seite eine **Vorschaukachel mit Button**, und erst der Klick lädt das Video bzw. den Player.

## 2. Welche externen Dienste übertragen Daten?

| Dienst | Wofür auf bockwurst.cc | Datenschutz-Relevanz | Consent nötig? |
|---|---|---|---|
| **YouTube** | Tour-Videos, Shorts auf der Startseite | Google-Server, Cookies, IP-Übertragung | **Ja** (externe Medien) |
| **Spotify** | „Sound der Tour" / Playlists je Tour | Cookies, Nutzungsstatistik | **Ja** (externe Medien) |
| **Karten (Leaflet + OpenStreetMap-Kacheln)** | Streckenkarte, Touren-Landkarte | IP-Übertragung an Kachel-Server; i. d. R. keine Cookies | **Ja**, sobald von externem Tile-Server geladen (s. 5.3) |
| **Strava** (Embeds/API, später) | Streckendaten, ggf. eingebettete Aktivitäten | externe Übertragung bei Embed | **Ja** bei Embed; serverseitiger API-Abruf ist unkritisch |
| **Google Fonts** | Typografie | **bereits selbst gehostet** → keine Übertragung an Google | **Nein** (Vorteil, schon gelöst) |
| **Statistik/Reichweite** (optional, später) | Besucherzahlen | je nach Tool Cookies/IP | **Ja**, eigene Kategorie |

Wichtig: **Notwendige** Cookies (z. B. die Consent-Entscheidung selbst, ggf. Session) brauchen keine Zustimmung. Alles andere ist standardmäßig **aus**, bis der Nutzer zustimmt.

## 3. Rechtlicher Rahmen (Kurzfassung)

- **§ 25 TDDDG** (vormals TTDSG) + **DSGVO**: Vor dem Setzen nicht-notwendiger Cookies bzw. dem Laden externer Inhalte braucht es eine **aktive Einwilligung** (Opt-in).
- **Ablehnen so einfach wie Akzeptieren**: gleichwertige Buttons auf der ersten Ebene, kein „Dark Pattern".
- **Granular**: pro Kategorie (notwendig / funktional / externe Medien / Statistik) einzeln wählbar.
- **Widerruf jederzeit**: ein dauerhaft erreichbarer Link/Button („Cookie-Einstellungen") im Footer.
- **Nachweisbar & dokumentiert**: Einwilligung wird protokolliert; die **Datenschutzerklärung** listet jeden Dienst, Zweck und Empfänger.
- **Vor-Einwilligung verboten**: kein externer Inhalt lädt vor dem Klick (deshalb Klick-zum-Laden, s. 5).

## 4. Consent-Kategorien (Vorschlag)

1. **Notwendig** – immer aktiv, nicht abwählbar (Consent-Speicherung, Sicherheit, Session).
2. **Funktional** – Komfort, der externe Dienste einbindet (z. B. Karten).
3. **Externe Medien** – YouTube, Spotify, Strava-Embeds.
4. **Statistik** – nur falls später ein Analyse-Tool dazukommt.

Bewusst schlank gehalten: weniger Kategorien = klarere Entscheidung für den Nutzer.

## 5. Technische Umsetzung in TYPO3

### 5.1 Zwei Bausteine, die zusammenspielen

1. **Consent-Banner / -Manager** – das Einwilligungs-Layer beim ersten Besuch, granular, mit Footer-Link zum Widerruf.
2. **Klick-zum-Laden (2-Klick-Lösung)** für jeden Embed – Platzhalterkachel mit Vorschaubild + Button; lädt den iframe erst nach Klick. Verknüpft mit dem Consent: Wer „Externe Medien" global akzeptiert, sieht die Inhalte direkt; wer nicht, bekommt pro Block die Wahl.

### 5.2 Gesetzte Extension: `sg_cookie_optin` (sgalinski)

**Entscheidung (Annahme für die Planung):** bockwurst.cc setzt **`sg_cookie_optin`** von sgalinski ein.

- **In-House-Referenz:** Die Extension läuft bereits bei **FutureSax** produktiv (erkennbar am „User-Hash" im Banner – die typische sg_cookie_optin-Signatur). Konfiguration, Styling und Stolpersteine sind also intern bekannt → geringerer Setup-Aufwand.
- **Funktionsumfang:** granulares Opt-in-Banner, Dienst-Blockierung inkl. Klick-zum-Laden für externe Medien, anonymer Einwilligungs-Hash als DSGVO-Nachweis, seit v7.1 Unterstützung für strenge Content-Security-Policy (CSP-Nonce). Aktiv gepflegt (letztes Paket-Update April 2026).
- **Kategorien** decken den Plan aus Abschnitt 4 ab: „Essenziell" = Notwendig, „Externe Inhalte" = Externe Medien (YouTube/Spotify/Karten), „Statistik" für späteres Tracking.
- **Offener Prüfpunkt:** **TYPO3 v14 verifizieren.** Offiziell dokumentiert ist bisher v13; vor dem Setup die sg_cookie_optin-Version mit v14-Support prüfen. Fallback, falls v14 noch nicht unterstützt wird: kurzzeitig auf einer kompatiblen Version starten oder spezialisierte Medien-Blocker (`media2click`, `content_consent`) ergänzen.

### 5.3 Quick Wins, die Aufwand sparen

- **Google Fonts selbst hosten** – bereits umgesetzt → kein Font-Consent nötig.
- **YouTube über `youtube-nocookie.com`** einbetten – TYPO3-Core nutzt diese Domain standardmäßig; reduziert das Tracking deutlich (Consent bleibt trotzdem nötig).
- **Karten-Kacheln** möglichst datensparsam: OpenStreetMap-Standardkacheln werden extern geladen → in „Funktional"/„Externe Medien" einordnen. Option für später: ein eigener/gecachter Tile-Proxy, dann lädt die Karte ohne Drittübertragung.
- **Vorschaubilder lokal** ausliefern (nicht von YouTube/Spotify ziehen), damit vor dem Klick keine Daten abfließen.

## 6. Konsequenz fürs Design (gilt schon für die Tour-Detailseite)

Jeder Embed wird als **gestaltete Platzhalterkachel** gebaut, nicht als nackter iframe:

- lokales Vorschaubild (bei Video z. B. das Tour-Cover),
- kleines Dienst-Logo + kurzer Hinweis („Video wird von YouTube geladen – dabei werden Daten an Google übertragen"),
- Button **„Laden"** (einmalig) und optional **„immer laden"** (setzt die Kategorie-Einwilligung).

Damit ist die 2-Klick-Lösung kein Fremdkörper, sondern Teil des Layouts – genau wie im aktuellen Tour-Design für Video und Spotify vorgesehen.

## 7. Einordnung in die Roadmap

Gehört ins **TYPO3-Fundament** und muss **vor dem Launch der ersten Seite mit Embeds** stehen (also vor der ersten öffentlichen Tour-Detailseite). Reihenfolge:

1. TYPO3-Setup steht (Domain + Server + Sitepackage).
2. `sg_cookie_optin` installieren (v14-Kompatibilität prüfen) und konfigurieren.
3. Klick-zum-Laden-Block als wiederverwendbares Element bauen (für YouTube + Spotify + Karten).
4. Datenschutzerklärung mit Dienst-Liste erstellen (fachkundige Prüfung).
5. Erst dann Embeds live schalten.

## Quellen

- [sgalinski – Cookie-Optin für TYPO3](https://www.sgalinski.de/en/typo3-products-web-development/cookie-optin-for-typo3/)
- [sgalinski/sg-cookie-optin – Packagist](https://packagist.org/packages/sgalinski/sg-cookie-optin)
- [TYPO3 News – How to make your TYPO3 application GDPR compliant](https://typo3.com/blog/how-to-make-your-typo3-application-gdpr-compliant)
- [content_consent – TYPO3 Extension (GitHub)](https://github.com/t3solution/content_consent)
- [brain_youtube – DSGVO-konforme YouTube-Einbettung](https://www.brain-appeal.com/en/brain-youtube)
- [VisionConnect – Externe Medien DSGVO-konform einbinden](https://www.visionconnect.de/blog/2023/externe-medien-dsgvo-konform-einbinden/)
