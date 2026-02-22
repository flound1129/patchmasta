from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
)
from PyQt6.QtCore import pyqtSignal, Qt
from model.patch import Patch
from model.bank import Bank

_COLUMNS = ["Slot", "Name", "Category", "Notes", "Created"]


class LibraryPanel(QWidget):
    patch_selected = pyqtSignal(object)
    patch_double_clicked = pyqtSignal(object)
    add_bank_requested = pyqtSignal()
    add_patch_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(_COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_bank_btn = QPushButton("+ Bank")
        self._add_patch_btn = QPushButton("+ Patch from Device")
        self._add_patch_btn.setEnabled(False)
        add_bank_btn.clicked.connect(self.add_bank_requested)
        self._add_patch_btn.clicked.connect(self.add_patch_requested)
        btn_row.addWidget(add_bank_btn)
        btn_row.addWidget(self._add_patch_btn)
        layout.addLayout(btn_row)

    def populate(self, banks: list[Bank], patches: list[Patch]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for patch in patches:
            row = self.table.rowCount()
            self.table.insertRow(row)

            slot_item = QTableWidgetItem()
            slot_item.setData(Qt.ItemDataRole.DisplayRole, patch.program_number)
            slot_item.setData(Qt.ItemDataRole.UserRole, patch)
            self.table.setItem(row, 0, slot_item)

            self.table.setItem(row, 1, QTableWidgetItem(patch.name))
            self.table.setItem(row, 2, QTableWidgetItem(patch.category))
            self.table.setItem(row, 3, QTableWidgetItem(patch.notes))
            self.table.setItem(row, 4, QTableWidgetItem(patch.created))
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def set_device_connected(self, connected: bool) -> None:
        self._add_patch_btn.setEnabled(connected)

    def _on_selection_changed(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        patch = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if isinstance(patch, Patch):
            self.patch_selected.emit(patch)

    def _on_double_click(self, row: int, _col: int) -> None:
        patch = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if isinstance(patch, Patch):
            self.patch_double_clicked.emit(patch)
