"""
de_radsport_events.py – Scraper for radsport-events.de (Rennrad/Gravel, DE).

Die Seite wurde 2026 auf eine client-gerenderte React-SPA umgebaut: die alte
`…/kalender.php` leitet per 301 auf `/rennrad-events` um, und die Eventliste
entsteht erst im Browser (kein Server-HTML). Das Frontend bezieht seine Daten
aber von einer sauberen, öffentlichen REST-API:

    GET https://api.radsport-events.de/api/v1/events
        ?page=0&size=200&country=DE&date=YYYY-01-01&dateTo=YYYY-12-31

Antwort (paginiert): {"content": [ …Events… ], "totalPages": N, …}. Jedes
Event liefert fertige Koordinaten (latitude/longitude), postalCode, city,
bundesland, category (ROAD/GRAVEL/MTB), eventType, distances[] u. v. m. – es ist
also KEIN Geocoding und KEINE Standort-Heuristik nötig, und der Scraper braucht
nur `requests` (kein Playwright/Chromium → keine Workflow-Änderung).

Scope: Deutschland (API-Filter country=DE), Kategorien ROAD+GRAVEL, nur
zukünftige Termine des Zieljahres. Nicht-Radsport (Triathlon/Duathlon) und
virtuelle Events werden übersprungen.
"""
from __future__ import annotations  # Python 3.9 compat

import time
from datetime import date, datetime

import requests

API_URL = "https://api.radsport-events.de/api/v1/events"
DETAIL_URL = "https://radsport-events.de/events/{id}"  # kanonische Event-URL
HEADERS = {
    "User-Agent": "bockwurst-events/2.0 (+github.com/stefangriessmann/sport-events)",
    "Accept": "application/json",
}
PAGE_SIZE = 200
MAX_PAGES = 50  # Sicherheitsobergrenze

# Welche Rad-Kategorien in den Guide einfließen. MTB ist bewusst aus (die Site
# ist Rennrad/Gravel-fokussiert); zum Aktivieren einfach "MTB" ergänzen – das
# ART_MAP unten deckt die MTB-Eventtypen bereits ab.
CATEGORIES = {"ROAD", "GRAVEL"}

# Nicht-Radsport bzw. virtuelle Eventtypen überspringen (Triathlon/Duathlon
# gehören in triathlon-de.json; virtuelle RTFs haben keinen echten Ort).
SKIP_EVENT_TYPES = {"TRIATHLON", "DUATHLON", "DUATHLON_CROSS", "VIRTUELLE_RTF"}

# eventType (API-Enum) → Anzeige-„art". Die Labels erscheinen 1:1 im Typ-Filter
# der Site; index.html ordnet jede hier gelieferte art automatisch dem Sport
# „rad" zu (TYPE_SPORT[art]=sp beim Laden). Wichtig: KEIN Label „Ultra" o. Ä.,
# das mit den fest verdrahteten TYPE_SPORT-Keys (Ultra→lauf, Triathlon→tri …)
# kollidieren würde – daher „Ultracycling".
ART_MAP = {
    # ROAD
    "RTF": "RTF",
    "BREVET": "Brevet",
    "RADMARATHON": "Marathon",
    "JEDERMANN": "Jedermannrennen",
    "HOBBYRENNEN": "Jedermannrennen",
    "VOLKSRADFAHREN": "Volksradfahren",
    "EINZELZEITFAHREN": "Zeitfahren",
    "ULTRA": "Ultracycling",
    "ETAPPENRENNEN": "Etappenrennen",
    "RENNEN_24H": "24h-Rennen",
    "RENNEN_12H": "12h-Rennen",
    "RENNEN_2_3_6H": "Zeitrennen",
    # GRAVEL
    "GRAVEL_RIDE": "Gravelride",      # Label an de_radnet angeglichen (ein Chip)
    "GRAVEL_TOUR": "Gravelride",
    "GRAVEL_RACE": "Gravel Race",
    "GRAVEL_CAMP": "Gravel Camp",
    "GRAVEL_SONSTIGES": "Gravelride",
    "BIKEPACKING": "Bikepacking",
    # MTB (nur relevant, falls "MTB" zu CATEGORIES hinzugefügt wird)
    "CTF": "CTF",
    "MTB_MARATHON": "MTB-Marathon",
    "CROSSCOUNTRY": "Cross-Country",
    "CYCLOCROSS": "Cyclocross",
    "DOWNHILL": "Downhill",
    "ENDURO": "Enduro",
    "HILLCLIMB": "Bergzeitfahren",
    "SONSTIGE_MTB": "MTB",
}

# 16 Bundesländer → Kurzcode (für die Anzeige „DE · <Code>", wie bei de_radnet).
BUNDESLAND_LV = {
    "Baden-Württemberg": "BW", "Bayern": "BAY", "Berlin": "BER",
    "Brandenburg": "BRA", "Bremen": "BRE", "Hamburg": "HAM", "Hessen": "HES",
    "Mecklenburg-Vorpommern": "MEV", "Niedersachsen": "NDS",
    "Nordrhein-Westfalen": "NRW", "Rheinland-Pfalz": "RLP", "Saarland": "SAA",
    "Sachsen": "SAC", "Sachsen-Anhalt": "SA", "Schleswig-Holstein": "SCH",
    "Thüringen": "THÜ",
}

WDAY_ABBR = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}
WDAY_FULL = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch", "Do": "Donnerstag",
    "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}


def _fmt_datum(date_iso: str):
    """'2026-10-10' → ('Sa, 10.10.2026', 'Sa', 'Samstag') oder None."""
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    wd = WDAY_ABBR[dt.weekday()]
    return f"{wd}, {dt.strftime('%d.%m.%Y')}", wd, WDAY_FULL[wd]


def _strecken(distances: list) -> str:
    """distances[] → '55/80/105' (aufsteigend, dedupliziert)."""
    kms = []
    for d in distances or []:
        km = d.get("distanceKm")
        if km is None:
            continue
        kms.append(int(km) if float(km).is_integer() else round(float(km), 1))
    uniq = sorted(dict.fromkeys(kms))
    return "/".join(str(k) for k in uniq)


def _fetch_page(session: requests.Session, params: dict):
    """Eine API-Seite holen; None bei (auch nach einem Retry) anhaltendem Fehler."""
    for attempt in range(2):
        try:
            r = session.get(API_URL, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  [rse] API-Fehler (Versuch {attempt + 1}/2) page={params.get('page')}: {e}")
            if attempt == 0:
                time.sleep(2)
    return None


def fetch(year: int) -> list[dict]:
    """
    Rad-Events (DE, ROAD+GRAVEL) des Zieljahres von radsport-events.de.

    Holt alle Seiten der REST-API im Datumsfenster [year-01-01, year-12-31],
    filtert auf Zukunft + Zieljahr + gewünschte Kategorien und liefert das
    gemeinsame Ausgabeschema der de_*-Scraper.
    """
    today = date.today().isoformat()
    base_params = {
        "country": "DE",
        "date": f"{year}-01-01",
        "dateTo": f"{year}-12-31",
        "size": PAGE_SIZE,
    }

    print(f"[radsport-events.de] Fetching {year} events via REST API (ROAD+GRAVEL)...")

    session = requests.Session()
    events: list[dict] = []
    seen_ids: set = set()
    skipped_year = skipped_cat = skipped_type = skipped_cancelled = skipped_nodate = 0

    total_pages = None
    page = 0
    while page < MAX_PAGES:
        data = _fetch_page(session, {**base_params, "page": page})
        if data is None:
            print(f"  Seite {page} dauerhaft fehlerhaft – breche Paginierung ab")
            break

        content = data.get("content", []) or []
        if total_pages is None:
            total_pages = data.get("totalPages", 1)
            print(f"  {data.get('totalElements', '?')} DE-Treffer {year}, {total_pages} Seite(n)")

        for ev in content:
            ev_id = ev.get("id")
            if ev_id in seen_ids:
                continue

            date_iso = ev.get("eventDate") or ""
            fmt = _fmt_datum(date_iso)
            if not fmt:
                skipped_nodate += 1
                continue
            datum, _wd, wochentag = fmt

            # Nur Zukunft + Zieljahr (dateTo begrenzt bereits, heute zusätzlich).
            if not date_iso.startswith(str(year)) or date_iso < today:
                skipped_year += 1
                continue

            if ev.get("category") not in CATEGORIES:
                skipped_cat += 1
                continue

            event_type = ev.get("eventType") or ""
            if event_type in SKIP_EVENT_TYPES:
                skipped_type += 1
                continue

            # Abgesagte Events ausblenden (die Site kennzeichnet sie, unser
            # schlankes Guide-Schema nicht – also lieber nicht anzeigen).
            if ev.get("cancelled"):
                skipped_cancelled += 1
                continue

            lat, lon = ev.get("latitude"), ev.get("longitude")
            ort = (ev.get("city") or ev.get("locationName") or "").strip()
            # Ortsbasierter Guide: ohne Koordinaten/Ort kippt der zentrale
            # Qualitätsfilter in update_data.py das Event ohnehin.
            if lat is None or lon is None or not ort:
                continue

            seen_ids.add(ev_id)

            # Mehrtägig: endDate (falls abweichend) als Ende übernehmen.
            end_iso = ev.get("endDate")
            if end_iso and end_iso != date_iso and _fmt_datum(end_iso):
                date_iso_end = end_iso
                datum_end = datetime.strptime(end_iso, "%Y-%m-%d").strftime("%d.%m.%Y")
            else:
                date_iso_end = None
                datum_end = None

            events.append({
                "art":          ART_MAP.get(event_type, "Sonstige"),
                "datum":        datum,
                "datum_end":    datum_end,
                "wochentag":    wochentag,
                "date_iso":     date_iso,
                "date_iso_end": date_iso_end,
                "km":           None,
                "lat":          lat,
                "lon":          lon,
                "titel":        (ev.get("title") or "").strip(),
                "ort":          ort,
                "plz":          (ev.get("postalCode") or "").strip(),
                "strecken":     _strecken(ev.get("distances")),
                "verein":       (ev.get("organizer") or "").strip(),
                "lv":           BUNDESLAND_LV.get(ev.get("bundesland") or "", ""),
                "country":      "DE",
                "url":          DETAIL_URL.format(id=ev_id),
                "serie":        "",
            })

        page += 1
        if total_pages is not None and page >= total_pages:
            break
        time.sleep(0.3)  # höflich zur API

    print(
        f"  {len(events)} DE-Events {year} übernommen (übersprungen: "
        f"{skipped_year} Jahr/Vergangenheit, {skipped_cat} andere Kategorie, "
        f"{skipped_type} Nicht-Radsport/virtuell, {skipped_cancelled} abgesagt, "
        f"{skipped_nodate} ohne Datum)"
    )
    return sorted(events, key=lambda e: e["date_iso"])


if __name__ == "__main__":  # manueller Test: python de_radsport_events.py [year]
    import sys
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year
    evs = fetch(yr)
    for e in evs[:8]:
        rng = f"–{e['date_iso_end']}" if e["date_iso_end"] else ""
        print(f"{e['date_iso']}{rng} {e['lv']:>3} {e['ort']} – {e['titel']} "
              f"[{e['art']}] ({e['strecken']})")
    print(f"total: {len(evs)}")
