#!/usr/bin/env python3
"""Update the Productivity Capital dashboard data file.

Usage examples:
  update_capital.py --money-today 120000 --money-yesterday 100000
  update_capital.py --money-pending 50000
  update_capital.py --traffic-today-views 1200 --traffic-today-visitors 340
  update_capital.py --traffic-yesterday-views 1000 --traffic-yesterday-visitors 300
  update_capital.py --set '{"money":{"today":100}}'
"""
import argparse, json, os
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.config/productivity-capital/capital.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"money": {"today": 0.0, "yesterday": 0.0, "pending": 0.0,
                          "currency": "IDR"},
                "traffic": {"today_views": 0, "yesterday_views": 0,
                            "today_visitors": 0, "yesterday_visitors": 0},
                "shipped": {"today": 0, "yesterday": 0}}

def save(d):
    d["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)
    print("updated", DATA_FILE)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--money-today", type=float, dest="money_today")
    ap.add_argument("--money-yesterday", type=float, dest="money_yesterday")
    ap.add_argument("--money-pending", type=float, dest="money_pending")
    ap.add_argument("--money-received", type=float, dest="money_today")  # alias
    ap.add_argument("--currency")
    ap.add_argument("--traffic-today-views", type=int, dest="tv_today")
    ap.add_argument("--traffic-yesterday-views", type=int, dest="tv_yesterday")
    ap.add_argument("--traffic-today-visitors", type=int, dest="vis_today")
    ap.add_argument("--traffic-yesterday-visitors", type=int, dest="vis_yesterday")
    ap.add_argument("--traffic-views", type=int, dest="tv_today")  # alias
    ap.add_argument("--traffic-visitors", type=int, dest="vis_today")  # alias
    ap.add_argument("--shipped-today", type=int, dest="shipped_today")
    ap.add_argument("--shipped-yesterday", type=int, dest="shipped_yesterday")
    ap.add_argument("--set", help="JSON object merged into data")
    args = ap.parse_args()
    d = load()
    m = d.setdefault("money", {})
    t = d.setdefault("traffic", {})
    if args.money_today is not None:
        m["today"] = args.money_today
    if args.money_yesterday is not None:
        m["yesterday"] = args.money_yesterday
    if args.money_pending is not None:
        m["pending"] = args.money_pending
    if args.currency:
        m["currency"] = args.currency
    if args.tv_today is not None:
        t["today_views"] = args.tv_today
    if args.tv_yesterday is not None:
        t["yesterday_views"] = args.tv_yesterday
    if args.vis_today is not None:
        t["today_visitors"] = args.vis_today
    if args.vis_yesterday is not None:
        t["yesterday_visitors"] = args.vis_yesterday
    s = d.setdefault("shipped", {})
    if args.shipped_today is not None:
        s["today"] = args.shipped_today
    if args.shipped_yesterday is not None:
        s["yesterday"] = args.shipped_yesterday
    if args.set:
        patch = json.loads(args.set)
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(d.get(k), dict):
                d[k].update(v)
            else:
                d[k] = v
    save(d)

if __name__ == "__main__":
    main()
