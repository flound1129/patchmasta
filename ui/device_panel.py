from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal
from midi.device import MidiDevice, list_midi_ports, find_rk100s2_port


class DevicePanel(QWidget):
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    send_requested = pyqtSignal()
    pull_requested = pyqtSignal()
    load_all_requested = pyqtSignal()
    load_range_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._device = MidiDevice()
        self._build_ui()
        self._refresh_ports()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        conn_group = QGroupBox("Device")
        conn_layout = QVBoxLayout(conn_group)

        self.port_combo = QComboBox()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo)
        port_row.addWidget(refresh_btn)
        conn_layout.addLayout(port_row)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connect)
        conn_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("Not connected")
        conn_layout.addWidget(self.status_label)
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

        self.load_all_btn = QPushButton("Load All Programs (200)")
        self.load_all_btn.setEnabled(False)
        self.load_all_btn.clicked.connect(self.load_all_requested)
        action_layout.addWidget(self.load_all_btn)

        self.load_range_btn = QPushButton("Load Slot Range...")
        self.load_range_btn.setEnabled(False)
        self.load_range_btn.clicked.connect(self.load_range_requested)
        action_layout.addWidget(self.load_range_btn)

        layout.addWidget(action_group)
        layout.addStretch()

    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        ports = list_midi_ports()
        for name in ports:
            self.port_combo.addItem(name)
        idx = find_rk100s2_port(ports)
        if idx is not None:
            self.port_combo.setCurrentIndex(idx)

    def _toggle_connect(self) -> None:
        if self._device.connected:
            self._device.disconnect()
            self._set_connected(False)
        else:
            idx = self.port_combo.currentIndex()
            name = self.port_combo.currentText()
            if idx >= 0:
                self._device.connect(idx, name)
                self._set_connected(True)

    def _set_connected(self, state: bool) -> None:
        for btn in (self.send_btn, self.pull_btn, self.load_all_btn, self.load_range_btn):
            btn.setEnabled(state)
        if state:
            self.connect_btn.setText("Disconnect")
            self.status_label.setText(f"Connected: {self._device.port_name}")
            self.connected.emit(self._device.port_name)
        else:
            self.connect_btn.setText("Connect")
            self.status_label.setText("Not connected")
            self.disconnected.emit()

    @property
    def device(self) -> MidiDevice:
        return self._device
