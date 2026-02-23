import logging
import subprocess
import threading
import webbrowser
from collections import deque

import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except ValueError:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3

from gi.repository import GLib, Gtk

logger = logging.getLogger(__name__)

_MAX_RECENT = 10


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def _open_url(url: str) -> None:
    """Open a URL in the default browser, Wayland-safe."""
    try:
        from gi.repository import Gio
        Gio.AppInfo.launch_default_for_uri(url, None)
    except Exception:
        webbrowser.open(url)


def _notify(title: str, body: str) -> None:
    try:
        subprocess.Popen(
            ["notify-send", "--icon=linkover", "--app-name=Linkover", title, body]
        )
    except FileNotFoundError:
        logger.warning("notify-send not found — skipping desktop notification")


class TrayApp:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recent: deque[dict] = deque(maxlen=_MAX_RECENT)

        self._indicator = AppIndicator3.Indicator.new(
            "linkover",
            "linkover",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_menu(self._build_menu())

    # ------------------------------------------------------------------
    # Called from the WebSocket thread
    # ------------------------------------------------------------------

    def on_messages(self, messages: list[dict]) -> None:
        for msg in messages:
            self._handle_message(msg)
        GLib.idle_add(self._refresh_menu)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_message(self, msg: dict) -> None:
        url = msg.get("url") or ""
        body = msg.get("message") or ""
        title = msg.get("title") or "Linkover"

        target = url if _is_url(url) else (body if _is_url(body) else None)
        display_body = url or body

        with self._lock:
            self._recent.appendleft(msg)

        _notify(title, display_body)

        if target:
            logger.info("Opening: %s", target)
            GLib.idle_add(_open_url, target)

    def _refresh_menu(self) -> bool:
        self._indicator.set_menu(self._build_menu())
        return False  # tell GLib not to repeat

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        with self._lock:
            recent = list(self._recent)

        if recent:
            for msg in recent:
                url = msg.get("url") or ""
                body = msg.get("message") or ""
                target = url if _is_url(url) else (body if _is_url(body) else None)
                label = (msg.get("title") or target or body or "Unknown")[:60]

                item = Gtk.MenuItem(label=label)
                if target:
                    item.connect("activate", lambda _, t=target: _open_url(t))
                else:
                    item.set_sensitive(False)
                menu.append(item)
        else:
            placeholder = Gtk.MenuItem(label="No links yet")
            placeholder.set_sensitive(False)
            menu.append(placeholder)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def run(self) -> None:
        Gtk.main()
