from __future__ import annotations

TOOL_DEFINITIONS = [
    {
        "name": "set_parameter",
        "description": "Set a synth parameter on the connected Korg RK-100S 2. The parameter change is sent immediately via MIDI and heard in real-time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name (e.g., 'voice_mode', 'arp_on_off')"},
                "value": {"type": "integer", "description": "Value to set (within the parameter's valid range)"},
            },
            "required": ["name", "value"],
        },
    },
    {
        "name": "get_parameter",
        "description": "Get the current value of a synth parameter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_parameters",
        "description": "List all available synth parameters with their current values, valid ranges, and descriptions.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "trigger_note",
        "description": "Play a MIDI note on the synth so we can hear or record the current sound.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "integer", "description": "MIDI note number (60 = middle C)", "default": 60},
                "velocity": {"type": "integer", "description": "Note velocity (0-127)", "default": 100},
                "duration_ms": {"type": "integer", "description": "Duration in milliseconds", "default": 1000},
            },
        },
    },
    {
        "name": "record_audio",
        "description": "Record audio from the computer's audio input for the specified duration. Returns the file path of the recorded WAV.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_s": {"type": "number", "description": "Recording duration in seconds", "default": 2.0},
            },
        },
    },
    {
        "name": "analyze_audio",
        "description": "Analyze a WAV file and return spectral characteristics: fundamental frequency, harmonic series, spectral centroid, amplitude envelope shape.",
        "input_schema": {
            "type": "object",
            "properties": {
                "wav_path": {"type": "string", "description": "Path to the WAV file to analyze"},
            },
            "required": ["wav_path"],
        },
    },
    {
        "name": "compare_audio",
        "description": "Compare two audio files spectrally and return a similarity report showing which frequencies differ most.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "description": "Path to the target WAV file"},
                "recorded_path": {"type": "string", "description": "Path to the recorded WAV file"},
            },
            "required": ["target_path", "recorded_path"],
        },
    },
]
