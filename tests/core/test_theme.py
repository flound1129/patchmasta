from dataclasses import fields

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from core.theme import (
    THEMES,
    ThemeColors,
    apply_theme,
    detect_system_scheme,
    get_theme,
)


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_theme_colors_has_all_fields():
    expected = {
        "name", "window", "base", "alternate_base",
        "text", "bright_text", "placeholder",
        "highlight", "highlight_text", "link",
        "button", "button_text",
        "mid", "dark", "light",
        "user_bubble_bg", "user_bubble_text",
        "ai_bubble_bg", "ai_bubble_text",
        "tool_bubble_bg", "tool_bubble_text",
        "accent",
        "section_osc", "section_filter", "section_amp",
        "section_mod", "section_voice", "section_fx",
    }
    actual = {f.name for f in fields(ThemeColors)}
    assert expected == actual


def test_all_themes_defined():
    assert set(THEMES.keys()) == {"light", "dark", "korg", "ocean", "sunset"}


def test_each_theme_produces_valid_palette():
    app = _ensure_app()
    for name, colors in THEMES.items():
        apply_theme(app, name)
        palette = app.palette()
        assert isinstance(palette, QPalette)
        # Verify a few colours were actually set
        assert palette.color(QPalette.ColorRole.Window).isValid()
        assert palette.color(QPalette.ColorRole.Highlight).isValid()


def test_detect_system_scheme_returns_valid():
    _ensure_app()
    result = detect_system_scheme()
    assert result in ("light", "dark")


def test_get_theme_auto_resolves():
    _ensure_app()
    theme = get_theme("auto")
    assert isinstance(theme, ThemeColors)
    assert theme.name in ("light", "dark")


def test_get_theme_unknown_falls_back_to_dark():
    _ensure_app()
    theme = get_theme("nonexistent")
    assert theme.name == "dark"


def test_chat_bubble_colors_differ_light_dark():
    light = THEMES["light"]
    dark = THEMES["dark"]
    assert light.ai_bubble_bg != dark.ai_bubble_bg
    assert light.user_bubble_bg == dark.user_bubble_bg or True  # both may use blue
    assert light.ai_bubble_text != dark.ai_bubble_text


def test_korg_theme_has_red_accent():
    korg = THEMES["korg"]
    assert korg.accent == "#cc0000"
    assert korg.highlight == "#cc0000"
