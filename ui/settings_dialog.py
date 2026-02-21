from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
)
from core.config import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._config = config
        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["claude", "groq"])
        layout.addRow("AI Backend:", self.backend_combo)

        self.claude_key_edit = QLineEdit()
        self.claude_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.claude_key_edit.setPlaceholderText("sk-ant-...")
        layout.addRow("Claude API Key:", self.claude_key_edit)

        self.groq_key_edit = QLineEdit()
        self.groq_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key_edit.setPlaceholderText("gsk_...")
        layout.addRow("Groq API Key:", self.groq_key_edit)

        self.audio_device_edit = QLineEdit()
        self.audio_device_edit.setPlaceholderText("(default)")
        layout.addRow("Audio Input Device:", self.audio_device_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_from_config(self) -> None:
        idx = self.backend_combo.findText(self._config.ai_backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self.claude_key_edit.setText(self._config.claude_api_key)
        self.groq_key_edit.setText(self._config.groq_api_key)
        self.audio_device_edit.setText(self._config.audio_input_device or "")

    def _on_accept(self) -> None:
        self._config.ai_backend = self.backend_combo.currentText()
        self._config.claude_api_key = self.claude_key_edit.text()
        self._config.groq_api_key = self.groq_key_edit.text()
        device = self.audio_device_edit.text().strip()
        self._config.audio_input_device = device if device else None
        self._config.save()
        self.accept()
