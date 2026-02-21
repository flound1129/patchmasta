from __future__ import annotations
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QSplitter, QMessageBox, QInputDialog,
)
from PyQt6.QtCore import Qt
from midi.sysex import (
    build_program_dump_request, build_program_write, parse_program_dump,
)
from model.patch import Patch
from model.bank import Bank
from model.library import Library
from ui.library_panel import LibraryPanel
from ui.patch_detail import PatchDetailPanel
from ui.device_panel import DevicePanel

APP_ROOT = Path(__file__).parent.parent


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Korg RK-100S 2 Patch Manager")
        self.resize(1000, 600)
        self._library = Library(root=APP_ROOT)
        self._selected_patch: Patch | None = None
        self._build_ui()
        self._connect_signals()
        self._refresh_library()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._library_panel = LibraryPanel()
        self._detail_panel = PatchDetailPanel()
        self._device_panel = DevicePanel()
        splitter.addWidget(self._library_panel)
        splitter.addWidget(self._detail_panel)
        splitter.addWidget(self._device_panel)
        splitter.setSizes([250, 450, 300])
        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        self._library_panel.patch_selected.connect(self._on_patch_selected)
        self._library_panel.add_patch_requested.connect(self._on_pull_current)
        self._detail_panel.patch_saved.connect(self._on_patch_saved)
        self._device_panel.pull_requested.connect(self._on_pull_current)
        self._device_panel.send_requested.connect(self._on_send_patch)
        self._device_panel.load_all_requested.connect(self._on_load_all)
        self._device_panel.load_range_requested.connect(self._on_load_range)

    def _refresh_library(self) -> None:
        banks = self._library.list_banks()
        patches = self._library.list_patches()
        self._library_panel.populate(banks=banks, patches=patches)

    def _on_patch_selected(self, patch: Patch) -> None:
        self._selected_patch = patch
        self._detail_panel.load_patch(patch)

    def _on_patch_saved(self, patch: Patch) -> None:
        patches_dir = APP_ROOT / "patches"
        for json_file in patches_dir.glob("*.json"):
            try:
                loaded = Patch.load(json_file)
                if loaded.name == patch.name and loaded.program_number == patch.program_number:
                    patch.save(json_file)
                    break
            except Exception:
                pass
        self._refresh_library()

    def _pull_slot(self, slot: int) -> Patch | None:
        device = self._device_panel.device
        received: list[bytes] = []

        def on_sysex(event, data=None):
            message, _ = event
            parsed = parse_program_dump(message)
            if parsed is not None:
                received.append(parsed)

        device.set_sysex_callback(on_sysex)
        device.send(build_program_dump_request(channel=1, program=slot))
        time.sleep(2)

        if received:
            return Patch(
                name=f"Program {slot + 1:03d}",
                program_number=slot,
                sysex_data=received[0],
            )
        return None

    def _on_pull_current(self) -> None:
        device = self._device_panel.device
        if not device.connected:
            return
        patch = self._pull_slot(0)
        if patch:
            self._library.save_patch(patch)
            self._refresh_library()
        else:
            QMessageBox.warning(self, "Timeout", "No response from device within 2 seconds.")

    def _on_send_patch(self) -> None:
        if self._selected_patch is None:
            QMessageBox.information(self, "No patch selected", "Select a patch first.")
            return
        patch = self._selected_patch
        if patch.sysex_data is None:
            QMessageBox.warning(self, "No SysEx data", "This patch has no SysEx data to send.")
            return
        self._device_panel.device.send(
            build_program_write(channel=1, program=patch.program_number, data=patch.sysex_data)
        )

    def _on_load_all(self) -> None:
        device = self._device_panel.device
        if not device.connected:
            return
        for slot in range(200):
            patch = self._pull_slot(slot)
            if patch:
                self._library.save_patch(patch)
        self._refresh_library()

    def _on_load_range(self) -> None:
        start, ok1 = QInputDialog.getInt(self, "Load Slot Range", "Start slot (0-127):", 0, 0, 127)
        if not ok1:
            return
        end, ok2 = QInputDialog.getInt(self, "Load Slot Range", "End slot (0-127):", 40, start, 127)
        if not ok2:
            return
        device = self._device_panel.device
        if not device.connected:
            return
        for slot in range(start, end + 1):
            patch = self._pull_slot(slot)
            if patch:
                self._library.save_patch(patch)
        self._refresh_library()
