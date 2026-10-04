from __future__ import annotations

import queue
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Mock pystray and PIL modules if not present in test environment
pystray = types.ModuleType("pystray")
pystray.Menu = lambda *args, **kwargs: None
pystray.MenuItem = lambda *args, **kwargs: None
pystray.Icon = lambda *args, **kwargs: None
sys.modules.setdefault("pystray", pystray)

PIL = types.ModuleType("PIL")
PIL.Image = types.SimpleNamespace(new=lambda *args, **kwargs: None)
PIL.ImageDraw = types.SimpleNamespace(Draw=lambda *args, **kwargs: None)
sys.modules.setdefault("PIL", PIL)
sys.modules.setdefault("PIL.Image", PIL.Image)
sys.modules.setdefault("PIL.ImageDraw", PIL.ImageDraw)

from mesh_panel_pc.app import AppController
from mesh_panel_pc.models import AppSettings, DisplayConfig
from mesh_panel_pc.power import WindowsPowerService
from mesh_panel_pc.services import SerialBridge


class FakeSerial:
    def __init__(self, ack_response=b"ACK:OK\r\n"):
        self.is_open = True
        self.written: list[bytes] = []
        self._response = ack_response

    def write(self, data: bytes) -> int:
        self.written.append(data)
        return len(data)

    def flush(self) -> None:
        pass

    def readline(self) -> bytes:
        resp = self._response
        self._response = b""
        return resp

    def close(self) -> None:
        self.is_open = False


class SerialBridgePowerTest(unittest.TestCase):
    def test_queue_power_sets_state_and_enqueues_command(self):
        bridge = SerialBridge()
        bridge.queue_power(False)
        self.assertTrue(bridge.is_sleeping())
        cmd, retries = bridge._queue.get_nowait()
        self.assertEqual(cmd, "POWER:0")
        self.assertEqual(retries, 3)

        bridge.queue_power(True)
        self.assertFalse(bridge.is_sleeping())
        cmd2, retries2 = bridge._queue.get_nowait()
        self.assertEqual(cmd2, "POWER:1")

    def test_queue_temp_ignored_when_sleeping(self):
        bridge = SerialBridge()
        bridge.queue_power(False)
        bridge.queue_temp(350)
        self.assertIsNone(bridge._latest_temp_tenths)

        bridge.queue_power(True)
        bridge.queue_temp(350)
        self.assertEqual(bridge._latest_temp_tenths, 350)

    def test_send_power_immediate_off(self):
        bridge = SerialBridge()
        fake = FakeSerial()
        bridge._serial = fake
        bridge._queue.put(("TEMP:123", 2))
        bridge.queue_temp(456)

        result = bridge.send_power_immediate(False)
        self.assertTrue(result)
        self.assertTrue(bridge.is_sleeping())
        self.assertIsNone(bridge._latest_temp_tenths)
        self.assertTrue(bridge._queue.empty())
        self.assertIn(b"POWER:0\n", fake.written)

    def test_send_power_immediate_on(self):
        bridge = SerialBridge()
        fake = FakeSerial()
        bridge._serial = fake
        bridge._is_sleeping = True

        result = bridge.send_power_immediate(True)
        self.assertTrue(result)
        self.assertFalse(bridge.is_sleeping())
        self.assertIn(b"POWER:1\n", fake.written)


class WindowsPowerServiceTest(unittest.TestCase):
    def test_window_proc_dispatches_events(self):
        suspend_called = False
        resume_called = False
        shutdown_called = False

        def on_suspend():
            nonlocal suspend_called
            suspend_called = True

        def on_resume():
            nonlocal resume_called
            resume_called = True

        def on_shutdown():
            nonlocal shutdown_called
            shutdown_called = True

        svc = WindowsPowerService(
            on_suspend=on_suspend,
            on_resume=on_resume,
            on_shutdown=on_shutdown,
        )

        WM_POWERBROADCAST = 0x0218
        PBT_APMSUSPEND = 0x0004
        PBT_APMRESUMEAUTOMATIC = 0x0012
        WM_QUERYENDSESSION = 0x0011

        svc._window_proc(0, WM_POWERBROADCAST, PBT_APMSUSPEND, 0)
        self.assertTrue(suspend_called)

        svc._window_proc(0, WM_POWERBROADCAST, PBT_APMRESUMEAUTOMATIC, 0)
        self.assertTrue(resume_called)

        svc._window_proc(0, WM_QUERYENDSESSION, 1, 0)
        self.assertTrue(shutdown_called)


class AppControllerPowerTest(unittest.TestCase):
    def test_app_power_callbacks(self):
        controller = AppController.__new__(AppController)
        controller._display_on = True
        controller.serial = MagicMock()
        controller.tray_callback_queue = queue.Queue()
        controller.status_var = MagicMock()
        controller.power_btn = MagicMock()
        controller.settings = AppSettings()
        controller._status_from_worker = MagicMock()

        # Test suspend
        controller._on_pc_suspend()
        self.assertFalse(controller._display_on)
        controller.serial.send_power_immediate.assert_called_with(False)

        # Test resume (with sleep mocked to 0)
        with patch("time.sleep", return_value=None):
            controller._on_pc_resume()
        self.assertTrue(controller._display_on)
        controller.serial.send_power_immediate.assert_called_with(True)
        controller.serial.queue_config.assert_called_with(controller.settings.display)

        # Test toggle to OFF
        controller.toggle_display_power()
        self.assertFalse(controller._display_on)
        controller.serial.send_power_immediate.assert_called_with(False)

        # Test toggle to ON
        controller.toggle_display_power()
        self.assertTrue(controller._display_on)
        controller.serial.send_power_immediate.assert_called_with(True)


if __name__ == "__main__":
    unittest.main()

