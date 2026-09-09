from __future__ import annotations

import sys
import types
import unittest

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
from mesh_panel_pc.models import AppSettings


class FakeListbox:
    def __init__(self, items):
        self.items = list(items)
        self._selected = set()

    def curselection(self):
        return [idx for idx in range(len(self.items)) if idx in self._selected]

    def selection_clear(self, start, end):
        self._selected.clear()

    def selection_set(self, *indices):
        for idx in indices:
            self._selected.add(int(idx))


class SourceSelectionTest(unittest.TestCase):
    def test_sync_sources_list_selection_restores_previous_state(self):
        controller = AppController.__new__(AppController)
        controller.sources = [
            type("S", (), {"source_id": "cpu", "label": "CPU", "temperature_unit": "C"})(),
            type("S", (), {"source_id": "gpu", "label": "GPU", "temperature_unit": "F"})(),
            type("S", (), {"source_id": "ssd", "label": "SSD", "temperature_unit": "C"})(),
        ]
        controller.settings = AppSettings(selected_source_ids=["gpu", "ssd"])
        controller.sources_list = FakeListbox([src.label for src in controller.sources])
        controller._last_sent_suffix = ""
        controller._active_source_ids = []
        controller._active_suffix = ""
        controller.suffix_var = type("V", (), {"set": lambda self, value: None})()
        controller.serial = type("Serial", (), {"queue_suffix": lambda self, value: None})()

        controller._sync_sources_list_selection()

        self.assertEqual(controller.sources_list.curselection(), [1, 2])
        self.assertEqual(controller.settings.selected_source_ids, ["gpu", "ssd"])
        self.assertEqual(controller._active_source_ids, ["gpu", "ssd"])


if __name__ == "__main__":
    unittest.main()
