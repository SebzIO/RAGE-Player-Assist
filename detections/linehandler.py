"""Config-driven detection rules for parsed RageMP chat lines."""
from __future__ import annotations

import ctypes
import re
import time
from pathlib import Path
from threading import Event
from typing import Callable

from config.app_config import AppConfig, CategoryOverride, DetectionConfig, load_config
from filehandler.readstorage import watch_chat


LogFunc = Callable[[str], None]
_MCI_SEND_STRING = ctypes.windll.winmm.mciSendStringW
_PLAYBACK_ALIAS = "gtaw_player_assistant_alert"

try:
    import pygame
except ImportError:
    pygame = None

_PYGAME_READY = False


def _default_logger(message: str) -> None:
    print(message)


def _init_pygame_audio(logger: LogFunc) -> bool:
    global _PYGAME_READY

    if pygame is None:
        return False

    if _PYGAME_READY:
        return True

    try:
        pygame.mixer.init()
    except Exception as error:
        logger(f"pygame audio init failed, using Windows fallback: {error}")
        return False

    _PYGAME_READY = True
    return True


def _play_sound_with_pygame(sound_path: Path, logger: LogFunc, volume_percent: int) -> bool:
    if not _init_pygame_audio(logger):
        return False

    try:
        sound = pygame.mixer.Sound(str(sound_path))
        sound.set_volume(max(0, min(100, volume_percent)) / 100.0)
        sound.play()
        return True
    except Exception as error:
        logger(f"pygame playback failed, using Windows fallback: {error}")
        return False


def _play_sound_with_mci(sound_path: Path, logger: LogFunc, volume_percent: int) -> None:
    _MCI_SEND_STRING(f"close {_PLAYBACK_ALIAS}", None, 0, 0)
    media_type = "mpegvideo" if sound_path.suffix.lower() == ".mp3" else "waveaudio"
    open_result = _MCI_SEND_STRING(
        f'open "{sound_path}" type {media_type} alias {_PLAYBACK_ALIAS}',
        None,
        0,
        0,
    )
    if open_result != 0:
        logger(f"Unable to open sound file: {sound_path}")
        return

    clamped_volume = max(0, min(100, int(volume_percent)))
    volume_result = _MCI_SEND_STRING(
        f"setaudio {_PLAYBACK_ALIAS} volume to {clamped_volume * 10}",
        None,
        0,
        0,
    )
    if volume_result != 0:
        logger(f"Unable to set sound volume for: {sound_path}")

    play_result = _MCI_SEND_STRING(f"play {_PLAYBACK_ALIAS} from 0", None, 0, 0)
    if play_result != 0:
        logger(f"Unable to play sound file: {sound_path}")
        _MCI_SEND_STRING(f"close {_PLAYBACK_ALIAS}", None, 0, 0)


def _play_sound(sound_path: str, logger: LogFunc, volume_percent: int = 100, muted: bool = False) -> None:
    if muted:
        return

    if not sound_path:
        return

    file_path = Path(sound_path)
    if not file_path.exists():
        logger(f"Missing sound file: {file_path}")
        return

    if _play_sound_with_pygame(file_path, logger, volume_percent):
        return

    _play_sound_with_mci(file_path, logger, volume_percent)


def play_sound_file(
    sound_path: str,
    logger: LogFunc | None = None,
    volume_percent: int = 100,
    muted: bool = False,
) -> None:
    _play_sound(sound_path, logger or _default_logger, volume_percent=volume_percent, muted=muted)


def _strip_chat_timestamp(line: str) -> str:
    return re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s*", "", line, count=1)


def _extract_message_body(line: str) -> str:
    content = _strip_chat_timestamp(line).strip()
    if ": " not in content:
        return ""
    _speaker, message = content.split(": ", 1)
    return message.strip()


def _contains_name_reference(text: str, name: str) -> bool:
    if not text or not name:
        return False
    pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _extract_speaker_segment(line: str) -> str:
    content = _strip_chat_timestamp(line).strip()
    if ": " not in content:
        return ""
    speaker, _message = content.split(": ", 1)
    return speaker.strip()


def _matches_detection(
    detection: DetectionConfig,
    line: str,
    normalized_line: str,
    mention_name: str,
) -> bool:
    if not detection.enabled:
        return False

    if detection.rule_type == "contains":
        return bool(detection.pattern) and detection.pattern.lower() in normalized_line

    if detection.rule_type == "mention":
        speaker = _extract_speaker_segment(line)
        if _contains_name_reference(speaker, mention_name):
            return False
        return _contains_name_reference(_extract_message_body(line), mention_name)

    if detection.rule_type == "regex":
        if not detection.pattern:
            return False
        try:
            flags = 0
            if not detection.regex_case_sensitive:
                flags |= re.IGNORECASE
            if detection.regex_multiline:
                flags |= re.MULTILINE
            if detection.regex_dotall:
                flags |= re.DOTALL
            return re.search(detection.pattern, line, flags) is not None
        except re.error:
            return False

    return False


def _category_override_for(config: AppConfig, category: str) -> CategoryOverride | None:
    for override in config.category_overrides:
        if override.category == category:
            return override
    return None


def get_matching_detections(line: str, config: AppConfig) -> list[DetectionConfig]:
    normalized_line = line.lower()
    return [
        detection
        for detection in config.detections
        if _matches_detection(detection, line, normalized_line, config.mention_name)
    ]


def handle_line(
    line: str,
    config: AppConfig,
    debug: bool = False,
    logger: LogFunc | None = None,
    last_triggered: dict[str, float] | None = None,
    play_sound: bool = True,
) -> None:
    log = logger or _default_logger
    normalized_line = line.lower()
    cooldown_tracker = last_triggered if last_triggered is not None else {}

    if debug:
        log(f"Received line: {line}")

    for detection in config.detections:
        if _matches_detection(detection, line, normalized_line, config.mention_name):
            now = time.monotonic()
            last_match_time = cooldown_tracker.get(detection.id, 0.0)
            if detection.cooldown_seconds > 0 and now - last_match_time < detection.cooldown_seconds:
                if debug:
                    remaining = detection.cooldown_seconds - (now - last_match_time)
                    log(f"Suppressed by cooldown: {detection.name} ({remaining:.1f}s remaining)")
                continue

            cooldown_tracker[detection.id] = now
            if debug:
                log(f"Matched rule: {detection.name}")

            prefix = detection.log_message.strip() or f"Detected line for {detection.name}"
            log(f"[{detection.category}] {prefix}: {line}")
            category_override = _category_override_for(config, detection.category)
            effective_muted = config.global_mute or (category_override.muted if category_override else False)
            effective_volume = (
                category_override.volume_percent
                if category_override and category_override.use_volume_override
                else detection.volume_percent
            )
            if play_sound:
                _play_sound(
                    detection.sound_path,
                    log,
                    volume_percent=effective_volume,
                    muted=effective_muted,
                )


def main(
    config: AppConfig | None = None,
    debug: bool = False,
    replay_last: int = 0,
    logger: LogFunc | None = None,
    stop_event: Event | None = None,
) -> None:
    active_config = config or load_config()
    log = logger or _default_logger
    storage_path = Path(active_config.storage_path)
    last_triggered: dict[str, float] = {}

    for line in watch_chat(
        storage_path=storage_path,
        debug=debug,
        replay_last=replay_last,
        stop_event=stop_event,
        logger=log,
    ):
        handle_line(
            line,
            config=active_config,
            debug=debug,
            logger=log,
            last_triggered=last_triggered,
        )


if __name__ == "__main__":
    main()
