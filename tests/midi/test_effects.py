"""Tests for the effect type registry (midi/effects.py)."""
import pytest
from midi.effects import EFFECT_TYPES, EffectTypeDef, EffectParam, get_effect_type


def test_all_18_entries_present():
    assert set(EFFECT_TYPES.keys()) == set(range(18))


def test_effect_off_has_no_params():
    off = EFFECT_TYPES[0]
    assert off.name == "Effect Off"
    assert len(off.params) == 0


def test_each_type_has_unique_id_and_name():
    ids = [t.type_id for t in EFFECT_TYPES.values()]
    names = [t.name for t in EFFECT_TYPES.values()]
    assert len(set(ids)) == len(ids)
    assert len(set(names)) == len(names)


def test_type_id_matches_dict_key():
    for key, typedef in EFFECT_TYPES.items():
        assert key == typedef.type_id


@pytest.mark.parametrize("type_id", range(18))
def test_params_valid_ranges(type_id):
    typedef = EFFECT_TYPES[type_id]
    for p in typedef.params:
        assert p.min_val <= p.max_val, f"{typedef.name}/{p.key}: min > max"
        assert 0 <= p.slot_index <= 22, f"{typedef.name}/{p.key}: slot_index out of range"


@pytest.mark.parametrize("type_id", range(18))
def test_no_duplicate_slot_index(type_id):
    typedef = EFFECT_TYPES[type_id]
    slots = [p.slot_index for p in typedef.params]
    assert len(set(slots)) == len(slots), f"{typedef.name}: duplicate slot_index"


@pytest.mark.parametrize("type_id", range(18))
def test_no_duplicate_key(type_id):
    typedef = EFFECT_TYPES[type_id]
    keys = [p.key for p in typedef.params]
    assert len(set(keys)) == len(keys), f"{typedef.name}: duplicate key"


def test_get_effect_type_valid():
    result = get_effect_type(1)
    assert result is not None
    assert result.name == "Compressor"


def test_get_effect_type_invalid():
    assert get_effect_type(99) is None
    assert get_effect_type(-1) is None


def test_expected_param_counts():
    expected = {
        0: 0, 1: 5, 2: 16, 3: 16, 4: 15, 5: 14, 6: 10, 7: 12,
        8: 18, 9: 9, 10: 16, 11: 8, 12: 14, 13: 10, 14: 14,
        15: 10, 16: 15, 17: 11,
    }
    for type_id, count in expected.items():
        actual = len(EFFECT_TYPES[type_id].params)
        assert actual == count, (
            f"Type {type_id} ({EFFECT_TYPES[type_id].name}): "
            f"expected {count} params, got {actual}"
        )


def test_all_active_types_have_dry_wet():
    """Every active effect type (1-17) should have a dry_wet param at slot 0."""
    for type_id in range(1, 18):
        typedef = EFFECT_TYPES[type_id]
        dry_wet = [p for p in typedef.params if p.key == "dry_wet"]
        assert len(dry_wet) == 1, f"{typedef.name}: missing dry_wet"
        assert dry_wet[0].slot_index == 0, f"{typedef.name}: dry_wet not at slot 0"


def test_dry_wet_always_ribbon_assignable():
    """dry_wet should be ribbon_assignable in every active effect type."""
    for type_id in range(1, 18):
        typedef = EFFECT_TYPES[type_id]
        dw = next(p for p in typedef.params if p.key == "dry_wet")
        assert dw.ribbon_assignable, f"{typedef.name}: dry_wet should be ribbon_assignable"


def test_all_active_types_have_ribbon_assigns():
    """Every active effect type should expose at least one ribbon-assignable param."""
    for type_id in range(1, 18):
        typedef = EFFECT_TYPES[type_id]
        assigns = typedef.ribbon_assigns()
        assert len(assigns) >= 1, f"{typedef.name}: no ribbon-assignable params"


def test_4band_eq_ribbon_assigns():
    """4Band EQ ribbon assigns match the confirmed list from the Sound Editor."""
    typedef = EFFECT_TYPES[3]
    keys = [p.key for p in typedef.ribbon_assigns()]
    assert keys == ["dry_wet", "b1_gain", "b2_gain", "b3_gain", "b4_gain"]


def test_compressor_ribbon_assigns():
    typedef = EFFECT_TYPES[1]
    keys = [p.key for p in typedef.ribbon_assigns()]
    assert keys == ["dry_wet", "sensitivity", "attack"]


def test_ribbon_assignable_field_defaults_true():
    """EffectParam.ribbon_assignable defaults to True."""
    p = EffectParam("x", "X", 0, 127, 0)
    assert p.ribbon_assignable is True


def test_effect_off_ribbon_assigns_empty():
    """Effect Off (type 0) has no params, so ribbon_assigns() is empty."""
    assert EFFECT_TYPES[0].ribbon_assigns() == []
