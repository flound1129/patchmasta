from __future__ import annotations
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QSplitter, QMessageBox, QInputDialog, QProgressDialog, QPushButton,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import time
from core.logger import AppLogger
from midi.sysex import (
    build_program_change, build_program_dump_request,
    build_program_write, parse_program_dump, extract_patch_name,
)
from model.patch import Patch
from model.library import Library
from ui.library_panel import LibraryPanel
from ui.patch_detail import PatchDetailPanel
from ui.device_panel import DevicePanel
from ui.log_panel import LogPanel
from ui.synth_editor_window import SynthEditorWindow
from midi.params import ParamMap
from core.config import AppConfig

APP_ROOT = Path(__file__).parent.parent


class PullWorker(QThread):
    """Pulls one or more program slots from the device on a background thread."""
    patch_ready = pyqtSignal(object)       # Patch on success, None on timeout
    progress = pyqtSignal(int, int, str)   # slots_done, slots_total, status_message
    finished = pyqtSignal(int, int)        # patches_received, slots_total

    def __init__(self, device, slots: list[int], logger: AppLogger | None = None, parent=None) -> None:
        super().__init__(parent)
        self._device = device
        self._slots = slots
        self._logger = logger or AppLogger()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._slots)
        received_count = 0
        try:
            for i, slot in enumerate(self._slots):
                if self._cancelled:
                    break
                self.progress.emit(i, total, f"Slot {slot + 1} of {total}...")
                received: list[bytes] = []
                event = threading.Event()

                def on_sysex(midi_event, data=None, _recv=received, _evt=event):
                    message, _ = midi_event
                    self._logger.midi(f"RX: {[hex(b) for b in message[:12]]}{'...' if len(message) > 12 else ''}")
                    parsed = parse_program_dump(list(message))
                    if parsed is not None:
                        _recv.append(parsed)
                        _evt.set()

                # Select the program slot, then request a dump of the current program
                pc_msg = build_program_change(channel=1, program=slot & 0x7F)
                self._device.send(pc_msg)
                time.sleep(0.05)  # let the device switch programs

                msg = build_program_dump_request(channel=1)
                if i == 0:
                    self._logger.midi(f"TX: slot {slot}: pc={[hex(b) for b in pc_msg]} dump={[hex(b) for b in msg]}")
                self._device.set_sysex_callback(on_sysex)
                self._device.send(msg)
                event.wait(timeout=2.0)

                # Clear callback before next slot to prevent cross-slot attribution
                try:
                    self._device.set_sysex_callback(lambda e, d=None: None)
                except Exception:
                    pass

                if received:
                    received_count += 1
                    name = extract_patch_name(received[0]) or f"Program {slot + 1:03d}"
                    self.patch_ready.emit(Patch(
                        name=name,
                        program_number=slot,
                        sysex_data=received[0],
                    ))
                else:
                    self.patch_ready.emit(None)
        except Exception:
            pass
        finally:
            self.finished.emit(received_count, total)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Korg RK-100S 2 Patch Manager")
        self.resize(1100, 900)
        self._logger = AppLogger()
        self._library = Library(root=APP_ROOT)
        self._selected_patch: Patch | None = None
        self._selected_patch_path: Path | None = None
        self._pull_worker: PullWorker | None = None
        self._config = AppConfig()
        self._param_map = ParamMap()
        self._synth_editor: SynthEditorWindow | None = None
        self._build_ui()
        self._connect_signals()
        self._refresh_library()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._library_panel = LibraryPanel()
        self._detail_panel = PatchDetailPanel()
        self._device_panel = DevicePanel(config=self._config)
        h_splitter.addWidget(self._library_panel)
        h_splitter.addWidget(self._detail_panel)
        h_splitter.addWidget(self._device_panel)
        h_splitter.setSizes([250, 450, 300])

        self._log_panel = LogPanel()

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.addWidget(h_splitter)
        v_splitter.addWidget(self._log_panel)
        v_splitter.setSizes([720, 180])

        layout.addWidget(v_splitter)

    def _connect_signals(self) -> None:
        self._library_panel.patch_selected.connect(self._on_patch_selected)
        self._library_panel.add_patch_requested.connect(self._on_pull_prompted)
        self._detail_panel.patch_saved.connect(self._on_patch_saved)
        self._device_panel.pull_requested.connect(self._on_pull_prompted)
        self._device_panel.send_requested.connect(self._on_send_patch)
        self._device_panel.load_all_requested.connect(self._on_load_all)
        self._device_panel.load_range_requested.connect(self._on_load_range)
        self._device_panel.connected.connect(lambda _: self._library_panel.set_device_connected(True))
        self._device_panel.disconnected.connect(lambda: self._library_panel.set_device_connected(False))
        self._device_panel.connected.connect(self._on_device_connected)
        self._device_panel.disconnected.connect(self._on_device_disconnected)
        self._device_panel.synth_editor_requested.connect(self.open_synth_editor)
        self._logger.message_logged.connect(self._log_panel.append_message)

    def _refresh_library(self) -> None:
        banks = self._library.list_banks()
        patches = self._library.list_patches()
        self._library_panel.populate(banks=banks, patches=patches)

    def _on_patch_selected(self, patch: Patch) -> None:
        self._selected_patch = patch
        self._selected_patch_path = patch.source_path
        self._detail_panel.load_patch(patch)

    def _on_patch_saved(self, patch: Patch) -> None:
        if self._selected_patch_path and self._selected_patch_path.exists():
            patch.save(self._selected_patch_path)
        else:
            self._library.save_patch(patch)
        self._refresh_library()

    def _start_pull(self, slots: list[int]) -> None:
        device = self._device_panel.device
        if not device.connected:
            return
        self._set_action_buttons_enabled(False)

        total = len(slots)
        self._progress_dialog = QProgressDialog(
            f"Pulling slot 1 of {total}...", "Cancel", 0, total, self
        )
        self._progress_dialog.setWindowTitle("Loading Patches")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setValue(0)

        worker = PullWorker(device, slots, logger=self._logger, parent=self)
        self._pull_worker = worker
        self._progress_dialog.canceled.connect(worker.cancel)
        worker.patch_ready.connect(self._on_patch_ready)
        worker.progress.connect(self._on_pull_progress)
        worker.finished.connect(self._on_pull_finished)
        worker.start()

    def _on_patch_ready(self, patch: object) -> None:
        if patch is not None:
            self._library.save_patch(patch)

    def _on_pull_progress(self, done: int, total: int, message: str) -> None:
        self._progress_dialog.setValue(done)
        self._progress_dialog.setLabelText(message)

    def _on_pull_finished(self, received: int, total: int) -> None:
        self._progress_dialog.close()
        self._refresh_library()
        self._set_action_buttons_enabled(self._device_panel.device.connected)
        if total > 1:
            self.statusBar().showMessage(
                f"Done -- {received} of {total} patches received.", 5000
            )

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        for btn in (
            self._device_panel.send_btn,
            self._device_panel.pull_btn,
            self._device_panel.load_all_btn,
            self._device_panel.load_range_btn,
        ):
            btn.setEnabled(enabled)

    def _on_pull_prompted(self) -> None:
        slot, ok = QInputDialog.getInt(
            self, "Pull Program", "Slot to pull (0-127):", 0, 0, 127
        )
        if ok:
            self._start_pull([slot])

    def _on_send_patch(self) -> None:
        if self._selected_patch is None:
            QMessageBox.information(self, "No patch selected", "Select a patch first.")
            return
        patch = self._selected_patch
        if patch.sysex_data is None:
            QMessageBox.warning(self, "No SysEx data", "This patch has no SysEx data to send.")
            return
        self._device_panel.device.send(
            build_program_write(channel=1, data=patch.sysex_data)
        )

    def _on_load_all(self) -> None:
        reply = QMessageBox.question(
            self, "Load All Programs",
            "This will clear the current library and load all 128 programs from the device.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._library.clear_patches()
        self._refresh_library()
        self._start_pull(list(range(128)))

    def _on_load_range(self) -> None:
        start, ok1 = QInputDialog.getInt(
            self, "Load Slot Range", "Start slot (0-127):", 0, 0, 127
        )
        if not ok1:
            return
        end, ok2 = QInputDialog.getInt(
            self, "Load Slot Range", "End slot (0-127):", min(start + 40, 127), start, 127
        )
        if not ok2:
            return
        self._start_pull(list(range(start, end + 1)))

    # -- Synth Editor Window --

    def _get_or_create_synth_editor(self) -> SynthEditorWindow:
        if self._synth_editor is None:
            self._synth_editor = SynthEditorWindow(
                device=self._device_panel.device,
                param_map=self._param_map,
                config=self._config,
                logger=self._logger,
                parent=None,
            )
            # Sync current connection state
            if self._device_panel.device.connected:
                self._synth_editor.set_device_connected(True)
        return self._synth_editor

    def _on_device_connected(self, port_name: str) -> None:
        if self._synth_editor is not None:
            self._synth_editor.set_device_connected(True)

    def _on_device_disconnected(self) -> None:
        if self._synth_editor is not None:
            self._synth_editor.set_device_connected(False)

    def open_synth_editor(self) -> None:
        editor = self._get_or_create_synth_editor()
        editor.show()
        editor.raise_()
        editor.activateWindow()
