"""
de_dtu.py – Scraper for dtu-kalender.de (Deutsche Triathlon Union).

The calendar is sorted by state (sort=state). Relevant states for events
near Chemnitz: Sachsen (SAC), Sachsen-Anhalt (SA), Thüringen (THÜ).
Based on empirical observation these appear on pages 19–23.
We fetch those pages plus a buffer to catch all nearby events.
"""
import re
import time
import math
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from geocoder import geocode_event

BASE = "https://www.dtu-kalender.de/event/sport/"
# PLZ 09111 = Chemnitz (50.8333, 12.9167)
CHEMNITZ = (50.8333, 12.9167)
MAX_KM = 200
TARGET_STATES = {"SAC", "SA", "THÜ", "BAY"}   # states within ~200 km
HEADERS = {"User-Agent": "sport-events-chemnitz/2.0 (github actions)"}

WDAY_DE = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}
MONTHS_DE = {
    "Jan": 1, "Feb": 2, "Mär": 3, "Apr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Dez": 12,
}


def _haversine(lat1, lon1, lat2, lon2) -> int:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return int(R * 2 * math.asin(math.sqrt(a)))


# Approximate state-centre coordinates for fallback distance
STATE_CENTRES = {
    "SAC": (51.05, 13.20),
    "SA":  (51.90, 11.80),
    "THÜ": (51.00, 11.00),
    "BAY": (48.80, 11.50),
}


def _parse_row(row) -> dict | None:
    """Parse one event row from the DTU calendar table."""
    cells = row.find_all("td")
    if len(cells) < 4:
        return None

    # --- Date cell ---
    date_text = cells[0].get_text(" ", strip=True)
    # Format: "Sa, 13.06.2026" or "Fr, 04.09.2026"
    date_m = re.search(r"([A-Za-z]{2}),?\s*(\d{2})\.(\d{2})\.(\d{4})", date_text)
    if not date_m:
        return None
    wday_short, day, mon, yr = date_m.groups()
    date_iso = f"{yr}-{mon}-{day}"
    datum = f"{wday_short}, {day}.{mon}.{yr}"

    # --- Art / Strecken ---
    art_cell = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
    # Typical: "Triathlon Sprint/OD" or "Duathlon"
    art_parts = art_cell.split()
    art = art_parts[0] if art_parts else "Triathlon"
    strecken = " ".join(art_parts[1:])

    # --- Title + URL ---
    title_cell = cells[2] if len(cells) > 2 else cells[-1]
    a = title_cell.find("a")
    titel = (a.get_text(strip=True) if a else title_cell.get_text(strip=True))
    url = ""
    if a and a.get("href"):
        href = a["href"]
        url = href if href.startswith("http") else "https://www.dtu-kalender.de" + href

    # --- LV / state ---
    lv_cell = cells[3].get_text(strip=True) if len(cells) > 3 else ""
    lv = lv_cell.strip()

    return {
        "art": art,
        "datum": datum,
        "wochentag": WDAY_DE.get(wday_short, ""),
        "date_iso": date_iso,
        "km": None,   # will be set after geocoding
        "lat": None,
        "lon": None,
        "titel": titel,
        "strecken": strecken,
        "verein": "",
        "lv": lv,
        "country": "DE",
        "url": url,
        "serie": "",
    }


def fetch(year: int, max_km: int = MAX_KM) -> list[dict]:
    """
    Fetch triathlon/duathlon events near Chemnitz from the DTU calendar.
    Pages are state-sorted; we scan pages 15–25 to capture SAC/SA/THÜ/BAY.
    """
    today = date.today().isoformat()
    events: list[dict] = []
    seen_urls: set[str] = set()

    print(f"[dtu] Fetching {year} events (pages 14-25)...")

    for page in range(14, 26):
        url = f"{BASE}?sort=state&page={page}&year={year}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            time.sleep(1)
            continue

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table tr")

        page_states: set[str] = set()
        for row in rows[1:]:  # skip header
            ev = _parse_row(row)
            if not ev:
                continue
            page_states.add(ev["lv"])
            if ev["lv"] not in TARGET_STATES:
                continue
            if ev["date_iso"] < today:
                continue
            if ev["url"] and ev["url"] in seen_urls:
                continue
            if ev["url"]:
                seen_urls.add(ev["url"])
            events.append(ev)

        print(f"  Page {page}: states seen = {sorted(page_states)}")
        time.sleep(0.5)

        # Stop early if we're past Thüringen (alphabetically last target state)
        if page_states and all(s > "THÜ" for s in page_states if s):
            print("  Past target states, stopping.")
            break

    print(f"  {len(events)} candidate events collected")

    # Geocode + compute km
    print("  Geocoding and computing distances...")
    result: list[dict] = []
    for ev in events:
        geo = geocode_event(ev["titel"], country="DE")
        if geo:
            ev["lat"], ev["lon"] = round(geo[0], 4), round(geo[1], 4)
            ev["km"] = _haversine(*CHEMNITZ, *geo)
        else:
            # Fallback: state centre
            centre = STATE_CENTRES.get(ev["lv"])
            if centre:
                ev["km"] = _haversine(*CHEMNITZ, *centre)
            else:
                ev["km"] = 999

        if ev["km"] <= max_km:
            result.append(ev)

    print(f"  {len(result)} events within {max_km} km")
    return sorted(result, key=lambda e: e["date_iso"])
