#!/usr/bin/env python3
"""Auto-compute 'shipped' (git commits) across ~/dev and update capital.json.

Counts commits whose author date falls on today / yesterday (local time)
across all git repos found up to depth 3 under ROOT. Skips node_modules, .cache.
"""
import json, os, subprocess, datetime

ROOT = os.path.expanduser("~/dev")
DATA_FILE = os.path.expanduser("~/.config/productivity-capital/capital.json")
MAX_DEPTH = 3
SKIP = {"node_modules", ".cache", "dist", "build", ".next", "target"}

def find_repos(root, depth=0):
    repos = []
    if depth > MAX_DEPTH:
        return repos
    try:
        entries = os.listdir(root)
    except OSError:
        return repos
    if os.path.isdir(os.path.join(root, ".git")):
        repos.append(root)
        # don't descend into a repo's submodules? still descend for nested repos
    for name in entries:
        if name in SKIP or name.startswith("."):
            # allow .git already handled; skip other hidden
            if name != ".git":
                continue
        path = os.path.join(root, name)
        if os.path.isdir(path) and name != ".git":
            repos.extend(find_repos(path, depth + 1))
    return repos

def count_commits(repo, since, until):
    try:
        out = subprocess.run(
            ["git", "-C", repo, "rev-list", "--count", f"--since={since}", f"--until={until}", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return 0
        return int(out.stdout.strip() or 0)
    except Exception:
        return 0

def last_commit_iso(repo):
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%cI"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip() or None
    except Exception:
        return None

def main():
    now = datetime.datetime.now()
    today = now.date()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    since_today = today.isoformat() + "T00:00:00"
    until_today = tomorrow.isoformat() + "T00:00:00"
    since_yest = yesterday.isoformat() + "T00:00:00"
    until_yest = today.isoformat() + "T00:00:00"

    repos = sorted(set(find_repos(ROOT)))
    today_n = 0
    yest_n = 0
    recent = []
    for r in repos:
        today_n += count_commits(r, since_today, until_today)
        yest_n += count_commits(r, since_yest, until_yest)
        iso = last_commit_iso(r)
        if iso:
            recent.append((iso, os.path.basename(r), r))
    recent.sort(reverse=True)
    top3 = [{"name": name, "when": iso} for iso, name, _ in recent[:3]]

    # update capital.json
    try:
        with open(DATA_FILE) as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        d = {}
    s = d.setdefault("shipped", {})
    s["today"] = today_n
    s["yesterday"] = yest_n
    d["repos"] = top3
    d["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)
    print(f"repos={len(repos)} shipped today={today_n} yesterday={yest_n} top3={[r['name'] for r in top3]}")

if __name__ == "__main__":
    main()
