from __future__ import annotations
import threading
import time
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from ai.llm import LLMBackend, Message
from ai.tools import TOOL_DEFINITIONS
import re
from midi.params import ParamMap
from midi.sysex_buffer import SysExProgramBuffer, DebouncedSysExWriter
from midi.sysex import build_program_write
from midi.effects import (
    EFFECT_TYPES, FX1_TYPE_PACKED, FX2_TYPE_PACKED, fx_param_packed,
    EffectParam,
)
from core.logger import AppLogger

SYSTEM_PROMPT = """You are an AI sound designer for the Korg RK-100S 2 keytar synthesizer.
You can control synth parameters in real-time via MIDI. When the user describes a sound they want,
translate their description into parameter changes.

Available parameter sections (per timbre):
- Oscillator 1: Wave (Saw/Pulse/Triangle/Sine/Formant/Noise/PCM-DWGS/Audio In), OSC Mod, Control 1/2, Wave Select
- Oscillator 2: Wave, OSC Mod (Off/Ring/Sync/Ring+Sync), Semitone, Tune
- Mixer: OSC1/OSC2/Noise levels, Punch Level
- Filter 1: Balance (LPF24/LPF12/HPF/BPF/THRU), Cutoff, Resonance, EG Int, Key Track, Velo Sens
- Filter 2: Type (LPF/HPF/BPF), Cutoff, Resonance, EG Int, Key Track, Velo Sens
- Filter Routing: Single/Serial/Parallel/Individual
- AMP: Level, Pan, Key Track, Wave Shape Depth/Type/Position
- Filter EG / AMP EG / Assignable EG: Attack, Decay, Sustain, Release, Lv.Velo
- LFO1 / LFO2: Wave, Key Sync, BPM Sync, Frequency, Sync Note
- Voice: Assign (Mono1/Mono2/Poly), Unison SW/Detune/Spread, Analog Tuning
- Pitch: Transpose, Bend Range, Detune, Vibrato Int, Portamento
- Timbre EQ: Low/High Freq + Gain

Common parameters:
- Voice Mode: Single/Layer/Split/Multi
- Arpeggiator: ON/OFF, Latch, Type, Gate, Select, Octave Range, Resolution, Last Step, Key Sync, Swing, Steps 1-8
- Virtual Patches 1-5: Source, Destination, Intensity
- Scale: scale (0=Equal Temp, 1=Pure Major, 2=Pure Minor, ... 20=Arabic), scale_key
- Master Effects 1 & 2: FX Type, Ribbon Assign/Polarity
  FX type IDs: 0=Off, 1=Compressor, 2=Filter, 3=4Band EQ, 4=Distortion, 5=Decimator,
  6=Delay, 7=L/C/R Delay, 8=Auto Panning Delay, 9=Modulation Delay, 10=Tape Echo,
  11=Chorus, 12=Flanger, 13=Vibrato, 14=Phaser, 15=Tremolo, 16=Ring Modulator,
  17=Grain Shifter. Set via fx1_type / fx2_type.
  When an effect type is active, its parameters are available as fx1_{param_key} / fx2_{param_key}
  (e.g. fx1_dry_wet, fx1_feedback). Use list_parameters to see currently available FX params.
- Vocoder: ON/OFF, Carrier levels, Modulator settings, Filter, AMP, 16-band Level/Pan
- Ribbon: Long Ribbon scale/pitch/filter, Short Ribbon settings

Parameters prefixed t1_ are Timbre 1, t2_ are Timbre 2.
NRPN params (arp, voice_mode, virtual patch src/dst, vocoder sw/band) send in real-time.
All other params require SysEx program write (handled automatically with debouncing).

When matching a sound from a WAV file:
1. First analyze the WAV to understand its spectral characteristics
2. Set initial parameters based on your analysis
3. Trigger a note, record the output, and compare
4. Iteratively adjust parameters to minimize the spectral difference

Think step-by-step about which parameters affect which sonic qualities."""


class AIController(QObject):
    response_ready = pyqtSignal(str)      # AI text response
    tool_executed = pyqtSignal(str, str)  # tool_name, result_summary
    parameter_changed = pyqtSignal(str, int)  # param_name, value
    note_played = pyqtSignal(int, int, bool)  # note, velocity, is_on
    error = pyqtSignal(str)

    def __init__(
        self,
        backend: LLMBackend,
        device,
        param_map: ParamMap,
        logger: AppLogger,
        sysex_buffer: SysExProgramBuffer | None = None,
        sysex_writer: DebouncedSysExWriter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._device = device
        self._param_map = param_map
        self._logger = logger
        self._sysex_buffer = sysex_buffer
        self._sysex_writer = sysex_writer
        self._history: list[Message] = []
        self._param_state: dict[str, int] = {}
        self._stop_requested = False
        self._audio_device = None
        self._auto_play_note = True  # play a note after each set_parameter call
        self._auto_note = 60         # middle C
        self._auto_note_velocity = 100
        self._auto_note_duration_ms = 300
        self._suppress_notes = False  # set True while MIDI file is playing

    def send_message(self, user_text: str) -> None:
        """Send a user message. Runs LLM call in a background thread."""
        self._history.append(Message(role="user", content=user_text))
        thread = threading.Thread(target=self._run_chat, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop_requested = True

    def _run_chat(self) -> None:
        try:
            self._stop_requested = False
            while not self._stop_requested:
                response = self._backend.chat(
                    messages=self._history,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                )
                if response.content:
                    self.response_ready.emit(response.content)
                if not response.tool_calls:
                    self._history.append(response)
                    break
                self._history.append(response)
                for tc in response.tool_calls:
                    result = self._execute_tool(tc["name"], tc["input"])
                    self.tool_executed.emit(tc["name"], str(result))
                    self._history.append(Message(
                        role="user",
                        content=f'Tool result for {tc["name"]}: {result}',
                    ))
        except Exception as exc:
            self.error.emit(str(exc))

    def _execute_tool(self, name: str, args: dict) -> str:
        self._logger.ai(f"Tool call: {name}({args})")
        if name == "set_parameter":
            return self._tool_set_parameter(args["name"], args["value"])
        if name == "get_parameter":
            return self._tool_get_parameter(args["name"])
        if name == "list_parameters":
            return self._tool_list_parameters()
        if name == "trigger_note":
            return self._tool_trigger_note(
                args.get("note", 60),
                args.get("velocity", 100),
                args.get("duration_ms", 1000),
            )
        if name == "record_audio":
            return self._tool_record_audio(args.get("duration_s", 2.0))
        if name == "analyze_audio":
            return self._tool_analyze_audio(args["wav_path"])
        if name == "compare_audio":
            return self._tool_compare_audio(args["target_path"], args["recorded_path"])
        return f"Unknown tool: {name}"

    def _tool_set_parameter(self, name: str, value: int) -> str:
        param = self._param_map.get(name)
        if param is None:
            # Try dynamic FX effect params
            resolved = self._resolve_fx_param(name)
            if resolved is not None:
                return self._set_fx_param(name, value, *resolved)
            return f"Unknown parameter: {name}"
        if not self._device.connected:
            return "Device not connected"

        sent_via = []

        # NRPN/CC params: send real-time MIDI
        if param.is_nrpn or param.cc_number is not None:
            msg = param.build_message(channel=1, value=value)
            for i in range(0, len(msg), 3):
                self._device.send(msg[i:i + 3])
            sent_via.append("NRPN" if param.is_nrpn else "CC")

        # SysEx params: update buffer and schedule debounced write
        if param.sysex_offset is not None:
            if self._sysex_buffer is not None and self._sysex_buffer.size > 0:
                self._sysex_buffer.set_param(param, value)
                if self._sysex_writer is not None:
                    self._sysex_writer.schedule()
                sent_via.append("SysEx")
            elif not sent_via:
                return f"Parameter {name} requires SysEx but no program is loaded"

        if not sent_via:
            return f"Parameter {name} has no MIDI address"

        self._param_state[name] = value
        self.parameter_changed.emit(name, value)

        if self._auto_play_note:
            self._flush_and_play_note()

        return f"Set {name} = {value} (via {'+'.join(sent_via)})"

    def _set_fx_param(self, name: str, value: int,
                      slot: int, packed: int, ep: EffectParam) -> str:
        if not self._device.connected:
            return "Device not connected"
        value = max(ep.min_val, min(ep.max_val, value))
        self._sysex_buffer.set_byte(packed, value & 0x7F)
        if self._sysex_writer is not None:
            self._sysex_writer.schedule()
        self._param_state[name] = value
        self.parameter_changed.emit(name, value)
        if self._auto_play_note:
            self._flush_and_play_note()
        return f"Set {name} = {value} (via SysEx)"

    _FX_PARAM_RE = re.compile(r"^fx([12])_(.+)$")

    def _resolve_fx_param(self, name: str) -> tuple[int, int, EffectParam] | None:
        """Parse an ``fx{1|2}_{key}`` name and resolve it against the current FX type.

        Returns ``(slot, packed_offset, EffectParam)`` or ``None``.
        """
        m = self._FX_PARAM_RE.match(name)
        if m is None:
            return None
        slot = int(m.group(1))
        key = m.group(2)
        if self._sysex_buffer is None or self._sysex_buffer.size == 0:
            return None
        type_packed = FX1_TYPE_PACKED if slot == 1 else FX2_TYPE_PACKED
        type_id = self._sysex_buffer.get_byte(type_packed)
        effect = EFFECT_TYPES.get(type_id)
        if effect is None or type_id == 0:
            return None
        for ep in effect.params:
            if ep.key == key:
                packed = fx_param_packed(slot, ep.slot_index)
                return (slot, packed, ep)
        return None

    def _flush_and_play_note(self) -> None:
        """Flush any pending SysEx write immediately, then play a brief note."""
        if not self._device.connected or self._suppress_notes:
            return
        # Flush dirty SysEx buffer before playing so the note uses updated params
        if (self._sysex_buffer is not None
                and self._sysex_buffer.dirty
                and self._sysex_buffer.size > 0):
            try:
                data = self._sysex_buffer.to_bytes()
                msg = build_program_write(channel=1, data=data)
                self._device.send(msg)
                self._sysex_buffer.mark_clean()
                time.sleep(0.05)  # give device time to process SysEx before note
            except Exception:
                pass
        try:
            self.note_played.emit(self._auto_note, self._auto_note_velocity, True)
            self._device.send_note_on(channel=1, note=self._auto_note,
                                       velocity=self._auto_note_velocity)
            time.sleep(self._auto_note_duration_ms / 1000.0)
            self._device.send_note_off(channel=1, note=self._auto_note)
            self.note_played.emit(self._auto_note, 0, False)
        except Exception:
            pass

    def _tool_get_parameter(self, name: str) -> str:
        param = self._param_map.get(name)
        if param is None:
            resolved = self._resolve_fx_param(name)
            if resolved is not None:
                _slot, packed, _ep = resolved
                val = self._sysex_buffer.get_byte(packed)
                return f"{name} = {val}"
            return f"Unknown parameter: {name}"
        # Try reading from SysEx buffer first (most accurate)
        if (param.sysex_offset is not None
                and self._sysex_buffer is not None
                and self._sysex_buffer.size > 0):
            val = self._sysex_buffer.get_param(param)
            if val is not None:
                return f"{name} = {val}"
        # Fall back to in-memory state
        if name in self._param_state:
            return f"{name} = {self._param_state[name]}"
        return f"{name} = unknown (not yet set in this session)"

    def _tool_list_parameters(self) -> str:
        lines = []
        for p in self._param_map.list_all():
            current = self._param_state.get(p.name, "?")
            lines.append(f"{p.name}: {p.description} [{p.min_val}-{p.max_val}] current={current}")
        # Append dynamic FX effect params based on current FX types
        if self._sysex_buffer is not None and self._sysex_buffer.size > 0:
            for slot, type_packed in ((1, FX1_TYPE_PACKED), (2, FX2_TYPE_PACKED)):
                type_id = self._sysex_buffer.get_byte(type_packed)
                effect = EFFECT_TYPES.get(type_id)
                if effect is None or type_id == 0:
                    continue
                lines.append(f"--- FX{slot}: {effect.name} ---")
                for ep in effect.params:
                    pname = f"fx{slot}_{ep.key}"
                    packed = fx_param_packed(slot, ep.slot_index)
                    val = self._sysex_buffer.get_byte(packed)
                    lines.append(
                        f"{pname}: {ep.display_name} [{ep.min_val}-{ep.max_val}] current={val}"
                    )
        return "\n".join(lines)

    def _tool_trigger_note(self, note: int, velocity: int, duration_ms: int) -> str:
        if not self._device.connected:
            return "Device not connected"
        if self._suppress_notes:
            return "Notes suppressed (MIDI file is playing)"
        self.note_played.emit(note, velocity, True)
        self._device.send_note_on(channel=1, note=note, velocity=velocity)
        time.sleep(duration_ms / 1000.0)
        self._device.send_note_off(channel=1, note=note)
        self.note_played.emit(note, 0, False)
        return f"Played note {note} vel={velocity} for {duration_ms}ms"

    def match_sound(self, wav_path: str, max_iterations: int = 10) -> None:
        """Start sound matching in a background thread."""
        thread = threading.Thread(
            target=self._run_match, args=(wav_path, max_iterations), daemon=True
        )
        thread.start()

    def _run_match(self, wav_path: str, max_iterations: int) -> None:
        try:
            self._stop_requested = False
            self._logger.ai(f"Analyzing target: {wav_path}")
            prompt = (
                f"I want to match this sound. Here is the spectral analysis of the target WAV:\n\n"
                f"{self._tool_analyze_audio(wav_path)}\n\n"
                f"Based on this analysis, set the synth parameters to your best initial guess. "
                f"Then trigger a note so we can record and compare."
            )
            self._history.append(Message(role="user", content=prompt))
            for iteration in range(max_iterations):
                if self._stop_requested:
                    self.response_ready.emit("Matching stopped by user.")
                    break
                self._run_chat()
                self._logger.ai(f"Match iteration {iteration + 1}/{max_iterations}")
        except Exception as exc:
            self.error.emit(str(exc))

    def _tool_record_audio(self, duration_s: float) -> str:
        from audio.engine import AudioRecorder
        import tempfile
        recorder = AudioRecorder(device=self._audio_device)
        samples = recorder.record(duration_s)
        path = Path(tempfile.mktemp(suffix=".wav"))
        recorder.save_wav(samples, path)
        self._logger.audio(f"Recorded {duration_s}s to {path}")
        return f"Recorded to {path}"

    def _tool_analyze_audio(self, wav_path: str) -> str:
        from audio.engine import AudioRecorder, AudioAnalyzer
        samples, sr = AudioRecorder.load_wav(Path(wav_path))
        analysis = AudioAnalyzer.analyze_samples(samples, sr)
        self._logger.audio(f"Analyzed {wav_path}: {analysis['fundamental_hz']:.1f} Hz")
        return str(analysis)

    def _tool_compare_audio(self, target_path: str, recorded_path: str) -> str:
        from audio.engine import AudioRecorder, AudioAnalyzer
        t_samples, t_sr = AudioRecorder.load_wav(Path(target_path))
        r_samples, r_sr = AudioRecorder.load_wav(Path(recorded_path))
        report = AudioAnalyzer.compare_samples(t_samples, r_samples, t_sr)
        self._logger.audio(f"Spectral distance: {report['spectral_distance']:.4f}")
        return str(report)
