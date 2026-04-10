"""Qt GUI for the RAGE Player Assist app."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QSignalBlocker, Qt, QThread, Signal
from PySide6.QtGui import QAction, QBrush, QCloseEvent, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QMessageBox,
    QProgressDialog,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QSplitter,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from config.app_config import (
    APP_NAME,
    APP_VERSION,
    CONFIG_FILE,
    APP_DIR,
    INSTALL_DIR,
    GITHUB_RELEASES_API,
    GITHUB_LATEST_RELEASE_API,
    GITHUB_RELEASES_URL,
    RESOURCE_DIR,
    AppConfig,
    CategoryOverride,
    DetectionConfig,
    build_details,
    build_stamp,
    default_logs_directory,
    load_config,
    save_config,
)
from detections.linehandler import explain_detection_match, get_matching_detections, main as run_line_handler, play_sound_file


THEMES: dict[str, dict[str, str]] = {
    "Latte Light": {
        "window_bg": "#f4efe7",
        "panel_bg": "#fcfaf6",
        "text": "#241f19",
        "muted_text": "#6b6258",
        "border": "#d8cfc3",
        "button_bg": "#efe6db",
        "button_hover": "#e6dacd",
        "button_pressed": "#ddcebf",
        "accent": "#c46f2d",
        "accent_text": "#ffffff",
        "input_bg": "#fffdfa",
        "slider_groove": "#dfd5c8",
    },
    "Latte Dark": {
        "window_bg": "#1d1915",
        "panel_bg": "#27211c",
        "text": "#f3eadf",
        "muted_text": "#c0b1a1",
        "border": "#4e4337",
        "button_bg": "#352d26",
        "button_hover": "#41362e",
        "button_pressed": "#4b3f35",
        "accent": "#d28745",
        "accent_text": "#16120f",
        "input_bg": "#211b16",
        "slider_groove": "#56493d",
    },
    "Solarized Light": {
        "window_bg": "#fdf6e3",
        "panel_bg": "#f7f0dd",
        "text": "#586e75",
        "muted_text": "#657b83",
        "border": "#d8c9a8",
        "button_bg": "#eee8d5",
        "button_hover": "#e5dec8",
        "button_pressed": "#ddd3ba",
        "accent": "#268bd2",
        "accent_text": "#fdf6e3",
        "input_bg": "#fffaf0",
        "slider_groove": "#d5c8ab",
    },
    "Solarized Dark": {
        "window_bg": "#002b36",
        "panel_bg": "#073642",
        "text": "#93a1a1",
        "muted_text": "#839496",
        "border": "#35505a",
        "button_bg": "#0d3a46",
        "button_hover": "#124450",
        "button_pressed": "#17505c",
        "accent": "#b58900",
        "accent_text": "#002b36",
        "input_bg": "#0a303b",
        "slider_groove": "#37535d",
    },
    "Nord Light": {
        "window_bg": "#e5e9f0",
        "panel_bg": "#eceff4",
        "text": "#2e3440",
        "muted_text": "#4c566a",
        "border": "#c7d0dd",
        "button_bg": "#d8dee9",
        "button_hover": "#cfd8e5",
        "button_pressed": "#c4cfdd",
        "accent": "#5e81ac",
        "accent_text": "#eceff4",
        "input_bg": "#f3f5f9",
        "slider_groove": "#cbd5e1",
    },
    "Nord Dark": {
        "window_bg": "#2e3440",
        "panel_bg": "#3b4252",
        "text": "#eceff4",
        "muted_text": "#d8dee9",
        "border": "#4c566a",
        "button_bg": "#434c5e",
        "button_hover": "#4c566a",
        "button_pressed": "#59667d",
        "accent": "#88c0d0",
        "accent_text": "#2e3440",
        "input_bg": "#333b49",
        "slider_groove": "#59667d",
    },
    "Dracula Light": {
        "window_bg": "#f7f7fb",
        "panel_bg": "#ffffff",
        "text": "#282a36",
        "muted_text": "#6272a4",
        "border": "#d7daf0",
        "button_bg": "#eceefe",
        "button_hover": "#dfe4ff",
        "button_pressed": "#d2d8fb",
        "accent": "#bd93f9",
        "accent_text": "#ffffff",
        "input_bg": "#ffffff",
        "slider_groove": "#d7daf0",
    },
    "Dracula Dark": {
        "window_bg": "#282a36",
        "panel_bg": "#343746",
        "text": "#f8f8f2",
        "muted_text": "#bd93f9",
        "border": "#4d5166",
        "button_bg": "#44475a",
        "button_hover": "#4d5166",
        "button_pressed": "#5a5f78",
        "accent": "#ff79c6",
        "accent_text": "#282a36",
        "input_bg": "#303341",
        "slider_groove": "#5a5f78",
    },
    "Solarized Soft Light": {
        "window_bg": "#f8f2dc",
        "panel_bg": "#fff8e8",
        "text": "#586e75",
        "muted_text": "#657b83",
        "border": "#d9ceb1",
        "button_bg": "#eee4ca",
        "button_hover": "#e5dbc1",
        "button_pressed": "#ddd1b6",
        "accent": "#cb4b16",
        "accent_text": "#fff8e8",
        "input_bg": "#fffdf4",
        "slider_groove": "#d8ccb0",
    },
    "Solarized Soft Dark": {
        "window_bg": "#073642",
        "panel_bg": "#0b4251",
        "text": "#93a1a1",
        "muted_text": "#839496",
        "border": "#31525c",
        "button_bg": "#124450",
        "button_hover": "#17505c",
        "button_pressed": "#1d5c68",
        "accent": "#2aa198",
        "accent_text": "#073642",
        "input_bg": "#093946",
        "slider_groove": "#355861",
    },
}


class WatcherThread(QThread):
    log_message = Signal(str)
    watcher_finished = Signal()
    watcher_failed = Signal(str)

    def __init__(self, config: AppConfig, debug: bool, replay_last: int) -> None:
        super().__init__()
        self.config = config
        self.debug = debug
        self.replay_last = replay_last
        self.stop_event = threading.Event()

    def run(self) -> None:
        try:
            run_line_handler(
                config=self.config,
                debug=self.debug,
                replay_last=self.replay_last,
                logger=self.log_message.emit,
                stop_event=self.stop_event,
            )
            self.log_message.emit("Watcher stopped.")
            self.watcher_finished.emit()
        except Exception as error:
            self.watcher_failed.emit(str(error))

    def stop(self) -> None:
        self.stop_event.set()


def _normalize_version(version: str) -> tuple[int, ...]:
    cleaned = version.strip()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    cleaned = cleaned.split("-", 1)[0]
    parts = []
    for part in cleaned.split("."):
        digits = "".join(char for char in part if char.isdigit())
        if digits == "":
            parts.append(0)
        else:
            parts.append(int(digits))
    return tuple(parts)


def _is_installed_build() -> bool:
    if not getattr(sys, "frozen", False):
        return False

    app_dir = INSTALL_DIR.resolve()
    program_files_roots = [
        Path(os.environ.get("ProgramFiles", "")),
        Path(os.environ.get("ProgramFiles(x86)", "")),
    ]
    for root in program_files_roots:
        if not str(root).strip():
            continue
        try:
            if app_dir.is_relative_to(root.resolve()):
                return True
        except (OSError, ValueError):
            continue
    return False


def _is_portable_build() -> bool:
    return getattr(sys, "frozen", False) and not _is_installed_build()


class UpdateCheckThread(QThread):
    update_ready = Signal(dict)
    update_failed = Signal(str)

    def run(self) -> None:
        request = urllib.request.Request(
            GITHUB_LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            self.update_failed.emit(f"GitHub returned HTTP {error.code} while checking for updates.")
            return
        except urllib.error.URLError as error:
            self.update_failed.emit(f"Could not reach GitHub: {error.reason}")
            return
        except (TimeoutError, json.JSONDecodeError) as error:
            self.update_failed.emit(f"Could not read release information: {error}")
            return

        latest_tag = str(payload.get("tag_name", "")).strip()
        release_name = str(payload.get("name", "")).strip()
        release_url = str(payload.get("html_url", "")).strip() or GITHUB_RELEASES_URL
        published_at = str(payload.get("published_at", "")).strip()
        latest_version = latest_tag[1:] if latest_tag.startswith("v") else latest_tag
        current_version = APP_VERSION
        is_newer = _normalize_version(latest_version) > _normalize_version(current_version)
        assets = payload.get("assets", [])
        installer_asset = next(
            (
                asset
                for asset in assets
                if str(asset.get("name", "")).lower().endswith("-setup.msi")
                or str(asset.get("name", "")).lower().endswith(".msi")
            ),
            None,
        )
        portable_asset = next(
            (
                asset
                for asset in assets
                if str(asset.get("name", "")).lower().endswith("-portable-windows.zip")
                or str(asset.get("name", "")).lower().endswith(".zip")
            ),
            None,
        )

        self.update_ready.emit(
            {
                "latest_tag": latest_tag,
                "latest_version": latest_version,
                "release_name": release_name,
                "release_url": release_url,
                "published_at": published_at,
                "current_version": current_version,
                "is_newer": is_newer,
                "installer_asset_name": str(installer_asset.get("name", "")).strip() if installer_asset else "",
                "installer_download_url": str(installer_asset.get("browser_download_url", "")).strip() if installer_asset else "",
                "portable_asset_name": str(portable_asset.get("name", "")).strip() if portable_asset else "",
                "portable_download_url": str(portable_asset.get("browser_download_url", "")).strip() if portable_asset else "",
            }
        )


class UpdateDownloadThread(QThread):
    download_progress = Signal(int, int)
    download_ready = Signal(str)
    download_failed = Signal(str)

    def __init__(self, download_url: str, asset_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.download_url = download_url
        self.asset_name = asset_name or "RAGE-Player-Assist-Setup.msi"
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        target_dir = Path(tempfile.gettempdir()) / "RAGEPlayerAssistUpdater"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / self.asset_name

        request = urllib.request.Request(
            self.download_url,
            headers={
                "Accept": "application/octet-stream",
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                total_bytes = int(response.headers.get("Content-Length", "0") or "0")
                bytes_read = 0
                with target_path.open("wb") as handle:
                    while True:
                        if self._cancel_requested:
                            handle.close()
                            try:
                                target_path.unlink(missing_ok=True)
                            except OSError:
                                pass
                            self.download_failed.emit("Update download was cancelled.")
                            return
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        handle.write(chunk)
                        bytes_read += len(chunk)
                        self.download_progress.emit(bytes_read, total_bytes)
        except urllib.error.HTTPError as error:
            self.download_failed.emit(f"GitHub returned HTTP {error.code} while downloading the installer.")
            return
        except urllib.error.URLError as error:
            self.download_failed.emit(f"Could not download the installer: {error.reason}")
            return
        except OSError as error:
            self.download_failed.emit(f"Could not save the installer: {error}")
            return

        self.download_ready.emit(str(target_path))


class ReleaseNotesThread(QThread):
    release_notes_ready = Signal(list)
    release_notes_failed = Signal(str)

    def run(self) -> None:
        request = urllib.request.Request(
            f"{GITHUB_RELEASES_API}?per_page=8",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            self.release_notes_failed.emit(f"GitHub returned HTTP {error.code} while loading release notes.")
            return
        except urllib.error.URLError as error:
            self.release_notes_failed.emit(f"Could not reach GitHub: {error.reason}")
            return
        except (TimeoutError, json.JSONDecodeError) as error:
            self.release_notes_failed.emit(f"Could not read release notes: {error}")
            return

        releases: list[dict[str, str]] = []
        for item in payload:
            releases.append(
                {
                    "tag_name": str(item.get("tag_name", "")).strip(),
                    "name": str(item.get("name", "")).strip(),
                    "published_at": str(item.get("published_at", "")).strip(),
                    "body": str(item.get("body", "")).strip(),
                    "html_url": str(item.get("html_url", "")).strip() or GITHUB_RELEASES_URL,
                }
            )
        self.release_notes_ready.emit(releases)


def _candidate_storage_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    env_candidates = [
        os.environ.get("SystemDrive", ""),
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
    ]
    for raw_candidate in env_candidates:
        if not raw_candidate:
            continue
        candidate = Path(raw_candidate).resolve()
        root = Path(candidate.anchor or str(candidate))
        normalized = str(root).lower()
        if normalized not in seen:
            seen.add(normalized)
            roots.append(root)

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = Path(f"{letter}:\\")
        if root.exists():
            normalized = str(root).lower()
            if normalized not in seen:
                seen.add(normalized)
                roots.append(root)

    return roots


def discover_storage_paths() -> list[Path]:
    matches: list[Path] = []
    seen: set[str] = set()
    relative_patterns = [
        Path("RAGEMP") / "client_resources",
        Path("Games") / "RAGEMP" / "client_resources",
        Path("Program Files") / "RAGEMP" / "client_resources",
        Path("Program Files (x86)") / "RAGEMP" / "client_resources",
    ]

    for root in _candidate_storage_roots():
        for relative_pattern in relative_patterns:
            client_resources_dir = root / relative_pattern
            if not client_resources_dir.exists() or not client_resources_dir.is_dir():
                continue
            try:
                for child in client_resources_dir.iterdir():
                    storage_path = child / ".storage"
                    if storage_path.exists() and storage_path.is_file():
                        normalized = str(storage_path).lower()
                        if normalized not in seen:
                            seen.add(normalized)
                            matches.append(storage_path)
            except OSError:
                continue

    return sorted(matches, key=lambda path: str(path).lower())


def _create_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QBrush(QColor("#c46f2d")))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    painter.setBrush(QBrush(QColor("#241f19")))
    painter.drawRoundedRect(10, 10, 44, 44, 10, 10)

    painter.setPen(QPen(QColor("#fffdfa")))
    font = QFont("Segoe UI", 26, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "A")
    painter.end()

    return QIcon(pixmap)


def _make_sound_path(filename: str) -> str:
    return str(RESOURCE_DIR / "sounds" / filename)


def _detection_template_definitions() -> list[dict[str, str | float]]:
    return [
        {
            "label": "Private Message",
            "name": "Private Message",
            "category": "Messages",
            "rule_type": "contains",
            "pattern": "(( pm from (",
            "sound_path": _make_sound_path("incomingpm.wav"),
            "log_message": "PM detected line",
            "cooldown_seconds": 2.0,
            "description": "Alerts when an incoming private message line appears.",
        },
        {
            "label": "Mention",
            "name": "Mention",
            "category": "Messages",
            "rule_type": "mention",
            "pattern": "",
            "sound_path": _make_sound_path("mentioned.wav"),
            "log_message": "Mention detected line",
            "cooldown_seconds": 2.0,
            "description": "Alerts when your configured mention name appears in a chat message.",
        },
        {
            "label": "Keyword Watch",
            "name": "Keyword Watch",
            "category": "General",
            "rule_type": "contains",
            "pattern": "keyword here",
            "sound_path": "",
            "log_message": "Keyword detected",
            "cooldown_seconds": 1.0,
            "description": "A generic contains rule you can adapt to server-specific phrases or names.",
        },
        {
            "label": "Regex Pattern",
            "name": "Regex Pattern",
            "category": "Advanced",
            "rule_type": "regex",
            "pattern": r"\bexample\b",
            "sound_path": "",
            "log_message": "Regex pattern detected",
            "cooldown_seconds": 1.0,
            "description": "A starter regex rule for power users who need more precise matching.",
        },
    ]


def _detection_from_template(template: dict[str, str | float]) -> DetectionConfig:
    return DetectionConfig(
        id=uuid4().hex,
        name=str(template["name"]),
        category=str(template["category"]),
        rule_type=str(template["rule_type"]),
        pattern=str(template["pattern"]),
        enabled=True,
        sound_path=str(template["sound_path"]),
        log_message=str(template["log_message"]),
        cooldown_seconds=float(template["cooldown_seconds"]),
        volume_percent=100,
        regex_case_sensitive=False,
        regex_multiline=False,
        regex_dotall=False,
    )


class DetectionTemplateDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._templates = _detection_template_definitions()
        self._selected_template: dict[str, str | float] | None = None

        self.setWindowTitle("Detection Templates")
        self.resize(760, 480)
        self.setMinimumSize(680, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Choose a Detection Template")
        title.setObjectName("dialogTitleLabel")
        subtitle = QLabel("Start from a common rule and then fine-tune it in the editor.")
        subtitle.setObjectName("dialogSubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)
        layout.addWidget(body, 1)

        self.template_list = QListWidget()
        self.template_list.currentRowChanged.connect(self._on_template_selected)
        body.addWidget(self.template_list)

        detail_panel = QWidget()
        detail_layout = QFormLayout(detail_panel)
        detail_layout.setContentsMargins(12, 8, 12, 8)
        detail_layout.setHorizontalSpacing(12)
        detail_layout.setVerticalSpacing(10)
        self.template_name_value = QLabel("Select a template")
        self.template_name_value.setObjectName("overviewValueBold")
        self.template_category_value = QLabel("-")
        self.template_type_value = QLabel("-")
        self.template_pattern_value = QLabel("-")
        self.template_sound_value = QLabel("-")
        self.template_description_value = QLabel("-")
        self.template_description_value.setWordWrap(True)
        detail_layout.addRow("Name", self.template_name_value)
        detail_layout.addRow("Category", self.template_category_value)
        detail_layout.addRow("Type", self.template_type_value)
        detail_layout.addRow("Pattern", self.template_pattern_value)
        detail_layout.addRow("Sound", self.template_sound_value)
        detail_layout.addRow("Purpose", self.template_description_value)
        body.addWidget(detail_panel)
        body.setSizes([260, 420])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        buttons.button(QDialogButtonBox.Ok).setText("Use Template")

        for template in self._templates:
            self.template_list.addItem(str(template["label"]))
        if self._templates:
            self.template_list.setCurrentRow(0)

    def _on_template_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._templates):
            self._selected_template = None
            return

        template = self._templates[row]
        self._selected_template = template
        self.template_name_value.setText(str(template["name"]))
        self.template_category_value.setText(str(template["category"]))
        self.template_type_value.setText(str(template["rule_type"]))
        pattern = str(template["pattern"]) or "(Uses your configured mention name)"
        self.template_pattern_value.setText(pattern)
        self.template_sound_value.setText(Path(str(template["sound_path"])).name)
        self.template_description_value.setText(str(template["description"]))

    def selected_detection(self) -> DetectionConfig | None:
        if self._selected_template is None:
            return None
        return _detection_from_template(self._selected_template)


class DetectionEditorDialog(QDialog):
    def __init__(self, detection: DetectionConfig, config: AppConfig, log_callback, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.original_id = detection.id
        self.config = config
        self.log_callback = log_callback
        self.setWindowTitle("Edit Detection")
        self.resize(720, 520)
        self.setMinimumSize(640, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        layout.addLayout(form)

        self.name_edit = QLineEdit(detection.name)
        self.name_edit.setToolTip("Human-friendly name for this detection rule.")
        self.category_edit = QLineEdit(detection.category)
        self.category_edit.setToolTip("Category used for grouping, filtering, and category-wide audio overrides.")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["contains", "mention", "regex"])
        self.type_combo.setCurrentText(detection.rule_type)
        self.type_combo.currentTextChanged.connect(self._refresh_pattern_state)
        self.type_combo.setToolTip("Choose how this rule matches chat lines.")
        self.pattern_edit = QLineEdit(detection.pattern)
        self.pattern_edit.setToolTip("Text or regex pattern to match. Mention rules use your mention name instead.")
        self.sound_edit = QLineEdit(detection.sound_path)
        self.sound_edit.setToolTip("Sound file to play when this rule matches. Leave blank for no sound.")
        self.log_label_edit = QLineEdit(detection.log_message)
        self.log_label_edit.setToolTip("Prefix shown in the activity log when this rule fires.")
        self.cooldown_spin = QDoubleSpinBox()
        self.cooldown_spin.setRange(0.0, 9999.0)
        self.cooldown_spin.setDecimals(1)
        self.cooldown_spin.setSingleStep(0.5)
        self.cooldown_spin.setValue(detection.cooldown_seconds)
        self.cooldown_spin.setToolTip("Minimum time before this same rule can fire again.")

        sound_widget = QWidget()
        sound_row = QHBoxLayout(sound_widget)
        sound_row.setContentsMargins(0, 0, 0, 0)
        sound_row.setSpacing(8)
        sound_row.addWidget(self.sound_edit, 1)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_sound)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(lambda: self.sound_edit.setText(""))
        test_button = QPushButton("Test Sound")
        test_button.clicked.connect(self._test_sound)
        sound_row.addWidget(browse_button)
        sound_row.addWidget(clear_button)
        sound_row.addWidget(test_button)

        volume_widget = QWidget()
        volume_row = QHBoxLayout(volume_widget)
        volume_row.setContentsMargins(0, 0, 0, 0)
        volume_row.setSpacing(8)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(detection.volume_percent)
        self.volume_slider.valueChanged.connect(self._sync_volume_spin)
        self.volume_slider.setToolTip("Per-rule sound volume. Category overrides can replace this.")
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(0, 100)
        self.volume_spin.setValue(detection.volume_percent)
        self.volume_spin.valueChanged.connect(self._sync_volume_slider)
        self.volume_spin.setToolTip("Per-rule sound volume as a percentage.")
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_spin)
        volume_row.addWidget(QLabel("%"))

        regex_widget = QWidget()
        regex_row = QHBoxLayout(regex_widget)
        regex_row.setContentsMargins(0, 0, 0, 0)
        regex_row.setSpacing(12)
        self.regex_case_checkbox = QCheckBox("Case-sensitive")
        self.regex_case_checkbox.setChecked(detection.regex_case_sensitive)
        self.regex_case_checkbox.setToolTip("Regex only. Match letter case exactly.")
        self.regex_multiline_checkbox = QCheckBox("Multiline")
        self.regex_multiline_checkbox.setChecked(detection.regex_multiline)
        self.regex_multiline_checkbox.setToolTip("Regex only. Make ^ and $ work per line.")
        self.regex_dotall_checkbox = QCheckBox("Dotall")
        self.regex_dotall_checkbox.setChecked(detection.regex_dotall)
        self.regex_dotall_checkbox.setToolTip("Regex only. Allow . to match newline characters.")
        regex_row.addWidget(self.regex_case_checkbox)
        regex_row.addWidget(self.regex_multiline_checkbox)
        regex_row.addWidget(self.regex_dotall_checkbox)
        regex_row.addStretch(1)

        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(detection.enabled)
        self.enabled_checkbox.setToolTip("Disable this rule without deleting it.")

        form.addRow("Name", self.name_edit)
        form.addRow("Category", self.category_edit)
        form.addRow("Type", self.type_combo)
        form.addRow("Pattern", self.pattern_edit)
        form.addRow("Sound file", sound_widget)
        form.addRow("Log label", self.log_label_edit)
        form.addRow("Cooldown (s)", self.cooldown_spin)
        form.addRow("Volume", volume_widget)
        form.addRow("Regex options", regex_widget)
        form.addRow("", self.enabled_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_pattern_state()

    def _refresh_pattern_state(self) -> None:
        rule_type = self.type_combo.currentText()
        self.pattern_edit.setEnabled(rule_type != "mention")
        regex_enabled = rule_type == "regex"
        self.regex_case_checkbox.setEnabled(regex_enabled)
        self.regex_multiline_checkbox.setEnabled(regex_enabled)
        self.regex_dotall_checkbox.setEnabled(regex_enabled)

    def _sync_volume_spin(self, value: int) -> None:
        if self.volume_spin.value() != value:
            self.volume_spin.setValue(value)

    def _sync_volume_slider(self, value: int) -> None:
        if self.volume_slider.value() != value:
            self.volume_slider.setValue(value)

    def _browse_sound(self) -> None:
        sounds_dir = RESOURCE_DIR / "sounds"
        initial_directory = sounds_dir if sounds_dir.exists() else Path(self.sound_edit.text().strip() or INSTALL_DIR)
        if initial_directory.is_file():
            initial_directory = initial_directory.parent

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Alert Sound",
            str(initial_directory),
            "Audio files (*.wav *.mp3);;All files (*.*)",
        )
        if path:
            self.sound_edit.setText(path)

    def _effective_audio(self) -> tuple[int, bool]:
        category = self.category_edit.text().strip() or "General"
        override = next((item for item in self.config.category_overrides if item.category == category), None)
        effective_muted = self.config.global_mute or (override.muted if override else False)
        effective_volume = override.volume_percent if override and override.use_volume_override else self.volume_spin.value()
        return effective_volume, effective_muted

    def _test_sound(self) -> None:
        sound_path = self.sound_edit.text().strip()
        if not sound_path:
            self.log_callback("No sound file selected for this detection.")
            return
        if not Path(sound_path).exists():
            self.log_callback(f"Selected sound file does not exist: {sound_path}")
            return
        volume_percent, muted = self._effective_audio()
        self.log_callback(f"Testing sound: {sound_path}")
        play_sound_file(sound_path, logger=self.log_callback, volume_percent=volume_percent, muted=muted)

    def get_detection(self) -> DetectionConfig | None:
        name = self.name_edit.text().strip() or "Unnamed Detection"
        category = self.category_edit.text().strip() or "General"
        rule_type = self.type_combo.currentText()
        pattern = self.pattern_edit.text().strip()
        sound_path = self.sound_edit.text().strip()
        log_message = self.log_label_edit.text().strip()

        if rule_type != "mention" and not pattern:
            self.log_callback("Pattern cannot be empty for non-mention detections.")
            return None
        if rule_type == "regex":
            flags = 0
            if not self.regex_case_checkbox.isChecked():
                flags |= re.IGNORECASE
            if self.regex_multiline_checkbox.isChecked():
                flags |= re.MULTILINE
            if self.regex_dotall_checkbox.isChecked():
                flags |= re.DOTALL
            try:
                re.compile(pattern, flags)
            except re.error as error:
                self.log_callback(f"Invalid regex pattern: {error}")
                return None
        if sound_path and not Path(sound_path).exists():
            self.log_callback(f"Selected sound file does not exist: {sound_path}")
            return None

        return DetectionConfig(
            id=self.original_id or uuid4().hex,
            name=name,
            category=category,
            rule_type=rule_type,
            pattern=pattern,
            enabled=self.enabled_checkbox.isChecked(),
            sound_path=sound_path,
            log_message=log_message,
            cooldown_seconds=self.cooldown_spin.value(),
            volume_percent=self.volume_spin.value(),
            regex_case_sensitive=self.regex_case_checkbox.isChecked(),
            regex_multiline=self.regex_multiline_checkbox.isChecked(),
            regex_dotall=self.regex_dotall_checkbox.isChecked(),
        )


class CategoryOverridesDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._loading = False
        self.setWindowTitle("Category Audio Overrides")
        self.resize(520, 280)
        self.setMinimumSize(460, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        layout.addLayout(form)

        self.category_combo = QComboBox()
        self.category_combo.currentTextChanged.connect(self._load_editor)
        self.category_combo.setToolTip("Choose which category to override.")
        self.muted_checkbox = QCheckBox("Mute category")
        self.muted_checkbox.toggled.connect(self._store_editor)
        self.muted_checkbox.setToolTip("Mute all sounds for this category, even if matching rules have sounds.")
        self.use_volume_checkbox = QCheckBox("Override volume")
        self.use_volume_checkbox.toggled.connect(self._store_editor)
        self.use_volume_checkbox.setToolTip("Use one shared volume for all rules in this category.")

        volume_widget = QWidget()
        volume_row = QHBoxLayout(volume_widget)
        volume_row.setContentsMargins(0, 0, 0, 0)
        volume_row.setSpacing(8)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(self._sync_volume_spin)
        self.volume_slider.setToolTip("Shared category volume override.")
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(0, 100)
        self.volume_spin.valueChanged.connect(self._sync_volume_slider)
        self.volume_spin.valueChanged.connect(lambda _value: self._store_editor())
        self.volume_spin.setToolTip("Shared category volume override as a percentage.")
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_spin)
        volume_row.addWidget(QLabel("%"))

        form.addRow("Category", self.category_combo)
        form.addRow("", self.muted_checkbox)
        form.addRow("", self.use_volume_checkbox)
        form.addRow("Volume", volume_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)
        self._refresh_categories()

    def _refresh_categories(self) -> None:
        categories = sorted({d.category for d in self.config.detections if d.category.strip()}) or ["General"]
        with QSignalBlocker(self.category_combo):
            current = self.category_combo.currentText() or categories[0]
            self.category_combo.clear()
            self.category_combo.addItems(categories)
            self.category_combo.setCurrentText(current if current in categories else categories[0])
        self._load_editor(self.category_combo.currentText())

    def _sync_volume_spin(self, value: int) -> None:
        if self.volume_spin.value() != value:
            self.volume_spin.setValue(value)
        self._store_editor()

    def _sync_volume_slider(self, value: int) -> None:
        if self.volume_slider.value() != value:
            self.volume_slider.setValue(value)

    def _load_editor(self, category: str) -> None:
        self._loading = True
        override = next((item for item in self.config.category_overrides if item.category == category), None)
        self.muted_checkbox.setChecked(override.muted if override else False)
        self.use_volume_checkbox.setChecked(override.use_volume_override if override else False)
        volume = override.volume_percent if override else 100
        self.volume_slider.setValue(volume)
        self.volume_spin.setValue(volume)
        self.volume_slider.setEnabled(self.use_volume_checkbox.isChecked())
        self.volume_spin.setEnabled(self.use_volume_checkbox.isChecked())
        self._loading = False

    def _store_editor(self) -> None:
        if self._loading:
            return
        category = self.category_combo.currentText().strip()
        if not category:
            return
        muted = self.muted_checkbox.isChecked()
        use_volume_override = self.use_volume_checkbox.isChecked()
        volume_percent = self.volume_spin.value()
        self.volume_slider.setEnabled(use_volume_override)
        self.volume_spin.setEnabled(use_volume_override)

        override = next((item for item in self.config.category_overrides if item.category == category), None)
        if not muted and not use_volume_override:
            self.config.category_overrides = [item for item in self.config.category_overrides if item.category != category]
            return
        if override is None:
            override = CategoryOverride(category=category)
            self.config.category_overrides.append(override)
        override.muted = muted
        override.use_volume_override = use_volume_override
        override.volume_percent = volume_percent


class TestLineDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Test Detection Line")
        self.resize(760, 520)
        self.setMinimumSize(680, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        instructions = QLabel(
            "Paste a raw chat line below to see which rules would match and why. No sounds will play."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.line_input = QPlainTextEdit()
        self.line_input.setPlaceholderText("[22:12:44] (Work) Incoming call from 123456. Use (/p)ickup to answer or (/h)angup to decline.")
        layout.addWidget(self.line_input, 1)

        button_row = QHBoxLayout()
        self.test_button = QPushButton("Test Line")
        self.test_button.clicked.connect(self._run_test)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.line_input.clear)
        button_row.addWidget(self.test_button)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.results_output = QPlainTextEdit()
        self.results_output.setReadOnly(True)
        layout.addWidget(self.results_output, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _run_test(self) -> None:
        line = self.line_input.toPlainText().strip()
        self.results_output.clear()
        if not line:
            self.results_output.setPlainText("Enter a line to test.")
            return

        matches = get_matching_detections(line, self.config)
        result_lines = [
            f"Matched {len(matches)} of {len(self.config.detections)} detection(s).",
            "",
        ]

        for detection in self.config.detections:
            matched, reason = explain_detection_match(detection, line, self.config.mention_name)
            category_override = next(
                (item for item in self.config.category_overrides if item.category == detection.category),
                None,
            )
            effective_muted = self.config.global_mute or (category_override.muted if category_override else False)
            effective_volume = (
                category_override.volume_percent
                if category_override and category_override.use_volume_override
                else detection.volume_percent
            )
            result_lines.append(f"[{'MATCH' if matched else 'MISS'}] {detection.name}")
            result_lines.append(f"Name: {detection.name}")
            result_lines.append(f"Category: {detection.category}")
            result_lines.append(f"Type: {detection.rule_type}")
            result_lines.append(f"Reason: {reason}")
            result_lines.append(f"Sound: {Path(detection.sound_path).name if detection.sound_path else 'None'}")
            result_lines.append(f"Effective audio: {'Muted' if effective_muted else f'{effective_volume}%'}")
            result_lines.append(f"Enabled: {'Yes' if detection.enabled else 'No'}")
            if detection.rule_type == "regex":
                flags = []
                if detection.regex_case_sensitive:
                    flags.append("case-sensitive")
                if detection.regex_multiline:
                    flags.append("multiline")
                if detection.regex_dotall:
                    flags.append("dotall")
                result_lines.append(f"Regex flags: {', '.join(flags) if flags else 'default'}")
            result_lines.append("")

        self.results_output.setPlainText("\n".join(result_lines).rstrip())


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("App Settings")
        self.resize(640, 420)
        self.setMinimumSize(560, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        title = QLabel("Application Settings")
        title.setObjectName("dialogTitleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Control window behavior, startup options, and file logging for the assistant.")
        subtitle.setObjectName("dialogSubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        behavior_group = QGroupBox("Window Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setContentsMargins(16, 16, 16, 16)
        behavior_layout.setSpacing(12)
        layout.addWidget(behavior_group)

        self.close_to_tray_checkbox = QCheckBox("Hide to tray when the window is closed")
        self.close_to_tray_checkbox.setChecked(self.config.close_to_tray_on_close)
        self.close_to_tray_checkbox.setToolTip("When enabled, clicking the window X hides the app to the system tray. If disabled, clicking X fully closes the application and stops the watcher.")
        behavior_layout.addWidget(self.close_to_tray_checkbox)

        self.start_watcher_checkbox = QCheckBox("Start watcher automatically when the app opens")
        self.start_watcher_checkbox.setChecked(self.config.start_watcher_on_launch)
        self.start_watcher_checkbox.setToolTip("When enabled, the watcher starts automatically on launch using the saved config. Disabled by default.")
        behavior_layout.addWidget(self.start_watcher_checkbox)

        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        logging_layout.setContentsMargins(16, 16, 16, 16)
        logging_layout.setHorizontalSpacing(14)
        logging_layout.setVerticalSpacing(14)
        logging_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        logging_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        layout.addWidget(logging_group)

        self.file_logging_checkbox = QCheckBox("Write activity to log files")
        self.file_logging_checkbox.setChecked(self.config.file_logging_enabled)
        self.file_logging_checkbox.setToolTip("When enabled, activity is written to dated log files. Detection and watcher messages will be saved.")
        self.file_logging_checkbox.toggled.connect(self._refresh_logging_state)
        logging_layout.addRow("File logging", self.file_logging_checkbox)

        log_dir_widget = QWidget()
        log_dir_row = QHBoxLayout(log_dir_widget)
        log_dir_row.setContentsMargins(0, 0, 0, 0)
        log_dir_row.setSpacing(8)
        self.log_directory_edit = QLineEdit(self.config.log_directory)
        self.log_directory_edit.setPlaceholderText("Default: Logs folder next to the executable")
        self.log_directory_edit.setToolTip("Optional custom folder for log files. Leave blank to use a Logs folder beside the executable.")
        log_dir_row.addWidget(self.log_directory_edit, 1)
        browse_log_dir_button = QPushButton("Browse")
        browse_log_dir_button.clicked.connect(self._browse_log_directory)
        browse_log_dir_button.setToolTip("Choose a custom folder for log files.")
        log_dir_row.addWidget(browse_log_dir_button)
        logging_layout.addRow("Log directory", log_dir_widget)

        self.log_debug_checkbox = QCheckBox("Include debug/verbose messages in log files")
        self.log_debug_checkbox.setChecked(self.config.log_debug_to_file)
        self.log_debug_checkbox.setToolTip("When enabled, verbose watcher/debug lines are written to the log file too.")
        logging_layout.addRow("Log detail", self.log_debug_checkbox)

        hint = QLabel("If no log directory is chosen, the app writes daily log files to a Logs folder beside the executable.")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_logging_state()

    def apply_to_config(self) -> None:
        self.config.close_to_tray_on_close = self.close_to_tray_checkbox.isChecked()
        self.config.start_watcher_on_launch = self.start_watcher_checkbox.isChecked()
        self.config.file_logging_enabled = self.file_logging_checkbox.isChecked()
        self.config.log_directory = self.log_directory_edit.text().strip()
        self.config.log_debug_to_file = self.log_debug_checkbox.isChecked()

    def _browse_log_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Log Directory")
        if path:
            self.log_directory_edit.setText(path)

    def _refresh_logging_state(self) -> None:
        enabled = self.file_logging_checkbox.isChecked()
        self.log_directory_edit.setEnabled(enabled)
        self.log_debug_checkbox.setEnabled(enabled)


class ReleaseNotesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Release Notes")
        self.resize(760, 560)
        self.setMinimumSize(680, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Release Notes")
        title.setObjectName("dialogTitleLabel")
        subtitle = QLabel("Recent GitHub releases for RAGE Player Assist.")
        subtitle.setObjectName("dialogSubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.notes_output = QPlainTextEdit()
        self.notes_output.setReadOnly(True)
        self.notes_output.setPlainText("Loading release notes...")
        layout.addWidget(self.notes_output, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

    def set_release_notes(self, releases: list[dict[str, str]]) -> None:
        if not releases:
            self.notes_output.setPlainText("No GitHub releases were returned.")
            return

        sections: list[str] = []
        for release in releases:
            header = release["tag_name"] or "Untitled release"
            if release["name"] and release["name"] != release["tag_name"]:
                header = f"{header} - {release['name']}"
            body = release["body"] or "No release notes provided."
            sections.append(
                "\n".join(
                    [
                        header,
                        f"Published: {release['published_at']}" if release["published_at"] else "",
                        f"URL: {release['html_url']}",
                        "",
                        body,
                    ]
                ).strip()
            )

        self.notes_output.setPlainText(("\n\n" + ("-" * 72) + "\n\n").join(sections))
        self.notes_output.moveCursor(QTextCursor.Start)

    def set_error(self, message: str) -> None:
        self.notes_output.setPlainText(message)


class FirstRunSetupDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._pages: list[QWidget] = []
        self._discovery_results: list[Path] = []

        self.setWindowTitle(f"{APP_NAME} Setup")
        self.setModal(True)
        self.resize(640, 420)
        self.setMinimumSize(600, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("First-Time Setup")
        title.setObjectName("dialogTitleLabel")
        subtitle = QLabel("Set the basics once so the watcher is ready to use.")
        subtitle.setObjectName("dialogSubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self._build_intro_page()
        self._build_storage_page()
        self._build_detection_page()
        self._build_finish_page()

        self.message_label = QLabel("")
        self.message_label.setObjectName("hintLabel")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self._go_back)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._go_next)
        self.finish_button = QPushButton("Save and Finish")
        self.finish_button.clicked.connect(self._finish)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.back_button)
        button_row.addWidget(self.next_button)
        button_row.addWidget(self.finish_button)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        self.storage_path_edit.setText(self.config.storage_path)
        self.mention_name_edit.setText(self.config.mention_name)
        self._refresh_finish_summary()
        self._refresh_buttons()

    def _add_page(self, page: QWidget) -> None:
        self._pages.append(page)
        self.stack.addWidget(page)

    def _build_intro_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        intro = QLabel(
            "RAGE Player Assist watches your RageMP .storage file, matches detection rules, and plays alerts "
            "for the lines you care about."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        bullets = QLabel(
            "This setup will help you:\n"
            "• choose the storage file to monitor\n"
            "• set the mention name used by the default mention rule\n"
            "• review the default detections that ship with the app"
        )
        bullets.setWordWrap(True)
        layout.addWidget(bullets)

        note = QLabel(
            "You can change any of this later from the main window. If you cancel, the app will still open, "
            "but the watcher will not be ready to start."
        )
        note.setObjectName("hintLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        self._add_page(page)

    def _build_storage_page(self) -> None:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        storage_widget = QWidget()
        storage_row = QHBoxLayout(storage_widget)
        storage_row.setContentsMargins(0, 0, 0, 0)
        storage_row.setSpacing(8)
        self.storage_path_edit = QLineEdit()
        self.storage_path_edit.setPlaceholderText(r"Example: E:\RAGEMP\client_resources\...\ .storage")
        self.storage_path_edit.textChanged.connect(self._refresh_finish_summary)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_storage)
        auto_detect_button = QPushButton("Auto-Detect")
        auto_detect_button.clicked.connect(self._auto_detect_storage)
        storage_row.addWidget(self.storage_path_edit, 1)
        storage_row.addWidget(auto_detect_button)
        storage_row.addWidget(browse_button)

        self.mention_name_edit = QLineEdit()
        self.mention_name_edit.setPlaceholderText("Enter your in-game name")
        self.mention_name_edit.textChanged.connect(self._refresh_finish_summary)

        storage_hint = QLabel(
            "Pick the RageMP .storage file that receives new chat lines. Use Auto-Detect to scan common RageMP install "
            "locations across available drives."
        )
        storage_hint.setObjectName("hintLabel")
        storage_hint.setWordWrap(True)

        mention_hint = QLabel(
            "The default Mention rule uses this name. Leave it blank only if you plan to disable mention-based detections."
        )
        mention_hint.setObjectName("hintLabel")
        mention_hint.setWordWrap(True)

        layout.addRow("Storage file", storage_widget)
        layout.addRow("", storage_hint)
        layout.addRow("Mention name", self.mention_name_edit)
        layout.addRow("", mention_hint)
        self._add_page(page)

    def _build_detection_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        heading = QLabel("Default Detections")
        heading.setObjectName("overviewValueBold")
        layout.addWidget(heading)

        info = QLabel(
            "The app starts with two default detections so it is immediately useful. You can edit or remove them later."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.default_detection_list = QListWidget()
        self.default_detection_list.setEnabled(False)
        for detection in self.config.detections:
            self.default_detection_list.addItem(
                f"{detection.name}  •  {detection.category}  •  {detection.rule_type}"
            )
        layout.addWidget(self.default_detection_list, 1)

        hint = QLabel(
            "Tip: the bundled sound browser now opens in the packaged sounds folder, so you can quickly pick a built-in alert "
            "or drag in your own file from another Explorer window."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._add_page(page)

    def _build_finish_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        summary_title = QLabel("Ready to Finish")
        summary_title.setObjectName("overviewValueBold")
        layout.addWidget(summary_title)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        finish_hint = QLabel(
            "Saving now writes the standard config file used by the rest of the application. After setup, you can start the "
            "watcher immediately from the main window."
        )
        finish_hint.setObjectName("hintLabel")
        finish_hint.setWordWrap(True)
        layout.addWidget(finish_hint)
        layout.addStretch(1)
        self._add_page(page)

    def _browse_storage(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select RageMP .storage File",
            self.storage_path_edit.text().strip(),
            "Storage files (*.storage);;All files (*.*)",
        )
        if path:
            self.storage_path_edit.setText(path)

    def _auto_detect_storage(self) -> None:
        matches = discover_storage_paths()
        self._discovery_results = matches
        if not matches:
            self.message_label.setText(
                "No .storage file was found in the common RageMP install paths that were checked. You can still browse manually."
            )
            return

        if len(matches) == 1:
            self.storage_path_edit.setText(str(matches[0]))
            self.message_label.setText(f"Auto-detected storage file: {matches[0]}")
            return

        options = [str(path) for path in matches]
        selection, accepted = QInputDialog.getItem(
            self,
            "Choose Auto-Detected Storage File",
            "Multiple RageMP storage files were found:",
            options,
            0,
            False,
        )
        if accepted and selection:
            self.storage_path_edit.setText(selection)
            self.message_label.setText(f"Auto-detected storage file selected: {selection}")

    def _go_back(self) -> None:
        self.stack.setCurrentIndex(max(0, self.stack.currentIndex() - 1))
        self._refresh_buttons()

    def _go_next(self) -> None:
        if not self._validate_current_page():
            return
        self.stack.setCurrentIndex(min(self.stack.count() - 1, self.stack.currentIndex() + 1))
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        last_index = self.stack.count() - 1
        current_index = self.stack.currentIndex()
        self.back_button.setEnabled(current_index > 0)
        self.next_button.setVisible(current_index < last_index)
        self.finish_button.setVisible(current_index == last_index)
        self.message_label.setText("")

    def _refresh_finish_summary(self) -> None:
        storage_text = self.storage_path_edit.text().strip() or "Not set yet"
        mention_text = self.mention_name_edit.text().strip() or "Blank"
        self.summary_label.setText(
            "\n".join(
                [
                    f"Storage file: {storage_text}",
                    f"Mention name: {mention_text}",
                    f"Default detections: {len(self.config.detections)}",
                ]
            )
        )

    def _validate_current_page(self) -> bool:
        if self.stack.currentIndex() != 1:
            return True

        storage_path = self.storage_path_edit.text().strip()
        if not storage_path:
            self.message_label.setText("Choose the RageMP .storage file before continuing.")
            return False

        storage_file = Path(storage_path)
        if not storage_file.exists():
            self.message_label.setText(f"Storage path does not exist: {storage_file}")
            return False
        if not storage_file.is_file():
            self.message_label.setText(f"Storage path is not a file: {storage_file}")
            return False

        mention_name = self.mention_name_edit.text().strip()
        mention_required = any(d.rule_type == "mention" and d.enabled for d in self.config.detections)
        if mention_required and not mention_name:
            self.message_label.setText("Enter your mention name or disable mention detections later from the main window.")
            return False

        return True

    def _finish(self) -> None:
        if not self._validate_current_page() and self.stack.currentIndex() == 1:
            return
        if self.stack.currentIndex() != self.stack.count() - 1:
            if not self._validate_current_page():
                return
            self.stack.setCurrentIndex(self.stack.count() - 1)
            self._refresh_buttons()
            return

        self.config.storage_path = self.storage_path_edit.text().strip()
        self.config.mention_name = self.mention_name_edit.text().strip()
        save_config(self.config)
        self.accept()


class PlayerAssistWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._config_exists_on_launch = CONFIG_FILE.exists()
        self.config = load_config()
        self.worker_thread: WatcherThread | None = None
        self.update_check_thread: UpdateCheckThread | None = None
        self.update_download_thread: UpdateDownloadThread | None = None
        self.update_progress_dialog: QProgressDialog | None = None
        self._silent_update_check = False
        self.release_notes_thread: ReleaseNotesThread | None = None
        self.selected_detection_id: str | None = None
        self.filtered_detection_ids: list[str] = []
        self.app_icon = _create_app_icon()
        self._dirty = False
        self._closing_for_exit = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.app_icon)
        self.resize(1260, 820)
        self.setMinimumSize(980, 680)
        self._build_ui()
        self._apply_styles()
        self._load_config_into_form()
        self._connect_dirty_signals()
        self._populate_detection_list()
        self._refresh_window_title()
        self._run_first_time_setup_if_needed()
        self._append_log("GUI ready.")
        self._log_startup_validation()
        if getattr(sys, "frozen", False):
            self.check_for_updates(silent=True)
        if self.config.start_watcher_on_launch and not self._needs_first_time_setup():
            self._append_log("Start watcher on launch is enabled.")
            self.start()

    def _build_ui(self) -> None:
        self._build_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        header = QWidget()
        header.setObjectName("headerWidget")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        subtitle = QLabel("Monitor RageMP chat and get alerts for messages that matter.")
        subtitle.setObjectName("subtitleLabel")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_layout.addLayout(title_col, 1)
        status_widget = QWidget()
        status_widget.setObjectName("statusWidget")
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(12, 6, 12, 6)
        status_layout.setSpacing(8)
        self.status_dot = QLabel("\u2022")
        self.status_dot.setObjectName("statusDot")
        self.status_value_label = QLabel("Stopped")
        self.status_value_label.setObjectName("statusValue")
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_value_label)
        header_layout.addWidget(status_widget)
        self.version_value_label = QLabel(f"v{APP_VERSION}")
        self.version_value_label.setObjectName("summaryLabel")
        self.version_value_label.setToolTip("Current application version.")
        header_layout.addWidget(self.version_value_label)
        root_layout.addWidget(header)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        root_layout.addLayout(top_row)

        watcher_group = QGroupBox("Watcher")
        watcher_layout = QGridLayout(watcher_group)
        watcher_layout.setHorizontalSpacing(10)
        watcher_layout.setVerticalSpacing(10)
        self.storage_path_edit = QLineEdit()
        self.storage_path_edit.setToolTip("Path to RageMP's .storage file that contains the chat log.")
        self.storage_path_edit.setPlaceholderText(r"Example: E:\RAGEMP\client_resources\...\ .storage")
        browse_storage_button = QPushButton("Browse")
        browse_storage_button.clicked.connect(self._browse_storage)
        self.mention_name_edit = QLineEdit()
        self.mention_name_edit.setToolTip("Name to use for mention detection when rule type is 'mention'.")
        self.mention_name_edit.setPlaceholderText("Enter your in-game name")
        watcher_layout.addWidget(QLabel("Storage file"), 0, 0)
        watcher_layout.addWidget(self.storage_path_edit, 0, 1)
        watcher_layout.addWidget(browse_storage_button, 0, 2)
        watcher_layout.addWidget(QLabel("Mention name"), 1, 0)
        watcher_layout.addWidget(self.mention_name_edit, 1, 1, 1, 2)
        top_row.addWidget(watcher_group, 3)

        runtime_group = QGroupBox("Runtime")
        runtime_layout = QVBoxLayout(runtime_group)
        runtime_layout.setSpacing(8)
        self.debug_checkbox = QCheckBox("Debug mode")
        self.debug_checkbox.setToolTip("Write detailed watcher and matching activity to the log.")
        self.global_mute_checkbox = QCheckBox("Global mute")
        self.global_mute_checkbox.setToolTip("Mute all sounds without disabling detections.")
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo, 1)
        replay_row = QHBoxLayout()
        replay_row.addWidget(QLabel("Replay last"))
        self.replay_spin = QSpinBox()
        self.replay_spin.setRange(0, 9999)
        self.replay_spin.setMaximumWidth(90)
        replay_row.addWidget(self.replay_spin)
        replay_row.addStretch(1)
        runtime_layout.addWidget(self.debug_checkbox)
        runtime_layout.addWidget(self.global_mute_checkbox)
        runtime_layout.addLayout(theme_row)
        runtime_layout.addLayout(replay_row)
        runtime_layout.addStretch(1)
        top_row.addWidget(runtime_group, 1)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(6)
        root_layout.addLayout(controls_row)
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start)
        self.start_button.setToolTip("Start watching the storage file for new chat lines.")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_current_config)
        test_line_button = QPushButton("Test Line")
        test_line_button.clicked.connect(self.open_test_line_dialog)
        category_audio_button = QPushButton("Category Audio\u2026")
        category_audio_button.clicked.connect(self._open_category_overrides)
        controls_row.addWidget(self.start_button)
        controls_row.addWidget(self.stop_button)
        controls_row.addSpacing(8)
        controls_row.addWidget(save_button)
        controls_row.addWidget(test_line_button)
        controls_row.addWidget(category_audio_button)
        controls_row.addStretch(1)

        body_splitter = QSplitter(Qt.Vertical)
        body_splitter.setChildrenCollapsible(False)
        root_layout.addWidget(body_splitter, 1)

        center_splitter = QSplitter(Qt.Horizontal)
        center_splitter.setChildrenCollapsible(False)
        body_splitter.addWidget(center_splitter)

        detections_group = QGroupBox("Detections")
        detections_layout = QVBoxLayout(detections_group)
        detections_layout.setSpacing(8)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Category"))
        self.filter_category_combo = QComboBox()
        self.filter_category_combo.currentIndexChanged.connect(self._populate_detection_list)
        filter_row.addWidget(self.filter_category_combo)
        self.detection_summary_label = QLabel("")
        self.detection_summary_label.setObjectName("summaryLabel")
        filter_row.addWidget(self.detection_summary_label)
        filter_row.addStretch(1)
        detections_layout.addLayout(filter_row)

        self.detection_list = QListWidget()
        self.detection_list.currentItemChanged.connect(self._on_detection_selected)
        self.detection_list.itemDoubleClicked.connect(lambda _item: self._edit_selected_detection())
        detections_layout.addWidget(self.detection_list, 1)

        detection_buttons = QHBoxLayout()
        detection_buttons.setSpacing(6)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_detection)
        template_button = QPushButton("Template")
        template_button.clicked.connect(self._add_detection_from_template)
        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(self._duplicate_selected_detection)
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_selected_detection)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._remove_detection)
        detection_buttons.addWidget(add_button)
        detection_buttons.addWidget(template_button)
        detection_buttons.addWidget(duplicate_button)
        detection_buttons.addWidget(edit_button)
        detection_buttons.addWidget(remove_button)
        detection_buttons.addStretch(1)
        detections_layout.addLayout(detection_buttons)
        center_splitter.addWidget(detections_group)

        overview_group = QGroupBox("Selected Detection")
        overview_layout = QFormLayout(overview_group)
        overview_layout.setContentsMargins(16, 20, 16, 16)
        overview_layout.setHorizontalSpacing(16)
        overview_layout.setVerticalSpacing(12)
        self.selected_name_value = QLabel("No detection selected")
        self.selected_name_value.setObjectName("overviewValueBold")
        self.selected_category_value = QLabel("-")
        self.selected_type_value = QLabel("-")
        self.selected_sound_value = QLabel("-")
        self.selected_behavior_value = QLabel("-")
        self.selected_status_value = QLabel("-")
        self.selected_status_value.setObjectName("overviewStatus")
        overview_layout.addRow("Name", self.selected_name_value)
        overview_layout.addRow("Category", self.selected_category_value)
        overview_layout.addRow("Type", self.selected_type_value)
        overview_layout.addRow("Sound", self.selected_sound_value)
        overview_layout.addRow("Behavior", self.selected_behavior_value)
        overview_layout.addRow("Status", self.selected_status_value)
        center_splitter.addWidget(overview_group)
        center_splitter.setSizes([520, 440])

        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(6)
        log_toolbar = QHBoxLayout()
        clear_log_button = QPushButton("Clear")
        clear_log_button.clicked.connect(self._clear_log)
        log_toolbar.addWidget(clear_log_button)
        log_toolbar.addStretch(1)
        log_layout.addLayout(log_toolbar)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_output.setMaximumBlockCount(2000)
        log_layout.addWidget(self.log_output, 1)
        body_splitter.addWidget(log_group)
        body_splitter.setSizes([520, 220])

        hide_action = QAction("Hide Window", self)
        hide_action.triggered.connect(self.hide_window)
        self.addAction(hide_action)
        self._create_tray_icon()

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("Save Config", self.save_current_config)
        file_menu.addSeparator()
        file_menu.addAction("Import Config\u2026", self.import_config)
        file_menu.addAction("Export Config\u2026", self.export_config)
        file_menu.addSeparator()
        file_menu.addAction("Settings\u2026", self.open_settings_dialog)
        file_menu.addSeparator()
        file_menu.addAction("Hide to Tray", self.hide_window)
        file_menu.addAction("Exit", self.exit_app)
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction("Open Logs Folder", self.open_logs_folder)
        view_menu.addAction("Open Config Folder", self.open_config_folder)
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("Test Line\u2026", self.open_test_line_dialog)
        tools_menu.addAction("Category Audio\u2026", self._open_category_overrides)
        tools_menu.addAction("Check for Updates\u2026", self.check_for_updates)
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("Release Notes\u2026", self.open_release_notes_dialog)
        help_menu.addAction("About", self.open_about_dialog)

    def _apply_styles(self) -> None:
        theme = THEMES.get(self.config.theme, THEMES["Latte Light"])
        stylesheet = """
            QMainWindow, QWidget {{
                background: {window_bg};
                color: {text};
                font-family: "Segoe UI";
                font-size: 10pt;
            }}
            QMenuBar {{
                background: {panel_bg};
                border-bottom: 1px solid {border};
                padding: 2px 0;
                font-size: 9pt;
            }}
            QMenuBar::item {{
                padding: 4px 10px;
                border-radius: 4px;
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background: {button_hover};
            }}
            QMenu {{
                background: {panel_bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                background: transparent;
            }}
            QMenu::item:selected {{
                background: {accent};
                color: {accent_text};
            }}
            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 4px 8px;
            }}
            QGroupBox {{
                background: {panel_bg};
                border: 1px solid {border};
                border-top: none;
                border-radius: 0 0 10px 10px;
                margin-top: 22px;
                font-weight: 600;
                padding: 10px 12px 12px 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0;
                top: 0;
                padding: 4px 14px;
                background: {border};
                color: {text};
                font-size: 9pt;
                font-weight: 700;
                letter-spacing: 0.5px;
                border-radius: 6px 6px 0 0;
            }}
            QGroupBox QLabel, QGroupBox QCheckBox, QGroupBox QRadioButton {{
                background: transparent;
            }}
            QWidget#statusWidget QLabel {{
                background: transparent;
            }}
            QWidget#headerWidget QLabel {{
                background: transparent;
            }}
            QLabel#titleLabel {{
                font-size: 20pt;
                font-weight: 700;
                color: {text};
            }}
            QLabel#dialogTitleLabel {{
                font-size: 15pt;
                font-weight: 700;
                color: {text};
                padding-bottom: 2px;
            }}
            QLabel#subtitleLabel, QLabel#summaryLabel {{
                color: {muted_text};
                font-size: 9pt;
            }}
            QLabel#dialogSubtitleLabel, QLabel#hintLabel {{
                color: {muted_text};
            }}
            QLabel#statusDot {{
                font-size: 16pt;
                color: {accent};
            }}
            QLabel#statusValue {{
                color: {text};
                font-weight: 600;
                font-size: 10pt;
            }}
            QLabel#overviewValueBold {{
                font-weight: 600;
                font-size: 11pt;
                color: {text};
            }}
            QLabel#overviewStatus {{
                font-weight: 600;
                color: {accent};
            }}
            QWidget#statusWidget {{
                background: {panel_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QPushButton {{
                background: {button_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background: {button_hover};
            }}
            QPushButton:pressed {{
                background: {button_pressed};
            }}
            QPushButton:disabled {{
                opacity: 0.5;
            }}
            QPushButton#startButton {{
                background: {accent};
                color: {accent_text};
                border: 1px solid {accent};
                font-weight: 600;
                padding: 7px 18px;
            }}
            QPushButton#startButton:hover {{
                border: 1px solid {text};
            }}
            QPushButton#startButton:disabled {{
                opacity: 0.4;
            }}
            QPushButton#stopButton {{
                font-weight: 600;
                padding: 7px 18px;
            }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QListWidget {{
                background: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 8px;
                selection-background-color: {accent};
                selection-color: {accent_text};
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border: 1px solid {accent};
            }}
            QListWidget {{
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 7px 10px;
                border-radius: 6px;
                margin: 1px 2px;
            }}
            QListWidget::item:selected {{
                background: {accent};
                color: {accent_text};
            }}
            QListWidget::item:hover:!selected {{
                background: {button_bg};
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                border-radius: 3px;
                background: {slider_groove};
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
                background: {accent};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {border};
                background: {input_bg};
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border: 1px solid {accent};
            }}
            QSplitter::handle {{
                background: transparent;
                height: 6px;
                width: 6px;
            }}
            QPlainTextEdit[readOnly="true"] {{
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 9pt;
            }}
            QDialogButtonBox {{
                padding-top: 4px;
            }}
        """.format(**theme)
        self.setStyleSheet(stylesheet)

    def _needs_first_time_setup(self) -> bool:
        if not self.config.storage_path.strip():
            return True

        mention_required = any(d.rule_type == "mention" and d.enabled for d in self.config.detections)
        return mention_required and not self.config.mention_name.strip()

    def _run_first_time_setup_if_needed(self) -> None:
        if not self._needs_first_time_setup():
            return

        if self._config_exists_on_launch:
            self._append_log("Configuration is incomplete. Opening setup wizard.")
        else:
            self._append_log("No existing configuration found. Opening first-time setup wizard.")

        dialog = FirstRunSetupDialog(self.config, self)
        if dialog.exec() != QDialog.Accepted:
            self._append_log("Setup wizard was dismissed before completion.")
            return

        self.config = load_config()
        self._load_config_into_form()
        self._populate_detection_list()
        self._apply_styles()
        self._append_log("First-time setup complete.")

    def _load_config_into_form(self) -> None:
        self.storage_path_edit.setText(self.config.storage_path)
        self.mention_name_edit.setText(self.config.mention_name)
        self.global_mute_checkbox.setChecked(self.config.global_mute)
        self.theme_combo.setCurrentText(self.config.theme if self.config.theme in THEMES else "Latte Light")
        self._set_dirty(False)

    def _connect_dirty_signals(self) -> None:
        self.storage_path_edit.textChanged.connect(self._mark_dirty)
        self.mention_name_edit.textChanged.connect(self._mark_dirty)
        self.global_mute_checkbox.toggled.connect(self._mark_dirty)
        self.theme_combo.currentTextChanged.connect(self._mark_dirty)

    def _mark_dirty(self, *_args) -> None:
        self._set_dirty(True)

    def _set_dirty(self, value: bool) -> None:
        self._dirty = value
        self._refresh_window_title()

    def _refresh_window_title(self) -> None:
        suffix = " *" if self._dirty else ""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}{suffix}")

    def _has_pending_form_changes(self) -> bool:
        return (
            self.storage_path_edit.text().strip() != self.config.storage_path
            or self.mention_name_edit.text().strip() != self.config.mention_name
            or self.global_mute_checkbox.isChecked() != self.config.global_mute
            or self.theme_combo.currentText() != self.config.theme
        )

    def _sync_dirty_state(self) -> None:
        self._set_dirty(self._dirty or self._has_pending_form_changes())

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)
        self._write_log_file(message)

    def _clear_log(self) -> None:
        self.log_output.clear()

    def _default_log_directory(self) -> Path:
        return default_logs_directory()

    def _effective_log_directory(self) -> Path:
        custom_path = self.config.log_directory.strip()
        if custom_path:
            return Path(custom_path)
        return self._default_log_directory()

    def _should_write_log_message(self, message: str) -> bool:
        if not self.config.file_logging_enabled:
            return False
        if self.config.log_debug_to_file:
            return True
        debug_prefixes = (
            "Received line:",
            "Matched rule:",
            "Suppressed by cooldown:",
            "Watcher heartbeat:",
            "Watcher initialized",
            "Watcher detected",
            "Watcher read failed:",
        )
        return not message.startswith(debug_prefixes)

    def _write_log_file(self, message: str) -> None:
        if not self._should_write_log_message(message):
            return
        try:
            log_dir = self._effective_log_directory()
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{datetime.now():%Y-%m-%d}.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"[{timestamp}] {message}\n")
        except OSError as error:
            if not getattr(self, "_log_write_error_shown", False):
                self._log_write_error_shown = True
                self.log_output.appendPlainText(f"File logging error (further errors suppressed): {error}")

    def _open_directory(self, path: Path, description: str) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path))
        except OSError as error:
            self._append_log(f"Could not open {description}: {error}")

    def _browse_storage(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select RageMP .storage File", "", "Storage files (*.storage);;All files (*.*)")
        if path:
            self.storage_path_edit.setText(path)

    def _log_startup_validation(self) -> None:
        storage_path = Path(self.config.storage_path)
        if not self.config.storage_path.strip():
            self._append_log("Startup check: no storage path is configured yet.")
            return
        if not storage_path.exists():
            self._append_log(f"Startup check: saved storage path is missing: {storage_path}")
        elif not storage_path.is_file():
            self._append_log(f"Startup check: saved storage path is not a file: {storage_path}")

    def _populate_detection_list(self) -> None:
        categories = sorted({d.category for d in self.config.detections if d.category.strip()})
        filter_values = ["All", *categories]
        with QSignalBlocker(self.filter_category_combo):
            current = self.filter_category_combo.currentText() or "All"
            self.filter_category_combo.clear()
            self.filter_category_combo.addItems(filter_values)
            self.filter_category_combo.setCurrentText(current if current in filter_values else "All")

        detections = self._filtered_detections()
        self.filtered_detection_ids = [d.id for d in detections]
        self.detection_list.clear()
        for detection in detections:
            state = "\u2713" if detection.enabled else "\u2013"
            label = f"{state}  {detection.name}   \u2022  {detection.category}   \u2022  {detection.rule_type}"
            if detection.cooldown_seconds > 0:
                label += f"   \u2022  {detection.cooldown_seconds:g}s cd"
            self.detection_list.addItem(QListWidgetItem(label))

        self.detection_summary_label.setText(f"{len(detections)} shown / {len(self.config.detections)} total")
        if detections:
            index = 0
            if self.selected_detection_id is not None:
                for idx, detection in enumerate(detections):
                    if detection.id == self.selected_detection_id:
                        index = idx
                        break
            self.detection_list.setCurrentRow(index)
        else:
            self.selected_detection_id = None
            self._clear_selected_overview()

    def _filtered_detections(self) -> list[DetectionConfig]:
        category = self.filter_category_combo.currentText() or "All"
        if category == "All":
            return list(self.config.detections)
        return [d for d in self.config.detections if d.category == category]

    def _on_detection_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.selected_detection_id = None
            self._clear_selected_overview()
            return
        row = self.detection_list.row(current)
        if row < 0 or row >= len(self.filtered_detection_ids):
            return
        self.selected_detection_id = self.filtered_detection_ids[row]
        detection = self._current_detection()
        if detection is None:
            return
        self.selected_name_value.setText(detection.name)
        self.selected_category_value.setText(detection.category)
        self.selected_type_value.setText(detection.rule_type)
        self.selected_sound_value.setText(Path(detection.sound_path).name if detection.sound_path else "No sound")
        behavior = f"Cooldown {detection.cooldown_seconds:g}s, Volume {detection.volume_percent}%"
        if detection.rule_type == "regex":
            flags = []
            if detection.regex_case_sensitive:
                flags.append("case")
            if detection.regex_multiline:
                flags.append("multiline")
            if detection.regex_dotall:
                flags.append("dotall")
            if flags:
                behavior += f", Regex {'/'.join(flags)}"
        self.selected_behavior_value.setText(behavior)
        self.selected_status_value.setText("Enabled" if detection.enabled else "Disabled")

    def _clear_selected_overview(self) -> None:
        self.selected_name_value.setText("No detection selected")
        self.selected_category_value.setText("-")
        self.selected_type_value.setText("-")
        self.selected_sound_value.setText("-")
        self.selected_behavior_value.setText("-")
        self.selected_status_value.setText("-")

    def _current_detection(self) -> DetectionConfig | None:
        if self.selected_detection_id is None:
            return None
        return next((d for d in self.config.detections if d.id == self.selected_detection_id), None)

    def _open_detection_editor(self, detection: DetectionConfig) -> DetectionConfig | None:
        dialog = DetectionEditorDialog(detection, self.config, self._append_log, self)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.get_detection()

    def _add_detection(self) -> None:
        draft = DetectionConfig(
            id=uuid4().hex,
            name="New Detection",
            category="General",
            rule_type="contains",
            pattern="",
            enabled=True,
            sound_path="",
            log_message="Detected line",
            cooldown_seconds=0.0,
            volume_percent=100,
        )
        updated = self._open_detection_editor(draft)
        if updated is None:
            return
        self.config.detections.append(updated)
        self.selected_detection_id = updated.id
        self._populate_detection_list()
        self._mark_dirty()
        self._append_log(f"Added detection: {updated.name}")

    def _add_detection_from_template(self) -> None:
        dialog = DetectionTemplateDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        draft = dialog.selected_detection()
        if draft is None:
            self._append_log("No template selected.")
            return

        updated = self._open_detection_editor(draft)
        if updated is None:
            return
        self.config.detections.append(updated)
        self.selected_detection_id = updated.id
        self._populate_detection_list()
        self._mark_dirty()
        self._append_log(f"Added detection from template: {updated.name}")

    def _duplicate_selected_detection(self) -> None:
        detection = self._current_detection()
        if detection is None:
            self._append_log("Select a detection first.")
            return

        duplicate = DetectionConfig(
            id=uuid4().hex,
            name=f"{detection.name} Copy",
            category=detection.category,
            rule_type=detection.rule_type,
            pattern=detection.pattern,
            enabled=detection.enabled,
            sound_path=detection.sound_path,
            log_message=detection.log_message,
            cooldown_seconds=detection.cooldown_seconds,
            volume_percent=detection.volume_percent,
            regex_case_sensitive=detection.regex_case_sensitive,
            regex_multiline=detection.regex_multiline,
            regex_dotall=detection.regex_dotall,
        )
        updated = self._open_detection_editor(duplicate)
        if updated is None:
            return

        self.config.detections.append(updated)
        self.selected_detection_id = updated.id
        self._populate_detection_list()
        self._mark_dirty()
        self._append_log(f"Duplicated detection: {detection.name} -> {updated.name}")

    def _edit_selected_detection(self) -> None:
        detection = self._current_detection()
        if detection is None:
            self._append_log("Select a detection first.")
            return
        updated = self._open_detection_editor(detection)
        if updated is None:
            return
        for index, item in enumerate(self.config.detections):
            if item.id == detection.id:
                self.config.detections[index] = updated
                break
        self.selected_detection_id = updated.id
        self._populate_detection_list()
        self._mark_dirty()
        self._append_log(f"Updated detection: {updated.name}")

    def _remove_detection(self) -> None:
        detection = self._current_detection()
        if detection is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Detection",
            f"Delete detection '{detection.name}'?\n\nThis cannot be undone unless you re-import or recreate it.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.config.detections = [item for item in self.config.detections if item.id != detection.id]
        self.selected_detection_id = self.config.detections[0].id if self.config.detections else None
        self._populate_detection_list()
        self._mark_dirty()
        self._append_log(f"Removed detection: {detection.name}")

    def _open_category_overrides(self) -> None:
        dialog = CategoryOverridesDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            self._mark_dirty()
            self._append_log("Updated category audio overrides.")

    def _collect_config(self) -> AppConfig | None:
        storage_path = self.storage_path_edit.text().strip()
        if not storage_path:
            self._append_log("Storage path is required.")
            return None
        if not Path(storage_path).exists():
            self._append_log(f"Storage path does not exist: {storage_path}")
            return None
        if not Path(storage_path).is_file():
            self._append_log(f"Storage path is not a file: {storage_path}")
            return None
        mention_name = self.mention_name_edit.text().strip()
        if any(d.rule_type == "mention" and not mention_name for d in self.config.detections if d.enabled):
            self._append_log("Mention name is required while mention detections are enabled.")
            return None
        self.config.storage_path = storage_path
        self.config.mention_name = mention_name
        self.config.global_mute = self.global_mute_checkbox.isChecked()
        self.config.theme = self.theme_combo.currentText()
        return self.config

    def _on_theme_changed(self, theme_name: str) -> None:
        if theme_name not in THEMES:
            return
        self.config.theme = theme_name
        self._apply_styles()

    def save_current_config(self) -> None:
        config = self._collect_config()
        if config is None:
            return
        save_config(config)
        self._set_dirty(False)
        self._append_log("Configuration saved.")

    def import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Configuration", "", "JSON files (*.json);;All files (*.*)")
        if not path:
            return
        try:
            import json
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self._append_log(f"Failed to read import file: {error}")
            return
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        imported = load_config()
        self.config = imported
        self.selected_detection_id = None
        self._load_config_into_form()
        self._populate_detection_list()
        self._apply_styles()
        self._set_dirty(True)
        self._append_log(f"Imported configuration: {path}")

    def export_config(self) -> None:
        config = self._collect_config()
        if config is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Configuration", "app_config.json", "JSON files (*.json);;All files (*.*)")
        if not path:
            return
        save_config(config, Path(path))
        self._append_log(f"Exported configuration: {path}")

    def open_test_line_dialog(self) -> None:
        dialog = TestLineDialog(self.config, self)
        dialog.exec()

    def check_for_updates(self, silent: bool = False) -> None:
        if self.update_check_thread is not None and self.update_check_thread.isRunning():
            if not silent:
                self._append_log("Update check is already running.")
            return

        self._silent_update_check = silent
        if silent:
            self._append_log("Checking for updates in the background...")
        else:
            self._append_log("Checking GitHub releases for updates...")
        self.update_check_thread = UpdateCheckThread(self)
        self.update_check_thread.update_ready.connect(self._on_update_check_ready)
        self.update_check_thread.update_failed.connect(self._on_update_check_failed)
        self.update_check_thread.finished.connect(self._on_update_check_finished)
        self.update_check_thread.start()

    def _on_update_check_ready(self, payload: dict) -> None:
        current_version = str(payload.get("current_version", APP_VERSION))
        latest_tag = str(payload.get("latest_tag", "") or "Unknown")
        latest_version = str(payload.get("latest_version", "") or "Unknown")
        release_name = str(payload.get("release_name", "")).strip()
        published_at = str(payload.get("published_at", "")).strip()
        release_url = str(payload.get("release_url", GITHUB_RELEASES_URL))
        installer_download_url = str(payload.get("installer_download_url", "")).strip()
        installer_asset_name = str(payload.get("installer_asset_name", "")).strip()
        portable_download_url = str(payload.get("portable_download_url", "")).strip()
        portable_asset_name = str(payload.get("portable_asset_name", "")).strip()

        if bool(payload.get("is_newer")):
            self._append_log(f"Update available: v{current_version} -> {latest_tag}")
            if _is_installed_build() and installer_download_url:
                message = "\n".join(
                    line
                    for line in [
                        f"You are running v{current_version}.",
                        f"The latest release is {latest_tag}.",
                        f"Release name: {release_name}" if release_name else "",
                        f"Published: {published_at}" if published_at else "",
                        "",
                        "Download and install the update now?",
                    ]
                    if line != ""
                )
                choice = QMessageBox.question(
                    self,
                    "Update Available",
                    message,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes if not self._silent_update_check else QMessageBox.No,
                )
                if choice == QMessageBox.Yes:
                    self._download_and_install_update(installer_download_url, installer_asset_name or f"{latest_tag}-setup.msi")
                return
            if _is_portable_build() and portable_download_url:
                message = "\n".join(
                    line
                    for line in [
                        f"You are running v{current_version}.",
                        f"The latest release is {latest_tag}.",
                        f"Release name: {release_name}" if release_name else "",
                        f"Published: {published_at}" if published_at else "",
                        "",
                        "Download and update the portable build now?",
                    ]
                    if line != ""
                )
                choice = QMessageBox.question(
                    self,
                    "Update Available",
                    message,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes if not self._silent_update_check else QMessageBox.No,
                )
                if choice == QMessageBox.Yes:
                    self._download_and_install_update(portable_download_url, portable_asset_name or f"{latest_tag}-portable.zip")
                return

            message = "\n".join(
                line
                for line in [
                    f"You are running v{current_version}.",
                    f"The latest release is {latest_tag}.",
                    f"Release name: {release_name}" if release_name else "",
                    f"Published: {published_at}" if published_at else "",
                    "",
                    "Open the GitHub Releases page now?",
                ]
                if line != ""
            )
            choice = QMessageBox.question(
                self,
                "Update Available",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if choice == QMessageBox.Yes:
                webbrowser.open(release_url)
            return

        self._append_log(f"No update available. Current version v{current_version} is up to date.")
        if not self._silent_update_check:
            QMessageBox.information(
                self,
                "No Update Available",
                "\n".join(
                    line
                    for line in [
                        f"You are running v{current_version}.",
                        f"The latest GitHub release is {latest_tag or latest_version}.",
                        f"Release name: {release_name}" if release_name else "",
                        f"Published: {published_at}" if published_at else "",
                    ]
                    if line != ""
                ),
            )

    def _on_update_check_failed(self, message: str) -> None:
        self._append_log(f"Update check failed: {message}")
        if not self._silent_update_check:
            QMessageBox.warning(self, "Update Check Failed", message)

    def _on_update_check_finished(self) -> None:
        self._silent_update_check = False
        self.update_check_thread = None

    def _download_and_install_update(self, download_url: str, asset_name: str) -> None:
        if self.update_download_thread is not None and self.update_download_thread.isRunning():
            self._append_log("Update download is already running.")
            return

        self.update_progress_dialog = QProgressDialog("Downloading update installer...", "Cancel", 0, 100, self)
        self.update_progress_dialog.setWindowTitle("Downloading Update")
        self.update_progress_dialog.setAutoClose(False)
        self.update_progress_dialog.setAutoReset(False)
        self.update_progress_dialog.setMinimumDuration(0)
        self.update_progress_dialog.canceled.connect(self._cancel_update_download)
        self.update_progress_dialog.show()

        self.update_download_thread = UpdateDownloadThread(download_url, asset_name, self)
        self.update_download_thread.download_progress.connect(self._on_update_download_progress)
        self.update_download_thread.download_ready.connect(self._on_update_download_ready)
        self.update_download_thread.download_failed.connect(self._on_update_download_failed)
        self.update_download_thread.finished.connect(self._on_update_download_finished)
        self.update_download_thread.start()
        self._append_log(f"Downloading update installer: {asset_name}")

    def _cancel_update_download(self) -> None:
        if self.update_download_thread is None:
            return
        self.update_download_thread.cancel()
        self._append_log("Update download cancellation requested.")

    def _on_update_download_progress(self, bytes_read: int, total_bytes: int) -> None:
        if self.update_progress_dialog is None:
            return
        if total_bytes > 0:
            progress = max(0, min(100, int((bytes_read / total_bytes) * 100)))
            self.update_progress_dialog.setMaximum(100)
            self.update_progress_dialog.setValue(progress)
            self.update_progress_dialog.setLabelText(f"Downloading update installer... {progress}%")
        else:
            self.update_progress_dialog.setMaximum(0)
            self.update_progress_dialog.setLabelText("Downloading update installer...")

    def _on_update_download_ready(self, installer_path: str) -> None:
        self._append_log(f"Update downloaded: {installer_path}")
        if self.update_progress_dialog is not None:
            self.update_progress_dialog.close()
            self.update_progress_dialog = None

        if installer_path.lower().endswith(".zip") and _is_portable_build():
            self._launch_portable_updater(installer_path)
            return

        try:
            subprocess.Popen(["msiexec.exe", "/i", installer_path], close_fds=True)
        except OSError as error:
            QMessageBox.warning(self, "Update Launch Failed", f"Could not launch the Windows installer: {error}")
            return

        QMessageBox.information(
            self,
            "Installer Launched",
            "The update installer has been launched. The app will now close so Windows Installer can continue.",
        )
        self.exit_app()

    def _on_update_download_failed(self, message: str) -> None:
        self._append_log(f"Update download failed: {message}")
        if self.update_progress_dialog is not None:
            self.update_progress_dialog.close()
            self.update_progress_dialog = None
        QMessageBox.warning(self, "Update Download Failed", message)

    def _on_update_download_finished(self) -> None:
        self.update_download_thread = None

    def _launch_portable_updater(self, archive_path: str) -> None:
        archive = Path(archive_path)
        updater_dir = archive.parent
        extract_dir = updater_dir / "portable_update_extract"
        script_path = updater_dir / "apply_portable_update.ps1"
        exe_path = Path(sys.executable).resolve()
        app_dir = INSTALL_DIR.resolve()

        script_contents = f"""$ErrorActionPreference = "Stop"
$archivePath = "{archive}"
$extractDir = "{extract_dir}"
$appDir = "{app_dir}"
$exePath = "{exe_path}"
$processId = {os.getpid()}

try {{
    Wait-Process -Id $processId
}} catch {{
}}

if (Test-Path $extractDir) {{
    Remove-Item -Recurse -Force $extractDir
}}

Expand-Archive -Path $archivePath -DestinationPath $extractDir -Force
Copy-Item (Join-Path $extractDir "RAGE Player Assist.exe") (Join-Path $appDir "RAGE Player Assist.exe") -Force

$internalSource = Join-Path $extractDir "_internal"
$internalTarget = Join-Path $appDir "_internal"
if (Test-Path $internalTarget) {{
    Remove-Item -Recurse -Force $internalTarget
}}
Copy-Item $internalSource $internalTarget -Recurse -Force

Start-Process -FilePath $exePath
"""
        script_path.write_text(script_contents, encoding="utf-8")

        try:
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-WindowStyle",
                    "Hidden",
                    "-File",
                    str(script_path),
                ],
                close_fds=True,
            )
        except OSError as error:
            QMessageBox.warning(self, "Portable Update Failed", f"Could not launch the portable updater: {error}")
            return

        QMessageBox.information(
            self,
            "Portable Update Ready",
            "The portable update has been downloaded. The app will now close, apply the update, and relaunch.",
        )
        self.exit_app()

    def open_release_notes_dialog(self) -> None:
        dialog = ReleaseNotesDialog(self)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        if self.release_notes_thread is not None and self.release_notes_thread.isRunning():
            dialog.set_error("Release notes are already being loaded. Please wait for the current request to finish.")
            dialog.exec()
            return

        self._append_log("Loading GitHub release notes...")
        self.release_notes_thread = ReleaseNotesThread(self)
        self.release_notes_thread.release_notes_ready.connect(dialog.set_release_notes)
        self.release_notes_thread.release_notes_failed.connect(dialog.set_error)
        self.release_notes_thread.release_notes_failed.connect(
            lambda message: self._append_log(f"Release notes load failed: {message}")
        )
        self.release_notes_thread.finished.connect(self._on_release_notes_finished)
        self.release_notes_thread.start()
        dialog.exec()

    def _on_release_notes_finished(self) -> None:
        self.release_notes_thread = None

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() != QDialog.Accepted:
            return
        dialog.apply_to_config()
        save_config(self.config)
        self._set_dirty(self._has_pending_form_changes())
        self._append_log("Updated application settings.")

    def open_logs_folder(self) -> None:
        self._open_directory(self._effective_log_directory(), "logs folder")

    def open_config_folder(self) -> None:
        self._open_directory(APP_DIR, "config folder")

    def open_about_dialog(self) -> None:
        detail_lines = build_details()
        QMessageBox.information(
            self,
            f"About {APP_NAME}",
            "\n".join(
                [
                    f"{APP_NAME} v{APP_VERSION}",
                    f"Build: {build_stamp()}",
                    *detail_lines,
                    f"Config file: {CONFIG_FILE}",
                    f"Default logs folder: {default_logs_directory()}",
                    "",
                    "The app watches the configured RageMP .storage file, matches detections, and still works while the game is alt-tabbed or not focused.",
                    "If 'Hide to tray when the window is closed' is enabled, clicking X keeps the app alive in the tray instead of fully exiting.",
                ]
            ),
        )

    def _create_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip(APP_NAME)
        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self._restore_from_tray)
        start_action = tray_menu.addAction("Start Watcher")
        start_action.triggered.connect(self.start)
        stop_action = tray_menu.addAction("Stop Watcher")
        stop_action.triggered.connect(self.stop)
        mute_action = tray_menu.addAction("Toggle Global Mute")
        mute_action.triggered.connect(self._toggle_global_mute_from_tray)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Exit")
        quit_action.triggered.connect(self.exit_app)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _restore_from_tray(self) -> None:
        self.show()
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def _toggle_global_mute_from_tray(self) -> None:
        self.global_mute_checkbox.setChecked(not self.global_mute_checkbox.isChecked())
        self._append_log(f"Global mute {'enabled' if self.global_mute_checkbox.isChecked() else 'disabled'} from tray.")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._restore_from_tray()

    def _set_status(self, running: bool) -> None:
        if running:
            self.status_value_label.setText("Running")
            self.status_dot.setStyleSheet("color: #4ade80;")
        else:
            self.status_value_label.setText("Stopped")
            self.status_dot.setStyleSheet("")
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

    def start(self) -> None:
        if self.worker_thread is not None and self.worker_thread.isRunning():
            return
        config = self._collect_config()
        if config is None:
            return
        save_config(config)
        self._set_dirty(False)
        self.worker_thread = WatcherThread(config=config, debug=self.debug_checkbox.isChecked(), replay_last=self.replay_spin.value())
        self.worker_thread.log_message.connect(self._append_log)
        self.worker_thread.watcher_finished.connect(self._on_worker_finished)
        self.worker_thread.watcher_failed.connect(self._on_worker_failed)
        self.worker_thread.start()
        self._set_status(True)
        self._append_log("Watcher started.")

    def stop(self) -> None:
        if self.worker_thread is not None:
            self.worker_thread.stop()
        self._set_status(False)
        self._append_log("Watcher stopping.")

    def _on_worker_finished(self) -> None:
        self._set_status(False)
        self.worker_thread = None

    def _on_worker_failed(self, error: str) -> None:
        self._append_log(f"Watcher failed: {error}")
        self._set_status(False)
        self.worker_thread = None

    def hide_window(self) -> None:
        if getattr(self, "tray_icon", None) is None:
            self._append_log("System tray is not available on this system.")
            return
        self.hide()
        self._append_log("Window hidden to tray. Watcher will keep running in the background.")
        if getattr(self, "tray_icon", None) is not None:
            self.tray_icon.showMessage(
                APP_NAME,
                "The app is still running in the system tray.",
                QSystemTrayIcon.Information,
                2500,
            )

    def exit_app(self) -> None:
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(1000)
        if getattr(self, "tray_icon", None) is not None:
            self.tray_icon.hide()
        self._closing_for_exit = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._closing_for_exit and self.config.close_to_tray_on_close and getattr(self, "tray_icon", None) is not None:
            self.hide_window()
            event.ignore()
            return
        if self._dirty:
            choice = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save them before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if choice == QMessageBox.Save:
                self.save_current_config()
                if self._dirty:
                    event.ignore()
                    self._closing_for_exit = False
                    return
            elif choice == QMessageBox.Cancel:
                event.ignore()
                self._closing_for_exit = False
                return
        event.accept()


def launch() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = PlayerAssistWindow()
    window.show()
    app.exec()
