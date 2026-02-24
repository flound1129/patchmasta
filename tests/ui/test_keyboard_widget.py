import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from ui.keyboard_widget import VirtualKeyboardWidget, KeyboardPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def keyboard(app):
    kb = VirtualKeyboardWidget()
    kb.resize(600, 100)
    return kb


@pytest.fixture
def panel(app):
    p = KeyboardPanel()
    p.resize(660, 100)
    return p


def test_keyboard_widget_initial_state(keyboard):
    assert keyboard._active_notes == {}
    assert keyboard.base_note == 48


def test_note_on_off_updates_active(keyboard):
    keyboard.note_on(60, 100)
    assert keyboard._active_notes[60] == 100
    keyboard.note_off(60)
    assert 60 not in keyboard._active_notes


def test_mouse_press_emits_signal(keyboard):
    handler = MagicMock()
    keyboard.note_pressed.connect(handler)
    # Simulate click in the middle of the widget (should hit a key)
    pos = QPointF(keyboard.width() / 2, keyboard.height() * 0.8)
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos, Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    keyboard.mousePressEvent(event)
    assert handler.called
    note, velocity = handler.call_args[0]
    assert 48 <= note <= 83  # within 3-octave range
    assert velocity == 100


def test_mouse_release_emits_signal(keyboard):
    release_handler = MagicMock()
    keyboard.note_released.connect(release_handler)
    # Press first
    pos = QPointF(keyboard.width() / 2, keyboard.height() * 0.8)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos, Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    keyboard.mousePressEvent(press_event)
    # Release
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        pos, Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    keyboard.mouseReleaseEvent(release_event)
    assert release_handler.called


def test_keyboard_default_range(keyboard):
    assert keyboard.base_note == 48
    assert keyboard.NUM_KEYS == 36  # 3 octaves


def test_octave_shift_up(panel):
    initial = panel.keyboard.base_note
    panel._shift_up()
    assert panel.keyboard.base_note == initial + 12


def test_octave_shift_down(panel):
    initial = panel.keyboard.base_note
    panel._shift_down()
    assert panel.keyboard.base_note == initial - 12


def test_octave_shift_clamp(keyboard):
    keyboard.base_note = 0
    keyboard.base_note -= 12  # would go to -12
    assert keyboard.base_note == 0

    keyboard.base_note = 96
    keyboard.base_note += 12  # would go to 108
    assert keyboard.base_note == 96


def test_active_notes_persist_across_shift(keyboard):
    # Activate a note outside visible range then shift to reveal
    keyboard.note_on(36, 80)  # below default base_note=48
    assert 36 in keyboard._active_notes
    keyboard.base_note = 24  # shift down to reveal it
    assert 36 in keyboard._active_notes
    assert keyboard._active_notes[36] == 80


def test_clear_all_notes(keyboard):
    keyboard.note_on(60, 100)
    keyboard.note_on(64, 80)
    keyboard.clear_all_notes()
    assert keyboard._active_notes == {}


def test_panel_delegates_note_on_off(panel):
    panel.note_on(60, 100)
    assert 60 in panel.keyboard._active_notes
    panel.note_off(60)
    assert 60 not in panel.keyboard._active_notes
