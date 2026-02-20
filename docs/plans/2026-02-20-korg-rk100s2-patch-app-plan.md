# Korg RK-100S 2 Patch Manager — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a PyQt6 desktop app to pull, organize, and push patches to/from the Korg RK-100S 2 keytar over USB MIDI.

**Architecture:** Layered MVC — a `midi/` layer handles all device communication via python-rtmidi, a `model/` layer manages patch/bank data objects and disk persistence as JSON + raw SysEx files, and a `ui/` layer provides a 3-panel PyQt6 interface (library tree, patch detail, device panel).

**Tech Stack:** Python 3.10+, PyQt6, python-rtmidi, pytest

---

## Reference

Design doc: `docs/plans/2026-02-20-korg-rk100s2-patch-app-design.md`

Key MIDI facts:
- Korg manufacturer ID: `0x42`
- Device channel byte: `0x30` (channel 1; adjust per Global MIDI channel setting)
- RK-100S 2 model ID: **TBD — verify against Parameter Guide** (placeholder `0x57` used; confirm before device testing)
- Program Change: 0-127
- Bank Select: CC 0 (MSB) + CC 32 (LSB)
- SysEx program dump request: `F0 42 3g [model_id] 10 F7`
- SysEx program dump response: `F0 42 3g [model_id] 40 [data...] F7`

---

## Task 1: Project Bootstrap

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `scripts/setup.sh`
- Create: `scripts/run.sh`
- Create: `scripts/test.sh`
- Create: `scripts/git.sh`
- Create: `main.py`

**Step 1: Create the venv**

```
python3 -m venv .venv
```

**Step 2: Create `requirements.txt`**

```
PyQt6>=6.6.0
python-rtmidi>=1.5.8
```

**Step 3: Create `requirements-dev.txt`**

```
pytest>=8.0.0
pytest-qt>=4.4.0
```

**Step 4: Install dependencies**

```
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

**Step 5: Create `scripts/setup.sh`**

```bash
#!/usr/bin/env bash
set -e
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
echo "Setup complete."
```

**Step 6: Create `scripts/run.sh`**

```bash
#!/usr/bin/env bash
set -e
.venv/bin/python main.py
```

**Step 7: Create `scripts/test.sh`**

```bash
#!/usr/bin/env bash
set -e
.venv/bin/pytest tests/ -v "$@"
```

**Step 8: Create `scripts/git.sh`**

```bash
#!/usr/bin/env bash
set -e

update_directory_structure() {
    find . \
        -not -path './.git/*' \
        -not -path './.venv/*' \
        -not -path './__pycache__/*' \
        -not -path './*/__pycache__/*' \
        -not -name '*.pyc' \
        | sort > directory_structure.txt
    git add directory_structure.txt
}

case "$1" in
    commit)
        shift
        update_directory_structure
        git add -A
        git commit -m "$@"
        ;;
    *)
        echo "Usage: scripts/git.sh commit <message>"
        exit 1
        ;;
esac
```

**Step 9: Make scripts executable and create package dirs**

```
chmod +x scripts/setup.sh scripts/run.sh scripts/test.sh scripts/git.sh
mkdir -p midi model ui patches banks tests/midi tests/model tests/ui
touch midi/__init__.py model/__init__.py ui/__init__.py
touch tests/__init__.py tests/midi/__init__.py tests/model/__init__.py tests/ui/__init__.py
```

**Step 10: Create stub `main.py`**

```python
def main():
    pass

if __name__ == "__main__":
    main()
```

**Step 11: Generate initial directory structure and commit**

```
find . -not -path './.git/*' -not -path './.venv/*' -not -path './__pycache__/*' -not -name '*.pyc' | sort > directory_structure.txt
git add -A
git commit -m "chore: project bootstrap with venv, deps, scripts"
```

---

## Task 2: MIDI Device Discovery

**Files:**
- Create: `midi/device.py`
- Create: `tests/midi/test_device.py`

**Step 1: Write the failing test in `tests/midi/test_device.py`**

```python
from unittest.mock import patch, MagicMock
from midi.device import list_midi_ports, find_rk100s2_port

def test_list_midi_ports_returns_list():
    with patch("rtmidi.MidiOut") as mock_cls:
        mock_out = MagicMock()
        mock_out.get_ports.return_value = ["Port A", "KORG RK-100S 2", "Port C"]
        mock_cls.return_value = mock_out
        ports = list_midi_ports()
    assert ports == ["Port A", "KORG RK-100S 2", "Port C"]

def test_find_rk100s2_port_returns_index():
    assert find_rk100s2_port(["Port A", "KORG RK-100S 2", "Port C"]) == 1

def test_find_rk100s2_port_returns_none_when_missing():
    assert find_rk100s2_port(["Port A", "Port C"]) is None
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/midi/test_device.py -v
```

Expected: `ImportError: cannot import name 'list_midi_ports'`

**Step 3: Implement `midi/device.py`**

```python
from __future__ import annotations
import rtmidi

DEVICE_NAME_FRAGMENT = "RK-100S"


def list_midi_ports() -> list[str]:
    midi_out = rtmidi.MidiOut()
    ports = midi_out.get_ports()
    midi_out.close_port()
    del midi_out
    return ports


def find_rk100s2_port(ports: list[str]) -> int | None:
    for i, name in enumerate(ports):
        if DEVICE_NAME_FRAGMENT in name:
            return i
    return None


class MidiDevice:
    def __init__(self) -> None:
        self._midi_out = rtmidi.MidiOut()
        self._midi_in = rtmidi.MidiIn()
        self._connected = False
        self._port_name: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port_name(self) -> str | None:
        return self._port_name

    def connect(self, port_index: int, port_name: str) -> None:
        if self._connected:
            self.disconnect()
        self._midi_out.open_port(port_index)
        self._midi_in.open_port(port_index)
        self._connected = True
        self._port_name = port_name

    def disconnect(self) -> None:
        if self._connected:
            self._midi_out.close_port()
            self._midi_in.close_port()
        self._connected = False
        self._port_name = None

    def send(self, message: list[int]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to a MIDI device")
        self._midi_out.send_message(message)

    def set_sysex_callback(self, callback) -> None:
        self._midi_in.ignore_types(sysex=False)
        self._midi_in.set_callback(callback)
```

**Step 4: Run tests to verify they pass**

```
scripts/test.sh tests/midi/test_device.py -v
```

Expected: 3 PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: midi device discovery and connection"
```

---

## Task 3: SysEx Message Building

**Files:**
- Create: `midi/sysex.py`
- Create: `tests/midi/test_sysex.py`

**Step 1: Write the failing test in `tests/midi/test_sysex.py`**

```python
from midi.sysex import (
    build_program_dump_request, build_all_dump_request,
    parse_program_dump, build_program_write,
    KORG_ID, MODEL_ID,
)

def test_korg_id():
    assert KORG_ID == 0x42

def test_program_dump_request_structure():
    msg = build_program_dump_request(channel=1, program=5)
    assert msg[0] == 0xF0
    assert msg[1] == 0x42
    assert msg[2] == 0x30
    assert msg[-1] == 0xF7

def test_program_dump_request_channel_encoding():
    msg = build_program_dump_request(channel=3, program=0)
    assert msg[2] == 0x32  # 0x30 + (3-1)

def test_parse_program_dump_returns_bytes():
    fake = [0xF0, 0x42, 0x30, MODEL_ID, 0x40, 0x01, 0x02, 0x03, 0xF7]
    result = parse_program_dump(fake)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_parse_program_dump_rejects_non_korg():
    bad = [0xF0, 0x41, 0x30, MODEL_ID, 0x40, 0x01, 0xF7]
    assert parse_program_dump(bad) is None

def test_build_program_write_roundtrip():
    data = bytes([0x01, 0x02, 0x03])
    msg = build_program_write(channel=1, program=0, data=data)
    assert msg[0] == 0xF0
    assert msg[1] == 0x42
    assert msg[-1] == 0xF7
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/midi/test_sysex.py -v
```

**Step 3: Implement `midi/sysex.py`**

```python
from __future__ import annotations

KORG_ID = 0x42
MODEL_ID = 0x57  # TODO: verify against Parameter Guide

FUNC_PROGRAM_DUMP_REQUEST = 0x10
FUNC_ALL_DUMP_REQUEST = 0x0E
FUNC_PROGRAM_DUMP = 0x40
FUNC_ALL_DUMP = 0x4E


def _channel_byte(channel: int) -> int:
    return 0x30 + (channel - 1)


def build_program_dump_request(channel: int, program: int) -> list[int]:
    return [0xF0, KORG_ID, _channel_byte(channel), MODEL_ID,
            FUNC_PROGRAM_DUMP_REQUEST, program & 0x7F, 0xF7]


def build_all_dump_request(channel: int) -> list[int]:
    return [0xF0, KORG_ID, _channel_byte(channel), MODEL_ID,
            FUNC_ALL_DUMP_REQUEST, 0xF7]


def parse_program_dump(message: list[int]) -> bytes | None:
    if len(message) < 6:
        return None
    if message[0] != 0xF0 or message[1] != KORG_ID:
        return None
    if message[3] != MODEL_ID or message[4] != FUNC_PROGRAM_DUMP:
        return None
    return bytes(message[5:-1])


def build_program_write(channel: int, program: int, data: bytes) -> list[int]:
    return ([0xF0, KORG_ID, _channel_byte(channel), MODEL_ID,
             FUNC_PROGRAM_DUMP, program & 0x7F]
            + list(data) + [0xF7])
```

**Step 4: Run tests**

```
scripts/test.sh tests/midi/test_sysex.py -v
```

Expected: 6 PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: korg sysex message building and parsing"
```

---

## Task 4: Patch Data Model

**Files:**
- Create: `model/patch.py`
- Create: `tests/model/test_patch.py`

**Step 1: Write the failing test in `tests/model/test_patch.py`**

```python
from pathlib import Path
from model.patch import Patch

def test_patch_creation():
    p = Patch(name="Fat Pad", program_number=42)
    assert p.name == "Fat Pad"
    assert p.program_number == 42
    assert p.category == ""
    assert p.sysex_data is None

def test_patch_to_dict():
    p = Patch(name="Test", program_number=5, category="Lead", notes="bright")
    d = p.to_dict()
    assert d["name"] == "Test"
    assert d["program_number"] == 5

def test_patch_save_and_load(tmp_path):
    data = bytes([0xF0, 0x42, 0x30, 0xF7])
    p = Patch(name="My Patch", program_number=10, category="Bass", sysex_data=data)
    json_path = tmp_path / "my-patch.json"
    p.save(json_path)
    assert json_path.exists()
    assert (tmp_path / "my-patch.syx").exists()
    loaded = Patch.load(json_path)
    assert loaded.name == "My Patch"
    assert loaded.sysex_data == data

def test_patch_load_without_syx(tmp_path):
    p = Patch(name="No SysEx", program_number=3)
    json_path = tmp_path / "no-sysex.json"
    p.save(json_path)
    loaded = Patch.load(json_path)
    assert loaded.sysex_data is None
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/model/test_patch.py -v
```

**Step 3: Implement `model/patch.py`**

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date


@dataclass
class Patch:
    name: str
    program_number: int
    category: str = ""
    notes: str = ""
    sysex_data: bytes | None = None
    created: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "program_number": self.program_number,
            "category": self.category,
            "notes": self.notes,
            "created": self.created,
        }

    def save(self, json_path: Path) -> None:
        d = self.to_dict()
        if self.sysex_data is not None:
            syx_path = json_path.with_suffix(".syx")
            syx_path.write_bytes(self.sysex_data)
            d["sysex_file"] = syx_path.name
        else:
            d["sysex_file"] = None
        json_path.write_text(json.dumps(d, indent=2))

    @classmethod
    def load(cls, json_path: Path) -> Patch:
        d = json.loads(json_path.read_text())
        sysex_data = None
        if d.get("sysex_file"):
            syx_path = json_path.parent / d["sysex_file"]
            if syx_path.exists():
                sysex_data = syx_path.read_bytes()
        return cls(
            name=d["name"],
            program_number=d.get("program_number", 0),
            category=d.get("category", ""),
            notes=d.get("notes", ""),
            sysex_data=sysex_data,
            created=d.get("created", date.today().isoformat()),
        )

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-").replace("/", "-")
```

**Step 4: Run tests**

```
scripts/test.sh tests/model/test_patch.py -v
```

Expected: 4 PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: patch data model with save/load"
```

---

## Task 5: Bank Data Model

**Files:**
- Create: `model/bank.py`
- Create: `tests/model/test_bank.py`

**Step 1: Write failing test in `tests/model/test_bank.py`**

```python
from pathlib import Path
from model.bank import Bank

def test_bank_creation():
    b = Bank(name="Live Set 1")
    assert b.name == "Live Set 1"
    assert b.slots == {}

def test_bank_assign_and_remove():
    b = Bank(name="Test")
    b.assign(slot=0, patch_file=Path("patches/fat-pad.json"))
    assert b.slots[0] == Path("patches/fat-pad.json")
    b.remove(slot=0)
    assert 0 not in b.slots

def test_bank_save_and_load(tmp_path):
    b = Bank(name="My Bank")
    b.assign(slot=0, patch_file=Path("patches/fat-pad.json"))
    b.assign(slot=1, patch_file=Path("patches/saw-lead.json"))
    bank_path = tmp_path / "my-bank.json"
    b.save(bank_path)
    loaded = Bank.load(bank_path)
    assert loaded.name == "My Bank"
    assert loaded.slots[0] == Path("patches/fat-pad.json")
    assert loaded.slots[1] == Path("patches/saw-lead.json")

def test_bank_ordered_slots():
    b = Bank(name="Test")
    b.assign(slot=5, patch_file=Path("p5.json"))
    b.assign(slot=2, patch_file=Path("p2.json"))
    assert list(b.ordered_slots()) == [(2, Path("p2.json")), (5, Path("p5.json"))]
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/model/test_bank.py -v
```

**Step 3: Implement `model/bank.py`**

```python
from __future__ import annotations
import json
from pathlib import Path


class Bank:
    def __init__(self, name: str) -> None:
        self.name = name
        self.slots: dict[int, Path] = {}

    def assign(self, slot: int, patch_file: Path) -> None:
        self.slots[slot] = patch_file

    def remove(self, slot: int) -> None:
        self.slots.pop(slot, None)

    def ordered_slots(self) -> list[tuple[int, Path]]:
        return sorted(self.slots.items())

    def save(self, path: Path) -> None:
        d = {
            "name": self.name,
            "slots": [
                {"slot": slot, "patch_file": str(pf)}
                for slot, pf in self.ordered_slots()
            ],
        }
        path.write_text(json.dumps(d, indent=2))

    @classmethod
    def load(cls, path: Path) -> Bank:
        d = json.loads(path.read_text())
        bank = cls(name=d["name"])
        for entry in d.get("slots", []):
            bank.assign(entry["slot"], Path(entry["patch_file"]))
        return bank

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-")
```

**Step 4: Run tests**

```
scripts/test.sh tests/model/test_bank.py -v
```

Expected: 4 PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: bank data model with slot assignment and save/load"
```

---

## Task 6: Library Manager

**Files:**
- Create: `model/library.py`
- Create: `tests/model/test_library.py`

**Step 1: Write failing test in `tests/model/test_library.py`**

```python
from pathlib import Path
from model.patch import Patch
from model.bank import Bank
from model.library import Library

def test_library_creates_dirs(tmp_path):
    lib = Library(root=tmp_path)
    assert (tmp_path / "patches").exists()
    assert (tmp_path / "banks").exists()

def test_library_save_and_list_patches(tmp_path):
    lib = Library(root=tmp_path)
    p = Patch(name="Fat Pad", program_number=1)
    lib.save_patch(p)
    patches = lib.list_patches()
    assert len(patches) == 1
    assert patches[0].name == "Fat Pad"

def test_library_save_and_list_banks(tmp_path):
    lib = Library(root=tmp_path)
    b = Bank(name="Live Set")
    lib.save_bank(b)
    banks = lib.list_banks()
    assert len(banks) == 1
    assert banks[0].name == "Live Set"

def test_library_patch_name_collision(tmp_path):
    lib = Library(root=tmp_path)
    lib.save_patch(Patch(name="Test", program_number=1))
    lib.save_patch(Patch(name="Test", program_number=2))
    assert len(lib.list_patches()) == 2

def test_library_delete_patch(tmp_path):
    lib = Library(root=tmp_path)
    p = Patch(name="To Delete", program_number=5, sysex_data=bytes([0x01]))
    path = lib.save_patch(p)
    lib.delete_patch(path)
    assert len(lib.list_patches()) == 0
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/model/test_library.py -v
```

**Step 3: Implement `model/library.py`**

```python
from __future__ import annotations
from pathlib import Path
from model.patch import Patch
from model.bank import Bank


class Library:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._patches_dir = self.root / "patches"
        self._banks_dir = self.root / "banks"
        self._patches_dir.mkdir(parents=True, exist_ok=True)
        self._banks_dir.mkdir(parents=True, exist_ok=True)

    def _unique_path(self, directory: Path, slug: str, suffix: str) -> Path:
        path = directory / f"{slug}{suffix}"
        counter = 1
        while path.exists():
            path = directory / f"{slug}-{counter}{suffix}"
            counter += 1
        return path

    def save_patch(self, patch: Patch) -> Path:
        path = self._unique_path(self._patches_dir, patch.slug, ".json")
        patch.save(path)
        return path

    def list_patches(self) -> list[Patch]:
        result = []
        for f in sorted(self._patches_dir.glob("*.json")):
            try:
                result.append(Patch.load(f))
            except Exception:
                pass
        return result

    def delete_patch(self, json_path: Path) -> None:
        syx = json_path.with_suffix(".syx")
        if syx.exists():
            syx.unlink()
        if json_path.exists():
            json_path.unlink()

    def save_bank(self, bank: Bank) -> Path:
        path = self._unique_path(self._banks_dir, bank.slug, ".json")
        bank.save(path)
        return path

    def list_banks(self) -> list[Bank]:
        result = []
        for f in sorted(self._banks_dir.glob("*.json")):
            try:
                result.append(Bank.load(f))
            except Exception:
                pass
        return result
```

**Step 4: Run all model tests**

```
scripts/test.sh tests/model/ -v
```

Expected: All PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: library manager for patch and bank disk operations"
```

---

## Task 7: Device Panel UI

**Files:**
- Create: `ui/device_panel.py`
- Create: `tests/ui/test_device_panel.py`

**Step 1: Write failing test in `tests/ui/test_device_panel.py`**

```python
import sys
import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_device_panel_sends_pull_buttons_disabled_when_disconnected(app):
    with patch("midi.device.rtmidi"):
        from ui.device_panel import DevicePanel
        panel = DevicePanel()
        assert not panel.send_btn.isEnabled()
        assert not panel.pull_btn.isEnabled()
        assert not panel.load_all_btn.isEnabled()
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/ui/test_device_panel.py -v
```

**Step 3: Implement `ui/device_panel.py`**

```python
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal
from midi.device import MidiDevice, list_midi_ports, find_rk100s2_port


class DevicePanel(QWidget):
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    send_requested = pyqtSignal()
    pull_requested = pyqtSignal()
    load_all_requested = pyqtSignal()
    load_range_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._device = MidiDevice()
        self._build_ui()
        self._refresh_ports()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        conn_group = QGroupBox("Device")
        conn_layout = QVBoxLayout(conn_group)

        self.port_combo = QComboBox()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo)
        port_row.addWidget(refresh_btn)
        conn_layout.addLayout(port_row)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connect)
        conn_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("Not connected")
        conn_layout.addWidget(self.status_label)
        layout.addWidget(conn_group)

        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        self.send_btn = QPushButton("Send Patch to Device")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.send_requested)
        action_layout.addWidget(self.send_btn)

        self.pull_btn = QPushButton("Pull Current Program")
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self.pull_requested)
        action_layout.addWidget(self.pull_btn)

        self.load_all_btn = QPushButton("Load All Programs (200)")
        self.load_all_btn.setEnabled(False)
        self.load_all_btn.clicked.connect(self.load_all_requested)
        action_layout.addWidget(self.load_all_btn)

        self.load_range_btn = QPushButton("Load Slot Range...")
        self.load_range_btn.setEnabled(False)
        self.load_range_btn.clicked.connect(self.load_range_requested)
        action_layout.addWidget(self.load_range_btn)

        layout.addWidget(action_group)
        layout.addStretch()

    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        ports = list_midi_ports()
        for name in ports:
            self.port_combo.addItem(name)
        idx = find_rk100s2_port(ports)
        if idx is not None:
            self.port_combo.setCurrentIndex(idx)

    def _toggle_connect(self) -> None:
        if self._device.connected:
            self._device.disconnect()
            self._set_connected(False)
        else:
            idx = self.port_combo.currentIndex()
            name = self.port_combo.currentText()
            if idx >= 0:
                self._device.connect(idx, name)
                self._set_connected(True)

    def _set_connected(self, state: bool) -> None:
        for btn in (self.send_btn, self.pull_btn, self.load_all_btn, self.load_range_btn):
            btn.setEnabled(state)
        if state:
            self.connect_btn.setText("Disconnect")
            self.status_label.setText(f"Connected: {self._device.port_name}")
            self.connected.emit(self._device.port_name)
        else:
            self.connect_btn.setText("Connect")
            self.status_label.setText("Not connected")
            self.disconnected.emit()

    @property
    def device(self) -> MidiDevice:
        return self._device
```

**Step 4: Run tests**

```
scripts/test.sh tests/ui/test_device_panel.py -v
```

Expected: PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: device panel UI with port selection and connect/disconnect"
```

---

## Task 8: Patch Detail Panel

**Files:**
- Create: `ui/patch_detail.py`
- Create: `tests/ui/test_patch_detail.py`

**Step 1: Write failing test in `tests/ui/test_patch_detail.py`**

```python
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from model.patch import Patch

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_patch_detail_empty_by_default(app):
    from ui.patch_detail import PatchDetailPanel
    panel = PatchDetailPanel()
    assert panel.name_edit.text() == ""

def test_patch_detail_loads_patch(app):
    from ui.patch_detail import PatchDetailPanel
    panel = PatchDetailPanel()
    p = Patch(name="Fat Pad", program_number=42, category="Lead", notes="warm")
    panel.load_patch(p)
    assert panel.name_edit.text() == "Fat Pad"
    assert panel.slot_spin.value() == 42
    assert panel.category_edit.text() == "Lead"

def test_patch_detail_save_emits_signal(app, qtbot):
    from ui.patch_detail import PatchDetailPanel
    panel = PatchDetailPanel()
    panel.load_patch(Patch(name="Test", program_number=1))
    with qtbot.waitSignal(panel.patch_saved, timeout=1000):
        panel.save_btn.click()
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/ui/test_patch_detail.py -v
```

**Step 3: Implement `ui/patch_detail.py`**

```python
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QVBoxLayout,
    QLineEdit, QSpinBox, QTextEdit, QPushButton,
)
from PyQt6.QtCore import pyqtSignal
from model.patch import Patch


class PatchDetailPanel(QWidget):
    patch_saved = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._patch: Patch | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, 127)
        self.category_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)

        form.addRow("Name:", self.name_edit)
        form.addRow("Slot (0-127):", self.slot_spin)
        form.addRow("Category:", self.category_edit)
        form.addRow("Notes:", self.notes_edit)
        layout.addLayout(form)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save)
        layout.addWidget(self.save_btn)
        layout.addStretch()

    def load_patch(self, patch: Patch) -> None:
        self._patch = patch
        self.name_edit.setText(patch.name)
        self.slot_spin.setValue(patch.program_number)
        self.category_edit.setText(patch.category)
        self.notes_edit.setPlainText(patch.notes)

    def _on_save(self) -> None:
        if self._patch is None:
            return
        self._patch.name = self.name_edit.text()
        self._patch.program_number = self.slot_spin.value()
        self._patch.category = self.category_edit.text()
        self._patch.notes = self.notes_edit.toPlainText()
        self.patch_saved.emit(self._patch)

    def clear(self) -> None:
        self._patch = None
        self.name_edit.clear()
        self.slot_spin.setValue(0)
        self.category_edit.clear()
        self.notes_edit.clear()
```

**Step 4: Run tests**

```
scripts/test.sh tests/ui/test_patch_detail.py -v
```

Expected: 3 PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: patch detail panel with load/edit/save"
```

---

## Task 9: Library Panel

**Files:**
- Create: `ui/library_panel.py`
- Create: `tests/ui/test_library_panel.py`

**Step 1: Write failing test in `tests/ui/test_library_panel.py`**

```python
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from model.patch import Patch
from model.bank import Bank

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_library_panel_shows_patches(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    panel.populate(banks=[], patches=[Patch(name="Fat Pad", program_number=1)])
    assert panel.tree.topLevelItemCount() >= 1

def test_library_panel_shows_bank(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    panel.populate(banks=[Bank(name="Live Set 1")], patches=[])
    item = panel.tree.topLevelItem(0)
    assert "Live Set 1" in item.text(0)
```

**Step 2: Run test to verify it fails**

```
scripts/test.sh tests/ui/test_library_panel.py -v
```

**Step 3: Implement `ui/library_panel.py`**

```python
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem,
)
from PyQt6.QtCore import pyqtSignal, Qt
from model.patch import Patch
from model.bank import Bank


class LibraryPanel(QWidget):
    patch_selected = pyqtSignal(object)
    add_bank_requested = pyqtSignal()
    add_patch_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Library")
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        btn_row = QHBoxLayout()
        add_bank_btn = QPushButton("+ Bank")
        add_patch_btn = QPushButton("+ Patch from Device")
        add_bank_btn.clicked.connect(self.add_bank_requested)
        add_patch_btn.clicked.connect(self.add_patch_requested)
        btn_row.addWidget(add_bank_btn)
        btn_row.addWidget(add_patch_btn)
        layout.addLayout(btn_row)

    def populate(self, banks: list[Bank], patches: list[Patch]) -> None:
        self.tree.clear()
        for bank in banks:
            item = QTreeWidgetItem([bank.name])
            item.setData(0, Qt.ItemDataRole.UserRole, bank)
            self.tree.addTopLevelItem(item)
            item.setExpanded(True)

        if patches:
            loose = QTreeWidgetItem(["-- loose --"])
            loose.setFlags(loose.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(loose)
            for patch in patches:
                child = QTreeWidgetItem([patch.name])
                child.setData(0, Qt.ItemDataRole.UserRole, patch)
                loose.addChild(child)
            loose.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, Patch):
            self.patch_selected.emit(data)
```

**Step 4: Run tests**

```
scripts/test.sh tests/ui/test_library_panel.py -v
```

Expected: 2 PASSED

**Step 5: Commit**

```
scripts/git.sh commit "feat: library panel tree view with banks and loose patches"
```

---

## Task 10: Main Window

**Files:**
- Create: `ui/main_window.py`
- Modify: `main.py`

**Step 1: Implement `ui/main_window.py`**

```python
from __future__ import annotations
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QSplitter, QMessageBox, QInputDialog,
)
from PyQt6.QtCore import Qt
from midi.sysex import (
    build_program_dump_request, build_program_write, parse_program_dump,
)
from model.patch import Patch
from model.bank import Bank
from model.library import Library
from ui.library_panel import LibraryPanel
from ui.patch_detail import PatchDetailPanel
from ui.device_panel import DevicePanel

APP_ROOT = Path(__file__).parent.parent


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Korg RK-100S 2 Patch Manager")
        self.resize(1000, 600)
        self._library = Library(root=APP_ROOT)
        self._selected_patch: Patch | None = None
        self._build_ui()
        self._connect_signals()
        self._refresh_library()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._library_panel = LibraryPanel()
        self._detail_panel = PatchDetailPanel()
        self._device_panel = DevicePanel()
        splitter.addWidget(self._library_panel)
        splitter.addWidget(self._detail_panel)
        splitter.addWidget(self._device_panel)
        splitter.setSizes([250, 450, 300])
        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        self._library_panel.patch_selected.connect(self._on_patch_selected)
        self._library_panel.add_patch_requested.connect(self._on_pull_current)
        self._detail_panel.patch_saved.connect(self._on_patch_saved)
        self._device_panel.pull_requested.connect(self._on_pull_current)
        self._device_panel.send_requested.connect(self._on_send_patch)
        self._device_panel.load_all_requested.connect(self._on_load_all)
        self._device_panel.load_range_requested.connect(self._on_load_range)

    def _refresh_library(self) -> None:
        banks = self._library.list_banks()
        patches = self._library.list_patches()
        self._library_panel.populate(banks=banks, patches=patches)

    def _on_patch_selected(self, patch: Patch) -> None:
        self._selected_patch = patch
        self._detail_panel.load_patch(patch)

    def _on_patch_saved(self, patch: Patch) -> None:
        patches_dir = APP_ROOT / "patches"
        for json_file in patches_dir.glob("*.json"):
            try:
                loaded = Patch.load(json_file)
                if loaded.name == patch.name and loaded.program_number == patch.program_number:
                    patch.save(json_file)
                    break
            except Exception:
                pass
        self._refresh_library()

    def _pull_slot(self, slot: int) -> Patch | None:
        device = self._device_panel.device
        received: list[bytes] = []

        def on_sysex(event, data=None):
            message, _ = event
            parsed = parse_program_dump(message)
            if parsed is not None:
                received.append(parsed)

        device.set_sysex_callback(on_sysex)
        device.send(build_program_dump_request(channel=1, program=slot))
        time.sleep(2)

        if received:
            return Patch(
                name=f"Program {slot + 1:03d}",
                program_number=slot,
                sysex_data=received[0],
            )
        return None

    def _on_pull_current(self) -> None:
        device = self._device_panel.device
        if not device.connected:
            return
        patch = self._pull_slot(0)
        if patch:
            self._library.save_patch(patch)
            self._refresh_library()
        else:
            QMessageBox.warning(self, "Timeout", "No response from device within 2 seconds.")

    def _on_send_patch(self) -> None:
        if self._selected_patch is None:
            QMessageBox.information(self, "No patch selected", "Select a patch first.")
            return
        patch = self._selected_patch
        if patch.sysex_data is None:
            QMessageBox.warning(self, "No SysEx data", "This patch has no SysEx data to send.")
            return
        self._device_panel.device.send(
            build_program_write(channel=1, program=patch.program_number, data=patch.sysex_data)
        )

    def _on_load_all(self) -> None:
        device = self._device_panel.device
        if not device.connected:
            return
        for slot in range(200):
            patch = self._pull_slot(slot)
            if patch:
                self._library.save_patch(patch)
        self._refresh_library()

    def _on_load_range(self) -> None:
        start, ok1 = QInputDialog.getInt(self, "Load Slot Range", "Start slot (0-127):", 0, 0, 127)
        if not ok1:
            return
        end, ok2 = QInputDialog.getInt(self, "Load Slot Range", "End slot (0-127):", 40, start, 127)
        if not ok2:
            return
        device = self._device_panel.device
        if not device.connected:
            return
        for slot in range(start, end + 1):
            patch = self._pull_slot(slot)
            if patch:
                self._library.save_patch(patch)
        self._refresh_library()
```

**Step 2: Replace `main.py`**

```python
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Korg RK-100S 2 Patch Manager")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

**Step 3: Smoke test — run the app**

```
scripts/run.sh
```

Expected: Window opens, 3 panels visible, no console errors.

**Step 4: Commit**

```
scripts/git.sh commit "feat: main window wiring all panels together"
```

---

## Task 11: Full Test Suite

**Step 1: Run all tests**

```
scripts/test.sh tests/ -v
```

Expected: All PASSED

**Step 2: Fix any failures**

**Step 3: Commit if any fixes were made**

```
scripts/git.sh commit "fix: test suite cleanup"
```

---

## Known TODOs (post-v1)

- **Verify `MODEL_ID = 0x57`** in `midi/sysex.py` against Parameter Guide before real device testing
- Replace blocking `time.sleep()` in pull operations with `QThread` worker for non-blocking UI
- Dirty indicator in PatchDetailPanel when unsaved changes exist
- Bank push: send all slots in a bank to the device in one operation
- Real-time parameter editing via NRPN (requires Parameter Guide SysEx/NRPN map)
