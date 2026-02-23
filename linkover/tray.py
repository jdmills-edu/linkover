import logging
import subprocess
import threading
import webbrowser
from collections import deque

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

_MAX_RECENT = 10
_ICON_SIZE = 64


def _build_icon_image() -> Image.Image:
    """Draw a white share icon for the GNOME dark top bar."""
    s = _ICON_SIZE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    color = (255, 255, 255, 230)
    node_r = 7
    lw = 4

    # Node positions — left hub, top-right, bottom-right
    left = (s // 4,         s // 2)
    top  = (s - s // 5,     s // 6)
    bot  = (s - s // 5, 5 * s // 6)

    # Lines drawn first so nodes sit on top
    d.line([left, top], fill=color, width=lw)
    d.line([left, bot], fill=color, width=lw)

    for cx, cy in (left, top, bot):
        d.ellipse([cx - node_r, cy - node_r, cx + node_r, cy + node_r], fill=color)

    return img


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


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
        self._icon = pystray.Icon(
            "linkover",
            _build_icon_image(),
            title="Linkover",
            menu=self._make_menu(),
        )

    # ------------------------------------------------------------------
    # Public interface called from the WebSocket thread
    # ------------------------------------------------------------------

    def on_messages(self, messages: list[dict]) -> None:
        for msg in messages:
            self._handle_message(msg)
        self._icon.menu = self._make_menu()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_message(self, msg: dict) -> None:
        """Process a single incoming Pushover message."""
        # Prefer the supplementary url field, fall back to the message body.
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
            webbrowser.open(target)

    def _make_menu(self) -> pystray.Menu:
        items: list[pystray.MenuItem] = []

        with self._lock:
            recent = list(self._recent)

        if recent:
            for msg in recent:
                url = msg.get("url") or ""
                body = msg.get("message") or ""
                target = url if _is_url(url) else (body if _is_url(body) else None)
                label = (msg.get("title") or target or body)[:50]

                if target:
                    items.append(
                        pystray.MenuItem(
                            label,
                            lambda _, t=target: webbrowser.open(t),
                        )
                    )
                else:
                    items.append(
                        pystray.MenuItem(label, None, enabled=False)
                    )
        else:
            items.append(pystray.MenuItem("No links yet", None, enabled=False))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self._quit))

        return pystray.Menu(*items)

    def _quit(self, icon: pystray.Icon) -> None:
        icon.stop()

    def run(self) -> None:
        self._icon.run()
