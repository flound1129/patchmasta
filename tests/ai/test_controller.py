from unittest.mock import MagicMock
import pytest
from ai.tools import TOOL_DEFINITIONS
from ai.controller import AIController
from midi.params import ParamMap
from midi.sysex_buffer import SysExProgramBuffer
from midi.effects import (
    EFFECT_TYPES, FX1_TYPE_PACKED, FX2_TYPE_PACKED, fx_param_packed,
)
from core.logger import AppLogger


def test_tool_definitions_are_valid():
    assert len(TOOL_DEFINITIONS) > 0
    for tool in TOOL_DEFINITIONS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool


def test_set_parameter_tool_exists():
    names = [t["name"] for t in TOOL_DEFINITIONS]
    assert "set_parameter" in names
    assert "list_parameters" in names
    assert "trigger_note" in names


# ---------------------------------------------------------------------------
# Helpers for FX param tests
# ---------------------------------------------------------------------------

_BUF_SIZE = 400  # large enough for all FX packed offsets


def _make_controller(fx1_type: int = 0, fx2_type: int = 0):
    """Create an AIController with a mock device and a SysEx buffer."""
    buf = SysExProgramBuffer(bytearray(_BUF_SIZE))
    buf.set_byte(FX1_TYPE_PACKED, fx1_type)
    buf.set_byte(FX2_TYPE_PACKED, fx2_type)

    device = MagicMock()
    device.connected = True

    logger = AppLogger()
    param_map = ParamMap()

    writer = MagicMock()

    ctrl = AIController(
        backend=MagicMock(),
        device=device,
        param_map=param_map,
        logger=logger,
        sysex_buffer=buf,
        sysex_writer=writer,
    )
    # Disable auto-play so tests don't sleep
    ctrl._auto_play_note = False
    return ctrl, buf


# ---------------------------------------------------------------------------
# _resolve_fx_param
# ---------------------------------------------------------------------------

def test_resolve_fx_param_returns_offset():
    """Set FX1 to Delay (type 6), resolve fx1_dry_wet."""
    ctrl, buf = _make_controller(fx1_type=6)
    result = ctrl._resolve_fx_param("fx1_dry_wet")
    assert result is not None
    slot, packed, ep = result
    assert slot == 1
    assert packed == fx_param_packed(1, 0)  # dry_wet is slot_index 0
    assert ep.key == "dry_wet"


def test_resolve_fx_param_slot2():
    """Resolve an FX2 param."""
    ctrl, buf = _make_controller(fx2_type=11)  # Chorus
    result = ctrl._resolve_fx_param("fx2_mod_depth")
    assert result is not None
    slot, packed, ep = result
    assert slot == 2
    assert packed == fx_param_packed(2, 1)  # mod_depth is slot_index 1 for Chorus
    assert ep.key == "mod_depth"


def test_resolve_fx_param_unknown_key_returns_none():
    """fx1_nonexistent should not resolve."""
    ctrl, buf = _make_controller(fx1_type=6)
    assert ctrl._resolve_fx_param("fx1_nonexistent") is None


def test_resolve_fx_param_type_off_returns_none():
    """When FX type is 0 (Off), no params available."""
    ctrl, buf = _make_controller(fx1_type=0)
    assert ctrl._resolve_fx_param("fx1_dry_wet") is None


def test_resolve_fx_param_no_buffer_returns_none():
    """Without a SysEx buffer, resolution should return None."""
    ctrl, _ = _make_controller()
    ctrl._sysex_buffer = None
    assert ctrl._resolve_fx_param("fx1_dry_wet") is None


# ---------------------------------------------------------------------------
# _tool_set_parameter with FX params
# ---------------------------------------------------------------------------

def test_set_fx_param_writes_buffer():
    ctrl, buf = _make_controller(fx1_type=6)  # Delay
    result = ctrl._tool_set_parameter("fx1_dry_wet", 64)
    assert "Set fx1_dry_wet = 64" in result
    assert "SysEx" in result
    packed = fx_param_packed(1, 0)
    assert buf.get_byte(packed) == 64


def test_set_fx_param_clamps_value():
    """Values should be clamped to [min_val, max_val]."""
    ctrl, buf = _make_controller(fx1_type=6)  # Delay: dry_wet max=127
    result = ctrl._tool_set_parameter("fx1_dry_wet", 200)
    assert "= 127" in result
    packed = fx_param_packed(1, 0)
    assert buf.get_byte(packed) == 127


def test_set_fx_param_unknown_returns_error():
    ctrl, buf = _make_controller(fx1_type=6)
    result = ctrl._tool_set_parameter("fx1_nonexistent", 10)
    assert "Unknown parameter" in result


def test_set_fx_param_type_off_returns_error():
    ctrl, buf = _make_controller(fx1_type=0)
    result = ctrl._tool_set_parameter("fx1_dry_wet", 64)
    assert "Unknown parameter" in result


def test_set_fx_param_device_disconnected():
    ctrl, buf = _make_controller(fx1_type=6)
    ctrl._device.connected = False
    result = ctrl._tool_set_parameter("fx1_dry_wet", 64)
    assert "not connected" in result


# ---------------------------------------------------------------------------
# _tool_get_parameter with FX params
# ---------------------------------------------------------------------------

def test_get_fx_param_reads_buffer():
    ctrl, buf = _make_controller(fx1_type=6)  # Delay
    packed = fx_param_packed(1, 0)
    buf.set_byte(packed, 42)
    result = ctrl._tool_get_parameter("fx1_dry_wet")
    assert "fx1_dry_wet = 42" in result


def test_get_fx_param_unknown_returns_error():
    ctrl, buf = _make_controller(fx1_type=6)
    result = ctrl._tool_get_parameter("fx1_nonexistent")
    assert "Unknown parameter" in result


# ---------------------------------------------------------------------------
# _tool_list_parameters with FX params
# ---------------------------------------------------------------------------

def test_list_parameters_includes_fx():
    ctrl, buf = _make_controller(fx1_type=6)  # Delay
    output = ctrl._tool_list_parameters()
    assert "--- FX1: Delay ---" in output
    assert "fx1_dry_wet" in output
    assert "fx1_feedback" in output


def test_list_parameters_excludes_fx_when_off():
    ctrl, buf = _make_controller(fx1_type=0, fx2_type=0)
    output = ctrl._tool_list_parameters()
    assert "--- FX1" not in output
    assert "--- FX2" not in output


def test_list_parameters_both_slots():
    ctrl, buf = _make_controller(fx1_type=6, fx2_type=11)  # Delay + Chorus
    output = ctrl._tool_list_parameters()
    assert "--- FX1: Delay ---" in output
    assert "--- FX2: Chorus ---" in output
    assert "fx2_mod_depth" in output
