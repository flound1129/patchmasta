import signal
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Korg RK-100S 2 Patch Manager")
    font = app.font()
    font.setPointSize(13)
    app.setFont(font)

    # Let Ctrl+C shut down cleanly. Qt's event loop blocks Python's signal
    # handling, so a timer ticks periodically to give Python a chance to run.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
