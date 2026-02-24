from __future__ import annotations

KORG_ID = 0x42
MODEL_ID = [0x00, 0x01, 0x22]  # RK-100S 2 model ID (3 bytes, confirmed from Parameter Guide)

FUNC_PROGRAM_DUMP_REQUEST = 0x10
FUNC_ALL_DUMP_REQUEST = 0x0E
FUNC_PROGRAM_DUMP = 0x40
FUNC_ALL_DUMP = 0x4E

_MODEL_ID_LEN = len(MODEL_ID)


def _channel_byte(channel: int) -> int:
    if not (1 <= channel <= 16):
        raise ValueError(f"MIDI channel must be 1-16, got {channel}")
    return 0x30 + (channel - 1)


NUM_PROGRAMS = 200  # RK-100S 2 has 200 programs across 2 banks

def build_program_change(channel: int, program: int) -> list[int]:
    """Standard MIDI Program Change message (not SysEx)."""
    if not (1 <= channel <= 16):
        raise ValueError(f"MIDI channel must be 1-16, got {channel}")
    return [0xC0 | (channel - 1), program & 0x7F]


def build_slot_messages(channel: int, slot: int) -> list[list[int]]:
    """Return bank-select + program-change messages for a given slot (0-199).

    Bank 0 (CC#32=0): slots 0-127
    Bank 1 (CC#32=1): slots 128-199
    """
    if not (1 <= channel <= 16):
        raise ValueError(f"MIDI channel must be 1-16, got {channel}")
    if not (0 <= slot < NUM_PROGRAMS):
        raise ValueError(f"Slot must be 0-{NUM_PROGRAMS - 1}, got {slot}")
    ch = channel - 1
    bank_lsb = 0 if slot < 128 else 1
    pc = slot if slot < 128 else slot - 128
    return [
        [0xB0 | ch, 0, 0],          # CC#0  bank MSB = 0
        [0xB0 | ch, 32, bank_lsb],  # CC#32 bank LSB
        [0xC0 | ch, pc],            # Program Change
    ]


def build_program_dump_request(channel: int) -> list[int]:
    """Request dump of the currently loaded program (no program number)."""
    return [0xF0, KORG_ID, _channel_byte(channel), *MODEL_ID,
            FUNC_PROGRAM_DUMP_REQUEST, 0xF7]


def build_all_dump_request(channel: int) -> list[int]:
    return [0xF0, KORG_ID, _channel_byte(channel), *MODEL_ID,
            FUNC_ALL_DUMP_REQUEST, 0xF7]


def parse_program_dump(message: list[int]) -> bytes | None:
    # Format: F0 42 3n 00 01 22 40 [data] F7
    if len(message) < 3 + _MODEL_ID_LEN + 3:
        return None
    if message[0] != 0xF0 or message[1] != KORG_ID:
        return None
    if list(message[3:3 + _MODEL_ID_LEN]) != MODEL_ID:
        return None
    func_idx = 3 + _MODEL_ID_LEN
    if message[func_idx] != FUNC_PROGRAM_DUMP:
        return None
    if message[-1] != 0xF7:
        return None
    return bytes(message[func_idx + 1:-1])


PATCH_NAME_OFFSET = 0
PATCH_NAME_LENGTH = 12


def extract_patch_name(data: bytes) -> str | None:
    if len(data) < PATCH_NAME_OFFSET + PATCH_NAME_LENGTH:
        return None
    raw = data[PATCH_NAME_OFFSET:PATCH_NAME_OFFSET + PATCH_NAME_LENGTH]
    name = bytes(b for b in raw if 0x20 <= b <= 0x7E).decode("ascii").strip()
    return name or None


def build_program_write(channel: int, data: bytes) -> list[int]:
    if any(b & 0x80 for b in data):
        raise ValueError("SysEx data bytes must all be <= 0x7F")
    return ([0xF0, KORG_ID, _channel_byte(channel), *MODEL_ID,
             FUNC_PROGRAM_DUMP]
            + list(data) + [0xF7])
