"""Tests for tools/file_format.py conversion functions."""
from pathlib import Path
import pytest
from tools.file_format import (
    sysex_to_prog_bytes, prog_file_to_sysex, read_patch,
    FILE_HEADER_SIZE, PROGRAM_DATA_SIZE,
)


PATCH_DIR = Path(__file__).parent.parent.parent / "patches"


def _have_patches() -> bool:
    return PATCH_DIR.exists() and any(PATCH_DIR.glob("*.rk100s2_prog"))


@pytest.mark.skipif(not _have_patches(), reason="No patch files in patches/")
@pytest.mark.parametrize("name", [
    "arpon", "arpon_octave2", "arpon_octave3", "arpon_octave4",
    "fx_compressor", "fx_off",
])
def test_round_trip_file_to_sysex_to_file(name):
    path = PATCH_DIR / f"{name}.rk100s2_prog"
    if not path.exists():
        pytest.skip(f"{path} not found")
    original = path.read_bytes()
    file_data = read_patch(path)
    sysex = prog_file_to_sysex(file_data)
    rebuilt = sysex_to_prog_bytes(sysex)
    assert rebuilt == original


def test_sysex_to_prog_bytes_size():
    sysex = bytes(496)
    result = sysex_to_prog_bytes(sysex)
    assert len(result) == FILE_HEADER_SIZE + PROGRAM_DATA_SIZE


def test_sysex_to_prog_bytes_header():
    sysex = bytes(496)
    result = sysex_to_prog_bytes(sysex)
    assert result[:8] == b"12100PgD"


def test_sysex_to_prog_bytes_ff_padding():
    sysex = bytes(496)
    result = sysex_to_prog_bytes(sysex)
    file_data = result[FILE_HEADER_SIZE:]
    assert all(b == 0xFF for b in file_data[474:])


def test_sysex_to_prog_bytes_too_short():
    with pytest.raises(ValueError, match="too short"):
        sysex_to_prog_bytes(bytes(100))


def test_prog_file_to_sysex_too_short():
    with pytest.raises(ValueError, match="too short"):
        prog_file_to_sysex(bytes(100))


def test_prog_file_to_sysex_hb_bytes_are_zero():
    file_data = bytes(496)
    sysex = prog_file_to_sysex(file_data)
    for p in range(18, 496):
        if p % 8 == 0:
            assert sysex[p] == 0, f"HB byte at packed {p} should be 0"
