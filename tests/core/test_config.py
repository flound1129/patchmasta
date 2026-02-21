from pathlib import Path
from core.config import AppConfig

def test_config_defaults(tmp_path):
    cfg = AppConfig(path=tmp_path / "config.json")
    assert cfg.ai_backend == "claude"
    assert cfg.claude_api_key == ""
    assert cfg.groq_api_key == ""
    assert cfg.audio_input_device is None

def test_config_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(path=path)
    cfg.ai_backend = "groq"
    cfg.groq_api_key = "gsk_test123"
    cfg.save()
    cfg2 = AppConfig(path=path)
    assert cfg2.ai_backend == "groq"
    assert cfg2.groq_api_key == "gsk_test123"

def test_config_does_not_crash_on_missing_file(tmp_path):
    cfg = AppConfig(path=tmp_path / "nonexistent" / "config.json")
    assert cfg.ai_backend == "claude"
