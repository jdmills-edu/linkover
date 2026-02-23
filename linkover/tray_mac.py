import logging
import subprocess
import threading
from collections import deque
from pathlib import Path

import rumps
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

_MAX_RECENT = 10
_ICON_CACHE = Path.home() / ".config" / "linkover" / "linkover.png"


def _ensure_icon() -> str:
    """Generate and cache the menu bar icon PNG on first run."""
    if _ICON_CACHE.exists():
        return str(_ICON_CACHE)

    _ICON_CACHE.parent.mkdir(parents=True, exist_ok=True)

    s = 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Match the SVG blue — looks fine on both light and dark menu bars
    color = (91, 184, 255, 230)
    node_r = 7
    lw = 4

    left = (s // 4,     s // 2)
    top  = (s - s // 5, s // 6)
    bot  = (s - s // 5, 5 * s // 6)

    d.line([left, top], fill=color, width=lw)
    d.line([left, bot], fill=color, width=lw)

    for cx, cy in (left, top, bot):
        d.ellipse([cx - node_r, cy - node_r, cx + node_r, cy + node_r], fill=color)

    img.save(_ICON_CACHE)
    return str(_ICON_CACHE)


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def _open_url(url: str) -> None:
    subprocess.Popen(["open", url])


def _notify(title: str, body: str) -> None:
    rumps.notification("Linkover", title, body, sound=False)


class TrayApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Linkover", icon=_ensure_icon(), quit_button=None)
        self._lock = threading.Lock()
        self._recent: deque[dict] = deque(maxlen=_MAX_RECENT)

        # Messages from the WebSocket thread are queued here and drained
        # by a timer on the main thread — rumps requires UI changes on main.
        self._pending: list[dict] = []
        self._pending_lock = threading.Lock()

        self._rebuild_menu()

        self._timer = rumps.Timer(self._drain_pending, 0.2)
        self._timer.start()

    # ------------------------------------------------------------------
    # Called from the WebSocket thread — enqueue only, no UI work here
    # ------------------------------------------------------------------

    def on_messages(self, messages: list[dict]) -> None:
        with self._pending_lock:
            self._pending.extend(messages)

    # ------------------------------------------------------------------
    # Internal — all UI work happens here, on the main thread via timer
    # ------------------------------------------------------------------

    def _drain_pending(self, _sender: rumps.Timer) -> None:
        with self._pending_lock:
            if not self._pending:
                return
            messages, self._pending = list(self._pending), []

        for msg in messages:
            self._handle_message(msg)
        self._rebuild_menu()

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
            _open_url(target)

    def _rebuild_menu(self) -> None:
        with self._lock:
            recent = list(self._recent)

        items: list = []

        if recent:
            for msg in recent:
                url = msg.get("url") or ""
                body = msg.get("message") or ""
                target = url if _is_url(url) else (body if _is_url(body) else None)
                label = (msg.get("title") or target or body or "Unknown")[:60]

                if target:
                    item = rumps.MenuItem(
                        label, callback=lambda _, t=target: _open_url(t)
                    )
                else:
                    item = rumps.MenuItem(label)
                items.append(item)
        else:
            items.append(rumps.MenuItem("No links yet"))

        items.append(None)  # separator
        items.append(rumps.MenuItem("Quit", callback=lambda _: rumps.quit_application()))

        self.menu.clear()
        self.menu = items

    def run(self) -> None:
        super().run()
