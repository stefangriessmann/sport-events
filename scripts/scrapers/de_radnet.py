"""
de_radnet.py – Scraper for breitensport.rad-net.de (BDR Breitensportkalender).

The listing page is server-rendered and already includes the straight-line distance
from the queried PLZ, so no geocoding is needed for the km value.
We also run Nominatim geocoding to store lat/lon for dynamic distance recalculation.
"""
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from geocoder import geocode_event

BASE = "https://breitensport.rad-net.de/breitensportkalender/"
HEADERS = {"User-Agent": "sport-events-chemnitz/2.0 (github actions)"}

# rad-net LV codes → our display codes
LV_MAP = {
    "SAC": "SAC", "SAH": "SA",  "THÜ": "THÜ", "BAY": "BAY",
    "NDS": "NDS", "HES": "HES", "NRW": "NRW", "BRA": "BRA",
    "MEV": "MEV", "SCH": "SCH", "RLP": "RLP", "BER": "BER",
    "BAD": "BAD", "WÜR": "WÜR", "SAA": "SAA", "HAM": "HAM",
    "BRE": "BRE",
}

# art values to skip (non-events or permanent routes)
SKIP_ARTS = {
    "CTF-Permanente", "RTF-Permanente", "RTF nach GPS", "vRTF",
    "Deutsches Radsportabzeichen", "Richtig fit Tag Radfahren",
    "Etappenfahrt", "Radwandern", "Permanent Gravelride",
}

WDAY = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}


def _parse_entry(li) -> dict | None:
    """Parse a single <li> result entry."""
    a = li.find("a")
    if not a:
        return None
    url = "https://breitensport.rad-net.de" + a["href"] if a["href"].startswith("/") else a["href"]
    text = a.get_text(" ", strip=True)

    # Extract LV  "(SAC)" at end
    lv_m = re.search(r"\(([A-Z]{2,4})\)\s*$", text)
    if not lv_m:
        return None
    lv_raw = lv_m.group(1)
    text = text[: lv_m.start()].strip()

    # Extract distance  "(~65 km)"
    km_m = re.search(r"\(~(\d+)\s*km\)", text)
    if not km_m:
        return None
    km = int(km_m.group(1))

    # Part before distance = optional art + date
    before = text[: km_m.start()].strip()
    date_m = re.search(r"([A-Za-z]{2},\s*\d{2}\.\d{2}\.\d{4})", before)
    if not date_m:
        return None
    datum_raw = date_m.group(1)
    # Normalise spaces: "Sa, 13.06.2026"
    datum = re.sub(r"\s+", " ", datum_raw).strip()
    art_raw = before[: date_m.start()].strip()

    # Part after distance = title + strecken + verein
    after = text[km_m.end():].strip()

    # Strecken: a sequence like "57/102/155" or "47/73/109/148"
    strecken_m = re.search(r"\s+([\d,./]+(?:/[\d,./]+)+)\s+", after)
    if strecken_m:
        titel = after[: strecken_m.start()].strip().rstrip(".")
        strecken = strecken_m.group(1)
        verein = after[strecken_m.end():].strip()
    else:
        # No strecken field in listing (some marathon entries)
        strecken_m2 = re.search(r"\s+(\d{2,4})\s+", after)
        if strecken_m2:
            titel = after[: strecken_m2.start()].strip().rstrip(".")
            strecken = strecken_m2.group(1)
            verein = after[strecken_m2.end():].strip()
        else:
            titel = after
            strecken = ""
            verein = ""

    # Clean title truncation
    titel = re.sub(r"\.{2,}$", "", titel).strip()

    # Normalise art
    art = art_raw if art_raw else "Gravelride"
    art_aliases = {
        "Radtourenfahrt": "RTF",
        "Radmarathon": "Marathon",
    }
    art = art_aliases.get(art, art)
    if art in SKIP_ARTS:
        return None

    try:
        date_iso = datetime.strptime(datum.split(", ")[1], "%d.%m.%Y").strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return None

    return {
        "art": art,
        "datum": datum,
        "wochentag": WDAY.get(datum[:2], ""),
        "date_iso": date_iso,
        "km": km,
        "lat": None,
        "lon": None,
        "titel": titel,
        "strecken": strecken,
        "verein": verein,
        "lv": LV_MAP.get(lv_raw, lv_raw),
        "country": "DE",
        "url": url,
        "serie": "",
    }


def fetch(year: int, max_km: int = 400) -> list[dict]:
    """
    Fetch all cycling events within max_km of PLZ 09111 (Chemnitz) for the given year.
    Returns list of event dicts, sorted by date_iso.
    """
    today = date.today().isoformat()
    events: list[dict] = []
    lstart = 0
    total = None

    print(f"[radnet] Fetching {year} events within {max_km} km of 09111...")

    while True:
        url = (
            f"{BASE}?plz=09111&umkreis={max_km}"
            f"&startdate=01.01.{year}&enddate=31.12.{year}"
            f"&lstart={lstart}"
        )
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error fetching page (lstart={lstart}): {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")

        # Detect total on first page
        if total is None:
            m = re.search(r"(\d+)\s+Treffer", soup.get_text())
            total = int(m.group(1)) if m else 0
            print(f"  Total results: {total}")

        # Result list items (skip header li)
        items = soup.select("ul li")
        new_items = 0
        for li in items:
            ev = _parse_entry(li)
            if ev and ev["date_iso"] >= today and ev["km"] <= max_km:
                events.append(ev)
                new_items += 1

        lstart += 30
        if lstart >= (total or 0):
            break
        time.sleep(0.5)

    # Deduplicate by URL, keep first occurrence
    seen: set[str] = set()
    unique: list[dict] = []
    for e in events:
        if e["url"] not in seen:
            seen.add(e["url"])
            unique.append(e)

    print(f"  {len(unique)} unique future events collected")

    # Geocode for lat/lon (city extracted from title)
    print("  Geocoding event locations...")
    for ev in unique:
        geo = geocode_event(ev["titel"], country="DE")
        if geo:
            ev["lat"], ev["lon"] = round(geo[0], 4), round(geo[1], 4)

    return sorted(unique, key=lambda e: e["date_iso"])
