#!/usr/bin/env python3
"""Automated SysEx byte-offset discovery for the RK-100S 2.

For NRPN-addressable parameters, this tool toggles each one between its min
and max values via NRPN, pulls program dumps before and after, and diffs to
find which byte(s) changed.  The results are saved to a JSON mapping file
that can be loaded to populate ParamDef.sysex_offset fields at runtime.

For SysEx-only parameters (no NRPN address), an interactive mode prompts the
user to change a specific param on the hardware, then diffs.

Usage (CLI):
    python tools/discover_offsets.py <midi-port-index> [--output offsets.json]
    python tools/discover_offsets.py --interactive <midi-port-index>

Programmatic:
    from tools.discover_offsets import OffsetDiscovery
    discovery = OffsetDiscovery(device, param_map)
    offsets = discovery.discover_nrpn_offsets()
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

from midi.sysex import (
    build_program_dump_request,
    build_program_write,
    parse_program_dump,
)
from midi.params import ParamDef, ParamMap


class OffsetDiscovery:
    """Discovers SysEx byte offsets by toggling params and diffing dumps."""

    def __init__(self, device, param_map: ParamMap, channel: int = 1) -> None:
        self._device = device
        self._param_map = param_map
        self._channel = channel

    # -- Low-level helpers ---------------------------------------------------

    def pull_program(self, timeout: float = 2.0) -> bytes | None:
        """Pull current program dump from device (blocking)."""
        received: list[bytes] = []
        event = threading.Event()

        def on_sysex(midi_event, data=None):
            message, _ = midi_event
            parsed = parse_program_dump(list(message))
            if parsed is not None:
                received.append(parsed)
                event.set()

        self._device.set_sysex_callback(on_sysex)
        self._device.send(build_program_dump_request(channel=self._channel))
        event.wait(timeout=timeout)
        # Clear callback
        self._device.set_sysex_callback(lambda e, d=None: None)
        return received[0] if received else None

    def write_program(self, data: bytes) -> None:
        """Write a full program dump to the device."""
        msg = build_program_write(channel=self._channel, data=data)
        self._device.send(msg)
        time.sleep(0.15)

    def _send_nrpn(self, param: ParamDef, value: int) -> None:
        """Send an NRPN value for a param."""
        self._device.send_nrpn(
            channel=self._channel,
            msb=param.nrpn_msb,
            lsb=param.nrpn_lsb,
            value=max(param.min_val, min(param.max_val, value)) & 0x7F,
        )

    @staticmethod
    def _diff_bytes(a: bytes, b: bytes) -> list[tuple[int, int, int]]:
        """Return [(offset, val_a, val_b), ...] for differing bytes."""
        diffs = []
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                diffs.append((i, a[i], b[i]))
        return diffs

    # -- NRPN auto-discovery -------------------------------------------------

    def discover_nrpn_offsets(
        self,
        on_progress: callable | None = None,
        settle_time: float = 0.15,
    ) -> dict[str, int]:
        """Auto-discover SysEx offsets for all NRPN-addressable params.

        For each NRPN param:
          1. Send min value via NRPN, pull dump
          2. Send max value via NRPN, pull dump
          3. Diff to find which byte(s) changed
          4. Restore the program to its original state

        Args:
            on_progress: callback(index, total, param_name) for progress updates
            settle_time: seconds to wait after NRPN send before pulling

        Returns:
            dict mapping param name → SysEx byte offset
        """
        # Pull baseline for restore
        baseline = self.pull_program()
        if baseline is None:
            raise RuntimeError("Failed to pull baseline program from device")

        nrpn_params = self._param_map.nrpn_params()
        total = len(nrpn_params)
        offsets: dict[str, int] = {}
        ambiguous: dict[str, list[tuple[int, int, int]]] = {}

        try:
            for i, param in enumerate(nrpn_params):
                if on_progress:
                    on_progress(i, total, param.name)

                # Clamp test values to valid NRPN range (0-127)
                val_lo = max(0, param.min_val)
                val_hi = min(127, param.max_val)
                if val_lo == val_hi:
                    continue  # can't diff a param with only one possible value

                # Set to low value, pull
                self._send_nrpn(param, val_lo)
                time.sleep(settle_time)
                dump_lo = self.pull_program()

                # Set to high value, pull
                self._send_nrpn(param, val_hi)
                time.sleep(settle_time)
                dump_hi = self.pull_program()

                if dump_lo is None or dump_hi is None:
                    continue

                diffs = self._diff_bytes(dump_lo, dump_hi)

                if len(diffs) == 1:
                    offsets[param.name] = diffs[0][0]
                elif len(diffs) > 1:
                    # Multiple bytes changed — record the first but flag it
                    offsets[param.name] = diffs[0][0]
                    ambiguous[param.name] = diffs

                # Restore original program state
                self.write_program(baseline)
        finally:
            # Always restore baseline, even if interrupted or an error occurs
            self.write_program(baseline)

        if on_progress:
            on_progress(total, total, "done")

        if ambiguous:
            print(f"\nNote: {len(ambiguous)} param(s) changed multiple bytes:")
            for name, diffs in ambiguous.items():
                offsets_str = ", ".join(f"{d[0]}" for d in diffs)
                print(f"  {name}: offsets [{offsets_str}]")

        return offsets

    # -- Interactive discovery for SysEx-only params -------------------------

    def discover_interactive(
        self,
        param_names: list[str] | None = None,
        on_progress: callable | None = None,
    ) -> dict[str, int]:
        """Interactive offset discovery for SysEx-only params.

        Prompts the user to change a param on the hardware, then diffs the
        program dump to find the offset.

        Args:
            param_names: specific params to discover (default: all SysEx-only
                         params without an offset)
            on_progress: callback(index, total, param_name)

        Returns:
            dict mapping param name → SysEx byte offset
        """
        if param_names:
            params = [self._param_map.get(n) for n in param_names]
            params = [p for p in params if p is not None]
        else:
            params = [
                p for p in self._param_map.list_all()
                if not p.is_nrpn and p.sysex_offset is None
            ]

        baseline = self.pull_program()
        if baseline is None:
            raise RuntimeError("Failed to pull baseline program from device")

        total = len(params)
        offsets: dict[str, int] = {}

        for i, param in enumerate(params):
            if on_progress:
                on_progress(i, total, param.name)

            label = param.display_name or param.name
            input(f"\n[{i+1}/{total}] Change '{label}' on the device, then press Enter...")

            after = self.pull_program()
            if after is None:
                print(f"  Failed to pull — skipping {param.name}")
                continue

            diffs = self._diff_bytes(baseline, after)
            if not diffs:
                print(f"  No changes detected for {param.name}")
                continue

            if len(diffs) == 1:
                offsets[param.name] = diffs[0][0]
                print(f"  Found: {param.name} → offset {diffs[0][0]} "
                      f"(was {diffs[0][1]}, now {diffs[0][2]})")
            else:
                offsets[param.name] = diffs[0][0]
                offsets_str = ", ".join(f"{d[0]}" for d in diffs)
                print(f"  Multiple bytes changed: [{offsets_str}] — using first")

            # Use new state as baseline for next param
            baseline = after

        return offsets

    # -- Persistence ---------------------------------------------------------

    @staticmethod
    def save_offsets(offsets: dict[str, int], path: Path) -> None:
        """Save discovered offsets to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(offsets, indent=2, sort_keys=True))

    @staticmethod
    def load_offsets(path: Path) -> dict[str, int]:
        """Load offsets from a JSON file."""
        return json.loads(path.read_text())

    @staticmethod
    def apply_offsets(param_map: ParamMap, offsets: dict[str, int]) -> int:
        """Apply discovered offsets to a ParamMap's ParamDef objects.

        Returns the number of params updated.
        """
        count = 0
        for name, offset in offsets.items():
            param = param_map.get(name)
            if param is not None:
                param.sysex_offset = offset
                count += 1
        return count


# -- CLI entry point ---------------------------------------------------------

def main() -> None:
    import argparse
    from midi.device import MidiDevice, list_midi_ports
    from core.logger import AppLogger

    parser = argparse.ArgumentParser(description="Discover SysEx byte offsets")
    parser.add_argument("port", type=int, nargs="?", default=None,
                        help="MIDI port index (use --list to see available ports)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available MIDI ports and exit")
    parser.add_argument("--output", "-o", default="offsets.json",
                        help="Output JSON file (default: offsets.json)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode for SysEx-only params")
    parser.add_argument("--settle", type=float, default=0.15,
                        help="Settle time in seconds after NRPN send (default: 0.15)")
    args = parser.parse_args()

    ports = list_midi_ports()
    if not ports:
        print("No MIDI ports found.")
        sys.exit(1)

    print("Available MIDI ports:")
    for i, name in enumerate(ports):
        print(f"  [{i}] {name}")
    print()

    if args.list:
        sys.exit(0)

    if args.port is None:
        print("Usage: python tools/discover_offsets.py <port-index>")
        print("       python tools/discover_offsets.py --list")
        sys.exit(1)

    if args.port >= len(ports):
        print(f"Port index {args.port} out of range (0-{len(ports)-1})")
        sys.exit(1)

    logger = AppLogger()
    device = MidiDevice(logger=logger)
    device.connect(args.port, ports[args.port])
    print(f"Connected to: {ports[args.port]}\n")

    param_map = ParamMap()
    discovery = OffsetDiscovery(device, param_map)

    all_offsets: dict[str, int] = {}

    # Phase 1: auto-discover NRPN params
    if not args.interactive:
        print("=== Phase 1: Auto-discovering NRPN param offsets ===\n")

        def on_progress(idx, total, name):
            if name == "done":
                print(f"\rDiscovered offsets for {total} NRPN params.       ")
            else:
                print(f"\r  [{idx+1}/{total}] {name}...", end="", flush=True)

        nrpn_offsets = discovery.discover_nrpn_offsets(
            on_progress=on_progress,
            settle_time=args.settle,
        )
        all_offsets.update(nrpn_offsets)

        print(f"\nFound {len(nrpn_offsets)} NRPN offsets:")
        for name, offset in sorted(nrpn_offsets.items(), key=lambda x: x[1]):
            print(f"  {name:40s} → offset {offset}")
        print()

    # Phase 2: interactive for remaining params
    if args.interactive:
        print("=== Interactive discovery for SysEx-only params ===\n")
        interactive_offsets = discovery.discover_interactive()
        all_offsets.update(interactive_offsets)

    # Save results
    out_path = Path(args.output)
    discovery.save_offsets(all_offsets, out_path)
    print(f"\nSaved {len(all_offsets)} offset(s) to {out_path}")

    device.disconnect()


if __name__ == "__main__":
    main()
