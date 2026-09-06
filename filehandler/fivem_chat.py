"""FiveM / GTAW chat watcher that tails the GTAW Assistant session file.

GTAW Assistant (FiveM adaptation) captures GTA World chat via FiveM's local NUI
DevTools endpoint and appends lines to:

    %LOCALAPPDATA%\\GTAW-Log-Parser-FiveM\\current-session.txt

Format per FiveMChatCaptureController.cs:
    [DATE: DD/MMM/YYYY | TIME: HH:MM:SS]   <- header, first line of session
    [HH:MM:SS] <message>                  <- one per captured NUI line

This module mirrors filehandler/readstorage.py's public API (watch_chat) but
reads the plain-text session file instead of RAGE's JSON .storage. It is
deliberately a polling tailer so it can run without filesystem watchers.

Reuse target: can be imported directly by detections/linehandler.py and by the
GUI without changing existing RAGE logic.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from threading import Event
from typing import Callable

LogFunc = Callable[[str], None]

# Default GTAW FiveM session path - see FiveMChatCaptureController.SessionFile
FIVEM_SESSION_FILE = Path(os.environ.get("LOCALAPPDATA", "")) / "GTAW-Log-Parser-FiveM" / "current-session.txt"

# Fallback if LOCALAPPDATA missing (unlikely on Windows)
if not os.environ.get("LOCALAPPDATA"):
    FIVEM_SESSION_FILE = Path.home() / "AppData" / "Local" / "GTAW-Log-Parser-FiveM" / "current-session.txt"

# Regexes to identify non-chat control lines written by the capturer
_DATE_HEADER_RE = re.compile(r"^\[DATE:\s*\d{2}/[A-Za-z]{3}/\d{4}\s*\|\s*TIME:\s*\d{2}:\d{2}:\d{2}\]\s*$")
# The watcher tolerates both 1-2 digit hour captures - GTAW header uses HH, NUI inject may vary
_TIMESTAMP_PREFIX_RE = re.compile(r"^\[\d{1,2}:\d{2}:\d{2}\]\s*")


def _default_logger(message: str) -> None:
    print(message)


def _read_fivem_lines(session_path: Path) -> list[str]:
    """Read the session file, return cleaned chat lines (header stripped, blanks removed)."""
    if not session_path.exists():
        return []
    try:
        # Use shared read so we don't collide with GTAW Assistant's FileShare.ReadWrite writer
        # Python's read_text opens with default sharing; on Windows that's tolerant.
        # For extra safety, read via open with errors=replace.
        text = session_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if _DATE_HEADER_RE.match(stripped):
            continue
        lines.append(raw.rstrip("\r\n"))
    return lines


def read_fivem_chat_lines(session_path: Path = FIVEM_SESSION_FILE) -> list[str]:
    """Public helper: return current cleaned lines without polling."""
    return _read_fivem_lines(session_path)


def _find_new_lines(previous_lines: list[str], current_lines: list[str]) -> list[str]:
    """Overlap diff identical to readstorage._find_new_lines - handles log truncation/rotation."""
    if not previous_lines:
        return current_lines
    anchor = previous_lines[-1]
    max_overlap = min(len(previous_lines), len(current_lines))
    for candidate_pos in range(max_overlap - 1, -1, -1):
        if current_lines[candidate_pos] != anchor:
            continue
        overlap = candidate_pos + 1
        if overlap <= len(previous_lines) and previous_lines[-overlap:] == current_lines[:overlap]:
            return current_lines[overlap:]
    return current_lines


def discover_fivem_session_paths() -> list[Path]:
    """Return candidate GTAW session files that exist on this machine."""
    candidates: list[Path] = []
    seen: set[str] = set()

    # Primary location
    if FIVEM_SESSION_FILE.exists() and FIVEM_SESSION_FILE.is_file():
        candidates.append(FIVEM_SESSION_FILE)
        seen.add(str(FIVEM_SESSION_FILE).lower())

    # Also check every drive's Users\<user>\AppData\Local for multi-user machines
    # Lightweight: just check LOCALAPPDATA already covers current user
    return candidates


def watch_fivem_chat(
    session_path: Path = FIVEM_SESSION_FILE,
    poll_interval: float = 0.5,
    start_from_end: bool = True,
    debug: bool = False,
    debug_heartbeat_interval: float = 5.0,
    replay_last: int = 0,
    stop_event: Event | None = None,
    logger: LogFunc | None = None,
):
    """Polling generator that yields new FiveM chat lines as they appear.

    Mirrors filehandler.readstorage.watch_chat signature so the GUI/handler can
    swap sources with a single branch.
    """
    previous_lines: list[str] = []
    last_debug_heartbeat = 0.0
    log = logger or _default_logger

    while stop_event is None or not stop_event.is_set():
        try:
            lines = _read_fivem_lines(session_path)

            if debug:
                now = time.monotonic()
                if now - last_debug_heartbeat >= debug_heartbeat_interval:
                    last_line = lines[-1] if lines else "<no chat lines>"
                    log(f"[FiveM] heartbeat: total_lines={len(lines)} last_line={last_line}")
                    last_debug_heartbeat = now

            if not previous_lines and start_from_end:
                if replay_last > 0 and lines:
                    replay_lines = lines[-replay_last:]
                    if debug:
                        log(f"[FiveM] replaying last {len(replay_lines)} line(s).")
                    for line in replay_lines:
                        yield line
                previous_lines = lines
                if debug:
                    log(f"[FiveM] watcher initialized with {len(lines)} existing lines @ {session_path}")
                if stop_event is not None and stop_event.wait(poll_interval):
                    break
                if stop_event is None:
                    time.sleep(poll_interval)
                continue

            new_lines = _find_new_lines(previous_lines, lines)

            # Also handle truncation / session reset: if file shrank, treat as new session
            if len(lines) < len(previous_lines) and len(new_lines) == len(lines):
                if debug:
                    log(f"[FiveM] detected session reset/truncation ({len(previous_lines)} -> {len(lines)} lines)")
                # _find_new_lines already returned full current lines in this case

            if debug and new_lines:
                log(f"[FiveM] detected {len(new_lines)} new line(s).")

            for line in new_lines:
                yield line

            previous_lines = lines
        except OSError as error:
            if debug:
                log(f"[FiveM] read failed: {error}")

        if stop_event is not None:
            if stop_event.wait(poll_interval):
                break
        else:
            time.sleep(poll_interval)


if __name__ == "__main__":
    # Quick manual smoke-test: tail the session file
    target = FIVEM_SESSION_FILE
    print(f"Tailing FiveM GTAW session: {target}")
    print(f"Exists: {target.exists()}  Size: {target.stat().st_size if target.exists() else 0} bytes")
    for chat_line in watch_fivem_chat(debug=True, replay_last=3):
        print(chat_line)
