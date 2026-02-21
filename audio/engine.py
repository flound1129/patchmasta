from __future__ import annotations
from pathlib import Path
import numpy as np
from scipy.io import wavfile


def generate_test_tone(freq: float, duration: float, sample_rate: int = 44100) -> np.ndarray:
    """Generate a sine wave for testing."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def list_audio_input_devices() -> list[tuple[int, str]]:
    """Return (index, name) for each audio device with input channels."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        return [
            (i, d["name"])
            for i, d in enumerate(devices)
            if d.get("max_input_channels", 0) > 0
        ]
    except OSError:
        return []


class AudioRecorder:
    """Records audio from an input device."""

    def __init__(self, device: int | str | None = None, sample_rate: int = 44100) -> None:
        self._device = device
        self._sample_rate = sample_rate

    def record(self, duration_s: float) -> np.ndarray:
        import sounddevice as sd
        samples = sd.rec(
            int(duration_s * self._sample_rate),
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            device=self._device,
        )
        sd.wait()
        return samples.flatten()

    def save_wav(self, samples: np.ndarray, path: Path) -> None:
        scaled = np.int16(samples * 32767)
        wavfile.write(str(path), self._sample_rate, scaled)

    @staticmethod
    def load_wav(path: Path) -> tuple[np.ndarray, int]:
        sr, data = wavfile.read(str(path))
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32767.0
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data, sr


class AudioMonitor:
    """Real-time audio passthrough from input to output."""

    def __init__(self, device=None, sample_rate: int = 44100) -> None:
        self._device = device
        self._sample_rate = sample_rate
        self._stream = None

    @property
    def is_running(self) -> bool:
        return self._stream is not None and self._stream.active

    def start(self) -> None:
        if self.is_running:
            return
        import sounddevice as sd
        # Use selected device for input, system default for output
        device = (self._device, None) if self._device is not None else None
        self._stream = sd.Stream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            device=device,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @staticmethod
    def _callback(indata, outdata, frames, time, status):
        outdata[:] = indata


class AudioAnalyzer:
    """Spectral analysis of audio samples."""

    @staticmethod
    def analyze_samples(samples: np.ndarray, sample_rate: int) -> dict:
        """Return spectral analysis of audio samples."""
        n = len(samples)
        fft_vals = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

        # Fundamental frequency (strongest peak above 20 Hz)
        min_bin = int(20 * n / sample_rate)
        peak_bin = min_bin + np.argmax(fft_vals[min_bin:])
        fundamental_hz = freqs[peak_bin]

        # Spectral centroid
        magnitude_sum = np.sum(fft_vals)
        if magnitude_sum > 0:
            centroid = np.sum(freqs * fft_vals) / magnitude_sum
        else:
            centroid = 0.0

        # Amplitude envelope (split into 50ms windows)
        window_size = int(sample_rate * 0.05)
        envelope = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i:i + window_size]
            envelope.append(float(np.sqrt(np.mean(chunk ** 2))))

        # Harmonic content
        harmonic_bins = []
        for h in range(2, 9):
            hfreq = fundamental_hz * h
            hbin = int(hfreq * n / sample_rate)
            if hbin < len(fft_vals):
                harmonic_bins.append(float(fft_vals[hbin]))
        harmonic_energy = sum(harmonic_bins) if harmonic_bins else 0
        total_energy = float(np.sum(fft_vals[min_bin:]))
        harmonic_ratio = harmonic_energy / total_energy if total_energy > 0 else 0

        return {
            "fundamental_hz": float(fundamental_hz),
            "spectral_centroid_hz": float(centroid),
            "harmonic_ratio": float(harmonic_ratio),
            "envelope": envelope[:20],
            "duration_s": len(samples) / sample_rate,
        }

    @staticmethod
    def compare_samples(
        target: np.ndarray, recorded: np.ndarray, sample_rate: int
    ) -> dict:
        """Compare two audio signals spectrally."""
        a1 = AudioAnalyzer.analyze_samples(target, sample_rate)
        a2 = AudioAnalyzer.analyze_samples(recorded, sample_rate)

        freq_diff = abs(a1["fundamental_hz"] - a2["fundamental_hz"]) / max(a1["fundamental_hz"], 1)
        centroid_diff = abs(a1["spectral_centroid_hz"] - a2["spectral_centroid_hz"]) / max(a1["spectral_centroid_hz"], 1)
        harmonic_diff = abs(a1["harmonic_ratio"] - a2["harmonic_ratio"])

        distance = (freq_diff + centroid_diff + harmonic_diff) / 3

        return {
            "spectral_distance": float(distance),
            "fundamental_diff_hz": float(a1["fundamental_hz"] - a2["fundamental_hz"]),
            "centroid_diff_hz": float(a1["spectral_centroid_hz"] - a2["spectral_centroid_hz"]),
            "harmonic_ratio_diff": float(a1["harmonic_ratio"] - a2["harmonic_ratio"]),
            "target_analysis": a1,
            "recorded_analysis": a2,
        }
