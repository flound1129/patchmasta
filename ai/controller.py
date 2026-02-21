from __future__ import annotations
import threading
import time
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from ai.llm import LLMBackend, Message
from ai.tools import TOOL_DEFINITIONS
from midi.params import ParamMap
from core.logger import AppLogger

SYSTEM_PROMPT = """You are an AI sound designer for the Korg RK-100S 2 keytar synthesizer.
You can control synth parameters in real-time via MIDI. When the user describes a sound they want,
translate their description into parameter changes.

Available parameter categories:
- Arpeggiator: on/off, latch, type, gate, select
- Voice: mode (single/layer/split/multi)
- Virtual Patches: 5 modulation routings (source -> destination with intensity)
- Vocoder: on/off, fc modulation source

When matching a sound from a WAV file:
1. First analyze the WAV to understand its spectral characteristics
2. Set initial parameters based on your analysis
3. Trigger a note, record the output, and compare
4. Iteratively adjust parameters to minimize the spectral difference

Think step-by-step about which parameters affect which sonic qualities."""


class AIController(QObject):
    response_ready = pyqtSignal(str)      # AI text response
    tool_executed = pyqtSignal(str, str)  # tool_name, result_summary
    error = pyqtSignal(str)

    def __init__(
        self,
        backend: LLMBackend,
        device,
        param_map: ParamMap,
        logger: AppLogger,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._device = device
        self._param_map = param_map
        self._logger = logger
        self._history: list[Message] = []
        self._param_state: dict[str, int] = {}
        self._stop_requested = False
        self._audio_device = None

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
            return f"Unknown parameter: {name}"
        if not self._device.connected:
            return "Device not connected"
        msg = param.build_message(channel=1, value=value)
        for i in range(0, len(msg), 3):
            self._device.send(msg[i:i + 3])
        self._param_state[name] = value
        return f"Set {name} = {value}"

    def _tool_get_parameter(self, name: str) -> str:
        if name in self._param_state:
            return f"{name} = {self._param_state[name]}"
        return f"{name} = unknown (not yet set in this session)"

    def _tool_list_parameters(self) -> str:
        lines = []
        for p in self._param_map.list_all():
            current = self._param_state.get(p.name, "?")
            lines.append(f"{p.name}: {p.description} [{p.min_val}-{p.max_val}] current={current}")
        return "\n".join(lines)

    def _tool_trigger_note(self, note: int, velocity: int, duration_ms: int) -> str:
        if not self._device.connected:
            return "Device not connected"
        self._device.send_note_on(channel=1, note=note, velocity=velocity)
        time.sleep(duration_ms / 1000.0)
        self._device.send_note_off(channel=1, note=note)
        return f"Played note {note} vel={velocity} for {duration_ms}ms"

    def _tool_record_audio(self, duration_s: float) -> str:
        # Placeholder - implemented in Task 10
        return "Audio recording not yet implemented"

    def _tool_analyze_audio(self, wav_path: str) -> str:
        # Placeholder - implemented in Task 10
        return "Audio analysis not yet implemented"

    def _tool_compare_audio(self, target_path: str, recorded_path: str) -> str:
        # Placeholder - implemented in Task 10
        return "Audio comparison not yet implemented"
