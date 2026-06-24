# Design-Brief: Tourenportal – Übersicht (für Claude Design)

> Zum Einfügen in Claude Design. Ergebnis: ein responsiver Übersichts-/Listenentwurf (HTML/CSS) für das Tourenportal.

## Kontext
Übersicht aller Touren von **bockwurst.cc**. Von hier gelangt man zu den einzelnen **Tour-Detailseiten**. Start mit einer **kuratierten Auswahl** (z. B. 10–15 Highlights), später wachsend auf 90+ Touren (aus den YouTube-Touren). Zweck: Stöbern, filtern, die passende Tour finden.

## Marke / Stil
- Identisch zu Startseite & Tour-Detailseite: hell, werbefrei, große Typo. Farben Cobalt `#2B5BFF`, Pink `#FF2E86`, Grün `#13C766`, Cyan `#1FB6C9`, Gelb `#FBC400`, Tinte `#0C0E14`, weiß. Schriften „Bricolage Grotesque" / „Familjen Grotesk".

## Seitenaufbau
1. **Kopf + Touren-Landkarte (Highlight):** Titel „Touren" + kurzer Einleitungssatz, darunter eine **interaktive Karte mit ALLEN Touren** – je Tour ein Marker am Startpunkt (Klick → Detailseite), optional die Routen als Linien. Zeigt auf einen Blick, „wo war ich überall". Quelle: Strava (Start/Strecke).
2. **Filter-/Sortierleiste:** Filter nach **Region**, **Distanz** (z. B. <100 / 100–200 / 200+ km), **Tour-Typ** (Rennrad/Gravel); Sortierung „neueste / längste".
3. **Touren-Raster:** Karten mit Bild, Titel, Region, **Eckdaten** (Distanz km, Höhenmeter hm), Typ-Badge, Schwierigkeit, 1-Zeilen-Teaser; Klick → Tour-Detailseite.
4. **Mehr laden / Pagination** (für später, wenn viele Touren).
5. **Vernetzung:** kleiner Block „Passende Events finden" (Absprung in den Event-Guide).
6. **Footer:** wie Startseite.

## Beispieldaten (zum Befüllen)
- „MSR300 – Mecklenburger Seenrunde" · Mecklenburg · 300 km · 1.450 hm · Rennrad · schwer
- „Erzgebirgs-Klassiker" · Erzgebirge · 120 km · 2.100 hm · Rennrad · mittel
- „Gravel rund um Chemnitz" · Sachsen · 75 km · 900 hm · Gravel · leicht

## Technische Hinweise
- Sauberes, eigenständiges HTML/CSS, nur die genannten Schriften extern. Mobile-first. Die Filter dürfen als statisches Layout entworfen sein (Funktion baue ich in TYPO3).
