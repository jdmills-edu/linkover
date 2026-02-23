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
    """Draw a minimal chain-link icon for the system tray."""
    img = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    blue = (100, 180, 255, 255)
    lw = 7

    # Left ring
    d.ellipse([4, 18, 34, 46], outline=blue, width=lw)
    # Right ring
    d.ellipse([30, 18, 60, 46], outline=blue, width=lw)
    # Erase the inner overlap so the rings look interlinked
    d.rectangle([32, 24, 36, 40], fill=(0, 0, 0, 0))

    return img


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def _notify(title: str, body: str) -> None:
    try:
        subprocess.Popen(
            ["notify-send", "--icon=emblem-shared", "--app-name=Linkover", title, body]
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
