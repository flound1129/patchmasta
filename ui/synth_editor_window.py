from __future__ import annotations
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QMessageBox, QTabWidget,
)
from PyQt6.QtCore import Qt
from ui.chat_panel import ChatPanel
from ui.synth_params_panel import SynthParamsPanel
from ui.synth_tabs import (
    TimbreSynthTab, ArpeggiatorTab, EffectsTab, VocoderTab, EQTab,
)
from ai.controller import AIController
from ai.llm import ClaudeBackend, GroqBackend
from midi.params import ParamMap
from midi.sysex_buffer import SysExProgramBuffer, DebouncedSysExWriter
from midi.sysex import build_program_write
from core.config import AppConfig
from core.logger import AppLogger


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
        self._sysex_buffer = SysExProgramBuffer()
        self._sysex_writer = DebouncedSysExWriter(
            debounce_ms=getattr(config, "sysex_write_debounce_ms", 150)
        )
        self._sysex_writer.write_requested.connect(self._flush_sysex)
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

        splitter.addWidget(chat_container)
        splitter.addWidget(self._tab_widget)
        splitter.setSizes([500, 1060])

        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        self._chat_panel.message_sent.connect(self._on_chat_message)
        self._chat_panel.match_requested.connect(self._on_match_sound)
        self._chat_panel.stop_requested.connect(self._on_stop_ai)
        self._chat_panel.backend_combo.currentTextChanged.connect(
            self._on_backend_changed
        )

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

    def set_device_connected(self, connected: bool) -> None:
        self._chat_panel.set_device_connected(connected)

    def closeEvent(self, event) -> None:
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
        self._ai_controller = ctrl
        return ctrl

    def _on_chat_message(self, text: str) -> None:
        self._chat_panel.append_user_message(text)
        ctrl = self._get_or_create_ai_controller()
        if ctrl:
            self._chat_panel.set_thinking(True)
            ctrl.send_message(text)

    def _on_match_sound(self, wav_path: str) -> None:
        ctrl = self._get_or_create_ai_controller()
        if ctrl:
            self._chat_panel.set_thinking(True)
            ctrl.match_sound(wav_path)

    def _on_stop_ai(self) -> None:
        if self._ai_controller:
            self._ai_controller.stop()
        self._chat_panel.set_thinking(False)

    def _on_ai_response(self, text: str) -> None:
        self._chat_panel.append_ai_message(text)
        self._chat_panel.set_thinking(False)

    def _on_ai_tool(self, tool_name: str, result: str) -> None:
        self._chat_panel.append_tool_message(tool_name, result)

    def _on_ai_error(self, error: str) -> None:
        self._chat_panel.append_ai_message(f"Error: {error}")
        self._chat_panel.set_thinking(False)
