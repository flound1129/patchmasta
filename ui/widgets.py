"""Shared synth-editor widgets extracted from synth_params_panel.

Used by the Overview tab, TimbreSynthTab, and other editor tabs.
"""
from __future__ import annotations
import math
from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QSlider,
    QRadioButton, QButtonGroup, QStyleOption, QStyle,
)
from PyQt6.QtCore import Qt as QtCore_Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPalette, QFont


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


class ParamRadioGroup(QWidget):
    """Horizontal radio-button group bound to a named parameter.

    Drop-in replacement for ParamCombo when the option count is small (≤5).
    """

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
        self._button_group = QButtonGroup(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for i, text in enumerate(labels):
            btn = QRadioButton(text)
            self._button_group.addButton(btn, i)
            layout.addWidget(btn)
        if labels:
            self._button_group.button(0).setChecked(True)
        self._button_group.idClicked.connect(self._on_clicked)

    def _on_clicked(self, idx: int) -> None:
        value = combo_index_to_value(idx, self._ranges)
        self._on_change(self.param_name, value)

    def set_value(self, value: int) -> None:
        idx = value_to_combo_index(value, self._ranges)
        btn = self._button_group.button(idx)
        if btn is not None:
            self._button_group.blockSignals(True)
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)
            self._button_group.blockSignals(False)


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


class ParamKnob(QWidget):
    """Custom-painted rotary knob replacing horizontal sliders.

    270-degree arc (7 o'clock to 5 o'clock) with value label below.
    Supports vertical mouse drag and mouse wheel.  Hold Shift for fine
    adjustment (1-unit steps instead of coarser increments).
    """

    _ARC_START = 225  # degrees – 7 o'clock (Qt: 0° = 3 o'clock, CCW positive)
    _ARC_SPAN = 270   # sweep from start to 5 o'clock

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
        self._min = min_val
        self._max = max_val
        self._value = min_val
        self._on_change = on_change
        self._drag_start_y: int | None = None
        self._drag_start_val: int | None = None
        self.setFixedSize(50, 62)
        self.setFocusPolicy(QtCore_Qt.FocusPolicy.WheelFocus)

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, value: int) -> None:
        value = max(self._min, min(self._max, value))
        if value != self._value:
            self._value = value
            self.update()

    def _set_value_interactive(self, value: int) -> None:
        value = max(self._min, min(self._max, value))
        if value != self._value:
            self._value = value
            self.update()
            self._on_change(self.param_name, self._value)

    def _fraction(self) -> float:
        span = self._max - self._min
        if span <= 0:
            return 0.0
        return (self._value - self._min) / span

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()

        knob_size = 40
        margin = (self.width() - knob_size) / 2
        knob_rect = QRectF(margin, 2, knob_size, knob_size)
        center = knob_rect.center()
        radius = knob_size / 2

        # Track arc (full 270°) – Mid color
        pen = QPen(pal.color(QPalette.ColorRole.Mid), 3)
        pen.setCapStyle(QtCore_Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            knob_rect.toRect(),
            self._ARC_START * 16,
            -self._ARC_SPAN * 16,
        )

        # Filled arc (value portion) – Highlight color
        frac = self._fraction()
        if frac > 0:
            pen = QPen(pal.color(QPalette.ColorRole.Highlight), 3)
            pen.setCapStyle(QtCore_Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(
                knob_rect.toRect(),
                self._ARC_START * 16,
                -int(self._ARC_SPAN * frac) * 16,
            )

        # Knob circle – Button fill with Mid border
        inner_r = radius - 5
        painter.setPen(QPen(pal.color(QPalette.ColorRole.Mid), 1.5))
        painter.setBrush(pal.color(QPalette.ColorRole.Button))
        painter.drawEllipse(center, inner_r, inner_r)

        # Indicator line – from center outward along the arc
        angle_deg = self._ARC_START - self._ARC_SPAN * frac
        angle_rad = math.radians(angle_deg)
        line_inner = 4
        line_outer = inner_r - 2
        p1 = QPointF(
            center.x() + line_inner * math.cos(angle_rad),
            center.y() - line_inner * math.sin(angle_rad),
        )
        p2 = QPointF(
            center.x() + line_outer * math.cos(angle_rad),
            center.y() - line_outer * math.sin(angle_rad),
        )
        pen = QPen(pal.color(QPalette.ColorRole.Highlight), 2)
        pen.setCapStyle(QtCore_Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

        # Value label below the knob
        label_rect = QRectF(0, knob_size + 4, self.width(), 14)
        painter.setPen(pal.color(QPalette.ColorRole.Text))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(
            label_rect,
            int(QtCore_Qt.AlignmentFlag.AlignHCenter | QtCore_Qt.AlignmentFlag.AlignTop),
            str(self._value),
        )
        painter.end()

    # --- interaction ---

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore_Qt.MouseButton.LeftButton:
            self._drag_start_y = int(event.position().y())
            self._drag_start_val = self._value
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_start_y is not None:
            dy = self._drag_start_y - int(event.position().y())
            span = self._max - self._min
            fine = event.modifiers() & QtCore_Qt.KeyboardModifier.ShiftModifier
            scale = 0.25 if fine else 1.0
            delta = int(dy * scale * max(1, span / 100))
            self._set_value_interactive(self._drag_start_val + delta)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_start_y = None
        self._drag_start_val = None
        event.accept()

    def wheelEvent(self, event) -> None:  # noqa: N802
        fine = event.modifiers() & QtCore_Qt.KeyboardModifier.ShiftModifier
        step = 1 if fine else max(1, (self._max - self._min) // 20)
        delta = step if event.angleDelta().y() > 0 else -step
        self._set_value_interactive(self._value + delta)
        event.accept()


class ParamToggle(QWidget):
    """Pill/rocker toggle switch for exactly 2-option parameters.

    Active half filled with Highlight, inactive with Button.
    Click left/right half to select.
    """

    def __init__(
        self,
        param_name: str,
        labels: list[str],
        ranges: list[tuple[int, int]],
        on_change: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        assert len(labels) == 2, "ParamToggle requires exactly 2 labels"
        self.param_name = param_name
        self._labels = labels
        self._ranges = ranges
        self._on_change = on_change
        self._selected = 0  # combo index (0 or 1)
        self.setFixedHeight(24)
        self.setMinimumWidth(100)

    @property
    def value(self) -> int:
        return combo_index_to_value(self._selected, self._ranges)

    def set_value(self, value: int) -> None:
        idx = value_to_combo_index(value, self._ranges)
        if idx != self._selected:
            self._selected = idx
            self.update()

    def _set_selected_interactive(self, idx: int) -> None:
        if idx != self._selected:
            self._selected = idx
            self.update()
            self._on_change(self.param_name, combo_index_to_value(idx, self._ranges))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()

        w = self.width()
        h = self.height()
        r = h / 2  # corner radius for pill shape

        # Draw pill outline
        pill = QRectF(0.5, 0.5, w - 1, h - 1)
        painter.setPen(QPen(pal.color(QPalette.ColorRole.Mid), 1))
        painter.setBrush(pal.color(QPalette.ColorRole.Button))
        painter.drawRoundedRect(pill, r, r)

        # Draw active half
        half_w = w / 2
        if self._selected == 0:
            active_rect = QRectF(1, 1, half_w - 1, h - 2)
        else:
            active_rect = QRectF(half_w, 1, half_w - 1, h - 2)

        painter.setPen(QtCore_Qt.PenStyle.NoPen)
        painter.setBrush(pal.color(QPalette.ColorRole.Highlight))
        painter.drawRoundedRect(active_rect, r - 1, r - 1)

        # Draw labels
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        for i, label in enumerate(self._labels):
            if i == 0:
                text_rect = QRectF(0, 0, half_w, h)
            else:
                text_rect = QRectF(half_w, 0, half_w, h)

            if i == self._selected:
                painter.setPen(pal.color(QPalette.ColorRole.HighlightedText))
            else:
                painter.setPen(pal.color(QPalette.ColorRole.Text))

            painter.drawText(
                text_rect,
                int(QtCore_Qt.AlignmentFlag.AlignCenter),
                label,
            )

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore_Qt.MouseButton.LeftButton:
            idx = 0 if event.position().x() < self.width() / 2 else 1
            self._set_selected_interactive(idx)
            event.accept()
