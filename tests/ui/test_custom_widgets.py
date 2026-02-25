import pytest
from PyQt6.QtWidgets import QApplication
from ui.widgets import ParamKnob, ParamToggle


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# --- ParamKnob ---

def test_knob_initial_value(app):
    knob = ParamKnob("test", 0, 127, lambda n, v: None)
    assert knob.value == 0


def test_knob_set_value(app):
    knob = ParamKnob("test", 0, 127, lambda n, v: None)
    knob.set_value(64)
    assert knob.value == 64


def test_knob_set_value_clamps_high(app):
    knob = ParamKnob("test", 0, 127, lambda n, v: None)
    knob.set_value(200)
    assert knob.value == 127


def test_knob_set_value_clamps_low(app):
    knob = ParamKnob("test", 0, 127, lambda n, v: None)
    knob.set_value(-10)
    assert knob.value == 0


def test_knob_set_value_no_callback(app):
    changes = []
    knob = ParamKnob("test", 0, 127, lambda n, v: changes.append((n, v)))
    knob.set_value(64)
    assert len(changes) == 0


def test_knob_interactive_fires_callback(app):
    changes = []
    knob = ParamKnob("test_param", 0, 127, lambda n, v: changes.append((n, v)))
    knob._set_value_interactive(100)
    assert changes == [("test_param", 100)]


def test_knob_interactive_clamps(app):
    changes = []
    knob = ParamKnob("test", 0, 127, lambda n, v: changes.append((n, v)))
    knob._set_value_interactive(200)
    assert knob.value == 127
    assert changes == [("test", 127)]


def test_knob_no_callback_when_unchanged(app):
    changes = []
    knob = ParamKnob("test", 0, 127, lambda n, v: changes.append((n, v)))
    knob._set_value_interactive(0)  # already at 0
    assert len(changes) == 0


def test_knob_param_name(app):
    knob = ParamKnob("my_param", 0, 100, lambda n, v: None)
    assert knob.param_name == "my_param"


def test_knob_fixed_size(app):
    knob = ParamKnob("test", 0, 127, lambda n, v: None)
    assert knob.width() == 50
    assert knob.height() == 62


# --- ParamToggle ---

def test_toggle_initial_value(app):
    toggle = ParamToggle("test", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: None)
    assert toggle.value == 0


def test_toggle_set_value_on(app):
    toggle = ParamToggle("test", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: None)
    toggle.set_value(127)
    assert toggle.value == 64  # combo_index_to_value(1, ranges) = 64


def test_toggle_set_value_off(app):
    toggle = ParamToggle("test", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: None)
    toggle.set_value(127)
    toggle.set_value(0)
    assert toggle.value == 0


def test_toggle_set_value_no_callback(app):
    changes = []
    toggle = ParamToggle("test", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: changes.append((n, v)))
    toggle.set_value(127)
    assert len(changes) == 0


def test_toggle_interactive_fires_callback(app):
    changes = []
    toggle = ParamToggle("sw", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: changes.append((n, v)))
    toggle._set_selected_interactive(1)
    assert changes == [("sw", 64)]


def test_toggle_interactive_no_callback_when_unchanged(app):
    changes = []
    toggle = ParamToggle("sw", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: changes.append((n, v)))
    toggle._set_selected_interactive(0)  # already at 0
    assert len(changes) == 0


def test_toggle_param_name(app):
    toggle = ParamToggle("my_toggle", ["A", "B"], [(0, 63), (64, 127)], lambda n, v: None)
    assert toggle.param_name == "my_toggle"


def test_toggle_requires_two_labels(app):
    with pytest.raises(AssertionError):
        ParamToggle("test", ["A"], [(0, 127)], lambda n, v: None)
    with pytest.raises(AssertionError):
        ParamToggle("test", ["A", "B", "C"], [(0, 42), (43, 85), (86, 127)], lambda n, v: None)


def test_toggle_fixed_height(app):
    toggle = ParamToggle("test", ["Off", "On"], [(0, 63), (64, 127)], lambda n, v: None)
    assert toggle.height() == 24
    assert toggle.minimumWidth() == 100
