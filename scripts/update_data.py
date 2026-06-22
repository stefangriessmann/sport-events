#!/usr/bin/env python3
"""
update_data.py – Writes event data as external JSON files instead of
                 injecting into index.html.

Usage:
    python scripts/update_data.py [--year YYYY] [--dry-run]

Outputs:
    data/radsport-de.json   – Radsport events (rad-net + radsport-events.de)
    data/triathlon-de.json  – Triathlon events (triathlondeutschland.de)
    data/laufen-de.json     – Laufen events (laufen.run + mammutmarsch)
    data/swim-de.json       – Schwimmen events (manually curated)
    data/meta.json          – {"stand": "DD.MM.YYYY", "counts": {...}}

Adding a new source:
    1. Create  scripts/scrapers/<cc>_<source>.py  with  fetch(year) -> list[dict].
    2. Add it to SOURCES below.  Done.
"""

import sys
import json
import argparse
import pathlib
from datetime import date

# ── Source registry ────────────────────────────────────────────────────────────
# Each entry: (module_path_or_list, output_filename, sport_key)
# module_path may be a string or list – multiple scrapers are merged + deduped.
SOURCES = [
    (["scrapers.de_radnet", "scrapers.de_radsport_events"], "radsport-de.json", "rad"),
    ("scrapers.de_triathlonde",                             "triathlon-de.json", "tri"),
    (["scrapers.de_laufen", "scrapers.de_mammutmarsch"],    "laufen-de.json",   "lauf"),
    # swim-de.json is manually curated – not auto-updated by scrapers
]

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = pathlib.Path(__file__).resolve().parent
DATA_DIR      = SCRIPT_DIR.parent / "data"
APPROVED_PATH = DATA_DIR / "approved_events.json"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "scrapers"))  # _geocode.py lives here


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_existing(filename: str) -> list:
    """Load existing JSON file, return empty list if missing or invalid."""
    path = DATA_DIR / filename
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARNING: Could not read {filename}: {e}")
        return []


def dedup(events: list) -> list:
    seen_urls: set = set()
    seen_titledate: set = set()
    result = []
    for ev in events:
        key_url = ev.get("url", "")
        key_td  = (ev.get("titel", ""), ev.get("date_iso", ""))
        if key_url and key_url in seen_urls:
            continue
        if key_td in seen_titledate:
            continue
        if key_url:
            seen_urls.add(key_url)
        seen_titledate.add(key_td)
        result.append(ev)
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year",      type=int, default=date.today().year)
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--no-scrape", action="store_true",
                        help="Skip scrapers – only inject approved_events.json into existing data files.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    today_fmt = date.today().strftime("%d.%m.%Y")
    today_iso = date.today().isoformat()

    import importlib

    # ── Phase 1: Scraper-Daten sammeln ─────────────────────────────────────────
    # scraped_data: filename → list[dict]
    scraped_data: dict = {}

    if args.no_scrape:
        print("\n── --no-scrape: Scraper übersprungen, nur approved_events.json wird eingemischt ──")
        for _, filename, _ in SOURCES:
            # Bestehende Daten als Basis laden, damit Phase 2 die Freigaben anhängt
            # und der MIN_EVENTS-Guard in Phase 3 nicht blockt.
            scraped_data[filename] = load_existing(filename)
    else:
        for module_path, filename, sport_key in SOURCES:
            modules = [module_path] if isinstance(module_path, str) else module_path
            print(f"\n── {', '.join(modules)} → {filename} ──────────────────")

            all_events = []
            for mp in modules:
                try:
                    mod   = importlib.import_module(mp)
                    batch = mod.fetch(args.year)
                    print(f"  {mp}: {len(batch)} events")
                    all_events.extend(batch)
                except Exception as e:
                    print(f"  SCRAPER ERROR ({mp}): {e}")

            events = dedup(sorted(all_events, key=lambda e: e.get("date_iso", "")))
            scraped_data[filename] = events

    # ── Phase 2: Manuell freigegebene Events einmischen ────────────────────────
    if APPROVED_PATH.exists():
        try:
            approved_raw = json.loads(APPROVED_PATH.read_text(encoding="utf-8"))
            added = 0

            # Map sport_key → filename
            sport_to_file = {sk: fn for (_, fn, sk) in SOURCES}
            # Also support direct _snapshot key
            snap_to_file = {
                "SNAPSHOT":      "radsport-de.json",
                "TRI_SNAPSHOT":  "triathlon-de.json",
                "LAUF_SNAPSHOT": "laufen-de.json",
                "SWIM_SNAPSHOT": "swim-de.json",
            }

            for ev in approved_raw:
                # Determine target file
                snap    = ev.get("_snapshot", "SNAPSHOT")
                sport   = ev.get("_sport", "")
                filename = sport_to_file.get(sport) or snap_to_file.get(snap, "radsport-de.json")

                ev_iso = ev.get("date_iso", "")
                if ev_iso < today_iso:
                    continue  # skip past events

                ev_clean = {k: v for k, v in ev.items() if not k.startswith("_")}

                events_list = scraped_data.setdefault(filename, [])
                url = ev_clean.get("url", "")
                td  = (ev_clean.get("titel", ""), ev_clean.get("date_iso", ""))
                duplicate = (url and any(e.get("url") == url for e in events_list)) or \
                            any((e.get("titel"), e.get("date_iso")) == td for e in events_list)
                if not duplicate:
                    # Geocode if ort/plz is set but lat/lon are missing
                    if not ev_clean.get("lat") and (ev_clean.get("plz") or ev_clean.get("ort")):
                        try:
                            from _geocode import geocode_plz as _gp, geocode as _gc
                            _coords = _gp(ev_clean["plz"]) if ev_clean.get("plz") else {"lat": None, "lon": None}
                            if _coords["lat"] is None and ev_clean.get("ort"):
                                _coords = _gc(ev_clean["ort"])
                            if _coords["lat"] is not None:
                                ev_clean["lat"] = _coords["lat"]
                                ev_clean["lon"] = _coords["lon"]
                        except Exception as _ge:
                            print(f"  [geocode approved] {ev_clean.get('titel','?')}: {_ge}")
                    events_list.append(ev_clean)
                    added += 1

            if added:
                print(f"\n── Manuell freigegebene Events eingemischt: {added} ──")
                # Re-sort after adding
                for fn in scraped_data:
                    scraped_data[fn].sort(key=lambda e: e.get("date_iso", ""))
        except Exception as e:
            print(f"\n  WARNING: approved_events.json konnte nicht geladen werden: {e}")

    # ── Phase 3: Schwellenwert-Schutz & Ausgabe ────────────────────────────────
    MIN_EVENTS = {
        "radsport-de.json":  50,
        "triathlon-de.json": 20,
        "laufen-de.json":    20,
        "swim-de.json":       0,  # manually curated, no minimum
    }

    counts = {}
    changed_files = []

    for _, filename, sport_key in SOURCES:
        events = scraped_data.get(filename, [])
        min_req = MIN_EVENTS.get(filename, 10)

        existing = load_existing(filename)

        if len(events) < min_req:
            print(f"\n  {filename}: Nur {len(events)} Events (min {min_req}) – bestehende Daten bleiben.")
            counts[sport_key] = len(existing)
            continue

        # 70% threshold guard against scraper timeouts
        if existing and len(existing) >= min_req and len(events) < 0.70 * len(existing):
            print(f"\n  ⚠️  {filename}: Neuer Count {len(events)} < 70% des bestehenden {len(existing)} → NICHT überschrieben.")
            counts[sport_key] = len(existing)
            continue

        counts[sport_key] = len(events)
        print(f"\n  {filename}: {len(events)} Events")

        if not args.dry_run:
            (DATA_DIR / filename).write_text(
                json.dumps(events, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8"
            )
            changed_files.append(filename)

    # ── Phase 4: swim-de.json – vergangene Events entfernen ───────────────────
    swim_path = DATA_DIR / "swim-de.json"
    swim_events = load_existing("swim-de.json")
    swim_future = [e for e in swim_events if e.get("date_iso", "9999") >= today_iso]
    if len(swim_future) < len(swim_events):
        purged = len(swim_events) - len(swim_future)
        print(f"\n  swim-de.json: {purged} vergangene(s) Event(s) entfernt.")
        counts["swim"] = len(swim_future)
        if not args.dry_run:
            swim_path.write_text(
                json.dumps(swim_future, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8"
            )
            changed_files.append("swim-de.json")
    else:
        counts.setdefault("swim", len(swim_events))

    # ── Phase 5: meta.json schreiben ──────────────────────────────────────────
    meta = {
        "stand": today_fmt,
        "stand_iso": today_iso,
        "counts": counts,
    }

    if not args.dry_run:
        (DATA_DIR / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        changed_files.append("meta.json")

    if args.dry_run:
        print(f"\n[dry-run] Würde schreiben: {', '.join(changed_files or ['(nichts)'])}")
        print(f"[dry-run] meta: {meta}")
    else:
        print(f"\nGeschrieben: {', '.join(changed_files) if changed_files else '(nichts geändert)'}")
        print(f"Stand: {today_fmt}")


if __name__ == "__main__":
    main()
