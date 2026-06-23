#!/usr/bin/env python3
"""Probe-Builder: data/radsport-gb.json aus Cycling UK + Sportive.com mit Fuzzy-Dedup + Zusammenfassung."""
import sys, json, pathlib
from datetime import date
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "scrapers"))

from scrapers import gb_cyclinguk, gb_sportive   # noqa: E402
import update_data                               # noqa: E402


def main():
    y = date.today().year
    a = gb_cyclinguk.fetch(y)
    b = gb_sportive.fetch(y)
    print(f"\nCycling UK: {len(a)}  |  Sportive.com: {len(b)}  |  roh: {len(a)+len(b)}", file=sys.stderr)
    evs = update_data.dedup_fuzzy(sorted(a + b, key=lambda e: e.get("date_iso", "")))
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "radsport-gb.json").write_text(
        json.dumps(evs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n=== radsport-gb.json (Cycling UK + Sportive.com, dedupliziert) ===")
    print(f"Events: {len(evs)}  (roh {len(a)+len(b)}, also {len(a)+len(b)-len(evs)} Dubletten entfernt)")
    print(f"  nach art: {dict(Counter(e['art'] for e in evs))}")
    print(f"  geocodiert: {sum(1 for e in evs if e['lat'] is not None)}  |  mit Postcode: {sum(1 for e in evs if e['plz'])}")
    print("\nBeispiele:")
    for e in evs[:10]:
        print(f"  {e['date_iso']}  {e['art']:11s} {e['titel'][:38]:38s} | {e['ort'][:26]:26s} | {e['plz']:8s}")


if __name__ == "__main__":
    main()
