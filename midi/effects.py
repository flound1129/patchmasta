"""Effect type registry for RK-100S 2 Master Effects.

Defines the 17 effect types (plus Off) with their per-type parameter metadata,
sourced from the Parameter Guide pp37-54 and confirmed against the Sound Editor
binary (v6 field in the param table at 0x0012D7EC marks ribbon_assignable=True).
SysEx byte offsets are NOT included here -- added later via device diffing.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EffectParam:
    """A single parameter within an effect type."""
    key: str              # e.g. "dry_wet", "cutoff"
    display_name: str     # e.g. "Dry/Wet", "Cutoff"
    min_val: int
    max_val: int
    slot_index: int       # position within the effect's data area (0-22)
    value_labels: dict[int, str] | None = None
    ribbon_assignable: bool = True  # appears in ribbon assign dropdown


@dataclass
class EffectTypeDef:
    """Definition of a single effect type."""
    type_id: int          # 0=Off, 1=Compressor, ..., 17=Grain Shifter
    name: str
    params: list[EffectParam] = field(default_factory=list)

    def ribbon_assigns(self) -> list[EffectParam]:
        """Return params that appear in the ribbon assign dropdown (in order)."""
        return [p for p in self.params if p.ribbon_assignable]


# ---------------------------------------------------------------------------
# Common value label dicts reused across many effect types
# ---------------------------------------------------------------------------
_LFO_WAVEFORM = {0: "Saw", 1: "Square", 2: "Triangle", 3: "Sine", 4: "S&H"}
_LFO_SYNC_NOTE = {
    0: "8/1", 1: "6/1", 2: "4/1", 3: "3/1", 4: "2/1", 5: "3/2",
    6: "1/1", 7: "3/4", 8: "1/2", 9: "3/8", 10: "1/3", 11: "1/4",
    12: "3/16", 13: "1/6", 14: "1/8", 15: "3/32", 16: "1/12",
    17: "1/16", 18: "1/24", 19: "1/32", 20: "1/48", 21: "1/64",
}
_OFF_ON = {0: "Off", 1: "On"}
_PHASE = {0: "+", 1: "-"}

# ---------------------------------------------------------------------------
# All 18 effect types (0 = Effect Off, 1-17 = active effects)
# ---------------------------------------------------------------------------

EFFECT_TYPES: dict[int, EffectTypeDef] = {
    # -----------------------------------------------------------------------
    # 0: Effect Off
    # -----------------------------------------------------------------------
    0: EffectTypeDef(0, "Effect Off"),

    # -----------------------------------------------------------------------
    # 1: Compressor (5 params)
    #    ribbon: dry_wet, sensitivity, attack
    # -----------------------------------------------------------------------
    1: EffectTypeDef(1, "Compressor", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("envelope_select", "Envelope Select", 0, 1, 1,
                    {0: "LR Mix", 1: "LR Individual"}, ribbon_assignable=False),
        EffectParam("sensitivity", "Sensitivity", 0, 127, 2),
        EffectParam("attack", "Attack", 0, 127, 3),
        EffectParam("output_level", "Output Level", 0, 127, 4, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 2: Filter (16 params)
    #    ribbon: dry_wet, cutoff, resonance, mod_intensity, mod_response,
    #            lfo_frequency, lfo_sync_note
    # -----------------------------------------------------------------------
    2: EffectTypeDef(2, "Filter", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("filter_type", "Filter Type", 0, 4, 1,
                    {0: "LPF24", 1: "LPF18", 2: "LPF12", 3: "HPF12", 4: "BPF12"},
                    ribbon_assignable=False),
        EffectParam("cutoff", "Cutoff", 0, 127, 2),
        EffectParam("resonance", "Resonance", 0, 127, 3),
        EffectParam("trim", "Trim", 0, 127, 4, ribbon_assignable=False),
        EffectParam("mod_source", "Mod Source", 0, 1, 5,
                    {0: "LFO", 1: "Control"}, ribbon_assignable=False),
        EffectParam("mod_intensity", "Mod Intensity", 0, 127, 6),
        EffectParam("mod_response", "Mod Response", 0, 127, 7),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 8, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 9),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 10, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 11, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 12, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 13, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 14,
                    ribbon_assignable=False),
        EffectParam("control_source", "Control Source", 0, 7, 15,
                    {0: "Off", 1: "Velocity", 2: "Short Ribbon (Pitch)",
                     3: "Short Ribbon (Mod)", 4: "MIDI Control 1",
                     5: "MIDI Control 2", 6: "MIDI Control 3"},
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 3: 4Band EQ (16 params)
    #    ribbon: dry_wet, b1_gain, b2_gain, b3_gain, b4_gain
    # -----------------------------------------------------------------------
    3: EffectTypeDef(3, "4Band EQ", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("trim", "Trim", 0, 127, 1, ribbon_assignable=False),
        EffectParam("b1_type", "B1 Type", 0, 1, 2,
                    {0: "Peaking", 1: "Shelving Low"}, ribbon_assignable=False),
        EffectParam("b1_frequency", "B1 Frequency", 0, 127, 3,
                    ribbon_assignable=False),
        EffectParam("b1_q", "B1 Q", 0, 127, 4, ribbon_assignable=False),
        EffectParam("b1_gain", "B1 Gain", 0, 36, 5),
        EffectParam("b2_frequency", "B2 Frequency", 0, 127, 6,
                    ribbon_assignable=False),
        EffectParam("b2_q", "B2 Q", 0, 127, 7, ribbon_assignable=False),
        EffectParam("b2_gain", "B2 Gain", 0, 36, 8),
        EffectParam("b3_frequency", "B3 Frequency", 0, 127, 9,
                    ribbon_assignable=False),
        EffectParam("b3_q", "B3 Q", 0, 127, 10, ribbon_assignable=False),
        EffectParam("b3_gain", "B3 Gain", 0, 36, 11),
        EffectParam("b4_type", "B4 Type", 0, 1, 12,
                    {0: "Peaking", 1: "Shelving High"}, ribbon_assignable=False),
        EffectParam("b4_frequency", "B4 Frequency", 0, 127, 13,
                    ribbon_assignable=False),
        EffectParam("b4_q", "B4 Q", 0, 127, 14, ribbon_assignable=False),
        EffectParam("b4_gain", "B4 Gain", 0, 36, 15),
    ]),

    # -----------------------------------------------------------------------
    # 4: Distortion (15 params)
    #    ribbon: dry_wet, gain, pre_eq_gain, b1_gain, b2_gain, b3_gain
    # -----------------------------------------------------------------------
    4: EffectTypeDef(4, "Distortion", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("gain", "Gain", 0, 127, 1),
        EffectParam("pre_eq_frequency", "Pre EQ Frequency", 0, 127, 2,
                    ribbon_assignable=False),
        EffectParam("pre_eq_q", "Pre EQ Q", 0, 127, 3, ribbon_assignable=False),
        EffectParam("pre_eq_gain", "Pre EQ Gain", 0, 36, 4),
        EffectParam("b1_frequency", "B1 Frequency", 0, 127, 5,
                    ribbon_assignable=False),
        EffectParam("b1_q", "B1 Q", 0, 127, 6, ribbon_assignable=False),
        EffectParam("b1_gain", "B1 Gain", 0, 36, 7),
        EffectParam("b2_frequency", "B2 Frequency", 0, 127, 8,
                    ribbon_assignable=False),
        EffectParam("b2_q", "B2 Q", 0, 127, 9, ribbon_assignable=False),
        EffectParam("b2_gain", "B2 Gain", 0, 36, 10),
        EffectParam("b3_frequency", "B3 Frequency", 0, 127, 11,
                    ribbon_assignable=False),
        EffectParam("b3_q", "B3 Q", 0, 127, 12, ribbon_assignable=False),
        EffectParam("b3_gain", "B3 Gain", 0, 36, 13),
        EffectParam("output_level", "Output Level", 0, 127, 14,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 5: Decimator (14 params — lfo_spread not present in binary)
    #    ribbon: dry_wet, fs, bit, fs_mod_intensity, lfo_frequency, lfo_sync_note
    # -----------------------------------------------------------------------
    5: EffectTypeDef(5, "Decimator", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("pre_lpf", "Pre LPF", 0, 1, 1, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("high_damp", "High Damp", 0, 100, 2, ribbon_assignable=False),
        EffectParam("fs", "Fs", 0, 127, 3),
        EffectParam("bit", "Bit", 0, 20, 4),
        EffectParam("output_level", "Output Level", 0, 127, 5,
                    ribbon_assignable=False),
        EffectParam("fs_mod_intensity", "Fs Mod Intensity", 0, 127, 6),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 7, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 8),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 9, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 10, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 11, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 12, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 13,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 6: Delay (10 params)
    #    ribbon: dry_wet, time_ratio, feedback
    # -----------------------------------------------------------------------
    6: EffectTypeDef(6, "Delay", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("type", "Type", 0, 1, 1,
                    {0: "Stereo", 1: "Cross"}, ribbon_assignable=False),
        EffectParam("delay_tempo_sync", "Delay Tempo Sync", 0, 1, 2, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("time_ratio", "Time Ratio", 0, 127, 3),
        EffectParam("l_delay_time", "L Delay Time", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("r_delay_time", "R Delay Time", 0, 127, 5,
                    ribbon_assignable=False),
        EffectParam("feedback", "Feedback", 0, 127, 6),
        EffectParam("high_damp", "High Damp", 0, 100, 7, ribbon_assignable=False),
        EffectParam("trim", "Trim", 0, 127, 8, ribbon_assignable=False),
        EffectParam("spread", "Spread", 0, 127, 9, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 7: L/C/R Delay (12 params)
    #    ribbon: dry_wet, time_ratio, c_feedback
    # -----------------------------------------------------------------------
    7: EffectTypeDef(7, "L/C/R Delay", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("delay_tempo_sync", "Delay Tempo Sync", 0, 1, 1, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("time_ratio", "Time Ratio", 0, 127, 2),
        EffectParam("l_delay_time", "L Delay Time", 0, 127, 3,
                    ribbon_assignable=False),
        EffectParam("c_delay_time", "C Delay Time", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("r_delay_time", "R Delay Time", 0, 127, 5,
                    ribbon_assignable=False),
        EffectParam("l_delay_level", "L Delay Level", 0, 127, 6,
                    ribbon_assignable=False),
        EffectParam("c_delay_level", "C Delay Level", 0, 127, 7,
                    ribbon_assignable=False),
        EffectParam("r_delay_level", "R Delay Level", 0, 127, 8,
                    ribbon_assignable=False),
        EffectParam("c_feedback", "C Feedback", 0, 127, 9),
        EffectParam("trim", "Trim", 0, 127, 10, ribbon_assignable=False),
        EffectParam("spread", "Spread", 0, 127, 11, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 8: Auto Panning Delay (18 params)
    #    ribbon: dry_wet, time_ratio, feedback, mod_depth, lfo_frequency,
    #            lfo_sync_note
    # -----------------------------------------------------------------------
    8: EffectTypeDef(8, "Auto Panning Delay", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("delay_tempo_sync", "Delay Tempo Sync", 0, 1, 1, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("time_ratio", "Time Ratio", 0, 127, 2),
        EffectParam("l_delay_time", "L Delay Time", 0, 127, 3,
                    ribbon_assignable=False),
        EffectParam("r_delay_time", "R Delay Time", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("feedback", "Feedback", 0, 127, 5),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 6),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 7, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 8),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 9, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 10, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 11, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 12, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 13,
                    ribbon_assignable=False),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 14,
                    ribbon_assignable=False),
        EffectParam("high_damp", "High Damp", 0, 100, 15, ribbon_assignable=False),
        EffectParam("trim", "Trim", 0, 127, 16, ribbon_assignable=False),
        EffectParam("spread", "Spread", 0, 127, 17, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 9: Modulation Delay (9 params)
    #    ribbon: dry_wet, time_ratio, feedback, mod_depth, lfo_frequency
    # -----------------------------------------------------------------------
    9: EffectTypeDef(9, "Modulation Delay", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("delay_tempo_sync", "Delay Tempo Sync", 0, 1, 1, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("time_ratio", "Time Ratio", 0, 127, 2),
        EffectParam("l_delay_time", "L Delay Time", 0, 127, 3,
                    ribbon_assignable=False),
        EffectParam("r_delay_time", "R Delay Time", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("feedback", "Feedback", 0, 127, 5),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 6),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 7),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 8,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 10: Tape Echo (16 params)
    #     ribbon: dry_wet, time_ratio, tap1_level, tap2_level, feedback,
    #             saturation
    # -----------------------------------------------------------------------
    10: EffectTypeDef(10, "Tape Echo", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("delay_tempo_sync", "Delay Tempo Sync", 0, 1, 1, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("time_ratio", "Time Ratio", 0, 127, 2),
        EffectParam("tap1_delay_time", "Tap1 Delay Time", 0, 127, 3,
                    ribbon_assignable=False),
        EffectParam("tap2_delay_time", "Tap2 Delay Time", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("tap1_level", "Tap1 Level", 0, 127, 5),
        EffectParam("tap2_level", "Tap2 Level", 0, 127, 6),
        EffectParam("feedback", "Feedback", 0, 127, 7),
        EffectParam("high_damp", "High Damp", 0, 100, 8, ribbon_assignable=False),
        EffectParam("low_damp", "Low Damp", 0, 100, 9, ribbon_assignable=False),
        EffectParam("trim", "Trim", 0, 127, 10, ribbon_assignable=False),
        EffectParam("saturation", "Saturation", 0, 127, 11),
        EffectParam("wow_flutter_frequency", "WOW Flutter Frequency", 0, 127, 12,
                    ribbon_assignable=False),
        EffectParam("wow_flutter_depth", "WOW Flutter Depth", 0, 127, 13,
                    ribbon_assignable=False),
        EffectParam("pre_tone", "Pre Tone", 0, 127, 14, ribbon_assignable=False),
        EffectParam("spread", "Spread", 0, 127, 15, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 11: Chorus (8 params)
    #     ribbon: dry_wet, mod_depth, lfo_frequency
    # -----------------------------------------------------------------------
    11: EffectTypeDef(11, "Chorus", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 1),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 2),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 3, ribbon_assignable=False),
        EffectParam("predelay_l", "PreDelay L", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("predelay_r", "PreDelay R", 0, 127, 5,
                    ribbon_assignable=False),
        EffectParam("trim", "Trim", 0, 127, 6, ribbon_assignable=False),
        EffectParam("high_eq_gain", "High EQ Gain", 0, 127, 7,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 12: Flanger (14 params)
    #     ribbon: dry_wet, delay, mod_depth, feedback, lfo_frequency,
    #             lfo_sync_note
    # -----------------------------------------------------------------------
    12: EffectTypeDef(12, "Flanger", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("delay", "Delay", 0, 127, 1),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 2),
        EffectParam("feedback", "Feedback", 0, 127, 3),
        EffectParam("phase", "Phase", 0, 1, 4, _PHASE, ribbon_assignable=False),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 5, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 6),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 7, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 8, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 9, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 10, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 11,
                    ribbon_assignable=False),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 12,
                    ribbon_assignable=False),
        EffectParam("high_damp", "High Damp", 0, 100, 13, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 13: Vibrato (10 params)
    #     ribbon: dry_wet, mod_depth, lfo_frequency, lfo_sync_note
    # -----------------------------------------------------------------------
    13: EffectTypeDef(13, "Vibrato", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 1),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 2, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 3),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 4, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 5, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 6, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 7, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 8,
                    ribbon_assignable=False),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 9,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 14: Phaser (14 params)
    #     ribbon: dry_wet, manual, mod_depth, resonance, lfo_frequency,
    #             lfo_sync_note
    # -----------------------------------------------------------------------
    14: EffectTypeDef(14, "Phaser", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("type", "Type", 0, 1, 1,
                    {0: "BLUE", 1: "U-VB"}, ribbon_assignable=False),
        EffectParam("manual", "Manual", 0, 127, 2),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 3),
        EffectParam("resonance", "Resonance", 0, 127, 4),
        EffectParam("phase", "Phase", 0, 1, 5, _PHASE, ribbon_assignable=False),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 6, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 7),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 8, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 9, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 10, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 11, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 12,
                    ribbon_assignable=False),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 13,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 15: Tremolo (10 params)
    #     ribbon: dry_wet, mod_depth, lfo_frequency, lfo_sync_note
    # -----------------------------------------------------------------------
    15: EffectTypeDef(15, "Tremolo", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("mod_depth", "Mod Depth", 0, 127, 1),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 2, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 3),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 4, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 5, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 6, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 7, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 8,
                    ribbon_assignable=False),
        EffectParam("lfo_spread", "LFO Spread", 0, 127, 9,
                    ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 16: Ring Modulator (15 params — lfo_spread not in binary)
    #     ribbon: dry_wet, fixed_frequency, note_offset, lfo_intensity,
    #             lfo_frequency, lfo_sync_note
    # -----------------------------------------------------------------------
    16: EffectTypeDef(16, "Ring Modulator", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("osc_mode", "OSC Mode", 0, 1, 1,
                    {0: "Fixed", 1: "Note"}, ribbon_assignable=False),
        EffectParam("fixed_frequency", "Fixed Frequency", 0, 127, 2),
        EffectParam("note_offset", "Note Offset", 0, 127, 3),
        EffectParam("note_fine", "Note Fine", 0, 127, 4,
                    ribbon_assignable=False),
        EffectParam("osc_waveform", "OSC Waveform", 0, 2, 5,
                    {0: "Saw", 1: "Triangle", 2: "Sine"}, ribbon_assignable=False),
        EffectParam("lfo_intensity", "LFO Intensity", 0, 127, 6),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 7, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 8),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 9, _LFO_SYNC_NOTE),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 10, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 11, ribbon_assignable=False),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 12, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 13,
                    ribbon_assignable=False),
        EffectParam("pre_lpf", "Pre LPF", 0, 127, 14, ribbon_assignable=False),
    ]),

    # -----------------------------------------------------------------------
    # 17: Grain Shifter (11 params)
    #     ribbon: dry_wet, time_ratio, lfo_frequency, lfo_sync_note
    # -----------------------------------------------------------------------
    17: EffectTypeDef(17, "Grain Shifter", [
        EffectParam("dry_wet", "Dry/Wet", 0, 127, 0),
        EffectParam("duration_tempo_sync", "Duration Tempo Sync", 0, 1, 1,
                    _OFF_ON, ribbon_assignable=False),
        EffectParam("time_ratio", "Time Ratio", 0, 127, 2),
        EffectParam("duration", "Duration", 0, 127, 3, ribbon_assignable=False),
        EffectParam("lfo_tempo_sync", "LFO Tempo Sync", 0, 1, 4, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_frequency", "LFO Frequency", 0, 127, 5),
        EffectParam("lfo_sync_note", "LFO Sync Note", 0, 21, 6, _LFO_SYNC_NOTE),
        EffectParam("lfo_key_sync", "LFO KeySync", 0, 1, 7, _OFF_ON,
                    ribbon_assignable=False),
        EffectParam("lfo_init_phase", "LFO Init Phase", 0, 127, 8,
                    ribbon_assignable=False),
        EffectParam("lfo_waveform", "LFO Waveform", 0, 4, 9, _LFO_WAVEFORM,
                    ribbon_assignable=False),
        EffectParam("lfo_shape", "LFO Shape", 0, 127, 10, ribbon_assignable=False),
    ]),
}


def get_effect_type(type_id: int) -> EffectTypeDef | None:
    """Return the EffectTypeDef for *type_id*, or None if unknown."""
    return EFFECT_TYPES.get(type_id)
