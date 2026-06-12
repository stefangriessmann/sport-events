"""
de_triathlonde.py – Scraper for triathlondeutschland.de/termine/veranstaltungskalender

The DTU calendar is server-rendered (Drupal 10), paginated chronologically.
Page 0 = oldest events (2021), newer years on higher pages.
Observed: page 20 = June 2022, so 2026 events ≈ page 85+.

Strategy:
- Start from page START_PAGE (default 80) and scan forward
- Extract year from event URL pattern /MM-YYYY/event-name
- Stop after 3 consecutive pages with no future events
- Filter events: only those with date_iso >= today and year == target year
"""
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE    = "https://www.triathlondeutschland.de/termine/veranstaltungskalender"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bockwurst-events/2.0; +github.com/stefangriessmann/sport-events)"}

# Observed: page 20 = June 2022 → ~3.3 pages per month → ~40 pages per year
# 2026 starts around page 0 + (2026-2021)*40 = page 200... let's check empirically
# Actually page 20 = June 2022, that's ~9 months → ~2.2 pages/month → ~26/year
# 2026 = 2021 + 5 years × 26 pages/year = page ~130
START_PAGE = 110

MONTH_DE = {
    "jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4,
    "mai": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "okt": 10, "nov": 11, "dez": 12,
}

WDAY_FROM_ISO = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

LV_MAP = {
    "Sachsen-Anhalt": "SA", "Sachsen": "SAC", "Thüringen": "THÜ",
    "Bayern": "BAY", "Niedersachsen": "NDS", "Hessen": "HES",
    "Nordrhein-Westfalen": "NRW", "Brandenburg": "BRA", "Mecklenburg-Vorpommern": "MEV",
    "Schleswig-Holstein": "SCH", "Rheinland-Pfalz": "RLP", "Berlin": "BER",
    "Hamburg": "HAM", "Bremen": "BRE", "Saarland": "SAA",
    "Baden-Württemberg": "BAD", "Bayern": "BAY",
}


def _lv_from_state(state_text: str) -> str:
    """Map German state name to abbreviation."""
    for name, code in LV_MAP.items():
        if name.lower() in state_text.lower():
            return code
    return ""


def _parse_date_from_url(url: str) -> str | None:
    """Extract YYYY-MM from URL like /veranstaltungskalender/06-2026/event-name"""
    m = re.search(r"/(\d{2})-(\d{4})/", url)
    if m:
        mon, yr = m.groups()
        return yr, mon
    return None


def _parse_date_from_text(text: str):
    """
    Parse dates like:
      '14  Juni 2026'          → (14, None, 6, 2026)
      '28–29  Aug. 2026'       → (28, 29, 8, 2026)
      '3–5  Juli 2026'         → (3, 5, 7, 2026)
    Returns (day_start, day_end_or_None, month_num, year) or None.
    """
    text = text.strip()
    m = re.match(
        r"(\d{1,2})(?:[–-](\d{1,2}))?\s+"
        r"([A-Za-zÄäÖöÜüß]+\.?)\s+"
        r"(\d{4})",
        text,
    )
    if not m:
        return None
    day_s, day_end_s, mon_s, yr_s = m.groups()
    mon_key = mon_s.lower().rstrip(".").strip()[:3]
    mon_num = MONTH_DE.get(mon_key)
    if not mon_num:
        return None
    return int(day_s), (int(day_end_s) if day_end_s else None), mon_num, int(yr_s)


def _parse_art(titel: str) -> str:
    t = titel.lower()
    if "duathlon" in t or "cross" in t:
        return "Duathlon"
    if "swimrun" in t or "swim" in t:
        return "SwimRun"
    return "Triathlon"


def fetch(year: int) -> list[dict]:
    """
    Fetch all German triathlon events for target year from triathlondeutschland.de.
    """
    today = date.today().isoformat()
    events: list[dict] = []
    seen_urls: set[str] = set()
    empty_streak = 0
    past_streak = 0

    print(f"[triathlondeutschland.de] Fetching {year} events, starting at page {START_PAGE}...")

    # We scan forward until we find events, then backward until they stop
    # Actually: scan forward from START_PAGE
    found_year = False

    for page in range(START_PAGE, 300):  # safety cap
        url = f"{BASE}?page={page}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            time.sleep(1)
            continue

        soup = BeautifulSoup(r.text, "lxml")

        # Find event links — they follow the pattern /aktive/wettkaempfe/veranstaltungskalender/MM-YYYY/
        # or /termine/veranstaltungskalender/ (newer Drupal URLs)
        # The main content area has event items
        main = soup.find("main") or soup.find(id="main-content") or soup

        # Find all links that match event URL pattern
        event_links = main.find_all(
            "a",
            href=re.compile(r"/veranstaltungskalender/\d{2}-\d{4}/")
        )

        if not event_links:
            empty_streak += 1
            print(f"  Page {page}: no event links (streak {empty_streak})")
            if empty_streak >= 5:
                break
            time.sleep(0.3)
            continue
        empty_streak = 0

        page_events = 0
        page_max_year = 0
        page_min_year = 9999

        for a_tag in event_links:
            href = a_tag["href"]
            full_url = href if href.startswith("http") else "https://www.triathlondeutschland.de" + href

            parsed = _parse_date_from_url(full_url)
            if not parsed:
                continue
            yr_s, mon_s = parsed
            yr_num = int(yr_s)
            page_max_year = max(page_max_year, yr_num)
            page_min_year = min(page_min_year, yr_num)

            if yr_num != year:
                continue

            titel = a_tag.get_text(strip=True)
            if not titel or full_url in seen_urls:
                continue

            # Try to extract day from surrounding text
            parent = a_tag.parent
            # Look for date text near the link
            surrounding = ""
            for ancestor in [parent, parent.parent if parent else None]:
                if ancestor:
                    surrounding = ancestor.get_text(" ", strip=True)
                    break

            day = 1  # default
            day_end = None
            parsed_date = _parse_date_from_text(surrounding)
            if parsed_date:
                day, day_end, mon_num, yr_check = parsed_date
            else:
                mon_num = int(mon_s)

            try:
                date_iso = f"{yr_s}-{int(mon_s):02d}-{day:02d}"
                dt = date(int(yr_s), int(mon_s), day)
                wd = dt.weekday()
                datum = f"{WDAY_FROM_ISO[wd][:2]}, {day:02d}.{int(mon_s):02d}.{yr_s}"
                wochentag = WDAY_FROM_ISO[wd]
            except ValueError:
                date_iso = f"{yr_s}-{int(mon_s):02d}-01"
                datum = f"01.{int(mon_s):02d}.{yr_s}"
                wochentag = ""

            if day_end:
                try:
                    date_iso_end = f"{yr_s}-{int(mon_s):02d}-{day_end:02d}"
                    datum_end    = f"{day_end:02d}.{int(mon_s):02d}.{yr_s}"
                except Exception:
                    date_iso_end = None
                    datum_end    = None
            else:
                date_iso_end = None
                datum_end    = None

            if date_iso < today:
                continue

            # Try to get location from sibling text nodes
            # The structure is: date text → location text → link
            location = ""
            state = ""
            # Look for the parent container
            container = a_tag.find_parent(lambda t: t.name in ["li", "div", "article", "section"])
            if container:
                text_chunks = [s.strip() for s in container.stripped_strings if s.strip()]
                for chunk in text_chunks:
                    if "," in chunk and len(chunk) < 80 and not chunk.startswith("["):
                        parts = chunk.split(",", 1)
                        if len(parts) == 2:
                            location = parts[0].strip()
                            state = parts[1].strip()
                            break

            lv = _lv_from_state(state or surrounding)
            art = _parse_art(titel)

            seen_urls.add(full_url)
            events.append({
                "art":          art,
                "datum":        datum,
                "datum_end":    datum_end,
                "wochentag":    wochentag,
                "date_iso":     date_iso,
                "date_iso_end": date_iso_end,
                "km":           None,
                "lat":          None,
                "lon":          None,
                "titel":        titel,
                "ort":          location,
                "strecken":     "",
                "verein":       "",
                "lv":           lv,
                "country":      "DE",
                "url":       full_url,
                "serie":     "",
            })
            page_events += 1
            found_year = True

        print(f"  Page {page}: years {page_min_year}-{page_max_year}, +{page_events} events for {year} (total {len(events)})")

        # Stop conditions
        if found_year and page_max_year < year:
            past_streak += 1
            if past_streak >= 3:
                print(f"  3 consecutive pages past {year} — stopping")
                break
        elif found_year and page_min_year > year:
            print(f"  Already past {year} (min year: {page_min_year}) — stopping")
            break
        else:
            past_streak = 0

        time.sleep(0.4)

    print(f"  {len(events)} total future {year} events collected")
    return sorted(events, key=lambda e: e["date_iso"])
