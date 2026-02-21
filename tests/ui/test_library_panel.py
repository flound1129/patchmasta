import sys
import pytest
from PyQt6.QtWidgets import QApplication
from model.patch import Patch
from model.bank import Bank

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_library_panel_shows_patches(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    panel.populate(banks=[], patches=[Patch(name="Fat Pad", program_number=1)])
    assert panel.tree.topLevelItemCount() >= 1

def test_library_panel_shows_bank(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    panel.populate(banks=[Bank(name="Live Set 1")], patches=[])
    item = panel.tree.topLevelItem(0)
    assert "Live Set 1" in item.text(0)
