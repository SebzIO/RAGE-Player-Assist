"""Utilities for reading and watching RageMP's `.storage` chat log."""
import json
import time
from pathlib import Path


STORAGE_FILE = Path(r"E:\RAGEMP\client_resources\cb242ee11d52ccd84309050503ab5242\.storage")


def _read_storage_data(storage_path: Path, retries: int = 3, retry_delay: float = 0.1) -> dict:
    """Read the JSON payload, tolerating transient partial writes from the game."""
    last_error = None

    for _ in range(retries):
        try:
            raw_text = storage_path.read_text(encoding="utf-8")
            return json.loads(raw_text)
        except (OSError, json.JSONDecodeError) as error:
            last_error = error
            time.sleep(retry_delay)

    if last_error is None:
        raise RuntimeError("Unable to read the storage file.")

    raise last_error


def read_chat_lines(storage_path: Path = STORAGE_FILE) -> list[str]:
    data = _read_storage_data(storage_path)
    chat_log = data.get("chat_log", "")
    return [line for line in chat_log.splitlines() if line.strip()]


def _find_new_lines(previous_lines: list[str], current_lines: list[str]) -> list[str]:
    """Return only lines not already represented in the previous snapshot."""
    if not previous_lines:
        return current_lines

    max_overlap = min(len(previous_lines), len(current_lines))
    for overlap in range(max_overlap, -1, -1):
        if overlap == 0:
            return current_lines

        if previous_lines[-overlap:] == current_lines[:overlap]:
            return current_lines[overlap:]

    return current_lines


def watch_chat(
    storage_path: Path = STORAGE_FILE,
    poll_interval: float = 0.5,
    start_from_end: bool = True,
    debug: bool = False,
    debug_heartbeat_interval: float = 5.0,
    replay_last: int = 0,
):
    previous_lines: list[str] = []
    last_debug_heartbeat = 0.0

    while True:
        try:
            lines = read_chat_lines(storage_path)

            if debug:
                now = time.monotonic()
                if now - last_debug_heartbeat >= debug_heartbeat_interval:
                    last_line = lines[-1] if lines else "<no chat lines>"
                    print(f"Watcher heartbeat: total_lines={len(lines)} last_line={last_line}")
                    last_debug_heartbeat = now

            if not previous_lines and start_from_end:
                if replay_last > 0 and lines:
                    replay_lines = lines[-replay_last:]
                    if debug:
                        print(f"Replaying last {len(replay_lines)} existing line(s).")
                    for line in replay_lines:
                        yield line

                previous_lines = lines
                if debug:
                    print(f"Watcher initialized with {len(lines)} existing chat lines.")
                time.sleep(poll_interval)
                continue

            new_lines = _find_new_lines(previous_lines, lines)

            if debug and new_lines:
                print(f"Watcher detected {len(new_lines)} new line(s).")

            for line in new_lines:
                yield line

            previous_lines = lines
        except (OSError, json.JSONDecodeError) as error:
            if debug:
                print(f"Watcher read failed: {error}")

        time.sleep(poll_interval)


if __name__ == "__main__":
    for chat_line in watch_chat():
        print(chat_line)
