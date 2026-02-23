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


def test_get_param_bit_mask():
    """sysex_bit_mask: get_param returns only masked bits."""
    param = ParamDef("test", "Test", "test", 0, 127,
                     sysex_offset=2, sysex_bit_mask=0x7F)
    data = bytearray(8)
    data[2] = 0b10000001  # bit 7 = lock On, CC# = 1
    buf = SysExProgramBuffer(data)
    assert buf.get_param(param) == 1  # only bits 0-6


def test_set_param_bit_mask_preserves_other_bits():
    """sysex_bit_mask: set_param does read-modify-write, preserving unmasked bits."""
    mod_assign = ParamDef("mod_assign", "Mod Assign", "test", 0, 127,
                          sysex_offset=2, sysex_bit_mask=0x7F)
    mod_lock = ParamDef("mod_lock", "Mod Lock", "test", 0, 1,
                        sysex_offset=2, sysex_bit=7)
    data = bytearray(8)
    data[2] = 0b10000001  # lock=On (bit 7), CC#=1
    buf = SysExProgramBuffer(data)
    # Change CC# to 64 — lock bit should be preserved
    buf.set_param(mod_assign, 64)
    assert buf.get_byte(2) == 0b11000000  # bit 7 still set, CC#=64
    assert buf.get_param(mod_assign) == 64
    assert buf.get_param(mod_lock) == 127  # still On


def test_get_param_bit_mask_with_shift():
    """sysex_bit_mask + sysex_bit_shift: get_param returns shifted masked value."""
    param = ParamDef("test", "Test", "test", 0, 15,
                     sysex_offset=2, sysex_bit_mask=0xF0, sysex_bit_shift=4)
    data = bytearray(8)
    data[2] = 0b00100011  # bits 4-7 = 0010 = 2, bits 0-2 = 011 = 3
    buf = SysExProgramBuffer(data)
    assert buf.get_param(param) == 2  # high nibble only, shifted right


def test_set_param_bit_mask_with_shift():
    """sysex_bit_mask + sysex_bit_shift: set_param writes to the correct nibble."""
    arp_res = ParamDef("arp_res", "Arp Res", "test", 0, 127,
                       sysex_offset=2, sysex_bit_mask=0xF0, sysex_bit_shift=4)
    arp_type = ParamDef("arp_type", "Arp Type", "test", 0, 127,
                        sysex_offset=2, sysex_bit_mask=0x07)
    data = bytearray(8)
    data[2] = 0b00100010  # res=2 (high nibble), type=2 (bits 0-2)
    buf = SysExProgramBuffer(data)
    buf.set_param(arp_res, 5)  # set resolution to 5
    assert buf.get_byte(2) == 0b01010010  # bits 4-7=5, bits 0-2 unchanged (2)
    assert buf.get_param(arp_type) == 2   # type bits preserved


def test_get_param_value_map():
    """sysex_value_map: get_param returns NRPN value via inverse map."""
    param = ParamDef("test", "Test", "test", 0, 127,
                     sysex_offset=2, sysex_bit_mask=0x07,
                     sysex_value_map={0: 0, 22: 1, 43: 2, 64: 3})
    data = bytearray(8)
    data[2] = 0b00000010  # SysEx value = 2 (Alt1)
    buf = SysExProgramBuffer(data)
    assert buf.get_param(param) == 43  # SysEx 2 → NRPN 43


def test_set_param_value_map():
    """sysex_value_map: set_param converts NRPN to SysEx value."""
    param = ParamDef("test", "Test", "test", 0, 127,
                     sysex_offset=2, sysex_bit_mask=0x07,
                     sysex_value_map={0: 0, 22: 1, 43: 2, 64: 3})
    data = bytearray(8)
    data[2] = 0b00100000  # bits 4-7 = 2, bits 0-2 = 0
    buf = SysExProgramBuffer(data)
    buf.set_param(param, 43)  # NRPN 43 → SysEx 2
    assert buf.get_byte(2) == 0b00100010  # bits 4-7 preserved, bits 0-2 = 2
    assert buf.get_param(param) == 43


def test_get_param_value_bias():
    """sysex_value_bias: get_param adds bias when reading."""
    param = ParamDef("test", "Test", "test", 1, 8,
                     sysex_offset=2, sysex_bit_mask=0x07, sysex_value_bias=1)
    data = bytearray(8)
    data[2] = 0b10000111  # bits 0-2 = 7 (stored as last_step-1 = 8-1)
    buf = SysExProgramBuffer(data)
    assert buf.get_param(param) == 8  # 7 + bias(1) = 8


def test_set_param_value_bias():
    """sysex_value_bias: set_param subtracts bias when writing."""
    param = ParamDef("arp_last", "Last Step", "test", 1, 8,
                     sysex_offset=2, sysex_bit_mask=0x07, sysex_value_bias=1)
    latch = ParamDef("latch", "Latch", "test", 0, 1,
                     sysex_offset=2, sysex_bit=7)
    data = bytearray(8)
    data[2] = 0b10000111  # latch=On (bit 7), last_step=8 (bits 0-2 = 7)
    buf = SysExProgramBuffer(data)
    buf.set_param(param, 4)  # NRPN 4 → SysEx 3 (4-1)
    assert buf.get_byte(2) == 0b10000011  # bit 7 preserved, bits 0-2 = 3
    assert buf.get_param(param) == 4       # reads back as 4
    assert buf.get_param(latch) == 127     # latch still On


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
