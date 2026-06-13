"""
_geocode.py – Shared Nominatim geocoder with disk cache.

Usage:
    from _geocode import geocode
    coords = geocode("Chemnitz")  # {"lat": 50.832, "lon": 12.923}

Rate limit: 1 req/s (Nominatim ToS).
Cache: ~/Claude/data/geocache.json (key = normalised city name).
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path

import requests

CACHE_PATH = Path("data") / "geocache.json"
HEADERS    = {"User-Agent": "bockwurst-events/2.0 stefan.griessmann@web.de"}
API_URL    = "https://nominatim.openstreetmap.org/search"

_cache: dict[str, dict] | None = None
_last_request = 0.0


def _load_cache() -> dict[str, dict]:
    global _cache
    if _cache is None:
        if CACHE_PATH.exists():
            with open(CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        else:
            _cache = {}
    return _cache


def _save_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)


def _normalise(ort: str) -> str:
    return re.sub(r"\s+", " ", ort.strip().lower())


def _nominatim(params: dict) -> dict[str, float | None]:
    """Single Nominatim request with rate-limit."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    try:
        r = requests.get(API_URL, params={**params, "format": "json", "limit": 1},
                         headers=HEADERS, timeout=10)
        _last_request = time.time()
        r.raise_for_status()
        data = r.json()
        if data:
            return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    except Exception as e:
        print(f"  [geocode] Error ({params}): {e}")
        _last_request = time.time()
    return {"lat": None, "lon": None}


def _first_segment(ort: str) -> str:
    """Extract first recognisable place from a compound string like 'Stiege/Alexisbad/Meisdorf'."""
    import re as _re
    # Split on / or " - " or " ("
    m = _re.split(r"/| - | \(", ort.strip())
    first = m[0].strip() if m else ort.strip()
    return first if first != ort.strip() else ""


def geocode(ort: str) -> dict[str, float | None]:
    """Return {lat, lon} for a German city name via Nominatim.

    Falls back to the first segment of compound names (e.g. 'Stiege/Alexisbad').
    Null results are NOT cached so the next run can retry with improved logic.
    """
    if not ort or not ort.strip():
        return {"lat": None, "lon": None}
    cache = _load_cache()
    key   = _normalise(ort)
    if key in cache and cache[key]["lat"] is not None:
        return cache[key]
    # Try full string
    result = _nominatim({"q": f"{ort},Deutschland"})
    if result["lat"] is None:
        # Try first segment for compound names
        first = _first_segment(ort)
        if first:
            result = _nominatim({"q": f"{first},Deutschland"})
    # Only cache successful results – null results are retried next run
    if result["lat"] is not None:
        cache[key] = result
        _save_cache()
    return result


def geocode_plz(plz: str) -> dict[str, float | None]:
    """Return {lat, lon} for a German PLZ via Nominatim postalcode lookup (more accurate than city name)."""
    if not plz or len(plz) != 5 or not plz.isdigit():
        return {"lat": None, "lon": None}
    cache = _load_cache()
    key   = f"plz:{plz}"
    if key not in cache:
        cache[key] = _nominatim({"postalcode": plz, "country": "DE"})
        _save_cache()
    return cache[key]


if __name__ == "__main__":
    for city in ["Chemnitz", "Hamburg", "Unbekannter Ort XYZ"]:
        print(f"{city}: {geocode(city)}")
    for plz in ["09111", "20095", "99999"]:
        print(f"PLZ {plz}: {geocode_plz(plz)}")
