from __future__ import annotations
import json
from pathlib import Path
from model.patch import Patch
from model.bank import Bank


class Library:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._patches_dir = self.root / "patches"
        self._banks_dir = self.root / "banks"
        self._patches_dir.mkdir(parents=True, exist_ok=True)
        self._banks_dir.mkdir(parents=True, exist_ok=True)

    def _unique_path(self, directory: Path, slug: str, suffix: str) -> Path:
        path = directory / f"{slug}{suffix}"
        counter = 1
        while path.exists():
            path = directory / f"{slug}-{counter}{suffix}"
            counter += 1
        return path

    def save_patch(self, patch: Patch) -> Path:
        path = self._unique_path(self._patches_dir, patch.slug, ".json")
        patch.save(path)
        return path

    def list_patches(self) -> list[Patch]:
        result = []
        for f in sorted(self._patches_dir.glob("*.json")):
            try:
                result.append(Patch.load(f))
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                pass  # skip malformed or unreadable files
        return result

    def delete_patch(self, json_path: Path) -> None:
        syx = json_path.with_suffix(".syx")
        if syx.exists():
            syx.unlink()
        if json_path.exists():
            json_path.unlink()

    def save_bank(self, bank: Bank) -> Path:
        path = self._unique_path(self._banks_dir, bank.slug, ".json")
        bank.save(path)
        return path

    def list_banks(self) -> list[Bank]:
        result = []
        for f in sorted(self._banks_dir.glob("*.json")):
            try:
                result.append(Bank.load(f))
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                pass  # skip malformed or unreadable files
        return result
