"""Tkinter GUI for the GTAW Admin Assistant."""
from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from uuid import uuid4

from config.app_config import AppConfig, DetectionConfig, load_config, save_config
from detections.linehandler import main as run_line_handler, play_sound_file


class AdminAssistApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GTAW Admin Assistant")
        self.root.geometry("1220x840")
        self.root.minsize(1040, 720)
        self.root.configure(bg="#f4efe7")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.config = load_config()
        self.selected_detection_id: str | None = None

        self.debug_mode = tk.BooleanVar(value=False)
        self.global_mute = tk.BooleanVar(value=self.config.global_mute)
        self.replay_last = tk.StringVar(value="0")
        self.status_text = tk.StringVar(value="Stopped")
        self.filter_category = tk.StringVar(value="All")
        self.detection_summary = tk.StringVar(value="")

        self.storage_path = tk.StringVar(value=self.config.storage_path)
        self.mention_name = tk.StringVar(value=self.config.mention_name)

        self.detection_name = tk.StringVar()
        self.detection_category = tk.StringVar()
        self.detection_type = tk.StringVar(value="contains")
        self.detection_pattern = tk.StringVar()
        self.detection_enabled = tk.BooleanVar(value=True)
        self.detection_sound = tk.StringVar()
        self.detection_log_message = tk.StringVar()
        self.detection_cooldown = tk.StringVar(value="0")
        self.detection_volume = tk.StringVar(value="100")
        self.detection_volume_scale = tk.IntVar(value=100)
        self._list_detection_ids: list[str] = []

        self._configure_styles()
        self._build_ui()
        self._populate_detection_list()
        self.detection_volume.trace_add("write", self._on_volume_entry_changed)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log_queue)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#f4efe7")
        style.configure("Card.TFrame", background="#fcfaf6")
        style.configure("Title.TLabel", background="#f4efe7", foreground="#1f1c18", font=("Segoe UI", 24, "bold"))
        style.configure("Subtitle.TLabel", background="#f4efe7", foreground="#6b6258", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe", background="#fcfaf6")
        style.configure("Section.TLabelframe.Label", background="#fcfaf6", foreground="#3d342b", font=("Segoe UI", 10, "bold"))
        style.configure("App.TLabel", background="#fcfaf6", foreground="#2d261f", font=("Segoe UI", 10))
        style.configure("StatusKey.TLabel", background="#f4efe7", foreground="#4b4036", font=("Segoe UI", 10, "bold"))
        style.configure("StatusValue.TLabel", background="#f4efe7", foreground="#1f1c18", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=18, style="App.TFrame")
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        header = ttk.Label(container, text="GTAW Admin Assistant", anchor="w", style="Title.TLabel")
        header.grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(
            container,
            text="Monitor RageMP chat, create alerts based on detection rules.",
            style="Subtitle.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 14))

        top_row = ttk.Frame(container, style="App.TFrame")
        top_row.grid(row=2, column=0, sticky="ew")
        top_row.columnconfigure(0, weight=3)
        top_row.columnconfigure(1, weight=1)

        watcher_frame = ttk.LabelFrame(top_row, text="Watcher", style="Section.TLabelframe", padding=14)
        watcher_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        watcher_frame.columnconfigure(1, weight=1)

        ttk.Label(watcher_frame, text="Storage file", style="App.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        ttk.Entry(watcher_frame, textvariable=self.storage_path).grid(row=0, column=1, sticky="ew", pady=(0, 10))
        ttk.Button(watcher_frame, text="Browse", command=self._browse_storage).grid(row=0, column=2, padx=(10, 0), pady=(0, 10))

        ttk.Label(watcher_frame, text="Mention name", style="App.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(watcher_frame, textvariable=self.mention_name).grid(row=1, column=1, columnspan=2, sticky="ew")

        runtime_frame = ttk.LabelFrame(top_row, text="Runtime", style="Section.TLabelframe", padding=14)
        runtime_frame.grid(row=0, column=1, sticky="nsew")
        runtime_frame.columnconfigure(0, weight=1)
        ttk.Checkbutton(runtime_frame, text="Debug mode", variable=self.debug_mode).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(runtime_frame, text="Global mute", variable=self.global_mute).grid(row=1, column=0, sticky="w", pady=(8, 0))

        replay_row = ttk.Frame(runtime_frame, style="Card.TFrame")
        replay_row.grid(row=2, column=0, sticky="w", pady=(14, 0))
        ttk.Label(replay_row, text="Replay last", style="App.TLabel").pack(side="left")
        ttk.Entry(replay_row, width=6, textvariable=self.replay_last).pack(side="left", padx=(8, 0))

        control_row = ttk.Frame(container, style="App.TFrame")
        control_row.grid(row=3, column=0, sticky="ew", pady=(14, 12))
        self.start_button = ttk.Button(control_row, text="Start", width=12, command=self.start, style="Accent.TButton")
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(control_row, text="Stop", width=12, command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Button(control_row, text="Hide Window", width=12, command=self.hide_window).pack(side="left", padx=(8, 0))
        ttk.Button(control_row, text="Save Config", width=12, command=self.save_current_config).pack(side="left", padx=(16, 0))
        ttk.Button(control_row, text="Exit", width=12, command=self.exit_app).pack(side="left", padx=(8, 0))
        ttk.Label(control_row, text="Status", style="StatusKey.TLabel").pack(side="left", padx=(24, 6))
        ttk.Label(control_row, textvariable=self.status_text, style="StatusValue.TLabel").pack(side="left")

        workspace = ttk.Frame(container, style="App.TFrame")
        workspace.grid(row=4, column=0, sticky="nsew")
        workspace.columnconfigure(0, weight=2)
        workspace.columnconfigure(1, weight=3)
        workspace.rowconfigure(0, weight=3)
        workspace.rowconfigure(1, weight=2)

        list_frame = ttk.LabelFrame(workspace, text="Detections", style="Section.TLabelframe", padding=12)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)

        list_toolbar = ttk.Frame(list_frame, style="Card.TFrame")
        list_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        list_toolbar.columnconfigure(3, weight=1)
        ttk.Label(list_toolbar, text="Category", style="App.TLabel").grid(row=0, column=0, sticky="w")
        self.category_filter_combo = ttk.Combobox(
            list_toolbar,
            textvariable=self.filter_category,
            state="readonly",
            width=18,
        )
        self.category_filter_combo.grid(row=0, column=1, sticky="w", padx=(8, 12))
        self.category_filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        ttk.Label(list_toolbar, textvariable=self.detection_summary, style="App.TLabel").grid(row=0, column=2, sticky="w")

        self.detection_list = tk.Listbox(
            list_frame,
            exportselection=False,
            bg="#fffdfa",
            fg="#241f19",
            font=("Segoe UI", 10),
            relief="flat",
            selectbackground="#c46f2d",
            selectforeground="#ffffff",
            activestyle="none",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#d8cfc3",
            highlightcolor="#c46f2d",
        )
        self.detection_list.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.detection_list.bind("<<ListboxSelect>>", self._on_detection_select)

        list_buttons = ttk.Frame(list_frame, style="Card.TFrame")
        list_buttons.grid(row=2, column=0, sticky="ew")
        ttk.Button(list_buttons, text="Add Detection", command=self._add_detection).pack(side="left")
        ttk.Button(list_buttons, text="Remove Detection", command=self._remove_detection).pack(side="left", padx=(8, 0))

        detail_frame = ttk.LabelFrame(workspace, text="Selected Detection", style="Section.TLabelframe", padding=12)
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        form = ttk.Frame(detail_frame, style="Card.TFrame")
        form.pack(fill="both", expand=True)

        self._labeled_entry(form, "Name", self.detection_name, 0)
        self._labeled_entry(form, "Category", self.detection_category, 1)

        ttk.Label(form, text="Type", style="App.TLabel").grid(row=2, column=0, sticky="w", pady=7, padx=(0, 12))
        type_combo = ttk.Combobox(
            form,
            textvariable=self.detection_type,
            values=("contains", "mention", "regex"),
            state="readonly",
        )
        type_combo.grid(row=2, column=1, sticky="ew", pady=6)
        type_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_pattern_state())

        ttk.Label(form, text="Pattern", style="App.TLabel").grid(row=3, column=0, sticky="w", pady=7, padx=(0, 12))
        self.pattern_entry = ttk.Entry(form, textvariable=self.detection_pattern)
        self.pattern_entry.grid(row=3, column=1, sticky="ew", pady=6)

        ttk.Label(form, text="Sound file", style="App.TLabel").grid(row=4, column=0, sticky="w", pady=7, padx=(0, 12))
        sound_row = ttk.Frame(form, style="Card.TFrame")
        sound_row.grid(row=4, column=1, sticky="ew", pady=6)
        sound_row.columnconfigure(0, weight=1)
        ttk.Entry(sound_row, textvariable=self.detection_sound).grid(row=0, column=0, sticky="ew")
        ttk.Button(sound_row, text="Browse", command=self._browse_sound).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(sound_row, text="Clear", command=lambda: self.detection_sound.set("")).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(sound_row, text="Test Sound", command=self._test_selected_sound).grid(row=0, column=3, padx=(8, 0))

        self._labeled_entry(form, "Log label", self.detection_log_message, 5)
        self._labeled_entry(form, "Cooldown (s)", self.detection_cooldown, 6)
        ttk.Label(form, text="Volume", style="App.TLabel").grid(row=7, column=0, sticky="w", pady=7, padx=(0, 12))
        volume_row = ttk.Frame(form, style="Card.TFrame")
        volume_row.grid(row=7, column=1, sticky="ew", pady=6)
        volume_row.columnconfigure(0, weight=1)
        self.volume_scale = tk.Scale(
            volume_row,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.detection_volume_scale,
            command=self._on_volume_scale_changed,
            showvalue=False,
            bg="#fcfaf6",
            activebackground="#c46f2d",
            troughcolor="#dfd5c8",
            highlightthickness=0,
            bd=0,
        )
        self.volume_scale.grid(row=0, column=0, sticky="ew")
        ttk.Entry(volume_row, textvariable=self.detection_volume, width=6).grid(row=0, column=1, padx=(8, 0))
        ttk.Label(volume_row, text="%", style="App.TLabel").grid(row=0, column=2, padx=(4, 0))

        ttk.Checkbutton(form, text="Enabled", variable=self.detection_enabled).grid(row=8, column=1, sticky="w", pady=8)

        ttk.Button(form, text="Apply Changes", command=self._apply_detection_changes, style="Accent.TButton").grid(row=9, column=1, sticky="w", pady=(14, 0))

        form.columnconfigure(1, weight=1)
        log_frame = ttk.LabelFrame(workspace, text="Activity Log", style="Section.TLabelframe", padding=12)
        log_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        log_toolbar = ttk.Frame(log_frame, style="Card.TFrame")
        log_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(log_toolbar, text="Clear Log", command=self._clear_log).pack(side="left")

        self.log_output = scrolledtext.ScrolledText(
            log_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
            height=12,
            bg="#fffdfa",
            fg="#231d17",
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#d8cfc3",
            highlightcolor="#c46f2d",
        )
        self.log_output.grid(row=1, column=0, sticky="nsew")

        self._append_log("GUI ready.")

    def _labeled_entry(self, parent: tk.Widget, label: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label, style="App.TLabel").grid(row=row, column=0, sticky="w", pady=7, padx=(0, 12))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=6)

    def _append_log(self, message: str) -> None:
        self.log_output.configure(state="normal")
        self.log_output.insert("end", f"{message}\n")
        self.log_output.see("end")
        self.log_output.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_output.configure(state="normal")
        self.log_output.delete("1.0", "end")
        self.log_output.configure(state="disabled")

    def _enqueue_log(self, message: str) -> None:
        self.log_queue.put(message)

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(message)

        self.root.after(100, self._drain_log_queue)

    def _browse_storage(self) -> None:
        path = filedialog.askopenfilename(
            title="Select RageMP .storage File",
            filetypes=[("Storage files", ".storage"), ("All files", "*.*")],
        )
        if path:
            self.storage_path.set(path)

    def _browse_sound(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Alert Sound",
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")],
        )
        if path:
            self.detection_sound.set(path)

    def _populate_detection_list(self) -> None:
        categories = sorted({d.category for d in self.config.detections if d.category.strip()})
        filter_values = ["All", *categories]
        self.category_filter_combo.configure(values=filter_values)
        if self.filter_category.get() not in filter_values:
            self.filter_category.set("All")

        filtered_detections = self._filtered_detections()
        self._list_detection_ids = [detection.id for detection in filtered_detections]
        self.detection_list.delete(0, "end")
        for detection in filtered_detections:
            state = "On" if detection.enabled else "Off"
            self.detection_list.insert(
                "end",
                f"{detection.name}  [{detection.category}]  {detection.rule_type}  {state}  {detection.cooldown_seconds:g}s  {detection.volume_percent}%",
            )
        self.detection_summary.set(f"{len(filtered_detections)} shown / {len(self.config.detections)} total")

        if filtered_detections:
            index = 0
            if self.selected_detection_id is not None:
                for idx, detection in enumerate(filtered_detections):
                    if detection.id == self.selected_detection_id:
                        index = idx
                        break
            self.detection_list.selection_clear(0, "end")
            self.detection_list.selection_set(index)
            self.detection_list.event_generate("<<ListboxSelect>>")
        else:
            self._clear_detection_form()

    def _filtered_detections(self) -> list[DetectionConfig]:
        category = self.filter_category.get()
        if category == "All":
            return list(self.config.detections)
        return [detection for detection in self.config.detections if detection.category == category]

    def _clear_detection_form(self) -> None:
        self.detection_name.set("")
        self.detection_category.set("")
        self.detection_type.set("contains")
        self.detection_pattern.set("")
        self.detection_enabled.set(True)
        self.detection_sound.set("")
        self.detection_log_message.set("")
        self.detection_cooldown.set("0")
        self.detection_volume.set("100")
        self.detection_volume_scale.set(100)
        self._refresh_pattern_state()

    def _current_detection(self) -> DetectionConfig | None:
        if self.selected_detection_id is None:
            return None

        for detection in self.config.detections:
            if detection.id == self.selected_detection_id:
                return detection
        return None

    def _on_detection_select(self, _event: object) -> None:
        selection = self.detection_list.curselection()
        if not selection:
            return

        detection_id = self._list_detection_ids[selection[0]]
        detection = next((item for item in self.config.detections if item.id == detection_id), None)
        if detection is None:
            return

        self.selected_detection_id = detection.id
        self.detection_name.set(detection.name)
        self.detection_category.set(detection.category)
        self.detection_type.set(detection.rule_type)
        self.detection_pattern.set(detection.pattern)
        self.detection_enabled.set(detection.enabled)
        self.detection_sound.set(detection.sound_path)
        self.detection_log_message.set(detection.log_message)
        self.detection_cooldown.set(str(detection.cooldown_seconds))
        self.detection_volume.set(str(detection.volume_percent))
        self.detection_volume_scale.set(detection.volume_percent)
        self._refresh_pattern_state()

    def _refresh_pattern_state(self) -> None:
        # Mention rules use the shared mention name, so the pattern field is informational only.
        state = "normal" if self.detection_type.get() != "mention" else "disabled"
        self.pattern_entry.configure(state=state)

    def _on_volume_scale_changed(self, value: str) -> None:
        self.detection_volume.set(str(int(float(value))))

    def _on_volume_entry_changed(self, *_args: object) -> None:
        value = self.detection_volume.get().strip()
        if not value:
            return
        try:
            volume_percent = int(float(value))
        except ValueError:
            return
        if 0 <= volume_percent <= 100 and self.detection_volume_scale.get() != volume_percent:
            self.detection_volume_scale.set(volume_percent)

    def _on_filter_change(self, _event: object) -> None:
        self._populate_detection_list()

    def _add_detection(self) -> None:
        detection = DetectionConfig(
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
        self.config.detections.append(detection)
        self.selected_detection_id = detection.id
        self._populate_detection_list()

    def _remove_detection(self) -> None:
        detection = self._current_detection()
        if detection is None:
            return

        self.config.detections = [item for item in self.config.detections if item.id != detection.id]
        self.selected_detection_id = self.config.detections[0].id if self.config.detections else None
        self._populate_detection_list()

    def _apply_detection_changes(self) -> bool:
        detection = self._current_detection()
        if detection is None:
            self._append_log("Select a detection before applying changes.")
            return False

        name = self.detection_name.get().strip() or "Unnamed Detection"
        category = self.detection_category.get().strip() or "General"
        rule_type = self.detection_type.get()
        pattern = self.detection_pattern.get().strip()
        enabled = self.detection_enabled.get()
        sound_path = self.detection_sound.get().strip()
        log_message = self.detection_log_message.get().strip()
        cooldown_text = self.detection_cooldown.get().strip() or "0"
        volume_text = self.detection_volume.get().strip() or "100"

        try:
            cooldown_seconds = float(cooldown_text)
        except ValueError:
            self._append_log("Cooldown must be a number.")
            return False

        if cooldown_seconds < 0:
            self._append_log("Cooldown cannot be negative.")
            return False

        try:
            volume_percent = int(float(volume_text))
        except ValueError:
            self._append_log("Volume must be a whole number from 0 to 100.")
            return False

        if volume_percent < 0 or volume_percent > 100:
            self._append_log("Volume must be between 0 and 100.")
            return False

        if rule_type != "mention" and not pattern:
            self._append_log("Pattern cannot be empty for non-mention detections.")
            return False

        if rule_type == "regex":
            try:
                re.compile(pattern)
            except re.error as error:
                self._append_log(f"Invalid regex pattern: {error}")
                return False

        if sound_path and not Path(sound_path).exists():
            self._append_log(f"Selected sound file does not exist: {sound_path}")
            return False

        detection.name = name
        detection.category = category
        detection.rule_type = rule_type
        detection.pattern = pattern
        detection.enabled = enabled
        detection.sound_path = sound_path
        detection.log_message = log_message
        detection.cooldown_seconds = cooldown_seconds
        detection.volume_percent = volume_percent
        self.detection_volume.set(str(volume_percent))
        self.detection_volume_scale.set(volume_percent)

        self._populate_detection_list()
        self._append_log(f"Updated detection: {detection.name}")
        return True

    def _collect_config(self) -> AppConfig | None:
        if self.selected_detection_id is not None and not self._apply_detection_changes():
            return None

        try:
            replay_last_value = max(0, int(self.replay_last.get().strip() or "0"))
        except ValueError:
            self._append_log("Replay last must be a whole number.")
            return None

        storage_path = self.storage_path.get().strip()
        if not storage_path:
            self._append_log("Storage path is required.")
            return None
        if not Path(storage_path).exists():
            self._append_log(f"Storage path does not exist: {storage_path}")
            return None
        if not Path(storage_path).is_file():
            self._append_log(f"Storage path is not a file: {storage_path}")
            return None

        mention_name = self.mention_name.get().strip()
        if any(d.rule_type == "mention" and not mention_name for d in self.config.detections if d.enabled):
            self._append_log("Mention name is required while mention detections are enabled.")
            return None

        self.config.storage_path = storage_path
        self.config.mention_name = mention_name
        self.config.global_mute = self.global_mute.get()
        self.replay_last.set(str(replay_last_value))
        return self.config

    def save_current_config(self) -> None:
        config = self._collect_config()
        if config is None:
            return

        save_config(config)
        self._append_log("Configuration saved.")

    def _test_selected_sound(self) -> None:
        sound_path = self.detection_sound.get().strip()
        if not sound_path:
            self._append_log("No sound file selected for this detection.")
            return
        if not Path(sound_path).exists():
            self._append_log(f"Selected sound file does not exist: {sound_path}")
            return

        self._append_log(f"Testing sound: {sound_path}")
        try:
            volume_percent = int(float(self.detection_volume.get().strip() or "100"))
        except ValueError:
            self._append_log("Volume must be a whole number from 0 to 100.")
            return
        if volume_percent < 0 or volume_percent > 100:
            self._append_log("Volume must be between 0 and 100.")
            return
        self.detection_volume_scale.set(volume_percent)
        play_sound_file(
            sound_path,
            logger=self._append_log,
            volume_percent=volume_percent,
            muted=self.global_mute.get(),
        )

    def start(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        config = self._collect_config()
        if config is None:
            return

        save_config(config)
        replay_last = int(self.replay_last.get())
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(
            target=self._run_watcher,
            kwargs={
                "config": config,
                "debug": self.debug_mode.get(),
                "replay_last": replay_last,
            },
            daemon=True,
        )
        self.worker_thread.start()
        self.status_text.set("Running")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._append_log("Watcher started.")

    def stop(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()

        self.status_text.set("Stopped")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._append_log("Watcher stopping.")

    def _run_watcher(self, config: AppConfig, debug: bool, replay_last: int) -> None:
        try:
            run_line_handler(
                config=config,
                debug=debug,
                replay_last=replay_last,
                logger=self._enqueue_log,
                stop_event=self.stop_event,
            )
            self._enqueue_log("Watcher stopped.")
        except Exception as error:
            self._enqueue_log(f"Watcher failed: {error}")
        finally:
            self.root.after(0, self._on_worker_finished)

    def _on_worker_finished(self) -> None:
        self.status_text.set("Stopped")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def hide_window(self) -> None:
        self.root.iconify()
        self._append_log("Window minimized. Watcher will keep running in the background.")

    def exit_app(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop()
            self.root.after(200, self.root.destroy)
            return
        self.root.destroy()

    def _on_close(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.hide_window()
            return
        self.root.after(150, self.root.destroy)


def launch() -> None:
    root = tk.Tk()
    AdminAssistApp(root)
    root.mainloop()
