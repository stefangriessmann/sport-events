"""
de_laufen.py – Scraper for laufen.run/kalender (regional running calendar).

Covers: Sachsen-Anhalt, Harz, Niedersachsen, Hessen, Thüringen.
Server-rendered Joomla page; pagination via ?start=N (15 items/page).
"""
import re
import math
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from geocoder import geocode_event

BASE = "https://laufen.run/kalender"
CHEMNITZ = (50.8333, 12.9167)
MAX_KM = 200
HEADERS = {"User-Agent": "sport-events-chemnitz/2.0 (github actions)"}

WDAY_DE = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}

# Abbreviated month names in German
MONTHS = {
    "Jan": "01", "Feb": "02", "Mär": "03", "Mrz": "03",
    "Apr": "04", "Mai": "05", "Jun": "06",
    "Jul": "07", "Aug": "08", "Sep": "09",
    "Okt": "10", "Nov": "11", "Dez": "12",
}

# Recognisable running event art keywords
ART_MAP = [
    ("trail",   "Trail"),
    ("berg",    "Trail"),
    ("forst",   "Trail"),
    ("ultra",   "Ultra"),
    ("backyard","Ultra"),
    ("marathon","Laufen"),
    ("lauf",    "Laufen"),
    ("run",     "Laufen"),
    ("walk",    "Laufen"),
]


def _detect_art(titel: str) -> str:
    t = titel.lower()
    for keyword, art in ART_MAP:
        if keyword in t:
            return art
    return "Laufen"


def _haversine(lat1, lon1, lat2, lon2) -> int:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return int(R * 2 * math.asin(math.sqrt(a)))


def _parse_date(raw: str) -> tuple[str, str, str] | None:
    """
    Parse German date strings like:
    "Sa 07.06.2026", "Samstag, 7. Juni 2026", "07.06.2026"
    Returns (datum_short, date_iso, wochentag_full) or None.
    """
    raw = raw.strip()

    # "Sa, 07.06.2026" or "Sa 07.06.2026"
    m = re.match(r"([A-Za-z]{2}),?\s*(\d{1,2})\.(\d{2})\.(\d{4})", raw)
    if m:
        wd, d, mo, y = m.groups()
        datum = f"{wd}, {int(d):02d}.{mo}.{y}"
        return datum, f"{y}-{mo}-{int(d):02d}", WDAY_DE.get(wd, "")

    # "07.06.2026"
    m = re.match(r"(\d{1,2})\.(\d{2})\.(\d{4})", raw)
    if m:
        d, mo, y = m.groups()
        iso = f"{y}-{mo}-{int(d):02d}"
        return f"??, {int(d):02d}.{mo}.{y}", iso, ""

    return None


def _parse_item(item) -> dict | None:
    """Parse a calendar list item from laufen.run."""
    # Title
    title_el = item.find(["h3", "h4", "strong", "a"])
    titel = title_el.get_text(strip=True) if title_el else item.get_text(" ", strip=True)[:80]
    if not titel:
        return None

    # URL
    a = item.find("a", href=True)
    url = a["href"] if a else ""
    if url and not url.startswith("http"):
        url = "https://laufen.run" + url

    # Date – search all text for recognisable date patterns
    text = item.get_text(" ", strip=True)
    date_m = re.search(r"([A-Za-z]{2}),?\s*(\d{1,2})\.(\d{2})\.(\d{4})", text)
    if not date_m:
        return None
    wd, d, mo, y = date_m.groups()
    datum = f"{wd}, {int(d):02d}.{mo}.{y}"
    date_iso = f"{y}-{mo}-{int(d):02d}"

    # Distances (e.g. "5/10/21,1/42,2")
    strecken_m = re.findall(r"\b(\d{1,3}(?:[,.]\d{1,2})?)\s*km\b", text, re.IGNORECASE)
    strecken = "/".join(strecken_m) if strecken_m else ""

    art = _detect_art(titel)

    return {
        "art": art,
        "datum": datum,
        "wochentag": WDAY_DE.get(wd, ""),
        "date_iso": date_iso,
        "km": None,
        "lat": None,
        "lon": None,
        "titel": titel,
        "strecken": strecken,
        "verein": "",
        "lv": "",
        "country": "DE",
        "url": url,
        "serie": "",
    }


def fetch(year: int, max_km: int = MAX_KM) -> list[dict]:
    """
    Fetch running events from laufen.run/kalender.
    Returns events near Chemnitz (within max_km), sorted by date.
    """
    today = date.today().isoformat()
    events: list[dict] = []
    seen_urls: set[str] = set()

    print(f"[laufen.run] Fetching {year} events...")

    start = 0
    while True:
        url = BASE if start == 0 else f"{BASE}?start={start}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error at start={start}: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")

        # Items: try various selectors used by Joomla event calendars
        items = (
            soup.select(".event-item")
            or soup.select("article")
            or soup.select(".list-item")
            or soup.select("li.item")
        )

        if not items:
            print(f"  No items found at start={start}, stopping.")
            break

        new = 0
        for item in items:
            ev = _parse_item(item)
            if not ev:
                continue
            if ev["date_iso"] < today:
                continue
            if not ev["date_iso"].startswith(str(year)):
                continue
            if ev["url"] and ev["url"] in seen_urls:
                continue
            if ev["url"]:
                seen_urls.add(ev["url"])
            events.append(ev)
            new += 1

        print(f"  start={start}: {new} new events (total so far: {len(events)})")
        if new == 0:
            break
        start += 15
        time.sleep(0.5)

    print(f"  {len(events)} candidate events total")

    # Geocode + filter by distance
    print("  Geocoding and filtering by distance...")
    result: list[dict] = []
    for ev in events:
        geo = geocode_event(ev["titel"], country="DE")
        if geo:
            ev["lat"], ev["lon"] = round(geo[0], 4), round(geo[1], 4)
            ev["km"] = _haversine(*CHEMNITZ, *geo)
        else:
            ev["km"] = 999

        if ev["km"] <= max_km:
            result.append(ev)

    print(f"  {len(result)} events within {max_km} km")
    return sorted(result, key=lambda e: e["date_iso"])
