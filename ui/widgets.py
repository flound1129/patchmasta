"""Shared synth-editor widgets extracted from synth_params_panel.

Used by the Overview tab, TimbreSynthTab, and other editor tabs.
"""
from __future__ import annotations
from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QSlider,
)
from PyQt6.QtCore import Qt as QtCore_Qt


def value_to_combo_index(value: int, ranges: list[tuple[int, int]]) -> int:
    for i, (lo, hi) in enumerate(ranges):
        if lo <= value <= hi:
            return i
    return 0


def combo_index_to_value(index: int, ranges: list[tuple[int, int]]) -> int:
    if 0 <= index < len(ranges):
        return ranges[index][0]
    return 0


class ParamCombo(QComboBox):
    """A combo box bound to a named parameter."""

    def __init__(
        self,
        param_name: str,
        labels: list[str],
        ranges: list[tuple[int, int]],
        on_change: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.param_name = param_name
        self._ranges = ranges
        self._on_change = on_change
        self.addItems(labels)
        self.currentIndexChanged.connect(self._emit_change)

    def _emit_change(self, idx: int) -> None:
        value = combo_index_to_value(idx, self._ranges)
        self._on_change(self.param_name, value)

    def set_value(self, value: int) -> None:
        self.blockSignals(True)
        self.setCurrentIndex(value_to_combo_index(value, self._ranges))
        self.blockSignals(False)


class ParamSlider(QWidget):
    """A slider with value label bound to a named parameter."""

    def __init__(
        self,
        param_name: str,
        min_val: int,
        max_val: int,
        on_change: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.param_name = param_name
        self._on_change = on_change
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._slider = QSlider(QtCore_Qt.Orientation.Horizontal)
        self._slider.setRange(min_val, max_val)
        self._slider.setValue(0)
        self._label = QLabel("0")
        self._label.setMinimumWidth(30)
        self._slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self._slider, stretch=1)
        layout.addWidget(self._label)

    def _on_slider(self, value: int) -> None:
        self._label.setText(str(value))
        self._on_change(self.param_name, value)

    def set_value(self, value: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._label.setText(str(value))
        self._slider.blockSignals(False)
