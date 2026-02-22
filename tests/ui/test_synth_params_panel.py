import pytest
from PyQt6.QtWidgets import QApplication
from midi.params import ParamMap
from ui.synth_params_panel import SynthParamsPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_panel_creates_overview_param_widgets(app):
    pm = ParamMap()
    panel = SynthParamsPanel(param_map=pm)
    # Overview panel contains voice, arp, virtual patch, and vocoder on/off widgets
    expected = [
        "voice_mode", "arp_on_off", "arp_latch", "arp_type", "arp_gate", "arp_select",
        "vocoder_sw",
    ]
    for name in expected:
        assert name in panel._widgets, f"Missing widget for {name}"
    # Virtual patch source/dest 1-5
    for i in range(1, 6):
        assert f"patch{i}_source" in panel._widgets
        assert f"patch{i}_dest" in panel._widgets


def test_on_param_changed_updates_combo(app):
    pm = ParamMap()
    panel = SynthParamsPanel(param_map=pm)
    # Set arp to "On" (value 127 maps to index 1)
    panel.on_param_changed("arp_on_off", 127)
    widget = panel._widgets["arp_on_off"]
    assert widget.currentText() == "On"


def test_on_param_changed_updates_slider(app):
    pm = ParamMap()
    panel = SynthParamsPanel(param_map=pm)
    panel.on_param_changed("arp_gate", 64)
    widget = panel._widgets["arp_gate"]
    assert widget._slider.value() == 64


def test_user_change_triggers_callback(app):
    pm = ParamMap()
    changes = []
    panel = SynthParamsPanel(
        param_map=pm,
        on_user_change=lambda name, val: changes.append((name, val)),
    )
    # Simulate user changing arp type combo to "Down" (index 1)
    panel._widgets["arp_type"].setCurrentIndex(1)
    assert len(changes) == 1
    assert changes[0][0] == "arp_type"


def test_on_param_changed_does_not_trigger_callback(app):
    pm = ParamMap()
    changes = []
    panel = SynthParamsPanel(
        param_map=pm,
        on_user_change=lambda name, val: changes.append((name, val)),
    )
    # External update should NOT trigger callback (blockSignals)
    panel.on_param_changed("arp_on_off", 127)
    assert len(changes) == 0


def test_voice_mode_widget_exists(app):
    pm = ParamMap()
    panel = SynthParamsPanel(param_map=pm)
    assert "voice_mode" in panel._widgets
    widget = panel._widgets["voice_mode"]
    assert widget.count() == 4  # Single, Layer, Split, Multi


def test_virtual_patch_widgets_exist(app):
    pm = ParamMap()
    panel = SynthParamsPanel(param_map=pm)
    for i in range(1, 6):
        assert f"patch{i}_source" in panel._widgets
        assert f"patch{i}_dest" in panel._widgets
