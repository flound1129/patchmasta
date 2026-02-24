#!/usr/bin/env python3
"""RK-100S 2 .rk100s2_prog file format analysis and offset conversion.

File format (528 bytes total):
  - 32-byte file header: magic "12100PgD" + metadata
  - 496 bytes program data

Program data layout:
  - Bytes 0-17:  Common header (stored at packed SysEx positions, including HB bytes)
    - 0-7:   Patch name (8 ASCII characters)
    - 8:     Constant 7 (format metadata? unknown purpose)
    - 9:     Voice mode related (0=piano patches, 3=vocoder patches)
    - 10:    arp_select (NRPN-validated at packed position 10)
    - 11-17: Other common params
  - Bytes 16+: Section data (stored at global unpacked positions, HB bytes stripped)

Packed SysEx format (device communication):
  Global packing: packed = (unpacked // 7) * 8 + (unpacked % 7) + 1
  HB bytes at every packed position where packed % 8 == 0 (0, 8, 16, 24, ...)

  Section layout in packed format:
    Common:     bytes 0-17   (18 bytes, direct mapping)
    Timbre 1:   base=18, k=3  (96 logical bytes, packed 19-127)
    Timbre 2:   base=128, k=1 (96 logical bytes, packed 129-237)
    Voc Bands:  base=237, k=6 (42 logical bytes, packed 238-285)
    Gap (FX):   base=283, k=4 (88 logical bytes, packed 284-383)
    Arp:        base=384, k=1 (24 logical bytes, packed 385-411)

File position conversion (verified against 9 diff-confirmed params):
  For common params (packed 0-17):  file_pos = packed (direct)
  For data params (packed >= 18):   file_pos = (packed // 8) * 7 + (packed % 8) - 1

Usage:
    python tools/file_format.py <patch_file.rk100s2_prog>   # Analyze a patch file
    python tools/file_format.py --convert <packed_offset>    # Convert packed → file offset
"""

from __future__ import annotations
import math
import sys
from pathlib import Path


FILE_HEADER_SIZE = 32
PROGRAM_DATA_SIZE = 496
FILE_MAGIC = b"12100PgD"

# Section definitions: (name, packed_base, k_value, logical_count)
SECTIONS = [
    ("Common", 0, None, 18),       # Direct mapping, no packing formula
    ("Timbre1", 18, 3, 96),
    ("Timbre2", 128, 1, 96),
    ("VocBands", 237, 6, 42),
    ("Gap", 283, 4, 88),
    ("Arp", 384, 1, 24),
]


def pack_offset(logical: int, base: int, k: int) -> int:
    """Compute packed SysEx position from section logical offset."""
    return base + logical + math.ceil((logical + k) / 7)


def packed_to_file(packed: int) -> int | None:
    """Convert packed SysEx position to .rk100s2_prog file position.

    Returns None for HB byte positions (no file equivalent in data section).
    """
    if packed < 18:
        return packed  # Common header: direct mapping
    if packed % 8 == 0:
        return None  # HB byte in global packing, no direct file equivalent
    return (packed // 8) * 7 + (packed % 8) - 1


def file_to_packed(file_pos: int) -> int:
    """Convert .rk100s2_prog file position to packed SysEx position.

    For common header (file_pos < 18): returns file_pos directly.
    For data section: applies inverse of global unpacking formula.
    """
    if file_pos < 18:
        return file_pos  # Common header: direct mapping
    # Inverse of: file = (packed // 8) * 7 + (packed % 8) - 1
    # = (u // 7) * 8 + (u % 7) + 1  where u = file_pos
    group = file_pos // 7
    pos = file_pos % 7
    return group * 8 + pos + 1


def packed_to_section(packed: int) -> tuple[str, int]:
    """Identify which section and logical offset a packed position belongs to.

    Returns (section_name, logical_offset) or ("Unknown", packed_offset).
    """
    if packed < 18:
        return ("Common", packed)

    # Build reverse map for each section
    for name, base, k, count in SECTIONS:
        if name == "Common":
            continue
        for L in range(count):
            pk = pack_offset(L, base, k)
            if pk == packed:
                return (name, L)

        # Check if this is an HB byte in this section
        # HB bytes are at positions where (pos - base) maps to group boundaries
        if base <= packed:
            rel = packed - base
            if rel >= 0 and rel // 8 <= count // 7 + 1:
                if rel % 8 == 0 or (rel == 0 and k > 0):
                    # Could be an HB byte for this section
                    pass  # Continue checking other sections

    return ("Unknown", packed)


def read_patch(path: Path) -> bytes:
    """Read program data from a .rk100s2_prog file (strips 32-byte header)."""
    data = path.read_bytes()
    if len(data) < FILE_HEADER_SIZE + PROGRAM_DATA_SIZE:
        raise ValueError(f"File too small: {len(data)} bytes "
                         f"(expected {FILE_HEADER_SIZE + PROGRAM_DATA_SIZE})")
    header = data[:FILE_HEADER_SIZE]
    if not header.startswith(FILE_MAGIC):
        raise ValueError(f"Bad magic: {header[:8]!r} (expected {FILE_MAGIC!r})")
    return data[FILE_HEADER_SIZE:FILE_HEADER_SIZE + PROGRAM_DATA_SIZE]


_FILE_HEADER = bytes.fromhex(
    "31323130305067442000f001000001000300000001000000f0010000ffffffff"
)
_FF_PAD_START = 474


def sysex_to_prog_bytes(sysex: bytes) -> bytes:
    """Convert packed SysEx buffer data to a complete .rk100s2_prog file.

    *sysex* is the 496-byte packed SysEx payload (as stored in
    ``SysExProgramBuffer``).  Returns 528 bytes ready to write to disk.
    """
    if len(sysex) < PROGRAM_DATA_SIZE:
        raise ValueError(f"SysEx data too short: {len(sysex)} bytes "
                         f"(need {PROGRAM_DATA_SIZE})")
    file_data = bytearray(PROGRAM_DATA_SIZE)
    # Common header: direct mapping (positions 0-17)
    for p in range(18):
        file_data[p] = sysex[p]
    # Data section: skip HB bytes, map to file positions
    for p in range(18, min(len(sysex), PROGRAM_DATA_SIZE)):
        if p % 8 != 0:
            fp = packed_to_file(p)
            if fp is not None and fp < PROGRAM_DATA_SIZE:
                file_data[fp] = sysex[p]
    # Fixed 0xFF padding at end
    for i in range(_FF_PAD_START, PROGRAM_DATA_SIZE):
        file_data[i] = 0xFF
    return bytes(_FILE_HEADER) + bytes(file_data)


def prog_file_to_sysex(file_data: bytes) -> bytes:
    """Convert 496-byte .rk100s2_prog program data to packed SysEx format.

    *file_data* is the 496 bytes after the 32-byte header (as returned by
    ``read_patch``).  Returns 496 bytes suitable for ``SysExProgramBuffer.load``.
    """
    if len(file_data) < PROGRAM_DATA_SIZE:
        raise ValueError(f"File data too short: {len(file_data)} bytes "
                         f"(need {PROGRAM_DATA_SIZE})")
    sysex = bytearray(PROGRAM_DATA_SIZE)
    # Common header: direct mapping
    for p in range(18):
        sysex[p] = file_data[p]
    # Data section: fill non-HB positions from file positions
    for p in range(18, PROGRAM_DATA_SIZE):
        if p % 8 == 0:
            sysex[p] = 0  # HB byte
        else:
            fp = packed_to_file(p)
            if fp is not None and fp < len(file_data):
                sysex[p] = file_data[fp]
    return bytes(sysex)


def analyze_patch(data: bytes) -> None:
    """Print a structured analysis of patch data."""
    # Name
    name = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[0:8])
    print(f"Name: {name}")

    # Common header
    print(f"\nCommon header (bytes 0-17):")
    for i in range(18):
        v = data[i]
        ascii_str = f" '{chr(v)}'" if 32 <= v < 127 else ""
        print(f"  [{i:2d}] = {v:3d} (0x{v:02X}){ascii_str}")

    # Section summaries
    print(f"\nSection data ranges (file positions):")
    for sec_name, base, k, count in SECTIONS:
        if sec_name == "Common":
            print(f"  {sec_name:10s}: file[0:18] (packed 0-17)")
            continue
        first_pk = pack_offset(0, base, k)
        last_pk = pack_offset(count - 1, base, k)
        first_fp = packed_to_file(first_pk)
        last_fp = packed_to_file(last_pk)
        print(f"  {sec_name:10s}: file[{first_fp}:{last_fp + 1}] "
              f"(packed {first_pk}-{last_pk}, {count} logical bytes)")

    # Check for non-zero data in arp section
    arp_start = packed_to_file(pack_offset(0, 384, 1))
    arp_end = packed_to_file(pack_offset(23, 384, 1))
    arp_data = data[arp_start:arp_end + 1]
    arp_nonzero = sum(1 for b in arp_data if b != 0)
    print(f"\n  Arp section: {arp_nonzero}/{len(arp_data)} non-zero bytes")

    # Extra region (beyond arp)
    extra_start = arp_end + 1
    extra_data = data[extra_start:]
    extra_nonzero = sum(1 for b in extra_data if b != 0)
    print(f"  Extra region [{extra_start}:{len(data)}]: "
          f"{extra_nonzero}/{len(extra_data)} non-zero bytes")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--convert":
        if len(sys.argv) != 3:
            print("Usage: --convert <packed_offset>")
            sys.exit(1)
        packed = int(sys.argv[2])
        fp = packed_to_file(packed)
        section, logical = packed_to_section(packed)
        if fp is None:
            print(f"Packed {packed} is an HB byte (no file equivalent)")
        else:
            print(f"Packed {packed} → file[{fp}] ({section} L{logical})")
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    data = read_patch(path)
    analyze_patch(data)


if __name__ == "__main__":
    main()
