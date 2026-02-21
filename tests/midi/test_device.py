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
