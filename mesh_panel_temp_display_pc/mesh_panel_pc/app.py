from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

import pystray
from PIL import Image, ImageDraw

from .models import AppSettings, DisplayConfig, SensorMode
from .preview import DigitPreview
from .services import SerialBridge, SettingsStore, StartupManager, TemperatureProvider, TemperatureSource

class Spinbox(ttk.Frame):
    def __init__(self, parent: ttk.Frame, var: tk.StringVar, step: float, **kwargs):
        super().__init__(parent, **kwargs)
        self.var = var
        self.step = step
        
        self.entry = ttk.Entry(self, textvariable=var, width=10)
        self.entry.grid(row=0, column=1, sticky="ew")
        
        self.minus_btn = tk.Button(self, text="-", command=self._decrement, width=2)
        self.minus_btn.grid(row=0, column=0, padx=(0, 2))
        
        self.plus_btn = tk.Button(self, text="+", command=self._increment, width=2)
        self.plus_btn.grid(row=0, column=2, padx=(2, 0))

    def _format_val(self, val: float) -> str:
        # If the value is an integer (e.g. 4.0), return "4", otherwise "4.1"
        if val == int(val):
            return str(int(val))
        return str(round(val, 2))

    def _decrement(self):
        try:
            current = float(self.var.get())
            self.var.set(self._format_val(current - self.step))
        except ValueError:
            pass

    def _increment(self):
        try:
            current = float(self.var.get())
            self.var.set(self._format_val(current + self.step))
        except ValueError:
            pass

class AppController:
    def __init__(self, start_minimized: bool) -> None:
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()

        self.temp_provider = TemperatureProvider()
        self.sources: list[TemperatureSource] = []

        self.status_queue: queue.Queue[str] = queue.Queue()
        self.tray_callback_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self.serial = SerialBridge(on_status=self._status_from_worker)
        self.serial.set_manual_port(self.settings.manual_com_port)

        if getattr(sys, "frozen", False):
            startup_command = f'"{sys.executable}"'
        else:
            pythonw_executable = Path(sys.executable).with_name("pythonw.exe")
            startup_command = f'"{pythonw_executable}" "{Path(__file__).resolve().parents[1] / "main.pyw"}"'
        self.startup = StartupManager(startup_command)

        self.root = tk.Tk()
        self.root.title("Mesh Panel Temp Display")
        self.root.geometry("760x560")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.sources_list: tk.Listbox | None = None
        self.preview: DigitPreview | None = None
        self._last_sent_suffix: str = ""
        self._active_source_ids: list[str] = []
        self._active_suffix: str = "C"

        self._build_ui()
        self._apply_settings_to_ui()

        self._tray_icon: object | None = None
        self._create_tray_icon()

        self.serial.start()
        self.serial.queue_config(self.settings.display)

        self.refresh_sources()
        self._start_temperature_loop()

        if start_minimized:
            self.hide_window()

    def run(self) -> None:
        self.root.after(200, self._drain_status_queue)
        self.root.mainloop()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Starting...")
        self.interval_var = tk.StringVar(value="1000")
        self.sensor_mode_var = tk.StringVar(value=SensorMode.SINGLE.value)
        self.manual_port_var = tk.StringVar()
        self.auto_start_var = tk.BooleanVar(value=True)

        self.dot_diameter_var = tk.StringVar(value="5")
        self.start_x_var = tk.StringVar(value="20")
        self.start_y_var = tk.StringVar(value="10")
        self.xx_spacing_var = tk.StringVar(value="7.0")
        self.xy_spacing_var = tk.StringVar(value="0.0")
        self.yx_spacing_var = tk.StringVar(value="-4.0")
        self.yy_spacing_var = tk.StringVar(value="7.0")
        self.digit_count_var = tk.StringVar(value="3")
        self.suffix_var = tk.StringVar(value="C")
        self.invert_var = tk.BooleanVar(value=False)
        self.test_value_var = tk.StringVar(value="339")
        self._preview_after_id: int | None = None

        notebook = ttk.Notebook(top)
        notebook.pack(fill="both", expand=True)

        general = ttk.Frame(notebook, padding=10)
        display = ttk.Frame(notebook, padding=10)
        notebook.add(general, text="General")
        notebook.add(display, text="Display Tuning")

        self._build_general_tab(general)
        self._build_display_tab(display)

        status = ttk.Label(top, textvariable=self.status_var)
        status.pack(anchor="w", pady=(8, 0))

    def _build_general_tab(self, parent: ttk.Frame) -> None:
        row = 0
        ttk.Label(parent, text="Update interval (ms)").grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.interval_var, width=10).grid(row=row, column=1, sticky="w", padx=(10, 0))

        row += 1
        ttk.Label(parent, text="Manual COM port (optional)").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=self.manual_port_var, width=14).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

        row += 1
        ttk.Label(parent, text="Sensor mode").grid(row=row, column=0, sticky="w", pady=(8, 0))
        mode_box = ttk.Combobox(
            parent,
            state="readonly",
            width=18,
            textvariable=self.sensor_mode_var,
            values=[SensorMode.SINGLE.value, SensorMode.MAX_SELECTED.value],
        )
        mode_box.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

        row += 1
        ttk.Label(parent, text="Temperature sources").grid(row=row, column=0, sticky="nw", pady=(8, 0))
        self.sources_list = tk.Listbox(parent, selectmode=tk.MULTIPLE, width=48, height=10)
        self.sources_list.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        self.sources_list.bind("<<ListboxSelect>>", self._on_source_selection_changed)

        row += 1
        btn_row = ttk.Frame(parent)
        btn_row.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        ttk.Button(btn_row, text="Refresh Sources", command=self.refresh_sources).pack(side="left")
        ttk.Button(btn_row, text="Apply + Save", command=self.apply_and_save).pack(side="left", padx=(8, 0))

        row += 1
        ttk.Checkbutton(parent, text="Start with Windows", variable=self.auto_start_var).grid(
            row=row, column=1, sticky="w", padx=(10, 0), pady=(8, 0)
        )

        row += 1
        ttk.Separator(parent).grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)

        row += 1
        ttk.Label(parent, text="Test TEMP value (tenths)").grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.test_value_var, width=10).grid(row=row, column=1, sticky="w", padx=(10, 0))

        row += 1
        ttk.Button(parent, text="Send Test TEMP", command=self.send_test_temp).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

    def _build_display_tab(self, parent: ttk.Frame) -> None:
        fields = [
            ("dotDiameter", self.dot_diameter_var, 1),
            ("startX", self.start_x_var, 0.1),
            ("startY", self.start_y_var, 0.1),
            ("xXSpacing", self.xx_spacing_var, 0.1),
            ("xYSpacing", self.xy_spacing_var, 0.1),
            ("yXSpacing", self.yx_spacing_var, 0.1),
            ("yYSpacing", self.yy_spacing_var, 0.1),
            ("digitCount (2/3/4)", self.digit_count_var, 1),
            ("suffix (auto)", self.suffix_var, None),
        ]
        for idx, (label, var, step) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=idx, column=0, sticky="w")
            if step is None:
                entry = ttk.Entry(parent, textvariable=var, width=12)
                entry.state(["readonly"])
            else:
                entry = Spinbox(parent, var, step)
            entry.grid(row=idx, column=1, sticky="w", padx=(10, 0), pady=(3, 3))

        ttk.Checkbutton(parent, text="Invert display", variable=self.invert_var).grid(row=9, column=1, sticky="w", padx=(10, 0), pady=(4, 8))

        btn_row = ttk.Frame(parent)
        btn_row.grid(row=10, column=1, sticky="w", padx=(10, 0), pady=(6, 4))
        ttk.Button(btn_row, text="Preview", command=self.update_preview).pack(side="left")
        ttk.Button(btn_row, text="Send Config", command=self.send_config_now).pack(side="left", padx=(8, 0))

        self.preview = DigitPreview(parent)
        self.preview.grid(row=0, column=2, rowspan=12, padx=(26, 0), sticky="n")

        # Live preview updates: trace changes to input vars (debounced)
        for var in (
            self.dot_diameter_var,
            self.start_x_var,
            self.start_y_var,
            self.xx_spacing_var,
            self.xy_spacing_var,
            self.yx_spacing_var,
            self.yy_spacing_var,
            self.digit_count_var,
            self.suffix_var,
        ):
            try:
                var.trace_add("write", lambda *_a, v=var: self._schedule_preview_update())
            except Exception:
                pass

        try:
            self.invert_var.trace_add("write", lambda *_a: self._schedule_preview_update())
        except Exception:
            pass

    def _apply_settings_to_ui(self) -> None:
        s = self.settings
        self.interval_var.set(str(s.refresh_interval_ms))
        self.sensor_mode_var.set(s.sensor_mode.value)
        self.manual_port_var.set(s.manual_com_port)
        self.auto_start_var.set(s.auto_start)

        d = s.display
        self.dot_diameter_var.set(str(d.dot_diameter))
        self.start_x_var.set(str(d.start_x))
        self.start_y_var.set(str(d.start_y))
        self.xx_spacing_var.set(str(d.xx_spacing))
        self.xy_spacing_var.set(str(d.xy_spacing))
        self.yx_spacing_var.set(str(d.yx_spacing))
        self.yy_spacing_var.set(str(d.yy_spacing))
        self.digit_count_var.set(str(d.digit_count))
        self.invert_var.set(d.invert)
        self.update_preview()
        self._sync_suffix_from_selection()

    def _read_display_config_from_ui(self) -> DisplayConfig:
        digit_count = int(self.digit_count_var.get())
        if digit_count not in {2, 3, 4}:
            digit_count = 3

        selected_ids = self._selected_source_ids()
        suffix = self._resolve_suffix_for_source_ids(selected_ids)

        return DisplayConfig(
            dot_diameter=max(1, min(255, int(self.dot_diameter_var.get()))),
            start_x=int(self.start_x_var.get()),
            start_y=int(self.start_y_var.get()),
            xx_spacing=float(self.xx_spacing_var.get()),
            xy_spacing=float(self.xy_spacing_var.get()),
            yx_spacing=float(self.yx_spacing_var.get()),
            yy_spacing=float(self.yy_spacing_var.get()),
            digit_count=digit_count,
            suffix=suffix,
            invert=self.invert_var.get(),
        )

    def _selected_source_ids(self) -> list[str]:
        selected_ids = [self.sources[i].source_id for i in self.sources_list.curselection()]
        if not selected_ids and self.sources:
            selected_ids = [self.sources[0].source_id]
        return selected_ids

    def _resolve_suffix_for_source_ids(self, source_ids: list[str]) -> str:
        for source_id in source_ids:
            source = next((s for s in self.sources if s.source_id == source_id), None)
            if source and source.temperature_unit in {"C", "F"}:
                return source.temperature_unit
        return "C"

    def _sync_suffix_from_selection(self) -> None:
        if not self.sources_list:
            return
        self.suffix_var.set(self._resolve_suffix_for_source_ids(self._selected_source_ids()))

    def _on_source_selection_changed(self, _event: object = None) -> None:
        if not self.sources_list:
            return
        live_ids = self._selected_source_ids()
        self._active_source_ids = list(live_ids)
        self.settings.selected_source_ids = list(live_ids)
        suffix = self._resolve_suffix_for_source_ids(live_ids)
        self._active_suffix = suffix
        self.suffix_var.set(suffix)
        self._queue_suffix_if_needed(suffix)

    def apply_and_save(self) -> None:
        try:
            display_cfg = self._read_display_config_from_ui()
            selected_ids = [self.sources[i].source_id for i in self.sources_list.curselection()]
            if not selected_ids and self.sources:
                selected_ids = [self.sources[0].source_id]

            mode_text = self.sensor_mode_var.get()
            try:
                mode = SensorMode(mode_text)
            except ValueError:
                mode = SensorMode.SINGLE

            settings = AppSettings(
                refresh_interval_ms=max(250, int(self.interval_var.get())),
                sensor_mode=mode,
                selected_source_ids=selected_ids,
                manual_com_port=self.manual_port_var.get().strip(),
                auto_start=self.auto_start_var.get(),
                display=display_cfg,
            )
            self.settings = settings
            self.settings_store.save(settings)
            self.serial.set_manual_port(settings.manual_com_port)
            self.serial.queue_config(settings.display)
            self._last_sent_suffix = settings.display.suffix
            self._active_source_ids = list(selected_ids)
            self._active_suffix = settings.display.suffix
            self.startup.set_enabled(settings.auto_start)
            self.update_preview()
            self.status_var.set(f"Saved: {self.settings_store.path}")
        except (ValueError, TypeError, OSError) as exc:
            messagebox.showerror("Invalid settings", str(exc))

    def send_config_now(self) -> None:
        try:
            cfg = self._read_display_config_from_ui()
            self.serial.queue_config(cfg)
            self.update_preview()
            self.status_var.set("Queued config commands")
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Invalid config", str(exc))

    def send_test_temp(self) -> None:
        try:
            tenths = max(0, int(self.test_value_var.get()))
            self.serial.queue_test_temp(tenths)
            self.status_var.set(f"Queued TEMP:{tenths}")
        except ValueError:
            messagebox.showerror("Invalid TEMP", "Enter an integer tenths value, e.g. 339")

    def refresh_sources(self) -> None:
        self.sources = self.temp_provider.discover()
        self.sources_list.delete(0, tk.END)

        selected = set(self.settings.selected_source_ids)
        for idx, src in enumerate(self.sources):
            self.sources_list.insert(tk.END, src.label)
            if src.source_id in selected:
                self.sources_list.selection_set(idx)

        if not self.sources:
            self.status_var.set("No sensors discovered. CPU sensors may require admin/hardware APIs.")
        else:
            self.status_var.set(f"Discovered {len(self.sources)} source(s)")
            if not self.sources_list.curselection():
                self.sources_list.selection_set(0)
            self._on_source_selection_changed()
            self._active_source_ids = list(self._selected_source_ids())
            self._active_suffix = self._resolve_suffix_for_source_ids(self._active_source_ids)

    def update_preview(self) -> None:
        if self.preview is None:
            return
        try:
            cfg = self._read_display_config_from_ui()
            self.preview.render(cfg)
        except (ValueError, TypeError, tk.TclError):
            pass

    def _schedule_preview_update(self) -> None:
        """Debounced scheduling for live preview updates from variable traces."""
        try:
            if self._preview_after_id is not None:
                try:
                    self.root.after_cancel(self._preview_after_id)
                except Exception:
                    pass
            self._preview_after_id = self.root.after(150, self._do_preview_update)
        except Exception:
            # If scheduling fails, try immediate update
            try:
                self.update_preview()
            except Exception:
                pass

    def _do_preview_update(self) -> None:
        self._preview_after_id = None
        try:
            self.update_preview()
        except Exception:
            pass

    def _start_temperature_loop(self) -> None:
        def worker() -> None:
            while True:
                try:
                    selected_ids = list(self._active_source_ids)
                    if not selected_ids:
                        selected_ids = list(self.settings.selected_source_ids)
                    if not selected_ids and self.sources:
                        selected_ids = [self.sources[0].source_id]

                    suffix = self._active_suffix or self._resolve_suffix_for_source_ids(selected_ids)
                    self._queue_suffix_if_needed(suffix)
                    temp_c = self.temp_provider.resolve_temperature(self.settings.sensor_mode, selected_ids)
                    if temp_c is not None:
                        tenths = int(round(temp_c * 10.0))
                        self.serial.queue_temp(tenths)
                        self._status_from_worker(f"Live TEMP:{tenths} ({temp_c:.1f} {suffix})")
                except (ValueError, RuntimeError, IndexError) as exc:
                    self._status_from_worker(f"Sensor read error: {exc}")

                interval = max(0.25, self.settings.refresh_interval_ms / 1000.0)
                time.sleep(interval)

        threading.Thread(target=worker, daemon=True, name="TemperatureLoop").start()

    def _queue_suffix_if_needed(self, suffix: str) -> None:
        suffix = (suffix or "").strip().upper()[:1]
        if suffix not in {"C", "F"}:
            suffix = ""
        if suffix != self._last_sent_suffix:
            self._last_sent_suffix = suffix
            self.serial.queue_suffix(suffix)

    def _status_from_worker(self, text: str) -> None:
        self.status_queue.put(text)

    def _drain_status_queue(self) -> None:
        latest = None
        while True:
            try:
                latest = self.status_queue.get_nowait()
            except queue.Empty:
                break
        if latest:
            self.status_var.set(latest)

        while True:
            try:
                callback = self.tray_callback_queue.get_nowait()
                callback()
            except queue.Empty:
                break

        self.root.after(250, self._drain_status_queue)

    def hide_window(self) -> None:
        self.root.withdraw()

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _create_tray_icon(self) -> None:
        image = Image.new("RGB", (64, 64), color=(18, 20, 22))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 12, 56, 52), outline=(112, 245, 160), width=3)
        draw.ellipse((16, 22, 24, 30), fill=(112, 245, 160))
        draw.ellipse((28, 22, 36, 30), fill=(112, 245, 160))
        draw.ellipse((40, 22, 48, 30), fill=(112, 245, 160))

        menu = pystray.Menu(
            pystray.MenuItem("Open", self._on_tray_open),
            pystray.MenuItem("Send Config", self._on_tray_send_config),
            pystray.MenuItem("Quit", self._quit_app),
        )

        self._tray_icon = pystray.Icon("mesh-panel-temp", image, "Mesh Panel Temp", menu)
        self._tray_icon.run_detached()

    def _on_tray_open(self, _icon: object, _item: object) -> None:
        self.tray_callback_queue.put(self.show_window)

    def _on_tray_send_config(self, _icon: object, _item: object) -> None:
        self.tray_callback_queue.put(self.send_config_now)

    def _quit_app(self, _icon: object = None, _item: object = None) -> None:
        if self._tray_icon:
            self._tray_icon.stop()
        self.serial.stop()
        self.root.after(0, self.root.destroy)


def run() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--minimized", action="store_true")
    args, _ = parser.parse_known_args()

    app = AppController(start_minimized=args.minimized)
    app.run()
