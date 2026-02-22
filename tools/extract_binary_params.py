#!/usr/bin/env python3
"""Extract ALL parameter definitions from the Korg Sound Editor binary.

The param definition table uses 0xFFFFFFFF boundary markers between entries.
Entry layout (from boundary):
  +0:  0xFFFFFFFF (boundary)
  +4:  internal name ptr (of PREVIOUS entry)
  +8:  display name ptr (THIS entry)
  +12: section indicator (0=common?, 1=timbre?)
  +16: logical byte offset within section
  +20: bit position or sub-field info
  +24: max value or value count
  +28: signed min?
  +32: display max / UI range
  +36: display offset
  +40: ??? (usually 1)
  +44: ??? (usually 1 or 3)

Next boundary at +48 or later (variable stride for some entries).
"""

import struct
import json
import math
from pathlib import Path
from collections import defaultdict, OrderedDict

BINARY_PATH = "/tmp/RK100S 2 Sound Editor.exe"
NRPN_OFFSETS_PATH = Path.home() / ".config" / "patchmasta" / "offsets.json"
IMAGE_BASE = 0x00400000
RDATA_VA = 0x113000
RDATA_RAW = 0x112400


def read_binary():
    with open(BINARY_PATH, "rb") as f:
        return f.read()


def va_to_file(va):
    rva = va - IMAGE_BASE
    if rva >= RDATA_VA:
        return rva - RDATA_VA + RDATA_RAW
    return rva


def read_string_at(data, offset, max_len=200):
    if offset < 0 or offset >= len(data):
        return None
    end = data.find(b'\x00', offset, offset + max_len)
    if end == -1:
        return None
    try:
        s = data[offset:end].decode('ascii')
        if all(0x20 <= ord(c) < 0x7f for c in s):
            return s
        return None
    except (UnicodeDecodeError, ValueError):
        return None


def resolve_string(data, va):
    if va < IMAGE_BASE or va > IMAGE_BASE + len(data):
        return None
    fo = va_to_file(va)
    return read_string_at(data, fo)


def find_all_boundaries(data, start, end):
    """Find all 0xFFFFFFFF-aligned DWORDs in the given range."""
    boundaries = []
    for off in range(start, end, 4):
        val = struct.unpack_from('<I', data, off)[0]
        if val == 0xFFFFFFFF:
            # Verify this looks like a param entry boundary:
            # +4 should be a string ptr or small int (internal name of prev)
            # +8 should be a string ptr (display name)
            if off + 12 <= len(data):
                display_va = struct.unpack_from('<I', data, off + 8)[0]
                display_name = resolve_string(data, display_va)
                if display_name and len(display_name) >= 3:
                    boundaries.append(off)
    return boundaries


def extract_entry(data, boundary_off, next_boundary_off=None):
    """Extract one param entry starting from its 0xFFFFFFFF boundary."""
    if next_boundary_off is None:
        next_boundary_off = boundary_off + 48  # default

    entry_size = next_boundary_off - boundary_off
    num_fields = entry_size // 4

    fields = []
    for i in range(min(num_fields, 20)):
        off = boundary_off + i * 4
        if off + 4 > len(data):
            break
        fields.append(struct.unpack_from('<I', data, off)[0])

    # f0: 0xFFFFFFFF
    # f1: internal name of PREVIOUS entry (string ptr or small int)
    # f2: display name of THIS entry (string ptr)
    # f3: section
    # f4: logical byte offset
    # f5+: metadata

    prev_internal = resolve_string(data, fields[1]) if len(fields) > 1 else None
    display_name = resolve_string(data, fields[2]) if len(fields) > 2 else None
    section = fields[3] if len(fields) > 3 else None
    byte_offset = fields[4] if len(fields) > 4 else None

    # The internal name for THIS entry is at the f1 position of the NEXT entry
    # We'll resolve that later

    return {
        'boundary_off': boundary_off,
        'entry_size': entry_size,
        'display_name': display_name,
        'prev_internal_name': prev_internal,
        'section': section,
        'byte_offset': byte_offset,
        'f5': fields[5] if len(fields) > 5 else None,
        'f6': fields[6] if len(fields) > 6 else None,
        'f7': fields[7] if len(fields) > 7 else None,
        'f8': fields[8] if len(fields) > 8 else None,
        'fields': fields,
    }


def pack_offset(logical, base, k=3):
    """physical = base + logical + ceil((logical + k) / 7)"""
    return base + logical + math.ceil((logical + k) / 7)


def main():
    data = read_binary()
    nrpn_offsets = json.loads(NRPN_OFFSETS_PATH.read_text())

    # Scan the entire region from 0x11E000 to 0x130000 for param tables
    scan_start = 0x11E000
    scan_end = 0x130000

    print(f"Scanning for param entry boundaries in 0x{scan_start:X}-0x{scan_end:X}...")
    boundaries = find_all_boundaries(data, scan_start, scan_end)
    print(f"Found {len(boundaries)} boundary markers")

    # Extract entries from consecutive boundaries
    entries = []
    for i, bnd in enumerate(boundaries):
        next_bnd = boundaries[i + 1] if i + 1 < len(boundaries) else bnd + 48
        entry = extract_entry(data, bnd, next_bnd)
        if entry['display_name']:
            entries.append(entry)

    print(f"Extracted {len(entries)} entries with display names")

    # Fix internal names: entry[i]'s internal name is at entry[i+1].prev_internal_name
    for i in range(len(entries) - 1):
        entries[i]['internal_name'] = entries[i + 1]['prev_internal_name']
    if entries:
        # Last entry's internal name we can try to resolve from boundary + stride
        last = entries[-1]
        last_bnd = last['boundary_off']
        # Look at the DWORD right after this entry's fields (at the next boundary - 4? no)
        # The internal name would be at the start of the NEXT entry's f1 field
        # We'll just leave it as None
        entries[-1]['internal_name'] = None

    # Print all entries grouped by section
    print(f"\n{'='*70}")
    print("ALL EXTRACTED PARAMETERS")
    print(f"{'='*70}")

    by_section = defaultdict(list)
    for e in entries:
        by_section[e['section']].append(e)

    for sec in sorted(by_section.keys()):
        elist = by_section[sec]
        print(f"\n--- Section {sec} ({len(elist)} params) ---")
        for e in elist:
            iname = e.get('internal_name', '?')
            size_note = f" [size={e['entry_size']}]" if e['entry_size'] != 48 else ""
            print(f"  off={e['byte_offset']:3d}  {e['display_name']:40s}  internal={iname}{size_note}")

    # Now validate against NRPN offsets
    # First, build the NRPN name → display name mapping
    print(f"\n{'='*70}")
    print("PACKING FORMULA VALIDATION")
    print(f"{'='*70}")

    # Known mapping from our params.py names to display names in the binary
    # We need to match NRPN param names to extracted display names
    # Focus on timbre section (section 1) params with known NRPN offsets

    # Build lookup: display_name → entry
    display_lookup = {}
    for e in entries:
        key = e['display_name']
        if key not in display_lookup:
            display_lookup[key] = e

    # Try to match known params
    nrpn_matches = {
        'patch1_source': ('Patch 1 Source', 'Patch 1 Src'),
        'patch1_dest': ('Patch 1 Dest', 'Patch 1 Destination'),
        'patch2_source': ('Patch 2 Source', 'Patch 2 Src'),
        'patch2_dest': ('Patch 2 Dest', 'Patch 2 Destination'),
        'patch3_source': ('Patch 3 Source', 'Patch 3 Src'),
        'patch3_dest': ('Patch 3 Dest', 'Patch 3 Destination'),
        'patch4_source': ('Patch 4 Source', 'Patch 4 Src'),
        'patch4_dest': ('Patch 4 Dest', 'Patch 4 Destination'),
        'patch5_source': ('Patch 5 Source', 'Patch 5 Src'),
        'patch5_dest': ('Patch 5 Dest', 'Patch 5 Destination'),
        'voice_mode': ('Voice Mode',),
    }

    # Find all "Patch" entries for debugging
    patch_entries = [e for e in entries if 'Patch' in (e['display_name'] or '')]
    print("\nAll 'Patch' entries found:")
    for e in patch_entries:
        print(f"  sec={e['section']} off={e['byte_offset']}  {e['display_name']:30s}  internal={e.get('internal_name')}")

    # Find all virtual patch related entries
    vp_entries = [e for e in entries if 'Virtual' in (e['display_name'] or '') or 'Patch ' in (e['display_name'] or '')]
    print("\nAll Virtual Patch entries found:")
    for e in vp_entries:
        print(f"  sec={e['section']} off={e['byte_offset']}  {e['display_name']:30s}  internal={e.get('internal_name')}")

    # Now try formula validation for section 1 (timbre) params
    print(f"\n--- Testing packing formula for section 1 (timbre) params ---")
    print("Formula: physical = base + logical + ceil((logical + k) / 7)")

    # Use the known working formula: base=18, k=3
    base, k = 18, 3
    print(f"\nUsing base={base}, k={k}:")

    for nrpn_name, physical in sorted(nrpn_offsets.items()):
        # Try to find matching entry
        for display_candidates in nrpn_matches.get(nrpn_name, ()):
            if display_candidates in display_lookup:
                e = display_lookup[display_candidates]
                if e['section'] == 1:
                    computed = pack_offset(e['byte_offset'], base, k)
                    match = '✓' if computed == physical else '✗'
                    print(f"  {match} {nrpn_name:25s} logical={e['byte_offset']:3d} → computed={computed:3d} expected={physical:3d}")
                break

    # Also print computed offsets for ALL section 1 params
    print(f"\n{'='*70}")
    print("COMPUTED PHYSICAL OFFSETS FOR ALL TIMBRE PARAMS (section 1)")
    print(f"{'='*70}")

    timbre_params = sorted(
        [e for e in entries if e['section'] == 1],
        key=lambda e: e['byte_offset']
    )

    for e in timbre_params:
        physical = pack_offset(e['byte_offset'], base, k)
        iname = e.get('internal_name', '?')
        print(f"  logical={e['byte_offset']:3d} → physical={physical:3d}  {e['display_name']:40s}  internal={iname}")

    # Also handle section 0 params
    print(f"\n{'='*70}")
    print("SECTION 0 (common/global) PARAMS")
    print(f"{'='*70}")

    common_params = sorted(
        [e for e in entries if e['section'] == 0],
        key=lambda e: e['byte_offset']
    )

    for e in common_params:
        iname = e.get('internal_name', '?')
        print(f"  offset={e['byte_offset']:3d}  {e['display_name']:40s}  internal={iname}")

    # Generate the complete offset map
    print(f"\n{'='*70}")
    print("GENERATING COMPLETE OFFSET MAP")
    print(f"{'='*70}")

    offset_map = OrderedDict()

    # Section 0: direct mapping (no packing), voice_mode at physical 8 = logical 8
    for e in common_params:
        name = e.get('internal_name') or e['display_name']
        if name and name != '?':
            # Check if direct mapping works for known params
            offset_map[f"common_{name}"] = e['byte_offset']

    # Section 1: use packing formula base=18, k=3
    for e in timbre_params:
        name = e.get('internal_name') or e['display_name']
        if name and name != '?':
            physical = pack_offset(e['byte_offset'], base, k)
            offset_map[f"timbre1_{name}"] = physical

    print(f"Total params mapped: {len(offset_map)}")
    print(json.dumps(offset_map, indent=2))


if __name__ == "__main__":
    main()
