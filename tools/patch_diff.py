#!/usr/bin/env python3
"""Diff two .rk100s2_prog patch files with section-aware labeling.

Shows which bytes changed, their section/logical offset, and packed SysEx position.
Useful for empirically discovering SysEx byte offsets for parameters.

Usage:
    python tools/patch_diff.py <before.rk100s2_prog> <after.rk100s2_prog>
    python tools/patch_diff.py --all /tmp/*.rk100s2_prog   # Diff consecutive pairs

The tool maps file byte positions → packed SysEx positions → section/logical offsets,
making it easy to identify which parameter changed.
"""

from __future__ import annotations
import math
import sys
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.file_format import (
    FILE_HEADER_SIZE, PROGRAM_DATA_SIZE, read_patch,
    pack_offset, packed_to_file, file_to_packed, packed_to_section,
)


def build_reverse_map() -> dict[int, tuple[str, int]]:
    """Build packed_position → (section_name, logical_offset) map."""
    rev = {}
    for i in range(18):
        rev[i] = ("Common", i)

    sections = [
        ("Timbre1", 18, 3, 96),
        ("Timbre2", 128, 1, 96),
        ("VocBands", 237, 6, 42),
        ("Gap", 283, 4, 88),
        ("Arp", 384, 1, 24),
    ]

    for name, base, k, count in sections:
        for L in range(count):
            pk = pack_offset(L, base, k)
            rev[pk] = (name, L)
        # HB bytes
        for pos in range(base, base + count + count // 7 + 2):
            if pos not in rev:
                rel = pos - base
                if rel >= 0 and rel % 8 == 0:
                    rev[pos] = (f"{name}_HB", rel // 8)

    # Mark positions beyond arp as "Extra" (checksum/padding)
    last_arp = pack_offset(23, 384, 1)  # = 411
    for pos in range(last_arp + 1, 500):
        if pos not in rev:
            rev[pos] = ("Extra", pos - last_arp - 1)

    return rev


# Known param names at specific logical offsets (for labeling)
KNOWN_PARAMS = {
    ("Common", 8): "voice_mode/HB",
    ("Common", 10): "arp_select",
    ("Timbre1", 91): "long_ribbon_filter_int",
    ("Timbre2", 91): "long_ribbon_filter_int",
    ("Gap", 0): "fx1_type",
    ("Gap", 2): "vocoder_fc_offset",
    ("Gap", 3): "vocoder_resonance",
    ("Gap", 4): "vocoder_fc_mod_int",
    ("Gap", 5): "vocoder_ef_sens",
    ("Gap", 24): "fx2_sw_type",
    ("Gap", 51): "???_gap51",
    ("Arp", 0): "arp_resolution",
    ("Arp", 1): "arp_last_step",
    ("Arp", 2): "arp_type",
    ("Arp", 4): "arp_gate",
    ("Arp", 5): "arp_swing",
    ("Arp", 6): "arp_step_switches",
    ("Arp", 10): "short_ribbon_mod_assign",
    ("Arp", 11): "short_ribbon_setting",
    ("Arp", 12): "scale",
    ("Arp", 13): "long_ribbon_scale_range",
    ("Arp", 14): "long_ribbon_pitch_range",
}


def diff_patches(a: bytes, b: bytes, label: str = "") -> list[tuple[int, int, int]]:
    """Diff two patch data buffers and print results with section labeling."""
    rev = build_reverse_map()

    diffs = []
    for file_pos in range(min(len(a), len(b))):
        if a[file_pos] != b[file_pos]:
            diffs.append((file_pos, a[file_pos], b[file_pos]))

    if label:
        print(f"\n{'=' * 75}")
        print(f"  {label}")
        print(f"{'=' * 75}")

    if not diffs:
        print("  No differences found.")
        return diffs

    # Separate meaningful changes from checksum/extra area
    # Extra region starts after last arp byte (packed 411+)
    last_arp = pack_offset(23, 384, 1)  # = 411
    last_arp_file = packed_to_file(last_arp)
    checksum_packed = set()
    for pk in range(last_arp + 1, 500):
        checksum_packed.add(pk)

    meaningful = []
    checksums = []
    for file_pos, old, new in diffs:
        packed = file_to_packed(file_pos)
        if packed in checksum_packed:
            checksums.append((file_pos, old, new))
        else:
            meaningful.append((file_pos, old, new))

    print(f"  Total diffs: {len(diffs)}, meaningful: {len(meaningful)}, "
          f"checksums: {len(checksums)}")
    print()

    if meaningful:
        print(f"  {'File':>5} {'Packed':>6} {'Section':>10} {'L#':>4}  "
              f"{'Old':>4} → {'New':>4}  {'Bits':>19}  Param")
        print(f"  {'-' * 70}")

        for file_pos, old, new in meaningful:
            packed = file_to_packed(file_pos)
            section, logical = rev.get(packed, ("???", packed))
            param_name = KNOWN_PARAMS.get((section, logical), "")

            print(f"  {file_pos:>5} {packed:>6} {section:>10} L{logical:<3d} "
                  f"{old:>4} → {new:>4}  "
                  f"{old:08b}→{new:08b}  {param_name}")

    if checksums:
        print(f"\n  ({len(checksums)} checksum byte changes omitted)")

    return diffs


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Diff consecutive pairs
        files = sorted(Path(f) for f in sys.argv[2:] if f.endswith('.rk100s2_prog'))
        patches = []
        for f in files:
            try:
                patches.append((f.stem, read_patch(f)))
            except (ValueError, FileNotFoundError) as e:
                print(f"Skipping {f}: {e}")

        for i in range(len(patches) - 1):
            name_a, data_a = patches[i]
            name_b, data_b = patches[i + 1]
            diff_patches(data_a, data_b, f"{name_a} → {name_b}")
    else:
        path_a = Path(sys.argv[1])
        path_b = Path(sys.argv[2])
        data_a = read_patch(path_a)
        data_b = read_patch(path_b)
        diff_patches(data_a, data_b, f"{path_a.stem} → {path_b.stem}")


if __name__ == "__main__":
    main()
