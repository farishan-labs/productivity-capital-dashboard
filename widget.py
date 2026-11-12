#!/usr/bin/env python3
"""Productivity Capital dashboard widget (GTK3 + WebKit, X11/GNOME).

Desktop widget that stays on the desktop (survives Super+D, not always-on-top)
and shows "productivity capital gained": money (primary) + traffic (secondary).

UI is a minimalist HTML/CSS dashboard rendered by WebKitGTK inside the GTK3
desktop window. Data comes from ~/.config/productivity-capital/capital.json and
is pushed to the page every REFRESH_SEC seconds.

Date format: "Updated 1 minute ago (7 Nov, 22:01)"
"""
import json, os, sys, warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone

INTERACTIVE = os.environ.get("INTERACTIVE", "").lower() in ("1", "true", "yes") or "--interactive" in sys.argv

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, Gdk, GLib, WebKit2

DATA_FILE = os.path.expanduser("~/.config/productivity-capital/capital.json")
REFRESH_SEC = 30

HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html, body { background: transparent; height: 100%; margin: 0; }
  body {
    color: #e6e6e6;
    font-family: 'Inter', 'Ubuntu', 'DejaVu Sans', sans-serif;
    padding: 0;
    overflow: hidden;
  }
  body.interactive .card { overflow-y: auto; }
  .card {
    background: transparent;
    padding: 18px 20px;
    width: 300px;
    max-height: 100vh;
    overflow-y: hidden;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,255,255,0.15) transparent;
  }
  .card::-webkit-scrollbar { width: 6px; }
  .card::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
  .money, .row b, .traffic b { text-shadow: 0 1px 3px rgba(0,0,0,0.8); }
  .title { font-size: 10px; letter-spacing: 1.6px; text-transform: uppercase; color: #777; margin-bottom: 10px; }
  .money { font-size: 34px; font-weight: 300; line-height: 1; margin-bottom: 2px; }
  .money .cur { font-size: 15px; color: #999; margin-left: 6px; vertical-align: middle; }
  .hdr { font-size: 10px; color: #666; margin-bottom: 8px; letter-spacing: 0.5px; }
  .row { display: flex; justify-content: space-between; font-size: 12px; color: #999; margin-top: 4px; }
  .row b { color: #e6e6e6; font-weight: 500; }
  .traffic, .shipped { margin-top: 8px; font-size: 12px; color: #999; }
  .repos { margin-top: 8px; font-size: 11px; color: #777; list-style: disc; padding-left: 16px; }
  .repos li { margin-top: 2px; }
  .traffic b, .shipped b { color: #e6e6e6; font-weight: 500; }
  .delta { font-size: 11px; margin-left: 6px; }
  .delta.pos { color: #4ade80; }
  .delta.neg { color: #f87171; }
  .delta.zero { color: #666; }
  .updated { margin-top: 12px; font-size: 10px; color: #555; }
</style>
</head>
<body class="INTERACTIVE_PLACEHOLDER">
  <div class="card">
    <div class="title">Productivity Capital</div>
    <div class="hdr">Today vs Yday</div>
    <div class="money"><span id="today">0</span> <span class="cur" id="cur">IDR</span> <span id="moneyDelta" class="delta">0</span></div>
    <div class="row"><span>pending</span><b id="pending">0</b></div>
    <div class="shipped">Shipped <b id="shipped">0</b> <span id="shippedDelta" class="delta">0</span></div>
    <div class="traffic">farishan.com <b id="viewsFc">0</b> views <span id="deltaFc" class="delta">0</span></div>
    <div class="traffic">han.farishan.com <b id="viewsHan">0</b> views <span id="deltaHan" class="delta">0</span></div>
    <ul class="repos" id="repos"></ul>
    <div class="updated" id="updated">Updated …</div>
  </div>
  <script>
    function fmt(n){ return Number(n||0).toLocaleString(); }
    function setDelta(el, x){
      x = Number(x||0);
      const e = document.getElementById(el);
      if (x > 0){ e.textContent = '+' + x.toLocaleString(); e.className = 'delta pos'; }
      else if (x < 0){ e.textContent = x.toLocaleString(); e.className = 'delta neg'; }
      else { e.textContent = '0'; e.className = 'delta zero'; }
    }
    function updateData(d) {
      const m = d.money || {};
      const t = d.traffic || {};
      const s = d.shipped || {};
      document.getElementById('today').textContent = fmt(m.today || 0);
      document.getElementById('cur').textContent = m.currency || 'IDR';
      setDelta('moneyDelta', (m.today||0)-(m.yesterday||0));
      document.getElementById('pending').textContent = fmt(m.pending || 0);
      document.getElementById('shipped').textContent = fmt(s.today || 0);
      setDelta('shippedDelta', (s.today||0)-(s.yesterday||0));
      const sites = t.sites || {};
      const fc = sites['farishan.com'] || {};
      const han = sites['han.farishan.com'] || {};
      document.getElementById('viewsFc').textContent = fmt(fc.today_views || 0);
      document.getElementById('viewsHan').textContent = fmt(han.today_views || 0);
      setDelta('deltaFc', (fc.today_views||0)-(fc.yesterday_views||0));
      setDelta('deltaHan', (han.today_views||0)-(han.yesterday_views||0));
      const repos = d.repos || [];
      const ul = document.getElementById('repos');
      ul.innerHTML = '';
      if (!repos.length) {
        const li = document.createElement('li');
        li.textContent = '—';
        ul.appendChild(li);
      } else {
        repos.forEach(r => {
          const li = document.createElement('li');
          li.textContent = r.name;
          ul.appendChild(li);
        });
      }
      document.getElementById('updated').textContent = d.updated_text || '';
    }
  </script>
</body>
</html>
"""
HTML = HTML.replace("INTERACTIVE_PLACEHOLDER", "interactive" if INTERACTIVE else "")


def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def format_updated(d):
    ts = d.get("updated_at", "")
    try:
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return "Updated never"
    now = datetime.now()
    delta_min = int((now - dt).total_seconds() // 60)
    if delta_min < 1:
        rel = "just now"
    else:
        rel = f"{delta_min} minutes ago"
    abs_str = dt.strftime("%-d %b, %H:%M")
    return f"Updated {rel} ({abs_str})"


def build_payload():
    d = load_data()
    return {
        "money": d.get("money", {}),
        "traffic": d.get("traffic", {}),
        "shipped": d.get("shipped", {}),
        "repos": d.get("repos", []),
        "updated_text": format_updated(d),
    }


class CapitalDashboard(Gtk.Window):
    def __init__(self):
        super().__init__(title="Productivity Capital")
        self.set_default_size(300, 290)
        self.set_position(Gtk.WindowPosition.CENTER)

        # transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual() if screen else None
        if visual is not None:
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_keep_below(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()
        self.set_accept_focus(INTERACTIVE)
        self.interactive = INTERACTIVE

        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_property("enable-developer-extras", False)
        try:
            self.webview.set_background_color(Gdk.RGBA(0, 0, 0, 0))
        except Exception:
            pass
        self.webview.load_html(HTML, "file:///")

        self.add(self.webview)
        self.connect("destroy", Gtk.main_quit)
        self.connect("realize", self._on_realize)

        self._loaded = False
        self.webview.connect("load-changed", self._on_load_changed)
        GLib.timeout_add(800, lambda: (self._center(), False)[1])
        GLib.timeout_add_seconds(REFRESH_SEC, self._tick)

    def _on_realize(self, _w):
        self.set_keep_below(True)
        self._apply_interactivity()
        self._center()
        # Re-raise above other desktop-layer windows (e.g. GNOME's desktop-icons
        # layer, which may map after this widget at login) while staying below
        # normal windows thanks to _NET_WM_STATE_BELOW.
        GLib.timeout_add(500, self._raise_window)
        GLib.timeout_add(2000, self._raise_window)

    def _apply_interactivity(self):
        try:
            win = self.get_window()
            if win is None:
                return
            if self.interactive:
                import cairo
                r = cairo.Region(cairo.RectangleInt(0, 0, 300, 300))
                win.input_shape_combine_region(r, 0, 0)
            else:
                import cairo
                win.input_shape_combine_region(cairo.Region(), 0, 0)
        except Exception:
            pass

    def _on_load_changed(self, _wv, event):
        if event == WebKit2.LoadEvent.FINISHED and not self._loaded:
            self._loaded = True
            self._push_data()

    def _center(self):
        try:
            display = Gdk.Display.get_default()
            if display is None:
                return
            mon = display.get_primary_monitor()
            geom = mon.get_geometry() if hasattr(mon, "get_geometry") else None
            if geom is None:
                screen = Gdk.Screen.get_default()
                mon = screen.get_primary_monitor()
                geom = screen.get_monitor_geometry(mon)
            x = geom.x + (geom.width - 300) // 2
            y = geom.y + (geom.height - 290) // 2
            self.move(x, y)
        except Exception:
            pass
        return False

    def _raise_window(self):
        # Open the display, raise, flush, and ALWAYS close it again.
        # Previously XOpenDisplay() was never paired with XCloseDisplay(),
        # leaking one X client connection per call (called every ~30s plus
        # twice at startup) until the 256-client X server limit was hit.
        d = None
        X11 = None
        try:
            import ctypes
            X11 = ctypes.CDLL("libX11.so.6")
            X11.XOpenDisplay.restype = ctypes.c_void_p
            X11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            X11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            X11.XFlush.argtypes = [ctypes.c_void_p]
            X11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            d = X11.XOpenDisplay(None)
            if d:
                win = self.get_window()
                if win is not None:
                    X11.XRaiseWindow(d, ctypes.c_ulong(win.get_xid()))
                    X11.XFlush(d)
        except Exception:
            pass
        finally:
            if d is not None and X11 is not None:
                try:
                    X11.XCloseDisplay(d)
                except Exception:
                    pass
        return False

    def _tick(self):
        self._raise_window()
        self._push_data()
        return True

    def _push_data(self):
        if not self._loaded:
            return
        import json as _json
        payload = _json.dumps(build_payload())
        self.webview.run_javascript(f"updateData({payload});", None, None, None)

    def refresh(self):
        self._push_data()


def main():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({
                "money": {"today": 0.0, "yesterday": 0.0, "pending": 0.0,
                          "currency": "IDR"},
                "traffic": {"today_views": 0, "yesterday_views": 0,
                            "today_visitors": 0, "yesterday_visitors": 0},
                "shipped": {"today": 0, "yesterday": 0},
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }, f, indent=2)
    w = CapitalDashboard()
    w.show_all()
    GLib.timeout_add(1000, lambda: (w._center(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
