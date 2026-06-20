"""
build_plz_map.py – Downloads German PLZ data and writes data/plz_map.json.

Run from ~/sport-events/:
    python3 scripts/build_plz_map.py

The file is served as a static asset and fetched lazily by the browser
only when the user enters a PLZ. Fallback: live Nominatim geocoding.

Sources tried in order:
  1. GeoNames DE.zip (download.geonames.org) – ~8200 entries, most reliable
  2. downloads.suche-postleitzahl.org (CSV)
  3. raw.githubusercontent.com/zauberware (JSON)
  4. data/plz_map.json (local cache from previous successful run)
  5. data/geocache.json (event geocoding cache, ~400 PLZ entries)
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import requests

CACHE_PATH = Path(__file__).parent.parent / "data" / "plz_map.json"
HEADERS         = {"User-Agent": "bockwurst-events/2.0 stefan.griessmann@web.de"}
URL_GEONAMES    = "https://download.geonames.org/export/zip/DE.zip"
URL_CSV         = "https://downloads.suche-postleitzahl.org/v2/public/plz_einwohner.csv"
URL_JSON        = "https://raw.githubusercontent.com/zauberware/postal-codes-json-xml-csv/master/data/DE/zipcodes.de.json"


def _parse_geonames(content: bytes) -> dict:
    """Parse DE.zip from GeoNames.
    Tab-separated: country | postal_code | place_name | ... | latitude | longitude | ...
    Columns: 0=country, 1=postal_code, 9=latitude, 10=longitude
    """
    plz_map = {}
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        with zf.open("DE.txt") as f:
            for line in f:
                parts = line.decode("utf-8").strip().split("\t")
                if len(parts) < 11:
                    continue
                plz = parts[1].strip().zfill(5)
                try:
                    lat = round(float(parts[9]), 4)
                    lon = round(float(parts[10]), 4)
                except (ValueError, IndexError):
                    continue
                if len(plz) == 5 and plz not in plz_map:
                    plz_map[plz] = [lat, lon]
    return plz_map


def _parse_csv(text: str) -> dict:
    plz_map = {}
    for line in text.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 4:
            continue
        plz = parts[0].strip().strip('"').zfill(5)
        try:
            lat = round(float(parts[2].strip().strip('"')), 4)
            lon = round(float(parts[3].strip().strip('"')), 4)
        except (ValueError, IndexError):
            continue
        if len(plz) == 5 and plz not in plz_map:
            plz_map[plz] = [lat, lon]
    return plz_map


def _parse_json(data: list) -> dict:
    plz_map = {}
    for entry in data:
        plz = str(entry.get("zipcode", entry.get("plz", ""))).zfill(5)
        lat = entry.get("latitude", entry.get("lat"))
        lon = entry.get("longitude", entry.get("lng", entry.get("lon")))
        if plz and len(plz) == 5 and lat and lon and plz not in plz_map:
            plz_map[plz] = [round(float(lat), 4), round(float(lon), 4)]
    return plz_map


def fetch_plz_map() -> dict:
    # Source 1: GeoNames DE.zip – all ~8200 German PLZs
    try:
        print("[build_plz_map] Trying GeoNames DE.zip...", file=sys.stderr)
        r = requests.get(URL_GEONAMES, headers=HEADERS, timeout=60)
        r.raise_for_status()
        plz_map = _parse_geonames(r.content)
        if plz_map:
            print(f"[build_plz_map] GeoNames: {len(plz_map)} entries", file=sys.stderr)
            return plz_map
    except Exception as e:
        print(f"[build_plz_map] GeoNames failed: {e}", file=sys.stderr)

    # Source 2: CSV (suche-postleitzahl.org)
    try:
        print("[build_plz_map] Trying CSV source...", file=sys.stderr)
        r = requests.get(URL_CSV, headers=HEADERS, timeout=30)
        r.raise_for_status()
        plz_map = _parse_csv(r.text)
        if plz_map:
            print(f"[build_plz_map] CSV: {len(plz_map)} entries", file=sys.stderr)
            return plz_map
    except Exception as e:
        print(f"[build_plz_map] CSV failed: {e}", file=sys.stderr)

    # Source 3: JSON (zauberware GitHub)
    try:
        print("[build_plz_map] Trying JSON fallback...", file=sys.stderr)
        r2 = requests.get(URL_JSON, headers=HEADERS, timeout=30)
        r2.raise_for_status()
        plz_map = _parse_json(r2.json())
        if plz_map:
            print(f"[build_plz_map] JSON: {len(plz_map)} entries", file=sys.stderr)
            return plz_map
    except Exception as e:
        print(f"[build_plz_map] JSON failed: {e}", file=sys.stderr)

    # Source 4: local plz_map.json cache
    if CACHE_PATH.exists():
        print("[build_plz_map] Using local cache data/plz_map.json", file=sys.stderr)
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)

    # Source 5: geocache.json (plz:XXXXX entries from event geocoding)
    geocache_path = Path(__file__).parent.parent / "data" / "geocache.json"
    if geocache_path.exists():
        try:
            print("[build_plz_map] Trying geocache.json fallback...", file=sys.stderr)
            with open(geocache_path, encoding="utf-8") as f:
                geocache = json.load(f)
            plz_map = {}
            for key, val in geocache.items():
                if key.startswith("plz:") and isinstance(val, dict) and "lat" in val and "lon" in val:
                    if val["lat"] is None or val["lon"] is None:
                        continue  # skip null/failed geocoding results
                    plz = key[4:].zfill(5)
                    if len(plz) == 5:
                        try:
                            plz_map[plz] = [round(float(val["lat"]), 4), round(float(val["lon"]), 4)]
                        except (TypeError, ValueError):
                            continue
            if plz_map:
                print(f"[build_plz_map] geocache: {len(plz_map)} PLZ entries", file=sys.stderr)
                return plz_map
        except Exception as e:
            print(f"[build_plz_map] geocache failed: {e}", file=sys.stderr)

    print("[build_plz_map] WARNING: all sources failed, PLZ_MAP stays empty", file=sys.stderr)
    return {}


def save(plz_map: dict) -> None:
    """Write plz_map.json to data/ directory (served as static asset)."""
    if not plz_map:
        print("[build_plz_map] Empty map – skipping", file=sys.stderr)
        return

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(plz_map, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = CACHE_PATH.stat().st_size // 1024
    print(f"[build_plz_map] Wrote {len(plz_map)} entries ({size_kb} KB) → {CACHE_PATH}", file=sys.stderr)


# Keep old name as alias so existing callers don't break
inject = save


if __name__ == "__main__":
    plz_map = fetch_plz_map()
    save(plz_map)
