import requests

_BASE = "https://api.pushover.net/1"


def login(email: str, password: str, twofa: str | None = None) -> dict:
    data = {"email": email, "password": password}
    if twofa:
        data["twofa"] = twofa
    r = requests.post(f"{_BASE}/users/login.json", data=data, timeout=15)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != 1:
        raise RuntimeError(f"Login failed: {body.get('errors', body)}")
    return body


def register_device(secret: str, name: str = "linkover") -> dict:
    r = requests.post(
        f"{_BASE}/devices.json",
        data={"secret": secret, "name": name, "os": "O"},
        timeout=15,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("status") != 1:
        raise RuntimeError(f"Device registration failed: {body.get('errors', body)}")
    return body


def fetch_messages(secret: str, device_id: str) -> list[dict]:
    r = requests.get(
        f"{_BASE}/messages.json",
        params={"secret": secret, "device_id": device_id},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("messages", [])


def delete_messages(secret: str, device_id: str, highest_id: int) -> None:
    requests.post(
        f"{_BASE}/devices/{device_id}/update_highest_message.json",
        data={"secret": secret, "highest_message_id": highest_id},
        timeout=15,
    ).raise_for_status()


def acknowledge(secret: str, receipt_id: str) -> None:
    requests.post(
        f"{_BASE}/receipts/{receipt_id}/acknowledge.json",
        data={"secret": secret},
        timeout=15,
    ).raise_for_status()
