from __future__ import annotations
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class SysExProgramBuffer:
    """In-memory buffer holding full RK-100S 2 program SysEx data.

    Provides typed access to individual bytes and parameters via ParamDef
    metadata.  Tracks dirty state so callers know when to write back.
    """

    def __init__(self, data: bytes | bytearray | None = None) -> None:
        self._data = bytearray(data) if data else bytearray()
        self._dirty = False

    # -- raw byte access --

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    def load(self, data: bytes | bytearray) -> None:
        self._data = bytearray(data)
        self._dirty = False

    def to_bytes(self) -> bytes:
        return bytes(self._data)

    def get_byte(self, offset: int) -> int:
        if offset < 0 or offset >= len(self._data):
            raise IndexError(f"Offset {offset} out of range (size={len(self._data)})")
        return self._data[offset]

    def set_byte(self, offset: int, value: int) -> None:
        if offset < 0 or offset >= len(self._data):
            raise IndexError(f"Offset {offset} out of range (size={len(self._data)})")
        value = value & 0x7F  # Korg uses 7-bit values
        if self._data[offset] != value:
            self._data[offset] = value
            self._dirty = True

    def get_signed(self, offset: int) -> int:
        """Read a 7-bit value and interpret as signed (-64..+63)."""
        raw = self.get_byte(offset)
        return raw if raw < 64 else raw - 128

    def set_signed(self, offset: int, value: int) -> None:
        """Write a signed value (-64..+63) as 7-bit unsigned."""
        if value < 0:
            value = value + 128
        self.set_byte(offset, value)

    # -- ParamDef-aware access --

    def get_param(self, param_def) -> int | None:
        """Read a parameter value using its sysex_offset metadata.

        Returns None if the param has no sysex_offset or buffer is empty.
        For bit-packed params (sysex_bit set), extracts the individual bit
        and returns 0 or 127 to match the NRPN value scale.
        """
        if param_def.sysex_offset is None or not self._data:
            return None
        if param_def.sysex_offset >= len(self._data):
            return None
        if param_def.sysex_bit is not None:
            byte_val = self._data[param_def.sysex_offset]
            bit_val = (byte_val >> param_def.sysex_bit) & 1
            return 127 if bit_val else 0
        if param_def.sysex_signed:
            return self.get_signed(param_def.sysex_offset)
        return self.get_byte(param_def.sysex_offset)

    def set_param(self, param_def, value: int) -> None:
        """Write a parameter value using its sysex_offset metadata.

        For bit-packed params (sysex_bit set), sets or clears the individual
        bit based on whether value >= 64 (matching NRPN on/off threshold).
        """
        if param_def.sysex_offset is None:
            raise ValueError(f"Parameter '{param_def.name}' has no sysex_offset")
        if not self._data:
            raise ValueError("Buffer is empty — load program data first")
        if param_def.sysex_bit is not None:
            current = self._data[param_def.sysex_offset]
            bit_mask = 1 << param_def.sysex_bit
            new_val = (current | bit_mask) if value >= 64 else (current & ~bit_mask)
            if current != new_val:
                self._data[param_def.sysex_offset] = new_val
                self._dirty = True
            return
        if param_def.sysex_signed:
            self.set_signed(param_def.sysex_offset, value)
        else:
            self.set_byte(param_def.sysex_offset, value)


class DebouncedSysExWriter(QObject):
    """Debounces SysEx program writes to avoid flooding the device.

    When a parameter changes, call `schedule()`.  After the debounce interval
    elapses with no further calls, `write_requested` is emitted so the caller
    can perform the actual SysEx write.
    """

    write_requested = pyqtSignal()

    def __init__(self, debounce_ms: int = 150, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self.write_requested.emit)

    @property
    def debounce_ms(self) -> int:
        return self._timer.interval()

    @debounce_ms.setter
    def debounce_ms(self, value: int) -> None:
        self._timer.setInterval(value)

    def schedule(self) -> None:
        """(Re)start the debounce timer."""
        self._timer.start()

    def cancel(self) -> None:
        self._timer.stop()

    @property
    def is_pending(self) -> bool:
        return self._timer.isActive()
