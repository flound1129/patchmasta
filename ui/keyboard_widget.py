from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPalette
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSlider, QWidget,
)

# Which semitones within an octave are black keys (sharps/flats)
_BLACK_SEMITONES = {1, 3, 6, 8, 10}

# Number of white keys per octave
_WHITES_PER_OCTAVE = 7


def _is_black(note: int) -> bool:
    return (note % 12) in _BLACK_SEMITONES


def _white_index_in_octave(semitone: int) -> int:
    """Return the white-key index (0-6) for a white semitone within an octave."""
    mapping = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}
    return mapping[semitone]


class VirtualKeyboardWidget(QWidget):
    """Custom-painted piano keyboard spanning 3 octaves (36 notes)."""

    note_pressed = pyqtSignal(int, int)   # note, velocity
    note_released = pyqtSignal(int)       # note

    OCTAVE_SPAN = 3
    NUM_KEYS = OCTAVE_SPAN * 12  # 36 keys visible

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_note = 36  # C2 — matches RK-100S 2 keytar range
        self._active_notes: dict[int, int] = {}  # note → velocity
        self._pressed_note: int | None = None
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)

    @property
    def base_note(self) -> int:
        return self._base_note

    @base_note.setter
    def base_note(self, value: int) -> None:
        self._base_note = max(0, min(96, value))
        self.update()

    def note_on(self, note: int, velocity: int) -> None:
        self._active_notes[note] = velocity
        self.update()

    def note_off(self, note: int) -> None:
        self._active_notes.pop(note, None)
        self.update()

    def clear_all_notes(self) -> None:
        self._active_notes.clear()
        self.update()

    # -- Geometry helpers --

    def _white_key_count(self) -> int:
        """Count white keys in the visible range."""
        count = 0
        for i in range(self.NUM_KEYS):
            if not _is_black(self._base_note + i):
                count += 1
        return count

    def _key_rects(self) -> list[tuple[int, float, float, float, float, bool]]:
        """Return (note, x, y, w, h, is_black) for each visible key.

        White keys are listed first, then black keys on top.
        """
        w = self.width()
        h = self.height()
        n_whites = self._white_key_count()
        if n_whites == 0:
            return []
        white_w = w / n_whites
        black_w = white_w * 0.6
        black_h = h * 0.6

        whites: list[tuple[int, float, float, float, float, bool]] = []
        blacks: list[tuple[int, float, float, float, float, bool]] = []
        white_idx = 0
        for i in range(self.NUM_KEYS):
            note = self._base_note + i
            if _is_black(note):
                # Black key sits between the two surrounding white keys
                x = white_idx * white_w - black_w / 2
                blacks.append((note, x, 0, black_w, black_h, True))
            else:
                x = white_idx * white_w
                whites.append((note, x, 0, white_w, h, False))
                white_idx += 1
        return whites + blacks

    def _note_at(self, x: float, y: float) -> int | None:
        """Find which note is at pixel (x, y). Black keys checked first."""
        rects = self._key_rects()
        # Check black keys first (they're at the end of the list, drawn on top)
        for note, kx, ky, kw, kh, is_black in reversed(rects):
            if is_black and kx <= x <= kx + kw and ky <= y <= ky + kh:
                return note
        # Then white keys
        for note, kx, ky, kw, kh, is_black in rects:
            if not is_black and kx <= x <= kx + kw and ky <= y <= ky + kh:
                return note
        return None

    # -- Painting --

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        accent = QColor(pal.color(QPalette.ColorRole.Highlight))
        white_bg = QColor(pal.color(QPalette.ColorRole.Base))
        black_bg = QColor(pal.color(QPalette.ColorRole.Dark))
        border = QColor(pal.color(QPalette.ColorRole.Mid))

        for note, x, y, w, h, is_black in self._key_rects():
            vel = self._active_notes.get(note)
            if is_black:
                if vel is not None:
                    color = QColor(accent)
                    color.setAlphaF(0.5 + 0.5 * (vel / 127.0))
                else:
                    color = black_bg
                painter.setBrush(color)
                painter.setPen(border)
                painter.drawRect(int(x), int(y), int(w), int(h))
            else:
                if vel is not None:
                    color = QColor(accent)
                    color.setAlphaF(0.3 + 0.5 * (vel / 127.0))
                else:
                    color = white_bg
                painter.setBrush(color)
                painter.setPen(border)
                painter.drawRect(int(x), int(y), int(w), int(h))
        painter.end()

    # -- Mouse interaction --

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            note = self._note_at(event.position().x(), event.position().y())
            if note is not None:
                self._pressed_note = note
                self.note_pressed.emit(note, 100)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._pressed_note is not None:
            self.note_released.emit(self._pressed_note)
            self._pressed_note = None


class KeyboardPanel(QWidget):
    """Container with octave shift buttons and the virtual keyboard."""

    note_pressed = pyqtSignal(int, int)   # note, velocity
    note_released = pyqtSignal(int)       # note

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._btn_down = QPushButton("\u25C0")  # ◀
        self._btn_down.setFixedWidth(28)
        self._btn_down.setToolTip("Shift down one octave")
        self._btn_down.clicked.connect(self._shift_down)

        self._keyboard = VirtualKeyboardWidget()

        self._btn_up = QPushButton("\u25B6")  # ▶
        self._btn_up.setFixedWidth(28)
        self._btn_up.setToolTip("Shift up one octave")
        self._btn_up.clicked.connect(self._shift_up)

        layout.addWidget(self._btn_down)
        layout.addWidget(self._keyboard, stretch=1)
        layout.addWidget(self._btn_up)

        # Forward signals
        self._keyboard.note_pressed.connect(self.note_pressed)
        self._keyboard.note_released.connect(self.note_released)

        self._update_tooltips()

    @property
    def keyboard(self) -> VirtualKeyboardWidget:
        return self._keyboard

    def note_on(self, note: int, velocity: int) -> None:
        self._keyboard.note_on(note, velocity)

    def note_off(self, note: int) -> None:
        self._keyboard.note_off(note)

    def clear_all_notes(self) -> None:
        self._keyboard.clear_all_notes()

    def _shift_down(self) -> None:
        self._keyboard.base_note -= 12
        self._update_tooltips()

    def _shift_up(self) -> None:
        self._keyboard.base_note += 12
        self._update_tooltips()

    def _update_tooltips(self) -> None:
        base = self._keyboard.base_note
        top = base + 35  # 3 octaves - 1
        note_names = ["C", "C#", "D", "D#", "E", "F",
                       "F#", "G", "G#", "A", "A#", "B"]
        lo = f"{note_names[base % 12]}{base // 12 - 1}"
        hi = f"{note_names[top % 12]}{top // 12 - 1}"
        self._keyboard.setToolTip(f"{lo}\u2013{hi}")


def _format_time(seconds: float) -> str:
    """Format seconds as m:ss."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


class TransportPanel(QWidget):
    """MIDI file transport controls: load, play/pause, stop, seek, tempo, loop."""

    load_requested = pyqtSignal()
    play_pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    rewind_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)
    tempo_changed = pyqtSignal(float)
    loop_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(44)
        self._duration: float = 0.0
        self._dragging = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Load button
        self._btn_load = QPushButton("Load MIDI...")
        self._btn_load.setMinimumWidth(90)
        self._btn_load.clicked.connect(self.load_requested)
        layout.addWidget(self._btn_load)

        # Rewind
        self._btn_rewind = QPushButton("\u23EE")  # ⏮
        self._btn_rewind.setMinimumWidth(36)
        self._btn_rewind.setEnabled(False)
        self._btn_rewind.clicked.connect(self.rewind_requested)
        layout.addWidget(self._btn_rewind)

        # Play / Pause
        self._btn_play = QPushButton("\u25B6")  # ▶
        self._btn_play.setMinimumWidth(36)
        self._btn_play.setEnabled(False)
        self._btn_play.clicked.connect(self.play_pause_requested)
        layout.addWidget(self._btn_play)

        # Stop
        self._btn_stop = QPushButton("\u25A0")  # ■
        self._btn_stop.setMinimumWidth(36)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self.stop_requested)
        layout.addWidget(self._btn_stop)

        # Progress slider (millisecond resolution)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setMinimumWidth(60)
        self._slider.setMaximumWidth(300)
        self._slider.setEnabled(False)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self._slider, stretch=1)

        # Time label
        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setFixedWidth(80)
        layout.addWidget(self._time_label)

        # Tempo slider (25% – 400%)
        self._tempo_slider = QSlider(Qt.Orientation.Horizontal)
        self._tempo_slider.setRange(25, 400)
        self._tempo_slider.setValue(100)
        self._tempo_slider.setMinimumWidth(40)
        self._tempo_slider.setMaximumWidth(60)
        self._tempo_slider.setEnabled(False)
        self._tempo_slider.valueChanged.connect(self._on_tempo_changed)
        layout.addWidget(self._tempo_slider)

        self._tempo_label = QLabel("100%")
        self._tempo_label.setFixedWidth(40)
        layout.addWidget(self._tempo_label)

        # Loop toggle
        self._btn_loop = QPushButton("\U0001F501")  # 🔁
        self._btn_loop.setMinimumWidth(36)
        self._btn_loop.setCheckable(True)
        self._btn_loop.setEnabled(False)
        self._btn_loop.toggled.connect(self.loop_toggled)
        layout.addWidget(self._btn_loop)

    def set_file_loaded(self, filename: str, duration: float) -> None:
        """Enable controls after a MIDI file is loaded."""
        self._duration = duration
        self._slider.setRange(0, int(duration * 1000))
        self._slider.setValue(0)
        self._time_label.setText(f"0:00 / {_format_time(duration)}")
        for w in (self._btn_rewind, self._btn_play, self._btn_stop,
                  self._slider, self._tempo_slider, self._btn_loop):
            w.setEnabled(True)

    def update_position(self, current: float, total: float) -> None:
        """Update slider and time label from playback position."""
        if self._dragging:
            return
        self._slider.setValue(int(current * 1000))
        self._time_label.setText(
            f"{_format_time(current)} / {_format_time(total)}"
        )

    def set_playing(self, playing: bool) -> None:
        """Toggle play/pause icon."""
        self._btn_play.setText("\u23F8" if playing else "\u25B6")  # ⏸ or ▶

    def reset(self) -> None:
        """Restore stopped state."""
        self.set_playing(False)
        self._slider.setValue(0)
        self._time_label.setText(
            f"0:00 / {_format_time(self._duration)}"
        )

    def _on_slider_pressed(self) -> None:
        self._dragging = True

    def _on_slider_released(self) -> None:
        self._dragging = False
        self.seek_requested.emit(self._slider.value() / 1000.0)

    def _on_tempo_changed(self, value: int) -> None:
        self._tempo_label.setText(f"{value}%")
        self.tempo_changed.emit(value / 100.0)
