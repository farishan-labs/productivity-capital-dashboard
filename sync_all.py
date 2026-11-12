#!/usr/bin/env python3
"""Run all capital.json syncs (shipped, site traffic, gumroad) best-effort."""
import os, subprocess, sys

DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["sync_shipped.py", "sync_traffic.py", "sync_gumroad.py"]

def main():
    for name in SCRIPTS:
        path = os.path.join(DIR, name)
        if not os.path.exists(path):
            print(f"skip (missing): {name}", file=sys.stderr)
            continue
        try:
            r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=120)
            print(f"== {name} ==")
            if r.stdout.strip():
                print(r.stdout.strip())
            if r.returncode != 0:
                print(f"  exit {r.returncode}: {r.stderr.strip()}", file=sys.stderr)
        except Exception as e:
            print(f"  error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
