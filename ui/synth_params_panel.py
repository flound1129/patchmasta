from __future__ import annotations
from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QScrollArea, QGridLayout,
)
from midi.params import ParamMap, ParamDef
from ui.widgets import ParamCombo as _ParamCombo, ParamSlider as _ParamSlider

# Value-label mappings from the RK-100S 2 Parameter Guide (p60-62)
_ARP_TYPE_LABELS = ["Up", "Down", "Alt1", "Alt2", "Random", "Trigger"]
_ARP_TYPE_RANGES = [(0, 21), (22, 42), (43, 63), (64, 85), (86, 106), (107, 127)]

_ARP_SELECT_LABELS = ["Timbre 1", "Timbre 2", "Timbre 1+2"]
_ARP_SELECT_RANGES = [(0, 42), (43, 85), (86, 127)]

_VOICE_MODE_LABELS = ["Single", "Layer", "Split", "Multi"]
_VOICE_MODE_RANGES = [(0, 31), (32, 63), (64, 95), (96, 127)]

_ON_OFF_LABELS = ["Off", "On"]
_ON_OFF_RANGES = [(0, 63), (64, 127)]

_VPATCH_SOURCE_LABELS = [
    "Filter EG", "AMP EG", "Assignable EG", "LFO1", "LFO2",
    "Velocity", "Short Ribbon (Pitch)", "Short Ribbon (Mod)",
    "Keyboard Track", "MIDI Ctrl 1", "MIDI Ctrl 2", "MIDI Ctrl 3",
    "Long Ribbon (Filter)",
]
_VPATCH_SOURCE_RANGES = [
    (0, 9), (10, 19), (20, 29), (30, 40), (41, 48), (49, 58),
    (59, 68), (69, 78), (79, 88), (89, 97), (98, 107), (108, 117),
    (118, 127),
]

_VPATCH_DEST_LABELS = [
    "Pitch", "OSC2 Tune", "OSC1 Ctrl 1", "OSC1 Level", "OSC2 Level",
    "Noise Level", "Filter1 Type Balance", "Filter1 Cutoff",
    "Filter1 Resonance", "Filter2 Cutoff", "Drive/WS Depth",
    "AMP Level", "Panpot", "LFO1 Freq", "LFO2 Freq", "Portamento",
    "OSC1 Ctrl 2", "Filter1 EG Int", "Filter1 Key Track",
    "Filter1 Resonance (2)", "Filter2 EG Int", "Filter2 Key Track",
    "Filter EG Attack", "Filter EG Decay", "Filter EG Sustain",
    "Filter EG Release", "AMP EG Attack", "AMP EG Decay",
    "AMP EG Sustain", "AMP EG Release", "Assign EG Attack",
    "Assign EG Decay", "Assign EG Sustain", "Assign EG Release",
    "Patch1 Int", "Patch2 Int", "Patch3 Int", "Patch4 Int",
    "Patch5 Int", "Long Ribbon (Filter) Int",
]
_VPATCH_DEST_RANGES = [
    (0, 2), (3, 5), (6, 9), (10, 12), (13, 15), (16, 18),
    (19, 21), (22, 25), (26, 28), (29, 31), (32, 34),
    (35, 37), (38, 41), (42, 44), (45, 47), (48, 50),
    (51, 53), (54, 57), (58, 60), (61, 63), (64, 66),
    (67, 69), (70, 73), (74, 76), (77, 79), (80, 82),
    (83, 85), (86, 89), (90, 92), (93, 95), (96, 98),
    (99, 101), (102, 105), (106, 108), (109, 111), (112, 114),
    (115, 117), (118, 121), (122, 124), (125, 127),
]


class SynthParamsPanel(QWidget):
    """Grouped parameter controls for the RK-100S 2 synth."""

    def __init__(
        self,
        param_map: ParamMap,
        on_user_change: Callable[[str, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._param_map = param_map
        self._on_user_change = on_user_change or (lambda n, v: None)
        self._widgets: dict[str, _ParamCombo | _ParamSlider] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        layout.addWidget(self._build_voice_group())
        layout.addWidget(self._build_arpeggiator_group())
        layout.addWidget(self._build_virtual_patch_group())
        layout.addWidget(self._build_vocoder_group())
        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_voice_group(self) -> QGroupBox:
        group = QGroupBox("Voice")
        layout = QHBoxLayout(group)
        layout.addWidget(QLabel("Mode:"))
        combo = _ParamCombo(
            "voice_mode", _VOICE_MODE_LABELS, _VOICE_MODE_RANGES,
            self._on_user_change,
        )
        self._widgets["voice_mode"] = combo
        layout.addWidget(combo, stretch=1)
        return group

    def _build_arpeggiator_group(self) -> QGroupBox:
        group = QGroupBox("Arpeggiator")
        layout = QGridLayout(group)

        row = 0
        # ON/OFF
        layout.addWidget(QLabel("ON/OFF:"), row, 0)
        w = _ParamCombo("arp_on_off", _ON_OFF_LABELS, _ON_OFF_RANGES, self._on_user_change)
        self._widgets["arp_on_off"] = w
        layout.addWidget(w, row, 1)

        # Type
        layout.addWidget(QLabel("Type:"), row, 2)
        w = _ParamCombo("arp_type", _ARP_TYPE_LABELS, _ARP_TYPE_RANGES, self._on_user_change)
        self._widgets["arp_type"] = w
        layout.addWidget(w, row, 3)

        row = 1
        # Latch
        layout.addWidget(QLabel("Latch:"), row, 0)
        w = _ParamCombo("arp_latch", _ON_OFF_LABELS, _ON_OFF_RANGES, self._on_user_change)
        self._widgets["arp_latch"] = w
        layout.addWidget(w, row, 1)

        # Select
        layout.addWidget(QLabel("Select:"), row, 2)
        w = _ParamCombo("arp_select", _ARP_SELECT_LABELS, _ARP_SELECT_RANGES, self._on_user_change)
        self._widgets["arp_select"] = w
        layout.addWidget(w, row, 3)

        row = 2
        # Gate
        layout.addWidget(QLabel("Gate:"), row, 0)
        w = _ParamSlider("arp_gate", 0, 127, self._on_user_change)
        self._widgets["arp_gate"] = w
        layout.addWidget(w, row, 1, 1, 3)

        return group

    def _build_virtual_patch_group(self) -> QGroupBox:
        group = QGroupBox("Virtual Patch")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("Source"), 0, 1)
        layout.addWidget(QLabel("Destination"), 0, 2)

        for i in range(1, 6):
            row = i
            layout.addWidget(QLabel(f"{i}:"), row, 0)

            src_name = f"patch{i}_source"
            src = _ParamCombo(
                src_name, _VPATCH_SOURCE_LABELS, _VPATCH_SOURCE_RANGES,
                self._on_user_change,
            )
            self._widgets[src_name] = src
            layout.addWidget(src, row, 1)

            dst_name = f"patch{i}_dest"
            dst = _ParamCombo(
                dst_name, _VPATCH_DEST_LABELS, _VPATCH_DEST_RANGES,
                self._on_user_change,
            )
            self._widgets[dst_name] = dst
            layout.addWidget(dst, row, 2)

        return group

    def _build_vocoder_group(self) -> QGroupBox:
        group = QGroupBox("Vocoder")
        layout = QHBoxLayout(group)
        layout.addWidget(QLabel("ON/OFF:"))
        w = _ParamCombo("vocoder_sw", _ON_OFF_LABELS, _ON_OFF_RANGES, self._on_user_change)
        self._widgets["vocoder_sw"] = w
        layout.addWidget(w, stretch=1)
        return group

    def on_param_changed(self, name: str, value: int) -> None:
        """Update a widget from an external source (e.g. AI controller)."""
        widget = self._widgets.get(name)
        if widget is not None:
            widget.set_value(value)
