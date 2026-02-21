import numpy as np
from audio.engine import AudioAnalyzer, AudioMonitor, generate_test_tone

def test_generate_test_tone():
    samples = generate_test_tone(freq=440.0, duration=0.5, sample_rate=44100)
    assert isinstance(samples, np.ndarray)
    assert len(samples) == 22050

def test_analyze_finds_fundamental():
    samples = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    analysis = AudioAnalyzer.analyze_samples(samples, sample_rate=44100)
    assert "fundamental_hz" in analysis
    assert abs(analysis["fundamental_hz"] - 440.0) < 10

def test_analyze_spectral_centroid():
    samples = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    analysis = AudioAnalyzer.analyze_samples(samples, sample_rate=44100)
    assert "spectral_centroid_hz" in analysis
    assert analysis["spectral_centroid_hz"] > 0

def test_compare_identical_is_low_distance():
    samples = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    report = AudioAnalyzer.compare_samples(samples, samples, sample_rate=44100)
    assert "spectral_distance" in report
    assert report["spectral_distance"] < 0.01

def test_compare_different_is_high_distance():
    s1 = generate_test_tone(freq=440.0, duration=1.0, sample_rate=44100)
    s2 = generate_test_tone(freq=880.0, duration=1.0, sample_rate=44100)
    report = AudioAnalyzer.compare_samples(s1, s2, sample_rate=44100)
    assert report["spectral_distance"] > 0.1

def test_audio_monitor_instantiates():
    monitor = AudioMonitor()
    assert monitor is not None

def test_audio_monitor_not_running_initially():
    monitor = AudioMonitor()
    assert monitor.is_running is False
