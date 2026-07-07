from __future__ import annotations

import json
import re
from typing import List

import requests


class LHMHelper:
    """Wrapper around LibreHardwareMonitor web server at localhost:8085."""

    def __init__(self, url: str = "http://localhost:8085/data.json") -> None:
        self.url = url

    def is_available(self) -> bool:
        """Check if LHM web server is reachable."""
        try:
            resp = requests.get(self.url, timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False

    def discover(self) -> List[dict]:
        """Fetch all temperature sensors from LHM."""
        try:
            resp = requests.get(self.url, timeout=2.0)
            if resp.status_code != 200:
                return []
            data = resp.json()

            sensors: List[dict] = []
            self._walk_tree(data, sensors, [])
            return sensors
        except (requests.RequestException, json.JSONDecodeError, ValueError, KeyError):
            return []

    def read(self, sensor_path: str) -> float | None:
        """Read a single sensor by SensorId (e.g. /amdcpu/0/temperature/2)."""
        try:
            resp = requests.get(self.url, timeout=1.0)
            if resp.status_code != 200:
                return None
            data = resp.json()

            node = self._find_by_sensor_id(data, sensor_path)
            if node is None:
                return None

            value = self._parse_value(node.get("Value"))
            if value is None or value <= 0:
                return None
            return value
        except (requests.RequestException, json.JSONDecodeError, ValueError, KeyError, TypeError):
            return None

    def _walk_tree(self, node: dict, sensors: List[dict], ancestors: List[str]) -> None:
        """Recursively walk LHM JSON tree and collect temperature sensors."""
        if not isinstance(node, dict):
            return

        text = str(node.get("Text", "")).strip()
        next_ancestors = ancestors + ([text] if text else [])

        if node.get("Type") == "Temperature":
            sensor_id = node.get("SensorId")
            sensor_text = str(node.get("Text", "")).strip()
            label = self._build_label(next_ancestors, sensor_text)
            value = self._parse_value(node.get("Value"))
            if sensor_id and value is not None and value > 0 and self._is_real_temperature_label(sensor_text, label):
                sensors.append({
                    "id": sensor_id,
                    "label": label,
                    "unit": self._parse_unit(node.get("Value")),
                    "type": "temperature",
                })
            return  # Don't recurse into sensor nodes

        # Recurse into children
        for child in node.get("Children", []):
            self._walk_tree(child, sensors, next_ancestors)

    def _find_by_sensor_id(self, node: dict, sensor_id: str) -> dict | None:
        """Recursively locate a node with a matching SensorId."""
        if not isinstance(node, dict):
            return None

        if node.get("SensorId") == sensor_id:
            return node

        for child in node.get("Children", []):
            found = self._find_by_sensor_id(child, sensor_id)
            if found is not None:
                return found
        return None

    def _parse_value(self, value: object) -> float | None:
        """Parse a numeric temperature from an LHM value field.

        The web server returns strings like "55.0 °C" rather than bare numbers.
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
            if match:
                try:
                    return float(match.group(0))
                except ValueError:
                    return None
        return None

    def _parse_unit(self, value: object) -> str:
        """Extract the temperature unit from the raw LHM value string."""
        if isinstance(value, str):
            text = value.upper()
            if "°F" in text or text.endswith(" F") or text.endswith("F"):
                return "F"
        return "C"

    def _is_real_temperature_label(self, sensor_text: str, label: str) -> bool:
        text = label.lower()
        raw = sensor_text.lower()
        if any(keyword in text for keyword in ("limit", "resolution", "warning temperature", "critical temperature", "low limit", "high limit")):
            return False
        if re.fullmatch(r"temperature\s*#\d+", raw):
            return False
        return True

    def _build_label(self, ancestors: List[str], sensor_text: str) -> str:
        """Build a user-facing label with the device chain plus sensor name."""
        device_parts = [part for part in ancestors if part and part not in {"Sensor", "Temperatures"}]
        if len(device_parts) >= 3:
            device = " / ".join(device_parts[1:-1])
        elif len(device_parts) == 2:
            device = device_parts[0]
        else:
            device = ""

        sensor_text = sensor_text.strip()
        if device and sensor_text:
            return f"{device} - {sensor_text}"
        return device or sensor_text
