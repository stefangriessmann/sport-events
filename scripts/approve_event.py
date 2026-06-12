#!/usr/bin/env python3
"""
approve_event.py – Parse a GitHub Issue body and append the event to
data/approved_events.json.

Called by the GitHub Action:
    python3 scripts/approve_event.py /tmp/issue_body.txt <issue_number>

Issue body must contain **Key:** Value pairs, e.g.:
    **Sport:** Radsport
    **Typ:** RTF
    **Name:** Muster-RTF 2026
    **Datum:** 2026-07-15
    **Datum-Ende:** 2026-07-16
    **Ort:** Chemnitz, Sachsen
    **Link:** https://example.com
"""
from __future__ import annotations
import sys
import json
import re
import pathlib
from datetime import date

SCRIPT_DIR = pathlib.Path(__file__).parent
DATA_FILE  = SCRIPT_DIR.parent / "data" / "approved_events.json"

# Sport-Label (lowercase) → JS-Snapshot-Variable
SPORT_SNAPSHOT: dict[str, str] = {
    "radsport":  "SNAPSHOT",
    "rad":       "SNAPSHOT",
    "schwimmen": "SWIM_SNAPSHOT",
    "swim":      "SWIM_SNAPSHOT",
    "triathlon": "TRI_SNAPSHOT",
    "tri":       "TRI_SNAPSHOT",
    "laufen":    "LAUF_SNAPSHOT",
    "lauf":      "LAUF_SNAPSHOT",
}

WDAY_DE = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]


def parse_body(body: str) -> dict[str, str]:
    """Extract **Key:** Value pairs from a GitHub Issue markdown body."""
    result: dict[str, str] = {}
    for line in body.splitlines():
        m = re.match(r'\*\*([^*]+)\*\*[:\s]+(.+)', line.strip())
        if m:
            key = m.group(1).strip().lower().replace(" ", "-").rstrip(":")
            val = m.group(2).strip()
            result[key] = val
    return result


def make_datum(date_iso: str) -> tuple[str, str]:
    """Return (short datum label, full weekday name) from an ISO date string."""
    try:
        d    = date.fromisoformat(date_iso)
        wd   = d.weekday()
        short = WDAY_DE[wd][:2]
        return f"{short}, {d.strftime('%d.%m.%Y')}", WDAY_DE[wd]
    except ValueError:
        return date_iso, ""


def build_event(fields: dict[str, str], issue_num: int) -> dict:
    date_iso      = fields.get("datum", "")
    date_iso_end  = fields.get("datum-ende", "") or None
    datum, wochentag = make_datum(date_iso)

    datum_end = None
    if date_iso_end:
        try:
            d2 = date.fromisoformat(date_iso_end)
            datum_end = d2.strftime("%d.%m.%Y")
        except ValueError:
            pass

    sport_raw = fields.get("sport", "").lower()
    snapshot  = SPORT_SNAPSHOT.get(sport_raw, "SNAPSHOT")
    art       = fields.get("typ", fields.get("art", "Sonstiges"))

    return {
        "art":          art,
        "datum":        datum,
        "datum_end":    datum_end,
        "wochentag":    wochentag,
        "date_iso":     date_iso,
        "date_iso_end": date_iso_end,
        "km":           None,
        "lat":          None,
        "lon":          None,
        "titel":        fields.get("name", ""),
        "ort":          fields.get("ort", ""),
        "strecken":     "",
        "verein":       "",
        "lv":           "",
        "country":      "DE",
        "url":          fields.get("link", ""),
        "serie":        "",
        "_snapshot":    snapshot,
        "_issue":       issue_num,
    }


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Usage: approve_event.py <body_file> <issue_number>")

    body_file = pathlib.Path(sys.argv[1])
    issue_num = int(sys.argv[2])
    body      = body_file.read_text(encoding="utf-8")

    fields = parse_body(body)
    print(f"Parsed fields: {fields}")

    if not fields.get("name") or not fields.get("datum"):
        sys.exit("ERROR: Missing required fields 'name' and/or 'datum'.")

    event = build_event(fields, issue_num)
    print(f"→ {event['titel']}  {event['date_iso']}  [{event['_snapshot']}]")

    # Load existing list, replace if same issue, append, sort, save
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    approved: list[dict] = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else []
    approved = [e for e in approved if e.get("_issue") != issue_num]
    approved.append(event)
    approved.sort(key=lambda e: e.get("date_iso", ""))
    DATA_FILE.write_text(json.dumps(approved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved – {len(approved)} approved events in {DATA_FILE}")


if __name__ == "__main__":
    main()
