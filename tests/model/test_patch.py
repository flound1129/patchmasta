from pathlib import Path
from model.patch import Patch

def test_patch_creation():
    p = Patch(name="Fat Pad", program_number=42)
    assert p.name == "Fat Pad"
    assert p.program_number == 42
    assert p.category == ""
    assert p.sysex_data is None

def test_patch_to_dict():
    p = Patch(name="Test", program_number=5, category="Lead", notes="bright")
    d = p.to_dict()
    assert d["name"] == "Test"
    assert d["program_number"] == 5

def test_patch_save_and_load(tmp_path):
    data = bytes([0xF0, 0x42, 0x30, 0xF7])
    p = Patch(name="My Patch", program_number=10, category="Bass", sysex_data=data)
    json_path = tmp_path / "my-patch.json"
    p.save(json_path)
    assert json_path.exists()
    assert (tmp_path / "my-patch.syx").exists()
    loaded = Patch.load(json_path)
    assert loaded.name == "My Patch"
    assert loaded.sysex_data == data

def test_patch_load_without_syx(tmp_path):
    p = Patch(name="No SysEx", program_number=3)
    json_path = tmp_path / "no-sysex.json"
    p.save(json_path)
    loaded = Patch.load(json_path)
    assert loaded.sysex_data is None

def test_patch_slug_sanitizes_special_chars():
    p = Patch(name="Lead: Bright (Warm)", program_number=0)
    assert ":" not in p.slug
    assert "(" not in p.slug
    assert ")" not in p.slug
    assert p.slug  # non-empty

def test_patch_load_blocks_sysex_path_traversal(tmp_path):
    """A crafted sysex_file path cannot escape the patch directory."""
    import json
    evil = tmp_path / "evil.json"
    evil.write_text(json.dumps({
        "name": "Evil",
        "program_number": 0,
        "sysex_file": "../../etc/passwd",
    }))
    p = Patch.load(evil)
    assert p.sysex_data is None  # traversal blocked, not read

def test_patch_slug_empty_name_fallback():
    """Names made entirely of special chars produce 'patch', not an empty string."""
    p = Patch(name="!!!", program_number=0)
    assert p.slug == "patch"
