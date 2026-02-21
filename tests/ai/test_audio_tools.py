import numpy as np
from pathlib import Path
from audio.engine import generate_test_tone
from scipy.io import wavfile

def test_analyze_audio_tool(tmp_path):
    # Create a test WAV
    samples = generate_test_tone(440.0, 1.0, 44100)
    wav_path = tmp_path / "test.wav"
    wavfile.write(str(wav_path), 44100, np.int16(samples * 32767))

    from ai.controller import AIController
    # Test the tool method directly
    ctrl = AIController.__new__(AIController)
    ctrl._logger = type("L", (), {"ai": lambda self, m: None, "audio": lambda self, m: None})()
    result = ctrl._tool_analyze_audio(str(wav_path))
    assert "fundamental_hz" in result
    assert "440" in result or "439" in result or "441" in result
