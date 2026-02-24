# Effects System: Dynamic UI & SysEx Offset Mapping

**Date:** 2026-02-23
**Status:** Complete

---

## What Was Built

### 1. Effect Type Registry (`midi/effects.py`)

A complete registry of all 18 RK-100S 2 Master Effect types (0=Off, 1–17 active),
sourced from the Parameter Guide pp37–54 and cross-checked against the Sound Editor
binary at `0x0012D7EC`.

**Data structures:**

```python
@dataclass
class EffectParam:
    key: str              # e.g. "dry_wet", "cutoff"
    display_name: str     # e.g. "Dry/Wet", "Cutoff"
    min_val: int
    max_val: int
    slot_index: int       # position within the effect's data area (0–22)
    value_labels: dict[int, str] | None = None
    ribbon_assignable: bool = True

@dataclass
class EffectTypeDef:
    type_id: int
    name: str
    params: list[EffectParam]

    def ribbon_assigns(self) -> list[EffectParam]: ...
```

**Effect types:**

| ID | Name | Params | Key ribbon params |
|----|------|--------|-------------------|
| 0 | Effect Off | 0 | — |
| 1 | Compressor | 5 | Dry/Wet, Sensitivity, Attack |
| 2 | Filter | 16 | Dry/Wet, Cutoff, Resonance, Mod Intensity, Mod Response, LFO Frequency, LFO Sync Note |
| 3 | 4Band EQ | 16 | Dry/Wet, B1–B4 Gain |
| 4 | Distortion | 15 | Dry/Wet, Gain, EQ Gains |
| 5 | Decimator | 14 | Dry/Wet, Fs, Bit, Fs Mod Intensity, LFO Frequency, LFO Sync Note |
| 6 | Delay | 10 | Dry/Wet, Time Ratio, Feedback |
| 7 | L/C/R Delay | 12 | Dry/Wet, Time Ratio, C Feedback |
| 8 | Auto Panning Delay | 18 | Dry/Wet, Time Ratio, Feedback, Mod Depth, LFO Frequency, LFO Sync Note |
| 9 | Modulation Delay | 9 | Dry/Wet, Time Ratio, Feedback, Mod Depth, LFO Frequency |
| 10 | Tape Echo | 16 | Dry/Wet, Time Ratio, Tap1/2 Level, Feedback, Saturation |
| 11 | Chorus | 8 | Dry/Wet, Mod Depth, LFO Frequency |
| 12 | Flanger | 14 | Dry/Wet, Delay, Mod Depth, Feedback, LFO Frequency, LFO Sync Note |
| 13 | Vibrato | 10 | Dry/Wet, Mod Depth, LFO Frequency, LFO Sync Note |
| 14 | Phaser | 14 | Dry/Wet, Manual, Mod Depth, Resonance, LFO Frequency, LFO Sync Note |
| 15 | Tremolo | 10 | Dry/Wet, Mod Depth, LFO Frequency, LFO Sync Note |
| 16 | Ring Modulator | 15 | Dry/Wet, Fixed Frequency, Note Offset, LFO Intensity, LFO Frequency, LFO Sync Note |
| 17 | Grain Shifter | 11 | Dry/Wet, Time Ratio, LFO Frequency, LFO Sync Note |

The `ribbon_assignable` flag for each param was confirmed from the Sound Editor binary
(v6 field in the second param table at `0x0012D7EC`, 17 blocks × 20 entries × 36 bytes).

---

### 2. Dynamic Effects Tab (`ui/synth_tabs.py`)

`EffectsTab` was rewritten to rebuild its parameter controls whenever the FX type
combo changes. Previously it showed only 3 static params per slot (Type, Ribbon Assign,
Ribbon Polarity).

**Architecture:**

- Static area: FX Type combo + Ribbon Polarity (from ParamMap, always visible)
- Dynamic container: rebuilt on type change via `_on_fx_type_changed(slot, type_id)`
  - Ribbon Assign combo (always present, options depend on active effect type)
  - Per-effect-type parameter widgets (ParamSlider or ParamCombo per EffectParam)

**Key implementation details:**

- `_dynamic_widgets[slot]` — tracks active dynamic param widgets per FX slot
- `_fx_packed_map` — maps `widget_name → packed_sysex_offset` for active dynamic params
- `get_fx_sysex_offset(name)` — exposed so SynthEditorWindow can route SysEx writes
- `fx_sysex_items()` — returns all active (name, packed_offset) pairs for patch loading

**SynthEditorWindow integration:**

- `_on_user_param_change` checks `effects_tab.get_fx_sysex_offset(name)` for params not
  in the ParamMap, writing directly to the SysEx buffer at the computed packed offset
- `load_program_data` dispatches fx_type changes first (which rebuilds dynamic widgets),
  then repopulates dynamic FX param values from the buffer via `fx_sysex_items()`

---

### 3. SysEx Offset Mapping (Empirically Confirmed)

All offsets confirmed by saving patch files from the Sound Editor and diffing against
a baseline with `tools/patch_diff.py`.

**Gap section layout** (base=283, k=4):

```
Gap L38  packed=327   fx1_type           (0=Off, 1=Compressor, ..., 17=Grain Shifter)
Gap L40  packed=330   fx1_ribbon_assign  encoding: 31=Assign Off, slot_index=assigned param
Gap L41  packed=331   fx1_ribbon_polarity  0=Forward, 1=Reverse
Gap L42  packed=332   FX1 slot 0  (dry_wet for all active types)
Gap L43  packed=333   FX1 slot 1
...
Gap L59  packed=354   FX1 slot 17  (max slot index across all effect types)
Gap L62  packed=355   fx2_type
Gap L64  packed=357   fx2_ribbon_assign  (same encoding as FX1)
Gap L65  packed=358   fx2_ribbon_polarity
Gap L66  packed=359   FX2 slot 0  (dry_wet)
...
Gap L83  packed=377   FX2 slot 17
```

**SysEx helper** in `midi/effects.py`:

```python
def fx_param_packed(slot: int, slot_index: int) -> int:
    """Return packed SysEx offset for effect param at slot (1 or 2), slot_index."""
    base = FX1_PARAMS_LOGICAL_BASE if slot == 1 else FX2_PARAMS_LOGICAL_BASE  # 42 or 66
    logical = base + slot_index
    return _GAP_BASE + logical + math.ceil((logical + _GAP_K) / 7)
```

**Ribbon assign encoding:**

The ribbon assign field stores the `slot_index` of the assigned parameter directly.
The sentinel value `31` means "Assign Off" (safe because no effect type has a param
at slot 31 — the maximum slot_index across all 17 types is 17).

The `ParamCombo` ranges for the ribbon assign widget are:
```python
sysex_vals = [31] + [p.slot_index for p in ribbon_params]
ranges = [(v, v) for v in sysex_vals]
```

This means `set_value(31)` selects "Assign Off", `set_value(0)` selects "Dry/Wet", etc.

**Previously wrong offsets fixed in `params.py`:**

| Param | Old (wrong) | New (confirmed) |
|-------|-------------|-----------------|
| fx1_type | 284 (Gap L0) | 327 (Gap L38) |
| fx2_type | 311 (Gap L24) | 355 (Gap L62) |

---

## Patch Files Used for Diffing

Saved from Korg Sound Editor into `patches/` directory:

| File | Contents |
|------|----------|
| `fx_off.rk100s2_prog` | FX1=Effect Off, FX2=Effect Off |
| `fx_compressor.rk100s2_prog` | FX1=Compressor (default params) |
| `fx_types.rk100s2_prog` | FX1=Filter, FX2=Compressor (both default params) |
| `fx2_compressor.rk100s2_prog` | FX1=Effect Off, FX2=Compressor |
| `fx1_ribbon_off.rk100s2_prog` | FX1=Compressor, ribbon assign=Assign Off |
| `fx1_ribbon_drywet.rk100s2_prog` | FX1=Compressor, ribbon assign=Dry/Wet, polarity=Forward |
| `fx1_ribbon_reverse.rk100s2_prog` | FX1=Compressor, ribbon assign=Dry/Wet, polarity=Reverse |
| `fx2_ribbon_drywet.rk100s2_prog` | FX1=Effect Off, FX2=Compressor, FX2 ribbon assign=Dry/Wet |

---

## Test Coverage

- `tests/midi/test_effects.py` — 22 tests covering the effect type registry
- `tests/ui/test_synth_tabs.py` — dynamic rebuild, type switching, ribbon assign encoding,
  FX1/FX2 independence, on_param_changed, user change callbacks
