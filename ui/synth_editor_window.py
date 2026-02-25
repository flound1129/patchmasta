from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QMessageBox, QTabWidget, QToolBar, QFileDialog,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QAction
from ui.chat_panel import ChatPanel
from ui.keyboard_widget import KeyboardPanel, TransportPanel
from ui.synth_params_panel import SynthParamsPanel
from ui.synth_tabs import (
    TimbreSynthTab, ArpeggiatorTab, EffectsTab, VocoderTab, EQTab,
)
from ai.controller import AIController
from ai.llm import ClaudeBackend, GroqBackend
from midi.params import ParamMap
from midi.sysex_buffer import SysExProgramBuffer, DebouncedSysExWriter
from midi.sysex import build_program_write, extract_patch_name
from midi.player import MidiFilePlayer
from tools.file_format import sysex_to_prog_bytes
from core.config import AppConfig
from core.chat_db import ChatHistoryDB
from core.logger import AppLogger


class _NoteSignalBridge(QObject):
    """Thread-safe bridge from MIDI input thread to Qt main thread."""
    note_received = pyqtSignal(int, int, bool)  # note, velocity, is_on


class SynthEditorWindow(QMainWindow):
    """Separate window combining AI chat with synth parameter controls."""

    def __init__(
        self,
        device,
        param_map: ParamMap,
        config: AppConfig,
        logger: AppLogger,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Synth Editor")
        self.resize(1560, 800)
        self._device = device
        self._param_map = param_map
        self._config = config
        self._logger = logger
        self._ai_controller: AIController | None = None
        self._chat_db = ChatHistoryDB()
        self._conversation_id: int | None = None
        self._sysex_buffer = SysExProgramBuffer()
        self._sysex_writer = DebouncedSysExWriter(
            debounce_ms=getattr(config, "sysex_write_debounce_ms", 150)
        )
        self._sysex_writer.write_requested.connect(self._flush_sysex)
        self._note_bridge = _NoteSignalBridge(self)
        self._midi_player: MidiFilePlayer | None = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: chat panel
        chat_container = QWidget()
        chat_layout = QHBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self._chat_panel = ChatPanel()
        chat_layout.addWidget(self._chat_panel)

        # Right: tabbed parameter editor
        self._tab_widget = QTabWidget()

        # Overview tab (the original SynthParamsPanel)
        self._params_panel = SynthParamsPanel(
            param_map=self._param_map,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._params_panel, "Overview")

        # Timbre 1 Synth tab
        self._timbre1_tab = TimbreSynthTab(
            param_map=self._param_map, timbre=1,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._timbre1_tab, "Timbre 1 Synth")

        # Timbre 2 Synth tab
        self._timbre2_tab = TimbreSynthTab(
            param_map=self._param_map, timbre=2,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._timbre2_tab, "Timbre 2 Synth")

        # Arpeggiator tab
        self._arp_tab = ArpeggiatorTab(
            param_map=self._param_map,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._arp_tab, "Arpeggiator")

        # Effects tab
        self._effects_tab = EffectsTab(
            param_map=self._param_map,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._effects_tab, "Effects")

        # Vocoder tab
        self._vocoder_tab = VocoderTab(
            param_map=self._param_map,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._vocoder_tab, "Vocoder")

        # EQ + Ribbon tab
        self._eq_tab = EQTab(
            param_map=self._param_map,
            on_user_change=self._on_user_param_change,
        )
        self._tab_widget.addTab(self._eq_tab, "EQ / Ribbon")

        # Right side: tabs on top, transport bar, keyboard on bottom
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self._tab_widget)
        self._transport_panel = TransportPanel()
        right_splitter.addWidget(self._transport_panel)
        self._keyboard_panel = KeyboardPanel()
        right_splitter.addWidget(self._keyboard_panel)
        right_splitter.setStretchFactor(0, 1)  # tabs stretch
        right_splitter.setStretchFactor(1, 0)  # transport fixed
        right_splitter.setStretchFactor(2, 0)  # keyboard fixed
        right_splitter.setCollapsible(1, False)
        right_splitter.setCollapsible(2, False)
        right_splitter.setSizes([656, 44, 100])

        splitter.addWidget(chat_container)
        splitter.addWidget(right_splitter)
        splitter.setSizes([500, 1060])

        layout.addWidget(splitter)

        # Toolbar
        toolbar = QToolBar("File")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self._save_action = QAction("Save Patch...", self)
        self._save_action.setEnabled(False)
        self._save_action.triggered.connect(self._on_save_patch)
        toolbar.addAction(self._save_action)

    def _connect_signals(self) -> None:
        self._chat_panel.message_sent.connect(self._on_chat_message)
        self._chat_panel.match_requested.connect(self._on_match_sound)
        self._chat_panel.stop_requested.connect(self._on_stop_ai)
        self._chat_panel.backend_combo.currentTextChanged.connect(
            self._on_backend_changed
        )
        # Keyboard click → device
        self._keyboard_panel.note_pressed.connect(self._on_keyboard_note_pressed)
        self._keyboard_panel.note_released.connect(self._on_keyboard_note_released)
        # MIDI input thread → main thread bridge → keyboard
        self._note_bridge.note_received.connect(self._on_midi_note_received)
        # Transport panel signals
        self._transport_panel.load_requested.connect(self._on_load_midi)
        self._transport_panel.play_pause_requested.connect(self._on_play_pause)
        self._transport_panel.stop_requested.connect(self._on_transport_stop)
        self._transport_panel.rewind_requested.connect(self._on_rewind)
        self._transport_panel.seek_requested.connect(self._on_seek)
        self._transport_panel.tempo_changed.connect(self._on_tempo_changed)
        self._transport_panel.loop_toggled.connect(self._on_loop_toggled)

    # -- Keyboard / note handling --

    def _on_keyboard_note_pressed(self, note: int, velocity: int) -> None:
        if self._device.connected:
            self._device.send_note_on(channel=1, note=note, velocity=velocity)
        self._keyboard_panel.note_on(note, velocity)

    def _on_keyboard_note_released(self, note: int) -> None:
        if self._device.connected:
            self._device.send_note_off(channel=1, note=note)
        self._keyboard_panel.note_off(note)

    def _on_midi_note_received(self, note: int, velocity: int, is_on: bool) -> None:
        if is_on:
            self._keyboard_panel.note_on(note, velocity)
        else:
            self._keyboard_panel.note_off(note)

    def _on_ai_note_played(self, note: int, velocity: int, is_on: bool) -> None:
        if is_on:
            self._keyboard_panel.note_on(note, velocity)
        else:
            self._keyboard_panel.note_off(note)

    # -- Parameter change handling --

    def _on_user_param_change(self, name: str, value: int) -> None:
        """User adjusted a synth control widget -- send MIDI to device."""
        param = self._param_map.get(name)
        if param is None:
            # Dynamic FX effect param (not in ParamMap) — SysEx-only write
            if self._device.connected:
                packed = self._effects_tab.get_fx_sysex_offset(name)
                if packed is not None and self._sysex_buffer.size > 0:
                    self._sysex_buffer.set_byte(packed, value)
                    self._sysex_writer.schedule()
            return

        if not self._device.connected:
            return

        # NRPN/CC params: send real-time MIDI
        if param.is_nrpn or param.cc_number is not None:
            msg = param.build_message(channel=1, value=value)
            for i in range(0, len(msg), 3):
                self._device.send(msg[i:i + 3])

        # SysEx-only params: update buffer and debounce write
        if param.sysex_offset is not None and self._sysex_buffer.size > 0:
            self._sysex_buffer.set_param(param, value)
            self._sysex_writer.schedule()

    def _flush_sysex(self) -> None:
        """Write the full program buffer to the device via SysEx."""
        if not self._sysex_buffer.dirty or not self._device.connected:
            return
        data = self._sysex_buffer.to_bytes()
        msg = build_program_write(channel=1, data=data)
        self._device.send(msg)
        self._sysex_buffer.mark_clean()
        self._logger.midi("SysEx program write sent")

    def load_program_data(self, data: bytes) -> None:
        """Load program SysEx data into buffer and update all UI widgets."""
        self._sysex_buffer.load(data)
        self._save_action.setEnabled(True)
        # Update UI from buffer for all ParamMap params (includes fx1_type/fx2_type,
        # which triggers dynamic FX widget rebuild in EffectsTab)
        for p in self._param_map.list_all():
            if p.sysex_offset is not None:
                val = self._sysex_buffer.get_param(p)
                if val is not None:
                    self._dispatch_param_to_ui(p.name, val)
        # Now populate dynamic FX params (rebuilt above when fx_type was dispatched)
        for name, packed in self._effects_tab.fx_sysex_items():
            if packed < self._sysex_buffer.size:
                val = self._sysex_buffer.get_byte(packed)
                self._effects_tab.on_param_changed(name, val)

    def _dispatch_param_to_ui(self, name: str, value: int) -> None:
        """Update the correct tab widget for a parameter change."""
        self._params_panel.on_param_changed(name, value)
        self._timbre1_tab.on_param_changed(name, value)
        self._timbre2_tab.on_param_changed(name, value)
        self._arp_tab.on_param_changed(name, value)
        self._effects_tab.on_param_changed(name, value)
        self._vocoder_tab.on_param_changed(name, value)
        self._eq_tab.on_param_changed(name, value)

    def _on_save_patch(self) -> None:
        """Save the current program buffer to a .rk100s2_prog file."""
        if self._sysex_buffer.size == 0:
            return
        sysex_data = self._sysex_buffer.to_bytes()
        name = extract_patch_name(sysex_data) or "patch"
        suggested = name.strip().replace(" ", "_") + ".rk100s2_prog"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Patch", suggested,
            "RK-100S 2 Patch (*.rk100s2_prog)",
        )
        if not path:
            return
        try:
            file_bytes = sysex_to_prog_bytes(sysex_data)
            Path(path).write_bytes(file_bytes)
            self._logger.info(f"Saved patch to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def set_device_connected(self, connected: bool) -> None:
        self._chat_panel.set_device_connected(connected)
        if connected:
            self._device.set_note_callback(
                lambda note, vel, is_on: self._note_bridge.note_received.emit(
                    note, vel, is_on
                )
            )
        else:
            self._keyboard_panel.clear_all_notes()

    # -- MIDI file player --

    def _get_or_create_midi_player(self) -> MidiFilePlayer:
        if self._midi_player is not None:
            return self._midi_player
        player = MidiFilePlayer(self)
        # Device output
        player.set_send_note_on(
            lambda ch, note, vel: (
                self._device.send_note_on(channel=ch, note=note, velocity=vel)
                if self._device.connected else None
            )
        )
        player.set_send_note_off(
            lambda ch, note: (
                self._device.send_note_off(channel=ch, note=note)
                if self._device.connected else None
            )
        )
        player.set_send_all_notes_off(
            lambda: (
                self._device.send_cc(channel=1, cc=120, value=0)
                if self._device.connected else None
            )
        )
        # Keyboard visualisation
        player.note_on.connect(self._keyboard_panel.note_on)
        player.note_off.connect(self._keyboard_panel.note_off)
        # Transport feedback
        player.position_changed.connect(self._transport_panel.update_position)
        player.file_loaded.connect(self._transport_panel.set_file_loaded)
        player.playback_finished.connect(self._on_playback_finished)
        self._midi_player = player
        return player

    def _on_load_midi(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load MIDI File", "",
            "MIDI Files (*.mid *.midi);;All Files (*)",
        )
        if path:
            player = self._get_or_create_midi_player()
            player.load_file(path)

    def _on_play_pause(self) -> None:
        player = self._get_or_create_midi_player()
        if player.playing:
            player.toggle_pause()
            self._transport_panel.set_playing(not player.paused)
        else:
            player.play()
            self._transport_panel.set_playing(True)
        self._update_ai_note_suppression()

    def _on_transport_stop(self) -> None:
        if self._midi_player is not None:
            self._midi_player.stop()
        self._transport_panel.reset()
        self._keyboard_panel.clear_all_notes()
        self._update_ai_note_suppression()

    def _on_rewind(self) -> None:
        if self._midi_player is not None:
            self._midi_player.seek(0)

    def _on_seek(self, seconds: float) -> None:
        if self._midi_player is not None:
            self._midi_player.seek(seconds)

    def _on_tempo_changed(self, factor: float) -> None:
        if self._midi_player is not None:
            self._midi_player.set_tempo_factor(factor)

    def _on_loop_toggled(self, enabled: bool) -> None:
        if self._midi_player is not None:
            self._midi_player.set_loop(enabled)

    def _on_playback_finished(self) -> None:
        # Fully reset the player (position, thread, notes) so replay works correctly
        if self._midi_player is not None:
            self._midi_player.stop()
        self._transport_panel.reset()
        self._keyboard_panel.clear_all_notes()
        self._update_ai_note_suppression()

    def _update_ai_note_suppression(self) -> None:
        """Suppress AI test notes and SysEx writes while MIDI is playing.

        Large SysEx program dumps (~400 bytes) block the MIDI output port
        for ~130ms, causing audible timing jitter in the player.  NRPN/CC
        messages (3 bytes) are unaffected and continue in real-time.
        Deferred SysEx changes flush automatically when playback stops.
        """
        playing = (self._midi_player is not None
                   and self._midi_player.playing
                   and not self._midi_player.paused)
        if self._ai_controller is not None:
            self._ai_controller._suppress_notes = playing
        if playing:
            self._sysex_writer.cancel()
            self._sysex_writer._suppressed = True
        else:
            self._sysex_writer._suppressed = False
            if self._sysex_buffer.dirty:
                self._sysex_writer.schedule()

    def closeEvent(self, event) -> None:
        if self._midi_player is not None:
            self._midi_player.stop()
            self._midi_player = None
        self._transport_panel.reset()
        self._keyboard_panel.clear_all_notes()
        self._update_ai_note_suppression()
        self.hide()
        event.ignore()

    # -- AI controller management --

    def _on_backend_changed(self) -> None:
        self._ai_controller = None

    def _get_or_create_ai_controller(self) -> AIController | None:
        if self._ai_controller is not None:
            return self._ai_controller
        backend_name = self._chat_panel.backend_combo.currentText().lower()
        if backend_name == "claude":
            if not self._config.claude_api_key:
                QMessageBox.warning(self, "No API Key", "Set claude_api_key in ~/.config/patchmasta/config.json")
                return None
            backend = ClaudeBackend(api_key=self._config.claude_api_key)
        else:
            if not self._config.groq_api_key:
                QMessageBox.warning(self, "No API Key", "Set groq_api_key in ~/.config/patchmasta/config.json")
                return None
            backend = GroqBackend(api_key=self._config.groq_api_key)
        ctrl = AIController(
            backend=backend,
            device=self._device,
            param_map=self._param_map,
            logger=self._logger,
            sysex_buffer=self._sysex_buffer,
            sysex_writer=self._sysex_writer,
        )
        ctrl.response_ready.connect(self._on_ai_response)
        ctrl.tool_executed.connect(self._on_ai_tool)
        ctrl.error.connect(self._on_ai_error)
        ctrl.parameter_changed.connect(self._dispatch_param_to_ui)
        ctrl.note_played.connect(self._on_ai_note_played)
        self._ai_controller = ctrl
        self._update_ai_note_suppression()
        self._conversation_id = self._chat_db.add_conversation(backend_name)
        return ctrl

    def _on_chat_message(self, text: str) -> None:
        self._chat_panel.append_user_message(text)
        ctrl = self._get_or_create_ai_controller()
        if ctrl:
            self._chat_db.add_message(self._conversation_id, "user", text)
            self._chat_panel.set_thinking(True)
            ctrl.send_message(text)

    def _on_match_sound(self, wav_path: str) -> None:
        ctrl = self._get_or_create_ai_controller()
        if ctrl:
            self._chat_db.add_message(
                self._conversation_id, "user", "Match sound", wav_path=wav_path
            )
            self._chat_panel.set_thinking(True)
            ctrl.match_sound(wav_path)

    def _on_stop_ai(self) -> None:
        if self._ai_controller:
            self._ai_controller.stop()
        self._chat_panel.set_thinking(False)

    def _on_ai_response(self, text: str) -> None:
        if self._conversation_id is not None:
            self._chat_db.add_message(self._conversation_id, "assistant", text)
        self._chat_panel.append_ai_message(text)
        self._chat_panel.set_thinking(False)

    def _on_ai_tool(self, tool_name: str, result: str) -> None:
        if self._conversation_id is not None:
            self._chat_db.add_message(
                self._conversation_id, "tool", result, tool_name=tool_name
            )
        self._chat_panel.append_tool_message(tool_name, result)

    def _on_ai_error(self, error: str) -> None:
        self._chat_panel.append_ai_message(f"Error: {error}")
        self._chat_panel.set_thinking(False)
