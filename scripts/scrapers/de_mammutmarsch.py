"""
de_mammutmarsch.py – Scraper for mammutmarsch.de

Mammutmarsch organises long-distance hiking/marching events (30–100 km) across
Germany and internationally.  This scraper fetches the homepage, parses the
event cards from the Owl-Carousel markup (which is present in the static HTML),
and returns only German events compatible with LAUF_SNAPSHOT.

art = "Marsch" so they appear as their own category in the UI.
"""
from __future__ import annotations

import re
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://mammutmarsch.de/"
HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; bockwurst-events/2.0; "
        "+github.com/stefangriessmann/sport-events)"
    )
}

WDAY = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
        "Freitag", "Samstag", "Sonntag"]

# City name (as found in title) → (state abbreviation, lat, lon)
# Coordinates hardcoded to avoid Nominatim rate-limit issues during scraping.
GERMAN_CITIES: dict[str, tuple[str, float, float]] = {
    "Berlin":     ("BER", 52.5200, 13.4050),
    "Hamburg":    ("HAM", 53.5753, 10.0153),
    "München":    ("BAY", 48.1374, 11.5755),
    "Dresden":    ("SAC", 51.0504, 13.7373),
    "Nürnberg":   ("BAY", 49.4539, 11.0775),
    "Essen":      ("NRW", 51.4556,  7.0116),
    "Dortmund":   ("NRW", 51.5142,  7.4652),
    "Ruhrgebiet": ("NRW", 51.4344,  6.7623),  # Duisburg as proxy
    "Stuttgart":  ("BW",  48.7758,  9.1829),
    "Hannover":   ("NDS", 52.3759,  9.7320),
    "Wiesbaden":  ("HES", 50.0820,  8.2491),
    "Mannheim":   ("BW",  49.4875,  8.4660),
    "Bremen":     ("BRE", 53.0793,  8.8017),
    "Leipzig":    ("SAC", 51.3397, 12.3731),
    "Bayern":     ("BAY", 48.1374, 11.5755),  # "Little Mammut Bayern" → München
}


def _extract_city(title: str) -> str | None:
    """
    'Mammutmarsch Berlin – 75/100 KM'  → 'Berlin'
    'Nachtmammut Hamburg – 30/42 KM'  → 'Hamburg'
    'Mammutmarsch München / Starnberger See – 42/55 KM' → 'München'
    """
    name = re.sub(r'^(Mammutmarsch|Nachtmammut|Little\s+Mammut)\s+',
                  '', title, flags=re.IGNORECASE).strip()
    # Remove distance suffix
    name = re.sub(r'\s*[–\-].*$', '', name).strip()
    # Take part before "/" for compound names
    name = name.split('/')[0].strip()
    return name or None


def _parse_km(title: str) -> int | None:
    """Return maximum distance in km from title like '30/42/100 KM'."""
    m = re.search(r'([\d/]+)\s*KM', title, re.IGNORECASE)
    if not m:
        return None
    nums = re.findall(r'\d+', m.group(1))
    return int(nums[-1]) if nums else None


def fetch(year: int | None = None) -> list[dict]:
    if year is None:
        year = date.today().year

    today_iso = date.today().isoformat()

    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [mammutmarsch] Fetch error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # Owl-Carousel items — in the raw HTML there are no .cloned duplicates yet
    cards = soup.select(".cms-carousel-item")
    if not cards:
        # Fallback: try generic grid/list items
        cards = soup.select(".cms-grid-item, .event-item")

    events: list[dict] = []
    seen_urls: set[str] = set()

    for card in cards:
        # ── Title ──────────────────────────────────────────────────────────────
        title_el = card.select_one("h2, h3, h4, .cms-title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        # ── Date ───────────────────────────────────────────────────────────────
        date_el = card.select_one(".cshero-woo-meta p, .event-date, time")
        if not date_el:
            continue
        date_str = date_el.get_text(strip=True)
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            continue

        date_iso = dt.date().isoformat()
        if date_iso < today_iso:
            continue

        # ── URL ────────────────────────────────────────────────────────────────
        link_el = card.select_one("a[href]")
        url = link_el["href"] if link_el else BASE_URL
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # ── German cities only ─────────────────────────────────────────────────
        city = _extract_city(title)
        if not city or city not in GERMAN_CITIES:
            continue

        lv, lat, lon = GERMAN_CITIES[city]

        # ── Distances ──────────────────────────────────────────────────────────
        km = _parse_km(title)

        # ── Datum string with weekday ──────────────────────────────────────────
        try:
            wd   = dt.weekday()
            datum = f"{WDAY[wd][:2]}, {dt.strftime('%d.%m.%Y')}"
        except Exception:
            datum = date_str

        events.append({
            "art":          "Marsch",
            "datum":        datum,
            "datum_end":    None,
            "wochentag":    WDAY[dt.weekday()],
            "date_iso":     date_iso,
            "date_iso_end": None,
            "km":           km,
            "lat":          lat,
            "lon":          lon,
            "titel":        title,
            "ort":          city,
            "lv":           lv,
            "country":      "DE",
            "url":          url,
        })

    print(f"  [mammutmarsch] {len(events)} German events found")
    return sorted(events, key=lambda e: e["date_iso"])
