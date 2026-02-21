import pytest
from PyQt6.QtWidgets import QApplication
from ui.chat_panel import ChatPanel

@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a

def test_chat_panel_has_input_and_history(app):
    panel = ChatPanel()
    assert panel.input_edit is not None
    assert panel.history is not None

def test_chat_panel_append_user_message(app):
    panel = ChatPanel()
    panel.append_user_message("make it warmer")
    text = panel.history.toPlainText()
    assert "make it warmer" in text

def test_chat_panel_append_ai_message(app):
    panel = ChatPanel()
    panel.append_ai_message("I'll lower the filter cutoff.")
    text = panel.history.toPlainText()
    assert "lower the filter cutoff" in text

def test_chat_panel_send_signal(app):
    panel = ChatPanel()
    received = []
    panel.message_sent.connect(lambda t: received.append(t))
    panel.input_edit.setText("test message")
    panel.send_btn.click()
    assert received == ["test message"]
    assert panel.input_edit.text() == ""

def test_chat_panel_thinking_indicator_shows_and_hides(app):
    panel = ChatPanel()
    panel.set_thinking(True)
    text = panel.history.toPlainText()
    assert "Thinking" in text
    panel.set_thinking(False)
    text = panel.history.toPlainText()
    assert "Thinking" not in text

def test_chat_panel_thinking_preserves_prior_messages(app):
    panel = ChatPanel()
    panel.append_user_message("hello")
    panel.set_thinking(True)
    assert "Thinking" in panel.history.toPlainText()
    assert "hello" in panel.history.toPlainText()
    panel.set_thinking(False)
    assert "hello" in panel.history.toPlainText()
    assert "Thinking" not in panel.history.toPlainText()
