# Bockwurst Sport Events – Konzept: Expansion nach UK

> **Stand:** 22.06.2026 · **Status:** Konzept (vor technischer Umsetzung) · **Sportarten:** Rennrad, Triathlon, Freiwasserschwimmen, Laufen, Challenge-Walks

Dieses Dokument beschreibt Quellen, Wettbewerb, Positionierung, technisches Vorgehen und eine Phasen-Roadmap für die Ausweitung des Event-Guides auf das Vereinigte Königreich. Es ist die Entscheidungsgrundlage, bevor Code entsteht.

---

## 1. Ausgangslage und Chance

Der Guide ist für eine Mehrländer-Nutzung bereits gut vorbereitet:

- Das Datenschema trägt schon ein `country`-Feld (aktuell durchgängig `"DE"`).
- Das Frontend ist zweisprachig angelegt (`data-de`/`data-en`); eine englische Oberfläche existiert also bereits im Ansatz.
- Der Umkreisfilter ist generisch (Haversine über `lat`/`lon`); er funktioniert mit jeder Koordinatenquelle, nicht nur mit deutschen PLZ.

UK ist als Markt attraktiv, weil die Ausdauer-Szene groß und kommerziell aktiv ist. Genau das ist aber auch die Kehrseite: Der Markt ist deutlich reifer und umkämpfter als der deutsche.

### Fokus & Abgrenzung

Es geht um **Breitensport / Jedermann-Events**: Sportives, RTF-/Gravel-Ausfahrten, Audax/Brevets, offene Club-Zeitfahren, Age-Group-Triathlons, Freiwasser-Mass-Events, Volks-/Trail-/Ultraläufe und Challenge-Walks. **Ausdrücklich nicht** im Fokus: Profi-/Elite-Rennen wie National Road Series, nationale Meisterschaften oder Elite-Ranglisten.

Das schärft die Quellenwahl: Aus elitelastigen Verbandsbereichen wird nur der **Breitensport-Teil** übernommen (z. B. die Sportive-/Club-Events von British Cycling, nicht die National Series; bei Leichtathletik die lizenzierten Volksläufe, nicht die Power-of-10-Elite-Ranglisten). Wo eine Quelle ausschließlich Elite listet, wird sie ausgelassen.

---

## 2. Wettbewerb in UK

Anders als in Deutschland gibt es in UK etablierte, teils gut finanzierte Aggregatoren:

| Anbieter | Modell | Einordnung |
|----------|--------|------------|
| **Find A Race** (findarace.com) | Größter UK-Aggregator für Breitensport-Events; Marktplatz, der zu Registrierungs-Anbietern (Race Roster, RunSignup) weiterleitet | Sehr breite Abdeckung über alle hier relevanten Sportarten (Sportives, Audax, Triathlon, Freiwasser, Laufen). Reines Marketing-/Discovery-Modell, keine eigene Anmeldung |
| **Let's Do This** (letsdothis.com) | Endurance-Marktplatz mit eigener Registrierung; 60 Mio. $ Series B | Starke Marke, Fokus auf Buchung/Conversion und Tools für Veranstalter |
| **Running Calendar UK**, **RunGuides**, **Finishers.com** | Lauf-/Multisport-Kalender | Solide Lauf-Abdeckung, teils international |
| **Timeoutdoors** | Outdoor-Events (Rad, Schwimmen, Walks) | Breit, aber weniger fokussiert |

**Bewertung:** Eine reine „Liste aller Events" ist in UK kein Alleinstellungsmerkmal – das machen Find A Race und Let's Do This bereits umfassend und mit Budget. Eine Differenzierung muss bewusst gesetzt werden (Abschnitt 4), sonst ist der Markteintritt aussichtslos.

---

## 3. Quellen je Sportart

Grundsatz: **Primärquellen/Verbände bevorzugen, kommerzielle Discovery-Aggregatoren meiden.** Aggregatoren wie Find A Race oder Let's Do This zu scrapen ist rechtlich heikel (ToS), technisch fragil und liefert ohnehin nur aufbereitete Sekundärdaten. Die Verbände, Anmeldeplattformen und spezialisierten Kalender sind die saubere Basis.

**Quellen-Taxonomie** (vier Ebenen, von sauber nach heikel):

1. **Verbände** – national und regional. Maßgeblich und meist scraping-tolerant.
2. **Anmelde-/Wettkampfplattformen** – SiEntries, EntryCentral, OpenTrack, Race Roster, Power of 10/RunEvents. Bündeln Club- und Grassroots-Events strukturiert; faktisch Primärdaten an der Anmeldung.
3. **Fachmagazine & Veranstalterkalender** – kuratierte Highlights, weniger einheitlich strukturiert.
4. **Kommerzielle Discovery-Aggregatoren** (Find A Race, Let's Do This) – meiden (ToS, Wettbewerb, Sekundärdaten).

**Vier Nationen:** „Gesamt UK" heißt England, Schottland, Wales und Nordirland. Mehrere Sportarten haben **Home-Nation-Verbände** mit eigenen Kalendern (z. B. Triathlon England / Triathlon Scotland / Welsh Triathlon). Die Quellenliste je Sportart muss diese regionalen Verbände mit abdecken, sonst fehlen ganze Landesteile.

**Clubs:** Einzelne Vereinsseiten zu scrapen ist unwirtschaftlich (zu viele, zu heterogen). Club-Events laufen ohnehin überwiegend über die Verbandskalender (Ebene 1) und Anmeldeplattformen (Ebene 2) – dort werden sie strukturiert eingesammelt, statt hunderte Club-Sites einzeln zu pflegen.

### Rennrad / Gravel

| Quelle | Inhalt | Struktur / Hinweis |
|--------|--------|--------------------|
| British Cycling – Events (britishcycling.org.uk/events) | Rennen, Sportives, Serien | Zentraler Verbandskalender; Detailseiten je Event |
| Cycling Time Trials (cyclingtimetrials.org.uk) | Zeitfahren, „Startsheet Finder" | UK-spezifische Disziplin (TT); strukturierte Startlisten |
| Audax UK (audax.uk/choose-a-ride/calendar-events) | Brevets/Randonnées (50–1000+ km) | Direktes Pendant zu den deutschen Brevets; klarer Kalender |
| UK Cycling Events (ukcyclingevents.co.uk) | Sportives, MTB/Gravel | Großer kommerzieller Veranstalter mit eigenem Kalender |
| Cycling UK (cyclinguk.org/event-listing) | Touren/Challenge-Rides | Breitensport-Listing |

### Triathlon

| Quelle | Inhalt | Struktur / Hinweis |
|--------|--------|--------------------|
| British Triathlon (britishtriathlon.org/events/search) | Triathlon, Duathlon, Aquathlon, Aquabike | Offizieller Verband, Event-Suche England/Wales + Schottland |
| Triathlon England (triathlonengland.org) | Meisterschaften, Qualifikationen | Ergänzend |
| UK Triathlon (uktriathlon.co.uk/events) | Veranstalter-Events | Ergänzend |

### Freiwasserschwimmen

| Quelle | Inhalt | Struktur / Hinweis |
|--------|--------|--------------------|
| Swim England (swimming.org/openwater) | Offizielle Open-Water-Termine | Verbandsquelle |
| BLDSA (bldsa.org.uk) | Langstrecken-Freiwasser | Traditionsreiche Events (z. B. ikonische Klassiker) |
| Outdoor Swimmer (outdoorswimmer.com/events) | Community-Kalender | Sehr breit, gut gepflegt |

### Laufen

| Quelle | Inhalt | Struktur / Hinweis |
|--------|--------|--------------------|
| Running Calendar UK (runningcalendar.co.uk) | 5k bis Ultra, in-person | Umfassender, klar strukturierter Kalender |
| RunGuides (runguides.com/uk) | Straße/Trail/Ultra | Ergänzend |
| Verbands-/Veranstalterseiten | Marathons, Serien | Für Großevents direkt an der Quelle |

> Hinweis zu **parkrun**: kostenlose, wöchentliche 5-km-Läufe – inhaltlich ideal zum Breitensport-Fokus, aber wiederkehrend statt Einzeltermin. Bei Aufnahme braucht es eine eigene Logik (Serie/wöchentlich); sonst bewusst weglassen.

### Challenge-Walks (Pendant zu Mammutmärschen)

| Quelle | Inhalt | Struktur / Hinweis |
|--------|--------|--------------------|
| LDWA (ldwa.org.uk/challenge_events/events_list.php) | 70+ Challenge-Events/Jahr, inkl. 100-Meilen-Flaggschiff | Eigene Events-Listenseite – gut scrapebar |
| Ultra Challenge (ultrachallenge.com) | 16+ Serien-Events, 10/25/50/100 km, „Ultra March" | Großer kommerzieller Anbieter, klare Distanzen |
| Timeoutdoors – Challenge Walks | Ergänzender Kalender | Breit |

### Regionale Verbände (Home Nations)

Pro Sportart neben dem UK-/England-Verband auch die regionalen Verbände aufnehmen:

| Sportart | Regionale Verbände |
|----------|--------------------|
| Triathlon | Triathlon England, **Triathlon Scotland** (~100 Events/Jahr), **Welsh Triathlon** (Triathlon Cymru), Triathlon Ireland (NI) |
| Rennrad | British Cycling + Heimnationen **Scottish Cycling**, **Welsh Cycling**, Cycling Ulster |
| Laufen | **England Athletics**, **scottishathletics**, **Welsh Athletics**, Athletics NI (Dachverband UKA) |
| Schwimmen | **Swim England**, **Scottish Swimming**, **Swim Wales**, Swim Ulster |

### Anmelde-/Wettkampfplattformen (Club- und Grassroots-Ebene)

Diese Plattformen sind technisch oft die ergiebigste Quelle, weil viele kleine Veranstalter und Clubs ihre Anmeldung darüber abwickeln – die Daten sind strukturiert und aktuell:

| Plattform | Schwerpunkt |
|-----------|-------------|
| **SiEntries** (sientries.co.uk) | Orientierungslauf, Trail-/Fell-Running, auch LDWA-Serien |
| **EntryCentral** (entrycentral.com) | Breite Mass-Participation-Events und Club-Mitgliedschaften |
| **OpenTrack** (opentrack.run) | Leichtathletik-Wettkämpfe, offene Datenplattform |
| **RunEvents / UKA Fixtures** (englandathletics.org/runevents, britishathletics.org.uk/ukfc-rdr) | Lizenzierte Volksläufe/Fixtures (Breitensport). *Power of 10* selbst ist Elite-Ranking → nicht relevant |
| **Race Roster / Roster Athletics** | Registrierungs-Backend von England Athletics |

> Hinweis: Auch hier ToS prüfen. Eine offene Datenplattform wie OpenTrack ist tendenziell unkritischer als ein kommerzieller Marktplatz.

### Fachmagazine & Veranstalterkalender

Eher für kuratierte Highlights und Lückenfüller als für Vollabdeckung:

| Quelle | Schwerpunkt |
|--------|-------------|
| **220 Triathlon** (220triathlon.com) | Triathlon + Sportive-Guides |
| **Outdoor Swimmer** (outdoorswimmer.com/events) | Freiwasser (bereits oben) |
| **Cycling Weekly / BikeRadar** | Rennrad-Highlights, Sportives |
| **Runner's World UK / Athletics Weekly** | Lauf-Highlights, Fixtures |
| **The Great Outdoors (TGO)** | Challenge-Walks/Hiking |
| **Active Training World** (atwevents.co.uk) | Veranstalter mit eigenem Multisport-Kalender |

---

## 4. Positionierung und Differenzierung

Gegen finanzierte Marktplätze gewinnt der Guide nicht über Vollständigkeit, sondern über **Haltung und Nutzererlebnis**:

- **Werbefrei, kostenlos, kein Tracking, keine Cookies** – das ist bei den Marktplätzen (Conversion-/Buchungsgetrieben) gerade nicht der Fall und ein glaubwürdiges Gegen-Versprechen.
- **Neutralität**: Discovery ohne Buchungs-Eigeninteresse. Der Guide verlinkt zur Original-Anmeldung, statt selbst zu vermarkten.
- **Multisport + Umkreissuche in einer Ansicht**: Rad, Triathlon, Schwimmen, Laufen, Walks gemeinsam, filterbar nach Postcode-Umkreis und Zeitraum. Die meisten UK-Quellen sind sportart-spezifisch; eine sportartübergreifende „Was ist in meinem Umkreis los"-Sicht ist eine echte Lücke.
- **Kuratierung**: Fokus auf den Breitensport-/Grassroots-Bereich, sauber statt vollständig.

> Realistische Einordnung: Differenzierung über Haltung ist tragfähig für eine Nische und persönliche Marke, ersetzt aber keine Reichweite. Wer rein auf Eventzahl gegen Find A Race antritt, verliert. Wer eine kuratierte, werbefreie, sportartübergreifende Umkreissuche bietet, hat einen verteidigbaren Winkel.

---

## 5. Technisches Vorgehen

Die bestehende Architektur lässt sich ohne Bruch erweitern – die Mehrländer-Fähigkeit ist im Kern schon angelegt.

### 5.1 Datenmodell

Zwei Optionen:

- **A) Land im Dateinamen** (empfohlen): je Sportart eine Datei pro Land, z. B. `radsport-gb.json`, `laufen-gb.json`. Vorteil: Scraper, Schwellenwerte (`MIN_EVENTS`) und Caches bleiben pro Land sauber getrennt; ein fehlschlagender UK-Scraper kann die DE-Daten nicht beschädigen.
- **B) Reines `country`-Feld** in den bestehenden Dateien. Einfacher im Frontend, aber riskanter bei Scraper-Fehlern und Schwellenwert-Logik.

Empfehlung: **A**. Das Frontend lädt dann zusätzlich die `*-gb.json` und führt sie wie die DE-Daten ins `EV`-Array zusammen; das `country`-Feld steuert Anzeige und Filter.

### 5.2 Geocoding

Statt der deutschen PLZ-Karte kommt für UK **postcodes.io** zum Einsatz: kostenlose, offene API (ONS-Daten, MIT-Lizenz, keine Authentifizierung, Self-Hosting möglich), liefert `lat`/`lon` zu UK-Postcodes. Damit funktioniert der bestehende Umkreisfilter unverändert – nur die Eingabevalidierung (UK-Postcode-Format statt 5-stelliger PLZ) und die Nachschlage-Quelle ändern sich. Für die statische Vorab-Karte lässt sich analog zur `plz_map.json` eine `postcode_map_gb.json` aus dem ONS-Postcode-Directory erzeugen.

### 5.3 Frontend (entschieden)

- **Auftritt: Länderfilter auf bockwurst.cc** – ein zusätzlicher Filter über das `country`-Feld (DE / UK), **keine** eigene `.co.uk`-Domain. Ein Auftritt, eine Codebasis, ein Deploy.
- **Sprache: automatisch über die Browsersprache.** Beim Laden `navigator.language` auswerten – `de*` → Deutsch, sonst Englisch. Der bestehende manuelle DE/EN-Umschalter bleibt als Override erhalten; die Übersetzungs-Mechanik (`data-de`/`data-en`) ist bereits vorhanden. Optional die zuletzt gewählte Sprache in `localStorage` merken.
- **Einheiten**: Distanz an das Land koppeln (DE: km, UK: miles) oder einen separaten Umschalter anbieten.
- **Sinnvolle Kopplung**: Bei Browsersprache Englisch bietet sich an, den Länderfilter initial auf UK vorzubelegen (und umgekehrt) – beides bleibt aber frei umschaltbar.

### 5.4 Scraper-Architektur

Unverändert zur bestehenden Konvention: ein Modul je Quelle mit `fetch(year) -> list[dict]`, Eintrag in `SOURCES` von `update_data.py`. Jeder UK-Scraper normalisiert auf dasselbe Schema (`date_iso`, `titel`, `ort`, `lat`, `lon`, `country: "GB"`, `art`, …). Der wöchentliche Cron und der `MIN_EVENTS`-/70%-Guard greifen automatisch mit.

### 5.5 Dedup über Quellen

Da mehrere UK-Quellen dieselben Events listen (z. B. ein Sportive bei British Cycling und Find A Race), ist eine **Deduplizierung** nötig (über `url`, sonst `titel`+`date_iso`). Das spricht zusätzlich dafür, primär Verbandsquellen zu nutzen und Aggregatoren wegzulassen – sonst potenziert sich das Doppel-Problem.

---

## 6. Rechtliche Aspekte

- **robots.txt und ToS je Quelle prüfen.** Verbände sind meist unkritisch; kommerzielle Aggregatoren (Find A Race, Let's Do This) untersagen Scraping in der Regel und sind ohnehin tabu (auch wettbewerblich heikel).
- **Faire Last**: niedrige Request-Rate, Caching, Identifikation via User-Agent – wie bei den DE-Scrapern (das radnet-Rate-Limiting ist eine bekannte Lehre).
- **Verlinkung statt Kopie**: nur Eckdaten plus Link zur Originalseite; keine Volltext-/Bildübernahme.
- **Partnerschaften statt Scraping** als perspektivische Alternative: Verbände stellen teils Feeds/APIs bereit; eine Anfrage kann eine saubere Datenquelle erschließen und gleichzeitig Reichweite bringen.

---

## 7. Risiken und offene Entscheidungen

**Risiken**

- Reifer, finanzierter Wettbewerb → Reichweite ist die eigentliche Hürde, nicht die Technik.
- Quellen-Heterogenität (jede Sportart eigene Seite, andere HTML-Struktur) → mehr Scraper-Pflegeaufwand als in DE.
- Distanz-/Einheiten-Thema (miles), Postcode-Validierung, ggf. Nordirland (Irish National Grid bei postcodes.io).

**Entschieden**

- **Auftritt:** Länderfilter auf bockwurst.cc (kein eigener `.co.uk`-Auftritt).
- **Sprache:** automatisch über die Browsersprache, manueller DE/EN-Umschalter bleibt als Override.
- **Pilot-Umfang:** Start mit **Radsport**, danach Sportart für Sportart.
- **Einheiten:** an das Land koppeln – UK = miles, DE = km (intern Haversine in km, nur Anzeige umrechnen).
- **parkrun:** vorerst **weglassen** (wiederkehrender Wochentermin, kein Einzelevent). Kann später mit eigener Serien-/Wochenlogik nachgerüstet werden, falls gewünscht.

**Bewusst vertagt (später entscheiden)**

- **Aggregatoren** (Find A Race, Let's Do This): meiden vs. Partnerschaft/Affiliate. Entscheidung, wenn die Abdeckung der Primärquellen und etwaige Lücken sichtbar sind.

---

## 8. Roadmap in Phasen

**Phase 0 – Validierung (kein Code).** robots.txt/ToS der Primärquellen prüfen; je Quelle 5–10 Beispiel-Events manuell sichten (Felder, Geodaten-Verfügbarkeit). Ergebnis: belastbare Quellen-Shortlist.

**Phase 1 – Pilot, eine Sportart.** Empfehlung: **Challenge-Walks** (LDWA + Ultra Challenge) oder **Audax/Sportives** – beide haben saubere, listenartige Quellen und sind in DE bereits verstanden. Ein UK-Scraper, `*-gb.json`, postcodes.io-Anbindung, Länderfilter im Frontend. Gegen Staging testen.

**Phase 2 – Geocoding & Filter produktiv.** `postcode_map_gb.json` aus ONS erzeugen, Umkreisfilter mit UK-Postcodes, Einheiten-Umschaltung (km/miles).

**Phase 3 – Sportarten ausrollen.** Restliche Sportarten Quelle für Quelle ergänzen, Dedup scharf stellen, Tests (Playwright) um UK-Fälle erweitern.

**Phase 4 – Auftritt & Reichweite.** Domain-/Sprachentscheidung umsetzen, SEO (englische Meta-Daten, hreflang ist im Frontend bereits vorgesehen), erste Reichweiten-Kanäle.

**Phase 5 – optional.** Verbands-Partnerschaften/Feeds statt Scraping; Newsletter.

---

## 9. Empfehlung

Technisch ist die Erweiterung gut machbar und risikoarm – die Architektur ist mehrländerfähig, postcodes.io ersetzt die PLZ-Karte sauber, die Scraper-Konvention bleibt. Der eigentliche Engpass ist **nicht** die Technik, sondern Wettbewerb und Reichweite.

Vorschlag: **klein und fokussiert starten** – eine Sportart mit sauberer Primärquelle als Pilot, sportartübergreifende Umkreissuche und das werbefrei/kein-Tracking-Versprechen als Differenzierung konsequent in den Vordergrund. Erst wenn der Pilot Nutzung zeigt, breiter ausrollen.

---

## Quellen

- Find A Race: https://findarace.com/ (Sportives, Audax, Triathlon, Open Water, Running)
- Let's Do This: https://www.letsdothis.com/gb/ · Funding: https://insider.fitt.co/lets-do-this-raises-60m-for-endurance-event-marketplace/
- findarace Modell: https://endurance.biz/2024/industry-news/event-listings-site-findarace-com-open-for-business-in-the-usa/
- British Cycling Events: https://www.britishcycling.org.uk/events/home
- Cycling UK Event-Listing: https://www.cyclinguk.org/event-listing
- UK Cycling Events: https://www.ukcyclingevents.co.uk/
- Audax UK Kalender: https://www.audax.uk/choose-a-ride/calendar-events/
- Cycling Time Trials: https://www.cyclingtimetrials.org.uk/
- British Triathlon Event-Suche: https://www.britishtriathlon.org/events/search
- Triathlon England: https://www.triathlonengland.org/
- Swim England Open Water: https://www.swimming.org/openwater/open-water-swimming-events/
- BLDSA: https://bldsa.org.uk/
- Outdoor Swimmer Events: https://outdoorswimmer.com/events/
- Running Calendar UK: https://www.runningcalendar.co.uk/
- RunGuides UK: https://www.runguides.com/uk/runs
- LDWA Challenge-Events: https://ldwa.org.uk/challenge_events/events_list.php
- Ultra Challenge: https://www.ultrachallenge.com/the-events/
- Postcodes.io (Geocoding): https://postcodes.io/ · Doku: https://postcodes.io/docs/overview/
- ONS Open Postcode Geo: https://www.data.gov.uk/dataset/091feb1c-aea6-45c9-82bf-768a15c65307/open-postcode-geo2

**Regionale Verbände & Leichtathletik-Fixtures**
- Triathlon Scotland: https://www.triathlonscotland.org/events/
- Welsh Triathlon: https://welshtriathlon.org/
- England Athletics RunEvents: https://www.englandathletics.org/runevents/
- Power of 10: https://www.powerof10.uk/ · runbritain Rankings: https://www.runbritainrankings.com/
- UKA Fixtures Calendar: https://www.britishathletics.org.uk/ukfc-rdr/

**Anmelde-/Wettkampfplattformen**
- SiEntries: https://www.sientries.co.uk/
- EntryCentral: https://www.entrycentral.com/
- OpenTrack: https://opentrack.run/ · Daten: https://data.opentrack.run/en-gb/x/

**Fachmagazine & Veranstalterkalender**
- 220 Triathlon: https://www.220triathlon.com/
- Active Training World: https://www.atwevents.co.uk/calendars/sport-events/

---

## Anhang A: Phase-0-Befund Radsport (Stand 22.06.2026)

Geprüft per direkter Sichtung von robots.txt, Listen- und Detailseiten.

### robots.txt / ToS-Ampel

| Quelle | Ampel | Befund |
|--------|-------|--------|
| **Cycling UK** (cyclinguk.org) | 🟢 | `/event-listing` nicht gesperrt. **Server-gerendert** (Drupal) – Events stehen im HTML |
| **UK Cycling Events** (ukcyclingevents.co.uk) | 🟢 | Nur admin/cart/Filter-Params gesperrt; eigener `Claude-User`-Block erlaubt Event-Seiten. Server-gerendert |
| **Audax UK** (audax.uk) | 🟢 (mit Aufwand) | Erlaubt, `Crawl-delay: 10`. Kalender wird aber **per JavaScript nachgeladen** → API-Discovery oder Headless nötig |
| **Cycling Time Trials** (cyclingtimetrials.org.uk) | 🟡 | `/event-finder/` per robots gesperrt → Event-Discovery eingeschränkt |
| **British Cycling** (britishcycling.org.uk) | 🔴 | **ClaudeBot komplett gesperrt**, `/events?*`-Listing gesperrt (nur `/events/details/*` erlaubt), `ai-train=no`. Meiden |

### Struktur & Felder (Beispiel Cycling UK)

- **Listing** (server-gerendert, paginiert): Datum, Titel, Startort (Stadt), Distanz (mi), **Event-Typ** (Sportive/Challenge Ride, Mass Participation Charity Ride, Local Group Event, Audax, Meeting/AGM, …), Surface, Detail-Link.
- **Detailseite**: volle **Adresse inkl. Postcode** (z. B. „Elstead Village Hall, GU8 6DG"), Distanz mi **und** km, Typ, Audax-Kategorie, Veranstalter, Datum + Uhrzeit, externe Event-URL.
- ⇒ Postcode auf der Detailseite ⇒ **postcodes.io** ⇒ `lat`/`lon`: der Umkreisfilter ist damit direkt bedienbar.
- **UK Cycling Events**: Listing mit Name, County, Datum, Distanzen (km), Detail-Link; Buchung über Let's Do This.

### Volumen (grobe Indikation)

- **Cycling UK**: sehr viele Einträge (mehrere Pagination-Seiten), aber **gemischt** – darunter viele Local-Group-Rides, AGMs, Webinare. Der **Breitensport-Teil** (Sportive/Challenge + Mass Participation Charity + Audax) ist die relevante Teilmenge; exakte Zahl erst nach Paginierung + Typ-Filter.
- **UK Cycling Events**: ~5–6 große Sportives pro Saison (ein Veranstalter), dafür hochwertig.

### Dubletten (zentrale Erkenntnis)

- **Cycling UK aggregiert Audax-Events** – die Detailseite verlinkt direkt auf `audax.uk`. ⇒ Überschneidung Cycling UK ∩ Audax UK.
- **UK Cycling Events bucht über Let's Do This** ⇒ Überschneidung mit den kommerziellen Aggregatoren.
- ⇒ **Cycling UK als breite Basis** (deckt Sportives + Audax + Charity-Rides **mit Postcode** ab); Audax UK nur **ergänzend** für Lücken; UK-Cycling-Events-Sportives separat. Dedup über externe Event-URL bzw. `titel`+`date_iso` (+ Postcode).

### Empfehlung Pilot Radsport

1. **Primärquelle: Cycling UK.** Scraper: Listing paginieren → auf Breitensport-Typen filtern → Detailseite je Event für Postcode → `postcodes.io` für `lat`/`lon`. Liefert in einem Aufwasch Sportives, Charity-Rides und Audax mit Geodaten.
2. **Ergänzend: UK Cycling Events** (wenige, aber starke Sportives).
3. **Audax UK** erst in Phase 1+ (API/Headless), nur falls Cycling-UK-Abdeckung lückenhaft.
4. **British Cycling & CTT** vorerst nicht (robots/ClaudeBot).

### Volumen-Messung Cycling UK (22.06.2026, per Sampling)

- Liste reicht über **~9 Seiten à ~50 Einträge** (Seite 10 leer) → **~400–450 Einträge** für den Rest der Saison 2026 (Seite 0 = 7.–27. Juni).
- **Aber gemischt:** Auf Seite 0 sind nur ~12–15 der ~50 Einträge echte Breitensport-Events (Sportive/Challenge, Mass Participation Charity, Audax) → **~25–30 %**. Der Rest: Local-Group-Vereinsausfahrten, AGMs, Rallyes.
- **Schätzung Breitensport-Rad (Cycling UK):** grob **~100–130** Events für den Rest 2026, über eine volle Saison eher **~150–250**.
- Davon ein nennenswerter Teil **Audax** → Überschneidung mit Audax UK (Dedup).
- **UK Cycling Events:** ~6 Flaggschiff-Sportives (Überschneidung mit Let's Do This).
- ⇒ Realistische, de-duplizierte Breitensport-Rad-Basis aus diesen Quellen: Größenordnung **~150–250/Jahr** – vergleichbar mit einer der deutschen Quellen, also lohnend.

> Methodik-Hinweis: Schätzung aus Seiten-Sampling (Verhältnis von Seite 0). Die **exakte** Zahl + Dedup liefert erst der Scraper-Lauf in der CI. Offen für Phase 1: Audax-API-Endpoint identifizieren; Postcode-Trefferquote über `postcodes.io` messen.

### Quellen-Backlog Radsport (Nutzerliste 22.06.2026, triagiert)

Grundsatz: Cycling UK deckt schon viel ab (inkl. Audax). Zusatzquellen lohnen nur, wenn sie **unique** Events liefern; Aggregatoren/Magazine bringen v. a. Overlap.

| Quelle | Verdikt |
|--------|---------|
| Sportive.com | 🆕 **Phase-0-Kandidat** – fokussierter Sportive-Kalender, ggf. unique kommerzielle Sportives |
| GranFondo.com | 🆕 **Phase-0-Kandidat** – Gran-Fondo/Sportive-Kalender |
| Gran Fondo Daily News | 🆕 Nische UK-Gran-Fondo, klein/optional |
| British Masters (BMCR) | 🆕 Masters-**Rennen**, nicht Jedermann → außerhalb Fokus, optional später |
| Time Outdoors | Aggregator → vertagt (wie Find A Race) |
| Find A Race, Let's Do This | Aggregator/Buchung & Wettbewerber → meiden (ToS) |
| Cycling Weekly, road.cc, Cyclist, Rouleur, Cycling Plus, Cycle | Medien/Magazine – keine strukturierten Kalender; nur für Highlights |
| British Cycling | 🔴 robots (ClaudeBot) + Elite-lastig → raus |

### Phase-0-Befund Sportive.com (22.06.2026) – starke Empfehlung

- **robots.txt:** erlaubt (nur Cart/Admin gesperrt). **Server-gerendert** (WordPress „The Events Calendar").
- **Koordinaten direkt eingebettet** (jeder Eintrag hat „Get Directions" mit `?query=lat,lon`) → **kein Geocoding nötig**.
- **iCal-/ICS-Feed** vorhanden (`https://sportive.com/events/?ical=1`) → sauberster Ingest-Weg (strukturierte VEVENTs: Titel, Datum, Ort, Geo, URL) statt HTML-Parsing.
- **~80 Events** im aktuellen Fenster, Schwerpunkt **kommerzielle Sportives** (RIDE/Action, Pulse, Iconic, Let's Go Velo, Sportiva, Channel, Parkinson's Pedal-Serie …) – **unique gegenüber Cycling UK** (das club-/Audax-/charity-lastig ist).
- **Subsumiert UK Cycling Events** (UKCE-Sportives sind hier mitgelistet) → separater UKCE-Scraper wird überflüssig.
- Enthält auch EU-Events (Marmotte, Etape, Mallorca 312) und vereinzelt Gravel/CX/Tri → bei Bedarf auf `country=GB` / Radsport filtern.

**Empfehlung:** Quellen-Set für den Radsport-Piloten = **Cycling UK** (Clubs/Audax/Charity) **+ Sportive.com** (kommerzielle Sportives, inkl. UKCE). Sportive.com idealerweise über den **iCal-Feed** anbinden. GranFondo.com vorerst zurückgestellt (robots permissiv, aber wahrscheinlich redundant zu Sportive.com).

---

## Anhang B: UX-Walkthrough aus Sicht eines UK-Nutzers (Stand 22.06.2026)

Durchgespielt am aktuellen `index.html`. Szenario: eine Person in UK mit englischem Browser öffnet bockwurst.cc und sucht Sportives im Umkreis ihres Postcodes. Schweregrad: 🔴 Blocker · 🟡 Anpassung · 🟢 passt.

### Schritt für Schritt

1. **Ankunft & Sprache** — 🔴 `let lang="de"` (index.html Z. 831), **keine** `navigator.language`-Erkennung. Der UK-Nutzer landet auf **Deutsch**. Der von dir gewünschte „Browsersprache → EN"-Flow ist noch **nicht gebaut**. Fix: beim Laden `navigator.language` auswerten (`de*` → Deutsch, sonst Englisch), `document.documentElement.lang` setzen, manuellen Umschalter als Override behalten, Wahl in `localStorage` merken.

2. **Land/Kontext** — 🔴 Es gibt **keinen Länderfilter**; alle Daten sind DE. Der UK-Nutzer sähe deutsche Events. Fix: `country`-Filter (DE/UK) einführen; bei englischer Browsersprache initial **UK** vorbelegen (frei umschaltbar). Erst damit funktioniert der Flow „EN-Browser → UK-Ansicht".

3. **Hero/SEO-Texte** — 🟡 Der EN-Hero sagt „700+ … events **across Germany**" (Z. 690), die Meta-Description „in ganz Deutschland" (Z. 6, 20). Für UK falsch. Fix: länderabhängige bzw. neutrale Texte („across the UK" / „near you"); SEO-Meta je Sprache/Land (hreflang ist bereits angelegt).

4. **Sportfilter** — 🟢 rad/tri/swim/lauf identisch, EN-Labels vorhanden.

5. **Zeitraum-Filter** — 🟢 Alle Termine / Wochenende / Monat / 30 Tage / eigener Zeitraum: sprachneutrale Logik, EN-Labels da, Datums-Picker ok.

6. **Postcode-Eingabe** — 🔴 **Blocker.** Feld `#plz` hat `maxlength="5"` und die Validierung akzeptiert nur fünfstellige Ziffern (`/^\d{5}$/`); das Geocoding ruft Nominatim fest mit `country=DE` (Z. 970). **UK-Postcodes** sind alphanumerisch, 5–8 Zeichen mit Leerzeichen (z. B. `GU8 6DG`) → werden abgelehnt. Fix: Eingabe/Validierung länderabhängig (UK-Postcode-Regex, Uppercase/Leerzeichen normalisieren), Geocoding über **postcodes.io** für UK, Label/Placeholder je Land („e.g. SW1A 1AA").

7. **Umkreis / Distanzlogik** — 🟡 Radius-Optionen fest in **km** (50/100/150/250, Z. 750), der Distanz-Chip zeigt fest „~X **km**" (Z. 899). UK-Nutzer denken in **Meilen**. Fix: Einheit an das Land koppeln (UK = miles). Intern bleibt Haversine in km; nur **Anzeige** umrechnen. Radius-Optionen in mi (z. B. 25/50/100/150 mi), Chip „~X mi", sinnvoller UK-Default (z. B. 50 mi). Das ist eine echte Logik-/Formatierungsänderung, nicht nur ein Label-Tausch.

8. **Event-Distanzen (`strecken`)** — 🟡 Werte kommen aus den Daten; UK-Quellen liefern teils mi und km (Cycling UK zeigt beides). Konsistente Anzeige je Land festlegen (UK: miles).

9. **Ergebnis-Karten** — 🟢 / 🟡 Datumsblock (Tag/Monat/Wochentag) über EN-Arrays ok. Das Badge „DE · `lv`" muss für UK „GB · Region" zeigen (kommt aus `country`/`lv`); sicherstellen, dass `country` korrekt gerendert wird.

10. **Kalenderansicht** — 🟡 (kosmetisch) Monats-/Wochentagsnamen EN ok; das Karten-Datum ist numerisch „DD.MM.YYYY" — UK-Konvention ist eher „7 Jun 2026" bzw. „DD/MM/YYYY".

11. **„Event vorschlagen"-Modal** — 🟡 Felder via `data-de/en`, aber Platzhalter „09111" / „Chemnitz" und PLZ `maxlength="5"` (Z. 1026) sind deutsch. Für UK lokalisieren (Postcode-Format, Beispielort).

12. **Promo-Zone** — 🟡 (inhaltlich) Das 6Points-Mallorca-Event ist englischsprachig und passt; die YouTube-Kachel ist Stefans **deutschsprachiger** Kanal/Titel → für UK-Nutzer wenig relevant. Entscheiden: länderabhängige Promo oder neutral lassen.

13. **Recht/Footer** — 🟡 Impressum (§ 5 TMG) und Datenschutz sind deutsch-rechtlich formuliert. Da derselbe Auftritt (kein eigener `.co.uk`), genügt eine englische Fassung; die Impressums-/DSGVO-Pflicht aus Betreibersicht bleibt ohnehin bestehen.

### Antwort auf die Kernfrage

„EN-Browser → landet auf UK-Filter in EN" funktioniert **nur**, wenn zwei heute fehlende Bausteine gebaut werden: (a) `navigator.language`-Erkennung und (b) ein Länderfilter, der bei EN initial auf UK steht. Beides gehört in Phase 1. Danach ist die Kette: englischer Browser → Oberfläche EN → Länderfilter UK → Einheit miles → UK-taugliche Postcode-Eingabe.

### Notwendige Frontend-Änderungen (priorisiert)

| Prio | Änderung | Stelle |
|------|----------|--------|
| 🔴 P0 | Länderfilter (`country` DE/UK) einführen | render/filtered, neues UI-Element |
| 🔴 P0 | Postcode-Eingabe + -Validierung + Geocoding länderabhängig (postcodes.io) | `#plz`, `geocodePlz` (Z. 748, 960–975) |
| 🔴 P0 | Sprache automatisch über `navigator.language` | Init (Z. 831 ff.) |
| 🟡 P1 | Einheiten miles/km je Land (Radius-Optionen, Distanz-Chip, strecken) | Z. 750, 899, renderList |
| 🟡 P1 | Texte/SEO länderabhängig (Hero „across Germany", Meta) | Z. 6, 20, 690 |
| 🟡 P2 | Vorschlags-Modal + Promo + Footer/Recht lokalisieren | Z. 1026, Promo-Zone, Footer |
| 🟢 P3 | Kalender-Datumsformat an Locale anpassen | renderCal |

> Gut zu wissen: Das Datenschema trägt `country` bereits, und die Übersetzungs-Mechanik (`data-de`/`data-en`) steht. Die P0-Punkte sind überschaubare, klar lokalisierte Eingriffe – kein Architektur-Umbau.
