import sys
import pytest
from PyQt6.QtWidgets import QApplication
from model.patch import Patch

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_patch_detail_empty_by_default(app):
    from ui.patch_detail import PatchDetailPanel
    panel = PatchDetailPanel()
    assert panel.name_edit.text() == ""

def test_patch_detail_loads_patch(app):
    from ui.patch_detail import PatchDetailPanel
    panel = PatchDetailPanel()
    p = Patch(name="Fat Pad", program_number=42, category="Lead", notes="warm")
    panel.load_patch(p)
    assert panel.name_edit.text() == "Fat Pad"
    assert panel.slot_spin.value() == 42
    assert panel.category_edit.text() == "Lead"

def test_patch_detail_save_emits_signal(app, qtbot):
    from ui.patch_detail import PatchDetailPanel
    panel = PatchDetailPanel()
    panel.load_patch(Patch(name="Test", program_number=1))
    with qtbot.waitSignal(panel.patch_saved, timeout=1000):
        panel.save_btn.click()
