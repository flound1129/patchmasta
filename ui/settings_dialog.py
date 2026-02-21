from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
)  # noqa: F401 — QLineEdit still used by key fields
from core.config import AppConfig
from core.theme import apply_theme, THEMES


_THEME_LABELS = [
    ("auto", "Auto (System)"),
    ("light", "Light"),
    ("dark", "Dark"),
    ("korg", "Korg"),
    ("ocean", "Ocean"),
    ("sunset", "Sunset"),
]


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._config = config
        self._build_ui()
        self._load_from_config()

    @property
    def selected_theme(self) -> str:
        return self.theme_combo.currentData()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)

        self.theme_combo = QComboBox()
        for key, label in _THEME_LABELS:
            self.theme_combo.addItem(label, key)
        layout.addRow("Theme:", self.theme_combo)

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_from_config(self) -> None:
        # Theme
        idx = self.theme_combo.findData(self._config.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        idx = self.backend_combo.findText(self._config.ai_backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self.claude_key_edit.setText(self._config.claude_api_key)
        self.groq_key_edit.setText(self._config.groq_api_key)

    def _on_accept(self) -> None:
        self._config.theme = self.selected_theme
        self._config.ai_backend = self.backend_combo.currentText()
        self._config.claude_api_key = self.claude_key_edit.text()
        self._config.groq_api_key = self.groq_key_edit.text()
        self._config.save()
        self.accept()
