"""
de_radnet.py – Scraper for breitensport.rad-net.de (BDR Breitensportkalender).

Fetches ALL cycling events across Germany (no distance pre-filter).
The JS dashboard handles distance filtering dynamically via STATE_GEO + user PLZ.

No geocoding – events are identified by their LV (Bundesland) code.
The JS uses STATE_GEO[lv] as a fallback for distance calculation.
"""
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE = "https://breitensport.rad-net.de/breitensportkalender/"
HEADERS = {"User-Agent": "bockwurst-events/2.0 (github.com/stefangriessmann/sport-events)"}

# PLZ 34117 = Kassel (geographically central in Germany), umkreis=600 covers all DE
SEARCH_PLZ    = "34117"
SEARCH_UMKREIS = 600

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

    # Extract distance "(~65 km)" – present in listing but relative to search PLZ, not user PLZ
    # We discard this value; JS recalculates from lv/STATE_GEO
    km_m = re.search(r"\(~(\d+)\s*km\)", text)
    if not km_m:
        return None
    text_before_km = text[: km_m.start()].strip()
    text_after_km  = text[km_m.end():].strip()

    # Date in the "before" part – optionally a range "Fr, 12.06.2026 - Sa, 13.06.2026"
    date_m = re.search(
        r"([A-Za-z]{2},\s*\d{2}\.\d{2}\.\d{4})"
        r"(?:\s*[-–]\s*[A-Za-z]{2},\s*(\d{2}\.\d{2}\.\d{4}))?",
        text_before_km,
    )
    if not date_m:
        return None
    datum_raw = date_m.group(1)
    datum = re.sub(r"\s+", " ", datum_raw).strip()
    datum_end_raw = date_m.group(2)  # None for single-day events
    art_raw = text_before_km[: date_m.start()].strip()

    # Title + strecken + verein from after part
    after = text_after_km
    strecken_m = re.search(r"\s+([\d,./]+(?:/[\d,./]+)+)\s+", after)
    if strecken_m:
        titel   = after[: strecken_m.start()].strip().rstrip(".")
        strecken = strecken_m.group(1)
        verein   = after[strecken_m.end():].strip()
    else:
        strecken_m2 = re.search(r"\s+(\d{2,4})\s+", after)
        if strecken_m2:
            titel    = after[: strecken_m2.start()].strip().rstrip(".")
            strecken = strecken_m2.group(1)
            verein   = after[strecken_m2.end():].strip()
        else:
            titel    = after
            strecken = ""
            verein   = ""

    titel = re.sub(r"\.{2,}$", "", titel).strip()

    art = art_raw if art_raw else "Gravelride"
    art_aliases = {"Radtourenfahrt": "RTF", "Radmarathon": "Marathon"}
    art = art_aliases.get(art, art)
    if art in SKIP_ARTS:
        return None

    try:
        date_iso = datetime.strptime(datum.split(", ")[1], "%d.%m.%Y").strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return None

    date_iso_end = None
    if datum_end_raw:
        try:
            date_iso_end = datetime.strptime(datum_end_raw, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    return {
        "art":       art,
        "datum":     datum,
        "datum_end": datum_end_raw,
        "wochentag": WDAY.get(datum[:2], ""),
        "date_iso":  date_iso,
        "date_iso_end": date_iso_end,
        "km":        None,   # JS calculates from lv → STATE_GEO
        "lat":       None,
        "lon":       None,
        "titel":     titel,
        "strecken":  strecken,
        "verein":    verein,
        "lv":        LV_MAP.get(lv_raw, lv_raw),
        "country":   "DE",
        "url":       url,
        "serie":     "",
    }


def fetch(year: int) -> list[dict]:
    """
    Fetch all German cycling events for the given year from rad-net.de.
    No distance pre-filtering – the JS dashboard filters dynamically.
    """
    today  = date.today().isoformat()
    events: list[dict] = []
    lstart = 0
    total  = None

    print(f"[radnet] Fetching ALL {year} events (PLZ {SEARCH_PLZ}, umkreis={SEARCH_UMKREIS}km)...")

    while True:
        url = (
            f"{BASE}?plz={SEARCH_PLZ}&umkreis={SEARCH_UMKREIS}"
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

        if total is None:
            m = re.search(r"(\d+)\s+Treffer", soup.get_text())
            total = int(m.group(1)) if m else 0
            print(f"  Total results on rad-net: {total}")

        items = soup.select("ul li")
        new_items = 0
        for li in items:
            ev = _parse_entry(li)
            if ev and ev["date_iso"] >= today:
                events.append(ev)
                new_items += 1

        print(f"  lstart={lstart}: +{new_items} events")
        lstart += 30
        if lstart >= (total or 0):
            break
        time.sleep(0.5)

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for e in events:
        if e["url"] not in seen:
            seen.add(e["url"])
            unique.append(e)

    print(f"  {len(unique)} unique future events collected (all Germany)")
    return sorted(unique, key=lambda e: e["date_iso"])
