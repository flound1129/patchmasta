from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QVBoxLayout,
    QLineEdit, QSpinBox, QTextEdit, QPushButton,
)
from PyQt6.QtCore import pyqtSignal
from model.patch import Patch


class PatchDetailPanel(QWidget):
    patch_saved = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._patch: Patch | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, 127)
        self.category_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)

        form.addRow("Name:", self.name_edit)
        form.addRow("Slot (0-127):", self.slot_spin)
        form.addRow("Category:", self.category_edit)
        form.addRow("Notes:", self.notes_edit)
        layout.addLayout(form)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save)
        layout.addWidget(self.save_btn)
        layout.addStretch()

    def load_patch(self, patch: Patch) -> None:
        self._patch = patch
        self.name_edit.setText(patch.name)
        self.slot_spin.setValue(patch.program_number)
        self.category_edit.setText(patch.category)
        self.notes_edit.setPlainText(patch.notes)

    def _on_save(self) -> None:
        if self._patch is None:
            return
        self._patch.name = self.name_edit.text()
        self._patch.program_number = self.slot_spin.value()
        self._patch.category = self.category_edit.text()
        self._patch.notes = self.notes_edit.toPlainText()
        self.patch_saved.emit(self._patch)

    def clear(self) -> None:
        self._patch = None
        self.name_edit.clear()
        self.slot_spin.setValue(0)
        self.category_edit.clear()
        self.notes_edit.clear()
