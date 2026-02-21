import pytest
from PyQt6.QtWidgets import QApplication
from core.config import AppConfig
from ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a


def test_settings_dialog_creates_with_defaults(app, tmp_path):
    cfg = AppConfig(path=tmp_path / "config.json")
    dlg = SettingsDialog(cfg)
    assert dlg.backend_combo.currentText() == "claude"
    assert dlg.claude_key_edit.text() == ""
    assert dlg.groq_key_edit.text() == ""


def test_settings_dialog_round_trips_values(app, tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(path=path)

    dlg = SettingsDialog(cfg)
    dlg.backend_combo.setCurrentText("groq")
    dlg.claude_key_edit.setText("sk-ant-test123")
    dlg.groq_key_edit.setText("gsk_test456")
    dlg._on_accept()

    cfg2 = AppConfig(path=path)
    assert cfg2.ai_backend == "groq"
    assert cfg2.claude_api_key == "sk-ant-test123"
    assert cfg2.groq_api_key == "gsk_test456"


def test_settings_dialog_loads_existing_config(app, tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(path=path)
    cfg.ai_backend = "groq"
    cfg.claude_api_key = "sk-existing"
    cfg.groq_api_key = "gsk_existing"
    cfg.save()

    cfg2 = AppConfig(path=path)
    dlg = SettingsDialog(cfg2)
    assert dlg.backend_combo.currentText() == "groq"
    assert dlg.claude_key_edit.text() == "sk-existing"
    assert dlg.groq_key_edit.text() == "gsk_existing"
