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

def test_monitor_btn_exists_and_starts_disabled(app):
    with patch("midi.device.rtmidi"):
        from ui.device_panel import DevicePanel
        panel = DevicePanel()
        assert hasattr(panel, "monitor_btn")
        assert not panel.monitor_btn.isEnabled()

def test_monitor_btn_enabled_on_connect(app):
    with patch("midi.device.rtmidi"):
        from ui.device_panel import DevicePanel
        panel = DevicePanel()
        panel._set_connected(True)
        assert panel.monitor_btn.isEnabled()

def test_monitor_btn_disabled_on_disconnect(app):
    with patch("midi.device.rtmidi"), \
         patch("ui.device_panel.AudioMonitor"):
        from ui.device_panel import DevicePanel
        panel = DevicePanel()
        panel._set_connected(True)
        panel.monitor_btn.setChecked(True)
        panel._set_connected(False)
        assert not panel.monitor_btn.isEnabled()
        assert not panel.monitor_btn.isChecked()
