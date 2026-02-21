# AI Sound Designer — Design Document

## Goal

Add an AI-powered chat interface to patchmasta that lets users describe sounds in natural language, and have the AI translate those descriptions into synth parameter changes on the Korg RK-100S 2 in real-time. Includes WAV-based sound matching: analyze a target waveform, make an initial best-guess patch, then iteratively refine using audio recording feedback.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       PyQt6 UI                           │
│  ┌─────────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌────────┐ │
│  │ Library │ │ Detail │ │ Chat │ │ Device │ │  Log   │ │
│  │ Panel   │ │ Panel  │ │Panel │ │ Panel  │ │ Panel  │ │
│  └─────────┘ └────────┘ └──┬───┘ └────────┘ └────────┘ │
│                            │                             │
│              ┌─────────────┴──────────────┐              │
│              │      AI Controller         │              │
│              │   (tool-use LLM layer)     │              │
│              └─────────────┬──────────────┘              │
│         ┌──────────────────┼──────────────────┐          │
│         ▼                  ▼                  ▼          │
│   ┌──────────┐     ┌────────────┐     ┌────────────┐    │
│   │  Param   │     │   Audio    │     │    MIDI    │    │
│   │   Map    │     │   Engine   │     │   Device   │    │
│   └──────────┘     └────────────┘     └────────────┘    │
└──────────────────────────────────────────────────────────┘
```

## Components

### 1. Chat Panel (UI)

New panel in the main window splitter.

- Scrollable message history (user + AI turns)
- Text input at the bottom with send button
- "Drop WAV" zone / file picker button at the top
- "Match Sound" button — starts the analyze → guess → record → refine loop
- "Stop" button — halts matching iteration
- Parameter changes shown inline (e.g., "Set Filter Cutoff → 85")

### 2. Log Panel (UI)

Replaces all `print()` debug output with an in-app log viewer.

- Dockable panel (bottom or right side)
- Scrollable, monospace text area showing timestamped log messages
- Categories: MIDI TX/RX, AI, Audio, General
- "Copy" button — copies full log contents to clipboard
- All existing `print()` calls route through a central logger that emits to both the log panel and stdout

### 3. AI Controller

Orchestrates LLM calls with tool-use/function-calling.

- Abstracted LLM interface with two backends:
  - **Claude** (Anthropic API) — tool-use via the messages API
  - **Groq** — tool-use via their OpenAI-compatible API (Llama/Mixtral)
- Backend selectable in a settings dropdown
- API keys stored in a local config file (`~/.patchmasta/config.json`)
- System prompt includes:
  - Full parameter descriptions from the Parameter Guide (name, range, sonic effect)
  - Current patch state (all known parameter values)
  - Synthesis reasoning instructions

### 4. LLM Tool Interface

Tools available to the AI via function/tool-use:

| Tool | Purpose |
|------|---------|
| `set_parameter(name, value)` | Change a synth parameter on the device |
| `get_parameter(name)` | Read current value of a parameter |
| `list_parameters()` | Show all available parameters with ranges |
| `trigger_note(note, velocity, duration)` | Play a note so we can record the result |
| `record_audio(duration)` | Capture from audio input device |
| `analyze_audio(wav_path)` | Spectral analysis of a WAV file |
| `compare_audio(target, recorded)` | Spectral diff between target and current output |

### 5. Parameter Map

Maps human-readable parameter names to MIDI messages.

- Each entry: name, description, valid range, sonic effect, MIDI message type (NRPN/CC/SysEx)
- Initial coverage: documented NRPN parameters (arpeggiator, virtual patches, vocoder, voice mode)
- Extended coverage: reverse-engineer SysEx parameter change messages from the Korg Sound Editor to cover core synth parameters (oscillator, filter, amp, EG, LFO, mixer, effects)
- Pluggable: new parameters added to a data file without code changes

### 6. Audio Engine

Records and analyzes audio.

- **Recording**: capture from a selectable audio input device (PyAudio or sounddevice)
- **Analysis**: FFT, harmonic series detection, amplitude envelope (ADSR shape), spectral centroid, MFCC
- **Comparison**: compute spectral distance between target WAV and recorded audio, generate a human-readable diff report for the AI

### 7. Sound Matching Pipeline

```
Target WAV
    │
    ▼
┌──────────────┐     ┌───────────────────┐
│Audio Analyzer │────▶│  AI (Claude/Groq) │
│ - FFT         │     │  "Looks like a    │
│ - Harmonics   │     │   saw wave with   │
│ - Envelope    │     │   LP filter..."   │
│ - MFCC        │     └────────┬──────────┘
└───────────────┘              │
                               ▼
                     ┌─────────────────┐
                     │ set_parameter() │──▶ Device
                     └─────────────────┘
                               │
               ┌───────────────┘  (iterative refinement)
               ▼
       ┌──────────────┐
       │ trigger_note │──▶ Device plays note
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │ record_audio │◀── Audio In
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │compare_audio │ target vs recorded
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │  AI adjusts  │──▶ set_parameter() ──▶ repeat
       └──────────────┘
```

1. **Analyze target WAV** — spectral content, harmonics, envelope shape
2. **AI makes initial best-guess** from waveform analysis alone (no recording)
3. **Send parameters to device** via NRPN/CC/SysEx
4. **Trigger a note** on the device via MIDI note-on
5. **Record synth output** from audio input
6. **Compare** recorded vs target (spectral distance)
7. **AI adjusts parameters** based on the difference
8. **Repeat** steps 4-7 until converged or user stops

Steps 1-3 work without audio input hardware. Steps 4-8 require audio-in.

## Patch Names from SysEx

The Parameter Guide does not document the SysEx program dump byte layout. The patch name offset needs to be discovered empirically:

- Pull a patch with a known name from the device
- Inspect the raw SysEx bytes for ASCII characters
- The name is likely 12 bytes of ASCII at offset 0 of the program data (based on similar Korg instruments like the microKORG XL+)

Once found, `parse_program_dump` in `midi/sysex.py` extracts the name and passes it through to the Patch model instead of the generic "Program NNN" label.

## Dependencies

- **anthropic** — Claude API client
- **groq** — Groq API client (OpenAI-compatible)
- **sounddevice** or **pyaudio** — audio recording
- **numpy** — spectral analysis (FFT)
- **scipy** — signal processing (MFCC, spectral features)

## Config

`~/.patchmasta/config.json`:
```json
{
  "ai_backend": "claude",
  "claude_api_key": "sk-ant-...",
  "groq_api_key": "gsk_...",
  "audio_input_device": null
}
```

## Out of Scope (for now)

- Full visual knob/slider synth editor
- Preset browsing / sound library from the internet
- Osmose (Expressive-E) support (tracked separately)
