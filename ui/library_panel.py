from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem,
)
from PyQt6.QtCore import pyqtSignal, Qt
from model.patch import Patch
from model.bank import Bank


class LibraryPanel(QWidget):
    patch_selected = pyqtSignal(object)
    add_bank_requested = pyqtSignal()
    add_patch_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Library")
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        btn_row = QHBoxLayout()
        add_bank_btn = QPushButton("+ Bank")
        add_patch_btn = QPushButton("+ Patch from Device")
        add_bank_btn.clicked.connect(self.add_bank_requested)
        add_patch_btn.clicked.connect(self.add_patch_requested)
        btn_row.addWidget(add_bank_btn)
        btn_row.addWidget(add_patch_btn)
        layout.addLayout(btn_row)

    def populate(self, banks: list[Bank], patches: list[Patch]) -> None:
        self.tree.clear()
        for bank in banks:
            item = QTreeWidgetItem([bank.name])
            item.setData(0, Qt.ItemDataRole.UserRole, bank)
            self.tree.addTopLevelItem(item)
            item.setExpanded(True)

        if patches:
            loose = QTreeWidgetItem(["-- loose --"])
            loose.setFlags(loose.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(loose)
            for patch in patches:
                child = QTreeWidgetItem([patch.name])
                child.setData(0, Qt.ItemDataRole.UserRole, patch)
                loose.addChild(child)
            loose.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, Patch):
            self.patch_selected.emit(data)
