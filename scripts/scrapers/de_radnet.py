"""
de_radnet.py – Scraper for breitensport.rad-net.de (BDR Breitensportkalender).

Fetches ALL cycling events across Germany (no distance pre-filter).
For each event, the detail page is fetched once (with cache) to extract Startort PLZ + city.
Geocoding via _geocode.geocode_plz(plz) or geocode(ort) as fallback.
Cache: data/startort_cache.json (keyed by event URL).
"""
from __future__ import annotations  # Python 3.9 compat
import re
import time
from datetime import date, datetime

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from _geocode import geocode_plz, geocode

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

# LV display-code → (lat, lon) of state centroid / capital, used as fallback
# when the detail page is unavailable (rate-limit).
LV_COORD_FALLBACK: dict[str, tuple[float, float]] = {
    "BAY": (48.79, 11.50),   # Bayern
    "NRW": (51.43, 7.66),    # Nordrhein-Westfalen
    "BRA": (52.52, 13.40),   # Brandenburg
    "SAC": (51.05, 13.74),   # Sachsen
    "SA":  (51.50, 11.97),   # Sachsen-Anhalt
    "THÜ": (50.98, 11.03),   # Thüringen
    "NDS": (52.37, 9.74),    # Niedersachsen
    "HES": (50.11, 8.68),    # Hessen
    "SCH": (54.32, 10.12),   # Schleswig-Holstein
    "RLP": (50.00, 7.27),    # Rheinland-Pfalz
    "BER": (52.52, 13.40),   # Berlin
    "BAD": (48.99, 8.41),    # Baden
    "WÜR": (49.79, 9.95),    # Württemberg
    "SAA": (49.24, 6.99),    # Saarland
    "HAM": (53.58, 10.02),   # Hamburg
    "BRE": (53.08, 8.80),    # Bremen
    "MEV": (53.64, 11.40),   # Mecklenburg-Vorpommern
}

LV_STATE_NAMES: dict[str, str] = {
    "BAY": "Bayern", "NRW": "Nordrhein-Westfalen", "BRA": "Brandenburg",
    "SAC": "Sachsen", "SA": "Sachsen-Anhalt", "THÜ": "Thüringen",
    "NDS": "Niedersachsen", "HES": "Hessen", "SCH": "Schleswig-Holstein",
    "RLP": "Rheinland-Pfalz", "BER": "Berlin", "BAD": "Baden", "WÜR": "Württemberg",
    "SAA": "Saarland", "HAM": "Hamburg", "BRE": "Bremen", "MEV": "Mecklenburg-Vorpommern",
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

# ── Startort-Cache ─────────────────────────────────────────────────────────
_STARTORT_CACHE_PATH = Path("data") / "startort_cache.json"
_startort_cache: dict | None = None


def _load_startort_cache() -> dict:
    global _startort_cache
    if _startort_cache is None:
        if _STARTORT_CACHE_PATH.exists():
            with open(_STARTORT_CACHE_PATH, encoding="utf-8") as f:
                _startort_cache = json.load(f)
        else:
            _startort_cache = {}
    return _startort_cache


def _save_startort_cache() -> None:
    _STARTORT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_STARTORT_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(_startort_cache, f, ensure_ascii=False, indent=2)


def _fetch_startort(detail_url: str) -> dict[str, str]:
    """
    Fetch rad-net detail page and extract Startort (PLZ + city).
    Returns {"ort": str, "plz": str} – empty strings if not found.
    Caches results in startort_cache.json keyed by URL.
    """
    cache = _load_startort_cache()
    if detail_url in cache:
        return cache[detail_url]

    result = {"ort": "", "plz": ""}
    try:
        time.sleep(1.5)   # rate-limit: increased from 0.5s to reduce blocking
        r = requests.get(detail_url, headers=HEADERS, timeout=15)
        r.raise_for_status()

        # Detect rad-net rate-limit page ("Bitte warten" / "automatisierter Zugriffe").
        # Do NOT cache – the next run will retry.
        if "automatisierter" in r.text or "bitte warten" in r.text.lower():
            print(f"  [radnet] Rate-limited: {detail_url[-50:]!r} – skipped (retry next run)")
            return result  # not cached

        soup = BeautifulSoup(r.text, "lxml")

        # <tr><th>Startort</th><td>Straße<br>PLZ Stadt<br>Geschäftsstelle…</td></tr>
        # Use get_text() to handle nested elements robustly
        th = next(
            (t for t in soup.find_all("th") if re.search(r"Startort", t.get_text(), re.I)),
            None,
        )
        if th:
            td = th.find_next_sibling("td")
            if td:
                text = td.get_text(" ", strip=True)
                # Extract 5-digit PLZ + city: "21255 Tostedt/Todtglüsingen"
                m = re.search(r"\b(\d{5})\s+(.+?)(?:\s+Geschäftsstelle|\s+Route\b|$)", text)
                if m:
                    result["plz"] = m.group(1)
                    result["ort"] = m.group(2).strip()
                else:
                    # Fallback: just the PLZ
                    plz_m = re.search(r"\b(\d{5})\b", text)
                    if plz_m:
                        result["plz"] = plz_m.group(1)
    except Exception as e:
        print(f"  [radnet] Detail fetch error for {detail_url}: {e}")

    cache[detail_url] = result
    _save_startort_cache()
    return result


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
        "km":        None,
        "lat":       None,   # filled in fetch() after detail-page lookup
        "lon":       None,
        "titel":     titel,
        "ort":       "",     # filled in fetch() after detail-page lookup
        "plz":       "",     # filled in fetch() after detail-page lookup
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

    # Enrich with Startort from detail pages (rate-limited, cached in startort_cache.json)
    print(f"  Enriching {len(unique)} events with Startort (cache hits skip HTTP)...")
    cache = _load_startort_cache()
    new_fetches = 0
    for i, e in enumerate(unique):
        was_cached = e["url"] in cache
        startort = _fetch_startort(e["url"])   # sleeps 0.5s only on cache miss
        e["ort"] = startort["ort"]
        e["plz"] = startort["plz"]
        if e["plz"]:
            coords = geocode_plz(e["plz"])
        elif e["ort"]:
            coords = geocode(e["ort"])
        else:
            coords = {"lat": None, "lon": None}
        e["lat"] = coords["lat"]
        e["lon"] = coords["lon"]
        # Fallback: when detail page was rate-limited or PLZ unknown,
        # use LV state centroid so every event has approximate coordinates.
        if e["lat"] is None and e["lv"] in LV_COORD_FALLBACK:
            e["lat"], e["lon"] = LV_COORD_FALLBACK[e["lv"]]
        if not e["ort"] and e["lv"] in LV_STATE_NAMES:
            e["ort"] = LV_STATE_NAMES[e["lv"]]
        if not was_cached:
            new_fetches += 1
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(unique)} enriched (new fetches so far: {new_fetches})...")

    print(f"  {new_fetches} new detail pages fetched, {len(unique) - new_fetches} from cache")
    print(f"  {len(unique)} unique future events collected (all Germany)")
    return sorted(unique, key=lambda e: e["date_iso"])
