#!/usr/bin/env python3
"""
update_snapshots.py – Monthly event snapshot updater.

Usage:
    python scripts/update_snapshots.py [--year YYYY] [--dry-run]

Reads sport-events-chemnitz.html, replaces SNAPSHOT / TRI_SNAPSHOT /
LAUF_SNAPSHOT / SWIM_SNAPSHOT with fresh data from all active scrapers,
and writes the file back.

Adding a new country/source:
    1. Create  scripts/scrapers/<cc>_<source>.py  with a  fetch(year) -> list[dict]  function.
    2. Add it to SOURCES below with the matching JS variable name and sport key.
    3. Done – the next monthly run picks it up automatically.
"""

import sys
import re
import json
import argparse
import pathlib
from datetime import date

# ── Source registry ────────────────────────────────────────────────────────────
# Each entry: (module_path, js_var_name, sport_key)
# sport_key matches the setSport() keys in the HTML ('rad', 'tri', 'lauf', 'swim')
# Add new countries here:
#   ("scrapers.aut_triathlon", "AUT_TRI_SNAPSHOT", "tri"),
#   ("scrapers.che_radnet",    "CHE_SNAPSHOT",     "rad"),
SOURCES = [
    ("scrapers.de_radnet", "SNAPSHOT",      "rad"),
    ("scrapers.de_dtu",    "TRI_SNAPSHOT",  "tri"),
    ("scrapers.de_laufen", "LAUF_SNAPSHOT", "lauf"),
    # SWIM_SNAPSHOT is manually curated – not auto-updated
]

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).parent
HTML_PATH  = SCRIPT_DIR.parent / "sport-events-chemnitz.html"
sys.path.insert(0, str(SCRIPT_DIR))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _js_value(v) -> str:
    """Render a Python value as a JS literal."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    # Escape single quotes in strings
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def events_to_js(events: list[dict]) -> str:
    """Render a list of event dicts as a JS array literal (multi-line)."""
    lines = ["["]
    for ev in events:
        fields = ", ".join(f'{k}:{_js_value(v)}' for k, v in ev.items())
        lines.append(f"  {{{fields}}},")
    lines.append("]")
    return "\n".join(lines)


def update_snapshot(html: str, var_name: str, events: list[dict]) -> str:
    """Replace  const VAR_NAME = [...];  in the HTML with fresh data."""
    js = events_to_js(events)
    pattern = rf'(const {re.escape(var_name)}\s*=\s*)\[[\s\S]*?\];'
    replacement = rf'\g<1>{js};'
    new_html, n = re.subn(pattern, replacement, html)
    if n == 0:
        print(f"  WARNING: '{var_name}' not found in HTML – skipped.")
    else:
        print(f"  Updated {var_name} with {len(events)} events.")
    return new_html


def update_stand_date(html: str, sport_key: str, new_date: str) -> str:
    """Update the Stand date inside the subs object in setSport()."""
    # Pattern: "rad":"400 km ... · Stand: DD.MM.YYYY"
    pattern = rf'("{sport_key}":\s*"[^"]*?Stand:\s*)[\d.]+(\s*")'
    return re.sub(pattern, rf'\g<1>{new_date}\g<2>', html)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year",    type=int, default=date.today().year)
    parser.add_argument("--dry-run", action="store_true", help="Print changes but don't write")
    args = parser.parse_args()

    if not HTML_PATH.exists():
        sys.exit(f"ERROR: {HTML_PATH} not found. Run from the repo root.")

    html = HTML_PATH.read_text(encoding="utf-8")
    today_fmt = date.today().strftime("%d.%m.%Y")

    changed = False
    for module_path, js_var, sport_key in SOURCES:
        print(f"\n── {module_path} → {js_var} ──────────────────")
        try:
            import importlib
            mod = importlib.import_module(module_path)
            events = mod.fetch(args.year)
        except Exception as e:
            print(f"  SCRAPER ERROR: {e}")
            print("  Skipping this source (keeping existing snapshot).")
            continue

        if not events:
            print("  No events returned – skipping to preserve existing data.")
            continue

        html = update_snapshot(html, js_var, events)
        html = update_stand_date(html, sport_key, today_fmt)
        changed = True

    if not changed:
        print("\nNo snapshots updated.")
        return

    if args.dry_run:
        print(f"\n[dry-run] Would write {len(html)} chars to {HTML_PATH}")
        return

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"\nWrote updated HTML to {HTML_PATH}")
    print(f"Stand: {today_fmt}")


if __name__ == "__main__":
    main()
