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


def test_effects_tab_dynamic_rebuild(app):
    """Change fx1_type to Compressor -> verify correct dynamic widgets appear."""
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    # Initially no dynamic widgets
    assert "fx1_dry_wet" not in tab.widgets
    # Trigger type change to Compressor (type_id=1)
    tab.on_param_changed("fx1_type", 1)
    assert "fx1_dry_wet" in tab.widgets
    assert "fx1_sensitivity" in tab.widgets
    assert "fx1_attack" in tab.widgets
    assert "fx1_output_level" in tab.widgets
    assert "fx1_envelope_select" in tab.widgets


def test_effects_tab_type_off(app):
    """Set type=0 (Effect Off) -> verify no dynamic widgets."""
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    # First set to a type with params
    tab.on_param_changed("fx1_type", 1)
    assert "fx1_dry_wet" in tab.widgets
    # Now set to Off
    tab.on_param_changed("fx1_type", 0)
    assert "fx1_dry_wet" not in tab.widgets
    assert len(tab._dynamic_widgets[1]) == 0


def test_effects_tab_type_switch(app):
    """Switch between types -> old widgets removed, new ones added."""
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    # Set to Compressor
    tab.on_param_changed("fx1_type", 1)
    assert "fx1_sensitivity" in tab.widgets
    assert "fx1_cutoff" not in tab.widgets
    # Switch to Filter
    tab.on_param_changed("fx1_type", 2)
    assert "fx1_sensitivity" not in tab.widgets
    assert "fx1_cutoff" in tab.widgets
    assert "fx1_resonance" in tab.widgets
    assert "fx1_dry_wet" in tab.widgets


def test_effects_tab_dynamic_user_change(app):
    """Change a dynamic param -> verify callback fires."""
    pm = ParamMap()
    changes = []
    tab = EffectsTab(
        param_map=pm,
        on_user_change=lambda n, v: changes.append((n, v)),
    )
    tab.on_param_changed("fx1_type", 1)
    # Manipulate the dynamic dry_wet slider
    w = tab.widgets["fx1_dry_wet"]
    w._slider.setValue(100)
    assert any(n == "fx1_dry_wet" for n, v in changes)


def test_effects_tab_fx2_independent(app):
    """FX1 and FX2 dynamic areas are independent."""
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    # Set FX1 to Compressor, FX2 to Filter
    tab.on_param_changed("fx1_type", 1)
    tab.on_param_changed("fx2_type", 2)
    # FX1 has compressor params
    assert "fx1_sensitivity" in tab.widgets
    assert "fx1_cutoff" not in tab.widgets
    # FX2 has filter params
    assert "fx2_cutoff" in tab.widgets
    assert "fx2_sensitivity" not in tab.widgets
    # Changing FX1 doesn't affect FX2
    tab.on_param_changed("fx1_type", 0)
    assert "fx1_sensitivity" not in tab.widgets
    assert "fx2_cutoff" in tab.widgets


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
    assert "short_ribbon_setting" in tab.widgets


def test_vocoder_tab_on_param_changed(app):
    pm = ParamMap()
    tab = VocoderTab(param_map=pm)
    tab.on_param_changed("vocoder_level_1", 100)
    w = tab.widgets["vocoder_level_1"]
    assert w._slider.value() == 100


def test_effects_tab_ribbon_assign_always_present(app):
    """fx1_ribbon_assign should be in widgets even before any type is set."""
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    assert "fx1_ribbon_assign" in tab.widgets
    assert "fx2_ribbon_assign" in tab.widgets


def test_effects_tab_ribbon_assign_type_off(app):
    """With type=0 (Effect Off) ribbon assign has only 'Assign Off' option."""
    from PyQt6.QtWidgets import QComboBox
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    w = tab.widgets["fx1_ribbon_assign"]
    assert isinstance(w, QComboBox)
    assert w.count() == 1
    assert w.itemText(0) == "Assign Off"


def test_effects_tab_ribbon_assign_4band_eq(app):
    """With type=3 (4Band EQ) ribbon assign has 6 options: Assign Off + 5 params."""
    from PyQt6.QtWidgets import QComboBox
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    tab.on_param_changed("fx1_type", 3)
    w = tab.widgets["fx1_ribbon_assign"]
    assert isinstance(w, QComboBox)
    assert w.count() == 6
    assert w.itemText(0) == "Assign Off"
    assert w.itemText(1) == "Dry/Wet"
    assert w.itemText(2) == "B1 Gain"
    assert w.itemText(3) == "B2 Gain"
    assert w.itemText(4) == "B3 Gain"
    assert w.itemText(5) == "B4 Gain"


def test_effects_tab_ribbon_assign_updates_on_type_switch(app):
    """Switching FX type rebuilds the ribbon assign combo."""
    from PyQt6.QtWidgets import QComboBox
    pm = ParamMap()
    tab = EffectsTab(param_map=pm)
    tab.on_param_changed("fx1_type", 3)   # 4Band EQ: 6 options
    assert tab.widgets["fx1_ribbon_assign"].count() == 6
    tab.on_param_changed("fx1_type", 1)   # Compressor: 4 options (Assign Off + 3)
    w = tab.widgets["fx1_ribbon_assign"]
    assert w.count() == 4
    assert w.itemText(1) == "Dry/Wet"
    assert w.itemText(2) == "Sensitivity"
    assert w.itemText(3) == "Attack"
