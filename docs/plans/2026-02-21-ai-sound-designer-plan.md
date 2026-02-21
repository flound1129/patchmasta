# AI Sound Designer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a chat-based AI synth editor with WAV sound matching to patchmasta, plus a debug log panel and patch name extraction from SysEx dumps.

**Architecture:** A new Chat Panel in the UI sends user messages to an AI Controller that calls LLM APIs (Claude/Groq) with tool-use. The AI can set synth parameters via NRPN/CC, trigger notes, record audio, and compare spectral features. All debug output routes through a central logger to an in-app Log Panel.

**Tech Stack:** PyQt6, anthropic SDK, groq SDK, sounddevice, numpy, scipy

---

### Task 1: Central Logger

Replace all `print()` calls with a central logger that emits to both stdout and a Qt signal (for the Log Panel in Task 2).

**Files:**
- Create: `core/__init__.py`
- Create: `core/logger.py`
- Create: `tests/core/__init__.py`
- Create: `tests/core/test_logger.py`
- Modify: `midi/device.py`
- Modify: `ui/main_window.py`
- Modify: `pyproject.toml` (add `core` to packages)

**Step 1: Write the failing test**

```python
# tests/core/test_logger.py
from core.logger import AppLogger

def test_logger_emits_messages():
    logger = AppLogger()
    received = []
    logger.message_logged.connect(lambda cat, msg: received.append((cat, msg)))
    logger.log("MIDI", "Connected to port 1")
    assert len(received) == 1
    assert received[0] == ("MIDI", "Connected to port 1")

def test_logger_categories():
    logger = AppLogger()
    received = []
    logger.message_logged.connect(lambda cat, msg: received.append(cat))
    logger.midi("TX: F0 42 30")
    logger.audio("Recording started")
    logger.ai("Thinking...")
    logger.general("Ready")
    assert received == ["MIDI", "AUDIO", "AI", "GENERAL"]
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/core/test_logger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core'`

**Step 3: Write minimal implementation**

```python
# core/__init__.py
```

```python
# core/logger.py
from __future__ import annotations
from PyQt6.QtCore import QObject, pyqtSignal

class AppLogger(QObject):
    message_logged = pyqtSignal(str, str)  # category, message

    def log(self, category: str, message: str) -> None:
        print(f"[{category}] {message}", flush=True)
        self.message_logged.emit(category, message)

    def midi(self, message: str) -> None:
        self.log("MIDI", message)

    def audio(self, message: str) -> None:
        self.log("AUDIO", message)

    def ai(self, message: str) -> None:
        self.log("AI", message)

    def general(self, message: str) -> None:
        self.log("GENERAL", message)
```

Add `"core"` to packages in `pyproject.toml`:
```toml
packages = ["midi", "model", "ui", "core"]
```

Create empty `tests/core/__init__.py`.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/core/test_logger.py -v`
Expected: PASS

**Step 5: Replace all print() calls**

In `midi/device.py`, replace all `print(f"[MIDI]...")` and `print(f"[RX raw]...")` with `logger.midi(...)` calls. The logger instance is passed into `MidiDevice.__init__` as an optional parameter (defaults to a new `AppLogger()` if not provided).

In `ui/main_window.py`, replace all `print(f"[TX]...")` and `print(f"[RX]...")` with logger calls. The `MainWindow` creates one `AppLogger` instance and passes it to the device and worker.

**Step 6: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add core/ tests/core/ midi/device.py ui/main_window.py pyproject.toml
git commit -m "feat: central logger replacing print() calls"
```

---

### Task 2: Log Panel UI

Add a dockable log viewer panel with copy button.

**Files:**
- Create: `ui/log_panel.py`
- Create: `tests/ui/test_log_panel.py`
- Modify: `ui/main_window.py`

**Step 1: Write the failing test**

```python
# tests/ui/test_log_panel.py
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
    text = panel.log_text.toPlainText()
    assert "MIDI" in text
    assert "Connected" in text
    assert "Thinking..." in text

def test_log_panel_copy_button_exists(app):
    panel = LogPanel()
    assert panel.copy_btn is not None
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_log_panel.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# ui/log_panel.py
from __future__ import annotations
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG


class LogPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))
        self.log_text.setMaximumBlockCount(5000)
        layout.addWidget(self.log_text)

        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy Log")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.log_text.clear)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.copy_btn)
        layout.addLayout(btn_row)

    def append_message(self, category: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{category}] {message}"
        # Thread-safe: use invokeMethod if called from a non-GUI thread
        QMetaObject.invokeMethod(
            self.log_text, "appendPlainText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, line),
        )

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.log_text.toPlainText())
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_log_panel.py -v`
Expected: PASS

**Step 5: Wire into MainWindow**

In `ui/main_window.py`:
- Import `LogPanel`
- Create a `QSplitter(Qt.Orientation.Vertical)` wrapping the existing horizontal splitter and the log panel below it
- Connect `self._logger.message_logged` to `self._log_panel.append_message`

**Step 6: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add ui/log_panel.py tests/ui/test_log_panel.py ui/main_window.py
git commit -m "feat: in-app log panel with copy button"
```

---

### Task 3: Patch Name Extraction from SysEx

Extract ASCII patch name from SysEx program dump data. The name is at the start of the program data payload (after the function byte 0x40). The exact offset and length need empirical verification — start with 12 bytes at offset 0, which matches similar Korg instruments (microKORG XL+).

**Files:**
- Modify: `midi/sysex.py`
- Modify: `tests/midi/test_sysex.py`
- Modify: `ui/main_window.py` (use extracted name in PullWorker)

**Step 1: Write the failing test**

```python
# Add to tests/midi/test_sysex.py
from midi.sysex import extract_patch_name

def test_extract_patch_name_ascii():
    # 12 bytes of ASCII name, padded with spaces
    name_bytes = list(b"BrassLead   ")
    data = bytes(name_bytes + [0x00] * 20)
    assert extract_patch_name(data) == "BrassLead"

def test_extract_patch_name_strips_padding():
    data = bytes(list(b"Pad         ") + [0x00] * 20)
    assert extract_patch_name(data) == "Pad"

def test_extract_patch_name_empty_data():
    assert extract_patch_name(b"") is None

def test_extract_patch_name_short_data():
    assert extract_patch_name(b"\x00\x01") is None
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/midi/test_sysex.py::test_extract_patch_name_ascii -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Add to `midi/sysex.py`:

```python
PATCH_NAME_OFFSET = 0
PATCH_NAME_LENGTH = 12

def extract_patch_name(data: bytes) -> str | None:
    """Extract the ASCII patch name from program dump data."""
    if len(data) < PATCH_NAME_OFFSET + PATCH_NAME_LENGTH:
        return None
    raw = data[PATCH_NAME_OFFSET:PATCH_NAME_OFFSET + PATCH_NAME_LENGTH]
    # Filter to printable ASCII, strip trailing spaces/nulls
    name = bytes(b for b in raw if 0x20 <= b <= 0x7E).decode("ascii").strip()
    return name or None
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/midi/test_sysex.py -v`
Expected: All PASS

**Step 5: Use extracted name in PullWorker**

In `ui/main_window.py`, in the `PullWorker.run()` method, after `parse_program_dump` succeeds:

```python
from midi.sysex import extract_patch_name

# ... inside the if received: block:
name = extract_patch_name(received[0]) or f"Program {slot + 1:03d}"
self.patch_ready.emit(Patch(
    name=name,
    program_number=slot,
    sysex_data=received[0],
))
```

**Step 6: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add midi/sysex.py tests/midi/test_sysex.py ui/main_window.py
git commit -m "feat: extract patch names from SysEx program dumps"
```

**Note:** The `PATCH_NAME_OFFSET` and `PATCH_NAME_LENGTH` constants may need adjustment after testing with real device data. If the name appears garbled, inspect the first 32 bytes of the `.syx` file for ASCII characters and update the constants.

---

### Task 4: Config System

Persistent settings file for API keys, audio device, and AI backend selection.

**Files:**
- Create: `core/config.py`
- Create: `tests/core/test_config.py`

**Step 1: Write the failing test**

```python
# tests/core/test_config.py
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/core/test_config.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

```python
# core/config.py
from __future__ import annotations
import json
from pathlib import Path

_DEFAULTS = {
    "ai_backend": "claude",
    "claude_api_key": "",
    "groq_api_key": "",
    "audio_input_device": None,
}


class AppConfig:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".patchmasta" / "config.json"
        self.ai_backend: str = _DEFAULTS["ai_backend"]
        self.claude_api_key: str = _DEFAULTS["claude_api_key"]
        self.groq_api_key: str = _DEFAULTS["groq_api_key"]
        self.audio_input_device: str | None = _DEFAULTS["audio_input_device"]
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
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/core/test_config.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/config.py tests/core/test_config.py
git commit -m "feat: persistent config for API keys and settings"
```

---

### Task 5: Parameter Map

Data structure mapping human-readable synth parameter names to MIDI messages with ranges and sonic descriptions.

**Files:**
- Create: `midi/params.py`
- Create: `tests/midi/test_params.py`

**Step 1: Write the failing test**

```python
# tests/midi/test_params.py
from midi.params import ParamMap, ParamDef

def test_param_map_lookup():
    pm = ParamMap()
    p = pm.get("voice_mode")
    assert p is not None
    assert p.name == "voice_mode"
    assert p.min_val == 0
    assert p.max_val == 127

def test_param_map_list_all():
    pm = ParamMap()
    params = pm.list_all()
    assert len(params) > 0
    assert all(isinstance(p, ParamDef) for p in params)

def test_param_map_build_message():
    pm = ParamMap()
    p = pm.get("voice_mode")
    msg = p.build_message(channel=1, value=63)
    assert isinstance(msg, list)
    assert len(msg) > 0

def test_param_map_clamps_value():
    pm = ParamMap()
    p = pm.get("voice_mode")
    msg_low = p.build_message(channel=1, value=-10)
    msg_high = p.build_message(channel=1, value=999)
    # Should not raise, value gets clamped
    assert msg_low is not None
    assert msg_high is not None
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/midi/test_params.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

```python
# midi/params.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ParamDef:
    name: str
    description: str
    sonic_effect: str
    min_val: int
    max_val: int
    nrpn_msb: int | None = None
    nrpn_lsb: int | None = None
    cc_number: int | None = None

    def build_message(self, channel: int, value: int) -> list[int]:
        """Build MIDI message(s) to set this parameter."""
        value = max(self.min_val, min(self.max_val, value))
        ch = (channel - 1) & 0x0F
        if self.nrpn_msb is not None and self.nrpn_lsb is not None:
            return [
                0xB0 | ch, 99, self.nrpn_msb,   # NRPN MSB
                0xB0 | ch, 98, self.nrpn_lsb,   # NRPN LSB
                0xB0 | ch, 6, value & 0x7F,      # Data Entry MSB
            ]
        if self.cc_number is not None:
            return [0xB0 | ch, self.cc_number, value & 0x7F]
        raise ValueError(f"No MIDI address for parameter '{self.name}'")


# Documented NRPN parameters from the RK-100S 2 Parameter Guide pp. 59-62
_PARAMS: list[ParamDef] = [
    # Arpeggiator
    ParamDef("arp_on_off", "Arpeggiator on/off", "Enables/disables the arpeggiator",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x02),
    ParamDef("arp_latch", "Arpeggiator latch", "Holds the arpeggio after releasing keys",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x04),
    ParamDef("arp_type", "Arpeggiator type", "Pattern: Up, Down, Alt1, Alt2, Random, Trigger",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x07),
    ParamDef("arp_gate", "Arpeggiator gate time", "Duration of each arpeggio note",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x0A),
    ParamDef("arp_select", "Arpeggiator timbre select", "Which timbre the arp applies to",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x0B),

    # Voice
    ParamDef("voice_mode", "Voice mode", "Single/Layer/Split/Multi timbre mode",
             0, 127, nrpn_msb=0x05, nrpn_lsb=0x00),

    # Virtual Patch Sources (Timbre 1)
    ParamDef("patch1_source", "Virtual Patch 1 source", "Modulation source for patch 1",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x00),
    ParamDef("patch2_source", "Virtual Patch 2 source", "Modulation source for patch 2",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x01),
    ParamDef("patch3_source", "Virtual Patch 3 source", "Modulation source for patch 3",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x02),
    ParamDef("patch4_source", "Virtual Patch 4 source", "Modulation source for patch 4",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x03),
    ParamDef("patch5_source", "Virtual Patch 5 source", "Modulation source for patch 5",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x04),

    # Virtual Patch Destinations (Timbre 1)
    ParamDef("patch1_dest", "Virtual Patch 1 destination", "Parameter modulated by patch 1",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x08),
    ParamDef("patch2_dest", "Virtual Patch 2 destination", "Parameter modulated by patch 2",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x09),
    ParamDef("patch3_dest", "Virtual Patch 3 destination", "Parameter modulated by patch 3",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x0A),
    ParamDef("patch4_dest", "Virtual Patch 4 destination", "Parameter modulated by patch 4",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x0B),
    ParamDef("patch5_dest", "Virtual Patch 5 destination", "Parameter modulated by patch 5",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x0C),

    # Vocoder
    ParamDef("vocoder_sw", "Vocoder on/off", "Enables/disables the vocoder",
             0, 127, nrpn_msb=0x05, nrpn_lsb=0x04),
    ParamDef("fc_mod_source", "Fc Modulation source", "Cutoff modulation source for vocoder",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x00),
]

# TODO: Add core synth parameters (oscillator, filter, amp, EG, LFO)
# once SysEx parameter change messages are reverse-engineered from
# the Korg Sound Editor. See design doc for details.


class ParamMap:
    def __init__(self) -> None:
        self._params = {p.name: p for p in _PARAMS}

    def get(self, name: str) -> ParamDef | None:
        return self._params.get(name)

    def list_all(self) -> list[ParamDef]:
        return list(self._params.values())

    def names(self) -> list[str]:
        return list(self._params.keys())
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/midi/test_params.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add midi/params.py tests/midi/test_params.py
git commit -m "feat: parameter map with NRPN definitions from Parameter Guide"
```

---

### Task 6: NRPN/CC Sender

Extend `MidiDevice` to send NRPN and CC messages (multi-byte sequences).

**Files:**
- Modify: `midi/device.py`
- Modify: `tests/midi/test_device.py`

**Step 1: Write the failing test**

```python
# Add to tests/midi/test_device.py
def test_send_nrpn(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = True
    sent = []
    dev._midi_out = type("FakeOut", (), {"send_message": lambda self, m: sent.append(m)})()
    dev.send_nrpn(channel=1, msb=0x05, lsb=0x00, value=63)
    assert len(sent) == 3  # NRPN MSB, NRPN LSB, Data Entry
    assert sent[0] == [0xB0, 99, 0x05]
    assert sent[1] == [0xB0, 98, 0x00]
    assert sent[2] == [0xB0, 6, 63]

def test_send_cc(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = True
    sent = []
    dev._midi_out = type("FakeOut", (), {"send_message": lambda self, m: sent.append(m)})()
    dev.send_cc(channel=1, cc=7, value=100)
    assert sent == [[0xB0, 7, 100]]
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/midi/test_device.py::test_send_nrpn -v`
Expected: FAIL with `AttributeError`

**Step 3: Write minimal implementation**

Add to `midi/device.py`:

```python
def send_nrpn(self, channel: int, msb: int, lsb: int, value: int) -> None:
    """Send an NRPN parameter change (3 CC messages)."""
    if not self._connected:
        raise RuntimeError("Not connected to a MIDI device")
    ch = 0xB0 | ((channel - 1) & 0x0F)
    self._midi_out.send_message([ch, 99, msb & 0x7F])
    self._midi_out.send_message([ch, 98, lsb & 0x7F])
    self._midi_out.send_message([ch, 6, value & 0x7F])

def send_cc(self, channel: int, cc: int, value: int) -> None:
    """Send a single CC message."""
    if not self._connected:
        raise RuntimeError("Not connected to a MIDI device")
    ch = 0xB0 | ((channel - 1) & 0x0F)
    self._midi_out.send_message([ch, cc & 0x7F, value & 0x7F])

def send_note_on(self, channel: int, note: int, velocity: int) -> None:
    if not self._connected:
        raise RuntimeError("Not connected to a MIDI device")
    ch = 0x90 | ((channel - 1) & 0x0F)
    self._midi_out.send_message([ch, note & 0x7F, velocity & 0x7F])

def send_note_off(self, channel: int, note: int) -> None:
    if not self._connected:
        raise RuntimeError("Not connected to a MIDI device")
    ch = 0x80 | ((channel - 1) & 0x0F)
    self._midi_out.send_message([ch, note & 0x7F, 0])
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/midi/test_device.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add midi/device.py tests/midi/test_device.py
git commit -m "feat: NRPN, CC, and note-on/off methods on MidiDevice"
```

---

### Task 7: LLM Abstraction Layer

Pluggable LLM backends for Claude and Groq with tool-use support.

**Files:**
- Create: `ai/__init__.py`
- Create: `ai/llm.py`
- Create: `tests/ai/__init__.py`
- Create: `tests/ai/test_llm.py`
- Modify: `pyproject.toml` (add `ai` to packages, add `anthropic` and `groq` to dependencies)

**Step 1: Write the failing test**

```python
# tests/ai/test_llm.py
from ai.llm import LLMBackend, ClaudeBackend, GroqBackend, Message

def test_message_dataclass():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"

def test_claude_backend_is_llm_backend():
    assert issubclass(ClaudeBackend, LLMBackend)

def test_groq_backend_is_llm_backend():
    assert issubclass(GroqBackend, LLMBackend)

def test_backend_has_chat_method():
    assert callable(getattr(ClaudeBackend, "chat", None))
    assert callable(getattr(GroqBackend, "chat", None))
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/ai/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Add to `pyproject.toml` dependencies:
```toml
dependencies = [
    "PyQt6>=6.6.0",
    "python-rtmidi>=1.5.8",
    "anthropic>=0.40.0",
    "groq>=0.12.0",
]
```

Add `"ai"` to packages:
```toml
packages = ["midi", "model", "ui", "core", "ai"]
```

Install: `.venv/bin/pip install -e .`

```python
# ai/__init__.py
```

```python
# ai/llm.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


class LLMBackend(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        system: str,
        tools: list[dict],
    ) -> Message:
        """Send messages and return the assistant response.
        May include tool_calls that the caller should execute."""
        ...


class ClaudeBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, messages: list[Message], system: str, tools: list[dict]) -> Message:
        api_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        kwargs = {"model": self._model, "max_tokens": 4096, "system": system, "messages": api_messages}
        if tools:
            kwargs["tools"] = tools
        response = self._client.messages.create(**kwargs)
        # Extract text and tool use from response
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        return Message(role="assistant", content="\n".join(text_parts), tool_calls=tool_calls)


class GroqBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        import groq
        self._client = groq.Groq(api_key=api_key)
        self._model = model

    def chat(self, messages: list[Message], system: str, tools: list[dict]) -> Message:
        api_messages = [{"role": "system", "content": system}]
        api_messages += [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        # Convert tools to OpenAI format
        oai_tools = [{"type": "function", "function": t} for t in tools] if tools else None
        kwargs = {"model": self._model, "messages": api_messages, "max_tokens": 4096}
        if oai_tools:
            kwargs["tools"] = oai_tools
        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                import json
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                })
        return Message(
            role="assistant",
            content=choice.message.content or "",
            tool_calls=tool_calls,
        )
```

Create empty `tests/ai/__init__.py`.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/ai/test_llm.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add ai/ tests/ai/ pyproject.toml
git commit -m "feat: LLM abstraction layer with Claude and Groq backends"
```

---

### Task 8: AI Controller with Tool-Use

Orchestrates the LLM conversation, defines tools, and executes tool calls against the MIDI device and audio engine.

**Files:**
- Create: `ai/controller.py`
- Create: `ai/tools.py`
- Create: `tests/ai/test_controller.py`

**Step 1: Write the failing test**

```python
# tests/ai/test_controller.py
from ai.tools import TOOL_DEFINITIONS

def test_tool_definitions_are_valid():
    assert len(TOOL_DEFINITIONS) > 0
    for tool in TOOL_DEFINITIONS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool

def test_set_parameter_tool_exists():
    names = [t["name"] for t in TOOL_DEFINITIONS]
    assert "set_parameter" in names
    assert "list_parameters" in names
    assert "trigger_note" in names
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/ai/test_controller.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

```python
# ai/tools.py
from __future__ import annotations

TOOL_DEFINITIONS = [
    {
        "name": "set_parameter",
        "description": "Set a synth parameter on the connected Korg RK-100S 2. The parameter change is sent immediately via MIDI and heard in real-time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name (e.g., 'voice_mode', 'arp_on_off')"},
                "value": {"type": "integer", "description": "Value to set (within the parameter's valid range)"},
            },
            "required": ["name", "value"],
        },
    },
    {
        "name": "get_parameter",
        "description": "Get the current value of a synth parameter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_parameters",
        "description": "List all available synth parameters with their current values, valid ranges, and descriptions.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "trigger_note",
        "description": "Play a MIDI note on the synth so we can hear or record the current sound.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "integer", "description": "MIDI note number (60 = middle C)", "default": 60},
                "velocity": {"type": "integer", "description": "Note velocity (0-127)", "default": 100},
                "duration_ms": {"type": "integer", "description": "Duration in milliseconds", "default": 1000},
            },
        },
    },
    {
        "name": "record_audio",
        "description": "Record audio from the computer's audio input for the specified duration. Returns the file path of the recorded WAV.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_s": {"type": "number", "description": "Recording duration in seconds", "default": 2.0},
            },
        },
    },
    {
        "name": "analyze_audio",
        "description": "Analyze a WAV file and return spectral characteristics: fundamental frequency, harmonic series, spectral centroid, amplitude envelope shape.",
        "input_schema": {
            "type": "object",
            "properties": {
                "wav_path": {"type": "string", "description": "Path to the WAV file to analyze"},
            },
            "required": ["wav_path"],
        },
    },
    {
        "name": "compare_audio",
        "description": "Compare two audio files spectrally and return a similarity report showing which frequencies differ most.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "description": "Path to the target WAV file"},
                "recorded_path": {"type": "string", "description": "Path to the recorded WAV file"},
            },
            "required": ["target_path", "recorded_path"],
        },
    },
]
```

```python
# ai/controller.py
from __future__ import annotations
import threading
import time
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from ai.llm import LLMBackend, Message
from ai.tools import TOOL_DEFINITIONS
from midi.params import ParamMap
from core.logger import AppLogger

SYSTEM_PROMPT = """You are an AI sound designer for the Korg RK-100S 2 keytar synthesizer.
You can control synth parameters in real-time via MIDI. When the user describes a sound they want,
translate their description into parameter changes.

Available parameter categories:
- Arpeggiator: on/off, latch, type, gate, select
- Voice: mode (single/layer/split/multi)
- Virtual Patches: 5 modulation routings (source → destination with intensity)
- Vocoder: on/off, fc modulation source

When matching a sound from a WAV file:
1. First analyze the WAV to understand its spectral characteristics
2. Set initial parameters based on your analysis
3. Trigger a note, record the output, and compare
4. Iteratively adjust parameters to minimize the spectral difference

Think step-by-step about which parameters affect which sonic qualities."""


class AIController(QObject):
    response_ready = pyqtSignal(str)      # AI text response
    tool_executed = pyqtSignal(str, str)  # tool_name, result_summary
    error = pyqtSignal(str)

    def __init__(
        self,
        backend: LLMBackend,
        device,
        param_map: ParamMap,
        logger: AppLogger,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._device = device
        self._param_map = param_map
        self._logger = logger
        self._history: list[Message] = []
        self._param_state: dict[str, int] = {}
        self._stop_requested = False

    def send_message(self, user_text: str) -> None:
        """Send a user message. Runs LLM call in a background thread."""
        self._history.append(Message(role="user", content=user_text))
        thread = threading.Thread(target=self._run_chat, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop_requested = True

    def _run_chat(self) -> None:
        try:
            self._stop_requested = False
            # Loop to handle tool calls
            while not self._stop_requested:
                response = self._backend.chat(
                    messages=self._history,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                )
                if response.content:
                    self.response_ready.emit(response.content)
                if not response.tool_calls:
                    self._history.append(response)
                    break
                # Execute tool calls
                self._history.append(response)
                for tc in response.tool_calls:
                    result = self._execute_tool(tc["name"], tc["input"])
                    self.tool_executed.emit(tc["name"], str(result))
                    self._history.append(Message(
                        role="user",
                        content=f'Tool result for {tc["name"]}: {result}',
                    ))
        except Exception as exc:
            self.error.emit(str(exc))

    def _execute_tool(self, name: str, args: dict) -> str:
        self._logger.ai(f"Tool call: {name}({args})")
        if name == "set_parameter":
            return self._tool_set_parameter(args["name"], args["value"])
        if name == "get_parameter":
            return self._tool_get_parameter(args["name"])
        if name == "list_parameters":
            return self._tool_list_parameters()
        if name == "trigger_note":
            return self._tool_trigger_note(
                args.get("note", 60),
                args.get("velocity", 100),
                args.get("duration_ms", 1000),
            )
        if name == "record_audio":
            return self._tool_record_audio(args.get("duration_s", 2.0))
        if name == "analyze_audio":
            return self._tool_analyze_audio(args["wav_path"])
        if name == "compare_audio":
            return self._tool_compare_audio(args["target_path"], args["recorded_path"])
        return f"Unknown tool: {name}"

    def _tool_set_parameter(self, name: str, value: int) -> str:
        param = self._param_map.get(name)
        if param is None:
            return f"Unknown parameter: {name}"
        if not self._device.connected:
            return "Device not connected"
        msg = param.build_message(channel=1, value=value)
        # NRPN messages are 3 separate CC messages (9 bytes)
        # Send them as individual 3-byte messages
        for i in range(0, len(msg), 3):
            self._device.send(msg[i:i + 3])
        self._param_state[name] = value
        return f"Set {name} = {value}"

    def _tool_get_parameter(self, name: str) -> str:
        if name in self._param_state:
            return f"{name} = {self._param_state[name]}"
        return f"{name} = unknown (not yet set in this session)"

    def _tool_list_parameters(self) -> str:
        lines = []
        for p in self._param_map.list_all():
            current = self._param_state.get(p.name, "?")
            lines.append(f"{p.name}: {p.description} [{p.min_val}-{p.max_val}] current={current}")
        return "\n".join(lines)

    def _tool_trigger_note(self, note: int, velocity: int, duration_ms: int) -> str:
        if not self._device.connected:
            return "Device not connected"
        self._device.send_note_on(channel=1, note=note, velocity=velocity)
        time.sleep(duration_ms / 1000.0)
        self._device.send_note_off(channel=1, note=note)
        return f"Played note {note} vel={velocity} for {duration_ms}ms"

    def _tool_record_audio(self, duration_s: float) -> str:
        # Placeholder — implemented in Task 10
        return "Audio recording not yet implemented"

    def _tool_analyze_audio(self, wav_path: str) -> str:
        # Placeholder — implemented in Task 10
        return "Audio analysis not yet implemented"

    def _tool_compare_audio(self, target_path: str, recorded_path: str) -> str:
        # Placeholder — implemented in Task 10
        return "Audio comparison not yet implemented"
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/ai/test_controller.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add ai/tools.py ai/controller.py tests/ai/test_controller.py
git commit -m "feat: AI controller with tool-use for synth parameter editing"
```

---

### Task 9: Chat Panel UI

The conversation interface in the main window.

**Files:**
- Create: `ui/chat_panel.py`
- Create: `tests/ui/test_chat_panel.py`
- Modify: `ui/main_window.py`

**Step 1: Write the failing test**

```python
# tests/ui/test_chat_panel.py
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/ui/test_chat_panel.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

```python
# ui/chat_panel.py
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class ChatPanel(QWidget):
    message_sent = pyqtSignal(str)
    wav_dropped = pyqtSignal(str)  # file path
    match_requested = pyqtSignal(str)  # wav file path
    stop_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._wav_path: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header with backend selector
        header = QHBoxLayout()
        header.addWidget(QLabel("AI Backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Claude", "Groq"])
        header.addWidget(self.backend_combo)
        header.addStretch()
        layout.addLayout(header)

        # WAV drop zone
        wav_row = QHBoxLayout()
        self._wav_label = QLabel("No WAV loaded")
        wav_btn = QPushButton("Load WAV...")
        wav_btn.clicked.connect(self._pick_wav)
        self.match_btn = QPushButton("Match Sound")
        self.match_btn.setEnabled(False)
        self.match_btn.clicked.connect(self._on_match)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested)
        wav_row.addWidget(self._wav_label, stretch=1)
        wav_row.addWidget(wav_btn)
        wav_row.addWidget(self.match_btn)
        wav_row.addWidget(self.stop_btn)
        layout.addLayout(wav_row)

        # Conversation history
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setFont(QFont("Courier", 11))
        layout.addWidget(self.history, stretch=1)

        # Input row
        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Describe the sound you want...")
        self.input_edit.returnPressed.connect(self._on_send)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.input_edit, stretch=1)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

    def _on_send(self) -> None:
        text = self.input_edit.text().strip()
        if text:
            self.input_edit.clear()
            self.message_sent.emit(text)

    def _pick_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select WAV file", "", "WAV files (*.wav)"
        )
        if path:
            self._wav_path = path
            self._wav_label.setText(path.split("/")[-1])
            self.match_btn.setEnabled(True)
            self.wav_dropped.emit(path)

    def _on_match(self) -> None:
        if self._wav_path:
            self.match_requested.emit(self._wav_path)

    def append_user_message(self, text: str) -> None:
        self.history.append(f"<b>You:</b> {text}")

    def append_ai_message(self, text: str) -> None:
        self.history.append(f"<b>AI:</b> {text}")

    def append_tool_message(self, tool: str, result: str) -> None:
        self.history.append(f"<i>⚙ {tool}: {result}</i>")

    def set_thinking(self, thinking: bool) -> None:
        self.send_btn.setEnabled(not thinking)
        self.input_edit.setEnabled(not thinking)
        self.stop_btn.setEnabled(thinking)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/ui/test_chat_panel.py -v`
Expected: All PASS

**Step 5: Wire into MainWindow**

In `ui/main_window.py`:
- Import `ChatPanel`, `AIController`, `AppConfig`, `ParamMap`
- Import `ClaudeBackend`, `GroqBackend`
- Add the chat panel to the horizontal splitter (between detail and device panels)
- On `chat_panel.message_sent`, create/use AIController and send message
- Connect AIController signals to chat panel display methods
- Update splitter sizes to `[250, 350, 350, 300]`

**Step 6: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add ui/chat_panel.py tests/ui/test_chat_panel.py ui/main_window.py
git commit -m "feat: chat panel UI with AI controller wiring"
```

---

### Task 10: Audio Engine

Record from audio input and analyze spectral features.

**Files:**
- Create: `audio/__init__.py`
- Create: `audio/engine.py`
- Create: `tests/audio/__init__.py`
- Create: `tests/audio/test_engine.py`
- Modify: `pyproject.toml` (add `audio` to packages, add `sounddevice`, `numpy`, `scipy` to deps)

**Step 1: Write the failing test**

```python
# tests/audio/test_engine.py
import numpy as np
from pathlib import Path
from audio.engine import AudioAnalyzer, generate_test_tone

def test_generate_test_tone():
    samples = generate_test_tone(freq=440.0, duration=0.5, sample_rate=44100)
    assert isinstance(samples, np.ndarray)
    assert len(samples) == 22050

def test_analyze_finds_fundamental():
    samples = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    analysis = AudioAnalyzer.analyze_samples(samples, sample_rate=44100)
    assert "fundamental_hz" in analysis
    # Allow ±10 Hz tolerance
    assert abs(analysis["fundamental_hz"] - 440.0) < 10

def test_analyze_spectral_centroid():
    samples = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    analysis = AudioAnalyzer.analyze_samples(samples, sample_rate=44100)
    assert "spectral_centroid_hz" in analysis
    assert analysis["spectral_centroid_hz"] > 0

def test_compare_identical_is_low_distance():
    samples = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    report = AudioAnalyzer.compare_samples(samples, samples, sample_rate=44100)
    assert "spectral_distance" in report
    assert report["spectral_distance"] < 0.01

def test_compare_different_is_high_distance():
    s1 = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    s2 = generate_test_tone(freq=880.0, duration=1.0, sample_rate=44100)
    report = AudioAnalyzer.compare_samples(s1, s2, sample_rate=44100)
    assert report["spectral_distance"] > 0.1
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/audio/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Add to `pyproject.toml`:
```toml
dependencies = [
    "PyQt6>=6.6.0",
    "python-rtmidi>=1.5.8",
    "anthropic>=0.40.0",
    "groq>=0.12.0",
    "sounddevice>=0.5.0",
    "numpy>=1.24.0",
    "scipy>=1.10.0",
]
```

Add `"audio"` to packages:
```toml
packages = ["midi", "model", "ui", "core", "ai", "audio"]
```

Install: `.venv/bin/pip install -e .`

```python
# audio/__init__.py
```

```python
# audio/engine.py
from __future__ import annotations
from pathlib import Path
import numpy as np
from scipy import signal as scipy_signal
from scipy.io import wavfile


def generate_test_tone(freq: float, duration: float, sample_rate: int = 44100) -> np.ndarray:
    """Generate a sine wave for testing."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


class AudioRecorder:
    """Records audio from an input device."""

    def __init__(self, device: int | str | None = None, sample_rate: int = 44100) -> None:
        self._device = device
        self._sample_rate = sample_rate

    def record(self, duration_s: float) -> np.ndarray:
        import sounddevice as sd
        samples = sd.rec(
            int(duration_s * self._sample_rate),
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            device=self._device,
        )
        sd.wait()
        return samples.flatten()

    def save_wav(self, samples: np.ndarray, path: Path) -> None:
        scaled = np.int16(samples * 32767)
        wavfile.write(str(path), self._sample_rate, scaled)

    @staticmethod
    def load_wav(path: Path) -> tuple[np.ndarray, int]:
        sr, data = wavfile.read(str(path))
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32767.0
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data, sr


class AudioAnalyzer:
    """Spectral analysis of audio samples."""

    @staticmethod
    def analyze_samples(samples: np.ndarray, sample_rate: int) -> dict:
        """Return spectral analysis of audio samples."""
        # FFT
        n = len(samples)
        fft_vals = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

        # Fundamental frequency (strongest peak above 20 Hz)
        min_bin = int(20 * n / sample_rate)
        peak_bin = min_bin + np.argmax(fft_vals[min_bin:])
        fundamental_hz = freqs[peak_bin]

        # Spectral centroid
        magnitude_sum = np.sum(fft_vals)
        if magnitude_sum > 0:
            centroid = np.sum(freqs * fft_vals) / magnitude_sum
        else:
            centroid = 0.0

        # Amplitude envelope (split into 50ms windows)
        window_size = int(sample_rate * 0.05)
        envelope = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i:i + window_size]
            envelope.append(float(np.sqrt(np.mean(chunk ** 2))))

        # Harmonic content: ratio of energy in harmonics vs total
        harmonic_bins = []
        for h in range(2, 9):
            hfreq = fundamental_hz * h
            hbin = int(hfreq * n / sample_rate)
            if hbin < len(fft_vals):
                harmonic_bins.append(float(fft_vals[hbin]))
        harmonic_energy = sum(harmonic_bins) if harmonic_bins else 0
        total_energy = float(np.sum(fft_vals[min_bin:]))
        harmonic_ratio = harmonic_energy / total_energy if total_energy > 0 else 0

        return {
            "fundamental_hz": float(fundamental_hz),
            "spectral_centroid_hz": float(centroid),
            "harmonic_ratio": float(harmonic_ratio),
            "envelope": envelope[:20],  # first 1s at 50ms windows
            "duration_s": len(samples) / sample_rate,
        }

    @staticmethod
    def compare_samples(
        target: np.ndarray, recorded: np.ndarray, sample_rate: int
    ) -> dict:
        """Compare two audio signals spectrally."""
        a1 = AudioAnalyzer.analyze_samples(target, sample_rate)
        a2 = AudioAnalyzer.analyze_samples(recorded, sample_rate)

        # Spectral distance: normalized difference across features
        freq_diff = abs(a1["fundamental_hz"] - a2["fundamental_hz"]) / max(a1["fundamental_hz"], 1)
        centroid_diff = abs(a1["spectral_centroid_hz"] - a2["spectral_centroid_hz"]) / max(a1["spectral_centroid_hz"], 1)
        harmonic_diff = abs(a1["harmonic_ratio"] - a2["harmonic_ratio"])

        distance = (freq_diff + centroid_diff + harmonic_diff) / 3

        return {
            "spectral_distance": float(distance),
            "fundamental_diff_hz": float(a1["fundamental_hz"] - a2["fundamental_hz"]),
            "centroid_diff_hz": float(a1["spectral_centroid_hz"] - a2["spectral_centroid_hz"]),
            "harmonic_ratio_diff": float(a1["harmonic_ratio"] - a2["harmonic_ratio"]),
            "target_analysis": a1,
            "recorded_analysis": a2,
        }
```

Create empty `tests/audio/__init__.py`.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/audio/test_engine.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add audio/ tests/audio/ pyproject.toml
git commit -m "feat: audio recording and spectral analysis engine"
```

---

### Task 11: Wire Audio Tools into AI Controller

Connect the audio engine methods to the AI controller's tool execution.

**Files:**
- Modify: `ai/controller.py`
- Create: `tests/ai/test_audio_tools.py`

**Step 1: Write the failing test**

```python
# tests/ai/test_audio_tools.py
import numpy as np
from pathlib import Path
from audio.engine import generate_test_tone
from scipy.io import wavfile

def test_analyze_audio_tool(tmp_path):
    # Create a test WAV
    samples = generate_test_tone(440.0, 1.0, 44100)
    wav_path = tmp_path / "test.wav"
    wavfile.write(str(wav_path), 44100, np.int16(samples * 32767))

    from ai.controller import AIController
    # We just test the tool method directly
    ctrl = AIController.__new__(AIController)
    ctrl._logger = type("L", (), {"ai": lambda self, m: None})()
    result = ctrl._tool_analyze_audio(str(wav_path))
    assert "fundamental_hz" in result
    assert "440" in result or "439" in result or "441" in result
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/ai/test_audio_tools.py -v`
Expected: FAIL

**Step 3: Update AIController audio tool methods**

In `ai/controller.py`, replace the placeholder methods:

```python
def _tool_record_audio(self, duration_s: float) -> str:
    from audio.engine import AudioRecorder
    import tempfile
    recorder = AudioRecorder(device=self._audio_device)
    samples = recorder.record(duration_s)
    path = Path(tempfile.mktemp(suffix=".wav"))
    recorder.save_wav(samples, path)
    self._logger.audio(f"Recorded {duration_s}s to {path}")
    return f"Recorded to {path}"

def _tool_analyze_audio(self, wav_path: str) -> str:
    from audio.engine import AudioRecorder, AudioAnalyzer
    samples, sr = AudioRecorder.load_wav(Path(wav_path))
    analysis = AudioAnalyzer.analyze_samples(samples, sr)
    self._logger.audio(f"Analyzed {wav_path}: {analysis['fundamental_hz']:.1f} Hz")
    return str(analysis)

def _tool_compare_audio(self, target_path: str, recorded_path: str) -> str:
    from audio.engine import AudioRecorder, AudioAnalyzer
    t_samples, t_sr = AudioRecorder.load_wav(Path(target_path))
    r_samples, r_sr = AudioRecorder.load_wav(Path(recorded_path))
    report = AudioAnalyzer.compare_samples(t_samples, r_samples, t_sr)
    self._logger.audio(f"Spectral distance: {report['spectral_distance']:.4f}")
    return str(report)
```

Also add `self._audio_device = None` to `__init__`.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/ai/test_audio_tools.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add ai/controller.py tests/ai/test_audio_tools.py
git commit -m "feat: wire audio engine into AI controller tools"
```

---

### Task 12: Sound Matching Pipeline

The "Match Sound" button triggers: analyze WAV → AI initial guess → record → compare → iterate.

**Files:**
- Modify: `ai/controller.py` (add `match_sound` method)
- Modify: `ui/main_window.py` (connect match_requested signal)

**Step 1: Add match_sound to AIController**

```python
def match_sound(self, wav_path: str, max_iterations: int = 10) -> None:
    """Start sound matching in a background thread."""
    thread = threading.Thread(
        target=self._run_match, args=(wav_path, max_iterations), daemon=True
    )
    thread.start()

def _run_match(self, wav_path: str, max_iterations: int) -> None:
    try:
        self._stop_requested = False
        # Step 1: Analyze target
        self._logger.ai(f"Analyzing target: {wav_path}")
        prompt = (
            f"I want to match this sound. Here is the spectral analysis of the target WAV:\n\n"
            f"{self._tool_analyze_audio(wav_path)}\n\n"
            f"Based on this analysis, set the synth parameters to your best initial guess. "
            f"Then trigger a note so we can record and compare."
        )
        self._history.append(Message(role="user", content=prompt))

        # Run the chat loop (handles tool calls internally)
        for iteration in range(max_iterations):
            if self._stop_requested:
                self.response_ready.emit("Matching stopped by user.")
                break
            self._run_chat()
            self._logger.ai(f"Match iteration {iteration + 1}/{max_iterations}")
    except Exception as exc:
        self.error.emit(str(exc))
```

**Step 2: Wire in MainWindow**

In `ui/main_window.py`, connect:
```python
self._chat_panel.match_requested.connect(self._on_match_sound)
```

```python
def _on_match_sound(self, wav_path: str) -> None:
    if self._ai_controller:
        self._chat_panel.set_thinking(True)
        self._ai_controller.match_sound(wav_path)
```

**Step 3: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add ai/controller.py ui/main_window.py
git commit -m "feat: sound matching pipeline with iterative refinement"
```

---

### Task 13: Full Integration Test

Run the entire app, verify all panels appear, and the test suite passes.

**Step 1: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All PASS

**Step 2: Manual smoke test**

Run: `.venv/bin/patchmasta`

Verify:
- Window opens with 5 panels: Library, Detail, Chat, Device, Log
- Log panel shows timestamped messages
- Copy button copies log to clipboard
- Chat panel has backend dropdown (Claude/Groq), text input, send button
- "Load WAV" button opens file picker
- "Match Sound" button is disabled until a WAV is loaded
- All existing functionality still works (connect, pull, send)

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration fixes from smoke test"
```

**Step 4: Push**

```bash
git push
```
