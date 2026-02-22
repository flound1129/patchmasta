import pytest
from PyQt6.QtWidgets import QApplication
from midi.params import ParamMap
from ui.synth_tabs import (
    TimbreSynthTab, ArpeggiatorTab, EffectsTab, VocoderTab, EQTab,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_timbre1_tab_creates_widgets(app):
    pm = ParamMap()
    tab = TimbreSynthTab(param_map=pm, timbre=1)
    # Should have widgets for Timbre 1 params
    assert "t1_osc1_wave" in tab.widgets
    assert "t1_filter1_cutoff" in tab.widgets
    assert "t1_amp_level" in tab.widgets
    assert "t1_filter_eg_attack" in tab.widgets
    assert "t1_lfo1_wave" in tab.widgets
    assert "t1_voice_assign" in tab.widgets
    assert "t1_transpose" in tab.widgets
    # Should NOT have Timbre 2 params
    assert "t2_osc1_wave" not in tab.widgets


def test_timbre2_tab_creates_widgets(app):
    pm = ParamMap()
    tab = TimbreSynthTab(param_map=pm, timbre=2)
    assert "t2_osc1_wave" in tab.widgets
    assert "t2_filter1_cutoff" in tab.widgets
    assert "t1_osc1_wave" not in tab.widgets


def test_timbre_tab_on_param_changed(app):
    pm = ParamMap()
    tab = TimbreSynthTab(param_map=pm, timbre=1)
    # Should not crash for unknown param
    tab.on_param_changed("nonexistent", 42)
    # Should update known param
    tab.on_param_changed("t1_filter1_cutoff", 100)
    widget = tab.widgets["t1_filter1_cutoff"]
    assert widget._slider.value() == 100


def test_timbre_tab_user_change_callback(app):
    pm = ParamMap()
    changes = []
    tab = TimbreSynthTab(
        param_map=pm, timbre=1,
        on_user_change=lambda n, v: changes.append((n, v)),
    )
    # Simulate user changing a slider
    widget = tab.widgets.get("t1_filter1_cutoff")
    if widget:
        widget._slider.setValue(64)
        assert len(changes) >= 1
        assert changes[-1][0] == "t1_filter1_cutoff"


def test_arpeggiator_tab_creates_widgets(app):
    pm = ParamMap()
    tab = ArpeggiatorTab(param_map=pm)
    assert "arp_on_off" in tab.widgets
    assert "arp_type" in tab.widgets
    assert "arp_octave_range" in tab.widgets
    # Step edit toggles
    assert "arp_step1_sw" in tab.widgets
    assert "arp_step8_sw" in tab.widgets


def test_arpeggiator_step_toggle(app):
    pm = ParamMap()
    changes = []
    tab = ArpeggiatorTab(
        param_map=pm,
        on_user_change=lambda n, v: changes.append((n, v)),
    )
    cb = tab.widgets["arp_step1_sw"]
    cb.setChecked(True)
    assert len(changes) >= 1
    assert changes[-1] == ("arp_step1_sw", 1)


def test_effects_tab_creates_widgets(app):
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    assert "fx1_type" in tab.widgets
    assert "fx2_type" in tab.widgets
    assert "fx1_ribbon_polarity" in tab.widgets


def test_vocoder_tab_creates_widgets(app):
    pm = ParamMap()
    tab = VocoderTab(param_map=pm)
    assert "vocoder_sw" in tab.widgets
    assert "vocoder_timbre1_level" in tab.widgets
    assert "vocoder_formant_shift" in tab.widgets
    # Band sliders
    assert "vocoder_level_1" in tab.widgets
    assert "vocoder_level_16" in tab.widgets
    assert "vocoder_pan_1" in tab.widgets
    assert "vocoder_pan_16" in tab.widgets


def test_eq_tab_creates_widgets(app):
    pm = ParamMap()
    tab = EQTab(param_map=pm)
    assert "t1_eq_low_freq" in tab.widgets
    assert "t1_eq_high_gain" in tab.widgets
    assert "t2_eq_low_freq" in tab.widgets
    assert "long_ribbon_scale_sw" in tab.widgets
    assert "short_ribbon_setting" in tab.widgets


def test_vocoder_tab_on_param_changed(app):
    pm = ParamMap()
    tab = VocoderTab(param_map=pm)
    tab.on_param_changed("vocoder_level_1", 100)
    w = tab.widgets["vocoder_level_1"]
    assert w._slider.value() == 100
