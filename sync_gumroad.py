#!/usr/bin/env python3
"""Sync Gumroad sales/views into capital.json (SSOT).

Reads the Gumroad MCP OAuth token from opencode's credential store, calls
the Gumroad MCP (get_analytics) for per-product views/sales/revenue, and
merges the result into ~/.config/productivity-capital/capital.json under
the "gumroad" key. Refreshes the token (and persists it) if expired.
"""
import json, os, sqlite3, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.config/productivity-capital/capital.json")
DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")
MCP_URL = "https://gumroad.com/claude/v1/mcp"
TOKEN_URL = "https://gumroad.com/oauth/token"
CLIENT_ID = "tu9BG8GrsfHBGd0K53LmnW2UuwQr19dUe863fU7qbdA"
INTEG = "mcp_0eb98bf26661d596"


def load_cred():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT value FROM credential WHERE integration_id=?", (INTEG,)
    ).fetchone()
    conn.close()
    if not row:
        raise RuntimeError("no gumroad credential in opencode.db")
    return json.loads(row[0])


def save_cred(cred):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE credential SET value=?, time_updated=? WHERE integration_id=?",
        (json.dumps(cred), int(time.time() * 1000), INTEG),
    )
    conn.commit()
    conn.close()


def mcp_call(tool, args, token):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": tool, "arguments": args or {}}}
    req = urllib.request.Request(
        MCP_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


def refresh_cred(cred):
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": cred["refresh"],
        "client_id": CLIENT_ID,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())
    cred["access"] = res["access_token"]
    if res.get("refresh_token"):
        cred["refresh"] = res["refresh_token"]
    return cred


def call_tool(tool, args):
    cred = load_cred()
    try:
        return mcp_call(tool, args, cred["access"])
    except urllib.error.HTTPError as e:
        if e.code == 401:
            cred = refresh_cred(cred)
            save_cred(cred)
            return mcp_call(tool, args, cred["access"])
        raise


def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    res = call_tool("get_analytics", {})
    text = res["result"]["content"][0]["text"]
    analytics = json.loads(text)
    rows = analytics.get("rows", [])

    products = []
    total_views = total_sales = total_revenue = 0
    for r in rows:
        v = r.get("views") or 0
        s = r.get("sales") or 0
        rc = r.get("revenue_cents") or 0
        products.append({
            "id": r["product_id"],
            "name": r["product_name"],
            "views": v,
            "sales": s,
            "revenue_cents": rc,
            "conversion_rate": r.get("conversion_rate"),
        })
        total_views += v
        total_sales += s
        total_revenue += rc

    # aggregate totals (best-effort)
    agg = {}
    try:
        res2 = call_tool("get_sales_totals", {})
        agg = json.loads(res2["result"]["content"][0]["text"]).get("totals", {})
    except Exception:
        pass

    d = load_data()
    now = datetime.now().isoformat(timespec="seconds")
    g = d.setdefault("gumroad", {})
    g["updated_at"] = now
    g["period_start"] = analytics.get("start_date")
    g["period_end"] = analytics.get("end_date")
    g["currency"] = analytics.get("currency", "usd")
    g["total_views"] = total_views
    g["total_sales"] = total_sales
    g["total_revenue_cents"] = total_revenue
    g["products"] = products
    g["totals"] = agg
    d["updated_at"] = now

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)
    print(f"synced gumroad: views={total_views} sales={total_sales} "
          f"revenue_cents={total_revenue} products={len(products)}")


if __name__ == "__main__":
    main()
