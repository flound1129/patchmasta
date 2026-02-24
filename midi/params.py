from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ParamDef:
    name: str
    description: str
    sonic_effect: str
    min_val: int
    max_val: int
    group: str = ""
    nrpn_msb: int | None = None
    nrpn_lsb: int | None = None
    cc_number: int | None = None
    # SysEx program buffer addressing
    sysex_offset: int | None = None
    sysex_signed: bool = False
    sysex_bit: int | None = None      # bit position within byte (for single-bit params)
    sysex_bit_mask: int | None = None  # bitmask for multi-bit fields sharing a byte
    sysex_bit_shift: int = 0           # right-shift applied after masking (for nibble fields)
    sysex_value_bias: int = 0          # added to SysEx value when reading (subtracted when writing)
    sysex_value_map: dict[int, int] | None = None  # NRPN→SysEx mapping; inverted for reads
    # Display metadata
    display_name: str = ""
    section: str = ""
    timbre: int | None = None  # 1 or 2, None for common params
    value_labels: dict[int, str] | None = None

    @property
    def is_nrpn(self) -> bool:
        return self.nrpn_msb is not None and self.nrpn_lsb is not None

    @property
    def is_sysex_only(self) -> bool:
        return self.sysex_offset is not None and not self.is_nrpn and self.cc_number is None

    def build_message(self, channel: int, value: int) -> list[int]:
        value = max(self.min_val, min(self.max_val, value))
        ch = (channel - 1) & 0x0F
        if self.nrpn_msb is not None and self.nrpn_lsb is not None:
            return [
                0xB0 | ch, 99, self.nrpn_msb,
                0xB0 | ch, 98, self.nrpn_lsb,
                0xB0 | ch, 6, value & 0x7F,
            ]
        if self.cc_number is not None:
            return [0xB0 | ch, self.cc_number, value & 0x7F]
        raise ValueError(f"No MIDI address for parameter '{self.name}'")


# ---------------------------------------------------------------------------
# Parameter definitions
# ---------------------------------------------------------------------------

_PARAMS: list[ParamDef] = [
    # -----------------------------------------------------------------------
    # Arpeggiator (NRPN, MSB=0x00)
    # -----------------------------------------------------------------------
    ParamDef("arp_on_off", "Arpeggiator on/off", "Enables/disables the arpeggiator",
             0, 127, group="arpeggiator", section="arpeggiator",
             nrpn_msb=0x00, nrpn_lsb=0x02,
             sysex_offset=385, sysex_bit=7,  # confirmed empirically 2026-02-23
             value_labels={0: "Off", 64: "On"}),
    ParamDef("arp_latch", "Arpeggiator latch", "Holds the arpeggio after releasing keys",
             0, 127, group="arpeggiator", section="arpeggiator",
             nrpn_msb=0x00, nrpn_lsb=0x04,
             sysex_offset=388, sysex_bit=7,  # confirmed empirically 2026-02-23
             value_labels={0: "Off", 64: "On"}),
    ParamDef("arp_type", "Arpeggiator type", "Pattern: Up, Down, Alt1, Alt2, Random, Trigger",
             0, 127, group="arpeggiator", section="arpeggiator",
             nrpn_msb=0x00, nrpn_lsb=0x07,
             sysex_offset=387, sysex_bit_mask=0x07,  # bits 0-2; confirmed empirically 2026-02-23
             sysex_value_map={0: 0, 22: 1, 43: 2, 64: 3, 86: 4, 107: 5},
             value_labels={0: "Up", 22: "Down", 43: "Alt1", 64: "Alt2", 86: "Random", 107: "Trigger"}),
    ParamDef("arp_gate", "Arpeggiator gate time", "Duration of each arpeggio note",
             0, 127, group="arpeggiator", section="arpeggiator",
             sysex_offset=389,
             nrpn_msb=0x00, nrpn_lsb=0x0A),
    ParamDef("arp_select", "Arpeggiator timbre select", "Which timbre the arp applies to",
             0, 127, group="arpeggiator", section="arpeggiator",
             nrpn_msb=0x00, nrpn_lsb=0x0B,
             sysex_offset=8, sysex_bit_mask=0x30, sysex_bit_shift=4,  # bits 4-5; confirmed 2026-02-23
             sysex_value_map={0: 0, 43: 1, 86: 2},
             value_labels={0: "Timbre 1", 43: "Timbre 2", 86: "Timbre 1+2"}),

    # -----------------------------------------------------------------------
    # Voice Mode (NRPN, MSB=0x05)
    # -----------------------------------------------------------------------
    ParamDef("voice_mode", "Voice mode", "Single/Layer/Split/Multi timbre mode",
             0, 127, group="voice", section="common",
             nrpn_msb=0x05, nrpn_lsb=0x00,
             sysex_offset=8,
             value_labels={0: "Single", 32: "Layer", 64: "Split", 96: "Multi"}),

    # -----------------------------------------------------------------------
    # Virtual Patch Source/Dest (NRPN, MSB=0x04)
    # -----------------------------------------------------------------------
    ParamDef("patch1_source", "Virtual Patch 1 source", "Modulation source for patch 1",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=103,
             nrpn_msb=0x04, nrpn_lsb=0x00),
    ParamDef("patch2_source", "Virtual Patch 2 source", "Modulation source for patch 2",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=107,
             nrpn_msb=0x04, nrpn_lsb=0x01),
    ParamDef("patch3_source", "Virtual Patch 3 source", "Modulation source for patch 3",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=110,
             nrpn_msb=0x04, nrpn_lsb=0x02),
    ParamDef("patch4_source", "Virtual Patch 4 source", "Modulation source for patch 4",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=114,
             nrpn_msb=0x04, nrpn_lsb=0x03),
    ParamDef("patch5_source", "Virtual Patch 5 source", "Modulation source for patch 5",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=117,
             nrpn_msb=0x04, nrpn_lsb=0x04),
    ParamDef("patch1_dest", "Virtual Patch 1 destination", "Parameter modulated by patch 1",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=105,
             nrpn_msb=0x04, nrpn_lsb=0x08),
    ParamDef("patch2_dest", "Virtual Patch 2 destination", "Parameter modulated by patch 2",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=108,
             nrpn_msb=0x04, nrpn_lsb=0x09),
    ParamDef("patch3_dest", "Virtual Patch 3 destination", "Parameter modulated by patch 3",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=111,
             nrpn_msb=0x04, nrpn_lsb=0x0A),
    ParamDef("patch4_dest", "Virtual Patch 4 destination", "Parameter modulated by patch 4",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=115,
             nrpn_msb=0x04, nrpn_lsb=0x0B),
    ParamDef("patch5_dest", "Virtual Patch 5 destination", "Parameter modulated by patch 5",
             0, 127, group="virtual_patch", section="virtual_patch",
             sysex_offset=118,
             nrpn_msb=0x04, nrpn_lsb=0x0C),

    # -----------------------------------------------------------------------
    # Vocoder (NRPN)
    # -----------------------------------------------------------------------
    ParamDef("vocoder_sw", "Vocoder on/off", "Enables/disables the vocoder",
             0, 127, group="vocoder", section="vocoder",
             nrpn_msb=0x05, nrpn_lsb=0x04,
             sysex_offset=232,
             value_labels={0: "Off", 64: "On"}),
    ParamDef("vocoder_fc_mod_source", "Vocoder Fc Mod Source",
             "Modulation source for vocoder carrier band-pass filter",
             0, 127, group="vocoder", section="vocoder",
             nrpn_msb=0x04, nrpn_lsb=0x00,
             sysex_offset=103,
             value_labels={0: "Filter EG", 11: "AMP EG", 21: "Assignable EG",
                           32: "LFO1", 43: "LFO2", 53: "Velocity",
                           64: "Short Ribbon (Pitch)", 75: "Short Ribbon (Mod)",
                           85: "Keyboard Track", 96: "MIDI Control 1",
                           107: "MIDI Control 2", 117: "MIDI Control 3"}),

    # Vocoder Band Level 1-16 (NRPN MSB=0x04, LSB=0x40..0x4F)
    # sysex_offset: pack_offset(logical=i*2+9, base=237, k=6)
    *[ParamDef(f"vocoder_level_{i+1}", f"Vocoder band {i+1} level",
               f"Output level of vocoder band {i+1}",
               0, 127, group="vocoder", section="vocoder_band",
               nrpn_msb=0x04, nrpn_lsb=0x40 + i,
               sysex_offset=237 + i*2+9 + (i*2+9 + 12) // 7)
      for i in range(16)],

    # Vocoder Band Pan 1-16 (NRPN MSB=0x04, LSB=0x50..0x5F)
    # sysex_offset: pack_offset(logical=i*2+8, base=237, k=6)
    *[ParamDef(f"vocoder_pan_{i+1}", f"Vocoder band {i+1} pan",
               f"Panning of vocoder band {i+1}",
               0, 127, group="vocoder", section="vocoder_band",
               nrpn_msb=0x04, nrpn_lsb=0x50 + i,
               sysex_offset=237 + i*2+8 + (i*2+8 + 12) // 7)
      for i in range(16)],

    # -----------------------------------------------------------------------
    # Virtual Patch Intensity (SysEx-only)
    # sysex_offset: pack_offset(logical=76+(i-1)*3, base=18, k=3)
    # -----------------------------------------------------------------------
    *[ParamDef(f"patch{i}_intensity", f"Virtual Patch {i} intensity",
               f"Modulation depth for virtual patch {i}",
               -63, 63, group="virtual_patch", section="virtual_patch",
               sysex_signed=True,
               sysex_offset=18 + 76+(i-1)*3 + (76+(i-1)*3 + 9) // 7,
               display_name=f"Patch {i} Intensity")
      for i in range(1, 6)],

    # -----------------------------------------------------------------------
    # Timbre 1: OSCILLATOR 1  (SysEx-only)
    # -----------------------------------------------------------------------
    ParamDef("t1_osc1_wave", "OSC1 Wave", "Selects the waveform for oscillator 1",
             0, 7, group="oscillator", section="osc1", timbre=1,
             display_name="Wave",
             sysex_offset=37,
             value_labels={0: "Saw", 1: "Pulse", 2: "Triangle", 3: "Sine",
                           4: "Formant", 5: "Noise", 6: "PCM/DWGS", 7: "Audio In"}),
    ParamDef("t1_osc1_osc_mod", "OSC1 Mod type", "Modulation type applied to OSC1",
             0, 3, group="oscillator", section="osc1", timbre=1,
             display_name="OSC Mod",
             sysex_offset=37,
             value_labels={0: "Waveform", 1: "Cross", 2: "Unison", 3: "VPM"}),
    ParamDef("t1_osc1_control1", "OSC1 Control 1", "Context-dependent control for OSC1",
             0, 127, group="oscillator", section="osc1", timbre=1,
             sysex_offset=38,
             display_name="Control 1"),
    ParamDef("t1_osc1_control2", "OSC1 Control 2", "Context-dependent control for OSC1",
             0, 127, group="oscillator", section="osc1", timbre=1,
             sysex_offset=39,
             display_name="Control 2"),
    ParamDef("t1_osc1_wave_select", "OSC1 PCM/DWGS Wave Select",
             "Selects PCM/DWGS waveform when Wave is PCM/DWGS",
             0, 63, group="oscillator", section="osc1", timbre=1,
             sysex_offset=41,
             display_name="Wave Select"),

    # -----------------------------------------------------------------------
    # Timbre 1: OSCILLATOR 2
    # -----------------------------------------------------------------------
    ParamDef("t1_osc2_wave", "OSC2 Wave", "Selects the waveform for oscillator 2",
             0, 3, group="oscillator", section="osc2", timbre=1,
             display_name="Wave",
             sysex_offset=43,
             value_labels={0: "Saw", 1: "Pulse", 2: "Triangle", 3: "Sine"}),
    ParamDef("t1_osc2_osc_mod", "OSC2 Mod type", "Oscillator 2 modulation type",
             0, 4, group="oscillator", section="osc2", timbre=1,
             display_name="OSC Mod",
             sysex_offset=43,
             value_labels={0: "Off", 1: "Ring", 2: "Sync", 3: "Ring+Sync"}),
    ParamDef("t1_osc2_semitone", "OSC2 Semitone", "Pitch offset in semitones for OSC2",
             -24, 24, group="oscillator", section="osc2", timbre=1,
             sysex_offset=44,
             sysex_signed=True, display_name="Semitone"),
    ParamDef("t1_osc2_tune", "OSC2 Tune", "Fine detune for OSC2 relative to OSC1",
             -63, 63, group="oscillator", section="osc2", timbre=1,
             sysex_offset=45,
             sysex_signed=True, display_name="Tune"),

    # -----------------------------------------------------------------------
    # Timbre 1: MIXER
    # -----------------------------------------------------------------------
    ParamDef("t1_mixer_osc1", "Mixer OSC1 level", "Output level of oscillator 1",
             0, 127, group="mixer", section="mixer", timbre=1,
             sysex_offset=46,
             display_name="OSC1"),
    ParamDef("t1_mixer_osc2", "Mixer OSC2 level", "Output level of oscillator 2",
             0, 127, group="mixer", section="mixer", timbre=1,
             sysex_offset=47,
             display_name="OSC2"),
    ParamDef("t1_mixer_noise", "Mixer Noise level", "Output level of noise generator",
             0, 127, group="mixer", section="mixer", timbre=1,
             sysex_offset=49,
             display_name="Noise"),
    ParamDef("t1_mixer_punch", "Mixer Punch level", "Punch (attack emphasis) level",
             0, 127, group="mixer", section="mixer", timbre=1,
             sysex_offset=71,
             display_name="Punch Level"),

    # -----------------------------------------------------------------------
    # Timbre 1: FILTER 1
    # -----------------------------------------------------------------------
    ParamDef("t1_filter1_balance", "Filter 1 Balance/Type", "Filter type selector",
             0, 127, group="filter", section="filter1", timbre=1,
             display_name="Balance",
             sysex_offset=52,
             value_labels={0: "LPF24", 32: "LPF12", 64: "HPF", 96: "BPF", 127: "THRU"}),
    ParamDef("t1_filter1_cutoff", "Filter 1 Cutoff", "Filter cutoff frequency",
             0, 127, group="filter", section="filter1", timbre=1,
             sysex_offset=53,
             display_name="Cutoff"),
    ParamDef("t1_filter1_resonance", "Filter 1 Resonance", "Filter resonance amount",
             0, 127, group="filter", section="filter1", timbre=1,
             sysex_offset=54,
             display_name="Resonance"),
    ParamDef("t1_filter1_eg_int", "Filter 1 EG Intensity", "Envelope depth on filter cutoff",
             -63, 63, group="filter", section="filter1", timbre=1,
             sysex_offset=55,
             sysex_signed=True, display_name="EG Int"),
    ParamDef("t1_filter1_key_track", "Filter 1 Key Track", "Keyboard tracking on filter cutoff",
             -63, 63, group="filter", section="filter1", timbre=1,
             sysex_offset=57,
             sysex_signed=True, display_name="Key Track"),
    ParamDef("t1_filter1_velo_sens", "Filter 1 Velocity Sensitivity", "Velocity effect on cutoff",
             -63, 63, group="filter", section="filter1", timbre=1,
             sysex_offset=58,
             sysex_signed=True, display_name="Velo Sens"),

    # -----------------------------------------------------------------------
    # Timbre 1: FILTER 2
    # -----------------------------------------------------------------------
    ParamDef("t1_filter2_type", "Filter 2 Type", "Filter 2 type selector",
             0, 2, group="filter", section="filter2", timbre=1,
             display_name="Type",
             sysex_offset=51,
             value_labels={0: "LPF", 1: "HPF", 2: "BPF"}),
    ParamDef("t1_filter2_cutoff", "Filter 2 Cutoff", "Filter 2 cutoff frequency",
             0, 127, group="filter", section="filter2", timbre=1,
             sysex_offset=59,
             display_name="Cutoff"),
    ParamDef("t1_filter2_resonance", "Filter 2 Resonance", "Filter 2 resonance amount",
             0, 127, group="filter", section="filter2", timbre=1,
             sysex_offset=60,
             display_name="Resonance"),
    ParamDef("t1_filter2_eg_int", "Filter 2 EG Intensity", "Envelope depth on filter 2 cutoff",
             -63, 63, group="filter", section="filter2", timbre=1,
             sysex_offset=61,
             sysex_signed=True, display_name="EG Int"),
    ParamDef("t1_filter2_key_track", "Filter 2 Key Track", "Keyboard tracking on filter 2 cutoff",
             -63, 63, group="filter", section="filter2", timbre=1,
             sysex_offset=62,
             sysex_signed=True, display_name="Key Track"),
    ParamDef("t1_filter2_velo_sens", "Filter 2 Velocity Sensitivity", "Velocity effect on filter 2 cutoff",
             -63, 63, group="filter", section="filter2", timbre=1,
             sysex_offset=63,
             sysex_signed=True, display_name="Velo Sens"),

    # -----------------------------------------------------------------------
    # Timbre 1: FILTER ROUTING
    # -----------------------------------------------------------------------
    ParamDef("t1_filter_routing", "Filter Routing", "Connection between filter 1 and 2",
             0, 3, group="filter", section="filter_routing", timbre=1,
             display_name="Filter Routing",
             sysex_offset=51,
             value_labels={0: "Single", 1: "Serial", 2: "Parallel", 3: "Individual"}),

    # -----------------------------------------------------------------------
    # Timbre 1: AMP
    # -----------------------------------------------------------------------
    ParamDef("t1_amp_level", "AMP Level", "Timbre volume level",
             0, 127, group="amp", section="amp", timbre=1,
             sysex_offset=65,
             display_name="Level"),
    ParamDef("t1_amp_pan", "AMP Pan", "Stereo position (L63..CNT..R63)",
             0, 127, group="amp", section="amp", timbre=1,
             sysex_offset=66,
             display_name="Pan"),
    ParamDef("t1_amp_key_track", "AMP Key Track", "Keyboard tracking on volume",
             -63, 63, group="amp", section="amp", timbre=1,
             sysex_offset=70,
             sysex_signed=True, display_name="Key Track"),
    ParamDef("t1_amp_ws_depth", "Wave Shape Depth", "Drive/waveshaping depth",
             0, 127, group="amp", section="amp", timbre=1,
             sysex_offset=68,
             display_name="WS Depth"),
    ParamDef("t1_amp_ws_type", "Wave Shape Type", "Wave shaping type",
             0, 10, group="amp", section="amp", timbre=1,
             display_name="WS Type",
             sysex_offset=67,
             value_labels={0: "Off", 1: "Drive", 2: "Hard Clip", 3: "Oct Saw",
                           4: "Multi Tri", 5: "Multi Sin", 6: "SubOSC Saw",
                           7: "SubOSC Squ", 8: "SubOSC Tri", 9: "SubOSC Sin",
                           10: "Level Boost"}),
    ParamDef("t1_amp_ws_position", "Wave Shape Position", "Pre-filter or pre-amp",
             0, 1, group="amp", section="amp", timbre=1,
             display_name="WS Position",
             sysex_offset=71,
             value_labels={0: "Pre Filter1", 1: "Pre AMP"}),

    # -----------------------------------------------------------------------
    # Timbre 1: FILTER EG
    # -----------------------------------------------------------------------
    ParamDef("t1_filter_eg_attack", "Filter EG Attack", "Filter EG attack time",
             0, 127, group="envelope", section="filter_eg", timbre=1,
             sysex_offset=74,
             display_name="Attack"),
    ParamDef("t1_filter_eg_decay", "Filter EG Decay", "Filter EG decay time",
             0, 127, group="envelope", section="filter_eg", timbre=1,
             sysex_offset=75,
             display_name="Decay"),
    ParamDef("t1_filter_eg_sustain", "Filter EG Sustain", "Filter EG sustain level",
             0, 127, group="envelope", section="filter_eg", timbre=1,
             sysex_offset=76,
             display_name="Sustain"),
    ParamDef("t1_filter_eg_release", "Filter EG Release", "Filter EG release time",
             0, 127, group="envelope", section="filter_eg", timbre=1,
             sysex_offset=77,
             display_name="Release"),
    ParamDef("t1_filter_eg_velo", "Filter EG Velocity", "Velocity sensitivity on filter EG",
             -63, 63, group="envelope", section="filter_eg", timbre=1,
             sysex_offset=78,
             sysex_signed=True, display_name="Lv.Velo"),

    # -----------------------------------------------------------------------
    # Timbre 1: AMP EG
    # -----------------------------------------------------------------------
    ParamDef("t1_amp_eg_attack", "AMP EG Attack", "AMP EG attack time",
             0, 127, group="envelope", section="amp_eg", timbre=1,
             sysex_offset=81,
             display_name="Attack"),
    ParamDef("t1_amp_eg_decay", "AMP EG Decay", "AMP EG decay time",
             0, 127, group="envelope", section="amp_eg", timbre=1,
             sysex_offset=82,
             display_name="Decay"),
    ParamDef("t1_amp_eg_sustain", "AMP EG Sustain", "AMP EG sustain level",
             0, 127, group="envelope", section="amp_eg", timbre=1,
             sysex_offset=83,
             display_name="Sustain"),
    ParamDef("t1_amp_eg_release", "AMP EG Release", "AMP EG release time",
             0, 127, group="envelope", section="amp_eg", timbre=1,
             sysex_offset=84,
             display_name="Release"),
    ParamDef("t1_amp_eg_velo", "AMP EG Velocity", "Velocity sensitivity on AMP EG",
             -63, 63, group="envelope", section="amp_eg", timbre=1,
             sysex_offset=85,
             sysex_signed=True, display_name="Lv.Velo"),

    # -----------------------------------------------------------------------
    # Timbre 1: ASSIGNABLE EG
    # -----------------------------------------------------------------------
    ParamDef("t1_assign_eg_attack", "Assignable EG Attack", "Assignable EG attack time",
             0, 127, group="envelope", section="assign_eg", timbre=1,
             sysex_offset=87,
             display_name="Attack"),
    ParamDef("t1_assign_eg_decay", "Assignable EG Decay", "Assignable EG decay time",
             0, 127, group="envelope", section="assign_eg", timbre=1,
             sysex_offset=89,
             display_name="Decay"),
    ParamDef("t1_assign_eg_sustain", "Assignable EG Sustain", "Assignable EG sustain level",
             0, 127, group="envelope", section="assign_eg", timbre=1,
             sysex_offset=90,
             display_name="Sustain"),
    ParamDef("t1_assign_eg_release", "Assignable EG Release", "Assignable EG release time",
             0, 127, group="envelope", section="assign_eg", timbre=1,
             sysex_offset=91,
             display_name="Release"),
    ParamDef("t1_assign_eg_velo", "Assignable EG Velocity", "Velocity sensitivity on Assignable EG",
             -63, 63, group="envelope", section="assign_eg", timbre=1,
             sysex_offset=92,
             sysex_signed=True, display_name="Lv.Velo"),

    # -----------------------------------------------------------------------
    # Timbre 1: LFO1
    # -----------------------------------------------------------------------
    ParamDef("t1_lfo1_wave", "LFO1 Wave", "LFO1 waveform shape",
             0, 4, group="lfo", section="lfo1", timbre=1,
             display_name="Wave",
             sysex_offset=94,
             value_labels={0: "Saw", 1: "Square", 2: "Triangle", 3: "S&H", 4: "Random"}),
    ParamDef("t1_lfo1_key_sync", "LFO1 Key Sync", "LFO1 key sync mode",
             0, 2, group="lfo", section="lfo1", timbre=1,
             display_name="Key Sync",
             sysex_offset=97,
             value_labels={0: "Off", 1: "Timbre", 2: "Voice"}),
    ParamDef("t1_lfo1_bpm_sync", "LFO1 BPM Sync", "LFO1 tempo sync on/off",
             0, 1, group="lfo", section="lfo1", timbre=1,
             display_name="BPM Sync",
             sysex_offset=97,
             value_labels={0: "Off", 1: "On"}),
    ParamDef("t1_lfo1_freq", "LFO1 Frequency", "LFO1 speed",
             0, 127, group="lfo", section="lfo1", timbre=1,
             sysex_offset=95,
             display_name="Frequency"),
    ParamDef("t1_lfo1_sync_note", "LFO1 Sync Note", "LFO1 sync note value",
             0, 14, group="lfo", section="lfo1", timbre=1,
             sysex_offset=98,
             display_name="Sync Note"),

    # -----------------------------------------------------------------------
    # Timbre 1: LFO2
    # -----------------------------------------------------------------------
    ParamDef("t1_lfo2_wave", "LFO2 Wave", "LFO2 waveform shape",
             0, 4, group="lfo", section="lfo2", timbre=1,
             display_name="Wave",
             sysex_offset=99,
             value_labels={0: "Saw", 1: "Square+", 2: "Sine", 3: "S&H", 4: "Random"}),
    ParamDef("t1_lfo2_key_sync", "LFO2 Key Sync", "LFO2 key sync mode",
             0, 2, group="lfo", section="lfo2", timbre=1,
             display_name="Key Sync",
             sysex_offset=101,
             value_labels={0: "Off", 1: "Timbre", 2: "Voice"}),
    ParamDef("t1_lfo2_bpm_sync", "LFO2 BPM Sync", "LFO2 tempo sync on/off",
             0, 1, group="lfo", section="lfo2", timbre=1,
             display_name="BPM Sync",
             sysex_offset=101,
             value_labels={0: "Off", 1: "On"}),
    ParamDef("t1_lfo2_freq", "LFO2 Frequency", "LFO2 speed",
             0, 127, group="lfo", section="lfo2", timbre=1,
             sysex_offset=100,
             display_name="Frequency"),
    ParamDef("t1_lfo2_sync_note", "LFO2 Sync Note", "LFO2 sync note value",
             0, 14, group="lfo", section="lfo2", timbre=1,
             sysex_offset=102,
             display_name="Sync Note"),

    # -----------------------------------------------------------------------
    # Timbre 1: VOICE
    # -----------------------------------------------------------------------
    ParamDef("t1_voice_assign", "Voice Assign", "How notes are articulated",
             0, 2, group="voice_settings", section="voice_settings", timbre=1,
             display_name="Voice Assign",
             sysex_offset=27,
             value_labels={0: "Mono1", 1: "Mono2", 2: "Poly"}),
    ParamDef("t1_unison_sw", "Unison Switch", "Unison on/off and voice count",
             0, 3, group="voice_settings", section="voice_settings", timbre=1,
             display_name="Unison SW",
             sysex_offset=23,
             value_labels={0: "Off", 1: "2 Voice", 2: "3 Voice", 3: "4 Voice"}),
    ParamDef("t1_unison_detune", "Unison Detune", "Detuning amount between unison voices",
             0, 99, group="voice_settings", section="voice_settings", timbre=1,
             sysex_offset=25,
             display_name="Unison Detune"),
    ParamDef("t1_unison_spread", "Unison Spread", "Stereo spread of unison voices",
             0, 127, group="voice_settings", section="voice_settings", timbre=1,
             sysex_offset=26,
             display_name="Unison Spread"),
    ParamDef("t1_analog_tuning", "Analog Tuning", "Random pitch drift amount",
             0, 127, group="voice_settings", section="voice_settings", timbre=1,
             sysex_offset=29,
             display_name="Analog Tuning"),

    # -----------------------------------------------------------------------
    # Timbre 1: PITCH
    # -----------------------------------------------------------------------
    ParamDef("t1_transpose", "Transpose", "Pitch offset in semitones",
             -48, 48, group="pitch", section="pitch", timbre=1,
             sysex_offset=30,
             sysex_signed=True, display_name="Transpose"),
    ParamDef("t1_bend_range", "Bend Range", "Pitch bend range in semitones",
             -12, 12, group="pitch", section="pitch", timbre=1,
             sysex_offset=34,
             sysex_signed=True, display_name="Bend Range"),
    ParamDef("t1_detune", "Detune", "Fine pitch adjustment in cents",
             -50, 50, group="pitch", section="pitch", timbre=1,
             sysex_offset=31,
             sysex_signed=True, display_name="Detune"),
    ParamDef("t1_vibrato_int", "Vibrato Intensity", "Vibrato depth via short ribbon",
             0, 127, group="pitch", section="pitch", timbre=1,
             sysex_offset=33,
             display_name="Vibrato Int"),
    ParamDef("t1_portamento", "Portamento Time", "Portamento glide speed",
             0, 127, group="pitch", section="pitch", timbre=1,
             sysex_offset=35,
             display_name="Portamento"),

    # -----------------------------------------------------------------------
    # Timbre 1: TIMBRE EQ
    # -----------------------------------------------------------------------
    ParamDef("t1_eq_low_freq", "EQ Low Frequency", "Low band EQ frequency",
             0, 127, group="eq", section="eq", timbre=1,
             sysex_offset=124,
             display_name="Low Freq"),
    ParamDef("t1_eq_low_gain", "EQ Low Gain", "Low band EQ gain",
             -63, 63, group="eq", section="eq", timbre=1,
             sysex_offset=125,
             sysex_signed=True, display_name="Low Gain"),
    ParamDef("t1_eq_high_freq", "EQ High Frequency", "High band EQ frequency",
             0, 127, group="eq", section="eq", timbre=1,
             sysex_offset=126,
             display_name="High Freq"),
    ParamDef("t1_eq_high_gain", "EQ High Gain", "High band EQ gain",
             -63, 63, group="eq", section="eq", timbre=1,
             sysex_offset=127,
             sysex_signed=True, display_name="High Gain"),

    # -----------------------------------------------------------------------
    # Timbre 2: OSCILLATOR 1
    # -----------------------------------------------------------------------
    ParamDef("t2_osc1_wave", "T2 OSC1 Wave", "Selects the waveform for oscillator 1",
             0, 7, group="oscillator", section="osc1", timbre=2,
             display_name="Wave",
             sysex_offset=147,
             value_labels={0: "Saw", 1: "Pulse", 2: "Triangle", 3: "Sine",
                           4: "Formant", 5: "Noise", 6: "PCM/DWGS", 7: "Audio In"}),
    ParamDef("t2_osc1_osc_mod", "T2 OSC1 Mod type", "Modulation type applied to OSC1",
             0, 3, group="oscillator", section="osc1", timbre=2,
             display_name="OSC Mod",
             sysex_offset=147,
             value_labels={0: "Waveform", 1: "Cross", 2: "Unison", 3: "VPM"}),
    ParamDef("t2_osc1_control1", "T2 OSC1 Control 1", "Context-dependent control for OSC1",
             0, 127, group="oscillator", section="osc1", timbre=2,
             sysex_offset=148,
             display_name="Control 1"),
    ParamDef("t2_osc1_control2", "T2 OSC1 Control 2", "Context-dependent control for OSC1",
             0, 127, group="oscillator", section="osc1", timbre=2,
             sysex_offset=149,
             display_name="Control 2"),
    ParamDef("t2_osc1_wave_select", "T2 OSC1 PCM/DWGS Wave Select",
             "Selects PCM/DWGS waveform when Wave is PCM/DWGS",
             0, 63, group="oscillator", section="osc1", timbre=2,
             sysex_offset=150,
             display_name="Wave Select"),

    # -----------------------------------------------------------------------
    # Timbre 2: OSCILLATOR 2
    # -----------------------------------------------------------------------
    ParamDef("t2_osc2_wave", "T2 OSC2 Wave", "Selects the waveform for oscillator 2",
             0, 3, group="oscillator", section="osc2", timbre=2,
             display_name="Wave",
             sysex_offset=153,
             value_labels={0: "Saw", 1: "Pulse", 2: "Triangle", 3: "Sine"}),
    ParamDef("t2_osc2_osc_mod", "T2 OSC2 Mod type", "Oscillator 2 modulation type",
             0, 4, group="oscillator", section="osc2", timbre=2,
             display_name="OSC Mod",
             sysex_offset=153,
             value_labels={0: "Off", 1: "Ring", 2: "Sync", 3: "Ring+Sync"}),
    ParamDef("t2_osc2_semitone", "T2 OSC2 Semitone", "Pitch offset in semitones for OSC2",
             -24, 24, group="oscillator", section="osc2", timbre=2,
             sysex_offset=154,
             sysex_signed=True, display_name="Semitone"),
    ParamDef("t2_osc2_tune", "T2 OSC2 Tune", "Fine detune for OSC2 relative to OSC1",
             -63, 63, group="oscillator", section="osc2", timbre=2,
             sysex_offset=155,
             sysex_signed=True, display_name="Tune"),

    # -----------------------------------------------------------------------
    # Timbre 2: MIXER
    # -----------------------------------------------------------------------
    ParamDef("t2_mixer_osc1", "T2 Mixer OSC1 level", "Output level of oscillator 1",
             0, 127, group="mixer", section="mixer", timbre=2,
             sysex_offset=156,
             display_name="OSC1"),
    ParamDef("t2_mixer_osc2", "T2 Mixer OSC2 level", "Output level of oscillator 2",
             0, 127, group="mixer", section="mixer", timbre=2,
             sysex_offset=157,
             display_name="OSC2"),
    ParamDef("t2_mixer_noise", "T2 Mixer Noise level", "Output level of noise generator",
             0, 127, group="mixer", section="mixer", timbre=2,
             sysex_offset=158,
             display_name="Noise"),
    ParamDef("t2_mixer_punch", "T2 Mixer Punch level", "Punch (attack emphasis) level",
             0, 127, group="mixer", section="mixer", timbre=2,
             sysex_offset=181,
             display_name="Punch Level"),

    # -----------------------------------------------------------------------
    # Timbre 2: FILTER 1
    # -----------------------------------------------------------------------
    ParamDef("t2_filter1_balance", "T2 Filter 1 Balance/Type", "Filter type selector",
             0, 127, group="filter", section="filter1", timbre=2,
             display_name="Balance",
             sysex_offset=162,
             value_labels={0: "LPF24", 32: "LPF12", 64: "HPF", 96: "BPF", 127: "THRU"}),
    ParamDef("t2_filter1_cutoff", "T2 Filter 1 Cutoff", "Filter cutoff frequency",
             0, 127, group="filter", section="filter1", timbre=2,
             sysex_offset=163,
             display_name="Cutoff"),
    ParamDef("t2_filter1_resonance", "T2 Filter 1 Resonance", "Filter resonance amount",
             0, 127, group="filter", section="filter1", timbre=2,
             sysex_offset=164,
             display_name="Resonance"),
    ParamDef("t2_filter1_eg_int", "T2 Filter 1 EG Intensity", "Envelope depth on filter cutoff",
             -63, 63, group="filter", section="filter1", timbre=2,
             sysex_offset=165,
             sysex_signed=True, display_name="EG Int"),
    ParamDef("t2_filter1_key_track", "T2 Filter 1 Key Track", "Keyboard tracking on filter cutoff",
             -63, 63, group="filter", section="filter1", timbre=2,
             sysex_offset=166,
             sysex_signed=True, display_name="Key Track"),
    ParamDef("t2_filter1_velo_sens", "T2 Filter 1 Velocity Sensitivity", "Velocity effect on cutoff",
             -63, 63, group="filter", section="filter1", timbre=2,
             sysex_offset=167,
             sysex_signed=True, display_name="Velo Sens"),

    # -----------------------------------------------------------------------
    # Timbre 2: FILTER 2
    # -----------------------------------------------------------------------
    ParamDef("t2_filter2_type", "T2 Filter 2 Type", "Filter 2 type selector",
             0, 2, group="filter", section="filter2", timbre=2,
             display_name="Type",
             sysex_offset=161,
             value_labels={0: "LPF", 1: "HPF", 2: "BPF"}),
    ParamDef("t2_filter2_cutoff", "T2 Filter 2 Cutoff", "Filter 2 cutoff frequency",
             0, 127, group="filter", section="filter2", timbre=2,
             sysex_offset=169,
             display_name="Cutoff"),
    ParamDef("t2_filter2_resonance", "T2 Filter 2 Resonance", "Filter 2 resonance amount",
             0, 127, group="filter", section="filter2", timbre=2,
             sysex_offset=170,
             display_name="Resonance"),
    ParamDef("t2_filter2_eg_int", "T2 Filter 2 EG Intensity", "Envelope depth on filter 2 cutoff",
             -63, 63, group="filter", section="filter2", timbre=2,
             sysex_offset=171,
             sysex_signed=True, display_name="EG Int"),
    ParamDef("t2_filter2_key_track", "T2 Filter 2 Key Track", "Keyboard tracking on filter 2 cutoff",
             -63, 63, group="filter", section="filter2", timbre=2,
             sysex_offset=172,
             sysex_signed=True, display_name="Key Track"),
    ParamDef("t2_filter2_velo_sens", "T2 Filter 2 Velocity Sensitivity", "Velocity effect on filter 2 cutoff",
             -63, 63, group="filter", section="filter2", timbre=2,
             sysex_offset=173,
             sysex_signed=True, display_name="Velo Sens"),

    # -----------------------------------------------------------------------
    # Timbre 2: FILTER ROUTING
    # -----------------------------------------------------------------------
    ParamDef("t2_filter_routing", "T2 Filter Routing", "Connection between filter 1 and 2",
             0, 3, group="filter", section="filter_routing", timbre=2,
             display_name="Filter Routing",
             sysex_offset=161,
             value_labels={0: "Single", 1: "Serial", 2: "Parallel", 3: "Individual"}),

    # -----------------------------------------------------------------------
    # Timbre 2: AMP
    # -----------------------------------------------------------------------
    ParamDef("t2_amp_level", "T2 AMP Level", "Timbre volume level",
             0, 127, group="amp", section="amp", timbre=2,
             sysex_offset=174,
             display_name="Level"),
    ParamDef("t2_amp_pan", "T2 AMP Pan", "Stereo position",
             0, 127, group="amp", section="amp", timbre=2,
             sysex_offset=175,
             display_name="Pan"),
    ParamDef("t2_amp_key_track", "T2 AMP Key Track", "Keyboard tracking on volume",
             -63, 63, group="amp", section="amp", timbre=2,
             sysex_offset=180,
             sysex_signed=True, display_name="Key Track"),
    ParamDef("t2_amp_ws_depth", "T2 Wave Shape Depth", "Drive/waveshaping depth",
             0, 127, group="amp", section="amp", timbre=2,
             sysex_offset=178,
             display_name="WS Depth"),
    ParamDef("t2_amp_ws_type", "T2 Wave Shape Type", "Wave shaping type",
             0, 10, group="amp", section="amp", timbre=2,
             display_name="WS Type",
             sysex_offset=177,
             value_labels={0: "Off", 1: "Drive", 2: "Hard Clip", 3: "Oct Saw",
                           4: "Multi Tri", 5: "Multi Sin", 6: "SubOSC Saw",
                           7: "SubOSC Squ", 8: "SubOSC Tri", 9: "SubOSC Sin",
                           10: "Level Boost"}),
    ParamDef("t2_amp_ws_position", "T2 Wave Shape Position", "Pre-filter or pre-amp",
             0, 1, group="amp", section="amp", timbre=2,
             display_name="WS Position",
             sysex_offset=181,
             value_labels={0: "Pre Filter1", 1: "Pre AMP"}),

    # -----------------------------------------------------------------------
    # Timbre 2: FILTER EG
    # -----------------------------------------------------------------------
    ParamDef("t2_filter_eg_attack", "T2 Filter EG Attack", "Filter EG attack time",
             0, 127, group="envelope", section="filter_eg", timbre=2,
             sysex_offset=183,
             display_name="Attack"),
    ParamDef("t2_filter_eg_decay", "T2 Filter EG Decay", "Filter EG decay time",
             0, 127, group="envelope", section="filter_eg", timbre=2,
             sysex_offset=185,
             display_name="Decay"),
    ParamDef("t2_filter_eg_sustain", "T2 Filter EG Sustain", "Filter EG sustain level",
             0, 127, group="envelope", section="filter_eg", timbre=2,
             sysex_offset=186,
             display_name="Sustain"),
    ParamDef("t2_filter_eg_release", "T2 Filter EG Release", "Filter EG release time",
             0, 127, group="envelope", section="filter_eg", timbre=2,
             sysex_offset=187,
             display_name="Release"),
    ParamDef("t2_filter_eg_velo", "T2 Filter EG Velocity", "Velocity sensitivity on filter EG",
             -63, 63, group="envelope", section="filter_eg", timbre=2,
             sysex_offset=188,
             sysex_signed=True, display_name="Lv.Velo"),

    # -----------------------------------------------------------------------
    # Timbre 2: AMP EG
    # -----------------------------------------------------------------------
    ParamDef("t2_amp_eg_attack", "T2 AMP EG Attack", "AMP EG attack time",
             0, 127, group="envelope", section="amp_eg", timbre=2,
             sysex_offset=190,
             display_name="Attack"),
    ParamDef("t2_amp_eg_decay", "T2 AMP EG Decay", "AMP EG decay time",
             0, 127, group="envelope", section="amp_eg", timbre=2,
             sysex_offset=191,
             display_name="Decay"),
    ParamDef("t2_amp_eg_sustain", "T2 AMP EG Sustain", "AMP EG sustain level",
             0, 127, group="envelope", section="amp_eg", timbre=2,
             sysex_offset=193,
             display_name="Sustain"),
    ParamDef("t2_amp_eg_release", "T2 AMP EG Release", "AMP EG release time",
             0, 127, group="envelope", section="amp_eg", timbre=2,
             sysex_offset=194,
             display_name="Release"),
    ParamDef("t2_amp_eg_velo", "T2 AMP EG Velocity", "Velocity sensitivity on AMP EG",
             -63, 63, group="envelope", section="amp_eg", timbre=2,
             sysex_offset=195,
             sysex_signed=True, display_name="Lv.Velo"),

    # -----------------------------------------------------------------------
    # Timbre 2: ASSIGNABLE EG
    # -----------------------------------------------------------------------
    ParamDef("t2_assign_eg_attack", "T2 Assignable EG Attack", "Assignable EG attack time",
             0, 127, group="envelope", section="assign_eg", timbre=2,
             sysex_offset=197,
             display_name="Attack"),
    ParamDef("t2_assign_eg_decay", "T2 Assignable EG Decay", "Assignable EG decay time",
             0, 127, group="envelope", section="assign_eg", timbre=2,
             sysex_offset=198,
             display_name="Decay"),
    ParamDef("t2_assign_eg_sustain", "T2 Assignable EG Sustain", "Assignable EG sustain level",
             0, 127, group="envelope", section="assign_eg", timbre=2,
             sysex_offset=199,
             display_name="Sustain"),
    ParamDef("t2_assign_eg_release", "T2 Assignable EG Release", "Assignable EG release time",
             0, 127, group="envelope", section="assign_eg", timbre=2,
             sysex_offset=201,
             display_name="Release"),
    ParamDef("t2_assign_eg_velo", "T2 Assignable EG Velocity", "Velocity sensitivity on Assignable EG",
             -63, 63, group="envelope", section="assign_eg", timbre=2,
             sysex_offset=202,
             sysex_signed=True, display_name="Lv.Velo"),

    # -----------------------------------------------------------------------
    # Timbre 2: LFO1
    # -----------------------------------------------------------------------
    ParamDef("t2_lfo1_wave", "T2 LFO1 Wave", "LFO1 waveform shape",
             0, 4, group="lfo", section="lfo1", timbre=2,
             display_name="Wave",
             sysex_offset=204,
             value_labels={0: "Saw", 1: "Square", 2: "Triangle", 3: "S&H", 4: "Random"}),
    ParamDef("t2_lfo1_key_sync", "T2 LFO1 Key Sync", "LFO1 key sync mode",
             0, 2, group="lfo", section="lfo1", timbre=2,
             display_name="Key Sync",
             sysex_offset=206,
             value_labels={0: "Off", 1: "Timbre", 2: "Voice"}),
    ParamDef("t2_lfo1_bpm_sync", "T2 LFO1 BPM Sync", "LFO1 tempo sync on/off",
             0, 1, group="lfo", section="lfo1", timbre=2,
             display_name="BPM Sync",
             sysex_offset=206,
             value_labels={0: "Off", 1: "On"}),
    ParamDef("t2_lfo1_freq", "T2 LFO1 Frequency", "LFO1 speed",
             0, 127, group="lfo", section="lfo1", timbre=2,
             sysex_offset=205,
             display_name="Frequency"),
    ParamDef("t2_lfo1_sync_note", "T2 LFO1 Sync Note", "LFO1 sync note value",
             0, 14, group="lfo", section="lfo1", timbre=2,
             sysex_offset=207,
             display_name="Sync Note"),

    # -----------------------------------------------------------------------
    # Timbre 2: LFO2
    # -----------------------------------------------------------------------
    ParamDef("t2_lfo2_wave", "T2 LFO2 Wave", "LFO2 waveform shape",
             0, 4, group="lfo", section="lfo2", timbre=2,
             display_name="Wave",
             sysex_offset=209,
             value_labels={0: "Saw", 1: "Square+", 2: "Sine", 3: "S&H", 4: "Random"}),
    ParamDef("t2_lfo2_key_sync", "T2 LFO2 Key Sync", "LFO2 key sync mode",
             0, 2, group="lfo", section="lfo2", timbre=2,
             display_name="Key Sync",
             sysex_offset=211,
             value_labels={0: "Off", 1: "Timbre", 2: "Voice"}),
    ParamDef("t2_lfo2_bpm_sync", "T2 LFO2 BPM Sync", "LFO2 tempo sync on/off",
             0, 1, group="lfo", section="lfo2", timbre=2,
             display_name="BPM Sync",
             sysex_offset=211,
             value_labels={0: "Off", 1: "On"}),
    ParamDef("t2_lfo2_freq", "T2 LFO2 Frequency", "LFO2 speed",
             0, 127, group="lfo", section="lfo2", timbre=2,
             sysex_offset=210,
             display_name="Frequency"),
    ParamDef("t2_lfo2_sync_note", "T2 LFO2 Sync Note", "LFO2 sync note value",
             0, 14, group="lfo", section="lfo2", timbre=2,
             sysex_offset=212,
             display_name="Sync Note"),

    # -----------------------------------------------------------------------
    # Timbre 2: VOICE
    # -----------------------------------------------------------------------
    ParamDef("t2_voice_assign", "T2 Voice Assign", "How notes are articulated",
             0, 2, group="voice_settings", section="voice_settings", timbre=2,
             display_name="Voice Assign",
             sysex_offset=137,
             value_labels={0: "Mono1", 1: "Mono2", 2: "Poly"}),
    ParamDef("t2_unison_sw", "T2 Unison Switch", "Unison on/off and voice count",
             0, 3, group="voice_settings", section="voice_settings", timbre=2,
             display_name="Unison SW",
             sysex_offset=133,
             value_labels={0: "Off", 1: "2 Voice", 2: "3 Voice", 3: "4 Voice"}),
    ParamDef("t2_unison_detune", "T2 Unison Detune", "Detuning amount between unison voices",
             0, 99, group="voice_settings", section="voice_settings", timbre=2,
             sysex_offset=134,
             display_name="Unison Detune"),
    ParamDef("t2_unison_spread", "T2 Unison Spread", "Stereo spread of unison voices",
             0, 127, group="voice_settings", section="voice_settings", timbre=2,
             sysex_offset=135,
             display_name="Unison Spread"),
    ParamDef("t2_analog_tuning", "T2 Analog Tuning", "Random pitch drift amount",
             0, 127, group="voice_settings", section="voice_settings", timbre=2,
             sysex_offset=139,
             display_name="Analog Tuning"),

    # -----------------------------------------------------------------------
    # Timbre 2: PITCH
    # -----------------------------------------------------------------------
    ParamDef("t2_transpose", "T2 Transpose", "Pitch offset in semitones",
             -48, 48, group="pitch", section="pitch", timbre=2,
             sysex_offset=140,
             sysex_signed=True, display_name="Transpose"),
    ParamDef("t2_bend_range", "T2 Bend Range", "Pitch bend range in semitones",
             -12, 12, group="pitch", section="pitch", timbre=2,
             sysex_offset=143,
             sysex_signed=True, display_name="Bend Range"),
    ParamDef("t2_detune", "T2 Detune", "Fine pitch adjustment in cents",
             -50, 50, group="pitch", section="pitch", timbre=2,
             sysex_offset=141,
             sysex_signed=True, display_name="Detune"),
    ParamDef("t2_vibrato_int", "T2 Vibrato Intensity", "Vibrato depth via short ribbon",
             0, 127, group="pitch", section="pitch", timbre=2,
             sysex_offset=142,
             display_name="Vibrato Int"),
    ParamDef("t2_portamento", "T2 Portamento Time", "Portamento glide speed",
             0, 127, group="pitch", section="pitch", timbre=2,
             sysex_offset=145,
             display_name="Portamento"),

    # -----------------------------------------------------------------------
    # Timbre 2: TIMBRE EQ
    # -----------------------------------------------------------------------
    ParamDef("t2_eq_low_freq", "T2 EQ Low Frequency", "Low band EQ frequency",
             0, 127, group="eq", section="eq", timbre=2,
             sysex_offset=234,
             display_name="Low Freq"),
    ParamDef("t2_eq_low_gain", "T2 EQ Low Gain", "Low band EQ gain",
             -63, 63, group="eq", section="eq", timbre=2,
             sysex_offset=235,
             sysex_signed=True, display_name="Low Gain"),
    ParamDef("t2_eq_high_freq", "T2 EQ High Frequency", "High band EQ frequency",
             0, 127, group="eq", section="eq", timbre=2,
             sysex_offset=236,
             display_name="High Freq"),
    ParamDef("t2_eq_high_gain", "T2 EQ High Gain", "High band EQ gain",
             -63, 63, group="eq", section="eq", timbre=2,
             sysex_offset=237,
             sysex_signed=True, display_name="High Gain"),

    # -----------------------------------------------------------------------
    # Arpeggiator (extended, SysEx-only)
    # -----------------------------------------------------------------------
    ParamDef("arp_octave_range", "Arp Octave Range", "Octave range for arpeggio",
             0, 127, group="arpeggiator", section="arpeggiator",
             sysex_offset=388, sysex_bit=5,  # confirmed empirically 2026-02-23; 0=3Oct, 64=2Oct (other values TBD)
             display_name="Octave Range",
             value_labels={0: "3 Oct", 64: "2 Oct"}),
    ParamDef("arp_resolution", "Arp Resolution", "Note spacing relative to tempo",
             0, 127, group="arpeggiator", section="arpeggiator",
             sysex_offset=387, sysex_bit_mask=0xF0, sysex_bit_shift=4,  # bits 4-7; confirmed 2026-02-23
             display_name="Resolution"),
    ParamDef("arp_last_step", "Arp Last Step", "Number of active steps",
             1, 8, group="arpeggiator", section="arpeggiator",
             sysex_offset=388, sysex_bit_mask=0x07, sysex_value_bias=1,  # bits 0-2, stored as value-1; confirmed 2026-02-23
             display_name="Last Step"),
    ParamDef("arp_key_sync", "Arp Key Sync", "Sync arpeggio to keyboard",
             0, 1, group="arpeggiator", section="arpeggiator",
             sysex_offset=385, sysex_bit=6,  # confirmed empirically 2026-02-23
             display_name="Key Sync",
             value_labels={0: "Off", 1: "On"}),
    ParamDef("arp_swing", "Arp Swing", "Swing amount for even-numbered notes",
             0, 127, group="arpeggiator", section="arpeggiator",
             sysex_offset=390,  # confirmed empirically 2026-02-23
             display_name="Swing"),
    # Step Edit: 8 steps on/off (all packed in single byte at Arp L6, packed 391; confirmed empirically 2026-02-23)
    *[ParamDef(f"arp_step{i}_sw", f"Arp Step {i} on/off", f"Step {i} on/off toggle",
               0, 1, group="arpeggiator", section="arpeggiator_steps",
               sysex_offset=391, sysex_bit=i - 1,
               display_name=f"Step {i}",
               value_labels={0: "Off", 1: "On"})
      for i in range(1, 9)],

    # -----------------------------------------------------------------------
    # Master Effects
    # -----------------------------------------------------------------------
    ParamDef("fx1_type", "Master Effect 1 Type", "FX1 effect type selector",
             0, 17, group="effects", section="fx1",
             display_name="FX Type",
             sysex_offset=327,  # Gap L38, confirmed empirically 2026-02-23
             value_labels={0: "Effect Off", 1: "Compressor", 2: "Filter",
                           3: "4Band EQ", 4: "Distortion", 5: "Decimator",
                           6: "Delay", 7: "L/C/R Delay", 8: "Auto Panning Delay",
                           9: "Modulation Delay", 10: "Tape Echo",
                           11: "Chorus", 12: "Flanger", 13: "Vibrato",
                           14: "Phaser", 15: "Tremolo", 16: "Ring Modulator",
                           17: "Grain Shifter"}),
    ParamDef("fx1_ribbon_assign", "FX1 Long Ribbon Assign", "Ribbon assign for FX1",
             0, 127, group="effects", section="fx1",
             sysex_offset=330,  # confirmed empirically 2026-02-23; 31=Assign Off, 0=Dry/Wet
             display_name="Ribbon Assign"),
    ParamDef("fx1_ribbon_polarity", "FX1 Long Ribbon Polarity", "Ribbon polarity for FX1",
             0, 1, group="effects", section="fx1",
             sysex_offset=331,  # confirmed empirically 2026-02-23
             display_name="Ribbon Polarity",
             value_labels={0: "Forward", 1: "Reverse"}),

    ParamDef("fx2_type", "Master Effect 2 Type", "FX2 effect type selector",
             0, 17, group="effects", section="fx2",
             display_name="FX Type",
             sysex_offset=355,  # Gap L62, confirmed empirically 2026-02-23
             value_labels={0: "Effect Off", 1: "Compressor", 2: "Filter",
                           3: "4Band EQ", 4: "Distortion", 5: "Decimator",
                           6: "Delay", 7: "L/C/R Delay", 8: "Auto Panning Delay",
                           9: "Modulation Delay", 10: "Tape Echo",
                           11: "Chorus", 12: "Flanger", 13: "Vibrato",
                           14: "Phaser", 15: "Tremolo", 16: "Ring Modulator",
                           17: "Grain Shifter"}),
    ParamDef("fx2_ribbon_assign", "FX2 Long Ribbon Assign", "Ribbon assign for FX2",
             0, 127, group="effects", section="fx2",
             sysex_offset=357,  # confirmed empirically 2026-02-23; 31=Assign Off
             display_name="Ribbon Assign"),
    ParamDef("fx2_ribbon_polarity", "FX2 Long Ribbon Polarity", "Ribbon polarity for FX2",
             0, 1, group="effects", section="fx2",
             sysex_offset=358,  # confirmed empirically 2026-02-23
             display_name="Ribbon Polarity",
             value_labels={0: "Forward", 1: "Reverse"}),

    # -----------------------------------------------------------------------
    # Vocoder (extended, SysEx-only params)
    # -----------------------------------------------------------------------
    ParamDef("vocoder_timbre1_level", "Vocoder Timbre 1 Level", "Carrier timbre 1 level",
             0, 127, group="vocoder", section="vocoder_carrier",
             sysex_offset=244,
             display_name="Timbre 1 Level"),
    ParamDef("vocoder_timbre2_level", "Vocoder Timbre 2 Level", "Carrier timbre 2 level",
             0, 127, group="vocoder", section="vocoder_carrier",
             sysex_offset=245,
             display_name="Timbre 2 Level"),
    ParamDef("vocoder_audio_source", "Vocoder Audio In Source", "Modulator audio source",
             0, 1, group="vocoder", section="vocoder_modulator",
             sysex_offset=238, sysex_bit=0,  # bits 0-2 of pk238
             display_name="Audio In Source",
             value_labels={0: "Audio Input", 1: "Timbre2"}),
    ParamDef("vocoder_gate_sens", "Vocoder Gate Sens", "Gate sensitivity",
             0, 127, group="vocoder", section="vocoder_modulator",
             sysex_offset=239,
             display_name="Gate Sens"),
    ParamDef("vocoder_gate_threshold", "Vocoder Gate Threshold", "Gate threshold level",
             0, 127, group="vocoder", section="vocoder_modulator",
             sysex_offset=241,
             display_name="Gate Threshold"),
    ParamDef("vocoder_hpf_gate", "Vocoder HPF Gate", "HPF gate enable",
             0, 1, group="vocoder", section="vocoder_modulator",
             sysex_offset=284, sysex_bit=6,  # bit 6 of pk284 (shared with fx1_type)
             display_name="HPF Gate",
             value_labels={0: "Disable", 1: "Enable"}),
    ParamDef("vocoder_hpf_level", "Vocoder HPF Level", "High-pass filter output level",
             0, 127, group="vocoder", section="vocoder_modulator",
             sysex_offset=242,
             display_name="HPF Level"),
    ParamDef("vocoder_formant_shift", "Vocoder Formant Shift", "Formant frequency shift",
             -2, 2, group="vocoder", section="vocoder_filter",
             sysex_offset=238, sysex_bit=3,  # bits 3-5 of pk238 (stored 0-4, 0=-2)
             sysex_signed=True, display_name="Formant Shift"),
    ParamDef("vocoder_fc_offset", "Vocoder FC Offset", "Carrier filter cutoff offset",
             -63, 63, group="vocoder", section="vocoder_filter",
             sysex_offset=286,
             sysex_signed=True, display_name="FC Offset"),
    ParamDef("vocoder_resonance", "Vocoder Resonance", "Carrier band-pass filter resonance",
             0, 127, group="vocoder", section="vocoder_filter",
             sysex_offset=287,
             display_name="Resonance"),
    ParamDef("vocoder_ef_sens", "Vocoder EF Sens", "Envelope follower sensitivity",
             0, 127, group="vocoder", section="vocoder_filter",
             sysex_offset=290,
             display_name="E.F.Sens"),
    ParamDef("vocoder_fc_mod_int", "Vocoder FC Mod Intensity", "Fc modulation depth",
             -63, 63, group="vocoder", section="vocoder_filter",
             sysex_offset=289,
             sysex_signed=True, display_name="FC Mod Int"),
    ParamDef("vocoder_level", "Vocoder Level", "Vocoder output level",
             0, 127, group="vocoder", section="vocoder_amp",
             sysex_offset=246,
             display_name="Vocoder Level"),
    ParamDef("vocoder_direct_level", "Vocoder Direct Level", "Dry signal level",
             0, 127, group="vocoder", section="vocoder_amp",
             sysex_offset=243,
             display_name="Direct Level"),

    # -----------------------------------------------------------------------
    # Common: Ribbon parameters
    # -----------------------------------------------------------------------
    ParamDef("long_ribbon_timbre_select", "Long Ribbon Timbre Select", "Ribbon timbre target",
             0, 2, group="ribbon", section="long_ribbon",
             sysex_offset=398, sysex_bit_mask=0xC0, sysex_bit_shift=6,  # bits 6-7; confirmed empirically 2026-02-23
             display_name="Timbre Select",
             value_labels={0: "Timbre 1", 1: "Timbre 2", 2: "Timbre 1+2"}),
    ParamDef("long_ribbon_scale_type", "Long Ribbon Scale Type", "Scale type (35 types incl. Scale Off)",
             0, 34, group="ribbon", section="long_ribbon",
             sysex_offset=398, sysex_bit_mask=0x3F,  # bits 0-5; Off=0, Chromatic=1; confirmed empirically 2026-02-23
             display_name="Scale Type"),
    ParamDef("long_ribbon_scale_key", "Long Ribbon Scale Key", "Scale key",
             0, 24, group="ribbon", section="long_ribbon",
             sysex_offset=397, sysex_bit_mask=0x7C, sysex_bit_shift=2,  # bits 2-6; confirmed empirically 2026-02-23
             # 25 items: C+(0),B+(1),A#+(2),A+(3),G#+(4),G+(5),F#+(6),F+(7),C(8),D+(9),...,C-(24)
             display_name="Scale Key"),
    ParamDef("long_ribbon_scale_range", "Long Ribbon Scale Range", "Octave range",
             65, 68, group="ribbon", section="long_ribbon",
             sysex_offset=399,  # confirmed empirically 2026-02-23; 65=1Oct,66=2Oct,67=3Oct,68=4Oct
             display_name="Scale Range",
             value_labels={65: "1 Oct", 66: "2 Oct", 67: "3 Oct", 68: "4 Oct"}),
    ParamDef("long_ribbon_pitch_range", "Long Ribbon Pitch Range", "Pitch range in octaves",
             65, 68, group="ribbon", section="long_ribbon",
             sysex_offset=401,  # confirmed empirically 2026-02-23; same encoding as scale_range
             display_name="Pitch Range",
             value_labels={65: "1 Oct", 66: "2 Oct", 67: "3 Oct", 68: "4 Oct"}),
    ParamDef("long_ribbon_filter_int", "Long Ribbon Filter Intensity", "Filter effect depth",
             -63, 63, group="ribbon", section="long_ribbon",
             sysex_offset=123,
             sysex_signed=True, display_name="Filter Int"),
    ParamDef("short_ribbon_setting", "Short Ribbon Setting", "Pitch or Modulation mode",
             0, 1, group="ribbon", section="short_ribbon",
             sysex_offset=397, sysex_bit=0,
             display_name="Setting",
             value_labels={0: "Pitch", 1: "Modulation"}),
    ParamDef("short_ribbon_mod_assign", "Short Ribbon Mod Assign", "CC number for modulation",
             0, 127, group="ribbon", section="short_ribbon",
             sysex_offset=396, sysex_bit_mask=0x7F,  # bits 0-6; bit 7 = mod_lock
             display_name="Mod Assign"),
    ParamDef("short_ribbon_mod_lock", "Short Ribbon Mod Lock", "Lock on/off for modulation",
             0, 1, group="ribbon", section="short_ribbon",
             sysex_offset=396, sysex_bit=7,  # bit 7 of pk396; confirmed empirically 2026-02-23
             display_name="Mod Lock",
             value_labels={0: "Lock Off", 1: "Lock On"}),

    # -----------------------------------------------------------------------
    # Common: Scale
    # -----------------------------------------------------------------------
    ParamDef("scale", "Scale", "Scale type for the program",
             0, 9, group="common", section="common",
             sysex_offset=398,
             display_name="Scale",
             value_labels={0: "Equal Temp", 1: "Pure Major", 2: "Pure Minor",
                           3: "Arabic", 4: "Pythagorean", 5: "Werckmeister",
                           6: "Kirnberger", 7: "Slendro", 8: "Pelog",
                           9: "User Scale"}),
    ParamDef("scale_key", "Scale Key", "Root note for the scale",
             0, 11, group="common", section="common",
             sysex_offset=12, sysex_bit=4,
             display_name="Scale Key"),
]


class ParamMap:
    def __init__(self) -> None:
        self._params = {p.name: p for p in _PARAMS}

    def get(self, name: str) -> ParamDef | None:
        return self._params.get(name)

    def list_all(self) -> list[ParamDef]:
        return list(self._params.values())

    def names(self) -> list[str]:
        return list(self._params.keys())

    def by_group(self, group: str) -> list[ParamDef]:
        return [p for p in self._params.values() if p.group == group]

    def by_section(self, section: str) -> list[ParamDef]:
        return [p for p in self._params.values() if p.section == section]

    def by_timbre(self, timbre: int) -> list[ParamDef]:
        return [p for p in self._params.values() if p.timbre == timbre]

    def sysex_params(self) -> list[ParamDef]:
        return [p for p in self._params.values() if p.sysex_offset is not None]

    def nrpn_params(self) -> list[ParamDef]:
        return [p for p in self._params.values() if p.is_nrpn]

