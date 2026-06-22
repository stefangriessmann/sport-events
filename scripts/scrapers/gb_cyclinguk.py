#!/usr/bin/env python3
"""
gb_cyclinguk.py – Scraper für Cycling UK (cyclinguk.org) Event-Listing.

Liefert Breitensport-Rad-Events in UK (Sportives, Charity-Rides, Audax) im
bockwurst-Schema mit Geodaten (Postcode → postcodes.io).

Konvention wie die DE-Scraper:  fetch(year) -> list[dict]

Direktlauf (CI/lokal, braucht Netz):
    python scripts/scrapers/gb_cyclinguk.py
schreibt data/radsport-gb.json und gibt eine Zusammenfassung aus.

robots.txt: /event-listing ist erlaubt (geprüft 22.06.2026). Niedrige Request-Rate.
"""
from __future__ import annotations

import json
import re
import sys
import time
import pathlib
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE = "https://www.cyclinguk.org"
LISTING = BASE + "/event-listing?page={page}"
UA = "bockwurst.cc event guide (+https://bockwurst.cc; contact stefan.griessmann@web.de)"
HEADERS = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"}

# Nur Breitensport-/Jedermann-Typen behalten (Teilstring-Treffer im "Type of event")
KEEP_TYPES = ("Sportive/Challenge Ride", "Mass Participation Charity Ride")

# UK-Postcode-Muster
POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b")

MAX_PAGES = 30          # Sicherheitsobergrenze
REQ_DELAY = 0.6         # Sekunden zwischen Requests (höflich)
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

_GEO_CACHE: dict[str, dict] = {}


def _get(url: str) -> str | None:
    try:
        r = SESSION.get(url, timeout=30)
        if r.status_code != 200:
            print(f"  WARN {r.status_code} {url}", file=sys.stderr)
            return None
        return r.text
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR {url}: {e}", file=sys.stderr)
        return None
    finally:
        time.sleep(REQ_DELAY)


def geocode_postcode(pc: str) -> dict | None:
    """postcodes.io – kostenlos, ohne Auth. Gibt lat/lon/region/country."""
    key = pc.replace(" ", "").upper()
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
    try:
        r = SESSION.get(f"https://api.postcodes.io/postcodes/{key}", timeout=20)
        time.sleep(REQ_DELAY)
        if r.status_code == 200:
            res = r.json().get("result") or {}
            out = {
                "lat": res.get("latitude"),
                "lon": res.get("longitude"),
                "region": res.get("region") or res.get("admin_district"),
                "country": res.get("country"),
            }
            _GEO_CACHE[key] = out
            return out
    except Exception as e:  # noqa: BLE001
        print(f"  GEO ERROR {pc}: {e}", file=sys.stderr)
    _GEO_CACHE[key] = None
    return None


def parse_listing_page(html: str) -> list[dict]:
    """Eventlinks + Basisdaten aus einer Listenseite."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    seen = set()
    for a in soup.select('a[href*="/event/"]'):
        href = a.get("href", "")
        if "/event/" not in href:
            continue
        url = href if href.startswith("http") else BASE + href
        if url in seen:
            continue
        seen.add(url)
        text = a.get_text(" ", strip=True)
        title_attr = a.get("title", "") or ""
        title = title_attr.rsplit(" - ", 1)[0].strip() if " - " in title_attr else title_attr.strip()
        m_type = re.search(r"Type of event:\s*(.+?)\s*(?:Ride surface:|View event|$)", text)
        m_loc = re.search(r"Start location:\s*(.+?)\s*(?:Distance:|Type of event:|Ride surface:|View event|$)", text)
        m_dist = re.search(r"Distance:\s*(.+?)\s*(?:Type of event:|Ride surface:|View event|$)", text)
        m_date = re.search(r"((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+\d{1,2}\s+\w+\s+\d{4})", text)
        out.append({
            "url": url,
            "titel": title,
            "type": (m_type.group(1).strip() if m_type else ""),
            "ort": (m_loc.group(1).strip() if m_loc else ""),
            "dist_raw": (m_dist.group(1).strip() if m_dist else ""),
            "date_text": (m_date.group(1).strip() if m_date else ""),
        })
    return out


_DATE_RE = re.compile(r"((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+\d{1,2}\s+\w+\s+\d{4})")


def _section(text: str, start: str, ends: tuple[str, ...]) -> str:
    """Textausschnitt ab Label `start` bis zum ersten der `ends`-Labels.

    Wichtig, um Navigation/Footer (z. B. die Büro-Postcode GU2 9JX oder die
    '280km/174-mile'-Promo im Menü) NICHT mitzuparsen.
    """
    i = text.find(start)
    if i == -1:
        return ""
    i += len(start)
    j = len(text)
    for e in ends:
        k = text.find(e, i)
        if k != -1:
            j = min(j, k)
    return text[i:j]


def _uniq(seq):
    return list(dict.fromkeys(seq))


def parse_detail(html: str) -> dict:
    """Postcode, Distanzen, Datum, Veranstalter, Audax-Kategorie – jeweils nur aus
    der passenden Detail-Sektion (nicht aus Nav/Footer)."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    d = {}

    # Adresse/Postcode nur aus der "Start location"-Sektion
    loc = _section(text, "Start location", ("Date and time", "Contact details", "Subscribe to Cycling UK"))
    pc = POSTCODE_RE.search(loc)
    d["postcode"] = pc.group(1).strip() if pc else ""

    # Distanzen nur aus "Route details" (steht vor "Start location")
    route = _section(text, "Route details", ("Start location", "Date and time", "Contact details"))
    d["km_list"] = _uniq(re.findall(r"(\d+(?:\.\d+)?)\s*km", route))
    d["mi_list"] = _uniq(re.findall(r"(\d+(?:\.\d+)?)\s*mi\b", route))

    # Datum aus "Date and time", sonst Fallback auf gesamten Text
    datesec = _section(text, "Date and time", ("Contact details", "Subscribe to Cycling UK"))
    m_date = _DATE_RE.search(datesec) or _DATE_RE.search(text)
    d["date_text"] = m_date.group(1).strip() if m_date else ""

    m_org = re.search(r"Organised by\s+(.+?)(?:\s{2,}|Audax category|Route details|Start location|Date and time|$)", text)
    d["organiser"] = m_org.group(1).strip()[:120] if m_org else ""
    d["is_audax"] = "Audax category" in text

    # externe Event-Website (z. B. audax.uk) als bevorzugte URL
    ext = ""
    for a in soup.select("a[href^='http']"):
        h = a.get("href", "")
        if "cyclinguk.org" in h:
            continue
        if any(k in h for k in ("audax.uk", "letsdothis", "eventrac", "british", "entrycentral", "sientries")):
            ext = h
            break
    d["ext_url"] = ext
    return d


def to_iso(date_text: str) -> str | None:
    if not date_text:
        return None
    try:
        return datetime.strptime(date_text, "%A %d %B %Y").date().isoformat()
    except ValueError:
        return None


def classify(type_str: str, is_audax: bool) -> str:
    if is_audax:
        return "Audax"
    if "Mass Participation Charity Ride" in type_str:
        return "Charity Ride"
    if "Sportive/Challenge Ride" in type_str:
        return "Sportive"
    return "Radsport"


def fetch(year: int | None = None) -> list[dict]:
    today = date.today().isoformat()
    listing_seen = 0
    kept_raw = []
    for page in range(MAX_PAGES):
        html = _get(LISTING.format(page=page))
        if not html:
            break
        if "doesn't look like we have anything" in html:
            break
        rows = parse_listing_page(html)
        if not rows:
            break
        listing_seen += len(rows)
        for r in rows:
            if any(t in r["type"] for t in KEEP_TYPES):
                kept_raw.append(r)
    print(f"  Listing: {listing_seen} Einträge gesichtet, {len(kept_raw)} Breitensport-Kandidaten", file=sys.stderr)

    events = []
    seen_urls = set()
    for r in kept_raw:
        if r["url"] in seen_urls:
            continue
        seen_urls.add(r["url"])
        detail_html = _get(r["url"])
        det = parse_detail(detail_html) if detail_html else {}
        date_iso = to_iso(det.get("date_text") or r["date_text"])
        if not date_iso or date_iso < today:
            continue
        art = classify(r["type"], det.get("is_audax", False))
        lat = lon = None
        lv = ""
        pc = det.get("postcode", "")
        if pc:
            geo = geocode_postcode(pc)
            if geo and geo.get("lat") is not None:
                lat, lon = geo["lat"], geo["lon"]
                lv = geo.get("region") or ""
        # Distanzen / km
        km_list = det.get("km_list") or []
        mi_list = det.get("mi_list") or []
        # strecken in Meilen (UK-Konvention); km bleibt intern als Zahl erhalten
        strecken = " / ".join(mi_list) if mi_list else (" / ".join(km_list) if km_list else r["dist_raw"])
        km_val = float(km_list[0]) if km_list else None
        try:
            dt = datetime.strptime(date_iso, "%Y-%m-%d").date()
            wd = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"][dt.weekday()]
            datum = f"{wd[:2]}, {dt.strftime('%d.%m.%Y')}"
        except ValueError:
            wd, datum = "", date_iso
        events.append({
            "art": art,
            "datum": datum,
            "datum_end": None,
            "wochentag": wd,
            "date_iso": date_iso,
            "date_iso_end": None,
            "km": km_val,
            "lat": lat,
            "lon": lon,
            "titel": r["titel"] or "(ohne Titel)",
            "ort": r["ort"],
            "plz": pc,
            "strecken": strecken,
            "verein": det.get("organiser", ""),
            "lv": lv,
            "country": "GB",
            "url": det.get("ext_url") or r["url