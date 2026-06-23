#!/usr/bin/env python3
"""
gb_sportive.py – Scraper für Sportive.com (UK) über den iCal-Feed.

Sportive.com nutzt "The Events Calendar" (WordPress) und bietet einen iCal-Feed.
Jedes VEVENT hat GEO (lat;lon), LOCATION (inkl. Postcode/Ort/Land), URL,
CATEGORIES (Road/Gravel/Charity/…) und DTSTART → kein Geocoding nötig.

Konvention wie die DE-Scraper:  fetch(year) -> list[dict]
Direktlauf: python scripts/scrapers/gb_sportive.py  (schreibt data/radsport-gb-sportive.json)

robots.txt: erlaubt (nur Cart/Admin gesperrt), geprüft 22.06.2026.
"""
from __future__ import annotations

import json
import re
import sys
import time
import pathlib
from datetime import date, datetime

import requests

ICAL = "https://sportive.com/events/?ical=1"
UA = "bockwurst.cc event guide (+https://bockwurst.cc; contact stefan.griessmann@web.de)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})

POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b")
MAX_PAGES = 12
REQ_DELAY = 0.8


def _unescape(v: str) -> str:
    return v.replace("\\,", ",").replace("\\;", ";").replace("\\n", "\n").replace("\\\\", "\\")


def _unfold(text: str) -> str:
    # RFC5545 Line-Folding: Folgezeilen beginnen mit Space/Tab
    return re.sub(r"\r?\n[ \t]", "", text)


def parse_ical(text: str) -> list[dict]:
    text = _unfold(text)
    out = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        d = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            name = key.split(";")[0]
            d.setdefault(name, val.strip())
        out.append(d)
    return out


def classify(cats: str) -> str:
    c = cats.lower()
    if "audax" in c:
        return "Audax"
    if "charity" in c:
        return "Charity Ride"
    if "gravel" in c:
        return "Gravel"
    if "mtb" in c:
        return "MTB"
    if "adventure" in c:
        return "Adventure"
    if "road" in c:
        return "Sportive"
    if "festival" in c:
        return "Festival"
    first = cats.split(",")[0].strip()
    return first or "Sportive"


def fetch(year: int | None = None) -> list[dict]:
    today = date.today().isoformat()
    by_uid: dict[str, dict] = {}
    for page in range(1, MAX_PAGES + 1):
        url = ICAL + (f"&tribe_paged={page}" if page > 1 else "")
        try:
            r = SESSION.get(url, timeout=30)
            time.sleep(REQ_DELAY)
            if r.status_code != 200:
                break
            vevents = parse_ical(r.text)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {url}: {e}", file=sys.stderr)
            break
        if not vevents:
            break
        new = 0
        for v in vevents:
            uid = v.get("UID", "")
            if uid and uid not in by_uid:
                by_uid[uid] = v
                new += 1
        print(f"  Seite {page}: {len(vevents)} VEVENTs, {new} neu (gesamt {len(by_uid)})", file=sys.stderr)
        if new == 0:  # Pagination liefert nichts Neues -> Ende
            break

    events = []
    for v in by_uid.values():
        loc = _unescape(v.get("LOCATION", ""))
        if "United Kingdom" not in loc:  # nur GB
            continue
        dt = v.get("DTSTART", "")[:8]
        try:
            date_iso = datetime.strptime(dt, "%Y%m%d").date().isoformat()
        except ValueError:
            continue
        if date_iso < today:
            continue
        geo = v.get("GEO", "")
        lat = lon = None
        if ";" in geo:
            try:
                la, lo = geo.split(";", 1)
                lat, lon = float(la), float(lo)
            except ValueError:
                pass
        pcm = POSTCODE_RE.search(loc)
        pc = pcm.group(1).strip() if pcm else ""
        segs = [s.strip() for s in loc.split(",") if s.strip()]
        if segs and segs[-1].lower() in ("united kingdom", "uk"):
            segs = segs[:-1]
        segs = [s for s in segs if not (pc and pc.replace(" ", "") in s.replace(" ", ""))]
        ort = ", ".join(segs[1:]) if len(segs) > 1 else (segs[0] if segs else "")
        art = classify(v.get("CATEGORIES", ""))
        desc = _unescape(v.get("DESCRIPTION", ""))
        dists = []
        for m in re.findall(r"(\d{2,3})\s*(?:km|KM|miles|mi)\b", desc):
            if m not in dists:
                dists.append(m)
        try:
            d2 = datetime.strptime(date_iso, "%Y-%m-%d").date()
            wd = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"][d2.weekday()]
            datum = f"{wd[:2]}, {d2.strftime('%d.%m.%Y')}"
        except ValueError:
            wd, datum = "", date_iso
        events.append({
            "art": art,
            "datum": datum,
            "datum_end": None,
            "wochentag": wd,
            "date_iso": date_iso,
            "date_iso_end": None,
            "km": None,
            "lat": lat,
            "lon": lon,
            "titel": _unescape(v.get("SUMMARY", "")) or "(ohne Titel)",
            "ort": ort,
            "plz": pc,
            "strecken": " / ".join(dists),
            "verein": "",
            "lv": "",
            "country": "GB",
            "url": v.get("URL", ""),
            "serie": ", ".join(c.strip() for c in v.get("CATEGORIES", "").split(",") if c.strip()),
        })
    events.sort(key=lambda e: e["date_iso"])
    return events


def main():
    events = fetch(date.today().year)
    root = pathlib.Path(__file__).resolve().parents[2]
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "radsport-gb-sportive.json").write_text(
        json.dumps(events, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from collections import Counter
    by_art = Counter(e["art"] for e in events)
    geo = sum(1 for e in events if e["lat"] is not None)
    print("\n=== Sportive.com Scraper – Zusammenfassung ===")
    print(f"UK-Events (zukünftig): {len(events)}")
    print(f"  nach art: {dict(by_art)}")
    print(f"  mit Koordinaten: {geo}  |  mit Postcode: {sum(1 for e in events if e['plz'])}")
    print(f"  -> data/radsport-gb-sportive.json")
    print("\nBeispiele:")
    for e in events[:10]:
        print(f"  {e['date_iso']}  {e['art']:11s} {e['titel'][:40]:40s} | {e['ort'][:30]:30s} | {e['plz']:8s} | {e['strecken']}")


if __name__ == "__main__":
    main()
