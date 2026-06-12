"""
de_radsport_events.py – Scraper for radsport-events.de cycling calendar.

Full listing (server-rendered HTML, ISO-8859-1):
  https://radsport-events.de/Termine-Hobby-und-Jedermannrennen/kalender.php
Pagination: ?kal_Start=N  (N=1, 22, 43, 64, ...; step=21; last page ≈ 673)
Event canonical URL: ?kal_Aktion=detail&kal_Nummer=NNNN

Table columns per event row:
  1. Date (possibly multi-day: "11.06.2026 Do – 13.06.2026 Sa")
  2. Title (link contains kal_Nummer)
  3. Category text (Radtourenfahrt, Brevet, Radmarathon, ...)
  4. Distance / Höhenmeter
  5. Location: [PLZ] City  /  Country [State]

Scope: Germany-only, future events, current year.
"""
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE      = "https://radsport-events.de/Termine-Hobby-und-Jedermannrennen/kalender.php"
HEADERS   = {
    "User-Agent": "Mozilla/5.0 (compatible; bockwurst-events/2.0; +github.com/stefangriessmann/sport-events)",
}

# Pagination step observed from links: kal_Start 1,22,43,64,...  (step 21)
PAGE_STEP = 21

# art values to skip entirely
SKIP_ARTS = {
    "Etappenfahrt", "Sonstige", "Vintage-Tour", "Triathlon", "Duathlon",
    "Swimrun", "Swim & Run", "24 h Rennen", "12 h Rennen",
}

# Map radsport-events.de category → internal art value
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

# German state names → our LV code
STATE_MAP = [
    ("sachsen-anhalt",      "SA"),
    ("sachsen",             "SAC"),
    ("thüringen",           "THÜ"),
    ("thueringen",          "THÜ"),
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
    ("württemberg",         "WÜR"),
    ("wuerttemberg",        "WÜR"),
    ("baden",               "BAD"),
]

WDAY_DE = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}


def _lv_from_state(state_text: str) -> str:
    t = state_text.lower()
    for fragment, code in STATE_MAP:
        if fragment in t:
            return code
    return ""


def _parse_date_cell(cell_text: str):
    """
    Parse date cell, possibly multi-day.
    Examples:
      '31.05.2026 So'
      '11.06.2026 Do - 13.06.2026 Sa'
      '12.06.2026 Fr\n- 13.06.2026 Sa'
    Returns (date_iso_start, date_iso_end_or_None, datum, datum_end_or_None, wochentag)
    """
    clean = re.sub(r"\s+", " ", cell_text).strip()

    # Match start date
    start_m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s+([A-Za-z]{2})", clean)
    if not start_m:
        return None

    d1, m1, y1, wd1 = start_m.groups()
    date_iso = f"{y1}-{m1}-{d1}"
    datum    = f"{wd1}, {d1}.{m1}.{y1}"
    wochentag = WDAY_DE.get(wd1, "")

    # Match optional end date after first date
    remainder = clean[start_m.end():]
    end_m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s+([A-Za-z]{2})?", remainder)
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
    Parse location cell.
    Examples:
      '21073 Hamburg\nDeutschland Hamburg'
      'Motala\nSchweden'
      '69115 Heidelberg\nDeutschland Baden-Württemberg'
    Returns (ort, country, lv)
    """
    lines = [l.strip() for l in cell_text.strip().splitlines() if l.strip()]
    if not lines:
        return "", "", ""

    # First line: optional PLZ + city
    ort_line = lines[0]
    plz_m = re.match(r"(\d{4,5})\s+(.+)", ort_line)
    ort = plz_m.group(2) if plz_m else ort_line

    # Second line: country + optional state
    country = ""
    lv = ""
    if len(lines) >= 2:
        country_line = lines[1]
        parts = country_line.split(None, 1)  # split on first whitespace
        country = parts[0] if parts else ""
        state   = parts[1] if len(parts) > 1 else ""
        lv = _lv_from_state(state)

    return ort, country, lv


def fetch(year: int) -> list[dict]:
    """
    Fetch all German cycling events for the given year from radsport-events.de.
    Filters to Germany only; skips arts in SKIP_ARTS.
    """
    today  = date.today().isoformat()
    events: list[dict] = []
    seen_ids: set[str] = set()

    print(f"[radsport-events.de] Fetching {year} cycling events...")

    # Determine total pages first (read page 1)
    last_start = None
    kal_start  = 1  # first page starts at 1 per observed URLs

    page_num = 0
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

        # Detect last page kal_Start from ">|" pagination link
        if last_start is None:
            last_link = soup.find("a", title="Ende")
            if last_link and last_link.get("href"):
                m = re.search(r"kal_Start=(\d+)", last_link["href"])
                if m:
                    last_start = int(m.group(1))
                    print(f"  Last page at kal_Start={last_start}")

        # Find all event rows — each <tr> or container with a kal_Nummer link
        # The page uses a table with rows per event
        rows = soup.find_all("tr")
        if not rows:
            # Fallback: look for any anchor with kal_Nummer
            rows = soup.find_all("td")

        page_count = 0
        # Process table rows
        table = soup.find("table")
        if not table:
            print(f"  Page {page_num}: no table found")
        else:
            trows = table.find_all("tr")
            for tr in trows:
                tds = tr.find_all("td")
                if len(tds) < 4:
                    continue

                # Column 0: date
                date_text = tds[0].get_text(" ", strip=True)
                parsed = _parse_date_cell(date_text)
                if not parsed:
                    continue
                date_iso, date_iso_end, datum, datum_end, wochentag = parsed

                # Filter by year and future
                if not date_iso.startswith(str(year)):
                    continue
                if date_iso < today:
                    continue

                # Column 1: title + kal_Nummer link
                a_tag = tds[1].find("a", href=re.compile(r"kal_Nummer=\d+"))
                if not a_tag:
                    continue
                titel = a_tag.get_text(strip=True)
                href  = a_tag["href"]
                num_m = re.search(r"kal_Nummer=(\d+)", href)
                if not num_m:
                    continue
                kal_num = num_m.group(1)
                if kal_num in seen_ids:
                    continue
                seen_ids.add(kal_num)
                url_ev = f"{BASE}?kal_Aktion=detail&kal_Nummer={kal_num}"

                # Column 2: category
                # Category is often in a <span> or second text node in column 1 or a dedicated column
                # Layout: col0=date, col1=title (with category below), col2=distance, col3=location
                # Actually check how many cols there are
                cat_text = ""
                if len(tds) >= 3:
                    # Category sometimes lives as second line in col1
                    col1_lines = [l.strip() for l in tds[1].get_text("\n").splitlines() if l.strip()]
                    cat_text = col1_lines[1] if len(col1_lines) > 1 else ""

                # Normalise category
                art_raw = cat_text.strip()
                art = ART_MAP.get(art_raw, "")
                if not art:
                    # Try partial match
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
                    elif "jedermann" in art_lower:
                        art = "Marathon"
                    elif "volksrad" in art_lower:
                        art = "Volksradfahren"
                    elif "hobbyrennen" in art_lower:
                        art = "Marathon"
                    else:
                        continue  # skip unknown/unwanted types

                if art_raw in SKIP_ARTS or art_raw.lower() in {s.lower() for s in SKIP_ARTS}:
                    continue

                # Column 2: distance / strecken
                dist_col = tds[2] if len(tds) > 2 else None
                strecken = dist_col.get_text(" ", strip=True) if dist_col else ""

                # Column 3: location
                loc_col  = tds[3] if len(tds) > 3 else None
                loc_text = loc_col.get_text("\n", strip=True) if loc_col else ""
                ort, country, lv = _parse_location(loc_text)

                # Germany only
                if country.lower() not in ("deutschland", "de", ""):
                    continue
                if not country:
                    continue  # no country info → skip

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

        # Advance to next page
        if last_start is not None and kal_start >= last_start:
            break
        kal_start += PAGE_STEP
        time.sleep(0.4)

        # Safety cap
        if page_num > 50:
            print("  Safety cap reached (50 pages)")
            break

    print(f"  {len(events)} total future {year} events collected (Germany only)")
    return sorted(events, key=lambda e: e["date_iso"])
