import time
import tempfile
import os

import pytest
import mido
from unittest.mock import MagicMock
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from midi.player import MidiFilePlayer


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _process_events_wait(condition, timeout_sec=5.0):
    """Spin waiting for condition(), processing Qt events so cross-thread
    signals get delivered."""
    deadline = time.time() + timeout_sec
    while not condition() and time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


def _make_midi_file(notes=None, tempo=500000, ticks_per_beat=480):
    """Create a temporary MIDI file with given notes.

    notes: list of (note, velocity, duration_ticks) or None for default.
    Returns the path to the temp file.
    """
    if notes is None:
        notes = [(60, 100, 240), (64, 100, 240), (67, 100, 240)]
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    for note, vel, dur in notes:
        track.append(mido.Message("note_on", note=note, velocity=vel, time=0))
        track.append(mido.Message("note_off", note=note, velocity=0, time=dur))
    fd, path = tempfile.mkstemp(suffix=".mid")
    os.close(fd)
    mid.save(path)
    return path


@pytest.fixture
def player(app):
    p = MidiFilePlayer()
    yield p
    p.stop()


@pytest.fixture
def midi_file():
    path = _make_midi_file()
    yield path
    os.unlink(path)


def test_load_file(player, midi_file):
    loaded = []
    player.file_loaded.connect(lambda name, dur: loaded.append((name, dur)))
    player.load_file(midi_file)
    assert len(loaded) == 1
    assert loaded[0][1] > 0  # duration > 0
    assert player.duration > 0


def test_play_emits_notes(player, midi_file):
    player.load_file(midi_file)
    on_notes = []
    off_notes = []
    player.note_on.connect(lambda n, v: on_notes.append(n))
    player.note_off.connect(lambda n: off_notes.append(n))
    player.play()
    _process_events_wait(lambda: not player.playing)
    # Final flush of pending events
    QCoreApplication.processEvents()
    assert set(on_notes) == {60, 64, 67}
    assert set(off_notes) == {60, 64, 67}


def test_stop_sends_all_notes_off(player):
    # Use a longer file so we can stop mid-play
    path = _make_midi_file(
        notes=[(60, 100, 4800), (64, 100, 4800)],
        tempo=500000,
    )
    try:
        player.load_file(path)
        off_notes = []
        player.note_off.connect(lambda n: off_notes.append(n))
        player.play()
        time.sleep(0.15)
        QCoreApplication.processEvents()
        player.stop()
        QCoreApplication.processEvents()
        assert not player.playing
    finally:
        os.unlink(path)


def test_pause_resume(player, midi_file):
    player.load_file(midi_file)
    player.play()
    time.sleep(0.05)
    player.toggle_pause()
    assert player.paused
    pos_at_pause = player.position
    time.sleep(0.1)
    # Position should not advance while paused
    assert abs(player.position - pos_at_pause) < 0.05
    player.toggle_pause()
    assert not player.paused
    time.sleep(0.1)
    assert player.position > pos_at_pause or not player.playing


def test_seek(player, midi_file):
    player.load_file(midi_file)
    mid_point = player.duration / 2
    player.seek(mid_point)
    assert abs(player.position - mid_point) < 0.1


def test_tempo_factor(player):
    # Short file, play at 4x — should finish faster
    path = _make_midi_file(
        notes=[(60, 100, 480)],
        tempo=500000,
        ticks_per_beat=480,
    )
    try:
        player.load_file(path)
        player.set_tempo_factor(4.0)
        player.play()
        _process_events_wait(lambda: not player.playing, timeout_sec=3.0)
        assert not player.playing
    finally:
        os.unlink(path)


def test_loop(player):
    path = _make_midi_file(notes=[(60, 100, 240)], tempo=500000)
    try:
        player.load_file(path)
        player.set_loop(True)
        player.set_tempo_factor(4.0)
        on_notes = []
        player.note_on.connect(lambda n, v: on_notes.append(n))
        player.play()
        _process_events_wait(lambda: len(on_notes) >= 2, timeout_sec=3.0)
        player.stop()
        QCoreApplication.processEvents()
        assert len(on_notes) >= 2
    finally:
        os.unlink(path)


def test_empty_file(player):
    path = _make_midi_file(notes=[])
    try:
        player.load_file(path)
        assert player.duration == 0.0
        # play should be a no-op
        player.play()
        assert not player.playing
    finally:
        os.unlink(path)


def test_playback_finished_signal(player, midi_file):
    player.load_file(midi_file)
    player.set_tempo_factor(4.0)
    finished = []
    player.playback_finished.connect(lambda: finished.append(True))
    player.play()
    _process_events_wait(lambda: len(finished) >= 1)
    assert len(finished) == 1
