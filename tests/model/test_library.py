from pathlib import Path
from model.patch import Patch
from model.bank import Bank
from model.library import Library

def test_library_creates_dirs(tmp_path):
    lib = Library(root=tmp_path)
    assert (tmp_path / "patches").exists()
    assert (tmp_path / "banks").exists()

def test_library_save_and_list_patches(tmp_path):
    lib = Library(root=tmp_path)
    p = Patch(name="Fat Pad", program_number=1)
    lib.save_patch(p)
    patches = lib.list_patches()
    assert len(patches) == 1
    assert patches[0].name == "Fat Pad"

def test_library_save_and_list_banks(tmp_path):
    lib = Library(root=tmp_path)
    b = Bank(name="Live Set")
    lib.save_bank(b)
    banks = lib.list_banks()
    assert len(banks) == 1
    assert banks[0].name == "Live Set"

def test_library_patch_name_collision(tmp_path):
    lib = Library(root=tmp_path)
    lib.save_patch(Patch(name="Test", program_number=1))
    lib.save_patch(Patch(name="Test", program_number=2))
    assert len(lib.list_patches()) == 2

def test_library_delete_patch(tmp_path):
    lib = Library(root=tmp_path)
    p = Patch(name="To Delete", program_number=5, sysex_data=bytes([0x01]))
    path = lib.save_patch(p)
    lib.delete_patch(path)
    assert len(lib.list_patches()) == 0
