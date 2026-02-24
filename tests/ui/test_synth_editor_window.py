import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from midi.params import ParamMap
from core.config import AppConfig
from core.logger import AppLogger


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app):
    with patch("midi.device.rtmidi"):
        from midi.device import MidiDevice
        device = MidiDevice()
        from ui.synth_editor_window import SynthEditorWindow
        win = SynthEditorWindow(
            device=device,
            param_map=ParamMap(),
            config=AppConfig(),
            logger=AppLogger(),
        )
    return win


def test_editor_has_chat_and_params(editor):
    assert editor._chat_panel is not None
    assert editor._params_panel is not None


def test_editor_close_hides_window(editor):
    editor.show()
    editor.close()
    assert not editor.isVisible()


def test_set_device_connected_propagates(editor):
    editor.set_device_connected(True)
    assert editor._chat_panel.input_edit.isEnabled()
    editor.set_device_connected(False)
    assert not editor._chat_panel.input_edit.isEnabled()


def test_user_param_change_sends_midi_when_connected(app):
    mock_device = MagicMock()
    mock_device.connected = True
    from ui.synth_editor_window import SynthEditorWindow
    win = SynthEditorWindow(
        device=mock_device, param_map=ParamMap(),
        config=AppConfig(), logger=AppLogger(),
    )
    win._on_user_param_change("arp_on_off", 127)
    assert mock_device.send.called


def test_user_param_change_skips_when_disconnected(app):
    mock_device = MagicMock()
    mock_device.connected = False
    from ui.synth_editor_window import SynthEditorWindow
    win = SynthEditorWindow(
        device=mock_device, param_map=ParamMap(),
        config=AppConfig(), logger=AppLogger(),
    )
    win._on_user_param_change("arp_on_off", 127)
    assert not mock_device.send.called


def test_save_action_disabled_initially(editor):
    assert not editor._save_action.isEnabled()


def test_save_action_enabled_after_load(editor):
    editor.load_program_data(bytes(496))
    assert editor._save_action.isEnabled()


def test_transport_panel_exists(editor):
    from ui.keyboard_widget import TransportPanel
    assert hasattr(editor, "_transport_panel")
    assert isinstance(editor._transport_panel, TransportPanel)


def test_midi_player_lazy_init(editor):
    assert editor._midi_player is None


def test_save_patch_writes_file(editor, tmp_path):
    """Verify that saving writes a valid 528-byte .rk100s2_prog file."""
    from tools.file_format import sysex_to_prog_bytes
    editor.load_program_data(bytes(496))
    dest = tmp_path / "test.rk100s2_prog"
    # Write directly (same logic as _on_save_patch without the dialog)
    file_bytes = sysex_to_prog_bytes(editor._sysex_buffer.to_bytes())
    dest.write_bytes(file_bytes)
    assert dest.exists()
    assert len(dest.read_bytes()) == 528  # 32-byte header + 496 data
    assert dest.read_bytes()[:8] == b"12100PgD"
