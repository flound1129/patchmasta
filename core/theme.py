from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


@dataclass
class ThemeColors:
    name: str
    # Window/widget backgrounds
    window: str
    base: str
    alternate_base: str
    # Text
    text: str
    bright_text: str
    placeholder: str
    # Accents
    highlight: str
    highlight_text: str
    link: str
    # Buttons
    button: str
    button_text: str
    # Borders/midtones
    mid: str
    dark: str
    light: str
    # Chat bubble colors
    user_bubble_bg: str
    user_bubble_text: str
    ai_bubble_bg: str
    ai_bubble_text: str
    tool_bubble_bg: str
    tool_bubble_text: str
    # Accent for group box titles, active elements
    accent: str


THEMES: dict[str, ThemeColors] = {
    "light": ThemeColors(
        name="light",
        window="#f5f5f5",
        base="#ffffff",
        alternate_base="#e8e8e8",
        text="#1a1a1a",
        bright_text="#ffffff",
        placeholder="#888888",
        highlight="#2563eb",
        highlight_text="#ffffff",
        link="#2563eb",
        button="#e0e0e0",
        button_text="#1a1a1a",
        mid="#c0c0c0",
        dark="#a0a0a0",
        light="#ffffff",
        user_bubble_bg="#2563eb",
        user_bubble_text="#ffffff",
        ai_bubble_bg="#e5e7eb",
        ai_bubble_text="#1a1a1a",
        tool_bubble_bg="#d1d5db",
        tool_bubble_text="#4b5563",
        accent="#2563eb",
    ),
    "dark": ThemeColors(
        name="dark",
        window="#1e1e2e",
        base="#181825",
        alternate_base="#262637",
        text="#cdd6f4",
        bright_text="#ffffff",
        placeholder="#6c7086",
        highlight="#2563eb",
        highlight_text="#ffffff",
        link="#89b4fa",
        button="#313244",
        button_text="#cdd6f4",
        mid="#45475a",
        dark="#11111b",
        light="#45475a",
        user_bubble_bg="#2563eb",
        user_bubble_text="#ffffff",
        ai_bubble_bg="#313244",
        ai_bubble_text="#cdd6f4",
        tool_bubble_bg="#262637",
        tool_bubble_text="#6c7086",
        accent="#89b4fa",
    ),
    "korg": ThemeColors(
        name="korg",
        window="#1a1a1a",
        base="#121212",
        alternate_base="#222222",
        text="#e0e0e0",
        bright_text="#ffffff",
        placeholder="#666666",
        highlight="#cc0000",
        highlight_text="#ffffff",
        link="#ff3333",
        button="#2a2a2a",
        button_text="#e0e0e0",
        mid="#444444",
        dark="#0a0a0a",
        light="#444444",
        user_bubble_bg="#cc0000",
        user_bubble_text="#ffffff",
        ai_bubble_bg="#2a2a2a",
        ai_bubble_text="#e0e0e0",
        tool_bubble_bg="#1f1f1f",
        tool_bubble_text="#888888",
        accent="#cc0000",
    ),
    "ocean": ThemeColors(
        name="ocean",
        window="#0d1b2a",
        base="#0a1628",
        alternate_base="#132d4a",
        text="#c8dce8",
        bright_text="#ffffff",
        placeholder="#4a6a80",
        highlight="#00b4d8",
        highlight_text="#ffffff",
        link="#48cae4",
        button="#1b3a5c",
        button_text="#c8dce8",
        mid="#2a4a6a",
        dark="#061018",
        light="#2a4a6a",
        user_bubble_bg="#00b4d8",
        user_bubble_text="#ffffff",
        ai_bubble_bg="#1b3a5c",
        ai_bubble_text="#c8dce8",
        tool_bubble_bg="#132d4a",
        tool_bubble_text="#4a6a80",
        accent="#00b4d8",
    ),
    "sunset": ThemeColors(
        name="sunset",
        window="#2d1b00",
        base="#241600",
        alternate_base="#3a2400",
        text="#fde8c8",
        bright_text="#ffffff",
        placeholder="#8a6a40",
        highlight="#f59e0b",
        highlight_text="#1a1000",
        link="#fbbf24",
        button="#4a3000",
        button_text="#fde8c8",
        mid="#5a4020",
        dark="#1a1000",
        light="#5a4020",
        user_bubble_bg="#f59e0b",
        user_bubble_text="#1a1000",
        ai_bubble_bg="#4a3000",
        ai_bubble_text="#fde8c8",
        tool_bubble_bg="#3a2400",
        tool_bubble_text="#8a6a40",
        accent="#f59e0b",
    ),
}


def detect_system_scheme() -> str:
    """Return ``'light'`` or ``'dark'`` based on the OS preference."""
    app = QApplication.instance()
    if app is not None:
        try:
            scheme = app.styleHints().colorScheme()
            from PyQt6.QtCore import Qt
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
            if scheme == Qt.ColorScheme.Light:
                return "light"
        except AttributeError:
            pass
        # Fallback: check palette window color lightness
        lightness = app.palette().color(QPalette.ColorRole.Window).lightness()
        return "light" if lightness > 128 else "dark"
    return "dark"


def get_theme(name: str) -> ThemeColors:
    """Return the resolved theme (``'auto'`` maps to system preference)."""
    if name == "auto":
        name = detect_system_scheme()
    return THEMES.get(name, THEMES["dark"])


def apply_theme(app: QApplication, theme_name: str) -> None:
    """Apply the named theme to the application."""
    colors = get_theme(theme_name)

    app.setStyle("Fusion")

    palette = QPalette()
    _set = palette.setColor
    _set(QPalette.ColorRole.Window, QColor(colors.window))
    _set(QPalette.ColorRole.WindowText, QColor(colors.text))
    _set(QPalette.ColorRole.Base, QColor(colors.base))
    _set(QPalette.ColorRole.AlternateBase, QColor(colors.alternate_base))
    _set(QPalette.ColorRole.Text, QColor(colors.text))
    _set(QPalette.ColorRole.BrightText, QColor(colors.bright_text))
    _set(QPalette.ColorRole.PlaceholderText, QColor(colors.placeholder))
    _set(QPalette.ColorRole.Highlight, QColor(colors.highlight))
    _set(QPalette.ColorRole.HighlightedText, QColor(colors.highlight_text))
    _set(QPalette.ColorRole.Link, QColor(colors.link))
    _set(QPalette.ColorRole.Button, QColor(colors.button))
    _set(QPalette.ColorRole.ButtonText, QColor(colors.button_text))
    _set(QPalette.ColorRole.Mid, QColor(colors.mid))
    _set(QPalette.ColorRole.Dark, QColor(colors.dark))
    _set(QPalette.ColorRole.Light, QColor(colors.light))

    # Disabled palette: dimmed text
    _set(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(colors.mid))
    _set(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors.mid))
    _set(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(colors.mid))

    app.setPalette(palette)

    # Minimal QSS for details Fusion doesn't cover
    accent = colors.accent
    mid = colors.mid
    btn = colors.button
    btn_light = colors.light
    app.setStyleSheet(f"""
        QGroupBox {{
            border: 1px solid {mid};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 4px;
        }}
        QGroupBox::title {{
            color: {accent};
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}
        QSplitter::handle {{
            background: {mid};
        }}
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        QPushButton {{
            padding: 4px 12px;
            border: 1px solid {mid};
            border-radius: 3px;
        }}
        QPushButton:hover {{
            background-color: {btn_light};
        }}
        QPushButton:pressed {{
            background-color: {accent};
        }}
        QScrollBar:vertical {{
            background: {btn};
            width: 10px;
        }}
        QScrollBar::handle:vertical {{
            background: {mid};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {btn};
            height: 10px;
        }}
        QScrollBar::handle:horizontal {{
            background: {mid};
            border-radius: 4px;
            min-width: 20px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """)


def connect_system_theme_changed(app: QApplication, config) -> None:
    """Re-apply theme when OS colour scheme changes (Qt 6.5+). No-op on older Qt."""
    try:
        hints = app.styleHints()
        hints.colorSchemeChanged.connect(
            lambda _scheme: apply_theme(app, config.theme)
            if config.theme == "auto"
            else None
        )
    except AttributeError:
        pass
