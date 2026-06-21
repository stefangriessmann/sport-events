#!/usr/bin/env python3
"""Sendet eine Ergebnis-Mail via Resend (HTTP-API, kein SMTP).

Aufruf:
    python3 scripts/notify_resend.py "<Betreff>" "<Text>"

Umgebung:
    RESEND_API_KEY   – Resend API-Key (Pflicht; fehlt er, wird ohne Fehler übersprungen)
    NOTIFY_TO        – Empfänger (Default: stefan.griessmann@web.de)
    NOTIFY_FROM      – Absender (Default: onboarding@resend.dev – bis bockwurst.cc verifiziert ist)

Ein Mail-Fehler beendet das Skript bewusst mit Exit 0, damit der Workflow
deswegen nicht rot wird.
"""
import os
import sys
import json
import urllib.request

key = os.environ.get("RESEND_API_KEY")
if not key:
    print("RESEND_API_KEY nicht gesetzt – Mail übersprungen.")
    sys.exit(0)

to      = os.environ.get("NOTIFY_TO", "stefan.griessmann@web.de")
sender  = os.environ.get("NOTIFY_FROM", "bockwurst.cc <onboarding@resend.dev>")
subject = sys.argv[1] if len(sys.argv) > 1 else "[bockwurst.cc] Benachrichtigung"
text    = sys.argv[2] if len(sys.argv) > 2 else ""

payload = {"from": sender, "to": [to], "subject": subject, "text": text}
req = urllib.request.Request(
    "https://api.resend.com/emails",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=20)
    print("Mail gesendet:", resp.status)
except Exception as e:  # noqa: BLE001
    print("Mail-Versand fehlgeschlagen:", e)
    sys.exit(0)
