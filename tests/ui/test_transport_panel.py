import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

from ui.keyboard_widget import TransportPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def transport(app):
    return TransportPanel()


def test_initial_state(transport):
    assert transport._btn_load.isEnabled()
    assert not transport._btn_play.isEnabled()
    assert not transport._btn_stop.isEnabled()
    assert not transport._btn_rewind.isEnabled()
    assert not transport._slider.isEnabled()
    assert not transport._tempo_slider.isEnabled()
    assert not transport._btn_loop.isEnabled()


def test_set_file_loaded_enables_controls(transport):
    transport.set_file_loaded("test.mid", 10.0)
    assert transport._btn_play.isEnabled()
    assert transport._btn_stop.isEnabled()
    assert transport._btn_rewind.isEnabled()
    assert transport._slider.isEnabled()
    assert transport._tempo_slider.isEnabled()
    assert transport._btn_loop.isEnabled()
    assert transport._slider.maximum() == 10000  # 10s * 1000


def test_update_position(transport):
    transport.set_file_loaded("test.mid", 120.0)
    transport.update_position(65.0, 120.0)
    assert transport._slider.value() == 65000
    assert "1:05" in transport._time_label.text()
    assert "2:00" in transport._time_label.text()


def test_set_playing_toggles_icon(transport):
    transport.set_playing(True)
    assert transport._btn_play.text() == "\u23F8"  # ⏸
    transport.set_playing(False)
    assert transport._btn_play.text() == "\u25B6"  # ▶


def test_reset(transport):
    transport.set_file_loaded("test.mid", 60.0)
    transport.update_position(30.0, 60.0)
    transport.set_playing(True)
    transport.reset()
    assert transport._btn_play.text() == "\u25B6"
    assert transport._slider.value() == 0


def test_signal_emissions(transport):
    transport.set_file_loaded("test.mid", 10.0)

    load_spy = MagicMock()
    transport.load_requested.connect(load_spy)
    transport._btn_load.click()
    assert load_spy.called

    play_spy = MagicMock()
    transport.play_pause_requested.connect(play_spy)
    transport._btn_play.click()
    assert play_spy.called

    stop_spy = MagicMock()
    transport.stop_requested.connect(stop_spy)
    transport._btn_stop.click()
    assert stop_spy.called

    rewind_spy = MagicMock()
    transport.rewind_requested.connect(rewind_spy)
    transport._btn_rewind.click()
    assert rewind_spy.called

    loop_spy = MagicMock()
    transport.loop_toggled.connect(loop_spy)
    transport._btn_loop.click()
    assert loop_spy.called
