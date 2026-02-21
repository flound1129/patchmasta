import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from model.patch import Patch

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

@pytest.fixture
def main_window(app, tmp_path):
    with patch("midi.device.rtmidi"):
        from ui.main_window import MainWindow
        with patch("ui.main_window.APP_ROOT", tmp_path):
            win = MainWindow()
    return win

def test_send_patch_no_selection_shows_dialog(main_window, qtbot, monkeypatch):
    """Send with no patch selected shows info dialog, does not crash."""
    shown = []
    monkeypatch.setattr(
        "ui.main_window.QMessageBox.information",
        lambda *a, **kw: shown.append(True),
    )
    main_window._on_send_patch()
    assert shown

def test_send_patch_no_sysex_shows_warning(main_window, qtbot, monkeypatch):
    """Send with a patch that has no SysEx data shows warning."""
    main_window._selected_patch = Patch(name="Empty", program_number=0)
    shown = []
    monkeypatch.setattr(
        "ui.main_window.QMessageBox.warning",
        lambda *a, **kw: shown.append(True),
    )
    main_window._on_send_patch()
    assert shown

def test_on_patch_saved_uses_source_path(main_window, tmp_path):
    """_on_patch_saved writes to source_path when available."""
    patches_dir = tmp_path / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    p = Patch(name="Test", program_number=1)
    json_path = patches_dir / "test.json"
    p.save(json_path)
    p.source_path = json_path

    main_window._selected_patch = p
    main_window._selected_patch_path = json_path

    p.name = "Renamed"
    main_window._on_patch_saved(p)

    loaded = Patch.load(json_path)
    assert loaded.name == "Renamed"
