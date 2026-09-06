# RAGE Player Assist

RAGE Player Assist is a Windows desktop companion for monitoring RageMP **and** FiveM GTAW chat feeds and surfacing the lines that matter. v1.1.0 adds cross-compatible FiveM support via GTAW Assistant.

It is built for situations where important chat activity can be easy to miss: private messages, name mentions, staff-related keywords, reports, or any custom pattern you want to track. Instead of watching the game window constantly, you can let the app monitor the feed in real time and alert you when a configured rule matches.

The project is local-first, lightweight in scope, and designed to keep working while the game is unfocused, minimized, or alt-tabbed.

## What This Project Is

At its core, RAGE Player Assist is a configurable chat watcher:

- it reads a RageMP `.storage` file **or** a FiveM GTAW log (via GTAW Assistant) as new lines are written
- it compares those lines against user-defined detection rules
- it logs matches and can play sounds when those rules fire
- it can stay running in the background through the system tray

Chat sources are selectable in the GUI and `app_config.json:chat_source` (`ragemp` | `fivem`):

- **RAGE MP**: tails the `.storage` JSON `chat_log` ( `filehandler/readstorage.py:37` )
- **FiveM (GTAW) file-tail**: tails `%LOCALAPPDATA%\GTAW-Log-Parser-FiveM\current-session.txt` written by GTAW Assistant (`filehandler/fivem_chat.py:48`)
- **FiveM Live NUI** (no file): forks GTAW Assistant's `NuiChatReader` — polls `http://127.0.0.1:13172/json` → `nui://game/ui/root.html` → `https://cfx-nui-client...` → `Runtime.evaluate` on `.chat__messages > li` (`filehandler/fivem_live.py:1`). Requires FiveM + GTAW HUD; `websocket-client` is optional otherwise falls back to file-tail.

This makes it useful for staff workflows, moderation workflows, and any playstyle where fast awareness matters more than constantly scanning chat manually.

## Who It Is For

RAGE Player Assist is most useful for:

- server admins and moderators
- staff members watching private messages or reports
- players who want audible alerts for direct mentions
- anyone who needs custom monitoring on top of RageMP chat output

If you already know exactly which chat events you care about, this app is meant to let you encode those events into rules and stop depending on constant manual attention.

## Feature Overview

The current app includes:

- real-time monitoring of a RageMP `.storage` file **and** FiveM GTAW logs (v1.1.0)
- chat-source selector (RAGE MP vs FiveM GTAW) with Live NUI vs file-tail toggle
- detection rules using `contains`, `mention`, and `regex`
- per-rule sound files
- per-rule cooldowns
- per-rule volume controls
- category-based mute and volume overrides
- global mute support
- a PySide6 desktop GUI (theme auto-saves on switch)
- system tray support for background use
- optional file logging
- config import and export
- console mode for non-GUI usage

Starter detections are included for private messages and mentions.

## How Detection Works

Each incoming line is evaluated against enabled detections in your config.

Supported rule types:

- `contains`: matches a plain text fragment anywhere in the line
- `mention`: matches your configured mention name inside the message body
- `regex`: matches using a regular expression with optional flags

Each detection can define:

- a display name
- a category
- whether it is enabled
- a pattern or rule type
- a sound file
- a log label
- a cooldown
- a volume level
- regex options where applicable

This gives you enough control to build simple alerting or more specific pattern-based monitoring depending on how structured your server chat is.

## Installation

### Download a Release

If a packaged release is available, you can choose between:

- a portable Windows zip
- a Windows `.msi` installer

The portable zip is for users who want to place the app wherever they like and keep it self-contained.

The `.msi` installer is for users who want a standard Windows install and uninstall flow.

If you choose the portable package, download the Windows zip from the repository’s Releases page.

After extracting it, keep these together in the same folder:

- `RAGE Player Assist.exe`
- `_internal/`

Then launch `RAGE Player Assist.exe`.

Because the executable is currently unsigned, Windows SmartScreen may show a warning before first launch. That is expected for unsigned desktop applications distributed outside the Microsoft Store. If you are downloading the build from this repository’s official Releases page, that warning is about the missing code-signing certificate rather than proof that the app is malicious.

If you choose the installer package, run the `.msi` file and follow the Windows Installer prompts. Uninstall is handled through the normal Windows installed apps/programs flow.

### Run From Source

Requirements:

- Windows
- Python 3.13

Setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\main.py
```

Console mode:

```powershell
python .\main.py --console
```

Useful flags:

- `--debug` prints watcher activity and parsed lines
- `--replay-last N` replays the last `N` parsed lines on startup

Example:

```powershell
python .\main.py --console --debug --replay-last 25
```

## First-Time Setup

On first launch:

1. Choose your chat source: **RAGE MP** or **FiveM (GTAW)**.
2. Pick the log: RAGE `.storage` file (auto-detect available) or FiveM `current-session.txt` (`%LOCALAPPDATA%\GTAW-Log-Parser-FiveM\current-session.txt` auto-detect) — or enable **Live NUI (127.0.0.1:13172)** for direct FiveM DevTools polling (no file needed, fork of GTAW Assistant).
3. Set your mention name if you plan to use mention-based detections.
4. Review the default detection rules.
5. Save your configuration.
6. Start the watcher.

If no config exists yet, the app creates `app_config.json` automatically.

## Using The App

The GUI is the primary interface.

From the main window, you can:

- choose the chat source (RAGE MP / FiveM GTAW) and Live NUI vs file-tail
- choose the storage file (RAGE) or FiveM session file (auto-detect) 
- define your mention name
- start and stop the watcher
- enable debug logging
- replay recent lines on startup
- add, edit, and remove detections
- browse for custom sound files
- test sounds before saving
- adjust cooldowns and volume
- group detections by category
- apply category-wide mute or volume overrides
- import and export configs
- open the config and log folders

If tray support is available and close-to-tray is enabled, closing the window hides the app instead of shutting it down. That allows the watcher to keep running in the background.

## Configuration And Data

The main config file is `app_config.json` (`%LOCALAPPDATA%\RAGE Player Assist\app_config.json` when installed, else next to exe).

It stores:

- `chat_source` (`ragemp` | `fivem`) and `fivem_use_live_nui`
- the selected storage file path (`storage_path` for RAGE) and FiveM session path (`fivem_session_path`, default `%LOCALAPPDATA%\GTAW-Log-Parser-FiveM\current-session.txt`)
- your mention name
- theme selection (auto-saves on switch)
- mute settings
- logging settings
- category overrides
- all configured detections

You can manage this through the GUI, or export and import config files when needed.

## Logging

The app can write logs to `Logs/` next to the application unless you set a custom log directory.

This is useful for reviewing what matched, when alerts fired, and how the watcher behaved over time.

## Building

This project uses PyInstaller for packaging.

To build locally:

```powershell
.\build_exe.ps1
```

The packaged application is produced in `dist\RAGE Player Assist\`.

For distribution, the important packaged contents are:

- `dist\RAGE Player Assist\RAGE Player Assist.exe`
- `dist\RAGE Player Assist\_internal\`

The extra top-level executable that may appear directly under `dist\` is not the intended release artifact.

## Releases

The repository includes a GitHub Actions workflow at `.github/workflows/release.yml`.

That workflow is intended to:

- build the Windows package
- produce a portable zip
- produce an `.msi` installer
- upload both to a GitHub release

Typical release flow:

1. Push your changes to `main`.
2. Create or publish a GitHub release with a version tag.
3. Let GitHub Actions build and attach the Windows zip.

If needed, the workflow can also be run manually against an existing release tag.

## Project Structure

Important files and folders:

- `main.py`: application entry point
- `config/`: config loading, defaults, and persistence (`app_config.py:114` now includes FiveM fields)
- `detections/`: detection and sound logic (`linehandler.py:309` branches RAGE vs FiveM watchers)
- `filehandler/`: chat/storage watcher logic (`readstorage.py`, `fivem_chat.py:48`, `fivem_live.py:1` fork of GTAW Assistant)
- `ui/`: desktop UI (`qt_gui.py:53` source selector + first-time setup cross-compat)
- `sounds/`: bundled alert sounds
- `build_exe.ps1`: local build script
- `rage_player_assist.spec`: PyInstaller spec

## Technical Notes

- The app is Windows-focused.
- The packaged GUI build runs without a console window.
- Sound playback uses `pygame` when available and falls back to Windows media APIs.
- The app is local and file-based; it does not require a backend service.
- FiveM Live NUI is a read-only localhost CDP WebSocket (`ws://127.0.0.1:13172`, `nui://game/ui/root.html` → `https://cfx-nui-client...`) — same source GTAW Assistant uses. Requires `websocket-client` (`requirements.txt:4`); file-tail works without it.
