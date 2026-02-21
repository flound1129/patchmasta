import sys
import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_device_panel_buttons_disabled_when_disconnected(app):
    with patch("midi.device.rtmidi"):
        from ui.device_panel import DevicePanel
        panel = DevicePanel()
        assert not panel.send_btn.isEnabled()
        assert not panel.pull_btn.isEnabled()
        assert not panel.load_all_btn.isEnabled()
        assert not panel.load_range_btn.isEnabled()
