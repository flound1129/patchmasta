from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class ChatPanel(QWidget):
    message_sent = pyqtSignal(str)
    wav_dropped = pyqtSignal(str)  # file path
    match_requested = pyqtSignal(str)  # wav file path
    stop_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._wav_path: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header with backend selector
        header = QHBoxLayout()
        header.addWidget(QLabel("AI Backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Claude", "Groq"])
        header.addWidget(self.backend_combo)
        header.addStretch()
        layout.addLayout(header)

        # WAV drop zone
        wav_row = QHBoxLayout()
        self._wav_label = QLabel("No WAV loaded")
        wav_btn = QPushButton("Load WAV...")
        wav_btn.clicked.connect(self._pick_wav)
        self.match_btn = QPushButton("Match Sound")
        self.match_btn.setEnabled(False)
        self.match_btn.clicked.connect(self._on_match)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested)
        wav_row.addWidget(self._wav_label, stretch=1)
        wav_row.addWidget(wav_btn)
        wav_row.addWidget(self.match_btn)
        wav_row.addWidget(self.stop_btn)
        layout.addLayout(wav_row)

        # Conversation history
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setFont(QFont("Courier", 11))
        layout.addWidget(self.history, stretch=1)

        # Input row
        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Describe the sound you want...")
        self.input_edit.returnPressed.connect(self._on_send)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.input_edit, stretch=1)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

    def _on_send(self) -> None:
        text = self.input_edit.text().strip()
        if text:
            self.input_edit.clear()
            self.message_sent.emit(text)

    def _pick_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select WAV file", "", "WAV files (*.wav)"
        )
        if path:
            self._wav_path = path
            self._wav_label.setText(path.split("/")[-1])
            self.match_btn.setEnabled(True)
            self.wav_dropped.emit(path)

    def _on_match(self) -> None:
        if self._wav_path:
            self.match_requested.emit(self._wav_path)

    def append_user_message(self, text: str) -> None:
        self.history.append(f"<b>You:</b> {text}")

    def append_ai_message(self, text: str) -> None:
        self.history.append(f"<b>AI:</b> {text}")

    def append_tool_message(self, tool: str, result: str) -> None:
        self.history.append(f"<i>⚙ {tool}: {result}</i>")

    def set_thinking(self, thinking: bool) -> None:
        self.send_btn.setEnabled(not thinking)
        self.input_edit.setEnabled(not thinking)
        self.stop_btn.setEnabled(thinking)
