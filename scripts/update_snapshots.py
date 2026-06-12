#!/usr/bin/env python3
"""
update_snapshots.py – Monthly event snapshot updater.

Usage:
    python scripts/update_snapshots.py [--year YYYY] [--dry-run]

Reads index.html, replaces SNAPSHOT / TRI_SNAPSHOT / LAUF_SNAPSHOT /
SWIM_SNAPSHOT with fresh scraper data + any manually approved events from
data/approved_events.json, and writes the file back.

Adding a new source:
    1. Create  scripts/scrapers/<cc>_<source>.py  with  fetch(year) -> list[dict].
    2. Add it to SOURCES below.  Done.
"""

import sys
import re
import json
import argparse
import pathlib
from datetime import date

# ── Source registry ────────────────────────────────────────────────────────────
# Each entry: (module_path_or_list, js_var_name, sport_key)
# module_path may be a string or a list of strings – multiple scrapers are
# merged and deduplicated (by url, then title+date_iso) into one JS variable.
SOURCES = [
    (["scrapers.de_radnet", "scrapers.de_radsport_events"], "SNAPSHOT",      "rad"),
    ("scrapers.de_triathlonde",                             "TRI_SNAPSHOT",  "tri"),
    ("scrapers.de_laufen",                                  "LAUF_SNAPSHOT", "lauf"),
    # SWIM_SNAPSHOT is manually curated – not auto-updated
]

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR     = pathlib.Path(__file__).parent
HTML_PATH      = SCRIPT_DIR.parent / "index.html"
APPROVED_PATH  = SCRIPT_DIR.parent / "data" / "approved_events.json"
sys.path.insert(0, str(SCRIPT_DIR))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _js_value(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def events_to_js(events: list) -> str:
    lines = ["["]
    for ev in events:
        fields = ", ".join(f'{k}:{_js_value(v)}' for k, v in ev.items())
        lines.append(f"  {{{fields}}},")
    lines.append("]")
    return "\n".join(lines)


def update_snapshot(html: str, var_name: str, events: list) -> str:
    js = events_to_js(events)
    pattern = rf'(const {re.escape(var_name)}\s*=\s*)\[[\s\S]*?\];'
    new_html, n = re.subn(pattern, rf'\g<1>{js};', html)
    if n == 0:
        print(f"  WARNING: '{var_name}' not found in HTML – skipped.")
    else:
        print(f"  Updated {var_name} with {len(events)} events.")
    return new_html


def update_stand_date(html: str, sport_key: str, new_date: str) -> str:
    pattern = rf'("{sport_key}":\s*"[^"]*?Stand:\s*)[\d.]+(\s*")'
    return re.sub(pattern, rf'\g<1>{new_date}\g<2>', html)


def update_static_badge_date(html: str, new_date: str) -> str:
    pattern = r'(<span class="snap-badge" id="snap-date">Stand )[^<]+(</span>)'
    result, n = re.subn(pattern, rf'\g<1>{new_date}\g<2>', html)
    if n:
        print(f"  Updated static snap-badge to Stand {new_date}")
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year",    type=int, default=date.today().year)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not HTML_PATH.exists():
        sys.exit(f"ERROR: {HTML_PATH} not found.")

    html      = HTML_PATH.read_text(encoding="utf-8")
    today_fmt = date.today().strftime("%d.%m.%Y")
    today_iso = date.today().isoformat()

    import importlib

    # ── Phase 1: Scraper-Daten sammeln ─────────────────────────────────────────
    # snapshot_data: js_var → (events_list, sport_key)
    snapshot_data: dict = {}

    for module_path, js_var, sport_key in SOURCES:
        modules = [module_path] if isinstance(module_path, str) else module_path
        print(f"\n── {', '.join(modules)} → {js_var} ──────────────────")

        all_events = []
        seen_urls: set = set()
        seen_titledate: set = set()

        for mp in modules:
            try:
                mod   = importlib.import_module(mp)
                batch = mod.fetch(args.year)
                print(f"  {mp}: {len(batch)} events")
            except Exception as e:
                print(f"  SCRAPER ERROR ({mp}): {e}")
                batch = []

            for ev in batch:
                key_url = ev.get("url", "")
                key_td  = (ev.get("titel", ""), ev.get("date_iso", ""))
                if key_url and key_url in seen_urls:
                    continue
                if key_td in seen_titledate:
                    continue
                if key_url:
                    seen_urls.add(key_url)
                seen_titledate.add(key_td)
                all_events.append(ev)

        snapshot_data[js_var] = (
            sorted(all_events, key=lambda e: e.get("date_iso", "")),
            sport_key,
        )

    # ── Phase 2: Manuell freigegebene Events einmischen ────────────────────────
    if APPROVED_PATH.exists():
        try:
            approved_raw = json.loads(APPROVED_PATH.read_text(encoding="utf-8"))
            added = 0
            for ev in approved_raw:
                snap    = ev.get("_snapshot", "SNAPSHOT")
                ev_iso  = ev.get("date_iso", "")
                if ev_iso < today_iso:
                    continue  # vergangene Events überspringen
                ev_clean = {k: v for k, v in ev.items() if not k.startswith("_")}

                if snap not in snapshot_data:
                    snapshot_data[snap] = ([], "")
                events_list, sk = snapshot_data[snap]

                url = ev_clean.get("url", "")
                td  = (ev_clean.get("titel", ""), ev_clean.get("date_iso", ""))
                duplicate = (url and any(e.get("url") == url for e in events_list)) or \
                            any((e.get("titel"), e.get("date_iso")) == td for e in events_list)
                if not duplicate:
                    events_list.append(ev_clean)
                    added += 1

            if added:
                print(f"\n── Manuell freigegebene Events eingemischt: {added} ──")
                for js_var, (evs, sk) in snapshot_data.items():
                    evs.sort(key=lambda e: e.get("date_iso", ""))
        except Exception as e:
            print(f"\n  WARNING: approved_events.json konnte nicht geladen werden: {e}")

    # ── Phase 3: HTML schreiben ─────────────────────────────────────────────────
    changed = False
    for js_var, (events, sport_key) in snapshot_data.items():
        if not events:
            print(f"\n  {js_var}: Keine Events – bestehende Daten bleiben.")
            continue
        MIN_EVENTS = {"SNAPSHOT": 50, "TRI_SNAPSHOT": 20, "LAUF_SNAPSHOT": 20}
        min_required = MIN_EVENTS.get(js_var, 10)
        if len(events) < min_required:
            print(f"\n  {js_var}: Nur {len(events)} Events (min {min_required}) – bestehende Daten bleiben.")
            continue
        print(f"\n  {js_var}: {len(events)} Events")
        html = update_snapshot(html, js_var, events)
        if sport_key:
            html = update_stand_date(html, sport_key, today_fmt)
        changed = True

    if not changed:
        print("\nKeine Snapshots aktualisiert.")
        return

    if args.dry_run:
        print(f"\n[dry-run] Würde {len(html)} Zeichen nach {HTML_PATH} schreiben.")
        return

    html = update_static_badge_date(html, today_fmt)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"\nHTML gespeichert: {HTML_PATH}")
    print(f"Stand: {today_fmt}")


if __name__ == "__main__":
    main()
