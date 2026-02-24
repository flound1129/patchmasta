from midi.sysex import (
    build_program_change, build_slot_messages, build_program_dump_request,
    build_all_dump_request, parse_program_dump, build_program_write,
    extract_patch_name, KORG_ID, MODEL_ID, NUM_PROGRAMS,
)

def test_korg_id():
    assert KORG_ID == 0x42

def test_program_dump_request_structure():
    msg = build_program_dump_request(channel=1)
    assert msg[0] == 0xF0
    assert msg[1] == 0x42
    assert msg[2] == 0x30
    assert msg[-1] == 0xF7
    # No program number byte — just F0 42 3n <model_id> 10 F7
    assert len(msg) == 3 + len(MODEL_ID) + 2

def test_program_dump_request_channel_encoding():
    msg = build_program_dump_request(channel=3)
    assert msg[2] == 0x32  # 0x30 + (3-1)

def test_build_program_change():
    msg = build_program_change(channel=1, program=5)
    assert msg == [0xC0, 5]
    msg16 = build_program_change(channel=16, program=127)
    assert msg16 == [0xCF, 127]

def test_build_program_change_invalid_channel():
    import pytest
    with pytest.raises(ValueError):
        build_program_change(channel=0, program=0)
    with pytest.raises(ValueError):
        build_program_change(channel=17, program=0)

def test_parse_program_dump_returns_bytes():
    fake = [0xF0, 0x42, 0x30, *MODEL_ID, 0x40, 0x01, 0x02, 0x03, 0xF7]
    result = parse_program_dump(fake)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_parse_program_dump_rejects_non_korg():
    bad = [0xF0, 0x41, 0x30, *MODEL_ID, 0x40, 0x01, 0xF7]
    assert parse_program_dump(bad) is None

def test_build_program_write_structure():
    data = bytes([0x01, 0x02, 0x03])
    msg = build_program_write(channel=1, data=data)
    assert msg[0] == 0xF0
    assert msg[1] == 0x42
    assert msg[-1] == 0xF7

def test_invalid_channel_raises():
    import pytest
    with pytest.raises(ValueError):
        build_program_dump_request(channel=0)
    with pytest.raises(ValueError):
        build_program_dump_request(channel=17)

def test_parse_program_dump_rejects_missing_f7():
    bad = [0xF0, 0x42, 0x30, *MODEL_ID, 0x40, 0x01, 0x02]  # no F7
    assert parse_program_dump(bad) is None

def test_extract_patch_name_ascii():
    name_bytes = list(b"BrassLead   ")
    data = bytes(name_bytes + [0x00] * 20)
    assert extract_patch_name(data) == "BrassLead"

def test_extract_patch_name_strips_padding():
    data = bytes(list(b"Pad         ") + [0x00] * 20)
    assert extract_patch_name(data) == "Pad"

def test_extract_patch_name_empty_data():
    assert extract_patch_name(b"") is None

def test_extract_patch_name_short_data():
    assert extract_patch_name(b"\x00\x01") is None


def test_num_programs():
    assert NUM_PROGRAMS == 200


def test_build_slot_messages_bank0():
    """Slots 0-127 use bank LSB=0."""
    msgs = build_slot_messages(channel=1, slot=0)
    assert len(msgs) == 3
    assert msgs[0] == [0xB0, 0, 0]   # CC#0 MSB=0
    assert msgs[1] == [0xB0, 32, 0]  # CC#32 LSB=0
    assert msgs[2] == [0xC0, 0]      # PC=0

    msgs127 = build_slot_messages(channel=1, slot=127)
    assert msgs127[1] == [0xB0, 32, 0]
    assert msgs127[2] == [0xC0, 127]


def test_build_slot_messages_bank1():
    """Slots 128-199 use bank LSB=1, PC = slot - 128."""
    msgs = build_slot_messages(channel=1, slot=128)
    assert msgs[1] == [0xB0, 32, 1]  # CC#32 LSB=1
    assert msgs[2] == [0xC0, 0]      # PC=0

    msgs199 = build_slot_messages(channel=1, slot=199)
    assert msgs199[1] == [0xB0, 32, 1]
    assert msgs199[2] == [0xC0, 71]  # 199 - 128 = 71


def test_build_slot_messages_channel_encoding():
    msgs = build_slot_messages(channel=2, slot=5)
    assert msgs[0][0] == 0xB1  # CC on channel 2
    assert msgs[2][0] == 0xC1  # PC on channel 2


def test_build_slot_messages_invalid():
    import pytest
    with pytest.raises(ValueError):
        build_slot_messages(channel=1, slot=-1)
    with pytest.raises(ValueError):
        build_slot_messages(channel=1, slot=200)
    with pytest.raises(ValueError):
        build_slot_messages(channel=0, slot=0)
