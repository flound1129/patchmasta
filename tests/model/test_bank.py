from pathlib import Path
from model.bank import Bank

def test_bank_creation():
    b = Bank(name="Live Set 1")
    assert b.name == "Live Set 1"
    assert b.slots == {}

def test_bank_assign_and_remove():
    b = Bank(name="Test")
    b.assign(slot=0, patch_file=Path("patches/fat-pad.json"))
    assert b.slots[0] == Path("patches/fat-pad.json")
    b.remove(slot=0)
    assert 0 not in b.slots

def test_bank_save_and_load(tmp_path):
    b = Bank(name="My Bank")
    b.assign(slot=0, patch_file=Path("patches/fat-pad.json"))
    b.assign(slot=1, patch_file=Path("patches/saw-lead.json"))
    bank_path = tmp_path / "my-bank.json"
    b.save(bank_path)
    loaded = Bank.load(bank_path)
    assert loaded.name == "My Bank"
    assert loaded.slots[0] == Path("patches/fat-pad.json")
    assert loaded.slots[1] == Path("patches/saw-lead.json")

def test_bank_ordered_slots():
    b = Bank(name="Test")
    b.assign(slot=5, patch_file=Path("p5.json"))
    b.assign(slot=2, patch_file=Path("p2.json"))
    assert list(b.ordered_slots()) == [(2, Path("p2.json")), (5, Path("p5.json"))]
