# RAGE Player Assist

A Windows desktop application that monitors GTA RP (RageMP) in-game chat logs and triggers configurable sound alerts based on detection rules (private messages, name mentions, custom regex patterns).

## Tech Stack

- **Language:** Python 3.13+
- **GUI:** PySide6 (Qt6) - primary UI in `ui/qt_gui.py`; legacy Tkinter UI in `ui/gui.py`
- **Audio:** pygame with Windows MCI fallback
- **Packaging:** PyInstaller for standalone Windows executables
- **CI:** GitHub Actions (`release.yml`) builds and uploads release zips

## Project Structure

```
main.py                  # Entry point: CLI (--console) or GUI
config/app_config.py     # Dataclass-based config, JSON persistence
detections/linehandler.py # Detection engine, rule matching, sound playback
filehandler/readstorage.py # .storage file watcher (polling generator)
ui/qt_gui.py             # Primary PySide6 GUI
sounds/                  # Bundled .wav alert sounds
build_exe.ps1            # Local build script
rage_player_assist.spec  # PyInstaller spec
```

## Key Patterns

- **Config:** `AppConfig` dataclass saved to `app_config.json` via `load_config()`/`save_config()`. Config auto-saves on load to fill defaults.
- **Detection rules:** Three types: `contains` (substring), `mention` (word-boundary name match excluding speaker), `regex` (with flags). Each has cooldown, volume, category.
- **File watching:** `watch_chat()` is a polling generator (0.5s) that reads RageMP's `.storage` JSON file and yields new chat lines via overlap diffing.
- **Threading:** Watcher runs in a `QThread` (Qt GUI) or daemon `Thread` (Tkinter/console). Uses `threading.Event` for clean shutdown.
- **Audio fallback:** Tries pygame first, falls back to Windows MCI (`ctypes.windll.winmm`).
- **Frozen detection:** Uses `sys.frozen` / `sys._MEIPASS` to resolve resource paths in PyInstaller builds.

## Build & Run

```bash
# Development
python main.py              # Launch Qt GUI
python main.py --console    # Console mode
python main.py --debug      # Verbose logging

# Build executable
pip install -r requirements.txt
powershell ./build_exe.ps1
```

## Version

- `APP_VERSION` is defined in `config/app_config.py` (currently "1.0.1")

## Notes

- Windows-only (uses `ctypes.windll`, `os.startfile`)
- No test suite exists
