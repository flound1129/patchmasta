import pytest
from midi.sysex_buffer import SysExProgramBuffer, DebouncedSysExWriter
from midi.params import ParamDef


def test_empty_buffer():
    buf = SysExProgramBuffer()
    assert buf.size == 0
    assert not buf.dirty


def test_load_data():
    data = bytes(range(128))
    buf = SysExProgramBuffer(data)
    assert buf.size == 128
    assert not buf.dirty
    assert buf.to_bytes() == data


def test_get_set_byte():
    buf = SysExProgramBuffer(bytes(64))
    assert buf.get_byte(0) == 0
    buf.set_byte(10, 42)
    assert buf.get_byte(10) == 42
    assert buf.dirty


def test_set_byte_clamps_7bit():
    buf = SysExProgramBuffer(bytes(16))
    buf.set_byte(0, 0xFF)  # should be masked to 0x7F
    assert buf.get_byte(0) == 0x7F


def test_set_byte_unchanged_not_dirty():
    buf = SysExProgramBuffer(bytes(16))
    assert not buf.dirty
    buf.set_byte(0, 0)  # same value
    assert not buf.dirty


def test_mark_clean():
    buf = SysExProgramBuffer(bytes(16))
    buf.set_byte(0, 1)
    assert buf.dirty
    buf.mark_clean()
    assert not buf.dirty


def test_get_set_signed():
    buf = SysExProgramBuffer(bytes(16))
    # Positive value
    buf.set_signed(0, 10)
    assert buf.get_signed(0) == 10
    # Negative value
    buf.set_signed(1, -10)
    assert buf.get_signed(1) == -10
    # Boundary: -64
    buf.set_signed(2, -64)
    assert buf.get_signed(2) == -64
    # Boundary: 63
    buf.set_signed(3, 63)
    assert buf.get_signed(3) == 63


def test_out_of_range_raises():
    buf = SysExProgramBuffer(bytes(8))
    with pytest.raises(IndexError):
        buf.get_byte(8)
    with pytest.raises(IndexError):
        buf.set_byte(-1, 0)


def test_load_resets_dirty():
    buf = SysExProgramBuffer(bytes(8))
    buf.set_byte(0, 1)
    assert buf.dirty
    buf.load(bytes(16))
    assert not buf.dirty
    assert buf.size == 16


def test_get_param_with_sysex_offset():
    param = ParamDef("test", "Test", "test effect", 0, 127, sysex_offset=5)
    data = bytearray(16)
    data[5] = 42
    buf = SysExProgramBuffer(data)
    assert buf.get_param(param) == 42


def test_get_param_signed():
    param = ParamDef("test", "Test", "test effect", -63, 63,
                     sysex_offset=3, sysex_signed=True)
    data = bytearray(16)
    data[3] = 128 - 10  # -10 in signed
    buf = SysExProgramBuffer(data)
    assert buf.get_param(param) == -10


def test_set_param():
    param = ParamDef("test", "Test", "test effect", 0, 127, sysex_offset=7)
    buf = SysExProgramBuffer(bytes(16))
    buf.set_param(param, 99)
    assert buf.get_byte(7) == 99
    assert buf.dirty


def test_get_param_no_offset():
    param = ParamDef("test", "Test", "test effect", 0, 127)
    buf = SysExProgramBuffer(bytes(16))
    assert buf.get_param(param) is None


def test_set_param_no_offset_raises():
    param = ParamDef("test", "Test", "test effect", 0, 127)
    buf = SysExProgramBuffer(bytes(16))
    with pytest.raises(ValueError):
        buf.set_param(param, 42)


def test_set_param_empty_buffer_raises():
    param = ParamDef("test", "Test", "test effect", 0, 127, sysex_offset=0)
    buf = SysExProgramBuffer()
    with pytest.raises(ValueError):
        buf.set_param(param, 42)


def test_debounced_writer_properties(qtbot):
    writer = DebouncedSysExWriter(debounce_ms=200)
    assert writer.debounce_ms == 200
    writer.debounce_ms = 100
    assert writer.debounce_ms == 100


def test_debounced_writer_emits_signal(qtbot):
    writer = DebouncedSysExWriter(debounce_ms=50)
    with qtbot.waitSignal(writer.write_requested, timeout=500):
        writer.schedule()


def test_debounced_writer_cancel(qtbot):
    writer = DebouncedSysExWriter(debounce_ms=50)
    writer.schedule()
    assert writer.is_pending
    writer.cancel()
    assert not writer.is_pending
