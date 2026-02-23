#!/usr/bin/env python3
"""Compute physical SysEx byte offsets for all RK-100S 2 parameters.

Reverse-engineered from the Korg Sound Editor binary + NRPN validation.

Packing formula: physical = base + logical + ceil((logical + k) / 7)
  - Timbre 1: base=18, k=3  (10/10 NRPN validation)
  - Timbre 2: base=128, k=1 (verified via global packing model)
  - Vocoder bands: base=237, k=6 (32/32 NRPN validation)
  - Gap (effects/vocoder settings/ribbon/scale): base=283, k=4
  - Arp section: base=384, k=1 (verified via global packing model)
  - Common header: direct mapping (bytes 0-17)

Global packing equivalence (verified against all 50 NRPN offsets):
  packed = (unpacked // 7) * 8 + (unpacked % 7) + 1
  The entire program dump is packed as one continuous block from byte 0.

Logical offsets derived from the Korg Sound Editor PE32 binary's
display-name parameter table (confirmed against NRPN-discovered offsets).
"""

import json
import math
from pathlib import Path
from collections import OrderedDict

OUTPUT_PATH = Path.home() / ".config" / "patchmasta" / "offsets.json"

# Ground-truth NRPN-discovered offsets (from device testing via midi/nrpn_scanner.py).
# These are the ONLY offsets validated against the actual hardware.
NRPN_GROUND_TRUTH = {
    "arp_gate": 389,
    "arp_latch": 384,
    "arp_on_off": 384,
    "arp_select": 10,
    "arp_type": 387,
    "patch1_dest": 105,
    "patch1_source": 103,
    "patch2_dest": 108,
    "patch2_source": 107,
    "patch3_dest": 111,
    "patch3_source": 110,
    "patch4_dest": 115,
    "patch4_source": 114,
    "patch5_dest": 118,
    "patch5_source": 117,
    "vocoder_fc_mod_source": 103,
    "vocoder_level_1": 249,
    "vocoder_level_10": 269,
    "vocoder_level_11": 271,
    "vocoder_level_12": 274,
    "vocoder_level_13": 276,
    "vocoder_level_14": 278,
    "vocoder_level_15": 281,
    "vocoder_level_16": 283,
    "vocoder_level_2": 251,
    "vocoder_level_3": 253,
    "vocoder_level_4": 255,
    "vocoder_level_5": 258,
    "vocoder_level_6": 260,
    "vocoder_level_7": 262,
    "vocoder_level_8": 265,
    "vocoder_level_9": 267,
    "vocoder_pan_1": 247,
    "vocoder_pan_10": 268,
    "vocoder_pan_11": 270,
    "vocoder_pan_12": 273,
    "vocoder_pan_13": 275,
    "vocoder_pan_14": 277,
    "vocoder_pan_15": 279,
    "vocoder_pan_16": 282,
    "vocoder_pan_2": 250,
    "vocoder_pan_3": 252,
    "vocoder_pan_4": 254,
    "vocoder_pan_5": 257,
    "vocoder_pan_6": 259,
    "vocoder_pan_7": 261,
    "vocoder_pan_8": 263,
    "vocoder_pan_9": 266,
    "vocoder_sw": 232,
    "voice_mode": 8,
}


def pack_offset(logical: int, base: int, k: int) -> int:
    """physical = base + logical + ceil((logical + k) / 7)"""
    return base + logical + math.ceil((logical + k) / 7)


# ======================================================================
# Logical byte offsets within each section (from binary extraction)
# ======================================================================

# Timbre synth params: logical offset within 96-byte timbre section
# These are the same for both Timbre 1 and Timbre 2
TIMBRE_LOGICAL = {
    # --- Voice / Unison ---
    "unison_sw": 4,
    "unison_detune": 5,
    "unison_spread": 6,
    "voice_assign": 7,
    "analog_tuning": 9,
    "transpose": 10,
    "detune": 11,
    "vibrato_int": 12,
    "bend_range": 13,
    "portamento": 14,

    # --- OSC 1 ---
    "osc1_wave": 16,       # bit-packed with osc1_osc_mod
    "osc1_osc_mod": 16,    # shares byte with osc1_wave
    "osc1_control1": 17,
    "osc1_control2": 18,
    "osc1_wave_select": 19,  # PCM/DWGS wave number (may span 2 bytes)

    # --- OSC 2 ---
    "osc2_wave": 21,       # bit-packed with osc2_osc_mod
    "osc2_osc_mod": 21,    # shares byte with osc2_wave
    "osc2_semitone": 22,
    "osc2_tune": 23,

    # --- Mixer ---
    "mixer_osc1": 24,
    "mixer_osc2": 25,
    "mixer_noise": 26,
    "mixer_punch": 46,     # confirmed from binary extraction

    # --- Filter 1 ---
    "filter_routing": 28,  # shares byte region with filter2_type
    "filter1_balance": 29,
    "filter1_cutoff": 30,
    "filter1_resonance": 31,
    "filter1_eg_int": 32,
    "filter1_key_track": 33,
    "filter1_velo_sens": 34,

    # --- Filter 2 ---
    "filter2_type": 28,    # bit-packed with filter_routing
    "filter2_cutoff": 35,
    "filter2_resonance": 36,
    "filter2_eg_int": 37,
    "filter2_key_track": 38,
    "filter2_velo_sens": 39,

    # --- AMP ---
    "amp_level": 40,
    "amp_pan": 41,
    "amp_ws_type": 42,     # Drive/WS Type
    "amp_ws_depth": 43,    # Drive/WS Depth
    "amp_key_track": 45,
    "amp_ws_position": 46, # WS Position (shares byte with punch/ws_sw)

    # --- Filter EG ---
    "filter_eg_attack": 48,
    "filter_eg_decay": 49,
    "filter_eg_sustain": 50,
    "filter_eg_release": 51,
    "filter_eg_velo": 52,

    # --- AMP EG ---
    "amp_eg_attack": 54,
    "amp_eg_decay": 55,
    "amp_eg_sustain": 56,
    "amp_eg_release": 57,
    "amp_eg_velo": 58,

    # --- Assignable EG ---
    "assign_eg_attack": 60,
    "assign_eg_decay": 61,
    "assign_eg_sustain": 62,
    "assign_eg_release": 63,
    "assign_eg_velo": 64,

    # --- LFO 1 ---
    "lfo1_wave": 66,
    "lfo1_freq": 67,
    "lfo1_key_sync": 68,
    "lfo1_sync_note": 69,
    "lfo1_bpm_sync": 68,   # shares byte with key_sync

    # --- LFO 2 ---
    "lfo2_wave": 70,
    "lfo2_freq": 71,
    "lfo2_key_sync": 72,
    "lfo2_sync_note": 73,
    "lfo2_bpm_sync": 72,   # shares byte with key_sync

    # --- Virtual Patches (stride 3: source, dest, intensity) ---
    "patch1_source": 74,   # Validated: physical 103
    "patch1_dest": 75,     # Validated: physical 105
    "patch1_intensity": 76,
    "patch2_source": 77,   # Validated: physical 107
    "patch2_dest": 78,     # Validated: physical 108
    "patch2_intensity": 79,
    "patch3_source": 80,   # Validated: physical 110
    "patch3_dest": 81,     # Validated: physical 111
    "patch3_intensity": 82,
    "patch4_source": 83,   # Validated: physical 114
    "patch4_dest": 84,     # Validated: physical 115
    "patch4_intensity": 85,
    "patch5_source": 86,   # Validated: physical 117
    "patch5_dest": 87,     # Validated: physical 118
    "patch5_intensity": 88,

    # --- Timbre EQ ---
    "eq_low_freq": 92,
    "eq_low_gain": 93,
    "eq_high_freq": 94,
    "eq_high_gain": 95,

    # --- Ribbon (per-timbre, mirrored in T1 and T2) ---
    "long_ribbon_filter_int": 91,  # Confirmed: T1→pk123, T2→pk233
}

# Vocoder band params: logical offset within vocoder band section
VOCODER_BAND_LOGICAL = {}
for band in range(1, 17):
    VOCODER_BAND_LOGICAL[f"vocoder_pan_{band}"] = (band - 1) * 2 + 8
    VOCODER_BAND_LOGICAL[f"vocoder_level_{band}"] = (band - 1) * 2 + 9

# Arp params: logical offset within arp section
ARP_LOGICAL = {
    "arp_resolution": 0,
    "arp_last_step": 1,
    "arp_type": 2,        # Validated: physical 387
    "arp_gate": 4,        # Validated: physical 389
    "arp_swing": 5,       # Confirmed via diff: physical 390
    # Logical 10-14 = ribbon params (confirmed via diff)
    "short_ribbon_mod_assign": 10,   # physical 396 (CC number, 7-bit)
    "short_ribbon_setting": 11,      # physical 397 (bit 0)
    "scale": 12,                      # physical 398 (confirmed via diff)
    "long_ribbon_scale_range": 13,   # physical 399
    "long_ribbon_pitch_range": 14,   # physical 401
    # Step SWs are at logical 16-23 (physical 403-411)
}

# Gap section: IFX (effects), vocoder filter, ribbon, scale
# Sits between vocoder bands (ends at packed 283) and arp (starts at packed 384)
# base=283, k=4 → first data byte at packed 284
GAP_LOGICAL = {
    # IFX 1 (effect slot 1): logical 0 + params
    "fx1_type": 0,          # Effect type (internal numbering)

    # Vocoder filter params (confirmed via diff testing):
    "vocoder_fc_offset": 2,     # Signed center=64, physical 286
    "vocoder_resonance": 3,     # Physical 287
    "vocoder_fc_mod_int": 4,    # Signed center=64, physical 289
    "vocoder_ef_sens": 5,       # Physical 290

    # IFX 1 params continue at logical 6+
    # IFX 2 (effect slot 2): logical 24-47
    "fx2_sw_type": 24,      # IFX2 on/off + type (bit-packed)

    # Remaining (logical 48-87): MFX EQ, ribbon, scale, other
    # MFX EQ at logical 48-51 (confirmed from binary extraction)
}

# Map params.py names to our naming convention
PARAMS_PY_TO_LOGICAL = {
    # Common/header params (direct physical offsets)
    "voice_mode": ("common", 8),
    "arp_select": ("common", 10),

    # Arp params
    "arp_on_off": ("arp_msb", 0),   # MSB byte at physical 384
    "arp_latch": ("arp_msb", 1),    # MSB byte at physical 384
    "arp_type": ("arp", 2),
    "arp_gate": ("arp", 4),
    "arp_resolution": ("arp", 0),
    "arp_last_step": ("arp", 1),

    # Gap section (IFX effects + vocoder filter)
    "fx1_type": ("gap", 0),
    "fx1_ribbon_assign": ("gap", 40),     # pk330, confirmed via diff
    "fx1_ribbon_polarity": ("gap", 41),   # pk331, confirmed via diff
    "fx2_type": ("gap", 24),
    "fx2_ribbon_assign": ("gap", 64),     # pk357, confirmed via diff
    "fx2_ribbon_polarity": ("gap", 65),   # pk358, confirmed via diff
    "vocoder_fc_offset": ("gap", 2),       # Signed center=64, confirmed via diff
    "vocoder_resonance": ("gap", 3),       # Confirmed via diff
    "vocoder_fc_mod_int": ("gap", 4),      # Signed center=64, confirmed via diff
    "vocoder_ef_sens": ("gap", 5),         # Confirmed via diff

    # Vocoder SW
    "vocoder_sw": ("vocoder_header", 232),
    "vocoder_fc_mod_source": ("timbre1", 74),  # Shares byte with patch1_source

    # Vocoder header params (base=237, k=6, logical 0-7)
    "vocoder_gate_sens": ("vocoder_band", 1),       # pk239
    "vocoder_gate_threshold": ("vocoder_band", 2),   # pk241
    "vocoder_hpf_level": ("vocoder_band", 3),        # pk242
    "vocoder_direct_level": ("vocoder_band", 4),     # pk243
    "vocoder_timbre1_level": ("vocoder_band", 5),    # pk244
    "vocoder_timbre2_level": ("vocoder_band", 6),    # pk245
    "vocoder_level": ("vocoder_band", 7),            # pk246

    # Arp extended params
    "arp_swing": ("arp", 5),               # Confirmed via diff
    "arp_key_sync": ("arp_msb", 6),        # HB[384] bit 6, confirmed via piano2→piano3 diff
    "arp_step_switches": ("arp", 6),       # All 8 steps in one byte, confirmed via piano3→piano4 diff
    "arp_octave_range": ("arp", 3),        # Arp L3 (pk388), bits 5-6, confirmed via diff
    "scale": ("arp", 12),                  # Confirmed via diff

    # Ribbon params (in arp section)
    "short_ribbon_mod_assign": ("arp", 10),    # pk396, CC number (7-bit)
    "short_ribbon_mod_lock": ("arp_msb2", 3),  # HB[392] bit 3 (MSB of pk396)
    "short_ribbon_setting": ("arp", 11),       # pk397 bit 0
    "long_ribbon_scale_range": ("arp", 13),    # pk399
    "long_ribbon_pitch_range": ("arp", 14),    # pk401

    # Ribbon filter intensity (per-timbre, stored at timbre logical 91)
    "long_ribbon_filter_int": ("timbre1", 91), # pk123 (mirrored in T2 at pk233)

    # Vocoder bands
    **{f"vocoder_level_{i}": ("vocoder_band", (i-1)*2+9) for i in range(1, 17)},
    **{f"vocoder_pan_{i}": ("vocoder_band", (i-1)*2+8) for i in range(1, 17)},

    # Virtual patches (source/dest use timbre1 section)
    **{f"patch{i}_source": ("timbre1", 74 + (i-1)*3) for i in range(1, 6)},
    **{f"patch{i}_dest": ("timbre1", 75 + (i-1)*3) for i in range(1, 6)},
    **{f"patch{i}_intensity": ("timbre1", 76 + (i-1)*3) for i in range(1, 6)},

    # Timbre 1 synth params
    **{f"t1_{k}": ("timbre1", v) for k, v in TIMBRE_LOGICAL.items()
       if not k.startswith("patch") and not k.startswith("eq_")},

    # Timbre 1 filter routing
    "t1_filter_routing": ("timbre1", 28),

    # Timbre 1 EQ
    "t1_eq_low_freq": ("timbre1", 92),
    "t1_eq_low_gain": ("timbre1", 93),
    "t1_eq_high_freq": ("timbre1", 94),
    "t1_eq_high_gain": ("timbre1", 95),

    # Timbre 2 synth params (same logical offsets, different base)
    **{f"t2_{k}": ("timbre2", v) for k, v in TIMBRE_LOGICAL.items()
       if not k.startswith("patch") and not k.startswith("eq_")},

    # Timbre 2 EQ
    "t2_eq_low_freq": ("timbre2", 92),
    "t2_eq_low_gain": ("timbre2", 93),
    "t2_eq_high_freq": ("timbre2", 94),
    "t2_eq_high_gain": ("timbre2", 95),
}


def compute_physical(section: str, logical: int) -> int:
    """Compute physical SysEx byte offset from section and logical offset."""
    if section == "common":
        return logical  # Direct mapping, no packing
    elif section == "timbre1":
        return pack_offset(logical, base=18, k=3)
    elif section == "timbre2":
        return pack_offset(logical, base=128, k=1)
    elif section == "vocoder_band":
        return pack_offset(logical, base=237, k=6)
    elif section == "vocoder_header":
        return logical  # Direct physical offset
    elif section == "gap":
        return pack_offset(logical, base=283, k=4)
    elif section == "arp":
        return pack_offset(logical, base=384, k=1)
    elif section == "arp_msb":
        return 384  # HB byte for arp section (bit-packed booleans)
    elif section == "arp_msb2":
        return 392  # 2nd HB byte in arp section (bit-packed: mod_lock, etc.)
    else:
        raise ValueError(f"Unknown section: {section}")


def main():
    # Compute all physical offsets
    offset_map = OrderedDict()

    for param_name, (section, logical) in sorted(PARAMS_PY_TO_LOGICAL.items()):
        physical = compute_physical(section, logical)
        offset_map[param_name] = physical

    # Use embedded NRPN ground truth for validation
    nrpn_data = NRPN_GROUND_TRUTH

    # Validate
    print("=" * 60)
    print("VALIDATION AGAINST NRPN-DISCOVERED OFFSETS")
    print("=" * 60)

    validated = 0
    failed = 0
    unmatched = 0

    for nrpn_name, nrpn_physical in sorted(nrpn_data.items()):
        computed = offset_map.get(nrpn_name)
        if computed is not None:
            ok = computed == nrpn_physical
            validated += int(ok)
            failed += int(not ok)
            mark = "✓" if ok else "✗"
            print(f"  {mark} {nrpn_name:30s} computed={computed:3d}  nrpn={nrpn_physical:3d}")
        else:
            unmatched += 1
            print(f"  ? {nrpn_name:30s} not in map  nrpn={nrpn_physical:3d}")

    print(f"\nValidated: {validated}  Failed: {failed}  Unmatched: {unmatched}")

    if failed > 0:
        print("\n*** VALIDATION FAILURES - DO NOT SAVE ***")
        return

    # Print summary by section
    print(f"\n{'='*60}")
    print("OFFSET MAP SUMMARY")
    print(f"{'='*60}")

    sections = {}
    for name, (section, _) in PARAMS_PY_TO_LOGICAL.items():
        sections.setdefault(section, []).append(name)

    for section in ["common", "timbre1", "timbre2", "vocoder_header",
                     "vocoder_band", "gap", "arp", "arp_msb", "arp_msb2"]:
        params = sections.get(section, [])
        if not params:
            continue
        physical_range = [offset_map[p] for p in params]
        print(f"\n  {section}: {len(params)} params, physical {min(physical_range)}-{max(physical_range)}")
        for p in sorted(params, key=lambda x: offset_map[x]):
            print(f"    {offset_map[p]:3d}  {p}")

    # Save
    print(f"\nSaving {len(offset_map)} offsets to {OUTPUT_PATH}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(offset_map, indent=2))
    print("Done!")


if __name__ == "__main__":
    main()
