"""
geocoder.py – Nominatim geocoding with persistent JSON cache.
Rate-limited to 1 req/s to comply with Nominatim usage policy.
"""
import json, time, pathlib, re
import requests

CACHE_PATH = pathlib.Path(__file__).parent / "geocache.json"
HEADERS = {"User-Agent": "sport-events-chemnitz/2.0 (https://github.com/youruser/sport-events-chemnitz)"}
_cache: dict[str, list[float] | None] = {}


def _load():
    global _cache
    if CACHE_PATH.exists():
        _cache = json.loads(CACHE_PATH.read_text())

def _save():
    CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False, indent=2))


def geocode(query: str, country_codes: str = "de") -> tuple[float, float] | None:
    """
    Geocode a free-text query (city name, address, PLZ).
    Returns (lat, lon) or None.
    Results are cached to disk.
    """
    if not _cache:
        _load()
    key = f"{query}|{country_codes}"
    if key in _cache:
        result = _cache[key]
        return tuple(result) if result else None  # type: ignore

    time.sleep(1.1)  # Nominatim rate limit
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": country_codes},
            headers=HEADERS,
            timeout=10,
        )
        data = r.json()
        if data:
            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
            _cache[key] = [lat, lon]
            _save()
            return lat, lon
        _cache[key] = None
        _save()
        return None
    except Exception as e:
        print(f"  Geocoding failed for '{query}': {e}")
        return None


# City patterns for extracting a geocodable city from a German event title
_STRIP_PREFIXES = re.compile(
    r"^\d+\.\s*", re.UNICODE
)
_SPORT_WORDS = re.compile(
    r"\b(triathlon|duathlon|marathon|halbmarathon|lauf|laufen|run|rtf|ctf|gravel|"
    r"rad|tour|cup|challenge|open|backyard|ultra|trail|bergauf|firmenlauf|staffel|"
    r"stadtlauf|nachtlauf|berglauf|hasse-see|bergsee|bergtriathlon|stadtwerke|"
    r"knappenman|o-see|gladiator|paradies|schloss|muldental|rochlitzer|"
    r"mitteldeutscher|zwickauer)\b",
    re.IGNORECASE | re.UNICODE,
)

def extract_city(title: str) -> str | None:
    """
    Heuristic: extract a city name from a German event title.
    '43. Schlosstriathlon Moritzburg'  → 'Moritzburg'
    'ZWICKAU TRIATHLON'                → 'Zwickau'
    '43. Leipziger Triathlon'          → 'Leipzig'
    """
    t = _STRIP_PREFIXES.sub("", title).strip()
    t = _SPORT_WORDS.sub("", t).strip()
    # Remove VSB, DSC 1898, etc. club-like tokens
    t = re.sub(r"\b[A-Z]{2,4}\s+\d{4}\b", "", t).strip()
    # Adjective → city: Jenaer→Jena, Dresdner→Dresden, Erfurter→Erfurt
    t = re.sub(r"(?<=[a-z])(er|ner)(\s|$)", r"\2", t, flags=re.IGNORECASE)
    words = [w.strip(".,;-–()") for w in t.split() if len(w.strip(".,;-–()")) > 2]
    # Prefer Title-cased words (likely proper nouns)
    titled = [w for w in words if w[0].isupper()]
    if titled:
        # Last title-cased word is often the city
        return titled[-1]
    return words[-1] if words else None


def geocode_event(title: str, country: str = "DE") -> tuple[float, float] | None:
    """Try to geocode an event by extracting its city from the title."""
    cc = country.lower()
    city = extract_city(title)
    if not city:
        return None
    # Try "CityName, Country"
    result = geocode(f"{city}, {country}", country_codes=cc)
    if result:
        return result
    # Try just the city
    return geocode(city, country_codes=cc)
