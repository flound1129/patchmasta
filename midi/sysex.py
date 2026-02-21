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


def build_program_dump_request(channel: int, program: int) -> list[int]:
    return [0xF0, KORG_ID, _channel_byte(channel), *MODEL_ID,
            FUNC_PROGRAM_DUMP_REQUEST, program & 0x7F, 0xF7]


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


def build_program_write(channel: int, data: bytes) -> list[int]:
    # TODO: verify write format against Parameter Guide before device testing
    return ([0xF0, KORG_ID, _channel_byte(channel), *MODEL_ID,
             FUNC_PROGRAM_DUMP]
            + list(data) + [0xF7])
