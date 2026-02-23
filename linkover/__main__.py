import getpass
import logging
import re
import socket
import sys

from . import api, config
from .client import PushoverClient

if sys.platform == "darwin":
    from .tray_mac import TrayApp
else:
    from .tray_linux import TrayApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _setup() -> dict:
    """Interactive first-run: log in and register this device with Pushover."""
    print("Linkover — first-time setup")
    print("Enter your Pushover account credentials:\n")

    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    try:
        result = api.login(email, password)
    except Exception as exc:
        msg = str(exc).lower()
        if "two" in msg or "twofa" in msg or "2fa" in msg:
            twofa = input("Two-factor code: ").strip()
            result = api.login(email, password, twofa)
        else:
            print(f"\nLogin failed: {exc}", file=sys.stderr)
            sys.exit(1)

    secret = result["secret"]

    hostname = socket.gethostname().split(".")[0]
    device_name = re.sub(r"[^a-zA-Z0-9_-]", "-", f"linkover-{hostname}")[:25]
    print(f"\nRegistering device as '{device_name}'…")

    try:
        device = api.register_device(secret, name=device_name)
    except Exception as exc:
        print(f"Device registration failed: {exc}", file=sys.stderr)
        sys.exit(1)

    cfg = {"secret": secret, "device_id": device["id"]}
    config.save(cfg)
    print(f"Done! Device registered as: {device['id']}\n")
    return cfg


def main() -> None:
    cfg = config.load()

    if not cfg.get("secret") or not cfg.get("device_id"):
        cfg = _setup()

    tray = TrayApp()
    ws = PushoverClient(cfg["secret"], cfg["device_id"], tray.on_messages)

    logger.info("Starting Linkover…")
    ws.start()

    # tray.run() blocks until the user clicks Quit
    tray.run()

    ws.stop()
    logger.info("Linkover stopped")


if __name__ == "__main__":
    main()
