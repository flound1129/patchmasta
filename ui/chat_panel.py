from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

import markdown

from core.theme import get_theme


class ChatPanel(QWidget):
    message_sent = pyqtSignal(str)
    wav_dropped = pyqtSignal(str)  # file path
    match_requested = pyqtSignal(str)  # wav file path
    stop_requested = pyqtSignal()

    _THINKING_TEXTS = ["Thinking.", "Thinking..", "Thinking..."]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._theme_name: str = "auto"
        self._wav_path: str | None = None
        self._thinking_timer: QTimer | None = None
        self._thinking_phase: int = 0
        self._device_connected: bool = False
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
        self.history.setFont(QFont("sans-serif", 11))
        layout.addWidget(self.history, stretch=1)

        # Input row
        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Connect a device to start chatting")
        self.input_edit.setEnabled(False)
        self.input_edit.returnPressed.connect(self._on_send)
        self.send_btn = QPushButton("Send")
        self.send_btn.setEnabled(False)
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
            self.match_btn.setEnabled(self._device_connected)
            self.wav_dropped.emit(path)

    def _on_match(self) -> None:
        if self._wav_path:
            self.match_requested.emit(self._wav_path)

    def set_theme(self, name: str) -> None:
        """Store theme name so new messages use its bubble colors."""
        self._theme_name = name

    def _user_bubble_html(self, body: str) -> str:
        c = get_theme(self._theme_name)
        return (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px;">'
            '<tr><td width="25%"></td>'
            f'<td style="background-color:{c.user_bubble_bg}; color:{c.user_bubble_text}; padding:8px 12px;">'
            f"{body}</td></tr></table>"
        )

    def _ai_bubble_html(self, body: str) -> str:
        c = get_theme(self._theme_name)
        return (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px;">'
            "<tr>"
            f'<td style="background-color:{c.ai_bubble_bg}; color:{c.ai_bubble_text}; padding:8px 12px;">'
            f"{body}</td>"
            '<td width="10%"></td></tr></table>'
        )

    def _tool_bubble_html(self, body: str) -> str:
        c = get_theme(self._theme_name)
        return (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:2px;">'
            "<tr>"
            f'<td style="background-color:{c.tool_bubble_bg}; color:{c.tool_bubble_text}; padding:4px 12px;'
            ' font-style:italic; font-size:small;">'
            f"{body}</td>"
            '<td width="10%"></td></tr></table>'
        )

    def append_user_message(self, text: str) -> None:
        self.history.append(self._user_bubble_html(text))

    def append_ai_message(self, text: str) -> None:
        body = markdown.markdown(text, extensions=["fenced_code"])
        self.history.append(self._ai_bubble_html(body))

    def append_tool_message(self, tool: str, result: str) -> None:
        self.history.append(self._tool_bubble_html(f"⚙ {tool}: {result}"))

    def set_device_connected(self, connected: bool) -> None:
        self._device_connected = connected
        self.input_edit.setEnabled(connected)
        self.send_btn.setEnabled(connected)
        self.match_btn.setEnabled(connected and self._wav_path is not None)
        self.input_edit.setPlaceholderText(
            "Describe the sound you want..."
            if connected
            else "Connect a device to start chatting"
        )

    def set_thinking(self, thinking: bool) -> None:
        can_input = self._device_connected and not thinking
        self.send_btn.setEnabled(can_input)
        self.input_edit.setEnabled(can_input)
        self.stop_btn.setEnabled(thinking)

        if thinking:
            self._thinking_phase = 0
            html = self._ai_bubble_html(self._THINKING_TEXTS[0])
            self.history.append(html)
            self._thinking_timer = QTimer(self)
            self._thinking_timer.setInterval(500)
            self._thinking_timer.timeout.connect(self._cycle_thinking)
            self._thinking_timer.start()
        else:
            if self._thinking_timer is not None:
                self._thinking_timer.stop()
                self._thinking_timer = None
            self._remove_last_block()

    def _cycle_thinking(self) -> None:
        self._thinking_phase = (self._thinking_phase + 1) % len(self._THINKING_TEXTS)
        new_text = self._THINKING_TEXTS[self._thinking_phase]
        # Replace content of the last block
        self._remove_last_block()
        html = self._ai_bubble_html(new_text)
        self.history.append(html)

    def _remove_last_block(self) -> None:
        cursor = self.history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(
            QTextCursor.MoveOperation.StartOfBlock,
            QTextCursor.MoveMode.MoveAnchor,
        )
        # Select to end
        cursor.movePosition(
            QTextCursor.MoveOperation.End,
            QTextCursor.MoveMode.KeepAnchor,
        )
        # Also grab the preceding newline if present
        if cursor.selectionStart() > 0:
            cursor.setPosition(cursor.selectionStart() - 1, QTextCursor.MoveMode.MoveAnchor)
            cursor.movePosition(
                QTextCursor.MoveOperation.End,
                QTextCursor.MoveMode.KeepAnchor,
            )
        cursor.removeSelectedText()
