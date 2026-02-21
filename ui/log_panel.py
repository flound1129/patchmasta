from __future__ import annotations
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG


class LogPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))
        self.log_text.setMaximumBlockCount(5000)
        layout.addWidget(self.log_text)

        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy Log")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.log_text.clear)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.copy_btn)
        layout.addLayout(btn_row)

    def append_message(self, category: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{category}] {message}"
        QMetaObject.invokeMethod(
            self.log_text, "appendPlainText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, line),
        )

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.log_text.toPlainText())
