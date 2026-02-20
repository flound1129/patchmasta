# Korg RK-100S 2 Patch Manager — Design Document

Date: 2026-02-20

## Overview

A desktop GUI application (Python + PyQt6) for creating, organizing, and transferring patches to/from the Korg RK-100S 2 keytar over USB MIDI.

## Goals

- Pull individual or all programs from the device as SysEx dumps
- Push patches back to specific program slots on the device
- Create and edit patch metadata (name, category, notes, slot assignment)
- Organize patches into named banks (ordered lists of program slots)
- Save patches as files on disk for a local library
- Load patches from the device (current program, all 200, or a slot range)

## Device Facts (from Owner's Manual)

- **Connection**: USB (class-compliant, appears as MIDI device)
- **Programs**: 200 total (numbered 1–200 on device, 0–127 via MIDI Program Change + Bank Select)
- **Bank Select**: CC 0 (MSB) + CC 32 (LSB)
- **Program Change**: 0–127
- **SysEx**: Bidirectional; Korg manufacturer ID `0x42`
- **NRPN** (CC 98/99): Supported — enables real-time parameter preview once SysEx/NRPN parameter map is sourced from the Parameter Guide
- **Note**: Full parameter editing requires the RK-100S 2 Parameter Guide (SysEx/NRPN map). Initial version handles program dumps only.

## Architecture: Layered MVC

### Layer 1 — MIDI (`midi/`)

| File | Responsibility |
|------|---------------|
| `device.py` | Port discovery, connect/disconnect, send/receive raw MIDI |
| `sysex.py` | Build Korg SysEx requests; parse received program dumps |

Key operations:
- Request current program dump (SysEx)
- Request program dump by slot number
- Request all 200 program dumps in sequence
- Send program dump to a specific slot
- Send Program Change + Bank Select

### Layer 2 — Data Model (`model/`)

| File | Responsibility |
|------|---------------|
| `patch.py` | Patch object: name, slot, category, notes, raw SysEx bytes |
| `bank.py` | Bank object: name + ordered list of (slot → patch_file) mappings |
| `library.py` | Manages `patches/` and `banks/` directories on disk |

### Layer 3 — Qt UI (`ui/`)

| File | Responsibility |
|------|---------------|
| `main_window.py` | Root window, toolbar, layout |
| `library_panel.py` | Left panel: tree view of banks + loose patches |
| `patch_detail.py` | Center panel: name, slot, category, notes, Save button |
| `device_panel.py` | Right panel: port selector, status, Send/Pull buttons |

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  [Connect ▼ KORG RK-100S 2]  [Load from Device ▼]  [Send Patch] │
├──────────────────┬──────────────────┬───────────────────┤
│  LIBRARY         │  PATCH DETAIL    │  DEVICE           │
│                  │                  │                   │
│  ▼ Live Set 1    │  Name: Fat Pad   │  Status: Connected│
│    Fat Pad       │  Slot:  42       │  Program: 042     │
│    Saw Lead      │  Cat:   Lead     │                   │
│    Bass Riff     │  Notes: ...      │  [Send to Slot]   │
│                  │                  │  [Pull Current]   │
│  ▼ Studio Pads   │  [Save]          │                   │
│    HeavyPad      │                  │                   │
│  ── loose ──     │                  │                   │
│    My Custom 1   │                  │                   │
│                  │                  │                   │
│  [+ Bank]  [+ Patch from Device]                        │
└──────────────────┴──────────────────┴───────────────────┘
```

### Load from Device dropdown

```
[Load from Device ▼]
  ├ Pull Current Program
  ├ Load All Programs (200)
  └ Load Slot Range...
```

Imported patches land as loose patches in the library. User drags them into banks.

## File Formats

### Patch (`patches/<slug>.json` + `patches/<slug>.syx`)

```json
{
  "name": "Fat Pad",
  "program_number": 42,
  "category": "Synth Hard",
  "notes": "",
  "created": "2026-02-20",
  "sysex_file": "patches/fat-pad.syx"
}
```

The `.syx` file is the raw SysEx bytes from the device program dump.

### Bank (`banks/<slug>.json`)

```json
{
  "name": "Live Set 1",
  "slots": [
    {"slot": 0, "patch_file": "patches/fat-pad.json"},
    {"slot": 1, "patch_file": "patches/saw-lead.json"}
  ]
}
```

Unfilled slots are skipped when pushing a bank to the device.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| No device connected | Send/Pull buttons disabled; toolbar shows "Not connected" |
| SysEx timeout (>2s) | Error dialog, no crash |
| Duplicate patch names | Allowed — files are slug-named on disk, display name is metadata |
| Bank with missing patch file | Warn on load, skip missing slot, continue |
| Unsaved changes | Dirty indicator on patch detail; prompt on window close |

## Dependencies

- Python 3.10+
- `PyQt6`
- `python-rtmidi`

## Out of Scope (v1)

- Real-time parameter editing (requires Parameter Guide SysEx/NRPN map)
- Audio preview
- Patch comparison / diff
