"""
de_dtu.py – Scraper for dtu-kalender.de (Deutsche Triathlon Union).

Fetches ALL German triathlon/duathlon events (no distance pre-filter).
The calendar is paginated; we scan all pages until they are empty.
The JS dashboard handles distance filtering dynamically via STATE_GEO + user PLZ.
"""
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE    = "https://www.dtu-kalender.de/event/sport/"
HEADERS = {"User-Agent": "bockwurst-events/2.0 (github.com/stefangriessmann/sport-events)"}

WDAY_DE = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag",
}


def _parse_row(row) -> dict | None:
    """Parse one event row from the DTU calendar table."""
    cells = row.find_all("td")
    if len(cells) < 4:
        return None

    # Date cell: "Sa, 13.06.2026"
    date_text = cells[0].get_text(" ", strip=True)
    date_m = re.search(r"([A-Za-z]{2}),?\s*(\d{2})\.(\d{2})\.(\d{4})", date_text)
    if not date_m:
        return None
    wday_short, day, mon, yr = date_m.groups()
    date_iso = f"{yr}-{mon}-{day}"
    datum    = f"{wday_short}, {day}.{mon}.{yr}"
    # Optional end date: "– So, 14.06.2026"
    end_m = re.search(r"[-–]\s*[A-Za-z]{2},?\s*(\d{2})\.(\d{2})\.(\d{4})", date_text[date_m.end():])
    if end_m:
        e_day, e_mon, e_yr = end_m.groups()
        date_iso_end = f"{e_yr}-{e_mon}-{e_day}"
        datum_end    = f"{e_day}.{e_mon}.{e_yr}"
    else:
        date_iso_end = None
        datum_end    = None

    # Art / Strecken: "Triathlon Sprint/OD" or "Duathlon"
    art_cell  = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
    art_parts = art_cell.split()
    art       = art_parts[0] if art_parts else "Triathlon"
    strecken  = " ".join(art_parts[1:])

    # Title + URL
    title_cell = cells[2] if len(cells) > 2 else cells[-1]
    a     = title_cell.find("a")
    titel = a.get_text(strip=True) if a else title_cell.get_text(strip=True)
    url   = ""
    if a and a.get("href"):
        href = a["href"]
        url  = href if href.startswith("http") else "https://www.dtu-kalender.de" + href

    # LV (Bundesland abbreviation)
    lv = cells[3].get_text(strip=True) if len(cells) > 3 else ""

    return {
        "art":          art,
        "datum":        datum,
        "datum_end":    datum_end,
        "wochentag":    WDAY_DE.get(wday_short, ""),
        "date_iso":     date_iso,
        "date_iso_end": date_iso_end,
        "km":           None,
        "lat":          None,
        "lon":          None,
        "titel":        titel,
        "strecken":     strecken,
        "verein":       "",
        "lv":           lv,
        "country":      "DE",
        "url":          url,
        "serie":        "",
    }


def fetch(year: int) -> list[dict]:
    """
    Fetch all German triathlon/duathlon events for the given year from dtu-kalender.de.
    Scans all pages (sorted by state) until two consecutive empty pages are found.
    No distance pre-filtering – the JS dashboard filters dynamically.
    """
    today      = date.today().isoformat()
    events:    list[dict] = []
    seen_urls: set[str]   = set()
    empty_streak           = 0

    print(f"[dtu] Fetching ALL {year} events (all German states)...")

    for page in range(1, 100):   # safety cap at 99 pages
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

        new_count = 0
        for row in rows[1:]:   # skip header row
            ev = _parse_row(row)
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
            new_count += 1

        print(f"  Page {page}: +{new_count} new events (total: {len(events)})")

        if new_count == 0:
            empty_streak += 1
            if empty_streak >= 2:
                print("  Two consecutive empty pages – done.")
                break
        else:
            empty_streak = 0

        time.sleep(0.4)

    print(f"  {len(events)} total future events collected (all Germany)")
    return sorted(events, key=lambda e: e["date_iso"])
