from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ParamDef:
    name: str
    description: str
    sonic_effect: str
    min_val: int
    max_val: int
    nrpn_msb: int | None = None
    nrpn_lsb: int | None = None
    cc_number: int | None = None

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


_PARAMS: list[ParamDef] = [
    ParamDef("arp_on_off", "Arpeggiator on/off", "Enables/disables the arpeggiator",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x02),
    ParamDef("arp_latch", "Arpeggiator latch", "Holds the arpeggio after releasing keys",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x04),
    ParamDef("arp_type", "Arpeggiator type", "Pattern: Up, Down, Alt1, Alt2, Random, Trigger",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x07),
    ParamDef("arp_gate", "Arpeggiator gate time", "Duration of each arpeggio note",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x0A),
    ParamDef("arp_select", "Arpeggiator timbre select", "Which timbre the arp applies to",
             0, 127, nrpn_msb=0x00, nrpn_lsb=0x0B),
    ParamDef("voice_mode", "Voice mode", "Single/Layer/Split/Multi timbre mode",
             0, 127, nrpn_msb=0x05, nrpn_lsb=0x00),
    ParamDef("patch1_source", "Virtual Patch 1 source", "Modulation source for patch 1",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x00),
    ParamDef("patch2_source", "Virtual Patch 2 source", "Modulation source for patch 2",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x01),
    ParamDef("patch3_source", "Virtual Patch 3 source", "Modulation source for patch 3",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x02),
    ParamDef("patch1_dest", "Virtual Patch 1 destination", "Parameter modulated by patch 1",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x08),
    ParamDef("patch2_dest", "Virtual Patch 2 destination", "Parameter modulated by patch 2",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x09),
    ParamDef("patch3_dest", "Virtual Patch 3 destination", "Parameter modulated by patch 3",
             0, 127, nrpn_msb=0x04, nrpn_lsb=0x0A),
    ParamDef("vocoder_sw", "Vocoder on/off", "Enables/disables the vocoder",
             0, 127, nrpn_msb=0x05, nrpn_lsb=0x04),
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
