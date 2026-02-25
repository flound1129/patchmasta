from __future__ import annotations

import threading
import time
from typing import Callable

import mido
from PyQt6.QtCore import QObject, pyqtSignal


class MidiFilePlayer(QObject):
    """MIDI file playback engine running in a daemon thread.

    Emits Qt signals for note events, position updates, and playback state.
    Accepts optional device output callables for sending notes to hardware.
    """

    note_on = pyqtSignal(int, int)       # note, velocity
    note_off = pyqtSignal(int)           # note
    position_changed = pyqtSignal(float, float)  # current_sec, total_sec
    playback_finished = pyqtSignal()
    file_loaded = pyqtSignal(str, float)  # filename, duration_seconds

    # RK-100S 2 uses channel 1 (0-indexed = 0)
    _CHANNEL = 0

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._events: list[tuple[float, mido.Message]] = []
        self._duration: float = 0.0
        self._filename: str = ""

        # Playback state
        self._playing = False
        self._paused = False
        self._loop = False
        self._tempo_factor: float = 1.0
        self._position: float = 0.0  # current position in seconds
        self._seek_target: float | None = None
        self._stop_flag = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._active_notes: set[int] = set()

        # Device output callables (set externally)
        self._send_note_on: Callable[[int, int, int], None] | None = None
        self._send_note_off: Callable[[int, int], None] | None = None
        self._send_all_notes_off: Callable[[], None] | None = None

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def position(self) -> float:
        return self._position

    def set_send_note_on(self, callback: Callable[[int, int, int], None]) -> None:
        self._send_note_on = callback

    def set_send_note_off(self, callback: Callable[[int, int], None]) -> None:
        self._send_note_off = callback

    def set_send_all_notes_off(self, callback: Callable[[], None]) -> None:
        self._send_all_notes_off = callback

    def load_file(self, path: str) -> None:
        """Parse a MIDI file, merge tracks, and convert to timed event list."""
        self.stop()
        mid = mido.MidiFile(path)
        merged = mido.merge_tracks(mid.tracks)

        events: list[tuple[float, mido.Message]] = []
        abs_time = 0.0
        tempo = 500000  # default 120 BPM

        for msg in merged:
            abs_time += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
            if msg.is_meta:
                if msg.type == "set_tempo":
                    tempo = msg.tempo
                continue
            if msg.type in ("note_on", "note_off"):
                events.append((abs_time, msg))

        self._events = events
        self._duration = abs_time if events else 0.0
        # If there are events, duration is at least the last event time
        if events:
            self._duration = max(self._duration, events[-1][0])
        self._filename = path.rsplit("/", 1)[-1] if "/" in path else path
        self._position = 0.0
        self.file_loaded.emit(self._filename, self._duration)

    def play(self) -> None:
        """Start or resume playback."""
        if not self._events:
            return
        if self._paused:
            with self._lock:
                self._paused = False
            return
        if self._playing:
            return
        self._stop_flag = False
        self._playing = True
        self._paused = False
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        if not self._playing:
            return
        with self._lock:
            self._paused = not self._paused

    def stop(self) -> None:
        """Stop playback and reset position."""
        self._stop_flag = True
        with self._lock:
            self._paused = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._playing = False
        self._position = 0.0
        # Send All Sound Off (CC 120) directly — don't rely on _active_notes
        # which may have been cleared by the playback thread already.
        if self._send_all_notes_off is not None:
            try:
                self._send_all_notes_off()
            except Exception:
                pass
        self._active_notes.clear()

    def seek(self, seconds: float) -> None:
        """Seek to a position in seconds."""
        seconds = max(0.0, min(seconds, self._duration))
        with self._lock:
            self._seek_target = seconds
            self._position = seconds

    def set_tempo_factor(self, factor: float) -> None:
        """Set tempo multiplier (1.0 = normal, 2.0 = double speed)."""
        self._tempo_factor = max(0.25, min(4.0, factor))

    def set_loop(self, enabled: bool) -> None:
        self._loop = enabled

    def _all_notes_off(self) -> None:
        """Send note-off for all currently active notes."""
        for note in list(self._active_notes):
            self.note_off.emit(note)
            if self._send_note_off is not None:
                try:
                    self._send_note_off(self._CHANNEL + 1, note)
                except Exception:
                    pass
        self._active_notes.clear()
        # Belt-and-suspenders: send MIDI CC 123 (All Notes Off) to the device
        if self._send_all_notes_off is not None:
            try:
                self._send_all_notes_off()
            except Exception:
                pass

    def _playback_loop(self) -> None:
        """Main playback thread loop."""
        last_pos_emit = 0.0
        event_index = 0

        while not self._stop_flag:
            # Handle pause
            if self._paused:
                time.sleep(0.01)
                continue

            # Handle seek
            with self._lock:
                seek = self._seek_target
                self._seek_target = None
            if seek is not None:
                self._all_notes_off()
                self._position = seek
                # Find the event index at or after seek position
                event_index = 0
                for i, (t, _) in enumerate(self._events):
                    if t >= seek:
                        event_index = i
                        break
                else:
                    event_index = len(self._events)
                continue

            # Check if we've played all events
            if event_index >= len(self._events):
                if self._loop:
                    self._all_notes_off()
                    self._position = 0.0
                    event_index = 0
                    continue
                else:
                    self._position = self._duration
                    self._emit_position(self._position, self._duration)
                    break

            event_time, msg = self._events[event_index]

            # Sleep until the next event, in small chunks for responsiveness
            while self._position < event_time and not self._stop_flag:
                if self._paused:
                    break
                with self._lock:
                    if self._seek_target is not None:
                        break

                sleep_remaining = (event_time - self._position) / self._tempo_factor
                chunk = min(0.01, sleep_remaining)
                if chunk > 0:
                    time.sleep(chunk)
                    self._position += chunk * self._tempo_factor

                # Throttled position update (~50ms)
                if self._position - last_pos_emit >= 0.05:
                    self._emit_position(self._position, self._duration)
                    last_pos_emit = self._position

            # If we broke out for pause/seek/stop, don't dispatch the event
            if self._stop_flag or self._paused:
                continue
            with self._lock:
                if self._seek_target is not None:
                    continue

            # Dispatch the note event
            self._position = event_time
            self._dispatch_note(msg)
            event_index += 1

        self._playing = False
        self._all_notes_off()
        if not self._stop_flag:
            self.playback_finished.emit()

    def _dispatch_note(self, msg: mido.Message) -> None:
        """Emit signal and send to device for a note event."""
        note = msg.note
        if msg.type == "note_on" and msg.velocity > 0:
            self._active_notes.add(note)
            self.note_on.emit(note, msg.velocity)
            if self._send_note_on is not None:
                try:
                    self._send_note_on(self._CHANNEL + 1, note, msg.velocity)
                except Exception:
                    pass
        else:
            self._active_notes.discard(note)
            self.note_off.emit(note)
            if self._send_note_off is not None:
                try:
                    self._send_note_off(self._CHANNEL + 1, note)
                except Exception:
                    pass

    def _emit_position(self, current: float, total: float) -> None:
        """Thread-safe position signal emission."""
        self.position_changed.emit(current, total)
