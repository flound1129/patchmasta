import sys
import pytest
from PyQt6.QtWidgets import QApplication
from model.patch import Patch

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)

def test_library_panel_shows_patches(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    panel.populate(banks=[], patches=[
        Patch(name="Fat Pad", program_number=1, category="Pad"),
        Patch(name="Lead", program_number=0, category="Lead"),
    ])
    assert panel.table.rowCount() == 2
    # Check cell contents (unsorted order matches insertion)
    names = {panel.table.item(r, 1).text() for r in range(2)}
    assert names == {"Fat Pad", "Lead"}

def test_library_panel_sorting_enabled(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    assert panel.table.isSortingEnabled()

def test_load_file_button_exists_and_emits_signal(app):
    from unittest.mock import MagicMock
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    assert panel._load_file_btn is not None
    assert panel._load_file_btn.isEnabled()
    spy = MagicMock()
    panel.load_file_requested.connect(spy)
    panel._load_file_btn.click()
    assert spy.called


def test_library_panel_columns(app):
    from ui.library_panel import LibraryPanel
    panel = LibraryPanel()
    headers = [
        panel.table.horizontalHeaderItem(c).text()
        for c in range(panel.table.columnCount())
    ]
    assert headers == ["Slot", "Name", "Category", "Notes", "Created"]
