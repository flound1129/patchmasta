from __future__ import annotations
import rtmidi
from core.logger import AppLogger

DEVICE_NAME_FRAGMENT = "RK-100S"


def list_midi_ports() -> list[str]:
    midi_out = rtmidi.MidiOut()
    ports = midi_out.get_ports()
    midi_out.delete()
    return ports


def find_rk100s2_port(ports: list[str]) -> int | None:
    # Prefer the SOUND port — that's the internal synth, which handles SysEx dumps
    for i, name in enumerate(ports):
        if DEVICE_NAME_FRAGMENT in name and "SOUND" in name:
            return i
    # Fall back to any port matching the device name
    for i, name in enumerate(ports):
        if DEVICE_NAME_FRAGMENT in name:
            return i
    return None


class MidiDevice:
    def __init__(self, logger: AppLogger | None = None) -> None:
        self._midi_out = rtmidi.MidiOut()
        self._midi_in = rtmidi.MidiIn()
        self._connected = False
        self._port_name: str | None = None
        self._logger = logger or AppLogger()

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
        self._logger.midi(f"OUT: {port_name} (index {port_index})")
        try:
            # Input and output port indices are independent on Windows —
            # find the input port by name rather than assuming the same index.
            in_ports = self._midi_in.get_ports()
            self._logger.midi(f"available IN ports: {in_ports}")
            in_index = next(
                (i for i, n in enumerate(in_ports) if DEVICE_NAME_FRAGMENT in n),
                None,
            )
            if in_index is None:
                raise RuntimeError(f"No MIDI input port found matching '{DEVICE_NAME_FRAGMENT}'")
            self._midi_in.open_port(in_index)
            self._logger.midi(f"IN:  {in_ports[in_index]} (index {in_index})")
            # Catch-all debug listener — logs every incoming message until replaced
            self._midi_in.ignore_types(sysex=False)
            self._midi_in.set_callback(
                lambda ev, _=None: self._logger.midi(f"RX raw: {[hex(b) for b in ev[0]]}")
            )
        except Exception:
            self._midi_out.close_port()
            raise
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
        if not self._connected:
            raise RuntimeError("Not connected to a MIDI device")
        self._midi_in.ignore_types(sysex=False)
        self._midi_in.set_callback(callback)
