"""
de_laufen.py – Scraper for laufen.run/kalender (national running calendar).

The site uses a Joomla CMS and renders events in an HTML <table>.
Each row: date (DD.MM.YYYY) | event title+link | location | cup | distance
Some rows are month/year headers — these are skipped.
"""
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

BASE    = "https://laufen.run/kalender"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bockwurst-events/2.0; +github.com/stefangriessmann/sport-events)"}

WDAY_FROM_ISO = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

ART_MAP = [
    ("trail",    "Trail"),
    ("berg",     "Trail"),
    ("forst",    "Trail"),
    ("ultra",    "Ultra"),
    ("backyard", "Ultra"),
    ("marathon", "Laufen"),
    ("lauf",     "Laufen"),
    ("run",      "Laufen"),
    ("walk",     "Laufen"),
    ("nordic",   "Laufen"),
]

STATE_DETECT = [
    ("sachsen-anhalt",  "SA"),
    ("sachsen",         "SAC"),
    ("thüringen",       "THÜ"),
    ("thueringen",      "THÜ"),
    ("bayern",          "BAY"),
    ("niedersachsen",   "NDS"),
    ("hessen",          "HES"),
    ("nordrhein",       "NRW"),
    ("westfalen",       "NRW"),
    ("brandenburg",     "BRA"),
    ("mecklenburg",     "MEV"),
    ("vorpommern",      "MEV"),
    ("schleswig",       "SCH"),
    ("holstein",        "SCH"),
    ("rheinland-pfalz", "RLP"),
    ("rheinland",       "RLP"),
    ("berlin",          "BER"),
    ("hamburg",         "HAM"),
    ("bremen",          "BRE"),
    ("saarland",        "SAA"),
    ("baden",           "BAD"),
    ("württemberg",     "WÜR"),
    ("wuerttemberg",    "WÜR"),
]


def _detect_art(titel: str) -> str:
    t = titel.lower()
    for keyword, art in ART_MAP:
        if keyword in t:
            return art
    return "Laufen"


def _detect_lv(text: str) -> str:
    t = text.lower()
    for fragment, lv in STATE_DETECT:
        if fragment in t:
            return lv
    return ""


def fetch(year: int) -> list[dict]:
    """
    Fetch all German running events for the given year from laufen.run/kalender.
    The page is server-rendered with a full HTML table — all year events on one page.
    """
    today      = date.today().isoformat()
    events:    list[dict] = []
    seen_urls: set[str]   = set()

    print(f"[laufen.run] Fetching {year} events...")

    html = ""
    for url in [BASE, f"{BASE}?year={year}"]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            if len(r.text) > 10000:
                html = r.text
                print(f"  Got {len(html)} bytes from {url}")
                break
        except Exception as e:
            print(f"  Error fetching {url}: {e}")

    if not html:
        print("  Could not fetch laufen.run")
        return []

    soup = BeautifulSoup(html, "lxml")

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells_el = row.find_all("td")
            if len(cells_el) < 2:
                continue

            cells = [c.get_text(" ", strip=True) for c in cells_el]
            date_text = cells[0].strip()

            # Formats: "12.06.2026" or "12.-14.06.2026" or "12.-14.06.2026"
            date_m = re.match(r"(\d{1,2})(?:\.[-–](\d{1,2}))?\.(\d{2})\.(\d{4})", date_text)
            if not date_m:
                continue

            d_str, d_end_str, mo_str, yr_str = date_m.groups()
            if int(yr_str) != year:
                continue

            date_iso = f"{yr_str}-{mo_str}-{int(d_str):02d}"
            if date_iso < today:
                continue

            if d_end_str:
                date_iso_end = f"{yr_str}-{mo_str}-{int(d_end_str):02d}"
                datum_end    = f"{int(d_end_str):02d}.{mo_str}.{yr_str}"
            else:
                date_iso_end = None
                datum_end    = None

            try:
                from datetime import date as ddate
                wd = ddate(int(yr_str), int(mo_str), int(d_str)).weekday()
                wochentag = WDAY_FROM_ISO[wd]
                datum = f"{WDAY_FROM_ISO[wd][:2]}, {int(d_str):02d}.{mo_str}.{yr_str}"
            except Exception:
                datum = f"{int(d_str):02d}.{mo_str}.{yr_str}"
                wochentag = ""

            # Title + URL from 2nd cell
            a = cells_el[1].find("a")
            titel = a.get_text(strip=True) if a else cells[1]
            if not titel:
                continue

            url_ev = ""
            if a and a.get("href"):
                href = a["href"]
                url_ev = href if href.startswith("http") else "https://laufen.run" + href

            if url_ev and url_ev in seen_urls:
                continue
            if url_ev:
                seen_urls.add(url_ev)

            ort      = cells[2].strip() if len(cells) > 2 else ""
            cup      = cells[3].strip() if len(cells) > 3 else ""
            strecken = cells[4].strip() if len(cells) > 4 else ""

            lv  = _detect_lv(ort + " " + titel)
            art = _detect_art(titel)

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
                "strecken":  strecken,
                "verein":    cup,
                "lv":        lv,
                "country":   "DE",
                "url":       url_ev,
                "serie":     "",
            })

    print(f"  {len(events)} future events collected")
    return sorted(events, key=lambda e: e["date_iso"])
