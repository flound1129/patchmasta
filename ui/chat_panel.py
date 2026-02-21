from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

import markdown


class ChatPanel(QWidget):
    message_sent = pyqtSignal(str)
    wav_dropped = pyqtSignal(str)  # file path
    match_requested = pyqtSignal(str)  # wav file path
    stop_requested = pyqtSignal()

    _USER_BUBBLE = (
        '<div style="text-align: right; margin: 6px 0;">'
        '<div style="display: inline-block; background-color: #2b7de9;'
        " color: #fff; border-radius: 12px; padding: 8px 14px;"
        ' max-width: 80%; text-align: left;">'
        "{body}</div></div>"
    )

    _AI_BUBBLE = (
        '<div style="text-align: left; margin: 6px 0;">'
        '<div style="display: inline-block; background-color: #e9ecef;'
        " color: #1a1a1a; border-radius: 12px; padding: 8px 14px;"
        ' max-width: 80%;">'
        "{body}</div></div>"
    )

    _TOOL_BUBBLE = (
        '<div style="text-align: left; margin: 4px 0;">'
        '<div style="display: inline-block; background-color: #f0f0f0;'
        " color: #666; border-radius: 8px; padding: 6px 12px;"
        ' max-width: 80%; font-style: italic;">'
        "{body}</div></div>"
    )

    _THINKING_TEXTS = ["Thinking.", "Thinking..", "Thinking..."]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._wav_path: str | None = None
        self._thinking_timer: QTimer | None = None
        self._thinking_phase: int = 0
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
        html = self._USER_BUBBLE.format(body=text)
        self.history.append(html)

    def append_ai_message(self, text: str) -> None:
        body = markdown.markdown(text, extensions=["fenced_code"])
        html = self._AI_BUBBLE.format(body=body)
        self.history.append(html)

    def append_tool_message(self, tool: str, result: str) -> None:
        html = self._TOOL_BUBBLE.format(body=f"⚙ {tool}: {result}")
        self.history.append(html)

    def set_thinking(self, thinking: bool) -> None:
        self.send_btn.setEnabled(not thinking)
        self.input_edit.setEnabled(not thinking)
        self.stop_btn.setEnabled(thinking)

        if thinking:
            self._thinking_phase = 0
            html = self._AI_BUBBLE.format(body=self._THINKING_TEXTS[0])
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
        html = self._AI_BUBBLE.format(body=new_text)
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
