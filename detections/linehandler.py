"""Detection rules for parsed RageMP chat lines."""
import ctypes
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

from filehandler.readstorage import watch_chat


MatchFunc = Callable[[str, str, bool], bool]
ActionFunc = Callable[[str], None]
BASE_DIR = Path(__file__).resolve().parent.parent
SOUNDS_DIR = BASE_DIR / "sounds"
MENTION_SOUND = SOUNDS_DIR / "mentioned.wav"
PM_SOUND = SOUNDS_DIR / "incomingpm.wav"
REPORT_SOUND = SOUNDS_DIR / "newreport.wav"
_MCI_SEND_STRING = ctypes.windll.winmm.mciSendStringW
_PLAYBACK_ALIAS = "gtaw_admin_assistant_alert"


@dataclass(frozen=True)
class DetectionRule:
    name: str
    match: MatchFunc
    action: ActionFunc


def _play_sound(sound_path: Path) -> None:
    if not sound_path.exists():
        print(f"Missing sound file: {sound_path}")
        return

    close_result = _MCI_SEND_STRING(f"close {_PLAYBACK_ALIAS}", None, 0, 0)
    open_result = _MCI_SEND_STRING(
        f'open "{sound_path}" alias {_PLAYBACK_ALIAS}',
        None,
        0,
        0,
    )
    if open_result != 0:
        print(f"Unable to open sound file: {sound_path}")
        return

    play_result = _MCI_SEND_STRING(f"play {_PLAYBACK_ALIAS} from 0", None, 0, 0)
    if play_result != 0:
        print(f"Unable to play sound file: {sound_path}")
        _MCI_SEND_STRING(f"close {_PLAYBACK_ALIAS}", None, 0, 0)


def _report_detected(line: str) -> None:
    print(f"Detected admin-related line: New Player Report: {line}")
    _play_sound(REPORT_SOUND)

def _pm_detected(line: str) -> None:
    print(f"PM detected line: {line}")
    _play_sound(PM_SOUND)

def _mention_detected(line: str) -> None:
    print(f"Mention detected line: {line}")
    _play_sound(MENTION_SOUND)

def _test_detected(line: str) -> None:
    print(f"Test detection matched: {line}")


RULES: tuple[DetectionRule, ...] = (
    DetectionRule(
        name="player_report",
        match=lambda line, normalized_line, test_mode: "has submitted a report" in normalized_line,
        action=_report_detected,
    ),
    DetectionRule(
        name="private_message",
        match=lambda line, normalized_line, test_mode: "(( pm from (" in normalized_line,
        action=_pm_detected,
    ),
    DetectionRule(
        name="self_mention",
        match=lambda line, normalized_line, test_mode: "sebz" in normalized_line,
        action=_mention_detected,
    ),
    DetectionRule(
        name="test_log",
        match=lambda line, normalized_line, test_mode: test_mode and "testlog" in normalized_line,
        action=_test_detected,
    ),
)


def handle_line(line: str, test_mode: bool = False, debug: bool = False) -> None:
    normalized_line = line.lower()

    if debug:
        print(f"Received line: {line}")

    for rule in RULES:
        if rule.match(line, normalized_line, test_mode):
            if debug:
                print(f"Matched rule: {rule.name}")
            rule.action(line)


def main(test_mode: bool = False, debug: bool = False, replay_last: int = 0) -> None:
    for line in watch_chat(debug=debug, replay_last=replay_last):
        handle_line(line, test_mode=test_mode, debug=debug)


if __name__ == "__main__":
    main()
