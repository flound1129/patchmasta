from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QMessageBox, QSlider,
)
from PyQt6.QtCore import Qt as QtCore_Qt
from PyQt6.QtCore import pyqtSignal
from midi.device import MidiDevice, list_midi_ports, find_rk100s2_port
from audio.engine import AudioMonitor, list_audio_input_devices
from core.config import AppConfig


class DevicePanel(QWidget):
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    send_requested = pyqtSignal()
    pull_requested = pyqtSignal()
    load_all_requested = pyqtSignal()
    load_range_requested = pyqtSignal()

    def __init__(self, config: AppConfig | None = None, parent=None) -> None:
        super().__init__(parent)
        self._config = config or AppConfig()
        self._device = MidiDevice()
        self._audio_monitor = AudioMonitor()
        self._build_ui()
        self._refresh_ports()
        self._refresh_audio_devices()
        # Now that the combo is populated, init monitor with the resolved index
        self._audio_monitor = AudioMonitor(device=self.audio_device_combo.currentData())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        conn_group = QGroupBox("Device")
        conn_layout = QVBoxLayout(conn_group)

        self.port_combo = QComboBox()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._on_refresh)
        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo)
        port_row.addWidget(refresh_btn)
        conn_layout.addLayout(port_row)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connect)
        conn_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("Not connected")
        conn_layout.addWidget(self.status_label)

        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("Audio Input:"))
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.currentIndexChanged.connect(self._on_audio_device_changed)
        audio_row.addWidget(self.audio_device_combo, stretch=1)
        conn_layout.addLayout(audio_row)

        monitor_row = QHBoxLayout()
        self.monitor_btn = QPushButton("Monitor Audio")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.setEnabled(False)
        self.monitor_btn.toggled.connect(self._toggle_monitor)
        monitor_row.addWidget(self.monitor_btn)

        self._gain_label = QLabel("Gain: 1.0x")
        self.gain_slider = QSlider(QtCore_Qt.Orientation.Horizontal)
        self.gain_slider.setRange(10, 200)  # 1.0x to 20.0x
        self.gain_slider.setValue(10)
        self.gain_slider.setTickInterval(10)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        monitor_row.addWidget(self._gain_label)
        monitor_row.addWidget(self.gain_slider, stretch=1)
        conn_layout.addLayout(monitor_row)

        layout.addWidget(conn_group)

        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        self.send_btn = QPushButton("Send Patch to Device")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.send_requested)
        action_layout.addWidget(self.send_btn)

        self.pull_btn = QPushButton("Pull Current Program")
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self.pull_requested)
        action_layout.addWidget(self.pull_btn)

        self.load_all_btn = QPushButton("Load All Programs (128)")
        self.load_all_btn.setEnabled(False)
        self.load_all_btn.clicked.connect(self.load_all_requested)
        action_layout.addWidget(self.load_all_btn)

        self.load_range_btn = QPushButton("Load Slot Range...")
        self.load_range_btn.setEnabled(False)
        self.load_range_btn.clicked.connect(self.load_range_requested)
        action_layout.addWidget(self.load_range_btn)

        layout.addWidget(action_group)
        layout.addStretch()

    def _on_refresh(self) -> None:
        self._refresh_ports()
        self._refresh_audio_devices()

    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        ports = list_midi_ports()
        for name in ports:
            self.port_combo.addItem(name)
        idx = find_rk100s2_port(ports)
        if idx is not None:
            self.port_combo.setCurrentIndex(idx)

    def _refresh_audio_devices(self) -> None:
        self.audio_device_combo.blockSignals(True)
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("(default)", None)
        saved = self._config.audio_input_device
        select = 0
        for dev_index, name in list_audio_input_devices():
            self.audio_device_combo.addItem(name, dev_index)
            if saved is not None and name == saved:
                select = self.audio_device_combo.count() - 1
        self.audio_device_combo.setCurrentIndex(select)
        self.audio_device_combo.blockSignals(False)

    def _on_audio_device_changed(self, idx: int) -> None:
        dev_index = self.audio_device_combo.currentData()
        dev_name = self.audio_device_combo.currentText() if dev_index is not None else None
        self._config.audio_input_device = dev_name if dev_index is not None else None
        self._config.save()
        was_running = self._audio_monitor.is_running
        self._audio_monitor.stop()
        self._audio_monitor = AudioMonitor(device=dev_index)
        if was_running:
            self._audio_monitor.start()

    def _toggle_connect(self) -> None:
        if self._device.connected:
            self._device.disconnect()
            self._set_connected(False)
        else:
            idx = self.port_combo.currentIndex()
            name = self.port_combo.currentText()
            if idx >= 0:
                try:
                    self._device.connect(idx, name)
                    self._set_connected(True)
                except Exception as exc:
                    QMessageBox.critical(self, "Connection Failed", str(exc))

    def _set_connected(self, state: bool) -> None:
        for btn in (self.send_btn, self.pull_btn, self.load_all_btn, self.load_range_btn):
            btn.setEnabled(state)
        if state:
            self.connect_btn.setText("Disconnect")
            self.status_label.setText(f"Connected: {self._device.port_name}")
            self.monitor_btn.setEnabled(True)
            self.connected.emit(self._device.port_name or "")
        else:
            self._audio_monitor.stop()
            self.monitor_btn.setChecked(False)
            self.monitor_btn.setEnabled(False)
            self.connect_btn.setText("Connect")
            self.status_label.setText("Not connected")
            self.disconnected.emit()

    def _toggle_monitor(self, checked: bool) -> None:
        if checked:
            self._audio_monitor.start()
            self.monitor_btn.setText("Stop Monitor")
        else:
            self._audio_monitor.stop()
            self.monitor_btn.setText("Monitor Audio")

    def _on_gain_changed(self, value: int) -> None:
        gain = value / 10.0
        self._gain_label.setText(f"Gain: {gain:.1f}x")
        self._audio_monitor.gain = gain

    @property
    def device(self) -> MidiDevice:
        return self._device
