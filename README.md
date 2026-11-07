# Productivity Capital Dashboard

A desktop widget (based on [ubuntu-desktop-widget-starter](https://github.com/farishan/ubuntu-desktop-widget-starter))
that shows **productivity capital gained**:

- **Money** (primary): today's capital vs yesterday, plus pending (awaiting verification)
- **Traffic** (secondary): today's views/visitors vs yesterday (social capital)

UI is a minimalist HTML/CSS dashboard rendered with **WebKitGTK** inside the
GTK3 desktop window. Date format: `Updated 1 minutes ago (7 Nov, 22:01)`.

Stays on the desktop, below normal windows, survives Super+D (Show Desktop).
Reads `~/.config/productivity-capital/capital.json` and refreshes every 30s.

## Run

```bash
python3 widget.py
```

## Restart (one command)

```bash
productivity-capital-restart
```

(or `./restart.sh` from the project dir). Refreshes shipped count from git activity across `~/dev`, then kills any running instance and launches a fresh one.

## Shipped + Recent repos (auto)

`sync_shipped.py` counts git commits today/yesterday across `~/dev` and writes
`shipped` + `repos` (top 3 most recently updated) to `capital.json`. Run manually
or via `restart.sh`/cron.

## Update data (used by agents / workflows)

```bash
./update_capital.py --money-today 150000 --money-yesterday 100000 --money-pending 25000 \
  --traffic-today-views 1200 --traffic-today-visitors 340 \
  --traffic-yesterday-views 900 --traffic-yesterday-visitors 280
```

Or merge raw JSON:

```bash
./update_capital.py --set '{"money":{"today":150000},"traffic":{"today_views":1200}}'
```

## Autostart

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/productivity-capital.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Productivity Capital
Exec=/usr/bin/python3 $HOME/dev/personal/productivity-capital-dashboard/widget.py
X-GNOME-Autostart-enabled=true
EOF
```

## Wayland caveat

Same as the starter: hints are ignored on GNOME/Wayland. Use X11 session or a GNOME Shell extension.
