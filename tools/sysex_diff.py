#!/usr/bin/env python3
"""Utility to diff two RK-100S 2 SysEx program dumps.

Usage:
    python tools/sysex_diff.py dump_before.syx dump_after.syx

Reads two raw .syx files (or parsed program-data files), compares byte by
byte, and prints which offsets changed and their old/new values.  Useful for
empirically discovering which byte offset corresponds to a given parameter.
"""

from __future__ import annotations
import sys
from pathlib import Path


def load_syx(path: Path) -> bytes:
    data = path.read_bytes()
    # If it's a full SysEx message, strip the wrapper:
    # F0 42 3n 00 01 22 40 [data] F7
    if data and data[0] == 0xF0 and data[-1] == 0xF7:
        # Find FUNC_PROGRAM_DUMP (0x40) after model ID
        for i in range(6, min(10, len(data))):
            if data[i] == 0x40:
                return data[i + 1:-1]
    return data


def diff_dumps(before: bytes, after: bytes) -> list[tuple[int, int, int]]:
    """Return list of (offset, old_value, new_value) for differing bytes."""
    diffs = []
    max_len = max(len(before), len(after))
    for i in range(max_len):
        b = before[i] if i < len(before) else None
        a = after[i] if i < len(after) else None
        if b != a:
            diffs.append((i, b, a))
    return diffs


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    path_before = Path(sys.argv[1])
    path_after = Path(sys.argv[2])

    if not path_before.exists():
        print(f"File not found: {path_before}")
        sys.exit(1)
    if not path_after.exists():
        print(f"File not found: {path_after}")
        sys.exit(1)

    before = load_syx(path_before)
    after = load_syx(path_after)

    print(f"Before: {len(before)} bytes  ({path_before.name})")
    print(f"After:  {len(after)} bytes  ({path_after.name})")
    print()

    diffs = diff_dumps(before, after)
    if not diffs:
        print("No differences found.")
        return

    print(f"Found {len(diffs)} difference(s):")
    print(f"{'Offset':>8}  {'Dec':>5}  {'Before':>8}  {'After':>8}  {'Signed Before':>14}  {'Signed After':>13}")
    print("-" * 70)
    for offset, old, new in diffs:
        old_str = f"0x{old:02X} ({old:3d})" if old is not None else "  (none)  "
        new_str = f"0x{new:02X} ({new:3d})" if new is not None else "  (none)  "
        # Also show signed interpretation
        old_signed = (old - 128) if old is not None and old >= 64 else old
        new_signed = (new - 128) if new is not None and new >= 64 else new
        old_s = str(old_signed) if old_signed is not None else "-"
        new_s = str(new_signed) if new_signed is not None else "-"
        print(f"{offset:>8}  {offset:>5}  {old_str}  {new_str}  {old_s:>14}  {new_s:>13}")


if __name__ == "__main__":
    main()
