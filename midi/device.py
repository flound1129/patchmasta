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
        self._note_callback = None
        self._sysex_callback = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port_name(self) -> str | None:
        return self._port_name

    def connect(self, port_index: int, port_name: str) -> None:
        if self._connected:
            self.disconnect()
        try:
            self._midi_out.open_port(port_index)
        except rtmidi.SystemError as exc:
            raise RuntimeError(
                f"Could not open MIDI output port '{port_name}'. "
                "It may be in use by another application (e.g. Korg software)."
            ) from exc
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
            try:
                self._midi_in.open_port(in_index)
            except rtmidi.SystemError as exc:
                raise RuntimeError(
                    f"Could not open MIDI input port '{in_ports[in_index]}'. "
                    "It may be in use by another application (e.g. Korg software)."
                ) from exc
            self._logger.midi(f"IN:  {in_ports[in_index]} (index {in_index})")
            self._midi_in.ignore_types(sysex=False)
            self._midi_in.set_callback(self._dispatch_midi_input)
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

    def send_nrpn(self, channel: int, msb: int, lsb: int, value: int) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to a MIDI device")
        ch = 0xB0 | ((channel - 1) & 0x0F)
        self._midi_out.send_message([ch, 99, msb & 0x7F])
        self._midi_out.send_message([ch, 98, lsb & 0x7F])
        self._midi_out.send_message([ch, 6, value & 0x7F])

    def send_cc(self, channel: int, cc: int, value: int) -> None:
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

    def _dispatch_midi_input(self, event, _data=None) -> None:
        """Route incoming MIDI messages to the appropriate callback."""
        msg = event[0]
        if not msg:
            return
        status = msg[0]
        if status == 0xF0:
            # SysEx message
            if self._sysex_callback is not None:
                self._sysex_callback(event, _data)
            else:
                self._logger.midi(f"RX sysex: {len(msg)} bytes")
        elif (status & 0xF0) == 0x90 and len(msg) >= 3 and msg[2] > 0:
            # Note On
            if self._note_callback is not None:
                self._note_callback(msg[1], msg[2], True)
            self._logger.midi(f"RX note-on: {msg[1]} vel={msg[2]}")
        elif (status & 0xF0) == 0x80 or ((status & 0xF0) == 0x90 and len(msg) >= 3 and msg[2] == 0):
            # Note Off
            if self._note_callback is not None:
                self._note_callback(msg[1], 0, False)
            self._logger.midi(f"RX note-off: {msg[1]}")
        else:
            self._logger.midi(f"RX raw: {[hex(b) for b in msg]}")

    def set_note_callback(self, callback) -> None:
        """Register a callback for incoming note messages: callback(note, velocity, is_on)."""
        self._note_callback = callback

    def set_sysex_callback(self, callback) -> None:
        """Register a callback for incoming SysEx messages."""
        if not self._connected:
            raise RuntimeError("Not connected to a MIDI device")
        self._sysex_callback = callback
