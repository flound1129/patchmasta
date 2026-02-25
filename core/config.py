from __future__ import annotations
import json
import os
from pathlib import Path


def downloads_dir() -> str:
    """Return the user's Downloads directory, falling back to home."""
    if os.name == "nt":
        # Windows: use the known-folder GUID via SHGetKnownFolderPath
        import ctypes
        from ctypes import wintypes
        FOLDERID_Downloads = ctypes.c_char_p(
            b"\xe3\x9c\x5e\x37\x4f\x01\xa5\x4b\xa1\x2e\x4b\x71\x3b\x85\x01\x31"
        )
        buf = ctypes.c_wchar_p()
        try:
            ctypes.windll.shell32.SHGetKnownFolderPath(
                FOLDERID_Downloads, 0, None, ctypes.byref(buf),
            )
            if buf.value:
                return buf.value
        except (OSError, AttributeError):
            pass
    # Linux / macOS / fallback
    xdg = os.environ.get("XDG_DOWNLOAD_DIR")
    if xdg and Path(xdg).is_dir():
        return xdg
    dl = Path.home() / "Downloads"
    if dl.is_dir():
        return str(dl)
    return str(Path.home())

_DEFAULTS = {
    "ai_backend": "claude",
    "claude_api_key": "",
    "groq_api_key": "",
    "audio_input_device": None,
    "midi_port": None,
    "theme": "auto",
    "sysex_write_debounce_ms": 150,
}

class AppConfig:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".config" / "patchmasta" / "config.json"
        self.ai_backend: str = _DEFAULTS["ai_backend"]
        self.claude_api_key: str = _DEFAULTS["claude_api_key"]
        self.groq_api_key: str = _DEFAULTS["groq_api_key"]
        self.audio_input_device: str | None = _DEFAULTS["audio_input_device"]
        self.midi_port: str | None = _DEFAULTS["midi_port"]
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
