import logging
import threading
import time
from collections.abc import Callable

import websocket

from . import api, config

logger = logging.getLogger(__name__)

_WS_URL = "wss://client.pushover.net/push"
_RECONNECT_DELAY = 5  # seconds


class PushoverClient(threading.Thread):
    """Background thread that maintains the Pushover WebSocket connection."""

    def __init__(
        self,
        cfg: dict,
        on_messages: Callable[[list[dict], bool], None],
    ) -> None:
        super().__init__(daemon=True, name="pushover-ws")
        self._cfg = cfg
        self.on_messages = on_messages
        self._stop = threading.Event()
        self._ws: websocket.WebSocketApp | None = None
        self._is_first_fetch = True
        self._last_seen_id: int = cfg.get("last_seen_id", 0)

    def stop(self) -> None:
        self._stop.set()
        if self._ws:
            self._ws.close()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect()
            except Exception:
                logger.exception("Unexpected WebSocket error")
            if not self._stop.is_set():
                logger.info("Reconnecting in %ds…", _RECONNECT_DELAY)
                time.sleep(_RECONNECT_DELAY)

    def _connect(self) -> None:
        def on_open(ws: websocket.WebSocketApp) -> None:
            logger.info("WebSocket open — logging in")
            ws.send(f"login:{self._cfg['device_id']}:{self._cfg['secret']}\n")

        def on_message(ws: websocket.WebSocketApp, raw: bytes | str) -> None:
            signal = raw.decode() if isinstance(raw, bytes) else raw
            signal = signal.strip()
            if signal == "!":
                self._fetch_and_deliver()
            elif signal == "R":
                logger.info("Server requested reconnect")
                ws.close()
            elif signal == "E":
                logger.error("Server sent error — reconnecting")
                ws.close()
            # "#" is a keepalive heartbeat — nothing to do

        def on_error(ws: websocket.WebSocketApp, err: Exception) -> None:
            logger.error("WebSocket error: %s", err)

        def on_close(ws: websocket.WebSocketApp, code: int, msg: str) -> None:
            logger.info("WebSocket closed (code=%s)", code)

        self._ws = websocket.WebSocketApp(
            _WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self._ws.run_forever(ping_interval=30, ping_timeout=10)

    def _fetch_and_deliver(self) -> None:
        is_initial = self._is_first_fetch
        self._is_first_fetch = False

        try:
            messages = api.fetch_messages(self._cfg["secret"], self._cfg["device_id"])
        except Exception:
            logger.exception("Failed to fetch messages")
            return

        if not messages:
            return

        highest = max(m["id"] for m in messages)

        # Filter to only messages we haven't seen yet.  _last_seen_id is now
        # persisted across restarts, so cleared/old messages never reappear.
        to_deliver = [m for m in messages if m["id"] > self._last_seen_id]
        self._last_seen_id = max(self._last_seen_id, highest)

        # Persist so the next startup knows where we left off.
        self._cfg["last_seen_id"] = self._last_seen_id
        config.save(self._cfg)

        if to_deliver:
            try:
                self.on_messages(to_deliver, is_initial)
            except Exception:
                logger.exception("on_messages callback raised")

        try:
            api.delete_messages(self._cfg["secret"], self._cfg["device_id"], highest)
        except Exception:
            logger.exception("Failed to delete messages")
