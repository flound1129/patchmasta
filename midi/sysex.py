from __future__ import annotations

KORG_ID = 0x42
MODEL_ID = 0x57  # TODO: verify against Parameter Guide

FUNC_PROGRAM_DUMP_REQUEST = 0x10
FUNC_ALL_DUMP_REQUEST = 0x0E
FUNC_PROGRAM_DUMP = 0x40
FUNC_ALL_DUMP = 0x4E


def _channel_byte(channel: int) -> int:
    return 0x30 + (channel - 1)


def build_program_dump_request(channel: int, program: int) -> list[int]:
    return [0xF0, KORG_ID, _channel_byte(channel), MODEL_ID,
            FUNC_PROGRAM_DUMP_REQUEST, program & 0x7F, 0xF7]


def build_all_dump_request(channel: int) -> list[int]:
    return [0xF0, KORG_ID, _channel_byte(channel), MODEL_ID,
            FUNC_ALL_DUMP_REQUEST, 0xF7]


def parse_program_dump(message: list[int]) -> bytes | None:
    if len(message) < 6:
        return None
    if message[0] != 0xF0 or message[1] != KORG_ID:
        return None
    if message[3] != MODEL_ID or message[4] != FUNC_PROGRAM_DUMP:
        return None
    return bytes(message[5:-1])


def build_program_write(channel: int, program: int, data: bytes) -> list[int]:
    return ([0xF0, KORG_ID, _channel_byte(channel), MODEL_ID,
             FUNC_PROGRAM_DUMP, program & 0x7F]
            + list(data) + [0xF7])
