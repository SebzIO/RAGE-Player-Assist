"""Persistent configuration for the RAGE Player Assist app."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _is_installed_build() -> bool:
    if not getattr(sys, "frozen", False):
        return False

    app_dir = _app_base_dir()
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        raw_root = os.environ.get(env_name, "").strip()
        if not raw_root:
            continue
        try:
            if app_dir.is_relative_to(Path(raw_root).resolve()):
                return True
        except (OSError, ValueError):
            continue
    return False


def _data_base_dir() -> Path:
    if _is_installed_build():
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data).resolve() / "RAGE Player Assist"
    return _app_base_dir()


def _resource_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        internal_dir = executable_dir / "_internal"
        if internal_dir.exists():
            return internal_dir

    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir).resolve()
    return Path(__file__).resolve().parent.parent


APP_DIR = _data_base_dir()
INSTALL_DIR = _app_base_dir()
RESOURCE_DIR = _resource_base_dir()
CONFIG_FILE = APP_DIR / "app_config.json"
DEFAULT_STORAGE_PATH = ""
APP_NAME = "RAGE Player Assist"
SOURCE_APP_VERSION = "1.0.4"
GITHUB_OWNER = "SebzIO"
GITHUB_REPO = "AdminAssist"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


def _load_build_metadata() -> dict[str, str]:
    metadata_path = RESOURCE_DIR / "build_metadata.json"
    if not metadata_path.exists():
        return {}

    try:
        raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return {str(key): str(value) for key, value in raw_metadata.items() if value not in (None, "")}


BUILD_METADATA = _load_build_metadata()
APP_VERSION = BUILD_METADATA.get("version", SOURCE_APP_VERSION)


@dataclass
class DetectionConfig:
    id: str
    name: str
    category: str
    rule_type: str
    pattern: str = ""
    enabled: bool = True
    sound_path: str = ""
    log_message: str = ""
    cooldown_seconds: float = 0.0
    volume_percent: int = 100
    regex_case_sensitive: bool = False
    regex_multiline: bool = False
    regex_dotall: bool = False


@dataclass
class CategoryOverride:
    category: str
    muted: bool = False
    use_volume_override: bool = False
    volume_percent: int = 100


@dataclass
class AppConfig:
    storage_path: str = DEFAULT_STORAGE_PATH
    mention_name: str = ""
    global_mute: bool = False
    theme: str = "Latte Light"
    close_to_tray_on_close: bool = True
    start_watcher_on_launch: bool = False
    file_logging_enabled: bool = False
    log_directory: str = ""
    log_debug_to_file: bool = False
    category_overrides: list[CategoryOverride] = field(default_factory=list)
    detections: list[DetectionConfig] = field(default_factory=list)


def _default_detections() -> list[DetectionConfig]:
    sounds_dir = RESOURCE_DIR / "sounds"
    return [
        DetectionConfig(
            id=uuid4().hex,
            name="Private Message",
            category="Messages",
            rule_type="contains",
            pattern="(( pm from (",
            sound_path=str(sounds_dir / "incomingpm.wav"),
            log_message="PM detected line",
            cooldown_seconds=2.0,
            volume_percent=100,
            regex_case_sensitive=False,
            regex_multiline=False,
            regex_dotall=False,
        ),
        DetectionConfig(
            id=uuid4().hex,
            name="Mention",
            category="Messages",
            rule_type="mention",
            sound_path=str(sounds_dir / "mentioned.wav"),
            log_message="Mention detected line",
            cooldown_seconds=2.0,
            volume_percent=100,
            regex_case_sensitive=False,
            regex_multiline=False,
            regex_dotall=False,
        ),
    ]


def default_config() -> AppConfig:
    return AppConfig(detections=_default_detections())


def default_logs_directory() -> Path:
    return APP_DIR / "Logs"


def build_stamp() -> str:
    metadata_stamp = BUILD_METADATA.get("built_at_utc")
    if metadata_stamp:
        return metadata_stamp

    reference_path = Path(sys.executable) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent / "main.py"
    try:
        modified = datetime.fromtimestamp(reference_path.stat().st_mtime)
        return modified.strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "Unknown"


def build_details() -> list[str]:
    details: list[str] = []

    release_tag = BUILD_METADATA.get("release_tag")
    if release_tag:
        details.append(f"Release tag: {release_tag}")

    commit_sha = BUILD_METADATA.get("commit_sha")
    if commit_sha:
        details.append(f"Commit: {commit_sha}")

    return details


def load_config(config_path: Path = CONFIG_FILE) -> AppConfig:
    if not config_path.exists():
        config = default_config()
        save_config(config, config_path)
        return config

    data = json.loads(config_path.read_text(encoding="utf-8"))
    detections = [
        DetectionConfig(
            id=item.get("id", uuid4().hex),
            name=item.get("name", "Unnamed Detection"),
            category=item.get("category", "General"),
            rule_type=item.get("rule_type", "contains") if item.get("rule_type", "contains") in {"contains", "mention", "regex"} else "contains",
            pattern=item.get("pattern", ""),
            enabled=item.get("enabled", True),
            sound_path=_resolve_sound_path(item.get("sound_path", "")),
            log_message=item.get("log_message", ""),
            cooldown_seconds=_coerce_cooldown(item.get("cooldown_seconds", 0.0)),
            volume_percent=_coerce_volume(item.get("volume_percent", 100)),
            regex_case_sensitive=bool(item.get("regex_case_sensitive", False)),
            regex_multiline=bool(item.get("regex_multiline", False)),
            regex_dotall=bool(item.get("regex_dotall", False)),
        )
        for item in data.get("detections", [])
    ]
    category_overrides = [
        CategoryOverride(
            category=str(item.get("category", "General")),
            muted=bool(item.get("muted", False)),
            use_volume_override=bool(item.get("use_volume_override", False)),
            volume_percent=_coerce_volume(item.get("volume_percent", 100)),
        )
        for item in data.get("category_overrides", [])
    ]

    config = AppConfig(
        storage_path=data.get("storage_path", DEFAULT_STORAGE_PATH),
        mention_name=data.get("mention_name", ""),
        global_mute=bool(data.get("global_mute", False)),
        theme=str(data.get("theme", "Latte Light")),
        close_to_tray_on_close=bool(data.get("close_to_tray_on_close", True)),
        start_watcher_on_launch=bool(data.get("start_watcher_on_launch", False)),
        file_logging_enabled=bool(data.get("file_logging_enabled", False)),
        log_directory=str(data.get("log_directory", "")),
        log_debug_to_file=bool(data.get("log_debug_to_file", False)),
        category_overrides=category_overrides,
        detections=detections or _default_detections(),
    )
    save_config(config, config_path)
    return config


def save_config(config: AppConfig, config_path: Path = CONFIG_FILE) -> None:
    payload = asdict(config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _coerce_cooldown(value: object) -> float:
    try:
        return max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _coerce_volume(value: object) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 100


def _resolve_sound_path(value: object) -> str:
    raw_path = str(value or "").strip()
    if not raw_path:
        return ""

    path = Path(raw_path)
    if path.exists():
        return str(path)

    bundled_candidate = RESOURCE_DIR / "sounds" / path.name
    if bundled_candidate.exists():
        return str(bundled_candidate)

    app_candidate = INSTALL_DIR / "_internal" / "sounds" / path.name
    if app_candidate.exists():
        return str(app_candidate)

    return raw_path
