import pytest
from unittest.mock import patch, MagicMock
from midi.device import list_midi_ports, find_rk100s2_port


@pytest.fixture
def mock_rtmidi():
    with patch("midi.device.rtmidi") as mock_mod:
        mock_mod.MidiOut.return_value = MagicMock()
        mock_mod.MidiIn.return_value = MagicMock()
        yield mock_mod


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


def test_send_nrpn(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = True
    sent = []
    dev._midi_out = type("FakeOut", (), {"send_message": lambda self, m: sent.append(m)})()
    dev.send_nrpn(channel=1, msb=0x05, lsb=0x00, value=63)
    assert len(sent) == 3
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

def test_send_note_on(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = True
    sent = []
    dev._midi_out = type("FakeOut", (), {"send_message": lambda self, m: sent.append(m)})()
    dev.send_note_on(channel=1, note=60, velocity=100)
    assert sent == [[0x90, 60, 100]]

def test_send_note_off(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = True
    sent = []
    dev._midi_out = type("FakeOut", (), {"send_message": lambda self, m: sent.append(m)})()
    dev.send_note_off(channel=1, note=60)
    assert sent == [[0x80, 60, 0]]

def test_send_nrpn_not_connected(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = False
    with pytest.raises(RuntimeError, match="Not connected"):
        dev.send_nrpn(channel=1, msb=0x05, lsb=0x00, value=63)

def test_send_cc_not_connected(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = False
    with pytest.raises(RuntimeError, match="Not connected"):
        dev.send_cc(channel=1, cc=7, value=100)

def test_send_note_on_not_connected(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = False
    with pytest.raises(RuntimeError, match="Not connected"):
        dev.send_note_on(channel=1, note=60, velocity=100)

def test_send_note_off_not_connected(mock_rtmidi):
    from midi.device import MidiDevice
    dev = MidiDevice()
    dev._connected = False
    with pytest.raises(RuntimeError, match="Not connected"):
        dev.send_note_off(channel=1, note=60)
