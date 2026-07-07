from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SensorMode(str, Enum):
    SINGLE = "single"
    MAX_SELECTED = "max_selected"


@dataclass
class DisplayConfig:
    dot_diameter: int = 5
    start_x: int = 20
    start_y: int = 10
    xx_spacing: float = 7.0
    xy_spacing: float = 0.0
    yx_spacing: float = -4.0
    yy_spacing: float = 7.0
    digit_count: int = 3
    suffix: str = "F"
    invert: bool = False


@dataclass
class AppSettings:
    refresh_interval_ms: int = 1000
    sensor_mode: SensorMode = SensorMode.SINGLE
    selected_source_ids: list[str] = field(default_factory=list)
    manual_com_port: str = ""
    auto_start: bool = True
    display: DisplayConfig = field(default_factory=DisplayConfig)

    def to_dict(self) -> dict:
        return {
            "refresh_interval_ms": int(self.refresh_interval_ms),
            "sensor_mode": self.sensor_mode.value,
            "selected_source_ids": list(self.selected_source_ids),
            "manual_com_port": self.manual_com_port,
            "auto_start": bool(self.auto_start),
            "display": {
                "dot_diameter": int(self.display.dot_diameter),
                "start_x": int(self.display.start_x),
                "start_y": int(self.display.start_y),
                "xx_spacing": float(self.display.xx_spacing),
                "xy_spacing": float(self.display.xy_spacing),
                "yx_spacing": float(self.display.yx_spacing),
                "yy_spacing": float(self.display.yy_spacing),
                "digit_count": int(self.display.digit_count),
                "suffix": self.display.suffix,
                "invert": bool(self.display.invert),
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        disp = data.get("display", {})
        display = DisplayConfig(
            dot_diameter=int(disp.get("dot_diameter", 5)),
            start_x=int(disp.get("start_x", 20)),
            start_y=int(disp.get("start_y", 10)),
            xx_spacing=float(disp.get("xx_spacing", 7.0)),
            xy_spacing=float(disp.get("xy_spacing", 0.0)),
            yx_spacing=float(disp.get("yx_spacing", -4.0)),
            yy_spacing=float(disp.get("yy_spacing", 7.0)),
            digit_count=int(disp.get("digit_count", 3)),
            suffix=str(disp.get("suffix", "F"))[:1],
            invert=bool(disp.get("invert", False)),
        )

        mode_value = str(data.get("sensor_mode", SensorMode.SINGLE.value))
        try:
            mode = SensorMode(mode_value)
        except ValueError:
            mode = SensorMode.SINGLE

        return cls(
            refresh_interval_ms=max(250, int(data.get("refresh_interval_ms", 1000))),
            sensor_mode=mode,
            selected_source_ids=[str(x) for x in data.get("selected_source_ids", [])],
            manual_com_port=str(data.get("manual_com_port", "")),
            auto_start=bool(data.get("auto_start", True)),
            display=display,
        )
