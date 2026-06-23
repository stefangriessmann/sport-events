# Design-Brief: Startseite (für Claude Design)

> Zum Einfügen in Claude Design. Ergebnis: ein responsiver Startseiten-Entwurf (HTML/CSS), den Claude Code in TYPO3 umsetzt.

## Kontext
Startseite von **bockwurst.cc** („Stefans Rennrad Welt"). Sie ist **Wegweiser + Bühne**: Touren stehen im Vordergrund (Marke), der Event-Guide bringt den schnellen Nutzwert, das 6-Points-Engagement ist immer präsent. Hauptzielgruppe: Breitensportler/Rennradfahrer.

## Marke / Stil (Konsistenz mit Event-Guide & Tour-Detailseite)
- Hell, klar, **werbefrei**, viel Weißraum, große Typo.
- Farben: Cobalt `#2B5BFF`, Pink `#FF2E86`, Grün `#13C766`, Cyan `#1FB6C9`, Gelb `#FBC400`, Tinte `#0C0E14`, Hintergrund weiß.
- Schriften: „Bricolage Grotesque" (Headlines), „Familjen Grotesk" (Text).
- Ton: sportlich, persönlich, authentisch.

## Seitenaufbau (von oben nach unten)
1. **Header/Navigation:** Logo „bockwurst.cc", Menü: Events · Touren · Über mich · Zwift · 6 Points · Sprache DE/EN.
2. **Hero:** Marke + aktuelles Highlight (neueste Tour oder neuestes Video) groß in Szene gesetzt, ein starker Satz/Claim, ein Haupt-Button (z. B. „Touren entdecken").
3. **Touren-Highlights (Schwerpunkt):** Raster mit 3–6 kuratierten Top-Touren (Bild, Titel, Region, Distanz/hm, Typ-Badge), Button „Alle Touren".
4. **6 Points Charity – Banner:** prominenter, durchgehend sichtbarer Block zu Stefans Markenbotschafter-Rolle (Mallorca-Charity), klarer CTA „Mehr erfahren / Mitmachen".
5. **Event-Teaser:** „Die 5 aktuellsten Events in deiner Nähe" – kompakte, interaktive Liste (Datum, Sportart, Ort), Button „Zum Event-Guide" (führt zu events.bockwurst.cc).
6. **YouTube Shorts:** horizontale Leiste mit 3–5 aktuellen Shorts (Vorschaubilder, datenschutzfreundlich erst auf Klick).
7. **Über Bockwurst – Anriss:** Foto + 1–2 Sätze (20 Jahre Rennrad, Rennrad Chemnitz, Zwift/Team Valhalla) + Button „Über mich".
8. *(später)* **Tipps & Erfahrungen:** Teaser für Blog-Artikel (Equipment, Erfahrungen). Platz vorsehen, vorerst optional.
9. **Footer:** Kontakt, Impressum, Datenschutz, Social-Links (YouTube, Strava, Instagram), Hinweis „werbefrei, kein Tracking".

## Prioritäten
- **Touren** = optisch der Schwerpunkt. **6 Points** = immer präsent/auffällig. **Event-Teaser** = klar nutzbar, aber kompakt.

## Technische Hinweise (Kontext für die Umsetzung)
- Sauberes, eigenständiges HTML/CSS, nur die genannten Schriften als externe Abhängigkeit. Mobile-first.
