"""
de_triathlonde.py – Scraper for triathlondeutschland.de/termine/veranstaltungskalender

The DTU calendar is server-rendered (Drupal 10), paginated.
URL structure changed: date filter params are now required.
Use date_from[min]=today & date_from[max]=12/31/year to get upcoming events for target year.
Start from page 0. Stop after 3 consecutive empty pages.

Location extraction: calendar list view doesn't include city names, so we fetch
each event's detail page to get the location. Results are cached in data/tri_location_cache.json.
"""
from __future__ import annotations
import json
import re
import time
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from _geocode import geocode

# --- Location detail-page cache ---
_LOC_CACHE_PATH = Path("data") / "tri_location_cache.json"
_loc_cache: dict[str, str] | None = None
_last_req = 0.0

def _load_loc_cache() -> dict[str, str]:
    global _loc_cache
    if _loc_cache is None:
        if _LOC_CACHE_PATH.exists():
            with open(_LOC_CACHE_PATH, encoding="utf-8") as f:
                _loc_cache = json.load(f)
        else:
            _loc_cache = {}
    return _loc_cache

def _save_loc_cache() -> None:
    _LOC_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOC_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(_loc_cache, f, ensure_ascii=False, indent=2)

def _fetch_detail_location(url: str) -> str:
    """
    Fetch an event detail page and extract the location/city name.
    Caches results so repeated scraper runs don't re-fetch.
    Returns empty string if location not found.
    """
    global _last_req
    cache = _load_loc_cache()
    if url in cache:
        return cache[url]

    # Rate limit: max 1 req/s
    elapsed = time.time() - _last_req
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        _last_req = time.time()
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        location = ""

        # Strategy 1: DTU RDFa microdata – <span class="locality">City</span>
        # Page structure: <p property="location" typeof="Place">
        #   <span property="address" typeof="PostalAddress">
        #     <span property="addressRegion">
        #       <span class="locality">Roth</span>, <span property="addressLocality">Bayern</span>
        #     </span>
        #   </span>
        # </p>
        loc_el = soup.find("span", class_="locality")
        if loc_el:
            txt = loc_el.get_text(strip=True)
            if txt and 2 < len(txt) < 60:
                location = txt

        # Strategy 2: Drupal field selectors
        if not location:
            for sel in [
                "[class*='field--name-field-ort']",
                "[class*='field--name-field-veranstaltungsort']",
                "[class*='field--name-field-stadt']",
                "[class*='field--name-field-city']",
                "[class*='field-name-field-ort']",
            ]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 60:
                        location = txt
                        break

        # Strategy 3: Schema.org itemprop or RDFa property for addressLocality
        if not location:
            for attr in [{"itemprop": "addressLocality"}, {"property": "addressLocality"},
                         {"itemprop": "location"}, {"property": "location"}]:
                loc_el = soup.find(attrs=attr)
                if loc_el:
                    txt = loc_el.get_text(strip=True)
                    if txt and 2 < len(txt) < 60:
                        location = txt
                        break

        # Strategy 4: "Ort:" / "Veranstaltungsort:" label in page text
        if not location:
            page_text = soup.get_text("\n")
            for pattern in [
                r"(?:Ort|Veranstaltungsort|Stadt|Austragungsort)\s*:\s*([^\n,]{2,50})",
                r"(?:Location|Place)\s*:\s*([^\n,]{2,50})",
            ]:
                m = re.search(pattern, page_text, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    if candidate and len(candidate) < 60:
                        location = candidate
                        break

        # Strategy 5: First comma-separated text in meta description
        if not location:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                parts = meta_desc["content"].split(",")
                if len(parts) >= 2:
                    candidate = parts[0].strip()
                    if 2 < len(candidate) < 50 and candidate.lower() not in ("triathlon","duathlon","swimrun"):
                        location = candidate

        cache[url] = location
        _save_loc_cache()
        return location

    except Exception as e:
        _last_req = time.time()
        print(f"  [detail] Error fetching {url}: {e}")
        cache[url] = ""  # cache failure too to avoid retry storms
        _save_loc_cache()
        return ""

BASE    = "https://www.triathlondeutschland.de/aktive/wettkaempfe/veranstaltungskalender"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bockwurst-events/2.0; +github.com/stefangriessmann/sport-events)"}

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
    "Baden-Württemberg": "BAD",
}


def _lv_from_state(state_text: str) -> str:
    for name, code in LV_MAP.items():
        if name.lower() in state_text.lower():
            return code
    return ""


def _parse_date_from_url(url: str):
    """Extract (year_str, month_str) from URL like /veranstaltungskalender/06-2026/event-name"""
    m = re.search(r"/veranstaltungskalender/(\d{2})-(\d{4})/", url)
    if m:
        mon, yr = m.groups()
        return yr, mon
    # also match /wettkaempfe/veranstaltungskalender/06-2026/
    m = re.search(r"/(\d{2})-(\d{4})/", url)
    if m:
        mon, yr = m.groups()
        return yr, mon
    return None


def _parse_date_from_text(text: str):
    """
    Parse dates like:
      '14  Juni 2026'      → (14, None, 6, 2026)
      '28–29  Aug. 2026'   → (28, 29, 8, 2026)
    Returns (day_start, day_end_or_None, month_num, year) or None.
    """
    text = text.strip()
    m = re.match(
        r"(\d{1,2})(?:[–\-](\d{1,2}))?\s+"
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
    if "duathlon" in t or "crossduathlon" in t:
        return "Duathlon"
    if "swimrun" in t or "swim & run" in t:
        return "SwimRun"
    if "aquathlon" in t:
        return "Aquathlon"
    if "aquabike" in t:
        return "Aquabike"
    return "Triathlon"


def fetch(year: int) -> list[dict]:
    """
    Fetch all German triathlon events for target year from triathlondeutschland.de.
    Uses date-filtered URL to avoid the old page-offset guessing.
    """
    today = date.today()
    today_iso = today.isoformat()
    today_str = today.strftime("%m/%d/%Y")   # MM/DD/YYYY for Drupal param
    year_end  = f"12/31/{year}"

    events: list[dict] = []
    seen_urls: set[str] = set()
    empty_streak = 0

    print(f"[triathlondeutschland.de] Fetching {year} events from page 0 with date filter...")

    for page in range(0, 100):   # safety cap: 100 pages × 20 events = 2000 max
        url = f"{BASE}?page={page}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            time.sleep(1)
            continue

        soup = BeautifulSoup(r.text, "lxml")

        # Event links follow /veranstaltungskalender/MM-YYYY/ or /wettkaempfe/veranstaltungskalender/MM-YYYY/
        event_links = soup.find_all(
            "a",
            href=re.compile(r"/veranstaltungskalender/\d{2}-\d{4}/")
        )

        if not event_links:
            empty_streak += 1
            print(f"  Page {page}: no event links (streak {empty_streak})")
            if empty_streak >= 3:
                break
            time.sleep(0.5)
            continue
        empty_streak = 0

        page_events = 0

        for a_tag in event_links:
            href = a_tag["href"]
            full_url = href if href.startswith("http") else "https://www.triathlondeutschland.de" + href

            if full_url in seen_urls:
                continue

            parsed = _parse_date_from_url(full_url)
            if not parsed:
                continue
            yr_s, mon_s = parsed
            yr_num = int(yr_s)

            # Skip events outside target year
            if yr_num != year:
                continue

            titel = a_tag.get_text(strip=True)
            if not titel:
                continue

            # Extract date text and location from surrounding container
            container = a_tag.find_parent(lambda t: t.name in ["li", "div", "article", "section"])
            surrounding = ""
            location = ""
            state = ""
            if container:
                text_chunks = [s.strip() for s in container.stripped_strings if s.strip()]
                for chunk in text_chunks:
                    if not surrounding:
                        parsed_date_text = _parse_date_from_text(chunk)
                        if parsed_date_text:
                            surrounding = chunk
                    if "," in chunk and len(chunk) < 80 and chunk != titel:
                        parts = chunk.split(",", 1)
                        if len(parts) == 2 and len(parts[0]) < 50:
                            location = parts[0].strip()
                            state = parts[1].strip()

            # Parse day from surrounding text
            day = 1
            day_end = None
            parsed_date_result = _parse_date_from_text(surrounding)
            if parsed_date_result:
                day, day_end, mon_num, yr_check = parsed_date_result
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

            if date_iso < today_iso:
                continue

            lv  = _lv_from_state(state or surrounding)
            art = _parse_art(titel)

            # If list view didn't yield location, fetch detail page
            if not location and full_url:
                location = _fetch_detail_location(full_url)

            coords = geocode(location)

            seen_urls.add(full_url)
            events.append({
                "art":          art,
                "datum":        datum,
                "datum_end":    datum_end,
                "wochentag":    wochentag,
                "date_iso":     date_iso,
                "date_iso_end": date_iso_end,
                "km":           None,
                "lat":          coords["lat"],
                "lon":          coords["lon"],
                "titel":        titel,
                "ort":          location,
                "plz":          "",
                "strecken":     "",
                "verein":       "",
                "lv":           lv,
                "country":      "DE",
                "url":          full_url,
                "serie":        "",
            })
            page_events += 1

        print(f"  Page {page}: +{page_events} events for {year} (total {len(events)})")
        time.sleep(0.4)

    print(f"  {len(events)} total future {year} events collected")
    return sorted(events, key=lambda e: e["date_iso"])
