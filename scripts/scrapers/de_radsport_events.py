"""
de_radsport_events.py – Scraper for radsport-events.de cycling calendar.

Full listing (server-rendered HTML, ISO-8859-1):
  https://radsport-events.de/Termine-Hobby-und-Jedermannrennen/kalender.php
Pagination: ?kal_Start=N  (N=1, 22, 43, 64, ...; step=21)
Event canonical URL: ?kal_Aktion=detail&kal_Nummer=NNNN

HTML structure per event (4 x div.kalTbLst inside a per-event container div):
  cells[0] = date:       "27.06.2026\xa0Sa-\xa028.06.2026\xa0So"  (or single day)
  cells[1] = title+cat:  <a class="kalDetl">TITLE</a><div class="uzl">CATEGORY</div>
  cells[2] = distance:   "122 / 233 / 333 km 2500 / 4600 / 6400 Hm"
  cells[3] = location:   PLZ + City + Country + State (may be concatenated)

Scope: Germany-only, future events, current year.
"""
from __future__ import annotations  # Python 3.9 compat for type hints
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

BASE      = "https://radsport-events.de/Termine-Hobby-und-Jedermannrennen/kalender.php"
HEADERS   = {
    "User-Agent": "Mozilla/5.0 (compatible; bockwurst-events/2.0; +github.com/stefangriessmann/sport-events)",
}

PAGE_STEP = 21

SKIP_ARTS = {
    "Etappenfahrt", "Sonstige", "Vintage-Tour", "Triathlon", "Duathlon",
    "Swimrun", "Swim & Run", "24 h Rennen", "12 h Rennen",
}

ART_MAP = {
    "Radtourenfahrt":   "RTF",
    "Radtourenfahrten": "RTF",
    "Brevet":           "Brevet",
    "Radmarathon":      "Marathon",
    "Jedermannrennen":  "Marathon",
    "Hobbyrennen":      "Marathon",
    "Volksradfahren":   "Volksradfahren",
    "Einzelzeitfahren": "CTF",
    "Bergzeitfahren":   "CTF",
    "Gravelride":       "Gravelride",
    "Gravelevent":      "Gravelride",
    "Gravel":           "Gravelride",
}

STATE_MAP = [
    ("sachsen-anhalt",      "SA"),
    ("sachsen",             "SAC"),
    ("thüringen",      "THÜ"),
    ("thueringen",          "THÜ"),
    ("thuringen",           "THÜ"),
    ("thuring",             "THÜ"),
    ("bayern",              "BAY"),
    ("niedersachsen",       "NDS"),
    ("hessen",              "HES"),
    ("nordrhein-westfalen", "NRW"),
    ("nordrhein",           "NRW"),
    ("westfalen",           "NRW"),
    ("brandenburg",         "BRA"),
    ("mecklenburg",         "MEV"),
    ("vorpommern",          "MEV"),
    ("schleswig-holstein",  "SCH"),
    ("schleswig",           "SCH"),
    ("rheinland-pfalz",     "RLP"),
    ("rheinland",           "RLP"),
    ("berlin",              "BER"),
    ("hamburg",             "HAM"),
    ("bremen",              "BRE"),
    ("saarland",            "SAA"),
    ("württemberg",    "WÜR"),
    ("wuerttemberg",        "WÜR"),
    ("wurttemberg",         "WÜR"),
    ("baden",               "BAD"),
]

WDAY_DE = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}

# Known country keywords to split location text
COUNTRY_KEYWORDS = [
    "Deutschland", "Frankreich", "Österreich", "Oesterreich",
    "Schweiz", "Italien", "Belgien", "Niederlande", "Spanien",
    "Tschechien", "Polen", "Dänemark",
]


def _lv_from_state(state_text: str) -> str:
    t = state_text.lower()
    for fragment, code in STATE_MAP:
        if fragment in t:
            return code
    return ""


def _parse_date_cell(cell_text: str):
    """
    Parse date cell, possibly multi-day.
    Handles \\xa0 (non-breaking space) used as separator on radsport-events.de.
    Examples:
      '31.05.2026\\xa0So'
      '27.06.2026\\xa0Sa-\\xa028.06.2026\\xa0So'
    Returns (date_iso, date_iso_end, datum, datum_end, wochentag) or None.
    """
    # Normalise non-breaking spaces and runs of whitespace to a single space
    clean = re.sub(r"[\xa0\s]+", " ", cell_text).strip()

    start_m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s+([A-Za-z]{2})", clean)
    if not start_m:
        return None

    d1, m1, y1, wd1 = start_m.groups()
    date_iso  = f"{y1}-{m1}-{d1}"
    datum     = f"{wd1}, {d1}.{m1}.{y1}"
    wochentag = WDAY_DE.get(wd1, "")

    remainder = clean[start_m.end():]
    end_m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s+([A-Za-z]{2}))?", remainder)
    if end_m:
        d2, m2, y2 = end_m.group(1), end_m.group(2), end_m.group(3)
        date_iso_end = f"{y2}-{m2}-{d2}"
        datum_end    = f"{d2}.{m2}.{y2}"
    else:
        date_iso_end = None
        datum_end    = None

    return date_iso, date_iso_end, datum, datum_end, wochentag


def _parse_location(cell_text: str):
    """
    Parse location cell from radsport-events.de.

    HTML child elements produce varying line structures when using get_text("\\n"):
      [city, PLZ, country, state]           (most common)
      [PLZ, city, country, state]
      [PLZ+city, country, state]            (concatenated, single line)
      "PLZCityCountryState"                 (all concatenated, no newlines)

    Approach:
      1. Detect foreign country anywhere in full text → reject.
      2. Detect "Deutschland" anywhere in full text → accept.
      3. Find the country line and extract city from lines before it.
      4. Fall back to single-line split on "Deutschland".

    Returns (ort, country_raw, lv).
    country_raw="" means Germany assumed (site is German-focused, accept the event).
    """
    # Normalised full text – use for country/state keyword search
    full = re.sub(r"[\xa0]", " ", cell_text)
    full_flat = re.sub(r"\s+", " ", full).strip()

    # Step 1 – skip explicit foreign events
    FOREIGN = [
        "Frankreich", "Österreich", "Oesterreich", "Schweiz", "Italien",
        "Belgien", "Niederlande", "Spanien", "Tschechien", "Polen",
        "Dänemark", "France", "Belgium", "Netherlands",
    ]
    for fw in FOREIGN:
        if fw in full_flat:
            return "foreign", fw, ""

    # Step 2 – extract LV from full text (works for all formats)
    lv = _lv_from_state(full_flat)

    # Step 3 – extract city from newline-separated lines
    lines = [l.strip() for l in full.splitlines() if l.strip()]
    if len(lines) >= 2:
        # Find which line contains "Deutschland" (or ends the city block)
        country_idx = next(
            (i for i, l in enumerate(lines) if "Deutschland" in l),
            len(lines)           # not found → treat all lines as pre-country
        )
        pre = lines[:country_idx]          # lines before country
        # First non-PLZ line is the city; PLZ-only line is just digits
        city_lines = [l for l in pre if not re.fullmatch(r"\d{4,5}", l)]
        if city_lines:
            # Remove a leading PLZ from the city line if present
            plz_m = re.match(r"\d{4,5}\s+(.*)", city_lines[0])
            ort = plz_m.group(1).strip() if plz_m else city_lines[0]
        elif pre:
            ort = pre[-1]   # last pre-country line as fallback
        else:
            ort = ""
        country_raw = "Deutschland" if country_idx < len(lines) else ""
        return ort or full_flat[:40], country_raw, lv

    # Step 4 – single-line: split on "Deutschland"
    if "Deutschland" in full_flat:
        before = full_flat[:full_flat.index("Deutschland")]
        plz_m  = re.match(r"\d{4,5}\s*(.*)", before.strip())
        if plz_m:
            ort = plz_m.group(1).strip()
        else:
            # PLZ glued to city: "98724Neuhaus am Rennweg"
            plz_m2 = re.match(r"\d{4,5}(.*)", before.strip())
            ort = plz_m2.group(1).strip() if plz_m2 else before.strip()
        return ort or before.strip() or full_flat[:40], "Deutschland", lv

    # Step 5 – no country keyword at all: accept (German cycling site), best-effort city
    plz_m = re.match(r"\d{4,5}\s*(.*)", full_flat)
    if plz_m:
        ort = plz_m.group(1).strip()
    else:
        plz_m2 = re.match(r"\d{4,5}(.*)", full_flat)
        ort = plz_m2.group(1).strip() if plz_m2 else full_flat[:40]
    return ort or full_flat[:40], "", lv


def fetch(year: int) -> list[dict]:
    """
    Fetch all German cycling events for the given year from radsport-events.de.
    Filters to Germany only; skips arts in SKIP_ARTS.
    """
    today     = date.today().isoformat()
    events: list[dict] = []
    seen_ids: set[str] = set()

    print(f"[radsport-events.de] Fetching {year} cycling events...")

    last_start = None
    kal_start  = 1
    page_num   = 0

    while True:
        page_num += 1
        url = BASE if kal_start == 1 else f"{BASE}?kal_Start={kal_start}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            r.encoding = "iso-8859-1"
        except Exception as e:
            print(f"  Error fetching page {page_num} (kal_Start={kal_start}): {e}")
            time.sleep(1)
            kal_start += PAGE_STEP
            continue

        soup = BeautifulSoup(r.text, "lxml")

        # Detect last page from ">|" pagination link
        if last_start is None:
            last_link = soup.find("a", title="Ende")
            if last_link and last_link.get("href"):
                m = re.search(r"kal_Start=(\d+)", last_link["href"])
                if m:
                    last_start = int(m.group(1))
                    print(f"  Last page at kal_Start={last_start}")

        page_count = 0

        # Each event has an <a class="kalDetl"> link inside a div.kalTbLst.
        # The grandparent of that link is the per-event container with 4 div.kalTbLst children.
        for a_tag in soup.find_all("a", class_="kalDetl"):
            href  = a_tag.get("href", "")
            num_m = re.search(r"kal_Nummer=(\d+)", href)
            if not num_m:
                continue
            kal_num = num_m.group(1)
            if kal_num in seen_ids:
                continue

            title_div = a_tag.parent   # div.kalTbLst that wraps the link
            if not title_div:
                continue
            row = title_div.parent     # per-event container
            if not row:
                continue

            cells = row.find_all("div", class_="kalTbLst")
            if len(cells) < 4:
                continue

            # Cell 0: date
            date_text = re.sub(r"[\xa0\s]+", " ", cells[0].get_text()).strip()
            parsed = _parse_date_cell(date_text)
            if not parsed:
                continue
            date_iso, date_iso_end, datum, datum_end, wochentag = parsed

            # Filter: target year and future only
            if not date_iso.startswith(str(year)):
                continue
            if date_iso < today:
                continue

            # Cell 1: title from link text; category from nested div.uzl
            titel = a_tag.get_text(strip=True)
            if not titel:
                continue

            cat_div = a_tag.find_next_sibling("div", class_="uzl")
            art_raw = cat_div.get_text(strip=True) if cat_div else ""

            art = ART_MAP.get(art_raw, "")
            if not art:
                art_lower = art_raw.lower()
                if "rtf" in art_lower or "radtour" in art_lower:
                    art = "RTF"
                elif "brevet" in art_lower:
                    art = "Brevet"
                elif "marathon" in art_lower:
                    art = "Marathon"
                elif "gravel" in art_lower:
                    art = "Gravelride"
                elif "zeitfahr" in art_lower:
                    art = "CTF"
                elif "jedermann" in art_lower or "hobbyrennen" in art_lower:
                    art = "Marathon"
                elif "volksrad" in art_lower:
                    art = "Volksradfahren"
                else:
                    continue  # skip unknown/unwanted types

            if art_raw in SKIP_ARTS:
                continue

            # Cell 2: distance / strecken
            strecken = cells[2].get_text(" ", strip=True)

            # Cell 3: location
            loc_text = cells[3].get_text("\n", strip=True)
            ort, country_raw, lv = _parse_location(loc_text)

            # Germany only: skip events explicitly tagged as foreign
            if ort == "foreign":
                continue

            seen_ids.add(kal_num)
            url_ev = f"{BASE}?kal_Aktion=detail&kal_Nummer={kal_num}"

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
                "ort":          ort,
                "strecken":     strecken,
                "verein":       "",
                "lv":           lv,
                "country":      "DE",
                "url":          url_ev,
                "serie":        "",
            })
            page_count += 1

        print(f"  Page {page_num} (kal_Start={kal_start}): +{page_count} DE events (total {len(events)})")

        if last_start is not None and kal_start >= last_start:
            break
        kal_start += PAGE_STEP
        time.sleep(0.4)

        if page_num > 50:
            print("  Safety cap reached (50 pages)")
            break

    print(f"  {len(events)} total future {year} events collected (Germany only)")
    return sorted(events, key=lambda e: e["date_iso"])
