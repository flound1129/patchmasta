"""Tab widgets for the expanded synth editor.

Each tab provides grouped parameter controls for a section of the RK-100S 2.
"""
from __future__ import annotations
from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QScrollArea, QGridLayout, QCheckBox,
)
from PyQt6.QtCore import Qt as QtCore_Qt
from midi.params import ParamMap, ParamDef
from midi.effects import EFFECT_TYPES, EffectParam, get_effect_type, fx_param_packed
from ui.widgets import ParamCombo, ParamSlider


def _make_widget(
    param: ParamDef,
    on_change: Callable[[str, int], None],
) -> ParamCombo | ParamSlider:
    """Create the appropriate widget for a ParamDef based on its value_labels."""
    if param.value_labels:
        sorted_items = sorted(param.value_labels.items())
        labels = [v for _, v in sorted_items]
        ranges = []
        keys = [k for k, _ in sorted_items]
        for i, k in enumerate(keys):
            hi = keys[i + 1] - 1 if i + 1 < len(keys) else param.max_val
            ranges.append((k, hi))
        return ParamCombo(param.name, labels, ranges, on_change)
    return ParamSlider(param.name, param.min_val, param.max_val, on_change)


def _build_section_group(
    title: str,
    params: list[ParamDef],
    on_change: Callable[[str, int], None],
    widgets: dict[str, ParamCombo | ParamSlider],
    columns: int = 2,
) -> QGroupBox:
    """Build a QGroupBox with a grid of labeled param widgets."""
    group = QGroupBox(title)
    layout = QGridLayout(group)
    for i, p in enumerate(params):
        row, col = divmod(i, columns)
        label_text = p.display_name or p.name.split("_", 2)[-1].replace("_", " ").title()
        layout.addWidget(QLabel(f"{label_text}:"), row, col * 2)
        w = _make_widget(p, on_change)
        widgets[p.name] = w
        layout.addWidget(w, row, col * 2 + 1)
    return group


class TimbreSynthTab(QWidget):
    """Full synth editor for a single timbre: OSC, Filter, AMP, EG, LFO, Voice, Pitch."""

    def __init__(
        self,
        param_map: ParamMap,
        timbre: int,
        on_user_change: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._param_map = param_map
        self._timbre = timbre
        self._on_user_change = on_user_change or (lambda n, v: None)
        self._widgets: dict[str, ParamCombo | ParamSlider] = {}
        self._build_ui()

    def _get_params(self, section: str) -> list[ParamDef]:
        return [p for p in self._param_map.by_section(section) if p.timbre == self._timbre]

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        sections = [
            ("Oscillator 1", "osc1"),
            ("Oscillator 2", "osc2"),
            ("Mixer", "mixer"),
            ("Filter 1", "filter1"),
            ("Filter 2", "filter2"),
            ("Filter Routing", "filter_routing"),
            ("AMP", "amp"),
            ("Filter EG", "filter_eg"),
            ("AMP EG", "amp_eg"),
            ("Assignable EG", "assign_eg"),
            ("LFO 1", "lfo1"),
            ("LFO 2", "lfo2"),
            ("Voice", "voice_settings"),
            ("Pitch", "pitch"),
            ("Timbre EQ", "eq"),
        ]

        for title, section in sections:
            params = self._get_params(section)
            if params:
                group = _build_section_group(
                    title, params, self._on_user_change, self._widgets
                )
                layout.addWidget(group)

        layout.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @property
    def widgets(self) -> dict[str, ParamCombo | ParamSlider]:
        return self._widgets

    def on_param_changed(self, name: str, value: int) -> None:
        widget = self._widgets.get(name)
        if widget is not None:
            widget.set_value(value)


class ArpeggiatorTab(QWidget):
    """Full arpeggiator editor with step toggles."""

    def __init__(
        self,
        param_map: ParamMap,
        on_user_change: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._param_map = param_map
        self._on_user_change = on_user_change or (lambda n, v: None)
        self._widgets: dict[str, ParamCombo | ParamSlider | QCheckBox] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        # Main arp params
        arp_params = [p for p in self._param_map.by_section("arpeggiator")]
        if arp_params:
            group = _build_section_group(
                "Arpeggiator", arp_params, self._on_user_change, self._widgets
            )
            layout.addWidget(group)

        # Step edit toggles
        step_params = self._param_map.by_section("arpeggiator_steps")
        if step_params:
            step_group = QGroupBox("Step Edit")
            step_layout = QHBoxLayout(step_group)
            for p in step_params:
                cb = QCheckBox(p.display_name or f"Step")
                cb.setProperty("param_name", p.name)
                cb.toggled.connect(lambda checked, name=p.name: self._on_user_change(name, 1 if checked else 0))
                self._widgets[p.name] = cb
                step_layout.addWidget(cb)
            layout.addWidget(step_group)

        layout.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @property
    def widgets(self) -> dict:
        return self._widgets

    def on_param_changed(self, name: str, value: int) -> None:
        widget = self._widgets.get(name)
        if widget is None:
            return
        if isinstance(widget, QCheckBox):
            widget.blockSignals(True)
            widget.setChecked(value > 0)
            widget.blockSignals(False)
        else:
            widget.set_value(value)


def _make_effect_widget(
    param: EffectParam,
    widget_name: str,
    on_change: Callable[[str, int], None],
) -> ParamCombo | ParamSlider:
    """Create a widget for an EffectParam (not a ParamDef)."""
    if param.value_labels:
        sorted_items = sorted(param.value_labels.items())
        labels = [v for _, v in sorted_items]
        keys = [k for k, _ in sorted_items]
        ranges = []
        for i, k in enumerate(keys):
            hi = keys[i + 1] - 1 if i + 1 < len(keys) else param.max_val
            ranges.append((k, hi))
        return ParamCombo(widget_name, labels, ranges, on_change)
    return ParamSlider(widget_name, param.min_val, param.max_val, on_change)


class EffectsTab(QWidget):
    """Master Effect 1 + 2 editor with dynamic per-effect-type params."""

    def __init__(
        self,
        param_map: ParamMap,
        on_user_change: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._param_map = param_map
        self._on_user_change = on_user_change or (lambda n, v: None)
        self._widgets: dict[str, ParamCombo | ParamSlider] = {}
        # Dynamic effect-param widgets per FX slot (excludes ribbon_assign)
        self._dynamic_widgets: dict[int, dict[str, ParamCombo | ParamSlider]] = {
            1: {}, 2: {},
        }
        # Container widgets for dynamic areas (cleared on type change)
        self._dynamic_containers: dict[int, QWidget] = {}
        # widget_name → packed SysEx offset for active dynamic params
        self._fx_packed_map: dict[str, int] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        for slot, section, title in [
            (1, "fx1", "Master Effect 1"),
            (2, "fx2", "Master Effect 2"),
        ]:
            # Static group: FX Type + Ribbon Polarity only
            # (ribbon_assign is rebuilt dynamically in the container below)
            static_params = [
                p for p in self._param_map.by_section(section)
                if p.name != f"fx{slot}_ribbon_assign"
            ]
            if static_params:
                group = _build_section_group(
                    title, static_params, self._on_user_change, self._widgets
                )
                layout.addWidget(group)

            # Dynamic container: ribbon_assign combo + per-effect-type params
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            self._dynamic_containers[slot] = container
            layout.addWidget(container)
            # Initialise with type=0 so ribbon_assign widget exists from the start
            self._on_fx_type_changed(slot, 0)

        layout.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_fx_type_changed(self, slot: int, type_id: int) -> None:
        """Clear and rebuild the dynamic param area for *slot*."""
        container = self._dynamic_containers[slot]
        # Remove existing dynamic widgets
        old_layout = container.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()

        # Clear tracking dicts (effect params only)
        old_names = list(self._dynamic_widgets[slot].keys())
        for name in old_names:
            self._widgets.pop(name, None)
            self._fx_packed_map.pop(name, None)
        self._dynamic_widgets[slot].clear()
        # Remove ribbon_assign from _widgets (will be rebuilt below)
        self._widgets.pop(f"fx{slot}_ribbon_assign", None)

        typedef = get_effect_type(type_id)

        # ----------------------------------------------------------------
        # Ribbon Assign combo — always built, options depend on effect type
        # ----------------------------------------------------------------
        ribbon_name = f"fx{slot}_ribbon_assign"
        ribbon_params = typedef.ribbon_assigns() if typedef else []
        labels = ["Assign Off"] + [p.display_name for p in ribbon_params]
        ranges = [(i, i) for i in range(len(labels))]
        ribbon_widget = ParamCombo(ribbon_name, labels, ranges, self._on_user_change)
        ribbon_group = QGroupBox("Ribbon Assign")
        ribbon_layout = QGridLayout(ribbon_group)
        ribbon_layout.addWidget(QLabel("Assign:"), 0, 0)
        ribbon_layout.addWidget(ribbon_widget, 0, 1)
        container.layout().addWidget(ribbon_group)
        self._widgets[ribbon_name] = ribbon_widget

        # ----------------------------------------------------------------
        # Per-effect-type params (only when type != 0)
        # ----------------------------------------------------------------
        if typedef is None or len(typedef.params) == 0:
            return

        group = QGroupBox(f"{typedef.name} Parameters")
        grid = QGridLayout(group)
        columns = 2
        for i, ep in enumerate(typedef.params):
            row, col = divmod(i, columns)
            grid.addWidget(QLabel(f"{ep.display_name}:"), row, col * 2)
            widget_name = f"fx{slot}_{ep.key}"
            w = _make_effect_widget(ep, widget_name, self._on_user_change)
            grid.addWidget(w, row, col * 2 + 1)
            self._dynamic_widgets[slot][widget_name] = w
            self._widgets[widget_name] = w
            self._fx_packed_map[widget_name] = fx_param_packed(slot, ep.slot_index)

        container.layout().addWidget(group)

    @property
    def widgets(self) -> dict:
        return self._widgets

    def get_fx_sysex_offset(self, name: str) -> int | None:
        """Return packed SysEx offset for a dynamic FX param, or None if unknown."""
        return self._fx_packed_map.get(name)

    def fx_sysex_items(self) -> list[tuple[str, int]]:
        """Return (widget_name, packed_offset) for all currently-active dynamic FX params."""
        return list(self._fx_packed_map.items())

    def on_param_changed(self, name: str, value: int) -> None:
        # Check if this is a type change that should trigger dynamic rebuild
        if name == "fx1_type":
            widget = self._widgets.get(name)
            if widget is not None:
                widget.set_value(value)
            self._on_fx_type_changed(1, value)
            return
        if name == "fx2_type":
            widget = self._widgets.get(name)
            if widget is not None:
                widget.set_value(value)
            self._on_fx_type_changed(2, value)
            return

        widget = self._widgets.get(name)
        if widget is not None:
            widget.set_value(value)


class VocoderTab(QWidget):
    """Vocoder editor: carrier, modulator, filter, AMP, 16-band level/pan."""

    def __init__(
        self,
        param_map: ParamMap,
        on_user_change: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._param_map = param_map
        self._on_user_change = on_user_change or (lambda n, v: None)
        self._widgets: dict[str, ParamCombo | ParamSlider] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        # On/off and Fc Mod Source from the vocoder section
        vocoder_main = [p for p in self._param_map.by_section("vocoder")]
        if vocoder_main:
            group = _build_section_group(
                "Vocoder", vocoder_main, self._on_user_change, self._widgets
            )
            layout.addWidget(group)

        for section, title in [
            ("vocoder_carrier", "Carrier"),
            ("vocoder_modulator", "Modulator"),
            ("vocoder_filter", "Filter"),
            ("vocoder_amp", "AMP"),
        ]:
            params = self._param_map.by_section(section)
            if params:
                group = _build_section_group(
                    title, params, self._on_user_change, self._widgets
                )
                layout.addWidget(group)

        # Band level + pan (16 each)
        band_params = self._param_map.by_section("vocoder_band")
        if band_params:
            band_group = QGroupBox("Band Level / Pan")
            band_layout = QGridLayout(band_group)
            band_layout.addWidget(QLabel("Band"), 0, 0)
            band_layout.addWidget(QLabel("Level"), 0, 1)
            band_layout.addWidget(QLabel("Pan"), 0, 2)
            for i in range(16):
                band_layout.addWidget(QLabel(f"{i+1}"), i + 1, 0)
                level_name = f"vocoder_level_{i+1}"
                pan_name = f"vocoder_pan_{i+1}"
                level_p = self._param_map.get(level_name)
                pan_p = self._param_map.get(pan_name)
                if level_p:
                    w = ParamSlider(level_name, 0, 127, self._on_user_change)
                    self._widgets[level_name] = w
                    band_layout.addWidget(w, i + 1, 1)
                if pan_p:
                    w = ParamSlider(pan_name, 0, 127, self._on_user_change)
                    self._widgets[pan_name] = w
                    band_layout.addWidget(w, i + 1, 2)
            layout.addWidget(band_group)

        layout.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @property
    def widgets(self) -> dict:
        return self._widgets

    def on_param_changed(self, name: str, value: int) -> None:
        widget = self._widgets.get(name)
        if widget is not None:
            widget.set_value(value)


class EQTab(QWidget):
    """Per-timbre EQ + Ribbon parameters."""

    def __init__(
        self,
        param_map: ParamMap,
        on_user_change: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._param_map = param_map
        self._on_user_change = on_user_change or (lambda n, v: None)
        self._widgets: dict[str, ParamCombo | ParamSlider] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        # Timbre 1 EQ
        t1_eq = [p for p in self._param_map.by_section("eq") if p.timbre == 1]
        if t1_eq:
            group = _build_section_group(
                "Timbre 1 EQ", t1_eq, self._on_user_change, self._widgets
            )
            layout.addWidget(group)

        # Timbre 2 EQ
        t2_eq = [p for p in self._param_map.by_section("eq") if p.timbre == 2]
        if t2_eq:
            group = _build_section_group(
                "Timbre 2 EQ", t2_eq, self._on_user_change, self._widgets
            )
            layout.addWidget(group)

        # Long Ribbon
        lr_params = self._param_map.by_section("long_ribbon")
        if lr_params:
            group = _build_section_group(
                "Long Ribbon", lr_params, self._on_user_change, self._widgets
            )
            layout.addWidget(group)

        # Short Ribbon
        sr_params = self._param_map.by_section("short_ribbon")
        if sr_params:
            group = _build_section_group(
                "Short Ribbon", sr_params, self._on_user_change, self._widgets
            )
            layout.addWidget(group)

        layout.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @property
    def widgets(self) -> dict:
        return self._widgets

    def on_param_changed(self, name: str, value: int) -> None:
        widget = self._widgets.get(name)
        if widget is not None:
            widget.set_value(value)
