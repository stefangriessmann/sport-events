# Design-Brief: Tour-Detailseite (für Claude Design)

> Zum Einfügen in Claude Design. Ergebnis: ein responsiver Seitenentwurf (HTML/CSS), den Claude Code anschließend in TYPO3 umsetzt.

## Kontext
Teil von **bockwurst.cc** („Stefans Rennrad Welt") – Tourenportal. Diese Seite stellt **eine einzelne Rennrad-/Gravel-Tour** vor. Sie soll Lust aufs Nachfahren machen und den Besucher mit dem restlichen Portal vernetzen (Events, weitere Touren, Profil).

## Marke / Stil (für Konsistenz mit dem Event-Guide)
- Helles, klares, **werbefreies** Design. Viel Weißraum, große Typo.
- Farben: Cobalt `#2B5BFF`, Pink `#FF2E86`, Grün `#13C766`, Cyan `#1FB6C9`, Gelb `#FBC400`, Tinte `#0C0E14`. Hintergrund weiß.
- Schriften: „Bricolage Grotesque" (Headlines), „Familjen Grotesk" (Text).
- Ton: sportlich, persönlich, authentisch.

## Seitenaufbau (von oben nach unten)
1. **Kopfbereich:** großes Titelbild oder Streckenkarte als Hintergrund; Titel der Tour; Untertitel mit Region/Startort; kleine Badges: Tour-Typ (Rennrad/Gravel), Schwierigkeit, Saison.
2. **Eckdaten-Leiste:** 4–5 Kacheln mit Icon – Distanz (km), Höhenmeter (hm), Dauer, Ø-Tempo, optional Watt. (Quelle: Strava)
3. **Strecke:** interaktive Karte mit eingezeichneter Route + darunter ein **Höhenprofil**.
4. **Video:** YouTube-Einbettung (zuerst Vorschaubild mit Play-Button, Klick startet – datenschutzfreundlich).
5. **Bericht:** Beschreibung der Tour (Fließtext, evtl. Zwischenüberschriften) und eine hervorgehobene **„Mein Fazit"-Box**.
6. **Bewertung:** Sterne/Skala für z. B. Landschaft, Anspruch, Straßenqualität (oder ein Gesamt-Rating mit kurzem Satz).
7. **Aktionen:** Buttons „GPX herunterladen", „Strecke nachfahren" (Komoot/Strava), „Teilen".
8. **Highlights (optional):** kurze Liste markanter Punkte entlang der Strecke (Pässe, Aussicht, Café-Stopp).
9. **Vernetzung (wichtig):** drei Blöcke – „Events in dieser Region" (führt zum Event-Guide), „Ähnliche Touren" (2–3 Kacheln), „Mehr über Bockwurst / Kanal abonnieren".

## Beispieldaten (zum Befüllen des Entwurfs)
- Titel: „Grenzerfahrung MSR300 – Mecklenburger Seenrunde, Nachtfahrt"
- Region: Mecklenburg · Tour-Typ: Rennrad · Schwierigkeit: schwer · Saison: Sommer
- Distanz: 300 km · Höhenmeter: 1.450 hm · Dauer: 12:48 h · Ø-Tempo: 23,4 km/h
- Fazit: „Eine Nacht, ein See nach dem anderen – mental wie körperlich an der Grenze, aber unvergesslich."

## Technische Hinweise (für die spätere Umsetzung – nur als Kontext)
- Bitte **sauberes, eigenständiges HTML/CSS**, ohne Abhängigkeiten außer den genannten Schriften und (für die Karte) Leaflet. Damit lässt es sich gut in TYPO3-Templates überführen.
- Mobile-first / responsiv.
