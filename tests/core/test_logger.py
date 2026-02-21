import sys
import pytest
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)


from core.logger import AppLogger


def test_logger_emits_messages(app):
    logger = AppLogger()
    received = []
    logger.message_logged.connect(lambda cat, msg: received.append((cat, msg)))
    logger.log("MIDI", "Connected to port 1")
    assert len(received) == 1
    assert received[0] == ("MIDI", "Connected to port 1")


def test_logger_categories(app):
    logger = AppLogger()
    received = []
    logger.message_logged.connect(lambda cat, msg: received.append(cat))
    logger.midi("TX: F0 42 30")
    logger.audio("Recording started")
    logger.ai("Thinking...")
    logger.general("Ready")
    assert received == ["MIDI", "AUDIO", "AI", "GENERAL"]
