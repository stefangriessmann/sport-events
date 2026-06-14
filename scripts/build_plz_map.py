"""
build_plz_map.py – Downloads German PLZ data and injects const PLZ_MAP into index.html.

Run from ~/sport-events/:
    python3 scripts/build_plz_map.py

Replaces the line:  const PLZ_MAP = {};
with the full minified map (~120 KB).

Sources tried in order:
  1. downloads.suche-postleitzahl.org (CSV)
  2. raw.githubusercontent.com/zauberware (JSON)
  3. data/plz_map.json (local cache from previous run)
  4. data/geocache.json (event geocoding cache, ~289 PLZ entries)
  5. keep existing PLZ_MAP in index.html (no filter, graceful degradation)
"""
import json
import re
import sys
from pathlib import Path

import requests

INDEX_HTML   = Path(__file__).parent.parent / "index.html"
CACHE_PATH   = Path(__file__).parent.parent / "data" / "plz_map.json"
HEADERS      = {"User-Agent": "bockwurst-events/2.0 stefan.griessmann@web.de"}
URL_CSV      = "https://downloads.suche-postleitzahl.org/v2/public/plz_einwohner.csv"
URL_JSON     = "https://raw.githubusercontent.com/zauberware/postal-codes-json-xml-csv/master/data/DE/zipcodes.de.json"


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
    # Source 1: CSV
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

    # Source 2: JSON fallback
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

    # Source 3: local cache
    if CACHE_PATH.exists():
        print("[build_plz_map] Using local cache data/plz_map.json", file=sys.stderr)
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)

    # Source 4: geocache.json (event geocoding cache with plz:XXXXX entries)
    geocache_path = Path(__file__).parent.parent / "data" / "geocache.json"
    if geocache_path.exists():
        try:
            print("[build_plz_map] Trying geocache.json fallback...", file=sys.stderr)
            with open(geocache_path, encoding="utf-8") as f:
                geocache = json.load(f)
            plz_map = {}
            for key, val in geocache.items():
                if key.startswith("plz:") and isinstance(val, dict) and "lat" in val and "lon" in val:
                    plz = key[4:].zfill(5)
                    if len(plz) == 5:
                        plz_map[plz] = [round(float(val["lat"]), 4), round(float(val["lon"]), 4)]
            if plz_map:
                print(f"[build_plz_map] geocache: {len(plz_map)} PLZ entries", file=sys.stderr)
                return plz_map
        except Exception as e:
            print(f"[build_plz_map] geocache failed: {e}", file=sys.stderr)

    print("[build_plz_map] WARNING: all sources failed, PLZ_MAP stays empty", file=sys.stderr)
    return {}


def inject(plz_map: dict) -> None:
    if not plz_map:
        print("[build_plz_map] Empty map – skipping injection", file=sys.stderr)
        return

    # Save to local cache for future offline runs
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(plz_map, f, ensure_ascii=False)

    html = INDEX_HTML.read_text(encoding="utf-8")
    inner = ",".join(f'"{k}":{json.dumps(v)}' for k, v in sorted(plz_map.items()))
    new_line = f"const PLZ_MAP = {{{inner}}};"
    html = re.sub(r"const PLZ_MAP = \{.*?\};", new_line, html, count=1)
    INDEX_HTML.write_text(html, encoding="utf-8")
    size_kb = len(new_line.encode()) // 1024
    print(f"[build_plz_map] Injected {len(plz_map)} entries ({size_kb} KB) into index.html", file=sys.stderr)


if __name__ == "__main__":
    plz_map = fetch_plz_map()
    inject(plz_map)
