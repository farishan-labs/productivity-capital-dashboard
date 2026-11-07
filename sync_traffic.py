#!/usr/bin/env python3
"""Sync site traffic from GoatCounter (han VPS) into capital.json.

Queries the GoatCounter SQLite DB over SSH for today/yesterday pageviews
per host (farishan.com, han.farishan.com) and updates:
  traffic.today_views / yesterday_views (combined)
  traffic.sites.<host>.today_views / yesterday_views
"""
import json, os, subprocess, sys
from datetime import datetime, timezone

DATA_FILE = os.path.expanduser("~/.config/productivity-capital/capital.json")
SSH_HOST = "vps"
DB_PATH = "/home/ubuntu/apps/goatcounter/data/goatcounter.db"

SQL = (
    "SELECT substr(p.path,2, CASE WHEN instr(substr(p.path,2),'/')=0 "
    "THEN length(p.path)-1 ELSE instr(substr(p.path,2),'/')-1 END) AS host, "
    "date(hc.hour) AS day, sum(hc.total) AS views "
    "FROM hit_counts hc JOIN paths p ON hc.path_id=p.path_id "
    "WHERE date(hc.hour) IN (date('now'), date('now','-1 day')) "
    "GROUP BY host, day"
)

def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

def save(d):
    d["updated_at"] = datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)
    print("synced traffic to", DATA_FILE)

def main():
    remote = ("sqlite3 2>/dev/null; /home/ubuntu/bin/goatcounter db query "
              "-db 'sqlite+" + DB_PATH + "' -format json \"" + SQL + "\"")
    cmd = ["ssh", "-o", "ConnectTimeout=10", SSH_HOST, remote]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=30)
    except Exception as e:
        print("ssh/query failed:", e, file=sys.stderr)
        sys.exit(1)
    rows = json.loads(out) if out.strip() else []

    sites = {}
    for r in rows:
        host = r["host"]
        day = r["day"]
        views = int(r["views"] or 0)
        sites.setdefault(host, {"today_views": 0, "yesterday_views": 0})
        # Determine which day relative to UTC today
        today = datetime.now(timezone.utc).date().isoformat()
        yday = (datetime.now(timezone.utc).date().toordinal() - 1)
        yday_iso = datetime.fromordinal(yday).date().isoformat() if False else None
    # Simpler: map by actual date string
    from datetime import date, timedelta
    today_iso = date.today().isoformat() if False else datetime.now(timezone.utc).date().isoformat()
    yday_iso = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    for r in rows:
        host = r["host"]
        day = r["day"]
        views = int(r["views"] or 0)
        sites.setdefault(host, {"today_views": 0, "yesterday_views": 0})
        if day == today_iso:
            sites[host]["today_views"] += views
        elif day == yday_iso:
            sites[host]["yesterday_views"] += views

    total_today = sum(s["today_views"] for s in sites.values())
    total_yday = sum(s["yesterday_views"] for s in sites.values())

    d = load()
    t = d.setdefault("traffic", {})
    t["today_views"] = total_today
    t["yesterday_views"] = total_yday
    t.setdefault("today_visitors", 0)
    t.setdefault("yesterday_visitors", 0)
    t["sites"] = sites
    save(d)
    print("today:", total_today, "yesterday:", total_yday, "sites:", sites)

if __name__ == "__main__":
    main()
