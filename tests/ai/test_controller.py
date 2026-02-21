from ai.tools import TOOL_DEFINITIONS


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
