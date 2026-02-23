# Linkover

A lightweight menu bar client for sharing links between your devices using [Pushover](https://pushover.net). Send a URL from your iPhone's share sheet and it instantly opens on your Linux desktop or Mac — no browser tab required, no always-on server to maintain.

Runs as a native tray/menu bar icon on **GNOME Linux** and **macOS**, with an **iOS Shortcut** as the sending side.

---

## Features

- **Real-time delivery** via Pushover's WebSocket API — no polling
- **Auto-opens** incoming links in your default browser
- **Menu bar icon** showing your last 10 received links, clickable to reopen
- **Desktop notifications** on arrival
- **iOS share sheet** integration via a one-tap Shortcut
- Tiny footprint — two pip dependencies, no Electron, no browser

---

## How it works

```
iPhone share sheet
      │
      ▼
iOS Shortcut  ──►  Pushover API  ──►  Linkover (WebSocket listener)
                                            │
                                     notify-send / rumps notification
                                            │
                                      xdg-open / open (browser)
```

Linkover registers itself with Pushover as an [Open Client](https://pushover.net/api/client), maintaining a persistent WebSocket connection. When a message arrives it shows a notification, opens the URL, and adds it to the menu.

---

## Requirements

### Pushover account

1. Create a free account at [pushover.net](https://pushover.net)
2. Note your **User Key** from the dashboard
3. Create an **App Token** at pushover.net/apps/build — name it anything (e.g. "Linkover iOS")

### Linux (GNOME)

- Bazzite, Fedora Atomic, or any GNOME distro
- [AppIndicator and KStatusNotifierItem Support](https://extensions.gnome.org/extension/615/appindicator-support/) GNOME extension — provides the menu bar slot
- `pipx` (installed automatically if missing)
- System `python3-gobject` / GTK — already present on any GNOME system

### macOS

- macOS 11 or later
- `pipx` — install via `brew install pipx`

---

## Installation

### Linux

```bash
git clone https://github.com/jdmills-edu/linkover.git
cd linkover
bash install.sh
```

Then run `linkover` once to complete first-time setup (Pushover login). After that it starts automatically on login via the XDG autostart entry at `~/.config/autostart/linkover.desktop`.

### macOS

```bash
git clone https://github.com/jdmills-edu/linkover.git
cd linkover
pipx install .
linkover
```

For autostart, add `linkover` to **System Settings → General → Login Items**.

> **Note:** The first notification will trigger a macOS permission prompt — allow it, or notifications will be silently suppressed.

---

## iOS Shortcut setup

This is the sending side. Create it once and it lives in your share sheet forever.

1. Open the **Shortcuts** app → tap **+**
2. **Add Action** → search "Receive" → **Receive input from Share Sheet**
   - Input types: **URLs**, **Safari web pages**, **Text**
3. **Add Action** → **Get URLs from Input**
4. **Add Action** → **Get Contents of URL**, configured as:
   - URL: `https://api.pushover.net/1/messages.json`
   - Method: **POST**
   - Request Body: **Form** with fields:

     | Key | Value |
     |-----|-------|
     | `token` | your App Token |
     | `user` | your User Key |
     | `message` | **URLs** variable (from step 3) |

5. Name the shortcut (e.g. **"Send to Desktop"**)

Now tap **Share → Send to Desktop** from any app to send the current URL to all your running Linkover instances.

---

## Configuration

Credentials are stored in `~/.config/linkover/config.json` after first-time setup. To re-run setup (e.g. to register a new device), delete that file and run `linkover` again.

To register Linkover on an additional machine, just install and run `linkover` — it will register a new device under the same Pushover account and both machines will receive every link you send.

---

## Project structure

```
linkover/
├── linkover/
│   ├── api.py          # Pushover REST calls (login, fetch, delete messages)
│   ├── client.py       # WebSocket thread with auto-reconnect
│   ├── tray_linux.py   # GNOME tray via AyatanaAppIndicator3 + GTK
│   ├── tray_mac.py     # macOS menu bar via rumps (NSStatusItem)
│   ├── config.py       # ~/.config/linkover/config.json
│   └── __main__.py     # Entry point, platform detection
├── linkover/icons/
│   └── linkover.svg    # Source icon (installed to hicolor theme on Linux)
├── install.sh          # Linux installer (pipx + icon + autostart)
└── linkover.desktop    # XDG autostart template
```

The three core modules (`api.py`, `client.py`, `config.py`) are fully cross-platform. Only the tray layer differs per OS.

---

## Updating

```bash
cd linkover
git pull
bash install.sh        # Linux
pipx install --force . # macOS
```
