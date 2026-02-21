from __future__ import annotations
import json
from pathlib import Path


class Bank:
    def __init__(self, name: str) -> None:
        self.name = name
        self.slots: dict[int, Path] = {}

    def assign(self, slot: int, patch_file: Path) -> None:
        self.slots[slot] = patch_file

    def remove(self, slot: int) -> None:
        self.slots.pop(slot, None)

    def ordered_slots(self) -> list[tuple[int, Path]]:
        return sorted(self.slots.items())

    def save(self, path: Path) -> None:
        d = {
            "name": self.name,
            "slots": [
                {"slot": slot, "patch_file": str(pf)}
                for slot, pf in self.ordered_slots()
            ],
        }
        path.write_text(json.dumps(d, indent=2))

    @classmethod
    def load(cls, path: Path) -> Bank:
        d = json.loads(path.read_text())
        bank = cls(name=d["name"])
        for entry in d.get("slots", []):
            bank.assign(entry["slot"], Path(entry["patch_file"]))
        return bank

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-")
