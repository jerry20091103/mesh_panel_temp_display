from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import psutil
import serial
from serial.tools import list_ports

from .models import AppSettings, DisplayConfig, SensorMode
try:
    from .lhm_helper import LHMHelper
    _lhm_helper = LHMHelper()
except ImportError:
    _lhm_helper = None


APP_FOLDER_NAME = "MeshPanelTempDisplay"


@dataclass
class TemperatureSource:
    source_id: str
    label: str
    source_type: str
    temperature_unit: str = "C"


class SettingsStore:
    def __init__(self) -> None:
        app_data = os.environ.get("APPDATA", str(Path.home()))
        self._folder = Path(app_data) / APP_FOLDER_NAME
        self._file = self._folder / "settings.json"

    @property
    def path(self) -> Path:
        return self._file

    def load(self) -> AppSettings:
        if not self._file.exists():
            return AppSettings()
        try:
            return AppSettings.from_dict(json.loads(self._file.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


class StartupManager:
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    VALUE_NAME = "MeshPanelTempDisplay"

    def __init__(self, launch_command: str) -> None:
        self._launch_command = launch_command

    def set_enabled(self, enabled: bool) -> None:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY, 0, winreg.KEY_ALL_ACCESS)
        try:
            if enabled:
                command = f"{self._launch_command} --minimized"
                winreg.SetValueEx(key, self.VALUE_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, self.VALUE_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)


class TemperatureProvider:
    def discover(self) -> list[TemperatureSource]:
        sources: list[TemperatureSource] = []
        try:
            temp_map = psutil.sensors_temperatures(fahrenheit=False)
            for group_name, entries in temp_map.items():
                for idx, entry in enumerate(entries):
                    label = entry.label or f"{group_name}-{idx}"
                    source_id = f"psutil:{group_name}:{idx}"
                    pretty = f"CPU {label}" if "cpu" in group_name.lower() else f"{group_name} {label}"
                    sources.append(TemperatureSource(source_id=source_id, label=pretty, source_type="cpu", temperature_unit="C"))
        except (AttributeError, OSError):
            pass

        for gpu in self._discover_nvidia_gpus():
            sources.append(gpu)

        # LibreHardwareMonitor helper (Windows) - add sensors if available
        try:
            if _lhm_helper and _lhm_helper.is_available():
                for item in _lhm_helper.discover():
                    raw_id = item.get("id")
                    if not raw_id:
                        continue
                    sid = f"lhm:{raw_id}"
                    label = item.get('label') or raw_id
                    unit = str(item.get("unit", "C")).upper()[:1]
                    if unit not in {"C", "F"}:
                        unit = "C"
                    sources.append(TemperatureSource(source_id=sid, label=label, source_type="temperature", temperature_unit=unit))
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError, TypeError):
            pass

        return sources

    def read_source(self, source_id: str) -> float | None:
        if source_id.startswith("psutil:"):
            return self._read_psutil(source_id)
        if source_id.startswith("nvidia:"):
            return self._read_nvidia(source_id)
        if source_id.startswith("lhm:"):
            return self._read_lhm(source_id)
        return None

    def _read_lhm(self, source_id: str) -> float | None:
        if not _lhm_helper:
            return None
        try:
            _, path = source_id.split(":", maxsplit=1)
            return _lhm_helper.read(path)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError, TypeError):
            return None

    def resolve_temperature(self, mode: SensorMode, selected_ids: list[str]) -> float | None:
        if not selected_ids:
            return None
        values = [self.read_source(sid) for sid in selected_ids]
        values = [v for v in values if v is not None]
        if not values:
            return None
        if mode == SensorMode.MAX_SELECTED:
            return max(values)
        return values[0]

    def _read_psutil(self, source_id: str) -> float | None:
        try:
            _, group_name, idx_text = source_id.split(":", maxsplit=2)
            idx = int(idx_text)
            data = psutil.sensors_temperatures(fahrenheit=False)
            entries = data.get(group_name, [])
            if idx >= len(entries):
                return None
            value = entries[idx].current
            return None if value is None else float(value)
        except (AttributeError, OSError, ValueError, IndexError):
            return None

    def _discover_nvidia_gpus(self) -> list[TemperatureSource]:
        cmd = [
            "nvidia-smi",
            "--query-gpu=index,name",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5, check=True)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return []

        sources: list[TemperatureSource] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",", maxsplit=1)]
            if not parts:
                continue
            idx = parts[0]
            name = parts[1] if len(parts) > 1 else f"GPU {idx}"
            sources.append(TemperatureSource(source_id=f"nvidia:{idx}", label=f"GPU {name}", source_type="gpu", temperature_unit="C"))
        return sources

    def _read_nvidia(self, source_id: str) -> float | None:
        _, idx = source_id.split(":", maxsplit=1)
        cmd = [
            "nvidia-smi",
            f"--id={idx}",
            "--query-gpu=temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1.0, check=True)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return None
        text = result.stdout.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None


class SerialBridge:
    ACK_OK = "ACK:OK"
    ACK_ERROR = "ACK:ERROR"

    def __init__(self, on_status: Callable[[str], None] | None = None) -> None:
        self._serial: serial.Serial | None = None
        self._on_status = on_status or (lambda _message: None)
        self._manual_port = ""
        self._queue: queue.Queue[tuple[str, int]] = queue.Queue()
        self._latest_temp_tenths: int | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="SerialBridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._disconnect()

    def set_manual_port(self, port: str) -> None:
        self._manual_port = port.strip()

    def queue_temp(self, tenths: int) -> None:
        with self._lock:
            self._latest_temp_tenths = max(0, tenths)

    def queue_config(self, config: DisplayConfig) -> None:
        lines = [
            f"DOTDIAMETER:{int(config.dot_diameter)}",
            f"STARTX:{int(config.start_x)}",
            f"STARTY:{int(config.start_y)}",
            f"XXSPACING:{float(config.xx_spacing):.3f}",
            f"XYSPACING:{float(config.xy_spacing):.3f}",
            f"YXSPACING:{float(config.yx_spacing):.3f}",
            f"YYSPACING:{float(config.yy_spacing):.3f}",
            f"DIGITCOUNT:{int(config.digit_count)}",
            f"SUFFIX:{config.suffix if config.suffix in {'C', 'F'} else ''}",
            f"INVERT:{1 if config.invert else 0}",
        ]
        for line in lines:
            self._queue.put((line, 3))

    def queue_test_temp(self, tenths: int) -> None:
        self._queue.put((f"TEMP:{max(0, tenths)}", 3))

    def queue_suffix(self, suffix: str) -> None:
        suffix = (suffix or "").strip().upper()[:1]
        if suffix not in {"C", "F"}:
            suffix = ""
        self._queue.put((f"SUFFIX:{suffix}", 3))

    def _worker(self) -> None:
        while not self._stop.is_set():
            if not self._serial or not self._serial.is_open:
                self._connect()
                if not self._serial:
                    time.sleep(1.2)
                    continue

            command: tuple[str, int] | None = None
            try:
                command = self._queue.get_nowait()
            except queue.Empty:
                with self._lock:
                    if self._latest_temp_tenths is not None:
                        temp = self._latest_temp_tenths
                        self._latest_temp_tenths = None
                        command = (f"TEMP:{temp}", 2)

            if command is None:
                time.sleep(0.02)
                continue

            line, retries = command
            if not self._send_with_ack(line):
                retries -= 1
                if retries > 0:
                    self._queue.put((line, retries))
                else:
                    self._on_status(f"Command failed: {line}")

    def _send_with_ack(self, line: str) -> bool:
        if not self._serial:
            return False
        payload = f"{line}\n".encode("ascii", errors="ignore")

        try:
            self._serial.write(payload)
            self._serial.flush()
        except serial.SerialException:
            self._disconnect()
            return False

        deadline = time.monotonic() + 0.35
        while time.monotonic() < deadline:
            response = self._read_line()
            if response is None:
                continue
            if response == self.ACK_OK:
                return True
            if response == self.ACK_ERROR:
                return False
        return False

    def _read_line(self) -> str | None:
        if not self._serial:
            return None
        try:
            raw = self._serial.readline()
        except serial.SerialException:
            self._disconnect()
            return None
        if not raw:
            return None
        text = raw.decode("ascii", errors="ignore").strip()
        if not text:
            return None
        if text.startswith("ACK:"):
            return text
        self._on_status(text)
        return None

    def _connect(self) -> None:
        port = self._manual_port or self._auto_detect_port()
        if not port:
            return

        try:
            conn = serial.Serial(port=port, baudrate=9600, timeout=0.05, write_timeout=0.1)
            time.sleep(0.15)
            self._serial = conn
            self._on_status(f"Connected: {port}")
            self._drain_startup_text()
        except serial.SerialException:
            self._serial = None

    def _drain_startup_text(self) -> None:
        start = time.monotonic()
        while self._serial and time.monotonic() - start < 0.4:
            text = self._read_line()
            if text in {self.ACK_OK, self.ACK_ERROR}:
                continue

    def _disconnect(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
            self._serial = None

    def _auto_detect_port(self) -> str:
        known_vid_pids = {
            (0x2341, 0x8037),
            (0x2341, 0x0037),
            (0x2A03, 0x8037),
            (0x2A03, 0x0037),
        }

        for port in list_ports.comports():
            if port.vid is not None and port.pid is not None and (port.vid, port.pid) in known_vid_pids:
                return port.device

        arduino_keywords = re.compile(r"arduino|micro|atmega32u4", re.IGNORECASE)
        for port in list_ports.comports():
            text = " ".join(filter(None, [port.description, port.manufacturer, port.hwid]))
            if arduino_keywords.search(text):
                return port.device

        return ""
