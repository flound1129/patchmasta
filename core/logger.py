from __future__ import annotations
from PyQt6.QtCore import QObject, pyqtSignal


class AppLogger(QObject):
    message_logged = pyqtSignal(str, str)  # category, message

    def log(self, category: str, message: str) -> None:
        print(f"[{category}] {message}", flush=True)
        self.message_logged.emit(category, message)

    def midi(self, message: str) -> None:
        self.log("MIDI", message)

    def audio(self, message: str) -> None:
        self.log("AUDIO", message)

    def ai(self, message: str) -> None:
        self.log("AI", message)

    def general(self, message: str) -> None:
        self.log("GENERAL", message)
