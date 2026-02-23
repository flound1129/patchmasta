#!/usr/bin/env python3
"""Decode remaining params from piano2→piano3 diff.

Changes:
  - long_ribbon_scale_key → C# (1)
  - long_ribbon_timbre_select → Timbre 1+2 (2)
  - long_ribbon_scale_type → Chromatic (0, was Arabic=3?)
  - arp_key_sync → off (0, was on=1)
  - all arp steps → off
  - fx1 ribbon assign → flanger
  - fx2 ribbon assign → chorus

Key arp section bytes that changed:
  Arp L0  (pk385): 192→128  (0b11000000→0b10000000) bit6: 1→0 = arp_key_sync?
  Arp L6  (pk391): 255→0    (all steps off) CONFIRMED
  Arp L11 (pk397): 157→163  short_ribbon_setting
  Arp L12 (pk398): 20→129   scale (combined?)

Let's look at Arp L11 and L12 across all patches to decode bit packing.
"""
import sys
sys.path.insert(0, '.')
from tools.file_format import read_patch, packed_to_file, pack_offset
from pathlib import Path

patches = {}
for name in ["piano", "piano_changed", "piano2", "piano3", "piano4",
             "robotvoc", "robotvoc2", "robotvoc3"]:
    try:
        patches[name] = read_patch(Path(f'/tmp/{name}.rk100s2_prog'))
    except (FileNotFoundError, ValueError):
        pass

# Key arp section bytes
arp_bytes = {
    "Arp L0 (pk385)": packed_to_file(385),   # arp_resolution + arp_on_off(bit7)
    "Arp L1 (pk386)": packed_to_file(386),   # arp_last_step
    "Arp L2 (pk387)": packed_to_file(387),   # arp_type
    "Arp L3 (pk388)": packed_to_file(388),   # ?
    "Arp L4 (pk389)": packed_to_file(389),   # arp_gate
    "Arp L5 (pk390)": packed_to_file(390),   # arp_swing
    "Arp L6 (pk391)": packed_to_file(391),   # step_switches
    "Arp L7 (pk393)": packed_to_file(393),   # ?
    "Arp L8 (pk394)": packed_to_file(394),   # ?
    "Arp L9 (pk395)": packed_to_file(395),   # ?
    "Arp L10 (pk396)": packed_to_file(396),  # short_ribbon_mod_assign
    "Arp L11 (pk397)": packed_to_file(397),  # short_ribbon_setting
    "Arp L12 (pk398)": packed_to_file(398),  # scale
    "Arp L13 (pk399)": packed_to_file(399),  # long_ribbon_scale_range
    "Arp L14 (pk401)": packed_to_file(401),  # long_ribbon_pitch_range
}

print("Arp section bytes across all patches:")
print(f"{'Byte':<20}", end="")
for name in patches:
    print(f" {name:>14}", end="")
print()

for label, fp in arp_bytes.items():
    print(f"{label:<20}", end="")
    for name, d in patches.items():
        v = d[fp]
        print(f" {v:>4} {v:08b}", end="")
    print()

# Focus on Arp L0 (arp_resolution + arp_on_off + maybe arp_key_sync)
print("\n\nArp L0 bit analysis:")
print("  bit7 = arp_on_off (from HB[384] bit 0)")
print("  bit6 = arp_key_sync? (changes 1→0 in piano2→piano3)")
print("  bits0-5 = arp_resolution?")
for name, d in patches.items():
    v = d[packed_to_file(385)]
    on = (v >> 7) & 1
    bit6 = (v >> 6) & 1
    lower = v & 0x3F
    print(f"  {name:>14}: val={v:3d} bit7(on)={on} bit6(keysync?)={bit6} bits0-5(res?)={lower}")

# Focus on Arp L12 (scale): decode across patches
# piano: 1 (default, Equal Temp + C?)
# piano_changed: 20 (Arabic + some key)
# piano3: 129 (Chromatic + C#?)
print("\n\nArp L12 (scale) bit analysis:")
print("  bit7 = HB[392] bit 5 (MSB)")
print("  bits0-6 = scale data")
for name, d in patches.items():
    v = d[packed_to_file(398)]
    msb = (v >> 7) & 1
    data = v & 0x7F
    # Try: lower bits = scale_type, upper bits = scale_key
    # scale_type: 0-9 (needs 4 bits), scale_key: 0-11 (needs 4 bits)
    type_lo4 = data & 0xF
    key_hi3 = (data >> 4) & 0x7
    # Or: scale_key in lower 4 bits, scale_type in upper bits
    key_lo4 = data & 0xF
    type_hi3 = (data >> 4) & 0x7
    print(f"  {name:>14}: val={v:3d} (0b{v:08b}) msb={msb} data={data:3d} "
          f"lo4={type_lo4:2d} hi3={key_hi3} | key_lo4={key_lo4:2d} type_hi3={type_hi3}")

# Focus on Arp L11 (short_ribbon_setting): decode bit changes
# piano2: 157 (0b10011101), piano3: 163 (0b10100011)
print("\n\nArp L11 (short_ribbon_setting) bit analysis:")
for name, d in patches.items():
    v = d[packed_to_file(397)]
    msb = (v >> 7) & 1
    data = v & 0x7F
    print(f"  {name:>14}: val={v:3d} (0b{v:08b}) msb={msb} data7={data:3d} (0b{data:07b})")

# Gap section: FX ribbon assigns
# FX1 area: Gap L0-L23, FX2: Gap L24-L47
# Let's check which bytes differ between piano_changed (no ribbon FX) and piano3 (flanger/chorus)
print("\n\nGap section FX1 area (L0-L23) across patches:")
for L in range(24):
    pk = pack_offset(L, 283, 4)
    fp = packed_to_file(pk)
    if fp is None:
        continue
    vals = [patches[n][fp] for n in ["piano", "piano_changed", "piano2", "piano3"]]
    if len(set(vals)) > 1:  # Only show bytes that differ
        print(f"  Gap L{L:2d} (pk{pk:3d}, file{fp:3d}): "
              + "  ".join(f"{n}={v:3d}" for n, v in zip(
                  ["piano", "piano_changed", "piano2", "piano3"], vals)))

print("\n\nGap section FX2 area (L24-L47) across patches:")
for L in range(24, 48):
    pk = pack_offset(L, 283, 4)
    fp = packed_to_file(pk)
    if fp is None:
        continue
    vals = [patches[n][fp] for n in ["piano", "piano_changed", "piano2", "piano3"]]
    if len(set(vals)) > 1:
        print(f"  Gap L{L:2d} (pk{pk:3d}, file{fp:3d}): "
              + "  ".join(f"{n}={v:3d}" for n, v in zip(
                  ["piano", "piano_changed", "piano2", "piano3"], vals)))

# Also check Gap L48-L60 (ribbon/scale area per binary extraction)
print("\n\nGap section L48-L60 (ribbon/scale area):")
for L in range(48, 61):
    pk = pack_offset(L, 283, 4)
    fp = packed_to_file(pk)
    if fp is None:
        continue
    vals = {n: patches[n][fp] for n in patches}
    if len(set(vals.values())) > 1:
        print(f"  Gap L{L:2d} (pk{pk:3d}, file{fp:3d}): "
              + "  ".join(f"{n}={v:3d}" for n, v in vals.items()))
