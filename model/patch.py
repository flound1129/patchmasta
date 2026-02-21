from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date


@dataclass
class Patch:
    name: str
    program_number: int
    category: str = ""
    notes: str = ""
    sysex_data: bytes | None = None
    created: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        """Return serializable metadata dict. Does not include sysex_file; use save() to write the full JSON."""
        return {
            "name": self.name,
            "program_number": self.program_number,
            "category": self.category,
            "notes": self.notes,
            "created": self.created,
        }

    def save(self, json_path: Path) -> None:
        d = self.to_dict()
        if self.sysex_data is not None:
            syx_path = json_path.with_suffix(".syx")
            syx_path.write_bytes(self.sysex_data)
            d["sysex_file"] = syx_path.name
        else:
            d["sysex_file"] = None
        json_path.write_text(json.dumps(d, indent=2))

    @classmethod
    def load(cls, json_path: Path) -> Patch:
        d = json.loads(json_path.read_text())
        sysex_data = None
        if d.get("sysex_file"):
            syx_path = json_path.parent / d["sysex_file"]
            if syx_path.exists():
                sysex_data = syx_path.read_bytes()
        if "name" not in d:
            raise ValueError(f"Patch JSON missing required 'name' field: {json_path}")
        return cls(
            name=d["name"],
            program_number=d.get("program_number", 0),
            category=d.get("category", ""),
            notes=d.get("notes", ""),
            sysex_data=sysex_data,
            created=d.get("created", date.today().isoformat()),
        )

    @property
    def slug(self) -> str:
        import re
        return re.sub(r"[^\w-]", "-", self.name.lower()).strip("-")
