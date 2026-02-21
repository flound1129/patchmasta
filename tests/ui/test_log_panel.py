import pytest
from PyQt6.QtWidgets import QApplication
from ui.log_panel import LogPanel

@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a

def test_log_panel_appends_messages(app):
    panel = LogPanel()
    panel.append_message("MIDI", "Connected")
    panel.append_message("AI", "Thinking...")
    app.processEvents()  # flush queued invokeMethod calls
    text = panel.log_text.toPlainText()
    assert "MIDI" in text
    assert "Connected" in text
    assert "Thinking..." in text

def test_log_panel_copy_button_exists(app):
    panel = LogPanel()
    assert panel.copy_btn is not None
