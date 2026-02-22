from __future__ import annotations
import json
from pathlib import Path

_DEFAULTS = {
    "ai_backend": "claude",
    "claude_api_key": "",
    "groq_api_key": "",
    "audio_input_device": None,
    "theme": "auto",
    "sysex_write_debounce_ms": 150,
}

class AppConfig:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".patchmasta" / "config.json"
        self.ai_backend: str = _DEFAULTS["ai_backend"]
        self.claude_api_key: str = _DEFAULTS["claude_api_key"]
        self.groq_api_key: str = _DEFAULTS["groq_api_key"]
        self.audio_input_device: str | None = _DEFAULTS["audio_input_device"]
        self.theme: str = _DEFAULTS["theme"]
        self.sysex_write_debounce_ms: int = _DEFAULTS["sysex_write_debounce_ms"]
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            for key in _DEFAULTS:
                if key in data:
                    setattr(self, key, data[key])
        except (json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: getattr(self, key) for key in _DEFAULTS}
        self._path.write_text(json.dumps(data, indent=2))
