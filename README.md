# RAGE Player Assist

RAGE Player Assist is a Windows desktop companion for monitoring a RageMP `.storage` chat feed and surfacing the lines that matter.

It is built for situations where important chat activity can be easy to miss: private messages, name mentions, staff-related keywords, reports, or any custom pattern you want to track. Instead of watching the game window constantly, you can let the app monitor the feed in real time and alert you when a configured rule matches.

The project is local-first, lightweight in scope, and designed to keep working while the game is unfocused, minimized, or alt-tabbed.

## What This Project Is

At its core, RAGE Player Assist is a configurable chat watcher:

- it reads a RageMP `.storage` file as new lines are written
- it compares those lines against user-defined detection rules
- it logs matches and can play sounds when those rules fire
- it can stay running in the background through the system tray

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

- real-time monitoring of a RageMP `.storage` file
- detection rules using `contains`, `mention`, and `regex`
- per-rule sound files
- per-rule cooldowns
- per-rule volume controls
- category-based mute and volume overrides
- global mute support
- a PySide6 desktop GUI
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

1. Choose the RageMP `.storage` file to monitor.
2. Set your mention name if you plan to use mention-based detections.
3. Review the default detection rules.
4. Save your configuration.
5. Start the watcher.

If no config exists yet, the app creates `app_config.json` automatically.

## Using The App

The GUI is the primary interface.

From the main window, you can:

- choose the storage file
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

The main config file is `app_config.json`.

It stores:

- the selected storage file path
- your mention name
- theme selection
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
- `config/`: config loading, defaults, and persistence
- `detections/`: detection and sound logic
- `filehandler/`: chat/storage watcher logic
- `ui/`: desktop UI
- `sounds/`: bundled alert sounds
- `build_exe.ps1`: local build script
- `rage_player_assist.spec`: PyInstaller spec

## Technical Notes

- The app is Windows-focused.
- The packaged GUI build runs without a console window.
- Sound playback uses `pygame` when available and falls back to Windows media APIs.
- The app is local and file-based; it does not require a backend service.
